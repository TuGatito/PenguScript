# Diagnósticos

El catálogo normativo vive en `docs/LANGUAGE.md` §20. Este documento describe
las reglas de presentación y la cobertura verificable por herramientas.

## Contrato

- Cada diagnóstico lleva un código `PGS-E####` o `PGS-W####` del catálogo.
- Un error bloquea el pipeline; un warning no (`CheckResult::is_clean`).
- El orden es estable: archivo, offset, fin, severidad, código.
- Cada diagnóstico tiene mensaje, span primario y, cuando aplica, notas/help.
- `PGS-E2014` está reservado para errores del backend sin mapa; no se usa para
  errores del checker.
- No se añaden códigos fuera de §20.

## Herramientas

`python3 scratch/tools/check_diagnostics.py` valida que:

1. el catálogo tenga exactamente 160 códigos;
2. el código no emita ningún `PGS-*` fuera del catálogo;
3. los códigos de test sintéticos no cuenten como emitidos.

El reporte muestra cuántos códigos están emitidos y cuáles siguen reservados.
Los reservados son deuda de fases posteriores, no códigos nuevos: el catálogo
no cambia sin actualizar la spec.

## Garantías

La tabla de garantías y sus tests está en `docs/GUARANTEES.md`. El checker usa
un fuzz determinista de entradas malformadas (`crates/pengu-types/tests/fuzz_smoke.rs`)
para comprobar que parser, HIR y checker no paniquean.
