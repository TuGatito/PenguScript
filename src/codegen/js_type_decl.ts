// Declaraciones de tipo del emisor JavaScript: `rune`, `omen`, `seal` y `echo`.
//
// Un `rune` sin comportamiento (ni `heir`, ni constructor, ni destructor, ni
// métodos) se emite como fábrica de objeto literal; en cuanto tiene
// comportamiento se emite como `class` de ES2022. La decisión es global al
// programa (`collect_class_runes`), porque el archivo que construye un valor
// puede no ser el que declara el tipo.
//
// `seal` y `echo` no existen en runtime: se borran y sus constructores se
// resuelven en el punto de uso.

import type { DeclNode, MethodDecl, OmenDecl, RuneDecl } from "../frontend/ast_decl.ts";
import type { ExprNode } from "../frontend/ast_expr.ts";
import type { PenguType } from "../semantic/types.ts";
import { omen_methods_of } from "../semantic/module_info.ts";
import type { ProgramUnit } from "./cpp_module.ts";
import { is_type_decl, order_type_decls } from "./cpp_type_order.ts";
import {
  declare_local,
  js_error,
  line,
  pop_scope,
  push_scope,
  symbol_name,
  type JsContext,
} from "./js_context.ts";
import { js_identifier } from "./js_names.ts";
import { emit_expr, emit_value_block } from "./js_expr.ts";
import { emit_statement } from "./js_stmt.ts";

// Clave global de un tipo: `realm::Nombre`.
export function type_key(realm: string, name: string): string {
  return `${realm}::${name}`;
}

// ¿Qué runes necesitan `class`? Se decide sobre todo el grafo, nunca sobre el
// `TypeEnv` local (§2.5): constructor, destructor, padre o métodos.
export function collect_class_runes(units: readonly ProgramUnit[]): ReadonlySet<string> {
  const classes = new Set<string>();
  for (const unit of units) {
    const realm = unit.module.realm;
    for (const decl of unit.program.decls) {
      if (decl.kind !== "rune_decl") continue;
      const info = unit.module.env.runes.get(decl.name);
      if (
        decl.parent !== undefined ||
        decl.constructor !== undefined ||
        decl.destructor !== undefined ||
        (info?.methods.size ?? 0) > 0
      ) {
        classes.add(type_key(realm, decl.name));
      }
    }
  }
  return classes;
}

export function is_class_rune(g: JsContext, realm: string, name: string): boolean {
  return g.class_runes.has(type_key(realm, name));
}

// Todas las declaraciones de tipo de una unidad, en orden de dependencias.
export function emit_type_decls(g: JsContext, unit: ProgramUnit): void {
  const decls = unit.program.decls.filter(is_type_decl);
  for (const decl of order_type_decls(decls)) emit_type_decl(g, unit, decl);
}

function emit_type_decl(g: JsContext, unit: ProgramUnit, decl: DeclNode): void {
  switch (decl.kind) {
    case "rune_decl":
      emit_rune(g, unit, decl);
      return;
    case "omen_decl":
      emit_omen(g, unit, decl);
      emit_free_methods(g, unit, decl.name);
      return;
    case "seal_decl":
    case "echo_decl":
      // Newtypes y alias: costo cero, no llegan al runtime, pero sus métodos
      // sí existen como funciones libres (`UserId__label`).
      emit_free_methods(g, unit, decl.name);
      return;
    case "meld_decl":
      js_error(
        g,
        "`meld` (uniones al estilo C) todavía no se emite a JavaScript: solo tiene sentido con `--target cpp`",
        decl.span,
      );
      return;
    default:
      return;
  }
}

// `rune Punto x: double y: double` → fábrica de objeto literal.
function emit_rune(g: JsContext, unit: ProgramUnit, decl: RuneDecl): void {
  const realm = unit.module.realm;
  if (is_class_rune(g, realm, decl.name)) {
    emit_rune_class(g, unit, decl);
    return;
  }
  const name = symbol_name(g, decl.name);
  const params = decl.fields.map((field) => {
    const param = js_identifier(field.name);
    if (field.default_value === undefined) return param;
    return `${param} = ${emit_expr(g, field.default_value)}`;
  });
  const fields = decl.fields.map((field) => js_identifier(field.name));
  line(g, `export function ${name}(${params.join(", ")}) {`);
  g.indent += 1;
  line(g, `return { ${fields.join(", ")} };`);
  g.indent -= 1;
  line(g, "}");
}

// `rune` con comportamiento → clase ES2022.
function emit_rune_class(g: JsContext, unit: ProgramUnit, decl: RuneDecl): void {
  const info = unit.module.env.runes.get(decl.name);
  const name = symbol_name(g, decl.name);
  const parent = info?.parent === undefined ? undefined : symbol_name(g, info.parent);
  const heritage = parent === undefined ? "" : ` extends ${parent}`;
  line(g, `export class ${name}${heritage} {`);
  g.indent += 1;

  const saved_self = g.self_expression;
  g.self_expression = "this";

  if (decl.constructor !== undefined) {
    emit_constructor(g, decl, parent !== undefined);
  } else {
    emit_synthetic_constructor(g, decl, parent !== undefined);
  }
  emit_clone(g, unit, decl);
  if (decl.destructor !== undefined) emit_destroy(g, decl);

  g.self_expression = saved_self;
  g.indent -= 1;
  line(g, "}");
  emit_rune_methods(g, unit, decl);
}

function emit_constructor(g: JsContext, decl: RuneDecl, has_parent: boolean): void {
  const constructor = decl.constructor;
  if (constructor === undefined) return;
  const params = constructor.params.map((param) => {
    const param_name = js_identifier(param.name);
    if (param.default_value === undefined) return param_name;
    return `${param_name} = ${emit_expr(g, param.default_value)}`;
  });
  line(g, `constructor(${params.join(", ")}) {`);
  g.indent += 1;
  push_scope(g);
  for (const param of constructor.params) declare_local(g, param.name);

  // `parent(...)` es la primera sentencia del constructor y en C++ es un
  // inicializador de base: en JS tiene que ser `super(...)` antes de tocar
  // `this`.
  const statements = [...constructor.body.statements];
  const first = statements[0];
  const parent_call =
    first !== undefined && first.kind === "expr_stmt" && first.expr.kind === "parent_call"
      ? first.expr
      : undefined;
  if (parent_call !== undefined) {
    line(g, `${emit_expr(g, parent_call)};`);
    statements.shift();
  } else if (has_parent) {
    line(g, "super();");
  }

  const field_names = new Set(decl.fields.map((field) => field.name));
  const param_names = new Set(constructor.params.map((param) => param.name));
  // Los campos con valor por defecto se inicializan antes de las asignaciones
  // del constructor del usuario (§2.5); los que reciben un parámetro del mismo
  // nombre se asignan solos, como en C++ (lista de inicialización).
  for (const field of decl.fields) {
    if (field.default_value === undefined || param_names.has(field.name)) continue;
    const value = emit_expr(g, field.default_value);
    line(g, `this.${js_identifier(field.name)} = ${masked(field, value)};`);
  }
  for (const param of constructor.params) {
    if (!field_names.has(param.name)) continue;
    const name = js_identifier(param.name);
    const field = decl.fields.find((candidate) => candidate.name === param.name);
    const value = field === undefined ? name : masked(field, name);
    line(g, `this.${name} = ${value};`);
  }
  for (const statement of statements) emit_statement(g, statement);
  pop_scope(g);
  g.indent -= 1;
  line(g, "}");
}

function emit_synthetic_constructor(g: JsContext, decl: RuneDecl, has_parent: boolean): void {
  const params = decl.fields.map((field) => {
    const param = js_identifier(field.name);
    if (field.default_value === undefined) return param;
    return `${param} = ${emit_expr(g, field.default_value)}`;
  });
  line(g, `constructor(${params.join(", ")}) {`);
  g.indent += 1;
  // Sin `constructor` propio, las asignaciones de campo son la construcción
  // agregada que ya hace C++.
  if (has_parent) line(g, "super();");
  for (const field of decl.fields) {
    const local = js_identifier(field.name);
    line(g, `this.${local} = ${masked(field, local)};`);
  }
  g.indent -= 1;
  line(g, "}");
}

// Campos `bits: N` se enmascaran en cada escritura (§2.9).
function masked(field: RuneDecl["fields"][number], value: string): string {
  if (field.bits === undefined) return value;
  const width = field.bits;
  const bits = width >= 32 ? 0xffffffff : (2 ** width - 1) >>> 0;
  return `(${value}) & ${bits}`;
}

// Métodos `enchanting` del rune, en el orden en que se declararon.
function methods_of(unit: ProgramUnit, target: string): readonly MethodDecl[] {
  const methods: MethodDecl[] = [];
  for (const decl of unit.program.decls) {
    if (decl.kind !== "enchanting_decl" || decl.target !== target) continue;
    for (const method of decl.methods) methods.push(method);
  }
  return methods;
}

// PenguScript no tiene despacho virtual: una llamada se resuelve con el tipo
// estático del receptor. Por eso los métodos de un rune se emiten como
// funciones libres (`Animal__describir(self, …)`) y no como métodos de la
// clase: `extends` solo aporta datos, `_clone` y el constructor heredado.
function emit_rune_methods(g: JsContext, unit: ProgramUnit, decl: RuneDecl): void {
  for (const method of methods_of(unit, decl.name)) {
    emit_rune_method(g, unit, decl.name, method);
  }
}

function emit_rune_method(
  g: JsContext,
  unit: ProgramUnit,
  base: string,
  method: MethodDecl,
): void {
  const info = method_info(unit, method);
  const exported = free_method_export(
    base,
    method.operator === undefined ? method.name : operator_method_name(method.operator),
  );
  symbol_name(g, method.operator === undefined ? method.name : method.operator);
  const params = method.params.map((param) => {
    const param_name = js_identifier(param.name);
    if (param.variadic) return `...${param_name}`;
    if (param.default_value === undefined) return param_name;
    return `${param_name} = ${emit_expr(g, param.default_value)}`;
  });
  const saved_lines = g.file.lines;
  const saved_indent = g.indent;
  const saved_self = g.self_expression;
  const saved_return = g.return_type;
  g.file.lines = [];
  g.indent = 0;
  g.self_expression = "self";
  g.return_type = info?.result;
  push_scope(g);
  declare_local(g, "self");
  for (const param of method.params) declare_local(g, param.name);
  line(g, `export function ${exported}(self${params.length === 0 ? "" : `, ${params.join(", ")}`}) {`);
  g.indent += 1;
  emit_value_block(g, method.body, info?.result);
  g.indent -= 1;
  line(g, "}");
  pop_scope(g);
  const text = g.file.lines.join("\n");
  g.file.lines = saved_lines;
  g.indent = saved_indent;
  g.self_expression = saved_self;
  g.return_type = saved_return;
  g.file.functions.push(text);
}

function method_info(unit: ProgramUnit, method: MethodDecl) {
  for (const decl of unit.program.decls) {
    if (decl.kind !== "enchanting_decl") continue;
    if (!decl.methods.includes(method)) continue;
    return unit.module.env.runes.get(decl.target)?.methods.get(method.name);
  }
  return undefined;
}

// `_clone()` copia campo a campo, incluidos los heredados: `Object.create` no
// inicializa nada y el clon no debe perder los campos del padre (§2.5).
function emit_clone(g: JsContext, unit: ProgramUnit, decl: RuneDecl): void {
  line(g, "_clone() {");
  g.indent += 1;
  line(g, "const copia = Object.create(Object.getPrototypeOf(this));");
  for (const name of inherited_field_names(unit, decl)) {
    line(g, `copia.${js_identifier(name)} = this.${js_identifier(name)};`);
  }
  line(g, "return copia;");
  g.indent -= 1;
  line(g, "}");
}

// Campos del rune y de toda su cadena `heir`.
function inherited_field_names(unit: ProgramUnit, decl: RuneDecl): readonly string[] {
  const names: string[] = [];
  const seen = new Set<string>();
  const walk = (current: RuneDecl): void => {
    if (seen.has(current.name)) return;
    seen.add(current.name);
    if (current.parent !== undefined) {
      const parent = find_rune_decl(unit, current.parent);
      if (parent !== undefined) walk(parent);
    }
    for (const field of current.fields) names.push(field.name);
  };
  walk(decl);
  return names;
}

function find_rune_decl(unit: ProgramUnit, name: string): RuneDecl | undefined {
  for (const decl of unit.program.decls) {
    if (decl.kind === "rune_decl" && decl.name === name) return decl;
  }
  return undefined;
}

// El destructor se emite como `_destroy()`; quién lo llama (con `try/finally`)
// se decide en la fase de posesión (§3).
function emit_destroy(g: JsContext, decl: RuneDecl): void {
  if (decl.destructor === undefined) return;
  line(g, "_destroy() {");
  g.indent += 1;
  emit_value_block(g, decl.destructor, undefined);
  g.indent -= 1;
  line(g, "}");
}

// `omen`: unitarias y `flags` como enteros congelados; algebraicas como
// factorías `{ tag, _0, … }` (§2.6).
function emit_omen(g: JsContext, unit: ProgramUnit, decl: OmenDecl): void {
  void unit;
  const name = symbol_name(g, decl.name);
  const algebraic = decl.variants.some((variant) => variant.payload.length > 0);
  if (!algebraic) {
    const entries = decl.variants.map((variant, index) => {
      const value = omen_value(g, decl, variant.value, index);
      return `${js_identifier(variant.name)}: ${value}`;
    });
    line(g, `export const ${name} = Object.freeze({ ${entries.join(", ")} });`);
    return;
  }
  line(g, `export const ${name} = Object.freeze({`);
  g.indent += 1;
  for (const variant of decl.variants) {
    const variant_name = js_identifier(variant.name);
    if (variant.payload.length === 0) {
      line(g, `${variant_name}: Object.freeze({ tag: "${variant.name}" }),`);
      continue;
    }
    const params = variant.payload.map((_, index) => `_${index}`);
    const fields = params.map((param) => `${param}`);
    line(g, `${variant_name}: (${params.join(", ")}) => ({ tag: "${variant.name}", ${fields.join(", ")} }),`);
  }
  g.indent -= 1;
  line(g, "});");
}

// Valor de una variante unitaria: el explícito si lo hay, si no el índice (o
// la potencia de dos en un `flags omen`).
function omen_value(g: JsContext, decl: OmenDecl, value: ExprNode | undefined, index: number): string {
  if (value !== undefined) return emit_expr(g, value);
  if (decl.is_flags) return String(2 ** index);
  return String(index);
}

// Métodos de `omen`, `seal` y `echo`: JS no tiene tipos nominales para
// colgarlos, así que son funciones libres `<Tipo>__<método>` con el receptor
// primero (§4.1). El nombre se resuelve en el punto de llamada.
export function free_method_name(type_name: string, method: MethodDecl): string {
  const suffix =
    method.operator === undefined ? js_identifier(method.name) : operator_method_name(method.operator);
  return `${js_identifier(type_name)}__${suffix}`;
}

// Nombre exportado de un método libre cuando solo se conoce su nombre.
export function free_method_export(type_name: string, method_name: string): string {
  return `${js_identifier(type_name)}__${js_identifier(method_name)}`;
}

function emit_free_methods(g: JsContext, unit: ProgramUnit, type_name: string): void {
  for (const method of methods_of(unit, type_name)) {
    emit_free_method(g, unit, type_name, method);
  }
}

function emit_free_method(
  g: JsContext,
  unit: ProgramUnit,
  type_name: string,
  method: MethodDecl,
): void {
  const exported = symbol_name(g, free_method_name(type_name, method));
  const result = free_method_result(unit, type_name, method);
  const params = method.params.map((param) => {
    const param_name = js_identifier(param.name);
    if (param.variadic) return `...${param_name}`;
    if (param.default_value === undefined) return param_name;
    return `${param_name} = ${emit_expr(g, param.default_value)}`;
  });
  push_scope(g);
  declare_local(g, "self");
  for (const param of method.params) declare_local(g, param.name);
  const saved_self = g.self_expression;
  const saved_return = g.return_type;
  g.self_expression = "self";
  g.return_type = result;
  line(g, `export function ${exported}(self${params.length === 0 ? "" : `, ${params.join(", ")}`}) {`);
  g.indent += 1;
  emit_value_block(g, method.body, result);
  g.indent -= 1;
  line(g, "}");
  g.return_type = saved_return;
  g.self_expression = saved_self;
  pop_scope(g);
}

function free_method_result(
  unit: ProgramUnit,
  type_name: string,
  method: MethodDecl,
): PenguType | undefined {
  const omen = unit.module.env.omens.get(type_name);
  const omen_method = omen === undefined ? undefined : omen_methods_of(omen)?.get(method.name);
  const alias = unit.module.env.aliases.get(type_name);
  return (omen_method ?? alias?.methods.get(method.name))?.result;
}

// Nombre del método de un operador dentro de una clase (`operator +` → `op_add`).
export function operator_method_name(op: string): string {
  return `op_${OPERATOR_NAMES[op] ?? js_identifier(op)}`;
}

const OPERATOR_NAMES: Readonly<Record<string, string>> = {
  "+": "add",
  "-": "sub",
  "*": "mul",
  "/": "div",
  "%": "mod",
  "==": "eq",
  "!=": "ne",
  "<": "lt",
  "<=": "le",
  ">": "gt",
  ">=": "ge",
  "<=>": "cmp",
  "[]": "index",
  "()": "call",
  "+=": "add_assign",
  "-=": "sub_assign",
  "*=": "mul_assign",
  "/=": "div_assign",
  "%=": "mod_assign",
};

// ¿El rune declara un método para este operador? Devuelve su nombre en JS.

// Rune que declara realmente un método: el propio tipo o el primero de su
// cadena `heir` (`PenguScript` no tiene despacho virtual, la llamada se
// resuelve con el tipo estático).
export function rune_method_owner(
  g: JsContext,
  realm: string,
  type_name: string,
  method_name: string,
): { realm: string; type: string; operator?: string } | undefined {
  let current_realm = realm;
  let current_name = type_name;
  const seen = new Set<string>();
  while (!seen.has(`${current_realm}::${current_name}`)) {
    seen.add(`${current_realm}::${current_name}`);
    const rune = g.units.get(current_realm)?.module.env.runes.get(current_name);
    if (rune === undefined) return undefined;
    const info = rune.methods.get(method_name);
    if (info !== undefined) {
      return { realm: current_realm, type: current_name, operator: info.operator };
    }
    const parent = rune.parent;
    if (parent === undefined) return undefined;
    current_name = parent;
  }
  return undefined;
}

// Rune que declara un operador (incluye `<=>` para derivar comparaciones).
export function rune_operator_owner(
  g: JsContext,
  realm: string,
  type_name: string,
  op: string,
): { realm: string; type: string } | undefined {
  let current_realm = realm;
  let current_name = type_name;
  const seen = new Set<string>();
  while (!seen.has(`${current_realm}::${current_name}`)) {
    seen.add(`${current_realm}::${current_name}`);
    const rune = g.units.get(current_realm)?.module.env.runes.get(current_name);
    if (rune === undefined) return undefined;
    for (const info of rune.methods.values()) {
      if (info.operator === op) return { realm: current_realm, type: current_name };
    }
    const parent = rune.parent;
    if (parent === undefined) return undefined;
    current_name = parent;
  }
  return undefined;
}

export function rune_operator_method(
  g: JsContext,
  realm: string,
  type_name: string,
  op: string,
): string | undefined {
  const rune = g.units.get(realm)?.module.env.runes.get(type_name);
  if (rune === undefined) return undefined;
  for (const info of rune.methods.values()) {
    if (info.operator === op) return operator_method_name(op);
  }
  return undefined;
}
