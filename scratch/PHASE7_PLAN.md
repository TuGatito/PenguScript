# Fase 7 — LSP avanzado y tamaños reales

Estado: **cerrada** (2026-11-15). Esta fase cierra la calidad de editor de PenguScript:
las features que un usuario espera de rust-analyzer/clangd/pyright, el tamaño
real en bytes de cada valor y el rendimiento para proyectos grandes.

Referencias: `scratch/TOOLING_PLAN.md` §9 (matriz de capacidades), §9.4
(rendimiento) y Fase 7; `scratch/PHASE6_PLAN.md` (base ya cerrada).

## 1. Objetivo y criterio de cierre

**Objetivo.** Un servidor LSP que se pueda usar a diario: navegar, renombrar,
ver tipos y tamaños, autocompletar, plegar código, saltar a implementaciones,
listar símbolos del proyecto y recibir arreglos rápidos, sin caídas ni
regresiones de rendimiento.

**Criterio de cierre.**

1. Todas las capacidades de la tabla de §9.3 de `scratch/TOOLING_PLAN.md`
   implementadas y cubiertas por tests de protocolo contra el binario real.
2. `pengu size` y el LSP muestran el **tamaño real** de structs, enums,
   variables, campos, variantes, constantes y la huella de las funciones, con
   los números **verificados contra `std::mem::size_of` de rustc** en tests.
3. Presupuestos de rendimiento medidos y documentados; sin análisis duplicado.
4. `cargo test --workspace`, `fmt` y `clippy -D warnings` limpios.
5. Documentación: `docs/LSP.md` (capacidades, tamaños, rendimiento),
   `scratch/STATUS.md`, `scratch/TOOLING_PLAN.md` Fase 7 ✅.

## 2. Tamaño real: el problema y la decisión

El backend emite Rust cuyo layout **no es especificable** por defecto:
`struct` y `enum` sin `repr` usan el layout interno de Rust (reordena campos,
optimiza enums con nichos) y los tamaños no se pueden predecir desde Pengu.

**Decisión A0 (D17).** El backend emite representaciones deterministas:

- `rune` (record) → `#[repr(C)]`.
- `enchanting` (sum) → `#[repr(C, u32)]`.

Con eso el layout pasa a ser ABI C más un discriminante `u32`, calculable con
exactitud. Los tuplas siguen siendo tuplas de Rust: se modela su reordenación
por alineación descendente (estable).

**Decisión A0 (D18).** Los tamaños se calculan en un crate propio,
`pengu-layout`, a partir del HIR (`Layout { size, align, niche }`), no con
`rustc` en caliente. La exactitud no se asume: una matriz de tests genera el
Rust real del compilador, lo compila y compara `size_of`/`align_of` con el
motor de layout. Cualquier divergencia rompe la suite.

**Nicho (`niche`).** `Option[T]` reutiliza un valor inválido de `T` y no crece.
El motor propaga "tiene nicho" (referencias, punteros, `String`, `Vec`, `Map`,
`Set`, `CStr`, `Char`, `Bool`, agregados con algún campo con nicho). Sin nicho,
`Option[T]` se calcula como enum de dos variantes con payload.

**Qué se muestra.** El tamaño es el de un valor en memoria:

| Símbolo | Qué se muestra |
|---|---|
| `rune`, `enchanting` | `size_of` / `align_of` |
| campo de `rune`, payload de variante | tamaño del campo y offset no (fase 8) |
| `bind`/`morph`/parámetro | tamaño de su tipo inferido |
| `sigil` (constante) | tamaño de su tipo |
| función | huella: suma de parámetros por valor + retorno, y `8 B` del puntero |
| expresión en hover | tamaño del tipo de la expresión |

En el editor se ve en: hover (línea `tamaño`), inlay hints (tipo + bytes),
code lens sobre declaraciones, `documentSymbol.detail` y `pengu size` en la CLI.

## 3. Arquitectura

- **`crates/pengu-layout`** (nuevo): motor de layout; depende solo de
  `pengu-hir`/`pengu-types`. API:
  `pub struct Layout { pub size: usize, pub align: usize, pub niche: bool }`,
  `pub fn layout_of(ty: &Ty, krate: &HirCrate) -> Option<Layout>`,
  `pub fn format_size(size: usize) -> String` (`12 B`, `1.5 KiB`).
- **`crates/pengu-lsp`**: `index` gana el tipo de cada símbolo y su tamaño;
  `features` usa el motor; nuevos módulos `references`, `semantic`, `hints`,
  `lens`, `calls`, `actions`, `folding`.
- **`crates/pengu-cli`**: `pengu size [ruta]` (tabla legible) y `pengu lsp`.
- **`crates/pengu-codegen`**: `#[repr(C)]`/`#[repr(C, u32)]` en ADTs.

## 4. Fases

Estado: **A0–A6 cerradas**. Lo que quedó fuera se justifica al final de cada fase.

### A0 — Layout y tamaños (base para todo lo demás) ✅

- [x] `pengu-layout` con el motor y sus tests unitarios.
- [x] `repr(C)` / `repr(C, u32)` en el backend (con `repr(u32)` en enums sin campos:
      `repr(C, u32)` da `E0566`).
- [x] Test de verificación contra rustc (`crates/pengu-codegen/tests/layout.rs`):
      `Point`, `Mixed`, `Nested`, `Holder[Int]`, `Shape`, `Flag` y `Payload`
      comparan `size_of`/`align_of` reales con el motor.
- [x] `pengu size` en la CLI, con salida estable (ADT, huella de función y
      `sigil`; los genéricos se anuncian como tales).
- [x] Hover con tamaño: ADT (`tamaño 8 B, alineación 4 B`), función (`huella`),
      `sigil` y expresión (`tamaño`).

### A1 — Navegación: references y rename ✅

- [x] `textDocument/references` (declaración incluida u opcional).
- [x] `textDocument/prepareRename` + `textDocument/rename` (`WorkspaceEdit`,
      validación de identificador y solo lectura para `std`).
- [x] `textDocument/documentHighlight`.
- [x] Rename de locales: mismo camino textual (el índice no distingue locales y
      el compilador resuelve por nombre dentro del archivo).

### A2 — Pistas y lentes: inlay hints, code lens ✅

- [x] `textDocument/inlayHint`: tipo y bytes de `bind`/`morph`/parámetros; se
      omite el hint si la declaración ya lleva anotación.
- [x] `textDocument/codeLens`: `@@test` → `pengu.runTest`.
- [ ] `textDocument/documentLink`: **descartado con motivo**. Los módulos de
      PenguScript no son archivos (el programa es uno solo y los paquetes se
      fusionan como módulos), así que la mayoría de `summon` no tiene archivo al
      que enlazar; completion y hover ya resuelven esos nombres.

### A3 — Semántica: tokens, folding y selección ✅

- [x] `textDocument/semanticTokens/full` y `/range`, con leyenda declarada.
- [x] `textDocument/foldingRange` (bloques por indentación y comentarios).
- [x] `textDocument/selectionRange` (línea y bloque contenedor).

### A4 — Ayuda de firma e implementaciones ✅

- [x] `textDocument/signatureHelp` con parámetro activo.
- [x] `textDocument/typeDefinition` (expresión → ADT).
- [x] `textDocument/implementation` (pacto → `ritual … for`).

### A5 — Proyecto: workspace symbols y call hierarchy ✅

- [x] `workspace/symbol` sobre los documentos abiertos (en este lenguaje el
      proyecto es un archivo; las dependencias se fusionan como módulos, así que
      no hay archivos extra que indexar).
- [x] `callHierarchy/prepare`, `incomingCalls`, `outgoingCalls`, resueltos por
      nombre dentro del archivo abierto (sin sobrecarga ni sombreado).
- [ ] `workspace/didChangeWatchedFiles`: **no aplica**. El servidor analiza
      documentos abiertos y el overlay del editor es la fuente de verdad; un
      cambio en disco sin `didChange` no representa lo que el usuario ve.

### A6 — Arreglos rápidos y cierre ✅

- [x] `textDocument/codeAction`: quickfix de campos privados → `unveil`.
- [x] Rendimiento: `editors/bench.mjs`, cancelación y caché por hash.
- [x] Documentación (`docs/LSP.md`), verificación final y commit de cierre.

## 5. Rendimiento

Objetivos de §9.4 adaptados al modelo real (programa de un archivo + std):

| Escenario | Objetivo |
|---|---|
| hover/definition/references en documento ya analizado | < 50 ms |
| completion | < 100 ms |
| inlay hints de 1 000 líneas | < 150 ms |
| análisis completo de 14 000 líneas (release) | < 600 ms |
| `workspace/symbol` con 10 paquetes | < 300 ms |

Reglas: una sola pasada por petición sobre el índice (sin recorrer spans en
bucle), reutilizar `cache` (una entrada por documento), responder `null` cuando
la feature no aplica y no serializar más de lo necesario.

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| El layout de Rust cambia entre versiones | `repr(C)` fija el contrato; el test contra rustc corre en CI con el toolchain declarado |
| `Option[T]` con nichos sutiles | matriz de tests generada; si un caso no se puede garantizar, el motor devuelve `None` y la UI no muestra número |
| Rename en `std` | `std` es de solo lectura: se rechaza con mensaje claro |
| Coste de referencias en archivos grandes | índice de ocurrencias construido una vez por análisis |
| Duplicar lógica entre CLI y LSP | todo el cálculo vive en `pengu-layout`/`pengu-lsp`; la CLI solo formatea |
