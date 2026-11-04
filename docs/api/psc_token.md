# psc.token

> Source: `src/psc/token.pengu`

psc/token.pengu — modelo de tokens y tabla de palabras reservadas.

`Token` es POD: no guarda strings. El lexema se obtiene del `SourceFile` con
`token_span`; los literales usan tablas laterales indexadas por `aux`.

## Convenciones
- `start` es inclusivo y `end` exclusivo, en bytes de `SourceFile.text`.
- `line`/`col` son 1-indexed; `col` es columna de byte.
- `kw` solo tiene sentido cuando `kind == TokKeyword`; en el resto vale
  `KwNotKeyword`.

## Por qué los prefijos `Tok`/`Kw`
Los nombres de variantes de un `omen` son globales en todo el programa. Un
`omen` con variantes `Error`, `None` o `Read` colisiona con la stdlib. Los
prefijos `Tok*`, `Kw*`, `Lex*`, `Com*`, `Seg*` y `Src*` evitan esas
colisiones sin perder legibilidad.

## Memoria
`Token`, `KeywordEntry` y `ByteSpan` son valores puros. `KeywordTable` es
dueña de su lista; las palabras son literales estáticos.

---

### `TokenKind`

> omen TokenKind

```pengu
    TokEof
    TokNewline
    TokIndent
    TokDedent
    TokIdentifier
    TokKeyword
    TokIntLit
    TokFloatLit
    TokStringLit
    TokCharLit
    TokAntiquusBody
    TokError
    TokLeftParen
    TokRightParen
    TokLeftBracket
    TokRightBracket
    TokLeftBrace
    TokRightBrace
    TokComma
    TokColon
    TokSemicolon
    TokDot
    TokDotDot
    TokEllipsis
    TokArrow
    TokAt
    TokPlus
    TokMinus
    TokStar
    TokSlash
    TokPercent
    TokAmpersand
    TokVerticalBar
    TokCaret
    TokTilde
    TokBang
    TokAssign
    TokEqual
    TokNotEqual
    TokLess
    TokLessOrEqual
    TokGreater
    TokGreaterOrEqual
    TokShiftLeft
    TokShiftRight
    TokPlusAssign
    TokMinusAssign
    TokStarAssign
    TokSlashAssign
    TokPercentAssign
    TokAmpersandAssign
    TokVerticalBarAssign
    TokCaretAssign
    TokShiftLeftAssign
    TokShiftRightAssign
```

 Categoría léxica de un token.

 Los keywords no tienen una variante por palabra: usan `TokKeyword` y
 `Token.kw`. Así este enum queda pequeño y el parser compara `tok.kw`.

### `KeywordKind`

> omen KeywordKind

```pengu
    KwNotKeyword
    KwAlias
    KwAnd
    KwAntiquus
    KwAs
    KwBanish
    KwBind
    KwBreak
    KwBytes
    KwCalling
    KwChr
    KwConcept
    KwConst
    KwContinue
    KwCyclus
    KwDeclare
    KwDefer
    KwDefined
    KwDerive
    KwDonum
    KwEcho
    KwElse
    KwEnchanting
    KwErrdefer
    KwError
    KwEssence
    KwFalse
    KwFor
    KwFrom
    KwIf
    KwImport
    KwIn
    KwInclude
    KwInsignia
    KwInto
    KwIs
    KwJudge
    KwLambda
    KwLdflag
    KwLet
    KwLink
    KwMany
    KwMaybe
    KwNone
    KwNot
    KwNull
    KwOf
    KwOmen
    KwOr
    KwOrd
    KwReturn
    KwRune
    KwSeal
    KwSet
    KwShard
    KwSigil
    KwSome
    KwStatic
    KwStep
    KwTest
    KwTo
    KwTransmute
    KwTrue
    KwTry
    KwUnless
    KwVar
    KwWeave
    KwWhen
    KwWhere
    KwWhile
    KwWith
    KwTypeOf
    KwSizeOf
    KwAlignOf
```

 Palabra reservada. `KwNotKeyword` es el valor por defecto.

 Las palabras *soft* (`self`, `unsafe`, `over`, `frozen`, `inline`, `ritual`,
 `do`, `type`, `size`, `main`, `ok`, `err`) no están aquí: el lexer las emite
 como `TokIdentifier` y el parser las interpreta por contexto.

### `Token`

> rune Token

```pengu
    kind as TokenKind
    kw as KeywordKind
    start as int
    end as int
    line as int
    col as int
    aux as int
```

 Un token léxico.

 ## Memoria
 Valor puro: no tiene heap.

### `KeywordEntry`

> rune KeywordEntry

```pengu
    word as string
    kind as KeywordKind
    first as int
    len as int
```

 Una entrada de la tabla de keywords.

### `KeywordTable`

> rune KeywordTable

```pengu
    entries as list of KeywordEntry
```

 Tabla de palabras reservadas.

 La búsqueda es lineal: 70 comparaciones de igualdad por identificador es
 barato en C y evita depender del orden lexicográfico de `string` (que el
 lenguaje no ofrece). Si el benchmark lo justifica, se añade un índice.

 ## Memoria
 `banish table` libera `entries`; los `word` son literales estáticos.

### `add_keyword`

> **add_keyword**(t: ref to KeywordTable, word: string, k: KeywordKind) -> void

 Añade una entrada a la tabla calculando `first` y `len`.

 ## Memoria
 Hace `push`; la palabra es un literal estático.

### `keyword_table_new`

> **keyword_table_new**() -> KeywordTable

 Construye la tabla de keywords completa.

 ## Memoria
 Asigna una lista; liberar con `banish`.

### `keyword_lookup`

> **keyword_lookup**(t: ref to KeywordTable, word: string) -> KeywordKind

 Busca un keyword con búsqueda binaria.

 ## Retorno
 `KwNotKeyword` si `word` no es una palabra reservada dura.

 ## Memoria
 O(log n), no asigna.

### `keyword_name`

> **keyword_name**(t: ref to KeywordTable, k: KeywordKind) -> string

 Devuelve el lexema de un keyword, o `""` si no está en la tabla.

 ## Memoria
 Devuelve un literal estático; no liberar.

### `token_kind_name`

> **token_kind_name**(k: TokenKind) -> string

 Nombre estable de una categoría de token.

 ## Memoria
 Devuelve un literal estático; no liberar.

### `token_span`

> **token_span**(t: Token) -> ByteSpan

 Rango de bytes de un token.

 ## Memoria
 O(1), no asigna.

### `is_kw`

> **is_kw**(t: Token, k: KeywordKind) -> bool

 `true` cuando el token es un keyword concreto.

 ## Memoria
 O(1), no asigna.

