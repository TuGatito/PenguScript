# Debugging PenguScript programs

<!-- toc -->
- [Quick start](#quick-start)
- [The DAP adapter](#the-dap-adapter)
- [VS Code](#vs-code)
- [Neovim](#neovim)
- [What works today](#what-works-today)
- [Pretty printers](#pretty-printers)
- [Source mapping and stepping](#source-mapping-and-stepping)
- [Fibers (stackful coroutines)](#fibers-stackful-coroutines)
- [Panics](#panics)
- [Memory debugging](#memory-debugging)
- [Release builds](#release-builds)
- [Troubleshooting](#troubleshooting)
<!-- /toc -->

PenguScript compiles to C with DWARF line information and `#line` markers, so
the C toolchain already gives you real source-level debugging. There are two
front ends:

| Front end | Use it for |
| --- | --- |
| `psc debug` | Interactive `gdb`/`lldb` in a terminal, fiber dumps, `p`/`x` inspection. |
| `psc debug-adapter` | A DAP server for VS Code, Neovim, Zed, Helix, Emacs, etc. |

Both debug the same binary and use the same `.pengu` line table.

## Quick start

Build with the debug profile first (the default):

```console
$ psc build .
$ psc debug .                    # build + gdb
$ psc debug . --llvm             # build + lldb
$ psc debug . -- --flag value    # program arguments
```

`psc debug` compiles the target, changes to its directory, enables fiber
tracing (`PENGU_FIBER_TRACE=1`) and starts `gdb -q -x psc-gdbinit --args
<artifact>`. The generated `psc-gdbinit` defines `pengu-fibers`.

For an editor, build the executable once and point the launch configuration at
it:

```console
$ psc build . --profile=debug
$ psc debug-adapter             # normally launched by the editor, not by hand
```

`program` must be the **compiled executable**, not the `.pengu` source. The
adapter rejects a `.pengu` path with a message that tells you to run
`psc build` first.

## The DAP adapter

`psc debug-adapter` speaks the [Debug Adapter Protocol](https://microsoft.github.io/debug-adapter-protocol/)
over stdio. It launches `gdb -q -i=mi2` and translates DAP requests to GDB/MI.

Launch configuration fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `program` | string, required | Compiled executable. Relative paths resolve against `cwd`. |
| `args` | string[] | Arguments passed to the program. |
| `cwd` | string | Working directory for the debuggee and relative source paths. |
| `stopOnEntry` | boolean | Stop at the first PenguScript statement (`pengu_main`). |
| `source` | string | Optional main `.pengu` file, useful for diagnostics. |
| `gdbPath` | string | GDB executable; default `gdb`. |
| `printers` | string | Optional path to `tools/pengu_printers.py`. If omitted and `<cwd>/tools/pengu_printers.py` exists, it is loaded automatically. |

The adapter sets `pagination off`, `confirm off`, `breakpoint pending on` and
`print pretty on` before inserting breakpoints.

### Supported requests

- `initialize`, `launch`, `configurationDone`, `disconnect`, `terminate`
- `setBreakpoints` (line, `condition`, `hitCondition`; verified flag)
- `setExceptionBreakpoints` (accepted; no filters yet)
- `continue`, `next`, `stepIn`, `stepOut`, `pause`
- `threads`, `stackTrace`, `scopes`, `variables`, `evaluate`
- `output` and `stopped` events (`breakpoint`, `step`, `entry`, `pause`,
  `exception`), `terminated`

`next` filters repeated stops on the same PenguScript line, so a `do:` block or
a comprehension does not feel like a single step through generated C. The
filter is bounded to 50 automatic steps to avoid an infinite loop on broken
line information.

### What is not supported yet

These are deliberate v1 limits, not silent failures:

- **Logpoints** and `logMessage`.
- **Data breakpoints / hardware watchpoints**, watch expressions and
  `variablesReference` children. Aggregate values show their type (`<PenguString>`)
  instead of expanding; use `evaluate` or the `psc debug` GDB console for `p`.
- **Exception filters** for `spark.panic`; see [Panics](#panics).
- **Reverse debugging**, disassembly, memory reads and instruction breakpoints.
- **Coroutine pseudo-threads**: `std.coro` runs on minicoro stacks, not OS
  threads, so DAP sees one thread. Use `psc debug` + `pengu-fibers` for them.
- **LLDB in the adapter**: `psc debug-adapter` uses GDB/MI. On macOS use
  `psc debug --llvm` for LLDB; an `lldb-dap` integration is a separate task.
- `evaluate` evaluates **C expressions**, not PenguScript. Names of locals and
  aggregates work; PenguScript-only syntax (`and`, `or`, `not`, `calling`, `is`)
  does not.

## VS Code

Install the PenguScript extension (`vscode-extension/`). It contributes the
`pengu` debugger type and launches `psc debug-adapter` with the resolved `psc`
executable.

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "pengu",
      "request": "launch",
      "name": "Debug PenguScript",
      "program": "${workspaceFolder}/build/app",
      "cwd": "${workspaceFolder}",
      "stopOnEntry": false,
      "args": []
    }
  ]
}
```

Use **Run and Debug** (`F5`). Breakpoints in `.pengu` files are sent as absolute
paths; the adapter resolves the DWARF `#line` paths back to the workspace.

If your `psc` is not on `PATH`, set `pengus.executablePath` in VS Code settings;
the debugger factory uses the same resolution as the language client.

## Neovim

`nvim-dap` speaks DAP directly. Add this to your Lua config:

```lua
local dap = require('dap')
dap.adapters.pengu = {
  type = 'executable',
  command = 'psc',
  args = { 'debug-adapter' },
}
dap.configurations.pengus = {
  {
    type = 'pengu',
    request = 'launch',
    name = 'Debug PenguScript',
    program = '${workspaceFolder}/build/app',
    cwd = '${workspaceFolder}',
    stopOnEntry = false,
    args = {},
  },
}
```

The filetype is `pengus` (the extension uses `pengus` as its language id).
`nvim-dap-ui` is recommended for the scopes/variables panel; without it
`nvim-dap` still provides breakpoints and stepping.

## What works today

| Feature | Status |
| --- | --- |
| Line breakpoints, `condition`, `hitCondition` | Yes |
| Continue / next / step in / step out / pause | Yes |
| Call stack, locals, `evaluate` | Yes (C expressions) |
| Multiple source files and absolute paths | Yes |
| Pretty printers in GDB (`p`) | Yes for strings, omens, runes, `Rc`/`Arc` |
| Expanded lists/maps/`maybe`/`result` | Metadata/limit: shown as `<Type>` |
| `spark.panic` breakpoint | Manual: `break spark_pengu_panic` |
| `std.filum` threads | One DAP thread; GDB sees OS threads |
| `std.coro` fibers | Single DAP thread; `pengu-fibers` in `psc debug` |

## Pretty printers

`tools/pengu_printers.py` registers GDB Python pretty printers by **layout**, so
it also works when the C type is anonymous:

```console
(gdb) p label
$1 = "ok"
(gdb) p st
$2 = State.Busy { load: 7 }
(gdb) p xs
$3 = PenguList(len=3, elem_size=4)
```

Strings print without the `{data, len, is_owned}` noise. Omens resolve their
`tag` enum to the variant name and flatten the active payload. `fundere` embeds
are shown as ordinary fields. `Rc`/`Arc` show the payload address plus
`strong`/`weak` counts from the header immediately before the payload.

The adapter loads the printers automatically when the launch `cwd` contains
`tools/pengu_printers.py`; otherwise pass `printers` explicitly. They affect the
GDB console (`psc debug` or the Debug Console's `-exec` commands). DAP
`variables` reports names and types for aggregates; it does not expand them in
v1.

## Source mapping and stepping

The generated C contains `#line N "path/to/file.pengu"` markers. GDB reports
PenguScript files and lines, not `bundle.c`. The C `main` wrapper is marked
`<psc-runtime>:1` so it does not appear as a fake user frame.

Step-over is filtered in the adapter: if GDB stops again on the same
PenguScript line (common with `do:`, `judge` and comprehensions that expand to
several C statements), the adapter silently issues another `-exec-next` until
the line changes. `next` from a line that expands to a statement expression may
still visit an earlier line once; that is a limitation of the current line
table, not of the adapter.

`#line` paths are stored relative to the compilation directory (normally the
project root). Keep `cwd` at the project root, or use `fullname` paths from MI;
the adapter resolves relative stack paths against `cwd`.

## Fibers (stackful coroutines)

Coroutines run on their own stacks (minicoro). When execution is inside a
coroutine, `bt` shows the coroutine frame followed by `mco_*` machinery.

`psc debug` enables `PENGU_FIBER_TRACE=1` and loads a `pengu-fibers` command
that lists every live coroutine with its stack bounds and the stack captured at
its **last yield**:

```console
(gdb) pengu-fibers
[PENGU] fibers: 1 live on this thread
  fiber 0x7ffff7a00000 state=suspended owner=1 stack=0x7ffff7a00620 size=65536
    #0 app(coro_yield+0x9)
    #1 app(main_worker+0x1b)
    #2 app(coro_run_box_inst20+0x28)
```

`bt` inside a running coroutine shows the live stack; `pengu-fibers` covers the
suspended ones. Frames are captured by walking the frame-pointer chain, not by
libgcc's unwinder (minicoro's sentinel frame crashes it). If you build manually,
keep `-g -fno-omit-frame-pointer` and link with `-rdynamic` to get names.
Coroutines that were never resumed have no captured stack. Set
`PENGU_CORO_STACK_SIZE` (bytes) to reproduce stack-overflow reports; the runtime
prints the coroutine stack bounds in its overflow diagnostic.

DAP reports one thread for the whole process. Debugging an individual coroutine
still requires `psc debug` + `pengu-fibers`; pseudo-thread support is future
work.

## Panics

`spark.panic` writes `[PANIC] ...` to stderr and calls `exit(1)`; it is not a C++
exception and does not raise `SIGABRT`. To stop at the panic site:

```console
(gdb) break spark_pengu_panic
(gdb) run
(gdb) bt
```

The symbol is module-prefixed (`spark_pengu_panic` for `std.spark`). Set the
breakpoint before `run`; pending breakpoints are enabled by the adapter and by
`psc debug`.

## Memory debugging

Combine with sanitizers (`docs/SANITIZERS.md`):

```console
$ psc build . --sanitize=address --profile=debug
$ gdb --args ./build/app
```

## Release builds

`--profile=release` omits `-g` and strips the binary (`-s`). To keep symbols
while optimising, use a custom profile:

```toml
[profiles.profile]
cflags = ["-O2", "-g"]
```

## Troubleshooting

* **`program must be an executable`** — point `program` at the compiled binary
  (`build/app`), not at `main.pengu`. Run `psc build . --profile=debug` first.
* **`No symbol table`** — you built with `--profile=release`; use the default
  debug profile or add `-g` to the profile.
* **Breakpoint moves / is unverified** — `--no-line-markers` disables `#line`;
  don't use it when debugging PenguScript sources. Also make sure `cwd` is the
  project root used at build time.
* **`ptrace: Operation not permitted`** — `kernel.yama.ptrace_scope` restricts
  attaching. Run the program under the debugger, as both front ends do.
* **Adapter exits immediately** — run `psc debug-adapter` by hand with a launch
  request; check that `gdb` is installed and that `program` exists. The adapter
  reports the failing request in the Debug Console.
* **Aggregate shows `<PenguString>`** — expected in v1; use `evaluate` or the
  GDB console for `p label`. Pretty printers cover the console path.
