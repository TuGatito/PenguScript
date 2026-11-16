# Backend status — B3/B4–B7

Fecha: 2026-11-13

## Hecho

- Receptores `@`, `@mut`, `@own` en `LExpr::Method` con `def` y codegen
  distinto (`borrow`, `borrow_mut`, `move`). Tests de mutación y consumo.
- `@.campo = valor` baja a `LStmt::SetField`.
- B4 completo: `Show` runtime para primitivos, `String`, `str`, `&str`, `()`,
  `&T`, `Box`/`Rc`/`Arc`, arrays/slices, `Vec`, `Map`, `Set`, `Option`, `Result`,
  tuplas 2–4 y `Ordering`; `print`/`format` e interpolación `#{}`; `panic`/`assert`
  con formato; implementaciones de usuario de `Show`.
- `SourceMap` por sentencia/expresión con marcadores; `lookup`, `to_json`.
- `pengu-project`: `to_cargo_toml`, `build_rs`, `[[bin]]`, features y deps.
- `pengu-build`: `compile`, `emit`, `build`/`run`/`test` con Cargo; `BuildReport`; `remap_rustc_diagnostics`.
- Tests: **518 workspace**, 43 codegen, 9 build, 13 project.

## Pendiente / límites

- `T` no-`Copy` devuelto desde `@`/`@mut` se rechaza con `PGS-E4105`; el
  usuario debe usar `@own`. La regla cubre cuerpos que devuelven `@.campo`.
- Locales bajan a **SSA/phi** (`enum __State` por bloque + `loop/match`), sin
  `Option<T>` ni `expect`; las variantes con préstamos usan `__State<'a>`.
  El estado se construye solo con locales vivos; Rust verifica la inicialización.
- `Drop` de usuario no existe; solo drop automático de Rust.
- Sourcemap por sentencia/expresión; no hay mapeo por columna.
- `pengu-build` usa Cargo; `build.rs` se genera y Cargo lo ejecuta.
- Gate B: **PASA** sobre la suite representativa `crates/pengu-build/tests/gate_b.rs` (15 programas). Ver `scratch/GATE_B_REPORT.md`. No cubre aún los 146 bloques completos.

## Próximo

1. Gate B sobre corpus y ejemplos; B8 remapeo de errores a nivel de span.
