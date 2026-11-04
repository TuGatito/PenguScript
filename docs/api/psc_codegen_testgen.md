# psc.codegen.testgen

> Source: `src/psc/codegen/testgen.pengu`

psc/codegen/testgen.pengu — sección `--test` de F4.

Emite cada `test "nombre":` como `static void pengu_test_N(void)` y un
`main` que los ejecuta en orden. No usa el runner JSON de stage0; F5 puede
añadir selección por argumentos encima de este contrato estable.

---

### `contains`

> **contains**(s: string, needle: string) -> bool

 `true` si `s` contiene `needle`.

 ## Memoria
 O(n*m).

### `emit_all`

> **emit_all**(c: ref to CgContext) -> int

 Emite todos los tests; devuelve cuántos hay.

 ## Memoria
 Strings temporales liberados.

### `emit_one`

> **emit_one**(c: ref to CgContext, module_id: int, node: int, index: int) -> void

 Emite un test concreto.

 ## Memoria
 Restaura el contexto de la función anterior.

### `emit_main`

> **emit_main**(c: ref to CgContext, count: int, as_json: bool) -> void

 Emite el `main` del modo test.

 ## Memoria
 Strings temporales liberados.

