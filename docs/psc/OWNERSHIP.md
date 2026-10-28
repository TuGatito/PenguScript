# Ownership de PSC (F1 + F2 + F3)

## Reglas

1. **`SourceFile`** es dueño de `path`, `text`, `line_starts` y `sha256`;
   `banish file` los libera.
2. **`LexResult`** es dueño de sus seis listas (`tokens`, `comments`, `strings`,
   `parts`, `chars`, `antiquus`). Todos los elementos son POD; `banish result`
   libera las listas, no hay liberación recursiva.
3. **`Session`** es dueño de `source`, `diagnostics`, `keywords` y `options`.
4. **`DiagnosticBag`** es dueño de sus diagnósticos y de las copias de fuentes.
5. **`KeywordTable`** es dueño de `entries`; las palabras son literales
   estáticos (`is_owned = 0`) y no se liberan.
6. **`PsAst`** es dueño de `nodes`, `children` y `labels`; `banish ast` libera
   las tres listas. Los `PsNode` y `PsLoopLabel` son POD.
7. **`PsParseResult`** es dueño de su `PsAst`; `banish result` libera el AST.
   **No** libera `SourceFile` ni `LexResult`.
8. **El AST presta** `SourceFile` y `LexResult`: el llamador debe mantenerlos
   vivos mientras use `PsParseResult`. Los hijos del AST son índices a tokens,
   no copias.
9. **`PsParser`** presta `SourceFile`, `DiagnosticBag` y `LexResult`. Es dueño
   del `PsAst` (que transfiere al resultado) y de las listas de trabajo
   `child_stack`/`marks` (que libera `free_scratch`).
10. **`InterpParseResult`** es el único bundle que posee `SourceFile`,
    `LexResult`, `DiagnosticBag` y `PsAst`, porque una expresión de
    interpolación no tiene un `Session` detrás. `banish bundle` lo libera todo.
11. Las funciones `decode_*` devuelven `string` owned; el llamador hace
    `banish`.
12. Los parámetros `string`/`ref to` son prestados; la función no los libera.
13. Nunca se pasa una interpolación directa a una función que no la consume:
    se bindea y se libera con `defer banish`.
14. No hay `banish` por token ni por nodo. El AST no libera tokens.
15. Los mensajes temporales de error se liberan con `defer banish` tras
    `emit`.
16. El `StringBuilder` del dump se libera con `defer banish`; los textos de
    tokens se liberan tras escribirlos.
17. **`SemaProgram`** se asigna en heap (`memoria.alloc`) porque los `ref to`
    de la tabla de tipos y símbolos deben quedar estables; `free_program` lo
    libera y `SemaResult.program` es un `ref` prestado hasta `free_result`.
18. **`NamePool`** es dueño de los buffers de sus strings internados y de las
    claves `ids`; `intern` copia el texto (`pengu_string_copy`). Los
    `intern_keys` de la tabla de tipos también poseen sus buffers.
19. **`SemaTypeTable`** es dueña de `types`, `type_children` y de las tablas
    laterales (nominales, firmas, campos, variantes, parámetros, bounds,
    derivados, concept_methods, fn_params, tparam_cache, intern_keys).
20. **`SemaSymbols`** es dueño de `symbols`, `scopes`, registros, métodos,
    plantillas, valores const y mapas de módulo. Los strings de `c_name` y
    nombres son `NameId`, no buffers.
21. **`SemaModule`** es dueño de `path` (copia), `source`, `lex`, `parse` y
    `annotations`; `free_module` los libera. El texto fuente se copia porque el
    parser puede sobrevivir al `maybe string` del loader.
22. **`SemaAnnotations`** es dueña de `items`; `free_annotations` la libera.
    Las anotaciones son POD (`SemaAnnotation`).
23. Los `when`/`for`/`judge`/lambda abren y cierran scope; los strings
    temporales de tokens se liberan con `defer banish`.
24. Las firmas y campos son POD; ninguna lista de `SemaType`/`SemaSymbol`
    libera recursivamente strings.
25. **Todo `string` con posesión es SDS** (`is_owned == 1`): `data` apunta a
    una reserva de `std_c/sds` y solo puede liberarse con `sdsfree`. Los
    productores usan `pengu_string_owned`, `pengu_string_owned_size`,
    `pengu_string_owned_from_sds` o `pengu_string_owned_from_sds_len`; nunca
    `malloc` seguido de `is_owned = 1`.
26. **Los contenedores usan CC**: `PenguList.data` apunta al payload de un
    `cc_vec` (la cabecera CC vive antes); `PenguMap.state` es un estado opaco
    con el handle `cc_map`. No se libera `data`/`state` con `free` ni se
    recorren las entradas del mapa a mano; usar las funciones del runtime.
27. **`is_owned == 2` es un bloque crudo opaco** que no es SDS y se libera con
    `free`. Solo lo usan `std/arena.pengu` (alineación de `max_align_t`) y
    `std/regulus.pengu` (puntero compilado de la librería `re`).

## Tabla

| Recurso | Dueño | Liberación |
|---|---|---|
| `SourceFile.text` | `SourceFile` | `banish file` |
| `SourceFile.line_starts` | `SourceFile` | `banish file` |
| `SourceFile.sha256` | `SourceFile` | `banish file` |
| `LexResult.*` | `LexResult` | `banish result` |
| `StringInfo`/`StringPart`/`CharInfo`/`AntiquusInfo` | `LexResult` | `banish result` (POD) |
| `DiagnosticBag.items/_sources` | `DiagnosticBag` | `banish bag` |
| `KeywordTable.entries` | `KeywordTable` | `banish table` |
| `PsAst.nodes/children/labels` | `PsParseResult` / llamador | `banish result` |
| `PsParser.child_stack/marks` | `PsParser` | `ps_free_scratch` |
| `InterpParseResult.*` | `InterpParseResult` | `banish result` |
| `PenguString.data` (`is_owned == 1`) | productor del string | `banish` (`sdsfree`) |
| `PenguString.data` (`is_owned == 2`) | productor del bloque opaco | `banish` (`free`) |
| `decode_*` / `ps_ast_token_text` | llamador | `banish` |
| `SourceFile.slice/line_text` | llamador | `banish` |
| Mensajes de `parse_issue_message` | llamador | `banish` tras `emit` |
| `SemaProgram` | programa | `free_program`/`free_result` |
| `NamePool.strings/ids` | `NamePool` | `free_pool` |
| `SemaTypeTable.*` | tabla | `free_table` |
| `SemaSymbols.*` | símbolos | `free_symbols` |
| `SemaModule.path/source/lex/parse/annotations` | módulo | `free_module` |
| `SemaAnnotations.items` | anotaciones | `free_annotations` |
| `SemaResult.program` | resultado | `free_result` |

## Comprobaciones

```bash
cd psc
PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -g" \
PENGU_LDFLAGS="-fsanitize=address,undefined" \
../.venv/bin/python ../pengu_project.py build
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 ./build/psc parse --quiet --check \
    ../tests/conformance/compliance/arena_ast.pengu
```

Estado medido en F2:

- `psc parse --check` sobre 205 archivos (src + std + tests): ASan/UBSan limpio.
- `parser_unit.pengu` y `parser_corpus.pengu`: verdes.
- Fuzz del parser bajo ASan (20 000): sin fugas ni UB.
- El oráculo AST no detecta nodos huérfanos porque el dump recorre desde la
  raíz; el AST sigue siendo determinista.

Estado medido en F3:

- `psc check` sobre 226 archivos (`std` + `tests` + `psc/src`): 225 válidos aceptados; el fixture negativo `coherence_conflict` se rechaza con E0047.
- `tests/psc/test_f3_acceptance.py`: 17 passed.
- `sema_smoke`, `sema_api_smoke` y `sema_check_smoke`: verdes.
- ASan/UBSan con `detect_leaks=1`: limpio en `main`, `oracle`, `petitio`,
  `cipher`, `arithmancy` y fixtures de `judge`.
- Se corrigió un doble free en `discover` (el `pop` de la pila de ciclos
  devuelve un string prestado; no se libera), la copia de texto del loader, el
  buffer crudo de `SourceFile` en `SemaModule`, `tparam_cache` y los `string at`
  de resolver/collect/convert/symbols.
- Benchmark Release: 2 000 funciones / 262 890 B en 78 ms (~25 600 funcs/s).
