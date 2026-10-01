// Probe: what does Ghidra's AArch64 model do with an explicit parameter list?
//
// The rebuild creates functions with no parameters at all, which is why
// ApplyFunctionSignatureCmd emits "parameter storage is locked" and why the
// earlier updateFunction attempt corrupted return types. This script does not
// modify anything: it only reports, for a handful of real functions, what
// storage Ghidra *would* assign, so the AAPCS64 model can be checked before
// anything is written.
//
//     ghidraRun ... -scriptPath <this dir> -postScript SigStorageProbe.java <out>

import java.io.File;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.data.ByteDataType;
import ghidra.program.model.data.Category;
import ghidra.program.model.data.CategoryPath;
import ghidra.program.model.data.DataType;
import ghidra.program.model.data.DataTypePath;
import ghidra.program.model.data.PointerDataType;
import ghidra.program.model.data.StructureDataType;
import ghidra.program.model.lang.PrototypeModel;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.VariableStorage;
import ghidra.program.model.pcode.Varnode;

public class SigStorageProbe extends GhidraScript {

    /** The language's default (AArch64 / AAPCS64) model, resolved once in run(). */
    private PrototypeModel model;

    @Override
    public void run() throws Exception {
        String[] outDir = getScriptArgs();
        File dir = new File(outDir.length > 0 ? outDir[0] : ".");
        PrintWriter w = new PrintWriter(new File(dir, "sigstorage.tsv"), "UTF-8");
        w.println("address\tname\treturnType\tparamTypes\tassignedStorage");

        int functions = 0;
        int withParams = 0;
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        while (it.hasNext() && functions < 4000) {
            Function f = it.next();
            functions++;
            if (f.getParameterCount() > 0) {
                withParams++;
            }
        }
        w.println("# functions sampled: " + functions + ", of which Ghidra already " +
            "has parameters on " + withParams);

        // What storage does the language's own prototype model assign to a
        // synthetic all-scalar parameter list? If this returns X0, X1, ... the
        // AAPCS64 model is usable and the whole problem is that the rebuild
        // never asks it to.
        model = currentProgram.getCompilerSpec().getDefaultCallingConvention();
        w.println("# default convention: " + (model == null ? "(none)" : model.getName()));

        if (model != null) {
            w.println("# built-in lookup: " + builtinNames());

            // How many integer/pointer arguments fit in registers before the
            // convention spills to the stack? This is the single most important
            // fact for a hand-rolled allocator to get right.
            for (int n = 1; n <= 12; n++) {
                DataType[] dts = new DataType[n];
                Arrays.fill(dts, builtin("uint"));
                probe(w, "uint x " + n, dts);
            }

            // Floats must go to V0..V7, not X0..X7, or every float argument is wrong.
            for (int n = 1; n <= 4; n++) {
                DataType[] dts = new DataType[n];
                Arrays.fill(dts, builtin("float"));
                probe(w, "float x " + n, dts);
            }

            // Mixed ordering is the case a naive "next free register"
            // implementation gets wrong: do the two register classes interleave
            // independently, or share one counter?
            probe(w, "mixed uint,float,uint,double", new DataType[] {
                builtin("uint"), builtin("float"), builtin("uint"), builtin("double") });
            probe(w, "mixed float,uint,float", new DataType[] {
                builtin("float"), builtin("uint"), builtin("float") });
            probe(w, "x9 then float (does float still find V0?)", new DataType[] {
                builtin("uint"), builtin("uint"), builtin("uint"), builtin("uint"),
                builtin("uint"), builtin("uint"), builtin("uint"), builtin("uint"),
                builtin("uint"), builtin("float") });

            // Pointers are the most common real parameter type here, and 8 bytes,
            // so they should behave exactly like uint.
            DataType ptr = currentProgram.getDataTypeManager()
                    .getDataType(CategoryPath.ROOT, "void *");
            if (ptr == null) {
                DataType v = builtin("void");
                if (v != null) {
                    ptr = new PointerDataType(v, currentProgram.getDataTypeManager());
                }
            }
            probe(w, "void* x1", new DataType[] { ptr });

            // An 8-byte struct is passed by value in a register on AArch64, and
            // larger aggregates go by reference. Both need to be known before
            // hand-rolling anything, because getting it wrong silently shifts
            // every subsequent argument.
            probe(w, "struct8 x1", new DataType[] { structure(8) });
            probe(w, "struct16 x1", new DataType[] { structure(16) });
            probe(w, "struct24 x1 (by reference?)", new DataType[] { structure(24) });
        }

        w.close();
        println("SigStorageProbe: wrote " + new File(dir, "sigstorage.tsv"));
    }

    /**
     * Resolve a built-in type by name.
     *
     * The obvious lookup, {@code getDataType("/BuiltInTypes/uint")}, returns null
     * here -- the category is named "BuiltIn" in some builds and "BuiltInTypes"
     * in others -- and a null DataType makes the storage model throw an opaque
     * NullPointerException from deep inside. Searching the categories by name
     * costs nothing and removes the guesswork.
     */
    private DataType builtin(String name) {
        DataType dt = currentProgram.getDataTypeManager()
                .getDataType("/BuiltInTypes/" + name);
        if (dt != null) {
            return dt;
        }
        for (CategoryPath c : categories()) {
            DataType found =
                currentProgram.getDataTypeManager().getDataType(c, name);
            if (found != null) {
                return found;
            }
        }
        return null;
    }

    private List<CategoryPath> categories() {
        List<CategoryPath> out = new ArrayList<>();
        java.util.Iterator<DataType> it =
            currentProgram.getDataTypeManager().getAllDataTypes();
        while (it.hasNext()) {
            CategoryPath cp = it.next().getDataTypePath().getCategoryPath();
            if (!out.contains(cp)) {
                out.add(cp);
            }
        }
        return out;
    }

    /** Report what the model assigns, tolerating a null type. */
    private void probe(PrintWriter w, String label, DataType[] dts) {
        for (int i = 0; i < dts.length; i++) {
            if (dts[i] == null) {
                w.println("# " + label + " -> NULL datatype at index " + i +
                    "; built-ins present: " + builtinNames());
                return;
            }
        }
        try {
            VariableStorage[] locs = model.getStorageLocations(currentProgram, dts, false);
            if (locs == null) {
                w.println("# " + label + " -> model returned null");
                return;
            }
            StringBuilder sb = new StringBuilder();
            for (VariableStorage vs : locs) {
                sb.append(storageText(vs)).append(' ');
            }
            w.println("# " + label + " -> " + sb.toString().trim());
        } catch (Throwable t) {
            w.println("# " + label + " -> FAILED " + t);
        }
    }

    private DataType structure(int size) {
        StructureDataType s = new StructureDataType(
            new CategoryPath("/probe"), "S" + size, size, currentProgram.getDataTypeManager());
        for (int off = 0; off < size; off += 4) {
            try {
                s.add(new ByteDataType(), off, "f" + off, null);
            } catch (Throwable t) {
                // A structure that cannot be filled in is still a valid size
                // probe; only the length matters to the storage model.
            }
        }
        return s;
    }

    private String builtinNames() {
        StringBuilder sb = new StringBuilder();
        for (String n : new String[] { "uint", "int", "float", "double", "void" }) {
            sb.append(n).append('=').append(builtin(n) == null ? "no" : "yes").append(' ');
        }
        return sb.toString();
    }

    private String storageText(VariableStorage vs) {
        if (vs == null) {
            return "(null)";
        }
        StringBuilder sb = new StringBuilder();
        for (Varnode v : vs.getVarnodes()) {
            if (sb.length() > 0) {
                sb.append(':');
            }
            if (v == null || v.getAddress() == null) {
                sb.append("?");
            } else {
                sb.append(v.getAddress());
            }
            sb.append(':').append(v.getSize());
        }
        return sb.toString();
    }
}
