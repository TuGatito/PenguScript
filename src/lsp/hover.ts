// Hover y ayuda de firma.

import type { PenguType } from "../semantic/types.ts";
import { type_display } from "../semantic/types.ts";
import { find_node_at, node_label } from "./query.ts";
import type { FileAnalysis, ProjectState } from "./project.ts";
import type { Symbol } from "../semantic/symbols.ts";
import { existing_symbol, ident_at, signature_of, type_of_node } from "./features.ts";

export interface HoverResult {
  readonly markdown: string;
  readonly symbol: Symbol | undefined;
}

// Tamaño en bytes de un tipo, si la medición está disponible.
export type SizeLookup = (type: PenguType) => { readonly size: number; readonly align: number } | undefined;
// Desplazamiento de un campo dentro de su tipo medido.
export type FieldLookup = (
  type: PenguType,
  field: string,
) => { readonly offset?: number; readonly width?: number; readonly size: number } | undefined;

export function hover_at(
  project: ProjectState,
  file: FileAnalysis,
  offset: number,
  sizes?: SizeLookup,
  fields?: FieldLookup,
): HoverResult | undefined {
  const node = find_node_at(file.program, offset);
  if (node === undefined) return undefined;

  // Métodos enhechizados: la firma vive en el módulo que declara el
  // `enchanting`, no en el índice de símbolos del archivo.
  const target = file.analysis.member_targets.get(node as never)
    ?? (node.kind === "call" ? file.analysis.member_targets.get((node as { callee?: unknown }).callee as never) : undefined);
  if (target !== undefined) {
    const signature = enchanted_signature(file, target.realm, target.name);
    if (signature !== undefined) {
      return { markdown: `\`\`\`pengu\n${signature}\n\`\`\`\n\nrealm \`${target.realm}\``, symbol: undefined };
    }
  }

  const symbol = existing_symbol(project, file, offset);
  if (symbol !== undefined) {
    const sections: string[] = [`\`\`\`pengu\n${signature_of(symbol)}\n\`\`\``];
    if (symbol.container !== undefined) sections.push(`en \`${symbol.container}\``);
    if (symbol.docs !== undefined) sections.push(symbol.docs);
    const measured = symbol.type === undefined || sizes === undefined ? undefined : sizes(symbol.type);
    if (measured !== undefined) sections.push(`tamaño: \`${measured.size} B\` · alineación: \`${measured.align} B\``);
    const member = node.kind === "member" ? (node as unknown as { object: never; name: string }) : undefined;
    const object_type = member === undefined ? undefined : type_of_node(file, member.object);
    const placed = fields === undefined || member === undefined || object_type === undefined
      ? undefined
      : fields(object_type, member.name);
    if (placed !== undefined) {
      sections.push(
        placed.width !== undefined
          ? `ancho: \`${placed.width} bit(s)\` · tamaño del campo: \`${placed.size} B\``
          : `desplazamiento: \`${placed.offset ?? 0} B\` · tamaño: \`${placed.size} B\``,
      );
    }
    return { markdown: sections.join("\n\n"), symbol };
  }

  const type = type_of_node(file, node);
  if (type !== undefined) {
    const sections: string[] = [`\`\`\`pengu\n${node_label(node)}: ${type_display(type)}\n\`\`\``];
    const measured = sizes === undefined ? undefined : sizes(type);
    if (measured !== undefined) sections.push(`tamaño: \`${measured.size} B\` · alineación: \`${measured.align} B\``);
    return { markdown: sections.join("\n\n"), symbol: undefined };
  }
  return undefined;
}

function enchanted_signature(file: FileAnalysis, realm: string, name: string): string | undefined {
  for (const enchanted of [...file.module.env.enchants.values(), ...file.analysis.enchants.values()]) {
    for (const [method_name, methods] of enchanted.methods) {
      if (method_name !== name) continue;
      for (const method of methods) {
        if (method.realm !== realm) continue;
        const params = method.info.params.map((param) => type_display(param)).join(", ");
        return `${method.info.mutable ? "mut " : ""}${name} = (${params}) -> ${type_display(method.info.result)}`;
      }
    }
  }
  return undefined;
}

export interface SignatureHelp {
  readonly signatures: readonly {
    readonly label: string;
    readonly parameters: readonly { readonly label: string }[];
  }[];
  readonly activeSignature: number;
  readonly activeParameter: number;
}

// Ayuda de firma dentro de una llamada `f(`.
export function signature_at(project: ProjectState, file: FileAnalysis, offset: number): SignatureHelp | undefined {
  const open = unmatched_open_paren(file.source.text, offset);
  if (open === undefined) return undefined;
  const callee = callee_before(file.source.text, open);
  if (callee === undefined) return undefined;

  const symbol = existing_symbol(project, file, callee.offset);
  if (symbol === undefined || symbol.type?.kind !== "function") return undefined;

  const parameters = symbol.type.params.map((param, index) => ({
    label: `${index + 1}: ${type_display(param)}`,
  }));
  const label = signature_of(symbol);
  return {
    signatures: [{ label, parameters }],
    activeSignature: 0,
    activeParameter: active_parameter(file.source.text, open, offset),
  };
}

function unmatched_open_paren(text: string, offset: number): number | undefined {
  let depth = 0;
  for (let index = offset - 1; index >= 0; index -= 1) {
    const char = text[index];
    if (char === ")") depth += 1;
    else if (char === "(") {
      if (depth === 0) return index;
      depth -= 1;
    } else if (char === "\n" && depth === 0) return undefined;
  }
  return undefined;
}

function callee_before(text: string, open: number): { readonly name: string; readonly offset: number } | undefined {
  let end = open;
  while (end > 0 && /\s/.test(text[end - 1] ?? "")) end -= 1;
  let start = end;
  while (start > 0 && /[A-Za-z0-9_:]/.test(text[start - 1] ?? "")) start -= 1;
  if (start === end) return undefined;
  const full = text.slice(start, end);
  const name = full.slice(full.lastIndexOf(":") + 1);
  return { name, offset: start + full.length - name.length };
}

function active_parameter(text: string, open: number, offset: number): number {
  let depth = 0;
  let count = 0;
  for (let index = open + 1; index < offset; index += 1) {
    const char = text[index];
    if (char === "(" || char === "[" || char === "{") depth += 1;
    else if (char === ")" || char === "]" || char === "}") depth -= 1;
    else if (char === "," && depth === 0) count += 1;
  }
  return count;
}

export { ident_at };
