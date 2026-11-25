// Driver del backend JavaScript (ES2022+ / ESM).
//
// El análisis es el mismo que el del backend C++ (`analyze_graph`): si el
// programa tiene errores, se reportan tal cual, sin intentar emitir. Solo
// cuando el programa es válido se generan los `.mjs` en el directorio de
// salida (`--out` o `.pengu-cache/js-<hash>/`).

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { make_sink } from "../diagnostics/sink.ts";
import { generate_js_program } from "../codegen/js_module.ts";
import { DEFAULT_INT64_MODE } from "../codegen/js_types.ts";
import { analyze_graph } from "./analyze.ts";
import type { CompileOptions, CompileResult } from "./compile.ts";

export function compile_js_file(path: string, options: CompileOptions = {}): CompileResult {
  const source_path = resolve(path);
  const text = readFileSync(source_path, "utf8");
  const sink = make_sink({ max: 200 });

  const analysis = analyze_graph(source_path, sink);
  const entry_module = analysis.entry_module;
  const entry = entry_module === undefined ? undefined : analysis.units.find((unit) => unit.module === entry_module);
  if (sink.has_errors() || entry === undefined) {
    return { ok: false, target: "js", diagnostics: sink.diagnostics, output: "", source_path };
  }

  const mode = options.int64 ?? DEFAULT_INT64_MODE;
  const program = generate_js_program(analysis.units, entry, sink, { mode });
  if (sink.has_errors()) {
    return { ok: false, target: "js", diagnostics: sink.diagnostics, output: "", source_path };
  }

  const out_dir = js_output_dir(source_path, options, content_hash(source_path, program_code(program, mode)));
  mkdirSync(out_dir, { recursive: true });

  const files: string[] = [];
  let changed = false;
  for (const file of program.files) {
    const file_path = join(out_dir, file.name);
    if (write_if_changed(file_path, file.code)) changed = true;
    files.push(file_path);
  }

  return {
    ok: true,
    target: "js",
    diagnostics: [],
    output: "",
    source_path,
    output_dir: out_dir,
    js_entry_path: join(out_dir, program.entry),
    files,
    reused: !changed,
  };
}

// Directorio de salida del backend JS (§12.1 #3): el `--out` explícito si
// lo hay y, si no, la caché junto al fuente.
export function js_output_dir(source_path: string, options: CompileOptions, hash: string): string {
  if (options.out !== undefined) return resolve(options.out);
  return join(dirname(source_path), ".pengu-cache", `js-${hash}`);
}

// Escribe solo si el contenido cambia: recompilar sin cambios no toca
// fechas de modificación ni invalida nada aguas abajo.
function write_if_changed(path: string, code: string): boolean {
  if (existsSync(path)) {
    const previous = readFileSync(path, "utf8");
    if (previous === code) return false;
  }
  writeFileSync(path, code);
  return true;
}

function program_code(program: ReturnType<typeof generate_js_program>, mode: string): string {
  return [`mode:${mode}`, ...program.files.map((file) => `${file.name}\u0000${file.code}`)].join("\u0001");
}

// FNV-1a de 32 bits sobre la ruta y el contenido: la misma idea que la caché
// del backend C++.
function content_hash(path: string, text: string): string {
  let hash = 0x811c9dc5;
  const data = `${path}\u0000${text}`;
  for (let index = 0; index < data.length; index += 1) {
    hash ^= data.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}
