<a id="sec-10-strings"></a>
## 10. Strings y chars

| Campo | Valor |
|---|---|
| Estado | `revisión` |
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
| Byte | `b"abc"` | `&[U8]` |
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
6. Un string sin cerrar es error léxico (`PGS-E1009`).

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

