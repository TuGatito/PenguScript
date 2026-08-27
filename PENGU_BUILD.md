# PenguScript v0.6 Build System & Package Manager

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

### 3. Incremental Compilation Caching
If `bundle.c` is newer than all `.pengu` source modules and the project configuration file, the builder skips unnecessary re-bundling and prints `Finished (cached)`.

### 4. Profiles (`debug` / `release`)
- `debug`: Enables debugging symbols (`-g`, `-O0`) and define `DEBUG`.
- `release`: Enables aggressive optimization (`-O3`) and define `NDEBUG`.
- Switch profiles using `--profile release` or `-p release`.

### 5. Multi-Platform Targets
- **Windows**: Produces `.exe`, `.dll` (without `-fPIC`), `.lib` / `.a` (using `lib.exe` or `ar`).
- **Linux**: Produces executable ELF, `.so` (with `-fPIC -shared`), `.a` (with `ar rcs`).
- **macOS**: Produces executable Mach-O, `.dylib` (with `-dynamiclib`), `.a`.

---

## 4. Compilación Automatizada del Runtime Estático (`build_runtime.py`)

PenguScript cuenta con un script de compilación automatizado e idempotente para compilar las bibliotecas externas (`PCRE2`, `libxml2`, `zlib`, `mbedtls`, `libcurl`, `libmicrohttpd`) y el runtime de PenguScript (`pengu_runtime.c`) como bibliotecas estáticas.

### Ejecución

```bash
# Compilar bibliotecas externas y runtime estático
python build_runtime.py

# Forzar recompilación completa desde cero
python build_runtime.py --rebuild
```

### Estructura Generada

```
build/
├── include/              # Headers de runtime y dependencias externas
│   ├── pcre2.h
│   ├── zlib.h
│   ├── zconf.h
│   ├── microhttpd.h
│   ├── libxml/           # Headers de libxml2
│   ├── mbedtls/          # Headers de mbedtls (MD5, SHA1, SHA256, SHA512)
│   ├── curl/             # Headers de libcurl
│   └── pengu_runtime.h
└── lib/                  # Bibliotecas estáticas generadas
    ├── libz.a            # zlib 1.3.2 (compresión zlib/gzip y CRC32)
    ├── libpcre2-8.a      # PCRE2 10.47 (8-bit regex para regulus)
    ├── libxml2.a         # libxml2 2.9.0 (XML/HTML para parchment)
    ├── libmbedcrypto.a   # mbedtls 4.2.0 (hashing criptográfico para seal)
    ├── libcurl.a         # curl 8.21.0 (cliente HTTP para precis)
    ├── libmicrohttpd.a   # libmicrohttpd 1.0.1 (servidor HTTP embebido para precis)
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
Junto con las bibliotecas de sistema necesarias (`-lws2_32 -lwinmm -ladvapi32 -lcrypt32 -lbcrypt` en Windows, `-pthread -lm` en Linux/Unix).


