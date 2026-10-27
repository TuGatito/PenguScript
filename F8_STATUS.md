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
| Code actions | acción “Format document” |
| On-type | `:` inserta salto e indentación |
| Tests | `test_f8_lsp.py` + `test_f8_features.py` (3 tests) |
| Bootstrap | punto fijo OK; gcc/clang/TCC READY |

## Pendiente

1. Diagnósticos UTF-16 verificados (hecho); faltan pruebas con CJK/emoji variados.
2. Caches/índice de workspace y paridad fina de semantic/inlay/actions/on-type.
3. Caches/índice de workspace (hoy escaneo en cada request).
4. Paridad con `pengu_lsp`; ñ/CJK/emoji; 1 000 didChange; ASan.
5. VS Code smoke, CI y docs completos.
6. Metadatos F3 (`module/line/col`) para navegación semántica precisa.

## Evidencia

```text
tests/psc/test_f8_lsp.py + test_f8_features.py: 3 passed
bootstrap: punto fijo OK
preflight gcc/clang/TCC: READY
psc lsp --tcp: initialize/shutdown/exit OK
```
