# Auditoría del compilador 0.29.0

| Campo | Valor |
|---|---|
| Fecha | 2026-11-04 |
| Compilador | `psc 0.29.0` (desde `0.28.9`) |
| Ámbito | resolución de nombres, codegen C, parser, lexer, caché del driver |
| Origen | `portus/scratch/portus-compiler-fixes.md` (v0.28.8) |
| Estado | Correcciones aplicadas y verificadas |

## 1. Resumen

Once bugs abiertos en el informe de portus más una regresión descubierta al
compilar portus con el compilador nuevo. La mayoría no eran fallos
independientes: compartían dos causas estructurales.

1. **La resolución de nombres ignoraba el módulo que llama.** Al no encontrar un
   nombre en la cadena de scopes, `lookup` caía a los mapas globales
   `functions`/`consts` (el último módulo recolectado ganaba) y `lookup_name`
   escaneaba todos los `SkImport` del programa. `lookup_type` consultaba los
   mapas globales de tipos antes que el scope local. De ahí los bugs 8, 14, 15,
   17 y la regresión `text.copy` de portus.
2. **Codegen deshacía la resolución semántica.** `call_expr` recibía el símbolo
   correcto en `ann.symbol_of`, pero tres heurísticas para `mod.fn`
   reconstruían el nombre C con el primer y último token y lo sobrescribían.

El resto eran fallos localizados: un slice exclusivo mal calculado en
`module_scope` (14), bloques en posición de valor que solo emitían la última
expresión (9), constructores de variante de omen sin literal compuesto (10),
argumentos de tipo genérico sin sustituir (3), `or:` consumido por el parser de
argumentos (19), escapes dentro de interpolación (16) y una clave de caché sin
los headers C (20).

## 2. Evidencia y causa por bug

| Bug | Síntoma reproducible | Causa | Commit |
|---|---|---|---|
| 3 | `returning 'void **' … 'Thing *'` | `NdGenericArgs` usaba `type_from_ast` sobre `of T` sin aplicar `names.subst` | `f938edc` |
| 8 | imprime `1` en vez de `7` | `demo.core.fn` dentro de `demo`: el nombre base resolvía al import del consumidor y el acceso intermedio no propagaba `base_import`; además codegen pisaba el nombre anotado | `4e3d17b`, `e254415` |
| 9 | `9 0`; C con `a` inexistente | `NdDoExpr`/`NdBlock` emitían solo la última expresión | `161698f` |
| 10 | `E _p = E_Empty;` (C inválido) | la variante se trataba como constante, sin `(E){.tag = …}` | `7a19cc9` |
| 14 | `route:x` en vez de `router:x` | `module_scope` recortaba seis caracteres a cualquier ruta y `router.pengu` caía en `route.pengu` | `4e3d17b` |
| 15 | `E0005 too few arguments` | fallback a los mapas globales por nombre | `4e3d17b` |
| 16 | se imprime `{m or else "none"}` | `find_balanced` no saltaba `\"`; el grupo nunca cerraba | `682f278` |
| 17 | C inválido con `ref to Handler` | `lookup_type` miraba antes los mapas globales; dos `struct Handler` sin prefijo | `4e3d17b`, `765bf3a` |
| 18 | `expected 'Wrapped', got 'Thing'` | **no reproduce** en 0.28.9/0.29.0; solo el retorno realmente incompatible da `E0020` | `4bbce0e` (test) |
| 19 | `get(&app, "/", 0)` | los argumentos consumían el nivel `or:` y el postfijo se ligaba al último argumento | `682f278` |
| 20 | editar un header no recompila | la clave de caché no hasheaba `c_dir`/`include_dir` | `1fe7146` |
| — | `text.copy` → `memoria_copy` | codegen reescribía la llamada ya resuelta con el bloque de alias `_fn` | `e254415` |

## 3. Plan de acción ejecutado

1. **Reproducir cada bug** con `build/psc` 0.28.9 en proyectos temporales
   (`/tmp/audit/b3 … b20`) y con un mínimo del patrón de portus
   (`/tmp/copytest2`).
2. **Arreglar la resolución antes que el codegen**, para que las anotaciones
   semánticas fuesen fiables:
   - `current_module` fijado en `collect_all`/`check_bodies`;
   - `module_of_scope`, `scope_of_module` y grafo de imports directos;
   - BFS de módulos visibles en `lookup`/`lookup_name`/`lookup_type`;
   - mapas globales solo como último recurso.
3. **Hacer que codegen respete la anotación** (`sid_direct`) antes de tocar las
   heurísticas de nombres.
4. **Arreglar cada fallo localizado** con su reproducción delante.
5. **Cerrar la suite**: regresión por bug, `regress.sh`, `run.sh`, `smoke.sh`,
   build de portus y sus e2e.
6. **Documentar y versionar**: CHANGELOG, `LANGUAGE` (ES/EN) y `SEMA`, bump a
   0.29.0.

## 4. Decisiones de diseño

- **BFS de imports visibles**, no solo el scope del módulo: un nombre suelto
  debe poder usar lo que el módulo importa (incluido lo que importan sus
  imports), pero nunca un módulo ajeno al grafo.
- **Prefijar tipos nominales solo en colisión.** Prefijar siempre rompía los
  bloques `antiquus` de `std/json`, `std/compressus` y `std/carmen`, que
  escriben el nombre C a mano, y la transición desde el bootstrap. Los nombres
  únicos conservan su C histórico; `Handler` en dos módulos pasa a
  `a_Handler`/`main_Handler`.
- **Bloques como sentencia-expresión de GNU** `__extension__(({ … }))`. Es la
  forma de conservar sentencias y valor sin crear un lambda ni romper el
  `#line`. Consecuencia: el C generado requiere GCC o Clang, las toolchains
  soportadas.
- **Hook en `CgContext` para los bloques** en vez de importar `stmt` desde
  `expr`: el compilador rechaza el ciclo de imports. `bundle` instala
  `stmt.block_value` al generar.

## 5. Verificación

- `./tools/build.sh --no-wasm` → OK; `psc 0.29.0` en el PATH.
- `tests/regress.sh` → 21/21 OK (10 previas + 11 nuevas).
- `tests/run.sh` → 104/104 OK.
- `tests/smoke.sh` → OK.
- portus: `psc build . --profile release` OK; e2e `hello`, `security` y `ws`
  OK.

## 6. Notas y deuda pendiente

- **Bug 18**: no se pudo reproducir con 0.28.9 ni 0.29.0. El test
  `regress_alias_return.sh` fija que el tipo subyacente se acepta y que un
  valor incompatible sigue dando `E0020`. Si reaparece, hace falta el proyecto
  exacto del informe.
- **Bug 13** del informe ya estaba marcado como no reproducible (otra cara del
  15).
- La interpolación de un `maybe` vacío (`"hola {m}"`) imprime el hueco; no se
  cambió el comportamiento en esta auditoría.
- `transmute ref to T to ref to void` sigue emitiendo la dirección de la
  variable puntero; es un bug latente del informe §22, fuera del alcance de
  estos arreglos.
