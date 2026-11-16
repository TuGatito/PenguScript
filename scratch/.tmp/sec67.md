<a id="sec-67-glosario"></a>
## 67. Glosario

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 10 |
| Rust | — |
| Palabras mágicas | todas |
| Depende de | §1–§66 |
| Ejemplos ejecutables | `no` |

Definiciones breves y no circulares. “Rust” marca un término que también
existe en Rust; “Pengu” marca una palabra propia del lenguaje.

### 67.1 Términos mágicos

| Término | Origen | Definición |
|---|---|---|
| `rune` | Pengu | Declara un struct: un tipo producto con campos nombrados, posicionales o ninguno. |
| `enchanting` | Pengu | Declara un enum: un tipo suma con variantes. |
| `pact` | Pengu | Declara un trait: un contrato de métodos, tipos y constantes. |
| `ritual` | Pengu | Implementa un trait para un tipo o añade métodos inherentes. |
| `essence` | Pengu | Declara un alias de tipo o un tipo asociado. |
| `scroll` | Pengu | Declara un módulo, en archivo o inline. |
| `summon` | Pengu | Importa nombres de otro módulo o crate. |
| `unveil` | Pengu | Hace visible un item; su forma con paréntesis ajusta el ámbito. |
| `sigil` | Pengu | Declara una constante evaluada en compilación. |
| `relic` | Pengu | Declara un static inmutable de módulo. |
| `grimoire` | Pengu | Punto de entrada del programa; genera `main`. |
| `incantation` | Pengu | Declara una macro de tokens; genera `macro_rules!`. |
| `chimera` | Pengu | Declara una unión; requiere `curse` para leer/escribir. |
| `curse` | Pengu | Marca código unsafe: función, bloque o trait. |
| `dream` | Pengu | Marca una función, bloque o lambda asíncrona. |
| `awaken` | Pengu | Espera un `Future`; genera `.await`. |
| `eternal` | Pengu | Marca una función `const`. |
| `foreign` | Pengu | Declara una interfaz externa (FFI). |
| `morph` | Pengu | Declara un binding mutable. |
| `bind` | Pengu | Declara un binding inmutable. |
| `@` | Pengu | Receptor `&self`; también binding en patrones. |
| `@mut` | Pengu | Receptor `&mut self`. |
| `@own` | Pengu | Receptor `self` por valor. |
| `@@` | Pengu | Atributo externo sobre el item siguiente. |
| `@@!` | Pengu | Atributo interno al inicio de un módulo/crate. |
| `?T` | Pengu | Azúcar para `Option<T>`. |
| `!T` | Pengu | Azúcar para `Result<T, Error>`. |
| `do` | Pengu | Introduce un bloque expresión. |
| `by` | Pengu | Paso de un `for`; genera `step_by`. |
| `when` | Pengu | Brazo de `match`. |
| `is`/`isnt` | Pengu | Igualdad/desigualdad; `==`/`!=`. |

### 67.2 Tipos y memoria

| Término | Origen | Definición |
|---|---|---|
| binding | Rust | Nombre que liga un valor a un tipo; `bind`/`morph`. |
| ownership | Rust | Regla por la que cada valor tiene un único dueño responsable de liberarlo. |
| move | Rust | Transferencia de ownership; el origen deja de ser usable. |
| borrow | Rust | Referencia temporal a un valor sin transferir ownership. |
| lifetime | Rust | Región del programa durante la que una referencia es válida. |
| NLL | Rust | Análisis de préstamos no léxico; el borrow termina en su último uso. |
| drop scope | Rust | Punto donde se liberan automáticamente los valores. |
| `Copy` | Rust | Tipo que se copia bit a bit en lugar de moverse. |
| `Clone` | Rust | Tipo que puede duplicarse explícitamente. |
| `Drop` | Rust | Trait que ejecuta limpieza al final del scope. |
| `Sized` | Rust | Tipo con tamaño conocido en compilación. |
| DST | Rust | Tipo de tamaño dinámico, como `[T]` o `dyn Trait`. |
| ZST | Rust | Tipo de tamaño cero, como un unit struct. |
| variance | Rust | Cómo cambia un tipo genérico al cambiar sus lifetimes. |
| provenance | Rust | Origen de un puntero que justifica su uso válido. |
| aliasing | Rust | Dos referencias al mismo dato; `&mut` exige exclusividad. |

### 67.3 Tipos, traits y genéricos

| Término | Origen | Definición |
|---|---|---|
| nominal | Rust | Sistema donde un tipo se identifica por su nombre/declaración. |
| genérico | Rust | Declaración parametrizada por tipos, lifetimes o constantes. |
| bound | Rust | Restricción que un parámetro genérico debe cumplir. |
| `where` | Rust | Cláusula que agrupa bounds. |
| HRTB | Rust | Bound `for<'a>` que cuantifica sobre cualquier lifetime. |
| trait object | Rust | Valor `dyn Trait` con dispatch dinámico. |
| object safety | Rust | Reglas que permiten usar un trait como `dyn Trait`. |
| GAT | Rust | Associated type genérico por lifetime/tipo. |
| RPITIT | Rust | `impl Trait` en posición de retorno de un trait. |
| coherence | Rust | Reglas que evitan implementaciones ambiguas. |
| orphan rule | Rust | Solo se implementa un trait externo si el tipo es local. |
| monomorphization | Rust | Generación de una versión por combinación de tipos. |
| dyn | Rust | Prefijo de trait object de dispatch dinámico. |
| impl Trait | Rust | Tipo opaco que implementa un trait. |
| associated type | Rust | Tipo declarado dentro de un trait y fijado por la impl. |
| const generic | Rust | Parámetro genérico que es una constante. |

### 67.4 Errores y control

| Término | Origen | Definición |
|---|---|---|
| `Option` | Rust | Tipo que representa presencia (`Some`) o ausencia (`None`). |
| `Result` | Rust | Tipo que representa éxito (`Ok`) o error (`Err`). |
| `?` | Rust | Operador que propaga `None`/`Err` temprano. |
| divergente | Rust | Expresión de tipo `Never` que no retorna normalmente. |
| `Never` | Rust | Tipo sin valores; `return`, `break`, `continue`, `panic`. |
| `Unit` | Rust | Tipo `()` con un solo valor. |
| exhaustivo | Rust | `match` que cubre todos los casos posibles. |
| refutable | Rust | Patrón que puede fallar; requiere `if let`/`while let`. |
| irrefutable | Rust | Patrón que siempre coincide; válido en `bind`. |
| guard | Rust | Condición extra en un brazo de `match`. |
| let-else | Rust | Binding con una rama `else` que debe divergir. |
| panic | Rust | Aborta la ejecución por un bug irrecuperable. |
| unwinding | Rust | Desenrollado de pila al hacer panic. |
| abort | Rust | Terminación inmediata sin unwinding. |

### 67.5 Colecciones, iteradores y concurrencia

| Término | Origen | Definición |
|---|---|---|
| array | Rust | Secuencia fija `[T; N]` en la pila. |
| slice | Rust | Vista `&[T]`/`&mut [T]` sobre una secuencia contigua. |
| `Vec` | Rust | Secuencia dinámica en el heap. |
| `VecDeque` | Rust | Cola doble terminada sobre un buffer circular. |
| `HashMap` | Rust | Mapa hash no ordenado. |
| `BTreeMap` | Rust | Mapa ordenado por clave. |
| `HashSet` | Rust | Conjunto hash sin orden. |
| `BTreeSet` | Rust | Conjunto ordenado. |
| iterador | Rust | Objeto que produce una secuencia de valores bajo demanda. |
| adaptador | Rust | Operación perezosa sobre un iterador (`map`, `filter`). |
| consumidor | Rust | Operación que agota un iterador (`collect`, `fold`). |
| `Future` | Rust | Valor que representa un cálculo asíncrono pendiente. |
| executor | Rust | Runtime que conduce `Future`s. |
| `Pin` | Rust | Garantía de que un valor no se mueve en memoria. |
| `Send` | Rust | Tipo seguro para transferirse entre hilos. |
| `Sync` | Rust | Tipo seguro para compartirse por referencia entre hilos. |
| `Mutex` | Rust | Exclusión mutua con bloqueo. |
| `RwLock` | Rust | Bloqueo de lectores/escritor. |
| atomic | Rust | Operación indivisible sobre un entero/bool. |
| ordering | Rust | Garantía de memoria de una operación atómica. |

### 67.6 Compilación y herramientas

| Término | Origen | Definición |
|---|---|---|
| transpilar | Doc | Traducir código fuente a otro lenguaje fuente. |
| codegen | Doc | Fase que emite Rust a partir del AST/IR de PenguScript. |
| source map | Doc | Correspondencia entre posiciones PenguScript y Rust generado. |
| front-end | Doc | Lexer, parser, resolver y typechecker. |
| lower | Doc | Conversión de azúcar a forma core. |
| Tome | Pengu | Unidad de paquete; su manifiesto es `Tome.toml`. |
| target | Doc | Binario, librería, test, bench o ejemplo. |
| feature | Rust | Conjunto de código activable en compilación. |
| cfg | Rust | Configuración de compilación (`target_os`, `feature`, etc.). |
| proc macro | Rust | Macro que se ejecuta en compilación y produce tokens. |
| macro_rules | Rust | Macro declarativa de tokens. |
| derive | Rust | Macro que genera implementaciones automáticas. |
| doc test | Doc | Fragmento de documentación que se compila/ejecuta. |
| property test | Doc | Test que verifica una propiedad sobre entradas generadas. |
| fuzzing | Doc | Prueba con entradas aleatorias para encontrar crashes. |
| benchmark | Doc | Medición reproducible de rendimiento. |
| LSP | Doc | Protocolo de servidor de lenguaje para editores. |
| MSRV | Rust | Versión mínima de Rust soportada. |
| semver | Doc | Versionado semántico `MAJOR.MINOR.PATCH`. |
| ADR | Doc | Registro de una decisión de arquitectura. |

### 67.7 Reglas de estilo del glosario

1. Un término se define una vez; las demás secciones enlazan aquí.
2. No se usan definiciones circulares (“A es B; B es A”).
3. Los términos de Rust se marcan como tales.
4. Los términos mágicos se traducen a su construcción Rust.
5. Una definición no introduce una regla nueva; solo resume.
6. Si un término cambia, se actualiza aquí y en §70.

[↑ Volver al índice](#indice)
