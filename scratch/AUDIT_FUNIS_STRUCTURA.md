# Auditoría: `funis`, `structura`, `libra`, `iason`, `digestum` y `versio`

Fecha: 2026-11-15. Base: `main` en `30e5f9d`.
Petición (m04348): auditar y verificar las limitaciones documentadas al crear esos
seis módulos, investigar cómo repararlas sin romper lo que ya funciona, plan por
fases en `scratch`, ejecutar fase por fase con commit a `main` y actualizar la
STDLIB. Además: **hay un error del checker que reparar**.

Cómo se verifica cada punto: se ejecuta la sonda de desarrollo

```bash
cargo build --manifest-path scratch/tools/probe/Cargo.toml
./scratch/tools/probe/target/debug/pengu-probe scratch/probes/audit3/<caso>.pengu [--run]
```

La sonda recompila la stdlib embebida (`include_str!`): **hay que reconstruirla**
después de tocar `std/*.pengu`, o se prueba la versión anterior.

---

## 1. Limitaciones verificadas

Estados: ✅ arreglada en esta tanda · ✗ confirmada y diferida (con motivo) ·
— no reproducida.

| # | Limitación documentada | Verificación | Estado |
|---|---|---|---|
| N58 | La coerción `Str` → `String` no llega a los **campos de record**: `Json(kind: "null", …)` falla | `[types] error[PGS-E3001]: tipos incompatibles: String y Str` | ✅ C1 |
| N59 | El cuerpo de una lambda se renderiza desde el AST con `_ => "()"` silencioso: `match`, `while` y llamadas del programa devuelven `()` sin diagnóstico | lectura de `lower_ast_expr` + prueba con lambda que hace `print` | ✗ C4 (documentada; el renderizador cubre if/call/vectores/tuplas/campos) |
| N60 | `structura` bloqueado: `[T: Ord]` no resuelve y con `summon std::opera::Ord` el compilador **desborda la pila** | `summon std::opera::Ord` + `unveil maximo = [T: Ord](…)` → `fatal runtime error: stack overflow` | ✅ C1 (dos causas, §2) |
| N61 | Asignar a un local mientras lo presta la condición de un `match` da `PGS-E4108`; `bind` de `Vec.get` da `E0597` | `match xs.get(0)` + `xs = Vec[v]`, `match m.get("a")` + `m = Map.new()`, `match xs.get(i)` + `i = v`: los tres compilan | — no reproducida en aislamiento |
| N36 | `Iter[T]` no tiene tipo nominal: los adaptadores viven en el checker | sigue igual (20 métodos); `funis.pengu` es documental | ✗ (necesita `rune Iter[T]` con `dyn`) |
| N34 | Métodos con cuerpo sobre `Option`/`Result` no se emiten (`impl<T> Option<T>` es E0116) | sigue | ✗ |
| N55 | Vista `CStr` en `bind` | sigue | ✗ |
| N63 | Devolver `Str` prestado desde una función genérica: `E0106` (falta lifetime) | `maximo__Str(mut a: &str …) -> &str` | ✗ documentada |

### Nuevas, descubiertas al arreglar lo anterior

| # | Hallazgo | Estado |
|---|---|---|
| N62 | `impl` de un `ritual` genérico: los **métodos** se emiten por instancia (`impl crate::Pila<i32>`), pero las **funciones asociadas** (`Pila.new()`) quedan ambiguas (`E0034: multiple applicable items`) y sin ruta (`crate::new()`). Emitir una plantilla `impl<T> Pila<T>` falla porque el `enum __State` interno no puede usar `T` (`E0401`). | ✅ decisión: se omiten las asociadas de impls genéricos y se emite `PGS-E1305` claro; la superficie genérica se ofrece con **funciones libres** |
| N66 | Una llamada cualificada por módulo (`std::via::exists`, `std::structura::pila_push`) no instanciaba los genéricos: el checker solo trataba como «función de item» la ruta de un segmento, así que `[T]` quedaba rígido y aparecía `tipos incompatibles: Vec[Generic] y Vec[Int]`. | ✅ C1: `callee_is_item` acepta cualquier ruta resuelta a `DefKind::Function` |
| N67 | Contenedores ordenados genéricos (`ordinata`, `ordinatum`, montículo): `==` exige el bound `Eq` y no se puede pasar un `T` por valor dos veces sin moverlo; los índices de `Vec` devuelven por valor y `T` no es `Copy`. | ✗ `structura` ofrece pila/cola/cola doble; los mapas ordenados esperan `Clone`/`Copy` en bounds |
| N68 | `[K: Ord, V]`: el parser interpreta `Eq` tras la coma como **otro parámetro** (`PGS-E1301: el genérico Eq no se usa`). La forma válida de un solo bound es `[K: Ord]`. | ✗ documentada (los bounds múltiples necesitan `+`, sin verificar) |
| N69 | El checker de ownership marca `PGS-E4102` cuando la condición de un `if` presta el receptor y una rama lo muta (`if out.is_empty() then … else some(out.remove(0_usize))`): el préstamo de la condición sigue vivo en las ramas. | ✅ evitado en `structura` guardando la condición en un `bind` antes de ramificar (`bind vacia = out.is_empty()`) |

---

## 2. Cómo se reparan (y por qué no rompen lo anterior)

### 2.1 El error del checker: recursión infinita en `implements`

`crates/pengu-types/src/check.rs`, `fn implements(&self, ty, pact)`:

```rust
"Ord" => self.implements(ty, pact) || matches!(ty, …),
```

se llamaba a sí misma con los mismos argumentos: **recursión infinita** y
desbordamiento de pila del compilador en cuanto alguien escribía `[T: Ord]`.

Arreglo: helper `fn implements_equality(&self, ty: &Ty) -> bool` con la lista de
tipos que tienen igualdad (`Bool`, enteros, `Char`, `String`, `Str`) y

```rust
"Eq" => self.implements_equality(ty),
"Ord" => self.implements_equality(ty) || matches!(ty, Ty::Float | Ty::F32 | Ty::F64),
```

Sin recursión, mismo comportamiento observable para todo lo demás.

### 2.2 Genéricos: instanciación en llamadas cualificadas (N66)

Dos arreglos complementarios:

1. `callee_is_item` (checker) acepta `ExprKind::Path(_)` cuando la resolución es
   `Res::Def(def)` con `DefKind::Function`; antes exigía `path.len() == 1`, así
   que `std::structura::pila_push(xs, 1)` no pasaba por `call_generic` y el `T`
   quedaba rígido (`Vec[Generic]` frente a `Vec[Int]`).
2. `call_generic` normaliza los genéricos «sueltos» de la firma con
   `resolve_stray_generics(ty, env, gens)`: si un `Ty::Generic(def)` no está en el
   entorno de inferencia, se busca el parámetro con **el mismo nombre** en
   `signature.generics`. Es defensivo (HIR puede resolver el `T` del tipo con un
   `DefId` distinto) y no cambia nada cuando los `DefId` coinciden.

Además `CheckResult.instantiations: HashMap<Span, Vec<Ty>>` guarda la
instanciación inferida de cada llamada (`call_generic` y las funciones asociadas
de un `impl` genérico), y el LIR/mono la usan para bajar la instancia.

### 2.3 `Ord`/`Eq` en la propia stdlib (N42 + N60)

Los módulos de `std` no pueden importarse entre sí, así que `[T: Ord]` dentro de
`std/structura.pengu` no resolvía `Ord`. Arreglo en `crates/pengu-hir/src/lower.rs`:
`fn builtin_pact(&self, path) -> Option<DefId>` resuelve por nombre los pactos
integrados (`Ord`, `Eq`, `Show`, `Clone`, `Hash`) sin depender de un `summon`.

### 2.4 Campos de record y `Str` → `String` (N58)

`fn record_ty` del checker calculaba `place` y llamaba a `coerce_strings` **antes**
de `unify_at`, solo para los campos de un constructor de `rune`. Los literales de
string (`Str`) y las interpolaciones (`String`) entran así en campos `String` sin
`String.from(...)`.

### 2.5 Funciones asociadas de `ritual` genérico (N62)

`emit_impl` omite las asociadas cuando `!imp.generics.is_empty()`; los métodos se
siguen emitiendo por instancia (lo exige `executes_generic_inherent_impl`). El LIR
emite un diagnóstico propio:

```
error[PGS-E1305]: las funciones asociadas de un `ritual` genérico no están
soportadas; usa una función libre (N62)
```

La superficie genérica de la STDLIB se escribe, por tanto, con funciones libres
que el mono instancia (`pila_push__Int`, …).

---

## 3. Plan por fases

| Fase | Contenido | `std/` que actualiza | Estado |
|---|---|---|---|
| **C0** | Auditoría y verificación con la sonda (esta sección 1) | — | ✅ |
| **C1** | Arreglos de compilador: `Ord` sin recursión, inferencia en llamadas cualificadas, `instantiations` en el checker, `builtin_pact`, coerción en campos de record, N62 con diagnóstico | `std/iason.pengu` (los `String.from` de los constructores ya no hacen falta, se dejan por claridad) | ✅ |
| **C2** | `structura`: pila, cola y cola doble con funciones libres genéricas sobre `Vec[T]`; registro en `FILES`; docs §23 con la superficie real; test de codegen | `std/structura.pengu` (nuevo) | ✅ |
| **C3** | `funis`: documentar que los adaptadores son métodos del checker (N36) y que `funis.pengu` no puede aportar métodos; revisar los 20 adaptadores y sus firmas | `std/funis.pengu` (comentarios), docs §22 | ✅ |
| **C4** | `libra`/`iason`/`digestum`/`versio`: revisar sus tablas de «diferido» y cerrar lo que ya es posible con las capacidades nuevas; anotar lo que sigue bloqueado (N59 en lambdas, N63) | `std/libra.pengu`, `std/iason.pengu`, `std/digestum.pengu`, `std/versio.pengu` | ✅ |
| **C5** | Cierre: `STATUS.md`, auditoría de limitaciones, Gate B y suite completa | — | ✅ |

Criterio de aceptación por fase: `cargo test --workspace` verde,
`cargo clippy --workspace --all-targets` sin warnings y commit en `main` con el
mensaje `C<n>: …`.

---

## 4. Riesgos y controles

- **Regresión de genéricos**: `executes_generic_inherent_impl` (métodos de
  `rune` genérico) y `generic_functions_with_bounds_and_inference_compile_and_run`
  cubren los dos caminos; el segundo se apoya en la inferencia nueva.
- **Campos de record**: la coerción solo actúa con `place` (`Path`/`Field`/`Index`);
  un temporal (`String.from(...)`) sigue yendo por `unify_at` y da el diagnóstico
  de siempre.
- **Corpus**: los programas del corpus que declaran funciones genéricas ahora
  compilan (59 → 62); la tupla esperada de `gate_b_corpus` se actualiza con el
  recuento real (4/12/63/5).
