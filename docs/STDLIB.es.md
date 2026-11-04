# La biblioteca estándar de PenguScript

Los 67 módulos de `std/` en `psc` 0.28.7: para qué sirve cada uno, cuándo
usarlo, cuándo usar otro y dónde vive su API generada.

Es el documento *catálogo* del conjunto de documentación:

| Documento | Responde |
| --- | --- |
| [LANGUAGE.es.md](LANGUAGE.es.md) | ¿Cómo escribo esta construcción y en qué se convierte en C? |
| [PENGUNIC.es.md](PENGUNIC.es.md) | ¿Cómo escribo PenguScript seguro, idiomático y rápido? |
| **STDLIB.es.md** (este archivo) | ¿Qué módulo estándar uso y dónde está su API? |

English: [STDLIB.md](STDLIB.md).

Cada módulo enlaza a una página de [`docs/api/`](api/), generada a partir de los
comentarios `##` del propio módulo por `psc doc --include-std`.

<!-- toc -->
- [0. Cómo usar este catálogo](#0-cómo-usar-este-catálogo)
- [1. La forma de la biblioteca estándar](#1-la-forma-de-la-biblioteca-estándar)
- [2. Elegir un módulo por tarea](#2-elegir-un-módulo-por-tarea)
- [3. Núcleo y memoria](#3-núcleo-y-memoria)
  - [`std.spark` — E/S de proceso, conversiones y control](#stdspark-es-de-proceso-conversiones-y-control)
  - [`std.memoria` — bloques crudos del heap](#stdmemoria-bloques-crudos-del-heap)
  - [`std.oracle` — `maybe` y `result`](#stdoracle-maybe-y-result)
  - [`std.builder` — `StringBuilder`](#stdbuilder-stringbuilder)
  - [`std.arena` — asignador bump](#stdarena-asignador-bump)
  - [`std.functor` — funciones con contexto](#stdfunctor-funciones-con-contexto)
  - [`std.sourcemap` — offsets de byte ↔ línea/columna](#stdsourcemap-offsets-de-byte-líneacolumna)
  - [`std.bitset` — conjunto de bits denso de longitud fija](#stdbitset-conjunto-de-bits-denso-de-longitud-fija)
  - [`std.diagnostic` — spans, etiquetas y renderizadores](#stddiagnostic-spans-etiquetas-y-renderizadores)
- [4. Texto y números](#4-texto-y-números)
  - [`std.scrolls` — strings orientados a bytes](#stdscrolls-strings-orientados-a-bytes)
  - [`std.lingua` — UTF-8 sobre codepoints](#stdlingua-utf-8-sobre-codepoints)
  - [`std.littera` — métodos sobre `char`](#stdlittera-métodos-sobre-char)
  - [`std.logica` — métodos sobre `bool`](#stdlogica-métodos-sobre-bool)
  - [`std.integrum` — métodos sobre enteros](#stdintegrum-métodos-sobre-enteros)
  - [`std.fractio` — métodos sobre floats](#stdfractio-métodos-sobre-floats)
  - [`std.numerus` — métodos sobre cualquier número](#stdnumerus-métodos-sobre-cualquier-número)
  - [`std.arithmancy` — vectores, matrices, cuaterniones](#stdarithmancy-vectores-matrices-cuaterniones)
  - [`std.lot` — números pseudoaleatorios](#stdlot-números-pseudoaleatorios)
- [5. Colecciones](#5-colecciones)
  - [`std.loom` — algoritmos de listas, familia segura](#stdloom-algoritmos-de-listas-familia-segura)
  - [`std.tally` — algoritmos de listas, familia concreta](#stdtally-algoritmos-de-listas-familia-concreta)
  - [`std.atlas` — mapas](#stdatlas-mapas)
  - [`std.coven` — conjuntos](#stdcoven-conjuntos)
  - [`std.ordinal` — contenedores sobre CC](#stdordinal-contenedores-sobre-cc)
- [6. Formatos y codificaciones](#6-formatos-y-codificaciones)
  - [`std.json` — JSON estricto (RFC 8259)](#stdjson-json-estricto-rfc-8259)
  - [`std.cipher` — codificaciones y checksums](#stdcipher-codificaciones-y-checksums)
  - [`std.carmen` — registros binarios de formato fijo](#stdcarmen-registros-binarios-de-formato-fijo)
  - [`std.toml` — TOML 1.0](#stdtoml-toml-10)
  - [`std.yaml` — el subconjunto legado de manifiestos](#stdyaml-el-subconjunto-legado-de-manifiestos)
  - [`std.ledger` — CSV y TSV](#stdledger-csv-y-tsv)
  - [`std.compressus` — gzip, zlib, deflate](#stdcompressus-gzip-zlib-deflate)
  - [`std.digest` — SHA-256 y compañía](#stddigest-sha-256-y-compañía)
  - [`std.regulus` — expresiones regulares pequeñas](#stdregulus-expresiones-regulares-pequeñas)
- [7. Sistema, tiempo y diagnósticos](#7-sistema-tiempo-y-diagnósticos)
  - [`std.archivum` — el sistema de archivos](#stdarchivum-el-sistema-de-archivos)
  - [`std.compass` — rutas](#stdcompass-rutas)
  - [`std.rites` — el sistema operativo](#stdrites-el-sistema-operativo)
  - [`std.invoke` — parseo tipado de línea de comandos](#stdinvoke-parseo-tipado-de-línea-de-comandos)
  - [`std.io` — E/S estándar exacta en bytes](#stdio-es-estándar-exacta-en-bytes)
  - [`std.net` — sockets TCP bloqueantes](#stdnet-sockets-tcp-bloqueantes)
  - [`std.chronicle` — relojes y calendarios](#stdchronicle-relojes-y-calendarios)
  - [`std.chrono` — instantes y duraciones (vaqt)](#stdchrono-instantes-y-duraciones-vaqt)
  - [`std.whisper` — logging por niveles](#stdwhisper-logging-por-niveles)
- [8. Testing](#8-testing)
  - [`std.ward` — aserciones para tests y guardas](#stdward-aserciones-para-tests-y-guardas)
  - [`std.trial` — suites y reporte](#stdtrial-suites-y-reporte)
- [9. Concurrencia](#9-concurrencia)
  - [`std.filum` — primitivas de sincronización](#stdfilum-primitivas-de-sincronización)
- [10. Servicios de red](#10-servicios-de-red)
  - [`std.petitio` — cliente HTTP](#stdpetitio-cliente-http)
  - [`std.jsonrpc` — JSON-RPC 2.0](#stdjsonrpc-json-rpc-20)
- [11. Interop y código nativo](#11-interop-y-código-nativo)
  - [`std.ffi` — búferes y strings de C](#stdffi-búferes-y-strings-de-c)
  - [`std.ffi_call` — llamadas dinámicas con libffi (opcional)](#stdffi_call-llamadas-dinámicas-con-libffi-opcional)
  - [`std.dynlib` — carga dinámica de librerías](#stddynlib-carga-dinámica-de-librerías)
  - [`std.secrets` — primitivas de libsodium (opcional)](#stdsecrets-primitivas-de-libsodium-opcional)
- [12. WebAssembly](#12-webassembly)
  - [`std.web` — el puente del navegador](#stdweb-el-puente-del-navegador)
  - [`std.web.js` — interop con JavaScript](#stdwebjs-interop-con-javascript)
  - [`std.web.dom` — elementos y listeners](#stdwebdom-elementos-y-listeners)
  - [`std.web.event` — accesores tipados de eventos](#stdwebevent-accesores-tipados-de-eventos)
  - [`std.web.canvas` — Canvas 2D](#stdwebcanvas-canvas-2d)
  - [`std.web.browser` — APIs de ventana](#stdwebbrowser-apis-de-ventana)
  - [`std.web.location` — `window.location`](#stdweblocation-windowlocation)
  - [`std.web.history` — `window.history`](#stdwebhistory-windowhistory)
  - [`std.web.router` — rutas por hash](#stdwebrouter-rutas-por-hash)
  - [`std.web.http` — `fetch`](#stdwebhttp-fetch)
  - [`std.web.websocket` — cliente WebSocket tipado](#stdwebwebsocket-cliente-websocket-tipado)
  - [`std.web.storage` — localStorage y sessionStorage](#stdwebstorage-localstorage-y-sessionstorage)
  - [`std.web.file` — elegir, leer, descargar](#stdwebfile-elegir-leer-descargar)
  - [`std.web.clipboard` — portapapeles del sistema](#stdwebclipboard-portapapeles-del-sistema)
  - [`std.web.crypto` — criptografía del navegador](#stdwebcrypto-criptografía-del-navegador)
  - [`std.web.url` — parseo y codificación de URL (también nativo)](#stdweburl-parseo-y-codificación-de-url-también-nativo)
  - [`std.web.security` — ayudas defensivas para strings (también nativo)](#stdwebsecurity-ayudas-defensivas-para-strings-también-nativo)
- [13. Dependencias opcionales y nativas](#13-dependencias-opcionales-y-nativas)
  - [Archivos de binding internos](#archivos-de-binding-internos)
- [14. El índice completo](#14-el-índice-completo)
- [Apéndice A — Chuleta de imports](#apéndice-a-chuleta-de-imports)
- [Apéndice B — Propiedad al llamar a la biblioteca estándar](#apéndice-b-propiedad-al-llamar-a-la-biblioteca-estándar)
- [Apéndice C — Convenciones de nombres en la biblioteca estándar](#apéndice-c-convenciones-de-nombres-en-la-biblioteca-estándar)
<!-- /toc -->

Todos los módulos que vienen con `psc` 0.28.7: para qué sirven, cuándo usarlos y
dónde vive la API generada de cada uno.

## 0. Cómo usar este catálogo

La biblioteca estándar está documentada dos veces, a propósito:

| Capa | Responde | Dónde |
| --- | --- | --- |
| **Este catálogo** | ¿Qué módulo uso y por qué? ¿Cuándo *no* debo usarlo? | `docs/STDLIB.md` |
| **API generada** | ¿Cuál es la firma exacta de `scrolls.substring`? | [`docs/api/std_scrolls.md`](api/std_scrolls.md) |

Las páginas generadas las produce `psc doc --include-std` a partir de los
comentarios `##` de `std/*.pengu`; las regenera `tools/docs/gen_api.sh` y CI las
comprueba. Este catálogo es manual y enlaza a ellas.

Cada entrada tiene la misma forma:

```
### `std.name` — una línea
**Úsalo cuando** …
**Evítalo cuando** …
**Destacados** los cinco nombres que más vas a escribir
**API** [enlace a la página generada] · [fuente]
```

**Versión.** Este catálogo describe `psc` 0.28.7 y el árbol `std/` del mismo
commit. La constante de versión de un módulo (`TRIAL_VERSION`, `CARMEN_VERSION`,
…) es la versión propia de su API, no la del compilador.

**Imports.** Los módulos estándar se importan explícitamente:

```pengu
import std.json
import std.scrolls
```

Los módulos `std.*` siempre se resuelven, nunca se copian a `lib/` y el
eliminador de código muerto los poda cuando no se usan: importar un módulo que
no llamas no cuesta nada en el binario. Importa lo que lees.

**Leer una entrada.** "Úsalo cuando" es el caso positivo; "Evítalo cuando" nombra
el módulo que probablemente quieres en su lugar. Cuando un módulo tiene una
dependencia nativa opcional (`libcurl`, `libffi`, `libsodium`, `dl`), la entrada
lo dice.

## 1. La forma de la biblioteca estándar

La biblioteca está por capas: todo descansa sobre un núcleo pequeño y los
módulos especializados nunca arrastran el mundo entero.

```
spark            E/S de proceso, parseo, panic, exit
├── memoria      bloques crudos del heap
├── oracle       maybe / result
├── scrolls      strings (bytes)
│   └── lingua   UTF-8 sobre codepoints
├── builder      StringBuilder
├── arena        asignador bump
├── ordinal      contenedores sobre CC
├── loom/tally   algoritmos de listas
├── atlas/coven  mapas y conjuntos
└── …
```

| Capa | Módulos | La usarás |
| --- | --- | --- |
| Núcleo | `spark`, `memoria`, `oracle`, `builder` | siempre |
| Texto | `scrolls`, `lingua`, `littera`, `logica` | constantemente |
| Números | `integrum`, `fractio`, `numerus`, `arithmancy`, `lot` | a menudo |
| Colecciones | `loom`, `tally`, `atlas`, `coven`, `ordinal`, `bitset` | a menudo |
| Ayudas de memoria | `arena`, `functor` | a veces |
| Formatos | `json`, `cipher`, `carmen`, `toml`, `yaml`, `ledger`, `compressus`, `digest`, `regulus` | a menudo |
| Sistema | `archivum`, `compass`, `rites`, `invoke`, `io`, `net`, `chronicle`, `chrono`, `whisper`, `diagnostic`, `sourcemap`, `dynlib` | a menudo |
| Concurrencia | `filum` | a veces |
| Testing | `ward`, `trial` | en todos los proyectos |
| Interop | `ffi`, `ffi_call`, `dynlib`, `secrets` | en los bordes |
| Servicios | `petitio`, `net`, `jsonrpc` | para herramientas y servidores |
| WebAssembly | `web` + `std/web/*` (16 módulos) | solo builds de navegador |

**Regla práctica.** Si un módulo está en la capa "Núcleo" o "Texto", impórtalo
sin miedo. Si está en "Interop" o "Servicios", lee antes su "Evítalo cuando":
puede traer una dependencia nativa.

## 2. Elegir un módulo por tarea

| Necesito… | Usa | No |
| --- | --- | --- |
| imprimir, parsear un int, salir | `std.spark` | — |
| construir un string en un bucle | `std.builder` | `+` en un bucle |
| partir, recortar, reemplazar, comparar strings | `std.scrolls` | bucles a mano |
| contar caracteres, no bytes | `std.lingua` | `s.len` sobre UTF-8 |
| clasificar un `char` | `std.littera` | rangos escritos a mano |
| hacer matemáticas con todos los tipos numéricos | `std.numerus` | una función por tipo |
| hacer matemáticas solo de enteros | `std.integrum` | `numerus` cuando necesitas `%` |
| hacer matemáticas solo de floats | `std.fractio` | `numerus` |
| vectores, matrices, cuaterniones | `std.arithmancy` | structs a mano |
| números aleatorios | `std.lot` | `time()` sembrado a ojo |
| iterar, trocear, zip, fold | `std.loom` | bucles con índice |
| reducir, buscar, ordenar una lista | `std.tally` | `loom` para rutas solo de int |
| mapa / conjunto | `std.atlas`, `std.coven` | listas paralelas |
| mapa ordenado, lista enlazada | `std.ordinal` | ordenar el mapa cada vez |
| pertenencia sobre un rango acotado | `std.bitset` | `map of int to bool` |
| asignar muchos objetos de vida corta | `std.arena` | un `alloc` para cada uno |
| pasar un callback con contexto | `std.functor` | una global |
| JSON | `std.json` | `std.cipher.parse_json` (legado, plano) |
| TOML / YAML / CSV | `std.toml`, `std.yaml`, `std.ledger` | regex |
| registros binarios | `std.carmen` | offsets de bytes a mano |
| base64, hex, CRC-32 | `std.cipher` | tablas a mano |
| gzip / zlib / deflate | `std.compressus` | llamar a `gzip` por shell |
| SHA-256 | `std.digest` | CRC-32 |
| expresiones regulares | `std.regulus` | partir strings |
| archivos, directorios, recorrerlos | `std.archivum` | `system("ls")` |
| rutas | `std.compass` | concatenar strings |
| entorno, argv, exec | `std.rites` | `getenv` por FFI |
| flags de CLI tipados | `std.invoke` | parsear `argv` a mano |
| leer exactamente N bytes | `std.io` | `std.spark.input` |
| sockets TCP | `std.net` | FFI a `socket()` |
| cliente HTTP | `std.petitio` | `net` + HTTP a mano |
| JSON-RPC 2.0 | `std.jsonrpc` | framing a mano |
| hora y fechas | `std.chronicle` | `time()` por FFI |
| nanosegundos, ISO 8601 | `std.chrono` | floats de `chronicle` |
| logging | `std.whisper` | `print` con prefijos |
| posiciones en el fuente | `std.sourcemap` | contar saltos de línea |
| errores estilo compilador | `std.diagnostic` | strings ad hoc |
| tests | `std.ward` + `std.trial` | `assert` de `spark` |
| mutex, atómicos, canales | `std.filum` | — |
| llamar a una librería C | `std.ffi` | `antiquus` por todas partes |
| llamar a una función por nombre en runtime | `std.ffi_call` | `dynlib` solo |
| cargar un `.so`/`.dll` | `std.dynlib` | — |
| bytes aleatorios, borrar memoria | `std.secrets` | `std.lot` |
| DOM, canvas, fetch en el navegador | `std.web.*` | — |

## 3. Núcleo y memoria

### `std.spark` — E/S de proceso, conversiones y control

**Úsalo cuando** necesites la consola (`print`, `println`, `eprint`), convertir
un escalar a texto (`str_int`, `str_float`), parsear (`parse_int`,
`parse_float`), un rango de enteros (`range`), una aserción que aborta en un
invariante real, o `exit`.

**Evítalo cuando** la salida sea un flujo de datos: `print` está orientado a
líneas y formatea valores; usa `std.io` para bytes y `std.whisper` para logs.

**Destacados** `print`, `println`, `eprintln`, `flush`, `parse_int`, `panic`,
`exit`.

**API** [`api/std_spark.md`](api/std_spark.md) · [fuente](../std/spark.pengu)

### `std.memoria` — bloques crudos del heap

**Úsalo cuando** estés implementando un contenedor, un protocolo de búfer o un
binding, y necesites `alloc`, `alloc_array`, `resize_array`, `copy`, `fill`,
`zero`, `swap` o `compare` sobre memoria sin tipo.

**Evítalo cuando** un tipo de valor ya cubra el caso: `list`, `map`,
`StringBuilder` y `arena` son dueños de su memoria y la liberan con un solo
`banish`.

**Destacados** `alloc of T`, `alloc_array of T with n`, `copy`, `zero`,
`resize_array`.

**API** [`api/std_memoria.md`](api/std_memoria.md) · [fuente](../std/memoria.pengu)

### `std.oracle` — `maybe` y `result`

**Úsalo cuando** un cálculo pueda estar ausente (`maybe T`) o fallar con un
motivo (`result of T to E`), y quieras la caja de herramientas completa:
constructores (`some_of`, `none_of`, `ok_of`, `err_of`), inspección
(`is_present`, `is_ok`, `is_err`), transformación (`map`, `and_then`, `map_err`),
recuperación (`unwrap_or`, `unwrap_or_else`) y conversión.

**Evítalo cuando** la ausencia sea imposible por construcción: devuelve `T`.

**Destacados** `some_of`, `none_of`, `ok_of`, `err_of`, `unwrap_or`.

**API** [`api/std_oracle.md`](api/std_oracle.md) · [fuente](../std/oracle.pengu)

### `std.builder` — `StringBuilder`

**Úsalo cuando** un string se arme con más de dos piezas, sobre todo en un
bucle: `append`, `append_int`, `append_char`, `append_slice`, `finish`.

**Evítalo cuando** estés uniendo una lista que ya tienes: `scrolls.join` es más
corto e igual de lineal.

**Destacados** `new`, `append`, `append_int`, `append_char`, `finish`.

**API** [`api/std_builder.md`](api/std_builder.md) · [fuente](../std/builder.pengu)

### `std.arena` — asignador bump

**Úsalo cuando** construyas un grafo grande de objetos con una sola vida (una
petición, un frame, un árbol de parseo) y quieras liberarlo todo de golpe:
`Arena.new`, `arena_alloc of T`, `reset`, `free`.

**Evítalo cuando** los objetos tengan vidas independientes, o uno sobreviva a la
arena: la arena lo libera todo junto.

**Destacados** `Arena.new`, `arena_alloc of T`, `arena_alloc_one`, `reset`.

**API** [`api/std_arena.md`](api/std_arena.md) · [fuente](../std/arena.pengu)

### `std.functor` — funciones con contexto

**Úsalo cuando** un callback deba recordar estado y un `concept` sea
demasiado: `Fn0`–`Fn3` llevan un puntero a función más un contexto explícito,
con `make_fn0`–`make_fn3` y `call`.

**Evítalo cuando** el callback no tenga estado: pasa el puntero a función.

**Destacados** `Fn1`, `make_fn1`, `call`.

**API** [`api/std_functor.md`](api/std_functor.md) · [fuente](../std/functor.pengu)

### `std.sourcemap` — offsets de byte ↔ línea/columna

**Úsalo cuando** informes posiciones en texto fuente: diagnósticos, trazas,
respuestas LSP, formateadores. `SourceMap` indexa los inicios de línea una vez y
responde en ambas direcciones.

**Evítalo cuando** solo imprimas una posición: contar saltos de línea es más
barato.

**Destacados** `SourceMap.from_source`, `position_at`, `offset_of`.

**API** [`api/std_sourcemap.md`](api/std_sourcemap.md) · [fuente](../std/sourcemap.pengu)

### `std.bitset` — conjunto de bits denso de longitud fija

**Úsalo cuando** la pertenencia sea sobre un universo entero acotado (flags de
visitado, máscaras de features, cierre de dependencias) y quieras O(1) por bit y
álgebra de conjuntos palabra a palabra (`and_with`, `or_with`, `xor_with`,
`and_not_with`, `not`).

**Evítalo cuando** el universo sea disperso o ilimitado: usa `std.coven`.

**Destacados** `BitSet.new`, `set`, `get`, `count_ones`, `and_with`.

**API** [`api/std_bitset.md`](api/std_bitset.md) · [fuente](../std/bitset.pengu)

### `std.diagnostic` — spans, etiquetas y renderizadores

**Úsalo cuando** construyas una herramienta que informa problemas en texto
fuente y quieras la forma conocida: severidad, código, mensaje, spans primarios
y secundarios, y un renderizador con caret.

**Evítalo cuando** el mensaje no tenga ubicación en el fuente: `whisper` o
`spark`.

**Destacados** `Diagnostic`, `Span`, `Label`, `Severity`, `render`.

**API** [`api/std_diagnostic.md`](api/std_diagnostic.md) · [fuente](../std/diagnostic.pengu)

## 4. Texto y números

### `std.scrolls` — strings orientados a bytes

**Úsalo cuando** el texto sea ASCII, o estés cortando bytes a propósito: `len`,
`substring`, `split`, `join`, `trim`, `strip`, `replace`, `index_of`,
`starts_with`, `lower`, `upper`, `pad_left`, conversión de caja
(`to_snake_case`, `pascal_case`, …) y clasificación ASCII.

**Evítalo cuando** el texto sea UTF-8 y te importen los caracteres: `len` cuenta
bytes, `char_at` devuelve un byte y `reverse` invierte bytes. Usa `std.lingua`
para codepoints.

**Destacados** `substring`, `split`, `join`, `trim`, `replace`, `starts_with`.

**API** [`api/std_scrolls.md`](api/std_scrolls.md) · [fuente](../std/scrolls.pengu)

### `std.lingua` — UTF-8 sobre codepoints

**Úsalo cuando** el texto visible por el usuario deba medirse o recorrerse en
caracteres: `codepoint_count`, `codepoint_at`, `next_codepoint`,
`prev_codepoint`, `encode`, `decode`, `validate`, `grapheme_count` y el seal
`Codepoint`.

**Evítalo cuando** la entrada sea ASCII conocida y esté en una ruta caliente:
las funciones de bytes de `std.scrolls` son más baratas.

**Destacados** `codepoint_count`, `codepoint_at`, `next_codepoint`, `validate`.

**API** [`api/std_lingua.md`](api/std_lingua.md) · [fuente](../std/lingua.pengu)

### `std.littera` — métodos sobre `char`

**Úsalo cuando** clasifiques o conviertas un solo carácter ASCII: `is_digit`,
`is_alpha`, `is_alnum`, `is_space`, `is_hex_digit`, `is_printable`, `to_lower`,
`to_upper`, `digit_value`, `to_int`.

**Evítalo cuando** el carácter pueda ser multibyte: eso es un codepoint, no un
`char`.

**Destacados** `is_digit`, `is_alpha`, `to_lower`, `to_upper`, `digit_value`.

**API** [`api/std_littera.md`](api/std_littera.md) · [fuente](../std/littera.pengu)

### `std.logica` — métodos sobre `bool`

**Úsalo cuando** una expresión booleana se lea mejor como conectiva con nombre:
`and_with`, `or_with`, `xor`, `nand`, `nor`, `implies`, `iff`, `toggle`,
`to_int`.

**Evítalo cuando** el operador ya sea claro: `a and b` gana a
`a.and_with with b`.

**Destacados** `xor`, `implies`, `toggle`, `to_int`.

**API** [`api/std_logica.md`](api/std_logica.md) · [fuente](../std/logica.pengu)

### `std.integrum` — métodos sobre enteros

**Úsalo cuando** el cálculo sea solo de enteros: `is_even`, `is_odd`,
`is_prime`, `gcd`, `lcm`, `factorial`, `bit_count`, `bit_length`,
`leading_zeros`, `trailing_zeros`, `div_floor`, `mod_floor`, `div_rem`,
`next_power_of_two`, `to_hex`, `to_bin`, `to_oct`.

**Evítalo cuando** el valor sea de coma flotante: `std.fractio`.

**Destacados** `is_even`, `gcd`, `div_floor`, `to_hex`, `bit_count`.

**API** [`api/std_integrum.md`](api/std_integrum.md) · [fuente](../std/integrum.pengu)

### `std.fractio` — métodos sobre floats

**Úsalo cuando** el cálculo sea de coma flotante: `sqrt`, `cbrt`, `pow`, `exp`,
`ln`, `log2`, `log10`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`,
`hypot`, `degrees`, `radians`, `lerp`, `approx_eq`, `is_nan`, `is_finite`,
`is_infinite`.

**Evítalo cuando** importe la aritmética decimal exacta: ningún float binario es
exacto; escala a enteros y usa `std.integrum`.

**Destacados** `sqrt`, `pow`, `approx_eq`, `is_nan`, `lerp`.

**API** [`api/std_fractio.md`](api/std_fractio.md) · [fuente](../std/fractio.pengu)

### `std.numerus` — métodos sobre cualquier número

**Úsalo cuando** el código deba servir tanto para enteros como para floats a
través del concepto `Num`: `abs`, `min_with`, `max_with`, `clamp`, `signum`,
`round`, `floor`, `ceil`, `truncate`, `square`, `cube`, `pow_int`, `is_zero`,
`is_between`, `to_i64`, `to_f64`.

**Evítalo cuando** necesites operaciones solo de enteros (`%`, trucos de bits):
esas están en `std.integrum`.

**Destacados** `abs`, `clamp`, `min_with`, `max_with`, `round`.

**API** [`api/std_numerus.md`](api/std_numerus.md) · [fuente](../std/numerus.pengu)

### `std.arithmancy` — vectores, matrices, cuaterniones

**Úsalo cuando** hagas geometría o gráficos: `Vec2`, `Vec3`, `Vec4`, `Mat4`,
`Quat`, con `dot`, `cross`, `normalize`, `length`, `distance`, `lerp`,
`reflect`, `mat4_perspective`, `mat4_look_at`, `mat4_rotate`, `quat_from_euler`,
`quat_from_axis_angle`, `slerp`.

**Evítalo cuando** baste una operación escalar: `std.fractio`.

**Destacados** `Vec3`, `Mat4`, `Quat`, `dot`, `normalize`, `mat4_perspective`.

**API** [`api/std_arithmancy.md`](api/std_arithmancy.md) · [fuente](../std/arithmancy.pengu)

### `std.lot` — números pseudoaleatorios

**Úsalo cuando** necesites aleatoriedad o muestreo: `rand_int`, `rand_float`,
`rand_bool`, `rand_range`, `rand_bytes`, `rand_normal`, `rand_exp`,
`rand_poisson`, `choice`, `choice_weighted`, `permutation`, `rand_password`.
El generador es PCG32 y la semilla es explícita.

**Evítalo cuando** los bytes deban ser criptográficamente seguros:
`std.secrets` (libsodium) o `std.web.crypto` en el navegador. `lot` es
reproducible, no secreto.

**Destacados** `rand_int`, `rand_float`, `rand_bytes`, `choice`, `rand_range`.

**API** [`api/std_lot.md`](api/std_lot.md) · [fuente](../std/lot.pengu)

## 5. Colecciones

### `std.loom` — algoritmos de listas, familia segura

**Úsalo cuando** transformes una lista y quieras una respuesta `maybe`/`list` en
vez de un centinela: generación (`range`, `repeat`, `unfold_range`), cortes
(`take`, `skip`, `chunks`, `windows`, `pairwise`), combinación (`chain`,
`zip_with`, `enumerate`, `interleave`, `intersperse`, `rotate`), folds (`fold`,
`scan_left`, `sum`, `product_num`, `min_max`, `mean`, `running_*`), `map`,
`filter`, `flat_map`, `find_first`, `any_ctx`, `all_ctx`.

**Evítalo cuando** la lista sea `list of int` y quieras la API concreta y
compacta: `std.tally` comparte 15 nombres con firmas distintas — no son
intercambiables.

**Destacados** `map`, `filter`, `fold`, `chunks`, `zip_with`, `enumerate`.

**API** [`api/std_loom.md`](api/std_loom.md) · [fuente](../std/loom.pengu)

### `std.tally` — algoritmos de listas, familia concreta

**Úsalo cuando** la lista contenga `int` (o un tipo con los bounds necesarios) y
quieras la API directa y con pocas asignaciones: `sum`, `average`, `max_val`,
`min_val`, `argmax`, `argmin`, `sort`, `dedup`, `contains`, `count_of`,
`frequencies`, `group_count`, `chunk`, `flatten`, `is_sorted_*`.

**Evítalo cuando** necesites respuestas `maybe` o floats: `std.tally` colapsa a
un centinela (`0`, `""`, `false`) y trunca a `int`. Usa `std.loom`.

**Destacados** `sum`, `average`, `sort`, `contains`, `frequencies`.

**API** [`api/std_tally.md`](api/std_tally.md) · [fuente](../std/tally.pengu)

### `std.atlas` — mapas

**Úsalo cuando** indexes valores por string o int: `get_safe`, `get_or`,
`has_key`, `put`, `remove`, `entries`, `keys`, `values`, `count`,
`filter_entries`, `from_pairs`, `from_lists`, más los métodos genéricos de
`map of K to V`.

**Evítalo cuando** las claves sean un rango pequeño y denso de enteros:
`std.bitset`, o un `list` indexado directamente.

**Destacados** `get_safe`, `get_or`, `has_key`, `entries`, `from_pairs`.

**API** [`api/std_atlas.md`](api/std_atlas.md) · [fuente](../std/atlas.pengu)

### `std.coven` — conjuntos

**Úsalo cuando** importen la pertenencia y la unicidad: `SetString`, `SetInt` y
el genérico `Set of T`, con `add`, `contains`, `remove`, `union`, `intersect`,
`difference`, `symmetric_difference`, `is_subset`, `is_superset`,
`is_disjoint`.

**Evítalo cuando** el universo sea un rango acotado de enteros: `std.bitset` es
más denso y rápido.

**Destacados** `add`, `contains`, `union`, `intersect`, `to_list`.

**API** [`api/std_coven.md`](api/std_coven.md) · [fuente](../std/coven.pengu)

### `std.ordinal` — contenedores sobre CC

**Úsalo cuando** necesites un contenedor que los integrados no dan:
`LinkedList of T`, `UnorderedSet of T`, `OrderedSet of T`, `OrderedMap of K and
V` — con `push_back`, `push_front`, `pop_front`, `put`, `get`, `has`, `remove`,
`keys`, `values`, `size`.

**Evítalo cuando** `list`, `map` o `Set` ya encajen: los contenedores CC existen
para los casos en que el orden o la estabilidad de nodos es el punto.

**Destacados** `new_linked_list`, `new_ordered_map`, `push_back`, `put`, `get`.

**API** [`api/std_ordinal.md`](api/std_ordinal.md) · [fuente](../std/ordinal.pengu)

## 6. Formatos y codificaciones

### `std.json` — JSON estricto (RFC 8259)

**Úsalo cuando** parsees o produzcas JSON y necesites un DOM de verdad: `parse`,
`stringify`, `JsonValue` con `as_object`, `as_array`, `as_string`, `as_int`,
`as_float`, `as_bool`, `get`, `at`, preservación del orden de inserción, JSON
Pointer (RFC 6901), merge profundo y validación de esquema.

**Evítalo cuando** el documento sea un mapa plano `{"clave": "valor"}` y quieras
el atajo de la era 0.14: `std.cipher.parse_json` devuelve
`map of string to string` y pierde los tipos.

**Destacados** `parse`, `stringify`, `as_object`, `as_string`, `get`.

**API** [`api/std_json.md`](api/std_json.md) · [fuente](../std/json.pengu)

### `std.cipher` — codificaciones y checksums

**Úsalo cuando** muevas bytes como texto o verifiques integridad:
`encode_base64`, `decode_base64` (estándar, URL-safe, sin relleno),
`encode_hex`, `decode_hex`, Base32/Base58/Base85/Z85, `encode_url`,
`decode_url`, `crc32`.

**Evítalo cuando** necesites un resumen criptográfico: `std.digest` (SHA-256).
CRC-32 detecta accidentes, no ataques.

**Destacados** `encode_base64`, `decode_base64`, `encode_hex`, `crc32`,
`encode_url`.

**API** [`api/std_cipher.md`](api/std_cipher.md) · [fuente](../std/cipher.pengu)

### `std.carmen` — registros binarios de formato fijo

**Úsalo cuando** un formato binario tenga offsets fijos y quieras describirlo,
no codificarlo a mano: una cadena de formato (`>I4sH`) más
`CarmenWriter`/`CarmenReader`, `calcsize`, `format`, endianness, modos nativo y
compatible con Python.

**Evítalo cuando** el formato se autodescriba o esté anidado: `std.json` o
`std.toml`.

**Destacados** `CarmenWriter`, `CarmenReader`, `calcsize`, `format`.

**API** [`api/std_carmen.md`](api/std_carmen.md) · [fuente](../std/carmen.pengu)

### `std.toml` — TOML 1.0

**Úsalo cuando** leas o escribas configuración y manifiestos: `parse`,
`parse_file`, `stringify`, `get`, `get_int`, `get_bool`, `get_float`,
`get_array`, `keys_with_prefix`, sobre claves punteadas de `TomlEntry`.

**Evítalo cuando** los datos ya sean JSON: convertirlos cuesta más de lo que
ahorra.

**Destacados** `parse`, `parse_file`, `get_int`, `stringify`.

**API** [`api/std_toml.md`](api/std_toml.md) · [fuente](../std/toml.pengu)

### `std.yaml` — el subconjunto legado de manifiestos

**Úsalo cuando** debas leer archivos estilo `pengu.yaml`/`pengu.yml`: `parse`,
`parse_file`, `get`, `get_array`. Implementa exactamente el subconjunto de
recorrido por indentación que aceptaba el compilador viejo, no YAML completo.

**Evítalo cuando** tú controles el formato: TOML (`std.toml`) es el formato
canónico de manifiesto y es un parser de verdad.

**Destacados** `parse`, `parse_file`, `get`.

**API** [`api/std_yaml.md`](api/std_yaml.md) · [fuente](../std/yaml.pengu)

### `std.ledger` — CSV y TSV

**Úsalo cuando** intercambies texto tabular: `parse_csv`, `parse_tsv`,
`read_csv`, `read_tsv`, `to_csv_string`, `CsvTable` con `row_count`,
`column_count`, `column`, `row_as_map`, `transpose`, modos de comillas (RFC
4180, barra invertida, ninguna).

**Evítalo cuando** el archivo sea una exportación de base de datos con tipos
anidados: normaliza primero a JSON.

**Destacados** `parse_csv`, `read_csv`, `row_as_map`, `to_csv_string`.

**API** [`api/std_ledger.md`](api/std_ledger.md) · [fuente](../std/ledger.pengu)

### `std.compressus` — gzip, zlib, deflate

**Úsalo cuando** comprimas o descomprimas bytes: `gzip_compress`,
`gzip_decompress`, `zlib_compress`, `zlib_decompress`, `deflate_compress`,
`inflate_decompress`, `detect_format`, variantes de archivo, `crc32`,
`adler32`. El wrapper añade el contenedor gzip (RFC 1952) sobre miniz vendorizado.

**Evítalo cuando** los bytes ya estén comprimidos (imágenes, vídeo): recomprimir
gasta CPU y no aporta nada. Antes de añadir compresión a un binario, prueba el
perfilado con `output = "static"`/`small`.

**Destacados** `gzip_compress`, `gzip_decompress`, `deflate_compress`,
`detect_format`.

**API** [`api/std_compressus.md`](api/std_compressus.md) · [fuente](../std/compressus.pengu)

### `std.digest` — SHA-256 y compañía

**Úsalo cuando** necesites un resumen criptográfico: `sha256_hex`, `sha256_raw`,
`sha256_file`, `hmac_sha256_hex`, `hmac_sha256_raw`, o el barato `fnv1a64` para
tablas hash.

**Evítalo cuando** solo necesites detección de errores: `std.cipher.crc32`.

**Destacados** `sha256_hex`, `sha256_raw`, `sha256_file`, `hmac_sha256_hex`.

**API** [`api/std_digest.md`](api/std_digest.md) · [fuente](../std/digest.pengu)

### `std.regulus` — expresiones regulares pequeñas

**Úsalo cuando** cases un patrón corto y bien entendido: `Regex`, `find_first`,
`match`, `is_match`, `matches`, `match_at`, `replace_first`, `replace_all`,
`split`, `escape`. El motor deliberadamente no es PCRE: sin sorpresas de
backtracking, un bloque compilado por patrón.

**Evítalo cuando** la entrada sea datos estructurados: regex para JSON, HTML o
email es un error de categoría. Usa `std.json`, un DOM o un validador.

**Destacados** `find_first`, `replace_all`, `split`, `escape`.

**API** [`api/std_regulus.md`](api/std_regulus.md) · [fuente](../std/regulus.pengu)

## 7. Sistema, tiempo y diagnósticos

### `std.archivum` — el sistema de archivos

**Úsalo cuando** leas, escribas, inspecciones o recorras archivos: `read_text`,
`read_bytes`, `write_text`, `append_text`, `exists`, `is_file`, `is_dir`,
`file_size`, `create_dir`, `delete_file`, `copy_file`, `copy_tree`,
`find_files`, `find_dirs`, `glob`, `dir_size`, y las variantes `*_result` que
dicen *por qué* falló una operación.

**Evítalo cuando** la operación sea sobre una ruta, no sobre el sistema de
archivos: eso es `std.compass`, que es puro y testeable.

**Destacados** `read_text`, `write_text`, `exists`, `read_file_result`,
`find_files`.

**API** [`api/std_archivum.md`](api/std_archivum.md) · [fuente](../std/archivum.pengu)

### `std.compass` — rutas

**Úsalo cuando** unas, partas o normalices una ruta: `join`, `basename`,
`dirname`, `ext`, `stem`, `normalize`, `absolute`, `relative_to`, `components`,
`expand_user`, `cwd`, `matches`, y el rune `Path`.

**Evítalo cuando** necesites tocar el disco: `std.archivum`.

**Destacados** `join`, `basename`, `dirname`, `normalize`, `absolute`.

**API** [`api/std_compass.md`](api/std_compass.md) · [fuente](../std/compass.pengu)

### `std.rites` — el sistema operativo

**Úsalo cuando** necesites el entorno del proceso: `getenv`, `has_env`,
`get_args`, `arg_at_or`, `get_flag_value`, `parse_flags`, `exec`, `exec_ok`,
`home_dir`, `config_dir`, `cache_dir`, `data_dir`, `getpid`, `hostname`,
`is_windows`, `is_linux`, `is_macos`, `chdir`, `expand_env`.

**Evítalo cuando** parsees una línea de comandos tipada: `std.invoke` maneja
flags, valores por defecto y usage.

**Destacados** `getenv`, `get_args`, `exec`, `home_dir`, `is_windows`.

**API** [`api/std_rites.md`](api/std_rites.md) · [fuente](../std/rites.pengu)

### `std.invoke` — parseo tipado de línea de comandos

**Úsalo cuando** un CLI tenga flags, opciones, posicionales o subcomandos:
`new_parser`, `add_flag`, `add_option`, `add_option_int`, `add_option_bool`,
`add_positional`, `add_subcommand`, `parse`, `get_int`, `get_bool`, `get_or`,
`usage_string`, `full_help`.

**Evítalo cuando** el programa reciba un solo argumento: `rites.get_args`.

**Destacados** `new_parser`, `add_flag`, `add_option`, `parse`, `get_int`.

**API** [`api/std_invoke.md`](api/std_invoke.md) · [fuente](../std/invoke.pengu)

### `std.io` — E/S estándar exacta en bytes

**Úsalo cuando** un protocolo necesite bytes exactos: `read_stdin_exact`,
`read_stdin_all`, `read_stdin_line`, `write_stdout`, `write_stderr`,
`flush_stdout`, `is_tty` — sin perder NUL incrustados ni añadir saltos de línea.

**Evítalo cuando** el texto sean líneas para humanos: `std.spark.print`.

**Destacados** `read_stdin_exact`, `read_stdin_all`, `write_stdout`, `is_tty`.

**API** [`api/std_io.md`](api/std_io.md) · [fuente](../std/io.pengu)

### `std.net` — sockets TCP bloqueantes

**Úsalo cuando** implementes un protocolo de servidor o cliente sobre TCP:
`listen`, `accept`, `connect`, `read`, `read_exact`, `write`, `close`,
`is_open`, sobre un rune `Socket` que guarda el descriptor.

**Evítalo cuando** hables HTTP: `std.petitio` (cliente) o un servidor hecho a
propósito. Reimplementar el framing de HTTP es como se envían bugs a
producción.

**Destacados** `listen`, `accept`, `connect`, `read_exact`, `write`.

**API** [`api/std_net.md`](api/std_net.md) · [fuente](../std/net.pengu)

### `std.chronicle` — relojes y calendarios

**Úsalo cuando** necesites tiempo ordinario: `time`, `monotonic`, `now_ms`,
`sleep_ms`, `DateTime`, `datetime_utc`, `datetime_local`, `format`, `from_iso`,
`add_days`, `days_between`, `is_weekend`, `start_of_day`, `end_of_month`,
`diff_seconds`, `elapsed_ms`.

**Evítalo cuando** necesites nanosegundos o aritmética de calendario de verdad:
`std.chrono` (`Instant`/`Duration`, ida y vuelta ISO 8601). Los timestamps de
`chronicle` son `float`, y `float` es de 32 bits, así que la resolución en épocas
modernas es gruesa.

**Destacados** `time`, `monotonic`, `sleep_ms`, `DateTime`, `format`.

**API** [`api/std_chronicle.md`](api/std_chronicle.md) · [fuente](../std/chronicle.pengu)

### `std.chrono` — instantes y duraciones (vaqt)

**Úsalo cuando** importe la precisión: `Instant`, `Duration`, `now`, `to_iso`,
`parse_iso`, `plus_days`, `add_duration`, `to_unix_nano`, `weekday`,
`format_datetime`. Respaldado por la librería vaqt vendorizada; es opt-in.

**Evítalo cuando** `chronicle` ya cubra el caso: `chrono` añade una dependencia
nativa y una API más grande para el mismo reloj de pared.

**Destacados** `Instant`, `Duration`, `now`, `to_iso`, `to_unix_nano`.

**API** [`api/std_chrono.md`](api/std_chrono.md) · [fuente](../std/chrono.pengu)

### `std.whisper` — logging por niveles

**Úsalo cuando** el programa necesite logs que lean una persona o una máquina:
`debug`, `info`, `warn`, `error`, `fatal`, `log`, `log_json` (líneas JSON),
`named_logger` (loggers hijos), `set_level` a través del logger por defecto,
colores ANSI, timestamps y redirección a archivo/stderr.

**Evítalo cuando** la salida sea el resultado real del programa: los logs van a
stderr, los resultados a stdout.

**Destacados** `info`, `error`, `log_json`, `named_logger`, `flush`.

**API** [`api/std_whisper.md`](api/std_whisper.md) · [fuente](../std/whisper.pengu)

## 8. Testing

### `std.ward` — aserciones para tests y guardas

**Úsalo cuando** un test deba detenerse en el primer valor incorrecto: `assert`,
`assert_msg`, `assert_true`, `assert_false`, `assert_eq_int`,
`assert_eq_string`, `assert_eq_bool`, `assert_eq_float` (con epsilon),
`assert_ne_*`, `assert_gt_*`, `assert_ge_*`, `assert_lt_*`, `assert_le_*`,
`assert_in_range_*`, variantes de listas y mapas, `assert_maybe_present`,
`assert_maybe_none`, `assert_ok_*`, `assert_err_*`.

**Evítalo cuando** la condición sea un invariante de producción:
`spark.assert` o un `result` explícito. `ward` es una dependencia de test.

**Destacados** `assert`, `assert_eq_int`, `assert_eq_string`, `assert_eq_float`.

**API** [`api/std_ward.md`](api/std_ward.md) · [fuente](../std/ward.pengu)

### `std.trial` — suites y reporte

**Úsalo cuando** un binario de test crezca más allá de un puñado de bloques
`test`: `TestSuite`, `new_suite`, `test_case`, `test`, `summary`. Reexporta las
aserciones habituales de `ward` para que un archivo de test necesite un solo
import.

**Evítalo cuando** el proyecto tenga uno o dos tests: los bloques `test` sueltos
bastan y `psc test` ya los ejecuta.

**Destacados** `new_suite`, `test_case`, `test`, `summary`.

**API** [`api/std_trial.md`](api/std_trial.md) · [fuente](../std/trial.pengu)

## 9. Concurrencia

### `std.filum` — primitivas de sincronización

**Úsalo cuando** existan hilos fuera del lenguaje y deban coordinarse: `Mutex`
(`lock`, `unlock`, `try_lock`), `WaitGroup` (`add`, `done`, `wait`), `Once`
(`do_once`), `Cond` (`cond_wait`, `signal`, `broadcast`), `AtomicInt` (`load`,
`store`, `add_atomic`, `swap`, `compare_swap`, `inc`, `dec`) y canales tipados
(`ChanInt`, `ChanString`, `ChanFloat`, `ChanBool`, `Chan`) con `send` → `bool` y
`recv` → `maybe`.

**Evítalo cuando** esperes que `filum` cree un hilo: no lo hace. La creación de
hilos pertenece al anfitrión (C, un binding o la aplicación que embebe);
`filum` aporta las primitivas que esos hilos usan.

**Destacados** `Mutex`, `WaitGroup`, `AtomicInt`, `chan_int`, `send`, `recv`.

**API** [`api/std_filum.md`](api/std_filum.md) · [fuente](../std/filum.pengu)

## 10. Servicios de red

### `std.petitio` — cliente HTTP

**Úsalo cuando** el programa hable HTTP: `get`, `post`, `put`, `delete`, `head`,
`patch`, `options`, `fetch_many`, cabeceras personalizadas, cuerpos JSON y de
formulario, multipart, query strings, cookies, timeouts, auth (`auth_basic`,
`auth_bearer`, `auth_digest`) y errores tipados con `result` (`HttpError`).

**Evítalo cuando** el transporte no sea HTTP (TCP crudo: `std.net`) o el cliente
deba vivir en el navegador (`std.web.http`, que usa `fetch`).

**Destacados** `get`, `post`, `Request`, `Response`, `HttpError`, `auth_bearer`.

**API** [`api/std_petitio.md`](api/std_petitio.md) · [fuente](../std/petitio.pengu)

### `std.jsonrpc` — JSON-RPC 2.0

**Úsalo cuando** implementes JSON-RPC: `encode_request`, `encode_notification`,
`encode_response_ok`, `encode_response_error`, `decode_message`, soporte de
lotes, los cinco códigos de error estándar y el framing `Content-Length` de LSP
(`encode_framed`, `decode_framed`).

**Evítalo cuando** el protocolo sea JSON plano sobre HTTP: `std.json` más
`std.petitio`.

**Destacados** `encode_request`, `decode_message`, `encode_framed`,
`decode_framed`.

**API** [`api/std_jsonrpc.md`](api/std_jsonrpc.md) · [fuente](../std/jsonrpc.pengu)

## 11. Interop y código nativo

### `std.ffi` — búferes y strings de C

**Úsalo cuando** una función C declarada con `declare` reciba o devuelva
`char *`, `void *`, un búfer con longitud prefijada o un array `T *`, y debas
convertir desde y hacia valores PenguScript: `cstr_from_string` (prestado, hay
que liberarlo con `cstr_free`), `bytes_from_string`, `is_null`, `ptr_add`,
`ptr_offset`, `size_of`, `alignment_of`, `slice_from_ptr`, `list_from_ptr`,
`map_from_ptr`, y la familia tipada `list_of_*_from_ptr`.

**Evítalo cuando** un parámetro `ref to char` acepte un literal de string: el
literal se convierte automáticamente, sin puente.

**Destacados** `cstr_from_string`, `cstr_free`, `is_null`, `size_of`,
`slice_from_ptr`.

**API** [`api/std_ffi.md`](api/std_ffi.md) · [fuente](../std/ffi.pengu)

### `std.ffi_call` — llamadas dinámicas con libffi (opcional)

**Úsalo cuando** la firma solo se conozca en runtime: `FfiSignature`,
`signature`, `call`, `ret_size`, `release`. Solo enlaza `-lffi` cuando se
importa.

**Evítalo cuando** la firma se conozca en tiempo de compilación: `declare` es
más rápido, está comprobado por tipos y no necesita dependencia.

**Destacados** `FfiSignature`, `signature`, `call`.

**API** [`api/std_ffi_call.md`](api/std_ffi_call.md) · [fuente](../std/ffi_call.pengu)

### `std.dynlib` — carga dinámica de librerías

**Úsalo cuando** un plugin o una dependencia opcional se cargue en runtime:
`Library`, `open`, `symbol`, `close`. La portabilidad está resuelta (`dlopen`
en POSIX, `LoadLibraryA` en Windows).

**Evítalo cuando** la librería sea una dependencia de build: `link "name"` más
`declare` se comprueba en el build y se poda correctamente.

**Destacados** `Library`, `open`, `symbol`, `close`.

**API** [`api/std_dynlib.md`](api/std_dynlib.md) · [fuente](../std/dynlib.pengu)

### `std.secrets` — primitivas de libsodium (opcional)

**Úsalo cuando** necesites secretos, no aleatoriedad: `init`, `random_bytes`,
`sha256_raw`, `wipe` (borrado seguro) y `compare` (tiempo constante). Requiere
`links = ["sodium"]`.

**Evítalo cuando** libsodium no esté enlazado, o los bytes no sean secretos:
`std.lot` es reproducible y no tiene dependencias.

**Destacados** `init`, `random_bytes`, `wipe`, `compare`.

**API** [`api/std_secrets.md`](api/std_secrets.md) · [fuente](../std/secrets.pengu)

## 12. WebAssembly

Todo lo de esta sección requiere `--target wasm` y una toolchain de Emscripten.
`std.web.url` y `std.web.security` son la excepción: son PenguScript puro y
también corren en builds nativos.

Protege el código solo de navegador con `when wasm:`; la rama inactiva se
elimina antes de emitir C.

```pengu
import std.web.dom
import std.web.event

when wasm:
    weave mount into void:
        let root as dom.Element is calling dom.create with "div"
        calling dom.set_text with root, "hello"
```

### `std.web` — el puente del navegador

**Úsalo cuando** necesites las piezas que todo build wasm tiene: `console_log`,
`console_warn`, `console_error`, `console_trace`, `set_main_loop` (mantiene vivo
el runtime para los callbacks) y el tipo de handle compartido.

**Evítalo cuando** un módulo especializado cubra el área: `std.web.dom` para
elementos, `std.web.http` para peticiones.

**Destacados** `console_log`, `console_error`, `set_main_loop`.

**API** [`api/std_web.md`](api/std_web.md) · [fuente](../std/web.pengu)

### `std.web.js` — interop con JavaScript

**Úsalo cuando** debas llamar a JavaScript directamente: handles `JsValue`,
`global`, `get`, `call_method`, `call`, `eval`, `import_module`, `from_string`,
`from_int`, `from_f64`, `array`, `object`, `retain`, `release`. Los handles
tienen dueño: libera lo que creas, retén lo que guardes más allá de un callback.

**Evítalo cuando** la operación tenga un wrapper tipado (`dom`, `canvas`,
`http`): los wrappers tipados llevan las reglas de propiedad.

**Destacados** `JsValue`, `global`, `call_method`, `retain`, `release`.

**API** [`api/std_web_js.md`](api/std_web_js.md) · [fuente](../std/web/js.pengu)

### `std.web.dom` — elementos y listeners

**Úsalo cuando** construyas o mutéis UI: `document`, `body`, `query`, `create`,
`create_text`, `append`, `set_text`, `html`, `on`, `off`, `Listener`,
`add_class`, `has_class`, `set_attr`, `get_attr`, `form_data`, `click`,
`focus`, `free`.

**Evítalo cuando** necesites dibujar: `std.web.canvas`.

**Destacados** `query`, `create`, `set_text`, `on`, `add_class`.

**API** [`api/std_web_dom.md`](api/std_web_dom.md) · [fuente](../std/web/dom.pengu)

### `std.web.event` — accesores tipados de eventos

**Úsalo cuando** un callback de `dom.on` deba leer el evento: `key`, `code`,
`client_x`, `client_y`, `page_x`, `page_y`, `button`, `target`,
`current_target`, `prevent_default`, `stop_propagation`, `is_shift`, `is_ctrl`,
`is_alt`, `is_meta`, `data`, `clipboard_text`.

**Evítalo cuando** solo necesites saber que el evento ocurrió.

**Destacados** `key`, `target`, `prevent_default`, `stop_propagation`.

**API** [`api/std_web_event.md`](api/std_web_event.md) · [fuente](../std/web/event.pengu)

### `std.web.canvas` — Canvas 2D

**Úsalo cuando** dibujes: `context2d`, `fill_rect`, `clear_rect`, `begin_path`,
`move_to`, `line_to`, `arc`, `fill`, `stroke`, `fill_text`, `measure_text`,
`draw_image`, `get_image_data`, `fit_display`. Todos los métodos devuelven un
`result`; un elemento ausente o una excepción del navegador se convierte en
`JsError`.

**Evítalo cuando** la salida sea estructura DOM: `std.web.dom`.

**Destacados** `context2d`, `fill_rect`, `fill_text`, `draw_image`.

**API** [`api/std_web_canvas.md`](api/std_web_canvas.md) · [fuente](../std/web/canvas.pengu)

### `std.web.browser` — APIs de ventana

**Úsalo cuando** necesites comportamiento a nivel de ventana: `inner_width`,
`inner_height`, `device_pixel_ratio`, `scroll_to`, `scroll_by`, `scroll_x`,
`scroll_y`, `open_url`, `reload`, `alert`, `confirm`, `prompt`, `match_media`,
`visibility_state`, `on_resize`, `on_scroll`, `on_visibility`.

**Evítalo cuando** el cambio de URL deba pasar por el router: `std.web.router`.

**Destacados** `inner_width`, `scroll_to`, `open_url`, `on_resize`.

**API** [`api/std_web_browser.md`](api/std_web_browser.md) · [fuente](../std/web/browser.pengu)

### `std.web.location` — `window.location`

**Úsalo cuando** leas o cambies la dirección: `href`, `origin`, `protocol`,
`host`, `hostname`, `port`, `pathname`, `search`, `hash`, `assign`, `replace`,
`reload`, `set_hash`, `search_params`. `assign`/`replace` rechazan esquemas
fuera de la lista blanca de seguridad.

**Evítalo cuando** parsees una URL que ya tienes como string: `std.web.url`.

**Destacados** `href`, `hash`, `search`, `assign`, `set_hash`.

**API** [`api/std_web_location.md`](api/std_web_location.md) · [fuente](../std/web/location.pengu)

### `std.web.history` — `window.history`

**Úsalo cuando** la app gestione estado de navegación: `push_state`,
`replace_state`, `state`, `back`, `forward`, `go`, `length`, `on_pop`.

**Evítalo cuando** las rutas sean por hash y declarativas: `std.web.router`.

**Destacados** `push_state`, `state`, `back`, `on_pop`.

**API** [`api/std_web_history.md`](api/std_web_history.md) · [fuente](../std/web/history.pengu)

### `std.web.router` — rutas por hash

**Úsalo cuando** una single-page app necesite rutas: `on_change`, `navigate`,
`match`, `current_path`, `param`, `off`, `free_params`. Los patrones admiten
literales, capturas `:name` y un `*` final.

**Evítalo cuando** la app tenga una sola pantalla.

**Destacados** `on_change`, `match`, `navigate`, `param`.

**API** [`api/std_web_router.md`](api/std_web_router.md) · [fuente](../std/web/router.pengu)

### `std.web.http` — `fetch`

**Úsalo cuando** el navegador deba llamar a una API HTTP: `request`, `get`,
`post`, `post_json`, `put`, `delete`, `json`, `header`, `Response`,
`response_from`, `free`. Asíncrono: el puente entrega la respuesta mediante un
callback.

**Evítalo cuando** el código también corra nativo: `std.petitio` cubre ambos
lados del cable en el servidor.

**Destacados** `get`, `post_json`, `json`, `response_from`.

**API** [`api/std_web_http.md`](api/std_web_http.md) · [fuente](../std/web/http.pengu)

### `std.web.websocket` — cliente WebSocket tipado

**Úsalo cuando** la app necesite un canal vivo: `open`, `send`, `close`, `state`,
`count`. Mantén vivo el runtime con `set_main_loop`.

**Evítalo cuando** baste con polling: `std.web.http`.

**Destacados** `open`, `send`, `close`, `state`.

**API** [`api/std_web_websocket.md`](api/std_web_websocket.md) · [fuente](../std/web/websocket.pengu)

### `std.web.storage` — localStorage y sessionStorage

**Úsalo cuando** persistas valores pequeños en el navegador: `local_get`,
`local_set`, `local_remove`, `local_keys`, `local_clear`, las variantes `_json`
y el espejo `session_*`. Las claves ausentes devuelven `none`.

**Evítalo cuando** los datos sean grandes o estructurados: IndexedDB a través de
`std.web.js`.

**Destacados** `local_get`, `local_set`, `local_keys`, `session_set`.

**API** [`api/std_web_storage.md`](api/std_web_storage.md) · [fuente](../std/web/storage.pengu)

### `std.web.file` — elegir, leer, descargar

**Úsalo cuando** el usuario seleccione o guarde un archivo: `pick_text`,
`read_text`, `read_data_url`, `save_text`, `text_from`. La lectura es
asíncrona; `save_text` dispara una descarga normal.

**Evítalo cuando** los bytes ya estén en memoria.

**Destacados** `pick_text`, `read_text`, `save_text`.

**API** [`api/std_web_file.md`](api/std_web_file.md) · [fuente](../std/web/file.pengu)

### `std.web.clipboard` — portapapeles del sistema

**Úsalo cuando** copies o pegues texto: `read`, `write`. Ambas direcciones son
asíncronas y el navegador las condiciona a permisos.

**Evítalo cuando** el texto esté dentro de la página: `dom.set_text`.

**Destacados** `read`, `write`.

**API** [`api/std_web_clipboard.md`](api/std_web_clipboard.md) · [fuente](../std/web/clipboard.pengu)

### `std.web.crypto` — criptografía del navegador

**Úsalo cuando** el navegador deba generar o hashear secretos: `random_bytes`,
`random_int`, `uuid_v4`, `sha256_hex`, `hmac_sha256_hex`. La aleatoriedad viene
de `crypto.getRandomValues`, nunca de `Math.random`; los resúmenes son
asíncronos.

**Evítalo cuando** el código corra nativo: `std.secrets` o `std.digest`.

**Destacados** `random_bytes`, `uuid_v4`, `sha256_hex`, `hmac_sha256_hex`.

**API** [`api/std_web_crypto.md`](api/std_web_crypto.md) · [fuente](../std/web/crypto.pengu)

### `std.web.url` — parseo y codificación de URL (también nativo)

**Úsalo cuando** parsees o construyas una URL: `parse`, `to_string`, `origin`,
`params`, `param`, `query_get`, `query_set`, `query_remove`, `encode_component`,
`decode_component`, `with_path`, `with_query`, `Url`.

**Evítalo cuando** necesites navegar: `std.web.location`.

**Destacados** `parse`, `to_string`, `encode_component`, `query_get`.

**API** [`api/std_web_url.md`](api/std_web_url.md) · [fuente](../std/web/url.pengu)

### `std.web.security` — ayudas defensivas para strings (también nativo)

**Úsalo cuando** texto de usuario llegue a HTML, a una URL o a un atributo:
`escape_html`, `is_safe_url` (rechaza `javascript:`, `vbscript:`, caracteres de
control y URLs `data:` ejecutables), `starts_with_ignore_case`,
`ends_with_ignore_case`.

**Evítalo cuando** el valor nunca salga del programa.

**Destacados** `escape_html`, `is_safe_url`.

**API** [`api/std_web_security.md`](api/std_web_security.md) · [fuente](../std/web/security.pengu)

## 13. Dependencias opcionales y nativas

La mayor parte de la biblioteca estándar es PenguScript puro. Unos pocos módulos
enlazan código nativo, y solo esos traen una dependencia de enlazado — y solo
cuando se importan, porque el eliminador de código muerto quita los `declare` de
un módulo sin usar.

| Módulo | Dependencia nativa | Cómo se habilita |
| --- | --- | --- |
| `std.petitio` | libcurl | `links = ["curl"]` en `pengu.toml` |
| `std.secrets` | libsodium | `links = ["sodium"]` en `pengu.toml` |
| `std.ffi_call` | libffi | `links = ["ffi"]` en `pengu.toml` |
| `std.dynlib` | `dl` (POSIX) / `kernel32` (Windows) | automático |
| `std.chrono` | vaqt | vendorizado en `std_c/vaqt/` |
| `std.compressus` | miniz 3.1.2 | vendorizado en `std_c/miniz/` |
| `std.lingua` | utf8.h | cabecera vendorizada en `std_c/` |
| `std.regulus` | tiny-regex-c | vendorizado en `std_c/re.c` |
| `std.ffi` | ninguna (ayudas del runtime) | automático |

**Vendorizado** significa que el código fuente viaja en `std_c/` y se compila
dentro del programa; **enlazado** significa que el sistema debe aportar la
librería.

### Archivos de binding internos

Cuatro módulos guardan sus declaraciones C en un `.d.pengu` aparte:

| Wrapper (importa este) | Archivo de declaraciones (no lo importes) |
| --- | --- |
| `std.compressus` | `std/compressus.d.pengu` |
| `std.lingua` | `std/lingua.d.pengu` |
| `std.petitio` | `std/petitio.d.pengu` |
| `std.regulus` | `std/regulus.d.pengu` |

El archivo de declaraciones solo contiene `include`, `link`, `declare` y tipos de
layout. El wrapper es dueño de la API pública, del modelo de errores y de las
reglas de propiedad. Importar el `.d` directamente se salta todo eso.

## 14. El índice completo

Los 67 módulos, en orden alfabético. La capa coincide con la sección 1; la
columna API lleva a la página generada por `psc doc --include-std`.

| Módulo | Capa | Qué te da | API |
| --- | --- | --- | --- |
| `std.archivum` | Sistema | leer, escribir, copiar, recorrer archivos y directorios | [`std_archivum`](api/std_archivum.md) |
| `std.arena` | Núcleo | asignador bump para grafos de objetos con una sola vida | [`std_arena`](api/std_arena.md) |
| `std.arithmancy` | Números | `Vec2`/`Vec3`/`Vec4`, `Mat4`, `Quat`, ayudas de geometría | [`std_arithmancy`](api/std_arithmancy.md) |
| `std.atlas` | Colecciones | mapas: `get_safe`, `put`, `entries`, filtrado | [`std_atlas`](api/std_atlas.md) |
| `std.bitset` | Colecciones | conjunto de bits denso de longitud fija y álgebra de conjuntos | [`std_bitset`](api/std_bitset.md) |
| `std.builder` | Núcleo | `StringBuilder`: ensamblado lineal de strings | [`std_builder`](api/std_builder.md) |
| `std.carmen` | Formatos | registros binarios de formato fijo descritos por una fórmula | [`std_carmen`](api/std_carmen.md) |
| `std.chronicle` | Sistema | reloj de pared, calendarios, `DateTime`, duraciones | [`std_chronicle`](api/std_chronicle.md) |
| `std.chrono` | Sistema | `Instant`/`Duration` con precisión de nanosegundos (vaqt) | [`std_chrono`](api/std_chrono.md) |
| `std.cipher` | Formatos | Base64/Hex/Base32/Base58/Base85, codificación URL, CRC-32 | [`std_cipher`](api/std_cipher.md) |
| `std.compass` | Sistema | unir/partir/normalizar rutas, rune `Path` | [`std_compass`](api/std_compass.md) |
| `std.compressus` | Formatos | gzip, zlib y deflate crudo | [`std_compressus`](api/std_compressus.md) |
| `std.coven` | Colecciones | conjuntos: pertenencia, unión, intersección | [`std_coven`](api/std_coven.md) |
| `std.diagnostic` | Núcleo | spans, etiquetas y renderizado estilo compilador | [`std_diagnostic`](api/std_diagnostic.md) |
| `std.digest` | Formatos | SHA-256, HMAC-SHA-256, FNV-1a | [`std_digest`](api/std_digest.md) |
| `std.dynlib` | Interop | carga de plugins con `dlopen`/`LoadLibrary` | [`std_dynlib`](api/std_dynlib.md) |
| `std.ffi` | Interop | conversiones de strings, búferes y punteros de C | [`std_ffi`](api/std_ffi.md) |
| `std.ffi_call` | Interop | llamadas dinámicas con libffi (opcional) | [`std_ffi_call`](api/std_ffi_call.md) |
| `std.filum` | Concurrencia | `Mutex`, `WaitGroup`, `Once`, `Cond`, atómicos, canales | [`std_filum`](api/std_filum.md) |
| `std.fractio` | Números | métodos de float: `sqrt`, `pow`, trigonometría | [`std_fractio`](api/std_fractio.md) |
| `std.functor` | Núcleo | `Fn0`–`Fn3`: puntero a función más contexto | [`std_functor`](api/std_functor.md) |
| `std.integrum` | Números | métodos de enteros: gcd, primos, bits, base | [`std_integrum`](api/std_integrum.md) |
| `std.invoke` | Sistema | parser de CLI tipado: flags, opciones, subcomandos | [`std_invoke`](api/std_invoke.md) |
| `std.io` | Sistema | stdin/stdout exactos en bytes | [`std_io`](api/std_io.md) |
| `std.json` | Formatos | parser JSON estricto, DOM, JSON Pointer | [`std_json`](api/std_json.md) |
| `std.jsonrpc` | Servicios | mensajes JSON-RPC 2.0, lotes, framing LSP | [`std_jsonrpc`](api/std_jsonrpc.md) |
| `std.ledger` | Formatos | tablas CSV y TSV | [`std_ledger`](api/std_ledger.md) |
| `std.lingua` | Texto | codepoints UTF-8, validación, conteo de grafemas | [`std_lingua`](api/std_lingua.md) |
| `std.littera` | Texto | clasificación de `char` y conversión de caja | [`std_littera`](api/std_littera.md) |
| `std.logica` | Texto | conectivas de `bool`: `xor`, `implies`, `nand` | [`std_logica`](api/std_logica.md) |
| `std.loom` | Colecciones | algoritmos de listas seguros que devuelven `maybe`/`list` | [`std_loom`](api/std_loom.md) |
| `std.lot` | Números | aleatoriedad PCG32, distribuciones, muestreo | [`std_lot`](api/std_lot.md) |
| `std.memoria` | Núcleo | bloques crudos del heap: `alloc`, `copy`, `resize_array` | [`std_memoria`](api/std_memoria.md) |
| `std.net` | Sistema | sockets TCP bloqueantes | [`std_net`](api/std_net.md) |
| `std.numerus` | Números | métodos numéricos sobre el concepto `Num` | [`std_numerus`](api/std_numerus.md) |
| `std.oracle` | Núcleo | caja de herramientas `maybe`/`result` | [`std_oracle`](api/std_oracle.md) |
| `std.ordinal` | Colecciones | `LinkedList`, `OrderedMap`/`OrderedSet`, `UnorderedSet` | [`std_ordinal`](api/std_ordinal.md) |
| `std.petitio` | Servicios | cliente HTTP sobre libcurl | [`std_petitio`](api/std_petitio.md) |
| `std.regulus` | Formatos | expresiones regulares pequeñas y explícitas | [`std_regulus`](api/std_regulus.md) |
| `std.rites` | Sistema | entorno, argv, `exec`, detección de plataforma | [`std_rites`](api/std_rites.md) |
| `std.scrolls` | Texto | strings orientados a bytes: split, trim, replace, join | [`std_scrolls`](api/std_scrolls.md) |
| `std.secrets` | Interop | aleatoriedad y borrado seguro de libsodium (opcional) | [`std_secrets`](api/std_secrets.md) |
| `std.sourcemap` | Núcleo | offset de byte ↔ línea/columna | [`std_sourcemap`](api/std_sourcemap.md) |
| `std.spark` | Núcleo | E/S de consola, parseo, `panic`, `exit` | [`std_spark`](api/std_spark.md) |
| `std.tally` | Colecciones | algoritmos concretos de listas para `list of int` | [`std_tally`](api/std_tally.md) |
| `std.toml` | Formatos | parseo y stringify de TOML 1.0 | [`std_toml`](api/std_toml.md) |
| `std.trial` | Testing | suites de test y resúmenes | [`std_trial`](api/std_trial.md) |
| `std.ward` | Testing | aserciones con mensajes informativos | [`std_ward`](api/std_ward.md) |
| `std.web` | WebAssembly | consola, bucle principal, puente de navegador compartido | [`std_web`](api/std_web.md) |
| `std.whisper` | Sistema | logging por niveles, líneas JSON, loggers hijos | [`std_whisper`](api/std_whisper.md) |
| `std.yaml` | Formatos | subconjunto legado de manifiestos | [`std_yaml`](api/std_yaml.md) |
| `std.web.browser` | WebAssembly | geometría de ventana, scroll, diálogos | [`std_web_browser`](api/std_web_browser.md) |
| `std.web.canvas` | WebAssembly | dibujo en Canvas 2D | [`std_web_canvas`](api/std_web_canvas.md) |
| `std.web.clipboard` | WebAssembly | lectura y escritura del portapapeles | [`std_web_clipboard`](api/std_web_clipboard.md) |
| `std.web.crypto` | WebAssembly | CSPRNG, UUID v4, SHA-256, HMAC | [`std_web_crypto`](api/std_web_crypto.md) |
| `std.web.dom` | WebAssembly | elementos, atributos, listeners | [`std_web_dom`](api/std_web_dom.md) |
| `std.web.event` | WebAssembly | accesores tipados de eventos | [`std_web_event`](api/std_web_event.md) |
| `std.web.file` | WebAssembly | elegir, leer y descargar archivos | [`std_web_file`](api/std_web_file.md) |
| `std.web.history` | WebAssembly | push/replace/pop del historial | [`std_web_history`](api/std_web_history.md) |
| `std.web.http` | WebAssembly | HTTP basado en `fetch` | [`std_web_http`](api/std_web_http.md) |
| `std.web.js` | WebAssembly | handles `JsValue` y llamadas a JavaScript | [`std_web_js`](api/std_web_js.md) |
| `std.web.location` | WebAssembly | `window.location` | [`std_web_location`](api/std_web_location.md) |
| `std.web.router` | WebAssembly | rutas por hash | [`std_web_router`](api/std_web_router.md) |
| `std.web.security` | WebAssembly | `escape_html`, `is_safe_url` (también nativo) | [`std_web_security`](api/std_web_security.md) |
| `std.web.storage` | WebAssembly | localStorage y sessionStorage | [`std_web_storage`](api/std_web_storage.md) |
| `std.web.url` | WebAssembly | parseo, construcción y codificación de URL (también nativo) | [`std_web_url`](api/std_web_url.md) |
| `std.web.websocket` | WebAssembly | cliente WebSocket | [`std_web_websocket`](api/std_web_websocket.md) |

## Apéndice A — Chuleta de imports

```pengu-fragment
# Core
import std.spark
import std.memoria
import std.oracle
import std.builder
import std.arena
import std.functor
import std.bitset
import std.sourcemap
import std.diagnostic

# Text and numbers
import std.scrolls
import std.lingua
import std.littera
import std.logica
import std.integrum
import std.fractio
import std.numerus
import std.arithmancy
import std.lot

# Collections
import std.loom
import std.tally
import std.atlas
import std.coven
import std.ordinal

# Formats
import std.json
import std.cipher
import std.carmen
import std.toml
import std.yaml
import std.ledger
import std.compressus
import std.digest
import std.regulus

# System
import std.archivum
import std.compass
import std.rites
import std.invoke
import std.io
import std.net
import std.chronicle
import std.chrono
import std.whisper

# Testing and concurrency
import std.ward
import std.trial
import std.filum

# Services and interop
import std.petitio
import std.jsonrpc
import std.ffi
import std.ffi_call
import std.dynlib
import std.secrets

# WebAssembly
import std.web
import std.web.dom
import std.web.event
import std.web.http
import std.web.js
```

## Apéndice B — Propiedad al llamar a la biblioteca estándar

La página generada de cada símbolo lleva una nota de propiedad en su texto
`##`. Las convenciones son consistentes:

| La función devuelve | Quién lo libera |
| --- | --- |
| `string` construido por partes | quien llama, con `banish` |
| `list of T`, `map`, `Set` | quien llama; libera antes los elementos si son `string` |
| `maybe T` / `result of T to E` | quien llama es dueño del payload cuando está presente |
| un `*_view`, `bytes_view`, `source`, `html`, un handle `dom` prestado por un evento | nadie — es una vista o un handle prestado |
| un handle (`JsValue`, `Element`, `Listener`, `Socket`) | quien llama, con el `free`/`close`/`off` correspondiente |

Cuando una función toma propiedad, su nombre o su nota `##` lo dicen
(`take_*`, `consume_*`, `_owned`). En caso de duda, lee la nota de la página
generada antes de escribir el `banish`.

## Apéndice C — Convenciones de nombres en la biblioteca estándar

| Patrón | Significado |
| --- | --- |
| `get_*` | puede fallar; devuelve `maybe` |
| `get_or` | recibe un valor por defecto |
| `*_safe` | comprueba límites, devuelve `maybe` |
| `*_result` | devuelve `result` con un omen de error |
| `is_*`, `has_*` | predicados, `bool` |
| `to_*` | conversión que puede perder información |
| `*_view` | vista prestada, nunca se libera |
| `*_owned` | copia con dueño; la libera quien llama |
| `*_file` | lee o escribe una ruta en vez de un búfer |
| `*_raw` | bytes en vez de un string codificado |
