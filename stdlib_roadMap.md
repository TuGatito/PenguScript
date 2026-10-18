# 🐧 Fase 1 — Filtro de módulos `std.*` para PenguScript 3.0

Perfecto. Antes de meter código, apliquemos el filtro. Voy a ser riguroso con las dos condiciones que planteaste, porque **"usable por el usuario para más cosas que el compilador"** es una condición más exigente de lo que parece a primera vista. Hay módulos que *parecen* generales pero que en realidad son "cosas que usas cuando escribes un compilador".

---

## 📋 1. Los dos criterios, formalizados

> **C1 — Implementabilidad:** el módulo se puede escribir **enteramente en PenguScript** o envolver una **librería single-header** (binding + wrapper).
>
> **C2 — Generalidad:** el módulo tiene **al menos dos dominios de uso no relacionados con el compilador** donde aporta valor real, **sin que el usuario tenga que reimplementar** el dominio de la Fase 0.

Algunos matices que aplican al filtro:

- **C1 no excluye `antiquus`.** Un módulo "puro" puede usar `antiquus` localmente si está justificado (p. ej. syscalls). Un módulo "binding" puede usar `declare` + `include` + `link`. Ambos cuentan.
- **C2 no exige que el módulo sea trivial.** Exige que exista un usuario no-compilador con un problema que el módulo resuelve **mejor que la alternativa existente**.
- **`std.cipher`, `std.scrolls`, etc. ya existen.** Si un módulo nuevo solapa con uno existente sin un motivo claro, es mejor **extender el existente** que crear uno nuevo.

---

## 🎯 2. Veredicto módulo por módulo

### ✅ Pasa los dos filtros — va al stdlib

| Módulo | C1 | C2 | Justificación |
|---|---|---|---|
| **`std.arena`** | ✅ Puro | ✅ | Cualquier programa que construya un árbol o un grafo temporal y quiera liberarlo de golpe. No es solo compiladores: parsers, deserializadores, editores de texto, renderers. |
| **`std.builder`** | ✅ Puro | ✅ | Cualquier programa que genere texto por partes. Logs, CSV, HTML, plantillas, correos, reportes. Absolutamente general. |
| **`std.diagnostic`** | ✅ Puro | ✅ | Cualquier herramienta que reporte errores **con posición en un fichero fuente**: linters, validadores de JSON/YAML/TOML, herramientas de migración, correctores ortográficos. Es **general si se diseña general** (ver §3.1). |
| **`std.sourcemap`** | ✅ Puro | ✅ | Cualquier herramienta que traduzca entre offset/línea/columna: editores, diff tools, visores de logs, formateadores, extractores de snippets. General. |
| **`std.bitset`** | ✅ Puro | ✅ | Conjuntos de enteros densos, filtros Bloom, máscaras, grafos de adyacencia, histogramas, validaciones por campo. Cualquier usuario lo usa. |
| **`std.json`** | ✅ Puro o binding | ✅ | Intercambio de datos universal. En 3.0 lo implementaría **puro** (extendiendo `std.cipher`) para evitar el binding; ver §4.2. |
| **`std.jsonrpc`** | ✅ Puro | ✅ | LSP, MCP (Model Context Protocol), APIs remotas, comunicación entre procesos. General. |
| **`std.unicode`** | ⚠️ Binding recomendado | ✅ | Texto no-ASCII es universal. `utf8.h` (single-header, MIT, ~2000 LOC) es perfecto. Binding + wrapper puro para la API idiomática. |
| **`std.regex`** | ⚠️ Binding recomendado | ✅ | Búsqueda de patrones en texto es universal. `tiny-regex-c` (single-header, ~200 LOC) o `re.h` (single-header, más completo). Binding + wrapper. |
| **`std.graph`** | ✅ Puro | ✅ | Ordenación topológica, BFS/DFS, componentes fuertemente conexas: build systems, gestores de paquetes, resolución de dependencias, planificación de tareas, análisis de redes. **Pero** ver §3.2: los *dominadores* son específicos de compiladores. |
| **`std.lexer`** | ✅ Puro | ⚠️ Matiz | **¿Es general?** Solo si el diseño es **"primitivas de lexer"** (cursor, peek, advance, error recovery, token stream genérico) y **no** "el lexer de PenguScript". Con ese diseño, sirve a cualquiera que escriba un DSL, un tokenizador de configuración, un parser de expresiones, etc. **Diseñarlo así.** |
| **`std.parser`** | ✅ Puro | ⚠️ Matiz | Igual que `std.lexer`: **"primitivas de parser"** (cursor de tokens, combinatorios manuales, error recovery, backtracking explícito) y no "el parser de PenguScript". Sin closures, los combinatorios clásicos son incómodos; el diseño correcto son **primitivas de recursive descent** (lookahead, consume, expect, recover). Diseñarlo así y sirve a cualquier DSL. |
| **`std.cst`** | ✅ Puro | ⚠️ Matiz | **"CST genérico con trivia"** sirve a formatters, refactorings, syntax highlighters, editores de código, generadores de diff estructural. Diseñarlo genérico (nodos con `kind`, `children`, `trivia`, `span`) y no específico de PenguScript. |

### ❌ No pasa C2 — va a repositorio satélite o al propio compilador

| Módulo | Razón | Destino |
|---|---|---|
| **`std.incremental`** | Caching incremental de compilación es específico del compilador. Un usuario que quiera cachear resultados tiene `std.lot` (PRNG) o puede construirlo. No merece un `std.*`. | **Compilador** o repositorio satélite `pengu-incremental`. |
| **Dominadores, dataflow, SSA** | Específicos de compiladores. Aunque `std.graph` es general, los algoritmos de dominadores no lo son. | **Compilador.** No entran en `std.graph`. |
| **Inferencia de tipos, unificación** | Específicos de compiladores de lenguajes con tipos. | **Compilador.** |
| **Codegen helpers** (emit `switch`, emit casts) | Específicos del backend de PenguScript. | **Compilador.** |
| **`std.regexp` full PCRE** | Un binding a PCRE2 no es single-header (son varios ficheros + dependencias). Va contra C1. | **Repositorio satélite** `pengu-pcre` si alguien lo quiere. |
| **`std.yaml`, `std.toml`, `std.xml`** | No están en la lista de Fase 1, pero por si acaso: son generales pero **no son de la Fase 1**. Se pueden añadir en 3.1+ si hay demanda. | **Futuras fases.** |

### 🤔 Casos límite que hay que decidir explícitamente

| Caso | Decisión propuesta | Razón |
|---|---|---|
| **`std.diagnostic`** — ¿general o específico de compilador? | **General, con extensión opcional.** El tipo `Diagnostic` base tiene `severity`, `message`, `location`, `help`, `note`. Nada de "AST node", "type trace", "symbol table entry". El compilador, si quiere, envuelve `Diagnostic` en un `rune CompilerDiagnostic` que añade esos campos. | General: linters, validadores, herramientas de migración. |
| **`std.graph`** — ¿incluye dominadores? | **No.** `std.graph` tiene BFS, DFS, topo sort, SCC, caminos mínimos genéricos. Dominadores van al compilador. | Dominadores son específicos. |
| **`std.cst`** — ¿incluye nodos específicos de PenguScript? | **No.** `std.cst` tiene `CstNode`, `CstKind` (enum cerrado pero genérico: Token, Group, List, Error, Comment…), `Span`, `Trivia`. El compilador define sus propios `kind` extendiendo o envolviendo. | General: formatters, refactorings, editores. |
| **`std.json` vs extender `std.cipher`** | **Crear `std.json` como módulo propio y deprecar el JSON de `cipher`** con una ventana de dos releases. | Coherencia: `cipher` es "codificaciones y hashing"; JSON es "formato de datos estructurado". Son dominios distintos. |
| **`std.lexer` / `std.parser`** — ¿módulos separados o `std.cst` con todo? | **Separados.** `std.cst` define la estructura; `std.lexer` produce tokens; `std.parser` los consume. Separación limpia. | Coherencia. |
| **`std.unicode`** — ¿binding o puro? | **Binding + wrapper puro.** `utf8.h` es MIT, single-header, ~2000 LOC, bien testeado, y reimplementar UTF-8 correctamente en puro es trabajo de semanas. La API pública (`std.unicode`) es puro PenguScript; el binding interno es la implementación. | C1 permite el binding. C2 lo exige. |
| **`std.regex`** — ¿binding a qué? | **Binding a `tiny-regex-c` + wrapper puro.** ~200 LOC, single-header, MIT. Cubre `^ $ . * + ? [] [^] | ()`. Para regex más potente, el usuario instala `pengu-pcre` como satélite. | C1 permite el binding. C2 lo exige. |

---

## 📦 3. Notas de diseño críticas (para que no te pase lo que a otros)

### 3.1 `std.diagnostic` debe ser general 🎯

Diseña la API pensando en un **validador de YAML**, no en el compilador de PenguScript:

```pengu
## std/diagnostic.pengu
rune Span:
    file as string
    start_line as int
    start_col as int
    end_line as int
    end_col as int
    start_byte as int
    end_byte as int

omen Severity:
    Error
    Warning
    Info
    Hint

rune Diagnostic:
    severity as Severity
    code as string           # "E0005" o "my-lint-rule"
    message as string
    span as Span
    help as maybe string
    note as maybe string
    related as list of Diagnostic   # relacionados (para "did you mean?")

rune DiagnosticBag:
    items as list of Diagnostic
    error_count as int
    warning_count as int

enchanting DiagnosticBag:
    weave add with d as Diagnostic into void:
        # actualiza counts + añade
    weave has_errors into bool:
        # error_count > 0
    weave render with color as bool into string:
        # render estilo Rust con --> ^^^, help:, note:
```

**Nada** de `ast_node: ref to Expr`. Nada de `type: TypeInfo`. Si el compilador necesita más, envuelve.

### 3.2 `std.graph` debe ser genérico, no específico 🎯

```pengu
## std/graph.pengu
rune Graph:
    n_nodes as int
    adjacency as list of list of int   # lista de adyacencia

enchanting Graph:
    weave ritual from_edges with n as int, edges as list of (int, int) into Graph
    weave ritual from_adjacency with adj as list of list of int into Graph
    weave bfs with start as int into list of int
    weave dfs with start as int into list of int
    weave topological_sort into maybe (list of int)   # none si hay ciclo
    weave has_cycle into bool
    weave scc into list of list of int                # Tarjan o Kosaraju
    weave shortest_path with from as int, to as int into maybe (list of int)
    weave connected_components into list of list of int
```

**No** incluyas dominadores, post-dominadores, dataflow. Eso son 2000 líneas de código específico de compilador y no tienen otro uso.

### 3.3 `std.cst` debe ser genérico 🎯

```pengu
## std/cst.pengu
omen CstKind:
    Token               # terminal concreto
    Group               # agrupación delimitada (paréntesis, llaves…)
    List                # secuencia con separadores
    Error               # nodo de error (recuperación)
    Comment             # trivia: comentario
    Whitespace          # trivia: espacio en blanco
    Eof

rune CstNode:
    kind as CstKind
    text as string             # el texto del token, o "" para nodos compuestos
    children as list of ref to CstNode
    span as diagnostic.Span

rune Cst:
    root as ref to CstNode
    source as string           # texto original completo
```

**No** incluyas `PenguScriptFunctionDeclNode`, `PenguScriptLetStmtNode`, etc. Eso es del compilador.

### 3.4 `std.lexer` / `std.parser` como primitivas, no como frameworks 🎯

```pengu
## std/lexer.pengu
rune Cursor:
    src as string
    pos as int
    line as int
    col as int

enchanting Cursor:
    weave peek into char
    weave peek_at with offset as int into char
    weave advance into char
    weave match with expected as char into bool
    weave match_str with expected as string into bool
    weave skip_whitespace with f as weave with c as char into bool into void
    weave span_from with start_pos as int into diagnostic.Span

## std/parser.pengu
rune TokenStream:
    tokens as list of Token
    pos as int

enchanting TokenStream:
    weave peek into Token
    weave peek_at with offset as int into Token
    weave advance into Token
    weave expect with kind as string into maybe Token   # none + error recovery
    weave recover_until with kinds as list of string into list of Token
```

**No** incluyas combinatorios genéricos (sin closures son incómodos). Primitivas que el usuario compone a mano con recursive descent.

---

## 🚀 4. Recomendaciones de binding single-header

Para los dos módulos que he marcado como binding:

### 4.1 `std.unicode` — `utf8.h` 🈁

- Repo: https://github.com/sheredom/utf8.h
- Licencia: MIT (compatible).
- Tamaño: ~2000 LOC, single-header.
- Features: decodificación UTF-8 (incluido codepoints > U+FFFF), codificación, validación, iteración, comparación, categorías parciales.
- Lo que **no** cubre: normalización Unicode (NFC/NFD), case folding completo, word breaking. Para eso, `pengu-icu` como satélite.
- **Enfoque:** `std/unicode.d.pengu` (declare) + `std/unicode.pengu` (wrapper puro) + `std/vendor/utf8.h` vendorizado + `build_runtime.py` añade `-I std/vendor/`.

### 4.2 `std.regex` — `tiny-regex-c` 🔍

- Repo: https://github.com/kokke/tiny-regex-c
- Licencia: public domain (aún mejor).
- Tamaño: ~200 LOC, single-header + 1 `.c`.
- Features: `^ $ . * + ? [] [^] | ()` — sin backreferences, sin lookahead/lookbehind.
- **Enfoque:** igual que unicode. `std/regex.d.pengu` + `std/regex.pengu` + `std/vendor/re.h` + `std/vendor/re.c`.
- **Wrapper puro** expone: `weave match`, `weave is_match`, `weave find`, `weave replace_first`, `weave replace_all`. Esto es lo que un usuario necesita el 90 % de las veces.
- Alternativa: `re.h` de Scott Vokes (más features, MIT, single-header). Si quieres lookahead, ve a este.

---

## 📊 5. Lista final propuesta

### 🟢 Va al stdlib (13 módulos)

| Prioridad | Módulo | C1 | C2 | Notas |
|---|---|---|---|---|
| **1** | `std.builder` | Puro | Fuerte | Ninguna dependencia. Rápido. |
| **2** | `std.arena` | Puro | Fuerte | Sobre `std.memoria`. |
| **3** | `std.diagnostic` | Puro | Fuerte | Diseño general (ver §3.1). |
| **4** | `std.sourcemap` | Puro | Fuerte | Trivial. |
| **5** | `std.json` | Puro | Fuerte | Nuevo, supersede JSON de `cipher`. |
| **6** | `std.bitset` | Puro | Moderado | Trivial. |
| **7** | `std.graph` | Puro | Moderado | Sin dominadores. |
| **8** | `std.unicode` | Binding | Fuerte | `utf8.h`. |
| **9** | `std.regex` | Binding | Fuerte | `tiny-regex-c`. |
| **10** | `std.jsonrpc` | Puro | Moderado | Sobre `std.json`. |
| **11** | `std.lexer` | Puro | Moderado | Primitivas (ver §3.4). |
| **12** | `std.parser` | Puro | Moderado | Primitivas (ver §3.4). |
| **13** | `std.cst` | Puro | Moderado | Genérico (ver §3.3). |

### 🔴 Va a satélite o al compilador (no stdlib)

| Módulo | Destino |
|---|---|
| `incremental` | Compilador o `pengu-incremental` satélite. |
| Dominadores / SSA / dataflow | Compilador. |
| Type inference / unification | Compilador. |
| Codegen helpers | Compilador. |
| PCRE2 binding | `pengu-pcre` satélite. |
| YAML / TOML / XML | Futuras fases. |

---

## 📅 6. Orden de implementación sugerido

Propongo **cuatro sub-fases** dentro de la Fase 1. Cada sub-fase termina en una versión publicable:

### Fase 1a — Fundamentales (→ 2.9.0) ✅
1. `std.builder` — puro, ~200 LOC.
2. `std.arena` — puro, ~300 LOC.
3. `std.sourcemap` — puro, ~150 LOC.
4. `std.bitset` — puro, ~200 LOC.

**Total:** ~850 LOC + tests. **Bloqueantes para el compilador.** No tienen dependencias.

### Fase 1b — Diagnósticos y datos (→ 2.10.0) ✅
5. `std.diagnostic` — puro, ~400 LOC.
6. `std.json` — puro, ~800 LOC (parser + writer + query).
7. `std.jsonrpc` — puro, ~300 LOC.

**Total:** ~1500 LOC + tests. **Bloqueantes para el LSP.**

### Fase 1c — Texto internacionalizado (→ 2.11.0) ✅
8. `std.unicode` — binding a `utf8.h` (~200 LOC wrapper + binding).
9. `std.regex` — binding a `tiny-regex-c` (~200 LOC wrapper + binding).

**Total:** ~400 LOC wrapper + binding + tests. **No bloqueantes**, pero mejoran la ergonomía.

### Fase 1d — Cliente HTTP (→ 2.12.0) ✅
10. `std.petitio` — wrapper de alto nivel sobre libcurl (~1100 LOC wrapper +
    ~600 LOC de puente C). `naett` se evaluó y se descartó: su API no tiene
    timeout total, ni límite de redirects, ni cookies, ni proxy, ni multipart.
    Smart linking por función (`-lpetitio -lcurl` solo al importar).

**Total:** ~1700 LOC + tests. **Desbloquea `pengu add <url>` nativo y las tareas
de red**, que era la petición más repetida de cualquier usuario de un lenguaje
de scripting. Ver `docs/PETITIO.md`.

### Fase 1e — Herramientas de lenguaje (→ 2.13.0)
11. `std.graph` — puro, ~500 LOC.
12. `std.lexer` — puro, ~300 LOC.
13. `std.parser` — puro, ~400 LOC.
14. `std.cst` — puro, ~400 LOC.

**Total:** ~1600 LOC + tests. **Bloqueantes para el `pengu fmt` autohospedado.**

---

## 🤔 7. Tres decisiones que quiero que confirmes antes de que el agente empiece

### 7.1 ¿`std.lexer` / `std.parser` como primitivas, o como "framework"?

He propuesto **primitivas** (cursor, token stream, lookahead, error recovery), porque sin closures los combinatorios clásicos (Haskell, Rust) son incómodos y porque **cada lenguaje tiene su propia gramática** — un framework genérico sería un lastre.

**Confirmación:** ¿de acuerdo? Si prefieres un enfoque más "framework", dímelo y diseño uno (probablemente peor, pero tu decisión).

### 7.2 ¿`std.json` como módulo propio, o extender `std.cipher`?

He propuesto **crear `std.json`** y deprecar el JSON de `cipher`. Alternativa: **extender `cipher`** con el parser completo, evitando un módulo nuevo.

**Confirmación:** ¿`std.json` propio (más limpio) o `cipher` extendido (menos módulos)?

### 7.3 ¿Priorizar `std.lexer` / `std.parser` / `std.cst` antes de `std.unicode` / `std.regex`?

He propuesto dejar `unicode`/`regex` para después de `lexer`/`parser`/`cst`. Alternativa: **priorizar los bindings** porque son rápidos (solo wrapper) y desbloquean texto no-ASCII en lexer/parser.

**Confirmación:** ¿prefieres el orden que propongo (puro primero, bindings después) o invertirlo?

---

## 🎯 8. Recomendación global

**Sí a los 13 módulos** en el stdlib, con las notas de diseño de §3. **No a `incremental`** ni a los específicos del compilador. **Sí a los bindings single-header** para `unicode` y `regex`, con wrapper puro.

**El orden de las cuatro sub-fases (1a → 1b → 1c → 1d)** es deliberado: lo que bloquea el compilador (1a) va primero; lo que bloquea el LSP (1b) después; la ergonomía (1c) puede esperar; las herramientas de lenguaje (1d) son las más grandes y se benefician de tener `builder`, `arena` y `diagnostic` ya disponibles.

Confírmame §7.1, §7.2, §7.3 y arrancamos con la **Fase 1a** (builder + arena + sourcemap + bitset). Puedo redactar la instrucción completa para el agente, con la misma autonomía total que en las fases anteriores.

¿Vamos? 🐧8