# psc.codegen.antiquus

> Source: `src/psc/codegen/antiquus.pengu`

psc/codegen/antiquus.pengu — bloques C crudos (`antiquus`).

F3 guarda el cuerpo como un literal de string en el AST. El codegen lo
decodifica y lo emite tal cual, sin reinterpretarlo.

---

### `decode`

> **decode**(raw: string) -> string

 Decodifica escapes de un literal PenguScript ya sin comillas.

 ## Memoria
 Devuelve string owned.

### `body_of`

> **body_of**(c: ref to CgContext, f: CgFunction) -> string

 Texto C crudo de una declaración antiquus.

 El lexer entrega un token de cuerpo crudo; se quitan los delimitadores
 (`r"""`, `"""`, `"` o `'`) pero **no** se decodifican escapes: el cuerpo es C
 literal y un `\n` dentro de `fputc('\n', ...)` debe seguir siendo `\n`.

 ## Memoria
 Devuelve string owned.

### `emit_body`

> **emit_body**(c: ref to CgContext, f: CgFunction) -> void

 Emite el cuerpo crudo.

 ## Memoria
 Strings temporales liberados.

