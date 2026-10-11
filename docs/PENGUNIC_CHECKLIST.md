# Checklist Pengunic 2.0 (operativa)

Marcar antes de cada commit de módulo. Cada chunk de la migración reescribe un
`std/<mod>.pengu`; esta lista es el mínimo común y se aplica igual a los 11
chunks restantes.

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
