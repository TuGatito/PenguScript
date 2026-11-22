# Plan — atacar las limitaciones documentadas de PenguScript

> Estado: **borrador para revisión** (2026-11-21). No se ha tocado código.
> Fuente de verdad del lenguaje: `docs/cheatsheet.md`.
> Lema del proyecto: cero deuda técnica, cero cajas negras, nada implícito
> que el programador no pueda ver.

Este documento hace tres cosas:

1. **Inventaria** todas las limitaciones declaradas en la documentación (L1–L22).
2. **Audita** cada una contra la ideología del lenguaje y contra el estado real
   del compilador, con evidencia ejecutada.
3. Propone **fases H1–H7** para implementarlas sin romper lo que ya funciona,
   y marca las decisiones (D1–D7) que necesitan el visto bueno del usuario.

---

## 0. Resumen ejecutivo

De las 22 limitaciones inventariadas (L9 aporta una cosa a dos categorías):

- **6 agujeros de sonoridad**: el checker acepta código que el C++ rechaza o
  que pierde una garantía — L2, L3, L5, L6, L7, L13.
- **1 contradicción con la spec**: L1 (despacho virtual). Lo implementamos en
  F6 y el cheatsheet dice tres veces que **no** existe.
- **3 deudas de diagnóstico o documentación**: L9 (mensaje absurdo de
  `range<int>`), L21 (bindgen omite variádicas que `extern` ya soporta), L22
  (README/cheatsheet desactualizados).
- **4 ampliaciones** que caben en la ideología: L4, L8, L9 (rangos como valor),
  L12.
- **9 decisiones de diseño** que **no** vamos a implementar y que solo hay que
  documentar mejor: L10, L11, L14, L15, L16, L17, L18, L19, L20.

El orden propuesto ataca primero lo que rompe la confianza (código aceptado que
explota en C++), luego la conformidad con la spec, luego las ampliaciones.

---

## 1. Inventario numerado

Cada entrada: qué promete o niega la documentación, dónde está, y qué hace hoy
el compilador (verificado con `pengu check`/`pengu run`).

### L1 — Despacho virtual (contradicción)

- Doc: `docs/cheatsheet.md:36` («Not in v0.2.0: … no virtual dispatch»),
  `:2238` («Runes are not classes. There is no virtual dispatch»),
  `:2477` («No `override` keyword; no virtual dispatch; the shadow is resolved
  statically by the compile-time type of the receiver»).
- Estado real: `src/codegen/cpp_type_order.ts` calcula `heir_names` y
  `src/codegen/cpp_decl.ts` emite `virtual` en métodos y destructores cuando un
  rune tiene herederos. `examples/11_polimorfismo` imprime `Toby: guau` pasando
  `ref<Animal>(ref(Perro(...)))`: eso **es** despacho dinámico.
- Veredicto: **implementamos de más**. La spec es explícita y la ideología
  («nada de OOP, todo estático y visible») apoya la spec.

### L2 — Panics que escapan como excepciones C++

- Doc: `:36` («No exceptions»), `:3338` («The panic is not a C++ exception; the
  runtime terminates the process with a message»), `:1369` (`arr[i]` panics).
- Estado real: `::pengu::panic` lanza `std::runtime_error`, `vec_at` usa `.at()`
  (lanza `std::out_of_range`) y `main` no captura. `pengu run` sobre `xs[5]`:
  ```
  terminate called after throwing an instance of 'std::out_of_range'
    what():  vector::_M_range_check: __n (which is 5) >= this->size() (which is 2)
  ```
  sin mensaje de PenguScript y con código de salida de aborto.
- Veredicto: agujero real de experiencia y de contrato.

### L3 — `any` no extraíble con `as`

- Doc: `:218` («`any` … se puede imprimir, pero no extraer con `as`»).
- Estado real: `x: any = 4` + `x as int` pasa el checker sin diagnósticos y
  falla en C++ con `E0803` (`static_cast` sobre `::pengu::Value`).
- Veredicto: agujero real: el checker acepta algo que la spec prohíbe y que el
  codegen no sabe emitir.

### L4 — `string` sin `get`/`pop`

- Doc: `:581` («There is no `s.get(i)`/`s.pop()` API in v0.2.0»).
- Estado real: `s.get(1)` → `E0506 el tipo «string» no tiene el miembro «get»`;
  `s.pop()` → igual. Existe `s[i]` (panics) y no hay forma segura de indexar.
- Veredicto: ampliación razonable y barata, en `std/string.pengu` (enchanting).

### L5 — Funciones con parámetros `mut` no son valores

- Doc: `:736` («A `mut` parameter is a calling contract, not part of the type,
  so function values with `mut` parameters are not first-class»).
- Estado real: asignar `incrementar` (con `mut x: int`) a
  `function<(int) -> void>` pasa el checker; el C++ generado es
  `std::function<void(int)> f = incrementar;` con `incrementar` de firma
  `void(int&)` → error de compilación C++ (`E0803`).
- Veredicto: agujero real; además el contrato `mut` se pierde en silencio.

### L6 — Funciones `unsafe` no son valores

- Doc: `:736` («`unsafe` functions are not first-class values either»).
- Estado real: `f: function<(raw<int>) -> int> = leer` (con `unsafe leer`)
  pasa el checker; llamar `f(...)` **no** exige `unsafe` en el punto de llamada
  y dentro se desreferencia un `raw<T>`. La barrera de `unsafe` se pierde.
- Veredicto: agujero de sonoridad real (el más serio de la lista).

### L7 — Hash sintetizado de runes (prometido, no emitido)

- Doc: `:1591` («A rune used as a key must declare `operator ==` for the
  unordered forms; its hash is synthesized field-by-field in declaration order»).
- Estado real: `map<Punto, int>` con una rune compila el checker pero el C++
  falla: no existe `std::hash<hash_rune::Punto>` (el error final es del
  `std::hash` de la rune). Tampoco se sintetiza `operator ==` (la doc lo exige
  declarado; el que falta es el hash).
- Veredicto: promesa incumplida; o se emite el hash, o se retira la promesa.

### L8 — Operaciones de conjunto

- Doc: `:1614` («Set operations (`union`, `intersection`, `difference`) are not
  defined in v0.2.0»).
- Estado real: `std/set.pengu` ya añadió `union(ref<set<T>>)`; `intersection` y
  `difference` no existen (`E0506`). La doc está desactualizada a medias.
- Veredicto: ampliación trivial en `std/set.pengu` (ya hay iteración e
  `insert`).

### L9 — Rangos no son valores de primera clase

- Doc: `:2014` («Ranges are not first-class values in v0.2.0 — they only appear
  in `for`»).
- Estado real: `sumar(1..10)` → `E0501 el argumento 1 de «sumar» espera «int»,
  recibió «range<int>»` (razonable). Pero además:
  `r: range<int> = 1..10` → `E0501 se esperaba «range<int>» en la
  inicialización, se encontró «range<int>»`: **mensaje absurdo**, dos tipos que
  se imprimen igual y no son iguales (`range` resuelto como `named("range")`
  sin argumento). Bug de diagnóstico real, independiente de si hacemos los
  rangos de primera clase.
- Veredicto: hay un bug (mensaje) y una ampliación (valores de rango).

### L10 — Sin constructores de copia/movimiento

- Doc: `:2305` («No copy or move constructors in v0.2.0. A rune is copyable iff
  all its fields are copyable… This is the C++ default»).
- Estado real: coherente; el codegen no emite nada y C++ usa la copia/movimiento
  por campos.
- Veredicto: **decisión de diseño**; no implementar. Documentar que `=` es
  copia/movimiento y que los campos mandan.

### L11 — Seals: sin unwrap transitivo ni `as` entre sellos

- Doc: `:3129`.
- Estado real: `is_safe_cast` solo permite `A as <subyacente>` y
  `Celsius(m as double)` para sello→sello. Coherente.
- Veredicto: **decisión de diseño** (fuerza conversiones visibles). Mantener.

### L12 — Punteros inteligentes no enhechizables

- Doc: `:3203`.
- Estado real: `enchanting unique<int>` → `E0709 «unique» no es un tipo al que
  se pueda enhechizar`.
- Veredicto: ampliación razonable. `unique<T>`, `shared<T>`, `weak<T>` por
  referencia; `raw<T>` solo accesible desde `unsafe`.

### L13 — Método enhechizado con sobrecargas usado como valor

- Doc: `:3203` («An enchanted method cannot be used as a value unless it has a
  single overload»).
- Estado real: `f = s.compare` (con `compare` sobrecargado en `std/string`)
  pasa el checker; el C++ generado falla con `E0803`. `resolve_enchanted_member`
  devuelve `any_type('método sobrecargado «compare»')` y nadie lo comprueba.
- Veredicto: agujero real; debe ser un error de checker con mensaje claro.

### L14 — Visibilidad solo con import

- Doc: `:3203`.
- Estado real: coherente (los métodos viven en el `Env` del módulo importado).
- Veredicto: **decisión de diseño** (explícito, sin magia). Mantener.

### L15 — Sigilos: sin constraints de usuario, defaults, variádicos, HKT, especialización

- Doc: `:3641`.
- Estado real: coherente; `needs` solo acepta las capacidades incorporadas
  (E0513).
- Veredicto: **decisión de diseño**. Un `concept` de usuario abre la puerta a
  un sistema de tipos mucho más grande; no entra en 0.1.0. Mantener y
  documentar el porqué.

### L16 — Omens sin operadores

- Doc: `:4027`.
- Estado real: `enchanting Color { operator + … }` → `E0706`.
- Veredicto: **decisión de diseño** (un enum con `+` casi siempre es un rune
  disfrazado). Mantener.

### L17 — Operadores no sobrecargables (`=`, `&&/||/!`, `++/--`, `as`, `&/*`) y sin impls por defecto

- Doc: `:4067`.
- Estado real: coherente (no hay ramas en el checker para esos operadores; `!=`
  derivado de `==` y comparaciones de `<=>` se emiten por la tabla del runtime).
  `<=>` simétrico funciona con free operator.
- Veredicto: **decisión de diseño**. Mantener; documentar mejor `<=>` simétrico
  (ya es posible con `operator <=>` libre).

### L18 — `+=` no se deriva de `+`

- Doc: `:4067` («compound operators are never derived»).
- Estado real: rune con `operator +` y sin `operator +=`: `a += b` → `E0501
  «+=» no está definido para «Numero»`.
- Veredicto: **decisión de diseño** (lo explícito gana). Mantener; añadir nota
  en la sección de operadores.

### L19 — `init_list<T>` solo como parámetro

- Doc: matriz F4 de `scratch/plan_compiler_completo.md`; no está en el
  cheatsheet como limitación de usuario.
- Estado real: `l: init_list<int> = [1, 2]` → `E0501 … se encontró
  «vector<int>»`; interpolar un `init_list` → `E0512`. Coherente con «un
  `initializer_list` no se puede almacenar» de C++.
- Veredicto: **decisión de diseño**; documentar en el cheatsheet.

### L20 — `to_upper`/`to_lower` solo ASCII

- Doc: no está documentado (lo mencioné al cerrar G4).
- Estado real: `std/string.pengu` usa `::pengu::to_upper_raw` con `<cctype>`.
  `PINGÜINOS` → `PINGÜINOS` (la `Ü` no cambia). El ejemplo 12 lo muestra tal
  cual.
- Veredicto: Unicode completo exige tablas/ICU; **documentar** el
  comportamiento ASCII y ofrecer `to_upper_unicode` como trabajo futuro.

### L21 — `bindgen` omite funciones C variádicas

- Doc: bitácora F3 en `scratch/plan_compiler_completo.md` («pengu bindgen still
  SKIPS variadic C functions»).
- Estado real: `src/bindgen/clang_ast.ts` marca `variadic` y
  `src/bindgen/emit.ts` las descarta con motivo; pero `extern "C"` variádico
  **sí** funciona desde F3 (probado en `tests/regression/f3.test.ts`).
- Veredicto: ampliación barata: emitir la declaración con `...` y añadir el
  caso al e2e de bindgen.

### L22 — Documentación obsoleta o incoherente

- `README.md:81`: «porque aún no hay funciones variádicas en el lenguaje» —
  falso desde F3 (las variádicas existen y `std/io` las usa).
- `docs/cheatsheet.md:1614`: dice que `union` no existe; `std/set` ya la ofrece.
- `docs/cheatsheet.md:36` y `:2477`: «no virtual dispatch» — hoy el codegen
  emite `virtual` (ver L1).
- `docs/stdlib.md`: no menciona `to_upper`/`to_lower` ASCII.
- Veredicto: deuda documental real; se cierra en la fase final.

---

## 2. Auditoría: ¿implementar o no?

Criterios aplicados, en este orden:

1. **Conformidad con la spec** (el cheatsheet manda).
2. **Ideología**: explícito, sin magia, sin OOP, sin excepciones al usuario,
   errores en compilación antes que en C++.
3. **Coste/riesgo**: ¿cuántas fases, cuántos archivos, cuántos casos borde?
4. **Valor real** para quien escribe PenguScript.

| # | Limitación | ¿Real? | Decisión | Fase |
|---|---|---|---|---|
| L1 | Despacho virtual | Contradice la spec | **Eliminar `virtual`** (despacho estático) | H2 |
| L2 | Panics como excepciones | Agujero | **Capturar en `main`**, mensaje `panic: …`, exit 1 | H1 |
| L3 | `any as T` | Agujero | **Rechazar** en el checker (código nuevo E0514) | H1 |
| L4 | `string.get/pop` | Ampliación | Implementar en `std/string.pengu` | H4 |
| L5 | Fn con `mut` como valor | Agujero | **Rechazar** (E0515) con nota | H1 |
| L6 | Fn `unsafe` como valor | Agujero de sonoridad | **Rechazar** (E0515) con nota | H1 |
| L7 | Hash de runes | Promesa incumplida | **Sintetizar** `std::hash` + exigir `==` | H3 |
| L8 | Ops de conjunto | Ampliación | `intersection`, `difference`, `is_subset` en `std/set` | H4 |
| L9 | Rangos primera clase | Bug + ampliación | Arreglar mensaje; `range<T>` como valor | H5 |
| L10 | Sin ctors copia/movimiento | Diseño | Mantener; documentar | H7 |
| L11 | Seals transitivos | Diseño | Mantener; documentar (ya está) | H7 |
| L12 | Punteros enhechizables | Ampliación | Implementar `unique/shared/weak`; `raw` solo unsafe | H6 |
| L13 | Miembro sobrecargado como valor | Agujero | **Error de checker** (E0708/E0516) | H1 |
| L14 | Visibilidad por import | Diseño | Mantener | H7 |
| L15 | Sigilos avanzados | Diseño | Mantener; documentar el porqué | H7 |
| L16 | Operadores en omens | Diseño | Mantener | H7 |
| L17 | Operadores prohibidos | Diseño | Mantener; documentar `<=>` simétrico | H7 |
| L18 | `+=` no derivado | Diseño | Mantener; nota explícita | H7 |
| L19 | `init_list` solo parámetro | Diseño | Mantener; documentar en cheatsheet | H7 |
| L20 | `to_upper` ASCII | Decisión | Documentar ASCII; futuro UTF-8 | H7 |
| L21 | Bindgen variádicas | Ampliación | Emitir `...` y probar e2e | H6 |
| L22 | Docs obsoletas | Deuda | Corregir README/cheatsheet/stdlib | H7 |

### Lo que **no** vamos a implementar (y por qué)

- **Constructores de copia/movimiento (L10)**: C++ ya define la semántica de
  campos y la spec la asume. Añadir sintaxis sería ruido sin ganancia.
- **Unwrap transitivo de sellos (L11)**: la conversión encadenada es una señal
  de diseño malo; la spec lo dice y lo compartimos.
- **Constraints de usuario, sigilos con default/variádicos/HKT,
  especialización (L15)**: es un sistema de tipos distinto. Si algún día se
  hace, merece su propia discusión; hoy no hay caso de uso en `std`.
- **Operadores en omens (L16)**: un omen es un `enum class`; si necesitas
  aritmética, necesitas un rune. Es exactamente la clase de «magia» que el
  lenguaje evita.
- **`=`, `&&/||/!`, `++/--`, `as`, `&`/`*` (L17)**: son la gramática del
  lenguaje, no huecos de la librería.
- **`+=` derivado de `+` (L18)**: derivar operadores compuestos esconde coste
  (copia vs `mut`) y rompe la regla «se declara lo que se usa».

---

## 3. Decisiones que necesitan visto bueno (D1–D7)

- **D1 (L1).** ¿Eliminamos el despacho virtual para cumplir la spec, o
  cambiamos la spec para permitirlo?
  - *Recomendado*: **eliminar**. Es lo que dice el cheatsheet en tres sitios,
    encaja con «no OOP» y hace el despacho visible en el tipo del receptor.
    Coste: `src/codegen/cpp_type_order.ts` deja de necesitar `heir_names`;
    `cpp_decl.ts` deja de emitir `virtual`; `examples/11_polimorfismo` pasa a
    mostrar herencia con llamadas estáticas; el test de F6 se ajusta.
  - *Alternativa*: mantener `virtual` y reescribir el cheatsheet. Rompe la
    promesa de «todo estático» y complica el modelo de objetos.
- **D2 (L3).** `any`:
  - *Recomendado*: **rechazar** `as` sobre `any` con E0514 ««any» no se puede
    convertir; guárdalo en un tipo concreto».
  - *Alternativa*: dar a `::pengu::Value` un `std::variant` de tipos conocidos y
    permitir `as` comprobado en runtime (coste alto, cambio de ABI interna).
- **D3 (L7).** Hash de runes:
  - *Recomendado*: **sintetizar** `std::hash<Rune>` campo a campo (con
    `std::hash` de cada campo) y exigir `operator ==` declarado, tal como dice
    la spec; error de compilación con mensaje claro si un campo no es hasheable.
  - *Alternativa*: función `to_hash` declarada por el usuario (nueva superficie
    de lenguaje, fuera de v0.2.0).
- **D4 (L9).** Alcance de los rangos como valor:
  - *Recomendado*: `range<T>` se puede declarar, pasar, devolver, iterar,
    `#r` (tamaño) y `x in r`; sin métodos adicionales.
  - *Alternativa*: solo arreglar el mensaje de error y dejar los rangos como
    azúcar de `for` (menos valor, menos riesgo).
- **D5 (L12).** Enchanting de punteros:
  - *Recomendado*: `unique<T>`, `shared<T>`, `weak<T>` con receptor por
    referencia; `raw<T>` solo si el método se declara `unsafe`; `weak.lock()`
    sigue siendo nativo.
  - *Alternativa*: solo `unique`/`shared`, dejando `weak`/`raw` fuera.
- **D6 (L20).** Unicode en `to_upper`/`to_lower`:
  - *Recomendado*: documentar ASCII y dejar UTF-8 para cuando exista `std/unicode`.
  - *Alternativa*: implementar un mapeo UTF-8 básico (Latin-1 + griego/cirílico
    común); coste medio y resultados incompletos.
- **D7 (L21).** Bindgen variádico:
  - *Recomendado*: emitir `name = (fijos…) -> R` con `...` cuando la función C
    sea variádica, y documentar que solo admite primitivos/`string` en la parte
    variable (como el `extern` actual).
  - *Alternativa*: seguir omitiéndolas (menos superficie, deuda documental).

Si el usuario aprueba «todo lo recomendado», D1–D7 quedan como arriba.

---

## 4. Fases

Cada fase deja el árbol en verde: `bun test`, `bunx tsc --noEmit`,
`pengu fmt --check examples std`, los 12 ejemplos y los casos de conformidad.
Ninguna fase cambia la versión: todo sigue en **0.1.0** hasta que el usuario
decida publicar.

### H1 — Cerrar agujeros de sonoridad y de diagnóstico

Objetivo: que el checker nunca acepte algo que el codegen no sepa emitir.

1. **L2**: `src/codegen/cpp_module.ts` envuelve la llamada a `main` en
   `try { … } catch (const std::exception& e) { std::fprintf(stderr, "panic: %s\n", e.what()); return 1; }`;
   `::pengu::panic` y `vec_at`/`map_at` lanzan `std::runtime_error` con mensaje
   en español. `panic` documentado como terminación controlada.
2. **L3**: nueva `CODES.invalid_any_cast = "E0514"`; en `infer_cast`,
   si el origen es `any` → E0514 ««any» no se puede convertir con «as»; usa un
   tipo concreto al asignarlo». `is_safe_cast` deja de aceptar `any`.
3. **L5**: `CODES.unsafe_value = "E0515"` (o reutilizar E0515 como
   `not_first_class`). En `check_initialization`/`check_argument_value`, si el
   valor es una referencia a una función con algún parámetro `mut` y el destino
   es `function<…>` → E0515 ««f» tiene parámetros «mut» y no es un valor de
   primera clase».
4. **L6**: misma comprobación para `FunctionInfo.is_unsafe` → E0515 ««f» es
   «unsafe» y no se puede guardar en un valor de función».
5. **L13**: en `infer_member` (rama de enhechizados), si
   `resolve_enchanted_member` devuelve `más de una` sobrecarga y el nodo se usa
   como valor (no como callee) → **E0708** con la lista de firmas.
6. **L9 (parcial)**: `resolve_named_type` resuelve `range<T>` a un tipo
   `named("range",[T])` coherente (o `range_type`) para que el mensaje de
   `r: range<int> = 1..10` sea correcto; se mantiene «los rangos no se pasan a
   funciones» hasta H5, pero con mensaje claro.

Pruebas: `tests/regression/h1.test.ts` con un caso por agujero (aceptación y
rechazo), más un `run` que comprueba `panic: índice fuera de rango` y exit 1.
Criterio: ningún `E0803` por estas causas en la suite.

### H2 — Despacho estático (conformidad con la spec)

1. `src/codegen/cpp_decl.ts`: dejar de emitir `virtual` (métodos y destructor).
   `heir_names`/`cpp_type_order.ts` se simplifican: `order_type_decls` se queda
   (el orden base→hija sigue haciendo falta), `heir_names` se elimina.
2. `examples/11_polimorfismo/main.pengu`: reescribir para mostrar herencia sin
   despacho dinámico (llamadas sobre el tipo estático; documentar en un
   comentario que el despacho es estático).
3. `docs/cheatsheet.md`: la sección de herencia ya lo dice; se añade una nota
   de implementación en «Estado en 0.1.0 (operadores e herencia)» y se corrige
   la tabla de decisiones.
4. Tests: `tests/regression/f6.test.ts` cambia la expectativa de despacho
   (el `ref<Animal>` llama a `Animal::hablar`); nuevo caso que demuestra que
   `Perro` como tipo estático sí llama a su método.

Riesgo: el ejemplo 11 y un test de F6 cambian de salida; es intencional.

### H3 — Hash sintetizado de runes

1. `src/codegen/cpp_decl.ts`: al emitir un rune, si se usa como clave de un
   contenedor no ordenado (o siempre, por simplicidad), emitir fuera del realm:
   ```cpp
   template <> struct std::hash<realm::Punto> {
     std::size_t operator()(const realm::Punto& value) const noexcept {
       std::size_t h = 0;
       h = ::pengu::hash_combine(h, std::hash<int>{}(value.x));
       …
       return h;
     }
   };
   ```
   con `::pengu::hash_combine` nuevo en el runtime. Runas genéricas: emitir
   `template <typename T> struct std::hash<realm::Caja<T>>` con las mismas
   reglas.
2. Comprobación en el checker: si un campo no tiene `std::hash` disponible
   (p. ej. `vector<int>`), error E0501 ««Rune» no se puede usar como clave:
   el campo «xs» no es hasheable»; sugerir contenedor ordenado.
3. `std/set`/`std/map`: nada que cambiar.

Pruebas: `map<Punto,int>` y `unordered_set<Punto>` corren y deduplican;
rune con `vector<int>` → error de checker; rune sin `operator ==` usada como
clave → error con nota.

### H4 — `std/string` y `std/set` más completos

1. `std/string.pengu`: `get(i: size_t) -> char?` (bounds-checked, `none` si
   fuera), `pop` como `mut` que devuelve `char?`; `chars` no (ya se itera).
2. `std/set.pengu`: `intersection(ref<set<T>>)`, `difference(ref<set<T>>)`,
   `is_subset(ref<set<T>>)`, `symmetric_difference(ref<set<T>>)`.
3. Tests en `tests/regression/h4.test.ts` + casos de conformidad nuevos.

### H5 — Rangos como valor

1. Tipo `range<T>` real en el checker (`range_type(element)`), con `#r`,
   `x in r`, iteración en `for`, paso a funciones y retorno. `1..2..` no;
   `step` solo en `for`.
2. Codegen: `cpp_type(range<T>)` = `::pengu::Range<T>`; `#` → `len(range)`;
   `in` → `contains(range, value)`.
3. Cuidado: `for i = a, b, step` sigue siendo numérico; `for x in 1..10` usa el
   iterador de `Range`.

Pruebas: `sumar(r: range<int>)`, `r = 1..4`, `#r`, `3 in r`, `for x in r`.

### H6 — Enchanting de punteros y bindgen variádico

1. `enchant_target_of`: `unique`, `shared`, `weak` (arity 1, por referencia),
   `raw` (arity 1, solo unsafe). Receptor C++: `const std::unique_ptr<T>&` o
   `const T*`; `@` del método es el puntero.
2. `std/memory.pengu` con métodos mínimos (`is_null` para `raw`).
3. Bindgen: `emit.ts` deja de descartar variádicas; `clang_ast.ts` ya expone
   `variadic`; el e2e `tests/e2e/bindgen_native.test.ts` gana una función
   variádica (`int sumar_todos(int n, ...)`).

### H7 — Documentación, conformidad y cierre

1. `README.md:81` (variádicas), `docs/cheatsheet.md` (L10, L11, L15–L20,
   `std/set`), `docs/stdlib.md` (ASCII, nuevos métodos, punteros),
   `CHANGELOG.md` bajo `0.1.0`.
2. Casos de conformidad nuevos para L2, L3, L5, L6, L7, L12, L13, L21.
3. Bitácora en este documento y en `plan_compiler_completo.md`.
4. Verificación final completa y commit.

---

## 5. Matriz de impacto

| Área | Archivos que cambian | Riesgo |
|---|---|---|
| Codegen runas/virtual | `cpp_decl.ts`, `cpp_type_order.ts` | Medio: ejemplo 11 y F6 |
| Checker | `checker_ops.ts`, `checker_call.ts`, `checker_member.ts`, `checker_context.ts` | Bajo (reglas nuevas) |
| Runtime | `runtime_source.ts` (panic, hash_combine) | Bajo |
| std | `std/string.pengu`, `std/set.pengu`, `std/memory.pengu` | Bajo |
| Bindgen | `emit.ts`, e2e | Bajo |
| Docs | cheatsheet, stdlib, README, CHANGELOG | Ninguno |

Nada de esto toca el formato del manifiesto `pengu.toml`, ni la CLI, ni el LSP
(salvo el hover de los métodos nuevos, que sale gratis del registro).

---

## 6. Riesgos y mitigaciones

1. **Cambiar el despacho de `ref<Animal>`** puede confundir a quien leyó el
   ejemplo anterior. Mitigación: nota explícita en el ejemplo y en el
   cheatsheet; el test nuevo demuestra la regla estática.
2. **Hash sintetizado** puede romper runes con campos no hasheables que hoy
   «compilan» hasta el C++. Mitigación: es exactamente lo que queremos (error
   temprano); se documenta el mensaje.
3. **Rangos como valor** tocan `for` y `in`. Mitigación: fase aislada, casos de
   conformidad de `for` numérico y de rango, y la suite completa por fase.
4. **Panics capturados** cambian el código de salida de aborto (134) a 1.
   Mitigación: prueba que lo fija y nota en el CHANGELOG.

---

## 7. Criterio de terminado

- `bun test` y `bunx tsc --noEmit` en verde; `pengu fmt --check` sin cambios;
  los 12 ejemplos corren; casos de conformidad nuevos pasando.
- Ningún camino del checker acepta código que el codegen no pueda emitir
  (cubierto por H1).
- La documentación no promete nada que el compilador no haga (L22 + L7 + L8).
- `CHANGELOG.md` actualizado bajo `0.1.0` y commit en `main` (push manual del
  usuario).

---

## 8. Bitácora

- **H1** ✅ — `any` fuera de `as` (E0514); `mut`/`unsafe` no son valores de primera clase (E0515); miembro enhechizado con una sola sobrecarga sí es valor, con varias o `mut` no; `xs[i]` lanza un panic con mensaje (`índice 5 fuera de rango (tamaño 2)`) y `main` lo imprime como `panic: …` con exit 1; `range<T>` se anota y se pasa. Suite 248/248.
- **H2** ✅ — sin `virtual`: la herencia despacha con el tipo estático; `examples/11_polimorfismo` y las pruebas de F6 muestran la diferencia entre `Perro` y `ref<Animal>`. Suite 257/257.
- **H7** ✅ — documentación al día: README (variádicas, ejemplo 13), cheatsheet (rangos, `any`, `init_list`, ASCII de `to_upper`/`to_lower`, punteros enhechizables), `std/memory` en `docs/stdlib.md`, `CHANGELOG` con las fases H1–H7, banco de conformidad H1–H6 y ejemplo `examples/13_enchanting`. Suite 278/278.
- **H6** ✅ — `enchanting unique<T>`/`shared<T>` con `@` = valor apuntado (`get`, `mut set`) y `enchanting weak<T>` con `@` = puntero (`is_alive`, `mut` rechazado con E0710); `raw<T>` sigue sin poder enhechizarse (E0709); `pengu bindgen` ya emite funciones C variádicas (`...resto: any`) y las llamadas cualificadas `demo::sumar_varios(3, 10, 20, 30)` pasan los argumentos sin caja `any`. Suite 271/271.
- **H5** ✅ — `range<T>` es un valor: se anota, se pasa, se devuelve, se mide con `#` y se prueba con `in`; `Range` gana `size()` y sus iteradores declaran los rasgos de `std::iterator_traits`; el checker resuelve `range<T>` y la heurística de tipo de retorno acepta `Nombre<Args>`. Suite 267/267.
- **H4** ✅ — `@ = valor` en métodos `mut` (E0406 si el método es `const`); `std/string` gana `get`/`mut pop`; `std/set` gana `intersection`, `difference`, `symmetric_difference` e `is_subset`; los bucles como sentencia se emiten sin lambda (un `return` dentro sale de la función) y la interpolación evalúa sus partes de izquierda a derecha (`join_parts`). Suite 263/263.
- **H3** ✅ — `std::hash` sintetizado para runes (campo a campo, orden de declaración) y sellos (valor subyacente); `hash_combine` en el runtime para `pair`/`tuple`/`optional`; el checker exige `==` en claves `unordered_*`, campos hasheables y `<=>`/`<` en claves ordenadas; las comparaciones se derivan de `<=>`; `for k, v in map` liga clave y valor (antes ligaba índice entero). Suite 257/257.

| Fecha | Fase | Resumen | Pruebas |
|---|---|---|---|
| 2026-11-21 | — | Inventario y auditoría; plan escrito. Sin cambios de código. | 237/237 (25 archivos) |
