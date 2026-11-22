// Sincronización de documentos del editor.
//
// El cliente envía cambios incrementales (`contentChanges` con rango); hay que
// aplicarlos en orden sobre el texto actual. De aquí sale también la «zona
// caliente»: el tramo que el usuario acaba de tocar, que sirve para no
// publicar errores sobre un identificador a medio escribir.

export interface ChangePosition {
  readonly line: number;
  readonly character: number;
}

export interface ChangeRange {
  readonly start: ChangePosition;
  readonly end: ChangePosition;
}

export interface ContentChange {
  readonly range?: ChangeRange;
  readonly text: string;
}

export interface HotRegion {
  readonly start: number;
  readonly end: number;
}

export interface ChangeResult {
  readonly text: string;
  readonly hot: HotRegion | undefined;
}

/** Offset de una posición LSP (línea/carácter) dentro de `text`. */
export function offset_of_position(text: string, position: ChangePosition): number {
  const lines = text.split("\n");
  const index = Math.max(0, Math.min(position.line, lines.length - 1));
  let offset = 0;
  for (let line = 0; line < index; line += 1) offset += (lines[line] ?? "").length + 1;
  const current = lines[index] ?? "";
  return offset + Math.max(0, Math.min(position.character, current.length));
}

/** Aplica un cambio (completo o con rango) y devuelve el texto nuevo. */
export function apply_change(text: string, change: ContentChange): string {
  if (change.range === undefined) return change.text;
  const start = offset_of_position(text, change.range.start);
  const end = offset_of_position(text, change.range.end);
  return text.slice(0, start) + change.text + text.slice(end);
}

/**
 * Aplica la lista de cambios del cliente. La zona caliente es la del último
 * cambio con rango; un cambio de documento completo no deja zona caliente.
 */
export function apply_changes(text: string, changes: readonly ContentChange[]): ChangeResult {
  let current = text;
  let hot: HotRegion | undefined;
  for (const change of changes) {
    if (change.range === undefined) {
      current = change.text;
      hot = undefined;
      continue;
    }
    const start = offset_of_position(current, change.range.start);
    const end = offset_of_position(current, change.range.end);
    current = current.slice(0, start) + change.text + current.slice(end);
    hot = { start, end: start + change.text.length };
  }
  return { text: current, hot };
}

/** ¿El diagnóstico toca la zona que se está escribiendo? */
export function touches(span: { readonly start: { offset: number }; readonly end: { offset: number } }, hot: HotRegion): boolean {
  return span.start.offset <= hot.end + 1 && span.end.offset >= hot.start - 1;
}
