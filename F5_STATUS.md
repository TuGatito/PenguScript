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

El **stage2** (PSC compilado por PSC) compila PSC y genera stage2, pero su
**checker** falla al resolver llamadas cualificadas de módulos importados:

```text
psc: undefined function 'foo'   # calling foo.hi
psc: undefined function 'spark' # calling spark.println
```

Los imports se cargan y el alias existe en la tabla de símbolos (se verificó
con trazas), pero la resolución del miembro del módulo (`foo.hi`) no lo
encuentra en el scope del módulo destino. Es un problema de **enlace de scopes
en el F3 compilado por PSC**, no de sintaxis ni de carga de módulos. Por eso:

- `stage1` (construido por stage0) es correcto y se auto-compila.
- `stage2` (construido por stage1) **se construye**, pero no puede compilar
  stage3 todavía.
- El **punto fijo stage2 == stage3** no se ha alcanzado.

## Qué falta para cerrar F5

1. Corregir el enlace de scopes/imports en el F3 que ejecuta stage2
   (`sema/symbols/table.pengu`, `sema/check/collect.pengu`, `sema/infer/core.pengu`).
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
