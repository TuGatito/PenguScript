// Emisor de `.d.pengu` a partir de lo que `partition.ts` decidió.
//
// El texto es determinista: los tipos en el orden del `.d.ts`, luego los
// namespaces, los alias, las `omen`, los globales y por último los `declare`.
// No se escribe ninguna fecha ni ruta absoluta, para que dos máquinas generen
// el mismo archivo (`--check` en la suite depende de eso).

import type {
  PenguAlias,
  PenguBindingModule,
  PenguDeclare,
  PenguEnum,
  PenguGlobal,
  PenguHostType,
  PenguMember,
  PenguNamespace,
} from "./partition.ts";

export interface EmitOptions {
  // Nombre del realm del módulo generado (`js_dom`, `js_events`…).
  readonly realm: string;
  // Nombre del `.d.ts` de origen, tal cual se escribe en la cabecera.
  readonly source: string;
  // Módulos que el catálogo necesita (`std/js/types` casi siempre).
  readonly invokes?: readonly string[];
}

const HEADER_LINES = 2;

export function emit_binding_module(module: PenguBindingModule, options: EmitOptions): string {
  const lines: string[] = [];
  lines.push(`-- Enlaces generados por «pengu ts-bindgen» desde ${options.source}.`);
  lines.push("-- No edites este archivo a mano: vuelve a ejecutar el generador.");
  lines.push("");
  lines.push(`realm ${options.realm}`);
  for (const invoke of options.invokes ?? []) {
    lines.push(`invoke "${invoke}"`);
  }

  for (const host of module.host_types) {
    lines.push("");
    lines.push(...host_type_lines(host));
  }
  for (const namespace of module.namespaces) {
    lines.push("");
    lines.push(...namespace_lines(namespace));
  }
  for (const alias of module.aliases) {
    lines.push("");
    lines.push(...alias_lines(alias));
  }
  for (const omen of module.enums) {
    lines.push("");
    lines.push(...enum_lines(omen));
  }
  for (const global of module.globals) {
    lines.push(...global_lines(global));
  }
  if (module.declares.length > 0) {
    lines.push("");
    lines.push("declare");
    for (const fn of module.declares) lines.push(...declare_lines(fn));
  }

  return `${lines.join("\n")}\n`;
}

// El texto de los `.d.ts` no se copia como comentario: el formateador
// reindenta los comentarios de un bloque a su manera y el catálogo generado
// tiene que quedar idéntico byte a byte tras `pengu fmt`. Los `doc` siguen en
// el modelo (§6.6) para cuando se emita JSDoc.
function doc_lines(_doc: string | undefined, _indent: string): string[] {
  return [];
}

function unused_doc_lines(doc: string | undefined, indent: string): string[] {
  if (doc === undefined) return [];
  const text = doc.replace(/\*\//g, "").replace(/\s+/g, " ").trim();
  if (text === "") return [];
  return [`${indent}-- ${text}`];
}

function host_type_lines(host: PenguHostType): string[] {
  const lines: string[] = [];
  lines.push(...doc_lines(host.doc, ""));
  const sigils = host.sigils.length > 0 ? `<${host.sigils.join(", ")}>` : "";
  const heir = host.parent === undefined ? "" : ` heir js::${host.parent}`;
  lines.push(`host js::${host.name}${sigils}${heir}`);
  for (const member of host.members) {
    lines.push(...member_lines(member, "  "));
  }
  return lines;
}

function member_lines(member: PenguMember, indent: string): string[] {
  // `operator` es la única palabra clave que el formateador separa del `:`
  // (`operator : T`): el resto de nombres clave se escriben tal cual.
  const colon = member.kind === "property" || member.kind === "method" ? (member.name === "operator" ? " :" : ":") : "";
  const lines = doc_lines(member.doc, indent);
  const optional = member.optional && member.kind === "property" ? "?" : "";
  const mutable = member.mutable ? "mut " : "";
  const is_static = member.static ? "static " : "";
  switch (member.kind) {
    case "property":
      lines.push(`${indent}${is_static}${mutable}${member.name}${optional}${colon} ${member.text}`);
      break;
    case "method": {
      const sigils = member.sigils.length > 0 ? `<${member.sigils.join(", ")}>` : "";
      lines.push(`${indent}${is_static}${member.name}${sigils}${colon} ${member.text}`);
      break;
    }
    case "index":
      // El formateador escribe `mut[indice: K]: V` sin espacio.
      lines.push(`${indent}${member.mutable ? "mut" : ""}${member.text}`);
      break;
    case "constructor":
      lines.push(`${indent}${member.text}`);
      break;
  }
  return lines;
}

function namespace_lines(namespace: PenguNamespace): string[] {
  const lines = [`host namespace ${namespace.name}`];
  for (const member of namespace.members) {
    lines.push(...member_lines(member, "  "));
  }
  return lines;
}

function alias_lines(alias: PenguAlias): string[] {
  const keyword = alias.seal ? "seal" : "echo";
  return [`${keyword} js::${alias.name} = ${alias.target}`];
}

function enum_lines(omen: PenguEnum): string[] {
  const lines = [`omen js::${omen.name}`];
  for (const member of omen.members) {
    const value = member.value === undefined ? "" : ` = ${member.value}`;
    lines.push(`  ${member.name}${value}`);
  }
  return lines;
}

function global_lines(global: PenguGlobal): string[] {
  const lines = doc_lines(global.doc, "");
  const type = global.type === undefined ? "" : `: ${global.type}`;
  lines.push(`host global ${global.name}${type}`);
  return lines;
}

function declare_lines(fn: PenguDeclare): string[] {
  const lines = doc_lines(fn.doc, "  ");
  lines.push(`  ${fn.name} = ${fn.text}`);
  return lines;
}

// Cabecera con la plataforma y el origen, que usa `--check` para detectar
// archivos generados en otra máquina.
export function binding_summary(module: PenguBindingModule): string {
  const parts = [
    `${module.host_types.length} tipo(s)`,
    `${module.members} miembro(s)`,
    `${module.namespaces.length} namespace(s)`,
    `${module.globals.length} global(es)`,
    `${module.declares.length} función(es)`,
  ];
  if (module.skipped.length > 0) parts.push(`${module.skipped.length} omitido(s)`);
  return parts.join(", ");
}

export function header_line_count(): number {
  return HEADER_LINES;
}
