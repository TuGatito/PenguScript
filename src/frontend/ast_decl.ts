// Declaraciones de nivel superior.
//
// Cada archivo `.pengu` es un módulo con un realm, invokes y
// declaraciones. El AST conserva el orden original para que el
// formateador y el LSP puedan reconstruir el archivo.

import type { Span } from "../util/span.ts";
import type { Block } from "./ast_stmt.ts";
import type { ExprNode } from "./ast_expr.ts";
import type { ParamNode } from "./ast_param.ts";
import type { TypeNode } from "./ast_type.ts";

export type DeclNode =
  | RealmDecl
  | InvokeDecl
  | ConstDecl
  | FunctionDecl
  | RuneDecl
  | EnchantingDecl
  | OmenDecl
  | EchoDecl
  | SealDecl
  | ExternDecl
  | IntrinsicDecl
  | LinkDecl
  | OpaqueDecl
  | CallbackDecl
  | MeldDecl
  | HostTypeDecl
  | HostGlobalDecl
  | HostNamespaceDecl;

export interface RealmDecl {
  readonly kind: "realm_decl";
  readonly name: string;
  readonly span: Span;
}

export interface InvokeItem {
  readonly name: string;
  readonly alias: string | undefined;
  readonly span: Span;
}

export interface InvokeDecl {
  readonly kind: "invoke_decl";
  readonly path: string;
  readonly alias: string | undefined;
  readonly items: readonly InvokeItem[] | undefined;
  readonly span: Span;
}

export interface ConstDecl {
  readonly kind: "const_decl";
  readonly name: string;
  readonly declared_type: TypeNode | undefined;
  readonly value: ExprNode;
  readonly is_static: boolean;
  readonly mutable: boolean;
  // `define NOMBRE = valor`: se emite `inline constexpr` y es exportable.
  readonly is_define: boolean;
  readonly span: Span;
}

export interface FunctionDecl {
  readonly kind: "function_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  readonly needs: readonly string[];
  readonly params: readonly ParamNode[];
  readonly result: TypeNode | undefined;
  readonly body: Block;
  readonly is_unsafe: boolean;
  readonly is_async: boolean;
  // Presente en los operadores libres (`operator + = (a, b) -> T`):
  // el nombre real de la función es el símbolo del operador.
  readonly operator?: string;
  readonly span: Span;
}

export interface FieldDecl {
  readonly name: string;
  readonly type: TypeNode;
  readonly default_value: ExprNode | undefined;
  // `bits N nombre: Tipo`: ancho del bitfield; `undefined` si no lo es.
  readonly bits: number | undefined;
  readonly span: Span;
}

export interface ConstructorDecl {
  readonly params: readonly ParamNode[];
  readonly body: Block;
  readonly span: Span;
}

export interface RuneDecl {
  readonly kind: "rune_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  readonly parent: string | undefined;
  readonly fields: readonly FieldDecl[];
  readonly constructor: ConstructorDecl | undefined;
  readonly destructor: Block | undefined;
  readonly span: Span;
}

export interface MethodDecl {
  readonly name: string;
  readonly name_span: Span;
  readonly operator: string | undefined;
  readonly mutable: boolean;
  readonly sigils: readonly string[];
  readonly needs: readonly string[];
  readonly params: readonly ParamNode[];
  readonly result: TypeNode | undefined;
  readonly body: Block;
  readonly is_unsafe: boolean;
  readonly is_async: boolean;
  readonly span: Span;
}

export interface EnchantingDecl {
  readonly kind: "enchanting_decl";
  readonly target: string;
  readonly target_span: Span;
  // Tipo patrón completo: `string`, `vector<T>`, `tuple<int, string>`.
  readonly target_type: TypeNode;
  readonly sigils: readonly string[];
  readonly methods: readonly MethodDecl[];
  readonly span: Span;
}

export interface OmenVariant {
  readonly name: string;
  readonly name_span: Span;
  readonly payload: readonly TypeNode[];
  readonly value: ExprNode | undefined;
  readonly span: Span;
}

export interface OmenDecl {
  readonly kind: "omen_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  readonly underlying: TypeNode | undefined;
  readonly is_flags: boolean;
  readonly variants: readonly OmenVariant[];
  readonly span: Span;
}

export interface EchoDecl {
  readonly kind: "echo_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  readonly target: TypeNode;
  readonly span: Span;
}

export interface SealDecl {
  readonly kind: "seal_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  readonly target: TypeNode;
  readonly span: Span;
}

// Enlaces al host (`host js::Document`): describen objetos de JavaScript
// (DOM, Canvas, `Storage`, …) sin código. Solo existen en el backend JS.
//
//   host js::Node heir js::EventTarget
//     nodeName: string
//     mut id: string
//     appendChild<T>(nodo: T) -> T
//     constructor(x: double)
//     [indice: int]: string
//     static from(x: double) -> js::Node
export interface HostProperty {
  readonly kind: "host_property";
  readonly name: string;
  readonly name_span: Span;
  readonly type: TypeNode;
  readonly mutable: boolean;
  // `nombre?: tipo`: puede faltar (se tipa `T?`).
  readonly optional: boolean;
  readonly span: Span;
}

export interface HostMethod {
  readonly kind: "host_method";
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  readonly params: readonly ParamNode[];
  readonly result: TypeNode | undefined;
  readonly is_static: boolean;
  readonly optional: boolean;
  readonly span: Span;
}

export interface HostConstructor {
  readonly kind: "host_constructor";
  readonly params: readonly ParamNode[];
  readonly span: Span;
}

export interface HostIndex {
  readonly kind: "host_index";
  readonly key_name: string;
  readonly key_type: TypeNode;
  readonly value: TypeNode;
  readonly mutable: boolean;
  readonly span: Span;
}

export type HostMember = HostProperty | HostMethod | HostConstructor | HostIndex;

export interface HostTypeDecl {
  readonly kind: "host_decl";
  // Nombre cualificado tal cual: `js::Document`.
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  // `heir js::Node`: el tipo base del host (se emite como `extends`).
  readonly parent: TypeNode | undefined;
  readonly members: readonly HostMember[];
  readonly span: Span;
}

// `host global document: js::Document`: un objeto o función global.
export interface HostGlobalDecl {
  readonly kind: "host_global_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly type: TypeNode | undefined;
  readonly span: Span;
}

// `host namespace Math`: funciones y constantes estáticas del host.
export interface HostNamespaceDecl {
  readonly kind: "host_namespace_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly members: readonly HostMember[];
  readonly span: Span;
}

export interface DeclareDecl {
  readonly name: string;
  readonly name_span: Span;
  readonly params: readonly ParamNode[];
  readonly result: TypeNode | undefined;
  readonly variadic: boolean;
  readonly span: Span;
}

export interface ExternDecl {
  readonly kind: "extern_decl";
  readonly abi: string | undefined;
  readonly declares: readonly DeclareDecl[];
  readonly span: Span;
}

// `declare`: funciones del runtime que implementa el compilador (stdlib).
export interface IntrinsicDecl {
  readonly kind: "intrinsic_decl";
  readonly declares: readonly DeclareDecl[];
  readonly span: Span;
}

// `link "raylib"`: bibliotecas que el módulo necesita al enlazar.
export interface LinkDecl {
  readonly kind: "link_decl";
  readonly path: string;
  readonly span: Span;
}

// `opaque rAudioBuffer`: tipo incompleto; solo se usa dentro de `raw`/`ref`.
export interface OpaqueDecl {
  readonly kind: "opaque_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly span: Span;
}

// `callback TraceLogCallback = (nivel: int, texto: string) -> void`:
// puntero a función con ABI C.
export interface CallbackDecl {
  readonly kind: "callback_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly params: readonly ParamNode[];
  readonly result: TypeNode;
  readonly span: Span;
}

// `meld Value`: unión C con campos triviales.
export interface MeldDecl {
  readonly kind: "meld_decl";
  readonly name: string;
  readonly name_span: Span;
  readonly sigils: readonly string[];
  readonly fields: readonly FieldDecl[];
  readonly span: Span;
}
