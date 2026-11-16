<a id="sec-65-diagnosticos"></a>
## 65. Catálogo de diagnósticos

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 10 |
| Rust | — |
| Palabras mágicas | — |
| Depende de | §2–§59 |
| Ejemplos ejecutables | `no` |

Este catálogo reúne los códigos `PGS-E...` y `PGS-W...` definidos en la especificación. La columna **Sección** indica dónde se explica el diagnóstico; si un código aparece en varias, se lista la primera aparición. Los códigos no se inventan aquí: se extraen de las tablas y del texto de las secciones.

**Total:** 457 códigos únicos (373 errores, 84 warnings).

### 65.1 Convención

| Prefijo | Significado |
|---|---|
| `PGS-E` | Error: el programa no compila. |
| `PGS-W` | Warning: el programa compila; puede silenciarse con `@@allow`. |
| `PGS-E1xxx` | Léxico/indentación. |
| `PGS-E2xxx` | Programa/compilación. |
| `PGS-E3xxx` | Tipos. |
| `PGS-E4xxx` | Constantes/statics. |
| `PGS-E5xxx` | Scope. |
| `PGS-E6xxx` | Expresiones. |
| `PGS-E9xxx` | Primitivos/strings/operadores/control. |
| `PGS-E16xx`–`E21xx` | Ownership, borrowing, lifetimes, punteros, memoria. |
| `PGS-E22xx`–`E27xx` | Colecciones. |
| `PGS-E28xx`–`E32xx` | Structs, enums, patrones, impls, aliases. |
| `PGS-E33xx`–`E40xx` | Genéricos, traits, closures, HOF, operadores. |
| `PGS-E41xx`–`E47xx` | Módulos, visibilidad, tomes, atributos, macros, derives, build. |
| `PGS-E48xx`–`E55xx` | Errores, iteradores, async, concurrencia, unsafe, FFI, const, no_std. |
| `PGS-E56xx`–`E59xx` | Testing, docs, herramientas, estilo. |
| `PGS-E61xx`–`E62xx` | Apéndices: léxico (61) y precedencia (62). |

### 65.2 Catálogo por familia

#### 65.2.10 Familia `10xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E1001` | BOM al inicio del archivo | guardar sin BOM | §2 |
| `PGS-E1002` | `CR` suelto o salto no válido | usar `LF` o `CRLF` | §2 |
| `PGS-E1003` | tabulador fuera de string/comentario | reemplazar por cuatro espacios | §2 |
| `PGS-E1004` | `DEDENT` sin nivel coincidente | alinear con un nivel abierto | §2 |
| `PGS-E1005` | `INDENT` inesperado | eliminar la indentación o abrir un bloque | §2 |
| `PGS-E1006` | falta el bloque esperado | indentar el cuerpo con cuatro espacios | §2 |
| `PGS-E1007` | comentario o string sin cerrar | cerrar `]]`, `"` o `"""` | §2 |
| `PGS-E1008` | escape inválido | usar un escape de §2.5 | §2 |
| `PGS-E1009` | literal inválido | revisar dígitos, sufijo o separador | §2 |
| `PGS-E1010` | `spell`/`spirit` retirados | usar `->` o `@` | §2 |
| `PGS-E1011` | cuerpo indentado mezcla entradas de mapa y expresiones | elegir mapa o array | §2 |
| `PGS-E1012` | cuerpo indentado vacío | usar `[]`, `{}`, `Vec[]` o `Set[]` | §2 |

#### 65.2.16 Familia `16xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E1601` | uso después de move | prestar, reordenar o clonar | §16 |
| `PGS-E1602` | `Copy` + `Drop` | quitar `Copy` o `Drop` | §16 |
| `PGS-E1603` | `Copy` sin `Clone` | derivar `Clone` | §16 |
| `PGS-E1604` | move parcial de tipo con `Drop` | mover el valor completo o prestar | §16 |
| `PGS-E1605` | move de un valor prestado | terminar el préstamo o clonar | §16 |
| `PGS-E1606` | uso de un `rune` parcialmente movido | usar los campos no movidos | §16 |
| `PGS-W1601` | `clone` innecesario | prestar en su lugar | §16 |

#### 65.2.17 Familia `17xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E1701` | préstamo mutable y compartido solapados | terminar uno antes del otro | §17 |
| `PGS-E1702` | move mientras hay un préstamo activo | esperar a que termine el préstamo | §17 |
| `PGS-E1703` | dos préstamos mutables solapados | usar `split_at_mut` o separar campos | §17 |
| `PGS-E1704` | préstamo de un temporal que no vive suficiente | guardar el temporal en un `bind` | §17 |
| `PGS-E1705` | retorno de referencia sin lifetime | añadir `'a` o devolver el valor | §17 |
| `PGS-E1706` | `&mut` sobre binding inmutable | usar `morph` | §17 |
| `PGS-W1701` | préstamo compartido innecesariamente largo | acortar el scope | §17 |

#### 65.2.18 Familia `18xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E1801` | lifetime de salida ambiguo | añadir `'a` y ligarlo | §18 |
| `PGS-E1802` | retorno de referencia a un local | devolver el valor o mover el dueño | §18 |
| `PGS-E1803` | lifetime no declarado en el `rune` | añadir `['a]` | §18 |
| `PGS-E1804` | bound `T: 'a` incumplido | acortar el lifetime o cambiar el tipo | §18 |
| `PGS-E1805` | `'static` requerido pero el valor es local | usar un `String`/`Box` o un estático | §18 |
| `PGS-E1806` | varianza incompatible | rediseñar el contenedor | §18 |
| `PGS-W1801` | lifetime explícito innecesario | dejar la elisión | §18 |

#### 65.2.19 Familia `19xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E1901` | deref de raw pointer fuera de `curse` | envolver en `curse` | §19 |
| `PGS-E1902` | llamada a función `curse` sin bloque `curse` | añadir `curse` | §19 |
| `PGS-E1903` | `&raw mut` sobre binding inmutable | usar `morph` | §19 |
| `PGS-E1904` | `NonNull` construido desde null | usar un valor válido | §19 |
| `PGS-E1905` | aritmética fuera de la allocation | rediseñar el offset | §19 |
| `PGS-E1906` | escritura con `*const T` | usar `*mut T` | §19 |
| `PGS-W1901` | `curse` sin comentario `SAFETY` | documentar el contrato | §19 |

#### 65.2.20 Familia `20xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E2001` | `grimoire` en una biblioteca | moverlo a `main.pengu` | §3 |
| `PGS-E2002` | más de un `grimoire` en un binario | dejar uno | §3 |
| `PGS-E2003` | sentencia o `bind` en nivel de módulo | mover dentro de una función | §3 |
| `PGS-E2004` | no se encuentra el archivo del `scroll` | crear el archivo o usar cuerpo inline | §3 |
| `PGS-E2005` | módulo duplicado o nombre no coincide | alinear archivo y declaración | §3 |
| `PGS-E2006` | importación ambigua o no resuelta | usar una ruta explícita | §3 |
| `PGS-E2007` | item privado usado desde otro módulo | añadir `unveil` | §3 |
| `PGS-E2008` | `Tome.toml` inválido | revisar §3.7 y D17 | §3 |
| `PGS-E2009` | meta sin raíz `.pengu` | declarar `path` | §3 |
| `PGS-E2010` | source map inconsistente | reportar un bug del compilador | §3 |
| `PGS-W2001` | `Mutex` envenenado recuperado con `unwrap` | usar `match`/`PoisonError` | §20 |
| `PGS-W2002` | ciclo `Rc`/`Arc` sin `Weak` | añadir `Weak` | §20 |

#### 65.2.21 Familia `21xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E2101` | `repr` incompatible con el tipo | quitar `repr` o cambiar la representación | §21 |
| `PGS-E2102` | referencia a campo de `repr(packed)` | copiar con `read_unaligned` | §21 |
| `PGS-E2103` | move parcial de un tipo con `Drop` | mover el valor completo o usar `Option` | §21 |
| `PGS-E2104` | `MaybeUninit` leído sin inicializar | escribir antes de `assume_init` | §21 |
| `PGS-E2105` | `size_of`/`align_of` sobre unsized | usar `&T`/`Box[T]` | §21 |
| `PGS-E2106` | `repr(C)` con campos no FFI-safe | usar tipos FFI-safe | §21 |
| `PGS-W2101` | fuga probable | revisar ciclos/`forget` | §21 |
| `PGS-W2102` | `mem::forget` explícito | justificar o usar `ManuallyDrop` | §21 |
| `PGS-W2103` | `repr(Rust)` en FFI | usar `repr(C)` | §21 |

#### 65.2.22 Familia `22xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E2201` | longitudes de array incompatibles | usar `Vec` o convertir | §22 |
| `PGS-E2202` | índice de tipo no entero | usar `Usize` | §22 |
| `PGS-E2203` | array sin contexto de tipo | anotar `[T; N]` | §22 |
| `PGS-E2204` | slice con rango invertido | corregir `a..b` | §22 |
| `PGS-E2205` | array demasiado grande para el stack | usar `Vec`/`Box` | §22 |
| `PGS-W2201` | indexación directa con índice externo | usar `get` | §22 |
| `PGS-W2202` | slice que retiene un préstamo largo | acortar el scope | §22 |

#### 65.2.23 Familia `23xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E2301` | `Vec[]` sin contexto de tipo | anotar `Vec[T]` | §23 |
| `PGS-E2302` | índice fuera de rango | usar `get` o comprobar `len` | §23 |
| `PGS-E2303` | `sort` sin `Ord` | usar `sort_by` o derivar `Ord` | §23 |
| `PGS-E2304` | `dedup` sin `PartialEq` | derivar `PartialEq` | §23 |
| `PGS-E2305` | `drain` con rango inválido | corregir el rango | §23 |
| `PGS-W2301` | `Vec` que crece sin reservar | usar `with_capacity` si se conoce | §23 |
| `PGS-W2302` | `insert(0, x)` repetido | usar `VecDeque` | §23 |

#### 65.2.24 Familia `24xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E2401` | índice de tupla inexistente | usar un índice válido o un `rune` | §24 |
| `PGS-E2402` | aridad distinta en destructuring | ajustar el patrón | §24 |
| `PGS-E2403` | tupla de 13+ elementos con `Debug` | usar un `rune` | §24 |
| `PGS-E2404` | `tuple[i]` con índice variable | usar un array | §24 |
| `PGS-W2401` | tupla usada como API pública | preferir un `rune` con nombres | §24 |

#### 65.2.25 Familia `25xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E2501` | clave sin `Eq + Hash` | derivar o usar `BTreeMap` | §25 |
| `PGS-E2502` | clave sin `Ord` en `BTreeMap` | derivar `Ord` | §25 |
| `PGS-E2503` | `map[k]` con clave posiblemente ausente | usar `get`/`entry` | §25 |
| `PGS-E2504` | préstamo mutable y lectura simultánea | separar scopes | §25 |
| `PGS-E2505` | set con elemento no hashable | cambiar el tipo | §25 |
| `PGS-W2501` | clave duplicada en literal | eliminar duplicado | §25 |
| `PGS-W2502` | `HashMap` iterado esperando orden | usar `BTreeMap` | §25 |

#### 65.2.26 Familia `26xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E2601` | `BinaryHeap` con tipo sin `Ord` | derivar `Ord` o usar `Reverse` | §26 |
| `PGS-E2602` | índice en `LinkedList` | usar `Vec`/`VecDeque` | §26 |
| `PGS-E2603` | `VecDeque` usado como slice | `make_contiguous()` | §26 |
| `PGS-E2604` | estructura externa sin dependencia | añadir a `Tome.toml` | §26 |
| `PGS-W2601` | `LinkedList` para acceso secuencial | preferir `Vec`/`VecDeque` | §26 |
| `PGS-W2602` | `BinaryHeap` esperando orden estable | añadir un contador de desempate | §26 |

#### 65.2.27 Familia `27xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E2701` | rango invertido | corregir `a..b` | §27 |
| `PGS-E2702` | rango fuera de bounds en índice | usar `get` o comprobar `len` | §27 |
| `PGS-E2703` | `step_by(0)` | usar un paso positivo | §27 |
| `PGS-E2704` | rango no iterable | usar un tipo `Step` o un iterador | §27 |
| `PGS-E2705` | pattern de rango no exhaustivo | añadir `_` | §27 |
| `PGS-W2701` | índice con rango calculado sin comprobar | usar `get` | §27 |
| `PGS-W2702` | `..` en una API pública | acotar el rango | §27 |

#### 65.2.28 Familia `28xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E2801` | campo duplicado | eliminar o renombrar | §28 |
| `PGS-E2802` | campo faltante en el literal | añadir el campo o `..base` | §28 |
| `PGS-E2803` | parámetro de tipo no usado | añadir `PhantomData` | §28 |
| `PGS-E2804` | `@@derive` no soportado en el campo | derivar en el `rune` | §28 |
| `PGS-E2805` | `unveil` en campo de tuple struct | usar struct nombrada | §28 |
| `PGS-E2806` | `..base` no es el último | moverlo al final | §28 |
| `PGS-W2801` | struct con muchos campos públicos | revisar encapsulación | §28 |
| `PGS-W2802` | `repr(packed)` en API pública | revisar alineación | §28 |

#### 65.2.29 Familia `29xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E2901` | variante duplicada | renombrar | §29 |
| `PGS-E2902` | nombre de variante no único | renombrar | §29 |
| `PGS-E2903` | discriminante duplicado | cambiar el valor | §29 |
| `PGS-E2904` | `as` sobre variante con datos | usar `match` | §29 |
| `PGS-E2905` | `match` no exhaustivo | añadir variante o `else` | §29 |
| `PGS-E2906` | `@@repr` inválido para la variante | usar fieldless o cambiar repr | §29 |
| `PGS-W2901` | enum con una sola variante | considerar un `rune` | §29 |
| `PGS-W2902` | `@@non_exhaustive` sin `else` fuera de la crate | añadir `else` | §29 |

#### 65.2.30 Familia `30xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E3001` | tipo esperado y tipo encontrado no coinciden | revisar la anotación o la expresión | §4 |
| `PGS-E3002` | no se puede inferir un tipo | añadir `: Tipo` | §4 |
| `PGS-E3003` | tipo desconocido | importarlo con `summon` o declararlo | §4 |
| `PGS-E3004` | faltan argumentos de tipo | añadir `[T]` | §4 |
| `PGS-E3005` | aridad de tipo incorrecta | revisar parámetros | §4 |
| `PGS-E3006` | `?`/`!` mal aplicado | usar `Option[T]`/`Result[T, E]` | §4 |
| `PGS-E3007` | trait bound no satisfecho | implementar el `pact` o ajustar el bound | §4 |
| `PGS-E3008` | implementación huérfana o solapada | mover el `pact`/tipo o eliminar el solapamiento | §4 |
| `PGS-E3009` | `dyn` no es object-safe | quitar métodos genéricos o usar `impl Trait` | §4 |
| `PGS-E3010` | `impl Trait` en posición inválida | moverlo a parámetro/retorno | §4 |
| `PGS-W3001` | `_` que oculta un valor útil | nombrar el binding | §30 |
| `PGS-W3002` | `match` con un solo brazo | considerar `if let` | §30 |

#### 65.2.31 Familia `31xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E3101` | `@` en función asociada | añadir receptor o quitar `@` | §31 |
| `PGS-E3102` | método duplicado | renombrar | §31 |
| `PGS-E3103` | `Self` fuera de `ritual` | mover dentro | §31 |
| `PGS-E3104` | receptor incompatible con el uso | usar `morph`/`@mut` | §31 |
| `PGS-E3105` | `ritual` inherente sobre tipo externo | mover a un newtype | §31 |
| `PGS-E3106` | violación de coherencia/huérfano | implementar trait local o tipo local | §31 |
| `PGS-E3107` | trait implementado dos veces | eliminar duplicado | §31 |
| `PGS-E3108` | falta un método del `pact` | implementarlo | §31 |
| `PGS-W3101` | método inherente y de trait con el mismo nombre | renombrar | §31 |
| `PGS-W3102` | `@own` en un método que no consume | usar `@` | §31 |

#### 65.2.32 Familia `32xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E3201` | alias recursivo | romper el ciclo | §32 |
| `PGS-E3202` | alias usado para violar coherencia | usar un newtype local | §32 |
| `PGS-E3203` | operación entre numéricos distintos | convertir con `as` | §32 |
| `PGS-E3204` | `as` sobre enum con datos | usar `match` | §32 |
| `PGS-E3205` | `From` lossy | usar `TryFrom` | §32 |
| `PGS-E3206` | `transmute` fuera de `curse` | envolver en `curse` | §32 |
| `PGS-E3207` | `transmute` con tamaños distintos | usar otra conversión | §32 |
| `PGS-E3208` | cast de referencia inválido | usar `From`/`Into` | §32 |
| `PGS-W3201` | cast constante con pérdida | revisar el valor | §32 |
| `PGS-W3202` | newtype sin constructor validado | añadir `new` con validación | §32 |

#### 65.2.33 Familia `33xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E3301` | parámetro de tipo no declarado | añadirlo a `[T]` | §33 |
| `PGS-E3302` | aridad de argumentos incorrecta | ajustar `Tipo[A, B]` | §33 |
| `PGS-E3303` | argumento de tipo en posición de valor | usar turbofish o un valor | §33 |
| `PGS-E3304` | parámetro no usado ni en campos ni en retorno | usar `PhantomData[T]` o eliminarlo | §33 |
| `PGS-E3305` | default de parámetro de tipo | eliminar el default | §33 |
| `PGS-E3306` | no se puede inferir el parámetro | escribir `foo[Tipo](...)` | §33 |
| `PGS-E3307` | const generic con tipo distinto de `Usize` | usar `Usize` | §33 |
| `PGS-E3308` | expresión no constante como argumento const | usar un literal o `sigil` | §33 |
| `PGS-W3301` | nombre de parámetro de una sola letra no convencional | usar `T`/`K`/`V` o un nombre claro | §33 |

#### 65.2.34 Familia `34xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E3401` | `where` vacío | eliminarlo | §34 |
| `PGS-E3402` | bound no satisfecho | implementar el `pact` o cambiar el tipo | §34 |
| `PGS-E3403` | bound sobre un parámetro no declarado | añadirlo a `[T]` | §34 |
| `PGS-E3404` | `T: ?Sized` usado por valor | pasar `&T`, `Box[T]` o un puntero | §34 |
| `PGS-E3405` | lifetime bound imposible | acortar el préstamo o usar `'static` | §34 |
| `PGS-E3406` | bound de tipo asociado mal formado | usar `Pact[Item = Tipo]` | §34 |
| `PGS-E3407` | `where` en un `ritual` incompatible con el tipo | alinear los bounds | §34 |
| `PGS-W3401` | bound redundante | eliminar o justificar | §34 |

#### 65.2.35 Familia `35xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E3501` | falta un método requerido | implementarlo | §35 |
| `PGS-E3502` | `pact` implementado dos veces | eliminar duplicado | §35 |
| `PGS-E3503` | `Self` fuera de `pact`/`ritual` | moverlo dentro | §35 |
| `PGS-E3504` | implementaciones solapadas | separar tipos o bounds | §35 |
| `PGS-E3505` | violación de huérfano | hacer local el tipo o el `pact` | §35 |
| `PGS-E3506` | `dyn Pact` no object-safe | quitar genéricos/`Self` por valor | §35 |
| `PGS-E3507` | método de `pact` sin receptor mal usado | añadir `@` o llamar como asociado | §35 |
| `PGS-W3501` | método default sobrescrito sin necesidad | documentar la diferencia | §35 |
| `PGS-W3502` | blanket impl muy amplia | acotar el bound | §35 |

#### 65.2.36 Familia `36xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E3601` | tipo asociado no fijado | añadir `essence Item = Tipo` | §36 |
| `PGS-E3602` | tipo asociado fijado dos veces | eliminar duplicado | §36 |
| `PGS-E3603` | GAT con parámetro no usado | usar el parámetro o eliminarlo | §36 |
| `PGS-E3604` | bound de asociado incompatible | alinear `Pact[Item = Tipo]` | §36 |
| `PGS-E3605` | `impl Trait` en posición inválida | moverlo a retorno/parámetro | §36 |
| `PGS-E3606` | `async fn` en `pact` object-safe | usar `dyn` compatible o evitar | §36 |
| `PGS-E3607` | constante asociada no const | simplificar la expresión | §36 |
| `PGS-W3601` | GAT que solo se usa con un lifetime | simplificar a tipo asociado | §36 |

#### 65.2.37 Familia `37xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E3701` | `for` sin lifetime | usar `for<'a>` | §37 |
| `PGS-E3702` | lifetime de retorno no conectado a un parámetro | añadir el préstamo o `'static` | §37 |
| `PGS-E3703` | HRTB no satisfecho por el closure | usar `move` o un `fn` item | §37 |
| `PGS-E3704` | `dyn` sin puntero | envolver en `Box[dyn ...]` o `&dyn ...` | §37 |
| `PGS-E3705` | `for<T>` o `for<const N>` | solo se cuantifican lifetimes | §37 |
| `PGS-W3701` | `for<'a>` redundante con la elisión | simplificar si no cambia la semántica | §37 |

#### 65.2.38 Familia `38xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E3801` | closure con tipo de retorno explícito | quitarlo; se infiere | §38 |
| `PGS-E3802` | `bind` para una closure `FnMut` | usar `morph` | §38 |
| `PGS-E3803` | captura movida y usada después | reordenar o clonar | §38 |
| `PGS-E3804` | `move` innecesario que impide reutilizar | quitar `move` | §38 |
| `PGS-E3805` | closure devuelta sin `move` | añadir `move` | §38 |
| `PGS-E3806` | `impl Fn` en campo de struct | usar genérico o `Box[dyn Fn]` | §38 |
| `PGS-E3807` | recursión por nombre de closure | usar función nombrada | §38 |
| `PGS-W3801` | closure que podría ser función | extraer a `name = (...) -> ...` | §38 |

#### 65.2.39 Familia `39xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E3901` | `map` sin tipo de `collect` | añadir turbofish `collect[Vec[Int]]()` | §39 |
| `PGS-E3902` | `fold` con acumulador incompatible | anotar el inicial o el retorno | §39 |
| `PGS-E3903` | `FnOnce` llamado dos veces | usar `Fn`/`FnMut` o consumir una vez | §39 |
| `PGS-E3904` | `?` en función que no devuelve `?T`/`!T` | cambiar el retorno o usar `match` | §39 |
| `PGS-E3905` | `and_then` devuelve `?T` dentro de `!T` | convertir con `ok_or`/`map_err` | §39 |
| `PGS-W3901` | cadena de iteradores con `collect` intermedio innecesario | eliminar el `Vec` intermedio | §39 |

#### 65.2.40 Familia `40xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E4001` | inicializador no constante | usar literales o una función `eternal` | §6 |
| `PGS-E4002` | `static mut` o `relic mut` | usar `@@shared` con `Mutex`/atómico | §6 |
| `PGS-E4003` | asignación o `morph` sobre `relic` | declarar un `rune` o usar interior mutability | §6 |
| `PGS-E4004` | `relic` no es `Sync` | usar `Mutex`/`RwLock` o `@@thread_local` | §6 |
| `PGS-E4005` | `@@shared` mal aplicado | aplicarlo solo a `relic` con tipo `Sync` | §6 |
| `PGS-E4006` | ciclo de constantes | romper la dependencia | §6 |
| `PGS-E4007` | `relic` dentro de una función | moverlo al módulo | §6 |
| `PGS-E4008` | `@@thread_local` fuera de módulo | moverlo al módulo | §6 |
| `PGS-E4009` | acceso FFI sin `curse` | envolver en `curse` | §6 |
| `PGS-E4010` | nombre que no es `SCREAMING_SNAKE_CASE` | renombrar | §6 |

#### 65.2.41 Familia `41xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E4101` | `essence Output` faltante | declararlo en el `ritual` | §40 |
| `PGS-E4102` | receptor incorrecto | `@own` para operadores que consumen, `@mut` para asignación | §40 |
| `PGS-E4103` | `Index` devuelve un valor | devolver `&Output` | §40 |
| `PGS-E4104` | `PartialOrd` sin `PartialEq` | implementar ambos o derivar | §40 |
| `PGS-E4105` | `Display` para un tipo sin representación estable | usar `Debug` o un método | §40 |
| `PGS-E4106` | `From` con dos tipos externos | newtype local | §40 |
| `PGS-E4110` | `scroll` sin archivo y sin cuerpo | crear el archivo o el cuerpo | §41 |
| `PGS-E4111` | dos raíces (`main.pengu` y `lib.pengu`) | elegir una | §41 |
| `PGS-E4112` | `foo.pengu` y `foo/scroll.pengu` a la vez | borrar uno o usar `@@path` | §41 |
| `PGS-E4113` | dos `summon` con el mismo nombre | aliasar uno | §41 |
| `PGS-E4114` | `scroll` dentro de una función | moverlo al nivel de módulo | §41 |
| `PGS-E4115` | path `self::` | usar `crate::`/`super::` o el nombre directo | §41 |
| `PGS-W4101` | `Deref` usado para simular herencia | composición o `pact` | §40 |
| `PGS-W4110` | glob import en API pública | importar nombres explícitos | §41 |

#### 65.2.42 Familia `42xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E4210` | `unveil` sobre un item que no lo admite | quitar o mover al item | §42 |
| `PGS-E4211` | item privado usado desde otro módulo | `unveil` o reexportar | §42 |
| `PGS-E4212` | `unveil` en campo de variante de enum | la variante hereda del enum | §42 |
| `PGS-E4213` | `pub(in path)` que no es ancestro | usar un ancestro real | §42 |
| `PGS-E4214` | tipo privado en API pública | hacer público el tipo o privada la API | §42 |
| `PGS-W4210` | supertrait privado en trait público | documentar el sellado | §42 |
| `PGS-W4211` | `unveil` redundante en el crate raíz | simplificar | §42 |

#### 65.2.43 Familia `43xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E4310` | falta `Tome.toml` | crearlo en la raíz | §43 |
| `PGS-E4311` | versión de `pengu` incompatible | actualizar el compilador o el campo | §43 |
| `PGS-E4312` | `rust-version` menor que 1.85 | subir el MSRV | §43 |
| `PGS-E4313` | `path` de meta no es `.pengu` | corregir la ruta | §43 |
| `PGS-E4314` | clave protegida en `[cargo]` | quitarla del passthrough | §43 |
| `PGS-E4315` | workspace con miembro fuera de la raíz | declarar el path o moverlo | §43 |
| `PGS-W4310` | lockfile desactualizado | `pengu update` | §43 |

#### 65.2.44 Familia `44xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E4410` | atributo desconocido | importar la proc macro o corregir el nombre | §44 |
| `PGS-E4411` | `@@!` después de un item | moverlo al inicio | §44 |
| `PGS-E4412` | derive no importado | `summon` la crate | §44 |
| `PGS-E4413` | `@@repr` en un item no válido | aplicarlo a struct/enum | §44 |
| `PGS-E4414` | `@@derive` en una función | quitarlo | §44 |
| `PGS-W4410` | `cfg` con feature no declarada | declararla en `Tome.toml` | §44 |
| `PGS-W4411` | atributo redundante | simplificar | §44 |

#### 65.2.45 Familia `45xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E4501` | nombre de macro inválido | usar un identificador | §45 |
| `PGS-E4502` | brazo mal formado | revisar `patrón => expansión` | §45 |
| `PGS-E4503` | delimitadores desbalanceados | cerrar `()`, `[]`, `{}` | §45 |
| `PGS-E4504` | metavariable repetida de forma inconsistente | igualar repeticiones | §45 |
| `PGS-E4505` | macro no encontrada | `summon` o definirla | §45 |
| `PGS-E4506` | definición de proc macro en PenguScript | escribirla en Rust | §45 |
| `PGS-W4501` | macro definida y no usada | eliminarla o usarla | §45 |
| `PGS-W4502` | invocación de macro en posición de tipo | usar un tipo o una macro de tipo | §45 |

#### 65.2.46 Familia `46xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E4601` | `@@derive` en un item no válido | moverlo a `rune`/`enchanting` | §46 |
| `PGS-E4602` | derive desconocido | importar la crate o corregir el nombre | §46 |
| `PGS-E4603` | `Copy` sin `Clone` | añadir `Clone` | §46 |
| `PGS-E4604` | `Copy` en un tipo con `Drop` | quitar `Copy` o `Drop` | §46 |
| `PGS-E4605` | `Eq`/`Ord` con `Float` | no derivarlos; implementar a mano | §46 |
| `PGS-E4606` | `Hash` sin `Eq` | añadir `Eq` | §46 |
| `PGS-W4601` | `Debug` en un tipo con secretos | implementar `Debug` a mano | §46 |
| `PGS-W4602` | derive innecesario | eliminarlo | §46 |

#### 65.2.47 Familia `47xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E4701` | `build.pengu` sin `grimoire` | añadir la entrada | §47 |
| `PGS-E4702` | directiva `cargo:` mal formada | revisar la línea | §47 |
| `PGS-E4703` | `OUT_DIR` no usado | escribir el archivo en `OUT_DIR` | §47 |
| `PGS-E4704` | feature no declarada | añadirla a `[features]` | §47 |
| `PGS-E4705` | `cfg` con clave desconocida | usar una clave válida | §47 |
| `PGS-E4706` | build script importa la crate actual | quitar la dependencia | §47 |
| `PGS-E4707` | código generado no determinista | eliminar timestamp/rutas | §47 |
| `PGS-W4710` | `cfg` de feature no declarada | declararla o corregir | §47 |
| `PGS-W4711` | `rerun-if-changed` ausente | declarar las entradas | §47 |

#### 65.2.48 Familia `48xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E4801` | `?` fuera de función compatible | devolver `Result`/`Option` o usar `match` | §48 |
| `PGS-E4802` | `?` de `Option` en función `Result` | convertir con `ok_or`/`ok_or_else` | §48 |
| `PGS-E4803` | error sin `From` al error de retorno | implementar `From` o mapear | §48 |
| `PGS-E4804` | `?` en `grimoire` no fallible | declarar `grimoire: !Unit` | §48 |
| `PGS-E4805` | `unwrap` en código de biblioteca | usar `?` o `expect` con invariante | §48 |
| `PGS-E4806` | `panic` para entrada inválida | devolver `Result` | §48 |
| `PGS-E4807` | `Error` sin `Display`/`Debug` | implementar ambos | §48 |
| `PGS-W4801` | `Box<dyn Error>` en API pública | definir un error de dominio | §48 |
| `PGS-W4802` | `catch_unwind` para flujo normal | usar `Result` | §48 |

#### 65.2.49 Familia `49xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E4901` | `for` sobre un valor no iterable | usar `.iter()`/`IntoIterator` | §49 |
| `PGS-E4902` | `iter_mut` sin binding `morph` | declarar `morph` | §49 |
| `PGS-E4903` | `collect` sin tipo de destino | añadir turbofish | §49 |
| `PGS-E4904` | `rev` sin `DoubleEndedIterator` | usar `collect` + `rev` | §49 |
| `PGS-E4905` | `len` en iterador no exacto | contar con `count` | §49 |
| `PGS-E4906` | adaptador que no se consume | añadir consumidor | §49 |
| `PGS-E4907` | `?` dentro de `map` sin `Result` | usar `filter_map`/`collect` | §49 |
| `PGS-W4901` | `cycle` sin `take` | limitar | §49 |
| `PGS-W4902` | `for_each` con lógica compleja | usar `for` | §49 |

#### 65.2.50 Familia `50xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E5001` | nombre no resuelto | declararlo o importarlo | §7 |
| `PGS-E5002` | glob ambiguo | usar una ruta explícita | §7 |
| `PGS-E5003` | uso antes de la declaración local | mover la declaración | §7 |
| `PGS-E5004` | binding duplicado en el mismo bloque | usar shadowing en un bloque interno | §7 |
| `PGS-E5005` | item privado inaccesible | añadir `unveil` | §7 |
| `PGS-E5006` | `Self` fuera de `ritual`/`pact` | moverlo o cambiar por el tipo | §7 |
| `PGS-W5001` | shadowing de la prelude | renombrar si no es intencional | §7 |
| `PGS-W5002` | importación no usada | eliminarla o usarla | §7 |

#### 65.2.51 Familia `51xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E5101` | `spawn` con closure no `Send` | usar `move`/`Arc` | §51 |
| `PGS-E5102` | `spawn` con préstamo no `'static` | usar `scope` o mover | §51 |
| `PGS-E5103` | `Rc`/`RefCell` compartido entre hilos | usar `Arc`/`Mutex` | §51 |
| `PGS-E5104` | `join` ignorado | manejar `Result` | §51 |
| `PGS-E5105` | lock mantenido entre `await` | reducir el scope | §51 |
| `PGS-E5106` | `Ordering` incompatible con la operación | revisar el protocolo | §51 |
| `PGS-W5101` | `Mutex` en sección crítica larga | reducir | §51 |
| `PGS-W5102` | `thread_local` con estado grande | revisar | §51 |

#### 65.2.52 Familia `52xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E5201` | operación unsafe fuera de `curse` | envolver en `curse` | §52 |
| `PGS-E5202` | `curse` sin justificación | añadir `-- SAFETY:` | §52 |
| `PGS-E5203` | `transmute` con tamaños distintos | usar una conversión válida | §52 |
| `PGS-E5204` | `chimera` con campo no `Copy` | usar `ManuallyDrop` | §52 |
| `PGS-E5205` | `assume_init` sin inicializar | escribir antes | §52 |
| `PGS-E5206` | `&mut` aliasado | separar los préstamos | §52 |
| `PGS-W5201` | `curse` sin comentario SAFETY | documentar | §52 |
| `PGS-W5202` | `curse` innecesario | usar código seguro | §52 |

#### 65.2.53 Familia `53xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E5301` | `foreign` sin ABI | añadir `"C"` u otro ABI | §53 |
| `PGS-E5302` | tipo no `repr(C)` en el borde | añadir `@@repr(C)` | §53 |
| `PGS-E5303` | llamada a `foreign` sin `curse` | envolver en `curse` | §53 |
| `PGS-E5304` | `foreign` con cuerpo y sin `foreign "C"` | declarar el ABI | §53 |
| `PGS-E5305` | `CString` con `NUL` | validar el texto | §53 |
| `PGS-E5306` | `link_name` duplicado | usar un alias | §53 |
| `PGS-W5301` | puntero potencialmente nulo | comprobar `is_null` | §53 |
| `PGS-W5302` | panic a través de FFI | capturar o `"C-unwind"` | §53 |

#### 65.2.54 Familia `54xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E5401` | operación no const en `sigil`/`eternal` | usar una operación const | §54 |
| `PGS-E5402` | `static mut` | `@@shared` + `Mutex` | §54 |
| `PGS-E5403` | const generic inválido | usar entero/`Bool`/`Char` | §54 |
| `PGS-E5404` | heap en const | mover a runtime | §54 |
| `PGS-E5405` | `panic!` con formato | usar literal | §54 |
| `PGS-E5406` | recursión const infinita | añadir caso base | §54 |
| `PGS-E5407` | `?` en const | usar `match`/`if` | §54 |
| `PGS-W5401` | `sigil` muy grande | usar `relic` | §54 |
| `PGS-W5402` | `sigil` que debería ser `eternal` | extraer función | §54 |

#### 65.2.55 Familia `55xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E5501` | `std` en crate `no_std` | usar `core`/`alloc` | §55 |
| `PGS-E5502` | binario `no_std` sin panic handler | añadir `@@panic_handler` | §55 |
| `PGS-E5503` | `alloc` sin allocator | añadir `@@global_allocator` | §55 |
| `PGS-E5504` | entry point ausente | añadir `@@entry` | §55 |
| `PGS-E5505` | volatile fuera de `curse` | envolver en `curse` | §55 |
| `PGS-E5506` | target sin soporte | instalar target/`build-std` | §55 |
| `PGS-W5501` | `no_std` innecesario | usar `std` | §55 |
| `PGS-W5502` | handler de panic que retorna | usar `-> !` | §55 |

#### 65.2.56 Familia `56xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E5601` | `@@test` con parámetros | quitar parámetros | §56 |
| `PGS-E5602` | `@@test` con retorno no permitido | usar `Unit`/`!Unit` | §56 |
| `PGS-E5603` | `@@test` en `ritual`/`pact` | mover a módulo libre | §56 |
| `PGS-E5604` | `@@should_panic` sin `@@test` | añadir `@@test` | §56 |
| `PGS-E5605` | `@@ignore` sin `@@test` | añadir `@@test` | §56 |
| `PGS-E5606` | test de integración usa item privado | hacer `unveil` | §56 |
| `PGS-W5601` | test sin aserción | añadir `assert` o retorno | §56 |
| `PGS-W5602` | `debug_assert` en test | usar `assert` | §56 |

#### 65.2.57 Familia `57xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E5701` | `@@doc` en item privado con `--document-private-items` | revisar visibilidad | §57 |
| `PGS-E5702` | bloque de código sin lenguaje | declarar `text` | §57 |
| `PGS-E5703` | HTML crudo | usar Markdown | §57 |
| `PGS-W5701` | enlace intra-doc roto | corregir ruta | §57 |
| `PGS-W5702` | item público sin docs | añadir `---` | §57 |
| `PGS-W5703` | `@@deprecated` sin `since` | añadir versión | §57 |

#### 65.2.58 Familia `58xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E5801` | flag desconocido | revisar `--help` | §58 |
| `PGS-E5802` | `Tome.toml` inválido | corregir TOML/claves | §58 |
| `PGS-E5803` | conflicto de versiones | fijar versión | §58 |
| `PGS-E5804` | `pengu` fuera de un tome | `pengu init` | §58 |
| `PGS-E5805` | `sourcemap.json` inválido | regenerar build | §58 |
| `PGS-E5806` | `publish` sin licencia | añadir `license` | §58 |
| `PGS-W5801` | clave de config desconocida | eliminar/renombrar | §58 |
| `PGS-W5802` | `--offline` sin cache | descargar antes | §58 |

#### 65.2.60 Familia `60xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E6001` | `bind`/`morph`/asignación en posición de expresión | sacarlo a una sentencia | §8 |
| `PGS-E6002` | ramas o brazos con tipos incompatibles | unificar el tipo o añadir `Never` | §8 |
| `PGS-E6003` | `return` fuera de función/lambda | moverlo dentro | §8 |
| `PGS-E6004` | `break`/`continue` fuera de un bucle | moverlo dentro | §8 |
| `PGS-E6005` | `break expr` en `while`/`for` | usar `loop` o `break` sin valor | §8 |
| `PGS-E6006` | `do` sin bloque | indentar el cuerpo | §8 |
| `PGS-E6007` | condición de `if`/`while` no es `Bool` | comparar explícitamente | §8 |
| `PGS-E6008` | `match` no exhaustivo | añadir brazos o un comodín | §8 |
| `PGS-W6001` | valor de expresión no usado | usar `bind _ =` o consumir el valor | §8 |
| `PGS-W6002` | código inalcanzable | eliminar o reestructurar | §8 |

#### 65.2.61 Familia `61xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E6101` | Identificador prohibido o palabra retirada. | Usar el reemplazo indicado en §61.5. | §61 |
| `PGS-W6101` | Se sombrea un tipo del preludio. | Renombrar el tipo local o usar el path completo. | §61 |
| `PGS-W6102` | Se sombrea una función del preludio. | Renombrar la función local o usar el path completo. | §61 |

#### 65.2.62 Familia `62xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E6201` | Comparación encadenada. | Usar paréntesis y combinar con `and`. | §62 |
| `PGS-E6202` | Asignación encadenada. | Separar en sentencias. | §62 |
| `PGS-E6203` | Rango mal formado. | Escribir `a..b`, `a..=b` o `a..`. | §62 |

#### 65.2.90 Familia `90xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E9001` | literal entero fuera de rango | usar un tipo más ancho o corregir el valor | §9 |
| `PGS-E9002` | sufijo incompatible con el tipo | cambiar sufijo o anotación | §9 |
| `PGS-E9003` | separador `_` mal colocado | quitar o recolocar el separador | §9 |
| `PGS-E9004` | literal `Char` con más de un escalar | usar un string o un solo carácter | §9 |
| `PGS-E9005` | `Str` por valor | usar `&Str`, `String` o `Cow[Str]` | §9 |
| `PGS-E9006` | overflow aritmético | usar `checked_*`, `wrapping_*` o `saturating_*` | §9 |
| `PGS-E9007` | división o resto por cero | comprobar el divisor o usar `checked_div` | §9 |
| `PGS-E9008` | shift mayor o igual que el ancho | comprobar el shift o usar `checked_shl` | §9 |
| `PGS-E9009` | cast `as` no permitido | usar una conversión explícita de §10/§32 | §9 |
| `PGS-E9010` | `NonZero.new(0)` usado como valor | desenvolver el `?` o comprobar `none` | §9 |
| `PGS-W9001` | cast que puede perder información | usar `try_into()` si el rango no es fijo | §9 |

#### 65.2.91 Familia `91xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E9101` | `Str` usado por valor | usar `&Str`, `String` o `Cow[Str]` | §10 |
| `PGS-E9102` | escape Unicode inválido | usar un escalar válido | §10 |
| `PGS-E9103` | interpolación sin cerrar | cerrar `#{...}` | §10 |
| `PGS-E9104` | índice entero sobre string | usar `chars().nth` o `get` | §10 |
| `PGS-E9105` | rango fuera de límite de carácter | usar `get` y comprobar `none` | §10 |
| `PGS-E9106` | `Str + Str` | usar `format` o `join` | §10 |
| `PGS-E9107` | `parse` fallido | devolver `!T` o usar `unwrap_or` | §10 |
| `PGS-E9108` | bytes no UTF-8 | usar `from_utf8` y `?`, o `from_utf8_lossy` | §10 |
| `PGS-E9109` | NUL interior en string C | quitar el NUL o usar `[U8]` | §10 |
| `PGS-E9110` | `String` mutado mientras está prestado | terminar el préstamo o clonar | §10 |
| `PGS-W9101` | indexación por carácter en bucle | cachear `chars()` o usar `char_indices()` | §10 |

#### 65.2.92 Familia `92xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E9201` | tipos incompatibles en operador | convertir explícitamente o implementar el trait | §11 |
| `PGS-E9202` | operador no definido para el tipo | usar otro operador o implementar §40 | §11 |
| `PGS-E9203` | comparación encadenada | separar con `and` | §11 |
| `PGS-E9204` | asignación usada como expresión | convertirla en sentencia | §11 |
| `PGS-E9205` | `&&` o ` |  | §11 |
| `PGS-E9206` | `++`/`--` | usar `+= 1`/`-= 1` | §11 |
| `PGS-E9207` | shift negativo o demasiado grande | comprobar el valor o usar `checked_shl` | §11 |
| `PGS-E9208` | rango mal formado | usar `a..b` o `a..=b`, sin encadenar | §11 |
| `PGS-E9209` | `in` sobre un tipo sin pertenencia | usar un iterador o `contains` explícito | §11 |
| `PGS-E9210` | `?` fuera de función que devuelve `?T`/`!T` | cambiar el retorno o usar `match` | §11 |

#### 65.2.93 Familia `93xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E9301` | condición que no es `Bool` | usar una comparación o `is_empty`/`is_some` | §12 |
| `PGS-E9302` | `and`/`or` con un operando que no es `Bool` | convertir la condición explícitamente | §12 |
| `PGS-E9303` | `&&`/`\ | \ | §12 |
| `PGS-E9304` | `not` sobre un tipo que no es `Bool` | usar `!` para enteros o una comparación | §12 |
| `PGS-E9305` | conversión implícita a `Bool` | escribir la comparación | §12 |
| `PGS-E9306` | `match` de `Bool` no exhaustivo | cubrir `true` y `false` | §12 |
| `PGS-W9301` | `&`/`\ | ` sobre `Bool` en contexto lógico | §12 |

#### 65.2.94 Familia `94xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E9401` | condición que no es `Bool` | usar una comparación | §13 |
| `PGS-E9402` | ramas de `if` con tipos incompatibles | convertir a un tipo común | §13 |
| `PGS-E9403` | forma inline sin `then` | añadir `then` o indentar el bloque | §13 |
| `PGS-E9404` | `elseif` después de `else` | mover `else` al final | §13 |
| `PGS-E9405` | `else if` usado | usar `elseif` | §13 |
| `PGS-E9406` | `elseif` dentro de `unless` | usar `if` | §13 |
| `PGS-E9407` | `if` sin cuerpo | añadir un bloque o `then` | §13 |
| `PGS-E9408` | `if` sin `else` usado como valor | añadir `else` o descartar el valor | §13 |
| `PGS-W9401` | `unless not` redundante | simplificar a `if` | §13 |
| `PGS-W9402` | valor de `if` descartado como sentencia | usar `bind _ =` o consumir el valor | §13 |

#### 65.2.95 Familia `95xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E9501` | condición de `while` que no es `Bool` | usar una comparación | §14 |
| `PGS-E9502` | `break` fuera de un bucle | moverlo dentro o eliminarlo | §14 |
| `PGS-E9503` | `continue` fuera de un bucle | moverlo dentro o eliminarlo | §14 |
| `PGS-E9504` | `break value` en `while`/`for` | usar `loop` o `break` sin valor | §14 |
| `PGS-E9505` | `by` no positivo | usar un entero positivo | §14 |
| `PGS-E9506` | `by` fuera de un `for` | moverlo al `for` | §14 |
| `PGS-E9507` | `loop` sin `break` usado como valor | añadir `break` o cambiar el contexto | §14 |
| `PGS-E9508` | `break`/`continue` en comprehension | usar un `for` explícito | §14 |
| `PGS-E9509` | etiqueta no encontrada | etiquetar el bucle envolvente | §14 |
| `PGS-E9510` | `break` con tipos incompatibles | unificar los valores | §14 |
| `PGS-W9501` | `loop` que nunca termina | añadir una condición de salida | §14 |

#### 65.2.96 Familia `96xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E9601` | falta `-> Tipo` en una función nombrada | añadir el tipo de retorno | §15 |
| `PGS-E9602` | cuerpo inline en función nombrada | indentar el cuerpo o usar `=>` | §15 |
| `PGS-E9603` | `->` sin tipo | escribir el tipo | §15 |
| `PGS-E9604` | no se puede inferir el tipo de un parámetro lambda | anotar el parámetro o el contexto | §15 |
| `PGS-E9605` | lambda a nivel de módulo | usar una función nombrada | §15 |
| `PGS-E9606` | `self`/`this` usado | usar `@`/`@mut`/`@own` | §15 |
| `PGS-E9607` | receptor fuera de la primera posición | moverlo al inicio | §15 |
| `PGS-E9608` | `return` incompatible con el retorno | ajustar el valor o el tipo | §15 |
| `PGS-E9609` | `return` sin valor en función no `Unit` | devolver un valor | §15 |
| `PGS-E9610` | `return valor` en función `Unit` | usar `return` sin valor | §15 |
| `PGS-E9611` | `return` en función `Never` | eliminar el retorno | §15 |
| `PGS-E9612` | nombre de función duplicado | renombrar | §15 |
| `PGS-E9613` | `grimoire` con parámetros | quitar los parámetros | §15 |
| `PGS-E9614` | más de un `grimoire` | dejar uno | §15 |
| `PGS-E9615` | tipo de retorno de `grimoire` inválido | usar `Unit` o `!Unit` | §15 |
| `PGS-E9616` | overloading/default/varargs | usar una sola firma | §15 |
| `PGS-E9617` | captura en función nombrada | usar una lambda | §15 |
| `PGS-E9618` | número o tipo de argumentos incorrecto | ajustar la llamada | §15 |
| `PGS-E9619` | método `@mut` sobre binding inmutable | usar `morph` | §15 |
| `PGS-E9620` | receptor incompatible con el método | ajustar `@`/`@mut`/`@own` | §15 |

### 65.3 Criterios de aceptación

- [x] Todos los códigos de la especificación aparecen al menos una vez.
- [x] Cada fila tiene situación, solución y sección.
- [x] Los códigos están ordenados por familia y número.
- [x] No hay códigos duplicados.
- [x] El catálogo no introduce códigos nuevos.

[↑ Volver al índice](#indice)
