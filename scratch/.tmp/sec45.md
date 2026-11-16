<a id="sec-45-macros"></a>
## 45. Macros (incantation)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
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
