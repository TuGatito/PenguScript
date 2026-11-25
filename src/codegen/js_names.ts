// Nombres en el código JavaScript generado.
//
// PenguScript permite identificadores que en JS son palabras reservadas
// (`new`, `class`), globales que el emisor usa sin cualificar (`Math`,
// `Object`) o nombres que colisionarían entre sí al aplanar el realm en un
// único módulo. Aquí están las tres tablas y las funciones que escapan.

export const JS_RESERVED: ReadonlySet<string> = new Set([
  "arguments", "await", "break", "case", "catch", "class", "const", "continue",
  "debugger", "default", "delete", "do", "else", "enum", "eval", "export",
  "extends", "false", "finally", "for", "function", "if", "implements",
  "import", "in", "instanceof", "interface", "let", "new", "null", "of",
  "package", "private", "protected", "public", "return", "static", "super",
  "switch", "this", "throw", "true", "try", "typeof", "undefined", "var",
  "void", "while", "with", "yield",
]);

// Globales que el código generado referencia sin cualificar. Un símbolo de
// usuario con este nombre lo ocultaría y rompería el módulo entero.
export const JS_GLOBALS: ReadonlySet<string> = new Set([
  "Array", "BigInt", "Boolean", "Error", "Infinity", "JSON", "Map", "Math",
  "NaN", "Number", "Object", "Promise", "Reflect", "Set", "String", "Symbol",
  "TextDecoder", "TextEncoder", "WeakMap", "WeakRef", "console", "globalThis",
  "parseFloat", "parseInt", "process", "rt", "structuredClone",
]);

// Nombres que no puede tomar un archivo emitido: son el runtime y el punto
// de entrada del directorio de salida.
export const RESERVED_FILE_NAMES: ReadonlySet<string> = new Set(["pengu_rt.mjs", "index.mjs"]);

export const JS_FILE_SUFFIX = ".mjs";

const IDENTIFIER = /^[A-Za-z_$][A-Za-z0-9_$]*$/;

// Identificador seguro para el código emitido. Es determinista: el mismo
// nombre de PenguScript produce siempre el mismo identificador, así que el
// declarador y todos los importadores coinciden.
export function js_identifier(name: string): string {
  let base = "";
  for (const char of name) {
    base += /[A-Za-z0-9_$]/.test(char) ? char : "_";
  }
  if (base.length === 0) base = "p";
  if (/^[0-9]/.test(base)) base = `_${base}`;
  if (base === "rt" || JS_RESERVED.has(base) || JS_GLOBALS.has(base)) return `${base}_`;
  return base;
}

// Alias único dentro de un conjunto de nombres ya usados. Se usa para los
// `import`: dos módulos distintos pueden exportar `Punto`.
export function js_alias(name: string, taken: ReadonlySet<string>): string {
  const base = js_identifier(name);
  if (!taken.has(base)) return base;
  for (let index = 2; index < 1000; index += 1) {
    const candidate = `${base}_${index}`;
    if (!taken.has(candidate)) return candidate;
  }
  return `${base}_x`;
}

// Nombre de archivo de un realm. Los nombres de archivo se emiten en
// minúsculas para que el resultado no dependa del sistema de archivos; la
// colisión con `pengu_rt.mjs`/`index.mjs` y entre realms que sanean igual la
// resuelve `js_unique_file_name` con el conjunto de nombres ya usados.
export function js_file_name(realm: string): string {
  let base = "";
  for (const char of realm.toLowerCase()) {
    base += /[A-Za-z0-9_$-]/.test(char) ? char : "_";
  }
  if (base.length === 0) base = "realm";
  if (/^[0-9]/.test(base)) base = `_${base}`;
  return `${base}${JS_FILE_SUFFIX}`;
}

// Nombre de archivo libre dentro de `taken`: `puntos.mjs`, `puntos_2.mjs`…
export function js_unique_file_name(base: string, taken: ReadonlySet<string>): string {
  const stem = base.endsWith(JS_FILE_SUFFIX) ? base.slice(0, -JS_FILE_SUFFIX.length) : base;
  const first = `${stem}${JS_FILE_SUFFIX}`;
  if (!taken.has(first)) return first;
  for (let index = 2; index < 1000; index += 1) {
    const candidate = `${stem}_${index}${JS_FILE_SUFFIX}`;
    if (!taken.has(candidate)) return candidate;
  }
  return `${stem}_x${JS_FILE_SUFFIX}`;
}

// Literal de cadena con las comillas y escapes de JS. `JSON.stringify` ya
// escapa lo necesario y deja pasar U+2028/U+2029, válidos desde ES2019.
export function js_string_literal(text: string): string {
  return JSON.stringify(text);
}

// Literal de carácter: en JS es una cadena de longitud 1.
export function js_char_literal(char: string): string {
  return js_string_literal(char);
}

// Número de punto flotante con la forma más corta que preserva el valor.
// `String(-0)` da "0", así que el cero negativo se emite explícito.
export function js_number_literal(value: number): string {
  if (Object.is(value, -0)) return "-0";
  if (Number.isNaN(value)) return "NaN";
  if (value === Infinity) return "Infinity";
  if (value === -Infinity) return "-Infinity";
  return String(value);
}

// Entero de 64 bits: `BigInt` necesita el sufijo `n`.
export function js_bigint_literal(digits: string): string {
  return `${digits}n`;
}

// `operator *` / `operator ==`: el símbolo del operador no es un identificador
// válido, así que se exporta con la misma tabla que los métodos.
export function free_operator_name(name: string): string | undefined {
  if (!name.startsWith("operator ")) return undefined;
  return `op_${OPERATOR_EXPORTS[name.slice("operator ".length).trim()] ?? js_identifier(name)}`;
}

const OPERATOR_EXPORTS: Readonly<Record<string, string>> = {
  "+": "add",
  "-": "sub",
  "*": "mul",
  "/": "div",
  "%": "mod",
  "==": "eq",
  "!=": "ne",
  "<": "lt",
  "<=": "le",
  ">": "gt",
  ">=": "ge",
  "<=>": "cmp",
  "[]": "index",
  "()": "call",
  "+=": "add_assign",
  "-=": "sub_assign",
  "*=": "mul_assign",
  "/=": "div_assign",
  "%=": "mod_assign",
};
