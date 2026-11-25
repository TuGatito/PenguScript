// Enhechizamientos (`enchanting`) sobre tipos incorporados.
//
// JavaScript no tiene resolución de sobrecargas ni un prototipo que respete el
// alcance léxico de los `invoke`, así que cada método se emite como una función
// libre en el realm que lo declara y se resuelve en el punto de llamada con la
// anotación `member_targets` del checker (plan §4.1).
//
// El receptor viaja como primer parámetro. Si el tipo base es de valor
// (`string`, `int`, `double`…) y el método es `mut`, el receptor es una celda
// `rt.Ref` para poder devolver el cambio a la variable del llamante (§4.3); en
// el cuerpo, `@` es `self.value`.

import type { EnchantingDecl, MethodDecl } from "../frontend/ast_decl.ts";
import type { Block } from "../frontend/ast_stmt.ts";
import { STRING_TYPES, is_primitive_type } from "../frontend/ast_type.ts";
import { UNKNOWN, VOID, primitive } from "../semantic/types.ts";
import type { PenguType } from "../semantic/types.ts";
import type { ProgramUnit } from "./cpp_module.ts";
import {
  cross_reference,
  declare_local,
  file_for,
  fresh_name,
  line,
  pop_scope,
  push_scope,
  realm_of_type,
  quiet_type_node,
  with_fresh_locals,
  runtime_name,
  symbol_name_in,
  with_file,
  type JsContext,
} from "./js_context.ts";
import { capture_lines, emit_expr, emit_value_block } from "./js_expr.ts";
import { js_identifier } from "./js_names.ts";
import { emit_jsdoc } from "./js_doc.ts";
import { operator_method_name } from "./js_type_decl.ts";

// Enhechizamientos declarados en un módulo (los `enchanting` del archivo).
export function enchanting_decls(unit: ProgramUnit): readonly EnchantingDecl[] {
  const decls: EnchantingDecl[] = [];
  for (const decl of unit.program.decls) {
    if (decl.kind === "enchanting_decl") decls.push(decl);
  }
  return decls;
}

// Método `name` del enhechizamiento sobre `base`, si existe.
export function enchanting_method(
  unit: ProgramUnit,
  base: string,
  name: string,
): MethodDecl | undefined {
  for (const decl of enchanting_decls(unit)) {
    if (!target_matches(unit, decl.target, base)) continue;
    const method = decl.methods.find((candidate) => candidate.name === name);
    if (method !== undefined) return method;
  }
  return undefined;
}

// Un `echo`/`seal` es transparente en runtime, así que `enchanting Metros`
// sobre `echo Metros = double` enhechiza `double` (§2.8).
function target_matches(unit: ProgramUnit, target: string, base: string): boolean {
  if (target === base) return true;
  const alias = unit.module.env.aliases.get(target)?.target;
  return alias !== undefined && base_name_of(alias) === base;
}

// Nombre exportado del método. En JS no hay sobrecargas, así que un mismo
// nombre sobre varias bases dentro del mismo realm (los enteros de
// `std/integers`, por ejemplo) se desambigua con `<base>__<método>` (§4.5).
export function enchanting_export_name(unit: ProgramUnit, base: string, name: string): string {
  let bases = 0;
  for (const decl of enchanting_decls(unit)) {
    if (decl.methods.some((method) => method.name === name)) bases += 1;
  }
  const collides = bases > 1 || unit.module.functions.has(name) || unit.module.consts.has(name);
  return collides ? `${js_identifier(base)}__${js_identifier(name)}` : js_identifier(name);
}

// Nombre exportado de un operador declarado con `enchanting`
// (`operator +` sobre `Point` → `Point__op_add`).
export function enchanting_operator_export(unit: ProgramUnit, base: string, operator: string): string {
  return `${js_identifier(base)}__${operator_method_name(operator)}`;
}

// Emite (una sola vez) el método y devuelve el nombre local con el que se
// puede llamar desde el archivo activo.
export function ensure_enchanting(
  g: JsContext,
  realm: string,
  base: string,
  name: string,
): string | undefined {
  const unit = g.units.get(realm);
  if (unit === undefined) return undefined;
  const method = enchanting_method(unit, base, name);
  if (method === undefined) return undefined;
  const file = file_for(g, realm);
  const exported = enchanting_export_name(unit, base, name);
  symbol_name_in(file, exported);
  const key = `${realm}\u0000enchant\u0000${base}\u0000${name}`;
  if (g.emitted.has(key)) return exported;
  g.emitted.add(key);
  with_file(g, realm, () => {
    emit_enchanting(g, unit, base, base_type_of(unit, base), method, exported, false);
  });
  return exported;
}

// Operador de un método enhechizado (`operator +` sobre `Point`).
export function ensure_enchanting_operator(
  g: JsContext,
  realm: string,
  base: string,
  operator: string,
): string | undefined {
  const unit = g.units.get(realm);
  if (unit === undefined) return undefined;
  let found: MethodDecl | undefined;
  for (const decl of enchanting_decls(unit)) {
    if (decl.target !== base) continue;
    found = decl.methods.find((method) => method.operator === operator);
    if (found !== undefined) break;
  }
  if (found === undefined) return undefined;
  const file = file_for(g, realm);
  const exported = enchanting_operator_export(unit, base, operator);
  symbol_name_in(file, exported);
  const key = `${realm}\u0000enchant_op\u0000${base}\u0000${operator}`;
  if (g.emitted.has(key)) return exported;
  g.emitted.add(key);
  const method = found;
  with_file(g, realm, () => {
    emit_enchanting(g, unit, base, base_type_of(unit, base), method, exported, true);
  });
  return exported;
}

// ¿El receptor tiene que viajar en una celda? Solo si el tipo base es de valor
// (en JS no hay aliasing para copiarlos) o si el cuerpo reasigna `@`.
export function enchanting_receiver_is_cell(base: PenguType, method: MethodDecl): boolean {
  if (!method.mutable) return false;
  return is_value_base(base) || assigns_self(method.body);
}

// Tipos cuyo valor se copia al pasarlo: cualquier `mut` sobre ellos necesita
// una celda para poder devolver el cambio al llamante.
export function is_value_base(type: PenguType): boolean {
  switch (type.kind) {
    case "primitive":
      return type.name !== "void";
    case "optional":
      return is_value_base(type.inner);
    case "ref":
    case "raw":
      return is_value_base(type.inner);
    case "named":
      // `string` y compañía llegan como primitivos, pero un enhechizamiento
      // puede nombrarlos como tipo simple.
      return is_primitive_type(type.name) || STRING_TYPES.has(type.name);
    default:
      return false;
  }
}

// Tipo base del enhechizamiento a partir de su nombre declarado.
function base_type_of(unit: ProgramUnit, base: string): PenguType {
  const alias = unit.module.env.aliases.get(base);
  if (alias !== undefined) return alias.target;
  if (is_primitive_type(base) || STRING_TYPES.has(base)) return { kind: "primitive", name: base };
  return { kind: "named", name: base, args: [] };
}

function assigns_self(body: Block): boolean {
  let found = false;
  const walk = (value: unknown): void => {
    if (found || value === null || typeof value !== "object") return;
    if (Array.isArray(value)) {
      for (const item of value) walk(item);
      return;
    }
    const record = value as Record<string, unknown>;
    if (record["kind"] === "assign" && Array.isArray(record["targets"])) {
      const targets = record["targets"] as readonly { kind?: string }[];
      if (targets.some((target) => target.kind === "self")) {
        found = true;
        return;
      }
    }
    for (const key of Object.keys(record)) {
      if (key === "span" || key === "kind") continue;
      walk(record[key]);
    }
  };
  walk(body);
  return found;
}

function emit_enchanting(
  g: JsContext,
  unit: ProgramUnit,
  base: string,
  base_type: PenguType,
  method: MethodDecl,
  exported: string,
  operator: boolean,
): void {
  const cell = !operator && enchanting_receiver_is_cell(base_type, method);
  const result = quiet_result(method);
  const params: string[] = [];
  const saved_self = g.self_expression;
  const saved_return = g.return_type;
  const saved_base = g.enchant_base;
  const saved_async = g.await_depth;
  const file = g.file;
  const text = with_fresh_locals(g, () => {
  push_scope(g);
  declare_local(g, "self");
  for (const param of method.params) {
    declare_local(g, param.name);
    const param_name = js_identifier(param.name);
    if (param.variadic) {
      params.push(`...${param_name}`);
    } else if (param.default_value !== undefined) {
      params.push(`${param_name} = ${emit_expr(g, param.default_value)}`);
    } else {
      params.push(param_name);
    }
  }
  g.enchant_base = base;
  g.self_expression = cell ? "self.value" : "self";
  g.return_type = result;
  g.await_depth = method.is_async ? saved_async + 1 : 0;
  return capture_lines(g, () => {
    const signature = params.length === 0 ? "self" : `self, ${params.join(", ")}`;
    emit_jsdoc(g, {
      summary: `${base}.${method.name} — método de enchanting.`,
      params: method.params.map((param) => ({
        name: param.name,
        type: param.type === undefined ? UNKNOWN : quiet_type_node(g, param.type),
      })),
      result: method.result === undefined ? result : doc_result(g, method, result),
    });
    line(g, `export ${method.is_async ? "async " : ""}function ${exported}(${signature}) {`);
    g.indent += 1;
    emit_value_block(g, method.body, result);
    g.indent -= 1;
    line(g, "}");
  });
  });
  g.self_expression = saved_self;
  g.return_type = saved_return;
  g.enchant_base = saved_base;
  g.await_depth = saved_async;
  file.functions.push(text);
}

// Tipo de retorno del método sin pasar por `resolve_type_node`: dentro de un
// `enchanting` genérico el checker ya validó el tipo y resolverlo aquí con el
// entorno del módulo puede emitir diagnósticos espurios (`set<T>` con `T` sin
// `<=>`). Solo interesa distinguir `void` de «produce valor».
// Para documentar, se intenta resolver el tipo declarado; si no, el del
// emisor (los genéricos del propio método quedan como `any`).
function doc_result(g: JsContext, method: MethodDecl, fallback: PenguType | undefined): PenguType | undefined {
  if (method.result === undefined) return fallback;
  const resolved = quiet_type_node(g, method.result);
  return resolved.kind === "any" ? fallback : resolved;
}

function quiet_result(method: MethodDecl): PenguType | undefined {
  const node = method.result;
  if (node === undefined) return undefined;
  if (node.kind === "primitive_type") return node.name === "void" ? VOID : primitive(node.name);
  if (node.kind === "named_type" && node.name === "void") return VOID;
  return UNKNOWN;
}

// Nombre de la base a partir del tipo del receptor (`vector<int>` → `vector`).
export function base_name_of(type: PenguType): string | undefined {
  switch (type.kind) {
    case "primitive":
      return type.name;
    case "named":
      return type.name;
    case "ref":
    case "raw":
      return base_name_of(type.inner);
    case "optional":
      return "optional";
    case "array":
      // `array<T, N>` se enhechiza como `array` en `std/array`.
      return "array";
    default:
      return undefined;
  }
}

// Llamada a un método enhechizado: `xs.sort()` → `sort(xs)` o
// `trim(rt.ref(...))` según el receptor.
export function emit_enchanting_call(
  g: JsContext,
  object: string,
  object_type: PenguType,
  realm: string,
  name: string,
  args: string,
  lvalue: boolean,
): string | undefined {
  const unit = g.units.get(realm);
  // El receptor puede venir envuelto (`optional<T>`, `ref<T>`): se prueban las
  // bases de dentro hacia fuera hasta dar con el bloque `enchanting`.
  const base = candidate_bases(g, object_type).find(
    (candidate) => unit !== undefined && enchanting_method(unit, candidate, name) !== undefined,
  );
  if (base === undefined) return undefined;
  const exported = ensure_enchanting(g, realm, base, name);
  if (exported === undefined) return undefined;
  const local = cross_reference(g, realm, exported);
  const method = unit === undefined ? undefined : enchanting_method(unit, base, name);
  if (method === undefined) return undefined;
  const tail = args.length === 0 ? "" : `, ${args}`;
  if (!enchanting_receiver_is_cell(object_type, method)) return `${local}(${object}${tail})`;
  return cell_call(g, local, object, tail, lvalue);
}

// Último recurso: si el checker no anotó la llamada (p. ej. un método heredado
// de un `echo`), se busca el `enchanting` por nombre del método entre todas las
// bases candidatas y los realms cargados.
export function find_enchanting(
  g: JsContext,
  object_type: PenguType,
  name: string,
): { realm: string; base: string } | undefined {
  for (const base of candidate_bases(g, object_type)) {
    for (const unit of g.units.values()) {
      if (enchanting_method(unit, base, name) === undefined) continue;
      return { realm: unit.module.realm, base };
    }
  }
  return undefined;
}

// Nombres de base candidatos para resolver un `enchanting`: el tipo tal cual y,
// si viene envuelto, sus capas interiores (`optional<string>` → `string`).
function candidate_bases(g: JsContext, type: PenguType): string[] {
  const bases: string[] = [];
  let current: PenguType | undefined = type;
  while (current !== undefined) {
    const name = base_name_of(current);
    if (name !== undefined && !bases.includes(name)) bases.push(name);
    // Un `seal`/`echo` es su tipo base en runtime (§2.8): `Metros = seal double`
    // recibe los métodos de `double`.
    if (current.kind === "named") {
      const alias: PenguType | undefined = g.units
        .get(realm_of_type(g, current.name) ?? "")
        ?.module.env.aliases.get(current.name)?.target;
      if (alias !== undefined) {
        current = alias;
        continue;
      }
    }
    if (current.kind === "optional" || current.kind === "ref" || current.kind === "raw") current = current.inner;
    else if (current.kind === "unique" || current.kind === "shared" || current.kind === "weak") current = current.inner;
    else current = undefined;
  }
  return bases;
}

// ¿La expresión se puede escribir desde JS? Identificadores, campos, índices y
// `@` sí; una llamada o un literal no.
export function object_lvalue(node: { kind: string }): boolean {
  return node.kind === "ident" || node.kind === "member" || node.kind === "index" || node.kind === "self";
}

// `f(rt.ref(() => x, (v) => { x = v; }), args)` para un lvalue; para un
// temporal se copia a un `let`, se muta y se devuelve el valor.
function cell_call(
  g: JsContext,
  local: string,
  object: string,
  tail: string,
  lvalue: boolean,
): string {
  const runtime = runtime_name(g);
  if (lvalue) {
    return `${local}(${runtime}.ref(() => ${object}, (_v) => { ${object} = _v; })${tail})`;
  }
  const temp = fresh_name(g, "r");
  const cell = `${runtime}.ref(() => ${temp}, (_v) => { ${temp} = _v; })`;
  return `((${temp}) => { ${local}(${cell}${tail}); return ${temp}; })(${object})`;
}

