# PenguScript v0.6 - Especificación corregida lista para gramática

> Fix de v0.5: `self` siempre es `ref`, `const` solo global, `var/let` solo local, `opaque` y uso directo de defines de C.

## 1. Principios y seguridad estilo V

- Indentación como Python. No `;` ni `{}`
- `as` = solo tipo, `is` = solo valor, `to` = conversión, `into` = retorno
- **Scope seguro:**
  - `const` -> solo top-level (global). Se traduce a `#define`. No se puede usar dentro de funciones.
  - `var` / `let` -> solo dentro de `weave` / `enchanting` / `if` / `for` / `while`. No globales.
  - Así evitas mutable global como en V lang.
- `self` en `enchanting` siempre es `ref to SelfType`, siempre se usa con `->`
- Todo es expresión: `if`, `when`, `for` retornan valor
- Runtime: `pengu_runtime.h`

## 2. Comentarios

```pengu
# línea
##
 bloque
##
```

```c
// línea
/* bloque */
```

## 3. Imports

```pengu
# tu código .pengu - se fusiona en un solo .c
import src.components.Player
import src.math.Vec2

# cabecera C - genera #include
include "raylib.h"

# librería C - genera -l
link "raylib"
link "m"
```

```c
#include "raylib.h"
#include "pengu_runtime.h"
// bundle de Player.pengu y Vec2.pengu
// clang bundle.c -lraylib -lm -o juego
```

## 4. Tipos base

```pengu
int, i32, i64, float, f32, f64, bool, string, void
ref to T
ref to void        # void* para WebUI y callbacks
array of T         # fijo
slice of T         # {data, len}
list of T          # dinámico
map of K to V      # dinámico
maybe T
opaque             # tipo incompleto de C, ej Texture2D
```

```c
void* p;
typedef struct { int* data; int len; } slice_int;
typedef struct Texture2D Texture2D; // opaque
```

## 5. Variables - var / let / const con scope

```pengu
# top-level SOLO const, rune, omen, alias, import, include, link, weave, enchanting
const MAX_ENTITIES as int is 1000
const PI as float is 3.14

rune Vec2:
  x as float
  y as float

weave main into int:
  var x as int is 10         # mutable local
  let y as int is 10         # inmutable local -> const int en C
  let p as ref to void is sigil of x to ref to void

  set x is x + 1             # solo var puede cambiar con set
  # set y is 20 -> error, y es let
```

```c
#define MAX_ENTITIES 1000
#define PI 3.14f
typedef struct { float x; float y; } Vec2;
int main() {
  int x = 10;
  const int y = 10;
  void* p = &x;
  x = x + 1;
}
```

Regla: `const` fuera de funciones. `var/let` solo dentro de funciones/estructuras de control.

## 6. Aritmética, conversión y bitwise

```pengu
let a is 10 + 20 * 2
let b is (10 + 20) * 2
let f as float is 10 to float
let bits is transmute f to int

# bitwise - para Raylib flags
let flags is FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT
let masked is flags & 0xFF
let xor is flags ^ 1
let not is ~flags
let shifted is 1 << 5
let rshift is 32 >> 2
```

```c
int flags = FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT;
int masked = flags & 0xFF;
```

## 7. Arrays, Slices, Lists, Maps, Strings

```pengu
let arr is array of int with size 10
let first is arr at 0
set arr at 0 is 99

let part as slice of int is arr at 1 to 3
let n is part length

# for como expresión
let evens is for x in arr when x % 2 == 0 then x
let doubled is for x in arr then x * 2

# list y map dinámicos - vienen con métodos via enchanting
var vertices as list of Vec2 is list of Vec2 with capacity MAX_ENTITIES
calling vertices.push with Vec2 is with x is 10 and y is 20

var lookup as map of int to Vec2 is map of int to Vec2

let msg is "player {name} at {x}"
```

```c
int arr[10];
slice_int part = {.data=&arr[1],.len=2};
list_Vec2 vertices; list_init(&vertices, MAX_ENTITIES); list_push(&vertices, ...);
```

## 8. Structs, Unions, Alias, Omen, Opaque

```pengu
rune Vec2:
  x as float
  y as float

let v as Vec2 is with x is 10 and y is 20
let vx is v.x
set v.x is 100.0

# si v es ref to Vec2, siempre ->
var vp as ref to Vec2 is sigil of v
set vp->x is 100.0

echo Value:
  i as int
  f as float

alias MyInt as int
alias Texture as opaque

omen Result:
  Ok with value as int
  Err with msg as string
```

```c
typedef struct { float x; float y; } Vec2;
Vec2 v = {.x=10,.y=20};
```

## 9. Enchanting

`self` siempre es `ref to SelfType`, siempre con `->`. Así no hay ambigüedad para Lark.

```pengu
rune Vec2:
  x as float
  y as float

enchanting Vec2:
  weave add with other as Vec2 into Vec2:
    Vec2 is with x is self->x + other.x and y is self->y + other.y

  weave length into float:
    (self->x * self->x + self->y * self->y) to float

  weave move with dx as float, dy as float into void:
    set self->x is self->x + dx
    set self->y is self->y + dy

enchanting Player:
  weave update with dt as float into void:
    set self->pos.x is self->pos.x + self->vel.x * dt
    set self->pos.y is self->pos.y + self->vel.y * dt

# uso
let a as Vec2 is with x is 10 and y is 20
let b as Vec2 is with x is 5 and y is 5
let c is calling a.add with b

var d as Vec2 is a
calling d.move with 10, 0
```

```c
Vec2 Vec2_add(Vec2* self, Vec2 other) { return (Vec2){self->x+other.x, self->y+other.y}; }
void Vec2_move(Vec2* self, float dx, float dy) { self->x+=dx; self->y+=dy; }
Vec2 c = Vec2_add(&a, b);
Vec2_move(&d, 10, 0);
```

## 10. Funciones

```pengu
weave add with a as int, b as int into int:
  a + b # implicit return

weave DrawText with text as string, x as int is 0, y as int is 0 into void:
  # ...

calling DrawText with text is "hola" and x is 100

declare InitWindow with w as int, h as int, title as string into void
declare WindowShouldClose into bool

inline weave fast_add with a as int, b as int into int:
  a + b
```

## 11. Punteros a función y void*

```pengu
alias AddFunc as ref to weave with int, int into int
let fp is AddFunc is sigil of add

# WebUI - callback con void*
alias WebUIHandler as ref to weave with e as ref to void into void
let handler as WebUIHandler is sigil of my_handler
declare webui_bind with win as ref to void, id as string, func as WebUIHandler into void
```

## 12. Scope, Defer, Banish

```pengu
weave test into void:
  let p as ref to int is calling alloc with size of int
  defer banish p
  errdefer banish p
  set essence of p is 10
```

## 13. Control de flujo

```pengu
let color is if x > 10 then "red" else "blue"

if file as File is calling open with "data.txt" is present:
  calling print with file->name

unless file is present:
  return 1

let state as string is judge key:
  when w -> "up"
  when s -> "down"
  else -> "idle"

while x < 10:
  set x is x + 1
  if x == 5: continue
  if x == 9: break

for i from 0 to 10:
  calling print with i

for item in arr:
  calling print with item
```

## 14. With statement - desambiguado

- `is with ...` = inicialización de struct (expresión)
- `with X:` = statement para no repetir objeto

```pengu
let v as Vec2 is with x is 10 and y is 20  # expresión

with player:           # statement
  set.x is 100
  set.y is 200
  calling.move with 5
```

```c
Vec2 v = {.x=10,.y=20};
player.x=100; player.y=200; Player_move(&player,5);
```

## 15. Destructuring

```pengu
let x, y is my_vec
```

## 16. Maybe + Result

```pengu
let user as maybe User is maybe none
let name is user or else "guest"
let u is user or return 1

let file is calling open_file with "data.txt" or:
  let err is error
  calling print with err
  return 1

let file2 is try calling open_file with "other.txt"
```

## 17. Memoria

```pengu
let p as ref to int is calling alloc with size of int
banish p
```

## 18. Resolución de identificadores de C

Cualquier identificador que no exista en Pengu pero que venga de un `include` se deja tal cual en C. Así puedes usar defines de Raylib sin declarar:

```pengu
include "raylib.h"
let key is KEY_W
let flag is FLAG_WINDOW_RESIZABLE
```

```c
#include "raylib.h"
int key = KEY_W;
```

## 19. Ejemplo completo v0.6 con scope seguro

`src/math/Vec2.pengu`

```pengu
rune Vec2:
  x as float
  y as float

enchanting Vec2:
  weave add with other as Vec2 into Vec2:
    Vec2 is with x is self->x + other.x and y is self->y + other.y

  weave move with dx as float, dy as float into void:
    set self->x is self->x + dx
```

`src/components/Player.pengu`

```pengu
import src.math.Vec2

rune Player:
  pos as Vec2
  vel as Vec2
  health as int

enchanting Player:
  weave update with dt as float into void:
    set self->pos.x is self->pos.x + self->vel.x * dt
```

`main.pengu`

```pengu
include "raylib.h"
link "raylib"

import src.components.Player
import src.math.Vec2

const MAX_ENTITIES as int is 1000

declare InitWindow with w as int, h as int, title as string into void
declare WindowShouldClose into bool
declare BeginDrawing into void
declare EndDrawing into void
declare CloseWindow into void

weave main into int:
  calling InitWindow with 800, 600, "Pengu v0.6"

  var player as Player is with pos is with x is 100 and y is 100 and vel is with x is 1 and y is 0 and health is 100
  var bullets as list of Vec2 is list of Vec2 with capacity MAX_ENTITIES
  let flags is FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT

  while calling WindowShouldClose is false:
    calling player.update with 0.016
    calling BeginDrawing
    calling EndDrawing

  calling CloseWindow
  return 0
```

**C bundle:**

```c
#include "raylib.h"
#include "pengu_runtime.h"
#define MAX_ENTITIES 1000
typedef struct { float x; float y; } Vec2;
Vec2 Vec2_add(Vec2* self, Vec2 other) { ... }
typedef struct { Vec2 pos; Vec2 vel; int health; } Player;
void Player_update(Player* self, float dt) { self->pos.x+=self->vel.x*dt; }

int main() {
  InitWindow(800,600,"Pengu v0.6");
  Player player = {.pos={100,100},.vel={1,0},.health=100};
  list_Vec2 bullets; list_init(&bullets, MAX_ENTITIES);
  const int flags = FLAG_WINDOW_RESIZABLE | FLAG_VSYNC_HINT;
  while(!WindowShouldClose()) { Player_update(&player,0.016); BeginDrawing(); EndDrawing(); }
  CloseWindow(); return 0;
}
```

## 20. Qué NO es PenguScript

- No clases/herencia
- No genéricos complejos
- No excepciones
- No operator overloading
- No globals mutables - var/let solo local, const global

## Sección 21 - Notas para Lark - Parser completo sin ambigüedades

Esta sección es para que un agente de IA genere el parser Lark de PenguScript v0.6 que pase tests. Incluye tokens, precedencia y fixes de ambigüedad.

## 21.1 Configuración Lark

Usar LALR + Indenter Python-like. No usar `;` ni `{}`.

```python
from lark import Lark
from lark.indenter import Indenter

class PenguIndenter(Indenter):
    NL_type = '_NEWLINE'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 4
```

Gramática empieza con `start: file`.

## 21.2 Keywords reservadas (no pueden ser NAME)

```coffee
"import" "include" "link" "const" "var" "let" "rune" "echo" "omen" "alias" 
"enchanting" "weave" "inline" "declare" "if" "then" "else" "unless" "while" 
"for" "from" "to" "step" "in" "when" "judge" "with" "as" "is" "into" "of" 
"ref" "array" "slice" "list" "map" "maybe" "opaque" "and" "or" "not" "set" 
"calling" "defer" "errdefer" "banish" "return" "break" "continue" "try" 
"present" "none" "length" "size" "capacity" "sigil" "essence" "transmute" "self" "error"
```

`and` tiene doble uso: separador de campos/args y lógico. En esta versión `and` solo es separador. No hay `and` lógico, usar `&` para bitwise.

## 21.3 Tokens

```lark
%import common.WS_INLINE
%import common.INT
%import common.FLOAT
%ignore WS_INLINE

_NEWLINE: /(\r?\n[\t ]*)+/
%ignore /#.*$/m   // comentario línea
%ignore /##[\s\S]*?##/  // bloque ## ##

NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
STRING: /"([^"\\]|\\.|{[^}]+})*"/   // permite {expr} dentro para interpolación
```

String con interpolación: luego en post-proceso extraer `{expr}` y generar `snprintf`.

`->` flecha: `ARROW: "->"`  // para when y para acceso `->` ??? Conflicto. Solución:

- Flecha when: `->` solo en contexto `when X -> Y`.
- Acceso puntero: también `->`. Es el mismo token, Lark lo distingue por contexto. Definir token `ARROW: "->"`

Acceso: `.` y `->` son tokens.

## 21.4 Tipos - sin ambigüedad

```lark
type: base_type
    | ref_type
    | array_type
    | slice_type
    | list_type
    | map_type
    | maybe_type
    | opaque_type
    | NAME  // custom rune

base_type: "int" | "i32" | "i64" | "float" | "f32" | "f64" | "bool" | "string" | "void"
ref_type: "ref" "to" (base_type | NAME | "void")
array_type: "array" "of" type ["with" "size" expr]
slice_type: "slice" "of" type
list_type: "list" "of" type ["with" "capacity" expr]
map_type: "map" "of" type "to" type
maybe_type: "maybe" type
opaque_type: "opaque"
```

Nota: `map of K to V` usa `to` pero aquí `to` solo aparece dentro de tipo, no como conversión. Sin conflicto porque conversión es `expr to type` a nivel expr.

## 21.5 Top-level - scope seguro

```lark
file: _NEWLINE* top_stmt* 

top_stmt: import_stmt
      | include_stmt
      | link_stmt
      | const_decl
      | rune_decl
      | omen_decl
      | echo_decl
      | alias_decl
      | weave_decl
      | enchanting_decl
      | declare_stmt

// Solo top-level const, no var/let global. El chequeo semántico luego rechaza var/let global.
// Pero gramática permite var/let para no complicar, luego validas.

import_stmt: "import" dotted_path _NEWLINE
dotted_path: NAME ("." NAME)*

include_stmt: "include" STRING _NEWLINE
link_stmt: "link" STRING _NEWLINE

const_decl: "const" NAME ["as" type] "is" expr _NEWLINE

rune_decl: "rune" NAME ":" _NEWLINE _INDENT field_decl+ _DEDENT
field_decl: NAME "as" type _NEWLINE

omen_decl: "omen" NAME ":" _NEWLINE _INDENT omen_variant+ _DEDENT
omen_variant: NAME ["with" NAME "as" type ("and" NAME "as" type)*] _NEWLINE

echo_decl: "echo" NAME ":" _NEWLINE _INDENT field_decl+ _DEDENT
alias_decl: "alias" NAME "as" type _NEWLINE
```

## 21.6 Enchanting - self siempre ref

```lark
enchanting_decl: "enchanting" type ":" _NEWLINE _INDENT weave_decl+ _DEDENT

weave_decl: ["inline"] "weave" NAME ["with" param_list] ["into" type] ":" _NEWLINE _INDENT stmt* _DEDENT

param_list: param (("," | "and") param)*
param: NAME ["as" type] ["is" expr]  // is expr = default arg

declare_stmt: "declare" NAME ["with" param_list] ["into" type] _NEWLINE
```

Dentro de `enchanting`, `self` es keyword que siempre es `ref to Self`. Traduce a `Self* self` en C.

## 21.7 Statements dentro de weave

```lark
stmt: var_decl
    | let_decl
    | set_stmt
    | if_stmt
    | unless_stmt
    | while_stmt
    | for_stmt
    | judge_stmt
    | with_stmt
    | defer_stmt
    | errdefer_stmt
    | banish_stmt
    | calling_stmt
    | return_stmt
    | break_stmt
    | continue_stmt
    | expr_stmt

var_decl: "var" NAME ["as" type] "is" expr _NEWLINE
let_decl: "let" NAME ["as" type] "is" expr _NEWLINE

set_stmt: "set" target "is" expr _NEWLINE
target: with_target | normal_target
with_target: "." NAME (("." NAME) | ("->" NAME))*
normal_target: NAME (("." NAME) | ("->" NAME) | ("at" expr))* 

calling_stmt: "calling" target ["with" arg_list] _NEWLINE
arg_list: arg (("," | "and") arg)*
arg: (NAME "is" expr) | expr  // named o posicional

defer_stmt: "defer" expr _NEWLINE
errdefer_stmt: "errdefer" expr _NEWLINE
banish_stmt: "banish" expr _NEWLINE
return_stmt: "return" [expr] _NEWLINE
break_stmt: "break" _NEWLINE
continue_stmt: "continue" _NEWLINE
expr_stmt: expr _NEWLINE
```

## 21.8 Control de flujo - desambiguado

```lark
// if statement vs if expression
if_stmt: "if" [NAME ["as" type] "is" expr] [if_present_check] ":" _NEWLINE _INDENT stmt+ _DEDENT [else_block]
if_present_check: "is" "present"

else_block: "else" ":" _NEWLINE _INDENT stmt+ _DEDENT
          | "else" if_stmt

unless_stmt: "unless" expr ":" _NEWLINE _INDENT stmt+ _DEDENT

// if expression: if cond then expr else expr
if_expr: "if" expr "then" expr "else" expr

while_stmt: "while" expr ":" _NEWLINE _INDENT stmt+ _DEDENT

for_stmt: "for" NAME "from" expr "to" expr ["step" expr] ":" _NEWLINE _INDENT stmt+ _DEDENT
        | "for" NAME "in" expr ":" _NEWLINE _INDENT stmt+ _DEDENT

judge_stmt: "judge" expr ":" _NEWLINE _INDENT when_clause+ [else_clause] _DEDENT
when_clause: "when" expr "->" expr _NEWLINE
else_clause: "else" "->" expr _NEWLINE

with_stmt: "with" expr ":" _NEWLINE _INDENT stmt+ _DEDENT
```

`for` como expresión (comprehension) es parte de expr, no stmt.

## 21.9 Expresiones con precedencia - CLAVE

Definir en orden de menor a mayor precedencia. Usar reglas separadas para evitar ambigüedad.

```lark
?expr: or_else_expr

?or_else_expr: try_expr
            | or_else_expr "or" "else" try_expr      -> or_else
            | or_else_expr "or" "return" try_expr    -> or_return
            | or_else_expr "or" ":" _NEWLINE _INDENT stmt+ _DEDENT -> or_block

?try_expr: "try" try_expr | if_expr | judge_expr | for_comp_expr | logic_or

?judge_expr: "judge" expr ":" _NEWLINE _INDENT when_clause+ [else_clause] _DEDENT

?for_comp_expr: "for" NAME "in" expr ["when" expr] "then" expr  -> for_comp

?logic_or: logic_or "|" logic_and  -> bitwise_or
         | logic_and

?logic_and: logic_and "&" bit_xor -> bitwise_and
          | bit_xor

?bit_xor: bit_xor "^" bit_shift -> bitwise_xor
        | bit_shift

?bit_shift: bit_shift "<<" bit_add -> shl
          | bit_shift ">>" bit_add -> shr
          | bit_add

?bit_add: bit_add "+" bit_mul -> add
        | bit_add "-" bit_mul -> sub
        | bit_mul

?bit_mul: bit_mul "*" unary -> mul
        | bit_mul "/" unary -> div
        | bit_mul "%" unary -> mod
        | unary

?unary: "~" unary -> bit_not
      | "not" unary
      | "sigil" "of" unary -> sigil_of
      | "essence" "of" unary -> essence_of
      | "transmute" unary "to" type -> transmute
      | postfix

?postfix: primary
        | postfix "at" expr ["to" expr] -> at_expr
        | postfix "length" -> length_expr
        | postfix "to" type -> cast_expr
        | postfix "." NAME -> field_access
        | postfix "->" NAME -> arrow_access

?primary: NAME
        | "self"
        | INT
        | FLOAT
        | STRING
        | "true" | "false"
        | "maybe" "none"
        | "(" expr ")"
        | struct_init
        | list_init_expr
        | map_init_expr

struct_init: "with" field_init ("and" field_init)*
field_init: NAME "is" expr

list_init_expr: "list" "of" type ["with" "capacity" expr]
map_init_expr: "map" "of" type "to" type
```

Notas:

- `at` con `to` para slice: `arr at 1 to 3` -> `at_expr` con dos expr. Si solo `at 0`, segundo es None.
- `is with` para struct: en realidad `let v as Vec2 is with x is 10` -> el `is` es de var_decl, el `with x is...` es struct_init como expr. Entonces `is` de asignación ya consumido, `struct_init` empieza con `with`. Perfecto.
- `to` para cast vs `to` para slice: cast es `postfix to type`, slice es `at expr to expr`. Como cast espera TYPE, no INT, no hay conflicto.

## 21.10 Resolución de defines de C

Regla semántica post-parse: si un NAME no está definido en tabla de símbolos Pengu, y existe un `include` previo, dejarlo pasar y generar tal cual en C. Así `KEY_W`, `FLAG_WINDOW_RESIZABLE` funcionan sin declare.

Implementar en el checker: `if name not in symbols and name is UPPER_CASE -> treat as C define`.

## 21.11 Tests que debe pasar el parser

El agente debe testear estos casos:

1. `const MAX as int is 100` solo top-level, no dentro de weave -> debe fallar si está dentro
2. `var x` dentro de weave ok, fuera debe fallar (chequeo semántico)
3. `enchanting Vec2:` con `self->x` ok, `self.x` debe fallar (self siempre ref)
4. `let flags is FLAG_A | FLAG_B & 0xFF` -> parsea bitwise
5. `let part as slice of int is arr at 1 to 3`
6. `let evens is for x in arr when x % 2 == 0 then x`
7. `with player: set.x is 100` -> target with_target
8. `calling vertices.push with Vec2 is with x is 10`
9. `if file is present:` vs `if x > 10 then 1 else 2`
10. `judge key: when w -> "up" else -> "idle"`
11. `ref to void` y `alias T as opaque`
12. String interpolación `"hi {name}"`

---

# 22. Sistema de Genéricos (Generics)

PenguScript v0.6 incorpora soporte completo para programación genérica mediante parámetros de tipo estáticos y monomorfización a tiempo de compilación.

## 22.1 Declaración de tipos genéricos (`shard`)

Los parámetros de tipo se declaran inmediatamente después del identificador utilizando la palabra clave `shard`, separados por `and` o comas `,`:

```pengu
rune Pair shard T and U:
  first as T
  second as U

echo Value shard T:
  num as int
  data as T

omen Status shard T and E:
  Success with data as T
  Failure with error as E

alias Entry shard K and V as Pair of K and V
```

## 22.2 Instanciación de tipos genéricos (`of`)

Los tipos genéricos se instancian utilizando la palabra clave `of`:

```pengu
let p as Pair of int and float is with first is 1 and second is 3.14
let nested as Pair of (Pair of int and int) and string is ...
```

Los paréntesis `(...)` permiten agrupar tipos genéricos anidados con total claridad sintáctica y sin ambigüedad.

## 22.3 Funciones genéricas

Las funciones (`weave`) y firmas externas (`declare`) pueden declarar parámetros de tipo antes de los parámetros de argumentos (`with`):

```pengu
weave identity shard T with x as T into T:
  return x

weave swap shard T and U with a as T, b as U into Pair of U and T:
  return with first is b and second is a
```

### Inferencia automática de parámetros de tipo
Al invocar una función genérica con `calling`, el compilador infiere automáticamente los argumentos de tipo a partir de los argumentos suministrados:

```pengu
let a as int is calling identity with 100         # T se infiere como int
let b as string is calling identity with "pengu"  # T se infiere como string
let s is calling swap with 10 and 3.14            # T=int, U=float -> Pair of float and int
```

## 22.4 Enchanting en tipos genéricos

Es posible extender tipos genéricos utilizando bloques `enchanting` con parámetros de tipo:

```pengu
rune Box shard T:
  value as T

enchanting Box of T:
  weave get into T:
    return self->value

  weave set with new_val as T into void:
    self->value is new_val
```

## 22.5 Monomorfización a C99

El compilador utiliza **monomorfización estática**. Cada combinación única de tipos genera una definición C concreta, garantizando cero sobrecosto en tiempo de ejecución (cero boxing y sin punteros opacos `void*`):

- `Pair of int and float` -> `struct Pair_int_float`
- `identity with 100` -> `int32_t identity_int(int32_t x)`
- `calling b.get` (en `Box of int`) -> `Box_int_get(&b)`

