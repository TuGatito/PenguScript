# F8 — LSP (núcleo implementado)

> Estado real: transporte, ciclo de vida, TCP/stdio, documentos, URI/UTF-16 y
> framing están implementados y probados. La inteligencia LSP (diagnósticos
> completos, completion, hover, navegación, symbols, etc.) sigue pendiente.

## Completado

| Área | Estado |
|---|---|
| `psc lsp` | comando real, ya no stub |
| Transporte | stdio y TCP (`--tcp --host --port`), framing `Content-Length`, flush |
| Lifecycle | `initialize`, `initialized`, `shutdown`, `exit`, ids number/string, método desconocido |
| Documentos | `didOpen`, `didChange` full-sync, `didClose` |
| URI | `file://` <-> path, percent-encoding, drive letter |
| UTF-16 | conversión byte <-> línea/character UTF-16 |
| Diagnósticos | `psc check --diagnostics=json` en subproceso y `publishDiagnostics` con contenido; falta convertir columnas a UTF-16 |
| Hover | firma/línea de declaración |
| Definition / implementation | definición por declaración; implementation delega en definition |
| Completion | keywords + identificadores del documento |
| References / highlight | ocurrencias del identificador |
| Symbols | documentSymbol y workspace/symbol |
| Folding | bloques por indentación |
| Formatting | `psc fmt --stdin` vía F7 |
| Rename | prepareRename + WorkspaceEdit |
| Signature help | parámetros desde la firma textual |
| Code lens | `Run` para `main`, `Run test` para tests |
| Build | `psc 0.8.0 (F8)`; bootstrap estable |
| Tests | `tests/psc/test_f8_lsp.py`: lifecycle stdio + TCP |
| C includes | deduplicación por texto, no por módulo; `netdb.h`/`unistd.h` llegan al bundle |

## Evidencia

```text
F8 LSP wire tests: 2 passed
bootstrap: punto fijo OK
psc lsp --help: OK
psc lsp --tcp: initialize/shutdown/exit OK
```

## Pendiente para cerrar F8

1. Diagnósticos con contenido real (hoy se publica `[]`; falta integrar
   `psc check` sin corromper el heap y validar UTF-16).
2. Completion, hover, signature help.
3. Definition, implementation, references, highlight.
4. Document/workspace symbols, folding.
5. Semantic tokens, inlay hints, code lens.
6. Code actions, prepareRename/rename.
7. Formatting/on-type.
8. Caches/índice de workspace e invalidación.
9. Paridad con `pengu_lsp`, UTF-16 ñ/CJK/emoji, 1 000 didChange, ASan.
10. VS Code smoke y docs/CI completos.

## Nota

Las capacidades anunciadas se limitan a `textDocumentSync=1` hasta que cada
feature esté implementada; no se anuncia paridad falsa.
