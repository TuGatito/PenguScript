// Lectura del AST de clang para generar enlaces.
//
// `clang++ -Xclang -ast-dump=json -fsyntax-only cabecera` produce un
// árbol JSON; aquí solo extraemos las funciones declaradas.

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

interface AstNode {
  readonly kind?: string;
  readonly name?: string;
  readonly type?: { readonly qualType?: string };
  readonly isImplicit?: boolean;
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

export function collect_functions(ast: unknown): NativeFunction[] {
  const functions: NativeFunction[] = [];

  function visit(node: AstNode): void {
    if (node.kind === "FunctionDecl" && node.name !== undefined && node.isImplicit !== true) {
      const qual = node.type?.qualType ?? "";
      if (!qual.includes("(")) {
        // Los punteros a función no se enlazan por ahora.
      } else if (node.name.startsWith("operator")) {
        // Operadores y métodos no forman parte de la ABI simple.
      } else {
        const params: NativeParam[] = [];
        for (const child of node.inner ?? []) {
          if (child.kind !== "ParmVarDecl") continue;
          params.push({ name: child.name ?? `arg${params.length}`, type: child.type?.qualType ?? "int" });
        }
        functions.push({
          name: node.name,
          params,
          result: extract_result(qual),
          variadic: qual.includes("..."),
        });
      }
    }
    for (const child of node.inner ?? []) visit(child);
  }

  if (is_node(ast)) visit(ast as AstNode);
  return functions;
}

// El tipo de retorno es lo que queda antes del primer paréntesis.
function extract_result(qual_type: string): string {
  const index = qual_type.indexOf("(");
  if (index < 0) return "void";
  return qual_type.slice(0, index).trim() || "void";
}
