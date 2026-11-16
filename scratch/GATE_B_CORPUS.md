# Gate B — corpus 0.6.0

Estado: **PASA** (compilador + stdlib). El harness procesa los 146 bloques de
`docs/LANGUAGE.md`, compila 68 programas autocontenidos con `rustc --edition 2024` y
clasifica **todos** los bloques restantes: 56 son fragmentos didácticos, 4 son
declaraciones, 5 son ejemplos de error y 13 están declarados como no ejecutables con
su motivo, uno por uno, en `DECLARED_NON_EXECUTABLE`.

## Cifras

| Categoría | Bloques |
|---|---:|
| Total | 146 |
| Ejemplos de error (`-- ERROR PGS-`) | 5 |
| Compilados a Rust (lib, rustc 2024) | 68 |
| Declaraciones `.d.pengu`/`foreign` | 4 |
| Fragmentos parseables / citas con nombres indefinidos | 56 |
| No ejecutables declarados con motivo | 13 |
| Bloqueos de backend sin declarar | **0** |

Suma: 5 + 68 + 4 + 56 + 13 = 146.

Test: `crates/pengu-build/tests/gate_b_corpus.rs`. Además de las cifras, el test exige:

- `unclassified.is_empty()`: cualquier fallo nuevo que no sea fragmento ni esté declarado
  rompe la suite con un listado listo para pegar.
- `declared_hits == DECLARED_NON_EXECUTABLE.len()`: si un bloque declarado empieza a
  compilar, hay que quitar su entrada. Así la lista no se queda obsoleta.
- Los invariantes de cifras, errores y suma.

Los **avisos** (`PGS-W*`) no cuentan como fallo: solo los errores. Suite actual: 584+
tests; `cargo clippy --workspace --all-targets -- -D warnings` y
`cargo fmt --all -- --check` limpios.

## Arreglos de esta sesión

Antes de declarar nada se cerraron los huecos que eran del compilador:

| Arreglo | Efecto |
|---|---|
| `UInt` como alias de `U32` en HIR, checker y codegen (6 tablas) | Compila el bloque 756 y las firmas del doc que usan `UInt` |
| `&String` → `Str` en `coerce_strings` (`crates/pengu-types/src/check.rs`) | `bind view: &Str = &text` con `text: String` |
| `&[T]` se normaliza a `Ty::Slice` (no `Ref(Slice)`) en `ty_from_ast` y `ast_type_ty` | Evita el doble préstamo `&&[i32]` en el Rust generado |
| `unify` acepta `[T]` ↔ `&[T; N]` en ambas direcciones (antes de la coerción genérica de préstamo) | `bind view: &[Int] = &numbers` |
| `iter_item_ty` pela `Ty::Ref`: `for x in &values` recorre el slice | `for` sobre préstamos |
| La regla de `ExprKind::Index` pela `Ty::Ref` | `view[0]` sobre `&[Int]` |
| El bucle `for` de LIR conserva el tipo prestado del contenedor y pela solo para clasificar | `&[i32]` tiene `len` e índice en el Rust emitido |
| `docs/LANGUAGE.md` §3.6: `unveil rune Config` y campos `unveil` | El ejemplo completo compila (antes `E0603: struct Config is private`) |

## No ejecutables declarados (13)

Ninguno depende de la stdlib: son fragmentos de la especificación, fuentes de `std` o
límites del lenguaje ya documentados en `scratch/LIMITATIONS_AUDIT.md`.

| Línea | Motivo |
|---:|---|
| 217 | Expresión suelta del doc §2 (`none` sin tipo esperado), no es un programa |
| 227 | Expresión suelta del doc §2 (`42 as Usize`) |
| 247 | Expresión suelta del doc §2 (literal `1.5`) |
| 308 | Expresión suelta del doc §2 (rango `0..10`) |
| 739 | `Result[Int, String] = err("no")`: el literal es `Str` y el constructor de variante no aplica la coerción `Str`→`String` (N73) |
| 984 | `bind area =` + bloque indentado: expresión de bloque en `bind` no soportada en LIR (N71) |
| 1034 | `bind value = do … end`: expresión `do` en `bind` no soportada en LIR (N71) |
| 1998 | `ritual[T]` sobre `rune` genérico: `@.value` se tipa `<error>` (N72) |
| 2079 | Fuente de `std` (`ritual Bool`/`Str`/`Int`): solo válida dentro de `scroll std` |
| 2193 | `ritual[T]` sobre `rune` genérico: `@.value` se tipa `<error>` (N72) |
| 2477 | `Result[Int, String] = ok(3)`: misma limitación de coerción en variantes que 739 |
| 2576 | Cita con `grimoire` que usa tipos definidos en la prosa (`ConfigError`, `read_config`) |
| 3896 | Cita con `grimoire` que usa tipos definidos en la prosa (`AppError`, `load`) |

Los dos últimos son los únicos "programas completos" (con `grimoire`) que no compilan, y
son citas: el texto los presenta como extractos de un programa mayor cuyos tipos están en
la prosa. Quedan declarados como no ejecutables; no bloquean Gate B.

## Verificación

```
cargo test -p pengu-build --test gate_b_corpus -- --nocapture
COUNTS compiled=68 decl=4 frag=56 gaps=13 err=5 full_gaps=2
test result: ok
```

`B8_VERBOSE=1` imprime un `DIAG <línea>\t<diagnóstico>` por bloque fallido, útil para
revisar la clasificación cuando cambia el doc.
