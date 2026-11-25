# Enlaces con C (`.d.pengu` y `pengu bindgen`)

PenguScript no tiene un FFI aparte: un archivo `.d.pengu` es un módulo normal
con las declaraciones que describen una cabecera C, y `pengu bindgen` lo
genera a partir del AST de `clang`. El compilador traduce esas declaraciones a
prototipos `extern "C"` y structs C++ con el mismo layout que C, así que los
programas cruzan llamadas reales contra `-lraylib`, `raygui.o` o cualquier
biblioteca del sistema.

## Qué es un archivo `.d.pengu`

- Es un `.pengu` más: mismo parser, mismo checker, mismos módulos. La
  extensión `.d.pengu` es una convención para separar los enlaces escritos a
  mano de tu código.
- El loader resuelve `invoke "raylib"` con este orden: `raylib.pengu`,
  `raylib.d.pengu`, `raylib/index.pengu`. Un módulo es **un** archivo: no se
  fusionan `.pengu` y `.d.pengu` del mismo nombre.
- La raíz del proyecto es el directorio con `pengu.toml`; desde ahí se
  resuelven las rutas relativas y el `std/` del proyecto.
- `realm raylib` fija el espacio de nombres del C++ generado (`raylib::InitWindow`).

## Las declaraciones

| Keyword | Uso | C++ generado |
|---------|-----|--------------|
| `realm` | `realm raylib` | `namespace raylib { … }` |
| `link` | `link "m"` | añade `-lm` al enlazar el módulo |
| `define` | `define MAX = 8` | `inline constexpr auto MAX = 8;` |
| `const` | `const FLAG: unsigned int = 64` | `inline constexpr unsigned int FLAG = 64;` |
| `opaque` | `opaque Textura` | `struct Textura;` (solo tras `raw<T>`) |
| `callback` | `callback Filtro = (x: int) -> int` | `using Filtro = int (*)(int);` |
| `meld` | `meld Valor` + campos | `union Valor { … };` |
| `bits` | `bits 3 modo: uint32_t` | `std::uint32_t modo : 3;` |
| `rune` | `rune Color` + campos | `struct Color { … };` |
| `omen` | `omen Modo` + variantes | `enum class Modo : int { … };` |
| `echo` | `echo Punto = Vector2` | `using Punto = Vector2;` |
| `extern "C"` | `InitWindow = (w: int, h: int, t: string) -> void` | `extern "C" void InitWindow(int, int, const char*);` |
| `declare` | `sqrt = (x: double) -> double` | intrínseco del runtime (solo `std/`) |

Reglas de las firmas:

- Un parámetro `string` cruza como `const char*` y un retorno `string` se
  convierte con `::pengu::from_c_string` (un `NULL` se lee como cadena vacía).
- `ref<T>` se emite como `T&`; para un parámetro mutable se escribe
  `mut valor: ref<int>` y se llama con `mut ref(x)`.
- `mut` en un `declare` va antes del nombre (`mut datos: ref<vector<char>>`).
- `...resto: any` produce `...`; solo se permiten primitivos y `string`, y se
  aplican las promociones de C (`float` se pasa como `double`).
- `meld` no admite `bits` ni valores por defecto; se construye vacío
  (`Valor()`) y se asigna el campo activo. Leer un campo exige `unsafe`.
- `bits N campo: T` exige un entero y `1 <= N <= ancho de T`. Además
  `pengu size --fields` informa del ancho (`bits 3`) en vez de un
  desplazamiento, porque `offsetof` no es legal sobre un bitfield.

## Reglas de ABI

`tests/bindgen/abi.test.ts` compara `sizeof`, `alignof` y `offsetof` de un
tipo C++ real con lo que mide `pengu size`: unión con `int`/`double`/`void*`,
bitfields y arrays incluidos, y además lo cruza por valor en ambos sentidos.

- **Runes**: struct con los campos en el orden declarado y las mismas reglas
  de alineación que C++ (`pengu size --fields` muestra bytes, alineación y
  desplazamientos).
- **Arrays**: `array<T, N>` es `std::array<T, N>`, con el mismo layout que
  `T[N]`.
- **Uniones (`meld`)**: tamaño del miembro mayor y alineación máxima; el
  miembro activo lo decide el programador, como en C.
- **Enums**: `enum class` con tipo `int` (o `std::uint64_t` con `flags`, o el
  `underlying` indicado). Pasarlos a un parámetro `unsigned int` de un `extern`
  funciona: el codegen inserta el `static_cast`.
- **Bitfields**: el layout es *implementation-defined*; la paridad está
  verificada con GCC/Clang en LP64 (Linux y macOS). MSVC puede empaquetar
  distinto: si tu biblioteca es de Windows, genera y valida allí.
- **`long`**: en LP64 es 64 bits. `pengu bindgen` lo traduce a `int64_t` (y
  `unsigned long` a `uint64_t`) para que cruce igual.
- **Callbacks**: un `typedef` de puntero a función cruza como `raw<void>`.
  No hay trampolines: para pasar un cierre C++ como callback hace falta una
  función C intermedia.
- **Agregados anónimos**: un `struct`/`union` sin nombre dentro de otro tipo no
  se genera; `bindgen` lo reporta y omite el record completo si no puede
  reproducir su layout.
- **Plataforma**: el archivo generado anota `-- Plataforma: linux x64 (LP64)`.
  `--check` avisa si el archivo se generó en otra plataforma.

## Punteros, buffers y `nullptr`

`raw<T>` es un puntero sin comprobaciones: se crea con `raw<T>(ref(x))` o
`nullptr` y se desreferencia dentro de `unsafe`. `ref<T>` en un `extern` es una
referencia C++ (`T&`), con la misma ABI que un puntero.

Un `char*` escribible se traduce a `raw<char>` (`const char*` sigue siendo
`string`). Para pasarlo, crea el buffer con `std/ffi`:

```coffee
invoke "std/ffi"

main = -> void
  buffer = ffi::cstring("", size_t::from(64))
  unsafe
    raylib::TextCopy(buffer.ptr(), "hola desde C")
  io::println(buffer.text())
```

`ffi::CString` guarda un `vector<char>` terminado en NUL, con `ptr()`, `text()`,
`len()`, `capacity()`, `clear()` y `set()`. `ffi::read(ptr)` y
`ffi::write(ptr, texto)` trabajan con punteros sueltos.

## `pengu bindgen`

```bash
pengu bindgen cabecera.h [--out archivo.d.pengu] [--realm nombre] \
  [--link biblioteca] [-I directorio] [-I directorio ...] \
  [--base otra.h --base-realm otro --base-module "../otro/otro.d"] \
  [--clang ruta] [--check]
```

- Traduce funciones, records (structs/uniones/bitfields), enums (también los
  anónimos con `typedef`), typedefs, callbacks y macros constantes.
- `--link raylib` emite `link "raylib"` en el archivo, así que el ejecutable
  enlaza sin banderas extra; `-I` se pasa a clang.
- `--check` regenera en memoria y falla si el archivo no existe, está
  desactualizado o se generó en otra plataforma. No escribe nada.
- `--base` reutiliza otra cabecera: sus tipos se cualifican con
  `--base-realm` (`raylib::Rectangle`) y no se repiten, y el archivo hace
  `invoke "<--base-module>"`.
- El informe final lista funciones, constantes y todo lo omitido con su motivo.

Flujo completo con raylib y raygui:

```bash
pengu bindgen /usr/include/raylib.h --realm raylib --link raylib \
  --out bindings/raylib/raylib.d.pengu

pengu bindgen ../raylib-pengu/include/raygui.h -I ../raylib-pengu/include \
  --base /usr/include/raylib.h --base-realm raylib \
  --base-module ../raylib/raylib.d --realm raygui --link raylib \
  --out bindings/raygui/raygui.d.pengu
```

`examples/17_raylib` abre una ventana con `InitWindow`, `DrawText` y
`DrawCircle`; `examples/18_raygui` usa `GuiButton` y `GuiLabel`. El segundo
necesita el objeto de raygui con su implementación:

```bash
cc -c -DRAYGUI_IMPLEMENTATION -I ../raylib-pengu/include raygui.h -o raygui.o
pengu run examples/18_raygui/main.pengu --link raygui.o
```

`tests/bindgen/committed.test.ts` regenera los enlaces comprometidos y
comprueba que siguen al día; `tests/bindgen/raylib_e2e.test.ts` usa los
enlaces reales (`Fade`, `CheckCollisionPointRec`, `GetRandomValue`).

## Diagnóstico

| Código | Qué significa |
|--------|---------------|
| `E0301` | No se encuentra un módulo `invoke` (revisa la ruta o `pengu.toml`). |
| `E0712` | El ancho de un `bits` no cabe en el tipo. |
| `E0713` | Un campo de `meld` no es trivial, tiene valor por defecto o `bits`. |
| `E0714` | Leer un campo de `meld` fuera de `unsafe`. |
| `E0715` | Un tipo `opaque` se usa por valor (usa `raw<T>`/`ref<T>`). |

Si el LSP y el CLI discrepan, ejecuta `pengu doctor`: compara la stdlib del
proyecto con la del compilador y muestra versión, compiladores y ruta del
proyecto.
