// RefCount -- for each address in a seed file, count references from code.
// Usage: RefCount.java <tsv>   (reads the address column)
import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.List;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;

public class RefCount extends GhidraScript {
	@Override
	public void run() throws Exception {
		String[] args = getScriptArgs();
		if (args.length < 1) {
			println("RefCount: need a seed tsv path");
			return;
		}
		List<Long> addrs = new ArrayList<>();
		try (BufferedReader br = new BufferedReader(new FileReader(args[0]))) {
			String line;
			while ((line = br.readLine()) != null) {
				if (line.startsWith("#")) {
					continue;
				}
				String[] f = line.split("\t", -1);
				if (f.length < 1) {
					continue;
				}
				String a = f[0];
				if (a.startsWith("0x") || a.startsWith("0X")) {
					a = a.substring(2);
				}
				try {
					addrs.add(Long.parseUnsignedLong(a, 16));
				}
				catch (Exception e) {
					// ignore
				}
			}
		}
		int withRefs = 0;
		long totalRefs = 0;
		long callRefs = 0;
		long codeRefs = 0;
		int biggest = 0;
		Address biggestAddr = null;
		for (Long l : addrs) {
			Address a = toAddr(l);
			int n = currentProgram.getReferenceManager().getReferenceCountTo(a);
			if (n > 0) {
				withRefs++;
				totalRefs += n;
				ghidra.program.model.listing.Function f =
					currentProgram.getFunctionManager().getFunctionAt(a);
				println("  " + a + " refs=" + n + " isFunc=" + (f != null));
				if (n > biggest) {
					biggest = n;
					biggestAddr = a;
				}
			}
			for (ghidra.program.model.symbol.Reference ref :
					currentProgram.getReferenceManager().getReferencesTo(a)) {
				if (!ref.isExternalReference()) {
					codeRefs++;
					if (ref.getReferenceType().isCall()) {
						callRefs++;
					}
				}
			}
		}
		println("RefCount: addresses=" + addrs.size() + " withRefs=" + withRefs +
			" totalRefs=" + totalRefs + " codeRefs=" + codeRefs + " callRefs=" + callRefs +
			" biggest=" + biggest + " @" + biggestAddr);
	}
}