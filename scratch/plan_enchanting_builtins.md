# Plan: `enchanting` sobre tipos incorporados (`string`, `vector`, …)

Estado: **aprobado** (2026-11-21). Decisiones D1–D8 aceptadas con dos
cambios: todos los `invoke` son explícitos (D1) y `tuple` entra en esta ronda
(D6). Versión del proyecto: se mantiene `0.1.0` (la del lenguaje documentada
es 0.2.0).

---

## 1. Objetivo

Permitir que cualquier módulo —empezando por `std/`— declare métodos dentro de
un tipo **incorporado**, para que el código de usuario escriba:

```pengu
"  hola  ".trim()
s.compare(otro)
xs.contains(3)
m.get_or("clave", 0)
pares.first
```

Es decir: `enchanting` deja de aceptar solo runes, omens, `echo` y `seal`, y
pasa a aceptar también primitivos, contenedores y tipos de la biblioteca
estándar, **incluidos los genéricos** (`vector<T>`, `map<K, V>`, `array<T>`,
`pair<A, B>`, `tuple<A, B>`…).

La meta de producto es que `std/string.pengu`, `std/vector.pengu`, etc. declaren
en PenguScript la superficie de métodos que hoy están cableados en el checker y
que C++20 ya ofrece, y que a partir de ahí podamos añadir métodos nuevos sin
tocar el compilador.

---

## 2. Estado actual (evidencia)

- `enchanting` solo resuelve destinos registrados como rune, omen o alias:
  `src/semantic/module_info.ts:277` (`register_enchanting`) devuelve
  `«X» no es un tipo al que se pueda enhechizar` (E0502) para `string`.
- El AST del destino es un **identificador simple**: `parsed_enchanting` en
  `src/frontend/parser_decl.ts:648` hace `expect_ident`, y los sigilos van
  aparte (`enchanting Box<T>`). No hay forma de escribir `vector<T>` como
  destino porque el nombre y los argumentos se confunden con sigilos.
- Los métodos de tipos incorporados viven en tablas del checker:
  `src/semantic/builtin_members.ts` (`member_of_builtin`, `builtin_index_result`,
  `MUTATING_MEMBERS`). Añadir un método nuevo exige editar esa tabla **y**
  `emit_member_call` en `src/codegen/cpp_expr_call.ts`.
- Resolución de miembros (`src/semantic/checker_member.ts`, `infer_member`):
  ref/unique/shared/raw → auto-deref; luego rune → alias → omen → echo →
  tabla incorporada. No hay paso intermedio para métodos declarados en `std`.
- Emisión de métodos ya existente para omens y `echo`:
  `emit_free_methods` en `src/codegen/cpp_decl.ts:281` genera funciones libres
  `Ret nombre(const Self& self, …)` dentro del `namespace` del realm y fija
  `g.self_expression = "self"`. Es exactamente el molde que necesitan los
  tipos incorporados, que en C++ no admiten métodos añadidos.
- `MethodInfo` (`src/semantic/type_env.ts:34`) guarda `params`, `result`,
  `mutable`, `operator`, `sigils`, `param_mutables`, `variadic`. No guarda el
  realm ni admite sobrecargas: el mapa es `nombre → método`.
- Los realms se fusionan por nombre entre archivos (`merge_realm_envs` en
  `src/project/module_graph.ts:82`), pero **no** se comparten métodos entre
  módulos que no comparten realm. Un `std/string.pengu` con `realm string` no
  sería visible desde `realm main` sin un mecanismo nuevo.

---

## 3. Diseño

### 3.1 Sintaxis: el destino es un patrón de tipo

```pengu
enchanting string
  compare = (otro: string) -> int
    …

enchanting vector<T>
  contains = (valor: T) -> bool
    …

enchanting map<K, V>
  get_or = (clave: K, por_defecto: V) -> V
    …

enchanting array<T>          -- la longitud N es implícita en C++
  first = -> T
    @[0]
```

Reglas:

- El destino se parsea como **(nombre, argumentos de tipo)**. Los argumentos
  son sigilos declarados por el propio bloque: `vector<T>` introduce `T`,
  igual que `rune Box<T>`.
- `string`, `int`, `double`, `bool`, `char`, `size_t`, … → patrón sin
  argumentos (los tipos primitivos del lenguaje).
- `vector<T>`, `deque<T>`, `list<T>`, `forward_list<T>`, `span<T>`,
  `array<T>`, `optional<T>`, `bitset<T>`… → un argumento de tipo.
- `map<K, V>`, `unordered_map<K, V>`, `pair<A, B>` → dos argumentos.
- `tuple<A, B>`, `tuple<A, B, C>`, … → **aridad variable**: el bloque se
  registra para tuples de exactamente N elementos (1 ≤ N ≤ 8) y se emite con
  `template <typename A, typename B, …>`. Un método para tuples de 2 no se
  aplica a tuples de 3: son entradas distintas del registro.
- `array<T>` acepta **un** sigilo aunque el tipo real tenga dos parámetros
  (`T` y `N`): la longitud se emite como `std::size_t N` implícito en la
  plantilla de C++ (ver §3.4 y decisión D3).
- `enchanting string<T>` → error de aridad (E0711).
- No se puede enhechizar un sigilo ni un puntero (`ref<T>`, `raw<T>`); sí
  `unique<T>`/`shared<T>` en una fase posterior (D5).

### 3.2 Registro: `EnchantedType`

Nuevo en `src/semantic/type_env.ts`:

```ts
export interface EnchantedMethod {
  readonly info: MethodInfo;
  readonly realm: string;   // realm que lo declara (para codegen y LSP)
}

export interface EnchantedType {
  readonly base: string;              // "string", "vector", "map"…
  readonly sigils: readonly string[]; // ["T"] / ["K","V"]
  readonly methods: ReadonlyMap<string, readonly EnchantedMethod[]>;
}

export interface TypeEnv {
  // …
  readonly enchants: Map<string, EnchantedType>; // clave: `${base}/${arity}`
}
```

- La clave es `base/aridad` (`string/0`, `vector/1`, `map/2`, `tuple/2`,
  `tuple/3`): la aridad sale de los sigilos del bloque. Así `tuple<A,B>` y
  `tuple<A,B,C>` conviven y una llamada elige por el número de elementos del
  receptor.
- Se puebla en `register_enchanting` (mismo sitio que hoy) cuando el destino
  **no** es rune/omen/alias pero **sí** es un tipo incorporado conocido
  (`is_primitive_type`, `STRING_TYPES`, `BUILTIN_CONTAINERS`).
- Los nombres de realm se guardan para emitir la llamada cualificada.
- `merge_realm_envs` (`src/project/module_graph.ts:82`) fusiona `enchants` de
  los archivos de un mismo realm, igual que hoy hace con runes y aliases.
- Visibilidad entre módulos: `ExternalImports` gana `enchants`
  (`src/semantic/external.ts`). Un módulo ve los enhechizamientos de **sus
  imports directos**, como cualquier otro símbolo.
- Duplicados: el mismo método (mismo nombre y misma firma) declarado dos veces
  en el mismo realm → **E0707** `«string.compare» ya está enhechizado en este
  realm`. Dos imports que declaren la misma firma y ninguno sea el propio
  módulo → **E0708** al usarlo (ambigüedad), no al importar: solo molesta si se
  llama.

### 3.3 Checker

1. `check_enchanting` construye `self_type`:
   - patrón sin argumentos → `resolve_named_type(base)`
     (`string` → `primitive("string")`, `int` → `INT`…).
   - patrón con sigilos → `named(base, sigilos.map(generic_type))`.
   El cuerpo se comprueba con `with_sigils(...)` y `self_type` igual que un
   método de rune. `@` es el valor receptor.
2. `infer_member(obj, nombre)` gana un paso **antes** de la tabla incorporada
   y **después** de runas/alias/omens/echo del módulo propio:

   ```text
   1. rune / alias / omen / echo del módulo propio (como hoy)
   2. enchants del módulo propio
   3. enchants de los imports directos (si hay más de un candidato → E0708)
   4. tablas incorporadas (member_of_builtin)
   5. error desconocido
   ```

   El paso 4 sigue existiendo: los métodos cableados son el **respaldo** para
   proyectos que no importan `std/string`; lo enhechizado tiene prioridad
   (D2).
3. **Unificación del receptor:** `named("vector", [int])` contra el patrón
   `vector<T>` produce `{ T: int }`; con eso se sustituyen `params` y `result`
   antes de devolver `function_type(...)`. Se reutiliza `unify_sigils` y
   `substitute_generics` de `src/semantic/checker_generics.ts`.
4. **Sobrecargas:** por nombre pueden existir varias firmas (C++20 tiene
   `compare(string)`, `compare(string, size_t)`…). Resolución:
   - filtrar por aridad (respetando `required` y `variadic`);
   - filtrar por `can_assign` argumento a argumento;
   - si queda una → esa; si quedan varias y una coincide **exactamente** con
     los tipos → esa; si no → **E0708** `«compare» es ambiguo para «string»:
     hay N sobrecargas compatibles`.
   - si no queda ninguna → E0501 con el candidato más cercano y su firma.
5. **Receptor `mut`:** un método `mut` exige receptor mutable. Se reutiliza
   `check_mut_receiver` (`src/semantic/checker_call.ts:703`): binding `mut`, o
   `ref`/`shared`/`unique`/`raw`. En tipos por valor (`int`, `double`, `bool`,
   `char`, omens, sellos) `mut` no tiene sentido → **E0710**
   `«int» es un tipo por valor: un método «mut» no puede modificar el receptor`.
6. **Anotación para codegen:** `CheckContext` gana
   `member_targets: Map<ExprNode, { realm: string; name: string }>` (mismo
   patrón que `types`). `infer_member` registra ahí el método elegido; el
   codegen lo consulta para cualificar la llamada.
7. **`@` como lvalue:** `ref(@)` dentro de un método de tipo incorporado debe
   ser legal (el receptor es `const T&` o `T&` en C++). `ref(@)` en un método
   `mut` produce `T&`. Esto ya funciona en sellos; se añade el caso a las
   pruebas.
8. **Ownership:** `ref(@)`, `mut @` y préstamos del receptor siguen las reglas
   de F7 sin cambios: `@` cuenta como variable raíz del método.

### 3.4 Codegen

No se puede añadir métodos a `std::string`, así que se emiten **funciones
libres** en el `namespace` del realm, reutilizando `emit_free_methods`:

```cpp
namespace string {

int compare(const std::string& self, const std::string& other) { … }

std::string trim(const std::string& self) { … }

void append(std::string& self, const std::string& suffix) { … }   // mut

} // namespace string
```

Detalles:

- Receptor: `const T&` si el método no es `mut`, `T&` si lo es. `g.self_expression
  = "self"` mientras se emite el cuerpo (ya implementado para `echo`).
- Patrones genéricos emiten plantilla:

  ```cpp
  template <typename T>
  bool contains(const std::vector<T>& self, const T& value) { … }

  template <typename T, std::size_t N>
  T first(const std::array<T, N>& self) { … }
  ```

  `array` añade el parámetro `N` aunque el patrón solo declare `T` (D3).
  `map<K, V>` → `template <typename K, typename V>`.
- Llamada: `xs.contains(3)` se emite como
  `vector::contains(xs, 3)` usando la anotación `member_targets`. Sin la
  anotación el codegen no sabe en qué realm vive el método (el tipo receptor es
  `std::vector<int>`, que no lleva realm).
- Nombres: `cpp_identifier` para el método; el realm pasa por
  `sanitize_namespace` (ya evita `time`, `random`, `assert`, y `main`). Hay que
  añadir a la lista los que choquen con cabeceras/`std` (`string`, `vector`,
  `map`… son válidos como `namespace`, pero se comprueba uno a uno en G3).
- Sin cambios en la tabla `BUILTIN_FUNCTIONS`: los métodos enhechizados no son
  intrínsecos; si un método necesita C++, se apoya en un `declare` del propio
  módulo (que sí va por `BUILTIN_FUNCTIONS`), exactamente como hace
  `std/io.pengu`.
- El tope de 250 líneas se mantiene: la emisión nueva vive en
  `src/codegen/cpp_enchant.ts`, no dentro de `cpp_decl.ts`.

### 3.5 Biblioteca estándar (contenido de G4)

Cada archivo declara el realm, unos pocos `declare` y los métodos en
PenguScript. Esbozo de `std/string.pengu`:

```pengu
realm string

invoke "std/io"

-- Intrínsecos: la parte que solo C++ puede hacer.
declare compare_raw = (a: ref<string>, b: ref<string>) -> int
declare find_raw = (a: ref<string>, b: ref<string>) -> size_t
declare length_raw = (a: ref<string>) -> size_t

enchanting string
  compare = (otro: string) -> int
    compare_raw(ref(@), ref(otro))

  length = -> size_t
    length_raw(ref(@))

  starts_with = (prefijo: string) -> bool
    length_raw(ref(prefijo)) <= length_raw(ref(@)) && compare_raw(ref(@[0..<#prefijo]), ref(prefijo)) == 0

  trim = -> string
    -- implementado con indexación y substr, sin intrínsecos nuevos
    …
```

Superficie mínima por tipo (se amplía en fases posteriores sin tocar el
compilador):

| Tipo | Métodos |
| --- | --- |
| `string` | `compare`, `starts_with`, `ends_with`, `find`, `contains`, `replace`, `trim`, `to_upper`, `to_lower`, `split`, `repeat`, `is_empty`, `substr`, `to_int`/`to_double` (vía `try_from`) |
| `vector<T>` | `contains`, `index_of`, `first`, `last`, `push`, `pop`, `remove_at`, `insert_at`, `reverse`, `sort`, `join` |
| `array<T>` | `contains`, `first`, `last`, `reverse`, `index_of` |
| `map<K,V>` | `get_or`, `contains_key`, `keys_list`, `values_list`, `remove`, `insert_or_replace` |
| `set<T>` | `contains`, `add`, `remove`, `intersection`, `union` |
| `optional<T>` | `value_or`, `is_some`, `is_none`, `map`, `filter`, `or_else` |
| `int` / `double` | `abs`, `min`, `max`, `clamp`, `to_string`, `is_even`, `sign` |
| `pair<A,B>` | `first`, `second`, `swap`, `to_tuple` |
| `tuple<A,B>` (y de 3 elementos) | `first`, `last`, `len`, `swap`, `to_pair` (solo 2) |
| `Ordering` | `is_lt`, `is_eq`, `is_gt`, `reverse`, `then` |

Los métodos marcados `mut` (`push`, `pop`, `sort`, `reverse` sobre vector,
`add`/`remove` sobre set) necesitan receptor mutable y siguen el contrato `mut`
de F7.

### 3.6 Errores nuevos

| Código | Nombre | Cuándo |
| --- | --- | --- |
| E0707 | `enchant_duplicate` | Misma firma enhechizada dos veces en el mismo realm. |
| E0708 | `ambiguous_method` | Varias sobrecargas compatibles y ninguna exacta, o dos imports con la misma firma. |
| E0709 | `unknown_enchant_target` | Destino que no es incorporado ni declarado (mensaje con sugerencias). |
| E0710 | `invalid_mut_receiver` | Método `mut` sobre un tipo por valor. |
| E0711 | `enchant_arity` | `vector` con 2 sigilos, `string` con 1, `map` con 1… |

Se añaden a `src/diagnostics/codes.ts`, a `docs/errors.md` y al test
`tests/docs.test.ts` que verifica la cobertura.

---

## 4. Matriz de conformidad

| Caso | Hoy | Objetivo | Fase |
| --- | --- | --- | --- |
| `enchanting string` con método | E0502 | compila y se llama | G1–G3 |
| `enchanting vector<T>` | error de sintaxis/registro | compila, `T` unificado | G1–G3 |
| `enchanting map<K,V>` | — | compila | G1–G3 |
| `enchanting array<T>` | — | compila, `N` implícito | G3 |
| `enchanting tuple<A, B>` | — | compila | G1–G3 |
| `enchanting tuple<A, B, C>` | — | convive con el de 2 | G1–G3 |
| `tuple` de 3 con método de 2 | — | “no tiene el miembro” | G2 |
| `enchanting int` con `mut` | — | E0710 | G2 |
| sobrecarga `compare/1` y `compare/2` | — | elige por tipos | G2 |
| dos imports con la misma firma | — | E0708 al llamar | G2 |
| método enhechizado que pisa a uno incorporado (`substr`) | — | gana el enhechizado | G2 |
| método `mut` sobre `vector` con binding inmutable | — | E0406 | G2 |
| `ref(@)` dentro del método | — | compila | G2 |
| LSP: hover/completion de un método de `std/string` | no aparece | aparece | G5 |
| formateador sobre `enchanting string` | no lo conoce | idempotente | G1 |

---

## 5. Fases

Cada fase termina con `bunx tsc --noEmit`, `bun test`, `pengu fmt --check` y
los 13 ejemplos en verde. No se avanza con rojo.

### G1 — Sintaxis y registro (sin cambiar comportamiento)

- Parser: el destino es nombre + sigilos (la gramática ya lo permitía para
  runes: `enchanting vector<T>`, `enchanting map<K, V>`, `enchanting array<T>`,
  `enchanting tuple<A, B>`); se formaliza con `EnchantingDecl.target_arity` y
  se valida que `target_span` cubra el patrón completo.
- `register_enchanting` acepta primitivos y contenedores; E0709/E0711.
- `TypeEnv.enchants`, `merge_realm_envs` y `ExternalImports.enchants`
  (registro sin consultas todavía).
- Formateador idempotente sobre los nuevos destinos.
- Tests: parser (4 formas), registro (aridad, destino inválido), duplicado
  E0707, `fmt` round-trip.
- Aceptación: nada de lo existente cambia de comportamiento; las tablas
  incorporadas siguen mandando porque el checker aún no consulta `enchants`.

### G2 — Checker

- `self_type` y `@` para tipos incorporados; `with_sigils`.
- `infer_member`: orden nuevo (propio → imports → incorporado).
- Unificación del receptor y sustitución de `params`/`result`.
- Sobrecargas y ambigüedad (E0708); `mut` (E0710).
- `member_targets` en `CheckContext` (anotación para G3 y LSP).
- Tests: `enchanting string` con cuerpo real, `vector<T>`, sobrecarga,
  ambigüedad entre dos imports, prioridad sobre `substr`, `mut`/E0406,
  `ref(@)`.

### G3 — Codegen

- Nuevo `src/codegen/cpp_enchant.ts`: emite funciones libres (plantillas si
  hay sigilos), receptor `const T&`/`T&`, `array` con `N` implícito,
  `self_expression`.
- `emit_member_call` consulta `member_targets` y emite `realm::metodo(obj, …)`.
- `emit_declarations` recorre `enchanting_decl` de tipos incorporados.
- Tests e2e: llamadas sobre `string`, `vector<int>`, `map<string,int>`,
  `array<int,3>`; método `mut` sobre vector con binding `mut`; llamada desde
  otro módulo.

### G4 — Biblioteca estándar

- `std/string.pengu`, `std/vector.pengu`, `std/array.pengu`,
  `std/map.pengu`, `std/set.pengu`, `std/optional.pengu`, `std/pair.pengu`,
  `std/tuple.pengu` (bloques para tuples de 2 y de 3), `std/int.pengu`,
  `std/double.pengu`, `std/ordering.pengu`.
- Intrínsecos mínimos por archivo, mapeados en `BUILTIN_FUNCTIONS` y en
  `runtime_source.ts`.
- Tests por archivo: cada método tiene al menos un caso positivo y uno
  negativo cuando aplica.
- Aceptación: `examples/14_strings` (nuevo) usa al menos 10 métodos sin tocar
  el compilador.

### G5 — Herramientas y documentación

- LSP: hover con firma del método enhechizado, autocompletado sobre receptores
  incorporados, `documentSymbol` para los bloques `enchanting`.
- `docs/errors.md` con E0707–E0711; `docs/cheatsheet.md` nueva sección
  «Enchanting de tipos incorporados»; `docs/stdlib.md` con la tabla de §3.5.
- `pengu check --json` sin cambios de formato.

### G6 — Conformidad y cierre

- Un caso en `tests/conformance/` por forma (string, vector, map, array,
  pair, tuple de 2 y de 3, sobrecarga, mut, ambigüedad).
- Suite completa en verde (195 actuales + nuevos), 13 ejemplos + el 14,
  `pengu fmt --check`, `tsc`.
- Bitácora y CHANGELOG (todo bajo `## [0.1.0]`).
- Opcional si el usuario lo aprueba: migrar las tablas incorporadas de
  `string` y `vector` a `std/` y dejar la tabla solo como respaldo.

---

## 6. Compatibilidad (qué NO se rompe)

- Las tablas incorporadas se quedan: sin `invoke "std/string"`, `s.substr(0,2)`
  sigue funcionando como hoy.
- `enchanting` sobre runes/omens/`echo`/`seal` no cambia en G1–G3; el único
  cambio es que el destino puede ser un patrón de tipo y que `infer_member`
  mira una tabla más.
- `MethodInfo` no cambia de forma; las sobrecargas se guardan en una lista
  **alrededor** (`EnchantedMethod[]`), así que runes y sellos siguen con su
  mapa de un método por nombre.
- El ABI interno de C++ no cambia para el código existente: los métodos de
  runes siguen dentro del `struct`; solo los incorporados pasan a funciones
  libres, y eso no toca el código ya compilado.
- La caché sigue siendo válida: la clave ya incluye el código C++ generado.

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Ambigüedad de sobrecargas al estilo C++ (conversiones implícitas) | Preferir coincidencia exacta; error explícito en vez de elegir “la primera”. |
| `namespace string` / `map` choca con algo en C++ | Probar cada nombre en G3; lista de reservados ampliable. |
| Plantilla con receptor `T&` y `const T&` a la vez | Un método es `mut` o no; nunca ambos; test por cada forma. |
| Método enhechizado pisa uno incorporado y cambia semántica | Precedencia documentada (D2) y tests de ambos caminos. |
| `@` no es lvalue en tipos por valor | `mut` prohibido en tipos por valor (E0710). |
| Duplicados entre dos imports | E0708 solo al usar el método; no rompe el import. |
| Archivos de codegen creciendo | Emisión nueva aislada en `cpp_enchant.ts` (tope 250 líneas). |

---

## 8. Decisiones que necesitan tu visto bueno

- **D1. ¿Import explícito o preludio?** **Aceptado: import explícito.** Todos
  los `invoke` de todos los tipos son explícitos; no hay preludio automático ni
  cajas negras. El programador ve exactamente qué módulo aporta cada método.
- **D2. Precedencia.** Propongo que **lo enhechizado gane** a la tabla
  incorporada, y que la tabla quede como respaldo. Es lo único que permite que
  `std/string` arregle o amplíe `substr` sin duplicar métodos.
- **D3. `array<T>` con `N` implícito.** Propongo que el patrón declare solo
  `T` y que el codegen añada `std::size_t N`; los const-parámetros genéricos
  (`array<T, N>` con `N` usable en firmas) quedan para una fase posterior.
- **D4. `mut` solo en tipos por referencia.** Propongo E0710 para `int`,
  `double`, `bool`, `char`, omens y sellos.
- **D5. Punteros.** Propongo dejar `unique<T>`/`shared<T>` para después de G6
  (el auto-deref ya funciona para leer, pero el receptor `mut` necesita más
  cuidado) y prohibir `raw<T>`/`ref<T>` como destino.
- **D6. `tuple`.** **Aceptado: `tuple` entra en esta ronda.** Se registra por
  aridad (`tuple/2`, `tuple/3`, …) y conviven sin ambigüedad; `pair<A,B>` sigue
  incluido.
- **D7. Sobrecargas también en runes.** Propongo no tocarlas ahora; el
  mecanismo de listas queda listo para reutilizarlo cuando lo pidas.
- **D8. Nombres de realm de `std`.** Propongo `string`, `vector`, `map`, `set`,
  `array`, `optional`, `int`, `double`, `ordering` (coherente con `math`,
  `fs`…), con `sanitize_namespace` ampliado si alguno choca.

---

## 9. Orden recomendado

G1 → G2 → G3 con **un** método de prueba (`string.compare`) antes de escribir
toda la biblioteca; ahí se validan sintaxis, resolución y codegen con el caso
más simple. Después G4 (biblioteca), G5 (herramientas y docs) y G6 (conformidad
y cierre). El corte natural para revisar es el final de G3: si `compare`
funciona de punta a punta, el resto es contenido.

---

## 10. Bitácora

| Fecha | Fase | Resumen | Pruebas |
| --- | --- | --- | --- |
| 2026-11-21 | G0 | Plan escrito y aprobado (D1–D8); `tuple` añadido a G1–G6. | 195/195 (punto de partida) |
| 2026-11-21 | G1 | `TypeEnv.enchants` por `base/aridad`, tabla `enchant_targets.ts` (primitivos, string, contenedores, `pair`, `tuple` 1–8), registro con E0707/E0709/E0710/E0711, fusión entre archivos del mismo realm y por imports (`external.enchants`), `self_type` y sigilos en `check_enchanting`. | 204/204 (22 archivos) |
