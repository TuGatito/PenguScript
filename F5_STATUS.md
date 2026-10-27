# F5 — estado de implementación

## Completado y verificado

| Área | Estado |
|---|---|
| F5a self-compile | `psc emit-c psc/src/main.pengu` compila con **gcc, clang y TCC**; `-Wall -Wextra -Werror` con gcc |
| Driver | `psc build`, `psc run`, `psc expand` para archivo y proyecto; `run` propaga el exit code |
| Manifiesto | `pengu.toml` (`project`, `build`, `profiles`) vía `std.toml` |
| Rutas/toolchain | runtime/header/std/std_c; `PENGU_*`; gcc/clang/TCC; `--cc`, `--out`, perfiles |
| Bootstrap | **stage1 → stage2 → stage3 → stage4 con punto fijo**: el C de stage3 y stage4 es byte-idéntico |
| TCC | preflight y driver probados con TCC; obligatorio en el gate Linux |
| Tests | F1–F4 (43 passed), `test_f5_acceptance.py`, `test_f5_bootstrap.py` (`PSC_BOOTSTRAP=1`) |
| ASan/UBSan | smoke de self-compile con `-fsanitize=address,undefined` |
| CI | job `psc-selfhost` (gcc/clang/TCC + driver) y nightly `psc-bootstrap` |
| Docs | `docs/selfhost/BOOTSTRAP.md`, `psc/docs/DRIVER.md` |

## Reproducir

```bash
cd psc
python ../pengu_project.py build          # stage1 con stage0
cd ..
python psc/tools/bootstrap.py            # stage2 → stage3 → stage4; punto fijo
python psc/tools/selfhost_preflight.py --psc psc/build/psc --smoke
python -m pytest -q tests/psc/test_f1_acceptance.py tests/psc/test_f2_acceptance.py \
  tests/psc/test_f3_acceptance.py tests/psc/test_f4_acceptance.py tests/psc/test_f5_acceptance.py
PSC_BOOTSTRAP=1 python -m pytest -q tests/psc/test_f5_bootstrap.py
```

## Notas de implementación

- Interpolación de campos anidados (`a.b.c`, `a->b`) y llaves literales.
- Evaluación de consts en codegen como fallback del bootstrap.
- `defer` comparte scope en bloques `else`; decodificación de escapes en strings.
- Instanciaciones genéricas con nombre único (`_instN`).
- El driver acepta `PENGU_STD_DIR`, `PENGU_LIB_DIR` y `PENGU_INCLUDE_DIR` para
  instalaciones fuera del checkout.
