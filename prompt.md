# P2 — Amplitud: rlgl, arrays 2D, estado de módulo, liberación de memoria, punteros estrictos, `pengu bind` real

> **Para:** agente de implementación (gemini 3.8 flash).
> **Repo:** `D:\Proyectos\PenguScript` (Windows, PowerShell). Trabaja **en el árbol de trabajo**, sin commits.
> **Punto de partida verificado (baseline P1 cerrado):** suite `767 passed, 1 skipped`; P0 y P1 completos;
> 5 ejemplos raylib portados en `scratch/port/` (01–05) que compilan y ejecutan. Lee `P1_PROGRESS.md`.
> **Objetivo:** cerrar los 6 frentes de P2 de `PRODUCTION_READINESS.md` §7, en el orden recomendado,
> dejando el árbol compilando y la suite verde tras **cada** hito.
> **Presupuesto:** si te quedas sin tokens, cierra el hito en curso y actualiza `P2_PROGRESS.md` (§7).
> No dejes tests en rojo ni el árbol a medio editar.

---

## 0. Reglas y contexto

### 0.1 Comandos (usa SIEMPRE el python del venv)

```powershell
cd D:\Proyectos\PenguScript
$env:PYTHONIOENCODING='utf-8'

# chequeo semántico (~4 s)
.\.venv\Scripts\python.exe pengu_project.py check --entry scratch\port\01_core_basic_window.pengu

# compilar un programa suelto -> build\bundle.c + build\app.exe
.\.venv\Scripts\python.exe pengu_project.py build --entry scratch\port\01_core_basic_window.pengu

# tests focalizados (siempre con -p no:cacheprovider)
.\.venv\Scripts\python.exe -m pytest tests/test_p2_features.py tests/test_p1_features.py -q -p no:cacheprovider

# suite completa (obligatoria al cerrar cada hito grande y al terminar)
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

Si un build "no refleja" tus cambios, borra la caché de ese programa:
`Remove-Item build\app.exe,build\bundle.c,build\.bundle_hash -ErrorAction SilentlyContinue`

### 0.2 Reglas duras (idénticas a P1; respétalas)
1. **PROHIBIDO** `git commit`, `git add -A`, `git checkout`, `git stash`, `git clean`, `git restore`.
   Todo el trabajo de la sesión está sin commitear y ya se perdió trabajo una vez con `git checkout -- std/`.
2. **No reformatees** archivos completos ni cambies finales de línea. Edita por fragmentos.
3. **No toques** `extern/` (vendors) ni los `std_c/*.h` que son de librerías. Puedes **añadir** archivos
   nuevos (`std_c/pengu_*.h`, stubs en `c_bind_stubs/`).
4. **No regeneres en bloque** `std/raylib.d.pengu` ni `std/sqlite3.d.pengu` (artesanales).
5. Código, comentarios, docstrings, tests y docs nuevos **en inglés**.
6. Tras cada hito: tests verdes + `P2_PROGRESS.md` actualizado (§7).

### 0.3 Criba de sintaxis (no pierdas tokens redescubriéndola)
Igual que en `prompt.md` (P1) §0.4. Recordatorios clave:
`calling f with a, b` · `sigil of x` · `essence of p` · `p->campo` · `transmute p to ref to T` ·
literal de struct `with x is 1.0, y is 2.0` (**entre paréntesis en argumentos**) ·
`array of T with size N is [0]` (init parcial rellena con ceros) · `xs at i` · `(xs length)` ·
`for i from 0 to N:` · `for x in coll:` · `judge n:` + `when 1 -> …` / `else -> …` ·
`when os == "windows":` · `import std.raylib` → `raylib.InitWindow` · `include "x.h"` · `link "m"` ·
`"Score: {score}"` (interpolación solo en contexto string; para `char*` usa `bytes of s`).
`at` es **postfix**: `xs at i + 1` es `(xs at i) + 1`; un índice calculado va entre paréntesis
(`set xs at (n - 1) is v`). Cualquier cambio aquí tiene tests en
`tests/test_p1_features.py::TestAtIndexSemantics`.

---

## 1. Orden de trabajo recomendado

| # | Frente | Impacto | Esfuerzo | Riesgo | Orden |
|---|--------|---------|----------|--------|-------|
| P2.2 | Arrays 2D (codegen inválido hoy) | corrige C inválido; 14 ejemplos | 2–4 h | bajo | **1º** |
| P2.4 | API de liberación string/list/map | fugas sin salida hoy | 2–4 h | bajo | **2º** |
| P2.3 | Idioma de estado de módulo | docs + tests, desbloquea 31 ejemplos | 1–2 h | muy bajo | **3º** |
| P2.1 | Binding de rlgl | 27 ejemplos | 2–4 h | medio | **4º** |
| P2.5 | Tipado estricto de punteros | cierra un agujero de sonido | 3–5 h | **alto** | **5º** |
| P2.6 | `pengu bind` con headers reales | tooling, 5 bindings a mano | 4–6 h | medio | **6º** |

Razón del orden: primero lo que arregla **C inválido o fugas** (P2.2, P2.4) y lo que es documentación
(P2.3); después el binding nuevo (P2.1, ya casi generado); y al final los dos frentes con más superficie
de regresión (P2.5 toca el sistema de tipos, P2.6 la herramienta de bindings), para que si se agota el
presupuesto el árbol quede en un estado sólido.

---

## 2. Hitos detallados

### P2.2 — Arrays 2D: el checker los acepta pero el codegen genera C inválido ⚠️

**Estado real (verificado):**
```pengu
var m as array of array of f32 with size 2 is [[1.0, 2.0], [3.0, 4.0]]   # check OK
var v as f32 is m at 0 at 1        # check OK
set m at 1 at 0 is 9.5             # check OK
```
pero al compilar: **`float m[2][None] = { … };`** → gcc
`error: 'None' undeclared` (reportado en tu línea `.pengu` gracias a las directivas `#line` de P0).
Evidencia: `build/bundle.c:187`.

**Causa raíz:**
- El tipo `array of array of f32 with size 2` deja el array **interno sin tamaño**
  (`array_type: "array" "of" type ["with" "size" (INT | NAME)]`, `pengu_parser/pengu_grammar.py`;
  el encadenado `array of array of f32 with size 2 with size 3` sí funciona: tamaño externo primero).
- `CTypeMapper.to_c_type` mapea un `ArrayType` anidado a **`float**`** (puntero, no array) y el
  declarador acaba imprimiendo `[2][None]` (fuga del `None` de Python). Anclas:
  `pengu_parser/pengu_types.py` (`ArrayType`) y `pengu_parser/pengu_codegen.py` (`CTypeMapper.to_c_type`,
  `to_c_decl`).

**Cambios:**
1. `CTypeMapper`: renderizar arrays anidados como `T[outer][inner]` en **declaración** y `T(*)[inner]`
   como **tipo de parámetro** (decay de la primera dimensión). Si alguna dimensión no tiene tamaño
   conocido, **no imprimas `None`**: emite un error semántico claro (p. ej. `E0015`:
   «dimensión interna desconocida en `array of array of T`: escribe
   `array of array of T with size M with size N` o inicializa con filas literales»).
2. Inferir el tamaño interno desde el inicializador cuando falte: un literal `[[…],[…]]` con filas de
   longitud homogénea fija la dimensión interna (el `array_lit` de `pengu_infer.py` ya calcula el tipo
   con las longitudes de fila; asegúrate de que ese tamaño **llega al tipo declarado** que usa el codegen).
   Si las filas tienen longitudes distintas → error claro.
3. `length` de una fila: `((m at 0) length)` debe emitir la dimensión interna (no `.len`).
4. Encadenado de índices y escritura: `m at i at j` y `set m at i at j is v` (ya funcionan en C: se vio
   `m[1][0] = 9.5f;`) — añade cobertura de tests.
5. Interop: decide y documenta cómo se pasa un array 2D a C (p. ej. un parámetro
   `ref to array of f32 with size N` recibe la fila; o `m at 0` → `ref to f32`). Test de compile+run.
6. Documenta en `CHEATSHEET.md` (sección de arrays) la sintaxis `with size M with size N` (externa primero)
   y el requisito de inicializar.

**Tests (clase `TestArray2D` en `tests/test_p2_features.py`):**
1. Codegen: el C contiene `float m[2][3]` (y no `None`).
2. Compile+run: inicialización, `m at 0 at 1`, `set m at 1 at 0`, lectura de vuelta y
   `((m at 0) length)` = dimensión interna.
3. Las dos grafías de tipo (`… with size 2 with size 3` y `… with size 3 with size 2`) producen la
   orientación correcta (externo primero) — test de tipo/C.
4. Error claro (no `None`) cuando la dimensión interna no se puede inferir:
   `var m as array of array of f32 with size 2 is []`-style → código `E…` + help.
5. Filas de longitud desigual → error.

**Aceptación:** los tests pasan; ningún programa puede generar un `[None]` (busca `None]` en
`build/bundle.c` de los ports como comprobación manual).

---

### P2.4 — API de liberación para `string` / `list` / `map`

**Estado real (verificado):** `banish s` sobre un `string`, `list of T` o `map of K to V` es
**E0008** («'banish' requires a reference type (ref to T)»). El runtime **ya tiene** las funciones:
`pengu_banish_string(PenguString*)` (`pengu_runtime.h:413`), `pengu_banish_list(PenguList*)` (`:1079`),
`pengu_banish_map(PenguMap*)` (`:1465`, que además libera claves/valores string). Hoy no hay forma de
liberar memoria desde PenguScript → fuga sin salida en bucles que construyen strings (verificado: el C
generado para un bucle de concatenación tiene **0** llamadas a `free`).

**Anclas:** checker `pengu_parser/pengu_checker.py:1560-1585` (rama `banish_stmt`, `E0008` en `:1580`);
codegen `pengu_parser/pengu_codegen.py:2109-2112` (`pengu_banish((void*)(target))`).

**Cambios:**
1. Checker: aceptar además `string`, `list of T` y `map of K to V` **lvalues** (nombre de variable o
   campo, no temporales, no `const`, no `frozen`), y seguir rechazando todo lo demás con un mensaje que
   enumere lo permitido.
2. Codegen: emitir la función correcta según el tipo —
   `pengu_banish_string(&s)`, `pengu_banish_list(&l)`, `pengu_banish_map(&m)`, y mantener
   `pengu_banish((void*)(p))` para `ref to T`. Debe funcionar igual dentro de `defer banish s`.
3. `banish` sobre un temporal o sobre `frozen` → error claro (no un C inválido).
4. Documenta la propiedad de memoria en `LANGUAGE.md` §9/ownership y `CHEATSHEET.md`: qué libera cada
   caso, que el valor queda vaciado (`s` pasa a `""`), que no se puede usar después, y que
   `pengu_banish_map` libera claves/valores string. Revisa que lo que dice `LANGUAGE.md` hoy sobre
   `banish` de strings (sección de ownership) quede **correcto** tras el cambio.
5. Opcional (si sobra presupuesto): envoltorios equivalentes en `std/ffi` (`drop_string`, `drop_list`,
   `drop_map`) para quien prefiera funciones a palabra clave.

**Tests (clase `TestBanishCollections`):**
1. Compile+run: bucle de 1000 iteraciones que crea una `string`, la usa y la banea → el programa termina
   sin crash y el C generado contiene `pengu_banish_string`.
2. `list of string` + `banish` → `pengu_banish_list`; `map of string to int` → `pengu_banish_map`.
3. `defer banish s` dentro de un `weave` compila y ejecuta.
4. Negativos: `banish` de un literal, de un `const`, de un `frozen` y de un temporal → error con código.
5. `banish` de `ref to T` sigue emitiendo `pengu_banish` (no regresión; hay tests previos).

---

### P2.3 — Idioma de estado de módulo (documentación + tests)

**Estado real:** `var` a nivel de módulo es `E0002` **por diseño** (`const` es global; `var`/`let` son
locales a la función) y `static var` de nivel superior es un error de sintaxis. Pero **`static var`
dentro de una función persiste entre llamadas** (verificado: un contador devolvió `1 2 3`).

**Decisión (no la cambies):** P2.3 **no** añade `var` de módulo. El entregable es el **idioma
documentado** y probado para tener estado por módulo, porque 31 ejemplos de raylib lo necesitan.

**Cambios:**
1. Nueva sección en `LANGUAGE.md` (p. ej. §10.5 «Module state») y entrada en `CHEATSHEET.md` con **dos
   patrones** y sus pros/contras:
   - **a) Statics privados + accessors**: `static var` dentro de weaves del módulo, expuestos con
     `weave get_x into T` / `weave set_x with v as T into void`. Es el más simple; no es reentrante ni
     thread-safe (menciónalo; con `std/filum` un mutex estático lo resuelve).
   - **b) Contexto explícito**: un `rune App` con los campos de estado, creado en `main` y pasado a los
     weaves (`with app as ref to App`). Es lo recomendable para código serio (testable, reentrante).
2. Ejemplo ejecutable en `tests/std_programs/test_modstate.pengu` (o un test en `tests/test_p2_features.py`)
   que use el patrón (a) desde **dos módulos** distintos (dos ficheros `.pengu` importados) y demuestre
   que el estado es **por módulo** y persiste entre llamadas.
3. Añade una nota de por qué no existe `var` global (enlace a la decisión de diseño del README) para que
   nadie lo "arregle" por error.

**Aceptación:** docs + test compile+run verdes; ningún cambio de semántica del compilador.

---

### P2.1 — Binding de `rlgl`

**Estado real (verificado):** `pengu bind` **ya genera** el binding:
```powershell
.\.venv\Scripts\python.exe pengu_project.py bind extern\raylib-6.0\src\rlgl.h --output scratch\rlgl_test.d.pengu --links raylib
```
→ 667 líneas: 163 `declare`, 122 `const` (`RL_DEFAULT_BATCH_*`, `RL_MAX_MATRIX_STACK_SIZE`…),
11 `omen`, 4 `rune` (incluye **su propio `rune Matrix`**, de forma **idéntica** al de
`std/raylib.d.pengu`), `include "rlgl.h"` y `link "raylib"`. Las funciones de rlgl son **símbolos
reales** en `libraylib.a` (`rlgl.c` se compila en el archivo), así que no hace falta shim.

**Cambios:**
1. Genera `std/rlgl.d.pengu` de forma **reproducible** (documenta el comando exacto en la cabecera del
   fichero) y añádele una cabecera de documentación en inglés (qué es, de dónde sale, cómo regenerarlo).
2. Resuelve la **convivencia con `std/raylib`**: verifica con `pengu check` un programa que haga
   `import std.raylib` **y** `import std.rlgl` (la regla E0046 acepta declaraciones duplicadas con la
   misma forma). Si hay colisión de nombres/constantes, decide y documenta: o el binding importa
   `std.raylib` y **no** redeclara `Matrix`/tipos de raylib (genera con `--include-paths` apuntando a los
   headers de raylib y con `--auto-import std`), o se aceptan los duplicados de forma idéntica.
   Comprueba también que pasar un `raylib.Matrix` a `rlSetUniformMatrix` type-checkea.
3. Audita el binding: funciones con parámetros `ref to rlDrawCall`/`rlVertexBuffer` (deben resolver),
   `const` mal mapeadas, `#define`s duplicados que el generador salta con warning
   (`RL_DEFAULT_BATCH_BUFFER_ELEMENTS`, `GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT`) — que no falte ninguna
   constante que use el ejemplo elegido.
4. **Test estrella:** porta un ejemplo que use rlgl de forma sencilla a `scratch/port/06_*.pengu`
   (candidatos: `shaders/shaders_texture_tiling.c`, `models/models_rlgl_solar_system.c`,
   `shaders/shaders_raymarching_rendering.c`; elige el más corto que use `rlPushMatrix`/`rlTranslatef`/
   `rlRotatef`/`rlPopMatrix` y/o `rlSetTexture`), con el límite de frames habitual (~120) y verifícalo
   **compilando y ejecutando**.
5. Actualiza `README.md` (lista de bindings) y `CHEATSHEET.md` (tabla de módulos).

**Tests (clase `TestRlgl`):** `check` limpio de un programa con `import std.raylib` + `import std.rlgl`
y llamadas a `rlPushMatrix`/`rlPopMatrix`; compile+run del port 06 (con `@requires_lib("raylib")`).

---

### P2.5 — Tipado estricto de punteros ⚠️ (el más delicado)

**Agujero real (verificado):** `BaseType.is_compatible` (`pengu_parser/pengu_types.py:279`) trata
**todos los enteros como compatibles entre sí** (`i32.is_compatible(char) == True`), así que:
- `calling take with sigil of n` donde el parámetro es `ref to char` **compila sin diagnóstico**
  (`ref to i32` ⇒ `ref to char`), y
- desde P1 también un `array of i32` decae a `ref to char` (rama de decay en
  `pengu_parser/pengu_infer.py:2080-2091`).
En cambio `ref to i32` → `ref to f64` **sí** se rechaza (`E0005`), y el resto del chequeo
(aridad, `frozen`, `void*`, literales) está bien.

**Objetivo:** que un puntero solo sea compatible con otro si el **pointee** coincide (o es
`void`/`opaque`, o el que llega es `frozen` del mismo tipo), sin romper la ampliación numérica de
**valores** (`int` → `i64` en una asignación debe seguir permitida).

**Cambios:**
1. **No** toques `BaseType.is_compatible` (lo usan los valores). Añade un helper estricto, p. ej.
   `_same_pointee(a, b)` en `pengu_types.py`: desenvuelve `AliasType`/`FrozenType`, y compara con `==`;
   decide explícitamente qué excepciones admites (recomendado: **solo `char`↔`byte`**, documentado como
   la equivalencia C `char*`/`uint8_t*`, para que `bytes of s` (que devuelve `ref to byte`) siga
   sirviendo en parámetros `ref to char`/`ref to frozen char`).
2. `RefType.is_compatible` (`pengu_types.py:390-408`): usa `_same_pointee` en lugar de
   `self.target.is_compatible(other.target)`, manteniendo el comodín `void`/`opaque` y la dirección de
   `frozen` (`ref to frozen T` **no** fluye a `ref to T`; `_drops_frozen` debe seguir funcionando).
3. `pengu_parser/pengu_infer.py` (`_passes`, ~2064-2091): aplica la misma regla estricta en la rama de
   punteros y en el decay de arrays (un `array of i32` a `ref to char` debe ser **E0005**; un
   `array of char` a `ref to frozen char` debe seguir pasando).
4. Migra lo que rompa en `std/` y `tests/` (el cambio es deliberadamente estricto): si aparece un sitio
   legítimo, usa `transmute` explícito en el código `.pengu` en vez de relajar la regla; si el sitio es
   sistemático (p. ej. `std/xlsx.pengu` pasando `bytes of s` a `const char*`), documenta la excepción
   `char`↔`byte` como la razón.
5. Documenta la regla en `LANGUAGE.md` §9 (interop) con una tabla de qué convierte y qué no, y añade el
   caso a `CHEATSHEET.md` (tabla de punteros).

**Tests (clase `TestStrictPointers`):**
1. Negativos (`E0005`): `ref to i32`→`ref to char`; `ref to i32`→`ref to byte`; `ref to u8`→`ref to char`;
   `array of i32`→`ref to char`; `ref to f32`→`ref to f64`.
2. Positivos: `ref to char`→`ref to frozen char`; `ref to byte`→`ref to char` (si aceptas esa excepción);
   `sigil of x`→`ref to void`; `array of char`→`ref to frozen char`; `bytes of s`→`ref to frozen void`.
3. `frozen` sigue siendo direccional: `ref to frozen int`→`ref to int` = `E0005` (ya hay tests en
   `tests/test_frozen.py`; no deben romperse).
4. Valores: `var n as int is 5` + `var m as i64 is n` sigue permitido (ampliación numérica intacta).

**Aceptación:** suite completa verde, **los 50 módulos de `std/` chequean juntos** (ver §3) y los ports
01–06 compilan.

---

### P2.6 — `pengu bind` usable con headers reales

**Estado real (verificado hoy):**
| Header | Resultado |
|---|---|
| `build/include/sqlite3.h`, `sqlite3ext.h` | ✅ bindea (¡header real y grande!) |
| `extern/raylib-6.0/src/rlgl.h` | ✅ bindea (667 líneas) |
| `extern/zlib-1.3.2/zlib.h` | ❌ preprocessing: `_mingw.h:295: #error Only Win32 target is supported!` (por el `-U_WIN32` que fuerza `pengu_bind.py:734`) — **con `-DZ_SOLO` + stubs parsea perfecto: 72 decls** |
| `std_c/xxhash.h` | ❌ pycparser: `XXH_PUBLIC_API XXH_CONSTF …` → `before: (`; al blanquear extensiones GNU avanza a `Invalid function definition` |
| `build/include/tomlc17.h` | ❌ pycparser `Invalid declaration` |
| `extern/yaml-0.2.5/include/yaml.h` | ❌ pycparser `Invalid specifier list` |
| `build/include/uv.h`, `microhttpd.h`, `pcre2.h` | ❌ preprocessing (faltan headers de sistema; `-nostdinc` + 13 stubs) |

**Anclas:** `pengu_bind.py:715-763` (`preprocess_and_parse`; flags en `:734`), `c_bind_stubs/` (13 headers),
CLI en `pengu_project.py:2092-2103` (`bind`).

**Cambios:**
1. **Flags nuevos en el CLI y en la API** (`generate_bind_file`):
   `--define/-D NAME[=V]` (repetible), `--cpp-flags "-DZ_SOLO -DXXH_INLINE_ALL=0"` (passthrough crudo),
   `--system-includes` (no pasar `-nostdinc` **y** no desdefinir `_WIN32`/`_MSC_VER`: usa los headers
   reales del compilador — es lo que rompe `_mingw.h` hoy), `--keep-defines` si hace falta,
   `--preprocessed FILE.i` (bindear desde un `.i` que el usuario genere con su propio `gcc/clang -E`).
2. **Blanqueo por defecto de extensiones GNU** en el preprocesado (verificado que mejora el caso xxhash y
   no rompe rlgl/sqlite3): `-D__attribute__(x)= -D__attribute__= -D__extension__= -D__restrict=
   -D__restrict__= -D__inline__=inline -D__inline=inline -D__asm__(x)= -D__asm__= -D__declspec(x)=
   -D__volatile__=volatile`. Añade un flag `--no-blank-extensions` para desactivarlo.
3. **Stubs nuevos** en `c_bind_stubs/`: al menos `pthread.h`, `sys/types.h`, `unistd.h`, `limits.h`,
   `fcntl.h` (mínimos, con los tipos/funciones que usan los vendors). Documenta en un README corto
   (`c_bind_stubs/README.md`) qué son y cómo ampliarlos.
4. **Diagnóstico accionable**: cuando falle, imprime (a) el último error del preprocesador con su línea,
   (b) el texto exacto preprocesado alrededor del punto donde pycparser se atasca, y (c) una sugerencia
   concreta: «prueba `--define Z_SOLO`», «prueba `--system-includes`», «prueba `--preprocessed`». Hoy el
   mensaje es genérico y hace perder mucho tiempo.
5. **Tests** (`tests/test_p2_bind.py` o dentro de `tests/test_p2_features.py`):
   - regresión: `build/include/sqlite3.h` y `extern/raylib-6.0/src/rlgl.h` bindean y el `.d.pengu`
     resultante pasa `pengu check`;
   - nuevo éxito: `extern/zlib-1.3.2/zlib.h --define Z_SOLO` bindea, el binding pasa `pengu check` y un
     programa mínimo que llame a `zlibVersion()` compila (link `-lz`) y ejecuta;
   - diagnóstico: un header que sigue fallando (`std_c/xxhash.h`) produce un mensaje que menciona el
     constructo y una de las sugerencias.
6. Documenta en `README.md` (sección `pengu bind`) y `CHEATSHEET.md`: flags nuevos, cuándo usar
   `--system-includes` y cuáles de los bindings incluidos siguen siendo artesanales y por qué.

**Aceptación:** los tests pasan; `zlib` es el primer header de terceros que antes fallaba y ahora se
bindea de punta a punta.

---

## 3. Verificación obligatoria (antes de cerrar cada hito grande y al final)

```powershell
# 1. tests focalizados
.\.venv\Scripts\python.exe -m pytest tests/test_p2_features.py tests/test_p1_features.py tests/test_p0_toolchain.py -q -p no:cacheprovider

# 2. suite completa
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider

# 3. los 50 módulos de std/ juntos (genera el entry y comprueba)
.\.venv\Scripts\python.exe -c "import glob,os; mods={os.path.basename(f)[:-6].removesuffix('.d') for f in glob.glob('std/*.pengu')}; mods.discard('whisper'); open('scratch/all_std_p2.pengu','w',encoding='utf-8').write('# auto\n'+''.join(f'import std.{m}\n' for m in sorted(mods))+'\nweave main into int:\n    return 0\n')"
.\.venv\Scripts\python.exe pengu_project.py check --entry scratch\all_std_p2.pengu

# 4. ports raylib 01–06 compilan (y 04–06 además ejecutan ~120 frames)
foreach ($f in @("01_core_basic_window","02_core_input_keys","03_shapes_basic_shapes","04_text_format_text","05_rotating_cube_raymath")) {
  Remove-Item build\app.exe,build\bundle.c,build\.bundle_hash -ErrorAction SilentlyContinue
  .\.venv\Scripts\python.exe pengu_project.py build --entry "scratch\port\$f.pengu"
}

# 5. bindings regenerables sincronizados
.\.venv\Scripts\python.exe regen_std_bindings.py --check
```

Actualiza además `CHANGELOG.md` (bloque `### P2 — …`), `README.md` (mueve a "works" lo completado) y
`PRODUCTION_READINESS.md` (§7 P2: marca ✅ lo hecho y ajusta el veredicto final).

---

## 4. Trampas conocidas (no las reintroduzcas)

1. **`#line`**: se emite por sentencia/definición y se suprime en contexto de expresión (el `({…})` puede
   caer dentro del macro `pengu_to_string(x)`). Tests: `tests/test_p0_toolchain.py::TestLineDirectives`.
2. **Caché del builder**: clave = contenido (entry + módulos + C glue). Si añades un `.c` nuevo,
   comprueba que entra en `collect_c_sources()`.
3. **`at` es postfix** (P1): `xs at i + 1` = `(xs at i) + 1`; el target exige paréntesis. Tests:
   `tests/test_p1_features.py::TestAtIndexSemantics`.
4. **Registro doble de runes** (`Vector2` y `raylib_Vector2`): cualquier búsqueda que itere
   `symbols.runes.values()` debe de-duplicar por firma.
5. **Varargs de C** (`declare … , ...`): los argumentos extra **no** se checan ni se envuelven; un string
   extra debe escribirse `bytes of s`.
6. **`banish`** solo acepta lvalues: no permitas que un cambio en P2.4 deje pasar temporales.
7. PowerShell: evita `Select-String` con `|` en el patrón (el shell se lo come).

## 5. Qué NO hacer

- No añadas features fuera de esta lista (uniones, bitfields, `goto`, `var` de módulo…).
- No relajes el chequeo de tipos para "hacer pasar" un test de P2.5: migra el sitio con `transmute`.
- No toques `extern/`, ni regeneres los bindings artesanales, ni commitees.
- No dejes `print()` de depuración en el compilador.

## 6. Definición de "hecho" (P2 completo)

1. Arrays 2D: sintaxis completa, codegen `T[o][i]` correcto, índice/escritura/length, errores claros,
   tests compile+run y docs.
2. `banish` funciona con `string`/`list`/`map` (y `defer banish …`), con negativos claros y docs de
   propiedad de memoria.
3. Estado de módulo documentado con dos patrones y un test que demuestra persistencia por módulo.
4. `std/rlgl.d.pengu` convive con `std/raylib` y hay un ejemplo con rlgl que compila y ejecuta.
5. Tipado estricto de punteros: pointee exacto (con `void`/`opaque` y `frozen` como excepciones
   documentadas), suite y 50 módulos verdes.
6. `pengu bind` gana `--define/--cpp-flags/--system-includes/--preprocessed`, blanqueo de extensiones,
   stubs nuevos, diagnóstico accionable y al menos `zlib.h` bindeado de punta a punta.
7. `tests/test_p2_features.py` (+ `tests/test_p2_bind.py`) con ≥ 20 tests verdes, suite completa verde,
   `P2_PROGRESS.md` completo y CHANGELOG/README/PRODUCTION_READINESS actualizados.

## 7. Handoff obligatorio: `P2_PROGRESS.md`

Crea `P2_PROGRESS.md` en la raíz **antes de empezar** con el baseline (cópialo de `P1_PROGRESS.md`:
suite 767 passed + 1 skipped, P0/P1 cerrados, ports 01–05) y actualízalo **tras cada hito**:

```markdown
# P2 progress (handoff)

Última actualización: <fecha/hora> · Agente: <modelo>

## Baseline (no borrar)
- Suite: 767 passed, 1 skipped · P0 y P1 cerrados · ports 01–05 OK

## Estado por hito
| Hito | Estado | Evidencia |
|------|--------|-----------|
| P2.2 arrays 2D | ⬜/🟡/✅ | tests, comando, resultado |
| P2.4 banish string/list/map | ... | ... |
| P2.3 estado de módulo | ... | ... |
| P2.1 rlgl | ... | ... |
| P2.5 punteros estrictos | ... | ... |
| P2.6 pengu bind real | ... | ... |

## Cambios de archivos (exactos, con líneas)
## Tests (nombres, resultado de la última corrida, suite completa)
## Lo que falta / siguiente paso concreto (archivo:línea + comando)
## Bloqueos y decisiones
```

Reglas: escribe tras cada hito (no al final); sé literal (rutas, líneas, comandos y salida resumida);
si algo queda a medias, el árbol debe compilar y pasar la suite, y lo incompleto debe estar **revertido a
mano** (nunca con `git checkout`) y documentado; si te quedas sin presupuesto, prioriza cerrar P2.2 y P2.4
(los que arreglan C inválido y fugas) aunque el resto quede sin empezar.
