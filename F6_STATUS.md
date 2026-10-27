# F6 — estado de implementación

> Base: F5 cerrada con bootstrap en punto fijo.
> Este documento refleja el estado real; no sustituye a `PLAN_F6_CLI.md`.

## Completado y verificado

| Área | Estado |
|---|---|
| Framework CLI | parser compartido (`--flag`, `--flag=value`, `--flag value`, `--`, short flags, `-D` repetible), help por comando, `psc help <cmd>`, flags globales |
| `build` | archivo/proyecto, perfiles, `-D`, `--test`, `--json`, `--out`/`-o`, `--entry`, DCE (`--no-dce`, `--prune-types`, `--prune-native`, `--dce-scope`, `--tree-shake-user`, `--no-line-markers`), `--target` -> F11 |
| Tipos de salida | `exe`, `c`, `obj`, `static` (ar), `shared` |
| C glue/assets | `c/*.c`, `build/*_assets.c`, include dirs de `build/` y `c/` |
| `run` | script/proyecto, `--` args, cache de scripts, exit code real, paths con espacios |
| `check` | archivo y proyecto; el proyecto ya **no** escribe bundle |
| `expand` | bundle-only restaurado |
| Caché | content-addressed para `run` de scripts, `PSC_CACHE_DIR`, `--no-cache`, `--clear-cache`, `--ephemeral`, `gc --all` |
| Proyecto | `init`, `new`, `clean`, `doctor`, `metadata`, `tree` |
| Tests/dev | `test` (runner de proyecto, fallo -> exit 1, `--json` JSONL), `watch`, `eval`, `time`, `benchmark`/`selftest` dev-only |
| Herramientas | `fmt` (unidad detectada, reindentación, `--check`/`--stdin`/`--diff`), `doc` (Markdown), `assets` (embed, list, C/header/interface) |
| Stubs | `add/remove/upgrade/verify/vendor/update` -> F9; `lsp` -> F8; `bind` -> F10 |
| Deuda F5 | paths liberados sin UAF, autodetección desde cwd, `check` puro, versión 0.6.0, quoting de argv |
| Bootstrap | stage1→stage4 con C idéntico; TCC verde |
| Tests | F1–F4 43 passed, F5 2, F6 4 (incluye `test --json`); CI `psc-cli`; ASan/UBSan smoke |

## Evidencia

```text
punto fijo: OK
bootstrap: OK
preflight gcc/clang/TCC: READY
```

## Pendiente para “F6 completo” según el plan

1. **Formatter con paridad stage0 completa** (espaciado `is/as/into`,
   `.pengufmt.toml`; ya detecta unidad, reindenta y muestra diff por línea).
2. **Doc**: búsqueda HTML y extracción de firmas/tipos como `pengu_doc`.
3. **Assets**: `embed=false` (disk), `exclude`, `.incbin` para assets grandes.
4. **Caché de proyectos** (no sólo scripts) y `gc --max-age`.
5. **Multi-file `check`** y `--json` de check completo.
6. **Proceso sin shell**: hoy `psc/os/shell` cita de forma segura, pero sigue
   usando `system()`; falta `posix_spawn`.
7. Endurecer CI/nightly con F6 completo y corpus.

## Reproducir

```bash
cd psc && python ../pengu_project.py build && cd ..
python psc/tools/bootstrap.py
python -m pytest -q tests/psc/test_f6_cli.py tests/psc/test_f5_acceptance.py
```

Los comandos nuevos están documentados en `psc/docs/CLI.md`.
