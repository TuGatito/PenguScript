# PenguScript v2.0.0 Build System & Package Manager

The PenguScript Build Manager (`pengu_project.py`) is a Cargo-style tool providing project initialization, module dependency resolution, C bundling, incremental compilation caching, debug/release profiles, and multi-target compilation with custom library linking.

---

## 1. CLI Commands (Cargo-style)

```bash
# Initialize a new project with template
python pengu_project.py init <name> [--type <exe|c|obj|static|shared>] [--links lib1,lib2]

# Create from a template (template-first `init`)
python pengu_project.py new <exe|cli|pengu-lib|cbind> <name>

# Build in default debug profile
python pengu_project.py build

# Build optimized release profile
python pengu_project.py build --profile release

# Build and immediately execute the output executable
python pengu_project.py run [--profile release]

# Clean build directory and intermediate files
python pengu_project.py clean
```

### Initializing Projects by Type

| Target Type | Command | Generated Template in `main.pengu` |
|---|---|---|
| `exe` | `python pengu_project.py init my_game --type exe` | Standalone app with `weave main into void:` |
| `static` | `python pengu_project.py init my_lib --type static --links m,pthread` | Static library with exported mathematical / utility functions |
| `shared` | `python pengu_project.py init my_plugin --type shared` | Dynamic library (`.dll` / `.so` / `.dylib`) |
| `obj` | `python pengu_project.py init my_obj --type obj` | Single object file (`.o`) |
| `c` | `python pengu_project.py init my_bundle --type c` | Pure C bundle generation without C compilation |

Project *templates* are chosen with `--template <exe|cli|pengu-lib|cbind>` (or the
template-first `pengu new <template> <name>`). `pengu init --template lib` is a
deprecated alias for `pengu-lib` and prints a notice.

### Templates

| Template | Command | What it creates | Use it for |
|---|---|---|---|
| `exe` | `pengu init my_game` | `src/main.pengu` hello-world (`weave main into void:`) | Default standalone program |
| `cli` | `pengu init my_tool --template cli` | `src/main.pengu` with a `std.invoke` argument parser | Command-line tools |
| `pengu-lib` | `pengu init my_lib --template pengu-lib` | `pengu/my_lib.pengu` with inline `test` blocks; `entry`/`src_dir` point at `pengu/` | Pure PenguScript libraries consumable with `pengu add` |
| `cbind` | `pengu init pengu_raylib --template cbind` | `pengu/raylib.d.pengu`, `include/raylib.h`, `c/raylib.c`, `lib/`, `build.pengu` | Bindings to a native C library |

`pengu-lib` and `cbind` repositories are laid out exactly the way
`pengu add` standardises a dependency (`pengu/`, `include/`, `c/`, `lib/`), so
installing one into a consumer moves nothing and leaves no duplicate module
behind. `cbind` ships a toy C library that compiles out of the box; replace
`c/<name>.c` and `include/<name>.h` with the real library and let `build.pengu`
fetch/compile it. The `link "..."` statements in `pengu/<name>.d.pengu`
propagate to the consumer's link line automatically.

Both templates now emit `build.pengu` (a PenguScript script compiled by the
toolchain), not `build.py`. Run it manually with `pengu run build.pengu`, or
`pengu run build.pengu -- --force` to rebuild. `pengu add --trust` and
`pengu update --trust` run it automatically.

See [BINDINGS.md](BINDINGS.md) for the full binding contract, the discovery
order and the migration table from `build.py`.

### Dependency builds: `pengu add` / `pengu update`

| Command | Behaviour |
|---|---|
| `pengu add <url> --trust` | Installs the dependency and runs its `build.pengu` (or a legacy build script). A fresh clone does **not** force a rebuild. |
| `pengu add <url> --trust --rebuild` | Same, but passes `--force` to the build script. |
| `pengu add <url> --trust --no-build` | Installs without running any build script. |
| `pengu update --trust` | Pulls every dependency and re-runs its build script **with `--force`**, because the pull may have changed native sources. |
| `pengu update --trust --no-build` | Pulls only; never runs a build script. |

Re-adding an already-installed Git dependency also forces a rebuild when its
`git pull` succeeds. The build script is discovered in this order:
`build.pengu` > `build.py` > `build.bat`/`build.sh` > `Makefile`; the legacy
forms print a deprecation note and stop working in 3.0.0.

`build.pengu` is executed through the CLI itself. If the CLI is not on `PATH`
(CI, a relocated install), set `PENGU_BIN=/path/to/pengu`; if
`libpengu_runtime.a` is missing, the toolchain prints the
`python build_runtime.py` hint and skips the build instead of failing inside a
nested `pengu run`.

### Non-empty directories

`pengu init` (and `pengu new`) refuse to write into an existing non-empty
directory, so a typo in the project name cannot overwrite an existing project.
Pass `--force` (alias `-f`) to write into it anyway: `--force` adds the template
files but never deletes what is already there.

---

## 1.1 Performance: caches, TCC, DCE y PCH

`pengu run` está optimizado para sentirse como ejecutar un script (ver
`docs/PERFORMANCE.md` para el diseño completo y las mediciones):

| Mecanismo | Qué hace | Cómo desactivarlo |
| --------- | -------- | ----------------- |
| Caché del parser | Serializa las tablas LALR de Lark en `~/.cache/pengu/parser/` (≈3 s → ≈0.26 s por arranque) | `PENGU_CACHE=0` |
| Caché de binarios | Guarda el binario final por *hash de contenido* en `~/.cache/pengu/scripts/<clave>/app` (`app.exe` en Windows) | `--no-cache`, `--ephemeral` |
| Caché del grafo de imports | Reutiliza la lista de módulos validando el digest de cada uno | `PENGU_CACHE=0` |
| TCC | Compilador preferido para `pengu run` si está disponible (empaquetado en los releases); ~19 ms por bundle frente a ~400 ms de gcc | `PENGU_NO_TCC=1`, `PENGU_DEV_CC=gcc` |
| Flags de desarrollo | `-g0 -fno-plt -pipe -fno-ident -fno-asynchronous-unwind-tables` en el perfil `debug` de `pengu run` | `pengu build --profile release` |
| DCE | Elimina las funciones de `std/`/`lib/` no alcanzables con una pasada exacta por símbolos C (924 → 96 líneas / 42,9 → 3,7 KB en `hello.pengu`, -91%); las instancias genéricas y los helpers derivados no alcanzables ya no se emiten. `bundle.c` lleva `/* Dead-code elimination: pruned N of M … */` y `pengu time` imprime el nº podado. `--prune-types` añade la poda opt-in de tipos/constantes | `--no-dce`, `PENGU_NO_DCE=1` |
| PCH | Precompila `pengu_runtime.h`; `build_runtime.py` deja uno compartido en `build/include/pengu_runtime.h.gch` y los releases lo empaquetan (opt-in: `--pch`, sin ganancia medible: ver `docs/PERFORMANCE.md` §7) | `--pch` lo activa, `--no-pch` lo fuerza a off |
| Memoización de `pkg-config` | Una sonda por paquete y proceso en vez de ~12 (~320 ms → 201 ms por build) | — (siempre activa; los paquetes que se sondeaban eran bibliotecas externas, hoy repos satélite, así que un build estándar no sondea nada) |

Directorios de caché: `~/.cache/pengu` (Linux/XDG), `~/Library/Caches/pengu`
(macOS), `%LOCALAPPDATA%\pengu` (Windows). `PENGU_CACHE_DIR` lo reubica y
`pengu gc` lo limpia. Si el directorio es de solo lectura se usa un temporal.

Comandos nuevos: `pengu doctor`, `pengu gc`, `pengu expand`, `pengu time`,
`pengu eval`, `pengu watch`.

### 1.2 Referencia de flags nuevos

Flags globales (todos los subcomandos):

| Flag | Efecto |
| ---- | ------ |
| `--quiet` / `-q` | Silencia el banner de progreso (`Scripting…`, `Finished…`); los errores siguen en stderr |
| `--no-color` | Desactiva el color ANSI (también `NO_COLOR=1` en el entorno) |
| `--verbose` / `-v` | Orden de módulos, comandos C exactos, métricas DCE y tiempos de fase |

`pengu run <script.pengu>` y `pengu build`:

| Flag | Efecto |
| ---- | ------ |
| `--keep` | Compila en `build/<nombre>_run/` y conserva `bundle.c` + binario (fuerza rebuild) |
| `--no-cache` | Ignora la caché de binarios de esta ejecución (ni lee ni escribe) |
| `--clear-cache` | Vacía la caché de scripts antes de ejecutar (alias de `pengu gc --all`) |
| `--ephemeral` | Construye en un temporal y **no** puebla la caché (ideal para CI) |
| `--pch` | Activa el header precompilado de `pengu_runtime.h` (gcc/clang) |
| `--no-pch` | Fuerza el PCH a off (ya es el valor por defecto en `run`) |
| `--no-dce` | Emite todos los weaves de `std/`/`lib/` (desactiva DCE) |
| `--prune-types` | Opt-in: poda también tipos y constantes que ningún C emitido nombra (respeta `--test`, librerías y `--no-dce`) |
| `--no-line-markers` | Omite las directivas `#line` de `bundle.c` (≈4–26 % menos; los errores C apuntan al bundle). También `PENGU_NO_LINE_MARKERS=1` |
| `--dce-scope=user` | Opt-in: poda también los `weave` no usados de módulos de proyecto (`src/`), conservando `main`, `@export`, bindings `.d.pengu` y lo referenciado por `c/`. Alias `--tree-shake-user`; por defecto `std` |
| `--prune-native` | Opt-in: poda includes/`link`/`ldflag` de módulos que ningún `weave` vivo, símbolo C ni glue de `c/` usa. También `PENGU_PRUNE_NATIVE=1` |
| `--` | Todo lo que sigue se pasa al script (`std.rites.get_args`) |

`pengu run` acepta además `--cc` (sustituye al compilador de desarrollo; con
`PENGU_DEV_CC` se puede forzar `gcc` puntualmente) y `pengu build` acepta
`--pch`, `--no-dce` y `-D/--define`. `--pch`/`--no-pch`/`--no-dce` se aplican
tanto a `pengu run script.pengu` como a `pengu run` sin script (modo proyecto):
ambos acaban en el mismo `build_project`.

### 1.3 Distribución de TinyCC en los releases

`make_release.py` empaqueta TinyCC en los tres sistemas operativos como
best-effort (si falla, el release se publica igual y el toolchain cae a
gcc/clang):

* Linux/macOS: `pengu_tcc.ensure_tcc()` clona y compila TinyCC desde fuente
  (`./configure --prefix=… && make && make install`). El `dest_dir` se
  absolutiza antes de configurar: `make install` corre con `cwd=<src>`, así que
  un `--prefix` relativo (como el `build/tcc-dist` del workflow) acababa dentro
  del árbol de fuentes.
* Windows: descarga el binario precompilado de
  `FitzRoyX/tinycc` (`PENGU_TCC_URL` permite usar un mirror, `PENGU_TCC_SHA256`
  el digest) dentro de `build/tcc-dist`, y `make_release.py` lo añade con
  `--add-binary` **conservando el nombre original** (`tcc/tcc.exe` en Windows,
  `tcc/tcc` en Unix) para que `find_tcc()` lo encuentre; antes el destino estaba
  fijo a `tcc/tcc` y el bundle de Windows se quedaba sin compilador. El ZIP se
  verifica contra `pengu_tcc.TCC_RELEASE_SHA256` **antes** de extraerlo (Fase 9,
  items 9.2/9.3): un mismatch aborta el job, no lo convierte en un aviso.
* `.github/workflows/release.yml` hace el staging antes de `make_release.py`
  (`python pengu_tcc.py --stage build/tcc-dist --allow-missing`);
  `ensure_tcc()` detecta el TCC ya presente y no lo recompila en CI. El árbol de
  fuentes (`tinycc-src`, ~30 MB) se borra tras `make install` salvo que se defina
  `PENGU_KEEP_TCC_SRC`.
* **macOS (Fase 9, item 9.9): no hay notarización.** El workflow firma *ad-hoc*
  (`codesign --sign - --force`) el binario `pengu` y cualquier `tcc` suelto antes
  de empaquetar, y el gate real es `codesign --verify --strict` (la firma ad-hoc
  tiene que ser válida). Lo que **no** se afirma: que el artefacto pase
  `spctl --assess`. Sin una cuenta de desarrollador de Apple no hay
  `notarytool`, y Gatekeeper rechaza cualquier binario descargado (con el
  atributo de cuarentena) que no esté notarizado. La salida medida de
  `spctl --assess -vv` se publica en el log del job `verify` de `release.yml`; el camino
  soportado es `xattr -d com.apple.quarantine pengu` o compilar desde fuentes.
  Ver `docs/RELEASE.md` §macOS.

En runtime `pengu_tcc.find_tcc()` busca en este orden:
`<bundle>/tcc/tcc(.exe)` (PyInstaller `sys._MEIPASS`), el mismo sin sufijo (releases
antiguos), `<exe_dir>/tcc/tcc(.exe)` (instalación portable con TCC junto a `pengu`),
`<checkout>/tcc*`, el staging `build/tcc-dist[/tcc-dist]/bin/tcc`, `$PENGU_TCC` y `PATH`.
`PENGU_NO_TCC=1` desactiva TCC por completo. `pengu doctor`
reporta la ruta y la versión de TCC, la del compilador C (`<cc> --version`) y la
ruta del PCH compartido; `pengu doctor --json` expone `cc_version`, `tcc`,
`tcc_version` y `pch`.

Si TCC (o cualquier `PENGU_DEV_CC`) falla al compilar, `PenguBuilder.compile()`
reintenta una vez con el compilador configurado del proyecto y lo avisa por
stderr (`development compiler failed; retrying with gcc`); la compilación nunca
muere por culpa de TCC. La línea de enlace de TCC **no** lleva
`-Wl,--start-group` (su driver de enlazado lo rechaza): sin eso, todos los builds
con TCC fallaban el enlace y caían a gcc, duplicando el tiempo de un cache miss.


### 1.4 CI multiplataforma, smoke test y *xfails* conocidos

Los tres workflows (`.github/workflows/ci.yml` y `release.yml`) ejecutan, en este
orden: build del runtime → **`python scripts/smoke.py`** → pytest (subconjunto
con `-x` y luego la suite completa con `--timeout=600`) → `make_release.py`.

`scripts/smoke.py` es un chequeo end-to-end barato que corre igual en Windows,
Linux y macOS y que la suite tarda en cubrir:

* `pengu doctor --json` encuentra compilador C con versión y sin problemas
  bloqueantes (TCC es opcional);
* `pengu run script.pengu` compila, cachea y ejecuta; el binario cacheado se
  llama `app` (`app.exe` en Windows) y **es ejecutable directamente** — un
  fichero sin extensión no arranca en Windows porque `CreateProcess` añade
  `.exe` al nombre de imagen;
* la segunda ejecución es un *cache hit* y no se crea `build/` en el CWD;
* `pengu expand` emite el marcador de DCE.

Tests que **no** pueden correr en todas las plataformas (y por eso se *skippean*
en lugar de fallar):

| Test / helper | Motivo | Comportamiento |
| ------------- | ------ | -------------- |
| `tests/leakcheck.c` (interponedor `LD_PRELOAD`) | Usa `<link.h>`/`dl_iterate_phdr`, `__libc_malloc` y `LD_PRELOAD`: solo glibc/ELF | `@requires_leakcheck` (marcador en `tests/conftest.py`); se ejecuta en Linux o donde haya `valgrind`, se salta en macOS/Windows. `PENGU_NO_LEAKCHECK=1` fuerza el salto |
| `tests/codegen/test_tcc_integration.py` | Necesita un TCC utilizable | `pytest.skip` a nivel de módulo si no hay TCC; el test "TCC compila el bundle" degrada a *skip* si el TCC empaquetado no compila en esa plataforma (el fallback a gcc ya está asertado) |
| `tests/codegen/test_tcc_integration.py::test_fallback_*` | Usan un stub `#!/bin/sh` | `skipif(os.name == "nt")`; el caso "compilador inexistente" (`PENGU_DEV_CC=pengu-no-such-compiler-xyz`) sí corre en Windows porque `subprocess` lanza `OSError` y el fallback lo captura |

**Fuga conocida del codegen (xfail).** Las suites de *leaks* destaparon un fallo
real: una temporal de string con dueño pasada como argumento a una llamada nunca
se libera (`calling spark.println with (n to string)` baja a
`spark_println((pengu_to_string(n)))` sin `pengu_banish_string`). Arreglarlo
requiere propiedad de temporales de expresión en el codegen (una funcionalidad,
no un parche), así que:

* `test_generics_no_memory_leaks[test_map_of_string_to_list]` y
  `test_string_composition_no_memory_leaks[leak_binary_interp]` son
  `xfail(strict=False)` (el marcado conservador del interponedor oculta el bloque
  en algunas pasadas: un fallo *flaky* pondría CI en rojo sin motivo);
* `test_call_argument_string_temporary_is_released` es un `xfail(strict=True)`
  determinista sobre el C generado: el día que se arregle el compilador, XPASSea
  y CI pedirá quitar los tres marcadores.

## 2. Configuration Files (`pengu.yaml` / `pengu.json` / `pengu.toml`)

The build manager automatically searches for:
1. `pengu.toml`
2. `pengu.yaml` / `pengu.yml`
3. `pengu.json`
4. `Pengu.toml`

### Example `pengu.yaml`
```yaml
project:
  name: "space_game"
  version: "0.1.0"
  entry: "main.pengu"
  output: "exe"        # Options: exe, c, obj, static, shared
  output_name: "space_game"

assets:
  dir: "assets"        # Directory containing asset files
  module: "arca"       # Generates src/arca.pengu
  embed: true          # true = embedded into .rodata, false = runtime disk reader
  exclude: ["*.psd"]   # Glob patterns to exclude

build:
  build_dir: "build"   # Isolated build directory for all artifacts
  includes: ["mylib.h"]        # headers shipped by an external binding (satellite repo)
  links: ["mylib", "m", "pthread"]
  lib_dirs: ["./lib"]
  include_dirs: ["./include"]
  cflags: ["-Wall", "-std=c11"]
  ldflags: []
  defines: ["MYLIB_STATIC"]
  cc: "gcc"

profiles:
  debug:
    cflags: ["-g", "-O0", "-Wall"]
    defines: ["DEBUG"]
  release:
    cflags: ["-O3", "-DNDEBUG"]
    defines: ["NDEBUG"]
```

---

## 3. Build Features

### 1. Build Directory Isolation
All build artifacts (`bundle.c`, `bundle.o`, `pengu_runtime.h`, `.exe`, `.a`, `.so`, `.dll`) are placed into `build_dir` (default: `build/`), keeping your root workspace clean.

### 2. Runtime Copying
`pengu_runtime.h` is automatically located and copied into the `build_dir`, ensuring `#include "pengu_runtime.h"` resolves reliably without needing manual include paths.

### 3. Embedded Assets (`arca`)
Projects can bundle binary and text assets directly into the output executable:
- `pengu assets` regenerates `src/arca.pengu` and `build/arca_assets.c`.
- `pengu assets --list` displays tracked files, sizes, and C identifiers.
- `pengu assets --force` forces regeneration ignoring content digests.
- Two modes: `embed: true` (compiles bytes into binary `.rodata`) and `embed: false` (lazy disk cache with `PENGU_ASSETS_DIR` override support).

### 4. Incremental Compilation Caching
If `bundle.c` is newer than all `.pengu` source modules, asset files, and the project configuration file, the builder skips unnecessary re-bundling and prints `Finished (cached)`. Changes to files in `assets/` automatically invalidate the compilation cache.

### 5. Profiles (`debug` / `release`)
- `debug`: Enables debugging symbols (`-g`, `-O0`) and define `DEBUG`.
- `release`: Enables aggressive optimization (`-O3`) and define `NDEBUG`.
- Switch profiles using `--profile release` or `-p release`.

### 5. Multi-Platform Targets
- **Windows**: Produces `.exe`, `.dll` (without `-fPIC`), `.lib` / `.a` (using `lib.exe` or `ar`).
- **Linux**: Produces executable ELF, `.so` (with `-fPIC -shared`), `.a` (with `ar rcs`).
- **macOS**: Produces executable Mach-O, `.dylib` (with `-dynamiclib`), `.a`.

---

## 4. Compilación Automatizada del Runtime Estático (`build_runtime.py`)

`build_runtime.py` compila el runtime de PenguScript (`pengu_parser/pengu_runtime.c` + `pengu_runtime.h`) en `build/lib/libpengu_runtime.a` y, además, cada `std_c/*.c` en su propio `build/lib/lib<name>.a` (hoy `std_c/re.c` → `libre.a`). El runtime es **autocontenido**: no necesita nada más allá de libc, libm y pthreads / hilos Win32. Las únicas bibliotecas C que se compilan aquí son las vendorizadas de `std_c/`, y son **smart-linked**: solo llegan a la línea de enlace de un programa que importe el módulo correspondiente. Las bibliotecas externas siguen viviendo en repositorios satélite que se instalan por proyecto con `pengu add` (ver `docs/EXTERNAL_MODULES.md`).

`build_runtime.py` también copia `std_c/*.h` a `build/include/`, de donde el layout portable y el FHS ya los recogen (`runtime/include/` e `include/pengu/`). Así un release congelado conserva `utf8.h` y `re.h` aunque el checkout no esté al lado del ejecutable.

La compilación es idempotente y rápida (**~1.4 s** con `--rebuild`): si `libpengu_runtime.a` ya existe y es más reciente que sus entradas, no se recompila.

### Ejecución

```bash
# Compilar el runtime estático (solo libpengu_runtime.a, sin descargas)
python build_runtime.py

# Forzar recompilación completa desde cero (~1.4 s)
python build_runtime.py --rebuild
```

`extern_manifest.py` conserva la infraestructura de descarga/hash con el `MANIFEST` **vacío**: este repositorio ya no la usa, pero los repositorios satélite la copian para empaquetar sus propias dependencias.

### Estructura Generada

```
build/
├── include/                 # Headers disponibles para el bundle
│   ├── pengu_runtime.h
│   ├── pengu_runtime.h.gch  # PCH compartido (gcc/clang, best effort)
│   ├── utf8.h               # copiado de std_c/ (std.lingua)
│   └── re.h                 # copiado de std_c/ (std.regulus)
├── obj_std_c/               # Objetos intermedios de std_c/
└── lib/                     # Bibliotecas estáticas generadas
    ├── libpengu_runtime.a   # Runtime de PenguScript
    └── libre.a              # std_c/re.c (tiny-regex-c)
```

Una compilación que importe `std.regulus` recibe `-Lbuild/lib -lre`; una que no
lo importe no recibe ni el flag ni la cabecera. El requisito se verifica en
`tests/build/test_smart_linking.py`.

El archivo lleva un objeto por subsistema (core y filum) compilado con `-ffunction-sections`, de modo que el enlazador solo incorpora lo que el programa referencia (ver `BENCHMARKS.md` §Binary size).

### Uso en Proyectos PenguScript

Para enlazar un proyecto con el runtime estático, añade `"pengu_runtime"` a la lista `links` en tu archivo de configuración:

```toml
# pengu.toml
[project]
name = "my_app"
entry = "main.pengu"
output = "exe"

[build]
links = ["pengu_runtime"]
lib_dirs = ["build/lib"]
include_dirs = ["build/include"]
```
El sistema de compilación (`pengu_project.py`) enlazará automáticamente `-lpengu_runtime` más las bibliotecas de sistema que el runtime necesita (`-lws2_32 -lwinmm` en Windows — kernel32/msvcrt las añade el driver de MinGW; `-pthread -lm -ldl` en Linux/Unix). Los archivos nativos de un binding externo los aporta el propio repositorio satélite a través de sus entradas explícitas en `links:`, no el runtime.

### Módulos en `std/`

El `std/` de este repositorio contiene **26 módulos puros** de PenguScript: `spark`, `scrolls`, `oracle`, `compass`, `archivum`, `cipher`, `chronicle`, `lot`, `arithmancy`, `rites`, `whisper`, `ward`, `trial`, `tally`, `atlas`, `coven`, `filum`, `fractio`, `integrum`, `littera`, `logica`, `numerus`, `loom`, `invoke`, `ffi` y `ledger`. Los bindings C externos (raylib, SQLite3, WebUI, miniaudio, …) **se movieron a repositorios satélite** y se instalan por proyecto con `pengu add`; consulta `docs/EXTERNAL_MODULES.md`.

`pengu bind` sigue disponible para generar archivos `.d.pengu` a partir de cualquier cabecera C, usando los stubs genéricos de `c_bind_stubs/` y verificando el resultado con `pengu check`.

---

## 5. Linux/macOS distribution layouts

PenguScript supports two release layouts; both are produced by `make_release.py`
and consumed transparently by `pengu`/`pengu.exe` via the `pengu_paths` module.

### Portable (`--layout portable`, default)

```
pengucc_build/
├── pengu                # binary
├── std/
└── runtime/
    ├── pengu_runtime.h
    ├── lib/*.a
    └── include/*.h
```

Copy anywhere and add to `PATH`. `pengu` looks for the runtime next to the
binary (`<exe_dir>/runtime/…`).

### FHS (`--layout fhs`, Linux/macOS)

```
pengucc_build/
├── bin/pengu
├── lib/pengu/*.a
├── include/pengu/*.h
├── share/pengu/std/
├── share/pengu/VERSION
├── install.sh
└── uninstall.sh
```

Install with:

```bash
./install.sh                            # ~/.local
PREFIX=/usr/local sudo ./install.sh     # /usr/local
DESTDIR=/tmp/stage PREFIX=/usr ./install.sh   # package-manager staging
```

At runtime the CLI derives its prefix from `sys.executable` (e.g.
`~/.local/bin/pengu` → prefix `~/.local`) and probes
`$PREFIX/{include,lib,share}/pengu`. Overrides: `PENGU_PREFIX`,
`PENGU_INCLUDE_DIR`, `PENGU_LIB_DIR`, `PENGU_STD_DIR`, `PENGU_VERSION_FILE`,
`PENGU_RUNTIME_HEADER`.



