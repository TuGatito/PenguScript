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
import type { GenContext } from "./cpp_context.ts";
import { declare_local, line, pop_scope, push_scope } from "./cpp_context.ts";
import { cpp_identifier, cpp_type_node } from "./cpp_types.ts";
import { emit_value_block } from "./cpp_stmt.ts";
import { emit_expr } from "./cpp_expr.ts";

export function emit_declarations(g: GenContext, decls: readonly DeclNode[]): void {
  const methods_by_rune = collect_methods(decls);
  for (const decl of decls) {
    switch (decl.kind) {
      case "realm_decl":
      case "invoke_decl":
        break;
      case "const_decl":
        emit_const(g, decl);
        break;
      case "function_decl":
        emit_function(g, decl);
        break;
      case "rune_decl":
        emit_rune(g, decl, methods_by_rune.get(decl.name) ?? []);
        break;
      case "omen_decl":
        emit_omen(g, decl);
        break;
      case "echo_decl":
        emit_echo(g, decl);
        break;
      case "seal_decl":
        emit_seal(g, decl, methods_by_rune.get(decl.name) ?? []);
        break;
      case "enchanting_decl":
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
  const type = decl.declared_type ? cpp_type_node(decl.declared_type, g.module.env, g.type_realms) : "auto";
  const name = cpp_identifier(decl.name);
  const value = emit_expr(g, decl.value);
  if (decl.is_static) {
    line(g, `inline ${type === "auto" ? "auto" : type} ${name} = ${value};`);
  } else {
    line(g, `const ${type === "auto" ? "auto" : type} ${name} = ${value};`);
  }
}

function emit_function(g: GenContext, decl: FunctionDecl): void {
  if (decl.sigils.length > 0) {
    line(g, `template <${decl.sigils.map((sigil) => `typename ${sigil}`).join(", ")}>`);
  }
  const result = decl.result ? cpp_type_node(decl.result, g.module.env, g.type_realms) : "void";
  const params = decl.params.map((param) => emit_param(g, param)).join(", ");
  line(g, `${result} ${cpp_identifier(decl.name)}(${params}) {`);
  g.indent += 1;
  push_scope(g);
  for (const param of decl.params) declare_local(g, param.name);
  emit_value_block(g, decl.body, result);
  pop_scope(g);
  g.indent -= 1;
  line(g, "}");
}

function emit_param(g: GenContext, param: ParamNode): string {
  const base = param.type ? cpp_type_node(param.type, g.module.env, g.type_realms) : "auto";
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
  // Los punteros únicos se reciben por valor: pasarlos los mueve.
  const is_move_only = base.startsWith("std::unique_ptr");
  const rendered = is_primitive || is_move_only ? base : `const ${base}&`;
  return param.default_value
    ? `${rendered} ${name} = ${emit_expr(g, param.default_value)}`
    : `${rendered} ${name}`;
}

function emit_rune(g: GenContext, decl: RuneDecl, methods: readonly MethodDecl[]): void {
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
    const init = initializers.length > 0 ? ` : ${initializers.join(", ")}` : "";
    line(g, `${name}(${params})${init} {`);
    g.indent += 1;
    push_scope(g);
    for (const param of decl.constructor.params) declare_local(g, param.name);
    emit_value_block(g, decl.constructor.body, "void");
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

  g.indent -= 1;
  line(g, "};");
}

function emit_method(g: GenContext, method: MethodDecl): void {
  const result = method.result ? cpp_type_node(method.result, g.module.env, g.type_realms) : "void";
  const params = method.params.map((param) => emit_param(g, param)).join(", ");
  const name = method.operator ? operator_name(method.operator) : cpp_identifier(method.name);
  const constness = method.mutable ? "" : " const";
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
    for (const variant of variants) {
      line(g, `struct ${name}_${variant.name} {`);
      g.indent += 1;
      variant.payload.forEach((payload, position) => {
        line(g, `${cpp_type_node(payload, g.module.env, g.type_realms)} v${position};`);
      });
      g.indent -= 1;
      line(g, "};");
    }
    const alternatives = variants.map((variant) => `${name}_${variant.name}`).join(", ");
    line(g, `struct ${name} {`);
    g.indent += 1;
    line(g, `std::variant<${alternatives}> value;`);
    for (const variant of variants) {
      const args = variant.payload.map((_, position) => `v${position}`).join(", ");
      const params = variant.payload
        .map((payload, position) => `${cpp_type_node(payload, g.module.env, g.type_realms)} v${position}`)
        .join(", ");
      line(g, `static ${name} ${variant.name}(${params}) { return ${name}{${name}_${variant.name}{${args}}}; }`);
    }
    g.indent -= 1;
    line(g, "};");
    return;
  }

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
  line(g, `using ${cpp_identifier(decl.name)} = ${cpp_type_node(decl.target, g.module.env, g.type_realms)};`);
}

function emit_seal(g: GenContext, decl: SealDecl, methods: readonly MethodDecl[]): void {
  const name = cpp_identifier(decl.name);
  const target = cpp_type_node(decl.target, g.module.env, g.type_realms);
  line(g, `struct ${name} {`);
  g.indent += 1;
  line(g, `${target} value;`);
  line(g, `explicit ${name}(${target} v) : value(v) {}`);
  g.self_value = true;
  for (const method of methods) emit_method(g, method);
  g.self_value = false;
  g.indent -= 1;
  line(g, "};");
}
