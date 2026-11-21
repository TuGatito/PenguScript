// Tipos del AST de PenguScript.
//
// Un tipo se representa como un nodo inmutable. El parser produce
// estos nodos tal cual aparecen en el código; el checker decide
// después si el nombre existe y si los argumentos son válidos.

import type { Span } from "../util/span.ts";
import type { ExprNode } from "./ast_expr.ts";

export type TypeNode =
  | PrimitiveTypeNode
  | NamedTypeNode
  | OptionalTypeNode
  | RefTypeNode
  | FunctionTypeNode
  | TupleTypeNode
  | ArrayTypeNode;

export interface PrimitiveTypeNode {
  readonly kind: "primitive_type";
  readonly name: string;
  readonly span: Span;
}

export interface NamedTypeNode {
  readonly kind: "named_type";
  readonly name: string;
  readonly args: readonly TypeNode[];
  readonly span: Span;
}

export interface OptionalTypeNode {
  readonly kind: "optional_type";
  readonly inner: TypeNode;
  readonly span: Span;
}

export interface RefTypeNode {
  readonly kind: "ref_type";
  readonly inner: TypeNode;
  readonly mutable: boolean;
  readonly span: Span;
}

export interface FunctionTypeNode {
  readonly kind: "function_type";
  readonly params: readonly TypeNode[];
  readonly result: TypeNode;
  readonly span: Span;
}

export interface TupleTypeNode {
  readonly kind: "tuple_type";
  readonly items: readonly TypeNode[];
  readonly span: Span;
}

export interface ArrayTypeNode {
  readonly kind: "array_type";
  readonly element: TypeNode;
  readonly size: ExprNode;
  readonly span: Span;
}

export const PRIMITIVE_TYPES: ReadonlySet<string> = new Set([
  "void",
  "bool",
  "char",
  "signed char",
  "unsigned char",
  "short",
  "unsigned short",
  "int",
  "unsigned int",
  "long",
  "unsigned long",
  "long long",
  "unsigned long long",
  "float",
  "double",
  "long double",
  "wchar_t",
  "char8_t",
  "char16_t",
  "char32_t",
  "nullptr_t",
]);

export const STRING_TYPES: ReadonlySet<string> = new Set([
  "string",
  "wstring",
  "u8string",
  "u16string",
  "u32string",
  "string_view",
  "wstring_view",
  "u8string_view",
  "u16string_view",
  "u32string_view",
]);

export const FIXED_WIDTH_TYPES: ReadonlySet<string> = new Set([
  "int8_t",
  "int16_t",
  "int32_t",
  "int64_t",
  "uint8_t",
  "uint16_t",
  "uint32_t",
  "uint64_t",
  "size_t",
  "ptrdiff_t",
  "intptr_t",
  "uintptr_t",
  "byte",
]);

export const BUILTIN_TYPE_NAMES: ReadonlySet<string> = new Set([
  "string",
  "wstring",
  "u8string",
  "u16string",
  "u32string",
  "string_view",
  "wstring_view",
  "u8string_view",
  "u16string_view",
  "u32string_view",
  "vector",
  "array",
  "deque",
  "list",
  "forward_list",
  "set",
  "multiset",
  "unordered_set",
  "map",
  "multimap",
  "unordered_map",
  "unordered_multimap",
  "stack",
  "queue",
  "priority_queue",
  "span",
  "pair",
  "tuple",
  "bitset",
  "unique",
  "shared",
  "weak",
  "ref",
  "raw",
  "optional",
  "variant",
  "any",
  "function",
  "init_list",
  "complex",
  "atomic",
  "mutex",
  "shared_mutex",
  "condition_variable",
  "thread",
]);

const MULTI_WORD_PRIMITIVES: readonly string[] = [
  "unsigned long long",
  "unsigned long",
  "unsigned int",
  "unsigned short",
  "unsigned char",
  "signed char",
  "long long",
  "long double",
];

export function is_primitive_type(name: string): boolean {
  return PRIMITIVE_TYPES.has(name) || FIXED_WIDTH_TYPES.has(name);
}

export function is_builtin_type_name(name: string): boolean {
  return is_primitive_type(name) || BUILTIN_TYPE_NAMES.has(name);
}

export function multi_word_primitives(): readonly string[] {
  return MULTI_WORD_PRIMITIVES;
}

export function type_node_name(node: TypeNode): string {
  if (node.kind === "primitive_type" || node.kind === "named_type") {
    if (node.kind === "named_type" && node.args.length > 0) {
      return `${node.name}<${node.args.map(type_node_name).join(", ")}>`;
    }
    return node.name;
  }
  if (node.kind === "optional_type") {
    return `${type_node_name(node.inner)}?`;
  }
  if (node.kind === "ref_type") {
    return `${node.mutable ? "mut " : ""}ref<${type_node_name(node.inner)}>`;
  }
  if (node.kind === "function_type") {
    const params = node.params.map(type_node_name).join(", ");
    return `function<(${params}) -> ${type_node_name(node.result)}>`;
  }
  if (node.kind === "tuple_type") {
    return `tuple<${node.items.map(type_node_name).join(", ")}>`;
  }
  return `array<${type_node_name(node.element)}>`;
}
