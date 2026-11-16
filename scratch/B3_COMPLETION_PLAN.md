# B3 — Plan para completar el codegen base

Estado: **B3a ✅ / B3b ✅ / B3c 🔶 (métodos y `Str`) / B3d pendiente**.
B3a cubre metadata, módulos, paths e items; B3b expresiones y locales; B3c
métodos y `Str` prestado; B3d cubre closures, iteradores, impls genéricos y
runtime.
Este documento fija qué falta, en qué orden resolverlo y cómo saber que B3
está cerrado.

Base: `128f66d` (B3b) + el commit de B3c.
Tests actuales: 474 workspace; 14 de codegen.

## 0. Estado B3a (2026-11-13)

Implementado:

- `Generated.diagnostics` propaga errores/warnings de HIR/LIR.
- HIR guarda `TestInfo`, `grimoires` y `foreign_abis`.
- Módulos `scroll` anidados, paths `crate::...` y visibilidad.
- `@@test`, `grimoire`, `foreign` agrupado por ABI, `curse` unsafe, pacts con
  métodos por defecto.
- 13 tests de codegen que compilan el Rust generado con `rustc`.

Pendiente para B3c: closures/captura, métodos/iteradores, `for` sobre
iteradores, impls genéricos, `Str` con lifetime de préstamo, `Drop` y runtime
`Show`/`print`.

## 1. Qué significa "completar B3"

B3 debe convertir **todo item declarado en HIR** y **todo cuerpo LIR válido** en
Rust compilable, preservando:

- jerarquía de módulos, visibilidad y nombres;
- metadata de items (`@@test`, `grimoire`, `foreign`, `curse`, `@@derive`);
- semántica de locals/moves (sin clones ni `expect` ocultos que cambien el
  programa);
- diagnóstico explícito para cualquier cosa que el backend no pueda emitir.

B3 **no** incluye todavía: runtime `Show`/`print` (B4), Cargo/Tome/link (B5),
sourcemaps (B6) ni build/run/test end-to-end (B7).

## 2. Hallazgos concretos

### 2.1 Módulos planos

`generate` recorre `krate.adts`, `krate.aliases`, `krate.consts`, `krate.pacts`,
`krate.impls` y `program.functions` globalmente. No usa `Module.items` ni
`Module.parent`, así que todos los items salen en la raíz.

Consecuencias:

- dos `scroll` con el mismo nombre de tipo/function colisionan;
- los paths `crate::a::Type`, `super::...` y los `summon` no se reflejan;
- `call_name` y `ast_type` emiten nombres desnudos, no paths;
- la visibilidad `unveil(scroll)`/`unveil(tome)` se aplica al item, pero no a
  un módulo inexistente.

HIR sí tiene la información: `Module { parent, items, def }` y cada `Def` tiene
`module`. Falta un `module_path(krate, ModuleId) -> Vec<String>` y emitir
recursivamente.

### 2.2 Metadata que HIR descarta

- `@@test`: `build_item(ItemKind::Test)` crea un `DefKind::Function` normal.
  Se pierden `TestOption { should_panic, ignore }`, así que no se puede emitir
  `#[test]`, `#[should_panic(expected = ...)]` o `#[ignore = ...]`.
- `grimoire`: se crea también como `DefKind::Function` con nombre `"main"`.
  Se pierde el hecho de que es el entry point y su retorno `Result`; el codegen
  emite `pub fn main()` sin wrapper de error/salida.
- `foreign`: `Foreign { abi, items }` se reduce a `foreign_fns: HashSet<DefId>`.
  Se pierde `abi` (`C` vs `system`) y no se puede emitir `#[link]` (B5, pero el
  ABI sí es B3).
- `curse`: `curse_fns` existe, pero `emit_function` no emite `unsafe fn`.
- `pact`: `PactDef.methods` conserva firmas, pero no los cuerpos por defecto;
  `emit_pact` solo emite `fn ...;`.

Solución: añadir side-tables a `HirCrate` (`tests: HashMap<DefId, TestInfo>`,
`grimoires: HashSet<DefId>`, `foreign_abis: HashMap<DefId, String>`) o ampliar
`Def`/`DefKind`. No duplicar datos que ya están en AST.

### 2.3 LIR incompleto para programas reales

`LExpr` actual: `Unit`, `Bool`, `Int`, `Float`, `Str`, `Local`, `Binary`,
`Unary`, `Call`, `Tuple`.

Faltan, entre otros:

- `Field`, `Index`;
- `Array`, `Struct`, `Variant`;
- `Cast`, `Range`;
- `?` / `Option`/`Result` constructors;
- closures;
- `for` sobre iteradores;
- asignación a lugar (`Place`) más allá de locals;
- `Drop`;
- `Origin`/source spans.

`lower_expr` B1 marca varios de estos como `PGS-E1901` ("expresión no soportada
en LIR B1") y **no** materializa una `LFunction` si hubo diagnóstico. El
codegen actual ignora `program.diagnostics`: `generate` siempre devuelve
`Generated { diagnostics: vec![] }`. Es un fallo de contrato: un programa que
el frontend acepta puede producir Rust incompleto sin diagnóstico.

Decisión necesaria: B3 debe extenderse con el subconjunto de LIR que exige
"tipos/items" (campos, records, variantes, arrays, índices, casts y `?`) o
reducir formalmente su alcance y mover esas expresiones a B4/B7. La opción
recomendada es ampliar LIR ahora: el codegen no puede ser correcto sin ellas.

### 2.4 Locals y moves

`emit_function_body` declara cada local no-param como:

```rust
let mut __lN: Option<Ty> = None;
```

y `LExpr::Local` lee:

```rust
__lN.clone().expect("local no inicializado")
```

Problemas:

- exige `Clone` para todo tipo, incluso records sin `Clone`;
- clona `String`/`Vec`/`Map` en cada lectura, cambiando semántica y rendimiento;
- después de un move, el `Option` sigue `Some` y el `expect` no detecta el
  movimiento (el checker sí, pero el Rust generado no lo refleja);
- no hay estrategia para `@own`, `Drop` ni locales prestados.

Alternativas:

1. **SSA por local**: una variable Rust por asignación y phi en joins; correcto
   pero requiere reconstruir el CFG.
2. **Option + take/as_ref tipado**: `take()` para owned, `as_ref()`/`copied()`
   para `Copy`, `as_mut()` para `morph`; el codegen consulta `Ty` y `is_copy`.
3. **Codegen estructurado desde AST**: genera `if`/`match`/`while` normales y
   deja que Rust resuelva la inicialización; evita el CFG artificial, pero
   duplica lógica y se aleja de LIR.

Recomendación: opción 2 para B3 (mínima invasión), con tests de move/borrow;
evaluar SSA si aparecen casos que `Option` no pueda expresar.

### 2.5 Genéricos, pacts e impls

- `emit_impl` busca la primera `LFunction` con `def == method`; para un método
  de `impl<T>` monomorfizado hay varias instancias y el cuerpo elegido puede
  ser el de `T=Int` para todas.
- `emit_pact` no emite métodos por defecto.
- `emit_impl` no maneja `Self`/tipos asociados (no existen en 0.6.0, pero sí
  `Self`).
- `generics` ya resuelve bounds por nombre; falta comprobar que el `impl`
  genérico use los mismos parámetros que el tipo.

Solución: para B3, emitir métodos de `impl` desde el AST/HIR genérico, no desde
una instancia monomorfizada; o generar un `impl` por instancia (especialización)
y prohibir `impl<T>` no monomorfizable. Hay que decidir y testear.

### 2.6 Tipos y visibilidad

- `ast_type` no resuelve paths importados; `Point` de otro módulo sale como
  `Point` y no compila.
- `Str` se emite como `&'static str`; el plan pide `&str` en params/locales.
  `&'static` es demasiado restrictivo y no modela préstamos.
- `visibility` de `rune`/`enchanting` se aplica al tipo, pero no a módulos
  (no existen aún).
- `Ptr`/`CStr` se mapean, pero no hay validación de contexto en codegen.

Solución: resolver paths contra `Scope`/`DefId` y cualificar; usar `&str` con
elipsis/lifetime solo donde sea legal; no emitir `&'static` por defecto.

### 2.7 Contrato de errores

`Generated.diagnostics` siempre vacío. Si `program.diagnostics` no está vacío,
`generate` debe:

1. devolver esos diagnósticos;
2. no emitir código parcial como si fuera válido;
3. no producir Rust que no corresponda a una función bajada.

### 2.8 Cobertura de tests

Los 4 tests actuales cubren:

- record + función;
- enum + alias;
- impl + const;
- foreign `extern "C"`.

Faltan: módulos anidados, `summon`/paths, `@@test`, `grimoire` Unit y Result,
`curse`, pacts con default, impl genérico, campos/índices/records/variantes,
arrays, `?`, closures, `for` iteradores, visibilidad y errores de codegen.

## 3. Plan de ejecución

### B3.1 — Contrato y metadata (1–2 días)

1. `Generated` pasa a incluir `diagnostics` reales y un `files: Vec<GeneratedFile>`
   si se decide multiarchivo (mínimo: un `source` y un `path`).
2. Añadir a HIR:
   - `tests: HashMap<DefId, TestInfo>`;
   - `grimoires: HashSet<DefId>`;
   - `foreign_abis: HashMap<DefId, String>`.
3. `generate` corta si `program.diagnostics` o `krate.diagnostics` no están
   vacíos; los copia a `Generated.diagnostics`.
4. Tests de contrato: LIR con error no produce Rust válido silencioso.

### B3.2 — Módulos y paths (2–4 días)

1. `module_path(krate, id)` y `def_path(krate, def)`.
2. Emitir `mod` recursivamente desde `krate.modules`; respetar `Visibility`.
3. Colocar cada item en su módulo (`Def.module`) y no en la raíz.
4. `call_name`/`ast_type` cualifican con `crate::...`/`super::...`.
5. Resolver paths de tipo con `Scope` (o `Resolution` de campos/firmas) y
   emitir el nombre cualificado.
6. Tests: dos `scroll` con tipos homónimos, `summon`, `unveil(tome/scroll)`.

### B3.3 — Items completos (2–4 días)

1. `@@test`: `#[test]`, `#[should_panic(expected = "...")]`, `#[ignore = "..."]`.
2. `grimoire`: `fn main()` sin `pub`; wrapper para `Result` (stderr + exit 1).
3. `foreign`: `extern "C"`/`"system"` según `abi`; `#[link]` queda para B5.
4. `curse`: `unsafe fn` y bloques `unsafe`.
5. `pact`: métodos por defecto (cuerpo LIR) si existen.
6. `impl`: métodos con `Self`, genéricos y visibilidad; decidir estrategia de
   instancias genéricas.
7. Tests de compilación para cada item.

### B3.4 — LIR de expresiones (5–8 días)

1. Extender `LExpr`/`LStmt` con `Field`, `Index`, `Array`, `Struct`, `Variant`,
   `Cast`, `Range`, `?`, constructores de `Option`/`Result`, closures.
2. Extender `lower_expr` desde HIR; cada extensión con test de LIR.
3. Codegen de patrones/records/variantes/arrays/índices; mapear a Rust.
4. `for` sobre iteradores y `Collect`/`Map` literals.
5. Tests de programas reales: `Point`, `Shape`, `Vec`, `Map`, `Option`, `?`.

### B3.5 — Locals correctos (2–4 días)

1. Implementar la estrategia elegida (`Option` tipado o SSA).
2. `@own`/move/borrow/drop: no clonar; `take`/`as_ref` según tipo y contexto.
3. Tests de move de `String`/record, lectura de `Copy`, `morph`, `@mut`, `@own`.

### B3.6 — Golden + Gate B3 (2–3 días)

1. Golden snapshots de Rust generado por item.
2. Compilar cada golden con `rustc --edition 2024 --crate-type lib` (o bin).
3. Corpus de programas aceptados por checker y por LIR; los no soportados
   deben tener diagnóstico, no Rust inválido.
4. Revisar que no se emita `unwrap`/`clone`/`expect` ocultos.
5. Actualizar plan/changelog; marcar B3 ✅ solo con todos los tests.

## 4. Orden recomendado

1. B3.1 contrato/metadata.
2. B3.2 módulos/paths.
3. B3.3 items.
4. B3.5 locals (antes de ampliar demasiadas expresiones).
5. B3.4 expresiones.
6. B3.6 golden/gate.

B3.5 antes de B3.4 evita escribir codegen de expresiones sobre una base de
locals que cambia la semántica.

## 5. Decisiones abiertas

- B3 se divide en B3a (items), B3b (expresiones/locales) y B3c (closures/iteradores/impls genéricos).
- ¿`impl<T>` se emite genérico o se especializa por instancia?
- ¿Locals con `Option` tipado o SSA?
- ¿`Generated` es un archivo o varios (`files` + `path`)?
- ¿`Str` usa `&str` con elipsis o un lifetime explícito interno?
- ¿`grimoire: Result` wrapper se genera en B3 o B4 (runtime de errores)?

## 6. Criterio de cierre

B3 se considera completo cuando:

- todos los items de §19 se emiten y compilan;
- módulos/imports/visibilidad se preservan;
- tests/grimoire/foreign/curse/pacts/impls tienen tests de compilación;
- LIR soportado cubre el subconjunto acordado y lo no soportado diagnostica;
- no hay `clone`/`expect`/`unwrap` ocultos en locals;
- golden y corpus compilan con `rustc`;
- `cargo test --workspace`, clippy y fmt verdes.

## 0.1 Estado B3b (2026-11-13)

Implementado:

- LIR extendido: campos, índices, arrays/repeat, `Vec`, `Map`, `Set`, records,
  variantes, primitivas (`some`/`none`/`ok`/`err`/`print`/`format`), casts,
  `?`, referencias, rangos y chars.
- Codegen de esas expresiones y de la expresión final de una función.
- Locales: los tipos `Copy` usan `expect`; los no `Copy` usan `take`, sin
  `clone()`.
- `grimoire: Result[Unit, E]` emite `fn main() -> Result<(), E>`.
- Tests de compilación y ejecución real (record, campos, `Vec`, índice, cast,
  `?`, actualización de record, `grimoire: Result`).

Pendiente B3c:

- closures y captura;
- métodos/iteradores y `for` sobre iteradores;
- impls genéricos con despacho correcto;
- `Str` con lifetime ligado a préstamo (hoy `&'static str`);
- `Drop`/runtime `Show`/`print` (B4).

## 0.2 Estado B3c (2026-11-13) — parcial

Implementado:

- LIR `Method { receiver, name, args }` para llamadas `obj.metodo(args)`.
- LIR baja `@` (`SelfValue`) al local `self` del método.
- Codegen de métodos inherentes (`impl Tipo { fn ... }`) y llamadas a métodos.
- `Str` se emite como `&str` (elisión de lifetime) en vez de `&'static str`.
- Test de ejecución real con `punto.suma()`.

Pendiente B3d:

- closures y captura;
- métodos/iteradores y `for` sobre iteradores;
- impls genéricos con despacho correcto;
- `Drop`/runtime `Show`/`print` (B4).

## 0.3 Estado B3d (2026-11-13) — parcial

Implementado:

- Closures `LExpr::Closure` con parámetros, retorno y capturas del scope
  exterior; se emiten como `Box<dyn Fn(...) -> ...>` (permite captura).
- `LExpr::ClosureCall` para invocar closures.
- `for x in vector`/array/slice se baja a un bucle con índice `usize`, `len()` e
  indexación prestada.
- `for` sobre `Set`/`Map` materializa a `Vec` con `collect` y usa el mismo bucle; los
  elementos de `Map` son tuplas `(K, V)`.
- Tests de ejecución real: closure sin captura, closure con captura,
  `for` sobre `Vec`/array/Set/Map y adaptadores `map`/`filter`/`fold`/`collect`
  (eager, consumen el `Vec`).

Pendiente B3d:

- adaptadores/iteradores (`map`, `filter`, `fold`, …) y `for` sobre ellos;
- impls genéricos con despacho correcto;
- `Drop` y runtime `Show`/`print` (B4).
