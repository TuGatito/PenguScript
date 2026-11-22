// Emisión de declaraciones de nivel superior.
//
// Los runes se convierten en structs; sus métodos vienen de bloques
// `enchanting`, que pueden estar en cualquier punto del módulo, así
// que primero se recogen y luego se insertan en el struct.

import type {
  ConstDecl,
  DeclNode,
  EchoDecl,
  EnchantingDecl,
  FunctionDecl,
  MethodDecl,
  OmenDecl,
  RuneDecl,
  SealDecl,
} from "../frontend/ast_decl.ts";
import type { ParamNode } from "../frontend/ast_param.ts";
import type { TypeNode } from "../frontend/ast_type.ts";
import type { Block } from "../frontend/ast_stmt.ts";
import type { GenContext } from "./cpp_context.ts";
import { declare_local, line, pop_scope, push_scope } from "./cpp_context.ts";
import { cpp_identifier, cpp_type, cpp_type_node, sanitize_namespace } from "./cpp_types.ts";
import { emit_value_block } from "./cpp_stmt.ts";
import { emit_expr } from "./cpp_expr.ts";
import { generic_type, named } from "../semantic/types.ts";
import type { TypeDecl } from "./cpp_type_order.ts";
import { is_type_decl, order_type_decls } from "./cpp_type_order.ts";
import { enchant_target_of, type_pattern_type } from "../semantic/enchant_targets.ts";


// Los sigilos deben estar activos mientras se emite una declaración
// genérica: `T` se traduce literalmente a `T` (parámetro de plantilla).
function with_sigils(g: GenContext, sigils: readonly string[], body: () => void): void {
  const previous = new Map(g.module.env.sigils);
  for (const sigil of sigils) g.module.env.sigils.set(sigil, generic_type(sigil));
  try {
    body();
  } finally {
    g.module.env.sigils.clear();
    for (const [key, value] of previous) g.module.env.sigils.set(key, value);
  }
}

export function emit_declarations(g: GenContext, decls: readonly DeclNode[]): void {
  emit_type_declarations(g, decls);
  emit_rest_declarations(g, decls);
}

// Solo tipos: se emiten antes de las especializaciones de `std::hash`, que
// a su vez deben estar declaradas antes de cualquier función que use
// contenedores `unordered_*`.
export function emit_type_declarations(g: GenContext, decls: readonly DeclNode[]): void {
  const methods_by_rune = collect_methods(decls);
  const type_decls: TypeDecl[] = [];
  for (const decl of decls) {
    if (is_type_decl(decl)) type_decls.push(decl);
  }
  const types = order_type_decls(type_decls);

  // Primero los tipos, en orden de dependencia: C++ necesita el padre
  // completo antes que la hija.
  for (const decl of types) {
    switch (decl.kind) {
      case "rune_decl":
        with_sigils(g, decl.sigils, () => emit_rune(g, decl, methods_by_rune.get(decl.name) ?? []));
        break;
      case "omen_decl":
        with_sigils(g, decl.sigils, () => {
          emit_omen(g, decl);
          emit_free_methods(g, decl.name, methods_by_rune.get(decl.name) ?? []);
        });
        break;
      case "echo_decl":
        with_sigils(g, decl.sigils, () => {
          emit_echo(g, decl);
          emit_free_methods(g, decl.name, methods_by_rune.get(decl.name) ?? []);
        });
        break;
      case "seal_decl":
        with_sigils(g, decl.sigils, () => emit_seal(g, decl, methods_by_rune.get(decl.name) ?? []));
        break;
    }
  }

  // `std::hash` sintetizado para runes y sellos: los contenedores
  // `unordered_*` necesitan poder hashear sus claves. Se acumula en
  // `g.std_extra` para emitirlo en el ámbito global.
  emit_hash_specializations(g, types);
}

// Constantes, funciones, externos y bloques `enchanting`.
export function emit_rest_declarations(g: GenContext, decls: readonly DeclNode[]): void {
  // Las constantes van antes que las funciones (que pueden usarlas) y
  // en orden de dependencia entre ellas.
  for (const decl of order_consts(decls)) emit_const(g, decl);

  // Después el resto, en el orden del fuente.
  for (const decl of decls) {
    switch (decl.kind) {
      case "realm_decl":
      case "invoke_decl":
      case "rune_decl":
      case "omen_decl":
      case "echo_decl":
      case "seal_decl":
        break;
      case "enchanting_decl":
        if (enchant_target_of(decl.target) !== undefined) emit_builtin_enchanting(g, decl);
        break;
      case "const_decl":
        break;
      case "function_decl":
        with_sigils(g, decl.sigils, () => emit_function(g, decl));
        break;
      case "extern_decl":
        emit_extern(g, decl);
        break;
    }
  }
}

// Declaraciones `extern "C"`: prototipos sin cuerpo para enlazar con
// bibliotecas nativas (las genera `pengu bindgen`).
// `string` cruza la frontera C como `const char*`; la envoltura convierte.
function c_boundary_type(rendered: string): string {
  return rendered === "std::string" ? "const char*" : rendered;
}

interface CDeclaration {
  readonly name: string;
  readonly params: readonly { readonly name: string; readonly type: string }[];
  readonly result: string;
}

function emit_extern(g: GenContext, decl: Extract<DeclNode, { kind: "extern_decl" }>): void {
  const declarations: CDeclaration[] = [];
  line(g, `extern "${decl.abi ?? "C"}" {`);
  g.indent += 1;
  for (const declared of decl.declares) {
    const params = declared.params.map((param) => ({
      name: cpp_identifier(param.name),
      type: param.type ? cpp_type_node(param.type, g.module.env, g.type_realms) : "auto",
    }));
    const variadic = declared.params.some((param) => param.variadic);
    const fixed = variadic ? params.slice(0, -1) : params;
    const result = declared.result ? cpp_type_node(declared.result, g.module.env, g.type_realms) : "void";
    const rendered = fixed.map((param) => `${c_boundary_type(param.type)} ${param.name}`);
    if (variadic) rendered.push("...");
    line(g, `${c_boundary_type(result)} ${cpp_identifier(declared.name)}(${rendered.join(", ")});`);
    declarations.push({ name: cpp_identifier(declared.name), params: fixed, result });
  }
  g.indent -= 1;
  line(g, "}");

  // Sobrecarga de conveniencia: acepta `string` y lo convierte a `const char*`.
  for (const declaration of declarations) {
    const converts =
      declaration.result === "std::string" || declaration.params.some((param) => param.type === "std::string");
    if (!converts) continue;
    const params = declaration.params.map(
      (param) => `${param.type}${param.type === "auto" ? "" : " const&"} ${param.name}`,
    );
    const args = declaration.params
      .map((param) => (param.type === "std::string" ? `${param.name}.c_str()` : param.name))
      .join(", ");
    line(g, `inline ${declaration.result} ${declaration.name}(${params.join(", ")}) {`);
    g.indent += 1;
    if (declaration.result === "void") {
      line(g, `${declaration.name}(${args});`);
    } else if (declaration.result === "std::string") {
      line(g, `return std::string(${declaration.name}(${args}));`);
    } else {
      line(g, `return ${declaration.name}(${args});`);
    }
    g.indent -= 1;
    line(g, "}");
  }
}

function collect_methods(decls: readonly DeclNode[]): Map<string, readonly MethodDecl[]> {
  const result = new Map<string, MethodDecl[]>();
  for (const decl of decls) {
    if (decl.kind !== "enchanting_decl") continue;
    const target = decl as EnchantingDecl;
    const existing = result.get(target.target) ?? [];
    existing.push(...target.methods);
    result.set(target.target, existing);
  }
  return result;
}

function emit_const(g: GenContext, decl: ConstDecl): void {
  const declared = decl.declared_type ? cpp_type_node(decl.declared_type, g.module.env, g.type_realms) : "auto";
  const type = declared === "auto" ? "auto" : declared;
  const name = cpp_identifier(decl.name);
  const value = emit_expr(g, decl.value);
  const info = g.module.consts.get(decl.name);
  const evaluable = info?.evaluable === true && declared !== "auto";

  if (decl.is_static) {
    // `static mut`: mutable de módulo, no `const`.
    line(g, `static ${type} ${name} = ${value};`);
    return;
  }

  const value_type = info?.type;
  if (is_interior_mutable(declared) || (declared === "auto" && value_type !== undefined && is_interior_mutable_type(value_type))) {
    // `atomic`, `mutex`, …: la vinculación es inmutable pero el objeto no.
    line(g, `inline ${type} ${name} = ${value};`);
    return;
  }

  if (evaluable) {
    line(g, `constexpr ${type} ${name} = ${value};`);
    return;
  }

  line(g, `const ${type} ${name} = ${value};`);
}

function is_interior_mutable_type(type: { readonly kind: string; readonly name?: string }): boolean {
  return type.kind === "named" && type.name !== undefined && INTERIOR_MUTABLE_NAMES.has(type.name);
}

const INTERIOR_MUTABLE_NAMES = new Set(["atomic", "mutex", "shared_mutex", "condition_variable"]);

function is_interior_mutable(type: string): boolean {
  return (
    type.startsWith("std::atomic") ||
    type === "std::mutex" ||
    type === "std::shared_mutex" ||
    type === "std::condition_variable"
  );
}

// Ordena las constantes por dependencia: C++ exige declarar antes de usar
// (las funciones pueden ir después, pero `constexpr` no).
function order_consts(decls: readonly DeclNode[]): readonly ConstDecl[] {
  const consts = decls.filter((decl): decl is ConstDecl => decl.kind === "const_decl");
  const by_name = new Map(consts.map((decl) => [decl.name, decl]));
  const ordered: ConstDecl[] = [];
  const state = new Map<string, "visiting" | "done">();

  function visit(decl: ConstDecl): void {
    const current = state.get(decl.name);
    if (current === "done" || current === "visiting") return;
    state.set(decl.name, "visiting");
    for (const name of referenced_names(decl.value)) {
      const dependency = by_name.get(name);
      if (dependency !== undefined) visit(dependency);
    }
    state.set(decl.name, "done");
    ordered.push(decl);
  }

  for (const decl of consts) visit(decl);
  return ordered;
}

function referenced_names(node: unknown): readonly string[] {
  const found: string[] = [];
  const walk = (value: unknown): void => {
    if (value === null || typeof value !== "object") return;
    if (Array.isArray(value)) {
      for (const item of value) walk(item);
      return;
    }
    const record = value as Record<string, unknown>;
    if (record.kind === "ident" && typeof record.name === "string") found.push(record.name);
    for (const key of Object.keys(record)) {
      if (key === "span") continue;
      walk(record[key]);
    }
  };
  walk(node);
  return found;
}

// En una función genérica, un parámetro con tipo de función no se puede
// deducir contra `std::function<...>`: el parámetro se vuelve una plantilla
// más y acepta tanto funciones como lambdas.
// Sigilos que menciona un nodo de tipo (`<T>(x: T)` → {T}).
function sigils_in_node(node: TypeNode): ReadonlySet<string> {
  const found = new Set<string>();
  const visit = (child: TypeNode): void => {
    switch (child.kind) {
      case "named_type":
        if (child.args.length === 0) {
          if (/^[A-Z][A-Z0-9]?$/.test(child.name)) found.add(child.name);
          return;
        }
        for (const arg of child.args) visit(arg);
        return;
      case "tuple_type":
        for (const item of child.items) visit(item);
        return;
      case "array_type":
        visit(child.element);
        return;
      case "optional_type":
      case "ref_type":
        visit(child.inner);
        return;
      case "function_type":
        for (const param of child.params) visit(param);
        if (child.result !== undefined) visit(child.result);
        return;
      case "primitive_type":
        return;
    }
  };
  visit(node);
  return found;
}

function union_of(sets: readonly ReadonlySet<string>[]): ReadonlySet<string> {
  const all = new Set<string>();
  for (const set of sets) for (const name of set) all.add(name);
  return all;
}

function generic_param_overrides(
  g: GenContext,
  decl: FunctionDecl,
): { readonly template_params: readonly string[]; readonly rendered: readonly string[] } {
  const template_params: string[] = [];
  // Un sigilo ya deducible desde un parámetro anterior no hace falta
  // deducirlo otra vez: se marca como no deducido para permitir conversiones
  // (por ejemplo `or_else(optional<size_t>, 0)`). El tipo de resultado no
  // participa en la deducción, así que no cuenta aquí.
  const seen = new Set<string>();
  const rendered = decl.params.map((param, index) => {
    if (param.type?.kind === "function_type") {
      const name = `F${index}`;
      template_params.push(name);
      return `const ${name}& ${cpp_identifier(param.name)}`;
    }
    const own = param.type ? sigils_in_node(param.type) : new Set<string>();
    const deducible = own.size > 0 && [...own].every((sigil) => seen.has(sigil));
    for (const sigil of own) seen.add(sigil);
    return emit_param(g, param, deducible);
  });
  return { template_params, rendered };
}

function emit_function(g: GenContext, decl: FunctionDecl): void {
  const generic = decl.sigils.length > 0;
  const overrides = generic ? generic_param_overrides(g, decl) : undefined;
  if (generic) {
    const names = [...decl.sigils, ...(overrides?.template_params ?? [])];
    line(g, `template <${names.map((sigil) => `typename ${sigil}`).join(", ")}>`);
  }
  const result = decl.result ? cpp_type_node(decl.result, g.module.env, g.type_realms) : "void";
  const params = (overrides?.rendered ?? decl.params.map((param) => emit_param(g, param))).join(", ");
  const name = decl.operator === undefined ? cpp_identifier(decl.name) : operator_name(decl.operator);
  line(g, `${result} ${name}(${params}) {`);
  g.indent += 1;
  push_scope(g);
  for (const param of decl.params) declare_local(g, param.name);
  emit_value_block(g, decl.body, result);
  pop_scope(g);
  g.indent -= 1;
  line(g, "}");
}

// Los omens y los `echo` no tienen métodos en C++ (son `enum class` y
// alias): sus bloques `enchanting` se emiten como funciones libres y
// las llamadas `valor.m(...)` se reescriben a `m(valor, ...)`.
// `enchanting` sobre un tipo incorporado: se emite como funciones libres
// dentro del realm que las declara, con el receptor como primer parámetro.
function emit_builtin_enchanting(g: GenContext, decl: EnchantingDecl): void {
  if (decl.methods.length === 0) return;
  const self_type = type_pattern_type(decl.target_type);
  // `enchanting array<T>` omite el tamaño: el receptor real es
  // `std::array<T, N>` y el tamaño entra como parámetro de plantilla.
  const is_array = decl.target === "array";
  const pointer =
    decl.target === "unique"
      ? "std::unique_ptr"
      : decl.target === "shared"
        ? "std::shared_ptr"
        : decl.target === "weak"
          ? "std::weak_ptr"
          : undefined;
  const self =
    pointer !== undefined
      ? `${pointer}<${decl.sigils[0] ?? "T"}>`
      : is_array
        ? `std::array<${decl.sigils[0] ?? "T"}, N>`
        : cpp_type(self_type, g.type_realms);
  const previous = g.self_expression;
  with_sigils(g, decl.sigils, () => {
    for (const method of decl.methods) {
      const overrides = decl.sigils.length > 0
        ? {
            template_params: [] as string[],
            rendered: method.params.map((param) => {
              const own = param.type ? sigils_in_node(param.type) : new Set<string>();
              return emit_param(g, param, own.size > 0);
            }),
          }
        : undefined;
      const extra = overrides?.template_params ?? [];
      if (is_array) {
        line(g, `template <typename ${decl.sigils[0] ?? "T"}, std::size_t N${extra.map((name) => `, typename ${name}`).join("")}>`);
      } else if (decl.sigils.length > 0) {
        const names = [...decl.sigils, ...extra];
        line(g, `template <${names.map((sigil) => `typename ${sigil}`).join(", ")}>`);
      }
      const result = method.result ? cpp_type_node(method.result, g.module.env, g.type_realms) : "void";
      const params = (overrides?.rendered ?? method.params.map((param) => emit_param(g, param))).join(", ");
      const separator = params.length > 0 ? ", " : "";
      const receiver = method.mutable ? `${self}& self` : `const ${self}& self`;
      const name = method.operator ? operator_name(method.operator) : cpp_identifier(method.name);
      line(g, `${result} ${name}(${receiver}${separator}${params}) {`);
      g.indent += 1;
      push_scope(g);
      declare_local(g, "self");
      for (const param of method.params) declare_local(g, param.name);
      g.self_expression =
        pointer === undefined || pointer === "std::weak_ptr" ? "self" : "(*self)";
      emit_value_block(g, method.body, result);
      g.self_expression = previous;
      pop_scope(g);
      g.indent -= 1;
      line(g, "}");
    }
  });
}

function emit_free_methods(
  g: GenContext,
  target: string,
  methods: readonly MethodDecl[],
): void {
  if (methods.length === 0) return;
  const omen = g.module.env.omens.get(target);
  const alias = g.module.env.aliases.get(target);
  if (omen === undefined && alias === undefined) return;
  const self = cpp_type(omen !== undefined ? named(target) : alias!.target, g.type_realms);
  const previous = g.self_expression;
  for (const method of methods) {
    const result = method.result ? cpp_type_node(method.result, g.module.env, g.type_realms) : "void";
    const params = method.params.map((param) => emit_param(g, param)).join(", ");
    const separator = params.length > 0 ? ", " : "";
    const name = method.operator ? operator_name(method.operator) : cpp_identifier(method.name);
    line(g, `${result} ${name}(const ${self}& self${separator}${params}) {`);
    g.indent += 1;
    push_scope(g);
    declare_local(g, "self");
    for (const param of method.params) declare_local(g, param.name);
    g.self_expression = "self";
    emit_value_block(g, method.body, result);
    g.self_expression = previous;
    pop_scope(g);
    g.indent -= 1;
    line(g, "}");
  }
}

function emit_param(g: GenContext, param: ParamNode, wrap = false): string {
  const raw = param.type ? cpp_type_node(param.type, g.module.env, g.type_realms) : "auto";
  const base = wrap && raw !== "auto" ? `std::type_identity_t<${raw}>` : raw;
  const name = cpp_identifier(param.name);
  if (param.variadic) {
    const element = base === "auto" ? "::pengu::Value" : base;
    return param.mutable
      ? `std::vector<${element}>& ${name}`
      : `const std::vector<${element}>& ${name}`;
  }
  if (base === "auto") return `auto ${name}`;
  if (param.mutable) return `${base}& ${name}`;
  if (base.endsWith("&")) return `${base} ${name}`;
  const is_primitive = param.type?.kind === "primitive_type";
  // Los punteros se reciben por valor: `unique` porque pasarlo lo mueve
  // y `raw` porque es una dirección copiable.
  const is_pointer =
    base.startsWith("std::unique_ptr") || base.endsWith("*");
  const rendered = is_primitive || is_pointer ? base : `const ${base}&`;
  return param.default_value
    ? `${rendered} ${name} = ${emit_expr(g, param.default_value)}`
    : `${rendered} ${name}`;
}

function emit_rune(
  g: GenContext,
  decl: RuneDecl,
  methods: readonly MethodDecl[],
): void {
  if (decl.sigils.length > 0) {
    line(g, `template <${decl.sigils.map((sigil) => `typename ${sigil}`).join(", ")}>`);
  }
  const name = cpp_identifier(decl.name);
  const parent = decl.parent ? ` : public ${cpp_identifier(decl.parent)}` : "";
  line(g, `struct ${name}${parent} {`);
  g.indent += 1;
  for (const field of decl.fields) {
    const type = cpp_type_node(field.type, g.module.env, g.type_realms);
    const default_value = field.default_value ? ` = ${emit_expr(g, field.default_value)}` : "";
    line(g, `${type} ${cpp_identifier(field.name)}${default_value};`);
  }


  if (decl.constructor) {
    const params = decl.constructor.params.map((param) => emit_param(g, param)).join(", ");
    const field_names = new Set(decl.fields.map((field) => field.name));
    const initializers = decl.constructor.params
      .filter((param) => field_names.has(param.name))
      .map((param) => `${cpp_identifier(param.name)}(${cpp_identifier(param.name)})`);

    // `parent(...)` como primera sentencia del constructor inicializa
    // la base; el resto del cuerpo sigue siendo normal.
    const body = parent_call_body(g, decl, initializers);
    const init = initializers.length > 0 ? ` : ${initializers.join(", ")}` : "";
    line(g, `${name}(${params})${init} {`);
    g.indent += 1;
    push_scope(g);
    for (const param of decl.constructor.params) declare_local(g, param.name);
    emit_value_block(g, body, "void");
    pop_scope(g);
    g.indent -= 1;
    line(g, "}");
  }

  if (decl.destructor) {
    line(g, `~${name}() {`);
    g.indent += 1;
    emit_value_block(g, decl.destructor, "void");
    g.indent -= 1;
    line(g, "}");
  }

  for (const method of methods) {
    emit_method(g, method);
  }

  // Las comparaciones se derivan de `<=>`: C++ solo reescribe `<` cuando
  // el operador espacial devuelve un orden estándar, y `Ordering` es
  // nuestro tipo. Emitimos las cuatro explícitamente.
  if (methods.some((method) => method.operator === "<=>")) {
    line(g, `bool operator<(const ${name}& otro) const { return (*this <=> otro).is_lt(); }`);
    line(g, `bool operator>(const ${name}& otro) const { return (*this <=> otro).is_gt(); }`);
    line(g, `bool operator<=(const ${name}& otro) const { auto orden = *this <=> otro; return orden.is_lt() || orden.is_eq(); }`);
    line(g, `bool operator>=(const ${name}& otro) const { auto orden = *this <=> otro; return orden.is_gt() || orden.is_eq(); }`);
  }

  g.indent -= 1;
  line(g, "};");
}

// Hash sintetizado campo a campo, en orden de declaración. Los sellos
// hashean su valor subyacente y las runes genéricas usan una
// especialización parcial.
function emit_hash_specializations(g: GenContext, decls: readonly TypeDecl[]): void {
  const realm = sanitize_namespace(g.module.realm);
  // Las especializaciones de `std::hash` viven en el ámbito global, no
  // dentro del namespace del realm: se acumulan para emitirlas después.
  const saved_lines = g.lines;
  const saved_indent = g.indent;
  const buffer: string[] = [];
  g.lines = buffer;
  g.indent = 0;
  let emitted = false;
  for (const decl of decls) {
    if (decl.kind === "rune_decl") {
      if (decl.fields.length === 0) continue;
      if (!emitted) line(g, "namespace std {");
      emitted = true;
      const name = cpp_identifier(decl.name);
      if (decl.sigils.length > 0) {
        line(g, `template <${decl.sigils.map((sigil) => `typename ${sigil}`).join(", ")}>`);
        line(g, `struct hash<::${realm}::${name}<${decl.sigils.join(", ")}>> {`);
      } else {
        line(g, "template <>");
        line(g, `struct hash<::${realm}::${name}> {`);
      }
      g.indent += 1;
      line(g, `std::size_t operator()(const ::${realm}::${name}${generic_args(decl.sigils)}& value) const noexcept {`);
      g.indent += 1;
      line(g, "std::size_t seed = 0;");
      for (const field of decl.fields) {
        line(g, `::pengu::hash_combine(seed, value.${cpp_identifier(field.name)});`);
      }
      line(g, "return seed;");
      g.indent -= 1;
      line(g, "}");
      g.indent -= 1;
      line(g, "};");
      continue;
    }
    if (decl.kind === "seal_decl") {
      if (!emitted) line(g, "namespace std {");
      emitted = true;
      const name = cpp_identifier(decl.name);
      if (decl.sigils.length > 0) {
        line(g, `template <${decl.sigils.map((sigil) => `typename ${sigil}`).join(", ")}>`);
        line(g, `struct hash<::${realm}::${name}<${decl.sigils.join(", ")}>> {`);
      } else {
        line(g, "template <>");
        line(g, `struct hash<::${realm}::${name}> {`);
      }
      const target = cpp_type_node(decl.target, g.module.env, g.type_realms);
      g.indent += 1;
      line(g, `std::size_t operator()(const ::${realm}::${name}${generic_args(decl.sigils)}& value) const noexcept {`);
      g.indent += 1;
      line(g, `return std::hash<${target}>{}(value.value);`);
      g.indent -= 1;
      line(g, "}");
      g.indent -= 1;
      line(g, "};");
    }
  }
  if (emitted) line(g, "}  // namespace std");
  g.lines = saved_lines;
  g.indent = saved_indent;
  if (emitted) g.std_extra.push(...buffer);
}

function generic_args(sigils: readonly string[]): string {
  return sigils.length === 0 ? "" : `<${sigils.join(", ")}>`;
}

// `parent(...)` no es una llamada normal: se convierte en el
// inicializador de la clase base y desaparece del cuerpo.
function parent_call_body(g: GenContext, decl: RuneDecl, initializers: string[]): Block {
  const body = decl.constructor?.body;
  if (body === undefined) return { kind: "block", statements: [], span: decl.span };
  const first = body.statements[0];
  if (first === undefined || first.kind !== "expr_stmt" || first.expr.kind !== "parent_call") {
    return body;
  }
  const args = first.expr.args.map((arg) => emit_expr(g, arg.expr)).join(", ");
  const base = decl.parent ?? "";
  initializers.unshift(`${cpp_identifier(base)}(${args})`);
  return { kind: "block", statements: body.statements.slice(1), span: body.span };
}

function emit_method(g: GenContext, method: MethodDecl): void {
  const result = method.result ? cpp_type_node(method.result, g.module.env, g.type_realms) : "void";
  const params = method.params.map((param) => emit_param(g, param)).join(", ");
  const name = method.operator ? operator_name(method.operator) : cpp_identifier(method.name);
  const constness = method.mutable ? "" : " const";
  // Sin despacho virtual: cada llamada se resuelve con el tipo estático.
  line(g, `${result} ${name}(${params})${constness} {`);
  g.indent += 1;
  push_scope(g);
  for (const param of method.params) declare_local(g, param.name);
  emit_value_block(g, method.body, result);
  pop_scope(g);
  g.indent -= 1;
  line(g, "}");
}

function operator_name(operator: string): string {
  if (operator === "[]") return "operator[]";
  if (operator === "()") return "operator()";
  return `operator${operator}`;
}

function emit_template_header(g: GenContext, sigils: readonly string[]): void {
  if (sigils.length > 0) {
    line(g, `template <${sigils.map((sigil) => `typename ${sigil}`).join(", ")}>`);
  }
}

function emit_omen(g: GenContext, decl: OmenDecl): void {
  const name = cpp_identifier(decl.name);
  const variants = decl.variants;
  const algebraic = variants.some((variant) => variant.payload.length > 0);
  const underlying = decl.underlying
    ? cpp_type_node(decl.underlying, g.module.env, g.type_realms)
    : decl.is_flags
      ? "std::uint64_t"
      : "int";

  if (algebraic) {
    const sigil_args = decl.sigils.length > 0 ? `<${decl.sigils.join(", ")}>` : "";
    for (const variant of variants) {
      emit_template_header(g, decl.sigils);
      line(g, `struct ${name}_${variant.name} {`);
      g.indent += 1;
      variant.payload.forEach((payload, position) => {
        line(g, `${cpp_type_node(payload, g.module.env, g.type_realms)} v${position};`);
      });
      g.indent -= 1;
      line(g, "};");
    }
    const alternatives = variants.map((variant) => `${name}_${variant.name}${sigil_args}`).join(", ");
    emit_template_header(g, decl.sigils);
    line(g, `struct ${name} {`);
    g.indent += 1;
    line(g, `std::variant<${alternatives}> value;`);
    for (const variant of variants) {
      const args = variant.payload.map((_, position) => `v${position}`).join(", ");
      const params = variant.payload
        .map((payload, position) => `${cpp_type_node(payload, g.module.env, g.type_realms)} v${position}`)
        .join(", ");
      line(
        g,
        `static ${name}${sigil_args} ${variant.name}(${params}) { return ${name}${sigil_args}{${name}_${variant.name}${sigil_args}{${args}}}; }`,
      );
    }
    g.indent -= 1;
    line(g, "};");
    return;
  }

  emit_template_header(g, decl.sigils);
  line(g, `enum class ${name} : ${underlying} {`);
  g.indent += 1;
  variants.forEach((variant, index) => {
    const explicit_value = variant.value ? ` = ${emit_expr(g, variant.value)}` : "";
    const implicit_value =
      decl.is_flags && !variant.value ? ` = 1ULL << ${index}` : "";
    line(g, `${variant.name}${explicit_value || implicit_value}${index === variants.length - 1 ? "" : ","}`);
  });
  g.indent -= 1;
  line(g, "};");

  if (decl.is_flags) {
    line(g, `inline constexpr ${name} operator|(${name} a, ${name} b) {`);
    line(g, `  return static_cast<${name}>(static_cast<${underlying}>(a) | static_cast<${underlying}>(b));`);
    line(g, "}");
    line(g, `inline constexpr ${name} operator&(${name} a, ${name} b) {`);
    line(g, `  return static_cast<${name}>(static_cast<${underlying}>(a) & static_cast<${underlying}>(b));`);
    line(g, "}");
    line(g, `inline constexpr ${name} operator^(${name} a, ${name} b) {`);
    line(g, `  return static_cast<${name}>(static_cast<${underlying}>(a) ^ static_cast<${underlying}>(b));`);
    line(g, "}");
    line(g, `inline constexpr ${name} operator~(${name} a) {`);
    line(g, `  return static_cast<${name}>(~static_cast<${underlying}>(a));`);
    line(g, "}");
    line(g, `inline ${name}& operator|=( ${name}& a, ${name} b) { a = a | b; return a; }`);
    line(g, `inline ${name}& operator&=( ${name}& a, ${name} b) { a = a & b; return a; }`);
  }
}

function emit_echo(g: GenContext, decl: EchoDecl): void {
  emit_template_header(g, decl.sigils);
  line(g, `using ${cpp_identifier(decl.name)} = ${cpp_type_node(decl.target, g.module.env, g.type_realms)};`);
}

function emit_seal(g: GenContext, decl: SealDecl, methods: readonly MethodDecl[]): void {
  emit_template_header(g, decl.sigils);
  const name = cpp_identifier(decl.name);
  const target = cpp_type_node(decl.target, g.module.env, g.type_realms);
  line(g, `struct ${name} {`);
  g.indent += 1;
  line(g, `${target} value;`);
  line(g, `explicit ${name}(${target} v) : value(v) {}`);
  g.self_expression = "value";
  for (const method of methods) emit_method(g, method);
  g.self_expression = undefined;
  g.indent -= 1;
  line(g, "};");
}
