<a id="sec-61-lexico-keywords"></a>
## 61. Léxico y palabras clave

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 10 |
| Rust | — |
| Palabras mágicas | todas |
| Depende de | §2, §15, §41 |
| Ejemplos ejecutables | `no` |

### 61.1 Identificadores

Un identificador usa `XID_Start` + `XID_Continue` (Unicode 15) y no puede
empezar por dígito. Son sensibles a mayúsculas. No se permite `__` inicial
reservado al compilador. Los nombres de tipo usan `PascalCase`; funciones,
variables y módulos usan `snake_case`; constantes/statics `SCREAMING_SNAKE_CASE`.

### 61.2 Palabras reservadas

No pueden usarse como identificadores, campos, variantes, módulos ni alias.

| Categoría | Palabras |
|---|---|
| Declaraciones | `bind`, `morph`, `sigil`, `relic`, `rune`, `enchanting`, `pact`, `ritual`, `essence`, `scroll`, `summon`, `unveil`, `grimoire`, `incantation`, `chimera`, `foreign`, `eternal` |
| Modificadores | `dream`, `curse`, `mut`, `move`, `ref`, `own` |
| Control | `if`, `elseif`, `else`, `unless`, `then`, `match`, `when`, `for`, `while`, `loop`, `break`, `continue`, `return`, `by`, `do` |
| Operadores/palabras | `and`, `or`, `not`, `is`, `isnt`, `in`, `as`, `where`, `dyn`, `impl` |
| Literales | `true`, `false`, `none` |
| Recepción | `@`, `@mut`, `@own` (no son identificadores) |
| Tipos especiales | `Self`, `Unit`, `Never` |

### 61.3 Contextuales

Solo son palabras clave en la posición indicada; fuera de ella pueden ser
identificadores.

| Palabra | Contexto | Fuera del contexto |
|---|---|---|
| `by` | tras el iterable de `for` | identificador normal |
| `when` | inicio de brazo de `match` | identificador normal |
| `then` | tras condición de `if`/`unless`/`when` | identificador normal |
| `else` | rama alternativa | reservada (no identificador) |
| `as` | cast o alias de `summon` | reservada |
| `in` | membresía o `for` | reservada |
| `where` | cláusula de bounds | reservada |
| `dyn` | tipo trait object | reservada |
| `impl` | tipo opaco o bloque `ritual` | reservada |
| `move` | captura de lambda | reservada |
| `ref` | patrón por referencia | reservada |
| `own` | receptor por valor | reservada |
| `tome` | `unveil(tome)` | identificador normal |
| `scroll` | `unveil(scroll)` o declaración | reservada |
| `crate`, `super` | path | reservadas |
| `Self` | tipo del impl/trait | reservada |

### 61.4 Preludio

Nombres disponibles sin `summon`; **no** son palabras clave y pueden
sombrearse (con warning `PGS-W6101`).

| Grupo | Nombres |
|---|---|
| Opciones/resultados | `Option`, `Some`, `None`, `Result`, `Ok`, `Err` |
| Azúcar | `some`, `none`, `ok`, `err` |
| Errores | `Error`, `panic`, `assert`, `assert_eq`, `assert_ne`, `debug_assert` |
| Salida | `print`, `println`, `format`, `eprintln` |
| Conversión | `Into`, `From`, `TryInto`, `TryFrom`, `AsRef`, `AsMut` |
| Iteración | `Iterator`, `IntoIterator`, `Extend`, `FromIterator` |
| Memoria | `Box`, `Vec`, `String`, `Str`, `Cow`, `Rc`, `Arc` |
| Colecciones | `HashMap`, `HashSet`, `BTreeMap`, `BTreeSet`, `VecDeque` |
| Sincronización | `Mutex`, `RwLock`, `Atomic*`, `OnceLock`, `LazyLock` |
| Tiempo/IO | `Duration`, `Instant`, `File`, `Read`, `Write` |
| Matemáticas | `min`, `max`, `abs`, `sqrt`, `pow` |

`print`/`format` son intrínsecos del compilador, no funciones de un módulo.
El preludio completo está en §4.5; este listado es el conjunto de nombres que
el resolver inyecta.

### 61.5 Prohibidas y migraciones

Estas palabras se rechazan con `PGS-E6101` y un reemplazo sugerido.

| Prohibida | Motivo | Reemplazo |
|---|---|---|
| `spell` | retirada en v0.2 | `name = (...) -> Tipo` |
| `spirit` | retirada en v0.2 | `@`, `@mut`, `@own` |
| `class` | no hay herencia | `rune` + `pact`/`ritual` |
| `new` | no hay constructor especial | función `new` o literal |
| `this` | no hay `this` | `@` |
| `null`, `nil`, `undefined` | no hay nulos | `?T` + `none` |
| `var`, `let`, `const` | palabras de otros lenguajes | `morph`/`bind`/`sigil` |
| `fn`, `struct`, `enum`, `trait`, `impl`, `mod`, `use`, `pub`, `static` | palabras de Rust | `rune`, `enchanting`, `pact`, `ritual`, `scroll`, `summon`, `unveil`, `relic` |
| `async`, `await` | palabras de Rust | `dream`, `awaken` |
| `def`, `lambda`, `end`, `elif` | sintaxis ajena | `->`, `=>`, indentación, `elseif` |
| `yield` | no hay generadores | iteradores/`Iterator` |
| `try`, `catch`, `finally`, `throw` | no hay excepciones | `!T` + `?` |
| `switch` | no hay switch | `match` |
| `do`/`while` | no hay do-while | `loop` + `break` |
| `typeof`, `instanceof` | no hay reflexión | `match`/tipos estáticos |
| `eval` | no hay eval | macros/código explícito |
| `global` | no hay globales | `sigil`/`relic` o estado explícito |

### 61.6 Colisiones y reglas

1. Un identificador no puede coincidir con una palabra reservada.
2. `@` no puede ser identificador; `@mut`/`@own` solo receptores.
3. `@@` no puede iniciar un identificador; inicia un atributo.
4. `r#` no existe como raw identifier; se usa un nombre alternativo.
5. Un nombre de módulo no puede colisionar con un `rune`/`pact` del mismo scope.
6. `crate`/`super`/`Self` no pueden declararse.
7. `by`/`when`/`then` pueden ser nombres de campo/variable; el parser los
   interpreta por posición.
8. El preludio puede sombrearse; el sombreado de un tipo del preludio emite
   `PGS-W6101`, el de una función `PGS-W6102`.
9. Las palabras reservadas de Rust que no son nuestras (`async`, `await`,
   `fn`, `struct`, etc.) se rechazan para evitar confusión; el generador
   escapa identificadores Rust con `_` cuando haga falta.
10. Los nombres de variantes pueden repetirse en enums distintos; se resuelven
    por path.

### 61.7 Criterios de aceptación

- [x] Toda palabra reservada tiene categoría y efecto.
- [x] Las contextuales tienen contexto explícito.
- [x] Las prohibidas tienen reemplazo.
- [x] El preludio está separado de las palabras clave.
- [x] No hay colisiones sin regla.

[↑ Volver al índice](#indice)
