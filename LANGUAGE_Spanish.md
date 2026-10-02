# Referencia del Lenguaje PenguScript

> **Versión cubierta:** PenguScript **0.14.x** (sincronizada con `VERSION` y `pengu_version.py`; generador de código C99/C11; cabeceras de runtime en `pengu_runtime.h`).
> Esta es la guía definitiva de sintaxis y semántica, escrita a partir de las fuentes
> del compilador (`pengu_grammar.py`, `pengu_checker.py`, `pengu_codegen.py`,
> `pengu_infer.py`, `pengu_runtime.h`). Complementa el
> [`CHEATSHEET.md`](CHEATSHEET.md) y el [`README.md`](README.md) rápidos, explicando cada
> característica con ejemplos de PenguScript y C generado.

---

## Tabla de contenidos

1. [Introducción y principios](#1-introduction--principles)
2. [Inicio rápido](#2-quick-start)
3. [Estructura léxica](#3-lexical-structure)
4. [Sistema de tipos](#4-type-system)
5. [Variables, constantes y ámbito](#5-variables-constants--scope)
6. [Operadores y expresiones](#6-operators--expressions)
7. [Flujo de control](#7-control-flow)
8. [Funciones](#8-functions)
9. [Tipos compuestos](#9-composite-types)
10. [Métodos, conceptos y enlace](#10-methods-concepts--binding)
11. [Genéricos](#11-generics)
12. [Opcionales y errores](#12-optionals--errors)
13. [Memoria y punteros](#13-memory--pointers)
14. [Módulos, importaciones e interoperabilidad con C](#14-modules-imports--c-interop)
15. [Literales: cadenas, arrays, mapas, bloques indentados y rangos](#15-literals-strings-arrays-maps-indent-blocks--ranges)
16. [Compilación condicional (`when`)](#16-conditional-compilation-when)
17. [Pruebas unitarias (`test`)](#17-unit-tests-test)
18. [Construcción estilo bloque (expresiones `with:`)](#18-block-style-construction-with-expressions)
19. [Biblioteca estándar](#19-standard-library)
    - 19.1 [Módulos de PenguScript puro](#191-pure-penguscript-modules-27-modules)
    - 19.2 [Módulos de enlace nativo de C](#192-c-native-binding-modules-25-dpengu-modules)
    - 19.3 [Ejemplos de la biblioteca estándar central](#193-core-standard-library-examples)
    - 19.4 [Recursos embebidos del proyecto (`arca`)](#194-embedded-project-assets-arca)
20. [Herramientas y estructura del proyecto](#20-tooling--project-layout)
21. [Ejemplo completo](#21-complete-example)
22. [Apéndice: Catálogo de diagnósticos del compilador (`E0000`–`E0050` y advertencias)](#22-appendix-compiler-diagnostic-catalog)

---

## 1. Introducción y principios

PenguScript es un lenguaje sensible a la indentación y de tipado estático que
compila directamente a C99/C11. Sus reglas de diseño:

- **Una palabra clave por tarea.** Las palabras reservadas son semánticas (`weave` para
  funciones, `rune` para structs, `omen` para enums/tipos suma, `calling` para
  llamadas, `set` para asignación, `banish` para liberación explícita, …).
- **Explícito antes que oculto.** La memoria *no* se recolecta como basura: los valores del heap se
  liberan explícitamente con `banish`, y se difieren con `defer`/`errdefer`. La propiedad
  de cada helper de runtime está documentada en `pengu_runtime.h`.
- **Amigable en tiempo de compilación.** `const`, la monomorfización genérica (`shard`),
  las bifurcaciones en tiempo de compilación con `when` y el plegado de constantes ocurren antes de
  emitir C.
- **C es el destino *y* la frontera.** `declare`/`include`/`link` hacen utilizable cualquier
  biblioteca de C; `rune`/`echo` se corresponden 1:1 con `struct`/`union` de C; los
  handles opacos de C son tipos `opaque`.

> [!NOTE]
> El pipeline del compilador es: gramática Lark → `PenguParser` → `PenguChecker`
> (dos pasadas: recolectar las definiciones de nivel superior y, después, validar sentencias) →
> `TypeInferrer`/`ConstFolder` → `PenguCodegen` (texto C). Un artefacto compilado
> es un único archivo C (`bundle.c`) enlazado contra `libpengu_runtime.a`.

---

## 2. Inicio rápido

```pengu
# hello.pengu  — a standalone script
weave main into int:
    calling print with "Hello, Pengu!\n"
    return 0
```

```console
$ pengu run hello.pengu          # build + execute a loose script
$ pengu run                      # build+run ./pengu.yaml project target
$ pengu build                    # compile project (default output exe)
$ pengu check                    # parse + type-check every module, no C
$ pengu test                     # compile & run the project's `test` blocks
$ pengu fmt                      # format .pengu files
$ pengu doc                      # emit Markdown from ## comments
$ pengu bind header.h            # generate a .d.pengu binding from a C header
$ pengu lsp                      # launch the language server (pygls)
```

> [!IMPORTANT]
> El `weave` de entrada debe llamarse `main` para los ejecutables. La función C
> generada es `pengu_main`; `main` en sí está reservado como variable en tiempo de
> compilación (véase [`when`](#16-conditional-compilation-when)).

---

## 3. Estructura léxica

### 3.1 Archivos

| Archivo | Propósito |
|------|---------|
| `*.pengu` | Módulo fuente (puede contener cuerpos de implementación). |
| `*.d.pengu` | Módulo de solo declaraciones (bindings). Los cuerpos de implementación son un error (`E0025`). Refleja el `.d.ts` de TypeScript; no se emite C para sus tipos. |
| `std/*` | Módulos de la biblioteca estándar (módulos envoltorio o bindings `*.d.pengu`). |

> [!NOTE]
> **Eliminación de BOM:** `PenguParser.parse` detecta y elimina automáticamente los Byte Order Marks UTF-8 (`\xef\xbb\xbf`) de las entradas fuente antes de la tokenización, evitando errores de sintaxis inesperados cuando los archivos se editan con herramientas de Windows.

### 3.2 Comentarios y documentación

```pengu
# line comment
## doc comment (used by `pengu doc` and hover/extraction)
# banner --------------------------------------------
## multi-line doc comment
   describing complex APIs
##
```

- Los comentarios de una sola línea comienzan con `#` (`/#[^#\r\n]*$/m`).
- Los comentarios de documentación comienzan con `##` (`## doc comment` o `##[\s\S]*?##` multilínea). Tanto `#` como `##` inmediatamente anteriores a declaraciones son recolectados por `pengu doc` y el servidor LSP.
- **Preservación de líneas:** El parser ejecuta `_strip_comments` durante el análisis léxico, reemplazando los comentarios por espacios en blanco. Esto garantiza que los números de línea y columna del código fuente permanezcan 100% exactos en los informes de error, los spans del LSP y las directivas `#line` del C generado.

### 3.3 Identificadores y visibilidad

Los identificadores cumplen `[A-Za-z_][A-Za-z0-9_]*`. Las convenciones de estilo siguen `snake_case` para valores, variables y weaves, y `PascalCase` para los tipos de usuario (`rune`, `echo`, `omen`, `concept`).

- **Privacidad de módulos y runes (prefijo `_`):** Cualquier símbolo de nivel superior (función, tipo, constante) que comience con `_` es estrictamente privado de su módulo. Cualquier campo de rune que comience con `_` (p. ej. `_internal_ptr`) es estrictamente privado de su definición de rune. Acceder a un símbolo privado desde fuera de su módulo o rune produce `E0043: PrivateSymbolAccessError`.
- **Internals del compilador (`_pengu_*`):** Todos los símbolos, temporales y helpers de runtime generados por el compilador usan el prefijo `_pengu_` o `pengu_`. Los usuarios deberían evitar declarar identificadores con este prefijo para prevenir colisiones de símbolos.
- **Binding de descarte (`_`):** Un guion bajo aislado `_` actúa como binding de descarte comodín (`for _, v in col`). Descarta el valor sin vincular un identificador en la tabla de símbolos.
- **Punto de entrada reservado (`main`):** `main` está reservado como el weave de entrada (`weave main …`). No puede declararse como variable local o global, constante ni variable estática (`var main`, `let main`, `const main`, `static var main` producen todos `E0040`).

### 3.4 Palabras reservadas

Las siguientes palabras clave están reservadas por PenguScript:

```text
import include link insignia const var let set static weave declare enchanting
rune echo omen alias seal concept bind shard where when test if
unless else while for in from to step judge calling with into as is many return
break continue defer errdefer banish some ord chr bytes of essence of sigil of
transmute size of try defined not and or lambda null true false maybe none error
derive cyclus donum
```

**Palabras clave blandas:**
- `frozen`: Activa solo en posiciones de expresión de tipo (`frozen int`, `ref to frozen T`). Los identificadores llamados `frozen` en nombres de variables, campos o funciones son válidos. Véase [§9.5](#95-frozen--read-only-qualification).
- `borrowed`: Activa solo inmediatamente después de `var` o `let` (`var borrowed x is …`, `let borrowed x is …`). En cualquier otro lugar (campos de struct, parámetros, nombres de funciones), `borrowed` se trata como un identificador normal. Ten en cuenta que `var borrowed is 5` es un error de sintaxis porque `borrowed` en esa posición se parsea como el modificador. Véanse [§5.4](#54-the-borrowed-modifier) y [§13.4](#134-scope-owned-locals-auto-banish).
- `inline`, `ritual`: Activas solo como modificadores de weave (`weave inline f into void:`, `inline weave f into void:`, `weave ritual make into T:`). En cualquier otro contexto, se tratan como identificadores ordinarios.

**Protección de identificadores de C (`E0035`):**
Para garantizar que el C generado compile limpiamente sin colisiones de nombres contra la biblioteca estándar de C o los tipos del runtime de C, PenguScript reserva nombres de tipos de la biblioteca estándar de C (`C_RESERVED_TYPE_NAMES`, p. ej. `FILE`, `size_t`, `int8_t`, `uint32_t`, `bool`) y nombres comunes de funciones de C (`C_RESERVED_FN_NAMES`, p. ej. `printf`, `malloc`, `free`, `exit`, `memcpy`). Declarar funciones de nivel superior o tipos de usuario con estos nombres produce `E0035`, a menos que:
1. Se declaren dentro de un archivo de binding `.d.pengu`;
2. Lleven el prefijo de un guion bajo inicial (`_`); o
3. Lleven el prefijo de la directiva `insignia` del módulo.

---

## 4. Sistema de tipos

### 4.1 Tipos primitivos

| Pengu | C (típico) | Tamaño (bits) | Notas |
|-------|-------------|-------------|-------|
| `int` / `i32` | `int32_t` | 32 | entero por defecto |
| `i8`/`i16`/`i64` | `int8_t`/`int16_t`/`int64_t` | 8/16/64 | enteros con signo de ancho fijo |
| `u8`/`byte` | `uint8_t` | 8 | `byte` es un alias de `u8` |
| `u16`/`u32`/`u64` | `uint16_t`/… | 16/32/64 | enteros sin signo de ancho fijo |
| `usize`/`isize` | `size_t`/`ssize_t`-ish | ancho de puntero | tamaño de palabra de la plataforma (32 o 64 bits) |
| `float`/`f64`/`double` | `double` | 64 | float IEEE de 64 bits por defecto |
| `f32` | `float` | 32 | float IEEE de 32 bits |
| `bool` | `bool` | 8 | booleano (`true`/`false`) |
| `char` | `char` | 8 | byte ASCII / C individual |
| `string` | `PenguString` | runtime | slice con longitud como prefijo + byte nulo; véase §4.2 |
| `void` | `void` | – | tipo vacío (sin valor) |

Los sufijos de literales enteros y las conversiones `to` están disponibles (`1.5 to int`, `x to string`). Los nombres de typedef estándar de C (`size_t`, `int8_t`, `uint64_t`) se aceptan como alias integrados.

> [!NOTE]
> **Estimación de tamaño (`estimate_size`):**
> El compilador calcula aproximaciones del tamaño en bytes usando `estimate_size` (`pengu_types.py`). Para los structs `rune`, `estimate_size` suma directamente los tamaños estimados de sus campos constituyentes sin calcular el padding de alineación nativo de C. El diseño exacto de memoria y el padding de structs los gestiona de forma nativa el compilador de C posterior durante la generación de código. Esta estimación se muestra en los tooltips de hover del LSP y se usa para heurísticas de diseño de contenedores.

### 4.2 Contenedores de runtime

PenguScript define structs de contenedor limpios y compatibles con C en `pengu_runtime.h`:

| Pengu | Tipo C del runtime | Diseño y definición del struct |
|-------|----------------|----------------------------|
| `string` | `PenguString` | `typedef struct { char *data; int len; } PenguString;` |
| `slice of T` | `PenguSlice` | `typedef struct { void *data; int len; size_t elem_size; } PenguSlice;` |
| `list of T` | `PenguList` | `typedef struct { void *data; int len; int cap; size_t elem_size; } PenguList;` |
| `map of K to V` | `PenguMap` | `typedef struct { PenguMapEntry *entries; int len; int cap; size_t key_size; size_t val_size; } PenguMap;` |
| `maybe T` | `PenguMaybe` | `typedef struct { bool is_present; void *value; } PenguMaybe;` |
| `result of T to E` | `PenguResult` | `typedef struct { bool is_ok; void *ok_val; void *err_val; } PenguResult;` |
| `range` (`a to b`) | `PenguRange` | `typedef struct { int64_t start; int64_t end; } PenguRange;` |
| Call Frame | `PenguFrame` | `typedef struct { const char *fn_name; const char *file; int line; } PenguFrame;` |

#### Semántica de contenedores y propiedad de memoria:
- **`PenguString`:** Representa una vista de cadena inmutable. Los literales de cadena en expresiones de runtime reservan memoria en el heap mediante `pengu_string_new` (o referencian `.rodata`), mientras que `pengu_string_from_cstr` crea una vista prestada sin propiedad sobre una cadena de C. Las cadenas dinámicas creadas mediante concatenación (`+`), formato `{expr}` o conversiones se reservan en el heap y se limpian automáticamente mediante auto-banish (§13.4).
- **`PenguSlice`:** Representa una ventana sin propiedad sobre elementos contiguos. Se crea mediante slicing (`nums at 1 to 3`) o a través de `std.ffi.slice_from_ptr`. Nunca posee memoria del heap; no hagas `banish` de un slice.
- **`PenguList`:** Vector dinámico ampliable. Gestiona un array interno en el heap de tamaño `cap * elem_size`, que se expande con un crecimiento amortizado de 2x al hacer `push`/`append`.
- **`PenguMap`:** Tabla hash con direccionamiento abierto y sondeo lineal. Las entradas se almacenan en `PenguMapEntry { void *key; void *val; bool occupied; }`. Las claves y los valores se copian en profundidad en las celdas de las entradas. El orden de iteración es el **orden de hash**, no el orden de inserción.
- **`PenguMaybe`:** Contenedor de valores para valores opcionales. Si `is_present` es `true`, `value` apunta a una copia en el heap reservada mediante `pengu_sigil_alloc(sizeof(T))`. Si `is_present` es `false`, `value` es `NULL`.
- **`PenguResult`:** Representa un éxito (`is_ok = true`, carga útil en `ok_val`) o un fallo (`is_ok = false`, carga útil en `err_val`).
- **`PenguFrame`:** Búfer circular en anillo de 64 frames. Rastrea las llamadas a funciones activas (`pengu_frame_push` / `pengu_frame_pop`) para emitir trazas de origen legibles por humanos en fallos fatales.

### 4.3 Tipos compuestos y de usuario

- `rune Name:` — `struct` de C (registros), véase [§9.1](#91-rune-structs).
- `echo Name:` — `union` de C (union etiquetada *sin* etiqueta de runtime), [§9.2](#92-echo-unions).
- `omen Name:` — `enum` de C (simple/con valores de cadena) o `struct` etiquetado (tipo suma algebraico), [§9.3](#93-omen-enums--algebraic-data-types).
- `seal Name as T` — newtype nominal fuerte que requiere conversiones explícitas, [§9.4](#94-seal--alias--opaque).
- `alias Name as T` — alias de tipo estructural transparente, [§9.4](#94-seal--alias--opaque).
- `opaque` — handle de puntero opaco de C (tipo `void*`; utilizable mediante `ref to`), [§9.4](#94-seal--alias--opaque).
- `ref to T`, `array of T with size N`, `array of array of T with size M with size N` (`T[M][N]` de C), `list of T`, `slice of T`, `map of K to V`, `maybe T`, `result of T to E`, tipos `fn`/puntero a weave.
- `frozen T` — cualificación de solo lectura (`const T` de C) utilizable en cualquier tipo como **modificador de tipo**, [§9.5](#95-frozen--read-only-qualification).

#### Reglas de compatibilidad y conversión de tipos:

| Familia de tipo | Tipo destino | ¿Asignable? | Regla semántica |
|-------------|-------------|-------------|---------------|
| `AliasType` | Cualquier `U` | Transparente | `alias A as B` hereda todas las reglas de compatibilidad de `B`. |
| `SealType` | `T` base | ❌ Requiere `to` | Estrictamente nominal. Un `seal S as int` no puede pasarse implícitamente a `int` sin `(val to int)`. |
| `FrozenType` | `T` (mutable) | ❌ Direccional | `mutable -> frozen` es válido; `frozen -> mutable` lo rechaza `_drops_frozen()`. |
| `RefType` | `ref to void` | ✅ Comodín | Un puntero a cualquier tipo de objeto se convierte implícitamente a `ref to void` o `ref to frozen void`. |
| `RefType` | `ref to T` | Pointee estricto | Los tipos apuntados deben coincidir exactamente (`_same_pointee`), con la única excepción de `char` ↔ `byte`. |
| `ArrayType` | `ref to T` | ✅ Decaimiento | Un array fijo decae a puntero a su primer elemento. |
| `FnType` | `ref to weave` | ✅ Decaimiento | Las declaraciones de función decaen sin problemas a referencias de puntero a función. |
| `CVarArgsType` | Variádico | Especial | Solo se permite en firmas `declare ...`; los argumentos extra de la llamada se pasan tal cual sin conversión. |

---

## 5. Variables, constantes y ámbito

### 5.1 Declaraciones

PenguScript admite ocho formas de declaración para variables, constantes y bindings desestructurados:

```pengu
# 1. Explicitly typed variable / binding with initializer
var count as int is 0
let name as string is "Ada"

# 2. Inferred variable / binding
var total is 100                          # inferred as int
let greeting is "Hello"                   # inferred as string

# 3. Zero-initialized variable with explicit type constructor
var buffer as array of byte with size 64 is array of byte with size 64

# 4. Destructuring binding (inferred container type)
let (x, y) is point_value

# 5. Destructuring with element-wise type annotations
var (id, label) as (int, string) is user_record

# 6. Destructuring with composite type annotation
let (r, g, b, a) as Color is current_color

# 7. Top-level compile-time constant
const MAX_USERS as int is 1024
const PI is 3.14159                       # type inferred as float

# 8. Function-static variable (preserved across invocations)
static var call_count as int is 0
```

- **Constantes de nivel superior (`const`):** Deben declararse en el ámbito de nivel superior (`E0001` si se colocan dentro de una función). Se evalúan y se pliegan como constantes en tiempo de compilación.
  - **Codegen de C por tipo:**
    - `RangeConst` (`a to b`): Emite `static const PenguRange c_name = { .start = a, .end = b };`.
    - `ref to char` (literal de cadena de C): Emite `#define c_name "..."`.
    - `string`: Emite `#define c_name pengu_string_from_cstr("...")`.
    - `bool`: Emite `#define c_name true` o `false`.
    - Escalares numéricos: Emite `#define c_name <folded_val>`.
    - Arrays fijos (`array of T with size N`): Emite `static const T c_name[N] = { ... };` (y dimensiones anidadas `[M][N]` para arrays multidimensionales).
    - Otros tipos inicializables estáticamente: Emite `static const T c_name = <expr>;`.
  - **Validación y prohibiciones (`_check_const_decl`):**
    - **Identificador reservado `main` (`E0040`):** No puede llamarse `main` (reservado para el punto de entrada y el `when` de comptime).
    - **Conflictos de identificadores de C (`E0035`):** No puede ensombrecer palabras reservadas de C ni nombres de tipos estándar (`C_RESERVED_TYPE_NAMES`, `C_RESERVED_WORDS`).
    - **Sin colecciones en el heap (`E0005`):** `list of T` y `map of K to V` se rechazan como constantes porque requieren reserva dinámica en el heap. Usa arrays fijos (`array of T`) en su lugar.
    - **Arrays inicializables estáticamente (`E0005`):** Los elementos de un array constante deben ser inicializables estáticamente (numéricos, bool, char, `ref to char` o runes/omens estáticos).
    - **Dimensiones conocidas (`E0015`):** Las constantes de tipo array no pueden tener dimensiones desconocidas u omitidas (`UnknownArrayDimensionError`).
    - **Expresiones en tiempo de compilación (`E0005`):** Los inicializadores deben ser estrictamente expresiones constantes en tiempo de compilación.
    - **Tipado explícito de null (`E0014`):** Inicializar una constante con `null` requiere una anotación de tipo explícita (p. ej. `const PTR as ref to int is null`; `const PTR is null` sin tipo produce `E0014`).
- **Ámbito local (`var`/`let`):** Prohibido en el ámbito de nivel superior (`E0002`) para garantizar la seguridad frente al estado global mutable compartido. Los bindings `var` son mutables; los bindings `let` son inmutables.
- **Locales estáticos de función (`static var`):** Se declaran dentro de un weave para mantener un estado local de función persistente entre invocaciones repetidas (§14.5). Se emiten como variables `static` de C con guardas de inicialización única.

#### Reglas y objetivos de la desestructuración (`E0017`):

La desestructuración desempaqueta estructuras compuestas en múltiples bindings locales independientes en una sola sentencia.
- **Structs `rune`:** Desempaqueta los campos en el orden exacto en que se declararon en la definición del `rune`.
- **Arrays fijos (`array of T with size N`):** Vincula los elementos desde el índice `0` hasta `N - 1`.
- **Slices (`slice of T`):** Vincula los elementos mediante indexación del puntero de datos `data[i]`.
- **Listas (`list of T`):** Vincula los elementos secuencialmente mediante `pengu_list_at(&lst, i)`.

> [!WARNING]
> La desestructuración solo se admite en runes, arrays fijos, slices y listas. Intentar desestructurar cualquier otro tipo (escalares, punteros, mapas) o proporcionar un número de bindings que no coincida con la estructura produce `E0017: DestructuringTypeError`.

#### Objetivos de asignación y `set`

`set` reasigna un objetivo mutable. El lado izquierdo de `set` puede ser:
1. Un nombre de variable simple: `set x is 42`
2. Un campo de rune: `set player.hp is 100`
3. Un campo de flecha de puntero: `set self->hp is 80`
4. Un campo con punto de builder: `set .x is 10` (dentro de builders `with:`)
5. Un contenedor indexado: `set items at (i + 1) is new_item`
6. Un puntero desreferenciado: `set essence of ptr is 99`

Intentar asignar a un binding `let` inmutable, a una `const` o a un valor/pointee `frozen` produce `E0006: MutabilityError`.

##### Los bounds se aplican en `set`

Cuando el tipo del objetivo es un **parámetro de tipo desnudo**, el valor asignado debe
satisfacer todos los bounds declarados para ese parámetro (la misma regla que el sitio de llamada
aplica a los argumentos):

```pengu
weave store shard T where T: Num with x as ref to T into void:
    set essence of x is "hello"     # E0005: 'string' does not satisfy 'Num'
    set essence of x is 42          # OK: 'int' implements 'Num'

weave loose shard T with x as ref to T into void:
    set essence of x is "anything"  # OK: an unbounded T is a wildcard
```

La comprobación se aplica igualmente a objetivos de elemento (`set xs at 0 is v` con
`xs as ref to list of T`) y acepta `any`, `null` y otro parámetro de tipo
(esos se resuelven más adelante). Esto cierra la asimetría en la que
`TypeParam.is_compatible(concrete)` respetaba los bounds pero
`concrete.is_compatible(TypeParam)` aceptaba cualquier cosa.

#### Asignación compuesta

`set` también acepta los operadores compuestos `+= -= *= /= %= &= |= ^= <<= >>=`:

```pengu
set counter += 1
set total -= fee
set acc *= factor
set acc /= n
set mask <<= 2
set flags |= 0x08
set text is "{text} suffix"  # strings use interpolation, never '+='
set essence of ptr += 5      # dereference assignment
```

| Operador | Tipos permitidos | Notas |
|---|---|---|
| `+=` | numéricos | `E0005` en `string`: compón con la interpolación `"{expr}"` |
| `-=` `*=` `/=` `%=` | numéricos | `%` es solo para enteros, igual que en `%` |
| `&=` `\|=` `^=` `<<=` `>>=` | enteros | bit a bit/desplazamiento; `E0005` en no enteros |

El lado izquierdo sigue las reglas normales de `set`: debe ser mutable (`E0006` en caso contrario). Los errores de tipo se informan como `E0005`.

### 5.2 Ámbito

Los ámbitos están delimitados por la indentación: cuerpos de weave, ramas `if`/`while`/`for`, bloques `with:`, bloques `or:` y expresiones `do:`. La resolución es léxica; un nombre declarado en un ámbito interno ensombrece a los identificadores externos. `banish`, `defer` y `errdefer` solo se permiten dentro de cuerpos de función (`E0008`).

### 5.3 Resumen de visibilidad

Los símbolos son públicos entre módulos por defecto. Cualquier símbolo de nivel superior o campo de rune que comience con un guion bajo inicial (`_`) es estrictamente privado (`E0043`). No existe la palabra clave `pub`; los guiones bajos iniciales constituyen el único mecanismo de encapsulación.

### 5.4 El modificador `borrowed`

Los locales pueden declararse explícitamente con la palabra clave blanda `borrowed`, con o sin una anotación de tipo explícita:

```pengu
var borrowed view is existing_string
var borrowed count as int is 5
let borrowed slice_view is container_ref
let borrowed tagged as TaggedRef is node_ref
```

- **Referencia sin propiedad:** Una variable marcada como `borrowed` indica que no posee el recurso subyacente del heap.
- **Desactiva el auto-banish:** El compilador nunca emitirá limpieza automática (`pengu_banish_*`) para una variable prestada al salir del ámbito.
- **Prohíbe el banish manual:** Llamar a `banish` sobre una variable `borrowed` es un error semántico en tiempo de compilación (`E0048: BorrowedBanishError`), lo que garantiza que las referencias prestadas no puedan desasignar por accidente la memoria de otro.
- Véase [§13.4](#134-scope-owned-locals-auto-banish) para todos los detalles sobre el modelo de propiedad y análisis de escape.

---

## 6. Operadores y expresiones

### 6.1 Precedencia (de menor a mayor)

1. `or else`, `or return`, bloques `or:`, `try`
2. `or` (booleano, cortocircuito)
3. `and` (booleano, cortocircuito)
4. `judge … when … -> … else -> …`, `if … then … else …` (expresiones), `when … then … else …`
5. comparaciones `== != <= >= < >`, pruebas de palabra `is present`, `is not present`, `is true`, `is false`, pertenencia `in`, `not in`
6. operadores bit a bit `|` `&` `^`
7. desplazamientos `<< >>`
8. aditivos `+ -`
9. multiplicativos `* / %`
10. unarios `~ not -`, `sigil of`, `essence of`, `transmute … to`, `size of`, `banish`, `some`, `ord`, `chr`, `bytes of`
11. postfijos `at`, slicing `at a to b`, `length`, `.field`, `->field`, conversión `to`
12. átomos: literales, `calling`, inicialización `with`/inicialización de struct, contenedores, `defined(…)`, `lambda … into …`

Todo es asociativo por la izquierda. `or` se une con menos fuerza que `and`, por lo que `a or b and c` se evalúa como `a or (b and c)`. `and`/`or` son operadores **booleanos** (con cortocircuito a `&&`/`||` en C); `&`/`|`/`^` son operadores **bit a bit de enteros**.

> [!NOTE]
> **Precedencia del postfijo `at`:** Como `at` se une con más fuerza que la aritmética aditiva (`+` / `-`), las expresiones de indexación con desplazamientos calculados requieren paréntesis:
> ```pengu
> xs at i + 1          # Parsed as (xs at i) + 1 — arithmetic on the retrieved element
> xs at (i + 1)        # The element at computed index i + 1
> set xs at (n - 1) is 77   # Assignment target
> ```
> Omitir los paréntesis (`xs at i + 1` cuando se pretendía calcular el índice) se rechaza como error de sintaxis (`E0000`).

> [!IMPORTANT]
> **Reglas de separación por comas y ambigüedad (`E0005`):**
> Los elementos de una lista en llamadas a funciones, parámetros, literales de array y literales de struct deben separarse con comas (`,`). Cuando `and` aparece directamente después de un argumento o campo de struct (`calling find with 1 and true`), el compilador lo rechaza con `E0005: Ambiguous 'and' after ...` para evitar confusiones con la sintaxis heredada. Pon paréntesis explícitos en las expresiones booleanas: `calling find with (1 and true)`.

### 6.2 Aritmética y bit a bit

```pengu
let z as int is (a + b) * 2 % 7
let f as float is 1.5
let bits as int is (x << 2) | (y & 0x0F)
let neg as bool is not ready
let flip as int is ~mask
```

- **Cadenas (`+` es un error de compilación, `==` está bien):** `+` es **solo numérico**. La composición de cadenas tiene exactamente una forma: la interpolación `"{expr}"` dentro de un literal de cadena (§15.2). `"a" + b` produce `E0005`; no hay promoción implícita `to string` ni temporal oculto. La igualdad `a == b` emite `pengu_string_equal(a, b)` (igualdad de contenido por valor, sin reserva de memoria).
- **Cortocircuito lógico (`and` / `or`):** Los operandos deben ser estrictamente `bool` (`E0005` en caso contrario). `or` evalúa su operando derecho solo si el izquierdo es `false`; `and` evalúa su operando derecho solo si el izquierdo es `true`.
  > **Nota sobre cortocircuito vs semántica de fallback:** `or` y `and` son exclusivamente operadores lógicos booleanos (`bool and bool -> bool`), no operadores de coalescencia o fallback de valores. Para desempaquetar un opcional o resultado con un valor por defecto, usa `or else` (p. ej. `val or else default`, §12) o un bloque `or:` (§12). Las expresiones de indexación en arrays/listas (`at`) bajo modo debug realizan comprobaciones de límites estrictas que abortan si el índice está fuera de rango; no deben protegerse con operadores lógicos sin una comprobación explícita con `if` o métodos de acceso seguro.


### 6.3 Comparación, pertenencia y pruebas de palabra

```pengu
if x > 0: ...
if m is present: ...          # m must be 'maybe T'; anything else is E0005
unless m is present: ...
if b is true: ...             # b must be 'bool'
if ch in "aeiou": ...         # uses strchr for char, strstr for string
if key in my_map: ...         # uses pengu_map_get
if p == null: ...             # valid for any pointer/opaque type
```

- **Pertenencia (`in` / `not in`):**
  - **Cadenas:** Si se busca un `char`, emite `strchr`. Si se busca un `string`, emite `strstr`.
  - **Mapas:** Emite `pengu_map_get(&map, key)` para comprobar la pertenencia de la clave.
  - **Rangos:** Comprueba el rango semiabierto `a <= x and x < b`.
- **Comparaciones de cadenas:** La igualdad (`==`, `!=`) se admite mediante `pengu_string_equal`. La ordenación relacional (`<`, `<=`, `>`, `>=`) sobre `string` **no se admite** (`E0005`) porque `PenguString` es un struct; usa comparaciones de caracteres o `std.scrolls.compare`.
- **Pruebas de palabra (`is present`, `is true`):**
  - `is present` e `is not present` son válidas **solo sobre `maybe T`**. Aplicarlas a `result of T to E` es `E0005` (usa `.is_ok` en los resultados).
  - `is true` e `is false` requieren un operando `bool` (`E0005` en caso contrario).
  - En posiciones de argumento de llamada, las palabras clave de prueba deben ir entre paréntesis (`calling print_bool with (m is present)`), porque `_reject_test_argument` prohíbe las pruebas sin paréntesis para evitar ambigüedades sintácticas.
- **Comparaciones con `null`:** Comparar `p == null` o `p != null` es válido para todos los tipos de puntero (`ref to T`, `ref to void`, `opaque`). Comparar `null` contra tipos que no son punteros (como `int == null`) produce `E0005`.

### 6.4 Dirección, desreferencia y tamaño

```pengu
var p as ref to int is sigil of x     # &x
var v as int is essence of p          # *p
set essence of p is 42                # *p = 42 (LHS of assignment)
let n as usize is size of MyRune      # sizeof(MyRune)
let raw_ptr as ref to void is transmute p to ref to void   # unsafe bit-cast
```

- **`sigil of expr` (`&`):** Toma la dirección de un lvalue. No puede aplicarse a literales, expresiones, `const` ni variables `frozen` (`E0008: InvalidMemoryOpError`).
- **`essence of expr` (`*`):** Desreferencia un puntero. El operando debe ser un `ref to T` o `Any`. Puede usarse tanto como rvalue como objetivo del lado izquierdo de una asignación `set` (`set essence of ptr is val`).
- **`size of TYPE`:** Evalúa el tamaño en bytes en tiempo de compilación de cualquier tipo (`sizeof(T)` en C) y devuelve `usize`.
- **`transmute expr to TYPE`:** Conversión insegura de reinterpretación a nivel de bits. Siempre dispara la advertencia del compilador `[W0001] transmute is unsafe`. Si los tipos de origen y destino tienen tamaños estimados diferentes, `W0001` incluye una notificación de discrepancia de tamaño. Las conversiones seguras deben usar `(expr to TYPE)`.

### 6.5 Primitivas de carácter y byte

```pengu
let code as int is ord "A"            # 65
let empty_code as int is ord ""       # 0
let ch as string is chr 66            # "B" (single-character string)
let raw_str as ref to frozen byte is bytes of my_string   # read-only view
let raw_arr as ref to byte is bytes of byte_array         # writable view
```

- **`ord expr`:** Convierte una cadena de un solo carácter o un literal char a su valor entero ASCII. Los literales de varios caracteres producen `E0005`. La cadena vacía `ord ""` se evalúa como `0`.
- **`chr expr`:** Convierte un código de byte entero (0–255) en un `PenguString` de un solo carácter.
- **`bytes of expr`:** Toma prestado un puntero a byte:
  - Si se aplica a `string`: devuelve `ref to frozen byte` (vista de solo lectura del búfer de caracteres de la cadena).
  - Si se aplica a `array of byte with size N`: devuelve `ref to byte` (puntero de escritura).
  - Aplicar `bytes of` a otros tipos produce `E0005`.

### 6.6 Constructores de `maybe` y contexto de `null`

```pengu
var m as maybe int is some 42         # boxes 42 into a PenguMaybe heap cell
var n as maybe int is maybe none      # empty optional
var p as ref to int is null           # null pointer
```

- **Boxing con `some expr`:** Evalúa `expr` y lo copia en una celda reservada en el heap mediante `pengu_sigil_alloc(sizeof(T))`:
  ```c
  /* Generated C for: some 42 */
  int32_t _some_1 = 42;
  PenguMaybe _maybe_2;
  _maybe_2.is_present = true;
  _maybe_2.value = pengu_sigil_alloc(sizeof(_some_1));
  if (!_maybe_2.value) _maybe_2.is_present = false;
  else memcpy(_maybe_2.value, &(_some_1), sizeof(_some_1));
  ```
- **Lowering de `maybe none`:** `maybe none` se traduce a la llamada de runtime `pengu_maybe_none()`, que devuelve un `PenguMaybe` vacío con `.is_present = false` y `.value = NULL`.
- **Requisito de contexto para `maybe none` y `null` (`E0014`):**
  Ni `maybe none` ni `null` tienen un tipo inherente. Requieren un contexto de tipo esperado (como una anotación de tipo explícita de variable `var m as maybe int is maybe none` o `var p as ref to int is null`). Inicializar una variable sin anotación con `maybe none` o `null` produce `E0014: TypeMismatchError`.
- **Variable `error` en `or:`:** Dentro de un bloque `or:`, los detalles del fallo se vinculan a la variable de ámbito `error` (tipo `string` para `maybe T`, o el tipo de error `E` para `result of T to E`). Acceder a `error` fuera de un bloque `or:` es un error (`E0015`).
- **`null` y parámetros genéricos (limitación conocida):** `null` se acepta donde se espera un parámetro de tipo *desnudo*, sean cuales sean sus bounds, porque un `T` sin bounds puede instanciarse con un puntero. Endurecer esto (`T: Num` rechazando `null`) se deja deliberadamente permisivo por compatibilidad hacia atrás; las conversiones se comprueban con normalidad.

---

## 7. Flujo de control

### 7.1 `if` / `unless` (sentencias) y expresiones `if`

```pengu
if score >= 100:
    calling print with "winner"
else:
    calling print with "keep going"

unless muted:
    calling play_sound with "beep"

let label as string is if x > 10 then "big" else "small"
```

`unless cond:` es equivalente a `if not cond:`. Las condiciones deben evaluarse a `bool` (`E0005` en caso contrario). Las ramas con condiciones constantes en tiempo de compilación se pliegan y la rama inalcanzable se elimina (advertencia `[W0004]` para código inalcanzable).

#### Bindings de `if`: `if v as T is <maybe>:`

Una condición `if` puede vincular de forma segura el valor contenido en un `maybe T` sin un unwrap explícito:

```pengu
weave describe with user as maybe User into string:
    if u as User is user:               # u is User inside the branch
        return u.name
    else:
        return "anonymous"
```

- El operando debe ser `maybe T` (`E0005` en caso contrario).
- `T` debe coincidir con el tipo de elemento del contenedor maybe.
- También funciona en posición de valor: `let label is if u as User is user: u.name else: "anonymous"`.
- Se traduce a un bloque C con ámbito que comprueba `pengu_maybe_is_present(&tmp)` una vez y extrae el valor; el identificador vinculado no se filtra a la rama `else` ni al ámbito externo.

#### Sentencias de una sola línea (`simple_stmt`)

Un bloque o rama de flujo de control puede contener una única sentencia en la misma línea que sigue a los dos puntos (`:`):

```pengu
if x == 1: return 1
unless x == 0: calling print with "non-zero"
while i < n: set i is i + 1
for j from 0 to 3: calling tick with j
```

Las formas de sentencia permitidas en la misma línea que los dos puntos (`simple_stmt`) son: `continue`, `break`, `return [expr]`, `set target is expr`, `set target OP expr` y cualquier expresión general (como `calling fn(...)`). Las declaraciones, los bloques, `defer`, `errdefer` y `banish` no pueden escribirse en la misma línea que los dos puntos.

### 7.2 `while`

```pengu
var i as int is 0
while i < 10:
    calling tick with i
    set i is i + 1
```

### 7.3 `for`

```pengu
for i from 0 to 10:            # integer range [0, 10), end-exclusive
    calling print with (i to string)

for item in items:             # array / list / slice / string / map iteration
    calling handle with item

for i, item in indexed:        # indexed form (i is iteration counter)
for _, v in values:            # discard index
for j from 5 to 0 step -1:     # negative step
```

- **Validación de bindings de bucle (`E0037`):** En la forma indexada `for i, v in col`, el identificador de índice `i` y el identificador de elemento `v` deben ser distintos. Usar el mismo nombre de identificador para ambos produce `E0037`. El comodín `_` puede usarse para descartar cualquiera de los dos bindings.
- **Iteración sobre cadenas:** Iterar sobre una cadena (`for ch in "abc":`) produce cada carácter como un `PenguString` de un solo carácter mediante `pengu_string_char_at`.
- **Iteración sobre mapas:** Iterar sobre un mapa (`for k in my_map` o `for i, k in my_map`) itera sobre las claves. El codegen recorre el array interno de la tabla hash (`entries[slot]`), comprobando `entries[slot].occupied`. **El orden de iteración es el orden de hash**, no el orden de inserción. En la forma indexada, `i` se incrementa solo cuando se visita una ranura ocupada.

#### Comprehensions (`for_comp`)

Las list comprehensions producen un nuevo `list of T` evaluando una expresión sobre un iterable:

```pengu
let squares is for x in nums then x * x
let evens  is for x in nums when x % 2 == 0 then x
```

- **Sintaxis:** `for item in col [when condition] then expr`. Las comprehensions en línea vinculan una única variable de elemento `item` (la forma indexada `i, item` no se admite en comprehensions en línea; usa un bloque de bucle `for` en posición de valor para colecciones indexadas). Los tipos de colección admitidos incluyen arrays fijos (`array of T`), slices (`slice of T`), listas dinámicas (`list of T`), rangos (`a to b`) y mapas (`map of K to V`, que itera sobre las claves activas en orden de hash).
- **Lowering del codegen:** Se evalúa como una statement-expression de GNU que reserva un `PenguList`:
  ```c
  (__extension__({
    PenguList _comp_list = pengu_list_new(sizeof(T));
    /* loop over col */
    if (condition) {
      T _val = expr;
      pengu_list_push(&_comp_list, &_val);
    }
    _comp_list;
  }))
  ```

### 7.4 `judge` — coincidencia de patrones

```pengu
let state_desc is judge state:
    when Ready -> "ready"
    when Loading -> "loading"
    when Done -> "done"
    else -> "unknown"
```

- **Sujetos admitidos:** variantes de `omen`, `bool`, `int`, `string` y `char`.
- **Formas de patrón:**
  - Nombre de variante desnudo: `when Ready ->`
  - Nombre de variante con punto: `when Phase.Ready ->`
  - Nombre C completo: `when Phase_Ready ->`
  - Literales: `when 42 ->`, `when "admin" ->`, `when 'X' ->`
  - Valor por defecto de reserva: `else -> <expr>`
- **Reglas de exhaustividad (`E0044`):**
  - Para sujetos `omen` y `bool`, deben cubrirse todas las variantes/valores posibles a menos que se proporcione una cláusula `else ->` por defecto. Las ramas faltantes producen `E0044: NonExhaustiveJudgeError`.
  - Para `int`, `string` y `char`, no se exige exhaustividad. Si no hay `else ->` y ningún patrón coincide, la expresión se evalúa a su valor cero/vacío por defecto (`0`, `""`, `'\0'`).
- **Cargas útiles de patrón (`with <campos>`):** Extrae los campos de la variante directamente en variables locales dentro del cuerpo de la cláusula:
  ```pengu
  judge status:
      when Status.Ok with value -> value + 1
      when Status.Err with code -> code
  ```
- **Guardas (`if <cond>` / `when <cond>`):** Filtra ramas del patrón usando expresiones booleanas evaluadas con las variables extraídas en el alcance local:
  ```pengu
  judge number:
      when Number.Val with n if n > 0 -> "positivo"
      when Number.Val with n if n < 0 -> "negativo"
      when Number.Val with n -> "cero"
  ```
  Los patrones con guarda no cuentan para la exhaustividad; se requiere un patrón sin guarda o una cláusula `else ->`.
- **Codegen:** Emite una sentencia `switch` de C cuando todos los casos de patrón son constantes enteras en tiempo de compilación sin guardas ni cargas útiles; genera ramas `if` estructuradas con extracción de carga útil y evaluación de guardas cuando hay cargas útiles o guardas, o recurre a una cadena ternaria `if-else` para patrones de cadena o variables.

### 7.5 `break` / `continue` / `return`

Sentencias de control de flujo estándar. `break` y `continue` solo se permiten dentro de bloques de bucle (`E0007`). `return` debe producir un tipo que coincida con la especificación `into` del weave contenedor (`E0020`); un `return` desnudo solo es válido en weaves `void`.

### 7.6 Expresiones de bloque: `do:`, `if` / `unless` en posición de valor y bucles

Cualquier bloque indentado puede evaluarse a un valor cuando se coloca en posición de valor:

```pengu
let x is do:                      # evaluates to its last statement's value
    var a is 10
    set a is a + 5
    a * 2                         # x == 30

let status is if score >= 100:    # if in value position
    let msg is "winner"
    msg
else:
    let msg is "keep going"
    msg

let squares as list of int is for i from 0 to 5:
    i * i                         # collects each iteration value into a list
```

- **Expresión `do:`:** Ejecuta sentencias en un ámbito léxico nuevo. El valor de `do:` es el valor de su sentencia de expresión final. Se traduce a la statement-expression de GCC `__extension__(({ <stmts>; <last_expr>; }))`.
- **`if` / `unless` en posición de valor:** Cada rama debe concluir con una expresión que comparta un tipo común (`E0005` si no coinciden). Se traduce a:
  ```c
  __extension__(({
    T _if_1;
    if (cond) { ... _if_1 = then_expr; }
    else { ... _if_1 = else_expr; }
    _if_1;
  }))
  ```
- **Bucles en posición de valor:** Los bucles (`while`, `for i from ... to ...`, `for x in col`) colocados en posición de valor recogen el valor final de cada iteración en un `list of T` recién reservado.
- **Sentencias finales válidas (`_check_block_value_stmt`):** La sentencia final de un bloque de valor determina el valor resultante del bloque. El compilador reconoce:
  1. `if_stmt` / `unless_stmt`: Se comprueban recursivamente en posición de valor, lo que permite ramificaciones anidadas.
  2. `while_stmt` / `for_range_stmt` / `for_in_stmt`: Se evalúan como bucles recolectores, produciendo un `list of T`.
  3. `do_expr`: Bloque de valor léxico anidado.
  4. `with_init_expr`: Bloque builder final, que infiere su tipo a partir de la ranura de valor contenedora.
  5. Cualquier expresión estándar o sentencia de llamada.
- **Protocolo del checker (`_pengu_value_type`):** El checker semántico adjunta `_pengu_value_type` a los nodos del AST situados en ranuras de valor. El codegen inspecciona estos metadatos para seleccionar la emisión de statement-expressions.
- **Protección del análisis de escape (`_exclude_escaping_val_from_banish`):** Los valores que salen de una expresión de bloque se excluyen explícitamente del auto-banish para evitar bugs de use-after-free.

> [!NOTE]
> CHEATSHEET §6.1.4 tiene la lista definitiva de lo que es y no es una expresión. Las operaciones de control a nivel de sentencia (como un `break` desnudo sin valor, o las declaraciones) no pueden servir como valores finales de bloque.

---

## 8. Funciones

### 8.1 `weave` — funciones

```pengu
weave greet with name as string, times as int is 1 into void:
    for i from 0 to times:
        calling print with "Hi {name}"

weave double with x as int into int:
    return x * 2
```

- **Parámetros y valores por defecto:** Los parámetros pueden especificar valores por defecto (`times as int is 1`). Las expresiones por defecto deben ser constantes en tiempo de compilación.
- **Return implícito:** Un cuerpo de función cuya última sentencia es una expresión devuelve implícitamente ese valor sin necesidad de un `return` explícito.
- **Sintaxis de llamada:**
  - Argumentos posicionales: `calling greet with "Ada", 3`
  - Argumentos con nombre: `calling greet with name is "Ada", times is 2`
  - Miembro de módulo: `calling spark.println with "Hello"`
  - Método de objeto: `calling player.move with 5, 3`
- **Requisito de paréntesis:** La lista de argumentos que sigue a `with` es voraz. Cuando una llamada está anidada dentro de una expresión aritmética o una comparación, envuelve la llamada en paréntesis: `(calling get_count) > 0`.
- **Diagnósticos de llamada y códigos de error:**
  - `E0004`: Miembro de módulo no encontrado (`Module 'X' has no exported member 'Y'`), o función C externa llamada sin un `declare` correspondiente.
  - `E0018`: Discrepancia de argumento en el push de `list of T` (`List of T push expects T, got U`).
  - `E0034: InvalidRitualCallError`: Intentar llamar a un método `ritual` (estático) sobre un objeto instancia, o llamar a un método de instancia sobre un nombre de tipo.
  - `E0043: PrivateSymbolAccessError`: Llamar a una función privada (con prefijo `_`) desde fuera de su módulo de definición.
  - `E0045`: `try` usado dentro de una función cuyo tipo de retorno es incompatible con el fallo desempaquetado.

#### Heurística de inlining automático (`inline`)

Las funciones pueden declararse explícitamente con el modificador `inline`: `inline weave fast_calc ...`. Además, el checker semántico (`_check_weave_decl`) marca automáticamente las funciones pequeñas como `is_inline = True` cuando:
1. El cuerpo de la función contiene 3 sentencias o menos (`len(stmt_children) <= 3`), o el recuento total de nodos del AST es 25 o menos (`node_count <= 25`).
2. La función **no contiene bucles** (`while`, `for i from ...`, `for item in ...`).
3. La función **no contiene variables estáticas** (`static var`).

Para todas las funciones inlineadas, el generador de código emite `static inline __attribute__((always_inline))` tanto en el prototipo forward como en la implementación C, eliminando la sobrecarga de llamada a función en código crítico para el rendimiento.

#### Envoltorio del punto de entrada (`pengu_main`)

El punto de entrada del usuario debe llamarse `main` (`weave main into int:` o `into void:`). El compilador genera la función C `pengu_main`, envuelta por un `main` estándar del runtime de C:

```c
/* Generated C runtime entry point wrapper */
int main(int argc, char** argv) {
    pengu_init(argc, argv);
    int pengu_status = (int)pengu_main();
    fflush(stdout);
    fflush(stderr);
    return pengu_status;
}
```

Este envoltorio automático inicializa los argumentos del runtime, los expone a `std.rites.get_args()`, ejecuta `pengu_main()`, vacía los búferes de E/S estándar y devuelve el código de estado de salida.

### 8.2 `declare` — funciones C externas

```pengu
declare pengu_print with s as string into void
declare strlen_c with s as ref to char into usize
declare my_callback with cb as ref to weave with x as int into void into void
declare printf with fmt as ref to frozen char, ... into int     # C varargs
```

`declare` registra prototipos de funciones C externas para que las llamadas se traduzcan directamente a invocaciones nativas de C sin envoltorios de glue.

#### Funciones variádicas de C (`...` vs `many T`)

Un `...` final en una lista de parámetros de `declare` representa argumentos variádicos crudos de C (`CVarArgsType`):
- **Parámetros fijos:** Se comprueban estrictamente según sus tipos declarados.
- **Argumentos variádicos:** Los argumentos extra se pasan **tal cual** a C. No se produce empaquetado en `PenguSlice` ni boxing de runtime; se aplican directamente las promociones de argumentos por defecto de C.
- **Distinción respecto de `many T`:** `many T` es el mecanismo variádico seguro de PenguScript, respaldado por slices, para funciones `weave`. `...` está reservado exclusivamente para firmas `declare` de C externas.
- **Modificadores:** `declare` también puede combinarse con los modificadores `inline` o `ritual`.

### 8.3 Punteros a función y callbacks

Un valor de función tiene tipo `weave … into …` (`FnType`). En C, los identificadores de función decaen sin problemas a punteros a función. Tanto `weave with … into …` como `ref to weave with … into …` son totalmente intercambiables:

```pengu
alias Handler as weave with x as int into void

weave handler with x as int into void:
    return

weave main into void:
    var cb as ref to weave with x as int into void is handler   # function decay
    calling register_cb with handler                            # passes C callback
    calling cb with 1                                           # calls through pointer
```

- **Decaimiento de callback a `void*`:** Cualquier identificador de `weave` o lambda puede pasarse donde se espera `ref to void` o `ref to frozen void` (habitual en APIs de C que reciben punteros de callback `void* user_data`).
- **Conversión de callbacks:** El compilador emite automáticamente conversiones explícitas de punteros a función (p. ej. `((AudioCallback)on_audio)`) para satisfacer a los compiladores estrictos de C99/C11 (como GCC 14+).

### 8.4 Lambdas

Las funciones anónimas en línea se declaran con `lambda`, parámetros tipados separados por comas y una expresión `into`:

```pengu
let no_args as weave into int is lambda into 42
let double as weave with x as int into int is lambda x as int into x * 2
let add as weave with a as int, b as int into int is lambda a as int, b as int into a + b
```

- **Tipos de parámetro y retorno:** Los parámetros de las lambdas requieren anotaciones de tipo explícitas. El tipo de retorno se infiere automáticamente a partir de la expresión del cuerpo.
- **Sin closures / funciones estáticas:** Las lambdas no capturan variables locales del entorno. Solo pueden acceder a sus propios parámetros y a las constantes, tipos y weaves de nivel de módulo.
- **Codegen:** Las lambdas se prescanean y se emiten como funciones C `static` de nivel superior llamadas `_pengu_lambda_1`, `_pengu_lambda_2`, etc. En el sitio de llamada, la lambda se evalúa a la dirección de la función estática.
- **Seguimiento de la pila de llamadas en runtime:** Las funciones lambda participan en el búfer circular de 64 frames del runtime emitiendo `pengu_frame_push("_pengu_lambda_N", file, line)` y `pengu_frame_pop()`, lo que garantiza que los pánicos y las señales de fallo fatal originados dentro de lambdas informen con precisión de su línea de origen.

### 8.5 Métodos `ritual` (estáticos)

```pengu
enchanting Vec2:
    weave ritual zero into Vec2:
        return with x is 0.0, y is 0.0

    weave length_sq into float:
        return self->x * self->x + self->y * self->y

weave main into int:
    var origin as Vec2 is calling Vec2.zero     # called on TYPE
    var l as float is calling origin.length_sq  # called on INSTANCE
    return 0
```

- Los métodos `ritual` son funciones asociadas (métodos estáticos) que pertenecen a un espacio de nombres de tipo. No tienen parámetro `self`. Referenciar `self` dentro de un `ritual` produce `E0033: InvalidRitualSelfAccessError`.
- Llamar a un método `ritual` sobre un objeto instancia, o llamar a un método de instancia sobre un nombre de tipo, produce `E0034: InvalidRitualCallError`.

---

## 9. Tipos compuestos

### 9.1 `rune` — structs

```pengu
rune Player:
    name as string
    hp as int
    is_alive as bool
    _secret_id as int                    # private field (E0043 outside rune)
```

Construcción:

```pengu
var p as Player is with name is "Hero", hp is 100, is_alive is true
var q as Player with:                        # block form, see §18
    set .name is "Villain"
    set .hp is 50

# Nested construction:
var hero as Person with:
    set .name is "Ada"
    set .age is 30
    set .address is with:
        set .street is "123 Main St"
        set .city is "New York"
        set .zip is "12345"
```

- **Disposición:** Las runes se corresponden 1:1 con structs de C, preservando la disposición exacta de memoria y la alineación de campos a través de los límites de C FFI.
- **Acceso a campos:** El acceso directo usa `p.name`; el acceso a través de una referencia `ref to Player` usa la sintaxis de flecha para punteros `p->name` (`E0003` si se usa el punto sobre una referencia).
- **Encapsulación (`E0043`):** Los campos con un guion bajo inicial (p. ej. `_secret_id`) son estrictamente privados de la rune que los define. Intentar acceder o asignar un campo privado mediante punto (`p._secret_id`) o flecha de puntero (`p->_secret_id`) desde fuera de la definición de la rune o de su módulo propietario provoca `E0043: PrivateSymbolAccessError`.
- **Desestructuración:** Las runes pueden desempaquetarse en variables locales mediante declaraciones de desestructuración: `let (n, h, a) is p` (§5.1).

#### 9.1.1 `cyclus` — tipos autorreferenciales

Por defecto, un tipo que se contiene a sí mismo **por valor** tiene tamaño infinito y se rechaza con `E0050`:

```pengu
rune Bad:
    next as Bad          # E0050: infinite type size
```

`cyclus` declara explícitamente que la declaración es intencionadamente autorreferencial; el ciclo debe romperse igualmente mediante indirección de puntero (`ref to`, `maybe ref to`, `slice`, `list`, `map`):

```pengu
rune Node cyclus shard T:
    value as T
    next as maybe ref to Node of T      # OK: indirection breaks the cycle
```

`cyclus` es documentación-como-sintaxis: **no** hace legal un ciclo por valor (eso seguiría produciendo un struct de C que se contiene a sí mismo), solo marca las declaraciones recursivas para que los lectores y las herramientas sepan que la recursión es intencionada.

#### 9.1.2 `derive` — implementaciones automáticas de conceptos

`derive` pide al compilador que genere los helpers de C para un concepto integrado a partir de los campos de la rune:

```pengu
rune Point derive Par, Ordo, Vinculum, Imago:
    x as int
    y as int
```

| Concepto | C generado | Habilita |
|---|---|---|
| `Par` | `<Rune>_eq`, `<Rune>_eq_val`, `<Rune>_Par` | `==`, `!=` |
| `Ordo` | `<Rune>_cmp`, `<Rune>_cmp_val`, `<Rune>_Ordo` | `<`, `<=`, `>`, `>=` |
| `Vinculum` | `<Rune>_Vinculum`, `<Rune>_hash` | rune como clave de `map` |
| `Imago` | `<Rune>_clone`, `_pengu_clone_<Rune>` | copia profunda hacia contenedores |
| `Nexus` | `<Rune>_nexus`, `_pengu_cleanup_<Rune>` | liberación recursiva |

Reglas:

* Solo `Par`, `Ordo`, `Vinculum`, `Imago` y `Nexus` son derivables; cualquier otra cosa provoca `E0005`.
* Cada campo debe implementar a su vez el concepto derivado, de lo contrario `E0032` señala el campo problemático.
* En una rune genérica, los conceptos derivados se convierten en **bounds sobre los parámetros de tipo**: `rune Point shard T derive Par` implica `T: Par` en los helpers generados.
* `Imago` y `Nexus` se implican mutuamente: un contenedor que copia en profundidad sus elementos también debe poder liberarlos, así que `derive Imago` también genera (y registra) `Nexus`, y viceversa.
* La comparación sobre una rune sin el `derive` correspondiente es `E0049`; sin él, el C generado llamaría a un helper que no existe.
* `derive` se rechaza con `E0005` en declaraciones `echo`: un `echo` es una unión de C sin etiqueta, por lo que la igualdad, el orden o el hashing leerían memoria que la última escritura no inicializó. Usa un `omen` algebraico (§9.3) o implementa el concepto explícitamente con `bind` (§10.3).
* Los omens algebraicos son structs etiquetados y admiten la misma cláusula `derive` en sus variantes con payload (solo se inspecciona el payload de la variante activa). Una variante sin payload puede usarse como valor (`var s as Shape is Point`) o en una comparación (`s == Point`), no solo como patrón de `judge`.
* Un valor con un `Nexus` derivado puede liberarse explícitamente — `banish doc` se reduce a `_pengu_cleanup_Doc(&doc)` (idempotente: los helpers de banish del runtime ponen a null los buffers que liberan), así que `defer banish doc` es el idioma para un local cuyos campos poseen memoria del heap. Los valores *rune* locales **no** se banishan automáticamente (eso requeriría un análisis de move/alias para evitar dobles frees), así que libéralos explícitamente o guárdalos en un contenedor que los posea.

### 9.2 `echo` — uniones

```pengu
echo Number:
    i as int
    f as float
```

Un `echo` compila directamente a una `union` de C. Acceder a cualquier campo de una unión `echo` activa el warning del compilador `[W0002] Echo union access is unsafe`, porque los campos de la unión comparten memoria sin una etiqueta discriminante automática. Para tipos suma seguros en cuanto a tipos, prefiere los `omen` algebraicos.

### 9.3 `omen` — enums, omens con valor de string y tipos suma algebraicos

PenguScript ofrece tres sabores distintos de `omen`:

```pengu
# 1. Numeric Enum (simple C enum)
omen Direction:
    North is 0
    South is 1
    East is 2
    West is 3

# 2. String-Valued Omen
omen Color with string:
    Red
    Green
    Blue

# 3. Algebraic Data Type (Sum Type with Payloads)
omen NetworkEvent:
    Disconnected
    Connecting with attempt as int
    Connected with session_id as string, latency_ms as float
```

#### Omens con valor de string (`omen X with string:`):
- Se declaran con `with string:` después del nombre del omen.
- Cada variante evalúa a un `PenguString` que contiene su propio nombre de variante (`Red` -> `"Red"`).
- **No se permiten payloads:** Las variantes de un omen con valor de string no pueden declarar payloads; añadir `with` a una variante provoca `E0028: InvalidOmenPayloadValueError`.
- **Codegen:** Emite `#define <Omen>_<variant> pengu_string_from_cstr("<variant>")`. En las expresiones, `Color.Red` o `Red` producen un `string` inmutable.

#### Modos de emisión del codegen:
- **Omen numérico normal en `.pengu`:** Emite un `typedef enum { <Omen>_<variant> = val, ... } <Omen>;` de C.
- **Omen de declaración en `.d.pengu`:** Emite **nombres de variante desnudos** (`KEY_LEFT`, `FLAG_MSAA_4X_HINT`) que coinciden con los enums de los headers de C originales, sin añadir prefijo.
- **Modo con prefijo de `insignia` (`c_name != name`):** Cuando el módulo especifica una directiva `insignia <prefix>`, el tipo enum de C generado recibe el prefijo (`<c_name>`, p. ej. `ray_Color`), y todas las etiquetas enum de variantes se generan como `<c_name>_<variant>` (p. ej. `ray_Color_Red`), evitando colisiones de nombres en C entre compilaciones multimódulo.
- **Omen con valor de string:** Emite definiciones de constantes de string (`#define <c_name>_<variant> pengu_string_from_cstr("<variant>")`).
- **Omen algebraico:** Emite un struct de C etiquetado que contiene una etiqueta discriminante (`<c_name>_Tag`) y una unión de payload:
  ```c
  typedef struct {
      int32_t tag;
      union {
          struct { int32_t attempt; } Connecting;
          struct { PenguString session_id; float latency_ms; } Connected;
      } data;
  } NetworkEvent;
  ```

#### Invariantes y validación de omens:
- Los nombres de variante simples pueden referenciarse directamente (`Red`) o cualificados (`Color.Red`, `Color_Red`).
- Los valores de variante duplicados provocan `E0027: DuplicateOmenValueError`.
- Los valores de variante deben ser constantes enteras de tiempo de compilación (`E0029`).
- Si los nombres de variante colisionan entre distintos omens del mismo módulo, las referencias sin cualificar provocan `E0046`, lo que exige cualificarlas explícitamente.

### 9.4 `seal`, `alias`, `opaque`

```pengu
seal UserId as int          # distinct nominal type: needs explicit `to` casts
alias Inches as int         # transparent structural alias: interchangeable
alias Buffer as opaque      # C opaque pointer handle (used behind `ref to`)
```

- **`alias` (estructural):** Un sinónimo puro de otro tipo. Supera todas las comprobaciones de tipos de forma intercambiable (`AliasType.is_compatible` es transparente).
- **`seal` (nominal):** Un newtype fuerte que envuelve una representación subyacente. Prohíbe la asignación implícita hacia o desde el tipo subyacente. El casting requiere una conversión explícita: `var id as UserId is (raw_id to UserId)`.
- **`opaque` (handles):** Representa tipos incompletos de C. La instanciación directa por valor está prohibida (`E0012: Cannot instantiate opaque type`). Los tipos opacos deben manipularse a través de punteros: `ref to Buffer`.

### 9.5 `frozen` — cualificación de solo lectura

`frozen` es el `const` de C: marca un valor o un pointee como no escribible. Es ortogonal a `let`/`var`, que controlan si el **nombre** puede reasignarse.

```pengu
frozen int                      # const int
ref to frozen int               # const int*
frozen ref to int               # alias of 'ref to frozen int'
frozen Player                   # const Player
ref to frozen void              # const void*   ← what qsort asks for
```

`frozen` es una palabra clave **suave**: solo es especial en posición de tipo, así que una variable, un campo o un weave llamado `frozen` sigue funcionando.

#### Asignación y compatibilidad direccional

Un valor mutable fluye hacia `frozen` (como en C); lo contrario no:

```pengu
var x as int is 5
set x is 6                      # OK

var y as frozen int is x        # OK: 'y' is a read-only copy
# set y is 7                    # E0006: cannot write through 'frozen'
```

- **Aplicación de `_drops_frozen()`:** El chequeador semántico prohíbe estrictamente eliminar el cualificador `frozen` (`frozen -> mutable` provoca `E0005: TypeMismatchError`).
- **Protección del pointee (`_frozen_write_block`):** Escribir a través de un puntero a un pointee frozen (`ref to frozen T`) se rechaza:
  - Asignar un campo con flecha: `set p->x is 1` provoca `E0006`.
  - Asignar un elemento por índice: `set p at i is 1` provoca `E0006`.
  - Asignar la desreferencia de un puntero: `set essence of p is 1` provoca `E0006`.
- **Normalización de punteros:** `frozen ref to T` se normaliza en `ast_to_type` a `ref to frozen T` (constancia del pointee). PenguScript nunca emite `T* const`.
- **Punteros comodín:** `ref to void` y `ref to frozen void` aceptan cualquier tipo de puntero, lo que habilita la interoperabilidad universal con APIs de C.

#### Uso en la interoperabilidad con C

`frozen` existe para describir firmas de C que llevan `const`. Ejemplo completo de `qsort` (salida ordenada: `1 2 3`):

```pengu
include "stdlib.h"

declare qsort with base as ref to void, nmemb as usize, size as usize, compar as ref to weave with a as ref to frozen void, b as ref to frozen void into int into void

weave compare_ints with a as ref to frozen void, b as ref to frozen void into int:
    let xa is essence of (transmute a to ref to frozen int)
    let xb is essence of (transmute b to ref to frozen int)
    if xa < xb:
        return -1
    if xa > xb:
        return 1
    return 0

weave main into int:
    var xs as array of int with size 3 is [3, 1, 2]
    calling qsort with xs, 3, (size of int), compare_ints
    var i as int is 0
    while i < 3:
        calling spark.println with ((xs at i) to string)
        set i is i + 1
    return 0
```

C generado:

```c
int32_t compare_ints(const void* a, const void* b);          /* prototype */

int32_t compare_ints(const void* restrict a, const void* restrict b) {
  const int32_t xa = (*(((const int32_t*)(a))));
  const int32_t xb = (*(((const int32_t*)(b))));
  if ((xa < xb)) { return -1; }
  if ((xa > xb)) { return 1; }
  return 0;
}

int32_t pengu_main(void) {
  int32_t xs[3] = { 3, 1, 2 }; /* stack */
  qsort(xs, 3, (sizeof(int32_t)), ((int32_t (*)(const void*, const void*))compare_ints));
  for (int32_t i = 0; i < 3; i++) { spark_println((pengu_to_string((xs[i])))); }
  return 0;
}
```

Sin `frozen`, el callback se declararía `int32_t (*)(void*, void*)`, y GCC 14+ rechaza entregárselo a `qsort` (cualificadores distintos). Con `frozen`, la firma de Pengu coincide con el prototipo de C y el cast de puntero a función es legal. (`restrict` en un parámetro no afecta a la compatibilidad de tipos; el argumento de array decae a puntero como en C.)

`void` es el puntero comodín a objeto que es en C, así que `ref to void` y `ref to frozen void` aceptan un puntero a cualquier cosa — mutable o frozen —, un array (decay) y un *literal* de string de C (`char*` → `const void*`), que se emite como un literal de C:

```pengu
declare UpdateTexture with texture as Texture2D, pixels as ref to frozen void into void
declare XXH64 with input as ref to frozen void, length as usize, seed as u64 into u64

calling UpdateTexture with tex, sigil of pixels     # any T*
var h as u64 is calling XXH64 with "PenguScript", 11, 0
```

Lejos de `void`, el cualificador sigue decayendo en una sola dirección: `ref to frozen int` donde se espera `ref to int` es `E0005`.

> [!NOTE]
> `frozen ref to T` es azúcar: se normaliza a `ref to frozen T` (`const` del pointee). PenguScript nunca emite `T* const` — para congelar el *puntero* en sí, usa `let`.

#### Lo que no cambia

- `frozen T` tiene el mismo tamaño y la misma disposición que `T`.
- Dentro de las expresiones, un `frozen int` se comporta como un `int` (aritmética, comparaciones, indexación); solo la escritura está restringida. El resultado de una operación es un valor simple, así que `return a + 0` es un `int`.
- `frozen` nunca aparece en literales, solo en anotaciones de tipo.
- La asignabilidad se comprueba allí donde se escribe un valor (inicializadores, argumentos, `return`, `set`); no hay un análisis más profundo de propagación de const. Un valor frozen que deba acabar en una posición mutable se convierte explícitamente: `var n as int is (a to int)`.

---

## 10. Métodos, conceptos y binding

En PenguScript, los métodos, los contratos y las extensiones de tipo están separados de las definiciones de structs:
- Los métodos se asocian a los tipos mediante bloques `enchanting T:`.
- Los contratos se declaran mediante bloques `concept Name:` y se implementan mediante bloques `bind Type with Concept:`.

> [!IMPORTANT]
> **Los conceptos son contratos de tiempo de compilación, NO interfaces de runtime.**
> A diferencia de las interfaces de Java, C# o Go, un `concept` no representa un tipo de runtime, no genera una tabla de métodos virtuales (vtable) y no admite despacho dinámico ni fat pointers polimórficos. Los conceptos existen estrictamente para definir restricciones y bounds de tiempo de compilación para parámetros de tipo genéricos (`where T: Concept`), garantizando cero sobrecoste en runtime.

---

### 10.1 `enchanting` — métodos sobre tipos

Methods are attached to any user-defined type (`rune`, `echo`, `omen`) or built-in container using an `enchanting` block:

```pengu
rune Player:
    name as string
    hp as int

enchanting Player:
    # Instance method: 'self' is implicit and has type 'ref to Player'
    weave heal with amount as int into void:
        set self->hp is self->hp + amount

    # Associated (static) function: declared with 'ritual', no 'self'
    weave ritual new_hero with name as string into Player:
        return with name is name, hp is 100
```

#### Reglas de `self` y métodos `ritual`:
1. **Acceso a `self`:** `self` se pasa implícitamente por referencia (`ref to T`). Por tanto, el acceso a sus campos requiere la flecha `self->field`. El uso de punto `self.field` arroja el error `E0003: SelfDotAccessError` (*help: Change 'self.' to 'self->'*).
2. **Métodos asociados (`ritual`):** Las funciones estáticas asociadas a un tipo se declaran anteponiendo la palabra clave `ritual`. No reciben `self`. Referenciar `self` dentro de un método `ritual` arroja `E0033: InvalidRitualSelfAccessError`.
3. **Invocación:**
   - Los métodos de instancia se invocan sobre valores o variables: `calling player.heal with 25` o `calling player->heal with 25`.
   - Los métodos `ritual` se invocan exclusivamente sobre el nombre del tipo: `var p as Player is calling Player.new_hero with "Ada"`.
   - Invocar un método `ritual` sobre una instancia o un método de instancia sobre el nombre del tipo arroja `E0034: InvalidRitualCallError`.

#### Nomenclatura en C y prefijos de `insignia`:
- Los métodos de instancia se emiten en C como `<Type>_<method>(Type* restrict self, ...)`:
  ```c
  void Player_heal(Player* restrict self, int32_t amount);
  ```
- Los métodos `ritual` se emiten en C como `<Type>_<method>(...)` sin el primer parámetro `self`.
- **Regla de prefijo de `insignia`:** La directiva `insignia` prefija las funciones de módulo y los tipos de usuario. Sin embargo, para métodos que encantan tipos primitivos o contenedores estándar (`string`, `list`, `map`, `slice`, `maybe`, `result`), el generador de código **no** aplica el prefijo de módulo, emitiendo nombres limpios como `string_trim`, `list_of_int_sum` o `map_of_string_to_int_keys` para evitar colisiones con las funciones internas del runtime (`pengu_string_*`, `pengu_list_*`).

#### Encantamiento de contenedores integrados (`list`, `map`):
Los módulos de la biblioteca estándar como `std.tally` y `std.atlas` encantan directamente contenedores estándar:
- `enchanting list of int:` agrega métodos OOP como `calling xs.sum`, `calling xs.first`, `calling xs.reverse`, `calling xs.sort_asc`.
- `enchanting map of string to int:` agrega métodos como `calling m.keys`, `calling m.keys_sorted`, `calling m.get_or with k, 0`, `calling m.sum_values`.
- Dentro de un bloque `enchanting` sobre contenedores, `self` tiene tipo `ref to list of ...` o `ref to map of ...`. La iteración sobre la colección se realiza mediante `for x in essence of self:`, y el acceso indexado mediante `self at i` o `self at key`.

#### Encantamiento genérico de contenedores estándar (`shard` en `enchanting`):
A partir de PenguScript 0.15.0, es posible encantar contenedores estándar (`map`, `list`, `slice`, `maybe`, `result`) de forma genérica usando parámetros `shard`:

```pengu
enchanting map of shard K to shard V:
    weave size into int:
        return calling self.len

    weave is_empty into bool:
        return (calling self.len) == 0

    weave has_key with k as K into bool:
        return calling self.contains with k

    weave get_or with k as K, fallback as V into V:
        if calling self.contains with k:
            return self at k
        return fallback

    weave clone into map of K to V:
        var res as map of K to V is map of K to V
        with res:
            for k in essence of self:
                calling .put with k, (self at k)
        return res

    weave rename_key with old_key as K, new_key as K into bool:
        if not (calling self.contains with old_key):
            return false
        var val as V is self at old_key
        with self:
            calling .remove with old_key
            calling .put with new_key, val
        return true
```

##### Mecánica y Reglas del Encantamiento Genérico:
1. **Sintaxis de tipo:** El objetivo de `enchanting` acepta la palabra clave `shard` precediendo los parámetros de tipo en contenedores:
   - `enchanting map of shard K to shard V:`
   - `enchanting list of shard T:`
   - `enchanting slice of shard T:`
   - `enchanting maybe shard T:`
   - `enchanting result of shard T to shard E:`
2. **Monomorfización bajo demanda:** Al compilar, el compilador (`pengu_codegen.py`) monomorfiza los métodos genéricos únicamente para las combinaciones de tipos concretas invocadas en el programa (por ejemplo, `map of string to string` o `map of int to float`), emitiendo funciones C especializadas (ej. `map_of_string_to_string_get_or`, `map_of_int_to_float_clone`).
3. **Resolución de dependencias transitivas:** Cuando un método genérico invoca a otro método genérico sobre `self` (como `copy` delegando en `self.clone`), el compilador detecta la invocación transitiva e itera hasta alcanzar un punto fijo, registrando todas las firmas y prototipos antes de generar el código C.
4. **Precedencia por especificidad (Overriding concreto):** Si existe un bloque concreto (por ejemplo, `enchanting map of string to int:`), sus métodos tienen precedencia estricta sobre la implementación genérica para ese tipo concreto. Esto permite especializaciones de alto rendimiento o métodos específicos del tipo (como `sum_values` o `all_values_positive` en mapas numéricos) conviviendo con métodos genéricos estructurales (`clone`, `put_all`, `rename_key`).
5. **Mutación in-place con `with self:`**: Dado que `self` es una referencia (`ref to map of K to V`), la mutación de la colección se realiza de forma natural y segura mediante bloques de contexto `with self:`, invocando métodos del runtime como `.put`, `.remove`, `.clear`.
6. **Cero sobrecoste en tiempo de ejecución:** Todo el proceso de inferencia y sustitución ocurre en tiempo de compilación. No existen vtables, boxing de primitivos ni sobrecarga dinámica.

> **Implementación:** `pengu_grammar.py` (`type_or_param`), `pengu_types.py` (`shard_param_ref`), `pengu_checker.py::_check_enchanting_decl`, `pengu_codegen.py::_collect_weave`, `pengu_infer.py::_resolve_call_target`.

---

### 10.2 `concept` — contratos de compile-time

Un `concept` define un conjunto de firmas de métodos que un tipo debe satisfacer para cumplir el contrato:

```pengu
concept Speaker:
    weave greet with target as string into string
    weave ritual default_greeting into string
```

#### Características y sintaxis:
- **Sintaxis completa:** `concept Name [shard T [and U]] [where T: OtherConcept] :` seguido de una o más firmas `weave`.
- **Sin cuerpos de implementación:** Los métodos dentro de un `concept` son puramente declarativos; no llevan `:` ni sentencias.
- **Concepts genéricos:** Los concepts pueden aceptar parámetros de tipo (`shard T`), permitiendo modelar contenedores y operaciones parametrizadas:
  ```pengu
  concept Container shard T:
      weave push with item as T into void
      weave len into int
  ```
- **Soporte de métodos `ritual`:** Los concepts pueden exigir métodos estáticos asociados (`weave ritual ...`), obligando al tipo a proveer constructores o utilidades estáticas.
- **Sin campos:** Un `concept` no puede declarar campos de datos, variables ni estados; únicamente firmas `weave`.

> **Implementación:** `pengu_grammar.py::concept_decl`, `pengu_checker.py::_collect_top_level`, `pengu_symbols.py::define_concept`.

---

### 10.3 `bind` — implementación del contrato

Un bloque `bind` conecta formalmente un tipo concreto con un `concept`:

```pengu
rune Dog:
    name as string

bind Dog with Speaker:
    weave greet with target as string into string:
        return "Woof, {target}!"

    weave ritual default_greeting into string:
        return "Woof!"
```

#### Reglas impuestas por el compilador:
1. **Exhaustividad obligatoria (`E0031`):** Se deben implementar **todos** los métodos requeridos por el concept. Si falta uno o más métodos, el chequeador emite `E0031: UnimplementedConceptMethodError` (*Type 'T' does not implement method 'm' required by concept 'C'*).
2. **Concordancia estricta de firmas (`E0030`):** Cada método en el `bind` debe tener exactamente la misma cantidad de parámetros y un tipo de retorno compatible con la definición del concept (`E0030: ConceptMethodMismatchError`).
3. **Tipos de parámetros idénticos (`E0030`):** Los tipos de cada parámetro deben coincidir exactamente con los declarados en el concept.
4. **Existencia previa del tipo y concept (`E0004`):** El tipo objetivo (`Type`) y el concept (`Concept`) deben estar declarados antes de su bloque `bind` (salvo que provengan de un `.d.pengu` con includes C).
5. **Múltiples contratos:** Un tipo puede tener tantos bloques `bind` como concepts necesite (`bind Player with Speaker:`, `bind Player with Serializable:`).
6. **Sin métodos por defecto:** Los concepts no proveen implementaciones por omisión (*default methods*); cada `bind` debe escribir la implementación completa de cada método.

> **Implementación:** `pengu_checker.py::_collect_top_level` (rama `bind_decl`), `pengu_symbols.py::concept_bindings`.

---

### 10.4 Resolución de métodos en compile-time

Cuando el compilador encuentra una llamada `calling x.method(...)`, el analizador semántico (`pengu_infer.py::_resolve_call_target`) resuelve la función destino siguiendo una búsqueda determinista:

1. **Determinación del receptor:** Se evalúa la expresión `x` para obtener su tipo base (`obj_type`).
2. **Desenvolvimiento de referencias:** Si `obj_type` es un `ref to T`, un alias (`alias`) o un tipo calificado (`frozen`, `seal`), se desenvuelve hasta el tipo subyacente `t_name`.
3. **Parámetro de tipo (`TypeParam`):** Si `x` es un parámetro genérico `T`, el compilador consulta los bounds declarados en la cláusula `where T: Concept`. Si el concept contiene el método, resuelve la llamada contra la firma del concept.
4. **Tabla unificada de métodos:** Se busca la tupla `(t_name, method_name)` en `symbols.methods` (tabla poblada por bloques `enchanting` y `bind`). Si el método es `ritual`, rechaza la llamada con `E0034`.
5. **Búsqueda por nombre calificado:** Se busca en `symbols.functions[f"{t_name}_{method_name}"]`.
6. **Caída a plantilla monomorfizada:** Si el tipo fue monomorfizado a partir de un genérico (ej. `Box_int`), se obtiene el nombre base `base_tname = t_name.split("_")[0]` (`Box`) y se busca en `symbols.generic_methods`. Las variables de tipo se sustituyen con los argumentos concretos correspondientes.
7. **Tabla de bindings de concepts:** Se busca `(base_tname, concept)` en `symbols.concept_bindings` para resolver métodos provistos mediante `bind`.
8. **Métodos integrados de contenedor:** Se comprueban métodos primitivos de listas (`push`, `pop`, `len`, etc.) y mapas (`get`, `put`, `contains`, etc.).
9. **Fallo:** Si ningún paso localiza el método, se emite `E0004: Type 't_name' has no method 'method_name'`.

#### Diagrama de resolución:

```text
  calling x.method(...)
         │
         ▼
  ¿Es 'x' un TypeParam (T)?  ──[Sí]──► Buscar en bounds (where T: Concept)
         │ [No]
         ▼
  Desenvolver punteros / alias -> t_name
         │
         ▼
  ¿Existe en symbols.methods[(t_name, method)]? ──[Sí]──► Verificar !ritual -> FnType
         │ [No]
         ▼
  ¿Existe en symbols.functions[t_name_method]? ──[Sí]──► Retornar FnType
         │ [No]
         ▼
  base_tname = t_name.split("_")[0]
  ¿Existe en generic_methods[(base_tname, method)]? ──[Sí]──► Sustituir shards -> FnType
         │ [No]
         ▼
  ¿Existe en concept_bindings[(base_tname, concept)]? ──[Sí]──► Retornar FnType
         │ [No]
         ▼
  ¿Es método nativo de ListType o MapType? ──[Sí]──► Retornar FnType sintético
         │ [No]
         ▼
  Error E0004: Type 't_name' has no method 'method'
```

> **Implementación:** `pengu_infer.py::_resolve_call_target`.

---

### 10.5 Bounds en genéricos (`where T: A and T: B`)

Los concepts se emplean principalmente como restricciones de tipo (*bounds*) en funciones y estructuras genéricas:

```pengu
concept Measurable:
    weave weight into float

concept Printable:
    weave print_me into void

weave display_weight shard T where T: Measurable and T: Printable with item as T into void:
    calling item.print_me
    calling spark.println with "Weight: {(calling item.weight to string)}"
```

- **Sintaxis de restricciones:** Se declaran tras `shard` mediante la cláusula `where T: Concept1 and T: Concept2` (o separadas por comas `where T: Concept1, T: Concept2`).
- **Verificación en el punto de llamada:** Cuando una función genérica se especializa con un tipo concreto (ej. `calling display_weight with my_dog`), el compilador invoca `implements_concept(arg_t, bound, symbols)`.
- **Falta de bound (`E0032`):** Si el tipo argumento no cuenta con un bloque `bind` para el concept requerido, el compilador emite:
  ```text
  error[E0032]: generic type argument 'Dog' does not implement required concept bound 'Printable'
  ```
  *(help: Bind the required concept to the type using 'bind Type with Concept:'.)*

> **Implementación:** `pengu_checker.py::_check_type_bounds`, `pengu_infer.py::implements_concept`.

---

### 10.6 Limitaciones explícitas de los concepts

Un `concept` en PenguScript no es un tipo de datos ordinario en tiempo de ejecución. Las siguientes limitaciones son fundamentales por diseño:

1. **No puede utilizarse como tipo de valor de primera clase:** Aunque declarar `var s as Speaker` pasa la fase sintáctica (porque internamente `ConceptType` se acepta durante el chequeo preliminar), **el generador de C mapea cualquier `ConceptType` directamente a `void*`** (`CTypeMapper.to_c_type`), perdiendo la estructura de tipos. En consecuencia, invocar `calling s.greet` fallará con `E0004: Type 'Speaker' has no method 'greet'`.
2. **Sin despacho dinámico ni vtables:** El compilador emite llamadas directas en C. No existen punteros a tablas virtuales ni sobrecarga de indirección en tiempo de ejecución.
3. **Sin colecciones heterogéneas:** No es posible crear una lista `list of Speaker` que contenga instancias mixtas de `Dog`, `Player` y `Robot` para despachar llamadas polimórficas.
4. **Sin herencia entre concepts:** No existe `concept A extends B`. Las combinaciones de contratos se expresan mediante bounds múltiples (`where T: A and T: B`).
5. **Sin campos o variables de instancia:** Los concepts no pueden definir campos de datos.
6. **Sin métodos por omisión:** Cada tipo debe implementar explícitamente todos los métodos requeridos.
7. **Sin verificación ni introspección en runtime:** No existen operadores como `instanceof`, `as`, ni `is Speaker` en tiempo de ejecución. La conformidad con un concept es 100% estática.

#### Ejemplo de uso incorrecto vs. corrección idiomática:

```pengu
concept Speaker:
    weave greet into string

rune Dog:
    name as string

bind Dog with Speaker:
    weave greet into string:
        return "Woof"

weave main into void:
    var d as Dog is with name is "Buddy"

    # ❌ INCORRECTO: Usar el concept como tipo de variable
    # var s as Speaker is d           # El C codegen mapea 'Speaker' a void*
    # calling s.greet                 # E0004: Type 'Speaker' has no method 'greet'

    # ✅ CORRECTO 1: Invocación directa sobre el tipo concreto
    calling d.greet

    # ✅ CORRECTO 2: Invocación polimórfica estática mediante genéricos con bounds
    calling greet_anyone with d

weave greet_anyone shard T where T: Speaker with s as T into void:
    calling spark.println with calling s.greet
```

> **Implementación:** `pengu_codegen.py::CTypeMapper.to_c_type`, `pengu_infer.py::_resolve_call_target`.

---

### 10.7 Comparativa con interfaces de Java/C#

| Característica | Interfaces (Java / C#) | Concepts (PenguScript) |
|---|---|---|
| **Mecanismo de despacho** | Dinámico (vtable / itable) en runtime | Estático (direct C call) en compile-time |
| **Uso como tipo de variable (`var x as T`)** | ✅ Sí (referencia polimórfica) | ❌ No (se mapea a `void*`) |
| **Colecciones heterogéneas (`list of T`)** | ✅ Sí (`List<Speaker>`) | ❌ No (`list of Speaker` no es utilizable) |
| **Herencia entre contratos** | ✅ Sí (`interface B extends A`) | ❌ No (bounds múltiples `where T: A and T: B`) |
| **Métodos por defecto (*default methods*)** | ✅ Sí (Java 8+, C# 8+) | ❌ No (cada `bind` implementa todo) |
| **Campos o propiedades** | ✅ En C# / constantes en Java | ❌ No (solo firmas `weave`) |
| **Inspección en runtime (`instanceof` / `is`)** | ✅ Sí | ❌ No (resuelto en tiempo de compilación) |
| **Restricciones genéricas (*bounds*)** | ✅ Sí (`<T extends Speaker>`) | ✅ Sí (`shard T where T: Speaker`) |
| **Implementación externa (*ad-hoc*)** | ❌ Requiere declarar `implements` en la clase | ✅ Sí (`bind` se declara fuera del `rune`) |
| **Parámetros genéricos en el contrato** | ✅ Sí (`Comparable<T>`) | ✅ Sí (`concept Container shard T:`) |
| **Métodos estáticos requeridos** | ❌ Limitado o no exigible | ✅ Sí (`weave ritual` en `concept`) |
| **Sobrecarga de rendimiento** | Puntero a objeto + puntero a vtable | **Cero overhead** (inlined o salto directo) |

---

### 10.8 Ejemplo end-to-end compilable

El siguiente programa ilustra la definición de un `concept` con métodos de instancia y `ritual`, su implementación mediante `bind`, y su consumo a través de funciones genéricas con cláusulas `where`:

```pengu
import std.spark

# 1. Definición del contrato
concept Formatter:
    weave format_entry with title as string into string
    weave ritual category_name into string

# 2. Tipos de datos
rune LogEntry:
    level as string
    message as string

# 3. Implementación del contrato
bind LogEntry with Formatter:
    weave format_entry with title as string into string:
        return "[{self->level}] {title}: {self->message}"

    weave ritual category_name into string:
        return "SYSTEM_LOG"

# 4. Función genérica restringida por el concept
weave print_formatted shard T where T: Formatter with item as T, header as string into void:
    var rendered as string is calling item.format_entry with header
    calling spark.println with rendered

# 5. Punto de entrada
weave main into int:
    var entry as LogEntry is with level is "INFO", message is "Compiler pipeline ready"

    # Llamada al método ritual estático del concept directamente sobre el tipo
    calling spark.println with "Category: {calling LogEntry.category_name}"

    # Llamada a través de la función genérica con bound comprobado estáticamente
    calling print_formatted with entry, "Build"
    return 0
```

### 10.9 Conceptos integrados

PenguScript incluye un conjunto cerrado de conceptos que el compilador, el chequeador y el C generado ya entienden. **No** son palabras clave: son nombres reservados en el ámbito global. Pueden usarse como bounds de `where`, y los marcados como *derivables* también pueden aparecer en una cláusula `derive`.

| Concepto | Latín | Operaciones / capacidades que habilita |
|---|---|---|
| `Num` | *numerus* | `+`, `-`, `*`, `/` y `-` unario sobre un parámetro de tipo |
| `Integrum` | *integer* | operadores solo para enteros: `%`, `&`, `|`, `^`, `<<`, `>>`, `~` |
| `Par` | *par* | `==`, `!=` |
| `Ordo` | *ordo* | `<`, `<=`, `>`, `>=` |
| `Vinculum` | *vinculum* | usable como clave de `map` (hashing) |
| `Imago` | *imago* | copia profunda (callback `clone` para contenedores con posesión) |
| `Nexus` | *nexus* | destrucción (callback `cleanup` para contenedores con posesión) |
| `Forma` | *forma* | interpolación / formateo de strings (`"{x}"`) |
| `Iterabilis` | *iterabilis* | iteración `for x in col` |
| `Donum` | *donum* | valor por defecto mediante la expresión `donum T` |

`Integrum` es un refinamiento estricto de `Num`: un bound `Integrum` también satisface `Num` (así que `where T: Integrum` permite `+`), pero no al revés — esto es lo que hace que `%` rechace `float`.

Qué tipos primitivos y de contenedor satisfacen cada concepto lo fija la tabla de conceptos del compilador:

| Tipo | Conceptos |
|---|---|
| primitivos enteros (`int`, `i8`…`u64`, `usize`, `isize`, `byte`, …) | `Num`, `Integrum`, `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Donum` |
| flotantes (`float`, `f32`, `f64`, `double`) | `Num`, `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Donum` |
| `bool` | `Par`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Donum` |
| `char` | `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma` |
| `string` | `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`, `Donum`, `Iterabilis` |
| `list of T` / `map of K to V` | `Par`, `Iterabilis`, `Imago`, `Nexus` |
| `slice of T` | `Par`, `Iterabilis` |
| `maybe T` / `result of T to E` | `Par`, `Imago`, `Nexus` |

Las runes, los echos y los omens algebraicos obtienen un concepto mediante `derive` (§9.1.2) o mediante un `bind` explícito (§10.3); un bound de `where` queda entonces satisfecho por la implementación derivada.

### 10.10 Coherencia de `bind`

Un tipo puede vincular varios conceptos, pero el par `(type, method)` solo puede proporcionarse una vez:

```pengu
concept A:
    weave f into int

concept B:
    weave f into int

bind Foo with A:
    weave f into int:
        return 1

bind Foo with B:
    weave f into int:
        return 2      # E0047: 'f' of 'Foo' is already provided by concept 'A'
```

Vincular el *mismo* par `(type, concept)` dos veces también es `E0047`. Dividir las operaciones object-safe de un tipo entre dos conceptos está bien siempre que los nombres de los métodos sean distintos.

---

## 11. Genéricos

```pengu
rune Box shard T:
    value as T

weave identity shard T with x as T into T:
    return x

weave swap shard T and U with a as T, b as U into Pair of U and T:
    return with first is b, second is a

weave output shard T where T: Printable with item as T into void:
    calling item.print_me
```

- `shard T` introduce un parámetro de tipo (se permiten varios: `shard T and U`).
- La aplicación de tipos usa `of`: `Box of int`, `Pair of string and int`.
- `where T: Concept` restringe un parámetro a los tipos que implementan el concepto.
- Las funciones genéricas se monomorfizan: cada llamada concreta instancia una
  función C especializada con los tipos sustituidos.
- Los `rune` genéricos pueden aparecer con `of` en las firmas; la inferencia de los
  parámetros de tipo que solo aparecen en posiciones de retorno/contenedor es limitada
  (véase la nota en las referencias del §18) — proporciona tipos de argumento concretos.
- **Enchanting de contenedores genéricos:** Los contenedores estándar admiten `enchanting`
  con parámetros de tipo directamente (`enchanting map of shard K to shard V:`,
  `enchanting list of shard T:`, `enchanting slice of shard T:`). El compilador
  monomorfiza los métodos por cada uso concreto, con soporte completo para llamadas
  transitivas sobre `self` y para la anulación por prioridad desde bloques concretos
  (véase §10.1).

> [!IMPORTANT]
> PenguScript no tiene «turbofish» (`f::<T>`). Los parámetros de tipo se infieren a
> partir de los tipos de los argumentos; cuando un tipo solo aparece en el *resultado*
> (por ejemplo, un constructor de contenedores genérico) debes dar al compilador un
> contexto concreto, o la comprobación falla con «Could not infer type parameter(s)».

### 11.1 Fundamentos de `shard`

Un parámetro de tipo se declara con `shard` y está en ámbito desde la lista de
parámetros `with` hasta el final de la declaración; también se puede usar en el tipo
de retorno y dentro de cuerpos de `rune`:

```pengu
rune Box shard T:
    value as T

weave identity shard T with x as T into T:
    return x

weave first_or shard T where T: Par with xs as list of T, fallback as T into T:
    if calling xs.len == 0:
        return fallback
    return xs at 0
```

Cada llamada *concreta* instancia una función/estructura C especializada
(`identity_int`, `Box_of_string`, …). Anidar un genérico dentro de otro genérico está
soportado sin volver a declarar los ayudantes: `Box of (Box of int)`.

Los argumentos de tipo explícitos están disponibles cuando la inferencia no puede
verlos:

```pengu
var a as int is calling identity of int with 5
var b as string is calling identity of string with "hi"
```

### 11.2 Cotas

Las cláusulas `where` asocian conceptos a los parámetros de tipo (véase §10.5 para la
gramática completa y §10.9 para la tabla de conceptos):

```pengu
weave sum shard T where T: Num with xs as list of T into T:
    ...

weave clamped shard T where T: Num and T: Ordo with lo as T, hi as T into T:
    ...
```

Las cotas también se propagan **a los cuerpos de los métodos**: cada `TypeParam`
construido al comprobar un `weave`, un `enchanting` o un `bind` genérico lleva las
cotas declaradas en el receptor (`enchanting Box shard T where T: Par`) y en el propio
método.

Las cotas se aplican en **ambas direcciones**:

* lectura/derivación — `T` solo puede usarse donde sus cotas lo permitan
  (operadores, `donum T`, iteración, …);
* escritura — asignar a un destino `T` requiere un valor que implemente todas las
  cotas (`set essence of x is "s"` con `T: Num` es `E0005`, §5.1); un `T` sin cotas
  sigue siendo un comodín, y `any`/`null`/otro parámetro siempre se aceptan.

### 11.3 Operadores en contextos genéricos

Los operadores solo están disponibles cuando el concepto correspondiente está entre las
cotas:

| Cota | Operadores disponibles en `T` |
|---|---|
| `Num` | `+`, `-`, `*`, `/`, `-` unario |
| `Integrum` | `%`, `&`, `\|`, `^`, `<<`, `>>`, `~` (y todo lo que permite `Num`) |
| `Par` | `==`, `!=` |
| `Ordo` | `<`, `<=`, `>`, `>=` |

Usar un operador sin su cota genera `E0049` junto con la cláusula `where` exacta que
hay que añadir:

```pengu
weave bad shard T with a as T, b as T into T:
    return a + b            # E0049: add 'where T: Num'

weave mod2 shard T where T: Num with a as T, b as T into T:
    return a % b            # E0049: '%' needs 'where T: Integrum'
```

### 11.4 `donum T` — valores por defecto

`donum T` es el valor cero/por defecto de un tipo que admite valor por defecto. Se
traduce al literal compuesto de C `(T){0}`, que es válido para escalares, punteros y
estructuras:

```pengu
weave sum shard T where T: Num with xs as list of T into T:
    var acc as T is donum T
    for x in xs:
        set acc is acc + x
    return acc
```

`donum T` necesita una cota cuyos tipos admitan valor por defecto (`Num`, `Integrum`,
`Par`, `Ordo`, `Forma`, `Donum`), o bien un tipo concreto que implemente `Donum`:

```pengu
var n as int is donum int                 # 0
var s as string is donum string           # empty string
var f as float is donum float             # 0.0
```

### 11.5 Iterar genéricos

La iteración necesita un tipo de elemento concreto. `list of T`, `slice of T`, los
arrays, las cadenas y los mapas funcionan dentro de código genérico:

```pengu
weave count shard T where T: Par with xs as list of T into int:
    var n as int is 0
    for x in xs:                 # element type is T
        set n is n + 1
    return n
```

Iterar un parámetro de tipo *desnudo* (`xs as T` con `for x in xs`) se rechaza con
`E0005`: se desconoce el tipo del elemento y el C generado no podría indexar el valor.
Usa `list of T` / `slice of T`, o espera a los tipos asociados (§11.7).

### 11.6 `derive` en tipos genéricos

`derive` funciona sobre declaraciones genéricas; los conceptos derivados se convierten
en cotas de los parámetros de tipo de las funciones auxiliares:

```pengu
rune Point shard T derive Par, Ordo:
    x as T
    y as T
```

Tanto `Point of int` como `Point of string` obtienen `==`, `<`, … funcionales siempre
que el argumento sustituido implemente el concepto (se comprueba en el punto de
llamada).

### 11.7 Tipos asociados (trabajo futuro)

Los conceptos al estilo de los iteradores, como el `Iterator` de Rust, necesitan un
*tipo asociado* para que el código genérico pueda nombrar el elemento:

```pengu
concept Iterabilis shard Self:
    alias Item
    weave next with it as ref to Self into maybe Self.Item
```

La sintaxis para declarar el tipo asociado (`alias Item`) se acepta por compatibilidad
futura, pero resolver `Self.Item` a un tipo C concreto durante la monomorfización
**aún no está implementado**. Hasta que llegue, la iteración genérica usa
`list of T`/`slice of T` (§11.5), y `for x in xs` sobre un `T: Iterabilis` desnudo es
un error de compilación.

### 11.8 Secciones relacionadas

* Métodos y contenedores genéricos: §10.1.
* Definiciones de conceptos y `bind`: §10.2, §10.3.
* Tabla de conceptos integrados: §10.9.
* Reglas de coherencia para `bind`: §10.10.
* Implementaciones de conceptos derivados: §9.1.2.
* Ownership de contenedores (`Imago`/`Nexus`): §13.5.

---

## 12. Opcionales y errores

```pengu
weave find_user with id as int into maybe string:
    if id == 1:
        return some "Admin"
    return maybe none

weave main into void:
    var user as maybe string is calling find_user with 1

    if user is present:
        let name is user.value          # unwrap only after a presence check
        calling print with name

    let fallback is user or else "Guest"          # value or fallback
    let u is user or return 0                     # value or early return
    let f is calling risky with 42 or:            # handle failure with a block
        calling spark.println with error
        return 1
    let f2 is try calling risky with 10           # propagate to caller
```

### Semántica y lowering de codegen:

- **Contenedores de valor:** `maybe T` y `result of T to E` se representan en C como
  estructuras `PenguMaybe` y `PenguResult`. Los valores presentes son copias asignadas
  en el heap mediante `pengu_sigil_alloc(sizeof(T))`.
- **Inspección de campos:**
  - `maybe T`: expone `.is_present` (`bool`) y `.value` (`T`, seguro de acceder cuando
    `is_present` es true).
  - `result of T to E`: expone `.is_ok` (`bool`), `.value` (`T`, seguro cuando `is_ok`
    es true) y `.error` / `.err` (`E`, seguro cuando `is_ok` es false).
- **`or else <expr>` (fallback perezoso):** evalúa `<expr>` solo si el valor primario
  está ausente o es un error. Emite una expresión de sentencia GNU:
  ```c
  __extension__(({
    PenguMaybe _m = user;
    _m.is_present ? (*(string*)_m.value) : ("Guest");
  }))
  ```
- **`or return <expr>` (retorno temprano):** comprueba la presencia/el éxito. Si el
  valor está ausente o ha fallado, ejecuta automáticamente todos los manejadores de
  limpieza registrados (`defer`, `errdefer`, auto-banish de ámbito) y devuelve `<expr>`
  desde el weave contenedor.
- **`try <expr>` (propagación):** desempaqueta el valor o devuelve inmediatamente un
  resultado vacío/con error desde la función contenedora:
  - Requiere que la función contenedora devuelva `maybe T` (para un operando `maybe`) o
    un tipo `result` compatible (`E0045: TypeMismatchError` si no coinciden).
  - En caso de fallo, limpia los ámbitos activos y ejecuta
    `pengu_frame_pop(); return pengu_maybe_none();` (o devuelve el resultado de error).
- **Bloques `or:` (sentencia vs expresión):**
  - **Como inicializador de destino (`var x is f() or: ...`):** se emiten como
    sentencias C limpias (`if (res.is_ok) { x = res.value; } else { ... }`).
  - **Como expresión independiente:** se emiten como una expresión de sentencia GNU.
  - **Ámbito léxico de `error`:** dentro de un bloque `or:`, la carga útil del fallo se
    liga a `error` (tipo `string` para `maybe T`, o el tipo de error `E` para `result`).
    Acceder a `error` fuera de un bloque `or:` es un error en tiempo de compilación
    (`E0015`). Una vez que el bloque se cierra, `error` se elimina del ámbito.
- **Posiciones sintácticas (`list_value_expr` vs aritmética):**
  - **En argumentos de llamada e inicializadores de struct:** `or else`, `or return` y
    los bloques `or:` son válidos directamente, sin paréntesis, en argumentos de
    función/weave (`calling f with a, b or else "default"`) y en inicializadores de
    campos de struct (`with name is get_name() or else "guest"`), porque
    `list_value_expr` analiza las expresiones de unwrap directamente.
  - **En aritmética binaria:** `or else` y `or return` se asocian con menor precedencia
    que los operadores binarios (`+`, `-`, `*`, `/`). Cuando se usan como operando en
    aritmética, se requieren paréntesis alrededor de la expresión de unwrap:
    `var total is 10 + (bonus or else 0)`. Escribir `10 + bonus or else 0` se agrupa
    como `(10 + bonus) or else 0`, lo que provoca un error de tipos no coincidentes
    (`E0005`) al evaluar la suma binaria.

> [!NOTE]
> Para una API a nivel de módulo sobre estos operadores, consulta los ayudantes nativos
> de `std.oracle` (`some_int`, `unwrap_int`, `unwrap_or_string`, …).

---

## 13. Memoria y punteros

```pengu
var raw as ref to int is sigil of value   # &value
var copy as int is essence of raw         # *raw
defer banish ptr                          # run on scope exit
errdefer banish ptr                       # run only on error return
banish ptr                                # explicit free now
banish str_var                            # free dynamic string (pengu_banish_string)
banish list_var                           # free list allocation (pengu_banish_list)
banish map_var                            # free map allocation and string keys/values (pengu_banish_map)
```

Reglas:
- `banish target` acepta un lvalue mutable de tipo `ref to T`, `string`, `list of T` o
  `map of K to V`.
- `banish ptr` (donde `ptr as ref to T`): emite `pengu_banish((void*)(ptr))` para
  liberar memoria asignada en el heap.
- `banish s` (donde `s as string`): emite `pengu_banish_string(&s)`. Libera los búferes
  de cadena asignados dinámicamente en el heap (`free(s.data)`), establece
  `s.data = NULL` y `s.len = 0`, vaciando la cadena. No accedas a ella después de
  aplicar banish.
- `banish l` (donde `l as list of T`): emite `pengu_banish_list(&l)`. Libera el búfer
  interno de elementos y reinicia la capacidad y la longitud a 0.
- `banish m` (donde `m as map of K to V`): emite `pengu_banish_map(&m)`. Libera los
  buckets y las entradas de la tabla hash, y libera automáticamente todas las claves y
  los valores de tipo `string` (`pengu_banish_string`), evitando fugas en diccionarios
  dinámicos.
- Las sentencias `defer`/`errdefer` funcionan con `banish` (por ejemplo, `defer banish s`)
  y también con bloques; la ejecución es LIFO al salir del ámbito (o solo en las rutas
  de error para `errdefer`).
- `ref to T` se pasa como puntero: permite la mutación desde C y receptores `self`
  eficientes.

#### Validación y prohibiciones (`_check_banish_stmt` y `banish_expr`):
- **Literales y no-lvalues (`E0008`):** intentar aplicar banish a un literal
  (`banish "str"`, `banish 10`) genera `E0008: InvalidMemoryOpError`.
- **Expresiones temporales (`E0008`):** las expresiones sin una ubicación de memoria
  asignable (llamadas, operadores binarios, unwraps) generan `E0008`. Asigna primero el
  temporal a una variable: `var tmp is f(); banish tmp`.
- **Tipos `seal` nominales (`E0008`):** los newtypes fuertes no se pueden banish
  directamente aunque su tipo subyacente sea una cadena o un puntero. Se requiere una
  conversión explícita: `banish (v to string)`.
- **Destinos `frozen` (solo lectura) (`E0008`):** banish modifica y desasigna la memoria
  del destino; aplicar banish a una variable o valor `frozen` genera `E0008`.
- **Constantes (`E0008`):** las constantes no se pueden banish.
- **Locales con ownership automático (`E0047`):** aplicar banish explícitamente a una
  variable local propiedad del ámbito genera `E0047: AutoOwnedBanishError` para evitar
  errores de doble free, ya que el compilador inyecta automáticamente la limpieza al
  final del bloque contenedor.
- **Locales prestados (`E0048`):** aplicar banish a una variable marcada como
  `borrowed` genera `E0048: BorrowedBanishError`, porque las referencias prestadas no
  poseen la memoria subyacente.

### 13.1 Indexar a través de punteros y tomar prestados búferes de C

Un `ref to T` se puede indexar directamente, tanto en lecturas como en escrituras, con
el mismo operador `at` que usan los arrays:

```pengu
weave fill with p as ref to int, count as int into int:
    for i in 0 to count:
        set p at i is i * 10        # p[i] = i * 10
    return p at 0                   # p[0]

weave main into int:
    var buf as array of int with size 4 is [0, 0, 0, 0]
    calling fill with buf, 4        # arrays decay to 'ref to int'
    return 0
```

- Se pueden construir slices sobre punteros C arbitrarios con `std.ffi.slice_from_ptr`:
  `var sl as slice of Vector2 is calling ffi.slice_from_ptr of Vector2 with (sigil of pts), 4`.
- **La aritmética de punteros (`p + 1`) no está soportada de forma deliberada.** La
  indexación (`p at i`), los slices (`ffi.slice_from_ptr`) y `transmute` ofrecen
  alternativas que acarrean límites o que son explícitas.

### 13.2 Tipado estricto de punteros e interoperabilidad

PenguScript impone un tipado estricto del tipo apuntado para `ref to T` a fin de evitar
desajustes silenciosos de tipo de búfer. Mientras que los valores numéricos permiten
widening (`int` → `i64`), los punteros exigen tipos apuntados idénticos (o el comodín
`void`/`opaque`).

| Puntero de origen (`src`) | Destino esperado (`dst`) | ¿Permitido? | Regla / Nota |
|---|---|---|---|
| `ref to T` | `ref to T` | ✅ Sí | Coincidencia exacta del tipo apuntado (`_same_pointee`) |
| `ref to char` | `ref to frozen char` | ✅ Sí | Lo mutable fluye hacia frozen (`const`) |
| `ref to byte` | `ref to char` | ✅ Sí | Interoperabilidad de búfer de bytes C sin procesar (`char*` ↔ `uint8_t*`) |
| `ref to char` | `ref to byte` | ✅ Sí | Interoperabilidad de búfer de bytes C sin procesar (`char*` ↔ `uint8_t*`) |
| `ref to T` | `ref to void` / `ref to frozen void` | ✅ Sí | Puntero a objeto comodín universal |
| `array of T with size N` | `ref to T` / `ref to frozen T` | ✅ Sí | Decaimiento de array a puntero |
| `bytes of s` | `ref to byte` / `ref to char` / `ref to frozen void` | ✅ Sí | Préstamo del almacenamiento de bytes de la cadena |
| `ref to frozen T` | `ref to T` | ❌ No (`E0005`) | El cualificador const no se puede descartar |
| `ref to i32` | `ref to char` / `ref to byte` | ❌ No (`E0005`) | El widening numérico no se aplica a los punteros |
| `ref to u8` | `ref to char` | ❌ No (`E0005`) | Solo se permite la excepción `char` ↔ `byte` |
| `array of i32 with size N` | `ref to char` | ❌ No (`E0005`) | Desajuste del tipo apuntado durante el decaimiento |
| `ref to f32` | `ref to f64` | ❌ No (`E0005`) | Los tipos apuntados float deben coincidir estrictamente |

### 13.3 Convenciones de ownership y tiempo de vida de búferes de C

Los bindings de C declaran funciones que devuelven búferes en el heap asignados por las
bibliotecas subyacentes (`malloc`, `strdup`, `LoadAudioStream`, `sqlite3_open`, etc.):
1. **Documentación del binding:** las docstrings `##` especifican la función de limpieza
   designada por la biblioteca.
2. **Limpieza de la biblioteca vs banish:** la memoria asignada por una biblioteca C
   externa debe liberarse con la propia rutina de limpieza de esa biblioteca (por
   ejemplo, `defer calling raylib.UnloadTexture with tex`), **no** con `banish`.
   `banish` está reservado para la memoria gestionada por el runtime de PenguScript
   (`pengu_sigil_alloc`, cadenas dinámicas, listas, mapas).

### 13.4 Locales propiedad del ámbito (auto-banish)

PenguScript implementa una gestión automática y determinista de la memoria para valores
del heap asignados localmente (*locales propiedad del ámbito*). Las variables locales
que contienen contenedores del heap (`string`, `list of T`, `map of K to V`)
inicializadas con expresiones frescas y sin aliasing son rastreadas por el compilador
(`is_auto_banished`).

Cuando la ejecución sale del bloque léxico donde se declaró la variable, el compilador
emite llamadas de limpieza deterministas y ordenadas LIFO (`pengu_banish_string`,
`pengu_banish_list`, `pengu_banish_map`).

#### Condiciones para el ownership automático (`_compute_auto_banished`):

Una variable local `x` se marca como de propiedad automática si y solo si se cumplen
**las seis** condiciones siguientes de forma simultánea:
1. **Tipo contenedor:** su tipo es `string`, `list of T` o `map of K to V` (no un
   `seal S as string` nominal, ni punteros, ni primitivos).
2. **No prestada:** se declara **sin** el modificador suave `borrowed`.
3. **Expresión fresca del heap:** su expresión inicializadora es una asignación fresca:
   - Formato de interpolación de cadenas `"{x} and {y}"`
   - Conversión de carácter `chr(n)` o conversión `(x to string)`
   - Constructores de colección: `list of T with capacity N` o literales con elementos `[a, b]`
   - Constructores de mapa: `map of K to V` o literales de mapa con entradas
   *(Los literales de cadena `"hello"` que referencian memoria estática, las colecciones
   vacías `[]` y las variables con alias NO activan el auto-banish. `+` es solo numérico,
   así que ya no puede producir una cadena fresca.)*
4. **Solo reasignación fresca:** cada `set x is …` del ámbito introduce un valor *fresco* (literal interpolado, constructor o resultado de una llamada). El valor anterior se libera justo antes de la nueva asignación, de modo que un bucle de reasignación se mantiene O(1). Asignar un rvalue prestado (`set x is y`, con `y` otro enlace) desactiva el auto-banish, porque el local pasaría a aliasar el búfer de `y` en lugar de poseer el suyo.
5. **Sin banish/defer explícitos:** no aparece en `banish x`, `defer banish x` ni
   `errdefer banish x`.
6. **Sin escape de ámbito:** no escapa de su ámbito léxico según el análisis de escape.

#### Disparadores del análisis estático de escape:

Una variable se marca como **escapada** (lo que desactiva automáticamente el auto-banish
para evitar use-after-free) si:
- **Se devuelve:** se devuelve directamente (`return x`), mediante puntero (`sigil of x`)
  o desde dentro de una expresión de bloque (`return if c: x else: y`, `return do: x`).
- **Se inserta en contenedores _sin_ copia profunda:** se pasa como argumento a métodos
  mutadores de contenedores (`calling lst.push with x`, `append`, `map.put`, `insert`,
  `set`) cuyo tipo de elemento **no tiene callback de clonado**. Los contenedores con
  ownership (`list of string`, `list of list of T`, `map of string to V`, runes con
  `derive Imago`, …) hacen copia profunda en `push`/`put`, así que el local conserva el
  ownership y sigue recibiendo auto-banish (§13.5); solo los almacenamientos
  superficiales o con aliasing marcan el valor como escapado. El tipo del receptor se
  resuelve a través de **cadenas de acceso** — `self->items`, `self.items`,
  `o->inner.items`, `bag.items`, `bag->items` y las formas indexadas llegan todos al
  contenedor subyacente —, de modo que un `push` a través de un campo de rune se
  clasifica por el tipo de elemento de ese campo, no por el rune que lo contiene.
- **Se incrusta en literales compuestos:** se incrusta en literales de struct
  (`with f is x`), arrays `[x]`, mapas, `tuple_lit`, `some x`, `ok x`, `err x` o
  literales de bloque indentados (`indent_entries`, `indent_array`, `map_entry`).
- **Tiene alias:** se asigna a otra variable (`var b is x`, `let b is x`).
- **Toma de dirección:** se toma un puntero explícito mediante `sigil of x`.
- **Campo de un contenedor que escapa:** se asigna el campo de un contenedor que escapa
  `set container.item is x`.
- **No es un escape (slots de cadena con ownership):** una `string` escrita en un slot
  de cadena resoluble — un campo de struct/omen (`set p.name is x`, `.name` dentro de un
  constructor `with:`, `with name is x`), un elemento de `list`/array
  (`set xs at 0 is x`) o un apuntado (`set essence of p is x`) — se **copia en
  profundidad** en ese slot, así que el local conserva su búfer y sigue recibiendo
  auto-banish. Los slots que no son de cadena (listas, mapas, runes) y los destinos cuyo
  tipo no se puede resolver mantienen el comportamiento conservador descrito arriba.

#### Diagnósticos e invariantes de seguridad:
- **`AutoOwnedBanishError` (`E0047`):** llamar manualmente a `banish x` sobre una
  variable de propiedad automática se rechaza en tiempo de compilación para evitar
  errores de doble free.
- **`BorrowedBanishError` (`E0048`):** llamar a `banish x` sobre una variable declarada
  con `borrowed` se rechaza en tiempo de compilación porque las referencias prestadas no
  poseen memoria.

#### Resumen de funciones del heap en runtime:

| Función | Firma / Operación | Comportamiento | Semántica de ownership |
|----------|-----------------------|----------|---------------------|
| `pengu_sigil_alloc` | `void* pengu_sigil_alloc(size_t sz)` | Asigna memoria del heap inicializada a cero para los opcionales `some`. | El llamador posee el puntero devuelto. |
| `pengu_string_new` | `PenguString pengu_string_new(const char *s, int len)` | Asigna un búfer de cadena con ownership en el heap. | El llamador posee el `PenguString.data` devuelto. |
| `pengu_string_from_cstr` | `PenguString pengu_string_from_cstr(const char *s)` | Crea una vista prestada sin ownership sobre una cadena de C. | Prestada; sin ownership (no apliques banish a literales estáticos). |
| `pengu_string_format_ex` | `PenguString pengu_string_format_ex(const char *fmt, ...)` | Formateador `"{expr}"` exacto a nivel de byte: `%.*s` copia `len` bytes (NULs incluidos). | Asigna un búfer nuevo; el llamador posee el resultado. |
| `pengu_string_concat` | `PenguString pengu_string_concat(PenguString a, PenguString b)` | Asigna y devuelve la cadena concatenada. | Asigna un búfer nuevo; el llamador posee el resultado. Las entradas `a`, `b` no cambian. |
| `pengu_string_equal` | `bool pengu_string_equal(PenguString a, PenguString b)` | Compara el contenido de bytes y la longitud para determinar la igualdad. | No asigna; las entradas se toman prestadas por valor. |
| `pengu_to_string` | `pengu_to_string(x)` | Macro genérica que convierte el primitivo `x` a `PenguString`. | Devuelve una cadena del heap con ownership para valores formateados, o una vista prestada. |
| `pengu_string_format` | `PenguString pengu_string_format(const char *fmt, ...)` | Asigna la cadena formateada mediante `vsnprintf`. | El llamador posee el `PenguString.data` devuelto. |
| `pengu_banish_string`| `void pengu_banish_string(PenguString *s)` | Libera el búfer de cadena del heap y anula el puntero de datos. | Libera el búfer de cadena del heap con ownership. |
| `pengu_banish_list`  | `void pengu_banish_list(PenguList *l)` | Libera el búfer dinámico de elementos de la lista y reinicia la longitud y la capacidad. | Libera el búfer de la lista. |
| `pengu_banish_map`   | `void pengu_banish_map(PenguMap *m)` | Libera las entradas del mapa y aplica banish recursivamente a las claves y los valores de tipo string. | Libera la tabla hash y las claves del heap. |
| `pengu_banish`       | `void pengu_banish(void *ptr)` | Llama al `free(ptr)` estándar del heap. | Libera la asignación del puntero sin procesar. |

### 13.5 Ownership de contenedores y copia profunda

Un `PenguList` / `PenguMap` puede llevar dos callbacks de ownership:

```c
typedef void (*PenguElemCleanup)(void *elem);              /* drop   */
typedef void (*PenguElemClone)(void *dst, const void *src); /* clone  */
```

```c
typedef struct {
    void *data; int len; int cap; size_t elem_size;
    PenguElemCleanup elem_cleanup;   /* called per element by pengu_banish_list */
    PenguElemClone   elem_clone;     /* called by pengu_list_push              */
} PenguList;

typedef struct {
    PenguMapEntry *entries; int len; int cap;
    size_t key_size, val_size;
    PenguElemCleanup key_cleanup, val_cleanup;
    PenguElemClone   key_clone,   val_clone;
} PenguMap;
```

* `pengu_list_new_owned(elem_size, cap, cleanup, clone)` y
  `pengu_map_new_owned(…)` registran los callbacks; el generador de código los emite
  automáticamente siempre que el tipo del elemento/clave/valor posea memoria (`string`,
  `list`, `map`, un rune con `derive Imago`, …).
* `pengu_list_push` **copia en profundidad** cuando `elem_clone` está definido
  (`memcpy` en caso contrario); `pengu_map_alloc_slot`/`pengu_map_put` hacen lo mismo
  por cada clave y valor.
* `pengu_banish_list` / `pengu_banish_map` invocan `*_cleanup` para cada elemento vivo
  antes de liberar el búfer, de modo que los contenedores anidados se liberan
  recursivamente (`list of string`, `map of string to list of int`, …).
* Los ayudantes `pengu_list_cleanup` / `pengu_list_clone` / `pengu_map_cleanup` /
  `pengu_map_clone` / `pengu_string_cleanup` / `pengu_string_clone` adaptan un
  contenedor o una cadena para usarlos como callback de elemento.
* **Invariante:** `elem_size` / `key_size` / `val_size` y los callbacks son inmutables
  una vez que el contenedor existe — el stride y el destructor deben mantenerse
  coherentes con los elementos ya almacenados.
* Los ayudantes de FFI `pengu_list_of_string_from_cstrs(arr, count)` y
  `pengu_list_of_string_from_cstrv(arr)` construyen una `list of string` con ownership a
  partir de un array de C, copiando cada cadena para que el llamador conserve el
  ownership de la entrada.

Como `push`/`put` copian, la variable de origen sigue liberándose mediante el
auto-banish (§13.4) y no hay aliasing entre el contenedor y el original:

```pengu
var rows as list of list of string is list of list of string
var row as list of string is ["a", "b"]     # owned
calling rows.push with row                  # deep copy into rows
# both 'row' and 'rows' own disjoint buffers; both are banished at scope exit
```

Los valores rune son distintos: un `rune` local que posee campos en el heap **no**
recibe auto-banish, así que libera explícitamente con `banish` (lo que requiere
`derive Nexus`, §9.1.2) o mantenlo dentro de un contenedor con ownership:

```pengu
rune Doc derive Par, Nexus:
    title as string
    tags as list of string

weave main into int:
    var d as Doc with:
        set .title is "spec!"
        set .tags is ["a", "b"]
    defer banish d          # -> _pengu_cleanup_Doc(&d) at scope exit
    ...
```

---

## 14. Módulos, imports e interoperabilidad con C

### 14.1 Imports y módulos

```pengu
import std.spark
import std.scrolls as s              # alias
import components.player             # project module (src/components/player.pengu)
```

#### Resolución, ordenación de dependencias y reglas de import:
- **Resolución de módulos:** las rutas con puntos se corresponden directamente con
  rutas de archivo relativas a `src/` o a las raíces configuradas (`components.player`
  -> `src/components/player.pengu` o `player.d.pengu`). Los módulos de la biblioteca
  estándar (`std.*`) se resuelven a la biblioteca estándar incluida con el compilador.
- **Ordenación topológica (`import_order`):** `resolve_imports` (`pengu_symbols.py`)
  visita los módulos recursivamente, calculando un orden topológico (post-orden inverso)
  para que las dependencias se comprueben de tipos y se emitan en C antes que sus
  dependientes.
- **Detección de dependencias circulares (`E0004`):** la resolución de dependencias usa
  un recorrido DFS de tres colores (`visited` / `visiting`). Si se vuelve a visitar un
  módulo activo, se detecta un ciclo de import circular y se lanza `SemanticError`
  (`E0004`), mostrando la ruta completa del ciclo (por ejemplo,
  `a.pengu -> b.pengu -> a.pengu`).
- **Imports duplicados (`E0004`):** importar el mismo módulo varias veces en el mismo
  archivo genera `E0004: Duplicate import of module '...'`.
- **Restricciones de alias en imports (`E0036`):**
  - **Alias de descarte prohibido:** ligar un import a `_` (`import std.math as _`)
    genera `E0036: Import alias cannot be '_' (discard)`.
  - **Conflictos con símbolos locales:** un alias que colisiona con un símbolo local
    existente en el módulo actual genera `E0036`.
- **Encapsulación (`E0043`):** los símbolos de nivel superior que empiezan por `_` son
  privados del módulo y no se pueden acceder desde los módulos que los importan
  (`E0043: PrivateSymbolAccessError`).

### 14.2 `include`, `link`, `insignia`, `declare`

```pengu
include "raylib.h"
link "raylib"
link "m"
insignia mylib_
```

- `include` añade la cabecera C al archivo generado.
- `link` añade la biblioteca al comando del enlazador.
- `insignia` cambia el prefijo C de todas las declaraciones y tipos posteriores del
  módulo (por ejemplo, `insignia pengu_` hace que `weave helper` pase a ser
  `pengu_helper` a nivel de C).
- `declare` proporciona firmas tipadas exactas para funciones C. Toda función C externa
  debe tener una firma `declare` explícita (`E0004` si se llama sin declaración).

**Cómo escribir constantes y variantes de enum de un binding.** Las variantes de `omen`
declaradas en un `.d.pengu` (`omen KeyboardKey:` + `KEY_RIGHT is 39`) son accesibles de
tres formas, y las dos primeras son las que hay que usar:

```pengu
import std.raylib

calling raylib.IsKeyDown with raylib.KEY_RIGHT                # bare module-qualified ✅
calling raylib.IsKeyDown with raylib.KeyboardKey.KEY_RIGHT   # nested: type-qualified ✅
calling raylib.IsKeyDown with KEY_RIGHT                      # unqualified ✅
calling raylib.SetConfigFlags with raylib.FLAG_MSAA_4X_HINT   # qualified #define / variant ✅
```

Se admiten las tres formas: cualificada por módulo sin más (`raylib.KEY_RIGHT`,
`raylib.FLAG_MSAA_4X_HINT`), cualificada por tipo (`raylib.KeyboardKey.KEY_RIGHT`) y sin
cualificar (`KEY_RIGHT`). También se admiten constantes con valor de struct como
`raylib.RAYWHITE` (su valor se emite tal como se define).


### 14.3 `ref to char`, `opaque`, `.d.pengu` y `bytes of`

Cadenas de C: pasa parámetros `ref to char`; los literales de cadena de PenguScript se
convierten automáticamente en punteros a cadena de C allí donde se espera un
`ref to char`. Usa `bytes of s` para vistas de bytes, y
`std.ffi.string_from_cstr` / `cstr_from_string` para idas y vueltas explícitas (semántica
con ownership vs. prestada, documentada en el módulo). Los handles opacos se declaran
`alias X as opaque` y se manejan mediante `ref to X`.

Archivos de **declaración** `.d.pengu`:

```pengu
# std/sqlite3.d.pengu (excerpt)
rune sqlite3:
    _ptr as opaque

declare sqlite3_open with filename as ref to char, ppDb as ref to opaque into int
```

- Solo registran tipos/firmas; las implementaciones viven en la cabecera C.
- Un `omen` declarado en un `.d.pengu` refleja un enum de la cabecera, así que el C
  emitido usa los nombres de variante **sin más** (`KEY_LEFT`, no
  `KeyboardKey_KEY_LEFT`).

### 14.4 Estructura y configuración del proyecto (`pengu.yaml` / `pengu.toml`)

Los proyectos de PenguScript se configuran mediante `pengu.yaml` o `pengu.toml`,
situados en la raíz del proyecto. Si existen ambos archivos, `pengu.toml` tiene
prioridad.

#### Esquema completo de `pengu.yaml`:

```yaml
name: my_app
version: 0.14.0
output: exe                  # exe | c | obj | static | shared
entry: src/main.pengu        # main entry module (defaults to src/main.pengu)
src_dirs: [src]              # source lookup roots (default: [src])
include_dirs: [include]      # additional C header search paths (-I)
lib_dirs: [lib]              # additional library search paths (-L)
links: [m, pthread]          # static / dynamic libraries to link (-l)
ldflags: []                  # raw linker flags
cflags: []                   # raw C compiler flags
defines: [ENABLE_LOGS]       # preprocessor macros (-D)
cc: gcc                      # default C compiler (gcc, clang)

profiles:
  debug:
    cflags: ["-g", "-O0"]
    defines: ["DEBUG=1"]
  release:
    cflags: ["-O3", "-DNDEBUG"]
    defines: []

assets:
  dir: "assets"              # directory relative to project root
  module: "arca"             # generated PenguScript module name (src/arca.pengu)
  embed: true                # true = embedded in .rodata; false = runtime disk reader
  exclude: ["*.tmp", "*.bak"]

dependencies:
  - name: my_c_lib
    git: "https://github.com/example/my_c_lib.git"
    build: "make"
```

#### Diseño de directorios del proyecto y artefactos de compilación:
- **Directorio `c/` para código de pegamento:** cualquier archivo `.c` o `.h` colocado
  en `./c/` se incluye, se compila y se enlaza automáticamente en el ejecutable final
  junto con `bundle.c`.
- **`lib/<binding>/pengu/`:** diseño de directorios estándar para los bindings de
  paquetes externos de PenguScript.
- **Directorio de compilación generado (`build/`):**
  - `build/bundle.c`: la unidad de traducción C unificada que emite el generador de
    código.
  - `build/arca_assets.c`: la tabla de datos de assets binarios incrustados que se genera
    cuando `assets.embed` está habilitado.
  - `build/lib/*.a`: archivos estáticos precompilados para el runtime de PenguScript
    (`libpengu_runtime.a`) y las bibliotecas C incluidas.
  - `build/include/`: archivos de cabecera de las bibliotecas C de terceros incluidas.

### 14.5 Patrones de estado a nivel de módulo (singletons y servicios)

Las declaraciones `var` y `let` de nivel superior están estrictamente prohibidas por
diseño (`E0002`). Todos los símbolos a nivel de módulo deben ser constantes en tiempo de
compilación (`const`).

Cuando crees servicios con estado, singletons, o necesites rastrear estado entre
llamadas, usa uno de estos dos patrones idiomáticos:

#### Patrón A: Estado encapsulado mediante `weave` de acceso con `static var`
El estado se contiene dentro de funciones de acceso usando `static var`. Una
`static var` mantiene su valor entre llamadas repetidas:

```pengu
# score_tracker.pengu
weave add_score with delta as int into int:
    static var score as int is 0
    set score is score + delta
    return score

weave get_score into int:
    return calling add_score with 0
```

**Estrategia de inicialización del codegen:**
- Para escalares constantes en tiempo de compilación (`int`, `float`, `bool`), el codegen
  emite un inicializador C estático simple: `static int32_t score = 0;`.
- Para inicializadores complejos, dinámicos o asignados en el heap, el codegen emite un
  booleano de guarda estático:
  ```c
  static MyStruct ctx;
  static bool ctx_initialized = false;
  if (!ctx_initialized) {
      ctx = ...;
      ctx_initialized = true;
  }
  ```

**Reglas y validación de `static var` (`_check_static_var_decl`):**
- **Solo hija directa de un weave (`E0035` / `E0002`):** `static var` debe declararse
  directamente dentro de un cuerpo de `weave`. Colocarla en el nivel superior del módulo
  genera `E0002`; anidarla dentro de bloques de control de flujo (`if`, `while`, `for`,
  `do:`, `or:`) genera `E0035`.
- **Identificador reservado `main` (`E0040`):** no se puede llamar `main`.
- **Arrays prohibidos (`E0035`):** las variables estáticas no pueden tener un tipo array
  (`array of T with size N`). Dado que los arrays de C no se pueden reasignar en tiempo
  de ejecución, los estáticos de tipo array se rechazan. Usa en su lugar un puntero
  (`ref to T`), un envoltorio de tipo rune o una `list of T`.
- **Tipado explícito de null (`E0014`):** inicializar una variable estática con `null`
  requiere una anotación de tipo explícita (por ejemplo,
  `static var buf as ref to byte is null`; `static var buf is null` sin tipo genera
  `E0014`).

#### Patrón B: Struct de contexto explícito (`ref to Context`)
Un patrón reentrante y thread-safe en el que el módulo define un `rune` de estado y las
funciones reciben una referencia:

```pengu
rune AudioContext:
    volume as float
    is_muted as bool

weave init into AudioContext:
    return with volume is 1.0, is_muted is false

weave set_volume with ctx as ref to AudioContext, vol as float into void:
    set ctx->volume is vol
```

---

## 15. Literales: cadenas, arrays, mapas, bloques indentados y rangos

### 15.1 Números, caracteres, booleanos, null

```pengu
42  -7  0xFF  0b101  1_000        # integers
1.5  -0.25  2e3                    # floats
'A'  '\n'  '\x41'                  # characters
true  false  null
```

- **`null`:** el literal `null` representa un puntero nulo. Requiere un contexto con un
  tipo de puntero esperado (`var p as ref to int is null`). Las declaraciones `null`
  sueltas y sin anotaciones de tipo generan `E0014: TypeMismatchError`.

### 15.2 Cadenas

```pengu
let a as string is "plain"
let b as string is "value: {x} and {name}"      # interpolation → pengu_string_format
let c as string is r"raw \n no escapes"          # raw single-line
let d as string is """triple
   quoted   string"""                            # dedented multiline
let e as string is r"""raw triple"""             # raw + multiline
```

- **La interpolación (`{expr}`) es *el* operador de composición de cadenas.** Emite
  `pengu_string_format` usando especificadores de formato específicos del tipo:
  - `%c` para `char` y `byte`
  - `%d` para enteros con signo y sin signo (`int`, `i8`..`i64`, `u8`..`u64`)
  - `%f` para números en coma flotante (`float`, `f32`, `f64`)
  - `%s` para `bool` (`"true"` / `"false"`)
  - `%.*s` para `string` (pasando `.len` y `.data`)
  - `%s` para punteros a cadena de C (`ref to char`)
  Pasar tipos complejos no soportados (por ejemplo, runes) sin conversión genera un
  error del compilador.
- **Composición exacta a nivel de byte:** un argumento `string` interpolado se copia
  usando su longitud, no la regla `%s` terminada en NUL de `printf`. Por eso `"a{nul}b"`
  conserva el `\0` incrustado y tiene 3 caracteres — las cargas binarias (digests hash,
  decodificadores Base64/hex) sobreviven a la composición. Ten en cuenta que `%f` y
  `to string` formatean los floats de manera distinta (`0.500000` vs `0.5`); usa la
  conversión explícita cuando la forma textual importe.
- **Comillas dentro de `{expr}`:** la expresión interpolada puede contener un literal
  entre comillas dobles (`"v={(calling getenv_or with k, "")}"`). Las expresiones con
  llaves desequilibradas no están soportadas dentro de un literal; constrúyelas en una
  variable local.
- **Por qué `+` no es un operador de cadena:** `"a" + b` genera `E0005`. Existe
  exactamente una forma de construir una cadena dinámica, así que no hay ambigüedad
  entre `+` sobre números y `+` sobre texto, ni promoción implícita `to string`, ni una
  asignación oculta adicional en cada concatenación. Convierte explícitamente cuando lo
  necesites (`"{b}"` o `b to string`) y acumula con interpolación:

  ```pengu
  # instead of:  "Hello, " + name
  let greeting as string is "Hello, {name}"

  # instead of:  set acc += item
  set acc is "{acc}{item}"      # O(n²) in a loop: prefer a 'list of string' + join
  ```

- **Cadenas entre comillas triples (`"""..."""`):** eliminan automáticamente la
  indentación inicial común.
- **Cadenas raw (`r"..."` y `r"""..."""`):** tratan las barras invertidas, las secuencias
  de escape y las llaves de forma literal, sin interpolación. Son esenciales para
  shaders GLSL/HLSL, patrones de expresiones regulares y plantillas incrustadas.

### 15.3 Arrays, listas, slices y mapas

```pengu
const MAX as int is 3
let nums as array of int with size MAX is [10, 20, 30]   # size by const name
let dyn as list of int is list of int                    # growable PenguList
let sl as slice of int is nums at 1 to 3                 # non-owning view
let m as map of string to int is map of string to int
```

- **Tamaño de array mediante identificador constante:** los arrays fijos admiten
  dimensionarse con nombres de constantes (`array of T with size NAME`), donde `NAME` se
  resuelve desde la tabla de símbolos durante la comprobación semántica (`ast_to_type`).
- **Literales entre corchetes (`[1, 2, 3]`):** producen arrays fijos en la pila. Los
  tipos de los elementos deben ser mutuamente compatibles (`E0005`).
- **Arrays multidimensionales:** se declaran con la dimensión externa primero:
  ```pengu
  var grid as array of array of f32 with size 2 with size 3 is [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
  ```
  Emite `float grid[2][3]`. La dimensión interna se puede omitir si se infiere de las
  filas. Las filas deben tener longitudes idénticas (`E0041: ArraySizeMismatchError`).
- **Orden de iteración de los mapas:** iterar sobre un mapa visita los slots en el orden
  interno de la tabla hash, no en el orden de inserción.

### 15.4 Literales por indentación

Los arrays, los mapas y los literales de struct se pueden declarar con una sintaxis
limpia de bloque indentado:

```pengu
var grid as array of array of int with size 2 with size 3 is:
    1, 2, 3
    4, 5, 6

var lookup as map of string to int is:
    "one": 1
    "two": 2

var p as Player is:
    name is "Ada"
    hp is 100
```

### 15.5 Rangos y pertenencia

```pengu
1 to 10         # PenguRange [1, 10), end-exclusive
1..10           # alternate range syntax
for i in 1 to 5: ...
if x in 0 to 100: ...
```

- Los rangos son semiabiertos (`[start, end)`).
- **Validación de rangos en tiempo de compilación (`E0042`):** cuando el inicio y el fin
  se conocen en tiempo de compilación, se exige `start <= end` para los rangos
  positivos. Si `start > end` sin un paso negativo, el compilador genera
  `E0042: InvalidRangeError`.

---
## 16. Compilación condicional (`when`)

PenguScript evalúa los bloques `when` estrictamente en tiempo de compilación, antes de la comprobación semántica y de la generación de código C. Las ramas inactivas se podan por completo del AST y no emiten nada de C.

### Tres formas de `when`:

#### 1. Declaraciones de nivel superior (`when_top_decl`)
Incluye o excluye condicionalmente funciones, tipos, constantes o bindings. Admite ramas encadenadas `else when` y un `else:` de reserva:

```pengu
when os == "windows":
    include "windows.h"
    declare Sleep with dwMilliseconds as u32 into void
else when os == "linux":
    include "unistd.h"
    declare usleep with usec as u32 into int
else:
    declare dummy_sleep into void
```

Las ramas de `when_top_decl` se evalúan en tiempo de compilación mediante `_active_when_top_stmts`. Solo las sentencias de la rama activa se registran en la tabla de símbolos y se comprueban de tipos; las ramas inactivas se podan antes del análisis semántico.

#### 2. Bloques y cadenas de sentencias (`when_stmt`)
Ramificación en tiempo de compilación dentro de cuerpos de función, con soporte de cadenas `else when` y un `else:` final:

```pengu
weave sleep_ms with ms as int into void:
    when os == "windows":
        calling Sleep with (ms to u32)
    else when os == "linux" or os == "macos":
        calling usleep with ((ms * 1000) to u32)
    else:
        calling spark.println with "Unsupported OS"
```

#### 3. Forma de expresión (`when_expr`)
Expresión ternaria en tiempo de compilación:

```pengu
let buffer_size as int is when arch == "x64" then 8192 else 4096
```

### Variables de comptime e intrínsecos:
- **`defined(NAME)`:** Se evalúa como `true` si el identificador `NAME` se proporcionó mediante `-D NAME` o existe en el entorno predefinido del compilador.
- **`main`:** `bool`. Se evalúa como `true` **solo** para el módulo de punto de entrada del proyecto (`compile_env.is_main`). Cuando se pasa el flag de CLI `-D main` o `-D main=true` (p. ej. `pengu build -D main` o `pengu run main.pengu -D main`), `main_flag_requested` habilita la semántica de main de entrada exclusivamente para el módulo de entrada; los módulos secundarios importados siempre se compilan con `is_main = false`, lo que evita puntos de entrada en conflicto.
- **`debug`:** `bool`, `true` al compilar con el perfil `debug` o con `-D debug`; `false` con `--profile release`.
- **`os`:** Constante de cadena que coincide con el sistema operativo destino (`'windows'`, `'linux'`, `'macos'`, `'freebsd'`).
- **`arch`:** Constante de cadena que coincide con la arquitectura de CPU destino (`'x64'` / `'x86_64'`, `'arm64'`, `'x86'`).
- **`compiler`:** Constante de cadena que coincide con el compilador de C destino (`'gcc'`, `'clang'`, `'msvc'`).
- Las condiciones no constantes en las construcciones `when` provocan `E0039: SemanticError`.

---

## 17. Pruebas unitarias (`test`)

PenguScript ofrece soporte de pruebas unitarias de primera clase, integrado directamente en el lenguaje y en el toolchain.

```pengu
test "arithmetic":
    calling expect_eq_int with 1 + 1, 2

test string_formatting:
    calling expect_eq_string with "abc", "abc"
```

- **Definición:** los bloques de prueba se declaran con `test <name>:`, donde `<name>` puede ser un literal de cadena o un identificador.
- **Validación semántica:** los cuerpos de prueba se validan semánticamente y se comprueban de tipos en **todos** los modos de compilación (`pengu check`, `pengu build`, `pengu run`, `pengu test`) mediante `_check_test_decl`. Los errores de sintaxis y de tipos dentro de los bloques de prueba aparecen de inmediato, incluso durante compilaciones normales.
- **Aislamiento del codegen de C:** los arneses de prueba de C, los weaves del ejecutor de pruebas y las llamadas de ejecución de pruebas solo se emiten al compilar en modo `--test` (`pengu test`). Los ejecutables de producción y las compilaciones de bibliotecas omiten por completo el código de prueba.
- **Declaraciones:** los bloques `test` dentro de archivos de declaración `.d.pengu` están estrictamente prohibidos (`E0025`).

### Ejecutar las pruebas

```console
$ pengu test              # Compile and execute all test blocks in project
$ pengu test --watch      # Watch mode: monitor .pengu sources and rerun on change
$ pengu test --json       # Machine-readable JSON Lines (JSONL) events for CI
```

- **Modo watch (`--watch`):** sondea continuamente los archivos fuente del proyecto (`mtime`), limpia el terminal y vuelve a ejecutar las pruebas cuando hay cambios.
- **Salida para CI (`--json`):** emite eventos estructurados JSON Lines a stdout (`start`, `test_start`, `test_pass`, `end`), manteniendo stderr limpio.

---

## 18. Construcción en estilo bloque (expresiones `with:`)

Para la construcción de structs complejos y la mutación in situ, PenguScript ofrece bloques constructores `with:`. Un bloque `with:` asigna un temporal puesto a cero y se evalúa como el valor de struct resultante:

```pengu
rune Point:
    x as int
    y as int

enchanting Point:
    weave shift with dx as int, dy as int into void:
        set self->x is self->x + dx
        set self->y is self->y + dy

weave main into int:
    var p as Point with:
        set .x is 10
        set .y is 20
        calling .shift with 5, 3     # call enchanting method on temporary
    return p.x + p.y                 # 38
```

### Reglas y validación de los constructores (`E0014`):
- **Sentencias permitidas:** dentro de los bloques constructores solo se permiten asignaciones `set .field is expr` y llamadas a métodos sobre el destino (`calling .method with ...` o llamadas normales).
- **Sentencias prohibidas:** las sentencias de flujo de control (`if`, `while`, `for`, `return`, `break`, `continue`), las declaraciones de variables (`var`, `let`) y la gestión de memoria (`defer`, `banish`) se rechazan estrictamente con `E0014: InvalidBuilderStatementError`.
- **Reglas de mutabilidad del destino:**
  - `var x with:` o `with var_target:`: mutable, los campos se pueden modificar.
  - `let x with:` (valor de rune): binding inmutable tras la construcción.
  - `with let_val:`: intentar mutar un rune `let` inmutable existente provoca `E0006: MutabilityError`.
  - `with let_ptr:` (donde `let_ptr as ref to T`): mutable, porque un `ref to T` apunta a memoria mutable.
  - `frozen T` o `ref to frozen T`: inmutable; la modificación de un campo provoca `E0006`.
- **Lowering de sentencia-expresión en el codegen:**
  ```c
  __extension__(({
    Point _with_1 = {0};
    _with_1.x = 10;
    _with_1.y = 20;
    Point_shift(&_with_1, 5, 3);
    _with_1;
  }))
  ```

### Anidar bloques `with:`

Un constructor `with:` se puede anidar a cualquier profundidad. Los constructores internos infieren sus tipos destino a partir de los campos a los que se asignan, sin necesidad de anotaciones de tipo redundantes:

```pengu
rune Address:
    street as string
    city as string
    zip as string

rune Person:
    name as string
    age as int
    address as Address

weave build into Person:
    return with:                       # target type inferred from weave return type
        set .name is "Ada"
        set .age is 30
        set .address is with:          # target type inferred as Address
            set .street is "123 Main St"
            set .city is "New York"
            set .zip is "12345"

weave rename into void:
    var p as Person with:
        set .name is "Ada"
        set .age is 30
        set .address is with:
            set .street is "1 First Ave"
            set .city is "Springfield"
            set .zip is "00001"

    with p:                            # edit the existing rune
        set .name is "Grace"
        set .address is with:          # nested builder, same inference rules
            set .street is "2 Second Ave"
            set .city is "Shelbyville"
            set .zip is "00002"
```

Reglas y garantías:

- El constructor interno hereda su tipo destino del campo al que se asigna
  (`Person.address` en el ejemplo anterior). No se requiere ninguna anotación adicional.
- El anidamiento funciona a cualquier profundidad; cada nivel asigna su propio
  temporal implícito de C (`_with_N`), así que los constructores internos y externos
  nunca chocan.
- `set .field is <block>` acepta cualquier bloque de valor (véase §7.6), incluidos
  constructores `with:` anidados, `if`/`unless` en posición de valor, bloques `do:`
  y bucles en posición de valor.
- La comprobación de tipos no cambia: un nombre de campo incorrecto (al estilo de `E0013`), un campo
  ausente o un desajuste de tipos dentro de un constructor anidado siguen provocando el mismo
  diagnóstico que provocarían en el nivel superior.
- El C generado es una statement-expression de GNU por constructor
  (`({ Person _with_N = {0}; …; _with_N; })`), así que el anidamiento se traduce de forma natural.

El constructor `with:` también es el valor de iteración dentro de un bucle en posición de valor
(§7.6), lo que te permite construir colecciones de runes compuestos sin repetir
el tipo destino:

```pengu
var ps as list of Person is for i from 0 to 3:
    with:                              # element type comes from 'list of Person'
        set .name is "p"
        set .age is i
        set .address is with:
            set .street is "s"
            set .city is "c"
            set .zip is "z"
```

El literal de struct en una línea `with x is …, y is …` no cambia, y cada
valor de campo puede ser a su vez un valor de bloque (un bloque multilínea debe ser el último
campo, o la `,` siguiente debe empezar en una línea nueva) —
véase [§7.6](#76-block-expressions-do-value-position-if--unless-and-loops).

> [!NOTE]
> Los miembros de un bloque se escriben con el `.` implícito (`set .x is 10`), de forma coherente
> con los ámbitos `with target:`. `set x is 10` dentro del bloque asignaría una
> *variable local* llamada `x`, que normalmente no existe.
>
> Un bloque constructor es en sí mismo un valor, así que puede aparecer en cualquier lugar donde
> se espere un valor: como inicializador de campo (anidamiento, arriba), como valor de iteración de un bucle,
> como rama de un `if`/`unless` en posición de valor y como cola de un bloque `do:`.
> La anotación `as T` en `var`/`let`/`static var` solo es necesaria en el
> nivel más externo; los constructores internos infieren su tipo a partir del campo al que
> se asignan.

### 18.2 Ámbitos `with` sobre colecciones (`list` y `map`)

La sentencia `with` también opera directamente sobre colecciones existentes (`list of T` y `map of K to V`, o referencias a ellas `ref to list of T` / `ref to map of K to V`). Dentro del bloque, las llamadas a métodos con punto inicial invocan los métodos integrados de la colección sin repetir el nombre de la variable de la colección:

```pengu
var scores as list of int is list of int
with scores:
    calling .push with 10
    calling .push with 20
    calling .push with 30

var registry as map of string to int is map of string to int
with registry:
    calling .put with "alpha", 1
    calling .put with "beta", 2
```

Métodos integrados admitidos dentro de los bloques `with` de colecciones:
- **`list`:** `.push(item)`, `.append(item)`, `.pop()`, `.clear()`, `.contains(item)`, `.index_of(item)`, `.at(idx)`, `.len()`, `.is_empty()`
- **`map`:** `.put(key, val)`, `.insert(key, val)`, `.set(key, val)`, `.get(key)`, `.remove(key)`, `.contains(key)`, `.len()`, `.is_empty()`, `.clear()`

---

## 19. Biblioteca estándar

PenguScript incluye una biblioteca estándar completa compuesta por **52 módulos**:
- **27 módulos de PenguScript puro** (`std.<module>`) que ofrecen abstracciones idiomáticas de alto nivel para E/S, cadenas, concurrencia, redes, serialización, matemáticas, pruebas y puentes de memoria.
- **25 módulos de binding de declaraciones de C** (`std.<binding>`, implementados mediante `.d.pengu`) que ofrecen acceso directo y sin sobrecarga a bibliotecas nativas de C (Raylib, SQLite3, WebUI, STB, etc.) conservando la documentación upstream 1:1.

### `print` integrado
`print` es un builtin del compilador que se traduce directamente a `printf` según el tipo del argumento (`print "hello"`, `print 42`, etc.). Para impresión estructurada o formateada con más opciones, usa `std.spark.println` o `std.spark.print`.

### 19.1 Módulos de PenguScript puro (27 módulos)

Todos los módulos puros se encuentran en el directorio `std/` y se importan como `import std.<module>`.

| Módulo | Propósito y capacidades principales |
|---|---|
| `std.spark` | E/S fundamental y runtime central: `print`, `println`, `print_line`, `input`, `panic`, conversiones numéricas (`str_int`, `parse_int`, `parse_float`), rangos de enteros (`range_to`, `range_inclusive`), helpers numéricos (`min_int`, `max_int`, `abs_int`, `clamp_int`), variantes de impresión tipadas (`print_int`, `println_int`, `print_float`, `println_float`, `print_bool`, `println_bool`), `eprintln` y entrada tipada (`read_line`, `read_int`, `read_float`). |
| `std.scrolls` | Manipulación de cadenas de alto nivel mediante métodos de enchanting y funciones de módulo: conversiones de mayúsculas/minúsculas (`capitalize`, `title`, `swap_case`, `to_snake_case`, `to_kebab_case`, `upper`, `lower`), búsqueda y métricas (`find`, `rfind`, `count`, `line_count`, `word_count`), recorte y relleno (`trim`, `lstrip`, `rstrip`, `ljust`, `rjust`, `zfill`, `center`), prefijos y divisiones (`removeprefix`, `removesuffix`, `partition`, `split`, `split_lines`), acceso a caracteres y bytes (`chars`, `bytes`), formato (`ellipsis`, `join`), validaciones (`is_lower`, `is_upper`, `is_space`, `is_palindrome`, `starts_with`, `ends_with`, `contains`) y ordenación de tres vías mediante `compare` (la forma canónica de ordenar y comparar cadenas en PenguScript, ya que `< <= > >=` están prohibidos con `string`). |
| `std.oracle` | Helpers de unwrap y propagación de contenedores con API nativa/heredada dividida: constructores nativos (`some_int`, `some_float`, `some_string`, `some_bool`, `none_*`), unwrappers nativos (`unwrap_*`, `unwrap_or_*`), helpers de result nativos (`is_ok_int_result`, `is_err_int_result`, `unwrap_int_result`, `unwrap_or_int_result`), conversiones puente entre runes heredados y contenedores nativos (`to_native_*`, `from_native_*`), formateadores de cadenas (`describe_int`, `describe_string`, `describe_result_*`, `describe_maybe_*`) y runes heredados (`MaybeInt`, `ResultInt`, etc.) con `is_none`, `is_err` y `unwrap_or` basados en `judge`. |
| `std.compass` | Manipulación de rutas del sistema de archivos multiplataforma: `join`, `join_all`, `basename`, `filename`, `dirname`, `ext`, `stem`, `file_stem`, `with_extension`, `without_extension`, `with_filename`, `add_ext`, `normalize`, `is_absolute`, `is_relative`, `is_root`, `is_hidden`, `is_unc`, `has_wildcard`, `matches` (coincidencia de patrones glob con `*` y `?`), `parent`, `split`, `components`, `has_component`, `cwd`, `expand_user`, `absolute`, consultas de separadores (`separator`, `alt_separator`, `is_windows`, `is_unix`) y el rune `Path` (`from_str`, `cwd`, `new_path`, `current_dir`) con métodos encadenables de consulta y transformación (`to_string`, `name`, `parent`, `stem`, `suffix`, `suffixes`, `drive`, `parts`, `components`, `is_absolute`, `is_relative`, `is_root`, `has_suffix`, `has_suffix_with`, `is_empty`, `is_hidden`, `matches`, `exists`, `is_file`, `is_dir`, `to_absolute`, `expand_user`, `to_uri`, `normalize`, `relative_to`, `with_suffix`, `with_name`, `add_suffix`, `without_suffix`). |
| `std.archivum` | Operaciones del sistema de archivos: E/S de archivos de texto y binarios (`read_file`, `read_bytes`, `write_file`, `write_bytes`, `append_file`, `append_bytes`), operaciones por líneas (`read_lines`, `read_first_n_lines`, `count_lines`, `write_lines`, `append_lines`), ciclo de vida de archivos (`delete_file`, `copy_file`, `move_file`, `rename`, `touch`), predicados de entradas (`exists`, `is_file`, `is_dir`, `is_symlink`, `is_empty_file`, `is_empty_dir`), operaciones de directorios (`create_dir`, `remove_dir`, `read_dir`, `copy_tree`, `list_files_recursive`), búsqueda y recorrido (`find_files`, `find_dirs`, `find_by_name`, `find_by_ext`, `glob`, `walk`), manejo de symlinks y rutas canónicas (`symlink`, `read_symlink`, `realpath`), helpers de sistema de archivos temporales (`temp_dir`, `temp_file`) e inspección exhaustiva de metadatos (`metadata`, `file_size`, `dir_size`, `modified_time`, `created_time`, `accessed_time`, `permissions`). |
| `std.cipher` | Codificaciones criptográficas, hashing y manipulación de JSON: Base64 y variantes (`encode_base64`, `decode_base64`, `is_base64`, `encode_base64_url`, `decode_base64_url`, `encode_base64_unpadded`, `encode_hex`, `decode_hex`, `is_hex`, `encode_base32`, `decode_base32`, `is_base32`), enchantments de cadenas (`to_base64`, `from_base64`, `to_base64_url`, `from_base64_url`, `to_hex`, `from_hex`, `to_base32`, `from_base32`), escape/unescape de JSON (`json_escape`, `json_unescape`), arrays JSON (`parse_json_array`, `stringify_json_array`), getters tipados (`json_get`, `json_get_int`, `json_get_float`, `json_get_bool`, `json_get_string`), navegación (`json_deep_clone`, `json_merge`, `json_path`, `json_parse_at`) y validación (`omen JsonKind`, `json_kind_of`, `is_valid_json`). |
| `std.chronicle` | Gestión de fechas, horas, calendario y temporizadores: relojes y retardos (`time`, `now_ms`, `time_ms`, `monotonic`, `monotonic_ms`, `sleep`, `sleep_ms`), conversión y análisis de cadenas formateadas (`format`, `format_now`, `parse`, `from_iso`, `to_iso`, `to_date_string`, `to_time_string`, `to_datetime_string`, `now_utc_iso`, `now_local_iso`, `now_date`, `now_time`), getters de componentes de calendario UTC y local (`utc_year`, `utc_month`, `utc_day`, `utc_hour`, `utc_minute`, `utc_second`, `utc_weekday`, `utc_yearday`, `utc_is_dst`, `local_year`, `local_month`, `local_day`, `local_hour`, `local_minute`, `local_second`, `local_weekday`, `local_yearday`, `local_is_dst`), helpers y límites de calendario (`is_leap_year`, `days_in_month`, `days_in_year`, `start_of_day`, `end_of_day`, `today`, `yesterday`, `tomorrow`, `start_of_month`, `start_of_year`), aritmética y relaciones de timestamps (`add_seconds`, `add_minutes`, `add_hours`, `add_days`, `add_weeks`, `diff_seconds`, `diff_days`, `is_before`, `is_after`, `is_between`), helpers de duración (`format_duration`, `parse_duration`), el rune `DateTime` (`datetime_utc`, `datetime_local`, `to_iso`, `to_date`, `to_time`) y el rune de temporizador monotónico de alta resolución `Stopwatch` (`new`, `new_stopwatch`, `elapsed_sec`, `elapsed_ms`, `reset`). |
| `std.lot` | Generación de números pseudoaleatorios (PRNG), muestreo y distribuciones estadísticas: gestión de estado LCG (`seed`, `next_int`, `next_float`, `rand_int`, `rand_float`), distribuciones continuas y discretas (`rand_uniform`, `rand_gauss`, `rand_exp`, `rand_between`, `rand_sign`, `rand_bit`, `rand_coin`, `rand_bool_with`, `rand_triangular`, `rand_lognormal`, `rand_weibull`, `rand_gamma`, `rand_beta`), muestreo y mezcla de colecciones (`choice`, `choice_string`, `choice_weighted`, `choice_weighted_string`, `shuffle`, `shuffle_string`, `sample`, `sample_with_replacement`, `sample_string`, `permutation`) y generadores de cadenas aleatorias (`rand_alpha`, `rand_digit_string`, `rand_alnum_string`, `rand_hex_string`, `rand_bytes_hex`, `rand_password`, `rand_from_charset`). |
| `std.rites` | Utilidades de procesos, entorno y sistema del sistema operativo: variables de entorno y gestión masiva (`getenv`, `setenv`, `unsetenv`, `get_env_keys`, `getenv_or`, `has_env`, `getenv_int`, `getenv_float`, `getenv_bool`, `get_env_map`, `set_env_map`, `clear_env`), expansión de variables (`expand_env`, `env_substitute`), argumentos del programa (`get_argc`, `get_argv`, `get_args`, `arg_at_or`, `parse_flags`, `has_flag`, `get_flag_value`), directorios estándar (`home_dir`, `temp_dir`, `config_dir`, `cache_dir`, `data_dir`), inspección de plataforma (`uname`, `hostname`, `os_arch`, `os_family`, `is_windows`, `is_unix`, `is_macos`, `is_linux`), resolución de ejecutables (`which`, `which_all`), identidad y control de procesos (`getpid`, `getppid`, `getcwd`, `chdir`, `exit`, `exec`, `spawn`, `exec_ok`, `exec_or_panic`, `run_shell`, `shell_escape`, `current_user`). |
| `std.whisper` | Logging estructurado por niveles con niveles de severidad (`LOG_TRACE` hasta `LOG_FATAL`, `COLOR_*`): helpers globales (`log`, `trace`, `debug`, `info`, `warn`, `error`, `fatal`, `set_level`, `get_level`, `get_level_name`, `get_level_color`, `is_enabled`, `set_level_from_string`, `set_level_from_env`, `fatal_and_exit`, `log_json`, `log_levels`) y el rune orientado a objetos `Logger` (`Logger.new`, `Logger.named`, `Logger.from_env`, `default_logger`) con métodos (`.log`, `.trace`, `.debug`, `.info`, `.warn`, `.error`, `.fatal`, `.set_level`, `.get_level`, `.is_enabled`, `.enable_timestamp`, `.disable_timestamp`, `.enable_color`, `.disable_color`, `.to_file`, `.child`, `.log_json`). |
| `std.ward` | Programación defensiva, aserciones de invariantes y validación de contratos con mensajes de fallo informativos: aserciones básicas (`assert_true`, `assert_false`, `assert_eq_int`, `assert_ne_int`, `assert_eq_string`, `assert_ne_string`, `assert_eq_bool`), tolerancia en coma flotante (`assert_eq_float`, `assert_ne_float`, `assert_almost_eq`), comprobaciones de orden y rango (`assert_gt_int`, `assert_ge_int`, `assert_lt_int`, `assert_le_int`, `assert_gt_float`, `assert_ge_float`, `assert_lt_float`, `assert_le_float`, `assert_in_range_int`, `assert_in_range_float`), validación de cadenas y contenedores (`assert_string_contains`, `assert_string_starts_with`, `assert_string_ends_with`, `assert_string_empty`, `assert_string_not_empty`, `assert_eq_int_list`, `assert_eq_string_list`, `assert_list_empty_int`, `assert_list_not_empty_int`, `assert_list_len_int`, `assert_map_has_key`, `assert_map_not_has_key`), aserciones genéricas de contenedores (`shard T`: `assert_maybe_present`, `assert_maybe_none`, `assert_result_ok`, `assert_result_err`), wrappers de prueba no fatales (`expect_*`, `check_*`) y utilidades de fallo de invariantes (`fail`, `fail_unreachable`). |
| `std.trial` | Framework de pruebas unitarias integrado: suites de pruebas, aserciones (`assert_eq`, `assert_true`), ejecutores de benchmarks e informes de pruebas estructurados. |
| `std.tally` | Utilidades para listas de enteros: aplica enchanting directamente sobre `list of int` (`calling xs.sum`, `calling xs.first`, `calling xs.reverse`) junto con funciones de nivel de módulo (`calling tally.sum with xs`). Incluye longitud y acceso (`len`, `first`, `last`, `at_or`, `at_safe`), búsqueda (`contains`, `index_of`, `count_of`, `find_first_gt`, `find_first_lt`), reducciones (`sum`, `product`, `max_val`, `min_val`, `max_index`, `min_index`), estadísticas (`mean`, `median`, `mode`), transformaciones (`reverse`, `sort_asc`, `sort_desc`, `unique`, `dedup`, `flatten`), selección (`take`, `drop`, `slice_list`), combinación (`concat`, `zip_sum`, `dot`, `repeat`), predicados, filtros (`filter_*`) y mapeos (`map_*`). |
| `std.atlas` | Utilidades de colecciones de tipo map multidato para 6 combinaciones clave-valor (`map of string to int`, `map of string to string`, `map of string to float`, `map of int to int`, `map of int to string`, `map of string to bool`). Aplica enchanting directamente sobre los tipos map (`calling m.keys`, `calling m.get_or with k, default`, `calling m.update with k, v`, `calling m.rename_key with old_k, new_k`, `calling m.clone`, `calling m.remove with k`, `calling m.clear`) junto con funciones de nivel de módulo (`calling atlas.keys with m`, `calling atlas.get_or_ss with m, k, def`). Incluye longitud y predicados (`size`, `is_empty`, `has_key`, `has_any_key`, `has_all_keys`), acceso (`get_or`, `get_safe`, `find_key_by_value`), mutación in situ (`update`, `rename_key`, `remove`, `clear`, `remove_all`), accesores masivos (`keys`, `values`, `keys_sorted`, `values_sorted`), reducciones numéricas (`sum_values`, `max_value`, `min_value`), contadores de bool (`count_true`, `count_false`), filtros y transformaciones (`filter_*`, `map_values_*`), combinación (`merge_*`, `merge_keep_left_*`), conversiones (`from_lists_*`, `to_keys_list`, `to_values_list`) y utilidades genéricas (`shard K, V`: `map_size`, `map_has_key`, `map_get_or`, `map_keys`, `map_values`, `map_put`, `map_remove`, `map_clear`). |
| `std.coven` | Colecciones de conjuntos únicos (`SetString`, `SetInt`): inserción y predicados (`add`, `contains`, `remove`, `len`, `clear`, `is_empty`), álgebra de conjuntos completa (`union`, `intersect`, `difference`, `symmetric_difference`, `is_subset`, `is_superset`, `is_disjoint`, `equals`), conversiones (`to_list`, `to_set_int`, `to_set_string`, `from_list`, `clone`) y filtros especializados (`filter_starts_with`, `filter_length_ge`). |
| `std.regulus` | Motor de expresiones regulares basado en PCRE2: compilación de regex (`compile`), coincidencia total/parcial (`match`, `search`, `is_match`, `is_full_match`, `is_match_at`), extracción de coincidencias (`find_all`, `match_count`, `match_at`, `match_offsets`), reemplazo de cadenas (`replace`, `replace_all`, `replace_fn`), división (`split`, `split_n`), utilidades de patrones (`escape`, `is_valid_pattern`, `flag_is_case_insensitive`) y métodos de enchanting de cadenas (`to_regex`, `matches_regex`, `regex_replace`, `regex_split`). |
| `std.parchment` | Parser de DOM de XML y HTML basado en libxml2: árboles de documento (`Document` con `parse_xml`, `parse_html`, `doc_to_string`), navegación y mutación de elementos (`Node` con `find`, `find_all`, `attr`, `set_attr`, `text`, `set_text`, `remove_child`), consultas al DOM (`find_by_id`, `find_by_class`, `find_all_by_class`, `has_class`, `add_class`, `remove_class`), utilidades de etiquetas (`is_void_element`, `normalize_tag`, `is_valid_tag_name`), limpieza de HTML (`strip_html_tags`, `extract_text`) y enchantments de cadena/Node. |
| `std.seal` | Compresión de datos y digests criptográficos: CRC32, MD5, SHA-1, SHA-256, SHA-512, HMAC (RFC 2104: `hmac_sha256`, `hmac_sha1`, `hmac_md5`), comparación en tiempo constante (`constant_time_eq`, `verify_sha256`, `verify_hmac_sha256`), deflate/inflate en bruto de zlib y compresión Gzip con métodos de enchanting de cadenas (`to_sha256`, `to_md5`, `to_crc32`, `to_gzip`, `from_gzip`). |
| `std.precis` | Programación de redes y protocolos web: cliente HTTP (`get`, `post`, `head`, `put`, `delete_req`), constructores de peticiones/respuestas HTTP (`Request`, `Response` con cabeceras y codificación de parámetros de consulta), servidor HTTP embebido (`serve_http`), predicados de códigos de estado (`is_success`, `is_redirect`, `is_client_error`, `is_server_error`, `status_text`) y códecs de URL (`url_encode`, `url_decode`, `parse_url`, `build_url`, `url_join`). |
| `std.filum` | Primitivas de concurrencia multihilo: exclusión mutua (`Mutex` con `lock`, `unlock`, `try_lock`, `free`), contadores de sincronización (`WaitGroup` con `add`, `done`, `wait`, `free`), guardas de una sola vez (`Once` con `do_once`, `do_action`, `free`), variables de condición (`Cond` con `cond_wait`, `wait_mutex`, `signal`, `broadcast`, `free`), enteros thread-safe (`AtomicInt` con `load`, `store`, `add`, `sub`, `inc`, `dec`, `inc_and_get`, `dec_and_get`, `swap`, `get_and_set`, `compare_swap`, `is_zero`, `reset`, `free`), canales tipados (`ChanInt`, `ChanString`, `ChanFloat`, `ChanBool` con `new`, `with_capacity`, `send`, `recv`, `close`, `len`, `cap`, `free`) y utilidades de sistema/tiempo (`sleep`, `sleep_sec`, `num_cpu`, `goroutine_id`). |
| `std.loom` | Generación de secuencias, transformaciones funcionales y algoritmos genéricos: secuencias (`range`, `repeat`, `take`, `skip`, `chain`, `chunks`, `windows`), reducciones (`mean`, `sum_squares`, `running_sum`, `running_max`, `running_min`, `differences`), predicados (`any_zero`, `all_equal`, `is_strictly_asc`, `is_strictly_desc`, `is_sorted_asc`, `is_sorted_desc`), transformaciones (`zip_with`, `zip_longest`, `enumerate`, `interleave`, `round_robin`, `rotate_left`, `rotate_right`, `intersperse`, `pairwise`, `flat_map_identity`), operaciones tipo conjunto ordenado (`union_sorted`, `intersect_sorted`, `difference_sorted`, `symmetric_difference_sorted`), búsqueda (`find_first`, `find_last`, `binary_search`, `count_if_even`, `count_if_positive`, `index_min`, `index_max`), modificaciones estructurales (`insert_at`, `remove_at`, `replace_at`, `swap_at`, `pad_left`, `pad_right`), estadísticas (`median`, `mode`, `variance`, `stddev`, `percentile`) y algoritmos genéricos (`shard T`: `first_or`, `generic_take`, `generic_take_last`, `generic_reverse`, `generic_chain`, `generic_index_of`). |
| `std.invoke` | Análisis de argumentos de interfaz de línea de comandos (CLI): sintaxis POSIX y GNU (`--flag`, `--key=value`, `-k=value`), negación de flags booleanos (`--no-flag`), subcomandos (`rune Subcommand`), opciones tipadas (int, float, bool, string, multi), opciones multi repetibles (`rune MultiOption`), sugerencias de erratas por Levenshtein, cadenas de ayuda y uso formateadas (`usage_string`, `full_help`), informes de error y variantes robustas de análisis (`parse`, `parse_no_exit`, `parse_or_exit`, `parse_or_usage`, accesores de `ParseResult` `get`, `get_or`, `get_int`, `get_int_or`, `get_float`, `get_float_or`, `get_bool`, `get_bool_or`, `get_all`, `to_map_values`, `to_map_flags`). |
| `std.ffi` | Puente de interfaz de funciones externas de C de bajo nivel: utilidades de punteros nulos (`null_void`, `null_char`, `null_byte`, `is_null`, `is_valid`, `ptr_eq`), constantes e inspección de arquitectura (`SIZEOF_POINTER`, `SIZEOF_INT`, `SIZEOF_FLOAT`, `pointer_size`, `size_of shard T`, `alignment_of shard T`), conversiones de cadenas C terminadas en nulo (`string_from_cstr`, `cstr_from_string`, `string_from_cstr_n`, `string_from_bytes`, `bytes_from_string`), vistas de memoria (`slice_from_ptr`), colecciones genéricas a partir de búferes de C (`list_from_ptr shard T`, `map_from_entries shard K, V`), copia/escritura de memoria en bruto (`memcpy_raw`, `memset_raw`) y 10 patrones canónicos de interoperabilidad con C. |
| `std.celeris` | Benchmarking de alta precisión y perfilado de rendimiento: temporizadores monotónicos de nanosegundos y suites de benchmark por iteraciones. |
| `std.xlsx` | Generación de libros de hojas de cálculo de Excel y extracción de datos de celdas. |
| `std.ledger` | Datos tabulares, análisis y serialización de CSV/TSV y operaciones con matrices: análisis (`parse_csv`, `parse_tsv`, `parse_line`, `detect_delimiter`, `parse_csv_strict`, `parse_csv_nocomments`, `parse_csv_skip`, `parse_line_strict`, `parse_csv_normalized`), abstracción de tabla `rune CsvTable` (`from_csv`, `from_rows`, `row_count`, `column_count`, `has_column`, `column_index`, `get`, `get_or`, `column`, `row_as_map`, `to_csv`), enchantments de matrices (`list of list of string`: `row_count`, `column_count`, `is_rectangular`, `column`, `transpose`), conversiones a mapas clave-valor (`parse_csv_as_pairs`, `parse_csv_key_value`, `write_key_value_map`), escape (`escape_field`, `escape_field_rfc4180`, `escape_field_backslash`), formateadores (`to_csv_string`, `to_tsv_string`, `to_csv_string_no_trailing_newline`, `to_csv_string_crlf`) y operaciones de archivos (`read_csv`, `read_tsv`, `write_csv`, `write_tsv`, `write_csv_safe`). |
| `std.arithmancy` | Álgebra lineal y funciones matemáticas avanzadas listas para juegos: constantes (`PI`, `TAU`, `E`, `EPSILON`), funciones escalares (`abs_i`, `abs_f`, `min_i`, `max_i`, `min_f`, `max_f`, `clamp_i`, `clamp_f`, `sqrt_f`, `pow_f`, `sin_f`, `cos_f`, `tan_f`, `asin_f`, `acos_f`, `atan_f`, `atan2_f`, `deg_to_rad`, `rad_to_deg`, `lerp_f`, `smoothstep_f`), vectores 2D (`rune Vec2` con `dot`, `cross`, `length`, `normalize`, `distance`), vectores 3D (`rune Vec3` con `dot`, `cross`, `length`, `normalize`, `distance`), vectores 4D (`rune Vec4`), matrices de transformación 4x4 (`rune Mat4` con `identity`, `translation`, `scaling`, `rotation_x/y/z`, `multiply`, `transpose`, `look_at`, `perspective`, `orthographic`) y cuaterniones (`rune Quat` con `identity`, `from_axis_angle`, `multiply`, `slerp`, `to_mat4`). |

### 19.2 Módulos de binding nativo de C (25 módulos `.d.pengu`)

Estos bindings de declaración exponen bibliotecas nativas de C sin sobrecarga de abstracción. El compilador enlaza las bibliotecas de C correspondientes durante la compilación:

| Módulo | Biblioteca nativa y descripción |
|---|---|
| `std.raylib` | **Raylib 5.x**: renderizado gráfico 2D y 3D, ventanas, audio, manejo de entrada, texturas y cámaras. |
| `std.raymath` | **Raylib Math**: matemáticas de vectores 2D/3D (`Vector2`, `Vector3`), matrices de transformación 4x4 (`Matrix`) y cuaterniones. |
| `std.rlgl` | **rlgl**: capa de abstracción gráfica de bajo nivel para OpenGL 1.1, 2.1, 3.3 y ES 2.0. |
| `std.rlights` | **rlights**: gestión de shaders con múltiples luces de Raylib (luces direccionales, puntuales y focos). |
| `std.raygui` | **raygui**: componentes de interfaz gráfica de usuario en modo inmediato (IMGUI) para Raylib. |
| `std.sqlite3` | **SQLite 3**: motor de base de datos relacional embebido y sin servidor, sentencias preparadas y ejecución de consultas. |
| `std.webui` | **WebUI**: binding de GUI de escritorio moderna que aprovecha el navegador web instalado por el usuario (Chrome, Edge, Firefox) mediante HTML/CSS/JS con RPC bidireccional. |
| `std.miniaudio` | **miniaudio**: reproducción de audio multiplataforma, mezcla multipista, grabación de sonido y audio espacial 3D. |
| `std.tomlum` | **tomlc99**: parser de archivos de configuración TOML rápido y conforme al estándar. |
| `std.yaml` | **libyaml**: parser conforme de documentos YAML de configuración y datos. |
| `std.uuid` | **RFC 4122 UUID**: generación, análisis y representación canónica en cadena de UUID versión 4 criptográficamente sólidos. |
| `std.xxhash` | **xxHash**: algoritmo de hash no criptográfico extremadamente rápido que opera al límite del ancho de banda de la RAM. |
| `std.xlsxio` | **libxlsxio**: lector y escritor de streaming en C de alto rendimiento para archivos Excel `.xlsx`. |
| `std.imago` | **stb_image**: carga de archivos de imagen (PNG, JPEG, BMP, TGA, PSD, GIF, HDR, PIC, PNM) desde disco o memoria. |
| `std.typis` | **stb_truetype**: carga de fuentes, decodificación de glifos vectoriales y rasterización a atlas de mapa de bits. |
| `std.scriptor` | **stb_sprintf**: implementación portátil y de alto rendimiento de `sprintf` sin dependencias de locale. |
| `std.perlinum` | **stb_perlin**: generación procedural de ruido Perlin y simplex para terrenos y texturas. |
| `std.stb_image_resize2` | **stb_image_resize2**: escalado de imágenes SIMD de alta calidad con filtros Catmull-Rom, Mitchell y Lanczos. |
| `std.stb_herringbone_wang_tile` | **stb_herringbone_wang_tile**: generación procedural de mapas no periódicos mediante teselas Herringbone Wang. |
| `std.nanosvg` | **NanoSVG**: parser vectorial SVG de una sola cabecera para extracción de trazados y teselado de polígonos. |
| `std.nanosvgrast` | **NanoSVGrast**: rasterizador software de alta velocidad para imágenes vectoriales NanoSVG. |
| `std.minicoro` | **minicoro**: corrutinas asimétricas con pila y conmutación de contexto de fibras. |
| `std.datastructura` | Estructuras de datos de C de alto rendimiento: búferes vectoriales dinámicos, hash maps y colas FIFO. |
| `std.fenestra` | Diálogos de ventana nativos multiplataforma: abrir archivo, guardar archivo, seleccionar carpeta, cuadros de mensaje y notificaciones emergentes. |
| `std.pactum` | Empaquetado de protocolos binarios compactos y serialización de mensajes de red sin esquema. |

### 19.3 Ejemplos básicos de la biblioteca estándar

#### Memoria e interoperabilidad con C (`std.ffi`)
Proporciona rutinas puente entre punteros de C y tipos de PenguScript. Las vistas de memoria **no** copian y **no** deben recibir `banish`; las conversiones que devuelven contenedores con ownership copian en profundidad su origen:

```pengu
import std.ffi
import std.spark

weave demonstrate_ffi with c_buf as ref to frozen byte, len as int into void:
    # 1. Borrow C memory as a slice view (zero allocations, non-owning)
    var view as slice of byte is calling ffi.slice_from_ptr with (transmute c_buf to ref to void), len
    calling spark.println with "Slice length: {(view.length to string)}"

    # 2. Convert null-terminated C string into an owned PenguScript string
    var c_str as ref to frozen char is transmute c_buf to ref to frozen char
    var owned_s as string is calling ffi.string_from_cstr with c_str

    # 3. Obtain non-owning null-terminated C string pointer from PenguScript string
    var back_to_c as ref to char is calling ffi.cstr_from_string with owned_s
    calling spark.println with "Converted string successfully"
```

#### Manipulación de cadenas (`std.scrolls`)
Algoritmos de cadenas en PenguScript puro que operan a través del enchantment del tipo `string`:

```pengu
import std.spark
import std.scrolls

weave demonstrate_strings into void:
    var raw as string is "  PenguScript,Systems,Language  "
    var trimmed as string is calling raw.trim
    var parts as list of string is calling trimmed.split with ","

    for part in parts:
        var upper_part as string is calling part.upper
        if calling upper_part.contains with "SYSTEMS":
            calling spark.println with "Found target: {upper_part}"

    var sub as string is calling scrolls.substring with trimmed, 0, 11
    calling spark.println with "Substring: {sub}"
```

#### Hashes criptográficos y compresión (`std.seal`)
Proporciona cálculo de digests y compresión de datos:

```pengu
import std.spark
import std.seal

weave demonstrate_seal with payload as string into void:
    # Calculate SHA-256 and MD5 hex digests
    var sha as string is calling seal.sha256 with payload
    var md5_sum as string is calling seal.md5 with payload
    calling spark.println with "SHA-256: {sha}"
    calling spark.println with "MD5: {md5_sum}"

    # Compress with Gzip
    var compressed as maybe string is calling seal.gzip with payload
    if compressed.is_present:
        var original as maybe string is calling seal.unzip with compressed.value
        if original.is_present:
            calling spark.println with "Roundtrip match: {(original.value == payload to string)}"
```

#### Redes y HTTP (`std.precis`)
Realiza peticiones HTTP salientes y opera con endpoints de socket:

```pengu
import std.spark
import std.precis

weave fetch_web_data with url as string into void:
    var headers as map of string to string is map of string to string
    var resp as maybe precis.ClientResponse is calling precis.get with url, headers

    if resp.is_present:
        var response as precis.ClientResponse is resp.value
        calling spark.println with "Status Code: {(response.status_code to string)}"
        if response.status_code == 200 and response.body.is_present:
            calling spark.println with "Body: {response.body.value}"
    else:
        calling spark.println with "Network request failed"
```

#### Concurrencia multihilo (`std.filum`)
Creación de hilos, exclusión mutua, wait groups y canales:

```pengu
import std.spark
import std.filum

weave worker_routine with wg_ptr as ref to filum.WaitGroup, m_ptr as ref to filum.Mutex into void:
    calling filum.lock with m_ptr
    calling spark.println with "Inside synchronized critical section"
    calling filum.unlock with m_ptr
    calling filum.done with wg_ptr

weave demonstrate_concurrency into void:
    var m as filum.Mutex is calling filum.mutex
    var wg as filum.WaitGroup is calling filum.wait_group

    calling filum.add with (sigil of wg), 1
    # Run worker tasks with explicit handle passing
    calling worker_routine with (sigil of wg), (sigil of m)
    calling filum.wait with (sigil of wg)

    calling filum.free_mutex with m
    calling filum.free_wait_group with wg
```

#### Expresiones regulares PCRE2 (`std.regulus`)
Coincidencia de patrones rápida, extracción de grupos y reemplazo:

```pengu
import std.spark
import std.regulus

weave demonstrate_regex into void:
    var re as regulus.Regex is calling regulus.compile with "[a-zA-Z]+@([a-zA-Z0-9-]+\\.[a-z]+)", "i"
    var m as maybe regulus.Match is calling regulus.search with re, "Contact: admin@penguscript.org"

    if m.is_present:
        var match_data as regulus.Match is m.value
        calling spark.println with "Matched text: {match_data.matched}"
        calling regulus.match_free with match_data

    var replaced as string is calling regulus.replace with re, "Send to user@domain.com", "[hidden]"
    calling spark.println with "Sanitized: {replaced}"
    calling regulus.regex_free with re
```

#### Gráficos interactivos 2D y 3D (`std.raylib` y `std.raymath`)
Pipeline interactivo de ventanas y renderizado:

```pengu
import std.raylib
import std.raymath
import std.ffi

weave main into int:
    var title as ref to char is calling ffi.cstr_from_string with "PenguScript Raylib Window"
    calling raylib.InitWindow with 800, 450, (transmute title to ref to frozen char)
    calling raylib.SetTargetFPS with 60

    var position as raymath.Vector2 is with x is 400.0, y is 225.0

    while not calling raylib.WindowShouldClose:
        calling raylib.BeginDrawing
        calling raylib.ClearBackground with raylib.RAYWHITE
        calling raylib.DrawCircle with (position.x to int), (position.y to int), 20.0, raylib.MAROON
        calling raylib.EndDrawing

    calling raylib.CloseWindow
    return 0
```

### 19.4 Recursos embebidos del proyecto (`arca`)

Los proyectos de PenguScript pueden empaquetar archivos estáticos (shaders, audio, imágenes, configuraciones, fuentes, plantillas, HTML/JS/CSS) directamente en el ejecutable mediante la característica `assets`. El compilador genera un módulo de PenguScript puro (por defecto: `src/arca.pengu`) y una implementación en C (`build/arca_assets.c`).

#### Configuración (`pengu.yaml`)

```yaml
assets:
  dir: "assets"           # directory relative to project root
  module: "arca"          # module name (generates src/arca.pengu)
  embed: true             # true = compiled into .rodata; false = runtime disk reader
  exclude: ["*.psd", "*.tmp"]
```

#### Referencia de la API (`arca`)

Todas las funciones son puras, seguras frente a nulos y autocontenidas:

| Función | Firma | Descripción |
|---|---|---|
| `count` | `weave count into int` | Número total de recursos rastreados. |
| `name` / `name_at` | `weave name with index as int into string` | Ruta relativa lógica del $i$-ésimo recurso (indexado desde 0). |
| `has` / `exists` | `weave has with name as string into bool` | `true` si existe un recurso con `name` y tiene un tamaño distinto de cero. |
| `size` | `weave size with name as string into usize` | Tamaño en bytes (0 si no se encuentra). |
| `ptr` | `weave ptr with name as string into ref to frozen void` | Puntero directo a los bytes del recurso en `.rodata` o en la caché del heap (`null` si no se encuentra). |
| `bytes` | `weave bytes with name as string into slice of byte` | Vista de slice sin ownership sobre los bytes del recurso (no aplicar `banish`). |
| `string` | `weave string with name as string into string` | Contenido como **cadena con ownership** (copia de `PenguString`, segura para `banish` o para almacenar). |

> [!NOTE]
> **Modelo de propiedad de memoria:**
> - `arca.string(name)` devuelve una **copia con ownership** del recurso como `string` (mediante `pengu_string_new`). Es seguro almacenarla en structs, pasarla entre hilos o liberarla con `banish`.
> - `arca.bytes(name)` y `arca.ptr(name)` devuelven **vistas de solo lectura** que referencian directamente la sección binaria embebida (`.rodata`) en modo `embed: true`, o la caché de memoria interna en modo `embed: false`. No asignan memoria en el heap y **nunca** deben recibir `banish` ni liberarse.

#### Formatos admitidos y agnosticismo de formato

La incorporación de recursos de PenguScript es completamente binaria y agnóstica al formato. Los bytes se conservan 1:1 sin modificación ni recodificación. Entre los tipos de archivo habituales se incluyen:
- **Imágenes**: PNG, JPG/JPEG, QOI, BMP, SVG
- **Audio**: WAV, OGG, MP3, QOA, FLAC
- **Shaders y 3D**: GLSL (`.vs`, `.fs`), HLSL, WGSL, OBJ, MTL, GLTF/GLB
- **Web y UI**: HTML, CSS, JS, WASM, JSON, SVG
- **Fuentes y datos**: TTF, OTF, FNT, TOML, YAML, CSV, archivos de base de datos SQLite

#### Constantes de recursos

Se emiten constantes para cada recurso rastreado con un formato de identificador determinista y libre de colisiones (`ASSET_<MODULE>_<CLEANED>_<SHA1_8>`):
- **`CLEANED`:** la ruta de archivo relativa con todos los caracteres no alfanuméricos reemplazados por guiones bajos y convertida a mayúsculas (`re.sub(r"[^A-Za-z0-9]", "_", name).upper()`). Si el nombre limpiado comienza por un dígito, se antepone un guion bajo `_` inicial.
- **`SHA1_8`:** los primeros 8 caracteres hexadecimales del digest SHA-1 en mayúsculas de la cadena de ruta relativa en UTF-8:
  ```python
  hashlib.sha1(name.encode("utf-8")).hexdigest()[:8].upper()
  ```
- **Prefijo:** `ASSET_` cuando se usa el módulo por defecto `arca`, o `ASSET_<MODULE>_` cuando se configura un nombre de módulo personalizado en `pengu.yaml` (p. ej. `ASSET_RECURSOS_`).

Esto garantiza identificadores únicos y conformes con C99 incluso cuando los nombres de archivo difieren solo en puntuación, separadores de ruta o mayúsculas/minúsculas:

```pengu
const ASSET_LOGO_PNG_A731E040 as string is "logo.png"
const ASSET_SHADERS_GRAYSCALE_FS_E362493E as string is "shaders/grayscale.fs"
```

Puedes pasar tanto la constante generada (`arca.ASSET_LOGO_PNG_A731E040`) como el literal de cadena (`"logo.png"` / `"shaders/grayscale.fs"`). Ejecuta `pengu assets --list` para ver todas las constantes y los tamaños de archivo.

#### Ejemplos de uso

**Carga de texturas y shaders de Raylib (memoria directa):**
```pengu
import arca
import std.raylib
import std.ffi
import std.spark

weave main into int:
    var title as ref to char is calling ffi.cstr_from_string with "Embedded Assets Demo"
    calling raylib.InitWindow with 800, 600, (transmute title to ref to frozen char)
    calling raylib.SetTargetFPS with 60

    # Load image from embedded buffer directly in memory (zero disk I/O)
    var p_logo as ref to frozen void is calling arca.ptr with "logo.png"
    var sz_logo as usize is calling arca.size with "logo.png"
    var ext as ref to char is calling ffi.cstr_from_string with ".png"
    var img as raylib.Image is calling raylib.LoadImageFromMemory with (transmute ext to ref to frozen char), (transmute p_logo to ref to frozen byte), (sz_logo to int)
    var texture as raylib.Texture2D is calling raylib.LoadTextureFromImage with img
    calling raylib.UnloadImage with img

    # Load shader from embedded string
    var fs_str as string is calling arca.string with "shaders/grayscale.fs"
    var fs_cstr as ref to char is calling ffi.cstr_from_string with fs_str
    var shader as raylib.Shader is calling raylib.LoadShaderFromMemory with (transmute 0 to ref to frozen char), (transmute fs_cstr to ref to frozen char)

    while not calling raylib.WindowShouldClose:
        calling raylib.BeginDrawing
        calling raylib.ClearBackground with raylib.RAYWHITE
        calling raylib.BeginShaderMode with shader
        calling raylib.DrawTexture with texture, 200, 150, raylib.WHITE
        calling raylib.EndShaderMode
        calling raylib.EndDrawing

    calling raylib.UnloadTexture with texture
    calling raylib.UnloadShader with shader
    calling raylib.CloseWindow
    return 0
```

**Aplicación autónoma con WebUI:**
```pengu
import arca
import std.webui
import std.spark

weave main into int:
    var w as int is calling webui.new_window
    # Retrieve embedded HTML interface
    var html as string is calling arca.string with "ui/index.html"
    calling webui.show with w, html
    calling webui.wait
    return 0
```

---

## 20. Herramientas y estructura del proyecto

El toolchain unificado de línea de comandos `pengu` gestiona la creación de proyectos, la compilación, las pruebas, el formato, la generación de bindings de cabeceras de C, la documentación y la integración con el Language Server Protocol (LSP).

### 20.1 Inicialización de proyectos (`pengu init`)

Genera un nuevo directorio de proyecto con la estructura de carpetas estándar, gitignore y código de plantilla:

```bash
pengu init <name> [--type {exe,c,obj,static,shared}] [--links LINKS] [--output-name OUTPUT_NAME] [--cc CC]
```

- `--type, -t`: Formato del artefacto destino:
  - `exe`: Ejecutable nativo autónomo (por defecto).
  - `c`: Bundle transpilado de código C en un solo archivo (`build/bundle.c`).
  - `obj`: Archivo objeto nativo compilado (`.o` / `.obj`).
  - `static`: Biblioteca estática compilada (`.a` / `.lib`).
  - `shared`: Biblioteca compartida de enlazado dinámico compilada (`.so` / `.dll` / `.dylib`).
- `--links, -l`: Bibliotecas nativas de C que enlazar, separadas por comas (p. ej. `raylib,m,pthread`).
- `--output-name`: Nombre base personalizado del binario de salida.
- `--cc`: Compilador de C alternativo (por defecto: `gcc`).

### 20.2 Compilación y perfiles de build (`pengu build`)

Compila el proyecto de PenguScript en el destino designado:

```bash
pengu build [--profile PROFILE] [--config CONFIG] [--entry ENTRY] [--output OUTPUT] [--test] [--cc CC] [--verbose] [-D DEFINES]
```

- `--profile, -p`: Selecciona los perfiles de optimización y diagnóstico:
  - `debug` (por defecto): Incluye símbolos de depuración (`-g`), comprobación de límites en runtime (`pengu_assert_bounds`), seguimiento de la pila de llamadas en runtime (`pengu_frame_push`/`pop`) y aserciones.
  - `release`: Maximiza el rendimiento (`-O3`), omite las comprobaciones de límites y desactiva el seguimiento de la pila de llamadas en runtime para lograr cero sobrecarga.
- `--test`: Incluye y compila todos los bloques `test` de nivel superior en el bundle del ejecutable.
- `-D, --define`: Define variables de tiempo de compilación para las condiciones `when` (p. ej. `-D os=linux`, `-D arch=x64`, `-D compiler=clang`, `-D debug`, `-D main`). Se puede repetir.
- `--verbose`: Emite tiempos detallados por fase, el orden de resolución de módulos y los comandos invocados del compilador de C.
- `--config, -c`: Ruta a un `pengu.yaml` personalizado o a la raíz del proyecto.
- `--entry, -e`: Sobrescribe el archivo de punto de entrada raíz (por defecto: `src/main.pengu`).
- `--output, -o`: Ruta de salida personalizada del destino (p. ej. `build/bundle.c` o `build/game.exe`).

### 20.3 Ejecución y modo script (`pengu run`)

Compila y ejecuta de inmediato el destino del proyecto:

```bash
pengu run [--profile PROFILE] [--config CONFIG] [--entry ENTRY] [--test] [--cc CC] [--verbose] [-D DEFINES] [script]
```

- `[script]`: Cuando se proporciona un archivo fuente `.pengu` opcional (p. ej. `pengu run hello.pengu`), el compilador lo ejecuta al vuelo como script autónomo, evaluando sus bloques condicionales `when main:` sin necesidad de un directorio de proyecto completo.
- **El binario compilado se cachea por hash de contenido** (`~/.cache/pengu/scripts/<key>/app`), así que un script sin cambios arranca en milisegundos y nunca toca el directorio `build/` del proyecto. `--keep` compila en `build/<name>_run/`; `--no-cache` omite la caché; `--ephemeral` usa un directorio desechable (CI) y `--clear-cache` vacía el almacén.
- Los argumentos posteriores a `--` se reenvían al script (`std.rites.get_args`).
- `PENGU_CACHE=0` desactiva las cachés; `PENGU_DEV_CC`/`PENGU_TCC`/`PENGU_NO_TCC` controlan la elección de compilador. Véase `docs/PERFORMANCE.md`.

### 20.3.1 Diagnósticos, caché y one-liners

| Comando | Qué hace |
| ------- | ------------ |
| `pengu doctor [--json]` | Informa sobre el compilador, la disponibilidad de TCC, la cabecera del runtime, `std/`, las rutas de caché y los permisos de escritura. |
| `pengu gc [--all] [--max-age N]` | Recoge los binarios de script en caché con más de N días de antigüedad (30 por defecto). |
| `pengu expand FILE.pengu [-o OUT]` | Imprime el `bundle.c` generado (útil para inspeccionar la eliminación de código muerto). |
| `pengu time FILE.pengu` | Ejecuta el script e imprime los tiempos por fase (imports, check, codegen, compilador de C, ejecución). |
| `pengu eval "EXPR"` | Envuelve la expresión en un script temporal, la compila a través de la caché e imprime el resultado. |
| `pengu watch FILE.pengu` | Vuelve a ejecutar el script siempre que él o cualquiera de los módulos que importa cambien. |

Flags globales: `--quiet`, `--no-color` (o `NO_COLOR=1`) y `--verbose`.

### 20.4 Pruebas unitarias integradas (`pengu test`)

Compila y ejecuta todos los bloques `test "..."` definidos en el proyecto:

```bash
pengu test [--profile PROFILE] [--config CONFIG] [--entry ENTRY] [--cc CC] [--verbose] [-D DEFINES] [--json] [--watch]
```

- `--watch`: Se ejecuta en modo de vigilancia de archivos, recompilando y reejecutando automáticamente las pruebas unitarias siempre que se modifique cualquier archivo `.pengu`.
- `--json`: Emite JSON Lines legible por máquina a `stdout` para la integración con CI/CD, con los resultados de las pruebas, la duración y los diagnósticos de fallo.

### 20.5 Comprobación rápida de tipos (`pengu check`)

Valida la sintaxis y los tipos del proyecto sin invocar GCC/Clang ni emitir código C:

```bash
pengu check [--profile PROFILE] [--config CONFIG] [--entry ENTRY] [--cc CC] [--verbose] [-D DEFINES]
```

- Comprueba rápidamente los tipos de todos los AST y verifica las tablas de símbolos de los módulos. Ideal para hooks pre-commit de git y pasos de lint en integración continua.

### 20.6 Generador de bindings de cabeceras de C (`pengu bind`)

Traduce archivos de cabecera de C (`.h`) directamente a bindings de declaración nativos de PenguScript (`.d.pengu`):

```bash
pengu bind <header> [--prefix PREFIX] [--links LINKS...] [--output OUTPUT] [--no-comments] [--ignore IGNORE...] [--include-paths INCLUDE_PATHS...] [--define DEFINES] [--cpp-flags CPP_FLAGS] [--system-includes] [--preprocessed FILE.i] [--no-blank-extensions] [--no-cpp] [--auto-import DIR]
```

- Neutraliza automáticamente las extensiones del compilador GNU (`__attribute__`, `__asm__`, `__extension__`) antes del análisis.
- `--define, -D`: Define macros del preprocesador de C (p. ej. `-D Z_SOLO`).
- `--cpp-flags`: Flags en bruto del preprocesador (p. ej. `"-DZ_SOLO -DXXH_INLINE_ALL=0"`).
- `--system-includes`: Conserva las cabeceras del sistema del compilador en lugar de stubs mínimos.
- `--preprocessed FILE.i`: Omite la invocación del preprocesador y analiza directamente un archivo `.i` existente.
- `--auto-import DIR`: Emite automáticamente sentencias `import` para los bindings `.d.pengu` hermanos correspondientes a las cabeceras incluidas.
- `--links`: Emite directivas `link "..."` en la salida del binding.

### 20.7 Formateador de código fuente (`pengu fmt`)

Da formato a los archivos fuente `.pengu` según las convenciones de estilo estándar:

```bash
pengu fmt <paths...> [--check] [--write] [--indent INDENT] [--tabs] [--verbose]
```

- Fuerza una indentación de 2 espacios (configurable mediante `--indent` o `--tabs`).
- Elimina los espacios en blanco finales, normaliza la indentación de bloques y conserva intactos los comentarios `#` / `##`.
- `--check`: Verifica el formato sin volver a escribir en disco; sale con estado distinto de cero si se necesitan cambios.
- Omite automáticamente cualquier archivo fuente que empiece por `## @generated`.

### 20.8 Generador de documentación (`pengu doc`)

Genera documentación en Markdown a partir de los docstrings del código fuente:

```bash
pengu doc [--config CONFIG] [--entry ENTRY] [--output OUTPUT]
```

- Extrae los comentarios de documentación (`##`) que preceden a weaves, runes, concepts, omens y constantes de todos los módulos del proyecto a archivos Markdown estructurados en `docs/`.

### 20.9 Gestor de recursos embebidos (`pengu assets`)

Inspecciona y actualiza los recursos embebidos del proyecto:

```bash
pengu assets [--config CONFIG] [--list] [--force]
```

- Reconstruye `src/arca.pengu` y `build/arca_assets.c` a partir del directorio `assets:` configurado.
- `--list`: Muestra todos los archivos de recursos rastreados, su tamaño exacto en bytes y los identificadores de constante de PenguScript generados.
- `--force`: Regenera todas las tablas de recursos incondicionalmente, omitiendo las cachés de modificación.

### 20.10 Language Server Protocol (`pengu lsp`)

Impulsa la integración con IDE (VS Code, Neovim, Emacs, Helix):

```bash
pengu lsp [--stdio] [--tcp] [--host HOST] [--port PORT]
```

- `--stdio`: Comunicación por E/S estándar (por defecto para subprocesos del editor).
- `--tcp`, `--host`, `--port`: Ejecuta el servidor LSP sobre un socket TCP (puerto por defecto: `2087`).
- Capacidades:
  - Informes de diagnóstico en tiempo real con spans de intercalación al estilo de Rust.
  - Autocompletado contextual de código (keywords, runes, métodos, variables locales, símbolos de módulo).
  - Información al pasar el cursor con firmas de tipo, docstrings y tamaños/alineaciones de memoria de structs calculados.
  - Ir a la definición e ir a la implementación.
  - Buscar referencias y búsqueda de símbolos en el workspace.
  - Esquema de símbolos del documento y símbolos del workspace.
  - Renombrar símbolos entre archivos.
  - Acciones de código: importar módulo, eliminar símbolos no usados, implementar métodos de concept.
  - Formato de documento.

### 20.11 Gestión de dependencias (`pengu add` y `pengu update`)

Integra módulos externos de PenguScript y bindings de C:

```bash
pengu add <source> [--branch BRANCH] [--name NAME] [--config CONFIG] [--no-build]
pengu update [--config CONFIG] [--verbose]
```

- `pengu add`: Clona un repositorio git remoto o crea un symlink de un directorio local en `lib/<name>`, y registra la dependencia en `pengu.yaml`.
- `pengu update`: Ejecuta `git pull` en todas las dependencias de `lib/` y vuelve a ejecutar los scripts de build de las dependencias.

### 20.12 Limpieza del proyecto (`pengu clean`)

Limpia el workspace del proyecto:

```bash
pengu clean [--config CONFIG]
```

- Elimina el directorio `build/`, los objetos compilados, los bundles de C y las cachés temporales.

### 20.13 Versionado del toolchain (`pengu -V` / `--version`)

```bash
pengu -V
pengu --version
```

- Muestra la cadena de versión (p. ej. `PenguScript v0.14.0`). La versión del compilador se registra en `VERSION` y se replica en `pengu_version.py`.

### 20.14 Infraestructura del runtime y diagnósticos

#### Backtraces mínimos del runtime
El runtime mantiene un búfer circular de frames ligero y thread-local:
- `pengu_frame_push(fn_name, file, line)` y `pengu_frame_pop()` registran los frames activos de la pila de llamadas hasta `PENGU_MAX_FRAMES` (64 por defecto).
- Los manejadores de fallos async-signal-safe para `SIGSEGV` y `SIGABRT` (y `SetUnhandledExceptionFilter` en Windows) interceptan errores fatales y escriben la pila de llamadas exacta con los nombres de archivo fuente `.pengu` y los números de línea directamente en `stderr`.

#### Comprobación de límites opcional
- Con el perfil de build `debug`, las operaciones de indexación (`xs at i` y `set xs at i`) emiten aserciones de límites (`pengu_assert_bounds`), que se detienen con un trazado de la pila de llamadas ante un acceso fuera de límites.
- Con `release`, las comprobaciones de límites se omiten por completo con cero sobrecarga en runtime.

#### Directivas `#line`
El código C generado incluye directivas `#line` que asignan cada sentencia de C al archivo y la línea de origen `.pengu`. Los diagnósticos del compilador de C y los depuradores GDB/LLDB apuntan directamente al código fuente de PenguScript.

#### Argumentos del programa y códigos de salida
- `int32_t pengu_main(void)` devuelve el código de salida del proceso (`0` si todo ha ido bien).
- El `main(argc, argv)` de C inicializa el runtime mediante `pengu_init(argc, argv)` antes de invocar `pengu_main`, lo que garantiza que `std.rites.get_argc()`, `get_argv()` y `get_args()` reciban los argumentos auténticos del sistema operativo.

#### Estructura estándar de directorios del proyecto

```
my_project/
├── pengu.yaml          # Project configuration (dependencies, build flags, assets)
├── src/
│   ├── main.pengu      # Entrypoint module
│   └── arca.pengu      # Auto-generated embedded assets module (optional)
├── assets/             # Static game/application assets (optional)
├── lib/                # External dependencies and C bindings
├── c/                  # Native C/C++ helper source files (compiled automatically)
└── build/              # Output binaries, object files, and bundle.c (gitignored)
```

---

## 21. Ejemplo completo

```pengu
import std.spark
import std.scrolls
import std.tally

# --- Types --------------------------------------------------------------
rune Player:
    name as string
    hp as int

omen Phase:
    Idle
    Fighting

concept Named:
    weave display_name into string

bind Player with Named:
    weave display_name into string:
        return self->name

enchanting Player:
    weave ritual new_hero with name as string into Player:
        return with name is name, hp is 100

    weave damage with amount as int into void:
        set self->hp is self->hp - amount
        if self->hp < 0:
            set self->hp is 0

# --- Generics -----------------------------------------------------------
rune Pair shard A, B:
    first as A
    second as B

weave first_of shard A, B with p as Pair of A, B into A:
    return p.first

# --- Main Entrypoint ---------------------------------------------------
weave main into int:
    var hero as Player with:                    # Block-style builder construction
        set .name is "Ada"
        calling .damage with 30

    let desc is judge Phase.Fighting:
        when Phase.Idle -> "idle"
        when Phase.Fighting -> "fighting"
        else -> "?"

    var scores as list of int is list of int
    calling scores.push with 10
    calling scores.push with 20
    calling scores.push with 30
    calling spark.println with "sum: {((calling tally.sum with scores) to string)}"
    var part as string is calling scrolls.substring with "done", 0, 4
    calling spark.println with part

    var ok as maybe int is some 1
    if ok.is_present:
        return 0
    return 1
```

El C generado es una única unidad de traducción que contiene los layouts de struct (`struct Player`, `enum Phase`), los tipos monomorfizados (`Pair_int_string`), los métodos (`Player_new_hero`, `Player_damage`) y el wrapper del punto de entrada `pengu_main(void)`.

---

## 22. Apéndice: catálogo de diagnósticos del compilador

PenguScript usa un reportero de diagnósticos del compilador inspirado en Rust, con salida en color ANSI, márgenes de línea, subrayados de span con intercalación, códigos de error (`[Exxxx]`) y sugerencias `note:` y `help:`.

### 22.1 Formato de los diagnósticos

Cuando se produce un error, el compilador formatea el diagnóstico del siguiente modo:

```text
error[E0006]: cannot assign to immutable variable 'count'
  --> src/main.pengu:14:5
   |
14 |     set count is count + 1
   |     ^^^^^^^^^^^^^^^^^^^^^^ cannot assign to 'let' binding
   |
   = note: 'let' bindings are immutable by default.
   = help: Declare the variable with 'var' instead of 'let' to allow mutation.
```

### 22.2 Catálogo de errores del compilador (`E0000`–`E0050`)

| Código | Clase de excepción | Condición semántica y explicación | Ayuda / nota por defecto |
|---|---|---|---|
| `E0000` | `ParseError` | Error de sintaxis: token inválido, indentación incorrecta o separadores de coma ausentes. | Comprueba la sintaxis alrededor de la ubicación; verifica la coherencia de la indentación. |
| `E0001` | `ConstInsideWeaveError` | `const` declarado dentro del cuerpo de una función. Las constantes solo pueden estar en el nivel superior. | Mueve la declaración de la constante fuera de la función, o usa `let`/`var`. |
| `E0002` | `VarLetTopLevelError` | `var` o `let` declarados en el nivel superior. El estado global mutable está prohibido. | Usa `const` en el nivel superior, o `static var` dentro de un weave. |
| `E0003` | `SelfDotAccessError` | Acceso con punto `self.` usado en lugar de la flecha `self->`. | Cambia `self.` por `self->` (`self` siempre es una referencia de puntero). |
| `E0004` | `UndefinedIdentifierError` / `SemanticError` | Símbolo no encontrado, ciclo de importación circular detectado o importación de módulo duplicada. | Comprueba la ortografía, verifica la declaración/importación o rompe la dependencia circular. |
| `E0005` | `TypeMismatchError` / `SemanticError` | Tipos incompatibles en una asignación, argumento u operador. Incluye la composición de cadenas con `+`/`+=` (`"a" + b`, `set s += x`), que debe usar interpolación `"{expr}"`. | Ajusta el tipo esperado, convierte con `to <Type>` o compón cadenas con `"{expr}"`. |
| `E0006` | `MutabilityError` | Intento de asignación a un binding `let` inmutable, a un `const` o a un destino `frozen`. | Declara la variable con `var` en lugar de `let` para permitir la mutación. |
| `E0007` | `InvalidControlFlowError` | Sentencia `break` o `continue` usada fuera de un bloque de bucle. | Elimina la sentencia de flujo de control o colócala dentro de un bucle `while` o `for`. |
| `E0008` | `InvalidMemoryOpError` / `SemanticError` | `sigil of` inválido sobre un literal/const, o `banish` inválido sobre algo que no es puntero/seal/frozen. | La toma de dirección y el banish manual requieren destinos de memoria mutable válidos. |
| `E0009` | `InvalidWithTargetError` | Acceso a miembro con punto inicial (`.field`) usado fuera de un bloque `with` activo. | Envuelve la llamada en un bloque `with` o usa un acceso explícito al objeto destino. |
| `E0010` | `SemanticError` (`code="E0010"`) | La inicialización de struct `with x is 1` no coincide con ningún tipo `rune` conocido en el ámbito. | Comprueba los nombres de campo o anota el tipo destino de forma explícita (`as RuneName`). |
| `E0011` | `SemanticError` (`code="E0011"`) | La inicialización de struct coincide con varios runes con nombres de campo idénticos. | Desambigua especificando el tipo de rune explícitamente con `as RuneName`. |
| `E0012` | `SemanticError` (`code="E0012"`) | Intento de instanciar directamente un tipo `opaque` con `with`. | Los tipos opacos no se pueden instanciar directamente; obtenlos mediante interoperabilidad con C. |
| `E0013` | `SemanticError` (`code="E0013"`) | El campo no existe en el rune, echo, maybe, result o tipo primitivo. | Comprueba la ortografía del campo o verifica los campos declarados en el struct/union. |
| `E0014` | `InvalidBuilderStatementError` / `TypeMismatchError` | Sentencia prohibida en un constructor `with:`, o inicialización de `null`/`maybe none` sin tipo. | Usa solo asignaciones de campos/llamadas en los constructores; proporciona un tipo explícito para `null`. |
| `E0015` | `UnknownArrayDimensionError` / `SemanticError` | No se puede determinar la dimensión de un array fijo, o se accede a `error` fuera de `or:`. | Especifica todas las dimensiones explícitamente; accede a `error` solo dentro de bloques `or:`. |
| `E0016` | `SemanticError` (`code="E0016"`) | Macro de C usada sin la directiva previa `include "header.h"`. | Añade `include "header.h"` antes de referenciar constantes de C. |
| `E0017` | `SemanticError` (`code="E0017"`) | No se puede desestructurar la expresión (el destino no es un rune, array fijo, slice ni list).| La desestructuración solo admite runes, arrays fijos, slices y lists. |
| `E0018` | `TypeMismatchError` (`code="E0018"`) | Tipo de elemento incompatible con el contenedor (`list.push` o inserción en map). | Pasa un valor compatible con el tipo de elemento declarado del contenedor. |
| `E0019` | `SemanticError` (`code="E0019"`) | Variable no definida o expresión mal formada dentro de la interpolación `{expr}` de una cadena. | Asegúrate de que la variable existe en el ámbito, o usa una cadena en bruto `r"..."` para desactivarla. |
| `E0020` | `TypeMismatchError` (`code="E0020"`) | La expresión de retorno o el valor de `or return` es incompatible con el tipo de retorno de la función. | Devuelve un valor que coincida con el tipo de retorno declarado de la función. |
| `E0021` | `GenericTypeMissingArgsError` | Tipo genérico usado sin los argumentos de tipo requeridos (`of`). | Proporciona los argumentos de tipo con `of` (p. ej. `Pair of int and float`). |
| `E0022` | `TypeParamOutsideGenericError`| Parámetro de tipo usado fuera de un contexto de declaración genérica. | Declara el parámetro de tipo con `shard` o usa un tipo concreto. |
| `E0023` | `MultipleManyParamsError` | Varios parámetros variádicos `many` declarados en una misma función. | Una función puede tener como máximo un parámetro variádico `many`. |
| `E0024` | `ManyParamNotLastError` | El parámetro variádico `many` no es el último de la lista de parámetros. | Mueve el parámetro variádico `many` al final de la lista de parámetros. |
| `E0025` | `SemanticError` (`code="E0025"`) | Cuerpo de función o bloque `test` dentro de un archivo de declaración `.d.pengu`. | Usa `declare` sin cuerpo en los archivos de declaración; elimina los bloques de prueba. |
| `E0026` | `MultipleInsigniaError` | Varias directivas `insignia` definidas en el mismo archivo de módulo. | Solo se permite una directiva `insignia` por archivo de módulo. |
| `E0027` | `DuplicateOmenValueError` | Valor entero explícito duplicado asignado a variantes de un omen. | Asegúrate de que todos los valores de las variantes del omen sean distintos. |
| `E0028` | `InvalidOmenPayloadValueError`| Asignación de valor explícita `is <val>` en un omen algebraico con payload (`with`). | Elimina `is <value>` de las variantes algebraicas con payload. |
| `E0029` | `InvalidOmenConstantValueError`| Valor no constante o no entero asignado a una variante de omen. | Los valores de las variantes de omen deben evaluarse a una constante entera en tiempo de compilación. |
| `E0030` | `ConceptMethodMismatchError` | La firma del método en `bind` no coincide con la declaración del concept. | Asegúrate de que los tipos de parámetro y el tipo de retorno coincidan con la especificación del concept. |
| `E0031` | `UnimplementedConceptMethodError`| El bloque `bind` no implementa todos los métodos requeridos del concept. | Implementa todos los métodos declarados en el concept vinculado. |
| `E0032` | `ConceptBoundNotSatisfiedError`| El argumento de tipo genérico no implementa el bound de concept requerido (`where`). | Implementa el concept mediante `bind Type with Concept:` antes de pasarlo como argumento. |
| `E0033` | `InvalidRitualSelfAccessError` | Se accede a `self` dentro de un método `ritual` (estático). | Los métodos ritual son estáticos; elimina `self` o quita el modificador `ritual`. |
| `E0034` | `InvalidRitualCallError` | Llamar a un método de instancia de forma estática o llamar a un método ritual sobre una instancia. | Llama a los métodos ritual sobre el tipo (`Type.method`) y a los métodos de instancia sobre objetos. |
| `E0035` | `SemanticError` (`code="E0035"`) | Colisión con un identificador reservado de C, static var anidada, array static o test vacío. | Elige un identificador no reservado; declara los static directamente en los weaves. |
| `E0036` | `SemanticError` (`code="E0036"`) | Símbolo de nivel superior duplicado, alias de importación `_` o alias de importación en conflicto. | Renombra el símbolo duplicado o cambia el alias de importación. |
| `E0037` | `SemanticError` (`code="E0037"`) | El índice del bucle y el binding del elemento comparten el mismo nombre en `for i, v in col`. | Renombra uno de los dos bindings del bucle para mantener identificadores distintos. |
| `E0038` | `SemanticError` (`code="E0038"`) | Literal de clave duplicado dentro de un literal de map. | Las claves de un literal de map deben ser únicas. |
| `E0039` | `SemanticError` (`code="E0039"`) | La condición `when` no se evalúa a una constante booleana en tiempo de compilación. | Usa booleanos de tiempo de compilación, `defined()` o variables de comptime. |
| `E0040` | `SemanticError` (`code="E0040"`) | `main` usado como variable local/static, parámetro, constante o nombre de campo. | `main` está reservado para el punto de entrada del programa y las comprobaciones `when main:`. |
| `E0041` | `ArraySizeMismatchError` | El número de elementos de un literal de array o la longitud de una fila no coincide con el tamaño declarado. | Asegúrate de que el número de elementos del literal coincide con el tamaño declarado del array fijo. |
| `E0042` | `InvalidRangeError` | Límites de rango inválidos: `start > end` en una expresión de rango conocida en tiempo de compilación. | Asegúrate de que el límite inicial del rango sea menor o igual que el límite final. |
| `E0043` | `PrivateSymbolAccessError` | Acceso a un símbolo privado (`_` inicial) desde fuera del módulo o rune que lo define. | Los símbolos con prefijo `_` son privados; usa el nombre público o el `insignia` de C. |
| `E0044` | `NonExhaustiveJudgeError` | La expresión `judge` sobre un omen o bool no es exhaustiva y carece de `else ->`. | Cubre todas las variantes del omen o añade una rama por defecto `else ->`. |
| `E0045` | `SemanticError` (`code="E0045"`) / `TypeMismatchError` | `try` usado dentro de una función que no devuelve un `maybe` o `result` compatible. | Cambia el tipo de retorno de la función a `maybe T` o `result of T to E`. |
| `E0046` | `SemanticError` (`code="E0046"`) | El nombre de una variante de omen colisiona con el de otro omen sin cualificación. | Usa nombres de variante distintos o refiérete mediante la forma cualificada `Omen.variant`. |
| `E0047` | `AutoOwnedBanishError` / `DuplicateConceptBindingError` | Intento de `banish` manual sobre una variable con ownership automático, **o** un concept vinculado dos veces al mismo tipo / dos concepts que aportan el mismo método (`(type, method)` debe ser único). | Elimina el `banish` manual, o elimina/renombra el método `bind` duplicado. |
| `E0048` | `BorrowedBanishError` | Intento de `banish` manual sobre una referencia prestada (`borrowed` o vista). | Solo el propietario de una asignación puede aplicarle banish; elimina `banish`. |
| `E0049` | `SemanticError` (`code="E0049"`) | Operación usada sobre un parámetro de tipo genérico (o tipo similar a struct) que no lleva el bound de concept requerido: aritmética sin `Num`, `%`/bit a bit sin `Integrum`, `==` sin `Par`, ordenación sin `Ordo`, `donum T` sin un bound que permita valor por defecto, `==`/`<` sobre un rune u omen algebraico sin `derive Par`/`Ordo`. | Añade la cláusula `where T: Concept` indicada o `derive Concept` a la declaración. |
| `E0050` | `InfiniteTypeSizeError` | Un rune (u omen algebraico) se contiene a sí mismo **por valor**, de forma directa o a través de otro tipo por valor, por lo que su tamaño en C no se puede calcular. | Rompe el ciclo con indirección por puntero: `ref to T`, `maybe ref to T`, `list of T`, `map of K to V`. |

### 22.3 Catálogo de advertencias del compilador (`W0001`–`W0004`)

| Código | Nombre de la advertencia | Condición que la activa | Práctica recomendada |
|---|---|---|---|
| `W0001` | `UnsafeTransmuteWarning` | `transmute` entre tipos de tamaños en bytes diferentes o tipos que no son punteros. | Usa la conversión segura `to <Type>` cuando sea posible, o verifica que los tamaños del layout de memoria coincidan. |
| `W0002` | `UnsafeEchoAccessWarning` | Acceso a campos de una union sin etiqueta (`echo`). | Las lecturas de unions sin etiqueta son intrínsecamente inseguras; prefiere variantes de `omen` algebraicas con payload. |
| `W0004` | `UnreachableCodeWarning` | Sentencias inalcanzables detectadas después de un `return` temprano, un `panic`, o en una rama de `if`/`when`. | Elimina el código muerto que sigue a returns incondicionales o a ramas falsas en tiempo de compilación. |

### 22.4 Escenarios ilustrativos de diagnósticos

#### Escenario 1: estado mutable de nivel superior (`E0002`)
```pengu
# Invalid:
var counter as int is 0

# Fix: Use const or encapsulate in a stateful weave with static var:
const INITIAL_COUNTER as int is 0

weave next_counter into int:
    static var counter as int is 0
    set counter is counter + 1
    return counter
```

#### Escenario 2: acceso con punto inicial fuera de un constructor (`E0009`)
```pengu
# Invalid:
set .hp is 100

# Fix: Wrap inside with block or assign directly to instance:
with player:
    set .hp is 100
# Or:
set player.hp is 100
```

#### Escenario 3: judge no exhaustivo (`E0044`)
```pengu
# Invalid (missing Fighting variant):
let name is judge current_phase:
    when Phase.Idle -> "Standing by"

# Fix: Add missing variant or else branch:
let name is judge current_phase:
    when Phase.Idle -> "Standing by"
    when Phase.Fighting -> "In battle"
    else -> "Unknown"
```

#### Escenario 4: banish con ownership de ámbito (`E0047`)
```pengu
# Invalid:
var words as list of string is list of string
calling words.push with "hello"
banish words  # E0047: words is locally allocated and scope-owned

# Fix: Remove manual banish; the compiler frees 'words' at scope exit:
var words as list of string is list of string
calling words.push with "hello"
# Compiler automatically frees 'words' here
```

#### Escenario 5: composición de cadenas (`E0005`)
```pengu
# Invalid: '+' never concatenates strings.
var name as string is "world"
calling print with "Hello, " + name
#   E0005: Cannot concatenate strings with '+' (the left operand is 'string')
#   = help: Use string interpolation: "text{value}more". '+' only adds numbers.

# Fix: one interpolation literal composes the whole string:
calling print with "Hello, {name}"

# Invalid: '+=' on a string.
var acc as string is "a"
set acc += "b"
#   E0005: Cannot concatenate strings with '+='

# Fix: rebind through interpolation.
set acc is "{acc}b"
```

---

*Fin de la referencia. Se agradecen las correcciones — este documento refleja el comportamiento del compilador en la versión 0.14.x; ejecuta `pengu check` sobre cualquier fragmento para confirmar la semántica en tu toolchain.*
