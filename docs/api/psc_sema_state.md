# psc.sema.state

> Source: `src/psc/sema/state.pengu`

psc/sema/state.pengu — estado compartido del checker y la inferencia.

`SemaState` no posee recursos: presta el módulo cargado, las tablas y el bag.
Los hooks rompen la recursión checker ↔ inferencia sin imports cíclicos.

## Memoria
Todos los campos `ref` son prestados. El dueño es `SemaProgram`/el llamador.

---

### `SemaHooks`

> rune SemaHooks

```pengu
    infer_expr as ref to weave with s: ref to SemaState, node: int, expected: int into int
    check_stmt as ref to weave with s: ref to SemaState, node: int into void
    check_block_value as ref to weave with s: ref to SemaState, node: int, expected: int into int
    check_lambda as ref to weave with s: ref to SemaState, node: int into int
    check_judge as ref to weave with s: ref to SemaState, node: int, expected: int into int
    check_with as ref to weave with s: ref to SemaState, node: int, expected: int into int
```

 Hooks entre checker e inferencia.

 ## Memoria
 Punteros a función; sin heap.

### `SemaState`

> rune SemaState

```pengu
    program as ref to SemaProgram
    module as ref to SemaModule
    src as ref to SourceFile
    lex as ref to LexResult
    ast as ref to PsAst
    types as ref to SemaTypeTable
    symbols as ref to SemaSymbols
    names as ref to NamePool
    bag as ref to DiagnosticBag
    opts as ref to SemaOptions
    annotations as ref to SemaAnnotations
    hooks as SemaHooks
    errors as int
    max_errors as int
    stop_after_first as bool
    stop as bool
    allow_mutating as bool
```

 Estado de un módulo en chequeo.

 ## Memoria
 Sin destructor; todas las referencias son prestadas.

### `_no_infer`

> **_no_infer**(s: ref to SemaState, node: int, expected: int) -> int

 Stub de inferencia.

 ## Memoria
 No asigna.

### `_no_stmt`

> **_no_stmt**(s: ref to SemaState, node: int) -> void

 Stub de statement.

 ## Memoria
 No asigna.

### `_no_block`

> **_no_block**(s: ref to SemaState, node: int, expected: int) -> int

 Stub de bloque.

 ## Memoria
 No asigna.

### `_no_lambda`

> **_no_lambda**(s: ref to SemaState, node: int) -> int

 Stub de lambda.

 ## Memoria
 No asigna.

### `_no_judge`

> **_no_judge**(s: ref to SemaState, node: int, expected: int) -> int

 Stub de judge.

 ## Memoria
 No asigna.

### `_no_with`

> **_no_with**(s: ref to SemaState, node: int, expected: int) -> int

 Stub de with.

 ## Memoria
 No asigna.

### `default_hooks`

> **default_hooks**() -> SemaHooks

 Crea los hooks por defecto.

 ## Memoria
 Valor puro de punteros.

### `install_hooks`

> **install_hooks**(s: ref to SemaState, h: SemaHooks) -> void

 Instala los hooks reales.

 ## Memoria
 Asigna punteros; no tiene heap.

### `should_stop`

> **should_stop**(s: ref to SemaState) -> bool

 `true` si ya hay que parar.

 ## Memoria
 O(1).

### `note_error`

> **note_error**(s: ref to SemaState) -> void

 Marca un error y decide si parar.

 ## Memoria
 O(1).

### `call_infer`

> **call_infer**(s: ref to SemaState, node: int, expected: int) -> int

 Llama al hook de inferencia.

 ## Memoria
 O(1); no asigna.

### `call_stmt`

> **call_stmt**(s: ref to SemaState, node: int) -> void

 Llama al hook de statement.

 ## Memoria
 O(1).

### `call_block`

> **call_block**(s: ref to SemaState, node: int, expected: int) -> int

 Llama al hook de bloque-valor.

 ## Memoria
 O(1).

### `call_lambda`

> **call_lambda**(s: ref to SemaState, node: int) -> int

 Llama al hook de lambda.

 ## Memoria
 O(1).

### `call_judge`

> **call_judge**(s: ref to SemaState, node: int, expected: int) -> int

 Llama al hook de judge.

 ## Memoria
 O(1).

### `call_with`

> **call_with**(s: ref to SemaState, node: int, expected: int) -> int

 Llama al hook de `with:`.

 ## Memoria
 O(1).

