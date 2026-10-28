# PSC — Fases 1–3: lexer, parser, AST y análisis semántico

Implementación en PenguScript del front-end de PSC, la segunda implementación
del compilador descrita en
the repository root.

## Estado actual

- **F1 — Source, diagnósticos y lexer.**
  - `SourceFile`: BOM, CRLF, índice de líneas, offsets de byte y SHA-256.
  - `Token` zero-copy y tablas laterales para strings, chars y `antiquus`.
  - Lexer iterativo: keywords, identificadores, números, strings/raw/triples,
    chars, comentarios/doc blocks, `antiquus` y operadores.
  - Post-lexer de indentación compatible con el `Indenter` de Lark.
  - Plegado de cadenas multilínea (`.`/`->`) compatible con stage0.
  - `DiagnosticBag` con `E0000`, `E0059` y `W0005`, render plain/ANSI/JSON.
  - CLI `psc lex`.
- **F2 — Parser, AST y recuperación.**
  - AST plano por índices (`PsAst`/`PsNode`), fiel a stage0.
  - Parser recursive descent de toda la gramática: declaraciones, statements,
    expresiones con precedencia, tipos, patrones, `judge`, `with`, `do`,
    `or`, `lambda`, `antiquus`, struct-init corto y cadenas multilínea.
  - Recuperación con panic mode, tope de errores y progreso garantizado.
  - Límite de profundidad de 512 con pre-scan de delimitadores.
  - Diagnósticos `E0000` con mensaje/help/note específicos.
  - CLI `psc parse` / `psc ast` y AST dump canónico.
  - API de interpolación bajo demanda.
- **F3 — Símbolos, tipos, checker e inferencia.**
  - `SemaType` POD internado, nominales (runa/echo/omen/alias/seal/concept),
    firmas, campos, variantes y compatibilidad/casts.
  - `SemaSymbol`/`SemaScope`, builtins, métodos, `@mutates` (`get_*`), concepts y
    genéricos `shard`.
  - Descubrimiento de módulos, imports cualificados, bindings C `.d.pengu` y
    compilación condicional `when wasm`.
  - Checker de declaraciones y cuerpos; inferencia de expresiones, `judge`,
    lambdas, `with`, `do`, contenedores, `maybe`/`result` y métodos nativos.
  - `SemaAnnotations` por nodo para F4; diagnósticos `E0004`–`E0022`.
  - CLI `psc check` (stdin, JSON, límites) y API `check_file`/`check_text`.
- **F4 — codegen C (completo).**
  - `psc emit-c`: bundle C11 con ABI pin, entry wrapper y `#line`.
  - Tipos/runas/ecos/omens/alias, funciones, `declare` y `antiquus`.
  - Expresiones y control básicos, struct init, campos, interpolación simple
    de identificadores y DCE conservadora de std.
  - Tests `tests/psc/test_f4_acceptance.py`; plan en
    [`docs/CODEGEN.md`](docs/CODEGEN.md); arquitectura y matriz de pruebas en
    [`docs/CODEGEN.md`](docs/CODEGEN.md).
  - Pendiente: métodos/genéricos, ownership (`defer`/`banish`), contenedores,
    `judge`/`with`/`or`, `--test`, DCE exacta y matriz completa de C.

Resultados medidos en este árbol:

| Gate | Resultado |
|---|---|
| Suite `tests/psc` F1/F2 con `PSC_PARITY=1` | 12 passed (5 F1 + 7 F2) |
| Suite `tests/psc/test_f3_acceptance.py` | 17 passed |
| Corpus F3 (`std`, `tests`, `psc/src`) | 225 válidos aceptados + 1 negativo (`coherence_conflict`) rechazado |
| Oráculo semántico F3 (193 casos) | 0 válidos rechazados, 0 negativos aceptados, 53/53 códigos |
| ASan/UBSan F3 | limpio en `main`, `oracle`, `petitio`, `cipher`, `arithmancy` y fixtures `judge` |
| Benchmark F3 Release | 2 000 funciones / 262 890 B en 78 ms (~25 600 funcs/s) |
| Oracle de tokens F1 | `files=175 failures=0` |
| Corpus F2 | 205 archivos, `bad=0` |
| Oráculo AST F2 | `exact=204 allowed=1 diverged=0` |
| Oráculo de errores F2 | 15 casos, 14 exactos + 1 allowlist |
| ASan/UBSan F2 | 205 archivos limpios |
| Fuzz parser | 1 000 000 de entradas sin crashes |
| Benchmark parser Release | ~13,3 MB/s, 680 002 nodos para 2,53 MB |

El allowlist de AST contiene solo `std/compressus.pengu`: stage0 aplica su
`_expand_short_struct_inits` sobre un struct-init y convierte un `pos_arg` en
`named_arg`. PSC parsea el árbol correcto; la semántica es la misma. El
allowlist de errores contiene `unexpected_eof`: F1 emite antes el `E0000` de un
`(` sin cerrar.

## Requisitos

El `pengu` instalado puede ser un binario congelado y no incluir los cambios
locales del compilador. Para desarrollar PSC usa el checkout:

```bash
cd psc
../.venv/bin/python ../pengu_project.py build
```

El binario se escribe en `psc/build/psc`.

## Uso

```bash
# Lexer: dump TSV de tokens
./build/psc lex ../tests/conformance/compliance/arena_ast.pengu

# Parser: dump AST
./build/psc parse src/main.pengu

# Alias
./build/psc ast src/main.pengu

# Solo diagnósticos de parseo
./build/psc parse --check src/main.pengu

# Chequeo semántico (F3)
./build/psc check src/main.pengu
./build/psc check --diagnostics=json --stdin < programa.pengu
./build/psc check --max-errors=10 ../std/atlas.pengu

# Sin cabecera (oráculos)
./build/psc parse --no-header tests/fixtures/basic.pengu

# Desde stdin
printf 'weave main into int:\n    return 0\n' | ./build/psc parse --stdin

# Diagnósticos JSON (LSP)
./build/psc parse --check --diagnostics=json \
    tests/fixtures/parser_bad_multi.pengu

# Versión
./build/psc version
```

Exit codes: `0` sin errores, `1` con diagnósticos de error, `2` uso o E/S. Los
warnings (`W0005`) no cambian el exit code.

## Tests

```bash
cd psc

# F1: unitarios y corpus
../.venv/bin/python ../pengu_project.py run tests/lexer_unit.pengu --no-cache
../.venv/bin/python ../pengu_project.py run tests/lexer_corpus.pengu --no-cache

# F2: unitarios y corpus
../.venv/bin/python ../pengu_project.py run tests/parser_unit.pengu --no-cache
../.venv/bin/python ../pengu_project.py run tests/parser_corpus.pengu --no-cache

# Golden F1 y F2
../.venv/bin/python tools/run_f1_checks.py
../.venv/bin/python tools/run_f2_checks.py

# Actualizar golden (revisar el diff antes de aceptar)
../.venv/bin/python tools/run_f1_checks.py --update-golden
../.venv/bin/python tools/run_f2_checks.py --update-golden

# F3: benchmark
../.venv/bin/python ../pengu_project.py run tests/bench_sema.pengu \
    --no-cache --profile release

# F3: smokes y corpus
../.venv/bin/python ../pengu_project.py run tests/sema_smoke.pengu --no-cache
../.venv/bin/python ../pengu_project.py run tests/sema_api_smoke.pengu --no-cache
../.venv/bin/python ../pengu_project.py run tests/sema_check_smoke.pengu --no-cache
(cd .. && .venv/bin/python -m pytest -q tests/psc/test_f3_acceptance.py)
# Oráculo semántico stage0 (opcional)
(cd .. && PSC_SEMA_ORACLE=1 .venv/bin/python -m pytest -q \
    tests/psc/test_f3_acceptance.py -k stage0_semantic)

# Fuzz del parser (10 000 por defecto)
../.venv/bin/python ../pengu_project.py run tests/fuzz_parse.pengu --no-cache -- 1000000

# Benchmark del parser
../.venv/bin/python ../pengu_project.py run tests/bench_parse.pengu \
    --no-cache --profile release
```

## Paridad con stage0

```bash
# Tokens F1
../.venv/bin/python psc/tools/lark_token_oracle.py --psc psc/build/psc \
    --root std tests

# AST F2
../.venv/bin/python psc/tools/lark_ast_oracle.py --psc psc/build/psc \
    --root std tests psc/src
# -> files=205 exact=204 allowed=1 diverged=0

# Errores F2
../.venv/bin/python psc/tools/lark_parse_error_oracle.py --psc psc/build/psc
# -> cases=15 accept_ok=15 pos_ok=14 allowed=1 failures=0
```

Detalles y divergencias en [`docs/PARITY.md`](docs/PARITY.md).

## Fuzz y sanitizers

```bash
# Fuzz nativo determinista
../.venv/bin/python ../pengu_project.py run tests/fuzz_parse.pengu \
    --no-cache -- 1000000

# Build con ASan/UBSan y pasada por el corpus
PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -g" \
PENGU_LDFLAGS="-fsanitize=address,undefined" \
../.venv/bin/python ../pengu_project.py build
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 ./build/psc parse --quiet --check \
    ../tests/conformance/compliance/arena_ast.pengu
```

## Estructura

```text
psc/src/main.pengu                  CLI (lex, parse, ast, version)
psc/src/psc/source.pengu            SourceFile, LineIndex, SHA-256
psc/src/psc/token.pengu             Token, KeywordTable
psc/src/psc/lexer*.pengu            lexer, strings, decode, comments, antiquus, indent
psc/src/psc/diagnostics.pengu       LexIssue y render
psc/src/psc/session.pengu           Session
psc/src/psc/token_dump.pengu        dump TSV de tokens
psc/src/psc/ast/kind.pengu          NodeKind + nombres
psc/src/psc/ast/node.pengu          PsNode, PsAst, codificación de hijos
psc/src/psc/ast/dump.pengu          AST dump canónico
psc/src/psc/parse/state.pengu       PsParser, cursor, errores, profundidad
psc/src/psc/parse/diagnostics.pengu ParseIssue + mensajes/help/note
psc/src/psc/parse/types.pengu       tipos
psc/src/psc/parse/expr/atoms.pengu  átomos y contenedores
psc/src/psc/parse/expr/calls.pengu  unarios, calling, postfix
psc/src/psc/parse/expr/util.pengu   helpers de nodos/spans
psc/src/psc/parse/expr/ops.pengu    precedencia y entrada de expresiones
psc/src/psc/parse/stmt/core.pengu   statements y bloques
psc/src/psc/parse/stmt/values.pengu hooks de constructos con valor
psc/src/psc/parse/patterns/core.pengu patrones de judge/when
psc/src/psc/parse/patterns/judge.pengu judge/judge over
psc/src/psc/parse/decl/core.pengu   declaraciones top-level
psc/src/psc/parse/api.pengu         API pública e interpolación
psc/src/psc/sema/names.pengu        NamePool
psc/src/psc/sema/types/             kind, table, canonical, compat, convert
psc/src/psc/sema/symbols/           symbol, scope, table
psc/src/psc/sema/modules/           loader, resolver, program
psc/src/psc/sema/check/             collect, body
psc/src/psc/sema/infer/core.pengu   inferencia de expresiones
psc/src/psc/sema/api.pengu          check_file/check_text
psc/src/psc/sema/state.pengu        SemaState y hooks
psc/src/psc/sema/annotate.pengu     SemaAnnotations (F4)
psc/tests/                           tests .pengu, fixtures y golden
psc/tools/                           oráculos/golden (dev-only)
```

## Documentación

- [`docs/CODEGEN.md`](docs/CODEGEN.md): codegen C F4 completo (arquitectura, estado y pruebas).
- [`docs/SEMA.md`](docs/SEMA.md): pipeline semántico, tipos, símbolos y checker.
- [`docs/TYPES.md`](docs/TYPES.md): modelo de tipos, interning y compatibilidad.
- [`docs/MODULES.md`](docs/MODULES.md): imports, bindings C y `when`.
- [`docs/SEMA_ERRORS.md`](docs/SEMA_ERRORS.md): códigos y formato.
- [`docs/AST.md`](docs/AST.md): modelo del AST, codificación, nodos y rarezas.
- [`docs/PARITY.md`](docs/PARITY.md): cómo se compara con stage0 y qué difiere.
- [`docs/OWNERSHIP.md`](docs/OWNERSHIP.md): quién libera cada recurso.
- [`../PLAN_F2_PARSER.md`](../PLAN_F2_PARSER.md): plan aprobado de F2 y estado.
- [`../PLAN_F3_SEMA.md`](../PLAN_F3_SEMA.md): plan aprobado de F3 y estado.
