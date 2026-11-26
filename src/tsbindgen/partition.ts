// Partición de un `.d.ts` en lo que PenguScript sabe representar.
//
// El lector entrega un árbol de declaraciones de TypeScript; aquí se decide
// qué es un tipo `host`, qué es un global, qué es un namespace del host, qué
// se convierte en `declare` (funciones del navegador) y qué se omite con un
// motivo. La salida es un módulo de PenguScript todavía sin formato: el emisor
// (`emit_dts.ts`) se encarga del texto.

import type { DtsInterface, DtsModule, DtsNode } from "./dts_ast.ts";
import type { DtsMember, DtsParam, DtsType } from "./dts_type.ts";
import type { DtsClass, DtsEnum, DtsFunction, DtsNamespace, DtsTypeAlias, DtsVar } from "./dts_ast.ts";
import { map_param, map_result, map_type, param_name } from "./ts_type.ts";
import { is_keyword } from "../frontend/token.ts";

export interface PenguMember {
  readonly kind: "property" | "method" | "index" | "constructor";
  readonly name: string;
  readonly sigils: readonly string[];
  // Para `property`/`index`: el tipo. Para `method`: `(params) -> resultado`.
  // Para `constructor`: `(params)`.
  readonly text: string;
  readonly mutable: boolean;
  readonly optional: boolean;
  readonly static: boolean;
  readonly doc?: string;
}

export interface PenguHostType {
  readonly name: string;
  readonly sigils: readonly string[];
  readonly parent?: string;
  readonly members: readonly PenguMember[];
  readonly doc?: string;
}

export interface PenguGlobal {
  readonly name: string;
  readonly type?: string;
  readonly doc?: string;
}

export interface PenguDeclare {
  readonly name: string;
  readonly text: string;
  readonly doc?: string;
}

export interface PenguNamespace {
  readonly name: string;
  readonly members: readonly PenguMember[];
}

export interface PenguAlias {
  readonly name: string;
  readonly target: string;
  readonly seal: boolean;
}

export interface PenguEnum {
  readonly name: string;
  readonly members: readonly { name: string; value?: string }[];
}

export interface Skipped {
  readonly name: string;
  readonly reason: string;
}

export interface PenguBindingModule {
  readonly source: string;
  readonly host_types: readonly PenguHostType[];
  readonly namespaces: readonly PenguNamespace[];
  readonly globals: readonly PenguGlobal[];
  readonly declares: readonly PenguDeclare[];
  readonly aliases: readonly PenguAlias[];
  readonly enums: readonly PenguEnum[];
  readonly skipped: readonly Skipped[];
  /** Nombres cuyas sobrecargas se han colapsado en la primera firma. */
  readonly collapsed: readonly string[];
  readonly members: number;
}

const MAX_HERITAGE_DEPTH = 4;

// PenguScript solo puede escribir como miembro o global lo que es un
// identificador ASCII (`annotation-xml`, `0` y `$1` existen en el DOM pero no
// se pueden nombrar). Las palabras clave valen como nombre de miembro, pero no
// como global.
const IDENT = /^[A-Za-z_][A-Za-z0-9_]*$/;

function writable_member(name: string): boolean {
  return IDENT.test(name);
}

function writable_global(name: string): boolean {
  return IDENT.test(name) && !is_keyword(name);
}

export function partition_module(module: DtsModule): PenguBindingModule {
  const by_name = new Map<string, DtsNode>();
  for (const node of module.nodes) {
    if (node.kind !== "namespace" && node.kind !== "global") by_name.set(node.name, node);
  }
  const namespaces: PenguNamespace[] = [];
  const globals: PenguGlobal[] = [];
  const declares: PenguDeclare[] = [];
  const aliases: PenguAlias[] = [];
  const enums: PenguEnum[] = [];
  const skipped: Skipped[] = [];
  const collapsed: string[] = [];
  const declare_names = new Set<string>();
  const host_types: PenguHostType[] = [];
  let members = 0;

  // Primero los tipos: los alias `echo js::X = js::Y` se resuelven en cuanto
  // se registra el módulo, así que `js::Y` tiene que estar declarado aquí
  // mismo (los tipos de otros módulos solo valen dentro de bloques `host`,
  // que sí se resuelven de forma perezosa).
  for (const node of module.nodes) {
    if (node.kind !== "interface" && node.kind !== "class") continue;
    const host = host_type_of(node, by_name, skipped);
    if (host === undefined) {
      skipped.push({ name: node.name, reason: "interfaz sin miembros representables" });
      continue;
    }
    host_types.push(host);
    members += host.members.length;
  }
  const local_hosts = new Set(host_types.map((host) => host.name));

  // Después todo lo demás, que ya puede referirse a los tipos de arriba.
  for (const node of module.nodes) {
    switch (node.kind) {
      case "interface":
      case "class":
        break;
      case "alias":
        alias_of(node, aliases, skipped, local_hosts);
        break;
      case "var":
        if (globals.some((global) => global.name === node.name)) {
          collapsed.push(node.name);
          break;
        }
        global_of(node, globals, skipped);
        break;
      case "function":
        // `lib.dom.d.ts` declara las sobrecargas como funciones sueltas: se
        // queda la primera firma y las demás cuentan como colapsadas.
        if (declare_names.has(node.name)) {
          collapsed.push(node.name);
          break;
        }
        declare_names.add(node.name);
        declare_of(node, declares, skipped, local_hosts);
        break;
      case "namespace":
        namespaces.push(namespace_of(node, skipped, local_hosts));
        break;
      case "enum":
        enums.push(enum_of(node));
        break;
      case "global":
        break;
    }
  }

  return {
    source: module.file,
    host_types,
    namespaces,
    globals,
    declares,
    aliases,
    enums,
    skipped,
    collapsed,
    members,
  };
}

function host_type_of(
  node: DtsInterface | DtsClass,
  by_name: ReadonlyMap<string, DtsNode>,
  skipped: Skipped[],
): PenguHostType | undefined {
  const params = new Set(node.type_params);
  const members = members_of(node.members, node.name, skipped, params);
  const inherited = inherited_members(node.heritage, by_name, skipped, 0, params);
  const parent = node.heritage[0]?.name;
  const all = merge_members(members, inherited);
  if (all.length === 0) return undefined;
  return {
    name: node.name,
    sigils: node.type_params.length > 0 ? [...node.type_params] : [],
    parent: parent === undefined ? undefined : bare_name(parent),
    members: all,
    ...(node.doc === undefined ? {} : { doc: node.doc }),
  };
}

function bare_name(name: string): string {
  return name.includes(".") ? name.slice(name.lastIndexOf(".") + 1) : name;
}

// Las interfaces del DOM heredan de varias (`HTMLElement extends Element,
// ElementCSSInlineStyle…`): la primera es la cadena `heir` y el resto se
// aplanan como miembros propios, que es lo que PenguScript puede comprobar.
function inherited_members(
  heritage: readonly { name: string; args: readonly DtsType[] }[],
  by_name: ReadonlyMap<string, DtsNode>,
  skipped: Skipped[],
  depth: number,
  params: ReadonlySet<string>,
): PenguMember[] {
  if (depth > MAX_HERITAGE_DEPTH) return [];
  const result: PenguMember[] = [];
  for (const base of heritage.slice(1)) {
    const node = by_name.get(bare_name(base.name));
    if (node === undefined || (node.kind !== "interface" && node.kind !== "class")) continue;
    result.push(...members_of(node.members, node.name, skipped, params));
    result.push(...inherited_members(node.heritage, by_name, skipped, depth + 1, params));
  }
  return result;
}

function merge_members(own: readonly PenguMember[], inherited: readonly PenguMember[]): PenguMember[] {
  const seen = new Set<string>();
  const result: PenguMember[] = [];
  for (const member of [...own, ...inherited]) {
    const key = `${member.kind}:${member.name}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(member);
  }
  return result;
}

function members_of(
  members: readonly DtsMember[],
  owner: string,
  skipped: Skipped[],
  scope: ReadonlySet<string> = new Set(),
): PenguMember[] {
  const result: PenguMember[] = [];
  for (const member of members) {
    const named = member.kind === "property" || member.kind === "method";
    if (named && !writable_member(member.name)) {
      skipped.push({ name: `${owner}.${member.name}`, reason: "nombre no escribible en PenguScript" });
      continue;
    }
    switch (member.kind) {
      case "property": {
        // Una propiedad cuyo tipo es una función se emite como método: en
        // PenguScript se llama igual (`obj.f()`), pero así no se le puede
        // asignar un valor, que es lo que el navegador no permite.
        if (member.type.kind === "function") {
          const fn = member.type;
          const params_text = signature_params(fn.params, owner, member.name, skipped, scope);
          result.push({
            kind: "method",
            name: member.name,
            sigils: [],
            text: `(${params_text}) -> ${map_result(fn.result, { params: scope }).text}`,
            mutable: false,
            optional: member.optional,
            static: false,
            ...(member.doc === undefined ? {} : { doc: member.doc }),
          });
          break;
        }
        const mapped = map_type(member.type, { name: member.name, params: scope });
        if (!mapped.exact) skipped.push({ name: `${owner}.${member.name}`, reason: mapped.reason ?? "tipo" });
        result.push({
          kind: "property",
          name: member.name,
          sigils: [],
          text: mapped.text,
          mutable: !member.readonly,
          optional: member.optional,
          static: false,
          ...(member.doc === undefined ? {} : { doc: member.doc }),
        });
        break;
      }
      case "method": {
        const inner = new Set([...scope, ...member.type_params]);
        const params_text = signature_params(member.params, owner, member.name, skipped, inner);
        const result_type = map_result(member.result, { params: inner });
        result.push({
          kind: "method",
          name: member.name,
          sigils: member.type_params,
          text: `(${params_text}) -> ${result_type.text}`,
          mutable: false,
          optional: member.optional,
          static: false,
          ...(member.doc === undefined ? {} : { doc: member.doc }),
        });
        break;
      }
      case "index": {
        // Los índices de JavaScript son enteros: `number` no debe traducirse
        // a `double` aunque el `.d.ts` lo declare así.
        const key = map_type(member.key, { name: "index", params: scope });
        const key_text = key.text === "double" ? "int" : key.text;
        const value = map_type(member.value, { name: "value", params: scope });
        result.push({
          kind: "index",
          name: "indice",
          sigils: [],
          text: `[indice: ${key_text}]: ${value.text}`,
          mutable: !member.readonly,
          optional: false,
          static: false,
        });
        break;
      }
      case "construct": {
        const params_text = signature_params(member.params, owner, "constructor", skipped, scope);
        result.push({
          kind: "constructor",
          name: "constructor",
          sigils: [],
          text: `constructor(${params_text})`,
          mutable: false,
          optional: false,
          static: false,
        });
        break;
      }
      case "call":
        skipped.push({ name: `${owner}.()`, reason: "interfaz invocable" });
        break;
    }
  }
  return result;
}

function signature_params(
  params: readonly DtsParam[],
  owner: string,
  member: string,
  skipped: Skipped[],
  scope: ReadonlySet<string>,
): string {
  return params
    .map((param) => {
      const mapped = map_param(param, { params: scope });
      if (!mapped.exact) {
        skipped.push({ name: `${owner}.${member}.${param.name}`, reason: mapped.reason ?? "tipo" });
      }
      return `${param.rest ? "..." : ""}${param_name(param.name)}: ${mapped.text}`;
    })
    .join(", ");
}

function alias_of(
  node: DtsTypeAlias,
  aliases: PenguAlias[],
  skipped: Skipped[],
  local_hosts: ReadonlySet<string>,
): void {
  const mapped = map_type(node.type);
  if (!mapped.exact) {
    skipped.push({ name: node.name, reason: mapped.reason ?? "tipo" });
    return;
  }
  const referenced = /^js::([A-Za-z0-9_]+)/.exec(mapped.text);
  if (referenced !== null && !local_hosts.has(referenced[1] ?? "")) {
    skipped.push({ name: node.name, reason: "alias a un tipo declarado en otro módulo" });
    return;
  }
  // Solo se emiten los alias que se pueden escribir como `echo`.
  const simple = /^(string|double|bool|int|void|int64_t|size_t|js::[A-Za-z0-9_]+(?:<[^>]*>)?)$/.test(mapped.text);
  if (!simple) {
    skipped.push({ name: node.name, reason: "alias estructural" });
    return;
  }
  aliases.push({ name: node.name, target: mapped.text, seal: false });
}

function global_of(node: DtsVar, globals: PenguGlobal[], skipped: Skipped[]): void {
  if (!writable_global(node.name)) {
    skipped.push({ name: node.name, reason: "nombre de global no escribible en PenguScript" });
    return;
  }
  const mapped = map_type(node.type);
  // Un global cuyo tipo no se puede escribir se omite; uno con una
  // aproximación útil (`js::Any` de una unión) se declara igual, porque el
  // programa lo va a usar (los objetos globales del navegador).
  if (!mapped.exact && mapped.text === "js::Any") {
    skipped.push({ name: node.name, reason: mapped.reason ?? "tipo" });
    return;
  }
  globals.push({
    name: node.name,
    type: mapped.text,
    ...(node.doc === undefined ? {} : { doc: node.doc }),
  });
}

// En un `declare` la firma se resuelve al registrar el módulo, así que un tipo
// del host de otro módulo no existe todavía: se degrada a `any` para que el
// archivo generado se pueda cargar solo.
function eager_text(text: string, local_hosts: ReadonlySet<string>): string {
  return text.replace(/js::([A-Za-z0-9_]+)/g, (whole, name: string) => {
    if (name === "Any") return "any";
    if (name === "String") return "string";
    if (name === "Number") return "double";
    if (name === "Boolean") return "bool";
    return local_hosts.has(name) ? whole : "any";
  });
}

function declare_of(
  node: DtsFunction,
  declares: PenguDeclare[],
  skipped: Skipped[],
  local_hosts: ReadonlySet<string>,
): void {
  const params = node.params
    .map((param) => {
      const mapped = map_param(param);
      if (!mapped.exact) skipped.push({ name: `${node.name}.${param.name}`, reason: mapped.reason ?? "tipo" });
      return `${param.rest ? "..." : ""}${param_name(param.name)}: ${eager_text(mapped.text, local_hosts)}`;
    })
    .join(", ");
  const result = eager_text(map_result(node.result).text, local_hosts);
  declares.push({ name: node.name, text: `(${params}) -> ${result}` });
}

function namespace_of(
  node: DtsNamespace,
  skipped: Skipped[],
  local_hosts: ReadonlySet<string>,
): PenguNamespace {
  const members: PenguMember[] = [];
  for (const child of node.nodes) {
    if (child.kind === "var") {
      const mapped = map_type(child.type);
      members.push({
        kind: "property",
        name: child.name,
        sigils: [],
        text: eager_text(mapped.text, local_hosts),
        mutable: false,
        optional: false,
        static: false,
      });
      continue;
    }
    if (child.kind === "function") {
      const params = child.params
        .map(
          (param) =>
            `${param.rest ? "..." : ""}${param_name(param.name)}: ${eager_text(map_param(param).text, local_hosts)}`,
        )
        .join(", ");
      members.push({
        kind: "method",
        name: child.name,
        sigils: child.type_params,
        text: `(${params}) -> ${map_result(child.result).text}`,
        mutable: false,
        optional: false,
        static: false,
      });
      continue;
    }
    skipped.push({ name: `${node.name}.…`, reason: "contenido de namespace no representable" });
  }
  return { name: node.name, members };
}

function enum_of(node: DtsEnum): PenguEnum {
  return {
    name: node.name,
    members: node.members.map((member) =>
      member.value === undefined ? { name: member.name } : { name: member.name, value: member.value },
    ),
  };
}
