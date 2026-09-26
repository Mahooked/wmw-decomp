// Decompile every function in the current program and write readable C++.
//
// Naming: this binary is only partially stripped, so the project supplies an
// address -> demangled-name map (out/symbols/functions.tsv, produced by our own
// Itanium demangler).  Each function is placed into a Ghidra namespace mirroring
// its C++ scope and given its bare member name, which reproduces the demangled
// spelling in the emitted C without pushing punctuation through Ghidra's symbol
// validator.
//
// Output: one .cpp per class, grouped by namespace, plus a function index.
//
// @category WMW
// @keybinding
// @menupath
// @toolbar

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;

import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSetView;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.FunctionManager;
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

    private static final Pattern RE_MEMBER =
        Pattern.compile("^([A-Za-z_][A-Za-z0-9_]*)\\s*(\\([\\s\\S]*)?$");

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length > 0) nameMapPath = args[0];
        if (args.length > 1) outRoot = args[1];
        if (args.length > 2) timeoutSec = Integer.parseInt(args[2]);
        if (args.length > 3) maxFunctions = Integer.parseInt(args[3]);

        Map<Long, String[]> nameMap = loadNameMap(nameMapPath);
        monitor.setMessage("DecompileAll: loaded " + nameMap.size() + " symbol names");
        println("DecompileAll: loaded " + nameMap.size() + " symbol names from " + nameMapPath);

        DecompInterface ifc = new DecompInterface();
        ifc.toggleCCode(true);
        ifc.toggleSyntaxTree(true);
        ifc.setSimplificationStyle("decompile");
        DecompileOptions opts = new DecompileOptions();
        // Keep the decompiler faithful: this is a decompilation project, not a
        // cleanup pass, so the caller-supplied names stay readable.
        opts.setEliminateUnreachable(true);
        ifc.setOptions(opts);
        if (!ifc.openProgram(currentProgram)) {
            printerr("DecompileAll: could not open program in decompiler");
            return;
        }

        Path root = Paths.get(outRoot);
        Files.createDirectories(root);
        PrintWriter index = new PrintWriter(
            new OutputStreamWriter(new FileOutputStream(root.resolve("_index.tsv").toFile()),
                StandardCharsets.UTF_8));
        index.println("#\tfile\taddress\tsize\tmangled\tdemangled\tstatus");

        // Group by owning scope so each class lands in one file.
        //
        // We iterate *Ghidra's* function list, because only its analysis has
        // followed control flow well enough to give each function a real body.
        // Driving from the symbol table instead (creating a Function per symbol)
        // yields 1-instruction stubs that decompile to nonsense, because the
        // addresses were never disassembled.
        //
        // Naming is the other half of the problem: Ghidra names functions from
        // call targets, so its boundaries only coincide with the ELF symbol
        // table at 102 of 17,375 addresses.  So we bind names by nearest
        // preceding symbol instead of exact address match, claiming each symbol
        // at most once so two Ghidra functions can never take the same name.
        Map<String, List<Long>> groups = new TreeMap<String, List<Long>>();
        Map<Long, String[]> meta = new HashMap<Long, String[]>();
        Map<Long, String> unsymbolized = new TreeMap<Long, String>();
        Set<Long> claimed = new HashSet<Long>();

        FunctionManager fm = currentProgram.getFunctionManager();
        List<Long> addrs = new ArrayList<Long>(nameMap.keySet());
        Collections.sort(addrs);

        // Exact-address hits first, so a real match always beats a guess.
        Map<Long, String[]> exact = new HashMap<Long, String[]>(nameMap);
        long[] symAddr = new long[addrs.size()];
        for (int i = 0; i < addrs.size(); i++) {
            symAddr[i] = addrs.get(i);
        }
        // How far past a symbol a Ghidra function may start and still be that
        // symbol.  Thunks are 16 bytes; real drift is a few dozen bytes.
        final long CLAIM_WINDOW = 0x200L;

        int total = 0, namedExact = 0, namedNear = 0;
        FunctionIterator it = fm.getFunctions(true);
        while (it.hasNext() && !monitor.isCancelled()) {
            Function f = it.next();
            if (maxFunctions > 0 && total >= maxFunctions) {
                break;
            }
            long entry = f.getEntryPoint().getOffset();
            String[] pair = exact.get(entry);
            long claimKey = entry;
            boolean isNear = false;
            if (pair == null) {
                int i = Arrays.binarySearch(symAddr, entry);
                int j = (i >= 0) ? i : -i - 2;
                if (j >= 0 && entry - symAddr[j] <= CLAIM_WINDOW && !claimed.contains(symAddr[j])) {
                    claimKey = symAddr[j];
                    pair = nameMap.get(claimKey);
                    isNear = pair != null;
                }
            }
            total++;
            if (pair == null) {
                // No ELF symbol behind this one; Ghidra's own GNU demangler has
                // usually named it, and it handles libc++ template expansion
                // better than our demangler does.
                unsymbolized.put(entry, f.getName());
                continue;
            }
            claimed.add(claimKey);
            if (isNear) {
                namedNear++;
            } else {
                namedExact++;
            }
            meta.put(entry, new String[] { pair[1], pair[0] });
            String key = groupKeyFor(pair[1]);
            List<Long> g = groups.get(key);
            if (g == null) {
                g = new ArrayList<Long>();
                groups.put(key, g);
            }
            g.add(entry);
        }

        // Symbols that never bound to a Ghidra function, so the inventory stays
        // complete and the gap is visible rather than silent.
        PrintWriter al = new PrintWriter(new OutputStreamWriter(
            new FileOutputStream(root.resolve("_unclaimed.tsv").toFile()),
            StandardCharsets.UTF_8));
        al.println("#\taddress\tmangled\tdemangled\treason");
        for (Long off : addrs) {
            if (claimed.contains(off)) {
                continue;
            }
            String[] pair = nameMap.get(off);
            String reason = exact.containsKey(off) ? "no-ghidra-function" : "interior";
            al.println("0x" + Long.toHexString(off) + "\t" + pair[0] + "\t" + pair[1]
                + "\t" + reason);
        }
        al.close();

        println("DecompileAll: " + total + " functions, " + namedExact
            + " exact symbol matches, " + namedNear + " bound by nearest symbol, "
            + unsymbolized.size() + " unsymbolised, " + groups.size() + " groups");

        PrintWriter un = new PrintWriter(new OutputStreamWriter(
            new FileOutputStream(root.resolve("_unsymbolized.tsv").toFile()),
            StandardCharsets.UTF_8));
        un.println("#\taddress\tghidra_name");
        for (Map.Entry<Long, String> e : unsymbolized.entrySet()) {
            un.println("0x" + Long.toHexString(e.getKey()) + "\t" + e.getValue());
        }
        un.close();

        applyNames(meta);

        int done = 0, ok = 0, failed = 0;
        long t0 = System.currentTimeMillis();
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
            out.println("/* generated by Ghidra DecompileAll; naming comes from the project's");
            out.println("   Itanium demangler via out/symbols/functions.tsv */");
            out.println();
            for (Long off : e.getValue()) {
                done++;
                String[] m = meta.get(off);
                monitor.setMessage("Decompiling " + m[0]);
                String status;
                String c = null;
                long fsize = 0;
                // Re-resolve the handle every time: the program is not mutated
                // during decompilation, but a missing function must not abort
                // the whole run.
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
                    if (status.equals("ok")) ok++;
                }
                out.println("/* " + status + "  address 0x" + Long.toHexString(off)
                    + "  size " + fsize + " */");
                if (m[1] != null && !m[1].isEmpty()) {
                    out.println("/* mangled: " + m[1] + " */");
                }
                out.println("/* " + m[0] + " */");
                out.println(c);
                out.println();
                index.println(rel + "\t0x" + Long.toHexString(off)
                    + "\t" + fsize + "\t"
                    + (m[1] == null ? "" : m[1]) + "\t" + m[0] + "\t" + status);
            }
            out.close();
            if (done % 100 == 0) {
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

    private Map<Long, String[]> loadNameMap(String path) throws IOException {
        Map<Long, String[]> m = new HashMap<Long, String[]>();
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
            try {
                long addr = Long.parseUnsignedLong(f[0].trim().replace("0x", ""), 16);
                m.put(addr, new String[] { f[2], f.length > 3 ? f[3] : f[2] });
            } catch (NumberFormatException ignore) {
                // skip malformed row
            }
        }
        return m;
    }

    /** Bucket a demangled name into an output group (usually a class). */
    private String groupKeyFor(String dem) {
        if (dem == null) {
            return "_misc";
        }
        int paren = indexOfTopLevel(dem, '(');
        String head = paren >= 0 ? dem.substring(0, paren) : dem;
        head = head.trim();
        // drop a trailing return type / const marker
        int last = head.lastIndexOf("::");
        if (last >= 0) {
            String owner = head.substring(0, last);
            if (owner.isEmpty()) {
                return "_misc";
            }
            return owner;
        }
        return "_globals";
    }

    private int indexOfTopLevel(String s, char ch) {
        int ang = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '<') ang++;
            else if (c == '>') ang = Math.max(0, ang - 1);
            else if (c == ch && ang == 0) return i;
        }
        return -1;
    }

    private String fileNameFor(String group) {
        // Deeply-templated libc++ names expand to kilobyte-long scopes. Collapse
        // anything past a sane depth so the tree stays navigable.
        if (group.length() > 90 || group.indexOf('<') >= 0) {
            String h = Integer.toHexString(group.hashCode());
            String tail = group.replaceAll("[^A-Za-z0-9_]", "_");
            if (tail.length() > 40) {
                tail = tail.substring(0, 40);
            }
            return "_tmpl/" + tail + "_" + h + ".cpp";
        }
        String s = group;
        // keep namespaces as directories, class as file
        s = s.replace("::", "/");
        s = s.replaceAll("[^A-Za-z0-9_/.-]", "_");
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
    private void applyNames(Map<Long, String[]> meta) {
        SymbolTable st = currentProgram.getSymbolTable();
        FunctionManager fm = currentProgram.getFunctionManager();
        int renamed = 0, nsFail = 0, skipped = 0;
        for (Map.Entry<Long, String[]> e : meta.entrySet()) {
            long off = e.getKey();
            String dem = e.getValue()[0];
            String mangled = e.getValue()[1];
            // Only override Ghidra's own GNU demangler where we have an ELF
            // symbol to back the name, and never touch template instantiations:
            // our demangler's libc++ substitution handling is less faithful than
            // GNU c++filt's, and mangling those names into namespaces makes the
            // output worse rather than better.
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
            String member = head.substring(last + 2).trim();
            // strip cv-qualifiers and any "operator" spacing
            member = member.replaceAll("\\s+", "_");
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
        // SymbolTable#getOrCreateNameSpace is the stable public entry point;
        // Program#getNamespaceManager is not exposed in Ghidra 12.
        SymbolTable st = currentProgram.getSymbolTable();
        Namespace cur = parent != null ? parent : globalNamespace();
        for (String part : scope.split("::")) {
            part = part.trim();
            if (part.isEmpty()) {
                continue;
            }
            part = part.replaceAll("[^A-Za-z0-9_]", "_");
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
