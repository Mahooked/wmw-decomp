// Probe 3: validate hand-allocated AAPCS64 storage against call sites.
//
// Probe 2 proved the types land correctly, but "Ghidra prints the right
// prototype" is not evidence the *storage* is right. A wrong register
// assignment still prints the right signature while mis-attributing every use
// inside the body, which is worse than no signature at all.
//
// The independent check is the *caller*. A high-pcode CALL operation's inputs
// are the values the caller's dataflow actually passed, so for every call site
// we know which registers were handed over and in what order. Comparing that
// against what AAPCS64 requires for the callee's real parameter list is a
// genuine cross-check that does not consult the callee's stored signature.
//
// Two mistakes worth recording, both made in this probe:
//   - Checking which registers the *callee* reads proves nothing. Compilers use
//     x1..x7 as scratch, so a one-argument function reading x0,x1,x2 in its
//     body is normal; callee-side use is always a superset of the parameters.
//   - Reading arguments from an Instruction's raw pcode finds none. A BL's raw
//     pcode has only the target and callop inputs; the argument list exists
//     solely in the decompiler's high pcode.
//
//     -postScript SigStorageProbe3.java <signaturesTsv> <outDir> <maxCallers>

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.FunctionDefinitionDataType;
import ghidra.program.model.data.ParameterDefinition;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.lang.Register;
import ghidra.program.model.pcode.HighFunction;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.Varnode;

public class SigStorageProbe3 extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] argv = getScriptArgs();
        String sigTsv = argv[0];
        String outDir = argv[1];
        int maxCallers = argv.length > 2 ? Integer.parseInt(argv[2]) : 400;
        PrintWriter w = new PrintWriter(new File(outDir, "sigstorage3.tsv"), "UTF-8");

        ghidra.app.util.parser.FunctionSignatureParser parser =
            new ghidra.app.util.parser.FunctionSignatureParser(
                currentProgram.getDataTypeManager(), null);
        FunctionDefinitionDataType host =
            new ghidra.program.model.data.FunctionDefinitionDataType("_wmw_sig");

        // ---- expected register sequence per callee, from the manglings ------
        Map<Long, String[]> expected = new HashMap<>();
        Map<Long, String> names = new HashMap<>();
        int usable = 0, rejected = 0;
        BufferedReader rd = new BufferedReader(new FileReader(sigTsv));
        for (String line = rd.readLine(); line != null; line = rd.readLine()) {
            if (line.startsWith("#") || line.startsWith("address")) {
                continue;
            }
            String[] p = line.split("\t", -1);
            if (p.length < 6 || p[4].isEmpty() || !p[2].startsWith("_Z")) {
                continue;
            }
            // Skip anything the parser has already been shown to mishandle:
            // templates, function pointers and const-qualified types.
            if (p[4].contains("(") || p[4].contains("<") || p[4].contains("const")) {
                continue;
            }
            String[] types = p[4].split("\\|");
            ParameterDefinition[] defs;
            try {
                defs = parser.parse(host, "void _wmw_sig(" +
                    String.join(", ", types) + ")").getArguments();
            } catch (Throwable t) {
                rejected++;
                continue;
            }
            if (defs.length != types.length) {
                rejected++;
                continue;
            }
            List<String> model = new ArrayList<>();
            int intIdx = 0, vecIdx = 0;
            boolean ok = true;
            for (ParameterDefinition d : defs) {
                if (d.getDataType() == null) {
                    ok = false;
                    break;
                }
                if (isFloating(d.getDataType())) {
                    model.add("v" + Math.min(vecIdx++, 7));
                } else {
                    model.add("i" + Math.min(intIdx++, 7));
                }
            }
            if (!ok || intIdx > 8 || vecIdx > 8) {
                rejected++;
                continue;
            }
            long addr = Long.parseLong(p[0].trim().replaceFirst("^0x", ""), 16);
            expected.put(addr, model.toArray(new String[0]));
            names.put(addr, p[3]);
            usable++;
        }
        rd.close();
        w.println("# callees with a model: " + usable + " (rejected " + rejected + ")");

        // ---- walk callers, collect the registers each CALL passes -----------
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        di.setSimplificationStyle("decompile");
        Map<Long, List<String[]>> observed = new HashMap<>();
        java.util.Set<Long> distinctTargets = new java.util.HashSet<>();
        List<String> sampleTargets = new ArrayList<>();
        int callers = 0, callsSeen = 0, argCalls = 0;
        int allCalls = 0, noTarget = 0, matchedCalls = 0;
        long minCallerAddr = argv.length > 3
            ? Long.parseLong(argv[3].replaceFirst("^0x", ""), 16) : 0L;
        try {
            FunctionIterator fit = currentProgram.getFunctionManager().getFunctions(true);
            while (fit.hasNext() && callers < maxCallers) {
                Function caller = fit.next();
                if (caller.isExternal() || caller.getBody().isEmpty()) {
                    continue;
                }
                // Functions iterate in address order, so the first several
                // hundred are the PLT thunks and ELF init stubs around 0x16xxxx.
                // They call almost nothing interesting; start once the game's
                // own code is reached or the sample is all boilerplate.
                if (caller.getEntryPoint().getOffset() < minCallerAddr) {
                    continue;
                }
                callers++;
                if (monitor.isCancelled()) {
                    break;
                }
                DecompileResults res = di.decompileFunction(caller, 30, monitor);
                if (res == null || !res.decompileCompleted()) {
                    continue;
                }
                HighFunction hf = res.getHighFunction();
                if (hf == null) {
                    continue;
                }
                java.util.Iterator<ghidra.program.model.pcode.PcodeOpAST> ops =
                    hf.getPcodeOps();
                while (ops.hasNext()) {
                    PcodeOp op = ops.next();
                    int opc = op.getOpcode();
                    if (opc != PcodeOp.CALL && opc != PcodeOp.CALLIND) {
                        continue;
                    }
                    allCalls++;
                    Address t = callTarget(op, hf);
                    if (t == null) {
                        noTarget++;
                        if (sampleTargets.size() < 8) {
                            sampleTargets.add("caller " + caller.getEntryPoint() +
                                " op" + opc + " target-is-addr=" +
                                (op.getInput(0) != null && op.getInput(0).isAddress()) +
                                " ninputs=" + op.getNumInputs() +
                                " inputs=" + describeInputs(op));
                        }
                        continue;
                    }
                    distinctTargets.add(t.getOffset());
                    Long key = t.getOffset();
                    if (!expected.containsKey(key)) {
                        continue;
                    }
                    matchedCalls++;
                    callsSeen++;
                    // A CALL's inputs after the first two are the arguments.
                    // CALLIND carries an extra opaque-function input first.
                    int first = opc == PcodeOp.CALLIND ? 3 : 2;
                    List<String> passed = new ArrayList<>();
                    for (int i = first; i < op.getNumInputs(); i++) {
                        String k = argRegKey(op.getInput(i));
                        if (k != null) {
                            passed.add(k);
                        }
                    }
                    if (passed.isEmpty()) {
                        continue;
                    }
                    argCalls++;
                    observed.computeIfAbsent(key, k -> new ArrayList<>())
                        .add(passed.toArray(new String[0]));
                }
            }
        } finally {
            di.dispose();
        }
        w.println("# callers decompiled: " + callers);
        w.println("# CALL/CALLIND ops seen: " + allCalls);
        w.println("# of those with no resolvable target: " + noTarget);
        w.println("# distinct call targets: " + distinctTargets.size());
        w.println("# of those, modelled: " + matchedCalls);
        for (String s : sampleTargets) {
            w.println("# sample " + s);
        }
        w.println("# calls to modelled callees: " + callsSeen);
        w.println("# of those with register arguments: " + argCalls);
        w.println("# distinct callees actually observed: " + observed.size());

        // ---- compare -------------------------------------------------------
        int agree = 0, disagree = 0, sitesJudged = 0, unjudgeable = 0;
        List<String> details = new ArrayList<>();
        for (Map.Entry<Long, List<String[]>> e : observed.entrySet()) {
            String[] model = expected.get(e.getKey());
            for (String[] passed : e.getValue()) {
                if (passed.length > model.length) {
                    // Caller passed more registers than the parameter list has
                    // slots. Either the parameter list is short or the call
                    // target is misidentified -- both worth knowing.
                    disagree++;
                    sitesJudged++;
                    if (details.size() < 30) {
                        details.add(String.format("0x%x", e.getKey()) + "\t" +
                            names.get(e.getKey()) + "\tpassed " + passed.length +
                            " > model " + model.length + "\t" + join(passed));
                    }
                    continue;
                }
                boolean ok = true;
                String why = "";
                for (int i = 0; i < passed.length; i++) {
                    if (!passed[i].equals(model[i])) {
                        ok = false;
                        why = "arg " + i + ": passed " + passed[i] +
                            ", model " + model[i];
                        break;
                    }
                }
                sitesJudged++;
                if (ok) {
                    agree++;
                } else {
                    disagree++;
                    if (details.size() < 30) {
                        details.add(String.format("0x%x", e.getKey()) + "\t" +
                            names.get(e.getKey()) + "\t" + why);
                    }
                }
            }
        }

        w.println("# call sites judged: " + sitesJudged +
            ", agree " + agree + ", disagree " + disagree);
        if (sitesJudged > 0) {
            w.printf("# call-site agreement: %.2f%%%n",
                100.0 * agree / sitesJudged);
        }
        for (String d : details) {
            w.println("DISAGREE\t" + d);
        }
        w.close();
        println("SigStorageProbe3: judged " + sitesJudged + " agree " + agree +
            " disagree " + disagree);
    }

    private String describeInputs(PcodeOp op) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < op.getNumInputs() && i < 6; i++) {
            if (i > 0) {
                sb.append(", ");
            }
            Varnode v = op.getInput(i);
            if (v == null) {
                sb.append("null");
            } else {
                sb.append(v.isAddress() ? "addr" : v.isRegister() ? "reg" : "other");
            }
        }
        return sb.append(']').toString();
    }

    private String join(String[] a) {
        StringBuilder sb = new StringBuilder();
        for (String s : a) {
            if (sb.length() > 0) {
                sb.append(',');
            }
            sb.append(s);
        }
        return sb.toString();
    }

    /** Resolve a CALL/CALLIND's destination to an address, if it is a direct one. */
    private Address callTarget(PcodeOp op, HighFunction hf) {
        Varnode target = op.getInput(0);
        if (target == null || !target.isAddress()) {
            return null;
        }
        Address a = target.getAddress();
        // A direct call points at the callee's entry point; a call to a PLT stub
        // points at the stub. Map through to the function Ghidra created.
        Function f = currentProgram.getFunctionManager().getFunctionContaining(a);
        return f == null ? a : f.getEntryPoint();
    }

    /**
     * Map a CALL argument varnode to an argument-register key ("i0".."i7" for
     * x/w, "v0".."v7" for s/d/q), or null if it is not an argument register.
     *
     * Values passed on the stack are deliberately ignored: a stack argument
     * carries no register evidence, and a partial match is worse than none.
     */
    private String argRegKey(Varnode v) {
        if (v == null) {
            return null;
        }
        // A CALL input is normally the register itself. When it is not (a phi or
        // copy node standing in for one) there is no single answer, so decline
        // rather than guess: a wrong key would look like a real disagreement.
        if (!v.isRegister()) {
            return null;
        }
        Register r = currentProgram.getRegister(v);
        if (r == null) {
            return null;
        }
        String base = r.getBaseRegister().getName();
        if (base.matches("x[0-7]") || base.matches("w[0-7]")) {
            return "i" + base.substring(1);
        }
        if (base.matches("[sdq][0-7]")) {
            return "v" + base.substring(1);
        }
        return null;
    }

    private boolean isFloating(ghidra.program.model.data.DataType dt) {
        String n = dt.getName().toLowerCase();
        return n.contains("float") || n.contains("double");
    }
}
