# Catálogo de diagnósticos

Generado por `tools/docs/check_codes.py --write`; no editar a mano.

Formato de un diagnóstico:

```text
error[E0005]: type mismatch: expected 'int', got 'string'
  --> src/main.pengu:7:13
   |
   = help: Ensure the value type matches the expected type.
```

Los códigos `E****` son errores; `W****`, advertencias. La columna
*emisores* cuenta las referencias a la constante en `src/psc` (sin contar
las declaraciones); *§18* indica si el código está en la tabla de
`docs/LANGUAGE.md`. Un código sin emisor es una promesa: o se implementa
en una fase del plan, o se elimina de la documentación.

| Código | Constante | Emisores | Estado | §18 |
| --- | --- | ---: | --- | --- |
| `E0000` | `CODE_SYNTAX`, `PSC_E_SYNTAX`, `PSC_E_LEX` | 2 | emitido | sí |
| `E0001` | `CODE_CONST_IN_WEAVE` | 0 | **sin emisor** | sí |
| `E0002` | `CODE_VAR_TOP_LEVEL` | 1 | emitido | sí |
| `E0003` | `CODE_SELF_DOT` | 1 | emitido | sí |
| `E0004` | `CODE_UNDEFINED` | 15 | emitido | sí |
| `E0005` | `CODE_TYPE_MISMATCH` | 43 | emitido | sí |
| `E0006` | `CODE_MUTABILITY` | 5 | emitido | sí |
| `E0007` | `CODE_CONTROL_FLOW` | 2 | emitido | sí |
| `E0008` | `CODE_MEMORY_OP` | 15 | emitido | sí |
| `E0014` | `CODE_BUILDER` | 0 | **sin emisor** | sí |
| `E0015` | `CODE_ARRAY_UNKNOWN` | 1 | emitido | sí |
| `E0019` | `CODE_INTERP_PARSE` | 3 | emitido | sí |
| `E0020` | `CODE_RETURN_TYPE` | 1 | emitido | sí |
| `E0021` | `CODE_GENERIC_ARGS` | 1 | emitido | sí |
| `E0022` | `CODE_TYPE_PARAM_OUTSIDE` | 0 | **sin emisor** | sí |
| `E0023` | `CODE_MANY_MULTIPLE` | 1 | emitido | sí |
| `E0024` | `CODE_MANY_NOT_LAST` | 1 | emitido | sí |
| `E0026` | `CODE_MULTIPLE_INSIGNIA` | 1 | emitido | sí |
| `E0027` | `CODE_OMEN_DUP` | 1 | emitido | sí |
| `E0028` | `CODE_OMEN_PAYLOAD_VALUE` | 0 | **sin emisor** | sí |
| `E0029` | `CODE_OMEN_CONST` | 1 | emitido | sí |
| `E0030` | `CODE_CONCEPT_SIG` | 0 | **sin emisor** | sí |
| `E0031` | `CODE_CONCEPT_MISSING` | 0 | **sin emisor** | sí |
| `E0032` | `CODE_CONCEPT_BOUND` | 1 | emitido | sí |
| `E0033` | `CODE_RITUAL_SELF` | 0 | **sin emisor** | sí |
| `E0034` | `CODE_RITUAL_CALL` | 0 | **sin emisor** | sí |
| `E0035` | `CODE_C_NAME` | 0 | **sin emisor** | sí |
| `E0036` | `CODE_C_NAME_KIND` | 0 | **sin emisor** | sí |
| `E0037` | `CODE_C_NAME_DUP` | 1 | emitido | sí |
| `E0038` | `CODE_C_NAME_RESERVED` | 0 | **sin emisor** | sí |
| `E0039` | `CODE_C_NAME_FIELD` | 1 | emitido | sí |
| `E0041` | `CODE_ARRAY_SIZE` | 0 | **sin emisor** | sí |
| `E0042` | `CODE_RANGE` | 0 | **sin emisor** | sí |
| `E0043` | `CODE_PRIVATE` | 0 | **sin emisor** | sí |
| `E0044` | `CODE_JUDGE_EXHAUSTIVE` | 1 | emitido | sí |
| `E0047` | `CODE_PRIMITIVE_METHOD` | 1 | emitido | sí |
| `E0049` | `CODE_CONCEPT_OPERATOR` | 2 | emitido | sí |
| `E0050` | `CODE_INFINITE_SIZE` | 0 | **sin emisor** | sí |
| `E0051` | `CODE_DANGLING` | 1 | emitido | sí |
| `E0052` | `CODE_CONCEPT_DUP` | 0 | **sin emisor** | sí |
| `E0053` | `CODE_CHAIN` | 8 | emitido | sí |
| `E0054` | `CODE_JSON_DERIVE` | 17 | emitido | sí |
| `E0056` | `CODE_ATTRIBUTE` | 2 | emitido | sí |
| `E0057` | `CODE_CHAR_RANGE` | 0 | **sin emisor** | sí |
| `E0059` | `PSC_E_ANTIQUUS` | 1 | emitido | sí |
| `E0063` | `CODE_STATIC_PLACEMENT` | 0 | **sin emisor** | sí |
| `E0064` | `CODE_TEST_NAME` | 0 | **sin emisor** | sí |
| `E0065` | `CODE_C_FIELD_COLLISION` | 0 | **sin emisor** | sí |
| `E0066` | `CODE_MUTATES_EXPR` | 4 | emitido | sí |
| `E0067` | `CODE_MUTATES_ATTR` | 5 | emitido | sí |
| `E0068` | `CODE_MUTATES_GETTER` | 0 | **sin emisor** | sí |
| `E0069` | `CODE_DUP_LABEL` | 1 | emitido | sí |
| `E0070` | `CODE_DUP_TYPE` | 0 | **sin emisor** | sí |
| `E0071` | `CODE_NAMED_ARG` | 5 | emitido | sí |
| `E0072` | `CODE_DEFAULT_ORDER` | 1 | emitido | sí |
| `E0073` | `CODE_DEFAULT_VALUE` | 3 | emitido | sí |
| `E0074` | `CODE_MANY_DEFAULT` | 1 | emitido | sí |
| `E0075` | `CODE_MANY_DECLARE` | 1 | emitido | sí |
| `E0076` | `CODE_MAP_LITERAL_TYPE` | 2 | emitido | sí |
| `E0077` | `CODE_WITH_TARGET` | 1 | emitido | sí |
| `E0079` | `CODE_BIND_COUNT` | 1 | emitido | sí |
| `E0080` | `CODE_USE_AFTER_MOVE` | 1 | emitido | sí |
| `E0081` | `CODE_IMPLICIT_COPY` | 2 | emitido | sí |
| `E0082` | `CODE_RC_CROSS_THREAD` | 2 | emitido | sí |
| `E0083` | `CODE_ARC_NOT_SHARED` | 1 | emitido | sí |
| `E0084` | `CODE_EXPORT_DROP` | 1 | emitido | sí |
| `E0085` | `CODE_EMBED_NOT_RUNE` | 1 | emitido | sí |
| `E0089` | `CODE_EMBED_NAME` | 3 | emitido | sí |
| `W0001` | `WARN_TRANSMUTE` | 0 | **sin emisor** | sí |
| `W0002` | `WARN_ECHO_ACCESS` | 0 | **sin emisor** | sí |
| `W0004` | `WARN_UNREACHABLE` | 0 | **sin emisor** | sí |
| `W0005` | `WARN_SHADOW`, `PSC_W_INDENT` | 1 | emitido | sí |
| `W0006` | `WARN_DEPRECATED` | 0 | **sin emisor** | sí |
| `W0007` | `WARN_UNSAFE` | 0 | **sin emisor** | sí |
| `W0008` | `WARN_COW_LOOP` | 1 | emitido | sí |
| `W0013` | `WARN_RANGE` | 0 | **sin emisor** | sí |

## Cómo agregar un código

1. Declará la constante `CODE_*` en `src/psc/sema/diagnostics.pengu`
   (o `PSC_*` en `src/psc/diagnostics.pengu` para el lexer).
2. Emitilo desde el checker o el codegen; nunca escribas el literal.
3. Agregá la fila en la tabla §18 de `docs/LANGUAGE.md` y su espejo en
   `docs/LANGUAGE.es.md`.
4. Corré `tools/docs/check_codes.py --write` y commiteá el catálogo.
