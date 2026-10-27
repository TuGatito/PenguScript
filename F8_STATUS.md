# F8 — LSP nativo (cerrado)

> El servidor nativo funciona en stdio y TCP, con lifecycle, documentos,
> diagnósticos y features LSP. La paridad fina con `pengu_lsp` se limita a
> diagnósticos; el resto es funcional pero heurístico.

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

## Verificaciones de cierre

- VS Code smoke reproducible (`scripts/vscode_f8_smoke.sh`) ✅
- Paridad de diagnósticos con `pengu_lsp` ✅
- ASan/UBSan 1 000 `didChange` ✅

Mejoras futuras (no bloquean F8): paridad fina del resto de features y usar más
metadatos F3 en lugar de heurísticas textuales.

## VS Code smoke

`scripts/vscode_f8_smoke.sh` instala/levanta la extensión con `--extensionDevelopmentPath`,
abre un `.pengu` inválido y verifica un diagnóstico real del LSP:

```text
F8_VSCODE_DIAGS=[{"message":"expected an expression","source":"pengu","severity":0}]
```

## Cierre técnico

- ASan/UBSan LSP: initialize + didOpen + 1 000 didChange, exit 0.
- Paridad de diagnósticos contra `pengu_lsp`: código, severidad y rango inicial.
- F8 tests: 16.

## Evidencia

```text
F6+F7+F8: 16 passed
VS Code smoke: F8_VSCODE_DIAGS=expected an expression
ASan/UBSan LSP: 1 000 didChange OK
bootstrap: punto fijo OK
preflight gcc/clang/TCC: READY
psc lsp --tcp: initialize/shutdown/exit OK
```
