// Coerción de literales y constantes enteras.
//
// El checker es estricto con los tipos, pero un literal que cabe en el
// destino no es ambiguo: `Color(255, 0, 0, 255)` con campos `uint8_t` o
// `Fade(color, 0.5)` con un parámetro `float` deben compilar. Sin esto,
// cualquier binding de C obliga a escribir `uint8_t::from(255)` en cada
// argumento, que es ruido.
//
// Solo se aceptan literales y constantes evaluables (con su valor conocido);
// una variable `int` sigue sin poder pasarse a `uint8_t` sin `::from`.

import type { ExprNode } from "../frontend/ast.ts";
import type { CheckContext } from "./checker_context.ts";
import { float_rank, integer_shape } from "./types.ts";
import type { PenguType } from "./types.ts";

// Una constante puede referirse a otra; el límite evita un bucle si el
// checker todavía no ha reportado el ciclo.
const MAX_DEPTH = 8;

export function integer_value_of(ctx: CheckContext, expr: ExprNode, depth = 0): bigint | undefined {
  if (depth > MAX_DEPTH) return undefined;
  switch (expr.kind) {
    case "int_lit":
      return parse_integer(expr.value);
    case "unary": {
      const inner = integer_value_of(ctx, expr.operand, depth + 1);
      if (inner === undefined) return undefined;
      if (expr.op === "-") return -inner;
      if (expr.op === "~") return ~inner;
      return undefined;
    }
    case "ident":
      return constant_value(ctx, ctx.module, expr.name, depth);
    case "path": {
      if (expr.segments.length !== 2) return undefined;
      const [alias, name] = expr.segments;
      if (alias === undefined || name === undefined) return undefined;
      const module = ctx.external?.modules.get(alias);
      if (module !== undefined) return constant_value(ctx, module, name, depth);
      const selected = ctx.external?.selective.get(alias);
      return selected === undefined ? undefined : constant_value(ctx, selected.module, selected.name, depth);
    }
    default:
      return undefined;
  }
}

function constant_value(
  ctx: CheckContext,
  module: { readonly consts: ReadonlyMap<string, { readonly mutable: boolean; readonly decl: { readonly value?: ExprNode } }> },
  name: string,
  depth: number,
): bigint | undefined {
  const constant = module.consts.get(name);
  if (constant === undefined || constant.mutable) return undefined;
  if (constant.decl.value === undefined) return undefined;
  return integer_value_of(ctx, constant.decl.value, depth + 1);
}

function parse_integer(text: string): bigint | undefined {
  try {
    return BigInt(text);
  } catch {
    return undefined;
  }
}

function in_integer_range(value: bigint, bits: number, signed: boolean): boolean {
  if (!signed) return value >= 0n && value < 1n << BigInt(bits);
  const limit = 1n << BigInt(bits - 1);
  return value >= -limit && value < limit;
}

// ¿El valor de esta expresión (literal o constante) encaja en `expected`?
export function literal_fits_type(ctx: CheckContext, expected: PenguType, value: ExprNode | undefined): boolean {
  if (value === undefined) return false;
  const shape = integer_shape(expected);
  if (shape !== undefined) {
    const number = integer_value_of(ctx, value);
    if (number === undefined) return false;
    return in_integer_range(number, shape.bits, shape.signed);
  }
  if (float_rank(expected) !== undefined) {
    // `0.5` es un literal `double` que cabe en `float`; un entero literal
    // también se convierte (como en C++), pero una variable no.
    if (value.kind === "float_lit") return true;
    return integer_value_of(ctx, value) !== undefined;
  }
  return false;
}
