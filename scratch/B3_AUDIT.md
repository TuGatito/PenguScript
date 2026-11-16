# B3 — Auditoría de cierre

Fecha: 2026-11-13. Base: `0cbadbf` + monomorfización de métodos de impl.

## Estado

| Parte | Estado | Evidencia |
|---|---|---|
| B3a items/módulos/paths | ✅ | 10 tests codegen; módulos, FFI, tests, grimoire |
| B3b expresiones/locales | ✅ | 13 tests; records, campos, Vec, `?`, casts, `Result` |
| B3c métodos/`Str` | ✅ | métodos inherentes, `@` como `self`, `Str = &str` |
| B3d closures/iteradores/for | ✅ | closures con captura, `Iterator`, `Map`/`Set`, `for` patterns y anidados |
| impls genéricos | 🔶 | `impl<T>` + instancias concretas; `@ -> T` con `T: Copy`; no-`Copy` requiere `@own`/clone |
| Gate B completo | ❌ | runtime/Drop, Cargo/Tome/link, sourcemaps, build/run/test |

## Deuda restante

1. **Receptores de método en llamadas.** ✅ `LExpr::Method` lleva `def`; codegen distingue `@`/`@mut`/`@own` (`lower_borrowed`/`lower_borrowed_mut`/move).
2. **Cuerpos genéricos no-`Copy`.** `@ -> T` con `T` no-`Copy` no puede mover el campo desde `&self`; la política es usar `@own` explícito. No se inserta `clone` implícito.
3. **`expect` oculto.** Locales `Copy` se leen con `expect`; el criterio B3 pide no ocultar `clone`/`expect`.
4. **`Map.iter()`/`Set.iter()`** consumen para mantener item por valor; documentado, pero no es préstamo.
5. **Fases posteriores.** B4 runtime/`Drop`/`Show`; B5 Cargo/Tome/link; B6 sourcemaps/errores `rustc`; B7 build/run/test; Gate B.

## Validación

- `cargo test --workspace`: 489.
- `cargo clippy --workspace --all-targets -- -D warnings`: limpio.
- `cargo fmt --all -- --check`: limpio.
- `check_rewrite` 160 diagnósticos/33 garantías; `check_pengu_blocks` 146.

## Conclusión

B3 como *codegen base* está prácticamente cerrado, pero **no** se declara completo: quedan receptores de método en llamadas y la política explícita para `T` no-`Copy`. Gate B sigue pendiente por B4–B7.
