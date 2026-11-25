// Modelo de tipos de un `.d.ts`, ya normalizado e independiente de TypeScript.
//
// El lector (dts_reader.ts) traduce los nodos de la Compiler API a esta unión.
// Todo lo que no tiene traducción a PenguScript cae en «unsupported» con el
// texto original y el motivo, para que el informe de omisiones sea honesto.

export interface DtsSpan {
  readonly file: string;
  readonly line: number;
  readonly column: number;
}

export interface DtsParam {
  readonly name: string;
  readonly type: DtsType;
  readonly optional: boolean;
  readonly rest: boolean;
}

export type DtsLiteral = string | number | boolean;

export type DtsKeyword =
  | "string"
  | "number"
  | "boolean"
  | "void"
  | "any"
  | "unknown"
  | "object"
  | "bigint"
  | "symbol"
  | "never"
  | "undefined"
  | "null";

export interface DtsMemberBase {
  readonly name: string;
  readonly doc?: string;
  readonly span: DtsSpan;
}

export type DtsMember =
  | (DtsMemberBase & {
      readonly kind: "property";
      readonly type: DtsType;
      readonly readonly: boolean;
      readonly optional: boolean;
    })
  | (DtsMemberBase & {
      readonly kind: "method";
      readonly type_params: readonly string[];
      readonly params: readonly DtsParam[];
      readonly result: DtsType;
      readonly optional: boolean;
    })
  | {
      readonly kind: "index";
      readonly key: DtsType;
      readonly value: DtsType;
      readonly readonly: boolean;
      readonly span: DtsSpan;
    }
  | {
      readonly kind: "construct";
      readonly params: readonly DtsParam[];
      readonly span: DtsSpan;
    }
  | {
      readonly kind: "call";
      readonly params: readonly DtsParam[];
      readonly result: DtsType;
      readonly span: DtsSpan;
    };

export type DtsType =
  | { readonly kind: "keyword"; readonly name: DtsKeyword }
  | {
      readonly kind: "ref";
      readonly name: string;
      readonly args: readonly DtsType[];
    }
  | { readonly kind: "literal"; readonly value: DtsLiteral }
  | { readonly kind: "union"; readonly items: readonly DtsType[] }
  | { readonly kind: "intersection"; readonly items: readonly DtsType[] }
  | { readonly kind: "array"; readonly element: DtsType }
  | { readonly kind: "tuple"; readonly items: readonly DtsType[] }
  | {
      readonly kind: "function";
      readonly params: readonly DtsParam[];
      readonly result: DtsType;
    }
  | {
      readonly kind: "object_literal";
      readonly members: readonly DtsMember[];
    }
  | {
      readonly kind: "indexed";
      readonly object: DtsType;
      readonly index: DtsType;
    }
  | { readonly kind: "keyof"; readonly object: DtsType }
  | { readonly kind: "typeof"; readonly name: string }
  | { readonly kind: "this_type" }
  | {
      readonly kind: "unsupported";
      readonly text: string;
      readonly because: string;
    };

export function unsupported_type(
  text: string,
  because: string,
): DtsType {
  return { kind: "unsupported", text, because };
}

export function ref_type(
  name: string,
  args: readonly DtsType[] = [],
): DtsType {
  return { kind: "ref", name, args };
}

// «T | null | undefined» es la forma en la que TypeScript dice «opcional».
// Devuelve el tipo sin los nulos y si había alguno.
export interface NullableSplit {
  readonly inner: DtsType;
  readonly nullable: boolean;
}

export function split_nullable(type: DtsType): NullableSplit {
  if (type.kind !== "union") return { inner: type, nullable: false };
  const kept: DtsType[] = [];
  let nullable = false;
  for (const item of type.items) {
    if (is_nullish(item)) {
      nullable = true;
      continue;
    }
    kept.push(item);
  }
  if (kept.length === 0) return { inner: { kind: "keyword", name: "any" }, nullable: true };
  if (kept.length === 1) return { inner: kept[0] as DtsType, nullable };
  return { inner: { kind: "union", items: kept }, nullable };
}

export function is_nullish(type: DtsType): boolean {
  return (
    type.kind === "keyword" &&
    (type.name === "null" || type.name === "undefined")
  );
}

// Recorre un tipo y devuelve los nombres referenciados (para el orden de
// declaración y para detectar dependencias entre interfaces).
export function referenced_names(type: DtsType, into: Set<string>): void {
  switch (type.kind) {
    case "ref":
      into.add(type.name);
      for (const arg of type.args) referenced_names(arg, into);
      return;
    case "union":
    case "intersection":
      for (const item of type.items) referenced_names(item, into);
      return;
    case "array":
      referenced_names(type.element, into);
      return;
    case "tuple":
      for (const item of type.items) referenced_names(item, into);
      return;
    case "function":
      for (const param of type.params) referenced_names(param.type, into);
      referenced_names(type.result, into);
      return;
    case "object_literal":
      for (const member of type.members) referenced_member_names(member, into);
      return;
    case "indexed":
      referenced_names(type.object, into);
      referenced_names(type.index, into);
      return;
    case "keyof":
      referenced_names(type.object, into);
      return;
    default:
      return;
  }
}

function referenced_member_names(member: DtsMember, into: Set<string>): void {
  switch (member.kind) {
    case "property":
      referenced_names(member.type, into);
      return;
    case "method":
      for (const param of member.params) referenced_names(param.type, into);
      referenced_names(member.result, into);
      return;
    case "index":
      referenced_names(member.key, into);
      referenced_names(member.value, into);
      return;
    case "construct":
    case "call":
      for (const param of member.params) referenced_names(param.type, into);
      return;
  }
}

// Huella textual estable de un tipo, para comparar firmas y para el informe.
export function type_text(type: DtsType): string {
  switch (type.kind) {
    case "keyword":
      return type.name;
    case "ref":
      return type.args.length === 0
        ? type.name
        : `${type.name}<${type.args.map(type_text).join(", ")}>`;
    case "literal":
      return typeof type.value === "string" ? JSON.stringify(type.value) : String(type.value);
    case "union":
      return type.items.map(type_text).join(" | ");
    case "intersection":
      return type.items.map(type_text).join(" & ");
    case "array":
      return `${type_text(type.element)}[]`;
    case "tuple":
      return `[${type.items.map(type_text).join(", ")}]`;
    case "function":
      return `(${type.params.map((param) => `${param.name}: ${type_text(param.type)}`).join(", ")}) => ${type_text(type.result)}`;
    case "object_literal":
      return `{ ${type.members.map(member_text).join("; ")} }`;
    case "indexed":
      return `${type_text(type.object)}[${type_text(type.index)}]`;
    case "keyof":
      return `keyof ${type_text(type.object)}`;
    case "typeof":
      return `typeof ${type.name}`;
    case "this_type":
      return "this";
    case "unsupported":
      return type.text;
  }
}

function member_text(member: DtsMember): string {
  switch (member.kind) {
    case "property":
      return `${member.readonly ? "readonly " : ""}${member.name}${member.optional ? "?" : ""}: ${type_text(member.type)}`;
    case "method":
      return `${member.name}(${member.params.map(param_text).join(", ")}): ${type_text(member.result)}`;
    case "index":
      return `[clave: ${type_text(member.key)}]: ${type_text(member.value)}`;
    case "construct":
      return `new (${member.params.map(param_text).join(", ")})`;
    case "call":
      return `(${member.params.map(param_text).join(", ")}) => ${type_text(member.result)}`;
  }
}

export function param_text(param: DtsParam): string {
  const rest = param.rest ? "..." : "";
  const optional = param.optional ? "?" : "";
  return `${rest}${param.name}${optional}: ${type_text(param.type)}`;
}
