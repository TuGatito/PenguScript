# F10 — Bind externo y release (cerrado)

> `psc bind` nativo con helper `pengu-bind` congelado, release portable/FHS
> sin Python en destino. Sólo TOML (`release.toml`); nada de YAML/JSON.

## Completado

| Área | Estado |
|---|---|
| `psc bind` | wrapper argv, sin shell |
| Locator | `$PENGU_BIND`, sibling, `libexec/pengu`, `$PENGU_HOME`, `PATH` |
| Contrato | flags de stage0, `--output -`, exit 0/1/2 |
| `pengu-bind` | entry Python + onefile PyInstaller |
| Paridad | `.d.pengu` byte-idéntico a stage0 en `stdio/stdlib/string` |
| No-Python | build y bind con `PATH` sin Python |
| Portable | `bin/psc`, `bin/pengu-bind`, `std/`, `include/`, `lib/`, stubs |
| FHS | `bin/`, `lib/pengu/`, `include/pengu/`, `share/pengu/` |
| `PENGU_HOME` | `psc` encuentra runtime/std/include en el paquete |
| Release | `release.toml`, `SHA256SUMS`, tar.gz/zip |
| Determinismo | tar.gz idéntico entre builds |
| Tests | paridad, locator, release, checksums (4) |
| CI | F10 tests + release Linux |

## Verificación

```text
tests/psc/test_f10_bind.py: 4 passed
F6..F10: 27 passed
release auto-home sin PENGU_HOME: OK
bootstrap: punto fijo OK
release portable + FHS: smoke OK
psc bind dentro del release: SAME que stage0
build sin Python en PATH: OK
```

## Limitaciones conocidas

- `pengu-bind` es un onefile de PyInstaller: incluye CPython dentro; no requiere
  Python instalado. Un parser C nativo sería F10b.
- macOS/Windows tienen pipeline preparado pero no ejecutado en esta sesión.
- No hay firma Authenticode/notarización macOS.
- No hay auto-update ni publicación en gestores de paquetes.
- `psc bind` no aplica timeout propio; el helper puede colgarse en un header
  patológico. Se mitigará con `PENGU_BIND_TIMEOUT` en una ronda posterior.
- `make_release.py` legacy sigue existiendo para stage0; el release F10 usa
  `psc/tools/release.py`.
