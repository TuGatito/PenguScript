// Raíz del AST: un módulo PenguScript completo.

import type { Span } from "../util/span.ts";
import type { DeclNode } from "./ast_decl.ts";

export interface Program {
  readonly kind: "program";
  readonly decls: readonly DeclNode[];
  readonly span: Span;
}

export * from "./ast_type.ts";
export * from "./ast_expr.ts";
export * from "./ast_pattern.ts";
export * from "./ast_param.ts";
export * from "./ast_stmt.ts";
export * from "./ast_decl.ts";
