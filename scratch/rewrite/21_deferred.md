---

<a id="sec-22"></a>
## 22. Diferido y no soportado

Esta sección **no es normativa para el código de usuario**. Lista lo que queda
fuera del núcleo y su alternativa.

### 22.1 Fuera del núcleo

| Área | Estado | Alternativa |
|---|---|---|
| Anotaciones de vida (`'a`, `'static`) | No soportado | Referencias solo en parámetros/locales; el compilador infiere. |
| `for<'a>` / rango superior | No soportado | Usar funciones concretas o sums. |
| `where` | No soportado | Bounds en la cabecera `[T: Pact]`. |
| Tipos asociados | No soportado | Usar un parámetro de tipo o un `enchanting`. |
| GATs | No soportado | Usar `Vec`/`String` owned. |
| `dyn` / objetos de trait | No soportado | `enchanting` + `match`. |
| `impl Trait` | No soportado | Tipo concreto, `Box[T]` o `enchanting`. |
| `async` / `await` | Diferido | `std.async` con runtime externo. |
| Hilos, canales, atomics | Diferido | `std.concurrent`. |
| `Rc` / `Arc` en la prelude | Std | `summon std::rc::Rc` / `std::sync::Arc`. |
| `Cell` / `RefCell` | Std | `std.cell`, explícito. |
| `Mutex` / `RwLock` | Std | `std.concurrent`, explícito. |
| `Box` en la prelude | Core | Disponible. |
| `Pin` / `Future` | Diferido | `std.async`. |
| `unsafe` general | No soportado | `curse` solo para FFI. |
| Punteros crudos | No soportado | Sin acceso directo a memoria. |
| `transmute` / uniones / asm | No soportado | Reestructurar el código. |
| Macros de usuario | No soportado | Funciones y `std.meta` no existe en v1. |
| Atributos generales | No soportado | Solo `@@derive` y `@@test`. |
| `repr` / layout estable | No soportado | El backend decide. |
| Build scripts | Diferido | `std.build` o un crate externo. |
| `I128` / `U128` | Std | `std.int`. |
| `BTreeMap` / `BTreeSet` | Std | `std.collections`. |
| `VecDeque` / `LinkedList` / `BinaryHeap` | Std | `std.collections`. |
| `Cow` | Std | `std.borrow`. |
| `Weak` | Std | `std.rc`/`std.sync`. |
| `Index` / `IndexMut` sobrecargables | No soportado | Método `.at(i)` o `get`. |
| `Deref` / `DerefMut` | No soportado | Acceso explícito a campos. |
| `From` / `Into` implícitos | No soportado | `.to_string()`, `.parse[T]()`, `as`. |
| `Display` / `Debug` sobrecargables | No soportado | `Show` y `@@derive(Debug)`. |
| `Drop` visible | No soportado | Destrucción automática. |
| Exportar funciones a C | No soportado | v1. |
| Variádicas C | No soportado | Funciones C concretas. |
| Bench/fuzz/property testing | Std | Herramientas externas. |
| `cfg` / `test` / `inline` / `must_use` | No soportado | El backend decide. |

### 22.2 Por qué

El criterio es siempre el mismo: si una feature no da potencia para el 95% del
código, no entra. Las que sí entran se simplifican hasta caber en una línea.

### 22.3 Lo que se puede importar

La librería estándar es chica:

`std.io`, `std.fs`, `std.process`, `std.env`, `std.time`, `std.math`,
`std.string`, `std.collections`, `std.ffi`, `std.rc`, `std.sync`,
`std.cell`, `std.async`, `std.test`, `std.ops`.

Todo lo demás es un crate externo.

[↑ Volver al índice](#indice)
