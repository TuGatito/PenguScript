# Fase 5 — Paquetes git, lock y vendor

Objetivo: **cerrar la Fase 5 de `scratch/TOOLING_PLAN.md`** con un gestor de paquetes
usable de verdad: `pengu add/remove/update/tree/fetch/vendor`, resolución de git
(tags/ramas/revs), `Tome.lock` con checksums, caché local, `--offline`/`--locked`,
detección de ciclos y conflictos, y proyectos vendoreados que compilan sin red.

Criterio de cierre (el que voy a exigir para marcar la fase ✅):

1. Un proyecto con **dos dependencias git** (una por `tag`, otra por `rev`) genera su
   `Tome.lock`, se construye sin red con `--offline` desde la caché, y `pengu vendor`
   produce un árbol que compila sin `~/.cache` ni red.
2. `pengu update` mueve una rama pero **no** un `rev`; `pengu build --locked` falla con
   `PGS-E1804` si el lock no coincide; un checksum manipulado da `PGS-E1808`.
3. Ciclos y conflictos de nombre/fuente/features dan `PGS-E1807` con el camino completo.
4. `pengu tree` muestra el grafo resuelto, deduplicado y ordenado.
5. Todo cubierto por tests de integración con repos git reales creados en `tempfile`
   (sin red), y la suite/clippy/fmt quedan limpios.

## Estado de partida

- `crates/pengu-project` sabe **leer** `Tome.toml` (`parse_manifest`), validarlo y
  convertirlo a `Cargo.toml` (`to_cargo_toml`), y tiene un `validate_lock` embrionario
  que compara la **versión del manifiesto** con `version = 1` del lock (incorrecto: la
  norma dice que compara el conjunto de paquetes, no la versión del proyecto).
- `crates/pengu-build` compila/ejecuta el proyecto, pero convierte dependencias git
  directamente a Cargo (sin lock, sin caché, sin vendor).
- **No existe binario `pengu`**: ninguna de las fases de tooling dejó CLI.
- La norma está en `docs/LANGUAGE.md` §18 (§18.2 manifiesto, §18.3 lockfile,
  §18.3.1 resolución). Códigos: `PGS-E1802`…`PGS-E1808`.

## Norma que hay que cumplir (resumen de §18)

- Dependencias **git o path**, sin registry. Git exige **exactamente uno** de
  `tag`/`branch`/`rev`; `pengu add` elige tag si existe, si no `branch = "main"` **con
  advertencia** (`PGS-E1806` si no hay ref válido).
- `Tome.lock`:

```toml
version = 1

[[package]]
name = "json"
version = "0.3.1"
source = "git+https://github.com/pengu/json?tag=v1.2.0"
commit = "9f1c..."
checksum = "sha256-..."
features = ["std"]
dependencies = ["text"]
```

  Reglas: `source` canónico (`git+URL?tag=|branch=|rev=`, `path+../local`), `commit`
  obligatorio solo en git, `checksum` **SHA-256 del árbol empaquetado** y obligatorio,
  `dependencies` nombres exactos, **una sola versión por nombre**, entradas ordenadas
  por `name`, el archivo lo reescribe `pengu`.
- Resolución determinista: sin SAT, una versión por nombre, features aditivas, `update`
  re-resuelve `branch`/`tag` e ignora el lock, `build` respeta el lock, `rev` no se mueve.

## Arquitectura

Dos crates nuevos, sin dependencias externas (igual que el resto del workspace):

```
crates/pengu-pkg/          lógica pura, sin red en los tests
  src/lib.rs               API pública y tipos (PkgError, ResolvedPackage…)
  src/sha256.rs            SHA-256 streaming + hex (`sha256-<hex>`)
  src/toml.rs              lector TOML pequeño (tablas, arrays, inline tables)
  src/manifest.rs          lectura/edición quirúrgica de Tome.toml (preserva formato)
  src/source.rs            Source canónico + parseo + validación (E1806)
  src/git.rs               trait Git + ShellGit (clone/fetch/rev-parse/ls-remote/archive)
  src/cache.rs             caché content-addressed en PENGU_HOME/cache
  src/lock.rs              Tome.lock: parseo, escritura, comparación (E1804/E1808)
  src/tree_hash.rs         checksum canónico del árbol empaquetado
  src/resolver.rs          grafo, features, ciclos y conflictos (E1807)
  src/vendor.rs            materialización y lectura de `vendor/`
  src/tree.rs              render del árbol de dependencias
  src/ops.rs               add/remove/update/fetch/vendor + build del lock

crates/pengu-cli/
  src/main.rs              binario `pengu`: parseo de args, códigos de salida
  src/args.rs              parser de flags/subcomandos (sin clap)
  src/commands.rs          add/remove/update/tree/fetch/vendor/build/run/test
  src/env.rs               raíz del proyecto, PENGU_HOME, TTY/color, verbosity
```

`pengu-project` se queda como está (lectura del manifiesto y conversión a Cargo);
`pengu-pkg` lo usa. `pengu build` en la CLI: resuelve/verifica el lock y luego llama a
`pengu_build::compile`/`build`.

## Decisiones (con motivo)

- **D1 · Sin dependencias externas.** El workspace ya prohíbe `unsafe` y no tiene
  crates externos; añadir `clap`/`toml`/`sha2` obligaría a vendorizar el propio
  compilador. CLI a mano + TOML mínimo + SHA-256 propio, cada uno con vectores de
  prueba (NIST para SHA-256; ida y vuelta para TOML).
- **D2 · Git vía `git` del sistema.** `Command::new("git")` con `LC_ALL=C`,
  `GIT_TERMINAL_PROMPT=0` y `-c protocol.version=2`; nunca `unsafe`. Tests usan
  `git init` local, así que no hay red en CI.
- **D3 · Caché por repositorio, no por checkout.** `cache/git/<slug>.git` (bare) por
  URL; `fetch` actualiza refs y los checkouts se materializan por commit en
  `cache/src/<sha256-url>/<commit>/`. Inmutable y compartible.
- **D4 · Checksum = hash canónico del árbol.** SHA-256 sobre entradas ordenadas por
  ruta en bytes: `path\0mode\0size\0contenido`, ignorando `.git`, `target`, `vendor`,
  `Tome.lock`; mismo algoritmo para git y path (el de path es el que exige la norma).
  Documentado en `tree_hash.rs` y con test de invariancia (orden, permisos, symlinks).
- **D5 · Lock como fuente de verdad en `build`.** Si existe `Tome.lock` y coincide con
  el manifiesto, se usan commit+checksum exactos sin tocar la red. `--locked` exige que
  exista y coincida; `--offline` prohíbe cualquier `fetch`.
- **D6 · Vendor reproducible.** `vendor/<name>/` con el árbol del commit + 
  `vendor/pengu-vendor.toml` (name, source, commit, checksum). `build` prefiere vendor
  si existe y **verifica checksums**; si no coincide, `PGS-E1808` (nunca compilar
  silenciosamente otra cosa).
- **D7 · Edición de manifiesto sin romper el archivo.** `add`/`remove` editan el texto
  por bloques (`[dependencies.<name>]` o línea inline), preservando comentarios y orden;
  `Tome.toml` se reescribe completo solo si hay que insertar tabla nueva. Test de
  idempotencia (`add` dos veces = un solo bloque).
- **D8 · Escritura atómica.** Lock y manifiesto se escriben a `.tmp` + `rename` en el
  mismo directorio; nunca se deja un archivo a medias si falla la resolución.
- **D9 · Un solo diagnóstico por fallo, con acción.** Cada error lleva `code`, mensaje
  y `help` ("ejecuta `pengu fetch`", "fija un `rev`", …). Sin `unwrap` en rutas de
  usuario: todo `io::Error` se convierte con contexto.
- **D10 · Determinismo.** Orden por `name` en lock, vendor y `tree`; sin timestamps
  dentro de archivos generados; `update` solo cambia lo que debe.
- **D11 · Features aditivas y una versión por nombre.** El resolver une features y
  falla (`E1807`) si dos consumidores piden fuentes distintas para el mismo nombre o el
  grafo tiene un ciclo; el mensaje muestra el camino `a -> b -> a`.
- **D12 · `rev` inmóvil.** `update` nunca mueve un `rev`; `tag`/`branch` sí se
  re-resuelven. Test explícito.

## Fases de ejecución

| Fase | Entrega | Aceptación |
|---|---|---|
| **P0** | `pengu-pkg` esqueleto: `sha256`, `toml`, `source`, `tree_hash` | Vectores NIST de SHA-256; `source` ida/vuelta; checksum estable |
| **P1** | `git.rs` + `cache.rs` | Clonar/fetch de repo local, `rev-parse`, checkout por commit, reutilización de caché |
| **P2** | `lock.rs` + `resolver.rs` (sin ciclos aún) | Lock determinista y ordenado; `E1804` si el manifiesto cambió |
| **P3** | `ops.rs` + CLI `fetch`/`tree`/`build --locked` | Grafo resuelto real; `tree` legible; `--locked`/`--offline` |
| **P4** | `add`/`remove`/`update` + flags | `add --git --tag/--branch/--rev`, tag preferido, aviso si `branch=main`; `update` mueve ramas y no revs |
| **P5** | `vendor.rs` + CLI `vendor` + build desde vendor | Proyecto vendoreado compila con `--offline` y sin caché |
| **P6** | Ciclos, conflictos, features, path deps | `E1807` con camino; features unidas; path verificado |
| **P7** | Docs, paridad, limpieza | `docs/STDLIB.md`/`TOOLING_PLAN.md`/`STATUS.md`; clippy+fv; sin TODO |

## Matriz de paridad (lo que se espera de un gestor de paquetes)

| Capacidad | Cargo | npm/pnpm | Go | Pengu (Fase 5) |
|---|---|---|---|---|
| Añadir dep por nombre/URL | `cargo add` | `npm i` | `go get` | `pengu add --git URL [--tag/--branch/--rev]` |
| Añadir dep local | `cargo add --path` | `file:` | `replace` | `pengu add --path ../x` |
| Quitar | `cargo rm` | `npm rm` | editar | `pengu remove` |
| Actualizar | `cargo update` | `npm update` | `go get -u` | `pengu update [dep]` |
| Árbol | `cargo tree` | `npm ls` | `go mod graph` | `pengu tree` |
| Descargar sin construir | `cargo fetch` | `npm ci` | `go mod download` | `pengu fetch` |
| Lock determinista | `Cargo.lock` | lockfile | `go.sum`+`go.mod` | `Tome.lock` |
| Integridad | rev git | `integrity` | `go.sum` | `checksum = sha256-…` |
| Offline | `--offline` | `--offline` | `GOPROXY=off` | `--offline` |
| Fallar si el lock cambia | `--locked` | `npm ci` | `-mod=readonly` | `--locked` |
| Vendor | `cargo vendor` | — | `go mod vendor` | `pengu vendor` |
| Detección de ciclos | sí | sí | sí | `PGS-E1807` con camino |

## Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| `git` ausente en el sistema | Detección temprana con mensaje accionable; los tests de lógica pura no lo necesitan |
| Checksum distinto entre SO por CRLF/symlinks | Normalizar a bytes, ignorar mtime, modo solo `exec`; test con symlink y archivo vacío |
| Caché compartida se corrompe | Verificación de commit en checkout; `pengu fetch --force` re-clona |
| `add` rompe el TOML del usuario | Edición por bloques + test de ida/vuelta con comentarios y tablas |
| Lock escrito a medias | Temp + rename + test que mata el proceso entre pasos |

## Diagnósticos

| Código | Cuándo |
|---|---|
| `PGS-E1802` | `pengu` mínimo del manifiesto no se cumple (ya existe) |
| `PGS-E1803` | Dependencia o `[link]` no encontrada / path inexistente |
| `PGS-E1804` | Lock ausente con `--locked`, o desactualizado respecto a `Tome.toml` |
| `PGS-E1806` | Git sin `tag`/`branch`/`rev` o ref inválida |
| `PGS-E1807` | Conflicto de nombre/fuente/features o ciclo en el grafo |
| `PGS-E1808` | Lock malformado, checksum incorrecto, o `--offline` sin caché |

## Cero deuda: reglas de trabajo

- Nada de `TODO`/`unimplemented!` al cerrar una fase; si algo no entra, no se escribe
  la función o se deja fallando con diagnóstico explicado.
- Cada módulo con tests propios; cada comando con test de integración de extremo a
  extremo (proceso real `pengu` cuando aplique).
- `cargo fmt --all -- --check` y `cargo clippy --workspace --all-targets -D warnings`
  limpios en cada fase, no al final.
- Toda decisión no obvia se anota aquí (sección Decisiones) y en `scratch/STATUS.md`.

## Estado final (2026-11-15)

Fase 5 **cerrada**. Las siete fases P0–P7 se completaron con sus criterios de aceptación:

| Fase | Estado | Evidencia |
|---|---|---|
| P0 | ✅ | `pengu-pkg` con `sha256` (NIST), `toml`, `source`, `tree_hash`; tests propios |
| P1 | ✅ | `cache.rs` + `git.rs`; tests con repos locales (tag, rama, rev, offline) |
| P2 | ✅ | `lock.rs` + `resolver.rs`; lock determinista, `PGS-E1804` si el manifiesto cambia |
| P3 | ✅ | `ops.rs` + CLI `fetch`/`tree`/`build --locked`/`run`/`test` |
| P4 | ✅ | `add`/`remove`/`update` con edición quirúrgica del manifiesto y spec automática |
| P5 | ✅ | `vendor.rs` + `pengu vendor [--check]`; build offline desde vendor y detección de copias editadas |
| P6 | ✅ | ciclos con camino, conflictos de fuente/versión, features aditivas, `optional`, path deps |
| P7 | ✅ | docs, paridad, clippy/fmt y suite completa |

Cifras finales: **646 tests** en el workspace, `cargo fmt --all -- --check` limpio,
`cargo clippy --workspace --all-targets -- -D warnings` sin avisos, y `git status` sin
archivos sin trackear. Sin `TODO`, sin `unimplemented!` y sin funciones a medias en
`pengu-pkg`/`pengu-cli`.

Desviaciones anotadas durante la ejecución:

- El build integra los paquetes **fusionándolos como módulos** en una sola crate Rust en
  vez de compilar cada paquete por separado (D2 ampliada): evita resolver tipos entre
  crates y reutiliza el cargador de `std`.
- El TOML del lock no admite flotantes ni fechas; cualquier otro valor es error.
- Un lock sin `[[package]]` es válido (proyecto sin dependencias).
- `update` sin nombre re-resuelve todo; con nombre congela el resto de commits.
- `pengu new` se añadió aquí (aunque el plan lo situaba en la Fase 1) porque la Fase 5
  exige "templates que usan dependencias": hay tres templates embebidos (`bin`, `lib`,
  `with-dependency`) y el último demuestra el flujo completo sin red. Los templates
  remotos y `pengu init` siguen pendientes en la Fase 1.
