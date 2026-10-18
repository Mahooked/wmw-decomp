Add the clang -fsyntax-only gate for the recovered tree.

- Add tools/check_syntax.py: scans out/src, rebuilds declarations from definitions (classes, members, namespace funcs, opaque structs, platform symbols, fold helpers), generates decls.h + preamble.h, runs clang++ -fsyntax-only freestanding per file.
- Add out/check/prelude.h: ambient declarations (primitives, ABI helpers, libc, libc++ skeletons, platform symbols, _Datum). _generated/ is gitignored.
- Baseline: 1,467 files, 1,460 with errors, 84,570 diagnostics; synthesised declarations compile with 0 errors. Structural defects: ctor/dtor return types (605), dtor with parameters (210) across 249 files.
- README: document gate, measurements, the small formatting fix.
