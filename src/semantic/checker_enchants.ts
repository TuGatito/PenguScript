// Resolución de métodos declarados con `enchanting` sobre tipos
// incorporados (`string`, `vector<T>`, `map<K, V>`, `tuple<A, B>`…).
//
// El receptor no lleva realm en su tipo, así que el checker elige aquí la
// sobrecarga y anota el destino (`realm::nombre`), que el generador de C++
// usa para cualificar la llamada como función libre.

import type { ExprNode } from "../frontend/ast_expr.ts";
import { CODES } from "../diagnostics/codes.ts";
import type { PenguType } from "./types.ts";
import {
  UNKNOWN,
  any_type,
  function_type,
  generic_type,
  named,
  substitute_generics,
  type_display,
  type_equals,
} from "./types.ts";
import type { EnchantedMethod, MethodTarget } from "./type_env.ts";
import type { CheckContext } from "./checker_context.ts";
import { can_assign } from "./checker_context.ts";
import { infer_expr, report_error } from "./checker_expr.ts";
import { unify_sigils } from "./checker_generics.ts";
import { check_argument_value, check_mut_argument, root_ident, sequence_element_of } from "./checker_call.ts";
import { lookup } from "./scopes.ts";

/** Una sobrecarga ya instanciada para el receptor concreto. */
interface Candidate {
  readonly method: EnchantedMethod;
  readonly params: readonly PenguType[];
  readonly result: PenguType;
  readonly required: number;
  readonly variadic: boolean;
}

type MemberNode = Extract<ExprNode, { kind: "member" }>;
type CallNode = Extract<ExprNode, { kind: "call" }>;

interface ActualArg {
  readonly node: CallNode["args"][number];
  readonly type: PenguType;
}

// Clave del registro: nombre base y aridad del receptor.
export function receiver_shape(type: PenguType): { base: string; arity: number } | undefined {
  if (type.kind === "primitive") return { base: type.name, arity: 0 };
  if (type.kind === "named" && !type.generic) return { base: type.name, arity: type.args.length };
  if (type.kind === "tuple") return { base: "tuple", arity: type.items.length };
  if (type.kind === "array") return { base: "array", arity: 1 };
  if (type.kind === "optional") return { base: "optional", arity: 1 };
  if (type.kind === "ref") return { base: "ref", arity: 1 };
  if (type.kind === "unique") return { base: "unique", arity: 1 };
  if (type.kind === "shared") return { base: "shared", arity: 1 };
  if (type.kind === "weak") return { base: "weak", arity: 1 };
  if (type.kind === "raw") return { base: "raw", arity: 1 };
  return undefined;
}

/** ¿Existe algún método enhechizado con ese nombre? Evita inferir el receptor. */
export function has_enchanted_method(ctx: CheckContext, name: string): boolean {
  for (const entry of ctx.module.env.enchants.values()) {
    if (entry.methods.has(name)) return true;
  }
  for (const entry of ctx.external?.enchants.values() ?? []) {
    if (entry.methods.has(name)) return true;
  }
  return false;
}

// El módulo propio manda; los imports solo se consultan si el propio no
// declara ese nombre.
function entries_for(ctx: CheckContext, base: string, arity: number, name: string) {
  const key = `${base}/${arity}`;
  const own = ctx.module.env.enchants.get(key);
  if (own !== undefined && own.methods.has(name)) return [own];
  const external = ctx.external?.enchants.get(key);
  if (external !== undefined && external.methods.has(name)) return [external];
  return [];
}

// Los argumentos de tipo del receptor, en el orden de los sigilos del
// patrón: `vector<T>` → [T], `tuple<A, B>` → [A, B], `optional<T>` → [T].
function receiver_arguments(type: PenguType): readonly PenguType[] {
  switch (type.kind) {
    case "named":
      return type.args;
    case "tuple":
      return type.items;
    case "array":
      return [type.element];
    case "optional":
    case "ref":
    case "unique":
    case "shared":
    case "weak":
    case "raw":
      return [type.inner];
    default:
      return [];
  }
}

function instantiate(method: EnchantedMethod, object: PenguType): Candidate {
  const mapping = new Map<string, PenguType>();
  const args = receiver_arguments(object);
  method.info.sigils.forEach((sigil, index) => {
    const real = args[index];
    if (real !== undefined) mapping.set(sigil, real);
  });
  const params = method.info.params.map((param) => substitute_generics(param, mapping));
  const result = substitute_generics(method.info.result, mapping);
  const variadic = method.info.variadic;
  const required = params.length - (variadic ? 1 : 0);
  return { method, params, result, required, variadic };
}

function candidates_for(ctx: CheckContext, object: PenguType, name: string): readonly Candidate[] {
  const shape = receiver_shape(object);
  if (shape === undefined) return [];
  const candidates: Candidate[] = [];
  for (const entry of entries_for(ctx, shape.base, shape.arity, name)) {
    for (const method of entry.methods.get(name) ?? []) {
      candidates.push(instantiate(method, object));
    }
  }
  return candidates;
}

function signature_of(candidate: Candidate, name: string): string {
  const params = candidate.params.map((param) => type_display(param)).join(", ");
  return `${name}(${params}) -> ${type_display(candidate.result)}`;
}

function signature_list(candidates: readonly Candidate[], name: string): string {
  return candidates.map((candidate) => signature_of(candidate, name)).join(" | ");
}

// Compatibilidad sin emitir diagnósticos: sirve para elegir sobrecarga.
function accepts(candidate: Candidate, args: readonly ActualArg[]): boolean {
  const plain = args.filter((arg) => !arg.node.spread).length;
  if (plain < candidate.required) return false;
  if (!candidate.variadic && plain > candidate.params.length) return false;
  return args.every((arg, index) => {
    const param = candidate.params[Math.min(index, candidate.params.length - 1)];
    if (param === undefined) return false;
    if (!arg.node.spread) return can_assign(param, arg.type);
    if (!candidate.variadic) return false;
    const inner = sequence_element_of(arg.type);
    return inner === undefined || can_assign(param, inner);
  });
}

function exact_matches(candidate: Candidate, args: readonly ActualArg[]): number {
  return args.reduce((count, arg, index) => {
    if (arg.node.spread) return count;
    const param = candidate.params[Math.min(index, candidate.params.length - 1)];
    return param !== undefined && type_equals(param, arg.type) ? count + 1 : count;
  }, 0);
}

// Un método `mut` exige un receptor modificable.
function check_mut_self(ctx: CheckContext, callee: MemberNode, object: PenguType): void {
  // Un `ref`, `shared`, `unique` o `raw` permite modificar lo apuntado,
  // aunque el receptor sea un valor temporal.
  if (
    object.kind === "ref" ||
    object.kind === "shared" ||
    object.kind === "unique" ||
    object.kind === "raw"
  ) {
    return;
  }
  const root = root_ident(callee.object);
  if (root === undefined) {
    report_error(
      ctx,
      CODES.mutable_required,
      `«${callee.name}» es «mut»: necesita una variable declarada con «mut»`,
      callee.name_span,
    );
    return;
  }
  const variable = lookup(ctx.scope, root.name);
  if (variable === undefined || variable.mutable) return;
  const type: PenguType = variable.type;
  if (type.kind === "ref" || type.kind === "shared" || type.kind === "unique" || type.kind === "raw") return;
  report_error(
    ctx,
    CODES.mutable_required,
    `«${root.name}» es inmutable; decláralo con «mut» para llamar a «${callee.name}»`,
    root.span,
  );
}

function validate_arguments(
  ctx: CheckContext,
  chosen: Candidate,
  node: CallNode,
  name: string,
  args: readonly ActualArg[],
): void {
  const params = chosen.params;
  const element = chosen.variadic ? params[params.length - 1] : undefined;
  const fixed = chosen.variadic ? params.slice(0, -1) : params;
  const plain = node.args.filter((arg) => !arg.spread).length;

  if (plain < chosen.required || (!chosen.variadic && plain > params.length)) {
    const expected =
      chosen.required === params.length
        ? `${params.length}`
        : chosen.variadic
          ? `al menos ${chosen.required}`
          : `entre ${chosen.required} y ${params.length}`;
    report_error(
      ctx,
      CODES.wrong_arity,
      `«${name}» espera ${expected} argumento(s), recibió ${plain}`,
      node.span,
    );
  }

  node.args.forEach((arg, index) => {
    check_mut_argument(ctx, chosen.method.info.param_mutables, index, arg, name);
    const actual = args[index];
    if (actual === undefined) return;
    const expected = index < fixed.length ? fixed[index] : element;
    if (expected === undefined) return;
    const value = arg.spread ? sequence_element_of(actual.type) : actual.type;
    if (value === undefined) return;
    check_argument_value(ctx, expected, value, index, name, arg.expr.span);
  });
}

function annotate(ctx: CheckContext, node: ExprNode, method: EnchantedMethod): void {
  ctx.member_targets?.set(node, { realm: method.realm, name: method.info.name });
}

/** Resuelve `obj.metodo(args)`; `undefined` si no hay enhechizamiento. */
export function resolve_enchanted_call(
  ctx: CheckContext,
  node: CallNode,
  object: PenguType,
  name: string,
): PenguType | undefined {
  if (node.callee.kind !== "member") return undefined;
  const candidates = candidates_for(ctx, object, name);
  if (candidates.length === 0) return undefined;

  const args: ActualArg[] = node.args.map((arg) => ({ node: arg, type: infer_expr(ctx, arg.expr) }));
  const compatible = candidates.filter((candidate) => accepts(candidate, args));
  if (compatible.length === 0) {
    report_error(
      ctx,
      CODES.type_mismatch,
      `ninguna sobrecarga de «${name}» acepta estos argumentos; candidatos: ${signature_list(candidates, name)}`,
      node.span,
    );
    return UNKNOWN;
  }

  let chosen = compatible[0] as Candidate;
  if (compatible.length > 1) {
    const ranked = compatible
      .map((candidate) => ({ candidate, score: exact_matches(candidate, args) }))
      .sort((left, right) => right.score - left.score);
    const best = ranked[0] as { candidate: Candidate; score: number };
    const second = ranked[1] as { candidate: Candidate; score: number };
    if (best.score === second.score) {
      report_error(
        ctx,
        CODES.ambiguous_method,
        `«${name}» es ambiguo para estos argumentos; candidatos: ${signature_list(compatible, name)}`,
        node.span,
      );
      return UNKNOWN;
    }
    chosen = best.candidate;
  }

  if (chosen.method.info.mutable) check_mut_self(ctx, node.callee, object);
  validate_arguments(ctx, chosen, node, name, args);
  annotate(ctx, node.callee, chosen.method);
  return chosen.result;
}

/** Acceso al método sin llamarlo: solo si no hay sobrecargas. */
export function resolve_enchanted_member(
  ctx: CheckContext,
  node: MemberNode,
  object: PenguType,
): PenguType | undefined {
  const candidates = candidates_for(ctx, object, node.name);
  if (candidates.length === 0) return undefined;
  if (candidates.length > 1) {
    report_error(
      ctx,
      CODES.ambiguous_method,
      `«${node.name}» está sobrecargado y no se puede usar como valor; candidatos: ${signature_list(candidates, node.name)}`,
      node.span,
      ["llama al método con sus argumentos para elegir la sobrecarga"],
    );
    return UNKNOWN;
  }
  const only = candidates[0] as Candidate;
  if (only.method.info.mutable) {
    report_error(
      ctx,
      CODES.not_first_class,
      `«${node.name}» es «mut»: no es un valor de primera clase`,
      node.span,
      ["un método «mut» modifica el receptor; llámalo directamente"],
    );
    return UNKNOWN;
  }
  annotate(ctx, node, only.method);
  return function_type(only.params, only.result, only.variadic, only.required);
}

export function enchanted_target_of(ctx: CheckContext, node: ExprNode): MethodTarget | undefined {
  return ctx.member_targets?.get(node);
}

export { check_mut_self as enforce_mut_receiver };