// Evaluador de constantes: decide si una expresión puede calcularse al
// compilar. No produce valores: solo comprueba la forma y el tipo, que
// es lo que el codegen necesita para emitir `constexpr`.

import type { ExprNode } from "../frontend/ast.ts";
import type { ModuleInfo } from "./module_info.ts";
import type { PenguType } from "./types.ts";
import {
  BOOL,
  CHAR,
  DOUBLE,
  INT,
  NONE,
  NULLPTR,
  STRING,
  is_numeric,
  type_display,
} from "./types.ts";

export interface ConstScope {
  readonly module: ModuleInfo;
  readonly evaluating: Set<string>;
}

export function make_const_scope(module: ModuleInfo): ConstScope {
  return { module, evaluating: new Set() };
}

// Devuelve el tipo del valor si la expresión es evaluable en
// compilación; `undefined` si depende de ejecución.
export function eval_const(scope: ConstScope, expr: ExprNode): PenguType | undefined {
  switch (expr.kind) {
    case "int_lit":
      return INT;
    case "float_lit":
      return DOUBLE;
    case "bool_lit":
      return BOOL;
    case "char_lit":
      return CHAR;
    case "string_lit":
      return expr.parts.every((part) => part.kind === "text_part") ? STRING : undefined;
    case "none_lit":
      return NONE;
    case "nullptr_lit":
      return NULLPTR;
    case "ident": {
      const constant = scope.module.consts.get(expr.name);
      if (constant === undefined || constant.mutable) return undefined;
      if (scope.evaluating.has(expr.name)) return undefined;
      scope.evaluating.add(expr.name);
      try {
        return constant.decl.value === undefined
          ? undefined
          : eval_const(scope, constant.decl.value);
      } finally {
        scope.evaluating.delete(expr.name);
      }
    }
    case "unary": {
      const inner = eval_const(scope, expr.operand);
      if (inner === undefined) return undefined;
      if (expr.op === "not") return is_bool(inner) ? BOOL : undefined;
      if (expr.op === "-" || expr.op === "~") return is_numeric(inner) && !is_bool(inner) ? inner : undefined;
      return undefined;
    }
    case "binary": {
      const left = eval_const(scope, expr.left);
      const right = eval_const(scope, expr.right);
      if (left === undefined || right === undefined) return undefined;
      return eval_binary(expr.op, left, right);
    }
    case "cast": {
      const inner = eval_const(scope, expr.value);
      return inner === undefined ? undefined : inner;
    }
    case "vector_lit":
    case "set_lit":
      // Un contenedor necesita construcción en ejecución; solo los
      // literales quedan fuera de `constexpr`.
      return undefined;
    default:
      return undefined;
  }
}

function is_bool(type: PenguType): boolean {
  return type.kind === "primitive" && type.name === "bool";
}

function eval_binary(operator: string, left: PenguType, right: PenguType): PenguType | undefined {
  if (operator === "+" && is_string(left) && is_string(right)) return STRING;
  if (operator === "and" || operator === "or") {
    return is_bool(left) && is_bool(right) ? BOOL : undefined;
  }
  if (
    operator === "==" ||
    operator === "!=" ||
    operator === "<" ||
    operator === "<=" ||
    operator === ">" ||
    operator === ">="
  ) {
    return is_numeric(left) || is_string(left) ? BOOL : undefined;
  }
  if (["+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>"].includes(operator)) {
    if (!is_numeric(left) || !is_numeric(right)) return undefined;
    if (is_bool(left) || is_bool(right)) return undefined;
    return left;
  }
  return undefined;
}

function is_string(type: PenguType): boolean {
  return (type.kind === "primitive" && type.name === "string") || (type.kind === "named" && type.name === "string");
}

export function evaluable_hint(type: PenguType): string {
  return `de tipo «${type_display(type)}»`;
}
