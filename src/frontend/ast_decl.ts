// Declaraciones de nivel superior.
//
// Cada archivo `.pengu` es un módulo con un realm, invokes y
// declaraciones. El AST conserva el orden original para que el
// formateador y el LSP puedan reconstruir el archivo.

import type { Span } from "../util/span.ts";
import type { Block } from "./ast_stmt.ts";
import type { ExprNode } from "./ast_expr.ts";
import type { ParamNode } from "./ast_param.ts";
import type { TypeNode } from "./ast_type.ts";

export type DeclNode =
  | RealmDecl
  | InvokeDecl
  | ConstDecl
  | FunctionDecl
  | RuneDecl
  | EnchantingDecl
  | OmenDecl
  | EchoDecl
  | SealDecl
  | ExternDecl
  | IntrinsicDecl;

export interface RealmDecl {
  readonly kind: "realm_decl";
  readonly name: string;
  readonly span: Span;
}

export interface InvokeItem {
  readonly name: string;
  readonly alias: string | undefined;
  readonly span: Span;
}

export interface InvokeDecl {
  readonly kind: "invoke_decl";
  readonly path: string;
  readonly alias: string | undefined;
  readonly items: readonly InvokeItem[] | undefined;
  readonly span: Span;
}

export interface ConstDecl {
  readonly kind: "const_decl";
  readonly name: string;
  readonly declared_type: TypeNode | undefined;
  readonly value: ExprNode;
  readonly is_static: boolean;
  readonly mutable: boolean;
  readonly span: Span;
}

export interface FunctionDecl {
  readonly kind: "function_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  readonly needs: readonly string[];
  readonly params: readonly ParamNode[];
  readonly result: TypeNode | undefined;
  readonly body: Block;
  readonly is_unsafe: boolean;
  // Presente en los operadores libres (`operator + = (a, b) -> T`):
  // el nombre real de la función es el símbolo del operador.
  readonly operator?: string;
  readonly span: Span;
}

export interface FieldDecl {
  readonly name: string;
  readonly type: TypeNode;
  readonly default_value: ExprNode | undefined;
  readonly span: Span;
}

export interface ConstructorDecl {
  readonly params: readonly ParamNode[];
  readonly body: Block;
  readonly span: Span;
}

export interface RuneDecl {
  readonly kind: "rune_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  readonly parent: string | undefined;
  readonly fields: readonly FieldDecl[];
  readonly constructor: ConstructorDecl | undefined;
  readonly destructor: Block | undefined;
  readonly span: Span;
}

export interface MethodDecl {
  readonly name: string;
  readonly name_span: Span;
  readonly operator: string | undefined;
  readonly mutable: boolean;
  readonly sigils: readonly string[];
  readonly needs: readonly string[];
  readonly params: readonly ParamNode[];
  readonly result: TypeNode | undefined;
  readonly body: Block;
  readonly is_unsafe: boolean;
  readonly span: Span;
}

export interface EnchantingDecl {
  readonly kind: "enchanting_decl";
  readonly target: string;
  readonly target_span: Span;
  // Tipo patrón completo: `string`, `vector<T>`, `tuple<int, string>`.
  readonly target_type: TypeNode;
  readonly sigils: readonly string[];
  readonly methods: readonly MethodDecl[];
  readonly span: Span;
}

export interface OmenVariant {
  readonly name: string;
  readonly name_span: Span;
  readonly payload: readonly TypeNode[];
  readonly value: ExprNode | undefined;
  readonly span: Span;
}

export interface OmenDecl {
  readonly kind: "omen_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  readonly underlying: TypeNode | undefined;
  readonly is_flags: boolean;
  readonly variants: readonly OmenVariant[];
  readonly span: Span;
}

export interface EchoDecl {
  readonly kind: "echo_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  readonly target: TypeNode;
  readonly span: Span;
}

export interface SealDecl {
  readonly kind: "seal_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  readonly target: TypeNode;
  readonly span: Span;
}

export interface DeclareDecl {
  readonly name: string;
  readonly name_span: Span;
  readonly params: readonly ParamNode[];
  readonly result: TypeNode | undefined;
  readonly variadic: boolean;
  readonly span: Span;
}

export interface ExternDecl {
  readonly kind: "extern_decl";
  readonly abi: string | undefined;
  readonly declares: readonly DeclareDecl[];
  readonly span: Span;
}

// `declare`: funciones del runtime que implementa el compilador (stdlib).
export interface IntrinsicDecl {
  readonly kind: "intrinsic_decl";
  readonly declares: readonly DeclareDecl[];
  readonly span: Span;
}
