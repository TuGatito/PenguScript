# Release

Este documento describe cómo se empaqueta y publica PenguScript: qué artefactos
se generan, cómo verificarlos y qué pasos hay que dar para cortar una versión.

## Artefactos

Cada release publica, por plataforma:

| Archivo | Contenido |
|---|---|
| `pengu-<version>-<target>.tar.gz` (Linux/macOS) o `.zip` (Windows) | el binario `pengu`, `VERSION`, `README.md` y `LICENSE` si existe |
| `SHA256SUMS` | suma de todos los archivos comprimidos |
| `VERSION` | la versión, para que los instaladores la consulten sin la API de GitHub |
| `sbom.json` (y `sbom-<target>.json`) | inventario de crates del workspace (formato `pengu-sbom-1`) |
| `penguscript.pengu-lsp-<version>.vsix` | la extensión de VS Code (se puede adjuntar a mano o publicar en el Marketplace) |

Targets:

| Target | Runner |
|---|---|
| `x86_64-unknown-linux-gnu` | `ubuntu-latest` |
| `x86_64-apple-darwin` | `macos-13` |
| `aarch64-apple-darwin` | `macos-14` |
| `x86_64-pc-windows-msvc` | `windows-latest` |

Windows ARM64 no se publica compilado; el instalador de PowerShell compila desde
fuente en ese caso (`-FromSource`).

## Empaquetar a mano

```sh
./scripts/package.sh                       # detecta target y compila en release
./scripts/package.sh --skip-build          # reutiliza target/release/pengu
./scripts/package.sh --version 0.1.0 --target aarch64-apple-darwin --out dist
```

`package.sh` se niega a continuar si faltan `target/release/pengu` (con
`--skip-build`) o si no puede leer la versión del crate. `SHA256SUMS` se ordena
para que dos plataformas produzcan el mismo orden de líneas.

## Extensión de VS Code

```sh
node scripts/vsix.mjs --check      # solo valida el manifiesto
node scripts/vsix.mjs              # escribe dist/penguscript.pengu-lsp-<version>.vsix
node scripts/vsix.mjs --install    # además la instala en el VS Code del sistema
node scripts/vsix.mjs --code /ruta/a/code --install
```

El script compara la versión de `editors/vscode/package.json` con
`pengu version --json` y **falla si no coinciden**: así el `.vsix` nunca se
publica desfasado. No hay `npm install`: el cliente LSP es JavaScript puro.

## Cortar una versión

1. Subir la versión en `crates/pengu-cli/Cargo.toml`, `Cargo.lock` y
   `editors/vscode/package.json` (deben coincidir).
2. Añadir la entrada en `CHANGELOG.md`.
3. Verificar en local:

   ```sh
   cargo test --workspace
   cargo fmt --all -- --check
   cargo clippy --workspace --all-targets -- -D warnings
   ./scripts/test-release.sh
   node scripts/vsix.mjs --check
   ```

4. Commit y tag:

   ```sh
   git commit -am "release: 0.1.0"
   git tag -a v0.1.0 -m "PenguScript 0.1.0"
   git push origin main --tags
   ```

5. El workflow `Release` compila la matriz, empaqueta, une `SHA256SUMS` y crea
   la release con `gh release create`. También se puede lanzar a mano
   (`workflow_dispatch`) indicando la versión.

Si el tag y el crate no coinciden, el workflow falla en el primer paso
("Comprobar que la versión del binario coincide").

## Prueba de humo local (sin red)

```sh
./scripts/test-release.sh              # compila en release y hace todo el ciclo
./scripts/test-release.sh --skip-build # reutiliza el release ya compilado
```

Hace exactamente lo mismo que un usuario:

1. empaqueta con `package.sh`;
2. monta un repositorio de releases falso en `$TMPDIR` (`releases/download/v<versión>/`);
3. instala con `PENGU_REPO=file://… scripts/install.sh` (verifica `SHA256SUMS`);
4. ejecuta `pengu run` sobre un proyecto temporal y exige que imprima `5`;
5. ejecuta `pengu doctor` con el prefijo en el PATH;
6. empaqueta el `.vsix`;
7. desinstala y comprueba que el binario desaparece.

El CI ejecuta la instalación desde fuente y el empaquetado en cada push; la
prueba de humo completa se puede lanzar a mano o desde el job de release.

## Verificar un artefacto descargado

```sh
sha256sum -c SHA256SUMS --ignore-missing
tar -tzf pengu-0.1.0-x86_64-unknown-linux-gnu.tar.gz
scripts/install.sh --version 0.1.0
```

En Windows:

```powershell
Get-FileHash .\pengu-0.1.0-x86_64-pc-windows-msvc.zip -Algorithm SHA256
```

## Instalación desde un release local

Es la vía que usa `test-release.sh` y sirve para ensayar una release antes de
publicarla:

```sh
mkdir -p /tmp/repo/releases/download/v0.1.0
cp dist/*.tar.gz dist/SHA256SUMS /tmp/repo/releases/download/v0.1.0/
PENGU_REPO=file:///tmp/repo ./scripts/install.sh --version 0.1.0 --prefix /tmp/pengu --no-path
```

## Reversión

Si una release sale mal:

1. `gh release delete v0.1.0 --yes` (o márcala como pre-release).
2. Publica una versión parche con el arreglo; **no** reescribas un tag ya
   publicado: los `SHA256SUMS` descargados dejarían de coincidir.
3. Los usuarios actualizan re-ejecutando el instalador con `--force` (no hay
   autoupdate: es una decisión de diseño, D10 del plan).

## Pendiente: firma de binarios

Los artefactos **no están firmados**. Para distribución pública conviene añadir:

- **macOS**: `codesign` + notarización (`notarytool`) del binario dentro del
  `tar.gz`; sin ello Gatekeeper avisa al primer arranque (`xattr -d
  com.apple.quarantine`).
- **Windows**: Authenticode (`signtool`) sobre `pengu.exe` antes de comprimir.
- **Linux**: no hay firma estándar; los `SHA256SUMS` y la verificación del
  instalador son la garantía actual.

Ambas rutas necesitan certificados de pago y secretos en el workflow; el plan de
release (`scratch/PHASE11_PLAN.md` §7) las declara fuera de alcance por eso.

## Capacidades de la release

- Binario único: compilador + stdlib embebida (29 módulos) + servidor LSP.
- Instaladores `.sh`/`.ps1`/`.bat` con verificación de checksum, PATH idempotente
  y desinstalación.
- Extras: completions de bash/zsh/fish y página de manual.
- `.vsix` reproducible sin npm, con instalación automática opcional.
- `pengu doctor` para diagnosticar instalaciones y `pengu version --json` para
  automatizar.
