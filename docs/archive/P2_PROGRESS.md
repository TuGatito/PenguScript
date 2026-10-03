# P2 progress (handoff)

Última actualización: P2 completado y auditado · Agentes: gemini 3.8 flash (implementación) + auditoría posterior

> Este documento lo **actualiza el agente que implementa P2 tras cada hito** (ver `prompt.md` §7).
> El bloque de baseline no debe borrarse: sirve para distinguir una regresión de P2 de algo preexistente.
>
> **Nota de auditoría:** la versión anterior de este fichero era contradictoria (la tabla marcaba
> P2.1/P2.5 como hechos y la sección "lo que falta" decía que P2.1 estaba pendiente, y el baseline citaba
> 762 tests en vez de 767). Se ha reescrito con el estado **verificado**.

## Baseline (verificado antes de empezar P2)

- **Suite completa:** `767 passed, 1 skipped` (`.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider`).
- **P0 cerrado:** exit status de `weave main`, directivas `#line`, caché del builder por contenido,
  `pengu_init(argc, argv)`, versiones unificadas (`VERSION` + `pengu --version`).
  Tests: `tests/test_p0_toolchain.py`.
- **P1 cerrado y auditado:** varargs de C (`declare …, ...`), arrays de structs sin E0011 espurio,
  `(xs length)` correcto, indexado de punteros + `ffi.slice_from_ptr shard T`, raymath (shim + binding).
  Tests: `tests/test_p1_features.py` (23, incluye `TestAtIndexSemantics`).
- **Ports raylib que compilan y ejecutan:** `scratch/port/01..05_*.pengu`.
- **Integración:** los 50 módulos de `std/` chequean juntos; `regen_std_bindings.py --check` →
  `written=0 would-write=13 skipped=11` (11 artesanales se saltan a propósito).
- Herramienta de árbol: **sin commits**.

## Estado por hito (verificado por el auditor, no solo por los tests del agente)

| Hito | Estado | Evidencia de la auditoría independiente |
|------|--------|------------------------------------------|
| P2.2 arrays 2D | ✅ | programa propio compilado y ejecutado: `float m[2][3]`, `rows=2 cols=3`, escritura `set m at 1 at 0` correcta, **sin `[None]`**; filas desiguales → `E0041`; `var m as array of array of i32 with size 2 is []` → `E0015` con help |
| P2.4 banish string/list/map | ✅ | bucle de 200 strings + `banish s` + `banish l` + `banish m` compila, ejecuta (`total=890`) y el C contiene `pengu_banish_string/list/map`; literales, `const` y `frozen` → `E0008` |
| P2.3 estado de módulo | ✅ | documentado en `LANGUAGE.md` §14.5 y `CHEATSHEET.md` §13.6; test ejecutable de dos módulos con persistencia; `E0002` sugiere los idiomas. Sin cambios de semántica del compilador |
| P2.1 rlgl | ✅ | `std/rlgl.d.pengu` con `import std.raylib` y **sin** `rune Matrix` duplicado (solo `rlDrawCall`/`rlVertexBuffer`/`rlRenderBatch`); programa propio con `import std.raylib` + `import std.rlgl` + `rlPushMatrix`/`rlTranslatef`/`rlPopMatrix` compila y ejecuta; `scratch/port/06_rlgl_solar_system.pengu` compila y ejecuta (~120 frames) |
| P2.5 punteros estrictos | ✅ | 6 negativos rechazados (`ref i32→ref char`, `ref i32→ref byte`, `ref u8→ref char`, `array i32→ref char`, `ref f32→ref f64`, `frozen→mutable`) y 4 positivos aceptados (`bytes of`→`ref to frozen char`, `sigil of f32`→`ref to void`, ampliación numérica `int`→`i64`); 50 módulos std limpios |
| P2.6 pengu bind real | ✅ | `pengu bind zlib.h --define Z_SOLO --links z` desde la CLI → 50 declares y el binding pasa `pengu check`; `sqlite3.h`/`rlgl.h` sin regresión; un header que falla (`xxhash.h`) da diagnóstico con `Tip 1: --define/--cpp-flags` y `Tip 2: --no-blank-extensions` |

## Tests

- `tests/test_p2_features.py`: **34 tests** (`TestArray2D` 6, `TestBanishCollections` 5, `TestModuleState` 3,
  `TestRlgl` 2, `TestStrictPointers` 12, `TestPenguBind` 5 + 1 añadido por la auditoría para el valor por
  defecto de `blank_extensions`).
- Suite completa: `800 passed, 1 skipped` → tras el arreglo del test del CLI, **801 passed, 1 skipped**
  (verificado al cerrar; el fallo era solo el nombre del `dest` del flag `--no-blank-extensions`).

## Lo que dejó incompleto el agente y se completó aquí

1. **`tests/test_p2_features.py::TestPenguBind::test_bind_cli_flags`**: asertaba
   `args.no_blank_extensions`, pero el CLI (correctamente) usa `--no-blank-extensions` con
   `dest="blank_extensions"` y `store_false`. Arreglado el test (+ test del valor por defecto).
2. **`CHANGELOG.md`**: no había sección de P2 → añadida `### P2 — Breadth and safety`.
3. **`PRODUCTION_READINESS.md`**: §7 seguía listando P2 como pendiente → marcado ✅ con la evidencia, y
   la tabla de veredicto y el "bottom line" actualizados.
4. **`CHEATSHEET.md`**: la tabla CLI de `bind` no listaba los flags nuevos, y §14.8 no los documentaba →
   añadidos (con la tabla de flags, el ejemplo de `zlib` y la nota de headers que aún necesitan ayuda).
5. **`README.md`**: el bloque beta seguía diciendo que `pengu bind` "necesita stubs para casi todos los
   headers" y que P0/P1/P2 estaban pendientes → actualizado, más el bullet de la feature `pengu bind`.
6. **Sanitización de nombres en `pengu_bind` (bug funcional)**: el agente renombraba *todos* los
   miembros y parámetros que fueran palabra clave o nombre de tipo (`type`→`_type`, `size`→`_size`,
   `opaque`→`_opaque`). Eso **bloqueaba la regeneración** de `std/nanosvg.d.pengu` y
   `std/typis.d.pengu` (usan esos nombres de miembro) y cambiaba la API generada sin necesidad:
   verifiqué que **ningún** nombre rompe un `declare` ni un `rune`. Política corregida y basada en
   evidencia: los miembros nunca se renombran, los parámetros de `declare` conservan su nombre (salvo
   `self`/`type`) y **solo los alias de callback** sanean los nombres tipo-token (`opaque`, `void`,
   `int`, los tipos de ancho fijo, `null`), que sí rompen `fn_param`
   (`alias Cb as ref to weave with opaque as voidpf` = error de sintaxis). Tests nuevos en
   `TestPenguBind` y `regen_std_bindings.py --check` de vuelta a 13 bindings idénticos.
7. **`std/rlgl.d.pengu`**: el comentario automático decía que `rlgl.h` incluye `raylib.h` (falso: no lo
   incluye, por eso el `import std.raylib` es manual). Documentado el motivo y por qué el regen lo salta.

## Lo que sigue pendiente (fuera de P2, para P3)

La re-análisis posterior a P2 (batería de programas reales: juego raylib sin assets, bind+uso de
zlib, proyecto multi-módulo con glue C, perfil release `-O2`, 20 000 strings con `banish`) está en
`PRODUCTION_READINESS.md` §9, con la lista priorizada crítica→opcional. Resumen de lo que queda:

- **CRÍTICO C1**: `modulo.CONSTANTE`/`modulo.VARIANTE` (forma desnuda cualificada) genera
  `modulo_CONSTANTE` → C inválido (el `check` pasa). Afecta a raylib (flags, uniform types, enums).
  Funcionan la forma sin cualificar y la anidada `modulo.Omen.VARIANTE` (documentado en
  `LANGUAGE.md` §14.2 como interino).
- **CRÍTICO C2**: literales con `{…}` (¡shaders GLSL!) necesitan raw string y el `E0000` no lo dice.
- **CRÍTICO C3**: `restrict` en todo parámetro `ref to T` (UB con APIs que solapan buffers).
- **ALTO H1**: `pengu bind` no emite los `typedef` primitivos que viven en headers compañeros
  (`uLong`/`uInt`/`Bytef` de zlib): el binding se genera pero sus APIs son inusables sin alias a mano.
- **ALTO H2**: divergencias `check` vs codegen aún vivas: `printf` desnudo (solo `include`), array
  literal como argumento, `declare … many T`.
- **MEDIO**: sin aritmética de punteros (`p + 1`), sin bounds checking, sin `pass` para bloques vacíos,
  headers vendor que aún necesitan flags.

## Bloqueos y decisiones

- Ninguno. Decisión de diseño mantenida: **no** hay `var` de nivel de módulo; el estado por módulo se
  expresa con `static var` privado + accessors o con un struct de contexto pasado por `ref`.
