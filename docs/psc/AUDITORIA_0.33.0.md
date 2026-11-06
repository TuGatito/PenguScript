# Auditoría técnica de PenguScript 0.32.0 → 0.33.0

**Fecha:** 2026-11-05
**Repositorio:** `TuGatito/PenguScript` (rama `main`, commit `bdd2023`)
**Compilador auditado:** `psc 0.32.0 (F13)` (auto-hospedado, `src/psc/**/*.pengu`, 50.913 líneas)
**Entorno de medición:** Linux 7.3.1 x86_64 (CachyOS), GCC 16.2.1, Node v26.13.0,
Emscripten 6.0.13-git, 36 núcleos, 31 GB RAM.
**Alcance:** auditoría de solo lectura. No se modificó código fuente; los logs y
reproducciones viven en `scratch/` y `/tmp/`.

---

## 0. Resumen ejecutivo

PenguScript 0.32.0 es un compilador **funcional y con una base de pruebas sólida**
(118 archivos de prueba + 19 regresiones verdes), pero su **caché de build es
incorrecta** (puede servir binarios obsoletos), su **build en caliente tarda ~30 s**
en el propio compilador, y tres funciones de la lista (debugger, cobertura,
cross-compile nativo) **no existen todavía**. El resto son mejoras parciales o
deuda de documentación.

Veredicto corto:

| Área | ¿Es posible? | Esfuerzo | Riesgo |
|---|---|---|---|
| 3 bugs abiertos | ✅ Sí, causas localizadas | 2–3 d | Bajo |
| Build incremental (<2 s en caliente) | ✅ Sí para no-op; ⚠️ por módulo real | 4–5 d + 10–15 d | Medio |
| Paralelismo de codegen | ⚠️ Sí, pero exige partir la TU única | 8–12 d | Alto |
| Cross-compile nativo | ⚠️ Sí con tabla de toolchains y CI | 5–7 d | Medio |
| Debugger (DWARF, breakpoints, fibras) | ⚠️ MVP con gdb/lldb sí; DAP completo no | 5–8 d | Medio |
| LSP (rename, definición, diagnósticos) | ✅ Sí; rename cruzado está roto | 3–4 d | Bajo |
| Cobertura (`psc test --coverage`) | ✅ Verificado con gcov + `#line` | 3–4 d | Bajo |
| Sanitizers (ASan/UBSan/TSan) | ✅ Sí; faltan perfiles y flags en la clave | 2–3 d | Bajo |
| Reproducible (`--frozen`, fechas) | ✅ Casi hecho; falta `-g` reproducible y CI | 2–3 d | Bajo |
| Rendimiento del compilador | ✅ Medido; hay margen 2–3× | 5–7 d | Medio |

**Recomendación de release:** publicar **0.33.0** con los bugs, la caché
correcta, LSP, cobertura, sanitizers, reproducibilidad, documentación y README
nuevo (≈22–28 días-persona). Dejar cross-compile nativo, debugger y
paralelismo/incremental por módulo para **0.34.0 / 0.35.0**, porque tocan el
modelo de compilación (TU única) y no deben bloquear el release de calidad.

> Los “3 bugs conocidos” no aparecen como issues en GitHub (el repositorio tiene
> 20 PRs y 0 issues abiertos). En esta auditoría se identifican y reproducen tres
> fallos de release-blocker, más un conjunto de defectos secundarios. Si el
> equipo tenía otra lista de 3, hay que contrastarla antes de F1.

---

## 1. Método

1. Baseline limpio: `tests/run.sh`, `tests/regress.sh`, `fmt --check`,
   `gen_stage0.sh --check` y `docs` (los tres últimos vía CI local cuando aplica).
2. Medición de fases con `psc build`, `psc check` y `psc expand` (codegen puro),
   más `gcc -c` del bundle para separar backend C.
3. Reproducciones mínimas en `/tmp` para cada sospecha (caché, target, run,
   LSP, cobertura, sanitizers, reproducibilidad).
4. Lectura del código relevante (`driver/build.pengu`, `cache`, `runner`,
   `target`, `cmd/*`, `lsp/server.pengu`) para confirmar causa raíz y líneas.
5. Prueba de escalado de codegen con proyectos sintéticos de 100–800 funciones.
6. Verificación de que las herramientas externas necesarias existen
   (`gcov`, `node`, `emcc`, `gdb`, `gprof`); `perf`, `valgrind`, `strace` y
   `/usr/bin/time` **no** están instalados en esta máquina.

### 1.1 Baseline

```
PSC=./build/psc ./tests/run.sh      → OK 118 PSC test file(s) + thread ownership, exit 0
bash ./tests/regress.sh             → 19/19 OK, exit 0
```

Logs: `scratch/audit-baseline-run.log`, `scratch/audit-baseline-regress.log`.
El árbol estaba limpio antes de la auditoría; no se cambió ningún `.pengu`.

### 1.2 Tiempos medidos (build del propio compilador)

| Operación | Tiempo | Qué incluye |
|---|---:|---|
| `psc build .` (caliente) | 30,3–31,3 s | sema + codegen + cc + hash de caché |
| `psc check .` | 3,6 s | solo sema |
| `psc expand . --out=...` | 22,0–22,7 s | sema + codegen, sin cc (bundle de 5.107.477 B) |
| `gcc -O0 -g -c build/bundle.c` | 5,5 s | backend C de una TU |
| `psc build . --no-dce` | 31,0 s | DCE no es el cuello |
| `psc build . --no-line-markers` | 29,3 s | `#line` no es el cuello |
| `psc build . --prune-types` | 28,1 s | poda de tipos no es el cuello |
| `psc build .` con caché “hit” (copia a `/tmp`) | 24,7–25,1 s | **sigue pagando sema+codegen** |

Descomposición aproximada: **codegen ≈ 18,4 s (60 %)**, sema ≈ 3,6 s (12 %),
cc ≈ 5,5 s (18 %), hash/overhead ≈ 2 s (7 %). El objetivo de < 2 s en caliente
es alcanzable **solo** si el acierto de caché ocurre antes de sema y codegen.

### 1.3 Escalado del codegen

Proyecto sintético con N funciones triviales, `psc expand`:

| N | Tiempo | Salida |
|---:|---:|---:|
| 100 | 41 ms | 17.726 B |
| 200 | 59 ms | 33.426 B |
| 400 | 115 ms | 64.975 B |
| 800 | 305 ms | 128.575 B |

Crecimiento casi lineal (2,4× al duplicar en el tramo alto), no hay una
cuadrática evidente en el emisor. El bundle real de 5,1 MB tarda ~18 s
(≈3,5 s/MB), así que el coste dominante es **constante por byte** (asignaciones,
copias de strings, `#line`, tabla de símbolos), no un bucle O(n²) global.

---

## 2. Estado de la lista solicitada

### 2.1 Bugs abiertos / release-blockers

| ID | Título | Estado | Evidencia |
|---|---|---|---|
| **B-01** | `psc run` ignora el `target` del manifiesto | Reproducido | `psc run .` en proyecto wasm → exit 127 sin diagnóstico |
| **B-02** | `psc run` enmascara el exit code de wasm | Reproducido | `psc run . --target wasm` → 0 aunque `main` devuelve 3 |
| **B-03** | La caché sirve artefactos obsoletos | Reproducido | cambiar `cflags` no invalida; `build/` participa en la clave |

Estos tres deben cerrarse con tests y un **gate de release** antes de publicar.

### 2.2 Lista original

| # | Ítem | Estado real | ¿Posible? |
|---:|---|---|---|
| 1 | Cerrar 3 bugs con tests | Causas localizadas; hay 3 blockers reales | ✅ |
| 2 | Build incremental, caché por módulo/hash, <2 s caliente | Caché solo de artefacto final; se consulta **después** de sema+codegen; clave incompleta | ✅ no-op; ⚠️ por módulo |
| 3 | Paralelismo: codegen por módulo | Una sola TU (`bundle.c`), un solo `cc`; sin hilos en el driver | ⚠️ requiere partir TU |
| 4 | Cross-compile: `target` en `pengu.toml`, Linux/macOS ARM | `[build] target` solo acepta host o wasm; nativo rechazado explícitamente | ⚠️ sí con toolchains |
| 5 | Debugger: DWARF, breakpoints, stacks de fibras | No existe; sin `-g` por defecto en proyectos de usuario | ⚠️ MVP gdb/lldb |
| 6 | LSP: completar rename, ir a definición, diagnósticos | Hover/definición/diagnósticos funcionan; **rename y references cruzados rotos** | ✅ |
| 7 | Cobertura `psc test --coverage` con mapa a `.pengu` | Flag inexistente; gcov ya mapea a `.pengu` vía `#line` | ✅ |
| 8 | Sanitizers ASan/UBSan/TSan documentados | Flags manuales vía manifiesto; sin perfiles ni flag; caché puede saltarlos | ✅ |
| 9 | Reproducible: `--frozen`, fechas, `SOURCE_DATE_EPOCH` | `--frozen` solo para deps; binarios idénticos sin `-g`; con `-g` difieren por rutas | ✅ |
| 10 | Rendimiento del compilador | Medido: 30 s; codegen domina | ✅ margen 2–3× |

---

## 3. Bugs: evidencia, causa y reparación

### B-01 — `psc run` ignora el target resuelto del manifiesto

**Reproducción**

```bash
mkdir -p /tmp/edge/src && cd /tmp/edge
cat > pengu.toml <<'EOF'
[project]
name = "edge"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
[build]
build_dir = "build"
target = "wasm32-unknown-emscripten"
EOF
cat > src/main.pengu <<'EOF'
weave main into int:
    return 3
EOF
/home/tugatito/Documentos/GitHub/PenguScript/build/psc build .
/home/tugatito/Documentos/GitHub/PenguScript/build/psc run .          # exit 127
node build/app.js                                                      # exit 3
```

Salida observada: `psc run .` termina con **127** y **ningún diagnóstico**.
`proc.run_argv` usa `_exit(127)` cuando `execvp` falla, y el artefacto es
`build/app.html`, que no es ejecutable nativo.

**Causa**

- `driver.build` resuelve el target del manifiesto internamente
  (`src/psc/driver/build.pengu:354-355`) pero `BuildResult` **no transporta el
  target resuelto**.
- `psc run` llama a `runner.run` con `o.platform`, que sigue siendo el host
  (`src/psc/cmd/build.pengu:486`; ídem `src/psc/cmd/test.pengu:158`).
- El runner decide “nativo vs wasm” con ese target equivocado y ejecuta el HTML.

**Reparación**

1. Añadir `target` (triple, `is_wasm`, `js_path`) a `driver.BuildResult` y
   rellenarlo en `build()`; liberar en `free_result`.
2. En `cmd/build.pengu` y `cmd/test.pengu`, usar `r.target` para `runner.run`,
   no `o.platform`.
3. Si el target es wasm y el artefacto es `.html`, ejecutar `build/app.js`
   con Node por defecto; si Node no existe, error accionable (nunca 127 mudo).
4. Test de regresión: proyecto wasm con `main` devolviendo 3; `psc run .` debe
   devolver 3, y `psc run . --target wasm` idéntico.

**Archivos:** `src/psc/driver/build.pengu`, `src/psc/driver/runner.pengu`,
`src/psc/cmd/build.pengu`, `src/psc/cmd/test.pengu`.

---

### B-02 — El fallback a navegador enmascara fallos del programa wasm

**Reproducción**

```bash
cd /tmp/edge
/home/tugatito/Documentos/GitHub/PenguScript/build/psc run . --target wasm
echo $?     # 0  ← incorrecto: main devuelve 3
node build/app.js; echo $?   # 3
```

**Causa**

`src/psc/driver/runner.pengu:207-211`:

```
if t.is_wasm and code != 0 and not browser:
    var chrome as maybe string is calling chromium_path
    if chrome.is_present:
        return calling run_browser with artifact
```

Cualquier código de salida distinto de 0 (incluido el 3 del programa) dispara
Chromium headless; Chromium carga la página y devuelve 0. El resultado del
programa se pierde y el test/CI queda verde falsamente.

**Reparación**

- Distinguir **fallo de ejecución** (Node ausente, `ENOENT`, 126/127) de
  **código de salida del programa**. Solo el primero puede caer al navegador,
  y únicamente con `--browser` explícito o una opción `--wasm-runner=auto`.
- Propagar siempre el código de Node; imprimir stderr de Node si falla.
- `--browser` debe ser opt-in y documentado; el navegador no puede devolver el
  exit code del programa, así que para tests/CI el runner por defecto es Node.
- Test: `main` devuelve 3 → `psc run` y `psc test` devuelven 3; Node ausente →
  error claro, no 0.

**Archivos:** `src/psc/driver/runner.pengu`, `src/psc/cmd/build.pengu`,
`src/psc/cmd/test.pengu`, `docs/WASM.md`.

---

### B-03 — Clave de caché incompleta y artefacto obsoleto

**Evidencia 1 (flags no invalidan).** Proyecto `/tmp/cflagbug2`:

```bash
# tras 2 builds de calentamiento, la caché acierta (cc=0)
sed -i 's/"-O2", "-DSENTINEL_X=1"/"-O2", "-DSENTINEL_X=1", "-DANOTHER_Y=2"/' pengu.toml
psc build . --verbose | grep -c '^cc:'     # 0  ← acierto de caché
psc build . --verbose | grep -o 'ANOTHER_Y=2'   # vacío ← flag inexistente en el binario
```

La clave (`src/psc/driver/build.pengu:718-790`) incluye `o.defines`,
`man.defines`, `man.ldflags`, `ldflags` del programa, el hash del compilador,
triple, cc, perfil, flags booleanos, módulos y hashes de directorios. **No
incluye**:

- `man.cflags` / `tc.cflags` (optimización, `-g`, `-fsanitize=*`, `--coverage`);
- `man.links` (`-l...`) ni `man.lib_dirs` (`-L...`);
- flags de entorno que el toolchain pueda añadir (si existen);
- el contenido de `assets_dir` (si `assets.embed`) y archivos JS/HTML del shell wasm, si existen.

Consecuencia: cambiar `[build] cflags` o `[profiles.*] cflags` **no reconstruye**
y se ejecuta el binario viejo. Esto invalida también los perfiles de sanitizers
y cobertura (F4): el flag llega a `cc` solo cuando la clave falla por otra razón.

**Evidencia 2 (`build/` invalida).** `push_dir_hashes`
(`src/psc/driver/build.pengu:124-138`) recorre todos los archivos de cada
`include_dir`; entre ellos está el `build_dir` del proyecto (aparece como
`-I.../build`). En `/tmp/cachebug`, el conteo de entradas pasó de 7801 → 7802
al crear `build/unrelated.txt` y → 7803 al borrarlo. Cualquier salida del build
(artefacto, `.o`, logs) cambia la clave; el warm-up necesita **dos** builds
(la primera escribe `bundle.c` antes de calcular la clave) y el artefacto de la
segunda cambia la clave de la tercera.

**Evidencia 3 (ETXTBSY y `put` silencioso).** Al reconstruir el propio
compilador, el artefacto es `build/psc`, que está en ejecución. En un acierto,
`archivum.copy_file(hit, artifact)` falla con `ETXTBSY`; el código ignora el
fallo y recompila. `cache.put` se ejecuta igual (`src/psc/driver/build.pengu:1012`)
y su resultado se descarta (`var storedx`). El conteo de entradas queda estable
pero **siempre se paga el build completo**.

**Evidencia 4 (orden no determinista).** `push_dir_hashes` no ordena la lista de
archivos; el orden de `readdir` puede variar entre sistemas/FS. Dos builds
idénticos pueden producir claves distintas.

**Reparación (F1)**

1. Calcular la clave **antes** de sema/codegen: en `build()`, tras cargar
   manifiesto/módulos/toolchain y antes de `sema_api.check_file` (línea 511).
   El bundle no debe formar parte de la clave.
2. Incluir en `cparts`: `man.cflags`, `tc.cflags` (en orden), `man.links`,
   `man.lib_dirs`, `man.assets_*`, rutas/contenido de assets y cualquier
   variable de entorno que el driver lea para flags.
3. Excluir el `build_dir` y directorios generados de `push_dir_hashes`; hashear
   solo `c_dir`, `include_dir` y `include_dirs` de dependencias, **ordenando**
   las rutas antes de hashear.
4. Subir la versión de formato de clave (`"psc-0.9.0"`), porque cambia el
   significado; las entradas viejas deben quedar huérfanas (y `psc gc` las
   limpia).
5. Instalación atómica del artefacto: copiar a `<artifact>.tmp.<pid>` en el
   mismo directorio y `rename()` sobre el destino. En Linux reemplaza un
   binario en ejecución sin `ETXTBSY`; en Windows, fallback a “no copiar”.
   Nunca ignorar el resultado de `put`: si falla, avisar con `--verbose` y
   seguir (el build ya es correcto).
6. Cachear también wasm cuando el artefacto sea multiarchivo (`.html`, `.js`,
   `.wasm`) o deshabilitarlo explícitamente con un comentario; hoy
   `not (eff.is_wasm and out_kind == "exe")` lo desactiva siempre.
7. Añadir `psc gc` automático opcional (tamaño máximo configurable,
   `PSC_CACHE_MAX_MB`) y documentar que la caché puede crecer a GB.

**Aceptación F1**

- No-op en el repo: `psc build .` ≤ 2 s (objetivo ≤ 0,5 s) sin `cc:` y sin
  reescribir `bundle.c`.
- Matriz de invalidación (12 casos): cambiar `cflags`, `-l`, `-L`, define,
  header en `c_dir`, header en `include_dir`, target, perfil, `--release-unsafe`,
  `--no-dce`, fuente de módulo, compilador → **miss**; no cambiar nada → **hit**.
- Crear/borrar un archivo en `build/` **no** cambia la clave.
- `psc build .` dos veces con el binario en ejecución no falla y acierta en la
  segunda.
- Tests en `tests/regress_cache_*.sh` (nuevos) + job CI.

---

### B-04 — Rename y references del LSP cruzados están rotos

**Reproducción** (`/tmp/lsp-ren`, dos documentos abiertos: `src/helper.pengu`
define `weave twice`, `src/main.pengu` importa y llama `twice`):

- rename en la llamada (`main.pengu`, línea 3, columna 25) → devuelve cambios
  **solo para `helper.pengu`**, falta `main.pengu`.
- rename en la definición (`helper.pengu`, línea 2, columna 7) → `null`.
- rename en otra posición de `main.pengu` → `null`.

**Causa**

`src/psc/lsp/server.pengu:1693-1753` obtiene el `sid` del documento actual y
luego, para cada documento abierto, crea **otro** `SemaProgram` (`doc_sema`) y
compara `query.symbol_at_offset(...) == sid`. Los `symbol id` son índices
**por programa**: el mismo símbolo en dos programas tiene ids distintos, así que
la comparación falla. El mismo patrón aparece en `handle_references`
(`src/psc/lsp/server.pengu:1494+`), por lo que “references across open documents”
tampoco es fiable.

`docs/LSP.md` afirma que rename es “Symbol-safe ... limited to open documents”;
con dos documentos abiertos ya falla, así que la documentación también está
desactualizada.

**Reparación (F3)**

- Introducir una identidad de símbolo **estable entre programas**:
  `(module_path, decl_kind, qualified_name, local_scope)` o un índice de
  workspace que cargue los módulos una vez y comparta el `SemaProgram` para los
  documentos abiertos (preferible).
- Rename: localizar la declaración canónica, recorrer todos los documentos
  abiertos y renombrar ocurrencias cuyo `symbol_at_offset` resuelva a la misma
  identidad estable; incluir el identificador de import si se renombra el
  export.
- References/highlight: misma identidad; `includeDeclaration` correcto.
- Añadir tests de ida y vuelta: rename en definición y en uso, dos y tres
  archivos, colisión de nombres en módulos distintos, rename de campo/método.
- `serverInfo.version` debe salir de una constante única (hoy literal
  `"0.32.0"` en `src/psc/lsp/server.pengu:411`; el script de bump lo edita,
  pero es frágil).

**Aceptación:** los tres escenarios devuelven `WorkspaceEdit` completo; el
documento se guarda y `psc check` sigue verde; `tests/lsp/run_lsp_tests.py`
incluye rename round-trip y references cruzados.

---

### B-05 — Los builds de usuario no llevan DWARF por defecto

**Evidencia**

```bash
cd /tmp/rep-a && psc build . && readelf -S build/app | grep -c debug
# 0 secciones .debug_* (proyecto sin [profiles.debug])
```

El repo sí define `[profiles.debug] cflags=["-g","-O0","-Wall"]` en su
`pengu.toml`; un proyecto creado con `psc init` no. El perfil `debug` por
defecto no añade `-g`, así que gdb/lldb no pueden mostrar líneas `.pengu`
(aunque el C generado ya tenga `#line`).

**Reparación (F6, con dependencia de F4):** en el driver, si el perfil es
`debug` y el usuario no pasó `-g` ni `--strip`, añadir `-g` (sin cambiar `-O0`);
añadir `--no-debug`/`--strip` para desactivar. Documentar el tamaño. Un test
`readelf`/`objdump` comprueba `.debug_line` y que `gdb` resuelve
`src/main.pengu:3`.

---

### B-06 — `psc expand --out PATH` rechaza la forma con espacio

**Evidencia**

```
psc expand p100 --out /tmp/scale/space.c
→ exit 2, imprime la ayuda
```

`psc build` acepta `--out PATH` y `--out=PATH`; `psc expand` solo la segunda.
Es una inconsistencia de CLI, no un bug de compilación. **Reparación:** unificar
el parser de `--out` (y `--target`, `--cc`) en `cmd/expand.pengu`;
test de CLI para ambas formas.

---

### B-07 — `target` de nivel superior se ignora en silencio

**Evidencia:** `pengu.toml` con `target = "wasm32-unknown-emscripten"` en la
raíz produce un binario nativo; solo `[build] target` funciona. No hay
diagnóstico de clave desconocida. **Reparación:** aceptar el alias de nivel
superior (compatibilidad) o emitir `E-unknown-key` con “did you mean
[build] target?”; documentar en `docs/LANGUAGE`/CLI.

### B-08 — Flags duplicados (`-Wall` dos veces)

En el build del repo, `--verbose` muestra `-Wall` repetido (manifiesto +
perfil). No rompe nada, pero ensucia logs y puede duplicar flags con efecto
acumulativo. **Reparación:** deduplicar `tc.cflags` conservando el orden y
las últimas apariciones; test unitario.

### B-09 — Caché de 1,7 GB sin política de limpieza

`~/.cache/pengu/psc` tenía ~7.800 entradas y 1,7 GB tras la auditoría; no hay
GC automático ni límite. `psc gc` existe pero es manual y no está en la guía.
**Reparación:** límite configurable (`PSC_CACHE_MAX_MB`, por defecto p. ej.
2048), GC al superar el umbral (LRU por `mtime` del directorio de entrada) y
documentación en CLI/README. No es release-blocker, pero sí higiene.

### B-10 — Windows no está en CI

`bootstrap/psc_stage0_windows_x64.c` existe y `release.toml` lista
`windows-x86_64`, pero la matriz CI solo corre Ubuntu y macOS, y el workflow de
release empaqueta solo Linux. **Reparación:** job Windows (MSVC o mingw) que
compile stage0, corra `tests/run.sh` (adaptando `sh`→PowerShell o usando
`bash` de Git for Windows) o, como mínimo, documentar “experimental, sin CI”.
Para 0.33: documentar con honestidad; para 0.34: job real.

### B-11 — `psc run` de un archivo usa una caché paralela más pobre

`src/psc/cmd/build.pengu:414-445` cachea el artefacto de `psc run <archivo>`
con una clave que solo contiene el texto del entry, `psc-0.8.0`, identidad del
compilador, target, perfil y cc. No incluye módulos importados, define ni
flags. En la prueba `/tmp/runbug` no se reprodujo stale (posiblemente porque
`put`/`get` no coinciden por la ruta), pero el diseño es frágil. **Reparación:**
reutilizar la clave del driver (una sola función `cache_key`) o desactivar esa
caché hasta que sea correcta. Entra en F1.

### B-12 — Resumen de bugs secundarios

| ID | Bug | Severidad | Fase |
|---|---|---|---|
| B-13 | `psc test` con target wasm del manifiesto usa el runner host | Alta (misma raíz B-01) | F2 |
| B-14 | Build wasm nunca cachea (multiarchivo) | Media (perf) | F1 |
| B-15 | `put` de caché ignora errores | Media | F1 |
| B-16 | `chmod` externo en caché (portabilidad Windows) | Baja | F1 |
| B-17 | `--verbose` imprime `cc:` aunque el artefacto no se regenere | Baja | F1 |
| B-18 | `docs/LSP.md` promete rename cruzado que no funciona | Media (docs) | F3 |
| B-19 | `serverInfo.version` literal | Baja | F3 |
| B-20 | Sin `psc test --coverage` (feature) | Alta (lista) | F4 |
| B-21 | Sin perfiles de sanitizers (feature) | Alta (lista) | F4 |
| B-22 | `-g` reproducible ausente (rutas absolutas) | Media | F4 |
| B-23 | Sin cross-compile nativo (feature) | Alta (lista) | F5 |
| B-24 | Sin debugger (feature) | Alta (lista) | F6 |
| B-25 | Sin incremental por módulo/paralelo (feature) | Alta (lista) | F7 |
| B-26 | Sin instrumentación de tiempos (perf) | Media | F8 |

---

## 4. Optimizaciones adicionales (no pedidas explícitamente)

| ID | Optimización | Ganancia estimada | Coste |
|---|---|---|---|
| O-01 | Clave antes de sema/codegen + fast-path | 30 s → <0,5 s en no-op | F1, 1–2 d |
| O-02 | `--timings`/`PSC_TIME=1` por fase (sema, codegen, cc, hash) | Visibilidad; base de F8 | F8, 0,5 d |
| O-03 | Reservar capacidad del `StringBuilder` del bundle (~5 MB) | Menos reallocs/copias | F8, 0,5 d |
| O-04 | Evitar `copy` de strings por línea en el emisor (usar vistas/`write`) | 10–25 % de codegen | F8, 2 d |
| O-05 | Cachear `symbol_at_offset`/lookups repetidos en sema | 5–15 % de sema | F8, 2 d |
| O-06 | Paralelizar especialización de genéricos y códecs JSON (independientes) | 2–4× en esa parte | F7, 3 d |
| O-07 | `cc` incremental por módulo (objetos + link) | 5,5 s → ~0,5 s por cambio | F7, 8–12 d |
| O-08 | Deduplicar flags y usar `-pipe` | Marginal | F1, 0,2 d |
| O-09 | `psc gc` automático y límite de caché | Evita GB y degradación | F1, 1 d |
| O-10 | Perfil `release` con LTO opcional (`-flto`) documentado | Rendimiento del programa final | F8, 2 d (medir) |
| O-11 | `psc doctor` comprueba `node`, `emcc`, `gcov`, `gdb`, `cc` y versiones | Mejor soporte | F4, 1 d |
| O-12 | Cachear el resultado de `psc check` por módulo | `check` 3,6 s → <1 s | F7, 3 d |

> O-10 (LTO) puede aumentar mucho el tiempo de link; debe ser opt-in y medirse,
> no por defecto.

---

## 5. Plan de acción por fases

Convención: **d** = días-persona aproximados, incluidos tests y documentación de
la fase. Cada fase termina con `tests/run.sh` + `regress.sh` verdes y un commit
temático.

### F0 — Preparación y red de seguridad (2 d)

**Objetivo:** poder medir y detectar regresiones antes de tocar la caché.

- Crear `tests/audit/` con proyectos fixture reutilizables (wasm, caché,
  LSP de dos archivos, cobertura, sanitizers).
- Añadir a `tests/regress.sh` un modo `--quick` y etiquetas por bug
  (`# B-01`).
- Script `tools/bench.sh`: mide `build` caliente/frío, `check`, `expand`, `cc`
  y guarda CSV en `scratch/bench-<fecha>.csv`.
- Documento `docs/psc/CACHE.md` (diseño actual y clave) para que F1 no sea
  arqueología.
- Gate de release: workflow `release-gate.yml` que exige los tests de B-01..B-03
  y `gen_stage0.sh --check`.

**Salida:** baseline reproducible; ningún cambio funcional.

### F1 — Caché correcta y fast-path < 2 s (4–5 d)

**Objetivo:** ningún artefacto obsoleto y no-op en caliente < 2 s.

Tareas (ordenadas):

1. Extraer `cache_key(...)` a una función única en `src/psc/driver/cachekey.pengu`
   (o `driver/build.pengu`) usada por `build`, `run` y `test`.
2. Mover el cálculo antes de sema/codegen; no hashear `bundle.c` ni `build_dir`.
3. Añadir cflags/links/lib_dirs/assets a la clave; versión `psc-0.9.0`.
4. Ordenar `push_dir_hashes`; excluir directorios generados; hash de contenido
   con tamaño (evitar colisiones por concatenación).
5. Instalación atómica (`tmp` + `rename`) y `chmod` nativo (sin proceso externo).
6. `put` comprobado; `--verbose` informa `cache hit/miss` y motivo.
7. GC: `PSC_CACHE_MAX_MB` (default 2048), LRU por `mtime`, `psc gc` documentado.
8. Cachear wasm multiarchivo o desactivarlo con mensaje.
9. Tests de matriz (12 mutaciones) y de concurrencia (dos builds simultáneos).

**Aceptación:**

- No-op repo ≤ 2 s (objetivo 0,5 s); `cc:` ausente.
- Matriz completa: hit solo cuando nada relevante cambió.
- `psc build .` con el binario en ejecución: segundo build acierta.
- 0 entradas nuevas al crear/borrar `build/unrelated.txt`.

**Riesgo:** medio. Mitigación: feature flag temporal
`PSC_CACHE=0`/`--no-cache` ya existe; comparar artefactos con y sin caché en CI
(sha256) para detectar staleness.

### F2 — Bugs de ejecución y target (2–3 d)

- B-01: `BuildResult.target`; `run`/`test` usan el target resuelto.
- B-02: fallback a navegador solo por fallo de ejecución; `--browser` opt-in;
  propagar exit code y stderr.
- B-13: `psc test` wasm con manifiesto.
- B-06/B-07/B-08: parser `--out`, alias/diagnóstico de `target`, dedupe flags.
- Tests: `tests/regress_run_wasm.sh`, `tests/regress_cache_flags.sh`,
  `tests/cli/expand_out_space.sh`.
- Docs: `docs/WASM.md` y `docs/psc/CLI.md` con la semántica de exit codes.

**Aceptación:** los tres blockers cerrados; `psc run`/`test` devuelven el código
del programa en nativo y wasm; CI release-gate verde.

### F3 — LSP completo y correcto (3–4 d)

- Identidad de símbolo estable entre documentos (workspace index o
  `SemaProgram` compartido).
- Rename y references cruzados; rename de campos/métodos/imports.
- `serverInfo.version` desde constante.
- Tests LSP: rename round-trip (2 y 3 archivos), references, definition,
  diagnostics; ejecutar con `PSC` absoluto en CI (hoy el test falla si es
  relativo).
- Actualizar `docs/LSP.md` (promesas reales, limitaciones, configuración).

**Aceptación:** `tests/lsp/run_lsp_tests.py` incluye rename y pasa; VS Code
extension sigue funcionando; sin regresiones en hover/inlay/semantic tokens.

### F4 — Cobertura, sanitizers y reproducibilidad (5–6 d)

**Cobertura**

- `psc test --coverage` (y `--coverage=lcov|html|text`).
- Compilar con `--coverage -g -O0` (forzar flags y **desactivar caché** o
  incluirlos en la clave; depende de F1).
- Ejecutar, invocar `gcov -b`, filtrar `*.pengu`, agregar por archivo/línea,
  generar `coverage/lcov.info` y resumen; fallar con `--coverage-fail-under=N`.
- Mapear a `.pengu` vía `#line` (verificado: gcov reporta
  `Source:src/main.pengu`).
- Tests: proyecto con ramas y líneas no cubiertas; comprobar porcentajes y que
  `lcov.info` tenga `SF:src/main.pengu`.

**Sanitizers**

- Flag `--sanitize=address,undefined` / `--sanitize=thread` (o perfiles en
  `pengu.toml`: `[profiles.asan]`), que añada flags a compile **y** link.
- `--sanitize` implica `-g -O1 -fno-omit-frame-pointer`; desactivar caché o
  incluir en clave.
- Perfiles documentados: ASan+UBSan, TSan (solo hilos), leaks opcional.
- Job CI Linux (ASan/UBSan smoke ya existe) + TSan para `std.filum`.
- `psc doctor` detecta soporte del cc.

**Reproducible**

- `--reproducible` (o por defecto): `-ffile-prefix-map=$PWD=.`,
  `-fdebug-prefix-map=$PWD=.`, `-fmacro-prefix-map=$PWD=.`; `-frandom-seed`
  estable por target; `SOURCE_DATE_EPOCH` respetado en `psc doc`/release.
- Verificar `sha256` idéntico en dos directorios distintos **con `-g`**.
- `--frozen`: documentar que hoy solo cubre deps; añadir `--frozen` a build
  para no escribir lock ni red (si aplica).
- CI: job “reproducibility” que construye en `/tmp/a` y `/tmp/b` y compara.
- Docs: `docs/psc/REPRODUCIBLE.md` + sección en README.

**Aceptación:** cobertura mapeada a `.pengu`; ASan/UBSan/TSan ejecutan un test
real; dos builds con `-g` en rutas distintas dan el mismo sha256.

### F5 — Cross-compile nativo (5–7 d)

**Objetivo:** `target` en `pengu.toml` y CLI para Linux ARM, macOS ARM y
Windows, con toolchains declarativas.

Diseño:

```toml
[targets.linux-aarch64]
triple = "aarch64-unknown-linux-gnu"
cc = "aarch64-linux-gnu-gcc"
sysroot = "/usr/aarch64-linux-gnu"
runtime = "vendor/runtime/linux-aarch64/libpengu_runtime.a"
```

- Extender `driver/target.pengu`: tabla de targets nativos, detección de
  `cc`/sysroot, error accionable si falta toolchain (hoy rechaza todo).
- Compilar `runtime/pengu_runtime.c` para cada target (script
  `tools/build_runtime_cross.sh`) y enlazar el archivo correcto.
- Windows: mingw-w64 (`x86_64-w64-mingw32-gcc`) + runtime; probar `psc.exe`
  bajo Wine solo como smoke; CI Windows nativo es F9/B-10.
- macOS ARM: solo se puede compilar en runner macOS (SDK); CI `macos-14`
  (arm64) ya existe y compila nativo arm64. Cross x86_64↔arm64 en macOS es
  posible con `-arch`; documentarlo.
- Linux ARM: CI con `gcc-aarch64-linux-gnu` + `qemu-aarch64` para ejecutar
  tests; matrices en `ci.yml`.
- `psc doctor` lista targets disponibles; `--target` valida.

**Aceptación:** `psc build . --target linux-aarch64` produce un ELF aarch64
ejecutable bajo qemu con `main` correcto; macOS arm64 en CI; Windows mingw
compila y `wine` ejecuta un hello world (si hay wine) o al menos enlaza.

**Riesgo:** alto en Windows/macOS por SDK; alcance realista: Linux aarch64
garantizado, macOS arm64 nativo en CI, Windows mingw “best effort”.

### F6 — Debugger MVP y stacks de fibras (5–8 d)

**Objetivo:** `-g` por defecto en debug, breakpoints y backtraces que muestren
`.pengu`, incluidas corrutinas.

- B-05: `-g` por defecto en perfil debug (sin cambiar `-O0`); `--strip` para
  release.
- `psc debug [target] -- args`: wrapper que localiza `gdb`/`lldb`, pasa
  `--args`, imprime la ruta del bundle y un `gdbinit` generado con
  `directory`, `set substitute-path` y pretty-printers.
- Scripts `tools/debug/pengu.gdb` y `pengu.lldb`: breakpoint por
  `archivo.pengu:línea`, `bt`, impresión de `PenguValue`/strings.
- Fibras: `runtime/pengu_coro.c` registra cada corrutina (id, stack base,
  tamaño, estado) en una lista global; exponer `pengu_coro_registry` para que
  el script de gdb recorra stacks (`mco_stack`/frame pointers) y muestre
  “fiber N”. Requiere compilar el runtime con `-g` y no optimizar en exceso.
- Test manual/documentado: programa con dos corrutinas, breakpoint dentro de
  una, `bt` muestra la fibra; test automatizado con `gdb --batch -ex`.
- Docs: `docs/psc/DEBUGGING.md`; `psc doctor` comprueba gdb/lldb.

**Aceptación:** gdb y lldb resuelven líneas `.pengu`; un breakpoint en una
corrutina se alcanza; `bt` no se rompe en `mco_resume` (muestra frames de la
fibra o al menos la cadena de arranque).

**Fuera de alcance 0.33:** DAP completo, UI de debugger, watchpoints
avanzados. Se puede ofrecer en 0.35+.

### F7 — Incremental por módulo y paralelismo (10–15 d)

**Objetivo:** cambiar un módulo y reconstruir en < 5 s (stretch < 2 s);
aprovechar núcleos en codegen y cc.

Enfoque por etapas, sin romper el modelo actual:

1. **Cache de fases** (3–4 d): guardar el `SemaProgram` serializado por hash de
   módulo y reutilizarlo si no cambió; invalida por imports/headers/flags.
   `psc check` por módulo < 1 s.
2. **Emisión paralela por módulo** (4–5 d): el DCE y la especialización de
   genéricos son globales; tras calcularlos, emitir cada módulo a un
   `StringBuilder` propio en hilos (`std.filum`), concatenar en orden
   determinista. Requiere que las tablas de símbolos sean de solo lectura
   durante la emisión y pasar un contexto por módulo.
3. **TU partida + cc paralelo** (5–8 d, opcional/experimental): generar
   `build/mod_<hash>.c` + `bundle.h`; compilar en paralelo (`-j N`) y enlazar.
   Problemas: `static`/`static inline` entre módulos, instancias de tipos
   compartidas, `#line` y DCE global. Solución: header con declaraciones,
   funciones internas con prefijo de módulo, instancias en un `.c` común.
   Mantener la TU única como default y `--parallel-codegen` como opt-in hasta
   que la paridad esté probada.
4. **Link** con `-Wl,--gc-sections` ya existe; medir `-flto` opcional.

**Aceptación:**

- No-op < 2 s (F1) se mantiene.
- Cambiar un módulo: codegen < 2 s y cc < 1 s (sin contar link).
- Build completo del repo en 36 núcleos ≤ 10 s (stretch ≤ 6 s).
- Salida idéntica (sha256) con y sin paralelismo en la suite de tests.

**Riesgo:** alto; por eso va después de 0.33. Si el tiempo aprieta, entregar
solo (1) y (2), y dejar (3) para 0.35.

### F8 — Rendimiento del compilador (5–7 d)

- Implementar `--timings`/`PSC_TIME=1`: sema, codegen (por módulo), cc,
  hash, total; volcar a stderr y JSON.
- Perfilar con `gprof` (compilar el compilador con `-pg` en un job aparte) o
  instrumentación manual; identificar top 20 funciones.
- Optimizaciones candidatas: reserva del builder, evitar `copy` por línea,
  internar strings de símbolos, cachear `symbol_at_offset`, reducir
  `specialize_all`/`scan_generic_refs_all`, JSON codecs perezosos.
- Presupuesto: self-build 30 s → ≤ 18 s (sin paralelismo) y ≤ 12 s con F7;
  `psc check` ≤ 2 s.
- Benchmark en CI (no bloqueante al principio; alertar > 20 % de regresión).

**Aceptación:** informe antes/después con la misma máquina; sin regresiones
funcionales; `--timings` documentado.

### F9 — Documentación, versión 0.33.0 y README (4–5 d)

**Documentación**

- Actualizar: `docs/psc/{CLI,DRIVER,CODEGEN,CACHE,DEBUGGING,REPRODUCIBLE}.md`,
  `docs/LSP.md`, `docs/WASM.md`, `docs/LIBRARIES*`, `docs/README.md`.
- `CHANGELOG.md`: sección 0.33.0 con bugs, features, breaking changes
  (clave de caché, flags), agradecimientos.
- `gen_api.sh --check` y `validate_docs.py` verdes; enlaces `check_links.sh`.
- `docs/` en inglés y español donde ya exista paridad (LANGUAGE/PENGUNIC/STDLIB/
  LIBRARIES). Las nuevas páginas internas pueden ir en inglés si el resto del
  directorio `docs/psc/` está en inglés/español según corresponda.

**Versión**

- `tools/bump_version.sh 0.33.0` (edita VERSION, pengu.toml, release.toml,
  `src/main.pengu`, LSP, docs, extensión).
- `tools/gen_stage0.sh` para regenerar los tres bundles stage0 y
  `gen_stage0.sh --check` en CI.
- `release.toml`: `version`/`bind_version` 0.33.0; revisar targets.
- Tag `v0.33.0` y release notes.

**README principal (raíz, inglés, con emojis)**

Contenido mínimo (más detalle en el anexo D):

1. Banner/título + tagline + badges (CI, licencia MIT, versión).
2. ✨ Features (autohospedado, tipado, corrutinas, hilos, WASM, LSP, etc.).
3. 🖥️ Plataformas soportadas: tabla Linux x86_64/aarch64, macOS arm64/x86_64,
   Windows x86_64 (estado), WASM (browser/Node; WASI no), con notas de CI.
4. 📦 Instalación: prebuilt (release), desde fuente (bootstrap + `cc`),
   requisitos, `psc doctor`, `PATH`.
5. 🚀 Quick start: `psc init`, `pengu.toml`, hello world, `build`, `run`,
   `test`, `fmt`.
6. 🛠️ CLI: tabla de comandos y opciones comunes (`--target`, `--profile`,
   `--release`, `--verbose`, `--no-cache`, `--frozen`, `--sanitize`,
   `--coverage`, `--timings`).
7. 📁 Estructura de proyecto y `pengu.toml` comentado.
8. 🌐 WASM: ejemplo, `emcc`, Node/browser, límites.
9. 📚 Documentación: enlaces a `docs/LANGUAGE.md`, `PENGUNIC.md`, `STDLIB.md`,
   `docs/api/`, `docs/psc/`, `docs/WASM.md`, `docs/LSP.md`, versiones ES.
10. 🧪 Testing, cobertura, sanitizers, reproducibilidad.
11. ⚡ Rendimiento y caché (cómo limpiar, `psc gc`).
12. 🤝 Contribuir: `tests/run.sh`, `tests/regress.sh`, `fmt --check`,
    `gen_stage0.sh --check`, docs.
13. 🙏 Agradecimientos + licencias (tabla de THIRD_PARTY).
14. 📄 Licencia MIT y citación.

**Aceptación:** README renderiza en GitHub, todos los enlaces relativos
existen, `check_links.sh` verde, y una persona nueva puede instalar y ejecutar
`psc run` siguiendo solo el README.

---

## 6. Roadmap de versiones propuesto

| Versión | Contenido | Duración estimada |
|---|---|---:|
| **0.33.0** | F0–F4 + F9 (bugs, caché, LSP, cobertura, sanitizers, reproducible, docs, README) | 22–28 d |
| **0.34.0** | F5 + F6 (cross-compile nativo, debugger MVP, Windows CI) | 10–15 d |
| **0.35.0** | F7 + F8 (incremental por módulo, paralelismo, perf) | 15–22 d |

Alternativa “todo en 0.33.0”: 45–65 d y un release muy grande; **no
recomendado** porque F7 toca el corazón del codegen y puede retrasar los
blockers. La lista del usuario se cumple completa en 0.35.0; 0.33.0 ya elimina
los bugs y añade la mayor parte del valor visible.

---

## 7. Decisiones que necesitan visto bueno

1. **Alcance de 0.33.0:** ¿F0–F4 + F9 (recomendado) o intentar todo?
2. **Debugger:** ¿MVP gdb/lldb + fibras (recomendado) o DAP completo (mucho
   mayor, 3–4 semanas)?
3. **Cross-compile:** ¿garantizar Linux aarch64 + macOS arm64 en CI y Windows
   mingw “best effort”, o exigir los tres al 100 %? (Windows requiere runner
   propio y pruebas de runtime).
4. **Paralelismo:** ¿aceptas `--parallel-codegen` experimental en 0.35 con TU
   partida, manteniendo la TU única por defecto?
5. **`-g` por defecto en debug:** añade tamaño y tiempo de link; ¿lo hacemos
   por defecto o solo con `--debug`?
6. **Caché:** ¿versión de formato `psc-0.9.0` y límite por defecto 2 GB?
   ¿GC automático o solo manual?
7. **Breaking changes:** la clave nueva invalida la caché existente (sin
   impacto funcional); ¿aceptas? ¿algún flag que deba mantenerse?
8. **Windows:** ¿0.33 lo documenta como experimental y 0.34 añade CI, o se
   bloquea el release hasta tener CI Windows?

---

## 8. Criterios de aceptación globales

- [ ] `tests/run.sh` (118+) y `tests/regress.sh` (19+) verdes en Linux y macOS.
- [ ] `fmt --check`, `gen_stage0.sh --check`, `gen_api.sh --check`,
      `validate_docs.py`, `check_links.sh` verdes.
- [ ] B-01/B-02/B-03 cerrados con tests que fallen antes y pasen después.
- [ ] No-op `psc build .` ≤ 2 s; matriz de invalidación de caché completa.
- [ ] LSP rename/references cruzados con round-trip.
- [ ] `psc test --coverage` produce `coverage/lcov.info` con `SF:` de `.pengu`.
- [ ] ASan/UBSan/TSan ejecutan al menos un test real en CI.
- [ ] Dos builds con `-g` en directorios distintos → mismo sha256.
- [ ] `psc build . --target linux-aarch64` ejecutable bajo qemu (F5).
- [ ] Breakpoint en `.pengu` y `bt` con fibra (F6).
- [ ] Build completo ≤ 18 s (F8), ≤ 12 s con paralelismo (F7).
- [ ] README completo, en inglés, enlaces válidos, licencias correctas.
- [ ] Versión 0.33.0 en todos los archivos y stage0 regenerado.

---

## 9. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| La caché nueva sigue sirviendo stale | Media | Alto | Matriz de 12 mutaciones + comparación sha con `--no-cache` en CI |
| ETXTBSY en Windows al reemplazar el exe | Media | Medio | `rename` falla → copiar a otro nombre y avisar; tests Windows |
| Partir la TU rompe `static`/genéricos | Alta | Alto | Flag experimental, paridad sha256, tests completos antes de default |
| TSan se queja de minicoro/fibras | Media | Medio | Perfil TSan separado, suprimir stacks conocidos documentados |
| gdb no entiende fibras | Alta | Medio | Registrar stacks en runtime; fallback a `bt` del scheduler |
| Cross macOS desde Linux imposible | Alta | Medio | Compilar en runner macOS; documentar límite |
| Windows CI inestable | Media | Medio | Job no bloqueante al principio; matriz nightly |
| Aumento de tamaño por `-g` | Alta | Bajo | `--strip` en release; doc de tamaños |
| Tiempo de F7 se dispara | Alta | Medio | Entregar F7 en dos hitos (fases cache; emisión paralela) |
| Pérdida de determinismo por paralelismo | Media | Alto | Orden determinista de concatenación + test sha256 |

---

## 10. Anexos

### A. Comandos de reproducción

```bash
# Baseline
PSC=./build/psc ./tests/run.sh
bash ./tests/regress.sh

# Tiempos
time ./build/psc build .
time ./build/psc check .
time ./build/psc expand . --out=/tmp/bundle.c
time gcc -O0 -g -c build/bundle.c -o /tmp/bundle.o

# B-01/B-02 (wasm run)
# ver /tmp/edge del texto

# B-03 (caché)
cd /tmp/cflagbug2 && PSC_CACHE_DIR=/tmp/cf-cache \
  /home/tugatito/Documentos/GitHub/PenguScript/build/psc build . --verbose

# B-04 (LSP rename)
python3 tests/lsp/run_lsp_tests.py   # con PSC absoluto

# Cobertura
cd /tmp/cov-proj && psc build . && ./build/app
gcov -b build/app-bundle.gcno        # genera src/main.pengu.gcov

# Reproducibilidad
cd /tmp/rep-a && psc build . && sha256sum build/app
cd /tmp/rep-b && psc build . && sha256sum build/app
```

### B. Clave de caché: antes vs después

**Antes (18–20 componentes):** hash del compilador, `"psc-0.8.0"`, triple,
wasm target, cc, perfil, `o.cc`, salida, `"test"`, is_test, json, strict,
unsafe, nodce, userdce, prunetypes, prunenative, nolines, defines, ldflags,
módulos (path+texto), hashes de `c_dir`, `include_dir`, `include_dirs`
(incluye `build_dir`).

**Después (propuesto):**

```
compiler_hash
"psc-0.9.0"
target.triple | target.wasm_target
cc path + cc version (opcional)
profile name + profile cflags (ordenados, deduplicados)
man.cflags + tc.cflags + man.links + man.lib_dirs
output kind + is_test + test_json + strict/unsafe/nodce/userdce/prunetypes/prunenative/nolines
man.defines + cli defines (orden)
man.ldflags + program ldflags
módulos: path + sha256(texto) (no el texto completo, para reducir memoria)
c_dir/include_dir/include_dirs: rutas ordenadas + sha256 por archivo (sin build_dir)
assets_dir (si assets.embed) + shell/JS (si aplica)
```

### C. Archivos que tocará la implementación

| Fase | Archivos |
|---|---|
| F1 | `src/psc/driver/build.pengu`, `src/psc/cache/cache.pengu`, nuevo `src/psc/driver/cachekey.pengu`, `src/psc/cmd/gc.pengu`, `src/psc/cmd/build.pengu` |
| F2 | `src/psc/driver/build.pengu`, `runner.pengu`, `src/psc/cmd/build.pengu`, `test.pengu`, `target.pengu` |
| F3 | `src/psc/lsp/server.pengu`, `src/psc/lsp/query.pengu`, `tests/lsp/*`, `docs/LSP.md` |
| F4 | `src/psc/cmd/test.pengu`, `src/psc/driver/build.pengu`, `tools/coverage/*`, `.github/workflows/ci.yml`, docs |
| F5 | `src/psc/driver/target.pengu`, `toolchain.pengu`, `build.pengu`, `tools/build_runtime_cross.sh`, CI |
| F6 | `src/psc/driver/build.pengu`, `runtime/pengu_coro.c`, `tools/debug/*`, docs |
| F7 | `src/psc/codegen/{bundle,emit,api}.pengu`, `driver/build.pengu`, `std/filum.pengu` |
| F8 | `src/psc/codegen/*`, `src/psc/sema/*`, `src/main.pengu` (timings) |
| F9 | `README.md`, `CHANGELOG.md`, `docs/**`, `VERSION`, `release.toml`, `pengu.toml`, stage0 |

### D. Esquema del README principal (inglés)

```
# 🐧 PenguScript
> A small, fast, self-hosted systems language with coroutines, threads and WASM.

Badges: CI | License MIT | Version 0.33.0

## ✨ Why PenguScript?
- Self-hosted compiler (psc written in PenguScript)
- Static types, ownership, no GC
- Stackful coroutines + threads (std.filum)
- Incremental builds and content-addressed cache
- First-class LSP (VS Code)
- Compiles to native (C11) and WebAssembly

## 🖥️ Supported platforms
| Platform | Arch | Status | Notes |
Linux | x86_64, aarch64 | ✅ CI | ...
macOS | arm64, x86_64 | ✅ CI | ...
Windows | x86_64 | ⚠️ experimental | no CI yet
WASM | wasm32 | ✅ Emscripten | browser + Node; WASI not supported

## 📦 Installation
### Prebuilt
### From source
requirements: cc, make?, python3?; bootstrap
psc doctor
### Editor support

## 🚀 Quick start
psc init hello && cd hello && psc run .
pengu.toml example

## 🛠️ CLI cheat sheet
(table)

## 🌐 WebAssembly
(short example + link docs/WASM.md)

## 📚 Documentation
Language / Pengunic / Stdlib / API / Compiler internals / WASM / LSP
(EN + ES links)

## 🧪 Testing, coverage, sanitizers, reproducibility

## ⚡ Performance & cache
(cache location, psc gc, --no-cache)

## 🤝 Contributing

## 🙏 Acknowledgements & licenses
(table: SDS, CC, vaqt, libffi, libsodium, libclang, minicoro, miniz,
tiny-regex-c, utf8.h, petitio/libcurl, toml_min, Emscripten/Node as tools)

## 📄 License
MIT
```

### E. Agradecimientos/licencias que debe listar el README

De `THIRD_PARTY.md` (verificar cada entrada antes de publicar):

| Componente | Uso | Licencia |
|---|---|---|
| SDS | strings dinámicos | BSD-2-Clause |
| CC | contenedores genéricos | MIT |
| vaqt | vectores/arena | BSD-3-Clause |
| libffi | FFI | MIT |
| libsodium | criptografía (opcional, no vendorizado) | ISC |
| libclang | bindings | Apache-2.0 WITH LLVM-exception |
| minicoro | corrutinas | Unlicense / MIT-0 |
| miniz | compresión | public domain / Unlicense |
| tiny-regex-c | regex | public domain |
| utf8.h | UTF-8 | public domain / Unlicense |
| petitio | HTTP (envuelve libcurl) | MIT |
| toml_min | parser TOML | MIT (first-party) |

Herramientas de build no vendorizadas que conviene mencionar: **Emscripten**
(MIT/UIUC), **Node.js** (MIT), **Emscripten SDK**. No son dependencias del
runtime, pero el README debe aclarar que se instalan aparte.

---

## 11. Conclusión

La lista es **viable**, pero no toda cabe en un solo release sano. Los tres
fallos de release-blocker tienen causa raíz identificada y arreglo pequeño; la
caché correcta es la palanca más grande (30 s → <2 s) y habilita cobertura,
sanitizers y reproducibilidad. LSP y cobertura son trabajo acotado y verificable.
Cross-compile, debugger y paralelismo son proyectos de ingeniería con riesgo
medio/alto que merecen releases propios.

**Petición:** visto bueno a F0–F4 + F9 para 0.33.0 (y al roadmap 0.34/0.35), o
ajuste de alcance/prioridades. Con la aprobación se empieza por F0/F1 y se
entrega cada fase con tests y medición antes/después.

---

## Anexo — estado de implementación (0.33.0, 2026-11-05)

Implementado y verificado en esta versión:

- **F1 caché**: clave pre-sema `psc-cache-2`, árboles ordenados, `build/`
  excluido, cflags/links/lib_dirs/runtime/JS incluidos, escritura atómica,
  fast-path < 2 s (0.19–0.33 s medido) y hit seguro con el binario en ejecución.
- **F2**: `BuildResult.is_wasm`, `psc run`/`test` respetan el target del
  manifiesto, sin fallback silencioso a Chromium; `--out PATH` en `expand`;
  deduplicación de flags/include dirs; flags `--no-cache`/`--clear-cache`/
  `--ephemeral` en `psc test`.
- **F3**: rename y referencias cross-file con identidad estable y fallback por
  token/nombre; suite LSP completa en verde.
- **F4**: `psc test --coverage` (gcov mapeado a `.pengu`), `--sanitize=address|
  undefined|thread`, `-g` por defecto en debug, builds reproducibles verificados
  y tests de regresión para cobertura, sanitizers y reproducibilidad.
- **F5**: triples nativos Linux x86_64/aarch64 (gnu/musl), macOS x86_64/aarch64 y
  Windows mingw; selección de compilador, `--target` para clang, runtime por
  triple en `build/lib/<triple>/` y error accionable; CI de Linux ARM64 con
  qemu; macOS ARM64 cubierto por el runner nativo `macos-latest`.
- **F6**: `psc debug` (gdb/lldb), DWARF por defecto en debug, breakpoints sobre
  `.pengu`; `pengu-fibers` lista corrutinas vivas y la pila capturada en su
  último yield (registro TLS + frame pointers, sin depender del unwinder de
  libgcc), con regresión `tests/regress_fibers.sh`.
- **F8 (medición y optimización)**: `PSC_TIME`, `tools/bench.sh` con gate de CI
  (<2 s caliente) y perfilado con gprof. Cuello identificado: codegen (~6.7 s
  release, ~20.5 s debug). Optimizaciones aplicadas en semántica: `tag_decl` ya
  no divide el archivo completo por declaración y `lookup_name` indexa alias de
  import (`import_by_name`) y se eliminó el escaneo lineal de imports del
  fallback; semántica 3.8 s → 1.5 s (debug) y 0.94 s → 0.5 s (release), con
  codegen release ~4.7 s en la última medición.
- **F9**: documentación completa (README, BUILD_CACHE, CROSS_COMPILE, COVERAGE,
  SANITIZERS, DEBUGGER, F7_MULTITU), versión 0.33.0 y stage0 regenerado; el
  empaquetado se valida con `tests/regress_release.sh`, que exige tarballs
  reproducibles y compila un proyecto con el portable extraído.

Pendiente y documentado como deuda explícita (no bloquea 0.33.0):

- **F7 (entregado)**: `psc build --split-codegen --jobs=N` emite `bundle.h` +
  `core.c` + una unidad por módulo y compila los objetos en paralelo. La caché
  `unit-object-v1` reutiliza los `.o` sin cambios: el compilador completo pasa
  de 19.9 s (single-TU) a 14.8 s con las 137 unidades reutilizadas; editar un
  módulo recompila solo su unidad. `psc check` cachea por clave pre-sema
  (1.9 s → 0.17 s) y `--verbose` explica qué módulo invalidó la clave. Queda
  como limitación conocida que la **emisión** de C sigue en un proceso y que
  wasm/estáticos usan single-TU. Detalle en `docs/psc/F7_MULTITU.md`.
- **F6+**: DAP con stepping fiber-aware; las fibras que nunca se resumieron no
  tienen pila capturada y solo muestran límites de stack.
- **F5**: workflow manual `windows-cross.yml` para mingw (`PE32+`); falta un job
  bloqueante y validación de red/hilos en Windows.
- **F4**: `--coverage` para wasm (en nativo el resumen ya filtra cabeceras del runtime).
