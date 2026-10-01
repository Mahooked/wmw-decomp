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
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
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

        decompileAndEmit(bound);
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
