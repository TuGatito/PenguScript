# Diagnósticos diferidos de Fase 2

Estos cinco códigos del catálogo 0.6.0 no se emiten todavía. No son deuda
oculta: cada uno depende de una superficie que no existe en el frontend/checker
actual. Gate C los acepta como **justificados**, no como implementados.

| Código | Motivo | Se implementará en |
|---|---|---|
| `PGS-E1205` | La regla huérfana necesita el grafo de módulos/imports cargado desde disco; C1 solo construye `scroll` inline y resuelve imports después de bajar los items. | C9 (loader e imports) |
| `PGS-E1506` | La spec no define si `panic` en una rama de valor es error o diverge; `Never` ya es compatible con cualquier tipo. Falta decisión normativa. | Revisión de spec |
| `PGS-E1705` | Los doc tests requieren `pengu test --doc` y un runner de snippets; no existe en 0.6.0. | C11 (tooling/test runner) |
| `PGS-E3007` | La descripción “`?T` usado con un tipo que no es `Option`” es ambigua: `?T` ya *es* `Option[T]`, y el uso de `?` fuera de Option/Result se reporta con `E1405`. | Revisión de spec |
| `PGS-W1210` | La colisión método inherente/pact sobre primitivos requiere la stdlib de primitivas (`std.int` etc.); 0.6.0 no compila esa stdlib. | C? (stdlib de primitivas) |
