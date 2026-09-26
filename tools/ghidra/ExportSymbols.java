// Export demangled names for the binary's mangled symbols.
//
// Ghidra's ELF loader already demangles symbols on import and stores the result
// as a second symbol at the same address. This script pairs the two up: the
// mangled name (starts with _Z) and the demangled name it was derived from
// (contains :: but is not itself mangled).
//
// Doing it this way means relying only on the symbol table API, and it uses
// Ghidra's mature GNU demangler as the authority. That matters because the
// repository's own demangler (tools/wmwtools/cxxfilt.py) resolves nested names,
// cv-qualifiers and simple parameter lists, but cannot always decode Itanium
// substitution indices into template argument lists -- the encoding behind
// std::basic_string<char, char_traits<char>, allocator<char>>.
//
// Args: <output-file>

import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public class ExportSymbols extends GhidraScript {

    /** True for a raw mangled name such as _ZN7Walaber6Sprite5drawE. */
    private static boolean isMangled(String s) {
        return s != null && s.startsWith("_Z");
    }

    /** True for a name Ghidra's demangler produced from a mangled symbol. */
    private static boolean looksDemangled(String s) {
        return s != null && !isMangled(s) && s.indexOf("::") >= 0;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) {
            println("ExportSymbols: need an output path");
            return;
        }

        // Index the symbol table by address, keeping both spellings. Reading
        // the mangled name from Function.getName() does not work: an earlier
        // DecompileAll run renamed 1,146 functions in place and headless runs
        // save the program, so those functions now report a demangled name.
        Map<Long, String> mangledByAddr = new HashMap<>();
        Map<Long, String> demangledByAddr = new HashMap<>();
        SymbolIterator all = currentProgram.getSymbolTable().getAllSymbols(true);
        while (all.hasNext() && !monitor.isCancelled()) {
            Symbol s = all.next();
            if (s.isExternal() || s.isDynamic()) {
                continue;
            }
            String name = s.getName();
            long addr = s.getAddress().getOffset();
            if (isMangled(name)) {
                mangledByAddr.putIfAbsent(addr, name);
            } else if (looksDemangled(name)) {
                demangledByAddr.putIfAbsent(addr, name);
            }
        }

        // Ghidra rebases a PIE image to 0x100000, so Address.getOffset() is the
        // rebased value, not the ELF virtual address. Every address written here
        // is normalised back to the ELF vaddr so the columns line up with
        // out/symbols/functions.tsv and the raw file offsets.
        long base = currentProgram.getImageBase().getOffset();

        int rows = 0;
        int named = 0;

        try (PrintWriter out = new PrintWriter(new OutputStreamWriter(
                new FileOutputStream(args[0]), StandardCharsets.UTF_8))) {
            out.println("#\taddress\tkind\tmangled\tdemangled");

            List<Long> addrs = new ArrayList<>(mangledByAddr.keySet());
            java.util.Collections.sort(addrs);
            for (long rebased : addrs) {
                String dem = demangledByAddr.get(rebased);
                if (dem != null) {
                    named++;
                }
                rows++;
                long vaddr = rebased - base;
                out.println(String.format("0x%x\t%s\t%s\t%s", vaddr,
                    kindAt(rebased), escape(mangledByAddr.get(rebased)),
                    escape(dem)));
            }
        }

        println(String.format(
            "ExportSymbols: %d mangled symbols, %d with a demangled name, base 0x%x",
            rows, named, base));
    }

    /** Label the row by the containing section, so callers can filter. */
    private String kindAt(long addr) {
        try {
            ghidra.program.model.address.Address a =
                currentProgram.getAddressFactory().getDefaultAddressSpace()
                    .getAddress(addr);
            ghidra.program.model.mem.MemoryBlock b =
                currentProgram.getMemory().getBlock(a);
            if (b != null && b.getName() != null) {
                return b.getName();
            }
        } catch (Exception ignored) {
            // Fall through to a generic label.
        }
        return "unknown";
    }

    private static String escape(String s) {
        if (s == null) {
            return "";
        }
        return s.replace("\t", " ").replace("\r", " ").replace("\n", " ");
    }
}
