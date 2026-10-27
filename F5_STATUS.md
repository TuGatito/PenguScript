# F5 — estado de implementación

> Actualizado durante la sesión de implementación. Este archivo es un
> **reporte de estado**, no el plan aprobado (`PLAN_F5_DRIVER.md`).

## Completado y verificado

| Área | Estado |
|---|---|
| F5a self-compile gate | `psc emit-c psc/src/main.pengu` compila con **gcc, clang y TCC** sin errores (`-Wall -Wextra -Werror` con gcc) |
| Smoke | El binario resultante responde `version`, `check` y `build` |
| F1–F4 | Suites verdes (43 passed, 5 skipped; goldens actualizados) |
| Driver | `psc build`, `psc run`, `psc expand` para archivo y proyecto |
| Manifiesto | `pengu.toml` (project/build/profiles) con `std.toml` |
| Runtime | Descubrimiento de `libpengu_runtime.a`, `pengu_runtime.h`, `std/`, `std_c/` |
| Compiladores | gcc, clang y TCC probados con `psc build` |
| Bootstrap etapa 1 | stage1 compila PSC → **stage2** correctamente |

## Bloqueo actual (honesto)

El **checker de stage2 ya funciona**: `stage2 check psc/src/main.pengu` y los
imports cualificados (`foo.hi`, `spark.println`) pasan. El bloqueo se movió a la
**generación de C de stage2** al construir stage3:

- `arena_arena_alloc_inst` colisiona entre instanciaciones genéricas de tipos
  distintos (`JsonEntry` vs `JsonValue`).
- Algunas interpolaciones de campos/`p->campo` siguen emitiendo argumentos
  vacíos (`%s` con `pengu_string_from_cstr("")`).
- Returns sin valor / expresiones vacías en `std.diagnostic` y `std/arena`.

Stage2 compila PSC y genera C sintácticamente mucho más cerca de stage1, pero
todavía no produce un bundle C compilable para stage3. Por eso:

- `stage1` (construido por stage0) es correcto y se auto-compila.
- `stage2` (construido por stage1) **se construye y ya checkea PSC**, pero su
  codegen no completa stage3.
- El **punto fijo stage2 == stage3** no se ha alcanzado.

## Qué falta para cerrar F5

1. Corregir el codegen de stage2: nombres únicos de instanciaciones genéricas,
   interpolación de campos/accesos `->` y returns/expresiones vacías.
2. Reconstruir stage1 → stage2 → stage3 y comparar el C normalizado.
3. Ejecutar el corpus 66 con el driver (no con el runner de F4) y ASan.
4. Añadir tests F5 y `docs/selfhost/BOOTSTRAP.md`.

## Notas de implementación

- `psc/tools/selfhost_preflight.py` es la métrica objetiva de F5a.
- `psc/src/psc/driver/{paths,manifest,toolchain,build}.pengu` y
  `psc/src/psc/cmd/build.pengu` son el driver.
- Cambios de F5a: identidad canónica de módulos, declaradores de punteros a
  función, scopes de `defer`, evaluación comptime, `to string`, consts
  cualificadas, igualdad de strings, listas literales, indexación con `ref`,
  nombres C por módulo y defaults de `judge`.
- TCC es obligatorio en el gate y funciona con el driver y con el auto-compilado.
