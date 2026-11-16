---

<a id="sec-27"></a>
## 27. Apéndice Z: qué se eliminó y por qué

Este apéndice es histórico y no normativo. Explica las features que la spec
`1.0.0-rc.1` tenía y que `0.5.0` deja fuera.

| Feature eliminada | Por qué |
|---|---|
| Anotaciones `'a`, `'static` | El usuario no debe aprender vidas; el compilador infiere y prohíbe escapes. |
| `for<'a>` / rango superior | No da potencia para el 95% del código; fuera del núcleo. |
| `where` | Los bounds caben en la cabecera `[T: Pact]`. |
| Tipos asociados | Duplican los parámetros de tipo y complican los pacts. |
| GATs | Superficie enorme para casos raros. |
| `dyn` / objetos de trait | Un `enchanting` + `match` es más explícito. |
| `impl Trait` | El tipo de retorno debe ser visible. |
| `Pin` / `Future` | Async no es del núcleo. |
| `async` / `await` | Diferido a `std.async`; el núcleo es síncrono. |
| `dream` / `awaken` | Nombres de la etapa async, eliminada. |
| Hilos / canales / atomics | `std.concurrent`, no el lenguaje. |
| `Send` / `Sync` visibles | Detalle del backend; el usuario no los escribe. |
| `Rc` / `Arc` en la prelude | Compartir debe ser explícito; van a `std`. |
| `Cell` / `RefCell` / `Mutex` / `RwLock` | Mutabilidad interior fuera del núcleo. |
| `Cow` / `Weak` | Casos avanzados; `std`. |
| Punteros crudos | Sin acceso directo a memoria en código seguro. |
| `transmute` / uniones / asm | Sin `unsafe` general; `curse` solo para FFI. |
| `MaybeUninit` / `ManuallyDrop` / `UnsafeCell` | Detalles que el usuario no debe tocar. |
| `PhantomData` / ZST / DST | Detalles de representación; el backend decide. |
| `repr` / layout estable | No se garantiza; no es parte del contrato. |
| `cfg` / `inline` / `must_use` | Atributos del backend, no del usuario. |
| Macros (`macro_rules!`, `incantation`) | Superficie enorme; no hay metaprogramación. |
| Atributos generales | Solo `@@derive` y `@@test`. |
| `rust` block | El backend es invisible; no hay escape de código. |
| Exportar funciones a C | v1 solo importa FFI; exportar exige ABI estable. |
| Build scripts | El 99% no los necesita; diferidos a `std.build`. |
| `I128` / `U128` | Rango raro; `std.int`. |
| `BTreeMap` / `BTreeSet` | `std.collections`. |
| `VecDeque` / `LinkedList` / `BinaryHeap` | `std.collections`. |
| `Index` / `IndexMut` sobrecargables | Requieren tipo asociado; se usa `.at(i)`/`get`. |
| `Deref` / `DerefMut` | Coerción automática; se accede de forma explícita. |
| `From` / `Into` | Conversiones implícitas; se usan métodos explícitos. |
| `Display` / `Debug` sobrecargables | Solo `Show` para imprimir. |
| `Drop` visible | La destrucción es automática. |
| `spell` | La función se declara con `->`. |
| `spirit` | El receptor es `@`. |
| `class` / `new` / `this` | No hay clases; records y métodos. |
| `null` / `nil` | `Option[T]` y `none`. |
| `try` / `catch` / `throw` | `Result[T, E]` y `?`. |
| `switch` con fallthrough | `match` exhaustivo. |
| Bench / fuzz / property testing | Herramientas externas; no el núcleo. |

### 27.1 Regla de eliminación

Una feature se elimina si:

1. no resuelve el 95% de los casos;
2. se puede reemplazar por un concepto del núcleo;
3. su costo de superficie supera su potencia.

Si una feature eliminada vuelve, vuelve en una versión mayor y con una ADR
nueva.

[↑ Volver al índice](#indice)
