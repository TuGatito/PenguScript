// Estado compartido por el emisor de JavaScript.
//
// A diferencia del backend C++, un programa no produce un archivo sino **uno
// por realm** (§12.1 #3). Además, JS no tiene enlazador: solo se emite lo que
// el programa puede llegar a usar, así que el contexto guarda qué símbolos ya
// se emitieron (`emitted`) y resuelve las referencias entre realms como
// `import` con alias local (`cross_reference`).
//
// Los imports se acumulan por archivo y la cabecera se escribe al final
// (cabecera diferida): el orden de emisión no importa.

import type { ExprNode } from "../frontend/ast_expr.ts";
import { make_sink, type DiagnosticSink } from "../diagnostics/sink.ts";
import { resolve_type_node } from "../semantic/type_env.ts";
import type { TypeNode } from "../frontend/ast_type.ts";
import { error as diagnostic_error } from "../diagnostics/diagnostic.ts";
import { CODES } from "../diagnostics/codes.ts";
import type { ProgramUnit } from "./cpp_module.ts";
import type { HostIndex } from "./js_host.ts";
import { EMPTY_HOST_INDEX } from "./js_host.ts";
import type { PenguType } from "../semantic/types.ts";
import { UNKNOWN } from "../semantic/types.ts";
import type { Span } from "../util/span.ts";
import type { Int64Mode } from "./js_types.ts";
import { DEFAULT_INT64_MODE } from "./js_types.ts";
import {
  RESERVED_FILE_NAMES,
  js_alias,
  js_file_name,
  js_identifier,
  js_unique_file_name,
} from "./js_names.ts";

// Un archivo `.mjs` del programa generado.
export interface JsFile {
  readonly realm: string;
  readonly name: string;
  // Constantes del realm, en orden de dependencias (sin cabecera).
  lines: string[];
  // Funciones ya completas. Van en bloques aparte para que emitir una
  // función desde dentro de otra no la parta por la mitad: el orden textual
  // del archivo nunca depende del orden de descubrimiento.
  readonly functions: string[];
  // Símbolo de PenguScript → nombre local en este archivo.
  readonly symbols: Map<string, string>;
  // Realm de origen → nombre exportado → alias local.
  readonly imports: Map<string, Map<string, string>>;
  // Nombres ocupados en este archivo (símbolos, alias e `rt`).
  readonly taken: Set<string>;
  // El módulo usa el runtime (`import * as rt from "./pengu_rt.mjs"`).
  uses_rt: boolean;
}

export interface JsContext {
  readonly unit: ProgramUnit;
  readonly sink: DiagnosticSink;
  readonly types: ReadonlyMap<ExprNode, PenguType>;
  readonly mode: Int64Mode;
  readonly jsdoc: boolean;
  // Realm → unidad analizada (todas las del programa, entrada incluida).
  readonly units: ReadonlyMap<string, ProgramUnit>;
  // Realm → archivo.
  readonly files: Map<string, JsFile>;
  file: JsFile;
  // Claves `${realm}\0${kind}\0${name}` ya emitidas o en curso.
  readonly emitted: Set<string>;
  // Realms cuyo cuerpo de constantes ya se volcó.
  readonly started: Set<string>;
  scopes: string[][];
  indent: number;
  temp: number;
  // Pila de banderas de `break` (para el `else` de los bucles).
  readonly break_flags: string[];
  // Variables que recogen el valor de cada `break value` (pila).
  readonly break_values: string[];
  // Verdadero mientras se emite el cuerpo de una función con resultado.
  in_value_body: boolean;
  // Tipo de retorno de la función que se emite (para `return` y literales).
  return_type: PenguType | undefined;
  // Expresión que representa `@` en el cuerpo actual (`undefined` → none).
  self_expression: string | undefined;
  // `await` emitido hasta ahora (permite saber si una IIFE capturada debe ser
  // `async`) y profundidad de funciones `async` en emisión.
  await_seen: number;
  await_depth: number;
  // Runas que se emiten como `class` (calculado sobre todo el programa).
  readonly class_runes: ReadonlySet<string>;
  // Runas con `destructor` declarado: obligan a `try/finally`.
  readonly destructor_runes: ReadonlySet<string>;
  // Tipos, globales y namespaces del host (`host`), de todos los módulos.
  readonly host_index: HostIndex;
  // Tipo con el que se declaró cada variable local (para conversiones).
  local_types: Map<string, PenguType>;
  // Base del `enchanting` que se está emitiendo (`string`, `optional`…), para
  // resolver los miembros nativos de `@` dentro del cuerpo.
  enchant_base: string | undefined;
}

export interface JsContextOptions {
  readonly mode?: Int64Mode;
  // Comentarios JSDoc en el código generado (`--jsdoc`).
  readonly jsdoc?: boolean;
  readonly units?: ReadonlyMap<string, ProgramUnit>;
  readonly class_runes?: ReadonlySet<string>;
  readonly destructor_runes?: ReadonlySet<string>;
  readonly host_index?: HostIndex;
}

export function make_js_context(
  unit: ProgramUnit,
  sink: DiagnosticSink,
  options: JsContextOptions = {},
): JsContext {
  const root = make_js_file(unit.module.realm, new Set());
  return {
    unit,
    sink,
    types: unit.types,
    mode: options.mode ?? DEFAULT_INT64_MODE,
    jsdoc: options.jsdoc === true,
    units: options.units ?? new Map([[unit.module.realm, unit]]),
    files: new Map([[unit.module.realm, root]]),
    file: root,
    emitted: new Set(),
    started: new Set(),
    scopes: [[]],
    indent: 0,
    temp: 0,
    break_flags: [],
    break_values: [],
    in_value_body: false,
    return_type: undefined,
    self_expression: undefined,
    await_seen: 0,
    await_depth: 0,
    class_runes: options.class_runes ?? new Set(),
    host_index: options.host_index ?? EMPTY_HOST_INDEX,
    enchant_base: undefined,
    destructor_runes: options.destructor_runes ?? new Set(),
    local_types: new Map(),
  };
}

function make_js_file(realm: string, taken: ReadonlySet<string>): JsFile {
  const names = new Set([...RESERVED_FILE_NAMES, ...taken]);
  return {
    realm,
    name: js_unique_file_name(js_file_name(realm), names),
    lines: [],
    functions: [],
    symbols: new Map(),
    imports: new Map(),
    taken: new Set(["rt"]),
    uses_rt: false,
  };
}

// Archivo de un realm, creándolo si es la primera vez. Dos realms que
// sanearían al mismo nombre (`a b` y `a_b`) reciben un sufijo.
export function file_for(g: JsContext, realm: string): JsFile {
  const existing = g.files.get(realm);
  if (existing !== undefined) return existing;
  const taken = new Set([...RESERVED_FILE_NAMES, ...[...g.files.values()].map((file) => file.name)]);
  const file = make_js_file(realm, taken);
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

// Nombre local de un símbolo de este archivo, declarándolo si es la primera
// vez. Dos símbolos que sanean igual (`class` y `class_`) no colisionan.
export function symbol_name(g: JsContext, name: string): string {
  const existing = g.file.symbols.get(name);
  if (existing !== undefined) return existing;
  const local = js_alias(js_identifier(name), g.file.taken);
  g.file.symbols.set(name, local);
  g.file.taken.add(local);
  return local;
}

// El runtime del programa (`rt`), añadiendo el import si hace falta.
export function runtime_name(g: JsContext): string {
  g.file.uses_rt = true;
  return "rt";
}

// Referencia a un símbolo de otro realm (o del propio archivo). Devuelve el
// nombre con el que se usa en el código emitido.
export function cross_reference(g: JsContext, realm: string, name: string): string {
  if (realm === g.file.realm) return symbol_name(g, name);
  const target = file_for(g, realm);
  const exported = target.symbols.get(name) ?? symbol_name_in(target, name);
  const key = `${realm}\u0000${exported}`;
  const existing = g.file.imports.get(realm)?.get(exported);
  if (existing !== undefined) return existing;
  const local = js_alias(exported, g.file.taken);
  g.file.taken.add(local);
  const map = g.file.imports.get(realm) ?? new Map<string, string>();
  map.set(exported, local);
  g.file.imports.set(realm, map);
  void key;
  return local;
}

// Nombre con el que un archivo exporta un símbolo, sin cambiar el archivo
// activo. Sirve para importarlo desde otro realm.
export function symbol_name_in(file: JsFile, name: string): string {
  const existing = file.symbols.get(name);
  if (existing !== undefined) return existing;
  const local = js_alias(js_identifier(name), file.taken);
  file.symbols.set(name, local);
  file.taken.add(local);
  return local;
}

export function js_error(g: JsContext, message: string, span: Span): void {
  g.sink.add(diagnostic_error(CODES.js_emit_failed, message, span));
}

// Función del lenguaje que el backend JavaScript no puede representar (FFI,
// uniones al estilo C, hilos…): E0807, no un fallo del emisor.
export function js_unsupported(g: JsContext, message: string, span: Span): void {
  g.sink.add(diagnostic_error(CODES.js_target_unsupported, message, span));
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
  const scope = g.scopes.pop();
  // Los tipos de las locales viven en un mapa plano: al cerrar el ámbito hay
  // que olvidarlos o una función posterior reutilizaría el tipo de otra.
  if (scope === undefined) return;
  for (const name of scope) g.local_types.delete(name);
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

// Emite un cuerpo con ámbitos propios: una función puede emitirse desde dentro
// de otra (emisión perezosa), y sus locales no deben verse entre sí.
export function with_fresh_locals<T>(g: JsContext, body: () => T): T {
  const saved_scopes = g.scopes;
  const saved_types = g.local_types;
  g.scopes = [];
  g.local_types = new Map(saved_types);
  push_scope(g);
  try {
    return body();
  } finally {
    g.scopes = saved_scopes;
    g.local_types = saved_types;
  }
}

export function fresh_name(g: JsContext, prefix: string): string {
  g.temp += 1;
  return `_${prefix}${g.temp}`;
}

// Unidad del archivo que se está emitiendo (no siempre es la de entrada:
// emitir `io::println` cambia el archivo activo a `io`).
export function current_unit(g: JsContext): ProgramUnit {
  return g.units.get(g.file.realm) ?? g.unit;
}

// Realm de un alias de `invoke`. El alias puede no coincidir con el nombre
// del realm (`invoke "./numeros" as nums`), así que se consultan los realms
// externos del módulo actual.
export function resolve_realm(g: JsContext, alias: string): string | undefined {
  if (g.units.has(alias)) return alias;
  const external = current_unit(g).external_realms?.get(alias);
  return external;
}

// Realm que declara un tipo (`rune`, `omen`, `seal`, `echo`), o `undefined`
// si no se encuentra en el grafo cargado.
export function realm_of_type(g: JsContext, name: string): string | undefined {
  for (const unit of g.units.values()) {
    const env = unit.module.env;
    if (env.runes.has(name) || env.omens.has(name) || env.aliases.has(name)) return unit.module.realm;
  }
  return undefined;
}

// Las anotaciones de tipos viven en la unidad del archivo que se emite: los
// nodos de `std/io` no están en el mapa de la unidad de entrada.
export function type_of(g: JsContext, node: ExprNode): PenguType {
  return current_unit(g).types.get(node) ?? UNKNOWN;
}

export function expression_type(g: JsContext, node: ExprNode): PenguType {
  return type_of(g, node);
}

// Resolución de un `TypeNode` sin diagnósticos. El emisor solo necesita una
// pista de tipo para decidir copias y literales; si el tipo no se resuelve
// (por ejemplo `T` de un `enchanting` genérico) el checker ya lo validó y no
// hay que duplicar el aviso.
export function quiet_type_node(g: JsContext, node: TypeNode): PenguType {
  const sink = make_sink({ max: 0 });
  return resolve_type_node(node, current_unit(g).module.env, sink);
}

// Registra el tipo de una variable local recién declarada.
export function declare_local_type(g: JsContext, name: string, type: PenguType): void {
  g.local_types.set(name, type);
  g.local_types.set(js_identifier(name), type);
}

// Tipo conocido de una variable local (`undefined` si no se declaró aquí).
export function local_type(g: JsContext, name: string): PenguType | undefined {
  return g.local_types.get(name);
}
