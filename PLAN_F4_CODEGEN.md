# 🖨️ Plan de implementación — F4: codegen C completo

> **Estado:** **F4 cerrado**. Codegen C completo, 66/66 fixtures de
> conformidad con librerías nativas, 17 tests de aceptación F4, ASan/UBSan,
> golden C normalizado y benchmark. La matriz MSVC/TCC se difiere a F5 porque
> F4 termina en `bundle.c` y no invoca el compilador C.
>
> **Fase:** F4 del
> [`AUDITORIA_AUTO_HOSPEDAJE.md`](AUDITORIA_AUTO_HOSPEDAJE.md) §9,
> aproximadamente **12–16 persona-semanas**. No se solapa con F5: F4 termina en
> `bundle.c`; F5 empieza con el driver `build`/`run`.
>
> **Estado de implementación (actualizado):** F4 está **en curso**, no
> terminada. El esqueleto `psc emit-c`, tipos/declaraciones, expresiones y
> control básicos, `antiquus`, `#line`, DCE conservadora, interpolación simple
> y entry/ABI ya funcionan y tienen tests. Quedan métodos completos, genéricos,
> ownership (`defer`/`banish`), contenedores, `judge`/`with`/`or`, `--test`,
> DCE exacta, matriz C completa y corpus. Ver `psc/docs/CODEGEN.md`.
>
> **Regla de la fase:** cero deuda técnica. Nada de “codegen aproximado” que
> compile de casualidad: o el C es correcto y determinista, o F4 no está
> cerrada. Cada diferencia con stage0 se mide con un oráculo, no se corrige a
> ojo.

---

## 📑 Índice

0. [Resumen ejecutivo](#-0-resumen-ejecutivo)
1. [Punto de partida](#-1-punto-de-partida)
2. [Alcance y no-alcance](#-2-alcance-y-no-alcance)
3. [Arquitectura](#-3-arquitectura)
4. [Contrato F3 → F4](#-4-contrato-f3--f4)
5. [Tipos PenguScript → C](#-5-tipos-penguscript--c)
6. [Nombres, mangling y layout](#-6-nombres-mangling-y-layout)
7. [Convenciones de bajada](#-7-convenciones-de-bajada)
8. [Subfases F4a–F4l](#-8-subfases-f4a-f4l)
9. [Genéricos y monomorfización](#-9-genéricos-y-monomorfización)
10. [DCE y poda](#-10-dce-y-poda)
11. [Entry point, `--test` y ABI](#-11-entry-point---test-y-abi)
12. [Diagnósticos de C y compiladores](#-12-diagnósticos-de-c-y-compiladores)
13. [API y CLI mínima](#-13-api-y-cli-mínima)
14. [Paridad, oráculos y tests](#-14-paridad-oráculos-y-tests)
15. [Checkpoints y calendario](#-15-checkpoints-y-calendario)
16. [Rendimiento y determinismo](#-16-rendimiento-y-determinismo)
17. [Riesgos y mitigaciones](#-17-riesgos-y-mitigaciones)
18. [Decisiones que necesito de ti](#-18-decisiones-que-necesito-de-ti)
19. [Mapa Python → PSC y ownership](#-19-mapa-python--psc-y-ownership)
20. [Criterios de aceptación](#-20-criterios-de-aceptación)
21. [Anexos](#-21-anexos)
22. [Cierre](#-22-cierre)

---

## 🎯 0. Resumen ejecutivo

F4 convierte el modelo semántico de F3 en **C11 compilable, determinista y
semánticamente equivalente** a stage0. El producto de la fase no es un driver:
es un `bundle.c` completo más una API pública y un comando mínimo `psc emit-c`
para poder probarlo sin esperar a F5.

La fase se divide en doce subfases (F4a–F4l) y trece checkpoints (CP0–CP12).
Cada checkpoint produce C compilable y ejecutable para un subconjunto creciente
del lenguaje. No se acumulan “features a medio emitir”.

### Resultado esperado

| Área | Resultado |
|---|---|
| Tipos y nombres | Todo `SemaType` tiene una representación C estable; sin `_T` filtrado |
| Declaraciones | runes, echos, omens, aliases, seals, consts, `declare`, `antiquus`, includes/links |
| Expresiones | literales, operadores, casts, llamadas, métodos, campos, índices, slices, `some`/`ok`/`err`, `judge`, lambdas |
| Statements | declaraciones, `set`, control, labels/gotos, `defer`/`errdefer`, `unsafe`, `with`, `or`, `banish` |
| Genéricos | monomorfización completa, bounds, constructores `ritual`, callbacks y funciones como valores |
| Interpolación | AST cacheado por F3, escape C, bytes y UTF-8 correctos |
| Entry/test | `main`/`pengu_main`, `--test`, selector de tests y JSON |
| DCE | exacto y determinista; flags de stage0 respetados |
| C limpio | gcc/clang/tcc/MSVC según matriz; `-Wall -Wextra -Werror` |
| Diagnósticos | errores de C remapeados a `.pengu` mediante `#line`/origin map |
| Paridad | binarios ejecutables comparados con stage0; C normalizado en 20 golden |
| Memoria | ASan/UBSan limpio en el codegen y en los binarios generados |

### Lo que F4 no hace

- No implementa `pengu build`, `run`, cache, toolchain discovery ni linking de
  usuario; eso es F5.
- No implementa el CLI completo, LSP, formatter, package manager ni `pengu-bind`.
- No cambia la ABI de `pengu_runtime.h`.
- No “arregla a ojo” diferencias de stage0. Los bugs B1/B2/B2b/B11 se resuelven
  en PSC porque un codegen correcto no puede heredarlos; se documentan como
  **mejoras de PSC**, no como falsos fallos de paridad.

---

## 🧱 1. Punto de partida

### 1.1 F3 cerrada (entrada de F4)

F3 deja un contrato estable:

- `SemaProgram` (`sema/api.pengu`) con `modules`, `order`, `by_path`, `root`,
  `types`, `symbols`, `names`, `options`, `diagnostics`.
- `SemaModule` (`sema/modules/loader.pengu`) con `path`, `source`, `lex`,
  `parse.ast`, `annotations`, `is_entry`, `is_std`, `insignia`, `order`.
- `SemaAnnotations` por id de nodo (`type_id`, `symbol_id`, `aux`, flags).
- `SemaTypeTable` con interning, nominales, firmas, campos, variantes,
  type params, bounds, derived y names canónicos.
- `SemaSymbols` con scopes, registros de funciones/consts/métodos, templates e
  instancias, c_names lógicos y flags.
- `psc check` como superficie de diagnóstico y `check_file`/`check_text` como
  API.

Evidencia de F3 (ya ejecutada, no se repite en F4):

```text
corpus válido: 225 archivos aceptados
fixture negativo: coherence_conflict.pengu -> E0047
oráculo semántico: 193 casos, valid_rejected=0, invalid_accepted=0, same_code=53/53
F3 pytest: 17 passed
ASan/UBSan: limpio en núcleo y muestra representativa
```

### 1.2 Stage0 que hay que portar

`pengu_parser/pengu_codegen/*.py` son ~14 440 líneas y 27 módulos, más
`pengu_dce.py` (~350 líneas). No se porta línea a línea: se porta el
**comportamiento**, dividido por responsabilidad.

Mapa de tamaños actuales (para presupuestar, no para copiar):

| Bloque Python | Tamaño | Responsabilidad |
|---|---:|---|
| `exprs.py` | 228 KB | expresiones, accesos, llamadas, judge |
| `declarations.py` | 81 KB | recogida de declaraciones y firmas |
| `stmts.py` | 67 KB | statements y control |
| `derived_gen.py` | 50 KB | helpers derivados de conceptos |
| `symbols.py` | 44 KB | tablas de nombres |
| `bundle.py` | 38 KB | secciones, DCE, feature gates |
| `runtime_helpers.py` | 29 KB | helpers inline emitidos |
| `types_gen.py` | 29 KB | definiciones de tipos |
| `or_block.py` | 28 KB | `or`/`or else`/`or return` |
| `loops.py` | 23 KB | loops/labels/gotos |
| `interpolate.py` | 22 KB | interpolación |
| `prototypes.py` | 21 KB | prototipos/atributos |
| `value_if.py` | 18 KB | `if` como valor |
| `main.py` | 13 KB | estado del generador |
| `tests_gen.py` | 11 KB | `--test` |
| `ctype.py` | 11 KB | Type → C |
| `constants.py` | 10 KB | consts |
| `slicing.py` | 8 KB | slices |
| `ast_utils.py` | 8 KB | utilidades AST |
| `calls.py` | 6 KB | llamadas |
| `bindings.py` | 6 KB | includes/links |
| `lambdas.py` | 5 KB | lambdas |
| `line_markers.py` | 4 KB | `#line` |
| `entry.py` | 2 KB | entry point |
| `attributes.py` | 1 KB | atributos C |

### 1.3 Runtime y ABI

`pengu_runtime.h` es compartido y **no se debe cambiar su ABI**:

- `PENGU_ABI_VERSION` actual: 2.
- `PenguString`, `PenguList`, `PenguMap`, `PenguMaybe`, `PenguResult`,
  `PenguSlice`, `PenguRange`, frames y helpers de bounds/overflow.
- `pengu_init`, `pengu_install_crash_handler`, `pengu_frame_push/pop`.
- `_Static_assert(PENGU_ABI_VERSION == 2)` en el bundle.
- Helpers `static inline` sólo si son aditivos y no cambian layout; cualquier
  helper nuevo se coordina con F5 y con el runtime.

### 1.4 Tests existentes que F4 debe reutilizar

- `tests/conformance/compliance/*.pengu`: **66 programas ejecutables** que
  imprimen `OK <nombre>`.
- `tests/compiler`: 56 archivos de test; cientos de casos `parse_and_check`,
  `emit_c` y `compile_and_run`.
- `tests/stdlib`: suites ejecutables de `std` (arena, numerus, integrum,
  arithmancia, etc.).
- `tests/codegen`: compilación limpia con todos los compiladores disponibles.
- `psc/tests`: smokes de F1/F2/F3.
- `tests/psc/test_f3_acceptance.py`: corpus F3 y oráculo semántico.

F4 añade su propia suite sin romper estas.

---

## 📐 2. Alcance y no-alcance

### 2.1 Dentro de F4

1. Recoger el programa F3 y emitir un único `bundle.c`.
2. Mapear tipos, layouts, nombres y firmas.
3. Emitir declaraciones, prototipos y definiciones en orden determinista.
4. Emitir expresiones y statements completos.
5. Monomorfizar genéricos y resolver callbacks/funciones como valores.
6. Emitir interpolación, lambdas, `judge`, `with`, `or`, bloques-valor.
7. Emitir entry point normal y `--test`.
8. Emitir `#line` y un origin map para remapear errores de C.
9. Implementar DCE exacto y flags de poda.
10. Soportar gcc/clang/tcc/MSVC y C99 estricto cuando aplique.
11. API `generate` + CLI mínimo `psc emit-c`.
12. Tests, oráculos, C golden, ASan/UBSan, benchmark y documentación.

### 2.2 Fuera de F4 (por fase)

| Fuera | Fase |
|---|---|
| Invocar gcc, cachear binarios, `build`/`run`/`test` de usuario | F5 |
| CLI completo, `init`, `clean`, `doctor` | F6 |
| Cache en disco, toolchain discovery, releases | F5/F6 |
| LSP | F8 |
| Package manager / lockfile | F9 |
| `pengu-bind` | F10 |
| Formatter/docgen | F7 |
| Cambiar el runtime o el lenguaje | No se hace |
| Arreglar bugs de stage0 Python | Se documentan; PSC no los hereda |

### 2.3 “Codegen terminado” significa

- El bundle compila con `-std=c11 -Wall -Wextra -Werror` en la matriz.
- Los programas de conformidad producen **la misma salida y exit code** que
  stage0.
- El C es **byte-idéntico entre dos ejecuciones de PSC**.
- El C normalizado coincide con stage0 en los 20 golden acordados.
- No hay placeholders, `_T`, nombres C sin resolver ni warnings.
- DCE, `--test`, `--strict-c99`, `--no-line-markers`, `--prune-types`,
  `--dce-scope` y `--prune-native` tienen tests propios.
- ASan/UBSan y el codegen no filtran memoria.

---

## 🏗️ 3. Arquitectura

### 3.1 Pipeline

```text
psc check (F3)
  ├─ SemaProgram (tipos, símbolos, módulos, anotaciones)
  └─ diagnostics
        │
        ▼
codegen.api.generate(program, options)
  ├─ Catalog           (declaraciones y firmas de todos los módulos)
  ├─ NameTable         (nombres C estables, mangling, colisiones)
  ├─ Layout            (topología de tipos y forward decls)
  ├─ Generics          (especializaciones y sustituciones)
  ├─ Emit              (StringBuilder + C escaping + indentación)
  ├─ Expr/Stmt         (bajada con anotaciones F3)
  ├─ DCE               (reachability exacta)
  ├─ Bundle            (secciones ordenadas)
  └─ OriginMap         (C line -> .pengu line)
        │
        ▼
CodegenResult { bundle, origins, stats, ok }
        │
        ├─ psc emit-c   (F4)
        └─ F5 build/run (futuro)
```

### 3.2 Contexto

`CodegenContext` (heap, dueño de todo lo temporal):

```pengu
rune CodegenContext:
    program as ref to sema.SemaProgram
    options as CodegenOptions
    names as NameTable
    catalog as Catalog
    specs as SpecializationTable
    origins as OriginMap
    out as StringBuilder
    diagnostics as ref to diag.DiagnosticBag
    scopes as list of CodegenScope
    current as CurrentUnit
    temps as int
    errors as int
```

Reglas:

- `SemaProgram` es **prestado**: F4 no lo libera ni lo muta.
- El `StringBuilder` de salida es del contexto y se entrega en el resultado.
- Las tablas de nombres/especializaciones/orígenes son del contexto.
- Los scopes de C son una pila propia; no se reutilizan los `SemaScope`.
- Ningún `map` decide orden de emisión. Se usa `map` para lookup y `list` para
  orden.
- Toda interpolación temporal se bindea y se libera (`defer banish`) antes de
  usarla como argumento; no se pasan interpolaciones directas a funciones.

### 3.3 Módulos propuestos

`psc/src/psc/codegen/` con archivos de **400–800 líneas**:

```text
api.pengu                 generate(), CodegenResult
options.pengu             CodegenOptions, flags
diagnostics.pengu         C compiler issues, remapeo
emit.pengu                StringBuilder, indentación, C strings
origin.pengu              OriginMap
names.pengu               NameTable, mangling, keywords
ctype.pengu               TypeId -> C, to_c_decl, const/restrict
catalog.pengu             declaraciones, firmas, atributos
layout.pengu              orden topológico, forward declarations
types/
  records.pengu           runas/ecos/campos
  omens.pengu             omens, variantes, payloads
  aliases.pengu           alias/seal/consts
  derived.pengu           Imago/Nexus/Par/Ordo/hash/eq
decls/
  weaves.pengu            definiciones y firmas
  extern.pengu            declare/include/link/antiquus
  attributes.pengu        @inline/@noreturn/@cold/@export...
expr/
  core.pengu              dispatch
  literals.pengu          int/float/char/string/bytes
  operators.pengu         aritmética, bits, comparación, casts
  calls.pengu             funciones, métodos, rituales, callbacks
  access.pengu            campos, flechas, at, slices, essence
  containers.pengu        list/map/array/struct init
  judge.pengu             judge/when/patrones
  interp.pengu            interpolación y escaping
  lambdas.pengu           funciones sin captura
  with_or.pengu           with/or/value-if
stmt/
  core.pengu              var/let/set/return/do
  control.pengu           if/unless/while/for/labels/gotos
  defer.pengu             defer/errdefer/banish
  judge.pengu             judge como statement
generics/
  specialize.pengu        worklist, sustitución, nombres
  resolve.pengu           llamadas genéricas y rituales
  instances.pengu         registro de instancias
dce/
  reach.pengu             reachability C
  prune.pengu             weaves/types/consts/native
bundle.pengu              secciones y feature gates
prototypes.pengu          forward prototypes
entry.pengu               main/pengu_main
tests.pengu               --test
```

No se permite un `utils.pengu` cajón de sastre. Cada archivo tiene una
responsabilidad y `insignia psc_codegen_<área>_`.

---

## 🔗 4. Contrato F3 → F4

### 4.1 Principio

**F4 no vuelve a inferir.** Consume las anotaciones de F3:

- `SemaAnnotations.type_of(node)` para el tipo de expresiones y locales.
- `SemaAnnotations.symbol_of(node)` para la resolución de nombres.
- Flags `ANN_*` para mutating, tuple, fn value, banish, judge, bindings.
- `SemaSymbol`/`SemaType` para firmas, campos, variantes, consts, atributos.

Si falta una anotación obligatoria, F4 emite un **error interno de codegen** y
falla. No se inventa un `any` ni se vuelve a llamar a `infer`.

### 4.2 Addendum A1 (mínimo, antes de F4a)

F3 verificó interpolaciones en un estado temporal y liberó su AST/anotaciones.
El codegen necesita el AST y los tipos de cada `{...}` para emitir C. Para no
re-inferir ni duplicar parser:

- añadir a `SemaModule` una tabla `interps` con:
  - nodo string/token,
  - índice de parte,
  - `PsAst` de la expresión,
  - `SemaAnnotations` de esa expresión,
  - span y `ok`;
- `check_string_literal` de F3 rellena esa tabla al comprobar;
- F4 la consume; no cambia ningún diagnóstico F3.

Si el usuario prefiere no tocar F3, la alternativa es que F4 parsee e infiera
cada interpolación con F2/F3, pero eso duplica trabajo y memoria; **no lo
recomiendo**.

### 4.3 Addendum A2 (sólo si hace falta)

F3 ya expone templates/instances, const_values, bounds y derived. Si el codegen
necesita un accessor adicional (por ejemplo, “dame todas las instancias de un
template”), se añade una función de sólo lectura en `sema/symbols/table.pengu`
o `sema/types/table.pengu`. Nunca se cambia la semántica de F3.

### 4.4 Reglas de inmutabilidad

- F4 no modifica `SemaType`, `SemaSymbol`, `SemaScope`, AST ni anotaciones.
- Los nombres C se guardan en `NameTable`, no en `SemaType.c_name`.
- Las especializaciones se guardan en `SpecializationTable`.
- El `c_name` de un símbolo F3 es una pista; F4 calcula el nombre final de
  forma determinista y lo cachea.

---

## 🧬 5. Tipos PenguScript → C

`ctype.pengu` es la única fuente de verdad. Ningún emisor escribe `int32_t`,
`PenguList` o `const` a mano.

### 5.1 Tabla base

| `SemaTypeKind` | C |
|---|---|
| `TkBase` int/i32/int32/int32_t | `int32_t` |
| i64/int64/long | `int64_t` |
| u32/uint32/uint | `uint32_t` |
| u64/uint64/ulong | `uint64_t` |
| i16/short | `int16_t` |
| u16/ushort | `uint16_t` |
| i8/int8 | `int8_t` |
| u8/byte | `uint8_t` |
| char | `char` |
| usize/size_t | `size_t` |
| isize/intptr_t | `intptr_t` |
| float/f32 | `float` |
| double/f64 | `double` |
| bool | `bool` |
| string | `PenguString` |
| void | `void` |
| opaque | `void*` |
| error | `const char*` |
| `TkRef` | `T*`, o `void*` para `ref to void` |
| `TkFrozen` | `const T` |
| `TkArray` | `T*` (y `T (*)[N]` como campo/parámetro) |
| `TkSlice`/`TkMany` | `PenguSlice` |
| `TkList` | `PenguList` |
| `TkMap` | `PenguMap` |
| `TkMaybe` | `PenguMaybe` |
| `TkResult` | `PenguResult` |
| `TkTuple` | rune sintético `PenguTuple_N` |
| `TkRange` | `PenguRange` |
| `TkFn` | declarador de función/`typedef` |
| `TkRune`/`TkEcho` | nombre C del nominal |
| `TkOmen` | enum entero o `PenguString` si es string-valued |
| `TkAlias`/`TkSeal` | nombre del typedef |
| `TkConcept` | `void*` en firmas C |
| `TkTypeParam` | **prohibido** fuera de un cuerpo genérico ya sustituido |
| `TkNull` | `void*` |
| `TkError` | `void*` (sólo recuperación interna) |

### 5.2 Detalles que no se pueden improvisar

- **`ref to frozen T`**: `const T*`; la cualificación va en el pointee, nunca en
  el puntero. `ref to frozen void` es `const void*`.
- **Arrays**: `T*` fuera de struct; en struct/parámetro por valor hay que
  conservar dimensiones con `to_c_decl` (`T (*)[N]`).
- **Function pointers**: `ref to weave …` es un puntero a función, no un
  puntero a puntero. Los parámetros de callback usan `to_c_decl`.
- **`opaque`**: `void*`; nunca se desreferencia sin `transmute`/cast.
- **Tuplas**: rune sintético con nombre estable por firma; el nombre incluye
  los tipos para no chocar (`PenguTuple_int_bool`).
- **Alias/seal**: `typedef`/struct con el nombre C resuelto; no expandir en
  cada uso.
- **Omens**: mismo backend que stage0 (enum entero o string), incluyendo
  payloads y `is_string_valued`.
- **Conceptos**: no generan C por sí mismos; los métodos se emiten en los
  tipos que los implementan.
- **`TypeParam`**: si aparece en una firma final es un bug de F3/F4. Se emite
  diagnóstico interno y se aborta el codegen; no se degrada a `_T`.

### 5.3 Layout de tipos

- Structs de runes/ecos con campos en orden de declaración.
- Omens con tag + payload según stage0.
- Alias/seal con `typedef`.
- Forward declarations para todos los tipos; orden topológico por dependencias
  **por valor**; las dependencias por puntero no exigen orden.
- `static_assert`/`_Static_assert` para ABI y tamaños cuando corresponda.
- Sin `#pragma pack` no justificado.
- `bool` requiere `<stdbool.h>`; el runtime ya lo incluye.

---

## 🏷️ 6. Nombres, mangling y layout

### 6.1 `NameTable`

Un solo lugar decide nombres C:

- símbolos de módulo con `insignia`;
- funciones, métodos, consts, tipos, variantes, campos;
- parámetros/locales (scope stack);
- temporales (`_tmp_N`, `_e_N`, etc.);
- labels C/gotos;
- lambdas y tests.

No se permite construir un nombre concatenando strings a mano en 20 módulos.

### 6.2 Esquema recomendado

- Público sin colisión: `insignia + nombre` (`sema_body_check_stmt`…).
- Sin `insignia`: nombre del símbolo en su módulo, con resolución de colisión
  global determinista.
- Métodos: `tipo_metodo` o `insignia_tipo_metodo`; receptores primitivos como
  stage0 (`int_clamp`).
- `@export("name")`: nombre C exacto; gana sobre el mangling.
- `@test`: `pengu_test_N` estable por orden de declaración.
- Genéricos: nombre base + firma canónica de argumentos
  (`atlas_map_get_or_int_string`); **nunca** `_T`.
- Constructores `ritual`: nombre del tipo + `_empty` + args de tipo; dos
  especializaciones no comparten nombre (fix B2).
- Tuplas: `PenguTuple_<canonical>`; typedefs si el nombre es largo.
- Names reservados de C (`int`, `for`, `main`, `_Static_assert`, …) se escapan
  con `_` o se detectan como error de binding.

### 6.3 Colisiones

- Colisión de dos símbolos del mismo nombre en el mismo namespace: F4 no debe
  emitir C ambiguo; se resuelve con insignia/módulo y, si no, error interno.
- `insignia` repetido en dos módulos: error de F3/F4 (no se inventa sufijo
  silencioso).
- Nombres de campo `self`/`_data`/`_len`: siguen las reglas de stage0.
- Mapas usados sólo para lookup; el orden de declaración es la fuente de
  nombres de locales/temporales.

### 6.4 Determinismo

- Orden de módulos: `SemaProgram.order` (topológico estable).
- Orden dentro del módulo: orden de declaración.
- Tipos: orden topológico; empates por `(module order, source offset)`.
- Nunca `for k in map`.
- Dos `emit-c` sobre el mismo programa deben producir exactamente el mismo
  string (excepto rutas absolutas si el usuario las pasa; el golden las
  normaliza).

---

## 🧩 7. Convenciones de bajada

### 7.1 Emisor

`emit.pengu` expone:

- `line`, `raw`, `indented`, `push_indent/pop_indent`;
- `c_string(s)` con escape de `"`/`\`/newline/bytes;
- `c_ident(s)`;
- `temp(prefix)` con contador del contexto;
- `section(title)`;
- `defer`/`banish` de strings temporales.

Reglas:

- Nada de `"{a}{b}"` en bucles grandes.
- Los strings temporales se bindean y se liberan.
- El C se escribe por líneas; no se guardan strings enormes intermedios.
- El resultado final se construye con un `StringBuilder` y se entrega una vez.

### 7.2 Expresiones vs statements

- Toda expresión tiene un tipo F3 anotado; el emisor puede pedir
  `type_of(node)` sin ambigüedad.
- Las expresiones que necesitan statements (`if` valor, `judge`, `do`, `with`,
  `or`) usan una de dos estrategias:
  1. **GNU statement expression** por defecto (como stage0);
  2. **hoisting** a un temporal + preludio antes del statement que la contiene
     con `--strict-c99`.
- El preludio se vacía en el statement que lo posee; no se permite un preludio
  huérfano ni una sentencia dentro de una macro.
- Las expresiones “view” (var, field, arrow, at, slice, essence) se reconocen
  sin generar temporales innecesarios.

### 7.3 Lvalues y side effects

- Una sola función `emit_lvalue(node)` para `set`, `set self`, `at`, campo,
  arrow, `essence`.
- No se evalúa dos veces una expresión con side effects; se hoistea.
- `set` compuesto (`set x += y`) respeta la evaluación única del target.
- `@mutates`:
  - en statement se baja a `mutating_fn(&target, ...)` o al `set` del target
    que stage0 genera;
  - en expresión F3 ya lo rechaza (`E0066`);
  - `get_*` se emite como función pura normal.

### 7.4 Ownership

- Los argumentos `string`/contenedores se prestan o se poseen según firma y
  flags; el codegen debe respetar la misma limpieza que stage0.
- `banish` genera la liberación del recurso y no deja el nombre usable.
- `defer`/`errdefer` se ejecutan LIFO en todas las salidas (return, break,
  continue, goto, error, `judge`).
- Los valores `some`/`ok`/`err` copian/poseen según el runtime; no se libera
  dos veces el payload.

### 7.5 Checks y `unsafe`

- Bounds y overflow activos por defecto; `unsafe:` o `--release-unsafe`
  desactivan **sólo** las comprobaciones, nunca la semántica.
- `at` y slices emiten `pengu_assert_bounds`/`pengu_bounds_panic` con la
  localización `.pengu`.
- Las operaciones de enteros con signo respetan overflow; las unsigned usan la
  semántica de C sin UB.
- `transmute`/`opaque` son explícitos; no se inventan casts implícitos.

### 7.6 Interpolación

- F4 consume el AST cacheado por F3 (A1).
- Los segmentos de texto se emiten como bytes C escapados (`\xNN` para bytes
  no ASCII), no como UTF-8 recodificado.
- `(chr N)` constante usa el byte correcto (fix B11: `\xC8`, no `\xC2\x88`).
- Las expresiones interpoladas se emiten con su tipo anotado; los strings
  temporales se liberan en el scope correcto.
- Los `{}` de strings raw no se interpretan.

### 7.7 Lambdas

- Sin captura: se emiten como funciones `static` top-level con nombre único.
- Los parámetros y el tipo de retorno salen de F3.
- `functor`/callbacks usan el mismo ABI que `to_c_decl`.
- Lambdas dentro de genéricos se especializan por la instancia; no comparten
  nombre con otra sustitución.

---

## 🧱 8. Subfases F4a–F4l

### F4a — Tipos, nombres, layout y esqueleto

**Objetivo:** un bundle mínimo con tipos vacíos compila.

Tareas:

- `CodegenOptions`/`CodegenContext`/`CodegenResult`.
- `NameTable`, `ctype`, `emit`, `origin`, `catalog` mínimos.
- `TypeId → C`, `to_c_decl`, const/restrict.
- Orden topológico de tipos y forward declarations.
- Prototipos de funciones (aún sin cuerpos).
- `#include "pengu_runtime.h"` y `_Static_assert` ABI.
- CLI mínimo `psc emit-c` (sólo bundle).
- Golden: bundle vacío/no-main.

**Salida:** `emit-c` de un programa vacío compila con gcc/clang.

### F4b — Declaraciones completas

Tareas:

- runes, echos, omens, aliases, seals.
- campos, variantes, payloads; `derive` y helpers iniciales.
- consts; `declare`; `antiquus`; `include`/`link`/`ldflags`.
- atributos (`@inline`, `@noreturn`, `@cold`, `@deprecated`, `@export`).
- `@mutates` como flag de método.
- forward declarations y dependencias por valor.
- feature gates de std.

**Salida:** declaraciones de `std`/bindings compilan; golden de 10 tipos.

### F4c — Firmas, prototipos y llamadas básicas

Tareas:

- `weave`/`declare`/métodos/rituales: firmas C.
- self por valor vs puntero; parámetros por valor/ref.
- llamadas directas, argumentos posicionales/nombrados, defaults.
- función como valor/callback básico.
- C names de métodos y tipos.
- errores de aridad ya resueltos por F3; F4 no duplica.

**Salida:** un programa `main` que llama a funciones y usa strings compila y
ejecuta.

### F4d — Expresiones completas

Tareas:

- literales exactos (int/float/char/string/raw/triple).
- operadores aritméticos/bits/lógicos/comparaciones y cortocircuito.
- casts `to`, `transmute`, `size of`, `type of`, `bytes of`, `ord/chr`.
- `at`, slices, list/map/array/struct init.
- `some`/`ok_of`/`err_of`, `null`, `none`, `donum`.
- accesos a campos, `->`, `essence`, `sigil`.
- string helpers/ownership de argumentos.
- `judge`/`when` como expresión y statement (con F4e para control).
- errores de C por expresiones deben ser 0.

**Salida:** corpus pequeño de expresiones con golden y ejecución.

### F4e — Statements, control y ownership

Tareas:

- `var`/`let`/`static`/`const`, destructuring de tuplas.
- `set`/`set` compuesto, lvalues.
- `if`/`unless`/`while`/`for in`/`for range`.
- labels/gotos/break/continue, `defer`/`errdefer`.
- `banish`, `unsafe`, `do` blocks, returns.
- scopes y liberación de temporales.
- strict C99 hoisting desde el inicio (no “después”).
- tests de fugas/ASan por scope.

**Salida:** programas con control y ownership idénticos a stage0.

### F4f — Genéricos y callbacks

Tareas:

- `SpecializationTable` y worklist.
- sustitución de type params en tipos/firmas/cuerpos.
- llamada genérica→genérica (fix B1).
- constructores `ritual` con múltiples especializaciones (fix B2).
- métodos de `enchanting shard T`, bounds y `where`.
- funciones como valores, callbacks, `functor`.
- límites de instanciación y errores claros.
- nombres C con args de tipo; sin `_T`.
- tests B1/B2 propios (no stage0).

**Salida:** genéricos de `std.atlas`/`std.loom` y casos complejos compilan/run.

### F4g — `with`, `or` y bloques-valor

Tareas:

- `with:` builders y `with init`.
- `or else`, `or return`, `or:`.
- `if`/`when` como valor; `do` como valor.
- temporales y preludios en expresiones anidadas.
- ownership de builders.

**Salida:** casos de `std.builder`, `or` y `with` ejecutan igual.

### F4h — Interpolación, lambdas, slices y datos

Tareas:

- cache A1 de F3; segmentos de texto/bytes.
- escaping C y `(chr N)` B11.
- lambdas sin captura, nombres y callbacks.
- `bytes of`, `frozen`, `slice of`, arrays multidimensionales.
- `map` de structs, `list of ref`, `opaque`.
- `@mutates` lowering en statements.

**Salida:** `std.cipher` JSON, `std.scrolls` y `std.functor` compilan/run.

### F4i — Entry, `--test` y ABI

Tareas:

- `main`/`pengu_main`, `pengu_init`, crash handler.
- `main` void/int; exit code.
- `--test`: sección, selector `--list/--only-index/--only`, JSON.
- entry as main (`main:` flag) sin contaminar otros módulos.
- bundle library (sin entry) y object/static/shared.
- `_Static_assert` ABI.
- tests de main, sin main, tests, library.

**Salida:** entry/test parity con stage0.

### F4j — DCE y poda

Tareas:

- reachability exacta sobre C emitido.
- raíces: user modules, `@export`, `main`, tests, C glue, natives.
- `--no-dce`, `--dce-scope=std|user`, `--tree-shake-user`.
- `--prune-types`, `--prune-native`.
- helpers derivados, lambdas, constantes, prototipos.
- determinismo y stats.
- tests de no eliminar reachable, callbacks, genéricos y C glue.

**Salida:** bundle size comparable, sin símbolos vivos eliminados.

### F4k — C99, compiladores y atributos

Tareas:

- gcc/clang/tcc/MSVC.
- `-std=c11 -Wall -Wextra -Werror`; MSVC `/W4 /WX`.
- `--strict-c99` (sin statement expressions/`__auto_type`).
- atributos/`restrict` por dialecto; MSVC `__declspec`.
- `static inline`, `noreturn`, `deprecated`, `cold`.
- Windows/macOS paths y flags.
- CI matrix.

**Salida:** misma semántica en todos los compiladores disponibles.

### F4l — Diagnósticos de C

Tareas:

- `OriginMap` y `#line` (por defecto; `--no-line-markers`).
- parser de stderr gcc/clang/tcc/MSVC.
- remapeo a `SourceFile`/span `.pengu`; severidad/mensaje/nota.
- tests con errores sintéticos y reales.
- no añadir códigos de lenguaje nuevos sin aprobación; se conserva el código
  del compilador C y se mapea el span.

**Salida:** un error de C apunta al `.pengu` correcto.

---

## 🧬 9. Genéricos y monomorfización

### 9.1 Modelo

- F3 ya tiene `SemaTemplate`/`SemaInstance` y bounds.
- F4 mantiene una `SpecializationTable`:

```text
key = (template symbol id, canonical type args, receiver type?)
value = C name, FnInfo sustituida, estado, body emitted?
```

- La instanciación es **bajo demanda** desde roots:
  - llamadas anotadas por F3,
  - métodos de `enchanting`,
  - constructores `ritual`,
  - valores de función,
  - tests.
- Worklist hasta punto fijo; recursión acotada.
- Cada especialización se emite una sola vez, antes de sus llamadores cuando
  sea posible; los prototipos rompen ciclos.

### 9.2 Sustitución

- `subst_map: TypeParam NameId -> TypeId`.
- Se aplica a:
  - tipos de parámetros/retorno,
  - tipos locales,
  - campos de structs genéricos,
  - nombres C,
  - lambdas y callbacks,
  - bounds (se validan antes de emitir).
- En un cuerpo genérico, toda referencia a `T` debe estar sustituida. Si queda
  un `TkTypeParam`, se emite error interno.

### 9.3 Bugs que PSC no hereda

| Bug | Comportamiento stage0 | F4/PSC |
|---|---|---|
| **B1** genérico→genérico | emite `_T` | se especializa el callee con los args del caller |
| **B2** `ritual` genérico | segunda instancia usa el nombre de la primera | el nombre incluye args de tipo |
| **B2b** tipo cualificado | C inválido / checker incoherente | `mod.Type.metodo` se resuelve como tipo F3 |
| **B11** `(chr 200)` en interpolación | UTF-8 `c2 88` (4 bytes) | byte `0xC8` (3 bytes) |
| **B9** orden de mapas | no determinista | `list` de orden + map de lookup |

Estos casos se prueban contra el resultado correcto, no contra stage0.

### 9.4 Límites

- Máximo de instanciaciones por template: configurable, por defecto 512.
- Profundidad de anidamiento: 256.
- Al superar: diagnóstico `E0049`/`E0005` de F3 o error de codegen con span; no
  se cuelga ni se emite C incompleto.
- No hay “monomorphization explosion” silenciosa: el benchmark mide el número
  de instancias.

---

## 🗑️ 10. DCE y poda

### 10.1 Política

- Por defecto, DCE elimina std/lib no alcanzable; los módulos del usuario se
  conservan (API pública).
- `--dce-scope=user`/`--tree-shake-user` también poda módulos del usuario.
- `--no-dce` no poda nada; se usa para A/B y bugs.
- `--prune-types` poda tipos/consts no nombrados por C vivo (opt-in).
- `--prune-native` poda includes/links/ldflags por origen (opt-in).
- `--test` y bibliotecas conservan lo necesario para sus cuerpos/API.

### 10.2 Reachability

- Raíces: `main`, `@export`, tests, todos los weaves de módulos no std,
  callbacks alcanzables, `include`/`link` usados por C glue.
- Se escanea el **C emitido**, no sólo el AST:
  - nombres de función/prototipo,
  - valores de función,
  - lambdas,
  - helpers derivados,
  - consts que generan símbolos.
- Punto fijo; sin falsos negativos; si hay duda, conservar.
- El catálogo completo se conserva para una segunda llamada a
  `generate_bundle` idempotente.

### 10.3 Determinismo

- DCE produce el mismo subconjunto/orden en cada ejecución.
- No se usan sets/maps para el orden de salida.
- `bundle.c` byte-idéntico entre dos ejecuciones.
- Stats deterministas (`before`, `after`, `dropped`, `names` ordenados).

### 10.4 Tests DCE

- función sólo alcanzable por callback;
- función sólo alcanzable por C glue con `--dce-scope=user`;
- genérico instanciado desde otro genérico;
- método `get_*` no usado;
- `--no-dce` superset;
- `--prune-types` no rompe C glue;
- `--prune-native` no elimina un include usado por C;
- `--test` conserva helpers de tests.

---

## 🚪 11. Entry point, `--test` y ABI

### 11.1 Entry normal

- `weave main` se emite como `pengu_main` (nombre C), nunca como `main`
  directamente.
- Wrapper `int main(int argc, char** argv)`:
  - `pengu_init(argc, argv)`;
  - `pengu_install_crash_handler()`;
  - llamada a `pengu_main`;
  - `fflush(stdout/stderr)`;
  - retorno int (0 si `main` es void).
- `entry_as_main`/`main` flag sólo para el módulo entry; no contaminar imports.

### 11.2 `--test`

- Cada `test "..."` es una función `static void pengu_test_N(void)`.
- Sección de tests con:
  - forward declarations,
  - registro de nombres/funciones,
  - `--list`, `--only-index N`, `--only NAME`,
  - JSON (`PENGU_TEST_JSON`) con `start/test_start/test_pass/end`.
- `--test` no aplica DCE de usuario que elimine cuerpos de tests.
- `pengu_run_tests` y `main` de test; exit code correcto.
- Tests con strings/UTF-8 se escapan en JSON.

### 11.3 ABI

- `PENGU_ABI_VERSION` 2; `_Static_assert` en C11.
- Firma de `pengu_init`, frames y helpers del runtime sin cambios.
- Tipos opacos/ref no se reinterpretan.
- `ref to void`/`opaque` conversiones C válidas.
- Un cambio de ABI requeriría F0/F5, no F4.

---

## 🧪 12. Diagnósticos de C y compiladores

### 12.1 `OriginMap`

- El codegen guarda por línea C: `(pengu file, pengu line, column)`.
- También emite `#line` cuando `line_markers` está activo.
- `#line` se suprime dentro de expresiones/macros que lo romperían.
- `--no-line-markers` deja el origin map para remapear en F5.

### 12.2 Parser de stderr

Soportar:

- GCC/Clang: `file:line:col: error: message`.
- TCC: `file:line: error: message`.
- MSVC: `file(line,col): error Cxxxx: message`.

Produce:

```pengu
rune CCompilerIssue:
    file as string
    line as int
    col as int
    severity as int
    message as string
    code as string
    origin as OriginEntry
```

- F4 no invoca el compilador; expone `parse_stderr`/`remap` para F5/tests.
- El span final es `.pengu`; si no hay mapping, se conserva el archivo C y se
  añade nota.
- No se inventan códigos E/W nuevos; se conserva `Cxxxx`/mensaje del compilador.

### 12.3 Matriz de compiladores

| Compilador | Flags base | Dialecto |
|---|---|---|
| GCC 12+ | `-std=c11 -Wall -Wextra -Werror` | GNU/statement exprs por defecto |
| Clang 15+ | idem | idem |
| TCC 0.9.27+ | `-std=c11 -Wall` | GNU; sin `__auto_type`/atributos no soportados |
| MSVC 19.x | `/std:c11 /W4 /WX` | `__declspec`, sin statement exprs |

- `--strict-c99` elimina GNU statement expressions y `__auto_type`.
- `--target-compiler` elige atributos/`restrict`.
- CI: Linux gcc+clang+tcc; Windows MSVC; macOS clang.
- WASM/emcc queda fuera del gate F4; F5/F10 lo añaden si se aprueba.

---

## 🧰 13. API y CLI mínima

### 13.1 API

`codegen/api.pengu`:

```pengu
rune CodegenOptions:
    base_dir as string
    entry_file as string
    is_test as bool
    is_library as bool
    dce as bool
    dce_scope_user as bool
    prune_types as bool
    prune_native as bool
    line_markers as bool
    strict_c99 as bool
    target_compiler as string
    release_unsafe as bool
    debug as bool

rune CodegenResult:
    ok as bool
    bundle as string
    origins as OriginMap
    diagnostics as ref to diag.DiagnosticBag
    stats as CodegenStats

weave generate with program as ref to sema.SemaProgram, opts as CodegenOptions into CodegenResult
weave free_result with r as ref to CodegenResult into void
```

- `generate` no libera `program`.
- `bundle` es owned; `free_result` lo libera.
- `ok=false` si hay errores de codegen; el bundle puede estar vacío.
- `CodegenStats`: tipos, prototipos, funciones, instancias, bytes, líneas,
  tiempo de cada fase, DCE.

### 13.2 CLI

Comando nuevo, sólo F4:

```text
psc emit-c FILE [--out=PATH | --stdout]
    [--test] [--library]
    [--no-dce] [--prune-types] [--dce-scope=std|user]
    [--prune-native] [--no-line-markers] [--strict-c99]
    [--target-compiler=gcc|clang|tcc|msvc]
    [--release-unsafe] [--debug]
    [--diagnostics=plain|json]
```

- Hace `check_file` de F3, luego `generate`.
- Escribe `bundle.c` y muestra stats.
- Exit 0 si `ok`, 1 con diagnósticos, 2 uso.
- No invoca gcc, no cachea binarios, no es `psc build`.
- `psc check` no cambia.

---

## ✅ 14. Paridad, oráculos y tests

### 14.1 Niveles

| Nivel | F4 |
|---|---|
| **A** | mismos accept/reject, exit, stdout/stderr; binario ejecuta |
| **B** | diagnósticos de C mapeados a `.pengu`; códigos de C preservados |
| **C** | `bundle.c` normalizado idéntico a stage0 en 20 golden |
| **D** | determinismo PSC (dos ejecuciones idénticas) |

No se exige C byte-idéntico a stage0 en todo el corpus: stage0 tiene orden de
mapas e interpolación distintos. Se exige **A+B en todo**, C en golden
representativos, D siempre.

### 14.2 Oráculo de ejecución

`psc/tools/codegen_diff.py`:

- Toma un `.pengu` ejecutable.
- Stage0: `pengu run/build --keep` en temp.
- PSC: `psc emit-c`, gcc/clang, ejecuta.
- Compara exit code, stdout, stderr relevante.
- Normaliza `#line`, rutas absolutas y mensajes de progreso.
- Reporta `pass/skip/diff`; no oculta fallos.
- Full corpus con `PSC_F4_FULL=1`.

### 14.3 Oráculo de C normalizado

`psc/tools/lark_codegen_oracle.py`:

- Genera C con stage0 y PSC para 20 casos pequeños.
- Normaliza:
  - `#line`,
  - rutas absolutas,
  - comentarios autogenerados,
  - espacios/tabs finales,
  - orden de bloques si stage0 usa map (sólo cuando está documentado).
- Compara exacto.
- Si difiere, explica el bloque/constructo, no lo marca como “allowed” sin
  revisión.

### 14.4 Suite PSC F4

`tests/psc/test_f4_acceptance.py`:

- `test_emit_c_smoke`: bundle no vacío, ABI/assert, sintaxis C.
- `test_compile_run_curated`: 20–30 programas, gcc/clang.
- `test_f4_compiler_matrix`: compiladores disponibles.
- `test_f4_determinism`: dos `emit-c` byte-idénticos.
- `test_f4_c_golden_20`: C normalizado.
- `test_f4_dce_flags`: `--no-dce`, `--prune-types`, `--dce-scope`, `--prune-native`.
- `test_f4_entry_and_test`: main/test/JSON.
- `test_f4_line_markers`: `#line` y `--no-line-markers`.
- `test_f4_c_diagnostics`: stderr sintético y error real remapeado.
- `test_f4_strict_c99`: sin statement expressions.
- `test_f4_generics_b1_b2`: regresiones.
- `test_f4_interpolation_b11`.
- `test_f4_full_corpus` (opt-in): 225 válidos + 1 negativo; compilar/run los
  ejecutables.
- `test_f4_asan`: binarios de conformidad con ASan/UBSan.
- `test_f4_benchmark`: tamaño/tiempo vs stage0.

### 14.5 Corpus

| Corpus | Uso F4 |
|---|---|
| 66 `tests/conformance/compliance` | compile/run, salida `OK` |
| 56 archivos `tests/compiler` (~832 tests) | casos de codegen/ejecución |
| `tests/stdlib` | std ejecutable |
| 225 válidos `std/tests/psc/src` | compilar bundle (no todos tienen main) |
| `coherence_conflict` | debe seguir rechazado por F3 |
| B1/B2/B2b/B11 | tests propios, no dependen del bug stage0 |

### 14.6 C golden

20 casos mínimos, uno por área:

1. hola mundo + return int
2. main void
3. rune con campos
4. omen + judge
5. `maybe`/`result`
6. list/map/array
7. strings/interpolación
8. genérico simple
9. genérico→genérico
10. método/enchanting
11. `with`/`or`
12. `defer`/`banish`
13. labels/loops
14. callbacks/fn value
15. `@mutates`
16. `antiquus`/include
17. `--test`
18. strict C99
19. DCE/no-DCE
20. line markers/`#line`

Cada golden se actualiza sólo con revisión manual y diff explicado.

### 14.7 ASan/UBSan

- Compilar y ejecutar 66 conformance con ASan/UBSan.
- Codegen PSC bajo ASan: `emit-c` sobre corpus curado sin fugas.
- `defer`/`banish`/strings/interpolación: casos específicos.
- Fugas del runtime compartido no se ocultan: se distingue runtime vs codegen.

### 14.8 Rendimiento

- `psc/tests/bench_codegen.pengu`: genera un programa sintético grande y mide
  tiempo de codegen, líneas y bytes.
- Comparar con stage0 `pengu build --keep` (sin gcc): codegen PSC ≤ 20% más
  lento en Release.
- Bundle size ≤ 20% mayor que stage0 en los casos representativos.
- Tiempo de compilación C ≤ 20% mayor.
- Sin explosión de especializaciones.

---

## 🗓️ 15. Checkpoints y calendario

| CP | Subfase | Entregable | Semanas |
|---|---|---|---:|
| CP0 | F4a + A1 | contrato, emit, ctype, API, `emit-c` vacío | 1.0 |
| CP1 | F4a/F4c | names/layout/prototipos, bundle vacío compila | 1.0 |
| CP2 | F4b | tipos/declaraciones/consts/extern/antiquus | 1.5 |
| CP3 | F4d | expresiones core, literales, operadores, llamadas | 2.0 |
| CP4 | F4e | statements, control, defer/banish, strict C99 | 1.5 |
| CP5 | F4g | with/or/value-if, métodos/rituales | 1.0 |
| CP6 | F4f | genéricos completos, callbacks, B1/B2 | 2.0 |
| CP7 | F4h | interpolación, lambdas, slices, datos | 1.5 |
| CP8 | F4i | entry/test/ABI | 0.5 |
| CP9 | F4l | line markers, origin map, C diagnostics | 0.5 |
| CP10 | F4j | DCE/poda exactos | 1.0 |
| CP11 | F4k | C99/MSVC/TCC/matriz | 1.0 |
| CP12 | cierre | corpus, ASan, benchmark, docs, paridad | 1.0 |
| **Total** | | | **15.0** |

Rango de plan: **12–16 persona-semanas**. Un solo desarrollador senior a
tiempo completo: ~15 semanas; un equipo de 2–3 puede solapar tests, golden y
matriz, pero no CP0–CP7 (dependencia fuerte).

No se empieza F5 hasta que CP12 esté aprobado.

---

## ⚡ 16. Rendimiento y determinismo

### 16.1 Presupuesto

- `emit-c` de 2 000 funciones (benchmark F3) < 300 ms en Release.
- Bundle de un programa mediano ≤ 20% más grande que stage0.
- Tiempo de gcc/clang ≤ 20% mayor.
- Número de especializaciones acotado y monitoreado.
- Sin O(n²) en strings/interpolación; usar `StringBuilder`.

### 16.2 Determinismo

- `SemaProgram.order` + offsets, no mapas.
- Nombres de temporales/lambdas contadores por recorrido determinista.
- DCE stats ordenados.
- Origin map ordenado.
- `bundle.c` idéntico entre dos ejecuciones en el mismo host.
- Tests con hash SHA-256 del bundle.

### 16.3 Perfilado

- Bench de codegen y de compilación C.
- Conteo de tipos/funciones/instancias/líneas.
- Comparación A/B con stage0 en `--no-dce` y DCE.
- No se acepta “optimizar” quitando checks/correctness.

---

## ⚠️ 17. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| F3 annotations incompletas | Media | Alto | addendum A1/A2; gate CP0 con corpus |
| genéricos anidados | Alta | Alto | CP6 temprano, B1/B2 tests, límites |
| DCE elimina reachable | Media | Alto | exact C scan, roots, tests callbacks/C glue |
| ownership de strings | Alta | Alto | tabla de ownership, ASan desde CP3 |
| C no compila en MSVC/TCC | Media | Medio | CP11, strict C99 desde CP3 |
| `#line` rompe macros | Media | Medio | supresión en expresión, tests |
| C diagnostics mal mapeados | Media | Medio | origin map, tests sintéticos/reales |
| bundle no determinista | Media | Alto | no mapas en emisión, hash test |
| rendimiento pobre | Media | Medio | benchmark, DCE, no O(n²) |
| scope creep a F5/F6 | Alta | Medio | `emit-c` sólo; build/run fuera |
| stage0 bug se toma como verdad | Media | Medio | B1/B2/B11 tests propios; divergencia documentada |
| código monolítico | Media | Medio | módulos ≤800 líneas, review por CP |

---

## ❓ 18. Decisiones que necesito de ti

Marca una opción por decisión; las recomendadas son las que usaré si apruebas
el plan tal cual.

### D1 — Genéricos

- ✅ **Recomendado: monomorfización completa en PSC** (B1/B2 corregidos). Es
  necesaria para codegen de usuario y evita la restricción “PSC sin genéricos
  compuestos”.
- ⚠️ Alternativa: limitar PSC a genéricos simples y factorías; más rápido al
  principio, deuda grande.

### D2 — CLI de F4

- ✅ **Recomendado: `psc emit-c` mínimo** (genera C; no compila, no cachea).
- ❌ Sin CLI: sólo API/tests; más incómodo para revisar.
- ❌ `psc build` completo: invade F5.

### D3 — Definición de paridad de C

- ✅ **Recomendado: A+B en todo el corpus, C normalizado en 20 golden, D
  determinismo PSC.** No se exige C byte-idéntico a stage0 en todo.
- ⚠️ Alternativa: intentar C byte-idéntico global; stage0 tiene orden de mapas
  e interpolación distintos y haría el gate frágil.

### D4 — Bundle

- ✅ **Recomendado: monolítico `bundle.c`** como stage0 (F4/F5).
- ⚠️ Alternativa: un `.c` por módulo; más trabajo de driver/cache, se puede
  posponer a F6.

### D5 — DCE

- ✅ **Recomendado: DCE exacto por defecto sobre std/lib; flags de stage0;
  `--prune-types`/`--prune-native` opt-in.**
- ⚠️ Alternativa: DCE opt-in; bundles más grandes y peor paridad.

### D6 — Dialecto C

- ✅ **Recomendado: gcc/clang/tcc GNU por defecto; `--strict-c99`; MSVC usa
  `__declspec`.** Mantiene paridad y portabilidad.
- ❌ C99 estricto siempre: rompe `#line`/expresiones de stage0 y más trabajo.

### D7 — Line markers

- ✅ **Recomendado: `#line` por defecto, `--no-line-markers` opcional**, más
  origin map siempre.
- ❌ Sin `#line`: peor diagnóstico y no paridad.

### D8 — Diagnósticos de C

- ✅ **Recomendado: preservar el código/mensaje del compilador C y mapear el
  span a `.pengu`; no añadir códigos E/W de lenguaje sin aprobación.**
- ⚠️ Alternativa: códigos PSC nuevos; requiere actualizar catálogo/paridad.

### D9 — Addendum F3 A1

- ✅ **Recomendado: permitir el cache de interpolaciones en F3** (sólo
  almacenamiento, sin cambiar diagnósticos) para que F4 no re-infiera.
- ❌ No tocar F3: F4 parsea/infiere otra vez; duplica trabajo y memoria.

### D10 — Plataformas del gate

- ✅ **Recomendado: Linux gcc/clang/tcc + Windows MSVC + macOS clang en CI;
  WASM/emcc fuera del gate F4.**
- ⚠️ Alternativa: sólo Linux; reduce cobertura y deja MSVC/TCC para F11.

### D11 — Corpus completo en CI

- ✅ **Recomendado: tests curados por defecto; corpus completo con
  `PSC_F4_FULL=1` en CI nocturno.** Igual que F3.
- ❌ Full en cada PR: lento.

### D12 — Bugs de stage0

- ✅ **Recomendado: PSC corrige B1/B2/B2b/B11 y los tests los tratan como
  regresiones de PSC, no como fallos de paridad con stage0.**
- ⚠️ Alternativa: replicar bugs; inaceptable para auto-hospedaje.

Si apruebas D1–D12 recomendadas, empiezo por CP0 (contrato + A1 + `ctype` +
`emit` + `psc emit-c` vacío) y no toco F5.

---

## 🗂️ 19. Mapa Python → PSC y ownership

### 19.1 Mapa

| Python | PSC F4 |
|---|---|
| `pengu_codegen/ctype.py` | `codegen/ctype.pengu` |
| `symbols.py` | `codegen/names.pengu` + `catalog.pengu` |
| `declarations.py` | `codegen/catalog.pengu`, `types/*`, `decls/*` |
| `types_gen.py` | `codegen/types/records.pengu`, `omens.pengu` |
| `derived_gen.py` | `codegen/types/derived.pengu` |
| `constants.py` | `codegen/types/aliases.pengu` |
| `prototypes.py` | `codegen/prototypes.pengu` |
| `exprs.py` | `codegen/expr/*` |
| `stmts.py` | `codegen/stmt/*` |
| `loops.py` | `codegen/stmt/control.pengu` |
| `or_block.py` | `codegen/expr/with_or.pengu` |
| `value_if.py` | `codegen/expr/with_or.pengu` |
| `interpolate.py` | `codegen/expr/interp.pengu` |
| `lambdas.py` | `codegen/expr/lambdas.pengu` |
| `slicing.py` | `codegen/expr/access.pengu` |
| `calls.py` | `codegen/expr/calls.pengu` |
| `bindings.py` | `codegen/decls/extern.pengu` |
| `runtime_helpers.py` | `codegen/runtime_helpers.pengu` |
| `line_markers.py` | `codegen/origin.pengu` |
| `tests_gen.py` | `codegen/tests.pengu` |
| `entry.py` | `codegen/entry.pengu` |
| `bundle.py` | `codegen/bundle.pengu` + `dce/*` |
| `pengu_dce.py` | `codegen/dce/reach.pengu`, `prune.pengu` |

### 19.2 Ownership

| Recurso | Dueño | Liberación |
|---|---|---|
| `CodegenContext` | `generate` | `free_context` |
| `bundle` string | `CodegenResult` | `free_result` |
| `NameTable`, `Catalog`, `SpecializationTable` | contexto | `free_context` |
| `OriginMap` | resultado/contexto | `free_result` |
| scopes de C | contexto | `pop_scope` |
| strings temporales | función | `defer banish` |
| `SemaProgram` | F3/llamador | no lo libera F4 |
| `DiagnosticBag` | F3/llamador | no lo libera F4 |

Regla: si F4 devuelve `string`/`list`/`map`, el llamador lo libera; si recibe
`ref to`, no lo libera. Cada función lleva `## ## Memoria`.

---

## 🏁 20. Criterios de aceptación

F4 se considera cerrada sólo si:

1. `psc emit-c` genera `bundle.c` para los **225 archivos válidos** del corpus
   F3 (los no ejecutables, al menos compilan como objeto/biblioteca).
2. Los **66 programas de conformidad** compilan, ejecutan y producen la misma
   salida/exit que stage0.
3. Los casos ejecutables de `tests/compiler` y `tests/stdlib` pasan con PSC.
4. `bundle.c` compila sin warnings con `-Wall -Wextra -Werror` en gcc y clang;
   TCC/MSVC en la matriz.
5. `--strict-c99` compila sin GNU statement expressions.
6. `--test`, `--no-dce`, DCE, `--prune-types`, `--dce-scope`,
   `--prune-native`, `--no-line-markers` y `--target-compiler` tienen tests.
7. Dos ejecuciones de `emit-c` producen exactamente el mismo bundle.
8. 20 C golden normalizados coinciden con stage0.
9. B1/B2/B2b/B11 tienen regresiones propias y PSC no hereda los bugs.
10. ASan/UBSan limpio en los 66 binarios y en el codegen sobre el corpus
    curado.
11. Tamaño/tiempo de bundle y C ≤ 20% peor que stage0 en los benchmarks.
12. `tests/psc/test_f4_acceptance.py` verde; full corpus con
    `PSC_F4_FULL=1`.
13. Documentación actualizada: `psc/docs/CODEGEN.md`, `C_TYPES.md`,
    `PARITY.md`, `OWNERSHIP.md`, `BENCHMARKS.md`, README de PSC.
14. Cero TODO/placeholder/`_T`/nombre C sin resolver en el C emitido.

---

## 📎 21. Anexos

### A. Comandos previstos

```bash
# C mínimo (F4)
psc emit-c psc/tests/fixtures/codegen_hello.pengu --out=/tmp/bundle.c
gcc -std=c11 -Wall -Wextra -Werror /tmp/bundle.c -o /tmp/hello
/tmp/hello

# Test mode
psc emit-c programa.pengu --test --out=/tmp/tests.c
gcc ... /tmp/tests.c -o /tmp/tests
/tmp/tests --list
/tmp/tests --only-index 0

# Estricto
psc emit-c programa.pengu --strict-c99 --target-compiler=msvc

# DCE
psc emit-c programa.pengu --no-dce
psc emit-c programa.pengu --prune-types --dce-scope=user

# Tests PSC
cd psc
../.venv/bin/python ../pengu_project.py build
../.venv/bin/python -m pytest -q ../tests/psc/test_f4_acceptance.py
PSC_F4_FULL=1 ../.venv/bin/python -m pytest -q ../tests/psc/test_f4_acceptance.py

# Oráculos
../.venv/bin/python ../psc/tools/lark_codegen_oracle.py --psc ./build/psc
../.venv/bin/python ../psc/tools/codegen_diff.py --psc ./build/psc --root ..
```

### B. Golden de C normalizado

Normalizador:

- elimina `#line`;
- normaliza rutas absolutas a `<path>`;
- elimina comentarios de cabecera autogenerados;
- conserva secciones/prototipos/definiciones;
- convierte tabs/espacios finales;
- hash SHA-256 al final.

Un golden se actualiza sólo con revisión manual y una explicación en el commit.

### C. Divergencias documentadas con stage0

- `std/compressus` (allowlist F2): AST distinto, C semánticamente igual.
- B1/B2/B2b/B11: PSC correcto; stage0 bug.
- `#line`/rutas: normalizados en el oráculo.
- Orden de mapas: PSC determinista; stage0 puede variar.
- `--prune-types`/`--prune-native`: opt-in, no comparados por defecto.

### D. Ficheros que F4 tocará

- `psc/src/psc/codegen/**` (nuevo).
- `psc/src/main.pengu` (nuevo `emit-c`).
- `psc/src/psc/sema/**` (sólo addendum A1/A2, sin cambiar semántica).
- `psc/tests/**` (nuevos).
- `tests/psc/test_f4_acceptance.py`, `psc/tools/lark_codegen_oracle.py`,
  `psc/tools/codegen_diff.py`.
- `psc/docs/CODEGEN.md`, `C_TYPES.md`, `PARITY.md`, `OWNERSHIP.md`,
  `BENCHMARKS.md`, `psc/README.md`.

No se toca `std/`, el runtime, F1/F2 ni el compilador Python.

---

## 🏁 22. Cierre

Este plan implementa **solo F4**. Si lo apruebas (o cambias alguna decisión en
§18):

1. congelaré el contrato F3→F4 y haré el addendum A1 (cache de interpolación);
2. construiré `ctype`, `names`, `emit`, `layout` y `psc emit-c` antes de tocar
   cuerpos;
3. avanzaré por checkpoints con C compilable en cada uno;
4. no empezaré F5 hasta que el corpus ejecutable y los golden estén verdes.

No he modificado código, `std/`, la auditoría, F1/F2/F3 ni el compilador
Python. `PLAN_F4_CODEGEN.md` es el único artefacto nuevo de esta conversación.
