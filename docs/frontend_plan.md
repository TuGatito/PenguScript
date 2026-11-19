# Plan de implementación del frontend (grammar.lark + parser)

## Principios rectores

- **Una sola gramática, una sola fase a la vez.** `grammar.lark` crece por fases; nunca se edita un archivo enorme de golpe. Cada fase es *parseable* y *testeable* de extremo a extremo con las fixtures que añade.
- **LALR(1) por defecto.** Solo se cambia a Earley si una regla concreta lo exige, y se documenta en el propio `.lark` con un comentario `// EARLEY: motivo`. El rendimiento importa.
- **Un archivo por fase, no por concepto.** El parser se valida con fixtures reales del `cheatsheet.md`, no con ejemplos inventados.
- **AST desacoplado del CST.** `transformer.py` es el único que conoce a Lark. A partir de ahí, `analysis/` y `backend/` solo ven dataclasses propias.
- **Toda regla nueva viene con su fixture mala.** Cada fase añade al menos 3 fixtures `bad/` con errores de sintaxis que deben fallar con código propio (E1xxx).

## Estructura del frontend

```
frontend/
├── grammar.lark              # ~600-800 líneas al terminar la fase 9
├── parser.py                 # Lark(config), Indenter, cache singleton
├── ast_nodes.py              # @dataclass(frozen=True, slots=True) por nodo
├── span.py                   # Span(start_byte, end_byte, line, col) desde meta
├── transformer.py            # Transformer Lark CST → AST propio
├── errors.py                 # SyntaxError, UnexpectedToken, UnexpectedEOF
└── postlex.py                # Indenter configurado + interpolación de strings
```

`postlex.py` contiene el `Indenter` configurado (`{}`, `[]`, `()` en `paren_table`) y un post-proceso de `STRING` para partir `"a #{expr} b"` en `StringInterp(parts=[...])` donde cada `#{...}` se parsea recursivamente.

---

## Fase 1 — Fundación léxica

**Alcance:** terminales de todos los tokens del lenguaje, `parser.py` con LALR + Indenter, `Span`, `ast_nodes` base (`Node`, `Expression`, `Statement`, `Declaration`), `transformer.py` vacío que rechaza todo. El parser acepta un archivo vacío y archivos con solo comentarios.

---

## Resumen de Fases 2 a 9

- **Fase 2 — Expresiones núcleo:** Precedencia, literales, acceso a realm (`::`), field access (`.`), llamadas, indexación, casteos, rangos, unarios, binarios.
- **Fase 3 — Statements y function literals:** Bloques, asignaciones, `if`/`unless`, loops (`while`, `until`, `repeat`, `for`), `break`/`continue`, `unsafe`, function literals.
- **Fase 4 — Top-level y módulos:** `realm`, `invoke`, `const`, `echo`, `seal`, `rune` (campos), `enchanting` vacío.
- **Fase 5 — Enchanting y operadores:** Constructores/destructores, métodos `mut`/`const`, operadores sobrecargados, `parent()`.
- **Fase 6 — Tipos y sigilos:** Tipos primitivos y genéricos, referencias, opcionales, sigilos y restricciones `needs`.
- **Fase 7 — Omens, flags, unsafe:** `omen`, `flags omen`, modificador `unsafe`.
- **Fase 8 — Expresiones avanzadas:** Comprehensions, if-expressions, interpolación de strings (`#{}`), prefijos de colecciones.
- **Fase 9 — Endurecimiento:** Error recovery, fixtures contra cheatsheet, benchmarks de rendimiento.
