// FieldScan -- recover struct/class field offsets from member-function bodies.
//
// Why this exists
// ---------------
// The prototypes recovered from the Itanium manglings are exact, but a
// prototype only names *types*: `void Fluids::setSpout(Spout*)` says nothing
// about how big a `Spout` is or what lives inside it.  The README's blocking
// item is exactly this -- the 202 project types in Ghidra are zero-length
// placeholders because their field layouts were never recovered.  Ghidra cannot
// invent them either; the only record of them is the machine code.
//
// The method
// ----------
// Every non-static member function receives `this` in `x0`, and field access is
// `this + constant`.  So: run an affine dataflow over the raw p-code of each
// member function and record every load/store whose address reduces to
// `object + constant`.  Ghidra's SLEIGH decoder supplies the p-code, so no
// hand-rolled instruction decoder is involved (an earlier attempt at one had
// the load/store `op2` field wrong; it was deleted rather than debugged).
//
// Why p-code rather than operand text
// ----------------------------------
// PcodeProbe.java established the three properties this depends on:
//   * `Program.getRegister(varnode)` maps a register-space p-code varnode to a
//     hardware Register, so w8/x8/q8 canonicalise to one key;
//   * a load/store address is emitted as its own INT_ADD, so `this + 8` is
//     literally an INT_ADD of a register and a constant -- no operand parsing;
//   * a load's result lands in a *unique*, not in the destination register, so
//     `Instruction.getResultObjects()` is what tells us to invalidate a
//     register whose value the p-code did not define.
//
// The value lattice
// -----------------
// A tracked value is `object + base + i * stride`:
//   K_BASE  - relative to a known object (slot 0 = `this`, slot n = a seeded
//             parameter); `stride != 0` means an indexed/array access;
//   K_SCALE - `i * stride`, an index expression with no object behind it yet,
//             so `INT_ADD(this, INT_MULT(i, 4))` still resolves to an array;
//   K_SP    - a frame slot at a fixed offset from the entry `sp`, which is how
//             a `this` saved to the stack keeps resolving across a prologue;
//   K_NONE  - anything else.  Load results are K_NONE on purpose: a loaded
//             pointer refers to a *different* object, so attributing it to this
//             class would be wrong.
//
// Two filters keep this honest, one applied here and one downstream:
//   * AAPCS64 caller-saved registers are dropped at every CALL, so a stale
//     `this` can never be read after a call reused the register;
//   * a field offset is only accepted when independent functions agree, which
//     is what rejects a *static* member function whose x0 is really its first
//     argument.  This script therefore emits per-access evidence, not verdicts.
//
// Inputs: members.tsv (address size class role mangled name evidence seeds)
// Output: <outDir>/_fieldraw.tsv
//
// Columns: class (the object the base belongs to), offset, stride, width, access,
//          slot (0 = whatever holds x0), role, mnem, dreg (the data register,
//          which is the only record of the element type), addr, fn, owner (the
//          class the function itself belongs to), hyp (`this` or `static`).
//
// The `hyp` column is the load-bearing one.  A non-static member function has
// `this` in x0; a static one starts its parameters there.  Both readings put an
// object in x0, and the mangling cannot distinguish them, so the body is
// scanned once per reading and every access is tagged.  Letting the two merge
// would be actively wrong, not merely noisy: the static reading's first
// parameter and the non-static reading's `this` share register x0, so one
// silently overwrites the other's class label and a large object's fields get
// filed under a small one.
//
// Usage: FieldScan.java <members.tsv> <outDir>

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayList;
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

public class FieldScan extends GhidraScript {

	private static final int K_NONE = 0;
	private static final int K_BASE = 1;
	private static final int K_SCALE = 2;
	private static final int K_SP = 3;

	/** Sentinel for "this varnode is not a compile-time constant". */
	private static final long NA = Long.MIN_VALUE;

	/** AAPCS64 caller-saved general registers, by base-register name. */
	private static final Set<String> CALLER_SAVED = new HashSet<>();
	static {
		for (int i = 0; i <= 17; i++) {
			CALLER_SAVED.add("x" + i);
		}
		CALLER_SAVED.add("x30");
	}

	// ----------------------------------------------------------------- value

	private static final class Ptr {
		final int kind;
		final int slot;
		final long base;
		final long stride;

		Ptr(int kind, int slot, long base, long stride) {
			this.kind = kind;
			this.slot = slot;
			this.base = base;
			this.stride = stride;
		}

		static final Ptr NONE = new Ptr(K_NONE, -1, 0, 0);
	}

	private static Ptr base(int slot) {
		return new Ptr(K_BASE, slot, 0, 0);
	}

	private static Ptr sp(long frameOffset) {
		return new Ptr(K_SP, -1, frameOffset, 0);
	}

	private static Ptr scale(long stride) {
		return new Ptr(K_SCALE, -1, 0, stride);
	}

	/** Same object, different constant offset. */
	private static Ptr at(Ptr a, long off) {
		return new Ptr(K_BASE, a.slot, off, a.stride);
	}

	/** Fold two tracked values, keeping index expressions symbolic. */
	private static Ptr plus(Ptr a, Ptr b) {
		if (a.kind == K_NONE) {
			return b;
		}
		if (b.kind == K_NONE) {
			return a;
		}
		if (a.kind == K_SP && b.kind == K_SP) {
			return Ptr.NONE;
		}
		if (a.kind == K_SP) {
			return b.kind == K_BASE ? Ptr.NONE : sp(a.base + b.base);
		}
		if (b.kind == K_SP) {
			return a.kind == K_BASE ? Ptr.NONE : sp(a.base + b.base);
		}
		if (a.kind == K_BASE && b.kind == K_BASE) {
			return Ptr.NONE;
		}
		if (a.kind == K_BASE && b.kind == K_SCALE) {
			return new Ptr(K_BASE, a.slot, a.base, a.stride + b.stride);
		}
		if (a.kind == K_SCALE && b.kind == K_BASE) {
			return new Ptr(K_BASE, b.slot, b.base, b.stride + a.stride);
		}
		return new Ptr(K_SCALE, -1, 0, a.stride + b.stride);
	}

	private static Ptr minus(Ptr a, Ptr b) {
		if (a.kind == K_BASE && b.kind == K_NONE) {
			return new Ptr(K_BASE, a.slot, a.base - b.base, a.stride);
		}
		if (a.kind == K_SCALE && b.kind == K_NONE) {
			return new Ptr(K_SCALE, -1, 0, a.stride - b.stride);
		}
		if (a.kind == K_SP && b.kind == K_NONE) {
			return sp(a.base - b.base);
		}
		return Ptr.NONE;
	}

	// ----------------------------------------------------------------- input

	private static final class Seed {
		int reg;
		String cls;
		boolean byval;

		Seed(int reg, String cls, boolean byval) {
			this.reg = reg;
			this.cls = cls;
			this.byval = byval;
		}
	}

	private static final class Rec {
		Address addr;
		String cls;
		String role;
		final List<Seed> seedsThis = new ArrayList<>();
		final List<Seed> seedsStatic = new ArrayList<>();
	}

	// ----------------------------------------------------------------- state

	private long ramSpaceId;
	private PrintWriter out;
	private int emitted;
	private int functionsScanned;
	private int symbolsSeen;
	private final List<String[]> pending = new ArrayList<>();

	private Map<Long, Ptr> regs = new HashMap<>();
	private Map<Long, Ptr> tmps = new HashMap<>();
	private Map<Long, Ptr> frame = new HashMap<>();
	private Map<Long, Register> regByOffset;
	private long spOff;
	private boolean spValid;
	private boolean thisUsed;

	@Override
	public void run() throws Exception {
		String[] args = getScriptArgs();
		if (args.length < 2) {
			println("FieldScan: usage FieldScan.java <members.tsv> <outDir>");
			return;
		}
		ramSpaceId = currentProgram.getAddressFactory().getAddressSpace("ram").getSpaceID();
		regByOffset = new HashMap<>();
		for (Register r : currentProgram.getLanguage().getRegisters()) {
			regByOffset.put(r.getAddress().getOffset(), r);
			Register b = r.getBaseRegister();
			if (b != null) {
				regByOffset.putIfAbsent(b.getAddress().getOffset(), b);
			}
		}

		List<Rec> recs = readMembers(args[0]);
		println("FieldScan: read " + recs.size() + " member records");

		out = new PrintWriter(new BufferedWriter(new FileWriter(new File(args[1], "_fieldraw.tsv"))));
		out.println("# class\toffset\tstride\twidth\taccess\tslot\trole\tmnem\tdreg\taddr\tfn\towner\thyp");

		// Deduplicate by (entry point, hypothesis): 138 symbols bind to the nearest
		// preceding function, and rescanning such a body would double-count its
		// accesses.  The hypothesis is part of the key because both readings of
		// the same body are wanted.
		Set<String> done = new HashSet<>();
		for (Rec r : recs) {
			Function f = currentProgram.getFunctionManager().getFunctionAt(r.addr);
			if (f == null) {
				symbolsSeen++;
				continue;
			}
			symbolsSeen++;
			if (done.add(f.getEntryPoint() + "|this")) {
				scanFunction(f, r, "this", r.seedsThis, r.cls);
			}
			// The static reading only exists if some parameter claims x0, and
			// that parameter's class is what x0 then holds.
			String staticClass = null;
			for (Seed s : r.seedsStatic) {
				if (s.reg == 0) {
					staticClass = s.cls;
					break;
				}
			}
			if (staticClass != null && done.add(f.getEntryPoint() + "|static")) {
				scanFunction(f, r, "static", r.seedsStatic, staticClass);
			}
			if (symbolsSeen % 1000 == 0) {
				println("FieldScan: " + symbolsSeen + "/" + recs.size() + " symbols, " +
					functionsScanned + " scans, " + emitted + " accesses");
			}
		}

		out.flush();
		out.close();
		println("FieldScan: done. symbols=" + recs.size() + " functions=" + functionsScanned +
			" accesses=" + emitted + " -> " + args[1] + "/_fieldraw.tsv");
	}

	// ------------------------------------------------------------------ read

	private List<Rec> readMembers(String path) throws Exception {
		Map<Address, Rec> byAddr = new HashMap<>();
		List<Rec> ordered = new ArrayList<>();
		try (BufferedReader br = new BufferedReader(new FileReader(path))) {
			String line;
			while ((line = br.readLine()) != null) {
				if (line.isEmpty() || line.startsWith("#")) {
					continue;
				}
				String[] f = line.split("\t", -1);
				// address size class role mangled name evidence params
				// seeds_this seeds_static
				if (f.length < 7) {
					continue;
				}
				Address a;
				try {
					a = toAddr(f[0]);
				}
				catch (Exception e) {
					continue;
				}
				Rec r = byAddr.get(a);
				if (r == null) {
					r = new Rec();
					r.addr = a;
					r.cls = f[2];
					r.role = f[3];
					byAddr.put(a, r);
					ordered.add(r);
				}
				if (f.length >= 9) {
					parseSeeds(f[8], r.seedsThis);
				}
				if (f.length >= 10) {
					parseSeeds(f[9], r.seedsStatic);
				}
			}
		}
		ordered.sort((a, b) -> a.addr.compareTo(b.addr));
		return ordered;
	}

	/** seeds column: `reg,class,v` / `reg,class,p`, `|`-separated.
	 *
	 * Commas separate the tuple and pipes separate the entries because a class
	 * name contains `::`, which rules out colons.  A class name cannot contain a
	 * comma: members.py drops every template argument for exactly this reason. */
	private static void parseSeeds(String col, List<Seed> into) {
		if (col.isEmpty()) {
			return;
		}
		for (String e : col.split("\\|")) {
			String[] p = e.split(",", 3);
			if (p.length < 3) {
				continue;
			}
			try {
				into.add(new Seed(Integer.parseInt(p[0]), p[1], "v".equals(p[2])));
			}
			catch (NumberFormatException ignored) {
				// An unparseable seed is dropped, never guessed at.
			}
		}
	}

	// --------------------------------------------------------------- scanning

private void scanFunction(Function f, Rec r, String hyp, List<Seed> seeds,
			String slot0Class) {
		functionsScanned++;
		regs = new HashMap<>();
		tmps = new HashMap<>();
		frame = new HashMap<>();
		spOff = 0;
		spValid = true;
		thisUsed = false;
		pending.clear();

		// Which class each object base belongs to.  Slot 0 holds whatever the
		// chosen reading puts there -- the owner under `this`, the first
		// parameter's class under `static` -- and the remaining slots are seeded
		// parameters, which are frequently a *different* class again.  That is
		// the only way a symbol-less POD such as Walaber::Vector2, which owns no
		// member functions at all, reveals its layout.
		Map<Integer, String> slotClass = new HashMap<>();
		slotClass.put(0, slot0Class);

		putReg(0, base(0));
		for (Seed s : seeds) {
			putReg(s.reg, base(s.reg));
			slotClass.put(s.reg, s.cls);
		}

		String fnName = f.getName();
		Iterator<Instruction> it =
			currentProgram.getListing().getInstructions(f.getBody(), true).iterator();
		while (it.hasNext()) {
			Instruction in = it.next();
			try {
				scanInstruction(in, fnName);
			}
			catch (Throwable t) {
				// One malformed instruction must not abort a whole function.
				continue;
			}
		}

		// Drop slot-0 evidence from any function that never used x0
		// as an object base at all, which is a decode slip rather than a field.
		for (String[] row : pending) {
			int slot = Integer.parseInt(row[5]);
			if (slot == 0 && !thisUsed) {
				continue;
			}
			String cls = slotClass.get(slot);
			if (cls == null) {
				continue;
			}
			out.println(cls + "\t" + row[0] + "\t" + row[1] + "\t" + row[2] + "\t" + row[3] +
				"\t" + slot + "\t" + r.role + "\t" + row[4] + "\t" + row[7] + "\t" +
				row[6] + "\t" + fnName + "\t" + r.cls + "\t" + hyp);
			emitted++;
		}
	}

	private void scanInstruction(Instruction in, String fnName) {
		Set<Long> written = new HashSet<>();
		// `getMnemonicString()` returns just "ldr" and throws away the operands,
		// which is where the element type actually lives.  The full text is kept
		// instead: it distinguishes `ldr d0` (float64) from `ldr w0` (int32), both
		// of which are p-code width 4, and it carries the SVE lane specifier
		// (`ld1 {v0.2s}` is two floats) that no register name encodes.  This
		// binary vectorises heavily, so most float fields are reached through
		// `z` registers and the lane specifier is the only float/int signal.
		String mnem = in.toString().replace('\t', ' ');
		// `Instruction.getMnemonicString()` returns "ldr" with no operands, so it
		// carries no register class and cannot tell `ldr s0` (float) from
		// `ldr w0` (int32).  The element type therefore comes from the data
		// register, and the two directions need different sources: a load's
		// destination is in the instruction's *results*, because operand 0 is the
		// address, while a store's source is operand 0.  Taking operand 0 for both
		// silently reports the base register and turns every float field into an
		// integer one.
		String loadReg = firstRegister(in.getResultObjects());
		String storeReg = firstRegister(in.getOpObjects(0));

		for (PcodeOp op : in.getPcode()) {
			int code = op.getOpcode();
			Varnode outv = op.getOutput();

			switch (code) {
				case PcodeOp.LOAD: {
					if (isRam(op.getInput(0))) {
						emit(resolve(eval(op.getInput(1))), outv == null ? 0 : outv.getSize(),
							"load", mnem, loadReg, in);
					}
					setOp(outv, Ptr.NONE, written);
					break;
				}
				case PcodeOp.STORE: {
					if (isRam(op.getInput(0))) {
						Ptr a = eval(op.getInput(1));
						Ptr v = eval(op.getInput(2));
						if (a.kind == K_SP) {
							// A spill slot: remember it so a later reload still
							// resolves, but it is not itself a field access.
							frame.put(a.base, v);
						}
						else {
							emit(a, op.getInput(2).getSize(), "store", mnem, storeReg, in);
						}
					}
					break;
				}
				case PcodeOp.COPY: {
					setOp(outv, eval(op.getInput(0)), written);
					break;
				}
				case PcodeOp.INT_ADD: {
					long c1 = constVal(op.getInput(1));
					Ptr v = plus(eval(op.getInput(0)), eval(op.getInput(1)));
					if (c1 != NA && v.kind == K_BASE) {
						v = at(v, v.base + c1);
					}
					setOp(outv, v, written);
					break;
				}
				case PcodeOp.INT_SUB: {
					Ptr v = minus(eval(op.getInput(0)), eval(op.getInput(1)));
					setOp(outv, v, written);
					break;
				}
				case PcodeOp.INT_MULT: {
					long c0 = constVal(op.getInput(0));
					long c1 = constVal(op.getInput(1));
					Ptr a = eval(op.getInput(0));
					Ptr b = eval(op.getInput(1));
					Ptr v = Ptr.NONE;
					if (c0 != NA && a.kind == K_BASE && a.stride == 0) {
						v = at(a, a.base * c0);
					}
					else if (c1 != NA && b.kind == K_BASE && b.stride == 0) {
						v = at(b, b.base * c1);
					}
					else if (c0 != NA && a.kind == K_SCALE) {
						v = scale(a.stride * c0);
					}
					else if (c1 != NA && b.kind == K_SCALE) {
						v = scale(b.stride * c1);
					}
					else if (c0 != NA && b.kind == K_NONE && a.kind == K_NONE) {
						v = scale(c0);
					}
					else if (c1 != NA && a.kind == K_NONE && b.kind == K_NONE) {
						v = scale(c1);
					}
					setOp(outv, v, written);
					break;
				}
				case PcodeOp.INT_LEFT: {
					long c1 = constVal(op.getInput(1));
					setOp(outv, c1 == NA || c1 > 8 ? Ptr.NONE : scale(1L << c1), written);
					break;
				}
				case PcodeOp.INT_ZEXT:
				case PcodeOp.INT_SEXT:
				case PcodeOp.CAST: {
					setOp(outv, eval(op.getInput(0)), written);
					break;
				}
				default: {
					setOp(outv, Ptr.NONE, written);
					break;
				}
			}
		}

		// Invalidate registers the instruction wrote but the p-code did not
		// define: a load's result lands in a unique, so without this x8 would
		// still hold whatever `this + k` it had before.
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

	// --------------------------------------------------------------- plumbing

	/** Base-register name of the first Register in a Ghidra object array, or "". */
	private static String firstRegister(Object[] objs) {
		if (objs == null) {
			return "";
		}
		for (Object o : objs) {
			if (o instanceof Register) {
				Register r = ((Register) o).getBaseRegister();
				if (r != null) {
					return r.getName();
				}
			}
		}
		return "";
	}

	private void emit(Ptr a, int width, String access, String mnem, String dataReg,
			Instruction in) {
		if (a == null || a.kind != K_BASE) {
			return;
		}
		if (width <= 0 || width > 16) {
			return;
		}
		if (a.stride != 0 && (a.stride % width) != 0) {
			// An element size that does not divide the stride is arithmetic we
			// misread, not an array.
			return;
		}
		if (a.slot == 0) {
			thisUsed = true;
		}
		pending.add(new String[] { Long.toString(a.base), Long.toString(a.stride),
			Integer.toString(width), access, mnem, Integer.toString(a.slot),
			in.getAddress().toString(), dataReg });
	}

	/** Resolve a frame reference to whatever object the slot holds. */
	private Ptr resolve(Ptr a) {
		if (a != null && a.kind == K_SP) {
			Ptr p = frame.get(a.base);
			return p == null ? Ptr.NONE : p;
		}
		return a == null ? Ptr.NONE : a;
	}

	private void setOp(Varnode outv, Ptr v, Set<Long> written) {
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
		long key = baseReg.getAddress().getOffset();
		written.add(key);
		if ("sp".equals(baseReg.getName())) {
			// Writing sp re-bases the frame: keep the concrete offset if the
			// p-code computed one, otherwise forget it.
			if (v != null && v.kind == K_SP) {
				spOff = v.base;
				spValid = true;
			}
			else {
				spValid = false;
			}
			regs.remove(key);
			return;
		}
		putReg(key, v);
	}

	private void putReg(int regIndex, Ptr v) {
		Register r = currentProgram.getRegister("x" + regIndex);
		if (r != null) {
			putReg(r.getAddress().getOffset(), v);
		}
	}

	private void putReg(long key, Ptr v) {
		if (v == null || v.kind == K_NONE) {
			regs.remove(key);
		}
		else {
			regs.put(key, v);
		}
	}

	private void dropCallerSaved() {
		List<Long> kill = new ArrayList<>();
		for (Map.Entry<Long, Ptr> e : regs.entrySet()) {
			Register r = regByOffset.get(e.getKey());
			if (r == null || CALLER_SAVED.contains(r.getBaseRegister().getName())) {
				kill.add(e.getKey());
			}
		}
		for (Long k : kill) {
			regs.remove(k);
		}
	}

	private boolean isRam(Varnode space) {
		return constVal(space) == ramSpaceId;
	}

	private static long constVal(Varnode v) {
		if (v == null || !v.isConstant()) {
			return NA;
		}
		return v.getOffset();
	}

	private Ptr eval(Varnode v) {
		if (v == null || v.isConstant()) {
			// A constant is an absolute address (string, vtable, literal pool),
			// never `this`-relative.
			return Ptr.NONE;
		}
		if (v.isUnique()) {
			Ptr p = tmps.get(v.getOffset());
			return p == null ? Ptr.NONE : p;
		}
		Register r = currentProgram.getRegister(v);
		if (r == null) {
			return Ptr.NONE;
		}
		Register b = r.getBaseRegister();
		if (b == null) {
			return Ptr.NONE;
		}
		if ("sp".equals(b.getName())) {
			return spValid ? sp(spOff) : Ptr.NONE;
		}
		Ptr p = regs.get(b.getAddress().getOffset());
		return p == null ? Ptr.NONE : p;
	}
}