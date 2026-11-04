# psc.codegen.emit

> Source: `src/psc/codegen/emit.pengu`

psc/codegen/emit.pengu — escritor C de bajo nivel.

Centraliza indentación, temporales, literales C y el `StringBuilder` de
salida. Ningún otro módulo concatena C a mano en bucles grandes.

---

### `CgEmitter`

> rune CgEmitter

```pengu
    sb as StringBuilder
    indent as int
    temps as int
```

 Emisor de C.

 ## Memoria
 Dueño del `StringBuilder`; `finish` transfiere el string.

### `new_emitter`

> **new_emitter**() -> CgEmitter

 Crea un emisor.

 ## Memoria
 Asigna el builder; liberar con `free` o transferir con `finish`.

### `emit_free`

> **emit_free**(e: ref to CgEmitter) -> void

 Libera un emisor no finalizado.

 ## Memoria
 Libera el builder.

### `line`

> **line**(e: ref to CgEmitter, text: string) -> void

 Escribe una línea con la indentación actual.

 ## Memoria
 No asigna salvo el builder.

### `blank`

> **blank**(e: ref to CgEmitter) -> void

 Escribe una línea vacía.

 ## Memoria
 O(1).

### `raw`

> **raw**(e: ref to CgEmitter, text: string) -> void

 Escribe texto crudo.

 ## Memoria
 O(n).

### `indent_more`

> **indent_more**(e: ref to CgEmitter) -> void

 Aumenta la indentación.

 ## Memoria
 O(1).

### `indent_less`

> **indent_less**(e: ref to CgEmitter) -> void

 Reduce la indentación.

 ## Memoria
 O(1).

### `temp`

> **temp**(e: ref to CgEmitter, prefix: string) -> string

 Genera un nombre temporal único.

 ## Memoria
 Devuelve un string owned.

### `finish`

> **finish**(e: ref to CgEmitter) -> string

 Finaliza y transfiere el bundle.

 ## Memoria
 El emisor queda vacío; el llamador libera el string.

### `escape_c`

> **escape_c**(s: string) -> string

 Escapa un string de PenguScript como literal C.

 Devuelve el contenido **sin** comillas; el llamador añade `"..."`.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `append_hex_digit`

> **append_hex_digit**(sb: ref to StringBuilder, d: int) -> void

 Añade un dígito hexadecimal minúscula al builder.

 ## Memoria
 Presta el builder; no asigna.

### `wrapped_parens`

> **wrapped_parens**(s: string) -> bool

 `true` si `s` está envuelto por un único par de paréntesis que abarca todo.

 ## Memoria
 O(n); no asigna.

