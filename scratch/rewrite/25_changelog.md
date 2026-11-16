---

<a id="sec-26"></a>
## 26. Changelog

### 26.1 Versión

| Componente | Versión |
|---|---|
| Spec | `0.5.0` |
| Compilador | `0.5.0` |
| Edición | `2024` |
| Backend mínimo | `1.85.0` |

`0.5.0` es una reescritura mayor, no un release candidate. Rompe la
compatibilidad con `1.0.0-rc.1`.

### 26.2 `0.5.0` — reescritura de misión

- PenguScript deja de presentarse como un transpilador y pasa a ser un lenguaje
  propio con backend invisible.
- Núcleo reducido a ~15 conceptos.
- Referencias sin anotaciones de vida; prohibidas en records, sums, retornos y
  alias.
- Pacts minimalistas: solo métodos con receptor, un superpact como máximo, sin
  tipos asociados.
- Operadores limitados a `std.ops`; sin `Index`, `Deref`, `From` ni `Display`
  sobrecargables.
- `?T` se mantiene; `!T` se elimina.
- Sin macros de usuario; solo `@@derive` y `@@test`.
- FFI solo de entrada; sin exportación a C.
- Sin build scripts.
- Catálogo de diagnósticos reducido a 150 códigos como máximo.
- Matriz de garantías reducida a 50 filas como máximo.
- Nuevas ADR D26–D34.
- Apéndice Z con las features eliminadas.

### 26.3 Compatibilidad

- Un programa `1.0.0-rc.1` no compila en `0.5.0` si usa lifetimes escritos,
  `where`, tipos asociados, GATs, `dyn`, `impl Trait`, async, macros, atributos
  generales, `rust` blocks o exportación FFI.
- El compilador `0.5.x` rechaza la sintaxis retirada con `PGS-E1010` o con el
  diagnóstico de la sección correspondiente.
- Las versiones `0.5.x` son compatibles entre sí en el núcleo; una feature
  nueva solo entra en una versión menor si no rompe programas existentes.

### 26.4 Política

- `0.x`: cambios mayores permitidos; se documentan en este changelog.
- `1.x`: solo adiciones compatibles; las eliminaciones requieren `2.0`.
- Un diagnóstico retirado no se reutiliza.
- Una feature diferida puede volver en una versión mayor, nunca en un parche.

[↑ Volver al índice](#indice)
