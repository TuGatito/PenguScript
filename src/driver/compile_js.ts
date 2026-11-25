// Driver del backend JavaScript (ES2022+ / ESM).
//
// Fase P0: el andamiaje está en su sitio (target, diagnósticos, tipos y
// nombres) pero la emisión todavía no existe. Se analiza el proyecto para
// reportar primero los errores reales del fuente y solo después el aviso de
// backend sin implementar: así un usuario ve sus errores, no un "no
// soportado" que los tapa.

import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import type { Diagnostic } from "../diagnostics/diagnostic.ts";
import { make_diagnostic } from "../diagnostics/diagnostic.ts";
import { CODES } from "../diagnostics/codes.ts";
import { make_sink } from "../diagnostics/sink.ts";
import { make_source, span_from } from "../util/span.ts";
import { analyze_graph } from "./analyze.ts";
import type { CompileOptions, CompileResult } from "./compile.ts";

export const JS_BACKEND_PENDING =
  "el backend JavaScript todavía no emite código (fase P0); falta la emisión de módulos";

export function compile_js_file(path: string, options: CompileOptions = {}): CompileResult {
  const source_path = resolve(path);
  const text = readFileSync(source_path, "utf8");
  const source = make_source(source_path, text);
  const sink = make_sink({ max: 200 });

  const analysis = analyze_graph(source_path, sink);
  if (sink.has_errors() || analysis.entry_module === undefined) {
    return {
      ok: false,
      target: "js",
      diagnostics: sink.diagnostics,
      output: "",
      source_path,
    };
  }

  return {
    ok: false,
    target: "js",
    diagnostics: [pending_diagnostic(source, options)],
    output: "",
    source_path,
  };
}

function pending_diagnostic(
  source: ReturnType<typeof make_source>,
  options: CompileOptions,
): Diagnostic {
  const out = options.out === undefined ? "" : join(resolve(options.out), "index.mjs");
  return make_diagnostic({
    code: CODES.js_target_unsupported,
    message: JS_BACKEND_PENDING,
    span: span_from(source, 0, 0),
    notes: [
      "el backend C++20 sigue disponible con --target cpp (por defecto)",
      out.length === 0 ? "salida por defecto: .pengu-cache/js-<hash>/index.mjs" : `salida: ${out}`,
    ],
  });
}

// Directorio de salida del backend JS (§12.1 #3): el `--out` explícito si
// lo hay y, si no, la caché junto al fuente.
export function js_output_dir(source_path: string, options: CompileOptions, hash: string): string {
  if (options.out !== undefined) return resolve(options.out);
  return join(dirname(source_path), ".pengu-cache", `js-${hash}`);
}
