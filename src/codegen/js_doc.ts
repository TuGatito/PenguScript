// Comentarios JSDoc opcionales (`--jsdoc`).
//
// El backend JavaScript no emite tipos, pero un `.mjs` generado se lee y se
// importa desde proyectos reales: con `--jsdoc` cada función pública lleva su
// bloque `@param`/`@returns` derivado de los tipos que ya resolvió el checker.
// Sin la opción no se escribe ni una línea extra.

import type { PenguType } from "../semantic/types.ts";
import { js_doc_type } from "./js_types.ts";
import { line, type JsContext } from "./js_context.ts";

export interface DocParam {
  readonly name: string;
  readonly type: PenguType;
}

export interface DocInfo {
  readonly params?: readonly DocParam[];
  readonly result?: PenguType;
  // Texto libre opcional (por ahora, el nombre del tipo o del método).
  readonly summary?: string;
}

export function emit_jsdoc(g: JsContext, info: DocInfo): void {
  if (!g.jsdoc) return;
  const parts: string[] = [];
  if (info.summary !== undefined) parts.push(info.summary);
  for (const param of info.params ?? []) {
    const type = doc_type(g, param.type);
    const safe = param.name.replace(/\*\//g, "*\\/");
    parts.push(`@param ${safe} - ${type}`);
  }
  if (info.result !== undefined && info.result.kind !== "void") {
    parts.push(`@returns ${doc_type(g, info.result)}`);
  }
  if (parts.length === 0) return;
  if (parts.length === 1) {
    line(g, `/** ${parts[0]} */`);
    return;
  }
  line(g, "/**");
  for (const part of parts) line(g, ` * ${part}`);
  line(g, " */");
}

function doc_type(g: JsContext, type: PenguType): string {
  return js_doc_type(type, g.mode);
}
