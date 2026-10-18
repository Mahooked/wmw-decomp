# Where's My Water? — full decompilation

Reverse-engineering notes, tooling, and recovered C++ for **Where's My Water? 1.18.9**
(Android, `com.disney.WMW`).

## The goal

**The full source code, exactly as the developers had it** — every function in
compilable C++ with its original names, types and file organisation, verified by
rebuilding against the shipped `libwmw.so`. A symbol map or a folder of
decompiler pseudocode is a milestone, not the destination.

The game makes this unusually tractable: the bulk of it is a **native C++ engine**
(`lib/arm64-v8a/libwmw.so`, 7.1 MB) that shipped **unstripped**, so thousands of
real class, method, and RTTI names survive in `.dynsym`. That turns "decompiling a
closed-source app" into something much closer to "reading a disassembly with the
original identifier table attached". Names are the easy half: bodies still have to
be lifted out of AArch64 machine code, and everything the compiler did not encode
— local variable names, comments, macros, original file layout — has to be
re-inferred.

## Where we are

| Subsystem | State | Coverage |
|---|---|---|
| ELF survey and symbol naming | **done** | 11,003 `.dynsym` entries; all 8,618 function symbols named and demangled |
| Itanium demangler at GCC parity | **done** | 6,769/6,769 reference names (100%, 0 diffs), regression-tested |
| Class hierarchy + vtables (RTTI) | **done** | 317 classes, 343 base edges, 284 polymorphic, 3,003 virtual slots, 184 headers |
| Data formats (SQLite, level XML, assets, dex/JNI) | **done** | schemas and vocabularies under `out/` |
| Decompiled, named function bodies | **done** | 8,618 / 8,618 symbols bound (100%), 1,467 files |
| Call-target names (PLT imports) | **done** | 64,007 / 66,330 call placeholders resolved from `.rela.plt`; 4,765 imports named (see "Call targets and PLT imports") |
| Exact function prototypes recovered | **done** | 6,769/6,769 C++ symbols validated against GCC's own rendering; 9,952 parameters |
| Struct/field layouts, signatures applied to bodies | **partly done** | 2,450 functions carry exact AAPCS64-allocated parameters through Ghidra, plus 641 more applied as text where Ghidra cannot name the type (see "Types without a type system"); 325 class layouts recovered from p-code field-access evidence, imported into Ghidra and rendered as member reads in the output (see "Function signatures") |
| Enum definitions | **partly done** | 9 value-typed enums recovered from constant-compare/store/mask/jump-table evidence, verified by a gate (see "Enums") |
| Original local names, file layout, comments | not encodable | never present in the binary; must be re-inferred |
| Compilable-tree syntax baseline | **measured** | every one of the 1,467 files parsed by `clang++ -fsyntax-only` against synthesised declarations; **74,002** diagnostics (down from 94,265), the declarations themselves compiling with **0 errors** (see "The syntax gate") |
| Rebuild-equivalence check (recompile and compare) | not started | this is the definition of done |

### Remaining work

1. **Recover type definitions.** Function signatures are exact (they are encoded
   in the manglings), validated against GCC, and now applied to 2,450 decompiled
   bodies through Ghidra plus a further 641 as plain text where Ghidra cannot
   name the type (see "Types without a type system"). Class field layouts are now
   recovered too — 325 of them, each proven to rebuild to its recovered `sizeof`
   under the C++ ABI — and 9 enums have been lifted out of the constant compares,
   masks and jump tables the binary performs on them (see "Enums"). Typedefs and
   the remaining field names still have to be read out of the code that uses
   them, and fields are currently named `f_0x<offset>` because the binary never
   recorded their names. See "Function signatures".
2. **Re-shape decompiler output into source-shaped code.** The emitted C is
   machine-shaped. Call targets are now named (see "Call targets and PLT
   imports") and the compiler's `-fstack-protector` canary has been stripped
   from 2,434 of the 2,513 guarded bodies (see "Source shaping"). The bodies'
   register copies are handled next: 1,094 dead or aliasing copies removed and
   586 alias reads folded back to their source across 273 files. What remains is
   if-converted branches, sub-register noise (`CONCAT`/`SUB`/`ZEXT`) and the C++
   exception landing pads. "Is it source?" is now a *number* rather than an
   opinion: `tools/check_syntax.py` points `clang++ -fsyntax-only` at all 1,467
   files against synthesised declarations and sorts the 74,002 diagnostics into
   the ones that are genuinely malformed C++ and the ones that are only missing
   declarations (see "The syntax gate"). The first two systematic defects it
   named are fixed — illegal return types and parameters on 695 constructors
   and destructors, then 17,182 calls spelled in Ghidra's static member form —
   and the next one it names is call/definition arity divergence.
3. **Re-infer local identifiers and file organisation.** These were never in the
   binary; they have to be reconstructed from behaviour and class structure.
4. **Verify by recompilation.** Rebuilding and comparing against the shipped
   binary is the only honest completion test.

### Milestones

- `5defcdf`..`febcf71` -- ELF tooling, decompiled source tree, class model, data
  formats, JNI bridge.
- `c77d06c`..`e49d4fc` -- demangler iterated against a GCC oracle from first cut
  to **100% parity** (substitutions, templates, expressions, thunks) plus a
  regression gate.
- Function boundaries rebuilt from the ELF symbol table: 2,131 -> **8,618
  symbols bound (100%)**, 641 -> 1,467 files. See "Function boundaries".
- Exact function prototypes recovered and validated against GCC's own rendering
  (6,769/6,769). See "Function signatures".
- 325 field layouts proven from p-code field-access evidence, ABI-verified, and
  applied to the output; signatures rise 2,282 -> 2,450. See "Function
  signatures".
- 9 enums recovered from constant-compare/store/mask/jump-table evidence, each
  re-derived by a gate. See "Enums".
- `out/src` regenerated from a clean import with layouts applied and path-free
  file headers.
- 64,007 call-site placeholders (`func_0x…`/`FUN_…`) rewritten to the real
  callee by decoding PLT stubs through `.rela.plt`: 66,330 -> 2,323 unresolved,
  of which 28,332 are game-symbol calls. See "Call targets and PLT imports".
- Exact function prototypes, which Ghidra could only apply when it could name
  the type, now written to **641** more definitions as text — libc++ template
  parameters included — with `param_N` falling 70,864 -> 66,674 and members'
  `param_1` shown as `this`. See "Types without a type system".
- Compiler-inserted code stripped from the bodies: the `-fstack-protector`
  canary and its dead locals removed from **2,434** guarded functions
  (`out/src` −19,500 lines, 485 files), the remaining 79 left intact because
  the guard shares a live local or an exit label. See "Source shaping".
- The decompiler's register copies collapsed: **1,094** dead or aliasing copies
  removed and **586** alias reads folded to their source, freeing **833**
  declarations across 273 files (`out/src` −1,927 lines). See "Source shaping".
- The distance to a compilable tree made measurable: `tools/check_syntax.py`
  synthesises the declarations the bodies are missing and has `clang++` parse all
  **1,467** files, sorting **84,570** diagnostics into malformed C++ and mere
  missing declarations. The synthesised declarations themselves compile with
  **0 errors**. See "The syntax gate".
- The baseline driven **84,570 → 75,922** by the gate's own largest buckets:
  illegal return types and destructor parameters stripped from **695**
  constructor/destructor definitions (none such remain); symbol detection
  extended to the `PTR_`/`UNK_` hex-suffixed forms; and member declarations
  synthesised in Ghidra's static form — `static` unless the body names
  `this`, never for constructors, destructors or operators — with every
  overload kept, moving *call to non-static member function* **17,182 →
  2,334**. See "The syntax gate".
- The baseline driven **75,922 → 74,002** by re-binding Ghidra's unbound
  input registers as parameters (`tools/shape_inw.py`): **764** definitions
  reshaped, moving *too many arguments to function call* **4,817 →
  1,895** — appends where AAPCS64 leaves no choice, front inserts only
  where the call sites corroborate the extra argument. See "The syntax
  gate".

## What the game turned out to be

The file extension on this game is `.wmw`, which invites the assumption that it is
some kind of Lua script bundle (the original Flash-adjacent `Where's My Water?`
community tooling is Lua-oriented). **It is not.** There is no Lua bytecode in the
APK. `assets/Script/WC.txt` is a localization table, not a script.

| | |
|---|---|
| Language | C++ (AArch64) + a thin Java shell |
| Engine namespaces | `Walaber` (engine), `WaterConcept` (game) |
| Java layer | one thin `classes.dex` (165 KB) — `com.disney.WMW.WMWActivity` |
| Level data | XML scene definitions + SQLite (`water.db`) |
| Vendored in-binary | libc++, SQLite, libxml2, libwebp, minizip |

Most of the interesting behaviour lives in the native library. The Java side is
little more than an activity, a billing bridge (`com.android.vending.BILLING`), and
a JNI entry point into `libwmw.so`.

## Findings at a glance

Everything below is recovered from the shipped binary and detailed in its own
section further down:

- **It is not Lua.** `.wmw` is a red herring; the game is a native C++ engine with
  a 165 KB Java shell.
- **The symbol table survived.** 8,618 function symbols, 403 typeinfo (`_ZTI`)
  and 303 vtable (`_ZTV`) objects in `.dynsym`; `.symtab` is stripped but
  `.dynsym` alone carries the developers' own identifiers.
- **Two game namespaces:** `Walaber` (engine) 3,351 symbols,
  `WaterConcept` (game) 2,356 — the rest is statically linked third-party code.
- **Vendored libraries:** libc++ (spelled `std::__ndk1`, i.e. the NDK build),
  SQLite, libxml2, libwebp, minizip.
- **The demangler is finished.** A from-scratch Itanium C++ demangler that
  matches GCC byte-for-byte on the full 6,769-name reference corpus (100%), with
  5,097 game symbols rendering with full parameter lists, and 464/464 agreement
  with Ghidra's own demangling.
- **The class hierarchy is read, not guessed.** RTTI survived: 317 classes,
  281 with recorded bases, 284 polymorphic, 3,003 primary-vtable slots; 184
  per-class headers generated.
- **Decompiled output:** all 8,618 function symbols are bound to a body (median
  144 bytes, p90 740) across 1,467 per-class files. Function boundaries come
  from the ELF symbol table rather than from Ghidra's auto-analysis — see
  "Function boundaries" below. 1,516 further functions exist in the gaps that no
  symbol covers; they keep Ghidra's name.
- **Call targets are named, not numbered.** 64,007 of 66,330 call-site
  placeholders were `func_0x…`/`FUN_…` pointing at PLT stubs; resolving the
  stubs through `.rela.plt` recovers the real callee for 4,765 imports (96%),
  turning them into `operator new`, `fopen`, `Walaber::SceneGraph::~SceneGraph`
  and 28,332 game-symbol calls. See "Call targets and PLT imports".
- **Levels are XML scene graphs**, not a binary format: 636 level files, a
  12-element vocabulary, ~42 objects per level; plus 345 reusable `.hs`
  object prototypes.
- **`water.db` is a real database** (19 tables, 1,014 rows: 671 levels, 46 packs,
  IAP SKUs, achievements) — and partly a program: `DuckSQL1/2` columns store SQL
  text inside the save file.
- **The Java↔native bridge is fully accounted for:** all 44 game-owned native
  methods resolve to `libwmw.so` exports; the 11 unresolved belong to Play
  Billing (9) and FMOD (2), which ship their own libraries.
- **Assets are inventoried without redistribution:** textures, audio and XML
  format vocabularies are catalogued in `out/assets/`.

## Recovered symbol statistics

From a single `libwmw.so` (arm64-v8a):

| Metric | Count |
|---|---|
| `.dynsym` entries | 11,003 |
| Function symbols | 8,618 |
| RTTI typeinfo objects (`_ZTI`) | 403 |
| Virtual tables (`_ZTV`) | 303 |
| Data symbols | 2,058 |
| Functions Ghidra's auto-analysis identifies | 17,375 (superseded; see "Function boundaries") |
| Functions after rebuilding from the symbol table | 9,680 |

Of the mangled function symbols that land in `.text`, 3,351 mention `Walaber`
and 2,356 mention `WaterConcept`. The remainder is libc++, SQLite, libxml2,
libwebp, and minizip, all statically linked into the same object.

Because RTTI survived, the class hierarchy and virtual method layout are directly
recoverable rather than inferred — see `out/symbols/classes.tsv`.

## Repository layout

```
tools/
  wmwtools/
    elf.py            dependency-free ELF64 parser (sections, symbols, relocs,
                      vaddr<->file-offset translation, cstrings)
    cxxfilt.py        Itanium C++ demangler written from scratch
  survey_native.py    generates out/symbols/* from a .so
  rtti.py             RTTI -> class hierarchy, primary vtables, class headers
  dbschema.py         SQLite schema/row-count dumper for the shipped .db files
  apkindex.py         classes.dex + binary AndroidManifest.xml reader, and the
                      JNI bridge between them and libwmw.so
  assetdoc.py         asset-tree inventory + XML format vocabulary recovery
  refdemangle.py      builds the GCC oracle (out/symbols/reference.tsv)
  refdiff.py          localises the first divergence against the oracle
  refprobe.py         asks the oracle about synthetic names
  members.py          classifies every mangled member function, recovers its exact
                      parameter list and the register/offset seeds it implies
  layout.py           raw field-access evidence -> verified class layouts
  fieldnames.py      recover human-readable field names from accessor getters/setters
                     (get*/set*/is*/has*) with conservative filters (range-based owner, base x0/w0, verb/direction + cross-accessor agreement)
  headers.py          verified layouts -> C++ headers + a type index
  check_headers.py    proves each generated header rebuilds to its recovered
                      offsets and sizeof under the C++ ABI (exit != 0 otherwise)
  enumparams.py       scan signatures.tsv for by-value/by-ref candidates whose
                      register word is really an enum, and seed the evidence pass
  enums.py            aggregate EnumScan's constant-compare/store/mask/jump-table
                      evidence into verified enum headers + out/types/enums.tsv
  check_enums.py      proves each recovered enum is attested by >= 2 distinct
                      values from >= 2 evidence functions, or one verified jump
                      table over >= 3 indices (exit != 0 otherwise)
  resolve_refs.py     rewrite func_0x/FUN_ call placeholders in out/src to the
                      real callee by decoding PLT stubs through .rela.plt;
                      --check gates that no resolvable placeholder remains
  apply_signatures.py write the exact parameter types from signatures.tsv back
                      into the decompiled definitions as text, including the
                      template types Ghidra cannot name; --check gates that no
                      applicable definition is left untyped
  shape_source.py     remove compiler-inserted code from the bodies, starting
                      with the -fstack-protector canary (entry load, guard test,
                      __stack_chk_fail and the dead locals); --check gates that
                      no strippable guard is left
  coalesce_locals.py  collapse the decompiler's register copies: in-block copy
                      propagation, single-assignment alias/temporary folding,
                      and dead-copy removal, then drop the freed declarations;
                      --check gates that no coalescible copy is left
  srcstats.py         token metrics over out/src (f_0x, DAT_, param_N, call)
  check_syntax.py     synthesise the declarations out/src is missing from the
                      definitions themselves, then have clang++ -fsyntax-only
                      parse every file and tally the diagnostics; --check gates
                      the tree, --decls-only checks just the generated headers
  test_cxxfilt.py     regression gate: 6,769/6,769 must match GCC (exit != 0
                      on any mismatch)
  test_apply_signatures.py  regression gate for apply_signatures.py's splitter,
                      name formatter and +1/`this` alignment rule
  test_shape_source.py      regression gate for shape_source.py: every stack
                      protector shape, and the bodies that must be left alone
  test_coalesce_locals.py   regression gate for coalesce_locals.py: every copy
                      rule and every case that must be left alone
  ghidra.ps1          non-interactive analyzeHeadless wrapper (the .bat pauses
                      on error and would otherwise hang forever headless)
  ghidra/
    DecompileAll.java headless Ghidra script: rebuilds function boundaries from
                      the ELF symbol table, import the verified layouts, then
                      bulk-decompile and emit a per-class source tree
    FieldScan.java    p-code dataflow over every function, recording each field
                      access with the class, offset and access width
    EnumScan.java     p-code dataflow over every function, recording the
                      constants each enum-typed register is compared against,
                      AND-masked with, stored through, or used to index a
                      jump table
    ProbeSwitch.java  recognize computed-jump sites and dump their p-code, the
                      basis of EnumScan's `switch` evidence channel
    PcodeProbe.java    verifies the p-code API assumptions FieldScan relies on
    ExportSymbols.java exports Ghidra's own demangled symbol names, for
                      cross-checking the local demangler
  wmwtools/
    cxxfilt.py         Itanium demangler, 100% parity with GCC on 6,769 names
    elf.py             ELF reader (sections, symbols, relocations)
    signature.py       exact prototypes recovered from a mangled name
  run_ghidra.ps1      driver for import -> analyse -> decompile
out/
  symbols/
    functions.tsv     address, size, mangled, demangled
    signatures.tsv    address, size, mangled, name, params, kind
    classnames.txt    project class names occurring as parameter types
    reference.tsv     the 6,769-name GCC oracle
    classes.tsv       RTTI class inventory
    gnu_symbols.tsv   Ghidra's demangled names, as a cross-check oracle
    imports.tsv       one row per PLT stub: address, GOT slot, .dynsym index,
                      mangled and resolved callee name
    summary.json      section table + namespace histogram
  types/
    enums.tsv         recovered enum definitions with their evidence
    layouts.tsv       verified class layouts
    typeindex.tsv     header path -> (class, sizeof)
    anchor_classes.txt classes proven by RTTI/constructor/destructor
    _enumparams.tsv   raw enum candidate/seed table (regenerated, not committed)
    _enumraw.tsv      raw constant-compare evidence (regenerated, not committed)
  src/                generated decompiler output, one .cpp per class
    _index.tsv        every recovered function: file, address, size, mangled,
                      demangled, status
    _unclaimed.tsv    symbols that never bound to a Ghidra function
    _unsymbolized.tsv functions Ghidra found with no ELF symbol behind them
  check/
    prelude.h         ambient declarations (Ghidra primitives, ABI helpers, libc,
                      libc++ skeletons, platform symbols) for check_syntax.py
    _generated/       decls.h + preamble.h synthesised from out/src (not tracked)
  rtti/               class hierarchy, vtables, per-class headers, metrics
  db/                 water*.db schemas (.schema.md) and schema.json
  apk/                dex.md (classes, JNI surface, manifest) + apkindex.json
  assets/             asset inventory and XML format vocabulary per format
```

## Recovered source

`out/src/` holds the decompiler output, organised by owning class. **All 8,618
function symbols are bound to a body**, across 1,467 groups:

| | |
|---|---|
| Functions decompiled | 8,230 (8,229 clean, 1 failed) |
| Symbols bound | 8,618 of 8,618 (100%) |
| Bound at their own symbol address | 8,092 addresses |
| Bound by nearest preceding symbol | 138 |
| Symbols unclaimed | 0 |
| Functions moved into C++ namespaces | 3,257 |
| Median function body | 144 bytes (p90 740, max 46,040) |
| Body size identical to ELF `st_size` | 8,089 of 8,092 (99.94%) |

### Function boundaries

The obvious pipeline is to let Ghidra's auto-analysis decide where functions
begin and then attach an ELF symbol to each function it created. That was the
first implementation here, and it recovered only 2,131 of 8,618 symbols. Its
premise turned out to be backwards. Measured on the real data:

| | |
|---|---|
| `.dynsym` symbols with a nonzero `st_size` | 8,616 of 8,618 |
| Symbols that are 4-byte aligned | 8,618 of 8,618 |
| Symbols starting *inside* another symbol's body | **0** |
| Distinct symbol addresses | 8,092 (526 are C1/C2 and D1/D2 alias pairs) |
| `.text` bytes covered by symbols | 3,124,540 of 4,828,328 (64.7%) |
| Ghidra functions starting *inside* a real function | **11,547 of 17,375** |
| Ghidra functions starting on an ELF symbol | 102 |

So the ELF symbol table is the clean, unambiguous oracle, and Ghidra's
boundaries are the unreliable ones — it promotes switch-case targets and
jump-table landings into functions of their own. The fix was to invert the
direction of the mapping: use the symbols to *define* the functions, and keep
Ghidra's analysis only for the parts worth keeping (disassembled bytes, jump
tables, string references). `DecompileAll.java` therefore deletes every
auto-analysis function and rebuilds from `[addr, addr + st_size)`.

That the rebuilt extents agree with the linker's own is the check that matters:
8,089 of 8,092 bodies are byte-identical in length to `st_size`. The three that
differ are a large `update()` that Ghidra stops 560 bytes short of and one 4-byte
body where the address is not an entry point at all.

Two details that cost real time to find:

- **Ghidra rebases a PIE `.so` to `0x100000`.** Every address is then 1 MB above
  the ELF vaddr the symbol table uses. Functions still "work" — the addresses
  land in memory, disassembly succeeds — but they are built over entirely wrong
  bytes and the C looks perfectly plausible. Import with
  `-loader ElfLoader -loader-imagebase 0x0`, and `DecompileAll` refuses to run if
  the executable blocks do not cover the symbol table's whole span.
- **Bound the gap sweep by the next entry, not by the end of the section.** With
  ~1,600 candidates, letting `followFlow` run to the end of `.text` from each
  one takes hours. And only *call* targets are entries: a loop header and every
  switch case are flows too, and treating them as entries shatters one function
  into dozens of stubs.

Symbols sharing an address — the Itanium ABI's `C1`/`C2` and `D1`/`D2` pairs,
526 of them — collapse to a single body carrying the complete-object name, with
the alias recorded alongside it where the two demangle differently.

### Function signatures

The Itanium ABI encodes every parameter type in the symbol, and the demangler
already prints it. `tools/wmwtools/signature.py` recovers that parameter list as
structured data and `tools/sigs.py` writes it to `out/symbols/signatures.tsv`,
along with `out/symbols/classnames.txt` (the 202 project class names that occur
as parameter types).

The parser is reused rather than rewritten: `_parse_params` already walks a
bare-function-type one `<type>` at a time, so subclassing it to record each
top-level type yields exact types with no second grammar to keep in sync. A
capture has to be gated on *type* depth, not on being inside a parameter list —
`_parse_type` recurses to parse a pointee, and without the gate
`P7_JavaVM` comes out as two parameters, `(_JavaVM, _JavaVM*)`.

Because GCC's own rendering of the name is an independent statement of the same
parameter list, it serves as the oracle. `tools/test_sigs.py` checks every C++
symbol in the binary against it:

```
test_cxxfilt: 6769/6769 match
test_sigs: 6769 C++ symbols, 6769 compared, 6769 agree, 0 unparsed (100.000%)
```

So the prototypes are exact, not inferred. The class-name list has to come from
the parameter types rather than from `classes.tsv`: that file is built from RTTI
and therefore only knows *polymorphic* classes, while the commonest parameter
type in the game, `Walaber::Vector2` (366 parameters), has no vtable and is
absent from it.

**The signatures now reach the decompiled bodies.** Ghidra's functions, rebuilt
from symbol extents, have no parameter storage at all: their parameter count never
matches the ELF one, not even once across 8,092 functions. Writing storage through
Ghidra's own signature commands made the output *worse*:

| Attempt | Applied | Result in `out/src` |
|---|---|---|
| `ApplyFunctionSignatureCmd` with the real declaration | 792 | parser merges the return type with the `::`-qualified name; almost everything rejected |
| …parameters only, under a throwaway name | 1,032 | works, but types that Ghidra cannot resolve abort the whole signature |
| …plus `const`/reference fixes and 173 RTTI class types | 1,711 | 2,099 `Unknown calling convention -- yet parameter storage is locked` warnings, 110 return types corrupted to `undefined1 [16]`, parameter names renumbered |
| …plus the 202 class names derived from parameter types | 2,221 | still zero project-class parameters visible in the output |
| …restricted to functions whose arity already matches | **0** | warnings gone, benefit gone too |
| …explicit AArch64 storage, types as `x0`/`w0`/`s0`/`d0` | 1,020 | correct scalars, but class types still invisible |
| …opaque class types actually added to the DataType manager | 1,372 | 202 of 202 resolvable, still only scalars applied |
| …`const` stripped and references passed as pointers | **2,282** | 1,037 functions with real `Walaber::Message *`-style parameters; 0 warnings |

So there were three separate faults, each of which had to be found by measurement
rather than assumption:

- **Storage has to be assigned explicitly.** With no parameters and no storage,
  Ghidra's commands have nothing to write into. `tools/ghidra/DecompileAll.java`
  now allocates AAPCS64 registers itself — `x0`–`x7`/`w0`–`w7` for
  integer-sized and pointer types, `s0`–`s7` for `float`, `d0`–`d7` for `double`
  — and calls `replaceParameters` with `CUSTOM_STORAGE`. Ghidra's own
  `PrototypeModel.getStorageLocations()` is not usable: asked for two `uint`s it
  returns `x0` twice.
- **A datatype is not a datatype until the manager holds it.** `new
  StructureDataType(name, 0, dtm)` only *builds* the object; it is transient until
  `dtm.addDataType` is called, so the first version "created" 202 class types and
  every later lookup still failed. Compounding it, a type created under that name
  is stored at `/Walaber::Message`, and `getDataType("Walaber::Message")` returns
  null while `getDataType("/Walaber::Message")` succeeds — a silent miss that
  looks exactly like a type that was never created. Both are now verified by a
  post-condition count rather than assumed.
- **Ghidra's C parser cannot express two of the things the ABI encodes.** `const`
  is rejected in every position, including plain `const int` ("Can't resolve
  datatype: const"), and a reference is silently degraded to a by-value type,
  which under AArch64 is actively wrong. `tools/sigs.py` therefore writes a second
  column, `gtype`, normalised for the parser — `const` stripped (2,593
  parameters) and `T &` passed as `T *` (3,599) — alongside the exact `params`
  column, and a `notes` column records which rewrite each parameter needed so the
  loss is visible rather than silent. Template types are deliberately *not*
  faked; they still fail, and inventing a stand-in would change their meaning.

The opaque class types are zero-length on purpose. Their real field layouts are
not known yet, and a plausible-but-wrong size would be worse than none, so they
carry the correct name and pointer-ness and nothing more.

The 1,693 prototypes still unparsed are 96% `const`/reference/template
parameters, and those are now handled; what remains is dominated by C++ templates
like `std::__ndk1::basic_string<char, ...>`, where the mangling encodes
instantiation arguments Ghidra cannot name. Ghidra renders a resolved `::` type as
`Walaber__Message` in identifiers, which is a display detail, not a wrong type.

For reference, the remaining parser limits, measured rather than assumed:

- A `::`-qualified type resolves only if the type's *name* contains `::`.
  `Walaber::Vector2 *` works with a flat type of that name; `Vector2 *` under a
  `/Walaber` category path does not.
- Given `undefined WaterConcept::Foo::bar(int)` the parser reads the return type
  greedily as `undefined WaterConcept::Foo::bar` and rejects the declaration.
- `getStorageLocations` does not allocate registers; explicit storage is required.

A note on symbol counts, because the numbers above are easy to conflate.
`.symtab` is **stripped**; every name comes from `.dynsym` (11,003 entries:
8,618 `STT_FUNC`, 2,062 `STT_OBJECT`, plus a handful of `STT_NOTYPE`). Of those,
8,162 are mangled C++ symbols, and all 8,162 were independently confirmed to
agree with Ghidra in both address and spelling.

#### Types without a type system

Ghidra can only apply a type it can *name*, which is exactly the wrong constraint:
the mangling already spells every type, including the libc++ templates Ghidra
cannot resolve. So the prototypes are applied a second way, as plain text, by
`tools/apply_signatures.py`. Writing a type needs no type system, so the
`std::__ndk1::basic_string<char, …>` parameters that defeated every Ghidra
attempt now reach the output:

```
-void Walaber::DatabaseManager::openDatabase(undefined8 param_1)
+void Walaber::DatabaseManager::openDatabase(
+    std::__ndk1::basic_string<char, std::__ndk1::char_traits<char>,
+                              std::__ndk1::allocator<char>> const& param_1)
```

The pass is only safe because the *alignment* is provable. Ghidra numbers the
inferred parameters `param_1…` in AAPCS64 allocation order:

- a **free** function's order is source order, so a definition whose parameter
  count already equals the signature's is a straight positional rename;
- a non-static **member** also receives `this` in `x0`, which the signature
  omits, so its count is exactly one greater — there `param_1` is `this`, so it is
  dropped from the list, renamed in the body, and the survivors shift down.

Any other count difference is left alone. But a count of one greater is not on its
own proof of `this`, and the first two attempts at this pass were both wrong in
ways the output had to expose.

**A hidden return pointer.** A function that returns a class larger than 16 bytes
*also* receives a hidden pointer, in `x8`, which Ghidra models as the first
inferred parameter exactly like `this`:

```
void Walaber::createRenderTexture2D(undefined8 *param_1, undefined4 param_2, …)
```

is a **free** factory returning a `SharedPtr`: `param_1` is the caller's return
buffer, not an object. `members.tsv` cannot separate the two — it files
`std::current_exception` under class `std` with role `method`, and `members.py`
itself warns that a plain `method` might be static. Only `ctor`, `dtor` and
`virtual` are *provably* non-static, and none of those can carry the hidden return
pointer (constructors and destructors return `void`; a virtual returning a class
by value would shift by two, not one).

**A hoisted floating-point parameter.** Even for a provably non-static member the
*order* is only certain while no floating-point parameter is present, because
Ghidra lists those first — `s0` ahead of `x0`:

```
void Walaber::SoundEffectInstance::SoundEffectInstance
               (undefined4 param_1, undefined8 *param_2, …)
{
  …
  *(undefined4 *)((long)param_2 + 0x2c) = param_1;   // the `float` argument
```

`fields.tsv` records a `float` at offset `0x2c`, so `param_1` is the `float` and
`param_2` is `this` — the opposite of what the count suggests. A constructor that
takes *arguments* is excluded as well, even without floating point: one for a
class with virtual bases receives a VTT pointer in `x0` and `this` in `x1`, which
nothing available here separates.

So the shift is applied only where the alignment is certain: a **free or static**
function with no floating-point parameter (positional rename), and a
**non-static member** that either takes no arguments — the `+1` is the hidden
`x0` and nothing else — or is a **virtual** method whose arguments contain no
floating point. A definition is touched only while its parameters still contain
`undefined`, which makes the pass idempotent; `--check` fails if any applicable
definition is left untyped.

| | before | after |
|---|---|---|
| definitions typed from `signatures.tsv` | 0 | 641 |
| …of those, member (`param_1` → `this`) | — | 438 |
| generic `param_N` tokens in `out/src` | 70,864 | 66,674 |

`tools/test_apply_signatures.py` pins the splitter, the name formatter and every
branch of the alignment rule — the zero-argument destructor that must be renamed,
the `method`, the constructor with arguments and the floating-point signature
that must not — on synthetic definitions, so the rule is checked without
touching the output.

### Call targets and PLT imports

Naming functions is not the same as naming the code they call. `DecompileAll`
gives a name to every function that has a symbol, but a shared library built
without `-Bsymbolic` reaches its own exported functions through the **PLT**, and
a PLT stub is not in the symbol table. The decompiler therefore printed every
such call as `func_0x00169310(…)` or `FUN_0016a330()`. That was the single
largest readability defect in the output — and, unlike local names, it is
fully recoverable.

Measured over the tree, 66,330 call-target placeholders fell into exactly two
classes:

| Placeholder target | Refs | Recoverable? |
|---|---|---|
| PLT stub (`.plt`, no symbol) | 64,007 | **yes**, via `.rela.plt` |
| gap function inside `.text` | 2,323 | no symbol exists |

`tools/resolve_refs.py` recovers the first class. The AArch64 PLT stub is a
four-instruction veneer whose first two instructions name the GOT slot it
loads:

```
adrp x16, page(GOT[n])      ; page = (pc & ~0xfff) + (imm << 12)
ldr  x17, [x16, #imm12*8]   ; slot = page + imm12*8
add  x16, x16, #imm
br   x17
```

`adrp`+`ldr` decode to the GOT slot; `.rela.plt` maps that slot to a `.dynsym`
index; `.dynsym` gives the mangled name — the linker's own mapping, not a
heuristic. All 4,765 mapped PLT entries decode to a slot that `.rela.plt`
actually contains (the 4,766th entry is an unpadded tail), so the read is
complete rather than sampled.

The name written at the call site is the demangled symbol with its parameter
list stripped — a *callee* name, so `func_0x00169310(uVar1, …)` reads as
`Walaber::ProgrammaticTexture2D::ProgrammaticTexture2D(uVar1, …)` and
`FUN_00164060(0xc0)` as `operator new(0xc0)`. It also makes the output
*internally consistent*: `std::uncaught_exception` had been emitting
`FUN_0016a330()` while `std::uncaught_exceptions`, calling the same stub, had
already shown `__cxa_uncaught_exceptions()`; both now agree.

| | before | after |
|---|---|---|
| unresolved call placeholders | 66,330 | 2,323 |
| …of those, resolvable via PLT | 64,007 | 0 |
| …of those, no symbol (gap function) | 2,323 | 2,323 |
| game-symbol call sites named | — | 28,332 |
| third-party call sites named | — | 35,675 |

The 2,323 that remain point at functions in the 35% of `.text` no symbol
covers; they cannot be named from the symbol table because they have no name
there. `out/symbols/imports.tsv` records the whole PLT map (stub address, GOT
slot, `.dynsym` index, mangled and resolved name) as the evidence, and
`resolve_refs.py --check` re-derives it and fails if any resolvable placeholder
survives. It is a post-pass over generated output, so it is idempotent.

A callee name is the qualified name only. `signature().name` keeps a member's
cv-qualifier (`Walaber::Property::asString const`), so the resolver strips a
trailing `const`/`volatile` (and any `&`/`&&`) before writing it; otherwise the
`const` lands mid-expression and the call no longer reads as C++. Because the
mangled symbol is the stable key, the pass is also *self-repairing*: it reads the
previous `imports.tsv` back, recomputes each name under the current rule, and
rewrites any stale name it finds. Fixing the rule therefore fixed the 82 distinct
names already written across 361 files, without a revert.

### Field layouts

Class layouts are recovered from the code that *uses* them, since the binary
records no field table. `tools/ghidra/FieldScan.java` runs a forward dataflow
pass over each function's p-code, tracking affine offsets from `x0` and from each
parameter register, through `LOAD`/`STORE` and stack spills, invalidating
AAPCS64 caller-saved registers at calls. That yields 39,348 tagged accesses, which
`tools/layout.py` turns into 3,048 fields across 450 classes.

Three things had to be got right, and each is a place a plausible-looking method
gives the wrong answer:

- **Static and non-static cannot be told apart from a mangling.** `FieldScan`
  therefore seeds `x0` under *both* hypotheses and tags every access `this` or
  `static`, rather than picking one. `layout.py` keeps the `this` reads as
  establishing evidence and uses `static` reads only to corroborate a field
  another function already established. Getting this backwards silently
  reconstructs every class in the binary with the layout of whatever it was
  handed.
- **A name is not automatically a class.** Owner extraction attributes a
  namespace's free functions to the namespace, so bare `Walaber` accumulated a
  "layout" that was really whatever those read from their first argument. A
  layout is emitted only for a name with positive evidence of being a type: a
  typeinfo in the RTTI, a constructor or destructor, or use as a parameter. 125
  names were withheld on this ground and are listed in the run output rather than
  silently dropped. Note that the two obvious tests both fail: real classes have
  nested classes, and plenty of real classes are static-only.
- **A recovered offset is authoritative; the inferred type is not.** If the
  binary addressed offset 1, the field is a byte, whatever the access width
  suggested. `headers.py` narrows 32 such types rather than bending the offset to
  fit them.

A layout is emitted only if it is internally consistent. A negative offset means
the evidence points into the middle of the object — a base subobject, or a
pointer to a member — which no flat struct can express; fields reaching past an
independently recovered `sizeof` means the two disagree about which object this
is. 8 classes were withheld for these reasons.

The result is checked rather than assumed. `tools/check_headers.py` walks every
generated header, applies the alignment rules a real compiler would, and confirms
each field lands at the correct offset and each struct measures its recovered sizeof (including accessor-named fields). headers.py accepts --names/--no-names and records provenance for named fields; check_headers.py validates accessor names against out/types/fieldnames.tsv. **325 headers, 2,616 field declarations, 0 disagreements.**
`DecompileAll.java` then rebuilds the same structures in Ghidra at explicit
offsets with packing disabled, and verifies all 325 measure their recovered size
before decompiling.

The payoff is visible in the output. `Walaber::Color`, recovered as four bytes at
offsets 0-3, decompiles as the channel arithmetic it is:

```c
in_s1 = (p3->f_0x4 - p3->f_0x0) / 255.0;
```

Those numbers are measured against a no-layout control run of the same pipeline,
not asserted:

| | no layouts | layouts |
| --- | --- | --- |
| signatures applied | 2,282 | 2,450 |
| signatures unparseable | 1,693 | 1,576 |
| field accesses rendered as `f_0x` | 0 | 4,884 |
| `DAT_` placeholders | 8,272 | 8,262 |
| generic `param_N` parameters | 74,258 | 70,864 |

The control is a fresh import of the same binary with only the layouts
skipped (`-nolayout`), so the single variable is whether the recovered
layouts are installed. Against it, 168 more signatures resolve and no
category regresses, and 4,884 field accesses render as `f_0x<offset>`
member reads instead of raw pointer casts. Both columns reproduce with
`tools/srcstats.py` (token counts over `out/src`, comment lines excluded),
and `out/src` itself is the layout-enabled run of that pipeline.

A separate audit confirms every line mentioning a field references a
*proven* class: none of the 125 withheld layouts leak into the output.
Field *names* are partially recovered from accessor methods
(`get*`/`set*`/`is*`/`has*`) when they unambiguously identify a single
(class, offset) with consistent verb/direction and cross-accessor
agreement. `tools/fieldnames.py` produces `out/types/fieldnames.tsv`
(class, offset, name, votes, accessors) and filters to proven layouts;
ambiguous or conflicting cases fall back to `f_0x<offset>`. `headers.py`
and the Ghidra import apply these names with provenance, and the remaining
`f_0x` placeholders are the obvious route to recovering the rest.

### Enums

Enumerations are recovered the same way field layouts are: read what the machine
code *does* with the type, and declare only what the evidence supports.
`tools/enumparams.py` walks the validated signatures for parameters whose word
is a value type -- an enum reaches the AArch64 ABI exactly like an `int` or a
flag field, so a by-value parameter of one of the 208 known class names is either
a small struct or an enum. It emits a candidate table (`out/types/_enumparams.tsv`:
524 such parameters across 456 functions), and `tools/ghidra/EnumScan.java` runs
the same forward dataflow as `FieldScan` over every function, tracking which
parameters are value-typed and recording the constants they are compared
against, stored through a reference, AND-masked with, or used to index a
jump table. That yields 215 evidence rows for 54 distinct types -- 65 of them
`switch` rows recovered from the 36 computed-jump sites ProbeSwitch found in
the seed functions.

`tools/enums.py` turns the evidence into verdicts, with the repo's usual
two-independent-observations rule:

- **cmp/store** constants are candidate enumerators, kept only if
  `0 <= v <= 0x7fffffff`. Addresses and the `-1` sentinel (0xffffffff) are not
  enumerators, and a lone `cmp e, #0` is a null/boolean test that proves nothing.
- **and masks** are candidate flag members, kept only if a power of two.
  Byte-rounding masks like `0xff`/`0xff00` are the saved-game serializer's
  bit-pack parsing and are dropped.
- **switch** rows come from jump-table dispatch. A backward slice on the
  computed-jump site recognizes the AArch64 switch idiom
  (`adrp`+`add`-on the table base, a bounds check, `ldrsw` the entry, `add`
  the case address, indirect branch) and only emits a row when the table's
  entry for index `i` branches to one of Ghidra's resolved flows on a
  contiguous run -- so a *single* function dispatching over >= 3 indices is
  proof by itself.
- A **values** enum is proven with >= 2 distinct values from >= 2 distinct
  functions, *or* one function's verified switch over >= 3 distinct indices;
  a **flags** enum with >= 2 power-of-two masks.

The 9 that clear the bar:

| enum | kind | recovered members | evidence |
|---|---|---|---|
| `Walaber::TextureInMemoryColorspace` | values | `0 1 2 3` | 5 functions |
| `Walaber::VertexColorBlendMode` | values | `0 1` | 5 functions |
| `Walaber::Language` | values | `0..17` | 3 jump tables + 6 functions |
| `Walaber::UTF8Helper::Shift_Key` | values | `0 1` | 2 functions |
| `WaterConcept::ConsiderSameAll` | values | `1 4 7` | 2 functions |
| `WaterConcept::ConsiderSameAlgae` | values | `1 4 5` | 2 functions |
| `WaterConcept::ConsiderSameRockOutline` | values | `1 4` | 3 functions |
| `WaterConceptConstants::StorylineType` | values | `0 1 2 3 4 6` | jump table + 2 functions |
| `Walaber::ValueTweaker::ValueDataType` | values | `0..5` | 1 jump table |

`out/types/enums.tsv` records each definition with its evidence, and
`tools/check_enums.py` is the gate: it re-derives the verdicts from the raw
evidence and fails if `enums.tsv`, the header set, or any member value
disagrees. Headers whose class was previously mis-filed as a one-`int` struct
(a value-typed enum read through a reference is `*(int*)p`, indistinguishable
from a 4-byte field) are retracted and rewritten as the enum they really are --
`Walaber/Language.h` and `Walaber/VertexColorBlendMode.h` here.

What is still thin, honestly. Most of the 54 candidates never get proven, and
the reasons are visible in the evidence rather than assumed: enum-typed
parameters are usually *forwarded* to a virtual or function-pointer call within
a few instructions, so the constant compare happens in a callee this pass does
not follow; jump tables are only reachable when the switch index derives from a
by-value seed *parameter* -- three of the five inlined draw routines dispatch on
a struct field and correctly yield nothing; and by-ref enums -- the
`PlayerDataSerializer::*Info` tags -- are only ever compared through their
pointer, which stays unproven. The enumerator *names* themselves are not encoded
anywhere in the binary; `E_<Name>_<ord>` placeholders stand in until the
re-inference step (README item 3).

### Source shaping

Ghidra lifts machine code, so the bodies carry work the *compiler* did and the
source never had. `tools/shape_source.py` deletes the largest and most
mechanical of those artefacts and nothing else.

The stack protector (`-fstack-protector`) is the first target. It appears in
2,513 of the 8,229 bodies as a canary loaded from the thread-control block at
entry and compared at every exit:

```c
lVar1 = tpidr_el0;
lStack_38 = *(long *)(lVar1 + 0x28);          /* entry   */
...
if (*(long *)(lVar1 + 0x28) == lStack_38) {   /* exit    */
  return;
}
__stack_chk_fail();
return;
```

It is pure ABI. The pass removes the two entry lines, the guard test, the
`__stack_chk_fail` call and the now-dead locals, leaving the body's own
`return` — that `return` is the function's, the `if` around the abort is the
compiler's. **2,434** guards come out this way (2,513 → 79), shrinking
`out/src` by 19,500 lines across 485 files.

The pattern is not always the tidy one. The compiler is free to invert the
test, so the abort is usually *inside* the block:

```c
if (*(long *)(lVar1 + 0x28) != lStack_38) {
  __stack_chk_fail();
  return;
}
return;
```

and `__stack_chk_fail` — declared `noreturn`, but not always typed so by Ghidra
— can be assigned, handed a spurious argument or cast:
`uVar3 = __stack_chk_fail();`, `__stack_chk_fail(uVar5);`,
`plVar4 = (long *)__stack_chk_fail();`. The canary also lives in a saved-register
array as often as a scalar (`alStack_38[2] = *(long *)(lVar1 + 0x28);`). All of
these are handled, and `tools/test_shape_source.py` pins each shape.

The pass is deliberately conservative, and the 79 it leaves are the two reasons
it must be:

- **A shared local.** `lVar1 = tpidr_el0` reuses a local the decompiler also
  gives a real value elsewhere, or the canary slot is reused for a live local.
  Slicing the guard out would then delete a live definition, so the whole body
  stays. A function is rewritten only when the canary and the TCB local are
  provably dead afterwards.
- **A shared exit label.** The abort sits behind a `LAB_…:` that other `goto`s
  reach; removing the block would strand them.

`--check` fails while any strippable guard remains, and the pass is idempotent:
a stripped body no longer matches.

#### Register copies

The stack protector gone, the next machine shape is the *register copy*. Ghidra
models each ARM64 register as a variable, so one source local often travels
through two or three of them, and a spilled value is written to a slot and read
straight back:

```c
uVar5 = (ulong)(abStack_40[0] >> 1);
uVar3 = uVar5;                 /* register alias */
...
uStack_98 = param_4;           /* argument spilled to a slot */
uVar7 = uStack_98;
```

`tools/coalesce_locals.py` removes them by substitution, under two rules that
keep it sound where the decompiler reuses a name:

- **Copy propagation, within a basic block.** Walking each straight-line run of
  plain statements, `x = y;` (both locals, no cast) records that `x` currently
  *is* `y`; later reads of `x` in the same run are rewritten to `y`. The alias
  is dropped the moment `y` is reassigned, and the whole environment is cleared
  at any control line — `if`, `while`, `goto`, `return`, a label, a brace — so
  an alias never crosses a branch. Locals whose address is taken are excluded
  entirely, so a call in the run can never observe one behind the rewrite.
- **Single-assignment folding, across blocks.** Where a name is assigned exactly
  once in the whole body, a copy can be folded even across control flow. If the
  source is *never* assigned (a local or a parameter) the destination is simply
  that value; if the source is a single-use temporary, the two names are
  collapsed into one. Either way the destination must not be read before the
  copy, because a stack slot the decompiler reused would hold another variable
  there.

Finally, any copy left with no reader is a dead store — Ghidra materialises the
values a `-O2` build leaves in registers — and is deleted, and declarations no
longer mentioned are dropped. In all, **1,094** copies are removed and **586**
alias reads folded, freeing **833** declarations across 273 files; `out/src`
loses 1,927 lines. `tools/test_coalesce_locals.py` pins every rule *and* every
case that must be refused (a branch between source and read, a reassignment, an
address-taken local, a cast, a pointer write such as `*p = …` that only *reads*
`p`). `--check` is a gate, and the pass is idempotent.

If-converted branches, the sub-register `CONCAT`/`SUB`/`ZEXT` noise and the C++
exception landing pads are the next targets for the same treatment.

### Quality caveats

Read this before treating `out/src/` as source.

- **Parameter and return types are mostly inferred.** Return types are never in
  the mangling, and only the 3,091 functions that carry a prototype (2,450
  through Ghidra, 641 as text; see "Function signatures") have recovered
  parameter types — there the types are exact. Everywhere else Ghidra's type
  propagation frequently mis-identifies them — a method taking
  `(Fluids*, ParticleDescription const&, int, bool&)` is emitted as taking
  `(_xmlNode*, char*)`. Where a prototype is present, trust it and the mangled
  comment; otherwise trust only the mangled comment.
- **Local variable names, comments and macros never survive compilation.**
  Everything inside a function body must be re-inferred; see the goal above.
- **Prototype comments can be misattributed** to an unrelated function.
- **Bodies are complete but types are still inferred.** Every symbol-bound body
  now spans its full `st_size` (8,089 of 8,092 exactly), so truncation is no
  longer a concern. 1,129 bodies are 16 bytes or shorter; those are the AArch64
  veneer thunks and small wrappers, which is what they are in the original.
- **1,516 functions have no ELF symbol** and appear as `FUN_...`/`func_0x...`
  calls inside other bodies. They live in the 35% of `.text` no symbol covers
  and are reachable only through call sites and relocation targets. They are
  inventoried in `out/src/_unsymbolized.tsv`. These are the *only* remaining
  `FUN_...`/`func_0x...` call targets: calls that go through a PLT stub — 96%
  of all call sites — are named from `.rela.plt` by `tools/resolve_refs.py`
  (see "Call targets and PLT imports").
- **`out/rtti/hierarchy.tsv` currently over-reports classes:** its 392 rows
  include 75 pointer/fundamental typeinfos (`char*`, `bool`, …) that are RTTI
  objects, not classes — the real class count is 317 (filter pending).
- This is decompiled machine code, not the original source. It does not yet
  compile as-is, though "how far from compiling" is now a measured number rather
  than an impression — see "The syntax gate" below.

## The syntax gate

Everything above measures what the tree *says*. This section measures what a
compiler *makes of it*. `tools/check_syntax.py` points `clang++ -fsyntax-only`
at every generated `.cpp` and tallies the diagnostics, so that "is this
source?" stops being a matter of opinion and becomes a number to drive the
remaining shaping work.

It cannot simply include the headers, because there are none: a body names
types and calls functions that are defined two directories away and were never
declared. So the missing declarations are *synthesised from the definitions
themselves*. An out-of-line definition — `void A::B::f(...) { }` — is only
well-formed once `A::B` has been declared and `f` matches a declaration in it,
so the tool walks every `/* ok address 0x… */` block, parses the definition
header and rebuilds exactly the class and namespace declarations those headers
require:

- a member definition contributes a member declaration to its owning class (the
  owner comes from `out/types/members.tsv`, which records the class of all 6,742
  classified members);
- a namespace-scope definition contributes a namespace declaration;
- a class's `f_0x<offset>` members come from the recovered layouts
  (`out/types/fields.tsv`), so the field reads the bodies already contain resolve;
- a type name the definitions mention but nothing declares becomes an opaque
  `struct` — Ghidra's flattened `Walaber__Vector2` is one of these — and a name
  used with `<…>` becomes a variadic template, so its arity never has to be
  guessed;
- the constructor/destructor return type Ghidra writes (`void A::A(...)`) is
  dropped in the declaration, because the declaration has to be legal C++ even
  where the body is not yet.

Everything the bodies name that is *not* the game — Ghidra's `undefined8`
primitives, the ABI helpers, libc and libm, the libc++ primary templates, the
GLES/XML/NEON/FMOD symbols the `.so` calls by their bare C names — is declared
in the hand-written `out/check/prelude.h`. `_Datum`, a type that accepts any
use, stands in for a data global the binary never named (`DAT_00634ed4`).

Those declarations compile clean: **408 classes, 272 member declarations, 141
opaque structs, 7,489 definitions parsed** (740 headers unparsed, 1,683
template-qualified definitions skipped because a template member cannot be
declared without the template's definition), **7,365 placeholder globals**, and
**0 errors** in the generated `decls.h` itself. The bodies are then checked
freestanding — `-target aarch64-linux-gnu -ffreestanding -nostdinc -nostdinc++`
— so that nothing depends on the host's headers.

The baseline over the whole tree:

| | |
|---|---|
| Files checked | 1,467 |
| Files with at least one error | 1,459 |
| Diagnostics | 74,002 |
| Trajectory | 94,265 → 84,570 (prelude) → 80,691 (ctor/dtor shape) → 79,870 (symbol regex) → 75,922 (static-form members) → **74,002** (input-register rebinding) |
| Declarations compiled against | **0 errors** |

The number is not a defect count, and the tool is careful to say so. Its own
largest buckets are **not** defects in the game:

- **10,756** *implicit instantiation of undefined template* and **1,715** *too
  many template arguments*: the libc++ primary templates are declared, not
  defined, and their arity is guessed.
- **6,973** *no matching function*, **1,895** *too many arguments to function
  call* (down from 4,817) and **2,130** *too few*: the call/definition arity
  divergence, now largely decided. Ghidra binds the callee's `w0` as its
  object parameter but leaves the argument the binary passes in the next
  register as an unbound input register (`in_w1`), so the definition declares
  one parameter where the call site passes two:
  `SoundManager::soundCountForGroup(uVar17, 0x79)` against
  `soundCountForGroup(int p0)`. `tools/shape_inw.py` re-binds those
  registers: an `in_wN` where N equals the parameter count is appended —
  AAPCS64 leaves no choice, the register *is* argument N+1 — while an
  `in_x0` preceding every bound parameter is inserted at the front only when
  call sites of the same qualified name corroborate the extra argument,
  because some bodies read `x0` while their call sites display no object at
  all. What remains is the residue: duplicate definitions of one member that
  decompile with divergent shapes, and call sites Ghidra printed without the
  argument.
- **3,922** *use of undeclared identifier*: overwhelmingly a *cascade*. When a
  definition fails to parse, its own parameter names (`p0`, `p1`, `param_1`)
  are not in scope in the body, and every use of them is reported.
- **2,334** *call to non-static member function without an object argument*,
  down from **17,182**: a decision, not a defect, and now decided. Ghidra
  writes every method call in static form and the tree contains zero
  object-style (`->`/`.`) calls, so member declarations are synthesised
  `static` unless the body names `this` (the ~438 definitions
  `apply_signatures` shifted onto the implicit receiver) or the member is a
  constructor, destructor or operator, none of which can be static. The
  declarations still compile with 0 errors and no *invalid use of `this`*
  diagnostic appeared — the guard holds.

The buckets that *are* real shape the next pass. Two defects the gate named
are now decided: **0** constructor or destructor definitions carry a return
type or a parameter (695 reshaped by `tools/shape_ctor_dtor.py`), and the
arity divergence above is largely rebound (`tools/shape_inw.py`, 764
definitions). What remains real: definitions of two distinct overloads that
flatten to a single signature (`stold` of a `char` string and of a `wchar_t`
string both become `stold(byte *, long *)`, so the second definition
collides; **7** of them newly visible now that both overloads are declared),
the libc++ template work, and the type mismatches the arity errors used to
mask — a call whose argument count now agrees gets its argument types
checked for the first time.

Run it with:

```powershell
py tools\check_syntax.py --clang "C:\Program Files\LLVM\bin\clang++.exe"
py tools\check_syntax.py --decls-only           # just the synthesised declarations
py tools\check_syntax.py --only WaterConcept    # one subtree
py tools\check_syntax.py --dump errors.tsv      # one row per diagnostic
py tools\check_syntax.py --check                # gate: non-zero while any remain
```

## Class hierarchy and virtual tables

`tools/rtti.py` reconstructs the class model directly from the binary. Because
the Itanium ABI records each class's base list, offsets and virtual-ness inside
its own `typeinfo` object, the hierarchy is *read*, not inferred:

| | |
|---|---|
| Classes recovered | 317 (of 403 `_ZTI` symbols: 75 name pointer/fundamental types, 11 are `__cxxabiv1` internals) |
| With a recorded base list | 281 |
| Base-class edges | 343 |
| Polymorphic classes | 284 |
| Virtual function slots (primary vtables) | 3,003 |
| Generated game-class headers | 184 |

By namespace: `Walaber` 127 classes / 944 slots, `WaterConcept` 61 / 1,298,
`std` 127 / 756, `ndk` 2 / 5.

Output lands in `out/rtti/`:

- `hierarchy.tsv` — every class with its bases, offsets and virtual-inheritance flags
- `vtables.tsv` — every primary-vtable slot with its owning symbol
- `headers/` — a compilable-looking `.hpp` per game class: base list, then
  virtual methods in slot order, annotated with the target address
- `summary.json` — the metrics above, plus the demangler coverage figures

Two things make this non-trivial and are worth knowing if you extend it:

- The library is **PIE**, so every pointer in `.data.rel.ro` is a relocation
  that must be resolved through `.rela.dyn` (`R_AARCH64_RELATIVE` is an addend;
  `ABS64` and `GLOB_DAT` are `dynsym[symidx].value + addend`). Reading the raw
  file offset instead yields garbage.
- A vtable must be anchored at a **fixed position** — offset-to-top, then the
  typeinfo pointer, then the slots. Scanning forward for typeinfo pointers runs
  straight into the neighbouring class's vtable, because they are laid out back
  to back, and silently attributes another class's methods to this one. This was
  a real bug during development; `WaterConcept::AlgaeHider` now correctly shows
  26 slots beginning with its own destructor.

Only **primary** vtables are emitted. Secondary vtables and virtual-inheritance
thunks (`_ZThn*`, `_ZTv*`) are skipped: they duplicate base-class slots, and the
inheritance graph already records the bases.

## Data formats

The game is mostly data-driven, and all of it is recoverable.

### `water.db` and friends — SQLite

Three databases ship under `assets/Data`. `tools/dbschema.py` dumps their
structure (`out/db/*.schema.md`); no row *contents* are recorded.

| File | Tables | Rows | Role |
|---|---|---|---|
| `water.db` | 19 | 1,014 | full game |
| `water-Lite.db` | 8 | 732 | reduced build |
| `water-demo.db` | 7 | 41 | demo build |

The schema is plain, unindexed SQLite — no views, no triggers, no explicit
indexes, `journal_mode=delete`. The interesting tables:

| Table | Rows | Notes |
|---|---|---|
| `LevelInfo` | 671 | one row per level: `Filename`, `ParTime`, `Stars`, `Type`, unlock state |
| `LevelPackInfo` | 46 | packs, `StarsRequired`, texture references, IAP linkage |
| `CollectibleInfo` | 60 | `Basename` + `Unlocked` + `HasViewed` |
| `FoodInfo` | 27 | `Basename`, `ObjectName`, `GroupName` |
| `IAPInfo` | 13 | per-store SKU ids: `Internal`, `iOS`, `Google`, `Amazon` |
| `Achievements` | 45 | points, hidden flag, localized description pairs |
| `HubInfo` | 5 | world-map nodes; note `DuckSQL1/2` and `ItemSQL1/2` columns that hold **SQL text** |
| `ADSettings`, `Settings`, `PlayerData`, `AllieSongs`, `MusicCollectInfo`, `LOWInfo` | 3–24 | settings, event counters, music unlocks, letter-of-the-week content |
| `AllieChallengeInfo`, `CrankyChallengeInfo`, `MysteryChallengeInfo` | 12–24 | challenge metadata |

The `DuckSQL1`/`ItemSQL1` columns are worth flagging: the database stores
queries inside itself, so the save file is partly a program, not just data.

### Level and object XML

Levels are **XML scene graphs**, not the binary format the `.wmw` extension
suggests. `tools/assetdoc.py` recovers the vocabulary exactly (`out/assets/`),
recording element paths, occurrence counts, and attribute *value shapes* rather
than values, so the format is documented without redistributing level layouts.

636 level files, all parsing cleanly, with a vocabulary of only 12 element paths:

```
/Objects                              636    the root container
/Objects/Object                    27,043    name=...;  ~42 objects per level
/Objects/Object/AbsoluteLocation  27,043    value = two floats
/Objects/Object/Properties        27,043
/Objects/Object/Properties/Property 81,195   name=, value= (float|int|string|asset path|...)
/Objects/Room                        636    one per level
/Objects/Region                         1    brCell / tlCell as number lists
/Objects/Lighting                       1    filename = asset path
```

The 345 `assets/Objects/*.hs` files share the same shape but describe reusable
`InteractiveObject` prototypes rather than level instances — collision
`Shapes`/`Shape`/`Point` polygons (2,096 points), `Sprites` with `gridSize`,
`angle`, `isBackground`, and `DefaultProperties` name/value pairs. Two files
additionally carry `UVs`/`VertIndices`, i.e. custom mesh geometry.

`assets/Script/WC.txt` is a **TSV localization table** (not a script) with 14
language columns, despite the `Script/` directory it lives in.

## The Java layer and the JNI bridge

`tools/apkindex.py` parses `classes.dex` and the binary `AndroidManifest.xml`
directly (`out/apk/dex.md`); no Android tooling was available in this
environment.

| | |
|---|---|
| `classes.dex` | 165 KB, 151 classes, 1,364 methods |
| Package / version | `com.disney.WMW` 1.18.9 (`versionCode` 66) |
| SDK | min 26, target 33 |
| Permissions | `INTERNET`, `ACCESS_NETWORK_STATE`, `ACCESS_WIFI_STATE`, `com.android.vending.BILLING` |
| Activity | `com.disney.WMW.WMWActivity`, plus a `wheresmywater://` deep link |
| Native methods | 55, of which **44/44 game-owned resolve to `libwmw.so` exports** |

That last row is the useful one: the Java layer is genuinely thin. Every
`com.disney.*` native method is bound by ordinary static JNI name mangling
(`Java_com_disney_common_BaseActivity_notifyProductInfo`, and so on — JNI
escapes `_` as `_1` and `/` as `_`). The 11 unresolved natives belong to
bundled third-party SDKs that ship their own libraries: Play Billing
(`com.android.billingclient.api.zzah`, 9) and FMOD audio
(`org.fmod.FMODAudioDevice`, 2).

`libwmw.so` also exports `JNI_OnLoad` and 48 `Java_*` symbols, so the bridge is
fully accounted for in both directions.

## The demangler

`tools/wmwtools/cxxfilt.py` is a from-scratch implementation of the Itanium C++
ABI mangling grammar. It is needed because the analysis runs headless in places
where `c++filt` is not available, and because the pipeline needs structured output
rather than a flat string.

It covers nested names, function and data manglings, template parameter and
argument lists, substitution-compressed back-references, builtin types, CV
qualifiers, ref qualifiers, operator overloads, converting constructors, the
destructor's `D0`/`D1`/`D2` encodings, non-virtual and virtual thunks, and
`J` argument packs — stored as a single template argument exactly as GCC
numbers them, then expanded element-by-element (with reference collapsing) by
`Dp` pack expansions. Template arguments that are full C++ expressions —
`enable_if` conditions built from `sr` qualified names, binary operators,
casts, `sizeof` and call expressions — are parsed and rendered the way
cp-demangle.c prints them, including GCC's operand-parenthesisation rules.
It also demangles the RTTI symbols (`_ZTI`, `_ZTV`,
`_ZTS`), which is what makes the class inventory possible.

It is deliberately **fault-tolerant**: a single malformed symbol degrades to a
`raw:` prefix instead of aborting a bulk run.

**Status: complete.** Accuracy is measured against an oracle built from Ghidra's
bundled GCC 4.1 `c++filt`, which resolves all 6,769 mangled names in the binary
and agrees with GCC 2.24 on every one. `tools/refdemangle.py` builds that oracle,
`tools/refdiff.py` localises the first divergence, and `tools/refprobe.py`
asks it about synthetic names. `tools/test_cxxfilt.py` runs the whole comparison
as a regression gate and exits non-zero on any mismatch — run it before touching
`cxxfilt.py`.

| Reference set (6,769 names) | |
|---|---|
| Match GCC | 6,769 (100%) |
| Differ | 0 |
| Left mangled | 0 |

| 5,097 game-namespace symbols | |
|---|---|
| Render to any readable form | 5,097 (100%) |
| Render with a full parameter list | 5,097 (100%) |
| Left mangled | 0 |

Cross-checked against the 464 symbols Ghidra had already demangled in its own
symbol table, the local demangler's name agrees on 464, differs on 0, and
leaves 0 unparsed. The comparison runs both names through a normaliser that
folds presentation differences (Ghidra's `std::__ndk1::` inline spelling,
`unsigned_int` for `unsigned int`, `Language_const` for `Language const`); the
sample itself is biased toward `std::__ndk1` internals — precisely the hardest
substitution cases — and excludes every ordinary `Walaber`/`WaterConcept`
method, so the absolute numbers understate the demangler on game code.

For anything load-bearing, prefer the mangled name in the source comments over
either demangler.

## Pipeline

```powershell
$so  = '<extracted-apk>\lib\arm64-v8a\libwmw.so'
$apk = '<extracted-apk>'

# 0. demangler regression gate (6,769/6,769 must match GCC)
py tools\test_cxxfilt.py

# 1. survey the binary -> out/symbols/
py tools\survey_native.py $so

# 2. import + analyse into a Ghidra project (run once, ~4 min)
#    -ProjectName picks a scratch project; use a fresh one, because headless
#    runs save the program and stale functions persist.
.\tools\ghidra.ps1 -Mode import -Rest @($so) -ProjectName 'wmwb'

# 3. decompile -> out/src/ (uses the same project)
.\tools\ghidra.ps1 -Mode script -Rest @('libwmw.so', "$PWD/out/symbols/functions.tsv", "$PWD/out/src", '60', '0') -ProjectName 'wmwb'

# 3b. name the call targets: rewrite func_0x/FUN_ PLT placeholders in out/src
#     and write out/symbols/imports.tsv (idempotent; run after any re-import)
py tools\resolve_refs.py $so
py tools\resolve_refs.py $so --check      # gate: 0 resolvable placeholders left

# 3c. write the exact parameter types from signatures.tsv into out/src
#     (idempotent; run after any re-import)
py tools\apply_signatures.py
py tools\apply_signatures.py --check      # gate: 0 applicable definitions left
py tools\test_apply_signatures.py         # gate: formatter + alignment rule

# 3d. strip compiler-inserted code (the -fstack-protector canary) from the
#     bodies (idempotent; run after any re-import)
py tools\shape_source.py
py tools\shape_source.py --check          # gate: 0 strippable guards left
py tools\test_shape_source.py             # gate: every guard shape

# 3e. collapse the decompiler's register copies (idempotent; run after 3d)
py tools\coalesce_locals.py
py tools\coalesce_locals.py --check       # gate: 0 coalescible copies left
py tools\test_coalesce_locals.py          # gate: every copy rule

# 3f. synthesise the declarations out/src is missing and compile-check every
#     body with clang++ -fsyntax-only; reports the diagnostics by kind
#     (needs clang; see "The syntax gate")
py tools\check_syntax.py --clang "<llvm>\bin\clang++.exe"
py tools\check_syntax.py --decls-only     # just the synthesised declarations

# 4. class hierarchy, vtables, per-class headers -> out/rtti/
py tools\rtti.py $so out\rtti

# 5. SQLite schemas -> out/db/
py tools\dbschema.py "$apk\assets\Data\water.db" "$apk\assets\Data\water-Lite.db" "$apk\assets\Data\water-demo.db" --out out\db

# 6. dex + manifest + JNI bridge -> out/apk/
py tools\apkindex.py $apk --out out\apk

# 7. asset inventory + XML format vocabulary -> out/assets/
py tools\assetdoc.py $apk --out out\assets
```

Steps 3b–3d and 4–7 need only Python and run in seconds; only steps 2–3 need
Ghidra.
`tools/ghidra.ps1 -Mode script -Script ExportSymbols.java ...` regenerates
`out/symbols/gnu_symbols.tsv`, which step 4 consumes as a demangler
cross-check.

`tools/ghidra.ps1` exists because `analyzeHeadless.bat` ends with a `pause` on
error, which blocks forever in a non-interactive shell and looks exactly like a
hang. The wrapper feeds the batch file an empty stdin so `pause` returns
immediately, and always surfaces the exit code. It also redirects Ghidra's
stdout to `out/ghidra/<tag>.console.txt`: the analyzers are extremely chatty on
an AArch64 shared library (the GCC exception-table analyzer alone emits tens of
thousands of `Failed to disassemble` lines), and unfiltered that reads like a
frozen process. Progress is echoed from the Ghidra log instead.

Do not re-import into a project that a previous decompile run has touched:
headless runs save the program, so any functions created by an earlier run
persist. Re-import into a fresh project when in doubt — although
`DecompileAll` now deletes every function before rebuilding, so it is
effectively idempotent.

## What is not in this repository

- **The APK and its extracted assets** (textures, audio, level data, art). These
  remain Disney's copyrighted material and are not redistributed. `run_ghidra.ps1`
  takes a path to an APK you supply.
- **Ghidra analysis logs**, which are large and machine-specific.

## Legal

This repository contains analysis tooling and notes produced by running static
analysis against a copy of the application. No game assets, artwork, audio, or
proprietary source are redistributed. Decompiled function bodies are included as
the output of a local analysis run and remain the property of their original
copyright holders. If you own this repository's contents and want the decompiled
output removed, open an issue and it will be taken down.