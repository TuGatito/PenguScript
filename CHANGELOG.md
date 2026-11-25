# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí. El formato
sigue [Keep a Changelog](https://keepachangelog.com/es/1.0.0/) y el proyecto usa
[versionado semántico](https://semver.org/lang/es/).

## Backend JavaScript: andamiaje (P0 de `plan_codegen_js.md`)

- **`--target <cpp|js>`** en `build`, `run` y `check` (por defecto `cpp`, así
  que nada cambia para quien no lo pase). Un backend desconocido se rechaza con
  `backend desconocido «wasm»; los disponibles son cpp y js`.
- **Backend JS seleccionable pero aún sin emisión**: `compile_js_file` analiza
  el programa con el mismo frontend y checker que C++ (mismos diagnósticos) y,
  si está limpio, responde con `E0807` explicando que falta la emisión y cómo
  seguir con `--target cpp`. `pengu run --target js` usa `js_runner.ts`
  (`bun` o, si no está, `node`).
- **Módulos nuevos**: `driver/target.ts` (selección de backend),
  `driver/compile_js.ts` (esqueleto del driver JS), `driver/js_runner.ts`,
  `codegen/js_types.ts` (tabla de tipos `PenguType`→JS, `needs_clone`,
  `--int64`), `codegen/js_names.ts` (identificadores, alias, nombres de archivo
  y literales) y `codegen/js_context.ts` (contexto de emisión por realm con
  archivos, imports, ámbitos y nombres temporales).
- **Nuevos diagnósticos**: `E0516 await_outside_async`, `E0517
  async_not_allowed`, `E0606 borrow_across_await`, `E0804
  async_unsupported_target`, `E0806 target_invalid`, `E0807
  js_target_unsupported`, `E0808 js_intrinsic_missing` y `E0809
  js_emit_failed`, documentados en `docs/errors.md`.
- **`ProgramUnit.external`**: el análisis ahora entrega a los backends los
  `ExternalImports` que ya usaba el checker (`modules`/`selective`/`enchants`),
  necesario para resolver métodos de `enchanting` importados.
- **Bugs reparados por el camino**: `-o <ruta>` guardaba `true` en `out` (el
  valor se perdía y el binario no se copiaba de la caché); `--release` y
  `--emit-cpp` estaban documentados en `help` pero no implementados;
  `CompileOptions.keep_cpp` era código muerto.
- **Tests nuevos**: `tests/codegen/js_types.test.ts`, `js_names.test.ts`,
  `tests/driver/target.test.ts`, `tests/cli/args.test.ts`,
  `tests/cli/js_target.test.ts` y `tests/cli/build_out.test.ts` (este último
  compila de verdad y ejecuta el binario para cubrir la regresión de `-o`).
- Verificado: `bun test` **547 pass / 0 fail** (1586 expect, 85 archivos);
  `bunx tsc --noEmit` limpio; `pengu fmt --check` «89 archivo(s) ya
  formateados»; y a mano `build --release --emit-cpp`, `build -o`, `run
  --target js`, `size --target js` y `check --target js`.

## Bindings C: documentación y cierre (F7 de `plan_bindings.md`)

- **`docs/ffi.md` nuevo**: referencia completa de los enlaces con C —qué es un
  `.d.pengu`, tabla keyword → uso → C++ generado, reglas de ABI (runes, arrays,
  uniones `meld`, enums, bitfields, callbacks y agregados anónimos), punteros y
  buffers con `std/ffi`, variádicas, flujo de `pengu bindgen` con raylib y
  raygui, y catálogo de diagnósticos E0301/E0712–E0715.
- **`docs/cheatsheet.md`**: la sección de C pasa a «Interoperabilidad con C»,
  con el flujo de `bindgen` (generar, importar, `--check`) y la referencia a
  `docs/ffi.md`.
- **`README.md`**: enlaces documentados, `bindings/` en la estructura del
  repositorio y `docs/ffi.md` en la lista de documentación.
- **`--check` anota la plataforma**: el archivo generado lleva
  `-- Plataforma: linux x64 (LP64)` y `bindgen --check` avisa cuando el
  archivo se generó en otra plataforma (D7).
- Verificado: `bun test` **497 pass / 0 fail / 1392 expect / 79 archivos**
  (516 s); `bunx tsc --noEmit` limpio; `pengu fmt --check` «89 archivo(s) ya
  formateados»; `embed_std --check` y `gen_stdlib_docs --check` al día;
  `bindings/raylib` y `bindings/raygui` regenerados y al día.

## Bindings C: validación raylib y raygui (F6 de `plan_bindings.md`)

- **Enlaces comprometidos**: `bindings/raylib/raylib.d.pengu` (619 funciones,
  40 constantes) y `bindings/raygui/raygui.d.pengu` (61 funciones `Gui*`, 6
  constantes) viven en el repositorio y se regeneran con `pengu bindgen`.
- **`pengu bindgen --check`**: regenera en memoria y falla si el archivo no
  existe o está desactualizado; no escribe nada.
- **`--base cabecera.h`**: reutiliza otra cabecera al generar. Sus tipos se
  cualifican con `--base-realm` (`raylib::Rectangle`) y el archivo generado
  hace `invoke "<--base-module>"`; así `raygui.d.pengu` no duplica los tipos
  ni las constantes de raylib y ambos módulos se pueden importar juntos.
- **`link "biblioteca"` en el archivo generado** cuando se pasa `--link`, de
  modo que `pengu run` enlaza sin banderas extra.
- **Ejemplos**: `17_raylib` (ventana, `Fade`, `DrawText`, `DrawCircle`) y
  `18_raygui` (botones y etiquetas con raygui) usan los enlaces; necesitan
  sesión gráfica, así que la suite solo comprueba que compilan y enlazan.
- Regresiones: `tests/bindgen/abi.test.ts` (unión con `void*`, bitfields y
  arrays: `sizeof`/`alignof`/`offsetof` contra C++ y cruce por valor),
  `tests/bindgen/committed.test.ts` (`--check` al día y desactualizado),
  `tests/bindgen/raylib_e2e.test.ts` (enlaces comprometidos con `Fade`,
  `CheckCollisionPointRec` y `GetRandomValue`) y
  `tests/bindgen/native_examples.test.ts`.

## Bindings C: buffers y `std/ffi` (F5 de `plan_bindings.md`)

- **`std/ffi.pengu` nuevo**: rune `CString { datos: vector<char> }` (cadena
  terminada en NUL) con `mut ptr` (`raw<char>`), `text`, `len`, `capacity`,
  `is_empty`, `mut clear`, `mut set` y `to_string`; libres `cstring(texto,
  capacidad = 0)` para crear el buffer, y `read(ptr)` / `write(ptr, texto)`
  para punteros sueltos. Los accesos por puntero van dentro de `unsafe`.
- **`char*` escribible → `raw<char>`** en bindgen (`const char*` sigue siendo
  `string`): las funciones que escriben en un buffer, como `TextCopy` de
  raylib o las de raygui, se pueden llamar con `buffer.ptr()`.
- **Runtime**: `cstring_ptr`, `cstring_text`, `cstring_read`,
  `cstring_write` y `cstring_from_text`, con `#include <cstring>`.
- Regresiones: `tests/bindgen/buffers.test.ts` (fixture C que rellena y copia
  en `char*`, ABI real; y `TextCopy` de raylib escribiendo en un `CString`) y
  `tests/std/ffi.test.ts` (crear, leer, escribir y limpiar).

## Bindings C: constantes y macros (F4 de `plan_bindings.md`)

- **`pengu bindgen` traduce también las macros constantes**. Lee
  `clang -E -dM` y clasifica las macros de objeto: enteros (`int` o
  `int64_t` según el rango y el signo), decimales (`double`, incluidos
  `PI`, `DEG2RAD` y `RAD2DEG` mediante un evaluador decimal que resuelve
  referencias a otras macros), texto, caracteres, inicializadores compuestos
  como `CLITERAL(Color){200, 200, 200, 255}` (se emiten como `const Color`) y
  alias de variantes de un `omen` (`MOUSE_LEFT_BUTTON = 0`).
- **Se omiten con motivo**: macros de función, macros del compilador o de la
  plataforma (`_*`, `PLATFORM_*`, `__*`), nombres que son keyword de
  PenguScript, nombres ya emitidos por un `omen` y expresiones que no son
  constantes. El informe de `pengu bindgen` cuenta funciones y constantes.
- **Resultado medido**: `raylib.h` → 619 funciones y 40 constantes (26
  colores, versión mayor/menor/parche, `PI`, `DEG2RAD`, `RAD2DEG` y seis alias
  de enums); `raygui.h` → 680 funciones y 46 constantes. Los dos `.d.pengu`
  generados pasan `pengu check`.
- Regresiones: `tests/bindgen/macros.test.ts` cubre las seis clases de macro
  (entero, negativo, grande, decimal, expresión decimal, texto, carácter,
  color y alias de enum) contra un fixture C real y contra `raylib.h`.

## Bindings C: bindgen de tipos (F3 de `plan_bindings.md`)

- **La cabecera completa**, no solo las funciones: `pengu bindgen` emite
  `omen` para los enums (valores explícitos e implícitos; los anónimos
  heredan el nombre de su `typedef`), `rune` para los structs, `meld` para las
  uniones, `bits N campo: Tipo` para los bitfields, `echo` para los typedefs y
  `opaque` para los records incompletos.
- **Orden topológico** (`src/bindgen/records.ts`): un record se emite después
  de los tipos que usa su cuerpo; los ciclos por valor se detectan y se
  omiten con motivo. Los campos resuelven alias al tipo final y un record con
  un campo no traducible se omite entero para no romper el layout.
- **Resolución de tipos** (`src/bindgen/native_types.ts`): `array<T, N>` para
  arrays, `raw<T>` para punteros, `string` para `char*` y `raw<void>` para
  callbacks y punteros desconocidos. Los typedefs de función se reportan como
  callbacks y sus parámetros en las funciones cruzan como `raw<void>`.
- **Enums de C como enteros**: un valor `omen` unitario encaja donde se espera
  un entero (como en C) y el codegen inserta `static_cast<T>` en los
  argumentos de `extern`, lo que hace usable `SetConfigFlags(unsigned int)`.
- **`meld` y `std::hash`**: las uniones se hashean por bytes (no hay miembro
  activo conocido), requisito para meter un record con unión en un `map`.
- **Layout verificado**: las 35 records de `raylib.h` coinciden con C en
  tamaño, alineación y los 202 desplazamientos comprobados (0 discrepancias);
  `raylib.d.pengu` genera 619 funciones y solo reporta los 6 typedefs de
  callback. Conexión y llamadas reales (`Fade`, `CheckCollisionRecs`) probadas
  contra raylib 6.2.
- Regresiones: `tests/bindgen/types.test.ts` (ABI con struct anidado, unión,
  enum con saltos, alias, arrays y bitfields; `pengu size` = C) y
  `tests/bindgen/raylib_layout.test.ts` (9 tipos reales con tamaño,
  alineación y offsets iguales a C).

## Bindings C: lenguaje `.d.pengu` v2 (F2 de `plan_bindings.md`)

- **Seis construcciones nuevas** para escribir cabeceras C sin trucos:
  `link "m"` (biblioteca que el módulo necesita, transitiva y normalizada a
  `-lm`), `define NOMBRE = valor` (`inline constexpr`), `opaque Nombre`
  (`struct Nombre;`, solo usable detrás de `raw<T>`/`ref<T>`),
  `callback Nombre = (params) -> ret` (`using Nombre = R (*)(params);`),
  `meld Nombre` (unión C) y `bits N campo: Tipo` dentro de un `rune`
  (bitfield C++).
- **`meld`**: se crea vacío (`Bits()`) y se escribe el campo activo; leer un
  campo exige `unsafe` (E0714). Solo admite tipos triviales (E0713), sin
  valores por defecto ni `bits`. El constructor de cero argumentos es
  exclusivo de las uniones.
- **`bits`**: exige un tipo entero y `1 <= ancho <= bits del tipo` (E0712);
  el sondeo de `pengu size` emite `BITS` en vez de `offsetof` (que no compila
  sobre bitfields) y `--fields` muestra `bits N`. El LSP muestra el ancho en
  el hover.
- **Checker**: `reject_opaque_by_value` (E0715) en campos, parámetros,
  retornos, constantes, locales, callbacks y `extern`; `define` debe ser
  evaluable en compilación; los argumentos de `extern`/`declare` ya marcan
  `variadic` cuando la firma lo pide.
- **Driver**: las bibliotecas de `link` de todos los módulos se suman a las
  de la línea de órdenes antes de compilar y entran en la clave de caché.
- Regresiones: `tests/bindgen/meld.test.ts` (ABI con una unión C y E0714),
  `tests/bindgen/bits.test.ts` (ABI con bitfields, E0712 y `pengu size`),
  `tests/bindgen/decls.test.ts` (opacos, callbacks, `define` y `link "m"`).
- Documentado en `docs/cheatsheet.md` («Declaring C types and libraries», con
  la tabla keyword → uso → C++ generado) y `docs/errors.md` (E0712–E0715).

## Bindings C: coerción de literales (F1 de `plan_bindings.md`)

- Un literal cuyo valor cabe en el destino ya no exige `::from`:
  `Color(255, 0, 0, 255)` con campos `uint8_t`, `Fade(color, 0.5)` con un
  parámetro `float` y `SetWindowState(FLAG)` con `const FLAG: int = 0x40`
  pasan a un parámetro `uint32_t`. Vale para literales enteros, decimales y
  constantes evaluables.
- Se rechazan los valores que no caben (`Color(256, …)`, `-1` a unsigned) y
  las variables siguen necesitando la conversión explícita.
- El checker gana `src/semantic/literal_fit.ts` (`integer_value_of`,
  `literal_fits_type`), usado por argumentos (funciones, métodos y
  constructores de runes) y por las inicializaciones tipadas.
- Regresiones: `tests/checker/literals.test.ts` (9 casos) y
  `tests/bindgen/raylib_literals.test.ts` contra la raylib instalada
  (`Color`, `Fade`, `GetRandomValue`); el fixture de F0 ya no usa `::from`.
- Documentado en `docs/cheatsheet.md` («Literals take the expected type»).

## Bindings C: cimientos del FFI (F0 de `plan_bindings.md`)

- **Un `extern "C"` que devuelve `string` ya compila.** El prototipo se emite
  como `const char*` y la conversión ocurre en el punto de llamada
  (`::pengu::from_c_string`, que convierte un puntero nulo en cadena vacía);
  desaparece la sobrecarga `inline` que era ilegal en C++ por diferir solo en
  el tipo de retorno (G1).
- Los argumentos `string` de una función nativa cruzan como `const char*` con
  `::pengu::c_str`, también en las variádicas (G1).
- **`--link raylib` enlaza de verdad**: un nombre suelto se normaliza a
  `-lraylib` en el driver, las rutas (`libfoo.a`, `/ruta/foo.o`) se respetan y
  `--link -lm` ya no se traga la bandera (G8).
- **bindgen** sufija con `_` los parámetros que son palabras reservadas de
  PenguScript (`SetWindowState(flags)` → `flags_: uint32_t`) y mapea los
  enteros de C a tipos de ancho fijo LP64 (`unsigned int` → `uint32_t`,
  `long` → `int64_t`, `unsigned long long` → `uint64_t`) para que no aparezcan
  tipos de dos palabras en las firmas (G2, G4 parcial).
- Si el nombre de una función C es palabra reservada, bindgen la omite con el
  motivo en el reporte: renombrarla rompería el símbolo del enlazador.
- `pengu bindgen -I <dir>` ahora pasa de verdad los directorios de includes a
  clang (antes se anunciaba en la ayuda y se ignoraban), y `pengu help` de
  `build`/`run`/`bindgen` documenta `--link`.
- Nuevas regresiones: `tests/bindgen/extern_string.test.ts`,
  `tests/bindgen/native_types.test.ts` (struct por valor, enum y `uint64_t`
  contra C real) y `tests/cli/link.test.ts`.
- Verificación: `bun test` **462 pruebas en 65 archivos**; `tsc --noEmit`
  limpio; `pengu fmt --check` sin cambios.

### Verificación final del LSP (F6 de `plan_lsp_errores.md`)

- Binario y `.vsix` reinstalados. La sonda JSON-RPC sobre los archivos del
  informe (y sobre el resto de `std/` y `examples/`) da **0 diagnósticos**
  tanto ejecutada desde el repositorio (usa el `std/` del proyecto) como desde
  un directorio sin proyecto (usa la std empotrada).
- `pengu doctor` en el repositorio confirma que la huella del proyecto y la del
  binario coinciden; en un proyecto con un `std/` distinto avisa con la orden
  de reinstalar.
- `bun test`: **456 pruebas en 62 archivos**; `tsc --noEmit` limpio;
  `pengu fmt --check` sin cambios; `embed_std.ts --check` y
  `gen_stdlib_docs.ts --check` al día.
- README: receta de diagnóstico para «el LSP marca lo que el CLI no ve».

### Higiene de diagnósticos y guía de desajustes (F5 de `plan_lsp_errores.md`)

- Retirados `E0002 manifest_missing` y `E0003 manifest_invalid`: el manifiesto
  es opcional y ningún camino del compilador los emitía, así que solo
  confundían al leer el catálogo.
- `docs/errors.md`: nueva sección «Cuando el LSP marca errores que el CLI no
  ve», con el orden de comprobación (stdlib distinta → `pengu doctor`, raíz
  distinta → `pengu.toml`, binario viejo, buffer sin guardar).
- `editors/vscode/README.md`: el mismo diagnóstico desde el editor, con la
  orden de reinstalar y recargar la ventana.

### LSP: raíz del workspace (F4 de `plan_lsp_errores.md`)

- El servidor de lenguaje usa `rootUri` (o `workspaceFolders`) como raíz del
  proyecto: las importaciones absolutas se resuelven contra el workspace y no
  contra el directorio del archivo abierto. Sin raíz explícita se mantiene el
  comportamiento anterior (deducirla del archivo).
- Si el `std/` del proyecto no coincide con el del compilador, el servidor
  envía un único `window/showMessage` con las dos huellas y la orden para
  reinstalar, en vez de publicar diagnósticos que solo existen por ese
  desajuste.
- Nuevo `src/lsp/workspace.ts`; `AnalyzeOptions.root`, `LoadOptions.root`,
  `ProjectOptions.root` y `ProjectState.root`. Regresiones en
  `tests/lsp/root.test.ts` y `docs/lsp.md` actualizado.

### Identidad del compilador (F3 de `plan_lsp_errores.md`)

- `src/project/std_bundle.ts` (generado) exporta `STD_FINGERPRINT` y
  `STD_FILE_COUNT`: sha256 sobre rutas y contenido de `std/`, estable entre el
  script de empaquetado y el binario. `scripts/embed_std.ts --check` falla si
  la std cambió sin regenerar el paquete.
- `pengu doctor` deja de responder lo mismo para cualquier binario: muestra la
  huella de la std empotrada, la raíz del proyecto y si su `std/` coincide
  (con el aviso de reinstalar cuando no). `--json` está implementado de
  verdad, con la misma información en forma de datos.
- Nuevo `src/cli/doctor_command.ts`; regresiones en `tests/cli/doctor.test.ts`.

### Proyecto real en el repositorio (F2 de `plan_lsp_errores.md`)

- **`pengu.toml` en la raíz** (nuevo): el repositorio es un proyecto, así que
  su `std/` es la biblioteca que usan el compilador y el LSP, en lugar de la
  copia empotrada en el binario instalado. Sin él, la raíz era el directorio
  del archivo abierto y `invoke "std/char"` caía en la std del binario (vieja),
  que es lo que producía los errores fantasma del LSP.
- `docs/cheatsheet.md` y `README.md`: la raíz del proyecto es el directorio con
  `pengu.toml` (opcional para archivos sueltos), orden de resolución
  `foo.pengu` → `foo.d.pengu` → `foo/index.pengu`, y el `std/` del proyecto
  gana al empotrado.
- Regresiones en `tests/project/root.test.ts`, incluida una que exige que el
  repositorio conserve su manifiesto.
- Binario y `.vsix` reconstruidos e instalados: la sonda LSP sobre los cuatro
  archivos del informe pasa de 28 diagnósticos a 0.

### LSP: importaciones `std/` inexistentes (F1 de `plan_lsp_errores.md`)

- Una importación `std/…` que no resuelve ya no se ignora en silencio: se
  reporta `E0301 no se encuentra el módulo` con las rutas buscadas, igual que
  cualquier otro módulo. Antes el grafo se saltaba el módulo y el usuario solo
  veía errores de miembros («el tipo «char» no tiene el miembro «is_space»»),
  que apuntaban al sitio equivocado.
- Regresiones nuevas en `tests/project/imports.test.ts`.

### Biblioteca estándar: F9 (documentación)

- **`scripts/gen_stdlib_docs.ts`** (nuevo): genera `docs/stdlib_api.md` desde el
  parser real — runes con campos y constructor, enchantings con firmas,
  funciones con valores por defecto, omens con variantes e intrínsecos. El
  modo `--check` falla si el documento no está al día y la suite lo comprueba
  (`tests/std/docs.test.ts`).
- **`README.md`**: sección «Recetas» con tres programas completos (física,
  CLI con flags y JSON, tiro parabólico) verificados con `pengu run`.
- **`docs/stdlib.md`**: enlace a la referencia generada y módulos previstos
  ajustados a 0.2.0.
- `version` sigue en `0.1.0`: la 0.1.0 se publica cuando termine la fase F9
  (documentación, extensión y `.vsix`).

#### Corregido en F9

- **`!` de prefijo** negaba mal: el parser solo reconocía `not valor`, así que
  `if !opciones.is_ok()` producía `E0403 «__error__»` y rompía el bloque
  siguiente. Ahora `!` en posición de prefijo es negación booleana (el `!` de
  sufijo sigue siendo el desarrollo del opcional). Pruebas en
  `tests/checker/checker.test.ts`.
- **`docs/cheatsheet.md`** citaba `std/fmt`, que no existe: ahora dice
  `std/format`.

### Biblioteca estándar: F8 (avanzados)

- **`std/file.pengu`** (nuevo): rune `File` sobre un manejador nativo con
  `open`, `create`, `append`, `read_line`, `read_all`, `write`, `write_line`,
  `flush`, `is_eof`, `close`, `path` y `mode`; libres `read_text`,
  `write_text` y `append_text`. Los errores se devuelven como `T?`/`bool`.
- **`std/process.pengu`** (nuevo): `run` (código de salida), `status`,
  `output` (captura la salida estándar) y `exit`.
- **`std/crypto.pengu`** (nuevo): `sha256` y `sha256_hex` con una
  implementación propia en el runtime (vectores conocidos verificados).
- Estudio de los módulos restantes en la bitácora del plan: `std/thread`,
  `std/channel`, `std/net` y `std/regex` se aplazan a 0.2.0 porque necesitan
  garantías de concurrencia, red o un motor de expresiones que 0.1.0 no debe
  prometer; `std/debug` se reduce a lo que ya cubre `std/assert`.
- `tests/std/advanced.test.ts` (nuevo): archivos con manejador, procesos,
  SHA-256 y una herramienta de huellas que lee un archivo y lo verifica.

#### Corregido en F8

- **Importaciones selectivas con alias**: `invoke {sqrt as raiz} from "std/math"`
  ahora emite la llamada al símbolo real (`std::sqrt`), no `math::raiz`; dos
  `invoke {…} from "mismo/módulo"` se acumulan en lugar de perder el segundo.
  Las tablas de intrínsecos viven en `src/codegen/builtins_emit.ts` para que el
  emisor de valores y el de llamadas las consulten sin ciclos de imports.
- `process::run` devuelve el código de salida del programa (antes el estado
  en bruto de `std::system`).
- El helper de lectura por líneas escapa correctamente `\n` y `\r` en el
  runtime embebido.

### Biblioteca estándar: F7 (datos y CLI)

- **`std/encoding.pengu`** (nuevo): `base64`, `base64_decode`, `base64_bytes`,
  `base64_to_bytes`, `hex`, `hex_decode`, `hex_bytes`, `hex_to_bytes`,
  `url_encode`, `url_decode`, `bytes`, `from_bytes` e `is_utf8`, con soporte
  UTF-8 real (no solo ASCII).
- **`std/hash.pengu`** (nuevo): `fnv1a32`, `fnv1a64`, `djb2`, `crc32`,
  `adler32`, `hex32`, `hex64` y las variantes `*_hex`; los valores coinciden con
  las referencias públicas (FNV, CRC-32, Adler-32).
- **`std/cli.pengu`** (nuevo): runes `Flag` y `Parsed`, constructores `flag`,
  `option`, `short_flag`, `short_option`, `parse` y `usage`. Acepta
  `--nombre=valor`, `--nombre valor`, `-n valor`, `-n=valor`, `--`, posicionales
  y falla con mensajes claros en opciones desconocidas o sin valor.
- **`std/console.pengu`** (nuevo): estilos ANSI, colores de 4, 8 y 24 bits,
  `paint*`, `strip`, limpieza de pantalla y control del cursor.
- **`std/json.pengu`** (nuevo): `Value` recursivo (`Null`, `Bool`, `Number`,
  `Text`, `Array`, `Object`), constructores, accesos, `stringify`, `pretty` y un
  analizador completo con escapes y pares sustitutos `\uXXXX`; `parse` y
  `error` informan del motivo y la posición.
- `tests/std/data.test.ts` (nuevo): codificación, huellas de referencia, CLI,
  consola, JSON de ida y vuelta y una herramienta de aceptación que combina
  banderas, archivo y JSON.
- Nuevo ejemplo `examples/16_herramienta`: una herramienta de línea de comandos
  que lee banderas con `std/cli`, calcula una huella con `std/hash` y escribe un
  documento JSON con `std/json`.

#### Corregido en F7

- El `else` de un `match` usado como sentencia se ejecutaba siempre: ahora se
  emite solo si ninguna variante coincidió (afectaba a `get`/`pretty` de JSON).
- Las variantes nulas de un `omen` algebraico se emiten como valor
  (`Value::Null()`); antes se emitía el nombre de la función estática.
- Los `omen` recursivos se declaran antes de sus variantes, así que
  `Array(vector<Value>)` compila.
- `to_string` del runtime distingue `int8_t`/`uint8_t` de `char` y el formato
  de números usa `format::fixed`.

### Biblioteca estándar: F6 (juegos)

- **`std/geometry.pengu`** (nuevo): runes `Vec2`, `Vec3`, `Rect` y
  `Transform2D` con operadores (`+`, `-`, `*`, `/`, `==`, `<=>`), productos
  escalar y vectorial, normalización, rotación, distancias, intersecciones y
  transformaciones afines 2D.
- **`std/easing.pengu`** (nuevo): curvas `linear`, `smoothstep`, `smootherstep`,
  `ping_pong`, `steps` y las familias `quadratic`, `cubic`, `quartic`,
  `quintic`, `sine`, `exponential`, `circular`, `back`, `bounce` y `elastic`
  con variantes `in`, `out` e `in_out`.
- **`std/noise.pengu`** (nuevo): `value_1d`, `value_2d`, `signed_2d`,
  `fractal_2d`, `turbulence_2d` y `ridged_2d`, deterministas por semilla.
- **`std/color.pengu`** (nuevo): rune `Color` con conversiones a `#RRGGBB`/
  `#RRGGBBAA`, `lerp`, `luminance`, `inverted`, `to_hsv` y constructores
  `rgb`, `rgba`, `from_rgb8`, `from_hex` y `from_hsv`.
- **`std/physics.pengu`** (nuevo): rune `Body` con gravedad, impulsos,
  amortiguación, integración y rebotes en suelo y paredes; `step` es funcional
  (`cuerpo = physics::step(cuerpo, gravedad, 0.0, 0.016)`).
- Nuevos ejemplos `examples/14_geometria` (rectángulos, intersecciones y
  transformaciones) y `examples/15_juego` (bucle con gravedad, rebote, easing
  y color).

#### Corregido en F6

- Los métodos de un rune importado se emiten como miembros (`Rect.contains`,
  `Color.to_hex`) en vez de caer en el miembro incorporado del mismo nombre.
- `pengu size` mide también las constantes: el sondeo de tamaños emite solo las
  constantes (sin cuerpos de funciones), así que las cachés siguen siendo
  estables y `sizeof` de cada valor existe.

### Biblioteca estándar: F5 (algoritmos)

- **`std/iter.pengu`** (nuevo): `map`, `filter`, `fold`, `count_if`, `any`,
  `all`, `none_of`, `find`, `position`, `zip`, `enumerate`, `take`, `skip`,
  `chain` y `flatten`, genéricos y con los sigilos explícitos.
- **`std/sort.pengu`** (nuevo): `insertion_sort`, `is_sorted`,
  `binary_search_sorted` y `sorted_copy`; funcionan con `vector<T>` y con
  runes que declaren `operator <=>`.
- **`std/result.pengu`** (nuevo): rune `Result<T, E>` con `is_ok`, `is_err`,
  `value`, `value_or`, `error`, `error_or`, `expect` y `to_string`; libres
  `ok`, `err`, `map`, `map_err`, `and_then` y `from_optional`.
- **`std/test.pengu`** (nuevo): `is_true`, `is_false`, `equal`, `not_equal`,
  `is_some` e `is_none`.
- Los tipos de módulos importados se pueden nombrar cualificados
  (`result::Result<int, string>`, `time::Duration`) y el checker sugiere el
  nombre completo cuando falta el alias.

#### Corregido en F5

- Los constructores de runes genéricos conservan sus argumentos de tipo
  (`Caja<int>(valor)`), y las llamadas a genéricos importados sustituyen sus
  sigilos (`iter::map<int, string>`).
- `mut items: ref<vector<T>>` se emite como `T&` (antes `const T&`), se puede
  indexar un `ref<secuencia>` y `f(mut ref(xs))` valida la variable prestada.
- Una función puede devolver un tipo cualificado con argumentos
  (`-> result::Result<int, string>`), que antes se confundía con una
  expresión.

### Biblioteca estándar: F4 (sistema)

- **`std/fs.pengu`**: `read_to_string`, `read_bytes`, `write_string`,
  `write_bytes`, `append_string`, `append_line`, `read_lines`, `write_lines`,
  `exists`, `is_file`, `is_dir`, `remove`, `remove_if_exists`, `create_dir`,
  `ensure_dir`, `list_dir`, `file_size`, `rename`, `copy`, `canonicalize`,
  `read_or` y `write_new`.
- **`std/path.pengu`** (nuevo): `separator`, `is_absolute`, `join`,
  `join_all`, `file_name`, `extension`, `stem`, `parent_dir`,
  `with_extension`, `normalize` y `components`.
- **`std/time.pengu`**: runes `Duration`, `Instant` y `DateTime` con
  aritmética, comparación, `Display` y conversiones; `duration_from_*`,
  `instant_now`, `datetime_now` y los intrínsecos de reloj.
- **`std/random.pengu`**: `seed`, `seed_from_time`, `float_range`, `chance`,
  `int_range` y los miembros `shuffle()`/`choose()` en secuencias.
- **`std/os.pengu`**: `args`, `get_env`, `set_env`, `env_or`, `has_env`,
  `pid`, `home_dir`, `temp_dir`, `current_dir`, `platform`, `arch` y
  `cpu_count`.
- **`std/io.pengu`**: `read_all`, `flush`, `is_terminal`, `read_char` y
  `read_line_trimmed`.

#### Corregido en F4

- Los runes declarados en un módulo importado ya resuelven campos, métodos,
  operadores, `<=>` y `Display` (nuevo `src/semantic/rune_lookup.ts`).
- El runtime imprime cualquier rune que declare `to_string` mediante una
  sobrecarga restringida de `::pengu::to_string`.
- Los milisegundos de `std/time` usan `int64_t`: `int` es de 32 bits en
  PenguScript y truncaba las fechas.
- `path::with_extension` conserva el directorio de la ruta original.

## [0.1.0] - 2026-11-20

Primera versión funcional del *toolchain* completo, escrita en TypeScript y
ejecutada con Bun. La versión del lenguaje que documenta `docs/cheatsheet.md`
es la 0.2.0; la del compilador y sus herramientas es la 0.1.0.

### Añadido

- **Compilador a C++20**: lexer con bloques por indentación, parser con AST
  inmutable, checker de tipos, resolución de módulos, análisis de posesión v1
  (`unique`/`shared`/`weak`, `ref`, `mut` y uso tras movimiento) y generación de
  C++20 por *realm* con runtime propio (`pengu_rt.hpp`).
- **CLI `pengu`** con los comandos `run`, `build`, `check`, `fmt`, `lsp`,
  `bindgen`, `init`, `clean` y `doctor`; caché de compilación por contenido y
  enlace de objetos nativos (`--link`).
- **Servidor LSP** por stdio sin dependencias: diagnósticos, *hover* con tipos
  inferidos, autocompletado, ir a la definición, símbolos de documento y
  formateo.
- **Formateador** idempotente: indentación de 2 espacios, espaciado de
  operadores, comentarios y líneas en blanco, genéricos y `operator`.
- **`pengu bindgen`**: lee el AST JSON de `clang++` y genera módulos
  `*.d.pengu` con `extern "C"`, incluidas conversiones `string` ↔ `const char*`.
- **Biblioteca estándar inicial** en `std/` con el nuevo bloque `declare`:
  `math`, `fs`, `time`, `random`, `os` y `assert`; `io`, `format` y `log` son
  intrínsecas hasta que el lenguaje soporte variádicas.
- **Soportes del lenguaje** incorporados en esta versión: `switch`/`match` con
  exhaustividad, `break` con valor, bucles con `else`, comprensiones de vector,
  mapa y conjunto, omens unitarios, flags y algebraicos, `echo`/`seal`,
  `enchanting` con operadores, cierres, genéricos con `needs` y módulos con
  `invoke` selectivo y alias.
- **Extensión de VS Code** en `editors/vscode`: gramática TextMate,
  configuración del lenguaje y cliente LSP.
- **Ejemplos** de `examples/01_hello` a `examples/12_colecciones`, todos
  compilables y ejecutables, más fixtures de bindgen nativo.
- **Scripts de instalación** en `scripts/`: `install.sh`/`install.ps1` compilan
  con Bun y dejan `pengu` en el PATH sin editar perfiles de shell;
  `vsix.sh`/`vsix.ps1` empaquetan e instalan la extensión.
- **Documentación**: `README.md` reescrito, `docs/stdlib.md` con el estado de la
  implementación y plan escalable en `scratch/plan_typescript.md`.

### Añadido en las fases G1–G6

- **`enchanting` sobre tipos incorporados**: un bloque `enchanting string`,
  `enchanting vector<T>`, `enchanting map<K, V>` o `enchanting tuple<A, B>`
  añade métodos a un tipo de la biblioteca sin tocar el compilador. Los
  métodos se registran por tipo base y aridad, admiten sobrecargas, respetan
  `mut` solo en tipos por referencia y se resuelven en este orden: propios,
  importados y, por último, la tabla nativa. Se añadieron los códigos E0707
  (firma duplicada), E0708 (ambigüedad entre módulos), E0709 (destino
  desconocido), E0710 (`mut` sobre un tipo por valor) y E0711 (aridad del
  patrón).
- **Biblioteca de colecciones en `std/`**: `std/string`, `std/vector`,
  `std/array`, `std/map`, `std/set`, `std/optional`, `std/pair`, `std/tuple`
  (pares y ternas), `std/int`, `std/double` y `std/ordering`. Cada módulo se
  importa explícitamente; sin el `invoke` los métodos no existen.
- **Codegen de métodos enhechizados**: funciones libres cualificadas por
  realm, `realm::metodo(receptor, ...)`, `std::get<N>` para tuplas y
  parámetros genéricos no deducidos con `std::type_identity_t` para permitir
  conversiones como `or_else(size_t?, 0)`.
- **LSP**: *hover* con la firma del método enhechizado y su realm,
  autocompletado de miembros tras `.` sobre receptores incorporados y
  `documentSymbol` para los bloques `enchanting`.
- **Documentación**: sección «Enchanting built-in types» en
  `docs/cheatsheet.md`, tabla de módulos enhechizados en `docs/stdlib.md` y
  `docs/errors.md` con E0707–E0711.
- **Pruebas**: `tests/regression/g2.test.ts` (resolución, sobrecargas, `mut`,
  ambigüedad), `tests/regression/g4.test.ts` (los once módulos de colecciones)
  y seis casos de conformidad nuevos (`g1_string` … `g6_ambiguedad`).

### Cambiado

- El proyecto pasa de la implementación anterior en Python a TypeScript + Bun,
  con estilo `snake_case`, sin clases y módulos pequeños.
- `docs/cheatsheet.md` actualizado a la versión 0.2.0 del lenguaje.

### Eliminado

- La implementación anterior en Python (`src/penguscript/`, `pyproject.toml`,
  `uv.lock` y sus pruebas).

Cobertura completa del lenguaje documentado en `docs/cheatsheet.md` (0.2.0):
las fases F1–F9 del plan `scratch/plan_compiler_completo.md`, sin deuda
técnica conocida en el compilador.

### Añadido en las fases F1–F9

- **Funciones variádicas** `(...xs: T)` con *spread* `f(...xs)`, tipo
  `function<(...T) -> R>` y `any` empaquetado en `::pengu::Value`; `stdio`,
  `format` y `log` pasan a escribirse en PenguScript sobre `declare`.
- **Tipos compuestos**: `array<T,N>`, literales con prefijo de tipo
  (`vector<int>[...]`, `set<T>{...}`, `map<K,V>{...}`), `pair`/`tuple`,
  `stack`, `queue`, `priority_queue`, `bitset`, `list`, `forward_list`,
  `multiset`, `unordered_*`, `span`, `variant`, `any`, `init_list`, `complex`,
  `atomic`, `mutex`, `shared_mutex`, `condition_variable` y `thread`.
- **Genéricos completos**: sigilos en funciones, runes, omens, `echo` y `seal`,
  instanciación explícita (`Caja<int>(7)`, `Resultado<int>::Ok(5)`) e
  inferencia, y restricciones `needs` comprobadas (E0513).
- **Runes**: herencia con `parent(...)`, `virtual` cuando hay herederos,
  *upcast* explícito `ref<Animal>(ref(d))`, operadores de usuario (`[]`, `+=`,
  unarios, `()`, `<=>`, libres por ADL) y `enchanting` sobre omens y sellos.
- **Memoria**: Ley de Exclusividad con préstamos por ámbito (E0602), contrato
  `mut` en la llamada (E0406), movimiento por campo e índice (E0601) y `unsafe`
  obligatorio para `raw`, `static mut`, `get_unchecked` y llamadas `unsafe`
  (E0603).
- **Módulos**: `const` evaluable en compilación (`constexpr`), `static mut` como
  variable de módulo (E0308 si no es evaluable), realms reabiertos con símbolos
  fusionados (E0304 al duplicar tipos) e importación por nombre de realm.
- **Diagnósticos**: conversiones numéricas portables y `T::try_from`/`T::from`,
  `Ordering` con `<=>`, mensajes con sugerencia de nombre y arreglo para la
  indentación, y `Display` obligatorio en interpolaciones y variádicas `any`.
- **CLI**: `pengu run`, `build` y `check` sin argumentos usan el `entry` del
  `pengu.toml` del proyecto; `check --json` escribe siempre en stdout y un
  archivo ausente aparece como E0005 en el propio JSON.
- **Herramientas**: `pengu check --json`, `docs/errors.md` con el catálogo de
  códigos y banco de conformidad en `tests/conformance/`.

### Cambiado en las fases F1–F9

- `checker_expr.ts` y `cpp_expr.ts` se dividieron en módulos por
  responsabilidad (llamadas, control y operadores) para mantener los archivos
  legibles.
- El nombre con que se importa un módulo es el de su **realm** salvo que se
  escriba `as`.

### Corregido en las fases F1–F9

- BOM UTF-8 que rompía `invoke`, `static mut`, `mut ref<T>`, `array<T,N>`,
  `function<Sig>`, `if ... then` con bloque y la aridad con argumentos por
  defecto.

### Añadido en la fase E (extensión de VS Code)

- Extensión completa en `editors/vscode/`: gramática para todo el lenguaje
  (palabras clave, tipos primitivos, contenedores, cadenas, ancho fijo,
  `declare`, `Ordering`, operadores y `...`), configuración de lenguaje con
  `wordPattern` y reglas de sangría, y 49 snippets validados por el parser.
- Comandos para ejecutar, compilar, verificar y formatear el archivo actual,
  ejecutar el proyecto, `bindgen`, `init`, `doctor`, reiniciar el servidor y
  configurar el ejecutable; menús del editor y del explorador, atajos
  `Ctrl+Alt+R/B/K`, terminal dedicada, barra de estado y canal de salida.
- Tareas `"type": "pengu"` con el *problem matcher* `$pengu`, verificación
  opcional al guardar (`pengu.check.onSave`) y reinicio automático del LSP al
  cambiar `pengu.executable` o la traza.
- Pruebas de la extensión en `tests/extension/` (36 pruebas) que comparan la
  gramática con las tablas del compilador, parsean los snippets y validan el
  manifiesto, las tareas y los módulos, y una prueba de humo que activa la
  extensión con un `vscode` simulado.
- `match` admite `else` al final, como documenta el *cheatsheet*.

### Añadido en las fases H1–H7

- **Rangos como valores**: `range<T>` se anota, se pasa, se devuelve, se mide
  con `#`, se prueba con `in` y se recorre con `for`.
- **`std/memory.pengu`**: `unique<T>` y `shared<T>` ganan `get` y `mut set`;
  `weak<T>` gana `is_alive`.
- **`std/string`**: `get(i) -> char?` y `mut pop() -> char?`.
- **`std/set`**: `intersection`, `difference`, `symmetric_difference` e
  `is_subset`.
- **Hash sintetizado** para runes y sellos, de modo que pueden usarse como
  claves de `unordered_map`/`unordered_set`.
- **Banco de conformidad H1–H6** en `tests/conformance/` (21 casos).

### Cambiado en las fases H1–H7

- La herencia usa **despacho estático**: ya no se emite `virtual`. Así lo
  documenta el lenguaje y así lo muestran `examples/11_polimorfismo` y las
  pruebas de F6.
- A partir de `operator <=>` se derivan `<`, `>`, `<=` y `>=`.
- `pengu bindgen` ya enlaza funciones C variádicas.

### Corregido en las fases H1–H7

- `any` no se puede convertir con `as` (E0514) ni `mut`/`unsafe` son valores de
  primera clase (E0515).
- Un índice fuera de rango imprime `panic: índice 5 fuera de rango (tamaño 2)`
  y termina con código 1 en lugar de abortar sin mensaje.
- `@ = valor` funciona en métodos `mut`; un método `mut` sobre un temporal da
  E0406.
- Un `return` dentro de un `for`/`while` usado como sentencia sale de la
  función (antes salía de una lambda).
- La interpolación evalúa sus partes de izquierda a derecha.
- `for k, v in mapa` liga la clave y el valor (antes ligaba un índice entero).
- El formateador escribe `ref<set<T>>` pegado y `#@ then` con espacio.
- `map{}` sin argumentos de tipo funciona cuando el contexto lo anota.

### Añadido en las fases I1–I8 (IntelliSense y tamaños)

- **Análisis de proyecto en el LSP**: el servidor reconstruye el grafo completo
  (documento abierto, sus `invoke` y `std/`) con *overlays* de los buffers sin
  guardar, publica diagnósticos por archivo y comparte un índice de símbolos.
- **Autocompletado completo**: ámbitos con sombreado, miembros de runes
  (heredados), omens, sellos, ecos, tipos incorporados y métodos enhechizados
  de `std/` y de módulos propios; `::` ofrece variantes y exportaciones; tras
  `:` y `->` se ofrecen tipos del proyecto, `vector<T>`, `map<K, V>` y `T?`.
- **Hover y ayuda de firma**: firma, documentación extraída de los comentarios
  `--`, contenedor, tamaño y desplazamiento de campos; `signatureHelp` marca el
  parámetro activo, también en variádicas.
- **Navegación y refactor**: definición de locales, parámetros, campos, métodos
  y símbolos de `std/`; referencias y renombrado por proyecto con sombreado;
  `prepareRename`; `std/` protegido contra renombrado; símbolos jerárquicos del
  documento y símbolos del workspace.
- **`pengu size`**: mide bytes y alineación reales compilando un programa de
  sondeo con el mismo toolchain (`--json`, `--type`, `--fields`). Cubre tipos
  primitivos, runes, omens, sellos, ecos, constantes y funciones (retorno +
  parámetros, y tamaño de `std::function`). La tabla se cachea por contenido y
  nunca inventa cifras: sin compilador informa y falla.
- **Inlay hints** de tipos inferidos (`x = 1` → `: int`) con opción de añadir el
  tamaño; **tokens semánticos**, **plegado** y **acciones de código**
  (arreglos rápidos y «añadir tipo explícito»).
- **Extensión**: ajustes `pengu.inlayHints.types`, `pengu.inlayHints.sizes`,
  `pengu.completion.docs` y `pengu.statusBar.size`, barra de estado con el
  tamaño del símbolo bajo el cursor y comando «Mostrar tamaño del símbolo».

### Corregido en las fases I1–I8

- La extensión encuentra `pengu` aunque VS Code no herede el `PATH` del shell:
  busca en el `PATH` del proceso y en `~/.local/bin`, `~/.bun/bin`, `~/bin`,
  `/usr/local/bin`, `/opt/homebrew/bin` y `/usr/bin`, y usa la ruta absoluta
  para la terminal, las tareas, los diagnósticos y el LSP. El aviso de
  ejecutable ausente explica el problema, abre los ajustes y muestra los
  directorios consultados en la salida.

- El autocompletado de miembros ya no pierde los métodos enhechizados del
  módulo propio y calcula bien el receptor con un prefijo a medio escribir.
- La finalización de `string` incluye `compare`, `trim`, `split`… y los
  métodos enhechizados aparecen primero.
- Los símbolos de función llevan su tipo `function<…>`, lo que habilita la
  ayuda de firma y el hover con firma.
- Los tokens semánticos usan el formato de cinco enteros por token exigido por
  el protocolo.
- La biblioteca estándar viaja **dentro** del ejecutable (`src/project/std_bundle.ts`,
  generado por `scripts/embed_std.ts`): antes, un binario instalado fuera del
  repositorio calculaba mal `std/` y, con ello, el LSP no veía `trim`, `join`,
  `sort`… aunque `bun run` sí. `bun run build` regenera el paquete y una prueba
  verifica que no quede desactualizado.
- El cliente LSP 11 de la extensión usa `LogOutputChannel` y toma `Trace` de
  `vscode-jsonrpc`; sin eso, el arranque del servidor fallaba con un mensaje
  engañoso («no respondió a `--version`»).
- La medición de tamaños cualifica los tipos de cada realm y omite `void`.

### Rendimiento del LSP (fases L1–L6)

- **Sincronización incremental de verdad**: `src/lsp/sync.ts` aplica cada
  `contentChanges[].range` sobre el texto actual. Antes el servidor anunciaba
  cambios incrementales pero reemplazaba el documento por el último fragmento.
- **Análisis agrupado**: una ráfaga de teclas espera 120 ms y produce un solo
  análisis y una sola publicación; `didSave` analiza de inmediato.
- **Diagnósticos por diferencia**: cada archivo tiene una huella; si su lista
  no cambió, no se reenvía (`src/lsp/publish.ts`). Los módulos empotrados
  (`std:…`) no se publican.
- **Sin errores fantasma al escribir**: `E0403`/`E0506` que tocan el tramo
  recién editado se filtran hasta 800 ms después del reposo, cuando se publica
  la lista definitiva.
- **Tamaños que no bloquean**: `src/lsp/sizes_state.ts` mantiene la última
  tabla válida y agenda la medición 400 ms después del último cambio. Hover,
  inlay hints y `pengu/sizeAt` responden al instante; al terminar se pide
  `workspace/inlayHint/refresh`. Nueva petición `pengu/refreshSizes` y
  `pengu/perf` con los tiempos del último análisis/publicación/medición.
- **Sondeo estable**: `generate_program` admite `declarations_only`; el sondeo
  de tamaños ya no incluye cuerpos, así que editar una función no recompila.
- **Caché de parseo** por contenido (hash FNV-1a) en `ParseCache`, compartida
  por el servidor entre pulsaciones.
- **Extensión**: debounce de 250 ms para `pengu/sizeAt` desde la barra de
  estado (`editors/vscode/src/debounce.js`) y ajuste `pengu.hover.sizes`.
- Cifras medidas en `examples/13_enchanting`: hover tras editar 1975 → 10 ms;
  reanálisis 6 ms; la medición de tamaños (1,8 s) pasa a segundo plano.

### Corregido en las fases L1–L6

- El servidor LSP corrompía el documento al recibir cambios incrementales
  (reemplazaba todo el texto por el fragmento insertado).
- El hover compilaba el sondeo C++ dentro de la propia petición (hasta 1975 ms).
- Cada pulsación publicaba los diagnósticos de todos los archivos del proyecto.
- El sondeo de tamaños cambiaba de hash al editar cualquier cuerpo, lo que
  invalidaba la caché y forzaba una compilación de ~1,9 s.

### Biblioteca estándar: F0 (cimientos)

- `emit_member_call` emite el C++ real de `pop` (devuelve `T`),
  `remove_at`, `insert(indice, valor)`, `remove`, `insert_or_assign`,
  `keys`/`values` y `first`/`last`, además de `find` de `string` como
  `optional<size_t>`. Antes generaba métodos que no existen en C++
  (`.remove`, `.keys`, `.first`) o `insert` con un solo argumento.
- Nuevos helpers del runtime `::pengu::pop_back_checked`, `erase_at`,
  `insert_at`, `remove_value`, `remove_from_set`, `map_assign`, `map_keys`,
  `map_values` y `find_opt`, más `to_fixed`, `to_scientific` y `to_radix`.
- `array<T, N>` y `span<T>` rechazan los cambios estructurales (el cheatsheet
  ya lo prometía).
- `std/log` compila: `log` pasa a los reinos reservados y se emite como
  `namespace log_rt` para no chocar con `log()` de `<math.h>`.
- Los métodos `mut` sobre `unique`/`shared` reciben el puntero por `const&`:
  la escritura va por `(*self)`, así que un `shared_ptr` const ya compila.
- Los métodos de un rune admiten argumentos por defecto (`MethodInfo.required`)
  y dos métodos con el mismo nombre son un error E0707 en vez de
  sobrescribirse en silencio.
- `format::fixed(valor, decimales)`, `format::scientific` y
  `format::radix(valor, base)` con precisión y base explícitas.
- Pruebas nuevas: `tests/std/bugs.test.ts` (7 regresiones de la auditoría) y
  `tests/std/modules.test.ts` (los 21 módulos compilan juntos con g++);
  `tests/std/std.test.ts` revisa los `declare` de cualquier archivo de `std/`
  y que todos los módulos se analicen sin diagnósticos.

### Biblioteca estándar: F1 (núcleo numérico)

- `std/math` pasa a `std/math.pengu`: constantes (`pi`, `e`, `tau`, `phi`,
  `sqrt2`, `ln2`, `ln10`), la trigonometría completa (directas e inversas,
  hiperbólicas), `exp*`, `ln`, `log2`, `log10`, `cbrt`, `hypot`, `fmod`,
  `remainder`, `trunc`, `nearbyint`, `fdim`, `fmax`, `fmin`, `copysign`, `fma`,
  `signbit`, `is_finite`, `is_infinite`, `is_nan`, `infinite`,
  `not_a_number`, `gcd` y `lcm`, más utilidades puras para física y juegos
  (`lerp`, `inverse_lerp`, `remap`, `clamp01`, `smoothstep`, `smootherstep`,
  `deg_to_rad`, `rad_to_deg`, `wrap`, `wrap_angle`, `lerp_angle`,
  `move_towards`, `damp`, `approx_eq`, `sign`, `min3`, `max3`, `average`,
  `ipow`, `is_power_of_two`, `next_power_of_two`, `align_up`).
- `std/int` añade `div_floor`, `div_ceil`, `mod_floor`, `mod_euclid`, `pow`,
  `wrap`, `next_multiple_of`, `abs_diff`, `digits`, `is_power_of_two`,
  `between`, `is_positive`, `is_negative`, `is_zero`, `to_float`, `to_int64`,
  `to_size` y `to_radix`.
- `std/double` añade redondeos (`fract`, `round_to`), raíces y exponenciales
  (`sqrt`, `cbrt`, `pow`, `exp`, `ln`, `log2`, `log10`), `hypot`, las
  comprobaciones de `NaN`/infinito, `signum`, `lerp`, `approx_eq`, ángulos
  (`to_radians`, `to_degrees`), texto con precisión (`to_fixed`,
  `to_scientific`) y conversiones seguras.
- Nuevos `std/float` y `std/long_double` con la misma superficie, con las
  primitivas de `<cmath>` declaradas por tipo para conservar el ancho.
- Nuevo `std/integers` (generado por `scripts/gen_integers.ts`): límites y
  métodos para `int8_t`…`uint64_t`. `size_t` y `ptrdiff_t` son alias de
  `uint64_t`/`int64_t` en LP64 y se convierten con `as`.
- Nuevo `std/char`: clasificación ASCII (`is_digit`, `is_alpha`,
  `is_alphanumeric`, `is_space`, `is_upper`, `is_lower`, `is_ascii`,
  `is_hex_digit`, `is_control`, `is_punctuation`), `code`, `digit_value`,
  `hex_value`, `to_upper` y `to_lower`.
- Correcciones de la fase: `::pengu::try_from_int` ya convierte a los destinos
  de 64 bits sin signo (`size_t::from(1)` paniqueaba siempre); `to_string` de
  `int8_t`/`uint8_t` los imprime como número y no como carácter; los literales
  `char` escapan `\r`, `\v`, `\f`, `\0` y los caracteres de control; las
  llamadas a métodos de `std/integers` con literales `int` ya no son ambiguas
  en C++ (el codegen convierte cada argumento a su tipo de parámetro); el
  formateador conserva `long double` y la resta tras `@`/`#@`.
- Pruebas nuevas: `tests/std/numbers.test.ts` (int, double, float,
  long double, integers y char) y `tests/std/math.test.ts` (constantes,
  utilidades y la aceptación de caída libre con rebote), más casos del
  formateador para nombres compuestos y operadores tras `@`.

### Biblioteca estándar: F2 (contenedores)

- `std/vector` crece hasta la API completa: consulta (`get_or`, `first_or`,
  `last_or`, `min`, `max`, `is_sorted`), mutación (`remove`, `remove_all`,
  `extend`, `retain`, `fill`, `swap`, `rotate_left`, `rotate_right`,
  `transform`, `sort_by`, `dedup`), orden superior (`any`, `all`, `none`,
  `count_if`, `find_if`, `position_if`, `fold`, `map`, `filter`), orden y
  búsqueda (`sorted`, `sorted_by`, `binary_search`) y partes (`take`, `skip`,
  `slice`, `chunks`, `windows`, `enumerate`), además de `sum`/`product`.
- `std/array` añade `to_vector`, `reversed`, `slice`, `join`, `min`, `max`,
  `find_if`, `any`, `all`, `none` (y hereda `sum`/`product`); sigue sin
  permitir cambios de tamaño.
- `std/map` añade `get_or_insert`, `update`, `entries`, `first_key`,
  `last_key`, `merge` y `retain`.
- `std/set` añade `is_superset`, `is_disjoint`, `insert_all`, `remove_all`,
  `extend`, `retain`, `first`, `last`, `map`, `filter` y `to_sorted_vector`.
- `std/optional` añade `map`, `and_then`, `or_else_get`, `zip` y `any`.
- Nuevo `std/deque` con doble extremo (`push_front`, `pop_front`, `insert_at`,
  `remove_at`) más `first`, `last`, `get_or`, `index_of`, `contains`,
  `to_vector` y `join`.
- `std/ordering` añade `to_int` y `then_with`; `std/tuple<A, B, C>` añade
  `first` y `second`.
- Adaptadores: `pop` de `stack`/`queue`/`priority_queue` devuelve el elemento
  (antes era `void`) y `clear` existe en los tres; `sum`/`product` funcionan
  con cualquier secuencia.
- Correcciones de la fase: `for clave, valor in ref(mapa)` itera el mapa y no
  por índice; el receptor de `mut` sobre `shared<T>` es constante; los
  métodos `ref<T>` de un método `mut` se pasan con `ref(x)`.
- Pruebas nuevas: `tests/std/containers.test.ts` (vector en tres bloques,
  array, map, set, optional, deque, adaptadores y bitset, ordering/tuplas y la
  comprobación de que mutar durante `for` sigue siendo `E0602`).

### Biblioteca estándar: F3 (texto)

- `std/string` crece hasta la API completa: búsqueda (`rfind`, `find_from`,
  `count`, `compare_ignore_case`), recorte (`trim_start`, `trim_end`,
  `trim_matches` y sus variantes), caja (`capitalize`, `decapitalize`,
  `title_case`), reemplazo (`replace`, `replace_first`), prefijos y sufijos,
  partes (`split_whitespace`, `split_lines`, `chars`, `bytes`, `char_count`),
  relleno (`pad_start`, `pad_end`, `pad_center` y `_with`), cortes
  (`insert_at`, `remove_range`, `truncate`, `substring`), predicados `is_*`,
  conversiones (`to_int`, `to_double`, `to_bool`) y `escape`/`unescape`.
- Intrínsecos nuevos del runtime: `rfind_raw`, `find_from_raw`,
  `replace_first_raw`, `split_whitespace_raw`, `char_count_raw` (cuenta
  puntos de código UTF-8), `reverse_raw` (invierte sin romper secuencias),
  `parse_int_raw`/`parse_double_raw` (`std::from_chars` con consumo completo)
  y `template_values`.
- `std/format` añade `hex`, `bin`, `oct`, `pad_left`, `pad_right`, `center`
  (y sus variantes `_with`), `join`, `separated` y `template`, que sustituye
  cada `{}` por el siguiente valor.
- `std/log` gana el omen `Level` (`Debug`, `Info`, `Warn`, `Error`) con
  `name()` y `to_int()`, y las funciones `set_level`, `level`, `enabled` y
  `timestamped`; el runtime filtra por nivel (`info` por defecto) y antepone
  `[nivel] [HH:MM:SS]` cuando la marca de tiempo está activa.
- Correcciones de la fase: una llamada variádica con parámetros fijos delante
  (`f(a, ...resto)`) empaquetaba también `a` en el vector; los métodos de un
  omen declarado en un módulo importado ya se resuelven (`log::level().name()`)
  y el codegen los emite cualificados por su realm; un omen importado con
  variantes unitarias implementa `Display`.
- Pruebas nuevas: `tests/std/text.test.ts` (8 casos, incluidos UTF-8, escape
  y niveles de log comprobando `stdout` y `stderr`).

### Verificado

- `bun test`: 482 pruebas en 70 archivos (lexer, parser, checker, formateador,
  LSP de integración, de consultas, de sincronización y de rendimiento,
  medición de tamaños, bindgen, biblioteca estándar, conformidad y e2e de los
  ejemplos, de las fases F1–F9, G1–G6, H1–H7, I1–I8, L1–L6 y de la biblioteca
  estándar (F0–F8), la documentación generada de la stdlib y las importaciones
  selectivas, y de la extensión de VS Code, más las regresiones del plan
  `lsp_errores` (importaciones, raíz del proyecto, doctor y raíz del LSP) y de
  las fases F0–F2 del plan `bindings` (tipos nativos, literales, uniones,
  bitfields, opacos, callbacks, `define` y `link`).
- `tsc --noEmit` sin errores y `pengu fmt --check` sin cambios pendientes.
- Los 15 ejemplos de `examples/` compilan y ejecutan con el compilador final.
