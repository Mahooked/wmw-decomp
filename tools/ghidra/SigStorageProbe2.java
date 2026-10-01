// Probe 2: can AArch64 parameter storage be assigned explicitly, and does the
// decompiler then honour it?
//
// Probe 1 established that Ghidra's own model cannot be asked for storage
// directly -- getStorageLocations returns the *same* register twice for
// `uint x 2` -- so AAPCS64 has to be allocated by hand. This script checks the
// two things that could still make that impossible:
//   1. are the X/V register views addressable by name?
//   2. does a hand-built VariableStorage survive setCustomVariableStorage and
//      show up in the decompiled prototype?
//
//     -postScript SigStorageProbe2.java <signaturesTsv> <outDir>

import java.io.File;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.app.util.parser.FunctionSignatureParser;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.DataType;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.ParameterImpl;
import ghidra.program.model.listing.Variable;
import ghidra.program.model.listing.VariableStorage;

public class SigStorageProbe2 extends GhidraScript {

    private static final String[] INT_REGS = {
        "x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7" };
    // 32-bit views of the same registers, for 4-byte integer and bool arguments.
    private static final String[] W_REGS = {
        "w0", "w1", "w2", "w3", "w4", "w5", "w6", "w7" };
    // There is no "v0" in Ghidra's AArch64 register file: the vector file is
    // q0..q7, with s0..s7 (32-bit) and d0..d7 (64-bit) as views of the same
    // storage. A float belongs in the s view and a double in the d view, so
    // the register is chosen from the parameter's own size.
    private static final String[] VEC_REGS_S = {
        "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7" };
    private static final String[] VEC_REGS_D = {
        "d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7" };

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String sigTsv = args[0];
        String outDir = args[1];
        PrintWriter w = new PrintWriter(
            new File(outDir, "sigstorage2.tsv"), "UTF-8");

        // Ghidra's AArch64 register file has no "v0": the 128-bit view is "q0"
        // and the low views are "s0" (32-bit) and "d0" (64-bit), all sharing one
        // address. Passing a whole q register for a float parameter would work,
        // but the 32-bit s register is the honest size for a float.
        Register x0 = currentProgram.getRegister("x0");
        Register v0 = currentProgram.getRegister("q0");
        Register w0 = currentProgram.getRegister("w0");
        Register d0 = currentProgram.getRegister("d0");
        Register s0 = currentProgram.getRegister("s0");
        Register q0 = currentProgram.getRegister("q0");
        w.println("# x0=" + reg(x0) + " w0=" + reg(w0));
        w.println("# v0=" + reg(v0) + " s0=" + reg(s0) + " d0=" + reg(d0) + " q0=" + reg(q0));
        for (String n : new String[] { "x8", "x30", "sp", "xzr" }) {
            w.println("# " + n + "=" + reg(currentProgram.getRegister(n)));
        }
        if (x0 == null || v0 == null) {
            w.println("# FATAL: expected x0 and v0 to exist");
            w.close();
            return;
        }

        // Pick a target: a real, small, all-scalar function from the table so
        // the before/after comparison is about storage and nothing else.
        List<String[]> rows = new ArrayList<>();
        java.io.BufferedReader rd =
            new java.io.BufferedReader(new java.io.FileReader(sigTsv));
        for (String line = rd.readLine(); line != null; line = rd.readLine()) {
            if (line.startsWith("#") || line.startsWith("address")) {
                continue;
            }
            String[] p = line.split("\t", -1);
            if (p.length >= 6 && !p[4].isEmpty() && p[2].startsWith("_Z")) {
                boolean allScalar = true;
                for (String t : p[4].split("\\|")) {
                    if (t.contains("(") || t.contains("<") || t.contains(" ") && !t.endsWith("*")) {
                        allScalar = false;
                        break;
                    }
                }
                if (allScalar) {
                    rows.add(p);
                }
            }
        }
        w.println("# all-scalar mangled signatures: " + rows.size());

        // The known-good route: FunctionSignatureParser, with the parameters
        // declared under a throwaway name so the qualified return type does not
        // confuse it. This is what the rebuild will use too.
        FunctionSignatureParser parser = new FunctionSignatureParser(
            currentProgram.getDataTypeManager(), null);

        int tried = 0, applied = 0;
        // parse() needs a FunctionSignature. A throwaway FunctionDefinition is
        // enough: the parser only uses it to resolve types, and the arguments
        // are read from the returned definition, never from this object.
        ghidra.program.model.data.FunctionDefinitionDataType parseHost =
            new ghidra.program.model.data.FunctionDefinitionDataType("_wmw_sig");
        for (String[] r : rows) {
            if (tried >= 6) {
                break;
            }
            Address entry = toAddr(r[0]);
            Function f = currentProgram.getFunctionManager().getFunctionAt(entry);
            if (f == null) {
                w.println("# " + r[0] + " no function at entry, skipped");
                continue;
            }
            tried++;

            String before = decompile(f);
            String[] types = r[4].split("\\|");
            List<Variable> params = new ArrayList<>();
            int intIdx = 0, vecIdx = 0;
            boolean ok = true;

            // Parse the whole list in one declaration: the parser resolves
            // commas between parameters itself, which avoids re-implementing
            // the "a type can contain a comma" problem in this probe.
            ghidra.program.model.data.ParameterDefinition[] defs = null;
            try {
                defs = parser.parse(parseHost, "void _wmw_sig(" +
                    String.join(", ", types) + ")").getArguments();
            } catch (Throwable t) {
                w.println("# " + r[0] + " parse threw: " + t);
            }
            if (defs == null) {
                w.println("# " + r[0] + " unparseable, skipped");
                continue;
            }
            if (defs.length != types.length) {
                w.println("# " + r[0] + " arity " + defs.length + " != " +
                    types.length + ", skipped");
                continue;
            }

            for (int i = 0; i < defs.length; i++) {
                DataType dt = defs[i].getDataType();
                if (dt == null) {
                    ok = false;
                    break;
                }
                // AAPCS64: integer/pointer arguments take the next x register and
                // floating-point arguments the next vector register, each class
                // with its own independent counter.
                //
                // The sub-register width matters. Passing "x0" for an `int`
                // parameter gives 8 bytes of storage for a 4-byte type, and the
                // decompiler then reports "Unknown calling convention -- yet
                // parameter storage is locked" instead of the real prototype.
                // Using "w0" for a 4-byte integer and "x0" for an 8-byte one
                // matches what the model itself would allocate.
                boolean isVec = isFloating(dt);
                int len = dt.getLength();
                int vi = Math.min(vecIdx++, 7);
                int xi = Math.min(intIdx++, 7);
                Register reg;
                if (isVec) {
                    reg = currentProgram.getRegister(
                        len == 4 ? VEC_REGS_S[vi] : VEC_REGS_D[vi]);
                } else if (len == 4) {
                    reg = currentProgram.getRegister(W_REGS[xi]);
                } else {
                    reg = currentProgram.getRegister(INT_REGS[xi]);
                }
                try {
                    params.add(new ParameterImpl("p" + i, dt,
                        new VariableStorage(currentProgram, reg), currentProgram));
                } catch (Throwable t) {
                    w.println("# " + r[0] + " storage failed on p" + i + ": " + t);
                    ok = false;
                    break;
                }
            }
            if (!ok) {
                w.println("# " + r[0] + " parse/storage failed, skipped");
                continue;
            }

            String assigned = "";
            for (Variable v : params) {
                assigned += v.getVariableStorage() + " ";
            }
            w.println("# " + r[0] + " " + r[3]);
            w.println("#   assigned: " + assigned.trim());
            w.println("#   decl-before: " + firstLine(before));

            try {
                // The calling convention has to be named, not left unknown:
                // __cdecl is what this compiler spec calls the AArch64 default,
                // and a function that still has the "unknown" placeholder model
                // makes the decompiler emit an "Unknown calling convention"
                // warning above the prototype even when the storage is correct.
                String cc = currentProgram.getCompilerSpec()
                        .getDefaultCallingConvention().getName();
                f.setCallingConvention(cc);
                f.setCustomVariableStorage(true);
                f.replaceParameters(params,
                    Function.FunctionUpdateType.CUSTOM_STORAGE, true,
                    ghidra.program.model.symbol.SourceType.USER_DEFINED);
                applied++;
                String after = decompile(f);
                w.println("#   decl-after:  " + firstLine(after));
            } catch (Throwable t) {
                w.println("#   APPLY FAILED: " + t);
            }
        }
        w.println("# tried " + tried + ", applied " + applied);
        w.close();
        println("SigStorageProbe2: done");
    }

    private boolean isFloating(DataType dt) {
        String n = dt.getName().toLowerCase();
        return n.contains("float") || n.contains("double");
    }

    private String reg(Register r) {
        return r == null ? "(absent)" : r.getName() + "@" + r.getAddress() + ":" + r.getMinimumByteSize();
    }

    private String decompile(Function f) {
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        try {
            DecompileResults res = di.decompileFunction(f, 30, monitor);
            if (res == null || !res.decompileCompleted()) {
                return "(decompile failed)";
            }
            return res.getDecompiledFunction().getC();
        } catch (Throwable t) {
            return "(error " + t + ")";
        } finally {
            di.dispose();
        }
    }

    /** The prototype line, i.e. everything up to the opening brace. */
    private String firstLine(String c) {
        if (c == null) {
            return "(null)";
        }
        int at = c.indexOf('{');
        String head = at < 0 ? c : c.substring(0, at);
        head = head.replaceAll("\\s+", " ").trim();
        return head.length() > 220 ? head.substring(0, 220) + "..." : head;
    }
}
