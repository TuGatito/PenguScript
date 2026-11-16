---

<a id="sec-21"></a>
## 21. Garantías del lenguaje

### 21.1 Qué garantiza PenguScript

| Garantía | Estado | Nota |
|---|---|---|
| Sin `null` | Core | La ausencia se modela con `Option[T]`. |
| Sin lectura de memoria liberada | Core | Ownership y préstamos. |
| Sin carreras de datos en código seguro | Core | Sin hilos en el núcleo; `std.concurrent` lo hace explícito. |
| Sin recolección de basura | Core | Destrucción determinista al final del scope. |
| Sin conversiones implícitas | Core | `as`, `.parse[T]()` y `.to_string()` son explícitos. |
| Sin excepciones | Core | `Result[T, E]` y `?`. |
| Sin truthiness | Core | Las condiciones son `Bool`. |
| Sin `switch` con fallthrough | Core | `match` exhaustivo. |
| Sin macros de usuario | Core | Solo `@@derive` y `@@test`. |
| Sin despacho dinámico | Core | Sums + `match`. |
| Sin anotaciones de vida | Core | El compilador infiere y prohíbe escapes. |
| Sin `unsafe` general | Core | `curse` solo para FFI. |
| Sin estado global mutable | Core | `sigil` y `relic` son inmutables. |
| Sin imports globales | Core | `summon` explícito. |
| Sin dependencias ocultas | Core | `Tome.toml` declara todo. |
| Sin código generado editable | Core | El backend es invisible. |
| Sin `async` en el núcleo | Diferido | §22. |
| Sin hilos/atomics en el núcleo | Diferido | `std.concurrent`. |
| Sin `Rc`/`Arc` en la prelude | Std | Se importan. |
| `Box` en la prelude | Core | `Box[T]` está disponible. |
| `Vec`/`Map`/`Set` en la prelude | Core | Están disponibles por defecto. |
| Sin `CStr`/`CString` en la prelude | Std | Se importan para FFI. |
| Sin `BTreeMap`/`BTreeSet` | Std | `std.collections`. |
| Sin `VecDeque`/`LinkedList`/`BinaryHeap` | Std | `std.collections`. |
| Sin `Cell`/`RefCell`/`Mutex`/`RwLock` | Std | `std.cell`/`std.concurrent`. |
| Sin `format!`/`print!` visibles | Core | `print`/`format` son funciones del compilador. |
| Sin `assert!`/`panic!` visibles | Core | `assert`/`panic` son funciones. |
| Sin `derive` externos | Core | Solo los nueve built-in. |
| Sin tests por atributos múltiples | Core | `@@test` con opciones. |
| Sin `repr`/`layout` estable | No soportado | El backend decide. |
| Sin ABI estable de PenguScript | No soportado | Solo `foreign "C"` de entrada. |
| Sin exportación a C | No soportado | v1. |
| Sin `dyn`/`impl Trait` | No soportado | Usar `enchanting`. |
| Sin tipos asociados/GATs | No soportado | Fuera del núcleo. |
| Sin genéricos de rango superior | No soportado | Fuera del núcleo. |
| Sin `where` | No soportado | Bounds en cabecera. |
| Sin `const` genéricos | No soportado | Arrays con `N` literal. |
| Sin especialización | No soportado | Fuera del núcleo. |

### 21.2 Límites

- PenguScript no garantiza un layout de memoria estable.
- No garantiza un ABI estable entre versiones.
- No garantiza que el backend produzca el mismo código máquina entre
  versiones; sí garantiza el mismo comportamiento observable.
- La cobertura de tests no es una garantía de corrección.

### 21.3 Lo que el usuario puede asumir

1. Un programa que compila no tiene lecturas de memoria liberada, carreras de
   datos en código seguro ni `null`.
2. Los errores esperables se modelan con `Result`; los bugs con `panic`.
3. Un `match` sin `else` es exhaustivo.
4. Un binding `bind` no cambia; uno `morph` sí.
5. Un valor se mueve o se copia de forma predecible.
6. El backend no filtra tipos, atributos ni sintaxis a la superficie.

[↑ Volver al índice](#indice)
