# Criticals progress (handoff)

Última actualización: 2026-09-11 C1, C2, C3 completados y verificados · Agente: gemini 3.8 flash

> Este documento lo **actualiza el agente que repara los críticos tras cada hito** (ver `prompt.md` §7).
> El bloque de baseline no debe borrarse: sirve para distinguir una regresión de un defecto preexistente.

## Baseline (verificado antes de empezar)

- **Suite completa inicial:** `804 passed, 1 skipped` (`.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider`).
- **Ports raylib 01–06** compilan (04–06 ejecutan con ventana real).
- **51 módulos de `std/`** chequean juntos: `Clean`; `regen_std_bindings.py --check` → 13 idénticos.
- **Batería de programas reales** (`scratch/readiness_battery.py`): juego raylib sin assets, bind+uso de
  zlib, proyecto multi-módulo con glue C, perfil release `-O2` y 20 000 strings con `banish` → todos en
  verde; los huecos que quedan son exactamente C1/C2/C3 y los casos listados en `PRODUCTION_READINESS.md` §9.3.
- Herramienta de árbol: **sin commits**.

## Repros exactos de los tres críticos (verificar SIEMPRE con `build`, no solo `check`)

```
C1  import std.raylib
    weave main into int:
        calling raylib.SetConfigFlags with raylib.FLAG_MSAA_4X_HINT   # C: raylib_FLAG_MSAA_4X_HINT ❌
        var d as bool is calling raylib.IsKeyDown with raylib.KEY_RIGHT
        return 0
    -> check limpio; build falla: 'raylib_FLAG_MSAA_4X_HINT' undeclared
    (funcionan: FLAG_MSAA_4X_HINT, raylib.KeyboardKey.KEY_RIGHT, raylib.RAYWHITE)

C2  weave main into int:
        var vs as string is "#version 330\nvoid main() { gl_Position = vec4(0.0); }"
        return 0
    -> E0000 genérico y mal ubicado (line 1, col 3); la solución es r"""…""" (funciona)

C3  weave poke with a as ref to int, b as ref to int into void:
        return
    -> el C generado declara 'int32_t* restrict a, int32_t* restrict b'
```

## Estado por crítico

| Crítico | Estado | Evidencia |
|---------|--------|-----------|
| C1 variantes cualificadas (`raylib.KEY_RIGHT`) | ✅ completado | `tests/test_p3_criticals.py::TestBindingOmenVariants` (4 passed); `scratch/readiness_battery.py` caso A pasa usando `raylib.FLAG_MSAA_4X_HINT`, `raylib.KEY_RIGHT`, `raylib.SHADER_UNIFORM_FLOAT` (exit=0, MSAA x4 habilitado) |
| C2 diagnóstico de interpolación (`{…}` en string) | ✅ completado | `tests/test_p3_criticals.py::TestInterpolationDiagnostics` (4 passed); error ubicado en la línea del literal, mensaje claro de expresión inválida, `code="E0019"`, y `help` sugiriendo `r"..."` / `r"""..."""` |
| C3 `restrict` en parámetros/`self` | ✅ completado | `pengu_codegen.py:1505` (`self`) y `:1509` (parámetros) sin `restrict`; `tests/test_p3_criticals.py::TestNoRestrictInGeneratedParams` (3 passed); tests adaptados en `test_compiler_core.py` y `test_p2_features.py` |

## Cambios de archivos

- `pengu_parser/pengu_checker.py` (870-878): para omens de `.d.pengu`, asignar `c_v_name = v_name`; verificar contra `self.symbols.global_scope.lookup(v_name)` para evitar sombreado por `c_define`.
- `pengu_parser/pengu_infer.py` (805-820): resolución de miembros de módulo importado verificando `field_name`, `var_name_field_name` y omens por sufijo, retornando directamente `mod_sym.type`.
- `pengu_parser/pengu_infer.py` (2720-2775): `_check_string_interpolation` captura errores de parseo y semánticos relanzando `SemanticError` con `E0019`, ubicado en la línea/columna del literal en el fichero, con mensaje descriptivo y pista hacia raw strings (`r"..."` o `r"""..."""`).
- `pengu_parser/pengu_codegen.py` (1505, 1509): eliminación de `restrict` en parámetros de funciones y métodos (`self`), manteniendo la opción opt-in en `CTypeMapper.to_c_decl`.
- `pengu_parser/pengu_codegen.py` (3791-3825): resolución de miembros de módulo importado devolviendo `self._get_omen_variant_c_name(o_logical, raw_field)` para variantes, `mod_field_sym.get_c_name()` (o `mod_const_key`/`raw_field`) para consts de `.d.pengu` respetando `insignia`.
- `tests/test_compiler_core.py` (2879, 2881): aserciones actualizadas a `Vec2* self` sin `restrict`.
- `tests/test_p2_features.py` (128): aserción de `sum_matrix` actualizada a `float (* m)[3]` sin `restrict`.
- `tests/test_p3_criticals.py`: 11 tests verdes (`TestBindingOmenVariants`, `TestInterpolationDiagnostics`, `TestNoRestrictInGeneratedParams`).
- `scratch/readiness_battery.py` (77, 104, 116): caso A actualizado para usar `raylib.FLAG_MSAA_4X_HINT`, `raylib.SHADER_UNIFORM_FLOAT`, y `raylib.KEY_RIGHT`.

## Tests

- `tests/test_p3_criticals.py`: 11 passed in 15.23s.
- Tests focalizados (`test_p3_criticals.py`, `test_p1_features.py`, `test_p2_features.py`, `test_p0_toolchain.py`): `92 passed, 1 skipped in 91.99s`.
- `tests/test_modules_bindings.py`: `46 passed in 6.73s`.
- `scratch/readiness_battery.py`: Casos A–G todos en verde (A pasó con MSAA 4x y variantes cualificadas).
- **Suite completa final:** `815 passed, 1 skipped in 378.69s (0:06:18)` (`.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider`).
- **51 módulos std/ limpios:** `.\.venv\Scripts\python.exe pengu_project.py check --entry scratch\all_std_p2_check.pengu` → Clean (0 errores).
- **Bindings sincronizados:** `.\.venv\Scripts\python.exe regen_std_bindings.py --check` → 13 idénticos, 12 omitidos, 0 escritos.
- **Raylib ports 01–06:** Los 6 compilaron exitosamente a `build/app.exe`.

## Estado de entrega

Todas las fases de `prompt.md` (§1–§8) han sido ejecutadas, verificadas y documentadas exitosamente. El árbol de trabajo se mantiene sin commits según la restricción obligatoria.

## Bloqueos y decisiones

- En C1: los omens de `.d.pengu` emiten el nombre simple (`KEY_RIGHT`), mientras que los omens definidos en `.pengu` mantienen el prefijo (`Color_Rojo`), preservando la compatibilidad con el sistema de tipos y símbolos de PenguScript.
- En C2: la interpolación válida `"score: {x}"` y las raw strings `r"""..."""` siguen intactas; cualquier fallo de sintaxis dentro de `{...}` en un string normal se diagnostica con la posición del literal y el help hacia raw strings.
- En C3: `restrict` se eliminó de la emisión por defecto de parámetros en funciones y `self`, eliminando riesgo de UB por solapamiento de buffers. `CTypeMapper.to_c_decl` conserva el parámetro `restrict=True` para casos que explícitamente lo requieran.
