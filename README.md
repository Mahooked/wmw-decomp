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

Method distribution across the two engine namespaces: `Walaber` 1,448,
`WaterConcept` 1,343. The remainder is libc++ and vendored third-party code.

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
  ghidra/
    DecompileAll.java headless Ghidra script: bulk-decompiles functions and
                      emits a per-class source tree
  run_ghidra.ps1      driver for import -> analyse -> decompile
out/
  symbols/
    functions.tsv     address, size, mangled, demangled
    classes.tsv       RTTI class inventory
    summary.json      section table + namespace histogram
  src/                generated decompiler output (added once the run completes)
```

## The demangler

`tools/wmwtools/cxxfilt.py` is a from-scratch implementation of the Itanium C++
ABI mangling grammar. It is needed because the analysis runs headless in places
where `c++filt` is not available, and because the pipeline needs structured output
rather than a flat string.

It covers nested names, function and data manglings, template parameter and argument
lists, substitution-compressed back-references, builtin types, CV qualifiers,
ref qualifiers, operator overloads, converting constructors, and the destructor's
`D0`/`D1`/`D2` encodings. It also demangles the RTTI symbols (`_ZTI`, `_ZTV`,
`_ZTS`), which is what makes the class inventory possible.

It is deliberately **fault-tolerant**: a single malformed symbol degrades to a
`raw:` prefix instead of aborting a bulk run. Two known edge cases, both cosmetic:

- deeply nested `std::__ndk1` template substitutions can be reconstructed in a
  technically-valid but not byte-identical-to-`c++filt` form
- symbols with a corrupt embedded length prefix fall back to `raw:` output

Neither affects symbol identification, which is all the pipeline relies on.

## Pipeline

```powershell
# 1. survey the binary -> out/symbols/
py tools\survey_native.py <path-to>\libwmw.so

# 2. import + analyse + decompile (needs a JDK and Ghidra on PATH or in GHIDRA_INSTALL_DIR)
tools\run_ghidra.ps1 -So <path-to>\libwmw.so
```

The Ghidra stage is a long run (the full pass is thousands of functions and takes
roughly half an hour). It writes one `.cpp` per recovered class into `out/src/`,
with the original mangled symbol retained as a comment on each function so any
name can be traced back to the binary.

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
