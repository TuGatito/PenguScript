# PenguScript documentation

Everything about the language, in two languages: **English** and **Spanish**.
Every document exists twice, with identical structure and examples.

## The three documents

| Document | Answers | Español |
| --- | --- | --- |
| [LANGUAGE.md](LANGUAGE.md) | How do I write this construct, and what does it become in C? Every construct, its semantics, its lowering and its diagnostics. | [LANGUAGE.es.md](LANGUAGE.es.md) |
| [PENGUNIC.md](PENGUNIC.md) | How do I write PenguScript that is safe, idiomatic and fast? Toolchain, style, memory, tests, libraries, bindings, performance. | [PENGUNIC.es.md](PENGUNIC.es.md) |
| [STDLIB.md](STDLIB.md) | Which standard module do I use, what is it for, and where is its API? | [STDLIB.es.md](STDLIB.es.md) |

If you are new to the language, read `LANGUAGE.md` first, then
`PENGUNIC.md` chapter 0 for the house rules. If you are looking for a module,
go straight to `STDLIB.md`.

## Generated API reference

Every module of the standard library has a page generated from its `##`
comments by `psc doc`:

* [docs/api/](api/) — one page per module, plus an index.
* Regenerate with `tools/docs/gen_api.sh`; verify with
  `tools/docs/gen_api.sh --check`.

The pages are committed so the links work on GitHub and in a checkout. CI
regenerates them and fails if the committed tree is stale.

## Other references

| Document | Contents |
| --- | --- |
| [CARMEN.md](CARMEN.md) | `std.carmen`, the binary struct format. |
| [EXTERNAL_MODULES.md](EXTERNAL_MODULES.md) | How bindings and C satellites are organised. |
| [LIBRARIES.md](LIBRARIES.md) / [LIBRARIES.es.md](LIBRARIES.es.md) | How to build, test and publish a library that installs with `psc add`. |
| [LSP.md](LSP.md) | The language server: hover, definition, references, rename, diagnostics. |
| [WASM.md](WASM.md) | Building for WebAssembly. |
| [CROSS_COMPILE.md](CROSS_COMPILE.md) | Native cross builds: Linux ARM64, macOS ARM64, Windows (best effort). |
| [BUILD_CACHE.md](BUILD_CACHE.md) | Incremental builds, cache key, `psc gc`, timings and reproducibility. |
| [COVERAGE.md](COVERAGE.md) | `psc test --coverage` mapped to `.pengu` lines. |
| [SANITIZERS.md](SANITIZERS.md) | ASan, UBSan and TSan profiles. |
| [DEBUGGER.md](DEBUGGER.md) | `psc debug`, the DAP adapter, breakpoints, pretty printers and fiber backtraces. |
| [psc/](psc/) | Compiler internals: AST, semantic analysis, codegen, modules. |
| [psc/AUDITORIA_0.33.0.md](psc/AUDITORIA_0.33.0.md) | Audit and phased plan for 0.33 (Spanish). |
| [psc/F7_MULTITU.md](psc/F7_MULTITU.md) | F7 implementation plan: per-module codegen units and parallel `cc`. |

## Keeping the docs honest

The documentation is checked like code:

```console
$ tools/docs/gen_api.sh --check                 # generated API is current
$ python3 tools/docs/validate_docs.py docs/*.md  # fences, tables, TOC, examples
$ tools/docs/check_links.sh docs                # relative links resolve
```

`validate_docs.py` compiles every `pengu` block with `psc check`, so an example
that stops compiling fails the build. Blocks marked `pengu-fragment` are
deliberate fragments (a statement, a declaration out of context) and are not
compiled.

## Versioning

The documents state the `psc` version they describe (currently **0.55.2**).
When the language changes, the same pull request updates:

1. the reference (`LANGUAGE.md` + `.es.md`),
2. the manual (`PENGUNIC.md` + `.es.md`) if practice changed,
3. the catalogue (`STDLIB.md` + `.es.md`) if a module changed,
4. `docs/api/` (regenerated).
