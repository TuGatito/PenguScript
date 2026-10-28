# F9 — Dependencias y package manager (cerrado)

> Implementación nativa PSC. Python queda como oráculo dev-only. Sólo
> `pengu.toml`: YAML/JSON se rechazan explícitamente.

## Completado

| Área | Estado |
|---|---|
| `add` | path local y git, `--name/--branch/--tag/--version/--no-build/--rebuild/--trust` |
| `remove` | manifiesto + `lib/<name>` (`--keep-files`) |
| `update` | refresca directas, resuelve y reescribe lock |
| `upgrade` | cambia versión/branch y reinstala |
| Transitivas | BFS, `required_by`/`children`, ciclos por nombre |
| Semver | `^`, `~`, `>=`, `>`, `<=`, `<`, `=`, `*`, tags `vX.Y.Z` |
| Lock | `pengu.lock` v1, commit, SHA-256 de árbol, target |
| `--locked` | verifica sin reescribir |
| `--frozen` | exige lock, restaura `vendor/`, no instala |
| `verify` | lock, presencia, commit y SHA-256 |
| `vendor` | snapshot de todos los paquetes del lock |
| `build.pengu` | `--trust`/`PENGU_TRUST_ALL`, `--force`, cwd de la dependencia |
| Build | `lib/<name>/src` en el resolver; include dirs; lock |
| `tree`/`metadata` | dependencias en JSON y texto |
| TOML-only | `pengu.yaml/yml/json` rechazados |
| Seguridad | nombres validados, sin shell en git, SHA-256 |

## Verificación

```text
tests/psc/test_f9_deps.py: 7 passed
F6+F7+F8+F9: 23 passed
ASan/UBSan: add + build --locked sin errores (detect_leaks=0)
bootstrap: punto fijo OK
```

## Limitaciones conocidas

- No hay registro central: sólo git/path. No hay autenticación interactiva.
- `verify` comprueba commit/SHA, no el `origin` del remoto.
- El target del lock es canónico para Linux x86_64 en esta fase.
- Semver de prerelease usa comparación textual.
- `vendor` copia el árbol completo (incluye `build/` si existe).
- `build.pengu` se ejecuta sólo para dependencias directas; las transitivas no.
- Los tests cubren Linux; Windows/macOS antes de F11.
- **LeakSanitizer** todavía reporta allocaciones retenidas en el comando `add`
  (no hay use-after-free ni doble free). Es deuda de ownership pendiente; no se
  declara “cero leaks”.

## Fuera de alcance

Registro central, publicación, Git LFS/submodules, lockfile v2, firmas GPG.
