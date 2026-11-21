export interface Position {
  readonly line: number;
  readonly column: number;
  readonly offset: number;
}

export interface Span {
  readonly file: string;
  readonly start: Position;
  readonly end: Position;
}

export interface Source {
  readonly file: string;
  readonly text: string;
  readonly line_starts: readonly number[];
}

export function make_source(file: string, text: string): Source {
  const line_starts: number[] = [0];
  for (let index = 0; index < text.length; index += 1) {
    if (text.charCodeAt(index) === 10) line_starts.push(index + 1);
  }
  return { file, text, line_starts };
}

function line_index_at(source: Source, offset: number): number {
  let low = 0;
  let high = source.line_starts.length - 1;
  while (low < high) {
    const middle = Math.ceil((low + high) / 2);
    const start = source.line_starts[middle];
    if (start !== undefined && start <= offset) low = middle;
    else high = middle - 1;
  }
  return low;
}

export function position_at(source: Source, offset: number): Position {
  const clamped = Math.max(0, Math.min(offset, source.text.length));
  const line_index = line_index_at(source, clamped);
  const line_start = source.line_starts[line_index] ?? 0;
  return { line: line_index + 1, column: clamped - line_start + 1, offset: clamped };
}

export function span_from(source: Source, start_offset: number, end_offset: number): Span {
  return {
    file: source.file,
    start: position_at(source, start_offset),
    end: position_at(source, Math.max(start_offset, end_offset)),
  };
}

export function span_of(source: Source, start_offset: number, length: number): Span {
  return span_from(source, start_offset, start_offset + length);
}

export function merge_spans(first: Span, second: Span): Span {
  return { file: first.file, start: first.start, end: second.end };
}

export function span_display(span: Span): string {
  return `${span.file}:${span.start.line}:${span.start.column}`;
}

export function line_text(source: Source, line: number): string {
  const index = line - 1;
  const start = source.line_starts[index];
  if (start === undefined) return "";
  const next = source.line_starts[index + 1];
  const end = next === undefined ? source.text.length : next - 1;
  return source.text.slice(start, end).replace(/\r$/, "");
}

export function offset_in_span(offset: number, span: Span): boolean {
  return offset >= span.start.offset && offset <= span.end.offset;
}
