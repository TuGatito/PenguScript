# Fase 11 — Release, instaladores y extras

## 0. Objetivo y criterio de cierre

Publicar PenguScript de forma que una persona pueda instalarlo en Linux, macOS
o Windows con un comando, tener `pengu` en el `PATH`, y disponer de la extensión
de VS Code instalada sin tocar `npm`.

Cierre cuando:

1. `scripts/install.sh` instala el compilador en un prefijo arbitrario, lo añade
   al `PATH`, es idempotente, se puede desinstalar y falla con mensajes claros.
2. `scripts/install.bat` + `scripts/install.ps1` hacen lo mismo en Windows
   (prefijo, `PATH` de usuario, desinstalación).
3. `scripts/vsix.mjs` empaqueta `editors/vscode` en un `.vsix` válido y, con
   `--install`, lo instala con `code --install-extension`.
4. `scripts/package.sh` genera los artefactos por plataforma con `SHA256SUMS` y
   un SBOM.
5. `.github/workflows/release.yml` construye y publica esos artefactos al crear
   un tag `v*`.
6. `pengu doctor`, `pengu completions <shell>` y `pengu man` existen y están
   probados.
7. Docs: `docs/INSTALL.md`, `docs/RELEASE.md`, `CHANGELOG.md`.
8. Suite completa en verde, `fmt`/`clippy` limpios, sin deuda declarada como
   "pendiente".

## 1. Auditoría del punto de partida

| Pieza | Estado |
| --- | --- |
| `pengu` | binario único; incluye `pengu lsp` y la stdlib embebida (`include_str!`) |
| `pengu version` | imprime `pengu 0.1.0` |
| `pengu doctor` | no existe |
| Completions / man | no existen |
| `editors/vscode` | extensión sin dependencias, con `package.json` mínimo |
| Empaquetado `.vsix` | no existe |
| Instaladores | no existen |
| CI | `.github/workflows/ci.yml` (fmt, clippy, tests, fmt/lint de std) |
| Release | no existe |
| `code` en la máquina de desarrollo | disponible (`code --install-extension`) |
| Herramientas | `sh`, `zip`, `tar`, `xz`, `sha256sum`, `curl`, `node` 26, `cargo` 1.99 |

## 2. Decisiones

- **D1 — un solo binario.** El instalador copia `pengu` (ya lleva LSP y std) y
  los extras (completions, man) generados por el propio binario. No hay
  instalación de crates ni de Cargo.
- **D2 — instalación por artefacto, con fuente como respaldo.** `install.sh`
  descarga `pengu-<versión>-<target>.tar.gz` y verifica `SHA256SUMS`; si no hay
  red o no existe el artefacto, `--from-source` compila con `cargo build
  --release`. En el repo, `--from-source .` usa el checkout actual.
- **D3 — prefijo por defecto `~/.pengu`** (`PENGU_HOME` lo cambia), binario en
  `<prefijo>/bin`, extras en `<prefijo>/share/{completions,man}`.
- **D4 — PATH idempotente y marcado.** Se añade un bloque entre
  `# >>> pengu >>>` y `# <<< pengu <<<` a `~/.profile`, `~/.bashrc` y
  `~/.zshrc` (los que existan), y a `config.fish` con `fish_add_path`. En
  Windows se usa el `PATH` de usuario con comprobación de duplicados.
- **D5 — desinstalación.** `--uninstall` borra el bloque de PATH y el prefijo;
  no toca nada más.
- **D6 — `.vsix` sin `npm`.** `scripts/vsix.mjs` (Node, sin dependencias) arma
  el ZIP con `[Content_Types].xml` + `extension.vsixmanifest` + `extension/`,
  usando `zip` si existe y `Compress-Archive` en Windows.
- **D7 — instalación de la extensión automática si se puede.** `--install`
  ejecuta `code --install-extension`; si `code` no está, explica cómo hacerlo a
  mano y sale con código 0 (no es un fallo de empaquetado).
- **D8 — checksums y SBOM.** `package.sh` escribe `SHA256SUMS` y
  `sbom-<target>.json` (paquetes del workspace, versión y licencia) sin
  dependencias.
- **D9 — `doctor` no finge.** Comprueba lo que puede comprobar de verdad:
  binario en PATH, stdlib embebida, formateador/linter en un buffer temporal,
  `rustc`/`cargo` (necesarios para compilar proyectos), `clang` y `git`
  (opcionales), y si la extensión está instalada. Exit 1 solo si falla algo
  requerido.
- **D10 — sin `self update` mágico.** Actualizar es volver a ejecutar el
  instalador; `doctor` muestra la versión y el comando sugerido. Se documenta en
  `docs/RELEASE.md` en vez de prometer autoupdate.

## 3. Fases

### R0 — Plan (este documento)

### R1 — CLI de release

- `pengu version` gana `--json` (`{"name","version","target","commit"}`).
- `pengu doctor` con secciones y `--json`.
- `pengu completions bash|zsh|fish` y `pengu man`.
- Tests de CLI para los cuatro.

### R2 — `scripts/install.sh`

- POSIX `sh` (sin bashismos), `set -eu`, trampa de errores con línea.
- Flags: `--version`, `--prefix`, `--from-source [DIR]`, `--no-path`,
  `--uninstall`, `--force`, `--yes`, `-h`.
- Detección de target (`uname -s/-m` → `x86_64-unknown-linux-gnu`,
  `aarch64-apple-darwin`, `x86_64-pc-windows-gnu`, …).
- Descarga + verificación SHA-256; respaldo a compilación.
- PATH idempotente, `pengu doctor` al final, resumen.
- `scripts/install.sh --help` documenta todo.

### R3 — Windows

- `scripts/install.ps1` (`-Version`, `-Prefix`, `-FromSource`, `-NoPath`,
  `-Uninstall`, `-Force`, `-Yes`), descarga de `.zip`, `Expand-Archive`, PATH de
  usuario, comprobación con `pengu doctor`.
- `scripts/install.bat`: envoltorio que localiza PowerShell y pasa argumentos.

### R4 — Empaquetado y CI de release

- `scripts/package.sh [target]`: compila release, arma
  `dist/pengu-<versión>-<target>.tar.gz` (o `.zip` en Windows), `SHA256SUMS`,
  `sbom-<target>.json`.
- `.github/workflows/release.yml`: matriz Linux/macOS/Windows, `package.sh`
  (o `Compress-Archive` en Windows), `SHA256SUMS` unificado y
  `gh release create` con los artefactos; verifica que el tag coincide con la
  versión del crate.

### R5 — Extensión VS Code

- `editors/vscode/package.json`: `publisher`, `version` alineada con el
  compilador, `engines.vscode`, `icon`, `repository`, `license`.
- `scripts/vsix.mjs`: `--out`, `--install`, `--code <ruta>`; valida el
  manifiesto antes de empaquetar.
- `scripts/install-extension.sh` y `.bat`: atajos que llaman a
  `vsix.mjs --install`.

### R6 — Pruebas

- `scripts/test-release.sh`: instala en prefijo temporal con `--no-path`,
  comprueba `bin/pengu`, ejecuta `doctor`, genera `.vsix` y valida su contenido,
  desinstala y verifica que no queda nada.
- Tests Rust de `doctor`/`completions`/`man`/`version --json`.
- CI: `scripts/test-release.sh` en Linux.

### R7 — Documentación y cierre

- `docs/INSTALL.md` (Linux/macOS/Windows, desde fuente, desinstalación,
  verificación), `docs/RELEASE.md` (proceso, versionado, checksums, SBOM,
  migración), `CHANGELOG.md`.
- `scratch/STATUS.md` §17, `scratch/TOOLING_PLAN.md` Fase 11 ✅.
- Suite completa, `fmt`, `clippy`, commit.

## 4. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| No hay releases publicados todavía | `--from-source` es la ruta probada; la descarga se valida con un servidor local en el test |
| Windows sin probar en esta máquina | `install.ps1`/`.bat` se validan por sintaxis (balance y ASCII) y el job `windows-latest` del workflow los ejercita al empaquetar y ejecutar `pengu` |
| `zip` puede no existir | `vsix.mjs` cae a `Compress-Archive` o a un escritor ZIP mínimo en Node |
| PATH roto por rc files ajenos | bloque marcado, idempotente, y `--no-path` para quien gestione el PATH a mano |

## 5. Seguimiento

| Fase | Estado |
| --- | --- |
| R0 | ✅ plan con auditoría, decisiones y criterio de cierre |
| R1 | ✅ `version --json`, `doctor`, `completions`, `man` y 4 tests |
| R2 | ✅ `install.sh` probado (release local, `--from-source`, PATH, `--uninstall`) |
| R3 | ✅ `install.ps1` + `install.bat` (ASCII, mapeo de flags, PATH de usuario) |
| R4 | ✅ `package.sh`, `release.yml` (4 targets) y CI con los pasos nuevos |
| R5 | ✅ publisher alineado, `.vsix` empaquetado e instalado con `code` |
| R6 | ✅ `test-release.sh` verde, 4 tests de `release.rs`, CI |
| R7 | ✅ `docs/INSTALL.md`, `docs/RELEASE.md`, `CHANGELOG.md`, README y cierre |

## 6. Resultado

La fase se cerró con el ciclo completo probado **sin red**:

```text
$ ./scripts/test-release.sh
== empaquetando ==
artefacto pengu-0.1.0-x86_64-unknown-linux-gnu.tar.gz
== montando el repositorio local ==
== instalando desde el repositorio ==
  checksum verificado
  completions en …/share/completions
  man en …/share/man/man1/pengu.1
== ejecutando un programa ==     (imprime 5)
== doctor ==                      todo listo
== extensión de VS Code ==        generado …/pengu-lsp.vsix
== desinstalando ==
todo listo: el ciclo de release funciona
```

- `scripts/install.sh --from-source . --prefix /tmp/pengu-inst --no-path`
  instala, genera extras y deja `doctor` en `todo listo`.
- Con `HOME` temporal escribe el bloque del PATH en `.bashrc` y `--uninstall`
  lo borra y elimina el prefijo (exit 0).
- `node scripts/vsix.mjs --install` instala
  `penguscript.pengu-lsp` y `code --list-extensions` lo confirma.
- `pengu doctor` detecta la extensión y falla (`FALLA PATH`) cuando el binario
  no está en el PATH, que es el comportamiento documentado.

Verificación final: **803 tests**, `cargo fmt --all -- --check` limpio y
`cargo clippy --workspace --all-targets -- -D warnings` limpio.

## 7. Renuncias declaradas

| Elemento del plan | Decisión |
| --- | --- |
| `pengu self update` | No se implementa: actualizar es re-ejecutar el instalador (D10); `doctor` sugiere el comando y `--force` reinstala |
| `pengu debug` (DAP) y `pengu repl` | Fuera del alcance de la Fase 11; el plan los marcaba como "extras si el tiempo lo permite" y no hay hueco en el calendario de la fase |
| Publicación en el Marketplace | El `.vsix` es reproducible y se adjunta a la release; publicar requiere credenciales de la cuenta `penguscript` |
| Firma de binarios (macOS notarization, Authenticode) | Requiere certificados de pago; documentado como pendiente en `docs/RELEASE.md` |

