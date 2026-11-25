// Los tipos `opaque` solo existen como identificador: `struct Nombre;`.
//
// Usarlos por valor no compila en C++ (`incomplete type`) y el mensaje del
// compilador no dice nada del lenguaje, así que el checker lo rechaza antes:
// un opaco únicamente puede aparecer dentro de `raw`, `ref`, `unique`,
// `shared` o `weak`.

import type { Span } from "../util/span.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import { CODES } from "../diagnostics/codes.ts";
import type { CheckContext } from "./checker_context.ts";
import type { PenguType } from "./types.ts";
import { type_display } from "./types.ts";

const HANDLES: ReadonlySet<string> = new Set(["raw", "ref", "unique", "shared", "weak"]);

export function reject_opaque_by_value(
  ctx: CheckContext,
  type: PenguType,
  span: Span,
  context: string,
): void {
  if (is_opaque(ctx, type)) {
    ctx.sink.add(
      make_error(
        CODES.opaque_by_value,
        `«${type_display(type)}» es opaco: ${context} solo puede usarlo dentro de «raw<${type_display(type)}>» o «ref<${type_display(type)}>»`,
        span,
      ),
    );
    return;
  }
  switch (type.kind) {
    case "optional":
      reject_opaque_by_value(ctx, type.inner, span, context);
      break;
    case "array":
      reject_opaque_by_value(ctx, type.element, span, context);
      break;
    case "tuple":
      for (const item of type.items) reject_opaque_by_value(ctx, item, span, context);
      break;
    case "function":
      for (const param of type.params) reject_opaque_by_value(ctx, param, span, context);
      reject_opaque_by_value(ctx, type.result, span, context);
      break;
    default:
      break;
  }
}

function is_opaque(ctx: CheckContext, type: PenguType): boolean {
  if (type.kind !== "named") return false;
  if (HANDLES.has(type.name)) return false;
  return ctx.module.env.opaques.has(type.name);
}
