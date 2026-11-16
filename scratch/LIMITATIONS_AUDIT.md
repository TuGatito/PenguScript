# Auditoría de limitaciones del lenguaje que bloquean la STDLIB

Fecha: 2026-11-14. Base: `7a5e856` + trabajo S0–S4 de la STDLIB sin commitear.
Método: cada limitación documentada en `docs/STDLIB.md`, `scratch/STDLIB_PLAN.md`
y en los comentarios de cabecera de `std/*.pengu` se reprodujo con una sonda real
(`scratch/tools/probe`, pipeline completo parse → HIR → tipos → LIR → codegen →
`rustc`). No se dio ninguna por buena sin evidencia.

## 0. Herramienta de verificación

`scratch/tools/probe` es una sonda de desarrollo (no forma parte del workspace ni
del compilador):

```
cargo build --manifest-path scratch/tools/probe/Cargo.toml
./scratch/tools/probe/target/debug/pengu-probe <archivo.pengu> [--emit] [--rustc] [--run] [--inject <archivo>]
```

- `--rustc` compila el Rust generado con `rustc --edition 2024`; `--run` además lo
  ejecuta.
- `--inject <archivo>` mete los items del archivo dentro del `scroll std`
  fusionado. Es la única forma de probar lo que el lenguaje solo permite dentro
  de la stdlib (`ritual` sobre primitivos, `foreign "pengu"`), porque declarar
  `scroll std` en un programa de usuario desactiva la fusión de la stdlib.

Los casos de prueba viven en `scratch/probes/limits/*.pengu` y
`scratch/probes/inject/*.pengu`; `scratch/probes/limits/run.sh` los ejecuta todos.

## 1. Veredicto por limitación

Estados: **CONFIRMADA** (el lenguaje no lo permite hoy), **YA RESUELTA** (el
trabajo S0–S4 ya la arregló y solo faltaba usarla en `std/`), **PARCIAL**
(funciona en un caso y no en otro), **DOC** (no es limitación del lenguaje sino
del documento o de la stdlib).

| # | Limitación documentada | Estado | Evidencia |
|---|---|---|---|
| 1a | `ritual` no admite funciones asociadas (`String.from`, `Char.from_u32`) | **YA RESUELTA** | `std/verbum.pengu:238` declara `new = () -> String` y compila; `Type.metodo(args)` resuelve en `pengu-types/src/check.rs:1656` (`associated_call`) |
| 1b | `ritual` no admite constantes asociadas (`Int.MAX`, `Float.EPSILON`) | **RESUELTA en A1** | Antes: `print(Int.MAX)` → `[types] error[PGS-E3001]: Int no tiene el campo MAX`. Ahora `RitualItem::Const`, `HirCrate::assoc_consts` y `LExpr::ConstRef` resuelven `Tipo.NOMBRE`; verificado con `Int.MIN/MAX/BITS`, `Float.*` y `Limits.MAX` de usuario (`crates/pengu-codegen/tests/codegen.rs`) |
| 2a | Variante unitaria ajena no nombrable en expresión (`FloatClass.NaN`) | **RESUELTA en A2** | `bind c = FloatClass.NaN` tipa como `FloatClass`; HIR resuelve `Tipo.Variante` en `expr.span`, el checker devuelve el ADT y LIR emite `LExpr::Variant` (codegen: `crate::std::floatem::FloatClass::Zero`) |
| 2b | Patrón `when Zero` fuera del módulo dueño | **RESUELTA en A2** | El parser acepta `when Tipo.Variante` (punto) y `when Variante`; HIR busca la variante calificada en el tipo visible y, sin calificar, la acepta si es única entre las sumas del crate; el chequeo de exhaustividad usa el último segmento |
| 3 | Método de primitivo `@own` que devuelve `Str` genera `-> &str` sin lifetime | **YA RESUELTA** | `ritual Float { name = (@own) -> Str "float" }` inyectado en `std` compila con `--rustc`; el codegen emite `pub fn float__name<'a>(__self: f64) -> &'a str` |
| 4 | Un literal `Str` no se convierte a `String` en el retorno | **CONFIRMADA** | `ritual Float { texto = (@own) -> String "1.0" }` → `[types] error[PGS-E7002]: tipos incompatibles: String y Str` |
| 5 | `Range[T]` no usable como tipo (`get(range)`, `replace_range`) | **RESUELTA en A6** | `Primitive::Range` en HIR, `constructor_ty` en el checker, `ast_type_ty` en LIR y `Show` para `Range`; `bind r: Range[Usize] = 0_usize..4_usize`, `s.get(0_usize..4_usize)`, `replace_range(range, …)` y `split_at` funcionan. Los límites usan el sufijo `_usize` |
| 6 | Slices `&[U8]`/`&mut [U8]` no usables | **PARCIAL en A6** | `bind v: &[Int] = &xs` sigue fallando (no hay coerción array→slice). `Str.as_bytes` devuelve `Vec[U8]` (copia) en vez de `&[U8]`, y `Char.encode_utf8` sigue diferido |
| 7 | Lambdas con cuerpo de bloque como argumento | **RESUELTA en A3** | La sintaxis real es `(x: Int) =>` (no `fun … ->`). Codegen: `LExpr::Closure` bajaba solo la última sentencia con `lower_ast_expr`, que devolvía `()` para `if`/`match`/bloques; ahora `lower_ast_block` baja binds, asignaciones, expresiones y `if` anidados. `elseif` inline permitido (`parse_elseif_inline`). Dentro de paréntesis el lexer no emite NEWLINE/INDENT, así que la forma inline es la que aplica |
| 8 | `else` en línea propia + bloque indentado no parsea | **YA RESUELTA** | `if @ < 0 then / -1 / else / 1` inyectado en `std` compila con `--rustc` |
| 9 | `Less`/`Equal`/`Greater` no resuelven como valores | **RESUELTA en A2** | `Primitive::OrderingLess/Equal/Greater` (valores), codegen `::std::cmp::Ordering::*`, patrón por igualdad en LIR y exhaustividad de `Ty::Ordering`; `bind o = Less` + `match o` imprime `menor` |
| 10 | Genéricos a nivel de método no soportados (`sort_by_key[K]`) | **CONFIRMADA** | `method_def` de la gramática (`docs/LANGUAGE.md:3161`) no admite `type_params`; solo `ritual[T]` los tiene |
| 11 | Sin auto-deref: callbacks reciben `T` por valor; `&T` no admite operadores | **CONFIRMADA (diseño)** | Los `pact` de `std/opera.pengu` declaran operadores sobre `@own`/`&` según el caso; no hay deref implícito en `pengu-types` |
| 12 | El checker no detecta uso de un valor movido | **CONFIRMADA** | `bind a = String.from("x")` / `bind b = a` / `print(a.len())` compila sin diagnóstico (debería ser error de move) |
| 13 | Iteradores/`Entry`/`drain`/`splice`/`chunks`/`windows` diferidos | **CONFIRMADA (diferido)** | No hay `Iter[T]`, `Entry[K,V]`, `Drain[T]`, `Splice[T]` en `std/` |
| 14 | `sigil` no admite llamadas a funciones | **CONFIRMADA** | `unveil sigil INF: Float = ff()` → `error[PGS-E1602]: llamada a foreign fuera de curse` + `error[PGS-E1107]: sigil requiere una expresión constante` |
| 15 | Genéricos de `rune` | **YA RESUELTA** | `rune Caja[T]` + `Caja(valor: 1)` compilan |
| 16 | `UInt` es alias documental de `U32` | **DOC** | `essence MiEntero = Int` compila; el alias de `std` es una decisión de documento, no una limitación |
| 17 | `is_punctuation`/`is_symbol`/`is_math`/`is_currency` aproximados | **DOC/CONFIRMADA** | Rust no expone la categoría general UAX #44; se quedan como rangos documentados |
| 18 | `classify` usa variantes sueltas (`Zero`) en vez de `FloatClass.Zero` | **CONFIRMADA (consecuencia de 2a/2b)** | Igual que 2a/2b |
| 19 | `docs/STDLIB.md` §32.1 marca ✅ módulos no implementados | **DOC** | `docs/STDLIB.md` afirma `via`, `exsecutor`, `tempus`, `ambitus`, `libra`, `iason`, `digestum`, `versio`, `terminus`, `globus`, `archivum`, `rete` como existentes; `std/` solo tiene 12 archivos |
| 21 | El literal `-2147483648` no cabe en `Int` (se parsea como negación de `2147483648`) | **RESUELTA en A2** | `sigil MIN: Int = -2147483648` → `[types] error[PGS-E3001]: el literal `2147483648` no cabe en `Int``; el checker pliega el signo (`negated_literals`) y valida el rango sobre el valor negativo; `Int.MIN` se escribe ya como `-2147483648` |
| 22 | El cuerpo de una lambda no se baja por LIR: lo renderiza `lower_ast_expr` desde el AST, con `_ => "()"` silencioso | **PARCIAL (N59)** | S7 añadió `none`, `some`/`ok`/`err`, `print`/`format`, `Vec[…]`/`[…]`, interpolación y records; siguen fuera `match`, `while`/`loop`, llamadas a funciones del programa y métodos genéricos. Un `match` en una lambda devuelve `()` sin diagnóstico |
| 23 | `structura` no se puede escribir sin tipos integrados nuevos | **CONFIRMADA (N60)** | `VecDeque`/`BTreeMap`/`BTreeSet`/`BinaryHeap`/`LinkedList` no existen en `Ty`; un `rune` de Pengu que los imite necesita ordenar por `K`, y `[T: Ord]` no resuelve (`PGS-E2004: no se encuentra el tipo Ord`) |
| 25 | Asignar a un local mientras dura un préstamo de una llamada (`PGS-E4108`) y préstamos de `Vec.get` que el state machine no puede mover entre estados | **CONFIRMADA (N61)** | `current = next` dentro del brazo de `match current.get(k)` da `PGS-E4108 "no se puede asignar a un valor prestado"`; `bind p = xs.get(i)` usado en otro bloque da `error[E0597]`. Se evita sacando el resultado a un `morph` y asignando después, o iterando con `for x in xs` |
| 26 | Los parámetros `&T` de `rune` no se auto-prestan en la llamada | **CONFIRMADA (N62)** | `doc.equals(other)` da `E0308 expected &Json`; hay que escribir `doc.equals(&other)`. Afecta a `equals`/`push`/`insert`/`set`/`Version.compare` |
| 24 | `[T: Ord]` con el pacto importado desborda la pila del compilador | **CONFIRMADA (N60)** | `summon std::opera::Ord` + `[T: Ord](a: T, b: T) -> Bool  a < b` → `thread 'main' has overflowed its stack / fatal runtime error: stack overflow` |
| 20 | Notas «Diferido a S5» (streams, `BufReader`, `read_to_end`, `write_all`, `copy`) | **CONFIRMADA** | `std/fluxus.pengu` solo declara `IoError`, `read_line`, `read_stdin_to_string`, `write_stdout`, `write_stderr`, `flush_stdout`, `flush_stderr` y los pactos `Reader`/`Writer` |

## 2. Investigación: cómo arreglar cada limitación sin romper lo anterior

Principio: **toda limitación se arregla en el compilador con tests de regresión y
después se usa en `std/`**. Nunca se cambia la stdlib para esquivar un hueco del
lenguaje sin antes decidir si el hueco se arregla.

### L1 — Constantes asociadas en `ritual` (limitación 1b)

Diseño: `ritual` acepta `sigil`/`relic` como item, con la forma
`sigil NAME: Tipo = expr` (misma sintaxis que a nivel de módulo).

- `pengu-syntax`: `RitualItem::Const(Const)` (`ast.rs:672`); en
  `parse_ritual` (`parser.rs:2464`) detectar `Sigil`/`Relic` y llamar a
  `parse_const`.
- `pengu-hir`: `ImplDef { consts: Vec<DefId> }` (`hir.rs`), y
  `HirCrate { assoc_consts: HashMap<String, Vec<DefId>> }` indexado por nombre
  de tipo, igual que `methods`. En `build_ritual` (`lower.rs:973`) crear el def
  con `create_aux_def` (no contamina el ámbito del módulo) y encolar
  `Pending::Const` (que ya rellena `krate.consts`).
- `pengu-types`: en `ExprKind::Field { base, name }` (`check.rs:1203`), si `base`
  es un path que resuelve a un tipo o a un primitivo y `(tipo, name)` está en
  `assoc_consts`, devolver el tipo del `ConstDef` en vez de `field_ty`.
- `pengu-lir`: en `ExprKind::Field` (`lower.rs:1119`), misma condición, emitir
  `LExpr::ConstRef(def)`.
- `pengu-codegen`: `emit_module` (`codegen.rs:150`) emite además las constantes
  asociadas de cada `ImplDef` como `const` de módulo (`crate::std::integrum::MAX`
  es una ruta válida y `def_path` ya la produce). `const_expr` acepta
  `Field(tipo, CONST)`.

Riesgo: colisión de nombres de constantes asociadas de dos tipos en el mismo
módulo (Rust no admite dos `const MAX` en el mismo `mod`). Mitigación: el nombre
Rust de la constante es `<tipo>__<NOMBRE>` cuando hay colisión, y `def_path` se
sustituye por `def_path_named`; se documenta.

### L2 — Variantes unitarias ajenas (limitaciones 2a, 2b, 9, 18)

Diseño en dos partes:

1. **Expresión** `Tipo.Variante`: en `check.rs` `ExprKind::Field`, si `base` es un
   path que resuelve a un tipo con variantes unitarias, resolver la variante como
   valor; en LIR bajar a `LExpr::Adt { variant, fields: [] }` (ya existe para
   construcciones). `Tipo.Variante(args)` para variantes con campos debe funcionar
   igual que `Variante(args)`.
2. **Patrón** `when Variante`: `bind_pattern` (`lower.rs:bind_pattern`) busca en
   el espacio de valores del módulo; si no está, y el patrón es un identificador
   suelto, probar como variante de un `enchanting` visible en el módulo (y, si el
   `summon` del tipo está en alcance, importar sus variantes al espacio de
   valores como hace Rust con `use Tipo::*`). La segunda vía arregla también
   `Ordering` (`Less`/`Equal`/`Greater`): basta con que `opera` declare el
   `enchanting` en la stdlib y el checker lo trate como cualquier suma.

Riesgo: ambigüedad entre un binding y una variante (`when x` debe seguir siendo
binding). Regla: un identificador suelto solo se interpreta como variante si no
está ya ligado en el ámbito local y existe una variante visible con ese nombre.

### L3 — Lambdas con cuerpo de bloque (limitación 7)

`fun (params) -> Tipo` seguido de `NEWLINE INDENT block DEDENT` debe parsear
como lambda con cuerpo de bloque. Hoy `parse_lambda` exige una expresión en la
misma línea. Cambio local en `pengu-syntax` + `ast::Lambda { body: Block }` (ya
es un bloque). Riesgo bajo.

### L4 — Coerción `Str` → `String` (limitación 4)

Diseño: coerción implícita **solo en posiciones donde el tipo esperado ya se
conoce**: retorno de función/método, argumento de llamada, campo inicializado y
`bind` con anotación. En `pengu-types`, al unificar `String` con `Str`, aceptar y
registrar la coerción en `Body` (span → `Coercion::StrToString`); en
`pengu-codegen`, al emitir la expresión en esa posición, envolver en
`.to_string()`. No se permite la coerción inversa ni en operadores.

Riesgo: `Str` es un préstamo y `String` es dueño; la coerción copia, así que no
rompe ownership. Es la misma solución que Rust aplica con `.to_string()`
explícito, pero ergonómica.

### L5 — Slices (limitación 6)

Tres piezas:
1. Coerción de `&[T; N]` a `&[T]` y de `&mut [T; N]` a `&mut [T]` en
   `pengu-types::unify` (regla de subtipado de arrays a slices).
2. `Ty::Slice(T)` en el checker y en `ty_rust` → `[T]`, `&[T]`, `&mut [T]`.
3. Indexación y `len()` sobre slices en LIR/codegen (`[i]`, `.len()`), y
   préstamos `&xs` / `&mut xs` sin doble referencia (hoy `&xs` produce `&&[T;N]`).

Riesgo: toca unify y codegen; se implementa con tests dedicados antes de tocar
la stdlib.

### L6 — `Range[Usize]` en la superficie (limitación 5)

Con `Ty::Range` ya existente para `0..2`, añadir a `std/verbum.pengu`:
`get(range: Range[Usize]) -> Str`, `replace_range(range, with)`, `as_bytes()` y
`split_at`. No requiere cambios de compilador si L5 y L6 están hechos; el
`get(range)` baja a `&s[a..b]`.

### L7 — Genéricos de método (limitación 10)

Añadir `type_params` a `method_def` en la gramática y al AST; el checker ya sabe
monomorfizar llamadas genéricas de función (`call_generic`), así que el trabajo
es propagar los parámetros del método a su `Signature` y a la llamada
`xs.sort_by_key[K](f)`. Se pospone a después de S5: bloquea `sort_by_key` pero no
la stdlib de sistema.

### L8 — Move checking (limitación 12)

`pengu-check/src/ownership.rs` ya recorre los cuerpos; falta marcar los usos
posteriores a un move de un valor no-`Copy`. Se implementa con un mapa
`LocalId → moved_at` y error `PGS-E4001` en el uso. Riesgo de falsos positivos en
bucles; se cubre con tests.

### L9 — `sigil` con llamadas (limitación 14)

Permitir en el valor de un `sigil` una llamada a función si todos los argumentos
son constantes y la función es `foreign` con ABI `"pengu"` o una función pura
marcada. Se implementa con evaluación constante en el checker. Mientras tanto,
las constantes de `std` se escriben con literales (como ya hace `numerus`).

## 3. Plan por fases

Cada fase: implementación + tests + `cargo test --workspace` verde + commit a
`main`. El orden maximiza lo que desbloquea por unidad de riesgo.

| Fase | Contenido | Desbloquea en `std/` |
|---|---|---|
| **A0** ✅ | Auditoría (este documento) + plan | — |
| **A1** ✅ | Constantes asociadas (`sigil`/`relic` en `ritual`) y funciones asociadas usadas en `std` | `Int.MIN/MAX/BITS`, `Int.from_str(_radix)`, `Float.EPSILON/MIN/MAX/MIN_POSITIVE/NAN/INFINITY`, `Float.from_str/from_bits`, `Char.from_u32/from_digit` |
| **A2** ✅ | Variantes unitarias calificadas en expresión y patrón; `Ordering` como suma; plegado del signo en literales | `FloatClass.NaN`, `classify` sin variantes sueltas, comparadores manuales (`Less`/`Equal`/`Greater`) |
| **A3** ✅ | Lambdas con cuerpo de bloque y `elseif` inline | `capsa`/`tabula` con callbacks multilínea y comparadores `Less`/`Equal`/`Greater` |
| **A6** ✅ | Tipo `Range[T]`, `get`/`split_at`/`replace_range` con rangos y desestructuración de bind desde expresión | `verbum` con APIs de rango |
| **A4** | Coerción `Str` → `String` | métodos que devuelven `String` sin intrínseco |
| **A5** | Slices `&[T]`/`&mut [T]` + coerción array→slice | `Char.encode_utf8`, `String.from_utf8`, `as_bytes`, `Reader`/`Writer` |
| **A7** | Move checking | soundness; permite escribir `std` con confianza |
| **S5** ✅ | `via` (FS), `exsecutor` (procesos), `ambitus` (entorno), `tempus` (tiempo) y `optio` (métodos de `Option`/`Result`) usando A1–A6 | Gate B: `std::env` (bloqueo 3798) |
| **S6** 🚧 | `nexus`: `CString` seguro (sin punteros ni `unsafe`; ver N38) | — |
| **S7** 🚧 | `funis`: adaptadores de `Iterator` (✅ `map/filter/fold/collect/count/any/all/find/position/take/skip/step_by/rev/enumerate/zip/nth/last/sum/min/max`); `structura` pendiente | — |
| **S8** 🚧 | `iason` (JSON) ✅, `digestum` (SHA-256/SHA-1/CRC-32/FNV-1a) ✅, `versio` (SemVer 2.0.0) ✅; `libra` (TOML) pendiente (N42) | auto-hospedaje H3 |
| **S9** 🚧 | `terminus` ✅, `globus` ✅, `cellula` ✅; `archivum` (tar/zip), `vinculum` (refcount), `frenum` (sync) pendientes: sin hilos ni tipos opacos | CLI auto-hospedado |
| **S10** 🚧 | `rete` TCP ✅ (`TcpListener`/`TcpStream` bloqueantes); TLS y HTTP pendientes (S10b) | — |
| **S9b/S10b** | `archivum` (tar sin compresión → zip), `vinculum`, `frenum`, TLS/HTTP, `structura` y `rune Iter[T]` | — |

Después de cada fase A, se actualizan los módulos de `std/` que la limitación
bloqueaba, se actualiza `docs/STDLIB.md` (quitando la nota de «diferido») y se
commitea todo junto.

### 3.1 Arreglos de plataforma descubiertos durante S5

Estos no estaban en la auditoría inicial porque solo aparecen al escribir módulos
de `std` que se usan entre sí y que exponen tipos propios:

| # | Limitación | Estado |
|---|---|---|
| 22 | Los métodos de un `impl` se emitían `fn` (privados): inutilizables desde otro módulo | **RESUELTA** (S5a): `pub fn` en impls inherentes; en impls de pacto sin `pub` (`error[E0449]`) |
| 23 | Las funciones asociadas de un `rune` se llamaban como `modulo::fn` pero se emitían en su `impl` (`Tipo::fn`) | **RESUELTA** (S5a): `inherent_impl_target` en codegen |
| 24 | `ast_type_ty` (LIR) resolvía los nombres de tipo por nombre global: `-> E` en un módulo hermano apuntaba al `E` de otro módulo | **RESUELTA** (S5): `lookup_crate_type(krate, module, name)` con el módulo de la firma |
| 25 | Las variantes integradas `some`/`ok`/`err` no funcionaban como patrón (`if false` + `unreachable!()`) | **RESUELTA** (S5): `BuiltinVariant`/`IsBuiltin`/`BuiltinField` en LIR y codegen |
| 26 | El payload de un patrón se extraía en el bloque de prueba, así que `unreachable!()` saltaba en las demás ramas | **RESUELTA** (S5): el binding se emite dentro del bloque de la rama |
| 27 | Los `rune` no implementaban `Show`: `print(mi_rune)` era `E0277` | **RESUELTA** (S5): `Clone` derivado cuando es posible + `unveil ritual X for Show` en la std |
| 28 | `ty_rust_state` emitía el nombre pelado de un `Ty::Adt` (los enums de estado de una función dentro de otro módulo no compilaban) | **RESUELTA** (S5): `def_path` |
| 29 | `__pengu_show` se emitía sin cualificar (`cannot find function` dentro de módulos) | **RESUELTA** (S5): `crate::__pengu_show` |
| 30 | `String.from("texto #{expr}")` no compila: la interpolación produce `String` y el parámetro es `&Str` | **ABIERTA** (la cierra A4); usar `format("… #{expr}")` |
| 31 | `print` de un `rune` sin `Show` propio; el mensaje `PGS-W1102` de sombreado saltaba entre ramas de `match` distintas | **RESUELTA** (S5): aviso solo si el binding es visible en el ámbito |
| 32 | `for value in vector` sobre `Vec[String]` generaba `let x = v[i];` (`E0507`: no se puede mover de un índice) | **RESUELTA** (S5): `is_copy_ty` y `v[i].clone()` cuando el elemento no es `Copy` |
| 33 | Las llamadas asociadas con el tipo cualificado por módulo (`tempus::Duration.from_millis`, `exsecutor::Command.new`) daban `path no soportado en LIR` | **RESUELTA** (S5): la detección usa `path.last()` en vez de exigir un único segmento |
| 34 | Los métodos con cuerpo sobre tipos integrados (`Option[T]`, `Result[T, E]`) no se emiten: `emit_impl` los descarta y Rust no admite `impl<T> Option<T>` (`E0116`) | **ABIERTA** (S7): requiere un trait de extensión en el prelude. Mientras tanto `std/optio.pengu` solo declara métodos homónimos de Rust (paso directo T3): `is_some`, `is_none`, `unwrap_or`, `unwrap_or_default`, `take`, `replace`, `is_ok`, `is_err` |
| 36 | `Iter[T]` no es un tipo con nombre: no se puede escribir `rune Iter[T]` ni declarar sus métodos en `std/`. La superficie vive en `method_signature` (`crates/pengu-types/src/check.rs`) y en `VecAdapterKind` (`crates/pengu-lir/src/lir.rs`) | **PARCIAL** (S7): 20 métodos implementados; el resto (`filter_map`, `chain`, `reduce`, …) espera al `rune Iter[T]` |
| 37 | `Vec` declaraba `sum`/`min`/`max`/`product` como paso directo, pero Rust no tiene esos métodos en `Vec` (`Ord::min` es binario) | **RESUELTA** (S7): se retiraron de `std/capsa.pengu`; se usan sobre `iter()` |
| 38 | `CString`/`CStr` son **tipos primitivos** del compilador (`Ty::CString`/`Ty::CStr`), no se pueden redeclarar como `rune` en `std/` (el nombre resuelve al primitivo y falla el acceso a campos). Además no hay `Ptr[T]` utilizable, así que la FFI real con C queda fuera de v1 | **PARCIAL** (S6): `std/nexus.pengu` expone funciones libres sobre el `CString` integrado; `from_raw`/`as_ptr`/`curse` con punteros quedan para v2 |
| 39 | Los `rune` **mutuamente recursivos** no se pueden declarar (`Entry` con campo `Json` y `Json` con `Vec[Entry]`): el tipo referenciado aún no está en el ámbito al resolver los campos del primero. La autorrecursión sí funciona (`Json` con `Vec[Json]`) | **RESUELTA** (S8): `std/iason.pengu` modela el objeto como `items` + `keys` en paralelo, sin tipos mutuos |
| 40 | El chequeo de `Clone` de un ADT (`adt_clone_ok`/`type_clone_ok`) recursaba sin límite en tipos recursivos y desbordaba la pila del compilador | **RESUELTA** (S8): `type_clone_ok_at`/`adt_clone_ok_at` con profundidad máxima 8 |
| 41 | `x == none` se emitía como `x == None`, que exige `PartialEq` en el payload | **RESUELTA** (S8): el codegen emite `x.is_none()` / `x.is_some()` |
| 42 | Los métodos de módulos de `std` no pueden importarse entre sí, así que `libra` (TOML) no puede reutilizar el árbol de `iason` | **RESUELTA** (S8b): `libra` aplana el documento (`clave.punteada -> texto` + tipo) en vez de compartir el árbol |
| 48 | Un `match` **dentro de la rama de otro `match`** usado como expresión inicializaba el slot del resultado con `unreachable!()` y saltaba en cuanto se construía el estado inicial (`internal error: entered unreachable code`) | **RESUELTA** (S11): los locales indefinidos del bloque de entrada cuyo tipo admite `Default` arrancan en `Default::default()` (`ty_has_default` en `crates/pengu-codegen/src/codegen.rs`); el resto conserva `unreachable!()` |
| 43 | Un `sigil`/`const` de tipo `Str` emitía el valor con comillas dobles escapadas (`"\"\u{1b}[0m\""`) porque `const_expr` volvía a escapar el segmento ya literal | **RESUELTA** (S9): `const_expr` emite el segmento tal cual |
| 44 | Las constantes de módulo se declaran con `unveil sigil NOMBRE: Tipo = valor`; `unveil NOMBRE = valor` no es una constante y falla al parsear | **DOCUMENTADA**: usar `sigil`/`relic` (ver `docs/LANGUAGE.md` §19) |
| 45 | `format("... \u{1b} ... #{x}")` con escapes ANSI y una interpolación mixta emitía el escape literal | **EVITADA** (S9): en `std/terminus.pengu` el color RGB se construye en el runtime (`terminus_rgb`). Queda abierta como N45 |
| 46 | `std/cellula.pengu` no puede ser genérica (`Cell[T]`) porque no hay tipos opacos ni hilos; guarda `String` por clave | **DOCUMENTADA** (S9): la API serializa a texto |
| 47 | `bind` es palabra clave del lenguaje, así que no puede ser el nombre de un método (`TcpListener.bind` no parsea: «se esperaba un nombre de campo») | **RESUELTA** (S10): el constructor de `rete` es `TcpListener.listen`; conviene revisar otros nombres del diseño (`match`, `when`, `else`) al escribir módulos nuevos |
| 35 | Ciertos nombres de método chocan con la gramática: `or`/`and`/`xor` son palabras clave y `ok`/`err` se leen como constructores (`[parse] E1901: se esperaba un nombre de campo`) | **ABIERTA**: el parser no distingue `.nombre` de un constructor. Mitigación: evitar esos nombres en la std (se usaron `or_with`/`and_with`/`xor_with`/`as_option`/`as_error` en el diseño descartado) |

### 3.1 Limitaciones nuevas encontradas al cerrar Gate B (2026-11-14)

| # | Limitación | Estado |
|---|---|---|
| 49 | `CStr` **no se puede usar por valor**: `ty_rust` lo emite como `::std::ffi::CStr`, que es *unsized* (`[i8]`). `Option[CStr]`, un local `CStr` o un `sigil` de tipo `CStr` dan `E0277: the size for values of type [i8] cannot be known`. Solo funciona detrás de una referencia (`&CStr`), y el checker no lo exige | **CERRADA (S6)**: `Ty::CStr` se emite como `&::std::ffi::CStr`, `&CStr` se normaliza a `CStr` y `ast_type` no duplica la referencia |
| 50 | La interpolación produce `String` y un parámetro `&Str` no la acepta (`E3001 String y Str`); es la A4 pendiente (`String.from("… #{x}")`, `format` con `Str`) | **ABIERTA** (A4). Sigue bloqueando los ejemplos 321 y 499 del corpus |
| 51 | La tabla §32.1 de `docs/STDLIB.md` mapea un alias a **varios** módulos (`std.collections` → `capsa` + `tabula` + `fasciculus` + `structura`). El compilador solo admite alias 1:1, así que `summon std::collections` sigue sin existir | **DOCUMENTADA**: usar los nombres latinos o los alias individuales (`std::map`/`std::set` no están en la tabla; conviene añadirlos) |
| 52 | `bind ok = f()` falla con `PGS-E1105 "el patrón es refutable; añade \`else\`"`: el nombre `ok` se lee como constructor de `Result`. El mensaje no sugiere la causa real | **DOCUMENTADA**: evitar `ok`/`err`/`some`/`none` como nombres de binding (o mejorar el diagnóstico) |
| 53 | `CString.new` ya tiene codegen (`LExpr::CStringNew`), pero el tipo del error es `Ty::Error`, así que se emite `Result<CString, ()>`: un `match` sobre el payload del error no tipa | **ABIERTA**: modelar `NulError` como `rune` de `std.ffi` si se quiere exponer el error |
| 54 | El `else` de un `bind` cuenta como manejo de `NulError` (arregla el ejemplo §16.5), pero `?` y `else` son las dos únicas formas aceptadas; no hay otra | **DOCUMENTADA** |

| 55 | Una vista `CStr` (p. ej. `ffi.cstring_as_c_str(&owned)`) **no puede guardarse en un `bind`** y usarse en sentencias posteriores: el state machine mueve la `CString` dueña al bloque siguiente y el préstamo no sobrevive (`error[E0597]: borrowed value does not live long enough`). | **DOCUMENTADA**: usar la vista como temporal en la misma expresión/bloque `curse`, o copiar con `cstring_to_str`/`cstring_to_string_lossy`/`cstr_to_cstring` |
| 56 | Llamar a una función `curse` fuera de un bloque `curse` estaba permitido (contra `LANGUAGE.md` §16.2). | **CERRADA (S6)**: `PGS-E1602` "llamada a una función `curse` fuera de un bloque `curse`", y cuenta como uso de la frontera FFI |
| 58 | La conversión `Str` → `String` de A4 no cubre **campos de record**: `Config(name: "pengu")` con `name: String` da `E3001 tipos incompatibles: String y Str`. | **ABIERTA (N58)**: extender la coerción a la construcción de `rune` (bloquea el ejemplo §3.6 del corpus, línea 504) |
| 57 | Un `match` cuyo último brazo deja un fallthrough al `join` obligaba a inicializar con `unreachable!()` locales definidos solo en algunos brazos cuando el tipo no tiene `Default` (panic al arrancar). | **CERRADA (S6)**: el fallthrough tras el último brazo se marca `LTerm::Unreachable` (el checker ya exige exhaustividad) |

Además se cerraron en esta sesión: llamadas cualificadas por módulo (`env.args()`, 
`fs.read_to_string()`), alias `std::ffi`/`std::env`/`std::fs`…, importación de tipos
integrados a través de `std` (`summon std::ffi::CString`), `CString.new` en codegen,
`curse` en LIR (cuerpo emitido dentro de `unsafe`) y la coerción `&CString` → `&CStr`.

## 4. Criterios de aceptación

- `cargo test --workspace` verde en cada commit.
- Cada fase A añade tests unitarios en el crate afectado **y** un caso en
  `crates/pengu-codegen/tests/codegen.rs` que compila y ejecuta el Rust generado.
- `std/` no contiene comentarios `-- Diferido` que ya no apliquen.
- `docs/STDLIB.md` y `std/` coinciden módulo a módulo (tabla §32.1 revisada).

### N60–N61: límites de la conversión `Str` ↔ `String` (T5)

| # | Limitación | Estado |
|---|---|---|
| N60 | No hay `String` → `Str` para temporales: `toma_str(String.from("x"))` da error porque prestar el resultado de una llamada produciría `E0716`. Solo se convierte cuando el valor es un *place* (local, campo o índice). | Documentada (por diseño) |
| N61 | Las ramas de un `if`/`match` no se convierten entre sí: una rama `String` y otra `Str` siguen sin unificar. Se resuelve con `String.from` en la rama `Str`, o anotando el binding como `String`. | Documentada |

## 5. Tanda C: funis, structura, libra, iason, digestum y versio (2026-11-15)

Auditoría completa y plan en `scratch/AUDIT_FUNIS_STRUCTURA.md`.

| # | Limitación | Estado |
|---|---|---|
| N58 | La coerción `Str` → `String` no llegaba a los campos de record (`Json(kind: "null", …)`). | ✅ C1 (`record_ty` coacciona antes de unificar) |
| N60 | `[T: Ord]` desbordaba la pila del compilador: `implements()` se llamaba a sí misma en el brazo `Ord`. | ✅ C1 (`implements_equality`) |
| N62 | Las funciones asociadas de un `ritual` genérico se emitían por instancia y quedaban ambiguas (`E0034`) porque la plantilla `impl<T>` choca con el `enum __State`. | ✅ C1: se omiten y el LIR da `PGS-E1305`; la superficie genérica usa funciones libres |
| N63 | Devolver `Str` prestado desde una función genérica (`-> Str` con `T` de por medio) da `E0106`. | Documentada |
| N66 | Una llamada cualificada por módulo (`std::structura::pila_push`) no instanciaba los genéricos: `Vec[Generic]` frente a `Vec[Int]`. | ✅ C1 (`callee_is_item` acepta rutas resueltas a función) |
| N67 | Contenedores ordenados genéricos: `==` exige `Eq`, no se puede pasar un `T` por valor dos veces sin moverlo y `Vec[i]` exige `Copy`. | Diferida; `structura` ofrece pila/cola/cola doble |
| N68 | `[K: Ord, V]` parsea `Eq` tras la coma como otro parámetro (`PGS-E1301`). | Documentada |
| N69 | El checker de ownership da `PGS-E4102` (préstamo inmutable y mutable simultáneos) cuando la condición de un `if` presta el receptor (`if out.is_empty() then … out.remove(0)`) y una rama lo muta. El préstamo de la condición sigue vivo en las ramas. | ✅ evitado en `structura`: se guarda la condición en un `bind` (`bind vacia = out.is_empty()`) antes de ramificar |

También queda anotado que N59 (cuerpos de lambda renderizados desde el AST con
`_ => "()"`) sigue abierta: el renderizador cubre `if`, `call`, vectores, tuplas,
campos e índices, pero no `match` ni `while`.
| N70 | `terminus.read_key` no pone el terminal en modo crudo: sin `termios` la entrada llega por líneas, así que devuelve el primer carácter tras pulsar Intro. | Documentada; modo crudo requeriría `libc`/`ioctl` (fuera de v1 por N38) |
| N71 | Una expresión de bloque en `bind` (`bind area =` + bloque indentado, o `bind value = do … end`) no baja a LIR: `PGS-E1901 expresión no soportada en LIR B1`. | Documentada; los bloques del doc 984 y 1034 quedan declarados no ejecutables |
| N72 | `ritual[T]` sobre un `rune` genérico no resuelve el tipo del campo del receptor: `@.value` se tipa `<error>` y da `` `<error>` no tiene el campo `value` ``. | Documentada; bloques 1998 y 2193 declarados no ejecutables |
| N73 | Un literal `Str` en el constructor de una variante genérica no acepta la coerción `Str`→`String`: `bind r: Result[Int, String] = err("no")` falla con `Result[Int, String]` frente a `Result[_, Str]`. | Documentada; funciona `err(String.from("no"))` |
