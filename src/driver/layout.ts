// Medición de tamaños reales: se genera un programa C++ con las
// declaraciones del proyecto, se compila con el mismo toolchain que el
// ejecutable y se leen `sizeof`, `alignof` y los desplazamientos de campo.
//
// Si no hay compilador, la medición no está disponible: nunca se inventa.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { spawnSync } from "node:child_process";
import type { ModuleInfo } from "../semantic/module_info.ts";
import type { ProgramUnit } from "../codegen/cpp_module.ts";
import { collect_type_realms, generate_program } from "../codegen/cpp_module.ts";
import { sanitize_namespace } from "../codegen/cpp_types.ts";
import { RUNTIME_HEADER } from "../codegen/runtime_source.ts";
import { make_sink } from "../diagnostics/sink.ts";
import { cpp_identifier, cpp_type } from "../codegen/cpp_types.ts";

export interface FieldLayout {
  readonly name: string;
  readonly offset: number;
  readonly size: number;
}

export interface TypeLayout {
  readonly name: string;
  readonly size: number;
  readonly align: number;
  readonly fields: readonly FieldLayout[];
}

export interface ValueLayout {
  readonly name: string;
  readonly size: number;
  readonly align: number;
}

export interface FunctionLayout {
  readonly name: string;
  readonly result: number;
  readonly params: number;
  readonly total: number;
  readonly callable: number;
}

export interface LayoutTable {
  readonly available: boolean;
  readonly message: string | undefined;
  readonly types: ReadonlyMap<string, TypeLayout>;
  readonly values: ReadonlyMap<string, ValueLayout>;
  readonly functions: ReadonlyMap<string, FunctionLayout>;
}

const EMPTY_TABLE: LayoutTable = { available: false, message: undefined, types: new Map(), values: new Map(), functions: new Map() };

export interface LayoutTarget {
  readonly name: string;
  readonly cpp: string;
  readonly fields: readonly string[];
}

export const PRIMITIVE_LAYOUTS: readonly LayoutTarget[] = [
  "bool", "char", "int", "long", "long long", "float", "double", "long double",
  "size_t", "ptrdiff_t", "intptr_t", "uintptr_t", "byte", "int8_t", "uint8_t", "int16_t",
  "uint16_t", "int32_t", "uint32_t", "int64_t", "uint64_t", "string", "string_view",
  "wstring", "u8string", "u16string", "u32string", "char8_t", "char16_t", "char32_t",
].map((name) => ({ name, cpp: cpp_of_primitive(name), fields: [] }));



function cpp_of_primitive(name: string): string {
  switch (name) {
    case "string":
      return "std::string";
    case "string_view":
      return "std::string_view";
    case "wstring":
      return "std::wstring";
    case "u8string":
      return "std::u8string";
    case "u16string":
      return "std::u16string";
    case "u32string":
      return "std::u32string";
    case "byte":
      return "std::byte";
    default:
      return name.startsWith("size_t") || name === "size_t" || name === "ptrdiff_t" || name === "intptr_t" || name === "uintptr_t"
        ? `std::${name}`
        : name;
  }
}

// Targets de los tipos declarados por el proyecto. Las runes y omens
// genéricos se miden con su instanciación representativa `int` (D3).
export function layout_targets(units: readonly ProgramUnit[]): LayoutTarget[] {
  const targets: LayoutTarget[] = [...PRIMITIVE_LAYOUTS];
  for (const unit of units) {
    const realm = sanitize_namespace(unit.module.realm);
    for (const [name, rune] of unit.module.env.runes) {
      const args = rune.sigils.map(() => "int");
      const cpp = `${realm}::${cpp_identifier(name)}${args.length === 0 ? "" : `<${args.join(", ")}>`}`;
      targets.push({ name: `${realm}::${name}`, cpp, fields: [...rune.fields.keys()] });
    }
    for (const [name, omen] of unit.module.env.omens) {
      const args = omen.sigils.map(() => "int");
      const cpp = `${realm}::${cpp_identifier(name)}${args.length === 0 ? "" : `<${args.join(", ")}>`}`;
      targets.push({ name: `${realm}::${name}`, cpp, fields: [] });
    }
    for (const [name, alias] of unit.module.env.aliases) {
      const args = alias.sigils.map(() => "int");
      const cpp = `${realm}::${cpp_identifier(name)}${args.length === 0 ? "" : `<${args.join(", ")}>`}`;
      targets.push({ name: `${realm}::${name}`, cpp, fields: [] });
    }
  }
  return targets;
}

export function probe_source(units: readonly ProgramUnit[], entry: ModuleInfo): string {
  const sink = make_sink({ max: 10 });
  const generated = generate_program(units, entry, sink, { emit_main: false });
  const targets = layout_targets(units);
  const realms = collect_type_realms(units);
  const cpp_type_of = (type: Parameters<typeof cpp_type>[0]): string => cpp_type(type, realms);
  const lines: string[] = [generated.code, "", "#include <cstddef>", "#include <cstdio>", "#include <functional>", "", "int main() {"];
  for (const target of targets) {
    lines.push(`  std::printf("SIZE\\t%s\\t%zu\\t%zu\\n", ${JSON.stringify(target.name)}, sizeof(${target.cpp}), alignof(${target.cpp}));`);
    for (const field of target.fields) {
      lines.push(
        `  std::printf("FIELD\\t%s\\t%s\\t%zu\\t%zu\\n", ${JSON.stringify(target.name)}, ${JSON.stringify(field)}, offsetof(${target.cpp}, ${cpp_identifier(field)}), sizeof(${target.cpp}::${cpp_identifier(field)}));`,
      );
    }
  }
  for (const unit of units) {
    const realm = sanitize_namespace(unit.module.realm);
    for (const [name, constant] of unit.module.consts) {
      if (constant.type === undefined) continue;
      if (constant.is_static) continue;
      lines.push(`  std::printf("VALUE\\t%s\\t%zu\\t%zu\\n", ${JSON.stringify(`${realm}::${name}`)}, sizeof(${realm}::${cpp_identifier(name)}), alignof(${realm}::${cpp_identifier(name)}));`);
    }
    for (const [name, fn] of unit.module.functions) {
      if (fn.is_extern) continue;
      const result_type = cpp_type_of(fn.result);
      const result_size = result_type === "void" ? "0" : `sizeof(${result_type})`;
      const param_terms = fn.params.map((param) => `sizeof(${cpp_type_of(param.type)})`);
      const params_size = param_terms.length === 0 ? "0" : param_terms.join(" + ");
      const signature = `${result_type}(${fn.params.map((param) => cpp_type_of(param.type)).join(", ")})`;
      lines.push(
        `  std::printf("FUNCTION\\t%s\\t%zu\\t%zu\\t%zu\\t%zu\\n", ${JSON.stringify(`${realm}::${name}`)}, ${result_size}, ${params_size}, (${result_size} + ${params_size}), sizeof(std::function<${signature}>));`,
      );
    }
  }
  lines.push("  return 0;");
  lines.push("}");
  return lines.join("\n");
}

export interface LayoutOptions {
  readonly compiler?: string;
  readonly cache_dir?: string;
  readonly timeout_ms?: number;
}

export function compute_layout(
  units: readonly ProgramUnit[],
  entry: ModuleInfo,
  options: LayoutOptions = {},
): LayoutTable {
  const source = probe_source(units, entry);
  if (options.cache_dir !== undefined) {
    const cached = read_cache(options.cache_dir, source);
    if (cached !== undefined) return cached;
  }
  const compiler = options.compiler ?? "g++";
  const dir = options.cache_dir ?? join(process.cwd(), ".pengu-cache", "layout");
  mkdirSync(dir, { recursive: true });
  const cpp_path = join(dir, "layout.cpp");
  const binary_path = join(dir, "layout");
  writeFileSync(cpp_path, source);
  writeFileSync(join(dir, "pengu_rt.hpp"), RUNTIME_HEADER);
  const compiled = spawnSync(compiler, ["-std=c++20", "-O0", cpp_path, "-o", binary_path], {
    encoding: "utf8",
    timeout: options.timeout_ms ?? 60_000,
  });
  if (compiled.status !== 0) {
    const detail = (compiled.stderr ?? "").split("\n").slice(0, 6).join("\n");
    return { available: false, message: `no se pudo compilar la medición con «${compiler}»:\n${detail}`, types: new Map(), values: new Map(), functions: new Map() };
  }
  const ran = spawnSync(binary_path, [], { encoding: "utf8", timeout: options.timeout_ms ?? 30_000 });
  if (ran.status !== 0) {
    return { available: false, message: `la medición falló al ejecutarse: ${ran.stderr ?? ""}`, types: new Map(), values: new Map(), functions: new Map() };
  }
  const table = parse_probe(ran.stdout ?? "");
  if (options.cache_dir !== undefined) write_cache(options.cache_dir, source, table);
  return table;
}

export function parse_probe(output: string): LayoutTable {
  const types = new Map<string, TypeLayout>();
  const values = new Map<string, ValueLayout>();
  const functions = new Map<string, FunctionLayout>();
  for (const line of output.split("\n")) {
    const parts = line.split("\t");
    if (parts[0] === "FIELD" && parts.length >= 5) {
      const type = types.get(parts[1] ?? "");
      if (type === undefined) continue;
      const fields = [
        ...type.fields,
        { name: parts[2] ?? "", offset: Number(parts[3] ?? "0"), size: Number(parts[4] ?? "0") },
      ];
      types.set(type.name, { ...type, fields });
      continue;
    }
    if (parts[0] === "VALUE" && parts.length >= 4) {
      values.set(parts[1] ?? "", { name: parts[1] ?? "", size: Number(parts[2] ?? "0"), align: Number(parts[3] ?? "0") });
      continue;
    }
    if (parts[0] === "FUNCTION" && parts.length >= 6) {
      functions.set(parts[1] ?? "", {
        name: parts[1] ?? "",
        result: Number(parts[2] ?? "0"),
        params: Number(parts[3] ?? "0"),
        total: Number(parts[4] ?? "0"),
        callable: Number(parts[5] ?? "0"),
      });
      continue;
    }
    if (parts[0] !== "SIZE" || parts.length < 4) continue;
    const name = parts[1] ?? "";
    const size = Number(parts[2] ?? "0");
    const align = Number(parts[3] ?? "0");
    if (name === "") continue;
    const previous = types.get(name);
    types.set(name, { name, size, align, fields: previous?.fields ?? [] });
  }
  return { available: true, message: undefined, types, values, functions };
}

const CACHE_FILE = "layout.json";

function read_cache(dir: string, source: string): LayoutTable | undefined {
  try {
    const raw = readFileSync(join(dir, CACHE_FILE), "utf8");
    const parsed = JSON.parse(raw) as {
      source: string;
      types: [string, TypeLayout][];
      values?: [string, ValueLayout][];
      functions?: [string, FunctionLayout][];
    };
    if (parsed.source !== source) return undefined;
    return {
      available: true,
      message: undefined,
      types: new Map(parsed.types),
      values: new Map(parsed.values ?? []),
      functions: new Map(parsed.functions ?? []),
    };
  } catch {
    return undefined;
  }
}

function write_cache(dir: string, source: string, table: LayoutTable): void {
  mkdirSync(dir, { recursive: true });
  writeFileSync(
    join(dir, CACHE_FILE),
    JSON.stringify({ source, types: [...table.types], values: [...table.values], functions: [...table.functions] }),
  );
  void dirname;
}
