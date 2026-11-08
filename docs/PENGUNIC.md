# The Pengunic Manual

How to write PenguScript that is safe, idiomatic and fast: the engineering
manual for the language implemented by `psc` 0.53.7.

It is the *practice* document of the documentation set:

| Document | Answers |
| --- | --- |
| [LANGUAGE.md](LANGUAGE.md) | How do I write this construct, and what does it become in C? |
| **PENGUNIC.md** (this file) | How do I write PenguScript that is safe, idiomatic and fast? |
| [STDLIB.md](STDLIB.md) | Which standard module do I use, and where is its API? |

Spanish: [PENGUNIC.es.md](PENGUNIC.es.md).

<!-- toc -->
- [0. The Pengunic contract](#0-the-pengunic-contract)
  - [0.1 The six principles](#01-the-six-principles)
  - [0.2 When the principles collide](#02-when-the-principles-collide)
  - [0.3 The three habits](#03-the-three-habits)
  - [0.4 How to use this manual](#04-how-to-use-this-manual)
  - [0.5 What this manual is not](#05-what-this-manual-is-not)
- [Part I — Project and toolchain](#part-i-project-and-toolchain)
- [1. Installing `psc` and setting up the editor](#1-installing-psc-and-setting-up-the-editor)
  - [1.1 What you need](#11-what-you-need)
  - [1.2 The commands you will actually type](#12-the-commands-you-will-actually-type)
  - [1.3 Editor and LSP](#13-editor-and-lsp)
  - [1.4 Formatting](#14-formatting)
  - [1.5 Version pinning](#15-version-pinning)
- [2. Anatomy of a project](#2-anatomy-of-a-project)
  - [2.1 `pengu.toml`](#21-pengutoml)
  - [2.2 Directory layout](#22-directory-layout)
  - [2.3 What the build produces](#23-what-the-build-produces)
- [3. Dependencies](#3-dependencies)
  - [3.1 Declaring them](#31-declaring-them)
  - [3.2 The command set](#32-the-command-set)
  - [3.3 The lock file](#33-the-lock-file)
  - [3.4 C libraries shipped as satellites](#34-c-libraries-shipped-as-satellites)
- [4. The build pipeline](#4-the-build-pipeline)
  - [4.1 Stages](#41-stages)
  - [4.2 Dead code elimination](#42-dead-code-elimination)
  - [4.3 Profiles and flags](#43-profiles-and-flags)
  - [4.4 Measuring the build](#44-measuring-the-build)
- [Part II — Style and structure](#part-ii-style-and-structure)
- [5. Naming](#5-naming)
  - [5.1 Files, directories and modules](#51-files-directories-and-modules)
  - [5.2 Types](#52-types)
  - [5.3 Functions (`weave`)](#53-functions-weave)
  - [5.4 Methods and rituals](#54-methods-and-rituals)
  - [5.5 Variables, constants, fields, generics](#55-variables-constants-fields-generics)
  - [5.6 Reserved prefixes](#56-reserved-prefixes)
- [6. Module layout and documentation](#6-module-layout-and-documentation)
  - [6.1 Canonical order](#61-canonical-order)
  - [6.2 Size and cohesion](#62-size-and-cohesion)
  - [6.3 Imports](#63-imports)
  - [6.4 Documentation comments](#64-documentation-comments)
  - [6.5 What `psc doc` publishes](#65-what-psc-doc-publishes)
- [7. Expressions over statements](#7-expressions-over-statements)
  - [7.1 Return the expression](#71-return-the-expression)
  - [7.2 `judge` is a value](#72-judge-is-a-value)
  - [7.3 Comprehensions instead of accumulators](#73-comprehensions-instead-of-accumulators)
  - [7.4 `with:` for builders](#74-with-for-builders)
  - [7.5 `do:` for local scope](#75-do-for-local-scope)
  - [7.6 Guard clauses over nesting](#76-guard-clauses-over-nesting)
  - [7.7 Recursion](#77-recursion)
  - [7.8 Name the argument that carries the meaning](#78-name-the-argument-that-carries-the-meaning)
  - [7.9 Reuse a receiver with `with`](#79-reuse-a-receiver-with-with)
  - [7.10 Build maps with literals](#710-build-maps-with-literals)
  - [7.11 Iterate with the container's own form](#711-iterate-with-the-containers-own-form)
  - [7.12 Destructure a rune when its fields are the point](#712-destructure-a-rune-when-its-fields-are-the-point)
- [8. Anti-patterns](#8-anti-patterns)
  - [8.1 String building](#81-string-building)
  - [8.2 Ownership of parameters](#82-ownership-of-parameters)
  - [8.3 Errors that lose the cause](#83-errors-that-lose-the-cause)
  - [8.4 Copy-paste per type](#84-copy-paste-per-type)
- [Part III — Safe code](#part-iii-safe-code)
- [9. Types, representation and arithmetic](#9-types-representation-and-arithmetic)
  - [9.1 The type table](#91-the-type-table)
  - [9.2 Value and reference semantics](#92-value-and-reference-semantics)
  - [9.3 Arithmetic and overflow](#93-arithmetic-and-overflow)
  - [9.4 Bounds checks](#94-bounds-checks)
  - [9.5 Choosing the right type](#95-choosing-the-right-type)
- [10. Conversions](#10-conversions)
  - [10.1 Numeric conversions truncate](#101-numeric-conversions-truncate)
  - [10.2 Text to numbers](#102-text-to-numbers)
  - [10.3 Characters and bytes](#103-characters-and-bytes)
  - [10.4 Strings, slices and bytes](#104-strings-slices-and-bytes)
  - [10.5 Newtypes](#105-newtypes)
  - [10.6 `transmute`](#106-transmute)
- [11. Errors](#11-errors)
  - [11.1 `maybe` or `result`](#111-maybe-or-result)
  - [11.2 Designing the error type](#112-designing-the-error-type)
  - [11.3 Propagating](#113-propagating)
  - [11.4 `error` and `or:`](#114-error-and-or)
  - [11.5 `panic` policy](#115-panic-policy)
- [12. `defer`, `errdefer` and `banish`](#12-defer-errdefer-and-banish)
  - [12.1 The three cleanup tools](#121-the-three-cleanup-tools)
  - [12.2 `defer`](#122-defer)
  - [12.3 `errdefer`](#123-errdefer)
  - [12.4 Placement](#124-placement)
  - [12.5 Error paths](#125-error-paths)
- [13. Concurrency](#13-concurrency)
  - [13.1 What exists](#131-what-exists)
  - [13.2 Mutex](#132-mutex)
  - [13.3 Atomics](#133-atomics)
  - [13.4 Channels](#134-channels)
  - [13.5 Sharing rules](#135-sharing-rules)
  - [13.6 Testing concurrency](#136-testing-concurrency)
  - [13.7 Coroutines](#137-coroutines)
  - [13.8 The reactor: scheduling is explicit](#138-the-reactor-scheduling-is-explicit)
- [14. C interoperability, safely](#14-c-interoperability-safely)
  - [14.1 The boundary file](#141-the-boundary-file)
  - [14.2 Ownership across the boundary](#142-ownership-across-the-boundary)
  - [14.3 Wrapping](#143-wrapping)
  - [14.4 `antiquus`](#144-antiquus)
  - [14.5 `psc bind`](#145-psc-bind)
  - [14.6 ABI](#146-abi)
- [15. Untrusted input](#15-untrusted-input)
  - [15.1 Where trust ends](#151-where-trust-ends)
  - [15.2 Validate, then convert](#152-validate-then-convert)
  - [15.3 Paths](#153-paths)
  - [15.4 URLs, JSON and regex](#154-urls-json-and-regex)
  - [15.5 Decompression and allocation limits](#155-decompression-and-allocation-limits)
  - [15.6 Secrets](#156-secrets)
- [16. Security checklist](#16-security-checklist)
  - [16.1 Memory](#161-memory)
  - [16.2 Input](#162-input)
  - [16.3 FFI](#163-ffi)
  - [16.4 Escape hatches](#164-escape-hatches)
- [Part IV — Manual memory](#part-iv-manual-memory)
- [17. The memory model](#17-the-memory-model)
  - [17.1 What the language guarantees](#171-what-the-language-guarantees)
  - [17.2 The ownership table](#172-the-ownership-table)
  - [17.3 Runes with `Nexus`](#173-runes-with-nexus)
  - [17.4 Moves are copies](#174-moves-are-copies)
  - [17.5 The stack and the heap, for people coming from Python or Java](#175-the-stack-and-the-heap-for-people-coming-from-python-or-java)
  - [17.6 Pointer, owner and borrow](#176-pointer-owner-and-borrow)
  - [17.7 Layer 1 — `derive Drop`](#177-layer-1-derive-drop)
  - [17.8 Layer 2 — `std.consortium`](#178-layer-2-stdconsortium)
  - [17.9 Layer 3 — copy-on-write](#179-layer-3-copy-on-write)
  - [17.10 Case study: an ECS](#1710-case-study-an-ecs)
  - [17.11 How to choose a layer](#1711-how-to-choose-a-layer)
  - [17.12 Rules](#1712-rules)
- [18. `banish` in depth](#18-banish-in-depth)
  - [18.1 What it accepts](#181-what-it-accepts)
  - [18.2 Per-type behaviour](#182-per-type-behaviour)
  - [18.3 Containers of containers](#183-containers-of-containers)
  - [18.4 Views and parameters](#184-views-and-parameters)
- [19. Views, borrows and lifetimes](#19-views-borrows-and-lifetimes)
  - [19.1 The three views](#191-the-three-views)
  - [19.2 Returning a view](#192-returning-a-view)
  - [19.3 Borrowing rules](#193-borrowing-rules)
- [20. Patterns](#20-patterns)
  - [20.1 Constructor / destructor pairs](#201-constructor-destructor-pairs)
  - [20.2 Ownership transfer](#202-ownership-transfer)
  - [20.3 Out-parameters](#203-out-parameters)
  - [20.4 Module state](#204-module-state)
  - [20.5 Builder for strings](#205-builder-for-strings)
  - [20.6 Arena for a phase](#206-arena-for-a-phase)
- [21. Leaks and corruption](#21-leaks-and-corruption)
  - [21.1 Case 1 — copied string handle](#211-case-1-copied-string-handle)
  - [21.2 Case 2 — error path before `defer`](#212-case-2-error-path-before-defer)
  - [21.3 Case 3 — banishing a view](#213-case-3-banishing-a-view)
  - [21.4 Case 4 — list of strings](#214-case-4-list-of-strings)
  - [21.5 Case 5 — double banish of a `Nexus` rune](#215-case-5-double-banish-of-a-nexus-rune)
  - [21.6 Tools](#216-tools)
- [22. Allocation strategy](#22-allocation-strategy)
  - [22.1 Stack first](#221-stack-first)
  - [22.2 One allocation, then grow](#222-one-allocation-then-grow)
  - [22.3 Reuse instead of reallocating](#223-reuse-instead-of-reallocating)
  - [22.4 Pool by lifetime](#224-pool-by-lifetime)
  - [22.5 Measure](#225-measure)
- [Part V — Tests](#part-v-tests)
- [23. The testing pyramid](#23-the-testing-pyramid)
  - [23.1 What to test where](#231-what-to-test-where)
  - [23.2 What must be tested](#232-what-must-be-tested)
- [24. `test` blocks, `ward` and `trial`](#24-test-blocks-ward-and-trial)
  - [24.1 A test block](#241-a-test-block)
  - [24.2 `std.ward`](#242-stdward)
  - [24.3 Structure: arrange, act, assert](#243-structure-arrange-act-assert)
  - [24.4 Table-driven tests](#244-table-driven-tests)
  - [24.5 Errors and ownership](#245-errors-and-ownership)
  - [24.6 `std.trial`](#246-stdtrial)
- [25. `psc test`](#25-psc-test)
  - [25.1 Running](#251-running)
  - [25.2 `--json`](#252---json)
  - [25.3 Writing for the runner](#253-writing-for-the-runner)
- [26. Hard cases](#26-hard-cases)
  - [26.1 Files and fixtures](#261-files-and-fixtures)
  - [26.2 FFI](#262-ffi)
  - [26.3 Concurrency](#263-concurrency)
  - [26.4 Memory](#264-memory)
  - [26.5 Wasm](#265-wasm)
  - [26.6 Determinism](#266-determinism)
- [27. CI](#27-ci)
  - [27.1 The pipeline](#271-the-pipeline)
  - [27.2 A memory job](#272-a-memory-job)
  - [27.3 Gates](#273-gates)
- [Part VI — Libraries and bindings](#part-vi-libraries-and-bindings)
- [28. Designing a public API](#28-designing-a-public-api)
  - [28.1 The rules](#281-the-rules)
  - [28.2 Shape](#282-shape)
  - [28.3 Options rune](#283-options-rune)
- [29. Versioning and deprecation](#29-versioning-and-deprecation)
  - [29.1 Versions](#291-versions)
  - [29.2 Deprecation](#292-deprecation)
  - [29.3 Changelog](#293-changelog)
- [30. Packaging a library](#30-packaging-a-library)
  - [30.1 Layout](#301-layout)
  - [30.2 Symbols](#302-symbols)
  - [30.3 Consuming a library](#303-consuming-a-library)
  - [30.4 Documentation](#304-documentation)
- [31. Writing a C binding](#31-writing-a-c-binding)
  - [31.1 Files](#311-files)
  - [31.2 Wrapper rules](#312-wrapper-rules)
  - [31.3 Checklist](#313-checklist)
- [32. `psc bind`](#32-psc-bind)
  - [32.1 Generating](#321-generating)
  - [32.2 Reviewing](#322-reviewing)
  - [32.3 Regenerating](#323-regenerating)
- [33. Satellites](#33-satellites)
- [34. ABI and release](#34-abi-and-release)
  - [34.1 What is stable](#341-what-is-stable)
  - [34.2 Layout](#342-layout)
  - [34.3 Exported symbols](#343-exported-symbols)
  - [34.4 Release checklist](#344-release-checklist)
- [Part VII — Performance and delivery](#part-vii-performance-and-delivery)
- [35. Performance](#35-performance)
  - [35.1 Profiles](#351-profiles)
  - [35.2 Dead code elimination](#352-dead-code-elimination)
  - [35.3 Micro-optimisations that matter](#353-micro-optimisations-that-matter)
  - [35.4 Measuring](#354-measuring)
  - [35.5 `--release-unsafe`](#355---release-unsafe)
- [36. WebAssembly and assets](#36-webassembly-and-assets)
  - [36.1 Target](#361-target)
  - [36.2 `std.web`](#362-stdweb)
  - [36.3 Assets](#363-assets)
  - [36.4 Size](#364-size)
- [37. Shipping](#37-shipping)
  - [37.1 The release checklist](#371-the-release-checklist)
  - [37.2 What users need](#372-what-users-need)
  - [37.3 After the release](#373-after-the-release)
- [Appendix A — C to Pengunic](#appendix-a-c-to-pengunic)
- [Appendix B — Style checklist](#appendix-b-style-checklist)
- [Appendix C — Pull request checklist](#appendix-c-pull-request-checklist)
- [Appendix D — Glossary](#appendix-d-glossary)
- [Appendix E — FAQ](#appendix-e-faq)
<!-- /toc -->

## 0. The Pengunic contract

"Pengunic" is the adjective for code that belongs in this ecosystem: safe by
default, explicit about ownership, fast without tricks, and readable six months
later by someone who did not write it. It is not a personality trait of the
compiler and it is not enforced by a linter — it is a set of decisions this
manual makes for you, with the reason attached.

### 0.1 The six principles

1. **The compiler checks what it can; you own what it cannot.** Types, arity,
   exhaustiveness and bounds are checked. Lifetimes, aliasing and leak freedom
   are not. Every chapter below says which side of that line you are on.
2. **Ownership is explicit, always.** A value is owned, borrowed or moved. If a
   function takes ownership, its name and documentation say so. There is no
   hidden copy and no garbage collector to hide a mistake.
3. **Values first, references when needed.** Return `Task`, not `ref to Task`.
   Take `string` by value; reach for `ref to T` only for mutation or for large
   data that must not move.
4. **Errors are values.** Absence is `maybe`; failure with a cause is `result`.
   `panic` is for bugs, never for input you could have rejected.
5. **Predictable C.** Every construct lowers to C you could have written
   yourself. If you cannot picture the C, the construct is wrong for the job.
6. **Documentation is part of the API.** `##` comments are the contract that
   `psc doc` publishes; undocumented public API is unfinished API.

### 0.2 When the principles collide

Use this order, and only this order:

```
safety  >  clarity  >  performance
```

Performance is a measured property, not an aesthetic one. You may break
"clarity" for a measured win, and you may break "safety" only through the
documented escape hatches (`transmute`, `unsafe`, `--release-unsafe`,
`antiquus`), in a comment that explains why, with a test that pins the
behaviour.

### 0.3 The three habits

* **Banish what you allocate.** Every owning allocation has exactly one
  `banish` or one `defer banish` on every path, including error paths.
* **Name the failure.** A `result` error type is a named `omen`, not `string`
  and not a `bool` out-parameter.
* **Test the boundary.** The code most likely to be wrong is where data enters
  the program: argv, files, network, FFI. Test those first.

### 0.4 How to use this manual

| If you are… | Read |
| --- | --- |
| starting a new project | Chapters 1–4 |
| writing your first module | Chapters 5–8 |
| reviewing a PR | 8.3, 16.6, 21.5, 34.6 |
| debugging a crash or a leak | Chapters 17–21 |
| adding tests to an untested library | Chapters 23–27 |
| publishing a library or a binding | Chapters 28–34 |
| making something faster | Chapters 22 and 35 |
| porting C code | Chapters 9, 14 and Appendix A |

Each chapter ends with a **Rules** box: the short version you can apply without
re-reading the chapter.

### 0.5 What this manual is not

It does not teach syntax — that is [LANGUAGE.md](LANGUAGE.md), one construct at a
time, with the C it becomes. It does not catalogue the standard library — that
is [STDLIB.md](STDLIB.md), module by module, with links to the generated API.

## Part I — Project and toolchain

## 1. Installing `psc` and setting up the editor

### 1.1 What you need

A C compiler (`gcc` or `clang`), `make`-free build via `psc`, and the `psc`
binary. From a checkout:

```console
$ bash tools/build_bootstrap.sh     # builds build/psc-stage0 from the C bundle
$ ./build/psc-stage0 build .        # self-hosts build/psc
$ ./build/psc --version
psc 0.53.7 (F13)
```

`build/psc` is the compiler you use from then on. `psc doctor` reports what it
found: the C compiler, the include/runtime paths, and the optional pieces
(libcurl for `std.petitio`, libffi for `std.ffi_call`, libsodium for
`std.secrets`).

### 1.2 The commands you will actually type

| Command | When |
| --- | --- |
| `psc check` | after every edit; no C is generated |
| `psc build` | to produce the artifact |
| `psc run FILE -- args` | to try a single file or the project |
| `psc test` | before every commit |
| `psc fmt` | before every commit |
| `psc doc` | when public API changed |

`psc check` is the fast loop; `psc build --profile release` is the slow one.
Both are incremental through the build cache unless you pass `--no-cache`.

### 1.3 Editor and LSP

`psc lsp` speaks the Language Server Protocol over stdio. The repository ships a
VS Code client in `vscode-extension/`, and any client that can launch a stdio
server works:

```console
$ psc lsp
```

The server publishes diagnostics (the same codes as `psc check`), completion,
go-to-definition and hover over `##` documentation. It is not a type-checking
substitute: keep `psc check` in your save hook.

### 1.4 Formatting

`psc fmt` is the canonical formatter. It reads `.pengufmt.toml` from the file's
directory upwards (flat `key = value` lines):

| Key | Values | Default |
| --- | --- | --- |
| `indent` / `tab_size` / `indent_size` / `indent_width` | positive integer | `4` |
| `tabs` | `true` / `false` | `false` |
| `insert_spaces` | `true` / `false` (inverse of `tabs`) | `true` |
| `blank_lines_max` | integer ≥ 0 | `2` |

```console
$ psc fmt --check        # exit 1 if a file would change
$ psc fmt --diff         # show the change
$ psc fmt src/ lib/      # format in place
```

Format before review, not during it: a formatting diff mixed with a logic diff
is unreviewable.

### 1.5 Version pinning

The compiler version is reported by `psc --version` and affects the ABI
generated for `rune`, `echo` and `omen`. Record the version your project was
tested with in the README, and run `psc doctor` in CI.

**Rules**

* One compiler version per project, written down.
* `psc check` on save, `psc fmt --check` and `psc test` before commit.
* Never mix a formatting change with a behavioural change in one commit.

## 2. Anatomy of a project

### 2.1 `pengu.toml`

`pengu.toml` is the only manifest format accepted (`pengu.yaml` and
`pengu.json` are rejected with an explicit error). A complete example:

```toml
[project]
name = "tasks"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"            # exe | c | obj | static | shared
output_name = "tasks"

[build]
src_dir = "src"
lib_dir = "lib"
include_dir = "include"
c_dir = "c"
build_dir = "build"
target = ""               # triple, or "wasm"
strict_c99 = false
links = []
lib_dirs = []
include_dirs = []
cflags = ["-Wall", "-std=c11"]
ldflags = []
defines = []
cc = "gcc"

[assets]
dir = "assets"
module = "arca"
embed = true
exclude = ["**/*.tmp"]

[profiles.release]
cflags = ["-O3", "-DNDEBUG", "-ffunction-sections", "-fdata-sections"]
defines = ["NDEBUG"]
```

Every key is optional; the defaults above are the ones `psc init` writes. Two
details matter in practice:

* `output` changes the artifact, not the language. `static`/`shared` build a
  library and skip the `main` wrapper; `c` stops after emitting C.
* `profiles.<name>` is selected with `--profile=<name>`; `debug` and `release`
  always exist, and any other name you define is additive.

### 2.2 Directory layout

```
tasks/
  pengu.toml
  src/
    main.pengu
    tasks/
      model.pengu
      store.pengu
  lib/            # dependencies installed by psc add
  include/        # your C headers, for bindings
  c/              # hand-written C compiled alongside
  assets/         # embedded by psc assets
  build/          # artifacts and cache (never edit)
```

Module paths follow directories: `src/tasks/store.pengu` is `tasks.store`. The
entry file is `project.entry` and must exist.

### 2.3 What the build produces

| `output` | Artifact |
| --- | --- |
| `exe` | `build/<output_name>` executable |
| `c` | `build/<output_name>.c` only |
| `obj` | `build/<output_name>.o` |
| `static` | `build/lib<output_name>.a` |
| `shared` | `build/lib<output_name>.so` (`.dylib` on macOS) |

`build/` is disposable: `psc clean` removes it, `psc gc` removes stale cache
entries only.

**Rules**

* `pengu.toml` is committed; `build/` never is.
* One project, one `src_dir`. Put experiments in `scratch/`.
* Set `output = "static"` or `"shared"` for libraries, never `exe`.

## 3. Dependencies

### 3.1 Declaring them

Dependencies live under `[dependencies]` in `pengu.toml`:

```toml
[dependencies.json]
url = "https://github.com/example/pengu-json"
tag = "v1.2.0"
version = "^1.2"

[dependencies.internal]
path = "../internal-lib"
```

`url` means git, `path` means a local checkout. `branch`, `tag` and `version`
narrow the resolution; `version` takes a semver constraint.

### 3.2 The command set

| Command | Effect |
| --- | --- |
| `psc add SOURCE` | resolve, install under `lib/`, write `pengu.lock` |
| `psc remove NAME` | uninstall and drop the lock entry |
| `psc update` | re-resolve within the declared constraints |
| `psc upgrade NAME` | move one dependency to a newer version |
| `psc verify` | check that `lib/` matches `pengu.lock` |
| `psc vendor` | snapshot dependencies into `vendor/` |

`psc add` runs the dependency's build script unless `--no-build` is passed;
`--trust` is required to run it, because a build script executes code.

### 3.3 The lock file

`pengu.lock` records the exact resolved commits and versions. Commit it.

`psc build --locked` fails if the lock is missing or out of date; `--frozen`
does the same and never touches the network. Use `--frozen` in CI and in
release builds, `--locked` on developer machines.

### 3.4 C libraries shipped as satellites

`std_c/<name>/` holds vendored C sources (each with `README.md`, `LICENSE`,
`SOURCE`, `pengu.pkg`). They are not fetched at build time; `tools/fetch_satellite.sh`
vendors them, and `tools/satellite_new.sh` scaffolds a new one. Chapter 33
covers the conventions.

**Rules**

* Commit `pengu.lock`; never hand-edit it.
* CI builds with `--frozen`.
* Pin a tag or a commit for anything you ship; a branch is not a version.

## 4. The build pipeline

### 4.1 Stages

```
.pengu files
   │ lexer        tokens, layout, literals
   │ parser       AST
   │ sema         names, types, ownership, exhaustiveness, bounds
   │ codegen      C (with #line markers), DCE, monomorphisation
   ▼
C compiler (gcc/clang)  →  object files  →  linker
```

`psc emit-c FILE` stops after codegen and prints the C; `psc expand` prints the
whole bundle including the runtime. When a diagnostic is confusing, reading the
C usually explains it.

### 4.2 Dead code elimination

The compiler only emits reachable code: `main`, `@export` roots, and everything
they transitively use. `--prune-types` also drops unused type helpers
(`_pengu_clone_*`, `_pengu_cleanup_*`), and `--prune-native` drops native
libraries that no live function needs. `--no-dce` disables all of it and is
only useful for debugging the compiler.

### 4.3 Profiles and flags

| Flag | Effect |
| --- | --- |
| `--profile=debug` | `-O0 -g`, checks on |
| `--profile=release` | `-O3 -DNDEBUG`, checks on unless `--release-unsafe` |
| `--release-unsafe` | removes bounds and overflow checks |
| `--strict-c99` | portable C99, no statement expressions |
| `--target=wasm` | Emscripten |

`--release-unsafe` is a measured decision, documented in the commit that makes
it, with tests that cover the inputs whose checks were removed.

### 4.4 Measuring the build

```console
$ psc time            # per-phase timings
$ psc build --verbose # the exact cc command line
$ psc tree            # the module graph
```

Caching is content-addressed; `--no-cache` forces a cold build, `psc gc` prunes
entries that no current project references.

**Rules**

* Read `psc emit-c` before optimising; know what you are optimising.
* `--release-unsafe` requires a comment, a test and a measurement.
* If the build is slow, profile with `psc time` before touching flags.

## Part II — Style and structure

## 5. Naming

Names are the cheapest documentation and the most expensive thing to change
later. Every rule below exists because a name that follows it can be read
without opening the file.

### 5.1 Files, directories and modules

| Element | Rule | Example |
| --- | --- | --- |
| Source file | `snake_case.pengu` | `store.pengu`, `json_pointer.pengu` |
| Declaration file | `snake_case.d.pengu` | `curl.d.pengu` |
| Test file | `<module>_test.pengu` | `store_test.pengu` |
| Directory | `snake_case/` | `src/tasks/` |
| Module | `snake_case`, concrete noun | `std.scrolls`, `tasks.store` |

A module name is a noun. If you cannot name the module with a noun, it has no
single responsibility — split it. Never `utils`, `helpers`, `common`, `misc`,
`base`, `core`, `manager`.

### 5.2 Types

| Construct | Style | Example |
| --- | --- | --- |
| `rune` | `PascalCase`, singular, concrete | `Task`, `HttpRequest` |
| `omen` | `PascalCase`, singular, category | `Priority`, `JsonKind` |
| `echo` | `PascalCase`, singular | `Number`, `Value` |
| `seal` | `PascalCase`, what it measures | `UserId`, `Meters` |
| `alias` | `PascalCase` | `Handler`, `Buffer` |
| `concept` | `PascalCase`, capability, singular | `Formatter`, `Nexus` |
| `shard` | `T`, `U`, `K`, `V`, `E` or a descriptive `PascalCase` | `Item`, `Key` |

A type that wraps a resource is named after the resource, not the operation:
`Mutex`, `ChanInt`, `Arena` — not `LockHelper`, `Syncer`.

### 5.3 Functions (`weave`)

`snake_case`, base-form verb, no `-ing`, no type in the name.

| Kind | Form | Example |
| --- | --- | --- |
| Action | transitive verb | `parse`, `split`, `merge` |
| Predicate | `is_`, `has_`, `can_`, `should_` | `is_empty`, `has_key` |
| Infallible conversion | `to_*` | `to_string`, `to_upper` |
| Fallible conversion | `parse_*` → `maybe`/`result` | `parse_int` |
| Constructor | `new`, `from_*`, `with_*` | `new`, `from_json` |
| Mutation | verb | `push`, `clear`, `set_volume` |
| Non-trivial getter | `get_*` | `get_or`, `getenv_or` |
| Trivial getter | noun | `len`, `first`, `keys` |
| Line I/O | `read_*`, `write_*` | `read_file` |
| Validation | `check_*` → `bool`; `assert_*` aborts | `check_range` |
| Iteration | `iter_*`, `each_*`, `gen_*` | `gen_digits` |
| Extraction with default | trailing `_or` | `at_or`, `arg_at_or` |

### 5.4 Methods and rituals

* A method does not repeat its type: `Task.complete`, not `Task.complete_task`.
* Mutators are verbs and use `self->`; queries are nouns or `is_*`/`has_*`.
* `ritual` constructors are `new`, `from_*`, `with_*`, `default`; a fallible
  constructor is `try_*`. Never `create`, `make`, `build` as the main name.
* A method that returns a new value of the same type (`plus`, `with_capacity`)
  does not mutate `self`. A `@mutates` method is named with the verb it applies
  and returns the receiver.

### 5.5 Variables, constants, fields, generics

| Element | Rule | Example |
| --- | --- | --- |
| Local | `snake_case` noun | `retry_count`, `user` |
| Top-level constant | `SCREAMING_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_PORT` |
| Field | `snake_case` noun | `created_at`, `is_ready` |
| Loop index | `i`, `j`, `k` in short loops; a noun otherwise | `for i from 0 to n` |
| Generic parameter | single capital or `PascalCase` | `T`, `E`, `Item` |

No Hungarian notation (`str_name`), no type suffixes (`count_int`), no
abbreviations that are not in the glossary (`cfg` → `config`, `req` →
`request`, `ctx` → `context`). Single-letter names are for loop indices and for
generic parameters only.

### 5.6 Reserved prefixes

* `pengu_*` and `_pengu_*` belong to the runtime and generated C. Never declare
  them.
* `std_*` belongs to the standard library's C layer.
* For `@export("symbol")`, use a project prefix: `tasks_fast_hash`, not
  `fast_hash` (which can collide with libc).

**Rules**

* The name says what it is, not how it is implemented.
* Singular for types; plural only for collections of the same type.
* No `utils`/`helpers`/`misc` module, no `manager`, no `data`, no `info`.
* A rename is a public API change: deprecate, do not silently rename.

## 6. Module layout and documentation

### 6.1 Canonical order

A module reads top to bottom in this order. Reviewers should be able to find a
declaration by position.

```pengu-fragment
## Module docstring: what it does, what it does not do, ownership rules.

include "mylib.h"
link "mylib"

import std.spark
import std.scrolls as s
import tasks.model

const MAX_RETRIES as int is 3

concept Formatter:
    weave format into string

rune Task:
    title as string
    done as bool

echo Value:
    number as int
    text as string

omen Priority:
    Low is 0
    Normal is 1
    High is 2

seal TaskId as int

bind Task with Formatter:
    weave format into string:
        return self->title

enchanting Task:
    weave complete into void:
        set self->done is true

weave make_task with title as string into Task:
    return with title is title, done is false

weave helper_pattern with t as Task into bool:
    return t.done

test "make_task defaults to pending":
    let t is calling make_task with "x"
    calling ward.assert_eq_bool with t.done, false
```

### 6.2 Size and cohesion

* One responsibility per module. If the docstring needs "and", split it.
* Soft limit: 400 lines of body. Past that, the module usually hides two
  modules.
* Helpers live next to their only caller; a helper used by two modules becomes
  public and documented (or moves to a shared module).
* No module-level mutable state unless the state *is* the module's subject
  (`std.whisper`'s configuration). Document every `static var`.

### 6.3 Imports

* Import what you use; the formatter keeps one `import` per line.
* Alias only to resolve a real collision or to shorten a long module name
  (`import std.scrolls as s`). Never alias to a misleading name.
* Imports are not re-exports: a module that re-exports must say so in its
  docstring.
* Importing `std.*` is free at runtime (DCE removes what is unused), so there is
  no reason to hide a std dependency behind an alias.

### 6.4 Documentation comments

`##` is the documentation; `#` is a note to the reader of the source. `psc doc`
publishes only `##`.

```pengu-fragment
## Parses a decimal integer.
##
## Returns `maybe none` when the text is not a complete integer; the caller
## decides whether that is an error. Never panics.
##
## ## Example
## ```pengu
## let n as maybe int is calling parse_int with "42"
## ```
weave parse_int with text as string into maybe int:
    ...
```

Rules for the module docstring: one sentence of purpose; what it does **not**
do; ownership/lifetime rules if any allocation is involved; one short example.
For a function: what it returns on each failure path, whether the result is
owned, and whether arguments are borrowed.

### 6.5 What `psc doc` publishes

One page per module, one `###` section per exported symbol, the signature and
the `##` text. `docs/api/` in this repository is the reference output. If a
symbol has no `##`, its page says `_Undocumented._` — that is a bug.

**Rules**

* Every public symbol has a `##` comment; private helpers may have one.
* The first line is a complete sentence in the imperative ("Parses…",
  "Returns…").
* Document ownership and failure explicitly for anything that allocates.
* `psc doc` must run clean before a release.

## 7. Expressions over statements

A PenguScript expression produces a value; a statement produces an effect. When
a value is what you need, prefer the expression form: it has one assignment, no
mutable accumulator, and no branch that can forget to set it.

### 7.1 Return the expression

```pengu-fragment
# ❌ statement-shaped
weave grade with score as int into string:
    var g as string is "F"
    if score >= 90:
        set g is "A"
    else if score >= 80:
        set g is "B"
    return g

# ✅ expression-shaped
weave grade with score as int into string:
    return if score >= 90:
        "A"
    else if score >= 80:
        "B"
    else:
        "F"
```

### 7.2 `judge` is a value

```pengu-fragment
weave priority_name with p as Priority into string:
    return judge p:
        when Priority.Low -> "low"
        when Priority.Normal -> "normal"
        when Priority.High -> "high"
```

`judge` must be exhaustive (`E0044`); the `else` arm is only for a catch-all
over an open set.

### 7.3 Comprehensions instead of accumulators

```pengu-fragment
# ❌ allocate-per-iteration and O(n²)
var out as list of string is list of string
for x in xs:
    calling out.push with "{x}"

# ✅ one expression, one allocation
let out as list of string is for x in xs then "{x}"
```

### 7.4 `with:` for builders

`with:` turns a sequence of `set .field` statements into one named
construction. It is the only place `.field` appears on the left of `set`.

```pengu-fragment
let req as Request is with:
    set .method is "GET"
    set .timeout_ms is 5000
```

### 7.5 `do:` for local scope

Use `do:` when a temporary should not leak into the surrounding scope:

```pengu-fragment
let total as int is do:
    let base is 100
    let tax is 21
    base + tax
```

### 7.6 Guard clauses over nesting

```pengu-fragment
weave handle with req as Request into result of Response to HttpError:
    if not req.is_valid:
        return calling err_of with HttpError.BadRequest
    let body as string is try calling read_body with req
    defer banish body
    return calling ok_of with (calling respond with body)
```

### 7.7 Recursion

Recursion is fine when the data is recursive (trees, JSON, paths). When it is
not, a loop is clearer and does not grow the C stack:

```pengu-fragment
# ✅ recursive by nature
weave depth with node as Node into int:
    if node.children.len == 0:
        return 1
    var best as int is 0
    for c in node.children:
        let d is calling depth with c
        if d > best:
            set best is d
    return best + 1
```

**Rules**

* One assignment per computed value; no "declare then set in every branch".
* `judge` for categories, `if` for conditions, comprehensions for lists.
* Guard clauses at the top; the happy path last.
* Recursion only over recursive data.

### 7.8 Name the argument that carries the meaning

Three bare integers at a call site say nothing; a boolean flag says less than its
name. Name an argument when its parameter name is part of the meaning, and keep
it positional when the order is obvious:

```pengu-fragment
calling window.resize with 800, 600
calling window.configure with resizable is false, title is "Logs"
```

**Rules**

* Name arguments that are flags, modes or units; leave obvious orders positional.
* Positional arguments first, then named ones — never a positional after a name.
* A named argument costs nothing at runtime: the compiler orders it and emits the
  same C call as the positional form.
* Chain and pipe steps take positional arguments only; when a step needs a name,
  call the method directly on its receiver.

### 7.9 Reuse a receiver with `with`

When one value owns most of the work in a block, bind it once with `with` and
write `.field` / `calling .method` in the body. The receiver is evaluated once,
the field names stay close to their owner, and a typo is a compile error instead
of a silently wrong access:

```pengu-fragment
with window:
    set .title is "Logs"
    calling .resize with 800, 600
    calling .refresh
```

**Rules**

* Use `with` when three or more lines touch the same receiver; below that the
  explicit receiver is clearer.
* The target must be an addressable place — bind a temporary first (`var tmp as
  T is …`) instead of `with make_widget():` (`E0077`).
* Inside the body there is no second receiver: nested `with` blocks stack, the
  innermost wins.

### 7.10 Build maps with literals

Prefer a map literal to a sequence of `.put` calls when the entries are known at
the point of construction: it states the contents in one place and the compiler
emits one insert per entry.

```pengu-fragment
var ages as map of string to int is {"ada": 36, "alan": 41}
defer banish ages
```

**Rules**

* Write the type on the binding (`var ages as map of string to int is …`);
  a bare `{"a": 1}` has no key/value type and is `E0076`.
* Use `.put` for entries computed later, and a literal for the initial shape.
* The literal owns the map; `banish` it like any other map.

### 7.11 Iterate with the container's own form

`for` knows every container, so index arithmetic is a red flag: it hides the
length rule of each type and re-derives it at the wrong moment.

```pengu-fragment
# ❌ manual index, wrong for slices and maps
var i as int is 0
while i < (calling xs.length):
    calling handle with (xs at i)
    set i is i + 1

# ✅ one loop, the compiler picks the accessor
for x in xs:
    calling handle with x

# ✅ a map binds both halves; there is no index to fake
for key, value in counts:
    calling emit_pair with key, value
```

Prefer a labelled loop over a boolean flag to leave nested loops
(`continue outer`), and a comprehension over an accumulator with `push`.
Iterating a string yields borrowed one-byte views: no allocation per
character, and no assumption about multi-byte boundaries.

### 7.12 Destructure a rune when its fields are the point

A rune is a record; unpack it once instead of naming the rune just to reach its
fields. The names bind in declaration order and the count must match (`E0079`).

```pengu-fragment
# ❌ the rune exists only to be dereferenced
var point as Pair is with left is 7, right is 3
calling print with "{point.left} {point.right}\n"

# ✅ the fields are the data; the rune is the shape
var (left, right) as Pair is point
calling print with "{left} {right}\n"
```

A rune needs `as T` to be destructured: the compiler must know the field order.
When a call returns several values, bind them in one step instead of keeping an
anonymous tuple around.

### 7.13 Compose with `fundere`, do not imitate inheritance

`fundere` is for "this value *has* that value, and reaching into it is noise".
It is not a way to build a type hierarchy: the host is not a subtype of the
embed, and nothing dispatches.

```pengu-fragment
rune GameObj:
    position as Vec2
    bounds as Rect

rune Enemy fundere GameObj:
    health as int
```

Use it when all of these hold:

* the host genuinely owns one embed of that type (one `GameObj`, one `Physics`);
* the embed is a stable part of the host's layout, not a pointer to a shared one;
* you want `enemy.position` because the embed has no identity of its own.

Write the field explicitly when any of these holds:

* you need to pass the embed to C (`sigil of e.gameObj` is still how you do it,
  but a named field makes the boundary obvious);
* the host has several embeds of the same type — name them (`as left`, `as right`);
* the relationship is "can do", not "is made of". That is a `concept` and an
  explicit `bind`, never a `fundere`;
* the embed would be a pointer/view. `fundere` stores the value inline.

Two traps:

* **Shadowing as a design.** If a host field shadows a promoted field, the host
  wins silently. It is legal and occasionally right (narrowing a type), but
  `--lint=shadow` exists because it is usually a rename waiting to happen.
* **Inheritance in disguise.** `rune Dog fundere Animal` reads like `Dog is an
  Animal`, and it is not: `ref to Dog` cannot be passed where `ref to Animal` is
  expected, `Animal`'s rituals are not inherited, and `Animal`'s concepts are not
  inherited either. If you want substitutability, define a `concept` and `bind`
  both types.

`fundere` propagates exactly two things, because memory demands it: `Drop` and
`Nexus`. A host with a `Drop` embed is `Drop` (move-only, composed destructor),
and a host with a `Nexus` embed can `banish`. Everything else is written on the
host on purpose.

Freeing the embed and then the host is safe, and so is freeing twice: `banish`
zeroes the handle it releases, and the composed destructor only frees what is
still owned. What is *not* safe is freeing through a second binding you made
yourself:

```pengu-bad
var g as GameObj is e.gameObj
banish g
banish e            # no libera dos veces, pero `g` era una vista
```

`e.gameObj` is a view of the host's storage, not a second owner. Read it, pass
it, promote through it; do not banish it and then expect the host to still own
the string.

## 8. Anti-patterns

Each row is a real mistake seen in this codebase or in code ported from C. The
expanded examples after the table show the four most expensive ones.

| ❌ Do not | ✅ Do instead | Why |
| --- | --- | --- |
| `"a" + b` | `"a {b}"` | `+` is numeric; string composition is interpolation |
| `set acc is "{acc}{x}"` in a loop | comprehension + `scrolls.join` | O(n²) allocation |
| `let MAX is 100` at top level | `const MAX as int is 100` | `let` at top level is `E0002` |
| `if m.is_present: m.value` | `if v as T is m:` | one check, one binding |
| `var r is 0` + `if`/`else` | `if cond then a else b` | one assignment |
| `x.foo` to call | `calling x.foo` | invocation is always explicit |
| `self.hp` | `self->hp` | `self` is a reference (`E0003`) |
| `rune Dog fundere Animal` to model "is-a" | `concept` + `bind`, or a named field | `fundere` is composition: no subtyping, no inherited methods |
| `bool` success + out-param | `result of T to E` | the failure carries a cause |
| `panic` for user input | `maybe`/`result` | panic is for bugs |
| `return maybe none` to signal an error | `result` with a named error | absence is not a cause |
| error type `string` | `omen` error type | exhaustiveness and stable codes |
| ignoring a `result` | `try`, `or:`, or handle it | a dropped error is a bug |
| `var b is a` for an owned `string`/`list` | `calling scrolls.copy with a`, or borrow `a` | the copy shares the buffer and both owners free it |
| `banish` a parameter | document borrowed parameters | the callee does not own them |
| `banish` a slice/view | banish the owner | views do not own storage |
| `banish` inside a loop over a list of strings | `pengu_banish_string_list` or per-element policy | the container does not free elements |
| freeing then using | `banish` once, at the end of the owning scope | use after free |
| `defer banish x` after `return` | put `defer` right after allocation | unreachable defer |
| allocating in a loop without freeing | allocate once, or arena | leak per iteration |
| `std.memoria.alloc` for a fixed array | `array of T with size N` | stack, no free |
| `ref to T` returned from a local | return the value | dangling reference (`E0051`) |
| `transmute` to convert numbers | `as`, `to_int`, `to_float` | reinterpretation, not conversion |
| `unsafe` for convenience | only with a comment, a test and a measurement | it removes the checks |
| `--release-unsafe` globally | per-target, documented | removes bounds checks |
| `antiquus` for ordinary logic | `weave` | C bodies are not type-checked |
| `antiquus` without `##` contract | document pre/postconditions | the compiler cannot help |
| `@packed` on an everyday struct | only wire/disk formats | changes the ABI |
| `@export` without prefix | `@export("mylib_x")` | libc collisions |
| `@noreturn` on something that returns | only truly non-returning functions | UB at the call site |
| `cyclus` to silence a forward reference | reorder declarations or use a pointer | hides infinite-size errors |
| `seal` for a plain alias | `alias` | `seal` is nominal and adds conversions |
| generic `T` with no bound when a bound is needed | add the minimal `where` bound | errors surface at the definition |
| duplicating a function per type | `shard T` | one implementation, one test set |
| `concept` for a single implementation | a plain function | concepts are for polymorphism |
| implementing `Par`/`Ordo` by hand | `derive Par, Ordo` | the derive is the canonical order |
| `ritual` inside `concept` | not supported; use `weave` | the checker rejects it |
| `@mutates` in value position | call it as a statement | `E0066` |
| chaining a mutation then reading | split into two statements | evaluation order surprises |
| `while` with an accumulator index | `for i from a to b` | the loop owns the index |
| `for ch in s` for UTF-8 text | `std.lingua` iteration | bytes vs code points |
| regex to parse JSON/HTML | `std.json`, a real parser | regex is not a parser |
| regex per character | precompile with `std.regulus` | compilation per call |
| trusting `argv`/env | validate and convert with `parse_*` | input is untrusted |
| trusting network/file sizes | check before allocating | allocation DoS |
| `File` opened without `defer close` | `defer` the close | leak on early return |
| `@deprecated` without a replacement | name the alternative | the warning must be actionable |
| public symbol without `##` | document it | `psc doc` shows `_Undocumented._` |
| test that depends on wall-clock time | inject a clock or use a range | flaky test |
| test that touches the network | fixture or a fake | flaky and slow |
| `test` asserting on a panic message | assert the `result` error | the message is not an API |
| 500-line `main` | one function per step | untestable |
| module named `utils` | a noun with one responsibility | no responsibility |

### 8.1 String building

```pengu-fragment
# ❌ E0005 — `+` does not concatenate strings
let msg is "Hello, " + name

# ✅ interpolation
let msg is "Hello, {name}"

# ✅ many pieces: one builder, one allocation
var b as StringBuilder is calling StringBuilder.new
defer banish b
for part in parts:
    calling b.append with part
let joined as string is calling b.finish
```

### 8.2 Ownership of parameters

```pengu-fragment
# ❌ the callee cannot know whether the caller still needs it
weave normalize with path as string into string:
    banish path                 # frees the caller's string
    return calling to_lower with path

# ✅ borrow, copy if you must return a new one
weave normalize with path as string into string:
    return calling scrolls.lower with path
```

### 8.3 Errors that lose the cause

```pengu-fragment
# ❌ absence tells the caller nothing about what to fix
weave load with path as string into maybe Config:
    let text as maybe string is calling archivum.read_text with path
    if text is not present:
        return maybe none
    return calling parse_config with text.value

# ✅ the caller can react, and the cause survives the boundary
weave load with path as string into result of Config to IoError:
    let text as string is try calling archivum.read_file_result with path
    defer banish text
    let cfg as maybe Config is calling parse_config with text
    if cfg is not present:
        return calling err_of with IoError.Unknown
    return calling ok_of with cfg.value
```

`try` refuses to cross error domains (`E0045`): if the function returns
`result of Config to LoadError`, the `try` above does not compile. Map the error
explicitly instead of widening it to `string`.

### 8.4 Copy-paste per type

```pengu-fragment
# ❌ one function per element type
weave sum_ints with xs as list of int into int: ...
weave sum_floats with xs as list of float into float: ...

# ✅ one generic function with the bound it needs
weave sum shard T where T: Num with xs as list of T into T:
    var total as T is donum T
    for x in xs:
        set total is total + x
    return total
```

The same rule applies to data transfer objects. Before `derive Json`, every DTO
needed a hand-written pair of walks over `std.json`, each one a place to forget a
`banish`. Now the codec is compiled from the rune itself:

```pengu
rune Address derive Json:
    city as string
    zip as int

rune User derive Json:
    id as i64
    name as string
    @json("e-mail") email as string
    @skip password as string
    tags as list of string
    nick as maybe string
    address as Address

weave handle with body as string into result of User to string:
    return calling User.from_json with body

weave send with user as ref to User into string:
    return calling user.to_json
```

What this buys, and what it does not:

- **It compiles to C, not to a runtime.** `to_json` becomes
  `_pengu_json_encode_User` and `from_json` becomes
  `_pengu_json_decode_User`; there is no reflection, no RTTI table and no
  dependency on `std.json`. The result reads like the serializer you would have
  written by hand.
- **The error path owns its cleanup.** On a decode failure the decoder frees the
  fields it had already reserved with `_pengu_json_free_User` and returns
  `err` with `line`/`col`, so the caller never receives a half-built value. Do
  not rely on `banish` for that: `Nexus` is deliberately shallow (see
  [LANGUAGE.md §9.1](LANGUAGE.md#91-rune--structs)).
- **Validation is not the codec's job.** `@format("email")`, ranges or business
  rules belong to a `weave validate` at the boundary; the compiler rejects those
  attributes inside a Json rune (`E0054`) instead of pretending to enforce them.
- **Keep the schema in the DTO, not in the compiler.** `derive Json` exposes
  nothing about OpenAPI or JSON Schema; a satellite tool (`psc doc`, `portus`)
  reads the rune and writes whatever specification it needs.

Full reference: [LANGUAGE.md §9.7.1](LANGUAGE.md#971-derive-json).

## Part III — Safe code

## 9. Types, representation and arithmetic

### 9.1 The type table

| PenguScript | C | Size | Notes |
| --- | --- | --- | --- |
| `int` | `int32_t` | 4 | default integer; overflow wraps |
| `i8`/`i16`/`i32`/`i64` | `intN_t` | 1/2/4/8 | signed |
| `u8`/`u16`/`u32`/`u64` | `uintN_t` | 1/2/4/8 | unsigned |
| `isize`/`usize` | `intptr_t`/`uintptr_t` | pointer | indices, sizes |
| `float` / `f32` | `float` | 4 | default float |
| `f64` / `double` | `double` | 8 | use for money, time, precision |
| `bool` | `bool` | 1 | no implicit int conversion |
| `char` | `char` | 1 | byte, not a code point |
| `byte` | `uint8_t` | 1 | raw byte |
| `string` | `PenguString` | 16 | pointer + length + ownership flag |
| `list of T` | `PenguList` | 24 | heap, growable |
| `map of K to V` | `PenguMap` | 32 | heap, hashed |
| `array of T with size N` | `T[N]` | N×sizeof(T) | stack, fixed |
| `slice of T` | `PenguSlice` | 16 | borrowed view |
| `ref to T` | `T *` | 8 | borrowed pointer |
| `maybe T` | `PenguMaybe` | 16 | flag + boxed payload |
| `result of T to E` | `PenguResult` | 24 | flag + boxed payload/error |

### 9.2 Value and reference semantics

`rune`, `echo`, `omen`, `seal` and the numeric types are values: assigning one
copies the bytes. `list`, `map`, `string`, `maybe`, `result` are handles: the
struct is copied, the storage it points to is not.

That last sentence is the source of most ownership bugs:

```pengu-fragment
var a as string is "hello"
var b as string is a          # copies the handle, NOT the text
banish a                      # frees the text; b is now dangling
calling print with b          # use after free
```

When you need a second owner, ask for a copy explicitly:

```pengu-fragment
var a as string is "hello"
defer banish a
var b as string is calling scrolls.copy with a
defer banish b
```

The same rule applies to `list`, `map`, `maybe` and `result`. To move instead of
copying, pass the value to a function that takes ownership and stop using it.

### 9.3 Arithmetic and overflow

Integer arithmetic wraps at the width of the type. There is no overflow check,
in debug or release:

```pengu
weave main into int:
    var max as int is 2147483647
    var next as int is max + 1
    calling print with "{next}"      # -2147483648
    return 0
```

Wrapping is fine for hashing and checksums; it is a bug for counters, money and
sizes. When overflow is possible:

* accumulate in `i64` and check the range before narrowing with `to`;
* or check the operand before adding (`if a > INT_MAX - b: …`) using the
  constants from `std.integrum`.

```pengu-fragment
weave add_checked with a as int, b as int into result of int to ArithError:
    if b > 0 and a > 2147483647 - b:
        return calling err_of with ArithError.Overflow
    return calling ok_of with a + b
```

Division and modulo by zero trap at the C level (SIGFPE). Guard the divisor, or
use `std.integrum` helpers that return a `result`.

Float arithmetic follows IEEE-754: `0.0 / 0.0` is NaN and NaN is not equal to
itself. Never compare floats with `==`; compare with a tolerance
(`std.fractio` provides the helpers) or compare integers.

### 9.4 Bounds checks

Indexing a `list`, `slice`, `array` or `string` is checked by default:

```
[PENGU] Index out of bounds: 5 (length 3)
[PENGU CRASH] bounds check failed
```

The check is removed inside `unsafe` blocks and with `--release-unsafe`. That is
the whole safety story for indexing: leave it on, and if you must turn it off,
prove the bound with a test.

`array of T with size N` is checked the same way; its size must be a
compile-time constant (`E0041`).

### 9.5 Choosing the right type

* Sizes and indices: `usize`/`isize`, not `int`.
* Money: integer cents in `i64`, never `float`.
* Time: `std.chrono.Instant`/`Duration` (integer nanoseconds) for intervals,
  `std.chronicle` for wall-clock.
* Text: `string` for UTF-8, `slice of byte`/`bytes of` for raw data.
* Absence: `maybe T`. Failure: `result of T to E`. Never `T` plus a `bool`.

**Rules**

* `float` is 32-bit; annotate `f64` for anything that needs precision.
* Never rely on overflow wrapping in business logic.
* Never compare floats for equality.
* Keep bounds checks on; `unsafe` needs a proof, not a hope.
* Copy owning handles explicitly (`scrolls.copy`, `list` clone) before they are
  banished by someone else.

## 10. Conversions

### 10.1 Numeric conversions truncate

`to` converts and narrows silently:

```pengu
weave main into int:
    var big as int is 300
    var small as u8 is big to u8
    calling print with "{small}"     # 44
    return 0
```

That is C semantics, not a check. If the value must fit, say so:

```pengu-fragment
weave to_u8_checked with n as int into result of u8 to RangeError:
    if n < 0 or n > 255:
        return calling err_of with RangeError.OutOfRange
    return calling ok_of with n to u8
```

### 10.2 Text to numbers

`std.spark.parse_int` and `parse_float` return `maybe`; `std.scrolls` and
`std.integrum` expose the same helpers. Never use C `atoi` from a binding: it
cannot report failure.

```pengu-fragment
let n as maybe int is calling spark.parse_int with text
if n is not present:
    return calling err_of with ConfigError.NotANumber
let port as int is n.value
```

Formatted output goes through interpolation or `str_int`/`str_float`; there is
no `printf` format string in the language, so format-string vulnerabilities do
not exist by construction.

### 10.3 Characters and bytes

`ord c` gives the byte value of a `char`; `chr n` builds a `char` from an
integer in 0–255 (`E0057` outside the range). A `char` is a byte, not a Unicode
code point: for UTF-8 work use `std.lingua` (`codepoint_at`, `utf8_len`,
`decode`), never `for ch in s` plus byte arithmetic.

### 10.4 Strings, slices and bytes

* `bytes of s` — `ref to frozen byte` view, no copy, valid while `s` lives.
* `slice of T` — borrowed window over a list/array/string.
* `s at i` on a `string` returns a one-character `string`; `s at i to j` returns
  a substring (owned).
* `s.len` is bytes, not characters; use `lingua.utf8_len` for code points.

### 10.5 Newtypes

`seal UserId as int` is nominal: `int to UserId` and `id to int` are the only
conversions, and they are explicit. Use a seal for values that must not be
mixed up (ids, units, hashes). `alias` is transparent and adds no safety.

### 10.6 `transmute`

`transmute x to T` reinterprets bits and emits `W0001`. Legal uses: reading a
wire format into a struct, inspecting a float's bit pattern in a test. Anything
else is a bug waiting for the next compiler version. Never transmute between
pointer types to dodge the type system; use `opaque` and `declare` instead.

**Rules**

* Every narrowing is either proven (`if` range check) or intentionally
  truncating (hashing, checksums) with a comment.
* Parse text with `parse_*`, never with C conversion functions.
* `char` is a byte; UTF-8 goes through `std.lingua`.
* `seal` for identity, `alias` for readability, nothing for magic.
* `transmute` requires a comment and a test that pins the layout.

## 11. Errors

### 11.1 `maybe` or `result`

| Question | Type |
| --- | --- |
| Is it there? (lookup, optional field, argv) | `maybe T` |
| Did it work, and if not, why? (I/O, parse, network, validation) | `result of T to E` |
| Programmer error, broken invariant | `panic` |
| Ordinary control flow | neither: an `if` |

If the caller can do something different depending on *why* it failed, it is a
`result`. If the only reaction is "use the default", it is a `maybe`.

### 11.2 Designing the error type

An error type is an `omen` with stable, meaningful variants:

```pengu-fragment
omen ConfigError:
    Missing
    PermissionDenied
    NotANumber
    OutOfRange
```

Rules:

* One error type per module boundary, not per function.
* Variants are causes, not messages: `Missing`, not `FileNotFoundAtPath`.
* No payload unless the caller needs the data (e.g. `Invalid { index }`).
* No `string` errors: they are not exhaustive and cannot be matched.
* Keep the variants stable; adding one is fine, renaming one is a breaking
  change (Chapter 29).

### 11.3 Propagating

| Form | Works on | Behaviour |
| --- | --- | --- |
| `x or else fallback` | `maybe`, `result` | default value, lazy |
| `x or return expr` | `maybe`, `result` | returns `expr` from the enclosing weave |
| `try x` | `maybe`, `result` | propagates the same failure |
| `x or:` | `maybe` only | block with `error` bound to the absence |

```pengu-fragment
weave first_line with path as string into result of string to IoError:
    let text as string is try calling archivum.read_file_result with path
    defer banish text
    let line as maybe string is calling first_line_of with text
    return calling ok_of with (line or else "")
```

`try` does not convert error domains: a function returning
`result of T to ConfigError` cannot `try` a `result of T to IoError` (`E0045`).
Map explicitly:

```pengu-fragment
weave load_config with path as string into result of Config to ConfigError:
    let read as result of string to IoError is calling archivum.read_file_result with path
    if not read.is_ok:
        return calling err_of with ConfigError.Missing
    let text as string is read.value
    defer banish text
    return calling parse_config with text
```

### 11.4 `error` and `or:`

`or:` handles the absence of a `maybe`; inside the block, `error` is the
payload (a `string` for `maybe`), and only there (`E0015` elsewhere).

```pengu-fragment
let port as maybe int is calling spark.parse_int with raw
let p as int is port or:
    calling spark.eprintln with "bad port: {error}"
    return 2
```

Do not use `or:` for a `result`: unwrap with `if r.is_ok` or propagate with
`try`.

### 11.5 `panic` policy

`panic` is for states that cannot happen if the code is correct: an invariant
of a data structure, an unreachable `judge` arm on a closed omen. It is never a
response to user input, missing files, or a failed allocation you could report.

A panic prints the message and a stack trace and aborts. Tests may assert that
a panic happens only through `std.trial`'s death tests, not by matching the
message text.

**Rules**

* Absence vs cause: choose the type before writing the function.
* One error `omen` per module boundary; variants are causes.
* `try` only across matching error types; map otherwise.
* No `string` errors, no error codes hidden in a bool.
* `panic` only for broken invariants, with a message that names the invariant.

## 12. `defer`, `errdefer` and `banish`

### 12.1 The three cleanup tools

| Tool | Runs | Use for |
| --- | --- | --- |
| `defer stmt` | at every exit from the scope, LIFO | releasing owned values |
| `errdefer stmt` | only when the scope returns an error | undoing partial work |
| `banish x` | immediately | releasing at a known point |

String temporaries are the exception that proves the rule: interpolation
(`"{x}"`), concatenation (`+`) and a view (`s at a to b`) hand you an owning
`string`, and the compiler releases it at the end of the statement when you use
it as a call argument. `set s += v` appends in place, so the handle you hold
stays valid. You never write `banish` for those.

### 12.2 `defer`

`defer` executes when the enclosing block ends: normally, by `return`, by
`break`/`continue`, or by an error propagated with `try`/`or return`. It runs in
reverse order of registration.

```pengu
import std.archivum

weave main into int:
    var text as string is "hello"
    defer banish text
    calling print with text
    return 0
```

Inside a loop, each iteration is its own scope: a `defer` in the body runs at
the end of each iteration, not at the end of the loop.

### 12.3 `errdefer`

`errdefer` is for undoing a side effect when the function is about to return an
error: closing a transaction, deleting a partial file, releasing a resource that
was handed off. Both `errdefer` and `defer` run, with `errdefer` first when it
was registered last.

```pengu-fragment
weave write_atomic with path as string, data as string into result of void to IoError:
    let tmp as string is "{path}.tmp"
    defer banish tmp
    let w as result of int to IoError is calling archivum.write_file_result with tmp, data
    errdefer calling archivum.delete_file with tmp
    if not w.is_ok:
        return calling err_of with w.error
    return calling ok_of with 0
```

### 12.4 Placement

* `defer banish x` goes on the line after the allocation, before anything that
  can fail.
* Never `defer` inside an `if` unless the value is allocated there.
* Never `defer banish` a parameter: the callee does not own it.
* Never `defer banish` a view (`slice`, `bytes of`, `ref to` field).
* If a function transfers ownership to the caller, it must not `defer banish`
  the returned value.

### 12.5 Error paths

The most common leak is a `return` on an error path before the `defer` is
registered:

```pengu-fragment
# ❌ leaks `buffer` when `parse` fails
var buffer as string is calling read_all with path
let value as maybe V is calling parse with buffer
if value is not present:
    return calling err_of with LoadError.Invalid
banish buffer

# ✅ defer first
var buffer as string is calling read_all with path
defer banish buffer
let value as maybe V is calling parse with buffer
if value is not present:
    return calling err_of with LoadError.Invalid
```

**Rules**

* One owner, one `banish`/`defer banish`, on every path.
* `defer` immediately after the allocation, never after the first failure point.
* `errdefer` only for side effects that must be undone.
* Never banish parameters, views or values you return.
* Test the error path: it is where the leaks are.

## 13. Concurrency

### 13.1 What exists

`std.filum` provides the synchronisation primitives — `Mutex`, `WaitGroup`,
`Once`, `Cond`, `AtomicInt` and typed channels (`ChanInt`, `ChanString`,
`ChanFloat`, `ChanBool`) — and, since 0.30.0, first-class threads:
`filum.start` returns a `Thread` you can `join`, `detach` or free. `std.coro`
adds coroutines: cooperative tasks that live on the thread that created them and
advance only when their owner resumes them.

A thread is OS parallelism; a coroutine is cooperative control inside one
thread. This chapter covers both: the sharing rules apply to threads, and
coroutine affinity removes races without locks.

### 13.2 Mutex

```pengu-fragment
rune Counter:
    lock as Mutex
    value as int

enchanting Counter:
    weave increment into void:
        calling lock with sigil of self->lock
        set self->value is self->value + 1
        calling unlock with sigil of self->lock
```

Rules:

* One mutex protects one invariant; name it after what it protects.
* Hold it for the shortest span: no I/O, no allocation, no callbacks under lock.
* `try_lock` is for avoiding deadlock, never for "probably free".
* A `defer unlock` is only safe if the critical section cannot return early; a
  `return` inside it would leave the mutex locked.

### 13.3 Atomics

`AtomicInt` is a sequentially consistent 32-bit integer:
`add_atomic`, `sub_atomic`, `swap`, `compare_swap`, `inc`, `dec`,
`inc_and_get`, `dec_and_get`. Use it for counters and flags, not for
multi-field invariants (that is a mutex).

```pengu-fragment
rune Stats:
    requests as AtomicInt
    errors as AtomicInt
```

### 13.4 Channels

```pengu-fragment
let jobs as ChanInt is calling ChanInt.with_capacity with 64
defer banish jobs

# producer
let ok as bool is calling jobs.send with 42

# consumer
let v as maybe int is calling jobs.recv
if v is not present:
    return 0
calling handle with v.value
```

* `send` returns `false` when the channel is closed; ignoring it loses work.
* `recv` returns `maybe none` when the channel is closed and drained.
* `close` signals no more sends; the receiver drains, then sees `none`.
* Free a channel exactly once, after every user is done.

### 13.5 Sharing rules

| Value | Across threads |
| --- | --- |
| numbers, `bool`, `char`, `seal` of them | copy freely |
| `rune` of values | copy; a copy per thread is safest |
| `string`, `list`, `map` | **never** share ownership; move it or copy it |
| `ref to T` | only with a lock covering every access |
| `slice of T` | only while the owner is alive and not mutated |
| `maybe`/`result` | values; the payload follows the rule of its type |

The compiler checks the `filum.start` boundary: an owning value must be a local
binding and is moved into the worker; a `ref to T` is accepted only when `T` is
marked `@shared`. It does not prove that `T`'s methods lock, and it does not
track aliases made before the move. If two threads can see the same
`PenguString`, the program is still wrong unless both treat it as immutable and
the owner outlives them.

### 13.6 Testing concurrency

Run the generated C under ThreadSanitizer when a binding allows it
(`cflags = ["-fsanitize=thread"]` in a debug profile), and write tests that
exercise the interleavings you care about with channels or a `WaitGroup`. A
concurrency test that passes once proves nothing: run it in a loop in CI.

**Rules**

* No data shared without a lock, an atomic, or a channel.
* A mutex protects an invariant, and nothing else runs inside it.
* Never ignore the result of `send`.
* Free channels and mutexes once, with a comment saying who owns them.
* Concurrency tests run in a loop; a single green run is not evidence.
### 13.7 Coroutines

A coroutine is not a thread and not a promise: it is a function that can be
suspended and resumed explicitly. `std.coro.start` creates it suspended,
`resume` runs it to the next `yield` or until it returns, and `status` reports
its state. `std.coro` brings no scheduler and no `async`/`await` syntax, and
there is no thread migration: if the owner does not resume it, it does not
advance. The scheduling policy is explicit and lives in `std.reactor` (§13.8).

```pengu
import std.coro

weave worker with out as ref to int into void:
    set essence of out is 1
    calling coro.yield
    set essence of out is 2

weave main into int:
    var n as int is 0
    var co as coro.Coroutine is calling coro.start with worker, (sigil of n)
    calling co.resume
    calling co.resume
    calling co.free
    return n
```

The same affinity that makes coroutines safe imposes the rules:

* A `ref to T` may cross into `coro.start` without `@shared`; the worker never
  changes thread. An owned `string`/`list`/`map` moves, just as with a thread, and
  the original binding becomes unusable (`E0008`).
* `free` is only called on a finished coroutine. A suspended one is discarded
  with `abandon`, which does not run its `defer`s: if the worker owned resources,
  the program leaks them. That is an explicit decision, not an oversight.
* `yield` outside a coroutine, `resume` on a finished one, or `free` on a
  suspended one are panics. They are program bugs; they do not become `result`.
* The stack is 64 KiB and recycled from an arena. Deeper recursion overflows the
  stack: reduce recursion or move the work to a thread.

Coroutines are the substrate for generators and lazy iterators, but PenguScript
adds no generator syntax: the pattern is written with `resume` and `yield`, and
values travel through `ref to` or the owner's state. There is also no
`async`/`await` keyword: the stdlib `*_async` variants are ordinary functions
that suspend the current coroutine and require a reactor task. There is no
function-coloring transform, no capturing closures, and no hidden generated
state machine.

### 13.8 The reactor: scheduling is explicit

`std.reactor` is the scheduling policy, in user space. The program creates the
loop, registers tasks and decides when they run:

```pengu
import std.reactor

weave tick with loop as ref to reactor.EventLoop, n as ref to int into void:
    calling loop.sleep_ms with 10

weave main into int:
    var loop as reactor.EventLoop is calling reactor.EventLoop.new
    calling loop.spawn with tick, 0
    calling loop.run
    calling loop.close
    return 0
```

`spawn` does not run the worker inline: it makes it ready for the next pass.
`run` is the only place that calls `epoll_wait`/`poll` and resumes tasks.
`park_read` and `park_write` park the current coroutine until the descriptor is
ready; `sleep_ms` parks it on a timer; `offload` sends blocking work to the loop
pool and `await_token` waits for it. `close` is called outside a coroutine,
abandons suspended tasks and does not close user descriptors.

**When to use it.** Network I/O, timers, many-connection servers and blocking
work that must not stop everything else (files, libcurl). It is the right choice
when the dominant cost is waiting, not computing.

**When not to.** Pure CPU or real parallelism: use `std.filum` and its `Pool`.
Do not use it to hide a blocking library you do not control: if there is no
`*_async` variant, `offload` is the honest boundary and the cost is one pool
thread per in-flight operation (several concurrent offloads need several
workers). On Windows the reactor uses `WSAEventSelect`; `std.net` is still
POSIX-only, so a TCP server built on `std.net` is not portable to Windows.

**Rules the compiler cannot save you from:**

* A loop belongs to the thread that created it. `new`, `spawn`, `run`, `stop` and
  `close` run on that thread; a worker never touches the loop directly.
* An `*_async` call only happens inside a loop task. Outside one it panics; it
  never blocks silently.
* Do not call `coro.yield` by hand inside a task: use `park_*`, `sleep_ms` or
  `await_token` so the loop knows why it is suspended. A bare `yield` panics on
  the next pass of `run`.
* A task may have several `offload`s in flight; each has its own token and
  `await_token` consumes exactly the one you ask for. `job_free` releases the
  box when the completion is consumed; a task that finishes with pending jobs
  panics.
* Do not close a descriptor the loop still has registered; close the task or the
  socket after `run` resumed it.
* `close` does not close your sockets or files: that responsibility stays yours.
* `std.filum` does not grow coroutine-suspending channels. Its `Mutex`, `Cond`,
  `Chan*` and `Pool` are thread primitives; coroutine parking lives in the
  reactor. To wait for a `Thread` from a task, use `Thread.is_finished` +
  `reactor.await_thread`.

**Anti-patterns.** One loop per request; `join` inside a worker; `Thread.sleep`
to wait for I/O; two `offload`s and waiting for only one; closing the loop from
inside a task; wrapping a blocking call in `spawn` and calling it "async" without
the reactor.


## 14. C interoperability, safely

### 14.1 The boundary file

A binding lives in `<lib>.d.pengu` and contains only declarations:

```pengu-fragment
include "mylib.h"
link "mylib"
insignia mylib_

declare mylib_open with path as ref to char into ref to opaque
declare mylib_read with h as ref to opaque, buf as ref to byte, n as usize into isize
declare mylib_close with h as ref to opaque into int
```

Rules:

* Exact C types: `usize` for `size_t`, `isize` for `ssize_t`, `i64` for
  `int64_t`, `ref to frozen char` for `const char *`, `ref to opaque` for a
  handle.
* No bodies in `.d.pengu`; no `weave`, no `antiquus` there.
* `insignia` prefixes every declaration so the C names stay grouped and do not
  collide with libc.
* `include` for headers you need; `link` for the library; `ldflag` only for what
  a library name cannot express.

### 14.2 Ownership across the boundary

For every function that returns a pointer, answer three questions in a `##`
comment: who owns the result, how is it released, and what is the lifetime of
borrowed arguments.

| C returns | PenguScript |
| --- | --- |
| `char *` owned by caller | `string` if you wrap it; `banish` frees with the matching C allocator |
| `const char *` borrowed | `frozen ref to char`; never banish |
| `void *` handle | `opaque`; release with the library's own close function |
| struct by value | a `rune` that mirrors the layout exactly |
| `NULL` on failure | `maybe`, after the wrapper checks |

Never `banish` memory allocated by a C library with a different allocator, and
never let a C library free memory allocated by the runtime. Wrap both directions
in a helper that uses the matching free function.

### 14.3 Wrapping

The `.d.pengu` is the declaration; the `pengu` module with a Latin name is the
safe API:

```pengu-fragment
import std.ffi

rune Handle:
    raw as ref to opaque

weave open with path as string into result of Handle to IoError:
    let c_path as ref to frozen char is calling ffi.cstr_from_string with path
    let h as ref to opaque is calling mylib_open with c_path
    if h == null:
        return calling err_of with IoError.NotFound
    return calling ok_of with (with raw is h)
```

A **literal** converts on its own where `ref to char` is expected; a `string`
variable does not (the C compiler sees `PenguString`), so the wrapper must go
through `ffi.cstr_from_string` (or a module-specific conversion).

The wrapper: validates arguments, converts `string` to NUL-terminated C strings
only when the C side requires it, maps C error codes to the module's error
`omen`, and owns every allocation it makes.

### 14.4 `antiquus`

`antiquus` embeds a literal C body. Use it only when the operation cannot be
expressed in the language (intrinsics, inline assembly, a macro that is not a
function). Every `antiquus` needs: a `##` contract, a test, and a comment
explaining why. The compiler does not type-check the body.

### 14.5 `psc bind`

`psc bind header.h` generates the `.d.pengu` from a C header using the bundled
`pengu-bind` helper (clang-based):

```console
$ psc bind include/mylib.h --prefix mylib_ --links mylib -o src/mylib.d.pengu
```

Then review the generated file: the generator cannot know ownership, so add the
`##` comments and the wrapper module by hand. Regenerating overwrites your
comments — keep them in the wrapper, not in the `.d.pengu`.

### 14.6 ABI

The generated C uses a documented runtime ABI (Chapter 34). Two rules keep it
stable: never expose a `rune` by value across a C boundary unless the C side
mirrors the layout, and never `@export` a symbol without a project prefix.

**Rules**

* `.d.pengu` contains declarations only; the safe API lives in a wrapper.
* Every ownership question is answered in a `##` comment.
* Never mix allocators.
* `antiquus` is the last resort, documented and tested.
* Re-run `psc bind` after a header change, then re-review the diff.

## 15. Untrusted input

### 15.1 Where trust ends

Every one of these is untrusted until validated: `argv` and environment,
files, stdin, network responses, JSON/TOML/YAML payloads, headers, query
strings, FFI buffers whose length came from outside.

The boundary function is where validation happens, once, and the rest of the
program works with validated types.

### 15.2 Validate, then convert

```pengu-fragment
weave parse_port with raw as string into result of int to ConfigError:
    let n as maybe int is calling spark.parse_int with raw
    if n is not present:
        return calling err_of with ConfigError.NotANumber
    let port as int is n.value
    if port < 1 or port > 65535:
        return calling err_of with ConfigError.OutOfRange
    return calling ok_of with port
```

* Parse with `parse_*`, never with `atoi`/`scanf` from a binding.
* Check ranges before narrowing.
* Bound lengths before allocating: a length field from the wire is a request,
  not a fact.
* Reject, do not sanitize, when the format is strict.

### 15.3 Paths

`std.compass` normalises paths (`cp_normalize`, `cp_absolute`,
`cp_components`). When a path comes from outside:

* reject absolute paths and `..` components unless the user is allowed to
  choose them;
* resolve against a fixed root, then verify the result still starts with that
  root;
* never pass a user string to a shell.

### 15.4 URLs, JSON and regex

* Build URLs with `std.web.url` (`parse`, `query_set`, `encode_component`);
  never concatenate a query string.
* Parse JSON with `std.json`; validate shape with the schema helpers, then read
  fields through `as_*` accessors, not `if kind ==`.
* Regex (`std.regulus`) is for text patterns, not for parsing JSON, HTML or
  config files. Compile once, reuse; never build a pattern from user input
  without escaping (`regulus.escape`).

### 15.5 Decompression and allocation limits

Compressed input can expand without bound. `std.compressus` exposes the
decompressed size; check it against a limit before allocating. The same applies
to image or archive formats in bindings.

### 15.6 Secrets

`std.secrets` (libsodium) provides `random_bytes`, `sha256_raw`, `compare` and
`wipe`. Rules: never log a secret, never include it in an error message, wipe
buffers you no longer need, and compare with `compare` (constant time), not
with `==`.

**Rules**

* One validated boundary per input source; the core never sees raw text.
* Parse, range-check, length-check, then allocate.
* Paths are resolved and checked against a root.
* URLs are built, not concatenated; regex patterns are escaped.
* Secrets never reach logs, errors or `panic` messages.

## 16. Security checklist

Run this list on every change that touches input, FFI, memory or error paths.

### 16.1 Memory

- [ ] Every owning allocation has one owner and one `banish`/`defer banish`.
- [ ] No `banish` of parameters, views, returned values or literals.
- [ ] No copy of an owning `string`/`list`/`map` handle without an explicit copy.
- [ ] Error paths release everything the success path releases.
- [ ] No `defer` after a `return` that can execute first.

### 16.2 Input

- [ ] Every external value is parsed at the boundary.
- [ ] Lengths and counts are checked before allocation.
- [ ] Paths are normalised and confined.
- [ ] URLs, JSON and regex are built with the std helpers.
- [ ] Errors do not echo secrets or full input.

### 16.3 FFI

- [ ] `.d.pengu` has no bodies and exact types.
- [ ] Ownership of every returned pointer is documented.
- [ ] Allocators match on both sides.
- [ ] `antiquus` has a contract, a test and a reason.
- [ ] `@export` symbols carry a project prefix.

### 16.4 Escape hatches

| Hatch | Allowed when | Required |
| --- | --- | --- |
| `unsafe` block | a bound is proven by construction | comment + test |
| `--release-unsafe` | measured hot path, checks covered by tests | comment + benchmark |
| `transmute` | wire layout or bit inspection | comment + test |
| `antiquus` | not expressible in the language | contract + test |
| `@packed`/`@align` | ABI of an external format | mirrored C declaration |
| `@export` | entry point for C or a plugin | prefixed symbol |

**Rules**

* The checklist is part of the PR description, not a memory exercise.
* An escape hatch without a test is a bug.
* Security review is a review of the boundary functions first.

## Part IV — Manual memory

## 17. The memory model

### 17.1 What the language guarantees

PenguScript has no garbage collector and no borrow checker. It has three layers
of memory management, each one opt-in and visible in the type:

* **Layer 1** — `derive Drop`: the rune is destroyed at scope exit and is never
  copied, only moved (§17.7).
* **Layer 2** — `std.consortium`: `Rc`/`Arc`/`Weak` for the cases where several
  owners must outlive one another (§17.8).
* **Layer 3** — copy-on-write containers: copying is O(1) and the first mutation
  clones the buffer (§17.9).

Outside those three layers the model is still manual. The compiler guarantees
that every value is well-typed, that `banish` (E0008) only accepts something it
can actually free, and that a `Drop` value is not used after a move (E0080) or
copied by accident (E0081).

Everything else is a convention enforced by review and tests:

* who owns a value,
* when it is released,
* what a function does with its arguments.

The rest of this part turns those conventions into rules precise enough to
check in review.

### 17.2 The ownership table

| Type | Owner | Release | Copy semantics |
| --- | --- | --- | --- |
| `string` | whoever holds the `PenguString` with `is_owned == 1` | `banish s` | copies the handle, **not** the text |
| `list of T` | the list value | `banish xs` | copies the handle; elements are shared |
| `map of K to V` | the map value | `banish m` | copies the handle |
| `maybe T` | the box, if present | `banish m` | copies the box |
| `result of T to E` | the box, if present | `banish r` | copies the box |
| `ref to T` from `memoria.alloc` | the caller | `banish p` | copies the pointer |
| `ref to T` borrowed | the original owner | **never** | copies the pointer |
| `slice of T` | the original container | **never** | copies the view |
| `bytes of s` | the string | **never** | copies the view |
| `rune` without `Nexus` | its fields are independent | by field | byte copy |
| `rune derive Nexus` | the value | `banish v` → `_pengu_cleanup_T` | byte copy (dangerous) |
| number, `bool`, `char`, `seal` | nobody | — | byte copy |
| literal `"..."` | the binary | **never** | view |

Read the last column twice: **every copy of an owning handle creates a second
owner of the same buffer**. That is the root of double free and use after free.

### 17.3 Runes with `Nexus`

`derive Nexus` generates `_pengu_cleanup_T`, which releases every owned field
recursively:

```pengu
rune User derive Nexus:
    name as string
    tags as list of int

weave main into int:
    var u as User is with name is "ab", tags is [1, 2]
    banish u
    return 0
```

emits

```c
static inline void _pengu_cleanup_User(User* p) {
    pengu_banish_string(&(p->name));
    pengu_banish_list(&(p->tags));
}
```

Without `Nexus`, `banish u` is `E0008`; the fields are still yours to release
individually. With `Nexus`, **the value owns its fields** — and a byte copy of
that value is a second owner, exactly like a copied `string`.

### 17.4 Moves are copies

There is no move operator. Passing a value to a function copies it; assigning it
copies it; returning it copies it. Ownership transfer is a convention: after
handing a value to a function that takes ownership, stop using it, and the
compiler will not warn you if you do.

That is why ownership must be visible in the signature and the `##` docs:
`weave take with s as string into void` means "I own `s` now"; `with s as
ref to frozen string` means "I borrow it".

That holds for types without a destructor. A `derive Drop` type (§17.7) has a
real move: assignment empties the source, the compiler knows it, so using the
source afterwards is `E0080` and copying it without `.clone()` is `E0081`.

**Rules**

* Every owning value has exactly one owner, named in the docs.
* Copying an owning handle is a bug unless it is an explicit deep copy.
* `derive Drop` makes a rune own its fields and lets the compiler check the
  moves; `derive Nexus` only adds the cleanup helper.
* Ownership transfer is a convention you document, except on `Drop` types,
  where the compiler enforces it.

### 17.5 The stack and the heap, for people coming from Python or Java

In Python or Java you do not think about where a value lives: `x = [1, 2]`
creates a list and that is it. In PenguScript there are two places a value can
live, and choosing one is part of writing the program.

* **The stack** is your local variables. It lives for the duration of the call
  and dies on its own when you return: there is nothing to free. An `int`, a
  `bool`, a `Vec2`, a `Buffer` with its fields inline, live on the stack when
  you declare them as locals.
* **The heap** is the buffers that grow or must outlive the call. `string`,
  `list of T`, `map of K to V`, `Rc of T` and `std.arena` live there. A stack
  value can hold a 24-byte *handle* pointing at a heap buffer.

```pengu-fragment
var n as int is 7                      # stack, gone by itself
var s as string is "hola"              # handle on the stack, text on the heap
banish s                               # frees the text
```

An empty `string` or an empty `list` has no buffer: the handle sits at zero and
`banish` does nothing. That is why banishing twice is not "safe" but does not
always blow up either: it only leaves the handle at zero if the type is `Drop`.

**Why there is no GC.** A collector needs pauses, extra memory and a way to find
every pointer. PenguScript compiles to C and wants the cost of each line to be
the one you see: if a function allocates, it shows in its signature and its
`##`; if it frees, too. A GC hides that cost.

### 17.6 Pointer, owner and borrow

Three words you do not need in Python or Java and do need here.

* **Pointer** (`ref to T`): an address of a value that lives elsewhere. You do
  not own what it points at. `ref to frozen T` is the same, but the compiler
  will not let you write through it.
* **Owner**: whoever is obliged to free. For an owning `string` it is the
  binding that created it; for an `Rc` it is the counter; for an owning `list`
  it is the binding that created it.
* **Borrow**: handing a value to a function without transferring the obligation.
  A parameter of container type **is** a borrow by default (LANGUAGE §13.7): the
  callee must not banish it.

```pengu
import std.scrolls

weave describe with s as string into int:    # borrow: does not free
    return calling scrolls.len with s

weave take with s as string into void:       # takes ownership (documented)
    banish s
```

The rule that prevents most bugs: **if you store a parameter, copy it**. A
parameter is a borrow; if you put it in a field and the caller frees the
temporary, your field dangles.

```pengu-fragment
# WRONG: stores the borrow
return with data is s

# RIGHT: stores an owned copy (concatenation creates a new string)
return with data is (s + "")
```

### 17.7 Layer 1 — `derive Drop`

Use it when a value has **one** owner and its life matches a scope. That is the
normal case: a `Buffer` read from a file, a `Parser`, a connection, a game
`World`.

```pengu
rune Frame derive Drop:
    name as string
    ticks as int

weave read_frame with path as string into Frame:
    return with name is (path + ""), ticks is 0

weave main into int:
    var f as Frame is calling read_frame with "a.txt"
    calling print with "{f.ticks}"
    return 0        # _pengu_cleanup_Frame(&(f)) inserted here
```

You do not write `banish f`: the compiler does it at every exit (`return`,
`break`, `continue`, end of block, `or return`). The destructor is the one
`derive Nexus` generated plus a `memset` that leaves the value at zero, so a
manual `banish` still works and the later drop is a no-op.

And it is not copied: it moves.

```pengu-fragment
var a as Frame is calling read_frame with "a.txt"
var b as Frame is a            # moves: `a` no longer exists
calling print with "{a.ticks}" # error[E0080]
```

**When not to use it.** When the value has several owners and you cannot tell
which dies last: that is layer 2. When the value is a tiny component living in a
contiguous array: give it no destructor, the array is the owner.

**Anti-example.** Storing a borrowed parameter in a `Drop` field without copying
it. The destructor frees what the caller still uses. That was a real bug in
`std/compass` (`Path.from_str`), fixed with `cp_own`.

### 17.8 Layer 2 — `std.consortium`

Use it when two parts of the program must see the same value and there is no
clear hierarchy: a document with two views, a node with a parent and a cache, an
asset shared by several scenes.

```pengu
import std.consortium
import std.spark

weave main into int:
    var doc as Rc of int is calling Rc.new with 42
    var view as Rc of int is doc          # one increment, O(1)
    calling spark.println with "{calling view.strong_count}"   # 2
    banish doc
    banish view
    return 0
```

`Rc` copies implicitly because it costs one non-atomic increment. `Arc` crosses
threads, and its copy is atomic: that is why you spell it `.clone()`.

```pengu-fragment
var shared as Arc of Counter is calling Arc.new with c
var other as Arc of Counter is calling shared.clone   # explicit and atomic
```

There are three doors to mutation, and each one says what it costs:

* `get` returns `ref to frozen T`: read, never write.
* `get_mut` returns `maybe ref to T` and only succeeds when you are the sole
  owner.
* `make_mut` clones the value when it is shared; it may cost O(n).

**When not to use it.** For a value with a clear owner: `Rc` is more expensive
and hides who frees. For a counter inside a loop: the counter is cache traffic.

**Cycles.** A parent pointing at a child and a child pointing at the parent with
`Rc` never gets freed. The child stores `WeakRc` and climbs back with `upgrade`,
which returns `maybe Rc`.

### 17.9 Layer 3 — copy-on-write

`string`, `list of T` and `map of K to V` share the buffer when copied. Copying
is O(1) and the first mutation clones:

```pengu-fragment
var a as list of int is [1, 2]
var b as list of int is a          # O(1), they share the buffer
calling b.push with 3              # clones b's buffer
# a.len == 2, b.len == 3
```

This turns "pass a list to a function that modifies it" from a silent O(n) copy
into free until something mutates. The price: mutating a shared copy costs a
full copy, which is why there is a warning (`W0008`):

```bash
psc check --lint=cow src/
```

The warning points at a `var x is y` inside a loop whose body mutates `x`: every
iteration clones the buffer. The fix is to hoist the copy out of the loop, or
`make_unique` once and reuse it.

Three methods make the state visible: `is_shared`, `ref_count` and
`make_unique`.

**When not to use it.** When the container is mutated once per iteration and
never copied; there the COW only adds a counter nobody reads. And do not confuse
it with ownership: `banish` is still your job.

### 17.10 Case study: an ECS

An ECS (entity-component-system) is the perfect example because each piece has a
different lifetime.

```pengu
rune Position:
    x as float
    y as float

rune Velocity:
    dx as float
    dy as float

rune World derive Drop:
    positions as list of Position
    velocities as list of Velocity
    alive as list of bool
    assets as map of string to Rc of Asset
```

* **`World` and its `Storage`**: layer 1. The world owns its arrays and dies
  with the scope of the game or the scene. `derive Drop` frees the three buffers
  and nobody writes `banish world`.
* **Components** (`Position`, `Velocity`): no layer. They are flat data, `~8`
  bytes, living inside the world's contiguous array. Giving them a destructor
  would make every `push` register a cleanup that does nothing.
* **Systems**: no layer. They take `ref to World` or `ref to frozen World` and
  own nothing.
* **Shared assets** (a texture used by two scenes): layer 2, with `Rc`. The
  scene that dies first drops its handle; the texture is freed when the last one
  goes.
* **Snapshots / replays**: layer 3. Copying the world state for a replay is O(1)
  per array; if the replay only reads, the buffer is never cloned.

```pengu-fragment
var snapshot as World is world      # O(1): shares the three arrays
calling snapshot.positions.push with p   # clones only that array
```

**Anti-example.** Putting `Rc` on every component "just in case": each component
goes from 8 bytes to 16 plus an allocation and a counter per access. The ECS
exists to avoid exactly that.

### 17.11 How to choose a layer

| If the value… | Use | Visible cost |
| --- | --- | --- |
| has one owner and a scope lifetime | `derive Drop` | destructor at every exit |
| is shared by several owners with no hierarchy | `Rc` | one increment per copy |
| is shared across threads | `Arc` + `@shared` | atomic per copy, move-only |
| is a cycle | `WeakRc` / `WeakArc` | `upgrade` returns `maybe` |
| is flat data inside an array | nothing | zero |
| is copied a lot and mutated little | COW (default) | full copy on mutation |
| is copied and mutated in a loop | COW + `make_unique` | one copy, not per iteration |

### 17.12 Rules

1. If it has one owner and lives in a scope, `derive Drop`. Do not write
   `banish`.
2. If a parameter is a container or `Drop`, it is a borrow: if you store it,
   copy it.
3. If several owners exist and you cannot tell which dies last, `Rc`. If they
   cross threads, `Arc` and an explicit `clone`.
4. If there is a cycle, one side is `Weak`; `upgrade` before using it.
5. To mutate a shared value: `get_mut` if you are the sole owner, `make_mut` if
   it may be shared. Never mutate through `get`.
6. Components and flat data carry no destructor: the array is the owner.
7. Copying a container is cheap; mutating a shared copy is not. If `--lint=cow`
   warns inside a loop, hoist the copy or `make_unique`.
8. Document in `##` who frees when the signature does not say.

## 18. `banish` in depth

### 18.1 What it accepts

`banish x` requires `x` to be a mutable lvalue of: `string`, `list of T`,
`map of K to V`, `maybe T`, `result of T to E`, `ref to T`, or a rune with
`derive Nexus`. Anything else is `E0008`: literals, temporaries, `seal`
newtypes, `frozen` values and constants.

```pengu-fragment
banish "hello"                  # E0008
banish calling read with p      # E0008: temporary
var s as string is calling read with p
banish s                        # fine
```

### 18.2 Per-type behaviour

| Target | Emitted | After |
| --- | --- | --- |
| `string` owned | `pengu_banish_string(&s)` | empty, `is_owned = 0` |
| `string` borrowed | same call, no-op | unchanged |
| `list`/`map` | `pengu_banish_*` | empty |
| `ref to T` | `pengu_banish((void*)p)` | pointer dangling |
| `maybe`/`result` present | payload + box freed | `none` |
| rune `Nexus` | `_pengu_cleanup_T(&v)` | fields released |
| element (`xs at 0`) | releases that element in place | slot still present |

`banish` does **not** null the pointer and does not mark the value as dead: after
`banish p`, `p` still holds the old address. Set it to `null` if it may be used
again, or keep it scoped.

### 18.3 Containers of containers

`banish xs` frees the list's element buffer only. For `list of string` the
strings inside leak:

```pengu-fragment
var names as list of string is ["a", "b"]
for n in names:
    banish n          # release each owned string
banish names          # release the array
```

The same applies to `list of list of int`, `map of string to string` (keys and
values), and `list` of `Nexus` runes: release the elements, then the container.
`std.loom` and `std.atlas` document which helpers return owned elements.

### 18.4 Views and parameters

Never banish:

* a parameter (`with s as string` borrows; the caller releases),
* a view (`slice`, `bytes of`, `ref to` a field),
* a literal,
* a value you return.

If a function takes ownership, say so in the name and the docs
(`take_*`/`free_*`), and do not `defer banish` the parameter.

**Rules**

* One `banish` per owning value, on every path.
* Banish the elements before the container when the elements are owned.
* Never banish parameters, views, literals or returned values.
* After `banish p`, treat `p` as invalid: assign `null` or drop the scope.

## 19. Views, borrows and lifetimes

### 19.1 The three views

| View | Created by | Valid while |
| --- | --- | --- |
| `slice of T` | `xs at i to j`, `slice of …` | the container is alive and not resized |
| `bytes of s` | `bytes of s` | the string is alive |
| `ref to T` | `sigil of x`, `ref to` field | the value is alive |

A view is a pointer plus a length. It does not keep the owner alive; nothing in
the compiler checks that the owner outlives it.

### 19.2 Returning a view

Returning a view of a local is always wrong: the owner dies at return.

```pengu-fragment
# ❌ dangling: `s` is released at return
weave bad into ref to byte:
    var s as string is "abc"
    defer banish s
    return bytes of s

# ✅ return an owned copy
weave good into string:
    return "abc"
```

Views are for parameters and temporaries inside one function, not for API
returns. If an API must expose a window, return the owner and a range
(`start`, `end`), or copy.

### 19.3 Borrowing rules

* A borrow must not outlive its owner: keep the owner in scope, or return an
  owned value instead.
* Do not resize a `list` while a `slice` into it exists: the buffer may move.
* Do not `banish` an owner while a view is alive.
* A `ref to frozen T` cannot be used to mutate; it is the right type for
  read-only parameters.
* Views passed to C are valid only for the duration of the call.

**Rules**

* Return owners, not views.
* A view never outlives the value it points into.
* No resize while a slice is alive.
* `ref to frozen T` for read-only parameters; `ref to T` only when mutating.

## 20. Patterns

### 20.1 Constructor / destructor pairs

Every module that allocates exposes a pair, documented together:

```pengu-fragment
weave reader_open with path as string into result of Reader to IoError:
    ...

weave reader_close with r as ref to Reader into void:
    ...
```

The caller does `defer calling reader_close with sigil of r`. The `##` of
`reader_open` says "the caller owns the result and must call `reader_close`".

### 20.2 Ownership transfer

```pengu-fragment
## Takes ownership of `buf`; the caller must not use or free it afterwards.
weave send_frame with conn as ref to Conn, buf as list of byte into result of void to NetError:
    defer banish buf
    ...
```

`take_*`/`consume_*` in the name, "takes ownership" in the docs, `defer banish`
in the body: the value has exactly one owner at every point.

### 20.3 Out-parameters

Prefer returning a `rune` or a `maybe`/`result`. When C requires an
out-parameter, wrap it so the pointer never escapes:

```pengu-fragment
weave read_size with p as ref to int into bool:
    if p == null:
        return false
    set essence of p is 42
    return true
```

### 20.4 Module state

A `static var` at module level lives for the whole program: initialise it once,
never free it during normal operation. Do not keep per-request data there.

### 20.5 Builder for strings

Repeated `+` on strings reallocates the whole buffer each time. Use
`std.builder` and `finish` once:

```pengu-fragment
var sb as StringBuilder is calling StringBuilder.new
defer banish sb
for i in 0 to 3:
    calling sb.append_int with i
    calling sb.append with ","
var out as string is calling sb.finish
defer banish out
```

### 20.6 Arena for a phase

When many small objects share a lifetime (one parse, one request, one frame),
allocate them in an `Arena` and release the arena once:

```pengu
import std.arena

weave main into int:
    var a as Arena is calling Arena.new
    defer banish a
    var xs as ref to int is calling arena.arena_alloc of int with sigil of a, 10
    set xs at 0 is 7
    calling print with "{xs at 0}"
    return 0
```

The arena frees every block at `banish a`; individual objects are never freed.
Do not let arena pointers escape the phase.

**Rules**

* Every allocator has a documented release function.
* Name ownership transfers (`take_*`, `consume_*`) and document them.
* Grow strings with a builder, not with a loop of `+`.
* Use an arena for phase-scoped graphs; never leak an arena pointer into a
  longer-lived structure.

## 21. Leaks and corruption

### 21.1 Case 1 — copied string handle

```pengu-fragment
var a as string is calling read_all with path
var b as string is a
banish a
calling print with b          # use after free
```

Fix: `var b as string is calling scrolls.copy with a`, or pass `a` by borrow.

### 21.2 Case 2 — error path before `defer`

```pengu-fragment
var buf as string is calling read_all with path
let v as maybe V is calling parse with buf
if v is not present:
    return calling err_of with LoadError.Invalid   # `buf` leaks
banish buf
```

Fix: `defer banish buf` immediately after the allocation.

### 21.3 Case 3 — banishing a view

```pengu-fragment
var s as string is "hello"
var v as slice of byte is bytes of s
banish v          # E0008: views are not owned
```

If it compiles in some future version, it would corrupt the heap. Views are
never released.

### 21.4 Case 4 — list of strings

```pengu-fragment
var names as list of string is ["a", "b"]
banish names      # leaks "a" and "b"
```

Fix: banish each element first, or use `pengu_banish_string_list` through a
binding if the list came from C.

### 21.5 Case 5 — double banish of a `Nexus` rune

```pengu-fragment
rune User derive Nexus:
    name as string

var u as User is with name is "ab"
var copy as User is u
banish u
banish copy       # double free of `name`
```

Fix: one owner. Pass by `ref to User` when a function only reads.

### 21.6 Tools

* AddressSanitizer: build with `cflags = ["-fsanitize=address", "-g"]` in a
  debug profile, run the binary; leaks print at exit.
* LeakSanitizer: included in ASan on Linux (`ASAN_OPTIONS=detect_leaks=1`).
* Valgrind: `valgrind --leak-check=full ./build/app` for a second opinion.
* `MALLOC_CHECK_=3`/glibc `MALLOC_PERTURB_` to make use-after-free fail fast.
* Tests: run the suite under ASan in CI for the memory-sensitive modules.

**Rules**

* The error path is where leaks live: test it.
* Views are never banished; owners are banished once.
* A `Nexus` rune has one owner, like a string.
* Run ASan on every PR that touches allocation.

## 22. Allocation strategy

### 22.1 Stack first

Numbers, small runes, fixed arrays (`array of T with size N`) and short strings
live on the stack: no allocation, no release. Reach for the heap only when the
size is dynamic or the value must outlive the function.

### 22.2 One allocation, then grow

`list`/`map` grow geometrically; each growth copies. Estimate the size and
reserve once (`std.loom`/`std.atlas` helpers), or build with a `StringBuilder`
and `finish`.

### 22.3 Reuse instead of reallocating

A buffer owned by a long-lived object can be cleared and reused
(`builder.reset`, `list.clear`) instead of banished and reallocated per
iteration.

### 22.4 Pool by lifetime

Group allocations by lifetime: per request (arena), per frame (arena), per
connection (owner struct with `Nexus`). Freeing one owner releases the group,
and there is no per-object bookkeeping.

### 22.5 Measure

`psc time` and `--profile release` first; then `perf`/`heaptrack` on the generated
binary. Do not optimise allocation before the profile shows it.

**Rules**

* Stack unless the size is dynamic or the lifetime escapes.
* Reserve once; grow geometrically, never one element at a time.
* Reuse long-lived buffers instead of reallocating.
* Group allocations by lifetime and free them together.

## Part V — Tests

## 23. The testing pyramid

### 23.1 What to test where

| Layer | Runs in | Cost | What it proves |
| --- | --- | --- | --- |
| pure functions | `test` blocks | milliseconds | logic, edge cases, arithmetic |
| module contracts | `test` blocks | milliseconds | invariants, ownership pairs, error mapping |
| integration | binary invocation / fixtures | seconds | CLI, files, FFI, network |
| end-to-end | built artifact | minutes | the shipped thing works |

Most tests live in the first two layers. If a behaviour can be tested as a
function, test it there; an end-to-end test that covers ten functions tells you
nothing when it fails.

### 23.2 What must be tested

Every public function, at least once, with:

* the happy path,
* the boundary (empty, zero, maximum, one element),
* the failure path (`maybe none`, `err`, `E00xx` you handle),
* ownership: what is released on each path.

Anything that touches memory, FFI or input validation gets an extra test.

## 24. `test` blocks, `ward` and `trial`

### 24.1 A test block

```pengu
import std.ward

test "arithmetic":
    calling ward.assert_eq_int with 1 + 1, 2

test string_formatting:
    calling ward.assert_eq_string with "abc", "abc"
```

A test is `test <name>:` where the name is a string literal or an identifier.
Bodies are type-checked in every mode; `psc test` emits the C harness and runs
them.

### 24.2 `std.ward`

| Helper | Use |
| --- | --- |
| `assert c` | plain condition |
| `assert_msg c, msg` | condition with a message |
| `assert_true` / `assert_false` | booleans |
| `assert_eq_int` / `assert_ne_int` | integers |
| `assert_eq_string` / `assert_ne_string` | strings |
| `assert_eq_bool` / `assert_ne_bool` | booleans |
| `assert_eq_float a, b, eps` | floats with tolerance (default `0.000001`) |

A failed assertion prints the file, line and expected/actual and aborts the
test run.

### 24.3 Structure: arrange, act, assert

```pengu-fragment
import std.ward

weave parse_pair with text as string into maybe (int, int):
    ...

test "parse_pair rejects half a pair":
    let got as maybe (int, int) is calling parse_pair with "7"
    calling ward.assert_false with got is present

test "parse_pair reads two numbers":
    let got as maybe (int, int) is calling parse_pair with "7,9"
    calling ward.assert_true with got is present
    calling ward.assert_eq_int with got.value.first, 7
    calling ward.assert_eq_int with got.value.second, 9
```

One behaviour per test, named as the behaviour ("rejects half a pair"), not as
the function.

### 24.4 Table-driven tests

```pengu-fragment
rune Case:
    input as string
    expected as int

weave run_cases with cases as list of Case into void:
    for c in cases:
        let got as maybe int is calling spark.parse_int with c.input
        calling ward.assert_true with got is present
        calling ward.assert_eq_int with got.value, c.expected
```

A table beats ten copy-pasted tests: add a row, not a function.

### 24.5 Errors and ownership

```pengu-fragment
test "load_config maps a missing file to Missing":
    let r as result of Config to ConfigError is calling load_config with "/nonexistent"
    calling ward.assert_false with r.is_ok
    calling ward.assert_eq_int with (r.error to int), (ConfigError.Missing to int)
```

Test that the failure variant is the intended one, not just "it failed".

### 24.6 `std.trial`

For suite-style runners (used by the std tests), `std.trial` provides
`new_suite`, `test_case`, `test` and `summary`:

```pengu-fragment
var suite as TestSuite is calling trial.new_suite with "parsing"
defer banish suite
calling trial.test_case with sigil of suite, "empty input", (calling parse with "") is present, ""
let ok as bool is calling trial.summary with sigil of suite
```

Use `test` blocks for new code; `trial` is for hosts that want their own runner
and report format.

**Rules**

* One behaviour per test; the name says the behaviour.
* Assert the failure variant, not just failure.
* Tables for input/output families.
* Every ownership pair gets a test on the error path too.

## 25. `psc test`

### 25.1 Running

```console
$ psc test              # every test block in the project
$ psc test --watch      # rerun on change
$ psc test --json       # JSON Lines events, for CI
$ psc test --verbose    # show each test
```

Flags: `--profile`, `--cc`, `--target`, `--entry`, `--json`, `--watch`,
`--verbose`. There is no name filter in 0.28.0: split slow suites into their own
project or file if you need to run a subset.

The command exits non-zero if any test fails, which is what CI checks.

### 25.2 `--json`

Each event is a JSON line with the test name and status, so CI can annotate
failures without parsing console output.

### 25.3 Writing for the runner

* No global mutable state shared between tests; each test sets up what it needs.
* No dependency on execution order.
* Clean up what you create (`defer` the deletion of temp files and dirs).
* Keep tests fast: no sleeps, no network unless it is the subject.

## 26. Hard cases

### 26.1 Files and fixtures

```pengu-fragment
import std.archivum
import std.compass

test "write then read a temp file":
    let dir as string is calling archivum.temp_dir
    defer banish dir
    defer calling archivum.remove_dir with dir, true
    let path as string is calling compass.join with [dir, "sample.txt"]
    defer banish path
    calling ward.assert_true with (calling archivum.write_file with path, "hi")
    let back as maybe string is calling archivum.read_file with path
    defer banish back
    calling ward.assert_true with back is present
    calling ward.assert_eq_string with back.value, "hi"
```

Fixtures live in `tests/fixtures/` for static data and in a temp dir for
generated data. Never write into the repository during a test.

### 26.2 FFI

Test the wrapper, not the C library. Feed it known values, check the mapped
error variants, and run at least one test under ASan so a wrong free is caught.

### 26.3 Concurrency

Run the test many times (`for i in 0 to 1000`) and use channels or a
`WaitGroup` to create real interleavings. A single green run proves nothing.

### 26.4 Memory

Build the test binary with `-fsanitize=address` and run it: leaks and double
frees abort with a stack trace. This is the cheapest ownership test there is.

### 26.5 Wasm

`--target wasm` tests run in the browser harness (`tests/wasm`); DOM-bound
modules (`std.web.*`) are tested there, not in native `psc test`.

### 26.6 Determinism

Seed randomness (`std.lot`) explicitly in tests. Time-dependent code takes the
clock as a parameter, so the test can pass a fixed instant.

**Rules**

* Fixtures never write into the repository.
* Test the wrapper around C, not the C library.
* Concurrency tests loop; memory tests run under ASan.
* Randomness and time are injected, not read from the environment.

## 27. CI

### 27.1 The pipeline

```yaml
- run: tools/build_bootstrap.sh
- run: build/psc-stage0 build . --profile release
- run: ./tests/run.sh
- run: build/psc test
- run: python3 tools/docs/validate_docs.py docs/LANGUAGE.md docs/LANGUAGE.es.md
```

The existing `.github/workflows/ci.yml` does the bootstrap, builds `psc` on
Ubuntu and macOS, and runs the suite. Add your project's tests after that.

### 27.2 A memory job

```yaml
- run: build/psc build . --profile debug --cc "cc -fsanitize=address -g"
- run: ./build/app --self-test
```

ASan in CI catches what review misses. Run it on the modules that allocate.

### 27.3 Gates

A pull request is green only when:

- [ ] `psc check` is clean.
- [ ] `psc test` passes.
- [ ] the new code has tests for success and failure paths.
- [ ] `docs` build and links validate (if docs changed).
- [ ] no new warning in the generated C.

**Rules**

* CI runs the same commands you run locally.
* Memory-sensitive modules get an ASan job.
* A red pipeline blocks the merge; there is no "merge and fix later".
* Docs are validated like code: broken links and uncompilable examples fail.

## Part VI — Libraries and bindings

## 28. Designing a public API

### 28.1 The rules

1. **Name the action, not the implementation.** `read_file`, not `do_read2`.
2. **Return the truth.** `maybe` for absence, `result` for failure, never a
   `bool` plus an out-parameter.
3. **One obvious way.** If two functions do the same thing, delete one.
4. **Small surface.** Every public symbol is a promise; make it few.
5. **Consistent with std.** Same verb (`read`, `write`, `open`, `close`,
   `parse`, `format`), same parameter order (target first, options last).
6. **Ownership is in the signature.** `take_*`/`consume_*` take ownership;
   `ref to frozen T` borrows; everything else returns owned values.
7. **Options are a rune,** not eight booleans.
8. **No flags that change the return type.** Split the function.
9. **Errors are one `omen` per boundary,** documented variant by variant.
10. **Documented, or it does not exist.** `##` on every public symbol.

### 28.2 Shape

```pengu-fragment
## Opens a reader for `path`. The caller owns the result and must call
## `reader_close`. Returns `IoError.NotFound` if the file does not exist.
weave reader_open with path as string into result of Reader to IoError:
    ...

## Reads up to `n` bytes into `buf`. Returns the number of bytes read.
weave reader_read with r as ref to Reader, buf as ref to byte, n as usize into result of usize to IoError:
    ...

## Releases the reader. Safe to call once; the value must not be used after.
weave reader_close with r as ref to Reader into void:
    ...
```

The trio documents who owns what at every step; a caller never has to read the
implementation to know when to free.

### 28.3 Options rune

```pengu-fragment
rune OpenOptions:
    create as bool
    truncate as bool
    mode as int

weave default_open_options into OpenOptions:
    return with create is false, truncate is false, mode is 0o644
```

Adding a field is not a breaking change; adding a parameter is.

**Rules**

* One promise per public symbol; document it with `##`.
* Ownership stated in the docs and reflected in the name.
* Options rune for anything with more than two optional knobs.
* No boolean parameters that change behaviour silently.

## 29. Versioning and deprecation

### 29.1 Versions

* A package has one `version` in `pengu.toml`, semver: `MAJOR.MINOR.PATCH`.
* `MAJOR` changes for a breaking change, `MINOR` for additions, `PATCH` for
  fixes.
* The compiler version and the package version are independent; the package
  states the compiler range it supports in its README.

### 29.2 Deprecation

```pengu-fragment
@deprecated("use read_file_result; this returns a bool and hides the cause")
weave read_file with path as string into bool:
    ...
```

`@deprecated` emits a warning at every use. The deprecation cycle:

1. Add the replacement.
2. Mark the old symbol `@deprecated("use X")` and document the migration in the
   same `##`.
3. Keep it for at least one minor release.
4. Remove it in the next major.

### 29.3 Changelog

One entry per release, in the repository's `CHANGELOG.md`, grouped as Added,
Changed, Deprecated, Removed, Fixed. The changelog is for users: say what they
must do, not which internal file changed.

**Rules**

* Semver, honestly: a rename is a major change.
* Deprecate before removing, with the replacement in the message.
* Every release has a changelog entry.
* The README states the supported compiler range.

## 30. Packaging a library

### 30.1 Layout

```
mylib/
  pengu.toml
  src/
    mylib.pengu          # public API, module docstring
    mylib_internal.pengu # helpers, not imported by users
  tests/
    mylib_test.pengu
  README.md
  CHANGELOG.md
  LICENSE
```

`pengu.toml`:

```toml
[project]
name = "mylib"
version = "0.1.0"
entry = "src/mylib.pengu"
output = "static"

[build]
src_dir = "src"
```

`psc build` writes `build/libmylib.a`. `output = "shared"` writes
`build/libmylib.so` (or `.dylib`). A library project has no `main`; the entry
module holds the public API.

### 30.2 Symbols

Generated C symbols are prefixed with the module name, not the project name.
Pin the names you export with `insignia mylib_` in the entry module:

```pengu-fragment
insignia mylib_

weave add with a as int, b as int into int:
    return a + b
```

produces `int32_t mylib_add(int32_t a, int32_t b)`.

### 30.3 Consuming a library

A consumer links the archive and the runtime:

```console
$ cc app.c build/libmylib.a runtime/pengu_runtime.c -I runtime -lm -lpthread -o app
```

The library's README must state this line and the ABI version it was built
against. Static archives do not include the runtime.

### 30.4 Documentation

`psc doc --output docs/api` generates one page per module from the `##` comments.
Publish those pages with the library; they are the API reference users read.

**Rules**

* Library projects have no `main`; the entry module is the public API.
* Pin exported symbols with `insignia`.
* The README carries the exact link line and the ABI version.
* `psc doc` output ships with the release.

## 31. Writing a C binding

### 31.1 Files

| File | Contents |
| --- | --- |
| `src/mylib.d.pengu` | `include`, `link`, `insignia`, `declare`, layout types |
| `src/mylib.pengu` | the safe API: wrappers, error mapping, ownership |
| `tests/mylib_test.pengu` | wrapper tests, including error paths |

The `.d.pengu` is generated (`psc bind`) or hand-written; the wrapper is always
hand-written and always documented.

### 31.2 Wrapper rules

* Validate inputs before calling C.
* Convert `string` with `ffi.cstr_from_string` (literal-only auto-conversion is
  not enough for variables).
* Map every C error code to an `omen` variant; keep the numeric code in the
  message if it helps debugging.
* Own every allocation; never return a bare C pointer.
* Free with the allocator that produced the memory.

### 31.3 Checklist

- [ ] `.d.pengu` has no bodies and exact types.
- [ ] Every returned pointer's owner is documented.
- [ ] Wrapper maps errors to an `omen`.
- [ ] Wrapper never leaks: every `alloc` has a `banish`.
- [ ] Tests cover success, failure and a wrong-argument path.
- [ ] README states the native dependency and how to install it.

**Rules**

* Declaration file and wrapper are separate.
* No raw C pointer escapes the wrapper.
* Error codes become variants, not strings.
* Every binding has a test that fails when the library is missing.

## 32. `psc bind`

### 32.1 Generating

```console
$ psc bind include/mylib.h --prefix mylib_ --links mylib -o src/mylib.d.pengu
```

The helper (`pengu-bind`, built from C with clang) reads the header and emits
`declare`s, layout types and `include`/`link` directives. Flags: `--prefix`,
`--output`, `--cpp-flags`, `--preprocessed`, `--auto-import`, `--define/-D`,
`--links`, `--ignore`, `--include-paths`, `--no-comments`, `--system-includes`,
`--no-blank-extensions`, `--no-cpp`, `--helper-version`, `--print-helper`.

### 32.2 Reviewing

The generator cannot know ownership, so review every function:

* `char *` → who frees it? Usually `ref to char` in the declaration and a
  wrapper that copies or owns.
* `void *` → `ref to opaque`, never `ref to void` in the public API.
* `size_t` → `usize`; `ssize_t` → `isize`.
* structs by value → a `rune` with `@packed`/`@align` mirroring the header.

### 32.3 Regenerating

Keep hand-written comments in the wrapper, never in the `.d.pengu`; regeneration
overwrites the file. Treat the regenerated diff as code review input.

**Rules**

* Generate, then review every declaration.
* Comments and ownership live in the wrapper.
* Regenerate after every header bump and commit the diff with the change.

## 33. Satellites

A satellite is a vendored C dependency under `std_c/<name>/`:

```
std_c/mylib/
  README.md      # what it is, version, license, how it is built
  LICENSE
  SOURCE         # upstream URL and commit/tag
  pengu.pkg      # build metadata used by the doc/build tooling
  mylib.c
  mylib.h
```

Rules:

* Pin the upstream commit in `SOURCE`; never track a branch.
* Record the license in `LICENSE` and in `THIRD_PARTY.md`.
* Add the binding (`std/<lib>.d.pengu`) and the wrapper
  (`std/<latin>.pengu`).
* Link policy: `link "mylib"` becomes `-lmylib` only if a live symbol needs it;
  release builds prune unused native code, so a satellite costs nothing when
  unused.
* Fetch scripts (`tools/fetch_satellite.sh`) must be reproducible.

**Rules**

* One directory per satellite, with version, license and source pinned.
* The binding and the wrapper are part of the satellite change.
* Unused satellites must not add link flags or binary size.

## 34. ABI and release

### 34.1 What is stable

`PENGU_ABI_VERSION` (currently 3) pins the layout of the runtime structs and the
names of the runtime functions. The generated C asserts it at compile time:

```c
_Static_assert(PENGU_ABI_VERSION == 3, "pengu_runtime.h ABI mismatch: bundle expects v3");
```

A library compiled against one runtime version must be linked with a compatible
runtime. That is why the README states the version.

### 34.2 Layout

| Type | Layout | Notes |
| --- | --- | --- |
| `string` | `{ char *data; int len; int32_t is_owned; }` | 16 bytes on 64-bit |
| `list` | `{ void *data; int len; int cap; size_t elem_size; }` | 24 bytes |
| `maybe` | `{ bool is_present; void *value; }` | payload boxed |
| `rune` | fields in declaration order | padding as the C ABI requires |

`@packed` removes padding; `@align(N)` raises alignment. Use them only to match
an external ABI, and declare the mirrored C struct next to it.

### 34.3 Exported symbols

* Default: `<module>_<name>`.
* `insignia <prefix>` overrides the prefix.
* `@export("symbol")` forces a name and marks the symbol as a DCE root.
* Never `@export` without a project prefix: collision with libc is a link error
  at best and a wrong function at worst.

### 34.4 Release checklist

- [ ] `psc check` and `psc test` clean.
- [ ] `--profile release` build, no new warnings.
- [ ] Version bumped in `pengu.toml`, changelog written.
- [ ] `psc doc` regenerated and published.
- [ ] Symbols exported with `insignia`/`@export` reviewed.
- [ ] ABI version documented in the README.
- [ ] LICENSE and THIRD_PARTY.md updated.

**Rules**

* Never ship a library without the ABI version in the README.
* Layout attributes only for an external ABI, with the mirrored C declaration.
* `@export` always namespaced.
* The release checklist is part of the release PR.

## Part VII — Performance and delivery

## 35. Performance

### 35.1 Profiles

| Profile | Flags | Use |
| --- | --- | --- |
| `debug` | `-O0 -g` | development, ASan |
| `release` | `-O2 -DNDEBUG` | shipping |
| `small` | `-Os -DPENGU_SIZE_OPT` | wasm, embedded, size-constrained |

Add your own in `pengu.toml`:

```toml
[profiles.fast]
cflags = ["-O3", "-march=native"]
```

### 35.2 Dead code elimination

The compiler prunes unused functions and types before emission:

* `--prune-types` removes unused type declarations,
* `--prune-native` removes unused native link flags,
* `--dce-scope=user` restricts pruning to user modules (keeps std complete),
* `--no-dce` keeps everything (debugging).

`@export("name")` marks a symbol as a DCE root: use it for entry points called
from C, and always with a project prefix.

### 35.3 Micro-optimisations that matter

* `@inline` on tiny hot functions; do not inline everything — it hurts the
  instruction cache.
* `@cold` on error paths, so the hot path stays compact.
* Prefer `array of T with size N` over `list` for fixed, hot data.
* Build strings with `StringBuilder`, not repeated `+`.
* Reserve `list` capacity when the size is known.
* Avoid `ref to opaque` indirection in tight loops.

### 35.4 Measuring

```console
$ psc time build --profile release
$ psc build --profile release --verbose
$ perf stat ./build/app
$ heaptrack ./build/app
```

Measure before and after; a change without a before/after number is not an
optimisation.

### 35.5 `--release-unsafe`

It removes bounds checks. It is a measurable win only in indexing-heavy code and
it turns a bug into memory corruption. Use it only with tests that cover the
bounds, and document it in the build profile.

**Rules**

* `release` for shipping, `small` for size-constrained targets.
* DCE on; `@export` only for real roots.
* Profile first, then optimise, and keep the numbers.
* `--release-unsafe` needs a test that proves the bounds.

## 36. WebAssembly and assets

### 36.1 Target

```console
$ psc build --target wasm
$ psc run   --target wasm
$ psc test  --target wasm
```

`wasm32-unknown-emscripten` is the only wasm target; `wasm32-wasi` is refused.
Emscripten (`emcc`, `emar`) must be installed and activated (`emsdk`), and the
wasm runtime built once with `./tools/build_runtime_wasm.sh`.

Artifacts for `output = "exe"`: `app.html`, `app.js`, `app.wasm` — they travel
together and must be served over HTTP (`file://` blocks the `.wasm` fetch).

### 36.2 `std.web`

`std.web` is the Emscripten bridge: `console_*`, the main loop, DOM
(`dom`, `event`), canvas, storage, fetch (`http`), websockets, clipboard,
history, location, router, browser, file and crypto. `std.web.url` and
`std.web.security` are pure and also run natively.

Guard browser-only code with `when wasm:`; the inactive branch is removed before
emission.

### 36.3 Assets

```toml
[assets]
dir = "assets"
module = "assets"
embed = true
exclude = ["*.tmp"]
```

`psc assets` writes `src/<module>.pengu` (constants `ASSET_<NAME>` and
`declare`s `_<module>_count`, `_<module>_name`, `_<module>_data`,
`_<module>_size`, `_<module>_string`) and the C files in `build/`. With
`embed = true` the bytes are compiled into the binary; otherwise they are read
from disk at runtime.

```pengu-fragment
import assets

weave main into int:
    let data as ref to frozen void is calling _assets_data with "logo.png"
    let size as usize is calling _assets_size with "logo.png"
    calling print with "{size} bytes at {data}"
    return 0
```

### 36.4 Size

Wasm binaries carry the runtime: measure with `psc build --profile small
--target wasm` and `ls -l build/app.wasm`. `--prune-native` and the `small`
profile are the first levers; `-Oz` via a custom profile is the second.

**Rules**

* Serve the three wasm artifacts together over HTTP.
* Guard browser-only code with `when wasm:`.
* Assets are generated, never hand-edited.
* Measure wasm size in the release job.

## 37. Shipping

### 37.1 The release checklist

- [ ] Version bumped (`pengu.toml`, changelog).
- [ ] `psc check` and `psc test` clean on the supported platforms.
- [ ] `--profile release` build, no new C warnings.
- [ ] Memory-sensitive modules tested under ASan.
- [ ] Docs regenerated (`psc doc`) and validated (`validate_docs.py`).
- [ ] Examples still compile.
- [ ] ABI version and native dependencies stated in the README.
- [ ] LICENSE and THIRD_PARTY.md up to date.
- [ ] Artifacts named and checksummed by the release job.

### 37.2 What users need

A release is not just a binary:

* the README with install, link line and supported compiler range;
* the API docs from `psc doc`;
* the changelog for this version;
* the license and third-party notices.

### 37.3 After the release

Tag it, publish the changelog, and open an issue for the next deprecation
cycle. A release with no follow-up is a release nobody maintains.

**Rules**

* The checklist is the release PR, not a memory aid.
* Users get docs, changelog and license with the artifact.
* Every release starts the next deprecation cycle.

## Appendix A — C to Pengunic

| C idiom | Pengunic |
| --- | --- |
| `for (i = 0; i < n; i++)` | `for i in 0 to n:` |
| `for (i = n - 1; i >= 0; i--)` | build a reversed `list` and `for x in xs:`, or an explicit `while` |
| `if (p == NULL)` | `if p == null:` |
| `if (!ok) return -1;` | `return calling err_of with E.Failed` |
| `char *s = malloc(n + 1)` | `var s as string is ""` + builder |
| `strlen(s)` | `s.len` |
| `strcmp(a, b) == 0` | `a == b` |
| `strcpy(dst, src)` | `set dst is calling scrolls.copy with src` |
| `struct { int x, y; }` | `rune Point:` with fields |
| `typedef struct X X; X *p` | `rune X` + `ref to X` |
| `enum { A, B }` | `omen E:` + `A`, `B` |
| `union` | `omen` with `@packed` payloads |
| `switch (x) { case 1: … }` | `judge x:` + `is 1:` |
| `goto cleanup` | `defer` / `errdefer` |
| `free(p)` | `banish p` |
| `p = NULL` after free | assign `null` explicitly |
| `assert(c)` | `ward.assert` in tests; `panic` for invariants |
| `printf("%d", n)` | `calling print with "{n}"` |
| `snprintf(buf, n, …)` | `StringBuilder` + `finish` |
| `errno` | `result of T to E` |
| `bool ok, T *out` | `result of T to E` |
| `sizeof(T)` | `size of T` |
| `(uint8_t *)p` | `transmute` (documented) or `bytes of` |
| `static` global | `static var` at module level |
| `#define N 10` | `const N as int is 10` |
| `#include <x.h>` | `include "x.h"` in a `.d.pengu` |
| `-lx` | `link "x"` |
| `#ifdef __EMSCRIPTEN__` | `when wasm:` |

## Appendix B — Style checklist

- [ ] File name is `snake_case.pengu`; module name matches.
- [ ] Types are `PascalCase`; runes are nouns.
- [ ] Functions are `snake_case` verbs; predicates read as questions.
- [ ] Constants are `SCREAMING_SNAKE_CASE`.
- [ ] Module order: directives, imports, constants, concepts, types, binds,
      enchantings, functions, helpers, tests.
- [ ] Every public symbol has a `##` docstring with an ownership note.
- [ ] No `+` on strings in a loop; no `+=` accumulation.
- [ ] `let` when the binding never changes; `var` otherwise.
- [ ] Errors are `maybe`/`result`, not `bool` plus out-parameters.
- [ ] Ownership transfers named `take_*`/`consume_*` and documented.
- [ ] No `antiquus` without a contract and a test.
- [ ] No `@export` without a prefix.
- [ ] `psc fmt` applied; `psc check` clean.

## Appendix C — Pull request checklist

- [ ] The change has one purpose and a sentence explaining why.
- [ ] Tests: success, failure, boundary; ownership on error paths.
- [ ] `psc check`, `psc test`, `psc fmt --check` pass.
- [ ] Memory-sensitive code ran under ASan.
- [ ] Docs updated (`##`, reference, changelog) if behaviour changed.
- [ ] No new dependency without a license entry.
- [ ] No debug prints, no commented-out code.
- [ ] The diff is reviewable: no unrelated reformatting.

## Appendix D — Glossary

| Term | Meaning |
| --- | --- |
| owned | the value is responsible for releasing its storage |
| view / borrow | pointer plus length into storage owned by someone else |
| banish | release an owned value; `E0008` if it is not owned |
| payload | the value inside a `maybe`/`result` |
| lowering | the C emitted for a construct |
| rune | product type (struct) |
| echo | sum type (union-like) |
| omen | enumeration of variants, optionally with payloads |
| seal | nominal newtype |
| insignia | prefix for generated C symbol names |
| bounds | valid index range of a sequence |
| DCE | dead code elimination |
| ABI | binary contract between generated C, the runtime and C callers |

## Appendix E — FAQ

**Why is `banish` explicit?**
Because the language has no GC and no borrow checker; explicit release is the
only model the compiler can check at all (`E0008`) without tracking lifetimes.

**Why does copying a string not copy the text?**
Because `PenguString` is a handle. Copy the handle when you mean to share
(borrow), or call `scrolls.copy` when you mean to own a second buffer.

**Why can't I `try` a different error type?**
Error domains are explicit; mapping between them is a decision the caller must
see (`E0045`).

**Why does `as` only work in conditions?**
`as` narrows a `maybe`/`result` in an `if`; numeric conversion is `to`, which
truncates, and `transmute`, which reinterprets bits.

**Are there threads and coroutines?**
Yes. 0.30.0 added first-class threads (`filum.start`, `join`, `detach`, `free`),
0.31.0 added `std.coro` (explicit stackful coroutines with `resume` and `yield`
on the same thread) and 0.53.7 adds `std.reactor`: an explicit `EventLoop` that
calls `epoll_wait`/`poll` and resumes tasks. There is no `async`/`await` keyword
and no hidden scheduler: you create the loop, `spawn` and call `run`. The stdlib
`*_async` variants are functions that suspend the current coroutine and only
work inside a loop task.

**Why is `float` 32-bit?**
It matches C's `float`; use `f64` when precision matters.

**Why does `@export` need a prefix?**
Unprefixed symbols collide with libc and other libraries at link time.

**Why do docs insist on `##`?**
`psc doc` reads only `##`; a `#` comment is invisible in the generated API.

**Why is `many T` not usable?**
It is reserved for variadics and not wired to a call site yet; use `slice of T`.

**Why do tests need ASan?**
The compiler does not detect leaks or double frees; ASan does, and it is
cheaper than a production incident.
