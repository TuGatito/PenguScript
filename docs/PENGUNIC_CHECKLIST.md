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
- [ ] `tests/test_<mod>.py` autocontenido: cada test escribe su programa y lo
      ejecuta por el pipeline real (Pengu → C → cc → binario)
- [ ] Los tests comparan comportamiento (stdout/stderr/exit code), nunca el C
      generado
- [ ] Tests cubren casos borde y errores documentados
- [ ] Si el módulo movió `static inline` del runtime, revisar
      `tests/runtime/`: esos tests solo incluyen `pengu_runtime.h` y no ven los
      `antiquus`
- [ ] Si el módulo tenía tests solo-std, borrarlos y reparar los tests que los
      importaban o consumían como corpus

## Verificación

- [ ] `pengu check --entry std/<mod>.pengu` pasa (0 errores; W0005 aceptado)
- [ ] `pengu test --entry std/<mod>.pengu` pasa
- [ ] `pengu fmt --check std/<mod>.pengu` pasa
- [ ] `pytest tests/test_<mod>.py -v` pasa
- [ ] `pengu run` de un programa mínimo imprime por stdout/stderr lo esperado
- [ ] `git status` sin `.o`, `.pyc`, `build/` ni ficheros sueltos
- [ ] `git diff pengu_runtime.h` solo elimina los símbolos movidos
- [ ] `docs/MIGRATION_2.0_PROGRESS.md` actualizado

## Commit

- [ ] Un único commit, mensaje `feat(std/<mod>): migrate to Pengunic 2.0, ...`
- [ ] Sin `git push`; sin `--amend` sobre commits ajenos
