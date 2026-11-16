# Gate C — auditoría de la Fase 2

Fecha: 2026-11-13
Estado: **PASA** (con 5 diagnósticos justificados y rendimiento pendiente del CLI)

## Criterios

| Criterio | Estado | Evidencia |
|---|---|---|
| Todos los ejemplos válidos checkean | **PASA** | Corpus de checker (`corpus_check.rs`): 8 válidos, 6 inválidos, 3 fragmentos; 14 tests. |
| Cada código de §20 tiene test negativo o justificación | **PASA** | 155 emitidos + 5 justificados = 160/160; `scratch/tools/check_diagnostics.py`. |
| Sin `panic!`/`unwrap` ante input inválido | **PASA** | Fuzz de 300 entradas; se corrigieron overflow en `resolve_type_path` y bordes de profundidad. |
| Ownership suite verde | **PASA** | `pengu-check/tests/ownership.rs`: 28 tests. |
| Const eval y `.d.pengu` verdes | **PASA** | Tests de const/FFI/derives y declaraciones; 449 workspace. |
| `pengu check` < 2 s para 10k líneas | **NO MEDIDO** | No existe el binario `pengu`; se medirá al cerrar el CLI. |

## Justificaciones

Los cinco códigos diferidos y su motivo están en
`scratch/DIAGNOSTIC_JUSTIFICATIONS.md`: `E1205`, `E1506`, `E1705`, `E3007`,
`W1210`. No se cuentan como implementados.

## Veredicto

Fase 2 (C1–C8) y Gate C quedan cerrados en lo que respecta a checker,
diagnósticos, corpus y runner. La medición de rendimiento queda explícitamente
diferida al CLI.
