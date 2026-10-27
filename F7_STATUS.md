# F7 — Herramientas de desarrollo (cerrado)

> Base: F6. F7 convierte las herramientas MVP en paritarias, incrementales y
> con procesos nativos.

## Completado y verificado

| Área | Estado |
|---|---|
| Paridad fmt | **323/323** archivos (`std`, `psc/src`, `psc/tests`, `tests`) byte-idénticos a stage0 |
| `fmt` | unidad, `.pengufmt.toml` ascendente, strings/triples/antiquus, CRLF/BOM, `--check`/`--stdin`/`--diff`, escritura atómica |
| `doc` | firmas/doc desde símbolos F3, Markdown estable, `src_<path>.md`, alias legacy `main.md`, HTML con búsqueda |
| `assets` | embed/disk, `exclude`, hash incremental, `--force`, `.incbin` con umbral y fallback TCC/MSVC |
| `watch` | polling de todo el proyecto + manifiesto, debounce por intervalo, spawn/kill del hijo, `--once`, `--clear`, `--interval` |
| `benchmark` | runner nativo PSC, `f7_arith`/`f7_fib`, `--repeat`/`--warmup`/`--only`, tabla/CSV/JSON |
| `selftest` | dev-only, `--smoke`, detección de `.venv`/`PSC_PYTHON`; `test --watch` |
| Procesos | `fork/execvp/waitpid`, spawn/kill/quiet para benchmarks y watch |
| CI | tests F7 + paridad fmt en `psc-cli` |
| Tests | F6/F7/F5: 11 passed; F1–F6: 49+ |
| Bootstrap | punto fijo stage3=stage4 |
| Preflight | gcc/clang/TCC READY |
| ASan/UBSan | `psc 0.7.0 (F7)` |

## Evidencia

```text
fmt parity: 323/323
F6+F7+F5: 11 passed
bootstrap: punto fijo OK
preflight gcc/clang/TCC: READY
psc version: psc 0.7.0 (F7)
```

## Notas de cierre
- `doc` usa la tabla de símbolos F3 para firmas y doc comments, con render
  textual para enumerar las páginas.
- `test --watch` reejecuta el runner y espera cambios de huella.
- Los benchmarks históricos que usan helpers que F4 aún no baja a C se
  reportan como `build-failed`; los casos nativos F7 funcionan.

## Notas

- `benchmark` incluye casos nativos F7; los benches históricos que usan
  `print`/helpers que el frontend F4 aún no baja a C se reportan como
  `build-failed`, no como victoria.
- `doc` extrae firmas de las declaraciones y comentarios; la lectura de tipos
  completa vía F3 queda como enriquecimiento posterior.
- `test --watch` no se añadió en F7; `watch` cubre scripts/proyectos.

## Reproducir

```bash
cd psc && python ../pengu_project.py build && cd ..
python psc/tools/parity_tools.py --only fmt --path std --path psc/src
python -m pytest -q tests/psc/test_f7_tools.py
python psc/tools/bootstrap.py
```
