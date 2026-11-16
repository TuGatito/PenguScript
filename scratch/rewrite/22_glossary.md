---

<a id="sec-23"></a>
## 23. Glosario

**Backend filoso.** El compilador que traduce PenguScript a código máquina.
Es invisible para el usuario; no se edita ni se ve.

**Karambit.** Metáfora del lenguaje: chico, curvo, filoso, capaz. No una navaja
suiza.

**Núcleo.** Los ~15 conceptos de §1. Todo lo demás es `std` o no existe.

**Prelude.** Nombres disponibles sin `summon`: tipos primitivos, `Option`,
`Result`, `Vec`, `Map`, `Set`, `String`, `Box`, `print`, `format`, `panic`,
`assert`, `Show`, `none`, `some`, `ok`, `err`.

**Binding.** Nombre que posee un valor. `bind` es inmutable; `morph` es mutable.

**Record.** Tipo producto con campos con nombre. Se declara con `rune`.

**Sum.** Tipo con variantes. Se declara con `enchanting`.

**Newtype.** Record de un solo campo; no se convierte solo en su campo.

**Pact.** Contrato de métodos con receptor. Se declara con `pact`.

**Ritual.** Implementación de métodos o de un pact. Se declara con `ritual`.

**`Show`.** Único pact de la prelude; lo usan `print` y `format`.

**Tome.** Unidad de compilación; su manifiesto es `Tome.toml`.

**Scroll.** Módulo. Puede ser inline o un archivo.

**Summon.** Import explícito de un nombre o módulo.

**Unveil.** Visibilidad pública (o acotada con `(tome)`/`(scroll)`).

**Grimoire.** Punto de entrada del binario.

**Ownership.** Regla de un único dueño para los valores owned.

**Préstamo.** Referencia temporal `&T`/`&mut T`; no escapa del scope.

**Move.** Transferencia de propiedad; el origen deja de ser usable.

**Copy.** Copia implícita de tipos simples.

**Clone.** Copia profunda explícita con `.clone()`.

**Option.** Tipo que representa ausencia: `some(T)` o `none`.

**Result.** Tipo que representa éxito o error: `ok(T)` o `err(E)`.

**`?`.** Operador que propaga `none`/`err` al caller.

**Patrón.** Forma que se compara con un valor en `match` o `bind ... else`.

**Exhaustivo.** Un `match` que cubre todos los casos sin `else`.

**FFI.** Frontera con C. Se declara con `foreign` y se llama dentro de `curse`.

**Curse.** Bloque auditado que permite llamar a FFI.

**Diferido.** Fuera del núcleo por ahora; puede volver en una versión mayor.

[↑ Volver al índice](#indice)
