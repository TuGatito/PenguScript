// Ensamblado del programa JavaScript: emisión perezosa por alcanzabilidad,
// cabeceras con imports y lanzador `index.mjs`.
//
// El backend C++ emite todos los módulos y deja que el enlazador descarte lo
// que no se usa. En JS no hay enlazador: aquí se emite un `.mjs` por realm y
// solo se escriben los símbolos a los que el programa llega desde `main`.

import type { FunctionDecl } from "../frontend/ast_decl.ts";
import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { error as diagnostic_error } from "../diagnostics/diagnostic.ts";
import { CODES } from "../diagnostics/codes.ts";
import type { ProgramUnit } from "./cpp_module.ts";
import type { Int64Mode } from "./js_types.ts";
import { DEFAULT_INT64_MODE } from "./js_types.ts";
import { RUNTIME_JS } from "./runtime_source_js.ts";
import {
  file_for,
  make_js_context,
  with_file,
  type JsContext,
  type JsFile,
} from "./js_context.ts";
import { emit_constants, emit_function } from "./js_decl.ts";
import { collect_class_runes, emit_type_decls, is_class_rune } from "./js_type_decl.ts";

export interface JsGeneratedFile {
  readonly name: string;
  readonly code: string;
}

export interface JsProgram {
  // Archivos generados: módulos de realm, `pengu_rt.mjs` e `index.mjs`.
  readonly files: readonly JsGeneratedFile[];
  // Ruta relativa del archivo que se ejecuta (`index.mjs`).
  readonly entry: string;
  readonly has_main: boolean;
}

export interface JsProgramOptions {
  readonly mode?: Int64Mode;
  readonly include_runtime?: boolean;
  // Comentarios JSDoc en el código emitido (`--jsdoc`).
  readonly jsdoc?: boolean;
}

// Emite el programa completo. `units` son las unidades analizadas (la entrada
// incluida) y `entry` la del archivo que se compila.
export function generate_js_program(
  units: readonly ProgramUnit[],
  entry: ProgramUnit,
  sink: DiagnosticSink,
  options: JsProgramOptions = {},
): JsProgram {
  const by_realm = new Map<string, ProgramUnit>();
  for (const unit of units) by_realm.set(unit.module.realm, unit);
  const g = make_js_context(entry, sink, {
    mode: options.mode ?? DEFAULT_INT64_MODE,
    jsdoc: options.jsdoc === true,
    units: by_realm,
    class_runes: collect_class_runes([...by_realm.values()]),
  });

  const main = entry.module.functions.get("main");
  if (main === undefined) {
    sink.add(
      diagnostic_error(
        CODES.missing_entry,
        `el realm de entrada «${entry.module.realm}» no define main`,
        entry.program.span,
      ),
    );
  } else {
    ensure_function(g, entry.module.realm, "main");
  }

  const files: JsGeneratedFile[] = [];
  for (const file of g.files.values()) {
    if (file.lines.length === 0 && file.functions.length === 0) continue;
    files.push({ name: file.name, code: assemble_file(file, g.files) });
  }

  const entry_file = g.files.get(entry.module.realm);
  if (options.include_runtime !== false) {
    files.push({ name: "pengu_rt.mjs", code: RUNTIME_JS });
  }
  // `main` puede ser `async`: el lanzador lo espera con top-level await.
  const main_is_async = main?.is_async === true;
  files.push({ name: "index.mjs", code: launcher(entry_file, main !== undefined, main_is_async) });

  return { files, entry: "index.mjs", has_main: main !== undefined };
}

// Emite una función de un realm si todavía no estaba emitida.
export function ensure_function(g: JsContext, realm: string, name: string): void {
  const key = `${realm}\u0000fn\u0000${name}`;
  if (g.emitted.has(key)) return;
  g.emitted.add(key);
  const unit = g.units.get(realm);
  if (unit === undefined) return;
  const info = unit.module.functions.get(name);
  if (info === undefined || info.is_intrinsic === true || info.is_extern === true) return;
  const decl = find_function(unit, name);
  if (decl === undefined) return;
  ensure_realm(g, realm);
  with_file(g, realm, () => emit_function(g, unit, decl));
}

// Las constantes de un realm se vuelcan todas juntas y en orden de
// dependencias: así ninguna referencia adelanta a su definición.
export function ensure_realm(g: JsContext, realm: string): void {
  if (g.started.has(realm)) return;
  g.started.add(realm);
  const unit = g.units.get(realm);
  if (unit === undefined) return;
  const file = file_for(g, realm);
  // Primero los tipos (clases y omens), después las constantes: una constante
  // puede construir un valor con `Punto(1, 2)`.
  const types = capture_into(g, file, () => emit_type_decls(g, unit));
  file.lines.push(...types);
  const lines = capture_into(g, file, () => emit_constants(g, unit));
  file.lines.push(...lines);
}

// Un tipo de un realm se emite con el resto de su realm: las declaraciones de
// tipo son pocas y siempre van antes de las constantes.
export function ensure_type(g: JsContext, realm: string, name: string): boolean {
  const unit = g.units.get(realm);
  if (unit === undefined) return false;
  ensure_realm(g, realm);
  return unit.module.env.runes.has(name) || unit.module.env.omens.has(name) || unit.module.env.aliases.has(name);
}

// ¿El rune se emite como clase? Lo consulta la construcción de valores.
export function rune_is_class(g: JsContext, realm: string, name: string): boolean {
  return is_class_rune(g, realm, name);
}

// Las constantes de un realm se emiten todas a la vez con `ensure_realm`, así
// que basta con asegurarse de que el realm está volcado: el nombre local lo
// resuelve después `cross_reference` en el archivo que usa la constante.
export function ensure_constant(g: JsContext, realm: string, name: string): void {
  ensure_realm(g, realm);
}

// Emite `body` en un búfer aparte y devuelve sus líneas sin indentación. Las
// constantes se emiten a veces desde dentro de otra función (al descubrir una
// referencia), así que no pueden escribirse directamente en el archivo.
function capture_into(g: JsContext, file: JsFile, body: () => void): string[] {
  const lines: string[] = [];
  const saved_file = g.file;
  const saved_indent = g.indent;
  g.file = { ...file, lines };
  g.indent = 0;
  try {
    body();
  } finally {
    file.uses_rt = file.uses_rt || g.file.uses_rt;
    g.file = saved_file;
    g.indent = saved_indent;
  }
  return lines;
}

function find_function(unit: ProgramUnit, name: string): FunctionDecl | undefined {
  for (const decl of unit.program.decls) {
    if (decl.kind === "function_decl" && decl.name === name) return decl;
  }
  return undefined;
}

// Cabecera de imports (diferida) más el cuerpo emitido.
function assemble_file(file: JsFile, files: ReadonlyMap<string, JsFile>): string {
  const header: string[] = ["// Generado por pengu. No editar a mano."];
  if (file.uses_rt) header.push('import * as rt from "./pengu_rt.mjs";');
  const realms = [...file.imports.keys()].sort();
  for (const realm of realms) {
    const map = file.imports.get(realm);
    const target = files.get(realm);
    if (map === undefined || map.size === 0 || target === undefined) continue;
    const names = [...map.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([exported, local]) => (exported === local ? exported : `${exported} as ${local}`));
    header.push(`import { ${names.join(", ")} } from "./${target.name}";`);
  }
  const body = [...file.lines];
  for (const text of file.functions) {
    if (body.length > 0) body.push("");
    body.push(text);
  }
  return `${header.join("\n")}\n\n${body.join("\n")}\n`;
}

// Lanzador: importa `main`, prepara los argumentos y reproduce el `panic` de
// C++ (`panic: <mensaje>` en stderr, código de salida 1).
function launcher(
  entry_file: JsFile | undefined,
  has_main: boolean,
  main_is_async: boolean,
): string {
  const lines = ["// Punto de entrada generado por pengu. No editar a mano."];
  lines.push('import * as rt from "./pengu_rt.mjs";');
  const main_name = entry_file?.symbols.get("main") ?? "main";
  if (has_main && entry_file !== undefined) {
    lines.push(`import { ${main_name} } from "./${entry_file.name}";`);
  }
  lines.push("");
  // Un `EPIPE` (por ejemplo `pengu run ... --target js | head`) no es un
  // error del programa: el binario nativo muere en silencio por SIGPIPE.
  lines.push('for (const stream of [process.stdout, process.stderr]) {');
  lines.push('  stream.on("error", (error) => { if (error?.code === "EPIPE") process.exit(0); });');
  lines.push("}");
  lines.push("rt.set_args(process.argv.slice(2));");
  if (!has_main) {
    lines.push("process.exit(1);");
    return `${lines.join("\n")}\n`;
  }
  lines.push("try {");
  lines.push(`  const resultado = ${main_is_async ? "await " : ""}${main_name}();`);
  lines.push('  if (typeof resultado === "number") process.exit(resultado);');
  lines.push("} catch (error) {");
  lines.push("  const mensaje = error instanceof Error ? error.message : String(error);");
  lines.push('  process.stderr.write("panic: " + mensaje + "\\n");');
  lines.push("  process.exit(1);");
  lines.push("}");
  return `${lines.join("\n")}\n`;
}
