# Fase 8 — Formatter, linter, docs, tests, fix y CI

Estado: **en curso**. Esta fase cierra el ciclo de calidad: el proyecto se
formatea, lintea, arregla, documenta, testea y mide solo con `pengu`.

Referencias: `scratch/TOOLING_PLAN.md` Fase 8 (entregables y tabla de comandos de
calidad), `docs/LANGUAGE.md` §17 (tests y doc tests) y §18 (formatter, linter,
códigos de tooling), `docs/LSP.md` (el LSP ya formatea con una versión
conservadora que esta fase sustituye).

## 1. Objetivo y criterio de cierre

**Objetivo.** Que un proyecto real se pueda mantener solo con la CLI:

```console
pengu fmt --check     # formato determinista, idempotente y sin cambios de semántica
pengu lint            # los lints de §18.5, configurables por proyecto
pengu fix             # arreglos seguros: formato, imports muertos, unveil, while true
pengu doc --open      # documentación navegable desde `---` y `--!`
pengu test --doc      # los bloques ```pengu de la documentación se ejecutan (PGS-E1705)
pengu bench           # coste medido por fase del pipeline
pengu explain PGS-E1104
pengu watch test      # re-ejecuta al cambiar fuentes
```

**Criterio de cierre.**

1. `pengu fmt` es **idempotente** y **preserva la semántica**: para cada archivo
   de `std/` y para un corpus de casos (indentación, comentarios, strings con
   `#{}`, mapas, genéricos, atributos), `format(format(x)) == format(x)` y la
   secuencia de tokens (tipo + lexema) es idéntica antes y después.
2. `pengu lint` implementa los lints de §18.5 con sus códigos (`PGS-W1102`,
   `PGS-W2001`, `PGS-W1501`, `PGS-W6001`, `PGS-W6002`, `PGS-W9001`, `PGS-W1001`,
   comparaciones redundantes e `if`→`match`), con `--allow`, `--deny` y
   `[lints]` en `Tome.toml`.
3. `pengu fix` solo aplica arreglos que no cambian el comportamiento y lo
   demuestra: cada arreglo va seguido de un re-análisis y, si aparece un
   diagnóstico nuevo, el archivo se restaura (transaccional como en `pengu add`).
4. `pengu test --doc` ejecuta los bloques ```pengu de `---`/`--!`; un bloque que
   no compila da `PGS-E1705`.
5. `pengu bench` mide fases del pipeline con iteraciones configurables y sin
   números inventados.
6. `pengu explain` explica cualquier código documentado en `docs/LANGUAGE.md`
   sin duplicar la tabla (la lee del documento embebido).
7. El LSP usa **el mismo** formatter (`pengu-fmt`), sin dos implementaciones.
8. CI en `.github/workflows/ci.yml`: fmt --check, lint, clippy -D warnings,
   tests y doc.
9. `cargo test --workspace`, `fmt` y `clippy -D warnings` limpios.
10. Documentación: `docs/QUALITY.md`, `docs/LSP.md` actualizado, `scratch/STATUS.md`,
    `scratch/TOOLING_PLAN.md` Fase 8 ✅.

## 2. Decisiones

- **D1 — El formatter es de tokens, no de AST.** La indentación es significativa:
  reindentar desde el AST cambiaría el programa si el AST se construyó con una
  indentación distinta. El formatter trabaja sobre la secuencia de tokens del
  lexer real (que ya conoce strings, `#{}`, comentarios y bloques), y solo
  normaliza espacios **entre** tokens y la indentación **existente** (tabuladores
  a múltiplos de 4 y espacios finales). Nunca añade ni quita niveles.
- **D2 — Qué se normaliza en v1.** Espacios finales, CRLF, tabuladores iniciales
  (4 espacios por tabulador), líneas en blanco (máximo una seguida), newline
  final, un espacio tras `:` en tipos, ninguno dentro de `[]`/`()` ni antes de
  `,`, y exactamente un espacio tras `,` en la misma línea. Lo que no se toca:
  alineación de expresiones, orden de líneas y saltos de línea (no hay reflow).
- **D3 — El límite de 100 columnas de §18.4 se reporta, no se reescribe.**
  Reflowar expresiones exige un pretty-printer por precedencia; en v1 `pengu fmt
  --check` señala las líneas largas como diferencia de formato, y
  `pengu fmt` no las parte. Queda documentado como límite consciente, no como
  deuda silenciosa.
- **D4 — Verificación semántica del formato.** Antes y después de formatear se
  lexa y se comparan las secuencias `(kind, lexema)`; si difieren, `PGS-E1805`
  y no se escribe nada.
- **D5 — Lints sobre HIR + AST, con códigos de §18.5.** Los que el compilador ya
  emite (`PGS-W1101`) no se duplican: el linter los reutiliza.
- **D6 — `unwrap`/`expect` no existen en PenguScript**, así que `PGS-W1501` se
  aplica al equivalente real: `panic(...)`/`fail(...)` fuera de `@@test` y fuera
  de `std`.
- **D7 — `pengu bench` mide el pipeline, no funciones de usuario.** §17.4 dice
  explícitamente que no hay `@@bench`, así que inventar un atributo sería deuda:
  `bench` reporta lex/parse/lower/check/codegen y el total de `cargo`, con
  `--iterations N` (media y mínimo).
- **D8 — Doc tests reutilizan el ejecutor de tests.** Cada bloque ```pengu se
  convierte en una función `@@test` al final del mismo archivo (misma resolución
  de nombres) y se ejecuta con el pipeline de `pengu test`.
- **D9 — `pengu explain` lee `docs/LANGUAGE.md` embebido** (`include_str!`): una
  sola fuente de verdad para los códigos.
- **D10 — Un solo formatter.** `pengu-lsp` deja de tener `format.rs` propio y
  llama a `pengu_fmt`.

## 3. Arquitectura

```
crates/pengu-fmt     formato determinista + verificación semántica
crates/pengu-lint    lints de §18.5 + configuración + sugerencias de fix
crates/pengu-doc     modelo de documentación y extracción de doc tests
crates/pengu-cli     comandos fmt/lint/fix/doc/bench/explain/watch
crates/pengu-lsp     formatting delega en pengu-fmt
```

## 4. Fases

### F0 — `pengu-fmt` ✅

- [x] `format_source(&str) -> Result<String, FormatError>` con `PGS-E1805`.
- [ ] Normalizaciones de D2 y verificación de D4.
- [ ] Tests: idempotencia, tokens idénticos, corpus (strings con `#{}`,
      comentarios de bloque, `Map[...]`, genéricos, `@@test`, tabs, CRLF).
- [ ] Cada archivo de `std/*.pengu` formateado sin cambios (ya está limpio).

### F1 — `pengu-lint` ✅

- [x] `Lint` + `Level` + `LintConfig` (`allow`/`deny`, `[lints]`, CLI).
- [ ] `PGS-W1102` sombreado, `PGS-W2001` import sin usar, `PGS-W1501`
      `panic`/`fail` en producción, `PGS-W6001` inalcanzable, `PGS-W6002`
      condición constante, `PGS-W9001` brazos inalcanzables, `PGS-W1001`
      convención de nombres, comparaciones redundantes, `if`→`match`.
- [ ] Tests por lint (positivo y negativo) y de configuración.

### F2 — CLI `fmt`/`lint`/`fix` ✅

- [x] `pengu fmt [--check]` sobre todos los `.pengu` del proyecto.
- [ ] `pengu lint [--allow CODE]... [--deny CODE]... [-D warnings]`.
- [ ] `pengu fix [--check]`: formato + imports muertos + `unveil` + `while true`.
      Verificación posterior y restauración si empeora.
- [ ] Tests de integración con el binario real.

### F3 — `pengu doc` y `pengu test --doc` ✅

- [x] `pengu-doc`: módulos, items, firmas y markdown de `---`/`--!`.
- [ ] `pengu doc [--open]` escribe `target/pengu/doc/index.md` y una página por
      módulo.
- [ ] `pengu test --doc`: bloques ```pengu → tests; `PGS-E1705` si no compilan.

### F4 — `pengu bench`, `pengu explain` y `--watch` 🟡

- [x] `pengu bench [--iterations N]` con tabla por fase y total.
- [ ] `pengu explain <code>` leyendo `docs/LANGUAGE.md`.
- [ ] `pengu watch <check|test|build|run>` y `--watch` en esos comandos.
      **Desviación:** `--watch` pertenece a la Fase 4 según `TOOLING_PLAN.md`
      (§"Fase 4 — Build, run y watch"); no se duplica aquí. Se documenta en
      `docs/QUALITY.md` como pendiente de esa fase.

### F5 — LSP, CI y cierre ✅

- [x] `pengu-lsp` usa `pengu-fmt`; se elimina `format.rs`.
- [ ] `.github/workflows/ci.yml`.
- [ ] `docs/QUALITY.md`, `docs/LSP.md`, `scratch/STATUS.md`,
      `scratch/TOOLING_PLAN.md` Fase 8 ✅.
- [ ] Suite completa y commit de cierre.

## 5. Estado (cierre)

| Fase | Estado | Nota |
| --- | --- | --- |
| F0 | ✅ | `pengu-fmt` (tokens, verificación semántica, 12 tests) |
| F1 | ✅ | `pengu-lint` (10 lints, `--allow/--warn/--deny`, 12 tests) |
| F2 | ✅ | `pengu fmt/lint/fix/explain` + 9 tests de integración |
| F3 | ✅ | `pengu doc` (Markdown desde `---`/`--!`) y `pengu test --doc` |
| F4 | 🟡 | `bench` y `explain` ✅; `--watch` es de la Fase 4 |
| F5 | ✅ | LSP usa `pengu-fmt`, CI, `docs/QUALITY.md` |
| Cierre | ✅ | 760 tests, fmt y `clippy -D warnings` limpios |

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| Tocar un string con `#{}` o un comentario de bloque | El lexer real delimita strings y comentarios; el formatter nunca reescribe su interior. |
| Cambiar semántica al normalizar indentación | Solo se convierten tabuladores y espacios finales; se comparan tokens (D4). |
| Lint ruidoso en `std` o en código generado | El linter no analiza `std` por defecto y `[lints]` permite silenciar códigos. |
| `fix` rompe código | Cada arreglo se reanaliza; si empeora, se restaura el original. |
| Duplicar el formatter entre LSP y CLI | D10: el LSP importa `pengu-fmt`. |
