// «mut» y «unsafe» son contratos de llamada, no parte del tipo: una función
// con ellos no puede guardarse en un valor `function<...>`. Sin esta regla la
// barrera de `unsafe` (y la de mutabilidad) se perdería al pasar la función.

import type { ExprNode } from "../frontend/ast.ts";
import { CODES } from "../diagnostics/codes.ts";
import type { CheckContext } from "./checker_context.ts";
import { report_error } from "./checker_expr.ts";
import type { FunctionInfo } from "./module_info.ts";

function function_of(ctx: CheckContext, expr: ExprNode): FunctionInfo | undefined {
  if (expr.kind === "ident") {
    return ctx.module.functions.get(expr.name);
  }
  if (expr.kind === "path") {
    const [head, tail] = expr.segments;
    if (head === undefined || tail === undefined) return undefined;
    const imported = ctx.external?.modules.get(head);
    if (imported !== undefined) return imported.functions.get(tail);
    const selective = ctx.external?.selective.get(head);
    if (selective !== undefined) return selective.module.functions.get(head);
  }
  return undefined;
}

function reason_of(info: FunctionInfo): string | undefined {
  if (info.is_unsafe) return `«${info.name}» es «unsafe»`;
  const mutable = info.params.find((param) => param.mutable);
  if (mutable !== undefined) return `«${info.name}» recibe «mut ${mutable.name}»`;
  return undefined;
}

export function check_first_class_value(ctx: CheckContext, value: ExprNode | undefined): void {
  if (value === undefined) return;
  const info = function_of(ctx, value);
  if (info === undefined) return;
  const reason = reason_of(info);
  if (reason === undefined) return;
  report_error(
    ctx,
    CODES.not_first_class,
    `${reason}: no es un valor de primera clase`,
    value.span,
    ["«mut» y «unsafe» son contratos de llamada; llama a la función directamente"],
  );
}


