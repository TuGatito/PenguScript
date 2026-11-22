// Genera `docs/stdlib_api.md` a partir de los módulos de `std/`.
//
// La referencia se escribe desde el código (parser real, no expresiones
// regulares) para que no se desincronice: `bun run scripts/gen_stdlib_docs.ts`
// la reescribe y `--check` falla si hay diferencias (lo usa la suite).

import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { parse_text } from "../src/frontend/parser.ts";
import type { DeclNode } from "../src/frontend/ast_decl.ts";
import type { TypeNode } from "../src/frontend/ast_type.ts";
import type { ParamNode } from "../src/frontend/ast_param.ts";
import type { ExprNode } from "../src/frontend/ast_expr.ts";

const root = join(import.meta.dir, "..");
const std_dir = join(root, "std");
const output = join(root, "docs", "stdlib_api.md");

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
      return `ref<${type_text(type.inner)}>`;
    case "function_type": {
      const params = type.params.map(type_text).join(", ");
      return `function<(${params}) -> ${type_text(type.result)}>`;
    }
    case "tuple_type":
      return `(${type.items.map(type_text).join(", ")})`;
    case "array_type":
      return `array<${type_text(type.element)}>`;
    default:
      return "?";
  }
}

function default_text(expr: ExprNode): string | undefined {
  switch (expr.kind) {
    case "int_lit":
    case "float_lit":
      return expr.value;
    case "bool_lit":
      return expr.value ? "true" : "false";
    case "char_lit":
      return `'${expr.value}'`;
    case "string_lit":
      return expr.parts.every((part) => part.kind === "text_part")
        ? `"${expr.parts.map((part) => (part.kind === "text_part" ? part.text : "")).join("")}"`
        : undefined;
    default:
      return undefined;
  }
}

function params_text(params: readonly ParamNode[]): string {
  return params
    .map((param) => {
      const mutable = param.mutable ? "mut " : "";
      const name = param.variadic ? `...${param.name}` : param.name;
      const type = param.type === undefined ? "" : `: ${type_text(param.type)}`;
      const fallback = param.default_value === undefined ? undefined : default_text(param.default_value);
      const value = param.default_value === undefined ? "" : ` = ${fallback ?? "…"}`;
      return `${mutable}${name}${type}${value}`;
    })
    .join(", ");
}

function signature(name: string, params: readonly ParamNode[], result: TypeNode | undefined): string {
  return `\`${name}(${params_text(params)}) -> ${type_text(result)}\``;
}

function summarize(source: string): string {
  const lines = source.split("\n");
  const collected: string[] = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === "") {
      if (collected.length > 0) break;
      continue;
    }
    if (!trimmed.startsWith("--")) break;
    collected.push(trimmed.slice(2).trim());
  }
  return collected.join(" ").trim();
}

interface ModuleDoc {
  readonly name: string;
  readonly summary: string;
  readonly realm: string | undefined;
  readonly consts: readonly string[];
  readonly omens: readonly string[];
  readonly runes: readonly string[];
  readonly enchantings: readonly string[];
  readonly functions: readonly string[];
  readonly intrinsics: readonly string[];
}

function render_module(name: string, source: string, decls: readonly DeclNode[]): ModuleDoc {
  const consts: string[] = [];
  const omens: string[] = [];
  const runes: string[] = [];
  const enchantings: string[] = [];
  const functions: string[] = [];
  const intrinsics: string[] = [];
  let realm: string | undefined;
  const methods_by_target = new Map<string, string[]>();

  for (const decl of decls) {
    switch (decl.kind) {
      case "realm_decl":
        realm = decl.name;
        break;
      case "const_decl":
        consts.push(`\`${decl.name}${decl.declared_type === undefined ? "" : `: ${type_text(decl.declared_type)}`}\``);
        break;
      case "omen_decl": {
        const variants = decl.variants
          .map((variant) =>
            variant.payload.length === 0
              ? variant.name
              : `${variant.name}(${variant.payload.map(type_text).join(", ")})`,
          )
          .join("; ");
        omens.push(`\`omen ${decl.name}\` — ${variants}`);
        break;
      }
      case "rune_decl": {
        const fields = decl.fields.map((field) => `\`${field.name}: ${type_text(field.type)}\``).join(", ");
        const ctor =
          decl.constructor === undefined ? "" : ` · constructor \`${decl.name}(${params_text(decl.constructor.params)})\``;
        runes.push(`\`rune ${decl.name}\` — campos: ${fields === "" ? "ninguno" : fields}${ctor}`);
        break;
      }
      case "enchanting_decl": {
        const methods = decl.methods.map(
          (method) =>
            `\`${method.mutable ? "mut " : ""}${method.name}(${params_text(method.params)}) -> ${type_text(method.result)}\``,
        );
        const key = type_text(decl.target_type);
        methods_by_target.set(key, [...(methods_by_target.get(key) ?? []), ...methods]);
        break;
      }
      case "function_decl": {
        const name = decl.operator === undefined ? decl.name : `operator ${decl.operator}`;
        functions.push(signature(name, decl.params, decl.result));
        break;
      }
      case "intrinsic_decl":
        for (const declare of decl.declares) intrinsics.push(declare.name);
        break;
      default:
        break;
    }
  }

  for (const [target, methods] of methods_by_target) {
    enchantings.push(`\`enchanting ${target}\` — ${methods.join(", ")}`);
  }

  return {
    name,
    summary: summarize(source),
    realm,
    consts,
    omens,
    runes,
    enchantings,
    functions,
    intrinsics,
  };
}

function render(docs: readonly ModuleDoc[]): string {
  const lines: string[] = [
    "<!-- Generado por scripts/gen_stdlib_docs.ts a partir de std/. No editar a mano. -->",
    "",
    "# Referencia de la biblioteca estándar",
    "",
    "Firmas exactas de cada módulo de `std/`, tomadas del parser del compilador.",
    "Los módulos previstos para 0.2.0 no aparecen aquí porque todavía no existen.",
    "",
  ];
  for (const doc of docs) {
    lines.push(`## \`std/${doc.name}\``);
    lines.push("");
    if (doc.summary !== "") {
      lines.push(doc.summary);
      lines.push("");
    }
    if (doc.realm !== undefined) lines.push(`Realm: \`${doc.realm}\`.`);
    lines.push("");
    if (doc.consts.length > 0) {
      lines.push("Constantes:");
      lines.push("");
      for (const item of doc.consts) lines.push(`- ${item}`);
      lines.push("");
    }
    if (doc.omens.length > 0) {
      lines.push("Omens:");
      lines.push("");
      for (const item of doc.omens) lines.push(`- ${item}`);
      lines.push("");
    }
    if (doc.runes.length > 0) {
      lines.push("Runes:");
      lines.push("");
      for (const item of doc.runes) lines.push(`- ${item}`);
      lines.push("");
    }
    if (doc.enchantings.length > 0) {
      lines.push("Métodos (enchantings):");
      lines.push("");
      for (const item of doc.enchantings) lines.push(`- ${item}`);
      lines.push("");
    }
    if (doc.functions.length > 0) {
      lines.push("Funciones:");
      lines.push("");
      for (const item of doc.functions) lines.push(`- ${item}`);
      lines.push("");
    }
    if (doc.intrinsics.length > 0) {
      lines.push(`Intrínsecos (\`declare\`): ${doc.intrinsics.map((name) => `\`${name}\``).join(", ")}.`);
      lines.push("");
    }
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
    const parsed = parse_text(`std/${file}`, source);
    const errors = parsed.diagnostics.filter((item) => item.severity === "error");
    if (errors.length > 0) {
      throw new Error(`std/${file}: ${errors.map((item) => item.message).join("; ")}`);
    }
    docs.push(render_module(file.replace(/\.(d\.)?pengu$/, ""), source, parsed.program.decls));
  }
  return render(docs);
}

const expected = generate();
if (process.argv.includes("--check")) {
  const current = readFileSync(output, "utf8");
  if (current !== expected) {
    console.error("docs/stdlib_api.md está desactualizado: ejecuta bun run scripts/gen_stdlib_docs.ts");
    process.exit(1);
  }
  console.log("docs/stdlib_api.md está al día");
} else {
  writeFileSync(output, expected);
  console.log(`docs/stdlib_api.md actualizado (${expected.split("\n").length} líneas)`);
}
