# psc.lsp.docs

> Source: `src/psc/lsp/docs.pengu`

psc/lsp/docs.pengu — documentación breve (inglés) para hover.

El LSP la usa cuando el cursor está sobre una palabra clave, un tipo
incorporado o un operador. El texto está pensado para quien llega al
lenguaje por primera vez: qué hace y cuándo se usa, sin jerga innecesaria.

## Memoria
Sólo devuelve literales estáticos; no asigna.

---

### `lookup`

> **lookup**(word: string) -> string

 Documentación de una palabra clave, tipo u operador. `""` si no hay.

### `keyword_doc`

> **keyword_doc**(word: string) -> string

 Palabras clave y operadores con forma de palabra.

### `type_doc`

> **type_doc**(word: string) -> string

 Tipos incorporados.

