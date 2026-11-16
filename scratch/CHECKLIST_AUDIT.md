# Auditoría del checklist del compilador (Apéndices §11)

Fecha: 2026-11-13
Estado: **B y C completos**.

## B. Checker

| Ítem | Evidencia |
|---|---|
| Módulos/imports/visibilidad | C1, `pengu-hir/tests/names.rs`; `E2004`–`E2006`, `E2012` |
| Sin globales | C1/HIR `E1101`, tests de names |
| Tipos nominales, sin coerción | C2/C3, `pengu-types/tests/check.rs` |
| Inferencia local y literales | C2, `check.rs` |
| Funciones/aridad/retorno/`Never` | C2/C6, `check.rs` |
| Closures/captura/`Fn`/sin `return`/`?` | C5, `pengu-check/tests/ownership.rs` |
| Records/sums/campos/variantes/`..base` | C3, `pengu-types/tests/c3.rs` |
| Patterns/exhaustividad/guards/`@`/`..` | C3 |
| Colecciones `Eq`/`Hash`/Float | C6/C7 |
| Ownership/move/Copy/Clone/borrow/NLL/drop | C4/C5 |
| Refs params/locales/no escapes/métodos | C4/C5 |
| Pacts/métodos/defaults/superpact/coherencia | C6 |
| Genéricos/bounds/turbofish/mono | C6 + B2 |
| Operadores/checked/casts | C6/C7; Cargo `overflow-checks` |
| `?` Option/Result | C2/C7 |
| FFI/foreign/curse/Ptr/CStr/link | C7/B3a |
| Const eval `sigil`/arrays | C7 |
| Derives | C7 |
| Tests `@@test` | C7/B3a |

## C. Codegen

| Ítem | Evidencia |
|---|---|
| Tipos mapeados | B3, `pengu-codegen/tests/codegen.rs` |
| Items (structs/enums/pacts/impls/aliases/módulos) | B3a; `use` resuelto a paths cualificados |
| Funciones/métodos/receptores | B3a–B3d |
| Locals/bindings/assignments | B3b/SSA |
| Control if/match/loop/while/for/break/continue/return | B3b–B3d |
| Operadores/casts/`?`/short-circuit | B3b/B4 |
| Literales/colecciones/interpolación | B4 |
| Patterns | B3d |
| FFI/curse/Ptr/CStr | B3a |
| Tests/derive | B3a/B4 |
| Cargo/Tome/link | B5 |
| Sourcemap | B6 |
| Errores remapeados | B7 |
| Overflow checks | B5: `[profile.dev]`/`[profile.release]` con `overflow-checks = true` |
| No Rust crudo | el backend solo emite desde codegen; errores remapeados |

## Gate B

`crates/pengu-build/tests/gate_b.rs` compila 15 programas representativos.
Informe: `scratch/GATE_B_REPORT.md`. El corpus completo de 146 bloques queda
como B8; no hay pendientes del checklist B/C.
