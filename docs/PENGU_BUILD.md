# PenguScript v1.0.0-rc1 Build System & Package Manager

The PenguScript Build Manager (`pengu_project.py`) is a Cargo-style tool providing project initialization, module dependency resolution, C bundling, incremental compilation caching, debug/release profiles, and multi-target compilation with custom library linking.

---

## 1. CLI Commands (Cargo-style)

```bash
# Initialize a new project with template
python pengu_project.py init <name> [--type <exe|c|obj|static|shared>] [--links lib1,lib2]

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
| DCE | Elimina las funciones de `std/`/`lib/` no alcanzables (432 → 65 líneas en `hello.pengu`, -84%); `bundle.c` lleva `/* Dead-code elimination: pruned N of M … */` y `pengu time` imprime el nº podado | `--no-dce`, `PENGU_NO_DCE=1` |
| PCH | Precompila `pengu_runtime.h`; `build_runtime.py` deja uno compartido en `build/include/pengu_runtime.h.gch` y los releases lo empaquetan (opt-in: `--pch`, sin ganancia medible: ver `docs/PERFORMANCE.md` §7) | `--pch` lo activa, `--no-pch` lo fuerza a off |
| Memoización de `pkg-config` | Una sonda por paquete y proceso en vez de ~12 (~320 ms → 201 ms por build) | — (siempre activa) |

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
  `spctl --assess -vv` se publica en el log de `release-verify.yml`; el camino
  soportado es `xattr -d com.apple.quarantine pengu` o compilar desde fuentes.
  Ver `docs/RELEASE.md` §macOS.

En runtime `pengu_tcc.find_tcc()` busca en este orden:
`<bundle>/tcc/tcc(.exe)` (PyInstaller `sys._MEIPASS`), el mismo sin sufijo (releases
antiguos), `<checkout>/tcc*`, el staging `build/tcc-dist[/tcc-dist]/bin/tcc`,
`$PENGU_TCC` y `PATH`.
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
| `tests/test_tcc_integration.py` | Necesita un TCC utilizable | `pytest.skip` a nivel de módulo si no hay TCC; el test "TCC compila el bundle" degrada a *skip* si el TCC empaquetado no compila en esa plataforma (el fallback a gcc ya está asertado) |
| `tests/test_tcc_integration.py::test_fallback_*` | Usan un stub `#!/bin/sh` | `skipif(os.name == "nt")`; el caso "compilador inexistente" (`PENGU_DEV_CC=pengu-no-such-compiler-xyz`) sí corre en Windows porque `subprocess` lanza `OSError` y el fallback lo captura |

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
  includes: ["raylib.h"]
  links: ["raylib", "m", "pthread", "opengl32", "gdi32", "winmm"]
  lib_dirs: ["./lib"]
  include_dirs: ["./include"]
  cflags: ["-Wall", "-std=c11"]
  ldflags: []
  defines: ["PLATFORM_DESKTOP"]
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

PenguScript cuenta con un script de compilación automatizado e idempotente para compilar las bibliotecas externas (`PCRE2`, `libxml2`, `zlib`, `mbedtls`, `libcurl`, `libmicrohttpd`, **SQLite3**, **Raylib**, **WebUI**, y el paquete **single-header** `imago/scriptor/typis/pactum/datastructura/perlinum/nanosvg`) y el runtime de PenguScript (`pengu_runtime.c`) como bibliotecas estáticas.

### Ejecución

```bash
# Compilar bibliotecas externas y runtime estático
python build_runtime.py

# Forzar recompilación completa desde cero
python build_runtime.py --rebuild
```

`build_runtime.py` descarga automáticamente las fuentes externas (ver `extern_manifest.py`) y produce artefactos idempotentes: si la biblioteca ya existe no se recompila salvo con `--rebuild`. WebUI se instala desde el asset estático oficial de su release (los fuentes asumen la API UNICODE de MSVC y no compilan con mingw).

### Estructura Generada

```
build/
├── include/              # Headers de runtime y dependencias externas
│   ├── pcre2.h
│   ├── zlib.h
│   ├── zconf.h
│   ├── microhttpd.h
│   ├── webui.h           # WebUI
│   ├── raylib.h          # Raylib
│   ├── sqlite3.h         # SQLite3
│   ├── imago.h … perlinum.h   # STB latin-renamed single headers
│   ├── libxml/           # Headers de libxml2
│   ├── mbedtls/          # Headers de mbedtls (MD5, SHA1, SHA256, SHA512)
│   ├── curl/             # Headers de libcurl
│   └── pengu_runtime.h
│   └── pengu_runtime.h.gch  # PCH compartido (gcc/clang) para builds rápidos
└── lib/                  # Bibliotecas estáticas generadas
    ├── libz.a            # zlib 1.3.2 (compresión zlib/gzip y CRC32)
    ├── libpcre2-8.a      # PCRE2 10.47 (8-bit regex para regulus)
    ├── libxml2.a         # libxml2 2.9.0 (XML/HTML para parchment)
    ├── libmbedcrypto.a   # mbedtls 4.2.0 (hashing criptográfico para seal)
    ├── libcurl.a         # curl 8.21.0 (cliente HTTP para precis)
    ├── libmicrohttpd.a   # libmicrohttpd 1.0.1 (servidor HTTP embebido para precis)
    ├── libsqlite3.a      # SQLite3 3.53.4 (base de datos SQL embebida)
    ├── libraylib.a       # Raylib 6.0 (gráficos/audio, desktop OpenGL 3.3)
    ├── libwebui.a        # WebUI 2.5.0-beta.3 (interfaces web nativas)
    ├── libpengu_stb.a    # single-headers STB latin + nanosvg (imago, typis, ...)
    └── libpengu_runtime.a # Runtime de PenguScript
```

### Uso en Proyectos PenguScript

Para enlazar un proyecto con el runtime estático y sus motores externos, añade `"pengu_runtime"` a la lista `links` en tu archivo de configuración:

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
El sistema de compilación (`pengu_project.py`) enlazará automáticamente:
`-lpengu_runtime -lpcre2-8 -lxml2 -lcurl -lmbedcrypto -lmicrohttpd -lz`
y auto-detecta en `build/lib` los archivos estáticos adicionales (`-lsqlite3 -lraylib -lwebui -lpengu_stb`) a medida que existan. Junto con las bibliotecas de sistema necesarias (`-lws2_32 -lwinmm -ladvapi32 -lcrypt32 -lbcrypt -lopengl32 -lgdi32 -lole32 -luuid -lshell32` en Windows, `-pthread -lm` en Linux/Unix).

### Bindings disponibles en `std/`

`import std.sqlite3`, `import std.raylib`, `import std.webui`, `import std.imago`,
`std.scriptor`, `std.typis`, `std.pactum`, `std.datastructura`, `std.perlinum`,
`std.nanosvg` y `std.nanosvgrast` declaran el surface C nativo (`.d.pengu`),
generado con `pengu bind` y verificado con `pengu check`.

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



