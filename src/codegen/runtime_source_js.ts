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
  const last = inclusive ? end : end - 1;
  const out = [];
  if (start <= last) {
    for (let value = start; value <= last; value += 1) out.push(value);
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

export function contains(container, value) {
  if (typeof container === "string") return container.includes(value);
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
`;
