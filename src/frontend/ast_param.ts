// Parámetros de funciones, métodos y lambdas.

import type { Span } from "../util/span.ts";
import type { ExprNode } from "./ast_expr.ts";
import type { TypeNode } from "./ast_type.ts";

export interface ParamNode {
  readonly kind: "param";
  readonly name: string;
  readonly type: TypeNode | undefined;
  readonly default_value: ExprNode | undefined;
  readonly mutable: boolean;
  readonly span: Span;
}
