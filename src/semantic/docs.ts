// Documentación de símbolos a partir de los comentarios `--`.
//
// Un bloque de líneas de comentario contiguo inmediatamente encima de la
// declaración se convierte en documentación markdown simple. No hay
// sintaxis nueva: lo que el programador escribe en el comentario se
// muestra tal cual en el hover y en el autocompletado.

import { position_at } from "../util/span.ts";
import type { Source } from "../util/span.ts";

// Devuelve el texto del bloque de comentarios que termina en la línea
// anterior a `offset`, o `undefined` si no hay ninguno.
export function docs_before(source: Source, offset: number): string | undefined {
  const first = position_at(source, offset).line; // 1-based
  if (first <= 1) return undefined;

  const lines: string[] = [];
  for (let line = first - 1; line >= 1; line -= 1) {
    const text = line_text(source, line).trimEnd();
    if (text.trim().length === 0) break;
    const trimmed = text.trimStart();
    if (!trimmed.startsWith("--")) break;
    lines.unshift(trimmed.slice(2).trim());
  }
  if (lines.length === 0) return undefined;
  const text = lines.join("\n").trim();
  return text.length === 0 ? undefined : text;
}

function line_text(source: Source, line: number): string {
  const start = source.line_starts[line - 1];
  if (start === undefined) return "";
  const next = source.line_starts[line];
  const end = next === undefined ? source.text.length : next;
  return source.text.slice(start, end).replace(/\n$/, "");
}
