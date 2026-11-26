// Acceso a miembros, rutas `realm::simbolo` e índices implícitos.


// cascadas de errores secundarios.

import type {
  ArgNode,
  Block,
  CallNode,
  ExprNode,
  ForClauseNode,
  LambdaNode,
  MatchArm,
  PatternNode,
  SwitchArm,
} from "../frontend/ast.ts";
import { CODES } from "../diagnostics/codes.ts";
import { error as make_error, warning as make_warning } from "../diagnostics/diagnostic.ts";
import type { Span } from "../util/span.ts";
import type { ParamNode } from "../frontend/ast_param.ts";
import { suggest_name } from "../util/suggest.ts";
import { declare, lookup } from "./scopes.ts";
import {
  host_constructor_type_of,
  host_member_of,
  host_member_type_of,
  host_method_type_of,
  host_namespace_of,
  host_type_of,
} from "./host_types.ts";
import type { CheckContext } from "./checker_context.ts";
import { with_scope } from "./checker_context.ts";
import { symbol_type_of } from "./external.ts";
import {
  add_borrow,
  ensure_not_iterating,
  can_assign,
  check_initialization,
  ensure_not_borrowed,
  expect_bool,
  is_generic_type,
  report_type_mismatch,
} from "./checker_context.ts";
import {
  BOOL,
  CHAR,
  FLOAT,
  INT,
  NONE,
  NULLPTR,
  SIZE_T,
  STRING,
  UNKNOWN,
  VOID,
  any_type,
  float_rank,
  function_type,
  integer_shape,
  is_any,
  is_float,
  is_integer,
  is_name,
  is_numeric,
  is_string,
  join_types,
  named,
  numeric_join,
  primitive,
  optional,
  ref_to,
  tuple_type,
  type_display,
  type_equals,
  types_equal,
} from "./types.ts";
import type { PenguType } from "./types.ts";
import { STRING_TYPES, is_primitive_type } from "../frontend/ast_type.ts";
import type { TypeNode } from "../frontend/ast_type.ts";
import type { OmenVariantInfo } from "./type_env.ts";
import { function_type_of, omen_methods_of } from "./module_info.ts";
import { find_free_operator } from "./operators.ts";
import { substitute_generics } from "./types.ts";
import type { FunctionInfo } from "./module_info.ts";
import { builtin_function, is_builtin_module } from "./builtin_modules.ts";
import { shared_type, unique_type, weak_type } from "./types.ts";
import { find_echo_method, find_rune_field, find_rune_method, is_heir_of, resolve_type_node } from "./type_env.ts";
import { rune_lookup, rune_method_of } from "./rune_lookup.ts";
import type { TypeEnv } from "./type_env.ts";
import type { OmenInfo } from "./type_env.ts";
import {
  builtin_index_result,
  is_map_type,
  is_sequence_container,
  is_set_type,
  is_string_type,
  map_key_value,
  member_of_builtin,
  sequence_element,
} from "./builtin_members.ts";
import { check_statement } from "./checker_stmt.ts";
import { infer_block, infer_expr, report_error, known_names, with_new_scope, with_loop, loop_result_type } from "./checker_expr.ts";
import { resolve_enchanted_member } from "./checker_enchants.ts";
import { infer_primitive_conversion, is_conversion_target, is_display, ORDERING_VARIANTS } from "./checker_ops.ts";


export function infer_path(
  ctx: CheckContext,
  segments: readonly string[],
  span: Span,
  type_args: readonly TypeNode[] = [],
): PenguType {
  const first = segments[0];
  const second = segments[1];
  if (first === undefined) return UNKNOWN;

  // Tipos del host: `js::URL(...)` construye y `js::URL::createObjectURL`
  // llama a un miembro estático.
  if (first === "js" && second !== undefined) {
    const host = host_type_of(ctx, { kind: "named", name: `js::${second}`, args: [] });
    if (host !== undefined) {
      const args = type_args.map((node) => resolve_type_node(node, ctx.module.env, ctx.sink));
      if (host.sigils.length !== args.length) {
        report_error(
          ctx,
          CODES.wrong_arity,
          `«${host.name}» necesita ${host.sigils.length} argumento(s) de tipo`,
          span,
        );
        return UNKNOWN;
      }
      const third = segments[2];
      if (third !== undefined) {
        const member = host_member_of(ctx, host, third);
        if (member === undefined) {
          report_error(ctx, CODES.unknown_field, `«${host.name}» no tiene el miembro «${third}»`, span);
          return UNKNOWN;
        }
        return host_member_type_of(ctx, member, host, args);
      }
      const call = host_constructor_type_of(ctx, host, args);
      if (call === undefined) {
        report_error(
          ctx,
          CODES.not_callable,
          `«${host.name}» no declara constructor`,
          span,
          ["el bloque «host» puede declarar «constructor(...)» o usar una función que lo construya"],
        );
        return UNKNOWN;
      }
      return call;
    }
  }

  // Namespaces del host: `Math::sin(x)`, `JSON::parse(texto)`.
  const namespace = host_namespace_of(ctx, first);
  if (namespace !== undefined && second !== undefined) {
    const member = namespace.members.get(second);
    if (member === undefined) {
      report_error(ctx, CODES.unknown_identifier, `el namespace «${first}» no tiene «${second}»`, span);
      return UNKNOWN;
    }
    return host_member_type_of(ctx, member);
  }

  // Módulos importados con `invoke "ruta"`: `alias::simbolo`.
  const imported_module = ctx.external?.modules.get(first);
  if (imported_module !== undefined && second !== undefined) {
    const type = symbol_type_of(imported_module, second);
    if (type !== undefined) return type;
    report_error(ctx, CODES.unknown_identifier, `el módulo «${first}» no exporta «${second}»`, span);
    return UNKNOWN;
  }

  if (is_builtin_module(first)) {
    if (second !== undefined) {
      const signature = builtin_function(first, second);
      if (signature !== undefined) {
        return function_type(signature.params, signature.result, signature.variadic ?? false);
      }
      report_error(ctx, CODES.unknown_identifier, `el módulo «${first}» no exporta «${second}»`, span);
      return UNKNOWN;
    }
    return any_type(`módulo std::${first}`);
  }

  if (first === "Ordering" && second !== undefined) {
    if (ORDERING_VARIANTS.has(second)) return named("Ordering");
    report_error(
      ctx,
      CODES.unknown_identifier,
      `«Ordering» no tiene la variante «${second}» (usa Less, Equal o Greater)`,
      span,
    );
    return UNKNOWN;
  }

  if (
    segments.length === 2 &&
    second !== undefined &&
    (second === "try_from" || second === "from") &&
    is_conversion_target(first)
  ) {
    return any_type(`conversión ${first}::${second}`);
  }

  const instance = type_args.length > 0
    ? named(first, type_args.map((arg) => resolve_type_node(arg, ctx.module.env, ctx.sink)))
    : named(first);

  if (segments.length === 2 && second !== undefined) {
    const omen = ctx.module.env.omens.get(first);
    if (omen !== undefined) {
      if (second === "try_from") return function_type([INT], optional(instance));
      if (second === "from") return function_type([INT], instance);
      const variant = omen.variants.get(second);
      if (variant !== undefined) {
        if (variant.payload.length > 0) {
          return function_type(variant.payload, instance);
        }
        return instance;
      }
      report_error(ctx, CODES.unknown_identifier, `el omen «${first}» no tiene la variante «${second}»`, span);
      return UNKNOWN;
    }

    const rune = rune_lookup(ctx, first)?.rune;
    if (rune !== undefined) {
      const method = rune.methods.get(second);
      if (method !== undefined) {
        return function_type(
          method.params,
          method.result,
          method.variadic,
          method.required,
        );
      }
      return any_type(`método asociado ${first}::${second}`);
    }
  }

  // `realm::symbol` dentro del mismo módulo.
  if (first === ctx.module.realm) {
    const rest = segments.slice(1).join("::");
    const constant = ctx.module.consts.get(rest);
    if (constant !== undefined) return constant.type;
    const fn = ctx.module.functions.get(rest);
    if (fn !== undefined) return function_type_of(fn);
    return any_type(`símbolo ${rest}`);
  }

  const imported = ctx.module.imports.get(first);
  if (imported !== undefined) {
    return any_type(`símbolo importado ${segments.join("::")}`);
  }

  if (ctx.module.env.omens.has(first) || rune_lookup(ctx, first) !== undefined) {
    return named(first);
  }

  const suggestion = suggest_name(segments.join("::"), known_names(ctx));
  const hint = suggestion === undefined ? "" : `; ¿quisiste decir «${suggestion}»?`;
  report_error(ctx, CODES.unknown_identifier, `no se reconoce «${segments.join("::")}»${hint}`, span);
  return UNKNOWN;
}

// Resultado de un operador declarado en `enchanting` para una rune.
export function rune_operator_method(
  ctx: CheckContext,
  type: PenguType,
  operator: string,
): PenguType | undefined {
  if (type.kind !== "named") return undefined;
  return rune_method_of(ctx, type.name, operator)?.result;
}

export function infer_member(
  ctx: CheckContext,
  object: PenguType,
  name: string,
  span: Span,
  node?: Extract<ExprNode, { kind: "member" }>,
): PenguType {
  if (is_any(object)) return object;

  if (object.kind === "ref" || object.kind === "unique" || object.kind === "shared" || object.kind === "raw") {
    return infer_member(ctx, object.inner, name, span, node);
  }

  if (object.kind === "weak") {
    if (name === "lock") return function_type([], optional(shared_type(object.inner)));
  }

  if (object.kind === "named") {
    // Objetos del host (`js::Document`): propiedades y métodos sin cuerpo.
    const host = host_type_of(ctx, object);
    if (host !== undefined) {
      const member = host_member_of(ctx, host, name);
      if (member === undefined) {
        report_error(
          ctx,
          CODES.unknown_field,
          `«${object.name}» no tiene el miembro «${name}»`,
          span,
          ["consulta los miembros que declara el bloque «host» de std/js"],
        );
        return UNKNOWN;
      }
      return host_member_type_of(ctx, member, host, object.args);
    }
    const lookup = rune_lookup(ctx, object.name);
    if (lookup !== undefined) {
      const field = find_rune_field(lookup.env, lookup.rune, name);
      if (field !== undefined) {
        // Leer un campo de una unión depende del miembro activo: es
        // responsabilidad del programador, así que pide `unsafe`.
        if (lookup.rune.meld === true && ctx.unsafe_depth === 0) {
          report_error(
            ctx,
            CODES.meld_access_unsafe,
            `leer «${field.name}» de la unión «${object.name}» requiere «unsafe»`,
            span,
          );
        }
        return field.type;
      }
      const method = find_rune_method(lookup.env, lookup.rune, name);
      if (method !== undefined) {
        return function_type(
          method.params,
          method.result,
          method.variadic,
          method.required,
        );
      }
      report_error(ctx, CODES.unknown_field, `el rune «${object.name}» no tiene «${name}»`, span);
      return UNKNOWN;
    }
    const alias = ctx.module.env.aliases.get(object.name);
    if (alias !== undefined) {
      const method = alias.methods.get(name);
      if (method !== undefined) {
        return function_type(
          method.params,
          method.result,
          method.variadic,
          method.required,
        );
      }
    }
    const omen = ctx.module.env.omens.get(object.name);
    if (omen !== undefined) {
      const method = omen_methods_of(omen)?.get(name);
      if (method !== undefined) {
        return function_type(
          method.params,
          method.result,
          method.variadic,
          method.required,
        );
      }
      if (omen.is_flags && name === "has") {
        return function_type([named(object.name)], BOOL);
      }
    }
    // Omen importado de otro módulo: sus enhechizamientos se emiten como
    // funciones libres en el realm que lo declara, así que el checker deja
    // anotado el destino para el codegen.
    if (omen === undefined) {
      const external = external_omen_of(ctx, object.name);
      const method = external === undefined ? undefined : omen_methods_of(external.omen)?.get(name);
      if (external !== undefined && method !== undefined) {
        if (node !== undefined) {
          ctx.member_targets?.set(node, {
            realm: external.realm,
            name,
            params: method.params,
            variadic: method.variadic,
          });
        }
        return function_type(
          method.params,
          method.result,
          method.variadic,
          method.required,
        );
      }
    }
  }

  const echo_method = find_echo_method(ctx.module.env, object, name);
  if (echo_method !== undefined) {
    return function_type(
      echo_method.params,
      echo_method.result,
      echo_method.variadic,
      echo_method.params.length - (echo_method.variadic ? 1 : 0),
    );
  }

  // `enchanting` sobre tipos incorporados: manda sobre la tabla nativa.
  if (node !== undefined) {
    const enchanted = resolve_enchanted_member(ctx, node, object);
    if (enchanted !== undefined) return enchanted;
  }

  const builtin = member_of_builtin(object, name);
  if (builtin !== undefined) return builtin;

  report_error(
    ctx,
    CODES.unknown_field,
    `el tipo «${type_display(object)}» no tiene el miembro «${name}»`,
    span,
  );
  return UNKNOWN;
}


// Capacidades estructurales de los sigilos (`needs Ord, Copy`).
// Solo se comprueban sobre tipos primitivos y contenedores conocidos;
// para runes y omens se confía en el compilador de C++.

// Busca un omen declarado en un módulo importado. Devuelve también su
// realm, donde viven sus métodos libres.
function external_omen_of(
  ctx: CheckContext,
  name: string,
): { omen: OmenInfo; realm: string } | undefined {
  for (const module of ctx.external?.modules.values() ?? []) {
    const omen = module.env.omens.get(name);
    if (omen !== undefined) return { omen, realm: module.realm };
  }
  return undefined;
}
