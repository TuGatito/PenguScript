# F6 — CLI completo (cerrado)

> F6 implementa el CLI completo de PSC sobre F5, con bootstrap estable y TCC.

## Completado y verificado

| Área | Estado |
|---|---|
| Framework CLI | parser compartido (`--flag`, `--flag=value`, `--flag value`, `--`, short flags, `-D` repetible), help por comando, `psc help <cmd>`, flags globales |
| `build` | archivo/proyecto, perfiles, `-D`, `--test`, `--json`, `--out`/`-o`, `--entry`, DCE, `--target` -> F11 |
| Salidas | `exe`, `c`, `obj`, `static` (ar), `shared` |
| C glue/assets | `c/*.c`, `build/*_assets.c`, include dirs de `build/` y `c/` |
| `run` | script/proyecto, `--` args, caché, exit code real, paths con espacios, stdin heredado |
| `check` | archivo y proyecto (puro), multiarchivo |
| `expand` | bundle-only |
| Caché | builds de proyecto y scripts, hash del compilador, `PSC_CACHE_DIR`, `--no-cache`, `--clear-cache`, `--ephemeral`, `gc --all/--max-age` |
| Proyecto | `init`, `new`, `clean`, `doctor`, `metadata`, `tree` |
| Tests/dev | `test` (fallo -> exit 1, `--json`), `watch`, `eval`, `time`, `benchmark`/`selftest` dev-only |
| Herramientas | `fmt` (unidad, `.pengufmt.toml`, reindentación, espaciado, `--check`/`--stdin`/`--diff`), `doc` (Markdown + HTML con búsqueda), `assets` (embed/disk, exclude, list, C/header/interface) |
| Stubs | `add/remove/upgrade/verify/vendor/update` -> F9; `lsp` -> F8; `bind` -> F10; `--target` -> F11 |
| Procesos | argv sin shell (`fork/execvp/waitpid`), stdio heredado |
| Deuda F5 | paths sin UAF, autodetección desde cwd, check puro, versión 0.6.0 |
| Bootstrap | stage1→stage4 con C idéntico; TCC verde |
| Tests | F1–F6: 49 passed, 5 skipped; CI `psc-cli`; ASan/UBSan smoke |

## Evidencia

```text
punto fijo: OK
bootstrap: OK
preflight gcc/clang/TCC: READY
ASan/UBSan: psc 0.6.0 (F6)
psc <cmd> --help: 0 en todos los comandos
```

## Notas

- `benchmark` y `selftest` son dev-only: requieren el checkout y Python; no
  forman parte del build de usuario.
- `--target`/WASM/MSVC, LSP, dependencias y `bind` pertenecen a F8/F9/F10/F11 y
  fallan explícitamente.
- El formatter conserva strings/triples/comentarios y no reinterpreta bloques
  `antiquus`; `--diff` muestra las líneas modificadas.
- Los assets grandes usan arrays C portables; `.incbin` es una optimización
  futura, no una capacidad pendiente.

## Reproducir

```bash
cd psc && python ../pengu_project.py build && cd ..
python psc/tools/bootstrap.py
python -m pytest -q tests/psc/test_f6_cli.py tests/psc/test_f5_acceptance.py
```

El contrato de usuario está en `psc/docs/CLI.md`.
