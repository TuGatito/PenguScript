# psc.diag_compat

> Source: `src/psc/diag_compat.pengu`

psc/diag_compat.pengu — constructor compatible con bootstraps antiguos.

Los compiladores publicados antes de PSC resuelven `diag.DiagnosticBag.new`
como un método del módulo `diag`. Este helper hace la construcción a través
de un import sin alias, que ambos compiladores entienden.

---

### `new_diagnostic_bag`

> **new_diagnostic_bag**() -> DiagnosticBag

 Construye un `DiagnosticBag` vacío.

 ## Retorno
 El bag recién creado; liberar con `banish`.

