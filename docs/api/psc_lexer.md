# psc.lexer

> Source: `src/psc/lexer.pengu`

psc/lexer.pengu — lexer principal de PSC.

Una pasada iterativa sobre `SourceFile.text` produce tokens significativos,
comentarios (trivia) y tablas laterales de literales. La indentación se
aplica después con `lexer_indent`.

## Orden de decisión en el bucle
1. espacio/tab; 2. newline; 3. comentario; 4. string/raw; 5. char;
6. palabra; 7. número; 8. operador; 9. desconocido.

## Memoria
`lex` devuelve un `LexResult` owned. El estado interno no sobrevive a la
llamada.

---

### `lex`

> **lex**(src: ref to SourceFile, bag: ref to DiagnosticBag, keywords: ref to KeywordTable, opts: LexOptions) -> LexResult

 Lexa un archivo completo.

 ## Memoria
 Devuelve un `LexResult` owned; liberar con `banish`.

### `chain_pipe_at`

> **chain_pipe_at**(lx: ref to LexerState, at: int) -> bool

 `true` si el `\n` actual va seguido inmediatamente de una línea `.`/`->`.

 Comprueba si en `at` empieza la palabra contextual `pipe` seguida de
 espacio. No consume nada.

 ## Memoria
 O(1), no asigna.

### `chain_continuation_ahead`

> **chain_continuation_ahead**(lx: ref to LexerState) -> bool

 Replica `_merge_chain_continuations` de stage0: solo pliega si la línea
 siguiente empieza por `.`, `->` o `pipe ` sin líneas en blanco ni
 comentarios de por medio. La comprobación se hace después del `\n` y de los
 espacios/tabs.

 ## Memoria
 Avanza la posición hasta el operador si hay continuación; no asigna.

### `scan_newline`

> **scan_newline**(lx: ref to LexerState) -> void

 Consume un run de `NEWLINE` + indentación + líneas de solo comentario.

 ## Memoria
 Añade un `TokNewline`; los comentarios se añaden como trivia.

### `lex_finish`

> **lex_finish**(lx: ref to LexerState) -> void

 Añade el NEWLINE sintético de EOF si hace falta.

 ## Memoria
 Puede añadir un token POD.

### `scan_word`

> **scan_word**(lx: ref to LexerState) -> void

 Escanea una palabra: keyword, identificador o compuesto `type of`/`size of`.

 No asigna un string por palabra: compara rangos de bytes contra la tabla.

 ## Memoria
 No asigna.

### `range_equals`

> **range_equals**(lx: ref to LexerState, start: int, end: int, word: string) -> bool

 Compara `[start, end)` con un literal ASCII.

 ## Memoria
 O(len), no asigna.

### `keyword_range`

> **keyword_range**(lx: ref to LexerState, start: int, end: int) -> KeywordKind

 Busca un keyword comparando el rango de bytes, sin materializar el lexema.

 ## Memoria
 O(entradas), no asigna.

### `try_compound_of`

> **try_compound_of**(lx: ref to LexerState, word_start: int, start_line: int, start_col: int) -> bool

 Intenta reconocer `type of` o `size of` y emitir el token compuesto.

 El llamador ya consumió la primera palabra. Solo avanza si la secuencia
 coincide; si no, deja la posición intacta.

 ## Retorno
 `true` si emitió un token compuesto.

 ## Memoria
 No asigna.

### `scan_number`

> **scan_number**(lx: ref to LexerState) -> void

 Escanea un número según la gramática de stage0.

 ## Memoria
 No asigna.

### `consume_prefixed`

> **consume_prefixed**(lx: ref to LexerState, base: int) -> bool

 Consume `0x`/`0o`/`0b` y los dígitos del prefijo.

 ## Retorno
 `false` si no hay ningún dígito/underscore tras el prefijo (el llamador debe
 tratar el `0` como decimal y dejar el prefijo para el siguiente token).

 ## Memoria
 No asigna.

### `digit_for_base`

> **digit_for_base**(b: int, base: int) -> bool

 `true` si `b` es un dígito válido en `base`.

 ## Memoria
 O(1), no asigna.

### `scan_operator`

> **scan_operator**(lx: ref to LexerState) -> bool

 Intenta escanear un operador o delimitador.

 ## Retorno
 `true` si emitió un pstoken.

 ## Memoria
 No asigna.

### `emit_op`

> **emit_op**(lx: ref to LexerState, kind: TokenKind, start: int, len: int, line: int, col: int) -> bool

 Emite un operador de `len` bytes.

 ## Memoria
 No asigna (salvo el token POD).

### `emit_colon`

> **emit_colon**(lx: ref to LexerState, start: int, line: int, col: int) -> bool

 Emite un `:` y marca la cabecera `antiquus` si corresponde.

 ## Memoria
 No asigna.

### `lex_match_at`

> **lex_match_at**(lx: ref to LexerState, needle: string) -> bool

 `true` si `needle` coincide en la posición actual.

 ## Memoria
 O(len), no asigna.

### `byte_of`

> **byte_of**(s: string, i: int) -> int

 Byte de un string en `i`.

 ## Memoria
 O(1), no asigna.

### `scan_unknown`

> **scan_unknown**(lx: ref to LexerState) -> void

 Recupera de un byte/codepoint desconocido.

 ## Memoria
 Añade un `TokError` y un diagnóstico; no deja heap.

