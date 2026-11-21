// Sentencias y bloques.
//
// Las sentencias no producen valor por sí mismas; un bloque sí, y su
// valor es el de su última sentencia-expresión. Por eso `if`, `switch`
// y los bucles viven en el AST de expresiones aunque se usen como
// sentencias.

import type { Span } from "../util/span.ts";
import type { ExprNode } from "./ast_expr.ts";
import type { TypeNode } from "./ast_type.ts";

export interface Block {
  readonly kind: "block";
  readonly statements: readonly StmtNode[];
  readonly span: Span;
}

export type StmtNode =
  | ExprStmtNode
  | AssignStmtNode
  | ReturnStmtNode
  | BreakStmtNode
  | ContinueStmtNode
  | PassStmtNode
  | ConstStmtNode;

export interface ExprStmtNode {
  readonly kind: "expr_stmt";
  readonly expr: ExprNode;
  readonly span: Span;
}

export type AssignOp = "=" | "+=" | "-=" | "*=" | "/=" | "%=" | "&=" | "|=" | "^=" | ">>=" | "<<=";

export interface AssignStmtNode {
  readonly kind: "assign";
  readonly targets: readonly ExprNode[];
  readonly op: AssignOp;
  readonly value: ExprNode;
  readonly mutable: boolean;
  readonly declared_type: TypeNode | undefined;
  readonly span: Span;
}

export interface ReturnStmtNode {
  readonly kind: "return";
  readonly value: ExprNode | undefined;
  readonly span: Span;
}

export interface BreakStmtNode {
  readonly kind: "break";
  readonly value: ExprNode | undefined;
  readonly span: Span;
}

export interface ContinueStmtNode {
  readonly kind: "continue";
  readonly span: Span;
}

export interface PassStmtNode {
  readonly kind: "pass";
  readonly span: Span;
}

export interface ConstStmtNode {
  readonly kind: "const_stmt";
  readonly name: string;
  readonly declared_type: TypeNode | undefined;
  readonly value: ExprNode;
  readonly span: Span;
}
