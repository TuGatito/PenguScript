---

<a id="sec-25"></a>
## 25. Decisiones de diseño (ADR)

### 25.1 ADR anteriores

Las decisiones D0–D25 de la spec `1.0.0-rc.1` quedan **superadas** por el nuevo
rumbo. Se conservan en `scratch/legacy/LANGUAGE_rc1.md` como historia, no como
norma. Ninguna se cita en las secciones normativas de este documento.

### D26. Lenguaje propio con backend invisible

**Contexto:** la spec anterior se presentaba como un lenguaje que compilaba a
otro lenguaje y exponía sus tipos.

**Decisión:** PenguScript es un lenguaje propio. El backend es un detalle de
implementación; el usuario no escribe ni ve su código.

**Alternativas:** seguir siendo un transpilador; generar código directamente.

**Consecuencias:** la superficie se juzga por sí misma, no por paridad. Los
errores del backend se traducen a diagnósticos propios.

### D27. Minimalismo de ~15 conceptos

**Contexto:** la spec anterior tenía 71 secciones y más de 400 diagnósticos.

**Decisión:** el núcleo tiene los conceptos de §1. Todo lo demás es `std`, una
herramienta externa o no existe.

**Consecuencias:** se eliminan familias enteras de features y se recorta el
catálogo a 150 códigos como máximo.

### D28. Referencias sin anotaciones de vida

**Contexto:** el usuario no debe aprender un sistema de vidas para escribir
código de sistemas.

**Decisión:** `&T`/`&mut T` solo en parámetros y locales. El compilador infiere;
si la referencia escapa, error `PGS-E1801`. No se guardan referencias en
records, sums, retornos ni alias.

**Alternativas:** exigir anotaciones; copiar siempre; usar solo valores owned.

**Consecuencias:** se pierden vistas persistentes; se ganan reglas simples y
un backend que puede inferir el resto.

### D29. Operadores minimalistas

**Contexto:** la sobrecarga de operadores puede volverse un lenguaje dentro del
lenguaje.

**Decisión:** solo `Add`, `Sub`, `Mul`, `Div`, `Rem`, `Neg`, `Eq` y `Ord`, con
`Self` contra `Self`, en `std.ops`. Sin tipos asociados. `[]`, `Deref`, `From`
y `Display` no se sobrecargan.

**Consecuencias:** menos magia; los tipos que necesitan indexación usan
métodos con nombre.

### D30. FFI de entrada

**Contexto:** exportar funciones a C obliga a estabilizar ABI y tipos.

**Decisión:** v1 solo importa funciones C con `foreign "C"`. No exporta
funciones PenguScript. `curse` es la frontera auditada.

**Consecuencias:** FFI como puerta, no como grieta. La exportación se difiere.

### D31. Sin macros ni atributos generales

**Contexto:** las macros y los atributos son una superficie enorme.

**Decisión:** no hay macros de usuario. Solo `@@derive` y `@@test`. El resto de
los atributos son detalles del backend.

**Consecuencias:** se pierde metaprogramación; se gana un lenguaje que se lee
completo.

### D32. `?T` sí, `!T` no

**Contexto:** dos azúcares para `Option` y `Result` duplican conceptos.

**Decisión:** `?T` es `Option[T]`. Los errores se escriben `Result[T, E]`
explícito.

**Consecuencias:** una sola forma corta; el error siempre tiene tipo concreto.

### D33. `Rc`/`Arc` fuera de la prelude

**Contexto:** compartir con contadores es una decisión de costo visible.

**Decisión:** `Rc` y `Arc` se importan de `std`. La prelude solo tiene `Box`,
`Vec`, `String`, `Map`, `Set` y `Option`/`Result`.

**Consecuencias:** el costo de compartir se ve en el import.

### D34. Karambit

**Contexto:** la tentación de agregar features “porque el backend puede”.

**Decisión:** la ausencia de features es una feature. Cada adición debe pagar
su costo en superficie, diagnóstico y documentación.

**Consecuencias:** el documento se mantiene corto; las features dudosas van a
§22.

[↑ Volver al índice](#indice)
