# Instalación

PenguScript se distribuye como un único binario `pengu` que incluye el
compilador, la biblioteca estándar embebida y el servidor LSP. No hay pasos de
compilación para el usuario: el binario compila programas con el `rustc` y el
`cargo` del sistema.

## Requisitos

| Plataforma | Requisitos |
|---|---|
| Linux x86_64 / aarch64 | `sh`, `curl` o `wget`; para compilar programas: `rustc` + `cargo` (Rust ≥ 1.85) |
| macOS x86_64 / arm64 | lo mismo |
| Windows x86_64 | PowerShell 5.1 (viene con Windows); para compilar programas: Rust con `cargo` |

Las dependencias Git y `clang` solo hacen falta para `pengu add`/`bindgen`.

## Linux y macOS

```sh
curl -fsSL https://raw.githubusercontent.com/TuGatito/PenguScript-Rust/main/scripts/install.sh | sh
```

O desde el repositorio:

```sh
git clone https://github.com/TuGatito/PenguScript-Rust
cd PenguScript-Rust
./scripts/install.sh
```

Opciones:

```sh
./scripts/install.sh --version 0.1.0          # versión concreta
./scripts/install.sh --prefix /opt/pengu      # otro prefijo
./scripts/install.sh --from-source .          # compila en vez de descargar
./scripts/install.sh --no-path                # no toca el PATH
./scripts/install.sh --uninstall              # desinstala
./scripts/install.sh --help
```

Variables de entorno: `PENGU_HOME` (prefijo, por defecto `~/.pengu`),
`PENGU_REPO` (repositorio de releases), `PENGU_NO_PATH=1` (equivale a
`--no-path`).

Si todavía **no hay una release publicada** (o el artefacto de tu plataforma no
está), el instalador avisa y compila desde el checkout en el que está: por eso
`./scripts/install.sh` dentro del repositorio funciona sin `--version`. Si lo
ejecutas por tubería (`curl … | sh`) no hay checkout, y entonces hace falta
`--version X` o clonar el repositorio.

## Windows

Desde `cmd`:

```bat
scripts\install.bat
```

Desde PowerShell:

```powershell
.\scripts\install.ps1
```

El `.bat` traduce las opciones al estilo de PowerShell:

```bat
scripts\install.bat --version 0.1.0
scripts\install.bat --prefix D:\pengu
scripts\install.bat --from-source .
scripts\install.bat --uninstall
```

El instalador de PowerShell es **ASCII puro** a propósito: Windows PowerShell 5.1
lee los `.ps1` sin BOM como ANSI y los acentos se corromperían.

## Qué instala

```text
~/.pengu/
├── bin/pengu
└── share/
    ├── completions/pengu.bash
    ├── completions/_pengu          (zsh)
    ├── completions/pengu.fish
    └── man/man1/pengu.1
```

En Windows, `%USERPROFILE%\.pengu\bin\pengu.exe` y los extras en
`%USERPROFILE%\.pengu\share`.

### PATH

El instalador añade una entrada al PATH **una sola vez**: es idempotente y
comprueba si el directorio ya está. En shell escribe un bloque delimitado en
`~/.bash_profile`, `~/.profile`, `~/.bashrc`, `~/.zshrc` y `~/.zprofile`
(los que existan, y crea `~/.profile` si no hay ninguno) para que también lo
vea una shell de login, que es la que hereda un VS Code abierto desde el
escritorio:

```sh
# >>> pengu >>>
export PATH="$HOME/.pengu/bin:$PATH"
# <<< pengu <<<
```

En fish usa `fish_add_path` en `~/.config/fish/config.fish`. En Windows escribe
el PATH **de usuario** (`[Environment]::SetEnvironmentVariable("Path", …, "User")`).

Abre una terminal nueva para que el PATH se aplique. `--uninstall` elimina el
bloque y la entrada.

## Comprobar la instalación

```sh
pengu version
pengu version --json
pengu doctor
```

`doctor` comprueba, sin fallar por lo opcional:

| Comprobación | Requerida | Qué verifica |
|---|---|---|
| `binario` | sí | ruta del ejecutable |
| `PATH` | sí | que `pengu` del PATH sea este binario |
| `stdlib` | sí | módulos embebidos (29) |
| `compilador` | sí | analiza un proyecto temporal de punta a punta |
| `rustc` | no | version y disponibilidad |
| `cargo` | no | version y disponibilidad |
| `clang` | no | necesario para `pengu bindgen` |
| `git` | no | necesario para dependencias git |
| `extensión` | no | `penguscript.pengu-lsp` en VS Code |

`pengu doctor --json` devuelve lo mismo en JSON y sale con 1 si falla alguna
comprobación requerida.

## Completions y manual

```sh
pengu completions bash >> ~/.bashrc
pengu completions zsh  > "${fpath[1]}/_pengu"
pengu completions fish > ~/.config/fish/completions/pengu.fish
pengu man | man -l -
```

El instalador ya deja los tres archivos y el manual en `share/`.

## Extensión de VS Code

```sh
node scripts/vsix.mjs            # genera dist/penguscript.pengu-lsp-0.1.0.vsix
node scripts/vsix.mjs --install  # además la instala con `code --install-extension`
```

El script no usa npm: valida el manifiesto, comprueba que la versión de la
extensión coincide con `pengu version`, arma el `.vsix` y lo comprime. Para
Neovim/LazyVim/vim consulta [`LSP.md`](LSP.md).

## Desinstalar

```sh
./scripts/install.sh --uninstall
```

```bat
scripts\install.bat --uninstall
```

Borra el prefijo, las completions, el manual y la entrada del PATH. No toca tus
proyectos ni la extensión de VS Code (`code --uninstall-extension
penguscript.pengu-lsp`).

## Problemas frecuentes

- **`pengu: command not found` tras instalar**: abre una terminal nueva; el
  bloque del PATH se añade al final del archivo de shell y las sesiones abiertas
  no lo leen.
- **`doctor` dice `FALLA PATH`**: hay otro `pengu` antes en el PATH. Usa
  `which -a pengu` y reordena, o reejecuta con `--prefix` en un directorio
  prioritario.
- **Windows: "no se puede cargar el archivo … porque la ejecución de scripts
  está deshabilitada"**: usa `install.bat`, que llama a PowerShell con
  `-ExecutionPolicy Bypass`.
- **`pengu build` falla con "no se encuentra cargo"**: instala Rust desde
  <https://rustup.rs>; el binario de PenguScript no incluye `cargo`.
