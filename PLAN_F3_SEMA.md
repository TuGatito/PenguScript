# 🧠 Plan de implementación — F3: módulos, símbolos, tipos, checker e inferencia

> **Estado:** **aprobada; F3 implementada y verificada.** D1–D10 y D12 según lo
> recomendado. D11: `insignia sema_<área>_` con nombres legibles y tipos
> `Sema*`; los helpers duplicados entre módulos se renombraron para que el
> registro global de stage0 no los confunda.
>
> **Verificación:** `psc check` acepta 225 archivos válidos del corpus (`std`,
> `tests`, `psc/src`) y rechaza el fixture negativo `coherence_conflict`;
> `tests/psc/test_f3_acceptance.py` pasa 17 pruebas y el oráculo semántico de
> 193 casos deja 0 válidos rechazados, 0 negativos aceptados y 53/53 códigos
> exactos. La paridad
> semántica de códigos/posiciones se documenta en
> [`psc/docs/SEMA.md`](psc/docs/SEMA.md) y [`psc/docs/PARITY.md`](psc/docs/PARITY.md).
>
> **Base:** PenguScript `3.0.3` (`3f99038`), con F1 y F2 cerradas.
> **Fase:** F3 del [`AUDITORIA_AUTO_HOSPEDAJE.md`](AUDITORIA_AUTO_HOSPEDAJE.md)
> §9, el corazón semántico del compilador.
>
> **Regla de la fase:** cero deuda técnica. Cada decisión que F4 vaya a
> consumir se congela aquí; cada diferencia con stage0 se mide con un oráculo,
> no se “arregla a ojo”.

---

## 📑 Índice

0. [Resumen ejecutivo](#-0-resumen-ejecutivo)
1. [Punto de partida verificado](#-1-punto-de-partida-verificado)
2. [Alcance](#-2-alcance)
3. [Decisiones de diseño](#-3-decisiones-de-diseño)
4. [Arquitectura y pipeline](#-4-arquitectura-y-pipeline)
5. [Modelo de tipos](#-5-modelo-de-tipos)
6. [Símbolos, scopes y módulos](#-6-símbolos-scopes-y-módulos)
7. [Checker de declaraciones y statements](#-7-checker-de-declaraciones-y-statements)
8. [Inferencia de expresiones](#-8-inferencia-de-expresiones)
9. [Genéricos, bounds e instanciación](#-9-genéricos-bounds-e-instanciación)
10. [Conceptos, `bind`, `enchanting` y `@mutates`](#-10-conceptos-bind-enchanting-y-mutates)
11. [Compilación condicional y constantes](#-11-compilación-condicional-y-constantes)
12. [Diagnósticos, warnings y recuperación](#-12-diagnósticos-warnings-y-recuperación)
13. [Contrato con F4: anotaciones semánticas](#-13-contrato-con-f4-anotaciones-semánticas)
14. [Módulos, archivos y DAG](#-14-módulos-archivos-y-dag)
15. [CLI y API pública](#-15-cli-y-api-pública)
16. [Orden de implementación y checkpoints](#-16-orden-de-implementación-y-checkpoints)
17. [Tests, oráculos y paridad](#-17-tests-oráculos-y-paridad)
18. [Rendimiento y determinismo](#-18-rendimiento-y-determinismo)
19. [Criterios de aceptación (DoD)](#-19-criterios-de-aceptación-dod)
20. [Riesgos y mitigaciones](#-20-riesgos-y-mitigaciones)
21. [Decisiones que necesito de ti](#-21-decisiones-que-necesito-de-ti)
22. [Anexos](#-22-anexos)
23. [Cierre](#-23-cierre)

---

## 🎯 0. Resumen ejecutivo

F3 convierte el AST exacto de F2 en un **modelo semántico completo**:

- resuelve imports y módulos;
- construye símbolos, scopes y tablas de tipos;
- valida declaraciones, statements, ownership y control de flujo;
- infiere el tipo de cada expresión;
- instancia y valida genéricos, bounds y conceptos;
- evalúa `when`/`defined` y pliega constantes;
- emite los mismos códigos `E`/`W` que stage0, con spans de byte;
- deja a F4 un contrato estable de tipos, símbolos e instancias.

No es un port línea a línea de `PenguChecker` (8 433 líneas) ni de
`TypeInferrer` (5 357). Es un port **semánticamente fiel**, dividido por
responsabilidad, con tablas planas, interning de tipos y hooks para romper la
recursión checker ↔ inferencia.

El oráculo principal será stage0:

- aceptar/rechazar cada archivo del corpus;
- mismo código, línea y columna del primer error (objetivo 100 %, mínimo 95 %);
- mismas firmas de tipos y símbolos en el dump semántico;
- mismos warnings relevantes;
- cero crashes, ASan limpio, determinismo.

**Esfuerzo estimado:** 14–18 semanas de una persona (la auditoría dice 10–14;
la diferencia es la paridad fina, recuperación y oráculos). Es la fase más
grande del proyecto y el mayor riesgo para F4/F5.

---

## 🔍 1. Punto de partida verificado

### 1.1 F2 cerrada

Estado medido al cerrar F2:

| Gate | Resultado |
|---|---|
| `pytest tests/psc` con `PSC_PARITY=1` | **12 passed** |
| Oracle de tokens F1 | `files=175 failures=0` |
| Corpus F2 | **205 archivos, bad=0** |
| Oracle AST F2 | `exact=204 allowed=1 diverged=0` |
| Oracle de errores F2 | 15 casos, 14 exactos + 1 allowlist |
| ASan/UBSan | 205 archivos limpios |
| Fuzz parser | 1 000 000 entradas sin crashes |
| Benchmark parser Release | **13,28 MB/s**, 680 002 nodos, 181 ms |

F2 deja:

- `PsAst`/`PsNode` con IDs estables, dump canónico y spans de byte.
- `LexResult` con tokens, strings, chars, `antiquus` y comentarios.
- `SourceFile` con índice de líneas.
- `DiagnosticBag` de `std.diagnostic`, con `Span.file` y multi-fuente.
- `psc parse`/`psc ast` y API `parse_interpolation_expr`.
- El parser es el contrato de entrada de F3; **no se re-parsea** para
  semántica salvo las expresiones de interpolación, que F3 pedirá a F2.

### 1.2 Stage0: el oráculo semántico

| Archivo | Líneas | Papel |
|---|---:|---|
| `pengu_parser/pengu_types.py` | 3 116 | 23 variantes de tipo, compatibilidad, casts, canonicalización, layout, conceptos |
| `pengu_parser/pengu_symbols.py` | 1 095 | `Symbol`, `Scope`, `SymbolTable`, resolución de imports |
| `pengu_parser/pengu_checker.py` | 8 433 | recolección top-level, scopes, checker, atributos, control, concepts |
| `pengu_parser/pengu_infer.py` | 5 357 | inferencia de expresiones, llamadas, métodos, genéricos, interpolación |
| `pengu_parser/pengu_comptime.py` | 423 | `CompileTimeEnv`, `when`, `defined`, constantes |
| **Total** | **18 424** | |

Además:

- **67 códigos `E`** en el catálogo (`docs/error_catalog.json`), de los que
  F3 implementa los semánticos `E0001–E0070` (los `E0061/E0062` de lockfile
  son de F6/F9).
- **9 códigos `W`**, de los que F3 emite `W0001`, `W0002`, `W0004`, `W0005`,
  `W0006`, `W0007` y `W0013` (`W0000` es fallback y `W0003` está reservado).
- **169 llamadas a `parse_and_check`** y **133 aserciones de error** en
  `tests/compiler/` (60 archivos). Es el mejor corpus negativo disponible.
- Stage0 acepta y compila los 205 archivos de F2.
- El checker de stage0 **lanza** el primer error pero acumula `all_errors` y
  warnings; no es recuperable para LSP. F3 debe acumular y recuperar.

### 1.3 Hechos medidos que condicionan F3

- Stage0 tarda ~10,7 s en parsear+y comprobar 10 archivos representativos
  (~718 KB). No es una referencia de velocidad aceptable.
- Los tipos de stage0 son objetos Python mutables con `__eq__`/`__hash__`
  estructural y nombres mangled; el checker muta el AST con atributos
  `_pengu_value_type`, `_pengu_symbol`, `_pengu_resolved_c_name`, etc. Eso no
  se puede copiar tal cual: F3 usará tablas laterales por `node_id`.
- Las reglas de compatibilidad y casting **no son simétricas** y dependen de
  `frozen`, `ref`, `alias`, `seal`, conceptos y tipo base. Hay que portarlas
  exactamente, no “reinterpretarlas”.
- Los nombres de función son globales por símbolo en PenguScript (F1 ya sufrió
  colisiones con `std.lingua`). F3 usa `insignia sema_<área>_` por módulo:
  los nombres de función quedan legibles y los símbolos C no colisionan; las
  llamadas entre módulos son cualificadas. Los tipos de dominio sí llevan
  prefijo `Sema` porque dos runas con el mismo nombre lógico no pueden
  convivir. Se hará una auditoría de colisiones antes de cerrar.
- Los errores de stage0 llevan línea/columna de **codepoint** de Lark; PSC usa
  bytes. El oráculo convertirá como en F1/F2.

### 1.4 Lo que F3 no puede dejar a medias

1. Resolver módulos y exports, incluidos ciclos, privacidad y `insignia`.
2. Recolectar todas las firmas y detectar duplicados/colisiones.
3. Implementar el modelo de tipos completo y sus reglas de compatibilidad.
4. Inferir todas las expresiones y llamadas.
5. Validar genéricos, bounds, concepts, `bind`, `enchanting` y `@mutates`.
6. Evaluar `when`/`defined` y plegar constantes.
7. Emitir diagnósticos con código/posición y recuperar para LSP.
8. Producir las anotaciones que F4 necesita, sin generarlas de nuevo.

---

## 📦 2. Alcance

### 2.1 Entra en F3

- `SemaProgram`, `SemaOptions`, `SemaSession`/estado y resultado.
- Resolución y carga de módulos:
  - `std/`, directorio del importador, `src_dir`, `lib_dir`, raíz;
  - `__init__.pengu`, `.d.pengu`;
  - DFS topológico determinista, ciclos, imports duplicados, módulo no hallado;
  - exports, privacidad, alias de módulo, re-export de tipos, genéricos
    transitivos, `insignia`.
- Tabla de nombres internados (`NamePool`).
- Tabla de tipos plana (`SemaTypeTable`) con interning estructural.
- Modelo de tipos:
  - primitivos, `ref`, `frozen`, `array`, `slice`, `many`, `list`, `map`,
    `maybe`, `result`, `range`, tuplas, `fn`, runas, echos, omens, alias,
    seals, conceptos, type params, `any`, `null`, `void`, `opaque`, `error`.
- Canonicalización, mangling, layout/`size of`, conceptos, `Donum`.
- Símbolos, scopes, builtins, `SymbolTable`, métodos, registros de genéricos,
  consts, imports, includes/links/ldflags.
- Checker de declaraciones y statements.
- Inferencia de expresiones.
- Genéricos: sustitución, bounds, instanciación, valores de función genéricos.
- `concept`/`bind`/`enchanting`, coherencia, métodos primitivos, `self` valor vs
  referencia, `ritual`, `@mutates`.
- `when`/`defined`/`-D`, `os`/`arch`/`compiler`/`main`/`debug`/`wasm`, constante
  folding.
- Catálogo de errores semánticos `E0001–E0070` aplicable y warnings.
- Recuperación de errores y símbolos parciales para LSP.
- Side tables de anotaciones para F4.
- CLI `psc check`.
- Tests, oráculos, fuzz, ASan, benchmark, documentación.

### 2.2 No entra en F3 (explícito)

- Generación de C, DCE, caché de bundle, toolchain (**F4/F6**).
- Formatter, doc generator, LSP completo (**F7/F8**); solo se deja el modelo
  de símbolos y diagnósticos que el LSP consumirá.
- Resolver `pengu.toml` completo, lockfile y versiones (**F6/F9**).
- Cache incremental en disco (**F5/F6**); F3 mantiene solo el parseo/cache en
  memoria de la ejecución.
- Cambiar el lenguaje, el runtime o el ABI.
- Nuevos códigos de error fuera del catálogo.
- Port literal de mensajes de stage0 si un mensaje es un bug evidente; se
  documenta y se mantiene el código/posición.

---

## 🧭 3. Decisiones de diseño

### D1 — Representación de tipos: tabla plana con `TypeId` (recomendado)

- [x] **Recomendado:** `SemaTypeTable` con `types as list of SemaType` y
  `TypeId = int`. Los tipos compuestos guardan IDs de hijos; los metadatos de
  runas/funciones viven en tablas laterales con `first/count`.
  - Interning estructural por clave canónica (mapa `string -> TypeId`).
  - Igualdad de tipos = igualdad de `TypeId`; compatibilidad semántica se
    calcula aparte.
  - `SemaType` es un `rune` POD de siete campos (un `kind` y seis enteros):
    `kind`, `name`, `a`, `b`, `c`, `first`, `count`.
  - `TkFn` apunta a `fn_infos`; `TkRune`/`TkEcho`/`TkOmen`/`TkAlias`/
    `TkSeal`/`TkConcept` apuntan a `nominal_infos`; `TkTypeParam` a
    `tparam_infos`.
  - Los hijos variables (tuplas, type args) viven en `type_children` con
    `first/count`.
- [ ] Alternativa: `omen Type` recursivo con `ref to Type` en arena.
  - Es atractivo, pero los payloads de un `omen` se construyen completos y no
    se mutan por campo en PenguScript; los tipos nominales necesitan rellenar
    campos y métodos después de crear el tipo (recursión `rune Node`), así que
    habría que separar metadatos mutables en otra estructura. Además, la
    interning y el `banish` recursivo se complican.
- [ ] Alternativa: `Type` como 23 `rune`s con herencia simulada por `judge`.
  - Más verboso aún y obliga a un `void*`/tag para referencias heterogéneas.

**Por qué:** IDs + tablas laterales dan determinismo, interning barato,
igualdad O(1), `banish` de listas planas y un dump de tipos trivial. Es el
mismo patrón que funcionó en F2 y lo que el audit recomienda para objetos de
dominio que no son AST.

### D2 — Símbolos y scopes: runas POD + mapas por scope (recomendado)

- [x] **Recomendado:** `SemaSymbol` POD en `symbols as list of SemaSymbol`;
  `SemaScope` en `scopes as list of SemaScope`; cada scope tiene
  `bindings as map of string to int` (nombre → SymbolId).
  - IDs estables en orden de definición.
  - El scope actual es un índice; los scopes tienen `start_line`/`end_line`
    para `lookup_at` (LSP).
  - Los registros globales (runas, funciones, métodos, consts, imports,
    genéricos) son mapas `string -> int` en `SemaSymbols`.
  - Las claves compuestas `(receptor, método)` se codifican como una cadena
    estable `receptor + "\x1f" + método`, porque `map` de tuplas no es portable
    ni determinista en la implementación actual.
- [ ] Alternativa: scopes con listas y búsqueda lineal. Simple, pero O(n) en
  cada lookup y malo para LSP.
- [ ] Alternativa: mapas anidados. Funciona, pero duplica claves y complica el
  ownership.

### D3 — Checker e inferencia: módulos separados con hooks (recomendado)

- [x] **Recomendado:** `sema/check/*` e `sema/infer/*` son módulos separados.
  `SemaHooks` guarda punteros a función para las llamadas cruzadas:
  - `infer_expr(node, expected)`;
  - `check_stmt(node)`;
  - `check_block_value(node, expected)`;
  - `check_lambda(node)`;
  - `resolve_type(ast_node)`;
  - `check_judge`, `check_with_builder` si la frontera lo pide.
- [ ] Alternativa: un `sema/body.pengu` monolítico de 3 000 líneas. Viola la
  división por responsabilidad que pediste en F2 y hace F3 imposible de revisar.
- [ ] Alternativa: pasar callbacks como parámetro a todas las funciones. Más
  ruido que los hooks.

### D4 — Genéricos: instanciar y validar en F3, emitir en F4 (recomendado)

- [x] **Recomendado:** F3 sustituye, valida bounds, crea `SemaInstance` para
  cada combinación concreta usada y deja los metadatos en una tabla. F4 solo
  emite esas instancias (y las que F4 descubra al recorrer cuerpos ya
  instanciados).
  - El checker necesita instanciar para inferir llamadas y validar `E0032`.
  - F4 no debe repetir la resolución.
  - Las instancias se cachean por clave estable (template + type args +
    receiver) y se ordenan por primera aparición.
- [ ] Alternativa: dejar toda la monomorfización a F4. Duplicaría la lógica y
  haría que F3 no pudiera validar bounds anidados ni valores de función
  genéricos.

### D5 — Recuperación: acumular y seguir (recomendado)

- [x] **Recomendado:** el checker no lanza por entrada de usuario.
  - `SemaState.errors`, `max_errors`, `stop_after_first`.
  - `TkError`/`SymbolError` para envenenar sin cascadas.
  - Al fallar una declaración, se registra un símbolo parcial con `TkError` y
    se continúa con la siguiente.
  - Las expresiones inválidas devuelven `TkError`; compatibilidad con
    `TkError` es permisiva para no generar 20 errores por uno.
  - El LSP obtiene scopes y símbolos válidos aunque el archivo tenga errores.
- [ ] Alternativa: abortar en el primer error como stage0. Incompatible con el
  objetivo de LSP y con la calidad de diagnósticos.

### D6 — Paridad de diagnósticos

- [x] **Recomendado:** códigos y posiciones exactos; mensajes/help/note
  portados de stage0 cuando sea posible.
  - El oráculo compara aceptación/rechazo, código, línea y columna del primer
    error; después compara el conjunto completo de errores cuando stage0 los
    acumula.
  - Una allowlist documenta divergencias inevitables (bugs de stage0,
    posiciones de un token sintético, etc.).
  - `SEMA_ERRORS.md` es la tabla viva de códigos, condiciones y mensajes.
- [ ] Alternativa: mensajes “mejores” sin mirar a stage0. Rompe la paridad B y
  dificulta el switchover.

### D7 — Alcance del CLI en F3

- [x] **Recomendado:** `psc check <archivo>` comprueba el archivo y todos sus
  imports transitivos, con `--base-dir`, `--src-dir`, `--lib-dir`,
  `--std-dir`, `-D`, `--os`, `--arch`, `--compiler`, `--target`, `--debug`,
  `--deny-deprecated`, `--diagnostics`, `--max-errors`, `--stop-after-first`,
  `--dump-sema`.
  - No requiere toolchain C.
  - No necesita el manifiesto completo: los defaults de proyecto son
    `base_dir = dirname(archivo)`, `src_dir = "src"`, `lib_dir = "lib"`.
  - F6 añadirá el driver de proyecto completo y la caché.
- [ ] Alternativa: esperar a F6 para tener `check`. No: F3 necesita medir
  semántica ya.

### D8 — Sin caché en disco en F3

- [x] **Recomendado:** cache en memoria por ejecución (módulo → AST/parse) y
  cache de tipos/instancias. La caché en disco y el `impl_id` son F5/F6.
- [ ] Alternativa: implementar caché ahora. Añade invalidación y riesgos antes
  de tener paridad semántica.

### D9 — API para LSP

- [x] **Recomendado:** `SemaProgram` expone módulos, scopes, símbolos,
  diagnósticos y anotaciones. El LSP podrá usarlo sin CLI. La API no se
  esconde detrás de `psc`.
- [ ] Alternativa: dejar solo el CLI. F8 tendría que duplicar el pipeline.

### D10 — Dump semántico para el oráculo

- [x] **Recomendado:** `psc check --dump-sema` emite un formato canónico:
  módulos, símbolos top-level con tipo canónico, tipos declarados, métodos,
  consts y anotaciones de expresión. Es el equivalente semántico del AST dump.
  - Sin posiciones absolutas de CRLF; usa línea/columna de byte.
  - Orden de fuente, sin mapas no deterministas.
  - Se compara con un oráculo Python que instrumenta `TypeInferrer`.
- [ ] Alternativa: comparar solo aceptación/rechazo. No detectaría una
  inferencia incorrecta que aún compila; F4 heredaría el error.

### D11 — Nombres y colisiones

- [x] **Elegido:** `insignia sema_<área>_` en cada módulo, funciones con
  nombres legibles (`intern`, `lookup`, `check_expr`, ...) y llamadas
  cualificadas entre módulos (`calling st.intern`). Los tipos de dominio usan
  prefijo `Sema` (`SemaType`, `SemaSymbol`, `SemaScope`, ...).
  - Comprobado con un proyecto de prueba: dos módulos con el mismo `helper`,
    el mismo `advance` de `std.json` y el mismo genérico `identity` compilan y
    ejecutan correctamente.
  - Se mantiene una auditoría automática de nombres y se renombra cualquier
    colisión real que aparezca.
- [ ] Alternativa: prefijar todos los helpers (`sema_type_intern`, ...). Se
  conserva como fallback si `insignia` falla en algún caso; no se elige porque
  empeora la legibilidad sin necesidad.

---

## 🏗️ 4. Arquitectura y pipeline

### 4.1 Pipeline

```text
SemaOptions
    │
    ▼
ModuleResolver ──▶ ModuleLoader ──▶ SemaModule* (SourceFile, LexResult, PsParseResult)
    │                                  │
    │                                  ▼
    │                            SymbolCollector (pass 1)
    │                                  │
    ▼                                  ▼
TypeTable + SymbolTable ◀──── DeclaredTypeValidator
    │                                  │
    ▼                                  ▼
Checker (pass 2) ◀── hooks ──▶ Inferrer
    │                                  │
    ▼                                  ▼
SemaAnnotations + GenericInstances + Comptime
    │
    ▼
SemaResult (ok, diagnostics, program, annotations)
```

### 4.2 Pasadas

1. **Resolve**: encontrar y ordenar módulos; detectar ciclos/duplicados.
2. **Load**: leer, lexar y parsear cada módulo con F1/F2; registrar
   `SourceFile`/`LexResult`/`PsParseResult`; añadir fuentes al `DiagnosticBag`.
3. **Collect**: registrar imports, `insignia`, includes/links/ldflags,
   builtins, tipos y firmas top-level; crear símbolos.
4. **Validate types**: convertir AST de tipos a `TypeId`, validar genéricos,
   bounds, tamaños, recursión, campos, variantes, alias/seal.
5. **Check**: cuerpos y statements; scopes, ownership, control, concepts.
6. **Infer**: tipos de expresiones y llamadas (on demand desde Check).
7. **Instantiate**: materializar genéricos usados y validar bounds.
8. **Comptime**: `when` y constantes que afectan a la recolección/check.
9. **Finalize**: warnings, duplicados globales, nombres C, side tables.

### 4.3 Hooks checker ↔ inferencia

```pengu
rune SemaHooks:
    infer_expr as ref to weave with s as ref to SemaState, node as int, expected as int into int
    check_stmt as ref to weave with s as ref to SemaState, node as int into void
    check_block_value as ref to weave with s as ref to SemaState, node as int, expected as int into int
    check_lambda as ref to weave with s as ref to SemaState, node as int into int
    resolve_type as ref to weave with s as ref to SemaState, node as int into int
```

- `SemaState` contiene `hooks`; `sema/api.pengu` los instala antes de
  comprobar.
- Los stubs emiten un diagnóstico interno controlado, nunca `panic`.
- Evita imports cíclicos y permite módulos de ~400–800 líneas.

### 4.4 Ownership

| Recurso | Dueño | Liberación |
|---|---|---|
| `SemaModule` (SourceFile/LexResult/PsParseResult) | `SemaProgram` | `sema_free_program` |
| `SemaTypeTable` (types, children, side tables, intern map) | `SemaProgram` | `sema_free_program` |
| `NamePool` | `SemaProgram` | `sema_free_program` |
| `SemaSymbols` (scopes, mapas, registros) | `SemaProgram` | `sema_free_program` |
| `SemaAnnotations` | `SemaProgram` | `sema_free_program` |
| `SemaInstances` | `SemaProgram` | `sema_free_program` |
| `DiagnosticBag` | `SemaProgram` | `sema_free_program` |
| `SemaOptions` strings | `SemaProgram` | `sema_free_program` |
| Diagnósticos temporales | llamador | `banish` tras emitir |
| `SemaModule` parse fallido | `SemaProgram` | igual |

- El programa se transfiere a `SemaResult`; `sema_free_result` libera todo.
- F4 recibe `ref to SemaProgram`, no lo libera.
- Ningún `TypeId`/`SymbolId` es válido después de liberar el programa.
- No se libera un tipo o símbolo individualmente.

---

## 🧬 5. Modelo de tipos

### 5.1 `TypeId` y `SemaType`

```pengu
omen SemaTypeKind:
    TkAny
    TkNull
    TkVoid
    TkOpaque
    TkError
    TkBase
    TkRef
    TkFrozen
    TkArray
    TkSlice
    TkMany
    TkList
    TkMap
    TkMaybe
    TkResult
    TkTuple
    TkRange
    TkCVarArgs
    TkFn
    TkRune
    TkEcho
    TkOmen
    TkAlias
    TkSeal
    TkConcept
    TkTypeParam

rune SemaType:
    kind as SemaTypeKind
    name as int       # NameId: base/nominal/param, 0 si no aplica
    a as int          # target/elem/key/ok/info/first-child
    b as int          # value/err/size/-1
    c as int          # flags o segundo payload
    first as int      # type_children
    count as int
```

- `TypeId = int`; `0` se reserva para `TkError`/inválido (los builtins
  empiezan en 1).
- Los tipos son inmutables una vez creados. Las runas/echo/omen y funciones
  usan tablas laterales mutables durante la recolección.
- Uso de los campos:
  - `TkBase`: `name`; `TkVoid`/`TkOpaque`/`TkAny`/`TkNull`/`TkError`/`TkCVarArgs`
    son singletons sin payload.
  - `TkRef`/`TkFrozen`/`TkSlice`/`TkMany`/`TkList`/`TkMaybe`/`TkRange`: `a` es
    el tipo interno.
  - `TkArray`: `a` = elemento, `b` = tamaño (`-1` desconocido).
  - `TkMap`: `a` = clave, `b` = valor; `TkResult`: `a` = ok, `b` = err.
  - `TkTuple` y los type args de un tipo nominal: `first/count` sobre
    `type_children`.
  - `TkFn`: `a` = índice en `fn_infos`; `TkRune`/`TkEcho`/`TkOmen`/`TkAlias`/
    `TkSeal`/`TkConcept`: `a` = índice en `nominal_infos`; `TkTypeParam`: `a` =
    índice en `tparams`.
  - `b`/`c` quedan para tamaño, flags o payload específico de la variante; cada
    constructor documenta su uso.
- `SemaTypeTable`:

```pengu
rune SemaTypeTable:
    types as list of SemaType
    type_children as list of int
    nominal_infos as list of SemaNominalInfo
    fn_infos as list of SemaFnInfo
    fields as list of SemaField
    variants as list of SemaVariant
    tparams as list of SemaTypeParamInfo
    bounds as list of int          # NameId de conceptos
    derived as list of int         # NameId de conceptos
    concept_methods as list of SemaConceptMethod
    fn_params as list of SemaFnParam
    intern as map of string to int
    canonical_cache as list of int # TypeId -> NameId
    mangled_cache as list of int
```

### 5.2 Side tables

| Tabla | Campos |
|---|---|
| `SemaNominalInfo` | `kind`, `base_name`, `c_name`, `module`, `flags`, `fields_first/count`, `variants_first/count`, `tparams_first/count`, `derived_first/count`, `attrs_node` |
| `SemaField` | `name`, `type`, `flags`, `attrs_node` |
| `SemaVariant` | `name`, `value_i`, `value_s`, `payload_first/count`, `flags` |
| `SemaTypeParamInfo` | `name`, `bounds_first/count`, `flags` |
| `SemaFnInfo` | `params_first/count`, `return_type`, `tparams_first/count`, `flags`, `attrs_node` |
| `SemaFnParam` | `name` (`-1` si no), `type`, `flags`, `default_node` |
| `SemaConceptMethod` | `name`, `fn_type`, `flags` |

- `attrs_node` y `default_node` son IDs de AST de F2; el AST vive en el
  módulo y sigue siendo válido.
- `flags` son bits documentados (`cyclus`, `algebraic`, `string_valued`,
  `public`, `auto_donum`, `self_is_value`, `ritual`, `mutates`, etc.).

### 5.3 Interning y nombres

- `NamePool`: `strings as list of string`, `ids as map of string to int`.
  Todos los nombres, docs y textos de `type of` se internan una vez.
- Clave estructural por variante:
  - `base:<canonical>`.
  - `ref:<id>`, `frozen:<id>`, `array:<id>:<size>`, `slice:<id>`,
    `many:<id>`, `list:<id>`, `map:<key>:<value>`, `maybe:<id>`,
    `result:<ok>:<err>`, `tuple:<ids>`, `range:<id>`.
  - `fn:<flags>:<params>:<ret>:<tparams>`.
  - `named:<module>:<c_name>:<args>`.
  - `tp:<name>:<bounds>`.
- `sema_type_intern` construye la clave con `StringBuilder`, la busca y solo
  crea un `SemaType` si no existe.
- `canonical_type_name(TypeId)` replica `canonical_type_name` de stage0:
  `byte`, `size_t`, `list of int`, `frozen ref to T`, `type of` spelling.
- `mangle_type(TypeId)` replica `mangle_type`; se usa para C y para claves de
  instancia. Se cachea.
- Las runas genéricas tienen `c_name` estable; las especializaciones añaden
  `_<arg mangled>`.

### 5.4 Compatibilidad y casts

Se portan **tabularmente** desde `pengu_types.py`, con tests por variante:

- `Any`: compatible con todo, en ambas direcciones.
- `Null`: solo con `ref`, `any`, `opaque`/puntero y `frozen` aplicable.
- `BaseType`:
  - igual nombre; alias primitivos (`int`/`i32`/`int32`/`int32_t`) son el mismo
    tipo canónico;
  - entero↔entero y float↔float son implícitos; entero↔float **no**;
  - `char`/`byte` cuentan como enteros, pero tienen reglas propias de
    literales/casts;
  - `opaque` acepta `null`;
  - `string` no se convierte a número ni al revés con `to`.
- `RefType`:
  - `ref to frozen T` no fluye a `ref to T`; al revés sí;
  - `void*` es catch-all de punteros, con la misma dirección de `frozen`;
  - `char`/`byte` comparten pointee;
  - `ref to fn` acepta un valor `fn` compatible.
- `FrozenType`: solo `frozen T`; el valor mutable fluye a frozen, no al revés.
- `ArrayType`: elemento y tamaño; un array literal debe coincidir.
- `SliceType`/`ManyType`/`ListType`/`MapType`/`MaybeType`/`ResultType`: reglas
  de covarianza/igualdad exactas de stage0.
- `TupleType`: aridad y cada elemento.
- `FnType`: params, retorno, defaults, bounds; `ref to fn` acepta `fn`.
- `RuneType`/`EchoType`/`OmenType`: identidad nominal (módulo + nombre); los
  genéricos comparan args. `Omen` string-valued acepta `string`.
- `AliasType`: transparente en compatibilidad, conserva el nombre para
  `type of`/diagnósticos.
- `SealType`: envuelve un subyacente y restringe casts/operaciones como stage0.
- `ConceptType`: no es un tipo de valor; solo bounds.
- `TypeParam`: wildcard direccional; los bounds builtin se comprueban en
  compatibilidad, los de usuario en el checker.

Casts (`to`): portar `can_cast_to` por variante. No inventar conversiones
“razonables”; stage0 es la especificación.

### 5.5 Layout, `Donum` y conceptos

- `estimate_size(TypeId)` replica C layout (con `@packed`/`@align`).
- `type_owns_heap`, `type_needs_deep_clone`, `receiver_deep_copies_on_store`,
  `automatic_donum`, `_field_type_is_donum` se portan y se usan en F3/F4.
- `PRIMITIVE_IMPLS`, `PRIMITIVE_ALIAS_GROUPS`, `PRIMITIVE_ALIASES`,
  `canonical_primitive_name`, `primitive_lookup_order`,
  `_CANONICAL_DISPLAY_OVERRIDES`, `_CANONICAL_EXTRA_ALIASES`.
- `CONCEPT_OPERATORS`, `CONCEPT_REFINES`, `concept_grants`, `concept_implies`,
  `type_implements_builtin_concept`, `implements_concept`,
  `resolve_concept_method`, `check_generic_bounds`.
- `BUILTIN_CONCEPTS`: `Num`, `Integrum`, `Real`, `Par`, `Ordo`, `Vinculum`,
  `Imago`, `Nexus`, `Forma`, `Iterabilis`, `Donum`.
- `derive` permitido: `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`;
  `Donum` es automático; `Imago` y `Nexus` van en pareja.

### 5.6 `ast_to_type`

`SemaTypeTable` convierte nodos de tipo de F2:

- `base_type`: primitivo canónico; `any`/`opaque`.
- `custom_type`: `dotted_path` + args; resolver tipo en el scope/módulo;
  genérico sin args → E0021; especialización con `substitute`.
- `ref_type`, `frozen_type` (sugar de `frozen ref`), `array_type`
  (multidimensional derecha→izquierda, tamaño INT/const/NAME), `slice_type`,
  `many_type`, `list_type`, `map_type`, `maybe_type`, `result_type`
  (default `error`), `tuple_type`, `fn_type`, `opaque_type`.
- `type_or_param`: `shard_param_ref` → `TkTypeParam`; tipo normal envuelto.
- Validar `T` fuera de genérico → E0022.
- Reproducir `ast_to_type` de stage0 **incluidos sus casos raros**
  documentados (alias transparente, `None` de `of`, tipo `T` mayúscula).

---

## 🗂️ 6. Símbolos, scopes y módulos

### 6.1 `SemaSymbol`

```pengu
omen SemaSymbolKind:
    SkVar, SkLet, SkConst, SkParam, SkStaticVar
    SkWeave, SkDeclare, SkType, SkRune, SkEcho, SkOmen, SkAlias, SkSeal,
    SkConcept, SkImport, SkCDefine, SkTest

rune SemaSymbol:
    name as int
    type as int
    kind as SemaSymbolKind
    flags as int
    c_name as int
    module as int
    line as int
    col as int
    attrs_node as int
    doc as int
    const_id as int
    first_bound as int
    bound_count as int
    module_scope as int
```

- `flags`: mutable, public, static, ritual, inline, antiquus, self_is_value,
  defined_in_c, is_mutating.
- `const_id`: índice en `consts` (`SemaConst`), `-1` si no es constante.
- `module_scope`: índice de scope para un símbolo `import`.
- `c_name`: nombre C efectivo (con `insignia` y desambiguación).
- Los símbolos se crean en orden de declaración; IDs deterministas.

### 6.2 `SemaScope`

```pengu
rune SemaScope:
    parent as int
    kind as SemaScopeKind
    bindings as map of string to int
    with_type as int
    with_is_mutable as bool
    with_target_name as int
    enchanting_type as int
    return_type as int
    in_loop as bool
    in_or_block as bool
    is_ritual as bool
    start_line as int
    end_line as int
    loop_label as int
    loop_labels as map of string to int
```

- `SemaScopeKind`: global, weave, enchanting, lambda, if, while, for, with,
  or_block, block, test.
- `push_scope`/`pop_scope` replican herencia de contexto de stage0.
- `lookup`, `lookup_local`, `lookup_at` (por línea, para LSP).
- `self` se define en `enchanting` como `ref to T`; en primitivos puede ser
  valor (`self_is_value`).
- `declare_loop_label`/`enclosing_loop_label` con frontera de lambda.

### 6.3 `SemaSymbols`

Portar los registros de `SymbolTable`:

- scopes, current scope, all scopes.
- `runes`, `echos`, `omens`, `aliases`, `seals`, `concepts`.
- `concept_bindings`, `bind_method_owner`.
- `functions`, `methods`, `mutating_methods`.
- `consts`.
- `generic_runes`, `generic_echos`, `generic_omens`, `generic_aliases`,
  `generic_concepts`, `generic_functions`, `generic_methods`.
- `generic_function_owner`.
- `primitive_method_owners`, `shard_method_bounds`.
- `monomorphized_types`, `monomorphized_functions`, `monomorphized_methods`.
- `types_by_module`, `current_module`.
- `includes`, `links`, `ldflag`, `ldflag_origins`, `link_origins`,
  `imports`, `imported_modules`, `import_graph`, `import_order`, `insignia`.
- `imported_names` para LSP.
- `_init_builtins`: primitivos, `print`, conceptos.
- `lookup_type` con búsqueda module-local primero; dotted `mod.Type`;
  aliases/seals/concepts/runes/echos/omens; monomorphized.
- `get_all_visible_names` para LSP.

### 6.4 Módulos

`SemaModule`:

```pengu
rune SemaModule:
    path as string
    display_path as string
    source as SourceFile
    lex as LexResult
    parse as PsParseResult
    ok as bool
    scope as int
    exports as int
    is_entry as bool
    is_std as bool
    sha256 as string
```

- `SemaProgram`:
  - `modules as list of SemaModule`
  - `by_path as map of string to int`
  - `import_order as list of int`
  - `root as int`
  - `types as SemaTypeTable`
  - `symbols as SemaSymbols`
  - `annotations as SemaAnnotations`
  - `instances as SemaInstances`
  - `names as NamePool`
  - `diagnostics as diag.DiagnosticBag`
  - `options as SemaOptions`
  - `comptime as CompileTimeEnv`

### 6.5 Resolución de imports

Orden de búsqueda (réplica de `find_module_path`):

1. `std.` → directorios estándar (`--std-dir`, entorno, raíz/std), candidatos
   `.pengu`, `.d.pengu`, `__init__.pengu`, `__init__.d.pengu`.
2. Relativo al directorio del importador.
3. `base_dir/src_dir`.
4. `base_dir/lib_dir/<binding>/pengu/` y `<binding>/`.
5. `base_dir/`.

Reglas:

- `dotted_path` → `a/b/c`.
- `import a.b as c`: alias `c`; sin alias, último segmento.
- `import a.b` y `import a.b as c` del mismo módulo: no duplicar chequeo,
  pero sí registrar alias.
- Duplicado exacto del mismo alias → E0004.
- Ciclo → E0004 con cadena legible.
- Archivo no hallado → E0004.
- `__init__.pengu` y `.d.pengu`.
- `module_sources` en memoria (LSP) tiene prioridad sobre disco; F3 acepta un
  mapa `path -> string` en opciones para el futuro inmediato.
- El orden topológico es DFS determinista, dependencias antes que importador;
  `import_order` se expone.
- `is_main` solo para el entry; los imports ven `main=false`.
- `std` se marca para reglas de privacidad/visibilidad.

### 6.6 Exports y privacidad

- Nombres que empiezan por `_` no se exportan.
- Un módulo exporta:
  - símbolos públicos del scope;
  - tipos declarados (runas/echos/omens/aliases/seals/concepts), aunque no
    estén en el scope;
  - consts (con valor);
  - genéricos propios, con su owner;
  - métodos/concept bindings.
- Al importar:
  - el `module_scope` permite `mod.Name`;
  - se registran alias `mod_Name` y C names para tipos/funciones/consts;
  - los genéricos solo se prefijan si el owner es el módulo importado;
  - los tipos re-exportados conservan su procedencia.
- `insignia` del módulo se propaga a sus nombres C; no se hereda al
  importador.

---

## 🧱 7. Checker de declaraciones y statements

### 7.1 Declaraciones top-level

- `import`, `include`, `link`, `ldflag`, `insignia`.
- `const`: tipo explícito o inferido; valor constante; `type of`/`size of`;
  duplicados entre módulos; `const` solo top-level.
- `var`/`let` top-level → E0002; `static var` top-level → E0002.
- `rune`/`echo`:
  - atributos, `cyclus`, `shard`, `derive`;
  - campos, colisiones C, recursión por valor (E0050), visibilidad;
  - `@packed`/`@align` y layout.
- `omen`:
  - variantes, valores duplicados (E0027), valores constantes (E0029),
    payload con valor (E0028), string-valued, algebraic;
  - derivables.
- `alias`/`seal`:
  - alias genérico, transparencia, `seal` del subyacente;
  - alias público/privado.
- `concept`:
  - métodos requeridos, firmas, genéricos.
- `bind`:
  - tipo + concepto + `shard`, métodos `weave`;
  - coherencia E0030/E0031/E0052.
- `weave`/`declare`:
  - atributos, modificadores `inline`/`ritual`, `shard`/`where`,
    parámetros, defaults, `many` (E0023/E0024), retorno;
  - genéricos y bounds;
  - `@mutates` (E0067/E0066/E0068);
  - `antiquus` cuerpo C (sin check).
- `enchanting`:
  - receptor tipo/`shard`, where, métodos, `self` ref/value, `ritual`.
- `test`:
  - nombre válido (E0064), cuerpo de statements.
- `when` top-level:
  - evaluar condición; recolectar la rama activa; `else when`.

### 7.2 Statements

- `block`/`simple_stmt` (una línea).
- `var`/`let`/`const`/`static var` locales:
  - `const` dentro de weave → E0001 (salvo constante evaluable? portar regla);
  - tipo opcional/inferido; `with:`/indent literal;
  - scopes.
- `set`/`compound_set`:
  - target normal/with/essence;
  - mutabilidad E0006; tipos;
  - `@mutates` rewrite y errores.
- `if`/`unless`/`while`/`for`/`for in`/`for range`:
  - condiciones bool, scopes, loops, labels, break/continue E0007;
  - tipos de elementos; range bounds; `step`.
- `when` statement: rama activa, `else`.
- `unsafe`: warning W0007, reglas de bounds/overflow.
- `with target:` statement:
  - target mutable, accesos `.field`, builder.
- `with:` builder expression:
  - statements permitidos (E0014), target type, fields, mutabilidad.
- `defer`/`errdefer`: solo en weave; expresión/block; ownership.
- `banish`: solo punteros/valores owning; E0008; no literal/const.
- `return`: tipo, múltiples valores, implícito, `do`/value blocks.
- `judge`/`judge over`: exhaustividad E0044, payloads, guards, narrowing.
- `expr_stmt`: evaluate; void/valor descartado; mutating calls.
- labels: duplicados E0069, break/continue a label, frontera lambda.

### 7.3 Ownership y memoria

- `banish expr`: comprobar que el tipo es owning/ref o `opaque`; no doble
  banish estático (lo que stage0 detecta); no banish de const/literal.
- `defer`/`errdefer`: contexto y orden.
- `some`/`ok_of`/`err_of`: move/box; no usar después; stage0 no hace análisis
  de flujo completo, sino reglas locales.
- `with:` builder: no escapa del bloque; assignment a target.
- `static var`: solo dentro de weave; E0063; estado de módulo.
- `@mutates`: solo método; receptor mutable; no en expresión si no es
  statement; no `get_` colisión.
- `ref`/`frozen`: dirección de const-correctness.
- `Donum`: defaults automáticos, `donum T`, `new` sin argumentos.
- `type_owns_heap`/`needs_deep_clone` para F4.

### 7.4 Atributos y nombres

Portar `_validate_attributes` y `_c_ident`:

- `weave`: `inline`, `cold`, `deprecated`, `noreturn`, `export`.
- `enchanted_weave`: + `mutates`.
- `declare`, `rune`, `echo`, `omen`, `field`.
- `@packed`, `@align(N)` (layout).
- `@deprecated(reason)` → W0006 en usos.
- `@noreturn`/`@export`.
- Desconocido/inválido → E0056.
- Nombres reservados de C para tipos → E0035; campos C colisionando → E0065.
- Tipos duplicados que no pueden tener identidad C distinta → E0070.
- `insignia` múltiple → E0026.
- Nombres C estables y `c_name` en símbolos/tipos.

---

## 🔎 8. Inferencia de expresiones

`TypeInferrer` se divide en módulos por familia. La entrada es un `node_id` y
un `expected TypeId` opcional; el resultado es un `TypeId` y se anota en
`SemaAnnotations`.

### 8.1 Núcleo

- Literales: `int` (i64 si fuera de int32), `float`, `bool`, `char`, string.
- `var_ref`/`const`: lookup, shadowing, deprecated W0006; const tipo/valor.
- C defines mayúsculas con includes.
- `self`: ref/value, E0003/E0033.
- `paren_expr`.
- Propagación de `expected`: colecciones vacías, `maybe none`, `null`,
  literales de string como `ref to char`, etc.

### 8.2 Operadores

- Binarios: `add/sub/mul/div/mod`, bitwise, shifts, comparaciones, booleanos,
  `in`/`not in`, ranges `..`/`to`, casts `to`.
- Unarios: `neg`, `bit_not`, `log_not`, `sigil of`, `essence of`, `some`,
  `banish`, `ord`, `chr`, `bytes of`, `transmute`, `size of`, `type of`.
- Reglas de tipo:
  - numéricos; no string `+` (E0005);
  - comparación bool, char/string/map/list/maybe?;
  - type params y conceptos (`E0049`);
  - `is present/not present/true/false`;
  - `or else`/`or return`/`or:` types;
  - `try` propagation;
  - `to` cast (compat/cast).
- Short-circuit eval, no side effects en tipos.

### 8.3 Llamadas

- `calling` target:
  - función de módulo/alias;
  - método de `enchanting`;
  - método ritual;
  - método de primitivo (`int`, `string`, ...);
  - método genérico/`shard`;
  - método con `@mutates`;
  - función como valor.
- `normal_target`/`with_target`/`at_access` en targets.
- Argumentos posicionales, nombrados, defaults, `many`/varargs; E0005 en
  nombres/orden/tipos.
- Genéricos: inferir type args desde argumentos/expected; instanciar; bounds.
- `declare` externo: FnType, sin cuerpo.
- `self` como argumento implícito.
- `calling` en interpolación.

### 8.4 Acceso y contenedores

- `.field`/`->field`: rune/echo fields, `self`, privacidad E0043, omen.
- `at`/slice: array/list/slice/string; bounds/type; `at a to b`.
- `length`.
- List/map/array literals, init expressions, indent literals, struct init,
  shorthand, `with:`/`do:`.
- Empty literals con expected; sin expected → E0014/E0015.
- `some`/`donum`; `defined`.
- `for` comprehensions.

### 8.5 Control como valor

- `if_expr`, `when_expr`, `judge`, `or:`, `do:`, `with:`.
- `if_stmt`/`while`/`for` como valor de bloque; unificación de ramas.
- `lambda`/`lambda_no_params`: params, expected FnType, capture, return.
- `try`.
- Value blocks (`do_expr`, `with_init_expr`, `or_block`) y su último
  statement/expresión.
- `judge` over, payload binding, guard, narrowing.

### 8.6 Strings e interpolación

- Literales normal/raw/triple, escapes, `\xNN`, `\u{...}`.
- Interpolación: F1 `StringInfo`/`StringPart`; F2
  `parse_interpolation_expr` para cada `{expr}`; inferir con expected
  `string`; errores con posición relativa al string.
- `ref to char`/`const char*` cuando expected es C string.
- `type of`/`size of` en interpolación.

---

## 🧬 9. Genéricos, bounds e instanciación

### 9.1 Sustitución

- `substitute(TypeId, map<TypeParamId, TypeId>) -> TypeId`, recursiva y
  memoizada por `(type, map fingerprint)`.
- Alias, ref, frozen, colecciones, tuplas, fn, runes/echos/omens.
- Sustituir type args de un tipo nominal crea una nueva `SemaNominalInfo` con
  campos sustituidos y `c_name` mangled.
- Los type params de un método y de su receptor se combinan; el orden importa.

### 9.2 Bounds

- `check_generic_bounds` replica stage0:
  - bounds builtin y de usuario;
  - `T: A and B`;
  - `where` en `shard`, `bind`, `enchanting`;
  - `E0032` si no se cumple; `E0049` para operadores sin bound.
- `concept_implies` transitivo.
- `TypeParam` sin bounds no garantiza operadores.
- `shard T` en `enchanting` y en `weave`.
- `where` en la declaración y en el tipo.

### 9.3 Instanciación

- `SemaInstance`:
  - kind (`fn`, `method`, `rune`, `echo`, `omen`, `alias`, `concept`);
  - template node/symbol;
  - type args;
  - receiver type (métodos);
  - specialized `FnType`/`TypeId`;
  - flags (ritual, mutates, self_is_value);
  - source span.
- Clave: `template_id + receiver_id + type_arg_ids + flags`.
- Cache `instances_by_key: map string to int`; lista en orden de primera
  aparición.
- Instanciar cuerpos de función cuando se usan (on demand), con un presupuesto
  de profundidad/instancias para evitar explosión.
- Genéricos anidados: instanciar el cuerpo del genérico y, si llama a otro,
  crear la instancia hija.
- Funciones genéricas como valor: inferir expected FnType, instanciar,
  registrar en anotaciones.
- Tipos genéricos usados como tipo: crear `SemaNominalInfo` especializada y
  registrar en `monomorphized_types`.
- F4 consume `SemaInstances`; F3 no emite C.

### 9.4 Caché y determinismo

- IDs de instancia en orden de primera aparición determinista.
- Los mapas no definen orden de emisión; se usan listas ordenadas.
- Las claves de cache no incluyen direcciones ni hashes aleatorios.

---

## 🎭 10. Conceptos, `bind`, `enchanting` y `@mutates`

### 10.1 Conceptos

- `concept NAME [shard T] :` con `weave` requeridos.
- `bind TYPE with CONCEPT [shard T] :` implementa métodos.
- Validar:
  - concepto y tipo existen (E0004);
  - firma de método coincide (E0030);
  - no falta ningún método requerido (E0031);
  - no hay dos binds del mismo `(tipo, método)` con conceptos distintos
    (E0052);
  - métodos primitivos duplicados (E0047);
  - `@mutates` en bind/enchanting (E0067);
  - `get_<name>` collision (E0068);
  - `@mutates` en expresión (E0066).

### 10.2 Enchanting

- `enchanting TYPE [shard] [where]:`.
- Receptor normal: `self as ref to T`.
- Primitivo/`shard T` value receiver: `self` por valor, `self_is_value`.
- Métodos `ritual`: sin `self`; error E0033 si se usa.
- Llamada estática vs instancia: E0034.
- Búsqueda de método:
  1. método de `enchanting` del tipo exacto;
  2. método de primitivo con alias canónico;
  3. método genérico/`shard`;
  4. concepto/bind;
  5. módulo/función.
- Prioridad y errores deben coincidir con stage0.
- `@mutates`:
  - solo en `enchanted_weave`;
  - receptor mutable; no `self` ritual;
  - statement rewrite (receptor = resultado);
  - expresión → E0066;
  - no `get_<name>` explícito → E0068.

### 10.3 Derivaciones

- `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`; `Donum` automático.
- `Imago`/`Nexus` en pareja.
- `derive` no permitido en omen algebraico/string-valued.
- `type_owns_heap`/`type_needs_deep_clone` para decidir helpers de F4.
- F3 anota `derived` y `needs_deep_clone` en el tipo/símbolo.

---

## 🕰️ 11. Compilación condicional y constantes

### 11.1 `CompileTimeEnv`

- `os`, `arch`, `compiler`, `is_main`, `is_debug`, `wasm_target`, `is_wasm`,
  `defines`.
- Defaults de stage0: host OS/arch/compiler; `CC`/`PENGU_CC`.
- `-D NAME`, `-D NAME=value`, `-D os=...`, `-D arch=...`,
  `-D compiler=...`, `-D main`, `-D debug`, `-D wasm`.
- `defined(NAME)`.
- `wasm`/`wasm_target` derivados del target.

### 11.2 Evaluación de `when`

- `when` top-level: filtrar ítems activos antes de recolectar; la rama
  inactiva no define símbolos ni tipos.
- `when` statement: elegir rama activa; no chequear la inactiva.
- `when_expr`/`if_expr` de comptime cuando la condición es constante.
- Operadores soportados: literales, `os/arch/compiler/main/debug/wasm`, `defined`,
  aritmética/bitwise/comparaciones, `not`, `if_expr`, `when_expr`.
- División/resto con semántica C (truncado hacia cero), no Python.
- Condición no constante en un contexto comptime → error correspondiente.

### 11.3 Const folding

- Portar `ConstFolder`:
  - int/float/bool/string/char;
  - nombres const;
  - `if_expr` constante;
  - unarios/binarios/bitwise/comparaciones;
  - no plegar `some`/`ok`/`err`, `chr`, `bytes`, arrays/maps, bloques,
    lambdas, `type of` no concreto;
  - `type of` pliega el nombre canónico;
  - división/resto C.
- `const` top-level guarda `SemaConst`; los usos en array sizes/omen values/
  `when` lo consultan.
- `const` dentro de weave: solo si es evaluable; si no, E0001.
- `static var`/const placement.

---

## 🩺 12. Diagnósticos, warnings y recuperación

### 12.1 Códigos

F3 implementa los códigos semánticos del catálogo:

- `E0001–E0009`: reglas básicas (const/var/self/undefined/mismatch/
  mutabilidad/control/banish/with).
- `E0014–E0015`: builders/arrays.
- `E0021–E0024`: genéricos/many.
- `E0026–E0034`: insignia/omen/conceptos/rituales.
- `E0041–E0044`: arrays/range/privacidad/judge.
- `E0047`, `E0050`, `E0052`, `E0056`, `E0057`.
- `E0063–E0070`: static var/test/C fields/mutates/type names.
- `E0000` viene de F1/F2 y se conserva en el bag.
- `E0061/E0062` (lockfile) se dejan a F6/F9.

Cada código tiene en `sema/diagnostics.pengu`:

- nombre (`SemaCode`),
- mensaje base/plantillas,
- help/note por defecto (portados de stage0),
- constructor con span.

### 12.2 Warnings

- `W0001` transmute inseguro.
- `W0002` lectura de echo sin tag.
- `W0004` código inalcanzable en ramas.
- `W0005` shadow de función global (y comparte código con el warning de
  indentación de F1; F3 no lo duplica).
- `W0006` símbolo deprecado.
- `W0007` bloque `unsafe`.
- `W0013` rango `..` deprecado.
- `W0000` fallback; `W0003` reservado.
- `# pengu: allow-warnings Wxxxx` por módulo; se parsea del texto/comentarios.
- `--deny-deprecated` convierte W0006 en error de salida (política CLI).

### 12.3 Recuperación

- `SemaState`:
  - `errors`, `warnings`, `max_errors`, `stop_after_first`;
  - `TkError`/`SymbolError`;
  - `last_error` para deduplicar;
  - `stop` por presupuesto.
- Al fallar una declaración:
  - registrar el símbolo con `TkError` (si se conoce el nombre);
  - saltar su cuerpo;
  - continuar con la siguiente.
- Al fallar un statement:
  - anotar `TkError`;
  - seguir con el siguiente statement del bloque.
- Al fallar una expresión:
  - devolver `TkError`; no propagar cascadas;
  - `TkError` es compatible con todo en modo recuperación.
- Las funciones `sema_check_*` no lanzan; devuelven `bool`/`SemaStatus`.
- Nunca se usa `spark.panic` para entrada de usuario.
- El LSP obtiene scopes/símbolos parciales y diagnósticos.

### 12.4 Paridad

- Mismos códigos y spans (byte line/col).
- El primer error de stage0 se compara con el primero de PSC.
- Se comparan también los conjuntos de errores cuando stage0 los acumula.
- Los warnings se comparan por código/posición; el texto puede diferir.
- Allowlist justificada en `psc/tools/sema_allowlist.txt`.
- `SEMA_ERRORS.md` documenta diferencias deliberadas.

---

## 🧾 13. Contrato con F4: anotaciones semánticas

F4 no debe volver a inferir. `SemaAnnotations` es una lista paralela al AST:

```pengu
rune SemaAnnotation:
    type_id as int
    symbol_id as int
    aux as int
    flags as int
```

- `type_id`: tipo inferido de la expresión/declaración.
- `symbol_id`: símbolo resuelto de un `var_ref`/llamada/import.
- `aux`: `NameId` del C name, `TypeId` de tupla, `InstanceId`, etc.
- `flags`: bits `HAS_TYPE`, `HAS_SYMBOL`, `MUTATING_CALL`, `TUPLE_VALUE`,
  `FN_VALUE`, `BIND_MAYBE`, `BIND_ELEM`, `JUDGE_OVER_CHECKED`, etc.
- Se accede por `node_id`; se inicializa una anotación por nodo del AST.
- Tablas auxiliares:
  - `instances` (F4 emite);
  - `bind_maybe_types`/`bind_elem_types` para narrowing;
  - `tuple_types`/`fn_types` si no caben en `aux`;
  - `const_values` en símbolos;
  - `module_exports`;
  - `link/includes/ldflags` en `SemaProgram`.

F4 necesita, como mínimo:

- tipo de cada expresión;
- símbolo y C name de cada referencia/llamada;
- target de cada llamada (módulo/método/ritual/primitivo/bind);
- instancias genéricas con type args y receptor;
- tipos de rune/echo/omen/alias/seal con campos, variantes, bounds y derivas;
- consts y sus valores;
- métodos `@mutates`;
- atributos y layout;
- includes/links/ldflags;
- tests y entry metadata;
- `judge` narrowing y bloques-valor.

El contrato se congela en CP0 y se documenta en `psc/docs/SEMA.md`.

---

## 🗂️ 14. Módulos, archivos y DAG

### 14.1 Árbol propuesto

```text
psc/src/psc/sema/
  api.pengu
  options.pengu
  state.pengu
  result.pengu
  names.pengu
  diagnostics.pengu
  annotate.pengu

  types/
    kind.pengu
    table.pengu
    builtins.pengu
    canonical.pengu
    compat.pengu
    convert.pengu
    layout.pengu
    concepts.pengu

  symbols/
    symbol.pengu
    scope.pengu
    table.pengu
    builtins.pengu

  modules/
    resolver.pengu
    loader.pengu
    graph.pengu
    exports.pengu

  generics/
    substitute.pengu
    bounds.pengu
    instantiate.pengu

  comptime/
    env.pengu
    fold.pengu
    when.pengu

  check/
    attributes.pengu
    decls.pengu
    records.pengu
    weaves.pengu
    statements.pengu
    control.pengu
    set.pengu
    with.pengu
    judge.pengu
    ownership.pengu

  infer/
    core.pengu
    literals.pengu
    operators.pengu
    calls.pengu
    access.pengu
    containers.pengu
    control.pengu
    strings.pengu
    lambdas.pengu
```

### 14.2 Tamaño estimado

| Grupo | Archivos | Líneas |
|---|---:|---:|
| core/options/names/diagnostics/annotate | 7 | ~2 000 |
| types | 8 | ~3 200 |
| symbols | 4 | ~1 500 |
| modules | 4 | ~1 500 |
| generics | 3 | ~1 200 |
| comptime | 3 | ~900 |
| check | 10 | ~4 500 |
| infer | 9 | ~4 200 |
| api/result/state | 3 | ~800 |
| **Total** | **~48** | **~19 800** |

Es comparable a las 18 424 líneas de stage0: PenguScript es más verboso en
tipos/ownership, pero la división evita el monolito.

### 14.3 DAG

```text
F1/F2: source, tokens, ast, parser, diagnostics
        │
        ▼
sema/names ──▶ sema/types ──▶ sema/symbols
        │                         │
        ▼                         ▼
sema/diagnostics ◀──── sema/state ─────▶ sema/modules
        │                         │
        ▼                         ▼
sema/comptime ◀──────── sema/generics
        │                         │
        ▼                         ▼
sema/check ◀──── hooks ─────▶ sema/infer
        │                         │
        └──────────┬──────────────┘
                   ▼
              sema/annotate
                   │
                   ▼
               sema/api
```

- `check` e `infer` no se importan entre sí; usan hooks.
- `types` no depende de símbolos; los nombres de tipos se resuelven por
  callback/`SemaSymbols`.
- `modules` depende de F2 y de `symbols`/`types`.
- `api` importa todo y libera.

### 14.4 Colisiones

Cada módulo declara `insignia sema_<área>_`; las funciones tienen nombres
legibles y los tipos `Sema*`. Antes del cierre se compara la lista de nombres
con `std/*.pengu` y se renombra cualquier colisión real. `insignia` prefija C,
no la resolución de símbolos, así que la auditoría sigue siendo obligatoria.

---

## 🖥️ 15. CLI y API pública

### 15.1 `psc check`

```bash
psc check psc/src/main.pengu
psc check --base-dir psc --src-dir src psc/src/main.pengu
psc check --diagnostics=json std/arena.pengu
psc check --stop-after-first --max-errors=1 tests/fixtures/sema_bad.pengu
psc check -D os=linux -D DEBUG --target wasm32-wasi src/main.pengu
psc check --dump-sema --no-color src/main.pengu
```

Flags:

- `--base-dir`, `--src-dir`, `--lib-dir`, `--std-dir` (repetible).
- `-D/--define`, `--os`, `--arch`, `--compiler`, `--target`, `--debug`.
- `--deny-deprecated`.
- `--diagnostics=plain|json`, `--color/--no-color`, `--quiet`.
- `--max-errors=N`, `--stop-after-first`.
- `--dump-sema`, `--no-header`.
- `--help`.

Exit codes: 0 sin errores, 1 con errores, 2 uso/E-S. Warnings no fallan salvo
`--deny-deprecated`.

### 15.2 API

```pengu
weave sema_check_file with path as string, opts as SemaOptions into SemaResult
weave sema_check_text with path as string, text as string, opts as SemaOptions into SemaResult
weave sema_free_result with r as ref to SemaResult into void
weave sema_dump with program as ref to SemaProgram, root as int, include_header as bool into string
weave sema_symbols_for_lsp with program as ref to SemaProgram, line as int into list of SemaSymbol
```

- `SemaResult` contiene `program`; el llamador lo usa y luego llama a
  `sema_free_result`.
- El CLI y los tests usan la misma API.
- `sema_check_text` permite LSP/tests sin archivo; `path` sigue siendo la
  identidad del módulo.

---

## 🗓️ 16. Orden de implementación y checkpoints

### 16.1 Secuencia

| # | Paso | Días | Depende | Entregable |
|---:|---|---:|---|---|
| 0 | Contract/spike: `SemaType`, side tables, interning, hooks, dump | 3 | — | CP0 congelado |
| 1 | Core: options, state, names, result, diagnostics base, annotate | 3 | 0 | Esqueleto compilable |
| 2 | Types: kind/table/builtins/canonical/compat/convert/layout | 8 | 1 | Modelo de tipos y tests |
| 3 | Symbols: symbol/scope/table/builtins | 5 | 2 | Scopes y lookup |
| 4 | Modules: resolver/loader/graph/exports | 7 | 3 | Imports y exports |
| 5 | Decl collection: const/vars, rune/echo/omen, alias/seal, concept/bind, weave/enchanting, declare/antiquus, test/when top | 9 | 4 | Firmas y símbolos top-level |
| 6 | Declared types/layout/names/atributos | 4 | 5 | Tipos validados |
| 7 | Check statements/control/set/ownership/with/judge/labels | 9 | 6 | Cuerpos locales |
| 8 | Infer core/literals/operators/access/containers | 8 | 7 | Expresiones básicas |
| 9 | Infer calls/methods/generics/lambdas/strings | 10 | 8 | Llamadas y genéricos |
| 10 | Concepts/bind/enchanting/mutates/ritual | 6 | 9 | Semántica de conceptos |
| 11 | Comptime/when/defined/const fold | 4 | 5 | `when` y consts |
| 12 | Diagnostics parity, recovery, LSP symbols, dump | 6 | 10,11 | Errores y sema dump |
| 13 | Tests/oracles/corpus/fuzz/ASan/bench/docs | 9 | 12 | F3 cerrada |
|  | **Total** | **~83** |  | |

14–18 semanas calendario con revisión e imprevistos.

### 16.2 Checkpoints

1. **CP0 — contrato.** `SemaType`, `SemaSymbol`, `SemaAnnotation`,
   `SemaProgram`, hooks y formato de `--dump-sema`.
2. **CP1 — módulos.** Resolver/cargar/ordenar imports; `psc check` mínimo;
   diagnósticos multi-fuente.
3. **CP2 — firmas.** Todo el corpus recolecta tipos, símbolos y funciones sin
   error de recolección.
4. **CP3 — tipos.** Compatibilidad, casts, canonicalización, layout y
   conceptos con tests unitarios y oracle de tipo.
5. **CP4 — cuerpos.** Statements, control, ownership y `with`/`judge`.
6. **CP5 — expresiones.** Inferencia completa de operadores, accesos,
   contenedores y strings.
7. **CP6 — llamadas/genéricos.** Métodos, primitivos, bounds, instancias,
   funciones como valores.
8. **CP7 — concepts.** Bind/enchanting/mutates/ritual con coherencia.
9. **CP8 — comptime.** `when`, `-D`, const folding, `main`/`wasm`.
10. **CP9 — paridad.** Errores/warnings y sema dump; allowlist.
11. **CP10 — cierre.** Fuzz, ASan, benchmark, docs, DoD.

### 16.3 No se hará aunque sobre tiempo

- Codegen/C.
- LSP completo.
- Caché en disco.
- Manifest/lockfile completos.
- Refactors cosméticos del AST.
- Nuevas features del lenguaje.

---

## 🧪 17. Tests, oráculos y paridad

### 17.1 Unitarios `.pengu`

`psc/tests/sema_unit.pengu` (~50–70 tests), con un fixture:

- `SemaFixture` que escribe texto, llama `sema_check_text`, expone errores,
  warnings, símbolos y tipos.
- Grupos:
  1. builtins, primitivos, canonicalización, `type of`.
  2. refs/frozen/alias/seal.
  3. arrays/slices/lists/maps/maybe/result/tuplas.
  4. rune/echo/omen; campos, variantes, derive, recurse.
  5. funciones/parámetros/defaults/many/retorno.
  6. scopes, mutabilidad, shadowing, labels.
  7. `set`/`banish`/`defer`/`static var`/unsafe.
  8. `with:`/`with target:`/`do:`/`or:`.
  9. `judge`/`judge over`, exhaustividad, payloads, guards.
  10. genéricos/bounds; genérico→genérico; función genérica como valor.
  11. concept/bind/enchanting/ritual/mutates.
  12. `when`/`defined`/`-D`/`main`/`wasm`.
  13. módulos: import, alias, privacidad, ciclo, `__init__`, `.d.pengu`.
  14. errores: un test por código relevante.
  15. warnings y `allow-warnings`.
  16. recuperación y determinismo del sema dump.

### 17.2 Corpus

`psc/tests/sema_corpus.pengu`:

- recorre los 205 `.pengu` con sus `base_dir`/`src_dir` correctos;
- exige 0 errores semánticos;
- cuenta módulos, símbolos, tipos, instancias;
- imprime `corpus: files=205 errors=0`.

### 17.3 Oráculo de aceptación/rechazo

`psc/tools/sema_oracle.py`:

- para cada archivo del corpus:
  - stage0: `PenguChecker(base_dir, src_dir, lib_dir).check(parse(source))`;
  - PSC: `psc check --diagnostics=json --stop-after-first`;
  - compara ok/err, primer `code`, línea y columna (byte);
  - compara warnings por código/posición;
- para casos negativos extraídos de `tests/compiler`:
  - `tools/extract_sema_cases.py` extrae literales de `parse_and_check`,
    `checker.check`, `emit_c` y tests similares;
  - descarta los dinámicos (`f"""`, concatenaciones, variables) y los
    registra en `skipped_dynamic.txt`;
  - ejecuta stage0 y PSC sobre cada snippet con `base_dir=ROOT`;
  - compara aceptación/rechazo y primer error.
- Salida:
  ```text
  corpus files=205 accept_ok=205 errors=205 pos_ok=205
  cases=... accept_ok=... pos_ok=... allowed=... failures=0
  ```
- `--verbose` muestra el primer diff.
- `sema_allowlist.txt` justifica divergencias.

### 17.4 Oráculo de tipos y sema dump

`psc/tools/sema_type_oracle.py`:

- monkeypatchea `TypeInferrer.infer` de stage0 para registrar
  `(path_de_nodo, canonical_type_name)` durante un `check` real;
- stage0 y PSC comparten la estructura de árbol de F2; el path es la lista de
  índices de hijos;
- PSC `psc check --dump-sema` emite, por path:
  - tipo inferido;
  - símbolo resuelto;
  - C name (cuando aplica);
  - flags de anotación;
- compara los tipos donde stage0 registró una inferencia;
- compara además la tabla de símbolos top-level (nombre, tipo canónico, kind,
  c_name, const) y los métodos;
- 15–25 casos golden: std/arena, std/json, std/loom, judge, generics,
  concepts, comptime, privacidad, etc.

Formato de `--dump-sema` (anexo F):

```text
# psc-sema-dump v1
# module: std/arena.pengu
module std/arena.pengu ok=true
  type Arena rune c_name=Arena fields=6 methods=12
  symbol new kind=weave type=... line=...
  expr path=0.4.2.1 type=int symbol=...
```

### 17.5 Golden de diagnósticos

`psc/tools/run_f3_checks.py`:

- 20–30 casos de error (uno por código relevante);
- 10–15 positivos con sema dump;
- compara stderr (plain) o stdout (`--dump-sema`);
- `--update-golden` con revisión manual.

### 17.6 Fuzz semántico

`psc/tests/fuzz_sema.pengu`:

- parte de fuentes válidas del corpus/fixtures;
- mutaciones deterministas:
  - truncar en posiciones;
  - borrar/duplicar/cambiar identificadores, tipos, operadores, números;
  - sustituir `T`/conceptos por nombres inexistentes;
  - anidar `if`/`with`/`judge`/genéricos;
- `sema_check_text` con `max_errors` bajo;
- assert: no panic, no cuelgue, diagnósticos deterministas;
- 100 000 iteraciones en CI; 1 000 000 en el gate de cierre.

### 17.7 ASan/UBSan

- `psc check` sobre 205 archivos.
- Fuzz bajo ASan (10 000–20 000).
- Tests unitarios.
- Cero leaks/UB.

### 17.8 Integración pytest

`tests/psc/test_f3_acceptance.py`:

- build de `psc`;
- `run_f3_checks.py`;
- `sema_unit.pengu`;
- `sema_corpus.pengu`;
- CLI check (stdin, JSON, `-D`, módulos);
- `PSC_PARITY=1`: `sema_oracle.py` y `sema_type_oracle.py`;
- no fuzz grande por defecto.

### 17.9 Paridad de warnings

- Comparar códigos y posiciones de `W0001`, `W0002`, `W0004`, `W0005`,
  `W0006`, `W0007`, `W0013` en casos concretos.
- Stage0 a veces emite warnings sin span; PSC siempre tiene span; si el
  código coincide, se permite diferencia de posición para esos casos,
  documentada.

---

## ⚡ 18. Rendimiento y determinismo

### 18.1 Reglas

- `TypeId` interning: igualdad O(1); compatibilidad estructural con cache.
- Nombres internados; nunca `slice` por token en bucles calientes.
- Scopes con mapas; lookup O(1) promedio.
- Sin `map` para orden de emisión; listas ordenadas.
- Sin excepciones; sin asignación por nodo salvo anotaciones.
- Parseo de cada módulo una vez; cache en memoria.
- Genéricos instanciados on demand y cacheados.
- Comptime/const folding solo cuando aporta; no re-evaluar.
- Los strings de diagnóstico solo se construyen al emitir.

### 18.2 Objetivos

- `psc check` de los 205 archivos en proceso: **< 2 s** (objetivo), mínimo
  **5× más rápido que stage0**.
- Sin regresión en `psc parse`/`psc lex`.
- Memoria lineal en nodos + tipos + símbolos; sin fugas.
- Determinismo byte a byte en `--dump-sema` y diagnósticos.
- Bench `bench_sema.pengu` con casos debug/release.

---

## ✅ 19. Criterios de aceptación (DoD)

### 19.1 Funcional

- [ ] `cd psc && pengu build` compila sin warnings nuevos.
- [ ] `psc check <archivo>` funciona y devuelve 0/1/2.
- [ ] `--diagnostics=json`, `--stop-after-first`, `--max-errors`, `-D`,
      `--target`, `--dump-sema` funcionan.
- [ ] Los 205 archivos del corpus pasan sin errores semánticos.
- [ ] `std/` completo pasa.
- [ ] Imports: alias, privacidad, ciclos, `__init__`, `.d.pengu`, `std/src/lib`.
- [ ] Declaraciones: rune/echo/omen/alias/seal/concept/bind/weave/enchanting/
      declare/antiquus/test/when.
- [ ] Tipos: primitivos, ref/frozen, arrays/slices/many/lists/maps/maybe/
      result/tuplas/fn, genéricos, runes/echos/omens.
- [ ] Expresiones: todas las del lenguaje, incluidas interpolación, lambdas,
      `judge`, `with`, `do`, `or`, `try`, `for_comp`.
- [ ] Ownership: `banish`, `defer`, `errdefer`, `some`, `ok`/`err`, consts.
- [ ] Genéricos: bounds, anidados, función genérica como valor, métodos shard.
- [ ] Conceptos/bind/enchanting/ritual/mutates.
- [ ] `when`/`defined`/`-D`/`main`/`debug`/`wasm`.
- [ ] Warnings y `allow-warnings`.
- [ ] Recuperación: varios errores, sin cascadas, símbolos parciales.
- [ ] `--dump-sema` determinista.

### 19.2 Paridad

- [ ] Aceptación/rechazo 100 % en corpus y casos extraídos.
- [ ] Código/línea/columna del primer error ≥95 % (objetivo 100 %) con
      allowlist justificada.
- [ ] Conjunto de errores comparable en casos con múltiples.
- [ ] Sema dump de 15–25 golden cases exacto.
- [ ] Firmas top-level de todo el corpus exactas.
- [ ] Warnings relevantes con código/posición.
- [ ] Allowlist vacía o mínima y documentada.

### 19.3 Robustez

- [ ] Fuzz 100 000 sin crashes/cuelgues; 1 000 000 en cierre.
- [x] ASan/UBSan limpio sobre el núcleo F3 y una muestra representativa del corpus (main/oracle/petitio/cipher/arithmancy/judge). El fuzz de F1/F2 sigue siendo la puerta de entradas adversariales.
- [ ] Entradas adversariales: profundidad, tipos recursivos, genéricos
      explosivos, ciclos, imports faltantes.
- [ ] Sin `spark.panic` para entrada de usuario.
- [ ] Sin fugas en scopes/mapas/tipos.

### 19.4 Rendimiento/determinismo

- [ ] Corpus in-process < 2 s y ≥5× stage0.
- [ ] Dos ejecuciones producen bytes idénticos.
- [ ] Sin rutas absolutas/timestamps en dumps.
- [ ] Memoria lineal.

### 19.5 Documentación

- [ ] `psc/docs/SEMA.md` (arquitectura, pasadas, API, ownership).
- [ ] `psc/docs/TYPES.md` (modelo, compatibilidad, casts, conceptos).
- [ ] `psc/docs/MODULES.md` (resolución/exports/privacidad).
- [ ] `psc/docs/SEMA_ERRORS.md` (códigos, condiciones, help/note, allowlist).
- [ ] `psc/docs/PARITY.md` actualizado con F3.
- [ ] `psc/docs/OWNERSHIP.md` actualizado.
- [ ] `psc/README.md` actualizado.
- [ ] `PLAN_F3_SEMA.md` con estado real al cerrar.

---

## ⚠️ 20. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Desviación de compatibilidad/casts | Alta | Muy alto | Port tabular + tests por variante + oracle de tipos |
| Genéricos anidados/explosión | Alta | Alto | Instancias cacheadas, presupuesto, tests B1/B10 |
| Módulos/exports/privacidad | Alta | Alto | Oráculo con corpus, casos de ciclo/alias, F3a temprano |
| Errores con posiciones distintas | Alta | Alto | Oráculo código/posición, allowlist, spans byte |
| Recuperación con cascadas | Media | Alto | `TkError`, `max_errors`, tests negativos, fuzz |
| Monolito checker/infer | Media | Medio | Hooks, módulos <800 líneas, revisión CP |
| Fugas en scopes/tipos | Alta | Alto | Ownership table, ASan desde CP2, `free_program` |
| Rendimiento pobre | Media | Medio | Interning, caches, benchmark, perfil |
| Stage0 bugs o rarezas | Alta | Medio | Allowlist + tests; no emular bugs sin decisión |
| Nombres globales colisionan | Media | Medio | Prefijos + auditoría de nombres |
| Tipos `T`/`any`/`null` mal resueltos | Media | Alto | Tabla de unresolved, tests `type_has_unresolved_parts` |
| Comptime no determinista | Media | Medio | Env explícito, `-D`, tests OS/arch/target |
| F4 contamina F3 | Alta | Alto | Contrato de anotaciones CP0; no codegen en F3 |
| Caché/incremental prematuro | Baja | Bajo | Postergar a F5/F6 |

---

## ❓ 21. Decisiones que necesito de ti

### D1 — Tipos

- [x] **Recomendado:** tabla plana `TypeId` + side tables.
- [ ] Alternativa: `omen Type` recursivo con refs/arena.

### D2 — Símbolos

- [x] **Recomendado:** `SemaSymbol` POD + scopes con mapas.
- [ ] Alternativa: objetos con listas/búsqueda lineal.

### D3 — Checker/infer

- [x] **Recomendado:** módulos separados + `SemaHooks`.
- [ ] Alternativa: un módulo recursivo monolítico.

### D4 — Genéricos

- [x] **Recomendado:** instanciar/validar en F3 y exponer `SemaInstances` a F4.
- [ ] Alternativa: dejar la monomorfización a F4.

### D5 — Recuperación

- [x] **Recomendado:** acumular, `TkError`, seguir; LSP parcial.
- [ ] Alternativa: abortar al primer error.

### D6 — Diagnósticos

- [x] **Recomendado:** códigos/posiciones exactos, mensajes portados y allowlist.
- [ ] Alternativa: mensajes nuevos sin paridad.

### D7 — CLI

- [x] **Recomendado:** `psc check` de entry + imports con opciones.
- [ ] Alternativa: esperar a F6.

### D8 — Caché

- [x] **Recomendado:** solo memoria en F3.
- [ ] Alternativa: caché en disco ahora.

### D9 — LSP

- [x] **Recomendado:** exponer `SemaProgram`/scopes/símbolos.
- [ ] Alternativa: solo CLI.

### D10 — Dump semántico

- [x] **Recomendado:** `--dump-sema` + oráculo de tipos.
- [ ] Alternativa: solo aceptación/rechazo.

### D11 — Nombres y división

- [x] **Elegido:** `insignia sema_<área>_` + nombres legibles + tipos `Sema*`;
  ~48 módulos, todos <~800 líneas; si un módulo crece, se parte en subcarpeta.
- [ ] Alternativa: un checker de 3 000 líneas o prefijos en todos los helpers.

### D12 — F1/F2

- [x] **Recomendado:** no cambiar F1/F2 salvo bug bloqueante; si se toca,
  regresión y `PARITY.md`.
- [ ] Alternativa: reabrir el front-end.

**Si dices “todas las recomendadas”, empiezo por CP0 y te reporto el contrato
de tipos/símbolos/annotations antes de escribir el checker completo.**

---

## 📎 22. Anexos

### A. `SemaTypeKind`

```text
TkAny, TkNull, TkVoid, TkOpaque, TkError,
TkBase, TkRef, TkFrozen,
TkArray, TkSlice, TkMany, TkList, TkMap, TkMaybe, TkResult, TkTuple, TkRange,
TkCVarArgs, TkFn,
TkRune, TkEcho, TkOmen, TkAlias, TkSeal, TkConcept,
TkTypeParam
```

### B. `SemaSymbolKind`

```text
SkVar, SkLet, SkConst, SkParam, SkStaticVar,
SkWeave, SkDeclare, SkType, SkRune, SkEcho, SkOmen, SkAlias, SkSeal,
SkConcept, SkImport, SkCDefine, SkTest
```

### C. Códigos de error

| Rango | Uso |
|---|---|
| `E0000` | parse/lexer (F1/F2) |
| `E0001–E0009` | reglas básicas |
| `E0014–E0015` | builders/arrays |
| `E0021–E0024` | genéricos/many |
| `E0026–E0034` | insignia/omen/conceptos/rituales |
| `E0035–E0039` | nombres C reservados y colisiones de nombres |
| `E0041–E0044` | arrays/range/privacidad/judge |
| `E0047` | método primitivo duplicado |
| `E0050` | tipo recursivo por valor |
| `E0052` | bind/concept duplicado |
| `E0056` | atributo inválido |
| `E0057` | char > 0x7F |
| `E0063–E0070` | static/test/C fields/mutates/type names |
| `E0061–E0062` | lockfile (F6/F9, fuera de F3) |

Catálogo completo y condiciones en `docs/error_catalog.json`;
`SEMA_ERRORS.md` será la tabla viva.

### D. Warnings

| Código | Nombre | F3 |
|---|---|---|
| `W0000` | UncategorizedWarning | fallback |
| `W0001` | UnsafeTransmuteWarning | sí |
| `W0002` | UnsafeEchoAccessWarning | sí |
| `W0003` | reservado | no |
| `W0004` | UnreachableCodeWarning | sí |
| `W0005` | ShadowedGlobalWarning | sí (indentación es F1) |
| `W0006` | DeprecatedSymbolWarning | sí |
| `W0007` | UnsafeBlockWarning | sí |
| `W0013` | RangeSyntaxDeprecated | sí |

### E. Orden de resolución de módulos

```text
1. std.<...> en std_dirs / base_dir/std
2. relativo al importador
3. base_dir/src_dir
4. base_dir/lib_dir/<binding>/pengu y /<binding>
5. base_dir
Candidatos: <p>.pengu, <p>.d.pengu, <p>/__init__.pengu, <p>/__init__.d.pengu
```

### F. Formato de `--dump-sema`

```text
# psc-sema-dump v1
# module: <path>
module <path> ok=<bool>
  type <name> kind=<rune|echo|omen|alias|seal|concept> c_name=<...> fields=<n> methods=<n>
  symbol <name> kind=<...> type=<canonical> c_name=<...> line=<n> col=<n>
  method <receiver>.<name> type=<...>
  const <name> type=<...> value=<...>
  instance <key> kind=<...> receiver=<...> args=<...>
  expr <path> type=<canonical> symbol=<...> flags=<...>
```

- Path = índices de hijos desde `start` (`0.4.2.1`).
- Tipo canónico = `canonical_type_name`.
- Sin posiciones absolutas de CRLF.
- Orden de fuente y listas deterministas.
- `--no-header` para goldens/oráculos.

### G. Comandos de trabajo

```bash
# Build
cd psc
../.venv/bin/python ../pengu_project.py build

# Check
./build/psc check tests/fixtures/basic.pengu
./build/psc check --base-dir . --src-dir src src/main.pengu
./build/psc check --diagnostics=json tests/fixtures/sema_bad.pengu
./build/psc check --dump-sema --no-header std/arena.pengu

# Tests F3
../.venv/bin/python ../pengu_project.py run tests/sema_unit.pengu --no-cache
../.venv/bin/python ../pengu_project.py run tests/sema_corpus.pengu --no-cache
../.venv/bin/python tools/run_f3_checks.py
../.venv/bin/python tools/run_f3_checks.py --update-golden

# Oráculos
../.venv/bin/python psc/tools/sema_oracle.py --psc psc/build/psc --root std tests psc/src
../.venv/bin/python psc/tools/sema_type_oracle.py --psc psc/build/psc --root std tests psc/src

# Fuzz
../.venv/bin/python ../pengu_project.py run tests/fuzz_sema.pengu --no-cache -- 100000

# Benchmark
../.venv/bin/python ../pengu_project.py run tests/bench_sema.pengu \
    --no-cache --profile release

# ASan
PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -g" \
PENGU_LDFLAGS="-fsanitize=address,undefined" \
../.venv/bin/python ../pengu_project.py build
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 ./build/psc check --quiet \
    ../std/arena.pengu
```

### H. Referencias

- [`AUDITORIA_AUTO_HOSPEDAJE.md`](AUDITORIA_AUTO_HOSPEDAJE.md) §5 (B1/B2/B4-B7),
  §7, §9 (F3), §10.
- [`PLAN_F2_PARSER.md`](PLAN_F2_PARSER.md).
- [`psc/docs/AST.md`](psc/docs/AST.md), [`PARITY.md`](psc/docs/PARITY.md),
  [`OWNERSHIP.md`](psc/docs/OWNERSHIP.md).
- [`pengu_parser/pengu_types.py`](pengu_parser/pengu_types.py).
- [`pengu_parser/pengu_symbols.py`](pengu_parser/pengu_symbols.py).
- [`pengu_parser/pengu_checker.py`](pengu_parser/pengu_checker.py).
- [`pengu_parser/pengu_infer.py`](pengu_parser/pengu_infer.py).
- [`pengu_parser/pengu_comptime.py`](pengu_parser/pengu_comptime.py).
- [`pengu_parser/pengu_errors.py`](pengu_parser/pengu_errors.py),
  [`docs/error_catalog.json`](docs/error_catalog.json).
- [`tests/compiler/conftest.py`](tests/compiler/conftest.py).
- [`LANGUAGE.md`](LANGUAGE.md) §4–§18, §22.
- [`std/diagnostic.pengu`](std/diagnostic.pengu).

---

## 🏁 23. Cierre

F3 está implementado con el alcance acordado:

1. contrato `SemaType`/`SemaSymbol`/`SemaAnnotation`/hooks congelado;
2. resolución de módulos, imports, bindings `.d.pengu` y `psc check`;
3. tipos/símbolos construidos antes de comprobar cuerpos;
4. inferencia, genéricos, concepts, `judge`, lambdas, `with`, `do`, `or`,
   compilación condicional y métodos nativos;
5. tests, corpus, CLI/JSON y documentación.

F4 puede consumir las anotaciones por nodo. La única deuda declarada es la
paridad fina de constructos exóticos: `infer` conserva el tipo esperado/`any`
para no encadenar errores; se documenta en `PARITY.md` y se ampliará con
fixtures específicos antes de F4. No se modificó `std/`, la auditoría ni el
compilador Python.

`PLAN_F3_SEMA.md` y los documentos de `psc/docs/` son los artefactos de cierre.
