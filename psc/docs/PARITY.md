# Paridad de PSC con stage0

## F1 — Tokens

### Método

`PenguParser.get_tokens()` **no es un oracle válido**: no aplica
`_strip_comments` y su comprobación de “múltiples statements en una línea” da
falsos positivos. El oracle de F1
([`tools/lark_token_oracle.py`](../tools/lark_token_oracle.py)) monkeypatchea
`lark.lexer.LexerThread.lex` y captura exactamente los tokens que consume un
`parse` real, con el lexer contextual de Lark.

Después normaliza ambos lados a una proyección canónica:

```text
(family, lexeme, line, byte_column)
```

Familias: `WORD`, `INT`, `FLOAT`, `STRING`, `CHAR`, `OP`, `NEWLINE`, `INDENT`,
`DEDENT`, `ANTIQUUS`, `EOF`.

- Lark cuenta columnas de **codepoint**; el oracle las convierte a columnas de
  byte usando el texto de la línea. PSC usa columnas de byte.
- Los lexemas del dump de PSC escapan bytes ≥ 0x7F como `\xNN`; el oracle los
  reconstruye y los decodifica como UTF-8.

### Resultado actual

```text
files=175 skipped=0 failures=0
levels=antiquus:28, exact:146, struct:1
```

- **exact (146):** familia + lexema + línea + columna de byte.
- **antiquus (28):** igual, salvo que el token `ANTIQUUS` se compara solo por
  familia (stage0 lo sustituye por un placeholder antes de parsear).
- **struct (1, `std/compressus.pengu`):** stage0 parsea un buffer reescrito por
  `_expand_short_struct_inits`; el oracle ejecuta PSC sobre **ese mismo buffer**
  para comparar manzanas con manzanas. El archivo original también se lexa en la
  pasada de corpus.

### Divergencias de F1

1. **Comentarios.** Stage0 los borra antes de parsear; PSC los captura como
   trivia. No son tokens significativos.
2. **Spans de `INDENT`/`DEDENT`.** Stage0 les presta el span del `NEWLINE`; PSC
   usa ancho cero en el primer token de la línea. El oracle compara secuencia y
   ancho, no la posición del delimitador.
3. **`NEWLINE` en líneas de solo comentario.** Stage0 blankea el comentario, así
   que su `_NEWLINE` puede empezar al inicio de la línea; PSC lo emite en el
   salto real.
4. **CRLF.** PSC preserva `\r\n`; stage0 normaliza a `\n`. Línea/columna de byte
   coinciden; el offset absoluto difiere.
5. **Cuerpo `antiquus`.** Stage0 lo sustituye por un placeholder y lo restitcha;
   PSC guarda el cuerpo real.
6. **UTF-8 inválido.** Stage0 falla al leer; PSC emite `E0000` y sigue lexando.
7. **Dedent inconsistente.** Stage0 aborta con `DedentError`; PSC emite `E0000`
   y recuerda el nuevo nivel.
8. **Paréntesis de cierre sobrante.** Stage0 puede abortar con un
   `AssertionError`; PSC emite `UnmatchedCloseBracket`.
9. **`E0059`.** Stage0 valida el cuerpo `antiquus` en el checker; PSC lo valida
   en el lexer. Mismo código y span.
10. **`W0005`.** Stage0 usa `warnings.warn` sin posición; PSC lo convierte en un
    `Diagnostic` con span.
11. **“Múltiples statements en una línea”.** Stage0 lo rechaza en el
    `PenguIndenter`; F1 lo delegó a F2. **F2 ya lo implementa** con el mismo
    mensaje y posición.
12. **Interpolación multilínea en triples.** PSC guarda el span crudo de la
    expresión; stage0 dedenta el contenido completo antes de separar las partes.
13. **Cadenas multilínea (`.`/`->`).** F1 no las plegaba; **corregido en F2**
    con `LexOptions.fold_chain_continuations`. El oracle de tokens no tiene
    regresiones.
14. **Keywords como nombres.** Stage0 usa un lexer contextual y acepta
    `var if as int is 5`; F1 documentó que PSC las rechazaría. **F2 las acepta
    en posiciones de nombre** (declaraciones, campos, parámetros, patrones,
    targets y `primary` como fallback), igual que stage0, porque el propio
    código de F1 usa `from`/`antiquus` como nombres.
15. **Nombres de helper del lexer.** Todos los helpers de `lexer_state`,
    `lexer_indent` y el `finish`/`match_at` del lexer se renombraron con
    prefijos `lex_*` para evitar colisiones globales con `std.sourcemap`,
    `std.lingua`, `std.json`, `std.builder` y `std.functor` (los símbolos de
    PenguScript son globales por nombre, no por módulo). Es un cambio interno;
    los tokens no cambian. También se eliminaron wrappers de render sin uso en
    `diagnostics.pengu`.

## F2 — AST

### Método

El oráculo [`tools/lark_ast_oracle.py`](../tools/lark_ast_oracle.py) parsea
cada archivo con stage0 (`PenguParser.parse`) y con PSC (`psc parse --no-header`)
y compara un dump canónico:

- Nodo: `node.data`.
- Token: `"texto"` escapado; CRLF normalizado en el dump.
- `None` de Lark: `_`.
- Loop etiquetado: `for_in_stmt @label "..."`.
- Sin posiciones (los spans se prueban con tokens/fixtures).

```text
files=205 exact=204 allowed=1 diverged=0
```

El corpus incluye `std/` (49), `tests/` (126) y `psc/src/` (30 con los módulos
nuevos de F2). El allowlist está en
[`tools/ast_allowlist.txt`](../tools/ast_allowlist.txt).

### Divergencias de AST

1. **`std/compressus.pengu` (allowlist).** Stage0 aplica
   `_expand_short_struct_inits` sobre `calling _le32 with data, at` dentro de un
   struct-init y transforma `at` en `named_arg`. PSC parsea el `pos_arg`
   correcto. La semántica es la misma (el nombre coincide con el parámetro),
   pero el árbol difiere. No se emula el bug.
2. **`parse_expr("with a, b")`.** Stage0 no expande el struct-init corto en
   `parse_expr`; PSC sí. Es una mejora deliberada; no afecta al parseo de
   archivos.
3. **Posiciones.** El dump no incluye posiciones para evitar el ruido de los
   tokens sintéticos de stage0. Los spans se validan con F1 y fixtures propios.

## F2 — Errores

### Método

`tools/lark_parse_error_oracle.py` compara aceptación/rechazo y línea/columna
del primer error para 15 casos. No compara el texto: PSC tiene mensajes/help
propios, pero mantiene `E0000` y la posición de stage0.

```text
cases=15 accept_ok=15 pos_ok=14 allowed=1 failures=0
```

### Divergencias de errores

1. **`unexpected_eof` (allowlist).** F1 emite `E0000` “unclosed '('” en el `(`
   antes de que el parser llegue al final de línea; stage0 no valida el
   delimitador y falla en la nueva línea. Mismo código, distinta posición del
   primer diagnóstico. Es una mejora de recuperación de F1.

## Lo que no se relaja

- Los lexemas de tokens significativos deben coincidir.
- La secuencia y el ancho de `NEWLINE`/`INDENT`/`DEDENT` deben coincidir en F1.
- El AST de archivos válidos debe coincidir (salvo allowlist justificada).
- El primer error de sintaxis debe tener `E0000` y la misma línea/columna en el
  catálogo (salvo allowlist justificada).
- Los literales decodificados deben coincidir con `_decode_literal`.

## F3 — Semántica

### Método

F3 no replica `PenguChecker` línea a línea. La paridad se mide en tres niveles:

1. **Aceptación de corpus.** `psc check` debe aceptar todo programa válido de
   `std/`, `tests/` y `psc/src/`. El gate es
   `tests/psc/test_f3_acceptance.py` y la pasada completa con
   `PSC_F3_FULL=1`.
2. **Códigos y spans.** Los fixtures propios cubren `E0004`, `E0005`, `E0006`,
   `E0013`, `E0020` y `E0022`. La posición es la del nodo AST/byte span, igual
   que F1/F2.
3. **Contrato F4.** `SemaAnnotations` expone `type`, `symbol`, `aux` y flags por
   id de nodo; los tests comprueban que la anotación existe tras `check_text`.

### Resultado medido

```text
F3 corpus: 226 archivos (std + tests + psc/src), bad=0
F3 pytest: 17 passed (smokes, corpus curado, CLI/JSON, códigos)
F3 smoke:  types=25, api ok, collect errors=1, flag ok
```

### Divergencias conocidas y política

- **Registro global de stage0.** PenguScript comparte funciones/consts por
  nombre entre módulos. F3 mantiene el lookup global tras los scopes locales y
  renombró helpers duplicados (`type_child_at`, `scope_define`,
  `symbol_define`, `sema_emit_error`, …) para que el C no colisione.
- **Bindings C `.d.pengu`.** Se cargan como companion y sus `declare` no se
  re-validan por ABI. Stage0 tampoco lo hace; el binding es la autoridad.
- **Tipos de cabecera desconocidos.** Con `include`, un custom type desconocido
  se representa como `opaque` (p. ej. `re_t`, `petitio_response`), que es lo que
  F4 necesita para emitir el tipo C.
- **Métodos `shard T`.** Se guarda un fallback por nombre sólo para receptores
  que son parámetro de tipo. Los receptores concretos (`Vec4`, `f64`) exigen
  coincidencia exacta, para que `get_lerp` de un vector no pise el de `f64`.
- **`when` top-level.** Se evalúa `wasm`/`not wasm`, defines y flags; ramas no
  activas no se recolectan, como stage0.
- **Constructos aún no modelados con precisión total.** `infer` conserva el
  tipo esperado o `any` para no encadenar falsos positivos; el corpus válido
  queda limpio. Cualquier diferencia nueva debe añadir un fixture y un oracle
  antes de tocar esta política.
