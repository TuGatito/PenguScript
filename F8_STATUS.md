# F8 — LSP nativo (features básicas implementadas)

> El servidor nativo funciona en stdio y TCP, con lifecycle, documentos,
> diagnósticos y una primera capa de features LSP basadas en el documento y en
> `psc check`. No es paridad completa con `pengu_lsp`.

## Completado

| Área | Estado |
|---|---|
| Transporte | stdio + TCP (`--tcp --host --port`), framing, flush |
| Lifecycle | initialize/initialized/shutdown/exit; ids number/string |
| Documentos | didOpen/didChange full-sync/didClose |
| URI/UTF-16 | módulos `uri` y `positions`; hover/definitions usan UTF-16 |
| Diagnósticos | `psc check --diagnostics=json-utf16`; `publishDiagnostics` con columnas UTF-16 |
| Hover | firma/línea de declaración |
| Definition / implementation | definition por declaración; implementation delega |
| Completion | keywords + identificadores |
| References / highlight | ocurrencias del identificador |
| Symbols | documentSymbol, workspace/symbol |
| Folding | bloques por indentación |
| Formatting | `psc fmt --stdin` (F7) |
| Rename | prepareRename + WorkspaceEdit |
| Signature help | parámetros desde la firma textual |
| Code lens | Run / Run test |
| Semantic tokens | léxico simple: keywords/identificadores/literales/números/comentarios |
| Inlay hints | tipo inferido básico para `var/let ... is <literal>` |
| Caches | workspace symbols se indexan una vez y se invalidan al editar |
| Code actions | acción “Format document” |
| On-type | `:` inserta salto e indentación |
| Tests | `test_f8_lsp.py` + `test_f8_features.py` + `test_f8_stress.py` (5 tests; 1 000 didChange) |
| Bootstrap | punto fijo OK; gcc/clang/TCC READY |
| Stress | 1 000 didChange (sin cambios) OK |

## Pendiente

1. ASan específico del LSP con 1 000 `didChange` (el binario ASan no completó el handshake en esta sesión).
2. VS Code smoke (no hay runner headless disponible).
3. Paridad fina con `pengu_lsp` y features todavía heurísticas.
4. Algunas features siguen usando texto en vez de símbolos F3, aunque los metadatos ya existen.

## Evidencia

```text
tests/psc/test_f8_lsp.py + test_f8_features.py: 3 passed
bootstrap: punto fijo OK
preflight gcc/clang/TCC: READY
psc lsp --tcp: initialize/shutdown/exit OK
```
