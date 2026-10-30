# 🖨️ Codegen C (F4)

`psc emit-c` convierte un programa comprobado por F3 en un único `bundle.c`
C11. F4 está cerrado: el emisor cubre la superficie de PSC usada por el
corpus, la stdlib y los 66 fixtures de conformidad.

## Pipeline

```text
psc check (F3)
  └─ SemaProgram (tipos, símbolos, anotaciones)
       │
       ▼
codegen.api.generate_c
  ├─ CgContext
  ├─ CgNames        nombres C estables
  ├─ CgCatalog      funciones y tipos
  ├─ CgReach        reachability (DCE conservadora)
  ├─ CgEmitter      StringBuilder + C escaping
  ├─ expr/stmt      bajada usando anotaciones F3
  └─ bundle.c
```

## Módulos

| Archivo | Responsabilidad |
|---|---|
| `api.pengu` | `generate_c`, `CgResult` |
| `options.pengu` | `CgOptions`, `CgStats` |
| `context.pengu` | estado, locals, `self` |
| `names.pengu` | nombres C, prefijos, `main` → `pengu_main` |
| `ctype.pengu` | `SemaType` → C |
| `catalog.pengu` | funciones/tipos del programa |
| `decl_types.pengu` | runes, echos, omens, alias |
| `function.pengu` | firmas/cuerpos |
| `expr.pengu` | expresiones |
| `stmt.pengu` | statements y control |
| `origin.pengu` | `#line` |
| `bundle.pengu` | secciones, ABI, entry |
| `dce.pengu` | reachability conservadora |
| `antiquus.pengu` | bloques C crudos |
| `emit.pengu` | escritor C |

## Estado actual (F4 cerrado)

- **P1:** build de PSC ~25–30 s y <4 GB.
- **P2:** métodos/ritual, receptores por valor y por referencia, constructores,
  `self` y métodos sobre campos.
- **P3.1:** `defer`/`banish`, orden correcto respecto a `return`, cleanups
  derivados y `std.arena` sin fugas.
- **P3.2:** funciones genéricas explícitas (`of T`) e inferidas; métodos,
  shards y tipos genéricos usados por la stdlib.
- **P3.3:** listas/mapas, literales, slices de string/array/lista, `judge`
  como expresión y statement, `with:`/`is:`, `or else`, lambdas sin captura,
  `@mutates`, `chr`/`ord`, interpolación completa y strings UTF-8.
- **P3.4:** `--test` integrado, `--strict-c99`, DCE por alcance de usuario,
  `--prune-types`, includes sólo de módulos vivos y matriz gcc/clang;
  `--prune-native` es no-op porque F4 no enlaza binarios (F5 sí).
- **P4:** constantes de módulo y su emisión C.
- **P4.1 (0.17.2):** `@mutates` con asignación y `get_*` puro, `transmute`,
  `for … from … to … [step]`, `judge` expresión con tipo esperado, `append`,
  `.length`, resolución de imports/homónimos y dispatch por receptor.
- **P4.2 (0.17.3):** `compound_set_stmt`, `simple_stmt`, `with target:`,
  `unsafe:`, `errdefer`, retorno implícito, interpolación con expresiones
  arbitrarias, comprehensiones, `in`/`not in`, `type of`, `donum`, `or return`,
  `try`, `or:`, bounds checks y cero de mapas ausentes. El detalle y la
  auditoría están en `AUDITORIA_0.17.3.md`.
- **Conformidad:** **66/66** fixtures con las librerías nativas.
- **Calidad:** 17 casos de aceptación F4, ASan/UBSan, golden C normalizado y
  benchmark de emisión.

La matriz MSVC/TCC pertenece al pipeline de F5 (enlazado y toolchains); F4
emite C11 portable y valida strict C99 con gcc y clang.

Implementado y probado:

- `main`/`pengu_main`, entry wrapper, ABI pin.
- funciones/prototipos, `declare`, `antiquus`, métodos y `ritual`.
- runes, echos, omens, alias/sellos, tuplas, struct/omen init y campos.
- `var`/`let`, `set`, `return`, `if`/`unless`, `while`, `for`, `break`,
  `continue`, `defer`/`banish`, `judge`, `with`, `or else`.
- literales básicos, aritmética, comparaciones, llamadas directas,
  interpolación completa, lambdas y `entry/test`.
- visibilidad con DCE conservadora/exacta por alcance y tipos.
- `#line`, `--no-line-markers`, `--strict-c99`, `--test`, `--prune-types`.
- tests `tests/psc/test_f4_acceptance.py`, golden C y benchmark.

## Memoria

- `SemaProgram` es prestado; F4 no lo libera.
- `CgResult.bundle` es owned; `free_result` lo libera.
- `CgContext` libera nombres, catálogo, emisor y locales con `context_free`.
- Los strings temporales se liberan con `defer banish` y nunca se devuelven
  después de liberarlos (bug corregido en el primer smoke).

## Cómo probar

```bash
cd psc
../.venv/bin/python ../pengu_project.py build
../.venv/bin/python -m pytest -q ../tests/psc/test_f4_acceptance.py
```

Si el compilador C o `libpengu_runtime.a` no están disponibles, los casos de
ejecución se saltan; la emisión y las comprobaciones de texto siguen
ejecutándose.
