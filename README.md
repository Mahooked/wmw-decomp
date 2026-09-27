# Where's My Water? — static analysis and decompilation

Reverse-engineering notes, tooling, and recovered C++ for **Where's My Water? 1.18.9**
(Android, `com.disney.WMW`).

The point of this repository is that the game is **not** compiled to an opaque blob.
The bulk of the game is a **native C++ engine** (`lib/arm64-v8a/libwmw.so`, 7.1 MB)
that shipped **unstripped**, so thousands of real class, method, and RTTI names
survive in `.dynsym`. That turns "decompiling a closed-source app" into something
much closer to "reading a disassembly with the original identifier table attached".

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

## Recovered symbol statistics

From a single `libwmw.so` (arm64-v8a):

| Metric | Count |
|---|---|
| `.dynsym` entries | 11,003 |
| Function symbols | 8,618 |
| RTTI typeinfo objects (`_ZTI`) | 394 |
| Virtual tables (`_ZTV`) | 294 |
| Data symbols | 2,058 |
| Functions Ghidra identifies | 17,375 |

Of the mangled function symbols that land in `.text`, 3,351 mention `Walaber`
and 1,746 mention `WaterConcept`. The remainder is libc++, SQLite, libxml2,
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
  ghidra.ps1          non-interactive analyzeHeadless wrapper (the .bat pauses
                      on error and would otherwise hang forever headless)
  ghidra/
    DecompileAll.java headless Ghidra script: bulk-decompiles functions and
                      emits a per-class source tree
    ExportSymbols.java exports Ghidra's own demangled symbol names, for
                      cross-checking the local demangler
  run_ghidra.ps1      driver for import -> analyse -> decompile
out/
  symbols/
    functions.tsv     address, size, mangled, demangled
    classes.tsv       RTTI class inventory
    gnu_symbols.tsv   Ghidra's demangled names, as a cross-check oracle
    summary.json      section table + namespace histogram
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

`out/src/` holds the decompiler output, organised by owning class. 2,131
functions were named from the ELF symbol table and decompiled across 568 groups:

| | |
|---|---|
| Functions decompiled | 2,131 (2,129 clean, 2 failed) |
| Named by exact address | 102 |
| Named by nearest preceding symbol | 2,029 |
| Functions moved into C++ namespaces | 1,146 |
| Real class files | 160 (`Walaber` 84, `WaterConcept` 68, `const_Walaber` 6, `const_WaterConcept` 2) |
| Median function body | 148 instructions |

The symbol table is larger than 2,131 because Ghidra's function boundaries
only coincide with the ELF symbol table at 102 addresses. That is inherent to
the binary rather than a defect in this pipeline: Ghidra derives functions from
call targets and jump tables, so it reports 17,375 functions, of which roughly
9,300 are 16-byte thunks, and 91% of real ELF symbols land *inside* a Ghidra
function body rather than at its start. Binding each function to the nearest
preceding unclaimed symbol recovers 20x more names than exact matching, and
claiming each symbol at most once keeps two functions from sharing a name.
`_unclaimed.tsv` lists what did not bind, so the gap is explicit rather than
silent.

A note on symbol counts, because the numbers above are easy to conflate.
`.symtab` is **stripped**; every name comes from `.dynsym` (11,003 entries:
8,618 `STT_FUNC`, 2,062 `STT_OBJECT`, plus a handful of `STT_NOTYPE`). Of those,
8,162 are mangled C++ symbols, and all 8,162 were independently confirmed to
agree with Ghidra in both address and spelling.

### Quality caveats

Read this before treating `out/src/` as source.

- **Parameter and return types are inferred, not recovered.** Function names,
  arity and class membership come from the symbol table and are trustworthy.
  Ghidra's type propagation frequently mis-identifies them — a method taking
  `(Fluids*, ParticleDescription const&, int, bool&)` is emitted as taking
  `(_xmlNode*, char*)`. Trust the mangled comment, not the C signature.
- **Prototype comments can be misattributed** to an unrelated function.
- **Bodies are frequently incomplete.** 1.8% of functions decompile to 4
  instructions or fewer (median 148, but the long tail reaches 16,148). Small
  bodies are usually thunks, wrappers, or template instantiations the
  optimiser folded away.
- This is decompiled machine code, not the original source. It does not
  compile as-is and never will without hand-reconstruction.

## Class hierarchy and virtual tables

`tools/rtti.py` reconstructs the class model directly from the binary. Because
the Itanium ABI records each class's base list, offsets and virtual-ness inside
its own `typeinfo` object, the hierarchy is *read*, not inferred:

| | |
|---|---|
| Classes recovered | 392 (of 394 `_ZTI` symbols; 2 are `__cxxabiv1` internals) |
| With a recorded base list | 281 |
| Base-class edges | 343 |
| Polymorphic classes | 284 |
| Virtual function slots (primary vtables) | 3,003 |
| Generated game-class headers | 184 |

By namespace: `Walaber` 127 classes / 944 slots, `WaterConcept` 61 / 1,298,
`std` 118 / 658, global 84 / 98, `ndk` 2 / 5.

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
`J` argument packs (spliced into the enclosing argument list, as GCC does). It
also demangles the RTTI symbols (`_ZTI`, `_ZTV`, `_ZTS`), which is what makes
the class inventory possible.

It is deliberately **fault-tolerant**: a single malformed symbol degrades to a
`raw:` prefix instead of aborting a bulk run.

Accuracy is measured against an oracle built from Ghidra's bundled GCC 4.1
`c++filt`, which resolves all 6,769 mangled names in the binary and agrees with
GCC 2.24 on every one. `tools/refdemangle.py` builds that oracle,
`tools/refdiff.py` localises the first divergence, and `tools/refprobe.py`
asks it about synthetic names.

| Reference set (6,769 names) | |
|---|---|
| Match GCC | 6,589 (97.3%) |
| Differ | 180 (2.7%) |
| Left mangled | 0 |

The 180 remaining differences are almost all one construct: **defaulted
function parameters** (`Dp`). Where GCC expands `__emplace_unique_key_args`'s
trailing `Dp` argument into the full parameter list it defaults to, the local
demangler stops at the first parameter. A smaller group is libc++ internal
traits (`std::__ndk1::enable_if<__is_forward_iterator<...>>`) surfacing as
template arguments, plus a few `__bit_iterator` instantiations.

The older game-symbol figures below are **stale** — they predate the thunk,
pack, and default-argument work and have not been regenerated yet:

| 5,097 game-namespace symbols (stale) | |
|---|---|
| Render to any readable form | 4,582 (89.9%) |
| Render with a full parameter list | 3,738 (73.3%) |
| Left mangled | 515 (10.1%) |

Cross-checked against the 464 symbols Ghidra had already demangled in its own
symbol table, the local demangler's name agrees on 77, differs on 71, and leaves
316 unparsed. Treat that figure as a **lower bound on quality**: the sample is
almost entirely `std::__ndk1` internals, i.e. precisely the hardest case, and it
excludes every ordinary `Walaber`/`WaterConcept` method. Ghidra's own rendering
is not a clean oracle either — it stores name-only strings and contains visible
errors of its own (`unsigned_int`, `int_const&`, a dropped `std::__ndk1::`
qualifier).

For anything load-bearing, prefer the mangled name in the source comments over
either demangler.

## Pipeline

```powershell
$so  = '<extracted-apk>\lib\arm64-v8a\libwmw.so'
$apk = '<extracted-apk>'

# 1. survey the binary -> out/symbols/
py tools\survey_native.py $so

# 2. import + analyse into a Ghidra project (run once, ~6 min)
.\tools\ghidra.ps1 -Mode import -Rest @($so)

# 3. decompile -> out/src/
.\tools\ghidra.ps1 -Mode script -Rest @('libwmw.so', "$PWD/out/symbols/functions.tsv", "$PWD/out/src", '60', '0')

# 4. class hierarchy, vtables, per-class headers -> out/rtti/
py tools\rtti.py $so out\rtti

# 5. SQLite schemas -> out/db/
py tools\dbschema.py "$apk\assets\Data\water.db" "$apk\assets\Data\water-Lite.db" "$apk\assets\Data\water-demo.db" --out out\db

# 6. dex + manifest + JNI bridge -> out/apk/
py tools\apkindex.py $apk --out out\apk

# 7. asset inventory + XML format vocabulary -> out/assets/
py tools\assetdoc.py $apk --out out\assets
```

Steps 4–7 need only Python and run in seconds; only steps 2–3 need Ghidra.
`tools/ghidra.ps1 -Mode script -Script ExportSymbols.java ...` regenerates
`out/symbols/gnu_symbols.tsv`, which step 4 consumes as a demangler
cross-check.

`tools/ghidra.ps1` exists because `analyzeHeadless.bat` ends with a `pause` on
error, which blocks forever in a non-interactive shell and looks exactly like a
hang. The wrapper feeds the batch file an empty stdin so `pause` returns
immediately, and always surfaces the exit code.

Do not re-import into a project that a previous decompile run has touched:
headless runs save the program, so any functions created by an earlier run
persist and block recovery of the real ones. Re-import into a fresh project when
in doubt.

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
