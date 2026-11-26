// Recolección de declaraciones de un módulo.
//
// Primero se registran los tipos (runes, omens, alias) para que las
// firmas puedan referirse a ellos sin importar el orden; después se
// funden los bloques `enchanting` y se registran funciones y
// constantes.

import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { CODES } from "../diagnostics/codes.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import type { Span } from "../util/span.ts";
import type { Program } from "../frontend/ast.ts";
import type {
  ConstDecl,
  DeclNode,
  EnchantingDecl,
  FunctionDecl,
  MethodDecl,
  OmenDecl,
  RuneDecl,
  DeclareDecl,
} from "../frontend/ast_decl.ts";
import type { ParamNode } from "../frontend/ast_param.ts";
import type { PenguType } from "./types.ts";
import { UNKNOWN, VOID, any_type, function_type, future_type, generic_type, named, type_display } from "./types.ts";
import type { AliasInfo, FieldInfo, MethodInfo, OmenInfo, RuneInfo, TypeEnv } from "./type_env.ts";
import { make_type_env, resolve_type_node } from "./type_env.ts";
import { register_host_decl } from "./host_types.ts";
import type { EnchantedType } from "./type_env.ts";
import { enchant_key, enchant_target_of, enchant_target_names, type_pattern_arity } from "./enchant_targets.ts";
import { suggest_name } from "../util/suggest.ts";

export interface ParamInfo {
  readonly name: string;
  readonly type: PenguType;
  readonly has_default: boolean;
  /** El parámetro se declara `mut`: contrato en la llamada. */
  readonly mutable: boolean;
  /** `(...xs: T)`: el tipo guardado es el del elemento, y dentro del
   *  cuerpo el parámetro vale `vector<T>`. */
  readonly variadic: boolean;
  readonly span: Span;
}

export interface FunctionInfo {
  readonly kind: "function";
  readonly name: string;
  readonly sigils: readonly string[];
  readonly needs: readonly string[];
  readonly params: readonly ParamInfo[];
  readonly variadic: boolean;
  readonly result: PenguType;
  readonly decl: FunctionDecl | undefined;
  readonly is_unsafe: boolean;
  // `async`: el cuerpo se comprueba contra `result` y las llamadas ven
  // `future<result>`.
  readonly is_async: boolean;
  readonly is_extern: boolean;
  readonly is_intrinsic: boolean;
  readonly span: Span;
}

export interface ConstInfo {
  readonly kind: "const";
  readonly name: string;
  // `define`: se emite `inline constexpr` y no lleva `static`.
  readonly is_define: boolean;
  readonly declared_type: PenguType | undefined;
  readonly decl: ConstDecl;
  readonly is_static: boolean;
  readonly mutable: boolean;
  readonly span: Span;
  type: PenguType;
  // `const` evaluable en compilación (literales y operaciones puras).
  evaluable: boolean;
}

export interface SelectiveItem {
  readonly name: string;
  readonly alias: string | undefined;
}

export interface ImportInfo {
  readonly path: string;
  readonly alias: string;
  // `as nombre`: el alias lo eligió el programa, no el realm del módulo.
  readonly explicit: boolean;
  readonly items: readonly SelectiveItem[] | undefined;
  readonly span: Span;
}

export interface ModuleInfo {
  readonly file: string;
  readonly realm: string;
  readonly env: TypeEnv;
  readonly imports: Map<string, ImportInfo>;
  readonly functions: Map<string, FunctionInfo>;
  readonly consts: Map<string, ConstInfo>;
  // Bibliotecas declaradas con `link "..."`.
  readonly links: string[];
}

export function collect_module(
  file: string,
  program: Program,
  sink: DiagnosticSink,
): ModuleInfo {
  const env = make_type_env();
  const imports = new Map<string, ImportInfo>();
  const functions = new Map<string, FunctionInfo>();
  const consts = new Map<string, ConstInfo>();
  const links: string[] = [];

  const module: ModuleInfo = { file, realm: default_realm(file), env, imports, functions, consts, links };
  let realm = module.realm;

  for (const decl of program.decls) {
    if (decl.kind === "realm_decl") {
      realm = decl.name;
      continue;
    }
    register_type_decl(decl, env, sink);
  }

  // Los `enchanting` necesitan que los runes ya existan.
  for (const decl of program.decls) {
    if (decl.kind === "enchanting_decl") {
      register_enchanting(decl, env, sink, realm);
    }
  }

  for (const decl of program.decls) {
    switch (decl.kind) {
      case "invoke_decl":
        register_import(decl, imports, sink);
        break;
      case "function_decl":
        register_function(decl, env, functions, sink);
        break;
      case "const_decl":
        register_const(decl, env, consts, sink);
        break;
      case "link_decl":
        if (decl.path.length > 0 && !links.includes(decl.path)) links.push(decl.path);
        break;
      case "realm_decl":
        break;
      case "rune_decl":
      case "meld_decl":
      case "omen_decl":
      case "echo_decl":
      case "seal_decl":
      case "opaque_decl":
      case "callback_decl":
      case "enchanting_decl":
      case "host_decl":
      case "host_global_decl":
      case "host_namespace_decl":
        break;
      case "extern_decl":
        for (const declared of decl.declares) register_extern(declared, env, functions, sink);
        break;
      case "intrinsic_decl":
        for (const declared of decl.declares) register_intrinsic(declared, env, functions, sink);
        break;
    }
  }

  return { ...module, realm };
}

function default_realm(file: string): string {
  const base = file.replace(/\\/g, "/").split("/").pop() ?? file;
  return base.replace(/\.d\.pengu$/, "").replace(/\.pengu$/, "");
}

function register_type_decl(decl: DeclNode, env: TypeEnv, sink: DiagnosticSink): void {
  switch (decl.kind) {
    case "rune_decl":
      register_rune(decl, env, sink, false);
      break;
    case "meld_decl":
      register_rune({ ...decl, kind: "rune_decl", constructor: undefined, destructor: undefined, parent: undefined }, env, sink, true);
      break;
    case "omen_decl":
      register_omen(decl, env, sink);
      break;
    case "opaque_decl": {
      if (env.opaques.has(decl.name) || env.runes.has(decl.name) || env.omens.has(decl.name) || env.aliases.has(decl.name)) {
        duplicate(sink, decl.name, decl.name_span);
        break;
      }
      env.opaques.set(decl.name, { kind: "opaque", name: decl.name, span: decl.name_span });
      break;
    }
    case "host_decl":
    case "host_global_decl":
    case "host_namespace_decl":
      register_host_decl(decl, env, sink);
      break;
    case "callback_decl": {
      if (env.callbacks.has(decl.name) || env.runes.has(decl.name) || env.omens.has(decl.name) || env.aliases.has(decl.name)) {
        duplicate(sink, decl.name, decl.name_span);
        break;
      }
      const params = decl.params.map((param) =>
        param.type === undefined ? UNKNOWN : resolve_type_node(param.type, env, sink),
      );
      const result = decl.result === undefined ? VOID : resolve_type_node(decl.result, env, sink);
      env.callbacks.set(decl.name, { kind: "callback", name: decl.name, params, result, span: decl.name_span });
      break;
    }
    case "echo_decl":
    case "seal_decl": {
      if (env.aliases.has(decl.name) || env.runes.has(decl.name) || env.omens.has(decl.name)) {
        duplicate(sink, decl.name, decl.name_span);
        return;
      }
      const previous = new Map(env.sigils);
      for (const sigil of decl.sigils) env.sigils.set(sigil, generic_type(sigil));
      const target = resolve_type_node(decl.target, env, sink);
      env.sigils.clear();
      for (const [key, value] of previous) env.sigils.set(key, value);
      const alias: AliasInfo = {
        kind: "alias",
        name: decl.name,
        seal: decl.kind === "seal_decl",
        target,
        sigils: decl.sigils,
        span: decl.name_span,
        methods: new Map(),
      };
      env.aliases.set(decl.name, alias);
      break;
    }
    default:
      break;
  }
}

function register_rune(rune: RuneDecl, env: TypeEnv, sink: DiagnosticSink, meld = false): void {
  if (env.runes.has(rune.name) || env.omens.has(rune.name) || env.aliases.has(rune.name)) {
    duplicate(sink, rune.name, rune.name_span);
    return;
  }

  const previous = new Map(env.sigils);
  for (const sigil of rune.sigils) env.sigils.set(sigil, generic_type(sigil));

  const fields = new Map<string, FieldInfo>();
  for (const field of rune.fields) {
    const type = resolve_type_node(field.type, env, sink);
    if (fields.has(field.name)) {
      sink.add(make_error(CODES.duplicate_symbol, `el campo «${field.name}» está repetido`, field.span));
      continue;
    }
    fields.set(field.name, {
      name: field.name,
      type,
      has_default: field.default_value !== undefined,
      bits: field.bits,
      span: field.span,
    });
  }

  const params = rune.constructor
    ? resolve_params(rune.constructor.params, env, sink)
    : [];

  const info: RuneInfo = {
    kind: "rune",
    name: rune.name,
    meld,
    sigils: rune.sigils,
    fields,
    methods: new Map(),
    constructor: rune.constructor
      ? { params: params.map((param) => param.type), span: rune.constructor.span }
      : undefined,
    parent: rune.parent,
    span: rune.name_span,
  };
  env.runes.set(rune.name, info);
  restore_sigils(env, previous);
}

function register_omen(omen: OmenDecl, env: TypeEnv, sink: DiagnosticSink): void {
  if (env.runes.has(omen.name) || env.omens.has(omen.name) || env.aliases.has(omen.name)) {
    duplicate(sink, omen.name, omen.name_span);
    return;
  }

  const previous = new Map(env.sigils);
  for (const sigil of omen.sigils) env.sigils.set(sigil, generic_type(sigil));

  const underlying = omen.underlying ? resolve_type_node(omen.underlying, env, sink) : undefined;
  const variants = new Map<
    string,
    { name: string; payload: readonly PenguType[]; value: number | undefined; span: Span }
  >();

  for (const variant of omen.variants) {
    if (variants.has(variant.name)) {
      sink.add(
        make_error(CODES.duplicate_symbol, `la variante «${variant.name}» está repetida`, variant.span),
      );
      continue;
    }
    const payload = variant.payload.map((type) => resolve_type_node(type, env, sink));
    const value =
      variant.value?.kind === "int_lit" ? Number.parseInt(variant.value.value, 10) : undefined;
    variants.set(variant.name, {
      name: variant.name,
      payload,
      value: Number.isNaN(value) ? undefined : value,
      span: variant.span,
    });
  }

  const info: OmenInfo = {
    kind: "omen",
    name: omen.name,
    sigils: omen.sigils,
    is_flags: omen.is_flags,
    underlying,
    variants,
    span: omen.name_span,
  };
  env.omens.set(omen.name, info);
  restore_sigils(env, previous);
}

function register_enchanting(
  decl: EnchantingDecl,
  env: TypeEnv,
  sink: DiagnosticSink,
  realm: string,
): void {
  const rune = env.runes.get(decl.target);
  const omen = env.omens.get(decl.target);
  const alias = env.aliases.get(decl.target);

  if (!rune && !omen && !alias) {
    register_builtin_enchanting(decl, env, sink, realm);
    return;
  }

  const previous = new Map(env.sigils);
  const target_sigils = rune?.sigils ?? omen?.sigils ?? [];
  for (const sigil of [...target_sigils, ...decl.sigils]) env.sigils.set(sigil, generic_type(sigil));

  for (const method of decl.methods) {
    const info = resolve_method(method, env, sink);
    const previous_method = rune?.methods.get(info.name) ?? alias?.methods.get(info.name);
    if (previous_method !== undefined) {
      // Los métodos de un rune o de un sello viven en un `Map` por nombre:
      // no hay sobrecargas por aridad. Antes se sobrescribían en silencio.
      sink.add(
        make_error(
          CODES.enchant_duplicate,
          `«${decl.target}.${info.name}» ya está definido: un método no se puede sobrecargar (usa nombres distintos o una función libre)`,
          method.name_span,
        ),
      );
      continue;
    }
    if (rune) {
      rune.methods.set(info.name, info);
    } else if (alias) {
      alias.methods.set(info.name, info);
    } else if (omen) {
      // Los métodos de omens son de solo lectura; se guardan igual.
      const existing = omen_methods.get(omen);
      const map = existing ?? new Map<string, MethodInfo>();
      map.set(info.name, info);
      omen_methods.set(omen, map);
    }
  }

  restore_sigils(env, previous);
}

// Dos métodos son la misma firma si coinciden en parámetros, variádicas y
// mutabilidad del receptor. Se usa para detectar duplicados (E0707).
export function same_method_signature(left: MethodInfo, right: MethodInfo): boolean {
  if (left.mutable !== right.mutable || left.variadic !== right.variadic) return false;
  if (left.params.length !== right.params.length) return false;
  return left.params.every((type, index) => type_display(type) === type_display(right.params[index]!));
}

// `enchanting` sobre un tipo incorporado: primitivos, contenedores y la
// familia de `string`. Se registra por `base/aridad`.
function register_builtin_enchanting(
  decl: EnchantingDecl,
  env: TypeEnv,
  sink: DiagnosticSink,
  realm: string,
): void {
  const target = enchant_target_of(decl.target);
  if (target === undefined) {
    const suggestion = suggest_name(decl.target, [...enchant_target_names(), ...env.runes.keys(), ...env.omens.keys()]);
    const hint = suggestion === undefined ? "" : `; ¿quisiste decir «${suggestion}»?`;
    sink.add(
      make_error(
        CODES.unknown_enchant_target,
        `«${decl.target}» no es un tipo al que se pueda enhechizar${hint}`,
        decl.target_span,
      ),
    );
    return;
  }

  const arity = type_pattern_arity(decl.target_type);
  if (!target.arities.includes(arity)) {
    const expected = target.arities.map(String).join(" o ");
    sink.add(
      make_error(
        CODES.enchant_arity,
        `«${decl.target}» espera ${expected} argumento(s) de tipo, recibió ${arity}`,
        decl.target_span,
      ),
    );
    return;
  }

  const previous = new Map(env.sigils);
  for (const sigil of decl.sigils) env.sigils.set(sigil, generic_type(sigil));

  const key = enchant_key(decl.target, arity);
  let entry: EnchantedType | undefined = env.enchants.get(key);
  if (entry === undefined) {
    entry = { base: decl.target, arity, sigils: [...decl.sigils], methods: new Map() };
    env.enchants.set(key, entry);
  }

  for (const method of decl.methods) {
    if (method.mutable && decl.target === "weak") {
      sink.add(
        make_error(
          CODES.invalid_mut_receiver,
          "«weak<T>» no permite métodos «mut»: el valor puede haber expirado; usa «is_alive» y «lock»",
          method.name_span,
        ),
      );
      continue;
    }
    if (method.mutable && !target.reference) {
      sink.add(
        make_error(
          CODES.invalid_mut_receiver,
          `«${decl.target}» es un tipo por valor: un método «mut» no puede modificar el receptor`,
          method.name_span,
        ),
      );
      continue;
    }
    const info = resolve_method(method, env, sink);
    const list = entry.methods.get(info.name) ?? [];
    if (list.some((existing) => same_method_signature(existing.info, info))) {
      sink.add(
        make_error(
          CODES.enchant_duplicate,
          `«${decl.target}.${info.name}» ya está enhechizado con esa firma en el realm «${realm}»`,
          method.name_span,
        ),
      );
      continue;
    }
    list.push({ info, realm });
    entry.methods.set(info.name, list);
  }

  restore_sigils(env, previous);
}

const omen_methods = new WeakMap<OmenInfo, Map<string, MethodInfo>>();

export function omen_methods_of(omen: OmenInfo): Map<string, MethodInfo> | undefined {
  return omen_methods.get(omen);
}

export function resolve_method(method: MethodDecl, env: TypeEnv, sink: DiagnosticSink): MethodInfo {
  const sigils = [...env.sigils.keys()];
  const params = resolve_params(method.params, env, sink);
  const declared = method.result ? resolve_type_node(method.result, env, sink) : UNKNOWN;
  const result = method.is_async ? future_type(declared) : declared;
  return {
    name: method.operator ?? method.name,
    params: params.map((param) => param.type),
    param_mutables: params.map((param) => param.mutable),
    variadic: params.some((param) => param.variadic),
    required: params.filter((param) => !param.has_default && !param.variadic).length,
    result,
    mutable: method.mutable,
    is_async: method.is_async,
    operator: method.operator,
    sigils,
    span: method.name_span,
  };
}

export function resolve_params(
  params: readonly ParamNode[],
  env: TypeEnv,
  sink: DiagnosticSink,
): readonly ParamInfo[] {
  return params.map((param) => ({
    name: param.name,
    type: param.type ? resolve_type_node(param.type, env, sink) : UNKNOWN,
    has_default: param.default_value !== undefined,
    mutable: param.mutable,
    variadic: param.variadic,
    span: param.span,
  }));
}

function register_import(decl: Extract<DeclNode, { kind: "invoke_decl" }>, imports: Map<string, ImportInfo>, sink: DiagnosticSink): void {
  const trimmed = decl.path.replace(/^\.\//, "");
  const alias = decl.alias ?? trimmed.split("/").filter(Boolean).pop() ?? trimmed;
  const explicit = decl.alias !== undefined;
  const items = decl.items?.map((item) => ({ name: item.name, alias: item.alias }));
  const existing = imports.get(alias);
  if (existing !== undefined) {
    // Dos `invoke {…} from "mismo/módulo"` son legales: se acumulan los símbolos.
    if (existing.items !== undefined && items !== undefined) {
      imports.set(alias, { ...existing, items: [...existing.items, ...items] });
      return;
    }
    sink.add(make_error(CODES.duplicate_symbol, `el módulo «${alias}» ya está importado`, decl.span));
    return;
  }
  imports.set(alias, { path: decl.path, alias, explicit, items, span: decl.span });
}

function register_extern(
  declared: DeclareDecl,
  env: TypeEnv,
  functions: Map<string, FunctionInfo>,
  sink: DiagnosticSink,
): void {
  if (functions.has(declared.name)) {
    duplicate(sink, declared.name, declared.name_span);
    return;
  }
  const params = declared.params.map((param) => ({
    name: param.name,
    type: param.type ? resolve_type_node(param.type, env, sink) : UNKNOWN,
    has_default: false,
    mutable: param.mutable,
    variadic: param.variadic,
    span: param.span,
  }));
  functions.set(declared.name, {
    kind: "function",
    name: declared.name,
    sigils: [],
    needs: [],
    params,
    variadic: params.some((param) => param.variadic),
    result: declared.result ? resolve_type_node(declared.result, env, sink) : VOID,
    decl: undefined,
    is_unsafe: false,
    is_async: false,
    is_extern: true,
    is_intrinsic: false,
    span: declared.name_span,
  });
}

// `declare`: firmas que implementa el compilador en el runtime.
function register_intrinsic(
  declared: DeclareDecl,
  env: TypeEnv,
  functions: Map<string, FunctionInfo>,
  sink: DiagnosticSink,
): void {
  if (functions.has(declared.name)) {
    duplicate(sink, declared.name, declared.name_span);
    return;
  }
  const params = declared.params.map((param) => ({
    name: param.name,
    type: param.type ? resolve_type_node(param.type, env, sink) : UNKNOWN,
    has_default: false,
    mutable: param.mutable,
    variadic: param.variadic,
    span: param.span,
  }));
  functions.set(declared.name, {
    kind: "function",
    name: declared.name,
    sigils: [],
    needs: [],
    params,
    variadic: params.some((param) => param.variadic),
    result: declared.result ? resolve_type_node(declared.result, env, sink) : VOID,
    decl: undefined,
    is_unsafe: false,
    is_async: false,
    is_extern: false,
    is_intrinsic: true,
    span: declared.name_span,
  });
}

function register_function(
  decl: FunctionDecl,
  env: TypeEnv,
  functions: Map<string, FunctionInfo>,
  sink: DiagnosticSink,
): void {
  if (functions.has(decl.name) || env.runes.has(decl.name) || env.omens.has(decl.name)) {
    duplicate(sink, decl.name, decl.name_span);
    return;
  }

  const previous = new Map(env.sigils);
  for (const sigil of decl.sigils) env.sigils.set(sigil, generic_type(sigil));

  const params = resolve_params(decl.params, env, sink);
  const declared = decl.result ? resolve_type_node(decl.result, env, sink) : UNKNOWN;

  restore_sigils(env, previous);

  functions.set(decl.name, {
    kind: "function",
    name: decl.name,
    sigils: decl.sigils,
    needs: decl.needs,
    params,
    variadic: params.some((param) => param.variadic),
    result: decl.is_async ? future_type(declared) : declared,
    decl,
    is_unsafe: decl.is_unsafe,
    is_async: decl.is_async,
    is_extern: false,
    is_intrinsic: false,
    span: decl.name_span,
  });
}

function register_const(
  decl: ConstDecl,
  env: TypeEnv,
  consts: Map<string, ConstInfo>,
  sink: DiagnosticSink,
): void {
  if (consts.has(decl.name) || env.runes.has(decl.name) || env.omens.has(decl.name)) {
    duplicate(sink, decl.name, decl.span);
    return;
  }

  const declared_type = decl.declared_type
    ? resolve_type_node(decl.declared_type, env, sink)
    : undefined;

  consts.set(decl.name, {
    kind: "const",
    name: decl.name,
    is_define: decl.is_define,
    declared_type,
    decl,
    is_static: decl.is_static,
    mutable: decl.mutable,
    span: decl.span,
    type: declared_type ?? UNKNOWN,
    evaluable: false,
  });
}

function restore_sigils(env: TypeEnv, previous: Map<string, PenguType>): void {
  env.sigils.clear();
  for (const [key, value] of previous) env.sigils.set(key, value);
}

function duplicate(sink: DiagnosticSink, name: string, span: Span): void {
  sink.add(make_error(CODES.duplicate_symbol, `«${name}» ya está declarado en este módulo`, span));
}

// Tipo función de un símbolo, con la aridad mínima que exigen los
// parámetros sin valor por defecto.
export function function_type_of(info: FunctionInfo): PenguType {
  return function_type(
    info.params.map((param) => param.type),
    info.result,
    info.variadic,
    info.params.filter((param) => !param.has_default && !param.variadic).length,
  );
}
