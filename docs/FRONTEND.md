# Frontend de PenguScript

Documento de ingeniería del frontend (Fase 1, F0–F6). No es normativo: la
gramática y el comportamiento del lenguaje están en [`LANGUAGE.md`](LANGUAGE.md).

## Pipeline

```text
fuente UTF-8
   │
   ▼
lexer ──────────────► tokens + diagnósticos léxicos
   │
   ▼
parser Pratt + items ─► AST + diagnósticos sintácticos
   │
   ▼
CST lossless ────────► árbol con todo el texto (trivia incluido)
   │
   ▼
HIR (C1) ────────────► módulos, defs, scopes, cuerpos, nombres
```

El frontend no conoce tipos, ownership ni codegen. `pengu-syntax` produce el AST
y el CST; `pengu-hir` construye la HIR de nombres (C1).

## Crates

| Crate | Responsabilidad |
|---|---|
| `pengu-span` | `FileId`, `Span`, `Spanned<T>` |
| `pengu-vfs` | archivos, overlays, líneas/columnas |
| `pengu-diag` | diagnósticos y etiquetas |
| `pengu-syntax` | lexer, AST, parser, CST, límites y formato base |
| `pengu-hir` | HIR de módulos, nombres y scopes (C1) |

## Recuperación de errores

- Cada error sintáctico tiene código `PGS-*` y span.
- El parser consume hasta `NEWLINE`, `DEDENT` o un token de sincronización y
  continúa; el árbol puede quedar parcial.
- `ParsedProgram`, `ParsedDeclaration` y `ParsedExpr` conservan el CST aunque
  el AST no se pueda construir.
- El tope es **100 diagnósticos por archivo** para evitar cascadas.

## Límites

| Recurso | Límite | Diagnóstico |
|---|---:|---|
| Tamaño de archivo | 10 MiB | `PGS-E1901` |
| Líneas | 200 000 | `PGS-E1901` |
| Profundidad de delimitadores/indentación | 1 000 | `PGS-E1901` |
| Diagnósticos por archivo | 100 | se trunca |

Los límites viven en `crates/pengu-syntax/src/limits.rs`. `lex()` corta antes
de tokenizar un archivo demasiado grande; el parser corta antes de construir un
árbol demasiado profundo. El umbral de profundidad se rechaza **al alcanzar**
1 000 para no agotar la pila del parser/CST.

## Fuzz

`crates/pengu-syntax/tests/fuzz_smoke.rs` ejecuta, de forma determinista:

- **10 000 000 de tokens** léxicos (10 chunks de 1M) sin pánico.
- 128 fuentes pseudoaleatorias contra `parse_program` y `parse_expression`.
- Anidamiento extremo: 1 000 delimitadores -> `PGS-E1901` sin pánico.

No usa `cargo-fuzz` ni dependencias externas. Es un smoke test reproducible,
no un reemplazo de un fuzzer con cobertura.

## Formato y CST

`SyntaxTree::reconstruct()` devuelve exactamente el fuente original. Sobre esa
base, `format_source()` y `format_declaration()` exponen una reconstrucción
estable desde el CST. El formateador de F6 es conservador (no reordena ni
reescribe espacios); las reglas de estilo se añadirán en la fase de CLI.

Gate F exige que `pengu fmt` pueda reconstruir desde el CST; la capacidad
binaria se implementa en la fase de CLI. Aquí queda la API y su test.

## Evidencia de Gate F

```sh
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo fmt --all -- --check
python3 scratch/tools/check_rewrite.py
python3 scratch/tools/check_pengu_blocks.py
```

Cobertura actual:

- 148 bloques `pengu` de la especificación: 143 válidos + 5 marcados
  `-- ERROR PGS-` (semánticos).
- Todas las producciones de §19 tienen parser y test (unidades + corpus).
- 10M tokens de fuzz léxico sin pánico.
- `reconstruct()` exacto sobre el corpus y sobre fuentes con BOM/CRLF/trivia.
