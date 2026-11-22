// Estado compartido por los emisores de C++.
//
// El generador es una función pura sobre el AST: recibe el módulo ya
// chequeado y escribe líneas. El estado mutable (profundidad de
// indentación, scopes, contadores) vive aquí para no pasarlo por
// todas las firmas.

import type { ExprNode } from "../frontend/ast_expr.ts";
import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { error as diagnostic_error } from "../diagnostics/diagnostic.ts";
import { CODES } from "../diagnostics/codes.ts";
import type { ModuleInfo } from "../semantic/module_info.ts";
import type { PenguType } from "../semantic/types.ts";
import type { MethodTarget } from "../semantic/type_env.ts";
import { UNKNOWN } from "../semantic/types.ts";
import type { Span } from "../util/span.ts";
import { cpp_identifier } from "./cpp_types.ts";
import type { TypeRealms } from "./cpp_types.ts";

export interface GenContext {
  // Líneas que deben emitirse en el ámbito global (p. ej. `std::hash`).
  std_extra: string[];
  readonly module: ModuleInfo;
  readonly types: ReadonlyMap<ExprNode, PenguType>;
  readonly sink: DiagnosticSink;
  lines: string[];
  readonly scopes: string[][];
  indent: number;
  temp: number;
  // Pila de banderas de `break` para traducir el `else` del bucle.
  readonly break_flags: string[];
  // Variables que recogen el valor de cada `break value` (pila).
  readonly break_values: string[];
  // Verdadero mientras se emite el cuerpo de una función que
  // devuelve un valor (para convertir la última expresión en return).
  in_value_body: boolean;
  // Expresión C++ que representa `@` dentro del cuerpo actual.
  // `undefined` significa el `this` de un método de rune.
  self_expression: string | undefined;
  // Tipo de usuario → realm que lo declara (para cualificar nombres).
  type_realms: TypeRealms;
  // Alias de `invoke` → realm del módulo importado.
  external_realms: ReadonlyMap<string, string>;
  // Símbolo importado con `invoke {a, b} from "x"` → realm de origen.
  selective_symbols: ReadonlyMap<string, { readonly realm: string; readonly name: string }>;
  // Nodo del miembro → `realm::nombre` para métodos enhechizados.
  member_targets: ReadonlyMap<ExprNode, MethodTarget>;
  // Alias de `invoke` → módulo importado (para saber si una función es extern).
  external_modules: ReadonlyMap<string, ModuleInfo>;
}

export function make_gen_context(
  module: ModuleInfo,
  types: ReadonlyMap<ExprNode, PenguType>,
  sink: DiagnosticSink,
  type_realms: TypeRealms = new Map(),
  external_realms: ReadonlyMap<string, string> = new Map(),
  selective_symbols: ReadonlyMap<string, { readonly realm: string; readonly name: string }> = new Map(),
  member_targets: ReadonlyMap<ExprNode, MethodTarget> = new Map(),
  external_modules: ReadonlyMap<string, ModuleInfo> = new Map(),
): GenContext {
  return {
    module,
    types,
    sink,
    lines: [],
    scopes: [[]],
    indent: 0,
    temp: 0,
    break_flags: [],
    break_values: [],
    in_value_body: false,
    self_expression: undefined,
    type_realms,
    external_realms,
    selective_symbols,
    member_targets,
    external_modules,
    std_extra: [],
  };
}

export function gc_error(g: GenContext, message: string, span: Span): void {
  g.sink.add(diagnostic_error(CODES.cpp_emit_failed, message, span));
}

export function line(g: GenContext, text: string): void {
  g.lines.push(`${"  ".repeat(g.indent)}${text}`);
}

export function push_scope(g: GenContext): void {
  g.scopes.push([]);
}

export function pop_scope(g: GenContext): void {
  g.scopes.pop();
}

export function declare_local(g: GenContext, name: string): void {
  const scope = g.scopes[g.scopes.length - 1];
  if (scope !== undefined) scope.push(cpp_identifier(name));
}

export function is_local_declared(g: GenContext, name: string): boolean {
  const cpp_name = cpp_identifier(name);
  for (let index = g.scopes.length - 1; index >= 0; index -= 1) {
    const scope = g.scopes[index];
    if (scope !== undefined && scope.includes(cpp_name)) return true;
  }
  return false;
}

export function fresh_name(g: GenContext, prefix: string): string {
  g.temp += 1;
  return `_${prefix}${g.temp}`;
}

export function type_of(g: GenContext, node: ExprNode): PenguType {
  return g.types.get(node) ?? UNKNOWN;
}

export function expression_type(g: GenContext, node: ExprNode): PenguType {
  return g.types.get(node) ?? UNKNOWN;
}
