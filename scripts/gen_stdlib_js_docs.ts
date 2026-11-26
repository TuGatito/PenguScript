// Genera `docs/stdlib_js.md` a partir de `std/js/`.
//
// Igual que `gen_stdlib_docs.ts` con `std/`, la referencia se escribe desde el
// código con el parser real: si un `.d.pengu` del catálogo no parsea, el script
// falla antes de documentarlo. Los archivos generados con `pengu ts-bindgen`
// llevan además su recuento de tipos y miembros, para que se vea de un vistazo
// qué cubre el catálogo y qué se queda fuera (las omisiones del informe).

import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { parse_text } from "../src/frontend/parser.ts";
import type { DeclNode } from "../src/frontend/ast_decl.ts";
import type { ParamNode } from "../src/frontend/ast_param.ts";
import type { TypeNode } from "../src/frontend/ast_type.ts";

const root = join(import.meta.dir, "..");
const std_dir = join(root, "std", "js");
const output = join(root, "docs", "stdlib_js.md");

function type_text(type: TypeNode | undefined): string {
  if (type === undefined) return "void";
  switch (type.kind) {
    case "primitive_type":
      return type.name;
    case "named_type":
      return type.args.length === 0 ? type.name : `${type.name}<${type.args.map(type_text).join(", ")}>`;
    case "optional_type":
      return `${type_text(type.inner)}?`;
    case "ref_type":
      return `${type.mutable ? "mut " : ""}ref<${type_text(type.inner)}>`;
    case "function_type":
      return `function<(${type.params.map(type_text).join(", ")}) -> ${type_text(type.result)}>`;
    case "tuple_type":
      return `(${type.items.map(type_text).join(", ")})`;
    case "array_type":
      return `array<${type_text(type.element)}>`;
    default:
      return "?";
  }
}

function param_text(param: ParamNode): string {
  const mutable = param.mutable ? "mut " : "";
  const name = param.variadic ? `...${param.name}` : param.name;
  const type = param.type === undefined ? "" : `: ${type_text(param.type)}`;
  return `${mutable}${name}${type}`;
}

interface MemberDoc {
  readonly text: string;
}

interface TypeDoc {
  readonly name: string;
  readonly parent: string | undefined;
  readonly members: readonly MemberDoc[];
}

interface ModuleDoc {
  readonly name: string;
  readonly generated: boolean;
  readonly realm: string | undefined;
  readonly invokes: readonly string[];
  readonly types: readonly TypeDoc[];
  readonly globals: readonly string[];
  readonly namespaces: readonly string[];
  readonly declares: readonly string[];
  readonly omens: readonly string[];
  readonly aliases: readonly string[];
}

function member_lines(decl: DeclNode): MemberDoc[] {
  if (decl.kind !== "host_decl") return [];
  return decl.members.map((member) => {
    switch (member.kind) {
      case "host_property":
        return { text: `\`${member.mutable ? "mut " : ""}${member.name}: ${type_text(member.type)}\`` };
      case "host_method": {
        const sigils = member.sigils.length === 0 ? "" : `<${member.sigils.join(", ")}>`;
        const params = member.params.map(param_text).join(", ");
        const statico = member.is_static ? "static " : "";
        return { text: `\`${statico}${member.name}${sigils}(${params}) -> ${type_text(member.result)}\`` };
      }
      case "host_constructor":
        return { text: `\`constructor(${member.params.map(param_text).join(", ")})\`` };
      case "host_index":
        return { text: `\`${member.mutable ? "mut " : ""}[${member.key_name}: ${type_text(member.key_type)}]: ${type_text(member.value)}\`` };
      default:
        return { text: "`?`" };
    }
  });
}

function render_module(name: string, source: string, decls: readonly DeclNode[]): ModuleDoc {
  const types: TypeDoc[] = [];
  const globals: string[] = [];
  const namespaces: string[] = [];
  const declares: string[] = [];
  const omens: string[] = [];
  const aliases: string[] = [];
  const invokes: string[] = [];
  let realm: string | undefined;

  for (const decl of decls) {
    switch (decl.kind) {
      case "realm_decl":
        realm = decl.name;
        break;
      case "invoke_decl":
        invokes.push(decl.path);
        break;
      case "host_decl": {
        const hier = decl.parent === undefined ? "" : ` → ${type_text(decl.parent)}`;
        types.push({ name: `${decl.name}${hier}`, parent: undefined, members: member_lines(decl) });
        break;
      }
      case "host_global_decl":
        globals.push(decl.type === undefined ? `\`${decl.name}\`` : `\`${decl.name}: ${type_text(decl.type)}\``);
        break;
      case "host_namespace_decl":
        namespaces.push(`\`${decl.name}\` (${decl.members.length} miembro(s))`);
        break;
      case "extern_decl":
        for (const declare of decl.declares) {
          const params = declare.params.map(param_text).join(", ");
          declares.push(`\`${declare.name}(${params}) -> ${type_text(declare.result)}\``);
        }
        break;
      case "intrinsic_decl":
        for (const declare of decl.declares) {
          const params = declare.params.map(param_text).join(", ");
          declares.push(`\`${declare.name}(${params}) -> ${type_text(declare.result)}\``);
        }
        break;
      case "omen_decl":
        omens.push(`\`omen ${decl.name}\``);
        break;
      case "echo_decl":
        aliases.push(`\`echo ${decl.name} = ${type_text(decl.target)}\``);
        break;
      case "seal_decl":
        aliases.push(`\`seal ${decl.name} = ${type_text(decl.target)}\``);
        break;
      default:
        break;
    }
  }

  return {
    name,
    generated: source.includes("Enlaces generados por «pengu ts-bindgen»"),
    realm,
    invokes,
    types,
    globals,
    namespaces,
    declares,
    omens,
    aliases,
  };
}

// Los módulos generados tienen cientos de globos y alias: se listan los
// primeros y se dice cuántos quedan (la lista completa está en el `.d.pengu`).
function cap(items: readonly string[], limit: number): string {
  if (items.length <= limit) return items.join(", ");
  return `${items.slice(0, limit).join(", ")} … y ${items.length - limit} más`;
}

function render(docs: readonly ModuleDoc[]): string {
  const manual = docs.filter((doc) => !doc.generated);
  const generated = docs.filter((doc) => doc.generated);
  const tipos = generated.reduce((total, doc) => total + doc.types.length, 0);
  const miembros = generated.reduce(
    (total, doc) => total + doc.types.reduce((sum, type) => sum + type.members.length, 0),
    0,
  );
  const lines: string[] = [
    "<!-- Generado por scripts/gen_stdlib_js_docs.ts a partir de std/js/. No editar a mano. -->",
    "",
    "# Catálogo del navegador (`std/js/`)",
    "",
    "Módulos que describen objetos que solo existen en un host JavaScript. Se",
    "compilan únicamente con `--target js`; usarlos con `--target cpp` da **E0518**.",
    "La sintaxis de enlace (`host`, `host global`, `host namespace`, `mut`) está en",
    "[`cheatsheet.md`](cheatsheet.md#host-objects-browser-apis), y la forma del código",
    "emitido en [`javascript.md`](javascript.md).",
    "",
    `Los módulos marcados «generado» salen de \`third_party/dts\` con`,
    "`bun run gen:std-js` y no se editan a mano.",
    "",
    `| Archivos | Tipos | Miembros |`,
    `| --- | --- | --- |`,
    `| ${manual.length} escritos a mano, ${generated.length} generados | ${tipos} | ${miembros} |`,
    "",
  ];

  const module_section = (doc: ModuleDoc): void => {
    lines.push(`## \`std/js/${doc.name}\``);
    lines.push("");
    if (doc.generated) {
      lines.push("Generado con `pengu ts-bindgen`; no editar a mano.");
      lines.push("");
    }
    if (doc.realm !== undefined) lines.push(`Realm: \`${doc.realm}\`.`);
    if (doc.invokes.length > 0) {
      lines.push(`Invoca: ${doc.invokes.map((path) => `\`${path}\``).join(", ")}.`);
    }
    lines.push("");
    if (doc.aliases.length > 0) {
      lines.push(`Alias (${doc.aliases.length}): ${cap(doc.aliases, doc.generated ? 10 : doc.aliases.length)}.`);
      lines.push("");
    }
    if (doc.omens.length > 0) {
      lines.push(`Omens (${doc.omens.length}): ${cap(doc.omens, doc.generated ? 10 : doc.omens.length)}.`);
      lines.push("");
    }
    if (doc.globals.length > 0) {
      lines.push(`Globales (${doc.globals.length}): ${cap(doc.globals, doc.generated ? 12 : doc.globals.length)}.`);
      lines.push("");
    }
    if (doc.namespaces.length > 0) {
      lines.push(`Namespaces: ${cap(doc.namespaces, doc.generated ? 10 : doc.namespaces.length)}.`);
      lines.push("");
    }
    if (doc.declares.length > 0) {
      lines.push(`Funciones del host (\`declare\`, ${doc.declares.length}):`);
      lines.push("");
      const limit = doc.generated ? 12 : doc.declares.length;
      for (const item of doc.declares.slice(0, limit)) lines.push(`- ${item}`);
      if (doc.declares.length > limit) {
        lines.push(`- … y ${doc.declares.length - limit} más (ver el \`.d.pengu\`)`);
      }
      lines.push("");
    }
    if (doc.generated) {
      // Un catálogo generado tiene miles de miembros: la referencia completa es
      // el propio `.d.pengu`, aquí solo interesa qué tipos trae y cuánto.
      const miembros = doc.types.reduce((total, type) => total + type.members.length, 0);
      lines.push(`Tipos del host (${doc.types.length}, ${miembros} miembro(s)):`);
      lines.push("");
      for (const type of doc.types) {
        lines.push(`- \`${type.name}\` (${type.members.length} miembro(s))`);
      }
      lines.push("");
      return;
    }
    if (doc.types.length > 0) {
      lines.push(`Tipos del host (${doc.types.length}):`);
      lines.push("");
      for (const type of doc.types) {
        lines.push(`### \`${type.name}\``);
        lines.push("");
        if (type.members.length === 0) {
          lines.push("Sin miembros declarados.");
          lines.push("");
          continue;
        }
        for (const member of type.members) lines.push(`- ${member.text}`);
        lines.push("");
      }
    }
  };

  if (manual.length > 0) {
    lines.push("## Módulos escritos a mano");
    lines.push("");
    for (const doc of manual) module_section(doc);
  }
  if (generated.length > 0) {
    lines.push("## Módulos generados");
    lines.push("");
    for (const doc of generated) module_section(doc);
  }
  return `${lines.join("\n").trimEnd()}\n`;
}

function generate(): string {
  const files = readdirSync(std_dir)
    .filter((name) => name.endsWith(".pengu"))
    .sort();
  const docs: ModuleDoc[] = [];
  for (const file of files) {
    const source = readFileSync(join(std_dir, file), "utf8");
    const parsed = parse_text(`std/js/${file}`, source);
    const errors = parsed.diagnostics.filter((item) => item.severity === "error");
    if (errors.length > 0) {
      throw new Error(`std/js/${file}: ${errors.map((item) => item.message).join("; ")}`);
    }
    docs.push(render_module(file.replace(/\.(d\.)?pengu$/, ""), source, parsed.program.decls));
  }
  return render(docs);
}

const expected = generate();
if (process.argv.includes("--check")) {
  const current = readFileSync(output, "utf8");
  if (current !== expected) {
    console.error("docs/stdlib_js.md está desactualizado: ejecuta bun run scripts/gen_stdlib_js_docs.ts");
    process.exit(1);
  }
  console.log("docs/stdlib_js.md está al día");
} else {
  writeFileSync(output, expected);
  console.log(`docs/stdlib_js.md actualizado (${expected.split("\n").length} líneas)`);
}
