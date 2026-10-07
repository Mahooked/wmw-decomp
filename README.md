# Where's My Water? G�� full decompilation

Reverse-engineering notes, tooling, and recovered C++ for **Where's My Water? 1.18.9**
(Android, `com.disney.WMW`).

## The goal

**The full source code, exactly as the developers had it** G�� every function in
compilable C++ with its original names, types and file organisation, verified by
rebuilding against the shipped `libwmw.so`. A symbol map or a folder of
decompiler pseudocode is a milestone, not the destination.

The game makes this unusually tractable: the bulk of it is a **native C++ engine**
(`lib/arm64-v8a/libwmw.so`, 7.1 MB) that shipped **unstripped**, so thousands of
real class, method, and RTTI names survive in `.dynsym`. That turns "decompiling a
closed-source app" into something much closer to "reading a disassembly with the
original identifier table attached". Names are the easy half: bodies still have to
be lifted out of AArch64 machine code, and everything the compiler did not encode
G�� local variable names, comments, macros, original file layout G�� has to be
re-inferred.

## Where we are

| Subsystem | State | Coverage |
|---|---|---|
| ELF survey and symbol naming | **done** | 11,003 `.dynsym` entries; all 8,618 function symbols named and demangled |
| Itanium demangler at GCC parity | **done** | 6,769/6,769 reference names (100%, 0 diffs), regression-tested |
| Class hierarchy + vtables (RTTI) | **done** | 317 classes, 343 base edges, 284 polymorphic, 3,003 virtual slots, 184 headers |
| Data formats (SQLite, level XML, assets, dex/JNI) | **done** | schemas and vocabularies under `out/` |
| Decompiled, named function bodies | **done** | 8,618 / 8,618 symbols bound (100%), 1,467 files |
| Exact function prototypes recovered | **done** | 6,769/6,769 C++ symbols validated against GCC's own rendering; 9,952 parameters |
| Struct/field layouts, signatures applied to bodies | **partly done** | 2,282 functions carry exact AAPCS64-allocated parameters, 1,037 of them with real project-class types; 325 class layouts recovered from p-code field-access evidence and imported into Ghidra (see "Function signatures") |
| Enum definitions | **partly done** | first 8 value-typed enums recovered from constant-compare/store/mask evidence, verified by a gate (see "Enums") |
| Original local names, file layout, comments | not encodable | never present in the binary; must be re-inferred |
| Rebuild-equivalence check (recompile and compare) | not started | this is the definition of done |

### Remaining work

1. **Recover type definitions.** Function signatures are exact (they are encoded
   in the manglings), validated against GCC, and now applied to 2,282 decompiled
   bodies. Class field layouts are now recovered too G�� 325 of them, each proven
   to rebuild to its recovered `sizeof` under the C++ ABI G�� and the first 8
   enums have been lifted out of the constant compares the binary performs on
   them (see "Enums"). Typedefs and the remaining field names still have to be
   read out of the code that uses them, and fields are currently named
   `f_0x<offset>` because the binary never recorded their names. See "Function
   signatures".
2. **Re-shape decompiler output into source-shaped code.** The emitted C is
   machine-shaped: if-converted branches, spill/reload noise, register aliases.
3. **Re-infer local identifiers and file organisation.** These were never in the
   binary; they have to be reconstructed from behaviour and class structure.
4. **Verify by recompilation.** Rebuilding and comparing against the shipped
   binary is the only honest completion test.

### Milestones (20 commits)

- `5defcdf`G��`febcf71` G�� ELF tooling, decompiled source tree, class model, data
  formats, JNI bridge.
- `c77d06c`G��`e49d4fc` G�� demangler iterated against a GCC oracle from first cut
  to **100% parity** (substitutions, templates, expressions, thunks) plus a
  regression gate.
- `0d307ad` G�� `out/src` regenerated with the final names, README stats refreshed.
- Function boundaries rebuilt from the ELF symbol table: 2,131 G�� **8,618
  symbols bound (100%)**, 641 G�� 1,467 files. See "Function boundaries".
- Exact function prototypes recovered and validated against GCC's own rendering
  (6,769/6,769). Applying them to the decompiled bodies is blocked on field
  layouts; see "Function signatures".

## What the game turned out to be

The file extension on this game is `.wmw`, which invites the assumption that it is
some kind of Lua script bundle (the original Flash-adjacent `Where's My Water?`
community tooling is Lua-oriented). **It is not.** There is no Lua bytecode in the
APK. `assets/Script/WC.txt` is a localization table, not a script.

| | |
|---|---|
| Language | C++ (AArch64) + a thin Java shell |
| Engine namespaces | `Walaber` (engine), `WaterConcept` (game) |
| Java layer | one thin `classes.dex` (165 KB) G�� `com.disney.WMW.WMWActivity` |
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
  `WaterConcept` (game) 2,356 G�� the rest is statically linked third-party code.
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
  from the ELF symbol table rather than from Ghidra's auto-analysis G�� see
  "Function boundaries" below. 1,516 further functions exist in the gaps that no
  symbol covers; they keep Ghidra's name.
- **Levels are XML scene graphs**, not a binary format: 636 level files, a
  12-element vocabulary, ~42 objects per level; plus 345 reusable `.hs`
  object prototypes.
- **`water.db` is a real database** (19 tables, 1,014 rows: 671 levels, 46 packs,
  IAP SKUs, achievements) G�� and partly a program: `DuckSQL1/2` columns store SQL
  text inside the save file.
- **The JavaG��native bridge is fully accounted for:** all 44 game-owned native
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
recoverable rather than inferred G�� see `out/symbols/classes.tsv`.

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
  enums.py            aggregate EnumScan's constant-compare/store/mask evidence
                      into verified enum headers + out/types/enums.tsv
  check_enums.py      proves each recovered enum is attested by >= 2 distinct
                      values from >= 2 evidence functions (exit != 0 otherwise)
  test_cxxfilt.py     regression gate: 6,769/6,769 must match GCC (exit != 0
                      on any mismatch)
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
                      AND-masked with, or stored through
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
boundaries are the unreliable ones G�� it promotes switch-case targets and
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
  the ELF vaddr the symbol table uses. Functions still "work" G�� the addresses
  land in memory, disassembly succeeds G�� but they are built over entirely wrong
  bytes and the C looks perfectly plausible. Import with
  `-loader ElfLoader -loader-imagebase 0x0`, and `DecompileAll` refuses to run if
  the executable blocks do not cover the symbol table's whole span.
- **Bound the gap sweep by the next entry, not by the end of the section.** With
  ~1,600 candidates, letting `followFlow` run to the end of `.text` from each
  one takes hours. And only *call* targets are entries: a loop header and every
  switch case are flows too, and treating them as entries shatters one function
  into dozens of stubs.

Symbols sharing an address G�� the Itanium ABI's `C1`/`C2` and `D1`/`D2` pairs,
526 of them G�� collapse to a single body carrying the complete-object name, with
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
capture has to be gated on *type* depth, not on being inside a parameter list G��
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
| GǪparameters only, under a throwaway name | 1,032 | works, but types that Ghidra cannot resolve abort the whole signature |
| GǪplus `const`/reference fixes and 173 RTTI class types | 1,711 | 2,099 `Unknown calling convention -- yet parameter storage is locked` warnings, 110 return types corrupted to `undefined1 [16]`, parameter names renumbered |
| GǪplus the 202 class names derived from parameter types | 2,221 | still zero project-class parameters visible in the output |
| GǪrestricted to functions whose arity already matches | **0** | warnings gone, benefit gone too |
| GǪexplicit AArch64 storage, types as `x0`/`w0`/`s0`/`d0` | 1,020 | correct scalars, but class types still invisible |
| GǪopaque class types actually added to the DataType manager | 1,372 | 202 of 202 resolvable, still only scalars applied |
| GǪ`const` stripped and references passed as pointers | **2,282** | 1,037 functions with real `Walaber::Message *`-style parameters; 0 warnings |

So there were three separate faults, each of which had to be found by measurement
rather than assumption:

- **Storage has to be assigned explicitly.** With no parameters and no storage,
  Ghidra's commands have nothing to write into. `tools/ghidra/DecompileAll.java`
  now allocates AAPCS64 registers itself G�� `x0`G��`x7`/`w0`G��`w7` for
  integer-sized and pointer types, `s0`G��`s7` for `float`, `d0`G��`d7` for `double`
  G�� and calls `replaceParameters` with `CUSTOM_STORAGE`. Ghidra's own
  `PrototypeModel.getStorageLocations()` is not usable: asked for two `uint`s it
  returns `x0` twice.
- **A datatype is not a datatype until the manager holds it.** `new
  StructureDataType(name, 0, dtm)` only *builds* the object; it is transient until
  `dtm.addDataType` is called, so the first version "created" 202 class types and
  every later lookup still failed. Compounding it, a type created under that name
  is stored at `/Walaber::Message`, and `getDataType("Walaber::Message")` returns
  null while `getDataType("/Walaber::Message")` succeeds G�� a silent miss that
  looks exactly like a type that was never created. Both are now verified by a
  post-condition count rather than assumed.
- **Ghidra's C parser cannot express two of the things the ABI encodes.** `const`
  is rejected in every position, including plain `const int` ("Can't resolve
  datatype: const"), and a reference is silently degraded to a by-value type,
  which under AArch64 is actively wrong. `tools/sigs.py` therefore writes a second
  column, `gtype`, normalised for the parser G�� `const` stripped (2,593
  parameters) and `T &` passed as `T *` (3,599) G�� alongside the exact `params`
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
the evidence points into the middle of the object G�� a base subobject, or a
pointer to a member G�� which no flat struct can express; fields reaching past an
independently recovered `sizeof` means the two disagree about which object this
is. 8 classes were withheld for these reasons.

The result is checked rather than assumed. `tools/check_headers.py` walks every
generated header, applies the alignment rules a real compiler would, and confirms
each field lands at the correct offset and each struct measures its recovered sizeof (including accessor-named fields). headers.py accepts --names/--no-names and records provenance for named fields; check_headers.py validates accessor names against out/types/fieldnames.tsv. **325 headers, 2,616 field declarations, 0 disagreements.**
recovered `sizeof`: **325 headers, 2,616 field declarations, 0 disagreements.**
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
| signatures unparseable | 1,684 | 1,567 |
| field accesses rendered as `f_0x` | 0 | 16,718 |
| `DAT_` placeholders | 6,087 | 6,077 |
| generic `param_N` parameters | 4,296 | 4,171 |

The control run is what makes this readable. Re-importing the binary into a fresh
project also repairs call targets that the previous, repeatedly-patched project had
left as `func_0x0016ace0`, which is why the committed tree differs so widely from a
clean run. Against the control G�� where the layouts are the only variable G�� 168 more
signatures resolve and no category regresses. A separate audit confirms all 15,222
lines mentioning a field reference a *proven* class: none of the 125 withheld
Field *names* are now partially recovered from accessor methods (`get*`/`set*`/`is*`/`has*`) when they unambiguously identify a single (class, offset) with consistent verb/direction and cross-accessor agreement. `tools/fieldnames.py` produces `out/types/fieldnames.tsv` (class, offset, name, votes, accessors) and filters to proven layouts; ambiguous or conflicting cases fall back to `f_0x<offset>`. `headers.py` and Ghidra import apply these names with provenance.
 
 
 
accessors are the obvious route to recovering them.

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
against, stored through a reference, or AND-masked with. That yields 150
evidence rows for 54 distinct types.

`tools/enums.py` turns the evidence into verdicts, with the repo's usual
two-independent-observations rule:

- **cmp/store** constants are candidate enumerators, kept only if
  `0 <= v <= 0x7fffffff`. Addresses and the `-1` sentinel (0xffffffff) are not
  enumerators, and a lone `cmp e, #0` is a null/boolean test that proves nothing.
- **and masks** are candidate flag members, kept only if a power of two.
  Byte-rounding masks like `0xff`/`0xff00` are the saved-game serializer's
  bit-pack parsing and are dropped.
- A **values** enum is proven with >= 2 distinct values from >= 2 distinct
  functions; a **flags** enum with >= 2 power-of-two masks.

The 8 that clear the bar:

| enum | kind | recovered members | evidence |
|---|---|---|---|
| `Walaber::TextureInMemoryColorspace` | values | `0 1 2 3` | 5 functions |
| `Walaber::VertexColorBlendMode` | values | `0 1` | 5 functions |
| `Walaber::Language` | values | `0 17` | 6 functions |
| `Walaber::UTF8Helper::Shift_Key` | values | `0 1` | 2 functions |
| `WaterConcept::ConsiderSameAll` | values | `1 4 7` | 2 functions |
| `WaterConcept::ConsiderSameAlgae` | values | `1 4 5` | 2 functions |
| `WaterConcept::ConsiderSameRockOutline` | values | `1 4` | 3 functions |
| `WaterConceptConstants::StorylineType` | values | `3 6` | 2 functions |

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
not follow; switch dispatch over a wide enum uses jump tables instead of `cmp`
chains (AArch64 `cmp` against an immediate also decodes to a flagged subtract,
which is captured but fires rarely); and by-ref enums -- the
`PlayerDataSerializer::*Info` tags -- are only ever compared through their
pointer, which stays unproven. The enumerator *names* themselves are not encoded
anywhere in the binary; `E_<Name>_<ord>` placeholders stand in until the
re-inference step (README item 3).

### Quality caveats

Read this before treating `out/src/` as source.

- **Parameter and return types are inferred, not recovered.** Function names,
  arity and class membership come from the symbol table and are trustworthy.
  Ghidra's type propagation frequently mis-identifies them G�� a method taking
  `(Fluids*, ParticleDescription const&, int, bool&)` is emitted as taking
  `(_xmlNode*, char*)`. Trust the mangled comment, not the C signature.
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
  inventoried in `out/src/_unsymbolized.tsv`.
- **`out/rtti/hierarchy.tsv` currently over-reports classes:** its 392 rows
  include 75 pointer/fundamental typeinfos (`char*`, `bool`, GǪ) that are RTTI
  objects, not classes G�� the real class count is 317 (filter pending).
- This is decompiled machine code, not the original source. It does not
  compile as-is and never will without hand-reconstruction.

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

- `hierarchy.tsv` G�� every class with its bases, offsets and virtual-inheritance flags
- `vtables.tsv` G�� every primary-vtable slot with its owning symbol
- `headers/` G�� a compilable-looking `.hpp` per game class: base list, then
  virtual methods in slot order, annotated with the target address
- `summary.json` G�� the metrics above, plus the demangler coverage figures

Two things make this non-trivial and are worth knowing if you extend it:

- The library is **PIE**, so every pointer in `.data.rel.ro` is a relocation
  that must be resolved through `.rela.dyn` (`R_AARCH64_RELATIVE` is an addend;
  `ABS64` and `GLOB_DAT` are `dynsym[symidx].value + addend`). Reading the raw
  file offset instead yields garbage.
- A vtable must be anchored at a **fixed position** G�� offset-to-top, then the
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

### `water.db` and friends G�� SQLite

Three databases ship under `assets/Data`. `tools/dbschema.py` dumps their
structure (`out/db/*.schema.md`); no row *contents* are recorded.

| File | Tables | Rows | Role |
|---|---|---|---|
| `water.db` | 19 | 1,014 | full game |
| `water-Lite.db` | 8 | 732 | reduced build |
| `water-demo.db` | 7 | 41 | demo build |

The schema is plain, unindexed SQLite G�� no views, no triggers, no explicit
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
| `ADSettings`, `Settings`, `PlayerData`, `AllieSongs`, `MusicCollectInfo`, `LOWInfo` | 3G��24 | settings, event counters, music unlocks, letter-of-the-week content |
| `AllieChallengeInfo`, `CrankyChallengeInfo`, `MysteryChallengeInfo` | 12G��24 | challenge metadata |

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
`InteractiveObject` prototypes rather than level instances G�� collision
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
(`Java_com_disney_common_BaseActivity_notifyProductInfo`, and so on G�� JNI
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
`J` argument packs G�� stored as a single template argument exactly as GCC
numbers them, then expanded element-by-element (with reference collapsing) by
`Dp` pack expansions. Template arguments that are full C++ expressions G��
`enable_if` conditions built from `sr` qualified names, binary operators,
casts, `sizeof` and call expressions G�� are parsed and rendered the way
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
as a regression gate and exits non-zero on any mismatch G�� run it before touching
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
sample itself is biased toward `std::__ndk1` internals G�� precisely the hardest
substitution cases G�� and excludes every ordinary `Walaber`/`WaterConcept`
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

# 4. class hierarchy, vtables, per-class headers -> out/rtti/
py tools\rtti.py $so out\rtti

# 5. SQLite schemas -> out/db/
py tools\dbschema.py "$apk\assets\Data\water.db" "$apk\assets\Data\water-Lite.db" "$apk\assets\Data\water-demo.db" --out out\db

# 6. dex + manifest + JNI bridge -> out/apk/
py tools\apkindex.py $apk --out out\apk

# 7. asset inventory + XML format vocabulary -> out/assets/
py tools\assetdoc.py $apk --out out\assets
```

Steps 4G��7 need only Python and run in seconds; only steps 2G��3 need Ghidra.
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
persist. Re-import into a fresh project when in doubt G�� although
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