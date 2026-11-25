// Nodos de expresión del AST.
//
// Todo en PenguScript es una expresión: if, switch, match, for,
// while y do producen un valor. El parser conserva esa forma y el
// checker decide si el valor se descarta en posición de sentencia.

import type { Span } from "../util/span.ts";
import type { Block } from "./ast_stmt.ts";
import type { ParamNode } from "./ast_param.ts";
import type { PatternNode } from "./ast_pattern.ts";
import type { TypeNode } from "./ast_type.ts";

export type ExprNode =
  | IntLitNode
  | FloatLitNode
  | BoolLitNode
  | CharLitNode
  | StringLitNode
  | NoneLitNode
  | NullptrLitNode
  | IdentNode
  | SelfNode
  | PathNode
  | ParentCallNode
  | MemberNode
  | IndexNode
  | CallNode
  | UnaryNode
  | BinaryNode
  | CastNode
  | RangeNode
  | TupleNode
  | ContainerNewNode
  | VectorLitNode
  | MapLitNode
  | SetLitNode
  | ComprehensionNode
  | IfNode
  | SwitchNode
  | MatchNode
  | DoNode
  | WhileNode
  | RepeatNode
  | ForNumericNode
  | ForIterNode
  | LambdaNode
  | AwaitNode
  | UnsafeNode;

export interface IntLitNode {
  readonly kind: "int_lit";
  readonly value: string;
  readonly span: Span;
}

export interface FloatLitNode {
  readonly kind: "float_lit";
  readonly value: string;
  readonly span: Span;
}

export interface BoolLitNode {
  readonly kind: "bool_lit";
  readonly value: boolean;
  readonly span: Span;
}

export interface CharLitNode {
  readonly kind: "char_lit";
  readonly value: string;
  readonly span: Span;
}

export interface StringLitNode {
  readonly kind: "string_lit";
  readonly parts: readonly StringPartNode[];
  readonly span: Span;
}

export type StringPartNode =
  | { readonly kind: "text_part"; readonly text: string; readonly span: Span }
  | { readonly kind: "expr_part"; readonly expr: ExprNode; readonly span: Span };

export interface NoneLitNode {
  readonly kind: "none_lit";
  readonly span: Span;
}

export interface NullptrLitNode {
  readonly kind: "nullptr_lit";
  readonly span: Span;
}

export interface IdentNode {
  readonly kind: "ident";
  readonly name: string;
  readonly span: Span;
}

export interface SelfNode {
  readonly kind: "self";
  readonly span: Span;
}

export interface PathNode {
  readonly kind: "path";
  readonly segments: readonly string[];
  /** `Resultado<int>::Ok`: argumentos de tipo explícitos del tipo. */
  readonly type_args?: readonly TypeNode[];
  readonly span: Span;
}

export interface ParentCallNode {
  readonly kind: "parent_call";
  readonly args: readonly ArgNode[];
  readonly span: Span;
}

export interface MemberNode {
  readonly kind: "member";
  readonly object: ExprNode;
  readonly name: string;
  readonly name_span: Span;
  readonly span: Span;
}

export interface IndexNode {
  readonly kind: "index";
  readonly object: ExprNode;
  readonly index: ExprNode;
  readonly span: Span;
}

export interface ArgNode {
  readonly kind: "arg";
  readonly expr: ExprNode;
  readonly mutable: boolean;
  /** `f(...xs)`: expande un vector en los argumentos variádicos. */
  readonly spread: boolean;
  readonly span: Span;
}

export interface CallNode {
  readonly kind: "call";
  readonly callee: ExprNode;
  readonly type_args: readonly TypeNode[];
  readonly args: readonly ArgNode[];
  readonly span: Span;
}

export interface UnaryNode {
  readonly kind: "unary";
  readonly op: string;
  readonly operand: ExprNode;
  readonly span: Span;
}

export interface BinaryNode {
  readonly kind: "binary";
  readonly op: string;
  readonly left: ExprNode;
  readonly right: ExprNode;
  readonly span: Span;
}

export interface CastNode {
  readonly kind: "cast";
  readonly value: ExprNode;
  readonly type: TypeNode;
  readonly span: Span;
}

export interface RangeNode {
  readonly kind: "range";
  readonly start: ExprNode;
  readonly end: ExprNode;
  readonly inclusive: boolean;
  readonly span: Span;
}

export interface TupleNode {
  readonly kind: "tuple";
  readonly items: readonly ExprNode[];
  readonly span: Span;
}

export interface VectorLitNode {
  readonly kind: "vector_lit";
  readonly items: readonly ExprNode[];
  // Prefijo explícito: `vector<int>[...]`, `array<int, 4>[...]`, ...
  readonly declared_type?: TypeNode;
  readonly span: Span;
}

export interface ContainerNewNode {
  readonly kind: "container_new";
  readonly name: string;
  readonly type_args: readonly TypeNode[];
  // `bitset<8>(...)`: el tamaño va como expresión, no como tipo.
  readonly size?: ExprNode;
  readonly args: readonly ArgNode[];
  readonly span: Span;
}

export interface MapEntryNode {
  readonly key: ExprNode;
  readonly value: ExprNode;
  readonly span: Span;
}

export interface MapLitNode {
  readonly kind: "map_lit";
  readonly entries: readonly MapEntryNode[];
  readonly declared_type?: TypeNode;
  readonly span: Span;
}

export interface SetLitNode {
  readonly kind: "set_lit";
  readonly items: readonly ExprNode[];
  readonly declared_type?: TypeNode;
  readonly span: Span;
}

export interface ComprehensionNode {
  readonly kind: "comprehension";
  readonly container: "vector" | "map" | "set";
  readonly body: ExprNode;
  readonly key: ExprNode | undefined;
  readonly clauses: readonly ForClauseNode[];
  readonly span: Span;
}

export interface ForClauseNode {
  readonly kind: "for_clause";
  readonly variables: readonly string[];
  readonly mutable: boolean;
  readonly iterable: ExprNode;
  readonly condition: ExprNode | undefined;
  readonly span: Span;
}

export interface IfNode {
  readonly kind: "if";
  readonly condition: ExprNode;
  readonly then_block: Block;
  readonly else_block: Block | undefined;
  readonly unless: boolean;
  readonly span: Span;
}

export interface SwitchArm {
  readonly patterns: readonly ExprNode[];
  readonly body: Block;
  readonly span: Span;
}

export interface SwitchNode {
  readonly kind: "switch";
  readonly subject: ExprNode;
  readonly arms: readonly SwitchArm[];
  readonly else_block: Block | undefined;
  readonly span: Span;
}

export interface MatchArm {
  readonly pattern: PatternNode;
  readonly guard: ExprNode | undefined;
  readonly body: Block;
  readonly span: Span;
}

export interface MatchNode {
  readonly kind: "match";
  readonly subject: ExprNode;
  readonly arms: readonly MatchArm[];
  readonly else_block?: Block;
  readonly span: Span;
}

export interface DoNode {
  readonly kind: "do";
  readonly block: Block;
  readonly span: Span;
}

export interface WhileNode {
  readonly kind: "while";
  readonly condition: ExprNode;
  readonly body: Block;
  readonly until: boolean;
  readonly span: Span;
}

export interface RepeatNode {
  readonly kind: "repeat";
  readonly body: Block;
  readonly condition: ExprNode;
  readonly span: Span;
}

export interface ForNumericNode {
  readonly kind: "for_numeric";
  readonly variable: string;
  readonly variable_type: TypeNode | undefined;
  readonly mutable: boolean;
  readonly start: ExprNode;
  readonly end: ExprNode;
  readonly step: ExprNode | undefined;
  readonly body: Block;
  readonly else_block: Block | undefined;
  readonly span: Span;
}

export interface ForIterNode {
  readonly kind: "for_iter";
  readonly variables: readonly string[];
  readonly mutable: boolean;
  readonly iterable: ExprNode;
  readonly body: Block;
  readonly else_block: Block | undefined;
  readonly span: Span;
}

export interface AwaitNode {
  readonly kind: "await";
  readonly value: ExprNode;
  readonly span: Span;
}

export interface LambdaNode {
  readonly kind: "lambda";
  readonly sigils: readonly string[];
  readonly needs: readonly string[];
  readonly params: readonly ParamNode[];
  readonly result: TypeNode | undefined;
  readonly body: Block;
  readonly is_unsafe: boolean;
  readonly is_async: boolean;
  readonly span: Span;
}

export interface UnsafeNode {
  readonly kind: "unsafe";
  readonly block: Block;
  readonly span: Span;
}
