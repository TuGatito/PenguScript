// Estado compartido por el emisor de JavaScript.
//
// A diferencia del backend C++, un programa no produce un archivo sino
// **uno por realm** (§12.1 #3). El contexto guarda el mapa de archivos y
// apunta al que se está emitiendo; los imports se acumulan en cada archivo
// y se escriben al final (cabecera diferida), así que el orden de emisión
// no importa.

import type { ExprNode } from "../frontend/ast_expr.ts";
import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { error as diagnostic_error } from "../diagnostics/diagnostic.ts";
import { CODES } from "../diagnostics/codes.ts";
import type { ProgramUnit } from "./cpp_module.ts";
import type { PenguType } from "../semantic/types.ts";
import { UNKNOWN } from "../semantic/types.ts";
import type { Span } from "../util/span.ts";
import type { Int64Mode } from "./js_types.ts";
import { DEFAULT_INT64_MODE } from "./js_types.ts";
import { RESERVED_FILE_NAMES, js_file_name, js_identifier, js_unique_file_name } from "./js_names.ts";

// Un archivo `.mjs` del programa generado.
export interface JsFile {
  readonly realm: string;
  readonly name: string;
  readonly lines: string[];
  // Archivo del que se importa → nombres importados (export y alias local
  // coinciden siempre: el alias se decide aquí una sola vez).
  readonly imports: Map<string, Set<string>>;
}

export interface JsContext {
  readonly unit: ProgramUnit;
  readonly sink: DiagnosticSink;
  readonly types: ReadonlyMap<ExprNode, PenguType>;
  readonly mode: Int64Mode;
  // Realm → archivo.
  readonly files: Map<string, JsFile>;
  file: JsFile;
  readonly scopes: string[][];
  indent: number;
  temp: number;
  // Pila de banderas de `break` (para el `else` de los bucles).
  readonly break_flags: string[];
  // Variables que recogen el valor de cada `break value` (pila).
  readonly break_values: string[];
  // Verdadero mientras se emite el cuerpo de una función con resultado.
  in_value_body: boolean;
  // Expresión que representa `@` en el cuerpo actual (`undefined` → none).
  self_expression: string | undefined;
  // Runas que se emiten como `class` (calculado sobre todo el programa).
  readonly class_runes: ReadonlySet<string>;
  // Runas con `destructor` declarado: obligan a `try/finally`.
  readonly destructor_runes: ReadonlySet<string>;
}

export interface JsContextOptions {
  readonly mode?: Int64Mode;
  readonly class_runes?: ReadonlySet<string>;
  readonly destructor_runes?: ReadonlySet<string>;
}

export function make_js_context(
  unit: ProgramUnit,
  sink: DiagnosticSink,
  options: JsContextOptions = {},
): JsContext {
  const root: JsFile = {
    realm: unit.module.realm,
    name: js_unique_file_name(js_file_name(unit.module.realm), RESERVED_FILE_NAMES),
    lines: [],
    imports: new Map(),
  };
  return {
    unit,
    sink,
    types: unit.types,
    mode: options.mode ?? DEFAULT_INT64_MODE,
    files: new Map([[unit.module.realm, root]]),
    file: root,
    scopes: [[]],
    indent: 0,
    temp: 0,
    break_flags: [],
    break_values: [],
    in_value_body: false,
    self_expression: undefined,
    class_runes: options.class_runes ?? new Set(),
    destructor_runes: options.destructor_runes ?? new Set(),
  };
}

// Archivo de un realm, creándolo si es la primera vez. Dos realms que
// sanearían al mismo nombre (`a b` y `a_b`) reciben un sufijo.
export function file_for(g: JsContext, realm: string): JsFile {
  const existing = g.files.get(realm);
  if (existing !== undefined) return existing;
  const taken = new Set([...RESERVED_FILE_NAMES, ...g.files.values()].map((file) =>
    typeof file === "string" ? file : file.name,
  ));
  const name = js_unique_file_name(js_file_name(realm), taken);
  const file: JsFile = { realm, name, lines: [], imports: new Map() };
  g.files.set(realm, file);
  return file;
}

// Cambia el archivo activo. El llamante debe restaurar el anterior si
// emite en varios realms dentro de la misma pasada.
export function with_file(g: JsContext, realm: string, body: () => void): void {
  const previous = g.file;
  g.file = file_for(g, realm);
  try {
    body();
  } finally {
    g.file = previous;
  }
}

// Añade un nombre a la lista de imports del archivo activo.
export function add_import(g: JsContext, from: string, name: string): void {
  const list = g.file.imports.get(from);
  if (list === undefined) g.file.imports.set(from, new Set([name]));
  else list.add(name);
}

export function js_error(g: JsContext, message: string, span: Span): void {
  g.sink.add(diagnostic_error(CODES.js_emit_failed, message, span));
}

export function line(g: JsContext, text: string): void {
  g.file.lines.push(`${"  ".repeat(g.indent)}${text}`);
}

// Línea en blanco (solo si la última no lo era).
export function blank(g: JsContext): void {
  const last = g.file.lines[g.file.lines.length - 1];
  if (last !== undefined && last.length > 0) g.file.lines.push("");
}

export function push_scope(g: JsContext): void {
  g.scopes.push([]);
}

export function pop_scope(g: JsContext): void {
  g.scopes.pop();
}

export function declare_local(g: JsContext, name: string): void {
  const scope = g.scopes[g.scopes.length - 1];
  if (scope !== undefined) scope.push(js_identifier(name));
}

export function is_local_declared(g: JsContext, name: string): boolean {
  const js_name = js_identifier(name);
  for (let index = g.scopes.length - 1; index >= 0; index -= 1) {
    const scope = g.scopes[index];
    if (scope !== undefined && scope.includes(js_name)) return true;
  }
  return false;
}

export function fresh_name(g: JsContext, prefix: string): string {
  g.temp += 1;
  return `_${prefix}${g.temp}`;
}

export function type_of(g: JsContext, node: ExprNode): PenguType {
  return g.types.get(node) ?? UNKNOWN;
}

export function expression_type(g: JsContext, node: ExprNode): PenguType {
  return g.types.get(node) ?? UNKNOWN;
}
