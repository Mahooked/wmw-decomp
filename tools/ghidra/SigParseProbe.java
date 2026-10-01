// Probe 4: why does the C parser reject a ::-qualified type we created?
//
// applySignatures() creates a zero-length structure for every project class
// and then still fails to parse 3,231 prototypes, 2,521 of which fail *on a
// project class name* -- Walaber::Message, for instance, which the script has
// just created as a DataType. So creation and resolution disagree.
//
// The hypothesis worth testing is how the parser tokenises a qualified name. If
// it consumes `Walaber` as a type and then meets `::` unexpectedly, the error
// message names the qualified name only because that is the whole declaration
// it was given. Deciding this needs a small matrix of spellings, because the
// fix differs completely between the two outcomes:
//
//   - if only the exact "A::B" spelling works, the opaque type must be created
//     with that exact name (already the case) and the failure is about the
//     *zero length*, not the spelling;
//   - if "struct A::B" or an "A *B *" form works, the declaration format needs
//     adjusting rather than the type manager.
//
//     -postScript SigParseProbe.java <outDir>

import java.io.File;
import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.data.DataType;
import ghidra.program.model.data.DataTypeManager;
import ghidra.program.model.data.FunctionDefinitionDataType;
import ghidra.program.model.data.ParameterDefinition;
import ghidra.program.model.data.StructureDataType;

public class SigParseProbe extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] argv = getScriptArgs();
        PrintWriter w = new PrintWriter(new File(argv[0], "sigparse.tsv"), "UTF-8");
        DataTypeManager dtm = currentProgram.getDataTypeManager();

        ghidra.app.util.parser.FunctionSignatureParser parser =
            new ghidra.app.util.parser.FunctionSignatureParser(dtm, null);
        FunctionDefinitionDataType host =
            new FunctionDefinitionDataType("_wmw_sig");

        // Create the type under three plausible names and see which resolves.
        // Reporting the real path is the point of this probe: creation appears
        // to succeed, but a name that is stored at a different path than the one
        // we later look up would explain every resolution failure.
        String[] made = { "ProbeNs::Msg", "ProbeZero::Msg", "ProbeSized::Msg" };
        for (int i = 0; i < made.length; i++) {
            try {
                StructureDataType s;
                if (i == 2) {
                    s = new StructureDataType(made[i], 8, dtm);
                    s.add(new ghidra.program.model.data.DWordDataType(), 0, "a", null);
                } else {
                    s = new StructureDataType(made[i], 0, dtm);
                }
                w.println("# created " + made[i] + " as path=" + s.getPathName() +
                    " name=" + s.getName() + " cat=" + s.getCategoryPath() +
                    " len=" + s.getLength());
            } catch (Throwable t) {
                w.println("# could not create " + made[i] + ": " + t);
            }
        }
        for (String n : made) {
            DataType dt = dtm.getDataType(n);
            w.println("# lookup " + n + " -> " +
                (dt == null ? "NOT FOUND" : dt.getPathName() + " len=" + dt.getLength()));
        }
        // Enumerate what the manager actually holds, in case creation silently
        // landed somewhere else entirely.
        w.println("# --- all types whose name mentions Probe ---");
        java.util.Iterator<DataType> all = dtm.getAllDataTypes();
        int probeHits = 0;
        while (all.hasNext() && probeHits < 20) {
            DataType dt = all.next();
            if (dt.getName().contains("Probe") || dt.getPathName().contains("Probe")) {
                w.println("#   " + dt.getPathName() + " (name=" + dt.getName() +
                    " cat=" + dt.getCategoryPath() + ")");
                probeHits++;
            }
        }
        if (probeHits == 0) {
            w.println("#   (none -- creation did not persist)");
        }

        // The matrix: same logical parameter, different spellings.
        String[] decls = {
            "void _wmw_sig(ProbeNs::Msg *)",
            "void _wmw_sig(ProbeNs::Msg *p)",
            "void _wmw_sig(ProbeZero::Msg *)",
            "void _wmw_sig(ProbeSized::Msg *)",
            "void _wmw_sig(struct ProbeNs::Msg *)",
            "void _wmw_sig(class ProbeNs::Msg *)",
            "void _wmw_sig(ProbeNs::Msg)",
            "void _wmw_sig(ProbeNs::Msg &)",
            "void _wmw_sig(ProbeNs::Msg * , int)",
            "void _wmw_sig(int , ProbeNs::Msg *)",
            "void _wmw_sig(ProbeNs::Msg **)",
            "void _wmw_sig(ProbeNs::Msg * , ProbeNs::Msg *)",
        };
        for (String d : decls) {
            try {
                ParameterDefinition[] a = parser.parse(host, d).getArguments();
                StringBuilder sb = new StringBuilder();
                for (ParameterDefinition p : a) {
                    sb.append(p.getDataType() == null ? "(null)" :
                        p.getDataType().getPathName()).append(' ');
                }
                w.println("OK\t" + d + "\t-> " + sb.toString().trim());
            } catch (Throwable t) {
                w.println("FAIL\t" + d + "\t-> " + t.getMessage());
            }
        }

        // And the same for a real project type that already exists in the
        // program, to confirm the behaviour is not specific to the probe names.
        String[] real = { "Walaber::Message", "Walaber::Vector2", "ndk::MotionEvent" };
        for (String n : real) {
            // The leading slash matters: a type created as
            // StructureDataType("Walaber::Message", ...) is stored at
            // /Walaber::Message, and getDataType("Walaber::Message") is null.
            DataType bare = dtm.getDataType(n);
            DataType slash = dtm.getDataType("/" + n);
            w.println("# real " + n + " -> bare=" +
                (bare == null ? "null" : bare.getPathName()) + ", slash=" +
                (slash == null ? "null" : slash.getPathName()));

            // Now try resolving one that genuinely exists, to separate "the type
            // is missing" from "the parser cannot handle a :: in the name".
            DataType target = slash != null ? slash : bare;
            if (target == null) {
                // Create it, so the parse test is meaningful.
                try {
                    target = dtm.addDataType(
                        new StructureDataType(n, 0, dtm),
                        ghidra.program.model.data.DataTypeConflictHandler.KEEP_HANDLER);
                } catch (Throwable t) {
                    w.println("# could not create " + n + ": " + t);
                    continue;
                }
            }
            w.println("#   target resolves as " + target.getPathName());

            // The decisive test: does the parser accept this name in a declaration?
            for (String spelling : new String[] {
                    n + " *",                       // Walaber::Message *
                    n.replace("::", " ") + " *",    // Walaber Message *
                    "void *",                       // control: must succeed
                    "int *",                        // control: must succeed
            }) {
                try {
                    ParameterDefinition[] a =
                        parser.parse(host, "void _wmw_sig(" + spelling + ")").getArguments();
                    w.println("OK\t\"" + spelling + "\" -> " +
                        a[0].getDataType().getPathName());
                } catch (Throwable t) {
                    w.println("FAIL\t\"" + spelling + "\" -> " + t.getMessage());
                }
            }
        }

        // And the workaround: a typedef-style alias whose *name* has no "::",
        // so the parser can resolve it by its last component.
        w.println("# --- can an unqualified name be resolved? ---");
        for (String n : real) {
            String last = n.substring(n.lastIndexOf("::") + 2);
            try {
                ParameterDefinition[] a = parser.parse(host,
                    "void _wmw_sig(" + last + " *)").getArguments();
                w.println("OK\tunqualified " + last + " -> " +
                    a[0].getDataType().getPathName());
            } catch (Throwable t) {
                w.println("FAIL\tunqualified " + last + " -> " + t.getMessage());
            }
        }
        w.close();
        println("SigParseProbe: done");
    }
}
