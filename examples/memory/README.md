# Manual memory management

PenguScript compiles to C99 and manages memory by hand, like Zig, Odin and
Nelua: the compiler inserts no hidden allocation, no deep copy on store and no
release at scope exit. You decide.

| Example | Shows |
|---|---|
| [`01_banish.pengu`](01_banish.pengu) | `banish x` releases the buffer `x` holds. Banishing a literal is a safe no-op (`is_owned == 0`). |
| [`02_defer_banish.pengu`](02_defer_banish.pengu) | `defer banish x` schedules the release at scope exit, LIFO. |
| [`03_derive_nexus.pengu`](03_derive_nexus.pengu) | `derive Nexus` is the opt-in destructor for a rune; `banish doc` runs it. |

Run them with:

```console
$ pengu run examples/memory/01_banish.pengu
```

The reference for the model is [`LANGUAGE.md` §13](../../LANGUAGE.md), and the
executable regression suite is [`tests/test_manual_memory/`](../../tests/test_manual_memory).
