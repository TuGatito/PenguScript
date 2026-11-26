// Emisión de los enlaces al host en JavaScript.
//
// Un `host` no genera código: sus miembros ya existen en el runtime del
// navegador. El emisor solo tiene que escribir el nombre real
// (`js::Document` → `document`, `js::Array<T>` → `T[]`) y no clonar ni
// convertir nada en la frontera.

import type { CallNode, ExprNode } from "../frontend/ast_expr.ts";
import type { TypeEnv } from "../semantic/type_env.ts";
import type {
  HostGlobalInfo,
  HostMemberInfo,
  HostNamespaceInfo,
  HostTypeInfo,
} from "../semantic/host_types.ts";
import { host_member_value_type } from "../semantic/host_types.ts";
import { make_sink } from "../diagnostics/sink.ts";
import type { PenguType } from "../semantic/types.ts";
import { js_type } from "./js_types.ts";
import { host_js_name } from "./js_types.ts";
import type { JsContext } from "./js_context.ts";
import { js_error } from "./js_context.ts";
import { emit_expr } from "./js_expr.ts";
import { expression_type } from "./js_context.ts";

export interface HostIndex {
  readonly types: ReadonlyMap<string, HostTypeInfo>;
  readonly globals: ReadonlyMap<string, HostGlobalInfo>;
  readonly namespaces: ReadonlyMap<string, HostNamespaceInfo>;
}

export const EMPTY_HOST_INDEX: HostIndex = {
  types: new Map(),
  globals: new Map(),
  namespaces: new Map(),
};

// Los `host` los declara cualquier módulo del grafo; el índice los junta.
export function collect_host_index(envs: readonly TypeEnv[]): HostIndex {
  const types = new Map<string, HostTypeInfo>();
  const globals = new Map<string, HostGlobalInfo>();
  const namespaces = new Map<string, HostNamespaceInfo>();
  for (const env of envs) {
    for (const [name, info] of env.host_types) if (!types.has(name)) types.set(name, info);
    for (const [name, info] of env.host_globals) if (!globals.has(name)) globals.set(name, info);
    for (const [name, info] of env.host_namespaces) if (!namespaces.has(name)) namespaces.set(name, info);
  }
  return { types, globals, namespaces };
}

export function host_type_info(g: JsContext, type: PenguType): HostTypeInfo | undefined {
  if (type.kind !== "named") return undefined;
  return g.host_index.types.get(type.name);
}

export function host_global_info(g: JsContext, name: string): HostGlobalInfo | undefined {
  return g.host_index.globals.get(name);
}

export function host_namespace_info(g: JsContext, name: string): HostNamespaceInfo | undefined {
  return g.host_index.namespaces.get(name);
}

// Miembro del host subiendo por `heir`.
export function host_member_info(
  g: JsContext,
  type: HostTypeInfo,
  name: string,
): HostMemberInfo | undefined {
  let current: HostTypeInfo | undefined = type;
  const seen = new Set<string>();
  while (current !== undefined && !seen.has(current.name)) {
    const member = current.members.get(name);
    if (member !== undefined) return member;
    seen.add(current.name);
    current = current.parent === undefined ? undefined : g.host_index.types.get(current.parent);
  }
  return undefined;
}

// `document`: el nombre del global tal cual.
export function emit_host_global(g: JsContext, name: string): string | undefined {
  const info = host_global_info(g, name);
  if (info === undefined) return undefined;
  return host_js_name(name);
}

// Argumentos de una llamada al host: sin `rt.box` ni clones (son objetos
// del navegador y valores que ya viajan como están).
function host_args(g: JsContext, node: CallNode): string {
  return node.args
    .map((arg) => `${arg.spread ? "..." : ""}${emit_expr(g, arg.expr)}`)
    .join(", ");
}

// `canvas.getContext("2d")`: emite `canvas.getContext("2d")`.
export function emit_host_member_call(
  g: JsContext,
  object: ExprNode,
  object_type: PenguType,
  name: string,
  node: CallNode,
): string | undefined {
  const info = host_type_info(g, object_type);
  if (info === undefined) return undefined;
  const member = host_member_info(g, info, name);
  if (member === undefined) {
    js_error(g, `«${info.name}» no tiene el miembro «${name}»`, node.span);
    return "undefined";
  }
  if (member.kind !== "method") {
    js_error(g, `«${name}» es una propiedad, no un método`, node.span);
    return "undefined";
  }
  const receiver = emit_expr(g, object);
  return `${receiver}.${host_js_name(member.name)}(${host_args(g, node)})`;
}

// `js::URL::createObjectURL(blob)`: miembro estático del tipo host.
export function emit_host_static_call(
  g: JsContext,
  type: HostTypeInfo,
  name: string,
  node: CallNode,
): string | undefined {
  const member = host_member_info(g, type, name);
  if (member === undefined) {
    js_error(g, `«${type.name}» no tiene el miembro estático «${name}»`, node.span);
    return "undefined";
  }
  if (member.kind !== "method") {
    js_error(g, `«${name}» es una propiedad, no un método`, node.span);
    return "undefined";
  }
  return `${host_js_name(type.name)}.${host_js_name(member.name)}(${host_args(g, node)})`;
}

// `js::URL(texto)`: `new URL(texto)`.
export function emit_host_construction(
  g: JsContext,
  type: HostTypeInfo,
  node: CallNode,
): string {
  return `new ${host_js_name(type.name)}(${host_args(g, node)})`;
}

// `Math::sin(x)` y `JSON::stringify(v)`: namespace del host.
export function emit_host_namespace_call(
  g: JsContext,
  namespace: HostNamespaceInfo,
  name: string,
  node: CallNode,
): string | undefined {
  const member = namespace.members.get(name);
  if (member === undefined) {
    js_error(g, `el namespace «${namespace.name}» no tiene «${name}»`, node.span);
    return "undefined";
  }
  if (member.kind !== "method") {
    js_error(g, `«${name}» es una propiedad del namespace, no una función`, node.span);
    return "undefined";
  }
  return `${host_js_name(namespace.name)}.${host_js_name(name)}(${host_args(g, node)})`;
}

// Entorno del módulo en curso y un sumidero mudo: aquí solo se resuelven
// anotaciones, no se diagnostica (el checker ya lo hizo).
function host_env(g: JsContext): { env: TypeEnv; sink: ReturnType<typeof make_sink> } {
  const unit = g.units.get(g.file.realm) ?? g.unit;
  return { env: unit.module.env, sink: make_sink({ max: 0 }) };
}

// Tipo de la llamada a un método del host (para JSDoc y coerciones).
export function host_member_result(g: JsContext, type: HostTypeInfo, name: string): PenguType | undefined {
  const member = host_member_info(g, type, name);
  if (member === undefined) return undefined;
  const { env, sink } = host_env(g);
  return host_member_value_type(env, sink, member);
}

// ¿Este nodo es una llamada al host? Lo usa `js_expr_call` para delegar.
export function host_call_target(
  g: JsContext,
  node: CallNode,
): { readonly kind: "type"; readonly type: HostTypeInfo } | { readonly kind: "namespace"; readonly namespace: HostNamespaceInfo } | undefined {
  const callee = node.callee;
  if (callee.kind === "path") {
    const [first, second, third] = callee.segments;
    if (first === undefined) return undefined;
    if (first === "js" && second !== undefined) {
      const type = g.host_index.types.get(`js::${second}`);
      if (type === undefined) return undefined;
      if (third !== undefined) return { kind: "type", type };
      return { kind: "type", type };
    }
    const namespace = g.host_index.namespaces.get(first);
    if (namespace !== undefined && second !== undefined) return { kind: "namespace", namespace };
  }
  return undefined;
}

// Nombre del tipo del host para anotaciones (`js::Array<js::Element>` → `Element[]`).
export function host_type_annotation(type: PenguType): string {
  return js_type(type);
}

export function host_type_name(type: HostTypeInfo): string {
  return host_js_name(type.name);
}

export function expression_host_type(g: JsContext, node: ExprNode): HostTypeInfo | undefined {
  return host_type_info(g, expression_type(g, node));
}
