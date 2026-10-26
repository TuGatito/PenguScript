# Diagnósticos semánticos (F3)

`sema/diagnostics.pengu` centraliza códigos y helpers. Todos llevan span de byte
(`start`/`end`), mensaje, help y note opcionales; `std.diagnostic` los renderiza
en plain/ANSI/JSON.

| Código | Significado |
|---|---|
| `E0000` | error de parseo (lo emite F2 y se propaga) |
| `E0004` | identificador, función, tipo, miembro, import o módulo no resuelto |
| `E0005` | tipo incompatible; expresión o target inválido; índice no indexable |
| `E0006` | asignación a un binding inmutable |
| `E0013` | campo inexistente en una runa/eco |
| `E0020` | valor de retorno incompatible con la firma |
| `E0022` | parámetro de tipo usado fuera de un `shard` genérico |

Warnings planificados/registrados: `W0001`–`W0009` (no usado, deprecated,
shadowing, etc.). `--deny-deprecated` convierte el warning de deprecación en
error de salida.

## Formato

```
error[E0005]: type mismatch: expected 'int', got 'string'
  --> file.pengu:2:12
   |
 2 |     return "x"
   |            ^^^
   = note: PenguScript requires type safety and explicit conversions.
```

## API interna

```pengu
calling sdiag.node_error with bag, src, code, start, end, message, help, note
calling sdiag.node_warning with bag, src, code, start, end, message, help
```

`node_error` usa `start_of/end_of` del AST; `emit_error` recibe offsets. Los
códigos viven como constantes (`sdiag.CODE_*`) para que F4 y los tests no
dependan de literales.
