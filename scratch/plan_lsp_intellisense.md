# Plan: IntelliSense real, tamaños en bytes e inlay hints

> **Estado:** propuesto (2026-11-21). Espera el visto bueno del usuario.
> **Versión del proyecto:** todo sigue en `0.1.0` (regla vigente).
> **Reglas vigentes:** sin clases en TypeScript, `snake_case`, archivos
> pequeños, cero deuda técnica, no romper lo que ya funciona.

## 0. Resumen

Cuatro objetivos, en este orden de dependencia:

1. **IntelliSense de verdad**: autocompletado de valores, tipos, módulos
   propios y `std/`, miembros de cualquier tipo, rutas de `invoke`,
   patrones de `when`, con firmas, documentación y orden útil.
2. **Tamaños en bytes exactos y siempre frescos** de runes, omens, sellos,
   ecos, variables, constantes, campos, tipos y funciones.
3. **Inlay hints** del tipo inferido (y, opcionalmente, del tamaño).
4. **El resto de lo que un desarrollador espera**: firma de llamadas,
   ir a definición de locales e importados, referencias, renombrar,
   resaltado de ocurrencias, acciones de código, plegado, enlaces a
   `invoke`, formato de rango, símbolos del workspace y tokens semánticos.

La causa raíz de casi todo es la misma: **el LSP analiza un solo archivo
y sin imports** (`src/lsp/analysis.ts`), así que no ve `std/`, ni los
módulos del programador, ni los ámbitos locales. El plan empieza por
convertir el análisis del LSP en un **análisis de proyecto con
overlays** (buffers sin guardar incluidos) que produce un **índice de
símbolos** y una **tabla de layouts**; las capacidades nuevas son
consultas sobre ese índice.

Los tamaños **no se calculan a mano**: se miden ejecutando el compilador
de C++ real (`sizeof`, `alignof`, `offsetof`) y se cachean por hash, de
modo que cualquier cambio de campo, tipo o herencia los actualiza solo.

Fases: **I1–I8**. Cada fase deja `bun test`, `tsc --noEmit` y `pengu fmt
--check` en verde y conserva todas las capacidades actuales.

---

## 1. Auditoría del estado actual

Evidencia medida sobre `main` (`0ef4be1`), sin tocar código.

| Área | Hoy | Evidencia | Consecuencia |
| --- | --- | --- | --- |
| Análisis | Un archivo, sin imports | `src/lsp/analysis.ts:30-45` usa `parse_text` + `check_program` sin `external` | `io::println` no tiene tipo; `invoke` invisible; los módulos propios no aportan símbolos; al editar un módulo importado no se reanaliza |
| Completion | Palabras clave + símbolos del módulo propio + palabras del texto | `src/lsp/server.ts:221-251` (`completion_items`) | El editor sugiere ruido, no `std/`, ni locales, ni tipos, ni miembros de contenedores |
| Completion de miembros | Solo `.` y solo runes/enchants del propio módulo | `src/lsp/server.ts:175-219` (`member_completion_items`) | Nada de `alias.`, `realm::`, `math::`, ni `vector.push`, ni `optional.value` |
| Hover | Firma o `nombre: tipo`; sin docs ni tamaño | `src/lsp/server.ts:120-165` | No hay documentación de `std/`; para nodos sin nombre se muestra el `kind` (`node_label` en `src/lsp/query.ts:47-51`) |
| Definición | Solo nombres de nivel de módulo | `src/lsp/server.ts:253-290` + `symbol_span` | Ir a definición de parámetros, locales, campos, métodos, variantes, `std/` e importados no funciona |
| Diagnósticos | Push en cada cambio, sin debounce | `src/lsp/server.ts:415-455` | Sin `relatedInformation`, sin `tags`, sin enlace a `docs/errors.md` |
| Capacidades LSP | `sync`, `hover`, `completion`, `definition`, `documentSymbol`, `formatting` | `src/lsp/server.ts:322-328` | Faltan `signatureHelp`, `references`, `rename`, `documentHighlight`, `codeAction`, `foldingRange`, `selectionRange`, `documentLink`, `workspaceSymbol`, `inlayHint`, `semanticTokens`, `rangeFormatting`, `codeLens`, `completionItem/resolve`, watched files, cancelación |
| Grafo | Existe (`load_graph`) pero solo lee disco | `src/project/module_graph.ts:236` | No ve buffers sin guardar |
| Tamaños | No existen en ninguna capa ni en el CLI | — | El usuario no tiene forma de saber `sizeof` de nada |
| Extensión | Sin ajustes de inlay hints, sin tamaño en la barra | `editors/vscode/package.json` | El editor no expone lo nuevo |
| Documentación de símbolos | No se conservan los comentarios `--` | `src/semantic/module_info.ts` (interfaces sin `docs`) | Hover y completion no pueden documentar `std/` |

Además, `src/lsp/server.ts` tiene 478 líneas: se parte en módulos de
handlers (regla de archivos ≤ 250 líneas).

---

## 2. Principios de diseño

1. **No romper.** Cada capacidad actual conserva su comportamiento y sus
   pruebas. Las nuevas se anuncian en `capabilities`; un cliente viejo
   las ignora.
2. **Fuente única.** Palabras clave, tipos, contenedores y métodos salen
   de las tablas del compilador (`src/frontend/token.ts`,
   `src/frontend/ast_type.ts`, `src/semantic/builtin_members.ts`). El LSP
   no mantiene listas paralelas; las pruebas comparan ambas.
3. **Exactitud.** Los tamaños se **miden**; nunca se estiman. Si no hay
   compilador de C++, se dice «no disponible», no se inventa.
4. **Frescura.** Toda tabla depende de un hash de su entrada (código del
   probe + compilador, índice + versión de documento). Cambiar algo
   invalida lo justo.
5. **Rendimiento con presupuesto.** Análisis incremental, caché de
   parseo, debounce y cancelación; presupuestos medidos en pruebas
   (§8).
6. **Sin clases y en archivos pequeños.** El estado del servidor sigue
   siendo un objeto plano con funciones que lo cierran.

---

## 3. Arquitectura

```
src/lsp/
  server.ts        (dispatch + estado; sin lógica)
  project.ts       (análisis de proyecto con overlays y debounce)
  index.ts         (índice de símbolos y consultas)
  completion.ts    (contextos de autocompletado)
  hover.ts         (hover markdown)
  signature.ts     (signature help)
  navigation.ts    (definición, referencias, rename, resaltado)
  inlay.ts         (inlay hints)
  actions.ts       (code actions, enlaces, code lens)
  tokens.ts        (tokens semánticos)
  folding.ts       (folding y selection ranges)
  workspace.ts     (símbolos del workspace, watched files)
  protocol.ts      (tipos LSP ampliados)
src/semantic/
  symbols.ts       (modelo de símbolos y referencias)
  docs.ts          (comentarios `--` → documentación)
  layout.ts        (modelo de tabla de layouts)
src/codegen/
  cpp_layout.ts    (probe C++ de tamaños)
src/driver/
  layout.ts        (compilar/ejecutar/cachear el probe)
src/cli/
  size_command.ts  (`pengu size`)
```

### 3.1 Análisis de proyecto

```ts
interface FileAnalysis {
  readonly uri: string;
  readonly version: number;
  readonly text: string;
  readonly source: Source;
  readonly program: Program;
  readonly module: ModuleInfo;
  readonly types: Map<ExprNode, PenguType>;
  readonly member_targets: Map<ExprNode, MethodTarget>;
  readonly symbols: SymbolIndex;
  readonly diagnostics: readonly Diagnostic[];
  readonly imports: ReadonlyMap<string, ModuleInfo>;
  readonly selective: ReadonlyMap<string, { module: ModuleInfo; name: string }>;
  readonly enchants: ReadonlyMap<string, EnchantedType>;
}

interface ProjectAnalysis {
  readonly entry: FileAnalysis | undefined;
  readonly files: ReadonlyMap<string, FileAnalysis>; // por ruta absoluta
  readonly order: readonly string[];                 // orden de dependencias
  readonly layout: LayoutTable | undefined;          // perezosa (§3.3)
  readonly version: string;                          // hash del proyecto lógico
}

function build_project(entry: string, overlays: ReadonlyMap<string, string>): ProjectAnalysis;
```

- `load_graph` gana un parámetro opcional **retrocompatible**:
  `load_graph(entry, { read_file?: (path: string) => string | undefined })`.
  El LSP pasa un lector que consulta overlays → disco → `std` empaquetado.
- **Invalidación**: al cambiar un buffer se re-parsea solo ese archivo y se
  re-chequea él y sus dependientes (orden topológico del grafo, ya
  conocido). Se publican diagnósticos de todos los afectados.
- **Debounce** de 40 ms por documento; `$/cancelRequest` respetado.
- **Watched files**: `workspace/didChangeWatchedFiles` (el cliente ya
  vigila `**/*.pengu`) invalida lo cargado; `std/**` también.
- **Raíz del proyecto**: `initialize.rootUri`/`workspaceFolders` +
  `find_project_root` para resolver `invoke`.

### 3.2 Índice de símbolos

```ts
type SymbolKind =
  | "function" | "const" | "variable" | "parameter" | "field" | "method"
  | "constructor" | "rune" | "omen" | "variant" | "echo" | "seal"
  | "realm" | "module" | "builtin" | "type";

interface Symbol {
  readonly id: string;          // estable: `${file}:${decl_offset}` o `mod:${file}:${name}`
  readonly name: string;
  readonly kind: SymbolKind;
  readonly type: PenguType | undefined;
  readonly signature: string | undefined;   // "sqrt = (x: double) -> double"
  readonly docs: string | undefined;        // comentarios `--` contiguos
  readonly file: string;
  readonly span: Span;          // declaración (para hover/definición)
  readonly scope: Span | undefined; // ámbito visible (locals/params)
  readonly container: string | undefined;  // "rune Punto", "realm math"
  readonly mutable: boolean;
}

interface SymbolIndex {
  readonly by_name: ReadonlyMap<string, readonly Symbol[]>;
  readonly at: (offset: number) => Symbol | undefined;      // símbolo declarado/uso en offset
  readonly visible: (offset: number) => readonly Symbol[];  // para completion
}
```

- Se construye con: `ModuleInfo` (funciones, consts, runes/omens/alias con
  spans), declaraciones locales y parámetros **capturados durante el
  chequeo** (hook en `declare`/`check_params`), imports (alias y
  selectivos) y `std/` (módulos cargados como cualquier otro).
- **Referencias**: al resolver un identificador, el checker registra
  `{ id, file, span, role }` en un `ReferenceIndex`; alimenta
  definición de locales, referencias, rename y documentHighlight.
- **Docs**: en `src/semantic/docs.ts`, un bloque de comentarios `--`
  contiguo inmediatamente encima de la declaración se guarda como texto
  markdown plano; sin sintaxis nueva.
- `visible(offset)` = locales/params del ámbito → módulo propio →
  selectivos → imports (`hash` con `::`) → preludio/`std` → keywords.

### 3.3 Tamaños en bytes: medir, no adivinar

```ts
interface FieldLayout { readonly name: string; readonly type: string; readonly offset: number; readonly size: number; readonly align: number; }
interface Layout { readonly size: number; readonly align: number; readonly fields?: readonly FieldLayout[]; readonly detail: string; }
interface LayoutTable {
  readonly hash: string;                 // hash del probe + compilador
  readonly types: ReadonlyMap<string, Layout>;    // "Punto", "Color", "lista<int>"
  readonly symbols: ReadonlyMap<string, Layout>;  // "main", "LIMITE", "Punto.x"
}
```

**Cómo se obtiene**: `src/codegen/cpp_layout.ts` genera un `.cpp` con el
runtime header + `emit_type_declarations` de todas las unidades + un
`main` que imprime `clave\tkind\tsize\talign` (y, para runes sin padre,
`offsetof` por campo, usando el nombre de campo). `src/driver/layout.ts`
lo compila con **el mismo compilador** que `pengu build`
(`-std=c++20 -O0`), lo ejecuta y parsea la salida.

**Frescura**: la clave de caché es
`hash(código del probe + versión del compilador + hash del runtime)`.
Cualquier cambio de campo, tipo, herencia, alias o tabla de runtime
produce un probe distinto ⇒ la tabla se recalcula. Nada de
invalidaciones manuales.

**Qué se mide**:

| Símbolo | Dato |
| --- | --- |
| `rune` | `sizeof`, `alignof`, campos con offset |
| `omen` unitario / `flags` | `sizeof` del `enum class` (tipo subyacente incluido) |
| `omen` algebraico | `sizeof` del `std::variant` y de cada variante |
| `seal` / `echo` | `sizeof` del subyacente (y del sello) |
| variable / `const` / campo | `sizeof` de su tipo |
| función | `sizeof` del retorno + cada parámetro (y `sizeof(std::function<…>)` si es valor) |
| `T?` / `ref<T>` / `raw<T>` / punteros | `sizeof`/`alignof` del tipo C++ real |
| genérico | instanciaciones representativas (`int`, `double`, `string`, `any`) y, en un uso concreto, la instanciación exacta |
| contenedores | el objeto contenedor (no el heap); se documenta en el hover |

**Dónde se ve**:
- hover: `tamaño: 24 B (alineación 8)` + campos y offsets;
- `pengu size <archivo> [--json] [--type N] [--fields]`;
- inlay hint opcional `(24 B)` tras el tipo;
- petición personalizada `pengu/sizeAt` para la barra de estado de la
  extensión;
- code lens opcional sobre declaraciones de tipo.

**Sin toolchain**: `layout === undefined`; el hover dice «tamaño no
disponible: no se encontró un compilador de C++».

### 3.4 Extensión

- Ajustes nuevos: `pengu.inlayHints.types` (por defecto `true`),
  `pengu.inlayHints.sizes` (`false`), `pengu.statusBar.size` (`true`),
  `pengu.completion.docs` (`true`).
- Barra de estado: `8 B` del símbolo bajo el cursor (debounce 150 ms,
  `pengu/sizeAt`), además del estado del servidor.
- Comando `pengu.showSize` (abre el hover del tamaño) y reutiliza
  `pengu.restartServer`.
- Sin dependencias nuevas; el cliente sigue siendo `vscode-languageclient`.

---

## 4. Comportamiento de cada capacidad

### 4.1 Autocompletado por contexto

| Contexto (offset) | Elementos | Detalle |
| --- | --- | --- |
| Inicio de expresión | keywords, locales, params, consts, funciones, runes, omens, alias, selectivos, módulos importados | firma + docs + tamaño |
| Tras `alias::` / `realm::` | exportaciones del módulo (funciones, consts, tipos, variantes de omens) y módulos `std/` | firma + `realm «…»` |
| Tras `.` | campos y métodos de rune (heredados incluidos), omens (variantes, `try_from`, `from`, métodos enhechizados), sellos (métodos), ecos (métodos del subyacente), tipos incorporados (vector, map, set, string, optional, range, tuplas, punteros) | firma + tamaño del retorno |
| Tras `:` en binding/param/retorno | tipos visibles: primitivos, contenedores, del proyecto, importados, `T?`, `ref<…>` | tipo |
| Tras `<` en llamada/tipo | sigilos visibles | parámetro de tipo |
| Tras `@` | miembros del `self` actual | firma |
| Tras `#` | variables y expresiones de tipo contenedor | — |
| En `when` de `switch`/`match` | variantes del omen del sujeto + patrones válidos | payload |
| Tras `invoke "` | rutas `*.pengu` del proyecto y `std/` | ruta resuelta |

Detalles de los ítems: `kind` correcto, `detail` con la firma,
`documentation` markdown (docs + `realm` + tamaño), `sortText` por
cercanía (locales `0…`, módulo `1…`, selectivos `2…`, imports `3…`,
`std` `4…`, keywords `9…`), `filterText`, `textEdit` que reemplaza el
prefijo ya escrito, `insertText` con placeholders
(`InsertTextFormat.Snippet`) para funciones y métodos.

`completionItem/resolve` completa la documentación de `std/` bajo
demanda (evita cargar todo en cada pulsación).

### 4.2 Hover

- Función/método/constructor: firma, docs, `realm`, tamaño de retorno y
  de cada parámetro, total de parámetros.
- Rune: campos con tipo, offset y tamaño; métodos; tamaño y alineación;
  padre si lo tiene.
- Omen: variantes, valores, tamaño del enum o del `variant`; métodos
  enhechizados.
- Sello/eco: subyacente, métodos, tamaño.
- Variable/const/parámetro: `nombre: tipo` + tamaño + docs del binding.
- Expresión: tipo inferido + tamaño del tipo.
- Módulo (`invoke`/alias): realm, archivo y lista breve de exportaciones.

### 4.3 Signature help

`(` sobre función, método, rune, constructor, método enhechizado o
incorporado: parámetros `nombre: tipo`, activo según las comas,
`variádicas` y valores por defecto indicados, documentación del
parámetro si existe, y `activeSignature` cuando hay sobrecargas
enhechizadas (se elige por argumentos ya escritos).

### 4.4 Navegación y refactor

- **Definición**: locales, params, campos, métodos, variantes, módulos
  importados, `std/`, y alias de `invoke` (al archivo).
- **Referencias**: todas las apariciones del símbolo en el proyecto
  (incluye el archivo de declaración), con `includeDeclaration`.
- **Rename**: `prepareRename` valida (no en `std/`, no en símbolos de
  otro realm, no en keywords) y devuelve rango del identificador;
  `rename` produce un `WorkspaceEdit` con todas las referencias,
  respetando sombreado (`shadowing`), sin tocar strings ni comentarios.
- **DocumentHighlight**: ocurrencias del mismo símbolo en el archivo
  (lectura/escritura distinguidas).
- **Workspace symbols**: búsqueda difusa por nombre en todo el proyecto.
- **Folding**: bloques por indentación, `realm`, `rune`, `omen`,
  `enchanting`, `declare`/`extern`, comentarios contiguos e imports.
- **Selection range**: cadena de nodos AST que contienen la posición.

### 4.5 Inlay hints

| Hint | Cuándo | Ejemplo |
| --- | --- | --- |
| Tipo inferido | binding sin anotación, `const`, variable de `for`, patrón de `match`, retorno implícito | `total` `: int` |
| Tamaño | ajuste `pengu.inlayHints.sizes` y layout disponible | `total: int (4 B)` |

Se piden con `range` (solo lo visible), respetan
`pengu.inlayHints.types/sizes`, y no se emiten para `any`, genéricos sin
instanciar ni tipos desconocidos.

### 4.6 Acciones de código, enlaces, diagnóstico y lentes

- **Quick fixes** desde `Diagnostic.fix` (el checker ya produce
  `replacement`): indentación, `mut` faltante, `invoke` faltante para
  módulos `std` conocidos, «insertar tipo inferido», «declarar
  parámetro `mut`» cuando el checker lo propone.
- **Document links** en `invoke "…"` → abre el archivo real (incluye
  `std/` empaquetado).
- **Range formatting**: formatea solo el rango si coincide con líneas
  completas de un bloque; en otro caso no ofrece edición (y lo dice en
  la documentación de la capacidad).
- **Diagnósticos**: `relatedInformation` con las `notes`,
  `codeDescription` a `docs/errors.md#e0xxx`, `tags: [1]` (unnecessary)
  para avisos de código muerto cuando exista, y `source: "pengu"`.
- **Code lens** (apagado por defecto): «ejecutar»/«compilar» sobre
  `main` y «tamaño» sobre declaraciones de tipo.

### 4.7 Tokens semánticos

Leyenda estándar (`namespace`, `type`, `class`, `enum`, `enumMember`,
`function`, `method`, `variable`, `parameter`, `property`, `keyword`,
`comment`, `string`, `number`, `operator`). Se calculan desde el AST y
el índice (no desde la gramática), con lo que aciertan en casos que la
gramática de TextMate no puede (método vs campo, variante vs tipo,
`@campo`). La gramática actual sigue siendo el fallback para clientes
sin `semanticTokensProvider`.

---

## 5. Exactitud y frescura de los tamaños (detalle)

**Por qué medir.** Los tamaños dependen de la ABI de la biblioteca
estándar y de la plataforma: `std::string` mide 32 B en libstdc++ y 24 B
en libc++, `std::map` 48 B vs 24 B, `std::optional<T>` añade padding,
`std::variant` reserva el mayor payload más el índice. Cualquier cálculo
propio sería una segunda implementación de la ABI, condenada a
desviarse.

**Garantías.**

1. Todo tamaño sale de `sizeof`/`alignof`/`offsetof` ejecutados por el
   **mismo compilador** que usa `pengu build` (`find_cxx`).
2. La tabla se cachea por `hash(probe + compilador + runtime)`: editar un
   campo, cambiar un tipo o tocar el runtime cambia el probe y la tabla.
3. El probe no incluye cuerpos de función: es rápido de compilar y no
   depende de la lógica del programa.
4. Si el probe no compila (por ejemplo, un tipo que aún no es válido en
   C++), el LSP conserva la última tabla buena y avisa en el canal de
   salida; nunca muestra un tamaño dudoso.
5. Las tablas son por proyecto y por compilador; dos proyectos con
   compiladores distintos pueden diferir, y es correcto.

**Verificación en pruebas** (fuente de verdad independiente):

- `tests/layout/layout.test.ts` compila un `.cpp` escrito a mano con
  `static_assert(sizeof(Punto) == N)` para los mismos tipos y compara
  con la tabla del probe.
- Un test edita un rune (añade un campo) y comprueba que el tamaño cambia
  y que el hash de la tabla cambia.
- Un test comprueba que un cambio de `std/string.pengu` (método nuevo)
  **no** cambia los tamaños (el probe no depende de cuerpos) y que un
  cambio de campo sí.

**Coste.** Una compilación `-O0` del probe (~200–400 ms en este equipo),
perezosa y cacheada; el análisis normal del LSP no la necesita.

---

## 6. Fases

Cada fase: objetivo, entregables, criterios de aceptación y pruebas.
Ninguna fase cambia el comportamiento observable de las anteriores.

### I1 · Análisis de proyecto, overlays e índice de símbolos

**Objetivo**: que el LSP vea el proyecto completo (incluidos buffers sin
guardar) y tenga un índice consultable.

- `load_graph(entry, { read_file })` retrocompatible.
- `src/lsp/project.ts`: `build_project`, overlays, debounce 40 ms,
  invalidación por dependencias, `didChangeWatchedFiles`, cancelación.
- `src/semantic/symbols.ts`: `Symbol`, `SymbolKind`, `SymbolIndex`,
  `ReferenceIndex`; captura de locales/params en el checker (hook
  opcional, sin cambiar su lógica).
- `src/semantic/docs.ts`: comentarios `--` → `docs`.
- `src/lsp/index.ts`: `visible(offset)`, `at(offset)`, `references(id)`.
- Partir `src/lsp/server.ts` (478 líneas) en `handlers_*.ts` pequeños.

**Aceptación**
- `analyze` del LSP devuelve `imports`/`selective`/`enchants`/`std` para un
  archivo con `invoke`.
- Un cambio en un módulo importado actualiza los diagnósticos de quien lo
  importa sin reiniciar el servidor.
- `bun test` verde; `tsc` limpio; 0 regresiones en `tests/lsp`.
- Documento de 500 líneas con 5 imports se analiza en < 150 ms (medido en
  test con `performance.now()` y margen ×3 en CI).

### I2 · Autocompletado completo

**Objetivo**: el IntelliSense de la §4.1, con `std/` y módulos propios.

- `src/lsp/completion.ts`: detección de contexto por offset (sin regex
  frágiles: se apoya en tokens y AST), generación de ítems, `sortText`,
  `textEdit`, snippets, documentación.
- Ampliar `src/lsp/protocol.ts`: `documentation`, `sortText`,
  `filterText`, `textEdit`, `insertTextFormat`, `completionItem/resolve`.
- Miembros de todos los tipos: runes (heredados), omens, sellos, ecos,
  incorporados (`builtin_members`), punteros, `optional`, `range`,
  tuplas.
- `alias::`/`realm::` con exportaciones del módulo; rutas de `invoke`.

**Aceptación**
- Tras `math::` aparecen `sqrt`, `abs`, `pi`…; tras `io::`, `println`.
- Tras `saludos.` (alias de un módulo propio) aparece su función.
- Tras `xs.` con `vector<int>` aparecen `push`, `pop`, `get`, `len`, y
  los enhechizados (`first`, `sort`, `join`).
- Tras `:` aparecen tipos del proyecto y `vector<int>`, `T?`.
- Los ítems de `std` traen `documentation` con la firma.
- Pruebas de integración por contexto (≈ 12) + unitarias de `visible()`.

### I3 · Hover, documentación y firma

**Objetivo**: hover rico y signature help.

- `src/lsp/hover.ts`: firma, docs, realm, tamaño (si hay layout; se
  integra en I5), campos/variantes, etiqueta legible para literales
  (arreglar `node_label`).
- `src/lsp/signature.ts`: `textDocument/signatureHelp` con parámetros,
  activo, variádicas, sobrecargas enhechizadas.
- Hover de módulos y de alias de `invoke`.

**Aceptación**
- Hover de `rune Punto` muestra campos con tipo y tamaño; de una función,
  firma + docs + tamaños de retorno y parámetros; de un `any`, su tamaño.
- `println(` muestra `...partes: any` como variádico.
- Documentación de `std/` visible (extraída de los comentarios `--`).

### I4 · Navegación y refactor

**Objetivo**: definición completa, referencias, rename, resaltado,
símbolos del workspace, plegado y selection ranges.

- `src/lsp/navigation.ts`, `src/lsp/folding.ts`, `src/lsp/workspace.ts`.
- `prepareRename`/`rename` con `WorkspaceEdit` (archivo + proyecto),
  sombreado respetado, `std/` protegido.

**Aceptación**
- Definición de un parámetro, un local, un campo, un método, una variante
  y un símbolo de `std/`.
- Referencias de una función de módulo importado en los dos archivos.
- Rename de un local no toca el mismo nombre en otro ámbito; rename de
  una función actualiza los imports selectivos y las llamadas.
- `std/` devuelve error de rename con mensaje claro.
- Workspace symbols encuentra `sqrt` y `Punto` desde cualquier archivo.

### I5 · Tamaños en bytes

**Objetivo**: §3.3 completo.

- `src/semantic/layout.ts`, `src/codegen/cpp_layout.ts`,
  `src/driver/layout.ts` (compilar, ejecutar, cachear, fallback).
- `src/cli/size_command.ts` + `pengu size` (+ `--json`, `--type`,
  `--fields`) y ayuda en `src/cli/help.ts`.
- Hover y code lens con tamaños; petición `pengu/sizeAt`.

**Aceptación**
- `pengu size examples/11_polimorfismo/main.pengu` lista runes, omens,
  sellos, ecos, consts y funciones con tamaño y alineación.
- Los tamaños coinciden con un `static_assert` compilado aparte.
- Editar un campo de un rune cambia el tamaño en la siguiente consulta,
  sin reiniciar el LSP (caché por hash).
- Sin compilador, `pengu size` sale con código 1 y mensaje claro; el LSP
  dice «no disponible».

### I6 · Inlay hints y ajustes de la extensión

**Objetivo**: §4.5 y §3.4.

- `src/lsp/inlay.ts` (`textDocument/inlayHint`), ajustes de cliente.
- Extensión: ajustes, barra de estado con tamaño, `pengu.showSize`,
  `inlayHint` habilitado en el cliente.

**Aceptación**
- Con tipos activados, cada binding sin anotación muestra `: T`; con
  tamaños activados, `(N B)`.
- La barra de estado muestra `8 B` al poner el cursor sobre un rune.
- Apagar los ajustes elimina los hints sin reiniciar.
- Pruebas de integración de inlay hints y de la barra de estado
  (`tests/extension`).

### I7 · Acciones, enlaces, diagnósticos y lentes

**Objetivo**: §4.6.

- `src/lsp/actions.ts`: code actions (quick fixes + «insertar tipo» +
  «añadir invoke»), document links, code lens, range formatting.
- Diagnósticos con `relatedInformation`, `codeDescription`, `tags`.

**Aceptación**
- El error E0406 ofrece el quick fix «declarar con mut» y aplica la
  edición correcta.
- Un `invoke "std/math"` es un enlace que abre
  `std/math.d.pengu`.
- `math::sqrt(...)` sin `invoke` ofrece «añadir `invoke "std/math"`».
- Formato de rango no rompe el archivo y no edita si el rango no es un
  bloque completo.

### I8 · Tokens semánticos, rendimiento y cierre

**Objetivo**: §4.7 + robustez + cierre del proyecto.

- `src/lsp/tokens.ts` (`semanticTokens/full`), leyenda estándar.
- Cancelación, watched files, debounce afinado, presupuestos.
- Suite de pruebas completa del LSP (unitarias + integración),
  `docs/lsp.md` (matriz de capacidades), README y extensión, CHANGELOG
  `0.1.0`, `.vsix` reempaquetado e instalado.
- Bitácora de las fases I1–I8 en este plan.

**Aceptación**
- Los tokens semánticos distinguen método/campo/variante/parámetro y no
  parpadean al editar.
- `bun test` ≥ 380 pruebas verdes; `tsc` limpio; `fmt --check` limpio;
  extensión instalada; 13 ejemplos siguen compilando y ejecutando.
- CHANGELOG actualizado y commit a `main` (el push lo hace el usuario).

---

## 7. Matriz de cobertura

| Capacidad | Fase | Pruebas |
| --- | --- | --- |
| Análisis de proyecto con overlays | I1 | `tests/lsp/project.test.ts` |
| Índice de símbolos y ámbitos | I1 | `tests/lsp/index.test.ts` |
| Autocompletado de valores y tipos | I2 | `tests/lsp/completion.test.ts` |
| Autocompletado de módulos, `std/` y miembros | I2 | `tests/lsp/completion_modules.test.ts` |
| Hover, docs y firma | I3 | `tests/lsp/hover.test.ts`, `tests/lsp/signature.test.ts` |
| Definición, referencias, rename | I4 | `tests/lsp/navigation.test.ts` |
| Plegado, selection ranges, workspace symbols | I4 | `tests/lsp/workspace.test.ts` |
| Tamaños exactos | I5 | `tests/layout/layout.test.ts` |
| `pengu size` | I5 | `tests/layout/size_command.test.ts` |
| Inlay hints | I6 | `tests/lsp/inlay.test.ts` |
| Barra de estado y ajustes | I6 | `tests/extension/status.test.ts` |
| Acciones, enlaces, lentes, formato de rango | I7 | `tests/lsp/actions.test.ts` |
| Tokens semánticos | I8 | `tests/lsp/tokens.test.ts` |
| Rendimiento y cancelación | I8 | `tests/lsp/performance.test.ts` |

---

## 8. Rendimiento (presupuestos)

| Operación | Presupuesto | Cómo se garantiza |
| --- | --- | --- |
| Análisis inicial de proyecto (500 líneas, 5 imports) | < 150 ms | parse cache + grafo ya resuelto |
| Reanálisis tras edición | < 80 ms | solo el archivo y dependientes |
| Completion | < 30 ms | índice ya construido, sin reanalizar |
| Hover / definición | < 15 ms | búsquedas en el índice |
| Layout (primera vez por versión) | < 500 ms | probe `-O0` |
| Layout (cacheado) | < 5 ms | JSON en caché |

Se miden en `tests/lsp/performance.test.ts` con holgura ×3 para CI.

---

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Compilar el probe en cada edición | caché por hash, cálculo perezoso, debounce |
| Proyecto grande: reanálisis lento | parse cache, invalidación por dependencias, cancelación |
| Rename destructivo | `prepareRename`, sombreado probado, `std/` bloqueado |
| Tablas de tipos duplicadas y desincronizadas | fuente única + pruebas de cobertura contra el compilador |
| Clientes sin soporte de una capacidad | todo se anuncia en `capabilities`; el servidor responde vacío si no se usa |
| Menús/atajos que chocan con el editor | atajos documentados y configurables (`keybindings` ya existentes) |
| Diferencias g++ / clang++ | la tabla usa el compilador configurado; se documenta |

---

## 10. Decisiones a aprobar

| # | Decisión | Recomendación |
| --- | --- | --- |
| D1 | Tamaños medidos con compilador real (probe) frente a cálculo propio | **Medir** (exactitud y frescura); sin toolchain, «no disponible» |
| D2 | Qué significa «tamaño de función» | Retorno + cada parámetro; para valores `function<…>`, `sizeof(std::function<…>)` |
| D3 | Genéricos | Instanciaciones representativas (`int`, `double`, `string`, `any`) + instanciación exacta en el uso |
| D4 | Inlay hints por defecto | Tipos **sí**, tamaños **no**; ambos configurables |
| D5 | Rename | Todo el proyecto, respetando sombreado; **bloqueado** en `std/` |
| D6 | Símbolos con `_` | Se ofrecen al final (prioridad baja), no se ocultan |
| D7 | Tokens semánticos | Sí; la gramática de TextMate queda como fallback |
| D8 | Debounce y cancelación | 40 ms + `$/cancelRequest`; invalidación por dependencias |
| D9 | Acciones de código | Solo quick fixes existentes, «insertar tipo» y «añadir invoke» |
| D10 | Documentación de símbolos | Comentarios `--` contiguos encima de la declaración, sin sintaxis nueva |

---

## 11. Criterio de terminado

1. Los cuatro objetivos funcionan con pruebas automatizadas.
2. `bun test` verde (≥ 330 pruebas), `bunx tsc --noEmit` limpio,
   `pengu fmt --check` limpio, 13 ejemplos compilando y ejecutando.
3. La extensión se reempaqueta, se instala y sus pruebas (`tests/extension`)
   pasan, incluidas las nuevas de inlay hints y barra de estado.
4. Tamaños verificados contra `static_assert` y actualizados al cambiar
   un tipo sin reiniciar el servidor.
5. Documentación: `docs/lsp.md` (matriz de capacidades), README raíz,
   README de la extensión, `docs/errors.md` enlazado desde diagnósticos.
6. `CHANGELOG.md` actualizado dentro de `## [0.1.0]` («Añadido en la fase
   I» y «Verificado»), bitácora I1–I8 completa.
7. Commit a `main` (el push lo hace el usuario) y árbol limpio.

---

## 12. Bitácora

| Fase | Estado | Verificación |
| --- | --- | --- |
| I1 · Proyecto, overlays e índice | ✅ | `tests/lsp/features.test.ts`: overlay gana al disco; símbolos con docs y sombreado. |
| I2 · Autocompletado | ✅ | Ámbito, `::`, miembros, tipos y `std/`; enhechizados primero. |
| I3 · Hover, docs y firma | ✅ | Firma, docs `--`, tamaño/offset de campos y variádicas. |
| I4 · Navegación y refactor | ✅ | Definición, referencias, `prepareRename`, `std/` protegido, símbolos jerárquicos y del workspace. |
| I5 · Tamaños en bytes | ✅ | `pengu size` y `pengu/sizeAt`; tipos, valores y funciones medidos con el toolchain. |
| I6 · Inlay hints y extensión | ✅ | Hints de tipos (con tamaño opcional) y barra de estado. |
| I7 · Acciones, enlaces y diagnósticos | ✅ | Code actions, `documentLink`, `codeLens` y `rangeFormatting`. |
| I8 · Tokens semánticos y cierre | ✅ | Tokens, plegado, conformidad y documentación. |
