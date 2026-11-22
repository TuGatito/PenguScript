// Ensamblado de varios módulos PenguScript en un único archivo C++20.
//
// Cada módulo se emite dentro de su `namespace <realm>`; los tipos de
// otros módulos se cualifican con su realm. El `main` del ejecutable
// llama a `main` del módulo de entrada.

import type { DiagnosticSink } from "../diagnostics/sink.ts";
import type { ExprNode } from "../frontend/ast_expr.ts";
import type { Program } from "../frontend/ast.ts";
import type { ModuleInfo } from "../semantic/module_info.ts";
import type { PenguType } from "../semantic/types.ts";
import type { MethodTarget } from "../semantic/type_env.ts";
import { cpp_type, sanitize_namespace } from "./cpp_types.ts";
import type { TypeRealms } from "./cpp_types.ts";
import { make_gen_context, line } from "./cpp_context.ts";
import { emit_const_declarations, emit_rest_declarations, emit_type_declarations } from "./cpp_decl.ts";

export interface ProgramUnit {
  readonly program: Program;
  readonly module: ModuleInfo;
  readonly types: ReadonlyMap<ExprNode, PenguType>;
  // Nodo del miembro → `realm::nombre` para métodos enhechizados.
  readonly member_targets: ReadonlyMap<ExprNode, MethodTarget>;
  // Alias de `invoke` del módulo → realm importado.
  readonly external_realms: ReadonlyMap<string, string>;
  // Símbolo importado de forma selectiva → realm de origen.
  readonly selective_realms: ReadonlyMap<string, string>;
  // Alias de `invoke` → módulo importado.
  readonly external_modules: ReadonlyMap<string, ModuleInfo>;
}

export interface GeneratedModule {
  readonly code: string;
  readonly has_main: boolean;
}

// Reúne los tipos de usuario de todos los módulos para cualificarlos.
export function collect_type_realms(units: readonly ProgramUnit[]): TypeRealms {
  const realms = new Map<string, string>();
  for (const unit of units) {
    const realm = sanitize_namespace(unit.module.realm);
    for (const name of unit.module.env.runes.keys()) if (!realms.has(name)) realms.set(name, realm);
    for (const name of unit.module.env.omens.keys()) if (!realms.has(name)) realms.set(name, realm);
    for (const name of unit.module.env.aliases.keys()) if (!realms.has(name)) realms.set(name, realm);
  }
  return realms;
}

export interface GenerateOptions {
  /** Emite solo las declaraciones de tipo (sin cuerpos ni constantes). */
  readonly declarations_only?: boolean;
  // `false` genera solo declaraciones (medición de tamaños).
  readonly emit_main?: boolean;
}

export function generate_program(
  units: readonly ProgramUnit[],
  entry: ModuleInfo,
  sink: DiagnosticSink,
  options: GenerateOptions = {},
): GeneratedModule {
  const type_realms = collect_type_realms(units);
  const header: string[] = ['#include "pengu_rt.hpp"', "#include <cmath>", ""];
  const body: string[] = [];

  for (const unit of units) {
    const g = make_gen_context(
      unit.module,
      unit.types,
      sink,
      type_realms,
      unit.external_realms,
      unit.selective_realms,
      unit.member_targets,
      unit.external_modules,
    );
    const realm = sanitize_namespace(unit.module.realm);
    body.push(`namespace ${realm} {`);
    g.lines = body;
    g.indent = 1;
    emit_type_declarations(g, unit.program.decls);
    g.indent = 0;
    body.push(`}  // namespace ${realm}`);
    body.push("");
    // `std::hash` sintetizado: en el ámbito global y antes de las
    // funciones que usan contenedores `unordered_*`.
    for (const extra of g.std_extra) body.push(extra);
    if (g.std_extra.length > 0) body.push("");
    if (options.declarations_only !== true) {
      body.push(`namespace ${realm} {`);
      g.lines = body;
      g.indent = 1;
      emit_rest_declarations(g, unit.program.decls);
      g.indent = 0;
      body.push(`}  // namespace ${realm}`);
      body.push("");
    } else {
      // En el sondeo de tamaños solo hacen falta las constantes: los cuerpos
      // de las funciones no cambian `sizeof` y sí cambian el hash de la caché.
      body.push(`namespace ${realm} {`);
      g.lines = body;
      g.indent = 1;
      emit_const_declarations(g, unit.program.decls);
      g.indent = 0;
      body.push(`}  // namespace ${realm}`);
      body.push("");
    }
  }

  const main = entry.functions.get("main");
  if (main !== undefined && options.emit_main !== false) {
    const realm = sanitize_namespace(entry.realm);
    body.push("int main(int argc, char** argv) {");
    body.push("  ::pengu::set_args(argc, argv);");
    body.push("  try {");
    const result = cpp_type(main.result, type_realms);
    if (result === "void") {
      body.push(`    ${realm}::main();`);
      body.push("    return 0;");
    } else if (result === "int") {
      body.push(`    return ${realm}::main();`);
    } else {
      body.push(`    ${realm}::main();`);
      body.push("    return 0;");
    }
    body.push("  } catch (const std::exception& error) {");
    body.push('    std::fprintf(stderr, "panic: %s\\n", error.what());');
    body.push("    return 1;");
    body.push("  }");
    body.push("}");
    body.push("");
  }

  return { code: [...header, ...body].join("\n"), has_main: main !== undefined };
}

export function main_result_type(module: ModuleInfo): PenguType | undefined {
  return module.functions.get("main")?.result;
}

export function cpp_main_return(module: ModuleInfo): string {
  const result = main_result_type(module);
  return result ? cpp_type(result) : "void";
}
