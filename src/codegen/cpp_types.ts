// Traducción de tipos PenguScript a C++20.
//
// El checker ya resolvió los tipos; aquí solo se elige la forma C++
// equivalente. Los tipos `any` (símbolos de std, builtins dinámicos)
// se traducen a `auto` y nunca deben usarse como tipo de retorno de
// una lambda.

import type { TypeNode } from "../frontend/ast_type.ts";
import type { TypeEnv } from "../semantic/type_env.ts";
import { resolve_type_node } from "../semantic/type_env.ts";
import type { PenguType } from "../semantic/types.ts";
import { make_sink } from "../diagnostics/sink.ts";

const PRIMITIVES: Readonly<Record<string, string>> = {
  bool: "bool",
  char: "char",
  "signed char": "signed char",
  "unsigned char": "unsigned char",
  short: "short",
  "unsigned short": "unsigned short",
  int: "int",
  "unsigned int": "unsigned int",
  long: "long",
  "unsigned long": "unsigned long",
  "long long": "long long",
  "unsigned long long": "unsigned long long",
  float: "float",
  double: "double",
  "long double": "long double",
  wchar_t: "wchar_t",
  char8_t: "char8_t",
  char16_t: "char16_t",
  char32_t: "char32_t",
  nullptr_t: "std::nullptr_t",
  int8_t: "std::int8_t",
  int16_t: "std::int16_t",
  int32_t: "std::int32_t",
  int64_t: "std::int64_t",
  uint8_t: "std::uint8_t",
  uint16_t: "std::uint16_t",
  uint32_t: "std::uint32_t",
  uint64_t: "std::uint64_t",
  size_t: "std::size_t",
  ptrdiff_t: "std::ptrdiff_t",
  intptr_t: "std::intptr_t",
  uintptr_t: "std::uintptr_t",
  byte: "std::uint8_t",
  string: "std::string",
  wstring: "std::wstring",
  u8string: "std::u8string",
  u16string: "std::u16string",
  u32string: "std::u32string",
  string_view: "std::string_view",
};

const CONTAINERS: Readonly<Record<string, string>> = {
  vector: "std::vector",
  array: "std::array",
  deque: "std::deque",
  list: "std::list",
  forward_list: "std::forward_list",
  set: "std::set",
  multiset: "std::multiset",
  unordered_set: "std::unordered_set",
  map: "std::map",
  multimap: "std::multimap",
  unordered_map: "std::unordered_map",
  unordered_multimap: "std::unordered_multimap",
  stack: "std::stack",
  queue: "std::queue",
  priority_queue: "std::priority_queue",
  span: "std::span",
  pair: "std::pair",
  tuple: "std::tuple",
  bitset: "std::bitset",
  atomic: "std::atomic",
  complex: "std::complex",
  variant: "std::variant",
  init_list: "std::initializer_list",
  mutex: "std::mutex",
  shared_mutex: "std::shared_mutex",
  condition_variable: "std::condition_variable",
  thread: "std::thread",
};

// Nombre de tipo de usuario → realm que lo declara. Los tipos de otros
// módulos se cualifican (`realm::Tipo`); los del módulo actual también
// funcionan cualificados desde dentro de su namespace.
export type TypeRealms = ReadonlyMap<string, string>;

// Reinos que chocan con nombres de la biblioteca C (`time`, `random`,
// `log`) o con macros (`assert`): se emiten con sufijo `_rt`. En C++ no
// se puede declarar `namespace log` junto a `double log(double)` de
// <math.h>; `std/log` fue el primer módulo que tropezó con esto.
const RESERVED_REALMS: ReadonlySet<string> = new Set(["time", "random", "assert", "log"]);

// Palabras clave de C++ que también son nombres válidos de realm en
// PenguScript: un `namespace int` no compila.
const CXX_KEYWORDS: ReadonlySet<string> = new Set([
  "alignas", "alignof", "and", "asm", "auto", "bool", "break", "case", "catch",
  "char", "class", "const", "consteval", "constexpr", "constinit", "const_cast",
  "continue", "co_await", "co_return", "co_yield", "decltype", "default", "delete",
  "do", "double", "dynamic_cast", "else", "enum", "explicit", "export", "extern",
  "false", "float", "for", "friend", "goto", "if", "inline", "int", "long",
  "mutable", "namespace", "new", "noexcept", "not", "nullptr", "operator", "or",
  "private", "protected", "public", "register", "reinterpret_cast", "requires",
  "return", "short", "signed", "sizeof", "static", "static_assert", "static_cast",
  "struct", "switch", "template", "this", "thread_local", "throw", "true", "try",
  "typedef", "typeid", "typename", "union", "unsigned", "using", "virtual", "void",
  "volatile", "wchar_t", "while", "xor",
]);

export function sanitize_namespace(name: string): string {
  if (name.length === 0) return "realm";
  if (name === "main") return "main_realm";
  if (RESERVED_REALMS.has(name) || CXX_KEYWORDS.has(name)) return `${name}_rt`;
  let out = "";
  for (const char of name) {
    out += /[A-Za-z0-9_]/.test(char) ? char : "_";
  }
  return /^[A-Za-z_]/.test(out) ? out : `_${out}`;
}

export function cpp_type(type: PenguType, realms?: TypeRealms): string {
  switch (type.kind) {
    case "primitive":
      return PRIMITIVES[type.name] ?? type.name;
    case "named": {
      if (type.name === "Ordering" && type.args.length === 0) return "::pengu::Ordering";
      const realm = realms?.get(type.name);
      const base = CONTAINERS[type.name] ?? (realm !== undefined ? `${sanitize_namespace(realm)}::${type.name}` : type.name);
      if (type.args.length === 0) return base;
      return `${base}<${type.args.map((arg) => cpp_type(arg, realms)).join(", ")}>`;
    }
    case "optional":
      return `std::optional<${cpp_type(type.inner, realms)}>`;
    case "ref":
      return type.mutable ? `${cpp_type(type.inner, realms)}&` : `const ${cpp_type(type.inner, realms)}&`;
    case "raw":
      return `${cpp_type(type.inner, realms)}*`;
    case "unique":
      return `std::unique_ptr<${cpp_type(type.inner, realms)}>`;
    case "shared":
      return `std::shared_ptr<${cpp_type(type.inner, realms)}>`;
    case "weak":
      return `std::weak_ptr<${cpp_type(type.inner, realms)}>`;
    case "function": {
      const params = type.variadic ? type.params.slice(0, -1) : type.params;
      const rendered = params.map((param) => cpp_type(param, realms));
      if (type.variadic) {
        const element = type.params[type.params.length - 1];
        rendered.push(`std::vector<${element === undefined ? "auto" : cpp_type(element, realms)}>`);
      }
      return `std::function<${cpp_type(type.result, realms)}(${rendered.join(", ")})>`;
    }
    case "tuple":
      return `std::tuple<${type.items.map((item) => cpp_type(item, realms)).join(", ")}>`;
    case "array":
      return `std::array<${cpp_type(type.element, realms)}, ${type.size}>`;
    case "range":
      return "::pengu::Range";
    case "void":
      return "void";
    case "none":
      return "std::nullopt_t";
    case "nullptr":
      return "std::nullptr_t";
    case "any":
      return "::pengu::Value";
  }
}

// Tipo utilizable como valor de retorno de una lambda o variable.
// `any` no puede deducirse con `auto` en ese contexto, así que se
// degrada a `void` (solo ocurre en expresiones descartadas).
export function cpp_value_type(type: PenguType | undefined, realms?: TypeRealms): string {
  if (type === undefined) return "void";
  return cpp_type(type, realms);
}

export function cpp_type_node(node: TypeNode, env: TypeEnv, realms?: TypeRealms): string {
  const sink = make_sink({ max: 1 });
  const type = resolve_type_node(node, env, sink);
  return cpp_type(type, realms);
}

// Parámetro de función: los runes y contenedores se pasan por
// referencia constante para no copiar; los primitivos por valor.
export function cpp_param_type(type: PenguType, mutable: boolean, realms?: TypeRealms): string {
  if (type.kind === "ref") {
    return `${cpp_type(type.inner, realms)}&`;
  }
  if (mutable && (type.kind === "named" || type.kind === "tuple")) {
    return `${cpp_type(type, realms)}&`;
  }
  if (type.kind === "named" || type.kind === "tuple" || type.kind === "optional" || type.kind === "array") {
    return `const ${cpp_type(type, realms)}&`;
  }
  return cpp_type(type, realms);
}

// Un identificador de PenguScript puede llamarse `union` o `template`; en
// C++ eso no compila, así que se escapa con un sufijo.
export function cpp_identifier(name: string): string {
  if (name.startsWith("_")) return "p" + name;
  if (CXX_KEYWORDS.has(name)) return `${name}_`;
  return name;
}
