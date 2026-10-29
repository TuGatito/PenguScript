# Auditoría del LSP y de la extensión VS Code de PenguScript

> **Estado:** auditoría original; implementación completada en esta rama.
> **Actualización 2026-10-29:** implementado en `0.15.0` (extensión 4.0.0); el plan de este documento se usó como guía. Ver `CHANGELOG.md`.
> **Fecha:** 2026-10-28
> **Repositorio:** `TuGatito/PenguScript`, commit `c061455` (`0.14.7`, extensión `3.2.0`).
> **Alcance:** servidor `psc lsp`, capa semántica que lo alimenta, extensión `vscode-extension`, gramática TextMate, `language-configuration.json`, snippets, empaquetado y pruebas.

---

## 0. Resumen ejecutivo

El LSP actual **no es un LSP semántico**: es un servidor de diagnóstico más un conjunto de heurísticas de texto. No consume el AST, los tipos, los símbolos ni los comentarios de documentación que el compilador ya construye. Eso explica la mayor parte de los síntomas reportados.

La extensión tampoco está “rota” de forma independiente: su gramática y sus snippets están desactualizados, pero el daño visual más grave lo produce el propio LSP al publicar **semantic tokens incorrectos** que pisan los colores de TextMate (`set`, `string`, `int`, `Persona` se clasifican como `variable`).

Además hay dos fallos de estabilidad/infraestructura que no se ven en la captura pero son críticos:

1. **Fuga de memoria del LSP:** cada `didChange` crea un `SemaResult` completo y nunca lo libera. Medido: **16 MB → 413 MB en 30 cambios**.
2. **Resolución de `std` rota fuera del checkout:** el LSP solo encuentra la stdlib si el proceso arranca con `cwd` en un directorio que tenga `std/`. En un proyecto normal o en una instalación release (`bin/psc` + `std/` al lado) no la encuentra.

**Veredicto:** no conviene “parchear” los síntomas uno por uno. Hay que:

1. arreglar la resolución de `std` y la propiedad de memoria;
2. exponer una capa de consulta semántica reutilizable (`SemaQuery`);
3. reescribir las features del LSP sobre esa capa;
4. actualizar gramática, snippets y manifiesto de la extensión;
5. añadir pruebas de protocolo LSP y de la extensión al CI.

Sin los pasos 2–3, cualquier arreglo de hover/completion/inlay hints será otra heurística que volverá a fallar.

---

## 1. Metodología y evidencia

Se hizo inspección estática del repositorio y **pruebas de protocolo reales** contra `build/psc lsp --stdio` (cliente JSON-RPC propio sobre stdio), además de ejecutar `psc check`, `psc doc`, `psc fmt` y `vsce package`.

No se dispone de una instancia de VS Code en este entorno, así que los defectos de UI se han inferido del manifiesto, del código TypeScript, de la gramática y de las capturas aportadas. Los defectos del LSP sí están reproducidos con el binario actual.

### 1.1 Reproducciones clave

| Síntoma del usuario | Reproducción | Resultado |
|---|---|---|
| `import std.spark` no resuelve | `psc check` sobre un archivo fuera del checkout | `E0004: cannot resolve imported module 'std.spark'` |
| `std.arcivum` no resuelve | No existe `std/arcivum.pengu`; el módulo real es `std/archivum.pengu` | Es un typo probable; el LSP no sugiere el nombre correcto |
| Hint `int` para `let b is ruta` | `textDocument/inlayHint` | Devuelve `: int` en `let b as string is ruta` |
| Hint duplicado `string: string` | Hint + anotación explícita | El hint se inserta aunque ya haya `as Type`; queda `let ruta: string as string` |
| Sin autocompletado de `std.` | `textDocument/completion` tras `import std.` | Lista palabras del documento (`Documentaci`, `n`, `30`…), ningún módulo `std.*` |
| `psc.run` no encontrado | `textDocument/codeLens` | Devuelve `{"title":"Run","command":"psc.run"}`; la extensión registra `pengus.run` |
| `set`/tipos sin iluminar | `textDocument/semanticTokens/full` | `set`, `string`, `int`, `Persona`, `suma` se emiten como `variable` |
| `##`/`#` no detectados | Hover y `psc doc` | Hover no usa docs; `psc doc` genera docs vacías y aborta en `std/archivum` |
| `with` sin tipo | `textDocument/inlayHint` | No emite hint para `var p as Persona with:` |
| Memoria | 30 `didChange` seguidos | RSS 16 MB → 413 MB |
| VSIX | `vsce package` | 326 archivos, 3,58 MB, icono de 3 MB, `node_modules` incluido |

### 1.2 Comandos usados (resumen)

```bash
# Resolución de std fuera del checkout
build/psc check /tmp/pengu-audit/sample.pengu --diagnostics=plain
# -> E0004 cannot resolve imported module 'std.spark'

# Inferencia real del compilador (correcta)
build/psc check /tmp/pengu-audit/sample_infer.pengu --diagnostics=plain
# -> E0005 expected 'int', got 'string'  (prueba de que `let b is ruta` SÍ infiere string)

# LSP
python3 /tmp/pengu-audit/lsp_probe4.py
# hover ruta -> "**ruta**"
# inlay -> [{"label":": string"}, {"label":": int"}]
# completion -> ["Documentaci","n","30",...] sin std.*

# Semántica
python3 /tmp/pengu-audit/sem_decode.py
# set -> variable; string -> variable; Persona -> variable

# Memoria
python3 /tmp/pengu-audit/lsp_leak.py
# 0: 29048 KB, 10: 157068 KB, 20: 285124 KB, 30: 413088 KB

# Documentación
build/psc doc --output=docs
# docs vacías; en std/archivum: "double free or corruption (out)"
```

---

## 2. Mapa síntoma → causa raíz

| # | Síntoma reportado | Causa(s) principal(es) | IDs |
|---|---|---|---|
| 1 | `cannot resolve imported module 'std.arcivum'` / `std.spark` | `SemaOptions.std_dirs` no busca `<proyecto>/std`, ni `<exe>/../std`, ni `PENGU_STD_DIR`; el LSP arranca con cwd ajeno al proyecto | SEMA-01, SEMA-03 |
| 2 | No autocompleta `import std.` | `completionProvider` sin `triggerCharacters`; completion léxica sin módulos ni símbolos | LSP-03, LSP-13 |
| 3 | El hint dice `int: int` / `string: string` | Inlay hint heurístico: no usa el tipo semántico, no respeta anotaciones explícitas | LSP-02 |
| 4 | `command 'psc.run' not found` | El LSP emite `psc.run`/`psc.test`; la extensión registra `pengus.run`/`pengus.test` | LSP-07, EXT-01 |
| 5 | No detecta documentación `##`/`#` | `collect_weave` no llama a `tag_decl`; hover no lee docs; `psc doc` tiene un pipeline roto | SEMA-02, DOC-01, LSP-04 |
| 6 | `let b is ruta` muestra `int` | Inlay hint mira el primer carácter de `ruta` y asume `int`; el compilador sí infiere `string` | LSP-02 |
| 7 | Sin autocompletado de tipos | Completion no consulta símbolos/tipos; solo escanea palabras del texto | LSP-03 |
| 8 | `with` no marca tipo | Inlay hint no entiende `NdWithInitExpr`; no hay consulta semántica | LSP-02 |
| 9 | `set` y tipos mal iluminados | Semantic tokens incompletos y erróneos; pisan TextMate | LSP-05, GRAM-01 |
| 10 | “Ni snippets tiene” | El VSIX actual sí incluye `snippets/pengus.json`; si no aparecen es versión vieja/ID de lenguaje, pero varios snippets son inválidos y no hay pruebas | EXT-05, TEST-01 |
| 11 | “Run | Run” duplicado | No reproducible con el binario actual (devuelve un solo lens); probable cliente/binario viejo o dos clientes. Hay que garantizar instancia única y versión compatible | LSP-07, EXT-01 |

---

## 3. Hallazgos detallados

### 3.1 Bloqueantes

#### SEMA-01 — La resolución de la stdlib está mal y no cubre una instalación release

**Severidad:** bloqueante.

`src/psc/sema/api.pengu:87-96` calcula:

```pengu
var parent as string is calling compass.cp_dirname with opts->base_dir
...
var std_path as string is calling compass.cp_join with parts   # parent/std
```

Es decir, para un proyecto en `/home/u/mi_proyecto` busca `/home/u/std`, **no** `/home/u/mi_proyecto/std`. Después añade `"std"` relativo al `cwd` del proceso, que es lo único que hace funcionar `psc check` cuando se ejecuta desde la raíz del checkout.

No se consultan:

- `PENGU_STD_DIR` (que sí usa `src/psc/driver/paths.pengu:112,210`);
- `<exe>/../std` (layout portable `bin/psc` + `std/`);
- `<exe>/../share/pengu/std` (layout FHS);
- `$PENGU_HOME/std`;
- el `std/` del proyecto de forma explícita.

**Impacto:** cualquier proyecto normal, y cualquier instalación release usada desde VS Code, falla al importar `std.*`. Es la causa directa de la captura.

**Solución:** extraer un único `resolve_std_dirs(base_dir, exe_path, env)` y usarlo desde `sema_api`, `driver/paths` y el LSP. Orden propuesto en §5.2.

---

#### LSP-01 — Fuga de memoria en cada cambio de documento

**Severidad:** bloqueante.

`src/psc/lsp/server.pengu:180-205`:

```pengu
var sr as sema_api.SemaResult is calling sema_api.check_text with path, text, opts
...
var jtext as string is calling sr.program->diagnostics.render_json_utf16
```

Nunca se llama a `sema_api.free_result`. Tampoco se libera `opts` (`sopts.default_options` es owned). Cada tecla filtra el `SemaProgram` completo y todos los módulos importados.

Medición real con `std.archivum` y 30 `didChange`:

```text
initial 16 MB
 0   29 MB
 5   93 MB
10  157 MB
15  221 MB
20  285 MB
25  349 MB
30  413 MB
```

**Impacto:** OOM/cuelgue en sesiones largas, especialmente con varios `std.*`. Es un blocker de producción, no una mejora.

**Solución:** el snapshot del documento debe poseer el `SemaResult` y liberarlo al reemplazarlo/cerrarlo. Añadir prueba de RSS/LSan.

---

#### LSP-02 — Los inlay hints de tipo son heurísticos y mienten

**Severidad:** bloqueante para la confianza del usuario.

`src/psc/lsp/server.pengu:1221-1280` implementa los hints así:

- busca `"var "` o `"let "` en la línea;
- toma el texto tras `" is "`;
- si empieza por `"` → `string`;
- si empieza por `t`/`f` → `bool`;
- si contiene `"."` → `float`;
- **si no, `int`**.

Consecuencias:

- `let b as string is ruta` → `: int` (mal).
- `let ruta as string is "datos.txt"` → añade `: string` aunque ya hay `as string` (duplicado visual).
- `let n is calling suma with 1, 2` → `int` por casualidad.
- `let s is calling obtener` → `int` aunque devuelva `string`.
- `var p as Persona with:` → **no emite nada**.
- `let m is maybe none` → `int`.
- `let x is 1.5 + 2.0` → `float` por el punto, pero `let x is 1e3` → `int`.
- También emite hints dentro de comentarios y strings si contienen `let ... is ...`.

El compilador **sí** infiere bien: se comprobó con un error forzado y devuelve `expected 'int', got 'string'` para `let b is ruta`.

**Solución:** usar `SemaAnnotations`/`SemaSymbol` y `TypeId` real; saltar declaraciones con anotación explícita; no emitir si no hay tipo resuelto (mejor ningún hint que uno falso).

---

#### LSP-03 — El autocompletado no es semántico y no completa módulos

**Severidad:** alta.

`src/psc/lsp/server.pengu:598-641` devuelve:

1. una lista fija de 13 keywords;
2. **todas las palabras del documento**, incluidas las de comentarios y strings;
3. todas con `kind: 6` (Variable);
4. sin `detail`, `documentation`, `insertText`, `textEdit`, `sortText` ni rango.

Evidencia real tras `import std.`:

```json
["weave","rune","echo","omen","const","var","let","if","else","while","for","return","calling","import",
 "std","spark","Persona","nombre","as","string","edad","int","Documentaci","n","de","suma","with",
 "a","b","into","main","ruta","is","datos","txt","juant","set","Juan","30","println","0"]
```

No aparece `archivum`, `net`, `json`, ni ningún módulo. Tampoco aparecen tipos, locales por scope, campos de runa, miembros de módulo ni snippets.

Además, `initialize_result` (`server.pengu:254-255`) declara `completionProvider: {}` sin `triggerCharacters`; por eso escribir `import std.` no dispara completion automático. En VS Code, `Ctrl+Space` sí la pide, pero devuelve la lista anterior.

**Solución:** completion por contexto usando símbolos, tipos, módulos y AST; `triggerCharacters: [".", ":"]`; `CompletionList` con `isIncomplete`; documentación y kinds correctos.

---

#### LSP-04 — El hover no muestra tipos, firmas ni documentación

**Severidad:** alta.

`src/psc/lsp/server.pengu:452-487` busca la palabra bajo el cursor y `decl_line` recorre el texto buscando `"weave " + word`, `"rune " + word`, etc. Devuelve:

- `**ruta**` para una variable local;
- `**int**` para el tipo `int`;
- la línea cruda de `weave suma...` para una función;
- nada de docs, tipo, firma, fields, variantes ni módulos.

Evidencia:

```json
{"contents":{"kind":"markdown","value":"**ruta**"}}
{"contents":{"kind":"markdown","value":"**b**"}}
{"contents":{"kind":"markdown","value":"```pengu\nweave suma with a as int, b as int into int:\n```"}}
```

**Solución:** hover semántico con:

- tipo canónico (`string`, `Persona`, `list of int`, `maybe string`, …);
- firma para funciones/métodos;
- docs `#`/`##`;
- campos/variantes para runas/echos/omens;
- exports para módulos;
- documentación de keywords;
- `range` opcional para subrayar el símbolo.

---

#### LSP-05 — Los semantic tokens son incorrectos y empeoran el coloreado

**Severidad:** alta (es la causa directa de “`set` no se ilumina” y “los tipos no se iluminan”).

`src/psc/lsp/server.pengu:1094-1126` define `is_keyword` con una lista incompleta. `handle_semantic` (`1148-1218`) hace:

```pengu
var ty as int is 3                      # variable por defecto
if calling is_keyword with w:
    set ty is 0                          # keyword
```

Nunca emite `1` (`type`) ni `2` (`function`), aunque están en la leyenda (`208-237`). Tampoco distingue parámetros, campos, variantes ni módulos.

Decodificación real de una muestra:

```text
(3, 6)  Persona -> variable
(4,15)  string  -> variable
(5,13)  int     -> variable
(8, 7)  suma    -> variable
(8,22)  int     -> variable
(11,7)  main    -> variable
(14,18) Persona -> variable
(15,9)  set     -> variable
(15,21) is      -> keyword
```

`set` es keyword en la tabla del lexer (`src/psc/token.pengu:414`), pero no está en `is_keyword`. Como los semantic tokens tienen prioridad sobre TextMate, la gramática no puede compensarlo: el editor muestra `set` como variable.

Además:

- las columnas de inicio se envían en **bytes**, no en UTF-16 (`push_token` recibe `i`, un índice de byte); con acentos/emoji los tokens se desplazan;
- las keywords compuestas/soft (`type of`, `size of`, `frozen`, `inline`, `ritual`) no se reconocen;
- strings raw/triple (`r"..."`, `"""..."""`) se trocean mal;
- no se emiten operadores ni puntuación.

**Solución:** generar tokens desde el lexer/AST, no desde un escáner propio; lista de keywords desde `src/psc/token.pengu`; tipos desde `TypeId`; funciones desde `SkWeave`/`SkDeclare`; campos desde `SemaField`; UTF-16 real. Mientras no esté probado, **desactivar** el provider o ponerlo detrás de un setting (ver D2).

---

### 3.2 Documentación y símbolos

#### SEMA-02 — Las funciones no reciben metadatos de símbolo (línea, columna, módulo, doc)

**Severidad:** alta.

En `src/psc/sema/check/collect.pengu:1001-1038`, `collect_weave` crea el símbolo con `symbol_define_function`, cambia su `kind`, pero **no llama a `tag_decl`**. `tag_decl` solo se invoca desde `register_type` (línea 543) y `collect_const` (línea 958).

Resultado: todo `weave`/`declare`/`test`/método tiene:

- `line = 0`, `col = 0` (valor por defecto de `make_symbol`);
- `module = -1`;
- `doc = -1`.

Esto rompe cualquier feature que quiera usar la tabla de símbolos (hover, definition, outline, docs) y obliga al LSP a reescanear texto, que es justo lo que falla.

Para locales, `src/psc/sema/check/body.pengu:379` hace:

```pengu
set sv.line is calling astutil.start_of with s->ast, node
```

Es decir, guarda un **offset de byte** en un campo documentado como línea 1-indexed. Cualquier consumidor que lo use obtiene basura.

**Solución:**

- llamar a `tag_decl` en `collect_weave`, `collect_declare`, `collect_test`, métodos de `enchanting`/`bind`/`concept`;
- añadir a `SemaSymbol` `start`/`end` de byte (y `doc_start`/`doc_end`) en vez de solo `line/col`;
- corregir `check_local` para línea/columna reales;
- adjuntar docs a campos y variantes (`SemaField.doc`, `SemaVariant.doc`).

---

#### DOC-01 — `psc doc` genera documentación vacía y aborta con `double free`

**Severidad:** alta.

Reproducción mínima:

```pengu
## doc for foo
weave foo into int:
    return 0

weave main into int:
    return calling foo
```

`psc doc --output=docs` genera:

```markdown
### `foo`

> **foo**() -> int


### `main`

> **main**() -> int

_Undocumented function._
```

La doc de `foo` desaparece. Con `std/archivum.pengu` (muchas docs y UTF-8):

```text
free(): invalid pointer
[PENGU CRASH] fatal signal (signal/code 6)
```

o

```text
double free or corruption (out)
```

Causas concretas visibles:

1. `collect_weave` no llama a `tag_decl` (SEMA-02), así que `SemaSymbol.doc` nunca existe para funciones.
2. `tag_decl` (`collect.pengu:491-533`) solo acepta líneas que empiezan por `##`; `LANGUAGE.md:135` promete `#` y `##`.
3. `cmd/doc.render_file` (`src/psc/cmd/doc.pengu:170-250`) vuelve a parsear el fuente a mano, guarda **slices prestados** de `trimmed` en `docs` y luego hace `banish` sobre ellos. Es el patrón clásico de DoubleFree/invalid-free con `PenguString`.
4. `render_file` genera dos páginas por archivo (`main.md` y `src_main.md`), duplicando la salida.
5. No se parsean tags Doxygen (`@param`, `@return`, `@deprecated`), aunque `LANGUAGE.md:4984` los promete.

**Solución:** reescribir la extracción de docs una sola vez (lexer trivia → `SemaSymbol.doc`), y hacer que `psc doc` renderice desde el AST/símbolos, sin slices prestados ni relectura de líneas. Añadir pruebas con `std/archivum` y UTF-8.

---

### 3.3 Navegación, símbolos y refactor

#### LSP-06 — Definición, referencias, highlight y rename son búsquedas de texto

**Severidad:** alta (rename es peligroso).

`handle_definition` (`server.pengu:490-521`) solo busca líneas que empiecen por `weave`, `rune`, `echo`, `omen` o `const`; no encuentra `let`, `var`, parámetros, campos, métodos ni símbolos de módulos. Devuelve un rango de longitud cero al inicio de la línea.

`handle_references` (`651-687`) y `handle_rename` (`826-873`) recorren **todo el texto** y reemplazan cualquier aparición de la palabra, incluidas las de comentarios y strings. No hay resolución de símbolo, ni comprobación de colisiones, ni cambios multi-archivo. `prepareRename` acepta cualquier palabra, incluso keywords.

**Solución:** navegación semántica con `SemaSymbol` + spans; referencias por scope/módulo; rename solo si el símbolo es renameable, con `WorkspaceEdit` multi-archivo; si no se puede garantizar, **no anunciar** la capability (mejor no tener rename que corromper código).

#### LSP-07 — Code lens: comando equivocado, matching por substring y sin argumentos

**Severidad:** alta.

`server.pengu:1050-1092`:

```pengu
if calling scrolls.contains with line, "weave main":
    set title is "Run"
    set cmdname is "psc.run"
else if calling scrolls.contains with line, "test ":
    set title is "Run test"
    set cmdname is "psc.test"
```

Problemas:

- `psc.run`/`psc.test` no existen en la extensión (registra `pengus.run`/`pengus.test`).
- `contains "weave main"` también matchea `weave main_helper`.
- `contains "test "` también matchea `weave contest ...` y comentarios.
- No pasa URI/posición: el “Run” de un archivo no ejecuta ese archivo, ejecuta el entry del proyecto.
- No distingue test concreto.
- En la captura aparecen dos “Run”; el binario actual devuelve uno, así que además hay que descartar cliente duplicado/versión vieja y garantizar instancia única.

**Solución:** emitir `pengus.run`/`pengus.test` con `arguments: [uri, range]`, matching exacto, y registrar alias `psc.run`/`psc.test` por compatibilidad. La extensión ejecutará `psc run <archivo>` / `psc test <archivo>`.

#### LSP-08 — Document/workspace symbols pobres y caros

**Severidad:** media-alta.

`handle_document_symbols` (`553-585`) solo reconoce líneas que empiezan por `weave/rune/echo/omen/const`; no detecta `alias`, `seal`, `concept`, `bind`, `enchanting`, `declare`, `test`, `static var`, `antiquus`, ni métodos anidados. Todo se emite con `kind: 12` (Function), incluso runas/omens. `selectionRange` es de longitud cero.

`handle_workspace_symbols` (`992-1048`) escanea hasta 500 archivos, indexa `std` si está dentro del root, no distingue módulos, no devuelve `isIncomplete`, y se invalida entero en cada edición. En una prueba devolvió 500 símbolos para query vacía.

**Solución:** construir el outline desde el AST, con kinds correctos y jerarquía; indexar workspace por módulo, excluir std por defecto y actualizar incrementalmente.

#### LSP-09 — Signature help no funciona para lo que usa el lenguaje

**Severidad:** media.

`handle_signature` (`917-989`) busca `calling ` en la línea actual y luego la declaración en el texto. Falla con:

- `calling spark.println with ...` (módulo cualificado);
- `calling obj.metodo with ...` (método);
- llamadas anidadas o en varias líneas;
- `ritual`/genéricos.

`activeParameter` siempre es 0 y los parámetros se etiquetan con el texto crudo. Además, los `triggerCharacters` son `(`, `,`, pero el lenguaje llama con `with a, b`; el `(` casi no aparece.

**Solución:** resolver la llamada desde el AST, identificar el argumento por offset, soportar módulos/métodos/genéricos, etiquetas `nombre: tipo`, docs, `activeParameter` real. Añadir `,` y `with ` como triggers (con cuidado).

---

### 3.4 Diagnósticos y protocolo

#### LSP-10 — Diagnósticos pobres, rango incorrecto y sin help/notes

**Severidad:** media-alta.

`publish` (`180-205`) convierte diagnósticos a JSON con `render_json_utf16`, los vuelve a parsear y los publica. `_lsp_diagnostic_u16` en `std/diagnostic.pengu:1250-1280` **no incluye `relatedInformation`** (solo lo hace `_lsp_diagnostic`), así que las etiquetas secundarias se pierden. Tampoco se envían `help`/`note`.

El rango del `E0004` de import ocupa líneas 0–2 en un import de una línea:

```json
{"range":{"start":{"line":0,"character":0},"end":{"line":2,"character":0}}}
```

`source` es `"pengu"` (compilador) en unos diagnósticos y `"psc"` en otros (`diag_json`, línea 105), inconsistente.

**Solución:** construir el `Diagnostic` LSP directamente desde `std.diagnostic.Diagnostic`; incluir `relatedInformation`, `help`/`note` (en `message` o `data` + code action), rango primario correcto, `source: "psc"` uniforme, y `tags` para deprecados.

#### LSP-11 — El protocolo declara cosas que no cumple

**Severidad:** media-alta.

`initialize_result` (`208-262`):

- `moreTriggerCharacter` no existe; el campo correcto es `moreTriggerCharacters` (`server.pengu:243`).
- `completionProvider: {}` sin triggers.
- `codeLensProvider: {}` sin `resolveProvider` (aceptable, pero conviene declararlo).
- `serverInfo.version` es `"0.8.0 (F8)"` aunque el binario es `0.14.7`.
- `implementationProvider` se implementa como `definition` (no es implementación).
- `codeActionProvider` solo ofrece “Format document”, no las acciones que promete el README.
- `textDocumentSync: 1` (full) sin incremental; no es un bug, pero agrava el rendimiento.
- No se anuncian `workspaceFolders` ni se manejan; `initialize` solo mira `rootUri` (`265-278`). En multi-root queda el cwd.
- `$/cancelRequest` se ignora; no hay cancelación.
- `handle_request` no maneja `textDocument/codeLens/resolve`, `workspace/executeCommand`, `textDocument/diagnostic` (pull), etc.

Además, el hack de `server.pengu:1473-1474`:

```pengu
var fixed as string is calling scrolls.replace_all with body.value, r""""params":null""", r""""params":{}"""
```

modifica el JSON en crudo. Puede corromper un string que contenga `"params":null`. La causa es que `std.jsonrpc` rechaza `params: null` (`std/jsonrpc.pengu:700-706`). Hay que aceptar `null` como ausencia de params y eliminar el replace.

#### LSP-12 — Formato y on-type formatting frágiles

**Severidad:** media.

`handle_formatting` (`789-823`):

- escribe en `/tmp` y ejecuta `"{exe} fmt --stdin < {tmp} > {out}"` con shell;
- no funciona en Windows (no hay `/tmp`, el shell puede ser distinto);
- no cita rutas con espacios;
- usa `chronicle.now_ms` + pid como nombre temporal (colisión posible);
- ignora el `.pengufmt.toml` más cercano al archivo (el cwd es el workspace);
- no informa del fallo de `psc fmt`.

`handle_on_type` (`1298-1340`) inserta `\n` + `4` espacios tras **cualquier** `:`, sin leer la configuración de formato y sin distinguir `:` de tipo de `:` de bloque. El README dice que también indenta tras newline; no es cierto.

**Solución:** ejecutar `psc fmt` con argv (sin shell), capturar stdout con un helper de proceso, usar un temp dir del sistema, pasar la ruta del archivo para que encuentre su `.pengufmt.toml`, y hacer on-type solo en aperturas de bloque, con el ancho configurado.

#### LSP-13 — Sin invalidación/republicación al cambiar dependencias

**Severidad:** media.

`workspace/didChangeWatchedFiles` (`1448-1450`) solo hace `st->ws_ready = false`. No revalida ni republica los documentos abiertos que importan el archivo cambiado. Editar un módulo importado no actualiza los diagnósticos del importador hasta que se toca el documento.

**Solución:** mantener un grafo de imports por documento; al cambiar un archivo, revalidar los abiertos afectados y republicar. Igual para `pengu.toml`.

#### LSP-14 — Rendimiento: recheck completo por tecla y sin caché

**Severidad:** media-alta.

Cada `didChange` ejecuta `check_text` completo, que carga y chequea todos los imports desde disco. No hay debounce, caché de módulos, parse cache, ni cancelación. En archivos con varios `std.*` esto se nota; con la fuga de LSP-01, además, la memoria crece.

**Solución:** snapshot por documento con debounce (~150 ms), caché de módulos/parse por contenido, invalidación selectiva, y liberación del snapshot anterior. Considerar incremental sync.

---

### 3.5 Extensión VS Code

#### EXT-01 — Comandos de code lens no registrados y ejecución incorrecta

**Severidad:** alta.

- LSP emite `psc.run`/`psc.test`; `package.json:79-121` y `extension.ts:202-282` registran `pengus.*`.
- `pengus.run` ejecuta `psc run --profile=...` en la raíz, no el archivo del lens.
- No hay `pengus.runFile`/`pengus.testFile`.
- `showMenu` despacha por `label.includes(...)` en vez de por un `command` estable.

**Solución:** `pengus.run`/`pengus.test` aceptan `arguments` `[uri, range]`; alias `psc.run`/`psc.test`; `showMenu` usa un array de `{label, command}`.

#### EXT-02 — Manifiesto inconsistente: engine, iconThemes, empaquetado

**Severidad:** media-alta.

- `engines.vscode` es `^1.80.0` (`package.json:25`), pero `vscode-languageclient@9.0.1` exige `^1.82.0` (`node_modules/vscode-languageclient/lib/node/main.js:35`). En VS Code 1.80/1.81 la extensión lanza “requires VS Code version ^1.82.0” y no activa.
- `contributes.iconThemes` apunta a `./icons/pengu_icon.png` (`package.json:59-66`). Un icon theme debe ser un JSON con `iconDefinitions`; un PNG no es válido. VS Code lo rechaza/loguea error. El icono de lenguaje ya está en `languages[0].icon`.
- `vsce package` incluye 326 archivos y `node_modules` completo, aunque `esbuild` ya bundlea `vscode-languageclient` en `out/extension.js`. Resultado: 3,58 MB y advertencia de rendimiento.
- El icono `pengu_icon.png` pesa **3 MB**; infla el VSIX.
- No hay `extensionKind` para Remote-SSH/WSL/Containers; si la extensión corre en UI y `psc` está en el workspace remoto, falla.
- No hay `capabilities.untrustedWorkspaces`/`virtualWorkspaces`.

**Solución:** subir engine a `^1.82.0`; eliminar `iconThemes` o sustituirlo por un JSON válido; excluir `node_modules` del VSIX (ya está bundleado); optimizar iconos; añadir `extensionKind: ["workspace"]`; declarar workspace trust.

#### EXT-03 — Ejecuta un binario del workspace sin workspace trust

**Severidad:** alta (seguridad).

`pscPath.candidateExecutables` incluye `./psc`, `./bin/psc`, `./dist/psc`, `./build/psc` (`pscPath.ts:105-112`). La extensión los ejecuta automáticamente al activarse (`extension.ts:88-104`). En un workspace no confiable, abrir una carpeta con un `build/psc` malicioso ejecuta código arbitrario.

**Solución:** si `vscode.workspace.isTrusted` es false, no aceptar candidatos dentro del workspace; solo `pengus.executablePath`/`PENGU_STD_DIR`/PATH del usuario, con confirmación. Declarar `untrustedWorkspaces` en el manifiesto.

#### EXT-04 — Ciclo de vida del cliente, watchers y terminal

**Severidad:** media-alta.

- `startClient()` se llama antes de registrar comandos (`extension.ts:199` vs `202`); si falta `psc`, el aviso puede intentar ejecutar `pengus.selectExecutable` antes de que exista.
- `client.start()` no se espera ni captura errores (`extension.ts:145`).
- `errorHandler.closed` siempre devuelve `CloseAction.Restart` (`131-134`): si el binario aborta al arrancar (p. ej. falta una lib), se reintenta en bucle infinito.
- Los `FileSystemWatcher` de `synchronize.fileEvents` se crean en cada `startClient` y no se guardan/liberan (`118-123`); cada restart acumula watchers.
- `output` no se pasa al `LanguageClient`; los logs/errores del servidor no aparecen en el canal “PenguScript”.
- `runInTerminal` concatena el comando sin citar (`58-62`): rutas con espacios rompen; `init` interpola el nombre sin validar (`236-245`) → inyección de shell.
- `getPscCommand()` cae a `psc` aunque no exista; no hay preflight ni comprobación de versión.
- `selectExecutable` no valida que el archivo sea ejecutable ni que sea `psc`.
- No hay status bar, aunque el README la promete.
- `deactivate` no libera terminal/status/watchers.

**Solución:** registrar comandos primero; `await client.start()` con `try/catch` y mensaje; restart con backoff/límite; guardar y disponer watchers; pasar `outputChannel`; usar `ShellExecution`/`Task` o citar argv; validar `init`; añadir status bar; comprobar `psc --version`.

#### EXT-05 — Snippets: existen, pero varios son inválidos y no hay pruebas

**Severidad:** media.

El VSIX sí incluye `snippets/pengus.json` (117 snippets), así que “no snippets” no se explica por el manifiesto. Si no aparecen, hay que revisar versión instalada, `files.associations` y `editor.snippetSuggestions`. Aun así, la calidad es mala:

- `main` y `main_void` usan `spark.println` **sin** `import std.spark` (no compilan solos).
- `println`, `judge_payload`, `or_block`, `many_param`, `weave_where`, `when_debug`, `or_block_err` usan `spark` sin import.
- `concept` genera `weave to_string with self into string`; los métodos de concept **no llevan** `self` (ver `LANGUAGE.md:2191`).
- `bind` genera `weave describe with self into string`; mismo error.
- No hay snippets para `##`/`#` docs, `import std.archivum`, `set .campo`, `with` init, `type of`, `size of`, `derive`, `cyclus`, `antiquus`, `test` con `ward`, etc.
- No hay validación de JSON/sintaxis ni tests de que cada snippet sea parseable.

**Solución:** corregir los snippets existentes; añadir los que faltan; validar en CI que el JSON parsea, que los prefijos son únicos y que los cuerpos (sustituyendo placeholders por valores válidos) parsean con `psc parse`.

#### EXT-06 — El README de la extensión promete features que no existen

**Severidad:** media (confianza del usuario).

`vscode-extension/README.md` afirma:

- “Contextual Documentation” con `#`/`##` → no existe (hover no lee docs).
- “Advanced Type & Size Hover” con tamaño en bytes → no existe.
- “Module-Scoped Autocompletion” (`spark.`, `ledger.`) → no existe.
- “Go to Definition across local variables/functions/std” → no existe (solo texto local).
- “Diagnostics with `help:`/`note:`” → no se envían.
- “Status Bar & QuickPick Menu” → no hay status bar.
- “v0.15.0 Feature Support” → el compilador es 0.14.7 y la gramática no cubre todo.

**Solución:** o implementar, o corregir el README. Recomendación: implementar lo que el usuario necesita (hover, completion, docs, code lens, status bar) y mover el resto a “roadmap”.

---

### 3.6 Gramática, language-configuration y snippets

#### GRAM-01 — La gramática TextMate está incompleta y tiene errores de orden

**Severidad:** alta (para “le falta mucha sintaxis”).

`vscode-extension/syntaxes/pengus.tmLanguage.json`:

- **`test_definition` está después de `keywords_declaration`** (`patterns` líneas 23-25). Como `keywords_declaration` matchea `test`, el nombre del test nunca se colorea como función.
- No incluye `antiquus`, `derive`, `cyclus`, `type of`, `enchanting` como bloque, `bind`, `seal` en posición de uso, `shard`, `where` en tipos, etc.
- `builtin_concepts` (líneas 216-223) está desactualizado: incluye `Index`, `IndexSet`, `Iter`, `Len`, `Display`, `Debug`, `Copy`, `Clone`, `Drop` (que ya no existen en el compilador) y **omite** `Real` e `Iterabilis`, que sí están en `src/psc/sema/symbols/table.pengu:612-622`.
- `builtin_types` no incluye `intptr_t`, `uintptr_t`, `ptrdiff_t`; y los tipos de usuario (`Persona`) no se colorean en posición de uso, solo en la declaración (`type_definition`).
- El bloque `comment.block.pengus` (`begin: "##", end: "##"`) es **código muerto**: antes está `comment.line.double-hash` (`^##.*$`), que consume la línea de apertura. Por eso el contenido de un bloque doc multilínea (`## ... ##`) no se colorea como comentario.
- No hay scope para atributos (`@mutates`), `declare` (nombre C), `include`, `link`, `ldflag`, `insignia`, `enchanting`.
- No hay puntuación (`:`, `,`, `->`) ni operadores bien delimitados.
- `fileTypes` incluye `"d.pengu"` además de las extensiones del manifiesto; es redundante y confuso.

**Solución:** reescribir la gramática por secciones, con orden correcto y patrones contextuales; generar las listas de keywords/tipos/conceptos desde el compilador (`psc language --json`) para que no vuelvan a divergir.

#### LANG-01 — `language-configuration.json` no cubre la sintaxis real

**Severidad:** media.

- `blockComment: ["##","##"]` no refleja el bloque doc real (`##` … `##`), y `lineComment: "#"` hace que `Ctrl+/` sobre una línea `##` produzca `###`.
- `indentationRules` no incluye `antiquus`, `bind`, `test`, `static` ni bloques doc; `decreaseIndentPattern` solo `else|when|or`.
- No hay `onEnterRules` para continuar `##`/`#` ni para cerrar bloques doc.
- No hay `wordPattern` para `self->campo`/módulos.
- `folding.markers` declara `##region`/`##endregion`, pero la gramática no les da un scope; funciona a medias.
- No hay `configurationDefaults` para `[pengus]` (`editor.tabSize`, `editor.insertSpaces`, `editor.formatOnSave`, semantic highlighting).

**Solución:** actualizar reglas de indentación, comentarios, folding y `onEnterRules`; añadir defaults y probar con fixtures.

---

### 3.7 Pruebas, CI y release

#### TEST-01 — No hay pruebas del LSP ni de la extensión en CI

**Severidad:** alta (es la razón por la que estos bugs llegan a release).

- `tests/run.sh` solo ejecuta archivos `.pengu` con `weave main`; no arranca el LSP.
- `vscode-extension/test/f8_smoke.js` requiere un VS Code real y no se ejecuta en CI; solo comprueba diagnósticos.
- El job `vscode` de `.github/workflows/ci.yml:88-126` solo compila `pscPath`, bundlea y empaqueta. No ejecuta la extensión ni prueba gramática/snippets.
- Los antiguos tests `tests/lsp/*` (hover, completion, symbols, semantic tokens, UTF-16, unsaved imports, etc.) fueron eliminados en el refactor; se pueden recuperar de `git show 91fdc6b^:tests/lsp/...` y adaptar.

**Solución:** añadir una suite de protocolo LSP sin VS Code (arranca `psc lsp --stdio` y valida JSON-RPC) y una suite de extensión con `@vscode/test-electron`; ejecutar ambas en CI. Añadir tests de gramática/snippets.

#### PKG-01 — El VSIX está inflado y no se valida el contenido

**Severidad:** media-baja.

`vsce package`:

```text
WARNING This extension consists of 326 files, out of which 166 are JavaScript files.
...
node_modules/ (vscode-languageclient, vscode-jsonrpc, ...)
icons/pengu_icon.png [3 MB]
...
3.58 MB
```

`out/extension.js` ya incluye el cliente; `node_modules` es redundante. El icono de 3 MB es excesivo.

**Solución:** `.vscodeignore` con `node_modules/**`, `out/**/*.map`, `test/**`, `src/**`, `tsconfig.json`; bundlear; optimizar icono; añadir un test que revise el contenido del VSIX.

---

## 4. Decisiones que necesito de ti

Las siguientes decisiones cambian el alcance/arquitectura. Mi recomendación está marcada.

| ID | Decisión | Opciones | Recomendación |
|---|---|---|---|
| D1 | ¿Dónde implementar el LSP? | (a) seguir en PSC, (b) volver a Python/pygls, (c) LSP en TypeScript | **(a) PSC**, usando la capa semántica del compilador. Evita duplicar el modelo de tipos y mantiene el proyecto autocontenido. |
| D2 | Semantic tokens mientras se arreglan | (a) dejarlos activos, (b) desactivarlos temporalmente, (c) setting `pengus.semanticHighlighting` | **(b) + (c)**: desactivar por defecto en el hotfix para que TextMate coloree `set`/tipos; reactivar cuando la suite de tokens pase. |
| D3 | Inlay hints con anotación explícita | (a) mostrar siempre, (b) solo si no hay `as Type` | **(b)**: estilo Rust; evita `string: string`. Para `with` con anotación, el tipo se ve en hover/outline, no hace falta hint. |
| D4 | IDs de comandos de code lens | (a) `psc.run`, (b) `pengus.run`, (c) ambos | **(c)**: canónico `pengus.run`/`pengus.test` + alias `psc.run`/`psc.test` para no romper servidores viejos. |
| D5 | `std.arcivum` | (a) crear alias, (b) tratarlo como typo y sugerir `std.archivum` | **(b)**: no inventar módulos; añadir “did you mean” en diagnóstico/completion. |
| D6 | Docs con `#` | (a) solo `##`, (b) `#` y `##` como dice `LANGUAGE.md` | **(b)**, solo si están contiguas a la declaración (sin línea en blanco), para no convertir cualquier comentario en doc. |
| D7 | Multi-root | (a) un cliente por carpeta, (b) un servidor con varias roots | **(a)** para la primera iteración: menos cambios en el compilador y aislamiento por proyecto. Reevaluar si hay demanda. |
| D8 | Idioma de la UI de la extensión | (a) inglés, (b) español, (c) l10n | **(a) inglés en el marketplace + README español**, y mensajes de error en inglés; hoy hay mezcla español/inglés. |
| D9 | Versión objetivo de gramática/snippets | (a) 0.14.7 actual, (b) 0.15.0 futura | **(a)**: `VERSION` manda; generar listas desde el compilador. La 0.15 se añade cuando exista. |
| D10 | Workspace trust | (a) permitir binario del workspace, (b) bloquearlo en untrusted | **(b)**: seguridad primero; en untrusted solo binario configurado/PATH. |

Si alguna decisión no te convence, dímelo antes de implementar. Las demás las tomaré como aceptadas.

---

## 5. Plan de reparación

### 5.1 Principios

1. **Una sola fuente de verdad:** tipos, símbolos, docs y keywords salen del compilador; el LSP y la extensión no duplican listas.
2. **Nada de heurísticas de texto para semántica:** si no hay dato del AST/tipos, no se muestra (mejor silencio que mentira).
3. **Cada feature con prueba de protocolo.**
4. **Liberar todo:** el LSP es un proceso de larga vida; cada snapshot debe tener dueño y `free`.
5. **Cambios pequeños y verificables:** fases con criterios de aceptación.

### 5.2 Fase 0 — Hotfix de desbloqueo (1–2 días)

Objetivo: que el usuario pueda abrir un proyecto, importar `std.*`, ver colores razonables y usar “Run” sin romper nada.

| Tarea | Archivos | Detalle |
|---|---|---|
| Resolver std de verdad | `src/psc/sema/api.pengu`, `src/psc/driver/paths.pengu`, nuevo `src/psc/sema/stdlib.pengu` | Buscar en este orden: `PENGU_STD_DIR`/`PSC_STD_DIR`; `<root>/std`; `<exe>/../std`; `<exe>/../share/pengu/std`; `$PENGU_HOME/std`; `$PENGU_HOME/share/pengu/std`; `<cwd>/std`; repo root. Pasar `exe` y `root` desde `psc lsp`/`psc check`. |
| Liberar el snapshot | `src/psc/lsp/server.pengu:180-205` | `defer sema_api.free_result with sigil of sr`; liberar `opts` con `sopts.free_options`. Añadir test de RSS. |
| Code lens | `src/psc/lsp/server.pengu:1050-1092`, `vscode-extension/package.json`, `src/extension.ts` | Emitir `pengus.run`/`pengus.test` con `arguments: [uri, range]`; registrar alias `psc.run`/`psc.test`; matching exacto. |
| Inlay hints seguros | `src/psc/lsp/server.pengu:1221-1280` | Si la línea tiene ` as ` antes de ` is `, no emitir hint. Si el inicializador no es un literal reconocible, no emitir (elimina `int` falsos). |
| Semantic tokens | `src/psc/lsp/server.pengu:208-262` | Quitar `semanticTokensProvider` del `initialize` (o ponerlo detrás de `pengus.semanticHighlighting`); hasta que LSP-05 esté arreglado. |
| Engine/manifest | `vscode-extension/package.json:25,59-66` | Subir engine a `^1.82.0`; eliminar `iconThemes`; `extensionKind`. |
| Aviso de versión | `src/extension.ts:88-146` | `psc --version` y `serverInfo.version`; warning si el binario es viejo. |
| README honesto | `vscode-extension/README.md` | Marcar features no implementadas; no prometer status bar hasta F3. |

**Criterio de salida:** un proyecto sin `std/` local importa `std.spark`/`std.archivum`; no hay `psc.run`; no hay hints contradictorios; el RSS se mantiene plano tras 100 cambios; `set` vuelve a colorearse por TextMate.

### 5.3 Fase 1 — Cimientos semánticos del compilador (3–5 días)

| Tarea | Archivos | Detalle |
|---|---|---|
| Metadatos de símbolo | `src/psc/sema/symbols/symbol.pengu`, `collect.pengu`, `body.pengu` | Añadir `start/end` de byte y `doc_start/doc_end`; `tag_decl` para weave/declare/test/métodos; corregir `check_local`. |
| Docs desde trivia | `collect.pengu`, `lexer_comment.pengu`, `lexer_state.pengu` | Recolectar `#`/`##`/bloques `##...##` contiguos; guardar en `SemaSymbol.doc`; no releer el fuente. |
| Campos/variantes | `types/kind.pengu`, `types/table.pengu`, `collect.pengu` | Añadir `doc` a `SemaField`/`SemaVariant` y poblarlo. |
| Resolver compartido | `driver/paths.pengu`, `sema/api.pengu`, nuevo módulo | Un solo `resolve_std_dirs` + lectura de `pengu.toml` (`src_dir`, `lib_dir`, `dep_dirs`). |
| API de consulta | nuevo `src/psc/lsp/sema_query.pengu` o `sema/api` | `symbol_at`, `type_text`, `doc_for`, `exports`, `module_for_path`, `call_at`, `fields_of`, `variants_of`, `comments_before`. |
| Docgen | `src/psc/docgen/sig.pengu`, `src/psc/cmd/doc.pengu` | Renderizar desde símbolos/AST; una página por módulo; Doxygen; eliminar doble página; arreglar DoubleFree. |
| Pruebas | `tests/sema/`, `tests/doc/` | Docs `#`/`##`, UTF-8, `std/archivum`, inferencia local, `with`. |

**Criterio de salida:** `psc doc` sobre `std/archivum` no aborta y conserva docs; `SemaSymbol` de un `weave` tiene línea/columna/módulo/doc; un test unitario puede pedir el tipo de `ruta`/`b`.

### 5.4 Fase 2 — LSP semántico (5–8 días)

| Tarea | Archivos | Detalle |
|---|---|---|
| Snapshot y caché | `server.pengu` | `DocumentSnapshot {text, version, sema, timestamp}`; debounce; liberar anterior; revalidar imports. |
| Diagnósticos | `server.pengu`, `std/diagnostic.pengu` | Construir LSP directo; relatedInformation/help/note; rangos correctos; source uniforme. |
| Hover | `server.pengu:452-487` | Símbolo/tipo/docs/firma/campos/módulos/keywords; `range`. |
| Completion | `server.pengu:598-641` | Contexto: keywords, tipos, conceptos, locales, params, campos, exports, `std.*`, módulos del proyecto; triggers `.`/`:`; kinds/docs. |
| Inlay hints | `server.pengu:1221-1280` | Tipos desde `SemaAnnotations`; solo no anotados; `with`; `for`; `const`; rango. |
| Semantic tokens | `server.pengu:1148-1218` | Desde lexer/AST; keywords completas; tipo/función/param/property/enumMember/namespace; UTF-16; strings raw/triple; modifiers; tests. |
| Navegación | `server.pengu:490-910` | Definition/references/rename/highlight semánticos; multi-archivo; desactivar rename si no es seguro. |
| Symbols | `server.pengu:553-585, 992-1048` | Outline AST con kinds/jerarquía; workspace index; cap + `isIncomplete`. |
| Signature | `server.pengu:917-989` | AST/call site; módulos/métodos; `activeParameter`; docs. |
| Code lens | `server.pengu:1050-1092` | Exacto, args, sin duplicados, test concreto. |
| Formato/on-type | `server.pengu:789-823, 1298-1340` | argv sin shell; temp dir; config del archivo; ancho real; no newline automático salvo ajuste. |
| Protocolo | `server.pengu:208-262, 1343-1503` | `moreTriggerCharacters`, `completionProvider`, `workspaceFolders`, `$/cancelRequest`, `codeLens/resolve`, `serverInfo`; aceptar `params:null` en `std.jsonrpc` y quitar el replace. |
| Code actions | `server.pengu:1282-1295` | Importar módulo, formatear; kinds correctos; diagnóstico asociado. |

**Criterio de salida:** los 11 síntomas de la tabla §2 tienen una prueba que falla antes y pasa después; el RSS no crece en 1000 ediciones; `psc lsp` responde a hover/completion/inlay/semantic como un LSP real.

### 5.5 Fase 3 — Extensión, gramática y snippets (3–4 días)

| Tarea | Archivos | Detalle |
|---|---|---|
| Manifiesto | `vscode-extension/package.json` | Engine `^1.82.0`; `extensionKind`; commands/runFile/testFile/check/format; configuración (`lsp.trace`, `inlayHints`, `semanticHighlighting`, `statusBar`, `autoRestart`, `stdDir`); menus; `configurationDefaults`; `capabilities.untrustedWorkspaces`. |
| Ciclo de vida | `src/extension.ts` | Registrar primero; `await client.start()` con error; restart con backoff; watchers guardados; `outputChannel`; status bar; `deactivate` limpio; multi-root (D7). |
| Seguridad | `src/pscPath.ts`, `src/extension.ts` | No binario del workspace en untrusted; validar ejecutable; `PSC_BIN_PATH`; `~`; comillas. |
| Comandos | `src/extension.ts` | `runFile`/`testFile` con args; `showMenu` por command ID; `init` validado/citado; `check`; `format`; `selectExecutable` con versión. |
| Gramática | `syntaxes/pengus.tmLanguage.json` | Reescribir por secciones; orden de `test_definition`; keywords completas; conceptos reales (`Real`, `Iterabilis`); tipos de usuario en uso; doc blocks; `antiquus`/`derive`/`cyclus`; atributos; puntuación. |
| Generación | nuevo `tools/gen_language_assets.py` o `psc language --json` | Exportar keywords/tipos/conceptos desde el compilador; validar gramática contra esa lista en CI. |
| Language config | `language-configuration.json` | Indentación, comentarios, `onEnterRules`, folding, `wordPattern`, defaults. |
| Snippets | `snippets/pengus.json` | Corregir `main` (import), `concept`/`bind` (sin `self`), `spark`; añadir docs/import/with/set/type of/size of/derive/cyclus/antiquus; validar. |
| README | `vscode-extension/README.md` | Features reales, instalación, troubleshooting (`psc` path, std, logs), compatibilidad de versiones. |
| Empaquetado | `.vscodeignore`, iconos | Excluir `node_modules`; optimizar icono; VSIX < 500 KB. |

**Criterio de salida:** `set`, `string`, `int`, `Persona`, `test`, `##` se iluminan bien; snippets `main` compilan; el VSIX es pequeño; los comandos funcionan desde palette y code lens.

### 5.6 Fase 4 — Pruebas, CI, documentación y release (2–3 días)

| Tarea | Detalle |
|---|---|
| Suite LSP | `tests/lsp/run_lsp_tests.py` (o Node): std en proyecto sin `std/`, hover tipo/docs, completion `std.`, inlay `b`, code lens `pengus.run`, semantic `set`, UTF-16, diagnósticos, formato, signature, rename seguro. |
| Suite VS Code | `@vscode/test-electron`: activación, language ID, snippets, comandos, status bar, code lens, diagnóstico, gramática con `vscode-textmate`. |
| Gramática/snippets | Tokenizar fixtures y comprobar scopes; parsear snippets con placeholders sustituidos. |
| Memoria | Test de RSS/LSan del LSP con 1000 `didChange`; fallar si supera un umbral. |
| CI | Añadir jobs; ejecutar todo en Linux/macOS; `vsce package` y comprobar contenido. |
| Docs | Actualizar `LANGUAGE.md` §20.10, `docs/psc/CLI.md`, README raíz, `vscode-extension/README.md`; añadir `docs/LSP.md`. |
| Release | Bump `VERSION`/extensión; regenerar stage0 (`tools/gen_stage0.sh`); subir VSIX y binarios; verificar `psc --version` vs `serverInfo`. |

**Criterio de salida:** CI verde con LSP + extensión + gramática + snippets; release reproducible.

---

## 6. Matriz de aceptación (síntomas reportados + regresiones)

| # | Prueba de aceptación | Antes | Después |
|---|---|---|---|
| 1 | Proyecto sin `std/` local, `psc` instalado en `bin/psc`; `import std.spark` | E0004 | Sin diagnóstico; hover/completion de `spark` |
| 2 | Escribir `import std.` | Sin sugerencias | Lista `archivum`, `spark`, `json`, … con docs |
| 3 | `let ruta as string is "datos.txt"` | Hint `: string` duplicado | Sin hint (anotación explícita) |
| 4 | `let b as string is ruta` | Hint `: int` | Sin hint o `: string` coherente; hover `string` |
| 5 | Clic en “Run” sobre `main` | `command 'psc.run' not found` | Ejecuta `psc run <archivo>`; un solo lens |
| 6 | Hover sobre `ruta`/`suma` | `**ruta**` / línea cruda | `let ruta: string` + doc; firma de `suma` |
| 7 | `##`/`#` sobre `weave` | Sin doc | Hover y `psc doc` muestran doc |
| 8 | `let b is ruta` | Hint `int` | Hint `string` |
| 9 | Completar tras `calling ` / `spark.` | Nada útil | Funciones/locales/campos/módulos |
| 10 | `var p as Persona with:` | Sin tipo | Hover/outline `Persona`; sin hints falsos |
| 11 | `set`, `string`, `Persona`, `test` | variables | keyword/type/function/type; kill switch si falla |
| 12 | 1000 ediciones | RSS crece sin límite | RSS estable |
| 13 | `psc doc` sobre `std/archivum` | crash | Markdown con docs, sin duplicados |

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| El refactor del LSP rompe diagnóstico estable | Fase 0 mantiene el checker actual; pruebas de protocolo antes/después; feature flag para semantic tokens. |
| El cambio de `SemaSymbol` afecta codegen | Añadir campos al final, sin cambiar los existentes; ejecutar `tests/run.sh` + ASan; revisar `SemaSymbol` copias POD. |
| Resolver std con muchas rutas ralentiza | Cachear `std_dirs` por proceso/proyecto; medir. |
| Docgen reescrito cambia salida esperada | Tests de snapshot; conservar `docs/README.md` y enlaces. |
| Multi-root se retrasa | D7: un cliente por carpeta en la extensión; documentar limitación. |
| Semántica de tokens distinta entre VS Code/Neovim | Probar con cliente LSP neutro; no depender de VS Code. |
| El usuario tiene un `psc` viejo | Comprobación de versión + mensaje accionable; no arrancar en silencio. |

---

## 8. Fuera de alcance (por ahora)

- Memoria/`estimate_size` en hover (requiere modelo de layout C; el `LANGUAGE.md` lo promete pero no existe en PSC).
- Rename multi-archivo completo si no hay garantía semántica (mejor desactivado).
- Formateo incremental/range formatting.
- Depuración (DAP), test explorer, task provider completo.
- Soporte Windows del LSP/formato (el repo dice que Windows no está soportado; la extensión tiene ramas Windows que habría que probar).
- Traducción completa de la UI (D8).

---

## 9. Anexo A — Evidencia cruda del LSP

### A.1 Capacidades actuales

```json
{
  "textDocumentSync": 1,
  "hoverProvider": true,
  "definitionProvider": true,
  "documentSymbolProvider": true,
  "referencesProvider": true,
  "documentHighlightProvider": true,
  "foldingRangeProvider": true,
  "documentFormattingProvider": true,
  "implementationProvider": true,
  "workspaceSymbolProvider": true,
  "codeLensProvider": {},
  "semanticTokensProvider": {
    "legend": {
      "tokenTypes": ["keyword","type","function","variable","string","number","comment"],
      "tokenModifiers": []
    },
    "full": true
  },
  "inlayHintProvider": true,
  "codeActionProvider": true,
  "documentOnTypeFormattingProvider": {
    "firstTriggerCharacter": ":",
    "moreTriggerCharacter": []
  },
  "signatureHelpProvider": { "triggerCharacters": ["(", ","] },
  "renameProvider": { "prepareProvider": true },
  "completionProvider": {}
}
```

Problemas visibles: `moreTriggerCharacter` (typo), `completionProvider` vacío, `serverInfo.version: "0.8.0 (F8)"`.

### A.2 Hover / inlay / completion

```json
hover ruta  -> {"contents":{"kind":"markdown","value":"**ruta**"}}
hover b     -> {"contents":{"kind":"markdown","value":"**b**"}}
hover suma  -> {"contents":{"kind":"markdown","value":"```pengu\nweave suma with a as int, b as int into int:\n```"}}

inlay -> [
  {"position":{"line":11,"character":12},"label":": string"},
  {"position":{"line":12,"character":9},"label":": int"}
]
```

`line 11` es `let ruta as string is "datos.txt"`; el hint `: string` se suma a la anotación. `line 12` es `let b as string is ruta`; el hint dice `int` (mal).

### A.3 Semantic tokens decodificados

```text
(3, 6)  Persona -> variable
(4,15)  string  -> variable
(5,13)  int     -> variable
(8, 7)  suma    -> variable
(14,18) Persona -> variable
(15,9)  set     -> variable
(15,21) is      -> keyword
```

No hay ni un token de tipo `type` ni `function`.

### A.4 Fuga de memoria

```text
initial rss KB 16280
0   29048
5   93044
10  157068
15  221112
20  285124
25  349120
30  413088
```

### A.5 Documentación

```text
$ psc doc --output=docs
### `foo`
> **foo**() -> int

### `main`
> **main**() -> int
_Undocumented function._
```

`foo` tenía `## doc for foo`; la doc desapareció. Con `std/archivum`: `free(): invalid pointer` / `double free or corruption (out)`.

---

## 10. Anexo B — Archivos que se tocarán (mapa rápido)

| Área | Archivos |
|---|---|
| Resolución std | `src/psc/sema/api.pengu`, `src/psc/driver/paths.pengu`, nuevo `src/psc/sema/stdlib.pengu` |
| Símbolos/docs | `src/psc/sema/symbols/symbol.pengu`, `.../table.pengu`, `src/psc/sema/check/collect.pengu`, `.../body.pengu`, `src/psc/sema/types/kind.pengu` |
| Consulta LSP | nuevo `src/psc/lsp/sema_query.pengu` |
| LSP | `src/psc/lsp/server.pengu`, `positions.pengu`, `transport.pengu`, `src/psc/cmd/lsp.pengu` |
| JSON-RPC | `std/jsonrpc.pengu` |
| Docgen | `src/psc/docgen/sig.pengu`, `src/psc/cmd/doc.pengu` |
| Diagnósticos | `std/diagnostic.pengu` |
| Extensión | `vscode-extension/package.json`, `src/extension.ts`, `src/pscPath.ts`, `.vscodeignore` |
| Gramática/config | `syntaxes/pengus.tmLanguage.json`, `language-configuration.json`, `snippets/pengus.json` |
| Pruebas/CI | `tests/lsp/*`, `vscode-extension/test/*`, `.github/workflows/ci.yml`, `tests/run.sh` |
| Docs | `LANGUAGE.md`, `docs/psc/CLI.md`, `README.md`, `vscode-extension/README.md`, nuevo `docs/LSP.md` |

---

## 11. Recomendación final

Aprobaría el plan en este orden:

1. **Fase 0** ya: resolver std + liberar memoria + code lens + desactivar tokens falsos. Es lo que desbloquea al usuario y evita que el LSP consuma gigabytes.
2. **Fase 1**: metadatos de símbolos y docs; sin esto, el resto es maquillaje.
3. **Fase 2**: LSP semántico con pruebas de protocolo.
4. **Fase 3**: gramática/snippets/extensión.
5. **Fase 4**: CI, release y documentación.

No intentaría arreglar hover/completion/inlay por separado antes de Fase 1: volverían a ser heurísticas. La inversión grande está en `SemaQuery` (Fase 1) y en el snapshot del LSP (Fase 2); después, cada feature es relativamente pequeña.

Cuando revises el documento, dime:

- si aceptas las decisiones D1–D10 (o cuáles cambias);
- si prefieres que la Fase 0 se entregue como hotfix `0.14.8` + extensión `3.2.1`, o que todo vaya en un solo release mayor;
- si quieres que el rename se desactive hasta Fase 2 (mi recomendación) o que se mantenga el textual con un warning.
