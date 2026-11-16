# PenguScript

**La especificación del lenguaje**

| Campo | Valor |
|---|---|
| Lenguaje | PenguScript |
| Versión de la spec | `1.0.0-rc.1` |
| Estado | Release candidate `1.0.0-rc.1`; 71/71 secciones completas; QA técnico y revisión adversarial completos; aprobado para implementación |
| Fecha | 2026-11-12 |
| Edición de Rust | 2024 |
| MSRV | 1.85.0 |
| Compilador de referencia | `rustc 1.99.1` (verificado en Fase 0) |
| Archivo | `docs/LANGUAGE.md` |
| Plan de trabajo | `scratch/LANGUAGE_PLAN.md` |
| QA de Fase 11 | `scratch/QA_REPORT.md` |
| Registro de decisiones | `scratch/DECISIONS.md` |

PenguScript es un lenguaje estático que compila a Rust. Su sintaxis toma la
indentación, las expresiones y la concisión de MoonScript/CoffeeScript; su
seguridad de tipos y su modelo de memoria toman las reglas de Rust, V y Kotlin.
No existen variables globales: solo constantes (`sigil`) y statics inmutables
(`relic`).

---

<a id="como-leer"></a>
## Cómo leer este documento

Este archivo es la **fuente única** de la sintaxis. Cada sección sigue la misma
plantilla: reglas normativas, sintaxis EBNF cuando hace falta, semántica,
ejemplos PenguScript, Rust generado, diagnósticos e interacciones.

- `pendiente`: la sección aún no se escribió; su alcance está en el plan.
- `borrador`: hay contenido, pero puede cambiar.
- `revisión`: el contenido está completo y espera revisión.
- `completo`: pasó el Definition of Done del Anexo B del plan.

Las palabras **DEBE**, **NO DEBE**, **DEBERÍA**, **PUEDE** y **NO ES
NECESARIO** se usan con el sentido de RFC 2119.

Los bloques de código se leen así:

| Lenguaje | Uso |
|---|---|
| `pengu` | Código PenguScript; puede ser un fragmento didáctico. |
| `rust` | Rust generado; debe compilar. |
| `ebnf` | Gramática normativa. |
| `toml` | `Tome.toml` válido. |
| `text` | Diagnósticos, árboles o tablas ilustrativas. |

Convenciones: 4 espacios por nivel; tabs prohibidos; `snake_case` para
funciones y variables; `PascalCase` para tipos.

---

<a id="indice"></a>
## Índice

**Navegación rápida**

- [Glosario rápido](#glosario-rapido)
- [Convenciones de código](#convenciones)

- [Parte I — Fundamentos](#part-1)
    - [1. Introducción y filosofía](#sec-01-introduccion)
    - [2. Estructura léxica](#sec-02-lexico)
    - [3. Estructura del programa y compilación](#sec-03-programa)
    - [4. Sistema de tipos](#sec-04-tipos)
    - [5. Variables y bindings](#sec-05-variables)
    - [6. Constantes, statics y estado global](#sec-06-constantes)
    - [7. Scope y resolución de nombres](#sec-07-scope)
    - [8. Expresiones, sentencias y bloques](#sec-08-expresiones)
- [Parte II — Núcleo del lenguaje](#part-2)
    - [9. Tipos primitivos](#sec-09-primitivos)
    - [10. Strings y chars](#sec-10-strings)
    - [11. Operadores](#sec-11-operadores)
    - [12. Booleanos y lógica](#sec-12-booleanos)
    - [13. Condicionales](#sec-13-condicionales)
    - [14. Bucles](#sec-14-bucles)
    - [15. Funciones](#sec-15-funciones)
- [Parte III — Ownership y memoria](#part-3)
    - [16. Ownership](#sec-16-ownership)
    - [17. Borrowing](#sec-17-borrowing)
    - [18. Lifetimes](#sec-18-lifetimes)
    - [19. Referencias y punteros](#sec-19-referencias)
    - [20. Smart pointers e interior mutability](#sec-20-smart-pointers)
    - [21. Memoria, Drop y layout](#sec-21-memoria)
- [Parte IV — Datos y agregados](#part-4)
    - [22. Arrays y slices](#sec-22-arrays)
    - [23. Vectores y VecDeque](#sec-23-vectores)
    - [24. Tuplas](#sec-24-tuplas)
    - [25. HashMap, HashSet, BTreeMap, BTreeSet](#sec-25-mapas)
    - [26. Otras estructuras de datos](#sec-26-estructuras-datos)
    - [27. Rangos e indexación](#sec-27-rangos)
    - [28. Structs (rune)](#sec-28-structs)
    - [29. Enums (enchanting)](#sec-29-enums)
    - [30. Pattern matching](#sec-30-pattern-matching)
    - [31. Implementaciones (ritual)](#sec-31-implementaciones)
    - [32. Type aliases, newtypes y casts (`essence`)](#sec-32-aliases-casts)
- [Parte V — Abstracción](#part-5)
    - [33. Genéricos](#sec-33-genericos)
    - [34. Constraints y where](#sec-34-constraints)
    - [35. Traits (`pact`)](#sec-35-traits)
    - [36. Associated items (types, consts, GATs)](#sec-36-associated-items)
    - [37. Higher-Ranked Items (HRTB)](#sec-37-hrtb)
    - [38. Closures](#sec-38-closures)
    - [39. Function pointers y higher-order functions](#sec-39-function-pointers)
    - [40. Operator overloading](#sec-40-operator-overloading)
- [Parte VI — Organización y metaprogramación](#part-6)
    - [41. Módulos (`scroll`)](#sec-41-modulos)
    - [42. Visibilidad (`unveil`)](#sec-42-visibilidad)
    - [43. Crates, packages y workspaces (`tome`)](#sec-43-crates)
    - [44. Atributos (`@@`)](#sec-44-atributos)
    - [45. Macros (`incantation`)](#sec-45-macros)
    - [46. Derives y traits comunes](#sec-46-derives)
    - [47. Build scripts, features y cfg](#sec-47-build-features)
- [Parte VII — Runtime avanzado](#part-7)
    - [48. Manejo de errores](#sec-48-errores)
    - [49. Iteradores](#sec-49-iteradores)
    - [50. Async/await](#sec-50-async)
    - [51. Concurrencia](#sec-51-concurrencia)
- [Parte VIII — Sistemas e interop](#part-8)
    - [52. Unsafe (curse)](#sec-52-unsafe)
    - [53. FFI e interop con Rust](#sec-53-ffi)
    - [54. Const eval](#sec-54-const-eval)
    - [55. no_std, embebidos y wasm](#sec-55-no-std)
- [Parte IX — Herramientas y calidad](#part-9)
    - [56. Testing](#sec-56-testing)
    - [57. Documentación](#sec-57-documentacion)
    - [58. Herramientas (CLI, LSP, formatter, linter)](#sec-58-herramientas)
    - [59. Guía de estilo](#sec-59-estilo)
- [Parte X — Apéndices y referencias](#part-10)
    - [60. Gramática EBNF](#sec-60-ebnf)
    - [61. Léxico y palabras clave](#sec-61-lexico-keywords)
    - [62. Precedencia y asociatividad](#sec-62-precedencia)
    - [63. Matriz de paridad Rust](#sec-63-paridad-rust)
    - [64. Desugaring](#sec-64-desugaring)
    - [65. Catálogo de diagnósticos](#sec-65-diagnosticos)
    - [66. No soportado y diferido](#sec-66-no-soportado)
    - [67. Glosario](#sec-67-glosario)
    - [68. Cookbook](#sec-68-cookbook)
    - [69. Decisiones de diseño (ADR)](#sec-69-adr)
    - [70. Changelog y versionado](#sec-70-changelog)
    - [71. Referencias](#sec-71-referencias)

---

<a id="glosario-rapido"></a>
## Glosario rápido

| Término | Significado |
|---|---|
| `bind` | Binding local inmutable. |
| `morph` | Binding local mutable. |
| `rune` | Struct. |
| `enchanting` | Enum. |
| `pact` | Trait. |
| `ritual` | Implementación inherente o de trait. |
| `sigil` | Constante de compile-time. |
| `relic` | Static inmutable. |
| `scroll` | Módulo. |
| `tome` | Paquete o crate. |
| `summon` | Importación. |
| `unveil` | Visibilidad pública. |
| `grimoire` | Bloque de entrada; compila a `fn main`. |
| `@` | Receptor: `&self`. |
| `@mut` | Receptor: `&mut self`. |
| `@own` | Receptor: `self`. |
| `@@` | Atributo. |
| `->` | Función nombrada o tipo de función. |
| `=>` | Lambda con captura. |
| `dream` / `awaken` | Async / await. |
| `curse` | Unsafe. |
| `foreign` | FFI. |
| `incantation` | Macro declarativa. |
| `do` | Bloque expresión. |
| `essence` | Alias de tipo o tipo asociado. |
| `?T` | `Option[T]`. |
| `!T` | `Result[T, Error]`. |
| `when` | Brazo de `match`. |
| `by` | Paso de un `for` numérico. |
| `chimera` | Unión (`union`). |
| `eternal` | `const fn` o bloque const. |

El glosario completo está en [§67](#sec-67-glosario).

---

<a id="convenciones"></a>
## Convenciones de código

- La indentación significativa usa **4 espacios**. Los tabs son un error léxico.
- Los bloques se introducen por indentación. `:` solo separa nombre y tipo, campo y
  valor, o clave y valor; nunca abre un bloque.
- Los comentarios de línea empiezan con `--`; los de bloque usan `--[[ ... ]]`.
- Los tipos se escriben en `PascalCase`; las funciones y variables, en
  `snake_case`.
- Los ejemplos completos viven en `scratch/examples/` durante las fases 0 y 1 y se
  moverán a `tests/golden/` cuando exista el compilador.
- Los bloques `pengu` del documento son **ejemplos didácticos**: pueden ser fragmentos (sentencias sueltas, funciones sin `grimoire`) y no siempre forman un módulo completo. La regla de no-globales se aplica a módulos completos; los ejemplos ejecutables completos están en `scratch/examples/`.
- Los errores con código se anotan como `-- ERROR PGS-Exxxx: descripción`; los ejemplos negativos sin código se explican en prosa.

---

<a id="part-1"></a>
## Parte I — Fundamentos

<a id="sec-01-introduccion"></a>
## 1. Introducción y filosofía

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 1 |
| Rust | Programa completo, items, `fn main` |
| Palabras mágicas | `grimoire`, `rune`, `enchanting`, `pact`, `ritual`, `scroll`, `summon` |
| Depende de | — |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec01_hello.pengu` |

PenguScript es un lenguaje **estático y compilado** cuya sintaxis está inspirada en
MoonScript y CoffeeScript, y cuyo modelo de tipos, memoria y seguridad toma ideas
de Rust, V y Kotlin. El compilador no interpreta el programa: lo traduce a Rust
2024 y deja que `rustc` sea la autoridad final sobre tipos, préstamos y código
máquina.

La forma del lenguaje es deliberadamente **mágica**: las declaraciones usan
sustantivos de fantasía (`rune`, `enchanting`, `pact`, `ritual`) y el flujo de
control usa verbos familiares (`if`, `for`, `while`, `match`). La magia está en
los nombres, no en las reglas. Una persona que sepa Rust debe poder leer un
programa PenguScript y predecir el Rust que produce.

### 1.1 Manifiesto

1. **La sintaxis sirve a la lectura.** La indentación, las palabras mágicas y la
   ausencia de llaves de bloque existen para que el programa se lea como una
   narración, no para ocultar lo que hace.
2. **La seguridad no es opcional.** Un programa que compila no puede tener
   variables globales mutables, `null`, conversiones implícitas ni carreras de
   datos detectables en tiempo de compilación.
3. **Todo lo que produce un valor es una expresión.** `if`, `match`, `loop`,
   bloques y funciones devuelven valores. Las únicas excepciones son las
   declaraciones (`bind`, `morph`), las asignaciones y las sentencias de control
   que divergen.
4. **El compilador es un traductor, no una máquina virtual.** PenguScript no
   tiene runtime propio, recolector de basura, metatablas ni bytecode. El
   programa generado es Rust ordinario, legible y depurable con las herramientas
   de Rust.
5. **Lo explícito gana.** La mutabilidad se declara (`bind`/`morph`), los tipos
   de los items se escriben, las conversiones se piden con `as` o `From`, y el
   estado global se declara con `sigil`/`relic` y una política de compartición.
6. **La interoperabilidad es una puerta, no una grieta.** `foreign`, `curse` y
   el bloque auditado `rust` permiten usar Rust y C cuando hace falta, pero cada
   uso queda marcado y revisable.
7. **Los errores enseñan.** Todo diagnóstico tiene un código estable, una
   explicación en español y una sugerencia de corrección cuando existe una.
8. **Cero costo por defecto.** Las abstracciones de PenguScript se bajan a
   construcciones de Rust sin envoltorios ocultos: un `rune` es un `struct`, un
   `enchanting` es un `enum`, un `pact` es un `trait`.

### 1.2 Principios de diseño

| Principio | Regla |
|---|---|
| Sin globales | No existe `bind` ni `morph` en el nivel de módulo. El estado de módulo solo puede ser `sigil` (constante) o `relic` (estático inmutable). |
| Tipado estático | Todo item declara sus tipos. Los cuerpos de funciones y los bloques locales infieren, pero nunca cambian el tipo de un item ya declarado. |
| Sin `null` | La ausencia se modela con `?T` (`Option[T]`). Un `none` no es un valor de `T`. |
| Sin truthiness | `if` exige `Bool`; no hay conversiones implícitas de enteros, strings o punteros a booleano. |
| Sin herencia de clases | La reutilización se hace con `pact` (trait), `ritual` (impl) y composición. |
| Todo es expresión | `if`, `match`, `loop`, `do` y los bloques producen valores; `bind` y la asignación son sentencias. |
| Explícito en los bordes | Las firmas de items, las conversiones, la mutabilidad y el estado global se escriben. |
| Compatible con Rust | Cada construcción tiene una traducción directa y documentada a Rust 2024. |
| Sin runtime | El binario final es un binario Rust normal; no hay `pengu_runtime` obligatorio. |
| Auditable | `curse`, `foreign` y `rust` son marcas visibles; el compilador puede listarlas y prohibirlas por configuración. |

### 1.3 Lo mágico y lo legible

La magia de PenguScript es **vocabulario**, no ambigüedad. Estas son las palabras
que un lector encuentra de inmediato:

| Palabra | Qué declara | Equivalente Rust |
|---|---|---|
| `rune` | estructura con campos | `struct` |
| `enchanting` | enumeración | `enum` |
| `pact` | contrato de comportamiento | `trait` |
| `ritual` | implementación de un `pact` o de un `rune` | `impl` |
| `essence` | alias de tipo | `type` |
| `scroll` | módulo | `mod` |
| `summon` | importación | `use` |
| `grimoire` | punto de entrada del binario | `fn main` |
| `sigil` | constante de compilación | `const` |
| `relic` | estático inmutable | `static` |
| `incantation` | macro declarativa | `macro_rules!` |

Las palabras de flujo de control (`if`, `else`, `for`, `while`, `match`, `return`)
se mantienen familiares a propósito. La magia no debe obligar a memorizar dos
vocabularios para la misma idea.

### 1.4 Lo que PenguScript no es

- No es un lenguaje interpretado ni tiene una máquina virtual.
- No es un reemplazo de Rust: es una **capa de sintaxis y verificación** sobre
  Rust 2024.
- No tiene clases, herencia, `self` como palabra clave, `null`, `undefined`,
  truthiness, metatablas, `eval` ni recolección de basura.
- No permite variables globales mutables. El estado compartido se declara con
  `relic` y una política explícita (`@@shared`, `@@thread_local`).
- No promete estabilidad de ABI entre versiones; la ABI estable se logra con
  `foreign` y `@@repr`.

### 1.5 El programa más pequeño

```pengu
grimoire
    print("hello, pengu")
```

`grimoire` declara el punto de entrada del binario. `print` es una función de la
prelude que escribe una línea en la salida estándar. La indentación de cuatro
espacios marca el cuerpo; no hay llaves de bloque.

Rust generado:

```rust
fn main() {
    println!("hello, pengu");
}
```

El ejemplo completo está en
[`scratch/examples/sec01_hello.pengu`](../scratch/examples/sec01_hello.pengu) y
su traducción en
[`scratch/examples/sec01_hello.rs`](../scratch/examples/sec01_hello.rs).

### 1.6 Un programa con un `rune`

```pengu
rune Point
    x: Float
    y: Float

grimoire
    bind p = Point(x: 3.0, y: 4.0)
    print(p.x)
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

fn main() {
    let p = Point { x: 3.0, y: 4.0 };
    println!("{}", p.x);
}
```

Este ejemplo muestra tres decisiones que se repiten en todo el documento:

1. Un `rune` se declara con campos tipados y se construye con la sintaxis
   `Point(x: ..., y: ...)`, que se traduce a un literal de struct de Rust.
2. `bind` introduce una variable inmutable; `morph` sería la forma mutable.
3. `print` recibe cualquier valor que implemente `Display`; el compilador genera
   `println!("{}", ...)`.

### 1.7 Diagnósticos de esta sección

Esta sección no introduce diagnósticos propios. Los errores de programa se
definen en §3 (entrada y módulos), §5 (bindings) y §6 (estado global).

### 1.8 Criterios de aceptación

- [x] El manifiesto fija las prioridades del lenguaje.
- [x] La tabla de palabras mágicas coincide con el lexicón de §4.6 y con
      `scratch/DECISIONS.md`.
- [x] El ejemplo mínimo y el ejemplo con `rune` tienen Rust compilable.
- [x] Se declara explícitamente que no hay variables globales, clases, `null`,
      truthiness ni runtime.
- [x] Se explica la relación con Rust 2024 y con MoonScript/CoffeeScript.

[↑ Volver al índice](#indice)

<a id="sec-02-lexico"></a>
## 2. Estructura léxica

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 1 |
| Rust | Literales, comentarios, identificadores, `HashMap` |
| Palabras mágicas | `true`, `false`, `none` |
| Depende de | — |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec02_literals.pengu` |

Esta sección define qué es un archivo PenguScript válido **antes** de construir el
AST: codificación, saltos de línea, indentación, comentarios, identificadores y
literales. El lexer produce una secuencia de tokens con marcas `INDENT`, `DEDENT`
y `NEWLINE`; el parser consume esa secuencia.

### 2.1 Archivos y codificación

| Regla | Norma |
|---|---|
| Codificación | UTF-8 sin BOM. Un BOM al inicio es un error (`PGS-E1001`). |
| Saltos de línea | `LF` (`U+000A`) o `CRLF` (`U+000D U+000A`). El lexer normaliza `CRLF` a `LF`. Un `CR` suelto es error (`PGS-E1002`). |
| Extensión | Los archivos fuente usan `.pengu`. Otros archivos no se compilan como PenguScript. |
| Última línea | Puede terminar o no en salto de línea; el lexer inserta uno lógico al final. |
| Contenido | Se permiten caracteres Unicode en strings, comentarios e identificadores según §2.4. |

No hay `#!` ni shebang. Un archivo que empiece por `#!` se trata como texto
ordinario y producirá un error de token.

### 2.2 Indentación y bloques

PenguScript usa **indentación significativa**. No hay llaves `{}` para delimitar
bloques; `{` y `}` se reservan para mapas y para el bloque auditado `rust`.

1. Cada nivel de indentación son **cuatro espacios**. Se prohíben tabuladores
   fuera de strings y comentarios (`PGS-E1003`).
2. Las líneas en blanco y las líneas que solo contienen un comentario no alteran
   la pila de indentación.
3. Al primer token de una línea lógica, el lexer compara la cantidad de espacios
   con la cima de la pila:
   - más espacios: emite `INDENT`; el aumento debe ser un múltiplo de cuatro
     (`PGS-E1005`);
   - los mismos espacios: no emite nada;
   - menos espacios: emite un `DEDENT` por cada nivel cerrado; si la columna no
     coincide con ningún nivel abierto, es error (`PGS-E1004`).
4. Un `INDENT` solo es válido si la construcción anterior espera un bloque. Un
   `INDENT` inesperado es error (`PGS-E1005`).
5. Si una construcción exige un bloque y la línea siguiente no está indentada,
   es error (`PGS-E1006`).
6. Los bloques se cierran con `DEDENT`. El final del archivo cierra todos los
   niveles abiertos.

Ejemplo de niveles válidos:

```pengu
grimoire
    bind x = 1
    if x > 0
        print("positivo")
    print("fin")
```

La columna 0 abre el cuerpo de `grimoire` en el nivel 1; la línea de `if` abre el
nivel 2; `print("fin")` vuelve al nivel 1 con un `DEDENT`.

#### Continuación de línea

La indentación no se procesa dentro de `()`, `[]` ni `{}`. Un salto de línea en
esos contextos es espacio en blanco. Fuera de ellos, una barra invertida (`\`) al
final de la línea continúa la línea lógica:

```pengu
bind total = 1 + \
    2 + 3
```

La barra invertida no puede ir seguida de espacios antes del salto de línea.

#### Dos puntos y punto y coma

- `:` separa un nombre de su tipo (`x: Int`), un campo de su valor
  (`Point(x: 1)`) o una clave de un valor en un mapa (`{ "a": 1 }`). **No** abre
  un bloque.
- `;` separa sentencias en la misma línea. Es opcional al final de una línea.
  Dos `;` consecutivos producen una sentencia vacía, que se ignora.

### 2.3 Comentarios

| Forma | Uso | Se conserva |
|---|---|---|
| `-- texto` | comentario de línea | no |
| `--[[ texto ]]` | comentario de bloque | no |
| `--- texto` | documentación del siguiente item | sí, como doc del item |
| `--! texto` | documentación del item que lo contiene | sí, como doc interno |

Reglas:

- `--` inicia un comentario hasta el final de la línea.
- `--[[` inicia un comentario de bloque que termina en el primer `]]`. No se
  anidan; un `--[[` dentro se trata como texto.
- `---` debe aparecer al inicio de una línea lógica (tras la indentación) y
  documenta el item siguiente. Varias líneas `---` consecutivas se acumulan.
- `--!` debe aparecer dentro de un item y documenta el item contenedor (por
  ejemplo, un `scroll` o un `ritual`).
- Los comentarios no producen tokens, salvo que sean comentarios de
  documentación, que se adjuntan al AST como atributos `doc`.
- Un comentario de bloque sin cerrar es error (`PGS-E1007`).

### 2.4 Identificadores y palabras reservadas

Un identificador cumple `XID_Start` seguido de cero o más `XID_Continue`, o
empieza por `_` seguido de al menos un carácter `XID_Continue`. El identificador
`_` por sí solo es el patrón comodín, no un nombre. Los identificadores distinguen
mayúsculas y minúsculas y no se pueden escapar.

La lista normativa de **palabras reservadas**, **contextuales** y del **preludio** está en §61.2–§61.4. No se duplica aquí para evitar divergencias.

`spirit` y `spell` están retirados. Si aparecen, el compilador sugiere `@` y
`->`, respectivamente (`PGS-E1010`); solo se reconocen para producir ese
diagnóstico de migración y no son parte de la gramática vigente.

### 2.5 Literales

#### Booleanos y ausencia

```pengu
true
false
none
```

`true` y `false` tienen tipo `Bool`. `none` es el constructor de `?T`
(`Option[T]`) y requiere contexto para inferir `T`.

#### Enteros

| Forma | Ejemplo | Rust |
|---|---|---|
| Decimal | `42`, `1_000_000` | `42`, `1_000_000` |
| Hexadecimal | `0xFF`, `0xdead_beef` | igual |
| Octal | `0o755` | igual |
| Binario | `0b1010_0101` | igual |
| Con sufijo | `42_i32`, `255_u8`, `1_000_usize` | `42i32`, `255u8`, `1_000usize` |

Reglas:

- Los guiones bajos solo aparecen entre dígitos; `_42`, `42_` y `4__2` son
  errores (`PGS-E1009`).
- Un entero decimal no lleva ceros a la izquierda, salvo el propio `0`.
- Los sufijos válidos son `_i8`, `_i16`, `_i32`, `_i64`, `_i128`, `_isize`,
  `_u8`, `_u16`, `_u32`, `_u64`, `_u128`, `_usize`.
- Sin sufijo, el tipo se infiere; si no hay contexto, se usa `Int` (`i32`).

#### Flotantes

| Forma | Ejemplo |
|---|---|
| Decimal | `3.14`, `0.5`, `1_000.25` |
| Exponente | `1e10`, `2.5e-3`, `1.0E+6` |
| Con sufijo | `3.0_f64`, `1.5_f32` |

Un flotante necesita un punto con al menos un dígito a cada lado, o un exponente.
`1.` y `.5` no son válidos; se escriben `1.0` y `0.5`. Los sufijos válidos son
`_f32` y `_f64`; sin sufijo se infiere `Float` (`f64`).

#### Caracteres

```pengu
'a'
'\n'
'\u{1F427}'
b'a'
```

Un `char` representa un escalar Unicode y se escribe entre comillas simples. Las
secuencias de escape son `\n`, `\r`, `\t`, `\\`, `\'`, `\"`, `\0`, `\xNN` y
`\u{...}`. Un `byte char` (`b'a'`) tiene tipo `U8`; el carácter directo debe ser ASCII, mientras que `\xNN` admite `0x00`–`0xFF`.

#### Strings

| Forma | Ejemplo | Interpolación |
|---|---|---|
| Normal | `"hola"` | sí, `#{expr}` |
| Triple | `"""línea 1\nlínea 2"""` | sí |
| Raw | `r"sin \escapes"` | no |
| Raw con almohadilla | `r#"puede contener "comillas""#` | no |
| Byte | `b"bytes"` | no |
| C | `c"cadena C"` | no |

- Un string normal admite escapes y interpolación. `#{expr}` evalúa `expr` y
  concatena su representación `Display`; para emitir `#{` literal se escribe
  `\#{`.
- Un string triple puede contener saltos de línea y comillas simples, pero no
  tres comillas consecutivas sin escapar.
- Un string raw no procesa escapes ni interpolación. `r#"..."#` permite incluir
  `"` sin cerrar el literal.
- Un string byte produce `&[u8; N]`; un string C produce `&CStr` y exige que no
  haya `\0` interior.
- Un string normal sin contexto es `&Str` (`&str`). Para obtener `String` se usa
  `String.from(...)` o una anotación explícita.

### 2.6 Colecciones literales

#### Arrays

```pengu
[]
[1, 2, 3]
[0; 4]
[1, 2, 3,]
```

- `[a, b, c]` es un array de longitud fija; su tipo es `[T; N]`.
- `[expr; N]` repite `expr` `N` veces; `N` debe ser una constante evaluable.
- La coma final es opcional.
- `[]` requiere contexto de tipo; sin él, el compilador no puede inferir `T`.

#### Mapas

```pengu
{ "a": 1, "b": 2 }
{ 1: "uno", 2: "dos" }
{}
```

- `{ k: v }` construye un `HashMap[K, V]`; las claves deben implementar `Eq` y
  `Hash`.
- `{}` requiere contexto de tipo.
- La coma final es opcional.
- `{` y `}` **no** delimitan bloques de código.

#### Tuplas

```pengu
()
(1,)
(1, "uno")
```

- `()` es el valor unitario, tipo `Unit`.
- `(x,)` es una tupla de un elemento; la coma es obligatoria.
- `(x)` es agrupación, no una tupla.
- `(a, b)` es una tupla de dos elementos.

#### Vectores

```pengu
Vec[]
Vec[1, 2, 3]
Vec[0; 4]
```

- `Vec[a, b, c]` construye un `Vec[T]`; se genera `vec![a, b, c]`.
- `Vec[expr; N]` repite `expr` `N` veces; se genera `vec![expr; N]`.
- `Vec[]` requiere contexto de tipo, igual que `[]`.
- `Vec` es el constructor de literal; `Vec[T]` en posición de tipo sigue siendo
  el tipo vector.

#### Sets

```pengu
Set[]
Set["magic", "static"]
```

- `Set[a, b, c]` construye un `HashSet[T]`; se genera
  `HashSet::from([a, b, c])`.
- `Set[]` requiere contexto de tipo.
- `Set[T]` exige `T: Eq + Hash`.
- Para un `BTreeSet[T]` se usa `BTreeSet.from([...])` (§25); el literal `Set[...]`
  siempre es `HashSet`.

#### Forma indentada sin delimitadores (estilo MoonScript)

Cuando una colección es el valor completo de un `bind`, un `morph` o un
`return`, se puede escribir **sin `[]` ni `{}`**: la indentación delimita el
cuerpo. La línea del `=` (o del `return`) termina, el cuerpo va un nivel más
indentado y el `DEDENT` cierra la colección.

```pengu
bind numbers =
    1
    2
    3

bind config =
    name: "PenguScript"
    kind: "language"

bind words = Vec
    "pingüino"
    "pengu"

bind tags = Set
    "magic"
    "static"
```

Rust generado:

```rust
use std::collections::{HashMap, HashSet};

fn main() {
    let numbers = [1, 2, 3];

    let config: HashMap<&str, &str> = HashMap::from([
        ("name", "PenguScript"),
        ("kind", "language"),
    ]);

    let words = vec!["pingüino", "pengu"];
    let tags = HashSet::from(["magic", "static"]);

    println!("{} {} {}", numbers.len(), config.len(), words.len() + tags.len());
}
```

Reglas:

1. **Contexto.** La forma sin delimitadores solo se reconoce cuando el `=`
   (de `bind`/`morph`), un `return` o el `:` de una entrada de mapa es el último
   token de la línea y la línea siguiente está indentada. En cualquier otro
   contexto se usa la forma inline.
2. **Cuerpo.** El cuerpo se indenta exactamente un nivel (cuatro espacios) más
   que la línea del `=`/`return`. El `DEDENT` lo cierra; no hay token de cierre.
3. **Array o mapa.** Si todas las líneas del cuerpo son entradas `clave: valor`,
   la colección es un mapa. Si son expresiones, es un array. Mezclar ambos
   estilos en el mismo cuerpo es error (`PGS-E1011`).
4. **Entradas de mapa.** `name: "x"` usa la clave string `"name"`; también se
   admiten claves literales (`1: "uno"`, `"a": 2`) y calculadas
   (`[expr]: valor`). Los corchetes de una clave calculada no son el delimitador
   de la colección.
5. **Mapa anidado.** Una entrada `clave:` sin valor inline puede abrir otra
   colección indentada un nivel más:

   ```pengu
   bind server =
       host: "localhost"
       ports:
           80
           443
       tls:
           enabled: true
           cert: "server.pem"
   ```

   `ports` es un array de dos enteros; `tls` es un mapa. La clasificación se
   repite en cada cuerpo.
6. **`Vec` y `Set`.** `Vec` al final de la línea abre un vector; `Set` abre un
   set. Su cuerpo es siempre una secuencia de expresiones (nunca un mapa):
   `bind v = Vec` + cuerpo, o `bind s = Set` + cuerpo. La forma inline
   `Vec[...]`/`Set[...]` sigue siendo válida.
7. **Anidamiento.** Un array indentado no puede contener otro array indentado
   como elemento, porque no habría forma de separar sus cuerpos. Para eso se usa
   la forma inline: `[[1, 2], [3, 4]]`, o cada fila inline dentro de un array
   indentado:

   ```pengu
   bind matrix =
       [1, 2]
       [3, 4]
   ```

8. **Tuplas.** Las tuplas conservan `()`; sin paréntesis serían indistinguibles
   de un array. La forma indentada de tupla sigue siendo
   `(` + cuerpo + `)`.
9. **Vacío.** Un cuerpo vacío no es válido (`PGS-E1012`). Para una colección
   vacía se usa `[]`, `{}`, `Vec[]` o `Set[]`.
10. **Bloques.** Un bloque de expresiones no se escribe con indentación desnuda
    después de `=`: se usa `do` (§8). Así `bind x =` + cuerpo es siempre una
    colección, no un bloque.
11. **Comas.** Cada línea del cuerpo es un elemento; la coma final de línea es
    opcional y se ignora. No se necesitan comas entre líneas.
12. **Equivalencia.** La forma sin delimitadores y la inline producen el mismo
    tipo, el mismo orden y el mismo Rust.

**Slices.** No hay literal de slice: se obtiene de un array o `Vec` con
`&xs[..]`/`&xs[a..b]` (§22) y no usa indentación.

La forma indentada es **opcional**: la forma inline sigue siendo la única
válida dentro de paréntesis, llamadas y expresiones que no sean el valor
completo de un `=`/`return`.

#### Rangos (adelanto de §27)

```pengu
1..10
1..=10
1..
    10
```

- `a..b` es un rango exclusivo; `a..=b` es inclusivo.
- El fin puede ir en una línea indentada después de `..`/`..=`.
- Los rangos no son colecciones: no asignan memoria.

### 2.7 Separadores y líneas lógicas

| Token | Función |
|---|---|
| `NEWLINE` | termina una sentencia o una línea lógica |
| `;` | separa sentencias en la misma línea; opcional al final |
| `,` | separa elementos de listas, parámetros y campos |
| `:` | separa nombre y tipo, campo y valor, clave y valor |
| `->` | introduce el tipo de retorno de una función nombrada o un tipo función |
| `=>` | introduce el cuerpo de una lambda |

Un `NEWLINE` se emite al final de una línea lógica y no dentro de `()`, `[]`,
`{}` en su forma inline. En la forma indentada sin delimitadores de §2.6, el
`NEWLINE` separa elementos y el `DEDENT` cierra la colección. El fin de un rango
puede ir tras un `NEWLINE` indentado después de `..`/`..=`. Una continuación con
`\` también suprime el `NEWLINE`. Los comentarios de línea no impiden el
`NEWLINE`.

### 2.8 Gramática léxica

```ebnf
source          ::= { logical_line } EOF
logical_line    ::= indent? token { token } newline
indent          ::= INDENT | DEDENT
token           ::= identifier | keyword | literal | operator | delimiter
identifier      ::= XID_START { XID_CONTINUE } | "_" XID_CONTINUE { XID_CONTINUE }
literal         ::= "true" | "false" | "none" | integer | float | char | string | byte_char
integer         ::= decimal | hex | octal | binary
decimal         ::= DIGIT { DIGIT | "_" } [ int_suffix ]
hex             ::= "0x" HEX_DIGIT { HEX_DIGIT | "_" }
octal           ::= "0o" OCT_DIGIT { OCT_DIGIT | "_" }
binary          ::= "0b" BIN_DIGIT { BIN_DIGIT | "_" }
int_suffix      ::= "_" ( "i8" | "i16" | "i32" | "i64" | "i128" | "isize"
                        | "u8" | "u16" | "u32" | "u64" | "u128" | "usize" )
float           ::= DIGIT { DIGIT | "_" } "." DIGIT { DIGIT | "_" }
                    [ exponent ] [ float_suffix ]
                  | DIGIT { DIGIT | "_" } exponent [ float_suffix ]
exponent        ::= ("e" | "E") ["+" | "-"] DIGIT { DIGIT }
float_suffix    ::= "_f32" | "_f64"
string          ::= '"' { string_char | interpolation } '"'
                  | '"""' { any_char } '"""'
                  | 'r"' { raw_char } '"'
                  | 'r#"' { raw_char } '"#'
                  | 'b"' { string_char } '"'
                  | 'c"' { string_char } '"'
char            ::= "'" ( char_content | escape ) "'"
byte_char       ::= "b" "'" ( ascii_char | byte_escape ) "'"
char_content    ::= (* cualquier escalar Unicode distinto de "'", "\\" y saltos de línea *)
ascii_char      ::= (* ASCII distinto de "'", "\\" y saltos de línea *)
string_char     ::= (* cualquier escalar Unicode distinto de '"', "\\" y saltos de línea *)
raw_char        ::= (* cualquier escalar Unicode distinto de '"' *)
any_char        ::= (* cualquier escalar Unicode *)
escape          ::= "\\" ( "n" | "r" | "t" | "0" | "\\" | '"' | "'"
                          | "x" HEX_DIGIT HEX_DIGIT | "u{" HEX_DIGIT+ "}" )
byte_escape     ::= "\\" ( "n" | "r" | "t" | "0" | "\\" | '"' | "'"
                          | "x" HEX_DIGIT HEX_DIGIT )
interpolation   ::= "#{" expression "}"
array           ::= inline_array | indented_collection
inline_array    ::= "[" [ expression { "," expression } [","] ] "]"
                  | "[" expression ";" const_expr "]"
const_expr      ::= expression
vector          ::= "Vec" ( inline_array | indented_collection )
set             ::= "Set" ( inline_array | indented_collection )
map             ::= inline_map | indented_collection
inline_map      ::= "{" [ map_entry { "," map_entry } [","] ] "}"
indented_collection ::= NEWLINE INDENT ( map_body | seq_body ) DEDENT
map_body        ::= map_entry { NEWLINE map_entry }
seq_body        ::= expression { NEWLINE [","] expression } [","]
map_entry       ::= (identifier | expression) ":"
                    ( expression | indented_collection )
tuple           ::= "(" ")" | "(" expression "," ")"
                  | "(" expression "," expression { "," expression } [","] ")"
                  | "(" NEWLINE INDENT { expression [","] NEWLINE } DEDENT ")"
range           ::= expression (".." | "..=") expression
                  | expression (".." | "..=") NEWLINE INDENT expression DEDENT
```

La gramática de `expression` se define en §60.7; la de items, en §60.2. El parser
decide si un `indented_collection` es array o mapa según `map_body`/`seq_body`;
el lexer solo produce tokens y marcas de indentación.

### 2.9 Ejemplo ejecutable

```pengu
grimoire
    bind hex = 0xFF
    bind big = 1_000_000
    bind ratio = 1.5
    bind letter = 'P'
    bind greeting = "hello"
    bind pair = (1, "one")
    bind numbers =
        1
        2
        3
    bind table =
        name: "pengu"
        version: 1
    bind words = Vec
        "magic"
        "static"
    bind maybe: ?Int = none
    print(greeting)
```

Rust generado:

```rust
use std::collections::HashMap;

fn main() {
    let hex = 0xFF;
    let big = 1_000_000;
    let ratio = 1.5;
    let letter = 'P';
    let greeting = "hello";
    let pair = (1, "one");
    let numbers = [1, 2, 3];
    let table: HashMap<&str, i32> = HashMap::from([("name", 1), ("version", 2)]);
    let words = vec!["magic", "static"];
    let maybe: Option<i32> = None;
    println!("{}", greeting);
}
```

El ejemplo completo está en
[`scratch/examples/sec02_literals.pengu`](../scratch/examples/sec02_literals.pengu)
y su traducción en
[`scratch/examples/sec02_literals.rs`](../scratch/examples/sec02_literals.rs).

### 2.10 Diagnósticos

| Código | Condición | Sugerencia |
|---|---|---|
| `PGS-E1001` | BOM al inicio del archivo | guardar sin BOM |
| `PGS-E1002` | `CR` suelto o salto no válido | usar `LF` o `CRLF` |
| `PGS-E1003` | tabulador fuera de string/comentario | reemplazar por cuatro espacios |
| `PGS-E1004` | `DEDENT` sin nivel coincidente | alinear con un nivel abierto |
| `PGS-E1005` | `INDENT` inesperado o aumento no múltiplo de cuatro | eliminar la indentación, abrir un bloque o usar 4 espacios |
| `PGS-E1006` | falta el bloque esperado | indentar el cuerpo con cuatro espacios |
| `PGS-E1007` | comentario o string sin cerrar | cerrar `]]`, `"` o `"""` |
| `PGS-E1008` | escape inválido | usar un escape de §2.5 |
| `PGS-E1009` | literal inválido | revisar dígitos, sufijo o separador |
| `PGS-E1010` | `spell`/`spirit` retirados | usar `->` o `@` |
| `PGS-E1011` | cuerpo indentado mezcla entradas de mapa y expresiones | elegir mapa o array |
| `PGS-E1012` | cuerpo indentado vacío | usar `[]`, `{}`, `Vec[]` o `Set[]` |

### 2.11 Interacciones y criterios de aceptación

- [x] Toda la sintaxis de ejemplo del plan se puede tokenizar con esta sección.
- [x] La indentación se describe con `INDENT`/`DEDENT` y errores concretos.
- [x] Los literales cubren booleanos, `none`, enteros, flotantes, caracteres,
      strings, arrays, vectores, sets, mapas, tuplas, rangos y sus formas
      indentadas sin delimitadores.
- [x] Los comentarios de documentación se distinguen de los ordinarios.
- [x] `spell` y `spirit` retirados solo aparecen como errores de migración.
- [x] No hay tabuladores en ningún ejemplo.

[↑ Volver al índice](#indice)

<a id="sec-03-programa"></a>
## 3. Estructura del programa y compilación

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 1 |
| Rust | `mod`, `use`, `pub`, `fn main`, `Cargo.toml`, `build.rs` |
| Palabras mágicas | `scroll`, `summon`, `unveil`, `grimoire` |
| Depende de | §2 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec03_program.pengu` |

Un **tome** es la unidad de compilación: un paquete con un `Tome.toml`, uno o más
archivos `.pengu` y un grafo de módulos. El compilador `pengu` transforma el tome
en un paquete Cargo ordinario y llama a `cargo`/`rustc` para producir el binario o
la biblioteca final.

### 3.1 Archivos, raíces y tomos

| Elemento | Convención |
|---|---|
| Manifiesto | `Tome.toml` en la raíz del tome. |
| Raíz de binario | `src/main.pengu`, con un bloque `grimoire`. |
| Raíz de biblioteca | `src/lib.pengu`, sin `grimoire`. |
| Módulo | `scroll nombre` en un archivo `nombre.pengu`, o `scroll nombre` con cuerpo inline. |
| Submódulo | `scroll nombre` dentro de otro módulo busca `nombre.pengu` o `nombre/mod.pengu` junto al archivo padre. |
| Extensión | Solo `.pengu`; los archivos `.rs` generados viven en `target/pengu/`. |
| Un tome, un crate | Cada tome genera exactamente un crate de Cargo. Varios binarios se declaran con `[[bin]]` en `Tome.toml`. |

Un tome puede declarar varias metas (`lib`, `bin`, `test`, `bench`, `example`).
Cada meta tiene su propia raíz y su propio `grimoire` si es un binario. El nombre
del crate se deriva de `[tome].name`; los guiones se convierten en guiones bajos
para el identificador de Rust.

### 3.2 Items de módulo

En el nivel de módulo solo se permiten **items**. Una sentencia suelta (`print`,
una asignación, un `if`) es error (`PGS-E1203`). La lista completa:

| Item | Sintaxis | Rust |
|---|---|---|
| `rune` | `rune Point` + campos | `struct` |
| `enchanting` | `enchanting Shape` + variantes | `enum` |
| `pact` | `pact Drawable` + firmas | `trait` |
| `ritual` | `ritual Point` + métodos | `impl` |
| `essence` | `essence Meters = Float` | `type` |
| `sigil` | `sigil MAX: Int = 10` | `const` |
| `relic` | `relic NAME: &'static Str = "x"` | `static` |
| `scroll` | `scroll geometry` | `mod` |
| `summon` | `summon std::fmt` | `use` |
| `unveil` | `unveil rune Point` | `pub` |
| función | `new = (x: Float) -> Point` | `fn new(...)` |
| `incantation` | `incantation nombre` | `macro_rules!` |
| `foreign` | `foreign "C"` + firmas | `extern "C"` |
| `chimera` | `chimera Bits` + campos | `union` |
| `grimoire` | `grimoire` + bloque | `fn main` |
| `rust` | `rust` + bloque | código Rust auditado |

Reglas:

1. `bind` y `morph` **no** son items de módulo; si aparecen en la columna 0, el
   compilador emite `PGS-E1203` con la sugerencia de moverlos dentro de una
   función. Esta es la regla de “sin variables globales”.
2. Una definición de función en el nivel de módulo (`name = (...) -> T`) es un
   item, no una variable global: no captura el entorno y se puede llamar desde
   cualquier módulo que la importe.
3. Los items son visibles en todo el módulo, sin importar el orden de
   declaración. Las variables locales, en cambio, se ven solo después de su
   declaración (§7).
4. `grimoire` solo aparece en la raíz de un binario. Un `lib.pengu` que lo
   contiene es error (`PGS-E1201`).

### 3.3 Módulos con `scroll`

Un módulo de archivo:

```pengu
scroll geometry
```

El compilador busca `geometry.pengu` junto al archivo actual. Si no existe,
busca `geometry/mod.pengu`. Si el archivo no existe, error (`PGS-E1204`).

Un módulo inline:

```pengu
scroll geometry
    rune Point
        x: Float
        y: Float

    length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()
```

La diferencia es sintáctica: si la línea siguiente a `scroll nombre` está
indentada, el cuerpo es inline; si no, es un módulo de archivo. No se permite
mezclar ambas formas para el mismo nombre en el mismo módulo (`PGS-E1205`).

Un `scroll` de archivo puede declarar sus propios `summon`, items y submódulos.
El nombre del módulo debe coincidir con el nombre del archivo o directorio; si no,
error (`PGS-E1205`).

### 3.4 Importaciones con `summon`

```pengu
summon std::fmt
summon std::collections::{HashMap, HashSet}
summon crate::geometry::Point
summon crate::geometry::*
summon std::fmt as fmt
```

- `summon` equivale a `use` de Rust y se permite en el nivel de módulo y dentro de
  bloques (import local).
- Las rutas usan `::`. No existe el prefijo `self::`; para el módulo actual se
  usa el nombre sin prefijo, para el padre `super::`, para la raíz `crate::`.
- Un `*` importa todos los nombres públicos del módulo. Dos globs que introducen
  el mismo nombre producen ambigüedad (`PGS-E1206`); una importación explícita
  gana sobre un glob.
- Una importación no usada produce un warning, no un error.
- Los nombres de la prelude (`print`, `Vec`, `Option`, `Result`, …) no necesitan
  `summon`, pero se pueden importar explícitamente para desambiguar.

### 3.5 Visibilidad con `unveil`

Por defecto, todo item es privado de su módulo. `unveil` lo hace público:

```pengu
unveil rune Point
unveil new = (x: Float, y: Float) -> Point
    Point(x: x, y: y)
```

Formas restringidas:

| Forma | Efecto | Rust |
|---|---|---|
| `unveil` | visible desde cualquier crate | `pub` |
| `unveil(tome)` | visible en todo el tome | `pub(crate)` |
| `unveil(scroll)` | visible en el módulo padre | `pub(super)` |

`unveil(parent)` y `unveil(in path)` se definen en §42. `unveil` no se aplica a
`ritual` (Rust no permite `pub impl`), a variables locales ni a campos: la
visibilidad de campos y variantes se trata en §28 y §29.

### 3.6 El punto de entrada `grimoire`

```pengu
grimoire
    print("hello")
```

`grimoire` declara `fn main()` y debe ser el único de su binario (`PGS-E1202`).
No recibe parámetros ni genéricos. Su cuerpo es un bloque normal; el valor final
se descarta y el tipo del bloque debe ser `Unit`. Para un `main` que devuelve un
código de salida o un `Result`, se usa `grimoire: !Unit`; esa forma se define en
§15 y §48.

### 3.7 `Tome.toml`

El manifiesto mínimo:

```toml
[tome]
name = "hello"
version = "0.1.0"
pengu = "1.0"
edition = "2024"
rust-version = "1.85"

[[bin]]
name = "hello"
path = "src/main.pengu"
```

- `[tome]` es obligatorio y contiene `name`, `version`, `pengu`, `edition` y
  `rust-version`.
- `[dependencies]`, `[dev-dependencies]` y `[build-dependencies]` usan el mismo
  formato que Cargo.
- `[[bin]]`, `[[test]]`, `[[bench]]` y `[[example]]` apuntan a archivos `.pengu`.
- `[lib]` declara la biblioteca; su `path` por defecto es `src/lib.pengu`.
- `[cargo]` es una tabla de paso directo a `Cargo.toml`; el compilador protege las
  claves que controla (`package`, `edition`, `rust-version`, `targets`).
- `Tome.lock` se genera y se versiona según §58.

El esquema completo, con todas las claves y sus valores por defecto, está en
`scratch/DECISIONS.md` (decisión D17). Este documento no duplica ese esquema.

### 3.8 Pipeline de compilación

| Etapa | Entrada | Salida | Errores |
|---|---|---|---|
| Lexer | fuente UTF-8 | tokens + `INDENT`/`DEDENT` | `PGS-E1xxx` |
| Parser | tokens | AST | `PGS-E2xxx` |
| Resolución | AST | AST resuelto | `PGS-E5xxx` |
| Type check | AST resuelto | AST tipado | `PGS-E3xxx` |
| Lowering | AST tipado | Rust AST + source map | `PGS-E7xxx` |
| Codegen | Rust AST | `target/pengu/src/*.rs` | `PGS-E7xxx` |
| Cargo | paquete generado | binario/lib | errores de `rustc` remapeados |

El compilador **no reimplementa** el borrow checker: genera Rust y deja que
`rustc` valide préstamos, lifetimes y traits. Los diagnósticos de `rustc` se
remapean a la posición del fuente `.pengu` usando `sourcemap.json`.

### 3.9 Artefactos y contrato de codegen

La compilación escribe en `target/pengu/`:

```text
target/pengu/
├── Cargo.toml
├── Cargo.lock
├── build.rs
├── src/
│   ├── main.rs
│   ├── lib.rs
│   └── geometry.rs
└── sourcemap.json
```

- `main.pengu` -> `src/main.rs`; `lib.pengu` -> `src/lib.rs`.
- Cada `scroll` de archivo `x.pengu` -> `src/x.rs`; los submódulos se aplanan con
  nombres estables.
- Los nombres PenguScript se convierten a `snake_case` para funciones y módulos, y
  a `PascalCase` para tipos. Las palabras reservadas de Rust se escapan con un
  sufijo `_`.
- No se emite `#![allow(...)]` global. Los warnings se conservan.
- El Rust generado se formatea con `rustfmt --edition 2024`.
- Los bloques `rust` se copian literalmente y se marcan en el source map.

Esquema mínimo de `sourcemap.json`:

```json
{
  "version": 1,
  "files": [
    {
      "generated": "src/main.rs",
      "source": "src/main.pengu",
      "mappings": [
        {
          "generated_line": 6,
          "generated_column": 5,
          "source_line": 2,
          "source_column": 5
        }
      ]
    }
  ]
}
```

`generated` es relativo a `target/pengu/`; `source` es relativo a la raíz del
tome. Las columnas son 1-based.

### 3.10 Ejemplo ejecutable

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    new = (x: Float, y: Float) -> Point
        Point(x: x, y: y)

    length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

grimoire
    bind p = Point.new(3.0, 4.0)
    print(p.length())
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn new(x: f64, y: f64) -> Point {
        Point { x, y }
    }

    fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }
}

fn main() {
    let p = Point::new(3.0, 4.0);
    println!("{}", p.length());
}
```

El ejemplo completo está en
[`scratch/examples/sec03_program.pengu`](../scratch/examples/sec03_program.pengu)
y su traducción en
[`scratch/examples/sec03_program.rs`](../scratch/examples/sec03_program.rs).

### 3.11 Diagnósticos

| Código | Condición | Sugerencia |
|---|---|---|
| `PGS-E1201` | `grimoire` en una biblioteca | moverlo a `main.pengu` |
| `PGS-E1202` | más de un `grimoire` en un binario | dejar uno |
| `PGS-E1203` | sentencia o `bind` en nivel de módulo | mover dentro de una función |
| `PGS-E1204` | no se encuentra el archivo del `scroll` | crear el archivo o usar cuerpo inline |
| `PGS-E1205` | módulo duplicado o nombre no coincide | alinear archivo y declaración |
| `PGS-E1206` | importación ambigua o no resuelta | usar una ruta explícita |
| `PGS-E1207` | item privado usado desde otro módulo | añadir `unveil` |
| `PGS-E1208` | `Tome.toml` inválido | revisar §3.7 y D17 |
| `PGS-E1209` | meta sin raíz `.pengu` | declarar `path` |
| `PGS-E1210` | source map inconsistente | reportar un bug del compilador |

### 3.12 Criterios de aceptación

- [x] Se distingue binario, biblioteca, módulo y tome.
- [x] `scroll`, `summon`, `unveil` y `grimoire` tienen sintaxis y semántica.
- [x] La regla de “sin variables globales” se aplica en el nivel de módulo.
- [x] El pipeline y los artefactos de codegen están definidos.
- [x] El ejemplo tiene Rust compilable y produce `5`.
- [x] Los diagnósticos de entrada, módulos y manifiesto tienen códigos.

[↑ Volver al índice](#indice)

<a id="sec-04-tipos"></a>
## 4. Sistema de tipos

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 1 |
| Rust | Tipos primitivos, `struct`, `enum`, `trait`, `type`, referencias, genéricos |
| Palabras mágicas | `rune`, `enchanting`, `pact`, `essence` |
| Depende de | §2 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec04_types.pengu` |

El sistema de tipos de PenguScript es **estático, fuerte y nominal**. Un tipo es
una promesa que el compilador verifica antes de generar Rust; `rustc` vuelve a
verificarla sobre el código generado. No hay `null`, truthiness, coerción
implícita ni tipos que aparezcan por accidente.

### 4.1 Reglas generales

1. **Estático.** Todo programa que compila tiene todos sus tipos resueltos en
   tiempo de compilación.
2. **Fuerte.** No hay conversiones implícitas entre enteros, flotantes, strings,
   punteros ni booleanos. Una conversión se escribe con `as` o con `From`/`Into`.
3. **Nominal.** Dos `rune` con los mismos campos son tipos distintos. Dos
   `enchanting` con las mismas variantes son tipos distintos. Los alias
   (`essence`) son transparentes.
4. **Inferencia local.** Los cuerpos de funciones y los bloques infieren tipos
   locales con un algoritmo bidireccional. Las firmas de items son explícitas.
5. **Sin `null`.** La ausencia es `?T` (`Option[T]`); el error es `!T`
   (`Result[T, Error]`). `none` no es un valor de `T`.
6. **Sin truthiness.** `if` y `while` exigen `Bool`. `0`, `""` y los punteros no
   son booleanos.
7. **Propiedad y préstamo.** Todo valor tiene un dueño; las referencias
   (`&T`, `&mut T`) prestan sin transferir. Las reglas completas están en §16–§18.
8. **Coherencia.** Un `ritual` solo puede implementar un `pact`local para un tipo
   local, o un `pact` externo para un tipo local. No hay implementaciones
   solapadas.

### 4.2 Sintaxis de tipos

| Forma | Ejemplo | Rust |
|---|---|---|
| Nombre | `Int`, `Point`, `std::path::Path` | `i32`, `Point`, `std::path::Path` |
| Aplicación genérica | `Vec[Int]`, `HashMap[String, Int]` | `Vec<i32>`, `HashMap<&str, i32>` |
| Argumento de lifetime | `Cow['a, Str]` | `Cow<'a, str>` |
| Tupla | `(Int, String)`, `(Int,)`, `()` | `(i32, &str)`, `(i32,)`, `()` |
| Array | `[Int; 4]` | `[i32; 4]` |
| Slice | `[Int]` | `[i32]` |
| Referencia | `&Int`, `&mut Int` | `&i32`, `&mut i32` |
| Referencia con lifetime | `&'a Int`, `&'a mut Int` | `&'a i32`, `&'a mut i32` |
| Puntero crudo | `*const Int`, `*mut Int` | `*const i32`, `*mut i32` |
| Función | `(Int, Int) -> Int` | `fn(i32, i32) -> i32` |
| Closure | `impl Fn(Int) -> Int` | `impl Fn(i32) -> i32` |
| Trait object | `dyn Drawable` | `dyn Drawable` |
| `impl Trait` | `impl Iterator[Item = Int]` | `impl Iterator<Item = i32>` |
| Opción | `?Int` o `Option[Int]` | `Option<i32>` |
| Resultado | `!Int` o `Result[Int, Error]` | `Result<i32, Error>` |
| Nunca | `Never` | `!` |
| Unidad | `Unit` | `()` |
| `Self` | `Self` | `Self` |
| Nunca inferido | `_` (solo en patrones/anotaciones) | `_` |

Gramática:

```ebnf
type            ::= "Unit" | "Never" | "Bool" | "Char" | "Str" | "String"
                  | "Int" | "UInt" | "Float" | "I8" | "I16" | "I32" | "I64"
                  | "I128" | "Isize" | "U8" | "U16" | "U32" | "U64" | "U128"
                  | "Usize" | "F32" | "F64" | "Self"
                  | path type_args?
                  | "?" type
                  | "!" type
                  | "(" ")"
                  | "(" type "," ")"
                  | "(" type { "," type } ")"
                  | "(" [ type { "," type } [","] ] ")" "->" type
                  | "[" type ";" const_expr "]"
                  | "[" type "]"
                  | "&" lifetime? "mut"? type
                  | "*const" type
                  | "*mut" type
                  | "dyn" bounds
                  | "impl" bounds
type_args       ::= "[" type_arg { "," type_arg } [","] "]"
type_arg        ::= lifetime | type | const_expr
lifetime        ::= "'" IDENT
bounds          ::= path { "+" path }
```

`?T` y `!T` son azúcar: el AST los normaliza a `Option[T]` y
`Result[T, Error]` inmediatamente. Los lifetimes y los const generics se
desarrollan en §18 y §35; aquí solo se fija su sintaxis.

### 4.3 Catálogo de tipos del lenguaje

#### Primitivos y strings

| Tipo | PenguScript | Rust | Notas |
|---|---|---|---|
| Unidad | `Unit` | `()` | único valor `()` |
| Nunca | `Never` | `!` | resultado de `return`, `break`, `panic` |
| Booleano | `Bool` | `bool` | `true`/`false` |
| Carácter | `Char` | `char` | escalar Unicode |
| String prestado | `Str` | `str` | unsized; se usa como `&Str` |
| String propio | `String` | `String` | UTF-8, heap |
| Entero con signo | `I8`…`I128`, `Isize` | `i8`…`i128`, `isize` | dos complementos |
| Entero sin signo | `U8`…`U128`, `Usize` | `u8`…`u128`, `usize` | módulo 2^n |
| Entero por defecto | `Int` | `i32` | alias de `I32` |
| Entero sin signo por defecto | `UInt` | `u32` | alias de `U32` |
| Flotante | `F32`, `F64` | `f32`, `f64` | IEEE 754 |
| Flotante por defecto | `Float` | `f64` | alias de `F64` |

#### Compuestos y sumas

| Tipo | PenguScript | Rust | Notas |
|---|---|---|---|
| Opción | `?T` / `Option[T]` | `Option<T>` | `none`/`some` |
| Resultado | `!T` / `Result[T, E]` | `Result<T, E>` | `ok`/`err`; `!T` usa `Error` |
| Error de prelude | `Error` | `Box<dyn std::error::Error + Send + Sync>` | alias boxed; `!T` lo usa |
| Tupla | `(A, B)` | `(A, B)` | longitud fija |
| Array | `[T; N]` | `[T; N]` | longitud fija, `N` const |
| Slice | `[T]` | `[T]` | unsized; se usa como `&[T]` |
| Referencia | `&T`, `&mut T` | `&T`, `&mut T` | préstamo |
| Puntero crudo | `*const T`, `*mut T` | `*const T`, `*mut T` | solo en `curse`/`foreign` |
| Función | `(A) -> B` | `fn(A) -> B` | sin captura |
| Closure | `impl Fn(A) -> B` | `impl Fn(A) -> B` | captura; §37 |
| Trait object | `dyn Pact` | `dyn Pact` | despacho dinámico |
| `impl Trait` | `impl Pact` | `impl Pact` | tipo opaco |

#### Punteros inteligentes y sincronización

| Tipo | PenguScript | Rust | Uso |
|---|---|---|---|
| Caja | `Box[T]` | `Box<T>` | heap con dueño único |
| Referencia contada | `Rc[T]` | `Rc<T>` | un solo hilo |
| Referencia atómica | `Arc[T]` | `Arc<T>` | varios hilos |
| Celda | `Cell[T]` | `Cell<T>` | interior mutability para `Copy` |
| Celda prestada | `RefCell[T]` | `RefCell<T>` | préstamo dinámico |
| Mutex | `Mutex[T]` | `Mutex<T>` | exclusión mutua |
| RwLock | `RwLock[T]` | `RwLock<T>` | lectura/escritura |
| Cow | `Cow['a, T]` | `Cow<'a, T>` | clonar al escribir |
| Pin | `Pin[P]` | `Pin<P>` | datos inmóviles |
| Phantom | `PhantomData[T]` | `PhantomData<T>` | marca de tipo |

#### Colecciones

| Tipo | PenguScript | Rust |
|---|---|---|
| Vector | `Vec[T]` | `Vec<T>` |
| Cola doble | `VecDeque[T]` | `VecDeque<T>` |
| Mapa hash | `HashMap[K, V]` | `HashMap<K, V>` |
| Conjunto hash | `HashSet[T]` | `HashSet<T>` |
| Mapa ordenado | `BTreeMap[K, V]` | `BTreeMap<K, V>` |
| Conjunto ordenado | `BTreeSet[T]` | `BTreeSet<T>` |
| Montículo | `BinaryHeap[T]` | `BinaryHeap<T>` |

#### Tipos de usuario

| Tipo | Se declara con | Rust |
|---|---|---|
| Estructura | `rune Point` | `struct Point` |
| Enumeración | `enchanting Shape` | `enum Shape` |
| Contrato | `pact Drawable` | `trait Drawable` |
| Alias | `essence Meters = Float` | `type Meters = f64;` |
| Genérico | `rune Box[T]` | `struct Box<T>` |
| Unión | `chimera Bits` | `union Bits` |

Los tipos de biblioteca (`PathBuf`, `OsString`, `CString`, `Duration`, `Instant`,
`NonZeroU32`, etc.) no son palabras clave: se importan con `summon` y se usan con
su nombre. El catálogo de §20–§26 cubre las colecciones y strings en detalle.

### 4.4 Azúcar y alias

| Azúcar | Forma canónica | Regla |
|---|---|---|
| `?T` | `Option[T]` | `none` y `some` construyen; `?` postfijo extrae en §48 |
| `!T` | `Result[T, Error]` | `ok` y `err` construyen; `?` propaga |
| `Int` | `I32` | entero por defecto |
| `UInt` | `U32` | entero sin signo por defecto |
| `Float` | `F64` | flotante por defecto |
| `Str` | `str` | siempre detrás de `&` o en un tipo prestado |
| `String` | `String` | owned |
| `Unit` | `()` | valor `()` |
| `Never` | `!` | divergencia |

`?` y `!` son **prefijos de tipo**, no operadores. `?Int` es una opción de `Int`;
`!Int` es un resultado de `Int`. Para anidar, se usan las formas canónicas:
`Option[?Int]`, `Result[!Int, Error]`.

`Error` es un alias de la prelude:

```pengu
essence Error = Box[dyn std::error::Error + Send + Sync]
```

Por eso `!T` se traduce a `Result<T, Error>`, que en Rust es
`Result<T, Box<dyn std::error::Error + Send + Sync>>`. Un error concreto se puede
convertir con `From` o envolver explícitamente; §48 lo detalla.

### 4.5 Inferencia local

La inferencia es **bidireccional** y **local**:

- Una anotación esperada se propaga hacia la expresión.
- Los literales numéricos sin contexto usan `Int`; los flotantes, `Float`.
- `none` y `{}` requieren contexto; sin él, error (`PGS-E1302`).
- El tipo de retorno de una función nombrada es obligatorio; el cuerpo se infiere
  contra ese tipo.
- Las lambdas infieren sus parámetros del contexto y su retorno del cuerpo.
- No hay inferencia global entre módulos: cada firma es una frontera.

```pengu
bind x = 1                 -- Int
bind y = 2.0               -- Float
bind name = "pengu"        -- Str
bind maybe: ?Int = none    -- Option[Int]
bind pair = (1, "uno")     -- (Int, String)
```

Una colección vacía sin contexto es error:

```pengu
bind v = []                -- PGS-E1302: no se puede inferir T
bind v: [Int; 0] = []      -- válido
```

### 4.6 Tipos nominales, traits y coherencia

- `rune` y `enchanting` son **nominales**: el nombre es el tipo. Dos estructuras
  con los mismos campos no son intercambiables.
- `pact` es un contrato nominal. `ritual` implementa un `pact` para un tipo.
- Un `essence` es un alias transparente: `Meters` y `Float` son el mismo tipo
  para el checker, pero el nombre se conserva en la documentación y en los
  diagnósticos.
- Un `pact` puede tener métodos con receptor `@`, `@mut` o `@own`, funciones
  asociadas y tipos asociados. Se detalla en §33–§36.
- La **coherencia** sigue la regla del huérfano de Rust: no se puede implementar
  un `pact` externo para un tipo externo. Las implementaciones solapadas son
  error (`PGS-E1308`).
- `dyn Pact` exige object safety. `impl Pact` es un tipo opaco y solo se permite
  en posición de parámetro o retorno.
- La **varianza** de los genéricos sigue a Rust: `&T` es covariante en `T`,
  `&mut T` es invariante, `Fn` es contravariante en argumentos y covariante en
  retorno. Se detalla en §35.

### 4.7 Ejemplo ejecutable

```pengu
rune Point
    x: Float
    y: Float

enchanting Shape
    Circle(Float)
    Rectangle(Float, Float)

pact Area
    area = (@) -> Float

essence Meters = Float

area_of = (shape: &Shape) -> Float
    match shape
        when Circle(r) then 3.141592653589793 * r * r
        when Rectangle(w, h) then w * h
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

enum Shape {
    Circle(f64),
    Rectangle(f64, f64),
}

trait Area {
    fn area(&self) -> f64;
}

type Meters = f64;

fn area_of(shape: &Shape) -> f64 {
    match shape {
        Shape::Circle(r) => 3.141592653589793 * r * r,
        Shape::Rectangle(w, h) => w * h,
    }
}
```

El ejemplo completo está en
[`scratch/examples/sec04_types.pengu`](../scratch/examples/sec04_types.pengu) y su
traducción en
[`scratch/examples/sec04_types.rs`](../scratch/examples/sec04_types.rs).

### 4.8 Diagnósticos

| Código | Condición | Sugerencia |
|---|---|---|
| `PGS-E1301` | tipo esperado y tipo encontrado no coinciden | revisar la anotación o la expresión |
| `PGS-E1302` | no se puede inferir un tipo | añadir `: Tipo` |
| `PGS-E1303` | tipo desconocido | importarlo con `summon` o declararlo |
| `PGS-E1304` | faltan argumentos de tipo | añadir `[T]` |
| `PGS-E1305` | aridad de tipo incorrecta | revisar parámetros |
| `PGS-E1306` | `?`/`!` mal aplicado | usar `Option[T]`/`Result[T, E]` |
| `PGS-E1307` | trait bound no satisfecho | implementar el `pact` o ajustar el bound |
| `PGS-E1308` | implementación huérfana o solapada | mover el `pact`/tipo o eliminar el solapamiento |
| `PGS-E1309` | `dyn` no es object-safe | quitar métodos genéricos o usar `impl Trait` |
| `PGS-E1310` | `impl Trait` en posición inválida | moverlo a parámetro/retorno |

### 4.9 Criterios de aceptación

- [x] El catálogo cubre primitivos, strings, opciones, resultados, tuplas,
      arrays, slices, referencias, punteros, funciones, closures, traits,
      punteros inteligentes, colecciones y tipos de usuario.
- [x] La sintaxis de tipos tiene gramática y tabla de traducción a Rust.
- [x] Se distingue `?T`/`!T` de `Option[T]`/`Result[T, E]` y se explica el azúcar.
- [x] La inferencia es local y las firmas de items son explícitas.
- [x] Se declaran coherencia, object safety y varianza.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="sec-05-variables"></a>
## 5. Variables y bindings

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 0 (piloto) |
| Rust | `let`, `let mut`, patrones, shadowing, drop |
| Palabras mágicas | `bind`, `morph` |
| Depende de | §4, §7, §8 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec05_variables.pengu` |

Esta sección es la **sección piloto** de la Fase 0. Fija la forma de declarar
estado local y valida la plantilla editorial que usarán las 71 secciones.

### 5.1 Reglas

- **DEBE** declararse toda variable local con `bind` o `morph`. No existe una
  forma implícita de crear variables.
- **NO DEBE** existir ningún `bind` ni `morph` a nivel de módulo. Un binding
  siempre vive dentro de una función, un `grimoire` o un bloque.
- `bind` declara un binding **inmutable**: se inicializa una vez y no se
  reasigna.
- `morph` declara un binding **mutable**: se puede inicializar y reasignar
  varias veces.
- **DEBE** inferirse el tipo a partir del inicializador cuando la anotación se
  omite y la inferencia es inequívoca.
- **DEBE** exigirse una anotación de tipo cuando no hay inicializador. Un
  `bind x` sin tipo ni valor es un error.
- **DEBE** rechazarse el uso de un binding antes de su inicialización. La
  comprobación es de flujo, no solo textual.
- **DEBE** rechazarse la reasignación de un `bind`. La primera asignación a un
  `bind` sin inicializador cuenta como su inicialización; una segunda
  asignación es un error.
- **PUEDE** hacerse shadowing en un scope interior. **NO DEBE** redeclararse el
  mismo nombre en el mismo scope; para eso se usa un nombre nuevo o un bloque
  interior.
- **PUEDE** usarse `_` como patrón de descarte. `_` no crea un binding.
- **DEBEN** respetarse las reglas de ownership y borrowing de §16 y §17:
  `morph` permite mutar el lugar, no ignorar un préstamo activo.
- **NO DEBE** confundirse `morph` con una variable global ni con un `static`.
  El estado de módulo se declara con `sigil` o `relic` (§6).
- **NO DEBE** confundirse una definición de función `name = (params) -> Tipo`
  con un binding. Es un **item de función** y por eso puede vivir en el módulo;
  no captura el entorno y no se puede reasignar.

La mutabilidad es explícita y opt-in. El lenguaje no adopta
mutable-by-default: un `bind` olvidado debe fallar, no volverse mutable en
silencio. Esta es la misma dirección que Rust (`let mut`), V (`mut`) y Kotlin
(`var`), y es la que necesita un modelo con préstamos.

### 5.2 Sintaxis

```ebnf
binding           ::= immutable_binding | mutable_binding
immutable_binding ::= "bind" pattern type_annotation? initializer? NEWLINE
mutable_binding   ::= "morph" pattern type_annotation? initializer? NEWLINE
type_annotation   ::= ":" type
initializer       ::= "=" expression
reassignment      ::= place_expr assignment_op expression NEWLINE
assignment_op     ::= "=" | "+=" | "-=" | "*=" | "/=" | "%="
                    | "&=" | "|=" | "^=" | "<<=" | ">>="
pattern           ::= IDENT | "_" | tuple_pattern | rune_pattern
tuple_pattern     ::= "(" pattern ("," pattern)* ","? ")"
```

`pattern` es el subconjunto de patrones de §30 que no requiere `match`:
identificadores, `_`, tuplas y patrones de `rune`. Los patrones con `|`, `if`
o rangos se reservan para §30.

Formas válidas:

```pengu
bind max_hp: Int = 100
bind inferred = 100
bind pending: Int
morph hp = max_hp
morph counter: Int
bind (x, y) = (1, 2)
bind _ = 0
hp = hp - 10
counter += 1
```

Formas inválidas:

```pengu
-- ERROR: no hay tipo ni inicializador
bind mystery

-- ERROR: un bind no se reasigna
bind fixed = 1
fixed = 2

-- ERROR: bind/morph no existen en el módulo
bind global = 1
```

La asignación `=` **no declara**: actualiza un lugar que ya existe. Los
operadores compuestos son azúcar de `lugar = lugar op expr`, evaluado una sola
vez sobre el lugar.

### 5.3 Semántica

**Scope y visibilidad.** Un binding es visible desde el final de su declaración
hasta el final del bloque que lo contiene. No es visible antes de la
declaración, ni fuera de ese bloque. Un bloque interior puede declarar otro
binding con el mismo nombre (shadowing); el binding exterior vuelve a ser
visible al salir del bloque interior. La redeclaración en el mismo bloque es un
error para evitar ambigüedad y cambios accidentales de significado.

**Inicialización y asignación.** `bind` y `morph` pueden declararse sin
inicializador si llevan anotación de tipo. La primera asignación posterior
inicializa el lugar; en un `bind` es la única asignación permitida. En un
`morph`, las asignaciones posteriores son reasignaciones. El compilador
comprueba inicialización definitiva antes de cada uso y antes de cada préstamo.

**Inferencia.** El tipo se infiere del inicializador cuando es posible. Si no
hay inicializador, la anotación es obligatoria. Si el inicializador es un
literal entero ambiguo, se aplica el tipo por defecto `Int` (= `i32`); si el
contexto no permite decidir, el programa debe anotar el tipo. La inferencia es
local a la función: no se infiere un tipo a partir de usos en otras funciones.

**Mutabilidad.** `morph` hace mutable el **lugar** del binding, no los valores
a los que apunta. `morph hp = max_hp` permite `hp = hp - 10`, pero no permite
mutar a través de un `&T` compartido. Un `bind` que contiene un tipo con
interior mutability (por ejemplo, `Cell`) sigue siendo inmutable en su
asignación, aunque su contenido pueda cambiar por una API explícita; §20 lo
detalla.

**Destructuring.** Un patrón de tupla o de `rune` introduce todos sus nombres
con la misma mutabilidad. El patrón se comprueba de izquierda a derecha. Un
movimiento parcial deja el binding original parcialmente movido; usar una parte
movida es un error. `_` no introduce nombre y descarta el valor en el punto de
la declaración.

**Drop.** Los bindings se destruyen en orden inverso al de declaración al salir
de su scope. El shadowing no destruye el binding anterior en ese punto: el
binding anterior sigue vivo hasta el final de su scope, salvo que haya sido
movido. Los movimientos y las copias siguen las reglas de §16.

**Codegen.** La traducción es directa:

| PenguScript | Rust generado |
|---|---|
| `bind x = 1` | `let x = 1;` |
| `bind x: Int` | `let x: i32;` |
| `morph x = 1` | `let mut x = 1;` |
| `morph x: Int` | `let mut x: i32;` |
| `x = expr` | `x = expr;` |
| `x += expr` | `x += expr;` |
| `bind (a, b) = expr` | `let (a, b) = expr;` |
| `bind _ = expr` | `let _ = expr;` |

El codegen **NO DEBE** añadir `mut` a un `bind`, ni omitirlo en un `morph`.
Tampoco debe convertir una asignación a un `bind` en una redeclaración
silenciosa: el error se detecta antes de generar Rust.

### 5.4 Ejemplos

**Ejemplo completo ejecutable.** Declara un binding inmutable, uno mutable,
aplica una asignación compuesta, hace destructuring de una tupla y usa
inicialización diferida.

```pengu
grimoire
    bind max_hp: Int = 100
    morph hp = max_hp
    hp -= 10

    bind pair = (3, 4)
    bind (left, right) = pair
    bind total = left + right

    bind pending: Int
    pending = total

    bind _ = 0

    print(hp)
    print(pending)
```

**Shadowing en un bloque interior.** El binding exterior no se modifica.

```pengu
grimoire
    bind value = 1
    do
        bind value = 2
        print(value)
    print(value)
```

`do` se define en §8; aquí solo se usa como bloque interior para el shadowing.

**Binding mutable con inicialización diferida.**

```pengu
grimoire
    morph counter: Int
    counter = 0
    counter += 1
    print(counter)
```

**Ejemplo negativo — global.** El siguiente programa no es válido porque
`bind` no puede aparecer en el módulo:

```pengu
bind global = 1
```

**Ejemplo negativo — reasignación de un `bind`.**

```pengu
grimoire
    bind fixed = 1
    fixed = 2
```

**Ejemplo negativo — uso antes de inicializar.**

```pengu
grimoire
    print(value)
    bind value = 1
```

**Ejemplo límite — `morph` no evita el borrow checker.** Mutar mientras un
préstamo compartido está vivo se diagnostica con las reglas de §17, no con una
excepción de §5:

```pengu
grimoire
    morph x = 1
    bind r = &x
    x = 2
    print(*r)
```

Este programa no compila: `r` sigue prestando `x` cuando se intenta `x = 2`.
El préstamo termina después de `print(*r)`. La sección §17 formaliza la regla.

### 5.5 Rust generado

El ejemplo completo de §5.4 genera:

```rust
fn main() {
    let max_hp: i32 = 100;
    let mut hp = max_hp;
    hp -= 10;

    let pair = (3, 4);
    let (left, right) = pair;
    let total = left + right;

    let pending: i32;
    pending = total;

    let _ = 0;

    println!("{}", hp);
    println!("{}", pending);
}
```

Compila con `rustc --edition 2024` y produce:

```text
90
7
```

### 5.6 Diagnósticos

| Código | Mensaje | Causa | Solución |
|---|---|---|---|
| `PGS-E1101` | `bind`/`morph` no permitido en el módulo | Se intentó declarar una variable global | Usa `sigil` o `relic`; si es estado local, muévelo a `grimoire` o a una función |
| `PGS-E1102` | no se puede reasignar un binding inmutable | Se usó `=` o un compuesto sobre un `bind` ya inicializado | Declara con `morph` si la mutación es intencional; si no, crea un binding nuevo |
| `PGS-E1103` | binding usado antes de inicializarse | El flujo de control permite leer antes de la primera asignación | Inicializa en la declaración o asigna en todas las rutas previas |
| `PGS-E1104` | no se puede inferir el tipo sin inicializador | `bind`/`morph` sin `:` y sin `=` | Añade una anotación de tipo o un inicializador |
| `PGS-E1105` | binding duplicado en el mismo scope | Dos `bind`/`morph` con el mismo nombre en el mismo bloque | Usa un nombre distinto o un bloque interior para shadowing |
| `PGS-E1106` | destino de asignación inválido | El lado izquierdo no es un lugar asignable | Asigna a una variable, campo o índice; no a una expresión temporal |
| `PGS-E1107` | uso después de mover | El valor se movió a otro binding | Usa `clone`/`Copy` si corresponde, o reordena el flujo (§16) |
| `PGS-E1108` | mutación con préstamo compartido activo | Se intentó mutar un lugar mientras un `&T` lo prestaba | Termina el préstamo o usa un préstamo mutable/interior mutability según §17 y §20 |

### 5.7 Interacciones

- **§4 Sistema de tipos:** la inferencia y la anotación usan el catálogo de
  tipos; `Int` es `i32`, `Float` es `f64`.
- **§6 Constantes y statics:** `sigil` y `relic` son la única forma de estado
  de módulo; `static mut` no se expone.
- **§7 Scope:** visibilidad, drop scopes, temporales y shadowing.
- **§8 Expresiones:** `bind` y la asignación son sentencias; no producen valor.
- **§15 Funciones:** los parámetros son bindings inmutables por defecto; su
  forma mutable se define allí.
- **§16 Ownership:** move, `Copy` y drop.
- **§17 Borrowing:** `morph` no anula préstamos.
- **§30 Pattern matching:** los patrones de `bind`/`morph` son el mismo sistema
  de patrones que `match`.

### 5.8 Ver también

- [§3.3 Items de nivel superior](#sec-03-programa)
- [§4 Sistema de tipos](#sec-04-tipos)
- [§6 Constantes, statics y estado global](#sec-06-constantes)
- [§7 Scope y resolución de nombres](#sec-07-scope)
- [§8 Expresiones, sentencias y bloques](#sec-08-expresiones)
- [§16 Ownership](#sec-16-ownership)
- [§17 Borrowing](#sec-17-borrowing)
- [§30 Pattern matching](#sec-30-pattern-matching)
- [§61 Léxico y palabras clave](#sec-61-lexico-keywords)
- [§65 Catálogo de diagnósticos](#sec-65-diagnosticos)

### 5.9 Criterios de aceptación

- [x] Todo binding local usa `bind` o `morph`; no hay creación implícita.
- [x] Ningún `bind`/`morph` vive en el nivel de módulo.
- [x] La inicialización, el shadowing y la reasignación tienen reglas y diagnósticos.
- [x] El ejemplo tiene Rust compilable y produce la salida documentada.

[↑ Volver al índice](#indice)

<a id="sec-06-constantes"></a>
## 6. Constantes, statics y estado global

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 1 |
| Rust | `const`, `static`, `thread_local!`, `Mutex`, interior mutability |
| Palabras mágicas | `sigil`, `relic`, `@@shared`, `@@thread_local` |
| Depende de | §4, §5 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec06_constants.pengu` |

PenguScript **no tiene variables globales**. Lo que existe en el nivel de módulo
es un conjunto cerrado de items inmutables: `sigil` (constante de compilación) y
`relic` (estático inmutable). El estado compartido mutable solo se permite con una
política explícita y un tipo que garantice seguridad entre hilos.

### 6.1 `sigil`: constantes de compilación

```pengu
sigil MAX_HP: Int = 100
sigil GREETING: &'static Str = "hello"
sigil ORIGIN: (Float, Float) = (0.0, 0.0)
```

Reglas:

1. `sigil` declara una constante. Se sustituye en tiempo de compilación y no
   ocupa almacenamiento en el binario.
2. El inicializador debe ser **evaluable en compilación**. Se permiten literales,
   operaciones aritméticas y lógicas constantes, constructores de `rune` con
   campos constantes, arrays, tuplas, `Option`, `Result` y llamadas a funciones
   `eternal`.
3. No se permiten `String`, `Vec`, `HashMap`, asignaciones de heap ni llamadas a
   funciones normales en el inicializador.
4. `sigil` puede aparecer en el nivel de módulo o dentro de un bloque. En un
   bloque sigue siendo un item, no una variable: no se puede reasignar.
5. `sigil` puede usarse como longitud de array, argumento const genérico y en
   patrones constantes.
6. El nombre se escribe en `SCREAMING_SNAKE_CASE`; otra forma produce un warning.

### 6.2 `relic`: estáticos inmutables

```pengu
relic VERSION: &'static Str = "0.1.0"
relic TABLE: [Int; 3] = [1, 2, 3]
```

Reglas:

1. `relic` declara un estático inmutable con almacenamiento propio. En Rust es un
   `static`.
2. Solo se permite en el nivel de módulo. Un `relic` dentro de una función es
   error (`PGS-E4007`).
3. El inicializador debe ser constante, igual que el de `sigil`.
4. Un `relic` es inmutable para siempre: no se puede asignar, ni declarar con
   `morph`, ni pasar como `&mut`.
5. El tipo debe ser `Sync` para que pueda compartirse entre hilos. Si no lo es,
   el compilador emite `PGS-E4004`.
6. `relic` no se puede usar como longitud de array ni como argumento const; para
   eso se usa `sigil`.
7. El nombre se escribe en `SCREAMING_SNAKE_CASE`.

### 6.3 `static mut` no existe

PenguScript **nunca** genera `static mut`. Tampoco existe una forma de declarar un
global mutable sin sincronización. Las alternativas son:

| Necesidad | Solución |
|---|---|
| Valor constante | `sigil` |
| Valor inmutable compartido | `relic` |
| Contador compartido entre hilos | `@@shared relic` con `Mutex`/`RwLock`/atómico |
| Estado por hilo | `@@thread_local relic` |
| Estado de una instancia | campo de un `rune`, no un global |

Cualquier intento de declarar `static mut`, `relic mut` o `morph relic` es error
(`PGS-E4002`/`PGS-E4003`).

### 6.4 Estado compartido con `@@shared`

```pengu
summon std::sync::Mutex

@@shared relic COUNTER: Mutex[Int] = Mutex.new(0)
```

`@@shared` es una **política explícita** para un `relic` que contiene
interior mutability. No cambia el tipo ni genera `unsafe`; solo documenta y valida
que el tipo es seguro de compartir.

Reglas:

1. `@@shared` solo se aplica a `relic`, nunca a `sigil` ni a un `bind`.
2. El tipo debe implementar `Sync`. `Mutex[T]`, `RwLock[T]`, `AtomicUsize` y
   similares cumplen; `RefCell[T]`, `Rc[T]` y `Cell[T]` no cumplen.
3. El acceso se hace a través de la API del tipo (`lock`, `read`, `write`,
   `fetch_add`), nunca con `static mut`.
4. El compilador no añade `unsafe`; si el tipo lo requiere, el código de acceso
   debe usar `curse` (§52).
5. `@@shared` no implica `Send` ni `Sync` automáticos: el tipo debe declararlos.

Ejemplo de acceso:

```pengu
@@shared relic COUNTER: Mutex[Int] = Mutex.new(0)

grimoire
    morph guard = COUNTER.lock().unwrap()
    *guard += 1
```

### 6.5 Estado por hilo con `@@thread_local`

```pengu
summon std::cell::RefCell

@@thread_local relic CACHE: RefCell[Int] = RefCell.new(0)
```

`@@thread_local` declara un estático cuyo valor es distinto en cada hilo. Se
traduce a `thread_local!` de Rust. Reglas:

1. Solo se aplica a `relic` de nivel de módulo.
2. El tipo no necesita `Sync`, porque no se comparte entre hilos.
3. El acceso se hace con la API de `thread_local!`; el codegen puede envolverlo
   en una función de acceso si el tipo no es `Copy`.
4. No se permite `@@thread_local` junto con `@@shared`.

### 6.6 Estáticos de FFI

Un bloque `foreign "C"` puede declarar estáticos de una biblioteca externa:

```pengu
foreign "C"
    @@link_name("errno") relic ERRNO: Int
```

Reglas:

1. Un `relic` de FFI no tiene inicializador; su valor lo proporciona la
   biblioteca.
2. Es de solo lectura desde PenguScript. Para escribir memoria externa se usa
   `curse` y un puntero crudo.
3. `static mut` de C se declara como `*mut T` y se accede en `curse`; el
   compilador no genera un `static mut` de Rust.
4. La semántica completa de `foreign` está en §55.

### 6.7 Evaluación constante

- `sigil` y `relic` se evalúan con el evaluador constante de Rust. Un
  inicializador que no es constante es error (`PGS-E4001`).
- Se permite llamar a funciones `eternal` (`const fn`) y a métodos `eternal` de
  un `ritual`.
- No se permite asignar memoria, leer variables de entorno, abrir archivos ni
  llamar a funciones que no sean `eternal`.
- Un ciclo entre constantes es error (`PGS-E4006`).
- `sigil` puede depender de otro `sigil`; `relic` puede depender de `sigil`, pero
  no de otro `relic` (para evitar orden de inicialización).

### 6.8 Visibilidad y nombres

- `unveil sigil` y `unveil relic` exportan el item; sin `unveil`, es privado del
  módulo.
- Los nombres usan `SCREAMING_SNAKE_CASE`. El compilador no los cambia.
- Un `sigil`/`relic` no puede compartir nombre con otro item del mismo módulo.

### 6.9 Ejemplo ejecutable

```pengu
summon std::sync::Mutex

sigil MAX_HP: Int = 100
relic GREETING: &'static Str = "hello"
@@shared relic COUNTER: Mutex[Int] = Mutex.new(0)

grimoire
    print(GREETING)
    print(MAX_HP)
```

Rust generado:

```rust
use std::sync::Mutex;

const MAX_HP: i32 = 100;
static GREETING: &str = "hello";
static COUNTER: Mutex<i32> = Mutex::new(0);

fn main() {
    println!("{}", GREETING);
    println!("{}", MAX_HP);
}
```

El ejemplo completo está en
[`scratch/examples/sec06_constants.pengu`](../scratch/examples/sec06_constants.pengu)
y su traducción en
[`scratch/examples/sec06_constants.rs`](../scratch/examples/sec06_constants.rs).

### 6.10 Diagnósticos

| Código | Condición | Sugerencia |
|---|---|---|
| `PGS-E4001` | inicializador no constante | usar literales o una función `eternal` |
| `PGS-E4002` | `static mut` o `relic mut` | usar `@@shared` con `Mutex`/atómico |
| `PGS-E4003` | asignación o `morph` sobre `relic` | declarar un `rune` o usar interior mutability |
| `PGS-E4004` | `relic` no es `Sync` | usar `Mutex`/`RwLock` o `@@thread_local` |
| `PGS-E4005` | `@@shared` mal aplicado | aplicarlo solo a `relic` con tipo `Sync` |
| `PGS-E4006` | ciclo de constantes | romper la dependencia |
| `PGS-E4007` | `relic` dentro de una función | moverlo al módulo |
| `PGS-E4008` | `@@thread_local` fuera de módulo | moverlo al módulo |
| `PGS-E4009` | acceso FFI sin `curse` | envolver en `curse` |
| `PGS-E4010` | nombre que no es `SCREAMING_SNAKE_CASE` | renombrar |

### 6.11 Criterios de aceptación

- [x] Se distingue `sigil` (const) de `relic` (static inmutable).
- [x] No existe `static mut` ni global mutable sin sincronización.
- [x] `@@shared` y `@@thread_local` tienen reglas y tipos válidos.
- [x] La evaluación constante y sus límites están definidos.
- [x] El ejemplo tiene Rust compilable.
- [x] Los diagnósticos cubren const, statics, FFI y nombres.

[↑ Volver al índice](#indice)

<a id="sec-07-scope"></a>
## 7. Scope y resolución de nombres

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 1 |
| Rust | Bloques, `use`, `crate::`, `super::`, `Self`, drop |
| Palabras mágicas | `summon`, `@`, `Self` |
| Depende de | §3, §5, §6 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec07_scope.pengu` |

El **scope** es la región del programa donde un nombre es visible. PenguScript
usa scope léxico: un nombre se resuelve en el bloque que lo contiene y en sus
bloques anidados, nunca “hacia arriba” en el archivo ni en tiempo de ejecución.

### 7.1 Scopes léxicos

| Scope | Se abre con | Contiene |
|---|---|---|
| Módulo | un archivo `.pengu` o un `scroll` inline | items, imports, submódulos |
| Función | `name = (...) -> T` | parámetros, `bind`/`morph`, items locales |
| Bloque | `if`, `else`, `for`, `while`, `loop`, `match`, `do` | bindings locales |
| Lambda | `(...) => ...` | parámetros y capturas |
| `grimoire` | `grimoire` | el cuerpo de `main` |

Reglas:

1. Un bloque puede leer nombres de sus bloques padres mientras no estén
   sombreados.
2. Un nombre local es visible **después** de su declaración, no antes
   (`PGS-E1403`).
3. Los parámetros son visibles en todo el cuerpo de la función, incluidas las
   lambdas anidadas.
4. Los items de un módulo son visibles en todo el módulo, sin importar el orden
   de declaración. Esto incluye funciones, `rune`, `enchanting`, `pact`, `sigil`,
   `relic` y `scroll`.
5. Un `scroll` inline crea un scope de módulo propio; sus items no son visibles
   en el módulo padre sin `summon`.

### 7.2 Items, locales y namespaces

PenguScript separa dos espacios de nombres:

| Namespace | Contiene | Se introduce con |
|---|---|---|
| Valores | variables, parámetros, funciones, constantes | `bind`, `morph`, parámetros, items de función, `sigil` |
| Tipos | `rune`, `enchanting`, `pact`, `essence`, genéricos | declaraciones de tipo |

Un `bind` local puede ocultar un item de función del mismo nombre en el
namespace de valores desde su declaración. No puede ocultar un tipo en el
namespace de tipos. Para llamar a la función oculta se usa una ruta
(`crate::nombre` o `summon` con alias).

### 7.3 Shadowing

El **shadowing** es declarar un nombre nuevo en un bloque interno que oculta uno
del bloque padre:

```pengu
bind x = 1
do
    bind x = 2
    print(x)   -- 2
print(x)       -- 1
```

Reglas:

1. Solo se permite en un bloque **interno**. Dos `bind`/`morph` con el mismo
   nombre en el mismo bloque son error (`PGS-E1404`).
2. El shadowing no muta el valor anterior: crea un binding nuevo. El valor
   anterior se conserva hasta el final de su scope.
3. Un `bind` puede ocultar un `morph` y viceversa; el tipo puede cambiar.
4. No se permite shadowing de items de módulo en el mismo módulo.
5. El shadowing de un nombre de la prelude produce un warning, no un error.

### 7.4 Rutas

| Forma | Significado | Rust |
|---|---|---|
| `Point` | nombre en el scope actual | `Point` |
| `geometry::Point` | nombre en un módulo importado | `geometry::Point` |
| `crate::geometry::Point` | raíz del tome | `crate::geometry::Point` |
| `super::Point` | módulo padre | `super::Point` |
| `std::fmt::Debug` | crate externa | `std::fmt::Debug` |
| `Self` | tipo del `ritual`/`pact` actual | `Self` |
| `@` | receptor actual | `self` |

Reglas:

1. No existe el prefijo `self::`. Para el módulo actual se usa el nombre sin
   prefijo; para el padre, `super::`; para la raíz, `crate::`.
2. `@` no es una ruta: solo aparece como receptor (`@`, `@mut`, `@own`) o en una
   expresión de acceso (`@.campo`). En patrones, `@` sigue siendo el operador de
   binding de Rust (`nombre @ patrón`), que se distingue por contexto (§30).
3. `Self` solo es válido dentro de un `ritual` o `pact`. Fuera de ellos es error
   (`PGS-E1406`).
4. Los nombres de crate externos se importan con `summon`; no se accede a ellos
   por un prefijo implícito.

### 7.5 Prelude

La prelude se importa automáticamente en todos los módulos:

```text
Option  Some  None  Result  Ok  Err
Vec  String  Box  Unit  Never  Error
print  format  panic  assert  assert_eq  assert_ne
```

Reglas:

1. La prelude no incluye `HashMap`, `Rc`, `Arc`, `Mutex` ni traits de `std`;
   esos se importan con `summon`.
2. Un nombre de la prelude puede sombrearse; el compilador avisa
   (`PGS-W1401`) para que la intención sea explícita.
3. `print` y `format` son funciones del compilador, no macros visibles. Se
   traducen a `println!` y `format!` respectivamente.
4. `Vec`, `String`, `Box`, `Option` y `Result` son tipos de la prelude; sus
   constructores se usan con `Vec.new()`, `String.from(...)`, `Box.new(...)`,
   `some(...)`, `ok(...)`, etc.

### 7.6 Drop scopes

El **drop scope** es el punto donde un valor se destruye. PenguScript sigue las
reglas de Rust 2024:

1. Los locales se destruyen en orden inverso a su declaración, al final del
   bloque.
2. `return` destruye los locales del cuerpo antes de salir.
3. `break` y `continue` destruyen los locales del cuerpo del bucle.
4. `?` destruye los locales antes de propagar el error.
5. Los temporales se destruyen al final del enunciado que los crea, salvo que la
   extensión de vida de temporales los prolongue.
6. En un `if`, los temporales de la condición se destruyen antes de entrar a la
   rama (regla de Rust 2024). En un `match`, el temporal del scrutinee vive
   durante todo el `match`.

### 7.7 Temporales y extensión de vida

Un **temporal** es un valor sin nombre, como `Point(x: 1, y: 2)` o
`String.from("x")`. Su vida depende de dónde se use:

```pengu
bind p = &Point(x: 1.0, y: 2.0)   -- el temporal vive hasta el final del bloque
print(p.x)
```

Reglas:

1. Un temporal ligado con `bind`/`morph` a una referencia se extiende hasta el
   final del bloque (temporary lifetime extension), igual que en Rust.
2. Un temporal usado como argumento vive hasta el final del enunciado.
3. Un temporal en la cola de un bloque se destruye después de producir el valor
   del bloque.
4. Un temporal en una condición de `if` se destruye antes de la rama.
5. El compilador no inventa extensiones adicionales; si el préstamo no vive lo
   suficiente, `rustc` lo rechaza y el diagnóstico se remapea.

### 7.8 Importaciones y globs

- `summon` en el nivel de módulo importa nombres en todo el módulo.
- `summon` dentro de un bloque importa nombres solo en ese bloque.
- `summon path::*` importa todos los nombres públicos. Si dos globs introducen el
  mismo nombre, el uso es ambiguo (`PGS-E1402`).
- Una importación explícita gana sobre una glob.
- Una importación no usada produce un warning (`PGS-W1402`).
- No se permite importar un item privado (`PGS-E1405`).

### 7.9 Ejemplo ejecutable

```pengu
sigil LIMIT: Int = 10

rune Counter
    value: Int

ritual Counter
    bump = (@mut) -> Unit
        @.value += 1

grimoire
    bind x = 1
    do
        bind x = 2
        print(x)
    print(x)

    morph counter = Counter(value: 0)
    counter.bump()
    print(counter.value)
```

Rust generado:

```rust
const LIMIT: i32 = 10;

struct Counter {
    value: i32,
}

impl Counter {
    fn bump(&mut self) {
        self.value += 1;
    }
}

fn main() {
    let x = 1;
    {
        let x = 2;
        println!("{}", x);
    }
    println!("{}", x);

    let mut counter = Counter { value: 0 };
    counter.bump();
    println!("{}", counter.value);
}
```

El ejemplo completo está en
[`scratch/examples/sec07_scope.pengu`](../scratch/examples/sec07_scope.pengu) y su
traducción en
[`scratch/examples/sec07_scope.rs`](../scratch/examples/sec07_scope.rs).

### 7.10 Diagnósticos

| Código | Condición | Sugerencia |
|---|---|---|
| `PGS-E1401` | nombre no resuelto | declararlo o importarlo |
| `PGS-E1402` | glob ambiguo | usar una ruta explícita |
| `PGS-E1403` | uso antes de la declaración local | mover la declaración |
| `PGS-E1404` | binding duplicado en el mismo bloque | usar shadowing en un bloque interno |
| `PGS-E1405` | item privado inaccesible | añadir `unveil` |
| `PGS-E1406` | `Self` fuera de `ritual`/`pact` | moverlo o cambiar por el tipo |
| `PGS-W1401` | shadowing de la prelude | renombrar si no es intencional |
| `PGS-W1402` | importación no usada | eliminarla o usarla |

### 7.11 Criterios de aceptación

- [x] Se distinguen scope de módulo, función, bloque, lambda y `grimoire`.
- [x] Items y locales tienen reglas de visibilidad explícitas.
- [x] El shadowing solo ocurre en bloques internos.
- [x] Las rutas `crate::`, `super::`, `Self`, `@` y los globs están definidos.
- [x] El drop scope y la extensión de temporales siguen Rust 2024.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="sec-08-expresiones"></a>
## 8. Expresiones, sentencias y bloques

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 1 |
| Rust | Bloques, `if`, `match`, `loop`, `return`, `!` |
| Palabras mágicas | `do`, `then`, `when`, `Never` |
| Depende de | §4, §5, §7 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec08_expressions.pengu` |

Una **expresión** produce un valor. Una **sentencia** no produce un valor, sino
que declara, asigna o controla el flujo. PenguScript lleva la idea de MoonScript
al extremo: casi todo es expresión, y las únicas sentencias son las que cambian
el estado o introducen nombres.

### 8.1 La distinción

| Construcción | ¿Expresión? | Tipo | Valor |
|---|---|---|---|
| Literal, path, llamada, campo, índice | sí | el del valor | el valor |
| Operador unario/binario | sí | según §11 | el resultado |
| `if` | sí | unión de ramas | rama ejecutada |
| `match` | sí | unión de brazos | brazo ejecutado |
| `loop` | sí | tipo del `break` | valor del `break` |
| Bloque / `do` | sí | última expresión | último valor |
| Lambda | sí | tipo función | la closure |
| `return`, `break`, `continue` | sí | `Never` | no retorna |
| `panic(...)` | sí | `Never` | no retorna |
| `while`, `for` | sí | `Unit` | `()` |
| `bind`, `morph`, asignación | **no** | — | — |

Reglas:

1. `bind` y `morph` son sentencias. No se pueden usar como valor, ni dentro de
   una expresión, ni en la cola de un bloque que deba producir un valor.
2. La asignación (`x = y`) es una sentencia. No existe la asignación como
   expresión (no hay `if (x = y)`).
3. `return`, `break` y `continue` son expresiones de tipo `Never`; pueden
   aparecer en posición de expresión y se coercionan a cualquier tipo.
4. `while` y `for` son expresiones de tipo `Unit`; su valor se descarta.
5. Un bloque cuya última sentencia no es una expresión produce `Unit`.

### 8.2 Categorías de expresión

```text
expresión ::= literal
            | path
            | call
            | method_call
            | field
            | index
            | unary
            | binary
            | "if" ...
            | "match" ...
            | "loop" ...
            | "do" bloque
            | "(" expresión ")"
            | lambda
            | "return" expresión?
            | "break" expresión?
            | "continue"
            | "panic" "(" expresión ")"
```

La gramática completa de operadores y precedencia está en §11. La de patrones,
en §30. La de llamadas y métodos, en §15 y §31.

### 8.3 Bloques y `do`

Un bloque es una secuencia de sentencias con un valor final opcional:

```pengu
do
    bind base = 10
    base + 1
```

- El valor del bloque es su última expresión.
- Si la última línea es una sentencia (`bind`, `morph`, asignación, `while`,
  `for`), el bloque vale `()`.
- Un bloque vacío vale `()`.
- `do` introduce un bloque en posición de expresión. Sin `do`, un bloque solo
  aparece como cuerpo de `if`, `match`, `loop`, función o `grimoire`.
- El bloque crea un scope léxico nuevo (§7).

Rust generado para el ejemplo (dentro de una función para que el fragmento sea
compilable):

```rust
fn example() -> i32 {
    let base = 10;
    base + 1
}
```

### 8.4 `if` como expresión

```pengu
bind score = 95
bind category = if score >= 90
    "excelente"
elseif score >= 60
    "aprobado"
else
    "reprobado"
```

Forma inline:

```pengu
bind n = 7
bind parity = if n % 2 == 0 then "par" else "impar"
```

Reglas:

1. La condición debe ser `Bool`; no hay truthiness (`PGS-E9301`).
2. Las ramas deben unificar en un tipo común (`PGS-E6002`). Si una rama es
   `Never`, no participa en la unificación.
3. Sin `else`, el tipo es `Unit` y las ramas con valor deben descartarlo.
4. `elseif` encadena condiciones; `else` es la rama final.
5. `if` se puede usar como sentencia; en ese caso el valor se descarta.
6. `unless` es azúcar de `if not` y se define en §13.

Rust generado:

```rust
fn main() {
    let score = 95;
    let category = if score >= 90 {
        "excelente"
    } else if score >= 60 {
        "aprobado"
    } else {
        "reprobado"
    };
    let n = 7;
    let parity = if n % 2 == 0 { "par" } else { "impar" };
    println!("{category} {parity}");
}
```

### 8.5 `match` como expresión

```pengu
bind area = match shape
    when Circle(r) then 3.141592653589793 * r * r
    when Rectangle(w, h) then w * h
```

Reglas:

1. `match` evalúa el scrutinee una vez y elige el primer brazo cuyo patrón
   coincide.
2. Todos los brazos deben unificar en un tipo (`PGS-E6002`).
3. El `match` debe ser exhaustivo (`PGS-E6008`); §30 define patrones y
   guardas.
4. No hay fallthrough: cada brazo es independiente.
5. `match` se puede usar como sentencia; el valor se descarta.

Rust generado:

```rust
enum Shape {
    Circle(f64),
    Rectangle(f64, f64),
}

fn area(shape: Shape) -> f64 {
    match shape {
        Shape::Circle(r) => 3.141592653589793 * r * r,
        Shape::Rectangle(w, h) => w * h,
    }
}
```

### 8.6 Bucles

#### `loop`

```pengu
bind result = loop
    bind value = read()
    if value > 0
        break value
```

- `loop` sin `break` tiene tipo `Never`.
- `break expr` produce el valor del `loop`.
- `break` sin expresión produce `Unit`.
- `continue` salta a la siguiente iteración.

#### `while`

```pengu
while condition
    tick()
```

- La condición debe ser `Bool`.
- El tipo es `Unit`; no produce valor.
- `break` y `continue` son válidos dentro del cuerpo.

#### `for`

```pengu
for item in items
    process(item)
```

- Itera sobre un valor que implementa `IntoIterator` (§49).
- El tipo es `Unit`; no produce valor.
- El patrón del `for` puede ser destructivo (`for (k, v) in map`).
- `break` y `continue` son válidos dentro del cuerpo.

### 8.7 Control de flujo y `Never`

`Never` es el tipo de las expresiones que no retornan normalmente:

| Expresión | Tipo | Restricción |
|---|---|---|
| `return expr?` | `Never` | solo dentro de una función, lambda o `grimoire` |
| `break expr?` | `Never` | solo dentro de un bucle; `break expr` solo en `loop` |
| `continue` | `Never` | solo dentro de un bucle |
| `panic(msg)` | `Never` | siempre disponible |
| `loop` sin `break` | `Never` | — |

Reglas:

1. `Never` se coacciona a cualquier tipo. Esto permite:
   ```pengu
   bind x = if condition then 1 else return 0
   ```
2. `return` dentro de una lambda retorna de la lambda, no de la función
   contenedora.
3. `break expr` solo es válido en un `loop`; en `while`/`for` el `break` no lleva
   valor (`PGS-E6005`).
4. El código después de una expresión `Never` es inalcanzable; el compilador
   emite un warning (`PGS-W6002`), no un error.
5. `panic` no se usa para errores recuperables; para eso está `!T` (§48).

### 8.8 Separadores, descarte y `Unit`

- Un `NEWLINE` separa sentencias. `;` también las separa en la misma línea.
- El `;` al final de una expresión descarta su valor y la convierte en sentencia.
- Una expresión en posición de sentencia cuyo tipo no es `Unit` produce un
  warning de valor no usado (`PGS-W6001`), salvo que sea `Never`.
- `Unit` tiene un único valor: `()`.
- `bind _ = expr` descarta explícitamente el valor y evita el warning.
- Los paréntesis agrupan; no crean una tupla salvo que haya una coma.

### 8.9 Ejemplo ejecutable

```pengu
grimoire
    bind value = if true
        10
    else
        20

    bind label = do
        bind base = "value"
        base

    bind result = loop
        break value + 1

    print(label)
    print(result)
```

Rust generado:

```rust
fn main() {
    let value = if true { 10 } else { 20 };

    let label = {
        let base = "value";
        base
    };

    let result = loop {
        break value + 1;
    };

    println!("{}", label);
    println!("{}", result);
}
```

El ejemplo completo está en
[`scratch/examples/sec08_expressions.pengu`](../scratch/examples/sec08_expressions.pengu)
y su traducción en
[`scratch/examples/sec08_expressions.rs`](../scratch/examples/sec08_expressions.rs).

### 8.10 Diagnósticos

| Código | Condición | Sugerencia |
|---|---|---|
| `PGS-E6001` | `bind`/`morph`/asignación en posición de expresión | sacarlo a una sentencia |
| `PGS-E6002` | ramas o brazos con tipos incompatibles | unificar el tipo o añadir `Never` |
| `PGS-E6003` | `return` fuera de función/lambda | moverlo dentro |
| `PGS-E6004` | `break`/`continue` fuera de un bucle | moverlo dentro |
| `PGS-E6005` | `break expr` en `while`/`for` | usar `loop` o `break` sin valor |
| `PGS-E6006` | `do` sin bloque | indentar el cuerpo |
| `PGS-E6008` | `match` no exhaustivo | añadir brazos o un comodín |
| `PGS-W6001` | valor de expresión no usado | usar `bind _ =` o consumir el valor |
| `PGS-W6002` | código inalcanzable | eliminar o reestructurar |

### 8.11 Criterios de aceptación

- [x] Se distingue expresión de sentencia y se prohíbe la asignación como
      expresión.
- [x] `if`, `match`, `loop`, `do` y los bloques producen valores.
- [x] `while`/`for` son `Unit`; `loop` puede producir valor.
- [x] `return`/`break`/`continue`/`panic` son `Never` y tienen restricciones.
- [x] El descarte, el `;` y `Unit` están definidos.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="part-2"></a>
## Parte II — Núcleo del lenguaje

<a id="sec-09-primitivos"></a>
## 9. Tipos primitivos

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 2 |
| Rust | `()`, `!`, `bool`, enteros, `f32`, `f64`, `char`, `str` |
| Palabras mágicas | — |
| Depende de | §4, §10 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec09_primitives.pengu` |

PenguScript no inventa una representación numérica: usa exactamente los tipos
primitivos de Rust y les da nombres legibles. La regla de oro es **no ocultar el
ancho**. `Int` y `Float` son cómodos para el código diario; los tipos con ancho
explícito se usan cuando el tamaño importa (ABI, archivos, protocolos, FFI).

### 9.1 Unit y Never

| PenguScript | Rust | Valores | Uso |
|---|---|---|---|
| `Unit` | `()` | uno: `()` | funciones y bloques sin valor |
| `Never` | `!` | ninguno | divergencia: `panic`, `return`, `break` |

`Unit` es el tipo de las funciones que no devuelven nada, de `while`/`for` y de
un bloque cuya última línea es una sentencia. `Never` es el tipo de las
expresiones que no terminan normalmente; se coacciona a cualquier tipo (§8).

```pengu
noop = () -> Unit
    ()

fail = (message: &Str) -> Never
    panic(message)
```

Rust generado:

```rust
fn noop() -> () {
    ()
}

fn fail(message: &str) -> ! {
    panic!("{}", message)
}
```

`Never` no se puede construir con un valor. Un `match` sin brazos, un `loop` sin
`break` o una llamada a `panic` producen `Never`.

### 9.2 Booleanos

`Bool` tiene exactamente dos valores: `true` y `false`. No hay truthiness: `0`,
`""`, `none` y los punteros nulos **no** son `Bool` (§12).

```pengu
bind enabled: Bool = true
bind visible = enabled and not false
```

`Bool` ocupa un byte en Rust; su tamaño no se especifica en la spec, pero el
codegen usa `bool`. Las operaciones permitidas se detallan en §12.

### 9.3 Enteros con signo

| Tipo | Rust | Rango |
|---|---|---|
| `I8` | `i8` | −128 a 127 |
| `I16` | `i16` | −32 768 a 32 767 |
| `I32` | `i32` | −2 147 483 648 a 2 147 483 647 |
| `I64` | `i64` | −2⁶³ a 2⁶³ − 1 |
| `I128` | `i128` | −2¹²⁷ a 2¹²⁷ − 1 |
| `Isize` | `isize` | depende del ancho del puntero del target |

`Isize` es el tipo con signo del tamaño de un puntero. No se garantiza que sea
de 64 bits: en un target de 32 bits es de 32 bits. Para índices se prefiere
`Usize`; para valores de dominio se prefieren tipos de ancho fijo.

### 9.4 Enteros sin signo

| Tipo | Rust | Rango |
|---|---|---|
| `U8` | `u8` | 0 a 255 |
| `U16` | `u16` | 0 a 65 535 |
| `U32` | `u32` | 0 a 4 294 967 295 |
| `U64` | `u64` | 0 a 2⁶⁴ − 1 |
| `U128` | `u128` | 0 a 2¹²⁸ − 1 |
| `Usize` | `usize` | depende del ancho del puntero del target |

`Usize` es el tipo de índices y longitudes de Rust. Un `Int` **no** se convierte
implícitamente en `Usize`: para indexar se usa `Usize` o una conversión explícita
(§9.13).

### 9.5 Alias cómodos: `Int`, `UInt`, `Float`

| Alias | Tipo real | Cuándo usarlo |
|---|---|---|
| `Int` | `I32` | enteros corrientes, contadores, valores pequeños |
| `UInt` | `U32` | cantidades no negativas corrientes |
| `Float` | `F64` | cálculo en coma flotante de doble precisión |

Los alias son **transparentes**: `Int` y `I32` son el mismo tipo. La anotación
`bind x: Int` genera `let x: i32`. La ventaja de `Int` es la legibilidad; la
ventaja de `I8`/`U64` es la precisión del contrato.

Regla: si un valor cruza una frontera de ABI, se serializa o se pasa a Rust, se
usa el tipo de ancho explícito. `Int` no promete 32 bits en una ABI; solo es un
alias de `I32` dentro del lenguaje.

### 9.6 Flotantes

| Tipo | Rust | Precisión |
|---|---|---|
| `F32` | `f32` | IEEE 754 binario32 |
| `F64` | `f64` | IEEE 754 binario64 |

`Float` es alias de `F64`. Los flotantes siguen IEEE 754: `NaN` no es igual a sí
mismo, `0.0` y `-0.0` se comparan iguales, y `inf`/`-inf` son valores válidos.
No se usa `==` para comparar flotantes con tolerancia; para eso se define una
función de épsilon en la biblioteca.

No hay `f16`, `f128` ni `Decimal` en el núcleo. Esos tipos, si existen, vienen de
un `tome` y se documentan en §26.

### 9.7 `Char`

`Char` es un **escalar Unicode** válido: un número en `0..=0x10FFFF` que no sea
un surrogate (`0xD800..=0xDFFF`). Ocupa 4 bytes en Rust.

```pengu
bind penguin: Char = '🐧'
bind newline: Char = '\n'
bind letter: U8 = b'P'
```

- Las comillas simples delimitan un `Char`: `'a'`, `'\n'`, `'\u{1F427}'`.
- `b'P'` es un **byte** (`U8`), no un `Char`.
- Un literal con más de un escalar es error (`PGS-E9004`).
- `Char` no es un string de longitud uno; para eso se usa `&Str`.

### 9.8 `Str`

`Str` es el tipo de los strings UTF-8 **no sizeados**. En la práctica aparece
siempre detrás de una referencia o dentro de un contenedor:

| Forma | Rust | Dueño |
|---|---|---|
| `&Str` | `&str` | no; préstamo |
| `String` | `String` | sí |
| `Cow[Str]` | `Cow<'_, str>` | a veces |

No se puede declarar un `bind x: Str = ...` por valor: `Str` no tiene tamaño
conocido y el compilador lo rechaza (`PGS-E9005`). Se usa `&Str`, `String` o
`Cow[Str]`. §10 cubre literales, métodos y conversiones.

### 9.9 Literales y sufijos

| Forma | Ejemplos | Tipo por defecto |
|---|---|---|
| Entero decimal | `0`, `42`, `1_000_000` | `Int` (`I32`) |
| Entero hexadecimal | `0xFF`, `0xdead_beef` | `Int` |
| Entero octal | `0o755` | `Int` |
| Entero binario | `0b1010_0101` | `Int` |
| Entero con sufijo | `42_i32`, `255_u8`, `1_000_usize` | el del sufijo |
| Flotante | `1.0`, `3.141_592`, `1.5e-3` | `Float` (`F64`) |
| Flotante con sufijo | `1.0_f32`, `2.5_f64` | el del sufijo |
| Booleano | `true`, `false` | `Bool` |
| Carácter | `'a'`, `'\n'`, `'🐧'` | `Char` |
| Byte | `b'a'`, `b'\n'` | `U8` |
| String | `"pengu"`, `"hola #{name}"` | `&Str` |

Reglas:

1. El sufijo es obligatorio solo cuando no hay anotación ni contexto que fije
   un ancho distinto del alias por defecto. `42_u8` es un `U8`; `42` es un
   `Int`; `bind b: U8 = 1` también es `U8`.
2. El sufijo debe ser un tipo entero o flotante conocido (`i8`…`u128`, `isize`,
   `usize`, `f32`, `f64`). Un sufijo incompatible es error (`PGS-E9002`).
3. Los guiones bajos son separadores visuales; no cambian el valor. No pueden
   aparecer al inicio ni al final, ni duplicarse (`PGS-E9003`).
4. Un literal entero fuera del rango de su tipo es error de compilación
   (`PGS-E9001`).
5. No hay literales octales con signo ni literales binarios con prefijo `0B`.
6. El signo `-` es un operador unario, no parte del literal. `-128_i8` es válido;
   `128_i8` no lo es.

```pengu
bind decimal = 42
bind hex = 0x2A
bind octal = 0o52
bind binary = 0b10_1010
bind small: U8 = 42_u8
bind ratio: F32 = 1.5_f32
bind penguin: Char = '🐧'
bind flag: Bool = true
```

### 9.10 Inferencia y defaults

La inferencia es local y bidireccional (§4.5). Para literales numéricos:

1. Si hay una anotación o un contexto que fija el tipo, se usa ese tipo.
2. Si no hay contexto, un entero sin sufijo es `Int` (`I32`) y un flotante es
   `Float` (`F64`).
3. Un sufijo siempre gana sobre el default, pero no sobre una anotación
   incompatible.
4. No se elige un tipo menor por el valor. `bind x = 1` es `Int`, no `U8`.

```pengu
bind a = 1              -- Int
bind b: U8 = 1          -- U8
bind c = 1_u8           -- U8
bind d = 1.0            -- Float
bind e: F32 = 1.0       -- F32
```

Un literal no se convierte implícitamente a otro tipo:

```pengu
bind a: U8 = 1
bind b: U16 = a         -- error: U8 no es U16
bind c = a as U16       -- conversión explícita
```

### 9.11 Overflow, división y shifts

El codegen activa `overflow-checks = true` en todos los perfiles. Por eso las
operaciones aritméticas **panican** al desbordar, en debug y en release. Esto es
deliberado: un desbordamiento silencioso es un error de seguridad, no una
optimización.

| Operación | Comportamiento |
|---|---|
| `a + b`, `a - b`, `a * b` | panic si el resultado no cabe |
| `a / b` | panic si `b == 0` |
| `a % b` | panic si `b == 0` |
| `MIN / -1` | panic por overflow |
| `a << b`, `a >> b` | panic si `b >=` ancho de `a` |
| `a.abs()` | panic si `a` es el mínimo con signo |
| `a.pow(n)` | panic si el resultado no cabe |

Los literales constantes se comprueban en compilación. Una expresión que puede
desbordar en runtime se detecta con las operaciones explícitas de §9.12.

### 9.12 Operaciones checked, wrapping y saturating

Para cada tipo entero, la prelude expone los mismos métodos que Rust:

| Familia | Resultado | Uso |
|---|---|---|
| `checked_add`, `checked_sub`, `checked_mul`, `checked_div`, `checked_rem`, `checked_neg`, `checked_shl`, `checked_shr` | `?T` | el llamador decide |
| `wrapping_add`, `wrapping_sub`, `wrapping_mul`, `wrapping_div`, `wrapping_rem`, `wrapping_neg`, `wrapping_shl`, `wrapping_shr` | `T` | aritmética modular explícita |
| `saturating_add`, `saturating_sub`, `saturating_mul`, `saturating_div`, `saturating_pow` | `T` | se queda en el mínimo/máximo |
| `overflowing_add`, `overflowing_sub`, `overflowing_mul` | `(T, Bool)` | valor + indicador |

```pengu
bind a: U8 = 250
bind checked = a.checked_add(10)      -- none
bind wrapped = a.wrapping_add(10)     -- 4
bind saturated = a.saturating_add(10) -- 255
```

`checked_*` devuelve `?T`, no un `Bool` ni un valor centinela. Para usar el
resultado hay que desenvolverlo (§48):

```pengu
bind next = a.checked_add(1)?
```

El `?` solo es válido dentro de una función que devuelve `?T`/`!T` o en un
contexto que lo permita; §48 lo formaliza.

### 9.13 Casts numéricos con `as`

`as` es una conversión **explícita** y puede perder información. No hay casts
implícitos entre tipos numéricos.

| Origen | Destino | Semántica |
|---|---|---|
| entero | entero | trunca o extiende según Rust |
| entero | flotante | redondeo al más cercano representable |
| flotante | entero | satura a `MIN`/`MAX` y `NaN` a `0` (Rust) |
| `Char` | `U32` | valor escalar |
| `U8` | `Char` | byte ASCII; otros valores son error en runtime |
| `Bool` | entero | **no permitido** |
| `&Str` | `Str`/`String` | **no** con `as`; usar §10 |

```pengu
bind big: I64 = 300
bind small = big as U8        -- 44 (truncado)
bind back = small as I64      -- 44
bind code = 'A' as U32        -- 65
```

`as` no comprueba el rango. Para una conversión segura se usa `try_into()`:

```pengu
bind small = big.try_into()?  -- !U8
```

`try_into` devuelve `!T`; el `?` propaga el error. La conversión segura es la
forma recomendada cuando el valor viene de fuera del programa.

### 9.14 `NonZero`

Los tipos `NonZeroI8`…`NonZeroI128`, `NonZeroIsize`, `NonZeroU8`…`NonZeroU128` y
`NonZeroUsize` garantizan que el valor no es cero. Rust los usa para niche
optimization: `?NonZeroU32` ocupa el mismo espacio que `U32`.

```pengu
bind id = NonZeroU32.new(7)          -- ?NonZeroU32
bind raw = id.unwrap().get()         -- U32
bind checked = NonZeroU32.new(0)     -- none
```

Reglas:

1. `new` devuelve `?T`; no panica.
2. `get()` devuelve el entero subyacente.
3. `new_unchecked` solo existe dentro de `curse` (§52) y es responsabilidad del
   llamador.
4. `NonZero` no cambia el ancho; `NonZeroU8` sigue siendo un byte.

### 9.15 Ejemplo completo

```pengu
grimoire
    bind count: Int = 42
    bind mask: UInt = 0xFF
    bind ratio: Float = 1.5
    bind letter: Char = 'P'
    bind name: &Str = "pengu"

    bind total = count + 1
    bind wrapped = mask.wrapping_add(1)
    bind checked = count.checked_add(1)

    print(total)
    print(wrapped)
    print(checked.unwrap_or(0))
    print(ratio)
    print(letter)
    print(name)
```

Rust generado:

```rust
fn main() {
    let count: i32 = 42;
    let mask: u32 = 0xFF;
    let ratio: f64 = 1.5;
    let letter: char = 'P';
    let name: &str = "pengu";

    let total = count + 1;
    let wrapped = mask.wrapping_add(1);
    let checked = count.checked_add(1);

    println!("{}", total);
    println!("{}", wrapped);
    println!("{}", checked.unwrap_or(0));
    println!("{}", ratio);
    println!("{}", letter);
    println!("{}", name);
}
```

La salida es `43`, `256`, `43`, `1.5`, `P`, `pengu`.

### 9.16 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9001` | literal entero fuera de rango | usar un tipo más ancho o corregir el valor |
| `PGS-E9002` | sufijo incompatible con el tipo | cambiar sufijo o anotación |
| `PGS-E9003` | separador `_` mal colocado | quitar o recolocar el separador |
| `PGS-E9004` | literal `Char` con más de un escalar | usar un string o un solo carácter |
| `PGS-E9005` | `Str` por valor | usar `&Str`, `String` o `Cow[Str]` |
| `PGS-E9006` | overflow aritmético | usar `checked_*`, `wrapping_*` o `saturating_*` |
| `PGS-E9007` | división o resto por cero | comprobar el divisor o usar `checked_div` |
| `PGS-E9008` | shift mayor o igual que el ancho | comprobar el shift o usar `checked_shl` |
| `PGS-E9009` | cast `as` no permitido | usar una conversión explícita de §10/§32 |
| `PGS-E9010` | `NonZero.new(0)` no comprobado | usar `?`, `match` o `unwrap_or` antes de usarlo como `NonZero` |
| `PGS-W9001` | cast que puede perder información | usar `try_into()` si el rango no es fijo |

### 9.17 Criterios de aceptación

- [x] Todos los tipos primitivos tienen mapeo a Rust y ejemplo.
- [x] `Int`, `UInt` y `Float` están definidos como alias, no como tipos nuevos.
- [x] La inferencia por defecto y los sufijos están especificados.
- [x] El comportamiento de overflow es explícito y seguro por defecto.
- [x] `Char`, `Str` y `String` se distinguen sin ambigüedad.
- [x] `NonZero` y los casts tienen reglas y diagnósticos.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="sec-10-strings"></a>
## 10. Strings y chars

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 2 |
| Rust | `str`, `String`, `char`, `Cow`, `OsString`, `Path`, `CString` |
| Palabras mágicas | — |
| Depende de | §2, §4, §9 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec10_strings.pengu` |

Un string de PenguScript es siempre UTF-8 válido. No hay strings “binarios” que
se puedan imprimir como texto: para bytes están `[U8]`, `Vec[U8]` y los tipos de
§22/§23. `Char` es un escalar Unicode, no un byte.

### 10.1 `Str` frente a `String`

| Tipo | Rust | Tamaño | Dueño | Uso |
|---|---|---|---|---|
| `Str` | `str` | no sizeado | no | parámetros y vistas |
| `&Str` | `&str` | préstamo | no | texto prestado |
| `String` | `String` | 24 bytes en 64-bit | sí | texto propio y mutable |
| `Cow[Str]` | `Cow<'_, str>` | variable | a veces | préstamo o copia |

`Str` no se puede usar por valor; siempre es `&Str` o forma parte de `String` y
`Cow`. Un literal de string tiene tipo `&Str` con lifetime `'static`.

```pengu
greet = (name: &Str) -> String
    "hola, #{name}"
```

El parámetro pide prestado; el retorno es propio. Esta es la firma por defecto
para funciones que construyen texto.

### 10.2 Literales y escapes

| Forma | Ejemplo | Resultado |
|---|---|---|
| Normal | `"hola"` | `&Str` |
| Triple | `"""línea 1\nlínea 2"""` | `&Str` con saltos reales |
| Raw | `r"a\b"` | `&Str` sin escapes |
| Raw con hash | `r#"puede contener "comillas""#` | `&Str` sin escapes |
| Byte | `b"abc"` | `&[U8; N]` |
| Byte char | `b'a'` | `U8` |
| C | `c"hola"` | `&CStr` |
| Con interpolación | `"hola, #{name}"` | `String` |

Escapes normales:

| Escape | Significado |
|---|---|
| `\n` | salto de línea |
| `\r` | retorno de carro |
| `\t` | tabulación |
| `\\` | barra invertida |
| `\"` | comilla doble |
| `\'` | comilla simple (en un `Char`) |
| `\0` | NUL (solo en byte/C strings; no en UTF-8 de texto) |
| `\xNN` | byte `NN` (solo byte strings) |
| `\u{...}` | escalar Unicode (1–6 dígitos hex) |

Reglas:

1. Un string normal no puede contener un salto de línea sin escapar; para eso se
   usa triple o `\n`.
2. `\u{...}` debe ser un escalar Unicode válido; un surrogate es error
   (`PGS-E9102`).
3. Los raw strings no procesan escapes ni interpolación.
4. Un string C no puede contener un NUL interior (`PGS-E9109`).
5. La interpolación `#{expr}` solo se procesa en strings normales. Para incluir
   `#{` literal se escribe `\#{`.
6. Un string sin cerrar es error léxico (`PGS-E1007`).

### 10.3 Interpolación y `format`

`"hola, #{name}"` es azúcar de `format("hola, #{name}")`. La expresión dentro de
`#{}` se evalúa y se formatea con `Display`; no se permiten especificadores de
formato dentro de `#{}` en el núcleo.

```pengu
bind name = "pengu"
bind count = 3
bind message = "hola, #{name}: #{count} mensajes"
```

Rust generado:

```rust
let name = "pengu";
let count = 3;
let message = format!("hola, {}: {} mensajes", name, count);
```

`format` también se puede llamar directamente:

```pengu
bind message = format("hola, #{name}")
```

`format` devuelve `String`; `print` escribe el valor con `Display` y añade un
salto de línea. Para depuración se usa `dbg`, que requiere `Debug` (§56).

### 10.4 Concatenación y construcción

| Operación | PenguScript | Rust | Notas |
|---|---|---|---|
| Concatenar propio + prestado | `a + b` | `a + b` | solo `String + &Str` |
| Concatenar dos prestados | `format("#{a}#{b}")` | `format!("{}{}", a, b)` | no hay `+` |
| Añadir al final | `s.push_str(t)` | `s.push_str(t)` | muta `String` |
| Añadir un char | `s.push(c)` | `s.push(c)` | muta `String` |
| Unir colección | `parts.join(", ")` | `parts.join(", ")` | `Vec[String]`/`Vec[&Str]` |
| Repetir | `s.repeat(n)` | `s.repeat(n)` | devuelve `String` |

`+` solo existe para `String + &Str`. `Str + Str` no compila
(`PGS-E9106`); usar `format` o `join`. La concatenación repetida en un bucle es
O(n²); para construir texto se usa `String` con `push_str` o `join`.

```pengu
morph out = String.new()
out.push_str("hola")
out.push(',')
out.push_str(" pengu")
print(out)
```

Rust generado:

```rust
let mut out = String::new();
out.push_str("hola");
out.push(',');
out.push_str(" pengu");
println!("{}", out);
```

### 10.5 Indexación y slicing

**No hay indexación por entero.** `s[0]` es error (`PGS-E9104`). Un string UTF-8
no tiene “carácter en la posición 0” en tiempo O(1), y permitir `s[0]` invitaría
a cortar un carácter multibyte.

Alternativas:

| Necesidad | Forma | Complejidad |
|---|---|---|
| carácter por posición | `s.chars().nth(i)` → `?Char` | O(n) |
| posición y carácter | `s.char_indices().nth(i)` → `?(Usize, Char)` | O(n) |
| recorrer caracteres | `for c in s.chars()` | O(n) |
| bytes | `s.bytes()` / `s.as_bytes()` | O(1) por byte |
| subcadena por bytes | `s.get(a..b)` → `?&Str` | O(1), valida límites |
| subcadena por caracteres | `s.chars().skip(a).take(n).collect[String]()` | O(n) |

`s.get(a..b)` es la única forma de cortar por offsets de byte. Devuelve `none` si
`a` o `b` no están en un límite de carácter o si `a > b`; no panica.

```pengu
bind text = "pingüino"
bind first = text.chars().nth(0)       -- some('p')
bind slice = text.get(0..4)            -- some("ping")
bind broken = text.get(0..5)           -- none: 5 cae dentro de ü
```

Rust generado:

```rust
let text = "pingüino";
let first = text.chars().nth(0);
let slice = text.get(0..4);
let broken = text.get(0..5);
```

`len()` devuelve **bytes**, no caracteres. Para contar caracteres se usa
`chars().count()`. Para contar grafemas se necesita un crate de segmentación
(§26), porque Unicode no garantiza que un grafema sea un `Char`.

### 10.6 `Char`, bytes y UTF-8

| Operación | Ejemplo | Tipo |
|---|---|---|
| Longitud UTF-8 de un char | `'á'.len_utf8()` | `Usize` |
| Byte a char ASCII | `65_u8 as Char` | `Char` |
| Char a escalar | `'A' as U32` | `U32` |
| Iterar chars | `s.chars()` | `Iterator[Char]` |
| Iterar bytes | `s.bytes()` | `Iterator[U8]` |
| Reemplazar inválidos | `String.from_utf8_lossy(bytes)` | `Cow[Str]` |

`String` siempre contiene UTF-8 válido. Para construir desde bytes:

```pengu
bind bytes: [U8; 5] = [104, 111, 108, 97, 33]
bind text = String.from_utf8(bytes)?       -- !String
bind lossy = String.from_utf8_lossy(bytes) -- Cow[Str]
```

`from_utf8` devuelve `!String`; `from_utf8_lossy` sustituye secuencias inválidas
por `�` y devuelve `Cow[Str]`.

### 10.7 Métodos de `Str` y `String`

| Método | Devuelve | Notas |
|---|---|---|
| `len()` | `Usize` | bytes |
| `is_empty()` | `Bool` | — |
| `chars()` | `Iterator[Char]` | escalares |
| `bytes()` | `Iterator[U8]` | bytes |
| `char_indices()` | `Iterator[(Usize, Char)]` | offset + char |
| `contains(pat)` | `Bool` | patrón `&Str`/`Char` |
| `starts_with(pat)` | `Bool` | — |
| `ends_with(pat)` | `Bool` | — |
| `find(pat)` | `?Usize` | offset de byte |
| `split(pat)` | `Iterator[&Str]` | — |
| `lines()` | `Iterator[&Str]` | sin `\n` |
| `trim()` | `&Str` | espacios Unicode |
| `to_lowercase()` | `String` | puede cambiar longitud |
| `to_uppercase()` | `String` | puede cambiar longitud |
| `replace(from, to)` | `String` | — |
| `repeat(n)` | `String` | — |
| `parse[T]()` | `!T` | `FromStr` |
| `to_string()` | `String` | copia |
| `as_str()` | `&Str` | vista de un `String` |

`to_lowercase`/`to_uppercase` no son simétricos para todos los caracteres; no se
usa para comparar identificadores. Para comparaciones sin mayúsculas se usa
`to_lowercase` explícitamente y se documenta la locale; el núcleo no tiene
collation.

### 10.8 Conversiones

| Desde | Hacia | Forma |
|---|---|---|
| `&Str` | `String` | `String.from(s)` o `s.to_string()` |
| `String` | `&Str` | `s.as_str()` o `&s` |
| `&Str` | `!T` | `s.parse[T]()` |
| `T: Display` | `String` | `format("#{value}")` |
| `String` | `Vec[U8]` | `s.into_bytes()` |
| `Vec[U8]` | `!String` | `String.from_utf8(bytes)?` |
| `&Str` | `Cow[Str]` | `Cow.borrowed(s)` |
| `String` | `Cow[Str]` | `Cow.owned(s)` |

`String.from` es la forma canónica de construir un `String` desde `&Str`;
`to_string` es el método de `Display` y se usa cuando el valor no es un string.

```pengu
bind owned: String = String.from("pengu")
bind view: &Str = owned.as_str()
bind number = "42".parse[Int]()?
bind bytes = owned.into_bytes()
```

### 10.9 `Cow`, `OsString`, `Path` y `CString`

Estos tipos son de la biblioteca estándar, no del núcleo del lenguaje. Se
documentan aquí porque aparecen en APIs reales; §26 y §53 los desarrollan.

| Tipo | Uso | Coste |
|---|---|---|
| `Cow[Str]` | prestar o poseer sin copiar siempre | copia solo al mutar |
| `OsString` | texto del sistema operativo, no necesariamente UTF-8 | específico de plataforma |
| `Path`/`PathBuf` | rutas del sistema de archivos | específico de plataforma |
| `CString` | string C terminado en NUL para FFI | valida NUL |

No se convierten implícitamente a `Str`. Una ruta no es un string de texto; para
mostrarla se usa `to_string_lossy()` y se acepta la pérdida.

### 10.10 `print` y `format`

`print(value)` escribe `value` con `Display` y un salto de línea. `format`
construye un `String` con el mismo formato. `dbg(value)` usa `Debug` y escribe
para diagnóstico; no forma parte de la salida del programa.

```pengu
print("hola")
print(42)
print('🐧')
print(format("x = #{1 + 2}"))
```

Rust generado:

```rust
println!("hola");
println!("42");
println!("🐧");
println!("x = {}", 1 + 2);
```

`print` no acepta un `String` por movimiento si se necesita después; toma el
valor por referencia en el codegen cuando es posible. Las reglas de ownership
son las de §16.

### 10.11 Ejemplo completo

```pengu
grimoire
    bind name: String = String.from("pengu")
    bind greeting = "hola, #{name}"
    bind chars = name.chars().count()
    bind bytes = name.len()
    bind upper = name.to_uppercase()

    print(greeting)
    print(chars)
    print(bytes)
    print(upper)
```

Rust generado:

```rust
fn main() {
    let name: String = String::from("pengu");
    let greeting = format!("hola, {}", name);
    let chars = name.chars().count();
    let bytes = name.len();
    let upper = name.to_uppercase();

    println!("{}", greeting);
    println!("{}", chars);
    println!("{}", bytes);
    println!("{}", upper);
}
```

La salida es `hola, pengu`, `5`, `5`, `PENGU`.

### 10.12 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9101` | `Str` usado por valor | usar `&Str`, `String` o `Cow[Str]` |
| `PGS-E9102` | escape Unicode inválido | usar un escalar válido |
| `PGS-E9103` | interpolación sin cerrar | cerrar `#{...}` |
| `PGS-E9104` | índice entero sobre string | usar `chars().nth` o `get` |
| `PGS-E9105` | rango fuera de límite de carácter | usar `get` y comprobar `none` |
| `PGS-E9106` | `Str + Str` | usar `format` o `join` |
| `PGS-E9107` | `parse` fallido | devolver `!T` o usar `unwrap_or` |
| `PGS-E9108` | bytes no UTF-8 | usar `from_utf8` y `?`, o `from_utf8_lossy` |
| `PGS-E9109` | NUL interior en string C | quitar el NUL o usar `[U8]` |
| `PGS-E9110` | `String` mutado mientras está prestado | terminar el préstamo o clonar |
| `PGS-W9101` | indexación por carácter en bucle | cachear `chars()` o usar `char_indices()` |

### 10.13 Criterios de aceptación

- [x] `Str`, `&Str` y `String` tienen dueño y tamaño explícitos.
- [x] Los literales normal, triple, raw, byte y C están cubiertos.
- [x] La interpolación se desazucara a `format!`.
- [x] No hay indexación por entero; el slicing seguro usa `get`.
- [x] `len()` se define en bytes y `chars().count()` en caracteres.
- [x] Las conversiones y los diagnósticos están definidos.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="sec-11-operadores"></a>
## 11. Operadores

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 2 |
| Rust | Operadores de Rust; `contains`, `as`, `?`, `.await` |
| Palabras mágicas | `and`, `or`, `not`, `is`, `isnt`, `in`, `as`, `awaken` |
| Depende de | §8, §9, §10 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec11_operators.pengu` |

Los operadores de PenguScript son los de Rust, con dos concesiones a
MoonScript: `and`/`or`/`not` en lugar de `&&`/`||`/`!` para lógica, e
`is`/`isnt` como alias legibles de `==`/`!=`. No hay sobrecarga definida por el
usuario en esta sección; §40 explica cómo un `ritual` implementa los traits de
operador.

### 11.1 Tabla de precedencia

De mayor a menor. Todos los operadores de un mismo nivel asocian a la izquierda
salvo los indicados.

La tabla **normativa** es §62.1; esta es su forma resumida.

| Nivel | Operadores | Asociatividad | Produce |
|---|---|---|---|
| 1 | `.` campo/método, `()` llamada, `[]` índice, `?` postfix, turbofish | izquierda | según el operando |
| 2 | `awaken` (prefijo) | derecha | `T` de `Future[T]` |
| 3 | `-` `+` `!` `*` `&` `&mut` (prefijos) | derecha | según el operando |
| 4 | `as` | izquierda | tipo destino |
| 5 | `*` `/` `%` | izquierda | numérico |
| 6 | `+` `-` | izquierda | numérico o string |
| 7 | `<<` `>>` | izquierda | entero |
| 8 | `&` | izquierda | entero o `Bool` |
| 9 | `^` | izquierda | entero o `Bool` |
| 10 | `\|` | izquierda | entero o `Bool` |
| 11 | `..` `..=` | no asociativo | rango |
| 12 | `==` `!=` `<` `<=` `>` `>=` `is` `isnt` `in` | no asociativo | `Bool` |
| 13 | `not` (prefijo) | derecha | `Bool` |
| 14 | `and` | izquierda, cortocircuito | `Bool` |
| 15 | `or` | izquierda, cortocircuito | `Bool` |
| 16 | `=` `+=` `-=` `*=` `/=` `%=` `&=` `\|=` `^=` `<<=` `>>=` | derecha; sentencia | sentencia, no usable como valor |

Consecuencias que conviene memorizar:

- `2 + 3 * 4` es `2 + (3 * 4)`.
- `0..n + 1` es `0..(n + 1)`, porque `+` tiene más precedencia que `..`.
- `not a == b` es `not (a == b)`, porque `not` está por debajo de comparación.
- `a and b or c` es `(a and b) or c`.
- `x = y = z` no es válido: la asignación no es expresión y no asocia.
- `a < b < c` no es válido: las comparaciones no encadenan. Se escribe
  `a < b and b < c`.

### 11.2 Aritméticos

| Operador | Tipos | Rust | Notas |
|---|---|---|---|
| `+` | enteros, flotantes | `+` | también `String + &Str` |
| `-` | enteros, flotantes | `-` | binario y unario |
| `*` | enteros, flotantes | `*` | — |
| `/` | enteros, flotantes | `/` | división entera trunca hacia cero |
| `%` | enteros, flotantes | `%` | resto; signo del dividendo |
| `-` unario | enteros, flotantes | `-` | `-x` |

La aritmética entera panica al desbordar y al dividir por cero (§9.11). La
división entera trunca hacia cero: `-7 / 2 == -3`, `-7 % 2 == -1`. Para
aritmética modular explícita se usan `wrapping_*`; para saturación,
`saturating_*`; para detectar, `checked_*`.

`+` con strings solo existe como `String + &Str` (§10.4). `Str + Str` es error.

### 11.3 Comparación e igualdad

| Operador | Significado | Requisito |
|---|---|---|
| `==` | igualdad | `PartialEq` |
| `!=` | desigualdad | `PartialEq` |
| `<` `<=` `>` `>=` | orden | `PartialOrd` |
| `is` | alias de `==` | `PartialEq` |
| `isnt` | alias de `!=` | `PartialEq` |

`is` e `isnt` son **azúcar de igualdad**, no identidad de referencia. Dos
`String` con el mismo contenido son `is`; dos referencias al mismo valor también.
No hay `===` ni `!==`.

```pengu
bind same = "pengu" is "pengu"     -- true
bind different = 1 isnt 2          -- true
```

Rust generado:

```rust
let same = "pengu" == "pengu";
let different = 1 != 2;
```

Las comparaciones no encadenan. `a < b < c` es error de tipo
(`PGS-E9203`), porque `a < b` es `Bool` y `Bool < c` no existe.

### 11.4 Lógicos

| Operador | Tipos | Rust | Cortocircuito |
|---|---|---|---|
| `and` | `Bool` | `&&` | sí |
| `or` | `Bool` | `\|\|` | sí |
| `not` | `Bool` | `!` | — |
| `!` prefijo | `Bool` o entero | `!` | — |

`and` y `or` solo aceptan `Bool`; no hay truthiness. El lado derecho no se evalúa
si el izquierdo decide el resultado:

```pengu
bind ok = is_ready() and side_effect()
bind fallback = is_ready() or side_effect()
```

Rust generado:

```rust
fn is_ready() -> bool { true }
fn side_effect() -> bool { true }
let ok = is_ready() && side_effect();
let fallback = is_ready() || side_effect();
```

No se aceptan `&&` ni `||` como alias: la forma canónica es `and`/`or`. `!` sí
se acepta como negación lógica de `Bool` y como complemento bit a bit de enteros;
`not` es el nombre legible para `Bool`.

### 11.5 Bitwise

| Operador | Tipos | Rust | Notas |
|---|---|---|---|
| `&` | enteros, `Bool` | `&` | AND bit a bit |
| `\|` | enteros, `Bool` | `\|` | OR bit a bit |
| `^` | enteros, `Bool` | `^` | XOR bit a bit |
| `<<` | enteros | `<<` | panic si el shift es ≥ ancho |
| `>>` | enteros | `>>` | shift aritmético para signed |
| `!` prefijo | enteros | `!` | complemento a uno |

`&`, `|` y `^` sobre `Bool` **no** cortocircuitan; para lógica se usan
`and`/`or`. El shift con cantidad negativa es error de tipo; con cantidad mayor o
igual al ancho panica (`PGS-E9008`).

```pengu
bind flags = 0b1010 & 0b0110       -- 0b0010
bind mask = 0b0001 | 0b1000        -- 0b1001
bind toggle = 0b1010 ^ 0b0011      -- 0b1001
bind shift = 1 << 3                -- 8
```

### 11.6 Rangos

| Forma | Significado | Rust |
|---|---|---|
| `a..b` | `a` inclusive, `b` exclusivo | `a..b` |
| `a..=b` | ambos inclusive | `a..=b` |

`..` no asocia: `a..b..c` es error. `..` con `..=` mezclados también. Los rangos
se usan en `for`, en `in` y como valores de tipo `Range[T]`/`RangeInclusive[T]`
(§27).

```pengu
bind digits = 0..10
bind inclusive = 0..=9
bind has_five = 5 in 0..10
```

### 11.7 `in`

`x in collection` comprueba pertenencia y produce `Bool`.

| Colección | Rust |
|---|---|
| array, slice, `Vec[T]` | `collection.contains(&x)` |
| rango | `range.contains(&x)` |
| `HashMap` | `map.contains_key(&x)` |
| `HashSet` | `set.contains(&x)` |
| string | `s.contains(x)` (substring) |

`in` no itera; es una comprobación. Para recorrer se usa `for` (§14). La
pertenencia usa `PartialEq`; en mapas y sets usa `Eq`/`Hash`.

```pengu
bind present = 3 in [1, 2, 3]
bind inside = 'p' in "pengu"
```

Rust generado:

```rust
let present = [1, 2, 3].contains(&3);
let inside = "pengu".contains('p');
```

### 11.8 Referencia, deref y acceso

| Forma | Significado | Rust |
|---|---|---|
| `&expr` | préstamo compartido | `&expr` |
| `&mut expr` | préstamo mutable | `&mut expr` |
| `*expr` | deref | `*expr` |
| `expr.field` | campo | `expr.field` |
| `expr.method(args)` | método | `expr.method(args)` |
| `expr[index]` | índice | `expr[index]` |
| `expr(args)` | llamada | `expr(args)` |
| `expr?` | propagación | `expr?` |
| `awaken expr` | await | `expr.await` |

`&`/`&mut` y `*` se desarrollan en §17–§19. `?` se desarrolla en §48. `awaken`
se desarrolla en §50. Aquí solo se fija su precedencia.

`?` es postfix y se aplica a `?T`/`!T`; no es el operador ternario de C. No hay
`a ? b : c`; para eso se usa `if`.

### 11.9 Casts con `as`

`as` convierte explícitamente entre tipos numéricos y entre `Char` y enteros
(§9.13). No hay casts implícitos ni casts entre strings y números; para eso se
usa `parse`/`to_string` (§10.8).

```pengu
bind small = 300 as U8          -- 44
bind code = 'A' as U32          -- 65
bind rounded = 3.9 as Int       -- 3
```

`as` tiene más precedencia que `*` y menos que los prefijos. `-1 as U8` es
`(-1) as u8`; el resultado es `255`.

### 11.10 Asignación y compuestos

La asignación es una **sentencia**, no una expresión:

| Forma | Rust | Notas |
|---|---|---|
| `x = expr` | `x = expr` | requiere `morph` |
| `x += expr` | `x += expr` | equivalente a `x = x + expr` |
| `x -= expr` | `x -= expr` | — |
| `x *= expr` | `x *= expr` | — |
| `x /= expr` | `x /= expr` | — |
| `x %= expr` | `x %= expr` | — |
| `x &= expr` | `x &= expr` | bitwise |
| `x \|= expr` | `x \|= expr` | bitwise |
| `x ^= expr` | `x ^= expr` | bitwise |
| `x <<= expr` | `x <<= expr` | — |
| `x >>= expr` | `x >>= expr` | — |

No hay `++` ni `--`. La asignación compuesta evalúa el lugar una sola vez y
respeta las reglas de préstamo: si `x` está prestado, `x += 1` es error hasta que
el préstamo termine (§17).

```pengu
morph total = 0
total += 10
total *= 2
```

### 11.11 Ejemplo completo

```pengu
grimoire
    bind a = 2 + 3 * 4
    bind b = (2 + 3) * 4
    bind c = 1 << 3
    bind d = 0b1010 & 0b0110
    bind e = not false and true
    bind f = 2 in [1, 2, 3]
    bind g = 3.9 as Int

    print(a)
    print(b)
    print(c)
    print(d)
    print(e)
    print(f)
    print(g)
```

Rust generado:

```rust
fn main() {
    let a = 2 + 3 * 4;
    let b = (2 + 3) * 4;
    let c = 1 << 3;
    let d = 0b1010 & 0b0110;
    let e = !false && true;
    let f = [1, 2, 3].contains(&2);
    let g = 3.9 as i32;

    println!("{}", a);
    println!("{}", b);
    println!("{}", c);
    println!("{}", d);
    println!("{}", e);
    println!("{}", f);
    println!("{}", g);
}
```

La salida es `14`, `20`, `8`, `2`, `true`, `true`, `3`.

### 11.12 Sobrecarga

Los operadores de esta sección son los de los tipos primitivos. Un `rune` puede
implementar `Add`, `Sub`, `Mul`, `Div`, `Rem`, `Neg`, `Not`, `BitAnd`, `BitOr`,
`BitXor`, `Shl`, `Shr`, `PartialEq` y `PartialOrd` mediante `ritual` (§40). Esa
implementación no cambia la precedencia ni la asociatividad.

No se permite definir operadores nuevos ni cambiar la aridad. `a + b + c` siempre
se agrupa como `(a + b) + c`, aunque `+` esté sobrecargado.

### 11.13 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9201` | tipos incompatibles en operador | convertir explícitamente o implementar el trait |
| `PGS-E9202` | operador no definido para el tipo | usar otro operador o implementar §40 |
| `PGS-E9203` | comparación encadenada | separar con `and` |
| `PGS-E9204` | asignación usada como expresión | convertirla en sentencia |
| `PGS-E9205` | `&&` o `\|\|` usados | usar `and`/`or` |
| `PGS-E9206` | `++`/`--` | usar `+= 1`/`-= 1` |
| `PGS-E9207` | shift negativo o demasiado grande | comprobar el valor o usar `checked_shl` |
| `PGS-E9208` | rango mal formado | usar `a..b` o `a..=b`, sin encadenar |
| `PGS-E9209` | `in` sobre un tipo sin pertenencia | usar un iterador o `contains` explícito |
| `PGS-E9210` | `?` fuera de función que devuelve `?T`/`!T` | cambiar el retorno o usar `match` |

### 11.14 Criterios de aceptación

- [x] La tabla de precedencia cubre todos los operadores y su asociatividad.
- [x] Los operadores aritméticos, lógicos, bitwise y de comparación están
      definidos.
- [x] `and`/`or` cortocircuitan y solo aceptan `Bool`.
- [x] `is`/`isnt` son alias de igualdad, no identidad.
- [x] La asignación es sentencia y no asocia.
- [x] `in`, `as`, `?` y `awaken` tienen precedencia y semántica inicial.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="sec-12-booleanos"></a>
## 12. Booleanos y lógica

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 2 |
| Rust | `bool`, `&&`, `\|\|`, `!` |
| Palabras mágicas | `and`, `or`, `not`, `is`, `isnt` |
| Depende de | §9, §11 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec12_booleans.pengu` |

`Bool` tiene dos valores y ninguna conversión implícita. PenguScript no tiene
truthiness: una condición no es “cualquier cosa que no sea cero/vacía/nula”. Si
una rama necesita un `Bool`, se escribe un `Bool`.

### 12.1 El tipo `Bool`

| Propiedad | Valor |
|---|---|
| Valores | `true`, `false` |
| Tipo Rust | `bool` |
| Tamaño | 1 byte en el codegen actual; no es parte de la ABI |
| Conversión implícita | ninguna |
| `null`/`none` como falso | no |

```pengu
bind enabled: Bool = true
bind disabled = false
bind also_disabled: Bool = not enabled
```

No se puede usar un entero como condición:

```pengu
if 1
    print("no")
```

El error es `PGS-E9301`: la condición debe ser `Bool`, no `Int`. Tampoco se puede
usar `none`, un string vacío ni un puntero.

### 12.2 Operadores lógicos

| Operador | Aridad | Tipos | Rust | Cortocircuito |
|---|---|---|---|---|
| `and` | binario | `Bool`, `Bool` | `&&` | sí |
| `or` | binario | `Bool`, `Bool` | `\|\|` | sí |
| `not` | unario | `Bool` | `!` | — |
| `!` | unario | `Bool` o entero | `!` | — |

`and` y `or` **solo** aceptan `Bool`. No devuelven el operando como Python:
`true and 1` es error de tipo, no `1`.

```pengu
bind can_run = ready and not paused
bind either = ready or paused
bind neither = not (ready or paused)
```

Rust generado:

```rust
let ready = true;
let paused = false;
let can_run = ready && !paused;
let either = ready || paused;
let neither = !(ready || paused);
```

`!` es un alias de `not` para `Bool`; `not` es la forma recomendada. `!` también
es el complemento bit a bit de enteros (§11.5); el tipo del operando decide.

No se aceptan `&&` ni `||` (`PGS-E9303`). La forma canónica es `and`/`or`, para
que la lógica se lea como MoonScript y no se mezclen dos vocabularios.

### 12.3 Cortocircuito

`and` evalúa el lado derecho solo si el izquierdo es `true`. `or` lo evalúa solo
si el izquierdo es `false`.

```pengu
bind ok = has_permission(user) and audit(user)
bind fallback = is_cached(key) or compute(key)
```

Rust generado:

```rust
fn has_permission(user: &str) -> bool { let _ = user; true }
fn audit(user: &str) -> bool { let _ = user; true }
fn is_cached(key: &str) -> bool { let _ = key; false }
fn compute(key: &str) -> bool { let _ = key; true }
let user = "ana";
let key = "cache";
let ok = has_permission(user) && audit(user);
let fallback = is_cached(key) || compute(key);
```

Consecuencias:

1. El lado derecho puede tener efectos secundarios que no ocurren.
2. No se usa `and`/`or` para elegir un valor; para eso está `if`.
3. `and`/`or` no son funciones; no se pueden pasar como argumento.
4. `not` no cortocircuita porque es unario.

### 12.4 Comparaciones

Las comparaciones producen `Bool`:

| Operador | Requisito | Resultado |
|---|---|---|
| `==`, `!=` | `PartialEq` | `Bool` |
| `<`, `<=`, `>`, `>=` | `PartialOrd` | `Bool` |
| `is`, `isnt` | alias de `==`, `!=` | `Bool` |

`is`/`isnt` no son identidad de referencia; comparan valores. Dos `String` con el
mismo contenido son `is`. Para identidad de referencia se usa `ptr_eq` (§19).

Las comparaciones **no encadenan**. `a < b < c` es error (`PGS-E9203`); se
escribe:

```pengu
bind in_range = low <= value and value <= high
```

### 12.5 Lógica y bitwise

`and`/`or` son lógicos y cortocircuitan. `&`/`|`/`^` son bit a bit y evalúan
ambos lados. Sobre `Bool`, `&`/`|`/`^` existen pero **no** son la forma
recomendada:

```pengu
bind a = true & false       -- false, evalúa ambos
bind b = true and false     -- false, cortocircuita
```

Para lógica se usan `and`/`or`/`not`. Para máscaras de bits se usan `&`/`|`/`^`
sobre enteros.

### 12.6 Condiciones estrictas

Toda posición que espera un `Bool` exige exactamente `Bool`:

| Posición | Regla |
|---|---|
| `if`/`elseif`/`unless` | condición `Bool` |
| `while` | condición `Bool` |
| `for ... if` (comprehension) | condición `Bool` |
| guard de `match` | condición `Bool` |
| `assert(cond)` | condición `Bool` |

No hay conversión de `Int`, `Float`, `Char`, `Str`, `?T`, `!T` ni punteros a
`Bool`. Si se necesita “no vacío”, se escribe `s.is_empty()` o
`option.is_some()`.

### 12.7 `Bool` y `match`

`match` sobre `Bool` debe cubrir `true` y `false`:

```pengu
bind label = match enabled
    when true then "activo"
    when false then "inactivo"
```

Un `match` sin uno de los dos brazos es no exhaustivo (`PGS-E9306`). El
compilador no añade un brazo comodín para `Bool`.

### 12.8 Ejemplo completo

```pengu
grimoire
    bind ready = true
    bind paused = false
    bind can_run = ready and not paused
    bind either = ready or paused
    bind neither = not (ready or paused)
    bind in_range = 1 <= 2 and 2 <= 3

    print(can_run)
    print(either)
    print(neither)
    print(in_range)
```

Rust generado:

```rust
fn main() {
    let ready = true;
    let paused = false;
    let can_run = ready && !paused;
    let either = ready || paused;
    let neither = !(ready || paused);
    let in_range = 1 <= 2 && 2 <= 3;

    println!("{}", can_run);
    println!("{}", either);
    println!("{}", neither);
    println!("{}", in_range);
}
```

La salida es `true`, `true`, `false`, `true`.

### 12.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9301` | condición que no es `Bool` | usar una comparación o `is_empty`/`is_some` |
| `PGS-E9302` | `and`/`or` con un operando que no es `Bool` | convertir la condición explícitamente |
| `PGS-E9303` | `&&`/`\|\|` usados | usar `and`/`or` |
| `PGS-E9304` | `not` sobre un tipo que no es `Bool` | usar `!` para enteros o una comparación |
| `PGS-E9305` | conversión implícita a `Bool` | escribir la comparación |
| `PGS-E9306` | `match` de `Bool` no exhaustivo | cubrir `true` y `false` |
| `PGS-W9301` | `&`/`\|` sobre `Bool` en contexto lógico | usar `and`/`or` si se busca cortocircuito |

### 12.10 Criterios de aceptación

- [x] `Bool` es estricto y no hay truthiness.
- [x] `and`/`or` cortocircuitan y solo aceptan `Bool`.
- [x] `not` y `!` están definidos sin ambigüedad.
- [x] Las comparaciones producen `Bool` y no encadenan.
- [x] Las condiciones de `if`/`while`/`match` exigen `Bool`.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="sec-13-condicionales"></a>
## 13. Condicionales

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 2 |
| Rust | `if`, `else if`, `else`, `!` |
| Palabras mágicas | `unless`, `then`, `elseif` |
| Depende de | §8, §12 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec13_conditionals.pengu` |

`if` es una expresión: produce el valor de la rama ejecutada. También se puede
usar como sentencia, en cuyo caso el valor se descarta. La condición debe ser
`Bool`; no hay truthiness (§12.6).

### 13.1 Forma multilínea

```pengu
bind score = 95

if score >= 90
    "excelente"
elseif score >= 60
    "aprobado"
else
    "reprobado"
```

Reglas:

1. La condición va en la misma línea que `if`, sin `then`.
2. El cuerpo es un bloque indentado; no se usan llaves.
3. `elseif` encadena condiciones; puede haber cero o más.
4. `else` es la rama final; es opcional.
5. `elseif` y `else` deben estar al mismo nivel de indentación que el `if`.
6. Un `elseif` después de `else` es error (`PGS-E9404`).
7. No se usa `else if`; la forma canónica es `elseif` (`PGS-E9405`).

La forma anterior es equivalente a:

```pengu
bind score = 95
bind category = if score >= 90
    "excelente"
elseif score >= 60
    "aprobado"
else
    "reprobado"
```

Rust generado:

```rust
fn main() {
    let score = 95;
    let category = if score >= 90 {
        "excelente"
    } else if score >= 60 {
        "aprobado"
    } else {
        "reprobado"
    };
    println!("{}", category);
}
```

### 13.2 Forma inline con `then`

Cuando cada rama cabe en una línea se usa `then`:

```pengu
bind n = 7
bind parity = if n % 2 == 0 then "par" else "impar"
bind max = if a > b then a else b
```

Reglas:

1. `then` es obligatorio en la forma inline; sin él, el parser espera un bloque
   indentado (`PGS-E9403`).
2. La rama del `then` es una expresión; el `else` también.
3. `then` no se usa en la forma multilínea.
4. Una forma inline sin `else` produce `Unit` y solo se permite como sentencia:
   `if debug then print("debug")`.
5. No se mezcla `then` con un bloque indentado en la misma rama.

Rust generado para `parity`:

```rust
fn example(n: i32) -> &'static str {
    let parity = if n % 2 == 0 { "par" } else { "impar" };
    parity
}
```

### 13.3 `unless`

`unless cond` es azúcar de `if not cond`:

```pengu
unless logged_in
    print("inicia sesión")
```

Rust generado:

```rust
fn example(logged_in: bool) {
    if !logged_in {
        println!("inicia sesión");
    }
}
```

Reglas:

1. `unless` acepta `else`, pero no `elseif` (`PGS-E9406`). Para varias ramas se
   usa `if`.
2. `unless cond then expr` es la forma inline.
3. `unless` no invierte el tipo de las ramas; solo niega la condición.
4. `unless not cond` es válido pero se simplifica a `if cond` con un warning
   (`PGS-W9401`).

### 13.4 `if` como expresión

`if` produce un valor si todas las ramas que pueden ejecutarse producen un valor
compatible.

| Forma | Tipo | Ejemplo |
|---|---|---|
| `if c then a else b` | unificación de `a` y `b` | `if ok then 1 else 0` |
| `if c ... else ...` | unificación de ramas | `if c` … `else` … |
| `if c then a` | `Unit` | solo sentencia |
| `if c` … (sin `else`) | `Unit` | solo sentencia |
| rama `Never` | no participa | `if c then 1 else return 0` |

Reglas de unificación:

1. Si todas las ramas tienen el mismo tipo `T`, el `if` tiene tipo `T`.
2. Una rama `Never` se coacciona a `T`; no obliga a unificar con las demás.
3. Si una rama es `Unit` y otra `T ≠ Unit`, el `if` es error (`PGS-E9402`),
   salvo que el contexto exija `Unit`.
4. Sin `else`, el tipo es `Unit`; usar el `if` como valor es error
   (`PGS-E9408`).
5. Los valores de las ramas no se mezclan: solo se evalúa una.

```pengu
bind count = 0
bind index = 3
bind length = 5
bind label = if count == 0
    "vacío"
else
    "con elementos"

bind next = if index + 1 < length then index + 1 else return index
```

Rust generado:

```rust
fn example() -> usize {
    let count = 0;
    let index = 3usize;
    let length = 5usize;
    let label = if count == 0 {
        "vacío"
    } else {
        "con elementos"
    };
    let _ = label;

    let next = if index + 1 < length {
        index + 1
    } else {
        return index;
    };
    next
}
```

### 13.5 `if` como sentencia

Un `if` en posición de sentencia descarta su valor:

```pengu
if debug
    print("modo debug")

if cache_hit
    use_cache()
else
    recompute()
```

No es necesario `then` en la forma multilínea. Si la rama produce un valor no
`Unit`, el compilador emite un warning (`PGS-W9402`) y el codegen descarta el
valor; no se convierte en una expresión.

### 13.6 Anidamiento y `else` colgante

La indentación resuelve el `else` colgante: un `else` pertenece al `if` más
cercano que esté abierto en el mismo nivel.

```pengu
if outer
    if inner
        print("ambos")
    else
        print("solo outer")
```

El `else` pertenece al `if inner`. Para que pertenezca a `outer`, se indenta el
`if inner` dentro de un `do` o se reestructura el código. No hay ambigüedad de
parser porque el `else` se alinea con su `if`.

### 13.7 `if` y `match`

`if` sirve para condiciones booleanas; `match` para elegir por forma o valor
(§30). Para comprobar una `Option` sin desenvolverla se puede usar `match`:

```pengu
match value
    when some(x)
        print(x)
    when none
        print("sin valor")
```

La forma abreviada de Rust `if let` se especifica en §30 como una forma de
`match`; en Fase 2 se usa `match` o `is_some()`/`is_none()`.

### 13.8 Ejemplo completo

```pengu
grimoire
    bind score = 75
    bind category = if score >= 90
        "excelente"
    elseif score >= 60
        "aprobado"
    else
        "reprobado"

    bind parity = if score % 2 == 0 then "par" else "impar"
    bind max = if score > 100 then score else 100

    unless score < 0
        print("puntaje válido")

    print(category)
    print(parity)
    print(max)
```

Rust generado:

```rust
fn main() {
    let score = 75;
    let category = if score >= 90 {
        "excelente"
    } else if score >= 60 {
        "aprobado"
    } else {
        "reprobado"
    };

    let parity = if score % 2 == 0 { "par" } else { "impar" };
    let max = if score > 100 { score } else { 100 };

    if !(score < 0) {
        println!("puntaje válido");
    }

    println!("{}", category);
    println!("{}", parity);
    println!("{}", max);
}
```

La salida es `puntaje válido`, `aprobado`, `impar`, `100`.

### 13.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9402` | ramas de `if` con tipos incompatibles | convertir a un tipo común |
| `PGS-E9403` | forma inline sin `then` | añadir `then` o indentar el bloque |
| `PGS-E9404` | `elseif` después de `else` | mover `else` al final |
| `PGS-E9405` | `else if` usado | usar `elseif` |
| `PGS-E9406` | `elseif` dentro de `unless` | usar `if` |
| `PGS-E9407` | `if` sin cuerpo | añadir un bloque o `then` |
| `PGS-E9408` | `if` sin `else` usado como valor | añadir `else` o descartar el valor |
| `PGS-W9401` | `unless not` redundante | simplificar a `if` |
| `PGS-W9402` | valor de `if` descartado como sentencia | usar `bind _ =` o consumir el valor |

### 13.10 Criterios de aceptación

- [x] `if`/`elseif`/`else` y `unless` están definidos.
- [x] `then` inline y bloque indentado no se mezclan.
- [x] `if` sin `else` produce `Unit`; con `else`, las ramas unifican.
- [x] Una rama `Never` no participa en la unificación.
- [x] La condición solo acepta `Bool`.
- [x] El `else` colgante se resuelve por indentación.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="sec-14-bucles"></a>
## 14. Bucles

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 2 |
| Rust | `while`, `loop`, `for`, `break`, `continue`, labels |
| Palabras mágicas | `while`, `loop`, `for`, `by`, `break`, `continue` |
| Depende de | §8, §11, §13 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec14_loops.pengu` |

PenguScript tiene tres bucles: `while` para repetir mientras una condición sea
`Bool`, `loop` para repetir hasta un `break`, y `for` para recorrer un iterable o
un rango. `loop` puede producir un valor con `break value`; `while` y `for`
producen `Unit`.

### 14.1 `while`

```pengu
morph n = 3
while n > 0
    print(n)
    n -= 1
```

Rust generado:

```rust
let mut n = 3;
while n > 0 {
    println!("{}", n);
    n -= 1;
}
```

Reglas:

1. La condición debe ser `Bool`; no hay truthiness (`PGS-E9301`).
2. La condición se evalúa antes de cada iteración; si es `false` al inicio, el
   cuerpo no se ejecuta.
3. `while` produce `Unit`; no se puede `bind` su resultado.
4. `break` sale del bucle; `continue` salta a la siguiente comprobación.
5. `break value` **no** es válido en `while` (`PGS-E9504`); para producir un
   valor se usa `loop`.

### 14.2 `loop`

```pengu
morph attempts = 0
loop
    attempts += 1
    if attempts >= 3
        break
```

Rust generado:

```rust
let mut attempts = 0;
loop {
    attempts += 1;
    if attempts >= 3 {
        break;
    }
}
```

`loop` sin `break` tiene tipo `Never`; un `loop` con `break value` tiene el tipo
del valor:

```pengu
bind answer = loop
    break 42
```

Rust generado:

```rust
let answer = loop {
    break 42;
};
```

Reglas:

1. `break` sin valor produce `Unit`; `break value` produce el tipo del valor.
2. Todos los `break value` de un mismo `loop` deben unificar (`PGS-E9510`).
3. Un `loop` sin `break` es `Never` y no termina normalmente.
4. `continue` vuelve al inicio del `loop` sin producir valor.
5. `loop` es una expresión; se puede usar en `bind`, `return` o como rama.

### 14.3 `for` sobre iterables

```pengu
for item in items
    print(item)

for (key, value) in table
    print(key)
    print(value)
```

Rust generado:

```rust
fn example(items: Vec<i32>, table: std::collections::HashMap<&'static str, i32>) {
    for item in items {
        println!("{}", item);
    }

    for (key, value) in table {
        println!("{}", key);
        println!("{}", value);
    }
}
```

Reglas:

1. `for` llama a `IntoIterator` sobre el iterable. Un array, `Vec`, slice, mapa,
   set o rango implementan `IntoIterator`; un tipo de usuario puede implementarlo
   en §49.
2. El patrón del `for` puede ser un identificador, una tupla, un `rune` o un
   patrón de §30.
3. El binding del patrón es inmutable. Para mutar el valor dentro del cuerpo se
   usa un `morph` local o se recorre por referencia mutable.
4. `for` produce `Unit`; no se puede `bind` su resultado.
5. El iterable se evalúa una vez, antes de la primera iteración.
6. Si el iterable se mueve, queda movido después del bucle (§16).

### 14.4 Rangos numéricos y `by`

```pengu
for i in 0..5
    print(i)

for i in 0..=10 by 2
    print(i)
```

Rust generado:

```rust
for i in 0..5 {
    println!("{}", i);
}

for i in (0..=10).step_by(2) {
    println!("{}", i);
}
```

Reglas:

1. `a..b` es exclusivo; `a..=b` es inclusivo.
2. `by n` es opcional y solo se aplica a rangos numéricos. `n` debe ser un entero
   positivo (`PGS-E9505`); `by 0` es error.
3. `by` no cambia el tipo del rango; el codegen usa `step_by`.
4. No hay `by` negativo. Para recorrer en orden inverso se usa `.rev()` sobre el
   rango (adelanto de §49).
5. `by` solo es válido en `for`, no en una expresión de rango general
   (`PGS-E9506`).

### 14.5 `break` y `continue`

| Forma | Dónde | Efecto |
|---|---|---|
| `break` | cualquier bucle | sale del bucle |
| `break value` | solo `loop` | sale y produce `value` |
| `continue` | cualquier bucle | salta a la siguiente iteración |
| `break label` | bucle etiquetado | sale del bucle con esa etiqueta |
| `continue label` | bucle etiquetado | continúa el bucle con esa etiqueta |

`break value` en `while` o `for` es error (`PGS-E9504`). `break` fuera de un
bucle es error (`PGS-E9502`); `continue` fuera de un bucle también
(`PGS-E9503`).

### 14.6 Etiquetas

Una etiqueta se escribe antes del bucle:

```pengu
outer: for i in 0..3
    inner: while true
        if i == 1
            break outer
        break
```

Rust generado:

```rust
'outer: for i in 0..3 {
    'inner: while true {
        if i == 1 {
            break 'outer;
        }
        break;
    }
}
```

Reglas:

1. La etiqueta es un identificador seguido de `:` al inicio de la línea del
   bucle; no es un tipo ni un campo.
2. `break outer` y `continue outer` deben referirse a un bucle etiquetado
   envolvente (`PGS-E9509`).
3. Las etiquetas no crean scope de variables; solo nombran el bucle.
4. No se puede etiquetar un `if` o un bloque, solo `while`/`loop`/`for`.

### 14.7 `loop` como expresión

```pengu
bind first_even = loop
    bind n = next()
    if n % 2 == 0
        break n
```

Rust generado:

```rust
fn next() -> i32 { 4 }

fn example() -> i32 {
    let first_even = loop {
        let n = next();
        if n % 2 == 0 {
            break n;
        }
    };
    first_even
}
```

El tipo de `first_even` es el tipo de `n`. Un `loop` con varios `break` debe
unificar sus valores; un `break` sin valor en un `loop` que produce valor es
error (`PGS-E9510`).

### 14.8 Comprehensions

Una comprehension es azúcar para construir una colección:

```pengu
bind squares = [x * x for x in 0..5]
bind evens = [x for x in 0..10 if x % 2 == 0]
bind lengths = { name: name.len() for name in ["a", "bb"] }
```

Rust generado:

```rust
let squares: Vec<i32> = (0..5).map(|x| x * x).collect();
let evens: Vec<i32> = (0..10).filter(|x| x % 2 == 0).collect();
let lengths: std::collections::HashMap<&str, usize> =
    ["a", "bb"].into_iter().map(|name| (name, name.len())).collect();
```

Reglas:

1. `[expr for pattern in iterable]` produce un `Vec[T]`.
2. `[expr for pattern in iterable if cond]` filtra con `cond`, que debe ser
   `Bool`.
3. `{ key: value for pattern in iterable }` produce un `HashMap[K, V]`; las
   claves deben implementar `Eq + Hash`.
4. No hay `break`/`continue` dentro de una comprehension; usar un `for`
   explícito (`PGS-E9508`).
5. El orden de los elementos de un `HashMap` no se garantiza.
6. Una comprehension es una expresión; se puede usar en `bind`, `return` o como
   argumento.

### 14.9 `while let` e iteradores

La forma `while let` de Rust se expresará con `match`/patrones en §30; en Fase 2
se usa un `loop` con `match` o `while cond`. Los adaptadores de iterador
(`map`, `filter`, `enumerate`, `zip`, `take`, `skip`, `chain`, `rev`) se
documentan en §49.

### 14.10 Ejemplo completo

```pengu
grimoire
    morph total = 0
    for i in 0..5
        total += i

    for i in 0..=10 by 2
        total += i

    outer: for i in 0..3
        for j in 0..3
            if i == 1 and j == 1
                break outer

    bind squares = [x * x for x in 0..5]
    bind evens = [x for x in 0..10 if x % 2 == 0]

    print(total)
    print(squares.len())
    print(evens.len())
```

Rust generado:

```rust
fn main() {
    let mut total = 0;
    for i in 0..5 {
        total += i;
    }

    for i in (0..=10).step_by(2) {
        total += i;
    }

    'outer: for i in 0..3 {
        for j in 0..3 {
            if i == 1 && j == 1 {
                break 'outer;
            }
        }
    }

    let squares: Vec<i32> = (0..5).map(|x| x * x).collect();
    let evens: Vec<i32> = (0..10).filter(|x| x % 2 == 0).collect();

    println!("{}", total);
    println!("{}", squares.len());
    println!("{}", evens.len());
}
```

La salida es `40`, `5`, `5`.

### 14.11 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9502` | `break` fuera de un bucle | moverlo dentro o eliminarlo |
| `PGS-E9503` | `continue` fuera de un bucle | moverlo dentro o eliminarlo |
| `PGS-E9504` | `break value` en `while`/`for` | usar `loop` o `break` sin valor |
| `PGS-E9505` | `by` no positivo | usar un entero positivo |
| `PGS-E9506` | `by` fuera de un `for` | moverlo al `for` |
| `PGS-E9507` | `loop` sin `break` usado como valor | añadir `break` o cambiar el contexto |
| `PGS-E9508` | `break`/`continue` en comprehension | usar un `for` explícito |
| `PGS-E9509` | etiqueta no encontrada | etiquetar el bucle envolvente |
| `PGS-E9510` | `break` con tipos incompatibles | unificar los valores |
| `PGS-W9501` | `loop` que nunca termina | añadir una condición de salida |

### 14.12 Criterios de aceptación

- [x] `while`, `loop` y `for` tienen sintaxis y semántica.
- [x] `loop` puede producir valor con `break value`.
- [x] `while`/`for` producen `Unit`; `break value` en ellos es error.
- [x] Los rangos inclusivos y `by` están definidos.
- [x] Las etiquetas y `break`/`continue` etiquetados están definidos.
- [x] Las comprehensions son expresiones y no contienen `break`.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="sec-15-funciones"></a>
## 15. Funciones

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 2 |
| Rust | `fn`, closures, `impl`, `fn main` |
| Palabras mágicas | `->`, `=>`, `@`, `grimoire`, `dream`, `curse`, `eternal` |
| Depende de | §4, §5, §7, §8 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec15_functions.pengu` |

Una función nombrada se declara con `=` y `->`:

```pengu
sum = (x: Int, y: Int) -> Int
    x + y
```

`->` es el operador de función: separa los parámetros del tipo de retorno. Una
lambda usa `=>` y produce una closure:

```pengu
bind inc = (x: Int) => x + 1
```

La diferencia no es cosmética: `->` declara un **item** de función, sin captura;
`=>` declara una **closure**, que puede capturar el entorno. Esta distinción
elimina la ambigüedad entre una función y una variable global, y permite que
`name = (...) -> Tipo` sea un item de módulo aunque `bind`/`morph` no puedan
usarse a nivel de módulo (§5).

### 15.1 Sintaxis de funciones nombradas

```pengu
name = (param: Tipo, otro: Tipo) -> TipoDeRetorno
    cuerpo

name = [T](valor: T) -> T
    valor
```

Reglas:

1. El nombre es un identificador XID (Unicode UAX #31: letras, dígitos y `_`); no puede repetirse en el mismo scope
   (`PGS-E9612`).
2. El tipo de retorno es **obligatorio**. `->` sin tipo es error
   (`PGS-E9603`).
3. El cuerpo va indentado en las líneas siguientes. No hay cuerpo inline para
   funciones nombradas (`PGS-E9602`); para una expresión corta se usa una lambda
   o se escribe el cuerpo en varias líneas.
4. La función es un item: se ve en todo el módulo, puede llamarse antes de su
   definición y no captura variables.
5. Una función nombrada solo puede declararse en un módulo, `scroll`, `ritual`,
   `pact` o `foreign`; no dentro de otra función. Para una función local se usa
   una lambda.
6. No hay overloading, argumentos por defecto, varargs ni argumentos nombrados
   (`PGS-E9616`).
7. Los parámetros se pasan por posición; el número y los tipos se comprueban en
   la llamada (`PGS-E9618`).

### 15.2 Parámetros

| Forma | Significado | Rust |
|---|---|---|
| `x: T` | parámetro inmutable | `x: T` |
| `morph x: T` | parámetro mutable local | `mut x: T` |
| `_: T` | parámetro ignorado | `_: T` |
| `@` | receptor `&self` | `&self` |
| `@mut` | receptor `&mut self` | `&mut self` |
| `@own` | receptor `self` | `self` |

Reglas:

1. El receptor, si existe, debe ser el primer parámetro.
2. Un método tiene exactamente un receptor; una función libre no tiene.
3. `morph` en un parámetro permite mutar la copia local; no cambia el tipo ni
   el ownership del argumento.
4. `_` se usa para parámetros no usados; no introduce nombre.
5. No se permite `self`, `this` ni `me`; el receptor es `@`/`@mut`/`@own`
   (`PGS-E9606`).
6. Los parámetros no son patrones; para destructuring se usa un `bind` dentro del
   cuerpo (§5.6).

### 15.3 Retorno implícito y `return`

La última expresión del cuerpo es el valor de retorno:

```pengu
sum = (x: Int, y: Int) -> Int
    x + y
```

Si la última línea es una sentencia (`bind`, asignación, `print`), la función
devuelve `Unit` y el tipo declarado debe ser `Unit`:

```pengu
log = (msg: &Str) -> Unit
    print(msg)
```

`return` sale antes:

```pengu
abs = (x: Int) -> Int
    if x < 0
        return -x
    x
```

Reglas:

1. `return expr` debe unificar con el tipo de retorno (`PGS-E9608`).
2. `return` sin valor solo es válido en una función `-> Unit` (`PGS-E9609`).
3. `return expr` en una función `-> Unit` es error (`PGS-E9610`).
4. `return` tiene tipo `Never` y puede aparecer en una rama de un `if` o
   `match` (§8.5).
5. No hay `return` implícito de `none`/`nil`; no existe `null`.

### 15.4 Recursión

Una función puede llamarse a sí misma o a otra función del módulo:

```pengu
fact = (n: UInt) -> UInt
    if n <= 1
        1
    else
        n * fact(n - 1)

is_even = (n: UInt) -> Bool
    if n == 0 then true else is_odd(n - 1)

is_odd = (n: UInt) -> Bool
    if n == 0 then false else is_even(n - 1)
```

La recursion mutua funciona porque los items se ven en todo el módulo (§7.3).
El tipo de retorno explícito es obligatorio para romper la inferencia circular.

### 15.5 Divergencia: `Never`

Una función que no retorna normalmente declara `Never`:

```pengu
fail = (msg: &Str) -> Never
    panic(msg)
```

Rust generado:

```rust
fn fail(msg: &str) -> ! {
    panic!("{}", msg);
}
```

Reglas:

1. `Never` solo es válido si el cuerpo diverge en todas las rutas: `panic`,
   `loop` sin `break`, o una llamada a otra función `Never`.
2. Una función `-> Never` puede usarse donde se espera cualquier tipo.
3. No se puede `return` un valor desde una función `Never` (`PGS-E9611`).
4. `panic` es una función de prelude con tipo `(&Str) -> Never`.

### 15.6 `grimoire`: el punto de entrada

`grimoire` declara `main`:

```pengu
grimoire
    print("hola, PenguScript")
```

Rust generado:

```rust
fn main() {
    println!("hola, PenguScript");
}
```

Un `grimoire` fallible devuelve `!Unit`:

```pengu
grimoire: !Unit
    bind text = read_file("Tome.toml")?
    print(text)
```

Rust generado:

```rust
fn read_file(_path: &str) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
    Ok(String::new())
}

fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let text = read_file("Tome.toml")?;
    println!("{}", text);
    Ok(())
}
```

Reglas:

1. `grimoire` no lleva parámetros (`PGS-E9613`).
2. Solo puede haber un `grimoire` por binario (`PGS-E9614`).
3. `grimoire` sin tipo o `grimoire: Unit` genera `fn main()`.
4. `grimoire: !Unit` genera un `main` con `Result<(), Error>` y permite `?`.
5. Otro tipo de retorno es error (`PGS-E9615`).
6. `grimoire` no es una función normal: no se llama, no se toma como valor y no
   se exporta.
7. El `grimoire` de un `lib.pengu` no existe; una librería no tiene `main`.
8. `main` no es una palabra mágica; el único punto de entrada es `grimoire`.

### 15.7 Lambdas y closures

```pengu
bind inc = (x: Int) => x + 1
bind add = (a: Int, b: Int) => a + b
bind make_adder = (n: Int) => (x: Int) => x + n
```

Reglas:

1. Una lambda se escribe `(params) => expr` o `(params) =>` seguido de un bloque
   indentado.
2. Puede capturar por referencia; `move` fuerza captura por valor:
   `move () => print(owner)`.
3. Debe estar ligada con `bind`/`morph`; una lambda a nivel de módulo es error
   (`PGS-E9605`).
4. El tipo de retorno se infiere; no se escribe `=> Tipo`.
5. Los tipos de los parámetros se pueden omitir si el contexto espera un tipo de
   función; si no, son obligatorios (`PGS-E9604`).
6. `return` dentro de una lambda retorna de la closure, no de la función
   envolvente.
7. Las lambdas no se pueden sobrecargar; el número de parámetros es fijo.

Ejemplo con tipo contextual:

```pengu
bind op: (Int, Int) -> Int = (a, b) => a + b
bind inc: (Int) -> Int = (x) => x + 1
```

### 15.8 Métodos y funciones asociadas

Dentro de un `ritual` o `pact`:

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

    translate = (@mut, dx: Float, dy: Float) -> Unit
        @.x += dx
        @.y += dy

    origin = () -> Point
        Point(x: 0.0, y: 0.0)
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }

    fn translate(&mut self, dx: f64, dy: f64) {
        self.x += dx;
        self.y += dy;
    }

    fn origin() -> Point {
        Point { x: 0.0, y: 0.0 }
    }
}
```

Reglas:

1. `@` es `&self`, `@mut` es `&mut self`, `@own` es `self`.
2. En el cuerpo del método, `@` se refiere al receptor; no se escribe `self`.
3. `origin` no tiene receptor: es una función asociada y se llama
   `Point.origin()`.
4. Un método se llama con el receptor antes del punto (`p.length()`); no se usa `length(p)`.
5. Un método `@mut` requiere un binding `morph` (`PGS-E9619`).
6. Un método `@own` consume el valor; después no se puede usar.
7. `@` en posición de patrón sigue siendo el operador de binding de Rust
   (`name @ pattern`, §30); el contexto distingue receptor de patrón.

### 15.9 Tipos de función y funciones como valores

Un tipo de función se escribe:

```pengu
bind op: (Int, Int) -> Int = add
bind apply: ((Int) -> Int, Int) -> Int = (f, x) => f(x)
```

Reglas:

1. `(A, B) -> C` es un tipo de función, no una declaración.
2. Una función nombrada se usa como valor escribiendo su nombre:
   `bind f = add`.
3. Una lambda se usa como valor directamente.
4. Las funciones `-> Never` son subtipo de cualquier tipo de función con los
   mismos parámetros.
5. Los tipos de función no llevan nombre de parámetro; solo tipos.

### 15.10 Genéricos: adelanto

La sintaxis de parámetros de tipo es `[T]`:

```pengu
identity = [T](value: T) -> T
    value

bind n = identity[Int](42)
bind s = identity[String](String.from("pengu"))
```

Las restricciones (`where`, `pact`) se definen en §33–§34. En Fase 2 solo se
documenta la forma; el codegen es:

```rust
fn identity<T>(value: T) -> T {
    value
}

let n = identity::<i32>(42);
let s = identity::<&str>("pengu");
```

### 15.11 Modificadores: adelanto

| Modificador | Rust | Se detalla en |
|---|---|---|
| `dream` | `async fn` | §50 |
| `curse` | `unsafe fn` | §52 |
| `eternal` | `const fn` | §46 |
| `foreign` | `extern "C"` | §54 |

```pengu
dream fetch = (url: &Str) -> !String
    -- cuerpo async
```

El tipo `!String` es `Result[String, Error]`; el `async` se añade por el
modificador. La semántica de `awaken`, `?` y errores se ve en §48–§50.

### 15.12 Ejemplo completo

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

    translate = (@mut, dx: Float, dy: Float) -> Unit
        @.x += dx
        @.y += dy

    origin = () -> Point
        Point(x: 0.0, y: 0.0)

sum = (x: Int, y: Int) -> Int
    x + y

grimoire
    morph p = Point(x: 3.0, y: 4.0)
    print(p.length())
    p.translate(1.0, 2.0)
    print(p.length())

    bind q = Point.origin()
    print(q.length())
    print(sum(2, 3))
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }

    fn translate(&mut self, dx: f64, dy: f64) {
        self.x += dx;
        self.y += dy;
    }

    fn origin() -> Point {
        Point { x: 0.0, y: 0.0 }
    }
}

fn sum(x: i32, y: i32) -> i32 {
    x + y
}

fn main() {
    let mut p = Point { x: 3.0, y: 4.0 };
    println!("{}", p.length());
    p.translate(1.0, 2.0);
    println!("{}", p.length());

    let q = Point::origin();
    println!("{}", q.length());
    println!("{}", sum(2, 3));
}
```

La salida es `5`, `7.211102550927978`, `0`, `5`.

### 15.13 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9601` | falta `-> Tipo` en una función nombrada | añadir el tipo de retorno |
| `PGS-E9602` | cuerpo inline en función nombrada | indentar el cuerpo o usar `=>` |
| `PGS-E9603` | `->` sin tipo | escribir el tipo |
| `PGS-E9604` | no se puede inferir el tipo de un parámetro lambda | anotar el parámetro o el contexto |
| `PGS-E9605` | lambda a nivel de módulo | usar una función nombrada |
| `PGS-E9606` | `self`/`this` usado | usar `@`/`@mut`/`@own` |
| `PGS-E9607` | receptor fuera de la primera posición | moverlo al inicio |
| `PGS-E9608` | `return` incompatible con el retorno | ajustar el valor o el tipo |
| `PGS-E9609` | `return` sin valor en función no `Unit` | devolver un valor |
| `PGS-E9610` | `return valor` en función `Unit` | usar `return` sin valor |
| `PGS-E9611` | `return` en función `Never` | eliminar el retorno |
| `PGS-E9612` | nombre de función duplicado | renombrar |
| `PGS-E9613` | `grimoire` con parámetros | quitar los parámetros |
| `PGS-E9614` | más de un `grimoire` | dejar uno |
| `PGS-E9615` | tipo de retorno de `grimoire` inválido | usar `Unit` o `!Unit` |
| `PGS-E9616` | overloading/default/varargs | usar una sola firma |
| `PGS-E9617` | captura en función nombrada | usar una lambda |
| `PGS-E9618` | número o tipo de argumentos incorrecto | ajustar la llamada |
| `PGS-E9619` | método `@mut` sobre binding inmutable | usar `morph` |
| `PGS-E9620` | receptor incompatible con el método | ajustar `@`/`@mut`/`@own` |

### 15.14 Criterios de aceptación

- [x] `name = (...) -> Tipo` y `(params) => expr` están definidos.
- [x] El tipo de retorno de una función nombrada es obligatorio.
- [x] El cuerpo de una función nombrada es indentado, sin inline.
- [x] `bind`/`morph` siguen prohibidos a nivel de módulo; las funciones no son
      variables globales.
- [x] `return`, recursión y `Never` están definidos.
- [x] `grimoire` y `grimoire: !Unit` generan `main` y `Result`.
- [x] Los receptores `@`/`@mut`/`@own` y las funciones asociadas están definidos.
- [x] Las lambdas capturan, `move` fuerza captura por valor y su tipo se infiere.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="part-3"></a>
## Parte III — Ownership y memoria

<a id="sec-16-ownership"></a>
## 16. Ownership

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 3 |
| Rust | `move`, `Copy`, `Clone`, `Drop`, `std::mem` |
| Palabras mágicas | `bind`, `morph`, `@own` |
| Depende de | §5, §15 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec16_ownership.pengu` |

Cada valor tiene **un solo dueño**. El dueño es responsable de liberar el valor
cuando sale de scope. Asignar, pasar como argumento o devolver un valor no
`Copy` transfiere la propiedad (un **move**); el dueño anterior deja de ser
usable. Esta regla es la base de la seguridad de memoria sin GC.

### 16.1 Move

```pengu
rune Token
    id: Int

grimoire
    bind a = Token(id: 1)
    bind b = a          -- mueve a -> b
    print(b.id)
    -- print(a.id)     -- error: a fue movido
```

Rust generado:

```rust
struct Token {
    id: i32,
}

fn main() {
    let a = Token { id: 1 };
    let b = a;
    println!("{}", b.id);
    // println!("{}", a.id); // error: use of moved value
}
```

Un move ocurre en:

| Operación | Ejemplo | Efecto |
|---|---|---|
| binding | `bind b = a` | `a` se mueve a `b` |
| reasignación | `b = a` | `a` se mueve a `b` |
| argumento | `take(a)` | `a` se mueve al parámetro |
| retorno | `return a` | `a` se mueve al llamador |
| campo | `bind n = pair.name` | el campo se mueve; el resto queda parcial |
| colección | `vec.push(a)` | `a` se mueve al vector |
| `@own` | `value.consume()` | el receptor se mueve al método |

Después de un move, el binding original no se puede leer, escribir, prestar ni
mover otra vez (`PGS-E1601`). El compilador de Rust emite `E0382`; el front-end
de PenguScript lo traduce a `PGS-E1601` con la misma ubicación.

### 16.2 `Copy`

Los tipos `Copy` se copian bit a bit en lugar de moverse:

```pengu
grimoire
    bind a = 10
    bind b = a
    print(a + b)        -- ambos siguen siendo válidos
```

Rust generado:

```rust
fn main() {
    let a = 10;
    let b = a;
    println!("{}", a + b);
}
```

Son `Copy`:

- todos los enteros, `Bool`, `Char`, `F32`/`F64`;
- las referencias compartidas `&T` (no `&mut T`);
- las tuplas y arrays de tipos `Copy`;
- un `rune` marcado `@@derive(Copy, Clone)` si todos sus campos son `Copy`.

No son `Copy`: `String`, `Vec[T]`, `Box[T]`, `Rc[T]`, `Arc[T]`, `HashMap`, ni
ningún tipo con `Drop`. Un tipo `Copy` no puede implementar `Drop`
(`PGS-E1602`); si necesita liberar recursos, no es `Copy`.

### 16.3 `Clone` explícito

Copiar un valor no `Copy` requiere `.clone()`:

```pengu
grimoire
    bind a = String.from("pengu")
    bind b = a.clone()
    print(a)
    print(b)
```

Rust generado:

```rust
fn main() {
    let a = String::from("pengu");
    let b = a.clone();
    println!("{}", a);
    println!("{}", b);
}
```

Reglas:

1. `.clone()` es explícito; no hay copia implícita de tipos no `Copy`.
2. `clone` puede ser costoso; no se usa para evitar pensar en ownership.
3. `@@derive(Clone)` genera `Clone` para un `rune` o `enchanting`.
4. `Clone` no implica `Copy`; `Copy` sí implica `Clone` (`PGS-E1603`).
5. Clonar una referencia (`&T.clone()`) clona la referencia, no el valor; para
   clonar el valor se usa `(*r).clone()` o `r.clone()` según el tipo.

### 16.4 `Drop`

Un tipo con `Drop` ejecuta código al salir de scope:

```pengu
rune Guard
    name: String

ritual Guard
    drop = (@mut) -> Unit
        print("drop #{@.name}")
```

El codegen implementa `Drop`:

```rust
struct Guard {
    name: String,
}

impl Drop for Guard {
    fn drop(&mut self) {
        println!("drop {}", self.name);
    }
}
```

Reglas:

1. `Drop` se ejecuta exactamente una vez, cuando el dueño sale de scope.
2. `Drop` no se llama en un move; el nuevo dueño se encarga.
3. El orden exacto se especifica en §21.3.
4. `Drop` y `Copy` son incompatibles (`PGS-E1602`).
5. No se llama `drop` manualmente; para liberar antes se usa un scope o
   `std.mem.drop` (que no existe en Rust estable; se usa `drop(value)`).
6. `std.mem.forget` evita el `Drop` y filtra memoria; es explícito y raro.

### 16.5 Moves parciales

```pengu
rune Pair
    name: String
    count: Int

grimoire
    bind pair = Pair(name: "pengu", count: 1)
    bind name = pair.name      -- mueve solo el campo name
    print(name)
    print(pair.count)          -- el campo count sigue disponible
    -- print(pair)            -- error: pair está parcialmente movido
```

Rust generado:

```rust
struct Pair {
    name: String,
    count: i32,
}

fn main() {
    let pair = Pair {
        name: String::from("pengu"),
        count: 1,
    };
    let name = pair.name;
    println!("{}", name);
    println!("{}", pair.count);
    // println!("{:?}", pair); // error: use of partially moved value
}
```

Reglas:

1. Se puede mover un campo de un `rune` que no implementa `Drop`.
2. Después del move parcial, el `rune` completo no se puede usar, pero los
   campos no movidos sí.
3. Un tipo con `Drop` no permite moves parciales (`PGS-E1604`).
4. Para conservar el `rune` completo, se presta el campo (`&pair.name`) o se
   clona.
5. Un `enchanting` con datos solo se mueve completo; el pattern matching puede
   mover campos en §30.

### 16.6 Ownership en funciones y retornos

Pasar un valor a una función lo mueve si el parámetro no es una referencia:

```pengu
take = (text: String) -> Unit
    print(text)

grimoire
    bind text = String.from("pengu")
    take(text)
    -- print(text) -- error: text fue movido
```

Rust generado:

```rust
fn take(text: String) {
    println!("{}", text);
}

fn main() {
    let text = String::from("pengu");
    take(text);
    // println!("{}", text); // error: use of moved value
}
```

Para conservar el valor se presta:

```pengu
borrow = (text: &Str) -> Unit
    print(text)

grimoire
    bind text = String.from("pengu")
    borrow(&text)
    print(text)
```

Rust generado:

```rust
fn borrow(text: &str) {
    println!("{}", text);
}

fn main() {
    let text = String::from("pengu");
    borrow(&text);
    println!("{}", text);
}
```

Devolver un valor transfiere ownership al llamador:

```pengu
make = () -> String
    String.from("pengu")

grimoire
    bind text = make()
    print(text)
```

Rust generado:

```rust
fn make() -> String {
    String::from("pengu")
}

fn main() {
    let text = make();
    println!("{}", text);
}
```

### 16.7 Ownership en colecciones

Meter un valor en un `Vec` lo mueve:

```pengu
grimoire
    morph names: Vec[String] = Vec.new()
    bind name = String.from("pengu")
    names.push(name)
    -- print(name) -- error: name fue movido al vector
    print(names.len())
```

Rust generado:

```rust
fn main() {
    let mut names: Vec<String> = Vec::new();
    let name = String::from("pengu");
    names.push(name);
    // println!("{}", name); // error: use of moved value
    println!("{}", names.len());
}
```

Sacar un valor del vector también lo mueve:

```pengu
bind first = names.remove(0)
```

`names[0]` indexa por referencia; para mover se usa `remove` o
`into_iter`. Los detalles están en §23.

### 16.8 `std.mem`: take, replace, swap, forget

```pengu
grimoire
    morph slot = String.from("old")
    bind taken = std.mem.take(&mut slot)
    bind replaced = std.mem.replace(&mut slot, String.from("new"))
    std.mem.swap(&mut slot, &mut taken)
    std.mem.forget(replaced)
    print(slot)
    print(taken)
```

Rust generado:

```rust
fn main() {
    let mut slot = String::from("old");
    let mut taken = std::mem::take(&mut slot);
    let replaced = std::mem::replace(&mut slot, String::from("new"));
    std::mem::swap(&mut slot, &mut taken);
    std::mem::forget(replaced);
    println!("{}", slot);
    println!("{}", taken);
}
```

| Operación | Efecto | Requiere |
|---|---|---|
| `std.mem.take(&mut x)` | deja `Default::default()` en `x` y devuelve el valor | `T: Default` |
| `std.mem.replace(&mut x, new)` | deja `new` y devuelve el valor anterior | — |
| `std.mem.swap(&mut a, &mut b)` | intercambia dos valores | mismos tipos |
| `std.mem.forget(x)` | consume `x` sin ejecutar `Drop` | — |

`forget` filtra memoria y recursos; solo se usa en código de bajo nivel
justificado. Un `Rc`/`Arc` con `forget` puede filtrar el contador.

### 16.9 Errores típicos del borrow checker

```text
error[E0382]: use of moved value: `a`
  --> src/main.rs:5:11
   |
 4 |     let b = a;
   |             - value moved here
 5 |     println!("{}", a.id);
   |                    ^ value used here after move
   |
   = note: move occurs because `a` has type `Token`, which does not implement the `Copy` trait
```

Soluciones, en orden de preferencia:

1. Prestar en lugar de mover: `print(&a)`.
2. Reordenar para usar `a` antes del move.
3. Clonar explícitamente: `a.clone()`.
4. Devolver el valor desde la función para transferir ownership al llamador.

### 16.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E1601` | uso después de move | prestar, reordenar o clonar |
| `PGS-E1602` | `Copy` + `Drop` | quitar `Copy` o `Drop` |
| `PGS-E1603` | `Copy` sin `Clone` | derivar `Clone` |
| `PGS-E1604` | move parcial de tipo con `Drop` | mover el valor completo o prestar |
| `PGS-E1605` | move de un valor prestado | terminar el préstamo o clonar |
| `PGS-E1606` | uso de un `rune` parcialmente movido | usar los campos no movidos |
| `PGS-W1601` | `clone` innecesario | prestar en su lugar |

### 16.11 Criterios de aceptación

- [x] Move, `Copy` y `Clone` están diferenciados.
- [x] `Drop` y la prohibición de `Copy + Drop` están definidos.
- [x] Los moves parciales y sus límites están especificados.
- [x] Ownership en funciones, retornos y colecciones está cubierto.
- [x] `std.mem.take/replace/swap/forget` están definidos.
- [x] Hay un ejemplo de error del borrow checker y sus soluciones.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="sec-17-borrowing"></a>
## 17. Borrowing

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 3 |
| Rust | `&`, `&mut`, NLL, reborrow |
| Palabras mágicas | `&`, `&mut`, `@` |
| Depende de | §16, §18 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec17_borrowing.pengu` |

Un **préstamo** (borrow) permite usar un valor sin transferir su ownership. Hay
dos clases:

| Forma | Tipo | Acceso | Se escribe |
|---|---|---|---|
| compartido | `&T` | lectura | `&value` |
| mutable | `&mut T` | lectura y escritura | `&mut value` |

La regla central: **o muchos préstamos compartidos, o exactamente un préstamo
mutable**, nunca ambos a la vez. El borrow checker de Rust comprueba que los
préstamos no se solapen; los préstamos terminan en su último uso (NLL), no
necesariamente al final del scope.

### 17.1 Préstamos compartidos

```pengu
grimoire
    bind text = String.from("pengu")
    bind a = &text
    bind b = &text
    print(a.len() + b.len())
```

Rust generado:

```rust
fn main() {
    let text = String::from("pengu");
    let a = &text;
    let b = &text;
    println!("{}", a.len() + b.len());
}
```

Reglas:

1. `&value` presta `value` por lectura.
2. Se pueden crear tantos `&T` como se quiera mientras no haya un `&mut T`
   activo.
3. El dueño no se puede mover mientras exista un préstamo activo.
4. Un `&T` permite leer y copiar el valor si `T: Copy`, pero no mutarlo.
5. Un `&T` se puede volver a prestar como `&T` sin límite.

### 17.2 Préstamos mutables

```pengu
grimoire
    morph text = String.from("pengu")
    bind r = &mut text
    r.push_str("!")
    print(text)
```

Rust generado:

```rust
fn main() {
    let mut text = String::from("pengu");
    let r = &mut text;
    r.push_str("!");
    println!("{}", text);
}
```

Reglas:

1. `&mut value` requiere que `value` sea un binding `morph` o un campo mutable.
2. Mientras un `&mut T` esté activo, no puede haber ningún otro `&T` ni `&mut T`
   sobre el mismo valor (`PGS-E1701`).
3. A través de `&mut T` se puede leer y escribir.
4. El préstamo mutable termina en su último uso; después el dueño vuelve a ser
   usable.
5. No se puede mover el dueño mientras el préstamo mutable esté activo
   (`PGS-E1702`).

### 17.3 NLL: el préstamo termina en el último uso

```pengu
grimoire
    morph text = String.from("pengu")
    bind r = &text
    print(r.len())
    text.push_str("!")        -- permitido: r ya no se usa
    print(text)
```

Rust generado:

```rust
fn main() {
    let mut text = String::from("pengu");
    let r = &text;
    println!("{}", r.len());
    text.push_str("!");
    println!("{}", text);
}
```

El compilador no usa el scope léxico para decidir el fin del préstamo: usa el
último punto donde la referencia puede usarse. Esto se llama **non-lexical
lifetimes** (NLL). Un préstamo sigue activo mientras pueda usarse, aunque no se
use en una línea concreta.

### 17.4 Conflictos y errores

```text
error[E0502]: cannot borrow `text` as mutable because it is also borrowed as immutable
  --> src/main.rs:5:5
   |
 4 |     let r = &text;
   |             ----- immutable borrow occurs here
 5 |     text.push_str("!");
   |     ^^^^^^^^^^^^^^^^^ mutable borrow occurs here
 6 |     println!("{}", r.len());
   |                      - immutable borrow later used here
```

Correcciones, en orden:

1. Terminar el préstamo compartido antes de mutar (reordenar).
2. Usar un scope explícito para limitar el préstamo.
3. Pasar `&mut` a una función en lugar de mezclar préstamos.
4. Usar `RefCell`/`Cell` si la mutabilidad interior es realmente necesaria
   (§20.4).

### 17.5 Reborrow

Prestar una referencia crea un **reborrow**:

```pengu
grow = (text: &mut String) -> Unit
    text.push_str("!")

grimoire
    morph text = String.from("pengu")
    grow(&mut text)
    grow(&mut text)
    print(text)
```

Rust generado:

```rust
fn grow(text: &mut String) {
    text.push_str("!");
}

fn main() {
    let mut text = String::from("pengu");
    grow(&mut text);
    grow(&mut text);
    println!("{}", text);
}
```

Reglas:

1. `&mut *r` y `&*r` re-prestan el valor apuntado por `r`.
2. El reborrow puede acortar el préstamo; es la base de pasar `&mut` a funciones
   sin perder el dueño.
3. Un reborrow mutable no puede coexistir con otro préstamo activo.
4. El compilador inserta reborrows implícitos al llamar funciones que esperan
   `&mut T`; no hace falta escribirlos siempre.

### 17.6 Préstamos en funciones

```pengu
length = (text: &Str) -> Usize
    text.len()

append = (text: &mut String, suffix: &Str) -> Unit
    text.push_str(suffix)

grimoire
    morph text = String.from("pengu")
    append(&mut text, "!")
    print(length(&text))
```

Rust generado:

```rust
fn length(text: &str) -> usize {
    text.len()
}

fn append(text: &mut String, suffix: &str) {
    text.push_str(suffix);
}

fn main() {
    let mut text = String::from("pengu");
    append(&mut text, "!");
    println!("{}", length(&text));
}
```

Reglas:

1. Un parámetro `&T` no consume el argumento.
2. Un parámetro `&mut T` requiere un binding `morph` y presta mutabilidad.
3. La función no puede guardar la referencia más allá de su lifetime; §18
   explica cómo se declara.
4. Devolver una referencia requiere que el lifetime de salida esté ligado a una
   entrada (§18.2).

### 17.7 Structs con referencias

Un `rune` puede contener referencias, pero necesita un lifetime:

```pengu
rune Excerpt['a]
    text: &'a Str

ritual Excerpt['a]
    len = (@) -> Usize
        @.text.len()

grimoire
    bind text = "pengu"
    bind excerpt = Excerpt(text: text)
    print(excerpt.len())
```

Rust generado:

```rust
struct Excerpt<'a> {
    text: &'a str,
}

impl<'a> Excerpt<'a> {
    fn len(&self) -> usize {
        self.text.len()
    }
}

fn main() {
    let text = "pengu";
    let excerpt = Excerpt { text };
    println!("{}", excerpt.len());
}
```

Reglas:

1. El `rune` declara sus parámetros de lifetime entre `[...]`.
2. El lifetime del campo debe ser un parámetro del `rune`, no un `'static`
   implícito.
3. El `ritual` repite `['a]` para implementar sobre `Excerpt['a]`.
4. El valor prestado debe vivir al menos tanto como el `rune` (§18.5).

### 17.8 Conflictos con colecciones: `split_at_mut`

Dos préstamos mutables a mitades distintas son seguros si el compilador puede
demostrar que no se solapan:

```pengu
grimoire
    morph values = Vec.from([1, 2, 3, 4])
    bind (left, right) = values.split_at_mut(2)
    left[0] = 9
    right[0] = 8
    print(left[0] + right[0])
```

Rust generado:

```rust
fn main() {
    let mut values = Vec::from([1, 2, 3, 4]);
    let (left, right) = values.split_at_mut(2);
    left[0] = 9;
    right[0] = 8;
    println!("{}", left[0] + right[0]);
}
```

`split_at_mut` es la solución estándar para mutar dos mitades a la vez. Otras
soluciones: `chunks_mut`, `iter_mut`, `split_first_mut`, o separar los datos en
campos distintos.

### 17.9 Mutabilidad interior

Cuando un valor compartido necesita mutar por dentro, se usa mutabilidad
interior (§20.4):

```pengu
bind cell = RefCell.new(0)
*cell.borrow_mut() += 1
print(*cell.borrow())
```

Rust generado:

```rust
use std::cell::RefCell;

fn main() {
    let cell = RefCell::new(0);
    *cell.borrow_mut() += 1;
    println!("{}", *cell.borrow());
}
```

`RefCell` comprueba los préstamos en runtime; un conflicto produce panic, no un
error de compilación. `Cell` copia valores y no permite referencias; `Mutex` y
`RwLock` son las versiones thread-safe (§20.5).

### 17.10 Préstamos y `@`

Dentro de un método:

| Receptor | Equivale a | Permite |
|---|---|---|
| `@` | `&self` | leer campos, llamar métodos `&self` |
| `@mut` | `&mut self` | mutar campos, llamar métodos `&mut self` |
| `@own` | `self` | consumir el valor |

Un método `@` no puede mutar el receptor; uno `@mut` no puede coexistir con un
préstamo compartido activo. El compilador aplica las mismas reglas que a
cualquier `&`/`&mut`.

### 17.11 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E1701` | préstamo mutable y compartido solapados | terminar uno antes del otro |
| `PGS-E1702` | move mientras hay un préstamo activo | esperar a que termine el préstamo |
| `PGS-E1703` | dos préstamos mutables solapados | usar `split_at_mut` o separar campos |
| `PGS-E1704` | préstamo de un temporal que no vive suficiente | guardar el temporal en un `bind` |
| `PGS-E1705` | retorno de referencia sin lifetime | añadir `'a` o devolver el valor |
| `PGS-E1706` | `&mut` sobre binding inmutable | usar `morph` |
| `PGS-W1701` | préstamo compartido innecesariamente largo | acortar el scope |

### 17.12 Criterios de aceptación

- [x] `&`/`&mut` y la regla XOR están definidos.
- [x] NLL y reborrow están explicados.
- [x] Los préstamos en funciones y retornos están cubiertos.
- [x] Los structs con referencias introducen lifetimes.
- [x] Los conflictos y sus soluciones incluyen `split_at_mut` e interior
      mutability.
- [x] El ejemplo de error muestra el mensaje de Rust y la corrección.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="sec-18-lifetimes"></a>
## 18. Lifetimes

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 3 |
| Rust | `'a`, `'static`, elisión, bounds, variance |
| Palabras mágicas | `'a`, `'static`, `for<'a>` |
| Depende de | §17, §33 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec18_lifetimes.pengu` |

Un **lifetime** es el rango en el que una referencia es válida. Rust lo comprueba
en tiempo de compilación; no hay coste en runtime. PenguScript usa la misma
sintaxis `'a` y `'static` que Rust, sin cambiarla.

### 18.1 Sintaxis

| Forma | Significado | Ejemplo |
|---|---|---|
| `&'a T` | referencia compartida con lifetime `'a` | `&'a Str` |
| `&'a mut T` | referencia mutable con lifetime `'a` | `&'a mut String` |
| `'static` | vive todo el programa | `&'static Str` |
| `['a]` | parámetro de lifetime | `Excerpt['a]` |
| `['a, T]` | lifetime y tipo | `Holder['a, T]` |
| `T: 'a` | `T` vive al menos `'a` | `T: 'a` |
| `'a: 'b` | `'a` vive al menos `'b` | `'a: 'b` |
| `for<'a>` | higher-ranked lifetime | `for<'a> (&'a T) -> &'a T` |

Los lifetimes no son valores: no se pueden almacenar, comparar ni imprimir. Solo
describen relaciones entre referencias.

### 18.2 Elisión

Rust permite omitir lifetimes en muchos casos. PenguScript aplica las mismas
reglas de elisión, en este orden:

| # | Situación | Resultado |
|---|---|---|
| 1 | Cada referencia de entrada sin lifetime recibe un lifetime distinto | `fn f(x: &T, y: &U)` → `fn f<'a, 'b>(x: &'a T, y: &'b U)` |
| 2 | Si hay exactamente un lifetime de entrada, la salida lo usa | `fn f(x: &T) -> &T` → `fn f<'a>(x: &'a T) -> &'a T` |
| 3 | Si hay un receptor `&self`/`&mut self`, la salida usa el lifetime del receptor | `fn f(&self, x: &T) -> &T` → salida ligada a `&self` |
| 4 | Si no se aplica ninguna regla, el lifetime de salida es obligatorio | error `PGS-E1801` |

Ejemplos:

```text
f(x: &T) -> &T                    -- elisión: salida = x
f(x: &T, y: &U) -> &T             -- error: dos entradas, salida ambigua
f<'a>(x: &'a T, y: &'a U) -> &'a T -- explícito: ambas entradas viven 'a
f(&self, x: &T) -> &T             -- salida ligada a &self
```

La elisión no cambia la semántica; solo evita escribir lifetimes cuando la
relación es obvia.

### 18.3 Lifetimes explícitos en funciones

```pengu
longest = ['a](a: &'a Str, b: &'a Str) -> &'a Str
    if a.len() >= b.len() then a else b

grimoire
    bind a = "pengu"
    bind b = "script"
    print(longest(a, b))
```

Rust generado:

```rust
fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}

fn main() {
    let a = "pengu";
    let b = "script";
    println!("{}", longest(a, b));
}
```

Reglas:

1. `['a]` declara el parámetro de lifetime de la función.
2. `&'a Str` dice que la referencia vive al menos `'a`.
3. `-> &'a Str` liga el retorno a `'a`; el llamador no puede usar el resultado
   más allá de los argumentos.
4. Todos los argumentos que compartan `'a` deben vivir al menos ese lifetime.
5. Si se devuelve una referencia a un temporal local, el compilador lo rechaza
   (`PGS-E1802`).

### 18.4 `'static`

`'static` significa que la referencia vive durante todo el programa:

```pengu
grimoire
    bind name: &'static Str = "pengu"
    print(name)
```

Rust generado:

```rust
fn main() {
    let name: &'static str = "pengu";
    println!("{}", name);
}
```

Son `'static`:

- los literales de string (`"pengu"`);
- los `relic` inmutables;
- las referencias a datos estáticos;
- `Box<dyn Trait + 'static>` (el trait object no contiene referencias cortas).

No son `'static` las referencias a locales, ni un `&T` que depende de un
préstamo. `'static` no significa “inmortal” para valores con `Drop`: un
`&'static T` puede apuntar a un valor que nunca se libera, pero el valor puede
tener un dueño estático.

### 18.5 Structs con lifetimes

```pengu
rune Excerpt['a]
    text: &'a Str

ritual Excerpt['a]
    len = (@) -> Usize
        @.text.len()

grimoire
    bind text = "pengu"
    bind excerpt = Excerpt(text: text)
    print(excerpt.len())
```

Rust generado:

```rust
struct Excerpt<'a> {
    text: &'a str,
}

impl<'a> Excerpt<'a> {
    fn len(&self) -> usize {
        self.text.len()
    }
}

fn main() {
    let text = "pengu";
    let excerpt = Excerpt { text };
    println!("{}", excerpt.len());
}
```

Reglas:

1. Un `rune` con referencias declara todos los lifetimes que usa.
2. El `ritual` repite los parámetros: `ritual Excerpt['a]`.
3. El valor prestado debe vivir al menos tanto como el `rune`.
4. Un `rune` con `'static` solo acepta referencias `'static`; no se puede
   construir con un local.
5. Los campos con referencias no se pueden mover fuera del `rune` sin romper el
   lifetime; se prestan o se copian.

### 18.6 Bounds de lifetime

```pengu
rune Holder['a, T: 'a]
    value: &'a T

ritual Holder['a, T]
    get = (@) -> &'a T
        @.value
```

Rust generado:

```rust
struct Holder<'a, T: 'a> {
    value: &'a T,
}

impl<'a, T: 'a> Holder<'a, T> {
    fn get(&self) -> &'a T {
        self.value
    }
}
```

Reglas:

1. `T: 'a` exige que `T` viva al menos `'a`; es necesario para guardar `&'a T`.
2. `'a: 'b` exige que `'a` viva al menos `'b`.
3. Los bounds se pueden escribir en la lista de parámetros o en `where` (§34).
4. Un `impl` puede repetir o relajar bounds; no puede añadir un bound que el
   tipo no cumpla.
5. Los bounds de lifetime no cambian el layout ni el coste.

### 18.7 Variance

La varianza describe cómo un cambio de lifetime afecta a un tipo genérico:

| Tipo | Varianza en `'a` | Varianza en `T` |
|---|---|---|
| `&'a T` | covariante | covariante si `T` lo es |
| `&'a mut T` | covariante | invariante |
| `Cell[T]`, `RefCell[T]`, `Mutex[T]` | — | invariante |
| `fn(T)` | — | contravariante |
| `fn() -> T` | — | covariante |
| `Box[T]`, `Vec[T]` | — | covariante |

Reglas:

1. Covariante: un `&'long T` se puede usar como `&'short T`.
2. Invariante: no se puede cambiar el lifetime ni el tipo aunque parezca seguro;
   es la opción conservadora para mutabilidad interior.
3. Contravariante: un `fn(&'short T)` puede usarse como `fn(&'long T)`.
4. PenguScript no expone anotaciones de varianza; se heredan de Rust.
5. Si un tipo no compila por varianza, la solución es un límite explícito o
   rediseñar el contenedor, no un cast.

### 18.8 HRTB: adelanto

Un **higher-ranked trait bound** cuantifica sobre todos los lifetimes:

```pengu
apply = (f: for<'a> (&'a Int) -> Int, x: Int) -> Int
    f(&x)
```

Rust generado:

```rust
fn apply<F>(f: F, x: i32) -> i32
where
    F: for<'a> Fn(&'a i32) -> i32,
{
    f(&x)
}
```

La sintaxis `for<'a>` se documenta en §37; en §18 solo se introduce para
reconocerla. `Fn`/`FnMut`/`FnOnce` se detallan en §38.

### 18.9 Errores típicos

```text
error[E0106]: missing lifetime specifier
  --> src/main.rs:3:31
   |
 3 | fn longest(a: &str, b: &str) -> &str {
   |                               ^ expected named lifetime parameter
   |
   = help: this function's return type contains a borrowed value, but the
           signature does not say whether it is borrowed from `a` or `b`
```

Corrección:

```rust
fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}
```

### 18.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E1801` | lifetime de salida ambiguo | añadir `'a` y ligarlo |
| `PGS-E1802` | retorno de referencia a un local | devolver el valor o mover el dueño |
| `PGS-E1803` | lifetime no declarado en el `rune` | añadir `['a]` |
| `PGS-E1804` | bound `T: 'a` incumplido | acortar el lifetime o cambiar el tipo |
| `PGS-E1805` | `'static` requerido pero el valor es local | usar un `String`/`Box` o un estático |
| `PGS-E1806` | varianza incompatible | rediseñar el contenedor |
| `PGS-W1801` | lifetime explícito innecesario | dejar la elisión |

### 18.11 Criterios de aceptación

- [x] La sintaxis de lifetimes y `'static` está definida.
- [x] La tabla de elisión cubre los casos estables.
- [x] Los lifetimes en funciones, structs e impls están cubiertos.
- [x] Los bounds y la varianza están explicados.
- [x] HRTB se introduce y se enlaza a §37.
- [x] Hay un error de elisión con corrección.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="sec-19-referencias"></a>
## 19. Referencias y punteros

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 3 |
| Rust | `&T`, `&mut T`, `*const T`, `*mut T`, `&raw`, `NonNull` |
| Palabras mágicas | `&`, `&mut`, `&raw`, `curse` |
| Depende de | §17, §18 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec19_pointers.pengu` |

PenguScript distingue tres familias:

| Forma | Tipo | Seguridad | Null |
|---|---|---|---|
| referencia compartida | `&T` | segura | no |
| referencia mutable | `&mut T` | segura | no |
| puntero raw | `*const T` / `*mut T` | solo en `curse` | puede ser null |

Las referencias son la forma normal de prestar. Los punteros raw existen para
FFI, estructuras de datos de bajo nivel y código `curse`; no son un reemplazo de
`&`/`&mut`.

### 19.1 Referencias

```pengu
grimoire
    bind value = 42
    bind shared = &value
    print(*shared)

    morph text = String.from("pengu")
    bind mutable = &mut text
    mutable.push_str("!")
    print(text)
```

Rust generado:

```rust
fn main() {
    let value = 42;
    let shared = &value;
    println!("{}", *shared);

    let mut text = String::from("pengu");
    let mutable = &mut text;
    mutable.push_str("!");
    println!("{}", text);
}
```

Reglas:

1. `&value` produce `&T`; `*r` lee el valor apuntado.
2. `&mut value` produce `&mut T`; requiere `morph`.
3. `*r = value` escribe a través de `&mut T`.
4. Las referencias nunca son null y siempre apuntan a un valor válido.
5. Un `&T` no permite mover el valor; un `&mut T` tampoco.

### 19.2 Punteros raw

```pengu
grimoire
    bind value = 42
    bind p = &raw const value
    print(p as Usize)
```

Rust generado:

```rust
fn main() {
    let value = 42;
    let p = &raw const value;
    println!("{}", p as usize);
}
```

Reglas:

1. `&raw const place` crea `*const T` sin crear una referencia intermedia.
2. `&raw mut place` crea `*mut T`; requiere `morph`.
3. Un puntero raw puede ser null, dangling o apuntar a memoria no inicializada;
   el compilador no lo comprueba.
4. Crear un puntero raw es seguro; **desreferenciarlo** requiere `curse`.
5. `p as Usize` convierte la dirección; `p as *const U` cambia el tipo.
6. `*const T` y `*mut T` no implementan `Send`/`Sync` por defecto; §52 lo trata.

### 19.3 Desreferenciar y `curse`

```pengu
curse read = (p: *const Int) -> Int
    *p
```

Rust generado:

```rust
unsafe fn read(p: *const i32) -> i32 {
    unsafe { *p }
}
```

Una función `curse` es `unsafe fn`; su cuerpo se trata como un bloque
`unsafe`. En el call site se necesita un bloque `curse`:

```pengu
grimoire
    bind value = 42
    bind p = &raw const value
    curse
        bind read = *p
        print(read)
```

Rust generado:

```rust
fn main() {
    let value = 42;
    let p = &raw const value;
    unsafe {
        let read = *p;
        println!("{}", read);
    }
}
```

Reglas:

1. `curse` como modificador declara una función `unsafe fn`.
2. `curse` como bloque introduce un contexto `unsafe` y produce el valor de su
   última expresión.
3. `*p` sobre `*const T`/`*mut T` solo es válido dentro de `curse`
   (`PGS-E1901`).
4. Escribir `*p = value` requiere `*mut T` y `curse`.
5. Llamar a una función `curse` requiere un bloque `curse` (`PGS-E1902`).
6. El bloque `curse` no relaja las reglas de aliasing ni de lifetimes; solo
   permite operaciones que Rust marca como unsafe.

### 19.4 `NonNull`

`NonNull[T]` es un puntero no nulo, pero no garantiza que sea válido:

```pengu
bind value = 42
bind ptr: NonNull[Int] = NonNull.from(&mut value)
```

Rust generado:

```rust
use std::ptr::NonNull;

fn main() {
    let mut value = 42;
    let ptr: NonNull<i32> = NonNull::from(&mut value);
    println!("{}", ptr.as_ptr() as usize);
}
```

Reglas:

1. `NonNull[T]` no puede ser null; es la opción para “puntero no nulo”.
2. `NonNull::from(&mut value)` crea un `NonNull` a partir de una referencia.
3. `ptr.as_ptr()` devuelve `*mut T`; para leer se necesita `curse`.
4. Un `NonNull` puede quedar dangling si el valor se libera; el tipo no lo evita.
5. Para un puntero que puede ser null se usa `?NonNull[T]` (`Option<NonNull<T>>`),
   no un `NonNull` “null”.

### 19.5 Aritmética de punteros

```pengu
curse offset = (p: *const Int, n: Usize) -> *const Int
    p.add(n)
```

Rust generado:

```rust
unsafe fn offset(p: *const i32, n: usize) -> *const i32 {
    unsafe { p.add(n) }
}
```

Reglas:

1. `p.add(n)` avanza `n` elementos, no `n` bytes; `n` se multiplica por
   `size_of::<T>()`.
2. El puntero resultante debe quedar dentro de la misma allocation o uno pasado
   el final; si no, la operación es UB.
3. `p.offset(n)` acepta enteros con signo; `p.add(n)`/`p.sub(n)` usan `Usize`.
4. `p.wrapping_add(n)` no exige estar dentro de la allocation, pero desreferenciar
   fuera de ella sigue siendo UB.
5. No se hace aritmética sobre `&T`; se convierte a `*const T` primero.

### 19.6 Null, dangling y provenance

| Concepto | Qué es | Cómo se evita |
|---|---|---|
| null | dirección 0 | usar `?NonNull[T]` o `Option<*const T>` |
| dangling | apunta a memoria liberada | mantener vivo el dueño |
| uninitialized | memoria sin inicializar | `MaybeUninit`/`MaybeUninit::assume_init` en `curse` |
| provenance | permiso de acceso que acompaña al puntero | no fabricar punteros con enteros; usar `&raw` |
| aliasing | dos accesos incompatibles | respetar `&T`/`&mut T` también en `curse` |

Rust usa **provenance**: un puntero no es solo una dirección, también lleva el
permiso sobre una allocation. Convertir un `Usize` arbitrario a puntero y
desreferenciarlo es UB aunque la dirección “exista”. La única forma portable de
obtener un puntero es `&raw`, un `NonNull` derivado de una referencia, o una
API de FFI documentada.

### 19.7 `curse` y FFI

Las funciones `foreign` con punteros se declaran en §54. Una función `curse`
puede recibir punteros de C, pero debe documentar:

- si el puntero puede ser null;
- quién es el dueño de la memoria;
- cuánto vive;
- si la función libera o no;
- si el puntero debe estar alineado.

Sin ese contrato, el código `curse` es una fuente de UB. La regla de PenguScript
es: **todo `curse` tiene un comentario de seguridad** (`-- SAFETY: ...`) o un
`@@safety` que lo sustituya. El linter lo comprueba (`PGS-W5201`).

### 19.8 Ejemplo completo

```pengu
curse read = (p: *const Int) -> Int
    *p

grimoire
    bind value = 42
    bind p = &raw const value
    bind copy = curse
        *p
    print(copy)
```

Rust generado:

```rust
unsafe fn read(p: *const i32) -> i32 {
    unsafe { *p }
}

fn main() {
    let value = 42;
    let p = &raw const value;
    let copy = unsafe { *p };
    println!("{}", copy);
}
```

`read` no se usa en este ejemplo; existe para mostrar la firma. El bloque
`curse` de `main` sí lee `p`.

### 19.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E1901` | deref de raw pointer fuera de `curse` | envolver en `curse` |
| `PGS-E1902` | llamada a función `curse` sin bloque `curse` | añadir `curse` |
| `PGS-E1903` | `&raw mut` sobre binding inmutable | usar `morph` |
| `PGS-E1904` | `NonNull` construido desde null | usar un valor válido |
| `PGS-E1905` | aritmética fuera de la allocation | rediseñar el offset |
| `PGS-E1906` | escritura con `*const T` | usar `*mut T` |

### 19.10 Criterios de aceptación

- [x] Referencias y punteros raw están diferenciados.
- [x] `&raw const`/`&raw mut` y `*p` están definidos.
- [x] `curse` como modificador y como bloque está definido.
- [x] `NonNull`, null, dangling y provenance están cubiertos.
- [x] La aritmética de punteros y sus límites están explicados.
- [x] FFI y el contrato de seguridad se enlazan a §52/§54.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

<a id="sec-20-smart-pointers"></a>
## 20. Smart pointers e interior mutability

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 3 |
| Rust | `Box`, `Rc`, `Arc`, `Cell`, `RefCell`, `Mutex`, `RwLock`, `Cow`, `Weak` |
| Palabras mágicas | `bind`, `morph`, `@mut`, `@@shared` |
| Depende de | §16, §17, §19 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec20_smart_pointers.pengu` |

Un **smart pointer** es un tipo que posee o comparte un valor y además ofrece
operaciones adicionales (contar referencias, comprobar préstamos en runtime,
sincronizar hilos). PenguScript no inventa una jerarquía nueva: expone los
smart pointers de Rust con nombres y reglas propias.

### 20.1 Guía de selección

| Necesidad | Tipo | Coste | `Send`/`Sync` | Se usa con |
|---|---|---|---|---|
| valor en el heap, un dueño | `Box[T]` | asignación | según `T` | recursión, `dyn Trait`, tamaños grandes |
| varios dueños, un hilo | `Rc[T]` | conteo no atómico | no | grafos, listas compartidas |
| varios dueños, varios hilos | `Arc[T]` | conteo atómico | sí, si `T` lo es | concurrencia |
| mutar a través de `&T`, un hilo | `Cell[T]` / `RefCell[T]` | préstamo runtime | no | interior mutability |
| mutar a través de `&T`, varios hilos | `Mutex[T]` / `RwLock[T]` | lock | sí, si `T` lo es | estado compartido |
| evitar copias de strings/slices | `Cow[Str]` | enum prestado/poseído | según `T` | APIs que a veces poseen |
| referencia débil | `Weak[T]` | conteo no propietario | según `T` | romper ciclos `Rc`/`Arc` |
| valor fijo en memoria | `Pin[P]` | sin coste | según `P` | `async`, self-references |

Regla: si no necesitas compartir, usa `Box[T]` o el valor directo. `Rc`/`Arc`
no son “el tipo por defecto para todo”; añaden conteo y pueden crear ciclos.

### 20.2 `Box[T]`

`Box[T]` guarda `T` en el heap y es el único dueño:

```pengu
rune Node
    value: Int
    next: ?Box[Node]

grimoire
    bind leaf = Node(value: 1, next: none)
    bind root = Box.new(Node(value: 2, next: some(Box.new(leaf))))
    print(root.value)
```

Rust generado:

```rust
struct Node {
    value: i32,
    next: Option<Box<Node>>,
}

fn main() {
    let leaf = Node { value: 1, next: None };
    let root = Box::new(Node {
        value: 2,
        next: Some(Box::new(leaf)),
    });
    println!("{}", root.value);
}
```

Reglas:

1. `Box.new(value)` -> `Box::new(value)`.
2. `Box[T]` implementa `Deref<Target = T>`; `box.field` y `*box` acceden al valor.
3. Mover el `Box` mueve el valor; clonar el `Box` requiere `T: Clone` y produce
   una copia profunda (`Box.clone(&b)`).
4. `Box[T]` permite tipos recursivos porque el tamaño del `Box` es un puntero.
5. `Box[Str]` es el tipo de un string poseído en el heap; `String` ya lo es, así
   que `Box[String]` solo se usa si necesitas indirección adicional.

### 20.3 `Rc[T]` y `Arc[T]`

`Rc[T]` comparte ownership dentro de un hilo; `Arc[T]` lo comparte entre hilos:

```pengu
grimoire
    bind a = Rc.new(String.from("pengu"))
    bind b = Rc.clone(&a)
    print(a)
    print(b)
    print(Rc.strong_count(&a))
```

Rust generado:

```rust
use std::rc::Rc;

fn main() {
    let a = Rc::new(String::from("pengu"));
    let b = Rc::clone(&a);
    println!("{}", a);
    println!("{}", b);
    println!("{}", Rc::strong_count(&a));
}
```

Reglas:

1. `Rc.new(value)`/`Arc.new(value)` crean el puntero con conteo 1.
2. `Rc.clone(&a)` incrementa el conteo; no copia `T`. Se escribe explícito para
   que el lector vea que no es un `Clone` profundo.
3. `Rc.strong_count(&a)`/`Arc.strong_count(&a)` devuelven el número de dueños.
4. El valor se libera cuando el último `Rc`/`Arc` se destruye.
5. `Rc[T]` no es `Send`; `Arc[T]` es `Send + Sync` solo si `T: Send + Sync`.
6. `Weak[T]` se crea con `Rc.downgrade(&a)`/`Arc.downgrade(&a)`; `weak.upgrade()`
   devuelve `?Rc[T]`/`?Arc[T]`. Un ciclo de `Rc`/`Arc` sin `Weak` nunca se libera.

```pengu
bind a = Arc.new(42)
bind weak = Arc.downgrade(&a)
bind restored = weak.upgrade()
```

Rust generado:

```rust
use std::sync::Arc;

fn main() {
    let a = Arc::new(42);
    let weak = Arc::downgrade(&a);
    let restored = weak.upgrade();
    println!("{:?}", restored);
}
```

`restored` es `Option<Arc<i32>>`; `print("{:?}")` es válido para `Option`.

### 20.4 `Cell[T]` y `RefCell[T]`

`Cell[T]` permite reemplazar el valor con `&self`; `RefCell[T]` permite
préstamos mutables comprobados en runtime:

```pengu
grimoire
    bind cell = RefCell.new(1)
    *cell.borrow_mut() += 1
    print(*cell.borrow())
```

Rust generado:

```rust
use std::cell::RefCell;

fn main() {
    let cell = RefCell::new(1);
    *cell.borrow_mut() += 1;
    println!("{}", *cell.borrow());
}
```

Reglas:

1. `RefCell.new(value)` -> `RefCell::new(value)`; `Cell.new(value)` ->
   `Cell::new(value)`.
2. `cell.borrow()` devuelve `Ref[T]`; `cell.borrow_mut()` devuelve `RefMut[T]`.
3. Dos `borrow_mut()` simultáneos, o `borrow()` + `borrow_mut()` solapados,
   hacen **panic** en runtime (`PGS-R2001`); no es un error de compilación.
4. `Cell[T]` solo funciona con `T: Copy` para leer (`cell.get()`); para tipos no
   `Copy` se usa `RefCell[T]` o `Cell.replace`.
5. `Cell`/`RefCell` no son `Sync`; no se comparten entre hilos. Para eso se usa
   `Mutex`/`RwLock`.
6. `RefCell` no evita ciclos ni fugas; solo mueve la comprobación de aliasing al
   runtime.

### 20.5 `Mutex[T]` y `RwLock[T]`

```pengu
summon std::sync::Arc
summon std::sync::Mutex
summon std::thread

grimoire
    bind counter = Arc.new(Mutex.new(0))
    bind c = Arc.clone(&counter)
    bind handle = thread.spawn(move () =>
        morph guard = c.lock().unwrap()
        *guard += 1
    )
    handle.join().unwrap()
    print(*counter.lock().unwrap())
```

Rust generado:

```rust
use std::sync::{Arc, Mutex};
use std::thread;

fn main() {
    let counter = Arc::new(Mutex::new(0));
    let c = Arc::clone(&counter);
    let handle = thread::spawn(move || {
        let mut guard = c.lock().unwrap();
        *guard += 1;
    });
    handle.join().unwrap();
    println!("{}", *counter.lock().unwrap());
}
```

Reglas:

1. `Mutex.new(value)` -> `Mutex::new(value)`; `lock()` devuelve
   `LockResult<MutexGuard[T>>`.
2. `lock().unwrap()` es el patrón por defecto; si el lock está envenenado
   (panic mientras se tenía), `unwrap()` propaga el panic. Una API puede usar
   `match` para recuperar el guard (`PGS-W2001`).
3. El `MutexGuard` libera el lock al salir de scope; no se puede mover fuera.
4. `RwLock` permite muchos lectores o un escritor; `read()`/`write()` siguen el
   mismo patrón.
5. Para compartir entre hilos: `Arc[Mutex[T]]` o `Arc[RwLock[T]]`. `Rc`/`RefCell`
   no cruzan hilos.
6. Un lock retenido mientras se hace I/O o se llama código desconocido puede
   bloquear el programa; mantener la sección crítica corta.

### 20.6 `Cow[Str]`

`Cow` (“clone on write”) guarda un préstamo o un valor poseído:

```pengu
bind borrowed: Cow[Str] = Cow.borrowed("pengu")
bind owned: Cow[Str] = Cow.owned(String.from("pengu"))
print(borrowed)
print(owned)
```

Rust generado:

```rust
use std::borrow::Cow;

fn main() {
    let borrowed: Cow<str> = Cow::Borrowed("pengu");
    let owned: Cow<str> = Cow::Owned(String::from("pengu"));
    println!("{}", borrowed);
    println!("{}", owned);
}
```

Reglas:

1. `Cow.borrowed(&str)` no copia; `Cow.owned(String)` posee.
2. `cow.to_mut()` clona solo si está prestado; devuelve `&mut String`.
3. `Cow[Str]` es útil en APIs que aceptan `&Str` y a veces necesitan poseer.
4. `Cow` no es un smart pointer de ownership compartido; no cuenta referencias.

### 20.7 `Pin[P]`

`Pin[P]` garantiza que el valor apuntado no se mueva. Se usa en `async` y en
estructuras auto-referenciales:

```pengu
bind pinned: Pin[Box[Int]] = Pin.new(Box.new(42))
```

Rust generado:

```rust
use std::pin::Pin;

fn main() {
    let pinned: Pin<Box<i32>> = Pin::new(Box::new(42));
    println!("{}", *pinned);
}
```

Reglas:

1. `Pin.new(pointer)` fija el valor; `Pin` no añade heap por sí mismo.
2. Un `Pin[&mut T]` no permite mover `T`; para extraerlo se necesita `T: Unpin`
   o `curse`.
3. `Pin` no es magia: si el tipo no es `Unpin`, el compilador impide moverlo.
4. §50 (async) y §51 (concurrencia) usan `Pin`; no se necesita en código normal.

### 20.8 Orden de drop con smart pointers

| Valor | Qué se libera al salir de scope |
|---|---|
| `Box[T]` | `T` y luego la allocation |
| `Rc[T]` | decrementa; si llega a 0, `T` y el bloque |
| `Arc[T]` | igual que `Rc`, con operación atómica |
| `RefCell[T]` | `T`; los `Ref`/`RefMut` vivos impiden el drop |
| `Mutex[T]` | `T` después de liberar el lock |
| `Cow[Str]` | nada si es prestado; el `String` si es poseído |

Un `Rc`/`Arc` puede mantener vivo un valor más allá del scope donde se creó; eso
es intencional, pero un ciclo sin `Weak` es una fuga de memoria lógica.

### 20.9 Ejemplo completo

```pengu
rune Node
    value: Int
    next: ?Box[Node]

grimoire
    bind list = Box.new(Node(
        value: 1,
        next: some(Box.new(Node(value: 2, next: none)))
    ))
    morph current = &list
    while current.next.is_some()
        current = current.next.as_ref().unwrap()
    print(current.value)
```

Rust generado:

```rust
struct Node {
    value: i32,
    next: Option<Box<Node>>,
}

fn main() {
    let list = Box::new(Node {
        value: 1,
        next: Some(Box::new(Node { value: 2, next: None })),
    });
    let mut current = &list;
    while current.next.is_some() {
        current = current.next.as_ref().unwrap();
    }
    println!("{}", current.value);
}
```

Este ejemplo recorre una lista enlazada sin copiar los nodos. `current` es un
`&Box<Node>`; `current.next.as_ref()` produce `Option<&Box<Node>>`.

### 20.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2001` | `Rc`/`RefCell` usado donde se exige `Send`/`Sync` | usar `Arc`/`Mutex` |
| `PGS-E2002` | `Box.clone` sin `T: Clone` | implementar `Clone` o mover |
| `PGS-E2003` | `RefCell` con préstamo mutable solapado | acortar el scope del `Ref`/`RefMut` |
| `PGS-E2004` | `Mutex` bloqueado dos veces en el mismo hilo | soltar el primer guard |
| `PGS-E2005` | `Pin` de un tipo que no se puede fijar | usar `Box::pin` o `Unpin` |
| `PGS-E2006` | `Cow` mutado sin `to_mut` | llamar `to_mut()` |
| `PGS-W2001` | `Mutex` envenenado recuperado con `unwrap` | usar `match`/`PoisonError` |
| `PGS-W2002` | ciclo `Rc`/`Arc` sin `Weak` | añadir `Weak` |

### 20.11 Criterios de aceptación

- [x] La guía de selección cubre `Box`, `Rc`, `Arc`, `Cell`, `RefCell`,
      `Mutex`, `RwLock`, `Cow` y `Pin`.
- [x] `Rc`/`Arc` distinguen conteo no atómico y atómico.
- [x] `RefCell` documenta el panic por préstamo solapado.
- [x] `Mutex`/`RwLock` enlazan con concurrencia (§51).
- [x] `Cow` y `Pin` tienen ejemplo y reglas.
- [x] El orden de drop con smart pointers está especificado.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-21-memoria"></a>
## 21. Memoria, Drop y layout

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 3 |
| Rust | `size_of`, `align_of`, `repr`, `Drop`, `ManuallyDrop`, `MaybeUninit` |
| Palabras mágicas | `@@repr`, `drop`, `curse` |
| Depende de | §16, §19, §20 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec21_memory.pengu` |

PenguScript no tiene GC ni un runtime de memoria propio. El layout, el orden de
drop y la validez de un valor siguen las reglas de Rust; el front-end solo
traduce y comprueba lo que puede en tiempo de compilación.

### 21.1 Stack, heap y valores

| Zona | Qué contiene | Quién libera |
|---|---|---|
| stack | locales, parámetros, valores `Sized` | el frame al salir |
| heap | `Box`, `Vec`, `String`, `Rc`, `Arc` | el dueño, al hacer drop |
| static | `sigil`, `relic`, literales `'static` | el programa |
| arena | bloques de una API | la arena |

Un valor `Sized` tiene un tamaño conocido en compilación y vive en el stack si no
se boxea. `Str`, `[T]` y `dyn Trait` son **unsized**: solo se usan detrás de una
referencia o un puntero inteligente (`&Str`, `Box[Str]`, `&dyn Trait`).

### 21.2 `size_of`, `align_of` y `repr`

```pengu
@@repr(C)
rune Pair
    a: U8
    b: U32

grimoire
    print(size_of[Pair]())
    print(align_of[Pair]())
```

Rust generado:

```rust
#[repr(C)]
struct Pair {
    a: u8,
    b: u32,
}

fn main() {
    println!("{}", std::mem::size_of::<Pair>());
    println!("{}", std::mem::align_of::<Pair>());
}
```

En una plataforma típica de 64 bits, `size_of[Pair]()` es `8` y
`align_of[Pair]()` es `4`: hay 3 bytes de padding entre `a` y `b`.

Reglas:

1. `size_of[T]()` -> `std::mem::size_of::<T>()`; `align_of[T]()` ->
   `std::mem::align_of::<T>()`.
2. `@@repr(C)` usa el layout de C; es obligatorio en structs que cruzan FFI.
3. `@@repr(Rust)` es el layout por defecto; el compilador puede reordenar campos.
   No se usa en FFI.
4. `@@repr(transparent)` exige un único campo no-ZST; el layout es el de ese
   campo.
5. `@@repr(u8)`/`u16`/`u32`/`u64`/`i8`/… fija la representación de un enum.
6. `@@repr(packed)` elimina padding; crear una referencia a un campo puede ser
   UB por desalineación (`PGS-E2102`). Solo se usa con copias y `read_unaligned`.
7. `@@repr(align(N))` fuerza una alineación mayor; `N` debe ser potencia de dos.

### 21.3 Orden de drop

El drop de un valor ocurre:

1. al final del scope, en orden **inverso** al de declaración de los locales;
2. en un struct, en orden de **declaración de campos** (no al revés);
3. en una tupla, de izquierda a derecha;
4. en un array, de izquierda a derecha;
5. después del cuerpo de `Drop::drop`, se dropean los campos.

```pengu
rune Loud
    name: String

-- Vista previa: la implementación de traits se define en §35.
ritual Drop for Loud
    drop = (@mut) -> Unit
        print(@.name)

grimoire
    do
        bind a = Loud(name: "a")
        bind b = Loud(name: "b")
        print("fin del bloque")
    print("fin de main")
```

Rust generado:

```rust
struct Loud {
    name: String,
}

impl Drop for Loud {
    fn drop(&mut self) {
        println!("{}", self.name);
    }
}

fn main() {
    {
        let a = Loud { name: String::from("a") };
        let b = Loud { name: String::from("b") };
        println!("fin del bloque");
    }
    println!("fin de main");
}
```

Salida:

```text
fin del bloque
b
a
fin de main
```

`b` se declara después de `a`, así que se dropea primero. El bloque interno se
dropea antes de `fin de main`.

Reglas:

1. Un tipo con `Drop` no puede moverse parcialmente: mover un campo dejaría el
   `Drop` con un valor incompleto (`PGS-E2103`).
2. `Drop::drop` recibe `@mut` (`&mut self`); no recibe `@own`.
3. `Drop` se ejecuta también durante un panic (unwind); si el panic ocurre en un
   `drop`, el programa aborta.
4. `mem::forget(value)` evita el drop; es seguro, pero puede filtrar memoria
   (`PGS-W2102`). No se usa para “liberar” antes.
5. `ManuallyDrop[T]` envuelve un valor y no lo dropea; el programador debe
   llamar `ManuallyDrop.drop` o `ManuallyDrop.take` en `curse`.
6. Los `Rc`/`Arc` pueden cambiar el momento del drop: el valor vive hasta el
   último dueño.

### 21.4 `ManuallyDrop`

```pengu
bind value = ManuallyDrop.new(String.from("pengu"))
print(*value)
```

Rust generado:

```rust
use std::mem::ManuallyDrop;

fn main() {
    let value = ManuallyDrop::new(String::from("pengu"));
    println!("{}", *value);
}
```

`ManuallyDrop` no libera el `String`; el ejemplo filtra memoria a propósito. La
forma correcta de liberarlo es `ManuallyDrop.drop(value)` dentro de `curse`.

### 21.5 `MaybeUninit`

`MaybeUninit[T]` representa memoria que puede no estar inicializada. Leerla sin
inicializar es UB; escribirla y luego llamar `assume_init` es la forma de
construir un valor manualmente:

```pengu
curse make = () -> Int
    morph slot: MaybeUninit[Int] = MaybeUninit.uninit()
    slot.write(42)
    slot.assume_init()
```

Rust generado:

```rust
use std::mem::MaybeUninit;

unsafe fn make() -> i32 {
    unsafe {
        let mut slot: MaybeUninit<i32> = MaybeUninit::uninit();
        slot.write(42);
        slot.assume_init()
    }
}
```

Reglas:

1. `MaybeUninit.uninit()` no inicializa; no se puede leer todavía.
2. `slot.write(value)` escribe sin dropear el contenido anterior.
3. `slot.assume_init()` promete que el valor está inicializado; si no, UB.
4. `MaybeUninit` se usa en `curse`, FFI, buffers y arrays grandes; no en código
   normal.
5. Un `MaybeUninit[T]` no dropea `T` automáticamente; hay que hacerlo a mano.

### 21.6 Zero-sized types y nichos

Un **ZST** ocupa 0 bytes (`struct Marker;`, `()`), pero puede tener alineación 1.
Los ZST no se reservan en el heap y un `Vec[ZST]` no asigna capacidad real.

Un **niche** es un valor inválido que el compilador usa para representar `None`
sin coste extra: `Option<&T>` tiene el mismo tamaño que `&T` porque null es un
valor imposible para una referencia. `Option<Box<T>>`, `Option<NonNull<T>>` y
`Option<NonZeroU32>` también usan nichos. `Option<i32>` no puede: necesita un
discriminante.

Reglas:

1. No se depende del tamaño exacto de un tipo `repr(Rust)`; puede cambiar entre
   versiones y plataformas.
2. Para FFI, serialización o layout binario, se usa `@@repr(C)` y se comprueba
   con `size_of`/`align_of`.
3. Un `enum` sin `repr` puede reordenar variantes; no se asume su discriminante.
4. `Option<&T>` y `Option<Box<T>>` son “gratis” en tamaño, pero `Option<i32>` no.

### 21.7 Fugas de memoria

Una fuga es memoria que ya no es alcanzable pero no se libera. En Rust una fuga
es **safe** (no viola memoria), pero puede agotar el sistema:

- `mem::forget`;
- ciclos `Rc`/`Arc` sin `Weak`;
- `ManuallyDrop` sin drop;
- un `Vec` que crece sin límite;
- `Box::leak` (convierte en `&'static mut T`).

PenguScript no prohíbe fugas; el linter avisa en patrones obvios (`PGS-W2101`).
Un `Box::leak` es explícito y se usa para valores globales inmutables, no para
“evitar el borrow checker”.

### 21.8 Ejemplo completo

```pengu
@@repr(C)
rune Header
    tag: U8
    len: U32

grimoire
    bind header = Header(tag: 1, len: 42)
    print(size_of[Header]())
    print(header.tag)
    do
        bind temp = String.from("temporal")
        print(temp)
    print("fin")
```

Rust generado:

```rust
#[repr(C)]
struct Header {
    tag: u8,
    len: u32,
}

fn main() {
    let header = Header { tag: 1, len: 42 };
    println!("{}", std::mem::size_of::<Header>());
    println!("{}", header.tag);
    {
        let temp = String::from("temporal");
        println!("{}", temp);
    }
    println!("fin");
}
```

Salida: `8`, `1`, `temporal`, `fin`. `temp` se dropea al final del bloque interno.

### 21.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2101` | `repr` incompatible con el tipo | quitar `repr` o cambiar la representación |
| `PGS-E2102` | referencia a campo de `repr(packed)` | copiar con `read_unaligned` |
| `PGS-E2103` | move parcial de un tipo con `Drop` | mover el valor completo o usar `Option` |
| `PGS-E2104` | `MaybeUninit` leído sin inicializar | escribir antes de `assume_init` |
| `PGS-E2105` | `size_of`/`align_of` sobre unsized | usar `&T`/`Box[T]` |
| `PGS-E2106` | `repr(C)` con campos no FFI-safe | usar tipos FFI-safe |
| `PGS-W2101` | fuga probable | revisar ciclos/`forget` |
| `PGS-W2102` | `mem::forget` explícito | justificar o usar `ManuallyDrop` |
| `PGS-W2103` | `repr(Rust)` en FFI | usar `repr(C)` |

### 21.10 Criterios de aceptación

- [x] Stack, heap, static y arena están diferenciados.
- [x] `size_of`, `align_of` y `repr` tienen reglas y ejemplo.
- [x] El orden de drop está especificado para locales, structs, tuplas y arrays.
- [x] `Drop`, `ManuallyDrop` y `MaybeUninit` están cubiertos.
- [x] ZST, nichos y fugas están explicados.
- [x] Los ejemplos Rust compilan.
- [x] Los diagnósticos enlazan con §16, §19 y §20.

[↑ Volver al índice](#indice)

<a id="part-4"></a>
## Parte IV — Datos y agregados

<a id="sec-22-arrays"></a>
## 22. Arrays y slices

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 4A |
| Rust | `[T; N]`, `&[T]`, `&mut [T]`, `array` |
| Palabras mágicas | `[`, `]`, `&` |
| Depende de | §2.6, §4, §17 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec22_arrays.pengu` |

Un **array** `[T; N]` tiene longitud fija conocida en compilación y vive en el
stack si no se boxea. Un **slice** `&[T]`/`&mut [T]` es una vista sobre una
secuencia contigua; no posee los elementos y no conoce su longitud en el tipo.

### 22.1 Tipo

| Forma | Significado | Tamaño |
|---|---|---|
| `[T; N]` | array de `N` elementos `T` | `N * size_of::<T>()` |
| `&[T]` | slice compartido | puntero + longitud |
| `&mut [T]` | slice mutable | puntero + longitud |
| `[[T; M]; N]` | array de arrays | `N * M * size_of::<T>()` |

`N` debe ser una constante evaluable (`Usize`). No se puede usar un valor de
runtime como longitud de array; para eso se usa `Vec[T]` (§23).

### 22.2 Literales

```pengu
bind empty: [Int; 0] = []
bind numbers = [1, 2, 3]
bind zeros = [0; 4]
bind grid = [[0; 3]; 2]
```

Forma indentada sin delimitadores:

```pengu
bind numbers =
    10
    20
    30
```

Rust generado:

```rust
fn main() {
    let empty: [i32; 0] = [];
    let numbers = [1, 2, 3];
    let zeros = [0; 4];
    let grid = [[0; 3]; 2];
    println!("{}", numbers[0] + zeros[0] + grid[0][0]);
}
```

Reglas:

1. `[a, b, c]` y la forma indentada producen `[T; N]`; `N` es el número de
   elementos.
2. `[expr; N]` repite `expr` `N` veces; `expr` debe ser `Copy` o const.
3. `[]` necesita contexto de tipo; `[Int; 0]` lo aporta.
4. Todos los elementos deben tener el mismo tipo; no hay arrays heterogéneos.
5. La forma indentada no cambia el tipo ni el orden.

### 22.3 Indexación y `get`

```pengu
bind numbers = [10, 20, 30]
print(numbers[0])
print(numbers.get(1).unwrap())
print(numbers.get(9).is_none())
```

Rust generado:

```rust
fn main() {
    let numbers = [10, 20, 30];
    println!("{}", numbers[0]);
    println!("{}", numbers.get(1).unwrap());
    println!("{}", numbers.get(9).is_none());
}
```

Reglas:

1. `array[i]` comprueba bounds en runtime y hace **panic** si `i >= N`
   (`PGS-R2201`). El compilador no puede demostrar todos los índices.
2. `array.get(i)` devuelve `?&T`; `get_mut(i)` devuelve `?&mut T`.
3. `get` es la forma segura cuando el índice viene de datos externos.
4. `len()` devuelve `Usize`; `is_empty()` equivale a `len() == 0`.
5. Un índice negativo no compila; los índices son `Usize`.

### 22.4 Slices

```pengu
bind numbers = [10, 20, 30, 40]
bind middle: &[Int] = &numbers[1..3]
print(middle.len())
print(middle[0])
```

Rust generado:

```rust
fn main() {
    let numbers = [10, 20, 30, 40];
    let middle: &[i32] = &numbers[1..3];
    println!("{}", middle.len());
    println!("{}", middle[0]);
}
```

Reglas:

1. `&array[a..b]` produce `&[T]`; `&mut array[a..b]` produce `&mut [T]`.
2. `a..b` es exclusivo; `a..=b` es inclusivo (§27).
3. El rango debe estar en bounds y en orden; si no, panic.
4. Un slice no puede vivir más que el array/`Vec` que lo respalda (§18).
5. `&array[..]` es el slice completo; `&array[1..]` va hasta el final.

### 22.5 Operaciones de slice

```pengu
bind numbers = [1, 2, 3, 4, 5, 6]
bind (left, right) = numbers.split_at(3)
print(left.len(), right.len())

for chunk in numbers.chunks(2)
    print(chunk.len())

bind window = numbers.windows(3).next().unwrap()
print(window.len())
```

Rust generado:

```rust
fn main() {
    let numbers = [1, 2, 3, 4, 5, 6];
    let (left, right) = numbers.split_at(3);
    println!("{} {}", left.len(), right.len());

    for chunk in numbers.chunks(2) {
        println!("{}", chunk.len());
    }

    let window = numbers.windows(3).next().unwrap();
    println!("{}", window.len());
}
```

Reglas:

1. `split_at(n)` devuelve `(&[T], &[T])`; `split_at_mut(n)` devuelve
   `(&mut [T], &mut [T])`.
2. `chunks(n)` produce slices de tamaño `n`; el último puede ser más corto.
3. `windows(n)` produce ventanas solapadas de tamaño `n`; si `n > len`, no hay
   ventanas.
4. `first()`/`last()` devuelven `?&T`; `first_mut()`/`last_mut()` son mutables.
5. `contains(&x)` requiere `T: PartialEq`.
6. `iter()` produce `&T`; `into_iter()` sobre `[T; N]` produce `T` (Rust 2021+).

### 22.6 Slice mutable

```pengu
morph numbers = [1, 2, 3]
bind part = &mut numbers[1..]
part[0] = 20
print(numbers[1])
```

Rust generado:

```rust
fn main() {
    let mut numbers = [1, 2, 3];
    let part = &mut numbers[1..];
    part[0] = 20;
    println!("{}", numbers[1]);
}
```

Mientras `part` vive, `numbers` no puede leerse ni moverse; el préstamo mutable
es exclusivo (§17). El `print(numbers[1])` ocurre después del último uso de
`part`, así que NLL lo permite.

### 22.7 Arrays multidimensionales

```pengu
bind grid =
    [1, 2, 3]
    [4, 5, 6]
print(grid[1][2])
```

Rust generado:

```rust
fn main() {
    let grid = [[1, 2, 3], [4, 5, 6]];
    println!("{}", grid[1][2]);
}
```

Un array multidimensional es un array de arrays; todas las filas tienen la misma
longitud. Para matrices de tamaño dinámico se usa `Vec[Vec[T]]` o una crate de
álgebra lineal.

### 22.8 Conversiones

| Operación | PenguScript | Rust |
|---|---|---|
| array a slice | `&array[..]` | `&array[..]` |
| slice a array | `array.try_into().unwrap()` | `TryInto` |
| array a `Vec` | `Vec.from(array)` | `Vec::from(array)` |
| `Vec` a slice | `&vec[..]` | `&vec[..]` |
| repetir | `[expr; N]` | `[expr; N]` |
| generar | `array.from_fn(N, f)` | `std::array::from_fn` |

`array.try_into()` falla si la longitud no coincide; el resultado es
`![T; N]`-style `Result<[T; N], _>`. PenguScript exige `unwrap()` o `match`; no
hay conversión implícita de slice a array.

### 22.9 Ejemplo completo

```pengu
bind scores =
    90
    80
    70

bind total = scores[0] + scores[1] + scores[2]
print(total)

bind average = total / scores.len() as Int
print(average)

bind top = &scores[0..2]
print(top.len())
```

Rust generado:

```rust
fn main() {
    let scores = [90, 80, 70];

    let total = scores[0] + scores[1] + scores[2];
    println!("{}", total);

    let average = total / scores.len() as i32;
    println!("{}", average);

    let top = &scores[0..2];
    println!("{}", top.len());
}
```

### 22.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2201` | longitudes de array incompatibles | usar `Vec` o convertir |
| `PGS-E2202` | índice de tipo no entero | usar `Usize` |
| `PGS-E2203` | array sin contexto de tipo | anotar `[T; N]` |
| `PGS-E2204` | slice con rango invertido | corregir `a..b` |
| `PGS-E2205` | array demasiado grande para el stack | usar `Vec`/`Box` |
| `PGS-W2201` | indexación directa con índice externo | usar `get` |
| `PGS-W2202` | slice que retiene un préstamo largo | acortar el scope |

### 22.11 Criterios de aceptación

- [x] `[T; N]`, `&[T]` y `&mut [T]` están diferenciados.
- [x] Literales inline e indentados producen el mismo tipo.
- [x] Indexación, `get` y bounds están explicados.
- [x] Slices, `split_at`, `chunks`, `windows` y `iter` están cubiertos.
- [x] Arrays multidimensionales y conversiones están documentados.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-23-vectores"></a>
## 23. Vectores y `VecDeque`

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 4A |
| Rust | `Vec<T>`, `VecDeque<T>` |
| Palabras mágicas | `Vec` |
| Depende de | §22 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec23_vectors.pengu` |

`Vec[T]` es una secuencia contigua de longitud variable en el heap. Crece
amortizando `O(1)` por push y permite indexación `O(1)`. `VecDeque[T]` es una
cola doble terminada; crece por ambos extremos y usa un buffer circular.

### 23.1 Literal

```pengu
bind empty: Vec[Int] = Vec[]
bind numbers = Vec[1, 2, 3]
bind zeros = Vec[0; 4]
```

Forma indentada sin delimitadores:

```pengu
bind numbers = Vec
    10
    20
    30
```

Rust generado:

```rust
fn main() {
    let empty: Vec<i32> = Vec::new();
    let numbers = vec![1, 2, 3];
    let zeros = vec![0; 4];
    println!("{} {} {}", empty.len(), numbers.len(), zeros.len());
}
```

Reglas:

1. `Vec[a, b, c]` -> `vec![a, b, c]`.
2. `Vec[expr; N]` -> `vec![expr; N]`; `N` puede ser runtime, a diferencia de un
   array.
3. `Vec[]` necesita contexto de tipo; `Vec[Int]` lo aporta.
4. El literal reserva exactamente lo necesario (o una capacidad cercana); para
   reservar una capacidad concreta se usa `Vec.with_capacity`.
5. La forma indentada es equivalente a la inline.

### 23.2 Construcción y capacidad

```pengu
morph values = Vec.with_capacity(10)
values.push(1)
print(values.capacity() >= 10)
print(values.len())
```

Rust generado:

```rust
fn main() {
    let mut values = Vec::with_capacity(10);
    values.push(1);
    println!("{}", values.capacity() >= 10);
    println!("{}", values.len());
}
```

Reglas:

1. `Vec.new()` crea vacío sin reservar; `Vec.with_capacity(n)` reserva `n`.
2. `capacity()` es cuántos elementos caben sin reasignar; `len()` es cuántos hay.
3. `push` puede reasignar y duplicar la capacidad; no se asume un valor exacto.
4. `reserve(n)`/`reserve_exact(n)` piden capacidad adicional.
5. `shrink_to_fit()` reduce la capacidad al `len`; puede reasignar.

### 23.3 Operaciones principales

```pengu
morph values = Vec[3, 1, 2, 2]
values.sort()
values.dedup()
values.insert(0, 9)
print(values.len())
print(values[0])
print(values.pop().unwrap())
```

Rust generado:

```rust
fn main() {
    let mut values = vec![3, 1, 2, 2];
    values.sort();
    values.dedup();
    values.insert(0, 9);
    println!("{}", values.len());
    println!("{}", values[0]);
    println!("{}", values.pop().unwrap());
}
```

| Operación | Coste | Nota |
|---|---|---|
| `push`/`pop` al final | amortizado `O(1)` | el más rápido |
| `insert(i)`/`remove(i)` | `O(n)` | desplaza el resto |
| `sort` | `O(n log n)` | requiere `Ord` |
| `dedup` | `O(n)` | requiere `PartialEq`; solo borra consecutivos |
| `retain` | `O(n)` | conserva los que cumplen el predicado |
| `binary_search` | `O(log n)` | requiere estar ordenado |
| `contains` | `O(n)` | usa `PartialEq` |

### 23.4 `retain`, `drain` y `binary_search`

```pengu
morph values = Vec[1, 2, 3, 4, 5]
values.retain((x: Int) => x % 2 == 0)
print(values.len())

bind index = values.binary_search(&4).unwrap()
print(index)
```

Rust generado:

```rust
fn main() {
    let mut values = vec![1, 2, 3, 4, 5];
    values.retain(|x| x % 2 == 0);
    println!("{}", values.len());

    let index = values.binary_search(&4).unwrap();
    println!("{}", index);
}
```

Reglas:

1. `retain(f)` conserva los elementos para los que `f` devuelve `true`; el
   predicado recibe `&T`.
2. `drain(a..b)` elimina y devuelve un iterador sobre el rango; si no se consume,
   el iterador dropea los elementos al salir de scope.
3. `binary_search(&x)` devuelve `Result[Usize, Usize]`: `ok(index)` si lo
   encuentra, `err(posición de inserción)` si no. Requiere orden.
4. `sort()` usa `Ord`; `sort_by`/`sort_by_key` permiten criterios propios.
5. `dedup()` solo elimina duplicados **consecutivos**; ordenar antes si se quiere
   eliminar todos.

### 23.5 Slices de un `Vec`

```pengu
bind values = Vec[10, 20, 30, 40]
bind middle: &[Int] = &values[1..3]
print(middle.len())
print(middle[0])
```

Rust generado:

```rust
fn main() {
    let values = vec![10, 20, 30, 40];
    let middle: &[i32] = &values[1..3];
    println!("{}", middle.len());
    println!("{}", middle[0]);
}
```

Un `Vec` se dereferencia a `[T]`, así que `&values[..]` produce `&[T]`. Mientras
el slice vive, el `Vec` no puede reasignarse ni modificarse de forma que lo
invalide.

### 23.6 `VecDeque`

```pengu
morph queue = VecDeque.new()
queue.push_back(1)
queue.push_front(0)
print(queue.pop_front().unwrap())
print(queue.len())
```

Rust generado:

```rust
use std::collections::VecDeque;

fn main() {
    let mut queue = VecDeque::new();
    queue.push_back(1);
    queue.push_front(0);
    println!("{}", queue.pop_front().unwrap());
    println!("{}", queue.len());
}
```

Reglas:

1. `VecDeque.new()` crea una cola vacía; `with_capacity(n)` reserva.
2. `push_back`/`pop_back` y `push_front`/`pop_front` son `O(1)` amortizado.
3. `VecDeque` se usa para colas, buffers circulares y ventanas deslizantes.
4. No es contiguo; para acceso indexado intensivo se prefiere `Vec`.
5. `make_contiguous()` puede reorganizar el buffer para devolver un slice
   contiguo; es `O(n)`.

### 23.7 Elección `Vec` vs. `VecDeque` vs. array

| Necesidad | Tipo | Razón |
|---|---|---|
| tamaño fijo conocido | `[T; N]` | sin heap, sin longitud dinámica |
| crecer al final | `Vec[T]` | contiguo, rápido al final |
| crecer por ambos extremos | `VecDeque[T]` | buffer circular |
| acceso indexado intensivo | `Vec[T]`/`[T; N]` | localidad de caché |
| cola FIFO/LIFO | `VecDeque[T]` | `pop_front` barato |
| compartir sin copiar | `&[T]` | vista |

### 23.8 Ejemplo completo

```pengu
morph scores = Vec
    70
    90
    80
scores.push(100)
scores.sort()
print(scores.len())
print(scores[0])
print(scores.pop().unwrap())
```

Rust generado:

```rust
fn main() {
    let mut scores = vec![70, 90, 80];
    scores.push(100);
    scores.sort();
    println!("{}", scores.len());
    println!("{}", scores[0]);
    println!("{}", scores.pop().unwrap());
}
```

### 23.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2301` | `Vec[]` sin contexto de tipo | anotar `Vec[T]` |
| `PGS-E2302` | índice fuera de rango | usar `get` o comprobar `len` |
| `PGS-E2303` | `sort` sin `Ord` | usar `sort_by` o derivar `Ord` |
| `PGS-E2304` | `dedup` sin `PartialEq` | derivar `PartialEq` |
| `PGS-E2305` | `drain` con rango inválido | corregir el rango |
| `PGS-W2301` | `Vec` que crece sin reservar | usar `with_capacity` si se conoce |
| `PGS-W2302` | `insert(0, x)` repetido | usar `VecDeque` |

### 23.10 Criterios de aceptación

- [x] `Vec[T]` y sus literales inline/indentados están definidos.
- [x] Construcción, capacidad y operaciones principales están cubiertas.
- [x] `retain`, `drain` y `binary_search` tienen ejemplo.
- [x] Slices de `Vec` y sus préstamos están explicados.
- [x] `VecDeque` y la guía de elección están incluidos.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-24-tuplas"></a>
## 24. Tuplas

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 4A |
| Rust | `()`, `(A, B)`, tuplas de hasta 12 |
| Palabras mágicas | `(`, `)`, `,` |
| Depende de | §2.6, §4 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec24_tuples.pengu` |

Una **tupla** agrupa valores de tipos posiblemente distintos con una longitud
fija. Es un producto cartesiano: `(A, B)` contiene un `A` y un `B`. No es una
colección homogénea; para eso se usa un array o un `Vec`.

### 24.1 Tipo y valores

```pengu
bind unit: Unit = ()
bind one = (42,)
bind pair = (42, "pengu")
bind triple = (1, 2.5, true)
```

Rust generado:

```rust
fn main() {
    let unit: () = ();
    let one = (42,);
    let pair = (42, "pengu");
    let triple = (1, 2.5, true);
    println!("{} {} {} {}", unit == (), one.0, pair.0, triple.2);
}
```

Reglas:

1. `()` es el único valor de `Unit`; no confundir con `none`.
2. `(x,)` es una tupla de un elemento; la coma es obligatoria.
3. `(x)` es agrupación, no una tupla.
4. `(a, b)` tiene tipo `(A, B)`; el orden importa.
5. Los elementos pueden ser de tipos distintos; no hay coerción entre ellos.
6. La longitud es parte del tipo: `(Int, Int)` y `(Int, Int, Int)` son distintos.

### 24.2 Acceso

```pengu
bind pair = (42, "pengu")
print(pair.0)
print(pair.1)
```

Rust generado:

```rust
fn main() {
    let pair = (42, "pengu");
    println!("{}", pair.0);
    println!("{}", pair.1);
}
```

Reglas:

1. `tuple.0`, `tuple.1`, … acceden por índice; el índice es un literal, no un
   valor de runtime.
2. No se puede escribir `tuple[i]` con `i` variable; para eso se usa un array.
3. `tuple.0` se puede asignar si la tupla es `morph` y el campo es mutable.
4. Acceder a un índice inexistente es error de compilación (`PGS-E2401`).

### 24.3 Destructuring

```pengu
bind (id, name) = (7, "pengu")
print(id)
print(name)
```

Rust generado:

```rust
fn main() {
    let (id, name) = (7, "pengu");
    println!("{}", id);
    println!("{}", name);
}
```

Reglas:

1. `bind (a, b) = expr` desestructura una tupla; `a` y `b` son bindings nuevos.
2. `morph (a, b) = expr` permite reasignar `a`/`b` después.
3. `_` ignora un elemento: `bind (id, _) = pair`.
4. La aridad debe coincidir; no hay “resto” en una tupla (`..` no aplica).
5. El destructuring de tuplas se usa también en `for`, `match` y parámetros
   (§30).

### 24.4 Retorno de tuplas

```pengu
make_pair = () -> (Int, String)
    (1, "one")

bind (n, s) = make_pair()
print(n)
print(s)
```

Rust generado:

```rust
fn make_pair() -> (i32, &'static str) {
    (1, "one")
}

fn main() {
    let (n, s) = make_pair();
    println!("{}", n);
    println!("{}", s);
}
```

Las tuplas permiten devolver varios valores sin definir un `rune`. Si el
resultado tiene semántica propia o se usa en una API pública, se prefiere un
`rune` con nombres; una tupla es más frágil porque el orden es posicional.

### 24.5 Anidación

```pengu
bind nested = ((1, 2), (3, 4))
print(nested.0.1)
print(nested.1.0)
```

Rust generado:

```rust
fn main() {
    let nested = ((1, 2), (3, 4));
    println!("{}", nested.0.1);
    println!("{}", nested.1.0);
}
```

Una tupla puede contener tuplas, arrays, `Vec`, `Option`, etc. El tipo se infiere
de los elementos; no hay tuplas heterogéneas “dinámicas”.

### 24.6 Tuple structs (adelanto de §28)

Un **tuple struct** es un `rune` con campos posicionales:

```pengu
rune Point(Int, Int)
bind p = Point(1, 2)
print(p.0)
```

Rust generado:

```rust
struct Point(i32, i32);

fn main() {
    let p = Point(1, 2);
    println!("{}", p.0);
}
```

A diferencia de una tupla, `Point` es un tipo nominal: `Point(1, 2)` no es
intercambiable con `(1, 2)`. §28 define la sintaxis completa y la visibilidad.

### 24.7 Traits en tuplas

Rust implementa automáticamente estos traits para tuplas hasta 12 elementos si
todos sus elementos los implementan:

| Trait | Requisito |
|---|---|
| `Clone` | todos los elementos `Clone` |
| `Copy` | todos los elementos `Copy` |
| `Debug` | todos los elementos `Debug` |
| `PartialEq`/`Eq` | todos los elementos correspondientes |
| `PartialOrd`/`Ord` | todos los elementos correspondientes |
| `Hash` | todos los elementos `Hash` |
| `Default` | todos los elementos `Default` |

Las tuplas de 13 o más elementos no implementan estos traits automáticamente; si
se necesitan, se usa un `rune`.

### 24.8 Coste y layout

Una tupla se layouta como sus campos en orden de declaración, con padding para
alinear cada campo. `size_of::<(u8, u32)>()` suele ser `8`, no `5`, por el
padding. El orden de drop es de izquierda a derecha (§21).

### 24.9 Ejemplo completo

```pengu
min_max = (a: Int, b: Int) -> (Int, Int)
    if a <= b then (a, b) else (b, a)

bind (low, high) = min_max(7, 3)
print(low)
print(high)
```

Rust generado:

```rust
fn min_max(a: i32, b: i32) -> (i32, i32) {
    if a <= b { (a, b) } else { (b, a) }
}

fn main() {
    let (low, high) = min_max(7, 3);
    println!("{}", low);
    println!("{}", high);
}
```

### 24.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2401` | índice de tupla inexistente | usar un índice válido o un `rune` |
| `PGS-E2402` | aridad distinta en destructuring | ajustar el patrón |
| `PGS-E2403` | tupla de 13+ elementos con `Debug` | usar un `rune` |
| `PGS-E2404` | `tuple[i]` con índice variable | usar un array |
| `PGS-W2401` | tupla usada como API pública | preferir un `rune` con nombres |

### 24.11 Criterios de aceptación

- [x] `Unit`, tupla de un elemento y tuplas múltiples están diferenciadas.
- [x] Acceso `.0` y destructuring están definidos.
- [x] Retorno de tuplas y anidación tienen ejemplo.
- [x] Los tuple structs se distinguen de las tuplas.
- [x] Los traits automáticos y el límite de 12 están documentados.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-25-mapas"></a>
## 25. Mapas y sets

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 4A |
| Rust | `HashMap<K,V>`, `HashSet<T>`, `BTreeMap<K,V>`, `BTreeSet<T>` |
| Palabras mágicas | `{`, `}`, `:`, `Set` |
| Depende de | §2.6, §22–§24 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec25_maps.pengu` |

Un **mapa** asocia claves únicas con valores. Un **set** es un mapa sin valores:
solo claves. PenguScript expone las cuatro variantes de Rust con nombres
explícitos; no hay un “mapa por defecto” implícito.

| Tipo | Orden | Inserción | Búsqueda | Uso |
|---|---|---|---|---|
| `HashMap[K,V]` | no | `O(1)` promedio | `O(1)` promedio | uso general |
| `BTreeMap[K,V]` | por clave | `O(log n)` | `O(log n)` | iterar ordenado |
| `HashSet[T]` | no | `O(1)` promedio | `O(1)` promedio | pertenencia |
| `BTreeSet[T]` | por valor | `O(log n)` | `O(log n)` | pertenencia ordenada |

### 25.1 Literales

```pengu
bind ages =
    "pengu": 3
    "seal": 5

bind tags = Set
    "magic"
    "static"
```

Rust generado:

```rust
use std::collections::{HashMap, HashSet};

fn main() {
    let ages = HashMap::from([
        ("pengu", 3),
        ("seal", 5),
    ]);

    let tags = HashSet::from([
        "magic",
        "static",
    ]);

    println!("{} {}", ages.len(), tags.len());
}
```

Reglas:

1. La forma inline `{ "clave": valor, ... }` o la forma indentada
   `clave: valor` (sin `{}`) producen un `HashMap` por defecto.
2. La forma inline `Set[valor, ...]` o `Set` + cuerpo indentado (sin `[]`)
   producen un `HashSet` por defecto.
3. Para `BTreeMap`/`BTreeSet` se usa `BTreeMap.from(...)`/`BTreeSet.from(...)` o
   una anotación de tipo; el literal no elige el orden.
4. Las claves deben implementar `Eq + Hash` para `HashMap`/`HashSet`, y `Ord`
   para `BTreeMap`/`BTreeSet`.
5. Claves duplicadas en un literal: gana la última; el compilador avisa
   (`PGS-W2501`).
6. `name: 1` (clave identificador) equivale a `"name": 1`; una clave calculada
   usa `[expr]: valor`.

### 25.2 Inserción, lectura y actualización

```pengu
morph ages = HashMap.new()
ages.insert("pengu", 3)
ages.insert("seal", 5)
ages.insert("pengu", 4)

print(ages.len())
print(ages.get("pengu").unwrap())
print(ages.contains_key("seal"))
```

Rust generado:

```rust
use std::collections::HashMap;

fn main() {
    let mut ages = HashMap::new();
    ages.insert("pengu", 3);
    ages.insert("seal", 5);
    ages.insert("pengu", 4);

    println!("{}", ages.len());
    println!("{}", ages.get("pengu").unwrap());
    println!("{}", ages.contains_key("seal"));
}
```

Reglas:

1. `insert(k, v)` devuelve `?V`: el valor anterior si la clave ya existía.
2. `get(&k)` devuelve `?&V`; `get_mut(&k)` devuelve `?&mut V`.
3. `contains_key(&k)` devuelve `Bool`; no inserta.
4. `remove(&k)` devuelve `?V`.
5. `len()` es el número de claves; `is_empty()` equivale a `len() == 0`.
6. `clear()` elimina todas las entradas sin cambiar la capacidad reservada.

### 25.3 `entry`

```pengu
morph counts = HashMap.new()
bind count = counts.entry("a").or_insert(0)
*count += 1
print(counts.get("a").unwrap())
```

Rust generado:

```rust
use std::collections::HashMap;

fn main() {
    let mut counts = HashMap::new();
    let count = counts.entry("a").or_insert(0);
    *count += 1;
    println!("{}", counts.get("a").unwrap());
}
```

`entry(k)` devuelve una `Entry`; las operaciones principales son:

| Método | Efecto |
|---|---|
| `or_insert(v)` | inserta `v` si falta; devuelve `&mut V` |
| `or_insert_with(f)` | calcula `v` solo si falta |
| `or_default()` | usa `V::default()` si falta |
| `and_modify(f)` | modifica el valor existente |
| `key()` | devuelve la clave de la entrada |

`entry` evita hacer dos búsquedas (una para `get`, otra para `insert`).

### 25.4 Sets

```pengu
morph tags = Set["magic", "static"]
tags.insert("safe")
tags.remove("static")
print(tags.contains("magic"))
print(tags.len())
```

Rust generado:

```rust
use std::collections::HashSet;

fn main() {
    let mut tags = HashSet::from(["magic", "static"]);
    tags.insert("safe");
    tags.remove("static");
    println!("{}", tags.contains("magic"));
    println!("{}", tags.len());
}
```

Reglas:

1. `insert(x)` devuelve `Bool`: `true` si era nuevo, `false` si ya estaba.
2. `contains(&x)` no modifica.
3. `remove(&x)` devuelve `Bool`.
4. Las operaciones de conjuntos son `union`, `intersection`, `difference` y
   `symmetric_difference`; devuelven iteradores.
5. `is_subset`/`is_superset`/`is_disjoint` comparan dos sets.

### 25.5 Mapas ordenados

```pengu
bind sorted = BTreeMap.from([
    ("b", 2)
    ("a", 1)
    ("c", 3)
])

for (key, value) in sorted
    print(key, value)
```

Rust generado:

```rust
use std::collections::BTreeMap;

fn main() {
    let sorted = BTreeMap::from([
        ("b", 2),
        ("a", 1),
        ("c", 3),
    ]);

    for (key, value) in sorted {
        println!("{} {}", key, value);
    }
}
```

`BTreeMap` itera en orden de clave (`Ord`), no en orden de inserción. Es la
elección cuando se necesita `range(a..b)` o una salida determinista sin ordenar
después.

### 25.6 `Hash` y `Eq`

Para usar una clave en `HashMap`/`HashSet`, el tipo debe implementar `Eq` y
`Hash` de forma coherente: si `a == b`, entonces `hash(a) == hash(b)`. En un
`rune`, se deriva con:

```pengu
@@derive(PartialEq, Eq, Hash)
rune UserId(Int)
```

Reglas:

1. `f64` no implementa `Eq`/`Hash`; no puede ser clave de un `HashMap`.
2. Los tipos con campos mutables no deberían usarse como clave si el hash cambia.
3. `BTreeMap` requiere `Ord`, no `Hash`.
4. Un hasher personalizado se pasa con `HashMap.with_hasher(...)`; el hasher debe
   implementar `BuildHasher`.
5. La coherencia `Eq`/`Hash` es responsabilidad del tipo; el compilador no la
   demuestra.

### 25.7 Indexar vs. `get`

```pengu
bind ages = { "pengu": 3 }
print(ages["pengu"])
```

Rust generado:

```rust
use std::collections::HashMap;

fn main() {
    let ages = HashMap::from([("pengu", 3)]);
    println!("{}", ages["pengu"]);
}
```

`map[k]` hace panic si la clave no existe (`PGS-R2501`); `get` devuelve `?V` y
obliga a manejar el caso ausente. En API pública se prefiere `get`; en un
invariante interno demostrado se puede usar `[]`.

### 25.8 Complejidad y elección

| Operación | `HashMap` | `BTreeMap` |
|---|---|---|
| insert | `O(1)` promedio | `O(log n)` |
| get | `O(1)` promedio | `O(log n)` |
| remove | `O(1)` promedio | `O(log n)` |
| iterar ordenado | no | sí |
| rango por clave | no | sí |
| peor caso | `O(n)` | `O(log n)` |

`HashMap` es más rápido en promedio, pero su orden no está especificado y puede
sufrir ataques de colisiones si las claves son adversarias. `BTreeMap` es más
predecible y permite rangos.

### 25.9 Ejemplo completo

```pengu
bind text = "pengu pengu seal"
morph counts = HashMap.new()

for word in text.split_whitespace()
    bind count = counts.entry(word).or_insert(0)
    *count += 1

print(counts.len())
print(counts.get("pengu").unwrap())
```

Rust generado:

```rust
use std::collections::HashMap;

fn main() {
    let text = "pengu pengu seal";
    let mut counts = HashMap::new();

    for word in text.split_whitespace() {
        let count = counts.entry(word).or_insert(0);
        *count += 1;
    }

    println!("{}", counts.len());
    println!("{}", counts.get("pengu").unwrap());
}
```

### 25.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2501` | clave sin `Eq + Hash` | derivar o usar `BTreeMap` |
| `PGS-E2502` | clave sin `Ord` en `BTreeMap` | derivar `Ord` |
| `PGS-E2503` | `map[k]` con clave posiblemente ausente | usar `get`/`entry` |
| `PGS-E2504` | préstamo mutable y lectura simultánea | separar scopes |
| `PGS-E2505` | set con elemento no hashable | cambiar el tipo |
| `PGS-W2501` | clave duplicada en literal | eliminar duplicado |
| `PGS-W2502` | `HashMap` iterado esperando orden | usar `BTreeMap` |

### 25.11 Criterios de aceptación

- [x] Los cuatro tipos de mapa/set están diferenciados.
- [x] Literales inline/indentados y claves identificador están definidos.
- [x] Inserción, `get`, `entry`, `remove` y `contains` están cubiertos.
- [x] `Hash`/`Eq` y la elección `HashMap` vs. `BTreeMap` están explicados.
- [x] Indexar vs. `get` y los diagnósticos están incluidos.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-26-estructuras-datos"></a>
## 26. Otras estructuras de datos

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 4A |
| Rust | `VecDeque`, `LinkedList`, `BinaryHeap`, `BTreeSet` |
| Palabras mágicas | — |
| Depende de | §22–§25 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec26_structures.pengu` |

Este capítulo cubre las estructuras de la biblioteca estándar que no son
arrays, `Vec`, tuplas, mapas ni sets. Ninguna es “mejor” en abstracto: la
elección depende del patrón de acceso y de la complejidad que se necesita.

### 26.1 `VecDeque`

`VecDeque[T]` es una cola doble terminada con buffer circular. `push_front`,
`push_back`, `pop_front` y `pop_back` son `O(1)` amortizado.

```pengu
morph queue = VecDeque.new()
queue.push_back(1)
queue.push_back(2)
queue.push_front(0)

print(queue.pop_front().unwrap())
print(queue.pop_back().unwrap())
print(queue.len())
```

Rust generado:

```rust
use std::collections::VecDeque;

fn main() {
    let mut queue = VecDeque::new();
    queue.push_back(1);
    queue.push_back(2);
    queue.push_front(0);

    println!("{}", queue.pop_front().unwrap());
    println!("{}", queue.pop_back().unwrap());
    println!("{}", queue.len());
}
```

Usos: colas FIFO/LIFO, buffers circulares, ventanas deslizantes, planificadores.
No es contiguo; si se necesita un slice, `make_contiguous()` es `O(n)`.

### 26.2 `LinkedList`

`LinkedList[T]` es una lista doblemente enlazada. Insertar/eliminar en los
extremos es `O(1)`, pero acceder por índice es `O(n)` y cada nodo es una
asignación separada.

```pengu
morph list = LinkedList.new()
list.push_back(2)
list.push_front(1)
list.push_back(3)

print(list.len())
print(list.front().unwrap())
print(list.back().unwrap())
```

Rust generado:

```rust
use std::collections::LinkedList;

fn main() {
    let mut list = LinkedList::new();
    list.push_back(2);
    list.push_front(1);
    list.push_back(3);

    println!("{}", list.len());
    println!("{}", list.front().unwrap());
    println!("{}", list.back().unwrap());
}
```

En la práctica `LinkedList` se usa poco: `Vec`/`VecDeque` suelen ganar por
localidad de caché. Es útil para splicing frecuente si ya se tiene un cursor,
pero la API de Rust no expone cursores estables.

### 26.3 `BinaryHeap`

`BinaryHeap[T]` es un max-heap: `peek()`/`pop()` devuelven el mayor elemento.
Requiere `T: Ord`.

```pengu
morph heap = BinaryHeap.new()
heap.push(3)
heap.push(1)
heap.push(5)

print(heap.peek().unwrap())
print(heap.pop().unwrap())
print(heap.len())
```

Rust generado:

```rust
use std::collections::BinaryHeap;

fn main() {
    let mut heap = BinaryHeap::new();
    heap.push(3);
    heap.push(1);
    heap.push(5);

    println!("{}", heap.peek().unwrap());
    println!("{}", heap.pop().unwrap());
    println!("{}", heap.len());
}
```

Para un min-heap se envuelve el valor en `Reverse`:

```pengu
morph min_heap = BinaryHeap.new()
min_heap.push(Reverse(3))
min_heap.push(Reverse(1))
print(min_heap.pop().unwrap().0)
```

Rust generado:

```rust
use std::cmp::Reverse;
use std::collections::BinaryHeap;

fn main() {
    let mut min_heap = BinaryHeap::new();
    min_heap.push(Reverse(3));
    min_heap.push(Reverse(1));
    println!("{}", min_heap.pop().unwrap().0);
}
```

Usos: colas de prioridad, Dijkstra, `k` elementos mayores/menores, simulaciones
de eventos. `BinaryHeap` no es estable: elementos iguales pueden salir en
cualquier orden.

### 26.4 `BTreeSet`

`BTreeSet[T]` es un set ordenado; iterar produce los elementos en orden `Ord`.
Es la contraparte de `HashSet` cuando se necesita orden o rangos.

```pengu
bind values = BTreeSet.from([3, 1, 2])

for value in values
    print(value)
```

Rust generado:

```rust
use std::collections::BTreeSet;

fn main() {
    let values = BTreeSet::from([3, 1, 2]);

    for value in values {
        println!("{}", value);
    }
}
```

### 26.5 Comparación de complejidades

| Estructura | Acceso por índice | Inserción al final | Inserción al inicio | Búsqueda | Orden |
|---|---|---|---|---|---|
| `[T; N]` | `O(1)` | — | — | `O(n)` | no |
| `Vec[T]` | `O(1)` | `O(1)` amort. | `O(n)` | `O(n)` | no |
| `VecDeque[T]` | `O(1)` | `O(1)` amort. | `O(1)` amort. | `O(n)` | no |
| `LinkedList[T]` | `O(n)` | `O(1)` | `O(1)` | `O(n)` | no |
| `BinaryHeap[T]` | — | `O(log n)` | — | `O(n)` | parcial |
| `HashMap[K,V]` | — | `O(1)` prom. | — | `O(1)` prom. | no |
| `BTreeMap[K,V]` | — | `O(log n)` | — | `O(log n)` | sí |
| `HashSet[T]` | — | `O(1)` prom. | — | `O(1)` prom. | no |
| `BTreeSet[T]` | — | `O(log n)` | — | `O(log n)` | sí |

### 26.6 Crates externas

La biblioteca estándar no cubre todos los casos. Algunas alternativas comunes
(no forman parte del lenguaje; se declaran en `Tome.toml`):

| Crate | Estructura | Cuándo |
|---|---|---|
| `indexmap` | `IndexMap`/`IndexSet` | orden de inserción + búsqueda hash |
| `smallvec` | `SmallVec` | pocos elementos sin heap |
| `arrayvec` | `ArrayVec` | capacidad fija sin heap |
| `dashmap` | `DashMap` | concurrencia con sharding |
| `crossbeam` | colas | MPSC/MPMC |
| `petgraph` | grafos | algoritmos de grafos |
| `slotmap` | slots | claves estables con reuso |

Regla: una estructura externa debe justificar su dependencia; si la API pública
la expone, se documenta en el `pact` correspondiente para no acoplar a los
usuarios a la crate.

### 26.7 Ejemplo completo

```pengu
morph tasks = BinaryHeap.new()
tasks.push(2)
tasks.push(5)
tasks.push(1)

print(tasks.pop().unwrap())
print(tasks.pop().unwrap())
print(tasks.pop().unwrap())
```

Rust generado:

```rust
use std::collections::BinaryHeap;

fn main() {
    let mut tasks = BinaryHeap::new();
    tasks.push(2);
    tasks.push(5);
    tasks.push(1);

    println!("{}", tasks.pop().unwrap());
    println!("{}", tasks.pop().unwrap());
    println!("{}", tasks.pop().unwrap());
}
```

### 26.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2601` | `BinaryHeap` con tipo sin `Ord` | derivar `Ord` o usar `Reverse` |
| `PGS-E2602` | índice en `LinkedList` | usar `Vec`/`VecDeque` |
| `PGS-E2603` | `VecDeque` usado como slice | `make_contiguous()` |
| `PGS-E2604` | estructura externa sin dependencia | añadir a `Tome.toml` |
| `PGS-W2601` | `LinkedList` para acceso secuencial | preferir `Vec`/`VecDeque` |
| `PGS-W2602` | `BinaryHeap` esperando orden estable | añadir un contador de desempate |

### 26.9 Criterios de aceptación

- [x] `VecDeque`, `LinkedList`, `BinaryHeap` y `BTreeSet` están cubiertos.
- [x] Cada estructura tiene ejemplo Rust compilable.
- [x] La tabla de complejidades está incluida.
- [x] Las crates externas y su justificación están documentadas.
- [x] Los diagnósticos distinguen errores de rendimiento.

[↑ Volver al índice](#indice)

<a id="sec-27-rangos"></a>
## 27. Rangos e indexación

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 4A |
| Rust | `Range<T>`, `RangeInclusive<T>`, `RangeFrom`, `RangeTo`, `..` |
| Palabras mágicas | `..`, `..=` |
| Depende de | §22–§26 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec27_ranges.pengu` |

Un **rango** representa un intervalo de valores. No es una colección: es un
valor de primera clase que se puede iterar, usar como índice de slice, comparar
o pasar a una función. Hay rangos exhaustivos (`a..b`, `a..=b`) y abiertos
(`a..`, `..b`, `..=b`, `..`).

### 27.1 Formas

| Forma | Tipo Rust | Incluye |
|---|---|---|
| `a..b` | `Range<T>` | `a <= x < b` |
| `a..=b` | `RangeInclusive<T>` | `a <= x <= b` |
| `a..` | `RangeFrom<T>` | `x >= a` |
| `..b` | `RangeTo<T>` | `x < b` |
| `..=b` | `RangeToInclusive<T>` | `x <= b` |
| `..` | `RangeFull` | todo |

```pengu
bind exclusive = 1..5
bind inclusive = 1..=5
bind from = 3..
bind to = ..3
bind values = [10, 20, 30]
bind all = &values[..]

print(exclusive.contains(&3))
print(inclusive.contains(&5))
print(from.contains(&4))
print(to.contains(&2))
print(all.len())
```

Rust generado:

```rust
fn main() {
    let exclusive = 1..5;
    let inclusive = 1..=5;
    let from = 3..;
    let to = ..3;
    let values = [10, 20, 30];
    let all = &values[..];

    println!("{}", exclusive.contains(&3));
    println!("{}", inclusive.contains(&5));
    println!("{}", from.contains(&4));
    println!("{}", to.contains(&2));
    println!("{}", all.len());
}
```

`RangeFull` (`..`) se usa como índice (`&values[..]`), no como valor con
`contains`; para comprobar pertenencia se usa un rango concreto.

### 27.2 Rangos como iteradores

```pengu
morph total = 0
for i in 0..5
    total += i
print(total)

for i in (0..6).step_by(2)
    print(i)

for i in (0..3).rev()
    print(i)
```

Rust generado:

```rust
fn main() {
    let mut total = 0;
    for i in 0..5 {
        total += i;
    }
    println!("{}", total);

    for i in (0..6).step_by(2) {
        println!("{}", i);
    }

    for i in (0..3).rev() {
        println!("{}", i);
    }
}
```

Reglas:

1. `a..b` e `a..=b` son iterables si `T` implementa `Step` (enteros, `char`).
2. `step_by(n)` requiere `n > 0`; si `n == 0`, panic.
3. `rev()` requiere un iterador de doble extremo; los rangos lo son.
4. `for i in 0..n` no incluye `n`; `0..=n` sí.
5. Un rango vacío (`5..5`, `5..=4`) no produce elementos; no es un error.

### 27.3 Rangos como índices

```pengu
bind values = [10, 20, 30, 40]
bind middle = &values[1..3]
print(middle.len())
print(values.get(1..9).is_none())
```

Rust generado:

```rust
fn main() {
    let values = [10, 20, 30, 40];
    let middle = &values[1..3];
    println!("{}", middle.len());
    println!("{}", values.get(1..9).is_none());
}
```

Reglas:

1. `&slice[a..b]` y `&slice[a..=b]` producen `&[T]`; con `mut`, `&mut [T]`.
2. El rango debe estar en bounds y en orden; si no, panic (`PGS-R2701`).
3. `get(a..b)` devuelve `?&[T]` y no hace panic; es la forma segura para rangos
   calculados.
4. `get_mut(a..b)` devuelve `?&mut [T]`.
5. `..` como índice significa el slice completo: `&values[..]`.

### 27.4 Rangos en patterns

```pengu
classify = (n: Int) -> &'static Str
    match n
        when 0..=9 then "digit"
        when 10..=99 then "two digits"
        else "many"

print(classify(7))
print(classify(42))
```

Rust generado:

```rust
fn classify(n: i32) -> &'static str {
    match n {
        0..=9 => "digit",
        10..=99 => "two digits",
        _ => "many",
    }
}

fn main() {
    println!("{}", classify(7));
    println!("{}", classify(42));
}
```

En un pattern, `a..=b` es inclusivo y `a..b` exclusivo; `..` ignora el resto de
los campos de un `rune`/tupla. Los rangos de patterns deben ser exhaustivos o
tener un caso `_`.

### 27.5 Rangos indentados

La forma indentada es opcional y equivalente:

```pengu
bind r = 1..
    10

for i in r
    print(i)
```

Rust generado:

```rust
fn main() {
    let r = 1..10;

    for i in r {
        println!("{}", i);
    }
}
```

Reglas:

1. El operador `..`/`..=` queda al final de la línea; el endpoint va en la línea
   siguiente, indentado un nivel.
2. El cierre no lleva delimitador; el rango termina en el endpoint.
3. `1..` con endpoint indentado es `1..10`; no confundir con `1..` abierto.
4. Para un rango abierto se escribe `1..` sin línea de endpoint.
5. La forma indentada no cambia el tipo ni la semántica.

### 27.6 `contains`, `split_at` y búsqueda

```pengu
bind r = 10..20
print(r.contains(&15))
print(r.contains(&20))

bind values = [1, 2, 3, 4, 5]
bind (left, right) = values.split_at(2)
print(left.len(), right.len())
```

Rust generado:

```rust
fn main() {
    let r = 10..20;
    println!("{}", r.contains(&15));
    println!("{}", r.contains(&20));

    let values = [1, 2, 3, 4, 5];
    let (left, right) = values.split_at(2);
    println!("{} {}", left.len(), right.len());
}
```

`r.contains(&20)` es `false` porque `10..20` es exclusivo. `split_at` no es un
rango, pero comparte la idea de partir una secuencia en dos mitades.

### 27.7 Rangos y préstamos

Un rango de índices no presta nada por sí mismo; el préstamo ocurre al indexar:

```pengu
bind values = [1, 2, 3]
bind r = 1..3
bind part = &values[r]
print(part.len())
```

Rust generado:

```rust
fn main() {
    let values = [1, 2, 3];
    let r = 1..3;
    let part = &values[r];
    println!("{}", part.len());
}
```

Mientras `part` vive, `values` no puede modificarse. El rango `r` es `Copy` si
`T: Copy`; no retiene el préstamo.

### 27.8 Ejemplo completo

```pengu
bind values = [10, 20, 30, 40, 50]
bind window = &values[1..4]
print(window.len())

morph total = 0
for value in window
    total += value
print(total)

for i in 0..3
    print(i)
```

Rust generado:

```rust
fn main() {
    let values = [10, 20, 30, 40, 50];
    let window = &values[1..4];
    println!("{}", window.len());

    let mut total = 0;
    for value in window {
        total += value;
    }
    println!("{}", total);

    for i in 0..3 {
        println!("{}", i);
    }
}
```

### 27.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2701` | rango invertido | corregir `a..b` |
| `PGS-E2702` | rango fuera de bounds en índice | usar `get` o comprobar `len` |
| `PGS-E2703` | `step_by(0)` | usar un paso positivo |
| `PGS-E2704` | rango no iterable | usar un tipo `Step` o un iterador |
| `PGS-E2705` | pattern de rango no exhaustivo | añadir `_` |
| `PGS-W2701` | índice con rango calculado sin comprobar | usar `get` |
| `PGS-W2702` | `..` en una API pública | acotar el rango |

### 27.10 Criterios de aceptación

- [x] Las seis formas de rango están diferenciadas.
- [x] Rangos como iteradores, índices y patterns están cubiertos.
- [x] La forma indentada está definida y ejemplificada.
- [x] `contains`, `split_at` y préstamos están explicados.
- [x] Los diagnósticos incluyen rangos invertidos y fuera de bounds.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-28-structs"></a>
## 28. Structs (`rune`)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 4B |
| Rust | `struct` |
| Palabras mágicas | `rune`, `unveil`, `@@derive`, `@@repr` |
| Depende de | §4, §17, §24 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec28_structs.pengu` |

Un **`rune`** es un tipo producto con nombre. Tiene tres formas: nombrada (campos
con nombre), de tupla (campos posicionales) y unitaria (sin campos). Es nominal:
`Point` y `Vector` con los mismos campos son tipos distintos.

### 28.1 Struct nombrada

```pengu
rune Point
    x: Float
    y: Float

bind p = Point(x: 3.0, y: 4.0)
print(p.x)
print(p.y)
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

fn main() {
    let p = Point { x: 3.0, y: 4.0 };
    println!("{}", p.x);
    println!("{}", p.y);
}
```

Reglas:

1. La cabecera `rune Nombre` va en una línea; los campos van indentados un nivel.
2. Cada campo es `nombre: Tipo`; no hay valores por defecto.
3. El orden de los campos es el orden de declaración; afecta al layout y al drop.
4. Un `rune` sin campos y sin paréntesis es unitario (§28.3).
5. Los campos son privados por defecto; `unveil` los expone (§28.4).

### 28.2 Struct de tupla

```pengu
rune Pair(Int, Int)
rune UserId(UInt)

bind pair = Pair(1, 2)
bind id = UserId(7)
print(pair.0)
print(id.0)
```

Rust generado:

```rust
struct Pair(i32, i32);
struct UserId(u32);

fn main() {
    let pair = Pair(1, 2);
    let id = UserId(7);
    println!("{}", pair.0);
    println!("{}", id.0);
}
```

Reglas:

1. `rune Nombre(T1, T2, ...)` declara campos posicionales.
2. Se accede con `.0`, `.1`, …; no hay nombres.
3. Los campos de un tuple struct son **privados** en PenguScript; si se necesita
   exponerlos, se usa una struct nombrada con `unveil` por campo. Esto evita una
   sintaxis de visibilidad posicional ambigua (`PGS-E2805`).
4. Un tuple struct de un campo es la forma canónica de **newtype** (§32).
5. Se puede usar en patterns: `when Pair(a, b)`.

### 28.3 Struct unitaria

```pengu
rune Marker
rune Ready

bind marker = Marker
bind ready = Ready
print(marker == Marker)
```

Rust generado:

```rust
#[derive(PartialEq)]
struct Marker;
#[derive(PartialEq)]
struct Ready;

fn main() {
    let marker = Marker;
    let ready = Ready;
    println!("{}", marker == Marker);
}
```

Una struct unitaria es un **ZST** (zero-sized type): no ocupa bytes y se usa como
marcador de tipo, token o estado. `Marker` y `Ready` son tipos distintos aunque
ambos sean ZST.

### 28.4 Visibilidad de campos

```pengu
unveil rune PublicPoint
    unveil x: Float
    y: Float

bind p = PublicPoint(x: 1.0, y: 2.0)
print(p.x)
```

Rust generado:

```rust
pub struct PublicPoint {
    pub x: f64,
    y: f64,
}

fn main() {
    let p = PublicPoint { x: 1.0, y: 2.0 };
    println!("{}", p.x);
}
```

Formas:

| Forma | Efecto | Rust |
|---|---|---|
| sin `unveil` | privado al módulo | campo privado |
| `unveil` | público | `pub` |
| `unveil(tome)` | visible en el tome | `pub(crate)` |
| `unveil(scroll)` | visible en el padre | `pub(super)` |

`unveil` en un campo debe ir al inicio de la línea del campo. No se permite
`unveil` en campos de tuple structs ni en variantes de enum; esas variantes
heredan la visibilidad del tipo contenedor.

### 28.5 Genéricos y `where`

```pengu
rune Holder[T]
    value: T

rune Wrapper[T] where T: Clone
    value: T

bind h = Holder(value: 42)
bind w = Wrapper(value: "pengu")
print(h.value)
print(w.value)
```

Rust generado:

```rust
struct Holder<T> {
    value: T,
}

struct Wrapper<T>
where
    T: Clone,
{
    value: T,
}

fn main() {
    let h = Holder { value: 42 };
    let w = Wrapper { value: "pengu" };
    println!("{}", h.value);
    println!("{}", w.value);
}
```

Reglas:

1. Los parámetros de tipo van entre `[T]` después del nombre.
2. Los bounds pueden ir en la cabecera con `where`, como en funciones.
3. Un `rune` genérico puede tener campos que usan `T`, `[T; N]`, `?T`, etc.
4. La inferencia del parámetro ocurre en el literal o en la anotación.
5. Sin `PhantomData`, un parámetro de tipo no usado es error (`PGS-E2803`).

### 28.6 `@@derive` y `@@repr`

```pengu
@@derive(Clone, Debug, PartialEq)
rune Version
    major: Int
    minor: Int

@@repr(C)
rune Header
    tag: U8
    len: U32

bind v = Version(major: 1, minor: 2)
print(v.clone().major)
print(size_of[Header]())
```

Rust generado:

```rust
#[derive(Clone, Debug, PartialEq)]
struct Version {
    major: i32,
    minor: i32,
}

#[repr(C)]
struct Header {
    tag: u8,
    len: u32,
}

fn main() {
    let v = Version { major: 1, minor: 2 };
    println!("{}", v.clone().major);
    println!("{}", std::mem::size_of::<Header>());
}
```

Reglas:

1. `@@derive(...)` se traduce a `#[derive(...)]`; los traits permitidos son los
   de Rust (`Clone`, `Copy`, `Debug`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`,
   `Hash`, `Default`).
2. `@@derive(Copy)` exige que todos los campos sean `Copy`; `Clone` no implica
   `Copy`.
3. `@@repr(C)`, `@@repr(transparent)`, `@@repr(packed)` y `@@repr(u8/u16/...)`
   se traducen literalmente.
4. `@@repr(packed)` puede producir referencias desalineadas; se documenta en
   §21 y §52.
5. Los atributos van antes del `rune`, en líneas propias; no dentro del cuerpo.

### 28.7 `PhantomData`

```pengu
rune Tagged[T]
    value: Int
    marker: PhantomData[T]

bind tagged: Tagged[String] = Tagged(value: 1, marker: PhantomData)
print(tagged.value)
```

Rust generado:

```rust
use std::marker::PhantomData;

struct Tagged<T> {
    value: i32,
    marker: PhantomData<T>,
}

fn main() {
    let tagged: Tagged<&str> = Tagged {
        value: 1,
        marker: PhantomData,
    };
    println!("{}", tagged.value);
}
```

`PhantomData[T]` no ocupa espacio; le dice al compilador que `Tagged[T]` “posee”
un `T` a efectos de variance, drop y auto traits. Se usa cuando `T` no aparece en
ningún campo real.

### 28.8 DST y ZST

Un **DST** (dynamically sized type) no tiene tamaño conocido en compilación. El
último campo de una struct puede ser unsized:

```pengu
rune Buffer
    len: Usize
    data: [U8]
```

Rust generado:

```rust
struct Buffer {
    len: usize,
    data: [u8],
}
```

No se puede crear un `Buffer` por valor; se usa detrás de `&Buffer`, `Box[Buffer]`
o `Rc[Buffer]`. El compilador calcula el tamaño del prefijo y guarda la longitud
del DST en el puntero graso.

Un **ZST** es una struct unitaria o una struct con solo campos ZST. No ocupa
espacio, pero conserva identidad de tipo. `PhantomData` es el ZST estándar para
marcar parámetros.

### 28.9 Literales: shorthand y actualización

```pengu
rune Point
    x: Float
    y: Float

bind x = 1.0
bind y = 2.0
bind p = Point(x: x, y: y)
bind moved = Point(x: 3.0, ..p)
print(moved.x)
print(moved.y)
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

fn main() {
    let x = 1.0;
    let y = 2.0;
    let p = Point { x, y };
    let moved = Point { x: 3.0, ..p };
    println!("{}", moved.x);
    println!("{}", moved.y);
}
```

Reglas:

1. `Point(x: x, y: y)` usa **field init shorthand** cuando el nombre del binding
   coincide con el campo; se genera `Point { x, y }`.
2. La sintaxis de actualización es `Point(campo: valor, ..base)`: `..base` va al
   final y copia/mueve los campos no mencionados.
3. `..base` requiere que `base` sea del mismo tipo; los campos movidos no pueden
   usarse después si no son `Copy`.
4. Un literal debe mencionar todos los campos o usar `..base`; no hay defaults.
5. `Point(..)` no es válido como literal; el rest solo aparece con `base`.

### 28.10 Acceso y mutación

```pengu
rune Counter
    value: Int

morph counter = Counter(value: 0)
counter.value += 1
print(counter.value)
```

Rust generado:

```rust
struct Counter {
    value: i32,
}

fn main() {
    let mut counter = Counter { value: 0 };
    counter.value += 1;
    println!("{}", counter.value);
}
```

Un campo se lee con `obj.campo` y se escribe con `obj.campo = valor` si `obj` es
`morph`. La mutabilidad del binding se propaga al campo; no hay campos `mut`
individuales. Para mutabilidad interior se usa `Cell`/`RefCell`/`Mutex` (§20).

### 28.11 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2801` | campo duplicado | eliminar o renombrar |
| `PGS-E2802` | campo faltante en el literal | añadir el campo o `..base` |
| `PGS-E2803` | parámetro de tipo no usado | añadir `PhantomData` |
| `PGS-E2804` | `@@derive` no soportado en el campo | derivar en el `rune` |
| `PGS-E2805` | `unveil` en campo de tuple struct | usar struct nombrada |
| `PGS-E2806` | `..base` no es el último | moverlo al final |
| `PGS-W2801` | struct con muchos campos públicos | revisar encapsulación |
| `PGS-W2802` | `repr(packed)` en API pública | revisar alineación |

### 28.12 Criterios de aceptación

- [x] Structs nombradas, de tupla y unitarias están diferenciadas.
- [x] La visibilidad por campo y sus límites están definidos.
- [x] Genéricos, `where`, `@@derive` y `@@repr` tienen ejemplo.
- [x] `PhantomData`, DST y ZST están cubiertos.
- [x] Shorthand y `..base` están especificados.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-29-enums"></a>
## 29. Enums (`enchanting`)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 4B |
| Rust | `enum` |
| Palabras mágicas | `enchanting`, `@@repr`, `@@non_exhaustive` |
| Depende de | §28, §30 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec29_enums.pengu` |

Un **`enchanting`** es un tipo suma: un valor es exactamente una de sus
variantes. Cada variante puede ser unitaria, de tupla o de struct. Es la forma
de modelar “uno de varios casos” sin null ni herencia.

### 29.1 Variantes

```pengu
enchanting Shape
    Circle(Float)
    Rectangle(Float, Float)
    Empty
```

Rust generado:

```rust
enum Shape {
    Circle(f64),
    Rectangle(f64, f64),
    Empty,
}
```

Reglas:

1. `Circle(Float)` es una variante de tupla con un campo.
2. `Rectangle(Float, Float)` tiene dos campos posicionales.
3. `Empty` es una variante unitaria (sin datos).
4. Una variante de struct se escribe con campos indentados:

```pengu
enchanting Message
    Quit
    Move
        x: Int
        y: Int
    Write(String)
```

Rust generado:

```rust
enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
}
```

5. Los nombres de variante deben ser únicos dentro del enum (`PGS-E2902`).
6. Las variantes heredan la visibilidad del enum; no se permite `unveil` por
   variante.

### 29.2 Construcción

```pengu
bind circle = Circle(2.0)
bind rect = Rectangle(3.0, 4.0)
bind empty = Empty
bind move = Move(x: 1, y: 2)
```

Rust generado:

```rust
enum Shape {
    Circle(f64),
    Rectangle(f64, f64),
    Empty,
}

enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
}

fn main() {
    let circle = Shape::Circle(2.0);
    let rect = Shape::Rectangle(3.0, 4.0);
    let empty = Shape::Empty;
    let mv = Message::Move { x: 1, y: 2 };
    println!("{}", match empty { Shape::Empty => "empty", _ => "other" });
    println!("{}", match circle { Shape::Circle(r) => r, _ => 0.0 });
    println!("{}", match rect { Shape::Rectangle(w, h) => w * h, _ => 0.0 });
    println!("{}", match mv { Message::Move { x, y } => x + y, _ => 0 });
}
```

En PenguScript, el nombre de la variante es suficiente si el tipo esperado es
conocido (`bind circle: Shape = Circle(2.0)`). Si hay ambigüedad entre enums, se
califica con `Shape.Circle(2.0)` o se anota el binding.

### 29.3 `Option` y `Result` son enums

`?T` es `Option[T]` y `!T` es `Result[T, Error]`. Sus variantes son `some(x)` /
`none` y `ok(x)` / `err(e)`:

```pengu
bind maybe: ?Int = some(3)
bind result: !Int = ok(7)

match maybe
    when some(x) then print(x)
    when none then print(0)

match result
    when ok(x) then print(x)
    when err(e) then print(e)
```

Rust generado:

```rust
fn main() {
    let maybe: Option<i32> = Some(3);
    let result: Result<i32, Box<dyn std::error::Error + Send + Sync>> = Ok(7);

    match maybe {
        Some(x) => println!("{}", x),
        None => println!("0"),
    }

    match result {
        Ok(x) => println!("{}", x),
        Err(e) => println!("{}", e),
    }
}
```

`Option` y `Result` están en la prelude; no se redeclaran. Un `match` sobre ellos
debe cubrir ambas variantes o usar `else`.

### 29.4 Discriminantes y `@@repr`

```pengu
@@repr(u8)
enchanting Level
    Low = 1
    High = 2

bind level = High
print(level as Int)
```

Rust generado:

```rust
#[repr(u8)]
enum Level {
    Low = 1,
    High = 2,
}

fn main() {
    let level = Level::High;
    println!("{}", level as i32);
}
```

Reglas:

1. Los discriminantes solo se permiten en variantes unitarias.
2. Sin `@@repr`, el discriminante se infiere desde 0; con `@@repr(u8)`, el
   almacenamiento es `u8`.
3. `as` convierte una variante fieldless a su discriminante; no se permite `as`
   sobre una variante con datos (`PGS-E2904`).
4. `@@repr(C)` fija el layout para FFI; `@@repr(u8/u16/u32/u64/usize)` fija el
   entero subyacente.
5. Los discriminantes no pueden repetirse (`PGS-E2903`).

### 29.5 `@@non_exhaustive`

```pengu
@@non_exhaustive
enchanting ApiError
    NotFound
    Denied
    Unknown
```

`@@non_exhaustive` se traduce a `#[non_exhaustive]`: los consumidores de otra
crate deben incluir un brazo `_`/`else`. Dentro de la crate que lo define, el
`match` sigue siendo exhaustivo sin `else`.

### 29.6 Optimización de nicho

Rust puede reutilizar un valor inválido de un tipo para representar una variante
sin ocupar espacio extra (niche optimization). Ejemplos:

| Tipo | Tamaño típico | Nicho |
|---|---|---|
| `?&T` | igual que `&T` | puntero nulo |
| `?Box[T]` | igual que `Box[T]` | puntero nulo |
| `?Bool` | 1 byte | tercer valor de `bool` |
| `?Char` | 4 bytes | escalar inválido |

PenguScript no garantiza un tamaño concreto salvo con `@@repr`; la optimización
es una propiedad de Rust que puede cambiar. Para FFI se usa `@@repr(C)` y no se
asume nicho.

### 29.7 Métodos

```pengu
enchanting Shape
    Circle(Float)
    Rectangle(Float, Float)

ritual Shape
    area = (@) -> Float
        match @
            when Circle(r) then 3.141592653589793 * r * r
            when Rectangle(w, h) then w * h

bind s = Circle(2.0)
print(s.area())
```

Rust generado:

```rust
enum Shape {
    Circle(f64),
    Rectangle(f64, f64),
}

impl Shape {
    fn area(&self) -> f64 {
        match self {
            Shape::Circle(r) => 3.141592653589793 * r * r,
            Shape::Rectangle(w, h) => w * h,
        }
    }
}

fn main() {
    let s = Shape::Circle(2.0);
    println!("{}", s.area());
}
```

### 29.8 `match` y exhaustividad

```pengu
label = (shape: &Shape) -> &'static Str
    match shape
        when Circle(_) then "círculo"
        when Rectangle(_, _) then "rectángulo"

bind s = Circle(1.0)
print(label(&s))
```

Un `match` sin `else` debe cubrir todas las variantes. Si `Shape` es
`@@non_exhaustive` desde otra crate, el compilador exige `else`. §30 define
patrones, guardas y `if let`.

### 29.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2901` | variante duplicada | renombrar |
| `PGS-E2902` | nombre de variante no único | renombrar |
| `PGS-E2903` | discriminante duplicado | cambiar el valor |
| `PGS-E2904` | `as` sobre variante con datos | usar `match` |
| `PGS-E2905` | `match` no exhaustivo | añadir variante o `else` |
| `PGS-E2906` | `@@repr` inválido para la variante | usar fieldless o cambiar repr |
| `PGS-W2901` | enum con una sola variante | considerar un `rune` |
| `PGS-W2902` | `@@non_exhaustive` sin `else` fuera de la crate | añadir `else` |

### 29.10 Criterios de aceptación

- [x] Variantes unitarias, de tupla y de struct están diferenciadas.
- [x] Construcción y calificación de variantes están definidas.
- [x] `Option`/`Result` se reconocen como enums de la prelude.
- [x] Discriminantes, `@@repr` y `@@non_exhaustive` están cubiertos.
- [x] La optimización de nicho se explica sin garantizar tamaños.
- [x] `ritual` sobre un enum tiene ejemplo.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-30-pattern-matching"></a>
## 30. Pattern matching

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 4B |
| Rust | `match`, `if let`, `while let`, `let-else` |
| Palabras mágicas | `match`, `when`, `else`, `@` (pattern) |
| Depende de | §13, §14, §28, §29 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec30_patterns.pengu` |

El **pattern matching** descompone un valor y elige un camino según su forma. Un
patrón puede ser refutable (no cubre todos los valores) o irrefutable (cubre
todos). `bind` y los parámetros exigen patrones irrefutables; `match`, `if` y
`while` aceptan refutables.

### 30.1 `match`

```pengu
label = (n: Int) -> &'static Str
    match n
        when 0 then "cero"
        when 1 | 2 | 3 then "pequeño"
        when 4..=9 then "mediano"
        else "grande"

print(label(0))
print(label(2))
print(label(7))
print(label(42))
```

Rust generado:

```rust
fn label(n: i32) -> &'static str {
    match n {
        0 => "cero",
        1 | 2 | 3 => "pequeño",
        4..=9 => "mediano",
        _ => "grande",
    }
}

fn main() {
    println!("{}", label(0));
    println!("{}", label(2));
    println!("{}", label(7));
    println!("{}", label(42));
}
```

Reglas:

1. La cabecera es `match expr`; los brazos van indentados.
2. Cada brazo empieza por `when`; el patrón va después.
3. `then expr` es un brazo inline; si se omite `then`, el cuerpo es un bloque
   indentado.
4. `else expr` es el brazo por defecto; debe ser el último.
5. El `match` evalúa el scrutinee una vez y elige el primer brazo que coincide.
6. Todos los brazos deben producir el mismo tipo; `Never` se unifica con
   cualquiera (§8).
7. Sin `else`, el `match` debe ser exhaustivo (`PGS-E3005`).

### 30.2 Patrones

| Patrón | Ejemplo | Rust |
|---|---|---|
| literal | `when 0` | `0` |
| binding | `when x` | `x` |
| wildcard | `when _` | `_` |
| tupla | `when (a, b)` | `(a, b)` |
| struct | `when Point(x, y)` | `Point { x, y }` |
| struct con nombres | `when Point(x: a, y: b)` | `Point { x: a, y: b }` |
| enum unitaria | `when none` | `None` |
| enum de tupla | `when some(x)` | `Some(x)` |
| enum de struct | `when Move(x: x, y: y)` | `Move { x, y }` |
| slice | `when [first, .., last]` | `[first, .., last]` |
| rango | `when 0..=9` | `0..=9` |
| or | `when 1 \| 2` | `1 \| 2` |
| binding `@` | `when whole @ 1..=9` | `whole @ 1..=9` |
| `ref` | `when ref x` | `ref x` |
| `ref mut` | `when ref mut x` | `ref mut x` |
| rest | `when Point(x, ..)` | `Point { x, .. }` |

### 30.3 Guardas

```pengu
classify = (n: Int) -> &'static Str
    match n
        when x if x < 0 then "negativo"
        when x if x == 0 then "cero"
        when x then "positivo"

print(classify(-3))
print(classify(0))
print(classify(5))
```

Rust generado:

```rust
fn classify(n: i32) -> &'static str {
    match n {
        x if x < 0 => "negativo",
        x if x == 0 => "cero",
        x => "positivo",
    }
}

fn main() {
    println!("{}", classify(-3));
    println!("{}", classify(0));
    println!("{}", classify(5));
}
```

Una guarda es `if condición` después del patrón, antes de `then`. Si la guarda
falla, se prueba el siguiente brazo; el binding del patrón no se filtra.

### 30.4 Structs, enums y `..`

```pengu
rune Point
    x: Int
    y: Int

enchanting Shape
    Circle(Int)
    Rectangle(Int, Int)
    Empty

origin = (shape: &Shape) -> Point
    match shape
        when Circle(r) then Point(x: 0, y: 0)
        when Rectangle(w, h) then Point(x: w, y: h)
        when Empty then Point(x: 0, y: 0)

bind s = Rectangle(3, 4)
bind p = origin(&s)
print(p.x)
print(p.y)
```

Rust generado:

```rust
struct Point {
    x: i32,
    y: i32,
}

enum Shape {
    Circle(i32),
    Rectangle(i32, i32),
    Empty,
}

fn origin(shape: &Shape) -> Point {
    match shape {
        Shape::Circle(r) => Point { x: 0, y: 0 },
        Shape::Rectangle(w, h) => Point { x: *w, y: *h },
        Shape::Empty => Point { x: 0, y: 0 },
    }
}

fn main() {
    let s = Shape::Rectangle(3, 4);
    let p = origin(&s);
    println!("{}", p.x);
    println!("{}", p.y);
}
```

En un patrón de struct, `Point(x, y)` es shorthand de `Point(x: x, y: y)`. El
resto `..` ignora los campos no mencionados: `Point(x, ..)`.

### 30.5 `@` como binding de patrón

`@` en un patrón **no** es el receptor `@`; liga el valor completo a un nombre:

```pengu
describe = (n: Int) -> &'static Str
    match n
        when whole @ 1..=9 then "dígito #{whole}"
        else "fuera"

print(describe(7))
```

Rust generado:

```rust
fn describe(n: i32) -> String {
    match n {
        whole @ 1..=9 => format!("dígito {}", whole),
        _ => "fuera".to_string(),
    }
}

fn main() {
    println!("{}", describe(7));
}
```

El contexto distingue `@` de receptor: en un patrón siempre es binding; en una
expresión o en la cabecera de un método es `self`. No se puede usar `@` como
nombre de binding.

### 30.6 `ref` y `ref mut`

El match ergonomics de Rust ya toma préstamos automáticamente cuando el
scrutinee es una referencia. `ref`/`ref mut` fuerzan un préstamo explícito:

```pengu
rune Pair(Int, Int)

bind pair = Pair(1, 2)
match pair
    when Pair(ref a, _) then print(a)
```

Rust generado:

```rust
struct Pair(i32, i32);

fn main() {
    let pair = Pair(1, 2);
    match pair {
        Pair(ref a, _) => println!("{}", a),
    }
}
```

Reglas:

1. `ref x` liga `&T`; `ref mut x` liga `&mut T` y exige un scrutinee mutable.
2. En la mayoría de casos no se necesitan; el compilador aplica match ergonomics.
3. `ref`/`ref mut` no se usan en `bind`; allí el binding ya decide el préstamo.
4. Un `ref mut` sobre un valor no mutable es error (`PGS-E3007`).

### 30.7 `if let`

La forma `if PATRÓN = EXPR` es azúcar de `match` con un solo brazo y `else`
opcional:

```pengu
bind maybe: ?Int = some(3)

if some(x) = maybe then
    print(x)
else
    print(0)
```

Rust generado:

```rust
fn main() {
    let maybe: Option<i32> = Some(3);

    if let Some(x) = maybe {
        println!("{}", x);
    } else {
        println!("0");
    }
}
```

Reglas:

1. El patrón a la izquierda de `=` debe ser refutable; un binding simple es
   error (`PGS-E3001`).
2. El `if` produce `Unit` salvo que ambas ramas produzcan el mismo tipo; sin
   `else`, produce `Unit`.
3. `elseif` no se usa con `if let`; se anida o se usa `match`.
4. El binding solo vive en la rama `then`.

### 30.8 `while let`

```pengu
morph values = Vec[1, 2, 3]

while some(x) = values.pop()
    print(x)
```

Rust generado:

```rust
fn main() {
    let mut values = vec![1, 2, 3];

    while let Some(x) = values.pop() {
        println!("{}", x);
    }
}
```

`while PATRÓN = EXPR` reevalúa `EXPR` en cada iteración y termina cuando el
patrón no coincide. El cuerpo es `Unit`; no hay `break value`.

### 30.9 `let-else`

`bind`/`morph` con `else` es la forma `let-else`: si el patrón es refutable y no
coincide, se ejecuta el bloque `else`, que debe divergir.

```pengu
first = (maybe: ?Int) -> Int
    bind some(x) = maybe else
        return 0
    x

print(first(some(7)))
print(first(none))
```

Rust generado:

```rust
fn first(maybe: Option<i32>) -> i32 {
    let Some(x) = maybe else {
        return 0;
    };
    x
}

fn main() {
    println!("{}", first(Some(7)));
    println!("{}", first(None));
}
```

Reglas:

1. Sin `else`, el patrón de `bind`/`morph` debe ser irrefutable.
2. Con `else`, el patrón puede ser refutable; el bloque `else` debe divergir
   (`return`, `break`, `continue`, `panic` o `Never`).
3. El binding vive después del `bind`/`else`; no en el bloque `else`.
4. `morph` con `else` permite mutar el binding resultante.

### 30.10 Exhaustividad y refutabilidad

- Un patrón es **irrefutable** si cubre todos los valores del tipo: un binding,
  `_`, una tupla de irrefutables, una struct de irrefutables.
- Es **refutable** si puede fallar: literales, rangos, variantes concretas,
  slices con longitud fija.
- `match` sin `else` exige cubrir todas las variantes; los rangos deben cubrir
  todo el dominio o tener `else`.
- `if let`/`while let` aceptan refutables por definición.
- `bind`/`morph` exigen irrefutables salvo que tengan `else`.
- `Bool` requiere `true` y `false`; no hay truthiness (§12).

### 30.11 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3001` | patrón irrefutable en `if let` | usar `bind` o un patrón refutable |
| `PGS-E3002` | `match` no exhaustivo | añadir variante/`else` |
| `PGS-E3003` | tipo incompatible entre brazos | unificar o convertir |
| `PGS-E3004` | `..` en posición inválida | moverlo al final del patrón |
| `PGS-E3005` | falta `else` en `match` abierto | añadir `else` |
| `PGS-E3006` | binding `@` con nombre reservado | renombrar |
| `PGS-E3007` | `ref mut` sobre valor inmutable | usar `morph` |
| `PGS-E3009` | `else` de `let-else` no diverge | añadir `return`/`panic` |
| `PGS-E3010` | guarda no `Bool` | usar una condición `Bool` |
| `PGS-W3001` | `_` que oculta un valor útil | nombrar el binding |
| `PGS-W3002` | `match` con un solo brazo | considerar `if let` |

### 30.12 Criterios de aceptación

- [x] `match`, brazos `when`, `else` y guardas están definidos.
- [x] Todos los patrones de tipos agregados están cubiertos.
- [x] `if let`, `while let` y `let-else` tienen ejemplo.
- [x] `@` de patrón se distingue del receptor `@`.
- [x] Exhaustividad y refutabilidad están explicadas.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-31-implementaciones"></a>
## 31. Implementaciones (`ritual`)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 4B |
| Rust | `impl` |
| Palabras mágicas | `ritual`, `pact`, `@`, `@mut`, `@own`, `Self` |
| Depende de | §15, §28, §29 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec31_impls.pengu` |

Un **`ritual`** implementa métodos y funciones asociadas para un tipo. Es el
equivalente de `impl` en Rust: no crea herencia ni subtipos; agrupa
comportamiento.

### 31.1 `ritual` inherente

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    new = (x: Float, y: Float) -> Point
        Point(x: x, y: y)

    origin = () -> Point
        Point(x: 0.0, y: 0.0)

    length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

    translate = (@mut, dx: Float, dy: Float) -> Unit
        @.x = @.x + dx
        @.y = @.y + dy

    into_pair = (@own) -> (Float, Float)
        (@.x, @.y)

bind p = Point.new(3.0, 4.0)
print(p.length())
print(Point.origin().length())
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn new(x: f64, y: f64) -> Point {
        Point { x, y }
    }

    fn origin() -> Point {
        Point { x: 0.0, y: 0.0 }
    }

    fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }

    fn translate(&mut self, dx: f64, dy: f64) {
        self.x = self.x + dx;
        self.y = self.y + dy;
    }

    fn into_pair(self) -> (f64, f64) {
        (self.x, self.y)
    }
}

fn main() {
    let p = Point::new(3.0, 4.0);
    println!("{}", p.length());
    println!("{}", Point::origin().length());
}
```

Reglas:

1. La cabecera es `ritual Tipo`; el cuerpo va indentado.
2. Un método es `nombre = (receptores, params) -> Tipo`.
3. `@` = `&self`, `@mut` = `&mut self`, `@own` = `self`.
4. Una función asociada no lleva receptor: `origin = () -> Point`.
5. `@` solo existe dentro de un método con receptor; en una función asociada
   es error (`PGS-E3101`).
6. `Self` se refiere al tipo implementado; se puede usar como tipo de retorno o
   en parámetros.
7. Los métodos no se sobrecargan: un nombre por `ritual` y tipo (`PGS-E3102`).
8. Las implementaciones inherentes solo se permiten para tipos locales
   (`PGS-E3105`).

### 31.2 Receptores

| Receptor | Rust | Mutabilidad | Consumo |
|---|---|---|---|
| `@` | `&self` | no | préstamo |
| `@mut` | `&mut self` | sí | préstamo mutable |
| `@own` | `self` | sí | mueve |

```pengu
rune Counter
    value: Int

ritual Counter
    get = (@) -> Int
        @.value

    add = (@mut, n: Int) -> Unit
        @.value = @.value + n

    consume = (@own) -> Int
        @.value

morph c = Counter(value: 0)
c.add(3)
print(c.get())
print(c.consume())
```

Rust generado:

```rust
struct Counter {
    value: i32,
}

impl Counter {
    fn get(&self) -> i32 {
        self.value
    }

    fn add(&mut self, n: i32) {
        self.value = self.value + n;
    }

    fn consume(self) -> i32 {
        self.value
    }
}

fn main() {
    let mut c = Counter { value: 0 };
    c.add(3);
    println!("{}", c.get());
    println!("{}", c.consume());
}
```

Llamar a `@mut` exige un binding `morph`; llamar a `@own` mueve el valor y no se
puede volver a usar.

### 31.3 `Self`

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    shifted = (@, dx: Float, dy: Float) -> Self
        Point(x: @.x + dx, y: @.y + dy)

    same = (@) -> Bool
        @.x == 0.0 and @.y == 0.0

bind p = Point(x: 1.0, y: 2.0)
print(p.shifted(1.0, 1.0).same())
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn shifted(&self, dx: f64, dy: f64) -> Self {
        Point {
            x: self.x + dx,
            y: self.y + dy,
        }
    }

    fn same(&self) -> bool {
        self.x == 0.0 && self.y == 0.0
    }
}

fn main() {
    let p = Point { x: 1.0, y: 2.0 };
    println!("{}", p.shifted(1.0, 1.0).same());
}
```

`Self` no se puede usar fuera de un `ritual` (`PGS-E3103`). En una función
asociada, `Self` es el tipo; para construir se usa el nombre del tipo o
`Self(...)`.

### 31.4 Genéricos y `where`

```pengu
rune Holder[T]
    value: T

ritual Holder[T]
    get = (@) -> &T
        &@.value

    replace = (@mut, value: T) -> T
        std.mem.replace(&mut @.value, value)
```

Rust generado:

```rust
struct Holder<T> {
    value: T,
}

impl<T> Holder<T> {
    fn get(&self) -> &T {
        &self.value
    }

    fn replace(&mut self, value: T) -> T {
        std::mem::replace(&mut self.value, value)
    }
}
```

Con `where`:

```pengu
rune Wrapper[T]
    value: T

ritual Wrapper[T] where T: Clone
    duplicate = (@) -> T
        @.value.clone()

bind w = Wrapper(value: 7)
print(w.duplicate())
```

Rust generado:

```rust
struct Wrapper<T> {
    value: T,
}

impl<T: Clone> Wrapper<T> {
    fn duplicate(&self) -> T {
        self.value.clone()
    }
}

fn main() {
    let w = Wrapper { value: 7 };
    println!("{}", w.duplicate());
}
```

El `where` del `ritual` debe ser compatible con el del tipo; se permiten bounds
adicionales solo para los métodos que los necesitan.

### 31.5 Implementaciones de trait

Un `pact` declara el contrato; `ritual Tipo for Pact` lo implementa:

```pengu
pact Show
    show = (@) -> String

rune Point
    x: Float
    y: Float

ritual Point
    length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

ritual Point for Show
    show = (@) -> String
        format!("Point(#{@.x}, #{@.y})")

bind p = Point(x: 3.0, y: 4.0)
print(p.show())
```

Rust generado:

```rust
trait Show {
    fn show(&self) -> String;
}

struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }
}

impl Show for Point {
    fn show(&self) -> String {
        format!("Point({}, {})", self.x, self.y)
    }
}

fn main() {
    let p = Point { x: 3.0, y: 4.0 };
    println!("{}", p.show());
}
```

Reglas de coherencia:

1. Una implementación inherente solo vale para un tipo local.
2. `ritual Tipo for Pact` exige que el tipo o el trait sea local (regla huérfana
   de Rust, `PGS-E3106`).
3. No hay implementaciones blanket en PenguScript; se reservan para §36.
4. Un trait no puede implementarse dos veces para el mismo tipo (`PGS-E3107`).
5. Todos los métodos requeridos por el `pact` deben existir; los métodos con
   default son opcionales.
6. El orden de resolución es inherente antes que trait; si ambos tienen el mismo
   nombre, se usa el inherente y se avisa (`PGS-W3101`).

### 31.6 Visibilidad de métodos

Por defecto, un método es tan visible como su tipo. `unveil` lo hace público y
`unveil(tome)`/`unveil(scroll)` limitan la visibilidad:

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    unveil length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

    unveil(tome) reset = (@mut) -> Unit
        @.x = 0.0
        @.y = 0.0
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    pub fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }

    pub(crate) fn reset(&mut self) {
        self.x = 0.0;
        self.y = 0.0;
    }
}
```

### 31.7 Constantes asociadas

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    sigil ORIGIN: Point = Point(x: 0.0, y: 0.0)

print(Point.ORIGIN.x)
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    const ORIGIN: Point = Point { x: 0.0, y: 0.0 };
}

fn main() {
    println!("{}", Point::ORIGIN.x);
}
```

Una constante asociada debe ser evaluable en `const`; no puede llamar a métodos
no `const` (§19).

### 31.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3101` | `@` en función asociada | añadir receptor o quitar `@` |
| `PGS-E3102` | método duplicado | renombrar |
| `PGS-E3103` | `Self` fuera de `ritual` | mover dentro |
| `PGS-E3104` | receptor incompatible con el uso | usar `morph`/`@mut` |
| `PGS-E3105` | `ritual` inherente sobre tipo externo | mover a un newtype |
| `PGS-E3106` | violación de coherencia/huérfano | implementar trait local o tipo local |
| `PGS-E3107` | trait implementado dos veces | eliminar duplicado |
| `PGS-E3108` | falta un método del `pact` | implementarlo |
| `PGS-W3101` | método inherente y de trait con el mismo nombre | renombrar |
| `PGS-W3102` | `@own` en un método que no consume | usar `@` |

### 31.9 Criterios de aceptación

- [x] `ritual` inherente y sus métodos están definidos.
- [x] `@`, `@mut`, `@own` mapean a `&self`, `&mut self`, `self`.
- [x] Funciones asociadas y `Self` tienen ejemplo.
- [x] Genéricos, `where` y métodos con bounds están cubiertos.
- [x] `ritual Tipo for Pact` y coherencia están definidos.
- [x] Visibilidad y constantes asociadas tienen ejemplo.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-32-aliases-casts"></a>
## 32. Type aliases, newtypes y casts (`essence`)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 4B |
| Rust | `type`, `struct`, `as`, `From`/`Into`, `TryFrom`/`TryInto` |
| Palabras mágicas | `essence`, `rune`, `as`, `curse` |
| Depende de | §4, §19, §28, §31 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec32_casts.pengu` |

PenguScript separa tres ideas que suelen confundirse:

- **Alias** (`essence`): otro nombre para un tipo existente. No crea un tipo
  nuevo ni cambia la coerción.
- **Newtype** (`rune` de un campo): un tipo nominal nuevo con el mismo layout,
  pero sin conversiones implícitas.
- **Cast** (`as`): una conversión explícita, posiblemente lossy, que el
  programador escribe a propósito.

### 32.1 Alias de tipo

```pengu
essence Meters = Float
essence Pair[T] = (T, T)
essence Callback = (Int, Int) -> Int

bind distance: Meters = 3.5
bind point: Pair[Int] = (1, 2)
bind add: Callback = (a: Int, b: Int) => a + b

print(distance)
print(point.0)
print(add(2, 3))
```

Rust generado:

```rust
type Meters = f64;
type Pair<T> = (T, T);
type Callback = fn(i32, i32) -> i32;

fn main() {
    let distance: Meters = 3.5;
    let point: Pair<i32> = (1, 2);
    let add: Callback = |a: i32, b: i32| a + b;

    println!("{}", distance);
    println!("{}", point.0);
    println!("{}", add(2, 3));
}
```

Reglas:

1. `essence Nombre = Tipo` declara un alias.
2. `essence Nombre[T] = Tipo` declara un alias genérico.
3. Un alias no crea un tipo nominal: `Meters` y `Float` son el mismo tipo para
   el compilador.
4. Los alias no pueden ser recursivos (`PGS-E3201`).
5. Un alias puede tener visibilidad: `unveil essence Meters = Float`.
6. Los alias no se pueden usar para implementar traits sobre tipos externos;
   la regla huérfana mira el tipo subyacente (`PGS-E3202`).
7. El alias no cambia el layout ni la representación.

### 32.2 Newtypes

```pengu
rune UserId(UInt)
rune Email(String)

ritual UserId
    value = (@) -> UInt
        @.0

bind id = UserId(7)
print(id.value())
```

Rust generado:

```rust
struct UserId(u32);
struct Email(String);

impl UserId {
    fn value(&self) -> u32 {
        self.0
    }
}

fn main() {
    let id = UserId(7);
    println!("{}", id.value());
}
```

Reglas:

1. Un newtype es un `rune` de tupla con un solo campo.
2. Es un tipo distinto: `UserId` no es `UInt` ni se convierte solo.
3. El campo `.0` existe, pero su visibilidad sigue las reglas de §28 (privado
   fuera del módulo).
4. Para exponer el valor se usa un método (`value`) o `unveil` en el campo
   cuando §28 lo permita.
5. Un newtype puede implementar métodos y traits como cualquier `rune`.
6. Los newtypes son la forma recomendada de dar semántica a un primitivo
   (`UserId`, `Meters`, `Email`) sin costo en runtime.

### 32.3 Casts con `as`

```pengu
bind a: Int = 300
bind b = a as U8
bind f = 3.9
bind i = f as Int
bind c = 'P' as U32

print(b)
print(i)
print(c)
```

Rust generado:

```rust
fn main() {
    let a: i32 = 300;
    let b = a as u8;
    let f = 3.9;
    let i = f as i32;
    let c = 'P' as u32;

    println!("{}", b);
    println!("{}", i);
    println!("{}", c);
}
```

Salida: `44`, `3`, `80`.

Reglas:

1. `as` es explícito y tiene alta precedencia (§11).
2. Los casts numéricos pueden ser lossy: `300 as U8` = `44`; `3.9 as Int` = `3`.
   El compilador avisa cuando el valor es constante y se pierde información
   (`PGS-W3201`).
3. No hay casts implícitos entre tipos numéricos; una suma `Int + Float` es
   error (`PGS-E3203`).
4. Se permite `Bool as Int`, `Char as U32`, `U8 as Char` (solo `U8`), enums
   fieldless a su entero, y punteros a enteros con `curse`.
5. No se permite `as` entre referencias de distinto tipo ni entre structs; para
   eso se usan `From`/`Into` o `transmute` en `curse`.
6. `as` sobre un enum con datos es error (`PGS-E3204`); se usa `match`.
7. Un cast de puntero conserva la dirección, no la validez; es `curse` (§19).

### 32.4 `From`/`Into`

```pengu
bind s = String.from("pengu")
bind t: String = "script".into()

print(s)
print(t)
```

Rust generado:

```rust
fn main() {
    let s = String::from("pengu");
    let t: String = "script".into();

    println!("{}", s);
    println!("{}", t);
}
```

Reglas:

1. `T.from(x)` llama a `From::from`; el tipo destino es `T`.
2. `x.into()` llama a `Into::into`; el tipo destino se infiere del contexto.
3. `From`/`Into` son conversiones **infalibles** y deben conservar la
   información; si puede fallar, se usa `TryFrom`/`TryInto`.
4. Una conversión `From` es la forma preferida para newtypes y tipos propios.
5. No se implementa `From` para conversiones lossy (`PGS-E3205`).

### 32.5 `TryFrom`/`TryInto`

```pengu
bind small: !U8 = U8.try_from(300)

match small
    when ok(value) then print(value)
    when err(_) then print("no cabe")
```

Rust generado:

```rust
fn main() {
    let small: Result<u8, Box<dyn std::error::Error + Send + Sync>> = u8::try_from(300).map_err(|e| Box::new(e) as Box<dyn std::error::Error + Send + Sync>);

    match small {
        Ok(value) => println!("{}", value),
        Err(_) => println!("no cabe"),
    }
}
```

`TryFrom` devuelve `!T` (`Result<T, Error>`). El error se puede propagar con `?`
(§48). `TryInto` es la forma método: `x.try_into()`.

### 32.6 Coerciones permitidas

PenguScript solo aplica las coerciones que Rust considera seguras y automáticas:

| Desde | Hacia | Condición |
|---|---|---|
| `&[T; N]` | `&[T]` | unsizing de array a slice |
| `&mut [T; N]` | `&mut [T]` | unsizing |
| `&T` | `&dyn Pact` | `T: Pact` |
| `Box[T]` | `Box[dyn Pact]` | `T: Pact` |
| `fn` item | `fn` pointer | función sin captura |
| `!` | cualquier tipo | divergencia |

No se permite coerción implícita entre:

- `Int` y `Float`;
- `String` y `Str` (se usa `.as_str()` o `&s`);
- `T` y `?T` (se usa `some(x)`);
- `T` y `!T` (se usa `ok(x)`);
- dos newtypes distintos;
- `&T` y `&mut T`.

### 32.7 Tipos asociados (avance)

Dentro de un `pact`, `essence Nombre` sin `=` declara un tipo asociado:

```pengu
pact Container
    essence Item

    first = (@) -> ?&Item

rune Numbers
    values: Vec[Int]

ritual Container for Numbers
    essence Item = Int

    first = (@) -> ?&Int
        @.values.first()

bind n = Numbers(values: Vec[1, 2, 3])
print(n.first())
```

Rust generado:

```rust
trait Container {
    type Item;

    fn first(&self) -> Option<&Self::Item>;
}

struct Numbers {
    values: Vec<i32>,
}

impl Container for Numbers {
    type Item = i32;

    fn first(&self) -> Option<&i32> {
        self.values.first()
    }
}

fn main() {
    let n = Numbers { values: vec![1, 2, 3] };
    println!("{:?}", n.first());
}
```

El tipo asociado se proyecta como `Self::Item` en el trait y se fija en cada
implementación. §35 profundiza en asociados y bounds.

### 32.8 `transmute`

`transmute` solo existe dentro de `curse` y exige que origen y destino tengan el
mismo tamaño:

```pengu
curse
    bind bits: U32 = transmute(1.0_f32)
    print(bits)
```

Rust generado:

```rust
fn main() {
    unsafe {
        let bits: u32 = std::mem::transmute(1.0_f32);
        println!("{}", bits);
    }
}
```

Reglas:

1. `transmute` es la última opción; prefiere `as`, `From` o `to_bits`.
2. Origen y destino deben tener el mismo tamaño (`PGS-E3207`).
3. No se permite `transmute` fuera de `curse` (`PGS-E3206`).
4. El resultado puede ser un valor inválido (por ejemplo, un `bool` con bits
   distintos de 0/1); la responsabilidad es del programador.
5. Para punteros se prefiere `cast`/`as` antes que `transmute`.

### 32.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3201` | alias recursivo | romper el ciclo |
| `PGS-E3202` | alias usado para violar coherencia | usar un newtype local |
| `PGS-E3203` | operación entre numéricos distintos | convertir con `as` |
| `PGS-E3204` | `as` sobre enum con datos | usar `match` |
| `PGS-E3205` | `From` lossy | usar `TryFrom` |
| `PGS-E3206` | `transmute` fuera de `curse` | envolver en `curse` |
| `PGS-E3207` | `transmute` con tamaños distintos | usar otra conversión |
| `PGS-E3208` | cast de referencia inválido | usar `From`/`Into` |
| `PGS-W3201` | cast constante con pérdida | revisar el valor |
| `PGS-W3202` | newtype sin constructor validado | añadir `new` con validación |

### 32.10 Criterios de aceptación

- [x] Alias simple y genérico están definidos.
- [x] Newtype y su relación con el tipo subyacente están claros.
- [x] `as` numérico, de puntero y de enum está cubierto.
- [x] `From`/`Into` y `TryFrom`/`TryInto` tienen ejemplo.
- [x] Las coerciones permitidas y prohibidas están tabuladas.
- [x] El avance de tipos asociados es consistente con §35.
- [x] `transmute` solo se permite en `curse`.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="part-5"></a>
## Parte V — Abstracción

<a id="sec-33-genericos"></a>
## 33. Genéricos

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 5 |
| Rust | Genéricos `<T>`, `PhantomData<T>`, const generics |
| Palabras mágicas | `[T]`, `[const N: Usize]`, `PhantomData` |
| Depende de | §4, §18, §28, §31 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec33_generics.pengu` |

Un **genérico** es un item que se escribe una vez y se especializa para varios
tipos. PenguScript usa `[T]` para declarar parámetros y `Tipo[Arg]` para
aplicarlos. El compilador genera una instancia por combinación de argumentos
(monomorphization), igual que Rust: no hay despacho dinámico implícito ni
boxeo oculto.

### 33.1 Parámetros de tipo

```pengu
rune Pair[A, B]
    first: A
    second: B

bind p = Pair(first: 1, second: "one")
print(p.first)
print(p.second)
```

Rust generado:

```rust
struct Pair<A, B> {
    first: A,
    second: B,
}

fn main() {
    let p = Pair { first: 1, second: "one" };
    println!("{}", p.first);
    println!("{}", p.second);
}
```

Reglas:

1. Los parámetros van entre `[` y `]` inmediatamente después del nombre del
   item: `Pair[A, B]`, `identity[T]`, `pact Convert[T]`.
2. Se permiten en `rune`, `enchanting`, `pact`, funciones nombradas, `ritual` y
   `essence` genérica.
3. En posición de tipo se aplican con `Pair[Int, Str]`; no se usa `::<>`.
4. En expresión, una llamada genérica usa turbofish: `identity[Int](42)`.
   `identity[Int]` sin llamada solo es válido como valor de función ya
   instanciado y debe poder inferirse o anotarse.
5. La inferencia toma los argumentos de los valores y del contexto. Si un
   parámetro no aparece en parámetros ni en el retorno, es error
   (`PGS-E3304`): no hay parámetros “fantasma” sin `PhantomData`.
6. No hay valores por defecto para parámetros de tipo. `rune Box[T = Int]` es
   error (`PGS-E3305`).
7. Los nombres son convencionales: `T`, `U`, `K`, `V`, `A`, `B`. No son
   palabras clave.
8. Un parámetro de tipo no es un valor: no se puede usar en una expresión, solo
   en tipos y en `PhantomData`.

### 33.2 Funciones genéricas

```pengu
identity = [T](value: T) -> T
    value

bind n = identity[Int](42)
bind s = identity[String](String.from("pengu"))
print(n)
print(s)
```

Rust generado:

```rust
fn identity<T>(value: T) -> T {
    value
}

fn main() {
    let n = identity::<i32>(42);
    let s = identity::<&str>("pengu");
    println!("{}", n);
    println!("{}", s);
}
```

Reglas:

1. El turbofish es obligatorio cuando el tipo no se puede inferir; por ejemplo,
   `identity[Int](42)` o `Vec[Int].new()`.
2. Si se infiere, se puede omitir: `identity(42)`.
3. Una función genérica sin argumentos que no permitan inferencia es error
   (`PGS-E3306`).
4. La función es un **item**, no una variable: se puede declarar en el módulo y
   no captura el entorno. Las lambdas genéricas no existen; una lambda puede
   recibir valores de cualquier tipo solo si su tipo se infiere por el contexto.

### 33.3 Structs y enums genéricos

```pengu
enchanting Maybe[T]
    Nothing
    Just(T)

unwrap_or = [T](value: Maybe[T], fallback: T) -> T
    match value
        when Just(x) then x
        when Nothing then fallback

bind value = Just(7)
bind result = unwrap_or[Int](value, 0)
print(result)
```

Rust generado:

```rust
enum Maybe<T> {
    Nothing,
    Just(T),
}

fn unwrap_or<T>(value: Maybe<T>, fallback: T) -> T {
    match value {
        Maybe::Just(x) => x,
        Maybe::Nothing => fallback,
    }
}

fn main() {
    let value = Maybe::Just(7);
    let result = unwrap_or::<i32>(value, 0);
    println!("{}", result);
}
```

Un `rune` genérico sigue las mismas reglas; sus campos pueden usar `T`,
`[T; N]`, `?T`, `&'a T` o cualquier tipo que dependa de los parámetros.

### 33.4 Parámetros de lifetime

```pengu
rune Excerpt['a]
    text: &'a Str

bind s = "pengu"
bind e = Excerpt(text: s)
print(e.text)
```

Rust generado:

```rust
struct Excerpt<'a> {
    text: &'a str,
}

fn main() {
    let s = "pengu";
    let e = Excerpt { text: s };
    println!("{}", e.text);
}
```

Los parámetros de lifetime se mezclan con los de tipo en el mismo corchete:

```pengu
rune Holder['a, T]
    value: &'a T
```

1. `'a` declara un lifetime; no es un tipo y no se puede usar como valor.
2. Los lifetimes se eliden cuando Rust puede inferirlos (§18); si no, se
   escriben.
3. Un lifetime de un `rune` debe usarse en un campo o en `PhantomData`.

### 33.5 Const generics

```pengu
rune Buffer[const N: Usize]
    data: [U8; N]

new = [const N: Usize]() -> Buffer[N]
    Buffer(data: [0; N])

bind b = new[4]()
print(b.data.len())
```

Rust generado:

```rust
struct Buffer<const N: usize> {
    data: [u8; N],
}

fn new<const N: usize>() -> Buffer<N> {
    Buffer { data: [0; N] }
}

fn main() {
    let b = new::<4>();
    println!("{}", b.data.len());
}
```

Reglas:

1. La sintaxis es `[const N: Usize]`. `Usize` es el único tipo permitido; no hay
   const generics de `Bool`, `Char` ni `Str`.
2. `N` es una constante de compile-time; se usa en tipos como `[T; N]`, no en
   expresiones de runtime.
3. La instanciación usa un literal o una constante: `Buffer[16]`, `Buffer[SIZE]`.
4. No se permiten expresiones aritméticas arbitrarias en el argumento
   (`Buffer[N + 1]`) en el subconjunto estable; se calcula una constante auxiliar
   fuera.
5. Un const generic no puede tener bounds de trait; su tipo ya es `Usize`.
6. El compilador genera una instancia por valor de `N` usado.

### 33.6 Genéricos en `ritual`

```pengu
rune Box[T]
    value: T

ritual Box[T]
    get = (@) -> &T
        &@.value

    replace = (@mut, value: T) -> T
        std.mem.replace(&mut @.value, value)

bind b = Box(value: 9)
print(b.get())
print(b.replace(10))
```

Rust generado:

```rust
struct Box<T> {
    value: T,
}

impl<T> Box<T> {
    fn get(&self) -> &T {
        &self.value
    }

    fn replace(&mut self, value: T) -> T {
        std::mem::replace(&mut self.value, value)
    }
}

fn main() {
    let mut b = Box { value: 9 };
    println!("{}", b.get());
    println!("{}", b.replace(10));
}
```

El `ritual` puede añadir bounds que el tipo no tiene, pero no puede quitar los
que el tipo exige. Un `ritual` genérico sin parámetros propios usa los del tipo:
`ritual Box[T]`; un `ritual` de trait usa `ritual Box[T] for Show`.

### 33.7 Monomorphization y costo

PenguScript no tiene genéricos en runtime. Cada uso concreto produce una
especialización:

- `identity[Int]` y `identity[String]` generan dos funciones.
- El código especializado es zero-cost: no hay tabla de métodos ni boxing.
- El costo es tamaño de binario y tiempo de compilación.
- Para despacho dinámico se usa `dyn Pact` (§35); para evitar el costo de
  monomorphization se puede aceptar `&dyn Pact`.

No hay “generic constants” de runtime ni reflexión de tipos.

### 33.8 `PhantomData`

Un parámetro que no aparece en ningún campo cambia la varianza y la propiedad
del tipo. Para declararlo explícitamente se usa `PhantomData[T]`:

```pengu
rune Tagged[T]
    value: Int
    marker: PhantomData[T]

bind t: Tagged[String] = Tagged(value: 1, marker: PhantomData)
print(t.value)
```

Rust generado:

```rust
use std::marker::PhantomData;

struct Tagged<T> {
    value: i32,
    marker: PhantomData<T>,
}

fn main() {
    let t: Tagged<&str> = Tagged { value: 1, marker: PhantomData };
    println!("{}", t.value);
}
```

1. `PhantomData[T]` ocupa cero bytes.
2. Sin `PhantomData`, un parámetro no usado es error (`PGS-E3304`).
3. `PhantomData` no se construye con `new`; el valor es el path `PhantomData`.
4. No se permite `PhantomData` para “inventar” un tipo que no participa en la
   API; documenta por qué está.

### 33.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3301` | parámetro de tipo no declarado | añadirlo a `[T]` |
| `PGS-E3302` | aridad de argumentos incorrecta | ajustar `Tipo[A, B]` |
| `PGS-E3303` | argumento de tipo en posición de valor | usar turbofish o un valor |
| `PGS-E3304` | parámetro no usado ni en campos ni en retorno | usar `PhantomData[T]` o eliminarlo |
| `PGS-E3305` | default de parámetro de tipo | eliminar el default |
| `PGS-E3306` | no se puede inferir el parámetro | escribir `foo[Tipo](...)` |
| `PGS-E3307` | const generic con tipo distinto de `Usize` | usar `Usize` |
| `PGS-E3308` | expresión no constante como argumento const | usar un literal o `sigil` |
| `PGS-W3301` | nombre de parámetro de una sola letra no convencional | usar `T`/`K`/`V` o un nombre claro |

### 33.10 Criterios de aceptación

- [x] La sintaxis `[T]` no colisiona con indexación ni slices.
- [x] Funciones, structs, enums y `ritual` genéricos tienen ejemplo.
- [x] Lifetimes y const generics están definidos.
- [x] `PhantomData` y el parámetro no usado están cubiertos.
- [x] Monomorphization y el costo están explicados.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-34-constraints"></a>
## 34. Constraints y where

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 5 |
| Rust | Bounds `T: Trait`, `where`, `?Sized` |
| Palabras mágicas | `where`, `:`, `+`, `?Sized` |
| Depende de | §33, §18, §35 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec34_constraints.pengu` |

Un **constraint** (bound) declara qué debe cumplir un parámetro de tipo o un
lifetime para que el item sea válido. PenguScript usa la misma relación que
Rust: el bound se comprueba en la definición y en cada uso; no hay duck typing
ni comprobaciones en runtime.

### 34.1 Bounds en la cabecera

```pengu
largest = [T: PartialOrd + Copy](items: &[T]) -> T
    morph best = items[0]
    for item in &items[1..]
        if *item > best
            best = *item
    best

bind nums = [3, 1, 4, 1]
print(largest(&nums))
```

Rust generado:

```rust
fn largest<T: PartialOrd + Copy>(items: &[T]) -> T {
    let mut best = items[0];
    for item in &items[1..] {
        if *item > best {
            best = *item;
        }
    }
    best
}

fn main() {
    let nums = [3, 1, 4, 1];
    println!("{}", largest(&nums));
}
```

Reglas:

1. Los bounds van después de `:` dentro del corchete: `[T: Pact + Clone]`.
2. `+` combina bounds; todos deben cumplirse.
3. Un bound puede ser un `pact`, un lifetime (`T: 'a`) o `?Sized`.
4. Los bounds se aplican a funciones, `rune`, `enchanting`, `pact`, `ritual` y
   `essence` genérica.
5. Un bound no puede ser una expresión ni un valor; solo un `pact` o lifetime.
6. No hay bounds negativos (`T: !Copy`) ni especialización.

### 34.2 `where`

Para listas largas o bounds que dependen de varios parámetros se usa `where`:

```pengu
describe = [T](value: T) -> String where T: Display + Clone
    format!("#{value}")

print(describe(42))
print(describe("pengu"))
```

Rust generado:

```rust
fn describe<T>(value: T) -> String
where
    T: std::fmt::Display + Clone,
{
    format!("{}", value)
}

fn main() {
    println!("{}", describe(42));
    println!("{}", describe("pengu"));
}
```

Reglas:

1. `where` va al final de la firma, antes del cuerpo.
2. Cada bound se separa con coma: `where T: A + B, U: C`.
3. No se puede repetir un bound idéntico (`PGS-W3401`); sí se pueden repartir
   bounds entre cabecera y `where`.
4. El `where` de un `ritual` debe ser compatible con el del tipo; no puede
   relajar los bounds del tipo (§31).
5. El `where` de un `pact` puede declarar bounds sobre tipos asociados
   (`I: Iterator[Item = Int]`).
6. Un `where` vacío es error (`PGS-E3401`).

### 34.3 Bounds de lifetime

```pengu
pick = ['a, T: 'a](a: &'a T, _b: &'a T) -> &'a T
    a

bind x = 1
bind y = 2
print(pick(&x, &y))
```

Rust generado:

```rust
fn pick<'a, T: 'a>(a: &'a T, _b: &'a T) -> &'a T {
    a
}

fn main() {
    let x = 1;
    let y = 2;
    println!("{}", pick(&x, &y));
}
```

1. `T: 'a` significa que `T` vive al menos tanto como `'a`.
2. `'a: 'b` significa que `'a` vive al menos tanto como `'b`.
3. Los bounds de lifetime no crean valores; solo restringen préstamos.
4. Un lifetime `'static` cumple cualquier bound de lifetime.

### 34.4 `?Sized`

Por defecto todo parámetro de tipo es `Sized`. `?Sized` lo relaja para aceptar
tipos Dynamically Sized (`Str`, `[T]`, `dyn Pact`):

```pengu
debug = [T: ?Sized + Debug](value: &T) -> String
    format!("{:?}", value)

bind text = "pengu"
print(debug(text))
```

Rust generado:

```rust
fn debug<T: ?Sized + std::fmt::Debug>(value: &T) -> String {
    format!("{:?}", value)
}

fn main() {
    let text = "pengu";
    println!("{}", debug(text));
}
```

1. `?Sized` solo tiene sentido detrás de una referencia, `Box[T]` o un puntero.
2. No se puede pasar un `T: ?Sized` por valor; el compilador no conoce su tamaño
   (`PGS-E3404`).
3. `?Sized` no implica `Copy` ni `Clone`.

### 34.5 Bounds sobre tipos asociados

```pengu
total = [I](iter: I) -> Int where I: Iterator[Item = Int]
    iter.sum()

bind values = [1, 2, 3]
print(total(values.iter().copied()))
```

Rust generado:

```rust
fn total<I>(iter: I) -> i32
where
    I: Iterator<Item = i32>,
{
    iter.sum()
}

fn main() {
    let values = [1, 2, 3];
    println!("{}", total(values.iter().copied()));
}
```

Reglas:

1. La forma `Pact[Item = Tipo]` fija un tipo asociado en el bound.
2. Se pueden fijar varios: `Pact[A = Int, B = Str]`.
3. Un tipo asociado no fijado sigue siendo opaco; el compilador no lo infiere
   por el uso.
4. Los bounds de tipo asociado se comprueban en la implementación (§36).

### 34.6 Supertraits y bounds de `pact`

```pengu
pact Show
    show = (@) -> String

pact Pretty: Show
    pretty = (@) -> String
        "**#{@.show()}**"

rune Point
    x: Int
    y: Int

ritual Show for Point
    show = (@) -> String
        format!("(#{@.x}, #{@.y})")

ritual Pretty for Point

bind p = Point(x: 1, y: 2)
print(p.pretty())
```

Rust generado:

```rust
trait Show {
    fn show(&self) -> String;
}

trait Pretty: Show {
    fn pretty(&self) -> String {
        format!("**{}**", self.show())
    }
}

struct Point {
    x: i32,
    y: i32,
}

impl Show for Point {
    fn show(&self) -> String {
        format!("({}, {})", self.x, self.y)
    }
}

impl Pretty for Point {}

fn main() {
    let p = Point { x: 1, y: 2 };
    println!("{}", p.pretty());
}
```

1. `pact Pretty: Show` declara que implementar `Pretty` exige `Show`.
2. El supertrait no se implementa automáticamente; `ritual Pretty for Point`
   debe ir acompañado de `ritual Show for Point`.
3. Un bound `T: Pretty` implica `T: Show`.
4. Los supertraits múltiples se separan con `+`: `pact Pretty: Show + Clone`.

### 34.7 Resolución de bounds

1. El compilador resuelve los bounds en el punto de uso, no en runtime.
2. Un bound no satisfecho es `PGS-E3402`; el mensaje debe indicar qué
   implementación falta.
3. Los bounds se pueden inferir por el contexto de retorno; si no, se escriben.
4. El orden de los bounds no importa.
5. Un bound redundante se acepta con warning (`PGS-W3401`), salvo que sea
   necesario para legibilidad.
6. No hay `where` clauses en lambdas; sus tipos se infieren o se anotan en el
   binding.

### 34.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3401` | `where` vacío | eliminarlo |
| `PGS-E3402` | bound no satisfecho | implementar el `pact` o cambiar el tipo |
| `PGS-E3403` | bound sobre un parámetro no declarado | añadirlo a `[T]` |
| `PGS-E3404` | `T: ?Sized` usado por valor | pasar `&T`, `Box[T]` o un puntero |
| `PGS-E3405` | lifetime bound imposible | acortar el préstamo o usar `'static` |
| `PGS-E3406` | bound de tipo asociado mal formado | usar `Pact[Item = Tipo]` |
| `PGS-E3407` | `where` en un `ritual` incompatible con el tipo | alinear los bounds |
| `PGS-W3401` | bound redundante | eliminar o justificar |

### 34.9 Criterios de aceptación

- [x] Bounds en cabecera y `where` son equivalentes.
- [x] Bounds de lifetime y `?Sized` tienen ejemplo.
- [x] Bounds sobre tipos asociados están definidos.
- [x] Supertraits y su implementación están explicados.
- [x] La resolución y los diagnósticos están cubiertos.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-35-traits"></a>
## 35. Traits (`pact`)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 5 |
| Rust | `trait`, `dyn Trait`, `impl Trait` |
| Palabras mágicas | `pact`, `ritual`, `dyn`, `impl` |
| Depende de | §31, §33, §34 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec35_traits.pengu` |

Un **`pact`** es un contrato nominal: declara métodos y tipos asociados que un
tipo puede implementar con `ritual`. No hay herencia de clases; la reutilización
se hace con `pact`, composición y `ritual`. Un `pact` no contiene estado.

### 35.1 Declaración

```pengu
pact Shape
    area = (@) -> Float
    name = (@) -> String
        "shape"

rune Circle
    radius: Float

ritual Circle for Shape
    area = (@) -> Float
        3.141592653589793 * @.radius * @.radius

bind c = Circle(radius: 2.0)
print(c.name())
print(c.area())
```

Rust generado:

```rust
trait Shape {
    fn area(&self) -> f64;

    fn name(&self) -> String {
        "shape".to_string()
    }
}

struct Circle {
    radius: f64,
}

impl Shape for Circle {
    fn area(&self) -> f64 {
        3.141592653589793 * self.radius * self.radius
    }
}

fn main() {
    let c = Circle { radius: 2.0 };
    println!("{}", c.name());
    println!("{}", c.area());
}
```

Reglas:

1. Un `pact` declara firmas con `name = (params) -> Tipo`; el cuerpo es opcional
   (método default).
2. Los métodos con receptor usan `@`, `@mut` o `@own`. Los métodos sin receptor
   son funciones asociadas y se llaman `Tipo.metodo(...)`.
3. Los métodos de un `pact` son públicos; la visibilidad se controla en el
   `pact`, no método a método.
4. Un `pact` no puede declarar campos ni estado.
5. Un `pact` puede ser genérico (`pact Convert[T]`) y tener supertraits
   (§34.6).
6. Un método default puede llamar a otros métodos del mismo `pact`, incluidos
   los requeridos.
7. No hay `pact` con implementación automática salvo los derives y los auto
   traits de Rust (§46).

### 35.2 Implementación

```pengu
pact Show
    show = (@) -> String

rune Point
    x: Int
    y: Int

ritual Show for Point
    show = (@) -> String
        format!("(#{@.x}, #{@.y})")

bind p = Point(x: 1, y: 2)
print(p.show())
```

Rust generado:

```rust
trait Show {
    fn show(&self) -> String;
}

struct Point {
    x: i32,
    y: i32,
}

impl Show for Point {
    fn show(&self) -> String {
        format!("({}, {})", self.x, self.y)
    }
}

fn main() {
    let p = Point { x: 1, y: 2 };
    println!("{}", p.show());
}
```

1. `ritual Tipo for Pact` implementa el contrato completo.
2. Todos los métodos requeridos deben existir; si falta uno, `PGS-E3501`.
3. Un método default se puede sobrescribir; si no, se hereda.
4. El tipo y el `pact` deben cumplir la regla huérfana (§35.9).
5. Un tipo puede implementar varios `pact`; los nombres de métodos pueden
   colisionar y se resuelven con `Pact.metodo(valor)` o `Tipo.metodo`.
6. No se puede implementar un `pact` dos veces para el mismo tipo
   (`PGS-E3502`).

### 35.3 Métodos default y `Self`

```pengu
pact Greet
    hello = (@) -> String
        "hello, #{@.name()}"

    name = (@) -> String

rune User
    name: String

ritual User for Greet
    name = (@) -> String
        @.name.clone()

bind u = User(name: "pengu")
print(u.hello())
```

Rust generado:

```rust
trait Greet {
    fn hello(&self) -> String {
        format!("hello, {}", self.name())
    }

    fn name(&self) -> String;
}

struct User {
    name: String,
}

impl Greet for User {
    fn name(&self) -> String {
        self.name.clone()
    }
}

fn main() {
    let u = User { name: "pengu".to_string() };
    println!("{}", u.hello());
}
```

`Self` dentro de un `pact` es el tipo que implementa el contrato; se usa en
tipos de retorno y parámetros. `Self` fuera de un `pact`/`ritual` es error
(`PGS-E3503`).

### 35.4 `pact` genérico

```pengu
pact Convert[T]
    convert = (@) -> T

rune Celsius
    degrees: Float

rune Fahrenheit
    degrees: Float

ritual Convert[Fahrenheit] for Celsius
    convert = (@) -> Fahrenheit
        Fahrenheit(degrees: @.degrees * 9.0 / 5.0 + 32.0)

bind c = Celsius(degrees: 100.0)
print(c.convert().degrees)
```

Rust generado:

```rust
trait Convert<T> {
    fn convert(&self) -> T;
}

struct Celsius {
    degrees: f64,
}

struct Fahrenheit {
    degrees: f64,
}

impl Convert<Fahrenheit> for Celsius {
    fn convert(&self) -> Fahrenheit {
        Fahrenheit { degrees: self.degrees * 9.0 / 5.0 + 32.0 }
    }
}

fn main() {
    let c = Celsius { degrees: 100.0 };
    println!("{}", c.convert().degrees);
}
```

Un `pact` genérico puede fijar el parámetro en el `ritual`
(`Convert[Fahrenheit]`) o dejarlo genérico (`ritual[T] Convert[T] for ...`).
La implementación debe ser coherente con los bounds del `pact`.

### 35.5 `dyn` y object safety

Un `dyn Pact` es un trait object: despacho dinámico a través de una tabla de
métodos. Solo es válido si el `pact` es **object safe**:

```pengu
pact Shape
    area = (@) -> Float

rune Circle
    radius: Float

ritual Shape for Circle
    area = (@) -> Float
        3.141592653589793 * @.radius * @.radius

bind shapes: Vec[Box[dyn Shape]] = Vec[Box.new(Circle(radius: 1.0))]
for shape in &shapes
    print(shape.area())
```

Rust generado:

```rust
trait Shape {
    fn area(&self) -> f64;
}

struct Circle {
    radius: f64,
}

impl Shape for Circle {
    fn area(&self) -> f64 {
        3.141592653589793 * self.radius * self.radius
    }
}

fn main() {
    let shapes: Vec<Box<dyn Shape>> = vec![Box::new(Circle { radius: 1.0 })];
    for shape in &shapes {
        println!("{}", shape.area());
    }
}
```

Reglas de object safety:

1. No puede tener métodos genéricos (`[T]`).
2. No puede devolver `Self` por valor; `&Self` sí.
3. No puede tener funciones asociadas sin receptor que usen `Self`.
4. No puede tener constantes asociadas (Rust las prohíbe en trait objects).
5. Los métodos con `@`, `@mut` y `@own` son aceptables si no violan lo anterior.
6. Un `pact` con métodos default que usen `Self` por valor no es object safe.
7. `dyn Pact` necesita un puntero: `&dyn Pact`, `Box[dyn Pact]`, `Rc[dyn Pact]`.
8. `dyn Pact + Send + Sync` se escribe con `+`; el trait object debe cumplir los
   auto traits.

### 35.6 `impl Trait`

`impl Pact` en posición de parámetro acepta cualquier tipo que implemente el
contrato; en retorno devuelve un tipo opaco:

```pengu
pact Shape
    area = (@) -> Float

rune Circle
    radius: Float

ritual Shape for Circle
    area = (@) -> Float
        3.141592653589793 * @.radius * @.radius

print_shape = (shape: impl Shape) -> Unit
    print(shape.area())

make = () -> impl Shape
    Circle(radius: 1.0)

print_shape(make())
```

Rust generado:

```rust
trait Shape {
    fn area(&self) -> f64;
}

struct Circle {
    radius: f64,
}

impl Shape for Circle {
    fn area(&self) -> f64 {
        3.141592653589793 * self.radius * self.radius
    }
}

fn print_shape(shape: impl Shape) {
    println!("{}", shape.area());
}

fn make() -> impl Shape {
    Circle { radius: 1.0 }
}

fn main() {
    print_shape(make());
}
```

1. `impl Pact` en parámetro es azúcar para un parámetro genérico con bound.
2. `impl Pact` en retorno es un tipo opaco; el llamador solo puede usar los
   métodos del `pact`.
3. No se puede usar `impl Pact` en campos de `rune`; usa un parámetro genérico o
   `Box[dyn Pact]`.
4. `impl Pact` no es `dyn Pact`: no hay despacho dinámico ni tamaño de trait
   object.
5. En un `pact`, `impl Pact` en retorno es RPITIT (§36).

### 35.7 Blanket implementations

```pengu
pact Show
    show = (@) -> String

ritual[T] Show for T where T: Display
    show = (@) -> String
        format!("{}", @)

bind n = 7
print(n.show())
```

Rust generado:

```rust
trait Show {
    fn show(&self) -> String;
}

impl<T: std::fmt::Display> Show for T {
    fn show(&self) -> String {
        format!("{}", self)
    }
}

fn main() {
    let n = 7;
    println!("{}", n.show());
}
```

1. Una blanket impl implementa un `pact` para todos los `T` que cumplen un
   bound: `ritual[T] Pact for T where ...`.
2. Debe ser coherente: no puede solaparse con otra implementación del mismo
   `pact` para un tipo concreto (`PGS-E3504`).
3. El `pact` debe ser local o el tipo debe ser local (regla huérfana).
4. Las blanket impls son potentes pero pueden impedir implementaciones futuras;
   se documentan y se prueban.

### 35.8 Auto traits y marker traits

- `Send`, `Sync`, `Sized`, `Unpin` son auto traits: el compilador los deriva de
  los campos.
- `Copy`, `Clone`, `Debug`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`, `Hash`,
  `Default` son traits normales; se implementan con `ritual` o `@@derive`.
- `Send`/`Sync` manuales solo se escriben con `curse ritual ... for ...` y
  requieren justificación de seguridad (§52).
- Un `pact` marker (sin métodos) se puede usar como bound: `pact Magic` +
  `T: Magic`.
- No hay `pact` con estado global ni métodos estáticos mutables.

### 35.9 Coherencia, huérfanos y sellado

1. `ritual Tipo for Pact` exige que `Tipo` o `Pact` sea local.
2. Un `pact` externo para un tipo externo es error de huérfano (`PGS-E3505`).
3. Dos implementaciones que pueden aplicar al mismo tipo son solapamiento
   (`PGS-E3504`).
4. No hay especialización ni `default` en `ritual`.
5. **Sellado por visibilidad:** si un `pact` público tiene un supertrait
   privado, los consumidores externos no pueden implementarlo. PenguScript no
   añade una palabra `seal`; el sellado se logra con `unveil` y un `pact`
   privado:

```pengu
pact Sealed
    hidden = (@) -> Unit

pact Public: Sealed
    value = (@) -> Int

rune Token
    id: Int

ritual Sealed for Token
    hidden = (@) -> Unit
        ()

ritual Public for Token
    value = (@) -> Int
        @.id
```

Rust generado:

```rust
trait Sealed {
    fn hidden(&self);
}

trait Public: Sealed {
    fn value(&self) -> i32;
}

struct Token {
    id: i32,
}

impl Sealed for Token {
    fn hidden(&self) {}
}

impl Public for Token {
    fn value(&self) -> i32 {
        self.id
    }
}

fn main() {
    let t = Token { id: 7 };
    println!("{}", t.value());
}
```

### 35.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3501` | falta un método requerido | implementarlo |
| `PGS-E3502` | `pact` implementado dos veces | eliminar duplicado |
| `PGS-E3503` | `Self` fuera de `pact`/`ritual` | moverlo dentro |
| `PGS-E3504` | implementaciones solapadas | separar tipos o bounds |
| `PGS-E3505` | violación de huérfano | hacer local el tipo o el `pact` |
| `PGS-E3506` | `dyn Pact` no object-safe | quitar genéricos/`Self` por valor |
| `PGS-E3507` | método de `pact` sin receptor mal usado | añadir `@` o llamar como asociado |
| `PGS-W3501` | método default sobrescrito sin necesidad | documentar la diferencia |
| `PGS-W3502` | blanket impl muy amplia | acotar el bound |

### 35.11 Criterios de aceptación

- [x] Declaración, métodos y default están definidos.
- [x] `pact` genérico y `dyn` tienen ejemplo.
- [x] Object safety está explicada.
- [x] `impl Trait` y blanket impls están cubiertas.
- [x] Coherencia, huérfanos y sellado por visibilidad están definidos.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-36-associated-items"></a>
## 36. Associated items (types, consts, GATs)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 5 |
| Rust | `type`, `const`, GATs, RPITIT, `async fn` |
| Palabras mágicas | `pact`, `essence`, `sigil`, `Self` |
| Depende de | §31, §35 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec36_associated.pengu` |

Los **items asociados** pertenecen a un `pact` o a un `ritual`, no al módulo.
Pueden ser tipos (`essence`), constantes (`sigil`) o funciones. Permiten que un
contrato diga “tengo un tipo de elemento” sin fijarlo en la declaración.

### 36.1 Tipos asociados

```pengu
pact Container
    essence Item

    first = (@) -> ?&Item

rune Numbers
    values: Vec[Int]

ritual Container for Numbers
    essence Item = Int

    first = (@) -> ?&Int
        @.values.first()

bind n = Numbers(values: Vec[1, 2, 3])
print(n.first())
```

Rust generado:

```rust
trait Container {
    type Item;

    fn first(&self) -> Option<&Self::Item>;
}

struct Numbers {
    values: Vec<i32>,
}

impl Container for Numbers {
    type Item = i32;

    fn first(&self) -> Option<&i32> {
        self.values.first()
    }
}

fn main() {
    let n = Numbers { values: vec![1, 2, 3] };
    println!("{:?}", n.first());
}
```

Reglas:

1. `essence Nombre` sin `=` declara un tipo asociado en un `pact`.
2. `essence Nombre = Tipo` lo fija en un `ritual`.
3. Dentro del `pact`, `Item` se refiere a `Self::Item`; fuera se proyecta con
   `Self::Item` o `Pact::Item` según el contexto.
4. Un tipo asociado debe fijarse exactamente una vez por implementación
   (`PGS-E3601`).
5. El tipo puede depender de los parámetros del `pact`.
6. No hay defaults de tipo asociado en el subconjunto estable; se fija en cada
   `ritual`.

### 36.2 Proyecciones y bounds

```pengu
pact Container
    essence Item
    first = (@) -> ?&Item

sum_first = [C](container: &C) -> ?Int where C: Container[Item = Int]
    container.first().copied()

rune Numbers
    values: Vec[Int]

ritual Container for Numbers
    essence Item = Int
    first = (@) -> ?&Int
        @.values.first()

bind n = Numbers(values: Vec[1, 2, 3])
print(sum_first(&n))
```

Rust generado:

```rust
trait Container {
    type Item;
    fn first(&self) -> Option<&Self::Item>;
}

fn sum_first<C>(container: &C) -> Option<i32>
where
    C: Container<Item = i32>,
{
    container.first().copied()
}

struct Numbers {
    values: Vec<i32>,
}

impl Container for Numbers {
    type Item = i32;
    fn first(&self) -> Option<&i32> {
        self.values.first()
    }
}

fn main() {
    let n = Numbers { values: vec![1, 2, 3] };
    println!("{:?}", sum_first(&n));
}
```

1. `Pact[Item = Tipo]` fija el asociado en un bound.
2. `Self::Item` es la proyección dentro del `pact`; `C::Item` es la proyección
   sobre un parámetro.
3. No se puede asumir un asociado no fijado; el compilador lo trata como opaco.
4. Un bound de asociado no crea una implementación; solo restringe.

### 36.3 Constantes asociadas

```pengu
pact Limits
    sigil MAX: Int
    sigil NAME: &'static Str

rune Small
    value: Int

ritual Limits for Small
    sigil MAX: Int = 100
    sigil NAME: &'static Str = "small"

print(Small.MAX)
print(Small.NAME)
```

Rust generado:

```rust
trait Limits {
    const MAX: i32;
    const NAME: &'static str;
}

struct Small {
    value: i32,
}

impl Limits for Small {
    const MAX: i32 = 100;
    const NAME: &'static str = "small";
}

fn main() {
    println!("{}", Small::MAX);
    println!("{}", Small::NAME);
}
```

1. Una constante asociada se declara con `sigil` dentro de un `pact`.
2. Debe ser evaluable en `const`; no puede llamar a métodos no `const`.
3. Se accede como `Tipo.CONSTANTE`, no como `Tipo.CONSTANTE()`.
4. Un `pact` con constantes asociadas no es object safe (§35.5).
5. El tipo debe ser `Sized` para una constante asociada de tipo `Self`; se
   prefiere un tipo concreto.

### 36.4 GATs (generic associated types)

Un **GAT** es un tipo asociado con parámetros propios, normalmente un lifetime:

```pengu
pact Lending
    essence View['a] where Self: 'a
    view = ['a](@) -> Self::View['a]

rune Buffer
    data: Vec[Int]

ritual Lending for Buffer
    essence View['a] = &'a [Int]

    view = ['a](@) -> &'a [Int]
        &@.data[..]

bind b = Buffer(data: Vec[1, 2, 3])
print(b.view().len())
```

Rust generado:

```rust
trait Lending {
    type View<'a>
    where
        Self: 'a;

    fn view<'a>(&'a self) -> Self::View<'a>;
}

struct Buffer {
    data: Vec<i32>,
}

impl Lending for Buffer {
    type View<'a> = &'a [i32];

    fn view<'a>(&'a self) -> &'a [i32] {
        &self.data[..]
    }
}

fn main() {
    let b = Buffer { data: vec![1, 2, 3] };
    println!("{}", b.view().len());
}
```

Reglas:

1. `essence View['a]` declara un GAT con un parámetro de lifetime; el
   `where Self: 'a` es obligatorio en el subconjunto estable de Rust.
2. Los parámetros del GAT se declaran en el corchete, como los de un `rune`.
3. En el `ritual`, `essence View['a] = &'a [Int]` fija la familia de tipos.
4. El método que devuelve `Self::View['a]` declara `['a]` y usa `@` con ese
   lifetime. El GAT exige `where Self: 'a` para que la implementación pueda
   prestar datos del receptor.
5. Los GATs permiten préstamos sin boxeo; son la base de iteradores que
   devuelven referencias.
6. No se permiten GATs con parámetros de tipo que no aparezcan en la firma;
   el compilador los rechaza.

### 36.5 RPITIT y `async fn` en `pact`

Un método de `pact` puede devolver `impl Iterator` (RPITIT) o ser `dream`:

```pengu
pact Evens
    evens = (@) -> impl Iterator[Item = Int]

rune Numbers
    values: Vec[Int]

ritual Evens for Numbers
    evens = (@) -> impl Iterator[Item = Int]
        @.values.iter().copied().filter((x: Int) => x % 2 == 0)

bind n = Numbers(values: Vec[1, 2, 3, 4])
print(n.evens().count())
```

Rust generado:

```rust
trait Evens {
    fn evens(&self) -> impl Iterator<Item = i32>;
}

struct Numbers {
    values: Vec<i32>,
}

impl Evens for Numbers {
    fn evens(&self) -> impl Iterator<Item = i32> {
        self.values.iter().copied().filter(|x| x % 2 == 0)
    }
}

fn main() {
    let n = Numbers { values: vec![1, 2, 3, 4] };
    println!("{}", n.evens().count());
}
```

`async fn` en un `pact` se declara con `dream`:

```pengu
pact Fetch
    dream fetch = (@) -> String

rune Client
    name: String

ritual Fetch for Client
    dream fetch = (@) -> String
        "data from #{@.name}"
```

Rust generado:

```rust
trait Fetch {
    async fn fetch(&self) -> String;
}

struct Client {
    name: String,
}

impl Fetch for Client {
    async fn fetch(&self) -> String {
        format!("data from {}", self.name)
    }
}
```

1. RPITIT devuelve un tipo opaco por método; no se puede nombrar fuera del
   `pact`.
2. `impl Iterator[Item = Int]` es la forma de return-position `impl Trait`.
3. `dream` en un `pact` es `async fn`; el llamador necesita un runtime (§50).
4. Un `pact` con `async fn` no es object safe en el sentido clásico; para
   despacho dinámico se usa `dyn` con cuidado o se evita.
5. `impl Trait` en retorno de un `pact` captura los lifetimes del receptor; si
   el préstamo no vive, el compilador lo rechaza.

### 36.6 `Self` y proyecciones

1. `Self` es el tipo que implementa; en un `pact` es el tipo del receptor.
2. `Self::Item` proyecta un tipo asociado; `Self` solo es válido en
   `pact`/`ritual`.
3. En un `ritual`, `Self` se puede usar en firmas y cuerpos.
4. `Self` no se puede usar como valor de retorno por valor en un `pact` object
   safe; usa `&Self` o un tipo concreto.
5. Las proyecciones no se evalúan en runtime; son tipos.

### 36.7 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3601` | tipo asociado no fijado | añadir `essence Item = Tipo` |
| `PGS-E3602` | tipo asociado fijado dos veces | eliminar duplicado |
| `PGS-E3603` | GAT con parámetro no usado | usar el parámetro o eliminarlo |
| `PGS-E3604` | bound de asociado incompatible | alinear `Pact[Item = Tipo]` |
| `PGS-E3605` | `impl Trait` en posición inválida | moverlo a retorno/parámetro |
| `PGS-E3606` | `async fn` en `pact` object-safe | usar `dyn` compatible o evitar |
| `PGS-E3607` | constante asociada no const | simplificar la expresión |
| `PGS-W3601` | GAT que solo se usa con un lifetime | simplificar a tipo asociado |

### 36.8 Criterios de aceptación

- [x] Tipos asociados, proyecciones y bounds tienen ejemplo.
- [x] Constantes asociadas están definidas.
- [x] GATs tienen ejemplo compilable.
- [x] RPITIT y `async fn` en `pact` están cubiertos.
- [x] `Self` y los diagnósticos están explicados.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-37-hrtb"></a>
## 37. Higher-Ranked Items (HRTB)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 5 |
| Rust | `for<'a>`, HRTB, function pointers |
| Palabras mágicas | `for<'a>`, `Fn`, `dyn` |
| Depende de | §18, §34, §38, §39 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec37_hrtb.pengu` |

Un **Higher-Ranked Trait Bound** (HRTB) expresa que una función o un tipo debe
funcionar para **todos** los lifetimes, no para uno concreto. Se escribe
`for<'a>` y se lee “para todo `'a`”. No es un tipo de item nuevo: es una forma de
cuantificar lifetimes en un bound o en un tipo de función.

### 37.1 `for<'a>` en tipos de función

```pengu
first = (s: &Str) -> &Str
    &s[..1]

apply_fn = (f: for<'a> (&'a Str) -> &'a Str, s: &Str) -> &Str
    f(s)

print(apply_fn(first, "pengu"))
```

Rust generado:

```rust
fn first(s: &str) -> &str {
    &s[..1]
}

fn apply_fn(f: for<'a> fn(&'a str) -> &'a str, s: &str) -> &str {
    f(s)
}

fn main() {
    println!("{}", apply_fn(first, "pengu"));
}
```

`for<'a> (&'a Str) -> &'a Str` en posición de tipo es un **fn pointer**: no
captura entorno. Para aceptar closures que capturan se usa un parámetro
genérico con bound `F: for<'a> Fn(&'a Str) -> &'a Str` (§37.2).

Reglas:

1. `for<'a> (A) -> B` es un tipo de función que funciona para cualquier
   lifetime `'a`.
2. `for<'a>` solo cuantifica lifetimes; no existen `for<T>` ni `for<const N>`.
3. Un `fn` item como `first` cumple automáticamente el HRTB si su firma es
   compatible.
4. Un function pointer (`fn`) es `Copy`; un closure que captura no lo es
   necesariamente (§38).
5. La forma sin `for<'a>` puede ser early-bound o elidida; si el préstamo debe
   vivir lo que el llamador decida, se escribe `for<'a>`.

### 37.2 HRTB en bounds

```pengu
apply = [F](f: F, s: &Str) -> &Str where F: for<'a> Fn(&'a Str) -> &'a Str
    f(s)

print(apply(first, "pengu"))
```

Rust generado:

```rust
fn first(s: &str) -> &str {
    &s[..1]
}

fn apply<F>(f: F, s: &str) -> &str
where
    F: for<'a> Fn(&'a str) -> &'a str,
{
    f(s)
}

fn main() {
    println!("{}", apply(first, "pengu"));
}
```

1. `F: for<'a> Fn(&'a T) -> &'a U` exige que `F` acepte cualquier lifetime.
2. Se puede combinar con otros bounds: `F: for<'a> Fn(&'a T) + Clone`.
3. El HRTB se comprueba en el punto de llamada; un closure que solo acepta un
   lifetime concreto no cumple.
4. La sintaxis `for<'a>` también aparece en `dyn` y en tipos de función.

### 37.3 `dyn for<'a>`

```pengu
first = (s: &Str) -> &Str
    &s[..1]

bind f: Box[dyn for<'a> Fn(&'a Str) -> &'a Str] = Box.new(first)
print(f("pengu"))
```

Rust generado:

```rust
fn first(s: &str) -> &str {
    &s[..1]
}

fn main() {
    let f: Box<dyn for<'a> Fn(&'a str) -> &'a str> = Box::new(first);
    println!("{}", f("pengu"));
}
```

1. `dyn for<'a> Fn(...)` es un trait object que acepta cualquier lifetime.
2. Necesita un puntero (`Box`, `&`, `Rc`, `Arc`).
3. El trait object no puede tener métodos genéricos; `for<'a>` en la firma no
   viola object safety porque el lifetime es parte del contrato.
4. `Fn`, `FnMut` y `FnOnce` aceptan `for<'a>`; `FnOnce` se consume al llamar.

### 37.4 Late-bound y early-bound

- Un lifetime **late-bound** se introduce en la llamada; `for<'a>` lo hace
  explícito. Es el caso de `fn(&str) -> &str` cuando la elisión lo permite.
- Un lifetime **early-bound** se fija al construir el item o el trait object;
  aparece en la firma del `fn` o en los parámetros del tipo.
- `for<'a>` fuerza late-bound: el llamador elige `'a` en cada llamada.
- Si un lifetime aparece solo en el retorno, debe estar conectado a un
  parámetro; si no, el compilador lo rechaza (`PGS-E3702`).

### 37.5 HRTB y closures

```pengu
apply = [F](f: F, s: &Str) -> &Str where F: for<'a> Fn(&'a Str) -> &'a Str
    f(s)

bind first = (s: &Str) => &s[..1]
print(apply(first, "pengu"))
```

1. Un closure puede cumplir un HRTB si no captura de forma que fije el lifetime.
2. Si el closure captura una referencia con un lifetime concreto, el HRTB puede
   fallar; usa `move` o un `fn` item.
3. `dyn for<'a> Fn` acepta closures y fn pointers.
4. Un closure que muta el entorno es `FnMut`; el HRTB se escribe
   `for<'a> FnMut(&'a T)`.

### 37.6 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3701` | `for` sin lifetime | usar `for<'a>` |
| `PGS-E3702` | lifetime de retorno no conectado a un parámetro | añadir el préstamo o `'static` |
| `PGS-E3703` | HRTB no satisfecho por el closure | usar `move` o un `fn` item |
| `PGS-E3704` | `dyn` sin puntero | envolver en `Box[dyn ...]` o `&dyn ...` |
| `PGS-E3705` | `for<T>` o `for<const N>` | solo se cuantifican lifetimes |
| `PGS-W3701` | `for<'a>` redundante con la elisión | simplificar si no cambia la semántica |

### 37.7 Criterios de aceptación

- [x] `for<'a>` en tipos de función y bounds tiene ejemplo.
- [x] `dyn for<'a>` y su necesidad de puntero están definidos.
- [x] Late-bound/early-bound están explicados.
- [x] HRTB con closures está cubierto.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-38-closures"></a>
## 38. Closures

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 5 |
| Rust | Closures, `Fn`/`FnMut`/`FnOnce`, `move` |
| Palabras mágicas | `=>`, `move`, `Fn`, `FnMut`, `FnOnce` |
| Depende de | §15, §17, §18, §37 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec38_closures.pengu` |

Una **closure** es una función anónima que puede capturar variables del entorno.
En PenguScript se escribe con `=>`; `->` se reserva para funciones nombradas y
tipos de función. La closure infiere sus tipos y su tipo de retorno; no se
declara `=> Tipo`.

### 38.1 Sintaxis

```pengu
bind inc = (x: Int) => x + 1
print(inc(4))

bind add = (a: Int, b: Int) =>
    a + b

print(add(2, 3))
```

Rust generado:

```rust
fn main() {
    let inc = |x: i32| x + 1;
    println!("{}", inc(4));

    let add = |a: i32, b: i32| {
        a + b
    };

    println!("{}", add(2, 3));
}
```

Reglas:

1. La forma corta es `(params) => expr`; la forma de bloque es `(params) =>`
   seguida de líneas indentadas.
2. Los tipos de los parámetros son opcionales si el contexto los infiere; en
   APIs públicas se escriben.
3. No se escribe tipo de retorno en la closure; se infiere.
4. Una closure se asigna con `bind` o `morph`, no se declara como item.
5. No hay closures genéricas; si necesitas genéricos, usa una función nombrada o
   un `pact`.
6. `=>` no se usa para `match`; los brazos usan `then`/bloques (§30).

### 38.2 Captura por referencia

```pengu
bind base = 10
bind add_base = (x: Int) => x + base
print(add_base(5))
```

Rust generado:

```rust
fn main() {
    let base = 10;
    let add_base = |x: i32| x + base;
    println!("{}", add_base(5));
}
```

1. Si la closure solo lee una variable, la captura es por referencia compartida
   (`&T`).
2. La variable debe vivir al menos lo que la closure.
3. El compilador infiere `Fn` si no muta ni consume.
4. No se puede mutar una captura compartida; para eso se usa `FnMut`.

### 38.3 Captura mutable y `FnMut`

```pengu
morph count = 0
morph inc = () => count += 1
inc()
inc()
drop(inc)
print(count)
```

Rust generado:

```rust
fn main() {
    let mut count = 0;
    let mut inc = || count += 1;
    inc();
    inc();
    drop(inc);
    println!("{}", count);
}
```

1. Una closure que muta una captura es `FnMut`.
2. El binding de la closure debe ser `morph`, porque llamarla requiere `&mut`.
3. Mientras la closure vive, la variable capturada está prestada mutuamente; no
   se puede usar directamente. Se libera con `drop(closure)` o al salir del
   scope.
4. `bind inc = ...` con una closure `FnMut` es error (`PGS-E3802`).

### 38.4 `move`

```pengu
bind owner = String.from("pengu")
bind take = move () => print(owner)
take()
```

Rust generado:

```rust
fn main() {
    let owner = String::from("pengu");
    let take = move || println!("{}", owner);
    take();
}
```

1. `move` captura por valor, no por referencia.
2. Es obligatorio cuando la closure sobrevive a la variable o se devuelve.
3. Mover un `String`/`Vec` transfiere la propiedad; la variable original queda
   movida y no se puede usar.
4. `move` no implica `FnOnce`; una closure `move` que solo lee puede ser `Fn`.

### 38.5 Devolver closures

```pengu
make_adder = (n: Int) -> impl Fn(Int) -> Int
    move (x: Int) => x + n

bind add5 = make_adder(5)
print(add5(3))
```

Rust generado:

```rust
fn make_adder(n: i32) -> impl Fn(i32) -> i32 {
    move |x| x + n
}

fn main() {
    let add5 = make_adder(5);
    println!("{}", add5(3));
}
```

1. El retorno es `impl Fn(...) -> ...`; el tipo concreto es opaco.
2. `move` es necesario para que `n` viva dentro de la closure.
3. No se puede devolver `dyn Fn` sin `Box`/`Rc`.
4. Si la closure muta estado, el retorno es `impl FnMut(...)` y el binding del
   llamador debe ser `morph`.

### 38.6 `Fn`, `FnMut`, `FnOnce`

| Trait | Puede llamarse | Captura | Binding |
|---|---|---|---|
| `Fn` | muchas veces | `&T` | `bind` |
| `FnMut` | muchas veces | `&mut T` | `morph` |
| `FnOnce` | una vez | `T` | `bind`/`morph` |

1. El compilador elige el trait más permisivo que la closure cumple.
2. `Fn` implica `FnMut`; `FnMut` implica `FnOnce`.
3. Una closure que consume una captura es `FnOnce`.
4. Un parámetro `f: impl Fn(Int) -> Int` acepta `Fn`; para `FnMut` se escribe
   `impl FnMut(Int) -> Int` y el parámetro debe ser `morph` para llamarlo.
5. `dyn Fn` necesita un puntero: `Box[dyn Fn(Int) -> Int]`.

### 38.7 Closures en structs

```pengu
rune Handler[F]
    run: F

bind h = Handler(run: (x: Int) => x + 1)
print((h.run)(1))
```

Rust generado:

```rust
struct Handler<F> {
    run: F,
}

fn main() {
    let h = Handler { run: |x: i32| x + 1 };
    println!("{}", (h.run)(1));
}
```

1. Un campo de closure usa un parámetro genérico `F` o `Box[dyn Fn...]`; no se
   puede usar `impl Fn` en un campo.
2. `Handler[F]` es genérico; cada closure produce una instancia distinta.
3. Para guardar closures heterogéneas se usa `Vec[Box[dyn Fn(Int) -> Int]]`.
4. La closure puede capturar; el struct se vuelve dueño de la captura si se usa
   `move`.

### 38.8 Recursión y closures

Una closure no puede llamarse a sí misma por el nombre del binding: el nombre
no existe hasta que termina la inicialización. Para recursión se usa una función
nombrada:

```pengu
factorial = (n: Int) -> Int
    if n <= 1 then 1 else n * factorial(n - 1)

print(factorial(5))
```

Rust generado:

```rust
fn factorial(n: i32) -> i32 {
    if n <= 1 { 1 } else { n * factorial(n - 1) }
}

fn main() {
    println!("{}", factorial(5));
}
```

1. Las funciones nombradas sí pueden ser recursivas.
2. Una closure recursiva requiere una indirección (`Rc<RefCell<...>>`) o un
   combinador; se desaconseja y se documenta como patrón avanzado.
3. No hay `let rec` ni `self` en closures.

### 38.9 HRTB y closures

```pengu
apply = [F](f: F, s: &Str) -> &Str where F: for<'a> Fn(&'a Str) -> &'a Str
    f(s)

bind first = (s: &Str) => &s[..1]
print(apply(first, "pengu"))
```

1. Una closure puede cumplir `for<'a> Fn(...)` si no fija el lifetime en una
   captura.
2. `move` puede ayudar, pero no cambia la firma; el HRTB se comprueba aparte.
3. Para callbacks que aceptan cualquier préstamo se prefiere `fn` item o
   `dyn for<'a> Fn`.
4. Los detalles de HRTB están en §37.

### 38.10 `dream` closures

La forma `dream (params) => ...` se reserva para closures asíncronas. Su
semántica, runtime y bounds se definen en §50; en Fase 5 no se generan ejemplos
ejecutables. Una closure normal no puede usar `awaken` sin un contexto async.

### 38.11 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3801` | closure con tipo de retorno explícito | quitarlo; se infiere |
| `PGS-E3802` | `bind` para una closure `FnMut` | usar `morph` |
| `PGS-E3803` | captura movida y usada después | reordenar o clonar |
| `PGS-E3804` | `move` innecesario que impide reutilizar | quitar `move` |
| `PGS-E3805` | closure devuelta sin `move` | añadir `move` |
| `PGS-E3806` | `impl Fn` en campo de struct | usar genérico o `Box[dyn Fn]` |
| `PGS-E3807` | recursión por nombre de closure | usar función nombrada |
| `PGS-W3801` | closure que podría ser función | extraer a `name = (...) -> ...` |

### 38.12 Criterios de aceptación

- [x] Sintaxis corta y de bloque están definidas.
- [x] Captura por referencia, mutable y `move` tienen ejemplo.
- [x] Devolver closures y `Fn`/`FnMut`/`FnOnce` están cubiertos.
- [x] Closures en structs, recursión y HRTB están explicados.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-39-function-pointers"></a>
## 39. Function pointers y higher-order functions

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 5 |
| Rust | Funciones de orden superior, iteradores, `Option`/`Result` |
| Palabras mágicas | `Fn`, `map`, `filter`, `fold`, `impl` |
| Depende de | §15, §23, §34, §38 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec39_functional.pengu` |

PenguScript no es un lenguaje funcional puro, pero adopta lo útil de ese estilo:
funciones como valores, composición, iteradores perezosos y combinadores de
`Option`/`Result`. Todo se apoya en traits de Rust (`Fn`, `Iterator`), sin
monadas, sin notación `do` y sin currying automático.

### 39.1 Funciones como valores

```pengu
double = (x: Int) -> Int
    x * 2

apply = (f: (Int) -> Int, x: Int) -> Int
    f(x)

print(apply(double, 5))
```

Rust generado:

```rust
fn double(x: i32) -> i32 {
    x * 2
}

fn apply(f: fn(i32) -> i32, x: i32) -> i32 {
    f(x)
}

fn main() {
    println!("{}", apply(double, 5));
}
```

1. Un `fn` item se usa como valor y se convierte a function pointer cuando el
   contexto lo pide.
2. Un function pointer es `Copy`, no captura y no tiene estado.
3. Un parámetro `(Int) -> Int` es un function pointer; para aceptar closures se
   usa un genérico `F: Fn(Int) -> Int` o `impl Fn(Int) -> Int`.
4. No hay sobrecarga por firma; el tipo del parámetro decide.

### 39.2 Genéricos y `Fn`

```pengu
double = (x: Int) -> Int
    x * 2

apply = [F](f: F, x: Int) -> Int where F: Fn(Int) -> Int
    f(x)

print(apply(double, 5))
print(apply((x: Int) => x + 1, 5))
```

Rust generado:

```rust
fn double(x: i32) -> i32 {
    x * 2
}

fn apply<F>(f: F, x: i32) -> i32
where
    F: Fn(i32) -> i32,
{
    f(x)
}

fn main() {
    println!("{}", apply(double, 5));
    println!("{}", apply(|x| x + 1, 5));
}
```

1. `F: Fn(Int) -> Int` acepta funciones, closures y function pointers.
2. Para mutar estado se usa `FnMut`; para consumir, `FnOnce` (§38).
3. `impl Fn(Int) -> Int` es azúcar para un parámetro genérico; no permite
   nombrar `F` en el cuerpo.
4. El compilador monomorfiza: una instancia por tipo de closure.

### 39.3 Iteradores: adaptadores y consumidores

```pengu
bind nums = [1, 2, 3, 4]

bind doubled = nums.iter()
    .map((x: &Int) => *x * 2)
    .collect[Vec[Int]]()

print(doubled)
```

Rust generado:

```rust
fn main() {
    let nums = [1, 2, 3, 4];

    let doubled = nums
        .iter()
        .map(|x| *x * 2)
        .collect::<Vec<i32>>();

    println!("{:?}", doubled);
}
```

1. `iter()` produce `&T`; `into_iter()` consume y produce `T`; `iter_mut()`
   produce `&mut T`.
2. `map`, `filter`, `flat_map`, `take`, `skip`, `step_by`, `chain`, `zip` son
   adaptadores perezosos: no hacen trabajo hasta un consumidor.
3. `collect`, `fold`, `sum`, `count`, `for_each`, `any`, `all` son consumidores.
4. `collect[Vec[Int]]()` fija el tipo de destino con turbofish; sin él, el
   compilador no sabe qué colección construir.
5. Una cadena de iteradores no asigna un `Vec` intermedio; el compilador la
   fusiona.

### 39.4 `fold`

```pengu
bind nums = [1, 2, 3, 4]
bind total = nums.iter().fold(0, (acc: Int, x: &Int) => acc + *x)
print(total)
```

Rust generado:

```rust
fn main() {
    let nums = [1, 2, 3, 4];
    let total = nums.iter().fold(0, |acc, x| acc + *x);
    println!("{}", total);
}
```

1. `fold(inicial, f)` es el consumidor universal: suma, producto, construcción
   de colecciones, máquina de estados.
2. El acumulador puede cambiar de tipo: `fold(String.new(), ...)`.
3. Para cortocircuito se usa `try_fold` o `find`/`any`, no `fold`.
4. `reduce` existe para el primer elemento; falla en vacío (`none`).

### 39.5 `Option` como funtor

```pengu
bind value: ?Int = some(3)
bind doubled = value.map((x: Int) => x * 2)
print(doubled.unwrap_or(0))

bind chained = value.and_then((x: Int) => if x > 0 then some(x + 1) else none)
print(chained.unwrap_or(0))
```

Rust generado:

```rust
fn main() {
    let value: Option<i32> = Some(3);
    let doubled = value.map(|x| x * 2);
    println!("{}", doubled.unwrap_or(0));

    let chained = value.and_then(|x| if x > 0 { Some(x + 1) } else { None });
    println!("{}", chained.unwrap_or(0));
}
```

1. `map` transforma el valor presente; `none` se propaga.
2. `and_then` encadena funciones que devuelven `?U`; evita `Option[Option[U]]`.
3. `unwrap_or`, `unwrap_or_else`, `ok_or`, `filter` son los combinadores
   habituales.
4. `?` en una función que devuelve `?T` propaga `none`; en `!T` propaga `err`.
5. No hay `null`; la ausencia es un valor explícito.

### 39.6 `Result` como funtor

```pengu
parse = (text: &Str) -> !Int
    text.parse[Int]()

bind value: !Int = parse("41")
bind next = value.map((x: Int) => x + 1)
print(next.unwrap_or(0))
```

Rust generado:

```rust
fn parse(text: &str) -> Result<i32, Box<dyn std::error::Error + Send + Sync>> {
    text.parse::<i32>().map_err(|e| Box::new(e) as Box<dyn std::error::Error + Send + Sync>)
}

fn main() {
    let value: Result<i32, Box<dyn std::error::Error + Send + Sync>> = parse("41");
    let next = value.map(|x| x + 1);
    println!("{}", next.unwrap_or(0));
}
```

1. `map` transforma el éxito; `map_err` transforma el error.
2. `and_then` encadena operaciones falibles; `or_else` recupera.
3. `?` propaga el error y convierte con `From`; el tipo de error debe ser
   compatible.
4. `unwrap_or` descarta el error; solo para prototipos o valores por defecto
   seguros.
5. `Error` es `Box<dyn Error + Send + Sync>` (§4.4).

### 39.7 Composición

```pengu
compose = [A, B, C](f: (B) -> C, g: (A) -> B) -> impl Fn(A) -> C
    move (x: A) => f(g(x))

bind inc = (x: Int) => x + 1
bind double = (x: Int) => x * 2
bind inc_then_double = compose(double, inc)
print(inc_then_double(3))
```

Rust generado:

```rust
fn compose<A, B, C, F, G>(f: F, g: G) -> impl Fn(A) -> C
where
    F: Fn(B) -> C,
    G: Fn(A) -> B,
{
    move |x| f(g(x))
}

fn main() {
    let inc = |x: i32| x + 1;
    let double = |x: i32| x * 2;
    let inc_then_double = compose(double, inc);
    println!("{}", inc_then_double(3));
}
```

1. `compose(f, g)` aplica `g` y luego `f`; el orden se documenta.
2. No hay operador `>>`/`<<`; se usa una función.
3. La composición devuelve `impl Fn` y captura por `move`.
4. Para pipelines largos, los iteradores suelen ser más legibles que componer
   funciones.

### 39.8 Qué no se adopta

- No hay currying automático: `f(a)(b)` requiere una función que devuelva otra.
- No hay typeclasses/HKT; los traits son el mecanismo de abstracción.
- No hay `do`-notation ni mónadas; `?` y `and_then` cubren el encadenamiento.
- No hay pattern matching en parámetros de closure; se hace en el cuerpo.
- No hay evaluación perezosa general; solo iteradores.
- No hay `compose` en el prelude; se define cuando se necesita.

### 39.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3901` | `map` sin tipo de `collect` | añadir turbofish `collect[Vec[Int]]()` |
| `PGS-E3902` | `fold` con acumulador incompatible | anotar el inicial o el retorno |
| `PGS-E3903` | `FnOnce` llamado dos veces | usar `Fn`/`FnMut` o consumir una vez |
| `PGS-E3904` | `?` en función que no devuelve `?T`/`!T` | cambiar el retorno o usar `match` |
| `PGS-E3905` | `and_then` devuelve `?T` dentro de `!T` | convertir con `ok_or`/`map_err` |
| `PGS-W3901` | cadena de iteradores con `collect` intermedio innecesario | eliminar el `Vec` intermedio |

### 39.10 Criterios de aceptación

- [x] Funciones como valores y `Fn` están definidas.
- [x] Iteradores perezosos, consumidores y `collect` tienen ejemplo.
- [x] `fold`, `Option` y `Result` tienen ejemplo.
- [x] Composición y límites del estilo funcional están explicados.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-40-operator-overloading"></a>
## 40. Operator overloading

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 5 |
| Rust | `Add`, `Sub`, `Mul`, `Index`, `Deref`, `PartialEq`, `Display` |
| Palabras mágicas | `ritual`, `essence`, `@`, `@own` |
| Depende de | §11, §31, §35, §36 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec40_operators.pengu` |

Un operador no es una construcción especial: es azúcar para un método de un
trait de `std`. PenguScript no permite inventar operadores ni precedencias; solo
implementar los traits existentes. Esto mantiene el código predecible y la
interoperabilidad con Rust.

### 40.1 `Add`, `Sub`, `Mul`, `Div`, `Rem`

```pengu
summon std::ops::Add

rune Point
    x: Int
    y: Int

ritual Point for Add
    essence Output = Point

    add = (@own, other: Point) -> Point
        Point(x: @.x + other.x, y: @.y + other.y)

bind p = Point(x: 1, y: 2) + Point(x: 3, y: 4)
print(p.x)
print(p.y)
```

Rust generado:

```rust
use std::ops::Add;

struct Point {
    x: i32,
    y: i32,
}

impl Add for Point {
    type Output = Point;

    fn add(self, other: Point) -> Point {
        Point {
            x: self.x + other.x,
            y: self.y + other.y,
        }
    }
}

fn main() {
    let p = Point { x: 1, y: 2 } + Point { x: 3, y: 4 };
    println!("{}", p.x);
    println!("{}", p.y);
}
```

Reglas:

1. El trait se nombra sin `std::ops::` si se importa con `summon`; también se
   puede escribir `std::ops::Add`.
2. `essence Output` fija el tipo de retorno; sin él, el trait no está completo.
3. `@own` es el receptor por valor (`self`); para operadores que consumen el
   operando izquierdo es lo correcto.
4. `add` recibe el operando derecho como parámetro normal.
5. `+` sigue la precedencia de §11; la implementación no la cambia.
6. `Add` no genera `AddAssign`; `+=` requiere `ritual Point for AddAssign`.
7. `Output` puede ser distinto de `Point` (por ejemplo, `Vector` + `Scalar`).

### 40.2 `AddAssign` y operadores de asignación

```pengu
summon std::ops::AddAssign

rune Counter
    value: Int

ritual Counter for AddAssign[Int]
    add_assign = (@mut, other: Int)
        @.value += other

morph c = Counter(value: 0)
c += 3
print(c.value)
```

Rust generado:

```rust
use std::ops::AddAssign;

struct Counter {
    value: i32,
}

impl AddAssign<i32> for Counter {
    fn add_assign(&mut self, other: i32) {
        self.value += other;
    }
}

fn main() {
    let mut c = Counter { value: 0 };
    c += 3;
    println!("{}", c.value);
}
```

1. `+=` usa `AddAssign`, no `Add`.
2. El receptor es `@mut` (`&mut self`).
3. La asignación compuesta es una sentencia, no una expresión (§8).
4. `SubAssign`, `MulAssign`, `DivAssign`, `RemAssign` siguen el mismo patrón.

### 40.3 `Neg`, `Not`, bitwise y shifts

| Operador | Trait | Receptor |
|---|---|---|
| `-x` | `Neg` | `@own` |
| `!x` | `Not` | `@own` |
| `x & y` | `BitAnd` | `@own` |
| `x \| y` | `BitOr` | `@own` |
| `x ^ y` | `BitXor` | `@own` |
| `x << y` | `Shl` | `@own` |
| `x >> y` | `Shr` | `@own` |

1. `!` sobre `Bool` usa `Not`; sobre enteros también.
2. `&`, `|`, `^` son bitwise, no lógicos; los lógicos son `and`/`or` (§12).
3. Los shifts no comprueban el desplazamiento en modo release; usa `checked_shl`
   si el valor es no confiable.
4. `Neg` puede devolver otro tipo; `Output` lo declara.

### 40.4 `Index` e `IndexMut`

```pengu
summon std::ops::Index

rune Point
    x: Int
    y: Int

ritual Point for Index[Int]
    essence Output = Int

    index = (@, i: Int) -> &Int
        if i == 0 then &@.x else &@.y

bind p = Point(x: 10, y: 20)
print(p[0])
print(p[1])
```

Rust generado:

```rust
use std::ops::Index;

struct Point {
    x: i32,
    y: i32,
}

impl Index<i32> for Point {
    type Output = i32;

    fn index(&self, i: i32) -> &i32 {
        if i == 0 { &self.x } else { &self.y }
    }
}

fn main() {
    let p = Point { x: 10, y: 20 };
    println!("{}", p[0]);
    println!("{}", p[1]);
}
```

1. `Index[Int]` significa `Index<Idx = Int>`; el índice puede ser otro tipo.
2. `Output` es el tipo del elemento; `index` devuelve `&Output`.
3. `IndexMut` se implementa aparte y usa `@mut`; `p[i] = v` requiere `IndexMut`.
4. El operador `[]` puede entrar en pánico; no hay `get` sobrecargable. Para
   acceso seguro se usa un método propio que devuelva `?&T`.
5. `Index` no puede devolver un valor por movimiento.

### 40.5 `PartialEq`, `Eq`, `PartialOrd`, `Ord`

```pengu
rune Point
    x: Int
    y: Int

ritual Point for PartialEq
    eq = (@, other: &Point) -> Bool
        @.x == other.x and @.y == other.y
```

Rust generado:

```rust
struct Point {
    x: i32,
    y: i32,
}

impl PartialEq for Point {
    fn eq(&self, other: &Point) -> bool {
        self.x == other.x && self.y == other.y
    }
}
```

1. `==`/`!=` usan `PartialEq`; `eq` recibe `&Point`.
2. Para igualdad total se implementa `Eq` (sin métodos adicionales).
3. `<`, `<=`, `>`, `>=` usan `PartialOrd`; `Ord` exige un orden total.
4. `@@derive(PartialEq, Eq, PartialOrd, Ord)` genera las implementaciones
   cuando los campos las cumplen; es la opción recomendada.
5. `NaN` hace que `Float` no implemente `Ord`; no se puede fingir un orden total.

### 40.6 `Display` y `Debug`

```pengu
summon std::fmt

rune Point
    x: Int
    y: Int

ritual Point for std::fmt::Display
    fmt = (@, f: &mut std::fmt::Formatter) -> std::fmt::Result
        f.write_str(format("(#{}, #{})", @.x, @.y))

print(Point(x: 1, y: 2))
```

Rust generado:

```rust
struct Point {
    x: i32,
    y: i32,
}

impl std::fmt::Display for Point {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        f.write_str(&format!("({}, {})", self.x, self.y))
    }
}

fn main() {
    println!("{}", Point { x: 1, y: 2 });
}
```

1. `Display` es para el usuario; `Debug` para diagnóstico. No son intercambiables.
2. `print`/`format` usan `Display`; `{:?}` usa `Debug`.
3. `fmt` recibe `&mut Formatter` y devuelve `fmt::Result`.
4. No se implementa `Display` para un tipo que no tiene una representación
   textual estable; usa `Debug` o un método `to_text`.
5. `@@derive(Debug)` es preferible para `Debug`; `Display` casi siempre es manual.

### 40.7 `Deref` y `DerefMut`

```pengu
summon std::ops::Deref

rune Wrapper
    value: Int

ritual Wrapper for Deref
    essence Target = Int

    deref = (@) -> &Int
        &@.value

bind w = Wrapper(value: 7)
print(*w)
```

Rust generado:

```rust
use std::ops::Deref;

struct Wrapper {
    value: i32,
}

impl Deref for Wrapper {
    type Target = i32;

    fn deref(&self) -> &i32 {
        &self.value
    }
}

fn main() {
    let w = Wrapper { value: 7 };
    println!("{}", *w);
}
```

1. `Deref` habilita `*x` y coerciones; no es para “heredar” métodos.
2. `DerefMut` usa `@mut` y habilita `*x = v`.
3. El `Target` debe ser un tipo detrás de una referencia.
4. El abuso de `Deref` para simular herencia se rechaza en revisión; usa
   composición o un `pact`.

### 40.8 `From` e `Into`

```pengu
rune Point
    x: Int
    y: Int

ritual Point for From[(Int, Int)]
    from = (pair: (Int, Int)) -> Point
        Point(x: pair.0, y: pair.1)

bind p: Point = (3, 4).into()
print(p.x)
print(p.y)
```

Rust generado:

```rust
struct Point {
    x: i32,
    y: i32,
}

impl From<(i32, i32)> for Point {
    fn from(pair: (i32, i32)) -> Point {
        Point {
            x: pair.0,
            y: pair.1,
        }
    }
}

fn main() {
    let p: Point = (3, 4).into();
    println!("{}", p.x);
    println!("{}", p.y);
}
```

1. `From[T]` se implementa para convertir `T` en el tipo local.
2. `Into` se obtiene gratis por el blanket impl de `std`; no se implementa a
   mano salvo casos especiales.
3. La conversión es infalible; para fallos se usa `TryFrom` (§32).
4. No hay conversiones implícitas entre tipos numéricos; `as` es explícito.
5. Coherencia: no puedes implementar `From` para un tipo externo y un tipo
   externo; al menos uno debe ser local.

### 40.9 Qué no se puede sobrecargar

- `=`, `==`, `!=`, `&&`, `||`, `..`, `?`, `as`, `.`, `@` y `=>` no son traits.
- No se puede cambiar la precedencia ni la asociatividad.
- No se pueden crear operadores nuevos (`**`, `++`, `===`).
- `print`/`format` no son operadores; usan `Display`.
- `Drop` se implementa con `ritual Tipo for Drop`, pero no es un operador.
- `Index` no reemplaza a `get`; el acceso seguro sigue siendo un método.

### 40.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4101` | `essence Output` faltante | declararlo en el `ritual` |
| `PGS-E4102` | receptor incorrecto | `@own` para operadores que consumen, `@mut` para asignación |
| `PGS-E4103` | `Index` devuelve un valor | devolver `&Output` |
| `PGS-E4104` | `PartialOrd` sin `PartialEq` | implementar ambos o derivar |
| `PGS-E4105` | `Display` para un tipo sin representación estable | usar `Debug` o un método |
| `PGS-E4106` | `From` con dos tipos externos | newtype local |
| `PGS-W4101` | `Deref` usado para simular herencia | composición o `pact` |

### 40.11 Criterios de aceptación

- [x] Operadores aritméticos y de asignación están definidos.
- [x] `Index`, comparación, `Display`, `Deref` y `From` tienen ejemplo.
- [x] Qué no se puede sobrecargar está claro.
- [x] Coherencia y precedencia se remiten a §11/§31.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="part-6"></a>
## Parte VI — Organización y metaprogramación

<a id="sec-41-modulos"></a>
## 41. Módulos (`scroll`)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 6 |
| Rust | `mod`, `use`, `crate`, `super` |
| Palabras mágicas | `scroll`, `summon`, `crate`, `super` |
| Depende de | §3, §7, §42 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec41_modules.pengu` |

Un **módulo** agrupa items y controla su visibilidad. En PenguScript se declara
con `scroll`. Un archivo `.pengu` es un módulo; la raíz del programa es
`main.pengu` (binario) o `lib.pengu` (librería). `scroll` inline permite agrupar
sin archivo; `scroll` sin cuerpo carga un archivo hermano.

### 41.1 Raíces y archivos

| Archivo | Crate | Rust |
|---|---|---|
| `main.pengu` | binario | `src/main.rs` |
| `lib.pengu` | librería | `src/lib.rs` |
| `geometry.pengu` | módulo `geometry` | `src/geometry.rs` |
| `geometry/scroll.pengu` | módulo `geometry` | `src/geometry/mod.rs` |

Reglas:

1. Solo hay una raíz por crate: `main.pengu` o `lib.pengu`.
2. Un `scroll foo` sin cuerpo busca `foo.pengu` o `foo/scroll.pengu`, en ese
   orden. Si ambos existen, error `PGS-E4112`.
3. Un `scroll foo` con cuerpo indentado es inline y no carga archivo.
4. El archivo se resuelve relativo al directorio del módulo padre.
5. `@@path("ruta.pengu")` sobre el `scroll` sustituye la resolución automática.
6. No se permite `mod.rs`; el nombre `scroll.pengu` es el equivalente moderno.

### 41.2 `scroll` inline

```pengu
scroll geometry
    unveil rune Point
        unveil x: Int
        unveil y: Int

    unveil norm = (p: &Point) -> Float
        ((p.x * p.x + p.y * p.y) as Float).sqrt()

bind p = geometry::Point(x: 3, y: 4)
print(geometry::norm(&p))
```

Rust generado:

```rust
mod geometry {
    pub struct Point {
        pub x: i32,
        pub y: i32,
    }

    pub fn norm(p: &Point) -> f64 {
        (((p.x * p.x + p.y * p.y) as f64).sqrt())
    }
}

fn main() {
    let p = geometry::Point { x: 3, y: 4 };
    println!("{}", geometry::norm(&p));
}
```

1. El cuerpo del `scroll` va indentado un nivel.
2. Los items internos se acceden con `geometry::Point` desde el padre.
3. `scroll` puede anidarse; el hijo se declara dentro del padre.
4. `unveil` decide qué sale del módulo (§42); sin él, el item es privado.
5. Un `scroll` inline no genera archivo separado; el codegen lo emite en el
   mismo `.rs`.

### 41.3 `scroll` desde archivo

`main.pengu`:

```pengu
scroll geometry
unveil summon crate::geometry::Point

bind p = Point(x: 3, y: 4)
print(p.x)
```

`geometry.pengu`:

```pengu
unveil rune Point
    unveil x: Int
    unveil y: Int
```

Rust generado (en el ejemplo de un solo archivo, el módulo se inlinea para
poder compilarlo aislado):

```rust
mod geometry {
    pub struct Point {
        pub x: i32,
        pub y: i32,
    }
}

use crate::geometry::Point;

fn main() {
    let p = Point { x: 3, y: 4 };
    println!("{}", p.x);
}
```

1. `scroll geometry` sin cuerpo es una declaración de módulo externo.
2. `geometry.pengu` se compila a `src/geometry.rs`; el `mod geometry;` de Rust
   queda en la raíz.
3. `unveil summon` reexporta el tipo desde la raíz del crate.
4. `summon crate::geometry::Point` también funciona sin reexportar.
5. La resolución es determinista: archivo hermano antes que carpeta.

### 41.4 `summon` y paths

```pengu
scroll geometry
    unveil rune Point
        unveil x: Int
        unveil y: Int

summon crate::geometry::Point
summon crate::geometry::Point as P

bind a = Point(x: 1, y: 2)
bind b = P(x: 3, y: 4)
print(a.x + b.x)
```

Rust generado:

```rust
mod geometry {
    pub struct Point {
        pub x: i32,
        pub y: i32,
    }
}

use crate::geometry::Point;
use crate::geometry::Point as P;

fn main() {
    let a = Point { x: 1, y: 2 };
    let b = P { x: 3, y: 4 };
    println!("{}", a.x + b.x);
}
```

1. `summon path` importa un item o un módulo.
2. `summon path as Alias` renombra.
3. `summon path::*` importa el glob; se desaconseja en APIs públicas.
4. `summon` debe ir antes de los items que lo usan, o en el prelude del módulo.
5. `crate::` empieza en la raíz del crate; `super::` sube un módulo.
6. No se escribe `self::`; dentro del módulo se usa el nombre sin prefijo.
7. Un path absoluto de dependencia empieza por el nombre del crate:
   `summon serde::Serialize`.

### 41.5 Reexportar

```pengu
scroll geometry
    unveil rune Point
        unveil x: Int
        unveil y: Int

unveil summon crate::geometry::Point

bind p = Point(x: 1, y: 2)
print(p.x)
```

Rust generado:

```rust
mod geometry {
    pub struct Point {
        pub x: i32,
        pub y: i32,
    }
}

pub use crate::geometry::Point;

fn main() {
    let p = Point { x: 1, y: 2 };
    println!("{}", p.x);
}
```

1. `unveil summon` es un `pub use`: reexporta con la visibilidad indicada.
2. Se usa para fachadas de crate (`prelude`, `api`) y para no exponer la ruta
   interna.
3. Un reexport no copia el item; cambia su camino público.
4. `unveil(tome) summon` reexporta solo dentro del crate.

### 41.6 Árbol de módulos

```text
src/
  main.pengu
  geometry.pengu
  shapes/
    scroll.pengu
    circle.pengu
```

`main.pengu`:

```pengu
scroll geometry
scroll shapes
```

`shapes/scroll.pengu`:

```pengu
scroll circle
unveil summon crate::shapes::circle::Circle
```

`shapes/circle.pengu`:

```pengu
unveil rune Circle
    unveil radius: Float
```

El árbol de Rust correspondiente:

```text
src/
  main.rs
  geometry.rs
  shapes/
    mod.rs
    circle.rs
```

1. `shapes/scroll.pengu` es el `mod.rs` de `shapes`.
2. `circle.pengu` es el hijo `shapes::circle`.
3. Los `scroll` de `main.pengu` declaran los hijos de la raíz.
4. El codegen conserva el árbol; no aplana módulos.

### 41.7 Prelude y resolución

- El prelude del crate contiene `Option`, `Result`, `String`, `Vec`, `Box`,
  `print`, `format`, `panic`, `assert` y los traits de operadores.
- Un `summon` en la raíz no se hereda automáticamente a los hijos; cada módulo
  importa lo que usa.
- Un nombre local gana al prelude; un `summon` explícito gana al prelude.
- Dos `summon` con el mismo nombre sin alias son ambiguos (`PGS-E4113`).
- Los módulos no se importan implícitamente; hay que declararlos con `scroll`.
- El orden de declaración no importa para la resolución; sí para la lectura.

### 41.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4110` | `scroll` sin archivo y sin cuerpo | crear el archivo o el cuerpo |
| `PGS-E4111` | dos raíces (`main.pengu` y `lib.pengu`) | elegir una |
| `PGS-E4112` | `foo.pengu` y `foo/scroll.pengu` a la vez | borrar uno o usar `@@path` |
| `PGS-E4113` | dos `summon` con el mismo nombre | aliasar uno |
| `PGS-E4114` | `scroll` dentro de una función | moverlo al nivel de módulo |
| `PGS-E4115` | path `self::` | usar `crate::`/`super::` o el nombre directo |
| `PGS-W4110` | glob import en API pública | importar nombres explícitos |

### 41.9 Criterios de aceptación

- [x] La resolución de archivos es determinista.
- [x] `scroll` inline y externo están definidos.
- [x] `summon`, alias, glob y reexport están cubiertos.
- [x] El árbol de módulos tiene ejemplo.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-42-visibilidad"></a>
## 42. Visibilidad (`unveil`)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 6 |
| Rust | `pub`, `pub(crate)`, `pub(super)`, `pub(in path)` |
| Palabras mágicas | `unveil`, `tome`, `scroll` |
| Depende de | §41 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec42_visibility.pengu` |

En PenguScript **todo es privado por defecto**. `unveil` abre un item, un campo
o un módulo. No hay `public`/`private`; la palabra es parte del léxico mágico y
se traduce directamente a las formas de `pub` de Rust.

### 42.1 Tabla de visibilidad

| PenguScript | Rust | Visible desde |
|---|---|---|
| sin modificador | privado | módulo actual y descendientes |
| `unveil` | `pub` | cualquier crate que dependa |
| `unveil(tome)` | `pub(crate)` | cualquier módulo del crate |
| `unveil(scroll)` | `pub(super)` | módulo padre |
| `unveil(in crate::a::b)` | `pub(in crate::a::b)` | ese módulo y descendientes |
| `unveil summon` | `pub use` | según el `unveil` |

Reglas:

1. `unveil` se escribe antes de la palabra del item:
   `unveil rune`, `unveil enchanting`, `unveil pact`, `unveil ritual`,
   `unveil sigil`, `unveil relic`, `unveil scroll`, `unveil incantation`.
2. En campos: `unveil x: Int`; el campo pasa a `pub x`.
3. En variantes de enum no se escribe `unveil`: si el enum es público, sus
   variantes son públicas, como en Rust.
4. En items de trait no se escribe `unveil`: la visibilidad la decide el trait.
5. En campos de struct de tupla no se escribe `unveil`; son privados por
   decisión (§28), y se accede con métodos o con un constructor.
6. `unveil` no se hereda: un campo público dentro de un struct privado no hace
   público el struct.
7. La visibilidad se comprueba en el punto de uso; un item privado usado desde
   otro módulo produce `PGS-E4211`.

### 42.2 Ejemplo completo

```pengu
scroll inner
    unveil rune Public
        unveil value: Int
        hidden: Int

    rune Private
        value: Int

    unveil new = (value: Int) -> Public
        Public(value: value, hidden: 0)

    unveil(scroll) show = (p: &Public) -> Int
        p.value

unveil(tome) crate_only = () -> Int
    1

bind p = inner::new(7)
print(inner::show(&p))
print(crate_only())
```

Rust generado:

```rust
mod inner {
    pub struct Public {
        pub value: i32,
        hidden: i32,
    }

    struct Private {
        value: i32,
    }

    pub fn new(value: i32) -> Public {
        Public { value, hidden: 0 }
    }

    pub(super) fn show(p: &Public) -> i32 {
        p.value
    }
}

pub(crate) fn crate_only() -> i32 {
    1
}

fn main() {
    let p = inner::new(7);
    println!("{}", inner::show(&p));
    println!("{}", crate_only());
}
```

1. `Public` es público, pero `hidden` no; el constructor `new` es la única forma
   de crear el valor desde fuera.
2. `Private` no sale de `inner`.
3. `show` es `pub(super)`: visible en la raíz, no fuera del crate.
4. `crate_only` es `pub(crate)`: visible desde cualquier módulo del crate.
5. `main` puede llamar a `show` porque está en el padre de `inner`.

### 42.3 Campos y variantes

```pengu
unveil rune Config
    unveil name: String
    unveil retries: Int

unveil enchanting Status
    Active
    Failed(Int)
```

Rust generado:

```rust
pub struct Config {
    pub name: String,
    pub retries: i32,
}

pub enum Status {
    Active,
    Failed(i32),
}
```

1. Los campos públicos se pueden leer y escribir desde fuera; los privados solo
   desde el módulo y sus descendientes.
2. Las variantes de un enum público son públicas; no se puede hacer un enum
   público con variantes privadas.
3. Los campos de una variante de struct (`Failed { code: Int }`) siguen las
   reglas de campos de struct.
4. `unveil` en un campo de enum es error (`PGS-E4212`).
5. Un enum privado con variantes públicas no existe: la visibilidad del enum
   manda.

### 42.4 `unveil` en módulos y reexports

```pengu
unveil scroll api
    unveil rune Request
        unveil id: Int

unveil summon crate::api::Request
```

Rust generado:

```rust
pub mod api {
    pub struct Request {
        pub id: i32,
    }
}

pub use crate::api::Request;
```

1. `unveil scroll` hace público el módulo; sin él, sus items públicos no son
   alcanzables desde fuera.
2. Un módulo público puede contener items privados.
3. `unveil summon` reexporta; es la forma recomendada de construir una fachada.
4. `unveil(tome) scroll` limita el módulo al crate.
5. La ruta pública no tiene por qué coincidir con la ruta interna.

### 42.5 `pub(in path)`

```pengu
scroll outer
    unveil scroll inner
        unveil(in crate::outer) helper = () -> Int
            42
```

Rust generado:

```rust
mod outer {
    pub mod inner {
        pub(in crate::outer) fn helper() -> i32 {
            42
        }
    }
}
```

1. `unveil(in crate::a::b)` solo es visible dentro de ese módulo y sus
   descendientes.
2. El path debe ser un ancestro del item; si no, error (`PGS-E4213`).
3. Es útil para APIs internas de un subsistema.
4. No se puede usar `unveil(in super::super)`; se escribe la ruta completa desde
   `crate`.
5. En el crate raíz, `unveil(in crate)` equivale a `pub(crate)`.

### 42.6 Privacidad y fugas de tipos

- Un item público no puede exponer un tipo privado en su firma; Rust lo detecta
  como `private_interfaces` (`PGS-E4214`).
- Un campo público de un tipo privado no es alcanzable; el compilador lo
  permite, pero el codegen lo marca como advertencia.
- Un `unveil summon` de un item privado es error.
- Un trait público con un supertrait privado es un trait sellado; se permite con
  advertencia (`PGS-W4210`).
- La visibilidad no cambia el layout ni el código; solo el acceso.

### 42.7 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4210` | `unveil` sobre un item que no lo admite | quitar o mover al item |
| `PGS-E4211` | item privado usado desde otro módulo | `unveil` o reexportar |
| `PGS-E4212` | `unveil` en campo de variante de enum | la variante hereda del enum |
| `PGS-E4213` | `pub(in path)` que no es ancestro | usar un ancestro real |
| `PGS-E4214` | tipo privado en API pública | hacer público el tipo o privada la API |
| `PGS-W4210` | supertrait privado en trait público | documentar el sellado |
| `PGS-W4211` | `unveil` redundante en el crate raíz | simplificar |

### 42.8 Criterios de aceptación

- [x] La tabla cubre todas las formas de `pub`.
- [x] Campos, variantes, módulos y reexports están definidos.
- [x] `pub(in path)` y sus restricciones están explicados.
- [x] Privacidad por defecto y fugas de tipos están cubiertas.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-43-crates"></a>
## 43. Crates, packages y workspaces (`tome`)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 6 |
| Rust | Cargo, `Cargo.toml`, workspaces, features |
| Palabras mágicas | `tome`, `Tome.toml` |
| Depende de | §3, §41, §47 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec43_tome.pengu` |

Un **tome** es la unidad de distribución de PenguScript: un directorio con
`Tome.toml`, código fuente y, opcionalmente, tests, ejemplos y benchmarks. Se
corresponde con un **package** de Cargo; el crate compilado es su biblioteca o
binario. Un **workspace** agrupa varios tomes.

### 43.1 Estructura de un tome

```text
pengu-demo/
  Tome.toml
  Tome.lock
  main.pengu
  lib.pengu
  build.pengu
  tests/
  examples/
  benches/
```

Reglas:

1. `Tome.toml` es obligatorio; sin él no es un tome.
2. La raíz del crate es `main.pengu` (binario), `lib.pengu` (librería) o ambos.
3. `Tome.lock` lo genera el compilador; no se edita a mano.
4. `build.pengu` es el build script (§47).
5. `tests/`, `examples/` y `benches/` siguen la convención de Cargo.
6. Un tome puede tener varias metas (`[[bin]]`, `[[test]]`, etc.).

### 43.2 `Tome.toml`

```toml
[tome]
name = "pengu-demo"
version = "0.1.0"
pengu = "1.0"
edition = "2024"
rust-version = "1.85"
description = "Demo de PenguScript"
license = "MIT"

[dependencies]
serde = { version = "1.0", features = ["derive"], optional = true }

[dev-dependencies]
pretty_assertions = "1"

[build-dependencies]
cc = "1"

[features]
default = ["std"]
std = []
serde = ["dep:serde"]

[lib]
path = "lib.pengu"

[[bin]]
name = "demo"
path = "main.pengu"

[[test]]
name = "integration"
path = "tests/integration.pengu"

[[bench]]
name = "throughput"
path = "benches/throughput.pengu"
harness = false

[profile.release]
lto = true
codegen-units = 1

[workspace]
members = ["crates/*"]
resolver = "2"

[cargo]
# Claves de Cargo sin equivalente PenguScript; se copian tal cual.
```

1. `[tome]` es la sección obligatoria; `name`, `version`, `pengu`, `edition` y
   `rust-version` son obligatorios.
2. `pengu` fija la versión del compilador; el compilador rechaza una versión
   incompatible (`PGS-E4311`).
3. `edition` es la edición de Rust generada; el valor inicial es `"2024"`.
4. `rust-version` es el MSRV; no puede ser menor que `1.85`.
5. Las tablas de dependencias son las de Cargo, con versiones semver.
6. `[features]` es aditivo; `dep:serde` activa la dependencia opcional.
7. `path` de las metas apunta a `.pengu`, no a `.rs`.
8. `[workspace]` convierte el tome en raíz de workspace.
9. `[cargo]` es el passthrough auditado; no puede sobrescribir claves
   protegidas (`package.name`, `package.version`, `lib.path`, `bin.path`).

### 43.3 De `Tome.toml` a `Cargo.toml`

El codegen produce un `Cargo.toml` en `target/pengu/`:

```toml
[package]
name = "pengu-demo"
version = "0.1.0"
edition = "2024"
rust-version = "1.85"
description = "Demo de PenguScript"
license = "MIT"

[lib]
path = "src/lib.rs"

[[bin]]
name = "demo"
path = "src/main.rs"

[features]
default = ["std"]
std = []
serde = ["dep:serde"]

[dependencies]
serde = { version = "1.0", features = ["derive"], optional = true }
```

1. Los `path` `.pengu` se reescriben a `src/*.rs`.
2. `[tome]` se convierte en `[package]`.
3. Las dependencias, features, perfiles y workspace se copian.
4. `Tome.lock` se copia a `Cargo.lock`; el lockfile es la fuente de verdad de
   las versiones resueltas.
5. El crate generado no se publica; se publica el tome y su código fuente.
6. `cargo` puede invocarse sobre `target/pengu/` para diagnóstico, pero el
   flujo normal es `pengu build`.

### 43.4 Dependencias

```toml
[dependencies]
serde = { version = "1.0", features = ["derive"] }
rand = "0.8"

[target.'cfg(target_os = "linux")'.dependencies]
libc = "0.2"

[target.'cfg(windows)'.dependencies]
windows-sys = { version = "0.59", features = ["Win32_Foundation"] }
```

1. Una dependencia normal se compila para el target.
2. Una dependencia de target solo se incluye si el `cfg` se cumple.
3. `optional = true` se activa con una feature; no se importa si no está activa.
4. `[dev-dependencies]` solo para tests, ejemplos y benches.
5. `[build-dependencies]` solo para `build.pengu`.
6. Las dependencias se resuelven con semver; `Tome.lock` fija las versiones.
7. Un path dependency usa `{ path = "../otro" }`; sigue siendo un tome.

### 43.5 Workspaces

```toml
[workspace]
members = ["crates/core", "crates/cli", "crates/macros"]
resolver = "2"

[workspace.dependencies]
serde = { version = "1.0", features = ["derive"] }
```

1. Un workspace comparte `Tome.lock` y `target/`.
2. `[workspace.dependencies]` centraliza versiones; un miembro las hereda con
   `serde.workspace = true`.
3. `resolver = "2"` es el recomendado para editiones modernas.
4. Un miembro puede ser binario, librería o ambos.
5. Los paths de workspace no pueden salir del directorio raíz sin declararlo.
6. `pengu build -p core` construye un miembro; `pengu build --workspace` todos.

### 43.6 Versiones, lockfile y registro

- La versión del tome sigue semver: `MAJOR.MINOR.PATCH`.
- `0.x` se considera inestable; un cambio incompatible sube `MINOR`.
- `Tome.lock` se versiona para binarios y se ignora para librerías publicadas.
- El registro por defecto es crates.io; `[registries]` permite registros
  alternativos.
- Un `pengu publish` empaqueta el fuente `.pengu`, no el Rust generado.
- El checksum del lockfile detecta cambios de dependencias.
- No se permite un `path` dependency en un paquete publicado; se usa una
  versión del registro.

### 43.7 Ejemplo mínimo

`Tome.toml`:

```toml
[tome]
name = "hello"
version = "0.1.0"
pengu = "1.0"
edition = "2024"
rust-version = "1.85"
```

`main.pengu`:

```pengu
grimoire
    print("hello from a tome")
```

Rust generado (`src/main.rs`):

```rust
fn main() {
    println!("hello from a tome");
}
```

### 43.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4310` | falta `Tome.toml` | crearlo en la raíz |
| `PGS-E4311` | versión de `pengu` incompatible | actualizar el compilador o el campo |
| `PGS-E4312` | `rust-version` menor que 1.85 | subir el MSRV |
| `PGS-E4313` | `path` de meta no es `.pengu` | corregir la ruta |
| `PGS-E4314` | clave protegida en `[cargo]` | quitarla del passthrough |
| `PGS-E4315` | workspace con miembro fuera de la raíz | declarar el path o moverlo |
| `PGS-W4310` | lockfile desactualizado | `pengu update` |

### 43.9 Criterios de aceptación

- [x] `Tome.toml` mapea a `Cargo.toml`.
- [x] Dependencias, features, targets y workspace están cubiertos.
- [x] Semver, lockfile y registro están definidos.
- [x] El ejemplo mínimo tiene Rust generado.
- [x] El ejemplo Rust compila.

[↑ Volver al índice](#indice)

<a id="sec-44-atributos"></a>
## 44. Atributos (`@@`)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 6 |
| Rust | `#[...]`, `#![...]` |
| Palabras mágicas | `@@`, `@@!` |
| Depende de | §28, §35, §45, §46 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec44_attributes.pengu` |

Un **atributo** es metadato de compilación. En PenguScript se escribe con `@@`
para no confundirlo con `@` (receptor). Los atributos internos, que aplican al
item que los contiene, usan `@@!`.

### 44.1 Sintaxis

```pengu
@@derive(Debug, Clone, PartialEq)
rune Point
    x: Int
    y: Int

@@inline
add = (a: Int, b: Int) -> Int
    a + b

@@must_use
important = () -> Int
    42
```

Rust generado:

```rust
#[derive(Debug, Clone, PartialEq)]
struct Point {
    x: i32,
    y: i32,
}

#[inline]
fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[must_use]
fn important() -> i32 {
    42
}
```

Reglas:

1. `@@nombre` sin argumentos; `@@nombre(args)` con argumentos.
2. Varios atributos van en líneas consecutivas antes del item.
3. El orden se conserva en el Rust generado.
4. `@@!` es un atributo interno y debe ir al inicio del archivo o del bloque
   `scroll`, antes de cualquier item.
5. Los argumentos son literales, identificadores o listas; no expresiones
   arbitrarias.
6. Un atributo desconocido es error (`PGS-E4410`), salvo que venga de una proc
   macro importada.
7. Los atributos no cambian la semántica del lenguaje; solo el codegen o el
   compilador de Rust.

### 44.2 Atributos internos

```pengu
@@!allow(dead_code)
@@!doc("Crate de ejemplo")

print("pengu")
```

Rust generado:

```rust
#![allow(dead_code)]
#![doc = "Crate de ejemplo"]

fn main() {
    println!("pengu");
}
```

1. `@@!` solo es válido al inicio de la raíz o de un `scroll`.
2. Un atributo interno después de un item es error (`PGS-E4411`).
3. `@@!allow`/`deny`/`warn` afectan a todo el módulo.
4. `@@!doc` documenta el crate o módulo.
5. `@@!no_std` convierte el crate en `no_std`; se detalla en §55.

### 44.3 Tabla de atributos

| PenguScript | Rust | Efecto |
|---|---|---|
| `@@derive(T1, T2)` | `#[derive(T1, T2)]` | genera impls |
| `@@repr(C)` / `@@repr(u8)` | `#[repr(...)]` | layout/discriminante |
| `@@cfg(cond)` | `#[cfg(cond)]` | compilación condicional |
| `@@cfg_attr(cond, attr)` | `#[cfg_attr(...)]` | atributo condicional |
| `@@test` | `#[test]` | test unitario |
| `@@bench` | `#[bench]` | benchmark (nightly) |
| `@@ignore` | `#[ignore]` | test ignorado |
| `@@should_panic` | `#[should_panic]` | test que debe fallar |
| `@@inline` / `@@inline(always)` | `#[inline]` | inline hint |
| `@@cold` | `#[cold]` | ruta fría |
| `@@track_caller` | `#[track_caller]` | ubicación del llamador |
| `@@must_use` | `#[must_use]` | valor que no se debe ignorar |
| `@@deprecated("msg")` | `#[deprecated(note = "msg")]` | aviso de uso |
| `@@non_exhaustive` | `#[non_exhaustive]` | obliga a `_` fuera del crate |
| `@@doc("texto")` | `#[doc = "texto"]` | documentación |
| `@@allow(lint)` | `#[allow(lint)]` | permite lint |
| `@@deny(lint)` | `#[deny(lint)]` | prohíbe lint |
| `@@warn(lint)` | `#[warn(lint)]` | avisa lint |
| `@@no_mangle` | `#[unsafe(no_mangle)]` | símbolo sin mangling |
| `@@link(...)` | `#[link(...)]` | biblioteca nativa |
| `@@link_name("x")` | `#[link_name = "x"]` | nombre de símbolo |
| `@@link_section("x")` | `#[link_section = "x"]` | sección del binario |
| `@@export_name("x")` | `#[export_name = "x"]` | símbolo exportado |
| `@@used` | `#[used]` | conservar símbolo |
| `@@path("ruta")` | `#[path = "ruta"]` | ruta de módulo |
| `@@macro_use` | `#[macro_use]` | importar macros |
| `@@panic_handler` | `#[panic_handler]` | handler de pánico |
| `@@global_allocator` | `#[global_allocator]` | allocator global |
| `@@no_std` | `#![no_std]` | crate sin std |
| `@@feature(...)` | `#![feature(...)]` | feature nightly |
| `@@target_feature(...)` | `#[target_feature(...)]` | instrucciones |
| `@@non_exhaustive` | `#[non_exhaustive]` | variantes futuras |

1. Los atributos de nightly (`@@bench`, `@@feature`) requieren un toolchain
   nightly; el compilador lo comprueba.
2. `@@no_mangle`, `@@link_section`, `@@export_name` y `@@target_feature` son
   `unsafe` en Rust 2024; el codegen emite `#[unsafe(...)]`.
3. `@@repr` solo se aplica a structs/enums; en otro item es error.
4. `@@derive` solo se aplica a structs/enums; en una función es error.
5. `@@cfg` se puede aplicar a cualquier item.

### 44.4 `@@cfg` y `@@cfg_attr`

```pengu
@@cfg(debug_assertions)
debug_only = () -> Int
    1

@@cfg_attr(debug_assertions, derive(Debug))
rune Config
    name: String
```

Rust generado:

```rust
#[cfg(debug_assertions)]
fn debug_only() -> i32 {
    1
}

#[cfg_attr(debug_assertions, derive(Debug))]
struct Config {
    name: String,
}
```

1. `@@cfg` elimina el item si la condición es falsa; no es un `if` de runtime.
2. `@@cfg_attr` aplica el atributo solo si la condición se cumple; en el ejemplo,
   solo en builds con `debug_assertions`.
3. Las condiciones usan la sintaxis de `cfg` de Rust: `feature = "x"`,
   `target_os = "linux"`, `debug_assertions`, `all(...)`, `any(...)`, `not(...)`.
4. Una feature no declarada en `Tome.toml` produce `PGS-W4410`.
5. `@@cfg` no puede depender de valores de runtime.

### 44.5 Atributos de documentación

```pengu
@@doc("Punto en el plano.")
@@derive(Debug, Clone, Copy)
rune Point
    @@doc("Coordenada horizontal.")
    x: Int
    y: Int
```

Rust generado:

```rust
#[doc = "Punto en el plano."]
#[derive(Debug, Clone, Copy)]
struct Point {
    #[doc = "Coordenada horizontal."]
    x: i32,
    y: i32,
}
```

1. `---` es el comentario de documentación idiomático; `@@doc("...")` es la
   forma explícita cuando se genera desde una herramienta.
2. `@@doc` acepta un string; no acepta Markdown como bloque.
3. `@@doc(hidden)` oculta el item de la documentación.
4. La documentación de un campo debe ir antes del campo.
5. `@@doc` en un `scroll` documenta el módulo.

### 44.6 Atributos de proc macro

```pengu
summon serde::Serialize
summon serde::Deserialize

@@derive(Serialize, Deserialize)]
rune User
    name: String
```

1. Un atributo de proc macro solo existe si la crate que lo define está en
   `Tome.toml` y el nombre está en scope.
2. PenguScript no define proc macros; las consume (§45).
3. `@@derive` con un nombre no importado es error (`PGS-E4412`).
4. Un atributo de función (`@@my_attr(...)`) se aplica al item siguiente.
5. El orden importa: `@@derive` antes de `@@repr` es lo habitual, pero el
   codegen conserva el orden escrito.

### 44.7 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4410` | atributo desconocido | importar la proc macro o corregir el nombre |
| `PGS-E4411` | `@@!` después de un item | moverlo al inicio |
| `PGS-E4412` | derive no importado | `summon` la crate |
| `PGS-E4413` | `@@repr` en un item no válido | aplicarlo a struct/enum |
| `PGS-E4414` | `@@derive` en una función | quitarlo |
| `PGS-W4410` | `cfg` con feature no declarada | declararla en `Tome.toml` |
| `PGS-W4411` | atributo redundante | simplificar |

### 44.8 Criterios de aceptación

- [x] `@@` y `@@!` tienen sintaxis y posición definidas.
- [x] La tabla cubre los atributos built-in.
- [x] `cfg`, `cfg_attr` y documentación tienen ejemplo.
- [x] La relación con proc macros está explícita.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-45-macros"></a>
## 45. Macros (`incantation`)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 6 |
| Rust | `macro_rules!`, `#[macro_export]`, proc macros |
| Palabras mágicas | `incantation`, `!` |
| Depende de | §3, §44, §53 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec45_macros.pengu` |

Una **incantación** es una macro. PenguScript soporta dos clases:

1. **Macros declarativas** definidas en PenguScript con `incantation`; generan
   `macro_rules!`.
2. **Macros procedurales** definidas en Rust; se consumen desde una crate y no
   se pueden definir en PenguScript.

Las macros son la única construcción que opera sobre tokens sin pasar por el
sistema de tipos. Por eso se usan cuando una función, un genérico o un `pact` no
alcanzan; no son la herramienta por defecto.

### 45.1 Definición declarativa

```pengu
incantation square
    ($x:expr) => {
        $x * $x
    }
```

Rust generado:

```rust
#[macro_export]
macro_rules! square {
    ($x:expr) => {
        $x * $x
    };
}
```

Reglas:

1. `incantation nombre` abre una definición; el cuerpo va indentado.
2. El cuerpo es una **región de tokens crudos**: no se aplican las reglas de
   expresión de PenguScript. `$`, `=>`, `{`, `}`, `;` y `[]` son tokens de la
   macro, no sintaxis del lenguaje.
3. La región termina al volver a la indentación de `incantation` o al final del
   archivo/módulo. Los delimitadores deben estar balanceados.
4. Cada brazo tiene la forma `(patrón) => { expansión }` o
   `(patrón) => expresión`. El `;` entre brazos es opcional.
5. El nombre debe ser un identificador único en el espacio de macros.
6. Sin `unveil`, la macro es local al módulo.
7. `unveil incantation nombre` genera `#[macro_export]` y la hace visible en la
   raíz de la crate.
8. No se permiten parámetros de tipo, `where` ni sobrecarga por tipos.

### 45.2 Invocación

```pengu
bind n = square!(5)
print(n)
```

Rust generado:

```rust
macro_rules! square {
    ($x:expr) => {
        $x * $x
    };
}

fn main() {
    let n = square!(5);
    println!("{}", n);
}
```

La invocación es `nombre!` seguido de un token tree:

| Forma | Ejemplo | Uso |
|---|---|---|
| paréntesis | `assert!(x > 0)` | expresión/statement |
| corchetes | `vec_of![1, 2, 3]` | listas |
| llaves | `make_item! { ... }` | items/bloques |

1. Después de `!` el contenido es un token tree crudo, como en la definición.
2. El token tree se emite tal cual; no se type-checkea en PenguScript.
3. La expansión se compila con Rust y sus errores se remapean (§3).
4. Una invocación sin macro visible es `PGS-E4505`.
5. Una macro de expresión se puede usar en cualquier expresión; una de item,
   solo en posición de item.

### 45.3 Repeticiones y metavariables

```pengu
incantation sum_all
    ($($x:expr),* $(,)?) => {
        0 $(+ $x)*
    }
```

Rust generado:

```rust
#[macro_export]
macro_rules! sum_all {
    ($($x:expr),* $(,)?) => {
        0 $(+ $x)*
    };
}
```

Metavariables habituales:

| Fragmento | Acepta |
|---|---|
| `$x:expr` | una expresión |
| `$x:ty` | un tipo |
| `$x:ident` | un identificador |
| `$x:pat` | un patrón |
| `$x:stmt` | una sentencia |
| `$x:item` | un item |
| `$x:block` | un bloque |
| `$x:literal` | un literal |
| `$x:tt` | un token tree |
| `$x:vis` | una visibilidad |
| `$x:lifetime` | un lifetime |

1. `$x` es una metavariable; `$($x),*` es una repetición.
2. El separador puede ser `,`, `;` o ninguno.
3. `$(,)?` acepta una coma final opcional.
4. Una metavariable debe repetirse el mismo número de veces en la expansión.
5. `$crate` se refiere a la crate que define la macro; es la forma portable de
   nombrar items internos.

### 45.4 Ejemplo: `vec_of`

```pengu
incantation vec_of
    ($($x:expr),* $(,)?) => {
        vec![$($x),*]
    }

grimoire
    bind xs = vec_of![1, 2, 3]
    print(xs.len())
```

Rust generado:

```rust
#[macro_export]
macro_rules! vec_of {
    ($($x:expr),* $(,)?) => {
        vec![$($x),*]
    };
}

fn main() {
    let xs = vec_of![1, 2, 3];
    println!("{}", xs.len());
}
```

### 45.5 Higiene y `$crate`

```pengu
incantation answer
    () => {
        $crate::ANSWER
    }

unveil sigil ANSWER: Int = 42
```

Rust generado:

```rust
#[macro_export]
macro_rules! answer {
    () => {
        $crate::ANSWER
    };
}

pub const ANSWER: i32 = 42;
```

1. `macro_rules!` tiene higiene sintáctica: los identificadores introducidos por
   la macro no capturan los del sitio de llamada.
2. `$crate` evita depender de la ruta del crate que define la macro.
3. La higiene no es total: los identificadores pasados como argumentos sí
   interactúan con la expansión.
4. Una macro exportada debe usar `$crate` para sus items internos.
5. No se puede simular una macro procedural con `incantation`; si se necesita
   inspeccionar tokens o generar items complejos, se escribe en Rust (§53).

### 45.6 Macros procedurales

```pengu
summon serde::Serialize
summon serde::Deserialize

@@derive(Serialize, Deserialize)
rune User
    name: String
```

1. PenguScript **no define** macros procedurales; solo las consume.
2. Una proc macro de derive se usa en `@@derive(...)`.
3. Una proc macro de atributo se usa como `@@nombre(...)`.
4. Una proc macro de función se invoca como `nombre!(...)`.
5. La crate que la define debe estar en `Tome.toml` y el nombre en scope.
6. Los errores de una proc macro se reportan en la invocación, con el span
   remapeado si la macro lo permite.

### 45.7 Cuándo usar macros

| Necesidad | Solución |
|---|---|
| calcular un valor | función |
| operar sobre varios tipos | genéricos + `pact` |
| construir un tipo compuesto | `rune`/`enchanting` |
| repetir código con tipos distintos | genéricos o macro |
| sintaxis nueva | macro declarativa |
| generar items desde atributos | proc macro (Rust) |
| inspeccionar tokens | proc macro (Rust) |
| logging con formato | macro (`print`/`format` ya lo son) |

1. Una macro no tiene firmas tipadas; el error aparece en la expansión.
2. Una macro no se puede depurar con el depurador de PenguScript.
3. Una macro puede aumentar el tiempo de compilación y el tamaño del binario.
4. Si una función o un genérico resuelven el problema, se prefieren.
5. Una macro declarativa bien documentada debe incluir ejemplos de uso y de
   error.

### 45.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4501` | nombre de macro inválido | usar un identificador |
| `PGS-E4502` | brazo mal formado | revisar `patrón => expansión` |
| `PGS-E4503` | delimitadores desbalanceados | cerrar `()`, `[]`, `{}` |
| `PGS-E4504` | metavariable repetida de forma inconsistente | igualar repeticiones |
| `PGS-E4505` | macro no encontrada | `summon` o definirla |
| `PGS-E4506` | definición de proc macro en PenguScript | escribirla en Rust |
| `PGS-W4501` | macro definida y no usada | eliminarla o usarla |
| `PGS-W4502` | invocación de macro en posición de tipo | usar un tipo o una macro de tipo |

### 45.9 Criterios de aceptación

- [x] `incantation` genera `macro_rules!`.
- [x] Definición, invocación, repeticiones e higiene están cubiertas.
- [x] Las macros procedurales solo se consumen.
- [x] Hay una guía de cuándo usar macros.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-46-derives"></a>
## 46. Derives y traits comunes

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 6 |
| Rust | `#[derive(...)]` |
| Palabras mágicas | `@@derive` |
| Depende de | §28, §29, §35, §44 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec46_derives.pengu` |

Un **derive** es una implementación generada automáticamente por el compilador
para un `rune` o un `enchanting`. En PenguScript se escribe con `@@derive(...)`;
el codegen lo traduce a `#[derive(...)]`.

### 46.1 Sintaxis

```pengu
@@derive(Debug, Clone, PartialEq)
rune Point
    x: Int
    y: Int

@@derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)
rune Id
    value: UInt
```

Rust generado:

```rust
#[derive(Debug, Clone, PartialEq)]
struct Point {
    x: i32,
    y: i32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
struct Id {
    value: u32,
}
```

1. `@@derive` solo se aplica a `rune` y `enchanting`.
2. Los nombres son los del trait que se deriva; deben estar en scope.
3. El orden de los derives se conserva, aunque el orden no cambia la semántica.
4. Un derive en un campo, función o `scroll` es error (`PGS-E4602`).
5. Los derives de una crate externa se importan con `summon`.
6. Un derive de una proc macro se documenta en la crate que lo define.

### 46.2 Derives built-in

| Derive | Genera | Requisito |
|---|---|---|
| `Clone` | `fn clone(&self) -> Self` | todos los campos `Clone` |
| `Copy` | copia bit a bit | `Clone`; todos los campos `Copy`; sin `Drop` |
| `Debug` | `fmt::Debug` | todos los campos `Debug` |
| `PartialEq` | `eq`/`ne` | todos los campos `PartialEq` |
| `Eq` | marca de equivalencia | `PartialEq`; todos los campos `Eq` |
| `PartialOrd` | `partial_cmp` | `PartialEq`; campos `PartialOrd` |
| `Ord` | `cmp` | `Eq` + `PartialOrd`; campos `Ord` |
| `Hash` | `hash` | `Eq`; campos `Hash` |
| `Default` | `default()` | todos los campos `Default` |

1. `Copy` implica `Clone`; no se puede derivar `Copy` sin `Clone`.
2. Un tipo con `Drop` no puede ser `Copy`.
3. `Eq` no se puede derivar para un tipo que contiene `Float`.
4. `Ord` no se puede derivar para un tipo que contiene `Float`.
5. `Hash` debe ser consistente con `Eq`: dos valores iguales tienen el mismo
   hash.
6. `Default` usa el valor por defecto de cada campo, no un constructor.

### 46.3 `Clone` y `Copy`

```pengu
@@derive(Debug, Clone, Copy, PartialEq)
rune Id
    value: UInt

grimoire
    bind a = Id(value: 7)
    bind b = a
    print(a == b)
```

Rust generado:

```rust
#[derive(Debug, Clone, Copy, PartialEq)]
struct Id {
    value: u32,
}

fn main() {
    let a = Id { value: 7 };
    let b = a;
    println!("{}", a == b);
}
```

1. `Copy` hace que `bind b = a` copie el valor; `a` sigue siendo usable.
2. Sin `Copy`, `bind b = a` mueve `a`; usarlo después es error (§16).
3. `Clone` es explícito: `a.clone()` para tipos no `Copy`.
4. Un `rune` con un `String` puede ser `Clone`, pero no `Copy`.
5. `Copy` es una promesa de bajo costo; no se deriva en tipos grandes sin
   medir.

### 46.4 `Debug` y `Display`

```pengu
@@derive(Debug)
rune Point
    x: Float
    y: Float

grimoire
    bind p = Point(x: 1.0, y: 2.0)
    print("#{p:?}")
```

Rust generado:

```rust
#[derive(Debug)]
struct Point {
    x: f64,
    y: f64,
}

fn main() {
    let p = Point { x: 1.0, y: 2.0 };
    println!("{:?}", p);
}
```

1. `Debug` es para diagnóstico; el formato puede cambiar.
2. `Display` **no** se deriva; se implementa con `ritual` (§35).
3. `print("#{p}")` requiere `Display`; `print("#{p:?}")` requiere `Debug`.
4. `{:#?}` es el formato multilínea de `Debug`.
5. Un tipo público debe implementar `Debug` salvo que exponga secretos.

`Display` manual:

```rust
use std::fmt;

struct Point {
    x: f64,
    y: f64,
}

impl fmt::Display for Point {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "({}, {})", self.x, self.y)
    }
}

fn main() {
    let p = Point { x: 1.0, y: 2.0 };
    println!("{}", p);
}
```

### 46.5 Igualdad y orden

```pengu
@@derive(Debug, PartialEq, Eq, PartialOrd, Ord)
rune Version
    major: UInt
    minor: UInt

grimoire
    bind a = Version(major: 1, minor: 2)
    bind b = Version(major: 1, minor: 3)
    print(a < b)
```

Rust generado:

```rust
#[derive(Debug, PartialEq, Eq, PartialOrd, Ord)]
struct Version {
    major: u32,
    minor: u32,
}

fn main() {
    let a = Version { major: 1, minor: 2 };
    let b = Version { major: 1, minor: 3 };
    println!("{}", a < b);
}
```

1. `PartialEq` compara campo a campo, en orden de declaración.
2. `Eq` no cambia la implementación; es una marca de equivalencia total.
3. `PartialOrd` usa el orden lexicográfico de los campos.
4. `Ord` es un orden total; requiere `Eq` y `PartialOrd`.
5. `Float` no implementa `Eq` ni `Ord`; un `rune` con `Float` no puede
   derivarlos.
6. El orden derivado es el orden de los campos, no el nombre.

### 46.6 `Hash`

```pengu
@@derive(Debug, PartialEq, Eq, Hash)]
rune Key
    id: UInt

grimoire
    summon std::collections::HashSet
    morph seen = HashSet.new()
    seen.insert(Key(id: 1))
    print(seen.contains(&Key(id: 1)))
```

Rust generado:

```rust
use std::collections::HashSet;

#[derive(Debug, PartialEq, Eq, Hash)]
struct Key {
    id: u32,
}

fn main() {
    let mut seen = HashSet::new();
    seen.insert(Key { id: 1 });
    println!("{}", seen.contains(&Key { id: 1 }));
}
```

1. `Hash` debe ser consistente con `Eq`.
2. `Hash` no garantiza un orden ni un valor estable entre ejecuciones.
3. Un `HashMap` con un tipo custom necesita `Eq + Hash`.
4. Para un hasher distinto, se usa `HashMap.with_hasher(...)` (§25).
5. No se deriva `Hash` en un tipo con `Float`.

### 46.7 `Default`

```pengu
@@derive(Debug, Default)
rune Config
    retries: UInt
    verbose: Bool

grimoire
    bind c = Config.default()
    print("#{c:?}")
```

Rust generado:

```rust
#[derive(Debug, Default)]
struct Config {
    retries: u32,
    verbose: bool,
}

fn main() {
    let c = Config::default();
    println!("{:?}", c);
}
```

1. `Default` usa `0`, `false`, `String::new()`, `Vec::new()`, etc.
2. Un campo sin `Default` impide derivar `Default`.
3. `Default` no es un constructor con argumentos; para eso se escribe `new`.
4. Un tipo público puede implementar `Default` y `new` a la vez.
5. `Config.default()` es la forma PenguScript de `Config::default()`.

### 46.8 Derives externos

```pengu
summon serde::Serialize
summon serde::Deserialize

@@cfg_attr(feature = "serde", derive(Serialize, Deserialize))
rune User
    name: String
```

1. Un derive externo es una proc macro; debe estar en `Tome.toml`.
2. `@@cfg_attr` permite activarlo solo con una feature.
3. La crate debe declarar la feature `serde`.
4. El derive puede añadir bounds automáticos; se documentan en su crate.
5. PenguScript no reexporta derives de terceros.

### 46.9 Errores y límites

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4601` | `@@derive` en un item no válido | moverlo a `rune`/`enchanting` |
| `PGS-E4602` | derive desconocido | importar la crate o corregir el nombre |
| `PGS-E4603` | `Copy` sin `Clone` | añadir `Clone` |
| `PGS-E4604` | `Copy` en un tipo con `Drop` | quitar `Copy` o `Drop` |
| `PGS-E4605` | `Eq`/`Ord` con `Float` | no derivarlos; implementar a mano |
| `PGS-E4606` | `Hash` sin `Eq` | añadir `Eq` |
| `PGS-W4601` | `Debug` en un tipo con secretos | implementar `Debug` a mano |
| `PGS-W4602` | derive innecesario | eliminarlo |

1. Un derive no puede violar la coherencia: no se implementa un trait externo
   para un tipo externo.
2. Un derive generado no se puede especializar por campo.
3. Si el comportamiento automático no sirve, se escribe el `ritual` a mano.
4. Un derive puede ser más lento de compilar que una implementación simple.
5. Los derives no sustituyen a los tests de igualdad/orden.

### 46.10 Criterios de aceptación

- [x] Los nueve derives built-in están definidos.
- [x] Requisitos y límites están claros.
- [x] `Clone`/`Copy`, `Debug`/`Display`, orden y `Hash` tienen ejemplo.
- [x] Los derives externos se consumen, no se definen.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-47-build-features"></a>
## 47. Build scripts, features y cfg

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 6 |
| Rust | `build.rs`, `[features]`, `#[cfg]`, `cfg!` |
| Palabras mágicas | `build.pengu`, `@@cfg` |
| Depende de | §3, §43, §44 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec47_build_features.pengu` |

Un **build script** es un programa que se ejecuta antes de compilar la crate.
Puede generar código, emitir directivas a Cargo, detectar el entorno y enlazar
bibliotecas nativas. En PenguScript se escribe en `build.pengu` y se traduce a
`build.rs`.

### 47.1 `build.pengu`

```pengu
summon std::env
summon std::fs

grimoire
    bind out = env.var("OUT_DIR").unwrap()
    bind path = "#{out}/generated.rs"
    fs.write(path, "pub const BUILD_ID: &str = \"demo\";").unwrap()
    print("cargo:rerun-if-changed=build.pengu")
```

Rust generado (`build.rs`):

```rust
use std::env;
use std::fs;

fn main() {
    let out = env::var("OUT_DIR").unwrap();
    let path = format!("{}/generated.rs", out);
    fs::write(&path, "pub const BUILD_ID: &str = \"demo\";").unwrap();
    println!("cargo:rerun-if-changed=build.pengu");
}
```

Reglas:

1. `build.pengu` es un programa completo con entrada `grimoire`.
2. Se ejecuta con la toolchain anfitriona, antes de compilar la crate.
3. Su salida estándar se interpreta como directivas `cargo:`.
4. `OUT_DIR` es el directorio donde puede escribir archivos generados.
5. No debe acceder a la red ni a rutas absolutas del desarrollador.
6. Si no existe `build.pengu`, no se genera `build.rs`.
7. `[build-dependencies]` en `Tome.toml` declara sus dependencias.
8. Un build script no puede importar la crate que está construyendo.

### 47.2 Directivas de Cargo

| Directiva | Efecto |
|---|---|
| `cargo:rerun-if-changed=RUTA` | reejecutar si cambia el archivo |
| `cargo:rerun-if-env-changed=VAR` | reejecutar si cambia la variable |
| `cargo:rustc-cfg=CLAVE` | activar un `cfg` |
| `cargo:rustc-check-cfg=CLAVE` | declarar un `cfg` conocido |
| `cargo:rustc-env=VAR=VALOR` | definir una variable de entorno |
| `cargo:rustc-link-lib=LIB` | enlazar una biblioteca nativa |
| `cargo:rustc-link-search=RUTA` | añadir un directorio de búsqueda |
| `cargo:rustc-link-arg=ARG` | pasar un argumento al linker |
| `cargo:warning=MENSAJE` | aviso de compilación |
| `cargo:metadata=...` | metadato para herramientas |

1. Cada directiva va en una línea, sin espacios antes de `cargo:`.
2. `rerun-if-changed` sustituye al comportamiento por defecto; si se emite, el
   script solo se reejecuta por esas rutas.
3. `rustc-check-cfg` evita el warning de `unexpected_cfgs`.
4. `rustc-env` está disponible con `env!` en el código.
5. `rustc-link-lib` y `rustc-link-search` se usan para FFI (§54).
6. `cargo:warning` no falla la compilación; para fallar, el script debe salir
   con error.

### 47.3 Features

```toml
[features]
default = ["std"]
std = []
serde = ["dep:serde"]
full = ["std", "serde"]

[dependencies]
serde = { version = "1.0", features = ["derive"], optional = true }
```

1. Una feature es una bandera de compilación; no es un valor de runtime.
2. Las features son **aditivas**: activar una no desactiva otra.
3. `default` se activa salvo `--no-default-features`.
4. `dep:serde` activa la dependencia opcional sin crear una feature implícita.
5. Una feature puede activar otras: `full = ["std", "serde"]`.
6. No hay features negativas; no se puede “quitar” una feature.
7. La unificación de features ocurre en todo el grafo de dependencias.
8. Una feature no debe cambiar la semántica de forma incompatible; debe añadir
   funcionalidad.

### 47.4 `@@cfg`

```pengu
@@cfg(feature = "serde")
serialize_user = (user: &User) -> String
    format!("{}", user.name)

@@cfg(target_os = "linux")
platform = () -> &'static Str
    "linux"
```

Rust generado:

```rust
struct User {
    name: String,
}

#[cfg(feature = "serde")]
fn serialize_user(user: &User) -> String {
    format!("{}", user.name)
}

#[cfg(target_os = "linux")]
fn platform() -> &'static str {
    "linux"
}
```

1. `@@cfg` elimina el item si la condición es falsa; no hay rama `else`.
2. La condición usa la sintaxis de `cfg` de Rust.
3. `feature = "x"` consulta una feature del tome.
4. `target_os`, `target_arch`, `target_family`, `target_env`,
   `target_pointer_width`, `unix`, `windows` describen el target.
5. `debug_assertions` distingue debug/release.
6. `test` solo está activo al compilar tests.
7. Una condición con una feature no declarada produce `PGS-W4710`.

### 47.5 `cfg!` en runtime

```pengu
grimoire
    if cfg!(debug_assertions) then
        print("debug")
    else
        print("release")
```

Rust generado:

```rust
fn main() {
    if cfg!(debug_assertions) {
        println!("debug");
    } else {
        println!("release");
    }
}
```

1. `cfg!` es una macro de Rust que se evalúa en compilación y devuelve `Bool`.
2. Es útil para código que debe existir en ambas ramas.
3. `cfg!` no elimina el código de la rama falsa; para eso se usa `@@cfg`.
4. `cfg!` en una condición de tipo no es válido; devuelve `Bool`.
5. `cfg!` con una feature no declarada produce el mismo warning que `@@cfg`.

### 47.6 `cfg` por target

```rust
#[cfg(target_os = "linux")]
fn platform() -> &'static str {
    "linux"
}

#[cfg(target_os = "windows")]
fn platform() -> &'static str {
    "windows"
}

#[cfg(not(any(target_os = "linux", target_os = "windows")))]
fn platform() -> &'static str {
    "other"
}

fn main() {
    println!("{}", platform());
}
```

1. Solo una definición de `platform` se compila por target.
2. Las tres ramas deben cubrir todos los targets que se quieran soportar.
3. Si ninguna coincide, el símbolo no existe y el error es de resolución.
4. Los `cfg` de target no son mutuamente excluyentes por sí solos; se usa
   `not(any(...))` para el caso restante.
5. Un `cfg` desconocido no es error de compilación, pero puede ser warning.

### 47.7 Código generado

```pengu
rust
    include!(concat!(env!("OUT_DIR"), "/generated.rs"));
```

1. Un build script puede escribir `.rs` en `OUT_DIR`.
2. `include!` inserta el archivo en el crate.
3. El código incluido es Rust crudo; pasa por el compilador de Rust.
4. El código generado debe ser determinista y no contener rutas absolutas.
5. Para generarlo desde PenguScript, se escribe con `fs.write` en el build
   script; no se evalúa en tiempo de compilación de PenguScript.
6. Un `include!` de un archivo ausente es error de compilación.

### 47.8 Reproducibilidad

1. Un build script no debe acceder a la red.
2. No debe leer variables de entorno no declaradas con
   `rerun-if-env-changed`.
3. No debe incluir timestamps ni rutas absolutas en el código generado.
4. Debe emitir `rerun-if-changed` para sus entradas.
5. La salida debe ser determinista para las mismas entradas.
6. `SOURCE_DATE_EPOCH` se usa si se necesita una fecha reproducible.
7. Un build script que falla debe imprimir un mensaje claro y salir con error.

### 47.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4701` | `build.pengu` sin `grimoire` | añadir la entrada |
| `PGS-E4702` | directiva `cargo:` mal formada | revisar la línea |
| `PGS-E4703` | `OUT_DIR` no usado | escribir el archivo en `OUT_DIR` |
| `PGS-E4704` | feature no declarada | añadirla a `[features]` |
| `PGS-E4705` | `cfg` con clave desconocida | usar una clave válida |
| `PGS-E4706` | build script importa la crate actual | quitar la dependencia |
| `PGS-E4707` | código generado no determinista | eliminar timestamp/rutas |
| `PGS-W4710` | `cfg` de feature no declarada | declararla o corregir |
| `PGS-W4711` | `rerun-if-changed` ausente | declarar las entradas |

### 47.10 Criterios de aceptación

- [x] `build.pengu` mapea a `build.rs`.
- [x] Las directivas de Cargo están cubiertas.
- [x] Features, `@@cfg` y `cfg!` están definidos.
- [x] El código generado y la reproducibilidad están tratados.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="part-7"></a>
## Parte VII — Runtime avanzado

<a id="sec-48-errores"></a>
## 48. Manejo de errores

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 7 |
| Rust | `Option<T>`, `Result<T, E>`, `?`, `panic!`, `Termination` |
| Palabras mágicas | `?T`, `!T`, `none`, `some`, `ok`, `err`, `panic` |
| Depende de | §4, §8, §29, §30, §35 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec48_errors.pengu` |

PenguScript no tiene `null`, excepciones ni errores implícitos. Un valor que
puede faltar se representa con `?T` (`Option<T>`); una operación que puede fallar,
con `!T` (`Result<T, Error>`). El operador `?` propaga el fallo sin `try`/`catch`.

### 48.1 `Option` y `Result`

| PenguScript | Rust | Constructor | Éxito | Fallo |
|---|---|---|---|---|
| `?T` | `Option<T>` | `some(v)` | `some(v)` | `none` |
| `!T` | `Result<T, Error>` | `ok(v)` | `ok(v)` | `err(e)` |
| `!T` con error custom | `Result<T, E>` | `ok(v)` | `ok(v)` | `err(e)` |

1. `?T` y `!T` son azúcar; no son tipos distintos de `Option`/`Result`.
2. `some`, `ok` y `err` son funciones; `none` es un valor constante.
3. `Option` no contiene un mensaje de error; para eso se usa `Result`.
4. `Result` no se puede ignorar silenciosamente: o se consume, o se propaga con
   `?`, o se convierte explícitamente.
5. `Option`/`Result` se pueden anidar: `? !T` es `Option<Result<T, E>>`.

```pengu
find = (items: &[Int], target: Int) -> ?Usize
    for (i, item) in items.iter().enumerate()
        if *item == target
            return some(i)
    none

parse = (text: &Str) -> !Int
    bind n = text.parse[Int]()?
    ok(n)
```

Rust generado:

```rust
fn find(items: &[i32], target: i32) -> Option<usize> {
    for (i, item) in items.iter().enumerate() {
        if *item == target {
            return Some(i);
        }
    }
    None
}

fn parse(text: &str) -> Result<i32, Box<dyn std::error::Error + Send + Sync>> {
    let n = text.parse::<i32>()?;
    Ok(n)
}
```

`Error` es el alias de `Box<dyn std::error::Error + Send + Sync>` (§4.4).

### 48.2 El operador `?`

`expr?` hace:

1. Si `expr` es `some(v)`/`ok(v)`, se evalúa a `v`.
2. Si es `none`/`err(e)`, retorna temprano con ese valor.
3. En `Result`, el error se convierte con `From` al tipo de error de la función.
4. En `Option`, no hay conversión: el fallo es `none`.

```pengu
read_config = (path: &Str) -> !String
    bind text = std.fs.read_to_string(path)?
    ok(text)

first_line = (path: &Str) -> ?String
    bind text = std.fs.read_to_string(path).ok()?
    text.lines().next().map(String.from)
```

Rust generado:

```rust
fn read_config(path: &str) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
    let text = std::fs::read_to_string(path)?;
    Ok(text)
}

fn first_line(path: &str) -> Option<String> {
    let text = std::fs::read_to_string(path).ok()?;
    text.lines().next().map(String::from)
}
```

Reglas:

1. `?` solo se usa en una función que devuelve `Result`/`Option` compatible
   (`PGS-E4801`).
2. `?` sobre `Result` en una función `Option` es error; y viceversa
   (`PGS-E4802`).
3. `?` sobre `Result` requiere `E: Into<Efun>`, donde `Efun` es el error de la
   función (`PGS-E4803`).
4. `?` no se usa en `grimoire` con retorno `Unit`; se declara `grimoire: !Unit`.
5. `?` no se usa en un bloque que no sea el cuerpo de una función compatible.
6. `?` no convierte `none` en `err`; son dominios distintos.
7. `?` se asocia al postfix más cercano: `foo()?.bar()` es
   `(foo()?).bar()`.
8. `?` no oculta el error: el tipo de retorno lo hace visible.

### 48.3 `panic`, `assert` y `unwrap`

```pengu
check = (n: Int) -> Int
    assert(n > 0, "n debe ser positivo")
    n

read_port = (text: &Str) -> UInt
    text.parse[UInt]().expect("puerto inválido")
```

Rust generado:

```rust
fn check(n: i32) -> i32 {
    assert!(n > 0, "n debe ser positivo");
    n
}

fn read_port(text: &str) -> u32 {
    text.parse::<u32>().expect("puerto inválido")
}
```

1. `panic("msg")` genera `panic!("msg")`; su tipo es `Never`.
2. `assert(cond, "msg")` genera `assert!(cond, "msg")`.
3. `assert_eq(a, b)` y `assert_ne(a, b)` están disponibles en tests.
4. `unwrap()`/`expect()` son para invariantes comprobadas; en código de
   biblioteca se prefiere `?`.
5. Un `panic` no es un error recuperable; no se usa para validación de entrada.
6. `panic` en `no_std` requiere `@@panic_handler` (§55).
7. `panic = "abort"` elimina el unwind; `catch_unwind` deja de capturar.

### 48.4 Errores custom

```pengu
@@derive(Debug)
enchanting ParseError
    Empty
    Invalid(String)

ritual Display for ParseError
    fmt = (@, f: &mut fmt::Formatter) -> fmt::Result
        match @
            when ParseError.Empty then write(f, "vacío")
            when ParseError.Invalid(msg) then write(f, "inválido: #{msg}")

ritual Error for ParseError
```

Rust generado:

```rust
use std::fmt;

#[derive(Debug)]
enum ParseError {
    Empty,
    Invalid(String),
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseError::Empty => write!(f, "vacío"),
            ParseError::Invalid(msg) => write!(f, "inválido: {}", msg),
        }
    }
}

impl std::error::Error for ParseError {}
```

1. Un error custom implementa `Debug`, `Display` y `Error`.
2. `Error` no requiere métodos; `source()` es opcional.
3. `Display` es el mensaje para el usuario; `Debug` es para diagnóstico.
4. Un `enchanting` es la forma natural de modelar variantes de error.
5. Un `rune` sirve para un error con campos comunes.
6. No se usa `String` como error en APIs públicas; se define un tipo.

### 48.5 Conversión con `From`

```pengu
@@derive(Debug)
rune ConfigError
    message: String

ritual Display for ConfigError
    fmt = (@, f: &mut fmt::Formatter) -> fmt::Result
        write(f, "config: #{@.message}")

ritual Error for ConfigError

ritual From[ParseError] for ConfigError
    from = (e: ParseError) -> ConfigError
        ConfigError(message: "#{e}")
```

Rust generado:

```rust
use std::fmt;

#[derive(Debug)]
struct ConfigError {
    message: String,
}

impl fmt::Display for ConfigError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "config: {}", self.message)
    }
}

impl std::error::Error for ConfigError {}

#[derive(Debug)]
enum ParseError {
    Empty,
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseError::Empty => write!(f, "vacío"),
        }
    }
}

impl std::error::Error for ParseError {}

impl From<ParseError> for ConfigError {
    fn from(e: ParseError) -> ConfigError {
        ConfigError { message: format!("{}", e) }
    }
}
```

Con `From`, `?` convierte automáticamente:

```pengu
load = (text: &Str) -> !Int
    bind n = parse(text)?
    ok(n)
```

1. `?` usa `From`, no `Into` directamente.
2. La implementación de `From` debe ser coherente y no perder información.
3. Un error de bajo nivel se envuelve en uno de dominio.
4. No se implementa `From<String>` para todo; se pierde el tipo.
5. `thiserror` y `anyhow` son crates externas; se consumen, no se integran al
   lenguaje.

### 48.6 `main` fallible

```pengu
grimoire: !Unit
    bind config = read_config("Tome.toml")?
    print(config)
```

Rust generado:

```rust
fn read_config(_path: &str) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
    Ok(String::new())
}

fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let config = read_config("Tome.toml")?;
    println!("{}", config);
    Ok(())
}
```

1. `grimoire: !Unit` genera `fn main() -> Result<(), E>`.
2. El `E` por defecto es `Box<dyn Error + Send + Sync>`.
3. `?` funciona en `main` solo con esta forma.
4. Un `main` fallible imprime el error y devuelve código de salida distinto de
   cero.
5. `Termination` permite personalizar el código de salida (§48.8).
6. Un `grimoire` normal no puede usar `?` (`PGS-E4804`).

### 48.7 `catch_unwind`

```pengu
bind result = std.panic.catch_unwind(() => panic("boom"))
match result
    when ok(_) then print("sin panic")
    when err(_) then print("panic capturado")
```

Rust generado:

```rust
fn main() {
    let result = std::panic::catch_unwind(|| panic!("boom"));
    match result {
        Ok(_) => println!("sin panic"),
        Err(_) => println!("panic capturado"),
    }
}
```

1. `catch_unwind` captura un panic de unwind, no un abort.
2. El closure debe ser `UnwindSafe`; si no, se usa `AssertUnwindSafe`.
3. No se usa para control de flujo normal.
4. Un panic puede dejar invariantes rotas; el estado compartido debe revisarse.
5. `panic = "abort"` hace que `catch_unwind` no capture.

### 48.8 `Termination` y códigos de salida

Rust permite que `main` devuelva cualquier `T: Termination`. PenguScript expone
solo dos formas:

1. `grimoire` -> `fn main()` con salida 0.
2. `grimoire: !Unit` -> `fn main() -> Result<(), Error>` con salida 1 en error.

Para un código distinto, se usa `std.process.exit(code)` explícitamente. No hay
un `main` con `ExitCode` en la superficie del lenguaje; el codegen puede
añadirlo en el futuro sin romper la sintaxis.

### 48.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4801` | `?` fuera de función compatible | devolver `Result`/`Option` o usar `match` |
| `PGS-E4802` | `?` de `Option` en función `Result` | convertir con `ok_or`/`ok_or_else` |
| `PGS-E4803` | error sin `From` al error de retorno | implementar `From` o mapear |
| `PGS-E4804` | `?` en `grimoire` no fallible | declarar `grimoire: !Unit` |
| `PGS-E4805` | `unwrap` en código de biblioteca | usar `?` o `expect` con invariante |
| `PGS-E4806` | `panic` para entrada inválida | devolver `Result` |
| `PGS-E4807` | `Error` sin `Display`/`Debug` | implementar ambos |
| `PGS-W4801` | `Box<dyn Error>` en API pública | definir un error de dominio |
| `PGS-W4802` | `catch_unwind` para flujo normal | usar `Result` |

### 48.10 Criterios de aceptación

- [x] `Option`/`Result` y sus constructores están definidos.
- [x] `?` tiene reglas de compatibilidad y conversión.
- [x] `panic`, `assert`, `unwrap` y `catch_unwind` están diferenciados.
- [x] Los errores custom implementan `Error`.
- [x] `grimoire: !Unit` está conectado con `Termination`.

[↑ Volver al índice](#indice)

<a id="sec-49-iteradores"></a>
## 49. Iteradores

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 7 |
| Rust | `Iterator`, `IntoIterator`, adaptadores |
| Palabras mágicas | `iter`, `iter_mut`, `into_iter` |
| Depende de | §14, §22–§27, §35, §38 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec49_iterators.pengu` |

Un iterador produce una secuencia de valores de forma perezosa. Los adaptadores
construyen una nueva secuencia; los consumidores la recorren y producen un
resultado. Un `for` es azúcar sobre `IntoIterator`.

### 49.1 `Iterator` e `IntoIterator`

| Forma | Produce | Rust |
|---|---|---|
| `collection.iter()` | referencias `&T` | `iter()` |
| `collection.iter_mut()` | referencias `&mut T` | `iter_mut()` |
| `collection.into_iter()` | valores `T` | `into_iter()` |
| `for x in collection` | valores o referencias según `IntoIterator` | `for` |
| `for x in collection.iter()` | referencias | `for` |

1. `Iterator` tiene un método `next() -> ?Item`.
2. `IntoIterator` convierte un valor en un iterador.
3. `for x in array` consume el array si sus elementos no son `Copy`; para
   conservarlo se usa `.iter()`.
4. `iter_mut` requiere un binding `morph` y produce préstamos mutables.
5. Un iterador no se reutiliza después de consumirse; se crea otro.

```pengu
values = [1, 2, 3]

grimoire
    for value in values.iter()
        print(value)

    morph mutable = [1, 2, 3]
    for value in mutable.iter_mut()
        *value *= 2

    print(mutable)
```

Rust generado:

```rust
fn main() {
    let values = [1, 2, 3];

    for value in values.iter() {
        println!("{}", value);
    }

    let mut mutable = [1, 2, 3];
    for value in mutable.iter_mut() {
        *value *= 2;
    }

    println!("{:?}", mutable);
}
```

### 49.2 Adaptadores

| Adaptador | Efecto | Ejemplo |
|---|---|---|
| `map` | transforma cada elemento | `xs.iter().map((x: &Int) => *x * 2)` |
| `filter` | conserva los que cumplen | `xs.iter().filter((x: &&Int) => **x > 0)` |
| `filter_map` | filtra y transforma | `xs.iter().filter_map((x: &&Int) => some(**x))` |
| `flat_map` | aplana el resultado | `xs.iter().flat_map((x: &&Int) => [**x, **x])` |
| `flatten` | aplana un iterador de iteradores | `nested.iter().flatten()` |
| `fold` | acumula con estado | `xs.iter().fold(0, (acc: Int, x: &Int) => acc + *x)` |
| `reduce` | acumula sin estado inicial | `xs.iter().reduce((a: &Int, b: &Int) => a + b)` |
| `scan` | acumula y emite | `xs.iter().scan(0, (acc: &mut Int, x: &Int) => ...)` |
| `take` | primeros `n` | `xs.iter().take(2)` |
| `skip` | omite `n` | `xs.iter().skip(2)` |
| `take_while` | mientras se cumpla | `xs.iter().take_while((x: &Int) => **x < 3)` |
| `skip_while` | omite mientras se cumpla | `xs.iter().skip_while((x: &Int) => **x < 3)` |
| `chain` | concatena | `a.iter().chain(b.iter())` |
| `zip` | empareja | `a.iter().zip(b.iter())` |
| `enumerate` | añade índice | `xs.iter().enumerate()` |
| `peekable` | permite `peek` | `xs.iter().peekable()` |
| `rev` | invierte | `xs.iter().rev()` |
| `cycle` | repite infinitamente | `xs.iter().cycle()` |
| `inspect` | observa sin consumir | `xs.iter().inspect((x: &Int) => print(x))` |
| `step_by` | cada `n` | `xs.iter().step_by(2)` |
| `fuse` | termina tras el primer `none` | `xs.iter().fuse()` |

1. Los adaptadores son perezosos: no ejecutan nada hasta un consumidor.
2. Cada adaptador devuelve un tipo distinto; no se guarda en una variable sin
   `impl Iterator` o `Box<dyn Iterator>`.
3. `map`/`filter` reciben referencias si el iterador es `.iter()`.
4. `filter_map` usa `?T`; `flatten` requiere un iterador de iteradores.
5. `scan` recibe el estado por referencia mutable.
6. `cycle` es infinito; se combina con `take`.
7. `rev` requiere `DoubleEndedIterator`.
8. `inspect` es para depuración, no para efectos secundarios de negocio.

### 49.3 Consumidores

| Consumidor | Resultado |
|---|---|
| `collect` | colección o `Result`/`Option` |
| `sum` | suma |
| `product` | producto |
| `min` / `max` | `?T` |
| `count` | `Usize` |
| `any` / `all` | `Bool` |
| `find` | `?T` |
| `position` | `?Usize` |
| `partition` | dos colecciones |
| `unzip` | dos colecciones |
| `for_each` | `Unit` |

```pengu
values = [1, 2, 3, 4, 5]

bind doubled = values.iter().map((x: &Int) => *x * 2).collect[Vec[Int]]()
bind total = values.iter().sum[Int]()
bind first_even = values.iter().find((x: &&Int) => **x % 2 == 0)
bind (evens, odds) = values.iter().partition((x: &&Int) => **x % 2 == 0)

print(doubled)
print(total)
print(first_even)
print(evens)
print(odds)
```

Rust generado:

```rust
fn main() {
    let values = [1, 2, 3, 4, 5];

    let doubled: Vec<i32> = values.iter().map(|x| *x * 2).collect();
    let total: i32 = values.iter().sum();
    let first_even = values.iter().find(|x| **x % 2 == 0);
    let (evens, odds): (Vec<&i32>, Vec<&i32>) =
        values.iter().partition(|x| **x % 2 == 0);

    println!("{:?}", doubled);
    println!("{}", total);
    println!("{:?}", first_even);
    println!("{:?}", evens);
    println!("{:?}", odds);
}
```

1. `collect` necesita el tipo de destino; se usa turbofish
   `collect[Vec[Int]]()`.
2. `collect` también puede producir `Result[Vec[T], E]` si el iterador es de
   `Result`.
3. `sum`/`product` necesitan un tipo numérico concreto.
4. `min`/`max` devuelven `?T`; no hay valor por defecto.
5. `partition` requiere anotar el tipo de las dos colecciones si no se infiere.
6. `unzip` separa pares en dos colecciones.
7. `for_each` se usa por efectos secundarios; un `for` suele ser más claro.

### 49.4 Iteradores custom

```pengu
rune Counter
    current: Int

ritual Iterator for Counter
    essence Item = Int

    next = (@mut) -> ?Int
        if @.current >= 3
            none
        else
            bind value = @.current
            @.current += 1
            some(value)
```

Rust generado:

```rust
struct Counter {
    current: i32,
}

impl Iterator for Counter {
    type Item = i32;

    fn next(&mut self) -> Option<i32> {
        if self.current >= 3 {
            None
        } else {
            let value = self.current;
            self.current += 1;
            Some(value)
        }
    }
}
```

1. Un iterador custom implementa `Iterator` y declara `Item`.
2. `next` recibe `@mut` y devuelve `?Item`.
3. El estado vive en el `rune`; no se usan generadores ni `yield`.
4. `size_hint` es opcional; si se omite, se usa el default.
5. Un iterador que termina y luego vuelve a producir viola el contrato; `fuse`
   lo protege.
6. Para un iterador que presta datos, el lifetime se declara en el `rune`
   (§18).

### 49.5 `impl Iterator`

```pengu
evens = (limit: Int) -> impl Iterator[Item = Int]
    (0..limit).filter((x: &Int) => *x % 2 == 0)
```

Rust generado:

```rust
fn evens(limit: i32) -> impl Iterator<Item = i32> {
    (0..limit).filter(|x| *x % 2 == 0)
}
```

1. `impl Iterator[Item = T]` oculta el tipo concreto y conserva el contrato.
2. No se puede devolver `impl Iterator` con dos tipos concretos distintos; para
   eso se usa `Box<dyn Iterator<Item = T>>`.
3. `impl Trait` en retorno es monomórfico y de coste cero.
4. El llamador no puede nombrar el tipo, pero puede recorrerlo.
5. Si el iterador presta datos, el lifetime debe aparecer en la firma.

### 49.6 `DoubleEndedIterator`, `ExactSizeIterator`, `FusedIterator`

| Trait | Permite | Ejemplo |
|---|---|---|
| `DoubleEndedIterator` | `next_back`, `rev` | `vec.iter().rev()` |
| `ExactSizeIterator` | `len` exacto | `array.iter().len()` |
| `FusedIterator` | `next` sigue devolviendo `none` | `iter.fuse()` |

1. `rev` solo existe si el iterador es `DoubleEndedIterator`.
2. `len` solo es exacto si el iterador es `ExactSizeIterator`.
3. `FusedIterator` es una garantía, no un adaptador; `fuse` la produce.
4. Un `filter` no es `ExactSizeIterator`; no se usa `len` para saber cuántos
   quedan.
5. Estas traits son marcadores: no cambian la lógica, solo habilitan métodos.

### 49.7 Pereza y comprehensions

Una comprensión produce una colección de inmediato:

```pengu
bind squares = [x * x for x in 0..5]
```

Un iterador es perezoso:

```pengu
bind squares = (0..5).map((x: Int) => x * x)
```

1. La comprensión es azúcar para un bucle que construye una colección; se
   evalúa al crearse.
2. El iterador no se evalúa hasta `collect`, `sum`, `for`, etc.
3. No se mezclan: `[x for x in iter]` consume el iterador; `iter.map(...)` no.
4. Una comprensión no puede ser infinita; un iterador sí (`cycle`).
5. Para depurar pereza, se usa `inspect`.

### 49.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4901` | `for` sobre un valor no iterable | usar `.iter()`/`IntoIterator` |
| `PGS-E4902` | `iter_mut` sin binding `morph` | declarar `morph` |
| `PGS-E4903` | `collect` sin tipo de destino | añadir turbofish |
| `PGS-E4904` | `rev` sin `DoubleEndedIterator` | usar `collect` + `rev` |
| `PGS-E4905` | `len` en iterador no exacto | contar con `count` |
| `PGS-E4906` | adaptador que no se consume | añadir consumidor |
| `PGS-E4907` | `?` dentro de `map` sin `Result` | usar `filter_map`/`collect` |
| `PGS-W4901` | `cycle` sin `take` | limitar |
| `PGS-W4902` | `for_each` con lógica compleja | usar `for` |

### 49.9 Criterios de aceptación

- [x] `Iterator`/`IntoIterator` y las tres formas de iterar están definidos.
- [x] La tabla de adaptadores y consumidores está completa.
- [x] Los iteradores custom y `impl Iterator` tienen ejemplo.
- [x] La diferencia con comprehensions es explícita.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-50-async"></a>
## 50. Async/await

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 7 |
| Rust | `async fn`, `.await`, `Future`, `Pin` |
| Palabras mágicas | `dream`, `awaken` |
| Depende de | §15, §35, §36, §48, §49 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec50_async.pengu` |

Una función asíncrona no bloquea el hilo mientras espera. Devuelve un **future**:
un valor que representa un cálculo que aún no terminó. El future se ejecuta
cuando un executor lo sondea; `awaken` espera su resultado dentro de otro
contexto asíncrono.

### 50.1 `dream` y `awaken`

```pengu
dream fetch = (url: &Str) -> !String
    bind response = http.get(url)?
    ok(response.text)

dream load = (url: &Str) -> !Usize
    bind text = awaken fetch(url)?
    ok(text.len())
```

Rust generado:

```rust
use std::error::Error;

async fn fetch(url: &str) -> Result<String, Box<dyn Error + Send + Sync>> {
    let response = http_get(url)?;
    Ok(response)
}

async fn load(url: &str) -> Result<usize, Box<dyn Error + Send + Sync>> {
    let text = fetch(url).await?;
    Ok(text.len())
}

fn http_get(_url: &str) -> Result<String, Box<dyn Error + Send + Sync>> {
    Ok(String::from("pengu"))
}

fn main() {
    let future = load("https://example.com");
    println!("future creado: {}", std::mem::size_of_val(&future) > 0);
}
```

Reglas:

1. `dream` es un modificador de función; el tipo de retorno es el **output** del
   future, no `Future<T>`.
2. Una llamada a una función `dream` devuelve un future; no se ejecuta hasta
   que se espera o se lanza en un executor.
3. `awaken expr` genera `expr.await`; solo es válido dentro de `dream`, de un
   bloque `dream do` o de una closure `dream`.
4. `awaken` es un operador prefijo; se aplica a la expresión que le sigue.
5. `?` después de `awaken` se aplica al resultado: `awaken f()?` es
   `(awaken f())?`.
6. Una función `dream` puede usar `?` si devuelve `Result`/`Option`.
7. Una función normal no puede usar `awaken` (`PGS-E5001`).

### 50.2 Bloques y closures async

```pengu
bind future = dream do
    bind value = awaken ready(21)
    value * 2

bind make = dream move (x: Int) => x + 1
```

Rust generado:

```rust
fn main() {
    let future = async {
        let value = ready(21).await;
        value * 2
    };

    let make = move |x: i32| async move { x + 1 };

    drop(future);
    drop(make);
}

async fn ready(value: i32) -> i32 {
    value
}
```

1. `dream do` crea un bloque asíncrono; el bloque puede capturar el entorno.
2. `dream (params) => expr` crea una closure asíncrona; captura como una
   closure normal.
3. La forma soportada es `dream (x: Int) => ...`; para forzar captura por
   valor se escribe `dream move (x: Int) => ...`. `move dream (...)` no es
   válido.
4. Una closure async devuelve un future por llamada; no se reutiliza el future.
5. Un bloque async no se ejecuta al crearse; se ejecuta al esperarlo.
6. El tipo del future es anónimo; se usa `impl Future[Output = T]` para
   devolverlo.

### 50.3 `Future`, `Pin` y `Unpin`

| Concepto | Significado | Rust |
|---|---|---|
| `Future` | cálculo que produce `Output` | `Future<Output = T>` |
| `poll` | intenta avanzar el future | `Future::poll` |
| `Pin` | garantiza que el future no se mueve | `Pin<&mut F>` |
| `Unpin` | el future puede moverse | `Unpin` |
| executor | sondea y despierta futures | tokio, async-std, smol |

1. Un future se compone de estados; `poll` devuelve `Pending` o `Ready`.
2. `Pin` es necesario porque un future puede guardar referencias a sí mismo.
3. La mayoría de los futures de `async fn` son `!Unpin`; se usa `Box.pin`.
4. No se implementa `Future` a mano salvo para adaptadores avanzados.
5. `awaken` no bloquea el hilo; el executor decide cuándo reanudar.
6. Un future que no se espera ni se lanza no hace nada; el compilador avisa si
   es `must_use`.

### 50.4 Executors y runtime

PenguScript no incluye un runtime. El tome elige uno:

```toml
[dependencies]
tokio = { version = "1", features = ["rt-multi-thread", "macros"] }
```

1. `tokio`, `async-std` y `smol` son executors externos.
2. El lenguaje no fija un runtime; el codegen no lo importa por defecto.
3. `dream grimoire` declara una entrada asíncrona; necesita un atributo de
   runtime (`@@tokio::main`) o un `main` que llame a `block_on`.
4. `@@tokio::main` sobre `dream grimoire` genera `#[tokio::main] async fn main()`.
5. Sin runtime, un future se puede construir pero no ejecutar.
6. Un runtime de un solo hilo no requiere `Send`; uno multi-hilo sí.

```pengu
@@tokio::main
dream grimoire
    bind text = awaken fetch("https://example.com")?
    print(text)
```

Rust conceptual:

```text
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let text = fetch("https://example.com").await?;
    println!("{}", text);
    Ok(())
}
```

El bloque anterior no se compila sin la crate `tokio`; es una muestra de codegen,
no un ejemplo aislado.

### 50.5 `Send` y `'static`

1. `spawn` requiere `F: Future + Send + 'static` y `F::Output: Send + 'static`.
2. Un future que presta datos locales no es `'static`; no se puede lanzar.
3. `Rc`/`RefCell` no son `Send`; `Arc`/`Mutex` sí.
4. Un `awaken` conserva el future en el estado; los préstamos deben vivir lo
   suficiente.
5. `async move` mueve las capturas al future; evita préstamos que no viven.
6. `Send` no se deriva; se comprueba estructuralmente.

```rust
fn require_send<T: Send>(_: T) {}

fn main() {
    let value = 1;
    let future = async move { value + 1 };
    require_send(future);
}
```

### 50.6 Cancelación y `select!`

1. Un future se cancela al dropearlo; no hay un `cancel()` universal.
2. `select!` espera el primero de varios futures; los demás se cancelan.
3. `select!` es una macro de un runtime/crate (`tokio::select!`,
   `futures::select!`), no una construcción del lenguaje.
4. La cancelación en un `awaken` puede dejar un recurso a medias; se usan
   guardas/RAII.
5. Un timeout se implementa con `timeout` del runtime o con `select!`.
6. No se cancela un future ya completado.

```rust
fn main() {
    let first = async { 1 };
    let second = async { 2 };
    drop(first);
    drop(second);
    println!("futures cancelados al dropear");
}
```

### 50.7 Streams

1. Un `Stream` produce una secuencia asíncrona; es el análogo async de
   `Iterator`.
2. El trait `Stream` vive en `futures-core`; no en `std`.
3. Se consume con `while let some(item) = stream.next().await`.
4. Los adaptadores (`map`, `filter`, `take`) son de `futures-util`.
5. Un stream no es un iterador; no se usa `for` directamente.
6. Backpressure: el consumidor controla el ritmo con `next().await`.

```rust
fn main() {
    let values = vec![1, 2, 3];
    let mut iter = values.into_iter();
    while let Some(value) = iter.next() {
        println!("{}", value);
    }
}
```

El bloque anterior es síncrono; un `Stream` real requiere `futures-core` y un
executor.

### 50.8 `async fn` en traits

```pengu
pact Fetch
    dream fetch = (@, url: &Str) -> String

ritual Client for Fetch
    dream fetch = (@, url: &Str) -> String
        "ok"
```

Rust generado (Rust 2024, `async fn` en traits):

```rust
trait Fetch {
    async fn fetch(&self, url: &str) -> String;
}

struct Client;

impl Fetch for Client {
    async fn fetch(&self, _url: &str) -> String {
        String::from("ok")
    }
}

fn main() {
    let _client = Client;
}
```

1. `async fn` en traits es estable en Rust 2024 para métodos no genéricos.
2. El future de retorno no se puede nombrar; se usa `impl Future`.
3. Un trait con `async fn` no es object-safe por defecto.
4. Para `dyn`, se usa un método que devuelve `Pin<Box<dyn Future + Send>>` o un
   trait auxiliar.
5. Los bounds `Send` no se añaden automáticamente; se declaran si el executor
   los necesita.

### 50.9 `no_std` y async

1. `core::future::Future` existe en `no_std`.
2. Un executor `no_std` requiere `alloc` para tareas y `Waker`.
3. `async` sin executor solo construye futures; no progresa.
4. `tokio` no es `no_std`; para embebidos se usan `embassy` o `smol`.
5. `Pin` y `Waker` están en `core`.
6. La sección §55 detalla `no_std`.

### 50.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5001` | `awaken` fuera de contexto async | marcar con `dream` |
| `PGS-E5002` | `dream` sin runtime en `grimoire` | añadir `@@tokio::main` o `block_on` |
| `PGS-E5003` | future no `Send` en `spawn` | usar `async move`/`Arc` |
| `PGS-E5004` | `awaken` en closure normal | usar `dream (..) =>` |
| `PGS-E5005` | `async fn` en trait no object-safe | usar `Pin<Box<dyn Future>>` |
| `PGS-E5006` | future no consumido | `awaken`, `spawn` o `drop` |
| `PGS-W5001` | `select!` sin cancelación segura | revisar recursos |
| `PGS-W5002` | runtime no especificado | declarar dependencia |

### 50.11 Criterios de aceptación

- [x] `dream`/`awaken` tienen sintaxis y semántica.
- [x] Futures, `Pin` y `Unpin` están explicados.
- [x] El runtime es explícito y sustituible.
- [x] `Send`/`'static` y cancelación están cubiertos.
- [x] Los ejemplos Rust compilan sin runtime externo.

[↑ Volver al índice](#indice)

<a id="sec-51-concurrencia"></a>
## 51. Concurrencia

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 7 |
| Rust | `thread`, `Arc`, `Mutex`, `RwLock`, atomics, channels |
| Palabras mágicas | `spawn`, `move`, `Send`, `Sync` |
| Depende de | §16, §17, §20, §35, §49 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec51_concurrency.pengu` |

La concurrencia segura se apoya en dos traits: `Send` indica que un valor puede
moverse entre hilos; `Sync` indica que puede compartirse por referencia. El
compilador rechaza los usos que rompen esas garantías.

### 51.1 Hilos

```pengu
grimoire
    bind handle = std.thread.spawn(move () =>
        print("hola desde otro hilo")
    )
    handle.join().unwrap()
```

Rust generado:

```rust
fn main() {
    let handle = std::thread::spawn(move || {
        println!("hola desde otro hilo");
    });
    handle.join().unwrap();
}
```

1. `std.thread.spawn` recibe una closure `FnOnce + Send + 'static`.
2. El closure debe ser `move` si captura valores que no viven en `'static`.
3. `JoinHandle.join()` devuelve `Result<T, Box<dyn Any + Send>>`.
4. Un panic en el hilo se propaga como `Err` en `join`; no se ignora.
5. El hilo principal no espera automáticamente; sin `join`, el programa puede
   terminar antes.
6. `spawn` no comparte el stack; los datos se mueven o se comparten con `Arc`.

### 51.2 Hilos con scope

```pengu
grimoire
    morph total = 0
    std.thread.scope((scope) =>
        scope.spawn(() =>
            total += 1
        )
    )
    print(total)
```

Rust generado:

```rust
fn main() {
    let mut total = 0;
    std::thread::scope(|scope| {
        scope.spawn(|| {
            total += 1;
        });
    });
    println!("{}", total);
}
```

1. `thread::scope` garantiza que todos los hilos terminen antes de salir del
   bloque; permite prestar datos locales.
2. El closure de `scope` recibe un `Scope`; `scope.spawn` acepta préstamos no
   `'static`.
3. Al salir del scope, se hace `join` implícito; un panic se propaga.
4. No se puede devolver una referencia a un dato del scope.
5. `scope` no sustituye a `Arc` cuando los hilos deben sobrevivir al bloque.
6. Los préstamos mutables deben ser disjuntos; el borrow checker lo comprueba.

### 51.3 `Send` y `Sync`

| Tipo | `Send` | `Sync` | Nota |
|---|---|---|---|
| `i32`, `bool`, `f64` | sí | sí | `Copy` |
| `String`, `Vec[T]` | sí | sí | si `T` lo es |
| `Rc[T]` | no | no | conteo no atómico |
| `Arc[T]` | sí | sí | si `T: Send + Sync` |
| `RefCell[T]` | sí | no | mutabilidad interior no thread-safe |
| `Mutex[T]` | sí | sí | si `T: Send` |
| `RwLock[T]` | sí | sí | si `T: Send + Sync` |
| `*const T`/`*mut T` | no | no | raw pointers |
| `Cell[T]` | sí | no | no compartible por referencia |

1. `Send` se comprueba estructuralmente; un `rune` es `Send` si todos sus campos
   lo son.
2. `Sync` permite `&T` entre hilos; `T: Sync` no implica `T: Send`.
3. `Rc`/`RefCell` son de un solo hilo; para compartir se usa `Arc`/`Mutex`.
4. Un tipo con `UnsafeCell` no es `Sync` por defecto.
5. `PhantomData` puede cambiar auto-traits; se documenta.
6. No se implementan `Send`/`Sync` a mano salvo en `curse` con justificación.

### 51.4 `Arc<Mutex<T>>`

```pengu
grimoire
    bind counter = Arc.new(Mutex.new(0))
    morph handles = Vec.new()

    for _ in 0..4
        bind c = Arc.clone(&counter)
        handles.push(std.thread.spawn(move () =>
            morph guard = c.lock().unwrap()
            *guard += 1
        ))

    for handle in handles
        handle.join().unwrap()

    print(*counter.lock().unwrap())
```

Rust generado:

```rust
use std::sync::{Arc, Mutex};
use std::thread;

fn main() {
    let counter = Arc::new(Mutex::new(0));
    let mut handles = Vec::new();

    for _ in 0..4 {
        let c = Arc::clone(&counter);
        handles.push(thread::spawn(move || {
            let mut guard = c.lock().unwrap();
            *guard += 1;
        }));
    }

    for handle in handles {
        handle.join().unwrap();
    }

    println!("{}", *counter.lock().unwrap());
}
```

1. `Arc` comparte el dueño; `Mutex` serializa el acceso.
2. `Arc.clone(&counter)` incrementa el conteo; no copia el valor.
3. `lock()` devuelve `LockResult<MutexGuard<T>>`; `unwrap` propaga un lock
   envenenado.
4. El `MutexGuard` se libera al salir del scope.
5. No se mantiene un guard mientras se espera otro lock; riesgo de deadlock.
6. `RwLock` permite múltiples lectores o un escritor.

### 51.5 `RwLock`

```rust
use std::sync::RwLock;

fn main() {
    let lock = RwLock::new(1);

    {
        let read = lock.read().unwrap();
        println!("{}", *read);
    }

    {
        let mut write = lock.write().unwrap();
        *write += 1;
    }

    println!("{}", *lock.read().unwrap());
}
```

1. `read` permite varios lectores; `write` es exclusivo.
2. Un lector no puede coexistir con un escritor.
3. `RwLock` puede ser más lento que `Mutex` para secciones críticas pequeñas.
4. El lock se envenena si un hilo panica mientras lo tiene.
5. `try_read`/`try_write` no bloquean; se usan para evitar deadlocks.

### 51.6 Canales

```pengu
grimoire
    bind (tx, rx) = std.sync.mpsc.channel()

    std.thread.spawn(move () =>
        tx.send(42).unwrap()
    )

    print(rx.recv().unwrap())
```

Rust generado:

```rust
use std::sync::mpsc;
use std::thread;

fn main() {
    let (tx, rx) = mpsc::channel();

    thread::spawn(move || {
        tx.send(42).unwrap();
    });

    println!("{}", rx.recv().unwrap());
}
```

1. `mpsc` es multi-productor, single-consumidor.
2. `send` falla si el receptor se cerró; `recv` falla si todos los emisores se
   cerraron.
3. El canal es una forma de transferir ownership sin locks.
4. `sync_channel` tiene capacidad limitada y aplica backpressure.
5. Para múltiples consumidores se usa `crossbeam-channel` o un `Mutex` sobre la
   cola.
6. Un canal no garantiza orden entre productores distintos; sí conserva el orden
   de cada productor.

### 51.7 Atómicos y `Ordering`

```pengu
grimoire
    bind count = Arc.new(AtomicUsize.new(0))
    morph handles = Vec.new()

    for _ in 0..4
        bind c = Arc.clone(&count)
        handles.push(std.thread.spawn(move () =>
            c.fetch_add(1, Ordering.SeqCst)
        ))

    for handle in handles
        handle.join().unwrap()

    print(count.load(Ordering::SeqCst))
```

Rust generado:

```rust
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::thread;

fn main() {
    let count = Arc::new(AtomicUsize::new(0));
    let mut handles = Vec::new();

    for _ in 0..4 {
        let c = Arc::clone(&count);
        handles.push(thread::spawn(move || {
            c.fetch_add(1, Ordering::SeqCst);
        }));
    }

    for handle in handles {
        handle.join().unwrap();
    }

    println!("{}", count.load(Ordering::SeqCst));
}
```

| `Ordering` | Uso |
|---|---|
| `Relaxed` | contador sin sincronización adicional |
| `Acquire`/`Release` | publicar/consumir datos |
| `AcqRel` | lectura-escritura atómica |
| `SeqCst` | orden total, el más fácil de razonar |

1. `SeqCst` es el default seguro; los demás se usan con un argumento de
   rendimiento.
2. Un atómico no protege un `rune` completo; para eso se usa `Mutex`.
3. `fetch_add` devuelve el valor anterior.
4. Un `Ordering` más débil puede romper la relación happens-before.
5. Los atómicos no evitan ABA; para eso se usa una versión o un lock.

### 51.8 `OnceLock`, `LazyLock` y `thread_local`

```rust
use std::sync::{LazyLock, OnceLock};

static CONFIG: OnceLock<String> = OnceLock::new();
static DATA: LazyLock<Vec<i32>> = LazyLock::new(|| vec![1, 2, 3]);

fn main() {
    CONFIG.set(String::from("pengu")).unwrap();
    println!("{}", CONFIG.get().unwrap());
    println!("{:?}", *DATA);
}
```

1. `OnceLock` se inicializa una vez; `set` devuelve error si ya estaba.
2. `LazyLock` inicializa en el primer acceso; es thread-safe.
3. `thread_local` crea una copia por hilo; no se comparte.
4. `static mut` no se usa; §6 lo prohíbe.
5. `LazyLock` requiere Rust 1.80+; el MSRV es 1.85.

```rust
use std::cell::RefCell;

thread_local! {
    static COUNTER: RefCell<u32> = RefCell::new(0);
}

fn main() {
    COUNTER.with(|c| *c.borrow_mut() += 1);
    COUNTER.with(|c| println!("{}", c.borrow()));
}
```

### 51.9 Rayon y paralelismo de datos

Rayon es una crate externa para paralelismo de datos. No forma parte del
lenguaje:

```toml
[dependencies]
rayon = "1.10"
```

1. `par_iter` paraleliza un iterador; el resultado conserva el orden.
2. El closure debe ser `Send + Sync`.
3. No se usa Rayon para blocking I/O; para eso se usa async o un pool.
4. El coste de sincronización puede superar el beneficio en cargas pequeñas.
5. Un `Mutex` dentro de `par_iter` serializa y anula el paralelismo.

### 51.10 Deadlocks, data races y `UnsafeCell`

1. Un **data race** es un acceso concurrente no sincronizado con al menos una
   escritura; Rust lo impide en código seguro.
2. Un **deadlock** no es un data race: dos hilos esperan locks en orden circular.
3. Prevención: un orden global de locks, `try_lock`, timeouts y secciones
   críticas cortas.
4. `UnsafeCell` es la base de la mutabilidad interior; usarlo mal rompe
   `Sync`.
5. `UnsafeCell` no es `Sync`; envolverlo en `Mutex` lo hace seguro.
6. Un `MutexGuard` no se envía a otro hilo sin comprobar el tipo.
7. Un panic con un lock tomado lo envenena; se maneja con `unwrap_or_else`.

### 51.11 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5101` | `spawn` con closure no `Send` | usar `move`/`Arc` |
| `PGS-E5102` | `spawn` con préstamo no `'static` | usar `scope` o mover |
| `PGS-E5103` | `Rc`/`RefCell` compartido entre hilos | usar `Arc`/`Mutex` |
| `PGS-E5104` | `join` ignorado | manejar `Result` |
| `PGS-E5105` | lock mantenido entre `await` | reducir el scope |
| `PGS-E5106` | `Ordering` incompatible con la operación | revisar el protocolo |
| `PGS-W5101` | `Mutex` en sección crítica larga | reducir |
| `PGS-W5102` | `thread_local` con estado grande | revisar |

### 51.12 Criterios de aceptación

- [x] Hilos, `spawn`, `join` y scoped threads están definidos.
- [x] `Send`/`Sync` tienen tabla y ejemplo de error.
- [x] `Arc<Mutex<T>>`, `RwLock` y canales tienen ejemplo.
- [x] Atómicos y `Ordering` están cubiertos.
- [x] Deadlocks y data races se distinguen.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="part-8"></a>
## Parte VIII — Sistemas e interop

<a id="sec-52-unsafe"></a>
## 52. Unsafe (`curse`)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 8 |
| Rust | `unsafe`, raw pointers, unions, `transmute` |
| Palabras mágicas | `curse`, `chimera`, `transmute` |
| Depende de | §16–§21, §28, §31, §53 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec52_unsafe.pengu` |

`curse` es la palabra para `unsafe`. No es un modo global ni una puerta
trasera: es un contrato local que el programador firma y justifica. Todo
`curse` debe tener un comentario `-- SAFETY:` que explique por qué se cumple el
invariante.

### 52.1 `curse` en funciones y bloques

```pengu
curse read = (p: *const Int) -> Int
    -- SAFETY: el llamador garantiza que `p` apunta a un Int válido.
    *p

grimoire
    bind x = 42
    bind p = &raw const x
    bind value = curse
        -- SAFETY: `p` apunta a `x`, que sigue vivo.
        *p
    print(value)
```

Rust generado:

```rust
unsafe fn read(p: *const i32) -> i32 {
    // SAFETY: el llamador garantiza que `p` apunta a un Int válido.
    unsafe { *p }
}

fn main() {
    let x = 42;
    let p = &raw const x;
    let value = unsafe {
        // SAFETY: `p` apunta a `x`, que sigue vivo.
        *p
    };
    println!("{}", value);
}
```

1. `curse name = (...) -> T` genera `unsafe fn`.
2. Un bloque `curse` genera `unsafe { ... }` y puede contener varias
   operaciones.
3. Llamar a una función `curse` requiere un contexto `curse`.
4. Un bloque `curse` no cambia el tipo de su última expresión.
5. `curse` no silencia el borrow checker; solo habilita operaciones marcadas
   como unsafe.
6. Un `curse` sin `-- SAFETY:` es warning (`PGS-W5201`).
7. `@@deny(unsafe_op_in_unsafe_fn)` obliga a envolver cada operación unsafe
   dentro de una función unsafe; es la política recomendada.

### 52.2 Punteros raw

| Operación | Rust | Seguridad |
|---|---|---|
| `&raw const x` | `&raw const x` | crear el puntero es seguro |
| `&raw mut x` | `&raw mut x` | crear el puntero es seguro |
| `*p` (lectura) | `*p` | requiere `curse` |
| `*p = v` (escritura) | `*p = v` | requiere `curse` y exclusividad |
| `p.is_null()` | `is_null()` | seguro |
| `p.add(n)` | `add(n)` | requiere provenance y bounds |
| `p.cast[T]()` | `cast::<T>()` | requiere alineación y tamaño |

1. Un puntero raw no tiene lifetime ni garantía de validez.
2. `&raw` evita crear una referencia temporal; es la forma recomendada.
3. `*const T`/`*mut T` no son `Send` ni `Sync`.
4. La aritmética de punteros debe quedar dentro del mismo allocation.
5. Un puntero nulo no se dereferencia; se comprueba con `is_null`.
6. La provenance (de qué allocation proviene) importa; no se inventa un
   puntero a partir de un entero salvo en FFI/OS con contrato explícito.
7. Un `&mut T` y un `*mut T` al mismo dato no pueden usarse a la vez sin un
   protocolo.

### 52.3 `chimera` (uniones)

```pengu
@@repr(C)
chimera IntOrFloat
    i: Int
    f: Float

grimoire
    bind value = IntOrFloat(i: 42)
    bind as_int = curse
        -- SAFETY: se escribió el campo `i`, se lee `i`.
        value.i
    print(as_int)
```

Rust generado:

```rust
#[repr(C)]
union IntOrFloat {
    i: i32,
    f: f32,
}

fn main() {
    let value = IntOrFloat { i: 42 };
    let as_int = unsafe {
        // SAFETY: se escribió el campo `i`, se lee `i`.
        value.i
    };
    println!("{}", as_int);
}
```

1. `chimera` genera `union`; todos los campos deben ser `Copy` o
   `ManuallyDrop`.
2. Escribir un campo es seguro; leerlo requiere `curse`.
3. Leer un campo distinto del último escrito solo es válido si los bytes son
   una representación válida del tipo leído; en caso contrario es UB.
4. Una unión no sabe qué variante está activa; se necesita una etiqueta
   externa.
5. `chimera` no reemplaza a `enchanting`; se usa para layout/FFI.
6. `MaybeUninit` es preferible para inicialización diferida.

### 52.4 `transmute`

```pengu
curse bits = (value: Float) -> U64
    -- SAFETY: `Float` y `U64` miden 8 bytes y la representación es estable.
    transmute(value)
```

Rust generado:

```rust
unsafe fn bits(value: f64) -> u64 {
    // SAFETY: `f64` y `u64` miden 8 bytes y la representación es estable.
    unsafe { std::mem::transmute(value) }
}
```

1. `transmute` exige que origen y destino tengan el mismo tamaño.
2. No comprueba validez: un `u32` convertido en `bool` puede ser inválido.
3. Para números, se prefieren `to_bits`/`from_bits`.
4. Para punteros, se prefiere `cast` y un contrato de provenance.
5. `transmute` entre tipos con drop puede filtrar recursos; se usa
   `ManuallyDrop`.
6. `transmute` no es una conversión de negocio; es una operación de bits.
7. `transmute` en genéricos puede fallar en compilación si los tamaños no
   coinciden.

### 52.5 `MaybeUninit`, `ManuallyDrop` y `UnsafeCell`

```rust
use std::mem::MaybeUninit;

fn main() {
    let mut value = MaybeUninit::<i32>::uninit();
    value.write(42);
    let value = unsafe { value.assume_init() };
    println!("{}", value);
}
```

1. `MaybeUninit[T]` representa un `T` que puede no estar inicializado.
2. `write` inicializa; `assume_init` es `curse` y exige que esté inicializado.
3. `assume_init_read` mueve el valor; `assume_init_drop` lo dropea.
4. `ManuallyDrop[T]` evita el drop automático; se usa para controlar el
   momento exacto.
5. `ManuallyDrop` no filtra por sí solo: hay que llamar a `drop` manualmente.
6. `UnsafeCell[T]` es la única forma legal de mutar a través de `&T`; la
   seguridad la aporta el envoltorio (`Cell`, `Mutex`, etc.).
7. `UnsafeCell` no es `Sync`; compartirlo sin sincronización es data race.

```rust
use std::cell::UnsafeCell;

struct Cell {
    value: UnsafeCell<i32>,
}

fn main() {
    let cell = Cell { value: UnsafeCell::new(1) };
    unsafe {
        *cell.value.get() += 1;
    }
    println!("{}", unsafe { *cell.value.get() });
}
```

### 52.6 Aliasing y soundness

1. Un `&mut T` es exclusivo mientras vive; no puede coexistir con otro acceso.
2. Un `&T` permite lecturas concurrentes; no escrituras.
3. Dos `&mut T` al mismo dato son UB aunque no se usen a la vez.
4. Un `&T` y un `*mut T` pueden coexistir solo si no se escribe mientras el
   `&T` está vivo.
5. `UnsafeCell` suspende la garantía de inmutabilidad, no la de exclusividad
   lógica.
6. Un `curse` no puede crear una referencia inválida, desalineada o nula.
7. La soundness es responsabilidad del código seguro que envuelve al `curse`;
   la API pública debe ser segura.

Checklist de soundness:

- [ ] El puntero apunta a un objeto vivo y alineado.
- [ ] El tamaño y el tipo coinciden.
- [ ] No hay aliasing mutable incompatible.
- [ ] El lifetime del préstamo cubre el uso.
- [ ] La inicialización está completa antes de leer.
- [ ] El drop se ejecuta exactamente una vez.
- [ ] El tipo no contiene valores inválidos.
- [ ] La concurrencia está sincronizada.

### 52.7 `curse` en traits

```pengu
curse pact UnsafeRead
    read = (@, p: *const Int) -> Int
```

Rust generado:

```rust
unsafe trait UnsafeRead {
    fn read(&self, p: *const i32) -> i32;
}
```

1. `curse pact` genera `unsafe trait`.
2. Un `ritual` de un trait unsafe debe ser `curse ritual`.
3. Un trait unsafe no hace unsafe a sus métodos por sí solo; cada método
   declara su propio contrato.
4. La implementación debe documentar por qué cumple el contrato.
5. Un trait unsafe no se puede implementar en código seguro.

### 52.8 Inline assembly

```rust
fn main() {
    unsafe {
        core::arch::asm!("nop");
    }
    println!("asm ok");
}
```

1. `asm!` y `global_asm!` son macros de Rust; se usan dentro de `curse`.
2. La sintaxis es específica de la arquitectura; no es portable.
3. Los registros, clobbers y opciones deben declararse.
4. `asm!` no es una optimización mágica; puede impedir optimizaciones.
5. Para código portátil, se usan intrínsecos o FFI.
6. `global_asm!` se usa a nivel de módulo; requiere `curse` y una sección
   explícita.

### 52.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5201` | operación unsafe fuera de `curse` | envolver en `curse` |
| `PGS-E5203` | `transmute` con tamaños distintos | usar una conversión válida |
| `PGS-E5204` | `chimera` con campo no `Copy` | usar `ManuallyDrop` |
| `PGS-E5205` | `assume_init` sin inicializar | escribir antes |
| `PGS-E5206` | `&mut` aliasado | separar los préstamos |
| `PGS-W5201` | `curse` sin comentario SAFETY | documentar |
| `PGS-W5202` | `curse` innecesario | usar código seguro |

### 52.10 Criterios de aceptación

- [x] `curse` cubre funciones, bloques y traits.
- [x] Punteros raw, uniones, `transmute` y `MaybeUninit` están definidos.
- [x] El checklist de soundness es explícito.
- [x] La asm está limitada a `curse`.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-53-ffi"></a>
## 53. FFI e interop con Rust

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 8 |
| Rust | `extern "C"`, `#[unsafe(no_mangle)]`, `#[repr(C)]`, `CStr`/`CString` |
| Palabras mágicas | `foreign`, `@@link`, `@@no_mangle` |
| Depende de | §28, §29, §32, §52 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec53_ffi.pengu` |

PenguScript compila a Rust, así que la interop tiene dos direcciones:

1. **Llamar código externo** (C, Rust, sistema) desde PenguScript.
2. **Exponer código PenguScript** a C u otros lenguajes.

La regla central es que el ABI no se adivina: se declara con `foreign`.

### 53.1 Bloques `foreign`

```pengu
foreign "C"
    abs = (x: Int) -> Int

grimoire
    bind value = curse
        -- SAFETY: `abs` recibe un i32 y no retiene el puntero.
        abs(-7)
    print(value)
```

Rust generado:

```rust
unsafe extern "C" {
    fn abs(x: i32) -> i32;
}

fn main() {
    let value = unsafe {
        // SAFETY: `abs` recibe un i32 y no retiene el puntero.
        abs(-7)
    };
    println!("{}", value);
}
```

1. `foreign "C"` abre un bloque de declaraciones sin cuerpo.
2. Cada línea `name = (params) -> Ret` genera una función `extern`.
3. El bloque completo genera `unsafe extern "C" { ... }` en Rust 2024.
4. Llamar una función `foreign` requiere `curse`.
5. El ABI se escribe como string: `"C"`, `"C-unwind"`, `"system"`,
   `"stdcall"`, `"fastcall"`, `"win64"`, `"sysv64"`.
6. `foreign` no implementa la función; solo declara su firma.
7. Una firma `foreign` no puede tener cuerpo.
8. Las funciones `foreign` no son `unsafe fn` por sí mismas en Rust; el
   bloque externo es unsafe y la llamada se envuelve en `curse`.

### 53.2 Exportar funciones PenguScript

```pengu
@@no_mangle
unveil foreign "C" add = (a: Int, b: Int) -> Int
    a + b
```

Rust generado:

```rust
#[unsafe(no_mangle)]
pub extern "C" fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

1. `foreign "C" name = (params) -> Ret` con cuerpo define una función
   exportada con ABI C.
2. `unveil` la hace `pub`; sin `unveil` el símbolo no se exporta.
3. `@@no_mangle` evita el mangling de Rust; el símbolo se llama `add`.
4. `@@export_name("...")` cambia el nombre del símbolo.
5. `@@link_name("...")` cambia el nombre que se busca al importar.
6. Una función exportada no puede entrar en pánico a través del borde FFI;
   se captura o se marca `"C-unwind"`.
7. Los tipos del borde deben ser `#[repr(C)]`.
8. Los strings no cruzan el borde como `String`; se usa `*const c_char`.

### 53.3 Tipos compatibles con C

```pengu
@@repr(C)
rune PointC
    x: Float
    y: Float
```

Rust generado:

```rust
#[repr(C)]
struct PointC {
    x: f64,
    y: f64,
}
```

| PenguScript | C | Rust |
|---|---|---|
| `I8`/`U8` | `int8_t`/`uint8_t` | `i8`/`u8` |
| `I16`/`U16` | `int16_t`/`uint16_t` | `i16`/`u16` |
| `I32`/`U32` | `int32_t`/`uint32_t` | `i32`/`u32` |
| `I64`/`U64` | `int64_t`/`uint64_t` | `i64`/`u64` |
| `Isize`/`Usize` | `intptr_t`/`uintptr_t` | `isize`/`usize` |
| `Float` | `double` | `f64` |
| `Bool` | `bool` | `bool` |
| `*const T`/`*mut T` | `const T*`/`T*` | `*const T`/`*mut T` |
| `chimera` | `union` | `union` |

1. `@@repr(C)` es obligatorio para structs, enums y uniones que cruzan el
   borde.
2. Un `enchanting` con `@@repr(C)` debe tener campos compatibles con C.
3. Un enum con datos no es un entero C; se usa una struct etiquetada.
4. `Bool` es `bool` de C99; si el header usa `int`, se declara `Int`.
5. `Str` no es `char*`; se usa `*const c_char` o `CStr`.

### 53.4 Tipos opacos

```pengu
@@repr(C)
rune FILE
    _private: [U8; 0]

foreign "C"
    fopen = (path: *const c_char, mode: *const c_char) -> *mut FILE
    fclose = (file: *mut FILE) -> Int
```

1. Un tipo opaco se declara con un campo privado de tamaño cero.
2. El código PenguScript nunca lee `_private`; solo pasa `*mut FILE`.
3. La definición real vive en C.
4. `fopen` puede devolver null; se comprueba antes de usar.
5. `fclose` consume el puntero; no se usa después.
6. Un tipo opaco no implementa `Drop` automático; el recurso se cierra con
   la función externa.

### 53.5 Strings C

```pengu
bind message = c"hello"

bind owned = CString.new("pengu")
bind ptr = owned.as_ptr()
```

Rust generado:

```rust
fn example() -> Result<(), Box<dyn std::error::Error>> {
    let message = c"hello";
    let owned = std::ffi::CString::new("pengu")?;
    let ptr = owned.as_ptr();
    let _ = (message, ptr);
    Ok(())
}
```

1. `c"..."` produce `&CStr`; no copia ni asigna.
2. `CString.new(text)` produce un buffer con terminador `NUL`.
3. `CString.new` falla si el texto contiene `NUL`; devuelve `!CString`.
4. `CStr.from_ptr(p)` es `curse` y exige que `p` sea un C string válido.
5. `CStr.to_str()` devuelve `!&Str` por UTF-8 inválido.
6. Un `CString` debe vivir mientras se use su `as_ptr()`.
7. No se libera un `CString` con `free`; lo hace `Drop`.

```rust
use std::ffi::CStr;

fn main() {
    let message = c"hello";
    let len = unsafe { strlen(message.as_ptr()) };
    println!("{} {}", len, message.to_str().unwrap());
}

unsafe extern "C" {
    fn strlen(s: *const std::ffi::c_char) -> usize;
}
```

### 53.6 Llamar a Rust desde PenguScript

Un crate Rust puede exponer funciones `extern "C"` y PenguScript las declara
con `foreign`:

```pengu
foreign "C"
    pengu_add = (a: Int, b: Int) -> Int
```

1. El crate Rust debe exportar `#[unsafe(no_mangle)] pub extern "C" fn`.
2. El enlace se declara en `Tome.toml` con `[dependencies]`.
3. Si la función vive en una librería estática, se añade `@@link`.
4. Los tipos deben ser `#[repr(C)]` o primitivos C.
5. Los errores se convierten en códigos; no se propaga un `Result` Rust.
6. Las panics se capturan antes de cruzar el borde.

### 53.7 Enlace y símbolos

```pengu
@@link(name = "m")
foreign "C"
    cos = (x: Float) -> Float
```

Rust generado:

```rust
#[link(name = "m")]
unsafe extern "C" {
    fn cos(x: f64) -> f64;
}
```

1. `@@link(name = "...")` enlaza una librería nativa.
2. `@@link_name("...")` cambia el símbolo importado.
3. `@@export_name("...")` cambia el símbolo exportado.
4. `@@no_mangle` desactiva el mangling.
5. `@@link_section("...")` coloca el símbolo en una sección.
6. `@@used` evita que el linker elimine el símbolo.
7. Los nombres no pueden colisionar entre crates.

### 53.8 ABI y unwinding

1. `"C"` no permite unwinding a través del borde; una panic iniciada dentro
   de la función `extern "C"` aborta el proceso (Rust 1.71+).
2. `"C-unwind"` permite unwinding controlado; se usa solo si ambos lados lo
   soportan.
3. `"system"` usa el ABI del sistema (`stdcall` en Windows x86, `C` en el
   resto).
4. Los enteros deben tener tamaño explícito; `Int` es `i32`, no `long`.
5. Los punteros pueden ser nulos; se documenta si lo son.
6. Las callbacks deben ser `extern "C"` y no capturar estado no `Send` sin
   contrato.
7. Un `struct` con `Drop` no se pasa por valor a C sin `ManuallyDrop`.

### 53.9 bindgen y cbindgen

1. **bindgen** genera declaraciones PenguScript a partir de headers C; el
   resultado se revisa y se marca con `@@repr(C)`.
2. **cbindgen** genera headers C a partir de las funciones `foreign`
   exportadas.
3. Las herramientas no forman parte del compilador; son pasos de build.
4. El header generado es la fuente de verdad del ABI.
5. Los nombres generados se pueden ajustar con `@@export_name`.
6. No se confía en bindgen para tipos opacos; se revisan a mano.

### 53.10 Bloque `rust` como escape auditado

```pengu
rust
    include!(concat!(env!("OUT_DIR"), "/bindings.rs"));
```

1. El bloque `rust` inserta tokens Rust sin traducir.
2. Se usa para bindings generados, no para lógica de negocio.
3. Todo bloque `rust` debe revisarse y marcarse en el source map.
4. No se permite en ejemplos básicos; es una herramienta de interop.
5. El código insertado sigue las reglas de Rust 2024, incluidos
   `#[unsafe(...)]`.
6. Un bloque `rust` no puede declarar globals PenguScript.

### 53.11 wasm

1. `wasm32-unknown-unknown` no tiene `std` completo; se usa `core`/`alloc`.
2. `wasm32-wasip1` tiene un sistema de archivos virtual y `std` disponible; las APIs dependen de WASI.
3. `wasm-bindgen` expone funciones con `@@wasm_bindgen`; el atributo lo
   aporta el proc macro, no el núcleo.
4. Los tipos JS (`JsValue`) se manejan como tipos opacos.
5. El tamaño y la alineación de `usize` cambian; se usan tipos explícitos.
6. Las funciones exportadas usan `foreign "C"` o `wasm-bindgen`.
7. El hilo único es el default; `wasm-bindgen-rayon` requiere features.

### 53.12 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5301` | `foreign` sin ABI | añadir `"C"` u otro ABI |
| `PGS-E5302` | tipo no `repr(C)` en el borde | añadir `@@repr(C)` |
| `PGS-E5303` | llamada a `foreign` sin `curse` | envolver en `curse` |
| `PGS-E5304` | `foreign` con cuerpo y sin `foreign "C"` | declarar el ABI |
| `PGS-E5305` | `CString` con `NUL` | validar el texto |
| `PGS-E5306` | `link_name` duplicado | usar un alias |
| `PGS-W5301` | puntero potencialmente nulo | comprobar `is_null` |
| `PGS-W5302` | panic a través de FFI | capturar o `"C-unwind"` |

### 53.13 Criterios de aceptación

- [x] `foreign` cubre importación y exportación.
- [x] Los tipos del borde tienen una tabla C/Rust.
- [x] Strings, tipos opacos y enlace están definidos.
- [x] El ABI y el unwinding están documentados.
- [x] El bloque `rust` queda como escape auditado.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-54-const-eval"></a>
## 54. Const eval

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 8 |
| Rust | `const`, `const fn`, `const {}`, const generics |
| Palabras mágicas | `sigil`, `eternal`, `relic` |
| Depende de | §6, §18, §33, §52 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec54_const_eval.pengu` |

PenguScript evalúa en compilación todo lo que pueda demostrarse puro. Hay tres
herramientas distintas:

| Herramienta | Declara | Se evalúa | Rust |
|---|---|---|---|
| `sigil` | una constante | en compilación | `const` |
| `eternal` | una función/bloque const | en compilación o runtime | `const fn` / `const {}` |
| `relic` | un static inmutable | inicializador const | `static` |

No hay `const` como palabra clave: `sigil` es el nombre mágico.

### 54.1 `sigil`: constantes

```pengu
sigil LIMIT: Usize = 64
sigil MASK: U64 = (1 << 8) - 1
sigil NAME: &'static Str = "pengu"
```

Rust generado:

```rust
const LIMIT: usize = 64;
const MASK: u64 = (1 << 8) - 1;
const NAME: &str = "pengu";
```

1. `sigil` declara una constante de módulo; no es una variable global.
2. El tipo es explícito; no se infiere en items.
3. El inicializador debe ser una expresión const.
4. `sigil` se puede usar en tipos, arrays, const generics y patrones.
5. `sigil` no se puede reasignar ni tomar `&mut`.
6. `unveil sigil` lo hace visible fuera del módulo.
7. Un `sigil` no tiene dirección estable; para eso se usa `relic`.

### 54.2 `eternal`: funciones const

```pengu
eternal square = (x: Int) -> Int
    x * x

eternal checked = (n: Usize) -> Usize
    if n == 0 then
        panic("zero")
    else
        n
```

Rust generado:

```rust
const fn square(x: i32) -> i32 {
    x * x
}

const fn checked(n: usize) -> usize {
    if n == 0 {
        panic!("zero")
    } else {
        n
    }
}
```

1. `eternal` genera `const fn`; se puede llamar en runtime y en contexto const.
2. El cuerpo solo usa operaciones const.
3. `panic` con un literal es const; el formato con argumentos no lo es.
4. `eternal` no puede ser `dream`, `curse` ni `foreign`.
5. `eternal` se limita a funciones y bloques const; los traits con métodos const están diferidos (§66.2).
6. La recursión const está limitada por el evaluation limit de rustc.
7. `eternal` no implica `inline`; se combina con `@@inline`.

### 54.3 Bloques `eternal`

```pengu
bind answer = eternal
    square(8) + 1
```

Rust generado:

```rust
const fn square(x: i32) -> i32 {
    x * x
}

let answer = const { square(8) + 1 };
```

1. Un bloque `eternal` evalúa su cuerpo en compilación.
2. El tipo se infiere del contexto.
3. Si el cuerpo no es const, error `PGS-E5401`.
4. Un bloque `eternal` puede usar `sigil` y `eternal` functions.
5. No puede usar heap, I/O, `println` ni aleatoriedad.
6. El bloque no crea un scope de runtime; no hay variables mutables.
7. `eternal` como prefijo de función y como bloque se distinguen por la
   posición: `eternal name = ...` vs `eternal` al inicio de una expresión.

### 54.4 Const generics

```pengu
rune Buffer[const N: Usize]
    data: [U8; N]

bind buf = Buffer[4](data: [0; 4])
```

Rust generado:

```rust
struct Buffer<const N: usize> {
    data: [u8; N],
}

let buf = Buffer::<4> { data: [0; 4] };
```

1. `[const N: Usize]` declara un parámetro const.
2. `N` se usa en tipos de array y en expresiones const.
3. El argumento se escribe `Buffer[4]` (turbofish de tipo).
4. Los const generics no tienen defaults en PenguScript v1.
5. El tipo debe ser entero, `Bool` o `Char`; `Float` no.
6. Las operaciones sobre `N` deben ser const y no desbordar.
7. Un const generic no puede depender de un tipo genérico.

### 54.5 `relic`: statics inmutables

```pengu
relic TABLE: [Int; 3] = [1, 2, 3]
relic START: Int = compute_start()

eternal compute_start = () -> Int
    1
```

Rust generado:

```rust
static TABLE: [i32; 3] = [1, 2, 3];
static START: i32 = compute_start();

const fn compute_start() -> i32 {
    1
}
```

1. `relic` genera `static`, no `const`.
2. El inicializador debe ser const.
3. `relic` tiene dirección estable y vive todo el programa.
4. `relic` es inmutable; no se puede `morph`.
5. `static mut` no existe en PenguScript; se usa `@@shared`.
6. `@@thread_local relic` genera un `thread_local!` con acceso por closure.
7. Un `relic` puede ser `unveil`.

### 54.6 Inicialización perezosa

```pengu
relic CACHE: OnceLock[Int] = OnceLock.new()

grimoire
    CACHE.set(42).unwrap()
    print(CACHE.get().unwrap())
```

Rust generado:

```rust
use std::sync::OnceLock;

static CACHE: OnceLock<i32> = OnceLock::new();

fn main() {
    CACHE.set(42).unwrap();
    println!("{}", CACHE.get().unwrap());
}
```

1. `OnceLock.new()` es const; el valor se inicializa en runtime.
2. `LazyLock.new(|| ...)` inicializa en el primer acceso.
3. `OnceLock` y `LazyLock` no son const-eval; son estado global seguro.
4. `@@shared` sigue siendo la forma de mutabilidad global explícita.
5. Un `relic` normal no se puede mutar; `OnceLock` encapsula la mutación.
6. `LazyLock` puede capturar solo lo que sea `Send + Sync` para un static.
7. La inicialización perezosa no debe esconder efectos costosos.

```rust
use std::sync::LazyLock;

static CONFIG: LazyLock<i32> = LazyLock::new(|| 7);

fn main() {
    println!("{}", *CONFIG);
}
```

### 54.7 Const panic

```rust
const fn checked(n: usize) -> usize {
    if n == 0 {
        panic!("zero")
    } else {
        n
    }
}

fn main() {
    println!("{}", checked(5));
}
```

1. `panic!` con un string literal es const.
2. `panic!` con formato (`{}`) no es const.
3. `assert!` con condición const es const; el mensaje debe ser literal.
4. Una panic const falla la compilación si se evalúa en const.
5. En runtime, una `const fn` que panic se comporta como una panic normal.
6. No se usa `panic` para validar entrada de usuario en const.

### 54.8 Límites de const eval

| Operación | ¿Const? | Nota |
|---|---|---|
| enteros, bools, chars | sí | aritmética y comparaciones |
| floats básicos | sí | sin `sqrt`/`sin` estables |
| arrays, tuples, structs | sí | si sus campos lo son |
| `if`/`match`/`loop`/`while` | sí | sin `for` |
| `panic!` literal | sí | sin formato |
| `size_of`/`align_of` | sí | `std::mem` |
| `transmute` | limitado | mismos tamaños; revisar |
| `Vec`/`String`/`Box` | no | heap |
| `println!`/I/O | no | efectos |
| `dyn Trait` | no | despacho dinámico |
| métodos de trait | no | salvo traits const inestables |
| `for` | no | usar `while`/`loop` |

1. La evaluación const tiene un límite de pasos; un bucle infinito es error.
2. No se permite asignación a memoria heap.
3. No se permite `Drop` no const.
4. No se permite lanzar una panic con formato.
5. Los traits const son inestables; se listan en §66.
6. La evaluación const no debe depender de la plataforma si el valor se usa
   en tipos.
7. Un `sigil` grande aumenta el binario; se prefiere `relic` para datos
   grandes.

### 54.9 `sigil` vs `relic` vs `eternal`

| Necesidad | Usar |
|---|---|
| valor escalar conocido en compilación | `sigil` |
| tabla/array grande con dirección | `relic` |
| función pura reutilizable en const | `eternal` |
| cálculo const local | bloque `eternal` |
| inicialización en runtime | `OnceLock`/`LazyLock` |
| mutabilidad global | `@@shared relic` |

### 54.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5401` | operación no const en `sigil`/`eternal` | usar una operación const |
| `PGS-E5402` | `static mut` | `@@shared` + `Mutex` |
| `PGS-E5403` | const generic inválido | usar entero/`Bool`/`Char` |
| `PGS-E5404` | heap en const | mover a runtime |
| `PGS-E5405` | `panic!` con formato | usar literal |
| `PGS-E5406` | recursión const infinita | añadir caso base |
| `PGS-E5407` | `?` en const | usar `match`/`if` |
| `PGS-W5401` | `sigil` muy grande | usar `relic` |
| `PGS-W5402` | `sigil` que debería ser `eternal` | extraer función |

### 54.11 Criterios de aceptación

- [x] `sigil`, `eternal` y `relic` están diferenciados.
- [x] Los const generics y los bloques const están definidos.
- [x] La tabla de límites const es explícita.
- [x] `static mut` está prohibido.
- [x] `OnceLock`/`LazyLock` se distinguen de const eval.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-55-no-std"></a>
## 55. `no_std`, embebidos y wasm

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 8 |
| Rust | `#![no_std]`, `core`, `alloc`, `#[panic_handler]`, `#[global_allocator]` |
| Palabras mágicas | `@@no_std`, `@@panic_handler`, `@@global_allocator` |
| Depende de | §3, §6, §51, §53 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec55_no_std.pengu` |

PenguScript puede compilar sin `std`. El subconjunto `core` está siempre
disponible; `alloc` solo si se declara un allocator. El objetivo es que el
mismo lenguaje sirva para sistemas, embebidos y wasm sin un runtime propio.

### 55.1 `@@no_std`

```pengu
@@no_std

unveil add = (a: Int, b: Int) -> Int
    a + b
```

Rust generado:

```rust
#![no_std]

pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

1. `@@no_std` debe estar en la raíz del crate (`main.pengu`/`lib.pengu`).
2. Desactiva `std`; deja `core` y, si se declara, `alloc`.
3. No se puede usar `std::` en un crate `no_std`.
4. `print`, `Vec`, `String` y `HashMap` requieren `alloc` o `std`.
5. `@@no_std` no desactiva el borrow checker ni los checks de seguridad.
6. Un crate `no_std` puede depender de crates `no_std`.
7. `@@no_std` es incompatible con `grimoire` de runtime normal; se usa una
   entry point del target.

### 55.2 `core` y `alloc`

| Necesidad | Crate | Ejemplo |
|---|---|---|
| tipos primitivos, `Option`, `Result` | `core` | `Option[Int]` |
| slices, arrays, iteradores | `core` | `&[U8]` |
| `fmt`, `cmp`, `ops` | `core` | `Display`, `Add` |
| `Vec`, `String`, `Box`, `Rc` | `alloc` | `Vec[U8]` |
| `HashMap`, `File`, `TcpStream` | `std` | no en `no_std` |

1. `core` no asigna memoria.
2. `alloc` requiere un allocator global.
3. `alloc` no incluye `HashMap`; se usa `alloc::collections::BTreeMap`.
4. `std` reexporta `core` y `alloc`.
5. Un crate `no_std` puede usar `alloc` con `extern crate alloc`.
6. Los iteradores de `core` son los mismos que los de `std`.
7. `format!` requiere `alloc`; `write!` puede usar `core::fmt::Write`.

```rust
#![no_std]

extern crate alloc;

use alloc::vec::Vec;

pub fn squares(n: usize) -> Vec<usize> {
    (0..n).map(|x| x * x).collect()
}
```

### 55.3 Panic handler

```pengu
@@no_std

@@panic_handler
panic = (info: &PanicInfo) -> !
    -- SAFETY: no hay runtime; se detiene el core.
    loop
```

Rust generado:

```rust
#![no_std]

use core::panic::PanicInfo;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {}
}
```

1. Un binario `no_std` necesita exactamente un `#[panic_handler]`.
2. Una librería `no_std` no lo necesita; el binario final lo aporta.
3. El handler debe ser `-> !` y no puede retornar.
4. En embebidos, suele reiniciar, hacer `udf` o escribir en un puerto.
5. En wasm, puede llamar a `unreachable`.
6. No se puede usar `println!` dentro del handler si no hay I/O.
7. `@@panic_handler` se marca con `@@deny(unconditional_panic)` si el cuerpo
   puede entrar en pánico.

### 55.4 Allocator

```pengu
@@global_allocator
relic ALLOC: System = System
```

Rust generado:

```rust
#[global_allocator]
static ALLOC: std::alloc::System = std::alloc::System;
```

1. `@@global_allocator` marca el allocator del crate.
2. Solo puede haber uno.
3. En `no_std`, se implementa `GlobalAlloc` o se usa un crate como `linked_list_allocator`.
4. El allocator debe ser seguro para todos los hilos o declarar su política.
5. `alloc` sin allocator falla en el link.
6. Un allocator de embebido suele usar un heap estático.
7. `System` solo existe con `std`; el ejemplo es para un crate con `std`.

### 55.5 Entry point y target

```pengu
@@no_std
@@no_main

@@panic_handler
panic = (info: &PanicInfo) -> !
    loop

@@entry
start = () -> !
    loop
```

Rust generado (`#[entry]` lo aporta el crate del target; aquí se usa
`#[unsafe(no_mangle)]` para que el bloque compile aislado):

```rust
#![no_std]
#![no_main]

use core::panic::PanicInfo;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {}
}

#[unsafe(no_mangle)]
pub extern "C" fn start() -> ! {
    loop {}
}
```

1. `@@no_main` desactiva el `main` de Rust.
2. `@@entry` lo aporta el crate del target (`cortex-m-rt`, `riscv-rt`,
   `wasm-bindgen`, etc.); no es un atributo del núcleo.
3. El símbolo de entrada debe ser `extern "C"` y `-> !` en embebidos.
4. El linker script define Flash/RAM y el vector table.
5. `start` no retorna; si retorna, el comportamiento es indefinido.
6. En wasm, la entry la genera `wasm-bindgen` o el runtime JS.
7. En un SO, `grimoire` sigue siendo la entrada normal.

### 55.6 Target triples

| Target | Uso | `std` |
|---|---|---|
| `thumbv6m-none-eabi` | Cortex-M0/M0+ | no |
| `thumbv7em-none-eabihf` | Cortex-M4F/M7F | no |
| `thumbv8m.main-none-eabihf` | Cortex-M33 | no |
| `riscv32imac-unknown-none-elf` | RISC-V embebido | no |
| `x86_64-unknown-none` | kernel/bare metal | no |
| `wasm32-unknown-unknown` | navegador | no |
| `wasm32-wasip1` | WASI | parcial |

1. El target se elige en `Tome.toml` o en la CLI.
2. `Tome.toml` declara `[[bin]] target = "..."`.
3. El target por defecto es el host.
4. Los targets `none` no tienen SO ni allocator.
5. Los targets wasm tienen memoria lineal y no threads por defecto.
6. La compilación cruzada requiere el target instalado (`rustup target add`).
7. `build-std` compila `core`/`alloc` desde fuente; requiere nightly.

### 55.7 Cross-compilation y linker

`Tome.toml`:

```toml
[tome]
name = "blink"
version = "0.1.0"
pengu = "1.0"
edition = "2024"
rust-version = "1.85"

[[bin]]
name = "blink"
path = "main.pengu"
target = "thumbv7em-none-eabihf"
```

`.cargo/config.toml`:

```toml
[target.thumbv7em-none-eabihf]
runner = "probe-rs run --chip STM32F401RE"
rustflags = ["-C", "link-arg=-Tlink.x"]

[build]
target = "thumbv7em-none-eabihf"
```

`memory.x`:

```ld
MEMORY
{
  FLASH : ORIGIN = 0x08000000, LENGTH = 512K
  RAM   : ORIGIN = 0x20000000, LENGTH = 128K
}
```

1. El linker script lo aporta el crate del chip (`cortex-m-rt`).
2. `memory.x` define las regiones; se incluye con `include!("memory.x")` en
   `build.rs` o con `-Tlink.x`.
3. `runner` permite `cargo run` sobre hardware.
4. `rustflags` debe ser reproducible; se documenta en el tome.
5. `probe-rs`/`openocd` no forman parte del compilador.
6. Un error de linker no es un error de tipos; se muestra con el comando.

### 55.8 Volatile y MMIO

```pengu
curse write_reg = (addr: Usize, value: U32) -> Unit
    -- SAFETY: `addr` es un registro MMIO válido y alineado.
    write_volatile(addr as *mut U32, value)
```

Rust generado:

```rust
fn write_reg(addr: usize, value: u32) {
    // SAFETY: `addr` es un registro MMIO válido y alineado.
    unsafe { core::ptr::write_volatile(addr as *mut u32, value) }
}
```

1. `read_volatile`/`write_volatile` no se optimizan ni se reordenan.
2. No reemplazan una barrera de memoria; para eso se usa `fence`.
3. El registro debe ser `*mut U32` alineado.
4. `Usize` no garantiza que la dirección sea válida.
5. En embebidos, los registros suelen ser `static` con `UnsafeCell`.
6. `volatile` no es para sincronización entre hilos.
7. `asm!` puede ser necesario para instrucciones especiales.

### 55.9 Interrupciones

1. Una interrupción es una función `extern "C"` con un vector asociado.
2. El atributo `@@interrupt` lo aporta el crate del chip; no es del núcleo.
3. El handler no debe bloquear ni asignar memoria.
4. El estado compartido se protege con `critical-section` o atomics.
5. `static mut` no se usa; se usa `@@shared` con `Mutex`/`RefCell` según el
   contexto.
6. La prioridad y el nesting dependen del chip.
7. En Cortex-M, el vector table lo genera `cortex-m-rt`.

### 55.10 `cortex-m` y `embassy`

1. `cortex-m` aporta `interrupt`, `entry`, `Peripherals` y `NVIC`.
2. `cortex-m-rt` aporta el runtime y el linker script.
3. `embassy` aporta async sin `std`; se usa `dream`/`awaken`.
4. `embassy-executor` es el executor; no hay runtime del lenguaje.
5. `embedded-hal` define traits de periféricos.
6. `defmt` es logging binario; no es `print`.
7. `panic-probe` implementa el panic handler sobre `defmt`.

### 55.11 wasm

1. `wasm32-unknown-unknown` no tiene `std`; se usa `core`/`alloc`.
2. `wasm32-wasip1` tiene `std` disponible y filesystem virtual; las APIs dependen de WASI.
3. `wasm-bindgen` expone funciones y tipos JS.
4. `#[wasm_bindgen]` es un proc macro; se consume, no se define.
5. La memoria se exporta como `WebAssembly.Memory`.
6. No hay threads por defecto; `wasm-bindgen-rayon` requiere features.
7. El tamaño de `Usize` es 32 bits en wasm32.
8. Las llamadas JS pueden lanzar excepciones; se capturan en el borde.

`Tome.toml` para wasm:

```toml
[tome]
name = "pengu-wasm"
version = "0.1.0"
pengu = "1.0"
edition = "2024"
rust-version = "1.85"

[lib]
path = "lib.pengu"
crate-type = ["cdylib"]

[dependencies]
wasm-bindgen = "0.2"
```

### 55.12 `build-std`

```toml
[unstable]
build-std = ["core", "alloc"]
build-std-features = ["compiler-builtins-mem"]
```

1. `build-std` compila `core`/`alloc` con el target actual.
2. Requiere nightly y `rust-src`.
3. Se usa cuando el target no tiene artifacts precompilados.
4. Aumenta el tiempo de build.
5. `compiler-builtins-mem` aporta `memcpy`/`memset`.
6. No se usa en el camino normal del compilador.
7. Las features inestables se documentan en §66.

### 55.13 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5501` | `std` en crate `no_std` | usar `core`/`alloc` |
| `PGS-E5502` | binario `no_std` sin panic handler | añadir `@@panic_handler` |
| `PGS-E5503` | `alloc` sin allocator | añadir `@@global_allocator` |
| `PGS-E5504` | entry point ausente | añadir `@@entry` |
| `PGS-E5505` | volatile fuera de `curse` | envolver en `curse` |
| `PGS-E5506` | target sin soporte | instalar target/`build-std` |
| `PGS-W5501` | `no_std` innecesario | usar `std` |
| `PGS-W5502` | handler de panic que retorna | usar `-> !` |

### 55.14 Criterios de aceptación

- [x] `@@no_std`, `core`/`alloc` y panic handler están definidos.
- [x] El allocator y la entry point están cubiertos.
- [x] Los targets, linker y `build-std` están documentados.
- [x] Volatile/MMIO e interrupciones están limitados a `curse`.
- [x] wasm y `wasm-bindgen` están integrados.
- [x] Los ejemplos Rust compilan como librería `no_std`.

[↑ Volver al índice](#indice)

<a id="part-9"></a>
## Parte IX — Herramientas y calidad

<a id="sec-56-testing"></a>
## 56. Testing

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 9 |
| Rust | `#[test]`, `#[should_panic]`, `#[ignore]`, `#[cfg(test)]` |
| Palabras mágicas | `@@test`, `@@should_panic`, `@@ignore`, `@@bench` |
| Depende de | §3, §13, §31, §48 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec56_testing.pengu` |

Los tests son **items**, no un lenguaje aparte. Se escriben en PenguScript, se
transpilan a `#[test]` y se ejecutan con `pengu test` o `cargo test`.

### 56.1 Principios

1. Un test es una función sin parámetros que no retorna un valor útil.
2. Los tests viven en el mismo crate o en `tests/`.
3. No hay `describe`/`it`: el nombre de la función es el nombre del test.
4. `assert` falla con pánico; el runner lo reporta como test fallido.
5. Un test no debe depender del orden de ejecución.
6. Los tests pueden usar `curse` si el código bajo prueba es unsafe.
7. Un test no puede ser `unveil`; no forma parte de la API.
8. Los tests no se compilan en `--release` salvo `cargo test --release`.

### 56.2 `@@test`

```pengu
add = (a: Int, b: Int) -> Int
    a + b

@@test
add_works = () -> Unit
    assert_eq(add(2, 3), 5)
```

Rust generado:

```rust
fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[test]
fn add_works() {
    assert_eq!(add(2, 3), 5);
}
```

1. `@@test` marca la función como test.
2. La función no lleva parámetros.
3. El tipo de retorno es `Unit` o `!Unit` (test fallible).
4. El nombre debe ser único en el módulo.
5. `@@test` implica `@@cfg(test)`; no se compila fuera de tests.
6. Un test puede llamar a funciones privadas del módulo.
7. `@@test` no se combina con `dream`, `curse` ni `eternal` en v1.
8. Un test no puede ser `@`/`@mut`/`@own`; no es método.

### 56.3 Test fallible

```pengu
@@test
parse_works = () -> !Unit
    bind n = parse_int("42")?
    assert_eq(n, 42)
    ok(())
```

Rust generado:

```rust
fn parse_int(s: &str) -> Result<i32, Box<dyn std::error::Error>> {
    Ok(s.parse()?)
}

#[test]
fn parse_works() -> Result<(), Box<dyn std::error::Error>> {
    let n = parse_int("42")?;
    assert_eq!(n, 42);
    Ok(())
}
```

1. `!Unit` permite usar `?` dentro del test.
2. El error debe convertir a `Box<dyn Error + Send + Sync>`.
3. `ok(())` es el retorno explícito.
4. Si el test retorna `err`, el runner lo marca como fallido.
5. `!Unit` no se usa para tests que solo panican.
6. El tipo de error se puede estrechar con `!Unit` + `Error` alias.
7. `?` no se usa en tests `Unit`.

### 56.4 Aserciones

| PenguScript | Rust | Uso |
|---|---|---|
| `assert(cond)` | `assert!(cond)` | condición booleana |
| `assert(cond, "msg")` | `assert!(cond, "msg")` | con mensaje |
| `assert_eq(a, b)` | `assert_eq!(a, b)` | igualdad |
| `assert_ne(a, b)` | `assert_ne!(a, b)` | desigualdad |
| `debug_assert(cond)` | `debug_assert!(cond)` | solo debug |
| `debug_assert_eq(a, b)` | `debug_assert_eq!(a, b)` | solo debug |
| `panic("msg")` | `panic!("msg")` | fallo incondicional |

1. `assert` y `assert_eq` son funciones del preludio, no palabras clave.
2. `assert_eq` requiere `Debug + PartialEq`.
3. El mensaje es `Str` y se evalúa solo al fallar.
4. `debug_assert` no se ejecuta en `--release`.
5. `panic` es `Never`; se puede usar en una rama.
6. No hay `assert_throws`; se usa `@@should_panic`.
7. Los mensajes deben describir el valor esperado y el obtenido.

```rust
fn main() {
    let total = 2 + 3;
    assert_eq!(total, 5, "2 + 3 debe ser 5");
    assert_ne!(total, 6);
}
```

### 56.5 `@@should_panic`

```pengu
@@test
@@should_panic(expected: "divide by zero")
divide_by_zero = () -> Unit
    bind _ = 1 / 0
```

Rust generado:

```rust
#[test]
#[should_panic(expected = "divide by zero")]
fn divide_by_zero() {
    let _ = 1 / 0;
}
```

1. `@@should_panic` espera un pánico; si no ocurre, el test falla.
2. `expected` es opcional; si se omite, cualquier pánico vale.
3. `expected` busca una subcadena del mensaje, no una igualdad exacta.
4. El pánico debe ocurrir en el cuerpo del test, no en el runner.
5. `@@should_panic` no se combina con `!Unit`.
6. Un `panic` en un `Drop` también cuenta.
7. El mensaje debe ser estable; no incluir direcciones ni rutas.

### 56.6 `@@ignore`

```pengu
@@test
@@ignore(reason: "requiere red")
network_test = () -> Unit
    assert(true)
```

Rust generado:

```rust
#[test]
#[ignore = "requiere red"]
fn network_test() {
    assert!(true);
}
```

1. `@@ignore` omite el test por defecto.
2. `pengu test -- --ignored` ejecuta solo los ignorados.
3. `--include-ignored` ejecuta todos.
4. `reason` se muestra en el reporte.
5. No se usa para ocultar tests rotos; se usa para tests lentos o externos.
6. `@@ignore` no cambia el código del test.
7. Un test ignorado cuenta como omitido, no como pasado.

### 56.7 Tests unitarios en el mismo archivo

```pengu
add = (a: Int, b: Int) -> Int
    a + b

@@cfg(test)
scroll tests
    summon super::*

    @@test
    add_works = () -> Unit
        assert_eq(add(2, 3), 5)
```

Rust generado:

```rust
fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_works() {
        assert_eq!(add(2, 3), 5);
    }
}
```

1. `@@cfg(test)` hace que el módulo solo exista en tests.
2. `summon super::*` importa el módulo padre.
3. El módulo de tests puede acceder a items privados.
4. No se usa `unveil` en el módulo de tests.
5. Los tests unitarios van al final del archivo.
6. Un módulo de tests no puede declarar `grimoire`.
7. Los nombres de tests pueden repetirse en módulos distintos.

### 56.8 Tests de integración

```text
tome/
├── Tome.toml
├── main.pengu
├── lib.pengu
└── tests/
    ├── api.pengu
    └── cli.pengu
```

`Tome.toml`:

```toml
[[test]]
name = "api"
path = "tests/api.pengu"

[[test]]
name = "cli"
path = "tests/cli.pengu"
```

1. Cada archivo de `tests/` es un crate de test independiente.
2. Solo puede usar la API pública (`unveil`).
3. `summon nombre_tome` importa la librería.
4. `tests/` no se compila en `pengu build`.
5. `pengu test --test api` ejecuta uno solo.
6. Los tests de integración pueden usar `std::process`.
7. Un test de integración no ve items privados.

### 56.9 Doc tests

1. Los bloques `pengu` en comentarios `---` se ejecutan con `pengu test --doc`.
2. El bloque se compila como un crate aparte.
3. `#` al inicio de una línea oculta esa línea en la documentación.
4. Un doc test que no compila falla.
5. `no_run` compila pero no ejecuta.
6. `should_panic` se escribe en el bloque.
7. Los doc tests usan la API pública.

### 56.10 Property testing

1. `proptest`/`quickcheck` se consumen como crates Rust.
2. La propiedad es una función `(T) -> Bool`.
3. El generador se declara con `proptest!` o `quickcheck!`.
4. Un fallo produce un caso mínimo (shrinking).
5. No hay sintaxis nueva en PenguScript; se usa el macro del crate.
6. Las propiedades no reemplazan tests de ejemplo.
7. Los rangos de entrada deben ser finitos.

### 56.11 Fuzzing

1. `cargo-fuzz` usa `libFuzzer` y un target `fuzz_target!`.
2. El target recibe `&[U8]` y no debe panican por entradas válidas.
3. Un crash se guarda en `fuzz/artifacts/`.
4. `pengu fuzz` es un wrapper de `cargo fuzz`.
5. Los targets viven en `fuzz/fuzz_targets/` y son Rust.
6. Un fuzz target no se ejecuta en CI por defecto.
7. La semilla se registra para reproducir.

### 56.12 Benchmarks

```pengu
@@bench
bench_add = () -> Unit
    bind _ = add(2, 3)
```

Rust generado (nightly, `#[bench]`; no se compila en stable):

```text
#![feature(test)]
extern crate test;

#[bench]
fn bench_add(b: &mut test::Bencher) {
    b.iter(|| add(2, 3));
}
```

Equivalente estable con `criterion` (crate externo):

```rust
fn add(a: i32, b: i32) -> i32 {
    a + b
}

fn bench_add() {
    let mut total = 0;
    for _ in 0..1000 {
        total += add(2, 3);
    }
    assert_eq!(total, 5000);
}
```

1. `@@bench` genera `#[bench]`, que requiere nightly.
2. En stable se usa `criterion` como crate externo.
3. Un benchmark no es un test; no falla por lentitud.
4. `criterion` mide con intervalo de confianza.
5. Los benchmarks no se ejecutan en `pengu test`.
6. `pengu bench` ejecuta `cargo bench`.
7. Los resultados no son parte del contrato del lenguaje.

### 56.13 Cobertura y CI

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - run: cargo install --path . --locked
      - run: pengu check --deny warnings
      - run: pengu test --all
      - run: pengu test --doc
```

1. `pengu test --coverage` usa `llvm-cov` o `tarpaulin`.
2. La cobertura es una señal, no un objetivo.
3. CI debe ejecutar `check`, `test`, `fmt --check`, `lint`.
4. `--locked` garantiza `Tome.lock`.
5. Los tests de integración pueden necesitar servicios; se marcan `@@ignore`.
6. La matriz de Rust se fija en `rust-version`.
7. Un test que pasa en local y falla en CI suele ser orden/estado global.

### 56.14 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5601` | `@@test` con parámetros | quitar parámetros |
| `PGS-E5602` | `@@test` con retorno no permitido | usar `Unit`/`!Unit` |
| `PGS-E5603` | `@@test` en `ritual`/`pact` | mover a módulo libre |
| `PGS-E5604` | `@@should_panic` sin `@@test` | añadir `@@test` |
| `PGS-E5605` | `@@ignore` sin `@@test` | añadir `@@test` |
| `PGS-E5606` | test de integración usa item privado | hacer `unveil` |
| `PGS-W5601` | test sin aserción | añadir `assert` o retorno |
| `PGS-W5602` | `debug_assert` en test | usar `assert` |

### 56.15 Criterios de aceptación

- [x] `@@test`, `@@should_panic` y `@@ignore` están definidos.
- [x] Las aserciones y sus tipos están documentadas.
- [x] Tests unitarios, de integración y doc tests están cubiertos.
- [x] Property testing, fuzzing, benchmarks y cobertura están explicados.
- [x] CI tiene un ejemplo ejecutable.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-57-documentacion"></a>
## 57. Documentación

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 9 |
| Rust | `///`, `//!`, `#[doc = "..."]`, `#[must_use]`, `#[deprecated]` |
| Palabras mágicas | `---`, `--!`, `@@doc`, `@@must_use`, `@@deprecated` |
| Depende de | §3, §42, §56 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec57_docs.pengu` |

La documentación es parte del código. Los comentarios `---` y `--!` generan
`rustdoc`; los bloques `pengu` se ejecutan como doc tests.

### 57.1 Comentarios de documentación

```pengu
--- Suma dos enteros.
---
--- # Ejemplos
---
--- ```pengu
--- add(2, 3) -- 5
--- ```
unveil add = (a: Int, b: Int) -> Int
    a + b
```

Rust generado:

```rust
/// Suma dos enteros.
///
/// # Ejemplos
///
/// ```pengu
/// add(2, 3) // 5
/// ```
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

1. `---` documenta el item que sigue.
2. `--!` documenta el módulo/crate que lo contiene.
3. `---` y `--!` son comentarios; el compilador no los parsea como código.
4. El contenido es Markdown, no PenguScript.
5. La primera línea es el resumen; el resto es el cuerpo.
6. Una línea vacía separa párrafos (`---` sola).
7. Los comentarios `--` normales no se publican.
8. `---` no se usa dentro de una función; para eso hay `--`.

### 57.2 Documentación interna

```pengu
--! # `math`
--!
--! Utilidades numéricas puras.
--!
--! Este módulo no hace I/O.

scroll math
    --- Constante de Euler.
    unveil E = 2.718281828459045
```

Rust generado:

```rust
//! # `math`
//!
//! Utilidades numéricas puras.
//!
//! Este módulo no hace I/O.

pub mod math {
    /// Constante de Euler.
    pub const E: f64 = 2.718281828459045;
}
```

1. `--!` debe estar al inicio del archivo o del `scroll`.
2. Solo hay un bloque `--!` por módulo.
3. `--!` describe el crate si está en `lib.pengu`/`main.pengu`.
4. Los `---` internos documentan items.
5. `--!` no se repite después de un item.
6. El README del crate se genera desde `--!`.
7. `--!` no genera un doc test por sí solo.

### 57.3 Markdown permitido

| Elemento | Sintaxis | Rustdoc |
|---|---|---|
| Encabezado | `# Título` | `<h1>` |
| Párrafo | texto | `<p>` |
| Lista | `- item` | `<ul>` |
| Lista numerada | `1. item` | `<ol>` |
| Código inline | `` `code` `` | `<code>` |
| Bloque | cerca de código con lenguaje | `<pre>` |
| Énfasis | `*texto*` | `<em>` |
| Fuerte | `**texto**` | `<strong>` |
| Enlace | `[texto](url)` | `<a>` |
| Imagen | `![alt](url)` | `<img>` |
| Tabla | `\| a \| b \|` | tabla HTML |
| Cita | `> texto` | `<blockquote>` |

1. Se permite el subconjunto CommonMark.
2. No se permite HTML crudo; se escapa.
3. Los enlaces externos llevan `https://`.
4. Las imágenes deben tener `alt`.
5. Las tablas necesitan encabezado y separador.
6. Los bloques de código declaran lenguaje (`pengu`, `rust`, `text`, `toml`).
7. Un bloque sin lenguaje se trata como `text`.

### 57.4 Enlaces intra-doc

```pengu
--- Un punto en el plano.
---
--- Se usa en [`Shape`] y en [`area`].
rune Point
    x: Float
    y: Float
```

Rust generado:

```rust
/// Un punto en el plano.
///
/// Se usa en [`Shape`] y en [`area`].
pub struct Point {
    pub x: f64,
    pub y: f64,
}
```

1. ``[`Item`]`` enlaza a un item del crate.
2. ``[`crate::math::Point`]`` usa una ruta absoluta.
3. ``[`Point::x`]`` enlaza a un campo/método.
4. ``[`add`]`` enlaza a una función.
5. Un enlace roto es warning `PGS-W5701`.
6. Los enlaces se resuelven después de typecheck.
7. No se permiten enlaces a items privados desde docs públicas.

### 57.5 `@@doc`

```pengu
@@doc("Alias de `add`.")
@@must_use(message: "el resultado debe usarse")
@@deprecated(since: "0.2.0", note: "usa `add_v2`")
unveil add_v1 = (a: Int, b: Int) -> Int
    a + b
```

Rust generado:

```rust
#[doc = "Alias de `add`."]
#[must_use = "el resultado debe usarse"]
#[deprecated(since = "0.2.0", note = "usa `add_v2`")]
pub fn add_v1(a: i32, b: i32) -> i32 {
    a + b
}
```

1. `@@doc` añade documentación sin `---`.
2. `@@doc(hidden)` oculta el item de rustdoc.
3. `@@doc(alias = "sum")` añade un alias de búsqueda.
4. `@@must_use` avisa si se descarta el valor.
5. `@@must_use(message: "...")` personaliza el aviso.
6. `@@deprecated` marca el item como obsoleto.
7. `since` debe ser una versión semver; `note` es Markdown.
8. `@@doc` y `---` se combinan; el orden es `---` primero.

### 57.6 Rustdoc

```bash
pengu doc
pengu doc --open
pengu doc --document-private-items
pengu doc --no-deps
```

1. `pengu doc` transpila y ejecuta `cargo doc`.
2. La salida va a `target/doc/`.
3. `--open` abre el navegador.
4. `--document-private-items` incluye items privados.
5. `--no-deps` no documenta dependencias.
6. Los docs de dependencias se enlazan con `--extern-html-root-url`.
7. `pengu doc` falla si un enlace intra-doc está roto y `--deny warnings` está activo.

### 57.7 Doc tests

```pengu
--- Suma dos enteros.
---
--- ```pengu
--- assert_eq(add(2, 3), 5)
--- ```
unveil add = (a: Int, b: Int) -> Int
    a + b
```

1. `pengu test --doc` extrae los bloques `pengu`.
2. Cada bloque se compila como un crate de test.
3. `assert_eq` debe estar disponible en el bloque.
4. `no_run` compila pero no ejecuta.
5. `ignore` omite el bloque.
6. `should_panic` espera un pánico.
7. Las líneas que empiezan con `# ` se ocultan en la documentación.
8. Un doc test no ve items privados.

### 57.8 README y ejemplos

1. `pengu doc --readme` genera `README.md` desde `--!`.
2. El README incluye instalación, ejemplo mínimo y enlaces.
3. Los ejemplos del README se prueban con `pengu test --doc`.
4. Un ejemplo debe ser ejecutable y no depender de red.
5. Los ejemplos largos viven en `examples/` y se enlazan.
6. `examples/` se compila con `pengu build --examples`.
7. Un ejemplo no es un test; puede imprimir.

### 57.9 Lints de documentación

| Código | Situación | Solución |
|---|---|---|
| `PGS-W5701` | enlace intra-doc roto | corregir ruta |
| `PGS-W5702` | item público sin docs | añadir `---` |
| `PGS-E5701` | `@@doc` en item privado con `--document-private-items` | revisar visibilidad |
| `PGS-E5702` | bloque de código sin lenguaje | declarar `text` |
| `PGS-E5703` | HTML crudo | usar Markdown |
| `PGS-W5703` | `@@deprecated` sin `since` | añadir versión |

1. `@@deny(missing_docs)` convierte W5702 en error.
2. `pengu lint --doc` revisa enlaces y estilo.
3. Los docs de items `unveil` son obligatorios en librerías.
4. Los docs de items privados son opcionales.
5. Un doc test roto es error, no warning.
6. Los enlaces externos no se comprueban en CI por defecto.
7. Los ejemplos deben usar la API pública.

### 57.10 Criterios de aceptación

- [x] `---` y `--!` están definidos y mapeados a rustdoc.
- [x] Markdown permitido y enlaces intra-doc están cubiertos.
- [x] `@@doc`, `@@must_use` y `@@deprecated` están especificados.
- [x] `pengu doc` y los doc tests están documentados.
- [x] Los lints de documentación tienen códigos.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

<a id="sec-58-herramientas"></a>
## 58. Herramientas (CLI, LSP, formatter, linter)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 9 |
| Rust | `cargo`, `rustc`, `rustfmt`, `clippy` |
| Palabras mágicas | `pengu` (CLI), `@@allow`, `@@deny`, `@@warn` |
| Depende de | §3, §43, §47, §56, §57 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec58_tooling.pengu` |

El compilador se invoca con `pengu`. La CLI transpila a Rust, invoca `cargo` y
traduce los diagnósticos de vuelta al código PenguScript mediante
`sourcemap.json`.

### 58.1 Comandos

| Comando | Uso | Efecto |
|---|---|---|
| `pengu new <name>` | crear proyecto | `Tome.toml`, `main.pengu`, `.gitignore` |
| `pengu init` | inicializar en directorio | igual, sin crear carpeta |
| `pengu build` | compilar | genera `target/pengu/` y ejecuta `cargo build` |
| `pengu run` | compilar y ejecutar | `cargo run` |
| `pengu check` | typecheck sin binario | `cargo check` |
| `pengu test` | tests | `cargo test` |
| `pengu fmt` | formatear | reescribe `.pengu` |
| `pengu lint` | lints | analiza AST + `clippy` |
| `pengu doc` | documentación | `cargo doc` |
| `pengu bench` | benchmarks | `cargo bench` |
| `pengu fuzz` | fuzzing | `cargo fuzz` |
| `pengu clean` | limpiar | borra `target/pengu/` |
| `pengu add <crate>` | dependencia | edita `Tome.toml` + lock |
| `pengu remove <crate>` | quitar dependencia | edita `Tome.toml` |
| `pengu update` | actualizar lock | respeta semver |
| `pengu publish` | publicar | valida y empaqueta |
| `pengu audit` | vulnerabilidades | `cargo audit` |
| `pengu lsp` | language server | JSON-RPC por stdio |
| `pengu explain <code>` | explicar diagnóstico | texto + ejemplo |
| `pengu metadata` | info del proyecto | JSON |

### 58.2 Flags comunes

| Flag | Comandos | Uso |
|---|---|---|
| `--release` | build/run/test/bench | perfil release |
| `--target <triple>` | build/run/check | target Rust |
| `--features <a,b>` | build/run/test | features del tome |
| `--all-features` | build/test | todas |
| `--no-default-features` | build/test | sin defaults |
| `--locked` | build/test/run | exige `Tome.lock` |
| `--offline` | build/test | no red |
| `--deny warnings` | check/build/test | warnings como errores |
| `--message-format json` | check/build | diagnósticos JSON |
| `--quiet` | todos | solo errores |
| `--verbose` | todos | comandos internos |
| `--color <auto\|always\|never>` | todos | color |

1. Los flags desconocidos son error de uso (`PGS-E5801`).
2. `--` separa flags de `pengu` de argumentos del programa.
3. `--target` no cambia el target de `Tome.toml`; lo sobrescribe.
4. `--locked` falla si el lock no existe o está desactualizado.
5. `--offline` no descarga crates; falla si falta el cache.
6. `--quiet` no suprime errores.
7. Los flags de `cargo` no documentados se pasan con `--cargo-args`.

### 58.3 Códigos de salida

| Código | Significado |
|---|---|
| `0` | éxito |
| `1` | error de compilación, test o lint |
| `2` | uso incorrecto de la CLI |
| `3` | error de configuración (`Tome.toml`) |
| `4` | error interno del compilador |
| `101` | pánico de Rust (no debería ocurrir) |

1. Un test fallido devuelve `1`.
2. Un `check` con warnings y `--deny warnings` devuelve `1`.
3. `pengu fmt --check` devuelve `1` si hay diferencias.
4. `pengu lint --deny warnings` devuelve `1` si hay warnings.
5. Un error de red en `pengu add` devuelve `1`.
6. `pengu explain` devuelve `0` si el código existe.
7. `pengu metadata` devuelve `0` aunque no haya lock.

### 58.4 Estructura del proyecto

```text
tome/
├── Tome.toml
├── Tome.lock
├── main.pengu
├── lib.pengu
├── src/
│   ├── math.pengu
│   └── math/
│       └── vector.pengu
├── tests/
│   └── api.pengu
├── examples/
│   └── demo.pengu
├── benches/
│   └── bench.pengu
├── build.pengu
└── target/
    └── pengu/
        ├── Cargo.toml
        ├── Cargo.lock
        ├── build.rs
        ├── src/
        └── sourcemap.json
```

1. `main.pengu` y `lib.pengu` son las raíces.
2. `src/` es opcional si no hay raíz.
3. `tests/`, `examples/` y `benches/` tienen el mismo rol que en Cargo.
4. `target/pengu/` es generado; no se edita.
5. `sourcemap.json` conecta Rust con PenguScript.
6. `Tome.lock` se versiona; `target/` no.
7. `build.pengu` se transpila a `build.rs`.

### 58.5 `pengu check`

1. Parsea, resuelve, typechequea y transpila sin emitir binario.
2. Ejecuta `cargo check` para validar préstamos y tipos Rust.
3. No ejecuta `build.rs` salvo que el crate lo requiera.
4. Es más rápido que `build` y apto para CI.
5. Los diagnósticos se remapean a `.pengu`.
6. `--deny warnings` convierte warnings en errores.
7. No genera `target/pengu/src/` completo si `--emit=metadata`.

### 58.6 `pengu build`

1. Transpila todos los archivos alcanzables desde las raíces.
2. Genera `Cargo.toml`, `Cargo.lock`, `build.rs` y `src/`.
3. Ejecuta `cargo build` con los flags traducidos.
4. Copia artefactos a `target/<target>/<profile>/`.
5. Escribe `sourcemap.json` para el debugger.
6. Falla si un `.pengu` no compila o si `rustc` falla.
7. No modifica los `.pengu`.

### 58.7 `pengu run`

1. Ejecuta `build` y luego el binario.
2. `--` pasa argumentos al programa.
3. El `cwd` es la raíz del tome.
4. `--release` usa el perfil release.
5. El código de salida del programa se propaga.
6. Un pánico de Rust se muestra con el mapa de líneas.
7. `run` no existe para `lib.pengu` sin `[[bin]]`.

### 58.8 `pengu test`

1. Ejecuta tests unitarios, de integración y doc tests.
2. `--all` incluye todos los targets.
3. `--test <name>` ejecuta un archivo de `tests/`.
4. `--doc` solo doc tests.
5. `-- --nocapture` pasa flags al runner.
6. `--coverage` genera un reporte (`llvm-cov`/`tarpaulin`).
7. Un test ignorado no cuenta como fallo.

### 58.9 `pengu fmt`

```bash
pengu fmt
pengu fmt --check
pengu fmt --stdin < main.pengu
pengu fmt --check --diff
```

1. El formatter es determinista e idempotente.
2. Usa 4 espacios; nunca tabs.
3. Ancho máximo: 100 columnas.
4. Una expresión/declaración por línea.
5. Comas finales en colecciones multilínea.
6. `summon` se ordena por ruta.
7. Conserva comentarios y líneas en blanco significativas.
8. `--check` no escribe; devuelve `1` si cambiaría algo.
9. `--stdin` lee de stdin y escribe a stdout.
10. `--diff` muestra el diff unificado.
11. No cambia la semántica; si lo hace, es un bug.
12. `@@fmt(off)` desactiva el formato en un rango.

### 58.10 Reglas del formatter

| Regla | Ejemplo |
|---|---|
| 4 espacios | `    bind x = 1` |
| sin tabs | `\t` -> error |
| 2 líneas entre items | `rune`/`enchanting`/`pact` |
| 1 línea entre métodos | `ritual` |
| coma final | `[1, 2, 3,]` multilínea |
| paréntesis mínimos | `(a + b) * c` conserva |
| strings | no reescribe escalas |
| imports | `summon` ordenados |
| comentarios | se conservan |
| ancho | 100 columnas |

### 58.11 Linter

```bash
pengu lint
pengu lint --deny warnings
pengu lint --fix
pengu lint --format json
```

| Código | Nombre | Categoría |
|---|---|---|
| `PGS-L101` | `unused_binding` | corrección |
| `PGS-L102` | `unreachable_code` | corrección |
| `PGS-L103` | `unused_import` | corrección |
| `PGS-L201` | `shadowing` | estilo |
| `PGS-L202` | `magic_number` | estilo |
| `PGS-L203` | `long_function` | complejidad |
| `PGS-L301` | `unsafe_without_safety` | seguridad |
| `PGS-L302` | `raw_pointer_escape` | seguridad |
| `PGS-L401` | `missing_docs` | documentación |
| `PGS-L402` | `broken_intra_doc_link` | documentación |
| `PGS-L501` | `lexicon_collision` | diseño |
| `PGS-L502` | `rust_escape_hatch` | diseño |

1. Los lints son warnings por defecto, salvo los de corrección.
2. `--deny warnings` los convierte en errores.
3. `--fix` solo aplica fixes seguros.
4. `@@allow(PGS-L201)` silencia un lint en el item.
5. `@@deny(PGS-L301)` lo convierte en error local.
6. `@@warn(PGS-L401)` lo activa localmente.
7. `PGS-L501` detecta una palabra mágica que también es identificador común.
8. `PGS-L502` avisa de cada bloque `rust`.

### 58.12 Configuración

`Tome.toml`:

```toml
[tool.pengu.fmt]
max-width = 100
indent = 4
trailing-comma = true

[tool.pengu.lint]
deny = ["PGS-L301", "PGS-L302"]
warn = ["PGS-L201"]
allow = ["PGS-L202"]

[tool.pengu.test]
coverage = false
```

1. `[tool.pengu]` no se pasa a Cargo.
2. `fmt.max-width` debe estar entre 80 y 120.
3. `lint.deny` tiene prioridad sobre `allow`.
4. La configuración del CLI se puede sobrescribir con flags.
5. `Tome.toml` inválido es `PGS-E5802`.
6. Los valores desconocidos son warning `PGS-W5801`.
7. La configuración se resuelve desde la raíz del tome.

### 58.13 LSP

```bash
pengu lsp
pengu lsp --stdio
pengu lsp --tcp 127.0.0.1:9257
```

| Capacidad | Soporte |
|---|---|
| `textDocument/publishDiagnostics` | sí |
| `textDocument/hover` | sí |
| `textDocument/completion` | sí |
| `textDocument/definition` | sí |
| `textDocument/references` | sí |
| `textDocument/rename` | sí |
| `textDocument/formatting` | sí |
| `textDocument/codeAction` | sí |
| `textDocument/inlayHint` | sí |
| `textDocument/semanticTokens` | sí |
| `workspace/symbol` | sí |
| `textDocument/documentSymbol` | sí |

1. JSON-RPC 2.0 sobre stdio o TCP.
2. `stdout` solo lleva protocolo; los logs van a `stderr`.
3. Los diagnósticos usan `sourcemap.json` para volver a `.pengu`.
4. `hover` muestra el tipo inferido y el doc.
5. `completion` incluye preludio, locales y campos.
6. `rename` respeta scopes y no renombra strings.
7. `formatting` usa el mismo formatter que `pengu fmt`.
8. `codeAction` ofrece fixes de lints seguros.
9. `inlayHint` muestra tipos de `bind` y retornos.
10. El servidor se reinicia si `Tome.toml` cambia.

### 58.14 Source maps y diagnósticos

`sourcemap.json`:

```json
{
  "version": 1,
  "generated": {
    "src/main.rs": "main.pengu",
    "src/math.rs": "src/math.pengu"
  },
  "mappings": [
    {
      "generated": { "file": "src/main.rs", "line": 3, "column": 4 },
      "source": { "file": "main.pengu", "line": 2, "column": 4 }
    }
  ]
}
```

1. Cada archivo Rust generado tiene un `.pengu` de origen.
2. Las líneas/columnas son 1-based en el JSON.
3. `rustc` emite JSON; `pengu` lo remapea.
4. Un diagnóstico sin mapping se muestra en Rust con nota.
5. `pengu explain PGS-E3001` muestra causa y ejemplo.
6. Los errores de macros apuntan al `incantation`.
7. Los errores de `build.rs` apuntan a `build.pengu`.

### 58.15 `pengu add`, `remove`, `update`

1. `add` edita `Tome.toml` y ejecuta `cargo add` sobre el `Cargo.toml` generado.
2. `--dev` añade a `[dev-dependencies]`.
3. `--features` activa features de la dependencia.
4. `remove` elimina la entrada y actualiza el lock.
5. `update` respeta el rango semver.
6. `update --precise` fija una versión exacta.
7. Un conflicto de versiones es `PGS-E5803`.

### 58.16 `pengu publish`

1. Verifica que el árbol esté limpio.
2. Ejecuta `check`, `test`, `fmt --check`, `lint`, `doc`.
3. Verifica que la versión no exista ya.
4. Empaqueta solo `Tome.toml`, fuentes, README y licencia.
5. `--dry-run` muestra el paquete sin subirlo.
6. `--allow-dirty` omite la comprobación de git.
7. Un fallo de docs o tests aborta la publicación.
8. El registro por defecto es `crates.io`; se puede cambiar en `[cargo]`.

### 58.17 Reproducibilidad y auditoría

1. `Tome.lock` fija versiones exactas.
2. `--locked` falla si el lock no coincide.
3. `--offline` exige cache local.
4. `SOURCE_DATE_EPOCH` fija timestamps en el paquete.
5. `pengu audit` ejecuta `cargo audit`.
6. `pengu deny` revisa licencias y duplicados.
7. `pengu publish` ejecuta `audit` salvo `--no-audit`.
8. Las dependencias con `unsafe` se revisan con `cargo geiger`.

### 58.18 `pengu new` y Rust generado

`pengu new hello --bin` genera:

```pengu
grimoire
    print("Hola, PenguScript!")
```

Rust generado:

```rust
fn main() {
    println!("Hola, PenguScript!");
}
```

1. `--bin` crea `main.pengu`; `--lib` crea `lib.pengu`.
2. `--vcs git` inicializa git; `--vcs none` no.
3. `--edition 2024` es el default.
4. `--name` valida el nombre del crate.
5. `new` no sobrescribe un directorio existente.
6. `init` sí acepta un directorio existente vacío.
7. La plantilla no incluye dependencias.

### 58.19 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5801` | flag desconocido | revisar `--help` |
| `PGS-E5802` | `Tome.toml` inválido | corregir TOML/claves |
| `PGS-E5803` | conflicto de versiones | fijar versión |
| `PGS-E5804` | `pengu` fuera de un tome | `pengu init` |
| `PGS-E5805` | `sourcemap.json` inválido | regenerar build |
| `PGS-E5806` | `publish` sin licencia | añadir `license` |
| `PGS-W5801` | clave de config desconocida | eliminar/renombrar |
| `PGS-W5802` | `--offline` sin cache | descargar antes |

### 58.20 Criterios de aceptación

- [x] Todos los comandos y flags están documentados.
- [x] Los códigos de salida son estables.
- [x] El formatter tiene reglas verificables.
- [x] El linter tiene catálogo y configuración.
- [x] LSP cubre las capacidades básicas.
- [x] Source maps y auditoría están cubiertos.
- [x] El ejemplo Rust compila.

[↑ Volver al índice](#indice)

<a id="sec-59-estilo"></a>
## 59. Guía de estilo

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 9 |
| Rust | `rustfmt`, `clippy` |
| Palabras mágicas | `pengu fmt`, `pengu lint` |
| Depende de | §2, §15, §31, §56, §58 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec59_style.pengu` |

El estilo no es cosmético: hace que el código se lea como magia clara, no como
ruido. Las reglas de esta sección son verificables por el formatter y el linter.

### 59.1 Principios

1. La claridad gana a la brevedad.
2. La indentación reemplaza llaves; no se mezcla con `{}` de bloque.
3. Una línea expresa una idea.
4. Los nombres dicen qué, no cómo.
5. La magia se concentra en las palabras clave; el resto es familiar.
6. El código se escribe una vez y se lee muchas.
7. El formatter decide el espacio; el autor decide la estructura.
8. Un `@@allow` necesita una razón.

### 59.2 Nombres

| Elemento | Convención | Ejemplo |
|---|---|---|
| Tome/paquete | `kebab-case` | `pengu-http` |
| Crate | `snake_case` | `pengu_http` |
| Módulo (`scroll`) | `snake_case` | `scroll geometry` |
| Tipo (`rune`/`enchanting`) | `PascalCase` | `rune Point` |
| Variante de enum | `PascalCase` | `Circle` |
| Función | `snake_case` | `compute_area` |
| Binding (`bind`/`morph`) | `snake_case` | `bind user_count` |
| Constante (`sigil`) | `UPPER_SNAKE` | `sigil MAX_SIZE` |
| Static (`relic`) | `UPPER_SNAKE` | `relic REGISTRY` |
| Tipo genérico | `T`, `K`, `V`, `E` | `rune Map[K, V]` |
| Lifetime | `'a`, `'de`, `'src` | `&'a Str` |
| Archivo | `snake_case.pengu` | `http_client.pengu` |
| Test | `behavior_condition` | `add_returns_sum` |

1. Los tipos son sustantivos; las funciones son verbos.
2. Un booleano empieza con `is_`, `has_`, `can_` o `should_`.
3. Una función que muta empieza con un verbo (`push`, `clear`, `update`).
4. Una función pura no lleva `get_`; se llama por lo que calcula.
5. Evita abreviaturas salvo `id`, `url`, `http`, `api`.
6. No uses `I`/`l`/`O` como nombres de una letra.
7. Los nombres mágicos (`rune`, `pact`, `curse`) van en minúscula.

### 59.3 Archivos y módulos

1. Un archivo = un módulo.
2. El nombre del archivo usa `snake_case`.
3. `scroll` no se usa para un archivo que ya es módulo.
4. Un módulo pequeño puede vivir inline; uno grande, en archivo.
5. `mod.pengu` es el módulo de `mod/`.
6. Los tests unitarios van al final del archivo.
7. Los ejemplos van en `examples/`, no en `src/`.

### 59.4 Indentación y líneas

1. 4 espacios por nivel.
2. Tabs prohibidos, incluso en strings multilínea.
3. Ancho máximo: 100 columnas.
4. Una declaración por línea.
5. Sin punto y coma al final.
6. Sin espacios al final de línea.
7. El archivo termina con un newline.
8. Dos líneas en blanco entre items de nivel superior.
9. Una línea en blanco entre métodos de un `ritual`.
10. Una línea en blanco antes de un comentario de bloque.

```pengu
-- bien
rune Point
    x: Float
    y: Float

    length = (@) -> Float
        (x * x + y * y).sqrt()

-- mal: dos declaraciones en una línea
rune Point2
    x: Float; y: Float
```

### 59.5 Espacios

1. Un espacio alrededor de operadores binarios: `a + b`.
2. Sin espacio antes de `(` en llamadas: `add(1, 2)`.
3. Sin espacio dentro de `[]`/`()`/`{}` inline: `[1, 2]`.
4. Un espacio después de `,` y `:` en mapas: `{name: "pengu"}`.
5. Sin espacio antes de `:` en un tipo: `x: Int`.
6. Un espacio después de `then`/`else`: `if x then 1 else 0`.
7. Sin espacio antes de `?`/`!`: `value?`, `!flag`.
8. `->` y `=>` llevan un espacio a cada lado.

### 59.6 Imports

```pengu
summon std::fmt
summon std::collections::HashMap
summon serde::Serialize
summon crate::geometry::Point
```

1. Orden: `std`, externos, `crate`, `super`, `self`.
2. Dentro de cada grupo, orden alfabético.
3. Un `summon` por línea; el formatter no agrupa.
4. `summon path::*` solo en tests o preludio.
5. Alias solo para colisión: `summon crate::a::Point as PointA`.
6. No importes lo que no usas; `PGS-L103`.
7. Los imports van al inicio del módulo, después de `--!`.

### 59.7 Funciones y expresiones

1. Prefiere el cuerpo de expresión; evita `return` al final.
2. Una función hace una cosa.
3. Máximo orientativo: 40 líneas; si es más, extrae.
4. Los parámetros son explícitos; no hay defaults ni varargs.
5. El tipo de retorno es obligatorio en funciones nombradas.
6. Usa `if`/`match` como expresión cuando devuelven un valor.
7. Evita anidar más de 3 niveles; extrae o usa `match`.
8. Un `match` cubre todos los casos o tiene `else`.

```pengu
-- bien
classify = (n: Int) -> &'static Str
    if n < 0 then "negative"
    elseif n == 0 then "zero"
    else "positive"

-- mal: return redundante
classify2 = (n: Int) -> &'static Str
    if n < 0 then
        return "negative"
    else
        return "positive"
```

### 59.8 Condicionales y bucles

1. `if`/`elseif`/`else` en líneas separadas; `then` en la misma línea.
2. `unless` para una negación simple; no para `elseif`.
3. No uses `if cond then true else false`; usa `cond`.
4. `for` para iterar; `while` para condición; `loop` para repetir hasta `break`.
5. Un `loop` debe tener una salida clara.
6. No uses `break`/`continue` para flujo complejo; extrae.
7. Las etiquetas se usan solo para bucles anidados.

### 59.9 Errores

1. Usa `?` para propagar; no envuelvas manualmente.
2. `expect("contexto")` cuando la ausencia es un bug.
3. `unwrap()` solo en tests, ejemplos y prototipos.
4. `panic` solo para invariantes imposibles.
5. Un error de dominio se modela con `enchanting`.
6. No uses `String` como error si hay un tipo.
7. Un mensaje de error dice qué falló y qué hacer.

```pengu
read_config = (path: &Str) -> !Config
    bind text = std::fs::read_to_string(path)?
    bind config = parse_config(&text)?
    ok(config)
```

### 59.10 Unsafe

1. Todo `curse` tiene un comentario `-- SAFETY:`.
2. La superficie unsafe es mínima; envuelve en una API segura.
3. No uses `transmute` si `as`/`From` sirve.
4. No uses `static mut`; usa `@@shared`.
5. Un `curse` no se propaga a toda la función si no hace falta.
6. Los invariantes se documentan en el `---` del item.
7. `PGS-L301` exige el comentario.

```pengu
curse read_u32 = (ptr: *const U32) -> U32
    -- SAFETY: el llamador garantiza alineación y validez.
    *ptr
```

### 59.11 Comentarios

1. `--` explica el porqué, no el qué.
2. `---` documenta la API; `--!` documenta el módulo.
3. No comentes código obvio.
4. Un TODO lleva dueño: `-- TODO(ana): ...`.
5. No dejes código comentado; usa git.
6. Un comentario de bloque empieza con mayúscula y termina con punto.
7. Los comentarios no se alinean con espacios.

```pengu
-- Reintentamos porque el servicio tiene un límite de 3 req/s.
```

### 59.12 Tests

1. El nombre describe el comportamiento: `parse_empty_returns_none`.
2. Un test prueba una cosa.
3. Estructura arrange-act-assert.
4. Sin `sleep`; usa relojes inyectables.
5. Sin dependencia de orden ni de red.
6. Los casos límite son explícitos.
7. Un test que falla debe decir qué esperaba.

### 59.13 Documentación

1. Todo item `unveil` tiene `---`.
2. El resumen cabe en una línea.
3. Los ejemplos son ejecutables.
4. Los enlaces intra-doc son relativos al crate.
5. `@@deprecated` dice el reemplazo.
6. No documentes la implementación; documenta el contrato.
7. `--!` describe el módulo, no la historia.

### 59.14 Interop con Rust

1. Prefiere `foreign` para FFI; usa el bloque `rust` solo si no hay otra opción.
2. Un bloque `rust` lleva un comentario de justificación.
3. No uses `#[allow]` global; usa `@@allow` local.
4. Los tipos `extern "C"` son `@@repr(C)`.
5. No expongas `std` en una API `no_std`.
6. Los nombres de Rust se mapean a `snake_case`.
7. `PGS-L502` avisa de cada bloque `rust`.

### 59.15 Lints y excepciones

1. `pengu lint` debe pasar sin warnings en CI.
2. `@@allow` va en el item más pequeño posible.
3. Un `@@allow` lleva un comentario con la razón.
4. No se usa `@@allow` para silenciar un bug.
5. Los lints de seguridad no se desactivan globalmente.
6. Los lints nuevos se documentan en §58.
7. Un `@@allow` sin razón es `PGS-L503`.

### 59.16 Formato de ejemplo

```rust
fn mean(values: &[f64]) -> f64 {
    let sum: f64 = values.iter().sum();
    sum / values.len() as f64
}

fn main() {
    let data = [1.0, 2.0, 3.0];
    println!("{:.1}", mean(&data));
}
```

1. El Rust generado sigue `rustfmt`.
2. No se edita a mano `target/pengu/`.
3. El formatter de PenguScript no cambia la semántica.
4. `pengu fmt --check` se ejecuta en CI.
5. Un diff de formato se revisa como cualquier cambio.

### 59.17 Diagnósticos de estilo

| Código | Situación | Solución |
|---|---|---|
| `PGS-L201` | shadowing innecesario | renombrar |
| `PGS-L202` | número mágico | `sigil` |
| `PGS-L203` | función larga | extraer |
| `PGS-L301` | `curse` sin `-- SAFETY:` | añadir razón |
| `PGS-L401` | item público sin docs | añadir `---` |
| `PGS-L501` | colisión de léxico | renombrar |
| `PGS-L502` | bloque `rust` | justificar |
| `PGS-L503` | `@@allow` sin razón | añadir comentario |

### 59.18 Criterios de aceptación

- [x] Nombres, archivos e indentación están definidos.
- [x] Espacios, imports y expresiones son verificables.
- [x] Errores, unsafe y comentarios tienen reglas.
- [x] Tests y documentación tienen guía.
- [x] La interop con Rust está limitada.
- [x] El ejemplo Rust compila.

[↑ Volver al índice](#indice)

<a id="part-10"></a>
## Parte X — Apéndices y referencias

<a id="sec-60-ebnf"></a>
## 60. Gramática EBNF

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 10 |
| Rust | — (gramática del front-end) |
| Palabras mágicas | todas |
| Depende de | §2, §3, §11–§15, §28–§47 |
| Ejemplos ejecutables | `no` |

Esta gramática es normativa para el parser. `INDENT`/`DEDENT` son tokens
sintéticos producidos por el algoritmo de §60.10. `NEWLINE` termina una
sentencia; dentro de delimitadores inline se ignora.

### 60.1 Convenciones

```ebnf
(* Terminales léxicos: identifier, literal, integer, float, string, char,
   byte_char, RAW_TOKEN, NEWLINE, INDENT, DEDENT, EOF. Se definen en §2.8,
   §60.1 (RAW_TOKEN) y §60.10. *)
ident          ::= identifier
RAW_TOKEN      ::= (* token crudo balanceado, sin interpretar *)
raw_tokens     ::= RAW_TOKEN*
raw_region     ::= RAW_TOKEN*   (* hasta el DEDENT que cierra el bloque *)
```

1. La gramática es determinista con tokens de indentación; §62 resuelve las ambigüedades de expresiones.
2. `?` en EBNF significa opcional; `*` repetición cero o más; `+` una o más.
3. Los literales terminales van entre comillas.
4. `NEWLINE`, `INDENT`, `DEDENT` y `EOF` son terminales sintéticos.
5. Una producción por línea; `|` separa alternativas.
6. Los comentarios `(* … *)` son explicativos, no parte del lenguaje.

### 60.2 Programa y módulos

```ebnf
program        ::= shebang? module_body EOF
shebang        ::= "#!" [^\n]* NEWLINE
module_body    ::= (NEWLINE | inner_attrs | item)*
item           ::= attributes? visibility? item_kind
item_kind      ::= function_def
                 | struct_def
                 | enum_def
                 | trait_def
                 | impl_def
                 | alias_def
                 | const_def
                 | static_def
                 | mod_def
                 | use_def
                 | foreign_def
                 | macro_def
                 | rust_block
                 | grimoire_def

const_def      ::= "sigil" ident ":" type "=" expr NEWLINE
static_def     ::= "relic" ident ":" type "=" expr NEWLINE
mod_def        ::= "scroll" ident ( NEWLINE INDENT module_body DEDENT | "=" string NEWLINE )?
use_def        ::= "summon" path ("::" "*" | "::" "{" ident ("," ident)* ","? "}")? ("as" ident)? NEWLINE
foreign_def    ::= "foreign" string NEWLINE INDENT foreign_item* DEDENT
                 | "foreign" string ident "=" "(" params? ")" "->" type (NEWLINE INDENT body DEDENT | NEWLINE)
foreign_item   ::= attributes? "curse"? ident "=" "(" params? ")" "->" type NEWLINE
macro_def      ::= "incantation" ident NEWLINE INDENT raw_region DEDENT
rust_block     ::= "rust" NEWLINE INDENT raw_region DEDENT
grimoire_def   ::= modifier* "grimoire" (":" type)? NEWLINE INDENT body DEDENT

attributes     ::= attribute+
attribute      ::= "@@" attr_name ( "(" attr_args? ")" )? NEWLINE
inner_attrs    ::= "@@!" attr_name ( "(" attr_args? ")" )? NEWLINE
attr_name      ::= ident ("::" ident)*
attr_args      ::= attr_arg ("," attr_arg)* ","?
attr_arg       ::= literal | ident ("=" literal)? | "(" attr_args? ")" | "[" attr_args? "]"
visibility     ::= "unveil" ( "(" ( "tome" | "scroll" | "in" path ) ")" )?
```

1. `attributes` se aplica al item siguiente.
2. `inner_attrs` solo al inicio de un `scroll` o crate.
3. `visibility` sin paréntesis es `pub`.
4. `unveil(tome)` es `pub(crate)`; `unveil(scroll)` es `pub(super)`.
5. Un item sin `visibility` es privado.
6. `NEWLINE` es obligatorio entre items de nivel superior.
7. `EOF` debe seguir a un `DEDENT` si hay bloques abiertos.

### 60.3 Funciones y tests

```ebnf
function_def   ::= modifier* ident "=" type_params? "(" params? ")" "->" type
                   where_clause? ( NEWLINE INDENT body DEDENT )?
modifier       ::= "dream" | "curse" | "eternal"
type_params    ::= "[" type_param ("," type_param)* ","? "]"
type_param     ::= ident (":" bounds)?
                 | "const" ident ":" type
                 | lifetime
params         ::= param ("," param)* ","?
param          ::= receiver | "morph"? ident ":" type
receiver       ::= "@" | "@mut" | "@own"
body           ::= statement+
```

1. El tipo de retorno es obligatorio.
2. El cuerpo, si existe, va indentado en las líneas siguientes; no hay cuerpo
   inline `= expr` para funciones nombradas.
3. `dream` genera `async`; `curse` genera `unsafe`; `eternal` genera `const`.
4. Un `pact`/`foreign` puede omitir el cuerpo (solo firma).
5. `@@test`/`@@bench` son atributos de una `function_def` normal; no hay
   producción separada.
6. Las funciones nombradas no capturan; las lambdas sí.
7. `@`/`@mut`/`@own` solo son válidos como primer parámetro de un método.

### 60.4 Structs, enums y aliases

```ebnf
struct_def     ::= "rune" ident type_params? where_clause? struct_body
struct_body    ::= NEWLINE INDENT field* DEDENT
                 | "(" field_list ")"
                 | NEWLINE
field          ::= visibility? ident ":" type NEWLINE
field_list     ::= type ("," type)* ","?
enum_def       ::= "enchanting" ident type_params? where_clause? NEWLINE
                   INDENT variant+ DEDENT
variant        ::= ident ( "(" field_list ")" | NEWLINE INDENT field* DEDENT )?
                   ("=" integer)?
alias_def      ::= "essence" ident type_params? "=" type NEWLINE
```

1. `rune Marker` sin cuerpo es unit struct.
2. `rune Pair(Int, Int)` es tuple struct.
3. Los campos de tuple struct son privados.
4. `enchanting Shape` requiere al menos una variante.
5. Un discriminante solo se permite en variantes sin campos.
6. `essence` no crea un tipo nuevo; es un alias.
7. `where_clause` se define en §60.6.

### 60.5 Traits e impls

```ebnf
trait_def      ::= modifier* "pact" ident type_params? (":" bounds)? where_clause? NEWLINE
                   INDENT trait_item* DEDENT
trait_item     ::= function_def
                 | "essence" ident (":" bounds)? ("=" type)? NEWLINE
                 | "sigil" ident ":" type ("=" expr)? NEWLINE
impl_def       ::= modifier* "ritual" type ("for" type)? where_clause? NEWLINE
                   INDENT impl_item* DEDENT
impl_item      ::= function_def
                 | "essence" ident "=" type NEWLINE
                 | "sigil" ident ":" type "=" expr NEWLINE
```

1. `pact` declara un trait; `ritual Tipo for Pact` lo implementa.
2. Los métodos usan `@`, `@mut` o `@own` como primer parámetro.
3. Un método sin `@` es función asociada.
4. `essence` dentro de `pact` es associated type.
5. `sigil` dentro de `pact` es associated const.
6. Las implementaciones no pueden añadir métodos a un trait externo.
7. La coherencia/orphan la valida rustc.

### 60.6 Tipos

```ebnf
type           ::= path type_args?
                 | "(" ")"                              (* Unit *)
                 | "(" type ")"
                 | "(" type ("," type)+ ","? ")"
                 | "(" type ("," type)* ")" "->" type  (* fn type *)
                 | "[" type ";" expr "]"
                 | "[" type "]"
                 | "&" lifetime? "mut"? type
                 | "*" ("const" | "mut") type
                 | "!" type                              (* Result<T, Error> *)
                 | "?" type                              (* Option<T> *)
                 | "dyn" bounds
                 | "impl" bounds
                 | "for" "<" lifetime ("," lifetime)* ">" type
                 | "Self"
                 | "Never"
type_args      ::= generic_arg ("," generic_arg)* ","?
generic_arg    ::= lifetime | type | integer
path           ::= ident ("::" ident)*
bounds         ::= bound ("+" bound)*
bound          ::= path type_args? | path "(" type ("," type)* ")" "->" type | "for" "<" lifetime ("," lifetime)* ">" bound | lifetime
where_clause   ::= "where" where_pred ("," where_pred)* ","?
where_pred     ::= type ":" bounds
lifetime       ::= "'" ident
```

1. `?T` y `!T` son azúcar; se normalizan a `Option[T]`/`Result[T, Error]`.
2. `&T`/`&mut T` son referencias; `*const T`/`*mut T` son raw pointers.
3. `[T; N]` es array; `[T]` es slice (sin tamaño).
4. `dyn Trait` es trait object; `impl Trait` es tipo opaco.
5. `for<'a> T` es HRTB; `T` puede ser un fn type.
6. `Never` es `!`; `Unit` es `()`.
7. Los tipos de función son `(A, B) -> C`.

### 60.7 Expresiones y sentencias

```ebnf
statement      ::= binding
                 | assignment
                 | "return" expr? NEWLINE
                 | "break" (ident | expr)? NEWLINE
                 | "continue" ident? NEWLINE
                 | labeled_statement
                 | expr NEWLINE
binding        ::= ("bind" | "morph") pattern (":" type)? "=" expr ("else" NEWLINE INDENT body DEDENT)? NEWLINE
assignment     ::= assignment_expr NEWLINE
labeled_statement ::= ident ":" (for_stmt | while_stmt | loop_stmt)
for_stmt       ::= "for" pattern "in" expr ("by" expr)? NEWLINE INDENT body DEDENT
while_stmt     ::= "while" if_condition NEWLINE INDENT body DEDENT
loop_stmt      ::= "loop" NEWLINE INDENT body DEDENT
branch         ::= expr | NEWLINE INDENT body DEDENT

expr           ::= assignment_expr
assignment_expr::= range_expr (assignment_op assignment_expr)?
assignment_op  ::= "=" | "+=" | "-=" | "*=" | "/=" | "%=" | "&=" | "|=" | "^="
                 | "<<=" | ">>="
range_expr     ::= or_expr ( (".." | "..=") or_expr? )?
or_expr        ::= and_expr ("or" and_expr)*
and_expr       ::= not_expr ("and" not_expr)*
not_expr       ::= "not" not_expr | comparison
comparison     ::= bitor_expr ( ("==" | "!=" | "<" | "<=" | ">" | ">=" | "is" | "isnt" | "in") bitor_expr )?
bitor_expr     ::= bitxor_expr ("|" bitxor_expr)*
bitxor_expr    ::= bitand_expr ("^" bitand_expr)*
bitand_expr    ::= shift_expr ("&" shift_expr)*
shift_expr     ::= additive (("<<" | ">>") additive)*
additive       ::= multiplicative (("+" | "-") multiplicative)*
multiplicative ::= cast_expr (("*" | "/" | "%") cast_expr)*
cast_expr      ::= unary_expr ("as" type)*
unary_expr     ::= ("-" | "+" | "!" | "*" | "&" "raw" ("const" | "mut") | "&" "mut"? | "awaken") unary_expr
                 | postfix_expr
postfix_expr   ::= primary_expr postfix*
postfix        ::= "." ident
                 | "." decimal
                 | "(" args? ")"
                 | "[" expr "]"
                 | "?"
                 | "[" type_args "]" "(" args? ")"   (* turbofish call *)
                 | "!" ("(" raw_tokens? ")" | "[" raw_tokens? "]" | "{" raw_tokens? "}") (* macro call *)
primary_expr   ::= literal
                 | path
                 | struct_literal
                 | "Vec" "[" (array_items | expr ";" expr)? "]"
                 | "Set" "[" array_items? "]"
                 | "(" expr ")"
                 | "(" ")"
                 | "(" expr "," ")"
                 | "[" (array_items | expr ";" expr)? "]"
                 | "{" map_items? "}"
                 | indented_collection
                 | if_chain
                 | "unless" if_condition if_body ("else" if_body)?
                 | "match" expr NEWLINE INDENT match_arm+ DEDENT
                 | "loop" NEWLINE INDENT body DEDENT
                 | "while" if_condition NEWLINE INDENT body DEDENT
                 | "for" pattern "in" expr ("by" expr)? NEWLINE INDENT body DEDENT
                 | "do" NEWLINE INDENT body DEDENT
                 | "return" expr?
                 | "break" (ident | expr)?
                 | "continue" ident?
                 | "(" expr ("," expr)+ ","? ")"              (* tuple *)
                 | "[" expr "for" pattern "in" expr ("by" expr)? ("if" expr)? "]"   (* array comprehension *)
                 | "{" map_item "for" pattern "in" expr ("by" expr)? ("if" expr)? "}" (* map comprehension *)
                 | "curse" NEWLINE INDENT body DEDENT
                 | "dream" "do" NEWLINE INDENT body DEDENT
                 | "dream" lambda
                 | lambda
                 | block_expr

if_chain       ::= "if" if_condition if_body ("elseif" if_condition if_body)* ("else" if_body)?
if_body        ::= "then" branch | NEWLINE INDENT body DEDENT
if_condition   ::= pattern "=" expr | condition_expr
condition_expr ::= or_expr
struct_literal ::= path "(" field_init ("," field_init)* ","? (".." expr)? ")"
field_init     ::= ident (":" expr)?
```

1. La asignación es expresión solo en el parser; el typechecker la trata como
   sentencia (valor `Unit`).
2. `..`/`..=` tienen menor precedencia que `or` pero mayor que `=`.
3. `as` es left-associative; `a as T as U` = `(a as T) as U`.
4. `?` es postfix y solo en funciones compatibles.
5. `awaken` es prefijo y solo en `dream`.
6. `is`/`isnt` son `==`/`!=`; no encadenan.
7. `in` es membresía; no es un operador de rango.

### 60.8 Colecciones, lambdas y bloques

```ebnf
array_items    ::= expr ("," expr)* ","?
map_items      ::= map_item ("," map_item)* ","?
map_item       ::= (ident | expr) ":" expr
indented_collection ::= NEWLINE INDENT collection_body DEDENT
collection_body::= (map_item | expr) (NEWLINE (map_item | expr))*
lambda         ::= "move"? "(" params? ")" "=>" (expr | NEWLINE INDENT body DEDENT)
block_expr     ::= NEWLINE INDENT body DEDENT

match_arm      ::= "when" pattern ("if" expr)? "then" branch NEWLINE
                 | "when" pattern ("if" expr)? NEWLINE INDENT body DEDENT
                 | "else" "then"? branch NEWLINE
args           ::= expr ("," expr)* ","?
```

1. Una colección indentada sin delimitadores se clasifica en §2.6.
2. `map_item` con `ident` usa el nombre como clave string.
3. Un `lambda` con `=>` captura; `move` fuerza captura por valor.
4. Un `block_expr` devuelve el valor de su última expresión.
5. `match` debe ser exhaustivo o tener `else`.
6. `when` es contextual; no es palabra reservada global.

### 60.9 Patrones

```ebnf
pattern        ::= or_pattern
or_pattern     ::= primary_pattern ("|" primary_pattern)*
primary_pattern::= "_"
                 | literal
                 | ident ("@" pattern)?
                 | "ref" "mut"? ident
                 | "(" pattern ("," pattern)* ","? ")"
                 | "[" pattern ("," pattern)* ","? "]"
                 | path ("(" pattern_list? ")" | "{" field_patterns? "}")?
                 | path ".." 
                 | range_pattern
field_patterns ::= ident (":" pattern)? ("," ident (":" pattern)?)* ","?
pattern_list   ::= pattern ("," pattern)* ","?
range_pattern  ::= literal (".." | "..=") literal
```

1. `@` en patrón liga el valor completo; no es el receptor `@`.
2. `ref`/`ref mut` toman referencia al campo.
3. `..` en struct/lista ignora el resto.
4. Un rango de patrón debe ser exhaustivo o tener `else`.
5. Los patrones de camino deben resolver a una variante/struct.
6. `_` es irrefutable; los literales son refutables.
7. `if let`/`while let` usan `pattern` + `=`.

### 60.10 Indentación

```text
algoritmo:
  stack = [0]
  al inicio de cada línea lógica:
    si la línea está vacía o es solo comentario: ignorar
    medir indent = número de espacios iniciales
    si hay tab en la indentación: error PGS-E1003
    si indent > stack.top:
        emitir INDENT; push(indent)
    mientras indent < stack.top:
        emitir DEDENT; pop()
    si indent != stack.top: error PGS-E1004
    emitir tokens de la línea
    emitir NEWLINE
  al final: emitir DEDENT por cada nivel > 0; emitir EOF
```

1. La indentación se mide en espacios, no en columnas visuales.
2. Un nivel debe ser múltiplo de 4; si no, `PGS-E1005`.
3. No se permite mezclar tabs y espacios.
4. Una línea de continuación dentro de `()`/`[]`/`{}` no genera INDENT.
5. Un `NEWLINE` dentro de delimitadores inline se ignora.
6. Un `NEWLINE` después de `..`/`..=` continúa el rango.
7. Un `DEDENT` inesperado es `PGS-E1004`.

### 60.11 Manifiesto

`Tome.toml` no es PenguScript; su gramática es TOML 1.0. Las claves de
`[tome]`, `[dependencies]`, `[features]`, `[[bin]]`, `[[test]]`, `[profile.*]`
y `[workspace]` se definen en §43. El compilador valida:

1. `name` y `version` obligatorios.
2. `pengu` y `rust-version` compatibles.
3. `path` de targets con extensión `.pengu`.
4. `[cargo]` no puede sobrescribir claves protegidas.
5. Un `Tome.lock` generado no se edita.

### 60.12 Criterios de aceptación

- [x] La gramática cubre las construcciones normativas; los fragmentos didácticos pueden omitir contexto de módulo.
- [x] Léxico, items, tipos, expresiones, patrones y atributos están definidos.
- [x] El algoritmo de indentación es determinista.
- [x] Las ambigüedades se resuelven en §62.
- [x] La gramática puede alimentar un parser determinista con tokens de indentación.

[↑ Volver al índice](#indice)

<a id="sec-61-lexico-keywords"></a>
## 61. Léxico y palabras clave

| Campo | Valor |
|---|---|
| Estado | `completo` |
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
| Control | `if`, `elseif`, `else`, `unless`, `match`, `for`, `while`, `loop`, `break`, `continue`, `return`, `do` |
| Operadores/palabras | `and`, `or`, `not`, `is`, `isnt`, `in`, `as`, `where`, `dyn`, `impl` |
| Literales | `true`, `false`, `none` |
| Recepción | `@`, `@mut`, `@own` (no son identificadores) |
| Tipos especiales | `Self`, `Unit`, `Never` |

### 61.3 Contextuales

Solo son palabras clave en la posición indicada; fuera de ella pueden ser
identificadores. Las demás palabras de §61.2 son **reservadas** y no pueden ser
identificadores.

| Palabra | Contexto | Fuera del contexto |
|---|---|---|
| `by` | tras el iterable de `for` | identificador normal |
| `when` | inicio de brazo de `match` | identificador normal |
| `then` | tras condición inline de `if`/`unless`/`when` | identificador normal |
| `tome` | `unveil(tome)` | identificador normal |

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

Las palabras retiradas (`spell`, `spirit`, `bind mut`) se rechazan con `PGS-E1010`; el resto, con `PGS-E6101`. En ambos casos se sugiere un reemplazo.

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
| `do` … `while` (do-while) | No existe el bucle `do`-`while`; `do` solo es un bloque | `loop` + `break` |
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

<a id="sec-62-precedencia"></a>
## 62. Precedencia y asociatividad

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 10 |
| Rust | — |
| Palabras mágicas | — |
| Depende de | §11, §13, §14 |
| Ejemplos ejecutables | `no` |

### 62.1 Tabla normativa

De mayor a menor precedencia. La columna “Asoc.” indica asociatividad;
“no asoc.” exige paréntesis si se encadena.

| Nivel | Operadores | Asoc. | Notas |
|---:|---|---|---|
| 1 | `.` `()` `[]` `?` turbofish | izquierda | postfix; `?` solo en `!T` |
| 2 | `awaken` | prefijo | solo en `dream` |
| 3 | `-` `+` `!` `*` `&` `&mut` | prefijo | unarios |
| 4 | `as` | izquierda | casts encadenados |
| 5 | `*` `/` `%` | izquierda | aritmética |
| 6 | `+` `-` | izquierda | aritmética |
| 7 | `<<` `>>` | izquierda | shifts |
| 8 | `&` | izquierda | bitwise and |
| 9 | `^` | izquierda | bitwise xor |
| 10 | `\|` | izquierda | bitwise or |
| 11 | `..` `..=` | no asoc. | rangos; extremo derecho opcional |
| 12 | `==` `!=` `<` `<=` `>` `>=` `is` `isnt` `in` | no asoc. | comparaciones |
| 13 | `not` | prefijo | negación lógica |
| 14 | `and` | izquierda | cortocircuito |
| 15 | `or` | izquierda | cortocircuito |
| 16 | `=` `+=` `-=` `*=` `/=` `%=` `&=` `\|=` `^=` `<<=` `>>=` | derecha | sentencia; no usable como valor |

### 62.2 Reglas de parseo

1. `a + b * c` = `a + (b * c)`.
2. `a as T + b` = `(a as T) + b`.
3. `-a as T` = `(-a) as T`; para `-(a as T)` se usan paréntesis.
4. `a..b + 1` = `a..(b + 1)`, porque `+` tiene más precedencia que `..`.
5. `a..=b` y `a..` son rangos; `..b` no es válido en expresión (solo patrón).
6. `a == b == c` es error `PGS-E6201`; usar `(a == b) and (b == c)`.
7. `a < b < c` es error `PGS-E6201`.
8. `a is b`/`a isnt b` son `==`/`!=`; misma precedencia que comparaciones.
9. `x in xs` es membresía; `not x in xs` se parsea `not (x in xs)`.
10. `a and b or c` = `(a and b) or c`.
11. `a or b and c` = `a or (b and c)`.
12. `a = b = c` es error `PGS-E6202`; la asignación no encadena.
13. `a += b + c` = `a += (b + c)`.
14. `*p = x` requiere `curse`; el parser no cambia la precedencia.
15. `&mut x` es un prefijo único; no se parsea como `& (mut x)`.
16. `foo[Int](x)` y `foo[0]` se parsean como `GenericOrIndex`; la resolución
    de nombres decide si `[...]` es lista de tipos (seguida de `(`) o índice.
    Si ambas lecturas son válidas, el compilador emite `PGS-E6203`.
17. `foo.bar[T](x)` es método genérico; `foo.bar[0]` es índice del campo.
18. `a?.b` = `(a?).b`; `a?` se evalúa antes del campo.
19. `a.b?` = `(a.b)?`.
20. `awaken f()?` = `(awaken f())?`; `awaken` es prefijo y se evalúa antes de `?`.

### 62.3 Ambigüedades resueltas

| Caso | Resolución |
|---|---|
| `foo[Int](x)` | genérico si `Int` resuelve a tipo y sigue `(`; si no, error |
| `foo[0]` | indexación; `0` es expresión |
| `foo[T]` sin `(` | indexación; para tipo se usa `foo[T]()` |
| `a < b > c` | error de comparación encadenada |
| `a..b` | rango; no es acceso a campo |
| `x @ pat` | binding de patrón, no receptor |
| `@` al inicio de línea | receptor en método; en patrón, binding |
| `-x.abs()` | `-(x.abs())` |
| `not a == b` | `not (a == b)` |
| `a as T?` | `(a as T)?` |
| `a? as T` | `(a?) as T` |
| `..=` sin izquierda | solo válido en patrón |
| `a..` | rango abierto; válido en expresión |
| `a..=..` | error `PGS-E6203` |

### 62.4 Tabla de resultados

| Expresión | Parseo |
|---|---|
| `1 + 2 * 3` | `1 + (2 * 3)` |
| `1 << 2 + 3` | `1 << (2 + 3)` porque `+` (6) tiene más precedencia que `<<` (7) |
| `1 & 2 == 0` | `(1 & 2) == 0` |
| `not a and b` | `(not a) and b` |
| `a or b and c` | `a or (b and c)` |
| `a..b + 1` | `a..(b + 1)` |
| `a + b..c` | `(a + b)..c` |
| `a as Int + 1` | `(a as Int) + 1` |
| `-a * b` | `(-a) * b` |
| `!a and b` | `(!a) and b` |
| `a?.b` | `(a?).b` |
| `a.b?` | `(a.b)?` |
| `awaken f()?` | `(awaken f())?` |
| `x in xs and y` | `(x in xs) and y` |

### 62.5 Criterios de aceptación

- [x] Hay una fila por nivel de precedencia.
- [x] La asociatividad está especificada.
- [x] Las comparaciones encadenadas se rechazan.
- [x] La asignación no encadena.
- [x] `as`, `?`, rangos y `awaken` tienen reglas explícitas.
- [x] Las ambigüedades de `[]` se resuelven.

[↑ Volver al índice](#indice)

<a id="sec-63-paridad-rust"></a>
## 63. Matriz de paridad Rust

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 10 |
| Rust | Rust 2024 estable, MSRV 1.85.0 |
| Palabras mágicas | todas |
| Depende de | §1–§59 |
| Ejemplos ejecutables | `no` |

### 63.1 Leyenda

| Estado | Significado |
|---|---|
| `Completo` | La construcción se expresa en PenguScript y se mapea a Rust sin pérdida semántica. |
| `Parcial` | Se expresa con una limitación documentada; el generador puede emitir Rust o exigir un `rust` block auditado. |
| `Diferido` | No está en el núcleo actual; hay una sección/ADR y una alternativa. |
| `No soportado` | No se puede expresar por diseño; se documenta la razón y la alternativa. |

`Parcial` no significa “roto”: significa que el usuario debe conocer una
restricción (por ejemplo, proc macros definidas en Rust). `Diferido` tiene
una fase o una decisión pendiente; no hay filas “TBD”.

### 63.2 Matriz

| # | Área de Rust | Sección(es) | Estado | Notas |
|---:|---|---|---|---|
| 1 | Items y declaraciones | §15, §28, §29, §31, §35, §41, §43 | Completo | `rune`/`enchanting`/`pact`/`ritual`/`essence`/`scroll`. |
| 2 | Visibilidad y paths | §41, §42 | Completo | `unveil`, `crate::`, `super::`; no `self::`. |
| 3 | Genéricos de tipo | §33 | Completo | `[T]`, turbofish. |
| 4 | Genéricos de lifetime | §33, §37 | Completo | `['a]`, `for<'a>`. |
| 5 | Const generics | §33, §54 | Completo | `[const N: Usize]`. |
| 6 | Bounds y `where` | §34 | Completo | Incluye `?Sized`, associated bounds. |
| 7 | Traits y defaults | §35 | Completo | `pact`; sin herencia de clases. |
| 8 | Associated types/consts/GATs | §36 | Completo | GAT con `where Self: 'a`. |
| 9 | `impl Trait` y RPITIT | §35, §36 | Completo | Incluye `async fn` en trait. |
| 10 | Trait objects (`dyn`) | §35 | Completo | Object safety la valida rustc. |
| 11 | Impls y coherencia | §31, §35 | Completo | Reglas de orphan de Rust. |
| 12 | Ownership/move | §16 | Completo | Sin GC. |
| 13 | `Copy`/`Clone`/`Drop` | §16, §21, §46 | Completo | `Drop` explícito. |
| 14 | Borrowing/NLL | §17 | Completo | Mismas reglas que rustc. |
| 15 | Lifetimes/elisión/variance | §18 | Completo | Tabla de elisión propia. |
| 16 | Referencias y raw pointers | §19 | Completo | Raw solo en `curse`. |
| 17 | Smart pointers | §20 | Completo | `Box`, `Rc`, `Arc`, `Cow`, etc. |
| 18 | Interior mutability | §20, §51 | Completo | `Cell`, `RefCell`, `Mutex`, `RwLock`, `UnsafeCell` en `curse`. |
| 19 | Primitivos/literales/overflow | §9 | Completo | Overflow checks siempre. |
| 20 | Strings/chars/UTF-8 | §10 | Completo | Sin indexación por byte. |
| 21 | Arrays y slices | §22 | Completo | `[T; N]`, `&[T]`, `&mut [T]`. |
| 22 | `Vec`/`VecDeque` | §23 | Completo | Incluye `VecDeque`. |
| 23 | Tuplas | §24 | Completo | Hasta 12 traits estándar. |
| 24 | Mapas y sets | §25 | Completo | `HashMap`, `HashSet`, `BTreeMap`, `BTreeSet`. |
| 25 | Otras colecciones | §26 | Completo | `LinkedList`, `BinaryHeap`; crates externas. |
| 26 | Rangos e indexación | §27 | Completo | `..`, `..=`, slicing seguro. |
| 27 | Structs | §28 | Completo | Named/tuple/unit. |
| 28 | Enums/discriminantes | §29 | Completo | `@@repr`, niche. |
| 29 | Pattern matching | §30 | Completo | Exhaustividad. |
| 30 | Type aliases/newtypes/casts | §32 | Completo | `as`, `From`/`Into`, `TryFrom`. |
| 31 | Operadores | §11, §40 | Completo | Sobrecarga vía traits. |
| 32 | Control de flujo | §8, §13, §14 | Completo | `if`, `unless`, `match`, `loop`, `while`, `for`, `do`. |
| 33 | Funciones/recursión | §15 | Completo | Retorno explícito, cuerpo implícito. |
| 34 | Closures | §38 | Completo | `=>`, `move`, `Fn*`. |
| 35 | Function pointers/HOF | §39 | Completo | `fn` tipos y valores. |
| 36 | Módulos y prelude | §41 | Completo | `scroll`, `summon`. |
| 37 | Crates/packages/workspaces | §43 | Completo | `Tome.toml`; `[cargo]` passthrough. |
| 38 | Features y cfg | §47 | Completo | Aditivas; `@@cfg`. |
| 39 | Atributos | §44 | Completo | `@@`, `@@!`. |
| 40 | Derives estándar | §46 | Completo | 9 derives + externos. |
| 41 | Macros declarativas | §45 | Completo | `incantation` -> `macro_rules!`. |
| 42 | Proc macros (definición) | §45 | Parcial | Se consumen; definirlas requiere Rust. |
| 43 | Proc macros (consumo) | §44, §45, §46 | Completo | `@@derive`, `@@attr`, `name!`. |
| 44 | `Option`/`Result`/`?` | §48 | Completo | `?T`, `!T`, `?`. |
| 45 | `panic`/unwinding | §48, §52 | Completo | `panic`, `catch_unwind` en `curse`. |
| 46 | Iteradores | §49 | Completo | Adaptadores/consumidores. |
| 47 | Async/await | §50 | Completo | `dream`/`awaken`; executor externo. |
| 48 | `Future`/`Pin`/`Unpin` | §50 | Completo | `Pin` explícito. |
| 49 | Threads | §51 | Completo | `std::thread`, scoped threads. |
| 50 | `Send`/`Sync` | §51 | Completo | Auto traits de Rust. |
| 51 | Channels | §51 | Completo | `mpsc`, `sync_channel`. |
| 52 | Atomics/ordering | §51 | Completo | `Atomic*`, `Ordering`. |
| 53 | `OnceLock`/`LazyLock`/TLS | §51 | Completo | `@@thread_local`. |
| 54 | Rayon/paralelismo | §51 | Parcial | Dependencia externa; feature. |
| 55 | Unsafe | §52 | Completo | `curse` + `-- SAFETY:`. |
| 56 | Unions | §52 | Completo | `chimera` + `@@repr(C)`. |
| 57 | `transmute` | §52 | Completo | Solo en `curse`. |
| 58 | `MaybeUninit`/`ManuallyDrop` | §52 | Completo | Requiere `curse`. |
| 59 | Inline asm | §52 | Parcial | `asm!`/`global_asm!` vía `rust` block auditado. |
| 60 | FFI | §53 | Parcial | `foreign "C"`, `@@no_mangle`, `repr(C)`; variádicas C diferidas. |
| 61 | Bindgen/cbindgen | §53 | Parcial | Herramientas externas; flujo documentado. |
| 62 | Const eval/`const fn` | §54 | Completo | `sigil`, `eternal`. |
| 63 | `no_std` | §55 | Completo | `core`/`alloc`. |
| 64 | Embebido | §55 | Parcial | Targets/`cortex-m`/`embassy`; depende de toolchain. |
| 65 | WASM | §55, §53 | Parcial | `wasm32-unknown-unknown`; JS glue externo. |
| 66 | Testing | §56 | Completo | `@@test`, `@@should_panic`, `@@ignore`. |
| 67 | Doc tests | §57 | Completo | `pengu doc --test`. |
| 68 | Benchmarks | §56 | Parcial | Harness externo (`criterion`/`divan`). |
| 69 | Property testing/fuzzing | §56 | Parcial | Crates externas (`proptest`, `cargo-fuzz`). |
| 70 | Documentación | §57 | Completo | `---`, `--!`, intra-doc links. |
| 71 | Formatter/linter/LSP | §58 | Completo | `pengu fmt`, `pengu lint`, `pengu lsp`. |
| 72 | Source maps/diagnósticos | §3, §58 | Completo | `sourcemap.json`; remapeo. |
| 73 | Build scripts | §47 | Completo | `build.pengu` -> `build.rs`. |
| 74 | Reproducibilidad/audit | §58 | Completo | `Tome.lock`, `pengu audit`. |
| 75 | Cross-compilation | §55, §58 | Parcial | Requiere target Rust instalado. |
| 76 | Miri/valgrind/sanitizers | §52, §58 | Parcial | Herramientas externas sobre Rust generado. |
| 77 | `cargo` ecosystem | §43, §58 | Completo | Passthrough y comandos propios. |
| 78 | `rustfmt`/`clippy` | §58 | Completo | Se ejecutan sobre Rust generado. |
| 79 | `cargo doc`/`rustdoc` | §57 | Completo | `pengu doc`. |
| 80 | `cargo publish`/registro | §58 | Completo | `pengu publish`; registro compatible. |
| 81 | `cargo expand` | §58 | Parcial | Solo sobre Rust generado. |
| 82 | Reflection/runtime eval | — | No soportado | Sin runtime/GC; usar macros/código explícito. |
| 83 | Herencia de clases | — | No soportado | `pact` + composición. |
| 84 | Excepciones | — | No soportado | `!T` + `?`. |
| 85 | Null/truthiness | — | No soportado | `?T`; `Bool` estricto. |
| 86 | Globales mutables | — | No soportado | `sigil`/`relic`/`@@shared`. |
| 87 | `static mut` | — | No soportado | `@@shared` + `Mutex`/atomics. |
| 88 | GC/ARC implícito | — | No soportado | Ownership; `Rc`/`Arc` explícitos. |
| 89 | Metatablas/prototipos | — | No soportado | Tipos nominales. |
| 90 | `goto`/`switch`/`do-while` | — | No soportado | `loop`, `match`, `while`. |

### 63.3 Reglas de mantenimiento

1. Toda fila `Parcial` debe enlazar a una sección y explicar la limitación.
2. Toda fila `Diferido` debe tener una fase/ADR y una alternativa.
3. Toda fila `No soportado` debe explicar el motivo y la alternativa.
4. Si una feature de Rust no aparece, se añade antes de un release candidate.
5. La matriz se revisa en cada fase que añada una construcción nueva.
6. `Completo` no promete paridad de APIs de `std`; promete paridad de la
   construcción del lenguaje y su mapeo.
7. Las features inestables de Rust no se exponen; se documentan en §66.
8. Las herramientas externas se marcan `Parcial` aunque el flujo esté probado,
   porque su disponibilidad no la controla PenguScript.

### 63.4 Criterios de aceptación

- [x] No hay filas vacías ni `TBD`.
- [x] Cada fila tiene sección o “—”.
- [x] Cada `Parcial`/`Diferido`/`No soportado` tiene nota.
- [x] La matriz cubre lenguaje, std, toolchain y ecosistema.
- [x] Las limitaciones de proc macros y herramientas externas son explícitas.

[↑ Volver al índice](#indice)

<a id="sec-64-desugaring"></a>
## 64. Desugaring

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 10 |
| Rust | Rust 2024 |
| Palabras mágicas | todas |
| Depende de | §2–§59 |
| Ejemplos ejecutables | `no` |

El desugaring es la transformación de la forma superficial de PenguScript a
una forma core explícita; después el generador emite Rust. Las tablas son
normativas para el compilador y para entender el código generado.

### 64.1 Declaraciones y tipos

| Azúcar | Forma core | Rust |
|---|---|---|
| `bind x = e` | `let x: T = e` | `let x = e;` |
| `morph x = e` | `let mut x: T = e` | `let mut x = e;` |
| `sigil N: T = e` | constante de módulo | `const N: T = e;` |
| `relic N: T = e` | static inmutable | `static N: T = e;` |
| `rune P` + campos | struct nominal | `struct P { … }` |
| `rune P(A, B)` | tuple struct | `struct P(A, B);` |
| `rune M` | unit struct | `struct M;` |
| `enchanting E` | enum nominal | `enum E { … }` |
| `pact T` | trait | `trait T { … }` |
| `ritual T for U` | impl de trait | `impl T for U { … }` |
| `ritual T` | impl inherente | `impl T { … }` |
| `essence A = B` | alias | `type A = B;` |
| `scroll m` | módulo | `mod m { … }` |
| `summon p` | import | `use p;` |
| `unveil` | visibilidad | `pub` |
| `unveil(tome)` | visibilidad crate | `pub(crate)` |
| `unveil(scroll)` | visibilidad padre | `pub(super)` |
| `unveil(in p)` | visibilidad path | `pub(in p)` |
| `@@attr` | atributo externo | `#[attr]` |
| `@@!attr` | atributo interno | `#![attr]` |
| `grimoire` | entry point | `fn main()` |
| `incantation n` | macro declarativa | `macro_rules! n` |
| `chimera U` | union | `union U` |
| `foreign "C"` | extern block | `extern "C"` |
| `rust` block | passthrough auditado | tokens Rust |

### 64.2 Funciones, lambdas y métodos

| Azúcar | Forma core | Rust |
|---|---|---|
| `f = (x: T) -> U` + cuerpo indentado | función item | `fn f(x: T) -> U { … }` |
| `(x: T) => e` | lambda que captura | `\|x: T\| e` |
| `move (x: T) => e` | lambda move | `move \|x: T\| e` |
| `@` | receiver inmutable | `&self` |
| `@mut` | receiver mutable | `&mut self` |
| `@own` | receiver por valor | `self` |
| `dream f = ...` | función async | `async fn f(...)` |
| `curse f = ...` | función unsafe | `unsafe fn f(...)` |
| `eternal f = ...` | función const | `const fn f(...)` |
| `f?` en retorno `!T` | propagación | `f?` |
| `return e` | retorno temprano | `return e;` |
| `panic(msg)` | divergencia | `panic!("{}", msg)` |

Una lambda sin `move` captura por referencia cuando es posible; el borrow
checker decide. Una lambda con `move` captura por valor. Las funciones
nombradas nunca capturan.

### 64.3 Expresiones y control

| Azúcar | Forma core | Rust |
|---|---|---|
| `if c then a else b` | `match c { true => a, false => b }` | `if c { a } else { b }` |
| `unless c then a` | `if not c then a` | `if !c { a; }` |
| `if c then a` sin else | rama `Unit` | `if c { a; }` |
| `match e` + `when p then x` | match | `match e { p => x, … }` |
| `when p if g then x` | guard | `p if g => x` |
| `else x` | wildcard | `_ => x` |
| `loop` + `break v` | loop con valor | `loop { break v; }` |
| `while c` | while | `while c { … }` |
| `for p in xs` | for | `for p in xs { … }` |
| `for p in a..b` | range for | `for p in a..b { … }` |
| `for p in xs by n` | step_by | `for p in xs.step_by(n) { … }` |
| `break` | break unit | `break;` |
| `continue` | continue | `continue;` |
| `outer: for …` | label | `'outer: for …` |
| `[e for x in xs if p]` | filter/map/collect | `xs.iter().filter(…).map(…).collect::<Vec<_>>()` |
| `{k: v for x in xs}` | map collect | `xs.iter().map(…).collect::<HashMap<_,_>>()` |
| `do` + bloque | block expression | `{ … }` |
| `a and b` | cortocircuito | `a && b` |
| `a or b` | cortocircuito | `a \|\| b` |
| `not a` | negación | `!a` |
| `a is b` | igualdad | `a == b` |
| `a isnt b` | desigualdad | `a != b` |
| `x in xs` | membresía | `xs.contains(&x)` |
| `a..b` | range | `a..b` |
| `a..=b` | range inclusive | `a..=b` |
| `a?` | try | `a?` |
| `awaken f` | await | `f.await` |
| `&raw const x` | raw ref | `&raw const x` |
| `&raw mut x` | raw ref mut | `&raw mut x` |

### 64.4 Colecciones y literal patterns

| Azúcar | Forma core | Rust |
|---|---|---|
| `[a, b]` | array | `[a, b]` |
| `[e; n]` | array repetido | `[e; n]` |
| `Vec[a, b]` | vector | `vec![a, b]` |
| `Set[a, b]` | set | `HashSet::from([a, b])` |
| `{ "k": v }` | map | `HashMap::from([("k", v)])` |
| `(a, b)` | tupla | `(a, b)` |
| `(a,)` | tupla de uno | `(a,)` |
| `()` | unit | `()` |
| `@` en patrón | binding | `x @ pat` |
| `ref x` | referencia | `ref x` |
| `ref mut x` | referencia mutable | `ref mut x` |
| `p1 \| p2` | or-pattern | `p1 \| p2` |
| `[first, .., last]` | slice pattern | `[first, .., last]` |
| `0..=9` en patrón | range pattern | `0..=9` |
| `if p = e then a` | if let | `if let p = e { a }` |
| `while p = e` | while let | `while let p = e { … }` |
| `bind p = e else b` | let-else | `let p = e else { b };` |

### 64.5 Errores, iteradores, async y concurrencia

| Azúcar | Forma core | Rust |
|---|---|---|
| `?T` | `Option<T>` | `Option<T>` |
| `!T` | `Result<T, Error>` | `Result<T, Box<dyn Error + Send + Sync>>` |
| `none` | `None` | `None` |
| `some(x)` | `Some(x)` | `Some(x)` |
| `ok(x)` | `Ok(x)` | `Ok(x)` |
| `err(e)` | `Err(e)` | `Err(e)` |
| `?` | early return | `?` |
| `panic(msg)` | panic | `panic!("{}", msg)` |
| `assert(c)` | assert | `assert!(c)` |
| `iter` | `iter()` | `.iter()` |
| `iter_mut` | `iter_mut()` | `.iter_mut()` |
| `into_iter` | `into_iter()` | `.into_iter()` |
| `dream do` | async block | `async { … }` |
| `dream (x) => e` | async closure | `\|x\| async move { e }` |
| `awaken e` | await | `e.await` |
| `thread.spawn` | thread spawn | `std::thread::spawn` |
| `Arc.new(Mutex.new(x))` | shared state | `Arc::new(Mutex::new(x))` |
| `lock` | lock guard | `.lock().unwrap()` |
| `@@thread_local` | TLS | `thread_local!` |
| `@@shared` | shared static | `static` + `Mutex`/atomics |

### 64.6 Macros, atributos y build

| Azúcar | Forma core | Rust |
|---|---|---|
| `incantation n` | macro_rules | `macro_rules! n { … }` |
| `n!(tokens)` | macro invocation | `n!(tokens)` |
| `$x` | metavariable | `$x` |
| `$(…)*` | repetición | `$(…)*` |
| `$crate` | crate de la macro | `$crate` |
| `unveil incantation` | export | `#[macro_export]` |
| `@@derive(A, B)` | derive | `#[derive(A, B)]` |
| `@@repr(C)` | repr | `#[repr(C)]` |
| `@@cfg(...)` | cfg | `#[cfg(...)]` |
| `@@cfg_attr(...)` | cfg_attr | `#[cfg_attr(...)]` |
| `@@test` | test | `#[test]` |
| `@@should_panic` | test panic | `#[should_panic]` |
| `@@ignore` | test ignore | `#[ignore]` |
| `@@no_mangle` | symbol | `#[unsafe(no_mangle)]` |
| `build.pengu` | build script | `build.rs` |
| `out_dir()` | env var | `std::env::var("OUT_DIR")` |
| `println("cargo:...")` | directive | `println!("cargo:...")` |

### 64.7 Manifiesto y codegen

| PenguScript | Rust/Cargo |
|---|---|
| `Tome.toml` | `Cargo.toml` generado |
| `[tome] name` | `[package] name` |
| `[tome] version` | `[package] version` |
| `[tome] edition` | `[package] edition` |
| `[tome] rust-version` | `[package] rust-version` |
| `[dependencies]` | `[dependencies]` (versiones compatibles) |
| `[[bin]] path = "main.pengu"` | `[[bin]] path = "src/main.rs"` |
| `[[test]] path = "tests/x.pengu"` | `[[test]] path = "tests/x.rs"` |
| `[features]` | `[features]` |
| `[workspace]` | `[workspace]` |
| `[cargo]` | claves passthrough permitidas |
| `main.pengu` | `src/main.rs` |
| `lib.pengu` | `src/lib.rs` |
| `foo.pengu` | `src/foo.rs` |
| `foo/scroll.pengu` | `src/foo/mod.rs` |
| `build.pengu` | `build.rs` |
| `sourcemap.json` | mapa byte/rango Pengu -> Rust |

### 64.8 Invariantes

1. El desugaring preserva el orden de evaluación de izquierda a derecha.
2. No introduce `unsafe` salvo que la construcción lo exija (`curse`, `transmute`,
   `asm`, raw pointer).
3. No oculta asignaciones: `morph` es la única forma de mutación de un binding.
4. No hay asignación dentro de una expresión salvo como sentencia explícita.
5. Las macros expanden tokens, no AST de PenguScript.
6. Un bloque `rust` se copia tal cual; no se desugara.
7. Los nombres generados son deterministas (misma entrada -> mismo Rust).
8. El sourcemap conserva la relación expresión/token con el Rust emitido.

### 64.9 Criterios de aceptación

- [x] Cada azúcar importante tiene fila.
- [x] Las filas incluyen la forma core y el Rust.
- [x] Las transformaciones no cambian la semántica.
- [x] Las construcciones que requieren `unsafe` lo indican.
- [x] El codegen y el manifiesto están cubiertos.

[↑ Volver al índice](#indice)

<a id="sec-65-diagnosticos"></a>
## 65. Catálogo de diagnósticos

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 10 |
| Rust | — |
| Palabras mágicas | — |
| Depende de | §2–§70 |
| Ejemplos ejecutables | `no` |

Este catálogo reúne los códigos `PGS-E...` y `PGS-W...` definidos en la especificación. La columna **Sección** indica dónde se explica el diagnóstico; si un código aparece en varias, se lista la primera aparición. Los códigos no se inventan aquí: se extraen de las tablas y del texto de las secciones.

**Total:** 486 códigos únicos (400 errores, 86 warnings).

### 65.1 Convención

| Prefijo | Significado |
|---|---|
| `PGS-E` | Error: el programa no compila. |
| `PGS-W` | Warning: el programa compila; puede silenciarse con `@@allow`. |
| `PGS-E10xx`–`E14xx` | Léxico, variables, programa, tipos y scope. |
| `PGS-E16xx`–`E21xx` | Ownership, borrowing, lifetimes, punteros, smart pointers y memoria. |
| `PGS-E22xx`–`E27xx` | Colecciones. |
| `PGS-E28xx`–`E32xx` | Structs, enums, patrones, impls y aliases. |
| `PGS-E33xx`–`E40xx` | Genéricos, traits, closures, HOF y operadores. |
| `PGS-E41xx`–`E47xx` | Módulos, visibilidad, tomes, atributos, macros, derives y build. |
| `PGS-E48xx`–`E59xx` | Errores, iteradores, async, concurrencia, unsafe, FFI, const, no_std, testing, docs, tooling y estilo. |
| `PGS-E61xx`–`E70xx` | Apéndices: léxico, precedencia, no soportado y versionado. |
| `PGS-E9xxx` | Primitivos, strings, operadores y control. |

### 65.2 Catálogo por familia

**Total:** 486 códigos únicos (400 errores, 86 warnings).

#### 65.2.10 Familia `10xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E1001` | BOM al inicio del archivo | guardar sin BOM | §2 |
| `PGS-E1002` | `CR` suelto o salto no válido | usar `LF` o `CRLF` | §2 |
| `PGS-E1003` | tabulador fuera de string/comentario | reemplazar por cuatro espacios | §2 |
| `PGS-E1004` | `DEDENT` sin nivel coincidente | alinear con un nivel abierto | §2 |
| `PGS-E1005` | `INDENT` inesperado o aumento no múltiplo de cuatro | eliminar la indentación, abrir un bloque o usar 4 espacios | §2 |
| `PGS-E1006` | falta el bloque esperado | indentar el cuerpo con cuatro espacios | §2 |
| `PGS-E1007` | comentario o string sin cerrar | cerrar `]]`, `"` o `"""` | §2 |
| `PGS-E1008` | escape inválido | usar un escape de §2.5 | §2 |
| `PGS-E1009` | literal inválido | revisar dígitos, sufijo o separador | §2 |
| `PGS-E1010` | `spell`/`spirit` retirados | usar `->` o `@` | §2 |
| `PGS-E1011` | cuerpo indentado mezcla entradas de mapa y expresiones | elegir mapa o array | §2 |
| `PGS-E1012` | cuerpo indentado vacío | usar `[]`, `{}`, `Vec[]` o `Set[]` | §2 |

#### 65.2.11 Familia `11xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E1101` | `bind`/`morph` no permitido en el módulo | Usa `sigil` o `relic`; si es estado local, muévelo a `grimoire` o a una función | §5 |
| `PGS-E1102` | no se puede reasignar un binding inmutable | Declara con `morph` si la mutación es intencional; si no, crea un binding nuevo | §5 |
| `PGS-E1103` | binding usado antes de inicializarse | Inicializa en la declaración o asigna en todas las rutas previas | §5 |
| `PGS-E1104` | no se puede inferir el tipo sin inicializador | Añade una anotación de tipo o un inicializador | §5 |
| `PGS-E1105` | binding duplicado en el mismo scope | Usa un nombre distinto o un bloque interior para shadowing | §5 |
| `PGS-E1106` | destino de asignación inválido | Asigna a una variable, campo o índice; no a una expresión temporal | §5 |
| `PGS-E1107` | uso después de mover | Usa `clone`/`Copy` si corresponde, o reordena el flujo (§16) | §5 |
| `PGS-E1108` | mutación con préstamo compartido activo | Termina el préstamo o usa un préstamo mutable/interior mutability según §17 y §20 | §5 |

#### 65.2.12 Familia `12xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E1201` | `grimoire` en una biblioteca | moverlo a `main.pengu` | §3 |
| `PGS-E1202` | más de un `grimoire` en un binario | dejar uno | §3 |
| `PGS-E1203` | sentencia o `bind` en nivel de módulo | mover dentro de una función | §3 |
| `PGS-E1204` | no se encuentra el archivo del `scroll` | crear el archivo o usar cuerpo inline | §3 |
| `PGS-E1205` | módulo duplicado o nombre no coincide | alinear archivo y declaración | §3 |
| `PGS-E1206` | importación ambigua o no resuelta | usar una ruta explícita | §3 |
| `PGS-E1207` | item privado usado desde otro módulo | añadir `unveil` | §3 |
| `PGS-E1208` | `Tome.toml` inválido | revisar §3.7 y D17 | §3 |
| `PGS-E1209` | meta sin raíz `.pengu` | declarar `path` | §3 |
| `PGS-E1210` | source map inconsistente | reportar un bug del compilador | §3 |

#### 65.2.13 Familia `13xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E1301` | tipo esperado y tipo encontrado no coinciden | revisar la anotación o la expresión | §4 |
| `PGS-E1302` | no se puede inferir un tipo | añadir `: Tipo` | §4 |
| `PGS-E1303` | tipo desconocido | importarlo con `summon` o declararlo | §4 |
| `PGS-E1304` | faltan argumentos de tipo | añadir `[T]` | §4 |
| `PGS-E1305` | aridad de tipo incorrecta | revisar parámetros | §4 |
| `PGS-E1306` | `?`/`!` mal aplicado | usar `Option[T]`/`Result[T, E]` | §4 |
| `PGS-E1307` | trait bound no satisfecho | implementar el `pact` o ajustar el bound | §4 |
| `PGS-E1308` | implementación huérfana o solapada | mover el `pact`/tipo o eliminar el solapamiento | §4 |
| `PGS-E1309` | `dyn` no es object-safe | quitar métodos genéricos o usar `impl Trait` | §4 |
| `PGS-E1310` | `impl Trait` en posición inválida | moverlo a parámetro/retorno | §4 |

#### 65.2.14 Familia `14xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E1401` | nombre no resuelto | declararlo o importarlo | §7 |
| `PGS-E1402` | glob ambiguo | usar una ruta explícita | §7 |
| `PGS-E1403` | uso antes de la declaración local | mover la declaración | §7 |
| `PGS-E1404` | binding duplicado en el mismo bloque | usar shadowing en un bloque interno | §7 |
| `PGS-E1405` | item privado inaccesible | añadir `unveil` | §7 |
| `PGS-E1406` | `Self` fuera de `ritual`/`pact` | moverlo o cambiar por el tipo | §7 |
| `PGS-W1401` | shadowing de la prelude | renombrar si no es intencional | §7 |
| `PGS-W1402` | importación no usada | eliminarla o usarla | §7 |

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

#### 65.2.20 Familia `20xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E2001` | `Rc`/`RefCell` usado donde se exige `Send`/`Sync` | usar `Arc`/`Mutex` | §20 |
| `PGS-E2002` | `Box.clone` sin `T: Clone` | implementar `Clone` o mover | §20 |
| `PGS-E2003` | `RefCell` con préstamo mutable solapado | acortar el scope del `Ref`/`RefMut` | §20 |
| `PGS-E2004` | `Mutex` bloqueado dos veces en el mismo hilo | soltar el primer guard | §20 |
| `PGS-E2005` | `Pin` de un tipo que no se puede fijar | usar `Box::pin` o `Unpin` | §20 |
| `PGS-E2006` | `Cow` mutado sin `to_mut` | llamar `to_mut()` | §20 |
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
| `PGS-E3001` | patrón irrefutable en `if let` | usar `bind` o un patrón refutable | §30 |
| `PGS-E3002` | `match` no exhaustivo | añadir variante/`else` | §30 |
| `PGS-E3003` | tipo incompatible entre brazos | unificar o convertir | §30 |
| `PGS-E3004` | `..` en posición inválida | moverlo al final del patrón | §30 |
| `PGS-E3005` | falta `else` en `match` abierto | añadir `else` | §30 |
| `PGS-E3006` | binding `@` con nombre reservado | renombrar | §30 |
| `PGS-E3007` | `ref mut` sobre valor inmutable | usar `morph` | §30 |
| `PGS-E3009` | `else` de `let-else` no diverge | añadir `return`/`panic` | §30 |
| `PGS-E3010` | guarda no `Bool` | usar una condición `Bool` | §30 |
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
| `PGS-E5001` | `awaken` fuera de contexto async | marcar con `dream` | §50 |
| `PGS-E5002` | `dream` sin runtime en `grimoire` | añadir `@@tokio::main` o `block_on` | §50 |
| `PGS-E5003` | future no `Send` en `spawn` | usar `async move`/`Arc` | §50 |
| `PGS-E5004` | `awaken` en closure normal | usar `dream (..) =>` | §50 |
| `PGS-E5005` | `async fn` en trait no object-safe | usar `Pin<Box<dyn Future>>` | §50 |
| `PGS-E5006` | future no consumido | `awaken`, `spawn` o `drop` | §50 |
| `PGS-W5001` | `select!` sin cancelación segura | revisar recursos | §50 |
| `PGS-W5002` | runtime no especificado | declarar dependencia | §50 |

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

#### 65.2.66 Familia `66xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E6601` | Feature diferida o no soportada | consultar §66 y usar la alternativa | §66 |

#### 65.2.70 Familia `70xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
| `PGS-E7002` | Versión de `pengu` incompatible con `Tome.toml` | ajustar `pengu` o actualizar el compilador | §70 |
| `PGS-W7001` | Feature deprecada | migrar al reemplazo indicado en §70.4 | §70 |

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
| `PGS-E9010` | `NonZero.new(0)` no comprobado | usar `?`, `match` o `unwrap_or` antes de usarlo como `NonZero` | §9 |
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
| `PGS-E9205` | `&&` o `\|\|` usados | usar `and`/`or` | §11 |
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
| `PGS-E9303` | `&&`/`\|\|` usados | usar `and`/`or` | §12 |
| `PGS-E9304` | `not` sobre un tipo que no es `Bool` | usar `!` para enteros o una comparación | §12 |
| `PGS-E9305` | conversión implícita a `Bool` | escribir la comparación | §12 |
| `PGS-E9306` | `match` de `Bool` no exhaustivo | cubrir `true` y `false` | §12 |
| `PGS-W9301` | `&`/`\|` usados | usar `and`/`or` si se busca cortocircuito | §12 |

#### 65.2.94 Familia `94xx`

| Código | Situación | Solución | Sección |
|---|---|---|---|
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

<a id="sec-66-no-soportado"></a>
## 66. No soportado y diferido

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 10 |
| Rust | Rust 2024 estable |
| Palabras mágicas | — |
| Depende de | §1, §63 |
| Ejemplos ejecutables | `no` |

Esta sección separa lo que **no existe por diseño** de lo que está **diferido**
a una fase futura. Un lector no debe asumir que una feature de Rust ausente
es un olvido: cada fila tiene una razón y una alternativa.

### 66.1 No soportado por diseño

| Feature | Por qué no | Alternativa |
|---|---|---|
| Variables globales mutables | Rompen el análisis de ownership y la inicialización estática (§5, §6). | `sigil`, `relic`, `@@shared` + `Mutex`, paso explícito de estado. |
| `static mut` | Acceso sin sincronización; Rust lo está retirando. | `@@shared` + `Mutex`/`RwLock`/atomics, o `UnsafeCell` en `curse`. |
| Herencia de clases | Composición y traits son más predecibles; evita diamonds. | `rune` + `pact` + `ritual`; campos y delegación. |
| `this`/`self` como palabra | `@` es el receptor; `self` se reserva a Rust generado. | `@`, `@mut`, `@own`. |
| `null`/`nil`/`undefined` | Elimina una clase de errores; `Option` es explícito. | `?T`, `none`, `some`. |
| Truthiness | Un `if` solo acepta `Bool`; evita conversiones implícitas. | Comparar explícitamente; `if x != 0 then`. |
| Conversiones implícitas | Dificultan la inferencia y el codegen. | `as` para casts, `From`/`Into` explícitos. |
| Excepciones (`try`/`catch`) | `Result` es parte del tipo; no hay flujo invisible. | `!T`, `?`, `match`, `panic` para bugs. |
| `switch` | `match` cubre y verifica exhaustividad. | `match`/`when`/`else`. |
| `do` … `while` (do-while) | `loop` + `break` es más general. | `loop` con condición y `break`; `do` como bloque sí existe. |
| `goto` | Rompe estructuras y drop scopes. | `loop`/`break`, funciones, máquinas de estado. |
| `++`/`--` | Mutación oculta y precedence confusa. | `x += 1`, `x -= 1`. |
| `===`/`!==` | No hay coerción; `==` ya es estricto. | `is`/`isnt`. |
| `typeof`/`instanceof` | No hay reflexión de runtime. | `match` sobre enums, traits, tipos estáticos. |
| `eval` | No hay compilación en runtime; seguridad. | Macros, `rust` block auditado, generación externa. |
| Metatablas/prototipos | Modelo nominal y estático. | `rune`, `pact`, `ritual`. |
| GC/ARC implícito | Coste e imprevisibilidad; ownership explícito. | `Rc`/`Arc` cuando se necesiten. |
| Reflexión de tipos | No hay metadata de runtime. | Traits, enums, macros declarativas. |
| Herencia múltiple/mixins | Ambigüedad de métodos y estado. | Composición + traits. |
| Operadores definidos por el usuario | Se limitan a los traits de §40. | `Add`, `Index`, `PartialEq`, etc. |
| `default` en parámetros | Variantes y sobrecargas complican el ABI. | Funciones con nombre, structs de opciones, `Option`. |
| Varargs | ABI y tipos variables. | Slice `&[T]`, tuplas, macros. |
| Sobrecarga por firma | Resolución ambigua y codegen complejo. | Nombres distintos, traits, genéricos. |
| `macro_rules!` con expansión AST | Las macros expanden tokens, no AST tipado. | `incantation` + macros declarativas; proc macros en Rust. |
| Proc macros definidas en PenguScript | Requieren un crate compilado por rustc. | Consumir proc macros de crates Rust (§45). |
| `static` con destructor | Rust no lo permite; orden de drop incierto. | `OnceLock`/`LazyLock`, `@@thread_local`, `sigil`. |
| `become`/tail calls garantizados | No es estable ni portable. | `loop`/retorno explícito. |
| `dyn*`/`async` trait objects arbitrary | Inestable. | `dyn Future`, `Pin<Box<dyn Future>>`. |
| `#[global_allocator]` múltiple | Rust permite uno; el lenguaje no elige por ti. | Uno explícito en `no_std`/binario. |
| `no_std` con `std` implícito | Debe ser explícito. | `@@no_std`, `core`/`alloc`. |

### 66.2 Diferido

| Feature | Estado | Fase/ADR | Alternativa actual |
|---|---|---|---|
| Especialización de traits | Diferido | §69 D21 | Traits + dispatch explícito. |
| `generic_const_exprs` | Diferido | §69 D22 | Const generics simples; arrays fijos. |
| Tipos dependientes | Diferido | §69 D23 | Genéricos + validación runtime. |
| `async` closures con `for<'a>` complejo | Parcial | §38, §50 | `dream (…) => …`; `Box::pin`. |
| `try` blocks | Diferido | §48 | Función/closures que retornan `!T`. |
| Generadores/`yield` | Diferido | §49 | `Iterator` manual o `impl Iterator`. |
| `c_variadic` | Diferido | §53 | `foreign` con firma fija; wrappers Rust. |
| `extern type` | Diferido | §53 | Puntero opaco + `size_of` conocido. |
| Allocator API | Diferido | §55 | `@@global_allocator` + `alloc`. |
| SIMD portable (`std::simd`) | Diferido | §51 | Intrínsecos/`rust` block; autovectorización. |
| `#[target_feature]` dinámico | Parcial | §52 | `rust` block auditado; funciones específicas. |
| Inline asm complejo | Parcial | §52 | `asm!`/`global_asm!` en `rust` block auditado. |
| `#[naked]` functions | Diferido | §55 | `global_asm!` + `extern "C"`. |
| `#[coverage]`/instrumentación fina | Parcial | §58 | `pengu test --coverage` con herramientas Rust. |
| Miri/valgrind integrados | Parcial | §58 | Ejecutar sobre Rust generado. |
| `cargo expand` nativo | Parcial | §58 | Expandir el Rust generado. |
| Proc macro attributes definidos en Pengu | No soportado | §45 | Crate Rust + `@@attr`. |
| Macros 2.0 (`decl macro`) | Diferido | §45 | `macro_rules!` estable. |
| `macro_metavar_expr` | Diferido | §45 | `macro_rules!` sin metavariables extra. |
| `const` traits | Diferido | §54 | `const fn` + `sigil`. |
| `const` closures | Diferido | §54 | `eternal` fn + `sigil`. |
| `const` allocation/`Vec` en const | Parcial | §54 | Arrays fijos, `MaybeUninit` en `curse`. |
| `no_std` async executor | Parcial | §50, §55 | Executor externo (`embassy`). |
| WASM con JS glue automático | Parcial | §55 | `wasm-bindgen` externo; `rust` block. |
| Cross-compilation automática | Parcial | §55 | `rustup target add` + linker. |
| `cargo` publish a registro propio | Parcial | §58 | `pengu publish` + configuración. |
| Formatter/linter 100% paridad Rust | Parcial | §58 | `pengu fmt`/`lint` + rustfmt/clippy. |
| LSP con todas las refactorizaciones | Parcial | §58 | `pengu lsp` básico; edits textuales. |
| REPL | No soportado | §58 | `pengu run` con archivo; sin JIT. |
| Hot reload | No soportado | §58 | Recompilar y reiniciar. |
| `goto`/etiquetas arbitrarias | No soportado | §14 | `loop` etiquetado. |

### 66.3 Reglas

1. Una feature `No soportado` no se acepta ni con `@@allow`; el parser la rechaza.
2. Una feature `Diferido` se rechaza con `PGS-E6601` y un enlace a esta tabla.
3. Una feature `Parcial` se acepta con la limitación documentada; si el usuario
   necesita más, usa un `rust` block auditado (§52) o una crate Rust.
4. No se añade una feature a la tabla sin sección, alternativa y estado.
5. Las features inestables de Rust no se exponen como si fueran estables.
6. `rust` block no es una feature del lenguaje: es un escape hatch auditado;
   su contenido no está garantizado por la especificación.
7. La tabla se revisa en cada release candidate; un cambio de estado requiere
   ADR (§69).

### 66.4 Criterios de aceptación

- [x] Cada fila tiene motivo/estado y alternativa.
- [x] No se confunde “no soportado” con “aún no implementado”.
- [x] Las features inestables están fuera del núcleo.
- [x] Las alternativas son expresables en el lenguaje.
- [x] El escape hatch `rust` está acotado y auditado.

[↑ Volver al índice](#indice)

<a id="sec-67-glosario"></a>
## 67. Glosario

| Campo | Valor |
|---|---|
| Estado | `completo` |
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

### 67.8 Criterios de aceptación

- [x] Los términos mágicos, de memoria, tipos, errores y tooling están definidos.
- [x] Las definiciones no son circulares y enlazan a la sección normativa.
- [x] Los términos retirados se marcan como tales.

[↑ Volver al índice](#indice)

<a id="sec-68-cookbook"></a>
## 68. Cookbook

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 10 |
| Rust | Rust 2024 |
| Palabras mágicas | `grimoire`, `rune`, `dream`, `foreign`, `@@` |
| Depende de | §3, §15, §28, §48, §50, §53, §55 |
| Ejemplos ejecutables | `sí` |

Recetas mínimas, completas y compilables. Cada una muestra el PenguScript y
el Rust que genera el compilador. Los bloques `rust` se compilan con
`rustc --edition 2024`.

### 68.1 Hello world

```pengu
grimoire
    print("Hola, PenguScript")
```

```rust
fn main() {
    println!("Hola, PenguScript");
}
```

### 68.2 CLI con argumentos

```pengu
summon std::env

grimoire
    bind args = env.args().skip(1).collect::<Vec[String]>()
    if args.is_empty() then
        print("uso: saludo <nombre>")
        return 1
    print("Hola, #{args[0]}")
    0
```

```rust
use std::env;

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() {
        println!("uso: saludo <nombre>");
        std::process::exit(1);
    }
    println!("Hola, {}", args[0]);
}
```

### 68.3 Librería

```pengu
-- lib.pengu
unveil rune Point
    x: Float
    y: Float

unveil length = (@) -> Float
    Math.sqrt(@.x * @.x + @.y * @.y)
```

```rust
pub struct Point {
    pub x: f64,
    pub y: f64,
}

impl Point {
    pub fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }
}
```

### 68.4 Errores con `?`

```pengu
rune ParseError
    message: String

read_number = (text: &Str) -> !Int
    bind value = text.parse[Int]()?
    ok(value)
```

```rust
#[derive(Debug)]
struct ParseError {
    message: String,
}

fn read_number(text: &str) -> Result<i32, Box<dyn std::error::Error + Send + Sync>> {
    let value: i32 = text.parse()?;
    Ok(value)
}

fn main() {
    match read_number("42") {
        Ok(v) => println!("{v}"),
        Err(e) => println!("error: {e}"),
    }
}
```

### 68.5 Async

```pengu
dream fetch = (url: &Str) -> !String
    bind response = awaken http.get(url)?
    ok(awaken response.text()?)

dream main_async = () -> !Unit
    bind body = awaken fetch("https://example.com")?
    print(body.len())
    ok(())
```

El executor no forma parte del lenguaje; el Rust generado usa `.await` y el
runtime que elija el `Tome.toml` (Tokio, async-std, embassy, etc.).

```rust
async fn fetch(url: &str) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
    let _ = url;
    Ok(String::from("hola"))
}

async fn main_async() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let body = fetch("https://example.com").await?;
    println!("{}", body.len());
    Ok(())
}

fn main() {
    let _future = main_async();
}
```

### 68.6 FFI

```pengu
foreign "C"
    curse cos(x: Float) -> Float

grimoire
    curse
        print(cos(0.0))
```

```rust
#[link(name = "m")]
unsafe extern "C" {
    fn cos(x: f64) -> f64;
}

fn main() {
    unsafe {
        println!("{}", cos(0.0));
    }
}
```

### 68.7 Embebido (`no_std`)

```pengu
@@no_std

unveil rune Register
    value: UInt

unveil read = (ptr: *const UInt) -> UInt
    curse
        *ptr
```

```rust
#![no_std]

pub struct Register {
    pub value: u32,
}

pub unsafe fn read(ptr: *const u32) -> u32 {
    *ptr
}
```

### 68.8 WASM

```toml
[tome]
name = "hello-wasm"
version = "0.1.0"
pengu = "1.0"
edition = "2024"
rust-version = "1.85"

[lib]
path = "lib.pengu"

[dependencies]
wasm-bindgen = "0.2"
```

```pengu
summon wasm_bindgen::prelude::*

@@wasm_bindgen
unveil greet = (name: &Str) -> String
    format("Hola, #{name}")
```

El glue JS y `wasm-bindgen` son externos; el target es
`wasm32-unknown-unknown`.

### 68.9 Macros

```pengu
incantation square
    ($x:expr) => {
        $x * $x
    }

grimoire
    print(square!(5))
```

```rust
macro_rules! square {
    ($x:expr) => {
        $x * $x
    };
}

fn main() {
    println!("{}", square!(5));
}
```

### 68.10 Checklist de una receta

1. El `pengu` debe ser válido según §60.
2. El `rust` debe compilar con `rustc --edition 2024`.
3. Si hay `unsafe`, debe llevar `-- SAFETY:` en el Pengu y un comentario
   `// SAFETY:` en el Rust.
4. Si hay async, el executor se declara en `Tome.toml`.
5. Si hay FFI, el ABI y el linker se declaran.
6. Si es `no_std`, no se importa `std`.
7. Si es WASM, el target y el glue se documentan.

### 68.11 Criterios de aceptación

- [x] Cada receta es completa y su Rust compila.
- [x] Se cubren CLI, librería, errores, async, FFI, `no_std`, WASM y macros.
- [x] Cada receta indica sus requisitos de manifiesto y seguridad.

[↑ Volver al índice](#indice)

<a id="sec-69-adr"></a>
## 69. Decisiones de diseño (ADR)

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 10 |
| Rust | Rust 2024 |
| Palabras mágicas | todas |
| Depende de | §1–§68 |
| Ejemplos ejecutables | `no` |

Cada decisión se registra una vez. “Alternativas” no es una lista de ideas
descartadas sin motivo: incluye por qué se rechazaron. Un cambio posterior
añade una ADR nueva; no reescribe la historia.

### 69.1 Formato

| Campo | Contenido |
|---|---|
| ID | `D0`–`D24` |
| Contexto | Fuerza o restricción que obliga a decidir. |
| Decisión | Regla normativa adoptada. |
| Alternativas | Opciones consideradas y razón de descarte. |
| Consecuencias | Efectos positivos, costes y deuda aceptada. |
| Estado | `cerrada`; un cambio crea `D25+`. |

### 69.2 Decisiones

| ID | Contexto | Decisión | Alternativas | Consecuencias |
|---|---|---|---|---|
| D0 | El usuario diseña y revisa en español; el código se lee como Rust. | Prosa en español; keywords, código y términos técnicos en inglés. | Todo en inglés. | Documento legible para el autor; mezcla deliberada de idiomas. |
| D1 | Rust 2024 es la edición estable objetivo y el codegen debe ser reproducible. | Rust 2024 estable; MSRV 1.85.0; probado con rustc 1.99.1. | Rust 2021; nightly por defecto. | Se pueden usar `let-else`, `async fn` en traits y `gen` no estable; sin nightly. |
| D2 | Un backend propio multiplica el trabajo y no garantiza la semántica de borrow. | Transpilador a Rust + Cargo; front-end propio; rustc es la autoridad final. | Backend propio; intérprete. | Reutiliza rustc; los errores de tipos/borrow se remapean; depende de Rust. |
| D3 | MoonScript/CoffeeScript usan indentación; los tabs son ambiguos. | 4 espacios; tabs prohibidos; `{}` solo para mapas/token trees. | Tabs; llaves obligatorias. | Parser determinista; editores deben configurar 4 espacios. |
| D4 | Se quiere una identidad mágica sin curvas innecesarias. | Sustantivos mágicos para ítems; verbos familiares para control. | Renombrar todos los keywords. | `rune`/`enchanting`/`pact`; `if`/`for`/`match` siguen siendo familiares. |
| D5 | La mutabilidad implícita es peligrosa con ownership. | `bind` inmutable; `morph` mutable; `=` reasigna; prohibidos en módulo. | `let`/`var`; mutable por defecto; `bind mut` (retirado). | No se olvida `mut`; no hay globales; más palabras que MoonScript. |
| D6 | `static mut` es una fuente de UB y el lenguaje no permite globales mutables. | `sigil` = `const`; `relic` = `static` inmutable; `static mut` no existe. | `const`/`static`; `static mut`. | Estado global solo con `@@shared` + sincronización. |
| D7 | Los defaults deben ser predecibles y alineados con Rust. | `Int` = `i32`; `UInt` = `u32`; `Float` = `f64`; `Str` = `str`; `String` = `String`. | `Int` = `isize`; `Str` = `String`. | Tipos explícitos; `Usize`/`Isize` para tamaños. |
| D8 | `Option`/`Result` son verbosos y el lenguaje quiere azúcar legible. | `?T` = `Option<T>`; `!T` = `Result<T, Error>`; `none`/`some`/`ok`/`err`; `?` postfijo. | Solo `Option`/`Result`; `T?`/`T!E`. | Azúcar sin ocultar el tipo; `!T` fija `Error`. |
| D9 | MoonScript presume “todo es expresión”; Rust tiene sentencias. | Bloques, `if`, `match`, `loop` y funciones son expresiones; `bind`/asignación son sentencias; `return`/`break`/`continue` son `Never`. | Asignación como expresión. | Se conserva la ventaja sin romper move semantics. |
| D10 | `spell` era verboso y `fn` es de Rust; `->` es característico. | `name = (params) -> Tipo`; retorno obligatorio; cuerpo indentado; `(params) => expr` para lambdas. | `spell` (retirado)/`fn`; retorno inferido en funciones. | `->` identifica funciones; lambdas capturan; parser sin ambigüedad. |
| D11 | La herencia de clases complica la composición y el layout. | `rune` = struct; `enchanting` = enum; sin herencia. | `class`/`extends`. | Composición + traits; no hay diamonds. |
| D12 | Se necesita dispatch estático y dinámico sin `self`. | `pact` = trait; `ritual` = impl; receptores `@`, `@mut`, `@own`. | `trait`/`impl`; `self`. | `@` es familiar para MoonScript; métodos explícitos. |
| D13 | `<>` choca visualmente con comparaciones y con la indentación. | `[T]` para genéricos; `[const N: Usize]`; lifetimes `'a`; turbofish `foo[Int](x)`; HRTB `for<'a>`. | `<>` para genéricos. | `[]` se comparte con indexación; el parser distingue por tipo. |
| D14 | Se quiere un manifiesto propio sin perder Cargo. | `Tome.toml` con `[cargo]` passthrough; archivo = `scroll`; `summon`/`unveil`. | Solo `Cargo.toml`; `mod`/`use`/`pub`. | Ecosistema Cargo accesible; una capa de validación propia. |
| D15 | `@` ya es el receptor; `#[...]` es de Rust. | `@@attr(...)`; inner `@@!attr(...)`; `@@derive`, `@@cfg`, `@@test`. | `#[...]`. | `@@` no se confunde con `@`; los atributos son explícitos. |
| D16 | Se necesita metaprogramación sin proc macros en PenguScript. | `incantation` = `macro_rules!`; invocación `name!(...)`; token trees `{}`/`()`/`[]`. | Macros solo desde Rust. | Macros declarativas; sin expansión AST tipada. |
| D17 | UTF-8 y ownership de strings deben ser explícitos. | `Str` no sizeado; `String` owned; interpolación `#{expr}`; raw/byte/C; sin indexación por bytes. | `Str` owned; single quotes para strings. | Sin corrupción UTF-8; `String` se construye explícitamente. |
| D18 | Los nombres de Rust para async/unsafe/FFI rompen la estética. | `dream`/`awaken`/`curse`/`foreign`/`chimera`; `rust` block auditado. | `async`/`await`/`unsafe`/`extern`. | Nombres mágicos consistentes; el escape hatch es visible. |
| D19 | Reimplementar la std es inviable y fragmenta el ecosistema. | `std`/`core`/`alloc` vía `summon`; sin runtime propio; crates vía `tome`; `print`/`format` en preludio. | Biblioteca propia. | Interop directa; el runtime es el de Rust. |
| D20 | El usuario exige un solo archivo con índice clickeable. | Un `docs/LANGUAGE.md`; anclas ASCII; plantilla; ejemplos compilables. | Varios archivos por tema. | Documento grande; navegación por índice y anclas. |
| D21 | Testing, docs y tooling deben ser parte del lenguaje, no un afterthought. | `@@test`; doc comments `---`; CLI `pengu`; rustfmt/clippy/rustdoc; source maps. | Herramientas externas sin integración. | Un solo toolchain; se apoya en herramientas Rust. |
| D22 | La spec y el compilador evolucionan por fases. | Semver para la spec; versión de compilador; edición Rust; MSRV; changelog. | Sin versionado. | Releases reproducibles; deprecaciones con ventana. |
| D23 | Rust no permite definir proc macros en otro lenguaje de forma estable. | Proc macros en crates Rust consumidas vía `tome`; `build.pengu` -> `build.rs`; `rust` block para casos extremos. | Proc macros en PenguScript desde el día 1. | Se acepta una dependencia de Rust para metaprogramación avanzada. |
| D24 | Las features inestables rompen la promesa de estabilidad. | Fuera del núcleo; opt-in con `@@feature` + nightly. | Incluirlas en el núcleo. | Núcleo estable; el usuario asume el riesgo del nightly. |
| D25 | El azúcar de colecciones indentadas necesitaba delimitadores y era ruidosa. | Las colecciones indentadas no llevan `[]`/`{}`; `Vec`/`Set` son marcadores; el cuerpo se clasifica por `clave: valor`. | Mantener delimitadores obligatorios. | Sintaxis MoonScript; requiere regla de clasificación y `do` para bloques. |

### 69.3 Consecuencias globales

1. El lenguaje no tiene runtime propio: hereda el de Rust y su modelo de
   memoria.
2. El compilador es un transpilador: la mayor parte de la semántica fina la
   decide rustc.
3. La sintaxis es más verbosa que MoonScript en bindings (`bind`/`morph`) y
   más estricta en tipos (retorno obligatorio, `Bool` estricto).
4. La magia está en los nombres y en la forma de declarar, no en efectos
   ocultos.
5. La compatibilidad con Rust es una prioridad: `rust` block y `foreign`
   existen para no bloquear casos límite.
6. La deuda principal es el parser de indentación y el sourcemap; se prueban
   con los ejemplos y validadores del repo.

### 69.4 Cómo cambiar una decisión

1. Abrir una ADR nueva (`D26+`) con contexto y alternativa.
2. Actualizar la sección afectada y §64/§65 si cambia el desugaring/código.
3. Actualizar §70 (changelog) y la matriz §63 si cambia la paridad.
4. Añadir/actualizar un ejemplo compilable.
5. No se reescribe una ADR cerrada; se marca como superada.

### 69.5 Criterios de aceptación

- [x] D0–D25 tienen contexto, decisión, alternativas y consecuencias.
- [x] Las decisiones cerradas no se reescriben; los cambios crean una ADR nueva.
- [x] Las consecuencias globales y el procedimiento de cambio son explícitos.

[↑ Volver al índice](#indice)

<a id="sec-70-changelog"></a>
## 70. Changelog y versionado

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 10 |
| Rust | Rust 2024, MSRV 1.85.0 |
| Palabras mágicas | — |
| Depende de | §69 |
| Ejemplos ejecutables | `no` |

### 70.1 Versiones

| Artefacto | Versión actual | Regla |
|---|---|---|
| Especificación | `1.0.0-rc.1` | SemVer; `1.0.0` final tras la aprobación de Fase 11. |
| Compilador `pengu` | `1.0.0-rc.1` | Sigue a la spec; el patch no cambia la gramática. |
| Edición Rust emitida | `2024` | Fijada por D1. |
| MSRV | `1.85.0` | Subirla requiere minor de la spec. |
| Referencia probada | `rustc 1.99.1` | No es un mínimo; es la versión de CI. |
| Formato de `Tome.toml` | `1` | Cambios incompatibles suben `pengu` minor. |
| Sourcemap | `1` | Cambios de esquema suben `sourcemap` major. |

### 70.2 Changelog de la especificación

| Revisión | Fecha | Cambio |
|---|---|---|
| `r0` | 2026-11-12 | Esqueleto, índice, 71 secciones, glosario y §5 piloto. |
| `r1` | 2026-11-12 | §§1–§8: introducción, léxico, programa, tipos, variables, constantes, scope, expresiones. |
| `r2` | 2026-11-12 | §§9–§15: primitivos, strings, operadores, booleanos, condicionales, bucles, funciones. |
| `r3` | 2026-11-12 | §§16–§21: ownership, borrowing, lifetimes, punteros, smart pointers, memoria. |
| `r4` | 2026-11-12 | §§22–§27: arrays, vectores, tuplas, mapas/sets, estructuras, rangos. |
| `r4.1` | 2026-11-12 | Colecciones indentadas sin `[]`/`{}`; `Vec`/`Set` como marcadores; `PGS-E1011`/`E1012`. |
| `r5` | 2026-11-12 | §§28–§32: structs, enums, pattern matching, impls, aliases/casts. |
| `r6` | 2026-11-12 | §§33–§40: genéricos, bounds, traits, associated items, HRTB, closures, HOF, operadores. |
| `r7` | 2026-11-12 | §§41–§47: módulos, visibilidad, tomes, atributos, macros, derives, build/features/cfg. |
| `r8` | 2026-11-12 | §§48–§51: errores, iteradores, async, concurrencia. |
| `r9` | 2026-11-12 | §§52–§55: unsafe, FFI, const eval, `no_std`/embebido/wasm. |
| `r10` | 2026-11-12 | §§56–§59: testing, documentación, herramientas, estilo. |
| `r11` | 2026-11-12 | §§60–§71: gramática, léxico, precedencia, paridad, desugaring, diagnósticos, no soportado, glosario, cookbook, ADR, changelog, referencias. |
| `r12` | 2026-11-12 | QA de Fase 11: renumeración de diagnósticos, catálogo de 486 códigos, aclaración de fragmentos, criterios de aceptación y release candidate. |
| `r13` | 2026-11-12 | QA final: gramática R1–R11, `byte_char`/`byte_escape`, alineación de `dream move`; re-auditorías de legibilidad y Rust aprobadas. |

### 70.3 Cambios de sintaxis relevantes

| Versión | Cambio | Compatibilidad |
|---|---|---|
| `v0.2` | Se retira `spell`; funciones `name = (…) -> Tipo`; lambdas `(…) => expr`. | Ruptura interna; no había usuarios externos. |
| `v0.2` | `bind` inmutable / `morph` mutable; se retira `bind mut`. | Ruptura interna. |
| `v0.2` | `spirit` (retirado) -> `@`; atributos `@attr` -> `@@attr`. | Ruptura interna. |
| `v0.4` | Colecciones indentadas sin delimitadores; `Vec`/`Set` marcadores. | Aditiva; las formas inline siguen válidas. |
| `v0.6` | GAT/RPITIT documentados; sin cambio de sintaxis. | Compatible. |
| `1.0.0-rc.1` | Release candidate de la spec; congela la gramática para `1.0.0`. | Compatible con la sintaxis v0.4+. |

### 70.4 Política de deprecación

1. Una feature se marca `deprecated` en la sección y en §66.
2. Se mantiene al menos un minor completo antes de retirarla.
3. El compilador emite `PGS-W7001` con el reemplazo.
4. Una retirada requiere ADR nueva y entrada en este changelog.
5. Las palabras retiradas (`spell`, `spirit`, `bind mut`) se rechazan con
   `PGS-E1010` y un mensaje de migración; no se aceptan silenciosamente.
6. Los cambios de gramática que rompen código suben `MAJOR` de la spec.
7. Los cambios aditivos suben `MINOR`; las correcciones de redacción, `PATCH`.

### 70.5 Versionado del compilador

| Cambio | Versión |
|---|---|
| Nueva sintaxis/azúcar | minor |
| Nuevo diagnóstico que rechaza código válido | major |
| Nuevo warning | minor |
| Corrección de codegen sin cambio de semántica | patch |
| Cambio de MSRV/edición | minor (y aviso) |
| Cambio de esquema de `Tome.toml`/sourcemap | major del artefacto |

El compilador declara `pengu --version` con su versión, la edición Rust y la
MSRV. Un `Tome.toml` puede fijar `pengu = "1.0"`; el compilador rechaza un
`pengu` incompatible con `PGS-E7002`.

### 70.6 Proceso de release

1. Pasar todos los validadores (`check_sections`, `check_anchors`,
   `check_terms`, `check_rust_snippets`).
2. Verificar que todos los ejemplos compilan.
3. Actualizar este changelog y la versión de la spec.
4. Generar `sourcemap.json` y `Tome.lock` reproducibles.
5. Etiquetar `vX.Y.Z`; no se publica un RC sin dos revisores (§Phase 11).

### 70.7 Criterios de aceptación

- [x] Hay versión de spec, compilador, edición y MSRV.
- [x] El changelog cubre todas las fases.
- [x] Hay política de deprecación.
- [x] Hay reglas de SemVer para spec y compilador.
- [x] El release candidate queda para Phase 11.

[↑ Volver al índice](#indice)

<a id="sec-71-referencias"></a>
## 71. Referencias

| Campo | Valor |
|---|---|
| Estado | `completo` |
| Fase | 10 |
| Rust | Rust 2024 |
| Palabras mágicas | — |
| Depende de | §1–§70 |
| Ejemplos ejecutables | `no` |

### 71.1 Documentación oficial de Rust

| Recurso | Uso en esta spec |
|---|---|
| [The Rust Reference](https://doc.rust-lang.org/reference/) | Gramática, semántica de items, patrones, atributos y edición 2024. |
| [The Rust Programming Language](https://doc.rust-lang.org/book/) | Ownership, borrowing, lifetimes, traits, closures, async. |
| [Rustonomicon](https://doc.rust-lang.org/nomicon/) | Unsafe, aliasing, `transmute`, `MaybeUninit`, FFI. |
| [The Cargo Book](https://doc.rust-lang.org/cargo/) | Manifiesto, features, targets, workspaces, publicación. |
| [The rustc Book](https://doc.rust-lang.org/rustc/) | Ediciones, targets, codegen, diagnósticos. |
| [Rust Standard Library](https://doc.rust-lang.org/std/) | Tipos, traits, colecciones, sincronización, `std::error`. |
| [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/) | Nombres, documentación, interoperabilidad. |
| [The Rust Style Guide](https://doc.rust-lang.org/style-guide/) | Formato de Rust generado. |
| [Rust RFCs](https://github.com/rust-lang/rfcs) | Origen de features estables/inestables. |
| [Rust Edition Guide](https://doc.rust-lang.org/edition-guide/) | Cambios de edición 2024. |
| [Rust Release Notes](https://doc.rust-lang.org/releases.html) | MSRV y estabilidad. |
| [Rust Security](https://www.rust-lang.org/security) | Divulgación y políticas. |

### 71.2 Herramientas del ecosistema

| Recurso | Uso |
|---|---|
| [rustfmt](https://rust-lang.github.io/rustfmt/) | Formato del Rust emitido. |
| [Clippy](https://doc.rust-lang.org/clippy/) | Lints sobre el Rust emitido. |
| [rustdoc](https://doc.rust-lang.org/rustdoc/) | Documentación y doc tests. |
| [Miri](https://github.com/rust-lang/miri) | Detección de UB en tests unsafe. |
| [cargo-fuzz](https://github.com/rust-fuzz/cargo-fuzz) | Fuzzing. |
| [proptest](https://proptest-rs.github.io/proptest/) | Property testing. |
| [criterion](https://bheisler.github.io/criterion.rs/book/) | Benchmarks. |
| [wasm-bindgen](https://rustwasm.github.io/wasm-bindgen/) | Interop WASM/JS. |
| [embassy](https://embassy.dev/) | Async embebido. |
| [cortex-m](https://github.com/rust-embedded/cortex-m) | Targets ARM Cortex-M. |

### 71.3 Lenguajes que inspiran la sintaxis

| Recurso | Uso |
|---|---|
| [MoonScript](https://moonscript.org/) | Indentación, `->`, `=>`, expresiones, estilo conciso. |
| [MoonScript Reference](https://moonscript.org/reference/) | Semántica de funciones, clases (no adoptadas) y comprensiones. |
| [CoffeeScript](https://coffeescript.org/) | `->`/`=>`, indentación, expresiones. |
| [V language](https://vlang.io/) | Variables inmutables por defecto, no globales, simplicidad. |
| [Kotlin](https://kotlinlang.org/docs/home.html) | Inferencia local, `val`/`var`, tipos estáticos. |
| [Rust](https://www.rust-lang.org/) | Ownership, traits, pattern matching, zero-cost. |

### 71.4 Estándares y especificaciones

| Recurso | Uso |
|---|---|
| [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) | “DEBE”, “DEBERÍA”, “PUEDE” en esta spec. |
| [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174) | Ambigüedad de mayúsculas en RFC 2119. |
| [Unicode UAX #31](https://www.unicode.org/reports/tr31/) | Identificadores XID. |
| [Unicode 15.0](https://www.unicode.org/versions/Unicode15.0.0/) | Tablas de `XID_Start`/`XID_Continue`. |
| [SemVer 2.0.0](https://semver.org/) | Versionado de spec/compilador. |
| [TOML 1.0.0](https://toml.io/en/v1.0.0) | `Tome.toml`. |
| [UTF-8 RFC 3629](https://www.rfc-editor.org/rfc/rfc3629) | Codificación de fuente y strings. |
| [IEEE 754](https://ieeexplore.ieee.org/document/8766229) | `F32`/`F64`. |
| [Itanium C++ ABI](https://itanium-cxx-abi.github.io/cxx-abi/) | Referencia para ABI `extern "C"`/FFI (solo como contexto). |

### 71.5 Lecturas por tema

| Tema | Secciones | Referencia principal |
|---|---|---|
| Léxico/indentación | §2, §60, §61 | Rust Reference: tokens; MoonScript. |
| Tipos/ownership | §4, §16–§21 | Rust Book: ownership; Nomicon. |
| Genéricos/traits | §33–§36 | Rust Book: generics/traits; Reference. |
| Patrones | §30 | Rust Book: patterns; Reference. |
| Async/concurrencia | §50–§51 | Rust Book: async; `std::thread`. |
| Unsafe/FFI | §52–§53 | Nomicon; Rust Reference: FFI. |
| `no_std`/embebido | §55 | Embedded Rust Book; cortex-m. |
| Testing/docs | §56–§57 | Cargo Book; rustdoc Book. |
| Tooling | §58 | rustc/Cargo/rustfmt/Clippy. |
| Diagnósticos | §65 | rustc diagnostics; esta spec. |

### 71.6 Cómo citar esta especificación

```text
PenguScript Language Specification, versión 1.0.0-rc.1, revisión r13.
Documento único: docs/LANGUAGE.md.
Rust 2024, MSRV 1.85.0.
```

### 71.7 Criterios de aceptación

- [x] Hay referencias para Rust, MoonScript, V, Kotlin y estándares.
- [x] Cada área técnica importante tiene una fuente.
- [x] Las URLs son oficiales o primarias.
- [x] Se distingue inspiración de semántica adoptada.
- [x] La spec se puede citar con versión y revisión.

[↑ Volver al índice](#indice)
