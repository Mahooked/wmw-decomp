// Rebuild function boundaries from the ELF symbol table, then decompile.
//
// Why this script rebuilds instead of binding names to Ghidra's functions
// -------------------------------------------------------------------------
// The obvious pipeline is: let Ghidra's auto-analysis decide where functions
// begin, then attach an ELF symbol to each function it created. That is what
// this script used to do, and it recovered only 2,131 of 8,618 symbols (25%).
// Measurement showed the assumption behind it is backwards:
//
//   * the ELF symbol table is *clean*: 8,616 of 8,618 symbols carry a nonzero
//     st_size, every address is 4-byte aligned, and **zero** symbols start
//     inside another symbol's body. They tile 8,092 distinct addresses and
//     cover 64.7% of .text with no ambiguity.
//   * Ghidra's boundaries are the unreliable ones: of 17,375 functions it
//     found, only 102 start on an ELF symbol, while 11,547 start strictly
//     *inside* a real function -- almost all of them switch-case targets and
//     jump-table landings that Ghidra promoted into functions of their own.
//
// So the symbol table is the better oracle, and the fix is to invert the
// direction of the mapping: use the symbols to *define* the functions, and
// treat Ghidra's analysis only as a source of already-disassembled bytes and
// jump-table data.
//
// Three passes, in order:
//   1. Delete every function Ghidra created. Instructions and analysis-derived
//      data (jump tables, strings) are deliberately left alone -- they are
//      useful, it is only the function boundaries that are wrong.
//   2. For each symbol, build a function over exactly [addr, addr+st_size),
//      disassembling that range first if the optimiser never reached it.
//      Symbols sharing an address (the C1/C2 and D1/D2 alias pairs the Itanium
//      ABI emits) collapse to one function carrying every alias name.
//   3. Sweep the gaps -- the 35% of .text no symbol covers -- for call
//      targets, switch targets and relocation targets, and give each one a
//      function. Those keep Ghidra's name, or land in _unsymbolized/.
//
// Output: one .cpp per class, grouped by namespace, plus a function index.
//
// @category WMW

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;

import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.cmd.function.DeleteFunctionCmd;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.address.AddressSetView;
import ghidra.program.model.data.ArrayDataType;
import ghidra.program.model.data.DataType;
import ghidra.program.model.data.DataTypeConflictHandler;
import ghidra.program.model.data.DataTypeManager;
import ghidra.program.model.data.DoubleDataType;
import ghidra.program.model.data.FloatDataType;
import ghidra.program.model.data.IntegerDataType;
import ghidra.program.model.data.LongDataType;
import ghidra.program.model.data.ShortDataType;
import ghidra.program.model.data.SignedCharDataType;
import ghidra.program.model.data.Structure;
import ghidra.program.model.data.StructureDataType;
import ghidra.program.model.data.UnsignedCharDataType;
import ghidra.program.model.data.UnsignedIntegerDataType;
import ghidra.program.model.data.UnsignedLongDataType;
import ghidra.program.model.data.UnsignedShortDataType;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.listing.ParameterImpl;
import ghidra.program.model.listing.Variable;
import ghidra.program.model.listing.VariableStorage;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.reloc.Relocation;
import ghidra.program.model.symbol.Namespace;
import ghidra.program.model.symbol.SourceType;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolTable;

public class DecompileAll extends GhidraScript {

    // ---- configuration (overridable from the launch script) --------------
    private String nameMapPath = "C:/AIC/wmw-decomp/out/symbols/functions.tsv";
    private String outRoot = "C:/AIC/wmw-decomp/out/src";
    private int timeoutSec = 180;
    /** Smoke-test escape hatch: 0 means "decompile everything". */
    private int maxFunctions = 0;
    /** "symbol" (default) rebuilds boundaries from the ELF table; "ghidra"
     *  keeps Ghidra's own boundaries and binds names to them, for A/B runs. */
    private String mode = "symbol";
    /** Prototype table produced by tools/sigs.py; empty disables signature
     *  application entirely. */
    private String sigPath = "C:/AIC/wmw-decomp/out/symbols/signatures.tsv";
    /** Apply recovered parameter types + explicit AArch64 storage. */
    private boolean applySigs = true;
    /** Directory holding layouts.tsv and fields.tsv from tools/layout.py.
     *  Empty, or a directory without them, skips structure import. */
    private String typesDir = "C:/AIC/wmw-decomp/out/types";
    /** Import recovered field layouts, replacing the opaque placeholders. */
    private boolean applyLayouts = true;

    // ---- AAPCS64 parameter storage ---------------------------------------
    // Ghidra's own model cannot be asked for this: calling
    // PrototypeModel.getStorageLocations with two uints returns the *same*
    // register twice, and the functions this script builds from ELF symbol
    // extents have no parameters at all, so the decompiler never allocates
    // storage for itself. That is why an earlier attempt at applying recovered
    // signatures produced "parameter storage is locked" warnings and corrupted
    // return types: there was nothing valid to write into.
    //
    // AAPCS64 is simple enough to allocate directly. Integer and pointer
    // arguments take x0..x7 in order; floating-point arguments take the vector
    // file s0..s7 (float) or d0..d7 (double) in order, with an independent
    // counter. A 4-byte integer uses the w view of the register, because
    // handing the decompiler 8 bytes of storage for a 4-byte type makes it
    // report an unknown calling convention instead of the real prototype.
    private static final String[] X_REGS = {
        "x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7" };
    private static final String[] W_REGS = {
        "w0", "w1", "w2", "w3", "w4", "w5", "w6", "w7" };
    private static final String[] S_REGS = {
        "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7" };
    private static final String[] D_REGS = {
        "d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7" };

    /** A recovered prototype: exact parameter types, '|'-separated. */
    private static final class Sig {
        final String address;
        final String name;
        final String[] params;
        Sig(String address, String name, String[] params) {
            this.address = address;
            this.name = name;
            this.params = params;
        }
    }

    private static final Pattern RE_MEMBER =
        Pattern.compile("^([A-Za-z_][A-Za-z0-9_]*)\\s*(\\([\\s\\S]*)?$");

    /** One ELF STT_FUNC symbol. Several can share an address (C1/C2, D1/D2). */
    private static final class Sym {
        long size;
        String mangled;
        String demangled;

        Sym(long size, String mangled, String demangled) {
            this.size = size;
            this.mangled = mangled;
            this.demangled = demangled;
        }
    }

    /** Why a symbol ended up without its own function. */
    private static final String REASON_NO_BYTES = "no-disassembly";
    private static final String REASON_CREATE_FAILED = "create-failed";
    private static final String REASON_ZERO_SIZE = "zero-size";

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length > 0) nameMapPath = args[0];
        if (args.length > 1) outRoot = args[1];
        if (args.length > 2) timeoutSec = Integer.parseInt(args[2]);
        if (args.length > 3) maxFunctions = Integer.parseInt(args[3]);
        if (args.length > 4) mode = args[4];
        if (args.length > 5) sigPath = args[5];
        if (args.length > 6) applySigs = !args[6].equals("nosig");
        if (args.length > 7) typesDir = args[7];
        if (args.length > 8) applyLayouts = !args[8].equals("nolayout");

        // addr -> every symbol at that address. Sorted so the pass order is
        // address order, which keeps the disassembly cache coherent.
        TreeMap<Long, List<Sym>> nameMap = loadNameMap(nameMapPath);
        println("DecompileAll: loaded " + countSymbols(nameMap) + " symbols over "
            + nameMap.size() + " addresses from " + nameMapPath);
        println("DecompileAll: mode=" + mode);

        AddressSet execSet = executableSet();
        println("DecompileAll: executable blocks " + execSet);

        if (!addressSpacesAgree(nameMap, execSet)) {
            printerr("DecompileAll: REFUSING TO RUN -- Ghidra's address space does not "
                + "match the ELF symbol table.");
            printerr("DecompileAll: the symbols are in ELF vaddr space; this program's "
                + "executable blocks are not. Functions would be built at the right "
                + "addresses over the wrong bytes.");
            printerr("DecompileAll: re-import with -loader ElfLoader -loader-imagebase 0x0.");
            return;
        }

        if (mode.equals("symbol")) {
            rebuildFromSymbols(nameMap, execSet);
        }

        Map<Long, List<Sym>> bound = mode.equals("symbol")
            ? bindSymbols(nameMap, execSet)
            : bindNearestPreceding(nameMap);

        if (applySigs) {
            applySignatures(bound);
        }

        decompileAndEmit(bound);
    }

    // ---- pass 3: recovered parameter types + explicit AArch64 storage -----

    /**
     * Give every function with a recovered prototype its exact parameter types,
     * placed at explicitly computed AArch64 storage.
     *
     * <p>The return type is deliberately left alone: the Itanium ABI does not
     * encode it, so anything written there would be a guess. Ghidra's own
     * inference is kept, which is the honest option.
     *
     * <p>Conservative by construction. A prototype is only applied when every
     * parameter resolves to a real DataType and fits a register; aggregates
     * passed by value, variadics and anything the parser rejects are skipped
     * rather than approximated, because a plausible-but-wrong signature is worse
     * than none -- it mis-attributes every reference in the body.
     */
    private void applySignatures(Map<Long, List<Sym>> bound) throws IOException {
        Map<Long, Sig> sigs = loadSignatures(sigPath);
        if (sigs.isEmpty()) {
            println("DecompileAll: no signatures at " + sigPath + ", skipping");
            return;
        }
        println("DecompileAll: loaded " + sigs.size() + " prototypes from " + sigPath);

        createProjectClassTypes(sigs);

        if (applyLayouts) {
            applyRecoveredLayouts();
        }

        FunctionManager fm = currentProgram.getFunctionManager();
        ghidra.app.util.parser.FunctionSignatureParser parser =
            new ghidra.app.util.parser.FunctionSignatureParser(
                currentProgram.getDataTypeManager(), null);
        // The parser needs a FunctionSignature to hang the parsed types off and
        // only reads back the types, so a throwaway definition is enough.
        ghidra.program.model.data.FunctionDefinitionDataType parseHost =
            new ghidra.program.model.data.FunctionDefinitionDataType("_wmw_sig");

        String ccName = currentProgram.getCompilerSpec()
            .getDefaultCallingConvention().getName();

        int applied = 0, unparsed = 0, noFunction = 0, overEight = 0, threw = 0;
        List<String> why = new ArrayList<>();
        PrintWriter tsv = openWriter("_signatures.tsv",
            "#\taddress\tname\tparams\tstatus\tdetail");

        for (Map.Entry<Long, Sig> e : sigs.entrySet()) {
            long addr = e.getKey();
            Sig s = e.getValue();
            if (s.params.length == 0) {
                continue;
            }
            List<Sym> syms = bound.get(addr);
            Function f = fm.getFunctionAt(toAddr(addr));
            if (f == null && syms != null && !syms.isEmpty()) {
                f = fm.getFunctionContaining(toAddr(addr));
                if (f != null) {
                    f = fm.getFunctionAt(f.getEntryPoint());
                }
            }
            if (f == null) {
                noFunction++;
                tsv.println(hex(addr) + "\t" + s.name + "\t" +
                    String.join("|", s.params) + "\tno-function\t");
                continue;
            }

            ghidra.program.model.data.ParameterDefinition[] defs;
            try {
                defs = parser.parse(parseHost, "void _wmw_sig(" +
                    String.join(", ", s.params) + ")").getArguments();
            } catch (Throwable t) {
                unparsed++;
                if (why.size() < 8) {
                    why.add(s.name + "   [" + t.getMessage() + "]");
                }
                tsv.println(hex(addr) + "\t" + s.name + "\t" +
                    String.join("|", s.params) + "\tunparseable\t" + t.getMessage());
                continue;
            }
            // A short parse would silently shift every later parameter.
            if (defs.length != s.params.length) {
                unparsed++;
                tsv.println(hex(addr) + "\t" + s.name + "\t" +
                    String.join("|", s.params) + "\tarity\t" +
                    defs.length + " of " + s.params.length);
                continue;
            }

            // Allocate AAPCS64 storage, declining anything that does not fit a
            // register. Nine or more integer (or vector) arguments spill to the
            // stack, which needs the frame size and is out of scope here.
            List<Variable> params = new ArrayList<>();
            int intIdx = 0, vecIdx = 0;
            boolean ok = true;
            StringBuilder storage = new StringBuilder();
            for (int i = 0; i < defs.length; i++) {
                DataType dt = defs[i].getDataType();
                if (dt == null || dt.isZeroLength()) {
                    ok = false;
                    break;
                }
                int len = dt.getLength();
                Register reg;
                if (isFloating(dt)) {
                    if (vecIdx >= 8) {
                        ok = false;
                        break;
                    }
                    reg = currentProgram.getRegister(
                        len == 4 ? S_REGS[vecIdx++] : D_REGS[vecIdx++]);
                } else {
                    if (intIdx >= 8) {
                        ok = false;
                        break;
                    }
                    // 4-byte integers take the w view; 8-byte types take x.
                    reg = currentProgram.getRegister(
                        len == 4 ? W_REGS[intIdx++] : X_REGS[intIdx++]);
                }
                if (reg == null) {
                    ok = false;
                    break;
                }
                try {
                    params.add(new ParameterImpl("p" + i, dt,
                        new VariableStorage(currentProgram, reg), currentProgram));
                    storage.append(reg.getName()).append(':').append(len).append(' ');
                } catch (Throwable t) {
                    ok = false;
                    break;
                }
            }
            if (!ok) {
                overEight++;
                tsv.println(hex(addr) + "\t" + s.name + "\t" +
                    String.join("|", s.params) + "\tno-register-storage\t");
                continue;
            }

            try {
                // Name the convention explicitly. Left as the unknown
                // placeholder, the decompiler prepends an "Unknown calling
                // convention" warning to every one of these functions.
                f.setCallingConvention(ccName);
                f.setCustomVariableStorage(true);
                f.replaceParameters(params,
                    Function.FunctionUpdateType.CUSTOM_STORAGE, true,
                    SourceType.USER_DEFINED);
                applied++;
                tsv.println(hex(addr) + "\t" + s.name + "\t" +
                    String.join("|", s.params) + "\tapplied\t" +
                    storage.toString().trim());
            } catch (Throwable t) {
                threw++;
                tsv.println(hex(addr) + "\t" + s.name + "\t" +
                    String.join("|", s.params) + "\tfailed\t" + t);
            }
        }
        tsv.close();

        println("DecompileAll: parameter types + storage applied to " + applied +
            " functions (" + unparsed + " unparseable, " + overEight +
            " not register-allocatable, " + threw + " failed, " + noFunction +
            " with no function)");
        for (String s : why) {
            println("DecompileAll:   skipped: " + s);
        }
    }

    /** Read signatures.tsv, keyed by entry address. */
    private Map<Long, Sig> loadSignatures(String path) {
        Map<Long, Sig> out = new TreeMap<>();
        Path p = Paths.get(path);
        if (!Files.isRegularFile(p)) {
            return out;
        }
        try (BufferedReader r = Files.newBufferedReader(p, StandardCharsets.UTF_8)) {
            String line;
            while ((line = r.readLine()) != null) {
                if (line.startsWith("#") || line.startsWith("address")) {
                    continue;
                }
                String[] f = line.split("\t", -1);
                if (f.length < 5 || f[0].isEmpty() || f[4].isEmpty()) {
                    continue;
                }
                try {
                    long addr = Long.parseLong(f[0].trim().replaceFirst("^0x", ""), 16);
                    // Column 5 (gtype) is the same list normalised for Ghidra's
                    // C parser: const stripped, references turned into pointers.
                    // Column 4 (params) is the exact recovered type list and is
                    // only used to collect class names. Fall back to params so an
                    // older signatures.tsv still works.
                    String gtypeCol = f.length > 5 && !f[5].isEmpty() ? f[5] : f[4];
                    out.put(addr, new Sig(f[0], f.length > 3 ? f[3] : "",
                        gtypeCol.split("\\|", -1)));
                } catch (NumberFormatException ignored) {
                    // Not an address line; skip it.
                }
            }
        } catch (IOException e) {
            printerr("DecompileAll: cannot read " + path + ": " + e);
        }
        return out;
    }

    /**
     * Create a zero-length opaque structure for every project class that occurs
     * as a parameter type.
     *
     * <p>Ghidra's C parser resolves a {@code ::}-qualified type only when the
     * type's <em>name</em> contains {@code ::}; a category path alone is not
     * enough. So the name has to be the fully qualified one.
     *
     * <p>The list is derived from the parameter types themselves rather than
     * from classes.tsv, because that file is built from RTTI and so only knows
     * polymorphic classes -- {@code Walaber::Vector2}, the commonest parameter
     * type in the game at 366 uses, has no vtable and never appears in it.
     */
    private void createProjectClassTypes(Map<Long, Sig> sigs) {
        Set<String> names = new TreeSet<>();
        for (Sig s : sigs.values()) {
            for (String t : s.params) {
                String base = t.replace("*", "").replace("&", "").trim();
                // A plain qualified name only: no templates, arrays or spaces.
                if (base.matches("^[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_][A-Za-z0-9_]*)+$")) {
                    names.add(base);
                }
            }
        }
        if (names.isEmpty()) {
            return;
        }
        DataTypeManager dtm = currentProgram.getDataTypeManager();
        // KEEP_HANDLER: a re-run over a program that already has these types
        // must reuse them rather than create duplicates or overwrite them.
        DataTypeConflictHandler conflict = DataTypeConflictHandler.KEEP_HANDLER;

        int created = 0, present = 0, failed = 0;
        for (String n : names) {
            if (findByQualifiedName(dtm, n) != null) {
                present++;
                continue;
            }
            try {
                // new StructureDataType(...) only *builds* the object. Until it is
                // handed to addDataType it is a transient value that the manager
                // does not hold, and every later lookup of the name fails -- which
                // is exactly what happened when this reported 202 types created
                // and the parser then rejected 2,521 prototypes for not finding
                // them.
                //
                // A zero-length structure is deliberate: the true field layout is
                // not known yet, and a wrongly-sized one would be worse than none.
                dtm.addDataType(new StructureDataType(n, 0, dtm), conflict);
                // Count what actually landed, not what was attempted. A zero-length
                // structure is the intended result, so it must not be read as a
                // failure.
                if (findByQualifiedName(dtm, n) != null) {
                    created++;
                } else {
                    failed++;
                }
            } catch (Throwable t) {
                // A name that cannot be created is simply not resolvable; the
                // signature using it will then be skipped as unparseable.
                failed++;
            }
        }
        // Verify rather than assume: count how many are actually resolvable now,
        // since that is what decides whether the parser can use them.
        int resolvable = 0;
        for (String n : names) {
            if (findByQualifiedName(dtm, n) != null) {
                resolvable++;
            }
        }
        println("DecompileAll: " + created + " opaque class types added, " +
            present + " already present, " + failed + " failed; " + resolvable +
            " of " + names.size() + " now resolvable by name");
    }

    /**
     * Replace the opaque zero-length placeholders with the field layouts
     * recovered by tools/layout.py, so that decompiled field accesses resolve to
     * {@code this->f_0x1c} rather than a bare offset.
     *
     * <p>The structures are built directly from fields.tsv rather than parsed
     * from the generated headers. tools/check_headers.py already proves that
     * each header's declared offsets rebuild exactly under the C++ ABI, so the
     * data here is the same data with the alignment questions already settled;
     * handing it to Ghidra as components at explicit offsets keeps that
     * guarantee instead of asking a second parser to rediscover it.
     *
     * <p>Packing is switched off first. With Ghidra's default packing enabled it
     * would re-insert its own padding between components and silently shift
     * every field that the binary placed at an odd offset.
     *
     * <p>Only rows layouts.tsv marks {@code proven} are read: a name that could
     * not be shown to be a type at all has had its evidence withheld, and
     * structures with a negative or overrunning offset were rejected as
     * internally inconsistent. Neither should reach the program.
     *
     * <p>Components are named {@code f_0x<offset>} unless fieldnames.tsv supplies
     * a name for that exact class and offset, in which case the accessor-derived
     * name is used instead so the decompiled source reads in the original terms.
     * The file is optional: without it every component keeps its offset name and
     * nothing else changes.
     */
    private void applyRecoveredLayouts() throws IOException {
        Path layoutsFile = Paths.get(typesDir, "layouts.tsv");
        Path fieldsFile = Paths.get(typesDir, "fields.tsv");
        Path namesFile = Paths.get(typesDir, "fieldnames.tsv");
        if (!Files.isRegularFile(layoutsFile) || !Files.isRegularFile(fieldsFile)) {
            println("DecompileAll: no layouts at " + layoutsFile + ", keeping opaque types");
            return;
        }

        // class -> (offset, width, kind, signed), offset ascending.
        Map<String, List<String[]>> byClass = new TreeMap<>();
        int proven = 0, withheld = 0;
        for (String[] row : readTsv(layoutsFile, 9)) {
            if ("1".equals(row[8])) {
                proven++;
            } else {
                withheld++;
            }
        }
        for (String[] row : readTsv(fieldsFile, 11)) {
            byClass.computeIfAbsent(row[0], k -> new ArrayList<>())
                   .add(new String[] { row[1], row[2], row[3], row[4] });
        }

        // class -> offset -> name, from tools/fieldnames.py. Only names for
        // offsets that actually have a field are used; the rest cannot be placed.
        Map<String, Map<Integer, String>> namesByClass = new TreeMap<>();
        int nameRows = 0;
        if (Files.isRegularFile(namesFile)) {
            for (String[] row : readTsv(namesFile, 3)) {
                try {
                    namesByClass.computeIfAbsent(row[0], k -> new HashMap<>())
                               .put(Integer.valueOf(row[1]), row[2]);
                    nameRows++;
                } catch (NumberFormatException e) {
                    // A name row without a usable offset cannot address a field.
                }
            }
        }

        DataTypeManager dtm = currentProgram.getDataTypeManager();
        DataTypeConflictHandler conflict = DataTypeConflictHandler.KEEP_HANDLER;
        int built = 0, replaced = 0, skipped = 0, noFields = 0, failed = 0;
        int components = 0, named = 0;

        for (Map.Entry<String, List<String[]>> e : byClass.entrySet()) {
            String name = e.getKey();
            List<String[]> rows = e.getValue();
            if (rows.isEmpty()) {
                noFields++;
                continue;
            }
            Integer size = recoveredSize(layoutsFile, name);
            if (size == null) {
                skipped++;
                continue;
            }
            Map<Integer, String> forClass = namesByClass.get(name);
            // Unconditional: a class with no recovered names must see an empty
            // map, not the previous class's, or it inherits names by offset
            // collision and gets fields named after unrelated members.
            Map<Integer, String> classNames =
                forClass == null ? Collections.<Integer, String>emptyMap() : forClass;
            try {
                DataType existing = findByQualifiedName(dtm, name);
                // Populate the existing structure in place rather than swapping in
                // a new DataType. replaceDataType() was tried first and is wrong
                // here: the replacement is an unmanaged StructureDataType carrying
                // the same name, and forcing the swap left `Walaber::Color` no
                // longer resolvable by name, so every later prototype mentioning it
                // failed to parse -- 1,401 signatures had applied before this ran and
                // all of them silently degraded to `byte *` on the next pass.
                // Editing the placeholder keeps its identity, so the pointers
                // already handed out by applied signatures stay valid.
                Structure s;
                boolean isNew = existing == null || !(existing instanceof Structure);
                if (isNew) {
                    s = new StructureDataType(name, 0, dtm);
                } else {
                    s = (Structure) existing;
                    // A re-run must not stack a second copy of every component.
                    while (s.getNumComponents() > 0) {
                        s.delete(0);
                    }
                    s.setLength(0);
                }
                // Offsets come from the binary and are authoritative; Ghidra must
                // not second-guess them with its own packing rules.
                s.setPackingEnabled(false);

                int placed = 0;
                for (String[] f : rows) {
                    int off = Integer.parseInt(f[0]);
                    int width = Integer.parseInt(f[1]);
                    DataType cdt = componentType(dtm, f[2], f[3], width);
                    if (cdt == null) {
                        continue;
                    }
                    // insertAtOffset rather than add(), so a field the binary
                    // placed before the natural alignment of its type still
                    // lands where the binary addressed it.
                    String fieldName = classNames.get(off);
                    if (fieldName == null) {
                        fieldName = "f_0x" + Integer.toHexString(off);
                    } else {
                        named++;
                    }
                    s.insertAtOffset(off, cdt, width, fieldName, null);
                    placed++;
                }
                if (placed == 0) {
                    failed++;
                    continue;
                }
                // A structure's length in Ghidra is the end of its last
                // component, so without explicit tail padding a class whose
                // recovered sizeof is rounded past its final field -- Vector2 is
                // 8 bytes of two floats, but a class of one float at offset 0
                // with sizeof 8 -- would measure short and mis-decompile every
                // allocation of it. The recovered size, not the last field, is
                // what the binary allocates.
                if (size > s.getLength()) {
                    s.add(UnsignedCharDataType.dataType, (int) (size - s.getLength()),
                        "_tail", "trailing padding to the recovered sizeof");
                }
                s.setDescription("recovered layout, " + placed + " fields, size " + size);
                components += placed;

                if (isNew) {
                    dtm.addDataType(s, conflict);
                    built++;
                } else {
                    replaced++;
                }
            } catch (Throwable t) {
                failed++;
                println("DecompileAll: layout for " + name + " rejected: " + t);
            }
        }

        // Prove the import landed rather than counting attempts: a structure's
        // length is its recovered sizeof only if the offsets were accepted.
        int correct = 0, wrongSize = 0, lost = 0;
        List<String> wrong = new ArrayList<>();
        for (Map.Entry<String, List<String[]>> e : byClass.entrySet()) {
            Integer size = recoveredSize(layoutsFile, e.getKey());
            if (size == null) {
                // layout.py withheld this one, so its opaque placeholder is
                // still the right thing to have and there is nothing to compare.
                continue;
            }
            DataType dt = findByQualifiedName(dtm, e.getKey());
            if (!(dt instanceof Structure)) {
                // The failure that motivated this check: the type stopped being
                // resolvable by name, so every prototype using it stopped parsing
                // and silently degraded. Counted separately because it is worse
                // than a wrong size.
                lost++;
                wrong.add(e.getKey() + " (NO LONGER RESOLVABLE)");
                continue;
            }
            if (dt.getLength() == size.longValue()) {
                correct++;
            } else {
                wrongSize++;
                wrong.add(e.getKey() + " (recovered " + size + ", Ghidra " +
                    dt.getLength() + ")");
            }
        }
        println("DecompileAll: layouts -- " + built + " added, " + replaced +
            " replaced, " + noFields + " empty, " + skipped + " not proven, " +
            failed + " failed; " + components + " field components, " + named +
            " of them named from accessors (" + nameRows + " names offered)");
        println("DecompileAll: " + proven + " proven layouts, " + withheld +
            " withheld; " + correct + " structures now measure their recovered " +
            "sizeof, " + wrongSize + " do not, " + lost + " lost their name");
        for (String w : wrong) {
            println("DecompileAll:   layout problem: " + w);
        }
        if (lost > 0) {
            // Continuing would apply signatures that cannot resolve these types,
            // which is worse than stopping: the run reports success while quietly
            // replacing every `Walaber::Color *` with `byte *`.
            throw new IllegalStateException(lost + " recovered layouts stopped being "
                + "resolvable by name; refusing to apply prototypes that use them");
        }
    }

    /** Read a tab-separated file, skipping the leading {@code #} header. */
    private List<String[]> readTsv(Path path, int columns) throws IOException {
        List<String[]> out = new ArrayList<>();
        for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            if (line.isEmpty() || line.startsWith("#")) {
                continue;
            }
            String[] f = line.split("\t", -1);
            if (f.length >= columns) {
                out.add(f);
            }
        }
        return out;
    }

    /** The recovered sizeof for one class, or null if it was not proven. */
    private Integer recoveredSize(Path layoutsFile, String name) throws IOException {
        for (String[] row : readTsv(layoutsFile, 9)) {
            if (row[0].equals(name) && "1".equals(row[8])) {
                return Integer.valueOf(row[1]);
            }
        }
        return null;
    }

    /**
     * Map a recovered field kind and width onto a Ghidra data type.
     *
     * <p>A field recovered at 16 bytes is two consecutive 64-bit halves with no
     * evidence separating them, so it is emitted as an array rather than guessed
     * at as a struct or a single 128-bit value.
     */
    private DataType componentType(DataTypeManager dtm, String kind, String signed, int width) {
        if (width <= 0) {
            return null;
        }
        if (width == 16) {
            return new ArrayDataType(UnsignedLongDataType.dataType, 2, 8);
        }
        if (width != 1 && width != 2 && width != 4 && width != 8) {
            return null;
        }
        if ("float".equals(kind) && width == 4) {
            return FloatDataType.dataType;
        }
        if ("float".equals(kind) && width == 8) {
            return DoubleDataType.dataType;
        }
        boolean s = "1".equals(signed);
        switch (width) {
            case 1: return s ? SignedCharDataType.dataType : UnsignedCharDataType.dataType;
            case 2: return s ? ShortDataType.dataType : UnsignedShortDataType.dataType;
            case 4: return s ? IntegerDataType.dataType : UnsignedIntegerDataType.dataType;
            default: return s ? LongDataType.dataType : UnsignedLongDataType.dataType;
        }
    }

    /**
     * Look up a {@code ::}-qualified type by name.
     *
     * <p>The leading slash is load-bearing. A structure created as
     * {@code new StructureDataType("Walaber::Vector2", 0, dtm)} is stored at path
     * {@code /Walaber::Vector2}, and {@code getDataType("Walaber::Vector2")}
     * returns null while {@code getDataType("/Walaber::Vector2")} succeeds. That
     * asymmetry is silent -- it just looks like the type was never created.
     */
    private DataType findByQualifiedName(DataTypeManager dtm, String n) {
        DataType dt = dtm.getDataType(n);
        if (dt != null) {
            return dt;
        }
        if (!n.startsWith("/")) {
            return dtm.getDataType("/" + n);
        }
        return null;
    }

    private boolean isFloating(DataType dt) {
        String n = dt.getName().toLowerCase();
        return n.contains("float") || n.contains("double");
    }

    // ---- pass 1 + 2: rebuild boundaries from the symbol table -----------

    private void rebuildFromSymbols(TreeMap<Long, List<Sym>> nameMap, AddressSet execSet) {
        FunctionManager fm = currentProgram.getFunctionManager();

        // Ghidra's boundaries are wrong for this binary (only 102 of its 17,375
        // functions start on a symbol), so every one of them has to go before
        // the symbol-derived ones are laid down. Instructions and analysis
        // data stay: that is the part of the auto-analysis worth keeping.
        int removed = 0;
        List<Address> victims = new ArrayList<Address>();
        FunctionIterator fit = fm.getFunctions(true);
        while (fit.hasNext()) {
            victims.add(fit.next().getEntryPoint());
        }
        for (Address a : victims) {
            if (fm.removeFunction(a)) {
                removed++;
            }
        }
        println("DecompileAll: removed " + removed + " auto-analysis functions");

        int created = 0, disassembled = 0, noBytes = 0, createFail = 0, zeroSize = 0;
        long t0 = System.currentTimeMillis();
        int done = 0;
        for (Map.Entry<Long, List<Sym>> e : nameMap.entrySet()) {
            if (monitor.isCancelled()) {
                println("DecompileAll: cancelled during rebuild");
                break;
            }
            long addr = e.getKey();
            List<Sym> aliases = e.getValue();
            // Aliases at one address share a body; take the widest st_size.
            long size = 0;
            for (Sym s : aliases) {
                size = Math.max(size, s.size);
            }
            if (size == 0) {
                zeroSize++;
                continue;
            }
            Address entry = toAddr(addr);
            Address end = entry.add(size - 1);
            AddressSet range = new AddressSet(entry, end);
            if (!execSet.intersects(range)) {
                continue;
            }

            Listing listing = currentProgram.getListing();
            // Always (re)disassemble the whole declared range rather than only
            // when the entry address is empty. Analysis often stopped partway
            // through a function, and a partial body means a truncated
            // decompilation; asking for the full st_size with followFlow keeps
            // switch targets inside the function and stops at the range edge.
            DisassembleCommand dc = new DisassembleCommand(entry, range, true);
            dc.applyTo(currentProgram, monitor);
            if (listing.getInstructionAt(entry) != null) {
                disassembled++;
            }

            AddressSet body = disassembledBody(range);
            if (body.isEmpty()) {
                noBytes++;
                continue;
            }
            if (createFunction(null, entry, body) != null) {
                created++;
            } else {
                createFail++;
            }

            done++;
            if (done % 1000 == 0) {
                long dt = (System.currentTimeMillis() - t0) / 1000;
                println("DecompileAll: rebuild " + done + "/" + nameMap.size() + " " + dt + "s");
            }
        }
        println("DecompileAll: rebuild done: " + created + " functions from symbols, "
            + disassembled + " ranges disassembled, " + noBytes + " " + REASON_NO_BYTES
            + ", " + createFail + " " + REASON_CREATE_FAILED + ", " + zeroSize + " "
            + REASON_ZERO_SIZE + ", " + (System.currentTimeMillis() - t0) / 1000 + "s");

        int gapFns = sweepGaps(nameMap, execSet);
        println("DecompileAll: gap sweep added " + gapFns + " functions in code no symbol covers");
    }

    /** Instruction bytes actually present inside a range, as a body set. */
    private AddressSet disassembledBody(AddressSetView range) {
        AddressSet body = new AddressSet();
        InstructionIterator ii = currentProgram.getListing().getInstructions(range, true);
        while (ii.hasNext()) {
            Instruction in = ii.next();
            body.add(in.getMinAddress(), in.getMaxAddress());
        }
        return body;
    }

    // ---- pass 3: give the unsymbolised code a function too ---------------

    /**
     * 35% of .text is not covered by any symbol: alignment padding, 16-byte
     * veneer thunks, and some vendored code. Anything that is *called* still
     * deserves a function, or it will be emitted as a bare address in the
     * middle of someone else's body.
     *
     * The probe for each candidate stops at the next planned entry. Letting
     * followFlow run to the end of the executable region instead is
     * catastrophic: with a few thousand candidates it takes hours, because
     * every one of them re-walks the whole remaining text.
     */
    private int sweepGaps(Map<Long, List<Sym>> nameMap, AddressSet execSet) {
        FunctionManager fm = currentProgram.getFunctionManager();

        // Symbol bodies are already functions; nothing inside one is a gap entry.
        AddressSet symbolBodies = new AddressSet();
        for (Map.Entry<Long, List<Sym>> e : nameMap.entrySet()) {
            long size = 0;
            for (Sym s : e.getValue()) {
                size = Math.max(size, s.size);
            }
            if (size > 0) {
                symbolBodies.add(toAddr(e.getKey()), toAddr(e.getKey()).add(size - 1));
            }
        }

        TreeSet<Long> candidates = new TreeSet<Long>();
        collectCandidates(execSet, symbolBodies, candidates);
        println("DecompileAll: gap sweep found " + candidates.size()
            + " candidate entries outside symbol bodies");
        if (candidates.isEmpty()) {
            return 0;
        }

        int created = 0, noBytes = 0;
        long prev = -1;
        long[] cands = new long[candidates.size()];
        int i = 0;
        for (long a : candidates) {
            cands[i++] = a;
        }
        long t0 = System.currentTimeMillis();
        for (int k = 0; k < cands.length; k++) {
            if (monitor.isCancelled()) {
                break;
            }
            long a = cands[k];
            Address entry = toAddr(a);
            // Stop at the next planned entry, or at the end of the block.
            Address stop;
            if (k + 1 < cands.length) {
                stop = toAddr(cands[k + 1]);
            } else {
                stop = execSet.getMaxAddress();
            }
            AddressSet probe = new AddressSet(entry, stop).intersect(execSet);
            if (probe.isEmpty()) {
                continue;
            }
            DisassembleCommand dc = new DisassembleCommand(entry, probe, true);
            dc.applyTo(currentProgram, monitor);

            AddressSet body = disassembledBody(probe);
            if (body.isEmpty()) {
                noBytes++;
                continue;
            }
            if (createFunction(null, entry, body) != null) {
                created++;
            }
            if (created % 500 == 0) {
                long dt = (System.currentTimeMillis() - t0) / 1000;
                println("DecompileAll: gap sweep " + (k + 1) + "/" + cands.length
                    + " (" + created + " created) " + dt + "s");
            }
        }
        println("DecompileAll: gap sweep done: " + created + " created, " + noBytes
            + " " + REASON_NO_BYTES + ", " + (System.currentTimeMillis() - t0) / 1000 + "s");
        return created;
    }

    /** Genuine function entries outside any symbol body: things that are
     *  *called* (a call operand is always a new function), plus GOT-relative
     *  relocation targets, which is how vtables and function-pointer tables
     *  point at code.
     *
     *  Branch targets are deliberately excluded. A conditional branch, a loop
     *  header and every switch case inside a function are flows too, and
     *  treating them as entries shatters one function into dozens of stubs --
     *  the first version of this sweep did exactly that and manufactured
     *  28,939 nonsense functions. */
    private void collectCandidates(AddressSet execSet, AddressSet symbolBodies,
            TreeSet<Long> out) {
        Listing listing = currentProgram.getListing();
        InstructionIterator ii = listing.getInstructions(execSet, true);
        while (ii.hasNext()) {
            Instruction in = ii.next();
            if (symbolBodies.contains(in.getAddress())) {
                continue;
            }
            boolean isCall = false;
            for (ghidra.program.model.symbol.Reference r : in.getReferencesFrom()) {
                if (r.getReferenceType().isCall()) {
                    isCall = true;
                    break;
                }
            }
            if (!isCall) {
                continue;
            }
            for (Address f : in.getFlows()) {
                if (f != null && execSet.contains(f) && !symbolBodies.contains(f)) {
                    out.add(f.getOffset());
                }
            }
        }
        Iterator<Relocation> rels = currentProgram.getRelocationTable().getRelocations();
        while (rels.hasNext()) {
            Address to = rels.next().getAddress();
            if (to != null && execSet.contains(to) && !symbolBodies.contains(to)) {
                out.add(to.getOffset());
            }
        }
    }

    /** createFunction that tolerates an existing body instead of throwing. */
    private Function createFunction(String name, Address entry, AddressSetView body) {
        try {
            if (currentProgram.getFunctionManager().getFunctionAt(entry) != null) {
                return currentProgram.getFunctionManager().getFunctionAt(entry);
            }
            CreateFunctionCmd cmd =
                new CreateFunctionCmd(name, entry, body, SourceType.USER_DEFINED);
            if (!cmd.applyTo(currentProgram, monitor)) {
                return null;
            }
            return cmd.getFunction();
        } catch (Throwable t) {
            return null;
        }
    }

    // ---- binding: which names go on which functions ----------------------

    /**
     * After a symbol-driven rebuild this is close to a lookup: a symbol's
     * function is the one at its own address. Symbols whose function could not
     * be built fall back to the nearest preceding one, and everything that
     * still has no ELF symbol behind it is inventoried in _unsymbolized.tsv.
     */
    private Map<Long, List<Sym>> bindSymbols(TreeMap<Long, List<Sym>> nameMap, AddressSet execSet) {
        FunctionManager fm = currentProgram.getFunctionManager();
        Map<Long, List<Sym>> bound = new TreeMap<Long, List<Sym>>();
        PrintWriter al = openWriter("_unclaimed.tsv",
            "#\taddress\tmangled\tdemangled\treason");
        Map<Long, String> unsymbolized = new TreeMap<Long, String>();

        long[] symAddr = new long[nameMap.size()];
        int i = 0;
        for (Long a : nameMap.keySet()) {
            symAddr[i++] = a;
        }

        int exact = 0, nearest = 0, missing = 0;
        FunctionIterator it = fm.getFunctions(true);
        while (it.hasNext()) {
            if (monitor.isCancelled()) {
                break;
            }
            Function f = it.next();
            long entry = f.getEntryPoint().getOffset();
            List<Sym> pair = nameMap.get(entry);
            if (pair != null) {
                bound.put(entry, pair);
                exact++;
                continue;
            }
            int j = Arrays.binarySearch(symAddr, entry);
            int k = (j >= 0) ? j : -j - 2;
            if (k >= 0 && entry - symAddr[k] <= 0x200L) {
                bound.put(entry, nameMap.get(symAddr[k]));
                nearest++;
            } else {
                unsymbolized.put(entry, f.getName());
            }
        }

        // Anything the rebuild could not place, with a real reason this time.
        // The old build reported "no-ghidra-function" for all 5,961 rows
        // because it tested membership in a map that was a copy of the one it
        // was iterating, so the "interior" branch was unreachable.
        for (Map.Entry<Long, List<Sym>> e : nameMap.entrySet()) {
            long a = e.getKey();
            if (containsAddr(bound, a)) {
                continue;
            }
            long size = 0;
            for (Sym s : e.getValue()) {
                size = Math.max(size, s.size);
            }
            String reason = size == 0 ? REASON_ZERO_SIZE
                : fm.getFunctionContaining(toAddr(a)) != null ? "absorbed"
                : REASON_NO_BYTES;
            List<Sym> v = e.getValue();
            for (Sym s : v) {
                al.println(hex(a) + "\t" + nvl(s.mangled) + "\t" + nvl(s.demangled)
                    + "\t" + reason);
            }
            missing += v.size();
        }
        al.close();

        writeUnsymbolized(unsymbolized);

        println("DecompileAll: bound " + (exact + nearest) + " functions ("
            + exact + " at their own symbol address, " + nearest
            + " by nearest preceding symbol), " + unsymbolized.size()
            + " unsymbolised, " + missing + " symbols unclaimed");
        return bound;
    }

    /** Kept for A/B comparison: trust Ghidra's boundaries, bind nearest-first. */
    private Map<Long, List<Sym>> bindNearestPreceding(TreeMap<Long, List<Sym>> nameMap) {
        FunctionManager fm = currentProgram.getFunctionManager();
        Map<Long, List<Sym>> bound = new TreeMap<Long, List<Sym>>();
        Map<Long, String> unsymbolized = new TreeMap<Long, String>();
        Set<Long> claimed = new HashSet<Long>();
        long[] symAddr = new long[nameMap.size()];
        int i = 0;
        for (Long a : nameMap.keySet()) {
            symAddr[i++] = a;
        }
        int exact = 0, nearest = 0;
        FunctionIterator it = fm.getFunctions(true);
        while (it.hasNext()) {
            Function f = it.next();
            long entry = f.getEntryPoint().getOffset();
            List<Sym> pair = nameMap.get(entry);
            long claimKey = entry;
            boolean isNear = false;
            if (pair == null) {
                int j = Arrays.binarySearch(symAddr, entry);
                int k = (j >= 0) ? j : -j - 2;
                if (k >= 0 && entry - symAddr[k] <= 0x200L && !claimed.contains(symAddr[k])) {
                    claimKey = symAddr[k];
                    pair = nameMap.get(claimKey);
                    isNear = pair != null;
                }
            }
            if (pair == null) {
                unsymbolized.put(entry, f.getName());
                continue;
            }
            claimed.add(claimKey);
            if (isNear) {
                nearest++;
            } else {
                exact++;
            }
            bound.put(entry, pair);
        }
        PrintWriter al = openWriter("_unclaimed.tsv",
            "#\taddress\tmangled\tdemangled\treason");
        for (Map.Entry<Long, List<Sym>> e : nameMap.entrySet()) {
            if (claimed.contains(e.getKey())) {
                continue;
            }
            for (Sym s : e.getValue()) {
                al.println(hex(e.getKey()) + "\t" + nvl(s.mangled) + "\t"
                    + nvl(s.demangled) + "\t" + "no-ghidra-function");
            }
        }
        al.close();
        writeUnsymbolized(unsymbolized);
        println("DecompileAll: bound " + (exact + nearest) + " functions (" + exact
            + " exact, " + nearest + " nearest-preceding), " + unsymbolized.size()
            + " unsymbolised");
        return bound;
    }

    private void writeUnsymbolized(Map<Long, String> unsymbolized) {
        PrintWriter un = openWriter("_unsymbolized.tsv", "#\taddress\tghidra_name");
        for (Map.Entry<Long, String> e : unsymbolized.entrySet()) {
            un.println(hex(e.getKey()) + "\t" + e.getValue());
        }
        un.close();
    }

    private static boolean containsAddr(Map<Long, List<Sym>> bound, long a) {
        for (Long k : bound.keySet()) {
            if (k == a) {
                return true;
            }
        }
        return false;
    }

    // ---- decompile + emit ------------------------------------------------

    private void decompileAndEmit(Map<Long, List<Sym>> bound) throws IOException {
        DecompInterface ifc = new DecompInterface();
        ifc.toggleCCode(true);
        ifc.toggleSyntaxTree(true);
        ifc.setSimplificationStyle("decompile");
        DecompileOptions opts = new DecompileOptions();
        opts.setEliminateUnreachable(true);
        ifc.setOptions(opts);
        if (!ifc.openProgram(currentProgram)) {
            printerr("DecompileAll: could not open program in decompiler");
            return;
        }

        FunctionManager fm = currentProgram.getFunctionManager();
        applyNames(bound);

        // group -> ordered function addresses
        Map<String, List<Long>> groups = new TreeMap<String, List<Long>>();
        Map<Long, Sym> chosen = new HashMap<Long, Sym>();
        int total = 0;
        for (Map.Entry<Long, List<Sym>> e : bound.entrySet()) {
            if (maxFunctions > 0 && total >= maxFunctions) {
                break;
            }
            if (fm.getFunctionAt(toAddr(e.getKey())) == null) {
                continue;
            }
            Sym primary = primary(e.getValue());
            chosen.put(e.getKey(), primary);
            String key = groupKeyFor(primary.demangled);
            List<Long> g = groups.get(key);
            if (g == null) {
                g = new ArrayList<Long>();
                groups.put(key, g);
            }
            g.add(e.getKey());
            total++;
        }

        Path root = Paths.get(outRoot);
        Files.createDirectories(root);
        PrintWriter index = new PrintWriter(
            new OutputStreamWriter(new FileOutputStream(root.resolve("_index.tsv").toFile()),
                StandardCharsets.UTF_8));
        index.println("#\tfile\taddress\tsize\tmangled\tdemangled\tstatus\taliases");

        int ok = 0, failed = 0;
        long t0 = System.currentTimeMillis();
        int done = 0;
        for (Map.Entry<String, List<Long>> e : groups.entrySet()) {
            if (monitor.isCancelled()) {
                println("DecompileAll: cancelled");
                break;
            }
            String rel = fileNameFor(e.getKey());
            Path outFile = root.resolve(rel);
            Files.createDirectories(outFile.getParent());
            PrintWriter out = new PrintWriter(
                new OutputStreamWriter(new FileOutputStream(outFile.toFile()),
                    StandardCharsets.UTF_8));
            out.println("/* " + e.getKey() + "  --  decompiled from " + currentProgram.getName()
                + " (" + currentProgram.getExecutablePath() + ") */");
            out.println("/* generated by Ghidra DecompileAll; function bodies come from the");
            out.println("   ELF symbol table in out/symbols/functions.tsv */");
            out.println();
            for (long off : e.getValue()) {
                done++;
                Sym m = chosen.get(off);
                List<Sym> aliases = bound.get(off);
                monitor.setMessage("Decompiling " + m.demangled);
                String status;
                String c = null;
                long fsize = 0;
                Function f = fm.getFunctionAt(toAddr(off));
                if (f == null) {
                    status = "fail:no-function";
                } else {
                    fsize = f.getBody().getNumAddresses();
                    try {
                        DecompileResults res = ifc.decompileFunction(f, timeoutSec, monitor);
                        if (res != null && res.getDecompiledFunction() != null) {
                            c = res.getDecompiledFunction().getC();
                            status = res.decompileCompleted() ? "ok" : "partial";
                        } else {
                            status = "fail:no-function";
                        }
                    } catch (Throwable t) {
                        status = "fail:" + t.getClass().getSimpleName();
                    }
                }
                if (c == null || c.trim().isEmpty()) {
                    failed++;
                    c = "/* decompilation failed (" + status + ") */";
                } else {
                    if (status.equals("ok")) {
                        ok++;
                    }
                }
                out.println("/* " + status + "  address " + hex(off)
                    + "  size " + fsize + " */");
                out.println("/* mangled: " + nvl(m.mangled) + " */");
                if (aliases.size() > 1) {
                    String als = aliasList(aliases, m);
                    if (!als.isEmpty()) {
                        out.println("/* also exported as: " + als + " */");
                    }
                }
                out.println("/* " + nvl(m.demangled) + " */");
                out.println(c);
                out.println();
                index.println(rel + "\t" + hex(off) + "\t" + fsize + "\t"
                    + nvl(m.mangled) + "\t" + nvl(m.demangled) + "\t" + status + "\t"
                    + (aliases.size() > 1 ? aliasList(aliases, m) : ""));
            }
            out.close();
            if (done % 200 == 0) {
                long dt = (System.currentTimeMillis() - t0) / 1000;
                println("DecompileAll: " + done + "/" + total + " (" + ok + " ok, " + failed
                    + " failed) " + dt + "s");
            }
        }
        index.close();
        long dt = (System.currentTimeMillis() - t0) / 1000;
        println("DecompileAll: DONE " + done + " functions, " + ok + " ok, " + failed
            + " failed, " + dt + "s");
        println("DecompileAll: wrote " + groups.size() + " files under " + outRoot);
        ifc.dispose();
    }

    // ---- helpers ---------------------------------------------------------

    private TreeMap<Long, List<Sym>> loadNameMap(String path) throws IOException {
        TreeMap<Long, List<Sym>> m = new TreeMap<Long, List<Sym>>();
        Path p = Paths.get(path);
        if (!Files.exists(p)) {
            println("DecompileAll: WARNING no symbol map at " + path);
            return m;
        }
        List<String> lines = Files.readAllLines(p, StandardCharsets.UTF_8);
        for (String line : lines) {
            if (line.isEmpty() || line.startsWith("#")) {
                continue;
            }
            String[] f = line.split("\t", -1);
            if (f.length < 3) {
                continue;
            }
            long addr;
            try {
                addr = Long.parseUnsignedLong(f[0].trim().replace("0x", ""), 16);
            } catch (NumberFormatException ignore) {
                continue;
            }
            long size;
            try {
                size = f.length > 1 && !f[1].isEmpty() ? Long.parseLong(f[1].trim()) : 0;
            } catch (NumberFormatException ignore) {
                size = 0;
            }
            String mangled = f[2];
            String dem = f.length > 3 && !f[3].isEmpty() ? f[3] : mangled;
            List<Sym> v = m.get(addr);
            if (v == null) {
                v = new ArrayList<Sym>();
                m.put(addr, v);
            }
            v.add(new Sym(size, mangled, dem));
        }
        return m;
    }

    private static int countSymbols(Map<Long, List<Sym>> m) {
        int n = 0;
        for (List<Sym> v : m.values()) {
            n += v.size();
        }
        return n;
    }

    /**
     * Guard against the worst possible failure mode here: a silently wrong
     * result. If Ghidra loaded the .so at a different base than the ELF vaddrs
     * (it defaults a PIE to 0x100000), then every address we take from
     * functions.tsv still lands inside *some* block, disassembly succeeds, and
     * the output looks entirely plausible while describing the wrong bytes.
     * So verify the span of the whole symbol table sits inside executable
     * memory before building anything.
     */
    private boolean addressSpacesAgree(TreeMap<Long, List<Sym>> nameMap, AddressSet execSet) {
        long lo = Long.MAX_VALUE;
        long hi = Long.MIN_VALUE;
        for (Map.Entry<Long, List<Sym>> e : nameMap.entrySet()) {
            long size = 0;
            for (Sym s : e.getValue()) {
                size = Math.max(size, s.size);
            }
            if (size == 0) {
                continue;
            }
            lo = Math.min(lo, e.getKey());
            hi = Math.max(hi, e.getKey() + size);
        }
        if (lo == Long.MAX_VALUE) {
            return true;   // nothing to check against
        }
        boolean ok = execSet.contains(toAddr(lo)) && execSet.contains(toAddr(hi - 1));
        if (!ok) {
            println("DecompileAll: symbol span 0x" + Long.toHexString(lo) + "..0x"
                + Long.toHexString(hi) + " vs executable " + execSet);
        }
        return ok;
    }

    private AddressSet executableSet() {
        // Print the block layout once: the ELF loader does not always flag the
        // leading part of .text as executable, and a symbol dropped for that
        // reason disappears without a trace.
        for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            println("DecompileAll: block " + b.getName() + " 0x" + b.getStart()
                + "..0x" + b.getEnd() + " r=" + b.isRead() + " w=" + b.isWrite()
                + " x=" + b.isExecute() + (b.isInitialized() ? "" : " (uninitialised)"));
        }
        AddressSet s = new AddressSet();
        for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            // .text/.plt are code by construction; trust the name as well as the
            // permission bit so an unflagged leading .text region is still
            // covered.
            String n = b.getName();
            if (b.isExecute() || n.equals(".text") || n.equals(".plt")
                || n.equals(".init") || n.equals(".fini")) {
                s.add(b.getStart(), b.getEnd());
            }
        }
        return s;
    }

    private PrintWriter openWriter(String name, String header) {
        try {
            Path root = Paths.get(outRoot);
            Files.createDirectories(root);
            PrintWriter w = new PrintWriter(new OutputStreamWriter(
                new FileOutputStream(root.resolve(name).toFile()), StandardCharsets.UTF_8));
            w.println(header);
            return w;
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    private static String hex(long a) {
        return "0x" + Long.toHexString(a);
    }

    private static String nvl(String s) {
        return s == null ? "" : s;
    }

    /**
     * C1/C2 and D1/D2 are the same code under two ABI-mandated names, so a
     * body gets one name and a comment listing the rest. Prefer the
     * complete-object spelling.
     */
    private static Sym primary(List<Sym> aliases) {
        Sym best = null;
        int bestRank = Integer.MAX_VALUE;
        for (Sym s : aliases) {
            int r = rank(s);
            if (r < bestRank) {
                bestRank = r;
                best = s;
            }
        }
        return best;
    }

    private static int rank(Sym s) {
        String m = s.mangled;
        if (m == null || m.isEmpty()) {
            return 50;
        }
        if (m.contains("C2E") || m.contains("D2E")) {
            return 2;   // base-object constructor/destructor alias
        }
        if (m.contains("C1E") || m.contains("D1E")) {
            return 0;
        }
        if (m.startsWith("_ZThn") || m.startsWith("_ZTv")) {
            return 3;
        }
        return 1;
    }

    private static String aliasList(List<Sym> aliases, Sym primary) {
        StringBuilder sb = new StringBuilder();
        for (Sym s : aliases) {
            if (s == primary) {
                continue;
            }
            // C1 and C2 are the same code under two ABI-mandated names and
            // usually demangle to the identical string. Listing it tells the
            // reader nothing, so only record aliases that actually differ.
            if (nvl(s.demangled).equals(nvl(primary.demangled))) {
                continue;
            }
            if (sb.length() > 0) {
                sb.append(" | ");
            }
            sb.append(nvl(s.mangled));
            sb.append(" = ");
            sb.append(nvl(s.demangled));
        }
        return sb.toString();
    }

    /** Bucket a demangled name into an output group (usually a class). */
    private String groupKeyFor(String dem) {
        if (dem == null) {
            return "_misc";
        }
        int paren = indexOfTopLevel(dem, '(');
        String head = (paren >= 0 ? dem.substring(0, paren) : dem).trim();
        int last = head.lastIndexOf("::");
        if (last >= 0) {
            String owner = head.substring(0, last);
            return owner.isEmpty() ? "_misc" : owner;
        }
        return "_globals";
    }

    private int indexOfTopLevel(String s, char ch) {
        int ang = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '<') {
                ang++;
            } else if (c == '>') {
                ang = Math.max(0, ang - 1);
            } else if (c == ch && ang == 0) {
                return i;
            }
        }
        return -1;
    }

    private String fileNameFor(String group) {
        if (group.length() > 90 || group.indexOf('<') >= 0) {
            String h = Integer.toHexString(group.hashCode());
            String tail = group.replaceAll("[^A-Za-z0-9_]", "_");
            if (tail.length() > 40) {
                tail = tail.substring(0, 40);
            }
            return "_tmpl/" + tail + "_" + h + ".cpp";
        }
        String s = group.replace("::", "/").replaceAll("[^A-Za-z0-9_/.-]", "_");
        while (s.contains("//")) {
            s = s.replace("//", "/");
        }
        if (s.startsWith("/")) {
            s = s.substring(1);
        }
        if (s.isEmpty()) {
            s = "_misc";
        }
        return s + ".cpp";
    }

    /** Move each function into a Ghidra namespace matching its C++ scope. */
    private void applyNames(Map<Long, List<Sym>> bound) {
        SymbolTable st = currentProgram.getSymbolTable();
        FunctionManager fm = currentProgram.getFunctionManager();
        int renamed = 0, nsFail = 0, skipped = 0;
        for (Map.Entry<Long, List<Sym>> e : bound.entrySet()) {
            long off = e.getKey();
            Sym m = primary(e.getValue());
            String dem = m.demangled;
            String mangled = m.mangled;
            if (mangled == null || mangled.isEmpty() || dem.indexOf('<') >= 0) {
                skipped++;
                continue;
            }
            int paren = indexOfTopLevel(dem, '(');
            String head = (paren >= 0 ? dem.substring(0, paren) : dem).trim();
            int last = head.lastIndexOf("::");
            if (last < 0) {
                continue;
            }
            String owner = head.substring(0, last);
            String member = head.substring(last + 2).trim().replaceAll("\\s+", "_");
            if (member.isEmpty()) {
                continue;
            }
            Function f = fm.getFunctionAt(toAddr(off));
            if (f == null) {
                continue;
            }
            try {
                Namespace ns = ensureNamespace(null, owner);
                if (ns == null) {
                    nsFail++;
                    continue;
                }
                Symbol sym = st.getPrimarySymbol(f.getEntryPoint());
                if (sym != null) {
                    sym.setName(member, SourceType.USER_DEFINED);
                    try {
                        f.setParentNamespace(ns);
                    } catch (Throwable ignore) {
                        // older APIs only allow the symbol to carry the namespace
                    }
                    sym.setNamespace(ns);
                    renamed++;
                }
            } catch (Throwable t) {
                nsFail++;
            }
        }
        println("DecompileAll: renamed " + renamed + " functions (" + nsFail
            + " namespace issues, " + skipped + " left to GNU demangler)");
    }

    /** Create nested Ghidra namespaces for a '::'-separated C++ scope. */
    private Namespace ensureNamespace(Namespace parent, String scope) {
        SymbolTable st = currentProgram.getSymbolTable();
        Namespace cur = parent != null ? parent : globalNamespace();
        for (String part : scope.split("::")) {
            part = part.trim().replaceAll("[^A-Za-z0-9_]", "_");
            if (part.isEmpty()) {
                continue;
            }
            Namespace next = null;
            try {
                next = st.getNamespace(part, cur);
            } catch (Throwable ignore) {
                // fall through to create
            }
            if (next == null) {
                try {
                    next = st.getOrCreateNameSpace(cur, part, SourceType.IMPORTED);
                } catch (Throwable t) {
                    return null;
                }
            }
            if (next == null) {
                return null;
            }
            cur = next;
        }
        return cur;
    }

    private Namespace globalNamespace() {
        return currentProgram.getGlobalNamespace();
    }
}
