# Gate B — Backend compilable

Fecha: 2026-11-13
Estado: **PASA (suite de backend)**

## Criterio

Gate B exige que todo programa aceptado por el checker compile a Rust y pueda
ejecutarse sin exponer errores crudos de Rust. La suite `crates/pengu-build/tests/gate_b.rs`
cubre un programa representativo por familia del lenguaje 0.6.0 y compila cada
proyecto con Cargo.

## Cobertura de la suite

| Caso | Cubre |
|---|---|
| `hello` | grimoire, print, strings |
| `records` | rune, campos, función, retorno |
| `sums` | enchanting, match de variantes, campos |
| `generic` | función genérica, turbofish, monomorfización |
| `option` | `?T`, `Result`, `?`, grimoire Result |
| `collections` | Vec, Map, indexación, for |
| `closure` | closures, captura, método `@mut` |
| `option-result` | patrón `some` + `bind ... else` |
| `modules` | scroll, visibilidad, paths `::`, record en módulo |
| `pacts` | pact, impl, método `@`, llamada |
| `generic-record` | ADT genérico, impl genérico, `@own` |
| `iterators` | `Iterator`, `map`, `collect`, `for` |
| `map-destructure` | `for (k, v)` sobre Map |
| `nested-destructure` | destructuring anidado de tuplas |
| `user-show` | `Show` de usuario, `print` |

## Resultado

- `cargo test -p pengu-build --test gate_b`: **1 test, 15 programas, PASS**.
- `cargo test --workspace`: **518 tests**, 0 fallos.
- `cargo clippy --workspace --all-targets -- -D warnings`: limpio.
- `cargo fmt --all -- --check`: limpio.
- `check_rewrite.py` / `check_pengu_blocks.py`: limpios.

## Correcciones necesarias

- Emisión de todas las instancias monomorfizadas de funciones genéricas, no solo
  una `LFunction` base (que no existe para genéricas).
- `LExpr::IsVariant` / `LExpr::VariantField` para `match` de sums.
- Lowering de `match` en posición de expresión (no solo sentencia).
- `Ty::Str` como `&str` con `grimoire` usando `&'static str` solo en el retorno
  de `main`.
- `compile` ya no se detiene ante warnings: solo ante errores; antes un warning
  dejaba `rust` vacío y Cargo fallaba con “main not found”.
- `unveil` en módulos para visibilidad de tipos/funciones.

## Límites

- La suite es representativa, no los 146 bloques completos de `LANGUAGE.md`.
- No cubre FFI con una librería externa enlazada, ni macros/proc-macros.
- El sourcemap es por sentencia/expresión, sin columnas.
- Gate B se declara sobre la suite de backend; el corpus completo queda como
  B8/expansión.
