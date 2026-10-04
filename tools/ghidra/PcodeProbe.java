// PcodeProbe -- what does Ghidra's AArch64 decoder actually hand back?
//
// FieldScan.java (field-offset recovery) depends on three properties of the
// decoded form, and this script establishes them by measurement rather than by
// assumption, the same way the rest of this repo does:
//
//   1. currentProgram.getRegister(varnode) maps a raw-p-code register varnode
//      to a hardware Register;
//   2. the address for a load/store is a separate p-code op, so an affine
//      `this + k` falls out of INT_ADD/COPY without operand parsing;
//   3. whether the *destination* register is a real register varnode in raw
//      p-code, or only a unique that the instruction never names.
//
// Usage: PcodeProbe.java <start-address> [instruction-count]
// Prints only. Writes nothing to out/.

import java.util.Arrays;
import java.util.Iterator;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.Varnode;

public class PcodeProbe extends GhidraScript {

	@Override
	public void run() throws Exception {
		String[] args = getScriptArgs();
		Address start = currentProgram.getAddressFactory().getDefaultAddressSpace()
				.getAddress(args[0]);
		int limit = args.length > 1 ? Integer.parseInt(args[1]) : 40;

		Instruction first = currentProgram.getListing().getInstructionAt(start);
		if (first == null) {
			println("PROBE no instruction at " + start);
			return;
		}
		Function fn = currentProgram.getFunctionManager().getFunctionContaining(start);
		println("PROBE fn=" + (fn == null ? "<none>" : fn.getName()) + " bodyAddrs=" +
			(fn == null ? -1 : fn.getBody().getNumAddresses()));

		Iterator<Instruction> it = currentProgram.getListing()
				.getInstructions(first.getMinAddress(), true).iterator();
		int n = 0;
		while (it.hasNext() && n < limit) {
			Instruction cur = it.next();
			n++;
			StringBuilder sb = new StringBuilder();
			sb.append("--- ").append(cur.getAddress()).append("  ").append(cur.toString());
			sb.append("\n    mnem=").append(cur.getMnemonicString());
			sb.append(" flow=").append(cur.getFlowType());
			sb.append(" results=").append(Arrays.toString(cur.getResultObjects()));
			sb.append("\n    pcode:");
			for (PcodeOp op : cur.getPcode()) {
				sb.append("\n      ").append(op.getMnemonic()).append(" op=")
					.append(op.getOpcode());
				sb.append("\n         OUT ").append(describe(op.getOutput()));
				for (int i = 0; i < op.getNumInputs(); i++) {
					sb.append("\n         in").append(i).append(" ").append(describe(op.getInput(i)));
				}
			}
			println(sb.toString());
		}
		println("PROBE done " + n + " instructions");
	}

	private String describe(Varnode v) {
		if (v == null) {
			return "(null)";
		}
		StringBuilder sb = new StringBuilder();
		sb.append("space=").append(v.getSpace());
		sb.append(" off=").append(v.getOffset());
		sb.append(" sz=").append(v.getSize());
		sb.append(" uniq=").append(v.isUnique());
		sb.append(" const=").append(v.isConstant());
		Register r = currentProgram.getRegister(v);
		sb.append(" -> ").append(r == null ? "-" : r.getName());
		return sb.toString();
	}
}
