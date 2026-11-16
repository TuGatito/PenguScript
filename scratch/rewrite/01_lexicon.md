---

<a id="sec-02"></a>
## 2. Léxico

### 2.1 Archivo y codificación

- Fuente UTF-8 sin BOM. Un BOM es `PGS-E1001`.
- Se aceptan LF y CRLF; CRLF se normaliza a LF.
- La indentación significativa usa **cuatro espacios** por nivel.
- Un tabulador fuera de un string o comentario es `PGS-E1002`.
- Un aumento de indentación que no sea múltiplo de cuatro es `PGS-E1003`.
- Un `DEDENT` que no coincide con ningún nivel abierto es `PGS-E1004`.

### 2.2 Comentarios

```pengu
-- comentario de línea
--[[ comentario
     de bloque ]]
--- documentación del siguiente item
--! documentación interna del módulo
```

`---` y `--!` son documentación, no comentarios libres. Se procesan en §17.

### 2.3 Identificadores

Un identificador empieza con `XID_Start` o `_` y continúa con `XID_Continue`.
Se permiten letras Unicode, pero no emojis ni marcas de control. Los
identificadores distinguen mayúsculas y minúsculas.

Convenciones:

- `snake_case` para funciones, bindings y campos.
- `PascalCase` para tipos, records, sums, pacts y variantes.
- `SCREAMING_SNAKE_CASE` para `sigil`.

### 2.4 Keywords

La lista completa es corta y cerrada:

| Familia | Keywords |
|---|---|
| Declaraciones | `rune`, `enchanting`, `pact`, `ritual`, `essence`, `scroll`, `summon`, `unveil`, `grimoire`, `foreign`, `curse` |
| Bindings | `bind`, `morph`, `sigil`, `relic` |
| Control | `if`, `elseif`, `else`, `unless`, `match`, `when`, `then`, `for`, `while`, `loop`, `break`, `continue`, `return`, `do` |
| Operadores | `and`, `or`, `not`, `is`, `isnt`, `in`, `as` |
| Literales | `true`, `false`, `none`, `some`, `ok`, `err` |
| Contextuales | `@`, `@mut`, `@own`, `Self`, `Vec`, `Map`, `Set` |

`Vec`, `Map`, `Set`, `Option`, `Result` y `String` son tipos de la prelude, no
keywords. `Self` solo se usa dentro de `pact` y `ritual`.

Las palabras `spell`, `spirit`, `class`, `null`, `async`, `await`, `macro`,
`trait`, `impl`, `dyn`, `move` y `ref` no son keywords y no se aceptan como
identificadores: el compilador las trata como término retirado (`PGS-E1010`).

### 2.5 Literales

#### Booleanos y ausencia

```pengu
true
false
none
```

`none` es el único literal de ausencia. No hay `null` ni `nil`.

#### Enteros

```pengu
42
0xFF
0o755
0b1010
1_000_000
42_i64
42_usize
```

Los sufijos son `I8`, `I16`, `I32`, `I64`, `Isize`, `U8`, `U16`, `U32`, `U64`
y `Usize`. Sin sufijo, el contexto decide; si no hay contexto, `Int`.

No hay `I128` ni `U128` en el núcleo. Se importan de `std.int` si hacen falta.

#### Flotantes

```pengu
1.5
1.0e10
2.5_f32
```

Sin sufijo, el contexto decide; si no hay contexto, `Float`. No hay `NaN`
literal; se usa `Float.nan()` de la prelude.

#### Char y strings

```pengu
'a'
'\n'
b'P'
"hola"
"hola, #{name}"
"""texto
con varias líneas"""
r"sin \escapes"
b"bytes"
c"cadena C"
```

Un `Char` es un escalar Unicode. Un `byte char` es `U8`; el carácter directo
debe ser ASCII y `\xNN` admite `0x00`–`0xFF`.

`String` es owned; `&Str` es una vista prestada. Un literal de string sin
contexto es `&Str`; para obtener `String` se usa `String.from("texto")`.

La interpolación `#{expr}` solo existe en strings normales y triples. Para
escribir `#{` literal se usa `\#{`.

#### Colecciones

```pengu
[1, 2, 3]
[0; 4]
Vec[1, 2, 3]
Map["a": 1, "b": 2]
Set["a", "b"]
(1, "uno")
()
```

Los arrays son de tamaño fijo; `Vec`, `Map` y `Set` son colecciones owned.
La forma indentada con `[]`/`{}` no forma parte del núcleo: la indentación se
reserva para bloques.

#### Rangos

```pengu
0..10
0..=10
```

Un rango no es una colección; se usa en `for` y en slices.

### 2.6 Separadores

- `NEWLINE` separa sentencias y elementos de un bloque.
- Dentro de `()`, `[]` y `{}` se permiten saltos de línea; las comas son
  opcionales antes del cierre.
- No se usa `;` como separador.
- La continuación de una expresión después de un operador binario es
  automática si la línea siguiente está más indentada.

### 2.7 Ejemplo

```pengu
grimoire
    bind name = "pengu"
    bind answer = 42
    bind ratio = 1.5
    bind letter = 'P'
    bind bytes = [1, 2, 3]
    bind words = Vec["magic", "static"]
    bind config = Map["name": name, "version": 1]
    print("#{name}: #{answer} / #{ratio} / #{letter}")
```

### 2.8 Diagnósticos del léxico

| Código | Situación |
|---|---|
| `PGS-E1001` | BOM al inicio. |
| `PGS-E1002` | Tabulador en indentación. |
| `PGS-E1003` | Indentación no múltiplo de cuatro. |
| `PGS-E1004` | `DEDENT` sin nivel correspondiente. |
| `PGS-E1005` | String sin cerrar. |
| `PGS-E1006` | Char o byte char sin cerrar. |
| `PGS-E1007` | Escape desconocido. |
| `PGS-E1008` | Byte char no ASCII. |
| `PGS-E1009` | Comentario de bloque sin cerrar. |
| `PGS-E1010` | Término retirado. |
| `PGS-E1011` | Identificador Unicode inválido. |

[↑ Volver al índice](#indice)
