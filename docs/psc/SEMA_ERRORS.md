# Diagnósticos semánticos (F3)

`sema/diagnostics.pengu` centraliza códigos y helpers. Todos llevan span de byte
(`start`/`end`), mensaje, help y note opcionales; `std.diagnostic` los renderiza
en plain/ANSI/JSON.

| Código | Significado |
|---|---|
| `E0000` | error de parseo (lo emite F2 y se propaga) |
| `E0004` | identificador, función, tipo, miembro, import o módulo no resuelto |
| `E0003` | `self` de un primitivo usado con `.`/`->` |
| `E0005` | tipo incompatible; expresión/target inválido; índice no indexable; patrón de `judge` inválido |
| `E0006` | asignación a un binding inmutable o al `self` valor |
| `E0007` | `break`/`continue` fuera de un loop |
| `E0008` | `banish` de un valor sin ownership (`derive Nexus`) |
| `E0013` | campo inexistente en una runa/eco |
| `E0019` | expresión de interpolación `{...}` inválida |
| `E0020` | valor de retorno incompatible con la firma |
| `E0022` | parámetro de tipo usado fuera de un `shard` genérico |
| `E0032` | el tipo no satisface un bound de concepto |
| `E0044` | `judge` no exhaustivo |
| `E0047` | método duplicado incoherente sobre un primitivo |
| `E0049` | operador no concedido por el bound / tipo sin `donum` |
| `E0066` | método `@mutates` usado como expresión |
| `E0067` | `@mutates` mal colocado, con argumentos o retorno incorrecto |
| `E0069` | label de loop duplicado |

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
