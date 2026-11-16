# PenguScript

**El lenguaje chico con backend filoso.**

PenguScript es un lenguaje de sistemas pequeño, estático y directo. El backend
Rust es un detalle de implementación: no se expone como lenguaje intermedio ni
como destino que el usuario tenga que conocer.

- Especificación: [`docs/LANGUAGE.md`](docs/LANGUAGE.md) — `0.6.0`.
- Biblioteca estándar: [`docs/STDLIB.md`](docs/STDLIB.md) — `0.3.0`.
- Cambios: [`CHANGELOG.md`](CHANGELOG.md).
- Instalación: [`docs/INSTALL.md`](docs/INSTALL.md).
- Release e instaladores: [`docs/RELEASE.md`](docs/RELEASE.md).
- Frontend: [`docs/FRONTEND.md`](docs/FRONTEND.md).
- Build, caché y remapeo de errores: [`docs/BUILD.md`](docs/BUILD.md).
- Formato, lints y calidad: [`docs/QUALITY.md`](docs/QUALITY.md).
- LSP y editores: [`docs/LSP.md`](docs/LSP.md).
- Bindgen de cabeceras C: [`docs/BINDGEN.md`](docs/BINDGEN.md).

## Instalación

Linux y macOS:

```sh
curl -fsSL https://raw.githubusercontent.com/TuGatito/PenguScript-Rust/main/scripts/install.sh | sh
```

Windows (PowerShell o `cmd`):

```bat
scripts\install.bat
```

Ambos instaladores colocan el binario en `~/.pengu/bin` (o `%USERPROFILE%\.pengu\bin`),
añaden el directorio al `PATH`, generan las completions de bash/zsh/fish y la
página de manual. Para compilar desde el repositorio:

```sh
./scripts/install.sh --from-source .
```

La extensión de VS Code se empaqueta e instala con:

```sh
node scripts/vsix.mjs --install
```

Detalles, opciones y desinstalación en [`docs/INSTALL.md`](docs/INSTALL.md).

## Uso rápido

```sh
pengu new hola --template bin
cd hola
pengu run
pengu test
pengu fmt --check
pengu lint
pengu lsp          # servidor LSP por stdio
```

## Estado

El compilador está **completo de punta a punta**: `pengu` analiza, verifica
(types, ownership, FFI), baja a LIR, genera Rust y compila con Cargo, con caché
incremental, remapeo de errores de `rustc` a spans del código fuente y
`pengu check --watch`.

- **Frontend**: lexer, parser Pratt, CST lossless con recuperación, límites y
  fuzz; corpus de sintaxis de la especificación clasificado (Gate B).
- **Semántica**: HIR de módulos/imports, checker de tipos e inferencia,
  genéricos, pacts y operadores, const eval, ownership con préstamos/NLL,
  moves y `curse`.
- **Backend**: LIR/CFG con locales SSA, monomorfización, codegen a Rust, runtime
  `Show`, `panic`/`assert`, Cargo/Tome/link y sourcemaps.
- **Biblioteca estándar**: 29 módulos en `std/` — núcleo (`integrum`, `floatem`,
  `verbum`, `capsa`, `tabula`, `fasciculus`, `littera`, `veritas`, `numerus`,
  `fluxus`, `proba`, `opera`, `optio`, `funis`, `structura`), sistema
  (`via`, `exsecutor`, `ambitus`, `tempus`, `terminus`, `globus`, `archivum`,
  `cellula`), FFI (`nexus`) y auto-hospedaje textual (`libra`, `iason`,
  `digestum`, `versio`, `rete`).
- **Herramientas**: `pengu new/fetch/tree/vendor/build/run/test/add/remove/update`,
  `fmt`, `lint`, `fix`, `doc`, `bench`, `explain`, `size`, `bindgen`, `lsp`,
  `doctor`, `completions`, `man`.
- **Editores**: cliente LSP propio para VS Code (`editors/vscode`, sin
  dependencias de npm) y configuración para Neovim/LazyVim/vim.

`cargo test --workspace` tiene **803 tests**; `fmt` y `clippy -D warnings`
están limpios y el CI ejecuta además `pengu fmt --check std`,
`pengu lint --std std`, la validación de los scripts de instalación y el ciclo
de release.

## Workspace

| Crate | Responsabilidad |
|---|---|
| `crates/pengu-span` | `FileId`, `Span`, `Spanned<T>` |
| `crates/pengu-vfs` | Archivos, overlays, líneas/columnas, hash de contenido |
| `crates/pengu-diag` | Diagnósticos, etiquetas, severidades |
| `crates/pengu-syntax` | Lexer, AST, parser y CST lossless de expresiones, items y `.d.pengu` |
| `crates/pengu-hir` | HIR de nombres, módulos, scopes, declaraciones y cuerpos |
| `crates/pengu-types` | Tipos, inferencia, records/sums/patrones, pacts, const eval y FFI |
| `crates/pengu-check` | Ownership, préstamos, NLL, closures y métodos |
| `crates/pengu-lir` | LIR/CFG y monomorfización |
| `crates/pengu-codegen` | Codegen a Rust y runtime embebido |
| `crates/pengu-layout` | Layout de tipos (`size`/`align`) verificado contra `rustc` |
| `crates/pengu-std` | Fuentes de la stdlib embebidas con un `FileId` por módulo |
| `crates/pengu-build` | Pipeline, Cargo, caché, remapeo y `check` |
| `crates/pengu-project` | `Tome.toml`, `Tome.lock` y validación del proyecto |
| `crates/pengu-pkg` | Resolución, lock, git, caché, vendor y operaciones de paquetes |
| `crates/pengu-json` | JSON mínimo compartido por el LSP y el build |
| `crates/pengu-sha256` | SHA-256 compartido por el gestor de paquetes y el build |
| `crates/pengu-fmt` | Formateador de tokens con verificación semántica |
| `crates/pengu-lint` | 10 lints configurables |
| `crates/pengu-bindgen` | Clang AST → `.d.pengu` |
| `crates/pengu-lsp` | Servidor LSP (JSON-RPC propio, UTF-8/16, caché por hash) |
| `crates/pengu-cli` | Binario `pengu` |

Requisitos: Rust 2024, MSRV **1.85.0**. El lexer usa `unicode-ident` para XID;
el resto del núcleo no tiene dependencias externas.

```sh
cargo test --workspace
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
```

## Estructura

```text
docs/       especificación, stdlib y guías
crates/     compilador, herramientas y servidor LSP en Rust
std/        biblioteca estándar en PenguScript
editors/    cliente de VS Code y configuración de Neovim
examples/   programas de ejemplo compilados y ejecutados en los tests
scripts/    instaladores, empaquetado y .vsix
scratch/    planes, herramientas y QA (no es código de producción)
```

El código de `scratch/` no forma parte del compilador; es material de diseño y
validación.
