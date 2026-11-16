# Plan del compilador PenguScript 0.6.0

> **Estado:** plan de ingeniería, no implementación.
> **Spec normativa:** [`docs/LANGUAGE.md`](../docs/LANGUAGE.md), `0.6.0`.
> **CLI:** [`scratch/CLI_PLAN.md`](CLI_PLAN.md), `0.1.0`.
> **Fecha:** 2026-11-12.
> **Regla:** el backend Rust es invisible; ningún tipo, atributo ni error crudo de Rust puede aparecer en la superficie.

---

## Índice

1. [Resumen y contrato](#1-resumen-y-contrato)
2. [Arquitectura](#2-arquitectura)
3. [Fase 1 — Frontend](#3-fase-1--frontend)
4. [Fase 2 — Checker semántico y de ownership](#4-fase-2--checker-semántico-y-de-ownership)
5. [Fase 3 — Lowering, codegen y build/run](#5-fase-3--lowering-codegen-y-buildrun)
6. [Librerías externas, licencias y auto-hospedaje](#6-librerías-externas-licencias-y-auto-hospedaje)
7. [Hitos, dependencias y puertas de calidad](#7-hitos-dependencias-y-puertas-de-calidad)
8. [Estrategia de pruebas](#8-estrategia-de-pruebas)
9. [Riesgos y puntos de spec cerrados](#9-riesgos-y-puntos-de-spec-cerrados)
10. [Ruta de auto-hospedaje](#10-ruta-de-auto-hospedaje)
11. [Apéndices](#11-apéndices)

---

## 1. Resumen y contrato

### 1.1 Objetivo

Construir un compilador real para **todo** PenguScript `0.6.0`:

- **Fase 1 Frontend:** fuente → tokens → CST/AST → árbol de items y módulos, con recuperación de errores y spans.
- **Fase 2 Checker:** resolución de nombres, tipos, genéricos, pacts, patrones, const eval y **ownership/borrowing**; produce HIR tipado y diagnósticos `PGS-*`.
- **Fase 3 Backend:** HIR → LIR → Rust generado → `Cargo.toml` → `rustc`/`cargo` → binario, con source maps y remapeo de errores.

No es un transpilador de conveniencia: el programa PenguScript se valida **antes** de generar Rust. El código Rust es un artefacto interno, no editable y no estable.

### 1.2 Restricciones duras

1. **Sin dependencias obligatorias en el núcleo semántico.** El compilador debe poder portarse a PenguScript; las librerías Rust son bootstrap, no arquitectura.
2. **Sin `dyn`, async, hilos, macros de usuario ni `unsafe` general** en la superficie. El backend puede usar `unsafe`/`dyn` internamente, pero el usuario nunca los ve.
3. **Sin lifetimes escritas.** `&T`/`&mut T` solo en params, locales y bindings locales; el checker infiere y prohíbe escapes.
4. **Presupuesto de diagnósticos.** El catálogo tiene 160 códigos y un límite de 160. `PGS-E1901` es el único código nuevo de F2 (error sintáctico); el checker no añade códigos: mapea a uno existente o abre una decisión de spec. No se inventa `PGS-E9999`.
5. **Sin filtrar Rust.** Ni `rustc` ni `Cargo` aparecen en diagnósticos de usuario salvo como nota de backend; todo error se remapea o cae en `PGS-E2014`.
6. **Determinismo.** Mismas entradas → mismos diagnósticos, mismo orden, mismo binario lógico. Nada de iterar `HashMap` sin ordenar.
7. **Auto-hospedaje desde el diseño.** Cada crate y algoritmo debe ser expresable en el subconjunto PenguScript de 0.6.0.

### 1.3 No objetivos de v1

- No implementar un backend nativo propio: Rust sigue siendo el backend.
- No implementar `abi "js"` (diferido).
- No implementar exportación de funciones PenguScript a C.
- No implementar `std.concurrent` dentro del compilador; el compilador es single-thread.
- No implementar un linker propio.
- No prometer ABI estable, layout estable ni reproducibilidad byte a byte del binario Rust antes de H5.

### 1.4 Definición de “terminado”

El compilador está terminado para 0.6.0 cuando:

- todos los ejemplos normativos de `LANGUAGE.md` se parsean y checkean;
- cada código de diagnóstico tiene al menos un test negativo;
- todo programa aceptado genera Rust que compila con `rustc 1.85+`, edición 2024;
- `pengu check` no invoca Cargo; `pengu build`/`run` sí;
- el corpus de tests diferenciales no produce errores crudos de Rust;
- el compilador puede compilar su propio subconjunto (H3/H4);
- la matriz de garantías §21 se cumple en tests.

---

## 2. Arquitectura

### 2.1 Capas

```text
pengu-vfs        snapshots de archivos, overlays, cambios
pengu-span       FileId, Span, SourceMap, líneas/columnas
pengu-diag       Diagnostic, Severity, render humano/JSON, fix-it
pengu-syntax     lexer, CST, AST, parser, módulos sintácticos
pengu-hir        HIR, DefId, resolución de nombres, scopes
pengu-types      Ty, inferencia, unificación, bounds, const eval
pengu-check      ownership, préstamos, exhaustividad, FFI checks
pengu-lower      HIR tipado -> LIR, monomorfización
pengu-codegen    LIR -> Rust, runtime, sourcemap
pengu-driver     sesión, pipeline, cache, Cargo, rustc, build/run
pengu-pkg        Tome.toml, Tome.lock, git, cache, vendor
pengu-os         paths, procesos, terminal, plataforma
```

`pengu-cli`, `pengu-lsp`, `pengu-fmt`, `pengu-lint`, `pengu-doc`, `pengu-test`, `pengu-bindgen` consumen estas capas; no las reimplementan.

### 2.2 Corrección de dependencias

El `CLI_PLAN.md` decía `pengu-diag -> pengu-syntax` y `pengu-syntax -> pengu-diag`, un ciclo. Se corrige:

```text
pengu-span  <-  pengu-syntax
pengu-span  <-  pengu-diag
pengu-syntax + pengu-diag  <-  pengu-hir
pengu-hir + pengu-diag     <-  pengu-types
pengu-types + pengu-diag   <-  pengu-check
pengu-check + pengu-diag   <-  pengu-lower
pengu-lower + pengu-diag   <-  pengu-codegen
pengu-driver orquesta todas
```

Ningún crate semántico depende de `pengu-cli`, `pengu-lsp` ni de Cargo.

### 2.3 Pipeline

```text
Tome.toml + .pengu
      |
      v
  pengu-vfs  ->  SourceDb (FileId, texto, hash)
      |
      v
  pengu-syntax: lexer -> tokens -> parser -> CST/AST
      |                                   |
      |                                   +-> SyntaxError (recuperable)
      v
  pengu-hir: módulos, imports, resolución, DefId, bodies
      |
      v
  pengu-types: Ty, inferencia, bounds, const eval
      |
      v
  pengu-check: ownership, borrows, patrones, FFI, garantías
      |
      +--> si hay errores: stop; no se genera Rust
      |
      v
  pengu-lower: LIR monomorfizado
      |
      v
  pengu-codegen: Rust + Cargo.toml + sourcemap.json + runtime
      |
      v
  pengu-driver: cargo/rustc -> binario; remapeo de diagnostics
```

### 2.4 Sesión y queries

No se usa Salsa ni un framework de incrementalidad con macros. Se implementa una sesión propia:

```rust
struct Session {
    vfs: Vfs,
    sources: SourceDb,
    syntax: Cache<FileId, Arc<SyntaxTree>>,
    hir: Cache<CrateId, Arc<Hir>>,
    types: Cache<BodyId, Arc<TypeInfo>>,
    check: Cache<CrateId, Arc<CheckResult>>,
    lower: Cache<CrateId, Arc<Lir>>,
    codegen: Cache<BuildKey, Arc<GeneratedCrate>>,
    revision: u64,
}
```

- Cada query devuelve `Arc<T>` y registra dependencias.
- Un cambio invalida por `FileId`/`BodyId`, no todo el proyecto.
- La API pública para LSP es síncrona y no bloquea; el CLI decide si usar worker.
- `SourceDb` conserva texto, line index y hash; un `Span` es `(FileId, start, end)` con offsets UTF-8.
- `SourceMap` traduce offset -> línea/columna (1-based para usuario, 0-based interno).

### 2.5 Modelo de spans

- `Span { file: FileId, start: u32, end: u32 }`; `DUMMY` para sintético.
- `Spanned<T>` en AST/HIR.
- `NodeId` estable por árbol; `DefId` global por crate.
- Todo diagnóstico tiene un `primary` span y cero o más `labels`.
- Todo nodo generado en codegen tiene un `Origin` que apunta a un `Span` o a un `DefId` contenedor.

---

## 3. Fase 1 — Frontend

**Objetivo:** aceptar todo el lenguaje 0.6.0 y producir un CST/AST lossless con errores recuperables. No hay tipos ni ownership.

### 3.1 Hitos

| Hito | Entrega | Criterio |
|---|---|---|
| F0 ✅ | workspace, `pengu-span`, `pengu-vfs`, `pengu-diag` | Completado 2026-11-12: 23 tests verdes, sin dependencias externas |
| F1 ✅ | lexer completo | Completado 2026-11-12: 39 tests del lexer (38 unitarios + corpus), 62 tests de workspace; tokens, indentación, strings/interpolación y diagnósticos E1001–E1011 |
| F2 ✅ | parser de expresiones | Completado 2026-11-12: Pratt §14.1, AST de expr/tipos/patrones/bloques, bindings tipados, tipos de función, `Self`, `PGS-E1901`, referencias, campos de tupla, formas inline/bloque estrictas; 84 tests de parser; 149 tests de workspace |
| F3 ✅ | parser de items y módulos | Completado 2026-11-12: items/programa y `.d.pengu`; 15 tests de programa, 3 de declaraciones; 105 tests de parser; 167 de workspace |
| F4 ✅ | CST/AST + recuperación | Completado 2026-11-12: `SyntaxTree` lossless con `SyntaxKind`/`SyntaxNode`/`SyntaxToken`/`SyntaxElement`, trivia y espacios sintéticos, `ParsedProgram.tree`/`ParsedDeclaration.tree`/`ParsedExpr.tree`, tope de 100 diagnósticos, `reconstruct()` exacto, nodos con spans iguales y `node_at()`; 15 tests de CST |
| F5 ✅ | corpus de sintaxis | Completado 2026-11-12: `spec_corpus.rs` parsea los 146 bloques `pengu` de la spec; 141 válidos y 5 marcados `-- ERROR PGS-`; soporte de `match` con `then`+bloque, record update `..base`, variantes `some/none/ok/err`, `bind` con bloque implícito y `unveil(tome)`/`unveil(scroll)`; 1 test de corpus |
| F6 ✅ | fuzz, límites, documentación | Completado 2026-11-13: límites 10 MiB/10 000 líneas/profundidad 1000 con `PGS-E1901`, smoke de 10M tokens léxicos y 128 fuentes aleatorias sin pánico, `format_source`/`reconstruct` desde CST, `docs/FRONTEND.md`; 5 tests de límites, 3 de fuzz, 3 de formato; 228 tests de workspace |
| Gate F ✅ | congelar sintaxis | 146 bloques (141 válidos + 5 `ERROR PGS-`), todas las producciones §19 con parser+test, recuperación con spans y tope 100, fuzz 10M sin pánico, CST reconstruible; no se acepta cambio de gramática sin test |

### 3.2 `pengu-vfs` y `pengu-span`

- `Vfs` con `HashMap<PathBuf, FileId>`, overlays para LSP, normalización de rutas.
- `SourceFile { path, text: Arc<str>, line_starts: Vec<u32>, hash: [u8; 32] }`.
- `line_starts` se calcula una vez; `line_col` por bisección.
- `SourceMap` para codegen: `generated_file -> Vec<Mapping>`.
- Un `FileId` es estable dentro de una sesión; el path es la clave externa.

### 3.3 Lexer

#### 3.3.1 Entrada

- UTF-8 estricto; BOM `EF BB BF` -> `PGS-E1001`.
- CRLF -> LF; CR suelto se trata como LF.
- Tabs fuera de string/comentario -> `PGS-E1002`.
- Indentación: solo espacios; 4 por nivel; no múltiplo -> `PGS-E1003`.

#### 3.3.2 Indentación

Algoritmo:

```text
stack = [0]
at_line_start = true
for each physical line:
    if blank or only comment: emit comment/trivia; continue
    count leading spaces; if tab -> error
    if in_string/comment: consume; continue
    if at_line_start:
        if count > stack.top: emit INDENT; push(count)
        while count < stack.top: emit DEDENT; pop()
        if count != stack.top: error E1004
    lex tokens until NEWLINE
    emit NEWLINE
emit DEDENT for all open levels; emit EOF
```

Reglas:

- `NEWLINE` dentro de `()`, `[]`, `{}` no genera INDENT/DEDENT; el parser lo ignora.
- Un `NEWLINE` tras operador binario con línea más indentada continúa la expresión (§2.6).
- Línea en blanco no cierra bloque.
- `DEDENT` se emite antes del primer token de la línea.

#### 3.3.3 Tokens

| Grupo | Tokens |
|---|---|
| Literales | `INT`, `FLOAT`, `CHAR`, `BYTE_CHAR`, `STRING`, `RAW_STRING`, `BYTE_STRING`, `C_STRING`, `TRUE`, `FALSE`, `NONE` |
| Identificadores | `IDENT` (XID_Start/`_` + XID_Continue); keywords cerradas |
| Items | `RUNE`, `ENCHANTING`, `PACT`, `RITUAL`, `ESSENCE`, `SCROLL`, `SUMMON`, `UNVEIL`, `GRIMOIRE`, `FOREIGN`, `CURSE`, `ABI`, `PTR` |
| Bindings | `BIND`, `MORPH`, `SIGIL`, `RELIC` |
| Control | `IF`, `ELSEIF`, `ELSE`, `UNLESS`, `MATCH`, `WHEN`, `THEN`, `FOR`, `WHILE`, `LOOP`, `BREAK`, `CONTINUE`, `RETURN`, `DO` |
| Operadores | `AND`, `OR`, `NOT`, `IS`, `ISNT`, `IN`, `AS` |
| Puntuación | `(`, `)`, `[`, `]`, `{`, `}`, `,`, `;`, `:`, `.`, `..`, `..=`, `->`, `=>`, `=`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `+`, `-`, `*`, `/`, `%`, `?`, `@`, `@mut`, `@own`, `@@`, `::`, `|` |
| Trivia | `NEWLINE`, `INDENT`, `DEDENT`, `DOC_OUTER` (`---`), `DOC_INNER` (`--!`), `COMMENT`, `EOF` |

`@@` se lexea como token de atributo en cualquier posición; el parser lo restringe a inicio de línea/antes de `test`/`derive` y produce el error sintáctico fuera de contexto. `;` se lexea siempre, pero el parser solo lo acepta en `[expr; N]` y `[T; N]`, nunca como separador de sentencias. La implementación agrupa strings como `String(StringKind)`/`StringStart(StringKind)` y comentarios como `Comment(CommentKind)`, en vez de variantes separadas por tipo. `INDENT`/`DEDENT` son significativos para el parser, aunque se agrupen bajo “Trivia” en esta tabla.

#### 3.3.4 Strings y chars

- Normal `"..."`: escapes `\n`, `\r`, `\t`, `\\`, `\"`, `\'`, `\0`, `\xNN`, `\u{...}`; interpolación `#{expr}`; `\#{` literal.
- Triple `"""..."""`: multilínea; indenta según el cierre; interpola.
- Raw `r"..."` / `r#"..."#`: sin escapes ni interpolación; el `#` permite comillas.
- Byte `b"..."`: bytes ASCII/`\xNN`; byte char `b'P'`.
- C `c"..."`: string C; se convierte a `CStr` en FFI; no admite NUL interno.
- Char `'P'`, `'\n'`, `'\u{...}'`; exactamente un scalar Unicode.
- `PGS-E1005` string sin cerrar; `E1006` char sin cerrar; `E1007` escape desconocido; `E1008` byte char no ASCII; `E1009` comentario de bloque sin cerrar.

#### 3.3.5 Interpolación

El lexer no evalúa `#{...}`: emite un token `STRING_START`, segmentos literales y `INTERP_START`/`INTERP_END` con sub-tokens delimitados por `{}` balanceados. El parser construye `Expr::InterpolatedString`. La interpolación se permite solo en strings normales/triple; no en raw/byte/C.

#### 3.3.6 Tests del lexer

- Corpus de todos los literales de §2.5.
- Indentación: 0/1/2/3/4/5/8 espacios, tabs, líneas vacías, comentarios.
- Strings: escapes, Unicode, interpolación anidada, raw, byte, C, sin cierre.
- Fuzz: bytes aleatorios UTF-8; no panic, no bucle infinito; siempre EOF.
- Snapshot de tokens por archivo.

Implementado en F1: 39 tests (38 unitarios + corpus de los 146 bloques `pengu` de la spec), incluyendo corpus de literales, anchos de indentación 0/1/2/3/4/5/8, comentarios de bloque, interpolación anidada, spans absolutos, CRLF/BOM y fuzz determinista. `cargo test --workspace` = 62 tests.

### 3.4 Parser

#### 3.4.1 Estrategia

- Descenso recursivo para items, tipos, patrones y sentencias.
- Pratt para expresiones, con binding powers de §14.1.
- Parser de dos modos: `.pengu` normal y `.d.pengu` (`decl_file`).
- CST lossless: cada token, incluido trivia, tiene un nodo; el AST es una vista tipada sobre el CST.
- Recuperación: en error, crear `ERROR` node, consumir hasta `NEWLINE`/`DEDENT`/un token de sincronización; máximo 100 errores por archivo.

#### 3.4.2 Binding powers

| Nivel | Operador | BP izquierdo | BP derecho |
|---|---|---|---|
| 11 | `=` | — | sentencia, no expresión |
| 10 | `or` | 10 | 11 |
| 9 | `and` | 20 | 21 |
| 8 | `==`, `!=`, `is`, `isnt`, `in` | 30 | 31 |
| 7 | `<`, `<=`, `>`, `>=` | 40 | 41 |
| 6 | `..`, `..=` | 50 | 51 |
| 5 | `+`, `-` | 60 | 61 |
| 4 | `*`, `/`, `%` | 70 | 71 |
| 3 | `as` | 80 | 81 |
| 2 | unario `-`, `not` | 90 | 90 |
| 1 | postfix `.`, `()`, `[]`, `?` | 100 | — |

`as` es postfix con tipo; `?` es postfix; no hay `**`. Comparaciones encadenadas: el parser las representa asociativas a la izquierda y el checker emite `PGS-E1408` si ve más de una.

Implementado en F2: `ast.rs` con `Expr`, `Type`, `Pattern`, `Stmt`, `Block`; `parser.rs` con Pratt, primarios, postfix, control, bloques, tipos y patrones; `parse_expression` devuelve `ParsedExpr`. Errores de sintaxis usan `PGS-E1901`. Tests: precedencia completa, postfix, colecciones, lambdas, `if`/`unless`/`match`/`do`/`loop`/`curse`, patrones, tipos, spans y errores.

#### 3.4.3 Items

| Producción | Función | Notas |
|---|---|---|
| `scroll` | `parse_scroll` | inline o archivo; `unveil` |
| `summon` | `parse_summon` | path, alias, glob |
| `rune` | `parse_rune` | campos, `unveil`, genéricos, `@@derive` previo |
| `enchanting` | `parse_enum` | variantes unit/named/tuple |
| `pact` | `parse_pact` | métodos con/sin cuerpo, superpact |
| `ritual` | `parse_impl` | inherente o `for`, genéricos |
| `essence` | `parse_type_alias` | alias; sin `where` |
| `foreign` | `parse_foreign` | solo firmas |
| función | `parse_function` | `IDENT = [T](...) -> T` + bloque |
| `sigil`/`relic` | `parse_const` | tipo + `=` expr |
| `grimoire` | `parse_main` | `: Type` opcional |
| `@@test` | `parse_test` | opciones `should_panic`, `ignore` |
| `@@derive` | `parse_derive` | solo antes de `rune`/`enchanting` |

Un item solo se acepta en módulo, `pact` o `ritual`; `statement` no incluye items (`PGS-E6001` no; el parser emite error sintáctico y el checker lo clasifica).

#### 3.4.4 Expresiones

`parse_expr` -> `parse_or` -> ... -> `parse_unary` -> `parse_postfix` -> `parse_primary`.

`primary`:

- literales;
- path;
- `(` expr `)` y tuplas;
- arrays `[ ... ]` y repeat `[e; N]`;
- `Map[ ... ]` y `{ ... }` (map);
- `Vec[ ... ]`, `Set[ ... ]`;
- `if`/`unless`/`match`/`do`/`loop`/`curse`;
- lambda `(params) => expr|bloque`;
- `@`, `Self` (contextual).

Ambigüedades:

- `(`: tupla, agrupación o lambda. Se decide por lookahead: si tras `)` viene `=>`, es lambda; si hay coma, tupla; si no, agrupación.
- `[`: array/repeat/slice; en expresión solo array/repeat; en tipo array/slice.
- `Map[`/`Vec[`/`Set[`: si el identificador es exactamente ese y sigue `[`, es literal; si no, path/índice.
- `@`: receptor solo si sigue a `=` en cabecera de método o es patrón `name @ pattern`; en expresión `@` es self.
- `-`: unario o binario según posición.
- `not`: prefijo; no `!`.

#### 3.4.5 Sentencias y bloques

- `block ::= statement+`; el parser exige al menos una sentencia; un bloque vacío es error sintáctico (usar `do` no cambia).
- `binding`: `bind|morph pattern = expr (else block)?`.
- `assignment`: `expr = expr` solo si el LHS es place; el parser lo deja al checker.
- `while`/`for`: `do` opcional; cuerpo obligatorio.
- `return` sin expresión; `break` con expresión opcional; `continue` sin expresión.
- `match` es expresión; sus brazos usan `when`/`then` o bloque.
- `if`/`unless` son expresiones; en posición de sentencia se descarta el valor.
- No hay `;`; un `;` es error léxico/sintáctico.
- No hay labels de bucle.

#### 3.4.6 Patrones

- Literales, `_`, ident, `ident @ pattern`, tupla, path con campos, path unitario, alternativa `|`, rango, slice, `..`.
- `named_pattern` para records/variantes.
- `bind ... else` exige bloque; el parser no valida divergencia (checker).
- En `for`, el patrón debe ser irrefutable; el checker lo comprueba.

#### 3.4.7 Tipos

- `?T`, `&T`, `&mut T`, `[T; N]`, `[T]`, `()`, `(T,)`, `(T, U)`, `path`, `path[args]`, `Ptr[T]`.
- `Ptr` solo en contextos de borde; el parser lo acepta y el checker emite `PGS-E2025` fuera.
- `N` es una expresión constante; el parser la guarda como `ConstArg`.
- `Self` solo en `pact`/`ritual`.

#### 3.4.8 Módulos y `.d.pengu`

- `scroll` inline: items hasta DEDENT.
- `scroll` archivo: `scroll foo` resuelve `foo.pengu` o `foo/scroll.pengu`; el driver lo carga; si ambos, `PGS-E2013`.
- `summon path (as ident)?`; glob no está en el core (no `*`); el plan no lo añade.
- `.d.pengu`: primera línea `abi "C"|"system"|"js"|"pengu"`; luego `rune`/`enchanting`/`pact`/function/const/summon sin cuerpos; `unveil` prohibido; `grimoire` prohibido.
- `Ptr[T]` solo en `.d.pengu`, `foreign`, `curse`.
- `[declarations]` de `Tome.toml` asocia nombres a archivos.

#### 3.4.9 Atributos

- `@@derive(...)` solo inmediatamente antes de `rune`/`enchanting`; lista cerrada.
- `@@test(...)` solo antes de una función sin parámetros; opciones `should_panic`, `ignore`.
- Cualquier otro `@@` es error; no hay atributos generales.
- El lexer emite `@@`; el parser construye `Attr` y lo adjunta al item.

#### 3.4.10 AST/CST

- `SyntaxKind` enum con kinds de items, bloques, sentencias, expresiones,
  tipos, patrones y tokens; las subexpresiones comparten `Expr`.
- `SyntaxNode { kind, span, children: Vec<SyntaxElement> }`; `SyntaxToken { kind, span, text }`.
- AST tipado: `ast::Item`, `ast::Expr`, `ast::Stmt`, `ast::Pattern`, `ast::Type`.
- Cada nodo AST expone su `span`; el CST se consulta por span con
  `SyntaxTree::node_at(span)`. No se añade un método `syntax()` en F4.
- El CST conserva comentarios y espacios; el AST los ignora.
- `SyntaxTree { root, errors, tokens, source }`.
- Implementado en F4: el CST sintetiza tokens `Whitespace` para los huecos, asigna cada token a un único nodo y `reconstruct()` devuelve el fuente exacto.

#### 3.4.11 Frontend gate

No se pasa a Fase 2 hasta:

- todas las producciones de §19 tienen parser y test;
- todos los ejemplos `pengu` de la spec parsean (o están marcados `error` y producen el código esperado);
- no hay pánicos en fuzz de 10M tokens;
- cada error sintáctico tiene span y recuperación;
- `pengu fmt` puede reconstruir el CST (aunque se implemente después).

#### 3.4.12 F6 — fuzz, límites y documentación

Implementado:

- `pengu-syntax/src/limits.rs`: 10 MiB, 10 000 líneas, profundidad 1000,
  `PGS-E1901` antes de lexear/parsear.
- `tests/fuzz_smoke.rs`: 10M tokens léxicos, 128 fuentes pseudoaleatorias y
  anidamiento extremo, sin pánicos.
- `tests/format.rs` y `pengu-syntax/src/format.rs`: reconstrucción desde CST.
- `docs/FRONTEND.md`: pipeline, recuperación, límites, fuzz y evidencia de
  Gate F.

Gate F queda cerrado para la Fase 1. Cualquier cambio de gramática debe venir
con un test de parser y una actualización de `docs/LANGUAGE.md`.

---

## 4. Fase 2 — Checker semántico y de ownership

**Objetivo:** convertir AST en HIR tipado y demostrar que el programa cumple §4–§16 y §21. Ningún programa inválido llega al backend.

### 4.1 HIR y resolución de nombres

#### 4.1.1 Estructuras

```rust
struct Crate { modules: Vec<Module>, defs: Vec<Def>, bodies: Vec<Body> }
struct Module { id: ModuleId, parent: Option<ModuleId>, items: Vec<ItemId>, scope: ScopeId }
struct Def { id: DefId, kind: DefKind, name: Symbol, vis: Visibility, span: Span }
enum DefKind { Module, Type, Variant, Field, Function, Const, Static, Pact, Impl, Local, Generic }
struct Body { owner: DefId, params: Vec<LocalId>, locals: Vec<LocalDecl>, blocks: Vec<Block>, exprs: Vec<Expr> }
```

- `DefId` global; `LocalId` por body; `ItemId` estable.
- `Res` map: cada `Path`/`Expr` resuelto a `Res::Def`/`Res::Local`/`Res::Primitive`/`Res::Error`.
- Namespaces separados: tipos, valores, módulos; un módulo y un tipo no comparten nombre en el mismo scope (`PGS-E2005`).
- Sin variables globales: `bind`/`morph` en módulo -> `PGS-E1101`; solo `sigil`/`relic`.
- `scroll` y `summon` construyen el grafo de módulos; ciclos -> `PGS-E2012`.
- `unveil`/`unveil(tome)`/`unveil(scroll)` se aplican a items; visibilidad por defecto privada.
- `summon` importa valores/tipos/módulos; alias; duplicados -> `PGS-E2005`; no encontrado -> `PGS-E2004`; privado -> `PGS-E2006`.
- `Self` se resuelve al tipo del `ritual`/`pact`; fuera -> `PGS-E1209`.
- `@`/`@mut`/`@own` solo en receptores y patrones de binding; fuera -> error.
- `Ptr` solo en contextos de borde; `abi` solo en `.d.pengu`.

#### 4.1.2 Módulos y `.d.pengu`

- `main.pengu`/`lib.pengu` raíz; `scroll` archivo con ruta única.
- `.d.pengu` se carga por `[declarations]` o adyacente; `abi` define el backend; `abi "js"` -> `PGS-E2022`; `abi "pengu"` sin implementación -> `PGS-E2024`.
- Un `.d.pengu` no genera cuerpo; sus firmas se usan para FFI/type checking.
- `[link]` de `Tome.toml` se asocia a `foreign`/`abi "C"`; falta -> `PGS-E2023`.
- `foreign` no puede tener cuerpo (`PGS-E1601`); llamada fuera de `curse` -> `PGS-E1602`; exportar -> `PGS-E1606`.

#### 4.1.3 Estado C1 (implementado 2026-11-12)

- Crate `pengu-hir`; `HirCrate`, `Module`, `Def`, `Body`, IDs y namespaces.
- `scroll` anidado y `summon` con alias/valores/tipos/módulos; duplicados,
  no encontrado y privado con `PGS-E2005`/`E2013`/`E2004`/`E2006`.
- Visibilidad `unveil`/`unveil(tome)`/`unveil(scroll)` en AST
  y parser; `can_access` respeta los cuatro niveles.
- `Self` en `pact`/`ritual`; `PGS-E1209` fuera. Valores y tipos de prelude.
- Tests: 20 de `pengu-hir`, **211 de workspace**; clippy/fmt limpios.
- Limitaciones: no carga archivos, no detecta ciclos de módulos, no comprueba
  tipos/ownership; `Body` es HIR de nombres, no HIR tipado. La resolución de
  tipos estructurales (`&T`, arrays, tuplas, fn) usa categorías preliminares.

### 4.2 Representación de tipos

```rust
enum Ty {
    Bool, Int, I8, I16, I32, I64, Isize,
    U8, U16, U32, U64, Usize, F32, F64,
    Char, String, Str, Unit, Never,
    Tuple(Vec<Ty>), Array(Box<Ty>, Const), Slice(Box<Ty>, Mutability),
    Ref(Box<Ty>, Mutability), Ptr(Box<Ty>),
    Vec(Box<Ty>), Map(Box<Ty>, Box<Ty>), Set(Box<Ty>),
    Option(Box<Ty>), Result(Box<Ty>, Box<Ty>),
    Box(Box<Ty>), Rc(Box<Ty>), Arc(Box<Ty>),
    Adt(DefId, Vec<Ty>), Generic(ParamId), Infer(InferVar),
    CStr, CString, Ordering,
}
```

- `Str` es `&str` prestado; `String` owned.
- `Ptr[T]` es tipo de borde, no se almacena/compara.
- `Never` es bottom; unifica con cualquier tipo; no se usa como valor.
- `Unit` es `()`.
- `Option[T]`/`Result[T,E]` son sums de prelude; no redeclarables (`PGS-E8008`).
- `Ordering` es sum de prelude.
- No hay `dyn`, `impl Trait`, asociados, GATs, HRTB, `Pin`, `Future`.

### 4.3 Inferencia

#### 4.3.1 Estado C2 (implementado 2026-11-13)

- Crate `pengu-types`: `Ty`, `Infer` (union-find con `IntVar`/`FloatVar`), `check_crate`, `CheckResult`.
- Cubre literales y sufijos, default `Int`/`Float`, rangos de enteros, firmas/aridad,
  arrays/`Vec`/`Map`/`Set`/tuplas, `bind`/`morph`, control, `loop`/`break`,
  `return`, `?`, `Option`/`Result`, `print`/`format`, `if`/`match`, `Never`,
  `in`, `as`, referencias y campos de tupla.
- `none` sin contexto -> `PGS-E1508`; `err` sin éxito -> `PGS-E1507`;
  `?` fuera de retorno Option/Result -> `PGS-E3007`.
- Tests: 39 de `pengu-types` (C2), 267 de workspace en C2; C3 añade 22 tests y 289 de workspace.
- Límites: records/sums y patrones complejos son C3; ownership es C4;
  genéricos/pacts son C6; no hay codegen.

- Unificación con union-find; `InferVar` con `Ty`/`IntVar`/`FloatVar`.
- Cada literal entero crea `IntVar` con rango/sufijo; defecto `Int`; cada float `FloatVar`; defecto `Float`.
- `none`/`some`/`ok`/`err` introducen `Option`/`Result`; `none` sin contexto -> `PGS-E1508`; `err` sin éxito -> `PGS-E1507`.
- `?T` se desazucara a `Option[T]` antes de inferir.
- `if`/`match`/`loop`/bloque: unificación de ramas; `Never` no participa; `if` sin `else` es `Unit`.
- `loop` sin `break` es `Never`; `break` con valor fija el tipo; `break` sin valor -> `Unit`.
- Funciones: firmas explícitas; argumentos/retorno; sin sobrecarga; sin defaults/varargs.
- Closures: parámetros tipados; retorno inferido; el tipo de la closure es `(A)->B`; captura inferida; no `return`/`?` (`PGS-E7004`).
- Genéricos: instanciar; bounds; turbofish; sin defaults; no `where`; no const generics.
- `as` no cambia la inferencia; el tipo destino es explícito.
- `in`/`is`/`isnt`; `is` exige `Eq` (Float no); `in` exige rango/Set/Map.
- `@@derive` añade impls al HIR; `Copy` exige `Clone` y campos Copy; `Eq`/`Ord`/`Hash` rechazan Float; `Default` exige campos Default.
- `sigil`/`relic`: tipo explícito; `sigil` const-eval; `relic` inmutable.
- `Map`/`Set` claves exigen `Eq + Hash` (`PGS-E3102`/`E3103`); Float no.
- `Ptr`/`CStr`/`CString` en FFI.

### 4.4 Ownership y borrowing

#### 4.4.1 Modelo

- `Place { base: Local/Param/Static/Field/Index/Deref, projections: Vec<Projection> }`.
- `Loan { place, kind: Shared|Mut, region: RegionId }`.
- `RegionId` es un grafo de restricciones (`'r` interno, no escrito).
- CFG por body; cada `Expr`/`Stmt` es un nodo; `Loan` tiene `live_from`/`live_to`.

#### 4.4.2 Reglas

1. **Move:** asignar/pasar/retornar un owned mueve; después el lugar no es usable (`E4101`).
2. **Copy:** primitivos, tuplas/arrays de Copy, records `@@derive(Copy, Clone)` se copian; no hay move.
3. **Clone:** `x.clone()` explícito; no hay clon implícito.
4. **Borrow:** `&place`/`&mut place`; no simultáneo shared+mut (`E4102`); no mover mientras prestado (`E4106`); no destruir mientras prestado (`E4108`).
5. **Escapes:** una referencia local no puede salir del scope (`E4104`); no campos/variantes/alias/retornos libres (`E4105`); métodos pueden devolver vista de `@`/`@mut`; no de locales.
6. **Tiempo de vida:** NLL local; la referencia vive hasta su último uso; no se escribe `'a`; si no se puede inferir -> `E4109`.
7. **Mutabilidad:** `bind` inmutable; `morph` mutable; asignar a `bind`/campo inmutable -> `E1103`; campo privado fuera -> `E1104`; `push` sobre inmutable -> `E3106`.
8. **Inicialización:** no se lee un local antes de `bind`/`morph`; `bind` debe inicializar; `morph` puede declararse con tipo y asignarse después solo si el checker lo permite (si la spec no lo permite, `morph x: T` sin `=` es error).
9. **Drop:** al final del scope, orden inverso; no `Drop` visible; `@own` consume; no se puede usar después.
10. **Closures:** captura por referencia si no escapa y el uso lo permite; por movimiento si escapa o el valor no se puede prestar; el checker decide; no `move`. Nunca son `FnOnce`: no pueden consumir/mover una captura; solo leerla o mutarla (`E7004`). Todo tipo `(A)->B` se puede llamar varias veces.
11. **Rc/Arc:** `.clone()` incrementa; no Copy; no mutabilidad interior en core; `Rc`/`Arc` importados (`E4107`).
12. **Métodos:** `@` = `&self`, `@mut` = `&mut self`, `@own` = `self`; llamada autoref; `@mut` requiere binding `morph` o `&mut`; `@own` consume.
13. **Colecciones:** `Vec`/`Map`/`Set`/`String` owned; pasar mueve; prestar `&[T]`/`&Str`/`&Map`; indexar presta; `get` devuelve `Option`.
14. **Patterns:** mover campos en `match`; `ref` no existe; `..` no mueve lo omitido; `bind ... else` no deja valor si falla.

#### 4.4.3 Algoritmo

1. Lower AST body a HIR con places.
2. Construir CFG (blocks, `if`, `match`, loops, `return`/`break`/`continue`).
3. Calcular `move`/`init` por flujo (forward dataflow) y `drop` (backward).
4. Generar restricciones de préstamo en cada uso; `Loan` vivo desde creación hasta último uso (NLL).
5. Resolver regiones con unión/fixpoint; detectar conflictos.
6. Para closures, capturar places y aplicar reglas de escape.
7. Emitir `E4101`–`E4109` con spans y sugerencias (`clone`, `&`, mover, `Rc`/`Arc`).
8. Si hay error, no se genera LIR.

#### 4.4.4 Casos obligatorios

- `bind a = String...; bind b = a; print(a)` -> E4101.
- `bind v = Vec...; bind r = &v; v.push(1)` -> E4102.
- `morph v` + `&mut` + `&` simultáneos -> E4102.
- `first_word = (text: &Str) -> &Str` -> E4105/E4109.
- `Str.get` devuelve `Option[&Str]` ligado a `@`; permitido.
- `bind view = &text; bind moved = text; print(view)` -> E4106.
- `Rc`/`Arc` sin `summon` -> E4107.
- `match` que mueve un campo y luego usa el record -> E4101.
- closure que captura `morph` y se llama dos veces -> E4102/E4101.
- `@mut` sobre `bind` -> E1103/E4103.
- `@own` y uso posterior -> E4101.

#### 4.4.5 Estado C4 (implementado 2026-11-13)

- Nuevo crate `pengu-check`; `CheckResult` expone tipos por `BodyId`/`LocalId` y
  `AdtDef.is_copy` se calcula desde `@@derive(Copy)`.
- Places con proyecciones de campo/índice; estado de inicialización, movimiento y
  préstamos; análisis por body con merge en ramas.
- Movimiento de owned, Copy/Clone, préstamos `&`/`&mut`, conflictos, movimiento de
  prestados, asignación a prestados/inmutables, `push` sobre inmutable, escapes de
  retorno y movimientos de campos en `match`.
- Diagnósticos `E4101`–`E4108` (E4109/NLL se completan en C5); `E1103`, `E3106`.
- Tests: 15 de C4, **304 de workspace**; clippy/fmt limpios.
- Límites: NLL, closures y métodos `@mut`/`@own` se completan en C5; la falta de
  import de `Rc`/`Arc` ya la reporta el HIR con `E2004`.

#### 4.4.6 Estado C5 (implementado 2026-11-13)

- NLL: cada préstamo ligado a un binding vive hasta el último uso de ese binding;
  los préstamos temporales mueren al terminar la sentencia. Se podan por bloque.
- Closures: capturas por referencia para valores no `Copy`; no consumen capturas,
  no usan `return`/`?` (`E7004`) y pueden llamarse varias veces. El préstamo de una
  captura dura hasta el último uso de la closure.
- Métodos: `Receiver` en HIR (`@`/`@mut`/`@own`), mapa tipo→métodos, lookup en el
  checker de tipos y tratamiento del receptor en ownership (`&self`, `&mut self`,
  `self`). `@mut` exige `morph`; `@own` consume.
- `Body.self_local` permite analizar `@.campo` en el cuerpo del método.
- Diagnósticos: `E4101`–`E4109` de C4 + `E7004` de closures.
- Tests: 13 de C5 en ownership + 1 de métodos en tipos; 28 de `pengu-check`;
  **318 de workspace**; clippy/fmt limpios.
- Límites: NLL es por sentencia/bloque, no un solver global de regiones; la
  resolución de métodos es estática por tipo y nombre, sin ambigüedad/implícitos
  de traits; los métodos de primitivas de `std` llegan con C6.

### 4.5 Patrones y exhaustividad

- Tipo del scrutinee; cada patrón se comprueba contra él (`E9003`).
- Bindings duplicados (`E9007`); `..` solo en agregados (`E9006`).
- Guards deben ser `Bool` (`E9004`); no cuentan para exhaustividad.
- `match` exhaustivo: sumas (todas las variantes), Bool (`true`+`false` o `_`), tuplas, records, slices; rangos de enteros requieren `else`; `Never` no participa.
- `else` después de exhaustivo -> `E9008`.
- Brazos inalcanzables -> `W9001`.
- `bind ... else`: el patrón es refutable; el `else` debe divergir (`E9005`); `for` solo irrefutable.
- `match` como expresión unifica tipos; `Never` no participa.
- `if let`/`while let` no existen; `bind ... else` cubre.

#### 4.5.1 Estado C3 (implementado 2026-11-13)

- HIR guarda `AdtDef`/`AdtField`/`AdtVariant` para records y sums; `variant_owners`
  enlaza variantes con su `enchanting`. Las variantes se enlazan también en el
  namespace de valores para `Circle`/`Admin`.
- Checker: construcción de records, campos, `..base`, variantes unit/tuple/named,
  `Option`/`Result`, patrones de tupla/record/variante/slice/rango/`or`/`@`/`..`,
  guards `Bool`, exhaustividad de sums/Bool/Option/Result y records completos,
  `bind ... else` y `for` irrefutable.
- Diagnósticos `PGS-E8001`–`E8005`, `PGS-E9001`–`E9008`, `PGS-W9001`.
- Tests: 22 de C3, 61 de `pengu-types`, **289 de workspace**; clippy/fmt limpios.
- Límites: genéricos en ADTs y visibilidad de campos profundos quedan para C6/C7;
  ownership es C4.


### 4.6 Const eval

- `sigil` solo expresiones de §5.6: literales, casts, operadores, constructores, arrays/tuplas, `some/none/ok/err`, otros `sigil`.
- Sin llamadas, métodos, `Vec`/`Map`/`Set` (runtime).
- Aritmética checked; overflow -> error; división cero -> error; `as` con tabla §14.6.
- `N` de `[T; N]` es const expr; debe ser entero no negativo; `sigil` permitido.
- `relic` se inicializa en runtime una vez; no const eval obligatorio.
- `@derive(Default)` usa valores por defecto; `Float` 0.0; `String` vacío; `Vec` vacío; `Option` none; records recursivos.
- `@@test` no const.

### 4.7 Genéricos, pacts, rituals y operadores

- Genéricos: `[T: Bound + Bound]`; bounds pacts; instanciación; turbofish; monomorfización; no `where`, no const generics, no defaults, no especialización.
- `pact`: métodos `@`/`@mut`/`@own`, defaults, máximo un superpact; `Self`; no asociados, no métodos genéricos, no async, no `where`, no blanket.
- `ritual`: inherente o `for`; coherencia huérfana; tipos locales/pacts locales; `ritual` sobre primitivo inherente solo en `std` (`E1210`); colisión inherente/pact en primitivo -> `W1210`.
- Operadores: solo `Add/Sub/Mul/Div/Rem/Neg/Eq/Ord`; firmas; `Ord` requiere `Eq`; `Eq`/`Ord` con Float no; `in` usa `contains`.
- `Show`: único pact de prelude; `print`/`format` exigen `Show` o primitivo; `@@derive(Debug)` no es `Show`.
- Sin despacho dinámico; llamadas a métodos se resuelven estáticamente; si es ambiguo -> error.
- `pact` genérico `Container[T]`; `ritual[T] Box[T]`; bounds.
- `Self` en tipos; no en expresiones fuera de `pact`/`ritual`.

#### 4.7.1 Estado C6 (completo, 2026-11-13)

- Genéricos de función con turbofish, inferencia y bounds de pacts de usuario.
- ADTs genéricos: inferencia de argumentos, sustitución en campos y patrones.
- `pact Container[T]` y `ritual[T] Box[T]`: parámetros ligados a un scope de tipo;
  `PactDef.generics`/`ImplDef.generics` poblados.
- Despacho de métodos de impls genéricos: el checker sustituye los parámetros del
  impl por los argumentos del tipo base.
- Pacts/impls: método faltante, firma incompatible, solapamiento; `Show` en
  `print`/`format`.
- Operadores de usuario `Add`/`Sub`/`Mul`/`Div`/`Rem`/`Neg`/`Eq`/`Ord`.
- Coherencia huérfana: en C6 solo existe un crate, así que no hay tipos/pacts
  externos que puedan violarla; la comprobación de solapamiento sí cubre impls
  genéricas por nombre de tipo.
- Tests: 52 de `pengu-types` (12 nuevos de C6); **330 de workspace**.

### 4.8 FFI y `curse`

- `foreign "C"`: solo firmas; tipos representables: `Int`, `I64`, `U8`, `Usize`, `Float`, `Bool`, `&CStr`, `Ptr[T]`; no records con `String`/`Vec`; `PGS-E1604`.
- `curse` block/function: `-- SAFETY:` obligatorio (`E1603`); llamadas `foreign` solo dentro (`E1602`); `curse` fuera de FFI -> `E1607`; no export (`E1606`).
- `CString` requiere manejo de `NulError` (`E1608`); `CStr` prestado; no `unwrap` silencioso.
- `abi "C"`/`"system"`; `abi "js"` -> E2022; `abi "pengu"` -> E2024 si no hay implementación.
- `Ptr[T]` solo en `.d.pengu`/`foreign`/`curse`; no se guarda/compara.
- `[link]` obligatorio para `abi "C"`/`"system"` que lo requiera (`E2023`).
- `panic` no cruza FFI; codegen aborta en el borde.
- `-- SAFETY:` contenido libre; el checker no lo valida semánticamente, solo presencia.

#### 4.8.1 Estado C7 (completo, 2026-11-13)

- **Derives**: `@@derive` se guarda en `AdtDef.derives`. El checker valida
  nombres conocidos (`E8006`), `Copy` exige `Clone` y campos `Copy`, `Default`
  no se permite en sumas, `Eq`/`Ord`/`Hash` rechazan campos `Float`, y `Ord`
  exige `Eq` (`E8007`).
- **FFI**: `foreign` registra sus firmas en `HirCrate.signatures` y sus `DefId`
  en `foreign_fns`; las funciones `curse` se registran en `curse_fns`.
  Se valida ABI (`C`/`system`; `js` -> `E2022`, desconocida -> `E1605`) y tipos
  representables (`E1604`). Una llamada a `foreign` fuera de `curse` produce
  `E1602`; un bloque `curse` abre el contexto.
- **Const eval**: `sigil`/`relic` se guardan en `ConstDef`; el checker valida
  el tipo contra el valor, exige expresión constante (`E1107`) y detecta
  división por cero constante (`E1403`). Construcciones no constantes se
  rechazan.
- Tests: 9 de derives/FFI + 3 de const eval; **64 de `pengu-types`** y
  **342 de workspace**.
- Límites conscientes: la presencia textual de `-- SAFETY:` y el manejo de
  `NulError` se validarán en C8/lint; `Ptr` se restringe por tipo en FFI, pero
  no hay análisis de flujo de punteros.

### 4.9 Diagnósticos y garantías

#### 4.9.1 Estado C8 y Gate C (completo, 2026-11-13)

- Diagnósticos ordenados por `(archivo, offset, fin, severidad, código)` en
  `DiagnosticBag` y `CheckResult`.
- Warnings no bloquean (`is_clean` solo mira errores); `W9001` cubre brazos
  unitarios duplicados.
- `docs/DIAGNOSTICS.md` documenta el contrato y la cobertura; `docs/GUARANTEES.md`
  enlaza cada garantía de §21 con su test.
- `scratch/tools/check_diagnostics.py`: catálogo de 160 códigos, sin códigos
  emitidos fuera de §20; reporta los 96 aún reservados para fases posteriores.
- Tests de garantías (`crates/pengu-types/tests/guarantees.rs`), corpus de
  programas válidos (`corpus_check.rs`) y fuzz de entradas malformadas
  (`fuzz_smoke.rs`, 300 casos) sin pánicos.
- Gate C **PASA** con `scratch/tools/gate_c.py`: 160/160 cubiertos (155
  emitidos + 5 justificados). La medición `pengu check` < 2 s queda diferida
  al CLI.
- Tests: **449 workspace**; clippy/fmt limpios.

- Cada check referencia un código de §20; no se añaden.
- Diagnóstico: código, mensaje, span primario, labels, help/fix, notas de backend.
- Orden estable: archivo, offset, código.
- Warnings no bloquean; `pengu lint --allow`.
- Garantías §21: tests que demuestren no-null, no-UAF, no-data-race (single-thread), no-GC, no-truthiness, exhaustividad, no-macros, no-dyn, no-lifetimes, curse-only-FFI, no-global.
- `PGS-E2014` reservado para errores de backend sin mapa; no para errores propios.

### 4.10 Checker gate

No se pasa a Fase 3 hasta:

- todos los ejemplos válidos checkean;
- cada código 160 tiene test negativo o justificación;
- no hay `panic!`/`unwrap` en el checker ante input inválido;
- ownership suite (move/borrow/clone/drop/refs/closures) verde;
- const eval y `.d.pengu` verdes;
- `pengu check` < 2s para 10k líneas (objetivo, no gate).

---

## 5. Fase 3 — Lowering, codegen y build/run

**Objetivo:** generar Rust correcto, compilarlo y ejecutarlo, sin filtrar Rust.

### 5.1 LIR

`LIR` es explícito, monomórfico y cercano a Rust:

```rust
struct LProgram { items: Vec<LItem>, functions: Vec<LFunction>, statics: Vec<LStatic>, types: Vec<LTyDef> }
struct LFunction { name: Symbol, params: Vec<LParam>, ret: LTy, locals: Vec<LLocal>, blocks: Vec<LBlock> }
struct LBlock { stmts: Vec<LStmt>, term: LTerm }
enum LStmt { Let(LocalId, LExpr), Assign(Place, LExpr), Eval(LExpr), Drop(LocalId) }
enum LTerm { Goto(BlockId), If(LExpr, BlockId, BlockId), Return(Option<LExpr>), Panic(LExpr), Abort, Unreachable }
enum LExpr { Const, Local, Place, Call, Binary, Unary, Cast, Struct, Variant, Array, Tuple, Closure, ... }
```

- `LIR` elimina azúcar: `?` -> match; `if`/`match` -> CFG; `for` -> iterador/while; `loop` -> loop; `break` -> goto.
- `LIR` conserva `Origin` por sentencia/expresión para source maps.
- `Place`/`Projection` se mantienen para asignación y préstamos.
- No hay tipos genéricos en LIR: todo monomorfizado.
- No hay `Option`/`Result` implícitos: son ADTs.

### 5.1.1 Estado B1 (completo, 2026-11-13)

- Crate `crates/pengu-lir`: `LProgram`, `LFunction`, `LBlock`, `LStmt`, `LTerm`, `LExpr`.
- `lower_crate` baja cuerpos HIR a CFG.
- Cubierto: `bind`/`morph`, asignación simple, `if`/`else` (sentencia y expresión), `while`, `loop` (sentencia y expresión), `for` sobre rangos, `match` de literales/rangos/Bool/wildcard/binding, `break`/`continue`, `return`, literales, locales, binarios/unarios, tuplas y llamadas.
- Tests `crates/pengu-lir/tests/control.rs`: 8; workspace 457.
- Fuera de B1 por diseño: `?` (error lowering), closures, ADTs, `for` sobre iteradores, monomorfización, `Drop` y codegen. Pertenecen a B2/B3.

### 5.2 Monomorfización

1. Recolectar instancias de funciones/tipos desde `main`/`lib`/tests.
2. Sustituir parámetros de tipo; comprobar bounds ya hechos en Fase 2.
3. Nombrar instancias: `foo__I32`, `Pair__I32_String`; colisiones -> hash corto.
4. Recolectar instancias transitivas hasta fixpoint.
5. Ordenar topológicamente; ciclos de llamadas permitidos; recursión permitida.
6. Emitir solo instancias alcanzables; `pub` de librería se emite si es API pública.

### 5.2.1 Estado B2 (completo, 2026-11-13)

- `crates/pengu-lir/src/mono.rs`: `MonoPlan`/`MonoInstance` y `plan_monomorphization`.
- Recolecta instancias desde todos los cuerpos no genéricos (funciones, `grimoire`, tests), resuelve llamadas con turbofish, sustituye `T` en llamadas transitivas y genera nombres `foo__Int`.
- `lower_crate` materializa una `LFunction` por instancia: sustituye tipos en locales, params, retorno y temporales; las funciones genéricas base no se emiten.
- `LExpr::Call(DefId, Vec<Ty>, Vec<LExpr>)` conserva los argumentos de tipo para que B3 resuelva la instancia.
- `ast_type_ty` convierte los tipos de firma (incluidos genéricos) a `Ty`; los `Ty::Generic` de los cuerpos se sustituyen con el entorno de la instancia.
- `LProgram.instances` contiene las instancias alcanzables.
- Tests `crates/pengu-lir/tests/mono.rs`: 3 (plan directo, transitivo y LIR materializado); workspace 460.
- Bug C6 corregido: `type_arg_ty` ahora consulta `generic_env` por nombre y `check_body` inicializa el entorno de genéricos del cuerpo.
- Límite: las instancias se siembran desde todos los cuerpos no genéricos; la API pública de librería se emite a través de esos cuerpos.


### 5.2.2 Estado B3b (2026-11-13)

- `crates/pengu-codegen`: `Generated` y `generate(krate, program)`.
- `Generated.diagnostics` propaga errores/warnings de HIR y LIR; si hay un
  error no se emite Rust.
- B3a: items completos, módulos `scroll` anidados, paths `crate::...`,
  visibilidad, `@@test`, `grimoire`, `foreign` por ABI, `curse`, pacts con
  defaults y metadata HIR (`TestInfo`, `grimoires`, `foreign_abis`).
- B3b: LIR/codegen de campos, índices, arrays/repeat, `Vec`/`Map`/`Set`,
  records, variantes, primitivas (`some`/`none`/`ok`/`err`/`print`/`format`),
  casts, `?`, refs, rangos y chars; expresión final de función; locales `Copy`
  con `expect` y no `Copy` con `take`; `grimoire: Result`.
- B3c (parcial): llamadas a métodos (`LExpr::Method`), `@` como local `self` y
  `Str` como `&str` (elisión de lifetime).
- B3d: closures (sin/con captura), iteradores lazy (`Iterator`/`IntoIter`/`Next`),
  `for` sobre `Vec`/array/`Map`/`Set`, destructuring plano/anidado, adaptadores e
  impls genéricos monomorfizados.
- B3: locales bajan a una state machine SSA (`enum __State` + `loop/match`);
  sin `Option<T>`/`expect`; variantes con préstamos usan `enum __State<'a>`.
- Tests `crates/pengu-codegen/tests/codegen.rs`: 41 (compilación y ejecución);
  workspace **505**.
- Límites: `Drop`/runtime de usuario y Gate B; B4–B7 en §5.3.1.

### 5.3.1 Estado B4–B7 (B4–B7 completos, 2026-11-13)

- B4 ✅: `Show` runtime (primitivos, strings, `&T`, `Box`/`Rc`/`Arc`,
  arrays/slices, `Vec`, `Map`, `Set`, `Option`, `Result`, tuplas y `Ordering`);
  `print`/`format`, interpolación `#{}`, `panic`/`assert` y `Show` de usuario; 42 codegen, 506 workspace.
- B5 ✅: `Cargo.toml` con `build.rs`, `rust-version`, features, dependencias git/path y `[link]`; `pengu-build` usa `cargo build`/`cargo run`; 5 build, 13 project, 511 workspace.
- B6 ✅: `SourceMap` por sentencia/expresión vía marcadores, `lookup`, `to_json`; `remap_rustc_diagnostics` para JSON de rustc/Cargo; 43 codegen, 7 build, 514 workspace.
- B7 ✅: `pengu-build::{compile, emit, build, run, test}` con Cargo; `BuildReport`/`run_report`/`test_report` con errores remapeados; 9 build, 518 workspace.
- Gate B: **PASA** sobre la suite representativa de 15 programas y sobre el corpus completo (B8); ver `scratch/GATE_B_REPORT.md` y `scratch/GATE_B_CORPUS.md`. Corpus: 68 compilan, 4 declaraciones, 56 fragmentos, 5 errores y 13 no ejecutables declarados con motivo (0 bloqueos sin declarar).

## 5.3 Mapa de tipos

| PenguScript | Rust generado | Nota |
|---|---|---|
| `Bool` | `bool` | |
| `Int` | `i32` | |
| `I8`..`I64` | `i8`..`i64` | |
| `Isize` | `isize` | |
| `U8`..`U64` | `u8`..`u64` | |
| `Usize` | `usize` | |
| `F32`/`F64`/`Float` | `f32`/`f64`/`f64` | |
| `Char` | `char` | |
| `String` | `String` | |
| `Str` | `&str` | en params/locales |
| `Unit` | `()` | |
| `Never` | `!` | retorno/divergencia |
| `(A,B)` | `(A,B)` | |
| `[T;N]` | `[T;N]` | N const |
| `&[T]`/`&mut [T]` | `&[T]`/`&mut [T]` | |
| `Vec[T]` | `Vec<T>` | |
| `Map[K,V]` | `HashMap<K,V>` | |
| `Set[T]` | `HashSet<T>` | |
| `Option[T]` | `Option<T>` | |
| `Result[T,E]` | `Result<T,E>` | |
| `Box[T]` | `Box<T>` | |
| `Rc[T]`/`Arc[T]` | `Rc<T>`/`Arc<T>` | importados |
| `Ptr[T]` | `*mut T` | solo borde |
| `CStr`/`CString` | `&CStr`/`CString` | |
| `Ordering` | `std::cmp::Ordering` | |
| `Show` | trait `Show` | runtime |
| `Self` | tipo del impl | |

### 5.4 Runtime

Se genera un módulo `rt.rs` (o crate interna) sin dependencias:

```rust
pub trait Show { fn show(&self) -> String; }
pub fn print<T: Show>(value: &T);
pub fn println<T: Show>(value: &T);
pub fn eprint...
pub fn panic_str(msg: &str) -> !;
pub fn assert...
```

- Implementar `Show` para primitivos, `String`, `Str`, `Vec`, `Map`, `Set`, `Option`, `Result`, tuplas/arrays.
- `format`/interpolación se compila a concatenación de `show`; no variádicos.
- `panic`/`assert` son funciones del runtime; `Never`.
- `@own`/move/drop: Rust nativo.
- `Rc`/`Arc` de std; no runtime propio.
- `CStr`/`CString`: std::ffi.
- `Ptr`: `*mut`; operaciones solo en `curse`.

### 5.5 Codegen por constructo

| Constructo | Rust |
|---|---|
| `bind` | `let` (inmutable) |
| `morph` | `let mut` |
| asignación | `place = expr` |
| `if`/`unless` | `if`/`if !`; Unit sin else |
| `match` | `match`/`if let`; exhaustivo |
| `while` | `while` |
| `loop` | `loop`; `break value` -> `break value` |
| `for` | `for` (IntoIterator) o `while let` |
| `return` | `return` |
| `break`/`continue` | `break`/`continue` |
| `?` | `match`/`return Err`; no `From` |
| `as` | `as` |
| `is`/`isnt` | `==`/`!=` |
| `in` | `contains`/range |
| `and`/`or` | `&&`/`||` cortos |
| `not` | `!` |
| interpolación | `format!`/concat `Show` |
| `print` | `rt::print` |
| `panic` | `rt::panic_str` |
| `grimoire` Unit | `fn main()` |
| `grimoire: Result` | `fn main()` + match; error a stderr + exit 1 |
| `rune` | `struct` |
| `enchanting` | `enum` |
| `pact` | `trait` |
| `ritual` | `impl` |
| `essence` | `type` |
| `scroll` | `mod` |
| `summon` | `use` |
| `unveil` | `pub`/`pub(crate)`/`pub(super)`/`pub(in ...)` |
| `sigil` | `const` |
| `relic` | `static` |
| `foreign` | `extern "C" { ... }` + `#[link]` |
| `curse` | `unsafe` |
| `@@derive` | `#[derive]` |
| `@@test` | `#[test]`, `#[should_panic]`, `#[ignore]` |
| `.d.pengu` | sin código; solo firmas |

- `Map` literal -> `HashMap::from([...])`; `Set` -> `HashSet::from([...])`; `Vec` -> `vec![]`; array -> `[...]`.
- Struct literal -> `Point { x, y }`; update `..p` -> `Point { y, ..p }`.
- Enum variant -> `Shape::Circle { radius }` / `Shape::Rectangle(a,b)`.
- Pattern -> Rust pattern; `@` binding -> `name @ pattern`.
- `..` rest -> `..`.
- No `ref`/`ref mut` patterns; use match ergonomics or explicit `&`.
- `@` receiver: `&self`; `@mut`: `&mut self`; `@own`: `self`.
- Methods: `impl Type { fn method(&self, ...) -> ... }`.
- Associated functions: `impl Type { fn origin() -> ... }`.
- Trait impl: `impl Pact for Type { ... }`.
- `Show`: `impl Show for Type`.
- Operator traits: `impl Add for Type { type Output = Type; fn add(self, other: Type) -> Type }`; `Eq`/`Ord` manual; no `Display`.

### 5.6 Codegen de ownership

- `bind` -> `let`; `morph` -> `let mut`.
- Moves: direct Rust moves.
- Borrows: `&`/`&mut`; Rust NLL.
- `@`/`@mut`/`@own`: receiver types.
- `Str` params/locals: `&str`; `String` owned.
- Method return `Option[&Str]`: `Option<&str>`; elision tied to `&self`.
- Free function returning ref: rejected F2, so no codegen.
- Closures:
  - Function item -> path.
  - Closure -> Rust closure; choose `move` if capture by value/escape.
  - Function type parameter -> generic `F: FnMut(...) -> ...`; nunca `FnOnce`.
  - Return closure -> `impl FnMut(...) -> ...` (or `Fn`).
  - No storage in aggregates; if later allowed, `Box<dyn FnMut>` internal.
- `Rc`/`Arc`: direct.
- Drop: Rust.
- `for` over `Vec` -> `for x in vec` (moves) or `.iter()` if borrowed? Checker decides; codegen picks based on HIR iteration kind.
- `Map` iteration -> `for (k,v) in &map`/`map`; checker decides ownership.

### 5.7 Cargo, Tome y enlace

Generated layout:

```text
target/pengu/<profile>/
  Cargo.toml
  Cargo.lock
  build.rs            # solo si hay build.pengu (diferido; no en 0.6.0)
  src/
    main.rs | lib.rs
    modules...
    rt.rs
  sourcemap.json
```

- `Tome.toml` -> `Cargo.toml`:
  - `[tome]` name/version/edition/rust-version.
  - `[dependencies]` git/path, features, default-features, optional.
  - `[features]`.
  - `[[bin]]`/`[[lib]]`.
  - `[link]` -> `#[link(name = "...")]`.
  - `[declarations]` no Cargo.
- No registry; git/path only; `Tome.lock` commit/checksum; no publish.
- `pengu check` no Cargo; `pengu build` invokes `cargo build --manifest-path target/pengu/Cargo.toml`; `run` executes; `test` cargo test; `bench` release tests.
- `rustc` JSON: `--message-format=json`; parse spans; sourcemap maps generated line/col to PenguScript; if unmapped -> `PGS-E2014`.
- `overflow-checks = true` in both profiles.
- `panic = "unwind"`; FFI boundary abort.
- `edition = "2024"`; MSRV 1.85.
- No `build.rs` in 0.6.0; future.
- Cargo env: `CARGO_TARGET_DIR=target/pengu/target`; offline/locked flags from CLI.

### 5.8 Source maps

```json
{
  "version": 1,
  "crate": "hello",
  "files": {
    "src/main.rs": [
      { "generated": {"line": 3, "col": 5}, "source": {"file": "src/main.pengu", "start": 42, "end": 48}, "kind": "expr" }
    ]
  }
}
```

- Cada `LExpr`/`LStmt` con `Origin` emite mapping.
- Mapeo inverso para rustc: generated -> source; fallback al item contenedor; si no, E2014.
- El sourcemap no se muestra al usuario; `pengu explain` puede exponerlo con `--backend`.

### 5.9 Build/run reales

- `pengu build`: frontend -> checker -> lower -> codegen -> cargo; artefacto.
- `pengu run`: build + exec; args after `--`; env; working dir; exit code.
- `pengu test`: genera harness; `@@test` -> `#[test]`; `should_panic` expected; `ignore`; doc tests later.
- `pengu bench`: `cargo test --release` (no `@@bench`).
- `pengu clean`: target/pengu.
- `pengu watch`: rebuild on change; debounce.
- `pengu check --json`: diagnostics only; no Cargo.
- `pengu build --json`: artifact paths + diagnostics.
- Errores de Cargo (missing dep, linker) -> `PGS-E18xx`/`E2014`; no raw Rust.

### 5.10 Incrementalidad y cache

- Key: hash of source files, `Tome.toml`, compiler version, flags, profile.
- Cache AST/HIR/types per file/body; invalidate dependents.
- `target/pengu/cache/`; content-addressed.
- No cache across compiler versions.
- Parallelism: none in core; CLI may parallelize independent crates? Single-thread for self-host; keep deterministic.

### 5.11 Backend gate

No se declara 0.6.0 compilable hasta:

- todo el corpus aceptado genera Rust que compila;
- `pengu run` ejecuta hello/cookbook;
- `pengu test` ejecuta tests;
- sourcemaps remapean errores forzados;
- no hay `rustc` crudo en stderr;
- `cargo` no se invoca en `check`;
- profiles con overflow checks.

---

## 6. Librerías externas, licencias y auto-hospedaje

### 6.1 Política

- **Núcleo semántico:** cero dependencias externas obligatorias. Lexer, parser, HIR, tipos, ownership, LIR y codegen se escriben con `std`.
- **Bootstrap permitido:** solo para archivos, TOML, hashes, versiones, terminal, tests. Debe tener reemplazo en `std` y una ruta de port.
- **Prohibido enlazar:** GPL/AGPL/LGPL sin excepción compatible; `libgit2`; `clap`/`miette`/`tower-lsp`/`salsa`/`gix`/`regex` en el núcleo; macros/derive que no se puedan portar.
- **Herramientas externas:** `git`, `clang`, `rustc`, `cargo` se ejecutan como procesos, no se enlazan.
- **Licencia del proyecto:** MIT OR Apache-2.0 (decisión abierta, pero el plan asume esto).

### 6.2 Tabla de dependencias

| Crate | Uso | Licencia | Fase | Portabilidad | Reemplazo |
|---|---|---|---|---|---|
| `unicode-ident` | XID_Start/Continue | MIT OR Apache-2.0 AND Unicode-DFS-2016 | F1 | tablas generadas; portable | `std.unicode` |
| `unicode-width` | ancho de diagnóstico | MIT OR Apache-2.0 | F1 | tabla; portable | `std.unicode` |
| `indexmap` | mapas ordenados | MIT OR Apache-2.0 | F2 | fácil | `Vec` + orden |
| `rustc-hash` | hashing rápido | MIT OR Apache-2.0 | F1/F2 | fácil | hasher propio |
| `toml` | `Tome.toml` | MIT OR Apache-2.0 | CLI/F1 | media (serde) | `std.toml` |
| `sha2` | checksums | MIT OR Apache-2.0 | CLI/F3 | media | `std.digest` |
| `semver` | versiones | MIT OR Apache-2.0 | CLI/F3 | fácil | `std.semver` |
| `tempfile` | tests/build | MIT OR Apache-2.0 | F3 | fácil | `std.fs` |
| `walkdir` | recorrer fuentes | Unlicense OR MIT | F1/F3 | fácil | `std.fs.walk` |
| `dirs` | config/cache | MIT OR Apache-2.0 | CLI | fácil | `std.env` |
| `which` | localizar tools | MIT | CLI | fácil | `std.process` |
| `libc` | terminal/OS | MIT OR Apache-2.0 | P3 | plataforma | `std.term`/`std.os` |
| `windows-sys` | Windows | MIT OR Apache-2.0 | P3 | plataforma | `std.os` |
| `insta` | snapshots | Apache-2.0 | dev | solo test | propio |
| `proptest` | propiedades | MIT OR Apache-2.0 | dev | solo test | propio |
| `criterion` | benchmarks | Apache-2.0 OR MIT | dev | solo test | propio |

Transitivas de `toml` (`serde`, `serde_spanned`, `toml_datetime`, etc.) se aceptan solo en bootstrap y se auditan con el mismo gate. `serde_json` no se usa en el núcleo; LSP implementa JSON propio.

### 6.3 Herramientas externas

| Herramienta | Uso | Licencia | Enlace |
|---|---|---|---|
| `rustc` | compilar Rust | MIT OR Apache-2.0 | proceso |
| `cargo` | build/run/test | MIT OR Apache-2.0 | proceso |
| `git` | paquetes | GPL-2.0 | proceso, no enlace |
| `clang` | bindgen AST JSON | Apache-2.0 WITH LLVM-exception | proceso |
| `rustfmt` | no; formatter propio | — | — |
| `libclang` | no | Apache-2.0 | prohibido enlazar |

### 6.4 Integración por fases

1. **P0 (F1–F3):** núcleo sin deps; `pengu-span`, `pengu-diag`, `pengu-syntax`, `pengu-hir`, `pengu-types`, `pengu-check`, `pengu-lower`, `pengu-codegen`.
2. **P1 (frontend):** `unicode-ident`/`unicode-width` opcionales; tablas vendorizadas; tests de XID.
3. **P2 (CLI/paquetes):** `toml`, `sha2`, `semver`, `tempfile`, `walkdir`, `dirs`, `which`; cada uno con `std` replacement.
4. **P3 (plataforma):** `libc`, `windows-sys` para terminal/instalador; no en checker/codegen.
5. **Gate CI:** `cargo tree -e normal` contra allowlist; falla si entra GPL/AGPL o un crate fuera de tabla; `cargo metadata` + script propio.

### 6.5 Auto-hospedaje

Cada crate se escribe con APIs portables:

- sin `dyn`, `impl Trait` en superficies, closures almacenadas, async, hilos;
- `Result`/`Option`/`Vec`/`Map`/`String`/`&str`;
- iteración determinista;
- errores como valores;
- sin macros/derive en el código que se porta;
- sin `unsafe`, salvo el runtime FFI generado.

La regla de oro: si una estructura no se puede escribir en PenguScript 0.6.0, no se usa en el compilador.

---

## 7. Hitos, dependencias y puertas de calidad

### 7.1 Fase 1 — Frontend (estimación 6–8 semanas)

| Semana | Hito | Entregable |
|---|---|---|
| 1 | F0 ✅ | workspace, span, diag, vfs |
| 2 | F1 ✅ | lexer completo + tests |
| 3 | F2 ✅ | expresiones/pratt |
| 4 | F3 ✅ | items/tipos/patrones |
| 5 | F4 ✅ | módulos, `.d.pengu`, atributos |
| 6 | F5 ✅ | corpus de sintaxis completo |
| 7 | F6 ✅ | fuzz, límites, documentación |
| 8 | Gate F ✅ | sintaxis congelada; no más cambios sin test |

### 7.2 Fase 2 — Checker (estimación 10–14 semanas)

| Semana | Hito | Entregable |
|---|---|---|
| 9–10 | C1 ✅ | HIR, módulos, nombres; 26 tests HIR, 228 de workspace |
| 11–12 | C2 ✅ | tipos, inferencia, literales; 39 tests de tipos, 267 de workspace |
| 13–14 | C3 ✅ | records/sums/patrones/exhaustividad; 22 tests C3, 61 de tipos, 289 de workspace |
| 15–16 | C4 ✅ | ownership: move/Copy/borrow; 15 tests C4, 304 de workspace |
| 17–18 | C5 ✅ | NLL, closures, métodos `@`/`@mut`/`@own`; 14 tests C5, 318 de workspace |
| 19 | C6 ✅ | pacts/impls, genéricos de funciones/ADTs, genéricos de pacts/rituals y operadores; 330 de workspace |
| 20 | C7 ✅ | const eval, FFI, derives; 342 de workspace |
| 21 | C8 ✅ | diagnósticos ordenados, garantías, corpus y fuzz; 449 de workspace |
| 22 | Gate C ✅ | 160/160 códigos cubiertos (155 emitidos + 5 justificados); `gate_c.py` PASS; rendimiento pendiente del CLI |

### 7.3 Fase 3 — Backend (estimación 8–12 semanas)

| Semana | Hito | Entregable |
|---|---|---|
| 23 | B1 ✅ | LIR + CFG de control (if/match/for-rango/while/loop/break/continue/return y expresiones); 8 tests |
| 24 | B2 ✅ | monomorfización materializada: instancias, sustitución de tipos y llamadas con type args; 3 tests |
| 25 | B3 ✅ | codegen de items, expresiones, locales SSA, métodos, closures, iteradores, `Map`/`Set`, impls genéricos; 35 codegen, 499 workspace |
| 26 | B4 ✅ | runtime, print/format/Show, interpolación y panic/assert; 42 codegen, 506 workspace |
| 27 | B5 ✅ | Cargo/Tome/link: Cargo.toml/build.rs, features, path/git deps, cargo build/run |
| 28 | B6 ✅ | sourcemaps por sentencia/expresión y parser JSON de rustc/Cargo |
| 29 | B7 ✅ | build/run/test con Cargo, `BuildReport` y errores remapeados |
| 30 | B8 ✅ | harness de los 146 bloques: 68 compilan, 56 fragmentos, 4 declaraciones, 5 errores y 13 no ejecutables declarados con motivo |
| 31 | Gate B ✅ | suite de 15 programas y corpus completo PASAn; 0 bloqueos sin declarar |
| 32 | H1 | bootstrap auto-hospedaje |

Estimación total: **30–34 semanas** de una persona; paralelizable en frontend/checker/backend con dos personas.

### 7.4 Puertas

- **Gate F:** toda la sintaxis; no se acepta un cambio de grammar sin test.
- **Gate C:** todo programa válido checkea; todo error tiene código; no pánicos.
- **Gate B:** todo programa aceptado compila; `run` funciona; no Rust crudo.
- **Gate H:** el compilador se compila a sí mismo y pasa el corpus.

---

## 8. Estrategia de pruebas

### 8.1 Corpus

- Extraer los 146 bloques `pengu` de `LANGUAGE.md` a `tests/corpus/` con metadatos:
  - `valid`: debe parsear/checkear/compilar.
  - `fragment`: didáctico, se envuelve en `grimoire`.
  - `invalid`: debe fallar con código.
  - `rust`: solo bloque Rust, no se compila como PenguScript.
- Cada ejemplo de `STDLIB.md` y `CLI_PLAN.md` que sea PenguScript.
- `tests/corpus/valid/*.pengu` con salida esperada; `tests/corpus/invalid/*.pengu` con código.

### 8.2 Frontend

- Snapshot de tokens y CST por archivo.
- Test de cada producción de §19.
- Indentación: matriz de 0–8 espacios, tabs, CRLF, comentarios.
- Strings: 50 casos de escapes/interpolación/raw/byte/C.
- Fuzz: `cargo fuzz` o harness propio; 10M tokens; no pánico.
- Límites: archivo 10MB, 10k líneas; profundidad 1000; error limpio.

### 8.3 Checker

- Un test por código de §20 (160).
- Ownership suite con 100+ casos:
  - move, Copy, Clone, borrow, reborrow, NLL, partial move, drop, closure capture, `@mut`, `@own`, `Rc`/`Arc`, `Vec`/`Map`/`Set`.
- Tipos: literales, inferencia, genéricos, bounds, `?`, `Result`, `as`, `in`, `is`.
- Patrones: exhaustividad, guards, `@`, `..`, slices, or, ranges.
- Const eval: overflow, división, casts, `sigil`, arrays.
- FFI: `foreign`, `curse`, `Ptr`, `CStr`, `.d.pengu`, `[link]`.
- Garantías: tests de no-null, no-UAF, no-truthiness, no-global.

### 8.4 Backend

- Golden Rust para cada constructo; compilar con `rustc --edition 2024`.
- Ejecutar binarios y comparar stdout/exit.
- Sourcemap: forzar error Rust y comprobar span PenguScript.
- Cargo: proyecto con git/path deps, features, `[link]`.
- Incremental: cambiar un archivo, verificar que no se recompila todo.
- No filtrar Rust: stderr no contiene `error[E` sin remapear.

### 8.5 Self-host

- H1: compilador Rust compila fuente PenguScript del compilador.
- H2: binario PenguScript compila su propia fuente.
- H3: comparar diagnósticos/salidas de H1/H2.
- H4: CLI/LSP en PenguScript.
- H5: bootstrap reproducible; checksums.

---

## 9. Riesgos y puntos de spec cerrados

Los cuatro puntos de §9.1–§9.4 se cerraron en `LANGUAGE.md` el 2026-11-12; F0 puede empezar. No se inventan códigos: se reutilizan los existentes (`E7004`, `E8007`, `E1702`).

### 9.1 Gramática de literales de colección (cerrado en spec)

Resuelto en `docs/LANGUAGE.md` §19.8: se añadieron `vector` y `map_lit` a `primary`:

```ebnf
vector ::= "Vec" "[" "]" | "Vec" "[" expr ("," expr)* ","? "]"
map_lit ::= "Map" "[" "]" | "Map" "[" map_entry ("," map_entry)* ","? "]"
primary ::= ... | vector | map_lit
```

`Map`/`Vec`/`Set` no son keywords; el parser reconoce `IDENT` exacto seguido de `[` en expresión. `Vec[T]`/`Map[K,V]` en tipo siguen siendo `path` + `type_args`.

### 9.2 Cierre `FnOnce`/captura

Resuelto en `docs/LANGUAGE.md` §7.6/§7.7: toda closure es invocable varias veces y **nunca es `FnOnce`**. Puede capturar por movimiento (también no-`Copy`), pero el cuerpo solo puede leer o mutar la captura, nunca consumirla/moverla fuera. `return`, `?` o consumo de captura producen `PGS-E7004`.

El checker no distingue `Fn`/`FnMut`/`FnOnce` en la superficie; el backend usa `FnMut` en parámetros genéricos e `impl FnMut` en retornos. Un `bind` de closure puede generar `let mut` interno sin permitir reasignar el binding.

### 9.3 `@@derive` en sums

Resuelto en `docs/LANGUAGE.md` §8.8: `enchanting` permite `Debug`, `Clone`, `Copy`, `PartialEq`, `Eq`, `PartialOrd`, `Ord` y `Hash` si todos los campos lo permiten; `Copy` exige `Clone` y todos los campos `Copy`. `Default` se rechaza en `enchanting` en 0.6.0; un derive imposible produce `PGS-E8007`.

### 9.4 `Test` con retorno

Resuelto en `docs/LANGUAGE.md` §17.1: `@@test` debe devolver `Unit` en 0.6.0. `Result[Unit, E]` se difiere; retorno distinto de `Unit` produce `PGS-E1702`. El harness Rust no declara retorno.

### 9.5 `Ptr` y `CStr` en firmas

`Ptr[T]` es `*mut T` interno; `CStr` es `&CStr`. El codegen debe decidir `*mut` vs `*const`; sin sintaxis, usar `*mut` para opacos y documentar que el usuario no lo desreferencia. `foreign` no exporta.

### 9.6 `format` e interpolación

`format("#{x}")` se compila a `Show`; no hay variádicos. Si `x` es `String`, `Show`; si es `&Str`, `Show`; si es un record, `@@derive(Debug)` **no** basta; se requiere `ritual Show`. Documentar.

### 9.7 `Map`/`Set` ordering

`HashMap`/`HashSet` no garantizan orden; el lenguaje no promete orden. Si se necesita, `std.collections`; no cambiar el core.

### 9.8 `Rc`/`Arc` y hilos

§11.7 dice que `Arc` comparte entre hilos, pero no hay hilos en el core. `Arc` sigue existiendo para FFI/futuro; no se garantiza `Send`/`Sync` en la superficie. Si se usa `std.concurrent`, es explícito.

### 9.9 Códigos exactos

No añadir códigos. Los checks nuevos deben mapear a un código existente. Si no hay código adecuado, se abre una ADR y se retira/mergea otro; el límite 160 es duro.

---

## 10. Ruta de auto-hospedaje

| Etapa | Qué se escribe en PenguScript | Backend |
|---|---|---|
| H0 | nada; compilador Rust | Rust |
| H1 | lexer/parser/HIR | Rust |
| H2 | checker/tipos/ownership | Rust |
| H3 | codegen/LIR + CLI básico | Rust |
| H4 | CLI/LSP completos | Rust |
| H5 | bootstrap completo; compilador se compila a sí mismo | Rust |

Antes de H3, `std` debe tener: `std.fs` completo, `std.process`, `std.toml`, `std.json`, `std.digest`, `std.semver`, `std.term`, `std.glob`, `std.archive` (para vendor), `std.net` no es necesario para el compilador (solo `git` externo).

Reglas de port:

- Cada crate Rust tiene un `scroll` homólogo; los tests se mantienen.
- No usar `HashMap` iteration; `Vec` ordenado.
- No usar closures almacenadas; funciones.
- No usar `dyn`/`impl Trait`; enums.
- No usar `unsafe`; solo runtime FFI.
- No usar `?` en closures; funciones.
- El compilador debe compilarse con `pengu` y producir el mismo corpus.

---

## 11. Apéndices

### A. Cobertura de sintaxis

| Sección | Constructo | Fase | Test |
|---|---|---|---|
| §2 | BOM, CRLF, tabs, indent | F1 | lexer |
| §2 | comentarios/doc | F1 | lexer |
| §2 | XID | F1 | unicode |
| §2 | keywords | F1 | lexer |
| §2 | literales numéricos | F1/F2 | parser/type |
| §2 | char/string/raw/byte/C | F1 | lexer |
| §2 | interpolación | F1/F2 | parser/type |
| §2 | arrays/vec/map/set/tuplas | F1 | parser |
| §2 | rangos | F1 | parser |
| §2 | separadores | F1 | parser |
| §3 | roots/scroll/summon | F1/F2 | modules |
| §3 | visibilidad | F2 | names |
| §3 | grimoire | F1/F2 | parser/check |
| §3 | Tome | F3 | driver |
| §2/§19 | `.d.pengu` | F1/F2 | parser/check |
| §4 | tipos | F2 | types |
| §4 | refs | F2 | check |
| §4 | genéricos | F2 | types |
| §5 | bind/morph/sigil/relic | F2 | check |
| §6 | if/unless/do/for/while/loop | F2 | check |
| §7 | funciones/closures | F2 | check |
| §8 | records/sums/derive | F2 | check |
| §9 | patterns/match | F2 | check |
| §10 | colecciones | F2 | check |
| §11 | ownership | F2 | check |
| §12 | pacts/rituals | F2 | check |
| §13 | genéricos/bounds | F2 | check |
| §14 | operadores/casts/`?` | F2 | check |
| §15 | Option/Result/panic | F2 | check |
| §16 | FFI/curse | F2 | check |
| §17 | tests/doc | F1/F3 | parser/codegen |
| §19 | grammar | F1 | parser |
| §20 | diagnostics | F1/F2 | tests |

### B. Checklist del checker

- [x] Resolución de módulos/imports/visibilidad.
- [x] Sin globales.
- [x] Tipos nominales; sin coerción.
- [x] Inferencia local; literales.
- [x] Funciones: aridad, tipos, retorno, `Never`.
- [x] Closures: captura, `Fn` kinds, no `return`/`?`.
- [x] Records/sums: campos, variantes, `..base`.
- [x] Patterns: exhaustividad, guards, `@`, `..`.
- [x] Colecciones: `Eq+Hash`, Float.
- [x] Ownership: move/Copy/Clone/borrow/NLL/drop.
- [x] Refs: params/locales, no escapes, methods.
- [x] Pacts: métodos, defaults, superpact, coherencia.
- [x] Genéricos: bounds, turbofish, mono.
- [x] Operadores: sobrecarga, checked arithmetic, casts.
- [x] `?`: Option/Result, same error.
- [x] FFI: foreign, curse, Ptr, CStr, link.
- [x] Const eval: `sigil`, arrays.
- [x] Derives: requisitos.
- [x] Tests: `@@test`.

### C. Checklist del codegen

> Auditado 2026-11-13. `use` no se emite como item: los `summon` se resuelven
> a paths cualificados (`crate::...`), por lo que no hay alias pendientes.
> `overflow-checks = true` se emite en `[profile.dev]` y `[profile.release]`.


- [x] Tipos mapeados.
- [x] Item items: structs/enums/traits/impls/type aliases/modules/use.
- [x] Funciones/métodos/receptores.
- [x] Locals/bindings/assignments.
- [x] Control: if/match/loop/while/for/break/continue/return.
- [x] Operadores/casts/`?`/short-circuit.
- [x] Literales/colecciones/interpolación.
- [x] Patterns.
- [x] FFI/curse/Ptr/CStr.
- [x] Tests/derive.
- [x] Cargo/Tome/link.
- [x] Sourcemap.
- [x] Errores remapeados.
- [x] Overflow checks.
- [x] No Rust crudo.

### D. Diagnósticos por fase

| Fase | Familias |
|---|---|
| F1 | `E10xx`, `E19xx` sintácticos, `E20xx` de módulos |
| F2 | `E11xx`, `E12xx`, `E13xx`, `E14xx`, `E15xx`, `E16xx`, `E30xx`, `E31xx`, `E41xx`, `E60xx`, `E70xx`, `E80xx`, `E90xx` |
| F3 | `E18xx` de Cargo/Tome, `E2014` de backend |

### E. Estructura de archivos

```text
compiler/
  crates/
    pengu-span/
    pengu-vfs/
    pengu-diag/
    pengu-syntax/
    pengu-hir/
    pengu-types/
    pengu-check/
    pengu-lower/
    pengu-codegen/
    pengu-driver/
    pengu-pkg/
    pengu-os/
  tests/
    corpus/
    diagnostics/
    ownership/
    codegen/
    selfhost/
  scripts/
    check-licenses.py
    check-corpus.py
    bootstrap.sh
```

---

## 12. Decisión de arranque

El orden recomendado es:

1. **F1/F2** lexer y parser de expresiones; congelar gramática de expresiones.
2. **F2** HIR/tipos; luego ownership; luego patrones/FFI.
3. **F3** LIR/codegen; primero hello, luego control, luego colecciones, luego FFI.
4. **H1** portar lexer/parser; medir.
5. **H2/H3** portar checker/codegen; no empezar hasta que el corpus Rust esté estable.

El compilador no se declara “0.6.0 completo” hasta que las tres puertas F/C/B y la puerta H1 estén verdes.

---

*Fin del plan.*
