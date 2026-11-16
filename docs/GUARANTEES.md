# Garantías del checker

Este documento enlaza cada garantía de §21 con la prueba que la demuestra.
Las garantías que dependen de ownership viven en `crates/pengu-check/tests/`;
las demás, en `crates/pengu-types/tests/`.

| Garantía | Prueba |
|---|---|
| Sin `null` | `pengu-types/tests/guarantees.rs::null_is_rejected` |
| Sin truthiness | `guarantees.rs::truthiness_is_rejected` |
| Sin variables globales | `guarantees.rs::module_globals_are_rejected` |
| Sin macros de usuario | `guarantees.rs::macros_are_rejected` |
| Sin `dyn` | `guarantees.rs::dynamic_trait_is_rejected` |
| Sin lifetimes escritos | `guarantees.rs::lifetime_annotations_are_rejected` |
| `match` exhaustivo | `guarantees.rs::non_exhaustive_match_is_rejected` |
| Sin `UAF`/uso tras move | `pengu-check/tests/ownership.rs` (move/borrow) |
| Sin doble préstamo mutable | `ownership.rs` (`shared_and_mut_borrow_conflict`) |
| Sin préstamo que escapa | `ownership.rs` (`reference_to_local_cannot_escape`) |
| `curse` solo para FFI | `pengu-types/tests/check.rs::foreign_call_outside_curse_is_rejected` |
| Sin conversiones implícitas | `pengu-types/tests/check.rs` (String/Str y casts) |
| Orden estable de diagnósticos | `pengu-diag` sort y `CheckResult::finish` |
| Warnings no bloquean | `check.rs::warnings_do_not_make_result_dirty` |
| Sin `GC`/runtime | No hay runtime de PenguScript; el backend es Rust |

Las garantías “sin data races” y “sin `UAF`” se apoyan en que el lenguaje no
expone hilos en 0.6.0 y en que el checker de ownership rechaza los movimientos y
préstamos inválidos antes del codegen.
