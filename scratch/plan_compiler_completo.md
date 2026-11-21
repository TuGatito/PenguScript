# Plan — soporte completo del lenguaje PenguScript

> **Alcance de este plan:** compilador (lexer, parser, checker) y codegen C++20.
> El LSP, el formateador, la extensión y el resto de herramientas quedan fuera
> por ahora; solo se tocan cuando una fase lo necesite para verificar algo.
>
> **Punto de partida (verificado):** 85 pruebas en 11 archivos, `tsc --noEmit`
> limpio y los ejemplos 01–10 compilando y ejecutándose. Versión del proyecto:
> 0.1.0. Este plan **no** sube la versión.
>
> **Regla de trabajo:** cada fase termina con pruebas nuevas en verde y una
> actualización de la bitácora (§9). No se da una fase por cerrada sin que su
> criterio de aceptación se pueda ejecutar con un comando.

---

## 1. Diagnóstico: lo que hoy no funciona

Antes de escribir el plan se sondeó el compilador con programas pequeños
(`/tmp/gaps/*.pengu`, no versionados) y con los ejemplos del repositorio. La
tabla siguiente es evidencia, no una lista de deseos: cada fila se reprodujo
con `pengu check` o `pengu run`.

### 1.1 Errores reportados por el usuario

| Síntoma | Reproducción | Causa encontrada |
|---|---|---|
| `invoke "std/io"` «se esperaba `=`» | Archivo con **BOM UTF-8** al inicio (`EF BB BF`). | El BOM forma parte del primer token (`\uFEFFinvoke`), deja de ser la palabra clave `invoke` y el parser lo trata como declaración. `make_source` no lo elimina. |
| `main = ->` «se esperaba `(`» | No se pudo reproducir con: 2/4 espacios, tabuladores, CRLF, comentarios tras `->`, cuerpo en la misma línea, `-> void`, archivo sin salto final. | Sin reproduce, pero apunta a un caso donde `->` no llega a `parse_function_decl` y el parser intenta otra producción. Se añade banco de regresión con todas las formas de flecha (§5, F1). |
| «quiere forzar indentación de 4 cuando permitimos también 2» | `pengu fmt` convierte 4 espacios a 2; el checker acepta 4 y solo rechaza anchos que no corresponden a ningún nivel abierto (E0101). | Dos problemas distintos: (a) el formateador no configura ni detecta el ancho, (b) el mensaje de E0101 no explica el nivel esperado ni ofrece arreglo. |

Comandos usados para el BOM:

```bash
printf '\xef\xbb\xbfinvoke "std/io"\n\nmain = ->\n  io::println("hola")\n' > bom.pengu
pengu check bom.pengu
# error[E0208]: se esperaba «=» tras «﻿invoke»
```

### 1.2 Falsos positivos del checker

| Programa | Diagnóstico actual | Lo correcto |
|---|---|---|
| `x: int? = none` | E0501 esperaba `int?`, recibí `none` | `none` es asignable a cualquier `T?`. |
| `p: raw<int> = nullptr` | E0501 esperaba `raw<int>`, recibí `nullptr` | `nullptr` es asignable a `raw<T>`. |
| `x: long long = 1` / `a: signed char = 1` | E0501 esperaba el tipo, recibí `int` | El literal entero se ajusta al tipo declarado si cabe. |
| `p: pair<int,int> = (1, 2)` / `t: tuple<int,string> = (1,"a")` | E0501 tipos distintos | El literal tupla se convierte al tipo compuesto declarado. |
| `f = (x: int = 100, y: int = x + 1000) -> int`; `f(1)` | E0504 espera 2 argumentos | Los parámetros con valor por defecto son opcionales en la llamada. |

Causa raíz del primer grupo: `report_type_mismatch` compara con
`type_equals` y **no** consulta `can_assign`; el camino de declaración tipada
(`checker_stmt.ts`, rama `declared_type`) llama a `report_type_mismatch` sin
comprobar antes. Hay que separar «diagnosticar» de «decidir si es asignable».

### 1.3 Huecos de análisis (acepta lo que debería rechazar)

| Programa | Hoy | Debería |
|---|---|---|
| `p.x = 2` con `p` inmutable | OK | E0406: el binding no es `mut`. |
| `c.inc()` donde `inc` es `mut` y `c` es inmutable | OK (falla al compilar C++) | E0406/llamada mut sobre binding inmutable. |
| `mut n = 1; r = ref(n); n = 2` | OK | E0602: Ley de Exclusividad. |
| `io::println("#{p}")` con `rune Punto` sin `to_string` | OK (falla al compilar C++) | E0509/Display: el rune no es Display. |
| `switch` sobre omen unitario sin `else` | Sin aviso | Advertencia de exhaustividad (el spec la pide). |
| `main` sin cuerpo / función con `-> int` sin retorno en alguna rama | Parcial | Análisis de caminos de retorno. |
| `static mut` leído en código seguro | No se puede ni declarar (bug de parseo) | Error de `unsafe` requerido. |
| Conversión estrecha fuera de `unsafe` | Bien (E0603) | Se conserva y se amplía a más casos. |

### 1.4 Construcciones del lenguaje que no existen o están a medias

| Construcción | Estado | Evidencia |
|---|---|---|
| `function<(int) -> int>` | ❌ parseo: «se esperaba un tipo, se encontró `(`» | El parser de tipos no distingue lista de parámetros de lista de tipos. |
| `array<int, 3>` | ❌ parseo: espera un tipo y encuentra `3` | Falta la rama `array<T, N>` con expresión de tamaño. |
| `[1,2,3]` con anotación `array<int,3>` | ❌ (depende de lo anterior) | Sin literal tipado por contexto. |
| `static mut` | ❌ parseo: el parser consume `mut` como nombre | Orden de tokens en `parse_static_decl`. |
| `operator` libre (fuera de `enchanting`) | ❌ «se esperaba una declaración, se encontró `operator`» | El parser solo lo admite dentro de `enchanting`. |
| `operator []` de usuario | ❌ E0508: no se puede indexar `Caja` | La indexación solo consulta tablas incorporadas. |
| `operator +=` de usuario | ❌ E0501: `+=` no definido para `P` | Las asignaciones compuestas no buscan operadores del rune. |
| `operator -` unario de usuario | ❌ E0501: `-` espera un número | El unario no consulta operadores del rune. |
| `<=>` + `Ordering` | ❌ no existe el tipo `Ordering` | Falta el tipo y la derivación de comparaciones. |
| `enchanting` sobre `omen` | ❌ E0506: el omen no tiene el miembro | Los métodos de omen se recolectan pero no se resuelven. |
| `enchanting` sobre `echo` (con `@`) | ❌ el checker trata `@` como el alias, no como el tipo base | Falta el mapeo de `@` al valor subyacente. |
| `int::try_from("42")` | ❌ no se reconoce `int::try_from` | `try_from` solo existe para omens y seals. |
| Métodos de primitivos (`3.5.floor()`, `int.abs()`) | ❌ E0506 | No hay tabla de métodos para `double`/enteros. |
| Genéricos: `rune Caja<T>` | ❌ E0502: no existe `T` en el constructor | Los sigilos no entran en ámbito al comprobar campos/constructor/cuerpo. |
| Genéricos: `omen Resultado<T>` con payload | ✅ | `emit_omen` genera `template` por variante. |
| Genéricos: `seal Id<T>` | ❌ codegen: `auto value` | Igual que el anterior. |
| Genéricos: `echo Lista<T>` | ✅ | El alias aplica `substitute_generics` en el uso. |
| Instanciación explícita `id<int>(3)` | ❌ E0502 en la declaración | El sigilo no está en ámbito; falta sustitución en la firma. |
| `any`, `variant<...>`, `init_list<T>` | ❌ no existen como tipos usables | Tablas de tipos y codegen. |
| `deque`, `list`, `span`, `bitset`, `stack`, `queue`, `pair`, `tuple` (más allá del literal), `complex`, `atomic`, `mutex`, `thread` | ❌ o parcial | `cpp_types` mapea algunos nombres, pero no hay literales, métodos ni asignaciones. |
| Herencia `heir` con `parent(...)` en el constructor | 🟡 check OK, codegen: «`parent` solo puede aparecer como primera sentencia de un constructor» | La marca de constructor no llega al emisor de la sentencia. |
| Despacho virtual por `ref<Animal>` | ❌ no comprobado; probablemente corte de objeto o método no virtual | Falta `virtual` y upcast seguro. |
| Ley de Exclusividad (`ref(x)` vs mutación) | ❌ no implementada | `VarInfo.borrowed` existe y nadie lo usa. |
| `mut` en la llamada (`increment(mut count)`) | 🟡 se parsea, no se exige en la llamada | Falta contrato de llamada. |
| Movimiento a través de campos/índices | 🟡 solo identificadores | `mark_moved` ignora `member`/`index`. |
| `const` evaluable en compilación | ❌ cualquier expresión | No hay evaluador de constantes. |
| Orden de evaluación de imports | ❌ no implementado | Sin init por módulo. |
| `Display` de `T?`, contenedores, omens, flags, seals | 🟡 el runtime lo hace para algunos; el checker no lo valida | Tabla de Display + validación. |
| Variádicas | ❌ no existen en el lenguaje | `declare`/`extern` guardan un flag `variadic` que el parser siempre pone en `false`. |

---

## 2. Cómo se implementará: reglas de diseño

1. **Un concepto, un archivo.** Si un archivo pasa de ~250 líneas se divide
   (`checker_expr.ts` y `cpp_expr.ts` ya están por encima; ver F9).
2. **El checker decide; el codegen obedece.** Ninguna conversión, mutabilidad
   ni Display se resuelve en C++ por accidente.
3. **Nada de comportamiento implícito silencioso.** Si el codegen no sabe
   traducir algo, emite E0801 con span y explicación; nunca genera C++ inválido
   sin diagnóstico (el caso de `p.len()` y de los runes sin `to_string` son la
   excepción que hay que eliminar).
4. **Pruebas de conformidad por construcción**, no por ejemplo suelto:
   `tests/conformance/<área>/<caso>.pengu` con resultado esperado (compila,
   error con código, salida). Ver §6.
5. **Compatibilidad hacia atrás del código escrito**: los 10 ejemplos y los
   programas existentes siguen compilando en cada fase.

---

## 3. Variádicas: diseño propuesto

### 3.1 Motivación

- `std/io` (`print`, `println`, `eprint`, `eprintln`), `std/format` y
  `std/log` son hoy intrínsecas **solo** porque el lenguaje no puede expresar
  «cero o más argumentos». Con variádicas pasan a ser `.pengu` normales.
- `pengu bindgen` hoy descarta funciones C variádicas (`printf`). El flag
  `variadic` ya existe en `DeclareDecl` pero nadie lo llena.

### 3.2 Sintaxis recomendada

```coffee
-- declaración: puntos suspensivos delante del nombre
sumar = (...numeros: int) -> int
  total = 0
  for n in numeros
    total += n
  total

-- llamada normal
sumar(1, 2, 3)

-- reenvío (spread)
registrar = (...valores: int) -> void
  io::println("#{sumar(...valores)}")

-- variádica heterogénea
imprimir = (...partes: any) -> void
  io::println(concatenar(partes))
```

- `...` va **delante del nombre**, no del tipo: se lee «varios `numeros` de
  tipo `int`» y encaja con el spread `...valores` en la llamada.
- Alternativas descartadas (documentadas para no volver a discutirlas):
  `numeros: int...` (se confunde con `T?`), `vararg numeros: int` (palabra
  clave nueva para algo que la puntuación ya expresa).
- En una firma variádica, el parámetro variádico **debe ser el último**; no
  puede tener valor por defecto; puede ser `mut` (no se permite combinarlo con
  `mut` en la llamada; se documenta como limitación v0.2).
- Funciones, métodos y `enchanting` pueden ser variádicos. Los operadores no.

### 3.3 Tipos y semántica

| Forma | Tipo del parámetro dentro del cuerpo | Llamada |
|---|---|---|
| `(...xs: T)` | `vector<T>` | `f(a, b, c)` → `vector<T>{a,b,c}` |
| `(...xs: any)` | `vector<any>` | cada argumento se boxea como `Value` |
| `f(...xs)` (spread) | — | pasa el vector tal cual si el elemento coincide |
| `f()` | vector vacío | válido |
| `#xs`, `xs[i]`, `for x in xs` | como `vector<T>` | igual que hoy |

Reglas de tipado:

1. Todos los argumentos de una variádica homogénea deben ser asignables a `T`
   (con las mismas reglas que un parámetro normal).
2. Cada argumento de una variádica `any` debe ser **Display** (ver §3.4).
3. El spread exige que el argumento sea `vector<T>` (o el propio parámetro
   variádico) y que `T` sea asignable al elemento.
4. En tipos función: `function<(...int) -> int>`, `function<(...any) -> void>`.
5. Los parámetros con defecto no pueden ir después del variádico; el checker
   emite E0504 con explicación.
6. La aridad mínima de una función variádica es la de sus parámetros fijos.

### 3.4 `any` y `Display`

`any` necesita representación real para que una variádica heterogénea sirva:

- En C++: `::pengu::Value`, una caja con `std::any` + renderizador
  `std::function<std::string()>`.
- `pengu::value(x)` captura `x` por valor si es copiable y guarda un
  `to_string(x)` perezoso; para valores no copiables se guarda una referencia
  con la vida de la llamada (documentado).
- Display estructural se implementa con un `to_string` genérico con
  `if constexpr (requires { x.to_string(); })`; así un rune con
  `to_string = -> string` es Display sin registro previo.
- El checker valida Display en: interpolación `#{...}`, argumentos de
  variádica `any`, `needs Display` y `format`/`log`. Un rune sin `to_string`
  produce error de compilación (hoy genera C++ inválido).
- `function`, `ref`, `raw`, `unique`, `shared`, `weak` y `void` nunca son
  Display (spec, línea 567 del cheatsheet).

### 3.5 Codegen

| Caso | C++ emitido |
|---|---|
| `(...xs: int)` | `const std::vector<int>& xs` (o `std::vector<int>` por valor si se mueve) |
| llamada `f(1,2,3)` | `f(std::vector<int>{1,2,3})` |
| spread `f(...xs)` | `f(xs)` |
| `(...xs: any)` | `const std::vector<::pengu::Value>& xs` |
| llamada heterogénea | `f({::pengu::value(1), ::pengu::value("a")})` |
| `function<(...int) -> int>` | `std::function<int(std::vector<int>)>` |

`declare`/`extern` también admiten variádicas:

```coffee
declare
  write_line = (texto: string) -> void
  write_values = (partes: vector<any>) -> void
```

Para C variádico (`printf`) se permite **solo dentro de `unsafe`** y con tipos
primitivos/`string`; el codegen pasa `...` tal cual (sin boxing). `bindgen`
dejará de descartar esas funciones y las marcará `unsafe`.

### 3.6 Migración de la stdlib

1. Añadir al runtime `::pengu::write_values` (recorre `Value` y escribe) y
   `::pengu::format_values`.
2. `std/io.d.pengu` conserva `write_line`/`write_values` como `declare`.
3. Nuevo `std/io.pengu`:
   ```coffee
   realm io
   println = (...partes: any) -> void
     write_line(format_values(partes))
   ```
4. `std/format.pengu` y `std/log.pengu` igual, sin intrínsecas.
5. `BUILTIN_FUNCTIONS` pierde `io::println`, `format::format` y `log::*`;
   se queda solo con lo que sigue siendo primitiva de runtime.
6. `tests/std` verifica que cada `declare` tiene implementación y que
   `println("x=", 7)` produce `x=7` (misma semántica actual: sin separadores
   implícitos).

### 3.7 Casos límite que el plan debe cubrir con pruebas

- `f()` sin variádicos; `f(1)` con un fijo y ninguno variádico.
- Spread de un vector vacío; spread dentro de otra variádica.
- Variádica que llama a otra variádica; recursión.
- `any` con `none`, `bool`, `char`, `vector`, `map`, rune con y sin
  `to_string` (positivo/negativo).
- Método variádico (`rune Logger` con `escribir(...partes: any)`).
- `needs Display` en una función genérica variádica.
- Error si el variádico no es el último; error si tiene defecto.
- `function<(...any) -> void>` asignado y llamado.

---

## 4. Matriz de conformidad (objetivo: todo ✅)

Leyenda: ✅ soportado y probado · 🟡 parcial · ❌ falta.

### 4.1 Léxico, tipos y declaraciones

| Área | Estado | Fase |
|---|---|---|
| Indentación (2/4/tabs), comentarios, BOM | 🟡 (BOM rompe `invoke`) | F1 |
| Primitivos de una palabra (`int`, `double`, `bool`, `char`, `string`, `size_t`…) | ✅ | — |
| Primitivos multi-palabra (`long long`, `unsigned char`, `long double`…) | 🟡 (parseo OK; asignación falla) | F1/F2 |
| Enteros de tamaño fijo (`int8_t`…`uint64_t`), `byte`, `ptrdiff_t` | 🟡 (tipo OK; literales fallan) | F2 |
| `wstring`, `u8/16/32string`, `string_view` | ✅ (`string_view` desde `string`; impresión de cadenas anchas) | F4 |
| `vector`, `map`, `set` (literales, acceso, edición, iteración) | ✅ | — |
| `array<T,N>`, `deque`, `list`, `forward_list`, `multiset`, `unordered_*` | ✅ | F4 |
| `stack`, `queue`, `priority_queue`, `span`, `bitset` | ✅ | F4 |
| `pair`, `tuple` (tipo, literal, acceso, desempaquetado) | ✅ | F4 |
| `T?` / `optional<T>` (`value`, `value_or`, `is_some`, `is_none`) | ✅ (salvo `none` tipado) | F1 |
| `variant<...>`, `any`, `init_list<T>`, `complex<T>`, `atomic`, `mutex`, `thread` | ✅ (variant con `as`; `any` es caja de Display; `init_list` como tipo de parámetro) | F4 |
| `unique`, `shared`, `weak`, `raw`, `ref` | 🟡 (básico OK; reglas de préstamo faltan) | F7 |
| `const` (declaración, evaluación en compilación) | 🟡 (se acepta cualquier expresión) | F8 |
| `static mut` | ❌ (parseo) | F1/F7 |
| Asignación simple/compuesta, multiobjetivo | ✅ | — |
| `mut` (binding, parámetro, llamada) | 🟡 (binding sí; contrato de llamada no) | F7 |

### 4.2 Funciones y control de flujo

| Área | Estado | Fase |
|---|---|---|
| Funciones con cuerpo indentado, inline, `-> void`, retorno implícito | ✅ | — |
| Parámetros por defecto (lazy, dependientes) | 🟡 (arity) | F1 |
| Cierres y funciones como valor | 🟡 (básico) | F5 |
| `function<Sig>` como tipo | ❌ parseo | F2 |
| `if`/`unless`/`else if`, inline con `then` | ✅ (falta `then` + bloque) | F1 |
| `switch` (comas, `else`, exhaustividad) | 🟡 (sin warning de omen) | F1 |
| `match` (variantes, payloads, guardas, exhaustividad) | ✅ | — |
| `do`, `while`, `until`, `repeat…until` | ✅ | — |
| `for` numérico/iterable, rangos, `mut`, índice | ✅ | — |
| `break`/`continue`, `break value`, `else` de bucle | ✅ | — |
| Comprensiones (vector/mapa/set, múltiples `for`, `if`) | ✅ | — |
| Retorno en todas las ramas / código inalcanzable | ❌ | F2 |
| Evaluación de cortocircuito y efectos | 🟡 | F9 |

### 4.3 Runes, omens, echoes y seals

| Área | Estado | Fase |
|---|---|---|
| `rune`, campos, `@`, constructor, destructor | ✅ | — |
| `enchanting` (métodos const/mut, sombreado) | ✅ | — |
| Herencia `heir`, `parent(...)`, upcast `ref<Animal>(ref(d))`, despacho | 🟡 (codegen de `parent` roto; sin virtual) | F6 |
| `omen` unitario, valores explícitos, subyacente | ✅ | — |
| `flags omen` + operadores + `.has` | ✅ | — |
| `omen` algebraico (payloads, `match`) | ✅ | — |
| `omen` genérico | ✅ | — |
| `enchanting` sobre omen | ❌ | F6 |
| Cast seguro de omen y `try_from`/`from` | ✅ (omen); ❌ primitivos | F2 |
| `echo` (transparente) y `seal` (opaco), métodos | ✅ (básico) | — |
| `echo`/`seal` genéricos | ✅ | — |
| `enchanting` sobre `echo` con `@` | ❌ | F6 |
| Display de runes/omens/flags/seals | 🟡 sin validación | F1 |

### 4.4 Genéricos, operadores, memoria y módulos

| Área | Estado | Fase |
|---|---|---|
| Sigilos `<T>`, `needs`, inferencia, instanciación explícita | ✅ | — |
| Restricciones estructurales (`Ord`, `Copy`, `Display`, `Into`…) | ❌ no se validan | F5 |
| `operator` en `enchanting` (`+`, `-` unario, `+=`, `[]`, `()`) | 🟡 (`+`, `()`, `-` binario; `[]`, compuestos y unario no) | F6 |
| `operator` libre / simétrico | ❌ | F6 |
| `<=>` y `Ordering` (derivación de `<`, `==`, etc.) | ❌ | F2 |
| Ley de Exclusividad y préstamos | ❌ | F7 |
| Movimiento (`unique`) por campo/índice, retorno, contenedor | 🟡 | F7 |
| `unsafe` obligatorio (raw, `static mut`, conversiones) | 🟡 (solo casts) | F7 |
| Módulos `invoke` (básico, selectivo, alias, ciclos, diamante) | ✅ | — |
| Reapertura de `realm`, tipos entre realms, colisiones | 🟡 | F8 |
| Orden de evaluación de imports/`const` | ❌ | F8 |
| Stdlib declarada y usable (math/fs/time/random/os/assert) | ✅ | — |
| `std/io`, `std/format`, `std/log` variádicas en `.pengu` | ❌ | F3 |

---

## 5. Fases

Cada fase es independiente y deja el árbol en verde. El orden está pensado
para que las fases siguientes no dependan de código que se va a reescribir.

### F1 — Correctitud inmediata del frontend y del checker

**Objetivo:** eliminar falsos positivos y aceptar/ rechazar lo que el spec dice,
sin añadir features nuevas.

Tareas:

1. `make_source` elimina el BOM UTF-8 inicial (y prueba con BOM + `invoke`).
2. Unificar la comprobación de asignación:
   - nuevo `check_initialization(ctx, expected, actual, span, contexto)` que
     usa `can_assign` y solo delega en `report_type_mismatch` si es `false`;
   - sustituir las llamadas sueltas a `report_type_mismatch` en
     `checker_stmt.ts` (declaración tipada, `const` tipada, asignación a
     campo/índice) y en `checker.ts` (retornos, argumentos, defectos);
   - `can_assign`: `none` → cualquier opcional; `nullptr` → `raw<T>` (decisión
     §7); numéricos con conversión segura del spec; tupla literal → `tuple`/
     `pair` declarados; `int` literal en rango → tipo entero declarado.
3. `static mut`: corregir el parser (orden `mut` + nombre + `=`) y registrar el
   binding como global inmutable/`static`.
4. Parámetros por defecto: aridad mínima = parámetros sin defecto; validar que
   los defectos son asignables al tipo; prohibir defectos después del variádico.
5. `if ... then` seguido de bloque indentado: tratarlo como bloque (igual que
   `when ... then`), y actualizar el formateador para que no lo rompa.
6. `switch` sobre omen unitario sin `else`: advertencia de exhaustividad
   (mismo código E0701 que `match`, severidad warning).
7. Validación de Display en interpolación y en argumentos variádicos `any`
   (cuando F3 exista; en F1 se deja la infraestructura y se prueban runes).
8. Mensajes: «¿quisiste decir `invoke`?» cuando una palabra clave se escribe
   con mayúscula inicial o existe un identificador parecido (distancia ≤ 1);
   E0101 con «niveles abiertos» y una corrección sugerida de sangría.
9. Banco de regresión de las tres quejas del usuario: BOM, todas las formas de
   `main = ->`, y archivos con 2/4 espacios y tabuladores.

**Criterio de aceptación:** los programas de §1.2 y §1.3 dan el resultado
correcto; `bun test` crece con al menos 12 casos nuevos; `pengu fmt --check`
sigue limpio; ningún ejemplo cambia de salida.

### F2 — Modelo numérico, conversiones y `Ordering`

1. Tipos numéricos como categoría (`is_integer`/`is_float` ya existen; ampliar
   a todos los anchos y signos), con tabla de rangos para literales.
2. `can_assign` con la matriz del spec: ensanchado entero, unsigned→signed más
   ancho, float→double, entero→float/double; nada más sin `as`/`unsafe`.
3. `as` seguro completo + `T::try_from`/`T::from` para primitivos
   (`int::try_from("42")`, `double::try_from("1.5")`, rango, string→número).
4. Métodos de primitivos: `abs`, `min`, `max`, `clamp`, `sign`, `is_nan`,
   `is_infinite`, `to_string`, y los de coma flotante del cheatsheet.
5. `Ordering` como omen del lenguaje (o rune predefinido) y `<=>`:
   - `a <=> b` sobre tipos con `operator <=>` definido o primitivos;
   - derivación de `<`, `<=`, `>`, `>=`, `==`, `!=` desde `<=>`/`==`;
   - código C++ `<=>` cuando esté disponible.
6. `function<(A) -> B>`: parser dedicado de tipos función (lista de parámetros
   con nombres opcionales) y codegen `std::function`.

**Criterio:** `3.5.floor()`, `x: long long = 1`, `p: raw<int> = nullptr`,
`a < b` con rune que define `<=>` y `int::try_from("9")` compilan y corren.

### F3 — Variádicas (lenguaje + codegen + stdlib)

1. AST: `ParamNode.variadic`, `FunctionDecl`/`DeclareDecl`/`MethodDecl`
   variádicos, `CallNode` con `spread` por argumento.
2. Parser: `(...nombre: T)` en funciones, métodos, `declare` y `extern`;
   `f(...xs)` como argumento expandido; validar posición final.
3. Checker: reglas de §3.3; `any` mínimo viable (§3.4) o, si F4 aún no está,
   `any` restringido a variádicas con boxing; Display obligatorio.
4. Codegen: `vector<T>`/`vector<Value>`, spread, tipos función variádicos,
   `declare`/`extern` variádicos (extern solo `unsafe`).
5. Runtime: `::pengu::Value`, `value(x)`, `format_values`, `write_values`,
   `to_string` genérico con `if constexpr requires`.
6. Migrar `io`, `format`, `log` a `.pengu`; limpiar `BUILTIN_FUNCTIONS`.
7. `bindgen`: dejar de descartar variádicas; marcarlas `unsafe`.
8. Documentar en `docs/cheatsheet.md` (sección «Funciones variádicas») y en
   `docs/stdlib.md`.

**Criterio:** `sumar(1,2,3)` y `println("a", 1, true)` definidos por el usuario
funcionan; `bindgen` de `printf` genera una firma usable en `unsafe`.

### F4 — Tipos compuestos completos

1. `array<T, N>`: parser del tamaño (expresión constante), literal `[...]`
   tipado por contexto/`array<int,4>[...]`, sin métodos de tamaño variable.
2. Literales tipados: `vector<int>[...]`, `deque<int>[...]`, `set<int>{...}`,
   `map<string,int>{...}` (el prefijo decide el tipo).
3. `pair`/`tuple`: construcción, `.first`/`.second`, `std::get`, comparación,
   asignación desde literal, desempaquetado múltiple.
4. `deque`, `list`, `forward_list`, `multiset`, `unordered_*`, `stack`,
   `queue`, `priority_queue`, `span`, `bitset`: tipos, operaciones del
   cheatsheet y métodos incorporados.
5. `any` completo (asignación, `as`/`unsafe`, `is<T>`), `variant<...>`
   (construcción, `match` por tipo, `as`), `init_list<T>`.
6. `complex<T>`, `atomic<T>`, `mutex`, `shared_mutex`, `condition_variable`,
   `thread`: tipos y operaciones mínimas del cheatsheet (el resto, fase de
   concurrencia).
7. `wstring`/`u16string`/`u32string`/`string_view`: codegen y métodos.

**Criterio:** cada fila de §4.1 con ❌/🟡 tiene al menos un fixture positivo y
otro negativo (método inválido, tamaño no constante, tipo no asignable).

### F5 — Genéricos completos

1. Sigilos en ámbito durante: firma, cuerpo, campos, constructor, métodos,
   `enchanting`, omens/seals/echoes genéricos.
2. `needs` con capacidades estructurales: `Eq`, `Ord`, `Hash`, `Copy`, `Move`,
   `Default`, `Numeric`, `Floating`, `Display`, `Into<U>`, `From<U>`.
   Validar en la instanciación (explícita o inferida).
3. Instanciación explícita `f<int>(x)` y en tipos `Caja<int>`.
4. Codegen con plantillas C++: `template <class T>` en runes, omens
   (payloads `Ok_V<T>`), echoes (`template <class T> using`), seals,
   funciones y métodos.
5. Chequeo del cuerpo genérico: `T` es opaco con las capacidades declaradas;
   los métodos solo se permiten si están en `needs`.
6. Mensajes de error con el sigilo que no cumple (`E0505 no cumple Ord`).

**Criterio:** `Caja<T>`, `Resultado<T>` con `match`, `Id<T>`, `Lista<T>` y
`id<int>(3)` compilan; un `Caja<Punto>` sin `<=>` que exige `Ord` falla con
E0505.

### F6 — Runes, herencia y operadores

1. `parent(...)` en constructor: marcar el contexto de constructor en el
   emisor (no solo en `check_rune`) y emitir inicialización de base.
2. Herencia: `virtual` en métodos y destructor cuando hay `heir`; upcast seguro
   `ref<Animal>(ref(d))`; prohibir slicing implícito; sombreado de métodos.
3. Operadores de usuario completos: `[]` (incluido `mut ref<V>`), `+=` y
   compuestos, unario `-`/`!` (donde aplique), `()`; lookup único
   (`método con ese operador` → operador libre → tabla incorporada).
4. Operadores libres/simétricos fuera de `enchanting` y su codegen.
5. `enchanting` sobre omens y echoes: reescritura de `obj.m(...)` a función
   libre cuando no hay clase C++ (omen/alias), con `@` = valor subyacente.
6. `Ordering` con métodos (`is_lt`, `reverse`, `then`).

**Criterio:** ejemplos nuevos: rune con `[]` y `+=`; `Animal`/`Perro` con
despacho por `ref<Animal>`; omen con método; echo `Metros` con `doble`.

### F7 — Memoria, préstamos y `unsafe`

1. Ley de Exclusividad: registrar alias `ref(x)` activos por scope; error al
   mutar/asignar/`mut`-pasar mientras exista uno. Usar `do` para cerrar
   préstamos.
2. Contrato `mut` en la llamada: `f(mut x)` exige argumento mutable y binding
   mutable; el parámetro `mut` es solo un contrato.
3. Mutabilidad de campos y métodos: `p.x = ...` y `c.inc()` requieren binding
   `mut` (o `ref<V>`/`mut ref<V>` correcto).
4. Movimiento: por campo/índice, en retorno, en contenedores, y detección de
   uso tras movimiento a través de esos caminos.
5. `unsafe` obligatorio para: deref de `raw<T>`, `static mut`, aritmética de
   punteros, conversiones estrechas, `as` de omen no verificado.
6. `ref`/`mut ref` de retorno de métodos e indexación: registrar el préstamo
   del contenedor.

**Criterio:** los programas de §1.3 fallan con E0406/E0601/E0602/E0603 y los
correctos compilan; `mut` correcto sigue funcionando.

### F8 — Módulos, constantes y evaluación

1. `const` evaluable en compilación: evaluador de literales, aritmética,
   concatenación de cadenas y `const` previas; error si no es evaluable.
2. `static mut`: emisión como variable de módulo y lectura/escritura solo en
   `unsafe`; inicialización constante.
3. Reapertura de `realm` entre archivos: tipos y funciones del mismo realm en
   varias unidades; colisión de tipos detectada.
4. Orden de evaluación: inicialización de `const` de módulo antes de las
   funciones del módulo que las importa; documentar el orden.
5. Acceso cualificado `realm::symbol` sin `invoke` (si el spec lo permite) y
   reglas de visibilidad `_`.

**Criterio:** proyecto con dos archivos del mismo realm, un `static mut` usado
solo en `unsafe`, y un `const` no evaluable que falla con código propio.

### F9 — Endurecimiento y calidad

1. Dividir `checker_expr.ts` y `cpp_expr.ts` (guía: ≤250 líneas) en módulos por
   tema, sin cambiar comportamiento; tests existentes como red.
2. Suíte de conformidad §6 completa y matriz §4 sin ❌.
3. `pengu check --json` (diagnósticos con código, span y notas) para pruebas y
   futuras herramientas.
4. Documentar cada código de error en `docs/errors.md`.
5. Actualizar `scratch/plan_typescript.md`, `README` y `docs/stdlib.md`.
6. Verificación final: `bun test`, `tsc --noEmit`, `pengu fmt --check`,
   `pengu doctor`, ejemplos 01–10 y los nuevos.

---

## 6. Estrategia de pruebas

```
tests/conformance/
  lexico/            BOM, indentación 2/4/tabs, comentarios, escapes
  tipos/             cada primitivo, contenedor, puntero, any/variant
  funciones/         defaults, cierres, variádicas, tipos función
  control/           if/switch/match/loops/comprensiones
  runes/             ctor, dtor, herencia, métodos, operadores
  omens/             unit, flags, algebraicos, genéricos, enchanted
  echo_seal/         transparencia, opacidad, genéricos
  genericos/         sigilos, needs, instanciación
  memoria/           movimiento, préstamos, unsafe
  modulos/           realm, invoke, ciclos, const/static
  stdlib/            cada módulo declarado
```

Cada fixture tiene un `caso.pengu` y un `esperado.json` con:

- `check`: `ok` o lista de códigos;
- `run`: salida esperada (para los que compilan);
- `cxx`: fragmento opcional de C++ esperado (golden, solo para constructos
  delicados: `<=>`, variádicas, genéricos).

Un solo runner (`tests/conformance/run.ts`) recorre los fixtures; los tests de
`bun test` lo invocan. Así se evita duplicar lógica y se ve de un vistazo qué
porcentaje del lenguaje está cubierto.

Negativos obligatorios por feature: Display de rune sin `to_string`, `mut`
sobre inmutable, préstamo activo, variádico no final, `array` sin tamaño
constante, `needs` no cumplido, `[]` vacío sin tipo, `switch` no exhaustivo.

---

## 7. Decisiones que necesitan tu visto bueno

1. **Sintaxis variádica**: `(...xs: T)` + spread `f(...xs)` (recomendada).
   ¿Te encaja o prefieres `vararg xs: T` / `xs: T...`?
2. **`nullptr`**: el spec dice «puntero raw vacío, no un opcional»; hoy el
   checker lo permitiría también en `unique`/`shared`/`weak`. Propongo dejarlo
   solo para `raw<T>` (lo demás se construye con `unique<T>()`).
3. **`any`**: aceptar el coste de `::pengu::Value` (boxing + renderizador) para
   variádicas heterogéneas y `any` normal. Es la única forma de que
   `println("x=", 7)` sea una función de usuario.
4. **Indentación configurable**: `pengu.toml` → `[format] indent_width = 2`,
   con detección del archivo en `fmt` y `--check`. El checker seguirá
   aceptando cualquier ancho consistente; solo cambia el formateador. ¿2 por
   defecto o detectar el archivo?
5. **Herencia**: métodos `virtual` solo cuando un rune tiene herederos
   (estilo C++), con destructor virtual en ese caso. Sin despacho virtual no
   hay polimorfismo real por `ref<Animal>`.
6. **`const`**: limitarlo a expresiones evaluables (literales, aritmética,
   `const` previas). Hoy cualquier cosa pasa; el spec pide const-evaluable.
7. **Operadores libres**: admitirlos fuera de `enchanting` (simétricos) y
   resolver `a + b` con: método del tipo izquierdo → operador libre por tipos.
8. **`enchanting` sobre `echo`/`omen`**: generar funciones libres y reescribir
   la llamada (no se puede añadir métodos a `using`/`enum class`). Es invisible
   para el usuario.

---

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Reescribir el checker rompe ejemplos | Cada fase corre los 10 ejemplos + conformance; cambios detrás de tests primero. |
| Codegen de genéricos con plantillas se complica | Empezar por runes/funciones, luego omens/echo/seal; golden C++ por constructo. |
| Variádicas `any` con vidas prestadas | Boxing por valor para copiables; documentar no-copiables; pruebas de `none`/contenedores. |
| `Display` estructural vs. runes sin método | Validación en checker + `if constexpr requires` en runtime; nunca llegar a C++ inválido. |
| Herencia y slicing | Prohibir conversión implícita; solo `ref<Base>(ref(derivado))`; tests de corte. |
| Ley de Exclusividad con falsos positivos | Modelo por scope léxico como el spec; allowlist para `do`; muchos positivos/negativos. |
| Crecimiento de archivos | F9 obliga a dividir; revisar líneas por archivo en cada fase. |

---

## 9. Bitácora

| Fecha | Fase | Cambios | Pruebas |
|---|---|---|---|
| 2026-11-21 | F7 | Ley de Exclusividad con préstamos por ámbito (`ref` registra el préstamo, `do`/bloques lo liberan, E0602); mutación estructural prohibida durante `for` (E0602); contrato `mut` en la llamada (`incrementar(mut n)`, parámetro declarado `mut`, E0406); campos y métodos `mut` exigen binding `mut` (con excepción de `atomic`/mutex); movimiento por campo e índice (`root_ident`, E0601); `unsafe` obligatorio para `*raw<T>`, `raw<T>(ref(x))`, lectura/escritura de `static mut`, `get_unchecked` y llamadas a funciones `unsafe` (E0603). | 177/177 (18 archivos) |
| 2026-11-21 | F6 | Herencia: `parent(...)`, emisión en dos pasadas por dependencia (`cpp_type_order.ts`), `virtual` en métodos y destructor cuando hay herederos, upcast explícito `ref<Animal>(ref(d))` (implícito prohibido), despacho virtual comprobado; operadores de usuario completos: `[]` mutable, `+=`, unarios, `()`, binarios, `<=>`, operadores libres por ADL y detección de duplicados (E0706); `enchanting` sobre omens (funciones libres) y sellos (`@` es el valor subyacente); `echo` no admite operadores (E0706); sombreado de campos (E0704); `Ordering` como clase con `is_lt`/`is_eq`/`is_gt`/`reverse`/`raw` y variantes `Less/Equal/Greater`; `mut ref<int>` como retorno de `operator []`. | 164/164 (17 archivos) |
| 2026-11-21 | F5 | Sigilos completos: `NamedType.generic` + `generic_type`/`substitute_generics`; sigilos activos al comprobar y emitir runes, omens, echoes, seals y funciones (`with_sigils`); `echo` genérico sustituido en el uso (`Lista<int>` → `vector<int>`); instanciación explícita en tipos, variantes y funciones (`Caja<int>(7)`, `Resultado<int>::Ok(5)`, `identity<int>(42)`) e inferencia por unificación (`unify_sigils`, incluye `vector<T>`); restricciones `needs` comprobadas con E0513; omens genéricos con `template` por variante y `match` con `get_if<Variant<int>>`; constructor sin cuerpo y campos con valor por defecto; aridad de campo con defaults. | 152/152 (16 archivos) |
| 2026-11-21 | F4 | `array<T,N>` con literal y comprobación de tamaño; literales con prefijo de tipo (`vector<int>[...]`, `deque<int>[...]`, `set<T>{...}`, `map<K,V>{...}`); `pair`/`tuple` construidos, accedidos y asignados con tipo exacto; contenedores auxiliares (`stack`, `queue`, `priority_queue`, `bitset`, `list`, `forward_list`, `multiset`, `unordered_*`, `span`) con tablas de métodos y codegen (`size`/`is_empty`/`push`/`pop`/`top`/`test`/`count`); construcciones `vector<int>()`, `mutex()`, `thread(...)`, `complex<T>(re, im)`, `atomic<T>(v)`; `variant<A,B>(v)` con `as` comprobado en compilación; `string_view` acepta `string`; cadenas anchas imprimibles; `Value` del runtime reordenado tras las sobrecargas de `to_string` (tuplas y pares imprimibles); `len` usa `std::distance` si no hay `.size()`; cabeceras de todos los contenedores incluidas en `pengu_rt.hpp`. | 143/143 (15 archivos) |
| 2026-11-21 | F3 | Variádicas `(...xs: T)` con `...` como spread y `...` en tipos de función; dentro del cuerpo el parámetro es `vector<T>`; `any` resuelto como tipo real y empaquetado en `::pengu::Value` (render de `Display` vía `to_string` o `to_string_value`); `check_argument_value` exige Display en variádicas `any` (E0512); `std/io`, `std/format`, `std/log` pasan a `.pengu` con `declare` de primitivas `vector<any>`; `extern` variádico emitido como C varargs; aridad mínima correcta con variádicas. | 129/129 (14 archivos) |
| 2026-11-21 | F2 | Modelo numérico portable (`INTEGER_SHAPES`, `numeric_join`, promoción al entero mayor, sin mezclas de signo del mismo ancho); `is_safe_cast` con matriz completa (enteros por ancho/signo, float, seal, omen subyacente); `T::try_from`/`T::from` para primitivos con comprobación de rango en runtime; métodos `.sqrt()/.abs()/.is_nan()`; `Ordering` con `<=>` (`::pengu::compare`) y variantes `Less/Equal/Greater`; `function<Sig>` ahora se analiza (lookahead de `<`); operadores de usuario recuperados para `+`/`-`/etc. | 119/119 (13 archivos) |
| 2026-11-21 | F1 | BOM ignorado por el lexer; `check_initialization` con `can_assign` real (enteros por ancho y signo, float→double, `none`/`nullptr` restringidos, literales que caben, tupla→`pair`/`tuple`); `static mut` arreglado; `then` + bloque; aridad mínima con defaults (`FunctionType.required`); aviso E0701 en `switch` sin `else` sobre omen unitario; Display obligatorio en interpolaciones (E0512); sugerencias de nombre (E0403/E0208) y arreglo para E0101. | 106/106 (12 archivos) |

---

## 10. Orden recomendado de trabajo

```
F1  correctitud (BOM, asignaciones, static, defaults, then-bloque)   ← primero
F2  numérico + conversiones + Ordering/<=> + tipos función
F3  variádicas + any mínimo + stdlib io/format/log
F4  tipos compuestos (array/tuple/pair/contenedores/variant/any)
F5  genéricos completos
F6  runes: herencia, operadores, enchanting de omen/echo
F7  memoria: exclusividad, mut, movimiento, unsafe
F8  módulos: const eval, static, realm, orden de evaluación
F9  conformance total, refactor, documentación
```

F1 y F2 son requisito para F3 (Display y asignaciones). F4 puede solaparse con
F5, pero conviene cerrar tipos antes de plantillas. F6 y F7 son independientes
entre sí; F8 no bloquea nada. El objetivo de cada fase es que el compilador
rechace con un diagnóstico claro todo lo que el spec prohíbe y acepte todo lo
que permite, sin llegar nunca a un error de C++ sin explicación.
