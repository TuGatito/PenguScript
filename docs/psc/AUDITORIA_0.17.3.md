# Auditoría de codegen 0.17.3

| Campo | Valor |
|---|---|
| Fecha | 2026-10-30 |
| Compilador | `psc 0.17.3` (desde `0.17.2`) |
| Ámbito | codegen C, sema, `std.ffi`, ejemplos de `raylib-pengu` |
| Estado | Correcciones aplicadas; bootstrap pendiente de regenerar |

## 1. Resumen

`psc 0.17.2` emitía `(void)(0);` para varios statements y `0` para varias
expresiones que el parser y el sema sí conocían. El programa compilaba y
`psc check` pasaba, pero la operación desaparecía en tiempo de ejecución. Los
ejemplos de cámara/plataformas/FPS de `raylib-pengu` abrían la ventana y no
movían nada; `std` perdía asignaciones compuestas y retornos implícitos.

La causa no era `std.ffi`, ni raylib, ni los ejemplos: era el *fallback* de
`emit_stmt`/`emit_expr` para nodos sin rama.

## 2. Evidencia

### 2.1 Asignación compuesta

Fuente:

```pengu
var n as int is 1
set n += 2
var total as int is n
return total
```

C de 0.17.2:

```c
int32_t n = 1;
(void)(0);          /* set n += 2; */
int32_t total = n;  /* 1, no 3 */
```

C corregido:

```c
int32_t n = 1;
n += 2;
int32_t total = n;
```

La correlación era 1:1: **110 líneas compuestas en 29 archivos de
`raylib-pengu`** producían 110 `(void)(0)`. En `core_3d_camera_split_screen`
eran 8; en `core_2d_camera_platformer`, 7; en `core_3d_camera_fps`, 12.

### 2.2 Prueba de runtime

Sonda con dos teclas y dos formas de asignación (eventos XTEST reales):

```pengu
if calling input.is_key_down with raylib.KEY_RIGHT:
    set right_frames += 1          # compuesta
if calling input.is_key_down with raylib.KEY_LEFT:
    set left_frames is left_frames + 1   # simple
```

Con 0.17.2:

```text
right_frames=0 left_frames=1
right_frames=0 left_frames=2
...
```

Con el codegen corregido, ambas avanzan. La ventana, `IsKeyDown`, el foco y el
bucle de eventos funcionaban; solo se perdía la asignación.

### 2.3 `std` y retorno implícito

`std/tally.pengu` producía el warning `control reaches end of non-void
function`: una función terminada en expresión (`acc`) emitía `(void)(acc);` en
vez de `return acc;`. El retorno implícito ya se emite.

## 3. Correcciones

| Nodo / caso | Antes | Ahora |
|---|---|---|
| `NdCompoundSetStmt` | `(void)(0);` | `<target> <op> <value>;` |
| `NdSimpleStmt` | `(void)(0);` | expresión-statement |
| `NdWithStmt` | `(void)(0);` | bloque + pila de targets |
| `NdUnsafeStmt` | `(void)(0);` | bloque + `unsafe_depth` |
| `NdErrdeferStmt` | nunca se ejecuta | ruta de error |
| retorno implícito | `(void)(expr);` | `return expr;` |
| `{expr}` interpolación | solo identificadores | AST del sema, expresiones arbitrarias |
| `NdForComp` | `0` | `PenguList` con bucle |
| `NdInExpr`/`NdNotInExpr` | `0` | list/map/string/range/array |
| `NdTypeOf` | `0` | nombre canónico |
| `NdDonumExpr` | `0` | cero del tipo |
| `NdOrReturn`/`NdTryExpr` | `0` | unwrap + fallback/propagación |
| `NdOrBlock` | `0` | unwrap + bloque de error |
| `at` fuera de rango | desreferencia NULL | `pengu_assert_bounds` |
| `map at` ausente | desreferencia NULL | cero del tipo de valor |

Además:

- `check_set` usa el slot 2 (valor) en nodos compuestos, no el slot 1 (token
  del operador), y valida el tipo.
- `SemaModule.interps` conserva AST y anotaciones de interpolación.
- `std.ffi.cstr_from_string` y `string_from_cstr` usan `ref to frozen char`.
- `unsafe:` desactiva los bounds checks; `--release-unsafe` los desactiva
  globalmente.

## 4. Pruebas recomendadas

1. `set x += 2`, `set p.x -= 3`, `set q->y *= 4`, `set arr at i += 5`:
   `psc emit-c` debe contener el operador y no `(void)(0)`.
2. `compound.pengu` con `1 + 10 + 5` debe devolver 19, no 16.
3. `int += "texto"` debe fallar con `E0005`.
4. `at` fuera de rango debe abortar con código 134 y el mensaje
   `[PENGU] Index out of bounds`.
5. `map at` con clave ausente debe devolver el cero del tipo.
6. `for x in xs when cond then expr` debe devolver la lista filtrada.
7. `or return`/`try`/`or:` deben propagar `none`/`error` y ejecutar
   `errdefer`.
8. Repetir el smoke de teclado de §2.2 y los 226 ejemplos de `raylib-pengu`.

## 5. Bootstrap

El `bootstrap/psc_stage0_*.c` se regeneró con `psc 0.17.3` y se validó:

```bash
PSC=build/psc-dev4 ./tools/gen_stage0.sh
./tools/build_bootstrap.sh
./build/psc-stage0 build src/main.pengu --out=build/psc-from-stage0
```

`psc-stage0` y `psc-from-stage0` son 0.17.3, compilan los 226 ejemplos y se
autohospedan. La cadena de arranque queda cerrada.

## 6. Limitaciones conocidas

- `or:`/`try` y `or return` están resueltos para inicializadores locales y para
  `return`; las posiciones de expresión más exóticas pueden seguir usando el
  camino de statement-expression sin `errdefer`.
- La interpolación de una expresión de tipo `string` que no es un identificador
  evalúa la expresión dos veces (`.len` y `.data`). Es correcta si la expresión
  es pura; conviene introducir un temporal en una revisión posterior.
- La interpolación de varios segmentos dentro de bloques anidados de `std` puede
  no encontrar su AST guardado; hay fallback para identificadores y caminos
  `a.b`/`self->x`, y `std.compass.cp_join` se reescribió con `StringBuilder`.
  Las expresiones complejas que no encuentran AST siguen emitiendo vacío.
- `when` como expresión y `judge … over` no tienen codegen dedicado; el código
  actual de `std` no los usa en rutas críticas.
- `unsafe:` desactiva bounds checks, no los checks de overflow aritmético
  (esos no se emiten en 0.17.x).
