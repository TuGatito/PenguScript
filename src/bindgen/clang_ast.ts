// Lectura del AST de clang para generar enlaces.
//
// `clang++ -Xclang -ast-dump=json -fsyntax-only cabecera` produce un
// árbol JSON; aquí extraemos funciones, records (con bitfields),
// enums y typedefs.

import { spawnSync } from "node:child_process";

export interface NativeParam {
  readonly name: string;
  readonly type: string;
}

export interface NativeFunction {
  readonly name: string;
  readonly params: readonly NativeParam[];
  readonly result: string;
  readonly variadic: boolean;
}

export interface NativeField {
  readonly name: string;
  readonly type: string;
  readonly bits: number | undefined;
}

export interface NativeRecord {
  readonly name: string;
  readonly is_union: boolean;
  readonly fields: readonly NativeField[];
}

export interface NativeVariant {
  readonly name: string;
  readonly value: number;
}

export interface NativeEnum {
  readonly name: string;
  readonly variants: readonly NativeVariant[];
}

export interface NativeTypedef {
  readonly name: string;
  readonly type: string;
  readonly function_pointer: boolean;
}

export interface NativeHeader {
  readonly functions: readonly NativeFunction[];
  readonly records: readonly NativeRecord[];
  readonly enums: readonly NativeEnum[];
  readonly typedefs: readonly NativeTypedef[];
  readonly skipped: readonly string[];
}

interface AstNode {
  readonly id?: string;
  readonly kind?: string;
  readonly name?: string;
  readonly type?: { readonly qualType?: string };
  readonly decl?: { readonly id?: string; readonly kind?: string };
  readonly isImplicit?: boolean;
  readonly isUnion?: boolean;
  readonly tagUsed?: string;
  readonly completeDefinition?: boolean;
  readonly isBitfield?: boolean;
  readonly value?: string;
  readonly variadic?: boolean;
  readonly inner?: readonly AstNode[];
}

export function find_clang(): string | undefined {
  for (const candidate of ["clang++", "clang"]) {
    const probe = spawnSync(candidate, ["--version"], { encoding: "utf8" });
    if (probe.status === 0) return candidate;
  }
  return undefined;
}

export function dump_ast(header: string, clang: string, include_dirs: readonly string[] = []): unknown {
  const includes = include_dirs.flatMap((dir) => ["-I", dir]);
  const dump = spawnSync(
    clang,
    ["-x", "c++-header", "-std=c++20", ...includes, "-Xclang", "-ast-dump=json", "-fsyntax-only", header],
    { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 },
  );
  if (dump.status !== 0) {
    throw new Error((dump.stderr ?? "").trim() || "clang no pudo analizar la cabecera");
  }
  const text = (dump.stdout ?? "").trim();
  if (text.length === 0) throw new Error("clang no devolvió ningún AST");
  return JSON.parse(text);
}

function is_node(value: unknown): value is AstNode {
  return typeof value === "object" && value !== null;
}

function children(node: AstNode): readonly AstNode[] {
  return node.inner ?? [];
}

export function collect_functions(ast: unknown): NativeFunction[] {
  const functions: NativeFunction[] = [];
  visit_nodes(ast, (node) => {
    if (node.kind !== "FunctionDecl" || node.name === undefined || node.isImplicit === true) return;
    const qual = node.type?.qualType ?? "";
    if (!qual.includes("(")) return;
    if (node.name.startsWith("operator")) return;
    const params: NativeParam[] = [];
    for (const child of children(node)) {
      if (child.kind !== "ParmVarDecl") continue;
      params.push({ name: child.name ?? `arg${params.length}`, type: child.type?.qualType ?? "int" });
    }
    functions.push({
      name: node.name,
      params,
      result: extract_result(qual),
      variadic: qual.includes("..."),
    });
  });
  return functions;
}

export function collect_header(ast: unknown): NativeHeader {
  const skipped: string[] = [];
  const enums_by_id = new Map<string, AstNode>();
  const typedef_nodes: AstNode[] = [];

  visit_nodes(ast, (node) => {
    if (node.kind === "EnumDecl" && node.id !== undefined) enums_by_id.set(node.id, node);
    if (node.kind === "TypedefDecl") typedef_nodes.push(node);
  });

  const record_names = new Map<string, string>();
  const records: NativeRecord[] = [];
  visit_nodes(ast, (node) => {
    if (node.kind !== "RecordDecl" && node.kind !== "CXXRecordDecl") return;
    if (node.completeDefinition !== true || node.name === undefined) return;
    if (node.id !== undefined) record_names.set(node.id, node.name);
    if (node.name.length === 0) return;
    const fields: NativeField[] = [];
    for (const child of children(node)) {
      if (child.kind !== "FieldDecl" || child.name === undefined) continue;
      fields.push({
        name: child.name,
        type: child.type?.qualType ?? "int",
        bits: child.isBitfield === true ? constant_value(child) : undefined,
      });
    }
    records.push({ name: node.name, is_union: node.isUnion === true || node.tagUsed === "union", fields });
  });

  // Un enum anónimo toma el nombre del typedef que lo envuelve
  // (`typedef enum { … } Color;`); un record con typedef se convierte
  // en un alias cuando el nombre visible es distinto del tag.
  const enum_names = new Map<string, string>();
  const typedefs: NativeTypedef[] = [];
  for (const node of typedef_nodes) {
    const name = node.name;
    if (name === undefined || name.startsWith("__")) continue;
    const qual = node.type?.qualType ?? "";
    const tag = children(node).find((child) => child.kind === "EnumType" || child.kind === "RecordType");
    if (tag?.kind === "EnumType" && tag.decl?.id !== undefined) {
      enum_names.set(tag.decl.id, name);
      continue;
    }
    if (tag?.kind === "RecordType") {
      const record_name = tag.decl?.id === undefined ? undefined : record_names.get(tag.decl.id);
      if (record_name !== undefined && record_name !== name) {
        typedefs.push({ name, type: `struct ${record_name}`, function_pointer: false });
      }
      continue;
    }
    typedefs.push({ name, type: qual, function_pointer: /\(\s*\*/.test(qual) });
  }

  const enums: NativeEnum[] = [];
  visit_nodes(ast, (node) => {
    if (node.kind !== "EnumDecl") return;
    const name = node.name !== undefined && node.name.length > 0
      ? node.name
      : (node.id === undefined ? undefined : enum_names.get(node.id));
    if (name === undefined) {
      skipped.push("un enum anónimo sin typedef");
      return;
    }
    const variants: NativeVariant[] = [];
    let next = 0;
    for (const child of children(node)) {
      if (child.kind !== "EnumConstantDecl" || child.name === undefined) continue;
      const explicit = constant_value(child);
      const value = explicit ?? next;
      next = value + 1;
      variants.push({ name: child.name, value });
    }
    enums.push({ name, variants });
  });

  return { functions: collect_functions(ast), records, enums, typedefs, skipped };
}

function visit_nodes(ast: unknown, visit: (node: AstNode) => void): void {
  if (!is_node(ast)) return;
  const walk = (node: AstNode): void => {
    visit(node);
    for (const child of children(node)) walk(child);
  };
  walk(ast);
}

// El valor de un enumerador o el ancho de un bitfield vienen en el
// primer descendiente con `value` (`ConstantExpr` o `IntegerLiteral`).
function constant_value(node: AstNode): number | undefined {
  for (const child of children(node)) {
    if (child.value !== undefined && /^-?\d+$/.test(child.value)) return Number(child.value);
    const nested = constant_value(child);
    if (nested !== undefined) return nested;
  }
  return node.value !== undefined && /^-?\d+$/.test(node.value) ? Number(node.value) : undefined;
}

// El tipo de retorno es lo que queda antes del primer paréntesis.
function extract_result(qual_type: string): string {
  const index = qual_type.indexOf("(");
  if (index < 0) return "void";
  return qual_type.slice(0, index).trim() || "void";
}
