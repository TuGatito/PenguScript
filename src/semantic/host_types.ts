// Tipos del host: objetos de JavaScript declarados con `host`.
//
// Un `host` no tiene código: describe la forma de un objeto que ya existe en
// el runtime de JavaScript (el DOM, `localStorage`, un `canvas`…). El checker
// los trata como runes sin cuerpo: propiedades, métodos, constructores e
// índice; el emisor JS los usa tal cual (sin `js::` y sin clonar) y el
// backend C++ los rechaza con E0518.
//
// Los tipos de los miembros se guardan como `TypeNode` y se resuelven en cada
// uso, con el entorno del módulo que usa el tipo. Así un `std/js/dom` puede
// escribir `js::String` aunque el alias lo declare `std/js/types`, que se
// invoca en otro archivo (la recolección de un módulo va antes que la de sus
// importados).

import type { DeclNode, HostMember } from "../frontend/ast_decl.ts";
import type { ParamNode } from "../frontend/ast_param.ts";
import type { TypeNode } from "../frontend/ast_type.ts";
import type { Span } from "../util/span.ts";
import { CODES } from "../diagnostics/codes.ts";
import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import type { CheckContext } from "./checker_context.ts";
import type { PenguType } from "./types.ts";
import { any_type, optional as optional_type, substitute_generics, type_display } from "./types.ts";
import type { TypeEnv } from "./type_env.ts";
import { resolve_type_node } from "./type_env.ts";

// Prefijo de los tipos del host. Los `std/js/*` declaran `js::Algo`.
export const HOST_PREFIX = "js::";

export function is_host_name(name: string): boolean {
  return name.startsWith(HOST_PREFIX);
}

export interface HostPropertyInfo {
  readonly kind: "property";
  readonly name: string;
  readonly type: TypeNode;
  readonly mutable: boolean;
  readonly optional: boolean;
  readonly span: Span;
}

export interface HostMethodInfo {
  readonly kind: "method";
  readonly name: string;
  readonly sigils: readonly string[];
  readonly params: readonly ParamNode[];
  readonly result: TypeNode | undefined;
  readonly is_static: boolean;
  readonly optional: boolean;
  readonly span: Span;
}

export interface HostIndexInfo {
  readonly kind: "index";
  readonly key: TypeNode;
  readonly value: TypeNode;
  readonly mutable: boolean;
  readonly span: Span;
}

export type HostMemberInfo = HostPropertyInfo | HostMethodInfo | HostIndexInfo;

export interface HostConstructorInfo {
  readonly params: readonly ParamNode[];
  readonly span: Span;
}

export interface HostTypeInfo {
  readonly kind: "host";
  readonly name: string;
  readonly sigils: readonly string[];
  readonly parent: string | undefined;
  readonly members: ReadonlyMap<string, HostMemberInfo>;
  readonly index: HostIndexInfo | undefined;
  readonly constructors: readonly HostConstructorInfo[];
  readonly span: Span;
}

export interface HostNamespaceInfo {
  readonly kind: "host_namespace";
  readonly name: string;
  readonly members: ReadonlyMap<string, HostMemberInfo>;
  readonly span: Span;
}

export interface HostGlobalInfo {
  readonly kind: "host_global";
  readonly name: string;
  readonly type: TypeNode | undefined;
  readonly span: Span;
}

// --- Búsqueda -------------------------------------------------------------

// Los tipos host viven en el `TypeEnv` del módulo que los declara; el checker
// los busca también en los módulos invocados (un programa usa `document` sin
// declararlo).
export function find_host_type(env: TypeEnv, name: string): HostTypeInfo | undefined {
  return env.host_types.get(name);
}

export function host_type_of(ctx: CheckContext, type: PenguType): HostTypeInfo | undefined {
  if (type.kind !== "named") return undefined;
  const local = ctx.module.env.host_types.get(type.name);
  if (local !== undefined) return local;
  const modules = ctx.external?.modules;
  if (modules === undefined) return undefined;
  for (const module of modules.values()) {
    const found = module.env.host_types.get(type.name);
    if (found !== undefined) return found;
  }
  return undefined;
}

export function host_global_of(ctx: CheckContext, name: string): HostGlobalInfo | undefined {
  const local = ctx.module.env.host_globals.get(name);
  if (local !== undefined) return local;
  const modules = ctx.external?.modules;
  if (modules === undefined) return undefined;
  for (const module of modules.values()) {
    const found = module.env.host_globals.get(name);
    if (found !== undefined) return found;
  }
  return undefined;
}

export function host_namespace_of(ctx: CheckContext, name: string): HostNamespaceInfo | undefined {
  const local = ctx.module.env.host_namespaces.get(name);
  if (local !== undefined) return local;
  const modules = ctx.external?.modules;
  if (modules === undefined) return undefined;
  for (const module of modules.values()) {
    const found = module.env.host_namespaces.get(name);
    if (found !== undefined) return found;
  }
  return undefined;
}

// Miembro de un tipo host, subiendo por la cadena `heir`.
export function host_member_of(
  ctx: CheckContext,
  type: HostTypeInfo,
  name: string,
): HostMemberInfo | undefined {
  let current: HostTypeInfo | undefined = type;
  const seen = new Set<string>();
  while (current !== undefined && !seen.has(current.name)) {
    const member = current.members.get(name);
    if (member !== undefined) return member;
    seen.add(current.name);
    current =
      current.parent === undefined
        ? undefined
        : host_type_of(ctx, { kind: "named", name: current.parent, args: [] });
  }
  return undefined;
}

// Índice del tipo host, subiendo por la cadena `heir`.
export function host_index_of(ctx: CheckContext, type: HostTypeInfo): HostIndexInfo | undefined {
  let current: HostTypeInfo | undefined = type;
  const seen = new Set<string>();
  while (current !== undefined && !seen.has(current.name)) {
    if (current.index !== undefined) return current.index;
    seen.add(current.name);
    current =
      current.parent === undefined
        ? undefined
        : host_type_of(ctx, { kind: "named", name: current.parent, args: [] });
  }
  return undefined;
}

// --- Resolución de tipos de miembros --------------------------------------

function param_type(env: TypeEnv, sink: DiagnosticSink, param: ParamNode): PenguType {
  return param.type === undefined ? any_type("parámetro del host") : resolve_type_node(param.type, env, sink);
}

function result_type(env: TypeEnv, sink: DiagnosticSink, node: TypeNode | undefined): PenguType {
  return node === undefined ? any_type("resultado del host") : resolve_type_node(node, env, sink);
}

// Un miembro puede escribir los sigilos del tipo (`value: T`). Al resolverlo
// fuera del bloque `host` hay que dar esos sigilos al entorno: con los
// argumentos si el tipo está instanciado (`js::Box<int>`) y con `any` si no.
export function host_scope(
  env: TypeEnv,
  host: HostTypeInfo | undefined,
  args: readonly PenguType[] = [],
): TypeEnv {
  if (host === undefined || host.sigils.length === 0) return env;
  const sigils = new Map<string, PenguType>();
  host.sigils.forEach((sigil, index) => {
    sigils.set(sigil, args[index] ?? any_type("genérico del host"));
  });
  return { ...env, sigils };
}

export function host_property_type(env: TypeEnv, sink: DiagnosticSink, info: HostPropertyInfo): PenguType {
  const resolved = resolve_type_node(info.type, env, sink);
  return info.optional ? optional_type(resolved) : resolved;
}

export function host_global_type(env: TypeEnv, sink: DiagnosticSink, info: HostGlobalInfo): PenguType {
  return info.type === undefined ? any_type("global del host") : resolve_type_node(info.type, env, sink);
}

export function host_index_types(
  env: TypeEnv,
  sink: DiagnosticSink,
  info: HostIndexInfo,
): { key: PenguType; value: PenguType } {
  return {
    key: resolve_type_node(info.key, env, sink),
    value: resolve_type_node(info.value, env, sink),
  };
}

// Tipo de una llamada a un método host. Los genéricos se sustituyen por
// `any`: el catálogo `std/js/*` evita sigilos y el bindgen los resolverá en T2.
export function host_method_type(env: TypeEnv, sink: DiagnosticSink, info: HostMethodInfo): PenguType {
  const params = info.params.map((param) => param_type(env, sink, param));
  const result = result_type(env, sink, info.result);
  const required = required_count(info.params);
  const variadic = info.params.some((param) => param.variadic);
  const final_result = info.optional ? optional_type(result) : result;
  if (info.sigils.length === 0) {
    return { kind: "function", params, result: final_result, variadic, required };
  }
  const mapping = new Map<string, PenguType>();
  for (const sigil of info.sigils) mapping.set(sigil, any_type("genérico del host"));
  return {
    kind: "function",
    params: params.map((param) => substitute_generics(param, mapping)),
    result: substitute_generics(final_result, mapping),
    variadic,
    required,
  };
}

// Tipo del miembro cuando se usa como valor (propiedad, método o índice).
export function host_member_value_type(
  env: TypeEnv,
  sink: DiagnosticSink,
  info: HostMemberInfo,
): PenguType {
  if (info.kind === "property") return host_property_type(env, sink, info);
  if (info.kind === "method") return host_method_type(env, sink, info);
  return resolve_type_node(info.value, env, sink);
}

// Tipo de la llamada al constructor: la primera firma declarada.
export function host_constructor_call_type(
  env: TypeEnv,
  sink: DiagnosticSink,
  host: HostTypeInfo,
): PenguType | undefined {
  env = host_scope(env, host);
  const constructor = host.constructors[0];
  if (constructor === undefined) return undefined;
  return {
    kind: "function",
    params: constructor.params.map((param) => param_type(env, sink, param)),
    result: host_constructor_result(host),
    variadic: false,
    required: required_count(constructor.params),
  };
}

// Tipo del valor que produce un constructor host.
export function host_constructor_result(type: HostTypeInfo): PenguType {
  return { kind: "named", name: type.name, args: type.sigils.map(() => any_type("genérico del host")) };
}

// --- Atajos para el checker (entorno y sumidero del módulo en curso) -------

export function host_property_type_of(
  ctx: CheckContext,
  info: HostPropertyInfo,
  host?: HostTypeInfo,
  args: readonly PenguType[] = [],
): PenguType {
  return host_property_type(host_scope(ctx.module.env, host, args), ctx.sink, info);
}

export function host_method_type_of(
  ctx: CheckContext,
  info: HostMethodInfo,
  host?: HostTypeInfo,
  args: readonly PenguType[] = [],
): PenguType {
  return host_method_type(host_scope(ctx.module.env, host, args), ctx.sink, info);
}

export function host_index_value_type(
  ctx: CheckContext,
  info: HostIndexInfo,
  host?: HostTypeInfo,
  args: readonly PenguType[] = [],
): PenguType {
  return host_index_types(host_scope(ctx.module.env, host, args), ctx.sink, info).value;
}

export function host_member_type_of(
  ctx: CheckContext,
  info: HostMemberInfo,
  host?: HostTypeInfo,
  args: readonly PenguType[] = [],
): PenguType {
  return host_member_value_type(host_scope(ctx.module.env, host, args), ctx.sink, info);
}

export function host_global_type_of(ctx: CheckContext, info: HostGlobalInfo): PenguType {
  return host_global_type(ctx.module.env, ctx.sink, info);
}

export function host_constructor_type_of(
  ctx: CheckContext,
  host: HostTypeInfo,
  args: readonly PenguType[] = [],
): PenguType | undefined {
  return host_constructor_call_type(host_scope(ctx.module.env, host, args), ctx.sink, host);
}

// --- Registro -------------------------------------------------------------

function error(sink: DiagnosticSink, code: string, message: string, span: Span, ...notes: string[]): void {
  sink.add(make_error(code, message, span, ...notes));
}

export function register_host_decl(decl: DeclNode, env: TypeEnv, sink: DiagnosticSink): void {
  switch (decl.kind) {
    case "host_decl":
      register_host_type(decl, env, sink);
      return;
    case "host_global_decl": {
      if (env.host_globals.has(decl.name)) {
        error(sink, CODES.duplicate_symbol, `«${decl.name}» ya está declarado como global del host`, decl.name_span);
        return;
      }
      env.host_globals.set(decl.name, {
        kind: "host_global",
        name: decl.name,
        type: decl.type,
        span: decl.name_span,
      });
      return;
    }
    case "host_namespace_decl": {
      if (env.host_namespaces.has(decl.name)) {
        error(sink, CODES.duplicate_symbol, `«${decl.name}» ya está declarado como namespace del host`, decl.name_span);
        return;
      }
      const members = new Map<string, HostMemberInfo>();
      for (const member of decl.members) {
        if (member.kind === "host_constructor") {
          error(sink, CODES.invalid_declaration, "un namespace del host no tiene constructor", member.span);
          continue;
        }
        if (member.kind === "host_index") {
          error(sink, CODES.invalid_declaration, "un namespace del host no tiene índice", member.span);
          continue;
        }
        const info = member_info(member);
        if (info !== undefined) members.set(info.name, info);
      }
      env.host_namespaces.set(decl.name, {
        kind: "host_namespace",
        name: decl.name,
        members,
        span: decl.name_span,
      });
      return;
    }
    default:
      return;
  }
}

function register_host_type(decl: DeclNode, env: TypeEnv, sink: DiagnosticSink): void {
  if (decl.kind !== "host_decl") return;
  if (env.host_types.has(decl.name)) {
    error(sink, CODES.duplicate_symbol, `«${decl.name}» ya está declarado como tipo del host`, decl.name_span);
    return;
  }
  if (!is_host_name(decl.name)) {
    error(
      sink,
      CODES.invalid_declaration,
      `el tipo del host «${decl.name}» debe empezar por «${HOST_PREFIX}»`,
      decl.name_span,
      "declara el objeto del host como «host js::Nombre»",
    );
    return;
  }

  const members = new Map<string, HostMemberInfo>();
  const constructors: HostConstructorInfo[] = [];
  let index: HostIndexInfo | undefined;

  for (const member of decl.members) {
    if (member.kind === "host_constructor") {
      constructors.push({ params: member.params, span: member.span });
      continue;
    }
    if (member.kind === "host_index") {
      index = {
        kind: "index",
        key: member.key_type,
        value: member.value,
        mutable: member.mutable,
        span: member.span,
      };
      continue;
    }
    const info = member_info(member);
    if (info !== undefined) members.set(info.name, info);
  }

  env.host_types.set(decl.name, {
    kind: "host",
    name: decl.name,
    sigils: decl.sigils,
    parent: decl.parent === undefined ? undefined : parent_name(decl.parent),
    members,
    index,
    constructors,
    span: decl.name_span,
  });
}

function parent_name(node: { kind: string; name?: string }): string | undefined {
  return node.kind === "named_type" ? node.name : undefined;
}

function required_count(params: readonly ParamNode[]): number {
  let required = 0;
  for (const param of params) {
    // Un parámetro con tipo `T?` es opcional aunque no declare valor por
    // defecto (`constructor(url: string, base: string?)`).
    const optional = param.type?.kind === "optional_type";
    if (param.default_value !== undefined || param.variadic || optional) break;
    required += 1;
  }
  return required;
}

function member_info(member: HostMember): HostPropertyInfo | HostMethodInfo | undefined {
  if (member.kind === "host_property") {
    return {
      kind: "property",
      name: member.name,
      type: member.type,
      mutable: member.mutable,
      optional: member.optional,
      span: member.span,
    };
  }
  if (member.kind === "host_method") {
    return {
      kind: "method",
      name: member.name,
      sigils: member.sigils,
      params: member.params,
      result: member.result,
      is_static: member.is_static,
      optional: member.optional,
      span: member.span,
    };
  }
  return undefined;
}

// ¿Este tipo puede recibir escritura? (`document.title = …`)
export function host_member_writable(info: HostMemberInfo): boolean {
  return (info.kind === "property" || info.kind === "index") && info.mutable;
}

export function host_display(name: string): string {
  return name;
}

// Un módulo invocado puede declarar `host`; el que lo invoca los necesita
// visibles sin cualificar (`document`, `js::Document`).
export function merge_host_types(env: TypeEnv, modules: Iterable<{ readonly env: TypeEnv }>): void {
  for (const module of modules) {
    for (const [name, info] of module.env.host_types) {
      if (!env.host_types.has(name)) env.host_types.set(name, info);
    }
    for (const [name, info] of module.env.host_globals) {
      if (!env.host_globals.has(name)) env.host_globals.set(name, info);
    }
    for (const [name, info] of module.env.host_namespaces) {
      if (!env.host_namespaces.has(name)) env.host_namespaces.set(name, info);
    }
    // Los alias del host (`echo js::String = string`) también cruzan: son la
    // forma en que un literal se pasa a la API del navegador sin conversión.
    for (const [name, info] of module.env.aliases) {
      if (!name.startsWith(HOST_PREFIX) || env.aliases.has(name)) continue;
      env.aliases.set(name, info);
    }
  }
}

// Mensaje único para cuando se usa un tipo host sin haberlo declarado.
export function unknown_host_type_message(name: string): string {
  return `no existe el tipo del host «${name}»: ningún módulo invocado lo declara`;
}

export function host_type_message(type: PenguType): string {
  return type_display(type);
}

// ¿`ancestor` está en la cadena `heir` de `descendant`? Los objetos del host
// son del navegador: `HTMLElement` encaja donde se espera `js::Node`.
export function host_is_ancestor(
  env: TypeEnv | undefined,
  ancestor: string,
  descendant: string,
): boolean {
  if (ancestor === descendant) return true;
  if (env === undefined) return false;
  let current = env.host_types.get(descendant);
  const seen = new Set<string>();
  while (current !== undefined && current.parent !== undefined && current.parent !== "") {
    const parent = current.parent;
    if (parent === ancestor) return true;
    if (seen.has(parent)) return false;
    seen.add(parent);
    current = env.host_types.get(parent);
  }
  return false;
}
