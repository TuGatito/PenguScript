// Llamadas del emisor JavaScript.
//
// Un `declare` de la stdlib se traduce a su destino en el runtime
// (`builtins_emit_js.ts`); una función de PenguScript se emite en su realm y
// se referencia con import si vive en otro archivo. Los argumentos variádicos
// que llegan a un parámetro `any` se boxean para que la presentación conserve
// el tipo estático (C++ lo resuelve con `Value`).

import type { ArgNode, ExprNode } from "../frontend/ast_expr.ts";
import type { PenguType } from "../semantic/types.ts";
import type { Span } from "../util/span.ts";
import { is_any, is_float, is_numeric, is_string, primitive } from "../semantic/types.ts";
import {
  cross_reference,
  current_unit,
  expression_type,
  is_local_declared,
  local_type,
  resolve_realm,
  js_error,
  runtime_name,
  type_of,
  type JsContext,
} from "./js_context.ts";
import { js_identifier } from "./js_names.ts";
import { is_bigint_type, js_int_normalizer, js_integer_kind } from "./js_types.ts";
import { needs_clone } from "./js_types.ts";
import { emit_expr } from "./js_expr.ts";
import { builtin_js_target } from "./builtins_emit_js.ts";
import { ensure_function, ensure_constant, ensure_type, rune_is_class } from "./js_module.ts";
import { omen_methods_of } from "../semantic/module_info.ts";
import {
  free_method_export,
  operator_method_name,
  rune_method_owner,
} from "./js_type_decl.ts";
import { base_name_of, emit_enchanting_call, is_value_base, object_lvalue } from "./js_enchant.ts";
import { type_node_name } from "../frontend/ast_type.ts";
import { realm_of_type } from "./js_context.ts";

type CallNode = Extract<ExprNode, { kind: "call" }>;

export function emit_call(g: JsContext, node: CallNode, expected?: PenguType): string {
  const callee = node.callee;
  if (callee.kind === "ident") return emit_named_call(g, callee.name, undefined, node, expected);
  if (callee.kind === "path") {
    const segments = callee.segments;
    const realm = segments[0];
    const name = segments[1];
    const variant = emit_variant_call(g, segments, node);
    if (variant !== undefined) return variant;
    if (segments.length === 2 && realm !== undefined && name !== undefined) {
      // `size_t::from(x)` / `int::try_from(x)`: conversión numérica explícita.
      const converted = emit_type_conversion(g, realm, name, node);
      if (converted !== undefined) return converted;
      // `geometry::Vec2(...)`: constructor de un tipo de otro realm.
      if (g.units.has(realm) || resolve_realm(g, realm) !== undefined) {
        const constructed = emit_type_construction(g, name, node, realm);
        if (constructed !== undefined) return constructed;
      }
      return emit_named_call(g, name, realm, node, expected);
    }
    js_error(g, "llamada a una ruta no soportada todavía en JavaScript", node.span);
    return "undefined";
  }
  if (callee.kind === "member") {
    return emit_member_call(g, callee, node);
  }
  return `${emit_expr(g, callee)}(${emit_args(g, undefined, false, node.args)})`;
}

// Llamada a `nombre(…)` o `realm::nombre(…)`.
function emit_named_call(
  g: JsContext,
  name: string,
  realm: string | undefined,
  node: CallNode,
  expected: PenguType | undefined,
): string {
  void expected;
  const current = current_unit(g);
  const imported = realm === undefined ? current.selective_symbols.get(name) : undefined;
  const owner = resolve_realm(g, realm ?? "") ?? imported?.realm ?? (realm === undefined ? current.module.realm : realm);
  const target_name = imported !== undefined && imported.realm === owner ? imported.name : name;
  const unit = g.units.get(owner);
  if (realm === undefined) {
    const ownership = emit_ownership_call(g, target_name, node);
    if (ownership !== undefined) return ownership;
    const constructed = emit_type_construction(g, target_name, node);
    if (constructed !== undefined) return constructed;
  }
  const info = unit?.module.functions.get(target_name);

  if (info !== undefined && (info.is_intrinsic || info.is_extern)) {
    const target = builtin_js_target(g, owner, target_name);
    if (target === undefined) {
      js_error(
        g,
        `el intrínseco «${owner}::${target_name}» todavía no tiene implementación en JavaScript (fase posterior del plan)`,
        node.span,
      );
      return "undefined";
    }
    return `${target}(${emit_args(g, info.params.map((param) => param.type), info.variadic, node.args)})`;
  }

  if (info !== undefined) {
    ensure_function(g, owner, target_name);
    const reference = realm === undefined && is_local_declared(g, name) ? js_identifier(name) : cross_reference(g, owner, target_name);
    const params = info.params.map((param) => param.type);
    return `${reference}(${emit_args(g, params, info.variadic, node.args)})`;
  }

  // Constante que guarda una función (`callback`/primera clase).
  if (unit?.module.consts.has(target_name) === true) {
    ensure_constant(g, owner, target_name);
    const reference = realm === undefined && is_local_declared(g, name) ? js_identifier(name) : cross_reference(g, owner, target_name);
    return `${reference}(${emit_args(g, undefined, false, node.args)})`;
  }

  const language = builtin_js_target(g, owner, target_name);
  if (language !== undefined) return `${language}(${emit_args(g, undefined, false, node.args)})`;

  js_error(g, `no se encontró la función «${name}» al emitir JavaScript`, node.span);
  return "undefined";
}

// `ref`, `unique`, `shared`, `weak` y `raw`: la posesión no existe en runtime,
// así que se borran salvo la celda de `ref` sobre tipos de valor (§2.8).
function emit_ownership_call(g: JsContext, name: string, node: CallNode): string | undefined {
  if (name === "unique" || name === "shared") {
    const type_node = node.type_args?.[0];
    const type_name = type_node === undefined ? undefined : type_node_name(type_node);
    if (type_name === undefined) return undefined;
    return emit_type_construction(g, type_name, node);
  }
  const first = node.args[0];
  if (first === undefined) return undefined;
  const code = emit_expr(g, first.expr);
  if (name === "raw") return code;
  if (name === "weak") {
    runtime_name(g);
    return `new WeakRef(${code})`;
  }
  if (name !== "ref") return undefined;
  // Un `ref` sobre un tipo con identidad (contenedores, runes) ya comparte el
  // objeto; solo los tipos de valor necesitan una celda de escritura.
  if (!is_value_base(type_of(g, first.expr))) return code;
  if (!object_lvalue(first.expr)) return code;
  const runtime = runtime_name(g);
  return `${runtime}.ref(() => ${code}, (_v) => { ${code} = _v; })`;
}

// Tipo del receptor. Dentro de un `enchanting`, `@` es el propio tipo base y
// el checker no siempre anota un tipo concreto para la expresión.
// Un receptor `ref<T>`, `unique<T>`, `shared<T>` o `raw<T>` ve los métodos de
// `T`: el préstamo no cambia el tipo estático de la llamada.
function unwrap_borrow(type: PenguType): PenguType {
  let current = type;
  while (
    current.kind === "ref" ||
    current.kind === "unique" ||
    current.kind === "shared" ||
    current.kind === "raw"
  ) {
    current = current.inner;
  }
  return current;
}

function receiver_type(g: JsContext, object: ExprNode): PenguType {
  const declared = object.kind === "ident" ? local_type(g, object.name) : undefined;
  if (declared !== undefined) return declared;
  const annotated = expression_type(g, object);
  if (object.kind !== "self" || g.enchant_base === undefined) return annotated;
  if (annotated.kind !== "any") return annotated;
  return { kind: "named", name: g.enchant_base, args: [] };
}

// Miembros nativos de `optional<T>` (`is_some`, `value`…), que existen en el
// runtime de C++ y no como `enchanting`.
function emit_optional_member(
  g: JsContext,
  object: string,
  name: string,
  node: CallNode,
): string | undefined {
  const args = node.args.map((arg) => emit_expr(g, arg.expr));
  switch (name) {
    case "is_some":
      return `(${object} !== null)`;
    case "is_none":
      return `(${object} === null)`;
    case "value":
    case "unwrap":
      runtime_name(g);
      return `rt.unwrap(${object})`;
    case "value_or":
      return `(${object} ?? ${args[0] ?? "undefined"})`;
    default:
      return undefined;
  }
}

// Miembros nativos de `string`.
function emit_string_member(
  g: JsContext,
  object: string,
  name: string,
  node: CallNode,
): string | undefined {
  const args = node.args.map((arg) => emit_expr(g, arg.expr));
  const first = args[0] ?? "0";
  const second = args[1] ?? "undefined";
  switch (name) {
    case "len":
      return `${object}.length`;
    case "is_empty":
      return `(${object}.length === 0)`;
    case "substr":
      // `substr(inicio, largo)`: los índices siempre son `number` en JS.
      return `${object}.substring(Number(${first}), Number(${first}) + Number(${second}))`;
    case "contains":
      return `${object}.includes(${first})`;
    case "clear":
      return `(${object} = "")`;
    default:
      return undefined;
  }
}

type ContainerKind = "array" | "map" | "set";

// Familia de un contenedor incorporado, para resolver sus miembros nativos
// (`push`, `insert`, `keys`…) sin pasar por `enchanting` (§4.6).
function container_kind(type: PenguType): ContainerKind | undefined {
  if (type.kind !== "named") return undefined;
  switch (type.name) {
    case "vector":
    case "array":
    case "deque":
    case "list":
    case "forward_list":
    case "stack":
    case "queue":
    case "span":
      return "array";
    case "map":
    case "multimap":
    case "unordered_map":
    case "unordered_multimap":
      return "map";
    case "set":
    case "multiset":
    case "unordered_set":
    case "unordered_multiset":
      return "set";
    default:
      return undefined;
  }
}

function emit_container_member(
  g: JsContext,
  kind: ContainerKind,
  object: string,
  name: string,
  node: CallNode,
): string | undefined {
  const args = node.args.map((arg) => emit_expr(g, arg.expr));
  const first = args[0] ?? "undefined";
  const second = args[1] ?? "undefined";
  if (name === "len") return `${object}.${kind === "array" ? "length" : "size"}`;
  if (name === "is_empty") {
    return kind === "array" ? `${object}.length === 0` : `${object}.size === 0`;
  }
  if (kind === "array") {
    switch (name) {
      case "size":
        return `${object}.length`;
      case "get":
        // `get` de una secuencia devuelve `T?` (como `::pengu::get_at`).
        return `(Number(${first}) < ${object}.length ? ${object}[Number(${first})] : null)`;
      case "get_or":
        return `(Number(${first}) < ${object}.length ? ${object}[Number(${first})] : ${second})`;
      case "push":
        return `${object}.push(${first})`;
      case "pop":
        runtime_name(g);
        return `rt.pop_back_checked(${object})`;
      case "first":
        return `${object}[0]`;
      case "last":
        return `${object}.at(-1)`;
      case "contains":
        return `${object}.includes(${first})`;
      case "index_of":
        return `${object}.indexOf(${first})`;
      case "clear":
        return `(${object}.length = 0)`;
      case "insert_at":
        return `${object}.splice(Number(${first}), 0, ${second})`;
      case "remove_at":
        return `${object}.splice(Number(${first}), 1)[0]`;
      case "sum":
        runtime_name(g);
        return `rt.sum(${object})`;
      case "product":
        runtime_name(g);
        return `rt.product(${object})`;
      default:
        return undefined;
    }
  }
  if (kind === "map") {
    switch (name) {
      case "size":
        return `${object}.size`;
      case "insert":
      case "insert_or_assign":
        return `${object}.set(${first}, ${second})`;
      case "get":
        // `get` devuelve `T?` (como `::pengu::map_get`): ausente → `null`.
        return `(${object}.has(${first}) ? ${object}.get(${first}) : null)`;
      case "get_or":
        return `(${object}.has(${first}) ? ${object}.get(${first}) : ${second})`;
      case "has":
      case "contains":
      case "contains_key":
        return `${object}.has(${first})`;
      case "remove":
        return `${object}.delete(${first})`;
      case "keys":
        return `[...${object}.keys()]`;
      case "values":
        return `[...${object}.values()]`;
      case "clear":
        return `${object}.clear()`;
      default:
        return undefined;
    }
  }
  switch (name) {
    case "insert":
      return `${object}.add(${first})`;
    case "has":
    case "contains":
      return `${object}.has(${first})`;
    case "remove":
      return `${object}.delete(${first})`;
    case "clear":
      return `${object}.clear()`;
    case "to_vector":
      return `[...${object}]`;
    default:
      return undefined;
  }
}

// Argumentos de una llamada, bboxeando los que van a un parámetro `any`.
function emit_args(
  g: JsContext,
  params: readonly PenguType[] | undefined,
  variadic: boolean,
  args: readonly ArgNode[],
): string {
  const last = params?.[params.length - 1];
  return args
    .map((arg, index) => {
      const declared = variadic && index >= (params?.length ?? 0) - 1 ? last : params?.[index];
      const expected = declared ?? type_of(g, arg.expr);
      const code = emit_expr(g, arg.expr, expected);
      const spread = arg.spread ? "..." : "";
      if (expected !== undefined && is_any(expected) && is_numeric(type_of(g, arg.expr))) {
        runtime_name(g);
        return `${spread}rt.box(${code}, "${box_kind(type_of(g, arg.expr))}")`;
      }
      // C++ pasa por valor: el argumento se copia salvo que sea una celda
      // (`ref`) o un tipo con identidad (`unique`/`shared`) (§3).
      if (declared !== undefined && arg.spread !== true && needs_clone(declared) && !is_any(declared)) {
        runtime_name(g);
        return `${spread}rt.clone(${code})`;
      }
      return `${spread}${code}`;
    })
    .join(", ");
}

// Pista de presentación para los valores que cruzan un `any`: solo los
// flotantes se distinguen de los enteros (`%g` frente a dígitos).
function box_kind(type: PenguType): string {
  return is_float(type) ? "float" : "int";
}

// Acceso a una ruta `realm::simbolo` como expresión (sin llamada).
export function emit_path_reference(g: JsContext, segments: readonly string[], span: Span): string {
  const realm = segments[0];
  const name = segments[1];
  if (segments.length === 2 && realm !== undefined && name !== undefined) {
    // `Color::Red` y `Ordering::Less`: variantes de una `omen` unitaria.
    const unit = current_unit(g);
    const omen = unit.module.env.omens.get(realm);
    if (omen !== undefined) {
      const type_name = cross_reference(g, unit.module.realm, realm);
      return `${type_name}.${js_identifier(name)}`;
    }
    if (realm === "Ordering") {
      runtime_name(g);
      return `rt.Ordering.${js_identifier(name)}`;
    }
    const owner = g.units.get(realm);
    const constant = owner?.module.consts.get(name);
    if (constant !== undefined) ensure_constant(g, realm, name);
    const fn = owner?.module.functions.get(name);
    if (fn !== undefined && (fn.is_intrinsic || fn.is_extern)) {
      const target = builtin_js_target(g, realm, name);
      if (target === undefined) {
        js_error(g, `el intrínseco «${realm}::${name}» todavía no tiene implementación en JavaScript`, span);
        return "undefined";
      }
      return target;
    }
    return cross_reference(g, realm, name);
  }
  js_error(g, "ruta no soportada todavía en JavaScript", span);
  return "undefined";
}

// Construcción de un valor de tipo: `Punto(1, 2)` (fábrica), `new Point(...)`
// (clase), `UserId(5)` (`seal`/`echo`, que se borran) y `Shape::Circle(...)`
// (`omen` algebraica).

// `T::from(x)` y `T::try_from(x)`: en JS la conversión es `Number`/`BigInt`
// (o un `null` si `try_from` no puede representar el valor).
function emit_type_conversion(
  g: JsContext,
  realm: string,
  name: string,
  node: CallNode,
): string | undefined {
  if (name !== "from" && name !== "try_from") return undefined;
  const target = PRIMITIVE_TYPE_NAMES.has(realm) ? primitive(realm) : undefined;
  if (target === undefined) return undefined;
  const first = node.args[0];
  if (first === undefined) return undefined;
  const code = emit_expr(g, first.expr);
  const converted = coerce_number(g, code, target);
  if (name === "from") return converted;
  // `try_from` devuelve `T?`: `null` si el valor no es finito.
  return `((_v) => (typeof _v === "number" && Number.isFinite(_v) ? ${coerce_number(g, "_v", target)} : null))(${converted})`;
}

function coerce_number(g: JsContext, code: string, target: PenguType): string {
  if (is_bigint_type(target, g.mode)) return `BigInt(${code})`;
  if (is_float(target)) return `Number(${code})`;
  const kind = js_integer_kind(target);
  if (kind === undefined) return `Number(${code})`;
  return js_int_normalizer(kind)(`Number(${code})`);
}

const PRIMITIVE_TYPE_NAMES: ReadonlySet<string> = new Set([
  "int",
  "long",
  "long long",
  "unsigned int",
  "unsigned long",
  "unsigned long long",
  "short",
  "unsigned short",
  "signed char",
  "unsigned char",
  "char",
  "size_t",
  "ptrdiff_t",
  "intptr_t",
  "uintptr_t",
  "int8_t",
  "int16_t",
  "int32_t",
  "int64_t",
  "uint8_t",
  "uint16_t",
  "uint32_t",
  "uint64_t",
  "float",
  "double",
  "long double",
]);

function emit_type_construction(
  g: JsContext,
  name: string,
  node: CallNode,
  realm?: string,
): string | undefined {
  // `geometry::Vec2(...)`: el constructor vive en el realm del tipo.
  const owner = realm === undefined ? current_unit(g) : (g.units.get(resolve_realm(g, realm) ?? realm) ?? current_unit(g));
  const unit = owner;
  const env = unit.module.env;
  const alias = env.aliases.get(name);
  if (alias !== undefined) {
    // `seal`/`echo`: el valor es el del argumento, sin envoltorio.
    const first = node.args[0];
    return first === undefined ? "undefined" : emit_expr(g, first.expr, alias.target);
  }
  const rune = env.runes.get(name);
  if (rune !== undefined) {
    ensure_type(g, unit.module.realm, name);
    const reference = cross_reference(g, unit.module.realm, name);
    const params = rune.constructor?.params ?? [...rune.fields.values()].map((field) => field.type);
    const args = emit_args(g, params, false, node.args);
    return rune_is_class(g, unit.module.realm, name) ? `new ${reference}(${args})` : `${reference}(${args})`;
  }
  return undefined;
}

// `Shape::Circle(2.0)` → `Shape.Circle(2.0)`; `Color::Red` sin llamada se
// resuelve en `emit_path_reference`.
function emit_variant_call(g: JsContext, segments: readonly string[], node: CallNode): string | undefined {
  if (segments.length !== 2) return undefined;
  const type_name = segments[0];
  const variant = segments[1];
  if (type_name === undefined || variant === undefined) return undefined;
  const unit = current_unit(g);
  const omen = unit.module.env.omens.get(type_name);
  if (omen === undefined) return undefined;
  const info = omen.variants.get(variant);
  if (info === undefined) return undefined;
  const name = cross_reference(g, unit.module.realm, type_name);
  return `${name}.${js_identifier(variant)}(${emit_args(g, info.payload, false, node.args)})`;
}

// Llamada a un método: los métodos de un rune son métodos de su clase; los de
// `enchanting` sobre tipos incorporados son funciones libres (fase P3).
function emit_member_call(
  g: JsContext,
  member: Extract<ExprNode, { kind: "member" }>,
  node: CallNode,
): string {
  const object_type = receiver_type(g, member.object);
  const object = emit_expr(g, member.object);
  const name = js_identifier(member.name);
  void name;
  // Método de un bloque `enchanting`: el checker anotó el realm que lo declara
  // y aquí se resuelve a la función libre correspondiente (§4.1).
  const enchanting_target = current_unit(g).member_targets?.get(member);
  if (enchanting_target !== undefined) {
    const args = emit_args(g, enchanting_target.params, enchanting_target.variadic, node.args);
    const call = emit_enchanting_call(
      g,
      object,
      object_type,
      enchanting_target.realm,
      enchanting_target.name,
      args,
      object_lvalue(member.object),
    );
    if (call !== undefined) return call;
  }
  const named_type = unwrap_borrow(object_type);
  if (named_type.kind === "named") {
    const unit = current_unit(g);
    const flags = unit.module.env.omens.get(named_type.name);
    if (flags !== undefined && flags.is_flags && member.name === "has") {
      runtime_name(g);
      return `((${object} & ${emit_args(g, [flags.underlying ?? object_type], false, node.args)}) !== 0)`;
    }
    // Métodos de un rune: función libre `<Tipo>__<método>` resuelta con el
    // tipo estático del receptor, sin despacho virtual (§2.5).
    const rune_realm = realm_of_type(g, named_type.name) ?? unit.module.realm;
    const owner = rune_method_owner(g, rune_realm, named_type.name, member.name);
    if (owner !== undefined) {
      const info = g.units.get(owner.realm)?.module.env.runes.get(owner.type)?.methods.get(member.name);
      ensure_type(g, owner.realm, owner.type);
      const exported = free_method_export(
        owner.type,
        owner.operator === undefined ? member.name : operator_method_name(owner.operator),
      );
      const target = cross_reference(g, owner.realm, exported);
      const args = emit_args(g, info?.params, info?.variadic ?? false, node.args);
      return `${target}(${object}${args.length === 0 ? "" : `, ${args}`})`;
    }
    // `omen`, `seal` y `echo` no tienen prototipo donde colgar métodos: son
    // funciones libres con el receptor primero (§4.1).
    const omen = unit.module.env.omens.get(named_type.name);
    const omen_method = omen === undefined ? undefined : omen_methods_of(omen)?.get(member.name);
    const alias = unit.module.env.aliases.get(named_type.name);
    const alias_method = alias?.methods.get(member.name);
    const method = omen_method ?? alias_method;
    if (method !== undefined) {
      const realm = realm_of_type(g, named_type.name) ?? unit.module.realm;
      if (ensure_type(g, realm, named_type.name)) {
        const target = cross_reference(g, realm, free_method_export(named_type.name, member.name));
        const args = emit_args(g, method.params, method.variadic, node.args);
        return `${target}(${object}${args.length === 0 ? "" : `, ${args}`})`;
      }
    }
  }
  const base = base_name_of(object_type);
  if (base === "optional") {
    const optional = emit_optional_member(g, object, member.name, node);
    if (optional !== undefined) return optional;
  }
  if (base === "string" || (is_string(object_type) && member.name !== "bytes_raw")) {
    const text = emit_string_member(g, object, member.name, node);
    if (text !== undefined) return text;
  }
  const container = container_kind(object_type);
  if (container !== undefined) {
    const builtin = emit_container_member(g, container, object, member.name, node);
    if (builtin !== undefined) return builtin;
  }
  if (is_string(object_type) && member.name === "bytes_raw") {
    runtime_name(g);
    return `rt.bytes_raw(${object})`;
  }
  js_error(
    g,
    `la llamada al método «${member.name}» todavía no se emite a JavaScript (fase P2/P3)`,
    node.span,
  );
  return "undefined";
}
