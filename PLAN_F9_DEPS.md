# PLAN F9 — Dependencias y package manager

> **Estado:** propuesta para aprobación. No implementado todavía.
> **Base:** F8 cerrada. El CLI PSC aún tiene `add/remove/update/upgrade/verify/
> vendor` como stubs F9 y el manifiesto rechaza `[dependencies]` no vacío.
> **Objetivo:** portar el package manager de stage0 a PSC, sin Python en
> producción, con lockfile reproducible, git/local, verificación y vendor
> offline.

---

## 1. Resumen ejecutivo

PenguScript no tiene un registro central: una dependencia es un **repo git** o
un **path local**, y sus versiones son los **tags git**. Stage0 ya implementa el
modelo completo en:

- `pengu_project.py` (`add/remove/update/upgrade/verify/vendor/tree`, resolución,
  build scripts, cache);
- `pengu_semver.py` (SemVer + constraints);
- `pengu_lock.py` (`pengu.lock`, tree SHA-256, diff);
- tests de `tests/build/test_build_pengu.py`.

F9 porta esa semántica a PSC bajo `psc/src/psc/pkg/**`, conecta
`psc build --locked/--frozen`, y retira los stubs. Python queda como **oráculo
dev-only** hasta F11.

**Fuera de F9:** servidor de registro, publicación, autenticación interactiva,
LSP/bind/cross (F8/F10/F11), cambios de runtime/ABI.

---

## 2. Estado actual

| Pieza | Estado |
|---|---|
| `psc add/remove/...` | stub `not available until F9` |
| `pengu.toml [dependencies]` | PSC lo rechaza con “planned F9” |
| `psc tree/metadata` | funcionan sin deps; con deps fallan |
| `build --locked/--frozen` | aceptados como no-op |
| Stage0 | implementación completa (Python) + tests |
| `pengu.lock` | formato v1, TOML |
| Vendor | `vendor/<name>` + lock; restore en build |
| Build scripts | `build.pengu` preferido; `build.py/sh/Makefile` legado |
| Semver | `^`, `~`, `>=`, `<=`, `>`, `<`, `=`, `*`, tags git |

### Modelo de stage0 que F9 debe preservar

```text
pengu.toml
  [dependencies]
  parent = { url = "https://…/parent.git", version = "^1.2" }
  local  = { path = "../local" }

pengu.lock
  version = 1
  [[package]]
  name = "leaf"
  source = "…"
  constraint = "^1.0"
  version = "1.2.3"
  commit = "…"
  sha256 = "…"
  required_by = ["parent"]
  children = []
```

Instalación en `lib/<name>/`; build script en la raíz de la dependencia;
`vendor/<name>/` para offline.

---

## 3. Decisiones

### D1 — Implementación nativa PSC

- ✅ **Recomendado:** todo el package manager en PSC; `pengu_project.py` y
  `pengu_lock.py` quedan como oráculo dev-only.
- ⚠️ Alternativa: empaquetar el Python. Rompe F11.

### D2 — Semántica stage0 como contrato

- ✅ **Recomendado:** portar el comportamiento y el **formato de lock v1**;
  paridad de mensajes/errores donde sea posible.
- ⚠️ Alternativa: rediseñar. Rompe proyectos existentes.

### D3 — Fuentes soportadas

- ✅ **Recomendado:** **local path** y **git** (`https`, `ssh`, `file://`).
  Versiones = tags git; sin registro central.
- ⚠️ Alternativa: registro HTTP propio. Es otro proyecto.

### D4 — Manifiesto

- ✅ **Recomendado:** sólo `pengu.toml`; `pengu.yaml/json` explícitamente
  rechazados (F6 ya lo hace). Escritura **quirúrgica** de `[dependencies]` para
  preservar comentarios/orden.
- ⚠️ Alternativa: reserializar todo el TOML. Pierde comentarios y formato.

### D5 — Resolver

- ✅ **Recomendado:** portar el resolver **forward-only** de stage0: BFS,
  orden determinista, sin backtracking; conflicto accionable `E0062`; ciclos
  detectados; `required_by`/`children`.
- ⚠️ Alternativa: SAT/backtracking. Más potente, no es stage0 y puede explotar.

### D6 — Lockfile

- ✅ **Recomendado:** `pengu.lock` v1, SHA-256 del árbol (sin `.git`, `build`,
  caches), commit, constraint, versión, `targets`.
  - `build` actualiza si falta;
  - `--locked` verifica y **no escribe**;
  - `--frozen` exige lock y no resuelve red.
- ⚠️ Alternativa: lock v2. Rompe stage0.

### D7 — `build.pengu` y trust

- ✅ **Recomendado:** ejecutar **sólo** `build.pengu` con `psc run`, previa
  autorización (`--trust`, `PENGU_TRUST_ALL=1`, o prompt interactivo).
  - `add` construye sólo la dependencia directa;
  - scripts transitivos no se ejecutan automáticamente;
  - `--no-build`, `--rebuild`/`--force`.
- ⚠️ Alternativa: seguir con `build.py/sh/Makefile`. Requiere Python/shell y
  contradice F11. En F9 se reportan como **legacy no soportado** (`E0063`) con
  instrucciones de migración.

### D8 — Vendor y offline

- ✅ **Recomendado:** `vendor/<name>` con copia reproducible, lock y README;
  `build` restaura desde vendor si falta `lib/<name>`; `--frozen` no toca red.
- ⚠️ Alternativa: sólo cache global. Un clone limpio no buildearía offline.

### D9 — Cache global

- ✅ **Recomendado:** cache de checkouts por `source`/`commit`/hash en
  `PSC_CACHE_DIR`/`~/.cache/pengu`; reutilizar sin copiar `.git` cuando sea
  posible; limpiar con `gc`.
- ⚠️ Alternativa: clonar siempre. Lento y dependiente de red.

### D10 — Seguridad

- ✅ **Recomendado:**
  - validar nombres (`[A-Za-z0-9_-]`), rechazar `..`, `/`, `\`, symlinks que
    escapen del proyecto;
  - validar URL de git (sin `--upload-pack`, `ext::`, opciones inyectadas);
  - ejecutar git con argv (`std.proc`), nunca shell;
  - SHA-256 de contenido, origin y commit en `verify`;
  - instalación atómica (tmp + rename) y rollback.
- ⚠️ Alternativa: confiar en el manifiesto. Inaceptable.

### D11 — Sin cambios de runtime/ABI

- ✅ **Recomendado:** F9 usa `std.rites`/`std.proc`, `std.digest`, `std.toml`,
  `std.archivum`. Si falta una primitiva, se añade en `std`, no en el runtime.
- ⚠️ Alternativa: tocar `pengu_runtime.h`. No hace falta.

### D12 — Compatibilidad

- ✅ **Recomendado:** leer `pengu.lock` existente sin reescribirlo con
  `verify`/`--locked`; preservar el orden canónico de stage0; no cambiar
  `source`/constraints por normalización agresiva.
- ⚠️ Alternativa: regenerar siempre. Cambios espurios en CI.

### D13 — Plataformas

- ✅ **Recomendado:** Linux/macOS primero; paths POSIX/Windows en el modelo;
  CI Windows no bloqueante en F9, antes de F11.
- ⚠️ Alternativa: sólo Linux. La release es multiplataforma.

---

## 4. Arquitectura

```text
psc/src/psc/pkg/
  model.pengu          # DependencySpec, ResolvedNode, Package, Project
  semver.pengu         # Version, Constraint, select_version
  manifest_edit.pengu  # lectura/escritura quirúrgica de [dependencies]
  lock.pengu           # read/write/diff, tree SHA-256
  git.pengu            # clone/fetch/tags/checkout/remote vía argv
  resolve.pengu        # BFS forward-only, conflicts, cycles
  install.pengu        # copia/clone atómico, layout lib/<name>
  build_script.pengu   # build.pengu + trust + force
  vendor.pengu         # snapshot/restore
  verify.pengu         # lock/origin/commit/hash
  cache.pengu          # checkout cache
  errors.pengu         # E0061/E0062/E0063/E0064/E0065
psc/src/psc/cmd/
  add.pengu remove.pengu update.pengu upgrade.pengu
  verify.pengu vendor.pengu
  meta.pengu           # tree/metadata con deps
  stubs.pengu          # sólo F10/F11
```

Reutiliza:

- `psc/driver/manifest.pengu` para el manifiesto y sus campos;
- `psc/driver/paths.pengu` para `lib/` e import roots;
- `psc/driver/build.pengu` para `--locked/--frozen` y cache;
- `std.toml` (lectura), `std.digest` (SHA), `std.proc` (git), `std.archivum`
  (copias), `std.chronicle`.

---

## 5. CLI

```bash
psc add NAME SOURCE [--name=NAME] [--branch=B] [--tag=T] [--version=CONSTRAINT]
                    [--no-build] [--rebuild] [--trust]
psc remove NAME [--keep-files]
psc update [--no-build] [--rebuild] [--trust]
psc upgrade NAME [--version=VERSION|CONSTRAINT] [--branch=B]
psc verify [--verbose] [--json]
psc vendor [--verbose]
psc tree [--json]
psc metadata [--json]
psc build [--locked|--frozen]
```

- `SOURCE`: path local, `file://`, URL git.
- `--version` acepta constraint (`^1.2`, `~1.2.0`, `>=1,<2`, `1.2.3`, `*`).
- `--branch`/`--tag` fijan la ref; `--version` resuelve tags.
- `--no-build`/`--rebuild`/`--trust` igual que stage0.
- `--frozen` implica `--locked` y prohíbe red.
- `tree`/`metadata --json` una línea JSON, `schema_version: 1`.
- Exit codes: 0 OK, 1 error de proyecto/lock/verify, 2 uso.

---

## 6. Manifiesto y escritura

Formato soportado:

```toml
[dependencies]
leaf = { url = "https://example.com/leaf.git", version = "^1.0" }
local = { path = "../local" }
pinned = { url = "…", branch = "main" }
tagged = { url = "…", tag = "v1.2.3" }
```

Reglas:

- nombre único; no `dependencies.foo` duplicado;
- `path` relativo al proyecto, resuelto y validado;
- una dependencia no puede ser `path` y `url` a la vez;
- constraint por defecto `*`;
- `add` escribe con un editor de líneas que preserva comentarios, claves y
  orden; si no puede, falla sin escribir (no reserializa a ciegas);
- escritura atómica y backup `.pengu.toml.bak` opcional;
- `remove` elimina la entrada y, salvo `--keep-files`, `lib/<name>`.

---

## 7. Lockfile

### 7.1 Formato

Idéntico a `pengu_lock.py` v1:

```toml
version = 1
targets = ["x86_64-unknown-linux-gnu"]

[[package]]
name = "leaf"
source = "https://example.com/leaf.git"
constraint = "^1.0"
version = "1.2.3"
commit = "a330b66…"
sha256 = "…"
required_by = ["parent"]
children = []
```

- Orden de paquetes por nombre; listas ordenadas.
- `sha256` = SHA-256 de `(path relativo + NUL + bytes + NUL)` ordenado, ignorando
  `.git`, `build`, `__pycache__`, `.venv`, `node_modules`.
- `targets` canónico (`x86_64-unknown-linux-gnu`, etc.).
- `pengu.lock` no se reescribe bajo `--locked`/`--frozen`/`verify`.

### 7.2 Reglas

- `build` sin flags: resuelve y actualiza lock.
- `--locked`: exige lock y que el grafo actual coincida; no escribe.
- `--frozen`: además exige lock existente y no hace red.
- `verify`: sólo lectura; lock ausente => error.
- `diff_locks`: nombres faltantes/sobrantes, commit, versión, SHA, target.

---

## 8. Resolver

- Entrada: `[dependencies]` del proyecto + manifiestos de dependencias.
- BFS por niveles; nombres ordenados; sin backtracking.
- Para git:
  - listar tags (`git ls-remote --tags` o cache local);
  - filtrar SemVer válido;
  - elegir la versión más alta que satisfaga **todas** las constraints;
  - checkout detached del commit; registrar commit/versión.
- Para path local: versión del manifiesto; commit vacío; hash del árbol.
- Detección de ciclos; `required_by` y `children`.
- Conflictos:
  - dos constraints incompatibles => `E0062` con paquetes/constraints;
  - falta tag => `E0062`;
  - nombre duplicado con fuentes distintas => `E0062`.
- Salida determinista; mismo lock en Linux/macOS.
- No instalar transitivas con `add` (sólo resolver), salvo que falten y el
  usuario ejecute `update`/`build`.

---

## 9. Instalación

- Destino `lib/<name>/`.
- Local: copia de árbol (excluyendo `build/`, caches) a tmp + rename; nunca
  symlink que escape.
- Git: clone/checkout a tmp + rename; `.git` conservado para upgrade/verify.
- Si existe:
  - `add` refresca y fuerza build de la directa;
  - `update` hace fetch/pull/checkout;
  - `--rebuild` fuerza script.
- Rollback si falla copia/clone; no dejar `lib/<name>` a medias.
- No seguir symlinks fuera del proyecto; validar cada path.

---

## 10. Build scripts y trust

- Sólo `build.pengu` (F9).
- Se ejecuta con `psc run build.pengu [-- --force]` desde la raíz de la dep.
- Requiere runtime (`PENGU_LIB_DIR`/build) como cualquier `psc run`.
- Trust:
  - `--trust`;
  - `PENGU_TRUST_ALL=1/true/yes/on`;
  - prompt interactivo si TTY;
  - sin trust y no interactivo: **skip con warning**, no ejecutar.
- `add` ejecuta sólo la dependencia directa; transitivas no.
- Errores del script: warning, no abortar la instalación (stage0), salvo que el
  usuario pida `--strict-build` (F9 opcional).
- `build.py`, `build.sh`, `Makefile`: error `E0063` “legacy build script not
  supported; migrate to build.pengu” (no Python/shell en producción).

---

## 11. Vendor y offline

```bash
psc vendor
# vendor/<name>/… + vendor/pengu.lock + README.md
```

- Copia `lib/<name>` a `vendor/<name>` excluyendo `build/`, `__pycache__`,
  caches; conserva `.git` (stage0) para upgrade.
- `build` restaura desde vendor si falta `lib/<name>`.
- `--frozen` no hace red y verifica commit/hash del lock.
- Un clone limpio + vendor debe buildear sin red.
- `vendor` no borra dependencias no usadas; reporta.

---

## 12. Verify

```bash
psc verify [--verbose] [--json]
```

Comprueba por paquete:

1. existe `lib/<name>`;
2. origen git coincide (si aplica);
3. commit coincide (prefijo corto permitido);
4. SHA-256 del árbol coincide;
5. lock existe y target coincide.

Salida 0/1; `--json` con `{type:"verify", ok, problems:[...]}`.
Nunca escribe lock.

---

## 13. Build/run con dependencias

- `manifest` deja de rechazar `[dependencies]`; expone `DependencySpec`.
- `paths` añade `lib/<dep>` y sus `src/` a import roots y C include dirs.
- `build`:
  1. lee manifiesto;
  2. si hay deps: restaura vendor si falta; resuelve/verifica lock;
  3. verifica/actualiza lock según flags;
  4. build scripts (trust) antes de compilar;
  5. compila con imports/links de deps;
  6. guarda lock.
- `run`/`test`/`expand`/`check` respetan deps y `--locked/--frozen`.
- Cache key incluye lock/hash de deps.
- `--frozen` sin lock => `E0061`; lock desactualizado => `E0061`.
- No red en `--frozen`.

---

## 14. Errores

| Código | Uso |
|---|---|
| `E0061` | lock ausente/desactualizado con `--locked`/`--frozen` |
| `E0062` | conflicto de resolución, tag inexistente, fuente duplicada |
| `E0063` | build script legacy no soportado |
| `E0064` | fallo de red/git/auth (mensaje accionable) |
| `E0065` | verify: origen/commit/SHA no coincide |
| `E0066` | nombre/path inseguro o escape del proyecto |

Todos con `help:` y exit 1 (uso 2).

---

## 15. Tests

### 15.1 Portar stage0

- `add` local, git, transitive, build.pengu, `--trust`.
- `add` existente fuerza rebuild.
- `update --trust` fuerza; `--no-build` no.
- transitiva no se construye automáticamente.
- `remove`/`--keep-files`.
- rechazo de `..`, path escape, nombres inválidos.
- readonly tree rollback.

### 15.2 Nuevos

- `test_f9_semver.py`: versiones/constraints/tags, prerelease.
- `test_f9_lock.py`: serialización determinista, hash, diff, `--locked` no
  reescribe, `--frozen` sin lock.
- `test_f9_local_git.py`: local + git + tag + branch.
- `test_f9_transitive.py`: grafo, ciclos, conflicto E0062.
- `test_f9_vendor_offline.py`: vendor, borrar `lib`, sin red, `--frozen`.
- `test_f9_verify.py`: SHA/commit/origin alterados.
- `test_f9_build_script.py`: trust/no trust, directa vs transitiva.
- `test_f9_manifest_edit.py`: comentarios preservados, duplicados, TOML válido.
- `test_f9_security.py`: traversal, symlink, URL maliciosa.
- `test_f9_cli_json.py`: tree/metadata/verify JSON.

### 15.3 Integración

- Proyecto fixture con dependencia local + git + transitiva; build PSC.
- Vendor en clone limpio sin red.
- Lock existente de stage0 se lee y `verify` no lo cambia.
- F1–F8 siguen verdes; bootstrap.

---

## 16. Fases y estimación

| Fase | Contenido | Semanas |
|---|---|---:|
| F9.0 | Modelo, semver, lock, manifest editor, errores | 1.5 |
| F9a | Add/remove local, layout `lib/`, build integration | 1.5 |
| F9b | Git clone/tags/branch, constraints, transitive | 2 |
| F9c | Update/upgrade/tree/metadata/verify | 1.5 |
| F9d | Vendor, offline, `--locked/--frozen`, cache | 1.5 |
| F9e | build.pengu/trust, security, rollback | 1.5 |
| F9f | Tests, CI, docs, performance | 1.5 |
| **Total** | | **9–11** |

Timebox: 9–11 semanas; si F9e se desborda, F9.5 con aprobación. El núcleo
local/git/lock/vendor no se recorta.

---

## 17. Criterios de aceptación

1. `add/remove/update/upgrade/verify/vendor/tree/metadata` funcionan en PSC.
2. Dependencia local + git + transitiva se instala y build con PSC.
3. `pengu.lock` de stage0 se lee; `verify`/`--locked` no lo reescriben.
4. `--frozen` sin red build desde `vendor`.
5. Conflicto de constraints => `E0062` determinista.
6. `build.pengu` sólo con trust; sin trust no ejecuta.
7. SHA/commit/origin verificados.
8. Path traversal/symlink/URL maliciosa rechazados.
9. Lock determinista entre Linux/macOS (y Windows antes de F11).
10. Sin Python en producción.
11. F1–F8, bootstrap y preflight siguen verdes.
12. Sin cambios de runtime/ABI.
13. Docs/CLI/CHANGELOG actualizados; commit final en `main`, sin push.

---

## 18. Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Editor TOML rompe comentarios | Alta | Medio | editor quirúrgico + tests |
| Semver distinto a stage0 | Media | Alto | port 1:1 + tabla de casos |
| Resolver forward-only no cubre un caso | Media | Medio | E0062 accionable; no backtracking |
| Git auth/red en CI | Media | Medio | tests con repos locales |
| build scripts inseguros | Media | Alto | trust + argv + sandbox de paths |
| Symlink/traversal | Media | Alto | validación y tests |
| Lock no determinista | Media | Alto | hash canónico + fixtures |
| Windows paths | Media | Medio | modelo portable, CI antes F11 |
| Scope creep a registro | Alta | Alto | fuera de alcance |

---

## 19. Fuera de alcance

- Registro central, publicación, búsqueda.
- Autenticación interactiva/gestión de credenciales.
- Git submodules/LFS.
- Workspaces multi-proyecto.
- Firma GPG de paquetes.
- Lockfile v2.
- Dependencias binarias por plataforma.

---

## 20. Preguntas para aprobar

1. ¿Aprobado portar stage0 1:1, con Python sólo como oráculo (D1/D2)?
2. ¿Aprobado local + git, sin registro central (D3)?
3. ¿Aprobado lock v1 y `--locked`/`--frozen` (D6)?
4. ¿Aprobado `build.pengu` only + `--trust`, con legacy `E0063` (D7)?
5. ¿Aprobado vendor/cache offline (D8/D9)?
6. ¿Aprobado el editor quirúrgico de TOML (D4)?
7. ¿Aprobado el resolver forward-only (D5)?
8. ¿Aprobado el presupuesto 6–10 semanas y la seguridad de D10?

Si se aprueba, empiezo por **F9.0** (modelo, semver, lock, manifest editor) y
luego **F9a** (local + build integration), que son la base del resto.
