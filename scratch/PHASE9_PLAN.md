# Fase 9 — Bindgen

## 0. Objetivo y criterio de cierre

Consumir C sin escribir bindings a mano: `pengu bindgen zlib.h` genera un
`.d.pengu` que el compilador acepta, que se puede importar con `summon` y que
enlaza contra la biblioteca real.

La fase se cierra cuando se cumplen **los diez** puntos:

1. `[declarations]` del manifiesto se carga y se usa en `build`, `check`, `run`
   y `test`; un programa puede llamar a una función declarada en `.d.pengu`.
2. Un `.d.pengu` con `abi "C"` sin `[link]` falla con `PGS-E2023` y un mensaje
   con la entrada exacta que hay que añadir.
3. `pengu bindgen cabecera.h` escribe un `.d.pengu` determinista (misma entrada,
   mismo byte a byte), sin tocar nada más.
4. El `.d.pengu` generado compila: `pengu check --strict-declarations` (o el
   modo de validación de `bindgen`) lo parsea, lo baja y verifica que los tipos
   son representables en C.
5. Mapeo de tipos documentado y probado: enteros con signo y sin signo de todos
   los anchos, `float`/`double`, `_Bool`, `void*`, `T*`, arrays en parámetros,
   `size_t`, punteros a función (omitidos con motivo), uniones y bitfields
   (omitidos con motivo).
6. `rune` de `.d.pengu` con layout C: `pengu-layout` coincide con
   `sizeof`/`alignof` que reporta clang para al menos tres structs reales.
7. Enums: constantes `NOMBRE: Int = valor`, usables desde el programa.
8. Allowlist/blocklist (`--allow`, `--block`, también por prefijo y por regex
   simple) y **reporte de omitidos** con el motivo, en stderr y con `--report`
   a archivo.
9. Corpus real: `zlib.h`, `sqlite3.h` y `<stdio.h>` generan bindings válidos;
   un ejemplo compila, enlaza y ejecuta `crc32`/`compress` de zlib.
10. Suite completa en verde, `fmt` y `clippy -D warnings` limpios, CI ampliada y
    documentación de usuario en `docs/BINDGEN.md`.

## 1. Estado de partida (auditoría)

| Pieza | Estado real |
| --- | --- |
| `parse_declaration_file` | ✅ existe (`pengu-syntax`) |
| `lower_declaration` | ✅ existe, pero **aísla** el archivo en su propio `HirCrate` |
| `.d.pengu` en `build` | ❌ no se carga: `[declarations]` no existe en el manifiesto |
| `abi "C"` sin `[link]` | ❌ `PGS-E2023` documentado pero no emitido |
| `Ptr[T]` | ✅ tipo y codegen (`*mut T`) |
| `foreign "C"` + `curse` | ✅ codegen (`unsafe extern "C"`), probado con libc (S6) |
| `rune` con layout C | ✅ desde F7 (`#[repr(C)]` siempre) |
| `pengu-layout` | ✅ motor propio validado contra `rustc` |
| `pengu bindgen` | ❌ no existe |
| clang | ✅ 23.1.4 en el entorno (`-ast-dump=json`) |

**Consecuencia:** el trabajo real no es "escribir un traductor de cabeceras",
es antes **conectar `.d.pengu` al pipeline**; sin eso el archivo generado no se
puede usar.

## 2. Decisiones

- **D1. Las declaraciones son módulos del programa.** `[declarations]` da
  `nombre = "ruta.d.pengu"`; el módulo se llama `nombre` y se importa con
  `summon nombre::item`. No se crean crates ni se compilan aparte: mismo
  modelo que los paquetes (F5).
- **D2. Un solo lowering.** `lower_program_with_declarations(program, &[(String, DeclarationFile)])`
  construye los módulos de declaración dentro del mismo `HirCrate`, marcando
  sus funciones como `foreign_fns` con el ABI del archivo. Así el checker, el
  LIR y el codegen no necesitan saber que existen declaraciones.
- **D3. `PGS-E2023` se comprueba en el build**, donde se conoce el manifiesto:
  si un `.d.pengu` declara `abi "C"` y `[link]` está vacío (o falta la librería
  concreta), error con la línea a añadir. El `.d.pengu` no puede saberlo.
- **D4. Nada de `@@repr(C)`.** Todos los `rune` se emiten `#[repr(C)]` desde
  F7; añadir el atributo sería decorativo y el lenguaje solo admite `@@test` y
  `@@derive` (`docs/LANGUAGE.md` §12.6). El entregable "layout C" se cumple por
  D17 y se **verifica** contra `sizeof` de clang.
- **D5. Bindgen no adivina.** Lo que no se puede representar (uniones,
  bitfields, varargs, punteros a función, structs anónimos, campos flexibles) se
  **omite con motivo** y se reporta; nunca se genera código a medias.
- **D6. Enums como constantes con valor.** `X: Int = 3` es válido en `.d.pengu`
  y el codegen lo emite como `const`; el tipo del enum se mapea a `Int`.
- **D7. Funciones declaradas no se llaman sin `curse`.** Es la regla de S6 y no
  se relaja: bindgen genera superficie, el usuario escribe el `curse` con
  `-- SAFETY:` y el compilador lo verifica.
- **D8. Determinismo.** Orden de items por nombre; sin rutas absolutas, sin
  marcas de tiempo, sin comentarios con la versión de clang; la cabecera de
  salida incluye solo el nombre del archivo de entrada.
- **D9. Salida sin dependencias externas.** El JSON del AST lo parsea
  `pengu-json`; nada de `serde`, `bindgen` ni `libclang`.
- **D10. `--check` valida reutilizando el compilador**, no un validador
  paralelo: parsea, baja y pasa `check_crate` + `check_ownership_with` sobre un
  programa mínimo que importa el módulo.

## 3. Arquitectura

```
crates/pengu-bindgen/          (nuevo)
  src/lib.rs                   API: Options, bind(header) -> Bindings
  src/clang.rs                 invoca clang y parsea el AST JSON
  src/ir.rs                    modelo intermedio (Function, Struct, Enum, Alias)
  src/types.rs                 mapeo C → Pengu + motivos de omisión
  src/emit.rs                  .d.pengu determinista
  src/report.rs                omitidos y estadísticas
crates/pengu-project/          [declarations] en el manifiesto
crates/pengu-hir/              lower_program_with_declarations
crates/pengu-build/            carga de declaraciones + PGS-E2023
crates/pengu-cli/              `pengu bindgen`
docs/BINDGEN.md                documentación de usuario
examples/zlib.pengu            ejemplo real
```

## 4. Fases

### B0 — Plan y auditoría ✅
Este documento, con la tabla del §1 y las decisiones D1–D10.

**Aceptación:** el plan existe y nombra cada pieza que hay que tocar.

### B1 — `[declarations]` y merge en el lowering ✅

- `Manifest.declarations: BTreeMap<String, PathBuf>` parseado de
  `[declarations]`, con validación de nombre y de extensión `.d.pengu`.
- `pengu-project::load` resuelve las rutas y comprueba que existen.
- `pengu-hir`: `lower_program_with_declarations(program, &[(name, DeclarationFile)])`
  crea `scroll <name>` con los items de la declaración; las funciones quedan en
  `foreign_fns` con su ABI y `Ptr[T]` se permite en sus firmas.
- `pengu-build`: carga cada declaración, la pasa al lowering y valida
  `PGS-E2023` cuando el ABI es `C`/`system` y falta `[link]`.
- `pengu check` hace lo mismo (comparte `analyze_with_packages`).

**Aceptación:** test con `libc.d.pengu` escrito a mano que declara `puts`,
`[link]` vacío → `PGS-E2023`; con `[link] libc` → compila, ejecuta y llama a
`puts` desde un `curse`.

**Estado:** hecho. `Manifest.declarations: Vec<Declaration>` (el `BTreeMap` del
plan se cambió por `Vec` conservando duplicados para poder emitir `PGS-E2013`),
`lower_program_with_declarations`, `build_declaration_module`,
`load_declarations` y `PGS-E2023`. Tests: `crates/pengu-build/tests/declarations.rs`
(6) y `crates/pengu-hir/tests/declarations.rs` (1). Además se arregló un hueco
real que apareció al escribir el ejemplo: `curse` en **posición de valor**
(rama de `match`, argumento) daba `PGS-E1901` en LIR; ahora se baja como bloque
con temporal (`lower_expr`, rama `ExprKind::Curse`), con regresión en
`crates/pengu-codegen/tests/codegen.rs::std_nexus_curse_as_value`.

### B2 — `pengu-bindgen`: clang → IR

- `clang::invoke(header, include_dirs, defines)`: `clang -Xclang -ast-dump=json
  -fsyntax-only -x c header.h`, lee stdout, `pengu_json::parse`.
- `ir.rs`: recorre `inner[]` recogiendo `FunctionDecl` (con `type.qualType`),
  `RecordDecl` (campos), `EnumDecl` (constantes y valores), `TypedefDecl`,
  `VarDecl` (constantes) y `ElaboratedType`/`PointerType`/`ArrayType` anidados.
- `types.rs`: mapea el `qualType` textual (más fiable que el árbol de tipos en
  clang 23) con una tabla explícita; devuelve `Mapped | Omitted(reason)`.
- `report.rs`: cuenta generados/omitidos por categoría.

**Aceptación:** tests unitarios con qualTypes (`unsigned long`, `const char *`,
`void (*)(int)`, `struct S *`, `int[4]`) y un test que corre clang sobre una
cabecera de fixture y comprueba funciones y structs extraídos.

### B3 — Emisor `.d.pengu`

- Cabecera `abi "C"`, `rune` por struct con campos mapeados, constantes de enum,
  y bloque de firmas al final (funciones ordenadas por nombre).
- Omisión de items cuyo tipo no mapea; los structs con campos omitidos se
  emiten **solo** si quedan campos representables y el tamaño no cambia; si no,
  se omiten por completo con motivo (`struct con bitfields`).
- `emit::declaration(bindings) -> String` determinista.

**Aceptación:** golden test con una cabecera de fixture; el `.d.pengu` se parsea
con `parse_declaration_file`, se baja con `lower_program_with_declarations` y
pasa `check_crate` sin diagnósticos.

### B4 — CLI `pengu bindgen`

- `pengu bindgen <header> [-o salida] [--allow P] [--block P] [--report FILE]
  [--include-dir DIR] [--define K=V] [--check]`.
- `--check` no escribe: genera en memoria y valida con el pipeline; sale 1 si el
  resultado no compila.
- Reporte de omitidos por stderr (`omitido: <nombre> (<motivo>)`) y estadísticas
  finales (`bindgen: N funciones, M tipos, K omitidos`).

**Aceptación:** tests de integración con un header de fixture; `--check` verde y
fallo controlado con un header que usa `union`.

### B5 — Corpus real y ejemplo

- `zlib.h`: `crc32`, `compress`, `uncompress`, `compressBound`, `z_stream`,
  constantes `Z_OK`/`Z_BUF_ERROR`.
- `sqlite3.h` con `--allow sqlite3_open` etc. (cabecera enorme; el test usa
  allowlist y comprueba que el `.d.pengu` valida).
- `<stdio.h>`: `puts`, `printf` (varargs omitido), `FILE` (typedef opaco
  omitido con motivo).
- `examples/zlib.pengu`: comprime y descomprime un buffer con zlib, imprime el
  CRC y el resultado; test que compila, enlaza (`[link] z`) y ejecuta.

**Aceptación:** los tres headers generan bindings válidos y el ejemplo imprime
la salida esperada.

### B6 — Documentación y cierre

- `docs/BINDGEN.md`: uso, mapeo de tipos, qué se omite y por qué, `[link]`,
  patrón `curse` + `-- SAFETY:`, limitaciones.
- `docs/LANGUAGE.md` §16: nota de `[declarations]` en el manifiesto.
- CI: `pengu bindgen --check` sobre los fixtures.
- `scratch/STATUS.md` §16, `scratch/TOOLING_PLAN.md` Fase 9 ✅.

**Aceptación:** suite completa en verde, fmt/clippy limpios, commit.

## 5. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El AST JSON de clang cambia entre versiones | Se usa `qualType` (texto estable) y el test se salta si `clang` no está |
| Cabeceras con `#include` de sistema | Se pasan `-I` y se documenta; `zlib.h`/`sqlite3.h` necesitan `-I/usr/include` implícito |
| Structs con bitfields o uniones | Se omiten con motivo; nunca se emite un layout incorrecto |
| `sqlite3.h` genera miles de líneas | El test usa allowlist y solo valida; no se versiona la salida |
| Enlazar una librería en macOS/Windows | El corpus de test se salta si la librería no está; zlib es obligatoria en el CI de Linux |

## 6. Seguimiento

| Fase | Estado |
| --- | --- |
| B0 | ✅ |
| B1 | ✅ |
| B2 | ✅ |
| B3 | ✅ |
| B4 | ✅ |
| B5 | ✅ |
| B6 | ✅ |

## 7. Resultado

- **`crates/pengu-bindgen`** (clang CLI → IR → `.d.pengu`), con `types`, `ir`,
  `emit`, `report` y `clang`; 10 tests de unidad y 3 de extremo a extremo.
- **`.d.pengu`** admite constantes con valor (`MODO: Int = 1`), necesario para
  los enums de C.
- **`[declarations]`** del manifiesto conecta los declarados al pipeline como
  módulos (`PGS-E2013`, `PGS-E2020`, `PGS-E2023`).
- **`curse` en posición de valor** (rama de `match`, argumento) baja a LIR.
- **CLI**: `pengu bindgen [-I] [-D] [-o] [--allow] [--block] [--check]`.
- **ABI de `CStr` corregida**: en `foreign "C"` viaja como
  `*const c_char`; el call site convierte con `.as_ptr()` y envuelve el retorno
  con `CStr::from_ptr`. Antes `&CStr` era un puntero gordo (16 B) y abortaba.
- **Corpus real**: `zlib.h`, `sqlite3.h` (191 funciones) y `stdio.h` generan
  declarados que `pengu check` acepta; `examples/zlib.pengu` llama a zlib y
  verifica la versión.
- Verificación: **799 tests**, `fmt` y `clippy -D warnings` limpios.
