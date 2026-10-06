# AUDIT FASE 6 — Completar stdlib

> Ejecución de la Fase 6 del `ROADMAP_2.0.md` (17 items) sobre la base del commit
> `86a80a2` ("Fase 5"). Un commit por item. Toda afirmación de este documento
> tiene un comando o un test que la respalda; nada se aprueba inspeccionando
> texto.

---

## Resumen

| Métrica | Antes | Después |
|---|---|---|
| Items cerrados | — | **13/17** |
| Items diferidos a 1.1 (con medición) | — | **2/17** (6.5, 6.11) |
| Items refutados (premisa falsa / ya resuelto) | — | **2/17** (6.14, 6.8 N/A) |
| Items ya resueltos por fases anteriores | — | **3/17** (6.2, 6.4, parte de 6.16) |
| `pengu check` sobre los 52 módulos | 0 errores / 0 warnings | **0 errores / 0 warnings** |
| W0001 con posición | `file:0:0` (0%) | `file:<línea>:<col>` (**100%** de los que se emiten) |
| W0005 residuales | 0 (ya suprimidos en 2.12) | **0** |
| Doc inline `scrolls` | 23/89 = 25.8% | **89/89 = 100%** |
| Doc inline `atlas` | 36/151 = 23.8% | **151/151 = 100%** |
| Doc inline `arithmancy` | 71/71 = 100% | **100%** (ya estaba) |
| Benchmarks que importan `std` | 1 | **6** (6 módulos distintos) |
| Nombres obsoletos en `CHEATSHEET.md` | 4 + recuento 25 | **0**, recuento 27 |
| Tests nuevos | — | **11 ficheros**, 2822 tests en total |
| LOC tocadas | — | 40 ficheros, +2338 / −59 |

**Nota sobre la aritmética:** los 2 refutados (6.14, 6.8) y los 3 ya resueltos
(6.2, 6.4 y la parte de 6.16 de la 4.15) cierran sin cambio de código o con solo
tests/documentación. `6.11` se difiere aunque se midió; `6.5` se difiere también
con medición. El criterio de "done" de la fase se evalúa al final (§Cierre).

---

## Pre-flight: verificación de premisas

Ejecutado **antes** de tocar código. El roadmap contenía varias premisas falsas.

| # | Premisa del roadmap | Estado real medido | Acción |
|---|---|---|---|
| 6.1 | `seal.crc32` debe devolver `u32`; `crc32("a") == 390611389` | Confirmado el bug: devolvía `int` y `crc32("a") == -390611389`. **El valor esperado del roadmap también era erróneo**: el CRC-32 IEEE de `"a"` es `0xE8B7BE43` = `3904355907` | Cerrado |
| 6.2 | `std/ffi.pengu:133,137,141` usan `transmute 0 to ref to T` | **Refutado**: 0 ocurrencias de `transmute 0` en `std/ffi.pengu`; ya se sustituyó por `null` en `6e30471` | Ya resuelto |
| 6.3 | Los 21 `W0001` salen como `std/filum.pengu:0:0` | Confirmado el síntoma en la ruta de diagnóstico: `W0001` se emitía sin posición. Pero la Fase 2 ya había eliminado los `transmute` de la stdlib, así que **hoy hay 0 `W0001`**: el bug se reprodujo con un fichero de prueba | Cerrado |
| 6.4 | 29 locales que sombrean; `loom` (21), `tally` (3), `precis` (4), … | **Refutado**: 0 `W0005` en los 52 módulos. La Fase 2 (2.12) los suprimió en bloques `test`, que era la vía que el propio roadmap aceptaba | Ya resuelto |
| 6.5 | 15 nombres duplicados entre `loom` y `tally` | Confirmado el solapamiento, pero **0 de los 15 comparten firma**: son dos contratos distintos (`loom.mean` → `float`, `tally.mean` → `int`) | Diferido a 1.1 |
| 6.6 | `SPARK_VERSION`/`STD_VERSION` incoherentes y "test vacuo" | Parcialmente refutado: `test_spark_extended.pengu` **ya asserta** las tres. El test vacuo era solo `test_spark.pengu`, que imprimía un literal obsoleto `"0.6.0-spark"` mientras la constante valía `0.7.0-spark` | Cerrado |
| 6.7 | `atlas` 32%, `arithmancy` 39%, `scrolls` 52% | Premisa correcta. Medido con la lógica del propio ratchet: `atlas` 23.8%, `arithmancy` **100%**, `scrolls` 25.8% | Cerrado |
| 6.8 | 19 bindings sin `<MOD>_VERSION`; objetivo 25/25 | **Refutado**: el test de versionado excluye `*.d.pengu` a propósito; las constantes de un binding son la versión de **upstream** (`RAYLIB_VERSION = "6.0"`, `SQLITE_VERSION = "3.53.4"`) y `RAYLIB_VERSION`/`RAYGUI_VERSION` colisionarían | N/A |
| 6.9 | `decode_base64` acepta `"QQ==QQ=="` | Confirmado | Cerrado |
| 6.10 | `escape_field` compara `s[i] == delim[0]` | Confirmado (`var dcode as int is ord delim`) | Cerrado |
| 6.11 | 32 helpers `cp_*` expuestos | Confirmado (32), pero **0 usuarios externos** y los 32 documentados | Diferido a 1.1 |
| 6.12 | `days_in_month` debe validar `m ∈ [1,12]`; "no leer `feb_days[12]`" | Confirmado el bug (`m=0` y `m=13` → 31). **Refutada la causa**: no hay tabla ni indexación, nunca hubo OOB | Cerrado |
| 6.13 | `compress`, `product`, `max`, `min` inexistentes; "25 modules" | Confirmado: los reales son `zlib_compress`, `product_num`, `max_int`, `min_int`; hay 27 módulos y faltaban `celeris`/`xlsx` del catálogo | Cerrado |
| 6.14 | `celeris`, `xlsx`, `trial` huérfanos | **Refutado**: los tres tienen importador que compila y ejecuta | Refutado |
| 6.15 | Alias `average`, `argmin`, `argmax`, `filter_range` con versión de retirada | Confirmado; y se descubrió algo mayor: **el toolchain sí soporta `@deprecated("…")` real, pero la stdlib no lo usa en ningún sitio** (90 marcadores de docstring, 0 atributos) | Cerrado |
| 6.16 | `4.15` ya añadió `stdlib_ops`; faltan "los que falten" | Confirmado: había **1** caso que importa `std` | Cerrado |
| 6.17 | Documentar `loom` vs `tally` | Confirmado: ambos módulos tenían notas de diseño pero ninguno decía cuál elegir | Cerrado |

### Hallazgos colaterales (no estaban en el roadmap)

1. **`W0006` también pierde la posición** (`file:0:0`), no solo `W0001`. El item
   6.3 arregló únicamente `W0001`; `W0006` sigue saliendo sin línea. Queda
   documentado como prerequisito de la aplicación real de `@deprecated` en la
   stdlib (ver §Hallazgos).
2. **La convención `@deprecated` estaba mal documentada** en tres cabeceras
   (`scrolls`, `oracle`, `loom`), que afirmaban que el toolchain no soporta
   deprecación. Es falso en los dos sentidos: el atributo existe y funciona, y
   la stdlib no lo usa (§Hallazgos).
3. **`parse_line`/`parse_line_strict` de `std/ledger` tienen el mismo bug de
   primer byte** que `escape_field` tenía (2 sitios con `ord delim`), fuera del
   alcance del item 6.10.
4. **9 de los 25 bindings `.d.pengu` no tienen importador ni test** en el repo
   (`datastructura`, `fenestra`, `pactum`, `perlinum`, `scriptor`, `typis`,
   `webui`, `stb_herringbone_wang_tile`, `stb_image_resize2`). Son adaptadores
   opt-in alcanzables por `import std.<lib>` y catalogados en `LANGUAGE.md` /
   `CHEATSHEET.md`.
5. **`SPARK_VERSION`/`STD_VERSION` no son incoherentes con `VERSION`: no deben
   serlo.** Forzar `SPARK_VERSION == VERSION` haría que la revisión de la API de
   spark cambiara con cada release del compilador, que es exactamente lo que la
   allowlist de la 4.9 evita.
6. **`loom.flatten` estaba marcado `@deprecated` en su docstring** y la cabecera
   de `loom` lo justificaba diciendo que `@deprecated` "no existe".

---

## Items cerrados

Cada fila: qué se cambió, el comando que lo demuestra y el commit.

### 6.1 — `seal.crc32` devuelve `u32` sin signo

- **Bug:** `int pengu_c_seal_crc32(...)` con `return (int)crc32(...)`. Todo
  checksum ≥ `0x80000000` salía negativo.
- **Evidencia antes:** `pengu run` de un programa `crc32("a")` → `-390611389`.
- **Evidencia después:** `u32 var = 3904355907`, `int var = -390611389`
  (la re-narrowing explícita a `int` sigue truncando, correcto).
- **Matiz importante:** la ABI C es **idéntica** (registro de 32 bits);
  lo que decide es el tipo declarado. Por eso el test que distingue ambos
  estados es un gate sobre el C generado
  (`static inline int32_t seal_crc32(` → `static inline uint32_t seal_crc32(`),
  no solo un assert de valor.
- **Corrección al roadmap:** el roadmap pedía `== 390611389`; el valor real es
  `3904355907` (`zlib.crc32(b"a") = 0xE8B7BE43`). El test calcula el esperado con
  `zlib.crc32` en tiempo de import.
- **API:** `crc32` → `u32`; `crc32_file` → `maybe u32` (deja atrás
  `MaybeInt`, deprecado); `to_crc32` → `u32`.
- **Test:** `tests/test_std_seal_crc32.py` (6). El gate de firma falla con el
  código pre-fix.
- **Commit:** `e480024`

### 6.9 — `decode_base64` rechaza `=` fuera de la posición final

- **Bug:** el bucle de cuantos trataba `=` como carácter de datos, así que
  `"QQ==QQ=="` se aceptaba.
- **Fix:** pasada de validación RFC 4648 tras el stripping y antes del bucle:
  `=` solo cierra la cadena, máximo 2, el tramo de padding empieza dentro del
  último cuánto y termina exactamente al final.
- **Evidencia:** rechaza `"QQ==QQ=="`, `"QQ==QQ"`, `"QQ=QQ=="`, `"Q==="`,
  `"QUJD===="`, `"="`, `"===="`; acepta `"QQ=="`, `"QUI="`, `"QUJD"`,
  `"aGVsbG8="`, el whitespace y `decode_base64_url`.
- **Test:** `tests/test_std_cipher_base64.py` (4).
  `test_double_padded_quantum_is_rejected` falla pre-fix con PANIC.
- **Commit:** `4402c88`

### 6.10 — `escape_field` compara el delimitador completo

- **Bug:** `var dcode as int is ord delim` comparaba cada carácter contra el
  **primer code point** del delimitador. `ord` exige un literal de un carácter en
  compilación pero acepta una variable de cualquier longitud en runtime.
- **Fix:** `calling field.contains with delim` (secuencia completa). Misma
  corrección en `escape_field_backslash`; `escape_field_rfc4180` delega.
- **Evidencia:** `escape_field("a:b", "::")` → `a:b` (antes se entrecomillaba);
  `escape_field("a::b", "::")` → `"a::b"`.
- **Test:** `tests/test_std_ledger_escape.py` (5).
- **Commit:** `cd98556`

### 6.12 — `days_in_month` valida el mes

- **Bug:** cadena de `if` con fallback `31`, así que `m=0`, `m=13`, negativos y
  `INT_MIN` devolvían 31.
- **Fix:** `if m < 1: return 0` / `if m > 12: return 0` + contrato documentado.
- **Corrección al roadmap:** la premisa "no leer `feb_days[12]` fuera de límites"
  es falsa; no hay tabla. El bug era de validación, no de memoria. El
  comportamiento observable pedido (`m=0`, `m=13` → 0) es el que se implementa.
- **Test:** `tests/test_std_chronicle_days_in_month.py` (3), matriz completa de
  12 meses × 4 años (bisiestos incluidos) + 5 casos fuera de rango.
- **Commit:** `65b4058`

### 6.3 — Los diagnósticos `W0001` llevan la posición AST

- **Bug:** `pengu check --entry <src>` reportaba `file:0:0` para todo `W0001`,
  porque el canal `warnings` es una lista de strings y el mensaje se construía
  sin posición; `_warning_diag` solo extraía línea del sufijo `on line N`.
- **Fix:** helper `TypeInferrer._warn(code, message, node=None, dedup=False)` que
  añade `on line L col C` cuando `_get_loc(node)` conoce la posición; `_warning_diag`
  parsea también `col` y lo propaga al diagnóstico estructurado.
- **Evidencia antes:** `Warning t_warn.pengu:0:0 [W0001] transmute from 'int' …`
- **Evidencia después:** `t_warn.pengu:5:12` y `t_warn.pengu:9:12` (la columna 12
  es exactamente donde empieza `transmute`).
- **Nota:** la Fase 2 ya eliminó los `transmute` de la stdlib, así que hoy hay 0
  `W0001`; el bug se reproduce con un fichero ad-hoc. El item estaba abierto: la
  ruta de diagnóstico seguía sin posición.
- **Alcance deliberado:** `W0002` **no** recibe posición, porque sus nodos
  `arrow_access` no traen metadata y el fallback reportaba la línea 1 (peor que
  no reportar nada). Se deja en `0:0` con comentario explicativo.
- **Test:** `tests/test_std_warning_positions.py` (3), incluido el canal `--json`.
- **Commit:** `5defafd`

### 6.6 — `spark_version()` asserta contra `SPARK_VERSION`

- **Bug real:** `spark.pengu` documentaba `"0.6.0-spark"` en el docstring, y
  `test_spark.pengu` **imprimía** ese literal obsoleto sin assertar nada.
  `test_stdlib.py` fijaba `"0.6.0-spark"` como marcador esperado, así que el
  suite pasaba en verde mientras la constante real era `0.7.0-spark`: una
  aserción placebo sostenida por estar desactualizada.
- **Fix:** docstrings corregidos y explicados (revisión de API vs toolchain);
  `test_spark.pengu` ahora asserta `spark_version() == SPARK_VERSION`, la
  constante no vacía, y el valor esperado; marcadores de `test_stdlib.py`
  actualizados.
- **Corrección al roadmap:** "ambas constantes coherentes con `VERSION`" se
  refuta. `SPARK_VERSION` es la revisión de la API de spark y la allowlist de la
  4.9 lo documenta; `STD_VERSION` es un tag legado que no sigue la convención
  `<MOD>_VERSION`. Renombrarlo/eliminarlo es superficie pública → 1.1.
- **Evidencia por mutación:** cambiar `SPARK_VERSION` a `"0.9.9-spark"` hace
  fallar `test_stdlib.py::test_std_module_program[test_spark.pengu]`. Con el test
  previo, cambiar la constante **no** lo rompía.
- **Commit:** `f1a06a3`

### 6.7 — Doc inline de `atlas`, `arithmancy`, `scrolls` ≥ 90%

Cerrado en tres tandas, midiendo con la misma lógica que
`tests/test_std_docs_completeness.py` (regex de declaración + comentario propio
en la línea inmediatamente anterior).

| Módulo | Antes | Después |
|---|---|---|
| `scrolls` | 23/89 = 25.8% | **89/89 = 100%** |
| `atlas` | 36/151 = 23.8% | **151/151 = 100%** |
| `arithmancy` | 71/71 = 100% | 100% (sin cambios) |

- **`scrolls` (commit `17ea760`):** los 66 `weave` de módulo son delegaciones
  mecánicas al método homónimo de `enchanting string`, y los 69 métodos ya
  estaban documentados. Se transfiere el docstring del método al wrapper,
  reindentado y con la única referencia a `self` adaptada a `s` (`partition`).
  Los 66 resolvieron sin ambigüedad.
- **`atlas` (commit `11e8d69`):** en tres pasadas — 50 envoltorios que delegan
  en un método documentado; 36 variantes monomorfizadas (`*_ss`, `*_sf`, …) con
  los tipos concretos sustituidos; y 30 escritas a mano desde firma y cuerpo
  (`keys_sorted*`, `values_sorted*`, `count_true_sb`, `count_false_sb`,
  `filter_keys_*`, `map_remove`, `map_clear`, `_one`, `_count`). Correcciones de
  coherencia posteriores: 18 docs de `merge_*`/`from_lists_*` que no citaban el
  tipo concreto, y 20 envoltorios que habían heredado la referencia al receptor
  (`self`) cuando su parámetro real es `m`.
- **Correcciones al roadmap:** la estimación de `arithmancy` (39%) era falsa
  —estaba al 100%— y las de `atlas` (32%) y `scrolls` (52%) eran imprecisas
  (23.8% y 25.8%).
- **Verificación:** los tres módulos `pengu check` limpios;
  `tests/test_std_docs_completeness.py` 4 passed; los 17 tests que mencionan
  `atlas` en verde.

### 6.13 — `CHEATSHEET.md`: nombres reales y recuento

- **Bugs confirmados:** `product` → `product_num`, `max`/`min` → `max_int`/`min_int`
  (los reales, `std/loom.pengu:163,167,178`); zlib `compress`/`decompress` →
  `zlib_compress`/`zlib_decompress` (`std/seal.pengu:340,346`); "25 modules" → 27.
- **Además:** `celeris` y `xlsx` **faltaban por completo** del catálogo. Se
  añaden con sus funciones reales y su carácter opt-in (librería estática + flags
  de link). La fila de `seal` gana las funciones que existían y no aparecían
  (`*_file`, HMAC, verificación en tiempo constante).
- **Test:** `tests/test_cheatsheet_catalog.py` (31): el recuento de filas y el
  número del encabezado deben coincidir con los 27 módulos reales; cada módulo
  debe tener fila; todo identificador `snake_case` entre backticks debe existir
  como `weave` en la stdlib.
- **Evidencia por mutación:** `product_num` → `product` o el encabezado a 25
  fallan; insertar `totally_bogus_fn` en cualquier fila falla el detector general.
- **Commit:** `c4413df`

### 6.15 — `docs/DEPRECATIONS.md`

- **Inventario medido:** 90 marcadores `@deprecated` en 4 módulos, 64 símbolos
  únicos — `tally` (6), `scrolls` (11 métodos), `loom` (1), `oracle` (46).
- **Estado:** todo **1.x** (retirada en 2.0, política D6) salvo `oracle`, marcado
  **blocked** con medición: 29 sitios de llamada a la familia legada siguen
  vivos en `std/`; `result_ok_string`/`result_err_string` los usan `std/seal` y
  `std/ward`.
- **Test:** `tests/test_std_deprecations_doc.py` (10). Cruza el documento con los
  marcadores reales **en ambas direcciones**, exige reemplazo y estado válidos, y
  comprueba que todo `módulo.símbolo` citado como reemplazo exista.
- **Evidencia por mutación:** borrar la fila de `tally.average` falla
  `test_every_deprecated_symbol_is_documented`; añadir `tally.ghost_alias` falla
  `test_documented_symbols_still_exist`.
- **Commit:** `0a7cdfb`

### 6.16 — 6 benchmarks que importan `std`, uno por tier

- **Antes:** 1 (`stdlib_ops`, de la 4.15).
- **Añadidos:** `scrolls_ops` (string search/slice/split/join), `atlas_ops`
  (map build/probe/sorted keys), `cipher_ops` (Base64 ida y vuelta + md5),
  `loom_ops` (sum/max_int/min_int/is_sorted_asc/running_sum), `arithmancy_ops`
  (sqrt/sin + is_prime/gcd/lcm). **Total 6 casos, 6 módulos distintos.**
- **Evidencia:** los 6 corren con `pengu run` y con `pengu benchmark`
  (`--only atlas_ops`: build 5.49 s, run 16 ms, 675.5 KiB).
- **Test:** `tests/test_benchmarks.py` (17) gana tres gates que impiden cumplir
  el criterio "de mentira": ≥6 casos, ≥6 módulos distintos, y todos registrados
  en el harness y presentes en disco.
- **Parcialmente refutado:** la 4.15 ya había sentado la base; lo que faltaba
  eran 5 casos.
- **Commit:** `65ca7e5`

### 6.17 — Doc de `loom` vs `tally`

- **Añadido:** `LANGUAGE.md` §19.1.1 "Choosing between `std.loom` and
  `std.tally`" con tabla comparativa (forma, entrada vacía, resultados
  fraccionarios, genéricos, cuándo usar cada uno), ejemplo de la divergencia
  (`loom.mean([1,2]) == 1.5` vs `tally.mean([1,2]) == 1`) y la regla: `tally` si
  la operación es una reducción con identidad natural; `loom` si una lista vacía
  no tiene respuesta. Enlazado desde las cabeceras de ambos módulos (que ganan su
  sección "Cuándo usar") y desde la fila `loom` del `CHEATSHEET`.
- **Corrección colateral:** tres cabeceras afirmaban que "el toolchain no soporta
  deprecación". Es falso (ver §Hallazgos). Corregidas `scrolls`, `oracle` y la
  nota de `loom`, que ahora remiten a `docs/DEPRECATIONS.md`.
- **Commit:** `1c004fa`

---

## Items diferidos a 1.1 (con medición)

### 6.5 — `loom` ∩ `tally`: medido y diferido (no son duplicados)

- **Medición:** 15 nombres públicos compartidos (`mean`, `median`, `mode`,
  `min_max`, `sum`, `flatten`, `take`, `windowed`, `zip_with`, `running_sum`,
  `scan_left`, `repeat`, `enumerate_pairs`, `is_sorted_asc`, `is_sorted_desc`).
  **0 de los 15 comparten firma.** Cuatro son conflictos semánticos:
  `mean` (`float` vs `int`), `median` (`maybe float` vs `int`), `mode`
  (`maybe int` vs `int`), `min_max` (`maybe Pair` vs `list of int`); más
  `enumerate_pairs` (`Pair` vs `list of int`), `windowed`/`running_sum`/`zip_with`
  (genéricos en `tally`, monomórficos en `loom`), `flatten` (aridades distintas)
  y `take` (`n` obligatorio vs default 1). El resto difiere solo en el nombre de
  los parámetros.
- **Evidencia ejecutada:** `loom.mean([1,2]) == 1.5` y `tally.mean([1,2]) == 1`;
  `loom.mode([])` → `none` y `tally.mode([])` → `0`.
- **Coste:** unificar es un cambio rompedor para la familia que pierda. `loom`
  tiene 11 ficheros de test/bench que lo usan y `tally` 15.
- **Por qué se difiere:** el roadmap lo pedía "resolver"; la medición muestra que
  no hay duplicación que resolver, sino dos filosofías de API deliberadas.
  Hacerlo bien exige alias `@deprecated` + ventana de dos releases, y la stdlib
  **no aplica atributos `@deprecated` reales** (ver §Hallazgos).
- **Reapertura:** cuando exista política de deprecación con ventana de dos
  releases; migrar `tally.mean`/`median`/`mode`/`min_max` a alias de `loom` y
  subir el major.
- **Test que fija la convivencia:** `tests/test_loom_tally_coexistence.py` (5).
- **Commit:** `e10223c`

### 6.11 — `compass.cp_*`: medido y diferido

- **Medición:** 32 helpers, **0 usuarios externos** en `std/`, `tests/`,
  `benches/`, `docs/` y guías de la raíz; los 32 llevan doc propia; ~169 sitios
  de referencia internos dentro de `compass.pengu`. `CHANGELOG.md` documenta que
  el split `cp_*` existe a propósito ("prevent method/weave symbol collision in
  codegen").
- **Coste:** renombrar 32 declaraciones y sus ~169 usos internos es mecánico,
  pero rompe a cualquier código 0.16 que llame a `cp_*` (no llevan marcador de
  deprecación, así que no hay aviso previo).
- **Por qué se difiere:** es un cambio rompedor de superficie pública sin
  beneficio de correctitud, y pertenece a la limpieza de API de 1.1 junto a 6.5.
- **Reapertura:** la limpieza de superficie pública de 1.1; `cp_*` → `_cp_*` (o
  promoción a espacio de nombres de bajo nivel documentado) con shims y entrada
  en el CHANGELOG.
- **Test que fija la medición:** `tests/test_std_compass_cp_helpers.py` (4). Si
  alguien empieza a importar `cp_*` desde fuera, el test de "sin usuarios" falla
  y obliga a revisar la decisión.
- **Commit:** `3c6dbed`

---

## Refutaciones (items ya resueltos o con premisa falsa)

### 6.2 — `transmute 0 to ref to T` en `std/ffi.pengu`

- **Refutado:** 0 ocurrencias de `transmute 0` en `std/ffi.pengu`. Las líneas que
  el roadmap citaba (133, 137, 141) son hoy `return null` en `null_void`,
  `null_char`, `null_byte`.
- **Ya resuelto en:** `6e30471` ("replace the transmute-based NULL idiom with
  `null` in ffi"), antes de esta fase.
- **Evidencia:** `grep -c "transmute 0" std/ffi.pengu` → 0; `pengu check --entry
  std/ffi.pengu` limpio; 0 `W0001` en los 52 módulos.
- **Sin cambios.** No se añadió test nuevo: el gate existente es
  `tests/test_audit_regressions.py:380` (`assert "transmute from 'int'" not in out`).

### 6.4 — 29 locales que sombrean funciones globales (`W0005`)

- **Refutado por medición:** `W0005` = **0** en los 52 módulos.
- **Ya resuelto en:** Fase 2, item 2.12. `pengu_checker.py:402` y `:4373`
  suprimen `W0005` dentro de bloques `test` (`self._test_block_depth`), y todos
  los sombreados de `loom`/`tally`/`precis` estaban en bloques `test`. El roadmap
  aceptaba explícitamente esa vía ("o solo los de bloques `test`, si 2.12 los
  silencia").
- **Evidencia:** recuento por módulo de todos los códigos `W00xx` → vacío; los 52
  reportan "Clean no errors found".
- **Sin cambios.**

### 6.14 — `celeris`, `xlsx`, `trial` huérfanos

- **Refutado:** los tres tienen importador que compila y **ejecuta**:
  - `std.celeris` → `test_ffi_libs.py::test_all_stb_modules_import_and_compile_in_one_bundle`
    compila y asserta `celeris.hash64(...) == 0x610DF71A00097754` (**PASSED**).
  - `std.xlsx` → `TestXlsxio::test_pengu_wrapper_writes_xlsx` escribe un `.xlsx`
    real y lo relee (**SKIPPED** en este entorno: falta el `libzip`/`xlsxio`
    extern, que es justo la dependencia opcional que el módulo documenta).
  - `std.trial` → `tests/std_programs/test_trial.pengu`, ejecutado por
    `test_stdlib.py::test_std_module_program[test_trial.pengu]` (**PASSED**).
- **Decisión:** no se mueve nada a `std/contrib/`. Además, mover sería un cambio
  rompedor de rutas de import sin beneficio funcional.
- **Test que fija la refutación:** `tests/test_std_orphan_modules.py` (11). El
  guard usa regex anclada (`^\s*import\s+std\.X\s*$`) y no substring: una versión
  previa con `in` pasaba con `import std.celeris_XX` y con el propio docstring del
  módulo. Verificado por mutación.
- **Commit:** `7982e23`

### 6.8 — `<MOD>_VERSION` en los bindings `.d.pengu` — **N/A por diseño**

- **Refutado por tres vías independientes:**
  1. `tests/test_std_versioning.py::_hand_written_modules()` **excluye**
     `*.d.pengu`, porque la constante de un binding es la versión de **upstream**:
     `RAYLIB_VERSION = "6.0"`, `SDL`-style, `SQLITE_VERSION = "3.53.4"` (con
     `SQLITE_VERSION_NUMBER = 3053004`). Añadir una que siga al toolchain obligaría
     a **sobrescribir** el valor de upstream.
  2. `RAYLIB_VERSION` y `RAYGUI_VERSION` ya existen: colisión de nombre.
  3. La política de la 4.9 exige `<MOD>_VERSION == VERSION`; un binding no puede
     cumplir eso y a la vez reflejar fielmente su cabecera.
- **Acción:** ninguna. El objetivo "25/25" contradice la política que fijó la 4.9.
- **Test:** `tests/test_bindings_version_policy.py` (4).
- **Commit:** `929c0dd`

---

## Hallazgos

Los cinco primeros se corrigieron o documentaron dentro de la fase; el sexto y el
séptimo se dejan con criterio de reapertura.

### H1 — El toolchain **sí** soporta `@deprecated("…")`; la stdlib **no lo usa**

El atributo real existe: `attribute: "@" NAME ["(" attribute_args ")"]` en la
gramática, registrado en el símbolo, emitido como `W0006` en el punto de uso
(arreglado en la Fase 2 item 2.11; hecho visible y denegable en la 5.4 con
`--deny-deprecated`). Verificado con un programa de prueba:
`@deprecated("Use new_f instead")` → `Warning …:0:0 [W0006] Symbol 'old_f' is
deprecated: Use new_f instead`.

**Pero la stdlib no usa ese atributo en ningún sitio:** medidos **90 marcadores de
docstring** (`## @deprecated Use X instead.`) y **0 atributos reales**. El checker
lee el atributo parseado, no el docstring, así que **ninguno de esos alias emite
hoy `W0006`**: su deprecación es documental.

Tres cabeceras afirmaban lo contrario en el otro sentido ("el toolchain no tiene
soporte de deprecación"): `scrolls`, `oracle` y una nota de `loom`. Corregidas.

Se intentó aplicar el atributo real a los alias de `scrolls` y `tally` y **se
revirtió**: rompía el criterio de "0 warnings propios" de la fase y excedía el
alcance declarado de 6.15 ("solo doc"). Los tres bloqueos medidos para hacerlo en
1.1 están documentados en `docs/DEPRECATIONS.md`, y fijados por
`tests/test_std_deprecation_enforcement.py` (4):

1. migrar los usos internos (`find` ×10 en `invoke`/`precis`, `rfind` ×1 en
   `precis`, `maybe_some_string` ×7 en `precis`, `result_ok_*`/`result_err_*` ×11
   cada uno en `seal`/`ward`);
2. sacar la cobertura de los alias de los bloques `test` (si no, el propio módulo
   avisa);
3. hacer que `W0006` lleve posición.

### H2 — `W0006` también pierde la posición

`W0006` sale como `file:0:0`. El item 6.3 arregló la posición solo para `W0001`.
El canal `warnings` del checker es una lista de strings y el emisor de `W0006`
(`_check_deprecated_symbol`) no la propaga. **Criterio de reapertura:** el mismo
cambio de forma que 6.3 (sufijo `on line L col C`) aplicado en
`_check_deprecated_symbol`; prerequisito de H1.

### H3 — `parse_line` / `parse_line_strict` repiten el bug de primer byte

`std/ledger.pengu` conserva 2 sitios con `var dcode as int is ord delim` en
`parse_line` (línea ~127) y `parse_line_strict` (~174): un delimitador
multi-carácter se trata como su primer byte, igual que `escape_field` antes de
6.10. **Fuera del alcance del item 6.10**, que nombraba solo `escape_field`.
**Criterio de reapertura:** un item propio en 1.1, con el mismo tratamiento
(`contains`/`starts_with` + avance por `delim` length) y tests de ida y vuelta
`escape_field` ↔ `parse_line`.

### H4 — 9 de los 25 bindings `.d.pengu` no tienen importador ni test

`datastructura`, `fenestra`, `pactum`, `perlinum`, `scriptor`, `typis`, `webui`,
`stb_herringbone_wang_tile`, `stb_image_resize2`. Son adaptadores opt-in
alcanzables por `import std.<lib>` y catalogados en `LANGUAGE.md`/`CHEATSHEET.md`.
Se extiende la guarda de huérfanos a los bindings, exigiendo que cada uno sea
alcanzable **por import o por documentación** (`tests/test_std_orphan_modules.py`).
**Sin cambios en 1.0.**

### H5 — `SPARK_VERSION`/`STD_VERSION` no deben seguir a `VERSION`

Forzar `SPARK_VERSION == VERSION` haría que la revisión de la API de spark
cambiara con cada release del compilador: exactamente lo que evita la allowlist
de la 4.9. `STD_VERSION` (`"0.14.1"`) es un tag legado que no sigue la convención
`<MOD>_VERSION`; renombrarlo/eliminarlo es superficie pública.
**Reapertura:** decidir en 1.1 si `STD_VERSION` se retira (con alias) o se
redefine como `<MOD>_VERSION` de `spark`.

### H6 — `pengu` no estaba en el PATH del entorno de trabajo

No es un hallazgo del roadmap, sino del entorno: `lark`, `pyyaml`, etc. no estaban
instalados y `pengu` no existía como comando. Se creó un venv local
(`.venv/`, ya en `.gitignore`) y un wrapper; además faltaba
`libmicrohttpd` en el sistema, que `build_runtime.py` espera en POSIX. Se
compiló el `libmicrohttpd-1.0.1` que ya viene en `extern/` hacia
`build/lib/libmicrohttpd.a` para poder compilar y ejecutar los tests.
Ninguno de estos cambios entra en el repositorio (están bajo `build/`).

---

## Cierre: criterio de "done" de la fase

| Criterio del roadmap | Estado |
|---|---|
| Los 52 módulos: 0 errores y 0 warnings propios | ✅ verificado: 52/52 "Clean no errors found", 0 códigos `W00xx` |
| `crc32` coincide con el estándar para valores ≥ `0x80000000` | ✅ `crc32("a") == zlib.crc32(b"a") == 3904355907`; el test calcula el esperado con `zlib` |
| 0 `transmute` con size mismatch en la stdlib | ✅ 0 `W0001`; ya venía de la Fase 2 |
| 0 `W0005` en la stdlib | ✅ 0 (suprimidos en bloques `test` por 2.12) |
| `loom`/`tally` sin nombres públicos en conflicto | ⏸️ **diferido a 1.1** con medición (6.5): los 15 nombres compartidos tienen contratos distintos y unificar rompe a una de las dos familias |
| 25/25 bindings con `<MOD>_VERSION`; todas coinciden con `VERSION` | ❌ **refutado como criterio** (6.8): contradice la política de 4.9; los bindings llevan versiones de upstream |
| ≥90% de doc inline en `atlas`, `arithmancy`, `scrolls`; 100% en el resto | ✅ los tres al **100%** (`arithmancy` ya lo estaba) |
| `CHEATSHEET.md` sin nombres inexistentes (test que cruza nombres) | ✅ `tests/test_cheatsheet_catalog.py` (31) cruza los nombres con los `weave` reales |
| ≥6 benchmarks que importan `std` y corren en CI | ✅ 6 casos, 6 módulos distintos, corren con `pengu benchmark` |

Los dos criterios no satisfechos están ambos justificados por medición y
registrados como diferido (6.5) o refutado (6.8); ninguno de los dos es
bloqueante para 1.0 según §20.6 del `AUDIT_1.0.md`.
