# 🧭 Plan de implementación — F1: Source, diagnósticos y lexer

> **Estado:** documento de planificación. **No se ha implementado nada de F1.**
> **Repositorio:** PenguScript `3.0.3` (commit `3f99038`).
> **Fase anterior:** F0 cerrada (B1–B12 y módulos std P0).
> **Fase que se planifica:** F1 de [`AUDITORIA_AUTO_HOSPEDAJE.md`](AUDITORIA_AUTO_HOSPEDAJE.md) §9.
> **Objetivo del documento:** que puedas revisar y aprobar (o corregir) el diseño
> antes de escribir la primera línea de PSC.

---

## 📑 Índice

0. [Resumen ejecutivo](#-0-resumen-ejecutivo)
1. [Punto de partida verificado](#-1-punto-de-partida-verificado)
2. [Alcance: qué entra y qué no](#-2-alcance-qué-entra-y-qué-no)
3. [Arquitectura y patrón de diseño](#-3-arquitectura-y-patrón-de-diseño)
4. [Diagramas](#-4-diagramas)
5. [Tipos exactos que se van a usar](#-5-tipos-exactos-que-se-van-a-usar)
6. [SourceFile: BOM, CRLF, líneas y hash](#-6-sourcefile-bom-crlf-líneas-y-hash)
7. [Modelo de tokens](#-7-modelo-de-tokens)
8. [Lexer: máquina de estados](#-8-lexer-máquina-de-estados)
9. [Strings, interpolación y escapes](#-9-strings-interpolación-y-escapes)
10. [Post-lexer de indentación](#-10-post-lexer-de-indentación)
11. [Diagnósticos](#-11-diagnósticos)
12. [Session y CLI](#-12-session-y-cli)
13. [Organización de archivos](#-13-organización-de-archivos)
14. [Plan de pruebas](#-14-plan-de-pruebas)
15. [Paridad con stage0](#-15-paridad-con-stage0)
16. [Rendimiento](#-16-rendimiento)
17. [Ownership y fugas](#-17-ownership-y-fugas)
18. [Riesgos y mitigaciones](#-18-riesgos-y-mitigaciones)
19. [Orden de implementación y estimación](#-19-orden-de-implementación-y-estimación)
20. [Criterios de aceptación (DoD)](#-20-criterios-de-aceptación-dod)
21. [Decisiones que necesito de ti](#-21-decisiones-que-necesito-de-ti)
22. [Anexos](#-22-anexos)

---

## 🎯 0. Resumen ejecutivo

F1 convierte bytes en una secuencia de tokens con spans exactos, comentarios
capturados como trivia, literales analizados y diagnósticos útiles. Es la base
sobre la que F2 escribirá el parser recursivo.

**Lo que se entrega:**

1. `psc/` con su `pengu.toml` y un CLI mínimo (`psc lex`).
2. `SourceFile` propio de PSC: BOM, CRLF, índice de líneas, offsets de byte,
   SHA-256 del archivo original y slicing sin copias innecesarias.
3. Modelo de tokens **sin asignaciones por token** (`Token` es POD) y tablas
   laterales para strings, chars y cuerpos `antiquus`.
4. Lexer escrito a mano, iterativo, con estados para strings, raw strings,
   triples, chars, números, comentarios/doc comments, `antiquus` y operadores.
5. Post-lexer de indentación que replica el `Indenter` de Lark (`tab = 2`,
   `INDENT`/`DEDENT`, supresión dentro de paréntesis/corchetes/llaves) y que
   **no aborta** ante un dedent inconsistente: diagnostica y recupera.
6. `DiagnosticBag` sobre `std.diagnostic`, con códigos compatibles (`E0000`,
   `E0059`, `E0057`, `W0005`), render plain/ANSI/JSON.
7. Token dump estable (TSV) y diagnósticos JSON para golden tests y CI.
8. Oracle de paridad *dev-only* que compara PSC contra el lexer contextual de
   stage0 capturando los tokens durante un `parse` real.
9. Fuzz determinista de 1 M de entradas, ASan/UBSan y benchmark de 1 MB.

**Decisiones de diseño principales (recomendadas):**

| # | Decisión | Recomendación |
|---|---|---|
| D1 | ¿Tokens con payload o zero-copy? | **Zero-copy**: `Token` solo tiene offsets y `aux`; los literales viven en tablas laterales. |
| D2 | Keywords contextuales de stage0 | Lexer **context-free** con keywords duras + lista de soft keywords; la permisividad de stage0 se documenta como divergencia. |
| D3 | CRLF | **Preservar** CRLF y quitar solo el BOM; el hash es sobre los bytes originales. |
| D4 | `antiquus` | Escaneo **nativo en el lexer**, sin pre-pasada que reescriba el texto. |
| D5 | Salida del CLI | TSV canónico + diagnósticos JSON; el JSON completo de tokens se difiere a F2/F6. |
| D6 | Oracle | Script Python **dev-only** que captura tokens contextuales durante un parse real de stage0. |
| D7 | Layout | Exactamente `psc/` del §8 de la auditoría, con archivos de ≤ 600–800 líneas. |

**Estimación:** ~25 días efectivos de implementación (4–5 semanas de
calendario con imprevistos), alineado con las 3–4 persona-semanas de la
auditoría. El desglose está en §19.

---

## 🔍 1. Punto de partida verificado

### 1.1 Lo que F0 sí dejó en el árbol

F0 añadió y probó los módulos que F1 necesita:

| Módulo | Uso en F1 | Estado |
|---|---|---|
| `std.digest` | SHA-256 del archivo para `SourceFile.hash` | ✅ presente |
| `std.diagnostic` | `Span`, `Label`, `Diagnostic`, `DiagnosticBag`, render JSON | ✅ presente |
| `std.builder` | acumular mensajes/dumps sin O(n²) | ✅ presente |
| `std.lingua` | validación UTF-8 y `encode_one` para `\u{...}` | ✅ presente |
| `std.archivum` | `read_bytes` (binario, sin decodificar) | ✅ presente |
| `std.io` | `read_stdin_all` para `psc lex --stdin` | ✅ presente |
| `std.sourcemap` | oracle de posiciones en tests; **no** se usa como base de `SourceFile` | ✅ presente |

También están los fixes de B1/B2/B2b y los tests de regresión de la auditoría.

### 1.2 Lo que **no** está en el árbol

- No existe `psc/` (ni `src/`, ni `pengu.toml`, ni esqueleto).
- No existe `tools/parity/` ni un harness de compilación diferencial.
- No existe el oracle de tokens.

> **Consecuencia:** F1 arranca creando el esqueleto mínimo de `psc/` y el oracle
> de tokens. No se reabre F0 ni se toca el compilador Python.

### 1.3 Cómo lexa stage0 hoy (y por qué importa)

El lexer de stage0 **no es un lexer independiente**. Es Lark LALR(1) con lexer
contextual + `PenguIndenter`, precedido por cuatro pasadas textuales:

1. `_extract_antiquus_bodies`: sustituye el cuerpo C por un placeholder.
2. `_strip_comments`: borra `#` y `##` conservando líneas y columnas.
3. `_merge_chain_continuations`: pega líneas que empiezan por `.` o `->`.
4. `_expand_short_struct_inits`: reescribe `with a, b` como
   `with a is a, b is b`.

Consecuencias directas para F1:

- **Los keywords son contextuales.** Stage0 acepta `var if as int is 5`,
  `var weave as int is 5`, etc., porque en esa posición el lexer contextual
  elige `NAME`. Un lexer independiente no puede replicarlo sin realimentación
  del parser. Es una rareza de Lark, no una feature del lenguaje.
- **`PenguParser.get_tokens` no sirve como oracle**: no quita comentarios y su
  chequeo de “múltiples statements en una línea” da falsos positivos
  (`std/bitset.pengu`, tres casos de `bitset_*`). Hay que capturar los tokens
  **durante un `parse` real**.
- **Las pasadas textuales cambian posiciones**: `_merge_chain_continuations`
  reasigna líneas a los tokens de la cadena y
  `_expand_short_struct_inits` inserta caracteres en la línea (desplaza
  columnas). El oracle debe tener niveles de comparación.
- **Los comentarios no llegan al parser.** F1 los captura como trivia, algo que
  stage0 no hace y que F7/LSP agradecerán.

### 1.4 Números reales del corpus (medidos hoy)

| Métrica | Valor |
|---|---:|
| Archivos `.pengu` en `tests/` + `std/` | **175** |
| Tokens contextuales de stage0 capturados en esos 175 | **321 313** |
| Archivos de `tests/conformance` | 66 |
| Archivos `.pengu` en todo `tests/` (incluye negativos) | 126 |
| Archivos que mencionan `antiquus` | 33 |
| Declaraciones `antiquus` con cuerpo extraíble | 204 en 28 archivos |
| Apariciones de raw strings (`r"…"` / `r"""…"""`) | 672 |
| Archivos con bloque doc `##` aislado | 54 |
| Archivos que stage0 reescribe con `_expand_short_struct_inits` | **1** (`std/compressus.pengu`) |
| Archivos con `_merge_chain_continuations` | **0** |
| Archivos sin ninguna reescritura textual | **146** |
| Fallos de parse de stage0 sobre los 175 | **0** |

Esto hace que la paridad de F1 sea realista: 146 archivos se pueden comparar
token a token con línea/columna exactas; 28 con la salvedad del cuerpo
`antiquus`; 1 con línea exacta y columna relajada.

### 1.5 APIs verificadas con un spike (en `/tmp`, sin tocar la repo)

Se comprobó que funcionan y que se pueden usar tal cual:

- `digest.sha256_hex("abc")` → `ba7816bf…`.
- `DiagnosticBag` + `diagnostic(...)` con `code`, `help`, `note`, labels.
- `bag.render_plain` y `bag.render_json` (JSON LSP válido).
- `lingua.from_u32` + `lingua.encode_one` con `StringBuilder`.
- `judge` sobre `omen` con `when Variant ->`.
- `rune` con campos `omen`, listas de structs, `derive Par`/`Nexus`.
- Cast de `omen` a `int` (`tok.kind to int`) para tablas de nombres.

> Nota práctica: para llamar a módulos del proyecto se usa el **nombre hoja**
> del módulo importado (`lexer.lex`, `util.double`) o un alias
> (`import psc.lexer as lexer`). La forma `demo.util.double` sigue fallando en
> 3.0.3; F1 no depende de ella ni de B2b.

---

## 📦 2. Alcance: qué entra y qué no

### 2.1 Entra en F1

| Área | Entregable |
|---|---|
| Source | `SourceFile`, `LineIndex`, `ByteSpan`, BOM, CRLF, hash, slicing, posiciones |
| Tokens | `TokenKind`, `KeywordKind`, `Token`, tablas de keywords/operadores |
| Lexer | palabras, keywords, números, strings, raw, triples, chars, comentarios, doc blocks, `antiquus`, operadores,unknown chars |
| Indentación | `NEWLINE`, `INDENT`, `DEDENT`, pila, paréntesis, recuperación, `W0005` |
| Diagnósticos | `LexIssue`, códigos, severidades, help/note, render plain/ANSI/JSON |
| Sesión | `Session` (source + bag + opciones + tabla), `open`, `lex` |
| CLI | `psc lex`, `--stdin`, `--comments`, `--check`, `--diagnostics=json`, exit codes |
| Pruebas | unitarias `.pengu`, golden de tokens/diagnósticos, corpus, oracle, fuzz, ASan, benchmark |
| Docs | `psc/README.md`, `psc/docs/PARITY.md`, `psc/docs/OWNERSHIP.md` |

### 2.2 No entra en F1 (explícito)

- Parser, AST y recuperación sintáctica (**F2**).
- Resolución de imports, símbolos, tipos, checker e inferencia (**F3**).
- Validación semántica de `char` > 0x7F (`E0057`): el lexer guarda el
  codepoint; la emisión del código semántico es F3. (Si el usuario prefiere,
  F1 puede emitirlo ya; ver D2 en §21.)
- Extracción de documentación a símbolos y hover (**F7/F8**); F1 solo captura
  la trivia y sus spans.
- Parseo de las expresiones de interpolación: F1 registra sus rangos; F2 las
  parsea.
- Formatter, LSP, JSON completo de tokens, cache incremental, compilación de
  PSC por PSC (**F5**).
- Cualquier cambio al compilador Python o a `std/`.

---

## 🏗️ 3. Arquitectura y patrón de diseño

### 3.1 Patrón: pipeline por etapas + máquina de estados + artefactos como datos

No es un “lexer monolítico”. Es una secuencia de transformaciones con
contratos claros:

```text
bytes
  → SourceFile (normaliza BOM, indexa líneas, hashea)
  → Lexer (escaneo iterativo, sin recursión)
  → IndentPass (post-lexer sobre la lista de tokens)
  → LexResult (tokens + trivia + tablas laterales)
  → F2 Parser
```

Principios, heredados del §7 de la auditoría:

1. **Pipeline explícito.** Cada archivo tiene una responsabilidad.
2. **Sesión explícita.** `Session` es dueña de `SourceFile`, `DiagnosticBag`,
   `KeywordTable` y opciones. No hay estado global mutable.
3. **Diagnósticos como datos.** El lexer nunca lanza excepciones por entrada de
   usuario; emite diagnósticos y sigue. Solo `spark.panic` para invariantes
   internas (bug del compilador).
4. **Zero-copy en tokens.** `Token` es POD; nada de un `string` por token.
   Los literales se guardan como spans en tablas laterales.
5. **Sin recursión en F1.** El escaneo, el split de strings y la indentación son
   iterativos. Así una entrada con 10 000 paréntesis no desborda la pila en el
   lexer (el límite de profundidad es F2).
6. **Determinismo.** Orden de fuente, sin mapas para emitir, sin timestamps.
7. **Ownership explícito.** Cada función documenta qué presta, qué toma y qué
   libera. `defer banish` en cada recurso.
8. **El core es una librería.** `main.pengu` es un frontend fino; `lex()` es
   reutilizable por el LSP y los tests.

### 3.2 Patrones concretos

| Patrón | Dónde | Por qué |
|---|---|---|
| **State machine** | `Lexer` | Strings, raw, triples, chars, comentarios y `antiquus` tienen estados distintos. |
| **Table-driven dispatch** | keywords y operadores | Evita cadenas gigantes de `if`; la tabla es auditable y se puede testear sola. |
| **Post-lexer / visitor** | `lexer_indent.pengu` | La indentación necesita ver la secuencia completa y la profundidad de paréntesis. |
| **Result object** | `LexResult` | Tokens, trivia y side tables viajan juntos; sin singletons. |
| **Facade** | `psc/diagnostics.pengu` | `std.diagnostic` tiene una API extensa; PSC expone solo lo que necesita y fija códigos. |
| **Null object** | `KeywordKind.None` | `Token.kw` siempre tiene un valor válido, aunque el token no sea keyword. |
| **Recovery token** | `TokenKind.Error` | El parser de F2 puede sincronizar sin abortar. |

### 3.3 Flujo de propiedad (resumen)

```text
Session
 ├── SourceFile      (dueña de text, line_starts, hash)
 ├── DiagnosticBag   (dueña de diagnósticos y copias de fuentes)
 ├── KeywordTable    (dueña de la lista de entradas; strings estáticos)
 └── LexOptions      (valor)

lex(src: ref to SourceFile, bag: ref to DiagnosticBag, ...)
 └── LexResult       (dueño de tokens/comments/strings/parts/chars/antiquus)
       └── banish result libera las seis listas (todas POD)
```

---

## 📐 4. Diagramas

### 4.1 Pipeline de F1

```text
                    ┌─────────────────────────────────────────────┐
 bytes del archivo  │ SourceFile.from_path / from_text / stdin    │
 ──────────────────▶│  · quita BOM (guarda bom_len)               │
                    │  · conserva CRLF                            │
                    │  · line_starts (índice de líneas)           │
                    │  · sha256(bytes originales)                 │
                    └──────────────────┬──────────────────────────┘
                                       │ ref to SourceFile
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │ Lexer (una pasada, iterativa)               │
                    │  keyword table · operator table             │
                    │  estados: normal/string/raw/triple/char/    │
                    │           comment/docblock/antiquus         │
                    └───────┬──────────────────────────┬──────────┘
                            │ tokens crudos            │ comments (trivia)
                            ▼                          ▼
                    ┌───────────────────────┐   ┌───────────────────────┐
                    │ IndentPass            │   │ CommentTable          │
                    │ pila de niveles       │   │ Line / Doc / DocBlock │
                    │ pila de brackets      │   └───────────────────────┘
                    │ NEWLINE/INDENT/DEDENT │
                    └──────────┬────────────┘
                               ▼
                    ┌─────────────────────────────────────────────┐
                    │ LexResult                                   │
                    │  tokens · comments · strings · parts ·      │
                    │  chars · antiquus                           │
                    └──────────┬──────────────────────────────────┘
                               ▼
                        F2: Parser
```

### 4.2 Máquina de estados del lexer

```text
                         ┌──────────────────────────────┐
                         │            NORMAL            │
                         └──┬───┬───┬───┬───┬───┬───┬───┘
                            │   │   │   │   │   │   │
             espacio/tab ───┘   │   │   │   │   │   └── desconocido → Error + diagnóstico
             letra/_ ──────────▶│   │   │   │   │
             dígito ────────────┘   │   │   │   │
             '"' ──────────────────▶│   │   │   │
             'r"' ──────────────────┘   │   │   │
             '"""' / 'r"""' ────────────┘   │   │
             "'" ───────────────────────────┘   │
             '#' ───────────────────────────────┘
             'antiquus' + header ':' + NL + '"""' ───────────────▶ ANTIQUUS

  STRING  ── '"' ──▶ NORMAL          (interpolación: grupo '{...}' equilibrado)
  RAW     ── '"' ──▶ NORMAL
  TRIPLE  ── '"""' ─▶ NORMAL
  RAWTRIPLE ─ '"""' ▶ NORMAL
  CHAR    ── "'" ──▶ NORMAL
  COMMENT ── fin de línea ──▶ NORMAL
  DOCBLOCK ── '##' de cierre / EOF ──▶ NORMAL
  ANTIQUUS ── '"""' de cierre ──▶ NORMAL
```

### 4.3 IndentPass

```text
tokens crudos
     │
     ▼
  ¿NEWLINE?
     │
     ├── paren_depth > 0 ──▶ se descarta (no hay INDENT/DEDENT dentro de ()[]{})
     │
     └── paren_depth == 0
            │
            ├── emit NEWLINE
            ├── indent > top  ──▶ push(indent); emit INDENT
            ├── indent == top ──▶ nada
            └── indent < top  ──▶ pop + DEDENT por cada nivel
                                   │
                                   └── si no coincide exactamente:
                                       E0000 + recuperación (push del nivel)
```

### 4.4 Ciclo de vida de un diagnóstico

```text
Lexer detecta un problema
   │
   ▼
LexIssue (enum)
   │
   ▼
emit_issue(bag, src, issue, span, detail)
   │  · elige code/severity/message/help/note
   │  · construye Span con posiciones 1-indexed
   ▼
DiagnosticBag.add(Diagnostic)
   │
   ├── render_plain / render_colored ──▶ stderr
   └── render_json ───────────────────▶ --diagnostics=json
```

---

## 🧱 5. Tipos exactos que se van a usar

> Todos los tipos viven en `psc/src/psc/*.pengu`. Los que tienen `Nexus` se
> liberan con `banish`; los que son `Par` son valores sin heap. Los nombres son
> los definitivos salvo que la revisión de F2 pida un cambio (checkpoint en §19).
>
> **Nota de implementación:** las variantes de `omen` son globales en todo el
> programa. Para no colisionar con la stdlib se prefijan: `Tok*` (TokenKind),
> `Kw*` (KeywordKind), `Lex*` (LexIssue), `Com*` (CommentKind), `Seg*`
> (StringPartKind), `Src*` (SourceErrorKind). Los nombres de §5.2 se leen con
> ese prefijo en el código real.

### 5.1 `span.pengu`

```pengu
## Un rango de bytes half-open [start, end).
##
## ## Memoria
## Valor puro: no tiene heap.
rune ByteSpan derive Par:
    start as int
    end as int
```

Helpers:

```pengu
weave span_len with s as ByteSpan into int
weave span_is_empty with s as ByteSpan into bool
weave span_contains with s as ByteSpan, offset as int into bool
weave span_merge with a as ByteSpan, b as ByteSpan into ByteSpan
weave span_clamp with s as ByteSpan, limit as int into ByteSpan
```

### 5.2 `token.pengu`

```pengu
## Categoría léxica de un token.
##
## Los keywords NO son variantes de TokenKind: viven en `Token.kw`, para que
## `TokenKind` sea pequeño y el dump pueda imprimir `Keyword(Weave)`.
omen TokenKind:
    ## Fin de archivo.
    Eof
    ## Salto de línea significativo (puede cubrir varias líneas en blanco).
    Newline
    ## Apertura de bloque.
    Indent
    ## Cierre de bloque.
    Dedent

    ## Identificador ASCII.
    Identifier
    ## Palabra reservada; el valor exacto está en `Token.kw`.
    Keyword
    ## Entero decimal/hex/bin/oct.
    IntLit
    ## Flotante.
    FloatLit
    ## String normal, raw o triple.
    StringLit
    ## Char literal.
    CharLit
    ## Cuerpo C de un `antiquus`.
    AntiquusBody
    ## Token de recuperación; el parser puede saltarlo.
    Error

    LeftParen
    RightParen
    LeftBracket
    RightBracket
    LeftBrace
    RightBrace
    Comma
    Colon
    Semicolon
    Dot
    DotDot
    Ellipsis
    Arrow
    At
    Plus
    Minus
    Star
    Slash
    Percent
    Ampersand
    VerticalBar
    Caret
    Tilde
    Bang
    Assign
    Equal
    NotEqual
    Less
    LessOrEqual
    Greater
    GreaterOrEqual
    ShiftLeft
    ShiftRight
    PlusAssign
    MinusAssign
    StarAssign
    SlashAssign
    PercentAssign
    AmpersandAssign
    VerticalBarAssign
    CaretAssign
    ShiftLeftAssign
    ShiftRightAssign
```

```pengu
## Palabra reservada. `None` es el valor por defecto de `Token.kw`.
##
## La lista completa está en el Anexo A. Las palabras *soft* (`self`, `unsafe`,
## `over`, `frozen`, `inline`, `ritual`, `do`, `type`, `size`) NO están aquí:
## el lexer las emite como Identifier y el parser las interpreta por contexto.
omen KeywordKind:
    None
    Import
    Include
    ...
```

```pengu
## Un token léxico.
##
## `start`/`end` son offsets de byte en `SourceFile.text` (después de quitar el
## BOM). `line`/`col` son 1-indexed y `col` es columna de byte, igual que
## `std.sourcemap`.
##
## ## Memoria
## Valor puro: no tiene heap.
rune Token derive Par:
    kind as TokenKind
    kw as KeywordKind
    start as int
    end as int
    line as int
    col as int
    aux as int
```

**Significado de `aux` (contrato cerrado):**

| `kind` | `aux` |
|---|---|
| `Newline` | ancho de indentación de la última línea del run (`espacios + tabs*2`) |
| `Keyword` | `0` (el keyword está en `kw`) |
| `IntLit` / `FloatLit` | base: `2`, `8`, `10`, `16`; `0` = float |
| `StringLit` | índice en `LexResult.strings` |
| `CharLit` | índice en `LexResult.chars` |
| `AntiquusBody` | índice en `LexResult.antiquus` |
| `Error` | índice en `LexResult.issues` (opcional, ver §11.4) |
| resto | `0` |

### 5.3 Comentarios/trivia

```pengu
omen CommentKind:
    ## Comentario de una línea con un solo '#'.
    Line
    ## Comentario de documentación de una línea ('## ...').
    Doc
    ## Bloque documental abierto con '##' aislado y cerrado con '##'.
    DocBlock

## Un comentario capturado. No entra en la lista de tokens.
##
## ## Memoria
## Valor puro: solo offsets y flags.
rune Comment derive Par:
    kind as CommentKind
    start as int
    end as int
    line as int
    col as int
    closed as bool
```

### 5.4 Literales: tablas laterales POD

```pengu
omen StringPartKind:
    ## Texto literal (puede contener escapes sin decodificar).
    Text
    ## Expresión de interpolación: el rango apunta al texto entre llaves.
    Interp

## Un segmento de un string. Los offsets son absolutos en el fuente.
rune StringPart derive Par:
    kind as StringPartKind
    start as int
    end as int

## Metadatos de un string literal.
##
## `content_start`/`content_end` excluyen las comillas. `dedent` es la
## indentación común que hay que quitar al decodificar un triple (0 si no es
## triple). `part_start`/`part_count` indexan `LexResult.parts`.
rune StringInfo derive Par:
    is_raw as bool
    is_triple as bool
    has_interp as bool
    content_start as int
    content_end as int
    part_start as int
    part_count as int
    dedent as int

## Metadatos de un char literal.
rune CharInfo derive Par:
    content_start as int
    content_end as int
    codepoint as int
    width as int

## Metadatos de un cuerpo `antiquus`.
rune AntiquusInfo derive Par:
    body_start as int
    body_end as int
    indent as int
    is_raw as bool
    empty as bool
```

**¿Por qué no guardar el texto decodificado en F1?**
Porque el parser (F2) y el codegen (F4) son los que necesitan el valor, y
pueden pedirlo con funciones puras:

```pengu
weave decode_string with src as ref to SourceFile, info as StringInfo into string
weave decode_string_part with src as ref to SourceFile, part as StringPart,
                               is_raw as bool, dedent as int into string
weave decode_char with src as ref to SourceFile, info as CharInfo into string
weave decode_antiquus with src as ref to SourceFile, info as AntiquusInfo into string
```

Así el lexer no asigna un `string` por literal ni por token; solo cuando F2/F4
lo necesiten. Los tests de F1 sí llaman a estos decodificadores.

### 5.5 Opciones y resultado

```pengu
rune LexOptions derive Par:
    keep_comments as bool           # true
    keep_indent_tokens as bool      # true
    warn_mixed_indentation as bool  # true
    tab_width as int                # 2 (igual que stage0)
    max_interp_depth as int         # 64
```

```pengu
## Resultado completo de una lexación.
##
## ## Memoria
## `banish result` libera las seis listas. Todos los elementos son POD, así que
## no hay que liberar elementos uno a uno.
rune LexResult derive Nexus:
    tokens as list of Token
    comments as list of Comment
    strings as list of StringInfo
    parts as list of StringPart
    chars as list of CharInfo
    antiquus as list of AntiquusInfo
    # issues as list of int          # opcional (D7); ver §11.4
```

### 5.6 Tabla de keywords

```pengu
rune KeywordEntry derive Par:
    word as string
    kind as KeywordKind

## Tabla ordenada por `word` para búsqueda binaria.
##
## ## Memoria
## `banish table` libera la lista. Los `word` son literales estáticos
## (`is_owned = 0`), así que no se liberan (y no deben liberarse).
rune KeywordTable derive Nexus:
    entries as list of KeywordEntry
```

Construcción y búsqueda:

```pengu
weave keyword_table_new into KeywordTable
weave keyword_lookup with t as ref to KeywordTable, word as string into KeywordKind
```

### 5.7 `SourceFile`

```pengu
## Un archivo fuente inmutable.
##
## ## Memoria
## `banish file` libera `text`, `line_starts`, `sha256` y `path`.
rune SourceFile derive Nexus:
    path as string
    text as string          # bytes sin BOM; CRLF preservado
    line_starts as list of int
    sha256 as string        # hex de los bytes ORIGINALES (incluye BOM/CRLF)
    bom_len as int
    raw_len as int
```

### 5.8 `Session`

```pengu
rune Session derive Nexus:
    source as SourceFile
    diagnostics as diag.DiagnosticBag
    keywords as KeywordTable
    options as LexOptions
```

### 5.9 `LexIssue`

```pengu
omen LexIssue:
    UnterminatedString
    UnterminatedTripleString
    UnterminatedRawString
    UnterminatedChar
    InvalidCharLiteral
    InvalidNumber
    UnknownCharacter
    InvalidUtf8
    UnexpectedBom
    IndentMismatch
    MixedIndentation
    UnmatchedCloseBracket
    UnclosedBracket
    AntiquusMissingBody
    AntiquusEmptyBody
    InterpolationTooDeep
```

La tabla `issue -> code/severity/message/help/note/recovery` está en §11.

---

## 📄 6. SourceFile: BOM, CRLF, líneas y hash

### 6.1 Política de normalización

| Elemento | Decisión | Razón |
|---|---|---|
| BOM | **Quitar** todos los BOM iniciales (`EF BB BF`), guardar `bom_len` | Stage0 lo hace; el primer token debe empezar en columna 1 |
| BOM interior | **No** quitar; diagnosticar `UnexpectedBom` | Un BOM a mitad de archivo es basura, no metadata |
| CRLF | **Preservar** `\r\n` | Los offsets de byte coinciden con el archivo real; LSP y `#line` no necesitan remapear |
| `\r` suelto | Diagnóstico `UnknownCharacter` | Stage0 tampoco lo acepta (`WS_INLINE` es solo espacio/tab) |
| UTF-8 inválido | Diagnóstico `InvalidUtf8` en el primer byte inválido; se sigue lexando | El LSP nunca debe morir por un buffer corrupto |
| Hash | SHA-256 de los **bytes originales** (BOM y CRLF incluidos) | Cambiar cualquier byte invalida caché; el hash representa el archivo en disco |

`SourceFile.text` es una copia **sin BOM**, con CRLF. Los offsets de token son
relativos a `text`. Para obtener el offset en el archivo original:
`file_offset = token.start + bom_len`.

### 6.1.1 Error de carga

`SourceFile.from_path` puede fallar antes de tener un fuente. Ese error no es un
diagnóstico léxico (no hay span); es un `result`:

```pengu
omen SourceErrorKind:
    Read
    InvalidPath

## ## Memoria
## `banish error` libera `path` y `message`.
rune SourceError derive Nexus:
    kind as SourceErrorKind
    path as string
    message as string
```

`Session.open` propaga este `SourceError`; el CLI lo imprime y devuelve 2.

### 6.2 Construcción

```pengu
weave from_path with path as string into result of SourceFile to SourceError
weave from_text with path as string, text as string into SourceFile
weave from_bytes with path as string, raw as string into SourceFile
```

- `from_path` usa `archivum.read_bytes` (binario). Si falla, devuelve `err_of`
  un `SourceError` con `kind` y `message`.
- `from_text`/`from_bytes` no tocan disco; los usa el LSP y los tests.
- `from_bytes` calcula SHA-256 **antes** de quitar el BOM.
- Detección de BOM repetido:
  ```text
  while raw[scan] == 0xEF and raw[scan+1] == 0xBB and raw[scan+2] == 0xBF:
      scan += 3
  bom_len = scan
  ```
- `text = raw at bom_len to raw_len` (copia; la cadena original puede liberarse).
- `line_starts = [0]`; por cada `\n` en `text`, añadir `i + 1`.
- `SourceFile` no emite diagnósticos: la validación UTF-8 y los avisos viven en
  `Session`/`Lexer`, que tienen el `DiagnosticBag`.

### 6.3 API de consulta

| Función | Retorno | Coste | Memoria |
|---|---|---:|---|
| `path` | `string` prestado | O(1) | no asigna |
| `text` | `string` prestado | O(1) | no asigna |
| `byte_len` | `int` | O(1) | no asigna |
| `line_count` | `int` | O(1) | no asigna |
| `sha256` | `string` prestado | O(1) | no asigna |
| `bom_len` | `int` | O(1) | no asigna |
| `file_offset(offset)` | `int` | O(1) | no asigna |
| `position_at(offset)` | `Position` | O(log líneas) | no asigna |
| `offset_of(line, col)` | `int` (result/panic) | O(1) | no asigna |
| `line_text(line)` | `string` **owned** | O(len línea) | `banish` |
| `slice(span)` | `string` **owned** | O(len) | `banish` |
| `span_at(start, end)` | `ByteSpan` | O(log líneas) | no asigna |
| `eof_position` | `Position` | O(1) | no asigna |
| `is_valid_offset` | `bool` | O(1) | no asigna |

`Position` se reutiliza de `std.sourcemap` (`line as int`, `col as int`) para no
inventar otro tipo. `SourceFile` **no** envuelve `SourceMap`: implementa su
propio `LineIndex` con una `list of int` y búsqueda binaria, porque necesita
CRLF preservado y no quiere una segunda copia del texto.

### 6.4 LineIndex: algoritmo

```text
position_at(offset):
    off = clamp(offset, 0, byte_len)
    lo = 0; hi = line_starts.len - 1
    while lo < hi:
        mid = (lo + hi + 1) / 2
        if line_starts at mid <= off: lo = mid
        else: hi = mid - 1
    return line = lo + 1, col = off - (line_starts at lo) + 1
```

- `line_text` excluye el `\n` y, si la línea termina en `\r\n`, también el `\r`.
- `offset_of` valida `1 <= line <= line_count`, `col >= 1`, y que el offset no
  pase del final de la línea (misma semántica que `std.sourcemap.offset_of`).
- Para un archivo vacío: `line_count == 1`, `line_starts == [0]`.
- Para un archivo que termina en `\n`: hay una línea final vacía; `eof_position`
  es `(line_count, 1)`.
- `slice(span)` clampa `start`/`end` y devuelve `""` si `start >= end`.

### 6.5 Tests de SourceFile

- `"hola\nmundo\n"`: 3 líneas, `position_at(6) == (2,1)`.
- CRLF: `"a\r\nb"` → 2 líneas, `line_text(1) == "a"`, offset de `b` = 3.
- BOM: `EF BB BF` + `"abc"` → `text == "abc"`, primer token en `(1,1)`,
  `bom_len == 3`, `sha256` cambia respecto a `"abc"`.
- BOM doble y BOM interior.
- Sin newline final: `eof_position` correcto; el lexer añade un `NEWLINE`
  sintético (ver §10.4).
- UTF-8 inválido: diagnóstico en el byte exacto y lexación posterior sin crash.
- `slice` con `start == end`, fuera de rango y backwards.
- Hash conocido: SHA-256 de `""`, `"abc"` y un archivo con BOM.

---

## 🔤 7. Modelo de tokens

### 7.1 Convenciones de posición

- `start` es inclusivo, `end` exclusivo, ambos offsets de byte en
  `SourceFile.text`.
- `line` y `col` son 1-indexed; `col` es columna de **byte**, no de codepoint
  (consistente con `std.sourcemap` y con el LSP, que convierte a UTF-16 en el
  borde).
- `end_line`/`end_col` no se guardan: se derivan con `source.position_at(end)`
  cuando el dump o un diagnóstico los necesitan.
- `NEWLINE` puede cubrir varias líneas en blanco y la indentación de la
  siguiente línea. `line`/`col` apuntan al primer `\n`; `end` apunta al primer
  carácter de código después de la indentación. Esto replica el `_NEWLINE` de
  Lark (`/(\r?\n[\t ]*)+/`).
- `INDENT`/`DEDENT` son tokens de ancho cero (start == end) situados en el
  primer token de la línea indentada / en la posición de dedent. Stage0 les
  presta el span del `NEWLINE`; el oracle normaliza esa diferencia.

### 7.2 Dónde viven los keywords

`TokenKind` tiene una sola variante `Keyword`; el valor exacto está en
`Token.kw` (`KeywordKind`). Ventajas:

- `TokenKind` tiene ~50 variantes, no ~130.
- El parser compara `tok.kw == KeywordKind.Var`, tipado y exhaustivo.
- El dump imprime el nombre del keyword desde la tabla, sin un `judge` de 75
  casos.
- `KeywordKind.None` es el valor por defecto de tokens no-keyword, así que el
  campo siempre es válido.

### 7.3 Keywords duras, soft y rarezas de stage0

**Duras** (el lexer las emite como `Keyword`): la lista completa está en el
Anexo A. Son 70 palabras: las de `LANGUAGE.md` §3.4 menos las soft (`size`),
más `ldflag` (directiva de build).

**Soft** (el lexer las emite como `Identifier`; el parser las interpreta):

| Palabra | Contexto |
|---|---|
| `self` | expresión `self`, `self->field`; stage0 acepta `var self` |
| `unsafe` | statement `unsafe:` |
| `over` | solo en `judge expr over field:` |
| `frozen` | solo en posición de tipo |
| `inline`, `ritual` | solo como modificadores de `weave` |
| `do` | solo en `do:` |
| `type`, `size` | solo en `type of` / `size of` |
| `main`, `ok`, `err` | nombres ordinarios (el compilador los trata en sema) |

`type of` y `size of` son la excepción: el lexer emite un token compuesto
`Keyword` con `kw == TypeOf` / `SizeOf` cuando ve `type`/`size`, espacios o
tabs, y `of` con frontera de palabra. Esto replica el terminal `_TYPE_OF` de
Lark y evita que el parser tenga que mirar dos tokens. En cualquier otro
contexto, `type`/`size` son `Identifier`.

> **Divergencia conocida:** stage0 acepta `var if as int is 5` por su lexer
> contextual. PSC no lo aceptará: `if` es keyword dura y el parser de F2
> rechazará keywords duras en posición de nombre. El corpus no usa esta
> rareza. Se documenta en `PARITY.md` y el oracle la marca como allowed
> difference. Si el usuario prefiere compatibilidad literal, se puede añadir
> un modo `--lenient-keywords` en F3; ver D2 en §21.

### 7.4 Tabla de operadores (longest match)

Orden de comprobación (de más largo a más corto):

```text
<<=  >>=  ...  ->  ..
+=  -=  *=  /=  %=  &=  |=  ^=  <<  >>  <=  >=  ==  !=
@  +  -  *  /  %  &  |  ^  ~  <  >  =  !  .  ,  :  ;  (  )  [  ]  {  }
```

Decisiones:

- `..` se reconoce antes que `.`; `...` antes que `..`.
- `1..2` debe lexar `IntLit("1") DotDot IntLit("2")`, no un float.
- `->` antes que `-`.
- `#` nunca llega a la tabla de operadores: se maneja como comentario.
- `?`, `$`, `\`` y cualquier otro byte desconocido → `Error` + `UnknownCharacter`.
- `=` se lexa como `Eq` aunque el lenguaje use `is`; el parser lo rechazará.
  Así un `=` accidental produce un error sintáctico con span, no un
  “unexpected character” genérico.

### 7.5 Token dump canónico (TSV)

`psc lex FILE` imprime:

```text
# psc-token-dump v1
# file: <path>
# sha256: <hex>
# bytes: <n>
# lines: <n>
# columns: index  kind  lexeme  start  end  line  col  end_line  end_col  aux
0	Keyword(Import)	import	0	6	1	1	1	7	0
1	Identifier	std	7	10	1	8	1	11	0
2	Dot	.	10	11	1	11	1	12	0
...
```

Reglas:

- `kind` es `Keyword(<Name>)` para keywords; para el resto, el nombre de la
  variante (`Identifier`, `IntLit`, `StringLit`, `Newline`, `Indent`, ...).
- `lexeme` se escapa en una línea: `\\`, `\t`, `\n`, `\r`, `\0`, `\xNN` para
  bytes no imprimibles y `\x7F` para DEL. Las comillas no necesitan escape
  porque no delimitan el campo.
- `end_line`/`end_col` se derivan de `source.position_at(end)`.
- `aux` se imprime como entero.
- Con `--comments`, después de los tokens se emite una sección:
  ```text
  # comments
  index	kind	start	end	line	col	closed
  0	Doc	12	25	2	1	false
  ```
- El dump es determinista y no incluye rutas absolutas si se invoca con una ruta
  relativa; los golden normalizan el path a su basename.

---

## ⚙️ 8. Lexer: máquina de estados

### 8.1 Estructura interna

```pengu
## Estado mutable de una lexación. No sale de `lexer.pengu`.
##
## ## Memoria
## No tiene destructor: sus listas se transfieren a `LexResult` al terminar.
## Si se añade un camino de salida anticipada, debe liberar `result`.
rune Lexer:
    src as ref to SourceFile
    bag as ref to DiagnosticBag
    keywords as ref to KeywordTable
    opts as LexOptions
    pos as int
    line as int
    line_start as int
    pending_antiquus as bool
    antiquus_colon as bool
    result as LexResult
```

`lex` es una función, no un método de `Session`:

```pengu
weave lex with src as ref to SourceFile, bag as ref to DiagnosticBag,
              keywords as ref to KeywordTable, opts as LexOptions
         into LexResult
```

### 8.2 Bucle principal (pseudocódigo)

```text
lx = Lexer{...}
while lx.pos < len:
    b = byte_at(lx.pos)
    if b == ' ' or b == '\t': advance; continue
    if b == '\n' or (b == '\r' and next == '\n'): scan_newline(lx); continue
    if b == '#': scan_comment_or_docblock(lx); continue
    if b == '"': scan_string(lx, raw=false, triple=false); continue
    if b == '\'' : scan_char(lx); continue
    if b == 'r' and next == '"': scan_raw_string(lx); continue
    if is_ascii_letter(b) or b == '_': scan_word(lx); continue
    if is_digit(b): scan_number(lx); continue
    if try_scan_operator(lx): continue
    # desconocido
    emit_error_token(lx, b)
    advance_one_codepoint_for_diagnostic(lx)
finish(lx)  # NEWLINE sintético, INDENT/DEDENT finales, EOF
```

`try_scan_operator` es una función table-driven que prueba las cadenas del §7.4
en orden y, si ninguna coincide, devuelve `false`.

### 8.3 Identificadores y keywords

```text
scan_word:
    start = pos
    while is_ascii_alnum(byte_at(pos)) or byte_at(pos) == '_': pos++
    end = pos
    word = src.text at start to end         # owned temporal
    kind = keyword_lookup(keywords, word)
    if kind != None:
        emit Keyword(kind, start, end)
    else:
        emit Identifier(start, end)
    banish word
```

- Solo ASCII: `[A-Za-z_][A-Za-z0-9_]*`. Un byte ≥ 0x80 en posición de nombre es
  `UnknownCharacter`, no un identificador Unicode.
- `_` sola es un identificador válido (discard binding).
- `r"` se comprueba **antes** de `scan_word`; `r` sola es un identificador.
- La tabla está ordenada y se busca con búsqueda binaria. Si en el benchmark
  resulta caro, se añade un índice por primera letra; no se cambia el contrato.

### 8.4 Números

Se replica la gramática de stage0:

```text
INT   := 0[xX][0-9a-fA-F_]+
       | 0[oO][0-7_]+
       | 0[bB][01_]+
       | [0-9][0-9_]*

FLOAT := [0-9][0-9_]*\.[0-9][0-9_]*([eE][-+]?[0-9][0-9_]*)?
       | [0-9][0-9_]*[eE][-+]?[0-9][0-9_]*
```

Algoritmo:

1. Si el primer byte es `0` y el siguiente es `x/X/o/O/b/B`, consumir el
   prefijo y luego uno o más caracteres del alfabeto correspondiente
   (`[0-9a-fA-F_]`, `[0-7_]`, `[01_]`). Emitir `IntLit` con `aux = base`.
   - Si no hay ningún carácter válido tras el prefijo, no consumir el prefijo:
     se lexa `0` como `IntLit` y el prefijo como `Identifier`/`UnknownCharacter`.
     Stage0 hace exactamente esto (`0x` → `INT("0") NAME("x")`).
2. Si no, consumir dígitos y `_`.
3. Si el siguiente es `.` y el byte posterior es dígito, consumir `.` + dígitos
   + `_`, y opcionalmente `e/E[-+]?dígitos` → `FloatLit`, `aux = 0`.
4. Si el siguiente es `.` y el posterior **no** es dígito, no consumir el punto:
   `1..2` → `IntLit(1) DotDot IntLit(2)`; `1.foo` → `IntLit(1) Dot Identifier`.
5. Si el siguiente es `e/E` seguido de dígitos (o signo + dígitos), consumir y
   emitir `FloatLit`.
6. Los `_` se permiten en cualquier posición después del primer dígito,
   incluido el final (`1_`), igual que el regex de stage0. La validación del
   valor (por ejemplo `0x_`) se hace en `parse_int_token` (F2/F3), no en el
   lexer; así el token dump coincide con stage0.
7. `InvalidNumber` se reserva para casos en los que el scanner no puede
   avanzar con seguridad (no para `0x_`, que es un token válido léxicamente).

### 8.5 Comentarios y doc comments

El lexer **no** borra comentarios; los captura en `LexResult.comments` y sigue.
Esto es una mejora sobre stage0 y no afecta al parser (F2 los ignora).

#### Comentario de línea `#`

- Desde `#` hasta el final de la línea (sin incluir `\r`/`\n`).
- `CommentKind.Line`, `closed = true`.
- Si `#` aparece dentro de un string o de una interpolación, no es comentario:
  el scanner de strings ya lo consumió.

#### Doc de una línea `## ...`

- `CommentKind.Doc`, `closed = true` si la línea termina en `##` (por ejemplo
  `## doc ##`), `false` en otro caso.
- `##` sola se trata como doc de una línea **salvo** que cumpla la regla de
  bloque de 8.5.3.

#### Bloque doc `##` aislado

Se replica exactamente `_strip_comments`:

1. La línea, ya sin indentación, es exactamente `##`.
2. La línea anterior **no** empieza por `#`.
3. La línea siguiente **no** empieza por `#`.
4. Entonces se busca la línea de cierre:
   - una línea cuyo contenido recortado sea exactamente `##`, o
   - una línea que empiece por `##`, tenga longitud > 2 y termine en `##`.
5. Se captura **un** `Comment` de tipo `DocBlock` desde la apertura hasta el
   cierre (o hasta EOF si no hay cierre), con `closed` según corresponda.
6. Las líneas intermedias se tratan como trivia, no como código. Si no hay
   cierre, se consume el resto del archivo (igual que stage0).

> Esto es importante: hay 54 archivos en el corpus con bloques `##` aislados.
> Sin esta regla, el texto intermedio se lexaría como código y fallaría.

#### Comentarios dentro de un run de `NEWLINE`

Cuando `scan_newline` consume líneas en blanco, también consume líneas que solo
tienen un comentario (tras la indentación). El comentario se registra como
trivia y el run continúa. La indentación que cuenta es la de la **última** línea
antes del siguiente token de código, igual que el regex `(\r?\n[\t ]*)+`.

### 8.6 Strings: delimitación

La delimitación se separa del análisis de partes (§9). Reglas:

| Forma | Cierre | Escapes | Interpolación |
|---|---|---|---|
| `"..."` | primer `"` no escapado, fuera de un grupo `{...}` equilibrado | sí | sí |
| `"""..."""` | primer `"""` (sin escapes que protejan) | sí | sí |
| `r"..."` | primer `"` | no | no |
| `r"""..."""` | primer `"""` | no | no |
| `'...'` | ver 8.7 | sí | no |

Para `"..."`:

- `\` consume el byte siguiente (y `\u{...}` se salta hasta `}` para no
  confundir un `"` interior).
- `{` intenta escanear un grupo equilibrado:
  - profundidad 1;
  - dentro, se respetan strings `"..."`/`'...'` con sus escapes;
  - `{` suma, `}` resta;
  - si llega a 0, el grupo es una interpolación válida;
  - si llega a EOF o al cierre del literal sin equilibrar, **el `{` es texto
    literal** (stage0 también lo trata así) y se sigue.
- `}` sin abrir es texto literal.
- El literal puede contener `\n` (stage0 lo permite en su regex); el parser de
  F2 decidirá si la expresión interpolada multilínea es válida.
- Si no se encuentra el cierre: `UnterminatedString`, token `StringLit` hasta
  el final de la línea (o EOF), y se continúa desde allí. No se consume el
  archivo entero.

Para triples:

- Se busca el primer `"""` sin interpretar escapes (stage0 usa
  `[\s\S]*?"""`). Un `\"""` **cierra** el literal en stage0; PSC replica eso.
- Si no se encuentra: `UnterminatedTripleString`, token hasta EOF.
- El contenido puede contener `"` y `""`; solo `"""` cierra.

### 8.7 Chars

Réplica del regex de stage0:

```text
' ( [^'\\] | \u{hex+} | \uXXXX | \xNN | \[0-7]{1,3} | \. ) '
```

- Exactamente una unidad entre comillas.
- `''`, `'ab'` y `'a` mal formados → `InvalidCharLiteral` o `UnterminatedChar`;
  se emite `CharLit` con `codepoint = -1` y `Error` para recuperación.
- Se calcula `codepoint`:
  - `\n`, `\t`, `\\`, `\'`, `\"`, `\0`, `\xNN`, octal → valor del byte;
  - `\uXXXX` / `\u{...}` → codepoint Unicode;
  - carácter directo → su codepoint UTF-8 si es multibyte; si es ASCII, el byte.
- `width` es el número de bytes que ocupa el char en el fuente (para spans).
- La validación `codepoint <= 0x7F` es semántica (`E0057`, F3). F1 guarda el
  valor y no emite ese código.

### 8.8 `antiquus`

En vez de una pre-pasada textual, el lexer reconoce el cuerpo nativamente.

#### Detección de cabecera

Un token `Keyword(Antiquus)` es candidato si:

- está a profundidad de paréntesis 0, y
- es el primer token de código de la línea lógica, o los tokens anteriores de
  esa línea son solo atributos (`@name`, `@name(...)`) y espacios.

Al verlo, `pending_antiquus = true`. Se sigue lexando la cabecera normalmente
(`antiquus`, nombre, `shard`, `with`, `into`, `:`).

Al llegar a un `Colon` con `pending_antiquus` y profundidad 0:
`antiquus_colon = true`.

Si llega un `NEWLINE` mientras `pending_antiquus` y no se vio `:`:
se cancela el estado (no era una declaración válida); el parser de F2 dará el
error sintáctico.

#### Cuerpo

Después del `NEWLINE` que sigue al `:`:

1. Saltar líneas en blanco (se conservan como parte del `NEWLINE`).
2. Si el primer contenido es `"""` o `r"""`:
   - `is_raw = true` si es `r"""`;
   - si en la misma línea hay un `"""` de cierre (`"""C"""`), el cuerpo es el
     texto entre ambos;
   - si no, el cuerpo son las líneas hasta la primera línea cuyo `strip()` sea
     exactamente `"""`.
3. Calcular `indent` = mínimo de espacios/tabs iniciales de las líneas no
   vacías del cuerpo (igual que stage0).
4. Quitar líneas en blanco finales.
5. Emitir `AntiquusBody` con `aux` apuntando a `AntiquusInfo`.
6. Si no hay triple quote: `AntiquusMissingBody` (`E0059`); **no** consumir la
   línea; se sigue lexando normalmente para que el parser de F2 recupere.
7. Si el cuerpo queda vacío: `AntiquusEmptyBody` (`E0059`), y se emite igual un
   `AntiquusBody` vacío (para que la declaración conserve su forma).
8. El `NEWLINE` posterior al cierre se lexa normalmente.

> `AntiquusInfo.body_start/body_end` apuntan al contenido crudo (sin comillas).
> `decode_antiquus` aplica `indent` y devuelve el C exacto que espera el codegen.
> `is_raw` se conserva por si el futuro codegen quiere distinguirlo; para el
> cuerpo C no cambia nada (stage0 no decodifica escapes en `antiquus`).

### 8.9 Unknown characters y recuperación

- Byte no reconocido fuera de string/comentario:
  - si es un BOM (`EF BB BF`), `UnexpectedBom`;
  - si es un byte UTF-8 válido pero no ASCII, `UnknownCharacter` con el
    codepoint en el mensaje;
  - si es un byte inválido, `InvalidUtf8`;
  - si es `\r` suelto, `UnknownCharacter`;
  - en todos: emitir `TokenKind.Error` con span del codepoint (1–4 bytes) y
    avanzar ese codepoint.
- `UnmatchedCloseBracket` lo detecta el IndentPass, no el scanner principal
  (necesita la pila).
- `InterpolationTooDeep` se detecta al superar `opts.max_interp_depth`; el
  scanner sigue hasta el cierre para no desincronizar, pero no registra más
  niveles.
- El lexer **nunca** hace `return` temprano por un error. Solo los invariantes
  internos (`pos` fuera de rango, tabla inconsistente) usan `spark.panic`.

---

## 🔡 9. Strings, interpolación y escapes

### 9.1 Separar delimitación, split y decodificación

Tres pasos independientes, cada uno testeable:

1. **Delimitación** (§8.6): encontrar `content_start`/`content_end` y los flags
   `is_raw`/`is_triple`.
2. **Split** (`split_parts`): recorrer el contenido y producir `StringPart`s
   `Text`/`Interp`. Es independiente de los escapes para los límites: un `{`
   escapado (`\{`) no abre interpolación; un `{` dentro de un string anidado
   dentro de la interpolación tampoco.
3. **Decodificación** (`decode_string_part`): aplicar escapes a un `Text` y
   devolver un `string` owned.

### 9.2 Reglas de split

- `\{`, `\}`, `\\`, `\"`, `\u{...}` no abren/cierran interpolación.
- `{` abre un grupo; se cuenta profundidad; se respetan `"..."` y `'...'`
  anidados con sus escapes; `}` cierra.
- Si el grupo no se equilibra, el `{` es texto (stage0).
- `StringInfo.has_interp` es verdadero si hay al menos un `Interp`.
- Un literal sin partes (por ejemplo `""`) tiene `part_count = 0`; `decode`
  devuelve `""`.
- Los segmentos `Text` vacíos entre interpolaciones adyacentes no se emiten.
- Los offsets de `Interp` apuntan **sin** las llaves: `{expr}` → `start` en
  `expr`, `end` en el `}`.
- `StringInfo.dedent` se calcula para triples: mínimo de indentación de las
  líneas no vacías del contenido crudo (incluidas las líneas de expresiones
  interpoladas, igual que stage0 `extract_string_parts`).

### 9.3 Triples: dedent

Réplica de `extract_string_parts`:

1. Si el contenido empieza por `\r\n` o `\n`, quitarlo.
2. Calcular `min_indent` sobre las líneas no vacías.
3. Quitar `min_indent` columnas a cada línea no vacía.
4. Si la última línea queda vacía, eliminarla.
5. Unir con `\n`.
6. Si el contenido original terminaba en línea vacía, preservar un `\n` final.

`StringInfo.dedent` guarda `min_indent` para que `decode_string_part` pueda
aplicar el mismo recorte a cada segmento `Text`. El parser de F2 usará
`decode_string` sobre el literal completo (más simple) y `split_parts` para las
expresiones; el codegen de F4 puede usar los segmentos.

### 9.4 Escapes (réplica exacta de `_decode_literal`)

| Escape | Resultado |
|---|---|
| `\n` | `0x0A` |
| `\r` | `0x0D` |
| `\t` | `0x09` |
| `\b` | `0x08` |
| `\f` | `0x0C` |
| `\v` | `0x0B` |
| `\a` | `0x07` |
| `\\` | `0x5C` |
| `\"` | `0x22` |
| `\'` | `0x27` |
| `\?` | `0x3F` |
| `\u{HEX+}` | codepoint Unicode → UTF-8 |
| `\uXXXX` | exactamente 4 hex → codepoint → UTF-8 |
| `\xNN` | exactamente 1–2 hex → **un byte** (no UTF-8) |
| `\NNN` octal | 1–3 dígitos → un byte |
| desconocido | se conserva `\` + carácter (stage0) |
| `\` al final | se conserva `\` |

Reglas:

- En raw strings no se decodifica nada (ni `\n`, ni `{}`).
- `\xNN` produce un byte crudo; `\u{...}` produce UTF-8. Esta distinción es la
  que arregló B11 y hay que conservarla.
- `\u{...}` con codepoint inválido (> 0x10FFFF, surrogate) cae al caso
  “desconocido” y se conserva literalmente (stage0).
- En la parte literal de un string interpolado, un `\0` es un byte NUL. El
  codegen de F4 ya rechaza NUL en la parte de formato (`E0019`); F1 solo
  decodifica.
- `decode_string` devuelve un `string` owned; el llamador hace `banish`.

### 9.5 Tests de strings

- `"a\nb"` → 3 bytes `61 0A 62`.
- `"\x41B"` → `41 42` (A, B), no `0x41B`.
- `"\u{1F427}"` → 4 bytes UTF-8.
- `"\u0041"` → `A`.
- `"\101"` → `A`.
- `"\q"` → `\q` (dos bytes), sin error.
- `r"\n"` → `\` + `n`.
- `"""\n  a\n  b\n"""` → `a\nb\n` (dedent).
- `"""a {x} b"""` → 3 partes: Text `a `, Interp `x`, Text ` b`.
- `"{"a"}"` → una Interp con `"a"` dentro.
- `"a{ {x} }b"` → Interp ` {x} ` (profundidad 2).
- `"{sin cerrar"` → Text literal.
- `"\""` → un byte `"`.
- Strings con `ñ`, `日本語`, `😀`: bytes UTF-8 exactos, sin normalización.

---

## 📏 10. Post-lexer de indentación

### 10.1 Réplica del `Indenter` de Lark

Constantes y reglas:

- `NL_type = Newline`
- `OPEN = LeftParen, LeftBracket, LeftBrace`
- `CLOSE = RightParen, RightBracket, RightBrace`
- `INDENT/DEDENT` propios
- `tab_width = 2` (un tab cuenta como 2 espacios)
- `indent_width(newline_token) = espacios + 2 * tabs` en la indentación final
  del run.

Algoritmo (iterativo):

```text
stack = [0]
bracket_stack = []          # posiciones de apertura para diagnósticos
for tok in tokens_crudos:
    if tok.kind == Newline:
        if bracket_stack.len > 0:
            # dentro de paréntesis: se descarta
            continue
        emit Newline
        indent = tok.aux
        if indent > stack.top:
            stack.push(indent); emit Indent
        elif indent < stack.top:
            while indent < stack.top:
                stack.pop(); emit Dedent
            if indent != stack.top:
                emit E0000 IndentMismatch
                # recuperación: recordar el nivel para no repetir el error
                stack.push(indent); emit Indent
        # si indent == top: nada
    else if tok.kind in OPEN:
        bracket_stack.push(tok.start)
        emit tok
    else if tok.kind in CLOSE:
        if bracket_stack.len == 0:
            emit E0000 UnmatchedCloseBracket
        else:
            bracket_stack.pop
        emit tok
    else:
        emit tok

# EOF
while stack.len > 1:
    stack.pop(); emit Dedent
if bracket_stack not empty:
    for each open in bracket_stack: emit E0000 UnclosedBracket at open
emit Eof
```

Detalles:

- Si `keep_indent_tokens == false`, se emiten `NEWLINE` pero no `INDENT`/`DEDENT`
  (útil para tests y para un futuro modo “tokens planos”).
- Los `NEWLINE` dentro de paréntesis se descartan, incluida su indentación. Por
  eso un array multilínea no genera `INDENT`.
- Los `DEDENT` de EOF se emiten en orden LIFO, con span cero en EOF.
- Un `UnmatchedCloseBracket` no aborta; el parser de F2 verá el token y podrá
  recuperar.
- Un `UnclosedBracket` se diagnostica al final, con la posición del `(`/`[`/`{`.

### 10.2 NEWLINE sintético

Stage0 hace `clean_code = code.rstrip() + '\n'`, así que todo archivo termina en
newline. PSC replica el efecto sin modificar `SourceFile.text`:

- Si el último token significativo **no** es `Newline`, se emite un `Newline`
  sintético con `start == end == byte_len`, `line/col = eof_position`, `aux = 0`.
- Si el archivo está vacío, se emite ese `Newline` sintético.
- Los `DEDENT` y el `Eof` vienen después.
- `is_synthetic` se deduce de `start == end`; no hace falta un flag.

### 10.3 Dedent inconsistente

Ejemplo:

```pengu
weave f into int:
    if true:
        return 1
      return 2      # dedent a 6: no coincide con 0 ni con 4
```

Stage0 lanza `DedentError` y aborta. PSC:

1. Emite `E0000` con mensaje
   `unexpected dedent to column 6 (expected 4)`.
2. Hace `pop` hasta el nivel inferior (0), y como 6 no coincide, hace push de 6
   y emite `INDENT`.
3. Sigue lexando. El parser de F2 verá una secuencia plausible y podrá
   recuperar sin perder el resto del archivo.
4. Solo se emite **un** diagnóstico por nivel nuevo, no uno por línea.

### 10.4 `W0005`: indentación mixta

Se replica `_check_indentation_consistency`:

- Recorrer las líneas de `SourceFile.text`.
- Ignorar líneas vacías y líneas cuyo primer token es `#` (comentario).
- Guardar la primera línea cuya indentación contiene un tab y la primera cuya
  indentación contiene un espacio.
- Si ambas existen, emitir `W0005`:
  `Inconsistent indentation: line {tab_line} uses tabs, line {space_line} uses spaces`.
- El span del warning es un punto en la línea que introduce la inconsistencia
  (`max(tab_line, space_line)`, columna 1). Stage0 no tiene posición para este
  warning; el código y el mensaje sí coinciden.
- `warn_mixed_indentation = false` lo desactiva.

### 10.5 Tests de indentación

- 4 espacios vs 1 tab (ambos width 4) → sin error, `W0005` por mixta.
- 2 espacios → INDENT; 0 → DEDENT.
- Bloques anidados de 3 niveles.
- Línea en blanco entre bloques.
- Comentario solo en una línea indentada.
- Bloque doc `##` dentro de un bloque.
- `(` multilínea: sin INDENT/DEDENT; `)` cierra.
- `[` y `{` multilínea.
- `)` extra → `UnmatchedCloseBracket`.
- `(` sin cerrar → `UnclosedBracket`.
- Dedent a nivel inexistente → `IndentMismatch` + recuperación.
- Archivo sin newline final → NEWLINE sintético + DEDENT.
- Archivo vacío → NEWLINE sintético + EOF.

---

## 🩺 11. Diagnósticos

### 11.1 Integración con `std.diagnostic`

No se reimplementa el renderizador. `psc/diagnostics.pengu` es una fachada:

```pengu
import std.diagnostic as diag

const PSC_E_LEX as string is "E0000"
const PSC_E_ANTIQUUS as string is "E0059"
const PSC_E_CHAR as string is "E0057"
const PSC_W_INDENT as string is "W0005"

weave emit_issue with bag as ref to diag.DiagnosticBag,
                       src as ref to SourceFile,
                       issue as LexIssue,
                       span as ByteSpan,
                       detail as string into void

weave emit_error with bag as ref to diag.DiagnosticBag,
                     src as ref to SourceFile,
                     code as string,
                     message as string,
                     span as ByteSpan,
                     help as string,
                     note as string into void

weave emit_warning with bag as ref to diag.DiagnosticBag,
                       src as ref to SourceFile,
                       code as string,
                       message as string,
                       span as ByteSpan,
                       help as string into void

weave render_plain with bag as ref to diag.DiagnosticBag into string
weave render_colored with bag as ref to diag.DiagnosticBag into string
weave render_json with bag as ref to diag.DiagnosticBag into string
```

`span_of(src, span)`:

- clampa `start`/`end` a `[0, byte_len]`;
- ordena si vienen al revés;
- calcula `Position` con `source.position_at`;
- usa `diag.span_from_positions(path, sl, sc, el, ec, start, end)`.

Así nunca se dispara el `panic` de `span_from_positions` por una posición
inválida.

### 11.2 Tabla de `LexIssue`

| Issue | Código | Severidad | Mensaje | Help / note | Recuperación |
|---|---|---|---|---|---|
| `UnterminatedString` | E0000 | Error | `unterminated string literal` | cerrar con `"` | token hasta fin de línea/EOF |
| `UnterminatedTripleString` | E0000 | Error | `unterminated triple-quoted string literal` | cerrar con `"""` | token hasta EOF |
| `UnterminatedRawString` | E0000 | Error | `unterminated raw string literal` | cerrar con `"` | token hasta fin de línea/EOF |
| `UnterminatedChar` | E0000 | Error | `unterminated character literal` | cerrar con `'` | token hasta fin de línea |
| `InvalidCharLiteral` | E0000 | Error | `invalid character literal` | exactamente un carácter/escape | `CharLit` con `codepoint = -1` |
| `InvalidNumber` | E0000 | Error | `invalid numeric literal` | revisar dígitos/prefijo | token al siguiente delimitador |
| `UnknownCharacter` | E0000 | Error | `unexpected character '{c}'` | — | `Error` + avanzar 1 codepoint |
| `InvalidUtf8` | E0000 | Error | `source is not valid UTF-8` | guardar como UTF-8 | `Error` + avanzar 1 byte |
| `UnexpectedBom` | E0000 | Error | `unexpected byte-order mark` | quitar el BOM | `Error` + avanzar 3 bytes |
| `IndentMismatch` | E0000 | Error | `unexpected dedent to column {n} (expected {m})` | indentación consistente | push del nivel + INDENT |
| `MixedIndentation` | W0005 | Warning | `Inconsistent indentation: line {a} uses tabs, line {b} uses spaces` | usar tabs **o** espacios | ninguno |
| `UnmatchedCloseBracket` | E0000 | Error | `unmatched '{c}'` | revisar paréntesis/corchetes | sigue |
| `UnclosedBracket` | E0000 | Error | `unclosed '{c}'` | cerrar el delimitador | al EOF |
| `AntiquusMissingBody` | E0059 | Error | `Antiquus '{name}' has no triple-quoted C body` | usar `"""..."""` | no consume la línea |
| `AntiquusEmptyBody` | E0059 | Error | `Antiquus '{name}' has an empty C body` | añadir C | token vacío |
| `InterpolationTooDeep` | E0000 | Error | `interpolation nesting exceeds the limit ({n})` | simplificar la expresión | sigue al cierre |

Todos los códigos salvo `E0059`/`E0057`/`W0005` son `E0000`, igual que stage0
para errores de sintaxis/léxicos. No se inventan códigos nuevos en F1.

### 11.3 Ownership de los diagnósticos

`emit_issue` construye un `Diagnostic` con `std.diagnostic.diagnostic(...)`:

- `code` y `message` se copian dentro de `diagnostic`;
- `labels` (con el `Span`) se transfieren;
- `help`/`note` se pasan como `maybe string` y **se transfieren**;
- el `DiagnosticBag.add` toma el `Diagnostic`.

Reglas:

- `emit_issue` es dueño del `message` que construye y lo libera después de
  `add` (porque `diagnostic` copia).
- `detail` es prestado; no se libera.
- `help`/`note` se construyen dentro de `emit_issue` a partir de literales o
  interpolaciones locales; se pasan como `some h` y no se vuelven a tocar.
- Los call sites **no** pasan una interpolación directa a `emit_*`; usan
  `emit_issue` (que construye dentro) o bindean `msg` + `defer banish`.

### 11.4 `issues` en `LexResult` (opcional)

Para tests y para el LSP, puede ser útil saber qué `LexIssue` produjo cada
`Error`. Si se implementa:

- `LexResult.issues as list of int` guarda el índice de `LexIssue` (cast a int).
- `Token.aux` de un `Error` indexa esa lista.
- Es opcional porque añade un campo y una tabla; el MVP puede omitirlo y los
  tests leer los códigos del `DiagnosticBag`. Decisión en §21 (D7).

### 11.5 Render

- `render_plain`: `bag.render_plain`, sin color.
- `render_colored`: `bag.render_colored`, respeta `NO_COLOR` y TTY.
- `render_json`: `bag.render_json` (array LSP con `range`, `severity`, `code`,
  `source: "pengu"`, `message`).
- El CLI imprime diagnósticos a **stderr**; los tokens a **stdout**.
- `--diagnostics=json` imprime el array JSON a stderr y no el render humano.

### 11.6 Ejemplo de diagnóstico

Fixture `unterminated.pengu`:

```pengu
var s as string is "hola
```

Salida esperada (plain):

```text
error[E0000]: unterminated string literal
  --> unterminated.pengu:1:20
   |
 1 | var s as string is "hola
   |                    ^^^^^
   |
   = help: add a closing '"' before the end of the line
```

El span va desde la comilla de apertura hasta el final de la línea (o EOF).

---

## 🧰 12. Session y CLI

### 12.1 `Session`

```pengu
## Una compilación/snapshot. Dueña del fuente y del bag.
##
## ## Memoria
## `banish session` libera source, diagnostics y keywords.
rune Session derive Nexus:
    source as SourceFile
    diagnostics as diag.DiagnosticBag
    keywords as KeywordTable
    options as LexOptions
```

API:

| Función | Retorno | Notas |
|---|---|---|
| `Session.open(path, options)` | `Session` con `ok`/`error` | lee bytes, valida UTF-8, registra fuente en el bag |
| `Session.open_text(path, text, options)` | `Session` | para LSP/tests |
| `session.lex` | `LexResult` | llama a `lexer.lex` y deja los diagnósticos en el bag |
| `session.has_errors` | `bool` | `diagnostics.has_errors` |
| `session.render_plain/colored/json` | `string` owned | fachada de diagnósticos |
| `session.source` | `ref to SourceFile` | prestado |
| `session.path` | `string` | prestado |

`Session.open` devuelve **siempre** una `Session`: si el archivo no se pudo
leer, `ok` es `false` y `error` explica por qué. El lenguaje no tiene move
semantics, así que mover una `Session` fuera de un `result` obligaría a copiar
listas o a dejar un puntero colgando; el flag `ok` evita ambos.

Pasos:

1. `archivum.read_bytes(path)`.
2. Si falla: `err_of SourceError(kind=Read, path, message)`.
3. `SourceFile.from_bytes(path, raw)`.
4. `DiagnosticBag.new`; `add_source(path, file.text)` para que el render tenga
   contexto.
5. Validar UTF-8 con `lingua.validate`; si falla, `InvalidUtf8` en el offset
   del error.
6. Construir `KeywordTable`.
7. Devolver `ok_of session`.

`SourceError` se define en `source.pengu` (§6.1.1). `Session.open` no inventa
otro tipo de error: reutiliza el mismo para que el CLI tenga un único camino de
fallo de E/S.

### 12.2 CLI `psc`

`psc/src/main.pengu` es fino: parsea argv, abre `Session`, llama `lex`, imprime.
No contiene lógica de lexing.

```text
psc lex <file> [opciones]
psc lex --stdin [opciones]
psc version
psc --help
```

Opciones:

| Flag | Efecto |
|---|---|
| `--comments` | incluye la sección de comentarios en el dump |
| `--no-indent` | no emite INDENT/DEDENT (solo NEWLINE) |
| `--check` | no imprime tokens; solo diagnósticos |
| `--diagnostics=plain\|json` | formato de diagnósticos (default plain) |
| `--color` / `--no-color` | fuerza/desactiva ANSI (default: TTY) |
| `--stdin` | lee de `stdin` con `io.read_stdin_all`, path `<stdin>` |
| `--quiet` | sin banner |
| `--help` | ayuda |

Exit codes:

| Código | Cuándo |
|---:|---|
| `0` | lexación sin errores (warnings no fallan) |
| `1` | al menos un diagnóstico de severidad Error |
| `2` | uso incorrecto, archivo no encontrado, error de E/S |

Salida:

- Tokens TSV a stdout (§7.5), salvo `--check`.
- Diagnósticos a stderr; `--diagnostics=json` emite el array JSON.
- El banner `Lexing <file>` solo si no `--quiet` y stdout es TTY; los golden
  usan `--quiet`.

### 12.3 Ejemplos

```bash
# Dump de tokens
psc lex tests/conformance/compliance/arena_ast.pengu

# Solo comprobar errores léxicos
psc lex --check src/main.pengu

# Diagnósticos JSON para CI
psc lex --check --diagnostics=json src/main.pengu

# Desde stdin (LSP/tests)
printf 'weave main into int:\n    return 0\n' | psc lex --stdin
```

---

## 🗂️ 13. Organización de archivos

```text
psc/
├── pengu.toml
├── README.md
├── docs/
│   ├── PARITY.md                 # oracle, normalización, divergencias
│   └── OWNERSHIP.md              # contratos de memoria por función
├── src/
│   ├── main.pengu                # CLI fino
│   └── psc/
│       ├── span.pengu            # ByteSpan + helpers
│       ├── source.pengu          # SourceFile, LineIndex, SHA-256, BOM/CRLF
│       ├── diagnostics.pengu     # LexIssue, códigos, emit_*, render_*
│       ├── token.pengu           # TokenKind, KeywordKind, Token, KeywordTable
│       ├── token_dump.pengu      # nombres, escapes y TSV
│       ├── lexer.pengu           # bucle principal, operadores, palabras, números
│       ├── lexer_string.pengu    # strings/raw/triple/chars/interp
│       ├── lexer_decode.pengu    # decode/dedent/escapes
│       ├── lexer_comment.pengu   # comentarios y doc blocks
│       ├── lexer_antiquus.pengu  # detección y cuerpo C
│       ├── lexer_indent.pengu    # post-lexer INDENT/DEDENT + W0005
│       └── session.pengu         # Session, open/lex, SourceError
├── tests/
│   ├── lexer_unit.pengu
│   ├── lexer_source.pengu
│   ├── lexer_strings.pengu
│   ├── lexer_numbers.pengu
│   ├── lexer_comments.pengu
│   ├── lexer_indent.pengu
│   ├── lexer_antiquus.pengu
│   ├── lexer_recovery.pengu
│   ├── lexer_corpus.pengu
│   ├── lexer_determinism.pengu
│   └── fuzz_lex.pengu
├── tools/
│   ├── lark_token_oracle.py      # dev-only: stage0 contextual tokens
│   ├── run_f1_checks.py          # build + tests + oracle + golden
│   ├── fuzz_lex.py               # generador de entradas (si se usa)
│   └── asan_f1.sh                # ASan/UBSan sobre el corpus
└── tests/golden/
    ├── tokens/*.txt
    └── diagnostics/*.txt
```

Responsabilidades y tamaño objetivo:

| Archivo | Responsabilidad | Líneas objetivo |
|---|---|---:|
| `span.pengu` | valor y helpers de rango | ~80 |
| `source.pengu` | SourceFile + LineIndex + hash | ~260 |
| `diagnostics.pengu` | códigos, issue, emit, render | ~260 |
| `token.pengu` | tipos, tabla, helpers | ~300 |
| `token_dump.pengu` | nombres y TSV | ~240 |
| `lexer.pengu` | bucle, whitespace, palabras, números, operadores | ~520 |
| `lexer_string.pengu` | strings/chars/interp/decode | ~560 |
| `lexer_comment.pengu` | comentarios/doc blocks | ~220 |
| `lexer_antiquus.pengu` | antiquus | ~260 |
| `lexer_indent.pengu` | indentación + W0005 | ~260 |
| `session.pengu` | sesión y open | ~220 |
| `main.pengu` | CLI | ~300 |

Todos por debajo del máximo de 600–800 líneas del §8.4 de la auditoría.

`psc/pengu.toml`:

```toml
[project]
name = "psc"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
output_name = "psc"

[build]
src_dir = "src"
lib_dir = "lib"
include_dir = "include"
c_dir = "c"
build_dir = "build"
includes = []
links = ["pengu_runtime"]
lib_dirs = []
include_dirs = []
cflags = ["-Wall", "-std=c11"]
ldflags = []
defines = []
cc = "gcc"

[profiles.debug]
cflags = ["-g", "-O0", "-Wall"]
defines = ["DEBUG"]

[profiles.release]
cflags = ["-O3", "-DNDEBUG", "-ffunction-sections", "-fdata-sections"]
defines = ["NDEBUG"]
```

Build:

```bash
cd psc
pengu build            # -> psc/build/psc
pengu run tests/lexer_unit.pengu --no-cache
```

> Los tests son scripts `.pengu` bajo `psc/tests/`; `pengu run` desde `psc/`
> resuelve `import psc.lexer` contra `src/` (verificado con un proyecto de
> prueba). No se usa `pengu check` en modo script para estos tests porque en
> 3.0.3 no resuelve el `src_dir` del proyecto.

---

## 🧪 14. Plan de pruebas

### 14.1 Pirámide

| Nivel | Herramienta | Qué cubre |
|---|---|---|
| Unitario | `.pengu` scripts + `std.ward` | helpers, spans, LineIndex, tokens, escapes, indent |
| Golden | TSV/diagnósticos en `psc/tests/golden/` | estabilidad byte a byte |
| Corpus | `psc lex --check` sobre 175 archivos | no crash, diagnósticos inesperados |
| Paridad | `lark_token_oracle.py` | tokens vs stage0 contextual |
| Fuzz | `fuzz_lex.pengu` / `fuzz_lex.py` | 1 M entradas, sin crash/fuga |
| Memoria | ASan/UBSan | fugas en corpus + fuzz |
| Rendimiento | `bench` .pengu + stage0 | 1 MB, tokens/s |
| Determinismo | dos ejecuciones | dumps idénticos |

### 14.2 Unitarios (`.pengu`)

Cada archivo `psc/tests/lexer_*.pengu` tiene un `weave main into int` que:

- construye `SourceFile.from_text` con un fixture;
- crea `LexOptions`/`KeywordTable`;
- llama `lex`;
- compara tokens con `std.ward.assert_eq_int`/`assert_eq_string`;
- imprime `OK <test>` y devuelve 0;
- libera todo con `defer banish`.

Tests mínimos por archivo:

| Archivo | Casos |
|---|---|
| `lexer_source.pengu` | BOM, CRLF, vacío, sin newline final, `offset_of`, `line_text`, hash |
| `lexer_unit.pengu` | keywords, identificadores, operadores, posiciones, `aux` |
| `lexer_strings.pengu` | escapes, raw, triple, dedent, interpolación, char |
| `lexer_numbers.pengu` | dec/hex/bin/oct, `_`, floats, `1..2`, `1.foo`, `0x_` |
| `lexer_comments.pengu` | `#`, `##`, `##` block, inline, EOF, `#` en string |
| `lexer_indent.pengu` | espacios/tabs, anidación, brackets, dedent malo, W0005 |
| `lexer_antiquus.pengu` | single/multi/raw, atributos, `when`, vacío, faltante |
| `lexer_recovery.pengu` | unknown char, strings sin cerrar, chars inválidos, `)` extra |
| `lexer_corpus.pengu` | recorre una lista de archivos y lexa cada uno |
| `lexer_determinism.pengu` | dos lexaciones → dumps idénticos |

### 14.3 Golden

- `psc/tests/golden/tokens/*.txt`: 20–30 archivos representativos (AST,
  strings, antiquus, indentación, errores).
- `psc/tests/golden/diagnostics/*.txt`: render plain y JSON de 10–15 fixtures.
- Regeneración solo con revisión manual:
  `python psc/tools/run_f1_checks.py --update-golden`.
- Normalizar rutas a basename y quitar ANSI.

### 14.4 Oracle de paridad

`psc/tools/lark_token_oracle.py` (Python dev-only):

1. Importa `pengu_parser` del repo.
2. Para cada archivo:
   - lee UTF-8;
   - aplica la misma preparación que `PenguParser.parse` (BOM, CRLF, antiquus,
     comentarios, chain, struct init);
   - **monkeypatchea** `lark.lexer.LexerThread.lex` para capturar los tokens
     reales que consume el parser;
   - parsea con `start='start'`;
   - normaliza los tokens a `(family, lexeme, line, col, end_line, end_col)`.
3. Ejecuta `psc lex --quiet` y normaliza igual.
4. Compara según el nivel del archivo:
   - `exact`: familia + lexema + línea + columna;
   - `struct`: familia + lexema + línea;
   - `seq`: familia + lexema (hoy no hay archivos de este tipo);
   - `antiquus`: como `exact`, pero el token `ANTIQUUS` solo por familia.
5. Reporta diferencias con contexto y `--update-allowlist` para casos
   justificados.

Normalización de tipos de stage0:

| Stage0 | Canónico |
|---|---|
| `NAME`, `IMPORT`, `RUNE`, …, `__ANON_*` | `WORD` |
| `_TYPE_OF` | `TYPE_OF` |
| `_SIZE_OF` | `SIZE_OF` |
| `_AND_SEP`, `_BOOL_AND` | `WORD("and")` |
| `_BOOL_OR` | `WORD("or")` |
| `PAT_OR` | `OP("|")` |
| `COMPOUND_OP` | `OP(lexeme)` |
| `ANTIQUUS_BODY_PLACEHOLDER` | `ANTIQUUS` (sin lexema/span) |
| `_NEWLINE` | `NEWLINE(indent_width)` |
| `_INDENT` | `INDENT(indent_width)` |
| `_DEDENT` | `DEDENT` |
| `INT`, `FLOAT`, `STRING`, `TRIPLE_STRING`, `RAW_STRING`, `RAW_TRIPLE_STRING`, `CHAR_LIT` | familia de literal |
| `LPAR`, `COLON`, … | `OP(lexeme)` |

> Stage0 no emite un token `$END` en el stream capturado: el EOF es implícito
> del parser. El oracle añade un `EOF` sintético en `len(text)` para stage0 y
> otro para PSC, y los compara como último elemento. PSC emite `Eof` después de
> los `DEDENT` finales.

### 14.5 Corpus

- `psc lex --check` sobre los 175 archivos de `std/` + `tests/`.
- Criterio: ningún archivo válido produce diagnósticos de error; los 4 archivos
  que stage0 no puede tokenizar con `get_tokens` sí parsean y deben lexar sin
  error.
- Los archivos negativos de `tests/compiler/` se usan como fixtures de error
  sintáctico, no léxico; F1 solo comprueba que no hay crash.

### 14.6 Fuzz

Dos capas:

1. **`fuzz_lex.pengu`** (nativo, rápido, determinista):
   - LCG propio para generar bytes;
   - incluye alfabetos sesgados: `"`, `'`, `#`, `{`, `}`, `\`, `\n`, `\r`,
     `0x`, `r"""`, `antiquus`, tabs/espacios, bytes UTF-8 válidos e inválidos;
   - 1 000 000 de entradas de 0–512 bytes;
   - por entrada: `from_bytes` + `lex`; comprobar que no hay panic y que
     `tokens.len > 0`;
   - liberar `LexResult` en cada iteración (`defer banish` dentro del bucle o
     `banish` explícito);
   - no imprime nada salvo el resumen final.
2. **`fuzz_lex.py`** (opcional, dev-only):
   - muta archivos reales del corpus;
   - ejecuta `psc lex --check` en un subprocess por lote;
   - sirve para reproducir un crash concreto.

El fuzz nativo se corre en CI nocturna con ASan; en el día a día, una muestra de
100 000.

### 14.7 ASan/UBSan

Comandos base (los mismos de la auditoría):

```bash
PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -g" \
PENGU_LDFLAGS="-fsanitize=address,undefined" \
ASAN_OPTIONS="detect_leaks=1:halt_on_error=1" \
pengu build
```

Luego:

```bash
./build/psc lex --check <cada archivo del corpus>
./build/psc lex --check psc/tests/fixtures/fuzz_sample.txt
```

Criterio: cero leaks y cero errores de UBSan.

### 14.8 Determinismo

- Ejecutar `psc lex --quiet` dos veces sobre el corpus y comparar los TSV
  (`sha256sum`).
- No debe haber rutas absolutas, timestamps ni orden de mapas.
- El hash del fuente y el dump deben ser estables entre ejecuciones y entre
  Debug/Release.

### 14.9 Benchmarks

- `psc/tests/bench_lex.pengu`: genera 1 MB de fuente variada (código, strings,
  comentarios) y mide con `std.chronicle`; imprime tokens, bytes, ms y
  tokens/s.
- Comparación con stage0: medir `pengu check` sobre el mismo archivo (incluye
  parseo, así que es una cota superior) y con el oracle de tokens (solo
  lexing).
- Medición real en F1 (3,0 MB, 760 001 tokens, x86_64): **11,8 MB/s en
  Release** y **1,8 MB/s en Debug**. La prioridad es no regresar respecto a
  stage0; el lexer nativo es >20× más rápido que la tokenización Python.

---

## 🎯 15. Paridad con stage0

### 15.1 Qué significa “mismo token”

No comparamos los nombres internos de Lark (`__ANON_8`, `_BOOL_OR`, …). Comparamos
la **proyección canónica**:

```text
(family, lexeme, line, col, end_line, end_col)
```

donde `family` es una de:

```text
WORD, TYPE_OF, SIZE_OF, INT, FLOAT, STRING, CHAR, OP, NEWLINE, INDENT,
DEDENT, ANTIQUUS, EOF
```

Para keywords, `lexeme` es la palabra; para operadores, el símbolo; para
`NEWLINE`, el ancho de indentación; para `INDENT`, el ancho; para `DEDENT`,
nada.

### 15.2 Niveles

| Nivel | Archivos | Comparación |
|---|---|---|
| `exact` | 146 | familia + lexema + línea + columna + end |
| `struct` | 1 (`std/compressus.pengu`) | familia + lexema + línea |
| `seq` | 0 (previsto para cadenas `.method`) | familia + lexema |
| `antiquus` | 28 | exact, salvo `ANTIQUUS` (solo familia) |

Criterio de salida: **100 % de los 175 archivos** en su nivel, sin diferencias
no allowlisteadas. Si aparece una diferencia, se investiga; solo se allowlistea
si es una divergencia deliberada y documentada.

### 15.3 Divergencias deliberadas (documentadas en `PARITY.md`)

1. **Keywords contextuales.** Stage0 acepta keywords duras como nombres en
   posiciones de `NAME`; PSC no. El corpus no las usa.
2. **Trivia.** PSC captura comentarios; stage0 los borra. El oracle los ignora.
3. **Spans de `INDENT`/`DEDENT`.** PSC usa ancho cero; stage0 presta el span del
   `NEWLINE`. El oracle normaliza.
4. **CRLF.** PSC preserva `\r\n`; stage0 normaliza a `\n`. Las líneas/columnas
   coinciden; los offsets de byte no se comparan.
5. **`NEWLINE` sintético.** PSC no modifica `text`; stage0 añade `\n`. Ambos
   producen un token final; el oracle lo normaliza.
6. **Cuerpo `antiquus`.** Stage0 sustituye por placeholder y luego restitcha;
   PSC guarda el cuerpo real. El oracle compara solo la presencia/tipo.
7. **Comentarios y doc blocks.** PSC los captura; stage0 los blankea. No afectan
   a los tokens significativos.
8. **Interpolación anidada.** PSC soporta profundidad arbitraria (hasta el
   límite); stage0 la soporta solo parcialmente por su regex. PSC es un
   superconjunto en los casos válidos.
9. **UTF-8 inválido.** Stage0 falla al leer; PSC diagnostica y sigue.
10. **Dedent inconsistente.** Stage0 aborta con `DedentError`; PSC diagnostica y
    recupera.
11. **`W0005`.** Stage0 usa `warnings.warn` sin posición; PSC lo convierte en un
    `Diagnostic` con span.
12. **Interpolación multilínea dentro de un triple.** PSC guarda el span crudo
    de la expresión y el parser usa ese texto; stage0 dedenta el contenido
    completo antes de separar las partes. El árbol es el mismo, pero una
    columna dentro de una expresión multilínea puede diferir. F1 documenta la
    limitación; no afecta a los tokens del literal.
13. **“Múltiples statements en una línea”.** Stage0 lo rechaza en el
    `PenguIndenter` (`var x is 1 var y is 2`). PSC no lo comprueba en el lexer:
    lo rechazará el parser de F2 con la gramática. Es un chequeo sintáctico,
    no léxico.
14. **Paréntesis de cierre sobrante.** Stage0 hace `assert paren_level >= 0` y
    puede abortar con un `AssertionError`; PSC emite
    `UnmatchedCloseBracket` y sigue. Es una mejora de robustez para el LSP.
15. **Fase de `E0059`.** Stage0 valida el cuerpo `antiquus` en el checker; PSC
    lo valida en el lexer porque el cuerpo ya no es un placeholder textual. El
    código y el span del diagnóstico son los mismos; cambia la fase que lo
    emite.

### 15.4 Lo que **no** se relaja

- El lexema de cada token significativo debe coincidir exactamente.
- La secuencia de `NEWLINE`/`INDENT`/`DEDENT` debe coincidir en ancho y orden.
- Las líneas/columnas de tokens en archivos `exact` deben coincidir.
- Los literales válidos deben decodificar a los mismos bytes que stage0
  (`_decode_literal`).

---

## ⚡ 16. Rendimiento

### 16.1 Objetivos

| Métrica | Objetivo |
|---|---|
| Throughput Debug | ≥ 1,5 MB/s (medido 1,8 MB/s) |
| Throughput Release | ≥ 10 MB/s (medido 11,8 MB/s) |
| 1 MB de fuente | ~0,1 s Release / ~0,55 s Debug |
| Tokens del corpus (321 k) | < 50 ms Release (medido) |
| Asignaciones por token | **0** |
| Memoria de `LexResult` | ~32 bytes/token + tablas de literales |

### 16.2 Decisiones que lo hacen posible

- `Token` es POD de 7 enteros; no hay `string` por token.
- El lexer recorre `bytes of text` con un índice; no crea substrings para
  comparar keywords (usa la tabla con `word` temporal solo para identificadores;
  se puede optimizar comparando por longitud/rango, pero no es necesario en el
  MVP).
- Los literales solo se decodifican cuando F2/F4 lo piden.
- La indentación es una pasada lineal sobre la lista de tokens.
- `SourceFile.position_at` es O(log líneas); el dump lo llama 2 veces por token,
  aceptable para una herramienta offline. El parser de F2 puede cachear la
  posición si hace falta.

### 16.3 Riesgos de rendimiento

- `KeywordTable` con búsqueda binaria sobre `string` puede ser caro; si el
  benchmark muestra que es el cuello, se añade un índice por primera letra
  (26 buckets) sin cambiar la API.
- `SourceFile.slice` en `scan_word` asigna un `string` por identificador.
  Optimización futura: comparar el rango con la tabla sin materializar. En el
  MVP, 321 k identificadores no son un problema; el benchmark decide.
- `DiagnosticBag.add_source` copia el fuente; para 1 MB son 1 MB extra. Aceptable
  y documentado.

---

## 🧠 17. Ownership y fugas

### 17.1 Reglas de oro

1. **`LexResult` es dueño de sus seis listas**; `banish result` las libera.
   Todos los elementos son POD, así que no hay liberación recursiva.
2. **`SourceFile` es dueño de `text`, `line_starts`, `sha256`, `path`**;
   `banish file` los libera.
3. **`Session` es dueño de `source`, `diagnostics`, `keywords`**;
   `banish session` los libera.
4. **`DiagnosticBag` es dueño de sus diagnósticos y de las copias de fuentes**;
   `banish bag` los libera.
5. **Las funciones `decode_*` devuelven `string` owned**; el llamador hace
   `banish`.
6. **Los parámetros `string`/`ref to` son prestados**; la función no los libera.
7. **Nunca** pasar una interpolación directa a una función que no la va a
   consumir; bindear y `defer banish`.
8. **`defer banish`** en cada recurso local: `SourceFile`, `Session`,
   `LexResult`, `StringBuilder`, strings temporales.
9. **No hay `banish` por token ni por nodo**; las listas se liberan de golpe.
10. **Los `word` de `KeywordTable` son literales estáticos** (`is_owned = 0`);
    `banish table` libera la lista, no las palabras.

### 17.2 Tabla de recursos

| Recurso | Dueño | Liberación |
|---|---|---|
| `SourceFile.text` | `SourceFile` | `banish file` |
| `SourceFile.line_starts` | `SourceFile` | `banish file` |
| `SourceFile.sha256` | `SourceFile` | `banish file` |
| `LexResult.tokens/comments/...` | `LexResult` | `banish result` |
| `StringInfo`/`StringPart`/`CharInfo`/`AntiquusInfo` | `LexResult` | `banish result` (POD) |
| `DiagnosticBag.items/_sources` | `DiagnosticBag` | `banish bag` |
| `KeywordTable.entries` | `KeywordTable` | `banish table`; palabras estáticas |
| `decode_*` result | llamador | `banish` |
| `SourceFile.slice/line_text` | llamador | `banish` |
| `issue_message` temporal | `emit_issue` | `banish` tras `bag.add` |

### 17.3 Checklist de PR

- [ ] Cada `string`/`list`/`map`/`maybe`/`result` devuelto tiene dueño
      documentado.
- [ ] Cada recurso local tiene `defer banish`.
- [ ] No hay interpolaciones directas como argumento.
- [ ] No se itera un `map` para emitir salida.
- [ ] `psc lex` sobre el corpus pasa ASan sin leaks.
- [ ] El fuzz nativo pasa ASan sin leaks.
- [ ] No se usa `spark.panic` para errores de usuario.

---

## ⚠️ 18. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Divergencia de tokens por el lexer contextual de stage0 | Alta | Medio | Oracle con captura durante parse; keywords duras/soft documentadas; allowlist |
| Divergencia en comentarios/doc blocks | Media | Alto | Replicar `_strip_comments` caso por caso; 54 archivos del corpus; tests |
| Divergencia en strings/interpolación | Media | Alto | Portar `extract_string_parts` + `_decode_literal`; fuzz diferencial; tests |
| `antiquus` mal detectado | Media | Alto | 204 casos en corpus; tests de single/multi/raw/atributos/`when` |
| Indentación distinta de Lark | Media | Alto | Replicar `Indenter` (tab=2, paréntesis); oracle de `_NEWLINE/_INDENT`; tests |
| Fugas de memoria | Alta | Alto | POD results; `defer banish`; ASan desde el día 1; checklist |
| Rendimiento pobre | Baja | Medio | Zero-copy, tablas, sin recursión; benchmark 1 MB |
| API de tokens inestable para F2 | Media | Medio | Checkpoint de revisión al final de F1; congelar `TokenKind`/`Token` |
| Falta de `psc/` y oracle | Alta | Bajo | Paso 0 de F1 los crea; no se reabre F0 |
| Windows/macOS | Baja | Bajo | F1 no tiene código de SO; lectura binaria; tests de CRLF |
| Scope creep (parser/LSP) | Media | Medio | No-objetivos explícitos; F1 se cierra con DoD |
| `std.diagnostic` cambia | Baja | Medio | Fachada `diagnostics.pengu`; tests de render |
| `SourceFile` y LSP | Media | Medio | Texto inmutable y offsets de byte; UTF-16 se convierte en F8 |

---

## 🗓️ 19. Orden de implementación y estimación

### 19.1 Secuencia

| # | Paso | Días | Depende de | Entregable |
|---:|---|---:|---|---|
| 0 | Scaffold `psc/` + `pengu.toml` + `main` vacío + build verde | 1 | — | `pengu build` funciona |
| 1 | `span.pengu` + `source.pengu` + tests | 2 | 0 | `SourceFile` completo |
| 2 | `diagnostics.pengu` + integración `DiagnosticBag` | 1.5 | 1 | diagnósticos renderizan |
| 3 | `token.pengu` + `KeywordTable` + `token_dump.pengu` | 2 | 0 | tokens y dump TSV |
| 4 | `lexer.pengu` núcleo: whitespace, palabras, operadores, newline | 3 | 3 | tokens básicos |
| 5 | `lexer_string.pengu`: strings/raw/triple/chars/interp/decode | 4 | 4 | literales |
| 6 | números + comentarios/doc blocks | 2 | 4 | corpus léxico |
| 7 | `lexer_indent.pengu` + W0005 + brackets | 2 | 4 | INDENT/DEDENT |
| 8 | `lexer_antiquus.pengu` | 2 | 5 | 204 casos |
| 9 | `session.pengu` + CLI `lex` | 2 | 2,7 | `psc lex` |
| 10 | Oracle + corpus + golden + fixes de paridad | 3 | 9 | 175 archivos |
| 11 | Fuzz + ASan + benchmark + docs | 3 | 10 | DoD |
|  | **Total** | **25.5** |  |  |

Nota: la auditoría estima 3–4 persona-semanas; este desglose es conservador
(4–5 semanas calendario con revisión, imprevistos y algún fix de paridad).

### 19.2 Checkpoints

1. **CP1 (paso 3):** tipos de token congelados; revisar que F2 tenga lo que
   necesita (keywords, operadores, spans, indent tokens).
2. **CP2 (paso 5):** strings completos; ejecutar el oracle parcial sobre 20
   archivos.
3. **CP3 (paso 9):** `psc lex` funciona sobre todo el corpus; medir tiempo.
4. **CP4 (paso 10):** oracle 100 %; allowlist vacía o justificada.
5. **CP5 (paso 11):** ASan/fuzz/bench/docs; cerrar F1.

### 19.3 Qué no se hará aunque sobre tiempo

- Parser, AST, checker.
- JSON completo de tokens.
- Extracción de doc a símbolos.
- Cache incremental.
- Cambios en `std/` o en el compilador Python (salvo un bug bloqueante,
  coordinado aparte).

---

## ✅ 20. Criterios de aceptación (DoD)

### 20.1 Funcional

- [ ] `cd psc && pengu build` compila sin errores.
- [ ] `psc lex <archivo>` produce un dump TSV estable.
- [ ] `psc lex --check` no imprime tokens y devuelve 1 si hay errores.
- [ ] `psc lex --stdin` funciona.
- [ ] `psc lex --diagnostics=json` produce JSON válido.
- [ ] Los 175 archivos de `std/` + `tests/` se lexan sin panic.
- [ ] Los 28 archivos con `antiquus` se lexan correctamente.
- [ ] Los 54 archivos con doc blocks se lexan sin tratar el texto como código.
- [ ] Los archivos con CRLF/BOM sintéticos se lexan con posiciones correctas.

### 20.2 Paridad

- [ ] Oracle: 146 archivos `exact` sin diferencias.
- [ ] Oracle: `std/compressus.pengu` `struct` sin diferencias.
- [ ] Oracle: 28 archivos `antiquus` sin diferencias (salvo cuerpo).
- [ ] Diferencias allowlisteadas = 0 o justificadas en `PARITY.md`.
- [ ] Secuencia de `NEWLINE`/`INDENT`/`DEDENT` idéntica en ancho y orden.
- [ ] Literales decodificados idénticos a `_decode_literal` de stage0.

### 20.3 Robustez

- [ ] Fuzz nativo de 1 M de entradas: cero crashes.
- [ ] Fuzz con ASan: cero leaks.
- [ ] `psc lex` sobre el corpus con ASan: cero leaks.
- [ ] `Unterminated*`, `InvalidChar`, `UnknownCharacter`, `IndentMismatch`,
      `UnclosedBracket` producen diagnósticos con línea/columna.
- [ ] El lexer nunca lanza una excepción de Python/stage0 (es nativo) y nunca
      usa `spark.panic` para entrada de usuario.

### 20.4 Rendimiento y determinismo

- [ ] 1 MB lexado en < 200 ms Debug (objetivo; se ajusta con la medición).
- [ ] Dos ejecuciones producen dumps idénticos.
- [ ] Sin rutas absolutas/timestamps en la salida.
- [ ] La memoria de `LexResult` es lineal en tokens y no hay asignación por
      token (verificado con ASan/inspección).

### 20.5 Documentación

- [ ] `psc/README.md` con build/run/test.
- [ ] `psc/docs/PARITY.md` con oracle, niveles y divergencias.
- [ ] `psc/docs/OWNERSHIP.md` con la tabla de §17.
- [ ] `AUDITORIA_AUTO_HOSPEDAJE.md` sigue intacto (no se edita sin pedirlo).
- [ ] `CHANGELOG.md` no se toca todavía (F1 es interno; se anotará al cerrar
      la fase o al preparar el release de PSC).

---

## ❓ 21. Decisiones que necesito de ti

Marca cada una; las recomendadas son las que desbloquean la implementación.

### D1 — Modelo de tokens

- [x] **Recomendado:** zero-copy + tablas laterales (`Token` POD, literales
  decodificados bajo demanda).
- [ ] Alternativa: `Token` con `string` decodificado (más simple de leer, más
  memoria y más fugas potenciales).

### D2 — Keywords contextuales

- [x] **Recomendado:** keywords duras + soft keywords; PSC rechaza keywords
  duras como nombres (stage0 las acepta por su lexer contextual). Divergencia
  documentada.
- [ ] Alternativa: replicar la permisividad de stage0 en F2/F3 con un modo
  `--lenient-keywords`; más trabajo y menos seguridad.

### D3 — CRLF y offsets

- [x] **Recomendado:** preservar CRLF, quitar solo el BOM, offsets de byte
  relativos al texto sin BOM, hash de los bytes originales.
- [ ] Alternativa: normalizar CRLF como stage0; se pierden offsets exactos del
  archivo y el LSP tiene que remapear.

### D4 — `antiquus`

- [x] **Recomendado:** escaneo nativo en el lexer, sin reescribir el texto.
- [ ] Alternativa: pre-pasada textual como stage0 (más fácil de portar, pero
  duplica la lógica y pierde posiciones exactas del cuerpo).

### D5 — Salida del CLI

- [x] **Recomendado:** TSV canónico + diagnósticos JSON; JSON de tokens en
  F2/F6.
- [ ] Alternativa: JSON completo de tokens ya en F1 (más trabajo de `std.json` y
  de esquema; no lo necesita F2).

### D6 — Oracle

- [x] **Recomendado:** Python dev-only que captura tokens contextuales durante
  un `parse` real de stage0.
- [ ] Alternativa: solo golden propios de PSC, sin comparación con stage0 (menos
  confianza en la paridad).

### D7 — `issues` en `LexResult`

- [x] **Recomendado:** omitir en el MVP; los tests leen el `DiagnosticBag`.
  Añadirlo solo si F2 lo necesita.
- [ ] Incluirlo desde F1 (`Token.aux` de `Error` indexa `issues`).

### D8 — Alcance de `E0057`

- [x] **Recomendado:** F1 guarda `codepoint`; F3 emite `E0057` para chars
  > 0x7F (igual que stage0, que lo valida en sema).
- [ ] Emitir `E0057` ya en F1 (adelanta trabajo semántico y mezcla capas).

---

## 📎 22. Anexos

### A. Keywords duras (`KeywordKind`)

La lista exacta (70 palabras), en orden alfabético para la tabla:

```text
alias, and, antiquus, as, banish, bind, break, bytes, calling, chr, concept,
const, continue, cyclus, declare, defer, defined, derive, donum, echo, else,
enchanting, errdefer, error, essence, false, for, from, if, import, in,
include, insignia, into, is, judge, lambda, ldflag, let, link, many, maybe,
none, not, null, of, omen, or, ord, return, rune, seal, set, shard, sigil,
some, static, step, test, to, transmute, true, try, unless, var, weave, when,
where, while, with
```

En `KeywordKind` cada palabra se escribe en PascalCase (`alias` → `Alias`,
`errdefer` → `Errdefer`, `when` → `When`, …). La lista se cubre con un test que
la compara contra `LANGUAGE.md` §3.4 y falla si alguien añade una palabra sin
actualizar la tabla.

**Soft / identificadores especiales** (no están en `KeywordKind`): `self`,
`unsafe`, `over`, `frozen`, `inline`, `ritual`, `do`, `type`, `size`, `main`,
`ok`, `err`. `size` está en la lista de reservadas de `LANGUAGE.md`, pero se
trata como soft porque solo es keyword en `size of`; lo mismo vale para `type`,
que ni siquiera figura en esa lista.

### B. Operadores

| Lexema | TokenKind | Notas |
|---|---|---|
| `(` `)` | `LeftParen` `RightParen` | |
| `[` `]` | `LeftBracket` `RightBracket` | |
| `{` `}` | `LeftBrace` `RightBrace` | mapas |
| `,` | `Comma` | |
| `:` | `Colon` | bloques, mapas, labels |
| `;` | `Semicolon` | no usado por la gramática; el parser lo rechaza |
| `.` | `Dot` | acceso |
| `..` | `DotDot` | rango deprecado `W0013` (sema) |
| `...` | `Ellipsis` | varargs |
| `->` | `Arrow` | acceso a campo de puntero |
| `@` | `At` | atributos |
| `+ - * / %` | `Plus`, `Minus`, `Star`, `Slash`, `Percent` | aritmética |
| `& | ^ ~` | `Ampersand`, `VerticalBar`, `Caret`, `Tilde` | bitwise |
| `!` | `Bang` | solo en `!=`; suelto lo rechaza el parser |
| `=` | `Assign` | no usado; el parser lo rechaza |
| `== != < <= > >=` | `Equal`, `NotEqual`, `Less`, `LessOrEqual`, `Greater`, `GreaterOrEqual` | comparación |
| `<< >>` | `ShiftLeft` `ShiftRight` | shifts |
| `+= -= *= /= %= &= |= ^= <<= >>=` | `PlusAssign` … `ShiftRightAssign` | compound assignment |

### C. Códigos de diagnóstico de F1

| Código | Uso | Severidad |
|---|---|---|
| `E0000` | todos los errores léxicos/de indentación | Error |
| `E0059` | `antiquus` sin cuerpo / cuerpo vacío | Error |
| `E0057` | char > 0x7F (F3, no F1) | Error |
| `W0005` | indentación mixta tabs/espacios | Warning |

No se añaden códigos nuevos. Si más adelante se quiere distinguir
“unterminated string” de “indentation”, se puede añadir un `DiagnosticKind`
interno sin cambiar el código público.

### D. Normalización del oracle (resumen)

```text
stage0 token                     canónico
------------------------------   ---------------------------------
NAME / keyword literal / ANON    WORD(lexeme)
_TYPE_OF                         TYPE_OF
_SIZE_OF                         SIZE_OF
_AND_SEP / _BOOL_AND             WORD("and")
_BOOL_OR                         WORD("or")
PAT_OR                           OP("|")
COMPOUND_OP                      OP(lexeme)
ANTIQUUS_BODY_PLACEHOLDER        ANTIQUUS (sin lexema/span)
_NEWLINE                         NEWLINE(indent_width)
_INDENT                          INDENT(indent_width)
_DEDENT                          DEDENT
INT/FLOAT/STRING/CHAR            familia + lexema
puntuación                       OP(lexema)
```

### E. Comandos de trabajo

```bash
# Build
cd psc && pengu build

# Tests unitarios
cd psc && pengu run tests/lexer_unit.pengu --no-cache

# Corpus
cd psc && pengu run tests/lexer_corpus.pengu --no-cache

# Oracle
python psc/tools/lark_token_oracle.py --corpus std tests --psc psc/build/psc

# Golden
python psc/tools/run_f1_checks.py --update-golden

# Fuzz (nativo)
cd psc && pengu run tests/fuzz_lex.pengu --no-cache -- --iterations 1000000

# ASan
PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -g" \
PENGU_LDFLAGS="-fsanitize=address,undefined" \
ASAN_OPTIONS="detect_leaks=1:halt_on_error=1" \
pengu build
./build/psc lex --check src/main.pengu

# Determinismo
cd psc && ./build/psc lex --quiet src/main.pengu > /tmp/a.tsv
cd psc && ./build/psc lex --quiet src/main.pengu > /tmp/b.tsv
diff /tmp/a.tsv /tmp/b.tsv
```

### F. Glosario

| Término | Significado |
|---|---|
| **PSC** | PenguScript Compiler, la implementación nueva en `.pengu` |
| **stage0** | El compilador Python actual |
| **Token POD** | Token sin heap: solo enteros y un `omen` |
| **Side table** | Lista paralela indexada por `Token.aux` |
| **Trivia** | Comentarios y espacios que no son tokens significativos |
| **Span** | Rango half-open de bytes |
| **Oracle** | Implementación de referencia que produce la salida esperada |
| **L-EXACT / L-STRUCT / L-SEQ / L-ANTIQ** | Niveles de comparación del oracle |

### G. Referencias

- [`AUDITORIA_AUTO_HOSPEDAJE.md`](AUDITORIA_AUTO_HOSPEDAJE.md) §7–§9.
- [`LANGUAGE.md`](LANGUAGE.md) §3 (lexical), §15 (literales), §22 (catálogo).
- [`pengu_parser/pengu_parser.py`](pengu_parser/pengu_parser.py): `PenguIndenter`,
  `_strip_comments`, `_merge_chain_continuations`,
  `_expand_short_struct_inits`, `_extract_antiquus_bodies`,
  `extract_string_parts`.
- [`pengu_parser/pengu_grammar.py`](pengu_parser/pengu_grammar.py): terminales,
  prioridades y keywords.
- [`pengu_parser/pengu_codegen/interpolate.py`](pengu_parser/pengu_codegen/interpolate.py):
  `_decode_literal`, `_c_escape_bytes`.
- [`std/diagnostic.pengu`](std/diagnostic.pengu),
  [`std/sourcemap.pengu`](std/sourcemap.pengu),
  [`std/digest.pengu`](std/digest.pengu),
  [`std/lingua.pengu`](std/lingua.pengu).
- [`docs/error_catalog.json`](docs/error_catalog.json) y
  [`LANGUAGE.md`](LANGUAGE.md) §22.
- [`PenguScriptGuideSpanish.md`](PenguScriptGuideSpanish.md) — guía idiomática
  (chaining de `calling`, retornos múltiples, métodos de encantamiento).

---

## ✅ Estado de implementación de F1

Implementado y verificado en este árbol:

- [x] `psc/` con `pengu.toml`, CLI y 14 módulos.
- [x] `SourceFile` (BOM, CRLF, LineIndex, SHA-256) y tests.
- [x] `Token` zero-copy + `KeywordTable` + `token_dump` TSV.
- [x] Lexer de keywords, identificadores, números, operadores, strings/raw/triples,
      chars, comentarios/doc blocks y `antiquus`.
- [x] Post-lexer de indentación con recuperación y `W0005`.
- [x] Diagnósticos `E0000`/`E0059`/`W0005` plain/ANSI/JSON.
- [x] `Session` y `psc lex` (`--stdin`, `--comments`, `--check`,
      `--diagnostics=json`, `--color`, `--no-color`).
- [x] 12 grupos de tests unitarios en `.pengu`.
- [x] Golden de 14 tokens y 10 diagnósticos.
- [x] Oracle: **175 archivos, 0 fallos** (`exact:146`, `antiquus:28`,
      `struct:1`).
- [x] Corpus: 175 archivos sin errores; ASan/UBSan limpio en 208 archivos.
- [x] Fuzz de **1 000 000** de entradas sin crashes.
- [x] Benchmark Release: **11,8 MB/s** (3,0 MB, 760 001 tokens).
- [x] Regresión del bug de stage0 “import alias vs parámetro local” y fix en
      `pengu_parser/pengu_codegen/exprs.py`.

Pendiente para F2: parser/AST; F1 no deja deuda funcional conocida.

## 🏁 Cierre

Este plan implementa **solo F1**. Si lo apruebas tal cual (o con cambios en
§21), el siguiente paso es crear el esqueleto de `psc/`, implementar
`SourceFile` y empezar el lexer en el orden de §19.

**Lo que necesito de ti para arrancar:**

1. Confirmar las decisiones D1–D8 (basta con “todas las recomendadas”).
2. Confirmar que `psc/` se crea desde cero (no existe hoy).
3. Confirmar que el oracle Python dev-only es aceptable.
4. Confirmar que F1 **no** toca `std/`, el compilador Python ni la auditoría.

Con eso, empiezo por el paso 0 y te voy reportando por checkpoints.
