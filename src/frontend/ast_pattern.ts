// Patrones de `match`.
//
// Los patrones se mantienen separados de las expresiones porque no
// son evaluables: solo describen la forma del valor observado.

import type { Span } from "../util/span.ts";
import type { ExprNode } from "./ast_expr.ts";

export type PatternNode =
  | WildcardPatternNode
  | LiteralPatternNode
  | BindingPatternNode
  | VariantPatternNode
  | TuplePatternNode;

export interface WildcardPatternNode {
  readonly kind: "wildcard_pattern";
  readonly span: Span;
}

export interface LiteralPatternNode {
  readonly kind: "literal_pattern";
  readonly value: ExprNode;
  readonly span: Span;
}

export interface BindingPatternNode {
  readonly kind: "binding_pattern";
  readonly name: string;
  readonly mutable: boolean;
  readonly span: Span;
}

export interface VariantPatternNode {
  readonly kind: "variant_pattern";
  readonly path: readonly string[];
  readonly args: readonly PatternNode[];
  readonly span: Span;
}

export interface TuplePatternNode {
  readonly kind: "tuple_pattern";
  readonly items: readonly PatternNode[];
  readonly span: Span;
}
