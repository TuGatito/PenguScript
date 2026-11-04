# psc.source

> Source: `src/psc/source.pengu`

psc/psource.pengu — `SourceFile`: bytes inmutables, índice de líneas y hash.

`SourceFile` es la única copia del texto de un archivo dentro de PSC. Guarda
los bytes **sin BOM** (CRLF preservado), un índice de inicios de línea y el
SHA-256 de los bytes **originales** (BOM/CRLF incluidos).

## Convenciones
- `line` y `col` son 1-indexed.
- `col` es una columna de **byte**, no de codepoint. Coincide con
  `std.sourcemap` y con el lexer; el LSP convierte a UTF-16 en el borde.
- `\n` empieza una línea nueva. En un par `\r\n`, el `\r` sigue contando para
  los offsets, pero `line_text` lo excluye.
- Los offsets son relativos a `text` (después de quitar el BOM). Para obtener
  el offset en el archivo original: `offset + bom_len`.

## Ejemplo
```pengu
import psc.source

var f as SourceFile is calling SourceFile.from_text with "a.pengu", "hola\nmundo\n"
defer banish f
var p as sourcemap.Position is calling f.position_at with 6
# p.line == 2, p.col == 1
```

## Memoria
`banish f` libera `path`, `text`, `line_starts` y `sha256`.

---

### `SOURCE_BOM_0`

> **SOURCE_BOM_0** : int

 Primer byte de un BOM UTF-8.

### `SOURCE_BOM_1`

> **SOURCE_BOM_1** : int

 Segundo byte de un BOM UTF-8.

### `SOURCE_BOM_2`

> **SOURCE_BOM_2** : int

 Tercer byte de un BOM UTF-8.

### `SOURCE_LF`

> **SOURCE_LF** : int

 Byte de line feed.

### `SOURCE_CR`

> **SOURCE_CR** : int

 Byte de carriage return.

### `SourceErrorKind`

> omen SourceErrorKind

```pengu
    SrcRead
    SrcInvalidPath
```

 Por qué falló una lectura de archivo.

### `SourceError`

> rune SourceError

```pengu
    kind as SourceErrorKind
    path as string
    message as string
```

 Error de carga de un archivo. No es un diagnóstico léxico: no hay pspan.

 ## Memoria
 `banish error` libera `path` y `message`.

### `source_error`

> **source_error**(kind: SourceErrorKind, path: string, message: string) -> SourceError

 Construye un `SourceError` con copias propias de `path` y `message`.

 ## Memoria
 Devuelve un valor owned; liberar con `banish`.

### `sha256_hex_of`

> **sha256_hex_of**(raw_hash: string) -> string

 Convierte los 32 bytes de un SHA-256 a hex minúsculas.

 `std.digest.sha256_hex` usa `ord (raw at i)`, que en 3.0.3 asigna un string
 por byte y filtra. Este helper usa `bytes of` y un builder, sin temporales.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `nibble_char`

> **nibble_char**(n: int) -> char

 Carácter hex de un nibble (0-15).

 ## Memoria
 O(1), no asigna.

### `SourceFile`

> rune SourceFile

```pengu
    path as string
    text as string
    line_starts as list of int
    sha256 as string
    bom_len as int
    raw_len as int
```

 Un archivo fuente inmutable.

 ## Memoria
 `banish file` libera `path`, `text`, `line_starts` y `sha256`.

### `from_bytes`

> **from_bytes**(path: string, raw: string) -> SourceFile

 Construye un `SourceFile` desde bytes crudos.

 Quita todos los BOM iniciales, conserva CRLF y calcula el SHA-256 de
 `raw` (antes de quitar el BOM).

 ## Parámetros
 - `path`: ruta lógica; se copia.
 - `raw`: contenido binario; se copia.

 ## Memoria
 Asigna `text`, `line_starts`, `sha256` y `path`. Liberar con `banish`.

### `from_text`

> **from_text**(path: string, text: string) -> SourceFile

 Alias de `from_bytes` para texto ya en memoria (LSP, tests).

 ## Memoria
 Igual que `from_bytes`.

### `get_path`

> **get_path**() -> string

 Ruta lógica del archivo (prestada).

### `get_text`

> **get_text**() -> string

 Texto sin BOM (prestado).

### `byte_len`

> **byte_len**() -> int

 Longitud del texto en bytes.

### `line_count`

> **line_count**() -> int

 Número de líneas. Un archivo vacío tiene una línea vacía.

### `get_sha256`

> **get_sha256**() -> string

 SHA-256 hex de los bytes originales (prestado).

### `get_bom_len`

> **get_bom_len**() -> int

 Bytes de BOM eliminados.

### `get_raw_len`

> **get_raw_len**() -> int

 Longitud original del archivo.

### `file_offset`

> **file_offset**(offset: int) -> int

 Convierte un offset del texto sin BOM al offset del archivo original.

### `is_valid_offset`

> **is_valid_offset**(offset: int) -> bool

 `true` cuando `offset` está en `[0, byte_len]`.

### `position_at`

> **position_at**(offset: int) -> Position

 Convierte un offset de byte a `(line, col)` 1-indexed.

 Los offsets fuera de rango se clampan. `position_at(byte_len)` es la
 posición justo después del último byte.

 ## Memoria
 O(log líneas), no asigna.

### `offset_of`

> **offset_of**(line: int, col: int) -> int

 Convierte `(line, col)` 1-indexed a un offset de byte.

 Panica si la posición no existe. Los usos internos de PSC prefieren
 `span_at`, que clampa.

 ## Memoria
 O(1), no asigna.

### `line_text`

> **line_text**(line: int) -> string

 Texto de una línea (1-indexed), sin `\n` ni `\r\n`.

 ## Retorno
 Un `string` owned; liberar con `banish`.

 ## Memoria
 Asigna la longitud de la línea.

### `line_span`

> **line_span**(line: int) -> ByteSpan

 Rango que cubre una línea sin su terminador.

 ## Memoria
 Asigna un temporal para medir la línea; devuelve un valor.

### `eof_position`

> **eof_position**() -> Position

 Posición del final del archivo.

 ## Memoria
 O(log líneas), no asigna.

### `span_at`

> **span_at**(start: int, end: int) -> ByteSpan

 Convierte un `ByteSpan` en el `ByteSpan` normalizado del archivo.

 ## Memoria
 O(1), no asigna.

### `slice`

> **slice**(s: ByteSpan) -> string

 Copia el texto del pspan.

 ## Retorno
 Un `string` owned; liberar con `banish`.

 ## Memoria
 Asigna la longitud del pspan.

### `byte_at`

> **byte_at**(offset: int) -> int

 Byte en `offset` como entero, o `-1` fuera de rango.

 ## Memoria
 O(1), no asigna.

### `_line_end_offset`

> **_line_end_offset**(line: int) -> int

 Offset del final del texto de una línea, sin `\n` ni `\r`.

