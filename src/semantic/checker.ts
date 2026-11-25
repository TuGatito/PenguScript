// Punto de entrada del checker.
//
// Recoge el módulo y comprueba cada declaración: constantes,
// funciones, runes, omens y bloques `enchanting`.

import type { Block, ExprNode, Program } from "../frontend/ast.ts";
import type {
  CallbackDecl,
  ConstDecl,
  DeclNode,
  EnchantingDecl,
  FunctionDecl,
  MeldDecl,
  MethodDecl,
  OmenDecl,
  RuneDecl,
} from "../frontend/ast_decl.ts";
import type { ParamNode } from "../frontend/ast_param.ts";
import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { CODES } from "../diagnostics/codes.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import type { CheckContext } from "./checker_context.ts";
import { annotate_literal, check_initialization, make_context, record_local, report_type_mismatch } from "./checker_context.ts";
import { collect_module } from "./module_info.ts";
import { eval_const, make_const_scope } from "./const_eval.ts";
import type { ModuleInfo } from "./module_info.ts";
import { declare } from "./scopes.ts";
import { infer_block, param_binding_type } from "./checker_expr.ts";
import type { MethodTarget, RuneInfo } from "./type_env.ts";
import {
  find_rune_field,
  find_rune_method,
  register_qualified_types,
  report_pending_types,
  resolve_type_node,
} from "./type_env.ts";
import {
  UNKNOWN,
  VOID,
  any_type,
  generic_type,
  is_any,
  named,
  primitive,
  shared_type,
  type_equals,
  unique_type,
  weak_type,
} from "./types.ts";
import { STRING_TYPES, is_primitive_type } from "../frontend/ast_type.ts";
import { enchant_target_of, type_pattern_type } from "./enchant_targets.ts";
import { check_bitfield, check_meld } from "./meld_check.ts";
import { reject_opaque_by_value } from "./opaque_check.ts";
import type { PenguType } from "./types.ts";
import { future_inner } from "./types.ts";
import type { ExternalImports } from "./external.ts";
import type { LocalSymbol } from "./symbols.ts";
import type { Span } from "../util/span.ts";

export interface CheckOptions {
  // Si se pasa, el checker anota el tipo de cada expresión. Lo usa el
  // generador de C++ para deducir tipos de lambdas y literales.
  readonly types?: Map<ExprNode, PenguType>;
  readonly member_targets?: Map<ExprNode, MethodTarget>;
  readonly external?: ExternalImports;
  // Si se pasa, el checker acumula las declaraciones locales aquí.
  readonly locals?: LocalSymbol[];
}

export function check_program(
  file: string,
  program: Program,
  sink: DiagnosticSink,
  options: CheckOptions = {},
): ModuleInfo {
  const module = collect_module(file, program, sink);
  check_loaded_module(module, program, sink, options);
  return module;
}

// Comprueba un módulo ya recogido (con su realm ya fusionado).
export function check_loaded_module(
  module: ModuleInfo,
  program: Program,
  sink: DiagnosticSink,
  options: CheckOptions = {},
): void {
  const ctx = make_context(module.file, module, sink);
  ctx.types = options.types;
  ctx.member_targets = options.member_targets;
  ctx.external = options.external;
  if (options.locals !== undefined) ctx.locals = options.locals;
  if (options.external !== undefined) {
    register_qualified_types(module.env, options.external.modules);
  }

  for (const decl of program.decls) {
    check_decl(ctx, decl);
  }

  report_pending_types(module.env, sink);
}

function check_decl(ctx: CheckContext, decl: DeclNode): void {
  switch (decl.kind) {
    case "const_decl":
      check_const(ctx, decl);
      break;
    case "function_decl":
      check_free_operator_given(ctx, decl);
      check_function(ctx, decl);
      break;
    case "rune_decl":
      check_rune(ctx, decl);
      break;
    case "meld_decl":
      check_meld(ctx, decl);
      break;
    case "callback_decl":
      check_callback(ctx, decl);
      break;
    case "enchanting_decl":
      check_enchanting(ctx, decl);
      break;
    case "omen_decl":
      check_omen(ctx, decl);
      break;
    case "realm_decl":
    case "invoke_decl":
    case "echo_decl":
    case "seal_decl":
    case "link_decl":
    case "opaque_decl":
      break;
    case "extern_decl":
      check_extern(ctx, decl);
      break;
  }
}

function check_callback(ctx: CheckContext, decl: CallbackDecl): void {
  for (const param of decl.params) {
    const type = param.type === undefined
      ? any_type(`parámetro ${param.name}`)
      : resolve_type_node(param.type, ctx.module.env, ctx.sink);
    reject_opaque_by_value(ctx, type, param.span, `el parámetro «${param.name}» del callback`);
  }
  if (decl.result !== undefined) {
    const result = resolve_type_node(decl.result, ctx.module.env, ctx.sink);
    reject_opaque_by_value(ctx, result, decl.result.span, "el retorno del callback");
  }
}

function check_extern(ctx: CheckContext, decl: Extract<DeclNode, { kind: "extern_decl" }>): void {
  for (const declared of decl.declares) {
    for (const param of declared.params) {
      if (param.type === undefined) continue;
      const type = resolve_type_node(param.type, ctx.module.env, ctx.sink);
      reject_opaque_by_value(ctx, type, param.span, `el parámetro «${param.name}» de «${declared.name}»`);
    }
    if (declared.result !== undefined) {
      const result = resolve_type_node(declared.result, ctx.module.env, ctx.sink);
      reject_opaque_by_value(ctx, result, declared.result.span, `el retorno de «${declared.name}»`);
    }
  }
}

function check_const(ctx: CheckContext, decl: ConstDecl): void {
  const info = ctx.module.consts.get(decl.name);
  if (info === undefined) return;
  if (decl.mutable && !decl.is_static && ctx.unsafe_depth === 0) {
    // La mutabilidad global solo tiene sentido en `static mut`; el
    // parser ya lo restringe, aquí no hace falta nada más.
  }

  const value = infer_block(ctx, {
    kind: "block",
    statements: [{ kind: "expr_stmt", expr: decl.value, span: decl.value.span }],
    span: decl.span,
  });

  if (info.declared_type !== undefined) {
    check_initialization(ctx, info.declared_type, value, decl.value.span, "en la constante", decl.value);
  } else {
    info.type = value;
  }

  info.evaluable = eval_const(make_const_scope(ctx.module), decl.value) !== undefined;
  if (decl.is_define && !info.evaluable) {
    ctx.sink.add(
      make_error(
        CODES.not_const_evaluable,
        `«${decl.name}» es «define» y necesita un valor evaluable en compilación`,
        decl.value.span,
        "usa literales, «const» u operaciones puras",
      ),
    );
  }
  if (decl.is_static && !info.evaluable) {
    ctx.sink.add(
      make_error(
        CODES.not_const_evaluable,
        `«${decl.name}» es «static mut» y necesita un valor evaluable en compilación`,
        decl.value.span,
        "usa literales, «const» o operaciones puras",
      ),
    );
  }
}

// Los sigilos de la declaración vuelven a estar activos mientras se
// comprueba su cuerpo: dentro, `T` es un tipo opaco que el codegen
// traduce a un parámetro de plantilla de C++.
function with_sigils(ctx: CheckContext, sigils: readonly string[], body: () => void): void {
  const previous = new Map(ctx.module.env.sigils);
  for (const sigil of sigils) ctx.module.env.sigils.set(sigil, generic_type(sigil));
  try {
    body();
  } finally {
    ctx.module.env.sigils.clear();
    for (const [key, value] of previous) ctx.module.env.sigils.set(key, value);
  }
}

function check_function(ctx: CheckContext, decl: FunctionDecl): void {
  const info = ctx.module.functions.get(decl.name);
  if (info === undefined) return;

  reject_opaque_by_value(ctx, info.result, decl.span, "el retorno de la función");
  const previous_return = ctx.current_return;
  const previous_unsafe = ctx.unsafe_depth;
  const previous_async = ctx.async_depth;
  // El cuerpo de una función `async` vale `T` (no `future<T>`), que es lo que
  // el módulo ya guardó desenvuelto; resolver el `TypeNode` otra vez aquí
  // rompería los sigilos genéricos, que solo existen dentro de `with_sigils`.
  ctx.current_return = decl.is_async
    ? future_inner(info.result) ?? UNKNOWN
    : is_any(info.result) ? undefined : info.result;
  if (decl.is_unsafe) ctx.unsafe_depth += 1;
  if (decl.is_async) ctx.async_depth += 1;

  with_sigils(ctx, decl.sigils, () => {
  try {
    const body = with_fresh_scope(ctx, () => {
      check_params(ctx, decl.params, decl.body.span);
      return infer_block(ctx, decl.body);
    });
    if (ctx.current_return !== undefined) {
      annotate_literal(ctx, ctx.current_return, last_expression(decl.body));
      if (ctx.current_return.kind === "void") {
        // Un cuerpo void puede terminar en cualquier expresión sin valor.
      } else if (!type_equals(body, ctx.current_return) && !is_any(body)) {
        check_initialization(ctx, ctx.current_return, body, decl.body.span, "en el retorno de la función", last_expression(decl.body));
      }
    } else if (!is_any(info.result) && !type_equals(body, info.result)) {
      annotate_literal(ctx, info.result, last_expression(decl.body));
      check_initialization(ctx, info.result, body, decl.body.span, "en el retorno de la función", last_expression(decl.body));
    }
  } finally {
    ctx.current_return = previous_return;
    ctx.unsafe_depth = previous_unsafe;
    ctx.async_depth = previous_async;
  }
  });
}

function check_params(ctx: CheckContext, params: readonly ParamNode[], scope: Span): void {
  for (const param of params) {
    const type = param.type === undefined
      ? any_type(`parámetro ${param.name}`)
      : resolve_type_node(param.type, ctx.module.env, ctx.sink);
    reject_opaque_by_value(ctx, type, param.span, `el parámetro «${param.name}»`);
    const binding = param_binding_type(param, type);
    declare(ctx.scope, param.name, binding, {
      mutable: param.mutable,
      kind: "param",
      span: param.span,
    });
    record_local(ctx, param.name, binding, param.mutable, "parameter", param.span, scope);
    if (param.default_value !== undefined) {
      const value = infer_block(ctx, {
        kind: "block",
        statements: [{ kind: "expr_stmt", expr: param.default_value, span: param.default_value.span }],
        span: param.span,
      });
      check_initialization(ctx, type, value, param.default_value.span, `en el valor por defecto de «${param.name}»`, param.default_value);
    }
  }
}

// Un operador libre y un método `enchanting` con el mismo símbolo y el
// mismo primer tipo serían dos definiciones de la misma operación.
function check_free_operator_given(ctx: CheckContext, decl: FunctionDecl): void {
  if (decl.operator === undefined) return;
  const first = decl.params[0];
  if (first === undefined || first.type === undefined) return;
  const type = resolve_type_node(first.type, ctx.module.env, ctx.sink);
  if (type.kind !== "named") return;
  const rune = ctx.module.env.runes.get(type.name);
  if (rune === undefined) return;
  if (find_rune_method(ctx.module.env, rune, decl.operator) === undefined) return;
  ctx.sink.add(make_error(
    CODES.invalid_operator,
    `el operador libre «${decl.operator}» duplica el de «${type.name}»`,
    decl.name_span,
  ));
}

function check_rune(ctx: CheckContext, decl: RuneDecl): void {
  const rune = ctx.module.env.runes.get(decl.name);
  if (rune === undefined) return;
  const self_type = named(decl.name);

  with_sigils(ctx, decl.sigils, () => {
  const previous_self = ctx.self_type;
  const previous_mutable = ctx.self_mutable;
  const previous_assign = ctx.self_assign;
  const previous_return = ctx.current_return;

  try {
    ctx.self_type = self_type;
    ctx.self_mutable = false;
    ctx.self_assign = false;

    check_field_shadowing(ctx, decl, rune);

    for (const field of decl.fields) {
      const info = rune.fields.get(field.name);
      const type = info?.type;
      if (type === undefined) continue;
      if (field.bits !== undefined) check_bitfield(ctx, type, field.bits, field.span);
      reject_opaque_by_value(ctx, type, field.span, "un campo");
    }

    for (const field of decl.fields) {
      if (field.default_value === undefined) continue;
      const type = resolve_type_node(field.type, ctx.module.env, ctx.sink);
      const value = infer_block(ctx, {
        kind: "block",
        statements: [{ kind: "expr_stmt", expr: field.default_value, span: field.default_value.span }],
        span: field.span,
      });
      // El valor por defecto toma el tipo declarado del campo (si no,
      // un `[]` vacío se inferiría como `vector<any>`).
      ctx.types?.set(field.default_value, type);
      check_initialization(ctx, type, value, field.default_value.span, `en el campo «${field.name}»`, field.default_value);
    }

    const constructor = decl.constructor;
    if (constructor !== undefined) {
      ctx.self_assign = true;
      ctx.current_return = undefined;
      with_fresh_scope(ctx, () => {
        check_params(ctx, constructor.params, constructor.body.span);
        infer_block(ctx, constructor.body);
      });
      ctx.self_assign = false;
    }

    const destructor = decl.destructor;
    if (destructor !== undefined) {
      ctx.current_return = undefined;
      with_fresh_scope(ctx, () => infer_block(ctx, destructor));
    }
  } finally {
    ctx.self_type = previous_self;
    ctx.self_mutable = previous_mutable;
    ctx.self_assign = previous_assign;
    ctx.current_return = previous_return;
  }
  });
}

function check_enchanting(ctx: CheckContext, decl: EnchantingDecl): void {
  const target = decl.target;
  // En sellos y echoes `@` es el valor subyacente; solo una rune
  // tiene un `self` con identidad propia.
  const alias = ctx.module.env.aliases.get(target);
  const builtin_self = enchant_self_type(ctx, decl);
  const self_type = alias !== undefined ? alias.target : builtin_self ?? named(target);

  // Un `echo` es un alias transparente: sus operadores son los del
  // tipo subyacente y no se pueden sobrecargar.
  if (alias !== undefined && !alias.seal) {
    for (const method of decl.methods) {
      if (method.operator === undefined) continue;
      ctx.sink.add(make_error(
        CODES.invalid_operator,
        `«${target}» es un «echo» transparente: no admite operadores; usa «seal»`,
        method.name_span,
      ));
    }
  }

  // Los tipos incorporados no admiten operadores: `=` y compañía ya
  // tienen significado en C++ y sobrecargarlos cambiaría el de todo el
  // programa.
  if (builtin_self !== undefined) {
    for (const method of decl.methods) {
      if (method.operator === undefined) continue;
      ctx.sink.add(make_error(
        CODES.invalid_operator,
        `«${target}» es un tipo incorporado: no admite el operador «${method.operator}»`,
        method.name_span,
      ));
    }
  }

  const target_sigils = ctx.module.env.runes.get(target)?.sigils ?? decl.sigils;
  with_sigils(ctx, target_sigils, () => {
    for (const method of decl.methods) {
      with_sigils(ctx, method.sigils, () => check_method(ctx, method, self_type));
    }
  });
}

// Los campos no se pueden sombrear: una hija que repite un campo del
// padre tendría dos copias y accesos ambiguos en C++.
function check_field_shadowing(ctx: CheckContext, decl: RuneDecl, rune: RuneInfo): void {
  const parent = rune.parent === undefined ? undefined : ctx.module.env.runes.get(rune.parent);
  if (parent === undefined) return;
  for (const field of decl.fields) {
    const inherited = find_rune_field(ctx.module.env, parent, field.name);
    if (inherited === undefined) continue;
    ctx.sink.add(make_error(
      CODES.field_shadow,
      `«${decl.name}.${field.name}» sombrea el campo heredado de «${parent.name}»`,
      field.span,
    ));
  }
}

// Tipo del receptor cuando el `enchanting` apunta a un tipo incorporado.
function enchant_self_type(ctx: CheckContext, decl: EnchantingDecl): PenguType | undefined {
  if (enchant_target_of(decl.target) === undefined) return undefined;
  // En `enchanting unique<T>`, `@` es el valor apuntado, no el puntero.
  if (decl.target === "unique" || decl.target === "shared" || decl.target === "weak") {
    const pattern = type_pattern_type(decl.target_type);
    if (pattern.kind === "named" && pattern.args.length === 1) {
      const inner = substitute_sigils(pattern.args[0] ?? pattern, new Set(decl.sigils));
      if (decl.target === "weak") return weak_type(inner);
      // En uniques y shared el método trabaja sobre el valor apuntado.
      return inner;
    }
  }
  // Los sigilos del patrón (`vector<T>`) llegan como tipos con nombre; el
  // cuerpo del método debe verlos como sigilos genéricos.
  return substitute_sigils(type_pattern_type(decl.target_type), new Set(decl.sigils));
}

function substitute_sigils(type: PenguType, sigils: ReadonlySet<string>): PenguType {
  switch (type.kind) {
    case "named":
      if (sigils.has(type.name) && type.args.length === 0) return generic_type(type.name);
      return { ...type, args: type.args.map((arg) => substitute_sigils(arg, sigils)) };
    case "optional":
      return { ...type, inner: substitute_sigils(type.inner, sigils) };
    case "ref":
      return { ...type, inner: substitute_sigils(type.inner, sigils) };
    case "raw":
    case "unique":
    case "shared":
    case "weak":
      return { ...type, inner: substitute_sigils(type.inner, sigils) };
    case "array":
      return { ...type, element: substitute_sigils(type.element, sigils) };
    case "tuple":
      return { ...type, items: type.items.map((item) => substitute_sigils(item, sigils)) };
    case "function":
      return {
        ...type,
        params: type.params.map((param) => substitute_sigils(param, sigils)),
        result: substitute_sigils(type.result, sigils),
      };
    case "range":
      return { ...type, element: substitute_sigils(type.element, sigils) };
    case "primitive":
    case "void":
    case "any":
    case "none":
    case "nullptr":
      return type;
  }
}

// La expresión final del cuerpo, para que el checker pueda anotar su tipo
// (por ejemplo, un literal de tupla que debe emitirse como `std::pair`).
function last_expression(body: Block): ExprNode | undefined {
  const last = body.statements[body.statements.length - 1];
  return last !== undefined && last.kind === "expr_stmt" ? last.expr : undefined;
}

function check_method(ctx: CheckContext, method: MethodDecl, self_type: PenguType): void {
  const previous_self = ctx.self_type;
  const previous_mutable = ctx.self_mutable;
  const previous_return = ctx.current_return;
  const previous_unsafe = ctx.unsafe_depth;
  const previous_async = ctx.async_depth;

  ctx.self_type = self_type;
  ctx.self_mutable = method.mutable;
  ctx.current_return = method.result === undefined
    ? undefined
    : resolve_type_node(method.result, ctx.module.env, ctx.sink);
  if (method.is_unsafe) ctx.unsafe_depth += 1;
  if (method.is_async) ctx.async_depth += 1;

  try {
    const body = with_fresh_scope(ctx, () => {
      check_params(ctx, method.params, method.body.span);
      return infer_block(ctx, method.body);
    });
    if (ctx.current_return !== undefined) {
      annotate_literal(ctx, ctx.current_return, last_expression(method.body));
    }
    if (
      ctx.current_return !== undefined &&
      ctx.current_return.kind !== "void" &&
      !is_any(body) &&
      !type_equals(body, ctx.current_return)
    ) {
      check_initialization(ctx, ctx.current_return, body, method.body.span, `en el retorno de «${method.name}»`, last_expression(method.body));
    }
  } finally {
    ctx.self_type = previous_self;
    ctx.self_mutable = previous_mutable;
    ctx.current_return = previous_return;
    ctx.unsafe_depth = previous_unsafe;
    ctx.async_depth = previous_async;
  }
}

function check_omen(ctx: CheckContext, decl: OmenDecl): void {
  const omen = ctx.module.env.omens.get(decl.name);
  if (omen === undefined) return;
  if (decl.is_flags && decl.variants.length > 64) {
    ctx.sink.add(
      make_error(
        CODES.invalid_omen_variant,
        `un omen de banderas no puede tener más de 64 variantes (${decl.variants.length})`,
        decl.span,
      ),
    );
  }
}

export function with_fresh_scope<T>(ctx: CheckContext, fn: () => T): T {
  const previous = ctx.scope;
  ctx.scope = { parent: previous, vars: new Map() };
  try {
    return fn();
  } finally {
    ctx.scope = previous;
  }
}
