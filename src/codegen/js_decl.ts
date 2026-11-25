// Declaraciones del emisor JavaScript: funciones y constantes de un realm.
//
// Las funciones se emiten como `export function` (hoisted, así que el orden
// no importa) y las constantes como `const`/`let` en orden de dependencias
// (JS evalúa los módulos de arriba abajo y una referencia adelantada sería
// un error de zona muerta temporal).

import type { FunctionDecl } from "../frontend/ast_decl.ts";
import type { ProgramUnit } from "./cpp_module.ts";
import {
  declare_local,
  line,
  pop_scope,
  push_scope,
  symbol_name,
  with_fresh_locals,
  type JsContext,
} from "./js_context.ts";
import { free_operator_name, js_identifier } from "./js_names.ts";
import { future_inner } from "../semantic/types.ts";
import { capture_lines, emit_expr, emit_value_block } from "./js_expr.ts";

// Cuerpo de una función de PenguScript. Los genéricos no se emiten: en JS los
// tipos no existen y las funciones son polimórficas por naturaleza.
export function emit_function(g: JsContext, unit: ProgramUnit, decl: FunctionDecl): void {
  const info = unit.module.functions.get(decl.name);
  // Un operador libre se exporta como `op_mul`, `op_eq`… (§4.4).
  const name = symbol_name(g, free_operator_name(decl.name) ?? decl.name);
  const params = decl.params.map((param) => {
    const param_name = js_identifier(param.name);
    if (param.variadic) return `...${param_name}`;
    if (param.default_value !== undefined) return `${param_name} = ${emit_expr(g, param.default_value)}`;
    return param_name;
  });

  const saved_self = g.self_expression;
  const saved_return = g.return_type;
  const saved_async = g.await_depth;
  // El cuerpo devuelve `T`, no `future<T>`: `await` desenvuelve el futuro y
  // la función `async` lo vuelve a envolver al salir (una `Promise`).
  const result = info === undefined ? undefined : future_inner(info.result) ?? info.result;
  g.self_expression = undefined;
  g.return_type = result;
  g.await_depth = decl.is_async ? saved_async + 1 : 0;
  const file = g.file;
  const text = with_fresh_locals(g, () => {
    push_scope(g);
    for (const param of decl.params) declare_local(g, param.name);
    return capture_lines(g, () => {
      line(g, `export ${decl.is_async ? "async " : ""}function ${name}(${params.join(", ")}) {`);
      g.indent += 1;
      emit_value_block(g, decl.body, result);
      g.indent -= 1;
      line(g, "}");
    });
  });
  g.self_expression = saved_self;
  g.return_type = saved_return;
  g.await_depth = saved_async;
  file.functions.push(text);
}

// Constante de módulo: `const` salvo que sea mutable (`let`).
export function emit_constant(g: JsContext, unit: ProgramUnit, name: string): void {
  const info = unit.module.consts.get(name);
  const decl = info?.decl;
  if (info === undefined || decl === undefined) return;
  const local = symbol_name(g, name);
  const value = emit_expr(g, decl.value, info.type);
  const keyword = info.mutable ? "let" : "const";
  // Las constantes viven en la cabecera del módulo, sin importar desde qué
  // profundidad de llamada se emitan.
  g.file.lines.push(`export ${keyword} ${local} = ${value};`);
}

// Constantes de un realm en orden de dependencias (una constante puede usar
// otra declarada más abajo en el archivo, y en C++ el backend las reordena).
export function emit_constants(g: JsContext, unit: ProgramUnit): void {
  const pending = [...unit.module.consts.keys()];
  const emitted = new Set<string>();
  const visiting = new Set<string>();
  const order: string[] = [];

  const visit = (name: string): void => {
    if (emitted.has(name) || visiting.has(name)) return;
    const info = unit.module.consts.get(name);
    if (info?.decl === undefined) {
      emitted.add(name);
      return;
    }
    visiting.add(name);
    const references = new Set<string>();
    collect_idents(info.decl.value, references);
    for (const reference of references) {
      if (unit.module.consts.has(reference)) visit(reference);
    }
    visiting.delete(name);
    emitted.add(name);
    order.push(name);
  };

  for (const name of pending) visit(name);
  for (const name of order) emit_constant(g, unit, name);
}

// Identificadores mencionados en una expresión (para ordenar constantes).
function collect_idents(value: unknown, out: Set<string>): void {
  if (value === null || typeof value !== "object") return;
  if (Array.isArray(value)) {
    for (const item of value) collect_idents(item, out);
    return;
  }
  const record = value as Record<string, unknown>;
  if (record.kind === "ident" && typeof record.name === "string") {
    out.add(record.name);
    return;
  }
  if (record.kind === "path") return;
  for (const key of Object.keys(record)) {
    if (key === "span" || key === "kind") continue;
    collect_idents(record[key], out);
  }
}
