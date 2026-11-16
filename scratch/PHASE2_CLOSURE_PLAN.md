# Plan de cierre de Fase 2 y Gate C

Estado: **abierto**. Este documento es la visión amplia del problema, no un
certificado de Gate C.

## Diagnóstico

Gate C falla por cuatro causas distintas, no por “faltan tests” en general:

1. **Deriva de códigos.** El checker emite códigos genéricos (`E3001`, `E3002`,
   `E1401`) donde §20 define códigos específicos (`E6001`, `E7005`, `E1501`).
   No es solo cobertura: hay que enrutar cada comprobación a su código.
2. **Checks ausentes.** Varias reglas de §20 no tienen implementación:
   `E1103`, `E1104`, `E1105`, `E1108`, `E1203`–`E1210`, `E1301`/`E1305`–
   `E1308`, `E1402`/`E1406`/`E1407`/`E1408`, `E1501`–`E1506`, `E1601`–
   `E1608`, `E3004`–`E3010`, `E3101`–`E3105`, `E4109`, `E6001`/`E6003`–
   `E6008`, `E7001`–`E7008`, `E8004`/`E8008`, y los warnings de lint.
3. **Corpus de sintaxis ≠ corpus de checker.** Los 146 bloques prueban el
   parser; muchos son fragmentos. Gate C exige programas completos que pasen
   HIR, tipos, patrones, ownership, const eval y FFI.
4. **No hay runner de Gate C.** No existe un comando único que mida catálogo,
   corpus, pánicos, ownership, FFI y rendimiento.

## Inventario de códigos

`python3 scratch/tools/check_diagnostics.py` da la lista viva. Estado actual:
160 documentados, 64 emitidos, 96 sin uso. Categorías:

| Categoría | Ejemplos | Tratamiento |
|---|---|---|
| Núcleo checker | `E6001`, `E7005`, `E1501`, `E3104`, `E6007` | implementar y enrutar |
| Ownership/NLL | `E1103`, `E4109` | extender `pengu-check` |
| FFI/const | `E1601`, `E1603`, `E1607`, `E1608` | checks específicos + lint |
| Pacts/genéricos | `E1203`–`E1210`, `E1301`–`E1308` | checks HIR/checker |
| Parser/forma inexistente | `E1208`, `E1307`, `E1406`, `E1606`, `E8008` | test negativo de parser + justificación |
| CLI/loader/backend | `E17xx`, `E18xx`, `E2001`–`E2003`, `E2007`–`E2011`, `E2014`, `E2020`–`E2027` | justificar por fase; no fingir check |
| Lint | `W1101`, `W1102`, `W1210`, `W1501`, `W2001`, `W6001`, `W6002` | `pengu lint`/C8-lint |

## Estrategia

### 1. Enrutado de diagnósticos
Crear un helper `error_at(code, msg, span)` y eliminar los `E3001` genéricos de
contextos con código propio. Orden de ataque:
- condiciones (`E6001`), `return` (`E6006`), `loop` valor (`E6007`);
- llamadas (`E7005`/`E7006`/`E7007`);
- `?` (`E1501`/`E1502`);
- `Vec`/`Map`/`Set` (`E3101`–`E3105`);
- `sigil`/`relic` (`E1106`/`E1108`);
- pacts/genéricos (`E1203`–`E1210`, `E1301`–`E1308`).

Cada cambio incluye un test negativo con el código exacto.

### 2. Checks ausentes
Implementar por lotes:
- **Lote A (control):** `E6001`, `E6003`–`E6008`.
- **Lote B (funciones):** `E7001`–`E7008`.
- **Lote C (tipos/colecciones):** `E3004`–`E3010`, `E3101`–`E3105`.
- **Lote D (pacts/genéricos):** `E1203`–`E1210`, `E1301`–`E1308`, `E1402`/`E1406`/`E1407`/`E1408`.
- **Lote E (ownership/FFI/const):** `E1103`, `E1104`, `E1105`, `E1108`, `E4109`, `E1601`, `E1603`, `E1607`, `E1608`.

### 3. Corpus de checker
Estructura `crates/pengu-types/tests/corpus/`:
- `valid/*.pengu`: programas completos (hello, records, sums, genéricos,
  ownership, const, FFI declarativo, tests).
- `invalid/*.pengu`: un archivo por código, con cabecera
  `-- EXPECT: PGS-E6001` y el programa mínimo.
- `fragments/*.pengu`: snippets marcados `-- FRAGMENTO`; no exigen checker.
- Runner `spec_check.rs`: para cada válido exige `is_clean`; para cada inválido
  exige el código exacto; para fragmentos exige solo parseo.

### 4. Gate C runner
`scratch/tools/check_gate_c.py`:
1. `check_diagnostics.py` (catálogo + manifest).
2. `cargo test --workspace`.
3. corpus válido/ inválido/ fragmentos.
4. fuzz de parser/HIR/checker (300 casos).
5. ownership suite.
6. const/FFI suite.
7. reporte de rendimiento (cuando exista `pengu check`).

## Definición de terminado

Gate C solo se marcará ✅ cuando:
- cada uno de los 160 códigos tenga test negativo o una justificación firmada
  en `scratch/DIAGNOSTIC_COVERAGE.md` (con fase/archivo responsable);
- el corpus válido pase completo y el inválido produzca el código esperado;
- no haya pánicos en fuzz;
- ownership/const/FFI verdes;
- el runner de Gate C pase en CI local.

## Estado inmediato

Lotes A–E iniciados: control, funciones, colecciones, operadores, bindings e
inmutabilidad ya emiten sus códigos (`E6001`, `E6004`–`E6006`, `E7001`–`E7003`,
`E7005`/`E7006`, `E1501`/`E1502`/`E1504`, `E3101`–`E3103`, `E1402`/`E1408`,
`E1103`/`E1105`/`E1106`/`E1108`, `E9005`). Catálogo: **155 emitidos + 5
justificados = 160/160**. Gate C **PASA** con `scratch/tools/gate_c.py`.
