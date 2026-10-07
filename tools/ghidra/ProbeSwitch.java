import java.util.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.symbol.FlowType;
import ghidra.program.model.symbol.RefType;
import ghidra.program.model.symbol.Reference;

// ProbeSwitch: locate computed JUMPs (switch dispatch) inside the enum-seed
// functions and dump the surrounding disassembly + p-code, so EnumScan can
// detect jump-table dispatch over a seed enum register and recover the case
// constants from the jump-table bytes.
public class ProbeSwitch extends GhidraScript {
    @Override
    public void run() throws Exception {
        String tsv = getScriptArgs()[0];
        Listing listing = getCurrentProgram().getListing();
        Map<Long, List<String[]>> seeds = new HashMap<>();
        for (String line : new String(java.nio.file.Files
                .readAllBytes(java.nio.file.Paths.get(tsv))).split("\n")) {
            line = line.trim();
            if (line.isEmpty() || line.startsWith("#"))
                continue;
            String[] f = line.split("\t");
            if (f.length < 4)
                continue;
            String addr = f[0].trim();
            if (addr.startsWith("0x"))
                addr = addr.substring(2);
            long a;
            try {
                a = Long.parseLong(addr, 16);
            } catch (NumberFormatException e) {
                continue;
            }
            seeds.computeIfAbsent(a, k -> new ArrayList<>()).add(f);
        }
        println("seed functions=" + seeds.size());
        long jumpSites = 0, withRefs = 0, refs = 0, shown = 0;
        for (Map.Entry<Long, List<String[]>> e : seeds.entrySet()) {
            Function f = getFunctionAt(toAddr(e.getKey()));
            if (f == null)
                continue;
            for (Instruction ins : listing.getInstructions(f.getBody(), true)) {
                FlowType ft = ins.getFlowType();
                if (!(ft.isComputed() && ft.isJump()))
                    continue;
                jumpSites++;
                Address[] flows = ins.getFlows();
                int nRefs = 0;
                for (Reference r : ins.getReferencesFrom()) {
                    if (r.getReferenceType() == RefType.COMPUTED_JUMP)
                        nRefs++;
                }
                if (nRefs > 0)
                    withRefs++;
                refs += nRefs;
                if ((ins.getAddress().getOffset() == 0x3fb5b0L
                        || ins.getAddress().getOffset() == 0x40bd28L
                        || ins.getAddress().getOffset() == 0x4701bcL)
                        && shown < 8) {
                    shown++;
                    StringBuilder sb = new StringBuilder();
                    sb.append(String.format(
                            "%s 0x%x flows=%d refs=%d%n",
                            f.getName(), ins.getAddress().getOffset(),
                            flows.length, nRefs));
                    Instruction before = ins;
                    int back = 0;
                    java.util.ArrayDeque<Instruction> stack = new java.util.ArrayDeque<>();
                    while (before != null && before.getPrevious() != null && back < 10) {
                        before = before.getPrevious();
                        stack.addFirst(before);
                        back++;
                    }
                    for (Instruction b : stack) {
                        sb.append(String.format("  0x%x %-20s %s%n",
                                b.getAddress().getOffset(), b.getMnemonicString(),
                                b.toString()));
                        for (PcodeOp op : b.getPcode())
                            sb.append("      " + op.toString() + "\n");
                    }
                    sb.append(String.format("  >>0x%x %-20s %s%n",
                            ins.getAddress().getOffset(), ins.getMnemonicString(),
                            ins.toString()));
                    for (PcodeOp op : ins.getPcode())
                        sb.append("      " + op.toString() + "\n");
                    println(sb.toString());
                }
            }
        }
        println("computed JUMP sites: " + jumpSites);
        println("sites with resolved jump-table refs: " + withRefs + " (total refs " + refs + ")");
    }
}
