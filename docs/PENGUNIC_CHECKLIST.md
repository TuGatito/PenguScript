# Checklist Pengunic 2.0 (operativa)

Marcar antes de cada commit de módulo. Cada chunk de la migración reescribe un
`std/<mod>.pengu`; esta lista es el mínimo común y se aplica igual a los 11
chunks restantes.

## Bug handling (regla nueva del Chunk 6)

> **Ningún bug se ignora.** Encontrado un bug — al leer, al escribir tests, al
> compilar o al razonar sobre el código — se arregla, se documenta y se le pone
> un test. No vale documentarlo y seguir. Protocolo obligatorio:

- [ ] **DETECTAR** activamente, no esperar a que aparezca. Leer el módulo línea a
      línea antes de reescribir y anotar cada defecto, incluidos los que el brief
      no liste.
- [ ] **REPORTAR** en `docs/BUGS_FIXED_CHUNK<N>.md` con la estructura fija:
      `### BUG-N: <título>`, **Módulo**, **Función**, **Síntoma**, **Causa raíz**,
      **Impacto**, **Fix aplicado**, **Test de regresión**.
- [ ] **ARREGLAR** el código para que el bug no pueda volver a ocurrir.
- [ ] **TEST** de regresión que **falla sin el fix** y pasa con él (interno
      `test "…"` y, cuando sea observable por stdout/stderr/exit code, caso en
      `tests/stdlib/test_<mod>.py`).
- [ ] **VERIFICAR**: `pengu test --entry std/<mod>.pengu` + la suite externa en
      verde.
- [ ] Los bugs que exijan tocar el compilador **no se arreglan a mano** (§5.3 del
      brief): se documentan en una sección aparte del bug doc, se esquivan dentro
      del chunk y se pasan al workstream de compilador. Documentar un bug del
      compilador **no** es ignorarlo.
- [ ] Contar los bugs arreglados en el reporte final y en
      `docs/MIGRATION_2.0_PROGRESS.md`.

## Docstrings

- [ ] Docstring de módulo con `## ## Ejemplo` y `## ## Memoria`
- [ ] Docstring por `weave` con `##`, `## ## Parámetros` y `## ## Retorno`
- [ ] Docstring por `antiquus` con `## ## Motivo` y `## ## Memoria`
- [ ] Docstring por `const` / `rune` / `omen` que lo necesite
- [ ] Todos en inglés (prosa); las secciones usan los nombres del brief
- [ ] Los invariantes de ownership se dicen explícitamente
      («el `string` devuelto es owned, libéralo con `banish`»)
- [ ] `##` inmediatamente encima del símbolo, sin línea en blanco entre medias

## Estilo

- [ ] `judge` en lugar de cadenas de `if/else` cuando aplique
- [ ] `if c then a else b` en lugar de `var tmp` + `if`
- [ ] `defer banish x` para temporales owned
- [ ] `when debug:` en asserts que deben desaparecer en release
- [ ] `let` para inmutables, `var` solo si muta
- [ ] SIN `+` sobre strings — solo `"{a}{b}"`
- [ ] SIN `+=` sobre strings
- [ ] SIN `str_*_or_panic` como fallback de parse: usar `maybe`
- [ ] `antiquus` solo para lo estrictamente justificado en su `## ## Motivo`

## `antiquus`

- [ ] Cuerpo en `r"""..."""` a columna 0 (todas las líneas, sin mezclar sangrías:
      `pengu fmt` reindenta el archivo entero si una línea queda indentada)
- [ ] Parámetros con nombres C válidos (`if`, `int`, `while` dan `E0035`)
- [ ] Sin `many T` (usar `slice of T` y leer `.data` / `.len`)
- [ ] Si es punto de entrada FFI, lleva `@export("pengu_<mod>_...")`
- [ ] El nombre no colisiona con la libc cuando el módulo es la entrada:
      añadir `insignia <mod>_` si se expone `exit`, `assert`, `printf`, …

## API

- [ ] Todos los símbolos públicos listados en el brief del chunk
- [ ] Firmas exactas al contrato
- [ ] Nombres según §2.3 de la guía
- [ ] `<MOD>_VERSION` actualizado y `docs/<MOD>_API.md` congelado
- [ ] Ningún helper extra fuera del contrato (los `_privados` se documentan)

## Tests

- [ ] Bloques `test` dentro del `.pengu` (mínimo 5), bajo `# --- Tests ---`
- [ ] Cada `test` puede correr en aislamiento (sin estado global)
- [ ] `tests/stdlib/test_<mod>.py` autocontenido: cada test escribe su programa y
      lo ejecuta por el pipeline real (Pengu → C → cc → binario). Desde el
      Chunk 3 la suite vive en `tests/stdlib/`, no en la raíz: `test_test_policy`
      congela `MAX_ROOT_TEST_FILES = 15` y `spark`/`scrolls`/`oracle` ya la
      llenaron
- [ ] Los tests comparan comportamiento (stdout/stderr/exit code), nunca el C
      generado
- [ ] Tests cubren casos borde y errores documentados
- [ ] Si el módulo movió `static inline` del runtime, revisar
      `tests/runtime/`: esos tests solo incluyen `pengu_runtime.h` y no ven los
      `antiquus`
- [ ] Si el módulo tenía tests solo-std, borrarlos y reparar los tests que los
      importaban o consumían como corpus

## Migración de `static inline` del runtime (Chunk 2+)

- [ ] Antes de mover nada: `grep` del símbolo en `std/`, `pengu_parser/`,
      `tests/runtime/` y `tests/conformance/`. Solo se mueve si **ningún otro
      módulo ni el codegen** lo usa.
- [ ] El codegen emite `pengu_string_char_at`, `pengu_string_substring`,
      `pengu_string_equal`, `pengu_string_compare`, `pengu_string_split` y
      `pengu__find_sub`: **no se mueven**.
- [ ] Cuidado con los nombres: con `insignia <mod>_`, un `antiquus _find_sub`
      colisiona con el `pengu__find_sub` de la cabecera. Usa un nombre distinto
      o un `declare` del helper que se queda.
- [ ] Regla del C-block redundante: si el C-block y un `weave` Pengu hacen lo
      mismo, se queda el C-block y **se borra el weave**. Nada de dos
      implementaciones.
- [ ] Si el módulo mueve helpers que `tests/runtime/test_runtime_strings.py`
      llama desde C, recortar esas secciones del driver y anotar que su cobertura
      pasa al `tests/test_<mod>.py`.

## Contenedores (`oracle`, `trial`, …)

- [ ] **Invariante de reconstrucción:** nunca `return m` / `return self` para un
      parámetro o receptor contenedor; se reconstruye (`some v`, `maybe none`,
      `calling ok_of with v`, `calling err_of with e`). Evita el doble free.
- [ ] En un `enchanting` con `shard`, `self` es `ref to T`: leer el valor con
      `essence of self`, no `self`.
- [ ] `where` no existe en métodos: los bounds viven en los `weave shard T
      where T: ...` de módulo.
- [ ] Los tipos legados se mantienen y se marcan con el **docstring**
      `## @deprecated Use X instead.` (no el atributo real, que emite W0006).

## Excepción `loom`/`tally` y módulos de colecciones (Chunk 3)

- [ ] `std.loom` y `std.tally` **no se fusionan**: comparten 15 nombres con
      contratos distintos (safe vs sentinel), excepción documentada en
      `LANGUAGE.md` §19.1.1 y `PenguScriptGuideSpanish.md` §15. No se renombran
      ni se añaden sufijos `_safe`/`_sentinel`.
- [ ] `loom` **no declara `enchanting`** (no invade los métodos de `tally`); sus
      operaciones son `weave` de módulo.
- [ ] Un método dentro de un `enchanting` genérico no puede llamar a otro
      genérico: cada cuerpo es autocontenido y las listas `list of T` se
      construyen con comprehensions, no con `push`/`pop`.
- [ ] Al quitar `import std.scrolls` de un módulo, revisar **todos** los usos de
      métodos de `string` que aportaba `scrolls` (`contains`, `starts_with`,
      `ends_with`, `substring`, …): hay que reescribirlos con slicing nativo
      (`s at a to b`, con el fin **exclusivo**) o conservar la dependencia.
- [ ] Las comprobaciones no paniqueantes nuevas devuelven el
      `result of string to string` nativo (`calling ok_of with "ok"` /
      `calling err_of with msg`); las legacy que devuelven `ResultString` se
      conservan y se marcan `## @deprecated Use <x>_native instead.`

## Colecciones genéricas y `antiquus` de contenedores (Chunk 4)

- [ ] `antiquus` con un parámetro `list of T`: el parámetro llega **por valor**
      como `PenguList`; usa `xs.data` / `xs.len` (nunca `->`). Mutar el buffer muta
      la lista del llamante.
- [ ] Tamaños de elemento en C: `int` = `int32_t` (4 bytes), `float` = `float`
      (32 bits, **no** `double`), `f64`/`double` = 8, `string` = `PenguString`. Un
      `qsort` con el `sizeof` equivocado corrompe el heap (SIGABRT).
- [ ] Los `antiquus` que ordenan llevan `## ## Motivo` + `## ## Memoria` y
      sustituyen al bucle Pengu equivalente (regla del C-block redundante).
- [ ] Los **bounds de un `enchanting` genérico no se comprueban** al resolver el
      método: la operación se monomorfiza para cualquier receptor con el que se
      llame. Por eso una comparación genérica `a > b` rompe `map of string to *`
      (C no define `>` para `PenguString`), aunque el bound sea `K: Ordo`.
- [ ] Para ordenar de verdad genéricamente hace falta un `concept` propio con un
      `bind` por tipo (`concept Ordered shard T: weave cmp with other as T into
      int`) y llamar `calling a.cmp with b` en el cuerpo. `alias` se desenvuelve
      al tipo base; `seal`/`rune` necesitan su propio `bind`.
- [ ] Un `enchanting map of string to shard V` **no** sirve: el compilador no
      infiere `V` para un método que lo devuelve. Usa bloques concretos o una
      función de módulo genérica (que sí infiere de sus argumentos).
- [ ] Un `rune` genérico no admite cláusula `where` (`rune_decl` no la tiene):
      escribe `rune Set shard T:` y documenta el bound implícito del campo.
- [ ] Un constructor `ritual` genérico no infiere sus parámetros desde el tipo
      declarado de la variable (`E0005`): expón `calling Set.empty of T` y/o
      constructores concretos.

## Retrofit de tipos en funciones de módulo (Chunk 5)

- [ ] Al generalizar una función de módulo de `list of int` a
      `list of shard T where T: <bound>`, **el nombre, el orden de parámetros y
      la semántica no cambian**: solo se ensancha el dominio de tipos.
- [ ] El cuerpo de un `weave shard T` es **autocontenido**: no puede delegar en
      otro `weave`/método genérico (`return calling l.sum` genera aritmética de
      `void *`). Se escribe el bucle directo.
- [ ] Los módulos con funciones de módulo genéricas llevan `insignia <mod>_`:
      es lo que hace fiable la resolución de `calling mod.fn` cuando el programa
      usa varias monomorfizaciones del mismo genérico.
- [ ] Las operaciones de **orden** con `T` genérico usan el `concept Ordered` de
      `std.atlas` (`calling a.cmp with b`): `>` no compila para `PenguString` en
      un cuerpo genérico (y `E0005` en código concreto), mientras que `==` sí
      funciona genéricamente. Las operaciones `Par` no necesitan concepto.
- [ ] Los defaults de tipo concreto (`tally.at_or`, `tally.clamp_all`) **no** se
      cambian: se añade una variante `*_shard` sin default.
- [ ] `tests/stdlib/test_<mod>.py` sigue verde **sin tocarlo** y los módulos
      consumidores siguen compilando.

## Aleatoriedad y logging (Chunk 6)

- [ ] Un módulo que pueda compilarse como **módulo de entrada** (es decir, que
      tenga tests internos) lleva `insignia <mod>_`: sin él, un `weave log`,
      `warn`, `error` o `seed` emite un símbolo C sin prefijo que colisiona con la
      libc (`math.h` declara `double log(double)`).
- [ ] La `insignia` va **después** de los `declare`, para que los puentes del
      runtime conserven sus nombres exactos (`pengu_c_*`, `pengu_log_*`).
- [ ] Un `antiquus` que solo se llama desde C (por ejemplo un mutex) lleva
      `@export("...")`: el DCE no ve la llamada y lo podaría. El nombre exportado
      debe incluir el prefijo del módulo.
- [ ] Nada de `chr 123` / `chr 125` para llaves: usar un **raw string**
      (`r"…{…}…"`). Los templates de formato (`set_format`) también son raw.
- [ ] Un `const` con llaves **no se puede pasar a un weave** (bug de compilador
      C-1): exponer un `weave` que devuelva el literal raw.
- [ ] Un cuerpo `antiquus` no lleva comentarios `/* … */`: `pengu fmt` reindenta
      el fichero entero (bug C-3). Usar `//`.
- [ ] Las llamadas `ritual` de un rune importado son **no cualificadas**
      (`calling Logger.new`), nunca `calling modulo.Logger.new` (bug C-2).
- [ ] No comparar dos `string` de nivel de módulo con `==`/`!=` (bug C-4: emite
      `PenguString == PenguString`); comparar contra un literal local o vía el
      comparador `antiquus` (`memcmp`).
- [ ] No construir texto con `"…{(chr 34)}…"` (bug C-5: la comilla se pliega
      cruda en el literal C); usar el escape `\"`.
- [ ] Un estado de proceso único (registro, celda de configuración) vive en un
      `weave` accesor con `static var`, o en una celda C con `antiquus`; nunca en
      un `var` de nivel superior (prohibido, `E0002`).
- [ ] La selección ponderada con pesos de tamaño arbitrario acumula en `i64`; el
      objetivo aleatorio se escala a `float`. Nunca sumar pesos en `int`.
- [ ] Una distribución con rechazo expone el agotamiento como `maybe none` y
      reintenta; jamás devuelve un valor "de relleno" silencioso.
- [ ] Una distribución que tome `log(u)` o `1/u` usa un helper de intervalo
      abierto `(0, 1)`; nunca pasa el draw crudo a `log`.
- [ ] Los helpers públicos nuevos de un módulo transversal (bytes, base64, UUID)
      se implementan sobre un único primitivo (`rand_bytes`) y se documenta que
      **no** son criptográficamente seguros.

## Datos binarios, JSON y criptografía (Chunk 7)

- [ ] Ningún `set out is "{out}{x}"` en un bucle: usa un buffer C
      pre-dimensionado (`antiquus`) o una `list of string` con un `_concat_parts`
      **propio**. `std.scrolls.join` es cuadrático y no sirve para esto.
- [ ] Los cuerpos `antiquus` van **planos a columna 0**, incluidas las líneas de
      continuación de las macros C: `pengu fmt` no converge si mezclan sangría.
- [ ] Ningún `chr` **constante** en una posición binaria o entrecomillada:
      `chr 0` desaparece, `chr 34`/`chr 92` rompen el C emitido y `chr N` con
      `N > 127` se convierte en dos bytes UTF-8. Construye el carácter desde una
      variable `int` (`_quote_char`, `nul_byte`, …).
- [ ] Un `omen` nuevo no reutiliza nombres de variante de un omen existente
      (E0046: el espacio de nombres es global).
- [ ] Un payload recursivo viaja por un `rune` envoltorio declarado **después**
      del omen (un `list of Omen` dentro del propio omen no unifica).
- [ ] `Module.Variant` (sin el nombre del omen) no se usa: pasa el checker y
      emite un símbolo C sin manglar. Usa `Module.Omen.Variant` o el alias corto.
- [ ] Los constructores `ritual` se llaman por el nombre del tipo exportado
      (`HashState.new_sha256`), no cualificados por el módulo.
- [ ] `std.spark.parse_float` **no se usa**: devuelve 0 para toda entrada
      (hallazgo X-1); escribe un parser acotado propio.
- [ ] Los secretos y MACs se comparan con `const_time_eq`/`digest_compare`,
      nunca con `==`; `verify_hash` debe rechazar un algoritmo desconocido antes
      de comparar.
- [ ] Todo `*_file` de hash/CRC hace **streaming** por bloques (64 KiB); ninguno
      materializa el fichero entero.
- [ ] Los buffers binarios se construyen por longitud (`memcpy`), nunca por
      interpolación con `printf`-style: los NUL embebidos deben sobrevivir.
- [ ] Ningún algoritmo criptográfico nuevo se añade al runtime si un `antiquus`
      del propio módulo lo resuelve: `pengu_runtime.h`/`.c` solo cambian si el
      brief lo autoriza, y entonces **solo añadiendo** símbolos.

## Verificación

- [ ] `pengu check --entry std/<mod>.pengu` pasa (0 errores; W0005 aceptado)
- [ ] `pengu test --entry std/<mod>.pengu` pasa
- [ ] `pengu fmt --check std/<mod>.pengu` pasa
- [ ] `pytest tests/stdlib/test_<mod>.py -v` pasa
- [ ] `pengu run` de un programa mínimo imprime por stdout/stderr lo esperado
- [ ] `git status` sin `.o`, `.pyc`, `build/` ni ficheros sueltos
- [ ] `git diff pengu_runtime.h` solo elimina los símbolos movidos
- [ ] `docs/MIGRATION_2.0_PROGRESS.md` actualizado

## Commit

- [ ] Un único commit, mensaje `feat(std/<mod>): migrate to Pengunic 2.0, ...`
- [ ] Sin `git push`; sin `--amend` sobre commits ajenos
