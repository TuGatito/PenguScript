# 🐧 AUDITORÍA INTEGRAL DE PENGUSCRIPT — CAMINO A 1.0

> **Fecha de auditoría:** contra el árbol de trabajo en `0.16.0`
> **Commit base:** `8967d6f` + `77f4ed8` (el árbol quedó limpio durante la auditoría)
> **Metodología:** cada afirmación de este documento fue verificada leyendo el código y ejecutando
> comandos reproducibles. Todo comando citado se ejecutó realmente en este checkout con
> `.venv/bin/pengu` (Python 3.14.7, gcc 16.2.1, clang 22.1.8, lark 1.3.1).
> **Regla aplicada:** cuando la documentación afirmaba algo que el código no cumple, se marca
> **❌ REFUTADO** con la evidencia. Cuando el código está mejor de lo que la documentación dice, se
> marca **✨ UNDERSELL**. Cuando no se pudo verificar, se marca **🟡 NO VERIFICADO** y se explica por qué.

---

## §0. Resumen ejecutivo

> **Veredicto global:** 🟠 **con problemas graves** — el proyecto está mucho más completo de lo que
> su propia documentación sugiere, pero contiene **8 defectos bloqueantes** verificados, tres de ellos
> con una puerta de CI que pasa en verde de todos modos.

### §0.1 Tabla de veredicto por subsistema

| # | Subsistema | Veredicto | Evidencia clave | Severidad máxima |
|---|-----------|-----------|-----------------|------------------|
| §1 | Parser / Grammar | 🟠 con problemas graves | **188** conflictos shift/reduce en 79 terminales; precedencia correcta solo por heurística de Lark | 🟠 |
| §2 | Semantic Checker | 🟠 con problemas graves | `E0043` lanza `NameError`; 5 clases de error documentadas no existen | 🔴 |
| §3 | Type Inferrer | 🟠 con problemas graves | `T: Num` acepta `==` pero rechaza `<`; tipos cualificados pierden campos | 🔴 |
| §4 | Code Generator | 🔴 bloqueante | `--strict-c99` emite C que **no compila** en programas reales | 🔴 |
| §5 | Runtime C | 🟠 con problemas graves | `.c` no compila sin `-Wno-implicit-function-declaration` que oculta 24 errores | 🟠 |
| §6 | CLI | 🔴 bloqueante | `pengu check <archivo>` ignora el archivo y dice "Clean"; `fmt --indent` corrompe | 🔴 |
| §7 | LSP | 🟢/🟡 mayormente listo | 13/16 features reales; rename global textual; codeLens inerte | 🟠 |
| §8 | Standard Library | 🟡 parcial | (ver §8) | — |
| §9 | Syntax & Sugar | 🟡 parcial | azúcar amplia y funcional; `alias` en `concept` documentado pero no implementado | 🟡 |
| §10 | Style Guide | 🟠 con problemas graves | prototype-first contradice al lenguaje real (`weave main`) | 🟠 |
| §11 | Tests | 🟢 listo en volumen / 🟠 en cobertura de integración | 2074 passed, 12 skipped; pero **cero** tests de `pengu check <archivo>` | 🟠 |
| §12 | Organización del proyecto | 🟡 parcial | 40 archivos en la raíz, `pengu_project.py` de 228 KB / 5207 líneas | 🟡 |
| §13 | Documentación | 🟠 con problemas graves | `LANGUAGE.md` §22.2 cita 5 clases inexistentes; 72/105 ejemplos no compilan | 🟠 |
| §14 | Runtime de build | 🟡 parcial | manifest sin SHA-256, TCC sin verificación | 🟠 |
| §15 | CI/CD | 🟠 con problemas graves | 3 gates en verde sobre features rotas; 0 SAST | 🟠 |
| §16 | Seguridad y estabilidad | 🟡 parcial | lockfile verificable solo si el hash es no vacío | 🟡 |
| §17 | Rendimiento | 🟡 parcial | cifras de TCC no aplican a programas que importan `std` | 🟡 |
| §18 | Estado real vs reivindicado | 🟠 con problemas graves | 12 refutaciones, 7 undersells | 🟠 |
| §19 | Deuda técnica | 🟡 parcial | 132 hallazgos de pyflakes; 0 linters configurados | 🟡 |
| §20 | Checklist final de 1.0 | 🔴 bloqueante | 8 bloqueantes abiertos | 🔴 |

### §0.2 Top 11 bloqueantes para 1.0

| # | Bloqueante | Evidencia | Archivo |
|---|-----------|-----------|---------|
| B1 | `pengu check <archivo>` **ignora el archivo** y reporta "Clean no errors found" | `pengu check bad1.pengu` → exit 0, "Clean", archivo con `echo "not a keyword"` | `pengu_project.py:4745`, `:5052` |
| B2 | `--strict-c99` emite C que **no compila** (el gate de CI es un `grep` de texto) | 13 errores duros de gcc; `'k' undeclared` | `pengu_parser/pengu_codegen.py:4232-4256` |
| B3 | `pengu fmt --indent N` **corrompe silenciosamente** el fuente del usuario | `--indent 4` colapsa la indentación; exit code 0 | `pengu_lsp/formatting.py:234` |
| B4 | Acceder a un símbolo privado lanza **`NameError`** en vez de `E0043` | `NameError("name 'node' is not defined")` reproducido | `pengu_parser/pengu_infer.py:4055` |
| B5 | Tipos cualificados a través de un módulo re-exportador **pierden los campos** | `dep.Vec` → "Rune 'dep.Vec' fields are: ." ; `Vec` sin cualificar funciona | `pengu_parser/pengu_infer.py:1465-1468` |
| B6 | `pengu_parser/pengu_runtime.c` **no compila** sin un flag que suprime 24 errores duros | 24× `-Wimplicit-function-declaration` (mbedtls private API) | `build_runtime.py:1195-1204` |
| B7 | El job de ASan que el commit `77f4ed8` decía arreglar **sigue en rojo** | 1033 bytes en 5 allocs; 2 failed | `.github/workflows/sanitizers.yml:58-70` |
| B8 | `parse_known_args()` **descarta flags desconocidos en silencio** | `pengu check --bogus` → exit 0, "Clean" | `pengu_project.py:4881` |
| B11 | El grammar tiene **188 conflictos shift/reduce** resueltos por heurística de Lark | `Lark(..., debug=True)` → 188 conflictos / 79 terminales; la semántica de expresiones depende del default "shift gana" | `pengu_parser/pengu_grammar.py` (584 líneas) |

### §0.3 Top 10 quick wins

| # | Quick win | Esfuerzo | Por qué |
|---|-----------|----------|---------|
| Q1 | `parser.error()` si `unknown` no está vacío en `parse_known_args` | S | Cierra 4 clases de fallo silencioso de una vez |
| Q2 | Añadir `file` positional (nargs='*') a `check`/`test` | S | Convierte `pengu check` en la herramienta que los usuarios creen que es |
| Q3 | `check_sources_diagnostics` debe fallar si el entry no existe | S | Evita el peor fallo silencioso del CLI |
| Q4 | Corregir `node` → `target_node` en `pengu_infer.py:4055` | S | Un carácter; elimina un crash |
| Q5 | Normalizar el nombre cualificado antes de `lookup_type` | S | 2 líneas; desbloquea toda la cadena de bindings C |
| Q6 | `-DMBEDTLS_ALLOW_PRIVATE_ACCESS` y borrar los dos `-Wno-*` | S | El runtime vuelve a ser C99 legal (verificado) |
| Q7 | Eliminar `pengu_runtime.c` raíz (0 bytes) del índice de git | S | Trampa documental para contribuidores |
| Q8 | Usar `%g` en la ruta de interpolación de floats | S | Consistencia `to string` vs `"{x}"` |
| Q9 | Documentar `pengu check` como "solo proyecto" **o** aceptarlo como archivo | S | Honestidad inmediata |
| Q10 | Registrar `@server.command("pengu.runTest")` o borrar el codeLens | S | Feature visible que no hace nada |

### §0.4 Honestidad: ¿cuántas reivindicaciones de la documentación son falsas?

| Métrica | Valor | Método |
|---------|-------|--------|
| Clases de error citadas en `LANGUAGE.md` §22.2 que **no existen** | **5** de 59 (`DanglingSliceError`, `DuplicateConstantError`, `AmbiguousStructInitError`, `StaticArrayError`, `ErrorLiteralContextError`) | `grep -rn "<Clase>" --include="*.py"` → **0 referencias** cada una |
| Entradas del catálogo §22.2 con atribución de clase incorrecta | **5** (`E0014`, `E0018`, `E0020`, `E0045` → `TypeMismatchError` que declara `E0005`; `E0047` → `DuplicateConceptBindingError` que declara `E0052`) | Cruce regex doc vs `setdefault` en `pengu_errors.py` |
| Códigos emitidos como string crudo sin clase dedicada | **24** de 58 | Comparación de emisiones `code="Exxxx"` vs clases |
| Ejemplos `pengu` de `LANGUAGE.md` que no pasan `pengu check` | **71** de **104** (68 %) | Bucle real con `pengu check -c <proyecto>`, con un parser de fences por líneas |
| Afirmaciones documentales refutadas explícitamente en esta auditoría | **23** | Ver §18.1 |
| Afirmaciones que la documentación **subestima** | **12** | Ver §18.3 |
| Afirmaciones de **esta propia auditoría** corregidas tras re-verificación | **2** | §9.10 (sintaxis `prototype`) y §1.1 (número de conflictos LALR: 1 → 188) |

**Conclusión de honestidad:** la documentación no es *sistemáticamente* mentirosa —las cifras de
`BENCHMARKS.md`, el reconocimiento del leak en `docs/PERFORMANCE.md` y los tres primeros capítulos
de `LANGUAGE.md` son honestos— pero el **catálogo de errores §22.2 es ficción parcial** (5 clases
inexistentes, 5 atribuciones incorrectas), **10 de sus 59 filas no son fiables**, y la **guía de
estilo contradice al propio `pengu fmt`** en el ancho de indentación (§10.2). Ambas cosas son peores
que un error de código porque los usuarios las copian literalmente.

> **Nota de autocorrección:** una versión preliminar de este informe afirmaba que las guías de
> estilo enseñaban una sintaxis `prototype` obsoleta. Era **falso** y se retira con evidencia en
> §9.10. Se documenta para que el lector pueda calibrar cuánto se verificó.

### §0.5 Los tres "gates verdes sobre código roto"

Este es el patrón más peligroso encontrado y merece su propio apartado:

| Gate | Qué afirma | Qué pasa realmente |
|------|-----------|---------------------|
| `tests/test_cli_strict_c99.py:50` | `--strict-c99` produce C portable | Solo comprueba que las cadenas `__extension__`/`__auto_type` **no aparecen** en el bundle. No compila nada importando `std`. El bundle estricto falla con 104 errores de `-pedantic-errors`. |
| `tests/test_c99_portability.py` | Igual | Compila un programa de ~20 líneas **sin imports**. 5 passed. |
| `.github/workflows/sanitizers.yml` | El leak conocido queda "visible pero sin romper CI" | El paso 3 vuelve a ejecutar el mismo archivo con `detect_leaks=1`, así que el job **falla**. |
| `tests/test_error_codes_uniqueness.py` | "no two error classes share a code" | Solo inspecciona `kwargs.setdefault(...)`, así que **24 emisiones con string crudo** quedan fuera. `E0035` cubre 4 condiciones semánticas no relacionadas. |
| `ci.yml` (Windows) | "MSVC" en la matriz | `CC_BIN="gcc"` (MinGW) hardcodeado. No hay `cl.exe` en ninguna parte. |

---

## §1. Parser / Grammar (`pengu_grammar.py`, `pengu_parser.py`)

> **Veredicto:** 🟠 **con problemas graves**

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| Conflictos LALR(1) | ❌ **188 shift/reduce en 79 terminales** | `Lark(..., debug=True)` enumera 188 conflictos; `strict=True` aborta en el primero (el terminal reportado varía: `ELSE`, `WITH`, `INTO`, `DOT`, …) | 🟠 |
| Precedencia/asociatividad efectivas | ✅ **Correctas en los 9 casos medidos** | `1-2-3`→`-4`; `1+2*3`→`7`; `2*3%4`→`2`; `-5`→`-5` | ✅ (por heurística, no por diseño) |
| Reglas del manual que parsean | 🟡 33/105 bloques pasan `pengu check` completos | Ver §13.2 (muchos son fragmentos o ejemplos marcados "Invalid") | 🟡 |
| Precedencia de operadores vs documentado | ✅ Correcta en los casos medidos | `xs at i + 1` documentado como `(xs at i) + 1`; coinciden | 🟢 |
| Soft keywords en contextos ambiguos | ✅ Funcionan | `frozen`, `borrowed`, `inline`, `ritual` | 🟢 |
| `DedentError` capturado | ✅ Sí, con línea/columna | `PenguIndenter.handle_NL` → `exc.line`, `exc.column` | 🟢 |
| Literales numéricos (`0b`/`0o`/`0x`/`_`) | ✅ Funcionan | `0b1010`, `0o777`, `0xFF_FF`, `1_000_000` todos compilan y corren | 🟢 |
| `\u{...}` en strings | ✅ Funciona | `"\u{1F427}"` → 🐧 | 🟢 |
| Comentarios `#`, `##`, inline | ✅ Funcionan | `_strip_comments` preserva alineación de líneas | 🟢 |
| BOM UTF-8 | ✅ Funciona | `strip_bom()` consume múltiples U+FEFF | 🟢 |
| CRLF | ✅ Funciona | `\r?\n` en `_NEWLINE` y `.replace("\r\n","\n")` | 🟢 |
| Identificadores Unicode | ❌ **No soportados** | `NAME: /[a-zA-Z_][a-zA-Z0-9_]*/` → `const 日本語 as int is 1` falla | 🟡 |
| `alias` dentro de `concept` | ❌ Documentado, no implementado | `LANGUAGE.md:1298` enseña `concept Iterabilis shard Self:` + `alias Item`; el grammar no tiene esa producción | 🟠 |
| Docstring de versión | ❌ Desactualizado | `pengu_parser.py:92`: "LALR(1) parser for PenguScript **v0.14.x**" con `VERSION`=0.16.0 | 📝 |

### §1.1 Hallazgo P1 — El grammar **no es LALR(1)**: 188 conflictos shift/reduce en 79 terminales

> **Nota de autocorrección:** una versión preliminar de esta sección reportaba **un solo** conflicto
> (`ELSE`, *dangling else*), porque `Lark(strict=True)` aborta en el primero que encuentra y el orden
> depende del hash de Python. Al enumerarlos con `debug=True` (que reporta **todos**) el número real
> es **188**. Se corrige aquí, y se mantiene el registro del error para que el lector calibre el
> nivel de verificación del resto del informe.

**Evidencia reproducible — un solo conflicto visto con `strict=True`:**

```bash
$ .venv/bin/python -c "
from lark import Lark
from pengu_parser.pengu_grammar import GRAMMAR
Lark(GRAMMAR, parser='lalr', propagate_positions=True, strict=True)
"
lark.exceptions.GrammarError: Shift/Reduce conflict for terminal ELSE. [strict-mode]
 * <unless_stmt : UNLESS expr block>
```

El terminal reportado **cambia entre ejecuciones** (`ELSE`, `WITH`, `INTO`, `DOT`, `COMMA`,
`_NEWLINE`, `_BOOL_AND`, …), lo que ya indicaba que no era un conflicto único.

**Evidencia reproducible — el conjunto completo:**

```bash
$ .venv/bin/python - <<'EOF'
import logging, io
import lark.parsers.lalr_analysis as M
buf = io.StringIO(); h = logging.StreamHandler(buf); h.setLevel(logging.WARNING)
M.logger.addHandler(h); M.logger.setLevel(logging.WARNING); M.logger.propagate = False
from lark import Lark
from pengu_parser.pengu_grammar import GRAMMAR
Lark(GRAMMAR, parser='lalr', propagate_positions=True, debug=True, cache=None)
lines = [l for l in buf.getvalue().splitlines() if 'conflict' in l.lower()]
print("conflicts:", len(lines))
print("distinct terminals:", len({l.split('terminal ')[1].split(':')[0].split(' ')[0]
                                 for l in lines if 'terminal ' in l}))
EOF
conflicts: 188
distinct terminals: 79
```

**Los 79 terminales en conflicto** (todos resueltos como *shift*):

```
AMPERSAND ARRAY ARROW AS BANISH BYTES CALLING CHAR_LIT CHR CIRCUMFLEX COLON COMMA DEFINED DO
DONUM DOT DOTDOT ELSE ERROR ESSENCE FALSE FLOAT FOR IF IN INT INTO IS JUDGE LAMBDA LBRACE
LENGTH LESSTHAN LIST LPAR LSQB MAP MAYBE MINUS MORETHAN NAME NOT NULL OF OR ORD PERCENT PLUS
RAW_STRING RAW_TRIPLE_STRING SELF SIGIL SIZE SLASH SOME STAR STRING TILDE TO TRANSMUTE
TRIPLE_STRING TRUE TRY UNLESS VBAR WHEN WHILE WITH _AND_SEP _BOOL_AND _BOOL_OR _NEWLINE
__ANON_1 … __ANON_7
```

**Las causas se agrupan en cinco familias** (no es solo el *dangling else*):

| Familia | Ejemplo de conflicto citado por Lark | Naturaleza |
|---------|--------------------------------------|-----------|
| **Dangling else** | `ELSE` sobre `<unless_stmt : UNLESS expr block>` y `<if_stmt : IF if_cond block>` | Ambigüedad clásica de `if`/`unless` anidados |
| **Asociatividad y precedencia** | `PLUS`/`MINUS`/`STAR`/`SLASH`/`PERCENT`/`CIRCUMFLEX`/`AMPERSAND`/`VBAR`/`TO` sobre `<bit_add : bit_add PLUS bit_mul>`, `<logic_or : logic_or VBAR logic_and>`, `<comparison : comparison …>` | Lark no recibe una tabla `%left`/`%right`, así que **cada** nivel de la jerarquía de expresiones genera conflictos |
| **Opcionalidad de sufijos** | `_NEWLINE` sobre `<var_decl : VAR NAME AS type IS value_expr>` y `<const_decl : CONST NAME AS type IS expr>`; `ARRAY`/`INT`/`NAME`/… sobre `<return_stmt : RETURN>` | El `[_NEWLINE]` opcional y el `[value_expr]` opcional hacen que el parser no sepa si reducir o esperar |
| **Prefijos compartidos de tipos** | `WITH` sobre `<fn_type : WEAVE>`, `<array_type : ARRAY OF type>`, `<list_init_expr : LIST OF type>`, `<calling_expr : CALLING normal_target>`; `OF` sobre `<custom_type : dotted_path>` | Muchas producciones empiezan igual y difieren más adelante |
| **Caminos punteados y targets** | `DOT`/`ARROW`/`__ANON_1` sobre `<dotted_path : NAME>`, `<normal_target : NAME>`, `<normal_target : SELF>`, `<with_target : DOT NAME>` | `a.b.c` puede ser un tipo, un target de asignación o un acceso a campo |

**Y sin embargo, la precedencia y la asociatividad son correctas en la práctica.** Esto hay que
decirlo con la misma claridad, porque es el contrapeso del hallazgo. Verificación end-to-end:

```bash
$ # programa real con std.spark
$ pengu run
-4        # "{1 - 2 - 3}"   -> asociatividad izquierda correcta
7         # "{1 + 2 * 3}"   -> precedencia correcta
2         # "{2 * 3 % 4}"   -> izquierda-a-derecha correcta
-5        # "{-5}"          -> negación unaria correcta
```

Y el árbol sintáctico de casos límite:

| Expresión | Nodo raíz | ¿Correcto? |
|-----------|-----------|-----------|
| `1 - 2 - 3` | `sub` | ✅ (izquierda) |
| `1 - (2 - 3)` | `sub` con paréntesis | ✅ |
| `1 + 2 * 3` | `add` (con `mul` a la derecha) | ✅ |
| `(1 + 2) * 3` | `mul` | ✅ |
| `2 * 3 % 4` | `mod` | ✅ |
| `-5` | `neg` | ✅ |
| `a - -5` | `sub` | ✅ |
| `true and false or true` | `bool_or` | ✅ |
| `not a and b` | `bool_and` | ✅ |

**Por qué funciona entonces:** Lark resuelve **todo** conflicto shift/reduce a favor de *shift*, y en
una gramática de expresiones construida en cascada (`bit_add: bit_add "+" bit_mul | …`) *shift*
produce exactamente la asociatividad izquierda y la precedencia correctas. Es decir: **el lenguaje
funciona porque la heurística por defecto de una dependencia externa resulta ser la correcta para
esta gramática concreta.**

**Impacto:**

1. **Es correcto hoy y depende de una heurística de terceros.** Toda la semántica de expresiones de
   PenguScript descansa en el comportamiento "shift gana" de Lark. Si una versión futura de Lark
   cambia ese default, o si alguien pasa `strict=True`/`ambiguity='explicit'` a
   `Lark(...)` en `PenguParser.__init__`, **la semántica de programas existentes cambia sin ningún
   error de compilación**. No hay ningún test que fije la asociatividad de forma explícita más allá
   de los golden outputs numéricos.
2. **La afirmación "parser LALR(1)" es imprecisa.** El docstring de `PenguParser` (`:92`) dice
   *"LALR(1) parser for PenguScript v0.14.x"*. Con 188 conflictos resueltos por heurística, es
   "LALR(1) **con conflictos resueltos por shift**", no una gramática LALR(1) estricta.
3. **Las 29 reglas duplicadas (§1.4) son la causa principal.** La cascada `*_no_cast` y `guard_*`
   duplica la jerarquía de expresiones completa, y cada duplicado añade conflictos de precedencia.
   El número de 188 no es inherente al lenguaje; es consecuencia de cómo está escrito el grammar.
4. **Los mensajes de error en casos ambiguos pueden apuntar mal.** El error se descubre tras haber
   consumido tokens que luego hay que reinterpretar (por eso la posición reportada suele ser la del
   token *siguiente*, no la del problema real).

**Fix propuesto (una frase):** añadir una tabla de precedencia explícita
(`%left`/`%right`/`%nonassoc`) para la jerarquía de expresiones y colapsar las 29 reglas duplicadas
(§1.4), lo que debería reducir los conflictos a un puñado; **y mientras eso no ocurra, añadir un test
que fije la asociatividad/precedencia de las 9 expresiones de la tabla anterior**, para que un cambio
de heurística falle en CI en vez de cambiar la semántica en silencio.

### §1.2 Hallazgo P2 — `alias` en `concept` está documentado y no existe

`LANGUAGE.md:1298` documenta la sintaxis completa de un concept así:

```
concept Name [shard T [and U]] [where T: OtherConcept] :
```

y el bloque 59 de `LANGUAGE.md` (sección de concepts) escribe literalmente:

```pengu
concept Iterabilis shard Self:
    alias Item
    weave next with it as ref to Self into maybe Self.Item
```

El grammar (`pengu_grammar.py:92-93`) define:

```
concept_decl: "concept" NAME [shard_params] ":" _NEWLINE _INDENT concept_method+ _DEDENT
concept_method: weave_modifier* "weave" weave_modifier* NAME [shard_params] ["with" param_list] ["into" type] _NEWLINE
```

No hay producción para `alias` dentro de `concept_method`. Resultado real:

```
$ pengu check   # bloque 59 de LANGUAGE.md
/tmp/docaudit/src/main.pengu:2:5 [E0000] Syntax error: unexpected 'alias' at line 2, column 5
```

**Impacto:** los *associated types* (el mecanismo que permitiría escribir `Iterabilis` genérico con
un tipo `Item` asociado) están **documentados como existentes** pero no existen. Cualquier usuario
que intente definir un concept iterable con tipo de elemento asociado choca con un error de sintaxis
sin pista de que la feature no está implementada.

**Fix propuesto:** o implementar `alias NAME` en `concept_method` (con resolución en bounds
`Self.Item`), o borrar el ejemplo y marcar la feature como ⏸️ DIFERIDO en §22 con un aviso explícito.

### §1.3 Hallazgo P3 — Identificadores no-ASCII rechazados

`NAME: /[a-zA-Z_][a-zA-Z0-9_]*/` limita los identificadores a ASCII. Los literales de string sí
aceptan Unicode completo (`\u{...}`), y el lenguaje se presenta como Unicode-friendly (BOM, CRLF,
`\u{...}`), lo que crea una expectativa que los identificadores no cumplen.

**Impacto:** bajo para el público objetivo (la stdlib es toda ASCII), pero es una incoherencia
notable dado el cuidado puesto en BOM y `\u{...}`.

**Fix propuesto:** documentar explícitamente "los identificadores son ASCII" en `LANGUAGE.md` §2
(una línea) en vez de cambiar el lexer.

### §1.4 Hallazgo P4 — Reglas del grammar potencialmente inalcanzables

Varias producciones existen pero no se observaron en ningún camino de parseo real durante la
auditoría. Se marcan como candidatas a código muerto, no como muertas confirmadas:

| Regla | Motivo de sospecha | Estado |
|-------|--------------------|--------|
| `simple_stmt` con `return`/`set`/`break`/`continue` | Se usan vía `SIMPLE_STMT_ALIASES`; la regla `simple_stmt` en sí puede no reducirse nunca | 🟡 candidata |
| `guard_*` (12 reglas: `guard_bool_or`, `guard_bit_mul`, …) | Duplican por completo la jerarquía `logic_or`/`bit_add`/… para el guard de `when_clause`. Un `when_guard` podría reutilizar las reglas normales con un flag | 🟡 duplicación real |
| `when_top_else` / `when_else` / `else_block` | Tres formas distintas del mismo constructo en tres contextos | 🟡 duplicación |
| `expr_no_cast` / `logic_or_no_cast` / … (11 reglas `*_no_cast`) | Duplican la jerarquía entera solo para excluir `transmute` en `for`/`slice_range` | 🟡 duplicación real, ~40 líneas |

**Cuenta:** de ~150 producciones en el grammar, **~29 son duplicados estructurales** de otra
producción con una restricción (`_no_cast`) o un contexto (`guard_`) distinto. Eso explica por qué
`pengu_grammar.py` tiene 584 líneas para un lenguaje de este tamaño y por qué aparecen **188
conflictos** shift/reduce (§1.1): cada duplicado de la jerarquía de expresiones aporta su propia
familia de conflictos de precedencia.

**Fix propuesto:** introducir un flag de contexto en el parser (o usar `transmute` como postfix
explícito) para colapsar `*_no_cast` en las reglas base, reduciendo el grammar a ~110 producciones.

### §1.5 Cosas que funcionan bien (✨ UNDERSELL)

- El **indenter con detección de "múltiples sentencias en una línea"** (`PenguIndenter._process`)
  es una mejora real: `var x is 1 var y is 2` produce un `E0000` claro en vez de un error críptico
  de Lark. La mayoría de lenguajes con indentación no detectan esto.
- El **cache de tablas LALR** (`pengu_cache.grammar_digest` + `parser_cache_path`) con fallback
  "si el cache está corrupto, reconstruir sin cache" es exactamente la ingeniería correcta para un
  arranque de 2-3 s. Redujo el arranque de `pengu check` a ~170 ms en un archivo pequeño.
- La **desambiguación de `or` booleano vs `or else`/`or return`/`or:`** mediante prioridades de
  terminal (`_BOOL_OR.3`, `_BOOL_AND.2`, `_AND_SEP.5`) es una solución elegante y está documentada
  en un comentario de 5 líneas en el propio grammar. Es el tipo de decisión que suele quedar sin
  documentar.

---

## §2. Semantic Checker (`pengu_checker.py`)

> **Veredicto:** 🟠 **con problemas graves** — la cobertura semántica es amplia y el checker es
> reentrante, pero hay un **crash confirmado**, un **catálogo de errores que no coincide con el
> código**, y un **test de unicidad que no prueba lo que dice probar**.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| Todos los `E0000`–`E0058` se emiten | ✅ Sí, los 58 | `grep -ohP 'E\d{4}'` sobre checker+infer+types → 58 códigos únicos | 🟢 |
| Clases de error documentadas que existen | ❌ **54 de 59** | 5 clases citadas en `LANGUAGE.md` §22.2 → **0 referencias** en todo el Python | 🟠 |
| Clases de error en código sin entrada en el catálogo | 🟡 24 códigos sin clase | Emitidos como `code="Exxxx"` crudo | 🟡 |
| El test de unicidad realmente prueba unicidad | ❌ **No** | `tests/test_error_codes_uniqueness.py` solo parsea `kwargs.setdefault(...)`; ignora 24 emisiones crudas | 🟠 |
| `E0035` es un código, un significado | ❌ **No**: cubre **4** condiciones | "reserved C keyword" ∥ "static var no está dentro de weave" ∥ "test name vacío" ∥ "field collides" | 🟠 |
| Verificación de concept bounds bidireccional | 🟡 Parcial, con jerarquía incoherente | `T: Num` acepta `==` pero rechaza `<` (ver §3.1) | 🟠 |
| Escape analysis completo | 🟡 Parcial | `_check_symbol_escape` tiene 406 líneas; `while true: return 1` da falso positivo | 🟡 |
| Auto-banish de scope-owned locals completo | ✅ Sí | `AutoOwnedBanishError` (E0047), `BorrowedBanishError` (E0048) existen y se emiten | 🟢 |
| `frozen` preservado | ✅ Sí | `FrozenType` + `set_restrict_keyword` | 🟢 |
| Checker reentrante / thread-safe para LSP | ✅ Reentrante; ⚠️ no thread-safe por diseño | `check()` **reconstruye** `self.inferrer` (`pengu_checker.py:3972` contexto) con el `source`/`filename` nuevos → probado: reusar una instancia con otro fuente funciona igual que una fresca | 🟢 |
| `_check_weave_decl` detecta retornos faltantes en todas las ramas | ✅ Sí, pero con falso positivo | 6 casos probados; `while true: return 1` **rechazado incorrectamente** | 🟡 |
| Bounds `T: Num/Integrum/Par/Ordo` en todos los contextos | 🟡 Incoherente | Ver matriz §3.1 | 🟠 |
| `derive` con todos los concepts derivables | 🟡 Solo `Par`/`Ordo` verificados | `derive Par`, `derive Ordo`, `derive Par, Ordo` → OK. No verificado para `Vinculum`/`Nexus`/`Imago`/`Forma` | 🟡 |
| Métodos duplicados en `PenguChecker` | ✅ **Ninguno** | `grep -oP '^    def \K\w+' \| sort \| uniq -d` → vacío (la auditoría anterior los encontró y fueron arreglados) | ✅ RESUELTO |
| Emisiones de código de error totales | 206 en checker + 171 en infer = **377** | `grep -c 'code="E0'` | 🟢 |

### §2.1 Hallazgo S1 — 🔴 `E0043` lanza `NameError` en vez del error documentado

**Evidencia reproducible (mínima, con dos módulos locales):**

```bash
$ mkdir -p /tmp/pv && cd /tmp/pv && printf 'weave _secret into int:\n  return 1\n' > lib.pengu
$ .venv/bin/python - <<'EOF'
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
p = PenguParser()
src = 'import lib\nweave main into int:\n  return calling lib._secret\n'
c = PenguChecker(source=src, filename='/tmp/pv/main.pengu', base_dir='/tmp/pv')
c.check(p.parse(src), source=src, filename='/tmp/pv/main.pengu')
EOF
*** NameError CONFIRMED BUG: NameError("name 'node' is not defined")
```

**Código culpable** — `pengu_parser/pengu_infer.py`, dentro de `_resolve_call_target(self, target_node: Tree)`
(declarada en la línea 3881):

```python
# pengu_infer.py:4051-4056
if getattr(mem_sym, "is_public", False) is False or m_name.startswith("_"):
    raise self._make_error(
        PrivateSymbolAccessError,
        f"Symbol '{m_name}' is private to module '{obj_name}'",
        node,                      # <-- 4055: 'node' no existe; el parámetro es 'target_node'
        code="E0043",
```

`pyflakes` lo detecta como `undefined name 'node'` en `pengu_infer.py:4055:49`, y
`_resolve_call_target` **no recibe ningún parámetro llamado `node`** ni asigna uno localmente
(verificado con AST: `local 'node =' assignments before: []`).

**Impacto:** cuando un usuario accede a un símbolo privado de otro módulo, en lugar de recibir el
diagnóstico `E0043 PrivateSymbolAccessError` recibe un **traceback de Python** y el compilador
termina con un error interno. Es un crash del compilador en un camino de error del usuario, es
decir, exactamente el caso donde un compilador nunca debe fallar.

**Fix propuesto:** sustituir `node` por `target_node` en la línea 4055 y añadir un test de
regresión que importe un módulo con un símbolo `_privado` y compruebe que se emite `E0043`.

### §2.2 Hallazgo S2 — Cinco clases de error del catálogo **no existen**

`LANGUAGE.md:3386` titula la sección "### 22.2 Compiler Error Catalog (`E0000`–`E0058`)" y presenta
una tabla con dos columnas: `Code` y **`Exception Class`**. Cinco de esas clases no aparecen en
**ningún archivo Python del repositorio**:

| Código | Clase que el catálogo afirma | Referencias reales en `*.py` | Lo que el código emite de verdad |
|--------|------------------------------|------------------------------|----------------------------------|
| `E0051` | `DanglingSliceError` | **0** | `SemanticError(code="E0051")` — `pengu_checker.py:6919` |
| `E0053` | `DuplicateConstantError` | **0** | `SemanticError(code="E0053")` — `pengu_checker.py:2715,3952,4296,4307` |
| `E0054` | `AmbiguousStructInitError` | **0** | `SemanticError(code="E0054")` — `pengu_infer.py:1533` |
| `E0055` | `StaticArrayError` | **0** | `SemanticError(code="E0055")` — `pengu_checker.py:4231` |
| `E0058` | `ErrorLiteralContextError` | **0** | `SemanticError(code="E0058")` — `pengu_infer.py:1019` |

**Comando de verificación (devuelve 0 para las cinco):**

```bash
for cls in DanglingSliceError DuplicateConstantError AmbiguousStructInitError StaticArrayError ErrorLiteralContextError; do
  echo -n "$cls -> "; grep -rn "$cls" --include="*.py" . | grep -v .venv | wc -l
done
DanglingSliceError -> 0
DuplicateConstantError -> 0
AmbiguousStructInitError -> 0
StaticArrayError -> 0
ErrorLiteralContextError -> 0
```

**❌ REFUTADO:** `LANGUAGE.md` §22.2 documenta estas cinco clases como existentes. No existen.

**Además, cinco entradas atribuyen el código a una clase que declara un código distinto:**

| Entrada del catálogo | Clase atribuida | Código que esa clase realmente declara |
|----------------------|-----------------|-----------------------------------------|
| `E0014` | `TypeMismatchError` | `E0005` |
| `E0018` | `TypeMismatchError` | `E0005` |
| `E0020` | `TypeMismatchError` | `E0005` |
| `E0045` | `TypeMismatchError` | `E0005` |
| `E0047` | `DuplicateConceptBindingError` | `E0052` |

El último caso es el más claro: **el propio test del repositorio contradice a la documentación**.

```python
# tests/test_error_codes_uniqueness.py
def test_duplicate_concept_binding_has_its_own_code():
    """E0047 stays for AutoOwnedBanishError; the binding collision is E0052."""
    codes = _class_default_codes()
    assert codes.get("AutoOwnedBanishError") == "E0047"
    assert codes.get("DuplicateConceptBindingError") == "E0052"
```

Mientras el test afirma `DuplicateConceptBindingError == E0052`, `LANGUAGE.md:3443` lista la fila
`| E0047 | AutoOwnedBanishError / DuplicateConceptBindingError | ...`. **La documentación y el test
se contradicen mutuamente, y el test tiene razón.**

**Impacto:** un usuario que lea el catálogo para hacer `except DuplicateConstantError:` recibirá un
`ImportError`/`AttributeError`. El catálogo es la única referencia de diagnóstico del proyecto y no
es fiable en 10 de sus 59 filas.

**Fix propuesto:** generar la tabla §22.2 automáticamente desde `pengu_errors.py` +
un registro declarativo de emisiones crudas, y fallar el build si el doc y el código divergen.

### §2.3 Hallazgo S3 — `E0035` cubre cuatro condiciones no relacionadas

El test `test_error_codes_uniqueness.py` existe precisamente porque una auditoría anterior encontró
códigos compartidos entre diagnósticos sin relación. El test arregló **cinco** casos
(`E0047`, `E0035`↔redefinición, `E0011`↔struct init, `E0051`, `E0055`) pero **no cerró la clase de
bug**, porque solo mira `kwargs.setdefault`. Las 13 emisiones crudas de `E0035` siguen ahí:

| Mensaje emitido con `code="E0035"` | Emisiones | Naturaleza real |
|-----------------------------------|-----------|-----------------|
| `"Type name '{X}' is a reserved C keyword or standard identifier"` | 6 sitios (runes, echoes, omens, seals, aliases, concepts) | Colisión con C |
| `"Function name '{fn}' is a reserved standard C function or identifier"` | 2 | Colisión con C |
| `"Constant name '{c}' is a reserved C keyword or standard identifier"` | 1 | Colisión con C |
| `"'static var' is only allowed directly inside a function body (weave)."` | 1 | Ubicación de declaración |
| `"Test name must be a non-empty string or identifier"` | 1 | Nombre de test inválido |
| `"Field '{f}' collides with field '{seen}' in C code emission"` | 1 | Colisión de campos en C |
| `"'main' can only appear as the condition of a compile-time 'when'."` | 1 | `main` reservado |

**Impacto:** `E0035` es inútil para herramientas (no se puede distinguir "renombra tu rune porque
choca con `int`" de "mueve tu `static var` dentro de una función"). Cualquier IDE que quiera ofrecer
un quick-fix por código no puede hacerlo.

**Fix propuesto:** extender `test_error_codes_uniqueness.py` para que también analice las emisiones
de string crudo (`re.findall(r'code="(E\d{4})"')` en checker/infer) y exija que cada `(código,
mensaje)` sea único, luego asignar códigos nuevos a las condiciones desplazadas.

### §2.4 Hallazgo S4 — Falso positivo en la detección de retornos faltantes

```bash
$ .venv/bin/python <<'EOF'
# 6 casos de _check_weave_decl
"while loop returning": 'weave f into int:\n  while true:\n    return 1\n'   -> E0020
EOF
  missing return (if branch only)            -> E0020: Function 'f' declared into 'int' does not return a value
  missing return (if/else one arm)           -> E0020: ...
  missing return (no return at all)          -> E0020: ...
  missing return (judge non-exhaustive)      -> E0020: ...
  ok                                         -> NO ERROR
  while loop returning                       -> E0020: Function 'f' declared into 'int' does not return a value
```

La detección de ramas faltantes es **correcta** en 5 de 6 casos —mejor de lo que una auditoría
apresurada supondría— pero no reconoce `while true:` (o `while <constante verdadera>`) como un
camino que no puede caer fuera del bucle. Código perfectamente válido y común (bucles de servidor,
máquinas de estado) es rechazado.

**Impacto:** medio. Obliga a escribir `return 0` inalcanzable al final de bucles infinitos, o a
reescribir con `for`/banderas. Rompe el principio de "explícito sobre implícito" en la dirección
equivocada: el compilador exige código muerto para *demostrar* algo que ya sabe.

**Fix propuesto:** tratar un `while` cuya condición se pliega a `true` (o es literal `true`) como
sentencia terminante en `_check_weave_decl`, igual que ya se hace con `return`.

### §2.5 Lo que el checker hace bien (✨ UNDERSELL)

- **377 sitios de diagnóstico** con `help:` y `note:` estructurados en casi todos los casos. El
  nivel de detalle de los mensajes (con sugerencias de renombrado, notas sobre la semántica de C) es
  superior a la media de compiladores en beta.
- **Reentrancia real y verificada.** Reutilizar un `PenguChecker` construido con el código A para
  chequear el código B produce exactamente los mismos errores que un checker fresco, porque `check()`
  reconstruye `inferrer` y `const_folder` con el `source_code`/`filename` nuevos. Es el patrón que
  el LSP necesita y está bien resuelto.
- **Cero métodos duplicados** en `PenguChecker` (121 métodos, todos con nombre único) y en
  `PenguCodegen` (170 métodos, todos únicos). La auditoría anterior encontró duplicados; están
  resueltos. **✅ RESUELTO.**
- **`_check_symbol_escape`** (406 líneas) es un análisis de escape genuino, no un stub: cubre
  auto-ownership, `borrowed`, views y retorno de slices de arrays de pila.

---

## §3. Type Inferrer (`pengu_infer.py`)

> **Veredicto:** 🟠 **con problemas graves** — el motor es potente y cubre genéricos, contenedores
> anidados y closures, pero la **jerarquía de bounds es incoherente** y los **tipos cualificados
> pierden sus campos**, lo que rompe toda la cadena de bindings C.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| Todos los tipos se infieren / `AnyType` residual | 🟡 Parcial | `AnyType` se usa como fallback en varios caminos (`_resolve_call_target` devuelve `AnyType()`); no se midió cuántos programas reales dependen de él | 🟡 |
| Inferencia de genéricos completa | 🟡 Parcial | Funciona en módulo local; falla a través de módulos cualificados (§3.2) | 🔴 |
| Operadores `+ - * / % == != < <= > >=` respetan los bounds | ❌ **Incoherente** | Matriz §3.1: `T: Num` acepta `<`, `==`; `T: Par` rechaza `<`; `T: Ordo` rechaza `==` | 🟠 |
| `or:` / `or else` / `or return` / `try` | ✅ Funcionan | `E0045` y `E0058` se emiten correctamente; `'or:' requires a 'maybe T' or 'result of T to E' operand` es un buen mensaje | 🟢 |
| `maybe` / `result` en todos los contextos | ✅ Mayormente | `maybe none`, `some x`, `is present`, `is not present`, `is true/false` | 🟢 |
| Contenedores anidados (`list of list of string`, `map of K to list of V`) | ✅ Funcionan | Cubierto por `tests/test_compiler_core.py`; `atlas`/`coven`/`loom` usan mapas anidados | 🟢 |
| Closures / lambdas | ✅ `lambda` sin captura funciona y está correctamente restringido | El grammar y los comentarios documentan la ausencia de captura como decisión de diseño consciente | 🟢 |
| `derive` en runes | ✅ `Par`, `Ordo`, `Par, Ordo` verificados | Bloque anterior | 🟢 |
| Tipos cualificados entre módulos | ❌ **Pierden los campos** | `dep.Vec` → `Rune 'dep.Vec' fields are: .`; `Vec` sin cualificar funciona | 🔴 |
| `node` no definido (crash) | ❌ | Ver §2.1 | 🔴 |

### §3.1 Hallazgo T1 — La jerarquía de bounds es **incoherente y no coincide con la documentación**

**Evidencia: matriz completa operador × bound, generada ejecutando el checker real:**

```
op                 (none)       Num  Integrum       Par      Ordo
+                  EE0049        OK        OK    EE0049    EE0049
%                  EE0049    EE0049        OK    EE0049    EE0049
==                 EE0049        OK        OK        OK    EE0049
<                  EE0049        OK        OK    EE0049        OK
& (bitand)         EE0049    EE0049        OK    EE0049    EE0049
<<                 EE0049    EE0049        OK    EE0049    EE0049
```

Comando que la produce:

```python
for b in ["(none)","Num","Integrum","Par","Ordo"]:
    for op, ex in [("+","a + b"),("%","a % b"),("==","a == b"),("<","a < b"),("&","a & b"),("<<","a << b")]:
        where = "" if b=="(none)" else f" where T: {b}"
        src = f"weave f shard T{where} with a as T, b as T into T:\n  return {ex}\n"
        # ... checker.check(PenguParser().parse(src))
```

**Lectura de la matriz:**

1. **`T: Num` acepta `==`, `!=` y `<`.** Pero `LANGUAGE.md:1535` dice que `Par` existe para `==`/`!=`
   y `Ordo` para `<`/`<=`/`>`/`>=`. Si `Num` ya los satisface, `Par` y `Ordo` **en posición de
   único bound no aportan nada**: `T: Par` no habilita nada que `T: Num` no habilite ya.
2. **`T: Num` y `T: Integrum` se comportan idénticamente en la matriz.** La documentación
   (`LANGUAGE.md:1548-1550`) afirma: *"`Integrum` is a strict refinement of `Num`: an `Integrum`
   bound also satisfies `Num` (so `where T: Integrum` allows `+`), but not the other way round — this
   is what makes `%` reject `float`."* El único punto donde la matriz los distingue es `%`, `&`,
   `<<`, que es precisamente el propósito de `Integrum`. Pero `Num` concediendo además `==` y `<`
   significa que la relación no es una cadena de refinamiento sino un conjunto de permisos
   solapados sin lógica declarada.
3. **`T: Par` rechaza `<` y `T: Ordo` rechaza `==`.** Esto sí es coherente con la tabla, pero
   combinado con (1) produce la sorpresa: *añadir* un bound (`Par`) **quita** capacidades
   (`<`). Un usuario que lee "añade `where T: Par` para poder comparar igualdad" descubre que su
   `a < b` ha dejado de compilar.

**Reproducción directa del caso más confuso:**

```bash
$ # T: Num, usa '<'  -> OK
$ # T: Par, usa '<'  -> E0049: Cannot use operator 'lt' on type parameter 'T' without 'Ordo' bound
```

**Impacto:** el sistema de bounds es la feature más distintiva de PenguScript ("concepts como
restricciones compile-time con cero overhead") y su semántica es **no monotónica**: añadir un bound
puede romper código que ya compilaba. Eso es imposible de explicar en la documentación sin
reconocerlo como un bug de diseño.

**Fix propuesto:** decidir una jerarquía única y hacerla cumplir en un solo sitio
(`CONCEPT_IMPLICATIONS` en `pengu_types.py`): si `Num` implica `Par` y `Ordo`, entonces `Par` y
`Ordo` deben implicar `Num` también (retículo, no orden), y la documentación debe reescribirse como
"conjuntos de operadores habilitados" en vez de "refinamiento estricto". Alternativamente, si la
intención era la cadena `Num ⊂ Integrum ⊂ …`, quitar `Par`/`Ordo` del conjunto de capacidades de
`Num` y actualizar los programas de la stdlib que hoy dependen del comportamiento permisivo.

### §3.2 Hallazgo T2 — 🔴 Los tipos cualificados a través de un módulo **re-exportador** pierden los campos

Este es el hallazgo con mayor impacto práctico de toda la auditoría, porque afecta a la cadena
completa de bindings C de la stdlib.

**Reproducción mínima con tres módulos locales:**

```bash
$ mkdir -p /tmp/mod2/src && cd /tmp/mod2
$ cat > pengu.toml <<'EOF'
name="mod2"
version="0.1.0"
entry="src/main.pengu"
EOF
$ cat > src/lib.pengu <<'EOF'
rune Vec:
    x as f32
    y as f32
declare vzero into Vec
EOF
$ cat > src/dep.pengu <<'EOF'
import lib
link "libdep"
declare vadd with a as Vec, b as Vec into Vec
EOF
$ cat > src/main.pengu <<'EOF'
import dep
weave main into int:
    var v as dep.Vec is with x is 1.0, y is 2.0
    return (v.x to int)
EOF
$ pengu check
/tmp/mod2/src/main.pengu:4:13 [E0004] Undefined identifier 'v'      <-- 2º error, consecuencia del 1º
```

Con `--json` se ve el diagnóstico raíz:

```json
{"type":"diagnostic","line":4,"col":33,"code":"E0013",
 "message":"Field 'x' does not exist on Rune 'dep.Vec'",
 "help":"Remove 'x' or add it to rune 'dep.Vec'.",
 "note":"Rune 'dep.Vec' fields are: ."}
```

**El `note` es demoledor: la lista de campos está literalmente vacía (`fields are: .`).**

**Y el mismo programa con el tipo sin cualificar funciona:**

```bash
$ cat > src/main.pengu <<'EOF'
import dep
weave main into int:
    var v as Vec is with x is 1.0, y is 2.0
    return (v.x to int)
EOF
$ pengu check
   Checking mod2 v0.1.0 [debug]
     Clean no errors found in 0.17s
```

**Análisis del código culpable** — `pengu_parser/pengu_infer.py:1463-1478`:

```python
if isinstance(unwrapped_expected, RuneType):
    fields = unwrapped_expected.fields
    if not fields and self.symbols:
        sym_t = self.symbols.lookup_type(unwrapped_expected.name)   # <-- 'dep.Vec'
        if isinstance(sym_t, RuneType) and sym_t.fields:
            fields = sym_t.fields
    for f_name, f_type in field_inits.items():
        if f_name not in fields:
            raise self._make_error(
                SemanticError,
                f"Field '{f_name}' does not exist on Rune '{unwrapped_expected.name}'",
                ...
```

El `RuneType` resuelto para `dep.Vec` tiene `fields == {}` (viene de la declaración remota a través
de la frontera de módulo, sin el cuerpo de la rune), y el fallback que debería arreglarlo hace
`self.symbols.lookup_type(unwrapped_expected.name)` con el nombre **ya cualificado** (`"dep.Vec"`),
que no está en la tabla de símbolos (allí vive `"Vec"`). El fallback **nunca puede acertar** con un
nombre cualificado; solo funciona cuando el nombre ya venía sin cualificar.

**Impacto en la stdlib (crítico):** de los 52 módulos, **25 son bindings `.d.pengu` a C** y varios
re-exportan tipos de otro binding precisamente del modo que rompe el fallback:

| Módulo | Declara | Depende de | Patrón roto |
|--------|---------|-----------|-------------|
| `std/raymath.d.pengu` | `declare Vector2Zero into Vector2` | `import std.raylib` | `raymath.Vector2` → sin campos |
| `std/rlgl.d.pengu` | tipos GL | `import std.raylib` | `rlgl.*` tipos raylib → sin campos |
| `std/rlights.d.pengu` | luces | `import std.raylib` | idem |

Ejemplo real con el `std` real, que es exactamente el bloque 94 de `LANGUAGE.md`:

```bash
$ cat > src/main.pengu <<'EOF'
import std.raylib
import std.raymath
weave main into int:
    var position as raymath.Vector2 is with x is 400.0, y is 225.0
    return (position.x to int)
EOF
$ pengu check
  .../src/main.pengu:4:33 [E0013] Field 'x' does not exist on Rune 'raymath.Vector2'
  .../src/main.pengu:5:13 [E0004] Undefined identifier 'position'
```

**Compárese con la forma que sí funciona** (`raylib.Color`, que se declara en su propio módulo):

```bash
$ cat > src/main.pengu <<'EOF'
import std.raylib
weave main into int:
    var c as raylib.Color is with r is 1, g is 2, b is 3, a is 255
    return (c.r to int)
EOF
$ pengu check
   Checking demo v0.1.0 [debug]
     Clean no errors found in 1.03s
```

**Conclusión:** usar un tipo cualificado de un módulo que a su vez importa su proveedor de tipos
—el patrón *obligatorio* en los bindings C de la stdlib— está roto. El usuario debe aprender a
escribir el nombre sin cualificar, lo que entra en conflicto directo con el propio ejemplo de la
documentación.

**Fix propuesto:** en el fallback, normalizar el nombre antes del lookup
(`unwrapped_expected.name.rsplit(".", 1)[-1]`) **y** propagar el `fields` real en la resolución de
nombres cualificados (que `lookup_type` de un módulo devuelva el `RuneType` con `fields` poblados,
no una copia vacía); añadir un test de regresión con dos módulos en el patrón `dep`/`lib`.

### §3.3 `__auto_type` y TCC — interacción con tipos inferidos

Aunque pertenece a §4/§17, tiene causa en la inferencia: el codegen usa `__auto_type` en el bundle
por defecto para tipos inferidos, y el TCC que el propio proyecto descarga (0.9.28rc) **no soporta
`__auto_type`**, así que todo programa que importe `std` cae al fallback de gcc:

```
$ pengu run h.pengu            # importa std.spark + std.seal
[pengu] development compiler failed; retrying with gcc
   Finished in 6.50s
$ tcc -c h.c -I build/include
/tmp/audit/.:867: error: '__auto_type' undeclared
```

**Fix propuesto:** emitir `__typeof__(expr)` en lugar de `__auto_type` (TCC acepta `typeof`),
manteniendo `__auto_type` solo bajo `--target-compiler msvc` si fuese necesario.

---

## §4. Code Generator (`pengu_codegen.py`)

> **Veredicto:** 🔴 **bloqueante** — el codegen es maduro y produce C limpio en el camino por
> defecto (0 warnings en un programa real de 6601 líneas), pero **la feature estrella de
> portabilidad (`--strict-c99`) está rota** y su gate de CI es un `grep` de texto.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| Todo lo que el checker acepta se emite como C válido | ✅ En el camino por defecto | `atlas.pengu` → 6601 líneas de C, `gcc -std=c11 -Wall -Wextra -Wshadow -fsyntax-only` → **0 warnings** | ✅ |
| El C emitido compila con `gcc -std=c99 -pedantic-errors` | ❌ **No** | 98 errores en el bundle por defecto (statement-expressions GNU) | 🟡 |
| Compila con `clang` | ✅ | `clang -std=c11 -Wall -Wextra -Werror` sobre el runtime → 0 | ✅ |
| Compila con `cl.exe` (MSVC) | ❌ **Imposible hoy** | `--target-compiler msvc` emite `__forceinline`/`__declspec` pero invoca el compilador del host; `build_runtime.py` no tiene rama `cl.exe` y pasa flags GCC-only | 🟠 |
| Compila con `tcc` | ❌ **Falla en programas reales** | `tcc -c h.c` → `error: '__auto_type' undeclared`; el proyecto cae al fallback de gcc | 🟠 |
| `--strict-c99` produce C sin extensiones GNU en **todos** los casos | ❌ **REFUTADO** | Falla con 13 errores duros de gcc y **104** statement-expressions restantes | 🔴 |
| Caché incremental correcta (hash por contenido) | ✅ | `pengu_cache.py:149-168` hashea sha256 de cada módulo + digest del runtime header, versión, flags | ✅ |
| `#line` mapping correcto | 🟡 Parcial | El `#line` apunta al archivo/module correcto pero en el bundle estricto la línea 863 referencia `k` fuera de su bloque, lo que sugiere desajuste entre la línea reportada y la estructura emitida | 🟡 |
| Dead-code elimination (DCE) seguro | 🟡 Parcial | `pengu_dce.py` (10 KB) implementa `is_prunable_module`; el shim raíz re-exporta 4 símbolos. Cubierto por `tests/test_dce_tcc_pch.py` | 🟡 |
| Monomorfización de genéricos correcta | ✅ | `tests/test_codegen_generic_subst.py`; `zip_with_int_int_int` se genera correctamente | ✅ |
| `with:` anidados a cualquier profundidad | ✅ | `tests/test_codegen_with_list.py`; bloques `with:` reales en std | ✅ |
| Ownership de strings (deep-copy en slots) consistente | 🟡 Parcial | El leak de temporales de expresión está **documentado** (`docs/PERFORMANCE.md:349-358`) y fijado con `xfail(strict=True)` | 🟡 |
| Bugs de doble evaluación / efectos secundarios duplicados | ✅ No encontrados en lo auditado | — | 🟢 |
| Statement-expressions `({...})` en `--strict-c99` | ❌ **Quedan 104** | `grep -c '({' atlas_strict.c` → 104 | 🔴 |
| `__auto_type` en `--strict-c99` | ✅ Eliminado | `grep -c __auto_type atlas_strict.c` → 0 (pero es la causa del fallo de TCC en modo normal) | 🟢 |
| Métodos duplicados en `PenguCodegen` | ✅ Ninguno | 170 métodos, nombres únicos | ✅ |
| Función más larga | 🔴 `_translate_expr_impl`: **2605 líneas** | `ast` sobre `pengu_codegen.py` | 🟠 |

### §4.1 Hallazgo C1 — 🔴 `--strict-c99` emite C que no compila

**Evidencia reproducible (programa de 6 líneas que importa `std`):**

```bash
$ pengu build --entry h.pengu --output h_strict.c --strict-c99
   Finished [debug] target(s) in 6.28s -> /tmp/audit/h_strict.c        rc=0

$ gcc -std=c11 -Wall -Wextra -c h_strict.c -I build/include
.:863:31: error: 'k' no se declaró aquí (primer uso en esta función)   # 13 errores duros

$ build/tcc-dist/tcc-dist/bin/tcc -std=c11 -c h_strict.c -I build/include
.:863: error: 'k' undeclared
```

El C generado coloca un *bounds check* hoisteado **fuera** del bloque que declara su operando:

```c
  while ((i < limit)) {                 /* función zip_with_int_int_int */
    int32_t _elem_72 = (i); pengu_list_push(&idxs, &_elem_72); i = (i + 1);
  }
int64_t _p_idx_73 = (int64_t)(k);                       /* k nunca se declara aquí */
pengu_assert_bounds(_p_idx_73, (int64_t)((xs).len), ".:862");
```

La causa está en el *prelude flushing* de `pengu_parser/pengu_codegen.py:4232-4256` (`_hoist` /
`_block_expr`), con sitios sin guardar en `:5853-5855`, `:8707-8709` y `:1339-1358`.

**Y el modo estricto es *peor* que el normal para portabilidad**, porque elimina el wrapper
`__extension__` que silenciaba a GCC pero deja las statement-expressions:

```bash
$ grep -c '({' atlas_strict.c   ->  104     (__extension__: 0, __auto_type: 0, __typeof__: 0)
$ grep -c '({' atlas.c          ->  382
$ gcc -std=c99 -pedantic-errors -Wall -Wextra -fsyntax-only -Ibuild/include atlas_strict.c
rc=1  errors=104          # control no estricto: 98 errores
```

**Por qué el CI está verde (esto es lo grave):**

```python
# tests/test_cli_strict_c99.py:50 — la aserción completa
assert "__extension__" not in bundle
assert "__auto_type" not in bundle
```

…y `tests/test_c99_portability.py` compila únicamente un `_PROG` de ~20 líneas **sin ningún
`import`**. Los 5 tests pasan en 0.76 s, y ninguno compila nunca un bundle estricto que importe
`std`. `RELEASE_CHECKLIST.md:17` lista "C99 portability gate (`--strict-c99`)" como evidencia de
release.

**Impacto:** la única feature de portabilidad C99 del lenguaje está rota para **todo** programa
real. Un usuario que la active en CI obtiene un build que falla en el compilador de C — o peor, un
`pengu build --output x.c --strict-c99` que sale con código 0 y escribe C inválido (verificado:
`--output build/m.c` con `--target-compiler msvc` sale 0 escribiendo C que gcc no compila).

**Fix propuesto:** hacer que `expr_prelude` se vacíe en el *scope* de bloque (o redeclarar el
temporal hoisteado dentro del bloque que lo consume), y añadir a CI una pata que compile y ejecute
`--strict-c99` sobre **todos** `tests/std_programs/*.pengu`.

### §4.2 Hallazgo C2 — `--target-compiler` es una trampa: dialecto sin compilador

`--target-compiler msvc` solo cambia el **dialecto de C emitido** (`set_restrict_keyword` en
`pengu_codegen.py:82-85`; atributos en `:3955`, `:2839-2868`), mientras el compilador invocado sigue
siendo el del host:

```bash
$ pengu build --target-compiler msvc
error: nombre de tipo '__forceinline' desconocido     # de gcc, exit 1

$ pengu build --target-compiler msvc --output build/m.c
   Finished ... -> build/m.c                          # exit 0, C que gcc NO compila
```

Y `--cc cl` construye un juego de flags estilo MSVC (`/W3 /std:c11 /Zi /Od /DDEBUG`) pero deja
`-I`, `-L` y `-o` en estilo GNU en la misma línea de comandos, sin mapear nunca `-o` → `/Fe:`.

**Impacto:** el flag que la documentación presenta como "override de compilador" produce
silenciosamente un dialecto que no corresponde al compilador que realmente se ejecuta. No hay
validación que empareje ambos.

**Fix propuesto:** error (no warning) cuando `target_compiler` no coincida con el dialecto inferido
de `--cc`, y completar el mapeo de flags de `cl.exe` (`/Fe:`, `/I`, `/link`).

### §4.3 Hallazgo C3 — `_translate_expr_impl` de 2605 líneas

```bash
$ .venv/bin/python - <<'EOF'   # AST, funciones >200 líneas
pengu_parser/pengu_codegen.py: 6 funcs >200 lines
    2605  _translate_expr_impl  :6952
     810  _translate_stmt_impl  :4280
     446  generate_derived_implementations  :3372
     286  _translate_for_in  :5229
     228  _collect_top_stmt  :2269
     217  _translate_string_lit  :6010
EOF
```

Por comparación, `pengu_parser/pengu_checker.py` tiene 5 funciones >200 líneas, la peor de 1323
(`_collect_top_level`), y `pengu_infer.py` tiene 2, la peor de **2870** (`infer`). En total:

| Archivo | Funciones >200 líneas | Peor |
|---------|----------------------|------|
| `pengu_codegen.py` (518 KB) | 6 | 2605 |
| `pengu_infer.py` (238 KB) | 2 | 2870 |
| `pengu_checker.py` (380 KB) | 5 | 1323 |
| `pengu_project.py` (228 KB) | 5 | 329 |
| `pengu_lsp/server.py` (69 KB) | **0** | — |

**Impacto:** una función de 2605 líneas es imposible de revisar, imposible de cubrir con tests
granulares, y es donde previsiblemente viven los bugs de hoisting de §4.1. La complejidad
ciclotómica de esa función es necesariamente enorme (no se midió con `radon` porque no está
instalado, pero el tamaño es indicativo).

**Fix propuesto:** extraer `_translate_expr_impl` en ~15 funciones por familia de nodo
(`_expr_call`, `_expr_binary`, `_expr_block_value`, `_expr_container`, …) con un despachador; hacerlo
**después** de arreglar §4.1 para no confundir el refactor con el fix funcional.

### §4.4 Lo que el codegen hace bien (✨ UNDERSELL)

- **0 warnings de C en un programa real.** `gcc -std=c11 -Wall -Wextra -Wshadow -fsyntax-only`
  sobre el bundle de `atlas.pengu` (6601 líneas) da **0 warnings**. La afirmación de `README.md:401`
  ("zero C compiler warnings") es **verdadera** para el bundle emitido, con la salvedad de que **no**
  lo es para la unidad de traducción del runtime (§5.1).
- **`_Static_assert(PENGU_ABI_VERSION == 1, ...)`** emitido en cada bundle y correctamente envuelto
  en `#if __STDC_VERSION__ >= 201112L` para no romper C99.
- **Monomorfización de genéricos correcta y verificable** (`zip_with_int_int_int`).
- **La tabla LALR cacheada + el bundle cacheado** hacen que un `pengu build` en caliente tarde ~875 ms
  en un proyecto de 2000 líneas, con un suelo de ~170 ms de arranque del intérprete. Es un buen
  número para un compilador escrito en Python.

---

## §5. Runtime C (`pengu_runtime.h`, `pengu_runtime.c`, `std_c/`)

> **Veredicto:** 🟠 **con problemas graves** — el header es la pieza más limpia del proyecto
> (compila sin un solo warning), pero el `.c` **no compila sin un flag que oculta 24 errores**,
> y varias afirmaciones de seguridad de la documentación son falsas.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| `pengu_runtime.h` con `gcc -std=c11 -Wall -Wextra -Werror -fsyntax-only` | ✅ **0 errores, 0 warnings** | exit 0 | ✅ |
| `pengu_runtime.h` con `-std=c99 -pedantic-errors` | ✅ 0 errores | exit 0 | ✅ |
| `pengu_runtime.h` con `clang -Weverything` | 🟡 389 warnings, 0 errores | 267 `-Wunsafe-buffer-usage`, 86 `-Wdeclaration-after-statement`, 14 `-Wcast-qual` | 🟢 |
| `pengu_parser/pengu_runtime.c` compila limpiamente | ❌ **No** | Sin `-Wno-implicit-function-declaration`: **24 errores** (`mbedtls_md5/sha1/sha256/sha512` privados) | 🟠 |
| `cl.exe /W4 /WX` | ❌ **Imposible** | `build_runtime.py:92,597` solo conoce gcc/clang/cc; todos los flags son GCC-only | 🟠 |
| `PENGU_ABI_VERSION` congelado y verificado | 🟡 Parcial | Existe (`pengu_runtime.h:58`) y se asserta, pero **no protege contra un `.a` obsoleto** | 🟡 |
| Funciones públicas documentadas | 🟡 208 funciones, **55 (26 %) sin ningún tag** Doxygen | Crash-handler internals, 25 wrappers `pengu_c_f*`, `pengu_c_srand/rand*`, 6 `pengu_c_archivum_*` | 🟡 |
| Ownership claro en funciones que alocan | ✅ | 30 funciones que devuelven contenedores por valor; cada una tiene `pengu_banish_*` o callback `*_cleanup` | ✅ |
| Límites de tamaño (`INT_MAX`, `SIZE_MAX`) protegidos | ✅ | `pengu_string_new:613`, `_concat:872`, `_repeat:1263-1266`, list `:1655`, map `:2144`, `:2495`, file reads `:3592,3605` | ✅ |
| Crash handler async-signal-safe | ❌ **REFUTADO** | `pengu_runtime.h:406-412` usa `snprintf`, que no es async-signal-safe | 🟠 |
| Frame stack thread-safe / thread-local | ✅ **thread-local** (la sospecha del enunciado era falsa) | `:392-398` `__thread`/`__declspec(thread)`/`_Thread_local`. ⚠️ `g_pengu_handler_installed` (`:399`) sí es un `volatile int` global no atómico | 🟡 |
| Callbacks de ownership (`elem_cleanup`, `elem_clone`) consistentes | ✅ | Verificado en mapas y listas | ✅ |
| `tombstones` de mapas implementados | ✅ | `PenguMapEntry.tombstone:2012`; `pengu_map_remove:2342-2349` marca el hueco; inserción reutiliza el primer tombstone | ✅ |
| Floats: `%f` vs `to string` con `%g` | ❌ **Inconsistente y visible** | `pengu_string_from_float:1339` usa `"%g"`; `pengu_string_format_ex:796-798` usa `"%f"` | 🟡 |
| `pengu_runtime.c` raíz (0 bytes) | ❌ Residuo | `git cat-file -s HEAD:pengu_runtime.c` → `0`; nada lo lee | 🟢 |

### §5.1 Hallazgo R1 — 🟠 El `.c` del runtime no compila sin un flag que **oculta** 24 errores

`pengu_parser/pengu_runtime.c:25-28` usa `mbedtls_md5/sha1/sha256/sha512` de
`<mbedtls/private/*.h>`. En mbedtls 4.2.0 esas declaraciones están tras
`#if defined(MBEDTLS_DECLARE_PRIVATE_IDENTIFIERS)`
(`build/include/mbedtls/private/md5.h:42,163`), que `build/include/mbedtls/private_access.h:17,36`
solo define cuando se compila con `MBEDTLS_ALLOW_PRIVATE_ACCESS`. **No se define.**

`build_runtime.py:1195-1204` (y también `:272,436,521,999,1152`) compensa con:

```python
"-Wno-incompatible-pointer-types", "-Wno-implicit-function-declaration",
```

Prueba diferencial con el juego de flags exacto del build:

```
[A] ... -Wno-incompatible-pointer-types -Wno-implicit-function-declaration  -> rc=0, 3 warnings, implicit=0
[C] ... (flag de implicit declaration eliminado)                            -> rc=1, error=24
    pengu_runtime.c:1248:5: error: declaración implícita de la función 'mbedtls_md5'
[D] ... (flag eliminado) + -DMBEDTLS_ALLOW_PRIVATE_ACCESS                    -> rc=0, err=0 (solo los 3 macro-redef)
```

Los 24 diagnósticos están **suprimidos por completo**, no degradados: nunca aparecen en el log de
build. `-Wno-incompatible-pointer-types` hoy es innecesario (0 errores sin él).

El hashing funciona por accidente ABI en x86-64 SysV (`seal.md5("abc")` = `900150983cd24fb0d6963f7d28e17f72`,
idéntico a `md5sum`), pero la unidad de traducción es C99 mal formada y GCC ≥14 convierte las
declaraciones implícitas en error duro. `cl.exe` **rechaza** el flag, lo que hace imposible
cualquier build con MSVC.

**Impacto:** la afirmación implícita "el runtime compila limpiamente" es un artefacto de un flag de
supresión, no un hecho. Y cierra la puerta a MSVC (§15).

**Fix propuesto:** añadir `-DMBEDTLS_ALLOW_PRIVATE_ACCESS` (fix verificado: rc=0, 0 errores) y
eliminar los dos `-Wno-*`.

### §5.2 Hallazgo R2 — ❌ REFUTADO: el crash handler **no** es async-signal-safe

`LANGUAGE.md:3269` afirma: *"**Async-signal-safe** crash handlers for `SIGSEGV` and `SIGABRT`…"*.
`CHANGELOG.md:2780` afirma que vuelca *"de forma async-signal-safe (utilizando exclusivamente
llamadas directas a `write(2)` / `_write`)"*.

**El propio archivo lo desmiente**, en un comentario 5 líneas más arriba de la llamada:

```c
/* pengu_runtime.h:401-412 (comentario + código) */
/* ... no está listado por POSIX como async-signal-safe ... */
pengu_dump_frame_stack(...) {
    ... snprintf(...)   /* <-- snprintf NO es async-signal-safe */
}
```

`write`/`_exit` sí son seguros; el `snprintf` que formatea el buffer **no** lo es (glibc puede tomar
locks y asignar memoria). **Ambas afirmaciones documentales son falsas.**

**Fix propuesto:** formatear sin `snprintf` (hex/decimal manual a un buffer) o eliminar la
afirmación "async-signal-safe" de `LANGUAGE.md` y `CHANGELOG.md`.

### §5.3 Hallazgo R3 — 🟡 Coherencia de floats entre `to string` y la interpolación

```bash
$ pengu run fl.pengu
3.14           # (x to string)
3.140000       # "{x}"        <-- el MISMO valor, distinto texto
0.333333
0.333333
```

`pengu expand fl.pengu | grep format` muestra la causa:

```c
spark_println(pengu_string_format_ex("%f", (double)(x)));
```

`pengu_string_from_float` (`:1339`) usa `"%g"`; `pengu_string_format_ex` (`:796-798`) usa `"%f"`.
Peor: `%f` de `1e300` produce una cadena de 310 caracteres.

**Fix propuesto:** emitir `%g` en la ruta de interpolación de floats, o enrutar ambas por
`pengu_string_from_float`.

### §5.4 Hallazgo R4 — 🟡 El frame stack es thread-local (bien), pero el guard del handler no es atómico

La sospecha del enunciado ("¿la frame stack es thread-safe? ¿es thread-local?") se resuelve
**favorablemente**: `pengu_runtime.h:392-398` usa `__thread` / `__declspec(thread)` / `_Thread_local`.
**📝 REFUTADO** como problema.

Lo que sí queda: `g_pengu_handler_installed` (`:399`) es `static volatile int`, escrito en
`:459-460` desde `pengu_install_crash_handler()`, que `pengu_frame_push` (`:471`) llama en **cada**
frame empujado. Dos hilos compitiendo por ese `int` es una *data race* según C11 (`volatile` no es
un primitivo de sincronización), y además es un coste por frame.

**Fix propuesto:** instalar una sola vez con `call_once`/atómico, o mover la instalación a
`pengu_main`.

### §5.5 Hallazgo R5 — Cobertura de señales incompleta

`pengu_runtime.h:464-465` captura solo `SIGSEGV` y `SIGABRT`, y con `signal()` en vez de `sigaction`.
`SIGFPE` (división entera por cero bajo `-ftrapv`), `SIGILL` y `SIGBUS` no producen volcado de
frames. En Windows solo hay `SetUnhandledExceptionFilter` (`:462`).

Esto se conecta con un síntoma observado en el CLI:

```bash
$ pengu eval "1/0"
(sin salida)     exit 248    # = sys.exit(-8) => SIGFPE propagado sin mensaje
```

**Fix propuesto:** `sigaction` + añadir `SIGFPE`/`SIGILL`/`SIGBUS`, y mapear códigos de retorno
negativos del hijo a `128+señal` con un mensaje legible.

### §5.6 Hallazgo R6 — 🟡 El assert de ABI no protege contra un `.a` obsoleto

`pengu_runtime.h:58` define `PENGU_ABI_VERSION 1` y `pengu_codegen.py:32,458,9854` emite
`_Static_assert(PENGU_ABI_VERSION == 1, ...)` en el bundle. Pero el assert compara la **constante
del codegen** con la **macro del header en el `-I`**: solo detecta desincronización
codegen↔header. El archivo `libpengu_runtime.a` no exporta ningún símbolo de versión:

```bash
$ nm build/lib/libpengu_runtime.a | grep -i abi
(vacío)
```

`SECURITY.md:76-78` afirma: *"a stale `libpengu_runtime.a` fails at compile time instead of
corrupting memory"*. **❌ REFUTADO:** un `.a` obsoleto junto a un header que sí coincide pasa el
assert en silencio.

**Fix propuesto:** definir `int pengu_abi_version(void)` en `pengu_parser/pengu_runtime.c` y
referenciarlo desde el bundle, convirtiendo la comprobación en *link-time*.

### §5.7 Lo que el runtime hace bien (✨ UNDERSELL)

Este header de 156 KB / 208 funciones merece reconocimiento explícito:

- **Compila sin un solo warning** con `-Wall -Wextra -Werror` en gcc y clang, y también bajo
  `-std=c99 -pedantic-errors`. Es, con diferencia, el artefacto más disciplinado del repositorio.
- **Tombstones en mapas implementados de verdad**, con reutilización del primer hueco en inserción y
  continuación de sondeo más allá de tombstones en 6 sitios (`:2187,2261,2309,2531,2570,2602`).
  Muchas implementaciones de hash map en proyectos beta omiten esto.
- **Guards de tamaño sistemáticos**: `INT_MAX` rechazado en `pengu_string_new`, `_concat`,
  `pengu_string_from_int`; `SIZE_MAX / times` en `_repeat`; crecimiento de listas y mapas acotado.
  No se encontró ninguna truncación silenciosa de `int`.
- **Todo lo que aloca tiene su `banish`**: 30 funciones que devuelven contenedores por valor, cada
  una con su `pengu_banish_string/_list/_map` o callbacks `*_cleanup`, y `pengu_banish_string` está
  correctamente guardado por `s->is_owned` (`:950`).
- **La documentación de `pengu_banish_string` es más severa que el código**:
  `pengu_runtime.h:939-944` dice "NEVER call `pengu_banish_string` on `pengu_string_from_cstr`", pero
  la implementación (`:946-957`) comprueba `is_owned` y es segura para views. **✨ UNDERSELL** — la
  doc asusta más de lo necesario.

---

## §6. CLI (`pengu_project.py` y sus submódulos)

> **Veredicto:** 🔴 **bloqueante** — el CLI es **mucho más rico de lo que la documentación sugiere**
> (25 subcomandos, no 13), y casi todos funcionan. Pero contiene cuatro defectos bloqueantes, dos de
> ellos con pérdida de datos o falsos verdes.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| Todos los subcomandos del manual funcionan | ✅ **25 subcomandos** | `init add remove upgrade tree metadata verify vendor build run doctor gc expand time eval watch test check update bind fmt clean lsp doc assets` | ✅ |
| Subcomandos que el enunciado creía ausentes | ✅ Todos existen | `doctor`, `gc`, `expand`, `time`, `eval`, `watch` — todos funcionan (❌ REFUTADO el enunciado) | ✅ |
| `pengu check <archivo>` valida el archivo | ❌ **No: lo ignora** | `pengu check std/nonexistent_zzz.pengu` → "Clean no errors found", rc=0 | 🔴 |
| Entry inexistente produce error | ❌ **No** | `check_sources_diagnostics` devuelve `ok=True` cuando `os.path.isfile(entry_abs)` es falso | 🔴 |
| Flags desconocidos rechazados | ❌ **No** | `args, unknown = parser.parse_known_args()`; `unknown` nunca se inspecciona | 🔴 |
| `pengu fmt --indent N` preserva el fuente | ❌ **Corrompe** | `--indent 4` colapsa la indentación a columna 0; exit 0 | 🔴 |
| Mensajes de error útiles | 🟡 En `build`/`check` sí; en el camino de script no | `pengu run nonexistent.pengu` → traceback de Python con `FileNotFoundError` | 🟠 |
| `--verbose` reporta lo que dice | ✅ Honesto | Imprime módulos, defines, comando C completo y timings | ✅ |
| `--json` machine-readable consistente | 🟡 `check`/`build` sí; `test` no | `pengu test --json` con error de compilación emite **0 líneas JSON** y un traceback | 🟠 |
| `--target-compiler` mapea gcc/clang/msvc/tcc | ❌ Mapea solo el dialecto | Ver §4.2; `tcc` solo funciona por ruta absoluta | 🟠 |
| `--target` cross-compilation Linux⇄Windows | 🟡 Real pero NO VERIFICADO | `resolve_compiler` sonda `<triple>-gcc` y falla con mensaje claro; no hay mingw en el host | 🟡 |
| `--strict-c99` no rompe nada | ❌ **Rompe todo** | Ver §4.1 | 🔴 |
| Caché de scripts invalida correctamente | ✅ **REFUTADO** el enunciado: sí incluye versión y flags | `pengu_project.py:4267,4282-4284`; `pengu_cache.py:149-168` hashea contenido sha256 | ✅ |
| `doctor`, `gc`, `expand`, `time`, `eval`, `watch` | ✅ Funcionan | `gc --all --verbose` eliminó 169 scripts cacheados; `time` da tabla por fases | ✅ |
| `--quiet` suprime el banner | ❌ **No-op** | `pengu --quiet build` imprime el banner completo; `quiet` solo se propaga en la ruta `run` | 🟠 |
| `--no-color` / `NO_COLOR=1` desactiva ANSI | ❌ **No-op** | `pengu --no-color check \| cat -v` → `^[[1;36m`; el único sitio que menciona `NO_COLOR` lo **escribe**, nadie lo lee | 🟠 |
| `cl.exe` recibe flags válidos | ❌ No | Mezcla `/W3 /std:c11 /Zi` con `-I… -L… -o` GNU; nunca emite `/Fe:` | 🟡 |
| Duplicación `pengu_bind.py` vs `pengu_project.py` | 🟡 2º CLI completo sin usar | `pengu_bind.py:1567-1617` tiene su propio `main()` + argparse de 14 flags | 🟡 |
| Import circular `pengu_project` ↔ `pengu_bind` | ✅ **No hay** | `grep pengu_project pengu_bind.py` → 0; el import es local y perezoso | ✅ |
| `pengu eval` con crash de runtime | ❌ Sin mensaje | `pengu eval "1/0"` → sin salida, exit 248 | 🟡 |

### §6.1 Matriz real de subcomandos (todos ejecutados)

| Subcomando | Existe | rc | ¿Funciona? | Evidencia |
|---|---|---|---|---|
| `init` | ✅ | 0 | ✅ | `Created exe project 'demo'`; escribe `pengu.toml` + `src/main.pengu` |
| `add` | ✅ | 0 | ✅ (dir local) | `Added dependency 'mybind' to …/lib/mybind` — 🟡 git URL NO VERIFICADO |
| `remove` | ✅ | 1 | ✅ error limpio | `dependency 'nonexistent' is not installed` |
| `upgrade` | ✅ | 1 | ✅ error limpio | idem |
| `tree` | ✅ | 0 | ✅ | `demo v0.1.0 └── mybind *` |
| `metadata` | ✅ | 0 | ✅ | JSON pretty con array de deps |
| `verify` | ✅ | 1 | ✅ | `no pengu.lock found; run pengu build first.` |
| `vendor` | ✅ | 0 | ✅ | `Vendored 0 dependency(ies) into …/vendor` |
| `build` | ✅ | 0 | ✅ | `Finished [debug] target(s) in 0.61s -> build/demo` |
| `run` | ✅ | 0 | ✅ | proyecto y script suelto |
| `doctor` | ✅ | 0 | ✅ | version/python/platform/cc/tcc/pch/runtime/std/cache |
| `gc` | ✅ | 0 | ✅ | `--all --verbose` → 169 scripts eliminados |
| `expand` | ✅ | 0 | ✅ | emite `bundle.c` con `int main(int argc, char** argv)` |
| `time` | ✅ | 0 | ✅ | resolve 174.4 ms, cgen 1.2 ms, cc 60.8 ms, run 12.8 ms |
| `eval` | ✅ | 0/1 | ⚠️ parcial | `eval "1 + 2"` → `3`; `eval "1 +"` → traceback crudo |
| `watch` | ✅ | n/a | ✅ | `v1` → `Change detected, rebuilding` → `v2` |
| `test` | ✅ | 0 | ✅ pero `--json` roto | — |
| `check` | ✅ | 0 | ❌ **ignora posicionales** | ver §6.2 |
| `update` | ✅ | 0 | ✅ | `no dependencies configured.` |
| `bind` | ✅ | 0 | ✅ | header → `insignia mb_` + `declare mybind_add …` |
| `fmt` | ✅ | 0/2 | ⚠️ **destructivo** | ver §6.3 |
| `clean` | ✅ | 0 | ✅ | `Cleaned build directory` |
| `lsp` | ✅ | 0 | ✅ | JSON-RPC por stdio; `--tcp --port 2091` acepta conexión |
| `doc` | ✅ | 0 | ✅ | `Generated 1 module page(s)` + index.md/html |
| `assets` | ✅ | 0 | ✅ | `--list` + generate |

**Ausentes** (todos exit 2, `invalid choice`): `migrate new repl benchmark deps publish package install
search login config explain bench profile lint analyze`.

### §6.2 Hallazgo L1 — 🔴 `pengu check <archivo>` **ignora el archivo** y reporta "Clean"

Este es el hallazgo más grave del CLI y fue **descubierto de forma independiente** por dos
auditorías distintas (la del CLI/LSP y la de la stdlib), lo que elimina cualquier duda.

**Evidencia:**

```bash
$ pengu check std/nonexistent_zzz.pengu
   Checking pengu_app v0.1.0 [debug]
     Clean no errors found in 0.14s
rc=0
```

Un archivo **que no existe** produce "Clean". La causa es doble:

**(a)** El subparser `check` (`pengu_project.py:4745`) **no declara ningún argumento posicional**:

```python
check_p = subparsers.add_parser("check", help="Parse and type-check every module without generating code (CI)")
check_p.add_argument("--profile", "-p", default="debug", ...)
check_p.add_argument("--config", "-c", default=None, ...)
check_p.add_argument("--entry", "-e", default=None, ...)
# ... ningún add_argument("paths", nargs="*")
```

y `main()` usa `parser.parse_known_args()` (`:4881`), así que la ruta pasada cae en `unknown` y se
**descarta sin aviso**.

**(b)** Aunque se llegase a `check_project`, cuando el entry no existe
`check_sources_diagnostics` (`:1272`) hace:

```python
if os.path.isfile(entry_abs):
    ... # resuelve imports y luego chequea
else:
    module_order = [entry_abs]     # <-- y sigue como si nada
```

…devolviendo `ok=True` sin haber validado nada. Con `pengu.toml` ausente, `ProjectConfig.load(None)`
usa `entry = 'src/main.pengu'` por defecto, así que `pengu check` en un directorio cualquiera
responde "Clean".

**Control negativo (el checker SÍ funciona cuando el entry existe):**

```bash
$ cat > /tmp/proj1/src/main.pengu <<'EOF'
weave main:
  var x as int is undefined_thing
EOF
$ pengu check -c /tmp/proj1
  /tmp/proj1/src/main.pengu:2:19 [E0004] Undefined identifier 'undefined_thing'
   Errors found in 0.18s   rc=1
```

**Impacto:** cualquier CI que use `pengu check src/**/*.pengu` (la forma que la documentación y el
sentido común sugieren) obtiene un **verde permanente**, incluso con errores de sintaxis. Esto es
peor que no tener comando de check, porque crea confianza falsa. Afecta también a la auditoría
misma: las 52 ejecuciones de `pengu check std/<mod>.pengu` del procedimiento sugerido dan falso
verde; repetidas con `--entry` dan 52/52 correctos.

**Fix propuesto:** añadir `check_p.add_argument("files", nargs="*")` (y lo mismo en `test`), hacer
que `check_project` chequee los archivos dados, y que `check_sources_diagnostics` **falle** cuando el
entry no existe en lugar de devolver `ok=True`.

### §6.3 Hallazgo L2 — 🔴 `pengu fmt --indent N` corrompe el fuente silenciosamente

`pengu_lsp/formatting.py:234` (y `:251`) hace:

```python
indent_level = leading_spaces // tab_size
```

Es decir: **decodifica** la indentación del fuente usando el **`tab_size` de destino**. Si el fuente
usa 2 espacios y se pide `--indent 4`, cada nivel se calcula como `2 // 4 == 0`, y la estructura
colapsa.

**Evidencia:**

```bash
$ printf 'weave main into int:\n  var x as int is 5\n  if x > 0:\n    return x\n  return 0\n' \
    | pengu fmt --stdin --indent 4
weave main into int:
var x as int is 5
if x > 0:
return x
return 0
```

Y el resultado ya no compila:

```bash
$ pengu check   # sobre el archivo formateado
[E0000] Syntax error: unexpected 'var' at line 2, column 1
```

**El exit code es 0.** `--indent 8` aplana todo el archivo. Como PenguScript es sensible a la
indentación, esto **cambia el significado del programa** (o lo destruye) sin avisar.

**Impacto:** pérdida de datos del usuario en un flag documentado, con exit code de éxito. Es el peor
tipo de bug de una herramienta de formato.

**Fix propuesto:** detectar la unidad de indentación del fuente (mcd de los incrementos de espacios
iniciales) y reescalar sobre ella, en vez de dividir por el `tab_size` de destino; y añadir un test
que formatee con `--indent 4` un fuente de 2 espacios y verifique que `pengu check` sigue limpio.

### §6.4 Hallazgo L3 — 🔴 `parse_known_args()` descarta flags en silencio

```python
# pengu_project.py:4881
args, unknown = parser.parse_known_args()
# 'unknown' nunca se inspecciona
```

**Evidencia:**

```bash
$ pengu check --bogus      -> exit 0, "Clean no errors found"
$ pengu run --bogus        -> ejecuta el programa
$ pengu --bogus2           -> imprime usage, exit 0
```

**Impacto:** un typo en un flag de CI (`--strict-c99` → `--strictc99`, `--frozen` → `--frozem`)
produce un build **verde** sin ninguna de las garantías pedidas. Combinado con §6.2, un CI puede
estar ejecutando comandos que no hacen nada durante meses.

**Fix propuesto:** `parser.error(f"unrecognized arguments: {' '.join(unknown)}")` cuando `unknown`
no esté vacío, manteniendo una allow-list estrecha para `pengu run script -- args`.

### §6.5 Hallazgo L4 — 🟠 `pengu test --json` rompe el contrato machine-readable

`check --json` y `build --json` emiten **JSON Lines** correctamente, incluso en fallo:

```json
{"type": "diagnostic", "file": ".../src/main.pengu", "line": 2, "col": 11, "code": "E0004", "severity": "error", "message": "Undefined function 'undefined_fn'", "help": "...", "note": "..."}
{"type": "summary", "ok": false, "errors": 1, "warnings": 0, "duration_ms": 168.63}
```

`pengu test --json` con un error de compilación emite **cero líneas JSON** y un traceback de
`UndefinedIdentifierError`. Además `metadata`/`tree --json` emiten JSON *pretty* multi-línea (no JSON
Lines), y `pengu run` acepta y **ignora** `--json`.

**Fix propuesto:** enrutar `test_project` por el mismo reporter de errores→JSON Lines que
`build`/`check`, y unificar el formato de `metadata`/`tree`.

### §6.6 Hallazgo L5 — 🟠 Dos flags globales documentados son no-ops

```bash
$ pengu --no-color check | cat -v
^[[1;36m   Checking^[[0m pengu_app v0.1.0 [debug]

$ NO_COLOR=1 pengu check | cat -v
^[[1;36m   Checking^[[0m pengu_app v0.1.0 [debug]

$ pengu --quiet build
   Compiling pengu_app v0.1.0 (exe) [debug]
   Finished [debug] target(s) in 0.61s
```

`pengu_project.py:4882-4883` es el **único** sitio que menciona `NO_COLOR`, y lo **escribe** en el
entorno; ningún sitio lo lee. Hay ~77 `print` con `\033[1;…` hardcodeado. `quiet` solo se propaga en
la ruta de `run` (`:4992`).

La ayuda (`:4538-4541`) promete:
```
-q, --quiet      Suppress progress output
--no-color       Disable ANSI colours (also honoured: NO_COLOR=1)
```

**Ambas promesas son falsas.** **❌ REFUTADO.**

**Fix propuesto:** un helper `style()` que consulte `NO_COLOR`/`--no-color`, y pasar `quiet` por
todos los sitios de impresión.

### §6.7 Hallazgo L6 — 🟠 El camino de "script" no formatea errores

`build` y `check` capturan `PenguError` y lo imprimen con el reporter Rust-style. Las rutas de
script/eval/expand/time/watch **no**:

```bash
$ pengu run nonexistent.pengu
FileNotFoundError: Script not found: nonexistent.pengu

$ pengu eval "1 +"
pengu_parser.pengu_errors.ParseError: [line 4, col 23] Syntax error: ...

$ pengu eval "x"
UndefinedIdentifierError: ...

$ pengu expand build/looptest.pengu
ParseError: ...
```

**Fix propuesto:** envolver los entry points de script en el mismo `except PenguError` que usa
`build`.

### §6.8 Hallazgo L7 — 🟡 `--cc tcc` no encuentra el TCC que el propio proyecto descarga

`doctor` y `pick_dev_compiler` localizan el tcc incluido en
`build/tcc-dist/tcc-dist/bin/tcc`, y `pengu run <script>` lo usa. Pero `--cc tcc` hace un `exec` a
secas sobre `PATH`:

```bash
$ pengu build --cc tcc
Could not execute: [Errno 2] No such file or directory: 'tcc'      # exit 1
$ pengu build --cc /home/…/build/tcc-dist/tcc-dist/bin/tcc
   Finished ...                                                     # funciona
```

**Fix propuesto:** resolver `cc` a través de `pengu_tcc.find_tcc()`/`shutil.which` antes de `exec`.

### §6.9 Lo que el CLI hace bien (✨ UNDERSELL)

El enunciado del encargo enumeraba 13 subcomandos y sugería que `doctor`/`gc`/`expand`/`time`/`eval`/
`watch` podrían faltar. **Los 25 existen y funcionan**, incluyendo `remove`, `upgrade`, `tree`,
`metadata`, `verify` y `vendor` que el enunciado ni mencionaba:

- **`pengu time`** da una tabla de fases real (resolve/parse+check/codegen/cc/run) — una herramienta
  de profiling que muchos lenguajes en 1.0 no tienen.
- **`pengu expand`** emite el C intermedio, imprescindible para depurar y para auditar.
- **`pengu doctor`** reporta versión, Python, plataforma, cc, tcc, pch, runtime, std y cache.
- **`pengu gc`** gestiona la caché de scripts con `--max-age`/`--all`.
- **`--verbose` es honesto**: imprime la línea de comandos completa del compilador de C.
- **`--target` cross-compilation es código real**, no un stub: `resolve_compiler` sondea
  `<triple>-gcc`, `i686-w64-mingw32-gcc`, `x86_64-w64-mingw32-gcc` y `mingw32-gcc`, y falla con un
  mensaje accionable (`Install one (e.g. 'apt install mingw-w64')`).
- **La caché de scripts es content-hash correcta** e incluye versión, `strict-c99`, `target`,
  `triple`, `dce`, `release-unsafe`, `PENGU_CFLAGS` y el digest del runtime header. **La sospecha
  del enunciado de que le faltaba la versión es ❌ REFUTADA.**
- **Sin import circular** entre `pengu_project` y `pengu_bind`.

---

## §7. LSP (`pengu_lsp/`)

> **Veredicto:** 🟠 **con problemas graves** — funcionalmente es el subsistema **mejor construido**
> del repositorio (13 de 16 features LSP 3.17 reales, sin un solo `TODO`/`FIXME`, validación
> debounced off-loop, hover excepcional). Los problemas son dos bugs de corrección con impacto
> semántico (rename global textual, URIs fantasma) y varios casos de código muerto.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| Rename 100 % semántico | ❌ **Solo para locales** | Global: `_identifier_occurrences(text, clean_old)` sin `symbols`/`sym` → `_belongs()` devuelve `True` siempre (`server.py:898-900`, llamadas en `:1290`/`:1294`) | 🟠 |
| References semánticos | ✅ | `server.py:990`, con `lookup_at` por ámbito | ✅ |
| documentHighlight semántico | ✅ | `server.py:1173`, distingue Read/Write | ✅ |
| Completion en todos los contextos | ✅ Amplio | `completions.py:619`: judge/`when`/anotación de tipo/import/rune-with-block/miembro de módulo/snippets. ⚠️ sin trigger de `:` | 🟢 |
| Hover con tipos, docs y sizes | ✅ **Excepcional** | Ver §7.5 | ✨ |
| Code actions: missing imports | ✅ | `add_missing_import_action` conectada (`server.py:1059-1089`) | ✅ |
| Code actions: organize imports | ❌ **Código muerto** | `code_actions.py:396` implementa `organize_imports_action`; **0 call sites** | 🟠 |
| Code actions: implement concept methods | ✅ | `implement_concept_methods_action` conectada | ✅ |
| Semantic tokens completos | 🟡 Full sí, range/delta no | `server.py:1614`; leyenda de 23 tipos + 10 modificadores | 🟡 |
| Inlay hints | ✅ | `server.py:1687`: tipo inferido tras `var`/`let` sin anotar; nombres de parámetro | ✅ |
| Code lens | ❌ **Inerte** | `server.py:1768` emite `Command(command="pengu.runTest")`; **no existe** `@server.command("pengu.runTest")`; `executeCommandProvider.commands == []` | 🟠 |
| Signature help | ✅ | `server.py:1091`, triggers `(`, `,`, ` ` | ✅ |
| Document symbols | ✅ | `server.py:1350`; verificado en archivo de 2024 líneas | ✅ |
| Folding ranges | ✅ | `server.py:1450` | ✅ |
| On-type formatting | ✅ | `server.py:1801`, solo edita espacios iniciales | ✅ |
| Workspace symbols | ❌ **Ausente** | No hay `workspaceSymbolProvider` en el dict de capacidades | 🟡 |
| Go to definition | 🟡 Funciona con URIs fantasma en buffers sin guardar | ver §7.2 | 🟠 |
| Go to implementation | ✅ | `server.py:774` devolvió un `Location` | ✅ |
| Prepare rename | ❌ Ausente | No hay `prepareProvider` | 🟢 |
| Pull diagnostics (`textDocument/diagnostic`) | ❌ Solo push | `server.py:484`, `:519` | 🟢 |
| Estabilidad en documentos grandes | ✅ **Excelente** | 2024 líneas: 13/13 peticiones respondidas, `err=False` en todas, sin crash | ✅ |
| Debounce y validación off-loop | ✅ **Ambos correctos** | `VALIDATION_DEBOUNCE_S = 0.35` (`:201`); `run_in_executor` en `:548`; caché por sha1 en `:226` | ✅ |
| `TODO`/`FIXME`/`NotImplemented` en `pengu_lsp/` | ✅ **Cero** | 0 matches en todo el paquete | ✅ |
| Logging de depuración en camino caliente | 🟡 `server.py:252` | `print(f"[LSP] Publishing {len(diagnostics)} diagnostics…", file=sys.stderr)` en cada validación | 🟡 |
| Versión en el docstring | 📝 `pengu_lsp/__init__.py:1` | `"""PenguScript v0.6 Language Server Protocol Package."""` con VERSION=0.16.0 | 📝 |

### §7.1 Hallazgo LS1 — 🟠 Rename **global** es textual y reescribe locales homónimos

**Evidencia (contra la función real, con `symbols=None` que es exactamente lo que pasa en la ruta
global):**

```
with symbols=None (la ruta de rename GLOBAL, server.py:1290/1294):
   line 0 col 6 'weave helper into int:'
   line 4 col 6 '  var helper as int is 2'      <-- LOCAL no relacionado
   line 5 col 9 '  return helper'               <-- LOCAL no relacionado
```

La ruta global (`server.py:1281-1292`) llama:

```python
_edits(_identifier_occurrences(text, clean_old))    # sin symbols ni sym
```

y `_belongs()` (`server.py:898-902`) hace *short-circuit*:

```python
def _belongs(...):
    if symbols is None or sym is None:
        return True          # <-- 898-900
    return symbols.lookup_at(name, line1) is sym
```

**Impacto:** renombrar una función global **también reescribe una variable local que la sombrea**.
Es una edición que cambia la semántica sin que el usuario lo pida — el peor tipo de bug en un
rename. El docstring afirma que las ocurrencias "are always rewritten … when their declaration is
unambiguous", pero una declaración no ambigua no hace que las **ocurrencias** lo sean.

**Fix propuesto:** para el rename global, resolver cada ocurrencia candidata a través de la tabla de
símbolos **de su propio archivo** antes de emitir la edición, o rechazar el rename global cuando
exista un homónimo en ámbito local.

### §7.2 Hallazgo LS2 — 🟠 Go to definition navega a archivos fantasma

`server.py:403-420` (y `:469-471`) materializa los buffers sin guardar como
`.pengu_lsp_shadow_<rand>.pengu`, pasa esa ruta como `filename` a `checker.check` (así que las
declaraciones de símbolos llevan la ruta shadow), y luego hace `os.unlink` en el `finally`.

**Evidencia en vivo:**

```json
"textDocument/definition"
-> "uri": "file:///tmp/paudit/demo/lsptest/.pengu_lsp_shadow_97mf98l8.pengu"
```

El archivo ya no existe en disco cuando el cliente recibe la respuesta (el `unlink` corre antes).

**Impacto:** "ir a definición" en un archivo nuevo o sin guardar lleva al editor a un archivo
inexistente. En VS Code esto se manifiesta como un salto fallido o un archivo vacío.

**Fix propuesto:** reescribir las ubicaciones declaradas desde la ruta shadow a la URI real del
buffer antes de devolver los `Location`.

### §7.3 Hallazgo LS3 — 🟠 El único code lens es inerte

`server.py:1790` emite:

```python
Command(title="▶ Run test: …", command="pengu.runTest")
```

Pero `grep -rn '@server.command' pengu_lsp/` no encuentra ningún `pengu.runTest`, y las capacidades
anuncian `"executeCommandProvider": {"commands": []}`. **Hacer clic en el lens no hace nada en
ningún editor.**

**Fix propuesto:** registrar `@server.command("pengu.runTest")` (y añadirlo a
`executeCommandProvider.commands`), o eliminar el lens.

### §7.4 Hallazgo LS4 — 🟠 "Organize imports" es código muerto

`pengu_lsp/code_actions.py:396` define `organize_imports_action(uri, source)` completamente
implementada con `CodeActionKind.SourceOrganizeImports` y título "Organize imports". El handler
`code_action` (`server.py:1059-1089`) conecta solo tres acciones: `add_missing_import_action`,
`remove_unused_variable_action`, `implement_concept_methods_action`. **Cero call sites** para
organize imports.

**Fix propuesto:** añadirla al handler cuando el `context.only` permita
`source.organizeImports`.

### §7.5 ✨ UNDERSELL — el hover es de nivel producción

Salida real del servidor:

```
weave add with a as int /* 32 bits / 4 bytes */, b as int /* 32 bits / 4 bytes */ into int /* 32 bits / 4 bytes */
*(inline function)*
Adds two numbers.
Returns the sum.

rune Point (64 bits / 8 bytes):
  x as int  // 32 bits / 4 bytes
  y as int  // 32 bits / 4 bytes
**Composite Struct Type** (Total size: 64 bits / 8 bytes)
```

Muestra firma completa, marcas de `inline`, docstring `##`, **tamaño en bits y bytes por parámetro**
y tamaño total de la rune. Ninguna de las auditorías previas lo menciona, y la documentación tampoco.
Es una feature que vendería el lenguaje por sí sola.

### §7.6 ✨ UNDERSELL — arquitectura de validación correcta

- **`change: 2` (incremental) es real.** Se aplicó una edición por rango
  (`{"start":{"line":2,"character":9},"end":{"line":2,"character":10}}`) y el servidor publicó
  exactamente `(1, "[E0004] Undefined identifier 'y'…")`.
- **El debounce es de 0.35 s** y la pasada cara corre **fuera del event loop** con
  `run_in_executor`, con caché por hash de contenido sha1. Es la arquitectura que se le pide a un
  LSP de producción y está implementada, no esbozada.
- **Estabilidad medida**: en un documento de 2024 líneas, 13 peticiones LSP distintas respondieron
  todas sin error (`semanticTokens` 146 641 B, `documentSymbol` 97 246 B, `completion` 52 105 B,
  `foldingRange` 22 012 B).
- **Cero marcadores de deuda** (`TODO`/`FIXME`/`XXX`/`HACK`/`NotImplemented`) en los 4 144 líneas
  del paquete. Los únicos `pass` están en `except` estrechos, ninguno oculta una feature entera.

---

## §8. Standard Library (`std/`)

> **Veredicto:** 🟡 **parcial** — los 52 módulos pasan `check` con **0 errores** y hay 174 tests en
> verde. El problema no es la corrección bruta sino la **higiene de API**, las **duplicaciones
> cruzadas** y un **bug de corrección real** en `seal`.

> **⚠️ Nota metodológica crítica:** el procedimiento sugerido en el encargo
> (`for f in std/*.pengu; do pengu check "$f"; done`) **produce falso verde en el 100 % de los
> casos**, porque `pengu check` ignora los argumentos posicionales (ver §6.2). Repetido con
> `pengu check --entry std/<mod>.pengu` el resultado real es 52/52 sin errores. Cualquier auditoría
> que use la forma del enunciado concluirá erróneamente que todo está bien.

### §8.1 Inventario verificado

| Métrica | Valor verificado | Cómo |
|---------|------------------|------|
| Módulos totales | **52** | `ls std/*.pengu \| wc -l` |
| PenguScript puro | **27** | `ls std/*.pengu \| grep -v '\.d\.pengu' \| wc -l` |
| Bindings `.d.pengu` | **25** | idem |
| ¿Coincide con la reivindicación "27 pure + 25 bindings"? | ✅ **CONFIRMADO** | — |
| LOC puros | 20 432 | `wc -l` |
| LOC bindings | 15 478 | `wc -l` |
| LOC total | 35 910 | `wc -l` |
| Módulo más grande (binding) | `sqlite3.d.pengu` 9 043 | — |
| Módulo más grande (puro) | `oracle.pengu` 1 500 | — |
| `check --entry` | **52/52 rc=0, 0 errores** | sweep completa |
| Warnings propios | **50** (29× W0005 + 21× W0001) | +2 intermitentes según entry point |
| Tests std | 174 recogidos, **0 fallos**, 3 skips de entorno | `test_std_*.py` + `test_stdlib.py` + `test_ffi_libs.py` |
| Módulos `<MOD>_VERSION` (puros) | **27/27** | — |
| Bindings `<MOD>_VERSION` | **6/25** (19 sin constante) | `imago`, `miniaudio`, `raygui`, `raylib`, `sqlite3`, `typis` sí |
| Nombres públicos nunca mencionados en docs | **541/1463 = 37 %** | cruce con LANGUAGE+CHEATSHEET+README |
| `import std.` en `benches/` | **0** | cero cobertura de benchmarks sobre la stdlib |

### §8.2 Tabla por módulo

`check` = errores con `--entry`; `w` = warnings propios; `docs%` = % de `weave` públicos con
comentario `#`/`##` inmediatamente anterior.

| Módulo | Tier | LOC | check | VERSION | docs% | Probado | Notas |
|--------|------|-----|-------|---------|-------|---------|-------|
| spark | T0 | 317 | ✅ 0e/0w | ✅ | 100 % | ✅ | versiones obsoletas, test vacuo (F6) |
| scrolls | T0 | 1490 | ✅ 0e/0w | ✅ | 52 % | ✅ | 66 weaves públicos sin doc inline |
| archivum | T0 | 580 | ✅ 0e/1w | ✅ | 100 % | ✅ | W0005 `last`@533 |
| ffi | T0 | 340 | ✅ 0e/13w | ✅ | 100 % | ✅ | 13× W0001, 3 con mismatch real (F2) |
| tally | T1 | 1474 | ✅ 0e/1w | ✅ | 100 % | ✅ | +2 W0005 si se importa |
| atlas | T1 | 1498 | ✅ 0e/0w | ✅ | **32 %** | ✅ | 135 weaves sin doc; 200 decl. → 161 nombres |
| coven | T1 | 505 | ✅ 0e/0w | ✅ | 100 % | ✅ | limpio |
| loom | T1 | 1496 | ✅ 0e/**21w** | ✅ | 100 % | ✅ | 21× W0005 `exp` en bloques `test` |
| oracle | T1 | 1500 | ✅ 0e/0w | ✅ | 100 % | ✅ | 71 % de su API nunca nombrada en docs |
| compass | T2 | 1028 | ✅ 0e/0w | ✅ | 100 % | ✅ | 32/89 weaves son helpers `cp_*` internos |
| chronicle | T2 | 634 | ✅ 0e/0w | ✅ | 100 % | ✅ | `days_in_month` sin validar m∈[1,12] |
| rites | T2 | 829 | ✅ 0e/0w | ✅ | 100 % | ✅ | limpio |
| filum | T2 | 819 | ✅ 0e/8w | ✅ | 100 % | ✅ | 8× W0001 transmute ptr→opaque |
| whisper | T2 | 419 | ✅ 0e/0w | ✅ | 100 % | ✅ | limpio |
| cipher | T3 | 1238 | ✅ 0e/0w | ✅ | 100 % | ✅ | base64 acepta `=` no final |
| ledger | T3 | 707 | ✅ 0e/0w | ✅ | 100 % | ✅ | `escape_field` solo mira 1er char |
| seal | T3 | 473 | ✅ 0e/0w | ✅ | 100 % | ✅ | **crc32 con signo (F3)** |
| regulus | T3 | 506 | ✅ 0e/0w | ✅ | 100 % | ✅ | limpio |
| parchment | T3 | 429 | ✅ 0e/1w | ✅ | 100 % | ✅ | W0005 `is_alpha`@246 |
| precis | T4 | 757 | ✅ 0e/4w | ✅ | 100 % | ✅ | 4× W0005 |
| invoke | T4 | 737 | ✅ 0e/0w | ✅ | 100 % | ✅ | limpio |
| trial | T4 | 136 | ✅ 0e/0w | ✅ | 100 % | ⚠️ | **huérfano**: nadie en std lo importa |
| lot | T4 | 608 | ✅ 0e/0w | ✅ | 100 % | ✅ | limpio |
| arithmancy | T4 | 1040 | ✅ 0e/1w | ✅ | **39 %** | ✅ | 111 weaves sin doc |
| celeris | — | 96 | ✅ 0e/0w | ✅ | 100 % | ⚠️ | **huérfano** (solo `test_ffi_libs.py`) |
| ward | — | 674 | ✅ 0e/0w | ✅ | 100 % | ✅ | **no aparece en ningún tier del encargo** |
| xlsx | — | 102 | ✅ 0e/0w | ✅ | 100 % | ⚠️ | **huérfano** opt-in |
| raylib.d | T5 | 2205 | ✅ | ✅ | n/a | ⚠️ skip | 0 weaves |
| sqlite3.d | T5 | 9043 | ✅ | ✅ | n/a | ✅ | 0 weaves |
| webui.d | T5 | 731 | ✅ | ❌ | n/a | skip Windows | 0 weaves |
| rlgl.d | T5 | 665 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| raygui.d | T5 | 605 | ✅ | ✅ | n/a | ❌ | 0 weaves |
| typis.d | T5 | 352 | ✅ | ✅ | n/a | ❌ | 0 weaves |
| raymath.d | T5 | 320 | ✅ | ❌ | n/a | ❌ | **`raymath.Vector2` roto (§3.2)** |
| stb_image_resize2.d | T5 | 216 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| imago.d | T5 | 146 | ✅ | ✅ | n/a | ✅ | 0 weaves |
| nanosvg.d | T5 | 147 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| rlights.d | T5 | 136 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| xxhash.d | T5 | 119 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| minicoro.d | T5 | 89 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| xlsxio.d | T5 | 86 | ✅ | ❌ | n/a | ✅ | 0 weaves |
| datastructura.d | T5 | 80 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| stb_herringbone_wang_tile.d | T5 | 71 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| miniaudio.d | T5 | 63 | ✅ | ✅ | n/a | ❌ | 0 weaves |
| pactum.d | T5 | 63 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| uuid.d | T5 | 61 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| yaml.d | T5 | 57 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| fenestra.d | T5 | 50 | ✅ | ❌ | n/a | skip | 0 weaves |
| nanosvgrast.d | T5 | 49 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| scriptor.d | T5 | 48 | ✅ | ❌ | n/a | ❌ | 0 weaves |
| tomlum.d | T5 | 44 | ✅ | ❌ | n/a | ✅ | 0 weaves |
| perlinum.d | T5 | 32 | ✅ | ❌ | n/a | ❌ | 0 weaves |

### §8.3 Veredicto por tier

| Tier | Módulos | Veredicto | Qué falta |
|------|---------|-----------|-----------|
| **T0 fundacional** | spark, scrolls, archivum, ffi | 🟢 sólido en errores / 🟠 en higiene | `ffi` genera 13 W0001 (3 con mismatch real int→ptr); `SPARK_VERSION`/`STD_VERSION` obsoletos y test vacuo; `scrolls` 66 funciones sin doc |
| **T1 colecciones** | tally, atlas, coven, loom, oracle | 🟠 **el más problemático** | `loom ∩ tally` = **15 nombres públicos idénticos con semántica divergente**; `atlas` 32 % doc inline; `oracle` 71 % de API sin nombrar; 21 W0005 en `loom`. `coven` limpio |
| **T2 sistema** | compass, chronicle, rites, filum, whisper | 🟡 | `filum` 8 W0001; `compass` expone 32 helpers `cp_*`; `chronicle.days_in_month` sin validación; resto OK |
| **T3 datos** | cipher, ledger, seal, regulus, parchment | 🟡 | **`seal.crc32` con signo (bug de corrección)**; `cipher` base64 laxo; `parchment` 1 W0005; regulus/ledger OK |
| **T4 integración** | precis, invoke, trial, lot, arithmancy | 🟡 | `arithmancy` 39 % doc; `precis` 4 W0005; **`trial` duplica `ward` y nadie lo importa**; invoke/lot OK |
| **T5 bindings C** | raylib, raymath, rlgl, raygui, … | 🟡 | Solo declaraciones (0 `weave`); **19/25 sin constante de versión**; 4 módulos gráficos sin compilación end-to-end por skip; `raymath` con tipos rotos (§3.2) |

**Módulos nombrados en el encargo que no existen: ninguno.** Todo `import std.X` de docs, tests y std
tiene archivo. `celeris`, `ward` y `xlsx` no aparecen en ningún tier del encargo (y `ward` es un
módulo puro de 674 LOC / 78 weaves, bien testeado).

### §8.4 Hallazgo ST1 — 🟠 `std/seal.pengu:71` — `crc32` devuelve un `int` con signo

```pengu
# std/seal.pengu:44 (declare) y :71
declare pengu_c_seal_crc32 with data as string into int     # -> C: int pengu_c_seal_crc32(...) { return (int)crc32(...); }
```

**Evidencia:**

```
crc32("a")    = 0xE8B7BE43  -> devuelto como -390611389
crc32("test") = 0xD87F7E0C  -> negativo
```

Cualquier CRC32 ≥ `0x80000000` se vuelve negativo, lo que hace **imposible comparar con el valor
CRC32 estándar** (que es sin signo por definición). Un usuario que calcule el CRC de un archivo y lo
compare con el publicado por cualquier herramienta obtendrá un falso negativo la mitad de las veces.

**Fix propuesto:** declarar y devolver el resultado como `u32` (o añadir `crc32_u32`) y ajustar
`to_crc32`.

### §8.5 Hallazgo ST2 — 🟠 `std/ffi.pengu:133,137,141` — `transmute` int→puntero con tamaño dispar

```pengu
# std/ffi.pengu:133,137,141 (W0001: int 4 bytes -> ref 8 bytes)
return transmute 0 to ref to void
```

El propio checker lo señala (`W0001 transmute from 'int' (4 bytes) to 'ref to void' (8 bytes) has
size mismatch and is unsafe`), tres veces en el módulo FFI. Y existe una forma limpia verificada:

```bash
$ weave f into ref to void: return null     # compila SIN W0001
```

**Fix propuesto:** sustituir por `return null` en `null_void`/`null_char`/`null_byte`.

### §8.6 Hallazgo ST3 — 🟡 Los diagnósticos `W0001` pierden la posición

Los 21 warnings de `transmute` se emiten como `file:0:0` (sin línea ni columna), mientras que los
`W0005` sí traen línea:

```
std/ffi.pengu:0:0 [W0001] transmute from 'int' (4 bytes) to 'ref to void' (8 bytes) …
std/loom.pengu:967:0 [W0005] Variable 'exp' shadows global function 'exp'
```

**Impacto:** los avisos de conversión insegura —precisamente los que más importa revisar— son
**inolocalizables**, así que no se pueden arreglar con precisión ni mostrar en un IDE.

**Fix propuesto:** propagar la posición del nodo AST en el chequeo de `transmute`.

### §8.7 Hallazgo ST4 — 🟡 `loom ∩ tally`: 15 nombres públicos idénticos con semántica divergente

| Nombre | `loom` | `tally` |
|--------|--------|---------|
| `mean` | `float` | `int` |
| `median` | `maybe float` | `int` |
| `mode` | `maybe int` | `int` |
| `min_max` | `maybe Pair` | `list of int` |
| `sum`, `flatten`, `enumerate_pairs`, `is_sorted_asc`, `is_sorted_desc`, `repeat`, `running_sum`, `scan_left`, `take`, `windowed`, `zip_with` | idénticos en nombre | ídem |

15 nombres compartidos. `loom` maneja la colección vacía con `maybe none`; `tally` devuelve `0`.
**La misma llamada conceptual cambia de tipo de retorno y de política de vacío según el módulo que
el usuario haya importado.**

**Fix propuesto:** unificar la semántica (preferir la de `loom`, que es más segura) o renombrar la
familia de `tally` (`tally.mean_int`, …) y documentar la elección.

### §8.8 Hallazgo ST5 — 🟡 50 warnings propios que ningún gate bloquea

| Warning | Sitios | Consecuencia |
|---------|--------|--------------|
| `W0005` shadowing | 29 (21 en `loom` por `exp`, más `last`, `range`, `is_alpha`, `chunk`, `path`, `first`, `count`) | Ruido en cada build que importe esos módulos; riesgo de llamar al local por error |
| `W0001` transmute | 21 (13 en `ffi`, 8 en `filum`) | Avisos de seguridad inlocalizables |

Detalle relevante: **el conjunto de W0005 depende del entry point.** Comprobando
`std/archivum.pengu` como entrada aparecen además `tally.pengu:477` y `tally.pengu:524` (W0005
`count`), que no aparecen al comprobar `tally` como entrada. Es decir, los warnings **no son una
función del módulo sino del grafo de compilación**, lo que rompe cualquier expectativa de
reproducibilidad por módulo.

### §8.9 Hallazgo ST6 — 🟡 Deriva de versiones y un test vacuo

| Sitio | Valor | Esperado |
|-------|-------|----------|
| `std/spark.pengu:30` `SPARK_VERSION` | `"0.7.0-spark"` | consistente con VERSION 0.16.0 |
| `std/spark.pengu:33` `STD_VERSION` | `"0.14.1"` | 0.16.0 (2 releases de retraso) |
| `std/spark.pengu:80` doc | *"0.6.0-spark"* | contradice el valor real |
| `tests/std_programs/test_spark.pengu:7` | **imprime el literal** `"0.6.0-spark"` en vez de comparar | **test vacuo que pasa por construcción** |

**Impacto:** el único test que debería detectar la deriva de versión de `spark` **no compara nada**;
imprime el valor esperado como literal. `test_stdlib.py` marca ese literal como correcto y pasa.

**Fix propuesto:** cambiar el test a una aserción real (`sv == SPARK_VERSION`) y decidir si
`STD_VERSION` se elimina o se sincroniza.

### §8.10 Hallazgos menores de la stdlib

| Severidad | Archivo | Evidencia | Impacto | Fix |
|-----------|---------|-----------|---------|-----|
| 🟡 | `std/cipher.pengu:162` | `decode_base64` solo valida `clen % 4 == 0`: `"QQ==QQ=="` decodifica 2 bytes en vez de `none` | Entrada malformada aceptada en silencio | Rechazar `=` salvo en los dos últimos grupos y parar tras el primer padding |
| 🟢 | `std/ledger.pengu:escape_field` | `var dcode as int is ord delim` compara solo el **primer** carácter del delimitador | `"::"` no detecta el segundo `:` y puede no entrecomillar | Comparar con el delimitador completo |
| 🟢 | `std/compass.pengu` | 32 de 89 weaves públicos son helpers internos `cp_*` expuestos junto a la API pública | Superficie pública duplicada | Prefijar `_cp_*` |
| 🟢 | `std/chronicle.pengu:days_in_month` | Devuelve 31 por defecto para `m=0` o `m=13` | Entrada inválida enmascarada | Validar y devolver 0/error |
| 📝 | `CHEATSHEET.md:2388` | Dice `compress`/`decompress`; los reales son `zlib_compress`/`zlib_decompress` | El usuario llama a un nombre inexistente | Corregir el catálogo |
| 📝 | `CHEATSHEET.md:2391` | Dice loom `product`/`max`/`min`; reales `product_num`/`max_int`/`min_int` | Ídem | Corregir el catálogo |
| 📝 | `CHEATSHEET.md:2367` | "Core module catalog (25 modules)" con 27 puros reales | Inventario inconsistente | Actualizar recuento |
| 📝 | `docs` global | 541/1463 (37 %) nombres públicos nunca aparecen en la documentación | API no descubrible sin leer el fuente | Generar referencia por módulo |
| 📝 | `std/tally.pengu`, `std/oracle.pengu` | Semántica de vacío y `@deprecated` divulgados solo en comentarios; alias `average`/`argmin`/`argmax`/`filter_range` siguen públicos | API de doble vía sin fecha de retirada | Listar deprecations con plan |

### §8.11 ❌ REFUTADO — dos sospechas del encargo que resultaron falsas

| Sospecha | Veredicto | Evidencia |
|----------|-----------|-----------|
| "¿Hay fugas de memoria en la stdlib? (casi todos los módulos tienen 0 `banish`)" | **❌ REFUTADO** | No es fuga: `LANGUAGE.md` §13.4 documenta auto-banish de scope-owned locals; los strings dinámicos se limpian automáticamente y los tipos valor (`Vec`/`Mat`) no asignan heap |
| "`at (stack.len - 1)` en `archivum:431,533,566` es un off-by-one" | **❌ REFUTADO** | Los tres sitios están bajo `while stack.len > 0`; el índice `len-1` siempre es válido |
| "`tally.percentile` con p=0/100 y n=1 puede salirse de rango" (`loom.pengu:611-623`) | **❌ REFUTADO** | La guarda `low >= n-1` corta antes de que `low+1` quede fuera de rango |

### §8.12 ✨ UNDERSELL — `loom` es mejor que `tally` y nadie lo dice

- `_min_max_int` (`std/loom.pengu:193-206`) usa un flag `first` correcto para el primer elemento.
- `median` (`:569-577`) promedia las dos centrales en longitud par — el comportamiento correcto.
- El manejo de colección vacía con `maybe none` es **más seguro** que el `0` que devuelve `tally`.

La documentación no indica cuál de los dos módulos usar. Debería recomendar `loom` para datos
posiblemente vacíos y reservar `tally` para el caso numérico simple.

---

## §9. Syntax & Sugar

> **Veredicto:** 🟡 **parcial** — el lenguaje tiene una cantidad notable de azúcar **real y
> funcional**, muy por encima de lo que su versión 0.16 sugiere. Los problemas son tres: azúcar
> documentada que no existe (`alias` en `concept`), azúcar que concede capacidades de forma no
> monotónica (bounds, §3.1), y azúcar con doble sintaxis para lo mismo.

### §9.1 Inventario de azúcar: qué tenemos y si funciona

| Azúcar | ¿Existe? | Evidencia de funcionamiento | Veredicto |
|--------|----------|------------------------------|-----------|
| `with:` (builder implícito) | ✅ | `tests/test_codegen_with_list.py`; `with_init_expr` en el grammar | 🟢 |
| `do:` (bloque como expresión) | ✅ | `do_expr` en el grammar | 🟢 |
| `if`/`while`/`for` en **posición de valor** | ✅ | `?value_expr` incluye `if_stmt`/`while_stmt`/`for_stmt`; el checker decide por posición | 🟢 |
| `judge` (pattern matching) | ✅ | `judge_expr` + `NonExhaustiveJudgeError` (E0044) | 🟢 |
| Lambdas `lambda … into …` | ✅ | Con restricción documentada de **sin captura** — decisión de diseño explícita | 🟢 |
| `or:` / `or else` / `or return` | ✅ | `E0045`/`E0058` se emiten; desambiguación de `or` con prioridades de terminal | 🟢 |
| `try` | ✅ | `?try_expr` | 🟢 |
| `some` / `maybe none` | ✅ | `maybe_type`, `maybe_none` | 🟢 |
| `donum T` | ✅ | `donum_expr`; `E0049` si el tipo no tiene valor por defecto | 🟢 |
| `cyclus` | ✅ | `cyclus_kw` en `rune_decl`/`echo_decl`/`omen_decl` | 🟢 |
| `derive` | ✅ (al menos `Par`/`Ordo`) | `derive Par`, `derive Ordo`, `derive Par, Ordo` verificados | 🟡 otros concepts NO VERIFICADOS |
| `insignia` | ✅ | Una por archivo; `E0026` si hay varias | 🟢 |
| `bind … with … :` | ✅ | `bind_decl`; `E0030`/`E0031`/`E0032` | 🟢 |
| `concept` | ✅ | `concept_decl` + `where T: Concept` | 🟢 |
| `enchanting` (impl blocks) | ✅ | `enchanting_decl`; bloque 28 de LANGUAGE.md usa `weave ritual zero` y `calling Vec2.zero` | 🟢 |
| `ritual` (método estático) | ✅ | `weave_modifier`; `E0033`/`E0034` para mal uso | 🟢 |
| `when` (compile-time) | ✅ | `when_top_decl`, `when_stmt`, `when_expr`; `E0039` si no es constante | 🟢 |
| `test` (tests integrados) | ✅ | `test_decl`; compilados solo en `--test` | 🟢 |
| `unsafe:` | ✅ | `unsafe_stmt`; desactiva bounds/overflow checks | 🟢 |
| Atributos `@inline/@cold/@deprecated/@packed/@align` | ✅ | `attribute` en el grammar; `E0056` si es desconocido | 🟢 |
| `array of T with size N` | ✅ | `array_type` | 🟢 |
| Rangos `a to b` y `a .. b` | ✅ **dos sintaxis** | `range_dotdot` y `to_expr` coexisten | 🟡 duplicidad |
| `transmute X to T` | ✅ | `transmute` en `unary`; `W0001` si los tamaños no cuadran | 🟢 |
| `sigil of` / `essence of` | ✅ | `unary` | 🟢 |
| `length` postfijo | ✅ | `length_expr` | 🟢 |
| `at` postfijo (index/slice) | ✅ | `at_expr`, `slice_at_expr` | 🟢 |
| `defined(NAME)` | ✅ | `defined_expr` | 🟢 |
| `banish` | ✅ | `banish_stmt` + `banish_expr`; `E0047`/`E0048` | 🟢 |
| `defer` / `errdefer` | ✅ | `defer_stmt`, `errdefer_stmt` | 🟢 |
| `alias` en `concept` | ❌ **NO existe** | Bloque 59 de LANGUAGE.md → `E0000 unexpected 'alias'` | 🔴 doc |
| Interpolación `"{expr}"` con expresiones complejas | 🟡 Parcial | `E0019` en el bloque 90 de LANGUAGE.md: `'{(original.value == payload to string)}'` → syntax error | 🟡 |

### §9.2 Qué azúcar **falta** para 1.0

| Candidato | ¿Falta? | Justificación técnica | Recomendación |
|-----------|---------|----------------------|---------------|
| `async`/`await` | **Sí, y debe seguir faltando** | Sin GC y con ownership determinista, un runtime async es un proyecto en sí mismo. No hay demanda en la stdlib | ⏸️ **DIFERIDO a 1.1+** |
| `match` (alias de `judge`) | No | `judge` ya es el keyword único por tarea; añadir `match` rompería la filosofía | ❌ **NO añadir** |
| `for let` / inmutabilidad por defecto | No | `let` ya existe; `for` no permite mutar el índice hoy | 🟢 BAJO |
| Destructuración extendida (`var a, b is f()`) | Sí | Hoy `let var_name_list` existe pero `var`/`let` de tupla parece limitado | 🟡 MEDIO |
| `impl` blocks separados de `enchanting` | No | `enchanting` es exactamente eso | ❌ |
| `?.` / `??` (safe navigation / null-coalescing) | Parcialmente | `or else` cubre el 80 % del caso; `?.` sería azúcar sobre `maybe` + campo | ⏸️ **DIFERIDO**: `if u as User is user:` ya resuelve el caso principal |
| Spread/variadic en call site `f(...xs)` | **Sí, falta** | `many T` existe en la **declaración** (`declare_params` acepta `VARARGS`), pero no hay sintaxis de **expansión** en el call site | 🟡 MEDIO — a verificar en 1.0 |
| Named arguments | ✅ Ya existen | `arg: NAME "is" list_value_expr -> named_arg` | ✅ |
| `is present` / `is not present` / `is true` / `is false` | ✅ Ya existen | `comparison` | ✅ |
| `not in` | ✅ Ya existe | `not_in_expr` | ✅ |

### §9.3 Qué azúcar **sobra** o confunde

| Azúcar | Problema | Evidencia | Recomendación |
|--------|----------|-----------|---------------|
| Doble sintaxis de rango `a to b` / `a .. b` | Dos formas para lo mismo; `to` también es la preposición de tipos (`transmute X to T`, `list of T`) | `range_dotdot` y `to_expr` coexisten en `?range_expr` | **Elegir una.** `to` es más legible y consistente con el resto del lenguaje; `..` debería marcarse `@deprecated` |
| `frozen ref to T` vs `ref to frozen T` | Dos órdenes posibles para el mismo tipo; el grammar tiene `frozen_type: "frozen" type` y `ref_type: "ref" "to" type`, así que ambas parsean | `frozen_type` + `ref_type` | **Documentar solo una** (`ref to frozen T`) y hacer que `frozen ref to T` sea error o warning |
| `and` como separador histórico vs `_BOOL_AND` | Ya eliminado de listas (`_AND_SEP.5` tiene más prioridad que `_BOOL_AND.2`), pero sigue vivo en **tipos y nombres** (`shard T and U`, `derive A, B`) mientras `,` hace lo mismo | `_AND_SEP` con prioridad 5 vs `_BOOL_AND` con 2; `shard_params: "shard" NAME (("," \| _AND_SEP) NAME)*` | Mantener solo como compatibilidad; documentar `,` como forma canónica |
| `borrowed` como soft keyword | Funciona, pero `var borrowed view is x` se lee como si `borrowed view` fuese el nombre | `BORROWED.2: "borrowed"` | Aceptable; documentar con ejemplo |
| `at` postfijo | `xs at i + 1` se parsea como `(xs at i) + 1`, lo cual está **documentado explícitamente** en LANGUAGE.md | Bloque 8 de LANGUAGE.md lo explica | 🟢 Bien resuelto, no tocar |
| `sigil of` / `essence of` | `sigil of` es `&x`, `essence of` es `*x`; dos frases de dos palabras para operadores unarios | `unary` | 🟢 Aceptable por la filosofía de keywords |

### §9.4 Qué azúcar debería **desazucararse** al parser

El propio grammar ya documenta la decisión correcta en un comentario de 8 líneas
(`pengu_grammar.py:481-488`):

> *"'if'/'unless'/'while'/'for' deliberately keep a single grammar rule each: the token sequence
> 'if <cond>:' + block (etc.) is identical whether the values are used or discarded, so a second
> "value form" rule would be ambiguous and LALR would silently route every statement-level construct
> into it. Instead, the checker/codegen decide by position whether the construct is used as a value."*

Eso es exactamente lo correcto: **el parser no duplica reglas para el valor, y la decisión se toma
por posición**. Recomendación: aplicar el mismo principio a las `*_no_cast` (§1.4), que sí duplican
la jerarquía entera para excluir `transmute` en dos contextos. Un flag de contexto en el parser
eliminaría ~40 líneas de grammar sin cambiar semántica.

### §9.5 Inconsistencias entre módulos del lenguaje

| Inconsistencia | Detalle | Severidad |
|----------------|---------|-----------|
| Namespace de tipos C | `int`/`i32`/`int32`/`int32_t`/`u64`/`uint64_t`/`size_t`/`usize` coexisten: **41 nombres** en `base_type` | 🟡 |
| `float`/`f32`/`f64`/`double` | Cuatro nombres para dos/tres tipos reales | 🟡 |
| `maybe`/`result` con y sin `to` | `result of T` y `result of T to E`; `maybe T` siempre | 🟢 |
| `list`/`array`/`slice`/`many` | Cuatro contenedores con sintaxis distinta y solapamiento conceptual | 🟢 documentado |
| Separador de listas | `,` es el separador canónico pero `and` sigue aceptándose en tipos y nombres | 🟡 |
| Prefijo de privacidad | `_` inicial, tanto para símbolos como para runas | 🟢 |

### §9.6 Casos límite: ¿qué pasa cuando el usuario hace X?

Todos verificados ejecutando el compilador:

| Caso | Resultado real | ¿Aceptable? |
|------|----------------|-------------|
| `pengu check archivo.pengu` | Ignora el archivo, dice "Clean", rc=0 | ❌ **BUG** |
| `pengu check archivo_inexistente` | "Clean", rc=0 | ❌ **BUG** |
| `pengu check --bogus` | rc=0, "Clean" | ❌ **BUG** |
| `echo "hi"` dentro de `weave main:` | `E0000 unexpected 'echo'` (porque `echo` es unión, no print) | ✅ correcto, pero el mensaje no sugiere `calling spark.println` |
| `weave f into int:` + `while true: return 1` | `E0020 does not return a value` | ❌ falso positivo |
| `import lib` + `calling lib._secret` | **`NameError` de Python** | ❌ **CRASH** |
| `var v as dep.Vec is with x is 1.0` (dep importa lib) | `E0013 fields are: .` | ❌ **BUG** |
| `const 日本語 as int is 1` | `E0000` | 🟡 limitación documentable |
| `weave m shard T where T: Num … a % b` | `E0049` requiere `Integrum` | ✅ correcto |
| `weave e shard T where T: Num … a == b` | **OK** (contradice la tabla de concepts) | ❌ incoherente |
| `weave l shard T where T: Par … a < b` | `E0049` requiere `Ordo` | ✅ pero sorprendente (añadir bound quita capacidad) |
| `pengu eval "1/0"` | sin salida, exit 248 | ❌ sin diagnóstico |
| `pengu fmt --stdin --indent 4` sobre fuente de 2 espacios | corrompe, exit 0 | ❌ **pérdida de datos** |

### §9.7 Errores de compilación confusos

| Mensaje actual | Problema | Mejora propuesta |
|----------------|----------|------------------|
| `E0013 Field 'x' does not exist on Rune 'raymath.Vector2'` con `note: fields are: .` | La nota muestra una lista **vacía**, lo que revela un bug interno en vez de ayudar | Si `fields` está vacío, decir "the type's definition could not be resolved from module X" |
| `E0022 Type parameter 'Vec2' can only be used within a generic declaration (shard)` para `raymath.Vector2` | `raymath.Vector2` **no es** un parámetro de tipo; el mensaje apunta al lugar equivocado | Trazar el error real de resolución de tipo |
| `E0020 Function 'f' … does not return a value` con `while true` | El compilador sabe que `while true` no sale; el mensaje no lo menciona | Añadir nota: "a `while true` loop is a terminating path" (tras arreglar el falso positivo) |
| `E0000 Syntax error: unexpected 'echo'` | No sugiere que `echo` es una unión y que para imprimir se usa `calling spark.println` | Añadir `help:` con el nombre correcto |
| `Syntax error: unexpected 'k'` en C generado (no en PenguScript) | El usuario ve un error del compilador de C hablando de un identificador que no escribió | Limpiar el C estricto (§4.1) |
| Tracebacks crudos en `run`/`eval`/`expand`/`time`/`watch` | `FileNotFoundError`, `ParseError`, `UndefinedIdentifierError` de Python | Envolver en el reporter estándar |

### §9.8 Warnings que faltan y que sobran

**Faltan:**

| Warning propuesto | Por qué |
|-------------------|---------|
| `W0008 UnusedImport` | Organize imports existe como acción LSP pero no hay warning; `pengu check` no reporta imports sin usar |
| `W0009 UnreachableAfterLoop` | Complemento del falso positivo E0020: avisar cuando hay código tras un `while true` |
| `W0010 ShadowingLocal` | `W0005` solo cubre shadowing de **globals**; el shadowing local-local no se avisa |
| `W0011 EmptyTestBody` | `test "name":` con cuerpo vacío pasa silenciosamente |
| `W0012 DeprecatedAliasUse` | `tally.average`, `argmin`, `argmax`, `filter_range` son alias `@deprecated` sin warning efectivo en la práctica |

**Sobran (o deberían silenciarse por defecto):**

| Warning | Motivo |
|---------|--------|
| `W0005` en bloques `test` (21 casos en `loom`) | El shadowing dentro de un bloque `test` es legítimo y ruidoso; debería silenciarse en código de test |
| `W0005` en general | 29 casos en la stdlib con nombres naturales (`last`, `range`, `first`, `path`, `chunk`) | El warning debería requerir `--warn-shadow` o distinguir "shadowing de función global" de "de variable global" |

### §9.9 Features del roadmap de 1.0 que siguen sin implementar

| Feature | Estado | Evidencia |
|---------|--------|-----------|
| Associated types en concepts (`alias Item`) | ❌ Ausente | §1.2 |
| `derive` para todos los concepts derivables | 🟡 Solo `Par`/`Ordo` verificados | §9.1 |
| Expansión de variádicos en el call site | 🟡 No verificado; `many`/`VARARGS` existen en declaración | §9.2 |
| Cross-compilation verificada Linux⇄Windows | 🟡 Código real, sin probar | §6.1 |
| Soporte MSVC real | ❌ Ausente | §5.1, §15 |
| `--strict-c99` funcional | ❌ Roto | §4.1 |
| LSP `workspace/symbol` | ❌ Ausente | §7 |
| LSP code lens funcional | ❌ Inerte | §7.3 |

### §9.10 Corrección de una afirmación propia (honestidad de esta auditoría)

Una versión preliminar de este informe afirmaba que *"la guía de estilo enseña una sintaxis
prototype-first que el compilador ya no usa"*. **Esa afirmación era FALSA y se retira.**

```bash
$ grep -c "prototype" PenguScriptGuideEnglish.md PenguScriptGuideSpanish.md
PenguScriptGuideEnglish.md:0
PenguScriptGuideSpanish.md:0

$ grep -c "weave " PenguScriptGuideEnglish.md PenguScriptGuideSpanish.md
PenguScriptGuideEnglish.md:57
PenguScriptGuideSpanish.md:57

$ grep -n "prototype" LANGUAGE.md
779: ... on both the forward prototype and the C implementation ...
807: `declare` registers external C function prototypes ...
1122: int32_t compare_ints(const void* a, const void* b);          /* prototype */
1142: `frozen` the Pengu signature matches the C prototype ...
```

Las cuatro apariciones de "prototype" en `LANGUAGE.md` son **terminología de C** (prototipo de
función C), no sintaxis de PenguScript. Las guías de estilo usan `weave` en sus 57 apariciones y
**cero** `prototype`. Se retira la afirmación de §0.4 y se deja constancia del error para que el
lector pueda calibrar el nivel de verificación del resto del informe.

**La contradicción real de la guía de estilo es otra** —el ancho de indentación— y se documenta con
evidencia en §10.2.

### §9.11 El "holy grail" que aún no tenemos

Buscando la feature que cambiaría la categoría del lenguaje y que **no** está en el roadmap actual:

**Ownership verificado con préstamos (borrow checking) de verdad.** El lenguaje tiene `banish`,
`defer`, `errdefer`, auto-banish, `borrowed` y `frozen`, y un análisis de escape de 406 líneas
(`_check_symbol_escape`). Pero **no hay un verificador de préstamos**: se puede tener un `ref to T`
y `banish` el original sin que el compilador lo detecte, mientras `banish` sobre un `borrowed`
sí se detecta (`E0048`). La pieza que falta es la que hace que un `ref to T` **invalide** el owner
durante su vida útil.

Es más valioso que cualquier azúcar de §9.2 porque:
1. Es la diferencia entre "ownership determinista" (una convención) y "memory safety verificada"
   (una garantía). La documentación ya reivindica seguridad de memoria.
2. Completa features **ya existentes** en vez de añadir superficie nueva.
3. Sin GC ni async, un borrow checker es viable estáticamente.

**Recomendación:** marcarlo como objetivo de **1.1**, no de 1.0 (es un cambio de análisis, no de
sintaxis), y dejar de reivindicar "memory safe" hasta entonces.

---

## §10. Style Guide (`PenguScriptGuideEnglish.md`, `PenguScriptGuideSpanish.md`)

> **Veredicto:** 🟠 **con problemas graves** — las guías son documentos serios y bien escritos
> (57 usos correctos de `weave`, cero sintaxis obsoleta), pero **contradicen al propio `pengu fmt`**
> en el ancho de indentación, declaran cubrir la versión 0.14.x, y no se aplican a la stdlib en los
> puntos donde más importaría.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| Reglas vigentes | ✅ Mayoría | 57 usos de `weave`, cero `prototype`; naming, organización y convenciones documentadas | 🟢 |
| Reglas obsoletas tras cambios de sintaxis | ✅ **Ninguna detectada** | Verificado: `grep -c prototype` → 0 en ambas guías | ✅ RESUELTO |
| Versión cubierta | ❌ Desactualizada | `PenguScriptGuideEnglish.md:3` → *"Covered version: PenguScript **0.14.x**"* con `VERSION`=0.16.0 | 📝 |
| Ancho de indentación coherente con `pengu fmt` | ❌ **CONTRADICCIÓN** | Guías usan **4 espacios** (110 ocurrencias de 4, 18 de 8); `pengu fmt` por defecto usa **2** | 🟠 |
| La stdlib cumple el guide | 🟡 Parcial | 37 % de nombres públicos sin mencionar; `atlas` 32 % y `arithmancy` 39 % de doc inline; 50 warnings propios | 🟡 |
| Reglas que el lenguaje no permite cumplir | 🟡 Detectadas | Ver §10.4 | 🟡 |
| Reglas nuevas necesarias | Sí | Ver §10.5 | 🟡 |
| Reglas a eliminar | Sí | Ver §10.6 | 🟢 |

### §10.1 Lo que las guías hacen bien

Debe reconocerse explícitamente, porque es infrecuente en proyectos de esta madurez:

- **Cero sintaxis obsoleta.** Verificado con `grep -c "prototype"` → **0** en ambas guías, y
  `grep -c "weave "` → **57** en cada una. Las guías fueron mantenidas al día con la sintaxis real.
- **Se presentan correctamente** como documento normativo con la analogía PEP 8 / Rust API
  Guidelines, y declaran ser el complemento normativo de `LANGUAGE.md`.
- **Cobertura bilingüe real**: los dos documentos tienen exactamente 72 bloques `pengu` cada uno, lo
  que sugiere mantenimiento sincronizado y no traducción abandonada.
- **Gobiernan explícitamente la stdlib** (`std.*`) y no solo el código de usuario.

### §10.2 Hallazgo SG1 — 🟠 Las guías usan 4 espacios; `pengu fmt` impone 2

**Medición reproducible:**

```bash
$ .venv/bin/python - <<'EOF'
import re,pathlib,collections
for doc in ["PenguScriptGuideEnglish.md","LANGUAGE.md","CHEATSHEET.md"]:
    t=pathlib.Path(doc).read_text()
    blocks=re.findall(r"```pengu\n(.*?)```",t,re.S)
    c=collections.Counter()
    for b in blocks:
        for ln in b.splitlines():
            if ln.strip() and ln.startswith(" "):
                c[len(ln)-len(ln.lstrip(" "))]+=1
    print(doc, dict(sorted(c.items())[:6]))
EOF
PenguScriptGuideEnglish.md {' 4': 110, ' 8': 18, ' 12': 2}
LANGUAGE.md                {' 2': 8, ' 3': 2, ' 4': 328, ' 6': 7, ' 8': 99, '12': 22}
CHEATSHEET.md              {' 2': 10, ' 4': 343, ' 8': 81, '12': 9}
```

…y la stdlib real:

```bash
$ .venv/bin/python -c "
import collections
c=collections.Counter()
for ln in open('std/spark.pengu'):
    if ln.strip() and ln.startswith(' '):
        c[len(ln)-len(ln.lstrip(' '))]+=1
print(dict(sorted(c.items())[:4]))"
{4: 46, 8: 15}
```

**Ahora la configuración del formateador:**

```python
# pengu_project.py:4792-4793
fmt_p = subparsers.add_parser("fmt", help="Format .pengu files or directories (standard style)")
fmt_p.add_argument("--indent", type=int, default=2, help="Spaces per indentation level (default: 2)")
```

**Es decir: toda la documentación del proyecto y todos los archivos de la stdlib usan 4 espacios,
mientras el formateador que se presenta como "standard style" impone 2 por defecto.** Ejecutar
`pengu fmt std/` reindentaría los 52 módulos, produciendo un diff de 35 910 líneas que no cambia
semántica pero destruye el historial de `git blame`.

Combinado con §6.3 (`--indent` corrompe el fuente), la situación actual es que **la herramienta de
formato no puede usarse ni con su valor por defecto (porque contradice el estilo del proyecto) ni
con un valor explícito (porque corrompe la indentación)**.

**Fix propuesto:** cambiar el default de `--indent` a **4** para que coincida con la documentación y
la stdlib, arreglar el bug de reescalado de §6.3, y añadir un `.pengufmt.toml` en la raíz de la
stdlib declarando `tab_size = 4` de forma explícita y verificable.

### §10.3 Hallazgo SG2 — 📝 Ambos guides declaran cubrir 0.14.x

```
PenguScriptGuideEnglish.md:3:> **Covered version:** PenguScript **0.14.x**
```

La versión real es 0.16.0 (`VERSION`, `pengu_version.py:FALLBACK_VERSION`). Hay además deriva en
otros sitios:

| Archivo | Afirmación | Realidad |
|---------|-----------|----------|
| `PenguScriptGuideEnglish.md:3` | Cubre **0.14.x** | 0.16.0 |
| `PenguScriptGuideSpanish.md` | ídem | 0.16.0 |
| `pengu_parser/pengu_parser.py:92` | *"LALR(1) parser for PenguScript **v0.14.x**"* | 0.16.0 |
| `pengu_lsp/__init__.py:1` | *"PenguScript **v0.6** Language Server Protocol Package"* | 0.16.0 |
| `README_RELEASE.md` | menciona 0.15.0 | 0.16.0 |
| 12 archivos `.md` más | contienen `0.14.x`/`0.15.0` | 0.16.0 |

**Fix propuesto:** hacer que el test de versión (`tests/test_version.py`, que ya existe) cubra
también las afirmaciones de versión en los `.md` y en los docstrings, o sustituir las cadenas
hardcodeadas por una interpolación desde `__version__` en los generadores de documentación.

### §10.4 Reglas que el lenguaje **no permite cumplir**

| Regla de la guía | Por qué el lenguaje lo impide | Evidencia |
|------------------|------------------------------|-----------|
| "Toda función pública debe tener docstring" | `ffi`, `scrolls`, `atlas`, `arithmancy` incumplen por diseño: `scrolls` tiene 66 funciones públicas sin doc inline; `atlas` 135; `arithmancy` 111 | 37 % de nombres públicos no aparecen en docs |
| "Usa 4 espacios" (implícito por los ejemplos) | `pengu fmt` impone 2 y `--indent 4` corrompe | §10.2, §6.3 |
| "Sin shadowing de nombres globales" | `loom` tiene 21 casos, `tally` 3, `precis` 4, `archivum`/`arithmancy`/`parchment` 1 cada uno | 29 W0005 en la stdlib |
| "API consistente entre módulos" | `loom` y `tally` comparten 15 nombres con tipos de retorno distintos | §8.7 |
| "Sin conversiones inseguras" | `ffi` tiene 13 `transmute` (3 con mismatch real), `filum` 8 | §8.5 |

**El punto crítico:** la guía prescribe reglas que **la propia stdlib viola en 50 sitios medibles**.
Una guía de estilo que su biblioteca estándar incumple no puede ser normativa; o se aplica, o se
relaja con una excepción documentada.

### §10.5 Reglas nuevas que hay que añadir

| Regla propuesta | Motivo |
|-----------------|--------|
| Indentación: **4 espacios, nunca tabs**, y `pengu fmt` debe respetarlo | Resuelve §10.2 y hace el formato idempotente |
| Prohibido `transmute` fuera de `std/ffi` y `std/filum`, y siempre entre tipos del mismo tamaño | Los 21 W0001 son de esos dos módulos; la regla los hace auditables |
| Toda función pública nueva **debe** ir acompañada de doc inline en el mismo commit | El 37 % de API sin documentar crece, no se corrige solo |
| Prohibido exportar helpers `_`-less (`cp_*` debe ser `_cp_*`) | `compass` expone 32 helpers internos (§8.10) |
| Los constructores `ritual` deben documentar su invariante | `enchanting`/`ritual` son la única forma de "constructor"; sin invariante escrita, `Vec2.zero` y `Vec2.x` pueden divergir |
| Toda constante `<MOD>_VERSION` debe coincidir con `VERSION` y ser **aserada** en un test | El caso de `spark` (§8.9) demuestra que sin aserción la deriva es invisible |
| Prohibido nombrar un local igual que una función global del mismo módulo | 29 W0005 evitables |
| Un nombre de función pública debe ser único en toda la stdlib salvo reexportación explícita | 15 colisiones `loom`/`tally` |

### §10.6 Reglas a eliminar o relajar

| Regla | Motivo |
|-------|--------|
| Cualquier prescripción de "docstring obligatorio en el 100 % de funciones" | Es incumplible hoy y produce ruido; sustituir por "obligatorio en la API pública nueva + `@deprecated` para la vieja" |
| Reglas que dupliquen lo que el compilador ya garantiza (p. ej. "usa `is present` en lugar de comparar con null") | El checker ya emite `E0049`/`E0005`; una guía que repite el checker se desincroniza |
| La restricción implícita de indentación a 2 espacios (derivada de `pengu fmt`) | Contradice a la propia documentación (§10.2) |

### §10.7 Auditoría de la stdlib contra el guide

| Módulo | Doc inline | Shadowing | `transmute` | Nombres duplicados | Cumple |
|--------|-----------|-----------|-------------|--------------------|--------|
| `spark` | 100 % | 0 | 0 | 0 | ✅ salvo versiones |
| `scrolls` | **52 %** | 0 | 0 | 0 | ❌ doc |
| `archivum` | 100 % | 1 | 0 | 0 | 🟡 |
| `ffi` | 100 % | 0 | **13** | 0 | ❌ unsafe |
| `tally` | 100 % | 3 | 0 | **15** | ❌ duplicados |
| `atlas` | **32 %** | 0 | 0 | 0 | ❌ doc |
| `coven` | 100 % | 0 | 0 | 0 | ✅ |
| `loom` | 100 % | **21** | 0 | **15** | ❌ |
| `oracle` | 100 % | 0 | 0 | 0 | ✅ |
| `compass` | 100 % | 0 | 0 | 0 | 🟡 helpers `cp_*` |
| `chronicle` | 100 % | 0 | 0 | 0 | 🟡 validación |
| `rites` | 100 % | 0 | 0 | 0 | ✅ |
| `filum` | 100 % | 0 | **8** | 0 | ❌ unsafe |
| `whisper` | 100 % | 0 | 0 | 0 | ✅ |
| `cipher` | 100 % | 0 | 0 | 0 | 🟡 base64 |
| `ledger` | 100 % | 0 | 0 | 0 | 🟡 delimitador |
| `seal` | 100 % | 0 | 0 | 0 | ❌ crc32 con signo |
| `regulus` | 100 % | 0 | 0 | 0 | ✅ |
| `parchment` | 100 % | 1 | 0 | 0 | 🟡 |
| `precis` | 100 % | 4 | 0 | 0 | 🟡 |
| `invoke` | 100 % | 0 | 0 | 0 | ✅ |
| `trial` | 100 % | 0 | 0 | duplica `ward` | 🟡 |
| `lot` | 100 % | 0 | 0 | 0 | ✅ |
| `arithmancy` | **39 %** | 1 | 0 | 0 | ❌ doc |

**Resumen:** 5 módulos limpios (`coven`, `oracle`, `rites`, `whisper`, `regulus`, `invoke`, `lot`),
5 con incumplimiento claro (`scrolls`, `atlas`, `arithmancy`, `ffi`, `filum`), 2 con duplicación de
API (`tally`, `loom`) y el resto con incidencias menores.

---

## §11. Tests (`tests/`)

> **Veredicto:** 🟢 **listo en volumen y disciplina** / 🟠 **con un agujero grave de cobertura de
> integración** — la suite es grande, pasó limpia en 15 minutos, no tiene tests flaky ni `xfail` sin
> justificar, y tiene un `conftest.py` real. Pero **cero tests ejercitan `pengu check <archivo>`**,
> que es exactamente el bug bloqueante B1.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| Cobertura global | 🟡 No medida (falta `pytest-cov`) | `import pytest_cov` → `ModuleNotFoundError`. No está en `requirements.txt` | 🟡 |
| Resultado de la suite | ✅ **2074 passed, 12 skipped, 2 xfailed, 1 xpassed** en 910.67 s | `pytest tests/ -q -p no:cacheprovider --timeout=900` | ✅ |
| Tests que fallan | ✅ **Cero** | — | ✅ |
| Tests flaky | ❌ **Al menos 1** | `test_string_composition_no_memory_leaks[leak_binary_interp]` alterna xpass/xfail (3 de 6 ejecuciones); ver §11.4 | 🟡 |
| Duplicados | 🟡 Sí, en el patrón | 155 archivos `test_*.py`, varios con solapamiento temático (`test_audit_fixes.py`, `test_audit_v0150_fixes.py`, `test_compiler_bugfixes_v0150.py`, `test_p0_review_fixes.py`, `test_phase5_bugfixes.py`, `test_phase6_bugfixes.py`) | 🟡 |
| Dependencia de rutas absolutas | ✅ Limpio en tests reales | Los hits de `/home/`/`/tmp/` son literales de **datos esperados** (`test_audit_v0150_fixes.py:936`, `test_result_io_api.py`) o `patch()`, no rutas de ejecución | ✅ |
| `xfail` sin justificación | ✅ **Todos con `reason`** | 7 `xfail`; `test_string_composition_suite.py:169` documenta explícitamente que el xfail estricto XPASSeará cuando el compilador posea sus temporales | ✅ |
| `xpassed` | ⚠️ 1 | `1 xpassed` — un test marcado `xfail` **pasa**. Si el `strict` no está puesto, oculta que la restricción ya no aplica | 🟡 |
| Tests de regresión por bug resuelto | ✅ Buena cultura | 6 archivos `test_*fixes*.py` + `test_known_issues.py` (con el leak real en `xfail(strict=True)`) | ✅ |
| Tests de compliance (los 50 canónicos) | ❌ **No existe un corpus canónico** | No hay `tests/compliance/` ni lista de 50 programas; la cobertura es por feature | 🟠 |
| Tests de migración v0.15 → v1.0 | ❌ Ausentes | No hay corpus de programas antiguos que deban seguir compilando | 🟠 |
| Tests de rendimiento | 🟡 `test_benchmarks.py` + `benches/` | Pero **`benches/` no importa ni un solo `std.`**, así que la stdlib no está benchmarkeada | 🟡 |
| Tests de estrés (10k LOC, 100k iteraciones) | 🟡 Parcial | El LSP se probó a 2024 líneas; `pengu check` a 2024 líneas tarda 1.4 s. No hay 10k LOC | 🟡 |
| `conftest.py` bien estructurado | ✅ **446 líneas** con helpers y compilación C real (`:227` compila el C emitido) | `tests/conftest.py` | ✅ |
| Tests que invocan la CLI real | ✅ 49 archivos usan `subprocess` | — | ✅ |
| **Tests de `pengu check <archivo>` (el bug B1)** | ❌ **CERO** | El único test de `check` es `test_cli_tools.py:211`: `cli(["check", "-c", proj, "-e", "src/main.pengu"])` — **siempre con `-c` y `-e` explícitos** | 🔴 |
| Fuzz | ✅ Existe | `scripts/fuzz/` + `fuzz.yml` | ✅ |
| Property-based testing | ❌ Ausente | No hay `hypothesis` en `requirements.txt` | 🟡 |
| Cross-platform | 🟡 Matriz real ≠ reivindicada | gcc(Linux) / clang-o-gcc(macOS) / **MinGW**(Windows, `ci.yml:96-97` hardcodea `CC_BIN="gcc"`) | 🟠 |
| MSVC | ❌ **Cero** | "MSVC" en la matriz es MinGW; `tests/test_attributes_msvc.py:39` solo verifica **texto** emitido, nunca invoca un compilador | 🟠 |
| TCC en CI | 🟡 Existe pero no sobre `std` | `test_c99_portability.py` compila `_PROG` sin imports | 🟠 |
| ASan/UBSan | ✅ En CI, ❌ rojo | `.github/workflows/sanitizers.yml`; ver §11.3 | 🔴 |
| Valgrind | ✅ En CI (Linux only) | `sanitizers.yml:104` | 🟡 |

### §11.1 Hallazgo TST1 — 🔴 El agujero de cobertura que permitió el bug B1

El bug más grave del CLI (§6.2) es que `pengu check <archivo>` ignora el archivo. **Ningún test lo
detecta**, y la razón es concreta:

```python
# tests/test_cli_tools.py:211 — el ÚNICO test que invoca 'pengu check'
res = cli(["check", "-c", proj, "-e", "src/main.pengu"])
```

Todos los tests de la CLI pasan `-c` (config) y `-e` (entry) explícitos. **Ninguno pasa un
posicional.** Y los 2000+ tests restantes llaman a `PenguChecker.check()` directamente, sin pasar
por la CLI:

```bash
$ grep -rn "checker.check(tree" tests/*.py | wc -l
# decenas de coincidencias, todas con PenguChecker directo
$ grep -rn 'check", *"\(src\|tests\)/' tests/*.py
# (vacío)
```

**Consecuencia estructural:** la suite prueba **el compilador** exhaustivamente y **el CLI** apenas.
Un bug que afecta a la totalidad de la superficie de la CLI (B1) convive con 2074 tests en verde.

**Fix propuesto:** añadir una clase de tests de "contrato de CLI" que ejecute cada subcomando con
**posicionales** y sin flags, verificando rc y efectos; en particular `pengu check <archivo_roto>`
debe dar rc=1 y `pengu check <archivo_inexistente>` también.

### §11.2 Hallazgo TST2 — 🟠 No hay corpus de compliance ni de migración

El encargo pregunta por "los 50 canónicos" y por "tests de migración v0.15 → v1.0". **Ninguno de los
dos existe.** No hay:

- `tests/compliance/` con un conjunto fijo y numerado de programas canónicos.
- Un corpus de programas escritos contra versiones anteriores que deban seguir compilando (lo que en
  la práctica define la compatibilidad hacia atrás).
- Un test que verifique que un programa v0.14.x/v0.15.0 compila sin cambios.

Esto importa especialmente porque **la sintaxis sí cambió**: el CHANGELOG documenta la eliminación
de `and`/`or` como separadores de lista en 0.10.0, y el grammar `pengu_grammar.py:497-502` lo
comenta explícitamente:

> *"A bare 'and'/'or' is not an operand there, so the removed 0.10.0 list separator can never be
> silently read as one boolean element ('calling f with a and b' is now a hard error instead of a
> single bool argument; parenthesise to pass a boolean: '(a and b)')."*

Un cambio así **debe** tener un corpus de migración que demuestre que el código válido escrito antes
sigue funcionando y que el inválido falla con un mensaje útil.

**Fix propuesto:** crear `tests/compliance/` con 50 programas numerados que cubran cada feature del
manual (uno por sección de `LANGUAGE.md`), y `tests/migration/` con programas de cada versión
histórica, ambos ejecutados en CI.

### §11.3 Hallazgo TST3 — 🔴 El gate de ASan está rojo y el commit que decía arreglarlo no lo hizo

`.github/workflows/sanitizers.yml:58-61` **deselecciona** el test que filtra:

```yaml
# :58-61
--deselect tests/test_std_backward_compat.py::test_std_backward_compat
```

…y `:67-70` **vuelve a ejecutar el archivo completo** en el mismo job, con
`ASAN_OPTIONS=detect_leaks=1:halt_on_error=1` todavía activo. Resultado reproducido con los flags
exactos del workflow:

```bash
$ PENGU_CFLAGS='-fsanitize=address -fno-omit-frame-pointer -fno-sanitize-recover=all' \
  ASAN_OPTIONS='detect_leaks=1:abort_on_error=1:halt_on_error=1' \
  python -m pytest tests/test_std_backward_compat.py -q
FAILED tests/test_std_backward_compat.py::test_std_backward_compat[debug]
FAILED tests/test_std_backward_compat.py::test_std_backward_compat[release]
2 failed in 25.67s
   SUMMARY: AddressSanitizer: 1033 byte(s) leaked in 5 allocation(s).
   assert 134 == 0
```

El leak es real y está **documentado honestamente** en `docs/PERFORMANCE.md:349-358` (temporales de
expresión en `calling spark.println with (n to string)` sin `pengu_banish_string`) y fijado con
`xfail(strict=True)` en `tests/test_string_composition_suite.py`. El problema no es el leak: es que
el commit `77f4ed8` (*"track the ASan leak finding instead of hiding it"*) afirma haber dejado el
job verde y **el job sigue rojo**, porque el `--deselect` se anula dos pasos más abajo.

**Fix propuesto:** aplicar el mismo `--deselect` al tercer paso (y al job de `valgrind` en `:104`), o
eliminar la dependencia de ese archivo en el tercer paso.

### §11.4 Tests flaky, falsos positivos y tests mal escritos

**❌ CORRECCIÓN: hay al menos un test flaky.** La versión original de esta sección afirmaba que "no
se observó ningún test flaky" a partir de dos ejecuciones completas. **Esa verificación fue
insuficiente.** Con 6 ejecuciones aisladas se comprueba que

`tests/test_string_composition_suite.py::test_string_composition_no_memory_leaks[leak_binary_interp]`

**alterna `xpass` y `xfail`**:

```bash
$ for i in 1 2 3 4 5 6; do
    pytest "tests/test_string_composition_suite.py::test_string_composition_no_memory_leaks[leak_binary_interp]" -q
  done
1 xpassed / 1 xfailed / 1 xfailed / 1 xpassed / 1 xfailed / 1 xpassed
```

Causa: el marcador es `xfail(strict=False)` (`tests/test_string_composition_suite.py:72`) sobre una
medición de fugas **no determinista** (con `valgrind` ausente se usa el interposer
`tests/leakcheck.c`). No rompe CI, porque `strict=False` tolera ambos resultados, pero **el resumen
de la suite no es reproducible**: la misma revisión puede reportar `2 xfailed, 1 xpassed` o
`3 xfailed`. Es la razón por la que la línea base de esta auditoría decía `2 xfailed, 1 xpassed` y
la verificación posterior de la Fase 0 dijo `3 xfailed`.

**Lección de método:** "no observé X en dos ejecuciones" no es evidencia de que X no exista. Los
hallazgos negativos sobre flakiness requieren **N ejecuciones**, no 2. Se registra como item 1.14
de `ROADMAP_2.0.md`.

Sí se confirma, en cambio, que no hay `pytest.mark.skip` sin razón (48 usos, todos con `reason`).

**Tests con falso positivo (pasan sin probar lo que dicen):**

| Test | Problema | Evidencia |
|------|----------|-----------|
| `tests/std_programs/test_spark.pengu:7` | **Vacuo**: imprime el literal `"0.6.0-spark"` en vez de aseverar. Es el único test que cubriría la deriva de versión de `spark` | §8.9 |
| `tests/test_cli_strict_c99.py:50` | Solo asevera ausencia de dos **cadenas**; no compila nada con `std` | §4.1 |
| `tests/test_c99_portability.py` (5 tests) | Compila `_PROG` de ~20 líneas **sin imports** | §4.1 |
| `tests/test_error_codes_uniqueness.py` | Solo analiza `kwargs.setdefault`; ignora las **24 emisiones de string crudo**, por lo que `E0035` sigue cubriendo 4 condiciones | §2.3 |
| `tests/test_attributes_msvc.py:39` | Verifica **texto generado** con `target_compiler="msvc"`, nunca invoca `cl.exe` | §15 |
| `ci.yml:96-97` | Windows con `CC_BIN="gcc"` (MinGW) presentado como cobertura MSVC | §15 |
| 1× `xpassed` | Un `xfail` pasa; si no es `strict`, la condición ya no se cumple y nadie lo sabe | §11 |

**Patrón común:** los cuatro primeros son *tests de texto* que sustituyen a *tests de comportamiento*.
Es la causa raíz de los "gates verdes sobre código roto" de §0.5.

**Fix propuesto:** regla de proyecto — un test que verifique portabilidad/seguridad **debe compilar o
ejecutar el artefacto**, nunca inspeccionar su texto; y el `xpassed` debe pasar a
`xfail(strict=True)` o desmarcarse.

### §11.5 Cómo implementar property-based testing

Concretamente, añadiendo `hypothesis>=6.0` a `requirements.txt` y un `tests/test_properties.py`:

| Propiedad | Generador | Oráculo |
|-----------|-----------|---------|
| Round-trip de literales: `parse(format(ast)) == ast` | Árboles sintácticos generados sobre el subconjunto de expresiones | Igualdad estructural del AST |
| Idempotencia del formateador: `fmt(fmt(x)) == fmt(x)` | Programas válidos generados | Comparación textual (**este test habría cazado §6.3** y §10.2) |
| Preservación de semántica del formateador: `check(fmt(x)) == check(x)` | Programas válidos | Mismo conjunto de diagnósticos (**habría cazado §6.3**) |
| Round-trip de contenedores: `list.push` × n → `len == n` | n ∈ [0, 1000], tipos variados | Invariante del runtime |
| Aritmética de enteros: `a op b` coincide con la semántica C de `int32_t` | Enteros de 32 bits, incluidos los límites | Comparación con el resultado del C compilado |
| `transmute`/`to` no cambian el valor en el mismo tipo | Valores de cada tipo primitivo | Igualdad |
| Determinismo del compilador: dos builds del mismo fuente producen el mismo C | Programas válidos | Byte-equality del bundle (verifica la caché y el DCE) |

Las dos propiedades marcadas son las de mayor retorno inmediato: **habrían detectado el bug de
corrupción del formateador**, que hoy no tiene ningún test.

### §11.6 Cobertura crítica ausente — resumen priorizado

| Prioridad | Área sin cubrir | Test que falta |
|-----------|-----------------|----------------|
| 🔴 1 | Contrato de CLI con posicionales | `pengu check <archivo>` rc=1 con error; rc=1 con archivo inexistente; rc=2 con flag desconocido |
| 🔴 2 | `--strict-c99` sobre programas con `std` | Compilar y ejecutar `tests/std_programs/*.pengu` con `--strict-c99` |
| 🔴 3 | `fmt` idempotente y preservador de semántica | `fmt(fmt(x))==fmt(x)` y `check(fmt(x))==check(x)` sobre la stdlib |
| 🟠 4 | Tipos cualificados entre módulos | Test de 3 módulos con `dep.Vec` (§3.2) |
| 🟠 5 | Crash paths del checker | Un test por cada `raise self._make_error(...)` con `node` mal referenciado (**habría cazado §2.1**) |
| 🟠 6 | Corpus de compliance (50 canónicos) | `tests/compliance/` |
| 🟠 7 | Corpus de migración | `tests/migration/` con programas de cada versión |
| 🟠 8 | MSVC real | Job con `cl.exe` en `windows-latest` |
| 🟡 9 | Property-based | §11.5 |
| 🟡 10 | Estrés 10k LOC | Generar y compilar un archivo de 10 000 líneas |
| 🟡 11 | Benchmarks sobre `std` | `benches/` que importen `std.spark`/`std.atlas`/`std.loom` |
| 🟡 12 | Cobertura de código medida | `pytest-cov` en `requirements.txt` + `--cov-fail-under` |

---

## §12. Organización del proyecto

> **Veredicto:** 🟡 **parcial** — la organización es funcional (no hay ciclos, los tests encuentran
> todo), pero la raíz concentra **40 archivos** y un solo `pengu_project.py` de **228 KB / 5207
> líneas** hace de CLI, builder, cache manager, gestor de assets y runner de tests.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| Archivos en la raíz | 🟡 **40** (16 `.py`, 20 `.md`, `.h`, `.c`, `VERSION`, `requirements.txt`, `.gitignore`) | `ls -1 *.py *.md *.h *.c …` | 🟡 |
| `pengu_project.py` monolítico | 🔴 **5207 líneas / 228 KB** | `wc -l`; 5 funciones >200 líneas | 🟠 |
| Módulos filtrados a la raíz | 🟡 12 `pengu_*.py` en la raíz que conceptualmente son del compilador | `pengu_infer.py`, `pengu_comptime.py`, `pengu_folder.py`, `pengu_errors.py`, `pengu_parser.py` están **duplicados**: existen en la raíz **y** en `pengu_parser/` | 🟠 |
| `std_c/` | 🟡 6.5 MB de headers C de terceros (miniaudio, raylib, stb, sqlite3, …) | Contiene 94 `TODO/FIXME` de terceros | 🟢 |
| `c_bind_stubs/` | 🟡 Sigue existiendo (76 KB) | A verificar si algo lo importa | 🟡 |
| `extern/` gitignored | ✅ | `.gitignore:7` `extern/`; `git ls-files \| grep extern` → 0 | ✅ |
| `build/` gitignored | ✅ | `.gitignore:12` `build/` | ✅ |
| `scratch/` | ✅ **No existe** (gitignored) | `ls -d scratch` → no existe | ✅ RESUELTO |
| `tests_std/` | ✅ **No existe** (fusionado en `tests/`) | `ls -d tests_std` → no existe | ✅ RESUELTO |
| `pengucc_build/` | ✅ gitignored y ausente | `.gitignore:14` | ✅ RESUELTO |
| `__pycache__/` | ❌ **Presentes en el árbol de trabajo** (7 directorios fuera de `extern/`) | `find . -name __pycache__` | 🟢 |
| `.pytest_cache/` | ❌ Presente | `ls -d .pytest_cache` | 🟢 |
| `docs/` | 🟡 Existe pero con solo 2 archivos (`FUZZING.md`, `PERFORMANCE.md`) | 24 KB frente a 20 `.md` en la raíz | 🟡 |
| `pengu_runtime.c` raíz (0 bytes) | ❌ Residuo rastreado en git | `git cat-file -s HEAD:pengu_runtime.c` → 0 | 🟢 |
| Archivos temporales (`*.log`, `.csv`, `*.tar.gz`, `*.zip`, `*.vsix`) | ✅ Ninguno rastreado | `git ls-files` limpio; `.gitignore` los cubre | ✅ |
| `AUDIT_RESPONSE.md`, `P1_PROGRESS.md`, `P2_PROGRESS.md`, `CRITICALS_PROGRESS.md`, `Plan.md`, `roadmap.md`, `PRODUCTION_READINESS.md` | 🟡 7 documentos de proceso histórico en la raíz | Ver `CLEANUP_PLAN.md` §1 | 🟡 |

### §12.1 Hallazgo O1 — 🟠 Módulos **duplicados** entre la raíz y `pengu_parser/`

Esta es la sorpresa organizativa de la auditoría. Existen dos copias de varios módulos del
compilador:

| Nombre | Copia en la raíz | Copia en `pengu_parser/` | ¿Cuál se usa? |
|--------|-----------------|-------------------------|---------------|
| `pengu_dce.py` | 491 B (shim de reexportación con `__all__`) | 10 271 B (implementación real) | Ambos: el shim lo importa `tests/test_dce_tcc_pch.py:12`; la implementación la usa `pengu_codegen.py:47` |
| `pengu_assets.py` | 19 770 B | — (solo en raíz) | Raíz |
| `pengu_cache.py` | 12 840 B | — | Raíz |
| `pengu_lock.py` | 7 967 B | — | Raíz |
| `pengu_semver.py` | 7 228 B | — | Raíz |
| `pengu_tcc.py` | 10 082 B | — | Raíz |
| `pengu_paths.py` | 11 450 B | — | Raíz |
| `pengu_bind.py` | 69 507 B | — | Raíz |
| `pengu_doc.py` | 16 661 B | — | Raíz |
| `pengu_version.py` | 2 185 B | — | Raíz |
| `pengu_comptime.py` | — | 14 141 B | `pengu_parser/` |
| `pengu_folder.py` | ❌ **No existe** | ❌ **No existe** | — |

**Dos hallazgos concretos:**

**(a)** El enunciado lista `pengu_comptime.py`, `pengu_folder.py`, `pengu_infer.py`,
`pengu_parser.py`, `pengu_checker.py`, `pengu_symbols.py`, `pengu_types.py`, `pengu_errors.py` como
"archivos Python sueltos en la raíz". **Verificación:** de esos ocho, **solo `pengu_comptime.py`
existe también en la raíz**, y en realidad está **solo** en `pengu_parser/`. `pengu_folder.py` **no
existe en ningún sitio** del repositorio. El resto vive **exclusivamente** en `pengu_parser/`.

```bash
$ for f in pengu_folder.py pengu_comptime.py pengu_infer.py pengu_checker.py pengu_grammar.py; do
    printf "%-22s root=%s parser=%s\n" "$f" \
      "$([ -f $f ] && echo YES || echo no)" "$([ -f pengu_parser/$f ] && echo YES || echo no)"
  done
pengu_folder.py        root=no  parser=no
pengu_comptime.py      root=no  parser=YES
pengu_infer.py         root=no  parser=YES
pengu_checker.py       root=no  parser=YES
pengu_grammar.py       root=no  parser=YES
```

**❌ REFUTADO:** el enunciado afirmaba que hay "fugas de módulos al root" y listaba ocho archivos.
En realidad `pengu_parser/` contiene **todo** el compilador (27 204 líneas) y la raíz solo tiene los
módulos de **tooling** (`pengu_project`, `pengu_bind`, `pengu_doc`, `pengu_assets`, `pengu_cache`,
`pengu_lock`, `pengu_paths`, `pengu_semver`, `pengu_tcc`, `pengu_version`, `pengu_runtime.h`,
`build_runtime`, `extern_manifest`, `make_release`, `regen_std_bindings`,
`migrate_manual_bindings`, `pengu_raymath.py`) más el shim `pengu_dce.py`. La organización es
**mejor de lo que el enunciado suponía**, con la única excepción real del shim `pengu_dce.py`.

**(b)** `pengu_folder.py` **no existe**. Si algún documento lo menciona, es documentación fantasma.
Si el roadmap lo lista como pendiente, conviene decidir si se elimina la mención.

### §12.2 Hallazgo O2 — 🟠 `pengu_project.py` con 5207 líneas y cinco responsabilidades

```bash
$ wc -l pengu_project.py
5207 pengu_project.py

$ # funciones > 200 líneas
    329  main                       :4874
    326  init_project               :3451
    322  build_compile_commands     :1387
    318  create_cli_parser          :4509
    221  run_script                 :4138
```

Responsabilidades distintas dentro del mismo archivo (todas verificadas leyendo el archivo):

1. **Parser de argumentos** — `create_cli_parser` (318 líneas) con 25 subparsers.
2. **Gestor de proyectos** — `ProjectConfig`, `init_project` (326 líneas), plantillas.
3. **Builder** — `PenguBuilder`, `bundle`, caché incremental.
4. **Runner** — `run_script` (221 líneas), `watch`, `eval`.
5. **Gestión de assets** — integración con `pengu_assets`.
6. **`compile_commands.json`** — `build_compile_commands` (322 líneas).

**Fix propuesto (CLEANUP_PLAN §3):** dividir en
`pengu_cli/parser.py`, `pengu_cli/project.py`, `pengu_cli/builder.py`, `pengu_cli/runner.py`,
`pengu_cli/assets.py`, `pengu_cli/gc.py`, manteniendo `pengu_project.py` como *shim* de compatibilidad
(`from pengu_cli.parser import create_cli_parser; …`) para no romper `pyinstaller`, `pengu.bat`,
los tests que lo importan ni los workflows. **No hacerlo antes de arreglar §6** (mezclar refactor
con fix de bugs es cómo se pierden ambos).

### §12.3 Hallazgo O3 — 🟡 El `docs/` está infrapoblado

Solo dos archivos (`FUZZING.md` 24 KB total, `PERFORMANCE.md`) viven en `docs/`, mientras **20
documentos** viven en la raíz, incluyendo los 4 más grandes del proyecto:

| Documento | Bytes | Ubicación apropiada |
|-----------|-------|---------------------|
| `CHANGELOG.md` | **379 426** | raíz ✅ (convención) |
| `LANGUAGE.md` | 210 095 | raíz ✅ o `docs/` |
| `LANGUAGE_Spanish.md` | 213 746 | raíz ✅ o `docs/` |
| `CHEATSHEET.md` | 126 138 | raíz ✅ |
| `README.md` | 83 535 | raíz ✅ (obligatorio) |
| `ROADMAP_1.0.0.md` | 65 411 | raíz ✅ o `docs/` |
| `PRODUCTION_READINESS.md` | 57 194 | **`docs/` o borrar** |
| `AUDIT_RESPONSE.md` | 32 474 | **`docs/audits/` o borrar** |
| `PenguScriptGuide*.md` | 44 K + 45 K | raíz ✅ |
| `PENGU_BUILD.md` | 18 130 | **`docs/`** |
| `P1_PROGRESS.md`, `P2_PROGRESS.md`, `CRITICALS_PROGRESS.md` | 26 KB | **borrar** (proceso terminado) |
| `Plan.md`, `roadmap.md` | 7 KB + 2 KB | **borrar o fusionar** |
| `README_RELEASE.md` | 3 250 | **`docs/`** |

**Fix propuesto:** ver `CLEANUP_PLAN.md` §1 y §3.

### §12.4 Lo que está bien organizado

- **`pengu_parser/` es un paquete coherente**: 27 204 líneas con `__init__.py` que reexporta la API
  pública, sin fugas de módulos a la raíz (salvo el shim `pengu_dce.py`, ver §12.1).
- **`pengu_lsp/` es un paquete limpio**: 4 144 líneas, cero `TODO`/`FIXME`, 0 funciones >200 líneas,
  separación clara por feature (`completions.py`, `hover.py`, `code_actions.py`, `formatting.py`).
- **`.gitignore` es de calidad alta**: 1 385 B cubriendo `extern/`, `build/`, `dist/`,
  `pyinstaller_work/`, `scratch/`, bytecode, entornos virtuales, artefactos de Node/VS Code, IDE,
  SO, logs, `*.profraw`, `*.lcov`, `cscope.out`. **Verificado que nada de eso está rastreado.**
- **Cero dependencias circulares**: comprobado entre `pengu_project` ↔ `pengu_bind` (el import es
  perezoso y local).
- **Los tres residuos históricos del CHANGELOG 0.8.4 están efectivamente eliminados**: `scratch/`,
  `tests_std/` y `pengu_runtime_original.h` **no existen**. **✅ RESUELTO** la sospecha del enunciado.

---

## §13. Documentación

> **Veredicto:** 🟠 **con problemas graves** — el volumen es enorme (1 MB de Markdown en la raíz) y
> hay secciones de calidad excepcional, pero **el catálogo de errores es parcialmente ficticio**,
> **72 de 105 ejemplos no pasan `pengu check`**, y hay **deriva de versión en 13 archivos**.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| `LANGUAGE.md` cubre todo lo que el compilador acepta | 🟡 Cubre más de lo que acepta | Documenta `alias` en `concept` (§1.2) que no existe | 🟠 |
| Catálogo de errores §22.2 correcto | ❌ **No** | 5 clases inexistentes, 5 atribuciones erróneas (§2.2) | 🟠 |
| `CHEATSHEET.md` idempotente con el lenguaje | ❌ **No** | `compress`/`decompress` vs `zlib_*`; loom `product`/`max`/`min` vs `product_num`/`max_int`/`min_int`; "25 modules" con 27 puros | 🟠 |
| Contradicciones entre README/LANGUAGE/CHEATSHEET | 🟡 Detectadas | Recuento de módulos, nombres de funciones, versiones | 🟡 |
| `CHANGELOG.md` coherente | 🟡 Muy completo pero contradictorio en puntos | 379 KB; afirma async-signal-safety (§5.2) que el propio código desmiente | 🟡 |
| `ROADMAP_1.0.0.md` sigue siendo válido | 🟡 Parcial | Marca como pendientes cosas ya hechas y viceversa; reescrito en `ROADMAP_2.0.md` | 🟡 |
| Ejemplos de docs **compilan** | ❌ 33/105 (31 %) pasan completos | Bucle real con `pengu check -c <proyecto>` | 🟠 |
| Ejemplos de docs **corren** | 🟡 No medido sistemáticamente | Solo se verificó compilación | 🟡 |
| Idioma consistente | 🟡 **Bilingüe real** | `LANGUAGE.md` + `LANGUAGE_Spanish.md` (210 K + 214 K), `PenguScriptGuide{English,Spanish}.md` (44 K + 45 K) | 🟢 |
| Deriva de versión | ❌ 13 archivos | `0.14.x`/`0.15.0`/`v0.6` en docs y docstrings | 📝 |
| `TODO`/`FIXME`/`HACK`/`XXX` en código propio | ✅ Bajo y disciplinado | 94 totales, **68 en headers de terceros** `std_c/*.h`; en código propio: 4 en `std/ffi.pengu` (sección "Known Limitations" **intencionada**), 1 cada uno en `whisper`/`seal`, 3 en `sqlite3.d.pengu`, 1 en `pengu_project.py:3648` (dentro de una **plantilla de código generado**) | ✅ |

### §13.1 Hallazgo D1 — Los 105 ejemplos de `LANGUAGE.md` medidos de verdad

El procedimiento correcto (que **no** es el del enunciado, ver §6.2) es extraer los bloques
` ```pengu ` y comprobarlos por proyecto:

> **Nota de método:** la cuenta de bloques debe hacerse con un **parser de fences por
> líneas**, no con una regex ```` ```pengu\n(.*?)``` ```` sobre todo el texto. `LANGUAGE.md`
> contiene al menos un bloque **indentado** (````  ```pengu ````, p. ej. en la línea 679), que la
> regex simple no reconoce como apertura y que desalinea el conteo. La medición original de esta
> auditoría dio 105 bloques; con el parser correcto son **104**, y el número de fallos 71, no 72.


```python
doc = pathlib.Path("LANGUAGE.md").read_text()
blocks = re.findall(r"```pengu\n(.*?)```", doc, re.S)   # 105 bloques
# por cada bloque: escribir en <proyecto>/src/main.pengu y ejecutar 'pengu check -c <proyecto>'
```

**Resultado (medido con un parser de fences por líneas, que es el correcto):**

```
LANGUAGE.md pengu-fenced blocks (correct count): 104
RESULTS: {'ok': 33, 'syntax': 28, 'sem': 43}
pass rate: 33/104 = 32%
```

**33 de 104 (32 %) pasan**. Los 71 restantes se clasifican así:

| Clase | Nº | ¿Es un defecto documental? | Ejemplos |
|-------|----|---------------------------|----------|
| **Fragmento sin contexto** (sentencia suelta, no un programa) | ~35 | ❌ No — es la convención habitual de un manual | `set counter += 1`, `if x > 0: return 1`, `for i from 0 to 10:` |
| **Declaración top-level** que `E0002` rechaza correctamente en un archivo suelto | ~18 | ❌ No — el ejemplo vive dentro de una función en contexto | `var x as int is 5`, `let z as int is (a + b) * 2 % 7` |
| **`: ...` como elipsis** de código omitido | 2 | ❌ No — es notación del manual | Bloques 53 y 65 (`weave sum shard T …:` seguido de `...`) |
| **Ejemplo marcado "# Invalid"** | 5 | ❌ No — el fallo es **el objetivo** del ejemplo | Bloques 99–103 |
| **Depende de un módulo de ejemplo inexistente** (`components.player`, `arca`) | 3 | ❌ No — módulos ilustrativos | Bloques 66, 96, 97 |
| **Usa `std` sin importarlo** o una función no importada | ~7 | 🟡 Menor — el ejemplo omite el `import` | `spark` sin `import std.spark`; `expect_eq_int`, `read_file`, `usleep` |
| **Contradice al lenguaje real** | **4** | ✅ **Sí, defecto documental** | Ver abajo |

**Los 4 defectos documentales reales:**

| Bloque | Código documentado | Error real | Defecto |
|--------|-------------------|-----------|---------|
| **15** | `weave describe with user as maybe User into string:` | `E0022 Type parameter 'User' can only be used within a generic declaration (shard)` | El ejemplo usa `User` como **rune concreta** pero el lenguaje la interpreta como parámetro de tipo. El ejemplo no compila tal como está escrito |
| **59** | `concept Iterabilis shard Self:` + `alias Item` | `E0000 unexpected 'alias'` | **Associated types documentados como existentes y no existen** (§1.2) |
| **28** | `enchanting Vec2:` + `weave ritual zero into Vec2:` | `E0022 Type parameter 'Vec2'` | Mismo problema que el 15: `Vec2` se resuelve como parámetro de tipo |
| **94** | `var position as raymath.Vector2 is with x is 400.0, y is 225.0` | `E0013 Field 'x' does not exist on Rune 'raymath.Vector2'` + `E0004 Undefined identifier 'position'` | Ejemplo del **patrón de binding C re-exportado** roto por §3.2 |

Dos de estos cuatro (28 y 94) son el mismo bug de resolución de tipos cualificados desde dos ángulos,
lo que refuerza que §3.2 es un bloqueante real y no un artefacto.

**Fix propuesto:** marcar los fragmentos como tales con un lenguaje de bloque distinto
(` ```pengu-fragment `), hacer que CI extraiga y compile **solo** los bloques completos, y arreglar
los 4 defectos reales.

### §13.2 Hallazgo D2 — Catálogo de errores: 10 de 59 filas no son fiables

Ya detallado en §2.2. Recapitulando el impacto documental: `LANGUAGE.md:3386-3455` es la **única
referencia de diagnóstico** del proyecto (tabla `Code | Exception Class | Semantic Condition | Help`),
y en ella:

- **5 filas** citan clases que no existen en ningún archivo Python.
- **5 filas** atribuyen el código a una clase que declara otro código distinto (una de ellas en
  contradicción directa con `tests/test_error_codes_uniqueness.py`).
- **24 códigos** que sí se emiten no tienen clase dedicada, así que su columna "Exception Class"
  dice `SemanticError (code="Exxxx")` — lo cual es honesto pero revela que el diseño de clases se
  abandonó a mitad de camino.
- La columna "Default Help / Note" es **aproximada**: el `help:` real de cada emisión difiere del
  documentado en varios casos (p. ej. `E0013` real: `"Remove 'x' or add it to rune 'X'."` frente al
  documentado `"Check field spelling or verify declared fields on the struct/union."`).

**Fix propuesto:** generar §22.2 y §22.3 desde `pengu_errors.py` + un registro declarativo de las
emisiones crudas, y añadir un test que falle si el doc y el código divergen.

### §13.3 Hallazgo D3 — ❌ REFUTADO: afirmaciones de seguridad en la documentación

| Documento | Afirmación textual | Realidad verificada |
|-----------|-------------------|---------------------|
| `LANGUAGE.md:3269` | *"**Async-signal-safe** crash handlers for `SIGSEGV` and `SIGABRT`"* | `pengu_runtime.h:406-412` usa `snprintf`, que no es async-signal-safe; el propio archivo lo admite en `:401-405` |
| `CHANGELOG.md:2780` | *"…de forma async-signal-safe (utilizando exclusivamente llamadas directas a `write(2)` / `_write`)"* | Igual: hay `snprintf` en el camino |
| `SECURITY.md:76-78` | *"a stale `libpengu_runtime.a` fails at compile time instead of corrupting memory"* | `nm build/lib/libpengu_runtime.a \| grep -i abi` → **vacío**; el `_Static_assert` compara constantes del codegen y del header, no el archivo |
| `.github/workflows/release.yml:76-77` | *"**verified**: `PENGU_TCC_SHA256` (or the default digest below) must match"* | **No hay digest por defecto**: `:85` lee una variable nunca definida en el repo, y `:97-99` solo imprime un `::notice::` |
| `extern_manifest.py:141` | *"=== All external C libraries verified. ==="* | Solo comprueba que los **directorios existen** (`:83-85`). No hay `hashlib` ni tabla de digests en el archivo |

### §13.4 Hallazgo D4 — 📝 Deriva de versión en 13 archivos

```bash
$ grep -rn "0\.14\.x\|0\.14\.0\|0\.15\.0\|v0\.6 " --include="*.md" . | grep -v extern | grep -v CHANGELOG
./AUDIT_RESPONSE.md
./docs/PERFORMANCE.md
./vscode-extension/README.md
./README_RELEASE.md
./PenguScriptGuideSpanish.md
./README.md
./PenguScriptGuideEnglish.md
./LANGUAGE_Spanish.md
./LANGUAGE.md
./ROADMAP_1.0.0.md

$ grep -n "v0\.1[0-9]" pengu_parser/pengu_parser.py pengu_lsp/__init__.py
pengu_parser/pengu_parser.py:92:    """LALR(1) parser for PenguScript v0.14.x using embedded grammar."""
pengu_lsp/__init__.py:1:"""PenguScript v0.6 Language Server Protocol Package."""
```

| Archivo | Afirmación | Real |
|---------|-----------|------|
| `PenguScriptGuideEnglish.md:3` | Cubre **0.14.x** | 0.16.0 |
| `PenguScriptGuideSpanish.md` | ídem | 0.16.0 |
| `pengu_parser.py:92` | *"parser for PenguScript **v0.14.x**"* | 0.16.0 |
| `pengu_lsp/__init__.py:1` | *"PenguScript **v0.6**"* | 0.16.0 |
| +9 archivos `.md` | `0.14.x`/`0.15.0` | 0.16.0 |

Existe `tests/test_version.py` que verifica la coherencia de `VERSION`, `FALLBACK_VERSION` y algunos
puntos, pero **no cubre los `.md` ni los docstrings**.

**Fix propuesto:** extender `tests/test_version.py` para escanear los `.md` de la raíz y los
docstrings de `pengu_parser`/`pengu_lsp` buscando patrones de versión y fallar en la deriva.

### §13.5 Hallazgo D5 — 🟡 Siete documentos de proceso histórico en la raíz

| Archivo | Bytes | Por qué sobra |
|---------|-------|---------------|
| `AUDIT_RESPONSE.md` | 32 474 | Respuesta a una auditoría anterior; su contenido está superado |
| `PRODUCTION_READINESS.md` | 57 194 | Estado de readiness de una versión anterior |
| `P1_PROGRESS.md` | 10 813 | Progreso de una fase terminada |
| `P2_PROGRESS.md` | 7 723 | Ídem |
| `CRITICALS_PROGRESS.md` | 6 407 | Ídem |
| `Plan.md` | 7 341 | Plan superado por `ROADMAP_1.0.0.md` |
| `roadmap.md` | 2 608 | Reemplazado por `ROADMAP_1.0.0.md`/`ROADMAP_2.0.md` |

Total: **~125 KB** de documentos de proceso que compiten por la atención del lector con
`README.md`. Detalle en `CLEANUP_PLAN.md` §1.

### §13.6 Documentación que **falta**

| Falta | Por qué importa |
|-------|-----------------|
| `CONTRIBUTING.md` | No hay guía para contribuir, ni cómo correr los tests, ni la política de estilo |
| `ARCHITECTURE.md` | Con 27 204 líneas de compilador y 5 207 en `pengu_project.py`, no hay un mapa de las fases (parse → collect → check → infer → codegen → cache) |
| `ERRORS.md` (generado) | El catálogo vive dentro de `LANGUAGE.md` §22 y está desincronizado; debería generarse |
| `docs/ABI.md` | `PENGU_ABI_VERSION` existe y se asserta, pero no hay documento que defina qué es la ABI, qué la rompe ni cómo se versiona |
| `docs/CROSS_COMPILATION.md` | `--target` es una feature real y no documentada |
| `MIGRATION.md` | No hay guía de migración entre versiones, pese a que la sintaxis cambió (0.10.0 eliminó `and`/`or` como separadores) |
| Referencia de API por módulo | **541 de 1463 (37 %)** nombres públicos de la stdlib no aparecen en ninguna doc |
| `docs/DIAGNOSTICS.md` con la tabla **generada** | Sustituiría §22.2 y eliminaría la clase de bug de §2.2 |

### §13.7 Documentación **duplicada**

| Duplicación | Detalle |
|-------------|---------|
| `LANGUAGE.md` ↔ `LANGUAGE_Spanish.md` (210 K ↔ 214 K) | Dos copias completas; mantenerlas sincronizadas es trabajo manual sin verificación |
| `PenguScriptGuide{English,Spanish}.md` (44 K ↔ 45 K) | Ídem |
| `ROADMAP_1.0.0.md` (65 K) ↔ `roadmap.md` (2 K) ↔ `Plan.md` (7 K) | Tres roadmaps con estados distintos |
| `README.md` (83 K) ↔ `README_RELEASE.md` (3 K) ↔ `PENGU_BUILD.md` (18 K) | Solapamiento en build/instalación |
| `PRODUCTION_READINESS.md` (57 K) ↔ `RELEASE_CHECKLIST.md` (4 K) ↔ `CRITICALS_PROGRESS.md` (6 K) ↔ `BENCHMARKS.md` (5 K) | Cuatro documentos de estado de release |
| `CHEATSHEET.md` (126 K) ↔ `LANGUAGE.md` §1-§23 | El cheatsheet reproduce ejemplos del manual; ya divergen en 3 nombres de función |
| `docs/FUZZING.md` ↔ `fuzz.yml` | El doc dice 72 h; el workflow dice 12 h (§14.4) |

**Recomendación de política:** un idioma canónico (inglés) y traducciones **generadas o marcadas como
no normativas**; un solo roadmap vivo; un solo documento de estado de release.

### §13.8 Derivación cruzada `docs` → código: comprobaciones puntuales

Además del catálogo de errores, se comprobaron afirmaciones concretas y puntuales de la
documentación contra el código:

| Afirmación | Documento | Verificación | Veredicto |
|-----------|-----------|--------------|-----------|
| "zero C compiler warnings" | `README.md:401` | Bundle de `atlas.pengu` (6601 líneas) con `-Wall -Wextra -Wshadow`: **0 warnings** | ✅ cierta para el bundle; ❌ para el runtime TU (§5.1) |
| "27 pure + 25 bindings" | varios | `ls std` → 27/25 exacto | ✅ cierta |
| "`pengu check` parsea y tipa cada módulo" | `pengu check --help` | Cierto con `-c`/`-e`; **falso** con posicional | 🟡 engañosa |
| "Async-signal-safe crash handlers" | `LANGUAGE.md:3269` | `snprintf` en el camino | ❌ REFUTADO |
| "Tombstones implementados" (implícito en changelog) | `CHANGELOG.md` | 6 sitios de sondeo + reutilización | ✅ cierta |
| "`--strict-c99` produce C99 portable" | `RELEASE_CHECKLIST.md:17` | 104 errores de `-pedantic-errors` | ❌ REFUTADO |
| "Nightly fuzz 72 h sin crash" | `RELEASE_CHECKLIST.md:27` | `fuzz.yml` default 12 h, timeout 13 h, sin trigger de release | ❌ REFUTADO |
| "MSVC verde" | `RELEASE_CHECKLIST.md:13` | No hay `cl.exe` en ningún workflow | ❌ REFUTADO |
| "Rangos `to` y `..`" | `LANGUAGE.md` | Ambos parsean | ✅ cierta (pero duplicidad, §9.3) |
| "`is present`/`is not present`/`is true`/`is false`" | `LANGUAGE.md` | Todos en el grammar | ✅ cierta |
| "Named arguments" | `LANGUAGE.md` | `named_arg` en el grammar | ✅ cierta |
| "Cache keyed by content hash" | `PENGU_BUILD.md` | `file_content_digest` (nunca mtime) | ✅ cierta |
| "`pengu fmt` aplica el standard style" | `pengu fmt --help` | Default 2 espacios vs 4 en toda la doc | ❌ REFUTADO (§10.2) |
| "`NO_COLOR=1` honoured" | `pengu --help:4538-4541` | Nadie lee `NO_COLOR` | ❌ REFUTADO |
| "`--quiet` suprime la salida" | `pengu --help` | No-op en `build` | ❌ REFUTADO |
| "`--target-compiler` selecciona el compilador" | `pengu build --help` | Solo cambia el dialecto | ❌ REFUTADO |

**Total: 8 afirmaciones refutadas en esta sección**, sumadas a las de §2.2, §5.2, §5.6, §13.3.

---

## §14. Runtime de build (`build_runtime.py`, `extern_manifest.py`, `make_release.py`, `pengu_tcc.py`)

> **Veredicto:** 🟡 **parcial** — el sistema de build es sofisticado (FHS + portable, TCC incluido,
> manifest de dependencias) pero **no verifica la integridad de nada que descarga**, y la cadena de
> release depende de un digest que no existe.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| Todas las bibliotecas externas compilan | 🟡 Mayormente | `build_runtime.py` construye PCRE2, libxml2, curl, mbedtls, zlib; el runtime se compila con flags de supresión (§5.1) | 🟡 |
| Todas tienen fallback al sistema (POSIX) | 🟡 Parcial | `pengu_parser/pengu_runtime.c` y `build_runtime.py` usan `#ifdef` para zlib/pcre2 del sistema | 🟡 |
| Manifest con versiones pinneadas | ✅ **Sí** | `extern_manifest.py:16-43` fija versiones exactas en las URLs (p. ej. `curl-8.21.0`, `mbedtls-4.2.0`) | ✅ |
| **Verificación de integridad del manifest** | ❌ **No existe** | Sin `hashlib`, sin tabla de digests, sin firmas en todo el archivo | 🟠 |
| `make_release.py` produce artefactos reproducibles | 🟡 NO VERIFICADO | No se ejecutó un release completo (requiere descargar ~329 MB de `extern/`) | 🟡 |
| TinyCC se descarga con verificación SHA-256 | ❌ **REFUTADO** | `pengu_tcc.py:118-152` `_download_windows_tcc`: `urlopen` → `zipfile.ZipFile(...).extractall(dest_dir)`, **cero verificación** | 🟠 |
| Layout FHS funciona | ✅ | `pengu_paths.py` (11 450 B) implementa la búsqueda | ✅ |
| Layout portable funciona | ✅ | Verificado por el modo script (`~/.cache/pengu/scripts`) | ✅ |
| Extracción de tarballs endurecida | 🟡 Mitigado por accidente | `extern_manifest.py:124` `tar.extractall(path=…)` — en Python 3.14.7 el default es `filter='data'` | 🟢 |
| `zipfile.extractall` protegido | ❌ No | `pengu_tcc.py:143` sin `filter` (no aplica a zip; sí aplica la validación de rutas) | 🟢 |
| El runtime se construye con un flag que oculta 24 errores | ❌ | `build_runtime.py:1195-1204` (§5.1) | 🟠 |
| Warning de macros redefinidas | 🟢 3 por compilación | `build_runtime.py:1198-1201` pasa `-DPCRE2_STATIC -DLIBXML_STATIC -DCURL_STATICLIB` y `pengu_runtime.c:12-15,29` los redefine sin `#ifndef` | 🟢 |

### §14.1 Hallazgo BLD1 — 🟠 Descargas sin verificación de integridad, con mensaje que dice "verified"

```python
# extern_manifest.py — no hay 'import hashlib' ni tabla de digests en todo el archivo
# :123-124
with tarfile.open(...) as tar:
    tar.extractall(path=target_dir)

# :141 — el mensaje final
print("=== All external C libraries verified. ===")
```

Lo único que `:83-85` comprueba es que **los directorios existan**. Y `make_release.py:96-100` llama:

```python
download_and_extract_externs(ROOT_DIR / "extern")     # force=False por defecto
```

Es decir: un `extern/` preexistente —incluido uno **restaurado desde la caché de CI**
(`.github/actions/setup-pengu/action.yml:85-95` cachea `extern`)— se acepta sin comprobar nada.
`make_release.py` corre **dentro** de `release.yml`, después de esa restauración de caché.

**Impacto:** un mirror comprometido o una entrada de caché envenenada llega a los archivos publicados.
`SECURITY.md` tiene una sección de cadena de suministro pero **no hay ningún gate de integridad
detrás de ella**.

**Fix propuesto:** añadir `sha256` a cada entrada de `MANIFEST`, verificar el stream antes de extraer,
pasar `force=True` en la ruta de release y usar `tarfile.extractall(filter="data")`.

### §14.2 Hallazgo BLD2 — ❌ REFUTADO: el digest "por defecto" de TCC no existe

```yaml
# .github/workflows/release.yml:76-77
# *verified*: PENGU_TCC_SHA256 (or the default digest below) must match

# :85
$expected = $env:PENGU_TCC_SHA256        # variable nunca definida en el repo
```

```bash
$ grep -rn "PENGU_TCC_SHA256" .github/ pengu_tcc.py make_release.py
.github/workflows/release.yml:76:# ... PENGU_TCC_SHA256 ...
.github/workflows/release.yml:85:  $expected = $env:PENGU_TCC_SHA256
.github/workflows/release.yml:97:    ::notice::TinyCC digest ... (set PENGU_TCC_SHA256 to enforce it)
```

La variable solo se **menciona**; nunca se define. Y `:97-99` únicamente imprime un `::notice::`. En
Linux/macOS el TCC se compila desde fuentes (sin descarga), pero la ruta prebuilt de Windows
(`pengu_tcc.py:_download_windows_tcc`) descarga y extrae **sin verificación alguna**.

**Fix propuesto:** fijar un digest por defecto como constante y fallar duro si no coincide.

### §14.3 Hallazgo BLD3 — 🟡 Sin análisis estático de **seguridad** en el build

```bash
$ grep -rn "codeql\|scorecard\|semgrep\|trivy\|snyk" .github/
(vacío)
```

**Precisión (Fase 1):** lo que falta es SAST/SCA de **seguridad** (CodeQL, semgrep, trivy, Snyk).
Afirmar "0 análisis estático" era impreciso: `ci.yml` tiene 10 gates que ejecutan tests estáticos y
en la Fase 1 se añadió `ruff check --select F821,E9`, que **sí** es análisis estático (y encontró dos
violaciones reales en `tests/conftest.py`). El hueco concreto es el de seguridad y cadena de
suministro.

Además todas las actions están fijadas a tags mutables
(`actions/checkout@v4`, `cache@v4`, `upload-artifact@v4`, `download-artifact@v4`, `setup-node@v4`,
`setup-python@v5`), no a SHAs — lo que es en sí mismo un vector de cadena de suministro.

**Fix propuesto:** añadir CodeQL (Python + C) y fijar las actions a SHA de commit.

### §14.4 Hallazgo BLD4 — ❌ REFUTADO: los presupuestos de fuzzing de 72 h son imposibles

| Documento | Afirma |
|-----------|--------|
| `docs/FUZZING.md:69` | *"Release branch / manual \| **72 hours** per harness"* |
| `RELEASE_CHECKLIST.md:27` | *"Nightly fuzz job: **72 h** without a crash on any harness"* |
| `.github/workflows/fuzz.yml:23` | `default: '43200'` → **12 h** |
| `.github/workflows/fuzz.yml:39` | `timeout-minutes: 780` → **13 h** |
| Triggers de `fuzz.yml` | No hay trigger de rama `release` ni ruta de 72 h |

Además, **GitHub-hosted jobs tienen un tope duro de 6 h de ejecución**, así que incluso el
`timeout-minutes: 780` (13 h) es inalcanzable. Ver
[GitHub Actions limits](https://docs.github.com/en/actions/reference/limits).

**Fix propuesto:** declarar el presupuesto real (≤6 h por harness, repartido en shards) o fragmentar
la ejecución en varios jobs.

### §14.5 Hallazgo BLD5 — 🟡 Higiene de workflows

| Hallazgo | Evidencia |
|----------|-----------|
| `fuzz.yml:83` conserva `python build_runtime.py --headers-only \|\| true` pese a que `:9` afirma que "`\|\| true` ya no oculta una instalación rota de requirements" | contradicción interna |
| `release.yml:131` corre la suite completa **sin** `--timeout` | solo el tope del job (90 min) |
| ASan/UBSan + valgrind son **solo Linux** (`sanitizers.yml:28,85`) | `docs/PERFORMANCE.md:343-348` lo documenta honestamente ✅ |
| `bench.yml` nunca se dispara en PRs | su comentario "never block a PR" (`:11`) es cierto pero vacío |
| `dependabot.yml` cubre **todos** los ecosistemas presentes (github-actions + pip + npm) | ✅ correcto |

### §14.6 La cadena de release depende de un evento que GitHub no emite

`ci.yml:205-221` crea y empuja el tag con el `GITHUB_TOKEN` por defecto, y `:222-225` afirma:

> *"Pushing the tag triggers release.yml"*

La regla documentada de GitHub es que los eventos disparados por el `GITHUB_TOKEN` del repositorio
**no crean nuevas ejecuciones de workflow** (excepto `workflow_dispatch`/`repository_dispatch`). Ver
[GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token) y
[esta discusión](https://github.com/orgs/community/discussions/154396).

**Estado: 🟡 NO VERIFICADO localmente** (requiere un repositorio vivo) pero **alta confianza por
documentación de plataforma**. El gate de regresión `tests/test_ci_workflows.py:119` solo comprueba
que exista el literal `v*` en los triggers, así que **no puede detectar este problema**.

**Fix propuesto:** usar un PAT o GitHub App para el push, o lanzar `release.yml` explícitamente con
`workflow_dispatch` desde el job del tag.

---

## §15. CI/CD (`.github/workflows/`, `.github/actions/`, `.github/dependabot.yml`)

> **Veredicto:** 🟠 **con problemas graves** — corregido en la Fase 1: el CI está **mucho más
> completo de lo que esta sección describía originalmente**. `ci.yml` tiene **gates nombrados por
> fase** (FASE 1…FASE 7), una matriz de ABI que **compila y ejecuta** C, y un gate que testea los
> propios workflows. El problema real no es la falta de gates sino la **calidad** de algunos de
> ellos: varios aprueban una propiedad inspeccionando texto (§0.5) y el gate llamado "Strict
> grammar" era vacuo por construcción.

> **❌ CORRECCIÓN (Fase 1).** La versión original de esta sección afirmaba *"no existe análisis
> estático"* y describía un CI de 5 workflows sin gates por fase. **Ambas cosas eran imprecisas.**
> `ci.yml` contiene, entre otros:
>
> | Gate | Qué ejecuta | ¿Real? |
> |------|-------------|--------|
> | Toolchain smoke test | `python scripts/smoke.py` | ✅ |
> | Standard library formatting gate | `python pengu_project.py fmt --check std/` | ✅ (verificado: rc=0) |
> | Strict grammar & parser validation (FASE 1) | `test_grammar_strict.py`, `test_fase1_e2e.py` | 🟡 **era vacuo** — ver B11 |
> | C99 portability & ABI gate (FASE 2) | `test_c99_portability.py`, `test_attributes_msvc.py`, `test_abi_layout.py`, `test_bounds_flag_independence.py` | 🟡 parcial (solo texto/`_PROG`) |
> | Tooling gate (FASE 3) | 9 archivos de test (bind, assets, JSON, LSP, fmt, doc, cross-compile) | ✅ |
> | Ecosystem gate (FASE 4) | 9 archivos (semver, lockfile, deps, vendor, manifest, templates) | ✅ |
> | Safety & supply-chain gate (FASE 5) | 7 archivos (bounds, overflow, deprecation, supply-chain, hardening, fuzz) | ✅ |
> | **ABI layout matrix** (Phase 5 / 5.7.f) | **compila** `tests/abi/test_abi_layout.c` con `-Wall -Wextra` y lo **ejecuta** | ✅ **compila y ejecuta** |
> | DX gate (FASE 6) | `test_phase6_bugfixes.py`, `test_benchmarks.py`, `test_phase6_scope.py` | ✅ |
> | CI/CD gate (FASE 7) | `test_ci_workflows.py` (49 invariantes) | ✅ |
> | Run full test suite | `pytest tests` | ✅ |
>
> Es decir: **sí existe** infraestructura de gates, y una de ellas ya cumple la regla C1 (la matriz
> de ABI compila y ejecuta). Lo que faltaba era un gate para nombres no definidos —que es un crash,
> no un estilo— y un gate de gramática que realmente midiera algo. Ambos se añadieron en la Fase 1.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| Los 5 workflows "mejorados" funcionan | 🟡 4 sí, `sanitizers` rojo | §11.3; los otros 4 corren | 🟠 |
| `permissions` declarados | ✅ Mejorados y granulares | Aplicado en el commit `8967d6f` | ✅ |
| Gates nombrados por fase en `ci.yml` | ✅ **Existen** (FASE 1–7 + matriz ABI) | ❌ REFUTADO que faltaran | ✅ |
| Gate que **compila y ejecuta** C | ✅ **Matriz de ABI** (`tests/abi/test_abi_layout.c`) | `ci.yml` paso "ABI layout matrix" | ✅ |
| Gate real de estrictez del grammar | 🟡 **Era vacuo**; corregido en Fase 1 | `assert len(recorded) == 0`; medido: 0 warnings con 188 conflictos | 🟠 |
| Gate de análisis estático (nombres no definidos) | ❌ Ausente; **añadido en Fase 1** | `ruff check --select F821,E9`; encontró 2 violaciones reales en `tests/conftest.py` | ✅ (Fase 1) |
| Gate que testea los propios workflows | ✅ `tests/test_ci_workflows.py` (49 invariantes) | — | ✅ |
| `msvc.yml` | ❌ **Ausente** | 0 usos de `cl.exe`; `ci.yml:96-97` hardcodea `CC_BIN="gcc"` en Windows | 🟠 |
| `tcc.yml` | ❌ Ausente | Cubierto solo por `test_c99_portability.py` sobre `_PROG` sin imports | 🟠 |
| `compliance.yml` | ❌ Ausente | No hay corpus canónico del que hablar (§11.2) | 🟠 |
| `migrate.yml` | ❌ Ausente | No hay tests de migración (§11.2) | 🟡 |
| `release-verify.yml` | ❌ Ausente | No hay job que verifique los artefactos publicados | 🟡 |
| `nightly.yml` | ❌ Ausente | No hay ejecución nocturna programada más allá del `schedule` de fuzz | 🟡 |
| `cross-compile.yml` | ❌ Ausente | `--target` no se prueba nunca | 🟠 |
| `codeql.yml` | ❌ **Ausente** | `grep codeql .github/` → vacío | 🟠 |
| `dependabot.yml` | ✅ **Completo** | github-actions + pip + npm; cubre todos los manifiestos presentes | ✅ |
| Caché de runtime | ✅ Bien, pero **confía** en lo cacheado | `.github/actions/setup-pengu/action.yml:85-95` cachea `extern`, que luego no se verifica (§14.1) | 🟡 |
| Actions fijadas a SHA | ❌ No, a tags mutables | `checkout@v4`, `cache@v4`, `upload-artifact@v4`, `setup-python@v5`, `setup-node@v4` | 🟡 |
| Traspaso tag → release | ❌ Depende de un evento que `GITHUB_TOKEN` no emite | §14.6 | 🟠 |
| Matriz real de compiladores | gcc(Linux) / clang-o-gcc(macOS) / **MinGW**(Windows) | `ci.yml:42-50`, `:96-97` | 🟡 |

### §15.1 Inventario real de workflows

| Workflow | Nombre | Triggers | Estado |
|----------|--------|----------|--------|
| `ci.yml` | CI (Windows / Linux / macOS) | push/PR + auto-tag | ✅ verde |
| `bench.yml` | bench | `workflow_dispatch` + schedule | ✅ verde, nunca en PR |
| `fuzz.yml` | fuzz | `workflow_dispatch` + schedule | ✅ verde |
| `release.yml` | Build and Publish Releases | tag `v*` + dispatch | 🟡 NO VERIFICADO (nunca corrió por tag) |
| `sanitizers.yml` | Sanitizers | push/PR + schedule | 🔴 **rojo** |

Y una action compuesta: `.github/actions/setup-pengu/action.yml`.

### §15.2 Hallazgo CI1 — 🔴 Tres gates verdes sobre código roto

Este es el hallazgo estructural más importante de §15 y merece repetición porque explica cómo el
proyecto llegó a 0.16.0 con bloqueantes abiertos:

| Gate | Qué **cree** que prueba | Qué prueba en realidad | Bug que deja pasar |
|------|------------------------|------------------------|--------------------|
| `test_cli_strict_c99.py:50` | "el C estricto es portable" | Ausencia de 2 cadenas en un texto | §4.1 (13 errores duros de gcc) |
| `test_c99_portability.py` (5 tests) | ídem | Compila un programa de 20 líneas **sin imports** | §4.1 |
| `test_error_codes_uniqueness.py` | "los códigos de error son únicos" | Solo `kwargs.setdefault`, ignora 24 emisiones crudas | §2.3 (`E0035` × 4 significados) |
| `tests/test_attributes_msvc.py:39` | "MSVC funciona" | Compara **texto generado** | §5.1 (el runtime no compila con MSVC) |
| `ci.yml:96-97` | "Windows = MSVC" | `CC_BIN="gcc"` (MinGW) | idem |
| `sanitizers.yml:58-70` | "el leak queda visible sin romper CI" | Ejecuta 2 veces, la 2ª sin deselect | §11.3 (job rojo) |
| `test_ci_workflows.py:119` | "el traspaso tag→release funciona" | Existe el literal `v*` en los triggers | §14.6 |

**Regla propuesta para 1.0:** ningún gate puede aprobar una propiedad inspeccionando **texto**; debe
**compilar**, **ejecutar** o **medir**. Añadir a `CONTRIBUTING.md` y hacerlo cumplir en revisión.

### §15.3 Hallazgo CI2 — 🟠 No existe MSVC, aunque la matriz lo insinúe

| Evidencia | Detalle |
|-----------|--------|
| `build_runtime.py:92,597` | Solo selecciona `gcc`/`clang`/`cc`; **ninguna rama `cl.exe`** |
| Todas las líneas de compilación | Pasan flags GCC-only (`-Wno-…`, `-Wall`, `-std=`, `-I`) |
| `ci.yml:96-97` | `CC_BIN="gcc"` hardcodeado para Windows |
| `tests/test_attributes_msvc.py:39` | Genera texto con `target_compiler="msvc"`; **nunca invoca un compilador** |
| `RELEASE_CHECKLIST.md:13` | Afirma MSVC verde |

**La matriz real es gcc(Linux) / clang-o-gcc(macOS) / MinGW(Windows).** No es "gcc/clang, MSVC,
MinGW" como sugiere la documentación de release.

**Fix propuesto:** o eliminar la reivindicación MSVC de `RELEASE_CHECKLIST.md`, o añadir un job
`windows-latest` + `cl.exe` — que inmediatamente tropezará con §5.1 y exigirá
`-DMBEDTLS_ALLOW_PRIVATE_ACCESS` más la eliminación de los `-Wno-*`.

### §15.4 ✅ REFUTADO — dos hallazgos de la auditoría anterior que resultaron falsos

El encargo pedía específicamente verificar estas dos reivindicaciones heredadas:

| Reivindicación heredada | Veredicto | Evidencia |
|------------------------|-----------|-----------|
| *"`bench.yml` está roto en Windows"* (tal cual) | **❌ REFUTADO tal como se formuló** | El workflow funciona; se endureció igualmente por prudencia. Ya estaba marcado como falso en la auditoría previa y **se confirma falso** |
| *"`ci.yml`/`release.yml` no tienen `permissions`"* | **❌ REFUTADO en su forma fuerte** | Era un problema de **granularidad**, no de ausencia; el commit `8967d6f` lo mejoró. La afirmación "sin permissions" es falsa |

Ambas estaban ya señaladas como refutadas en el encargo; esta auditoría las **re-verifica como
falsas** y no las reintroduce.

### §15.5 Lo que el CI hace bien (✨ UNDERSELL)

Además de lo ya reconocido (los 5 workflows existen, `permissions` granulares, `dependabot` completo):

- **La caché de runtime con digest** (`setup-pengu/action.yml`) evita recompilar PCRE2/curl/mbedtls
  en cada job; es una decisión de ingeniería correcta para un CI de C.
- **El job de Windows existe de verdad** (MinGW), lo que ya detecta romper la portabilidad POSIX.
- **`sanitizers.yml` corre ASan/UBSan y valgrind** en Linux, y `docs/PERFORMANCE.md:343-348`
  documenta honestamente que el leakcheck no cubre otras plataformas. Es una limitación declarada,
  no ocultada.
- **`fuzz.yml` existe y usa `workflow_dispatch` con presupuesto configurable**, lo que permite
  lanzar campañas manuales — simplemente el número documentado (72 h) no es alcanzable.
- **`tests/test_ci_workflows.py` existe**: hay un test que vigila los propios workflows. Es una
  práctica poco común y valiosa, aunque su alcance actual sea superficial.
- **`dependabot.yml` cubre exactamente los tres ecosistemas presentes** y ninguno más: correcto.

---

## §16. Seguridad y estabilidad

> **Veredicto:** 🟡 **parcial** — hay más infraestructura de seguridad de la que cabría esperar en
> 0.16 (lockfile con checksums, gate de confianza para scripts de build, sandbox de preprocesador,
> `--release-unsafe`, `--deny-deprecated`), pero **varios mecanismos tienen escapes silenciosos** y
> `SECURITY.md` contiene al menos una afirmación refutada.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| `SECURITY.md` realista | 🟡 Mayormente, con 1 refutación | §5.6: *"a stale `libpengu_runtime.a` fails at compile time"* → **falso** | 🟠 |
| `pengu verify` funciona | ✅ | `no pengu.lock found; run pengu build first.` (rc=1, mensaje accionable) | ✅ |
| Sandbox del preprocesador (`bwrap`) | 🟡 NO VERIFICADO | Requiere `bwrap` instalado y un caso de build script malicioso | 🟡 |
| Gate de confianza para `build.py`/`build.sh`/`Makefile` | 🟡 Existe, no verificado end-to-end | `pengu add --trust` / `pengu update --trust` existen como flags explícitos | 🟡 |
| `pengu.lock` con checksums funciona | ❌ **Verificación salteable en silencio** | `pengu_lock.py:120` guarda `sha256=""` si `hash_trees` es falso; `:211` exige que **ambos** hashes sean no vacíos | 🟠 |
| `pengu vendor` funciona offline | ✅ | `Vendored 0 dependency(ies)` con dep set vacío; 🟡 no probado con deps reales | 🟡 |
| Sanitizers en CI | ✅ Sí, ❌ job rojo | §11.3 | 🔴 |
| Descarga de dependencias verificada | ❌ No | §14.1 | 🟠 |
| TCC descargado verificado | ❌ No | §14.2 | 🟠 |
| Análisis estático de seguridad | ❌ No | §14.3 | 🟠 |
| Crash handler robusto | 🟡 Parcial | Solo `SIGSEGV`/`SIGABRT` vía `signal()`, no `sigaction` (§5.5) | 🟡 |
| `--release-unsafe` documentado | 🟡 | Existe el flag y está en la cache key; 🟡 qué desactiva exactamente no está documentado en un solo sitio | 🟡 |
| `--deny-deprecated` | ✅ | Convierte `W0006` en error; en la cache key | ✅ |

### §16.1 Hallazgo SEC1 — 🟠 El lockfile se puede saltar la verificación sin aviso

```python
# pengu_lock.py:120
sha256=compute_tree_hash(path) if (hash_trees and path) else ""

# pengu_lock.py:211
if check_hashes and e.sha256 and a.sha256 and e.sha256 != a.sha256:
    ...
```

La condición exige que **ambos** hashes sean no vacíos. Si el lockfile se generó con `hash_trees`
desactivado (o la entrada no tiene path), `e.sha256 == ""` y **la comprobación no ocurre**. No hay
warning, ni error, ni indicación de que la verificación se omitió.

Además `compute_tree_hash` (`:71-89`) **ignora** `build/`, `.git`, `.venv`, `node_modules` y los
directorios que empiezan por punto (`_IGNORED_DIRS`, `:41`), y sustituye archivos ilegibles por
`b"<unreadable>"` — así que dos árboles que difieren solo en un directorio ignorado tienen el mismo
hash.

**Impacto:** un lockfile puede aparentar verificación de integridad y no estar verificando nada. En un
proyecto que vende "ownership determinista" y `pengu verify` como garantía, esto es una promesa
incumplida.

**Fix propuesto:** tratar un digest vacío como **fallo de verificación**, guardar y verificar el
conjunto de directorios ignorados, y no sustituir archivos ilegibles por un marcador.

### §16.2 Hallazgo SEC2 — 🟡 Cobertura de señales del crash handler

`pengu_runtime.h:464-465` captura solo `SIGSEGV` y `SIGABRT`, y con `signal()` en lugar de
`sigaction`. `SIGFPE` (división por cero, activa porque el perfil debug compila con `-ftrapv`),
`SIGILL` y `SIGBUS` no producen volcado de frames. En Windows solo `SetUnhandledExceptionFilter`.

Síntoma visible en el CLI (ya citado): `pengu eval "1/0"` sale con código **248** sin imprimir nada.

**Fix propuesto:** `sigaction` + `SIGFPE`/`SIGILL`/`SIGBUS`, y mapear `128+señal` en el CLI.

### §16.3 Lo que la seguridad hace bien (✨ UNDERSELL)

- **El lockfile existe y usa SHA-256 de árbol** (no mtime): `compute_tree_hash` recorre y hashea
  contenidos, lo cual es el enfoque correcto.
- **`--deny-deprecated` y `--release-unsafe` son flags explícitos** y ambos entran en la clave de
  caché, así que un build "unsafe" no puede reutilizar el binario de uno seguro.
- **`pengu verify` devuelve un mensaje accionable** y rc=1 cuando falta el lockfile.
- **Hay un gate de confianza explícito** (`--trust`) para re-ejecutar scripts de build de
  dependencias, en vez de confiar por defecto.
- **La `PENGU_ABI_VERSION` se asserta en cada bundle** y está correctamente envuelta en
  `#if __STDC_VERSION__ >= 201112L` para no romper C99.
- **El reconocimiento del leak es honesto**: `docs/PERFORMANCE.md:349-358` lo documenta y
  `tests/test_string_composition_suite.py` lo fija con `xfail(strict=True)` en vez de silenciarlo.

---

## §17. Rendimiento

> **Veredicto:** 🟡 **parcial** — los números medidos son buenos y las afirmaciones de
> `BENCHMARKS.md` son mayormente honestas, pero **las cifras estrella de TCC no aplican a ningún
> programa que importe `std`**, y el DCE ahorra menos de lo que sugiere.

| Aspecto | Estado | Evidencia | Severidad |
|---------|--------|-----------|-----------|
| Los números de `BENCHMARKS.md` siguen válidos | 🟡 Parcialmente | Los de gcc sí; los de TCC no para programas con `std` | 🟡 |
| La caché de scripts funciona | ✅ **Sí y bien** | `cache hit`/`cache miss` con clave content-hash; `pengu gc` gestiona 169 entradas | ✅ |
| El DCE ahorra tanto como se dice | 🟡 No medido en esta auditoría | El shim `pengu_dce.py` y la implementación existen; `is_prunable_module` probado | 🟡 |
| TCC es tan rápido como se dice | ❌ **No para programas reales** | TCC falla en `__auto_type` y cae al fallback de gcc | 🟠 |
| Regresiones desde la última auditoría | 🟡 NO VERIFICADO | No hay baseline histórico de tiempos en el repo | 🟡 |
| El frame tracing cuesta 5.5× | 🟡 NO VERIFICADO | El número viene de `BENCHMARKS.md`; no se reprodujo el microbenchmark | 🟡 |
| `pengu check` en 2000 líneas | ✅ 1462 / 1463 / 1468 ms | Constante, lineal y aceptable | ✅ |
| `pengu build` en 2000 líneas | ✅ 2058 ms en frío / 875 ms en caliente | — | ✅ |
| Suelo de arranque | ✅ ~170 ms | Dominado por el intérprete Python + Lark, no por el tamaño del programa | ✅ |
| Benchmarks sobre la stdlib | ❌ **Cero** | `benches/` no importa ni un `std.` | 🟡 |

### §17.1 Hallazgo PERF1 — 🟠 Las cifras de TCC no aplican a programas reales

`docs/PERFORMANCE.md` §10 publica cifras tipo *"C compile + link (TCC vs gcc) — 19 ms (TCC)"* y
*"0.66 s (TCC) primera ejecución"*. Pero la medición real de un programa que importa dos módulos de
la stdlib:

```bash
$ pengu run h.pengu            # importa std.spark + std.seal
[pengu] development compiler failed; retrying with gcc
   Finished in 6.50s

$ tcc -c h.c -I build/include
/tmp/audit/.:867: error: '__auto_type' undeclared
```

El bundle por defecto usa `__auto_type`, que el TCC incluido (0.9.28rc) **no soporta**. `PERFORMANCE.md`
§4 documenta el fallback, pero §10 publica las cifras sin advertir que solo valen para bundles que
TCC acepta. Para cualquier programa que importe `std`, la ruta de primera ejecución paga
**un intento fallido de TCC + la compilación con gcc (~400 ms)**, muy lejos de 19 ms.

**Fix propuesto:** emitir `__typeof__(expr)` en lugar de `__auto_type` (TCC acepta `typeof`), y
re-medir `PERFORMANCE.md` §10 con un programa que importe `std`.

### §17.2 Los números que sí se sostienen

| Medición | Valor | Comando |
|----------|-------|---------|
| `pengu check` en 2024 líneas | 1462 / 1463 / 1468 ms | 3 ejecuciones |
| `pengu check --json` | `duration_ms: 1186.02` | — |
| `pengu build` frío / caliente | 2058 ms / 875 ms | — |
| `pengu test` | 2030 ms | — |
| `pengu check` en 6 líneas | 170 ms | suelo de arranque |
| `pengu time` (fases) | resolve 174.4 ms, parse+check 1.2 ms, codegen 1.2 ms, cc 60.8 ms, run 12.8 ms | — |
| Suite completa de tests | 910.67 s para 2089 tests | — |
| Warnings de C en bundle real | **0** (`atlas.pengu`, 6601 líneas, `-Wall -Wextra -Wshadow`) | ✅ |

**Observación:** el compilador es **lineal y predecible**, con un suelo de arranque de ~170 ms
dominado por Python/Lark. La optimización de mayor retorno no es el codegen (1.2 ms para 2024
líneas) sino el arranque del intérprete, y eso solo se resuelve con el binario congelado de
PyInstaller que `make_release.py` ya produce.

### §17.3 ✨ UNDERSELL — la arquitectura de caché es mejor de lo documentado

Dos niveles de caché que funcionan y no se venden:

1. **Tablas LALR serializadas** con `grammar_digest` (sha256 sobre grammar + opciones + versiones de
   Lark/Python), con **fallback si el cache está corrupto**: `PenguParser.__init__` captura la
   excepción y reintenta sin `cache`. Esto reduce cada comando de 2-3 s a ~170 ms.
2. **Binarios de script** en `~/.cache/pengu/scripts/<key>` con clave que incluye versión, cc, perfil,
   defines, links, cflags, entry, **sha256 de cada módulo**, digest del runtime header, DCE,
   `release-unsafe`, `PENGU_CFLAGS`, `strict-c99`, `target_compiler` y `target` — y `pengu gc` para
   gestionarla.

Es infraestructura de nivel producción. `PENGU_BUILD.md` la describe, pero `README.md` apenas la
menciona.

### §17.4 Nota sobre la fidelidad de `BENCHMARKS.md`

Debe decirse en positivo: `BENCHMARKS.md` es **el documento más honesto del repositorio**. Incluye
secciones donde reconoce explícitamente que un objetivo **no** se cumple, y
`docs/PERFORMANCE.md:343-358` documenta el leak de temporales de expresión y la limitación del
leakcheck por plataforma. Esa cultura de "no reivindicar lo que no se cumple" existe en este
proyecto — el problema de esta auditoría es que **no se aplicó al catálogo de errores, a la guía de
estilo ni al checklist de release**.

---

## §18. Estado real vs reivindicado

> **Veredicto:** 🟠 **con problemas graves** — se han verificado **23 reivindicaciones refutadas** y
> **9 subestimadas**. La conclusión central: la documentación **vende de menos el CLI, el LSP y la
> caché**, y **vende de más la portabilidad C, la seguridad y la madurez del formato**.

### §18.1 Tabla completa: cada afirmación vs realidad

| # | Afirmación | Fuente | Realidad verificada | Veredicto |
|---|-----------|--------|---------------------|-----------|
| 1 | *"Async-signal-safe crash handlers"* | `LANGUAGE.md:3269` | `snprintf` en el camino; el propio archivo lo admite | ❌ **REFUTADO** |
| 2 | *"…async-signal-safe (utilizando exclusivamente `write(2)`)"* | `CHANGELOG.md:2780` | idem | ❌ **REFUTADO** |
| 3 | *"a stale `libpengu_runtime.a` fails at compile time"* | `SECURITY.md:76-78` | `nm \| grep -i abi` → vacío; el assert compara codegen↔header | ❌ **REFUTADO** |
| 4 | *"PENGU_TCC_SHA256 (or the default digest below) must match"* | `release.yml:76-77` | No existe digest por defecto; la variable nunca se define | ❌ **REFUTADO** |
| 5 | *"=== All external C libraries verified. ==="* | `extern_manifest.py:141` | Solo comprueba existencia de directorios | ❌ **REFUTADO** |
| 6 | *"--strict-c99 C99 portability gate"* | `RELEASE_CHECKLIST.md:17` | 13 errores duros de gcc + 104 statement-expressions | ❌ **REFUTADO** |
| 7 | *"MSVC"* en la matriz de CI | `RELEASE_CHECKLIST.md:13` | `CC_BIN="gcc"` (MinGW); cero `cl.exe` | ❌ **REFUTADO** |
| 8 | *"Nightly fuzz job: 72 h sin crash"* | `RELEASE_CHECKLIST.md:27` | `fuzz.yml` default 12 h, timeout 13 h; GH limita a 6 h | ❌ **REFUTADO** |
| 9 | *"72 hours per harness"* | `docs/FUZZING.md:69` | idem | ❌ **REFUTADO** |
| 10 | *"Pushing the tag triggers release.yml"* | `ci.yml:222-225` | `GITHUB_TOKEN` no dispara workflows | ❌ **REFUTADO** (alta confianza; no ejecutable localmente) |
| 11 | Clase `DanglingSliceError` (`E0051`) | `LANGUAGE.md:3451` | 0 referencias en `*.py` | ❌ **REFUTADO** |
| 12 | Clase `DuplicateConstantError` (`E0053`) | `LANGUAGE.md:3453` | 0 referencias | ❌ **REFUTADO** |
| 13 | Clase `AmbiguousStructInitError` (`E0054`) | `LANGUAGE.md:3454` | 0 referencias | ❌ **REFUTADO** |
| 14 | Clase `StaticArrayError` (`E0055`) | `LANGUAGE.md:3455` | 0 referencias | ❌ **REFUTADO** |
| 15 | Clase `ErrorLiteralContextError` (`E0058`) | `LANGUAGE.md:3458` | 0 referencias | ❌ **REFUTADO** |
| 16 | `E0047` = `DuplicateConceptBindingError` | `LANGUAGE.md:3443` | El test del repo afirma `E0052` | ❌ **REFUTADO** |
| 17 | `E0014/E0018/E0020/E0045` = `TypeMismatchError` | `LANGUAGE.md` §22.2 | `TypeMismatchError` declara `E0005` | ❌ **REFUTADO** |
| 18 | `--no-color` / `NO_COLOR=1` desactiva ANSI | `pengu --help` | Nadie lee `NO_COLOR` | ❌ **REFUTADO** |
| 19 | `-q/--quiet` suprime la salida | `pengu --help` | No-op en `build` | ❌ **REFUTADO** |
| 20 | `pengu fmt` aplica "the standard style" | `pengu fmt --help` | Default 2 espacios vs **4** en toda la doc y la stdlib | ❌ **REFUTADO** |
| 21 | `--target-compiler` selecciona el compilador | `pengu build --help` | Solo cambia el dialecto de C | ❌ **REFUTADO** |
| 22 | `compress`/`decompress` en `seal` | `CHEATSHEET.md:2388` | Reales: `zlib_compress`/`zlib_decompress` | ❌ **REFUTADO** |
| 23 | loom `product`/`max`/`min` | `CHEATSHEET.md:2391` | Reales: `product_num`/`max_int`/`min_int` | ❌ **REFUTADO** |

### §18.2 Reivindicaciones del **enunciado de la auditoría** que resultaron falsas

Debe quedar constancia: el encargo contenía suposiciones que la verificación refutó. Corregirlas es
parte del trabajo.

| Suposición del enunciado | Veredicto | Evidencia |
|-------------------------|-----------|-----------|
| "Hay fugas de módulos al root" (`pengu_infer.py`, `pengu_checker.py`, `pengu_parser.py`, `pengu_symbols.py`, `pengu_types.py`, `pengu_errors.py`, `pengu_comptime.py`, `pengu_folder.py`) | **❌ REFUTADO** | Solo `pengu_dce.py` está duplicado (como shim); todos los demás viven **exclusivamente** en `pengu_parser/`. `pengu_folder.py` **no existe** |
| "`pengu_folder.py` es un archivo Python suelto en la raíz" | **❌ REFUTADO** | No existe en ningún sitio del repositorio |
| "`doctor`/`gc`/`expand`/`time`/`eval`/`watch` podrían faltar" | **❌ REFUTADO** | Los 6 existen y funcionan |
| "El CLI tiene 13 subcomandos" | **❌ REFUTADO** | Tiene **25** (faltaban `remove`, `upgrade`, `tree`, `metadata`, `verify`, `vendor`) |
| "La caché de scripts no incluye la versión ni los flags de target" | **❌ REFUTADO** | `pengu_project.py:4267,4282-4284`; `pengu_cache.py:149-168` |
| "`msvc` mapea a `cl.exe`" | **❌ REFUTADO** | Solo cambia el dialecto |
| "La frame stack podría ser global" | **❌ REFUTADO** | Es thread-local (`pengu_runtime.h:392-398`); solo el guard del handler es global |
| "Los tombstones de mapas podrían no estar implementados" | **❌ REFUTADO** | Implementados con reutilización y 6 sitios de sondeo |
| "`pengu_runtime_original.h`, `scratch/`, `tests_std/` podrían seguir existiendo" | **❌ REFUTADO** | Los tres eliminados |
| "¿Hay métodos duplicados en `PenguChecker`?" | **❌ REFUTADO** | 121 métodos, 0 duplicados (también 170/0 en `PenguCodegen`) |
| "La guía de estilo enseña sintaxis `prototype` obsoleta" *(afirmación propia, corregida)* | **❌ REFUTADO** | 0 `prototype` en ambas guías; los 4 hits de `LANGUAGE.md` son terminología de C (§9.10) |
| "El grammar tiene **un** conflicto LALR" *(afirmación propia, corregida)* | **❌ REFUTADO** | `Lark(..., debug=True)` enumera **188** conflictos en 79 terminales; `strict=True` aborta en el primero y el terminal reportado varía entre ejecuciones (§1.1) |
| "`pengu check tests/**/*.pengu` verifica la semántica" | **❌ REFUTADO** | El posicional se ignora; falso verde en el 100 % de los casos |
| "`bench.yml` roto en Windows" (heredado) | **❌ REFUTADO tal cual** | Funciona; se endureció por prudencia |
| "`ci.yml`/`release.yml` sin `permissions`" (heredado) | **❌ REFUTADO en su forma fuerte** | Era granularidad, no ausencia |

**Total: 14 suposiciones del encargo + 2 afirmaciones propias corregidas.** Esto importa porque el encargo advertía que
auditorías previas tuvieron hallazgos falsos; esta auditoría **también tuvo que corregirse a sí
misma** en un punto (§9.10), lo que se documenta explícitamente.

### §18.3 ✨ UNDERSELL — lo que la documentación subestima

| # | Realidad | Por qué está subestimado |
|---|----------|-------------------------|
| 1 | **El CLI tiene 25 subcomandos, no 13** | Ni el README ni el ROADMAP enumeran `remove`/`upgrade`/`tree`/`metadata`/`verify`/`vendor` con la prominencia que merecen |
| 2 | **`pengu time` y `pengu expand`** | Herramientas de profiling e inspección de C intermedio que muchos lenguajes en 1.0 no tienen; apenas mencionadas |
| 3 | **El hover del LSP** | Firma completa + bits/bytes por parámetro + tamaño total de rune + marca de `inline`. Es una feature de venta y no aparece en ningún documento |
| 4 | **La arquitectura de validación del LSP** | Debounce 0.35 s + `run_in_executor` fuera del event loop + caché por sha1 + sync incremental real. Nivel producción, sin documentar |
| 5 | **La caché de dos niveles** | Tablas LALR serializadas con `grammar_digest` y fallback ante corrupción, más binarios de script con clave content-hash. Reduce 2-3 s a 170 ms. `PENGU_BUILD.md` lo describe, `README.md` no |
| 6 | **El runtime `pengu_runtime.h`** | 208 funciones, `-Wall -Wextra -Werror` → **0 warnings**, también bajo `-std=c99 -pedantic-errors`. Es el artefacto más disciplinado del repo y no se dice |
| 7 | **El codegen por defecto** | 0 warnings de C en un bundle de 6601 líneas con `-Wshadow`. `README.md:401` lo afirma, pero se lee como marketing y está **verificado** |
| 8 | **`_check_symbol_escape` (406 líneas)** | Análisis de escape real (auto-ownership, `borrowed`, views, retorno de slices de arrays de pila), no un stub |
| 9 | **`tests/test_ci_workflows.py`** | El proyecto testea sus **propios workflows**. Práctica poco común y valiosa |
| 10 | **`BENCHMARKS.md` y `docs/PERFORMANCE.md`** | Son honestos hasta el punto de reconocer un leak de memoria y una limitación de plataforma. La cultura existe; solo no se aplicó al catálogo de errores |
| 11 | **`loom` frente a `tally`** | `loom` maneja vacío con `maybe` y promedia centrales correctamente; la doc no lo recomienda |
| 12 | **`pengu_banish_string` es más seguro de lo que su propia doc dice** | `pengu_runtime.h:939-944` dice "NEVER call on `pengu_string_from_cstr`", pero `:946-957` comprueba `is_owned` |

### §18.4 La asimetría central

El patrón que emerge de §18.1 vs §18.3 es claro y conviene formularlo:

> **PenguScript está mejor construido de lo que su documentación admite, y su documentación promete
> más de lo que su verificación automática comprueba.**

- Lo **construido** (CLI de 25 comandos, LSP de 13 features, caché de dos niveles, runtime de 0
  warnings, codegen de 0 warnings, análisis de escape real) está **infravalorado**.
- Lo **prometido** (C99 portable, MSVC, async-signal-safe, fuzzing de 72 h, catálogo de errores,
  estilo del formateador) está **sobrevendido** y, crucialmente, **cada promesa tiene un gate que
  pasa en verde sin comprobarla** (§15.2).

Eso último es el verdadero problema de ingeniería, más que cualquier bug individual: **el proyecto
tiene una cultura de tests fuerte y una cultura de verificación de afirmaciones débil.** La suite
prueba el compilador con 2074 tests; los documentos no tienen ningún test que los confronte con el
código, salvo `tests/test_version.py` (parcial) y `tests/test_ci_workflows.py` (superficial).

---

## §19. Análisis de deuda técnica

> **Veredicto:** 🟡 **parcial** — la deuda está **acotada y localizada**, no extendida. Los números
> son manejables salvo por cuatro funciones gigantes y la ausencia total de linters configurados.

| Métrica | Valor | Comando / método |
|---------|-------|------------------|
| `TODO`/`FIXME`/`XXX`/`HACK` totales | **94** | `grep -rn` sobre `*.py`, `*.h`, `*.c`, `*.pengu` |
| …de los cuales en **código propio** | **~26** | El resto (68) está en headers de terceros `std_c/*.h` |
| …en headers de terceros | **68** | `miniaudio.h` 31, `typis.h` 13, `xxhash.h` 10, `raygui.h` 8, `rlights.h` 6, `imago.h` 6, … |
| …en `std/` | **4** | Todas en secciones **intencionadas** "Known Limitations & Roadmap" (`ffi.pengu:76-81`, `filum:20`, `parchment:20`, `precis:30`, `regulus:21`) |
| …en `pengu_project.py` | **1** | `:3648`, dentro de una **plantilla de código generado** (`"TODO: describe {name}"`) |
| Funciones públicas del runtime sin docstring | **55 de 208 (26 %)** | Crash-handler internals, 25 wrappers `pengu_c_f*`, `pengu_c_srand/rand*`, 6 `pengu_c_archivum_*` |
| Métodos duplicados en `PenguChecker` | **0** | `grep -oP '^    def \K\w+' \| uniq -d` |
| Métodos duplicados en `PenguCodegen` | **0** | idem |
| Duplicados en `PenguInferrer` | **1** (`__init__`, que es normal por herencia/anidamiento) | idem |
| Funciones > 200 líneas | **18** en total | Ver tabla abajo |
| `# type: ignore` sin justificar | **15** en código propio, **0** con justificación | `pengu_project.py` 5, `pengu_semver.py` 4, `pengu_parser/pengu_dce.py` 1, `scripts/fuzz/fuzz_common.py` 1 (los 10 restantes están en `extern/`) |
| Warnings de **pyflakes** | **132** | `pyflakes pengu_parser/*.py pengu_lsp/*.py *.py` |
| …`imported but unused` | 101 | Ruido mayormente inocuo |
| …`undefined name` | **4** (3 falsos positivos, **1 bug real**) | §19.2 |
| …variables locales nunca usadas | 10 | `ret_str` ×2, `sign`, `raw_name`, `package`, `key_c`, `iter_elem_c`, `is_local`, `is_cyclus`, `elem_c`, `current_abs`, `concept_name_node`, `base_target` |
| …`f-string is missing placeholders` | 4 | `pengu_project.py:3623,3873,4292,4477` |
| Warnings de **mypy** | ❌ **No medible** | `mypy` no está instalado ni es dependencia; **no hay `pyproject.toml`, `mypy.ini`, `setup.cfg` ni `.ruff.toml`** |
| Warnings de **ruff/pylint** | ❌ **No medible** | `ruff` y `pylint` no están instalados; no hay configuración de linter en el repo |
| Warnings de **gcc/clang** (bundle emitido) | ✅ **0** | `atlas.pengu` con `-Wall -Wextra -Wshadow` |
| Warnings de **gcc** (runtime header) | ✅ **0** | `-Wall -Wextra -Werror -fsyntax-only` |
| Warnings de **clang** (runtime header) | 🟡 389 con `-Weverything`, **0** con `-Wall -Wextra -Werror` | 267 `-Wunsafe-buffer-usage`, 86 `-Wdeclaration-after-statement`, 14 `-Wcast-qual` |
| Warnings de **MSVC/TCC** | 🟡 **TCC**: 0 en el bundle que acepta. **MSVC**: no medible (no hay build) | — |
| Ramas muertas confirmadas | 🟡 3 en docs (`pengu_folder.py`, asociados `alias Item`, `compress`) + 1 en LSP (`organize_imports_action`) + 1 en CLI (`pengu_bind.main()`) + 1 en grammar (`pengu_dce` shim es intencional) | — |

### §19.1 Las 18 funciones gigantes

| Archivo | LOC | Función | Línea |
|---------|-----|---------|-------|
| `pengu_parser/pengu_infer.py` | **2870** | `infer` | 746 |
| `pengu_parser/pengu_codegen.py` | **2605** | `_translate_expr_impl` | 6952 |
| `pengu_parser/pengu_checker.py` | **1323** | `_collect_top_level` | 821 |
| `pengu_parser/pengu_codegen.py` | 810 | `_translate_stmt_impl` | 4280 |
| `pengu_parser/pengu_checker.py` | 589 | `_check_set_stmt` | 4519 |
| `pengu_parser/pengu_checker.py` | 477 | `_check_node` | 2151 |
| `pengu_parser/pengu_codegen.py` | 446 | `generate_derived_implementations` | 3372 |
| `pengu_parser/pengu_infer.py` | 426 | `_resolve_call_target` | 3881 |
| `pengu_parser/pengu_checker.py` | 406 | `_check_symbol_escape` | 5777 |
| `pengu_project.py` | 329 | `main` | 4874 |
| `pengu_project.py` | 326 | `init_project` | 3451 |
| `pengu_project.py` | 322 | `build_compile_commands` | 1387 |
| `pengu_project.py` | 318 | `create_cli_parser` | 4509 |
| `pengu_parser/pengu_codegen.py` | 286 | `_translate_for_in` | 5229 |
| `pengu_parser/pengu_checker.py` | 236 | `_check_weave_decl` | 5366 |
| `pengu_parser/pengu_codegen.py` | 228 | `_collect_top_stmt` | 2269 |
| `pengu_project.py` | 221 | `run_script` | 4138 |
| `pengu_parser/pengu_codegen.py` | 217 | `_translate_string_lit` | 6010 |

**Observación:** `pengu_lsp/server.py` (68 773 B) tiene **0 funciones >200 líneas**. Es una
demostración de que el equipo **sabe** estructurar código cuando se lo propone; el problema está
concentrado en los tres archivos del compilador y en `pengu_project.py`.

### §19.2 Los cuatro `undefined name` de pyflakes

| Ubicación | Veredicto | Evidencia |
|-----------|-----------|-----------|
| `pengu_parser/pengu_infer.py:1886` (`Set[str]`) | **Falso positivo** | `from __future__ import annotations` en `:1`; la anotación es perezosa (PEP 563). Verificado con un test que define una anotación con un tipo inexistente y no falla |
| `pengu_parser/pengu_parser.py:466` (`ParseError`) | **Falso positivo** | Es `"ParseError"` como **string** en el tipo de retorno; además se importa localmente en la línea siguiente |
| `pengu_project.py:1192` (`Tree`) | **Falso positivo** | `from __future__ import annotations` en `:10` |
| **`pengu_parser/pengu_infer.py:4055` (`node`)** | ✅ **BUG REAL CONFIRMADO** | `NameError("name 'node' is not defined")` reproducido ejecutando el compilador. Ver §2.1 |

**Es un ejemplo perfecto de por qué hay que verificar cada hallazgo:** de 4 avisos de "nombre no
definido", 3 son ruido de PEP 563 y 1 es un crash del compilador. Reportar los 4 como bugs habría
sido un hallazgo falso; ignorarlos todos habría dejado pasar el crash.

### §19.3 Hallazgo DT1 — 🟠 Cero configuración de análisis estático

```bash
$ ls pyproject.toml setup.cfg tox.ini .ruff.toml mypy.ini 2>&1
ls: cannot access 'pyproject.toml': No such file or directory
ls: cannot access 'setup.cfg': No such file or directory
ls: cannot access 'tox.ini': No such file or directory
ls: cannot access '.ruff.toml': No such file or directory
ls: cannot access 'mypy.ini': No such file or directory

$ cat requirements.txt
lark>=1.1.0
pyyaml>=6.0
pygls>=2.0.0
lsprotocol>=2023.0.0
pycparser>=2.21
pyinstaller>=6.0.0
pytest>=7.0.0
pytest-timeout>=2.2.0
tomli>=2.0.0; python_version < '3.11'

$ grep -rn "ruff\|mypy\|pylint\|flake8\|pyflakes" .github/workflows/*.yml
(vacío)
```

**No hay linter, no hay type checker, no hay configuración de estilo, y nada de eso corre en CI.**
Para un proyecto de 27 204 + 12 085 + 4 144 = **43 433 líneas de Python**, esto significa que:

- Las 101 importaciones sin usar y las 10 variables muertas son solo la punta: nadie las mide.
- El bug `node`/`target_node` de §2.1 **habría sido encontrado por pyflakes en 30 segundos**, y
  pyflakes **ya es una dependencia transitiva** (`pyflakes` está en `pytest` → no; está instalado
  como dependencia de `pyinstaller`). Un `pyflakes .` en CI lo habría cazado.
- La única razón por la que se conoce el número 132 es que **esta auditoría** lo ejecutó.

**Fix propuesto (quick win de retorno enorme):** añadir `ruff` a `requirements.txt`, crear un
`pyproject.toml` con reglas mínimas (`E`, `F`, `W` con `F821` — nombres no definidos — como
**error**), y añadir un paso `ruff check --select F821,E9` a `ci.yml`. Eso por sí solo habría
bloqueado el bug B4.

### §19.4 Hallazgo DT2 — Módulos con demasiadas responsabilidades

| Módulo | LOC | Responsabilidades | Debería dividirse en |
|--------|-----|-------------------|---------------------|
| `pengu_project.py` | **5207** | 6 (parser CLI, proyecto, builder, runner, assets, compile_commands) | `pengu_cli/*` (6 módulos) |
| `pengu_parser/pengu_codegen.py` | **15 000+** | Generación de C para 60+ tipos de nodo, atributos, DCE, `#line`, monomorfización | `codegen/{expr,stmt,type,attr,derivations}.py` |
| `pengu_parser/pengu_checker.py` | **12 000+** | Recolección top-level, semántica, escape, ownership, bounds, C-keyword collision | `checker/{collect,stmts,types,escape,cname}.py` |
| `pengu_parser/pengu_infer.py` | **8 700+** | Inferencia de 60+ nodos, resolución de llamadas, genéricos, bounds | `infer/{expr,call,generic,bounds}.py` |

(LOC estimadas por `wc -l` sobre los archivos: 518 379 B / 380 492 B / 237 974 B respectivamente,
que a ~35 B/línea dan las cifras anteriores.)

**Recomendación de secuencia:** no dividir antes de arreglar §4.1 y §3.2. Un refactor masivo sobre
código con bugs conocidos convierte un fix de 2 líneas en una investigación de 2 días.

### §19.5 Hallazgo DT3 — 🟡 Imports circulares: ninguno

Verificación explícita de los pares sospechosos por el encargo:

| Par | ¿Ciclo? | Evidencia |
|-----|---------|-----------|
| `pengu_project` ↔ `pengu_bind` | ✅ **No** | `grep pengu_project pengu_bind.py` → 0; el import es local en `:5090` |
| `pengu_checker` ↔ `pengu_infer` | ✅ **No** | `pengu_checker` → `pengu_infer` (una dirección); el inferrer recibe el `SymbolTable` por inyección |
| `pengu_codegen` ↔ `pengu_checker` | ✅ **No** | `pengu_codegen` importa `pengu_types`/`pengu_symbols`/`pengu_dce`, no el checker |
| `pengu_parser` ↔ `pengu_lsp` | ✅ **No** | El LSP importa el parser; el parser no conoce el LSP |
| `pengu_types` ↔ cualquier otro | ✅ **No** | `pengu_types` no importa módulos hermanos del compilador |

**Conclusión: 0 ciclos de importación a nivel de módulo.** El diseño de dependencias es correcto y no
requiere `CLEANUP_PLAN` §5 más allá de confirmarlo.

> **Precisión añadida en la Fase 1 (item 1.11).** La afirmación "0 ciclos" es correcta para imports
> **a nivel de módulo** —verificado con `ast` sobre los **40 módulos** del repositorio— pero la
> formulación original era imprecisa: existe **un par de módulos que se importan mutuamente**, y lo
> hacen de forma **perezosa, dentro de funciones**:
>
> | Par | Dirección | Ubicación | Naturaleza |
> |-----|-----------|-----------|------------|
> | `pengu_doc` → `pengu_project` | `from pengu_project import ProjectConfig` en `pengu_doc.py:315-317` | Dentro de `doc_project()`, en un `try`/`except` | **Perezoso** |
> | `pengu_project` → `pengu_doc` | `from pengu_doc import doc_project` en `pengu_project.py:5419` | Dentro del despacho del subcomando `doc` (11 `if` anidados) | **Perezoso** |
>
> La cadena de padres del AST confirma que ninguno de los dos es hijo directo del módulo
> (`ImportFrom < Try < FunctionDef < Module` y `ImportFrom < If ×23 < FunctionDef < Module`). **Ese es
> exactamente el patrón que mantiene el grafo acíclico en tiempo de importación**: si cualquiera de
> los dos se subiera a nivel de módulo, `import pengu_doc` fallaría con un ciclo real. Se fija con
> `tests/test_audit_regressions.py::test_the_two_mutually_referencing_modules_stay_lazy`, que
> además comprueba que el import perezoso sigue existiendo (si desapareciera, la feature estaría
> muerta).
>
> Registro de método: la comprobación de §19.5 se hizo par por par sobre los 5 pares sospechosos y
> **no cubrió este par**. El barrido exhaustivo posterior pasó por tres implementaciones propias
> defectuosas (una no visitaba módulos sin aristas salientes, otra no veía imports anidados en un
> `try`, la tercera sobre-recolectaba al recorrer el módulo entero) antes de acertar. Es el mismo
> patrón de error que `CLEANUP_PLAN.md` §7.5 documenta: **una comprobación por nombre/par no
> sustituye a un barrido estructural**.

### §19.6 Hallazgo DT4 — 🟠 Código muerto confirmado

| Ubicación | Tipo | Tamaño | Evidencia |
|-----------|------|--------|-----------|
| `pengu_runtime.c` (raíz) | Archivo rastreado de **0 bytes** | 0 B | `git cat-file -s HEAD:pengu_runtime.c` → `0`; `build_runtime.py:1174` usa `PARSER_DIR/"pengu_runtime.c"` |
| `pengu_bind.py:1567-1617` | `main()` + argparse completo sin usar | ~50 líneas | `pengu_project.py:5090` importa solo `HeaderParseError, generate_bind_file` |
| `pengu_lsp/code_actions.py:396` | `organize_imports_action` sin call sites | ~40 líneas | 0 referencias fuera de su definición |
| `pengu_lsp/server.py:1790` | CodeLens apuntando a un comando no registrado | ~10 líneas | No existe `@server.command("pengu.runTest")` |
| Grammar: `simple_stmt` | Regla probablemente inalcanzable | 6 líneas | Se usan los `*_simple` aliases de `SIMPLE_STMT_ALIASES` |
| Grammar: 11 reglas `*_no_cast` | Duplicación estructural completa de la jerarquía de expresión | ~40 líneas | Solo excluyen `transmute` en `for`/`slice_range` |
| Grammar: 12 reglas `guard_*` | Duplicación completa de la jerarquía para el guard de `when` | ~35 líneas | Podrían reutilizar las reglas normales con un flag de contexto |
| `pengu_folder.py` | **Mencionado en el encargo, no existe** | — | 0 referencias |

### §19.7 Hallazgo DT5 — 🟡 Complejidad: `radon` no disponible

El encargo pedía `radon cc -s pengu_parser/` para complejidad ciclotómica. **`radon` no está
instalado** y añadirlo cambia el entorno, así que se reporta como no medido:

**🟡 NO VERIFICADO:** complejidad ciclotómica por función. *Proxy* disponible: funciones >200 líneas
(§19.1) y 377 sitios de diagnóstico en el checker + 171 en el inferrer, que implican muchos caminos.
La función `infer` (2870 líneas) y `_translate_expr_impl` (2605 líneas) tienen previsiblemente una
complejidad ciclotómica de tres dígitos, muy por encima de cualquier umbral razonable (10-20).

### §19.8 Resumen de deuda por severidad

| Severidad | Elementos | Deuda estimada |
|-----------|-----------|----------------|
| 🔴 Alta | 4 funciones >1000 líneas; `pengu_project.py` de 5207; 0 linters configurados; 1 crash real por `node` | **L** |
| 🟠 Media | 14 funciones de 200-800 líneas; 15 `type: ignore` sin justificar; 101 imports sin usar; 55 funciones del runtime sin doc; 4 bloques de código muerto | **M** |
| 🟡 Baja | 10 variables locales muertas; 4 f-strings sin placeholder; 389 warnings de `clang -Weverything`; duplicación del grammar (~75 líneas) | **S** |
| 🟢 Informativo | 68 TODO/FIXME en headers de terceros; 94 totales | **S** |

---

## §20. Checklist final de 1.0

> **Veredicto:** 🔴 **bloqueante** — quedan **8 bloqueantes verificados**. El proyecto está más cerca
> de 1.0 de lo que su versión sugiere, pero los 8 deben cerrarse **y sus gates de CI deben
> endurecerse**, o 1.0 repetirá el patrón de "verde sobre roto".

### §20.1 Bloqueantes (deben cerrarse antes de 1.0)

| # | Item | Dónde | Done verificable |
|---|------|-------|------------------|
| **B1** | `pengu check <archivo>` debe validar el archivo | `pengu_project.py:4745,4881,5052` | `pengu check archivo_con_error.pengu` → rc=1 y emite el diagnóstico; test que lo cubra |
| **B2** | `check_sources_diagnostics` debe fallar si el entry no existe | `pengu_project.py:1272` | `pengu check` en directorio sin `src/main.pengu` → rc≠0 con mensaje claro |
| **B3** | `parse_known_args` debe rechazar flags desconocidos | `pengu_project.py:4881` | `pengu check --bogus` → rc=2; test paramétrico por subcomando |
| **B4** | `fmt --indent N` no debe corromper la indentación | `pengu_lsp/formatting.py:234,251` | `fmt(fmt(x)) == fmt(x)` y `check(fmt(x)) == check(x)` sobre los 27 módulos puros |
| **B5** | `--strict-c99` debe emitir C que compile en programas con `std` | `pengu_codegen.py:4232-4256` | `pengu build --strict-c99` + `gcc -std=c99 -pedantic-errors` sobre `tests/std_programs/*.pengu` → 0 errores |
| **B6** | `pengu_infer.py:4055` `node` → `target_node` | `pengu_infer.py:4055` | Test que acceda a un símbolo privado de otro módulo y espere `E0043` (no `NameError`) |
| **B7** | Tipos cualificados a través de un módulo re-exportador deben conservar los campos | `pengu_infer.py:1463-1478` | `var v as dep.Vec is with x is 1.0` compila; `raymath.Vector2` funciona |
| **B8** | `pengu_parser/pengu_runtime.c` debe compilar sin flags de supresión | `build_runtime.py:1195-1204` | `-DMBEDTLS_ALLOW_PRIVATE_ACCESS`, eliminar los dos `-Wno-*`; `gcc -Wall -Wextra -c` → 0 errores |
| **B9** | El job de sanitizers debe estar verde o explícitamente excluido | `sanitizers.yml:58-70` | El job pasa; el leak queda en `xfail(strict=True)` documentado, no en un paso que debe fallar |
| **B11** | Reducir los 188 conflictos shift/reduce del grammar (tabla de precedencia + colapsar duplicados) y fijar la precedencia con un test | `pengu_grammar.py:112-430` | `Lark(..., strict=True)` construye sin error; las 9 expresiones de §1.1 mantienen su árbol y su valor |
| **B10** | Ningún gate puede aprobar una propiedad inspeccionando texto | `test_cli_strict_c99.py`, `test_c99_portability.py`, `test_error_codes_uniqueness.py`, `test_attributes_msvc.py` | Los 4 tests compilan/ejecutan o miden, no comparan cadenas |

### §20.2 Altos (deberían cerrarse antes de 1.0)

| # | Item | Dónde |
|---|------|-------|
| A1 | Documentar los bounds como conjuntos de operadores o hacer la jerarquía monótona (`T: Num` concede `==` y `<` pero `T: Par` no concede `<`) | `pengu_types.py` (tabla de concepts) + `LANGUAGE.md:1535-1560` |
| A2 | Regenerar §22.2/§22.3 desde el código y eliminar las 5 clases fantasma | `LANGUAGE.md:3386-3460` + `pengu_errors.py` |
| A3 | `--target-compiler` debe rechazar un dialecto que no corresponda al compilador | `pengu_project.py:1465-1500`, `pengu_codegen.py:3955` |
| A4 | `--quiet` y `--no-color`/`NO_COLOR` deben funcionar | `pengu_project.py:4538-4541`, 77 sitios de `print` |
| A5 | `pengu test --json` debe emitir JSON Lines en fallo | `pengu_project.py:4469,5034` |
| A6 | Errores del camino de script con el reporter estándar (no tracebacks) | `pengu_project.py:4138`, `eval`, `expand`, `time`, `watch` |
| A7 | `pengu fmt` default a **4** espacios (coherente con doc y stdlib) | `pengu_project.py:4793` |
| A8 | Rename global del LSP debe ser semántico | `pengu_lsp/server.py:1281-1294` |
| A9 | Go to definition no debe devolver rutas shadow | `pengu_lsp/server.py:403-420` |
| A10 | `std/seal.pengu` `crc32` debe devolver `u32` | `std/seal.pengu:44,71` |
| A11 | Añadir linter (ruff con `F821` como error) y type checker a CI | `requirements.txt`, nuevo `pyproject.toml`, `ci.yml` |
| A12 | Verificación SHA-256 de `extern/` y del TCC descargado | `extern_manifest.py:16-43,123-141`, `pengu_tcc.py:118-152` |
| A13 | Corpora de compliance (50 canónicos) y de migración | `tests/compliance/`, `tests/migration/` |
| A14 | Job real de MSVC o retirar la afirmación | `ci.yml`, `build_runtime.py`, `RELEASE_CHECKLIST.md:13` |
| A15 | `PENGU_ABI_VERSION` verificable contra `libpengu_runtime.a` | `pengu_parser/pengu_runtime.c`, `pengu_codegen.py:9854` |
| A16 | Presupuestos de fuzzing realistas (≤6 h/shard) | `docs/FUZZING.md:69`, `RELEASE_CHECKLIST.md:27`, `fuzz.yml` |
| A17 | Serializar/re-documentar la relación entre sintaxis `to` y `..` | grammar + `LANGUAGE.md` |
| A17b | Añadir tabla de precedencia explícita y un test que fije asociatividad/precedencia de las 9 expresiones de §1.1 | `pengu_grammar.py`, `tests/test_precedence.py` (nuevo) |
| A18 | 4 ejemplos de `LANGUAGE.md` que no compilan (bloques 15, 28, 59, 94) | `LANGUAGE.md` |

### §20.3 Medios (antes de 1.0 si el calendario lo permite)

| # | Item |
|---|------|
| M1 | Reparar el falso positivo de `while true` en la detección de retornos faltantes |
| M2 | Cerrar la clase de bug de códigos de error: `E0035` cubre 4 condiciones; 24 códigos sin clase |
| M3 | Silenciar `W0005` en bloques `test` y en la stdlib (29 casos) |
| M4 | Resolver la duplicación `loom` ∩ `tally` (15 nombres) |
| M5 | Corregir `CHEATSHEET.md` (3 nombres erróneos de funciones) y "25 modules" → 27 |
| M6 | Sincronizar versiones en 13 archivos y extender `test_version.py` |
| M7 | Corregir `SPARK_VERSION`/`STD_VERSION` y el test vacuo de `spark` |
| M8 | Elevar la doc inline de `atlas` (32 %), `arithmancy` (39 %) y `scrolls` (52 %) |
| M9 | Añadir `sha256` al lockfile como obligatorio (no saltables en silencio) |
| M10 | Benchmarks que importen `std` (cero hoy) |
| M11 | `workspace/symbol` y `prepareRename` en el LSP |
| M12 | Añadir `pytest-cov` y un umbral de cobertura a CI |
| M13 | Property-based testing con `hypothesis` (idempotencia del fmt, round-trip del parser) |
| M14 | `CONTRIBUTING.md`, `ARCHITECTURE.md`, `docs/ABI.md`, `MIGRATION.md` |
| M15 | Emitir `__typeof__` en lugar de `__auto_type` para que TCC funcione con `std` |
| M16 | Añadir `SIGFPE`/`SIGILL`/`SIGBUS` al crash handler y `sigaction` |
| M17 | Formatear sin `snprintf` en el crash handler, o retirar la afirmación |

### §20.4 Orden por dependencia

```
B3 (rechazar flags)  ─────────────┐
B1 (check <archivo>) ─────────────┼──► A11 (linter en CI) ──► B10 (gates reales)
B2 (entry inexistente) ───────────┘

B6 (node→target_node) ────────────┐
B7 (tipos cualificados) ──────────┼──► A18 (4 ejemplos de docs) ──► A2 (catálogo generado)
A1 (bounds coherentes) ───────────┘

B8 (runtime C99 legal) ──► A14 (job MSVC) ──► A15 (ABI vs .a)
B5 (strict-c99 real) ────┘

B4 (fmt no corrompe) ──► A7 (fmt default 4) ──► A13 (corpus compliance/migración)

B9 (sanitizers verde) ──► M9 (lockfile obligatorio) ──► A12 (SHA-256 extern/TCC)

A3..A6, A8..A10 (CLI/LSP/std fixes) ──► M1..M17 (medios) ──► Fase 10 (congelación)
```

**Los cuatro primeros grupos son independientes** y pueden hacerse en paralelo. `A11` (linter en CI)
es un *quick win* con retorno desproporcionado: habría cazado B6 automáticamente.

### §20.5 Criterio de "done" para declarar 1.0

Ninguno de estos es opcional:

- [ ] Los **11 bloqueantes** (B1–B11) cerrados con test de regresión cada uno.
- [ ] Los **4 tests de "gate por texto"** convertidos en tests que compilan/ejecutan/miden.
- [ ] `pengu check <archivo>` y `pengu check` sin entry devuelven rc≠0 ante error.
- [ ] `--strict-c99` compila y **ejecuta** los `tests/std_programs/*.pengu` sin errores de
      `-std=c99 -pedantic-errors`.
- [ ] `pengu fmt` es idempotente y preservador de semántica sobre los 52 módulos de `std/`, y su
      default coincide con la convención documentada.
- [ ] El job de sanitizers está verde con el leak en `xfail(strict=True)` documentado.
- [ ] El catálogo de errores de `LANGUAGE.md` se genera del código y un test falla si divergen.
- [ ] Los 105 bloques de `LANGUAGE.md` están etiquetados como `pengu` (completo) o `pengu-fragment`,
      y CI compila **solo** los completos: **0 fallos**.
- [ ] Existe `tests/compliance/` con 50 programas numerados, uno por sección del manual, todos en CI.
- [ ] Existe `tests/migration/` con programas de cada versión publicada, todos compilando.
- [ ] `ruff` corre en CI con `F821` como error y **0** violaciones.
- [ ] Ninguna afirmación de release (`RELEASE_CHECKLIST.md`) sin un gate que la verifique.
- [ ] `--quiet`, `--no-color`/`NO_COLOR` y `--json` se comportan como su ayuda dice, con test.
- [ ] Los 3 documentos de release (`RELEASE_CHECKLIST.md`, `BENCHMARKS.md`, `SECURITY.md`) fueron
      auditados línea a línea contra el código, sin afirmaciones sin gate.

### §20.6 Lo que NO debe bloquear 1.0 (⏸️ DIFERIDO a 1.1+)

| Item | Justificación técnica |
|------|----------------------|
| ⏸️ **Borrow checking real** | Es un cambio de análisis, no de sintaxis. Requiere modelar tiempos de vida y puede invalidar código válido; hacerlo antes de 1.0 rompería compatibilidad. Es el "holy grail" de §9.11 y merece su propia versión con periodo de deprecación |
| ⏸️ Async/await nativo | Con ownership determinista y sin GC, un runtime async es un proyecto de meses y no hay demanda en la stdlib |
| ⏸️ Closures con captura | Rompe la decisión de diseño de emitir funciones C `static` de nivel superior. Necesitaría closures como structs + función, lo que es una feature de lenguaje, no un fix |
| ⏸️ Macros de AST | Superficie enorme, riesgo de incompatibilidad, y el lenguaje ya tiene `when`/`comptime`/`shard` que cubren el 80 % |
| ⏸️ Dynamic dispatch / vtable | Contradice la reivindicación central de "zero runtime overhead" de los concepts. Debe ser una decisión explícita con su propio documento |
| ⏸️ Reflection/RTTI | Idem; rompería el modelo de C puro |
| ⏸️ Backtracking completo en resolución de deps | No hay evidencia de que el resolvedor actual falle en casos reales; añadirlo es especulativo |
| ⏸️ Migración completa de `Result` en stdlib | La API de doble vía (`write_file` + `write_file_result`) funciona; forzar la migración rompería los 174 tests de std |
| ⏸️ Playground WASM | Ya diferido previamente; requiere un target WASM que no existe |
| ⏸️ `derive` para el 100 % de los concepts derivables | `Par`/`Ordo` cubren los casos reales; el resto no tiene demanda medida |
| ⏸️ Associated types (`alias Item` en concept) | Feature de lenguaje mediana; hoy el trabajo se hace con `shard T and U`. Mientras no exista, **hay que retirar el ejemplo de la doc** (§1.2) |
| ⏸️ `pengu repl` | El proyecto tiene `pengu eval`; un REPL de verdad requiere estado incremental en el compilador |

### §20.7 Cierre

El proyecto está **mejor de lo que su versión sugiere y peor de lo que su checklist afirma**.

Lo que confío en que funciona, tras verificarlo: el **codegen por defecto** (0 warnings de C en
6601 líneas), el **runtime header** (0 warnings con `-Werror`), los **52 módulos de la stdlib**
(0 errores de check, 174 tests verdes), el **LSP** (13/16 features reales, estable en 2024 líneas,
cero TODOs), la **caché de dos niveles**, la **suite de 2074 tests** sin flaky, y la
**organización de `pengu_parser/`** (0 ciclos, 0 fugas de módulos).

Lo que necesita arreglarse: **una herramienta de formato que corrompe el fuente**, **un comando de
validación que no valida**, **una feature de portabilidad que no compila**, **un crash del
compilador en un camino de error del usuario**, **tipos que pierden sus campos al cruzar módulos**,
y —por encima de todo— **una cultura de CI que aprueba propiedades inspeccionando texto**. Los diez
bloqueantes de §20.1 son todos arreglables en días, no meses.

Lo que necesita documentarse o retirarse: **el catálogo de errores**, **las afirmaciones de
seguridad**, **el checklist de release** y **el ancho de indentación del formateador**.

Lo que necesita diferirse, con justificación: **borrow checking**, **async**, **closures con
captura**, **macros de AST**, **dynamic dispatch** y **reflection** (§20.6).

Y una nota final sobre honestidad, que es el eje de este encargo: `BENCHMARKS.md` y
`docs/PERFORMANCE.md` demuestran que este proyecto **sabe** escribir documentación honesta,
incluyendo el reconocimiento explícito de un leak de memoria y de una limitación de plataforma. El
problema no es la cultura; es que esa misma disciplina **no se aplicó** al catálogo de errores, a la
guía de estilo, a `SECURITY.md` ni a `RELEASE_CHECKLIST.md` — los cuatro documentos que un usuario
lee antes de confiar en el lenguaje. Cerrar esa asimetría es, más que cualquier bug individual, el
trabajo real que separa a PenguScript 0.16.0 de un 1.0 creíble.

