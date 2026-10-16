# Planificación de PenguScript 3.0 — Self-Hosting

He revisado los cuatro documentos (LANGUAGE_Spanish.md, README.md, PenguScriptGuideSpanish.md, requirements.txt). Voy a organizar el análisis en dos partes, como pediste, y una tercera con un roadmap sugerido.

---

## Parte 1 — Estado de la sintaxis para self-hosting

### 1.1 Lo que ya está listo (y es mucho)

Para escribir un compilador en PenguScript, el lenguaje ya ofrece las piezas fundamentales:

| Necesidad del compilador | Característica existente |
|---|---|
| AST con nodos recursivos | `rune` + `cyclus` + `ref to` / `maybe ref to` (§9.1.1) |
| Uniones etiquetadas con payload | `omen` algebraico (§9.3) |
| Pattern matching sobre nodos | `judge … when … with <campos>` (§7.4) |
| Genéricos para estructuras de datos | `shard T` + `where` (§11) |
| Contratos estáticos | `concept` + `bind` (§10) |
| Manejo de errores sin excepciones | `maybe T` / `result of T to E` (§12) |
| Estado de módulo | `static var` + accesores (§14.5) |
| I/O de archivos | `std.archivum` |
| Procesos y CLI | `std.rites` + `std.invoke` |
| JSON | `std.cipher` |
| Hilos | `std.filum` |
| Memoria manual | `banish` / `defer` / `std.memoria` |
| Atributos FFI | `@export`, `@noreturn`, `@packed`, `@align` |
| C embebido | `antiquus` (§9.6) |

El compilador **puede** escribirse en PenguScript hoy. Lo que sigue son los puntos que harían la diferencia entre "se puede" y "es cómodo y robusto".

### 1.2 Gaps identificados (ordenados por impacto)

#### 🔴 Crítico — sin esto el self-hosting es doloroso

**1. Pattern matching sobre `rune` (no solo `omen`)**

Hoy `judge` solo acepta como sujeto `omen`, `bool`, `int`, `string`, `char`. Para recorrer un AST, el 90% de los casos son variantes de `omen` (bien), pero cuando un nodo es un `rune` con campos (p. ej. `BinaryExpr(op, left, right)`) no hay forma de desestructurarlo en el `when`. Habría que escribir:

```pengu
# Hoy: verboso
when node.kind == ExprKind.Binary:
    let op is node.binary_op
    let left is node.binary_left
    ...
```

**Propuesta:** extender `judge` para aceptar `rune` como sujeto y permitir `when <RuneName> with a, b, c ->`:

```pengu
judge node:
    when BinaryExpr with op, left, right -> calling visit_binary with op, left, right
    when Literal with value -> calling visit_literal with value
    else -> panic "unknown node"
```

Esto es el cambio #1 más rentable para self-hosting.

**2. Arena / pool allocator (`std.arena`)**

Un compilador asigna miles de nodos AST, entradas de tabla de símbolos y strings temporales. Liberar cada uno con `banish` es inviable y propenso a fugas. Necesitas un asignador de arena:

```pengu
var arena as Arena is calling arena.new with 1_048_576   # 1 MB
defer calling arena.free with (sigil of arena)
var node as ref to Expr is calling arena.alloc of Expr
# ... todos los nodos viven hasta que la arena se libera de golpe
```

Sin esto, el compilador autohospedado será un desastre de fugas. `std.memoria` no lo cubre hoy.

**3. String builder eficiente (`std.builder`)**

Codegen produce C concatenando fragmentos. Hoy `"{a}{b}"` asigna un buffer nuevo cada vez → O(n²) para un `bundle.c` de miles de líneas. La guía recomienda `list of string` + `join`, pero eso tampoco es lo ideal.

**Propuesta:** un tipo `StringBuilder` en `std.builder` con `append`, `append_char`, `append_int`, `append_string`, `finish`:

```pengu
var sb as StringBuilder is calling builder.new
calling sb.append with "int main() {\n"
calling sb.append with "    return 0;\n"
calling sb.append with "}\n"
var code as string is calling sb.finish   # un solo banish al final
```

Mejor aún: azúcar de lenguaje `builder { … }` o un operador dedicado. Pero con biblioteca basta para empezar.

**4. Diagnósticos estructurados (`std.diagnostic`)**

El compilador necesita acumular errores con span, severidad, mensaje, help, note. Hoy `std.whisper` es logging, no diagnósticos. Necesitas:

```pengu
rune Diagnostic:
    file as string
    line as int
    col as int
    end_col as int
    severity as Severity
    code as string
    message as string
    help as maybe string
    note as maybe string

rune DiagnosticBag:
    items as list of Diagnostic
    error_count as int
```

Y un renderizador ANSI que imite el estilo Rust que ya usas (`-->`, `^`, `help:`).

#### 🟡 Importante — mejora mucho la ergonomía

**5. Closures con captura**

Hoy las lambdas no capturan. Para el checker (visitor pattern) y el LSP (callbacks) sería muy útil:

```pengu
# Deseado
weave walk with node as ref to Expr, f as weave with n as ref to Expr into void into void:
    calling f with node
    for child in calling children_of with node:
        calling walk with child, f
```

Actualmente hay que pasar contexto explícitamente por parámetro, lo cual es viable pero verboso. **No es bloqueante**, es mejora.

**6. `type of x` / reflexión de tipos**

Para el checker, a veces necesitas inspeccionar el tipo de una expresión sin conocerlo. Hoy hay `size of T`, pero no `type of expr`. Podría ser un `omen TypeKind` + una función `typeof` que devuelva un `TypeInfo`. No es bloqueante pero sí molesto si no está.

**7. Etiquetas en `break` / `continue`**

Para parsers con bucles anidados, viene bien:

```pengu
outer: for line in lines:
    for ch in line:
        if ch == ';':
            continue outer
```

Hoy `break`/`continue` solo afectan al bucle más interno. Se puede trabajar con banderas, pero es ruido.

**8. Views de string (`string_view`)**

Para lexer sin copiar: `slice of byte` existe, pero un tipo `string_view` (o `slice of char`) con las operaciones de string sería más cómodo. `bytes of s` da `ref to frozen byte`, y `ffi.slice_from_ptr` construye slices, así que es viable hoy; solo sería azúcar.

**9. `donum` extendido a tipos de usuario**

`donum T` requiere que T implemente `Donum`. Está bien, pero para un AST con muchos `rune`, tener que derivar `Donum` en cada uno es ruido. Podría ser automático para runes con todos los campos `Donum`.

#### 🟢 Deseable — calidad de vida

**10. Macros / quote-unquote**

Para codegen, generar C con plantillas sería enorme:

```pengu
# Deseado
let c is quote:
    int ${name}(${params}) {
        ${body}
    }
```

Pero esto es un cambio grande. **Diferible a 3.1** si 3.0 ya es self-hosted.

**11. Tipos asociados en concepts**

Ya está marcado como diferido en §11.7. Para iteradores genéricos en el compilador (recorrer ASTs) sería útil, pero se puede vivir sin ellos usando `list of T` explícitos.

**12. Async/await para LSP**

El LSP necesita concurrencia. `std.filum` da hilos, lo cual es suficiente. Async/await sería más limpio pero no bloqueante.

### 1.3 Ajustes menores de sintaxis

**13. `for x in col then expr` — permitir bindings múltiples**

Hoy solo un binding. Para recorrer mapas con índice sería útil `for k, v in m then …`. Ya existe en `for` sentencia; extenderlo a comprehensions sería coherente.

**14. `with:` en `return` / `let` sin anotación**

Hoy `return with:` infiere el tipo del `into` del weave. Bien. Pero `let x is with:` no infiere sin anotación. Podría inferirse del campo al que se asigna (si es un `set .field is with:`). Ya está resuelto en §18. Solo mencionarlo por si acaso.

**15. `or:` como expresión en más posiciones**

Hoy `or:` funciona en argumentos y struct-lits, pero en aritmética requiere paréntesis. Es razonable, pero documentarlo mejor.

### 1.4 Resumen de cambios de sintaxis propuestos

| # | Cambio | Prioridad | Impacto |
|---|---|---|---|
| 1 | `judge` sobre `rune` con destructuring | 🔴 Crítico | AST traversal limpio |
| 2 | `std.arena` (biblioteca) | 🔴 Crítico | Memoria del compilador |
| 3 | `std.builder` (biblioteca) | 🔴 Crítico | Codegen O(n) |
| 4 | `std.diagnostic` (biblioteca) | 🔴 Crítico | Errores del compilador |
| 5 | Closures con captura | 🟡 Importante | Visitors, LSP |
| 6 | `type of expr` | 🟡 Importante | Checker |
| 7 | Labels en `break`/`continue` | 🟡 Importante | Parsers |
| 8 | `string_view` | 🟡 Importante | Lexer sin copias |
| 9 | `donum` automático en runes | 🟢 Deseable | Menos ruido |
| 10 | Macros / quote-unquote | 🟢 Deseable (3.1) | Codegen |
| 11 | Tipos asociados | 🟢 Deseable (3.1) | Iteradores |
| 12 | Async/await | 🟢 Deseable (3.1) | LSP |

---

## Parte 2 — Librerías necesarias para self-hosting

### 2.1 Lo que ya tienes

| Módulo | Cubre |
|---|---|
| `std.spark` | I/O básica, print, parse_int/float |
| `std.scrolls` | Manipulación de strings |
| `std.archivum` | Archivos, directorios, symlinks |
| `std.cipher` | Base64/Hex/Base32, JSON básico |
| `std.chronicle` | Tiempo, fechas, timers |
| `std.rites` | Procesos, env, argv, exec/spawn |
| `std.whisper` | Logging |
| `std.filum` | Hilos, mutex, canales, atómicos |
| `std.memoria` | Alloc/free de bajo nivel |
| `std.tally` / `std.atlas` / `std.coven` | Colecciones |
| `std.loom` | Pipelines de secuencias |
| `std.oracle` | Maybe/Result helpers |
| `std.invoke` | CLI parsing |
| `std.ffi` | Puente C |
| `std.ledger` | CSV/TSV |
| `std.numerus` / `std.integrum` / `std.fractio` / `std.littera` / `std.logica` | Métodos primitivos |
| `std.compass` | Rutas |
| `std.lot` | PRNG |
| `std.ward` / `std.trial` | Aserciones / tests |
| `std.arithmancy` | Matemáticas avanzadas |

### 2.2 Librerías **puras** de PenguScript que faltan

Estas son las que hay que escribir **en PenguScript** para que el compilador autohospedado las use:

| Biblioteca | Propósito | Complejidad | Prioridad |
|---|---|---|---|
| `std.arena` | Asignador de arena (alloc/free en bloque) | Media | 🔴 Crítico |
| `std.builder` | StringBuilder eficiente | Baja | 🔴 Crítico |
| `std.diagnostic` | Diagnósticos con span, severidad, render ANSI | Media | 🔴 Crítico |
| `std.unicode` | Decodificación UTF-8, codepoints, categorías | Alta | 🟡 Importante |
| `std.regex` | Expresiones regulares (o un matcher simple) | Alta | 🟡 Importante |
| `std.graph` | Algoritmos de grafos (dependencias, dominadores) | Media | 🟡 Importante |
| `std.bitset` | Bitsets para dataflow analysis | Baja | 🟡 Importante |
| `std.json` | JSON completo (más allá del básico de cipher) | Media | 🟡 Importante (LSP) |
| `std.jsonrpc` | Framing JSON-RPC para LSP | Baja | 🟡 Importante (LSP) |
| `std.incremental` | Cache de compilación por hash | Media | 🟢 Deseable |
| `std.sourcemap` | Mapa línea/col ↔ offset | Baja | 🟡 Importante |
| `std.span` | Span, posición, rango | Baja | 🔴 Crítico |
| `std.lexer` | Lexer combinatorio genérico | Media | 🟢 Deseable |
| `std.parser` | Parser combinatorio / Pratt | Alta | 🟢 Deseable |
| `std.cst` | Concrete Syntax Tree con trivia | Media | 🟢 Deseable (fmt) |

**Nota:** `std.arena` y `std.builder` podrían implementarse con `std.memoria` + `antiquus` si hace falta rendimiento, pero la API pública debe ser PenguScript puro.

### 2.3 Bindings de C que podrían necesitarse

Para el **compilador** en sí, sorprendentemente pocos:

| Binding | Propósito | ¿Realmente necesario? |
|---|---|---|
| Compilador C | Invocar `gcc`/`clang`/`tcc` | No — `std.rites.exec` basta |
| `libc` | syscalls, archivos, memoria | No — `std.archivum` + `std.memoria` cubren |
| `termios` | Modo raw para REPL | Solo si haces REPL |
| `readline` | Historial en REPL | Solo si haces REPL |
| `libclang` | Para `pengu bind` | No — el bind actual usa pycparser; en PenguScript habría que escribir un parser de C |

Para el **LSP**:

| Binding | Propósito | ¿Necesario? |
|---|---|---|
| `libuv` / `libevent` | Async I/O | No — `std.filum` + stdio basta |
| `inotify` / `kqueue` / `ReadDirectoryChangesW` | File watching | No — polling con `std.archivum` es suficiente |
| `zlib` | Compresión (no crítico) | No |

**Conclusión:** el compilador autohospedado **no necesita bindings C nuevos**. Todo lo que necesita se puede hacer con `std.rites` (procesos), `std.archivum` (archivos), `std.filum` (hilos) y `std.memoria` (memoria). Esto es una gran noticia para el self-hosting: menos superficie de C, menos portabilidad que resolver.

### 2.4 Herramientas de desarrollo

Para el propio desarrollo del compilador en PenguScript necesitarás:

| Herramienta | ¿En PenguScript? | Notas |
|---|---|---|
| Formateador (`pengu fmt`) | Sí | Usa `std.cst` + `std.builder` |
| Doc generator (`pengu doc`) | Sí | Usa `std.json` para el índice HTML |
| Bind generator (`pengu bind`) | Sí | Requiere un parser de C — alta complejidad |
| LSP | Sí | `std.jsonrpc` + `std.filum` |
| Test runner (`pengu test`) | Sí | Ya tienes `std.trial` |
| Benchmark (`pengu benchmark`) | Sí | `std.chronicle` |
| Package manager (`pengu add`) | Sí | `std.rites` + git CLI |

`pengu bind` es el más complejo porque parsear cabeceras C es un proyecto en sí mismo. **Recomendación:** mantener `pengu bind` en Python o como binding a `libclang` durante 3.0, y diferir su reescritura a 3.1.

### 2.5 Resumen de librerías

```
Críticas (escribir primero):
  std.span         — posición, rango, span
  std.arena        — asignador de arena
  std.builder      — StringBuilder
  std.diagnostic   — diagnósticos + render ANSI

Importantes (escribir en 3.0):
  std.unicode      — UTF-8, codepoints
  std.regex        — regex o matcher
  std.bitset       — bitsets
  std.graph        — grafos
  std.json         — JSON completo
  std.jsonrpc      — JSON-RPC framing
  std.sourcemap    — línea/col ↔ offset
  std.cst          — CST con trivia (para fmt)

Deseables (3.1):
  std.lexer        — lexer combinatorio
  std.parser       — parser combinatorio
  std.incremental  — cache incremental
```

---

## Parte 3 — Roadmap sugerido para 3.0

### Fase 0 — Cerrar sintaxis (2-4 semanas)

1. **Extender `judge` a `rune`** con destructuring (§1.2 #1). Es el cambio más rentable.
2. **Etiquetas en `break`/`continue`** (§1.2 #7). Cambio pequeño.
3. **`type of expr`** si se decide incluir (§1.2 #6).
4. **Aprobar `donum` automático** en runes (§1.2 #9).
5. **Documentar `with:` en más posiciones** y pulir la spec.
6. **Decidir closures**: ¿3.0 o 3.1? Si 3.0, es un cambio mayor.

### Fase 1 — Librerías base (1-2 meses)

1. `std.span`, `std.sourcemap`
2. `std.arena`
3. `std.builder`
4. `std.diagnostic`
5. `std.unicode`
6. `std.json` completo
7. `std.jsonrpc`

### Fase 2 — Compilador autohospedado (3-6 meses)

1. **Lexer** en PenguScript (probablemente manual, no generado)
2. **Parser** — decidir: manual recursive descent vs Pratt vs combinatorio. Dado que no hay closures, recursive descent manual es lo pragmático.
3. **AST** con `rune` + `omen` algebraico + `cyclus`.
4. **Checker** con `concept` + `bind` para visitors.
5. **Codegen** con `std.builder`.
6. **Driver** con `std.rites` para invocar el C compiler.

### Fase 3 — Herramientas (2-3 meses)

1. `pengu fmt` en PenguScript
2. `pengu doc` en PenguScript
3. `pengu lsp` en PenguScript
4. `pengu test` en PenguScript (ya está casi)
5. **`pengu bind` se queda en Python** en 3.0, o se hace binding a `libclang`.

### Fase 4 — Bootstrap (1-2 meses)

1. Compilar el compilador con el compilador viejo (Python).
2. Verificar que el output es idéntico al del viejo.
3. Compilar el compilador con el compilador nuevo (self-compile).
4. Verificar que el output es idéntico otra vez (fixed-point).
5. Eliminar el compilador Python.

---

## Conclusión

**Sintaxis:** el lenguaje está sorprendentemente cerca de ser self-hostable. El único gap crítico de sintaxis es `judge` sobre `rune` con destructuring. Los demás son mejoras de ergonomía. Las closures son la decisión más grande: sin ellas se puede escribir el compilador (con visitors manuales), con ellas es más limpio.

**Librerías:** necesitas 4 críticas (`span`, `arena`, `builder`, `diagnostic`), ~8 importantes (`unicode`, `regex`, `bitset`, `graph`, `json`, `jsonrpc`, `sourcemap`, `cst`), y ~3 deseables. **Ningún binding C nuevo es necesario** para el compilador en sí; todo se puede hacer con lo que ya tienes (`std.rites`, `std.archivum`, `std.filum`, `std.memoria`). Esto es una gran ventaja para la portabilidad.

**Recomendación de orden:**
1. Extender `judge` a `rune` (bloqueante para AST traversal limpio).
2. Escribir `std.span` + `std.arena` + `std.builder` + `std.diagnostic` (bloqueantes para el compilador).
3. Decidir closures (sí/no en 3.0).
4. Empezar el lexer + parser en PenguScript.
5. Dejar `pengu bind` en Python para 3.0; reescribir en 3.1 con `libclang` o parser propio.

¿Quieres que profundice en alguna de estas áreas? Por ejemplo, puedo:
- Diseñar la sintaxis exacta para `judge` sobre `rune`.
- Diseñar la API de `std.arena` / `std.builder` / `std.diagnostic`.
- Analizar cómo sería el AST del compilador en PenguScript (con ejemplos de código).
- Comparar opciones para el parser (recursive descent vs Pratt vs combinatorio sin closures).
