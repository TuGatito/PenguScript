// Validación del backend elegido.
//
// El checker no sabe de backends: `host` y `std/js/*` son semánticamente
// válidos siempre. Pero el backend C++20 no puede representar un objeto del
// navegador, así que la compilación a C++ rechaza el programa con E0518 antes
// de generar código (con un mensaje que dice qué hacer), en vez de fallar con
// un error de emisión o un tipo C++ inexistente.

import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { CODES } from "../diagnostics/codes.ts";
import { error } from "../diagnostics/diagnostic.ts";
import type { Target } from "./target.ts";
import type { ProgramUnit } from "../codegen/cpp_module.ts";
import type { Span } from "../util/span.ts";

const HOST_MODULE_PREFIX = "std/js/";

export function is_host_module(path: string): boolean {
  return path.startsWith(HOST_MODULE_PREFIX) || path.includes(`/${HOST_MODULE_PREFIX}`);
}

// Un módulo usa el host si lo invoca o si él mismo es parte de `std/js/`.
function uses_host(unit: ProgramUnit): { paths: string[]; span: Span } | undefined {
  if (is_host_module(unit.module.file)) return undefined;
  const paths: string[] = [];
  let first: Span | undefined;
  for (const info of unit.module.imports.values()) {
    if (!is_host_module(info.path)) continue;
    paths.push(display_path(info.path));
    first = first ?? info.span;
  }
  if (paths.length === 0 || first === undefined) return undefined;
  return { paths, span: first };
}

// Ruta legible: `std/js/dom` en vez de la ruta absoluta del bundle.
function display_path(path: string): string {
  const marker = `/${HOST_MODULE_PREFIX}`;
  const cut = path.indexOf(marker);
  return cut < 0 ? path : HOST_MODULE_PREFIX + path.slice(cut + marker.length);
}

export function validate_target(
  units: readonly ProgramUnit[],
  target: Target,
  sink: DiagnosticSink,
): void {
  if (target !== "cpp") return;
  const seen = new Set<string>();
  for (const unit of units) {
    const used = uses_host(unit);
    if (used === undefined) continue;
    const key = `${unit.module.file}\0${used.paths.join(",")}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const lista = used.paths.map((path) => `«${path}»`).join(", ");
    const verbo = used.paths.length === 1 ? "describe" : "describen";
    sink.add(
      error(
        CODES.host_unsupported_target,
        `${lista} ${verbo} objetos de JavaScript: no se puede compilar con «--target cpp»`,
        used.span,
        "compila con «pengu build --target js» o quita esos «invoke»",
        "el backend C++20 no tiene DOM, Canvas, Storage ni Promise",
      ),
    );
  }
}
