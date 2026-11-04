# std.memoria

> Source: `std/memoria.pengu`

std/memoria.pengu — manual heap memory management.

`memoria` expone las primitivas canónicas para reservar, redimensionar,
copiar y manipular bloques de memoria del heap en PenguScript. Cada método se
declara `shard T`, así que se monomorfiza por tipo concreto en tiempo de
compilación: no hay boxing, ni vtables, ni sobrecoste en runtime. `alloc of
int` y `alloc of Player` son dos funciones C distintas, cada una con su
`sizeof` ya resuelto.

## Lo que **no** está aquí
`memoria` **no** expone `free`, `sizeof` ni `address_of`: esos ya viven en
el lenguaje y duplicarlos sería anti-Pengunic. La forma canónica de cada
concepto es:

| Concepto | Forma canónica |
|---|---|
| Liberar | `banish p` / `defer banish p` / `errdefer banish p` |
| Tamaño | `size of T` (operador) |
| Dirección | `sigil of x` (operador) |
| Desreferencia | `essence of p` (operador) |
| Destructor de rune | `derive Nexus` + `banish (essence of p)` |

## Zeroed por defecto
`alloc` y `alloc_array` devuelven memoria **puesta a cero**. No existe
`alloc_uninit`: un bloque sin inicializar es una deuda de seguridad, no una
primitiva de biblioteca. Si de verdad necesitas uno (rendimiento medido,
código de arranque), declara un bloque `antiquus` con
`#include <stdlib.h>` y llama a `malloc` directamente, documentando el
motivo en el punto de uso. La biblioteca estándar no esconderá esa deuda por
ti.

## OOM: aborta por defecto, `maybe` con `try_*`
Si el sistema se queda sin memoria, `alloc`, `alloc_array` y `resize_array`
abortan con `[PENGU] out of memory` (la política `PENGU_OOM_ABORT` del
runtime, ver LANGUAGE.md §5.0). Si prefieres manejar el fallo, usa
`try_alloc`, `try_alloc_array` o `try_resize_array`, que devuelven
`maybe none` en lugar de abortar. En `try_resize_array`, un fallo deja el
bloque original **válido y en propiedad del llamador**.

## Composición con el lenguaje
La pareja canónica es `memoria.alloc of T` + `banish`:

```pengu
import std.memoria

rune Player:
    hp as int

weave main into int:
    var p as ref to Player is calling memoria.alloc of Player
    defer banish p
    set p->hp is 100
    return 0
```

Para runes con `derive Nexus`, `banish p` libera el bloque pero **no**
invoca el destructor: llama a `banish (essence of p)` antes de `banish p`,
o envuelve la liberación en un helper.

## Memoria
**Todos** los métodos de este módulo devuelven punteros que el llamador debe
liberar con `banish`. No hay gestión automática: el heap manual es manual.

## Ejemplo: buffer dinámico
```pengu
import std.memoria

weave main into int:
    var cap as usize is 8
    var buf as ref to int is calling memoria.alloc_array of int with cap
    defer banish buf
    calling memoria.fill of int with buf, 42, cap
    set buf is calling memoria.resize_array of int with buf, cap, 16
    set cap is 16
    return 0
```

`defer banish buf` nombra la **variable**, así que libera el puntero
vigente al salir del scope (el que devolvió `resize_array`), no una copia
del valor inicial. No hay doble `banish`.

---

### `MEMORIA_VERSION`

> **MEMORIA_VERSION** : string

 Memoria module version.

### `pengu_memoria_alloc`

> **pengu_memoria_alloc**(n: usize) -> ref to void

 Reserva `n` bytes a cero; aborta según `PENGU_OOM_ABORT`.

### `pengu_memoria_alloc_array`

> **pengu_memoria_alloc_array**(count: usize, elem_size: usize) -> ref to void

 Reserva `count` elementos de `elem_size` bytes a cero; aborta según OOM.

### `pengu_memoria_try_alloc`

> **pengu_memoria_try_alloc**(n: usize) -> ref to void

 Como `pengu_memoria_alloc` pero devuelve NULL en OOM.

### `pengu_memoria_try_alloc_array`

> **pengu_memoria_try_alloc_array**(count: usize, elem_size: usize) -> ref to void

 Como `pengu_memoria_alloc_array` pero devuelve NULL en OOM.

### `pengu_memoria_resize`

> **pengu_memoria_resize**(p: ref to void, old_n: usize, new_n: usize, elem_size: usize) -> ref to void

 Redimensiona preservando `min(old_n, new_n)`; la cola nueva va a cero.

### `pengu_memoria_try_resize`

> **pengu_memoria_try_resize**(p: ref to void, old_n: usize, new_n: usize, elem_size: usize) -> ref to void

 Como `pengu_memoria_resize` pero devuelve NULL en OOM dejando `p` válido.

### `pengu_memoria_swap`

> **pengu_memoria_swap**(a: ref to void, b: ref to void, elem_size: usize) -> void

 Intercambio byte a byte de `elem_size` bytes.

### `pengu_memoria_fill`

> **pengu_memoria_fill**(dst: ref to void, value: ref to frozen void, count: usize, elem_size: usize) -> void

 Relleno de `count` elementos con el patrón de `elem_size` bytes en `value`.

### `memmove`

> **memmove**(dst: ref to void, src: ref to frozen void, n: usize) -> void

 `memmove` de <string.h>: copia sin solapar ya soportado.

### `memset`

> **memset**(dst: ref to void, value: int, n: usize) -> void

 `memset` de <string.h>: relleno de bytes.

### `memcmp`

> **memcmp**(a: ref to frozen void, b: ref to frozen void, n: usize) -> int

 `memcmp` de <string.h>: comparación de bytes.

### `alloc`

> **alloc**() -> ref to T

 Reserva un valor de tipo `T` en el heap, **inicializado a cero**.

 ## Memoria
 El llamador debe liberar el resultado con `banish` (o `defer banish`).

 ## Ejemplo
 ```pengu
 var p as ref to Player is calling memoria.alloc of Player
 defer banish p
 ```

### `alloc_array`

> **alloc_array**(n: usize) -> ref to T

 Reserva un array de `n` elementos de tipo `T`, **inicializado a cero**.

 ## Precondiciones
 `n > 0`. Con `n == 0` el comportamiento es el de `calloc(1, 0)`, que la
 norma C deja a discreción de la implementación (NULL o un bloque mínimo);
 no lo uses como caso normal.

 ## Memoria
 El llamador debe liberar el resultado con `banish`.

 ## Ejemplo
 ```pengu
 var buf as ref to int is calling memoria.alloc_array of int with 100
 defer banish buf
 ```

### `try_alloc`

> **try_alloc**() -> maybe ref to T

 Como `alloc`, pero devuelve `maybe none` en caso de OOM en lugar de abortar.

 ## Memoria
 Hacen falta **dos** liberaciones, porque un `maybe ref to T` no es dueño del
 bloque apuntado: la caja contiene una copia del puntero, no su propiedad.
 1. `banish p` libera el bloque que devolvió el runtime;
 2. `banish mp` libera la caja del `maybe`.

 ## Ejemplo
 ```pengu
 var mp as maybe ref to int is calling memoria.try_alloc of int
 if p as ref to int is mp:
     set essence of p is 1
     banish p
 banish mp
 ```

### `try_alloc_array`

> **try_alloc_array**(n: usize) -> maybe ref to T

 Como `alloc_array`, pero devuelve `maybe none` en caso de OOM.

 ## Memoria
 Como en `try_alloc`: `banish p` libera el bloque y `banish mp` la caja.

### `resize_array`

> **resize_array**(p: ref to T, old_n: usize, new_n: usize) -> ref to T

 Redimensiona un bloque previamente asignado con `alloc_array`/`resize_array`.

 ## Por qué pide `old_n`
 `realloc` de C no sabe cuántos elementos hay dentro del bloque. El llamador
 tiene que saberlo igualmente, y olvidarlo es un bug silencioso que corrompe
 la cola nueva. Al pedir `old_n` el contrato queda explícito y el runtime
 puede preservar exactamente `min(old_n, new_n)` elementos y poner a cero el
 resto.

 ## Semántica
 - `new_n > old_n`: crece; contenido preservado, cola **zeroed**.
 - `new_n < old_n`: encoge; primeros `new_n` elementos preservados.
 - `new_n == old_n`: no-op; devuelve `p` **sin** liberarlo.
 - `p == null`: equivale a `alloc_array of T with new_n`.
 - `new_n == 0`: no soportado (igual que `realloc(p, 0)` en C: indefinido).

 ## Precondiciones
 `p` debe provenir de `alloc_array`/`resize_array` sobre el mismo `T`, y
 `old_n` debe ser el tamaño **actual** del bloque.

 ## Memoria
 ⚠️ Tras una llamada con éxito, el puntero antiguo **queda inválido**: usa
 solo el retorno. `realloc` libera el bloque viejo si tiene que moverlo, y si
 no lo mueve el retorno es el mismo puntero. En ambos casos el patrón seguro
 es reasignar la misma variable y dejar que `defer banish` la lea al salir:
 ```pengu
 var buf as ref to byte is calling memoria.alloc_array of byte with 8
 defer banish buf
 set buf is calling memoria.resize_array of byte with buf, 8, 16
 # 'buf' ya apunta al bloque nuevo; el defer libera ESE puntero.
 ```

### `try_resize_array`

> **try_resize_array**(p: ref to T, old_n: usize, new_n: usize) -> maybe ref to T

 Como `resize_array`, pero devuelve `maybe none` en caso de OOM.

 ## Memoria
 Si el resultado es `maybe none` y `p` era no nulo, el bloque original sigue
 siendo válido y propiedad del llamador. Si es `some np`, el bloque viejo
 queda inválido: libera el bloque con `banish np` y la caja con `banish mp`.

### `copy`

> **copy**(dst: ref to T, src: ref to frozen T, n: usize) -> void

 Copia `n` elementos de tipo `T` desde `src` a `dst`.

 ## Seguridad
 Usa `memmove` internamente: es seguro aunque los bloques se solapen. El
 coste extra frente a `memcpy` es despreciable (glibc detecta la ausencia de
 solape). `src` es `ref to frozen T`: `copy` nunca escribe en el origen.

 ## Precondiciones
 `dst` y `src` deben apuntar a bloques de al menos `n * (size of T)` bytes.

 ## Ejemplo
 ```pengu
 calling memoria.copy of int with dst, src, 4
 ```

### `fill`

> **fill**(dst: ref to T, value: T, n: usize) -> void

 Rellena `n` elementos de `dst` con el valor `value`.

 A diferencia de `zero`, el patrón no tiene por qué ser cero (un `int`, un
 `float`, un puntero…). Se copia el patrón byte a byte, elemento a elemento.

 ## Ejemplo
 ```pengu
 calling memoria.fill of int with buf, 0, 100      # equivalente a zero
 calling memoria.fill of int with buf, -1, 100
 calling memoria.fill of float with buf, 1.5, 50
 ```

### `zero`

> **zero**(dst: ref to T, n: usize) -> void

 Pone a cero `n` elementos de tipo `T` en `dst`.

 ## Por qué está separado de `fill`
 Resetear un buffer es el patrón más común, y `memset` es más rápido que un
 bucle de `fill` que copia un patrón de varios bytes.

 ## Ejemplo
 ```pengu
 calling memoria.zero of int with buf, 16
 ```

### `swap`

> **swap**(a: ref to T, b: ref to T) -> void

 Intercambia los valores apuntados por `a` y `b` (byte a byte).

 ## Ejemplo
 ```pengu
 var x as int is 1
 var y as int is 2
 calling memoria.swap of int with (sigil of x), (sigil of y)
 # x == 2, y == 1
 ```

### `compare`

> **compare**(a: ref to T, b: ref to T, n: usize) -> int

 Compara byte a byte `n` elementos de tipo `T` en `a` y `b`.

 ## Retorno
 - `-1` si `a` es menor (el primer byte distinto es menor en `a`),
 - `0` si son iguales,
 - `1` si `a` es mayor.

 ## Nota
 Es una comparación de bytes **sin signo**, como `memcmp`. No respeta el
 orden lógico del tipo (para eso usa los métodos de `Ordo` sobre valores).

 ## Ejemplo
 ```pengu
 var n as int is calling memoria.compare of byte with a, b, 8
 if n < 0: ... # a < b
 ```

### `bytes_for`

> **bytes_for**(n: usize) -> usize

 Devuelve cuántos bytes ocupan `n` elementos de tipo `T`.

 Equivale a `n * (size of T)`, pero como función sirve en contextos genéricos
 donde ya tienes un `T` y quieres el tamaño total del bloque.

 ## Ejemplo
 ```pengu
 let total is calling memoria.bytes_for of Player with 100
 ```

### `MemoriaPoint`

> rune MemoriaPoint

```pengu
    x as int
    y as int
```

 Rune de apoyo para los tests: sin campos con dueño, `banish` libera directo.

### `_t_int`

> **_t_int**(got: int, want: int) -> void

 Helper de test: igualdad exacta de `int`.

### `_t_usize`

> **_t_usize**(got: usize, want: usize) -> void

 Helper de test: igualdad exacta de `usize` expresada como `int`.

### `"alloc returns a zeroed int"`

> test "alloc returns a zeroed int"

 ─── alloc ──────────────────────────────────────────────────────────────────

### `"alloc supports writing and reading back"`

> test "alloc supports writing and reading back"

_Undocumented._

### `"alloc of float is zeroed"`

> test "alloc of float is zeroed"

_Undocumented._

### `"alloc of byte is zeroed"`

> test "alloc of byte is zeroed"

_Undocumented._

### `"alloc of a rune is zeroed"`

> test "alloc of a rune is zeroed"

_Undocumented._

### `"alloc_array of one element is zeroed"`

> test "alloc_array of one element is zeroed"

 ─── alloc_array ────────────────────────────────────────────────────────────

### `"alloc_array of many elements is zeroed"`

> test "alloc_array of many elements is zeroed"

_Undocumented._

### `"alloc_array supports indexed writes"`

> test "alloc_array supports indexed writes"

_Undocumented._

### `"alloc_array of byte keeps every value"`

> test "alloc_array of byte keeps every value"

_Undocumented._

### `"alloc_array of float is zeroed and writable"`

> test "alloc_array of float is zeroed and writable"

_Undocumented._

### `"try_alloc returns some and a usable pointer"`

> test "try_alloc returns some and a usable pointer"

 ─── try_alloc / try_alloc_array ────────────────────────────────────────────

### `"try_alloc_array returns some and zeroes"`

> test "try_alloc_array returns some and zeroes"

_Undocumented._

### `"try_alloc_array of one element"`

> test "try_alloc_array of one element"

_Undocumented._

### `"resize preserves the old content"`

> test "resize preserves the old content"

 ─── resize_array ───────────────────────────────────────────────────────────

### `"resize zeroes the new tail"`

> test "resize zeroes the new tail"

_Undocumented._

### `"resize shrink keeps the prefix"`

> test "resize shrink keeps the prefix"

_Undocumented._

### `"resize with equal sizes keeps the content"`

> test "resize with equal sizes keeps the content"

_Undocumented._

### `"resize from null behaves like alloc_array"`

> test "resize from null behaves like alloc_array"

_Undocumented._

### `"resize grows a byte buffer"`

> test "resize grows a byte buffer"

_Undocumented._

### `"try_resize returns some and preserves content"`

> test "try_resize returns some and preserves content"

 ─── try_resize_array ───────────────────────────────────────────────────────

### `"try_resize with equal sizes returns the same pointer"`

> test "try_resize with equal sizes returns the same pointer"

_Undocumented._

### `"try_resize from null allocates zeroed"`

> test "try_resize from null allocates zeroed"

_Undocumented._

### `"copy moves non-overlapping blocks"`

> test "copy moves non-overlapping blocks"

 ─── copy ───────────────────────────────────────────────────────────────────

### `"copy overlaps forward safely"`

> test "copy overlaps forward safely"

_Undocumented._

### `"copy overlaps backward safely"`

> test "copy overlaps backward safely"

_Undocumented._

### `"copy of zero elements is a no-op"`

> test "copy of zero elements is a no-op"

_Undocumented._

### `"copy works on byte buffers"`

> test "copy works on byte buffers"

_Undocumented._

### `"fill writes a non-zero int pattern"`

> test "fill writes a non-zero int pattern"

 ─── fill ───────────────────────────────────────────────────────────────────

### `"fill writes a float pattern"`

> test "fill writes a float pattern"

_Undocumented._

### `"fill with zero matches zero"`

> test "fill with zero matches zero"

_Undocumented._

### `"fill works on a single element"`

> test "fill works on a single element"

_Undocumented._

### `"zero clears one element"`

> test "zero clears one element"

 ─── zero ───────────────────────────────────────────────────────────────────

### `"zero clears many elements"`

> test "zero clears many elements"

_Undocumented._

### `"zero clears a float buffer"`

> test "zero clears a float buffer"

_Undocumented._

### `"swap exchanges two ints"`

> test "swap exchanges two ints"

 ─── swap ───────────────────────────────────────────────────────────────────

### `"swap is a no-op on equal values"`

> test "swap is a no-op on equal values"

_Undocumented._

### `"swap exchanges two floats"`

> test "swap exchanges two floats"

_Undocumented._

### `"swap exchanges two runes"`

> test "swap exchanges two runes"

_Undocumented._

### `"compare returns zero for equal blocks"`

> test "compare returns zero for equal blocks"

 ─── compare ────────────────────────────────────────────────────────────────

### `"compare returns minus one when a is smaller"`

> test "compare returns minus one when a is smaller"

_Undocumented._

### `"compare returns one when a is larger"`

> test "compare returns one when a is larger"

_Undocumented._

### `"compare finds the first differing element"`

> test "compare finds the first differing element"

_Undocumented._

### `"compare of zero elements is zero"`

> test "compare of zero elements is zero"

_Undocumented._

### `"compare works on byte buffers"`

> test "compare works on byte buffers"

_Undocumented._

### `"bytes_for counts int elements"`

> test "bytes_for counts int elements"

 ─── bytes_for ──────────────────────────────────────────────────────────────

### `"bytes_for counts byte elements"`

> test "bytes_for counts byte elements"

_Undocumented._

### `"bytes_for counts f64 elements"`

> test "bytes_for counts f64 elements"

_Undocumented._

### `"bytes_for counts rune elements"`

> test "bytes_for counts rune elements"

_Undocumented._

### `"bytes_for of zero elements is zero"`

> test "bytes_for of zero elements is zero"

_Undocumented._

### `"alloc, fill and banish compose"`

> test "alloc, fill and banish compose"

 ─── composición ────────────────────────────────────────────────────────────

### `"resize plus defer frees exactly once"`

> test "resize plus defer frees exactly once"

_Undocumented._

