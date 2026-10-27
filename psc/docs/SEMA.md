# SEMA — tipos, símbolos, checker e inferencia (F3)

`psc/sema` es el corazón semántico de PSC. Convierte el AST de F2 en un modelo
estable para F4: `TypeId`s internados, símbolos, scopes, anotaciones por nodo y
diagnósticos con spans de byte.

## Pipeline

```
SemaOptions
  └─ SemaProgram            (modules/program.pengu)
       ├─ resolve imports  (modules/resolver.pengu)
       ├─ load modules     (modules/loader.pengu)
       ├─ module scopes    (symbols/table.pengu)
       ├─ collect decls    (check/collect.pengu)
       │    ├─ tipos/rune/echo/omen/alias/seal/concept
       │    ├─ consts, weaves, declaraciones C y links
       │    └─ imports, `when` top-level activo, tests
       └─ check bodies     (check/body.pengu + infer/core.pengu)
            ├─ statements, control, ownership
            ├─ expresiones y métodos
            └─ SemaAnnotations
```

`SemaState` (`state.pengu`) es el contexto de una pasada: programa, módulo,
fuente, lexer, AST, tablas, diagnósticos y hooks. Los hooks desacoplan
`infer`/`body` para que `sema/types` no importe el checker.

## Tipos

`SemaType` es POD y vive en una tabla plana:

| Servicio | Archivo |
|---|---|
| `SemaType`, `SemaTypeKind`, nombres | `types/kind.pengu` |
| Tabla, interning, nominales, campos, variantes, firmas | `types/table.pengu` |
| Nombres canónicos/mangled | `types/canonical.pengu` |
| Compatibilidad, casts, elementos, punteros | `types/compat.pengu` |
| Conversión AST→tipo | `types/convert.pengu` |

Propiedades del contrato:

- Todo tipo es un `TypeId` (`>0`); `0` reservado para error/ausente.
- El interning es estructural y **propietario** de las claves del map.
- Los singletons (`void`, `opaque`, `any`, `null`) y las bases (`int`, `i64`,
  `u8`, `usize`, `float`, `f64`, `bool`, `string`, `char`, …) se crean en
  `new_table` y se reutilizan siempre.
- `u8` se muestra como `byte`; `usize` como `size_t`.
- `SemaType` guarda dos payloads enteros (`a`, `b`), flags y `name`; los
  nominales y las firmas se indexan en tablas laterales con `first/count`.

Los tipos de dominio usan prefijo `Sema` (`SemaType`, `SemaSymbol`,
`SemaAnnotation`) para no colisionar con los de F1/F2. Las funciones usan
nombres legibles y cada módulo declara `insignia`.

## Símbolos y scopes

`SemaSymbol` (`symbols/symbol.pengu`) es POD:

```
name, type, kind, flags, c_name, module, line, col,
attrs_node, doc, const_id, bounds, module_scope
```

`SemaSymbols` (`symbols/table.pengu`) contiene:

- `symbols` y `scopes` planos; el scope `0` es el global de builtins.
- registros de runas, ecos, omens, aliases, seals, concepts, funciones, consts,
  métodos, métodos mutantes y plantillas genéricas;
- valores de const, tipos por módulo, includes/links/ldflags, imports y orden
  topológico.

Reglas:

- Los scopes léxicos encadenan `parent`; `define/lookup/lookup_local` operan por
  `NameId`.
- Los métodos **no** se enlazan al scope (evitan sombrear funciones); viven en
  `methods` con clave `(receiver, method)`.
- Los métodos de receptores `shard T` tienen un fallback `generic_methods` por
  nombre, usado sólo cuando no hay método exacto para el receptor concreto.
- `@mutates` registra además `get_<nombre>` (forma pura). Nunca sobrescribe un
  `get_*` explícito.
- Un import es un `SkImport` con `module_scope`; permite resolver miembros
  cualificados (`spark.println`, `types.NIF_*`, `web.IS_WASM`).
- El lookup cae al registro global de funciones/consts para respetar el
  comportamiento de stage0 y los helpers de proyecto.
- Los nombres de tipos/omens también funcionan como namespace de variantes
  (`NodeKind.NdError`, `CipherJsonValue.JvBool`).

### Módulos

- `resolver.find_module` busca `std.dirs`, dir del importador, `base/src_dir`,
  `lib_dir/<binding>/pengu` y `base`; prueba `.pengu`, `.d.pengu`,
  `__init__.pengu`, `__init__.d.pengu`.
- `program.discover` hace DFS, detecta ciclos y carga el **binding companion**
  `<modulo>.d.pengu` junto al módulo. Las declaraciones del companion se
  recolectan en el scope del módulo padre (ABI C, includes, declare).
- `when wasm:` / `when not wasm:` top-level se evalúa con `SemaOptions`
  (`wasm_target`, defines, `is_main`, `is_debug`). Sólo se recolecta la rama
  activa.

## Checker

`collect.pengu` hace dos pasadas:

1. **predeclare_types**: registra nombres de runas/omens/aliases/seals/concepts
   antes de convertir campos y firmas (referencias adelantadas, recursión).
2. **collect_module**: declara tipos, campos, variantes, consts, funciones,
   métodos, imports, links y tests. No comprueba cuerpos.

`body.pengu` comprueba después:

- `weave`, `enchanting` y `test` (todos los statements, no sólo el último);
- `let/var/static var`, `set`, `return`, `if/unless/while/for`, `with`,
  `judge`, `defer`, `break/continue`;
- bindings de `if x as T is expr`, `for`, payloads de `judge` y parámetros de
  lambda/defer.

Los targets aplican los accesos (`at`, `arrow`, `essence`) antes de comparar el
tipo. La asignación a través de un puntero (`set p at i`) es válida aunque el
binding sea `let`: se escribe en el pointee, no se reasigna el binding.

`self` es un valor en receptores primitivos/`shard` y un `ref` en runes/ecos;
asignar al `self` valor o usar `self->field` sobre un primitivo emite `E0006` /
`E0003`. Las etiquetas de loop se registran en el scope del loop; `break`/
`continue` con label inexistente son `E0004`, fuera de loop `E0007`, labels
duplicados `E0069`. Las lambdas abren un scope que corta labels/loops externos.
`@mutates` sólo se acepta en métodos, sin argumentos, con retorno `void` o el
receptor; usarlo como expresión emite `E0066`.

`set`/`let` respetan `SYM_MUTABLE`; los parámetros son mutables. `let` con
destructuring de tuplas (`let (q, r) is f()`) define cada nombre con el tipo del
elemento correspondiente.

## Inferencia

`infer/core.pengu` cubre:

- literales, `var_ref`, `self`, paréntesis, `some/none`, `donum`, `defined`;
- llamadas directas, cualificadas, métodos, tipos rituales (`StringBuilder.new`)
  y `with` (`.method`);
- campos, flechas, `at`, slices, `length`, casts `to`, listas/mapas/arrays,
  struct-init, comparaciones, aritmética, bits, unario, rangos, punteros;
- `size of`, `type of`, `bytes of`, `chr`, `ord`;
- `judge` (incluye payloads tipados desde el omen), `lambda`, `do`, `with`,
  `or`, `try`, `if/when` como expresión, `for ... then`.

Los métodos nativos de contenedores (`list`, `map`, `array`, `slice`, `string`,
`maybe`, `result`) están modelados en `builtin_method`. Los C `declare` no se
re-validan por ABI: su firma la define el binding.

### Genéricos y conceptos

- `shard T` crea `TypeParam` estables por `NameId` (`type_param_type` cachea).
- `where T: Concepto` registra bounds en `types.bounds` y en el símbolo de la
  función/método. Los conceptos integrados (`Num`, `Integrum`, `Real`, `Par`,
  `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Iterabilis`, `Donum`) se
  registran como tipos nominales en `init_builtins`.
- Al llamar a una función/método genérico se comprueba que el tipo concreto
  satisfaga sus bounds (`concept_satisfied`); si no, `E0032` en funciones y
  `E0004` en métodos no disponibles.
- Dentro del cuerpo, `bound_operator_ok` concede operadores según el concepto:
  `Num` aritmética, `Integrum` módulo/bits/orden, `Real` aritmética flotante y
  orden, `Par` igualdad, `Ordo` orden. Un operador no concedido es `E0049`.
- `bind Tipo with Concepto` valida que cada método exista en el concepto y
  registra la implementación por receptor.
- `derive Nexus/Par/Ordo` se guarda en `derived`; `derive Real` se rechaza con
  `E0005`. `banish` exige un rune/echo con `derive Nexus` (`E0008`).
- Los métodos de `shard T` se resuelven por fallback genérico; los de un
  receptor concreto (`Vec4`, `f64`, …) exigen coincidencia exacta. `f32` cae a
  `float` e `i32` a `int` sólo cuando no hay método exacto.

## Diagnósticos

`sema/diagnostics.pengu` expone los códigos `E0000`–`E0070` y `W*`, y helpers
`emit_error/emit_warning/node_error/node_warning` con span de byte, help y note.
El render lo hace `std.diagnostic` (plain/ANSI/JSON).

Códigos usados por el checker F3:

| Código | Uso |
|---|---|
| `E0000` | error de parseo propagado por F2 |
| `E0004` | identificador/función/tipo/miembro/import no resuelto |
| `E0005` | tipo incompatible, expresión/target inválido |
| `E0006` | asignación a binding inmutable |
| `E0013` | campo inexistente |
| `E0020` | retorno incompatible |
| `E0022` | parámetro de tipo fuera de un `shard` |

## Anotaciones (contrato F4)

`SemaAnnotations` indexa por **id de nodo AST**:

- `type` (`TypeId`), `symbol` (`SymbolId`), `aux` (índice auxiliar);
- flags `ANN_*` (const plegada, lvalue, mutante, builtin, …).

F4 puede leer tipos y símbolos sin repetir resolución. La API pública está en
`sema/api.pengu` (`check_file`, `check_text`, `free_result`).

## CLI

```
psc check [--stdin] [--diagnostics=plain|ansi|json] [--no-color]
          [--max-errors=N] [--stop-after-first] [--deny-deprecated]
          [--base-dir=DIR] [--src-dir=DIR] [--lib-dir=DIR] FILE
```

`psc check` devuelve `0` sin errores y `1` con diagnósticos. El `SemaResult`
contiene el programa; `free_result` libera tipos, símbolos, módulos y nombres.

## Verificación

- `tests/psc/test_f3_acceptance.py`: smokes, corpus curado, CLI/JSON, códigos
  `E0004/E0005/E0006` y, con `PSC_F3_FULL=1`, el corpus completo.
- `psc/tools/lark_sema_oracle.py`: 193 casos literales de `tests/compiler`;
  mide aceptación y primer código contra stage0. Resultado actual:
  `valid=140 valid_rejected=0 invalid=53 invalid_accepted=0 same_code=53`.
  Los 193 casos coinciden en aceptación y primer código; se documenta en
  `PARITY.md`.
- ASan/UBSan (`detect_leaks=1`): limpio sobre `main`, `oracle`, `petitio`,
  `cipher`, `arithmancy` y fixtures de `judge`.
- `psc/tests/bench_sema.pengu`: 2 000 funciones / 262 890 B en 78 ms Release
  (~25 600 funcs/s).
- `psc/tests/sema_smoke.pengu`: tabla/interning/canonical/compat.
- `psc/tests/sema_api_smoke.pengu`: `check_text` válido/inválido.
- `psc/tests/sema_check_smoke.pengu`: collect + bodies + bad return.
- `psc/tests/flag.pengu`: constante importada y operador bit a bit.
