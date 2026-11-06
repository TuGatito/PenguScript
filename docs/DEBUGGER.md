# Debugging PenguScript programs

<!-- toc -->
- [Breakpoints](#breakpoints)
- [Fibers (stackful coroutines)](#fibers-stackful-coroutines)
- [Memory debugging](#memory-debugging)
- [Release builds](#release-builds)
- [Troubleshooting](#troubleshooting)
<!-- /toc -->

`psc debug` builds a program with DWARF debug information and starts it under
`gdb` (or `lldb` with `--llvm`).

```console
$ psc debug .                       # build + gdb
$ psc debug . --llvm                # build + lldb
$ psc debug . -- --flag value       # program arguments
$ psc debug examples/hello.pengu
```

The generated C uses `#line` markers that point at the original `.pengu` files,
so breakpoints, `list`, `next`, `step` and backtraces refer to PenguScript
lines, not to `bundle.c`. Debug builds include `-g` by default (release builds
do not).

## Breakpoints

```console
(gdb) break src/main.pengu:12
(gdb) break my_function            # C symbol, e.g. pengu_main or a Pengu function
(gdb) run
(gdb) bt
```

A backtrace looks like:

```
#0  pengu_main () at src/main.pengu:12
#1  main (argc=1, argv=...) at src/main.pengu:20
```

Symbols are emitted for every live PenguScript function, so `break <name>` works
even without opening the file. Use `info functions pengu` to list them.

## Fibers (stackful coroutines)

Coroutines run on their own stacks (minicoro). When execution is inside a
coroutine, `bt` shows the coroutine frame followed by `mco_*` machinery. Useful
commands:

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
prints the coroutine stack bounds in its overflow diagnostic. A native DAP
debugger with fiber-aware stepping is on the roadmap.

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

* **`No symbol table`** — you built with `--profile=release`; use the default
  debug profile or add `-g` to the profile.
* **Breakpoint moves** — `--no-line-markers` disables `#line`; don't use it when
  debugging PenguScript sources.
* **`ptrace: Operation not permitted`** — `kernel.yama.ptrace_scope` restricts
  attaching to a running process. Run the program *under* gdb (`psc debug`)
  rather than attaching.
