<!-- Generado por scripts/gen_stdlib_js_docs.ts a partir de std/js/. No editar a mano. -->

# Catálogo del navegador (`std/js/`)

Módulos que describen objetos que solo existen en un host JavaScript. Se
compilan únicamente con `--target js`; usarlos con `--target cpp` da **E0518**.
La sintaxis de enlace (`host`, `host global`, `host namespace`, `mut`) está en
[`cheatsheet.md`](cheatsheet.md#host-objects-browser-apis), y la forma del código
emitido en [`javascript.md`](javascript.md).

Los módulos marcados «generado» salen de `third_party/dts` con
`bun run gen:std-js` y no se editan a mano.

| Archivos | Tipos | Miembros |
| --- | --- | --- |
| 19 escritos a mano, 5 generados | 1265 | 10539 |

## Módulos escritos a mano

## `std/js/array`

Realm: `js_array`.
Invoca: `std/js/types`.

Funciones del host (`declare`, 5):

- `array_from(origen: ref<vector<any>>) -> vector<any>`
- `to_vector(origen: js::Array<any>) -> vector<any>`
- `of_size(largo: int) -> vector<any>`
- `is_array(valor: any) -> bool`
- `from_text(texto: string) -> vector<string>`

## `std/js/boolean`

Realm: `js_boolean`.
Invoca: `std/js/types`.

Funciones del host (`declare`, 2):

- `to_string(valor: bool) -> string`
- `from_number(valor: double) -> bool`

## `std/js/canvas`

Realm: `js_canvas`.
Invoca: `std/js/types`, `std/js/dom`.

Tipos del host (3):

### `js::HTMLCanvasElement → js::HTMLElement`

- `mut width: int`
- `mut height: int`
- `getContext(tipo: string) -> js::CanvasRenderingContext2D`
- `toDataURL(tipo: string) -> string`

### `js::ImageData`

- `mut width: int`
- `mut height: int`
- `mut data: js::Array<int>`

### `js::CanvasRenderingContext2D`

- `mut fillStyle: string`
- `mut strokeStyle: string`
- `mut lineWidth: double`
- `mut lineCap: string`
- `mut lineJoin: string`
- `mut font: string`
- `mut textAlign: string`
- `mut textBaseline: string`
- `mut globalAlpha: double`
- `mut globalCompositeOperation: string`
- `mut shadowBlur: double`
- `mut shadowColor: string`
- `canvas: any`
- `fillRect(x: double, y: double, ancho: double, alto: double) -> void`
- `strokeRect(x: double, y: double, ancho: double, alto: double) -> void`
- `clearRect(x: double, y: double, ancho: double, alto: double) -> void`
- `beginPath() -> void`
- `closePath() -> void`
- `moveTo(x: double, y: double) -> void`
- `lineTo(x: double, y: double) -> void`
- `bezierCurveTo(c1x: double, c1y: double, c2x: double, c2y: double, x: double, y: double) -> void`
- `quadraticCurveTo(cx: double, cy: double, x: double, y: double) -> void`
- `arc(x: double, y: double, radio: double, inicio: double, fin: double) -> void`
- `arcTo(x1: double, y1: double, x2: double, y2: double, radio: double) -> void`
- `rect(x: double, y: double, ancho: double, alto: double) -> void`
- `fill() -> void`
- `stroke() -> void`
- `clip() -> void`
- `save() -> void`
- `restore() -> void`
- `translate(x: double, y: double) -> void`
- `rotate(radianes: double) -> void`
- `scale(x: double, y: double) -> void`
- `setTransform(a: double, b: double, c: double, d: double, e: double, f: double) -> void`
- `resetTransform() -> void`
- `fillText(texto: string, x: double, y: double) -> void`
- `strokeText(texto: string, x: double, y: double) -> void`
- `measureText(texto: string) -> any`
- `createLinearGradient(x0: double, y0: double, x1: double, y1: double) -> any`
- `createRadialGradient(x0: double, y0: double, r0: double, x1: double, y1: double, r1: double) -> any`
- `createPattern(imagen: any, repeticion: string) -> any`
- `drawImage(imagen: any, x: double, y: double, ancho: double, alto: double) -> void`
- `getImageData(x: double, y: double, ancho: double, alto: double) -> js::ImageData`
- `putImageData(datos: js::ImageData, x: double, y: double) -> void`

## `std/js/console`

Realm: `js_console`.
Invoca: `std/js/types`.

Globales (1): `console: js::Console`.

Tipos del host (1):

### `js::Console`

- `log(...partes: any) -> void`
- `info(...partes: any) -> void`
- `warn(...partes: any) -> void`
- `error(...partes: any) -> void`
- `debug(...partes: any) -> void`
- `table(datos: any) -> void`
- `group(etiqueta: string) -> void`
- `group_end() -> void`
- `time(etiqueta: string) -> void`
- `time_end(etiqueta: string) -> void`
- `assert(condicion: bool, ...partes: any) -> void`
- `clear() -> void`

## `std/js/dom`

Realm: `js_dom`.
Invoca: `std/js/types`, `std/js/events`, `std/js/string`, `std/js/timers`.

Globales (1): `document: js::Document`.

Tipos del host (7):

### `js::Node → js::EventTarget`

- `nodeName: string`
- `nodeType: int`
- `parentNode: js::Node?`
- `childNodes: js::Array<js::Node>`
- `firstChild: js::Node?`
- `lastChild: js::Node?`
- `mut textContent: string`
- `appendChild(hijo: js::Node) -> js::Node`
- `removeChild(hijo: js::Node) -> js::Node`
- `insertBefore(nuevo: js::Node, referencia: js::Node?) -> js::Node`
- `replaceChild(nuevo: js::Node, viejo: js::Node) -> js::Node`
- `contains(otro: js::Node?) -> bool`
- `cloneNode(profundo: bool) -> js::Node`

### `js::Element → js::Node`

- `mut id: string`
- `mut className: string`
- `tagName: string`
- `mut innerHTML: string`
- `mut outerHTML: string`
- `getAttribute(nombre: string) -> string?`
- `setAttribute(nombre: string, valor: string) -> void`
- `removeAttribute(nombre: string) -> void`
- `hasAttribute(nombre: string) -> bool`
- `querySelector(selector: string) -> js::Element?`
- `querySelectorAll(selector: string) -> js::Array<js::Element>`
- `getBoundingClientRect() -> any`
- `scrollIntoView(alinear: bool) -> void`
- `focus() -> void`
- `blur() -> void`
- `click() -> void`

### `js::HTMLElement → js::Element`

- `mut title: string`
- `mut lang: string`
- `mut hidden: bool`
- `mut tabIndex: int`
- `mut style: any`
- `mut dataset: any`
- `mut innerText: string`
- `offsetWidth: int`
- `offsetHeight: int`

### `js::HTMLInputElement → js::HTMLElement`

- `mut value: string`
- `mut placeholder: string`
- `mut type: string`
- `mut name: string`
- `mut disabled: bool`
- `mut checked: bool`
- `mut readOnly: bool`
- `mut maxLength: int`
- `select() -> void`

### `js::HTMLImageElement → js::HTMLElement`

- `mut src: string`
- `mut alt: string`
- `mut width: int`
- `mut height: int`
- `naturalWidth: int`
- `naturalHeight: int`
- `complete: bool`

### `js::Text → js::Node`

- `mut data: string`
- `mut length: int`

### `js::Document → js::Node`

- `mut title: string`
- `mut cookie: string`
- `readyState: string`
- `documentElement: js::HTMLElement`
- `body: js::HTMLElement`
- `head: js::HTMLElement?`
- `getElementById(identificador: string) -> js::HTMLElement?`
- `getElementsByClassName(clases: string) -> js::Array<js::Element>`
- `getElementsByTagName(etiqueta: string) -> js::Array<js::Element>`
- `querySelector(selector: string) -> js::Element?`
- `querySelectorAll(selector: string) -> js::Array<js::Element>`
- `createElement(etiqueta: string) -> js::HTMLElement`
- `createElementNS(espacio: string, etiqueta: string) -> js::Element`
- `createTextNode(texto: string) -> js::Text`
- `createDocumentFragment() -> js::Node`

## `std/js/events`

Realm: `js_events`.
Invoca: `std/js/types`.

Tipos del host (2):

### `js::Event`

- `type: string`
- `target: any`
- `prevent_default() -> void`
- `stop_propagation() -> void`

### `js::EventTarget`

- `addEventListener(tipo: string, listener: function<(js::Event) -> void>) -> void`
- `removeEventListener(tipo: string, listener: function<(js::Event) -> void>) -> void`
- `dispatchEvent(evento: js::Event) -> bool`

## `std/js/fetch`

Realm: `js_fetch`.
Invoca: `std/js/types`.

Funciones del host (`declare`, 2):

- `fetch(url: string) -> future<js::Response>`
- `fetch_with(url: string, opciones: js::RequestInit) -> future<js::Response>`

Tipos del host (3):

### `js::Headers`

- `get(nombre: string) -> string?`
- `has(nombre: string) -> bool`
- `set(nombre: string, valor: string) -> void`

### `js::Response`

- `status: int`
- `statusText: string`
- `ok: bool`
- `url: string`
- `headers: js::Headers`
- `text() -> future<string>`
- `json() -> future<any>`
- `arrayBuffer() -> future<js::ArrayBuffer>`

### `js::RequestInit`

- `method: string`
- `headers: js::Headers?`
- `body: any`
- `mode: string`
- `cache: string`
- `credentials: string`
- `signal: any`

## `std/js/map`

Realm: `js_map`.
Invoca: `std/js/types`.

Funciones del host (`declare`, 1):

- `map_new() -> js::Map<any, any>`

Tipos del host (1):

### `js::Map`

- `size: int`
- `get(clave: K) -> V?`
- `set(clave: K, valor: V) -> void`
- `has(clave: K) -> bool`
- `delete(clave: K) -> bool`
- `clear() -> void`
- `keys() -> js::Iterable<K>`
- `values() -> js::Iterable<V>`

## `std/js/math`

Realm: `js_math`.

Namespaces: `Math` (43 miembro(s)).

## `std/js/number`

Realm: `js_number`.
Invoca: `std/js/types`.

Funciones del host (`declare`, 16):

- `parse_int(texto: string, base: int) -> double`
- `parse_float(texto: string) -> double`
- `is_nan(valor: double) -> bool`
- `is_finite(valor: double) -> bool`
- `is_integer(valor: double) -> bool`
- `is_safe_integer(valor: double) -> bool`
- `to_fixed(valor: double, digitos: int) -> string`
- `to_precision(valor: double, digitos: int) -> string`
- `to_exponential(valor: double, digitos: int) -> string`
- `to_string(valor: double) -> string`
- `max_value() -> double`
- `min_value() -> double`
- `epsilon() -> double`
- `max_safe_integer() -> double`
- `positive_infinity() -> double`
- `negative_infinity() -> double`

## `std/js/object`

Realm: `js_object`.
Invoca: `std/js/types`.

Funciones del host (`declare`, 8):

- `keys(objeto: any) -> vector<string>`
- `values(objeto: any) -> vector<any>`
- `entries(objeto: any) -> vector<vector<any>>`
- `has_key(objeto: any, clave: string) -> bool`
- `from_entries(entradas: vector<vector<any>>) -> any`
- `freeze(objeto: any) -> any`
- `json_parse(texto: string) -> any`
- `json_stringify(valor: any) -> string`

## `std/js/performance`

Realm: `js_performance`.
Invoca: `std/js/types`.

Globales (1): `performance: js::Performance`.

Tipos del host (2):

### `js::PerformanceEntry`

- `mut name: string`
- `entryType: string`
- `startTime: double`
- `duration: double`

### `js::Performance`

- `timeOrigin: double`
- `now() -> double`
- `mark(nombre: string) -> void`
- `measure(nombre: string, inicio: string?, fin: string?) -> void`
- `getEntries() -> js::Array<js::PerformanceEntry>`
- `getEntriesByName(nombre: string) -> js::Array<js::PerformanceEntry>`
- `clearMarks(nombre: string) -> void`

## `std/js/promise`

Realm: `js_promise`.
Invoca: `std/js/types`.

Funciones del host (`declare`, 6):

- `resolve(valor: any) -> future<any>`
- `reject(motivo: any) -> future<any>`
- `all(promesas: vector<future<any>>) -> future<vector<any>>`
- `all_settled(promesas: vector<future<any>>) -> future<vector<any>>`
- `race(promesas: vector<future<any>>) -> future<any>`
- `any_of(promesas: vector<future<any>>) -> future<any>`

## `std/js/set`

Realm: `js_set`.
Invoca: `std/js/types`.

Funciones del host (`declare`, 1):

- `set_new() -> js::Set<any>`

Tipos del host (1):

### `js::Set`

- `size: int`
- `add(valor: T) -> void`
- `has(valor: T) -> bool`
- `delete(valor: T) -> bool`
- `clear() -> void`
- `values() -> js::Iterable<T>`

## `std/js/storage`

Realm: `js_storage`.
Invoca: `std/js/types`.

Globales (2): `localStorage: js::Storage`, `sessionStorage: js::Storage`.

Tipos del host (1):

### `js::Storage`

- `length: int`
- `getItem(clave: string) -> string?`
- `setItem(clave: string, valor: string) -> void`
- `removeItem(clave: string) -> void`
- `clear() -> void`
- `key(indice: int) -> string?`

## `std/js/string`

Realm: `js_string`.
Invoca: `std/js/types`.

Funciones del host (`declare`, 21):

- `from_char_code(codigo: int) -> string`
- `to_upper(texto: string) -> string`
- `to_lower(texto: string) -> string`
- `trim(texto: string) -> string`
- `trim_start(texto: string) -> string`
- `trim_end(texto: string) -> string`
- `char_at(texto: string, posicion: int) -> string`
- `includes(texto: string, buscado: string) -> bool`
- `starts_with(texto: string, buscado: string) -> bool`
- `ends_with(texto: string, buscado: string) -> bool`
- `index_of(texto: string, buscado: string) -> int`
- `last_index_of(texto: string, buscado: string) -> int`
- `split(texto: string, separador: string) -> vector<string>`
- `slice(texto: string, inicio: int, fin: int) -> string`
- `substring(texto: string, inicio: int, fin: int) -> string`
- `replace(texto: string, buscado: string, nuevo: string) -> string`
- `repeat_text(texto: string, veces: int) -> string`
- `pad_start(texto: string, largo: int, relleno: string) -> string`
- `pad_end(texto: string, largo: int, relleno: string) -> string`
- `encode_uri_component(texto: string) -> string`
- `decode_uri_component(texto: string) -> string`

## `std/js/timers`

Realm: `js_timers`.
Invoca: `std/js/types`.

Funciones del host (`declare`, 8):

- `set_timeout(funcion: function<() -> void>, milisegundos: int) -> int`
- `set_interval(funcion: function<() -> void>, milisegundos: int) -> int`
- `clear_timeout(identificador: int) -> void`
- `clear_interval(identificador: int) -> void`
- `request_animation_frame(funcion: function<(double) -> void>) -> int`
- `cancel_animation_frame(identificador: int) -> void`
- `queue_microtask(funcion: function<() -> void>) -> void`
- `delay(milisegundos: int) -> future<void>`

## `std/js/types`

Realm: `js_types`.

Alias (3): `echo js::String = string`, `echo js::Number = double`, `echo js::Boolean = bool`.

Tipos del host (9):

### `js::Any`

Sin miembros declarados.

### `js::Array`

- `mut length: int`
- `[indice: int]: T`
- `push(valor: T) -> int`
- `pop() -> T?`
- `join(separador: js::String) -> string`
- `indexOf(valor: T) -> int`
- `includes(valor: T) -> bool`
- `slice(inicio: int, fin: int) -> js::Array<T>`
- `map(funcion: function<(T, int) -> T>) -> js::Array<T>`
- `forEach(funcion: function<(T, int) -> void>) -> void`

### `js::Object`

- `[clave: string]: js::Any`

### `js::Function`

Sin miembros declarados.

### `js::ArrayBuffer`

Sin miembros declarados.

### `js::Uint8Array`

- `[indice: int]: int`
- `mut length: int`

### `js::Error`

- `mut message: string`
- `mut name: string`

### `js::Iterable`

Sin miembros declarados.

### `js::Promise`

Sin miembros declarados.

## `std/js/url`

Realm: `js_url`.
Invoca: `std/js/types`.

Tipos del host (2):

### `js::URLSearchParams`

- `get(clave: string) -> string?`
- `getAll(clave: string) -> js::Array<string>`
- `has(clave: string) -> bool`
- `set(clave: string, valor: string) -> void`
- `append(clave: string, valor: string) -> void`
- `delete(clave: string) -> void`
- `sort() -> void`
- `toString() -> string`
- `constructor()`

### `js::URL`

- `mut href: string`
- `mut protocol: string`
- `mut host: string`
- `mut hostname: string`
- `mut port: string`
- `mut pathname: string`
- `mut search: string`
- `mut hash: string`
- `origin: string`
- `username: string`
- `password: string`
- `searchParams: js::URLSearchParams`
- `toString() -> string`
- `toJSON() -> string`
- `constructor(url: string, base: string?)`
- `static createObjectURL(objeto: js::Any) -> string`
- `static revokeObjectURL(url: string) -> void`
- `static canParse(url: string) -> bool`

## Módulos generados

## `std/js/dom_generated`

Generado con `pengu ts-bindgen`; no editar a mano.

Realm: `js_dom_generated`.
Invoca: `std/js/types`.

Alias (31): `echo js::SVGMatrix = js::DOMMatrix`, `echo js::WebKitCSSMatrix = js::DOMMatrix`, `echo js::SVGPoint = js::DOMPoint`, `echo js::SVGRect = js::DOMRect`, `echo js::webkitURL = js::URL`, `echo js::ElementTagNameMap = js::HTMLElementTagNameMap`, `echo js::Base64URLString = string`, `echo js::COSEAlgorithmIdentifier = double`, `echo js::DOMHighResTimeStamp = double`, `echo js::EpochTimeStamp = double` … y 21 más.

Globales (171): `console: js::Console`, `clientInformation: js::Navigator`, `closed: bool`, `customElements: js::CustomElementRegistry`, `devicePixelRatio: double`, `document: js::Document`, `event: js::Event?`, `external: js::External`, `frameElement: js::Element?`, `frames: js::WindowProxy`, `history: js::History`, `innerHeight: double` … y 159 más.

Namespaces: `CSS` (67 miembro(s)), `WebAssembly` (14 miembro(s)).

Funciones del host (`declare`, 41):

- `alert(message: any?) -> void`
- `blur() -> void`
- `cancelIdleCallback(handle: double) -> void`
- `captureEvents() -> void`
- `close() -> void`
- `confirm(message: string?) -> bool`
- `focus() -> void`
- `getComputedStyle(elt: js::Element, pseudoElt: string??) -> js::CSSStyleDeclaration`
- `getSelection() -> js::Selection?`
- `matchMedia(query: string) -> js::MediaQueryList`
- `moveBy(x: double, y: double) -> void`
- `moveTo(x: double, y: double) -> void`
- … y 29 más (ver el `.d.pengu`)

Tipos del host (1123, 9533 miembro(s)):

- `js::AddEventListenerOptions → js::EventListenerOptions` (3 miembro(s))
- `js::AddressErrors` (10 miembro(s))
- `js::AesCbcParams → js::Algorithm` (1 miembro(s))
- `js::AesCtrParams → js::Algorithm` (2 miembro(s))
- `js::AesDerivedKeyParams → js::Algorithm` (1 miembro(s))
- `js::AesGcmParams → js::Algorithm` (3 miembro(s))
- `js::AesKeyAlgorithm → js::KeyAlgorithm` (1 miembro(s))
- `js::AesKeyGenParams → js::Algorithm` (1 miembro(s))
- `js::Algorithm` (1 miembro(s))
- `js::AnalyserOptions → js::AudioNodeOptions` (4 miembro(s))
- `js::AnimationEventInit → js::EventInit` (3 miembro(s))
- `js::AnimationPlaybackEventInit → js::EventInit` (2 miembro(s))
- `js::AssignedNodesOptions` (1 miembro(s))
- `js::AudioBufferOptions` (3 miembro(s))
- `js::AudioBufferSourceOptions` (6 miembro(s))
- `js::AudioConfiguration` (5 miembro(s))
- `js::AudioContextOptions` (2 miembro(s))
- `js::AudioDataCopyToOptions` (4 miembro(s))
- `js::AudioDataInit` (7 miembro(s))
- `js::AudioDecoderConfig` (4 miembro(s))
- `js::AudioDecoderInit` (2 miembro(s))
- `js::AudioDecoderSupport` (2 miembro(s))
- `js::AudioEncoderConfig` (6 miembro(s))
- `js::AudioEncoderInit` (2 miembro(s))
- `js::AudioEncoderSupport` (2 miembro(s))
- `js::AudioNodeOptions` (3 miembro(s))
- `js::AudioProcessingEventInit → js::EventInit` (3 miembro(s))
- `js::AudioTimestamp` (2 miembro(s))
- `js::AudioWorkletNodeOptions → js::AudioNodeOptions` (5 miembro(s))
- `js::AuthenticationExtensionsClientInputs` (5 miembro(s))
- `js::AuthenticationExtensionsClientOutputs` (4 miembro(s))
- `js::AuthenticationExtensionsPRFInputs` (2 miembro(s))
- `js::AuthenticationExtensionsPRFOutputs` (2 miembro(s))
- `js::AuthenticationExtensionsPRFValues` (2 miembro(s))
- `js::AuthenticatorSelectionCriteria` (4 miembro(s))
- `js::AvcEncoderConfig` (1 miembro(s))
- `js::BiquadFilterOptions → js::AudioNodeOptions` (5 miembro(s))
- `js::BlobEventInit` (2 miembro(s))
- `js::BlobPropertyBag` (2 miembro(s))
- `js::CSSMatrixComponentOptions` (1 miembro(s))
- `js::CSSNumericType` (8 miembro(s))
- `js::CSSStyleSheetInit` (3 miembro(s))
- `js::CacheQueryOptions` (3 miembro(s))
- `js::CanvasRenderingContext2DSettings` (4 miembro(s))
- `js::CaretPositionFromPointOptions` (1 miembro(s))
- `js::ChannelMergerOptions → js::AudioNodeOptions` (1 miembro(s))
- `js::ChannelSplitterOptions → js::AudioNodeOptions` (1 miembro(s))
- `js::CheckVisibilityOptions` (5 miembro(s))
- `js::ClientQueryOptions` (2 miembro(s))
- `js::ClipboardEventInit → js::EventInit` (1 miembro(s))
- `js::ClipboardItemOptions` (1 miembro(s))
- `js::CloseEventInit → js::EventInit` (3 miembro(s))
- `js::CompositionEventInit → js::UIEventInit` (1 miembro(s))
- `js::ComputedEffectTiming → js::EffectTiming` (6 miembro(s))
- `js::ComputedKeyframe` (5 miembro(s))
- `js::ConstantSourceOptions` (1 miembro(s))
- `js::ConstrainBooleanParameters` (2 miembro(s))
- `js::ConstrainDOMStringParameters` (2 miembro(s))
- `js::ConstrainDoubleRange → js::DoubleRange` (2 miembro(s))
- `js::ConstrainULongRange → js::ULongRange` (2 miembro(s))
- `js::ContentVisibilityAutoStateChangeEventInit → js::EventInit` (1 miembro(s))
- `js::ConvolverOptions → js::AudioNodeOptions` (2 miembro(s))
- `js::CredentialCreationOptions` (2 miembro(s))
- `js::CredentialPropertiesOutput` (1 miembro(s))
- `js::CredentialRequestOptions` (3 miembro(s))
- `js::CryptoKeyPair` (2 miembro(s))
- `js::CustomEventInit → js::EventInit` (1 miembro(s))
- `js::DOMMatrix2DInit` (12 miembro(s))
- `js::DOMMatrixInit → js::DOMMatrix2DInit` (11 miembro(s))
- `js::DOMPointInit` (4 miembro(s))
- `js::DOMQuadInit` (4 miembro(s))
- `js::DOMRectInit` (4 miembro(s))
- `js::DelayOptions → js::AudioNodeOptions` (2 miembro(s))
- `js::DeviceMotionEventAccelerationInit` (3 miembro(s))
- `js::DeviceMotionEventInit → js::EventInit` (4 miembro(s))
- `js::DeviceMotionEventRotationRateInit` (3 miembro(s))
- `js::DeviceOrientationEventInit → js::EventInit` (4 miembro(s))
- `js::DisplayMediaStreamOptions` (2 miembro(s))
- `js::DocumentTimelineOptions` (1 miembro(s))
- `js::DoubleRange` (2 miembro(s))
- `js::DragEventInit → js::MouseEventInit` (1 miembro(s))
- `js::DynamicsCompressorOptions → js::AudioNodeOptions` (5 miembro(s))
- `js::EcKeyAlgorithm → js::KeyAlgorithm` (1 miembro(s))
- `js::EcKeyGenParams → js::Algorithm` (1 miembro(s))
- `js::EcKeyImportParams → js::Algorithm` (1 miembro(s))
- `js::EcdhKeyDeriveParams → js::Algorithm` (1 miembro(s))
- `js::EcdsaParams → js::Algorithm` (1 miembro(s))
- `js::EffectTiming` (9 miembro(s))
- `js::ElementCreationOptions` (1 miembro(s))
- `js::ElementDefinitionOptions` (1 miembro(s))
- `js::EncodedAudioChunkInit` (5 miembro(s))
- `js::EncodedAudioChunkMetadata` (1 miembro(s))
- `js::EncodedVideoChunkInit` (4 miembro(s))
- `js::EncodedVideoChunkMetadata` (1 miembro(s))
- `js::ErrorEventInit → js::EventInit` (5 miembro(s))
- `js::EventInit` (3 miembro(s))
- `js::EventListenerOptions` (1 miembro(s))
- `js::EventModifierInit → js::UIEventInit` (14 miembro(s))
- `js::EventSourceInit` (1 miembro(s))
- `js::FilePropertyBag → js::BlobPropertyBag` (1 miembro(s))
- `js::FileSystemCreateWritableOptions` (1 miembro(s))
- `js::FileSystemFlags` (2 miembro(s))
- `js::FileSystemGetDirectoryOptions` (1 miembro(s))
- `js::FileSystemGetFileOptions` (1 miembro(s))
- `js::FileSystemRemoveOptions` (1 miembro(s))
- `js::FocusEventInit → js::UIEventInit` (1 miembro(s))
- `js::FocusOptions` (1 miembro(s))
- `js::FontFaceDescriptors` (9 miembro(s))
- `js::FontFaceSetLoadEventInit → js::EventInit` (1 miembro(s))
- `js::FormDataEventInit → js::EventInit` (1 miembro(s))
- `js::FullscreenOptions` (1 miembro(s))
- `js::GainOptions → js::AudioNodeOptions` (1 miembro(s))
- `js::GamepadEffectParameters` (6 miembro(s))
- `js::GamepadEventInit → js::EventInit` (1 miembro(s))
- `js::GetAnimationsOptions` (1 miembro(s))
- `js::GetHTMLOptions` (2 miembro(s))
- `js::GetNotificationOptions` (1 miembro(s))
- `js::GetRootNodeOptions` (1 miembro(s))
- `js::HashChangeEventInit → js::EventInit` (2 miembro(s))
- `js::HkdfParams → js::Algorithm` (3 miembro(s))
- `js::HmacImportParams → js::Algorithm` (2 miembro(s))
- `js::HmacKeyAlgorithm → js::KeyAlgorithm` (2 miembro(s))
- `js::HmacKeyGenParams → js::Algorithm` (2 miembro(s))
- `js::IDBDatabaseInfo` (2 miembro(s))
- `js::IDBIndexParameters` (2 miembro(s))
- `js::IDBObjectStoreParameters` (2 miembro(s))
- `js::IDBTransactionOptions` (1 miembro(s))
- `js::IDBVersionChangeEventInit → js::EventInit` (2 miembro(s))
- `js::IIRFilterOptions → js::AudioNodeOptions` (2 miembro(s))
- `js::IdleRequestOptions` (1 miembro(s))
- `js::ImageBitmapOptions` (6 miembro(s))
- `js::ImageBitmapRenderingContextSettings` (1 miembro(s))
- `js::ImageDataSettings` (1 miembro(s))
- `js::ImageEncodeOptions` (2 miembro(s))
- `js::InputEventInit → js::UIEventInit` (5 miembro(s))
- `js::IntersectionObserverInit` (3 miembro(s))
- `js::JsonWebKey` (18 miembro(s))
- `js::KeyAlgorithm` (1 miembro(s))
- `js::KeyboardEventInit → js::EventModifierInit` (7 miembro(s))
- `js::Keyframe` (4 miembro(s))
- `js::KeyframeAnimationOptions → js::KeyframeEffectOptions` (2 miembro(s))
- `js::KeyframeEffectOptions → js::EffectTiming` (3 miembro(s))
- `js::LockInfo` (3 miembro(s))
- `js::LockManagerSnapshot` (2 miembro(s))
- `js::LockOptions` (4 miembro(s))
- `js::MIDIConnectionEventInit → js::EventInit` (1 miembro(s))
- `js::MIDIMessageEventInit → js::EventInit` (1 miembro(s))
- `js::MIDIOptions` (2 miembro(s))
- `js::MediaCapabilitiesDecodingInfo → js::MediaCapabilitiesInfo` (1 miembro(s))
- `js::MediaCapabilitiesEncodingInfo → js::MediaCapabilitiesInfo` (1 miembro(s))
- `js::MediaCapabilitiesInfo` (3 miembro(s))
- `js::MediaConfiguration` (2 miembro(s))
- `js::MediaDecodingConfiguration → js::MediaConfiguration` (1 miembro(s))
- `js::MediaElementAudioSourceOptions` (1 miembro(s))
- `js::MediaEncodingConfiguration → js::MediaConfiguration` (1 miembro(s))
- `js::MediaEncryptedEventInit → js::EventInit` (2 miembro(s))
- `js::MediaImage` (3 miembro(s))
- `js::MediaKeyMessageEventInit → js::EventInit` (2 miembro(s))
- `js::MediaKeySystemConfiguration` (7 miembro(s))
- `js::MediaKeySystemMediaCapability` (3 miembro(s))
- `js::MediaKeysPolicy` (1 miembro(s))
- `js::MediaMetadataInit` (4 miembro(s))
- `js::MediaPositionState` (3 miembro(s))
- `js::MediaQueryListEventInit → js::EventInit` (2 miembro(s))
- `js::MediaRecorderOptions` (4 miembro(s))
- `js::MediaSessionActionDetails` (4 miembro(s))
- `js::MediaStreamAudioSourceOptions` (1 miembro(s))
- `js::MediaStreamConstraints` (4 miembro(s))
- `js::MediaStreamTrackEventInit → js::EventInit` (1 miembro(s))
- `js::MediaTrackCapabilities` (15 miembro(s))
- `js::MediaTrackConstraintSet` (15 miembro(s))
- `js::MediaTrackConstraints → js::MediaTrackConstraintSet` (1 miembro(s))
- `js::MediaTrackSettings` (15 miembro(s))
- `js::MediaTrackSupportedConstraints` (15 miembro(s))
- `js::MessageEventInit → js::EventInit` (5 miembro(s))
- `js::MouseEventInit → js::EventModifierInit` (9 miembro(s))
- `js::MultiCacheQueryOptions → js::CacheQueryOptions` (1 miembro(s))
- `js::MutationObserverInit` (7 miembro(s))
- `js::NavigationPreloadState` (2 miembro(s))
- `js::NotificationOptions` (9 miembro(s))
- `js::OfflineAudioCompletionEventInit → js::EventInit` (1 miembro(s))
- `js::OfflineAudioContextOptions` (3 miembro(s))
- `js::OptionalEffectTiming` (9 miembro(s))
- `js::OpusEncoderConfig` (6 miembro(s))
- `js::OscillatorOptions → js::AudioNodeOptions` (4 miembro(s))
- `js::PageTransitionEventInit → js::EventInit` (1 miembro(s))
- `js::PannerOptions → js::AudioNodeOptions` (14 miembro(s))
- `js::PayerErrors` (3 miembro(s))
- `js::PaymentCurrencyAmount` (2 miembro(s))
- `js::PaymentDetailsBase` (3 miembro(s))
- `js::PaymentDetailsInit → js::PaymentDetailsBase` (2 miembro(s))
- `js::PaymentDetailsModifier` (4 miembro(s))
- `js::PaymentDetailsUpdate → js::PaymentDetailsBase` (4 miembro(s))
- `js::PaymentItem` (3 miembro(s))
- `js::PaymentMethodChangeEventInit` (2 miembro(s))
- `js::PaymentMethodData` (2 miembro(s))
- `js::PaymentOptions` (5 miembro(s))
- `js::PaymentShippingOption` (4 miembro(s))
- `js::PaymentValidationErrors` (3 miembro(s))
- `js::Pbkdf2Params → js::Algorithm` (3 miembro(s))
- `js::PerformanceMarkOptions` (2 miembro(s))
- `js::PerformanceMeasureOptions` (4 miembro(s))
- `js::PerformanceObserverInit` (3 miembro(s))
- `js::PeriodicWaveConstraints` (1 miembro(s))
- `js::PeriodicWaveOptions → js::PeriodicWaveConstraints` (2 miembro(s))
- `js::PermissionDescriptor` (1 miembro(s))
- `js::PictureInPictureEventInit → js::EventInit` (1 miembro(s))
- `js::PlaneLayout` (2 miembro(s))
- `js::PointerEventInit → js::MouseEventInit` (14 miembro(s))
- `js::PointerLockOptions` (1 miembro(s))
- `js::PopStateEventInit → js::EventInit` (1 miembro(s))
- `js::PositionOptions` (3 miembro(s))
- `js::ProgressEventInit → js::EventInit` (3 miembro(s))
- `js::PromiseRejectionEventInit → js::EventInit` (2 miembro(s))
- `js::PropertyDefinition` (4 miembro(s))
- `js::PropertyIndexedKeyframes` (4 miembro(s))
- `js::PublicKeyCredentialCreationOptions` (9 miembro(s))
- `js::PublicKeyCredentialCreationOptionsJSON` (10 miembro(s))
- `js::PublicKeyCredentialDescriptor` (3 miembro(s))
- `js::PublicKeyCredentialDescriptorJSON` (3 miembro(s))
- `js::PublicKeyCredentialEntity` (1 miembro(s))
- `js::PublicKeyCredentialParameters` (2 miembro(s))
- `js::PublicKeyCredentialRequestOptions` (6 miembro(s))
- `js::PublicKeyCredentialRequestOptionsJSON` (7 miembro(s))
- `js::PublicKeyCredentialRpEntity → js::PublicKeyCredentialEntity` (1 miembro(s))
- `js::PublicKeyCredentialUserEntity → js::PublicKeyCredentialEntity` (2 miembro(s))
- `js::PublicKeyCredentialUserEntityJSON` (3 miembro(s))
- `js::PushSubscriptionJSON` (3 miembro(s))
- `js::PushSubscriptionOptionsInit` (2 miembro(s))
- `js::QueuingStrategy` (2 miembro(s))
- `js::QueuingStrategyInit` (1 miembro(s))
- `js::RTCCertificateExpiration` (1 miembro(s))
- `js::RTCConfiguration` (6 miembro(s))
- `js::RTCDTMFToneChangeEventInit → js::EventInit` (1 miembro(s))
- `js::RTCDataChannelEventInit → js::EventInit` (1 miembro(s))
- `js::RTCDataChannelInit` (6 miembro(s))
- `js::RTCDtlsFingerprint` (2 miembro(s))
- `js::RTCEncodedAudioFrameMetadata` (4 miembro(s))
- `js::RTCEncodedVideoFrameMetadata` (10 miembro(s))
- `js::RTCErrorEventInit → js::EventInit` (1 miembro(s))
- `js::RTCErrorInit` (6 miembro(s))
- `js::RTCIceCandidateInit` (4 miembro(s))
- `js::RTCIceCandidatePairStats → js::RTCStats` (17 miembro(s))
- `js::RTCIceServer` (3 miembro(s))
- `js::RTCInboundRtpStreamStats → js::RTCReceivedRtpStreamStats` (37 miembro(s))
- `js::RTCLocalSessionDescriptionInit` (2 miembro(s))
- `js::RTCOfferOptions` (3 miembro(s))
- `js::RTCOutboundRtpStreamStats → js::RTCSentRtpStreamStats` (23 miembro(s))
- `js::RTCPeerConnectionIceErrorEventInit → js::EventInit` (5 miembro(s))
- `js::RTCPeerConnectionIceEventInit → js::EventInit` (2 miembro(s))
- `js::RTCReceivedRtpStreamStats → js::RTCRtpStreamStats` (3 miembro(s))
- `js::RTCRtcpParameters` (2 miembro(s))
- `js::RTCRtpCapabilities` (2 miembro(s))
- `js::RTCRtpCodec` (4 miembro(s))
- `js::RTCRtpCodecParameters → js::RTCRtpCodec` (1 miembro(s))
- `js::RTCRtpCodingParameters` (1 miembro(s))
- `js::RTCRtpContributingSource` (4 miembro(s))
- `js::RTCRtpEncodingParameters → js::RTCRtpCodingParameters` (6 miembro(s))
- `js::RTCRtpHeaderExtensionCapability` (1 miembro(s))
- `js::RTCRtpHeaderExtensionParameters` (3 miembro(s))
- `js::RTCRtpParameters` (3 miembro(s))
- `js::RTCRtpSendParameters → js::RTCRtpParameters` (3 miembro(s))
- `js::RTCRtpStreamStats → js::RTCStats` (4 miembro(s))
- `js::RTCRtpTransceiverInit` (3 miembro(s))
- `js::RTCSentRtpStreamStats → js::RTCRtpStreamStats` (2 miembro(s))
- `js::RTCSessionDescriptionInit` (2 miembro(s))
- `js::RTCStats` (3 miembro(s))
- `js::RTCTrackEventInit → js::EventInit` (4 miembro(s))
- `js::RTCTransportStats → js::RTCStats` (9 miembro(s))
- `js::ReadableStreamGetReaderOptions` (1 miembro(s))
- `js::ReadableStreamIteratorOptions` (1 miembro(s))
- `js::ReadableStreamReadDoneResult` (2 miembro(s))
- `js::ReadableStreamReadValueResult` (2 miembro(s))
- `js::ReadableWritablePair` (2 miembro(s))
- `js::RegistrationOptions` (3 miembro(s))
- `js::ReportingObserverOptions` (2 miembro(s))
- `js::RequestInit` (14 miembro(s))
- `js::ResizeObserverOptions` (1 miembro(s))
- `js::ResponseInit` (3 miembro(s))
- `js::RsaHashedImportParams → js::Algorithm` (1 miembro(s))
- `js::RsaHashedKeyAlgorithm → js::RsaKeyAlgorithm` (1 miembro(s))
- `js::RsaHashedKeyGenParams → js::RsaKeyGenParams` (1 miembro(s))
- `js::RsaKeyAlgorithm → js::KeyAlgorithm` (2 miembro(s))
- `js::RsaKeyGenParams → js::Algorithm` (2 miembro(s))
- `js::RsaOaepParams → js::Algorithm` (1 miembro(s))
- `js::RsaOtherPrimesInfo` (3 miembro(s))
- `js::RsaPssParams → js::Algorithm` (1 miembro(s))
- `js::SVGBoundingBoxOptions` (4 miembro(s))
- `js::ScrollIntoViewOptions → js::ScrollOptions` (2 miembro(s))
- `js::ScrollOptions` (1 miembro(s))
- `js::ScrollToOptions → js::ScrollOptions` (2 miembro(s))
- `js::SecurityPolicyViolationEventInit → js::EventInit` (12 miembro(s))
- `js::ShadowRootInit` (4 miembro(s))
- `js::ShareData` (4 miembro(s))
- `js::SpeechSynthesisErrorEventInit → js::SpeechSynthesisEventInit` (1 miembro(s))
- `js::SpeechSynthesisEventInit → js::EventInit` (5 miembro(s))
- `js::StaticRangeInit` (4 miembro(s))
- `js::StereoPannerOptions → js::AudioNodeOptions` (1 miembro(s))
- `js::StorageEstimate` (2 miembro(s))
- `js::StorageEventInit → js::EventInit` (5 miembro(s))
- `js::StreamPipeOptions` (4 miembro(s))
- `js::StructuredSerializeOptions` (1 miembro(s))
- `js::SubmitEventInit → js::EventInit` (1 miembro(s))
- `js::TextDecodeOptions` (1 miembro(s))
- `js::TextDecoderOptions` (2 miembro(s))
- `js::TextEncoderEncodeIntoResult` (2 miembro(s))
- `js::ToggleEventInit → js::EventInit` (2 miembro(s))
- `js::TouchEventInit → js::EventModifierInit` (3 miembro(s))
- `js::TouchInit` (15 miembro(s))
- `js::TrackEventInit → js::EventInit` (1 miembro(s))
- `js::Transformer` (5 miembro(s))
- `js::TransitionEventInit → js::EventInit` (3 miembro(s))
- `js::UIEventInit → js::EventInit` (3 miembro(s))
- `js::ULongRange` (2 miembro(s))
- `js::UnderlyingByteSource` (5 miembro(s))
- `js::UnderlyingDefaultSource` (4 miembro(s))
- `js::UnderlyingSink` (5 miembro(s))
- `js::UnderlyingSource` (5 miembro(s))
- `js::ValidityStateFlags` (10 miembro(s))
- `js::VideoColorSpaceInit` (4 miembro(s))
- `js::VideoConfiguration` (10 miembro(s))
- `js::VideoDecoderConfig` (9 miembro(s))
- `js::VideoDecoderInit` (2 miembro(s))
- `js::VideoDecoderSupport` (2 miembro(s))
- `js::VideoEncoderConfig` (14 miembro(s))
- `js::VideoEncoderEncodeOptions` (2 miembro(s))
- `js::VideoEncoderEncodeOptionsForAvc` (1 miembro(s))
- `js::VideoEncoderInit` (2 miembro(s))
- `js::VideoEncoderSupport` (2 miembro(s))
- `js::VideoFrameBufferInit` (10 miembro(s))
- `js::VideoFrameCallbackMetadata` (10 miembro(s))
- `js::VideoFrameCopyToOptions` (4 miembro(s))
- `js::VideoFrameInit` (6 miembro(s))
- `js::WaveShaperOptions → js::AudioNodeOptions` (2 miembro(s))
- `js::WebGLContextAttributes` (9 miembro(s))
- `js::WebGLContextEventInit → js::EventInit` (1 miembro(s))
- `js::WebTransportCloseInfo` (2 miembro(s))
- `js::WebTransportErrorOptions` (2 miembro(s))
- `js::WebTransportHash` (2 miembro(s))
- `js::WebTransportOptions` (4 miembro(s))
- `js::WebTransportSendStreamOptions` (1 miembro(s))
- `js::WheelEventInit → js::MouseEventInit` (4 miembro(s))
- `js::WindowPostMessageOptions → js::StructuredSerializeOptions` (1 miembro(s))
- `js::WorkerOptions` (3 miembro(s))
- `js::WorkletOptions` (1 miembro(s))
- `js::WriteParams` (4 miembro(s))
- `js::ANGLE_instanced_arrays` (4 miembro(s))
- `js::ARIAMixin` (43 miembro(s))
- `js::AbortController` (2 miembro(s))
- `js::AbortSignalEventMap` (1 miembro(s))
- `js::AbortSignal → js::EventTarget` (6 miembro(s))
- `js::AbstractRange` (5 miembro(s))
- `js::AbstractWorkerEventMap` (1 miembro(s))
- `js::AbstractWorker` (3 miembro(s))
- `js::AnalyserNode → js::AudioNode` (9 miembro(s))
- `js::Animatable` (2 miembro(s))
- `js::AnimationEventMap` (3 miembro(s))
- `js::Animation → js::EventTarget` (24 miembro(s))
- `js::AnimationEffect` (3 miembro(s))
- `js::AnimationEvent → js::Event` (3 miembro(s))
- `js::AnimationFrameProvider` (2 miembro(s))
- `js::AnimationPlaybackEvent → js::Event` (2 miembro(s))
- `js::AnimationTimeline` (1 miembro(s))
- `js::Attr → js::Node` (8 miembro(s))
- `js::AudioBuffer` (7 miembro(s))
- `js::AudioBufferSourceNode → js::AudioScheduledSourceNode` (9 miembro(s))
- `js::AudioContext → js::BaseAudioContext` (11 miembro(s))
- `js::AudioData` (10 miembro(s))
- `js::AudioDecoderEventMap` (1 miembro(s))
- `js::AudioDecoder → js::EventTarget` (10 miembro(s))
- `js::AudioDestinationNode → js::AudioNode` (1 miembro(s))
- `js::AudioEncoderEventMap` (1 miembro(s))
- `js::AudioEncoder → js::EventTarget` (10 miembro(s))
- `js::AudioListener` (11 miembro(s))
- `js::AudioNode → js::EventTarget` (8 miembro(s))
- `js::AudioParam` (12 miembro(s))
- `js::AudioParamMap` (1 miembro(s))
- `js::AudioProcessingEvent → js::Event` (3 miembro(s))
- `js::AudioScheduledSourceNodeEventMap` (1 miembro(s))
- `js::AudioScheduledSourceNode → js::AudioNode` (5 miembro(s))
- `js::AudioWorkletNodeEventMap` (1 miembro(s))
- `js::AudioWorkletNode → js::AudioNode` (5 miembro(s))
- `js::AuthenticatorAssertionResponse → js::AuthenticatorResponse` (3 miembro(s))
- `js::AuthenticatorAttestationResponse → js::AuthenticatorResponse` (5 miembro(s))
- `js::AuthenticatorResponse` (1 miembro(s))
- `js::BarProp` (1 miembro(s))
- `js::BaseAudioContextEventMap` (1 miembro(s))
- `js::BaseAudioContext → js::EventTarget` (28 miembro(s))
- `js::BeforeUnloadEvent → js::Event` (1 miembro(s))
- `js::BiquadFilterNode → js::AudioNode` (6 miembro(s))
- `js::Blob` (7 miembro(s))
- `js::BlobEvent → js::Event` (2 miembro(s))
- `js::Body` (8 miembro(s))
- `js::BroadcastChannelEventMap` (2 miembro(s))
- `js::BroadcastChannel → js::EventTarget` (7 miembro(s))
- `js::ByteLengthQueuingStrategy → js::QueuingStrategy` (2 miembro(s))
- `js::CSSAnimation → js::Animation` (3 miembro(s))
- `js::CSSConditionRule → js::CSSGroupingRule` (1 miembro(s))
- `js::CSSContainerRule → js::CSSConditionRule` (2 miembro(s))
- `js::CSSCounterStyleRule → js::CSSRule` (11 miembro(s))
- `js::CSSFontFaceRule → js::CSSRule` (1 miembro(s))
- `js::CSSFontFeatureValuesRule → js::CSSRule` (1 miembro(s))
- `js::CSSFontPaletteValuesRule → js::CSSRule` (4 miembro(s))
- `js::CSSGroupingRule → js::CSSRule` (3 miembro(s))
- `js::CSSImportRule → js::CSSRule` (5 miembro(s))
- `js::CSSKeyframeRule → js::CSSRule` (2 miembro(s))
- `js::CSSKeyframesRule → js::CSSRule` (7 miembro(s))
- `js::CSSKeywordValue → js::CSSStyleValue` (1 miembro(s))
- `js::CSSLayerBlockRule → js::CSSGroupingRule` (1 miembro(s))
- `js::CSSLayerStatementRule → js::CSSRule` (1 miembro(s))
- `js::CSSMathClamp → js::CSSMathValue` (3 miembro(s))
- `js::CSSMathInvert → js::CSSMathValue` (1 miembro(s))
- `js::CSSMathMax → js::CSSMathValue` (1 miembro(s))
- `js::CSSMathMin → js::CSSMathValue` (1 miembro(s))
- `js::CSSMathNegate → js::CSSMathValue` (1 miembro(s))
- `js::CSSMathProduct → js::CSSMathValue` (1 miembro(s))
- `js::CSSMathSum → js::CSSMathValue` (1 miembro(s))
- `js::CSSMathValue → js::CSSNumericValue` (1 miembro(s))
- `js::CSSMatrixComponent → js::CSSTransformComponent` (1 miembro(s))
- `js::CSSMediaRule → js::CSSConditionRule` (1 miembro(s))
- `js::CSSNamespaceRule → js::CSSRule` (2 miembro(s))
- `js::CSSNumericArray` (3 miembro(s))
- `js::CSSNumericValue → js::CSSStyleValue` (10 miembro(s))
- `js::CSSPageRule → js::CSSGroupingRule` (2 miembro(s))
- `js::CSSPerspective → js::CSSTransformComponent` (1 miembro(s))
- `js::CSSPropertyRule → js::CSSRule` (4 miembro(s))
- `js::CSSRotate → js::CSSTransformComponent` (4 miembro(s))
- `js::CSSRule` (16 miembro(s))
- `js::CSSRuleList` (3 miembro(s))
- `js::CSSScale → js::CSSTransformComponent` (3 miembro(s))
- `js::CSSScopeRule → js::CSSGroupingRule` (2 miembro(s))
- `js::CSSSkew → js::CSSTransformComponent` (2 miembro(s))
- `js::CSSSkewX → js::CSSTransformComponent` (1 miembro(s))
- `js::CSSSkewY → js::CSSTransformComponent` (1 miembro(s))
- `js::CSSStyleDeclaration` (507 miembro(s))
- `js::CSSStyleRule → js::CSSGroupingRule` (3 miembro(s))
- `js::CSSStyleSheet → js::StyleSheet` (9 miembro(s))
- `js::CSSStyleValue` (1 miembro(s))
- `js::CSSTransformComponent` (3 miembro(s))
- `js::CSSTransformValue → js::CSSStyleValue` (5 miembro(s))
- `js::CSSTransition → js::Animation` (3 miembro(s))
- `js::CSSTranslate → js::CSSTransformComponent` (3 miembro(s))
- `js::CSSUnitValue → js::CSSNumericValue` (2 miembro(s))
- `js::CSSUnparsedValue → js::CSSStyleValue` (3 miembro(s))
- `js::CSSVariableReferenceValue` (2 miembro(s))
- `js::Cache` (7 miembro(s))
- `js::CacheStorage` (5 miembro(s))
- `js::CanvasCaptureMediaStreamTrack → js::MediaStreamTrack` (4 miembro(s))
- `js::CanvasCompositing` (2 miembro(s))
- `js::CanvasDrawImage` (1 miembro(s))
- `js::CanvasDrawPath` (6 miembro(s))
- `js::CanvasFillStrokeStyles` (6 miembro(s))
- `js::CanvasFilters` (1 miembro(s))
- `js::CanvasGradient` (1 miembro(s))
- `js::CanvasImageData` (3 miembro(s))
- `js::CanvasImageSmoothing` (2 miembro(s))
- `js::CanvasPath` (10 miembro(s))
- `js::CanvasPathDrawingStyles` (7 miembro(s))
- `js::CanvasPattern` (1 miembro(s))
- `js::CanvasRect` (3 miembro(s))
- `js::CanvasRenderingContext2D → js::CanvasCompositing` (70 miembro(s))
- `js::CanvasShadowStyles` (4 miembro(s))
- `js::CanvasState` (4 miembro(s))
- `js::CanvasText` (3 miembro(s))
- `js::CanvasTextDrawingStyles` (10 miembro(s))
- `js::CanvasTransform` (7 miembro(s))
- `js::CanvasUserInterface` (1 miembro(s))
- `js::CaretPosition` (3 miembro(s))
- `js::CharacterData → js::Node` (14 miembro(s))
- `js::ChildNode → js::Node` (4 miembro(s))
- `js::Clipboard → js::EventTarget` (4 miembro(s))
- `js::ClipboardEvent → js::Event` (1 miembro(s))
- `js::ClipboardItem` (3 miembro(s))
- `js::CloseEvent → js::Event` (3 miembro(s))
- `js::CompositionEvent → js::UIEvent` (2 miembro(s))
- `js::CompressionStream → js::GenericTransformStream` (2 miembro(s))
- `js::ConstantSourceNode → js::AudioScheduledSourceNode` (3 miembro(s))
- `js::ContentVisibilityAutoStateChangeEvent → js::Event` (1 miembro(s))
- `js::ConvolverNode → js::AudioNode` (2 miembro(s))
- `js::CountQueuingStrategy → js::QueuingStrategy` (2 miembro(s))
- `js::Credential` (2 miembro(s))
- `js::CredentialsContainer` (4 miembro(s))
- `js::Crypto` (3 miembro(s))
- `js::CryptoKey` (4 miembro(s))
- `js::CustomElementRegistry` (5 miembro(s))
- `js::CustomEvent → js::Event` (2 miembro(s))
- `js::CustomStateSet` (1 miembro(s))
- `js::DOMException → js::Error` (28 miembro(s))
- `js::DOMImplementation` (4 miembro(s))
- `js::DOMMatrix → js::DOMMatrixReadOnly` (34 miembro(s))
- `js::DOMMatrixReadOnly` (42 miembro(s))
- `js::DOMParser` (1 miembro(s))
- `js::DOMPoint → js::DOMPointReadOnly` (4 miembro(s))
- `js::DOMPointReadOnly` (6 miembro(s))
- `js::DOMQuad` (6 miembro(s))
- `js::DOMRect → js::DOMRectReadOnly` (4 miembro(s))
- `js::DOMRectList` (3 miembro(s))
- `js::DOMRectReadOnly` (9 miembro(s))
- `js::DOMStringList` (4 miembro(s))
- `js::DOMStringMap` (1 miembro(s))
- `js::DOMTokenList` (12 miembro(s))
- `js::DataTransfer` (9 miembro(s))
- `js::DataTransferItem` (5 miembro(s))
- `js::DataTransferItemList` (5 miembro(s))
- `js::DecompressionStream → js::GenericTransformStream` (2 miembro(s))
- `js::DelayNode → js::AudioNode` (1 miembro(s))
- `js::DeviceMotionEvent → js::Event` (4 miembro(s))
- `js::DeviceMotionEventAcceleration` (3 miembro(s))
- `js::DeviceMotionEventRotationRate` (3 miembro(s))
- `js::DeviceOrientationEvent → js::Event` (4 miembro(s))
- `js::DocumentEventMap → js::GlobalEventHandlersEventMap` (7 miembro(s))
- `js::Document → js::Node` (218 miembro(s))
- `js::DocumentFragment → js::Node` (11 miembro(s))
- `js::DocumentOrShadowRoot` (9 miembro(s))
- `js::DocumentType → js::Node` (8 miembro(s))
- `js::DragEvent → js::MouseEvent` (1 miembro(s))
- `js::DynamicsCompressorNode → js::AudioNode` (6 miembro(s))
- `js::EXT_blend_minmax` (2 miembro(s))
- `js::EXT_color_buffer_half_float` (4 miembro(s))
- `js::EXT_sRGB` (4 miembro(s))
- `js::EXT_texture_compression_bptc` (4 miembro(s))
- `js::EXT_texture_compression_rgtc` (4 miembro(s))
- `js::EXT_texture_filter_anisotropic` (2 miembro(s))
- `js::EXT_texture_norm16` (8 miembro(s))
- `js::ElementEventMap` (2 miembro(s))
- `js::Element → js::Node` (129 miembro(s))
- `js::ElementCSSInlineStyle` (2 miembro(s))
- `js::ElementContentEditable` (4 miembro(s))
- `js::ElementInternals → js::ARIAMixin` (11 miembro(s))
- `js::EncodedAudioChunk` (5 miembro(s))
- `js::EncodedVideoChunk` (5 miembro(s))
- `js::ErrorEvent → js::Event` (5 miembro(s))
- `js::Event` (22 miembro(s))
- `js::EventCounts` (1 miembro(s))
- `js::EventListenerObject` (1 miembro(s))
- `js::EventSourceEventMap` (3 miembro(s))
- `js::EventSource → js::EventTarget` (12 miembro(s))
- `js::EventTarget` (3 miembro(s))
- `js::External` (2 miembro(s))
- `js::File → js::Blob` (3 miembro(s))
- `js::FileList` (3 miembro(s))
- `js::FileReaderEventMap` (6 miembro(s))
- `js::FileReader → js::EventTarget` (19 miembro(s))
- `js::FileSystem` (2 miembro(s))
- `js::FileSystemDirectoryEntry → js::FileSystemEntry` (3 miembro(s))
- `js::FileSystemDirectoryHandle → js::FileSystemHandle` (5 miembro(s))
- `js::FileSystemDirectoryReader` (1 miembro(s))
- `js::FileSystemEntry` (6 miembro(s))
- `js::FileSystemFileEntry → js::FileSystemEntry` (1 miembro(s))
- `js::FileSystemFileHandle → js::FileSystemHandle` (3 miembro(s))
- `js::FileSystemHandle` (3 miembro(s))
- `js::FileSystemWritableFileStream → js::WritableStream` (3 miembro(s))
- `js::FocusEvent → js::UIEvent` (1 miembro(s))
- `js::FontFace` (13 miembro(s))
- `js::FontFaceSetEventMap` (3 miembro(s))
- `js::FontFaceSet → js::EventTarget` (10 miembro(s))
- `js::FontFaceSetLoadEvent → js::Event` (1 miembro(s))
- `js::FontFaceSource` (1 miembro(s))
- `js::FormData` (7 miembro(s))
- `js::FormDataEvent → js::Event` (1 miembro(s))
- `js::GainNode → js::AudioNode` (1 miembro(s))
- `js::Gamepad` (8 miembro(s))
- `js::GamepadButton` (3 miembro(s))
- `js::GamepadEvent → js::Event` (1 miembro(s))
- `js::GamepadHapticActuator` (2 miembro(s))
- `js::GenericTransformStream` (2 miembro(s))
- `js::Geolocation` (3 miembro(s))
- `js::GeolocationCoordinates` (8 miembro(s))
- `js::GeolocationPosition` (3 miembro(s))
- `js::GeolocationPositionError` (5 miembro(s))
- `js::GlobalEventHandlersEventMap` (103 miembro(s))
- `js::GlobalEventHandlers` (100 miembro(s))
- `js::HTMLAllCollection` (4 miembro(s))
- `js::HTMLAnchorElement → js::HTMLElement` (28 miembro(s))
- `js::HTMLAreaElement → js::HTMLElement` (24 miembro(s))
- `js::HTMLAudioElement → js::HTMLMediaElement` (2 miembro(s))
- `js::HTMLBRElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLBaseElement → js::HTMLElement` (4 miembro(s))
- `js::HTMLBodyElementEventMap → js::HTMLElementEventMap` (18 miembro(s))
- `js::HTMLBodyElement → js::HTMLElement` (26 miembro(s))
- `js::HTMLButtonElement → js::HTMLElement` (21 miembro(s))
- `js::HTMLCanvasElement → js::HTMLElement` (9 miembro(s))
- `js::HTMLCollectionBase` (3 miembro(s))
- `js::HTMLCollection → js::HTMLCollectionBase` (1 miembro(s))
- `js::HTMLCollectionOf → js::HTMLCollectionBase` (3 miembro(s))
- `js::HTMLDListElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLDataElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLDataListElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLDetailsElement → js::HTMLElement` (4 miembro(s))
- `js::HTMLDialogElement → js::HTMLElement` (7 miembro(s))
- `js::HTMLDirectoryElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLDivElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLDocument → js::Document` (2 miembro(s))
- `js::HTMLElementEventMap → js::ElementEventMap` (103 miembro(s))
- `js::HTMLElement → js::Element` (137 miembro(s))
- `js::HTMLEmbedElement → js::HTMLElement` (9 miembro(s))
- `js::HTMLFieldSetElement → js::HTMLElement` (13 miembro(s))
- `js::HTMLFontElement → js::HTMLElement` (5 miembro(s))
- `js::HTMLFormControlsCollection → js::HTMLCollectionBase` (1 miembro(s))
- `js::HTMLFormElement → js::HTMLElement` (21 miembro(s))
- `js::HTMLFrameElement → js::HTMLElement` (12 miembro(s))
- `js::HTMLFrameSetElementEventMap → js::HTMLElementEventMap` (18 miembro(s))
- `js::HTMLFrameSetElement → js::HTMLElement` (22 miembro(s))
- `js::HTMLHRElement → js::HTMLElement` (7 miembro(s))
- `js::HTMLHeadElement → js::HTMLElement` (2 miembro(s))
- `js::HTMLHeadingElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLHtmlElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLHyperlinkElementUtils` (12 miembro(s))
- `js::HTMLIFrameElement → js::HTMLElement` (21 miembro(s))
- `js::HTMLImageElement → js::HTMLElement` (29 miembro(s))
- `js::HTMLInputElement → js::HTMLElement` (61 miembro(s))
- `js::HTMLLIElement → js::HTMLElement` (4 miembro(s))
- `js::HTMLLabelElement → js::HTMLElement` (5 miembro(s))
- `js::HTMLLegendElement → js::HTMLElement` (4 miembro(s))
- `js::HTMLLinkElement → js::HTMLElement` (21 miembro(s))
- `js::HTMLMapElement → js::HTMLElement` (4 miembro(s))
- `js::HTMLMarqueeElement → js::HTMLElement` (15 miembro(s))
- `js::HTMLMediaElementEventMap → js::HTMLElementEventMap` (2 miembro(s))
- `js::HTMLMediaElement → js::HTMLElement` (51 miembro(s))
- `js::HTMLMenuElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLMetaElement → js::HTMLElement` (7 miembro(s))
- `js::HTMLMeterElement → js::HTMLElement` (9 miembro(s))
- `js::HTMLModElement → js::HTMLElement` (4 miembro(s))
- `js::HTMLOListElement → js::HTMLElement` (6 miembro(s))
- `js::HTMLObjectElement → js::HTMLElement` (28 miembro(s))
- `js::HTMLOptGroupElement → js::HTMLElement` (4 miembro(s))
- `js::HTMLOptionElement → js::HTMLElement` (10 miembro(s))
- `js::HTMLOptionsCollection → js::HTMLCollectionOf` (4 miembro(s))
- `js::HTMLOrSVGElement` (6 miembro(s))
- `js::HTMLOutputElement → js::HTMLElement` (15 miembro(s))
- `js::HTMLParagraphElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLParamElement → js::HTMLElement` (6 miembro(s))
- `js::HTMLPictureElement → js::HTMLElement` (2 miembro(s))
- `js::HTMLPreElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLProgressElement → js::HTMLElement` (6 miembro(s))
- `js::HTMLQuoteElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLScriptElement → js::HTMLElement` (15 miembro(s))
- `js::HTMLSelectElement → js::HTMLElement` (28 miembro(s))
- `js::HTMLSlotElement → js::HTMLElement` (6 miembro(s))
- `js::HTMLSourceElement → js::HTMLElement` (9 miembro(s))
- `js::HTMLSpanElement → js::HTMLElement` (2 miembro(s))
- `js::HTMLStyleElement → js::HTMLElement` (6 miembro(s))
- `js::HTMLTableCaptionElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLTableCellElement → js::HTMLElement` (17 miembro(s))
- `js::HTMLTableColElement → js::HTMLElement` (8 miembro(s))
- `js::HTMLTableDataCellElement → js::HTMLTableCellElement` (2 miembro(s))
- `js::HTMLTableElement → js::HTMLElement` (25 miembro(s))
- `js::HTMLTableHeaderCellElement → js::HTMLTableCellElement` (2 miembro(s))
- `js::HTMLTableRowElement → js::HTMLElement` (12 miembro(s))
- `js::HTMLTableSectionElement → js::HTMLElement` (9 miembro(s))
- `js::HTMLTemplateElement → js::HTMLElement` (7 miembro(s))
- `js::HTMLTextAreaElement → js::HTMLElement` (32 miembro(s))
- `js::HTMLTimeElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLTitleElement → js::HTMLElement` (3 miembro(s))
- `js::HTMLTrackElement → js::HTMLElement` (13 miembro(s))
- `js::HTMLUListElement → js::HTMLElement` (4 miembro(s))
- `js::HTMLUnknownElement → js::HTMLElement` (2 miembro(s))
- `js::HTMLVideoElementEventMap → js::HTMLMediaElementEventMap` (2 miembro(s))
- `js::HTMLVideoElement → js::HTMLMediaElement` (15 miembro(s))
- `js::HashChangeEvent → js::Event` (2 miembro(s))
- `js::Headers` (7 miembro(s))
- `js::Highlight` (3 miembro(s))
- `js::HighlightRegistry` (1 miembro(s))
- `js::History` (8 miembro(s))
- `js::IDBCursor` (10 miembro(s))
- `js::IDBCursorWithValue → js::IDBCursor` (1 miembro(s))
- `js::IDBDatabaseEventMap` (4 miembro(s))
- `js::IDBDatabase → js::EventTarget` (13 miembro(s))
- `js::IDBFactory` (4 miembro(s))
- `js::IDBIndex` (12 miembro(s))
- `js::IDBKeyRange` (5 miembro(s))
- `js::IDBObjectStore` (19 miembro(s))
- `js::IDBOpenDBRequestEventMap → js::IDBRequestEventMap` (2 miembro(s))
- `js::IDBOpenDBRequest → js::IDBRequest` (4 miembro(s))
- `js::IDBRequestEventMap` (2 miembro(s))
- `js::IDBRequest → js::EventTarget` (9 miembro(s))
- `js::IDBTransactionEventMap` (3 miembro(s))
- `js::IDBTransaction → js::EventTarget` (13 miembro(s))
- `js::IDBVersionChangeEvent → js::Event` (2 miembro(s))
- `js::IIRFilterNode → js::AudioNode` (1 miembro(s))
- `js::IdleDeadline` (2 miembro(s))
- `js::ImageBitmap` (3 miembro(s))
- `js::ImageBitmapRenderingContext` (2 miembro(s))
- `js::ImageData` (4 miembro(s))
- `js::ImportMeta` (2 miembro(s))
- `js::InputDeviceInfo → js::MediaDeviceInfo` (1 miembro(s))
- `js::InputEvent → js::UIEvent` (5 miembro(s))
- `js::IntersectionObserver` (7 miembro(s))
- `js::IntersectionObserverEntry` (7 miembro(s))
- `js::KHR_parallel_shader_compile` (1 miembro(s))
- `js::KeyboardEvent → js::UIEvent` (17 miembro(s))
- `js::KeyframeEffect → js::AnimationEffect` (6 miembro(s))
- `js::LargestContentfulPaint → js::PerformanceEntry` (7 miembro(s))
- `js::LinkStyle` (1 miembro(s))
- `js::Location` (14 miembro(s))
- `js::Lock` (2 miembro(s))
- `js::LockManager` (2 miembro(s))
- `js::MIDIAccessEventMap` (1 miembro(s))
- `js::MIDIAccess → js::EventTarget` (6 miembro(s))
- `js::MIDIConnectionEvent → js::Event` (1 miembro(s))
- `js::MIDIInputEventMap → js::MIDIPortEventMap` (1 miembro(s))
- `js::MIDIInput → js::MIDIPort` (3 miembro(s))
- `js::MIDIInputMap` (1 miembro(s))
- `js::MIDIMessageEvent → js::Event` (1 miembro(s))
- `js::MIDIOutput → js::MIDIPort` (3 miembro(s))
- `js::MIDIOutputMap` (1 miembro(s))
- `js::MIDIPortEventMap` (1 miembro(s))
- `js::MIDIPort → js::EventTarget` (12 miembro(s))
- `js::MathMLElementEventMap → js::ElementEventMap` (103 miembro(s))
- `js::MathMLElement → js::Element` (108 miembro(s))
- `js::MediaCapabilities` (2 miembro(s))
- `js::MediaDeviceInfo` (5 miembro(s))
- `js::MediaDevicesEventMap` (1 miembro(s))
- `js::MediaDevices → js::EventTarget` (7 miembro(s))
- `js::MediaElementAudioSourceNode → js::AudioNode` (1 miembro(s))
- `js::MediaEncryptedEvent → js::Event` (2 miembro(s))
- `js::MediaError` (6 miembro(s))
- `js::MediaKeyMessageEvent → js::Event` (2 miembro(s))
- `js::MediaKeySessionEventMap` (2 miembro(s))
- `js::MediaKeySession → js::EventTarget` (13 miembro(s))
- `js::MediaKeyStatusMap` (4 miembro(s))
- `js::MediaKeySystemAccess` (3 miembro(s))
- `js::MediaKeys` (3 miembro(s))
- `js::MediaList` (7 miembro(s))
- `js::MediaMetadata` (4 miembro(s))
- `js::MediaQueryListEventMap` (1 miembro(s))
- `js::MediaQueryList → js::EventTarget` (7 miembro(s))
- `js::MediaQueryListEvent → js::Event` (2 miembro(s))
- `js::MediaRecorderEventMap` (6 miembro(s))
- `js::MediaRecorder → js::EventTarget` (18 miembro(s))
- `js::MediaSession` (4 miembro(s))
- `js::MediaSourceEventMap` (3 miembro(s))
- `js::MediaSource → js::EventTarget` (14 miembro(s))
- `js::MediaStreamEventMap` (2 miembro(s))
- `js::MediaStream → js::EventTarget` (13 miembro(s))
- `js::MediaStreamAudioDestinationNode → js::AudioNode` (1 miembro(s))
- `js::MediaStreamAudioSourceNode → js::AudioNode` (1 miembro(s))
- `js::MediaStreamTrackEventMap` (3 miembro(s))
- `js::MediaStreamTrack → js::EventTarget` (18 miembro(s))
- `js::MediaStreamTrackEvent → js::Event` (1 miembro(s))
- `js::MessageChannel` (2 miembro(s))
- `js::MessageEvent → js::Event` (6 miembro(s))
- `js::MessagePortEventMap` (2 miembro(s))
- `js::MessagePort → js::EventTarget` (7 miembro(s))
- `js::MimeType` (4 miembro(s))
- `js::MimeTypeArray` (4 miembro(s))
- `js::MouseEvent → js::UIEvent` (23 miembro(s))
- `js::MutationObserver` (3 miembro(s))
- `js::MutationRecord` (9 miembro(s))
- `js::NamedNodeMap` (9 miembro(s))
- `js::NavigationPreloadManager` (4 miembro(s))
- `js::Navigator → js::NavigatorAutomationInformation` (42 miembro(s))
- `js::NavigatorAutomationInformation` (1 miembro(s))
- `js::NavigatorBadge` (2 miembro(s))
- `js::NavigatorConcurrentHardware` (1 miembro(s))
- `js::NavigatorContentUtils` (1 miembro(s))
- `js::NavigatorCookies` (1 miembro(s))
- `js::NavigatorID` (9 miembro(s))
- `js::NavigatorLanguage` (2 miembro(s))
- `js::NavigatorLocks` (1 miembro(s))
- `js::NavigatorOnLine` (1 miembro(s))
- `js::NavigatorPlugins` (4 miembro(s))
- `js::NavigatorStorage` (1 miembro(s))
- `js::Node → js::EventTarget` (47 miembro(s))
- `js::NodeIterator` (8 miembro(s))
- `js::NodeList` (4 miembro(s))
- `js::NodeListOf → js::NodeList` (3 miembro(s))
- `js::NonDocumentTypeChildNode` (2 miembro(s))
- `js::NonElementParentNode` (1 miembro(s))
- `js::NotificationEventMap` (4 miembro(s))
- `js::Notification → js::EventTarget` (17 miembro(s))
- `js::OES_draw_buffers_indexed` (7 miembro(s))
- `js::OES_standard_derivatives` (1 miembro(s))
- `js::OES_texture_half_float` (1 miembro(s))
- `js::OES_vertex_array_object` (5 miembro(s))
- `js::OVR_multiview2` (5 miembro(s))
- `js::OfflineAudioCompletionEvent → js::Event` (1 miembro(s))
- `js::OfflineAudioContextEventMap → js::BaseAudioContextEventMap` (1 miembro(s))
- `js::OfflineAudioContext → js::BaseAudioContext` (7 miembro(s))
- `js::OffscreenCanvasEventMap` (2 miembro(s))
- `js::OffscreenCanvas → js::EventTarget` (9 miembro(s))
- `js::OffscreenCanvasRenderingContext2D → js::CanvasCompositing` (68 miembro(s))
- `js::OscillatorNode → js::AudioScheduledSourceNode` (6 miembro(s))
- `js::OverconstrainedError → js::DOMException` (1 miembro(s))
- `js::PageTransitionEvent → js::Event` (1 miembro(s))
- `js::PannerNode → js::AudioNode` (16 miembro(s))
- `js::ParentNode → js::Node` (9 miembro(s))
- `js::Path2D → js::CanvasPath` (1 miembro(s))
- `js::PaymentAddress` (11 miembro(s))
- `js::PaymentMethodChangeEvent → js::PaymentRequestUpdateEvent` (2 miembro(s))
- `js::PaymentRequestEventMap` (3 miembro(s))
- `js::PaymentRequest → js::EventTarget` (12 miembro(s))
- `js::PaymentRequestUpdateEvent → js::Event` (1 miembro(s))
- `js::PaymentResponseEventMap` (1 miembro(s))
- `js::PaymentResponse → js::EventTarget` (14 miembro(s))
- `js::PerformanceEventMap` (1 miembro(s))
- `js::Performance → js::EventTarget` (18 miembro(s))
- `js::PerformanceEntry` (5 miembro(s))
- `js::PerformanceEventTiming → js::PerformanceEntry` (5 miembro(s))
- `js::PerformanceMark → js::PerformanceEntry` (1 miembro(s))
- `js::PerformanceMeasure → js::PerformanceEntry` (1 miembro(s))
- `js::PerformanceNavigation` (7 miembro(s))
- `js::PerformanceNavigationTiming → js::PerformanceResourceTiming` (11 miembro(s))
- `js::PerformanceObserver` (3 miembro(s))
- `js::PerformanceObserverEntryList` (3 miembro(s))
- `js::PerformanceResourceTiming → js::PerformanceEntry` (20 miembro(s))
- `js::PerformanceServerTiming` (4 miembro(s))
- `js::PerformanceTiming` (22 miembro(s))
- `js::PermissionStatusEventMap` (1 miembro(s))
- `js::PermissionStatus → js::EventTarget` (5 miembro(s))
- `js::Permissions` (1 miembro(s))
- `js::PictureInPictureEvent → js::Event` (1 miembro(s))
- `js::PictureInPictureWindowEventMap` (1 miembro(s))
- `js::PictureInPictureWindow → js::EventTarget` (5 miembro(s))
- `js::Plugin` (7 miembro(s))
- `js::PluginArray` (5 miembro(s))
- `js::PointerEvent → js::MouseEvent` (14 miembro(s))
- `js::PopStateEvent → js::Event` (2 miembro(s))
- `js::PopoverInvokerElement` (2 miembro(s))
- `js::ProcessingInstruction → js::CharacterData` (3 miembro(s))
- `js::ProgressEvent → js::Event` (4 miembro(s))
- `js::PromiseRejectionEvent → js::Event` (2 miembro(s))
- `js::PublicKeyCredential → js::Credential` (5 miembro(s))
- `js::PushManager` (3 miembro(s))
- `js::PushSubscription` (6 miembro(s))
- `js::PushSubscriptionOptions` (2 miembro(s))
- `js::RTCCertificate` (2 miembro(s))
- `js::RTCDTMFSenderEventMap` (1 miembro(s))
- `js::RTCDTMFSender → js::EventTarget` (6 miembro(s))
- `js::RTCDTMFToneChangeEvent → js::Event` (1 miembro(s))
- `js::RTCDataChannelEventMap` (6 miembro(s))
- `js::RTCDataChannel → js::EventTarget` (21 miembro(s))
- `js::RTCDataChannelEvent → js::Event` (1 miembro(s))
- `js::RTCDtlsTransportEventMap` (2 miembro(s))
- `js::RTCDtlsTransport → js::EventTarget` (7 miembro(s))
- `js::RTCEncodedAudioFrame` (3 miembro(s))
- `js::RTCEncodedVideoFrame` (4 miembro(s))
- `js::RTCError → js::DOMException` (5 miembro(s))
- `js::RTCErrorEvent → js::Event` (1 miembro(s))
- `js::RTCIceCandidate` (15 miembro(s))
- `js::RTCIceCandidatePair` (2 miembro(s))
- `js::RTCIceTransportEventMap` (3 miembro(s))
- `js::RTCIceTransport → js::EventTarget` (8 miembro(s))
- `js::RTCPeerConnectionEventMap` (9 miembro(s))
- `js::RTCPeerConnection → js::EventTarget` (40 miembro(s))
- `js::RTCPeerConnectionIceErrorEvent → js::Event` (5 miembro(s))
- `js::RTCPeerConnectionIceEvent → js::Event` (1 miembro(s))
- `js::RTCRtpReceiver` (8 miembro(s))
- `js::RTCRtpSender` (9 miembro(s))
- `js::RTCRtpTransceiver` (7 miembro(s))
- `js::RTCSctpTransportEventMap` (1 miembro(s))
- `js::RTCSctpTransport → js::EventTarget` (7 miembro(s))
- `js::RTCSessionDescription` (3 miembro(s))
- `js::RTCStatsReport` (1 miembro(s))
- `js::RTCTrackEvent → js::Event` (4 miembro(s))
- `js::RadioNodeList → js::NodeList` (1 miembro(s))
- `js::Range → js::AbstractRange` (29 miembro(s))
- `js::ReadableByteStreamController` (5 miembro(s))
- `js::ReadableStream` (6 miembro(s))
- `js::ReadableStreamBYOBReader → js::ReadableStreamGenericReader` (2 miembro(s))
- `js::ReadableStreamBYOBRequest` (3 miembro(s))
- `js::ReadableStreamDefaultController` (4 miembro(s))
- `js::ReadableStreamDefaultReader → js::ReadableStreamGenericReader` (2 miembro(s))
- `js::ReadableStreamGenericReader` (2 miembro(s))
- `js::RemotePlaybackEventMap` (3 miembro(s))
- `js::RemotePlayback → js::EventTarget` (9 miembro(s))
- `js::Report` (4 miembro(s))
- `js::ReportBody` (1 miembro(s))
- `js::ReportingObserver` (3 miembro(s))
- `js::Request → js::Body` (14 miembro(s))
- `js::ResizeObserver` (3 miembro(s))
- `js::ResizeObserverEntry` (5 miembro(s))
- `js::ResizeObserverSize` (2 miembro(s))
- `js::Response → js::Body` (8 miembro(s))
- `js::SVGAElement → js::SVGGraphicsElement` (6 miembro(s))
- `js::SVGAngle` (11 miembro(s))
- `js::SVGAnimateElement → js::SVGAnimationElement` (2 miembro(s))
- `js::SVGAnimateMotionElement → js::SVGAnimationElement` (2 miembro(s))
- `js::SVGAnimateTransformElement → js::SVGAnimationElement` (2 miembro(s))
- `js::SVGAnimatedAngle` (2 miembro(s))
- `js::SVGAnimatedBoolean` (2 miembro(s))
- `js::SVGAnimatedEnumeration` (2 miembro(s))
- `js::SVGAnimatedInteger` (2 miembro(s))
- `js::SVGAnimatedLength` (2 miembro(s))
- `js::SVGAnimatedLengthList` (2 miembro(s))
- `js::SVGAnimatedNumber` (2 miembro(s))
- `js::SVGAnimatedNumberList` (2 miembro(s))
- `js::SVGAnimatedPoints` (2 miembro(s))
- `js::SVGAnimatedPreserveAspectRatio` (2 miembro(s))
- `js::SVGAnimatedRect` (2 miembro(s))
- `js::SVGAnimatedString` (2 miembro(s))
- `js::SVGAnimatedTransformList` (2 miembro(s))
- `js::SVGAnimationElement → js::SVGElement` (12 miembro(s))
- `js::SVGCircleElement → js::SVGGeometryElement` (5 miembro(s))
- `js::SVGClipPathElement → js::SVGElement` (4 miembro(s))
- `js::SVGComponentTransferFunctionElement → js::SVGElement` (15 miembro(s))
- `js::SVGDefsElement → js::SVGGraphicsElement` (2 miembro(s))
- `js::SVGDescElement → js::SVGElement` (2 miembro(s))
- `js::SVGElementEventMap → js::ElementEventMap` (103 miembro(s))
- `js::SVGElement → js::Element` (111 miembro(s))
- `js::SVGEllipseElement → js::SVGGeometryElement` (6 miembro(s))
- `js::SVGFEBlendElement → js::SVGElement` (27 miembro(s))
- `js::SVGFEColorMatrixElement → js::SVGElement` (15 miembro(s))
- `js::SVGFEComponentTransferElement → js::SVGElement` (8 miembro(s))
- `js::SVGFECompositeElement → js::SVGElement` (21 miembro(s))
- `js::SVGFEConvolveMatrixElement → js::SVGElement` (23 miembro(s))
- `js::SVGFEDiffuseLightingElement → js::SVGElement` (12 miembro(s))
- `js::SVGFEDisplacementMapElement → js::SVGElement` (17 miembro(s))
- `js::SVGFEDistantLightElement → js::SVGElement` (4 miembro(s))
- `js::SVGFEDropShadowElement → js::SVGElement` (13 miembro(s))
- `js::SVGFEFloodElement → js::SVGElement` (7 miembro(s))
- `js::SVGFEFuncAElement → js::SVGComponentTransferFunctionElement` (2 miembro(s))
- `js::SVGFEFuncBElement → js::SVGComponentTransferFunctionElement` (2 miembro(s))
- `js::SVGFEFuncGElement → js::SVGComponentTransferFunctionElement` (2 miembro(s))
- `js::SVGFEFuncRElement → js::SVGComponentTransferFunctionElement` (2 miembro(s))
- `js::SVGFEGaussianBlurElement → js::SVGElement` (11 miembro(s))
- `js::SVGFEImageElement → js::SVGElement` (9 miembro(s))
- `js::SVGFEMergeElement → js::SVGElement` (7 miembro(s))
- `js::SVGFEMergeNodeElement → js::SVGElement` (3 miembro(s))
- `js::SVGFEMorphologyElement → js::SVGElement` (14 miembro(s))
- `js::SVGFEOffsetElement → js::SVGElement` (10 miembro(s))
- `js::SVGFEPointLightElement → js::SVGElement` (5 miembro(s))
- `js::SVGFESpecularLightingElement → js::SVGElement` (13 miembro(s))
- `js::SVGFESpotLightElement → js::SVGElement` (10 miembro(s))
- `js::SVGFETileElement → js::SVGElement` (8 miembro(s))
- `js::SVGFETurbulenceElement → js::SVGElement` (19 miembro(s))
- `js::SVGFilterElement → js::SVGElement` (9 miembro(s))
- `js::SVGFilterPrimitiveStandardAttributes` (5 miembro(s))
- `js::SVGFitToViewBox` (2 miembro(s))
- `js::SVGForeignObjectElement → js::SVGGraphicsElement` (6 miembro(s))
- `js::SVGGElement → js::SVGGraphicsElement` (2 miembro(s))
- `js::SVGGeometryElement → js::SVGGraphicsElement` (7 miembro(s))
- `js::SVGGradientElement → js::SVGElement` (10 miembro(s))
- `js::SVGGraphicsElement → js::SVGElement` (8 miembro(s))
- `js::SVGImageElement → js::SVGGraphicsElement` (9 miembro(s))
- `js::SVGLength` (17 miembro(s))
- `js::SVGLengthList` (10 miembro(s))
- `js::SVGLineElement → js::SVGGeometryElement` (6 miembro(s))
- `js::SVGLinearGradientElement → js::SVGGradientElement` (6 miembro(s))
- `js::SVGMPathElement → js::SVGElement` (3 miembro(s))
- `js::SVGMarkerElement → js::SVGElement` (19 miembro(s))
- `js::SVGMaskElement → js::SVGElement` (8 miembro(s))
- `js::SVGMetadataElement → js::SVGElement` (2 miembro(s))
- `js::SVGNumber` (1 miembro(s))
- `js::SVGNumberList` (10 miembro(s))
- `js::SVGPathElement → js::SVGGeometryElement` (2 miembro(s))
- `js::SVGPatternElement → js::SVGElement` (12 miembro(s))
- `js::SVGPointList` (10 miembro(s))
- `js::SVGPolygonElement → js::SVGGeometryElement` (4 miembro(s))
- `js::SVGPolylineElement → js::SVGGeometryElement` (4 miembro(s))
- `js::SVGPreserveAspectRatio` (16 miembro(s))
- `js::SVGRadialGradientElement → js::SVGGradientElement` (8 miembro(s))
- `js::SVGRectElement → js::SVGGeometryElement` (8 miembro(s))
- `js::SVGSVGElementEventMap → js::SVGElementEventMap` (18 miembro(s))
- `js::SVGSVGElement → js::SVGGraphicsElement` (51 miembro(s))
- `js::SVGScriptElement → js::SVGElement` (4 miembro(s))
- `js::SVGSetElement → js::SVGAnimationElement` (2 miembro(s))
- `js::SVGStopElement → js::SVGElement` (3 miembro(s))
- `js::SVGStringList` (10 miembro(s))
- `js::SVGStyleElement → js::SVGElement` (7 miembro(s))
- `js::SVGSwitchElement → js::SVGGraphicsElement` (2 miembro(s))
- `js::SVGSymbolElement → js::SVGElement` (4 miembro(s))
- `js::SVGTSpanElement → js::SVGTextPositioningElement` (2 miembro(s))
- `js::SVGTests` (2 miembro(s))
- `js::SVGTextContentElement → js::SVGGraphicsElement` (16 miembro(s))
- `js::SVGTextElement → js::SVGTextPositioningElement` (2 miembro(s))
- `js::SVGTextPathElement → js::SVGTextContentElement` (12 miembro(s))
- `js::SVGTextPositioningElement → js::SVGTextContentElement` (7 miembro(s))
- `js::SVGTitleElement → js::SVGElement` (2 miembro(s))
- `js::SVGTransform` (16 miembro(s))
- `js::SVGTransformList` (12 miembro(s))
- `js::SVGURIReference` (1 miembro(s))
- `js::SVGUnitTypes` (3 miembro(s))
- `js::SVGUseElement → js::SVGGraphicsElement` (7 miembro(s))
- `js::SVGViewElement → js::SVGElement` (4 miembro(s))
- `js::Screen` (7 miembro(s))
- `js::ScreenOrientationEventMap` (1 miembro(s))
- `js::ScreenOrientation → js::EventTarget` (6 miembro(s))
- `js::ScriptProcessorNodeEventMap` (1 miembro(s))
- `js::ScriptProcessorNode → js::AudioNode` (4 miembro(s))
- `js::SecurityPolicyViolationEvent → js::Event` (12 miembro(s))
- `js::Selection` (24 miembro(s))
- `js::ServiceWorkerEventMap → js::AbstractWorkerEventMap` (1 miembro(s))
- `js::ServiceWorker → js::EventTarget` (7 miembro(s))
- `js::ServiceWorkerContainerEventMap` (3 miembro(s))
- `js::ServiceWorkerContainer → js::EventTarget` (11 miembro(s))
- `js::ServiceWorkerRegistrationEventMap` (1 miembro(s))
- `js::ServiceWorkerRegistration → js::EventTarget` (14 miembro(s))
- `js::ShadowRootEventMap` (1 miembro(s))
- `js::ShadowRoot → js::DocumentFragment` (21 miembro(s))
- `js::SharedWorker → js::EventTarget` (4 miembro(s))
- `js::Slottable` (1 miembro(s))
- `js::SourceBufferEventMap` (5 miembro(s))
- `js::SourceBuffer → js::EventTarget` (17 miembro(s))
- `js::SourceBufferListEventMap` (2 miembro(s))
- `js::SourceBufferList → js::EventTarget` (6 miembro(s))
- `js::SpeechRecognitionAlternative` (2 miembro(s))
- `js::SpeechRecognitionResult` (4 miembro(s))
- `js::SpeechRecognitionResultList` (3 miembro(s))
- `js::SpeechSynthesisEventMap` (1 miembro(s))
- `js::SpeechSynthesis → js::EventTarget` (11 miembro(s))
- `js::SpeechSynthesisErrorEvent → js::SpeechSynthesisEvent` (1 miembro(s))
- `js::SpeechSynthesisEvent → js::Event` (5 miembro(s))
- `js::SpeechSynthesisUtteranceEventMap` (7 miembro(s))
- `js::SpeechSynthesisUtterance → js::EventTarget` (15 miembro(s))
- `js::SpeechSynthesisVoice` (5 miembro(s))
- `js::StereoPannerNode → js::AudioNode` (1 miembro(s))
- `js::Storage` (7 miembro(s))
- `js::StorageEvent → js::Event` (6 miembro(s))
- `js::StorageManager` (4 miembro(s))
- `js::StyleMedia` (2 miembro(s))
- `js::StylePropertyMap → js::StylePropertyMapReadOnly` (4 miembro(s))
- `js::StylePropertyMapReadOnly` (5 miembro(s))
- `js::StyleSheet` (7 miembro(s))
- `js::StyleSheetList` (3 miembro(s))
- `js::SubmitEvent → js::Event` (1 miembro(s))
- `js::SubtleCrypto` (12 miembro(s))
- `js::Text → js::CharacterData` (3 miembro(s))
- `js::TextDecoder → js::TextDecoderCommon` (1 miembro(s))
- `js::TextDecoderCommon` (3 miembro(s))
- `js::TextDecoderStream → js::GenericTransformStream` (5 miembro(s))
- `js::TextEncoder → js::TextEncoderCommon` (2 miembro(s))
- `js::TextEncoderCommon` (1 miembro(s))
- `js::TextEncoderStream → js::GenericTransformStream` (3 miembro(s))
- `js::TextEvent → js::UIEvent` (2 miembro(s))
- `js::TextMetrics` (12 miembro(s))
- `js::TextTrackEventMap` (1 miembro(s))
- `js::TextTrack → js::EventTarget` (13 miembro(s))
- `js::TextTrackCueEventMap` (2 miembro(s))
- `js::TextTrackCue → js::EventTarget` (9 miembro(s))
- `js::TextTrackCueList` (3 miembro(s))
- `js::TextTrackListEventMap` (3 miembro(s))
- `js::TextTrackList → js::EventTarget` (8 miembro(s))
- `js::TimeRanges` (3 miembro(s))
- `js::ToggleEvent → js::Event` (2 miembro(s))
- `js::Touch` (12 miembro(s))
- `js::TouchEvent → js::UIEvent` (7 miembro(s))
- `js::TouchList` (3 miembro(s))
- `js::TrackEvent → js::Event` (1 miembro(s))
- `js::TransformStream` (2 miembro(s))
- `js::TransformStreamDefaultController` (4 miembro(s))
- `js::TransitionEvent → js::Event` (3 miembro(s))
- `js::TreeWalker` (11 miembro(s))
- `js::UIEvent → js::Event` (4 miembro(s))
- `js::URL` (14 miembro(s))
- `js::URLSearchParams` (10 miembro(s))
- `js::UserActivation` (2 miembro(s))
- `js::VTTCue → js::TextTrackCue` (13 miembro(s))
- `js::VTTRegion` (8 miembro(s))
- `js::ValidityState` (11 miembro(s))
- `js::VideoColorSpace` (5 miembro(s))
- `js::VideoDecoderEventMap` (1 miembro(s))
- `js::VideoDecoder → js::EventTarget` (10 miembro(s))
- `js::VideoEncoderEventMap` (1 miembro(s))
- `js::VideoEncoder → js::EventTarget` (10 miembro(s))
- `js::VideoFrame` (14 miembro(s))
- `js::VideoPlaybackQuality` (4 miembro(s))
- `js::ViewTransition` (4 miembro(s))
- `js::VisualViewportEventMap` (2 miembro(s))
- `js::VisualViewport → js::EventTarget` (11 miembro(s))
- `js::WEBGL_color_buffer_float` (3 miembro(s))
- `js::WEBGL_compressed_texture_astc` (29 miembro(s))
- `js::WEBGL_compressed_texture_etc` (10 miembro(s))
- `js::WEBGL_compressed_texture_etc1` (1 miembro(s))
- `js::WEBGL_compressed_texture_pvrtc` (4 miembro(s))
- `js::WEBGL_compressed_texture_s3tc` (4 miembro(s))
- `js::WEBGL_compressed_texture_s3tc_srgb` (4 miembro(s))
- `js::WEBGL_debug_renderer_info` (2 miembro(s))
- `js::WEBGL_debug_shaders` (1 miembro(s))
- `js::WEBGL_depth_texture` (1 miembro(s))
- `js::WEBGL_draw_buffers` (35 miembro(s))
- `js::WEBGL_lose_context` (2 miembro(s))
- `js::WEBGL_multi_draw` (4 miembro(s))
- `js::WakeLock` (1 miembro(s))
- `js::WakeLockSentinelEventMap` (1 miembro(s))
- `js::WakeLockSentinel → js::EventTarget` (6 miembro(s))
- `js::WaveShaperNode → js::AudioNode` (2 miembro(s))
- `js::WebGL2RenderingContext → js::WebGL2RenderingContextBase` (437 miembro(s))
- `js::WebGL2RenderingContextBase` (350 miembro(s))
- `js::WebGL2RenderingContextOverloads` (18 miembro(s))
- `js::WebGLActiveInfo` (3 miembro(s))
- `js::WebGLContextEvent → js::Event` (1 miembro(s))
- `js::WebGLRenderingContext → js::WebGLRenderingContextBase` (18 miembro(s))
- `js::WebGLRenderingContextBase` (419 miembro(s))
- `js::WebGLRenderingContextOverloads` (18 miembro(s))
- `js::WebGLShaderPrecisionFormat` (3 miembro(s))
- `js::WebSocketEventMap` (4 miembro(s))
- `js::WebSocket → js::EventTarget` (18 miembro(s))
- `js::WebTransport` (8 miembro(s))
- `js::WebTransportBidirectionalStream` (2 miembro(s))
- `js::WebTransportDatagramDuplexStream` (7 miembro(s))
- `js::WebTransportError → js::DOMException` (2 miembro(s))
- `js::WheelEvent → js::MouseEvent` (7 miembro(s))
- `js::WindowEventMap → js::GlobalEventHandlersEventMap` (23 miembro(s))
- `js::Window → js::EventTarget` (211 miembro(s))
- `js::WindowEventHandlersEventMap` (18 miembro(s))
- `js::WindowEventHandlers` (20 miembro(s))
- `js::WindowLocalStorage` (1 miembro(s))
- `js::WindowOrWorkerGlobalScope` (18 miembro(s))
- `js::WindowSessionStorage` (1 miembro(s))
- `js::WorkerEventMap → js::AbstractWorkerEventMap` (2 miembro(s))
- `js::Worker → js::EventTarget` (7 miembro(s))
- `js::Worklet` (1 miembro(s))
- `js::WritableStream` (4 miembro(s))
- `js::WritableStreamDefaultController` (2 miembro(s))
- `js::WritableStreamDefaultWriter` (7 miembro(s))
- `js::XMLDocument → js::Document` (2 miembro(s))
- `js::XMLHttpRequestEventMap → js::XMLHttpRequestEventTargetEventMap` (1 miembro(s))
- `js::XMLHttpRequest → js::XMLHttpRequestEventTarget` (26 miembro(s))
- `js::XMLHttpRequestEventTargetEventMap` (7 miembro(s))
- `js::XMLHttpRequestEventTarget → js::EventTarget` (9 miembro(s))
- `js::XMLHttpRequestUpload → js::XMLHttpRequestEventTarget` (2 miembro(s))
- `js::XMLSerializer` (1 miembro(s))
- `js::XPathEvaluatorBase` (3 miembro(s))
- `js::XPathExpression` (1 miembro(s))
- `js::XPathResult` (19 miembro(s))
- `js::XSLTProcessor` (8 miembro(s))
- `js::Console` (20 miembro(s))
- `js::CustomElementConstructor` (1 miembro(s))
- `js::HTMLElementTagNameMap` (112 miembro(s))
- `js::HTMLElementDeprecatedTagNameMap` (29 miembro(s))
- `js::SVGElementTagNameMap` (63 miembro(s))
- `js::MathMLElementTagNameMap` (29 miembro(s))

## `std/js/es5_generated`

Generado con `pengu ts-bindgen`; no editar a mano.

Realm: `js_es5_generated`.
Invoca: `std/js/types`.

Globales (30): `NaN: double`, `Infinity: double`, `Object: js::ObjectConstructor`, `Function: js::FunctionConstructor`, `String: js::StringConstructor`, `Boolean: js::BooleanConstructor`, `Number: js::NumberConstructor`, `Math: js::Math`, `Date: js::DateConstructor`, `RegExp: js::RegExpConstructor`, `Error: js::ErrorConstructor`, `EvalError: js::EvalErrorConstructor` … y 18 más.

Namespaces: `Intl` (3 miembro(s)).

Funciones del host (`declare`, 11):

- `eval(x: string) -> any`
- `parseInt(string: string, radix: double?) -> double`
- `parseFloat(string: string) -> double`
- `isNaN(number: double) -> bool`
- `isFinite(number: double) -> bool`
- `decodeURI(encodedURI: string) -> string`
- `decodeURIComponent(encodedURIComponent: string) -> string`
- `encodeURI(uri: string) -> string`
- `encodeURIComponent(uriComponent: any) -> string`
- `escape(string: string) -> string`
- `unescape(string: string) -> string`

Tipos del host (72, 597 miembro(s)):

- `js::Symbol` (2 miembro(s))
- `js::PropertyDescriptor` (6 miembro(s))
- `js::PropertyDescriptorMap` (1 miembro(s))
- `js::Object` (7 miembro(s))
- `js::ObjectConstructor` (15 miembro(s))
- `js::Function` (8 miembro(s))
- `js::FunctionConstructor` (2 miembro(s))
- `js::CallableFunction → js::Function` (3 miembro(s))
- `js::NewableFunction → js::Function` (3 miembro(s))
- `js::IArguments` (3 miembro(s))
- `js::String` (22 miembro(s))
- `js::StringConstructor` (3 miembro(s))
- `js::Boolean` (1 miembro(s))
- `js::BooleanConstructor` (2 miembro(s))
- `js::Number` (5 miembro(s))
- `js::NumberConstructor` (7 miembro(s))
- `js::TemplateStringsArray → js::ReadonlyArray` (1 miembro(s))
- `js::ImportCallOptions` (2 miembro(s))
- `js::ImportAssertions` (1 miembro(s))
- `js::ImportAttributes` (1 miembro(s))
- `js::Math` (26 miembro(s))
- `js::Date` (43 miembro(s))
- `js::DateConstructor` (5 miembro(s))
- `js::RegExpMatchArray → js::Array` (2 miembro(s))
- `js::RegExpExecArray → js::Array` (2 miembro(s))
- `js::RegExp` (8 miembro(s))
- `js::RegExpConstructor` (7 miembro(s))
- `js::Error` (3 miembro(s))
- `js::ErrorConstructor` (2 miembro(s))
- `js::EvalErrorConstructor → js::ErrorConstructor` (2 miembro(s))
- `js::RangeErrorConstructor → js::ErrorConstructor` (2 miembro(s))
- `js::ReferenceErrorConstructor → js::ErrorConstructor` (2 miembro(s))
- `js::SyntaxErrorConstructor → js::ErrorConstructor` (2 miembro(s))
- `js::TypeErrorConstructor → js::ErrorConstructor` (2 miembro(s))
- `js::URIErrorConstructor → js::ErrorConstructor` (2 miembro(s))
- `js::JSON` (2 miembro(s))
- `js::ReadonlyArray` (16 miembro(s))
- `js::ConcatArray` (4 miembro(s))
- `js::Array` (23 miembro(s))
- `js::ArrayConstructor` (3 miembro(s))
- `js::TypedPropertyDescriptor` (6 miembro(s))
- `js::PromiseLike` (1 miembro(s))
- `js::Promise` (2 miembro(s))
- `js::ArrayLike` (2 miembro(s))
- `js::WeakKeyTypes` (1 miembro(s))
- `js::ArrayBuffer` (2 miembro(s))
- `js::ArrayBufferTypes` (1 miembro(s))
- `js::ArrayBufferConstructor` (3 miembro(s))
- `js::ArrayBufferView` (3 miembro(s))
- `js::DataView` (19 miembro(s))
- `js::DataViewConstructor` (2 miembro(s))
- `js::Int8Array` (28 miembro(s))
- `js::Int8ArrayConstructor` (5 miembro(s))
- `js::Uint8Array` (28 miembro(s))
- `js::Uint8ArrayConstructor` (5 miembro(s))
- `js::Uint8ClampedArray` (28 miembro(s))
- `js::Uint8ClampedArrayConstructor` (5 miembro(s))
- `js::Int16Array` (28 miembro(s))
- `js::Int16ArrayConstructor` (5 miembro(s))
- `js::Uint16Array` (28 miembro(s))
- `js::Uint16ArrayConstructor` (5 miembro(s))
- `js::Int32Array` (28 miembro(s))
- `js::Int32ArrayConstructor` (5 miembro(s))
- `js::Uint32Array` (28 miembro(s))
- `js::Uint32ArrayConstructor` (5 miembro(s))
- `js::Float32Array` (28 miembro(s))
- `js::Float32ArrayConstructor` (5 miembro(s))
- `js::Float64Array` (28 miembro(s))
- `js::Float64ArrayConstructor` (5 miembro(s))
- `js::String` (1 miembro(s))
- `js::Number` (1 miembro(s))
- `js::Date` (3 miembro(s))

## `std/js/fetch_generated`

Generado con `pengu ts-bindgen`; no editar a mano.

Realm: `js_fetch_generated`.
Invoca: `std/js/types`.

Alias (2): `echo js::DOMHighResTimeStamp = double`, `echo js::ReadableStreamReaderMode = string`.

Globales (1): `caches: js::CacheStorage`.

Namespaces: `CSS` (67 miembro(s)), `WebAssembly` (14 miembro(s)).

Funciones del host (`declare`, 1):

- `fetch(input: any, init: js::RequestInit?) -> any<js::Response>`

Tipos del host (34, 184 miembro(s)):

- `js::AddEventListenerOptions → js::EventListenerOptions` (3 miembro(s))
- `js::CacheQueryOptions` (3 miembro(s))
- `js::EventListenerOptions` (1 miembro(s))
- `js::MultiCacheQueryOptions → js::CacheQueryOptions` (1 miembro(s))
- `js::ReadableStreamGetReaderOptions` (1 miembro(s))
- `js::ReadableStreamReadDoneResult` (2 miembro(s))
- `js::ReadableStreamReadValueResult` (2 miembro(s))
- `js::ReadableWritablePair` (2 miembro(s))
- `js::RequestInit` (14 miembro(s))
- `js::ResponseInit` (3 miembro(s))
- `js::StreamPipeOptions` (4 miembro(s))
- `js::AbortController` (2 miembro(s))
- `js::AbortSignalEventMap` (1 miembro(s))
- `js::AbortSignal → js::EventTarget` (6 miembro(s))
- `js::Blob` (7 miembro(s))
- `js::Body` (8 miembro(s))
- `js::Cache` (7 miembro(s))
- `js::CacheStorage` (5 miembro(s))
- `js::Event` (22 miembro(s))
- `js::EventListenerObject` (1 miembro(s))
- `js::EventTarget` (3 miembro(s))
- `js::File → js::Blob` (3 miembro(s))
- `js::FormData` (7 miembro(s))
- `js::Headers` (7 miembro(s))
- `js::ReadableStream` (6 miembro(s))
- `js::ReadableStreamBYOBReader → js::ReadableStreamGenericReader` (2 miembro(s))
- `js::ReadableStreamDefaultReader → js::ReadableStreamGenericReader` (2 miembro(s))
- `js::ReadableStreamGenericReader` (2 miembro(s))
- `js::Request → js::Body` (14 miembro(s))
- `js::Response → js::Body` (8 miembro(s))
- `js::URL` (14 miembro(s))
- `js::URLSearchParams` (10 miembro(s))
- `js::WritableStream` (4 miembro(s))
- `js::WritableStreamDefaultWriter` (7 miembro(s))

## `std/js/performance_generated`

Generado con `pengu ts-bindgen`; no editar a mano.

Realm: `js_performance_generated`.
Invoca: `std/js/types`.

Alias (1): `echo js::DOMHighResTimeStamp = double`.

Globales (1): `performance: js::Performance`.

Namespaces: `CSS` (67 miembro(s)), `WebAssembly` (14 miembro(s)).

Tipos del host (23, 143 miembro(s)):

- `js::AddEventListenerOptions → js::EventListenerOptions` (3 miembro(s))
- `js::EventListenerOptions` (1 miembro(s))
- `js::PerformanceMarkOptions` (2 miembro(s))
- `js::PerformanceMeasureOptions` (4 miembro(s))
- `js::PerformanceObserverInit` (3 miembro(s))
- `js::AbortSignalEventMap` (1 miembro(s))
- `js::AbortSignal → js::EventTarget` (6 miembro(s))
- `js::Event` (22 miembro(s))
- `js::EventCounts` (1 miembro(s))
- `js::EventListenerObject` (1 miembro(s))
- `js::EventTarget` (3 miembro(s))
- `js::PerformanceEventMap` (1 miembro(s))
- `js::Performance → js::EventTarget` (18 miembro(s))
- `js::PerformanceEntry` (5 miembro(s))
- `js::PerformanceMark → js::PerformanceEntry` (1 miembro(s))
- `js::PerformanceMeasure → js::PerformanceEntry` (1 miembro(s))
- `js::PerformanceNavigation` (7 miembro(s))
- `js::PerformanceNavigationTiming → js::PerformanceResourceTiming` (11 miembro(s))
- `js::PerformanceObserver` (3 miembro(s))
- `js::PerformanceObserverEntryList` (3 miembro(s))
- `js::PerformanceResourceTiming → js::PerformanceEntry` (20 miembro(s))
- `js::PerformanceServerTiming` (4 miembro(s))
- `js::PerformanceTiming` (22 miembro(s))

## `std/js/storage_generated`

Generado con `pengu ts-bindgen`; no editar a mano.

Realm: `js_storage_generated`.
Invoca: `std/js/types`.

Alias (1): `echo js::DOMHighResTimeStamp = double`.

Globales (2): `localStorage: js::Storage`, `sessionStorage: js::Storage`.

Namespaces: `CSS` (67 miembro(s)), `WebAssembly` (14 miembro(s)).

Tipos del host (13, 82 miembro(s)):

- `js::AddEventListenerOptions → js::EventListenerOptions` (3 miembro(s))
- `js::EventInit` (3 miembro(s))
- `js::EventListenerOptions` (1 miembro(s))
- `js::StorageEventInit → js::EventInit` (5 miembro(s))
- `js::AbortSignalEventMap` (1 miembro(s))
- `js::AbortSignal → js::EventTarget` (6 miembro(s))
- `js::Event` (22 miembro(s))
- `js::EventListenerObject` (1 miembro(s))
- `js::EventTarget` (3 miembro(s))
- `js::Storage` (7 miembro(s))
- `js::StorageEvent → js::Event` (6 miembro(s))
- `js::URL` (14 miembro(s))
- `js::URLSearchParams` (10 miembro(s))
