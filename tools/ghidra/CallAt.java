// CallAt -- given a target address, print every referencing instruction with
// its CALL p-code inputs, to reconcile reference analysis with raw p-code.
import java.util.Iterator;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.Varnode;
import ghidra.program.model.symbol.Reference;

public class CallAt extends GhidraScript {
	@Override
	public void run() throws Exception {
		String[] args = getScriptArgs();
		if (args.length < 1) {
			println("CallAt: need a target address");
			return;
		}
		String a = args[0];
		if (a.startsWith("0x") || a.startsWith("0X")) {
			a = a.substring(2);
		}
		Address target = toAddr(Long.parseUnsignedLong(a, 16));
		println("CallAt: target " + target + " (" + Long.toUnsignedString(target.getOffset(), 16) + ")");
		int shown = 0;
		for (Reference ref : currentProgram.getReferenceManager().getReferencesTo(target)) {
			if (ref.isExternalReference()) {
				continue;
			}
			Address from = ref.getFromAddress();
			Instruction in = currentProgram.getListing().getInstructionAt(from);
			if (in == null) {
				continue;
			}
			Function owner = currentProgram.getFunctionManager().getFunctionContaining(from);
			println("  ref from " + from + " type=" + ref.getReferenceType() +
				" owner=" + (owner == null ? "-" : owner.getName()));
			if (shown++ >= 4) {
				break;
			}
			for (PcodeOp op : in.getPcode()) {
				if (op.getOpcode() == PcodeOp.CALL || op.getOpcode() == PcodeOp.CALLIND) {
					int kind = op.getOpcode() == PcodeOp.CALL ? 0 : 1;
					System.out.print("    CALL(" + kind + ") in=" + op.getNumInputs());
					for (int i = 0; i < op.getNumInputs(); i++) {
						Varnode v = op.getInput(i);
						System.out.print(" [" + i + "]=" + v +
							" const=" + v.isConstant() +
							" size=" + v.getSize() +
							" off=" + Long.toUnsignedString(v.getOffset(), 16) +
							" space=" + v.getAddress().getAddressSpace().getName());
					}
					System.out.println();
				}
			}
		}
	}
}