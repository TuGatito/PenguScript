// Punto de entrada del checker.
//
// Recoge el módulo y comprueba cada declaración: constantes,
// funciones, runes, omens y bloques `enchanting`.

import type { ExprNode, Program } from "../frontend/ast.ts";
import type {
  ConstDecl,
  DeclNode,
  EnchantingDecl,
  FunctionDecl,
  MethodDecl,
  OmenDecl,
  RuneDecl,
} from "../frontend/ast_decl.ts";
import type { ParamNode } from "../frontend/ast_param.ts";
import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { CODES } from "../diagnostics/codes.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import type { CheckContext } from "./checker_context.ts";
import { check_initialization, make_context, report_type_mismatch } from "./checker_context.ts";
import { collect_module } from "./module_info.ts";
import type { ModuleInfo } from "./module_info.ts";
import { declare } from "./scopes.ts";
import { infer_block, param_binding_type } from "./checker_expr.ts";
import { resolve_type_node } from "./type_env.ts";
import { any_type, generic_type, is_any, named, type_equals } from "./types.ts";
import type { PenguType } from "./types.ts";
import type { ExternalImports } from "./external.ts";

export interface CheckOptions {
  // Si se pasa, el checker anota el tipo de cada expresión. Lo usa el
  // generador de C++ para deducir tipos de lambdas y literales.
  readonly types?: Map<ExprNode, PenguType>;
  readonly external?: ExternalImports;
}

export function check_program(
  file: string,
  program: Program,
  sink: DiagnosticSink,
  options: CheckOptions = {},
): ModuleInfo {
  const module = collect_module(file, program, sink);
  const ctx = make_context(file, module, sink);
  ctx.types = options.types;
  ctx.external = options.external;

  for (const decl of program.decls) {
    check_decl(ctx, decl);
  }

  return module;
}

function check_decl(ctx: CheckContext, decl: DeclNode): void {
  switch (decl.kind) {
    case "const_decl":
      check_const(ctx, decl);
      break;
    case "function_decl":
      check_function(ctx, decl);
      break;
    case "rune_decl":
      check_rune(ctx, decl);
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
      break;
    case "extern_decl":
      check_extern(ctx, decl);
      break;
  }
}

function check_extern(ctx: CheckContext, decl: Extract<DeclNode, { kind: "extern_decl" }>): void {
  for (const declared of decl.declares) {
    for (const param of declared.params) {
      if (param.type !== undefined) resolve_type_node(param.type, ctx.module.env, ctx.sink);
    }
    if (declared.result !== undefined) resolve_type_node(declared.result, ctx.module.env, ctx.sink);
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

  const previous_return = ctx.current_return;
  const previous_unsafe = ctx.unsafe_depth;
  ctx.current_return = is_any(info.result) ? undefined : info.result;
  if (decl.is_unsafe) ctx.unsafe_depth += 1;

  with_sigils(ctx, decl.sigils, () => {
  try {
    const body = with_fresh_scope(ctx, () => {
      check_params(ctx, decl.params);
      return infer_block(ctx, decl.body);
    });
    if (ctx.current_return !== undefined) {
      if (ctx.current_return.kind === "void") {
        // Un cuerpo void puede terminar en cualquier expresión sin valor.
      } else if (!type_equals(body, ctx.current_return) && !is_any(body)) {
        check_initialization(ctx, ctx.current_return, body, decl.body.span, "en el retorno de la función");
      }
    } else if (!is_any(info.result) && !type_equals(body, info.result)) {
      check_initialization(ctx, info.result, body, decl.body.span, "en el retorno de la función");
    }
  } finally {
    ctx.current_return = previous_return;
    ctx.unsafe_depth = previous_unsafe;
  }
  });
}

function check_params(ctx: CheckContext, params: readonly ParamNode[]): void {
  for (const param of params) {
    const type = param.type === undefined
      ? any_type(`parámetro ${param.name}`)
      : resolve_type_node(param.type, ctx.module.env, ctx.sink);
    declare(ctx.scope, param.name, param_binding_type(param, type), {
      mutable: param.mutable,
      kind: "param",
      span: param.span,
    });
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
        check_params(ctx, constructor.params);
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
  const self_type = named(target);

  const target_sigils = ctx.module.env.runes.get(target)?.sigils ?? [];
  with_sigils(ctx, target_sigils, () => {
    for (const method of decl.methods) {
      with_sigils(ctx, method.sigils, () => check_method(ctx, method, self_type));
    }
  });
}

function check_method(ctx: CheckContext, method: MethodDecl, self_type: ReturnType<typeof named>): void {
  const previous_self = ctx.self_type;
  const previous_mutable = ctx.self_mutable;
  const previous_return = ctx.current_return;
  const previous_unsafe = ctx.unsafe_depth;

  ctx.self_type = self_type;
  ctx.self_mutable = method.mutable;
  ctx.current_return = method.result === undefined
    ? undefined
    : resolve_type_node(method.result, ctx.module.env, ctx.sink);
  if (method.is_unsafe) ctx.unsafe_depth += 1;

  try {
    const body = with_fresh_scope(ctx, () => {
      check_params(ctx, method.params);
      return infer_block(ctx, method.body);
    });
    if (
      ctx.current_return !== undefined &&
      ctx.current_return.kind !== "void" &&
      !is_any(body) &&
      !type_equals(body, ctx.current_return)
    ) {
      check_initialization(ctx, ctx.current_return, body, method.body.span, `en el retorno de «${method.name}»`);
    }
  } finally {
    ctx.self_type = previous_self;
    ctx.self_mutable = previous_mutable;
    ctx.current_return = previous_return;
    ctx.unsafe_depth = previous_unsafe;
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
