// EnumScan -- recover enum type definitions from constant-comparison evidence.
//
// Why this exists
// ---------------
// The Itanium ABI encodes the enum *type* of every parameter in the symbol, but
// not its enumerators.  The only record of the values is machine code: every
// use site compares an enum value against a compile-time constant, tests a
// flag with a mask, stores a constant into an enum slot, or passes one to a
// function that takes an enum by value.  The 104-style candidate types and the
// register that holds each one come from tools/enumparams.py
// (out/types/_enumparams.tsv); this script turns them into evidence
// (out/types/_enumraw.tsv).  tools/enums.py then decides what the sum of that
// evidence supports, exactly as layout.py does for struct fields.
//
// The value lattice
// -----------------
// A tracked value is one of:
//   K_ENUM(e)   - holds an enum of type e (a by-value param seed; also the
//                 result of loading through a K_ENUMREF pointer);
//   K_ENUMREF(e)- holds a pointer to an e (a by-reference/pointer-param seed);
//   K_CONST(c)  - holds compile-time constant c;
//   K_SP(off)   - the frame pointer at a known entry-sp offset, which is how a
//                 spilled enum keeps resolving across a prologue;
//   K_NONE      - anything else (loads from arbitrary objects, arithmetic on
//                 enums, comparison results, post-call garbage).
//
// A comparison against K_ENUM records `cmp`, an AND with a mask records `and`
// (flag enums), a store of a constant through K_ENUMREF records `store`, a
// direct call to an enum-parameter function with a K_CONST in the argument
// register records `call`, and a computed jump whose index register descends
// from a by-value seed enum records `switch`: the jump-table bytes are read and
// every recovered case constant is verified against the flows Ghidra resolved
// for the jump, so a `switch` row is an enumerator of the switched enum.  Only
// CALL/simd widths and the false-positive guards differ from FieldScan's
// honest-evidence policy:
//   * constants for `cmp` are capped at 0xffff and `call` too -- a real
//     absolute address is a register larger than that, and AArch64 comparison
//     immediates are 12-bit scaled, so smaller than 0xffff anyway;
//   * an K_ENUMREF compared against zero is a null test, not an enum value, so
//     only by-value enums (K_ENUM) earn `cmp` evidence;
//   * a constant pointer passed to a by-reference enum parameter is a null
//     pointer, not an enumerator, so `call` evidence requests by-value params;
//   * enums are deliberately NOT propagated through INT_SUB/INT_MULT/INT_LEFT,
//     so a switch-range adjust or a shift-based bit test cannot smuggle in the
//     range bounds as enumerators.
//
// Inputs: out/types/_enumparams.tsv   (address func reg enum byval)
// Output: <outDir>/_enumraw.tsv
//
// Columns: enum, value (hex), kind (cmp/and/store/call/switch), addr (scanning
//          function's entry, hex), fn, reg (base register the value was in).
//
// Usage: EnumScan.java <enumparams.tsv> <outDir>

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.Varnode;

public class EnumScan extends GhidraScript {

	private static final int K_NONE = 0;
	private static final int K_CONST = 1;
	private static final int K_ENUM = 2;
	private static final int K_ENUMREF = 3;
	private static final int K_SP = 4;

	/** Sentinel for "this varnode is not a compile-time constant". */
	private static final long NA = Long.MIN_VALUE;

	/** Absolute addresses never look like enumerators; caps per evidence kind. */
	private static final long MAX_CMP = 0xFFFFL;
	private static final long MAX_CALL = 0xFFFFL;
	private static final long MAX_AND = 0xFFFFFFFFL;

	/** AAPCS64 caller-saved general registers, by base-register name. */
	private static final Set<String> CALLER_SAVED = new HashSet<>();
	static {
		for (int i = 0; i <= 17; i++) {
			CALLER_SAVED.add("x" + i);
		}
		CALLER_SAVED.add("x30");
	}

	// ----------------------------------------------------------------- value

	private static final class Val {
		final int kind;
		final long c;      // K_CONST value or K_SP frame offset
		final String e;    // K_ENUM / K_ENUMREF type name

		Val(int kind, long c, String e) {
			this.kind = kind;
			this.c = c;
			this.e = e;
		}

		static final Val NONE = new Val(K_NONE, 0, null);
	}

	private static Val con(long c) {
		return new Val(K_CONST, c, null);
	}

	private static Val en(String e) {
		return new Val(K_ENUM, 0, e);
	}

	private static Val enref(String e) {
		return new Val(K_ENUMREF, 0, e);
	}

	private static Val sp(long off) {
		return new Val(K_SP, off, null);
	}

	// ----------------------------------------------------------------- input

	private static final class Seed {
		int reg;          // base register index (0..7)
		String e;
		boolean byval;

		Seed(int reg, String e, boolean byval) {
			this.reg = reg;
			this.e = e;
			this.byval = byval;
		}
	}

	// ----------------------------------------------------------------- state

	private Map<Long, Register> regByOffset;
	private long ramSpaceId;
	private final Map<Long, List<Seed>> seedByAddr = new HashMap<>();
	private PrintWriter out;
	private int emitted;
	private int functionsScanned;
	private int byValueSeeds;
	private int byRefSeeds;
	private final int[] byKind = new int[5]; // cmp and store call switch
	private int callsSeen;
	private int callsConst;
	private int callsMatched;
	private int callsEmitted;
	private boolean debug;
	private int debugCallsShown;

	private Map<Long, Val> regs = new HashMap<>();
	private Map<Long, Val> tmps = new HashMap<>();
	private Map<Long, Val> frame = new HashMap<>();
	private long spOff;
	private boolean spValid;

	// Recent p-code ops of the current function (a ring), so a computed jump
	// can be sliced backwards to the table-load/index expression that feeds it.
	private final Deque<PcodeOp> funcOps = new ArrayDeque<>();
	// Monotonic per-function program position of each op in the ring, used to
	// bound `findDef` to writes that precede a given use.
	private final Map<PcodeOp, Integer> opIdx = new HashMap<>();
	private int opSeq = 0;
	// by-value seed registers of the current function: base-register offset ->
	// enum name.  Only a switch *index* that traces back to one of these is a
	// jump-table dispatch over a recovered enum.
	private final Map<Long, String> seedByReg = new HashMap<>();

	@Override
	public void run() throws Exception {
		String[] args = getScriptArgs();
		if (args.length < 2) {
			println("EnumScan: usage EnumScan.java <enumparams.tsv> <outDir>");
			return;
		}
		debug = args.length > 2;
		regByOffset = new HashMap<>();
		ramSpaceId = currentProgram.getAddressFactory().getAddressSpace("ram").getSpaceID();
		for (Register r : currentProgram.getLanguage().getRegisters()) {
			regByOffset.put(r.getAddress().getOffset(), r);
			Register b = r.getBaseRegister();
			if (b != null) {
				regByOffset.putIfAbsent(b.getAddress().getOffset(), b);
			}
		}

		int seeds = readSeeds(args[0]);
		println("EnumScan: read " + seeds + " seeds (" + byValueSeeds + " by value, " +
			byRefSeeds + " by ref) for " + seedByAddr.size() + " functions");

		out = new PrintWriter(new BufferedWriter(new FileWriter(new File(args[1], "_enumraw.tsv"))));
		out.println("# enum\tvalue\tkind\taddr\tfn\treg");

		for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
			Address entry = f.getEntryPoint();
			List<Seed> s = seedByAddr.get(entry.getOffset());
			scanFunction(f, s);
			if (functionsScanned % 2000 == 0) {
				println("EnumScan: " + functionsScanned + " functions, " + emitted + " evidence");
			}
		}

		out.flush();
		out.close();
		println("EnumScan: done. functions=" + functionsScanned + " evidence=" + emitted +
			" (cmp=" + byKind[0] + " and=" + byKind[1] + " store=" + byKind[2] +
			" call=" + byKind[3] + " switch=" + byKind[4] + ") -> " +
			args[1] + "/_enumraw.tsv");
		println("EnumScan: calls=" + callsSeen + " const=" + callsConst +
			" matched=" + callsMatched + " call-evidence=" + callsEmitted);
	}

	// ------------------------------------------------------------------ read

	private int readSeeds(String path) throws Exception {
		int n = 0;
		try (BufferedReader br = new BufferedReader(new FileReader(path))) {
			String line;
			while ((line = br.readLine()) != null) {
				if (line.isEmpty() || line.startsWith("#")) {
					continue;
				}
				String[] f = line.split("\t", -1);
				// address func reg enum byval
				if (f.length < 5) {
					continue;
				}
				long addr;
				try {
					String a = f[0];
					if (a.startsWith("0x") || a.startsWith("0X")) {
						a = a.substring(2);
					}
					addr = Long.parseUnsignedLong(a, 16);
				}
				catch (Exception e) {
					continue;
				}
				Register r = currentProgram.getRegister(f[2]);
				if (r == null) {
					continue;
				}
				int regIdx = regIndexOf(r);
				if (regIdx < 0) {
					continue;
				}
				boolean byval = "1".equals(f[4]);
				seedByAddr.computeIfAbsent(addr, a -> new ArrayList<>())
					.add(new Seed(regIdx, f[3], byval));
				if (byval) {
					byValueSeeds++;
				}
				else {
					byRefSeeds++;
				}
				n++;
			}
		}
		return n;
	}

	/** xN base index of a general register, or -1. */
	private int regIndexOf(Register r) {
		Register b = r.getBaseRegister();
		if (b == null) {
			return -1;
		}
		String name = b.getName();
		if (name.length() < 2 || name.charAt(0) != 'x') {
			return -1;
		}
		try {
			int idx = Integer.parseInt(name.substring(1));
			return idx <= 7 ? idx : -1;
		}
		catch (NumberFormatException e) {
			return -1;
		}
	}

	// --------------------------------------------------------------- scanning

	private void scanFunction(Function f, List<Seed> seeds) {
		functionsScanned++;
		regs = new HashMap<>();
		tmps = new HashMap<>();
		frame = new HashMap<>();
		spOff = 0;
		spValid = true;
		funcOps.clear();
		opIdx.clear();
		opSeq = 0;
		seedByReg.clear();

		if (seeds != null) {
			for (Seed s : seeds) {
				valReg(s.reg, s.byval ? en(s.e) : enref(s.e));
				if (s.byval) {
					long key = regKey(s.reg);
					if (key >= 0) {
						seedByReg.put(key, s.e);
					}
				}
			}
		}

		String fnName = f.getName();
		Iterator<Instruction> it =
			currentProgram.getListing().getInstructions(f.getBody(), true).iterator();
		while (it.hasNext()) {
			Instruction in = it.next();
			try {
				scanInstruction(in, fnName, f);
			}
			catch (Throwable t) {
				// One malformed instruction must not abort a whole function.
				continue;
			}
		}
	}

	private void scanInstruction(Instruction in, String fnName, Function f) {
		Set<Long> written = new HashSet<>();

		for (PcodeOp op : in.getPcode()) {
			int code = op.getOpcode();
			Varnode outv = op.getOutput();
			funcOps.addLast(op);
			opIdx.put(op, opSeq);
			opSeq++;
			if (funcOps.size() > 8192) {
				funcOps.removeFirst();
			}

			switch (code) {
				case PcodeOp.LOAD: {
					Val a = eval(op.getInput(1));
					Val v = Val.NONE;
					if (a.kind == K_SP) {
						Val t = frame.get(a.c);
						v = t == null ? Val.NONE : t;
					}
					else if (a.kind == K_ENUMREF) {
						v = en(a.e);
					}
					setOp(outv, v, written);
					break;
				}
				case PcodeOp.STORE: {
					// input(0) is the space id, (1) the address, (2) the value.
					Val a = eval(op.getInput(1));
					Val v = eval(op.getInput(2));
					if (a.kind == K_SP) {
						// A spill slot: remember it so a later reload still
						// resolves; not itself field evidence.
						frame.put(a.c, v);
					}
					else if (a.kind == K_ENUMREF && v.kind == K_CONST &&
						v.c >= 0 && v.c != 0 && v.c <= MAX_AND) {
						emit(a.e, v.c, "store", in.getAddress(), fnName, "");
					}
					break;
				}
				case PcodeOp.COPY: {
					setOp(outv, eval(op.getInput(0)), written);
					break;
				}
				case PcodeOp.INT_ADD: {
					setOp(outv, add(eval(op.getInput(0)), eval(op.getInput(1))), written);
					break;
				}
				case PcodeOp.INT_SUB: {
					// AArch64 `cmp` is encoded as `subs` (a flagged subtract):
					// the output lands in a unique and the flags feed a later
					// branch.  A flagged subtract of an enum against a constant
					// IS a comparison, and this fork is exactly how the bulk of
					// switch/if evidence reaches us.  A plain sub into a general
					// register is an arithmetic adjust (range base, index) and
					// stays untracked, so the two are told apart by the
					// destination's uniqness.
					Val aS = eval(op.getInput(0));
					Val bS = eval(op.getInput(1));
					long caS = constVal(op.getInput(0));
					long cbS = constVal(op.getInput(1));
					boolean toUnique = outv != null && outv.isUnique();
					if (toUnique) {
						if (aS.kind == K_ENUM && cbS != NA && cbS >= 0 && cbS <= MAX_CMP) {
							emit(aS.e, cbS, "cmp", in.getAddress(), fnName, regName(op.getInput(0)));
						}
						else if (bS.kind == K_ENUM && caS != NA && caS >= 0 && caS <= MAX_CMP) {
							emit(bS.e, caS, "cmp", in.getAddress(), fnName, regName(op.getInput(1)));
						}
					}
					Val vS = Val.NONE;
					if (aS.kind == K_CONST && cbS != NA) {
						vS = con(aS.c - cbS);
					}
					else if (aS.kind == K_SP && cbS != NA) {
						vS = sp(aS.c - cbS);
					}
					else if (aS.kind == K_ENUMREF && cbS != NA) {
						vS = enref(aS.e);
					}
					setOp(outv, vS, written);
					break;
				}
				case PcodeOp.INT_MULT: {
					long c0 = constVal(op.getInput(0));
					long c1 = constVal(op.getInput(1));
					setOp(outv, c0 != NA && c1 != NA ? con(c0 * c1) : Val.NONE, written);
					break;
				}
				case PcodeOp.INT_ZEXT:
				case PcodeOp.INT_SEXT:
				case PcodeOp.CAST: {
					setOp(outv, eval(op.getInput(0)), written);
					break;
				}
				case PcodeOp.INT_AND: {
					Val a = eval(op.getInput(0));
					Val b = eval(op.getInput(1));
					long ca = constVal(op.getInput(0));
					long cb = constVal(op.getInput(1));
					Val r = Val.NONE;
					if (b.kind == K_ENUM && ca != NA && ca >= 0 && ca <= MAX_AND) {
						emit(b.e, ca, "and", in.getAddress(), fnName, regName(op.getInput(0)));
					}
					else if (a.kind == K_ENUM && cb != NA && cb >= 0 && cb <= MAX_AND) {
						emit(a.e, cb, "and", in.getAddress(), fnName, regName(op.getInput(1)));
					}
					else if (ca != NA && cb != NA && ca >= 0 && cb >= 0) {
						r = con(ca & cb);
					}
					setOp(outv, r, written);
					break;
				}
				case PcodeOp.INT_EQUAL:
				case PcodeOp.INT_NOTEQUAL:
				case PcodeOp.INT_LESS:
				case PcodeOp.INT_LESSEQUAL:
				case PcodeOp.INT_SLESS:
				case PcodeOp.INT_SLESSEQUAL: {
					for (int i = 0; i < 2; i++) {
						Val vi = eval(op.getInput(i));
						long c = constVal(op.getInput(1 - i));
						if (vi.kind == K_ENUM && c != NA && c >= 0 && c <= MAX_CMP) {
							emit(vi.e, c, "cmp", in.getAddress(), fnName, regName(op.getInput(i)));
						}
					}
					setOp(outv, Val.NONE, written);
					break;
				}
				case PcodeOp.BRANCHIND: {
					// A computed jump whose index register traces back to a
					// by-value seed enum is a table dispatch over that enum:
					// recover the case constants from the jump-table bytes and
					// verify them against Ghidra's own resolved flows.
					if (op.getNumInputs() >= 1) {
						resolveSwitch(in, fnName, op.getInput(0));
					}
					setOp(outv, Val.NONE, written);
					break;
				}
				case PcodeOp.CALL: {
					callsSeen++;
					if (debug && debugCallsShown < 4) {
						debugCallsShown++;
						println("DEBUG call @" + in.getAddress() + "  " + in.toString());
						for (int di = 0; di < op.getNumInputs(); di++) {
							Varnode iv = op.getInput(di);
							println("  in[" + di + "]=" + iv + " const=" + iv.isConstant() +
								" off=" + Long.toUnsignedString(iv.getOffset(), 16) +
								" space=" + iv.getAddress().getAddressSpace().getName());
						}
					}
					// A direct `bl` decodes to a *single* ram-space address varnode
					// (CALL (ram, target, 8)), not the (spaceid, constant) pair
					// that CALLIND's input[0] would masquerade as.
					Varnode tgt = op.getNumInputs() >= 1 ? op.getInput(0) : null;
					boolean direct = tgt != null &&
						!tgt.isConstant() &&
						tgt.getSize() == 8 &&
						tgt.getAddress().getAddressSpace().getSpaceID() == ramSpaceId;
					if (direct) {
						callsConst++;
						List<Seed> cs = seedByAddr.get(tgt.getOffset());
						if (cs != null) {
							callsMatched++;
							for (Seed s : cs) {
								if (!s.byval) {
									continue;
								}
								Val v = regVal(s.reg);
								if (v.kind == K_CONST && v.c >= 0 && v.c <= MAX_CALL) {
									emit(s.e, v.c, "call", in.getAddress(), fnName, "x" + s.reg);
									callsEmitted++;
								}
							}
						}
					}
					setOp(outv, Val.NONE, written);
					break;
				}
				default: {
					setOp(outv, Val.NONE, written);
					break;
				}
			}
		}

		// Invalidate registers the instruction wrote but the p-code did not
		// define: a load's result lands in a unique, so without this x8 would
		// still hold whatever value it had before.
		for (Object o : in.getResultObjects()) {
			if (!(o instanceof Register)) {
				continue;
			}
			long key = ((Register) o).getBaseRegister().getAddress().getOffset();
			if (!written.contains(key)) {
				regs.remove(key);
			}
		}

		if (in.getFlowType().isCall()) {
			dropCallerSaved();
			tmps.clear();
		}
	}

	// ------------------------------------------------------- switch resolution

	// Recovered state of the current computed-jump site (reset per site).
	private long minConst = 0;
	private boolean haveMin = false;
	private int entrySize = 0;
	private long leftShift = NA;
	private long multBy = NA;
	private boolean sextEntry = false;
	private long tableBase = NA;
	private long caseBase = NA;
	private String seedEnum = null;
	private String seedReg = null;
	private int sliceDepth = 0;

	/**
	 * If the computed jump is a table dispatch whose index register derives
	 * from a by-value seed enum, verify the table and emit the constants.
	 *
	 * The AArch64 switch idiom is `adrp/add` the table base into a register
	 * (folds to a constant), `sub w<idx>, w<seed>[, #min]`, an address
	 * expression `INT_ADD(base, INT_LEFT(index, shift))`, a LOAD (the entry,
	 * sign-extended), an optional `INT_ADD(entry, caseBase)`, and the computed
	 * jump itself.  The enum value stored in the seed register is
	 * `tableIndex + min`; the table's own contents fix the case target so the
	 * recovered value can be checked against Ghidra's resolved flows.
	 */
	private void resolveSwitch(Instruction in, String fnName, Varnode tgt) {
		minConst = 0;
		haveMin = false;
		entrySize = 0;
		leftShift = NA;
		multBy = NA;
		sextEntry = false;
		tableBase = NA;
		caseBase = NA;
		seedEnum = null;
		seedReg = null;
		sliceDepth = 0;
		matchExpr(tgt, false, fnName, opSeq);
		if (seedEnum == null || tableBase == NA || entrySize <= 0) {
			if (debug && seedEnum != null) {
				println("SWITCH-DBG " + fnName + " " + in.getAddress() + " seed=" + seedEnum +
					" fail=seed/env tableBase=" + (tableBase == NA ? "NA" : Long.toHexString(tableBase)) +
					" entrySize=" + entrySize);
			}
			return;
		}
		long stride = leftShift != NA ? (1L << leftShift) : multBy;
		if (stride == NA || stride <= 0 || stride != entrySize) {
			if (debug) {
				println("SWITCH-DBG " + fnName + " " + in.getAddress() + " seed=" + seedEnum +
					" fail=stride stride=" + (stride == NA ? "NA" : stride) + " entrySize=" + entrySize);
			}
			return;
		}
		Address[] flows = in.getFlows();
		if (flows == null || flows.length < 3) {
			if (debug) {
				println("SWITCH-DBG " + fnName + " " + in.getAddress() + " seed=" + seedEnum +
					" fail=flows n=" + (flows == null ? -1 : flows.length));
			}
			return;
		}
		Set<Long> flowSet = new HashSet<>();
		for (Address a : flows) {
			flowSet.add(a.getOffset());
		}
		int n = flows.length;
		int maxEntries = Math.min(n + 1, 128);
		byte[] buf;
		try {
			buf = new byte[maxEntries * entrySize];
			currentProgram.getMemory().getBytes(toAddr(tableBase), buf);
		}
		catch (Exception e) {
			return;
		}
		List<Long> values = new ArrayList<>();
		String dbgFirst = "";
		for (int i = 0; i < maxEntries; i++) {
			long raw = 0;
			for (int b = 0; b < entrySize; b++) {
				raw |= (long) (buf[i * entrySize + b] & 0xFF) << (8 * b);
			}
			long entry = sextEntry ? signExtend(raw, entrySize) : raw;
			long target = caseBase != NA ? caseBase + entry : entry;
			if (debug && i < 3) {
				dbgFirst += " e" + i + "=" + Long.toHexString(entry);
				dbgFirst += " tgt=" + Long.toHexString(target);
				dbgFirst += " inFlows=" + flowSet.contains(target);
			}
			if (flowSet.contains(target)) {
				values.add((long) i + minConst);
			}
			if (values.size() >= n) {
				break;
			}
		}
		// Every flow must be reached, landing on a contiguous index run, so the
		// value `i + min` is the table index, not a lucky coincidence.
		if (values.size() != n) {
			if (debug) {
				println("SWITCH-DBG " + fnName + " " + in.getAddress() + " seed=" + seedEnum +
					" fail=count got=" + values.size() + "/" + n +
					" tableBase=" + Long.toHexString(tableBase) +
					" caseBase=" + (caseBase == NA ? "NA" : Long.toHexString(caseBase)) +
					" entrySize=" + entrySize + " min=" + minConst + " sext=" + sextEntry +
					" flowsN=" + flows.length + " " + dbgFirst);
			}
			return;
		}
		for (int i = 0; i < n; i++) {
			if (values.get(i) != (long) i + minConst) {
				if (debug) {
					println("SWITCH-DBG " + fnName + " " + in.getAddress() + " seed=" + seedEnum +
						" fail=contig at " + i + " got=" + values.get(i) + " want=" + ((long) i + minConst));
				}
				return;
			}
		}
		for (long v : values) {
			emit(seedEnum, v, "switch", in.getAddress(), fnName, seedReg);
		}
	}

	/** Backward one-expressions slice over the current function's p-code.
	 *  `pos` is the program position of the consuming op; definitions are
	 *  only searched strictly before it, so register reuse (e.g. an index
	 *  register rewritten into a case address) resolves to the right write. */
	private void matchExpr(Varnode v, boolean inAddr, String fnName, int pos) {
		if (v == null || sliceDepth > 10) {
			return;
		}
		sliceDepth++;
		Val c = eval(v);
		if (c != null && c.kind == K_CONST) {
			// An address-sized constant is a base (table or case); anything
			// smaller is an index adjustment we do not model and must reject.
			if (c.c >= 0x10000L) {
				if (inAddr && tableBase == NA) {
					tableBase = c.c;
				}
				else if (!inAddr && caseBase == NA) {
					caseBase = c.c;
				}
			}
			sliceDepth--;
			return;
		}
		if (v.isConstant()) {
			sliceDepth--;
			return;
		}
		if (!v.isUnique()) {
			Register r = currentProgram.getRegister(v);
			if (r != null) {
				Register base = r.getBaseRegister();
				String baseName = base == null ? r.getName() : base.getName();
				if (baseName != null && baseName.startsWith("sp")) {
					sliceDepth--;
					return;
				}
			}
			// Registers are identified by their register-space offset alone:
			// the classifier's branch target is a copy-in register Ghidra does
			// not expose through getRegister(), and w0/x0 share the offset.
			String e = seedByReg.get(v.getAddress().getOffset());
			if (e != null) {
				seedEnum = e;
				seedReg = seedName(v);
				sliceDepth--;
				return;
			}
		}
		PcodeOp d = findDef(v, pos);
		if (d == null) {
			sliceDepth--;
			return;
		}
		int oc = d.getOpcode();
		switch (oc) {
			case PcodeOp.COPY:
			case PcodeOp.CAST:
			case PcodeOp.INT_ZEXT:
			case PcodeOp.INT_SEXT:
				if (oc == PcodeOp.INT_SEXT) {
					sextEntry = true;
				}
				matchExpr(d.getInput(0), inAddr, fnName, idxOf(d));
				break;
			case PcodeOp.INT_SUB:
			case PcodeOp.INT_ADD: {
				long c2 = constVal(d.getInput(1));
				if (oc == PcodeOp.INT_SUB && c2 != NA && !haveMin) {
					minConst = c2;
					haveMin = true;
				}
				int p = idxOf(d);
				if (oc == PcodeOp.INT_ADD && !inAddr && c2 != NA) {
					// `add x, seed, #k`: constant index adjustment.
					matchExpr(d.getInput(0), inAddr, fnName, p);
				}
				else {
					matchExpr(d.getInput(0), inAddr, fnName, p);
					matchExpr(d.getInput(1), inAddr, fnName, p);
				}
				break;
			}
			case PcodeOp.INT_LEFT: {
				long c2 = constVal(d.getInput(1));
				if (c2 != NA && leftShift == NA) {
					leftShift = c2;
				}
				matchExpr(d.getInput(0), inAddr, fnName, idxOf(d));
				break;
			}
			case PcodeOp.INT_MULT: {
				long c2 = constVal(d.getInput(1));
				if (c2 != NA && multBy == NA) {
					multBy = c2;
				}
				matchExpr(d.getInput(0), inAddr, fnName, idxOf(d));
				break;
			}
			case PcodeOp.LOAD: {
				Varnode o = d.getOutput();
				if (o != null && entrySize == 0) {
					entrySize = o.getSize();
				}
				matchExpr(d.getInput(1), true, fnName, idxOf(d));
				break;
			}
			default:
				break;
		}
		sliceDepth--;
	}

	private int idxOf(PcodeOp d) {
		Integer i = opIdx.get(d);
		return i == null ? 0 : i;
	}

	private PcodeOp findDef(Varnode v, int pos) {
		PcodeOp found = null;
		int best = -1;
		for (PcodeOp d : funcOps) {
			Integer i = opIdx.get(d);
			if (i == null || i >= pos) {
				continue;
			}
			Varnode o = d.getOutput();
			if (o != null && sameVarnode(o, v) && i > best) {
				found = d;
				best = i;
			}
		}
		return found;
	}

	private boolean sameVarnode(Varnode a, Varnode b) {
		if (a.isUnique() != b.isUnique() || a.isConstant() != b.isConstant()) {
			return false;
		}
		if (a.isUnique()) {
			return a.getOffset() == b.getOffset() && a.getSize() == b.getSize();
		}
		if (a.isConstant()) {
			return false;
		}
		// Registers live in the "register" space; pairs of sub-registers
		// (w0/x0 etc.) share the same address offset, which is all the
		// backward slice needs. getRegister() is not consulted because the
		// classifier inserts its own copy-in register at an offset Ghidra
		// does not expose as a named register.
		if (a.getAddress().getAddressSpace().getSpaceID() !=
			b.getAddress().getAddressSpace().getSpaceID()) {
			return false;
		}
		return a.getAddress().getOffset() == b.getAddress().getOffset();
	}

	private long regKey(int regIndex) {
		Register r = currentProgram.getRegister("x" + regIndex);
		return r == null ? -1 : r.getBaseRegister().getAddress().getOffset();
	}

	private String seedName(Varnode v) {
		Register r = currentProgram.getRegister(v);
		Register base = r == null ? null : r.getBaseRegister();
		return base == null ? ("off" + v.getAddress().getOffset()) : base.getName();
	}

	private static long signExtend(long raw, int size) {
		if (size >= 8) {
			return raw;
		}
		int bits = size * 8;
		long m = 1L << (bits - 1);
		long mask = (1L << bits) - 1;
		long x = raw & mask;
		return (x ^ m) - m;
	}

	// --------------------------------------------------------------- plumbing

	private void emit(String e, long value, String kind, Address addr, String fn, String reg) {
		out.println(e + "\t0x" + Long.toHexString(value) + "\t" + kind + "\t" +
			addr.getOffset() + "\t" + fn + "\t" + reg);
		emitted++;
		int ki = "cmp".equals(kind) ? 0 : "and".equals(kind) ? 1
			: "store".equals(kind) ? 2 : "switch".equals(kind) ? 4 : 3;
		byKind[ki]++;
	}

	private void setOp(Varnode outv, Val v, Set<Long> written) {
		if (outv == null) {
			return;
		}
		if (outv.isUnique()) {
			tmps.put(outv.getOffset(), v);
			return;
		}
		Register r = currentProgram.getRegister(outv);
		if (r == null) {
			return;
		}
		Register baseReg = r.getBaseRegister();
		if (baseReg == null) {
			return;
		}
		long key = baseReg.getAddress().getOffset();
		written.add(key);
		if ("sp".equals(baseReg.getName())) {
			// Writing sp re-bases the frame: keep the concrete offset if the
			// p-code computed one, otherwise forget it.
			if (v != null && v.kind == K_SP) {
				spOff = v.c;
				spValid = true;
			}
			else {
				spValid = false;
			}
			regs.remove(key);
			return;
		}
		valReg(key, v);
	}

	private void valReg(int regIndex, Val v) {
		String name = "x" + regIndex;
		Register r = currentProgram.getRegister(name);
		if (r != null) {
			valReg(r.getBaseRegister().getAddress().getOffset(), v);
		}
	}

	private void valReg(long key, Val v) {
		if (v == null || v.kind == K_NONE) {
			regs.remove(key);
		}
		else {
			regs.put(key, v);
		}
	}

	private Val regVal(int regIndex) {
		Register r = currentProgram.getRegister("x" + regIndex);
		if (r == null) {
			return Val.NONE;
		}
		Val v = regs.get(r.getBaseRegister().getAddress().getOffset());
		return v == null ? Val.NONE : v;
	}

	private void dropCallerSaved() {
		List<Long> kill = new ArrayList<>();
		for (Map.Entry<Long, Val> e : regs.entrySet()) {
			Register r = regByOffset.get(e.getKey());
			if (r == null || CALLER_SAVED.contains(r.getBaseRegister().getName())) {
				kill.add(e.getKey());
			}
		}
		for (Long k : kill) {
			regs.remove(k);
		}
	}

	private static long constVal(Varnode v) {
		if (v == null || !v.isConstant()) {
			return NA;
		}
		return v.getOffset();
	}

	private String regName(Varnode v) {
		if (v == null || v.isConstant() || v.isUnique()) {
			return "";
		}
		Register r = currentProgram.getRegister(v);
		if (r == null) {
			return "";
		}
		Register b = r.getBaseRegister();
		return b == null ? "" : b.getName();
	}

	/** Base-register name of where an enum value was, or the varnode itself. */
	private Val eval(Varnode v) {
		if (v == null) {
			return Val.NONE;
		}
		if (v.isConstant()) {
			return con(v.getOffset());
		}
		if (v.isUnique()) {
			Val p = tmps.get(v.getOffset());
			return p == null ? Val.NONE : p;
		}
		Register r = currentProgram.getRegister(v);
		if (r == null) {
			return Val.NONE;
		}
		Register b = r.getBaseRegister();
		if (b == null) {
			return Val.NONE;
		}
		if ("sp".equals(b.getName())) {
			return spValid ? sp(spOff) : Val.NONE;
		}
		Val p = regs.get(b.getAddress().getOffset());
		return p == null ? Val.NONE : p;
	}

	private static Val add(Val a, Val b) {
		if (a.kind == K_CONST && b.kind == K_CONST) {
			return con(a.c + b.c);
		}
		if (a.kind == K_CONST && b.kind == K_SP) {
			return sp(b.c + a.c);
		}
		if (a.kind == K_SP && b.kind == K_CONST) {
			return sp(a.c + b.c);
		}
		if (a.kind == K_ENUMREF && b.kind == K_CONST) {
			return enref(a.e);
		}
		if (a.kind == K_CONST && b.kind == K_ENUMREF) {
			return enref(b.e);
		}
		return Val.NONE;
	}
}
