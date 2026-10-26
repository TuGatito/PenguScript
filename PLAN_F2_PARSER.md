# 🧩 Plan de implementación — F2: Parser, AST y recuperación

> **Estado:** **F2 implementada, verificada y cerrada.** El plan se aprobó con
> la modificación D9 (carpetas y módulos legibles por humanos) y se ejecutó
> completo. Este archivo queda como registro de diseño y resultados.
>
> **Base:** PenguScript `3.0.3` (`3f99038`). **Fases previas:** F0/F1
> implementadas en `psc/`. **Fase implementada:** F2 del
> [`AUDITORIA_AUTO_HOSPEDAJE.md`](AUDITORIA_AUTO_HOSPEDAJE.md) §9.
>
> **Regla de esta fase:** cero deuda técnica. Los huecos de F1 que aparecieron
> durante F2 se corrigieron con tests de regresión y se documentaron en
> `psc/docs/PARITY.md`.

---

## 📑 Índice

0. [Resumen ejecutivo](#-0-resumen-ejecutivo)
1. [Punto de partida verificado](#-1-punto-de-partida-verificado)
2. [Alcance: qué entra y qué no](#-2-alcance-qué-entra-y-qué-no)
3. [Decisiones de diseño](#-3-decisiones-de-diseño)
4. [Arquitectura y patrón](#-4-arquitectura-y-patrón)
5. [AST por índices](#-5-ast-por-índices)
6. [Estado del parser y recuperación](#-6-estado-del-parser-y-recuperación)
7. [Mapa gramática → parser](#-7-mapa-gramática--parser)
8. [Diagnósticos de sintaxis](#-8-diagnósticos-de-sintaxis)
9. [Huecos de F1 que hay que cerrar](#-9-huecos-de-f1-que-hay-que-cerrar)
10. [Tipos exactos](#-10-tipos-exactos)
11. [Módulos y archivos](#-11-módulos-y-archivos)
12. [Orden de implementación y checkpoints](#-12-orden-de-implementación-y-checkpoints)
13. [Tests, oráculos y paridad](#-13-tests-oráculos-y-paridad)
14. [Rendimiento y determinismo](#-14-rendimiento-y-determinismo)
15. [Criterios de aceptación (DoD)](#-15-criterios-de-aceptación-dod)
16. [Riesgos y mitigaciones](#-16-riesgos-y-mitigaciones)
17. [Decisiones que necesito de ti](#-17-decisiones-que-necesito-de-ti)
18. [Anexos](#-18-anexos)
19. [Cierre](#-19-cierre)

---

## 🎯 0. Resumen ejecutivo

F2 convierte la lista de tokens de F1 en el **mismo árbol semántico que
stage0**, con spans, recuperación de errores y un límite de profundidad, y lo
expone por CLI para poder compararlo automáticamente.

La propuesta es deliberadamente **fiel a stage0**, no un AST “bonito” nuevo:

- `NodeKind` replica los nombres y la aridad de las reglas de
  [`pengu_grammar.py`](pengu_parser/pengu_grammar.py), incluidos los
  placeholders `None` que Lark deja en el árbol.
- El AST es plano, en listas contiguas (arena), con hijos referenciados por
  enteros; no hay un `alloc` por nodo.
- El parser es recursive descent + precedencia, escribe en el AST y **nunca
  lanza** por entrada de usuario: emite diagnósticos `E0000` y produce un AST
  parcial.
- Un oráculo Python (dev-only) compara el árbol de stage0 con el de PSC sobre
  los **189 archivos** del corpus; el criterio de salida es igualdad exacta
  (salvo divergencias deliberadas y documentadas).
- Se corrigen dos huecos de F1 que F2 necesita: el plegado de cadenas
  multilínea (`.`/`->`) y la comprobación de “varios statements en una línea”
  que F1 delegó explícitamente al parser.

**Resultado esperado:** `psc parse` produce un AST determinista, con
diagnósticos útiles, sin crashes, con ASan limpio, y con paridad de árbol
demostrada contra stage0 en todo el corpus. Es la base sobre la que F3
(símbolos, tipos, checker e inferencia) podrá portar la lógica de stage0 sin
reinventar la forma del árbol.

**Esfuerzo estimado:** 6–8 semanas de una persona, alineado con la auditoría
(F2: 6–8 persona-semanas). El desglose de §12 suma ~35–40 días de trabajo
efectivo, con revisión e imprevistos.

---

## 🔍 1. Punto de partida verificado

### 1.1 Lo que F1 dejó en el árbol

`psc/` contiene 14 módulos PenguScript (~3 500 líneas de código, ~6 600 con
tests y documentación):

| Módulo | Responsabilidad |
|---|---|
| `source.pengu` | `SourceFile`: BOM, CRLF, índice de líneas, SHA-256 |
| `span.pengu` | `ByteSpan` half-open |
| `token.pengu` | `TokenKind`, `KeywordKind`, `KeywordTable` |
| `lexer_state.pengu` | Estado, opciones, `LexResult`, tablas de literales |
| `lexer.pengu` | Bucle principal, palabras, números, operadores |
| `lexer_string.pengu` | Strings, raw, triples, chars, interpolación |
| `lexer_decode.pengu` | Decodificación de literales y `antiquus` |
| `lexer_comment.pengu` | Comentarios y doc blocks |
| `lexer_antiquus.pengu` | Cuerpos C de `antiquus` |
| `lexer_indent.pengu` | `NEWLINE`/`INDENT`/`DEDENT`, `W0005` |
| `diagnostics.pengu` | `LexIssue`, render plain/ANSI/JSON |
| `token_dump.pengu` | Dump TSV canónico |
| `session.pengu` | `SourceFile` + `DiagnosticBag` + keywords + opciones |
| `main.pengu` | CLI `psc lex` / `psc version` |

Estado medido y reproducido en este árbol:

```text
pytest tests/psc -q
# -> 4 passed, 1 skipped (el oracle de 175 archivos se salta sin PSC_PARITY=1)
```

- Oracle F1: `files=175 skipped=0 failures=0`
  (`exact:146`, `antiquus:28`, `struct:1`).
- ASan/UBSan: 208 archivos sin fugas.
- Fuzz nativo: 1 000 000 de entradas sin crashes.
- Benchmark Release: ~11,8 MB/s de lexado (3,0 MB, 760 001 tokens).
- Golden: 14 dumps de tokens y 10 de diagnósticos.

Los contratos que F2 va a consumir están congelados y probados:

- `Token` es POD: `kind`, `kw`, `start`, `end`, `line`, `col`, `aux`.
- `NEWLINE` lleva en `aux` el ancho de indentación; `INDENT`/`DEDENT` son de
  ancho cero.
- `TokStringLit.aux` indexa `LexResult.strings` (`StringInfo`), y sus
  `StringPart` están en `LexResult.parts`.
- `TokAntiquusBody.aux` indexa `LexResult.antiquus` (`AntiquusInfo`).
- Los comentarios son trivia (`LexResult.comments`) y no llegan al parser.
- `SourceFile.text` conserva CRLF; `line`/`col` son 1-indexed y `col` es
  columna de **byte**.

### 1.2 Lo que F2 tiene delante

Corpus real medido hoy (sin contar `psc/build/`):

| Raíz | Archivos `.pengu` |
|---|---:|
| `std/` | 49 |
| `tests/` (incluye `tests/conformance/`) | 126 |
| `psc/src/` | 14 |
| **Total** | **189** |

Métricas de stage0 sobre esos 189 archivos (parse real de Lark, sin contar
arranque):

```text
files=189  bytes=2 989 802
nodos=279 639  tokens retenidos=154 126
profundidad máxima del AST=52
tiempo=8.726 s  -> 0.34 MB/s
```

Ese 0,34 MB/s es la referencia: F2 debe ser mucho más rápido y, sobre todo,
mucho más simple de medir.

### 1.3 Lo que F1 deliberadamente dejó a F2

1. **Parser, AST y recuperación** (esta fase).
2. **“Múltiples statements en una línea”**: F1 lo documenta como divergencia
   (`.PARITY.md` #12) y lo delega al parser. Ejemplo:
   ```pengu
   var x is 1 var y is 2
   ```
   stage0 falla en `E0000` línea 2, columna 16.
3. **Cadenas multilínea**: el lenguaje documenta
   ```pengu
   let slug is calling raw
       .trim
       .lower
       .replace with " ", "-"
   ```
   stage0 lo resuelve plegando texto antes del lexer. El lexer de F1 no lo
   hace: emite `NEWLINE` + `INDENT` + `.trim` + ... + `DEDENT`. Ningún archivo
   del corpus actual usa esta forma, por eso el oracle F1 no lo detectó. F2 no
   puede parsearlo bien sin tocar F1 o sin un filtro de tokens; §9 propone la
   corrección pequeña y testeada.
4. **Interpolación**: F1 guarda los rangos de `{expr}` en `StringPart`, pero no
   parsea la expresión. Stage0 la re-parsea bajo demanda en codegen. §9 propone
   una API de F2 para parsearla sin cambiar el árbol de archivo.

### 1.4 Qué no se toca

- `std/` no se modifica.
- `pengu_parser/` (stage0) no se modifica, salvo que aparezca un bug
  bloqueante y lo acordemos aparte. El parser nuevo vive en `psc/`.
- `AUDITORIA_AUTO_HOSPEDAJE.md` no se edita.
- `CHANGELOG.md` no se toca hasta el cierre/release de PSC.

---

## 📦 2. Alcance: qué entra y qué no

### 2.1 Entra en F2

- AST plano por índices, con spans, placeholders y tablas laterales.
- Parser recursive descent completo de la gramática de `pengu_grammar.py`:
  - declaraciones top-level: `import`, `include`, `link`, `ldflag`,
    `insignia`, `const`, `var`, `let`, `rune`, `echo`, `omen`, `alias`,
    `seal`, `concept`, `bind`, `weave`, `enchanting`, `antiquus`, `declare`,
    `test`, `when` top-level;
  - statements: `set`/compound, `if`/`unless`, `while`, `for` (rango e `in`),
    `when`, `with`, `unsafe`, `defer`/`errdefer`, `banish`, `return`,
    `break`/`continue` con label, `expr_stmt`, loops etiquetados;
  - expresiones con la precedencia exacta de `LANGUAGE.md` §6.1 y la
    gramática real (que tiene matices, p. ej. `and`/`or` booleanos vs `|`/`&`);
  - tipos: `ref to`, `frozen`, `weave`, `array`, `slice`, `many`, `list`,
    `map`, `maybe`, `result`, `opaque`, `shard`, `where`, tuplas, tipos
    cualificados y genéricos;
  - `judge`/`judge over`, `when` con payloads, guardas, or-patterns y
    narrowing;
  - `with:` como expresión y como statement, `do:`, `or else`/`or return`/
    `or:`, `lambda`, literales indentados, arrays, mapas, `donum`, `defined`,
    `with` struct-init corto;
  - `antiquus` con su cuerpo C.
- Recuperación de errores: nodos `Error`, sincronización, tope de errores,
  garantía de progreso, límite de profundidad.
- Diagnósticos `E0000` con mensaje, `help` y `note`; render plain/ANSI/JSON.
- CLI `psc parse` (y alias `psc ast`) con `--check`, `--stdin`,
  `--diagnostics`, `--no-header`, `--max-errors`, `--stop-after-first`.
- AST dump canónico para golden y oráculo.
- Tests unitarios, de corpus, golden, diferenciales contra stage0, fuzz,
  ASan/UBSan y benchmark.
- Documentación: `psc/docs/AST.md`, actualización de `README.md`,
  `PARITY.md`, `OWNERSHIP.md`.
- Corrección de los dos huecos de F1 de §1.3 (cadena multilínea y
  multi-statement), con regresión.

### 2.2 No entra en F2 (explícito)

- Símbolos, scopes, imports resueltos, tipos semánticos, checker o inferencia
  (**F3**).
- Codegen, DCE o C (**F4**).
- Formatter (`fmt`), documentación (`doc`), LSP (**F7/F8**).
- Parseo incremental o caché de AST.
- Un CST con trivia; los comentarios siguen en `LexResult.comments`.
- Cambiar `std/` o el compilador Python.
- Nuevos códigos de diagnóstico: la sintaxis sigue siendo `E0000`, como en
  stage0.
- JSON completo de tokens (sigue diferido).
- Reemplazar `pengu_parser` en el CLI actual; `psc` es un binario separado.

---

## 🧠 3. Decisiones de diseño

Estas son las decisiones que condicionan F3/F4. Las recomendadas son las que
propongo; al final hay una lista para que marques.

### D1 — Forma del AST: fiel a stage0 vs AST canónico nuevo

- [x] **Recomendado: fiel a stage0.**
  - `NodeKind` replica los nodos de `pengu_grammar.py` (`file`, `top_stmt`,
    `stmt`, `weave_decl`, `add`, `custom_type`, …), incluyendo wrappers y
    placeholders `None`.
  - El AST dump se puede comparar 1:1 con el árbol de Lark (normalizando solo
    texto/CRLF/`None`), así que el gate de F2 es medible y fuerte.
  - F3/F4 pueden portar la lógica de stage0 nodo a nodo, sin reinterpretar
    formas; esto reduce el riesgo en las dos fases más grandes.
  - Se añaden helpers de acceso (`ast_child_node`, `ast_child_token`,
    `ast_optional`, `ast_label`) para que el código de F3 sea legible y no
    dependa de índices mágicos.
  - Se documentan las rarezas heredadas (por ejemplo, `when_variant` vacío
    para `maybe none`, la aridad variable de `arrow_access`, `to_expr` como
    cast/rango, `for_in_stmt` sin placeholder para el segundo nombre) en
    `psc/docs/AST.md`. No son deuda oculta: son contrato explícito.
- [ ] Alternativa: AST canónico “limpio” (sin wrappers ni `None`).
  - Más agradable de leer, pero exige un traductor Lark→AST en el oráculo,
    reescribir todos los accesos de F3/F4 y re-derivar semántica que stage0 ya
    tiene resuelta. Mayor riesgo y más tiempo; no lo veo para F2.

**Por qué:** la prioridad es calidad y llegar al auto-hospedaje con el menor
riesgo posible. Un AST fiel es el “contrato stage0” que ya está validado por
1 400 tests; un AST nuevo sería un segundo contrato que hay que validar
además.

### D2 — Almacenamiento: arena plana en listas, no punteros

- [x] **Recomendado:** `Ast` con `nodes as list of Node`,
  `children as list of int` y `labels as list of LoopLabel`.
  - Los hijos se codifican en un entero: `0` ausente, `>0` nodo `id+1`,
    `<0` token `-id-1`.
  - `Node` es POD de 6 enteros: `kind`, `start`, `end`, `first_child`,
    `child_count`, `aux`.
  - No hay `alloc` por nodo ni punteros que se invaliden al crecer la lista.
  - `banish ast` libera las tres listas de golpe.
- [ ] Alternativa: `std.arena` + punteros/refs recursivos.
  - La arena ya está auditada, pero para nodos POD de tamaño fijo una `list`
    contigua hace lo mismo con menos indirección y mejor localidad. No
    necesitamos memoria variable por nodo. `std.arena` se usará en F3 para
    strings/tipos internados, no para el AST.

### D3 — Cadena multilínea: corregir el lexer de F1

- [x] **Recomendado:** añadir a `LexOptions` un flag
  `fold_chain_continuations` (default `true`) y, en `scan_newline`, si la
  línea siguiente empieza por `.` o `->` y no hay líneas en blanco ni
  comentarios en medio, **no emitir `NEWLINE`** y dejar la posición en el
  operador. Así el flujo de tokens coincide con el texto plegado de stage0 y
  no hay `INDENT`/`DEDENT` espurios.
  - Test nuevo `psc/tests/fixtures/chain_multiline.pengu`.
  - El oracle F1 y los golden actuales deben seguir dando 0 diferencias.
  - Se actualiza `PARITY.md`: la cadena deja de ser divergencia y pasa a ser
    comportamiento soportado.
- [ ] Alternativa: un filtro de tokens en F2 que elimine `NEWLINE`/`INDENT`/
  `DEDENT` de las continuaciones. Es más frágil (hay que emparejar niveles) y
  deja el lexer de F1 sin cubrir una feature documentada. No.

### D4 — Interpolación de strings

- [x] **Recomendado:** el parser de archivo **no** parsea las expresiones de
  interpolación (stage0 tampoco lo hace en `parse`); guarda el `TokStringLit`
  y su `StringInfo`. Se añade una API bajo demanda
  `parse_interpolation_expr` que, para un `StringPart` de tipo `SegInterp`,
  extrae el texto, lo lexa/parsea y devuelve un bundle owned con
  `SourceFile`+`LexResult`+`Ast` (posiciones relativas a la expresión).
  - F3/F4 la usan al compilar el string.
  - No cambia la aceptación/rechazo del archivo, así que la paridad con
    stage0 se mantiene.
  - Cierra el punto que F1 dejó abierto sin inventar un nodo distinto para
    strings interpolados.
- [ ] Alternativa: parsear todas las interpolaciones dentro de `parse_file`.
  Detectaría antes errores, pero divergiría de stage0 y obligaría a un nodo
  `StringInterp` que luego F3 tendría que reconciliar. No para F2.
- [ ] Alternativa: no ofrecer API y dejar que F3 lo haga. Es deuda; no.

### D5 — Política de recuperación

- [x] **Recomendado:** recuperar por defecto.
  - `ParseOptions.max_errors = 100`, `stop_after_first = false`.
  - `--stop-after-first` y `max_errors` configurables por CLI y tests.
  - Sincronización en `NEWLINE`, `DEDENT`, `EOF` y starters de declaración/
    statement.
  - Si un error no consumió ningún token, se fuerza un avance: **progreso
    garantizado**.
  - Tras un error se entra en “panic mode” hasta el siguiente separador para
    no emitir cascadas.
  - Los errores del lexer (`TokError`) no se duplican: se saltan y se sigue.
  - El oráculo de errores compara **el primer** diagnóstico (stage0 aborta en
    el primero); el CLI puede mostrar varios.
- [ ] Alternativa: abortar al primer error como stage0. Es más simple, pero
  malo para LSP y para la experiencia de usuario. No.

### D6 — Límite de profundidad

- [x] **Recomendado:** `MAX_PARSE_DEPTH = 512`, como stage0.
  - Pre-scan de delimitadores `()[]{}` sobre los tokens antes de parsear:
    emite `E0000` en el token 513, con línea/columna. Esto reproduce el
    comportamiento de stage0 (B7) y evita que el parser recursivo llegue a
    desbordar la pila.
  - Guard adicional `enter_depth`/`leave_depth` en expresiones, tipos y
    bloques, por si la recursión no viene de un delimitador (unarios, `if`
    anidados, etc.).
  - Un fallo de profundidad deja `ok=false` y un `Error` node; no hay
    `RecursionError` ni segfault.
- [ ] Alternativa: confiar solo en el guard del parser. Es suficiente para
  paréntesis, pero la posición no coincidiría con stage0 y algunos caminos
  (unarios) no tienen delimitador. El pre-scan es barato.

### D7 — Formato del AST dump

- [x] **Recomendado:** dump indentado canónico, **sin posiciones** por
  defecto.
  - Nodo: `nombre_del_nodo`.
  - Token: `"texto escapado"` (comillas incluidas).
  - Placeholder: `_`.
  - Loop etiquetado: `for_in_stmt @label "outer"`.
  - `antiquus`: se imprime el cuerpo C ya dedentado (no el placeholder).
  - CRLF se normaliza a LF **solo para el dump** (el AST y los spans
    conservan los bytes originales).
  - Las posiciones/columnas se prueban aparte contra F1 y en fixtures; no se
    meten en el dump porque stage0 inserta tokens sintéticos en el struct-init
    corto y sus columnas no son comparables.
- [ ] Alternativa: incluir `@line:col` en cada token. Rompe la paridad en
  `with a, b` (tokens insertados por stage0) y hace los golden mucho más
  grandes. No.

### D8 — CLI

- [x] **Recomendado:** `psc parse <archivo>` como comando principal y
  `psc ast` como alias.
  - `--check` (solo diagnósticos), `--stdin`, `--diagnostics=plain|json`,
    `--color`/`--no-color`, `--quiet`, `--no-header`,
    `--max-errors=N`, `--stop-after-first`.
  - `psc lex` se queda igual; `psc version` pasa a `0.2.0 (F2)`.
- [ ] Alternativa: solo `psc ast`. Menos discoverable; el alias es barato.

### D9 — Carpetas y módulos (cambio aprobado)

- [x] **Aprobado por el usuario:** dividir el parser en carpetas y módulos
  legibles por humanos, no en un `parser_body.pengu` monolítico.
  - `ast/`: `kind`, `node`, `dump`.
  - `parse/`: `state`, `diagnostics`, `types`, `api`.
  - `parse/expr/`: `atoms`, `calls`, `util`, `ops` (precedencia).
  - `parse/stmt/`: `core` (statements/bloques), `values` (hooks de valor).
  - `parse/patterns/`: `core`, `judge`.
  - `parse/decl/`: `core` (declaraciones top-level).
  - La recursión mutua se resuelve con `PsHooks` (punteros a función) en
    `PsParser`; cada módulo tiene una responsabilidad y un tamaño revisable.
- [ ] Alternativa descartada: un único `parser_body.pengu` de ~1 500 líneas.

### D10 — Alcance de las correcciones a F1

- [x] **Recomendado:** solo dos cambios, ambos con regresión:
  1. plegado de cadenas multilínea en `lexer.pengu` (D3);
  2. nada más en el lexer; “múltiples statements” se implementa en el parser.
  - Si el parser descubre otro bug de F1 (p. ej. un span mal puesto), se
    corrige con test y se anota en `PARITY.md`; no se reabre F1 en bloque.
- [ ] Alternativa: no tocar F1 y resolver todo en F2. Dejaría el lexer sin una
  feature documentada y obligaría a un filtro de tokens; peor.

---

## 🏗️ 4. Arquitectura y patrón

### 4.1 Pipeline de F2

```text
SourceFile (F1)
    │
    ▼
LexResult (F1: tokens + strings + parts + chars + antiquus + comments)
    │
    ├──▶ pre-scan de profundidad (tokens) ──▶ E0000 si > 512
    │
    ▼
Parser (estado mutable, sin heap propio salvo el AST)
    │  recursive descent + precedencia
    │  construye nodos en Ast
    ▼
ParseResult { ok, root, ast, error_count }
    │
    ├──▶ DiagnosticBag (F1) con E0000 / help / note
    └──▶ AstDump (S-expression indentada canónica)
```

### 4.2 Principios

1. **Una sola pasada sobre los tokens.** No se re-lexa ni se re-parsea nada
   durante el parseo de archivo.
2. **Sin estado global.** Todo vive en `Parser`; el AST se transfiere al
   `ParseResult`.
3. **Sin excepciones para entrada de usuario.** Los errores son diagnósticos y
   nodos `Error`.
4. **Sin asignación por token/nodo** salvo crecimiento amortizado de las dos
   listas del AST. Los nombres y literales se referencian por índice de token,
   no se copian.
5. **Determinismo.** Los nodos se crean en orden de fuente; no se itera un
   `map` para emitir nada; el dump no lleva timestamps ni rutas absolutas.
6. **Ownership explícito.** El parser toma prestados `SourceFile` y
   `LexResult`; es dueño del `Ast` que devuelve. El llamador mantiene vivos
   `SourceFile` y `LexResult` mientras use el AST (igual que un AST que
   referencia tokens).
7. **Fidelidad a stage0.** La forma del árbol es contrato; los helpers la
   hacen usable, no la esconden.
8. **Errores útiles.** Cada `ParseIssue` tiene mensaje, `help` y, cuando
   aporta, `note`; los códigos siguen siendo `E0000`.

### 4.3 Flujo de ownership

```text
Session
  ├── SourceFile      (dueño: Session)
  ├── DiagnosticBag   (dueño: Session)
  ├── KeywordTable    (dueño: Session)
  └── LexOptions

parse_file(src: ref, bag: ref, lex: ref, opts) -> ParseResult
  ├── Parser (stack)  presta src/lex/bag
  └── Ast             dueño: ParseResult
```

| Recurso | Dueño | Liberación |
|---|---|---|
| `SourceFile` | `Session` / llamador | `banish session` |
| `LexResult` | llamador | `banish lex` |
| `Ast.nodes/children/labels` | `ParseResult` | `banish result` |
| `Parser` | pila de `parse_file` | no tiene heap fuera del AST |
| Mensajes temporales de error | parser | `defer banish` tras `emit` |
| `StringBuilder` del dump | `ast_dump` | `defer banish` |
| Bundle de interpolación | llamador | `banish bundle` |

**Regla:** el AST **no** libera tokens ni fuente; solo libera sus propias
listas. El `ParseResult` no se debe copiar y liberar dos veces; se transfiere
por valor una vez, como `LexResult` en F1.

---

## 🧱 5. AST por índices

### 5.1 `Node`

```pengu
## Nodo POD del AST. `kind` es la regla de stage0; `start`/`end` son bytes.
##
## ## Memoria
## Valor puro: no tiene heap.
rune Node derive Par:
    kind as NodeKind
    start as int
    end as int
    first_child as int
    child_count as int
    aux as int
```

- `aux` se usa por tipo de nodo (documentado en `AST.md`):
  - operadores binarios/comparaciones/unarios/rango: índice del token del
    operador (para mensajes y para el hint de `and`), `0` si es sintético;
  - `base_type`: `0` (el texto está en el token hijo);
  - resto: `0` reservado.
- `start`/`end` cubren el constructo completo (primer token al último token
  consumido). En nodos sintéticos de recuperación, el span puede ser de ancho
  cero.

### 5.2 Codificación de hijos

Un hijo se guarda como un `int` en `Ast.children`:

| Valor | Significado |
|---:|---|
| `0` | ausente (`None` de Lark) |
| `> 0` | nodo `id = valor - 1` |
| `< 0` | token `id = -valor - 1` |

Helpers:

```pengu
weave enc_node with id as int into int        # id + 1
weave enc_token with id as int into int       # -(id + 1)
weave child_is_node with c as int into bool   # c > 0
weave child_is_token with c as int into bool  # c < 0
weave child_node with c as int into int       # -1 si no es nodo
weave child_token with c as int into int      # -1 si no es token
```

Ventajas:

- 4 bytes por hijo, contiguos.
- Un nodo hoja de token no ocupa un `Node`; solo un `int` en el padre.
- El AST es serializable y determinista; los IDs son estables en orden de
  fuente.
- No hay `banish` por nodo.

### 5.3 `Ast`

```pengu
## Etiqueta de un loop etiquetado (`outer: for ...`).
rune LoopLabel derive Par:
    node as int
    token as int

## Arena del AST.
##
## ## Memoria
## `banish ast` libera las tres listas. Los nodos y las etiquetas son POD.
rune Ast derive Nexus:
    nodes as list of Node
    children as list of int
    labels as list of LoopLabel
```

`enchanting Ast` expone:

- `node_new(kind, start, end, aux)` → id.
- `add_child(parent, child)` / `add_token(parent, token_index)` /
  `add_absent(parent)`.
- `child_count(id)`, `child(id, slot)`, `child_node(id, slot)`,
  `child_token(id, slot)`, `optional_node`, `optional_token`.
- `label(node)` / `set_label(node, token)`.
- `kind(id)`, `span(id)`.
- `validate()` (solo debug/tests): comprueba que cada `first_child/count` cae
  dentro de `children`, que cada `child` codifica un índice válido y que no
  hay ciclos (el AST es un DAG/árbol por construcción).

### 5.4 Placeholders `None`

Lark, con `maybe_placeholders=True`, inserta `None` en los grupos `[...]`
opcionales. El AST los replica con `0` para que la aridad sea fija:

| Nodo | Hijos |
|---|---|
| `import_stmt` | `dotted_path`, alias (`0` si no) |
| `var_decl` | nombre, tipo (`0`), valor |
| `const_decl` | nombre, tipo (`0`), valor |
| `weave_decl` | `attributes`, `weave_modifier*`, nombre, `shard_params?`, `param_list?`, tipo?, `stmt+` |
| `if_stmt` | `if_cond`, `block`, `else_block?` |
| `when_clause` | patrón, payload?, guard?, body |
| `param` | nombre, tipo, default? |
| `custom_type` | `dotted_path`, args? (`0` si no hay `of`) |
| `return_stmt` | valor(es); `0` si es `return` desnudo |
| `break_stmt` / `continue_stmt` | label? (`0` si no) |

Los grupos `(...)` opcionales **no** generan placeholder (Lark no lo hace), y
por eso `for_in_stmt` tiene 3 hijos con un nombre y 4 con dos:
`[nombre, (nombre2), expr, block]`. Esto se replica tal cual y se documenta.

### 5.5 Nodos especiales que no vienen de stage0

- `NodeKind.NdError`: nodo de recuperación. Hijos: los que se hayan podido
  parsear; `aux` reservado. `ast_dump` lo imprime como `error`.
- No se replica `labeled_loop`: stage0 lo desenvuelve en
  `_attach_loop_labels`; PSC escribe la etiqueta directamente en
  `Ast.labels` sobre el nodo `for_*`/`while`.
- No se replica `ANTIQUUS_BODY_PLACEHOLDER`: el lexer de F1 ya entrega
  `TokAntiquusBody`.
- No se replica `_expand_short_struct_inits` como texto: el parser construye
  directamente `field_init(nombre, var_ref(nombre))` para `with a, b`.

### 5.6 Ejemplo de construcción

```pengu
# let x as int is a + b * 2
let_decl
  var_name_list
    x
  base_type
    int
  add
    var_ref
      a
    mul
      var_ref
      b
    int_lit
      2
```

En el AST:

```text
Node(let_decl, first=0, count=3)
  children[0] = enc_node(var_name_list)
  children[1] = enc_node(base_type)
  children[2] = enc_node(add)
Node(var_name_list, first=3, count=1)
  children[3] = enc_token(x)
Node(add, first=4, count=2, aux=op_plus)
  children[4] = enc_node(var_ref)
  children[5] = enc_node(mul)
...
```

---

## ⚙️ 6. Estado del parser y recuperación

### 6.1 `Parser`

```pengu
## Estado mutable de un parseo. Vive en la pila de `parse_file`.
##
## ## Memoria
## No tiene destructor: `ast` se transfiere al `ParseResult`. Si se añade una
## salida anticipada, debe transferir el AST igualmente.
rune Parser:
    src as ref to psource.SourceFile
    bag as ref to diag.DiagnosticBag
    lex as ref to LexResult
    tokens as ref to list of Token
    opts as ParseOptions
    pos as int
    depth as int
    errors as int
    panic as bool
    stop as bool
    last_error_pos as int
    root as int
    ast as Ast
```

`Parser` no se expone fuera de `parser*.pengu`; la API pública es
`parse_file`/`parse_expr_tokens`.

### 6.2 Cursor de tokens

- `peek(p)`, `peek_at(p, n)`, `current_kind`, `current_kw`.
- `advance(p)` avanza uno y devuelve el token anterior.
- `check(p, kind)`, `check_kw(p, kw)`, `accept(p, kind)`,
  `accept_kw(p, kw)`.
- `expect(p, kind, issue)` consume o emite error sin consumir.
- `token_is_word(p, tok, "self")`: compara el rango del token con un literal,
  sin asignar string. Sirve para soft keywords (`self`, `unsafe`, `over`,
  `frozen`, `inline`, `ritual`, `do`, `type`, `size`, `main`, `ok`, `err`).
- `token_text(p, index)` → `string` owned (solo para errores/dump; no en
  bucles calientes).
- `skip_error_tokens(p)`: los `TokError` del lexer ya tienen su `E0000`; el
  parser los salta para no duplicar.

### 6.3 Recuperación

Reglas concretas:

1. `emit_issue(p, issue, start, end, detail)`:
   - si `start == last_error_pos` y ya hay un error ahí, no duplica;
   - llama a `parse_diagnostics.emit` (bag) y suma `errors`;
   - si `errors >= max_errors` o `stop_after_first`, `stop = true`.
2. `synchronize(p, context)`:
   - si `panic`, avanza hasta `NEWLINE`, `DEDENT`, `EOF` o starter de
     declaración/statement (`import`, `weave`, `rune`, `var`, `let`, `set`,
     `if`, `while`, `for`, `return`, …);
   - no consume el `DEDENT` del bloque exterior: el llamador decide.
   - al salir, `panic = false`.
3. `parse_stmt_list(p, end_kind)`:
   - salta `NEWLINE` y basura;
   - si `DEDENT`/`EOF`, termina;
   - parsea un `stmt`;
   - comprueba “múltiples statements en una línea” (§9.2);
   - si no hubo avance, `advance(p)` y emite `InternalProgress` (no debería
     ocurrir; el test de fuzz lo vigila).
4. `parse_file`:
   - salta `NEWLINE`;
   - parsea `top_stmt` hasta `EOF`;
   - si no hay avance, avanza y sincroniza;
   - crea `start -> file` con los `top_stmt` como hijos.
5. `parse_block`:
   - tras `:` si hay `NEWLINE`: consume, exige `INDENT`, parsea `stmt+` hasta
     `DEDENT`, consume `DEDENT`;
   - si no: parsea un `simple_stmt`, exige `NEWLINE`;
   - bloque vacío: `EmptyBlock` (stage0 exige `stmt+`).
6. `parse_expr`/`parse_type`:
   - si el token actual no puede empezar la construcción, emiten
     `ExpectedExpression`/`ExpectedType` y devuelven un `Error` de ancho cero;
   - no consumen el token para que el llamador sincronice.

### 6.4 Garantía de progreso

Cada bucle del parser cumple una de estas dos condiciones:

- consume al menos un token por iteración, o
- rompe explícitamente (`EOF`, `DEDENT`, `stop`).

Además, `parse_file` y `parse_stmt_list` comparan `pos` antes/después de cada
iteración y fuerzan un avance si no cambió. El fuzz de parser comprueba que
100 000 entradas terminan y que `pos` avanza.

### 6.5 Profundidad

- `MAX_PARSE_DEPTH = 512`.
- `pre_scan_depth(p)` recorre los tokens y cuenta `(`/`[`/`{`; al 513 emite
  `MaxDepth` en ese token con línea/columna y devuelve `false`.
- `enter(p)`/`leave(p)` alrededor de:
  - `parse_expr`, `parse_type`, `parse_pattern`, `parse_block`;
  - `parse_unary` (cadenas de `not`/`-`);
  - `parse_postfix` (por si una cadena larga).
- Si `depth > max_depth`, emite `MaxDepth` una vez, `stop=true` y devuelve
  `Error`.
- Los paréntesis anidados se rechazan en el pre-scan con la misma
  línea/columna que stage0 (probado con 513/600/1 000).
- Los bloques se controlan con el guard de `parse_block`; se prueba el mismo
  caso adversarial. Si la posición difiere de stage0 en indentaciones
  patológicas, se documenta (la aceptación/rechazo sí coincide).

---

## 🗺️ 7. Mapa gramática → parser

### 7.1 Precedencia (de menor a mayor)

La tabla de `LANGUAGE.md` §6.1 y la gramática real no son idénticas; manda la
gramática, que es lo que stage0 acepta. Funciones:

| Nivel | Regla de gramática | Función |
|---:|---|---|
| 1 | `or else`, `or return`, `or:` | `parse_or_else` |
| 2 | `try` | `parse_try` |
| 3 | `if … then … else`, `when … then … else`, `judge`, `judge over`, `for … then` | `parse_try` → `parse_if_expr` / `parse_when_expr` / `parse_judge` / `parse_for_comp` |
| 4 | `or` booleano | `parse_bool_or` |
| 5 | `and` booleano | `parse_bool_and` |
| 6 | comparaciones, `is present`, `is true/false`, `in`, `not in` | `parse_comparison` |
| 7 | `..`, `to` | `parse_range` |
| 8 | `\|` | `parse_bit_or` |
| 9 | `&` | `parse_bit_and` |
| 10 | `^` | `parse_bit_xor` |
| 11 | `<<`, `>>` | `parse_shift` |
| 12 | `+`, `-` | `parse_add` |
| 13 | `*`, `/`, `%` | `parse_mul` |
| 14 | unarios | `parse_unary` |
| 15 | `calling`, postfix | `parse_calling` / `parse_postfix` |
| 16 | átomos | `parse_primary` |

Matices que se implementan explícitamente:

- `list_expr` (argumentos, arrays, mapas, struct fields, defaults, literales
  indentados) **no** incluye `and`/`or` booleanos; por eso
  `calling f with a and b` produce `bool_and(call, b)` como en stage0, y el
  checker de F3 lo rechaza con `E0005` (comportamiento actual).
- `value_expr` y `list_value_expr` incluyen `if`/`unless`/`while`/`for` como
  constructos con valor, además de `expr`/`list_expr`.
- `expr_no_cast` (cotas de `for ... from ... to ...`) no admite `try`,
  `if_expr`, `judge` ni `or else`; replica la regla.
- `guard_expr` (guardas de `when`) tiene su propia jerarquía restringida;
  no admite llamadas ni `at` con expresiones complejas.
- `to` se usa tanto para rango (`a to b`) como para cast (`(a to int)`); el
  nodo es el mismo `to_expr`, igual que stage0.
- `at` es postfix y su índice es un `unary_no_cast`/`slice_range`; el error de
  precedencia de `set xs at n - 1 is v` se detecta en el target y se emite
  `AtIndexPrecedence` con el `help` de stage0.
- `and` como separador solo se admite donde la gramática lo permite
  (`shard_params`, `where_clause`, `derive_clause`, `generic_args`,
  `custom_type`, `fn_param_list`, `when_payload`, `omen` fields). En
  `param_list`, `arg_list`, `struct_init`, `array_lit` y `map_lit` **no**;
  si aparece, se emite `LegacyAndSeparator` con el mismo texto de ayuda que
  stage0.

### 7.2 Statements

| Construcción | Función | Nodo(s) |
|---|---|---|
| bloque `:` + indent | `parse_block` | `block` + `stmt*` |
| bloque de una línea | `parse_simple_stmt` | `block` + `stmt` |
| `var`/`let`/`const`/`static var` | `parse_var_like` | `var_decl`/`let_decl`/`const_decl`/`static_var_decl` |
| `set` / `set +=` | `parse_set` | `set_stmt`/`compound_set_stmt` |
| `if`/`unless`/`while`/`for` | `parse_if_like` | `if_stmt`/`unless_stmt`/`while_stmt`/`for_range_stmt`/`for_in_stmt` |
| `when` statement | `parse_when_stmt` | `when_stmt` + `when_else_plain`/`when_else_when` |
| `with target:` | `parse_with_stmt` | `with_stmt` + `stmt*` |
| `unsafe:` | `parse_unsafe` | `unsafe_stmt` + `block` |
| `defer`/`errdefer` | `parse_defer` | `defer_stmt` |
| `banish` | `parse_banish` | `banish_stmt` |
| `return`/`break`/`continue` | `parse_return`/`parse_break`/`parse_continue` | `return_stmt`/`break_stmt`/`continue_stmt` |
| expresión | `parse_expr_stmt` | `expr_stmt` |
| `label: for/while` | `parse_labeled_loop` | loop + `Ast.labels` |

### 7.3 Declaraciones

| Construcción | Función | Nodo(s) |
|---|---|---|
| `import` | `parse_import` | `import_stmt` + `dotted_path` |
| `include`/`link`/`ldflag` | `parse_string_top` | `include_stmt`/`link_stmt`/`ldflag_stmt` |
| `insignia` | `parse_insignia` | `insignia_stmt` |
| `rune`/`echo` | `parse_record` | `rune_decl`/`echo_decl` + `field_decl*` |
| `omen` | `parse_omen` | `omen_decl` + `omen_variant*` |
| `alias`/`seal` | `parse_alias` | `alias_decl`/`seal_decl` |
| `concept` | `parse_concept` | `concept_decl` + `concept_method*` |
| `bind` | `parse_bind` | `bind_decl` + `weave_decl*` |
| `weave` | `parse_weave` | `weave_decl` |
| `enchanting` | `parse_enchanting` | `enchanting_decl` + `weave_decl*` |
| `antiquus` | `parse_antiquus` | `antiquus_decl` + `TokAntiquusBody` |
| `declare` | `parse_declare` | `declare_stmt` |
| `test` | `parse_test` | `test_decl` |
| `when` top-level | `parse_when_top` | `when_top_decl` + `when_top_else_*` |
| atributos | `parse_attributes` | `attributes` + `attribute*` |
| parámetros | `parse_param_list` | `param_list` + `param*` |

### 7.4 Tipos

`parse_type` replica el orden de `?type`:

- `ref to`, `frozen`, `weave` (fn type), `array of T [with size N]`,
  `slice of`, `many`, `list of`, `map of K to V`, `maybe`, `result of T [to E]`,
  `opaque`, `base_type`, `custom_type [of T, …]`, `tuple_type`, `(type)`.
- `dotted_path` para nombres cualificados.
- `shard_params` (`shard T`, `shard T and U`, `where …`).
- `where_bound`: `(NAME | type) ":" custom_type`.
- `derive_clause`: `derive A, B and C`.
- `fn_param_list`/`fn_param`: `[NAME as] type`, separados por `,` o `and`.

### 7.5 Patrones y `judge`

- `judge expr:` y `judge expr over NAME:`.
- `when_clause`: `when_pattern [with when_payload] [when_guard] -> when_body`.
- `when_pattern`: variantes separadas por `|`; variante = INT/FLOAT/string/
  char/bool/`maybe none`/`NAME(.NAME)*`.
- `when_payload`: `when_field` separados por `,` o `and`;
  `when_field: NAME [as field_pattern]`; `field_pattern` = tupla o estado
  cualificado; `field_tuple: "(" NAME ("," NAME)+ ")"`.
- `when_guard`: `if`/`when` + `guard_expr`.
- `when_body`: expresión en la misma línea, o `do_expr` con bloque.
- `else ->` o `else` + bloque.

### 7.6 `with`, `do`, `or` y lambdas

- `with` en expresión:
  - `with:` → `with_init_expr` + `stmt*`;
  - `with campo is valor, …` → `struct_init` + `field_init*`;
  - `with a, b` → `struct_init` con `field_init` sintéticos (mismo nodo que
    stage0 tras `_expand_short_struct_inits`).
- `with` en statement:
  - `with target:` → `with_stmt` + `stmt*` (sin `block`, como stage0).
- `do:` → `do_expr` + `stmt*`.
- `or:` → `or_block` + `expr` + `stmt*`.
- `lambda params into expr` → `lambda_expr`/`lambda_no_params`.
- `defined(NAME)` → `defined_expr`.

---

## 🩺 8. Diagnósticos de sintaxis

### 8.1 Código y severidad

Todo error sintáctico es `E0000` (Error), igual que stage0. No se inventan
códigos nuevos; los mensajes/help/note son la mejora de F2.

### 8.2 `ParseIssue`

```pengu
omen ParseIssue:
    ExpectedToken        # falta un token concreto
    UnexpectedToken      # token que no puede empezar la construcción
    ExpectedExpression
    ExpectedType
    ExpectedName
    ExpectedNewline
    ExpectedIndent
    ExpectedDedent
    EmptyBlock
    MultipleStatements   # "var x is 1 var y is 2"
    LegacyAndSeparator   # 'and' donde ya no es separador
    AtIndexPrecedence    # 'set xs at n - 1 is v'
    MaxDepth             # > 512 delimitadores/unarios/bloques
    InvalidSetTarget
    InvalidCallTarget
    InvalidAttribute
    InvalidDeclareParams
    InvalidWhenClause
    InvalidType
    UnexpectedEof
```

Cada variante tiene:

- `parse_issue_message(issue, detail)` → `string` owned.
- `parse_issue_help(issue)` → literal estático.
- `parse_issue_note(issue)` → literal estático.
- `emit_parse_issue(bag, src, issue, span, detail)`.

Mensajes clave (se copian de stage0 para no confundir a los usuarios):

- `MultipleStatements`:
  `"Syntax error: multiple statements on a single line require a newline delimiter"`
  en el token que empieza el segundo statement.
- `LegacyAndSeparator`:
  `"'and' is no longer a separator: use ',' (offending 'and' at line L, column C)"`
  + help de stage0 + note de la migración 0.10.0.
- `AtIndexPrecedence`:
  `"The index after 'at' binds tighter than '<op>': parenthesise the index expression"`
  + help con `set xs at (n <op> 1) is v`.
- `MaxDepth`:
  `"Source nesting exceeds the maximum supported depth (512)"` /
  `"Block nesting exceeds the maximum supported depth (512)"`.

### 8.3 Posiciones

- Se emite en el token actual (o en el token concreto del operador) con
  `line`/`col` de byte; `psdiag.diag_span` construye el `Span`.
- Para EOF se usa `SourceFile.eof_position`.
- Para un nodo de error se usa el span del primer token no consumido.
- El primer error de un caso negativo debe coincidir con stage0 en línea y
  columna para el catálogo de pruebas; los errores de recuperación
  posteriores son nuestros y no se comparan.

### 8.4 Ejemplos de recuperación

```pengu
# falta el ':' del if
if x
    return 1
```

- Se emite `ExpectedToken("':'")` en `x`/NEWLINE.
- Se sincroniza hasta `NEWLINE`/`DEDENT`.
- El `block` se construye con un `Error` node; `ok=false`.
- El siguiente statement se parsea normalmente.

```pengu
weave f into int:
    var x is 1 var y is 2
```

- Se parsea `var x is 1`.
- El `var` de `y` está en la misma línea y no es un separador válido.
- `MultipleStatements` en `var` (línea 2, columna 16), exactamente como
  stage0.
- Se sincroniza y se parsea `var y is 2` como recuperación (dos errores en
  total si no se pide `--stop-after-first`).

---

## 🧷 9. Huecos de F1 que hay que cerrar

### 9.1 Cadenas multilínea (`.` / `->`)

**Problema.** `pengu_parser._merge_chain_continuations` pliega, antes del
lexer, cualquier línea cuyo primer token sea `.` o `->`. F1 no lo hace, así
que el parser vería:

```text
... raw NEWLINE INDENT . trim NEWLINE . lower NEWLINE ... DEDENT
```

en lugar de:

```text
... raw . trim . lower ...
```

**Fix propuesto (D3).** En `psc/src/psc/lexer.pengu::scan_newline`:

- añadir `fold_chain_continuations as bool` a `LexOptions` (default `true`);
- dentro de `scan_newline`, tras consumir el `\n` y los espacios/tabs, mirar
  el siguiente byte:
  - si es `.` (46) o `-` seguido de `>` (45, 62);
  - y no se ha consumido ninguna línea en blanco ni comentario en el run;
  - y solo ha habido un `\n`;
  - entonces **no** emitir `TokNewline`: dejar `lx->pos` en el operador y
    salir.
- Si hay una línea en blanco o un comentario entre el receptor y el `.`, no se
  pliega (stage0 tampoco lo hace, porque su plegado es por líneas contiguas).
- El `INDENT`/`DEDENT` desaparece solo, porque no se emitió `NEWLINE`.

**Tests.**

- `psc/tests/fixtures/chain_multiline.pengu` con cadenas en indent 0, dentro
  de un bloque, con `->`, con comentario final de línea y con una línea en
  blanco en medio (esta última **no** debe plegarse).
- Comparar tokens con el oracle F1 sobre el fixture (stage0 también pliega).
- Golden F1 actual: 0 diferencias.
- Test unitario de que `c.lex` sobre el corpus no cambia.

**Riesgo:** bajo. Solo cambia archivos con continuación de cadena; el corpus
actual no tiene ninguno, así que el oracle F1 no se mueve.

### 9.2 Múltiples statements en una línea

F1 lo delegó a F2 (`PARITY.md` #12). Stage0 lo hace en `PenguIndenter`:

- starters: `var`, `let`, `set`, `const`, `static`;
- si aparecen al mismo nivel de paréntesis y en la misma línea que el token
  anterior;
- y el token anterior no es `:`, `;`, `defer`, `errdefer` ni `static`;
- entonces `E0000` en el token del starter.

F2 lo implementa en `parse_stmt_list`/`parse_top_file`:

- después de parsear un statement, si el siguiente token es uno de esos
  starters y su `line` es la misma que la del último token consumido, emite
  `MultipleStatements` en ese token;
- el mensaje es exactamente el de stage0;
- no se aplica dentro de un bloque de una línea (`if c: return 0`), porque ahí
  el `simple_stmt` ya termina en `NEWLINE`.

### 9.3 Interpolación bajo demanda

`StringInfo.has_interp` y `StringPart.kind == SegInterp` ya existen. F2 añade:

```pengu
## Parsea una expresión de interpolación aislada.
##
## ## Memoria
## El bundle es dueño de SourceFile, LexResult y Ast; liberar con `banish`.
weave parse_interpolation_expr with text as string into InterpParseResult
```

- Crea `SourceFile.from_text("<interp>", text)`, lexa, parsea con start
  `expr` y devuelve `InterpParseResult { source, lex, ast, root, ok }`.
- Las posiciones son relativas al texto de la expresión, como en stage0.
- No se llama durante `parse_file`; la usa F3/F4 cuando compila el string.
- Tests con `{x + 1}`, `{calling f with 1}`, `{if c then 1 else 2}` y una
  expresión inválida.

### 9.4 Otros huecos detectados

- **`TokError` del lexer**: el parser los salta sin duplicar diagnóstico; si
  aparecen en medio de una expresión, emite `UnexpectedToken` una sola vez.
- **`antiquus` sin cuerpo**: el lexer ya emite `E0059`; el parser espera
  `NEWLINE INDENT TokAntiquusBody NEWLINE DEDENT` y, si falta, construye un
  `Error` sin segundo diagnóstico.
- **Placeholders `None`**: se replican; no es un hueco, es contrato (D1).
- **`parse_expr` y struct-init corto**: stage0 no lo expande en
  `parse_expr`; PSC sí lo aceptará (mejora deliberada, documentada).

---

## 🧾 10. Tipos exactos

### 10.1 `ParseOptions`

```pengu
rune ParseOptions derive Par, Nexus:
    max_depth as int
    max_errors as int
    stop_after_first as bool

weave default_parse_options into ParseOptions:
    return with max_depth is 512, max_errors is 100, stop_after_first is false
```

### 10.2 `ParseResult`

```pengu
rune ParseResult derive Nexus:
    ok as bool
    root as int
    ast as Ast
    error_count as int
```

- `ok` es `true` solo si el parser no emitió ningún `ParseIssue`. Los errores
  del lexer se consultan en el `DiagnosticBag` (`psc parse` usa
  `bag.has_errors` para el exit code).
- `root` es el id del nodo raíz (`start` para archivo, la expresión para
  `parse_expr`).
- `banish result` libera `ast`.

### 10.3 `ParseIssue`

Ver §8.2. Todos los códigos `E0000`.

### 10.4 `NodeKind`

`NodeKind` es un `omen` con prefijo `Nd` para evitar colisiones globales de
variantes (igual que `Tok`/`Kw` en F1). Ejemplos:

```pengu
omen NodeKind:
    NdStart
    NdFile
    NdTopStmt
    NdImportStmt
    NdDottedPath
    NdWeaveDecl
    NdRuneDecl
    NdOmenDecl
    NdIfStmt
    NdBlock
    NdStmt
    NdAdd
    NdMul
    NdVarRef
    NdIntLit
    NdCustomType
    NdError
    # … hasta completar las reglas de stage0
```

`node_kind_name(kind)` devuelve el nombre de stage0 (`"weave_decl"`,
`"add"`, `"int_lit"`, …) y es lo que usa el dump. El inventario completo está
en el anexo A y se congela en CP1.

### 10.5 `LoopLabel`

```pengu
rune LoopLabel derive Par:
    node as int
    token as int
```

`Ast.labels` es una lista lineal; los loops etiquetados son raros (<1 %), así
que buscar en ella es barato y evita un campo extra en todos los nodos.

### 10.6 `InterpParseResult`

```pengu
rune InterpParseResult derive Nexus:
    source as SourceFile
    lex as LexResult
    ast as Ast
    root as int
    ok as bool
```

Es el único bundle que posee fuente+lex+AST, porque la expresión de
interpolación no tiene un `Session` detrás.

---

## 🗂️ 11. Módulos y archivos

### 11.1 Archivos nuevos

```text
psc/src/psc/ast/kind.pengu            NodeKind + ps_node_kind_name
psc/src/psc/ast/node.pengu            PsNode, PsAst, codificación de hijos
psc/src/psc/ast/dump.pengu            dump canónico
psc/src/psc/parse/state.pengu         PsParser, hooks, cursor, errores, profundidad
psc/src/psc/parse/diagnostics.pengu   ParseIssue + mensajes/help/note
psc/src/psc/parse/types.pengu         tipos, dotted_path, shard/where/derive
psc/src/psc/parse/expr/atoms.pengu    átomos, literales, contenedores
psc/src/psc/parse/expr/calls.pengu    unarios, calling, postfix, argumentos
psc/src/psc/parse/expr/util.pengu     helpers de nodos/spans
psc/src/psc/parse/expr/ops.pengu      precedencia y entrada de expresiones
psc/src/psc/parse/stmt/core.pengu     statements, bloques, control
psc/src/psc/parse/stmt/values.pengu   hooks de if/when/for/do/with/or
psc/src/psc/parse/patterns/core.pengu patrones y cláusulas
psc/src/psc/parse/patterns/judge.pengu judge/judge over
psc/src/psc/parse/decl/core.pengu     declaraciones top-level
psc/src/psc/parse/api.pengu           API, hooks e interpolación

psc/tests/parser_unit.pengu
psc/tests/parser_corpus.pengu
psc/tests/fuzz_parse.pengu
psc/tests/bench_parse.pengu
psc/tests/fixtures/chain_multiline.pengu
psc/tests/fixtures/parser_*.pengu
psc/tests/golden/ast/*.txt
psc/tests/golden/parse_diagnostics/*.txt
psc/tools/run_f2_checks.py
psc/tools/lark_ast_oracle.py
psc/tools/ast_allowlist.txt
psc/tools/lark_parse_error_oracle.py
psc/tools/parse_error_allowlist.txt

tests/psc/test_f2_acceptance.py
psc/docs/AST.md
```

### 11.2 Archivos que se modifican

| Archivo | Cambio |
|---|---|
| `psc/src/main.pengu` | subcomandos `parse`/`ast`, flags, versión 0.2.0 |
| `psc/src/psc/lexer_state.pengu` | `fold_chain_continuations` en `LexOptions` |
| `psc/src/psc/lexer.pengu` | plegado de cadenas en `scan_newline` |
| `psc/README.md` | build/run/test de F2 |
| `psc/docs/PARITY.md` | método, resultado F2, divergencias |
| `psc/docs/OWNERSHIP.md` | AST, ParseResult, bundle de interpolación |
| `psc/src/psc/lexer_state.pengu` | `lex_*` para evitar colisiones globales |
| `psc/src/psc/source.pengu` | sin cambios funcionales |
| `psc/pengu.toml` | versión 0.2.0 |
| `tests/psc/test_f1_acceptance.py` | sin cambios; se añade `test_f2_acceptance.py` |

### 11.3 Tamaño real

| Archivo | Líneas |
|---|---:|
| `ast/kind.pengu` | 435 |
| `ast/node.pengu` | 226 |
| `ast/dump.pengu` | 205 |
| `parse/state.pengu` | 759 |
| `parse/diagnostics.pengu` | 169 |
| `parse/types.pengu` | 500 |
| `parse/expr/atoms.pengu` | 531 |
| `parse/expr/calls.pengu` | 403 |
| `parse/expr/util.pengu` | 55 |
| `parse/expr/ops.pengu` | 682 |
| `parse/stmt/core.pengu` | 859 |
| `parse/stmt/values.pengu` | 216 |
| `parse/patterns/core.pengu` | 207 |
| `parse/patterns/judge.pengu` | 82 |
| `parse/decl/core.pengu` | 911 |
| `parse/api.pengu` | 118 |
| **Total** | **~6 300** |

Todos los módulos quedan por debajo de ~1 000 líneas; la división por
responsabilidad pedida en D9 se cumple.

### 11.4 DAG de imports

```text
F1: span/source/token/lexer_state/diagnostics
        │
        ▼
ast/kind ──▶ ast/node ──▶ ast/dump
        │
        ▼
parse/diagnostics
        │
        ▼
parse/state (PsParser + PsHooks)
        │
        ├──▶ parse/types
        ├──▶ parse/expr/atoms ──▶ parse/expr/util
        │        │
        │        ▼
        │   parse/expr/calls
        │        │
        │        ▼
        │   parse/expr/ops ◀── hooks
        ├──▶ parse/patterns/core ──▶ parse/patterns/judge
        ├──▶ parse/stmt/core ──▶ parse/stmt/values
        └──▶ parse/decl/core
                 │
                 ▼
             parse/api ──▶ main.pengu
```

Los hooks de `PsHooks` rompen la recursión mutua (`value`, `when`, `judge`,
`do_block`, `with_init`, `or_block`, `when_body`, `expr`, `list_expr`,
`value_expr`, `list_value_expr`, `expr_no_cast`, `guard_expr`). No hay imports
cíclicos.

## 🗓️ 12. Orden de implementación y checkpoints

### 12.1 Secuencia

| # | Paso | Días | Depende de | Entregable |
|---:|---|---:|---|---|
| 0 | Congelar contrato: probe de stage0, inventario `NodeKind`, `AST.md` borrador | 2 | — | Tabla de nodos/aridades y dump de muestra |
| 1 | `ast_kind.pengu` + `ast.pengu` + tests unitarios | 2 | 0 | AST construible/recorrible |
| 2 | `parse/diagnostics.pengu` + `parse/state.pengu` + tests | 2 | 1 | Cursor, hooks, errores, profundidad, sync |
| 3 | Fix cadena multilínea en lexer + regresión F1 | 1.5 | 2 | `chain_multiline` y oracle F1 verde |
| 4 | `parse/types.pengu` + tests | 3 | 2 | Tipos completos |
| 5 | `parse/expr/{util,atoms,calls,ops}.pengu`: precedencia, átomos, llamadas, literales | 4 | 4 | Expresiones |
| 6 | `parse/stmt/{core,values}.pengu` + `parse/patterns/{core,judge}.pengu`: statements, bloques, patrones, judge/when, with/do/or | 5 | 5 | Cuerpo completo |
| 7 | `parse/decl/core.pengu` + top-level + `antiquus` + atributos | 4 | 6 | Declaraciones |
| 8 | `parse/api.pengu` + `ast/dump.pengu` + CLI `psc parse` | 3 | 7 | CLI y dump |
| 9 | Golden AST + diagnóstico + `run_f2_checks.py` | 2 | 8 | Golden verdes |
| 10 | `lark_ast_oracle.py` + corpus 189 + fixes de paridad | 4 | 9 | 189/189 árbol igual |
| 11 | Recuperación fina, multi-statement, `and`/`at`, profundidad | 3 | 10 | Errores y robustez |
| 12 | Fuzz, ASan/UBSan, benchmark, docs, DoD | 3 | 11 | F2 cerrada |
|  | **Total** | **~38** |  |  |

### 12.2 Checkpoints

1. **CP1 (paso 0–1): contrato congelado.**
   - `NodeKind` completo, inventario de aridades, dump canónico de muestra.
   - Revisión de que F3 tendrá helpers suficientes.
   - Se acepta el AST fiel y se documentan las rarezas.
2. **CP2 (paso 5): expresiones.**
   - Precedencia, asociatividad, `calling`, literales, contenedores.
   - Tests unitarios de expresiones verdes.
3. **CP3 (paso 7): corpus parsea.**
   - 189/189 archivos con `ok=true`, sin panics.
   - `parser_corpus.pengu` verde.
4. **CP4 (paso 10): paridad de árbol.**
   - Oracle 189/189 exacto; divergencias allowlisteadas = 0 o justificadas.
   - Golden AST de 20–30 casos.
5. **CP5 (paso 12): robustez y cierre.**
   - Fuzz, ASan, benchmark, docs, DoD completo.

### 12.3 Qué no se hará aunque sobre tiempo

- Semántica/checker.
- Codegen.
- LSP.
- Formatter.
- AST canónico nuevo.
- Optimizaciones prematuras que compliquen el parser.

---

## 🧪 13. Tests, oráculos y paridad

### 13.1 Unitarios (`.pengu`)

`psc/tests/parser_unit.pengu`, con un `ParseFixture` que hace
`SourceFile` + `lex` + `parse` y expone helpers:

- `expect_ok`, `expect_node_kind`, `expect_child_kind`,
  `expect_token_text`, `expect_absent`, `expect_issue`, `expect_label`.
- Grupos:
  1. `file`/`start`, vacío, solo newlines.
  2. imports, include/link/ldflag/insignia.
  3. const/var/let/static; tipos opcionales.
  4. rune/echo/omen/alias/seal; campos, variantes, derive, cyclus, string.
  5. concept/bind/enchanting/weave/declare; modificadores y atributos.
  6. antiquus (single/multi/raw; sin cuerpo).
  7. test y when top-level.
  8. statements completos, labels, `set`, compound, `defer`, `unsafe`.
  9. expresiones: todos los operadores, precedencia, asociatividad,
     `or else`/`or return`/`or:`, `try`, `if_expr`, `when_expr`, `judge`,
     `for_comp`, `lambda`, `do`, `with:`, `with` struct/short.
  10. tipos: todos los composites, `shard`, `where`, tuplas, fn types.
  11. patrones: or-pattern, payload, guard, tuple pattern, narrow.
  12. errores: multi-statement, `and`, `at`, `else` inesperado, paréntesis
      sin cerrar, bloque vacío, EOF.
  13. profundidad: 513/1 000 paréntesis, bloques, unarios.
  14. determinismo: parsear dos veces y comparar dump.

### 13.2 Corpus

`psc/tests/parser_corpus.pengu`:

- recorre `src/`, `../std`, `../tests` (excluyendo fixtures);
- para cada `.pengu`: `SourceFile`, `lex`, `parse`;
- exige 0 errores del parser y del lexer;
- acumula `files`, `nodes`, `tokens`, `bad`;
- imprime `corpus: files=189 nodes=... bad=0`;
- `main` devuelve `bad`.

### 13.3 Golden

`psc/tools/run_f2_checks.py`:

- `AST_CASES`: 20–30 archivos representativos (fixtures + corpus), con flags;
- ejecuta `psc parse --quiet --no-header` y compara
  `psc/tests/golden/ast/<name>.txt`;
- `DIAG_CASES`: 15–20 fixtures de error, ejecuta
  `psc parse --quiet --no-color --check` y compara stderr;
- `--update-golden` reescribe; el diff se revisa a mano;
- salida `golden failures=0`.

Casos AST recomendados:

- `basic`, `declarations`, `types`, `statements`, `expressions`,
  `precedence`, `judge_patterns`, `judge_over`, `with_do_or`, `lambda`,
  `antiquus`, `chain_multiline`, `short_struct`, `labels`, `when_top`,
  `test_decl`, `compressus` (struct corto), `arena_ast`, `std/arena`,
  `std/json`, `expr/ops`, `stmt/core`, `decl/core`.

### 13.4 Oráculo de AST contra stage0

`psc/tools/lark_ast_oracle.py` (dev-only):

- usa `PenguParser().parse(text)` de stage0;
- normaliza el árbol a un dump idéntico al de `psc parse --no-header`:
  - nodo → `nombre`;
  - token → `"texto"` escapado;
  - `None` → `_`;
  - `loop_label` → `@label "..."`;
  - `antiquus` → cuerpo decodificado;
  - CRLF → LF en el texto de tokens (solo dump);
  - sin posiciones.
- ejecuta `psc parse --quiet --no-header <archivo>` y compara byte a byte;
- modos:
  ```bash
  python psc/tools/lark_ast_oracle.py --psc psc/build/psc --root std tests psc/src
  # -> files=189 exact=189 diverged=0
  ```
- `--verbose` imprime el primer diff con contexto;
- `--allowlist psc/tools/ast_allowlist.txt` (vacío al cerrar F2);
- exit 1 si hay diferencias no allowlisteadas.

**Divergencias deliberadas** (documentadas en `PARITY.md`):

1. Identificadores que son keywords duras: stage0 los acepta por su lexer
   contextual (`var if as int is 5`); PSC los rechaza (decisión D2 de F1).
   No hay casos en el corpus.
2. `parse_expr("with a, b")`: stage0 falla, PSC acepta (mejora).
3. Columnas de tokens sintéticos de `with a, b` no se comparan (no hay
   posiciones en el dump).
4. Errores de recuperación posteriores al primero no se comparan.

### 13.5 Oráculo de errores

`psc/tools/lark_parse_error_oracle.py`:

- lista de ~30 snippets negativos (multi-statement, `and` legado, `at`,
  `else` inesperado, falta `:`/`then`, paréntesis, bloque vacío, EOF,
  profundidad, keywords como nombres);
- ejecuta stage0 `parse` y captura `ParseError` (código/línea/columna);
- ejecuta `psc parse --check --stop-after-first --diagnostics=json`;
- compara aceptación/rechazo, `E0000`, línea y columna del primer error;
- salida `cases=30 accept_match=... pos_match=...`; objetivo 100 % en el
  catálogo, con allowlist justificada si un heurístico de stage0 no se puede
  replicar sin copiar su preprocesado.

### 13.6 Fuzz

`psc/tests/fuzz_parse.pengu`:

- PRNG determinista;
- modos:
  - truncar un archivo válido en posiciones aleatorias;
  - sustituir/duplicar/borrar tokens;
  - bytes aleatorios con estructura léxica;
  - `with`/`judge`/`if` anidados hasta el límite;
- para cada entrada: `lex` + `parse`, `banish` todo, sin panic;
- contador de iteraciones y de `ok=false` (se espera);
- 100 000 iteraciones en CI normal; 1 000 000 en el gate de cierre;
- con ASan, sin fugas.

### 13.7 ASan/UBSan

```bash
cd psc
PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -g" \
PENGU_LDFLAGS="-fsanitize=address,undefined" \
../.venv/bin/python ../pengu_project.py build
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 ./build/psc parse --quiet --check \
    ../tests/conformance/compliance/arena_ast.pengu
```

- Pasada por 189 archivos con `parse --check`.
- Pasada por los golden y fixtures de error.
- Cero leaks, cero UB.

### 13.8 Benchmark

`psc/tests/bench_parse.pengu`:

- genera en memoria un fuente válido de ~3 MB (muchas `weave`, tipos,
  expresiones y bloques);
- lexa una vez, parsea N veces;
- reporta MB/s, nodos/s, tokens/s, memoria (vía ASan o `size`);
- perfiles debug y release.

Objetivo:

- Objetivo Release ≥ 10 MB/s de parseo; **mínimo aceptable ≥ 5 MB/s y ≥ 15×
  stage0** (stage0: 0,34 MB/s; F1 lexer: 11,8 MB/s). El número final se fija
  con la medición de CP2/CP5, no antes.
- No degradar el lexer de F1 >5 % por el flag de cadenas.
- Tiempo total de `psc parse` sobre el corpus in-process ≤ 1/5 del de stage0.

### 13.9 Integración pytest

`tests/psc/test_f2_acceptance.py`:

- build del binario (reutiliza el fixture de F1);
- `run_f2_checks.py` verde;
- `parser_unit.pengu` verde;
- `parser_corpus.pengu` verde (`bad=0`);
- CLI: `parse --stdin`, `--diagnostics=json`, `--no-header`;
- `PSC_PARITY=1`: oracle de AST 189/189 y de errores;
- no ejecuta el fuzz grande por defecto (gate de cierre).

---

## ⚡ 14. Rendimiento y determinismo

### 14.1 Reglas de rendimiento

- Sin `string` por token: comparaciones por bytes y referencias a tokens.
- Sin `map` en el parser; no hay búsquedas por nombre.
- Sin `judge` en el bucle caliente de precedencia; `if`/`switch` por
  `TokenKind`/`KeywordKind`.
- AST en listas contiguas; `push` amortizado.
- Los wrappers de stage0 añaden nodos, pero son POD y baratos; se mide y, si
  el benchmark muestra un problema, se optimiza solo lo medido.
- `ast_dump` usa `StringBuilder`, nunca `"{a}{b}"` en bucle.
- No se materializa el texto de un token salvo en error/dump.
- `@inline` solo si el benchmark lo justifica (no por defecto).

### 14.2 Determinismo

- Nodos en orden de fuente; IDs estables.
- Etiquetas en orden de aparición.
- Sin timestamps, rutas absolutas ni orden de hash.
- Dos ejecuciones de `psc parse` producen bytes idénticos.
- El dump incluye `sha256` y `bytes` del fuente, no la ruta absoluta
  (la ruta se imprime tal como la pasó el usuario; en tests es relativa).

---

## ✅ 15. Criterios de aceptación (DoD)

### 15.1 Funcional

- [ ] `cd psc && pengu build` compila sin errores ni warnings nuevos.
- [ ] `psc parse <archivo>` produce un dump AST estable.
- [ ] `psc ast <archivo>` funciona como alias.
- [ ] `psc parse --check` no imprime AST y devuelve 1 si hay errores.
- [ ] `psc parse --stdin` funciona.
- [ ] `psc parse --diagnostics=json` produce JSON válido.
- [ ] `psc parse --no-header` omite la cabecera.
- [ ] `psc version` informa `0.2.0 (F2)`.
- [ ] Los 189 archivos de `std/` + `tests/` + `psc/src/` parsean con
      `ok=true`.
- [ ] Los 28 archivos con `antiquus` parsean y su cuerpo se dumpea
      correctamente.
- [ ] Los archivos con CRLF/BOM se parsean con spans correctos.
- [ ] Las cadenas multilínea (`.`/`->`) se parsean.
- [ ] El struct-init corto (`with a, b`) se parsea en archivo y en
      `parse_expr`.
- [ ] `psc lex` sigue funcionando y su oracle no tiene regresiones.

### 15.2 Paridad

- [ ] Oracle AST: `files=189 exact=189 diverged=0`.
- [ ] Golden AST: 20–30 casos byte-idénticos.
- [ ] Golden de diagnósticos: 15–20 casos.
- [ ] Oracle de errores: aceptación/rechazo 100 %; línea/columna del primer
      error 100 % en el catálogo (o allowlist justificada).
- [ ] Divergencias allowlisteadas = 0 o documentadas en `PARITY.md`.
- [ ] Los placeholders `None` y las rarezas de aridad están documentados y
      cubiertos por tests.

### 15.3 Robustez

- [ ] Fuzz de 100 000 entradas: cero crashes, cero cuelgues, progreso
      garantizado.
- [ ] Fuzz de 1 000 000 en el gate de cierre.
- [ ] ASan/UBSan limpio sobre 189 archivos + fixtures + fuzz.
- [ ] 513 paréntesis anidados → `E0000` con línea/columna, sin
      `RecursionError` ni segfault.
- [ ] 1 000 paréntesis y 10 000 bloques → diagnóstico controlado.
- [ ] `else` inesperado, `:` faltante, bloque vacío, `and` legado y `at`
      producen diagnósticos con línea/columna.
- [ ] `psc parse` nunca usa `spark.panic` para entrada de usuario.
- [ ] Ningún bucle del parser puede quedarse sin avanzar (test de progreso).

### 15.4 Rendimiento y determinismo

- [ ] Release ≥ 5 MB/s de parseo y ≥ 15× stage0 (objetivo: 10 MB/s).
- [ ] Corpus in-process ≤ 1/5 del tiempo de stage0.
- [ ] Dos ejecuciones producen dumps idénticos.
- [ ] Sin rutas absolutas ni timestamps en la salida.
- [ ] Memoria del AST lineal en nodos; sin `alloc` por nodo.

### 15.5 Documentación

- [ ] `psc/README.md` con build/run/test de F2.
- [ ] `psc/docs/AST.md` con `NodeKind`, aridades, placeholders, `aux`,
      rarezas y ejemplos.
- [ ] `psc/docs/PARITY.md` con el método F2, resultado 189/189 y
      divergencias.
- [ ] `psc/docs/OWNERSHIP.md` con AST/ParseResult/interpolación.
- [ ] `AUDITORIA_AUTO_HOSPEDAJE.md` intacto.
- [ ] `CHANGELOG.md` intacto hasta el release de PSC.

---

## ⚠️ 16. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| El AST fiel arrastra rarezas de Lark y confunde a F3 | Media | Medio | `AST.md` + helpers + tests de formas raras; CP1 |
| Divergencia de paridad por `None`/aridades | Alta | Alto | Oráculo 189 archivos; tabla congelada; tests por nodo |
| Un módulo del parser demasiado grande | Media | Medio | Carpetas y módulos por responsabilidad; `expr/calls` y `expr/ops` separados; revisión CP2 |
| Recuperación en cascada o bucle infinito | Media | Alto | Panic mode, tope, progreso forzado, fuzz |
| Cadena multilínea rompe F1 | Baja | Medio | Flag default, oracle F1, golden, fixture |
| Multi-statement con posiciones distintas | Media | Medio | Réplica de la regla de `PenguIndenter`; test exacto |
| `and` legado/`at` con heurísticas distintas | Media | Bajo | Mensajes propios, catálogo de errores, allowlist justificada |
| Profundidad no coincide en bloques | Baja | Bajo | Pre-scan de delimitadores exacto; aceptación/rechazo; documentar |
| Fugas/lifetimes AST↔tokens | Alta | Alto | Contrato de ownership; `ParseResult` dueño del AST; ASan |
| Rendimiento pobre por wrappers | Media | Medio | Benchmark; POD; sin strings; optimizar solo lo medido |
| CRLF en strings/antiquus rompe el dump | Media | Medio | Normalizar solo el dump; tests de CRLF |
| El corpus no cubre construcciones raras (`unsafe`, `try`, `when_expr`) | Alta | Medio | Tests unitarios específicos además del corpus |
| `parse_interpolation_expr` no se usa y queda muerto | Baja | Bajo | Tests y uso previsto en F3; documentado |
| Se toca stage0 por un bug | Baja | Medio | Solo si es bloqueante y acordado; preferir F1/PSC |

---

## ❓ 17. Decisiones que necesito de ti

Marca cada una. Las recomendadas son las que desbloquean la implementación.

### D1 — Forma del AST

- [x] **Recomendado:** fiel a stage0 (nombres, aridades, `None`, wrappers).
- [ ] Alternativa: AST canónico nuevo (más limpio, más riesgo y trabajo).

### D2 — Almacenamiento

- [x] **Recomendado:** arena plana en `list of Node` + `list of int` +
  codificación de hijos; sin `std.arena` para nodos.
- [ ] Alternativa: `std.arena` + punteros/refs recursivos.

### D3 — Cadena multilínea

- [x] **Recomendado:** corregir el lexer de F1 con
  `fold_chain_continuations` (default `true`) y tests.
- [ ] Alternativa: filtro de tokens en F2 (más frágil).

### D4 — Interpolación

- [x] **Recomendado:** no parsear en `parse_file`; API bajo demanda
  `parse_interpolation_expr`.
- [ ] Alternativa: parsear todas las interpolaciones en F2 (detecta antes,
  pero diverge de stage0).
- [ ] Alternativa: dejarlo todo a F3 (deuda).

### D5 — Recuperación

- [x] **Recomendado:** recuperar por defecto, tope 100, panic mode,
  `--stop-after-first` opcional.
- [ ] Alternativa: abortar al primer error como stage0.

### D6 — Profundidad

- [x] **Recomendado:** `MAX_PARSE_DEPTH=512`, pre-scan de delimitadores +
  guard en el parser.
- [ ] Alternativa: solo guard del parser.

### D7 — AST dump

- [x] **Recomendado:** sin posiciones por defecto; spans se prueban aparte.
- [ ] Alternativa: incluir `@line:col` (rompe paridad en struct-init corto).

### D8 — CLI

- [x] **Recomendado:** `psc parse` + alias `psc ast`, flags de §2.1.
- [ ] Alternativa: solo `psc ast`.

### D9 — Carpetas y módulos

- [x] **Aprobado:** carpetas `ast/`, `parse/expr/`, `parse/stmt/`,
  `parse/patterns/`, `parse/decl/` y `parse/` con módulos de responsabilidad
  única; la recursión se resuelve con `PsHooks`.
- [ ] Alternativa descartada: un `parser_body.pengu` monolítico.

### D10 — Cambios a F1

- [x] **Recomendado y aplicado:** plegado de cadenas multilínea, comprobación
  de multi-statement en F2 y renombrado de los helpers del lexer a `lex_*` para
  evitar colisiones globales con `std.lingua`, `std.sourcemap`, `std.json`,
  `std.builder` y `std.functor`.
- [ ] Alternativa: no tocar F1.

**Si me dices “todas las recomendadas”, arranco por el paso 0 y te reporto
CP1 antes de escribir el parser completo.**

---

## 📎 18. Anexos

### A. Inventario inicial de `NodeKind`

Se congela en CP1 contra el corpus. Los nombres son los `node.data` de
stage0, con prefijo `Nd` en el `omen`.

**Archivo / top-level / declaraciones**

```text
start, file, top_stmt, import_stmt, dotted_path, include_stmt, link_stmt,
ldflag_stmt, insignia_stmt, attributes, attribute, attribute_args,
const_decl, var_decl, let_decl, var_name_list, static_var_decl,
rune_decl, echo_decl, field_decl, cyclus_kw, shard_params, shard_param_ref,
where_clause, where_bound, derive_clause,
omen_decl, omen_variant, omen_field, omen_string_kind,
alias_decl, seal_decl, concept_decl, concept_method,
bind_decl, weave_decl, weave_modifier, param_list, param,
enchanting_decl, antiquus_decl, declare_stmt, declare_params,
test_decl, when_top_decl, when_top_else_plain, when_top_else_when
```

**Statements**

```text
stmt, block, set_stmt, compound_set_stmt, set_target, with_target,
normal_target, essence_target, if_stmt, if_cond, if_cond_binding,
unless_stmt, while_stmt, for_range_stmt, for_in_stmt,
when_stmt, when_else_plain, when_else_when, else_block,
with_stmt, unsafe_stmt, defer_stmt, errdefer_stmt, banish_stmt,
return_stmt, break_stmt, continue_stmt, expr_stmt
```

**Expresiones**

```text
or_else, or_return, or_block, try_expr, if_expr, when_expr,
judge_expr, judge_over_expr, for_comp,
bool_or, bool_and,
eq, ne, lt, le, gt, ge, in_expr, not_in_expr,
is_present, is_not_present, is_true, is_false,
range_dotdot, to_expr,
bitwise_or, bitwise_and, bitwise_xor, shl, shr,
add, sub, mul, div, mod,
bit_not, log_not, neg,
sigil_of, essence_of, transmute, size_of, type_of,
some_expr, banish_expr, ord_expr, chr_expr, bytes_expr,
calling_expr, normal_target, with_target,
generic_args, arg_list, pos_arg, named_arg,
postfix: field_access, arrow_access, at_expr, slice_at_expr,
length_expr, at_access, dot_access, slice_range,
paren_expr, var_ref, self_ref,
int_lit, float_lit, string_lit, char_lit, true_lit, false_lit,
null_lit, maybe_none, error_lit, donum_expr, defined_expr,
struct_init, field_init, with_init_expr, do_expr,
lambda_expr, lambda_no_params, lambda_param, lambda_param_list,
list_init_expr, map_init_expr, array_init_expr,
array_lit, map_lit, map_entry, field_entry,
indent_literal, indent_array, indent_row, indent_entries
```

**Patrones / `judge`**

```text
when_clause, when_pattern, when_variant, when_payload, when_field,
field_pattern, field_tuple, when_guard, else_clause
```

**Tipos**

```text
type_or_param, ref_type, frozen_type, fn_type, fn_param_list, fn_param,
array_type, slice_type, many_type, list_type, map_type, maybe_type,
result_type, opaque_type, base_type, custom_type, tuple_type
```

**Recuperación**

```text
error
```

> Total: ~172 nombres de stage0 + `error`. El orden exacto de hijos de cada
> uno se documenta en `psc/docs/AST.md` y se valida con el oráculo.

### B. Formato del AST dump

```text
# psc-ast-dump v1
# file: <ruta tal como se pasó>
# sha256: <hex>
# bytes: <n>
# nodes: <n>
# columns: indentation  payload

start
  file
    top_stmt
      import_stmt
        dotted_path
          "std"
          "spark"
        _
```

Reglas:

- Cada nivel son dos espacios.
- Nodo: `nombre`.
- Token: `"texto"` con escapes C (`\\`, `\"`, `\n`, `\t`, `\r`, `\0`,
  bytes no imprimibles `\xNN`).
- Ausente: `_`.
- Loop etiquetado: `for_in_stmt @label "outer"`.
- `antiquus`: se imprime el cuerpo decodificado, con `\n` escapado.
- Sin posiciones.
- Sin colores.
- Orden de hijos: el del AST.

### C. Comandos de trabajo

```bash
# Build
cd psc
../.venv/bin/python ../pengu_project.py build

# Tests unitarios
../.venv/bin/python ../pengu_project.py run tests/parser_unit.pengu --no-cache

# Corpus
../.venv/bin/python ../pengu_project.py run tests/parser_corpus.pengu --no-cache

# Golden
python tools/run_f2_checks.py
python tools/run_f2_checks.py --update-golden

# Oráculo AST
python ../psc/tools/lark_ast_oracle.py --psc build/psc --root ../std ../tests src

# Oráculo de errores
python ../psc/tools/lark_parse_error_oracle.py --psc build/psc

# Fuzz
../.venv/bin/python ../pengu_project.py run tests/fuzz_parse.pengu --no-cache -- 100000

# Benchmark
../.venv/bin/python ../pengu_project.py run tests/bench_parse.pengu --no-cache --profile release

# ASan
PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -g" \
PENGU_LDFLAGS="-fsanitize=address,undefined" \
../.venv/bin/python ../pengu_project.py build
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 ./build/psc parse --quiet --check \
    ../tests/conformance/compliance/arena_ast.pengu

# CLI
./build/psc parse src/main.pengu
./build/psc parse --check --diagnostics=json tests/fixtures/parser_bad.pengu
printf 'weave main into int:\n    return 0\n' | ./build/psc parse --stdin
```

### D. Divergencias deliberadas previstas

| # | Divergencia | Motivo | Test |
|---|---|---|---|
| 1 | Keywords duras como nombres se rechazan | F1 D2; stage0 las acepta por lexer contextual | `parser_unit` |
| 2 | `parse_expr("with a, b")` se acepta | Mejora sobre el preprocesado de stage0 | `parser_unit` |
| 3 | El dump no incluye posiciones | Evita ruido de tokens sintéticos; spans se prueban aparte | `AST.md` |
| 4 | Recuperación produce más de un error | LSP/UX; el oráculo compara el primero | `lark_parse_error_oracle.py` |
| 5 | `psc` no acepta `if` como identificador | Coherencia con F1 | `parser_unit` |

### E. Glosario

| Término | Significado |
|---|---|
| **AST** | Abstract Syntax Tree; aquí, árbol plano por índices |
| **Arena** | Listas contiguas que se liberan de golpe |
| **Nodo** | Entrada POD de `Ast.nodes` |
| **Hijo codificado** | `int` que referencia un nodo o un token |
| **Placeholder** | `0` que representa un `None` de Lark |
| **Panic mode** | Modo de recuperación que evita cascadas |
| **AST dump** | Representación textual canónica para golden/oráculo |
| **Oráculo** | Implementación de referencia (stage0) que produce el esperado |

### F. Referencias

- [`AUDITORIA_AUTO_HOSPEDAJE.md`](AUDITORIA_AUTO_HOSPEDAJE.md) §5 (B7), §7, §9
  (F2), §10.
- [`PLAN_F1_LEXER.md`](PLAN_F1_LEXER.md).
- [`psc/README.md`](psc/README.md), [`psc/docs/PARITY.md`](psc/docs/PARITY.md),
  [`psc/docs/OWNERSHIP.md`](psc/docs/OWNERSHIP.md).
- [`pengu_parser/pengu_grammar.py`](pengu_parser/pengu_grammar.py) — gramática
  exacta.
- [`pengu_parser/pengu_parser.py`](pengu_parser/pengu_parser.py) —
  preprocesado, `MAX_PARSE_DEPTH`, errores, `extract_string_parts`.
- [`LANGUAGE.md`](LANGUAGE.md) §6.1, §7, §8, §9, §12, §15, §16, §18, §26.
- [`PenguScriptGuideSpanish.md`](PenguScriptGuideSpanish.md) §16 (cadenas de
  métodos).
- [`std/diagnostic.pengu`](std/diagnostic.pengu),
  [`std/sourcemap.pengu`](std/sourcemap.pengu).

---

## 🏁 19. Estado de implementación y cierre

**F2 está implementada y verificada en este árbol.**

### Entregado

- [x] `ast/kind.pengu`, `ast/node.pengu`, `ast/dump.pengu`.
- [x] `parse/state.pengu` con `PsParser`, `PsHooks`, cursor, errores,
  profundidad de expresiones y bloques, y progreso garantizado.
- [x] `parse/diagnostics.pengu` con `ParseIssue` y mensajes/help/note.
- [x] `parse/types.pengu`, `parse/expr/{atoms,calls,util,ops}.pengu`,
  `parse/stmt/{core,values}.pengu`, `parse/patterns/{core,judge}.pengu`,
  `parse/decl/core.pengu`, `parse/api.pengu`.
- [x] Gramática completa: declaraciones, statements, expresiones, tipos,
  patrones, `judge`, `with`, `do`, `or`, `lambda`, `antiquus`, struct-init
  corto, cadenas multilínea, labels y `when` top-level.
- [x] Recuperación, multi-statement, `and` legado, `at` con paréntesis,
  profundidad 512 y diagnósticos JSON.
- [x] CLI `psc parse`/`psc ast` con `--stdin`, `--check`, `--no-header`,
  `--max-errors`, `--stop-after-first`, `--diagnostics`, color.
- [x] `parse_interpolation_expr` bajo demanda.
- [x] Tests: `parser_unit`, `parser_corpus`, fuzz, bench, golden F2 y
  `test_f2_acceptance.py`.
- [x] Oráculos: AST y errores contra stage0, con allowlists justificadas.
- [x] Docs: `psc/docs/AST.md`, `README.md`, `PARITY.md`, `OWNERSHIP.md`.

### Resultados medidos

```text
pytest tests/psc con PSC_PARITY=1        -> 12 passed (5 F1 + 7 F2)
oracle tokens F1                         -> files=175 failures=0
parser_corpus                            -> files=205 bad=0
oracle AST F2                            -> exact=204 allowed=1 diverged=0
oracle errores F2                        -> cases=15 pos_ok=14 allowed=1 failures=0
ASan/UBSan sobre 205 archivos            -> limpio
fuzz parser                              -> 1 000 000 sin crashes
bench parser Release                     -> 2 528 890 bytes, 680 002 nodos, 181 ms, 13,3 MB/s
```

### Correcciones a F1 encontradas por F2

1. Plegado de cadenas multilínea (`.`/`->`).
2. Colisiones globales de nombres: `source_len`, `is_letter`, `is_digit`,
   `is_hex_digit`, `is_blank` renombrados a `lex_*`; los símbolos de
   PenguScript son globales, no por módulo.
3. El parser acepta keywords como nombres en posiciones de nombre, igual que
   el lexer contextual de stage0 (necesario para `from`, `antiquus`, etc.).
4. Multi-statement se implementó en el parser, como F1 había delegado.
5. Los golden de F1 se regeneraron solo por el cambio de líneas del lexer.

### Pendiente fuera de F2

- F3 (símbolos, tipos, checker, inferencia).
- F4 (codegen C).
- F5–F11.

El plan se cumplió sin dejar TODOs en el código de F2. Las únicas excepciones
documentadas son los dos allowlists de `std/compressus.pengu` (bug de stage0)
y `unexpected_eof` (posición del `E0000` del lexer de F1).
