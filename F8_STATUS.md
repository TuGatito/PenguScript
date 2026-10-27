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
| Diagnósticos | in-process con `sema_api.check_text` + `render_json_utf16`; sin subproceso |
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
| Tests | LSP + features + stress + interpolación/caché + paridad Python (8 archivos; 16 tests) |
| Bootstrap | punto fijo OK; gcc/clang/TCC READY |
| Stress | 1 000 didChange (sin cambios) OK, también bajo ASan/UBSan O1 |

## Pendiente

1. VS Code smoke real (no hay runner headless/xvfb en este entorno).
2. Paridad fina del resto de features (hoy sólo diagnósticos).
3. Varias features siguen usando texto en vez de símbolos F3, aunque los metadatos ya existen.

## Cierre técnico

- ASan/UBSan LSP: initialize + didOpen + 1 000 didChange, exit 0.
- Paridad de diagnósticos contra `pengu_lsp`: código, severidad y rango inicial.
- F8 tests: 16.

## Evidencia

```text
tests/psc/test_f8_lsp.py + test_f8_features.py: 3 passed
bootstrap: punto fijo OK
preflight gcc/clang/TCC: READY
psc lsp --tcp: initialize/shutdown/exit OK
```
