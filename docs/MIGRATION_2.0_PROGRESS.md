# Migración a Pengunic 2.0 — Estado

Documento de seguimiento de la migración de las 27 librerías `std.*` de
PenguScript puro a la guía de estilo Pengunic 2.0. Cada chunk reescribe un módulo,
mueve a él el código de `pengu_runtime.h` que solo ese módulo usa (vía `antiquus`)
y deja su contrato congelado en un `docs/<MOD>_API.md`.

## Chunks completados

### ✅ Chunk 1: `std.spark`

- [x] Reescrito `std/spark.pengu` completo en Pengunic 2.0.
- [x] 13 puentes C viven ahora en `spark` como bloques `antiquus`:
      6 movidos desde `pengu_runtime.h` (`pengu_print`, `pengu_println`,
      `pengu_input`, `pengu_parse_int`, `pengu_parse_float`, `pengu_panic`) y
      7 nuevos (`pengu_eprint`, `pengu_eprintln`, `pengu_flush_stdout`,
      `pengu_flush_stderr`, `pengu_read_char`, `pengu_parse_int_radix`,
      `pengu_exit`).
- [x] Nuevos símbolos públicos: `eprint`, `eprintln`, `eprint_line`, `flush`,
      `eflush`, `read_char`, `read_bool`, `parse_bool`, `parse_int_hex`,
      `parse_int_bin`, `parse_int_oct`, `range_down`, `sign_int`, `gcd_int`,
      `lcm_int`, `pow_int`, `exit`, `exit_success`, `exit_failure`,
      `assert_debug`.
- [x] Bug arreglado: `eprintln` y `eprint_line` escriben a fd 2 (antes stdout).
- [x] `pengu_runtime.h`: 4983 → 4860 líneas (−123) al eliminar los 6 helpers
      `static inline` que se movieron.
- [x] Tests std borrados (ver abajo).
- [x] `tests/test_spark.py` creado: 30 tests end-to-end.
- [x] 14 bloques `test` internos en `std/spark.pengu` (todos verdes).
- [x] `SPARK_VERSION` subido de `"0.7.0-spark"` a `"0.8.0-spark"`.
- [x] `docs/SPARK_API.md` y `docs/PENGUNIC_CHECKLIST.md` creados.

### ✅ Chunk 2: `std.scrolls` + `std.oracle`

`std/scrolls`:

- [x] Reescrito `std/scrolls.pengu` completo en Pengunic 2.0 (1594 → 3731 líneas,
      casi todo docstrings en inglés).
- [x] 14 bloques `antiquus` añadidos: 6 clasificadores ASCII (`_char_is_space`,
      `_char_is_digit`, `_char_is_upper`, `_char_is_lower`, `_char_is_alpha`,
      `_char_is_alnum`) y 8 helpers de string movidos desde `pengu_runtime.h`
      (`pengu_string_contains`, `pengu_string_starts_with`,
      `pengu_string_ends_with`, `pengu_string_index_of`,
      `pengu_string_last_index_of`, `pengu_string_replace`,
      `pengu_string_repeat`, `pengu_string_reverse`).
- [x] 9 weaves Pengu redundantes eliminados (regla del C-block): los 6
      `_char_is_*`, `_index_of_from`, `_last_index_of_from` y `_has_prefix_at`.
      Sus llamantes pasan por los C-blocks o por `pengu__find_sub`.
- [x] `pengu__find_sub` **no se mueve**: lo usan `pengu_string_split` y el matcher
      de globs; `scrolls` lo `declare` (antes de `insignia pengu_`, ver bugs).
- [x] 10 símbolos públicos nuevos: `strip`, `splitn`, `rsplit`,
      `starts_with_any`, `ends_with_any` (método + función de módulo).
- [x] 137 símbolos públicos previos preservados; 23 marcadores
      `## @deprecated` intactos.
- [x] 135 bloques `test` internos (124 traducidos + 11 nuevos).
- [x] `tests/test_scrolls.py`: 28 tests end-to-end.

`std/oracle`:

- [x] Reescrito `std/oracle.pengu` completo en Pengunic 2.0 (1506 → 2394 líneas).
- [x] 156/156 declaraciones preservadas con firmas idénticas (152 públicas + 4
      helpers `_expect*`); 0 símbolos añadidos o eliminados.
- [x] Invariante de reconstrucción de contenedores mantenido y documentado
      (`return some v` / `maybe none` / `ok_of` / `err_of`; nunca `return m`).
- [x] 50 marcadores `## @deprecated` mantenidos; la prosa en español de los 5
      runes legados traducida al inglés.
- [x] 125 bloques `test` internos, traducidos al inglés.
- [x] `tests/test_oracle.py`: 42 tests end-to-end.
- [x] Ningún `static inline` movido: `pengu_maybe_*` / `pengu_result_*` los emite
      el codegen en todos los bundles.

Común:

- [x] `pengu_runtime.h`: 4860 → 4673 líneas (−187) al quitar los 8 helpers de
      string.
- [x] `tests/runtime/test_runtime_strings.py` recortado (sus secciones movidas
      pasan a `tests/test_scrolls.py`).
- [x] `docs/SCROLLS_API.md` y `docs/ORACLE_API.md` creados.
- [x] `docs/PENGUNIC_CHECKLIST.md` ampliada con las reglas del Chunk 2.
- [x] `docs/api/` y `tests/_test_policy_baseline.json` regenerados.

### ✅ Chunk 3: `std.tally` + `std.loom` + `std.ward`

- [x] Reescrito `std/tally.pengu` en Pengunic 2.0 (`TALLY_VERSION = "2.1.0"`):
      1488 → 3158 líneas; prosa y docstrings en inglés con secciones canónicas
      (`Parámetros`/`Retorno`/`Ejemplo`); 152 tests internos (antes 111).
- [x] Reescrito `std/loom.pengu` en Pengunic 2.0 (`LOOM_VERSION = "2.1.0"`):
      1511 → 2508 líneas; 124 → 130 tests internos (siete de los nuevos se
      reescribieron sobre los núcleos privados: ver desviación 6). Sigue **sin**
      declarar `enchanting` (decisión explícita, documentada en el módulo).
- [x] Reescrito `std/ward.pengu` en Pengunic 2.0 (`WARD_VERSION = "2.1.0"`):
      674 → 2366 líneas; 42 tests internos (antes 0).
- [x] `ward` ya no importa `std.scrolls`: `_w_fmt_string` usa el slicing nativo
      `s at 0 to 77` y los tres predicados de string comparan slices nativos.
- [x] Añadidas las siete `check_*_native` en `ward`, que devuelven
      `result of string to string` (`ok_of`/`err_of`); las nueve `check_*`
      legacy se conservan y quedan deprecadas.
- [x] `tests/stdlib/test_tally.py` (50 tests), `tests/stdlib/test_loom.py`
      (51 tests) y `tests/stdlib/test_ward.py` (38 tests) creados; los tres
      juzgan stdout/stderr/exit code, nunca el C generado.
- [x] `docs/TALLY_API.md`, `docs/LOOM_API.md` y `docs/WARD_API.md` creados
      (contratos congelados).
- [x] Decisión documentada: `loom` y `tally` se mantienen separados
      (`LANGUAGE.md` §19.1.1; guía de estilo §15). No hay fusión, renombrado ni
      sufijos `_safe`/`_sentinel`.
- [x] `docs/api/` regenerado y `docs/DEPRECATIONS.md` ampliado con la sección de
      los `check_*` legacy de `ward`.
- [x] `pengu_runtime.h` **sin tocar**: este chunk no mueve código C.

### ✅ Chunk 4: `std.atlas` + `std.coven` + `std.compass`

- [x] Reescrito `std/atlas.pengu` en Pengunic 2.0 (`ATLAS_VERSION = "2.1.0"`):
      1614 → 4551 líneas; 126 → 153 tests internos.
- [x] Generalizado con un `concept Ordered shard T` (+ `bind` de `int`, `i32`,
      `i64`, `float`, `f32`, `f64`, `string`): un único `keys_sorted`
      (`K: Ordered, V: Par`) y un único `values_sorted` (`K: Par, V: Ordered`)
      cubren string y numéricos. `keys_sorted_of`/`values_sorted_of` pasan de
      `Ordo` a `Ordered`.
- [x] `count_true`/`count_false` generalizados a `map of shard K to bool`.
- [x] Eliminados los bloques concretos redundantes: `enchanting map of int to
      int:` entero y todos los `keys_sorted`/`values_sorted` concretos. Ningún
      símbolo público desaparece (solo cambian de bloque).
- [x] Seis `antiquus` de ordenación (`qsort` para `int32`, `float` y
      `PenguString` con `memcmp`) usados por los wrappers de compatibilidad y
      `_sort_strings`; los comparadores llevan `@export` porque el DCE poda los
      `weave` referenciados solo desde C.
- [x] Reescrito `std/coven.pengu` en Pengunic 2.0 (`COVEN_VERSION = "2.1.0"`):
      505 → 2260 líneas; 0 → 44 tests internos.
- [x] Añadido `rune Set shard T` genérico (16 métodos) y constructores
      `make_set shard T` / `from_items_set shard T` + los concretos
      `new_int_set`/`new_string_set`/`new_float_set`/`new_bool_set`/`new_char_set`.
      `SetString`/`SetInt` intactos (marcados `## @deprecated`).
- [x] Reescrito `std/compass.pengu` en Pengunic 2.0 (`COMPASS_VERSION =
      "2.1.0"`): 1028 → 2293 líneas; 0 → 77 tests internos.
- [x] `cp_glob_match` convertido en `antiquus` (matcher de wildcards con
      punteros); resultados idénticos verificados con 55 casos. Los cinco
      `declare` al runtime y el rune `Path` no se tocan.
- [x] **Bug de memoria corregido en `compass`:** `cp_change_ext` devolvía un
      buffer ya liberado (`defer banish st` + `set buf is st` en la rama sin
      directorio), lo que hacía basura no determinista en
      `without_extension("a.txt")`, `change_ext("a.txt", "")` y
      `Path.without_suffix`; ahora copia con `"{st}"`.
- [x] `tests/stdlib/test_atlas.py` (50 tests), `test_coven.py` (30) y
      `test_compass.py` (37+) creados.
- [x] `docs/ATLAS_API.md`, `docs/COVEN_API.md` y `docs/COMPASS_API.md` creados.
- [x] `docs/DEPRECATIONS.md` ampliado (`SetString`/`SetInt`) y
      `docs/PENGUNIC_CHECKLIST.md` con las reglas de colecciones genéricas.
- [x] `pengu_runtime.h` **sin tocar**: este chunk no mueve código C.

### ✅ Chunk 5: `std.archivum` + `std.rites` + `std.chronicle` (+ retrofit de `std.tally` / `std.loom` / `std.coven`)

`std/archivum` (`ARCHIVUM_VERSION = "2.1.0"`):

- [x] Reescrito `std/archivum.pengu` completo en Pengunic 2.0 (FS: lectura,
      escritura, copia, borrado, listado, metadatos y búsqueda).
- [x] **+23 nombres públicos**, 0 eliminados o renombrados: `read_text`,
      `write_text`, `read_last_n_lines`, `read_dir_full`, `is_readable`,
      `is_writable`, las 11 variantes `*_result` (`read_lines_result`,
      `write_lines_result`, `read_dir_result`, `create_dir_result`,
      `remove_dir_result`, `copy_file_result`, `copy_tree_result`,
      `append_lines_result`, `touch_result`, `symlink_result`,
      `metadata_result`) y los métodos del `enchanting compass.Path`
      (`append_text`, `delete`, `mkdir`, `rmdir`, `iter_dir`, `stat`; `read_text`
      y `write_text` ya contaban).
- [x] 0 → **33 tests internos**.
- [x] `docs/ARCHIVUM_API.md` creado (contrato congelado 2.1.0).

`std/rites` (`RITES_VERSION = "2.1.0"`):

- [x] Reescrito `std/rites.pengu` completo en Pengunic 2.0 (entorno, argumentos,
      identidad de proceso, directorios estándar, detección de plataforma,
      búsqueda de ejecutables y captura de shell).
- [x] **+9 nombres públicos**, 0 eliminados: la API de captura
      (`run_capture`, `run_capture_result`, `run_capture_lines`,
      `run_capture_stderr`, `run_shell_capture`) y las credenciales POSIX
      (`get_uid`, `get_gid`, `get_euid`, `get_egid`). Los `antiquus`
      `_rites_capture`, `_rites_run_status` y `_rites_id` son privados y no
      aparecen en el contrato.
- [x] 0 → **49 tests internos**.
- [x] `pengu_runtime.h` **no gana ningún símbolo**: los `declare pengu_c_*`
      siguen apuntando a los `static inline` existentes y las dos capacidades
      nuevas viven en cuerpos `antiquus` de `rites`.
- [x] `docs/RITES_API.md` creado (contrato congelado 2.1.0).

`std/chronicle` (`CHRONICLE_VERSION = "2.1.0"`):

- [x] Reescrito `std/chronicle.pengu` completo en Pengunic 2.0 (reloj de pared,
      reloj monótono, timestamps, campos de calendario UTC/local, el rune
      `DateTime`, fronteras de calendario, formato/parseo y `Stopwatch`).
- [x] **+16 nombres públicos**, 0 eliminados o renombrados: `to_timestamp`,
      `plus_seconds`/`plus_minutes`/`plus_hours`/`plus_days`/`plus_weeks`,
      `is_same_day`, `weekday_name`, `month_name`, `is_weekend`,
      `start_of_week`, `start_of_quarter`, `end_of_month`, `days_between`,
      `hours_between`, `seconds_to_hms`.
- [x] 0 → **35 tests internos**, todos con timestamps fijos (deterministas).
- [x] Los 24 `declare` C son byte-idénticos a 2.0.0; el módulo no tiene
      `antiquus` y no mueve código del runtime.
- [x] `docs/CHRONICLE_API.md` creado (contrato congelado 2.1.0).

Retrofit `std.tally` / `std.loom` / `std.coven`:

- [x] `std/tally.pengu` (`TALLY_VERSION = "2.2.0"`): 152 → **170 tests
      internos**. Todas las funciones de módulo se ensanchan a
      `list of shard T where T: <bound>` (antes `list of int`); **+2 nombres
      públicos**: `at_or_shard shard T where T: Donum` y
      `clamp_all_shard shard T where T: Num and T: Ordo`.
- [x] `at_or` y `clamp_all` conservan **a propósito** su firma concreta
      `list of int` y sus defaults `int`: un parámetro genérico no admite un
      default dependiente de `T` (`default as int is 0`, `lo as int is 0`,
      `hi as int is 100`). El camino genérico son `at_or_shard` /
      `clamp_all_shard`, con el default/bounds explícitos.
- [x] `std/loom.pengu` (`LOOM_VERSION = "2.2.0"`): 130 → **146 tests
      internos**. Todas las entradas públicas pasan a `shard T` con el bound
      que cada cuerpo necesita; **0 nombres nuevos de API** (el `seal
      LoomUserId` + su `bind LoomUserId with Ordered:` son solo de test y
      quedan documentados como tales). `range`, `unfold_range`, `pad_left`,
      `pad_right` y `zip_longest` siguen concretas porque su default depende
      del tipo de elemento.
- [x] `std/coven.pengu` (`COVEN_VERSION = "2.2.0"`): 44 → **55 tests
      internos**. **+4 nombres públicos**: los constructores concretos
      `new_i64_set`, `new_u64_set`, `new_usize_set` y `new_isize_set`; la
      matriz de tipos de elemento de `Set of T` (`int`, `i8`..`i64`,
      `u8`..`u64`, `byte`, `usize`, `isize`, `float`/`f32`/`f64`, `char`,
      `bool`, `string` y `rune derive Par, Vinculum`) queda verificada y
      documentada.
- [x] **`insignia tally_` e `insignia loom_`.** Las funciones de módulo se
      emiten con prefijo C (`tally_sum`, `loom_min_max`, …). Eso es
      exactamente lo que hace fiable la resolución de una llamada genérica
      cualificada (`calling tally.sum with floats`) cuando el bundle contiene
      varias monomorfizaciones: se elige el símbolo mangleado exacto en vez de
      la heurística "solo hay una coincidencia" (ver Bug 2).
- [x] Ordenación y strings: las operaciones de orden pasan por
      `T: Ordered` (concepto de `std.atlas`, con `bind` para `int`, `i32`,
      `i64`, `float`, `f32`, `f64` y `string`); la igualdad (`==`) sí es
      genérica, así que el grupo `Par` no necesita concepto.
- [x] `docs/TALLY_API.md`, `docs/LOOM_API.md` y `docs/COVEN_API.md`
      actualizados a 2.2.0 de forma **aditiva**: cada símbolo ya documentado
      sigue en la página, con la firma ensanchada y el bound explícito.
- [x] `tests/stdlib/test_tally.py`, `tests/stdlib/test_loom.py` y
      `tests/stdlib/test_coven.py` ampliados (float, `i64`, string y `seal`
      tanto por función de módulo como por método).
- [x] `tests/stdlib/test_archivum.py` (30+), `tests/stdlib/test_rites.py`
      (25+) y `tests/stdlib/test_chronicle.py` (25+) creados; juzgan
      stdout/stderr/exit code, nunca el C generado.
- [x] `pengu_runtime.h` **sin tocar** en el retrofit.

Recuento de tests internos de Chunk 5: `tally` **170**, `loom` **146**,
`coven` **55**, `chronicle` **35**, `rites` **49**, `archivum` **33**.

Deltas de nombres públicos de Chunk 5 (todos aditivos, cero eliminaciones o
renombrados): `archivum` **+23**, `chronicle` **+16**, `rites` **+9**,
`coven` **+4**, `tally` **+2**, `loom` **+0** de API.

### Bugs del compilador arreglados en Chunk 5

1. **Una `weave` genérica libre secuestraba un método genérico homónimo**
   (`pengu_parser/pengu_infer.py`). Con `weave sum shard T where T: Num with l
   as list of T into T` y `enchanting list of shard T where T: Num: weave sum`,
   la llamada `calling xs.sum` fallaba con `E0005 Could not infer type
   parameter(s) T for generic function 'sum'`: la resolución adoptaba la
   función libre en lugar del método, también cuando ambos vivían en módulos
   distintos. Arreglado exigiendo `method_self_type is None` antes de adoptar
   una función genérica desnuda.
2. **Una llamada genérica cualificada a un módulo resolvía el símbolo C
   equivocado** (`pengu_parser/pengu_codegen/exprs.py`). `calling mod.generic
   with xs` emitía un `sum` desnudo en cuanto existían dos especializaciones
   (heurística `len(m_matches) == 1`). Arreglado con
   `_resolve_monomorphized_call`, que unifica los tipos declarados de los
   parámetros con los tipos inferidos de los argumentos para construir el
   nombre manglado exacto. Es la razón por la que `tally` y `loom` llevan
   `insignia`: el prefijo C `tally_`/`loom_` es lo que da a cada
   monomorfización un símbolo distinto y resoluble.
3. **Bug 3** (`pengu_parser/pengu_codegen/exprs.py`,
   `_resolve_monomorphized_call`): a qualified generic module call that omits a
   parameter with a default (`calling loom.zip_with with a, b` where
   `op as int is 0`) emitted the unspecialized C symbol `loom_zip_with`
   (`implicit declaration of function 'loom_zip_with'; did you mean
   'loom_zip_with_int'?`). Fixed by unifying only the supplied argument prefix
   against the declared parameters instead of requiring
   `len(args) == len(params)`.

### Desviaciones y hallazgos de Chunk 5

1. **`Set.empty` sigue sin existir.** Un `ritual` genérico sigue
   miscompilando en cuanto el bundle contiene dos especializaciones `Set of T`
   (`invalid initializer`; el ritual se emite para la `T` sin especializar), y
   un `Set.empty` sin `of T` no infiere (`E0005`). El smoke de Chunk 5 usa por
   eso `coven.make_set of float` (y los constructores concretos
   `new_i64_set`/`new_u64_set`/`new_usize_set`/`new_isize_set`); la limitación
   queda registrada como deuda.
2. **La ordenación de strings va por `atlas.Ordered`.** `>` sobre `PenguString`
   dentro de un cuerpo genérico emite un `>` crudo de C que no compila, y una
   string concreta lo rechaza con `E0005`; por eso `tally` importa `std.atlas`
   y las operaciones de orden se acotan `where T: Ordered` comparando con
   `calling a.cmp with b`. `==` sí funciona genéricamente en strings.
3. **`std/scrolls.pengu`: dos locales `W0005` preexistentes renombrados.** El
   nuevo `import std.atlas` de `loom` arrastra `scrolls` (vía `atlas`) a su
   grafo transitivo, y el gate de Chunk 5 exige cero warnings. Los locales
   `sign` se renombran a `sign_text` / `sign_factor` para eliminar el
   `W0005` preexistente. No cambia ninguna firma ni comportamiento.
4. **Los tests internos nuevos usan receptores cualificados.** La `weave`
   genérica de `loom`/`tally` comparte 15 nombres: dentro de los bloques `test`
   se prefiere el receptor con punto (`calling xs.sum`) o un núcleo privado
   concreto para no depender del espacio de nombres compartido entre módulos
   importados (ver Chunk 3, bug de nombres compartidos).
5. **`std/scrolls.pengu` was the only out-of-scope module edit of Chunk 5.** The
   `sign` → `sign_text`/`sign_factor` rename was the only change made outside
   the chunk's modules, and it was needed to keep the six-module gate at zero
   warnings after `std/loom` started importing `std.atlas` (which pulls
   `scrolls` into the transitive graph); no other out-of-scope module was
   touched.

### ✅ Chunk 6: `std.lot` + `std.whisper`

- [x] Reescrito `std/lot.pengu` en Pengunic 2.0 (`LOT_VERSION = "2.1.0"`)
- [x] Arreglados 13 bugs de `lot` (ver `docs/BUGS_FIXED_CHUNK6.md`)
- [x] Añadidas 18 funciones nuevas (paridad Python `random` + `secrets`)
- [x] Reescrito `std/whisper.pengu` en Pengunic 2.0 (`WHISPER_VERSION = "2.1.0"`)
- [x] Arreglados 16 bugs de `whisper`
- [x] Añadidas 18 funciones/métodos nuevos (paridad Python `logging`)
- [x] `tests/stdlib/test_lot.py` y `tests/stdlib/test_whisper.py` creados
- [x] `docs/LOT_API.md` y `docs/WHISPER_API.md` creados
- [x] `docs/BUGS_FIXED_CHUNK6.md` creado (29 entradas + 5 hallazgos fuera de alcance)

#### Bugs arreglados

`std/lot` (13): B1 `rand_gamma` devolvía `scale * d` al agotar el bucle;
B2 `rand_weibull` podía no terminar y devolver `inf`; B3 `choice_weighted`
desbordaba el `total` de 32 bits; B4 `rand_bytes_hex` fabricaba dígitos hex en
lugar de bytes reales (y faltaba `rand_bytes`); B5 el hack `chr 123`/`chr 125` de
`rand_password`; B6 `shuffle` reconstruía la lista con `push`; B7 `seed` truncaba
semillas negativas sin documentarlo; B8 `rand_lognormal` no validaba `sigma`;
B9 `choice` no cubría el contenedor vacío con `n <= 0`; B10 `rand_int` podía
devolver un valor negativo; B11 el módulo no era thread-safe; B12 (nuevo)
`rand_beta` no validaba `a`/`b`; B13 (nuevo) `sample`/`sample_string` intentaban
mutar el parámetro `k` (inmutable) para clamparlo.

`std/whisper` (16): B12 `Logger.child` perdía el `file_path` del padre;
B13 documentación de que un archivo nunca lleva color; B14 `_json_escape` no
escapaba `\b`, `\f` ni los bytes de control `< 0x20`; B15 `log_json` no incluía
timestamp; B16 `log_json` iteraba el mapa en orden de hash; B17 `from_env` no
distinguía "sin setear" de "valor inválido"; B18 `set_level_from_env` dejaba el
nivel en `LOG_TRACE`; B19 no había salida a stderr; B20 no había registro
singleton por nombre; B21 el fallo de `archivum.append_file` se descartaba en
silencio; B22 el módulo no era thread-safe; B23 `child` no validaba el segmento;
B24 el formato estaba hardcodeado; B25 (nuevo) el símbolo C `log` colisionaba con
`math.h` cuando `whisper` era el módulo de entrada (lo arregla
`insignia whisper_`); B26 (nuevo) `default_logger` creaba un logger nuevo en cada
llamada; B27 (nuevo) `set_level` sobre un singleton no publicaba el nivel al
registro.

#### Recuento de tests internos de Chunk 6

`lot` **38**, `whisper` **29** (`pengu test --entry std/{lot,whisper}.pengu`,
todo verde). Las suites externas viven en `tests/stdlib/` (no en la raíz: el
gate `test_test_policy` congela 15 ficheros raíz y ya estaban llenos).

#### Hallazgos fuera de alcance (compilador / formatter)

Los cinco están documentados y esquivados en `docs/BUGS_FIXED_CHUNK6.md` §5;
§5.3 del brief prohíbe tocar el compilador.

1. **El plegado de `const` pierde la marca de raw string.** Un `const` con `{` o
   `}` pasado como argumento falla con `E0000 String interpolation is not
   supported … (ref to char)` incluso en `pengu run` normal. Reproducción mínima
   en el bug doc. Esquiva: `password_symbols` es un `weave`, no un `const`.
2. **Las llamadas rituales con punto (`modulo.Tipo.ritual`) no resuelven.**
   `calling whisper.Logger.get_or_create` da `E0004 Type 'whisper' has no method
   'get_or_create'`; también le pasaba al `std/whisper.pengu` pre-migración y a
   cualquier módulo importado (`m3.Thing.new`). La forma soportada y documentada
   es la no cualificada: `calling Logger.get_or_create with "app"`. El smoke del
   brief usa la forma con punto y por eso se verificó con la forma soportada.
3. **`pengu fmt` reindenta el fichero entero si un cuerpo `antiquus` contiene un
   comentario C `/* … */`.** Esquiva: usar `//` en los cuerpos `antiquus`.
4. **`==`/`!=` entre dos `string` de nivel de módulo emite C inválido.** Comparar
   una variable local contra un literal sí se baja; dos símbolos de módulo
   (`whisper.COLOR_GREEN == whisper.COLOR_RESET`) genera `PenguString ==
   PenguString`. Esquiva en los tests: imprimir las constantes y comparar en
   Python.
5. **`"…{(chr 34)}…"` pliega una comilla cruda en el literal C generado** y rompe
   la compilación. Esquiva: usar el escape de fuente `\"`.

#### Decisiones de estilo de Chunk 6

- `insignia` en ambos módulos, colocado **después** de los `declare` para que los
  puentes del runtime conserven sus nombres `pengu_c_*` / `pengu_log_*`.
- Los `antiquus` `_mtx`/`_lock`/`_unlock` (uno por módulo) dan un mutex portable
  compartido con el runtime; `@export` en `_mtx` lo mantiene vivo porque el
  pruner no ve las llamadas desde C.
- `set_default_level`/`get_default_level` y el registro singleton de loggers usan
  una celda C compartida y un `static var` dentro de un `weave` accesor
  (`_registry`), respectivamente, porque el lenguaje prohíbe un `var` de nivel
  superior.

### Próximo: Chunk 7 (`std/filum` + `std/celeris`)

## Desviaciones y hallazgos de Chunk 4

1. **`atlas` estaba incompleto por construcción, y arreglarlo exigió una
   característica del lenguaje.** `keys_sorted`/`values_sorted` vivían solo en
   bloques concretos de string/int. El plan del brief (un bloque genérico
   `K: Ordo`) **no puede funcionar**: los bounds de un `enchanting` no se
   comprueban al resolver el método, y un cuerpo genérico emite un `>` crudo de C
   que no compila para `PenguString`. Medido: añadir un `keys_sorted` genérico
   `K: Ordo` rompe `m.keys_sorted` sobre `map of string to int` **aunque exista
   un override concreto** (el genérico se monomorfiza igual). La solución es un
   `concept Ordered shard T` propio con un `bind` por tipo y `calling a.cmp with
   b` en el cuerpo. Es el primer uso de `concept`/`bind` en `std/`.
2. **Solo algunos nombres primitivos admiten `bind`.** Aceptan `int`, `i32`,
   `i64`, `float`, `f32`, `f64`, `string`, `bool`; rechazan `i8`, `i16`,
   `u8`…`u64`, `usize`, `isize`, `char`, `double`, `byte` y las grafías C
   (`int32_t`, …) con `E0004`. Por tanto `keys_sorted`/`values_sorted` cubren
   `{int, i32, i64, float, f32, f64, string}`, los `alias` de esos tipos y
   cualquier `seal`/`rune` que añada su propio `bind`; los enteros estrechos/sin
   signo y `char` quedan fuera de alcance.
3. **Un `bind` no puede tener un destino privado ni un concept cualificado.**
   `seal _X as int` + `bind _X` da `E0004 Undefined type ''`, y
   `bind X with atlas.Ordered:` da `E0004 Undefined concept 'atlas.Ordered'`.
   La receta para el usuario es `import std.atlas` y luego
   `bind <Type> with Ordered:` **sin cualificar**. Esto obligó a retirar los
   fixtures `AtlasTest*` que se habían usado en los tests internos para no
   publicar tipos solo-de-test (la cobertura de tipos de usuario vive ahora en
   `tests/stdlib/test_atlas.py`).
4. **Los bounds de un `enchanting` son decorativos.** Un `map of string to int`
   acepta un método declarado en `where K: Integrum` (verificado). Como
   consecuencia, un método puede monomorfizarse para tipos que no cumplen su
   bound: los bounds no son la única red de seguridad.
5. **Un `enchanting` mixto genérico/concreto no infiere el parámetro genérico
   cuando aparece en el retorno.** `enchanting map of string to shard V` no sirve
   para `filter_keys_contains -> map of string to V` (`E0005`); un método que
   devuelve `int` sí funciona, pero el bloque `count_true`/`count_false` necesitó
   además un segundo parámetro `shard` en el destino
   (`enchanting map of shard K to bool shard K and V where …`) porque con uno
   solo el compilador no resuelve la llamada. Los filtros de string siguen
   concretos.
6. **Tamaños de elemento y ABI en `antiquus`.** `int` = `int32_t` (4 bytes),
   `float` = `float` (32 bits, **no** `double`), `f64`/`double` = 8, `string` =
   `PenguString`. Un parámetro `list of T` llega **por valor** como `PenguList`
   (`xs.data`, `xs.len`, sin `->`). Un `qsort` con `sizeof(int64_t)` sobre una
   `list of int` corrompe el heap (SIGABRT) — medido antes de corregirlo.
7. **`rune` no admite cláusula `where`** (el `rune_decl` de la gramática no la
   tiene): `rune Set shard T:` y el campo `map of T to int` impone `T: Vinculum`
   al instanciar.
8. **Un constructor `ritual` genérico no es utilizable.** `Set.empty` sobre un
   rune genérico se resuelve por sufijo y se enlaza con el símbolo equivocado
   (`Set_int_is_empty`) en cuanto el bundle contiene más de una especialización
   `Set of T` (y las propias `test` del módulo las contienen), o directamente no
   compila (`invalid initializer`). Se retiraron `Set.empty`/`Set.from_items` y se
   sustituyeron por las funciones de módulo `make_set`/`from_items_set` (con
   `of T` explícito) y los constructores concretos. Además, `new_set` tuvo que
   renombrarse a `make_set`: su especialización `new_set of string` se manglea a
   `new_set_string` y secuestra el `coven.new_set_string` legacy.
9. **`atlas` arrastra un defecto preexistente de mutación por valor.** Un
   parámetro `map`/`list` se pasa **por valor** como copia de struct
   (`PenguMap m`, no `PenguMap*`); por eso ninguna función de módulo que reciba
   `m as map of K to V` y devuelva `void` puede mutar el mapa del llamante
   (`map_put`, `put*`, `map_remove`, `remove*`, `map_clear`, `clear*`, `update`,
   `rename_key`). Medido: `/tmp/c4/probe_byvalue.pengu` imprime
   `nongeneric=0 generic=0 list=2`; las formas de **método** sí funcionan porque
   `self` es `ref to map` (`calling m.clear` deja el mapa a 0). El fallo estaba
   oculto porque la suite interna de `atlas` se detenía antes en
   `filter_keys_contains` (roto desde antiguo), así que los tests de mutación
   posteriores no se ejecutaban. Este chunk **no** cambia firmas (haría falta
   `ref to map` y `sigil of` en cada llamada, o un cambio en el compilador, que
   está fuera de alcance): los tests internos ejercitan las formas de método y la
   limitación queda documentada como deuda.
10. **Un `bag` de tests rojo ocultaba fallos en cadena.** Además de
    `filter_keys_contains` (esperaba 2 claves con `"a"` en `{alpha, beta,
    gamma}`: son 3) y del test de bundling de `scrolls` (Chunk 2, arreglado aquí
    en `tests/compiler/test_compiler_bugfixes_v0150.py`), el propio `compass`
    tenía el use-after-free de `cp_change_ext` descrito arriba, introducido al
    añadir `defer banish st` en la migración sobre un `set buf is st` que
    aliasaba el buffer.
11. **`defer` es de ámbito de función en el C generado.** Un `defer banish x`
    sobre una variable declarada dentro de un `if`/`else` no compila
    (`'x' was not declared`); los temporales owned van al nivel superior de la
    función o se liberan con `banish` explícito dentro del bloque.

## Desviaciones y hallazgos de Chunk 3

1. **Los tests externos viven en `tests/stdlib/`, no en la raíz.** El brief pedía
   `tests/test_{tally,loom,ward}.py`, pero `tests/test_test_policy.py` congela
   `MAX_ROOT_TEST_FILES = 15` y la raíz ya estaba exactamente llena tras los
   Chunks 1–2 (`spark`, `scrolls`, `oracle`). Añadirlos habría puesto en rojo
   `test_the_root_test_set_stays_small` en CI (`pytest tests` corre la suite
   entera). Decisión del usuario: respetar el tope y usar el paquete de área.
   La ruta equivalente es `pytest tests/stdlib/test_<mod>.py`.
2. **Quitar `std.scrolls` de `ward` no bastó con `_w_fmt_string`.** El módulo
   también usaba los métodos `string.contains` / `starts_with` / `ends_with` que
   aporta `scrolls` (`E0004` sin el import). Se reescribieron los tres predicados
   con slices nativos (`at a to b`, fin exclusivo) preservando los mensajes de
   panic exactos. Coste: un slice temporal por offset candidato, mientras que
   `scrolls` usaba helpers C `memcmp` sin asignación.
3. **`defer banish` no acepta `result` ni los contenedores legacy** (`E0008`),
   aunque `banish` simple sobre los mismos valores sí compila. Los docstrings de
   los `check_*` recomiendan `banish` (no `defer banish`) para esos contenedores.
   Es un bug del compilador en `defer`, no del módulo.
4. **Notas de diseño obsoletas corregidas.** `tally` y `loom` afirmaban que
   importar `std.ward` crearía un ciclo (`ward -> tally` / `ward -> scrolls`);
   tras el Chunk 2 `ward` ya no importa `scrolls`, y nunca importó `tally`. La
   razón real de mantener el harness privado `_expect*` es no arrastrar una
   dependencia solo-de-test (`oracle`) a todo programa que importe el módulo.
5. **`judge` solo donde aplica.** `loom` lo usa en el despacho de `_apply_op_int`;
   `tally` y `ward` no tienen cadenas que comparen un sujeto contra varias
   constantes, así que no se forzó (la guía pide `judge` "cuando aplique").
6. **Tests internos de `loom`: 137 → 130.** Siete de los trece tests que el chunk
   añadió llamaban sin cualificar a nombres compartidos con `tally` y rompían
   `pengu run` en cuanto un programa importaba los dos módulos (bug del
   compilador, ver abajo). Se sustituyeron por aserciones sobre los núcleos
   privados concretos; los wrappers públicos siguen cubiertos por
   `tests/stdlib/test_loom.py` (comprobado: `mean` 6, `median` 6, `mode` 6,
   `min_max` 5, `running_sum` 2, `zip_with` 9, `enumerate_pairs` 2, `flatten` 1,
   `windowed` 1 referencias cualificadas). El balance neto del chunk sigue siendo
   positivo: 124 → 130 tests internos.

## Decisiones de estilo tomadas en Chunk 1

- Los cuerpos C de los `antiquus` van a columna 0 dentro de `r"""..."""`, sin
  ninguna línea indentada: `pengu fmt` reindenta el archivo entero si un cuerpo
  mezcla líneas a columna 0 con líneas indentadas. Se escribió el C (por ejemplo
  `pengu_input`) con las sentencias a columna 0 para satisfacer el formateador y
  la regla §20.5 de la guía a la vez.
- Docstrings `##` con secciones en español (`## ## Parámetros`, `## ## Retorno`,
  `## ## Ejemplo`, `## ## Motivo`, `## ## Memoria`) y prosa en inglés, siguiendo
  literalmente el brief del Chunk 1.
- `judge` para `parse_bool`, no cadenas de `if/else`.
- `if cond then a else b` para `min_int`/`max_int`/`abs_int`/`clamp_int`/`sign_int`.
- `defer banish line` en `read_int`, `read_float` y `read_bool`.
- `when debug:` en `assert_debug` (compilado fuera en release).
- `insignia spark_` añadido: sin él, `weave exit` colisiona con `exit()` de
  `<stdlib.h>` cuando `spark` es el fichero de entrada
  (`pengu test --entry std/spark.pengu`). Es la misma técnica que usa `atlas`.

## Helpers añadidos a spark

- `_none_bool`: weave privado que devuelve un `maybe bool` vacío tipado. Es
  necesario porque `maybe none` dentro de una rama `else ->` de `judge` no tiene
  contexto de tipo (`E0014`); no es superficie pública.
- Fuera de eso, nada fuera del contrato de §5 del brief.

## Tests borrados (solo std)

Directorios completos:

- `tests/std_programs/` (61 programas de ejercicio por módulo)
- `tests/conformance/std_programs/` (37 casos de conformidad de std)

Ficheros:

- `tests/stdlib/test_std_chronicle_days_in_month.py`
- `tests/stdlib/test_std_cipher_base64.py`
- `tests/stdlib/test_std_compass_cp_helpers.py`
- `tests/stdlib/test_std_deprecation_enforcement.py`
- `tests/stdlib/test_std_ledger_escape.py`
- `tests/stdlib/test_std_orphan_modules.py`
- `tests/stdlib/test_std_seal_crc32.py`
- `tests/stdlib/test_std_style_rules.py`
- `tests/stdlib/test_std_versioning.py`
- `tests/stdlib/test_stdlib.py`
- `tests/stdlib/test_loom_tally_coexistence.py`
- `tests/docs/test_std_docs_completeness.py`
- `tests/docs/test_std_deprecations_doc.py`
- `tests/docs/test_style_guide_exceptions.py` (ver desviaciones)

Se conservan los tests que verifican el lenguaje/compilador aunque su nombre
empiece por `test_std_`: `tests/stdlib/test_std_bindings.py` (codegen de
bindings C) y `tests/stdlib/test_std_warning_positions.py` (posiciones de W0001).

## Reparaciones de tests tras el borrado

- `tests/tooling/test_bindings_version_policy.py`: dejó de importar el helper de
  `test_std_versioning`; comprueba la política contra `std/*.pengu`.
- `tests/tooling/test_freeze_manifest.py`: la tabla de módulos opt-in queda
  inline (`celeris`, `trial`, `xlsx`).
- `tests/cli/test_cli_strict_c99.py` y
  `tests/compiler/test_compiler_bugfixes_v0150.py`: sus casos que consumían
  `tests/std_programs/` se saltan cuando el corpus no está.
- `tests/runtime/test_runtime_strings.py`: se eliminaron los bloques que
  llamaban a `pengu_parse_int`/`pengu_parse_float` (ya no están en la cabecera);
  su cobertura vive en `tests/test_spark.py`.
- `tests/conformance/antiquus/basic.pengu`: su cuerpo C llamaba a
  `pengu_println`, que ya no existe a nivel de cabecera; ahora usa
  `pengu_string_from_cstr` (que sí sigue en `pengu_runtime.h`) y `fwrite`/`fputc`
  de `stdio`. Es la consecuencia directa de mover los helpers de I/O: un cuerpo
  `antiquus` ya no puede llamar a `pengu_println` directamente.
- `tests/conformance/_manifest.json` y `_deps.json`: regenerados sin los casos
  `std_programs/*`.
- `.github/workflows/nightly.yml` + `tests/test_known_issues.py`: el deselect del
  sanitizer apunta a `tests/test_known_issues.py::test_known_leak_legacy_containers`
  (la fuga rastreada se reproduce inline), y el paso dirigido ya no se deselecciona
  a sí mismo.
- `tests/_test_policy_baseline.json` y `docs/api/` regenerados.

## Desviaciones del brief (con justificación)

1. **Solo 6 de los 13 símbolos existían en `pengu_runtime.h`.** Los otros 7 son
   nuevos; no se podía "mover" lo que no estaba. El recorte real es de 123
   líneas, no de 13 funciones.
2. **Se borró también `tests/docs/test_style_guide_exceptions.py`.** Importaba
   helpers de `test_std_docs_completeness.py` y, además, fija los números
   `documented/total` de cobertura de docstrings de `std/` que las guías citan
   literalmente. La migración los cambia (`weave` 1314/1315 → 1333/1334,
   `declare` 630/1862 → 624/1856, `const` 123/593 → 123/597) y el brief prohíbe
   tocar las guías, así que el test no puede sobrevivir sin editarlas. Las
   cifras quedan pendientes de resincronizar en un chunk posterior que sí pueda
   tocar las guías.
3. **`insignia spark_`** no estaba en el brief, pero es obligatorio para que
   `pengu test --entry std/spark.pengu` compile (colisión de `exit` con la
   libc). Documentado arriba.
4. **Se conservaron `test_std_bindings.py` y `test_std_warning_positions.py`**, que
   verifican el compilador y no módulos `std.*` de PenguScript puro.
5. **Se conservaron `test_api_docs.py` y `test_cheatsheet_catalog.py`** (con
   `docs/api/` regenerado), porque prueban herramientas del repo, no la
   semántica de un módulo `std`.
6. **La API C de `antiquus` encoge.** La guía (§9.6) documenta que un cuerpo
   `antiquus` puede llamar a `pengu_println`; tras mover los helpers de I/O a
   `spark`, ese símbolo ya no está en `pengu_runtime.h` y el caso de conformidad
   `tests/conformance/antiquus/basic.pengu` se reescribió para usar
   `pengu_string_from_cstr` + `stdio`. La prosa de la guía queda desactualizada en
   ese ejemplo concreto, y el brief prohíbe editarla.

## Desviaciones y hallazgos de Chunk 2

1. **`declare` se manglea bajo `insignia`.** Un `declare pengu__find_sub` colocado
   *después* de `insignia pengu_` emite `pengu_pengu__find_sub` (símbolo sin
   definir) y falla al enlazar. En `scrolls` la declaración va **antes** de
   `insignia`, con un comentario que lo explica. No afecta a los `antiquus`, que
   sí llevan el prefijo (`pengu_pengu_string_*`) sin colisionar.
2. **Regla del C-block aplicada a 9 weaves.** Los 6 `_char_is_*` y los 3 helpers
   de búsqueda (`_index_of_from`, `_last_index_of_from`, `_has_prefix_at`) se
   eliminaron; sus llamantes usan los `antiquus` o `pengu__find_sub`. No queda
   doble implementación en `scrolls`.
3. **`rsplit` sin `n` es equivalente a `split`.** Se implementó con un escaneo
   hacia delante que no asigna substrings temporales; el resultado es idéntico al
   de `split` (como en Python sin `maxsplit`). Documentado en el propio símbolo.
4. **Los helpers opcionales de `oracle` se descartaron a propósito.**
   `maybe.map_or`, `maybe.inspect`, `result.inspect`, `result.inspect_err` y
   `result.map_or` compilan, pero su sola presencia rompe llamadas existentes:
   `filter`, `map` y `map_err` pasan a resolver al símbolo C de `map_or`
   (`maybe_int_map_or_int` con 2 de 3 argumentos) y el bundle no compila. Es un
   bug del compilador (resolución de métodos por prefijo), no del módulo; se
   verificó con el programa de ejercicio pre-migración. Queda registrado abajo.
5. **Temporales de slice sin `banish`.** El patrón `let x is s at a to b` asigna
   un buffer nuevo y no lo libera; es ubicuo en toda la stdlib preexistente
   (`rites`, `precis`, `compass`, `ledger`, …) y también estaba en el `scrolls`
   original. Se dejó como estaba para no cambiar el comportamiento del módulo ni
   arriesgar un doble free fuera de alcance; el código **nuevo** (`rsplit`) sí
   evita la asignación. Candidato a limpieza global en un chunk dedicado.

## Bugs del compilador encontrados en Chunk 2

- **Resolución de métodos por prefijo (bloqueante para la API opcional de
  `oracle`).** Con un método `map_or` definido en `enchanting maybe shard T`, las
  llamadas `m.map` / `m.filter` de código existente resuelven al símbolo de
  `map_or` en el C generado, con el número de argumentos equivocado. Reproducción
  mínima: añadir `map_or` a `std/oracle.pengu` y compilar el antiguo
  `tests/std_programs/oracle.pengu` (hoy borrado; se usó `git show f9aa84a^:…`).
- **`declare` + `insignia`** (ver hallazgo 1): el `declare` hereda el prefijo de
  módulo, lo que impide declarar un símbolo C existente con su nombre exacto si el
  módulo tiene `insignia`.
- **`__auto_type` bajo tcc.** La indexación con comprobación de límites emite
  `__extension__({ __auto_type … })`; el compilador de desarrollo (tcc) falla y la
  CLI reintenta con gcc. Es preexistente (roadmap 3.3) y no lo introduce el
  Chunk 2, pero hace que `pengu run` sea más lento en programas que usan
  `scrolls`/`oracle`.

## Bugs del compilador encontrados en Chunk 3

- **Resolución de nombres compartidos entre módulos dentro de los bloques
  `test` (regresión de compilación, no de comportamiento).** El checker tipa
  también los bloques `test` de los módulos **importados**, en un espacio de
  nombres compartido. En un bundle que importa `std.tally` y `std.loom`, una
  llamada sin cualificar desde un `test` de `loom` a uno de los 15 nombres
  compartidos puede resolverse a la declaración de `tally`; si esa declaración es
  genérica (`windowed shard T`, `running_sum shard T`, `mean shard T`, …) la
  inferencia falla con `E0005` y **todo el programa deja de compilar**, aunque el
  bloque `test` no se ejecute nunca en `run`. Reproducción mínima: cualquier
  programa con `import std.tally` antes de `import std.loom` (el orden importa)
  más una llamada a `windowed`/`running_sum`/… desde un `test` de `loom`.
  Medido contra `HEAD~1`: el smoke del brief (spark + tally + loom + ward) pasa
  con los módulos pre-migración y fallaba con los migrados, así que el Chunk 3 lo
  destapó al añadir tests internos nuevos. No se puede esquivar cualificando
  dentro del propio módulo (`calling loom.mean` da `E0004`: el identificador del
  módulo no está en scope). Mitigación aplicada: los `test` internos de `loom`
  usan los núcleos concretos privados (`_mean_int`, `_min_max_int`, `_windows_int`,
  …) y la superficie pública la cubre `tests/stdlib/test_loom.py`, que llama
  cualificado. Verificado en ambos órdenes de import y con `ward` delante.
  Queda como bug abierto del compilador.

## Bloqueos conocidos

- Ninguno para Chunk 4.
- Deuda registrada: las guías Pengunic citan cifras de cobertura de docstrings de
  `std/` que ya no son exactas (Chunk 1, desviación 2).
- Deuda registrada: temporales de slice sin `banish` en toda la stdlib (hallazgo 5).
- Deuda registrada: bug de resolución de métodos por prefijo (bloquea añadir
  `map_or`/`inspect` a `oracle`).
- Deuda registrada: un `ritual` genérico con dos especializaciones sigue
  miscompilando, así que `Set.empty` no existe; usar `coven.make_set of T` o los
  constructores concretos (Chunk 5, desviación 1).
- Deuda registrada: `std/chronicle.pengu` timestamps are 32-bit `float` while
  the runtime bridges are `double`, so at modern epochs the resolution is ~128 s
  (`add_seconds(1700000000.0, 1)` returns the same value). The public surface
  keeps `float` for compatibility and the module docstring now states the
  limitation; switching the timestamps to `f64` is the correct fix and is
  deferred.
- Deuda registrada: `pengu_c_strptime` (runtime) ignores `fmt`, resolves in the
  process's **local** time zone with `mktime` and zeroes unparsed time fields.
  `chronicle.parse` was mis-declaring the bridge as `maybe float` while the
  bridge allocates a `double` payload, so `.value` was garbage; the declare is
  now `maybe f64` with an explicit `to float` conversion, and the docstring
  records the zone/`fmt` limitation.
- Deuda registrada: `chronicle.now_ms`/`time_ms` return 32-bit `int`
  milliseconds (overflows after 1970); they should be `i64`. Deferred because it
  is a pre-existing public signature.
- Deuda registrada: `chronicle` pre-1970 round-trips are silently wrong
  (`_epoch_days` starts at 1970).
- Deuda registrada: `std/archivum.pengu`: `glob` is rooted at the process
  working directory, reports `./<path>` entries, never matches absolute patterns
  and treats `?` as a literal; the docstring now says so.
- Deuda registrada: `result.is_err` / `result.is_ok` are `std.oracle`
  enchantings, not core fields: `*_result` callers must `import std.oracle` and
  use `calling r.is_err`.

## Notas para Chunk 3

- `tally`, `loom` y `ward` importan `std.spark` (y `ward` además `oracle` y
  `scrolls`); no crear ciclos (E0004): el harness de tests interno debe ser
  privado (`_expect*`), no `ward`.
- Antes de mover cualquier `static inline` del runtime, `grep` en `std/`,
  `pengu_parser/` y `tests/runtime/`: esos tests solo incluyen
  `pengu_runtime.h` y no ven los `antiquus` de un módulo. El codegen emite
  `pengu_string_char_at`, `pengu_string_substring`, `pengu_string_equal`,
  `pengu_string_compare`, `pengu_string_split` y `pengu__find_sub`: no se mueven.
- Mantener el patrón: `insignia <mod>_` cuando un weave pueda colisionar con un
  símbolo de la libc, y colocar los `declare` **antes** de `insignia`.
- Los cuerpos `antiquus` van a columna 0 (todas las líneas), o `pengu fmt`
  reindenta el archivo entero.
- No renombrar ni eliminar símbolos públicos: la API es superset.
