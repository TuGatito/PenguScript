# psc.parse.patterns.judge

> Source: `src/psc/parse/patterns/judge.pengu`

psc/parse/patterns/judge.pengu — `judge` y `judge over`.

Implementa el hook `PsHooks.judge`. Reutiliza los patrones de
`patterns/core.pengu` y el hook `when_body` para los cuerpos.

## Memoria
Construye nodos en el AST.

---

### `ppatj_parse_judge`

> **ppatj_parse_judge**(p: ref to PsParser) -> int

 Parsea `judge expr [: | over NAME :] cláusulas [else -> body]`.

 ## Memoria
 Crea `judge_expr` o `judge_over_expr`.

### `ppatj_parse_else_clause`

> **ppatj_parse_else_clause**(p: ref to PsParser) -> int

 Parsea `else -> body` de un `judge`.

 ## Memoria
 Crea un nodo `else_clause`.

