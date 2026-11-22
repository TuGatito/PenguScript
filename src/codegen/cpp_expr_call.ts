// Emisión de llamadas, índices, miembros y literales de contenedor.

import type {
  BinaryNode,
  CallNode,
  CastNode,
  ComprehensionNode,
  ExprNode,
  ForClauseNode,
  MatchNode,
  SwitchNode,
} from "../frontend/ast_expr.ts";
import type { PatternNode } from "../frontend/ast_pattern.ts";
import type { GenContext } from "./cpp_context.ts";
import {
  declare_local,
  fresh_name,
  is_local_declared,
  gc_error,
  line,
  pop_scope,
  push_scope,
  type_of,
} from "./cpp_context.ts";
import { cpp_identifier, cpp_type, cpp_type_node, cpp_value_type, sanitize_namespace } from "./cpp_types.ts";
import {
  is_adapter_type,
  is_map_type,
  is_sequence_container,
  is_set_type,
  is_string_type,
} from "../semantic/builtin_members.ts";
import { omen_methods_of } from "../semantic/module_info.ts";
import { find_echo_method } from "../semantic/type_env.ts";
import type { PenguType } from "../semantic/types.ts";
import { UNKNOWN, is_float, is_numeric, is_string, named, primitive, type_equals } from "../semantic/types.ts";
import { is_conversion_target } from "../semantic/checker_expr.ts";
import { resolve_type_node } from "../semantic/type_env.ts";
import { STRING_TYPES } from "../frontend/ast_type.ts";
import type { TypeNode } from "../frontend/ast_type.ts";
import { emit_block, emit_value_block } from "./cpp_stmt.ts";


import { cpp_string, emit_expr } from "./cpp_expr.ts";

export function emit_index(g: GenContext, object: ExprNode, index: ExprNode): string {
  const object_type = type_of(g, object);
  if (has_user_index(g, object_type)) {
    return `${emit_expr(g, object)}[${emit_expr(g, index)}]`;
  }
  const rendered = `${emit_expr(g, object)}, ${emit_expr(g, index)}`;
  return is_map_type(object_type)
    ? `::pengu::map_at(${rendered})`
    : `::pengu::vec_at(${rendered})`;
}

// ¿La rune declara su propio `operator []`?
export function has_user_index(g: GenContext, type: PenguType): boolean {
  if (type.kind !== "named") return false;
  const rune = g.module.env.runes.get(type.name);
  return rune !== undefined && rune.methods.has("[]");
}

// Argumentos de una llamada variádica: se empaquetan en un vector.
// Con `...` el vector se concatena en tiempo de ejecución.
export function emit_variadic_args(g: GenContext, node: CallNode, element: PenguType | undefined): string {
  const vector = `std::vector<${element === undefined ? "::pengu::Value" : cpp_type(element, g.type_realms)}>`;
  const boxed = element === undefined || element.kind === "any";
  const pieces = node.args.map((arg) => {
    const rendered = emit_expr(g, arg.expr);
    if (arg.spread) return { rendered, spread: true };
    return { rendered: boxed ? `::pengu::value(${rendered})` : rendered, spread: false };
  });
  if (pieces.every((piece) => !piece.spread)) {
    return `${vector}{${pieces.map((piece) => piece.rendered).join(", ")}}`;
  }
  const builder = fresh_name(g, "varargs");
  const parts = pieces.map((piece) =>
    piece.spread
      ? `::pengu::append(${builder}, ${piece.rendered});`
      : `${builder}.push_back(${piece.rendered});`,
  );
  return `([&]() { ${vector} ${builder}; ${parts.join(" ")} return ${builder}; })()`;
}

// ¿La función llamada es un `extern "C"`? Los varargs de C se emiten sin la
// caja de `any`, con los valores tal cual.
function is_extern_callee(g: GenContext, callee: ExprNode): boolean {
  if (callee.kind === "ident") return g.module.functions.get(callee.name)?.is_extern === true;
  if (callee.kind === "path" && callee.segments.length === 2) {
    const [head, tail] = callee.segments;
    if (head === undefined || tail === undefined) return false;
    const imported = g.external_modules.get(head);
    return imported?.functions.get(tail)?.is_extern === true;
  }
  return false;
}

// Los enhechizados de `std/integers` emiten un `min`/`clamp` por cada ancho:
// con literales `int` la sobrecarga de C++ sería ambigua. Convertimos cada
// argumento a su tipo de parámetro para elegir la sobrecarga exacta.
function emit_enchanting_args(
  g: GenContext,
  node: CallNode,
  params: readonly PenguType[],
  variadic: boolean,
): string {
  const fixed = variadic ? params.slice(0, -1) : params;
  return node.args
    .map((arg, index) => {
      const declared = index < fixed.length ? fixed[index] : variadic ? params[params.length - 1] : undefined;
      const rendered = emit_expr(g, arg.expr);
      const param = declared;
      if (param === undefined || param.kind !== "primitive") return rendered;
      if (type_equals(type_of(g, arg.expr), param)) return rendered;
      return `static_cast<${cpp_type(param, g.type_realms)}>(${rendered})`;
    })
    .join(", ");
}

export function emit_call(g: GenContext, node: CallNode): string {
  const callee_type = type_of(g, node.callee);
  const variadic = callee_type.kind === "function" && callee_type.variadic;
  const params = callee_type.kind === "function" ? callee_type.params : [];
  const element = variadic ? params[params.length - 1] : undefined;
  const extern_variadic = variadic && is_extern_callee(g, node.callee);
  const args = extern_variadic
    ? node.args
        .map((arg) => {
          const rendered = emit_expr(g, arg.expr);
          return is_string(type_of(g, arg.expr)) ? `${rendered}.c_str()` : rendered;
        })
        .join(", ")
    : variadic
    ? emit_variadic_args(g, node, element)
    : node.args
        .map((arg, index) => {
          const rendered = emit_expr(g, arg.expr);
          const param = params[index];
          // Pasar un `unique<T>` por valor lo mueve.
          return param?.kind === "unique" && !arg.mutable ? `std::move(${rendered})` : rendered;
        })
        .join(", ");
  const callee = node.callee;
  if (callee.kind === "path" && callee.segments.length === 2) {
    const target_name = callee.segments[0];
    const operation = callee.segments[1];
    if (
      target_name !== undefined &&
      (operation === "try_from" || operation === "from") &&
      is_conversion_target(target_name)
    ) {
      return emit_conversion(g, target_name, operation, node);
    }
  }
  const callee_type_args = callee.kind === "path" ? callee.type_args : undefined;
  const explicit_type_args: readonly TypeNode[] = callee_type_args ?? node.type_args;
  const type_args = explicit_type_args.map((arg: TypeNode) => cpp_type_node(arg, g.module.env, g.type_realms));
  if (callee.kind === "ident") {
    return emit_ident_call(g, callee.name, type_args, args, node);
  }
  if (callee.kind === "path") {
    return emit_path_call(g, callee.segments, type_args, args);
  }
  if (callee.kind === "member") {
    const target = g.member_targets.get(callee);
    const args_text =
      target !== undefined && target.params.length > 0
        ? emit_enchanting_args(g, node, target.params, target.variadic)
        : args;
    return emit_member_call(g, callee.object, callee.name, args_text, callee);
  }
  return `(${emit_expr(g, callee)})(${args})`;
}

// Las primitivas de «float» y «long double» se resuelven contra las
// sobrecargas de <cmath>; el nombre del tipo no participa en el C++.
const FLOAT_REALM_INTRINSICS: Readonly<Record<string, string>> = {
  sqrt: "std::sqrt",
  cbrt: "std::cbrt",
  pow: "std::pow",
  exp: "std::exp",
  ln: "std::log",
  log2: "std::log2",
  log10: "std::log10",
  floor: "std::floor",
  ceil: "std::ceil",
  round: "std::round",
  trunc: "std::trunc",
  hypot: "std::hypot",
  is_finite: "std::isfinite",
  is_infinite: "std::isinf",
  is_nan: "std::isnan",
  is_sign_negative: "std::signbit",
  to_fixed: "::pengu::to_fixed",
  to_scientific: "::pengu::to_scientific",
};

const FLOAT_REALM_FUNCTIONS: Readonly<Record<string, string>> = Object.fromEntries(
  ["float", "long_double"].flatMap((realm) =>
    Object.entries(FLOAT_REALM_INTRINSICS).map(([name, cpp]) => [`${realm}::${name}`, cpp]),
  ),
);

// Límites de los enteros de ancho fijo: `int8_max()` y compañía.
const INTEGER_LIMIT_TYPES: Readonly<Record<string, string>> = {
  int8: "std::int8_t",
  int16: "std::int16_t",
  int32: "std::int32_t",
  int64: "std::int64_t",
  uint8: "std::uint8_t",
  uint16: "std::uint16_t",
  uint32: "std::uint32_t",
  uint64: "std::uint64_t",
  size: "std::size_t",
  ptrdiff: "std::ptrdiff_t",
};

const INTEGER_LIMIT_FUNCTIONS: Readonly<Record<string, string>> = Object.fromEntries(
  Object.entries(INTEGER_LIMIT_TYPES).flatMap(([short, cpp]) => [
    [`integers::${short}_max`, `std::numeric_limits<${cpp}>::max`],
    [`integers::${short}_min`, `std::numeric_limits<${cpp}>::min`],
  ]),
);

// Conversión de caja de caracteres ASCII: devuelven `char` (la versión de
// <cctype> devuelve `int`).
const CHAR_FUNCTIONS: Readonly<Record<string, string>> = {
  "char::to_upper_raw": "::pengu::char_upper",
  "char::to_lower_raw": "::pengu::char_lower",
};

export const BUILTIN_FUNCTIONS: Readonly<Record<string, string>> = {
  ...CHAR_FUNCTIONS,

  ...FLOAT_REALM_FUNCTIONS,
  ...INTEGER_LIMIT_FUNCTIONS,
  "io::read_line": "::pengu::read_line",
  "io::write_values": "::pengu::write_values",
  "io::eprint_values": "::pengu::eprint_values",
  "format::format_values": "::pengu::format_values",
  "format::fixed": "::pengu::to_fixed",
  "format::scientific": "::pengu::to_scientific",
  "format::radix": "::pengu::to_radix",
  "log::log_values": "::pengu::log_values",
  "string::find_raw": "::pengu::find_raw",
  "string::trim_raw": "::pengu::trim_raw",
  "string::to_upper_raw": "::pengu::to_upper_raw",
  "string::to_lower_raw": "::pengu::to_lower_raw",
  "string::split_raw": "::pengu::split_raw",
  "os::args": "::pengu::os_args",
  "debug::println": "::pengu::println",
  "console::println": "::pengu::println",
  "math::sqrt": "std::sqrt",
  "math::abs": "std::abs",
  "math::floor": "std::floor",
  "math::ceil": "std::ceil",
  "math::round": "std::round",
  "math::pow": "std::pow",
  "math::min": "std::min",
  "math::max": "std::max",
  "math::sin": "std::sin",
  "math::cos": "std::cos",
  "math::tan": "std::tan",
  "fs::read_to_string": "::pengu::read_file",
  "fs::write_string": "::pengu::write_file",
  "fs::exists": "::pengu::path_exists",
  "fs::is_dir": "::pengu::path_is_dir",
  "fs::remove": "::pengu::path_remove",
  "fs::create_dir": "::pengu::create_dir",
  "time::now_millis": "::pengu::now_millis",
  "time::now_seconds": "::pengu::now_seconds",
  "time::sleep_millis": "::pengu::sleep_millis",
  "os::get_env": "::pengu::get_env",
  "os::exit": "std::exit",
  "random::int": "::pengu::random_int",
  "random::float": "::pengu::random_float",
  "random::bool": "::pengu::random_bool",
  "assert::that": "::pengu::assert_that",
  "assert::fail": "::pengu::panic",
  "math::clamp": "std::clamp",
  "math::cbrt": "std::cbrt",
  "math::trunc": "std::trunc",
  "math::nearbyint": "std::nearbyint",
  "math::asin": "std::asin",
  "math::acos": "std::acos",
  "math::atan": "std::atan",
  "math::atan2": "std::atan2",
  "math::sinh": "std::sinh",
  "math::cosh": "std::cosh",
  "math::tanh": "std::tanh",
  "math::asinh": "std::asinh",
  "math::acosh": "std::acosh",
  "math::atanh": "std::atanh",
  "math::exp": "std::exp",
  "math::exp2": "std::exp2",
  "math::expm1": "std::expm1",
  "math::ln": "std::log",
  "math::log2": "std::log2",
  "math::log10": "std::log10",
  "math::log1p": "std::log1p",
  "math::hypot": "std::hypot",
  "math::fmod": "std::fmod",
  "math::remainder": "std::remainder",
  "math::fdim": "std::fdim",
  "math::fmax": "std::fmax",
  "math::fmin": "std::fmin",
  "math::copysign": "std::copysign",
  "math::fma": "std::fma",
  "math::signbit": "std::signbit",
  "math::is_finite": "std::isfinite",
  "math::is_infinite": "std::isinf",
  "math::is_nan": "std::isnan",
  "math::infinite": "::pengu::infinite_double",
  "math::not_a_number": "::pengu::nan_double",
  "math::gcd": "std::gcd",
  "math::lcm": "std::lcm",
};

export const BUILTIN_CONSTANTS: Readonly<Record<string, string>> = {
  "math::pi": "std::numbers::pi",
  "math::e": "std::numbers::e",
};

export function emit_ident_call(
  g: GenContext,
  name: string,
  type_args: readonly string[],
  args: string,
  node: CallNode,
): string {
  // Una función `declare` del propio módulo se resuelve contra el
  // runtime (por ejemplo `write_values` dentro de `std/io`).
  const intrinsic = BUILTIN_FUNCTIONS[`${g.module.realm}::${name}`];
  if (intrinsic !== undefined) return `${intrinsic}(${args})`;
  if ((name === "unique" || name === "shared") && type_args.length === 1) {
    const maker = name === "unique" ? "std::make_unique" : "std::make_shared";
    return `${maker}<${type_args[0]}>(${args})`;
  }

  // Puntero crudo: `raw<T>(ref(x))` toma la dirección; `raw<T>(nullptr)`
  // es el puntero nulo.
  if (name === "raw" && type_args.length === 1) {
    const arg = node.args[0];
    if (arg === undefined) return "nullptr";
    const rendered = emit_expr(g, arg.expr);
    return arg.expr.kind === "call" ? `&${rendered}` : rendered;
  }

  if (name === "weak") {
    const arg = node.args[0];
    const arg_type = arg === undefined ? undefined : type_of(g, arg.expr);
    const inner = arg_type?.kind === "shared" ? cpp_type(arg_type.inner, g.type_realms) : "auto";
    return `std::weak_ptr<${inner}>(${args})`;
  }

  if (name === "ref") {
    const first = node.args[0];
    if (first === undefined) return "/* ref */";
    const rendered = emit_expr(g, first.expr);
    // `ref<T>(x)`: upcast explícito de la referencia.
    const target = node.type_args?.[0];
    if (target === undefined) return rendered;
    // La referencia conserva la mutabilidad del origen: un upcast sobre
    // un binding inmutable produce `const Base&`.
    const source = type_of(g, first.expr);
    const constant = source.kind === "ref" && source.mutable ? "" : "const ";
    return `static_cast<${constant}${cpp_type_node(target, g.module.env, g.type_realms)}&>(${rendered})`;
  }
  if (name === "panic") return `::pengu::panic(${args})`;

  // Variantes de omen sin prefijo: `Circle(1.0)` → `Shape{Shape_Circle{1.0}}`.
  for (const [omen_name, omen] of g.module.env.omens) {
    const variant = omen.variants.get(name);
    if (variant === undefined) continue;
    if (variant.payload.length === 0) {
      return `${cpp_identifier(omen_name)}::${cpp_identifier(name)}`;
    }
    const rendered = variant.payload.map((_type, index) => `v${index}`).join(", ");
    return `${cpp_identifier(omen_name)}{${cpp_identifier(omen_name)}_${cpp_identifier(name)}{${args}}}`;
  }

  const rune = g.module.env.runes.get(name);
  if (rune !== undefined) {
    const rendered_name = type_args.length > 0 ? `${name}<${type_args.join(", ")}>` : name;
    if (rune.constructor !== undefined) return `${rendered_name}(${args})`;
    return `${rendered_name}{${args}}`;
  }

  const alias = g.module.env.aliases.get(name);
  if (alias !== undefined) {
    const rendered = type_args.length > 0 ? `${cpp_identifier(name)}<${type_args.join(", ")}>` : cpp_identifier(name);
    return `${rendered}(${args})`;
  }

  const sigils = type_args.length > 0 ? `<${type_args.join(", ")}>` : "";
  const imported_realm = g.selective_realms.get(name);
  if (imported_realm !== undefined && !g.module.functions.has(name) && !g.module.consts.has(name)) {
    return `${sanitize_namespace(imported_realm)}::${cpp_identifier(name)}${sigils}(${args})`;
  }
  return `${cpp_identifier(name)}${sigils}(${args})`;
}

// `alias::simbolo` de un módulo importado se traduce a `realm::simbolo`.
export function emit_path(g: GenContext, segments: readonly string[]): string {
  const constant = BUILTIN_CONSTANTS[segments.join("::")];
  if (constant !== undefined) return constant;

  if (segments[0] === "Ordering" && segments.length === 2) {
    return `::pengu::Ordering::${segments[1]}`;
  }

  const first = segments[0];
  const realm = first !== undefined ? g.external_realms.get(first) : undefined;
  if (realm !== undefined) {
    return [sanitize_namespace(realm), ...segments.slice(1).map(cpp_identifier)].join("::");
  }
  return segments.map(cpp_identifier).join("::");
}

export function emit_path_call(
  g: GenContext,
  segments: readonly string[],
  type_args: readonly string[],
  args: string,
): string {
  const joined = emit_path(g, segments);
  const builtin = BUILTIN_FUNCTIONS[segments.join("::")];
  if (builtin !== undefined) return `${builtin}(${args})`;

  const head = segments[0] ?? "";
  const last = segments[segments.length - 1] ?? "";
  const omen = g.module.env.omens.get(head);
  if (omen !== undefined) {
    if (last === "try_from") return `::pengu::try_from<${head}>(${args})`;
    if (last === "from") return `::pengu::from<${head}>(${args})`;
    const variant = omen.variants.get(last);
    if (variant !== undefined) {
      const sigils = type_args.length > 0 ? `<${type_args.join(", ")}>` : "";
      if (variant.payload.length === 0) return `${head}${sigils}::${last}`;
      return emit_generic_variant(g, head, last, type_args, args);
    }
  }

  const sigils = type_args.length > 0 ? `<${type_args.join(", ")}>` : "";
  return `${joined}${sigils}(${args})`;
}

export function emit_generic_variant(g: GenContext, head: string, variant: string, type_args: readonly string[], args: string): string {
  const sigils = type_args.length > 0 ? `<${type_args.join(", ")}>` : "";
  return `${head}${sigils}{${head}_${variant}${sigils}{${args}}}`;
}

// `int::try_from(x)` se traduce a una comprobación en el runtime: el
// resultado es `std::optional<T>` (`from` lo desenvuelve o aborta).
export function emit_conversion(
  g: GenContext,
  target_name: string,
  operation: "try_from" | "from",
  node: CallNode,
): string {
  const target = cpp_type(primitive(target_name), g.type_realms);
  const arg = node.args[0];
  const source = arg === undefined ? UNKNOWN : type_of(g, arg.expr);
  const value = arg === undefined ? "" : emit_expr(g, arg.expr);
  let conversion: string;
  if (is_string(source)) {
    conversion = `::pengu::try_parse<${target}>(${value})`;
  } else if (is_float(source)) {
    conversion = `::pengu::try_from_double<${target}>(static_cast<double>(${value}))`;
  } else {
    conversion = `::pengu::try_from_int<${target}>(static_cast<long long>(${value}))`;
  }
  if (operation === "from") {
    return `::pengu::or_panic(${conversion}, "no se pudo convertir a ${target_name}")`;
  }
  return conversion;
}

export function emit_member_call(
  g: GenContext,
  object: ExprNode,
  name: string,
  args: string,
  callee?: ExprNode,
): string {
  // `enchanting` sobre un tipo incorporado: el checker anotó la función
  // libre concreta, así que se emite cualificada por su realm.
  const target = callee === undefined ? undefined : g.member_targets.get(callee);
  if (target !== undefined) {
    const rendered_object = emit_expr(g, object);
    const realm = sanitize_namespace(target.realm);
    const separator = args.length > 0 ? ", " : "";
    return `${realm}::${cpp_identifier(target.name)}(${rendered_object}${separator}${args})`;
  }

  const rendered = emit_expr(g, object);
  const object_type = type_of(g, object);
  // Los métodos declarados por el usuario tienen prioridad sobre las
  // tablas de métodos incorporados (por ejemplo `len` en un rune).
  if (object_type.kind === "named") {
    const rune = g.module.env.runes.get(object_type.name);
    if (rune?.methods.has(name) === true) {
      return `${rendered}.${cpp_identifier(name)}(${args})`;
    }
    // Omens: los métodos son funciones libres (`nombre(color)`).
    const omen = g.module.env.omens.get(object_type.name);
    if (omen !== undefined && omen_methods_of(omen)?.has(name) === true) {
      return `${cpp_identifier(name)}(${rendered}${args.length > 0 ? `, ${args}` : ""})`;
    }
  }
  // Un `seal` emite métodos reales dentro del struct.
  if (object_type.kind === "named") {
    const alias = g.module.env.aliases.get(object_type.name);
    if (alias?.seal === true && alias.methods.has(name)) {
      return `${rendered}.${cpp_identifier(name)}(${args})`;
    }
  }
  // Un `echo` es un alias: sus métodos también son funciones libres.
  {
    const echo = find_echo_method(g.module.env, object_type, name);
    if (echo !== undefined) {
      return `${cpp_identifier(name)}(${rendered}${args.length > 0 ? `, ${args}` : ""})`;
    }
  }
  if (object_type.kind === "primitive" && (object_type.name === "float" || object_type.name === "double" || object_type.name === "long double")) {
    switch (name) {
      case "sqrt":
        return `std::sqrt(${rendered})`;
      case "abs":
        return `std::abs(${rendered})`;
      case "is_nan":
        return `std::isnan(${rendered})`;
    }
  }
  switch (name) {
    case "push":
      // `push` en un contenedor secuencial es `push_back`; en stack,
      // queue y priority_queue el nombre real ya es `push`.
      return is_adapter_type(object_type)
        ? `${rendered}.push(${args})`
        : `${rendered}.push_back(${args})`;
    case "pop":
      // `pop()` devuelve el elemento; en stack/queue/priority_queue el
      // `pop()` de C++ devuelve void, así que se lee `top()` antes.
      if (is_adapter_type(object_type)) return `::pengu::adapter_pop(${rendered})`;
      return is_sequence_container(object_type)
        ? `::pengu::pop_back_checked(${rendered})`
        : `${rendered}.pop()`;
    case "pop_front":
      return `::pengu::pop_front_checked(${rendered})`;
    case "push_front":
      return `${rendered}.push_front(${args})`;
    case "insert_at":
      return `::pengu::insert_at(${rendered}, ${args})`;
    case "sum":
      return `::pengu::sum_of(${rendered})`;
    case "product":
      return `::pengu::product_of(${rendered})`;
    case "clear":
      if (is_adapter_type(object_type)) return `::pengu::adapter_clear(${rendered})`;
      return `${rendered}.clear()`;
    case "is_empty":
      return `${rendered}.empty()`;
    case "contains":
      if (is_map_type(object_type) || is_set_type(object_type)) return `${rendered}.contains(${args})`;
      return `::pengu::contains(${rendered}, ${args})`;
    case "is_some":
      return `${rendered}.has_value()`;
    case "is_none":
      return `!${rendered}.has_value()`;
    case "len":
      return `static_cast<std::size_t>(${rendered}.size())`;
    case "has":
      return `::pengu::has(${rendered}, ${args})`;
    case "pop_opt":
      return `::pengu::pop_opt(${rendered})`;
    case "lock":
      if (object_type.kind === "weak") return `::pengu::lock_weak(${rendered})`;
      return `${rendered}.lock(${args})`;
    case "get": {
      if (is_map_type(object_type)) return `::pengu::map_get(${rendered}, ${args})`;
      if (is_sequence_container(object_type)) return `::pengu::get_at(${rendered}, ${args})`;
      return `${rendered}.get(${args})`;
    }
    case "get_unchecked":
      return `::pengu::vec_at(${rendered}, ${args})`;
    case "get_or":
      return `::pengu::map_get_or(${rendered}, ${args})`;
    case "extract":
      return `::pengu::map_extract(${rendered}, ${args})`;
    case "insert":
      if (is_map_type(object_type)) return `::pengu::map_insert(${rendered}, ${args})`;
      if (is_set_type(object_type)) return `::pengu::set_insert(${rendered}, ${args})`;
      if (is_sequence_container(object_type)) {
        return `::pengu::insert_at(${rendered}, ${args})`;
      }
      return `${rendered}.insert(${args})`;
    case "insert_or_assign":
      return `::pengu::map_assign(${rendered}, ${args})`;
    case "remove":
      if (is_map_type(object_type)) return `::pengu::map_extract(${rendered}, ${args})`;
      if (is_set_type(object_type)) return `::pengu::remove_from_set(${rendered}, ${args})`;
      return `::pengu::remove_value(${rendered}, ${args})`;
    case "remove_at":
      return `::pengu::erase_at(${rendered}, ${args})`;
    case "keys":
      return `::pengu::map_keys(${rendered})`;
    case "values":
      return `::pengu::map_values(${rendered})`;
    case "first":
      return `${rendered}.front()`;
    case "last":
      return `${rendered}.back()`;
    case "find":
      if (is_string_type(object_type)) return `::pengu::find_opt(${rendered}, ${args})`;
      return `${rendered}.find(${args})`;
    case "to_uint64":
      return `${rendered}.to_ullong()`;
    case "value":
      return `${rendered}.value()`;
    case "value_or":
      return `${rendered}.value_or(${args})`;
    default:
      return `${rendered}.${cpp_identifier(name)}(${args})`;
  }
}

export function emit_unary(g: GenContext, node: import("../frontend/ast_expr.ts").UnaryNode): string {
  const operand = emit_expr(g, node.operand);
  switch (node.op) {
    case "not":
      return `!(${operand})`;
    case "#":
      return `::pengu::len(${operand})`;
    case "&":
      return `&(${operand})`;
    case "*": {
      // Un `ref<T>` ya es una referencia en C++: no hay que desreferenciarlo.
      const type = type_of(g, node.operand);
      if (type.kind === "ref") return operand;
      return `*(${operand})`;
    }
    default:
      return `${node.op}(${operand})`;
  }
}

export function emit_binary(g: GenContext, node: BinaryNode): string {
  const left = emit_expr(g, node.left);
  const right = emit_expr(g, node.right);
  switch (node.op) {
    case "and":
      return `(${left} && ${right})`;
    case "or":
      return `(${left} || ${right})`;
    case "in":
      return `::pengu::contains(${right}, ${left})`;
    case "<=>": {
      const left_type = type_of(g, node.left);
      if (is_numeric(left_type) || is_string(left_type)) {
        return `::pengu::compare(${left}, ${right})`;
      }
      return `::pengu::Ordering(${left} <=> ${right})`;
    }
    default:
      // Los operadores libres los encuentra C++ por ADL (el argumento
      // es del realm que declara el operador).
      return `(${left} ${node.op} ${right})`;
  }
}

export function emit_cast(g: GenContext, node: CastNode): string {
  const target = cpp_type_node(node.type, g.module.env, g.type_realms);
  const value_type = type_of(g, node.value);
  let value = emit_expr(g, node.value);
  if (value_type.kind === "named" && value_type.name === "variant") {
    return `std::get<${target}>(${value})`;
  }
  const is_seal = value_type.kind === "named" && g.module.env.aliases.get(value_type.name)?.seal === true;
  const is_self_value = g.self_expression === "value" && node.value.kind === "self";
  if (is_seal && !is_self_value) {
    value = `${value}.value`;
  }
  return `static_cast<${target}>(${value})`;
}

export function emit_vector_lit(g: GenContext, node: import("../frontend/ast_expr.ts").VectorLitNode): string {
  const type = type_of(g, node);
  if (type.kind === "array") {
    const prefix = `std::array<${cpp_type(type.element, g.type_realms)}, ${type.size}>`;
    return `${prefix}{${node.items.map((item) => emit_expr(g, item)).join(", ")}}`;
  }
  if (type.kind === "named" && type.args.length === 1) {
    const base = cpp_type(type, g.type_realms);
    return `${base}{${node.items.map((item) => emit_expr(g, item)).join(", ")}}`;
  }
  return `std::vector<auto>{${node.items.map((item) => emit_expr(g, item)).join(", ")}}`;
}

export function emit_map_lit(g: GenContext, node: import("../frontend/ast_expr.ts").MapLitNode): string {
  const type = type_of(g, node);
  const prefix = type.kind === "named" && type.args.length === 2 ? cpp_type(type, g.type_realms) : "std::map<auto, auto>";
  const entries = node.entries
    .map((entry) => `{${emit_expr(g, entry.key)}, ${emit_expr(g, entry.value)}}`)
    .join(", ");
  return `${prefix}{${entries}}`;
}

export function emit_set_lit(g: GenContext, node: import("../frontend/ast_expr.ts").SetLitNode): string {
  const type = type_of(g, node);
  const prefix = type.kind === "named" && type.args.length === 1 ? cpp_type(type, g.type_realms) : "std::set<auto>";
  return `${prefix}{${node.items.map((item) => emit_expr(g, item)).join(", ")}}`;
}

