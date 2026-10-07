// ProbeCall -- dump the p-code of the first few CALL-bearing instructions,
// to see how a direct `bl` is represented in this program's saved analysis.
import java.util.Iterator;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.Varnode;

public class ProbeCall extends GhidraScript {

	@Override
	public void run() throws Exception {
		int shown = 0;
		String[] args = getScriptArgs();
		long startAddr = -1;
		if (args.length > 0) {
			String a = args[0];
			if (a.startsWith("0x") || a.startsWith("0X")) {
				a = a.substring(2);
			}
			startAddr = Long.parseUnsignedLong(a, 16);
		}
		for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
			if (startAddr >= 0 && f.getEntryPoint().getOffset() != startAddr) {
				continue;
			}
			Iterator<Instruction> it = currentProgram.getListing().getInstructions(f.getBody(), true).iterator();
			while (it.hasNext()) {
				Instruction in = it.next();
				PcodeOp[] ops = in.getPcode();
				boolean hasCall = false;
				for (PcodeOp op : ops) {
					if (op.getOpcode() == PcodeOp.CALL) {
						hasCall = true;
						System.out.println(in.getAddress() + "  " + in.toString());
						System.out.println("  CALL inputs=" + op.getNumInputs() +
							" in1.const=" + op.getInput(1).isConstant() +
							" in1=" + op.getInput(1) +
							" offset=" + Long.toUnsignedString(op.getInput(1).getOffset(), 16) +
							" space=" + op.getInput(1).getAddress().getAddressSpace().getName());
						for (Varnode iv : op.getInputs()) {
							System.out.println("    input: " + iv + " isConst=" + iv.isConstant() +
								" size=" + iv.getSize());
						}
						shown++;
						break;
					}
				}
				if (hasCall) {
					break;
				}
			}
			if (shown >= 8 || startAddr >= 0) {
				break;
			}
		}
	}
}