// Runtime de JavaScript (§7 del plan).
//
// Es un único módulo ESM (`pengu_rt.mjs`) que se escribe junto a los módulos
// del programa. Solo contiene lo que el código generado no puede expresar por
// sí mismo: formato de números idéntico a C++ (`%g`), presentación de valores
// para `echo`/interpolación, contenedores auxiliares y las primitivas de la
// stdlib que en C++ eran `::pengu::*`.
//
// Regla: nada de estado global salvo los argumentos del programa; todo lo
// demás son funciones puras o clases de datos.

export const RUNTIME_JS = `// Runtime generado por pengu 0.1.0. No editar a mano.
// Módulo ESM: se importa como \`rt\` desde los módulos del programa.

import * as fs from "node:fs";
import * as os from "node:os";
import * as child_process from "node:child_process";

// --- Presentación de valores -------------------------------------------

// Mismo formato que \`std::ostringstream << double\` (printf %g, 6 dígitos
// significativos): 1 -> "1", 1/3 -> "0.333333", 1e21 -> "1e+21".
export function fmt_float(value) {
  if (Number.isNaN(value)) return "nan";
  if (value === Infinity) return "inf";
  if (value === -Infinity) return "-inf";
  if (value === 0) return Object.is(value, -0) ? "-0" : "0";
  const exponent = Math.floor(Math.log10(Math.abs(value)));
  if (exponent < -4 || exponent >= 6) {
    const [mantissa, exp] = value.toExponential(5).split("e");
    const trimmed = trim_zeros(mantissa);
    const digits = exp.replace(/^[+-]/, "").padStart(2, "0");
    return trimmed + "e" + (exp.startsWith("-") ? "-" : "+") + digits;
  }
  return trim_zeros(value.toFixed(Math.max(0, 5 - exponent)));
}

function trim_zeros(text) {
  return text.includes(".") ? text.replace(/\\.?0+$/, "") : text;
}

// Caja con la pista de tipo estático. En C++ \`Value\` guarda un \`to_string\`
// resuelto en tiempo de compilación; aquí el tipo se pierde al pasar por
// \`any\`, así que la caja lo recuerda para enteros y flotantes.
export const BOX_KINDS = Object.freeze({ int: "int", float: "float" });

export function box(value, kind) {
  return { __pengu_box: kind, value };
}

function is_box(value) {
  return value !== null && typeof value === "object" && typeof value.__pengu_box === "string";
}

// Texto de un valor. Es la versión dinámica de \`::pengu::to_string(value)\`.
export function show(value) {
  if (value === null || value === undefined) return "none";
  if (is_box(value)) {
    return value.__pengu_box === "float" ? fmt_float(value.value) : String(value.value);
  }
  switch (typeof value) {
    case "string":
      return value;
    case "boolean":
      return value ? "true" : "false";
    case "bigint":
      return value.toString();
    case "number":
      return Number.isInteger(value) ? String(value) : fmt_float(value);
    case "function":
      return "<function>";
    default:
      break;
  }
  if (value instanceof Set) return show_set(value);
  if (value instanceof Map) return show_map(value);
  if (Array.isArray(value)) return show_list(value);
  if (typeof value.to_string === "function") return value.to_string();
  return String(value);
}

// Las tuplas se representan como arrays (el tipo no existe en runtime), así
// que la interpolación pide explícitamente el formato de tupla entre paréntesis.
export function show_tuple(value) {
  return "(" + value.map((item) => show(item)).join(", ") + ")";
}

function show_list(items) {
  return "[" + items.map((item) => show(item)).join(", ") + "]";
}

function show_set(items) {
  return "{" + [...items].map((item) => show(item)).join(", ") + "}";
}

function show_map(entries) {
  const parts = [];
  for (const [key, item] of entries) parts.push(show(key) + ": " + show(item));
  return "{" + parts.join(", ") + "}";
}

// --- Orden y rangos -----------------------------------------------------

export const Ordering = Object.freeze({ Less: -1, Equal: 0, Greater: 1 });

// \`a..b\` / \`a..<b\`: se recorre con \`for (const i of rt.range(a, b, false))\`.
export function range(start, end, inclusive) {
  // Los índices son number aunque el rango venga de un size_t: se normaliza
  // para que un extremo BigInt no rompa la aritmética.
  const desde = Number(start);
  const hasta = Number(end);
  const last = inclusive ? hasta : hasta - 1;
  const out = [];
  if (desde <= last) {
    for (let value = desde; value <= last; value += 1) out.push(value);
  }
  return out;
}

// --- Contenedores -------------------------------------------------------

export function len(value) {
  if (typeof value === "string") return value.length;
  if (typeof value === "bigint") return 0;
  return value.length === undefined ? value.size : value.length;
}

export function vec_at(items, index) {
  if (index < 0 || index >= items.length) {
    panic("índice " + String(index) + " fuera de rango (tamaño " + String(items.length) + ")");
  }
  return items[index];
}

export function map_at(map, key) {
  if (!map.has(key)) panic("no existe la clave en el mapa");
  return map.get(key);
}

export function pop_back_checked(items) {
  if (items.length === 0) panic("pop() sobre un contenedor vacío");
  return items.pop();
}

// Suma y producto de un vector (con el acumulador del tipo de los elementos).
export function sum(items) {
  let total = 0n;
  let flotante = false;
  for (const item of items) {
    if (typeof item === "bigint") total += item;
    else if (typeof item === "number") {
      if (!Number.isInteger(item)) flotante = true;
      total = flotante ? Number(total) + item : BigInt(total) + BigInt(item);
    }
  }
  return flotante ? Number(total) : total;
}

export function product(items) {
  let total = 1n;
  let flotante = false;
  for (const item of items) {
    if (typeof item === "bigint") total *= item;
    else if (typeof item === "number") {
      if (!Number.isInteger(item)) flotante = true;
      total = flotante ? Number(total) * item : BigInt(total) * BigInt(item);
    }
  }
  return flotante ? Number(total) : total;
}

// Comparación de tres vías de C++ (a <=> b): -1, 0 o 1 según el orden.
export function compare(a, b) {
  a = is_cell(a) ? a.value : a;
  b = is_cell(b) ? b.value : b;
  if (typeof a === "string" || typeof b === "string") {
    const izquierda = String(a);
    const derecha = String(b);
    if (izquierda < derecha) return Ordering.Less;
    return izquierda > derecha ? Ordering.Greater : Ordering.Equal;
  }
  if (a < b) return Ordering.Less;
  return a > b ? Ordering.Greater : Ordering.Equal;
}

export function contains(container, value) {
  if (typeof container === "string") return container.includes(value);
  if (Array.isArray(container)) return container.includes(value);
  return container.has(value);
}

// --- Errores ------------------------------------------------------------

export function panic(message) {
  throw new Error(message);
}

export function assert_that(condition) {
  if (!condition) panic("aserción fallida");
}

export function assert_fail(message) {
  panic(message);
}

export function or_panic(value, message) {
  if (value === null || value === undefined) panic(message);
  return value;
}

// --- Entrada y salida ---------------------------------------------------

let program_args = [];

export function set_args(argv) {
  program_args = argv.slice();
}

export function args() {
  return program_args.slice();
}

export function write_values(values, newline) {
  let text = "";
  for (const value of values) text += show(value);
  if (newline) text += "\\n";
  process.stdout.write(text);
}

export function eprint_values(values, newline) {
  let text = "";
  for (const value of values) text += show(value);
  if (newline) text += "\\n";
  process.stderr.write(text);
}

export function format_values(values) {
  let text = "";
  for (const value of values) text += show(value);
  return text;
}

export function flush() {
  return undefined;
}

export function is_terminal() {
  return process.stdout.isTTY === true;
}

// --- Semántica de valor ----------------------------------------------------
// C++ copia en cada asignación, argumento y \`return\`; JS comparte objetos.
// \`clone\` reproduce la copia en los puntos donde el checker marca un tipo con
// semántica de valor (§3).

export const CELL = Symbol("pengu.ref");

// Celda de referencia para tipos de valor (cadenas, números): es lo que
// permite que un metodo mut escriba de vuelta en la variable del llamante.
export function ref(get, set) {
  return {
    [CELL]: true,
    get value() {
      return get();
    },
    set value(dato) {
      set(dato);
    },
  };
}

export function is_cell(value) {
  return typeof value === "object" && value !== null && value[CELL] === true;
}

export function clone(value) {
  if (value === null || typeof value !== "object") return value;
  // Una Promise es un identificador: se comparte, no se copia.
  if (value instanceof Promise) return value;
  if (Array.isArray(value)) return value.map(clone);
  if (value instanceof Map) {
    const copia = new Map();
    for (const [clave, dato] of value) copia.set(clone(clave), clone(dato));
    return copia;
  }
  if (value instanceof Set) {
    const copia = new Set();
    for (const dato of value) copia.add(clone(dato));
    return copia;
  }
  if (value instanceof WeakRef) return value;
  if (is_cell(value)) return value;
  if (Object.isFrozen(value)) return value;
  if (typeof value._clone === "function") return value._clone();
  const copia = Object.create(Object.getPrototypeOf(value));
  for (const clave of Object.keys(value)) copia[clave] = clone(value[clave]);
  return copia;
}

// --- Aritmética de <cmath> -------------------------------------------------
// Las que \`Math\` no ofrece con la misma semántica que C++.

export function round(value) {
  if (Number.isNaN(value) || value === 0) return value;
  return Math.sign(value) * Math.round(Math.abs(value));
}

// \`std::nearbyint\` redondea a par (bancario), no hacia arriba.
export function nearbyint(value) {
  if (!Number.isFinite(value)) return value;
  const floor = Math.floor(value);
  const diff = value - floor;
  if (diff === 0.5 && floor % 2 !== 0) return floor + 1;
  if (diff === 0.5) return floor;
  return Math.round(value);
}

export function exp2(value) {
  return 2 ** value;
}

export function fmod(left, right) {
  return left % right;
}

export function remainder(left, right) {
  return left - right * nearbyint(left / right);
}

export function fdim(left, right) {
  const diff = left - right;
  return diff > 0 ? diff : 0;
}

export function fma(a, b, c) {
  return a * b + c;
}

export function copysign(magnitude, sign) {
  const negative = sign < 0 || Object.is(sign, -0);
  return negative ? -Math.abs(magnitude) : Math.abs(magnitude);
}

export function signbit(value) {
  return value < 0 || Object.is(value, -0);
}

export function is_infinite(value) {
  return value === Infinity || value === -Infinity;
}

export function clamp(value, low, high) {
  return Math.min(Math.max(value, low), high);
}

export function gcd(left, right) {
  let a = Math.abs(left);
  let b = Math.abs(right);
  while (b !== 0) {
    const rest = a % b;
    a = b;
    b = rest;
  }
  return a;
}

export function lcm(left, right) {
  if (left === 0 || right === 0) return 0;
  return Math.abs(left * right) / gcd(left, right);
}

export function infinite() {
  return Infinity;
}

export function nan() {
  return NaN;
}

// --- Cadenas ------------------------------------------------------------
//
// Los declare de std/string trabajan con ref<string>, pero la cadena se pasa
// por valor: en JavaScript las cadenas son inmutables y las variantes *_raw
// solo leen. find devuelve la longitud cuando no encuentra, que es el
// centinela que usa std/string (equivalente a npos en C++).

// Las variantes *_raw reciben ref<string> en PenguScript: la celda puede
// llegar como tal o ya desenvuelta segun el punto de llamada.
function text_of(value) {
  return is_cell(value) ? value.value : value;
}

export function find_raw(texto, buscado) {
  texto = text_of(texto);
  buscado = text_of(buscado);
  const posicion = texto.indexOf(buscado);
  return posicion < 0 ? texto.length : posicion;
}

export function rfind_raw(texto, buscado) {
  texto = text_of(texto);
  buscado = text_of(buscado);
  const posicion = texto.lastIndexOf(buscado);
  return posicion < 0 ? texto.length : posicion;
}

export function find_from_raw(texto, buscado, desde) {
  texto = text_of(texto);
  buscado = text_of(buscado);
  desde = text_of(desde);
  const posicion = desde > texto.length ? -1 : texto.indexOf(buscado, desde);
  return posicion < 0 ? texto.length : posicion;
}

export function trim_raw(texto) {
  texto = text_of(texto);
  return texto.trim();
}

export function to_upper_raw(texto) {
  texto = text_of(texto);
  return texto.toUpperCase();
}

export function to_lower_raw(texto) {
  texto = text_of(texto);
  return texto.toLowerCase();
}

export function split_raw(texto, separador) {
  texto = text_of(texto);
  separador = text_of(separador);
  if (separador.length === 0) return Array.from(texto);
  return texto.split(separador);
}

export function split_whitespace_raw(texto) {
  texto = text_of(texto);
  const limpio = texto.trim();
  return limpio.length === 0 ? [] : limpio.split(/\\s+/);
}

export function replace_first_raw(texto, viejo, nuevo) {
  texto = text_of(texto);
  viejo = text_of(viejo);
  nuevo = text_of(nuevo);
  const posicion = texto.indexOf(viejo);
  if (posicion < 0) return texto;
  return texto.slice(0, posicion) + nuevo + texto.slice(posicion + viejo.length);
}

export function reverse_raw(texto) {
  texto = text_of(texto);
  return Array.from(texto).reverse().join("");
}

export function char_count_raw(texto) {
  texto = text_of(texto);
  return Array.from(texto).length;
}

export function parse_int_raw(texto) {
  texto = text_of(texto);
  const limpio = texto.trim();
  if (!/^[+-]?\\d+$/.test(limpio)) return null;
  const valor = Number(limpio);
  if (!Number.isSafeInteger(valor)) return null;
  return valor;
}

export function parse_double_raw(texto) {
  texto = text_of(texto);
  const limpio = texto.trim();
  if (limpio.length === 0 || !/^[+-]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][+-]?\\d+)?$/.test(limpio)) return null;
  return Number(limpio);
}

export function bytes_raw(texto) {
  texto = text_of(texto);
  return Array.from(new TextEncoder().encode(texto));
}


// --- Entorno, sistema de archivos y procesos ----------------------------

export function fs_read_to_string(ruta) {
  try {
    return fs.readFileSync(ruta, "utf8");
  } catch {
    return null;
  }
}

export function fs_read_bytes(ruta) {
  try {
    return Array.from(fs.readFileSync(ruta));
  } catch {
    return null;
  }
}

export function fs_write_string(ruta, contenido) {
  try {
    fs.writeFileSync(ruta, contenido, "utf8");
    return true;
  } catch {
    return false;
  }
}

export function fs_write_bytes(ruta, bytes) {
  try {
    fs.writeFileSync(ruta, Buffer.from(bytes));
    return true;
  } catch {
    return false;
  }
}

export function fs_append_string(ruta, contenido) {
  try {
    fs.appendFileSync(ruta, contenido, "utf8");
    return true;
  } catch {
    return false;
  }
}

export function fs_exists(ruta) {
  return fs.existsSync(ruta);
}

export function fs_is_file(ruta) {
  try {
    return fs.statSync(ruta).isFile();
  } catch {
    return false;
  }
}

export function fs_is_dir(ruta) {
  try {
    return fs.statSync(ruta).isDirectory();
  } catch {
    return false;
  }
}

export function fs_remove(ruta) {
  try {
    fs.rmSync(ruta, { recursive: true, force: false });
    return true;
  } catch {
    return false;
  }
}

export function fs_create_dir(ruta) {
  try {
    fs.mkdirSync(ruta, { recursive: true });
    return true;
  } catch {
    return false;
  }
}

export function fs_list_dir(ruta) {
  try {
    return fs.readdirSync(ruta).sort();
  } catch {
    return [];
  }
}

export function fs_file_size(ruta) {
  try {
    return fs.statSync(ruta).size;
  } catch {
    return null;
  }
}

export function fs_rename(desde, hasta) {
  try {
    fs.renameSync(desde, hasta);
    return true;
  } catch {
    return false;
  }
}

export function fs_copy(desde, hasta) {
  try {
    fs.copyFileSync(desde, hasta);
    return true;
  } catch {
    return false;
  }
}

export function fs_canonicalize(ruta) {
  try {
    return fs.realpathSync(ruta);
  } catch {
    return null;
  }
}

// --- Entorno (os) -------------------------------------------------------

export function os_args() {
  return program_args.slice();
}

export function os_get_env(nombre) {
  const valor = process.env[nombre];
  return valor === undefined ? null : valor;
}

export function os_set_env(nombre, valor) {
  try {
    process.env[nombre] = valor;
    return true;
  } catch {
    return false;
  }
}

export function os_exit(codigo) {
  process.exit(Number(codigo));
}

export function os_pid() {
  return process.pid;
}

export function os_home_dir() {
  const valor = process.env.HOME ?? process.env.USERPROFILE;
  return valor === undefined ? null : valor;
}

export function os_temp_dir() {
  return os.tmpdir();
}

export function os_current_dir() {
  try {
    return process.cwd();
  } catch {
    return null;
  }
}

export function os_platform() {
  return process.platform;
}

export function os_arch() {
  // C++ nombra la arquitectura como la espera uname (x86_64, aarch64).
  const nombres = { x64: "x86_64", arm64: "aarch64", ia32: "i686" };
  return nombres[process.arch] ?? process.arch;
}

export function os_cpu_count() {
  return os.cpus().length === 0 ? 1 : os.cpus().length;
}

// --- Tiempo -------------------------------------------------------------

export function now_millis() {
  return Date.now();
}

export function now_seconds() {
  return Math.floor(Date.now() / 1000);
}

export function now_nanos() {
  return BigInt(Date.now()) * 1000000n;
}

export function monotonic_millis() {
  return Math.floor(performanceNowMs());
}

export function monotonic_nanos() {
  return BigInt(Math.floor(performanceNowMs() * 1e6));
}

function performanceNowMs() {
  return typeof performance !== "undefined" && typeof performance.now === "function" ? performance.now() : Date.now();
}

export function sleep_millis(millis) {
  const total = Number(millis);
  if (total <= 0) return;
  const final = performanceNowMs() + total;
  while (performanceNowMs() < final) {
    // Espera activa: el runtime es síncrono, como el backend C++.
  }
}

export function time_parts(millis) {
  const fecha = new Date(Number(millis));
  return [
    fecha.getFullYear(),
    fecha.getMonth() + 1,
    fecha.getDate(),
    fecha.getHours(),
    fecha.getMinutes(),
    fecha.getSeconds(),
  ];
}

export function format_datetime(millis) {
  const [anio, mes, dia, hora, minuto, segundo] = time_parts(millis);
  const dos = (valor) => String(valor).padStart(2, "0");
  return String(anio).padStart(4, "0") + "-" + dos(mes) + "-" + dos(dia) + " " + dos(hora) + ":" + dos(minuto) + ":" + dos(segundo);
}

// --- Azar: generador xorshift128+ reproducible con semilla ---------------

const RANDOM_STATE = { a: 0x9e3779b9n, b: 0x243f6a88n };

export function random_seed(semilla) {
  const valor = BigInt.asUintN(64, BigInt(Number(semilla))) ^ 0x9e3779b97f4a7c15n;
  RANDOM_STATE.a = valor === 0n ? 1n : valor;
  RANDOM_STATE.b = 0x243f6a8885a308d3n;
}

function random_next() {
  let x = RANDOM_STATE.a;
  const y = RANDOM_STATE.b;
  RANDOM_STATE.a = y;
  x ^= BigInt.asUintN(64, x << 23n);
  RANDOM_STATE.b = BigInt.asUintN(64, x ^ y ^ (x >> 17n) ^ (y >> 26n));
  return RANDOM_STATE.b;
}

export function random_float() {
  const valor = random_next() >> 11n;
  return Number(valor) / 9007199254740992;
}

export function random_int(desde, hasta) {
  const bajo = Number(desde);
  const alto = Number(hasta);
  if (alto <= bajo) return bajo;
  return bajo + Math.floor(random_float() * (alto - bajo));
}

export function random_bool() {
  return random_float() < 0.5;
}

export function random_float_range(desde, hasta) {
  return Number(desde) + random_float() * (Number(hasta) - Number(desde));
}

// --- Procesos -----------------------------------------------------------

export function process_run(comando) {
  try {
    const resultado = child_process.spawnSync(text_of(comando), { shell: true, encoding: "utf8" });
    return resultado.status === null ? 1 : resultado.status;
  } catch {
    return 1;
  }
}

export function process_output(comando) {
  try {
    const resultado = child_process.spawnSync(text_of(comando), { shell: true, encoding: "utf8" });
    return resultado.stdout ?? "";
  } catch {
    return "";
  }
}

export function process_status(comando) {
  return process_run(comando) === 0;
}

export function process_exit(codigo) {
  process.exit(Number(codigo));
}

// --- Codificación -------------------------------------------------------

export function base64_raw(texto) {
  return Buffer.from(text_of(texto), "utf8").toString("base64");
}

export function base64_decode_raw(texto) {
  try {
    return decode_utf8(Buffer.from(text_of(texto), "base64"));
  } catch {
    return null;
  }
}

export function hex_raw(texto) {
  return Buffer.from(text_of(texto), "utf8").toString("hex");
}

export function hex_decode_raw(texto) {
  const limpio = text_of(texto);
  if (!/^([0-9a-fA-F]{2})*$/.test(limpio)) return null;
  return decode_utf8(Buffer.from(limpio, "hex"));
}

export function url_raw(texto) {
  return encodeURIComponent(text_of(texto));
}

export function url_decode_raw(texto) {
  try {
    return decodeURIComponent(text_of(texto));
  } catch {
    return null;
  }
}

export function bytes_of(texto) {
  return Array.from(new TextEncoder().encode(text_of(texto)));
}

export function text_of_bytes(datos) {
  return new TextDecoder("utf-8", { fatal: true }).decode(new Uint8Array(datos));
}

export function from_bytes(datos) {
  try {
    return text_of_bytes(datos);
  } catch {
    return null;
  }
}

export function is_utf8(texto) {
  try {
    new TextDecoder("utf-8", { fatal: true }).decode(new TextEncoder().encode(text_of(texto)));
    return true;
  } catch {
    return false;
  }
}

function decode_utf8(buffer) {
  return new TextDecoder("utf-8").decode(new Uint8Array(buffer));
}

// --- Hash ---------------------------------------------------------------

export function fnv1a32(texto) {
  const datos = new TextEncoder().encode(text_of(texto));
  let hash = 0x811c9dc5;
  for (const byte of datos) {
    hash ^= byte;
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash;
}

export function fnv1a64(texto) {
  const datos = new TextEncoder().encode(text_of(texto));
  let hash = 0xcbf29ce484222325n;
  const primo = 0x100000001b3n;
  const mascara = 0xffffffffffffffffn;
  for (const byte of datos) {
    hash ^= BigInt(byte);
    hash = (hash * primo) & mascara;
  }
  return hash;
}

export function djb2(texto) {
  const datos = new TextEncoder().encode(text_of(texto));
  let hash = 5381;
  for (const byte of datos) hash = ((Math.imul(hash, 33) >>> 0) + byte) >>> 0;
  return hash >>> 0;
}

const CRC_TABLE = (() => {
  const tabla = new Uint32Array(256);
  for (let i = 0; i < 256; i += 1) {
    let valor = i;
    for (let bit = 0; bit < 8; bit += 1) {
      valor = (valor & 1) === 1 ? (0xedb88320 ^ (valor >>> 1)) >>> 0 : valor >>> 1;
    }
    tabla[i] = valor >>> 0;
  }
  return tabla;
})();

export function crc32(texto) {
  const datos = new TextEncoder().encode(text_of(texto));
  let crc = 0xffffffff;
  for (const byte of datos) crc = (CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8)) >>> 0;
  return (crc ^ 0xffffffff) >>> 0;
}

export function adler32(texto) {
  const datos = new TextEncoder().encode(text_of(texto));
  let a = 1;
  let b = 0;
  for (const byte of datos) {
    a = (a + byte) % 65521;
    b = (b + a) % 65521;
  }
  return ((b << 16) | a) >>> 0;
}

export function hex32(valor) {
  return (Number(valor) >>> 0).toString(16).padStart(8, "0");
}

export function hex64(valor) {
  return BigInt.asUintN(64, BigInt(valor)).toString(16).padStart(16, "0");
}

// --- Formato ------------------------------------------------------------

export function format_fixed(valor, decimales) {
  const texto = Number(valor).toFixed(Number(decimales));
  return texto === "-0" && Number(valor) !== 0 ? texto : texto;
}

export function format_scientific(valor, decimales) {
  const texto = Number(valor).toExponential(Number(decimales));
  const [mantisa, exponente] = texto.split("e");
  const signo = exponente.startsWith("-") ? "-" : "+";
  const digitos = exponente.replace(/^[+-]/, "").padStart(2, "0");
  return mantisa + "e" + signo + digitos;
}

export function format_radix(valor, base) {
  const numero = BigInt(valor);
  return numero.toString(Number(base));
}

export function template_values(texto, partes) {
  let salida = text_of(texto);
  for (const parte of partes) salida = salida.replace("#{" + "}", show(parte));
  let posicion = 0;
  return salida.replace(/\\{\\}/g, () => (posicion < partes.length ? show(partes[posicion++]) : "{}"));
}

// --- Consola y log ------------------------------------------------------

const LOG_STATE = { threshold: 1, timestamped: false };

function log_severity(nombre) {
  switch (nombre) {
    case "debug":
      return 0;
    case "info":
      return 1;
    case "warn":
      return 2;
    case "error":
      return 3;
    default:
      return 1;
  }
}

export function log_set_level(nivel) {
  LOG_STATE.threshold = log_severity(text_of(nivel));
}

export function log_level() {
  return ["debug", "info", "warn", "error"][LOG_STATE.threshold];
}

export function log_timestamped(enabled) {
  LOG_STATE.timestamped = enabled === true;
}

export function log_values(nivel, partes) {
  if (log_severity(text_of(nivel)) < LOG_STATE.threshold) return;
  let linea = "[" + text_of(nivel) + "] ";
  if (LOG_STATE.timestamped) {
    const ahora = new Date();
    const dos = (valor) => String(valor).padStart(2, "0");
    linea += "[" + dos(ahora.getHours()) + ":" + dos(ahora.getMinutes()) + ":" + dos(ahora.getSeconds()) + "] ";
  }
  process.stderr.write(linea + format_values(partes) + "\\n");
}

export function console_esc(texto) {
  return "\\u001b[" + text_of(texto) + "m";
}

export function console_strip(texto) {
  return text_of(texto).replace(/\\u001b\\[[0-9;]*m/g, "");
}

// --- Crypto (sha256) ----------------------------------------------------

export function sha256_raw(texto) {
  return sha256_hex(new TextEncoder().encode(text_of(texto)));
}

function sha256_hex(datos) {
  const largo = datos.length;
  const bits = largo * 8;
  const relleno = (largo + 9 + 63) & ~63;
  const buffer = new Uint8Array(relleno);
  buffer.set(datos);
  buffer[largo] = 0x80;
  const vista = new DataView(buffer.buffer);
  vista.setUint32(relleno - 8, Math.floor(bits / 0x100000000));
  vista.setUint32(relleno - 4, bits >>> 0);
  const k = SHA256_K;
  const h = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
  const w = new Uint32Array(64);
  for (let bloque = 0; bloque < relleno; bloque += 64) {
    for (let i = 0; i < 16; i += 1) w[i] = vista.getUint32(bloque + i * 4);
    for (let i = 16; i < 64; i += 1) {
      const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
      const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
    }
    let [a, b, c, d, e, f, g, hh] = h;
    for (let i = 0; i < 64; i += 1) {
      const s1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = (e & f) ^ (~e & g);
      const t1 = (hh + s1 + ch + k[i] + w[i]) >>> 0;
      const s0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const t2 = (s0 + maj) >>> 0;
      hh = g;
      g = f;
      f = e;
      e = (d + t1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (t1 + t2) >>> 0;
    }
    h[0] = (h[0] + a) >>> 0;
    h[1] = (h[1] + b) >>> 0;
    h[2] = (h[2] + c) >>> 0;
    h[3] = (h[3] + d) >>> 0;
    h[4] = (h[4] + e) >>> 0;
    h[5] = (h[5] + f) >>> 0;
    h[6] = (h[6] + g) >>> 0;
    h[7] = (h[7] + hh) >>> 0;
  }
  return h.map((valor) => valor.toString(16).padStart(8, "0")).join("");
}

function rotr(valor, bits) {
  return ((valor >>> bits) | (valor << (32 - bits))) >>> 0;
}

const SHA256_K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);

// --- Archivos (manejadores) --------------------------------------------

const FILES = new Map();

export function file_open(ruta, modo) {
  try {
    const opciones = text_of(modo).includes("w")
      ? "w"
      : text_of(modo).includes("a")
        ? "a"
        : "r";
    const descriptor = fs.openSync(text_of(ruta), opciones === "w" ? "w" : opciones === "a" ? "a" : "r");
    FILES.set(descriptor, { descriptor, pendiente: "" });
    return BigInt(descriptor);
  } catch {
    return -1n;
  }
}

export function file_close(manejador) {
  const descriptor = Number(manejador);
  try {
    fs.closeSync(descriptor);
    FILES.delete(descriptor);
    return true;
  } catch {
    return false;
  }
}

export function file_read_all(manejador) {
  const descriptor = Number(manejador);
  try {
    const partes = [];
    const buffer = Buffer.alloc(65536);
    let leidos = 0;
    while ((leidos = fs.readSync(descriptor, buffer, 0, buffer.length, null)) > 0) {
      partes.push(Buffer.from(buffer.subarray(0, leidos)));
    }
    return Buffer.concat(partes).toString("utf8");
  } catch {
    return null;
  }
}

export function file_read_line(manejador) {
  const descriptor = Number(manejador);
  const estado = FILES.get(descriptor);
  if (estado === undefined) return null;
  const buffer = Buffer.alloc(1);
  for (;;) {
    let leidos = 0;
    try {
      leidos = fs.readSync(descriptor, buffer, 0, 1, null);
    } catch {
      return null;
    }
    if (leidos === 0) {
      if (estado.pendiente.length === 0) return null;
      const resto = estado.pendiente;
      estado.pendiente = "";
      return resto;
    }
    const letra = buffer.toString("utf8");
    if (letra === "\\n") {
      const linea = estado.pendiente.endsWith("\\r") ? estado.pendiente.slice(0, -1) : estado.pendiente;
      estado.pendiente = "";
      return linea;
    }
    estado.pendiente += letra;
  }
}

export function file_write(manejador, texto) {
  try {
    fs.writeSync(Number(manejador), Buffer.from(text_of(texto), "utf8"));
    return true;
  } catch {
    return false;
  }
}

export function file_flush(manejador) {
  try {
    fs.fsyncSync(Number(manejador));
    return true;
  } catch {
    return false;
  }
}

export function file_eof(manejador) {
  const descriptor = Number(manejador);
  try {
    const posicion = fs.readSync(descriptor, Buffer.alloc(1), 0, 1, null);
    return posicion === 0;
  } catch {
    return true;
  }
}

// Carácter a partir de un punto de código (json::code_char_raw).
export function code_char(codigo) {
  return String.fromCodePoint(Number(codigo));
}

// --- Caracteres ---------------------------------------------------------

export function char_upper(valor) {
  return text_of(valor).toUpperCase();
}

export function char_lower(valor) {
  return text_of(valor).toLowerCase();
}

export function char_code(valor) {
  return text_of(valor).charCodeAt(0);
}

function char_matches(valor, patron) {
  return patron.test(text_of(valor));
}

export function char_is_digit(valor) {
  return char_matches(valor, /^[0-9]$/);
}

export function char_is_alpha(valor) {
  return char_matches(valor, /^\\p{L}$/u);
}

export function char_is_alphanumeric(valor) {
  return char_matches(valor, /^[\\p{L}0-9]$/u);
}

export function char_is_space(valor) {
  return char_matches(valor, /^\\s$/u);
}

export function char_is_upper(valor) {
  const texto = text_of(valor);
  return texto.toUpperCase() === texto && texto.toLowerCase() !== texto;
}

export function char_is_lower(valor) {
  const texto = text_of(valor);
  return texto.toLowerCase() === texto && texto.toUpperCase() !== texto;
}

export function char_is_ascii(valor) {
  return text_of(valor).charCodeAt(0) < 128;
}

export function char_is_hex_digit(valor) {
  return char_matches(valor, /^[0-9a-fA-F]$/);
}

export function char_is_control(valor) {
  const codigo = text_of(valor).charCodeAt(0);
  return codigo < 32 || codigo === 127;
}

export function char_is_punctuation(valor) {
  return char_matches(valor, /^[\\p{P}\\p{S}]$/u);
}

export function char_digit_value(valor) {
  const texto = text_of(valor);
  return /^[0-9]$/.test(texto) ? Number(texto) : -1;
}

export function char_hex_value(valor) {
  const texto = text_of(valor);
  return /^[0-9a-fA-F]$/.test(texto) ? parseInt(texto, 16) : -1;
}

// --- Límites de enteros -------------------------------------------------

export function int8_max() {
  return 127;
}
export function int8_min() {
  return -128;
}
export function int16_max() {
  return 32767;
}
export function int16_min() {
  return -32768;
}
export function int32_max() {
  return 2147483647;
}
export function int32_min() {
  return -2147483648;
}
export function int64_max() {
  return 9223372036854775807n;
}
export function int64_min() {
  return -9223372036854775808n;
}
export function uint8_max() {
  return 255;
}
export function uint8_min() {
  return 0;
}
export function uint16_max() {
  return 65535;
}
export function uint16_min() {
  return 0;
}
export function uint32_max() {
  return 4294967295;
}
export function uint32_min() {
  return 0;
}
export function uint64_max() {
  return 18446744073709551615n;
}
export function uint64_min() {
  return 0n;
}

// --- Entrada estándar ---------------------------------------------------

const STDIN_STATE = { buffer: "", eof: false };

function fill_stdin() {
  const buffer = Buffer.alloc(65536);
  let leidos = 0;
  try {
    leidos = fs.readSync(0, buffer, 0, buffer.length, null);
  } catch {
    leidos = 0;
  }
  if (leidos > 0) STDIN_STATE.buffer += buffer.toString("utf8", 0, leidos);
  else STDIN_STATE.eof = true;
}

export function read_line() {
  for (;;) {
    const corte = STDIN_STATE.buffer.indexOf("\\n");
    if (corte >= 0) {
      const linea = STDIN_STATE.buffer.slice(0, corte);
      STDIN_STATE.buffer = STDIN_STATE.buffer.slice(corte + 1);
      return linea.endsWith("\\r") ? linea.slice(0, -1) : linea;
    }
    if (STDIN_STATE.eof) {
      const resto = STDIN_STATE.buffer;
      STDIN_STATE.buffer = "";
      return resto;
    }
    fill_stdin();
  }
}

export function read_all() {
  while (!STDIN_STATE.eof) fill_stdin();
  const resto = STDIN_STATE.buffer;
  STDIN_STATE.buffer = "";
  return resto;
}

export function read_char() {
  if (STDIN_STATE.buffer.length === 0) fill_stdin();
  if (STDIN_STATE.buffer.length === 0) return null;
  const letra = STDIN_STATE.buffer.slice(0, 1);
  STDIN_STATE.buffer = STDIN_STATE.buffer.slice(1);
  return letra;
}

// --- Contenedores propios ----------------------------------------------

// Clave canónica para mapas con claves que no son primitivas (runes, tuplas):
// Map compara por identidad y PenguScript compara por valor.
export function key_of(value) {
  if (value === null || value === undefined) return "null";
  const tipo = typeof value;
  if (tipo === "string") return "s:" + value;
  if (tipo === "number") return "n:" + value;
  if (tipo === "bigint") return "n:" + value.toString();
  if (tipo === "boolean") return "b:" + value;
  if (Array.isArray(value)) return "a:[" + value.map((item) => key_of(item)).join(",") + "]";
  if (value instanceof Map) {
    return "m:{" + [...value.entries()].map(([k, v]) => key_of(k) + "=" + key_of(v)).join(",") + "}";
  }
  if (value instanceof Set) return "t:{" + [...value].map((item) => key_of(item)).join(",") + "}";
  const claves = Object.keys(value).sort();
  return "o:{" + claves.map((clave) => clave + "=" + key_of(value[clave])).join(",") + "}";
}

export class PMap {
  constructor(entradas) {
    this.claves = new Map();
    this.valores = new Map();
    if (entradas !== undefined) for (const [clave, valor] of entradas) this.set(clave, valor);
  }

  get size() {
    return this.valores.size;
  }

  set(clave, valor) {
    const canonica = key_of(clave);
    this.claves.set(canonica, clave);
    this.valores.set(canonica, valor);
    return this;
  }

  get(clave) {
    const canonica = key_of(clave);
    return this.valores.get(canonica);
  }

  has(clave) {
    return this.valores.has(key_of(clave));
  }

  delete(clave) {
    const canonica = key_of(clave);
    this.claves.delete(canonica);
    return this.valores.delete(canonica);
  }

  clear() {
    this.claves.clear();
    this.valores.clear();
  }

  keys() {
    return [...this.claves.values()];
  }

  values() {
    return [...this.valores.values()];
  }

  entries() {
    return this.keys().map((clave) => [clave, this.get(clave)]);
  }

  [Symbol.iterator]() {
    return this.entries()[Symbol.iterator]();
  }
}

export class PHeap {
  constructor(comparador) {
    this.datos = [];
    this.comparador = comparador ?? ((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  }

  get size() {
    return this.datos.length;
  }

  push(valor) {
    this.datos.push(valor);
    let indice = this.datos.length - 1;
    while (indice > 0) {
      const padre = (indice - 1) >> 1;
      if (this.comparador(this.datos[indice], this.datos[padre]) >= 0) break;
      [this.datos[indice], this.datos[padre]] = [this.datos[padre], this.datos[indice]];
      indice = padre;
    }
    return this;
  }

  pop() {
    if (this.datos.length === 0) return undefined;
    const cima = this.datos[0];
    const ultimo = this.datos.pop();
    if (this.datos.length === 0) return cima;
    this.datos[0] = ultimo;
    let indice = 0;
    for (;;) {
      const izquierda = indice * 2 + 1;
      const derecha = izquierda + 1;
      let menor = indice;
      if (izquierda < this.datos.length && this.comparador(this.datos[izquierda], this.datos[menor]) < 0) menor = izquierda;
      if (derecha < this.datos.length && this.comparador(this.datos[derecha], this.datos[menor]) < 0) menor = derecha;
      if (menor === indice) break;
      [this.datos[indice], this.datos[menor]] = [this.datos[menor], this.datos[indice]];
      indice = menor;
    }
    return cima;
  }

  top() {
    return this.datos[0];
  }

  is_empty() {
    return this.datos.length === 0;
  }
}

// --- Opcionales ---------------------------------------------------------

export function unwrap(value) {
  if (value === null || value === undefined) panic("optional vacío");
  return value;
}
`;
