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

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
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

        // group functions by owning scope so each class lands in one file
        Map<String, List<Function>> groups = new TreeMap<String, List<Function>>();
        Map<Function, String[]> meta = new IdentityHashMap<Function, String[]>();
        Map<Function, String> groupKey = new IdentityHashMap<Function, String>();

        int total = 0, named = 0;
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        while (it.hasNext() && !monitor.isCancelled()) {
            Function f = it.next();
            if (maxFunctions > 0 && total >= maxFunctions) {
                break;
            }
            total++;
            String[] pair = nameMap.get(f.getEntryPoint().getOffset());
            String demangled = pair != null ? pair[1] : null;
            if (demangled == null || demangled.isEmpty()) {
                // Not in the ELF symbol table (a thunk or a Ghidra-created
                // function). Ghidra's own GNU demangler has already named it,
                // and handles libc++ template expansion better than ours, so
                // leave those names alone.
                demangled = f.getName();
            } else {
                named++;
            }
            String key = groupKeyFor(demangled);
            meta.put(f, new String[] { demangled, pair != null ? pair[0] : "" });
            groupKey.put(f, key);
            List<Function> g = groups.get(key);
            if (g == null) {
                g = new ArrayList<Function>();
                groups.put(key, g);
            }
            g.add(f);
        }
        println("DecompileAll: " + total + " functions, " + named
            + " matched to demangled names, " + groups.size() + " groups");

        applyNames(meta, groupKey);

        int done = 0, ok = 0, failed = 0;
        long t0 = System.currentTimeMillis();
        for (Map.Entry<String, List<Function>> e : groups.entrySet()) {
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
            for (Function f : e.getValue()) {
                done++;
                String[] m = meta.get(f);
                monitor.setMessage("Decompiling " + m[0]);
                String status;
                String c = null;
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
                if (c == null || c.trim().isEmpty()) {
                    failed++;
                    c = "/* decompilation failed (" + status + ") */";
                } else {
                    if (status.equals("ok")) ok++;
                }
                out.println("/* " + status + "  address 0x" + Long.toHexString(f.getEntryPoint().getOffset())
                    + "  size " + f.getBody().getNumAddresses() + " */");
                if (m[1] != null && !m[1].isEmpty()) {
                    out.println("/* mangled: " + m[1] + " */");
                }
                out.println("/* " + m[0] + " */");
                out.println(c);
                out.println();
                index.println(rel + "\t0x" + Long.toHexString(f.getEntryPoint().getOffset())
                    + "\t" + f.getBody().getNumAddresses() + "\t"
                    + (m[1] == null ? "" : m[1]) + "\t" + m[0] + "\t" + status);
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
    private void applyNames(Map<Function, String[]> meta, Map<Function, String> groupKey) {
        SymbolTable st = currentProgram.getSymbolTable();
        int renamed = 0, nsFail = 0, skipped = 0;
        for (Map.Entry<Function, String> e : groupKey.entrySet()) {
            Function f = e.getKey();
            String dem = meta.get(f)[0];
            // Only override Ghidra's own GNU demangler where we have an ELF
            // symbol to back the name, and never touch template instantiations:
            // our demangler's libc++ substitution handling is less faithful than
            // GNU c++filt's, and mangling those names into namespaces makes the
            // output worse rather than better.
            if (meta.get(f)[1] == null || meta.get(f)[1].isEmpty() || dem.indexOf('<') >= 0) {
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
