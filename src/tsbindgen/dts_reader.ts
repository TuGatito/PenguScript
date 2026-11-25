// Lector de `.d.ts`: de la Compiler API de TypeScript al IR de dts_ast.ts.
//
// Solo se usa desde `pengu ts-bindgen`; el compilador nunca importa este módulo,
// así que `typescript5` sigue siendo una dependencia de desarrollo.
//
// La API que se usa es la mínima: `createSourceFile` y los predicados de nodo.
// No hay `Program` ni resolución de módulos porque los `.d.ts` de la librería
// estándar son *ambient* y globales: todo se referencia por nombre.

import ts from "typescript5";
import type {
  DtsClass,
  DtsDoc,
  DtsEnum,
  DtsEnumMember,
  DtsFunction,
  DtsGlobal,
  DtsHeritage,
  DtsInterface,
  DtsModule,
  DtsNamespace,
  DtsNode,
  DtsNamedNode,
  DtsStats,
  DtsTypeAlias,
  DtsVar,
} from "./dts_ast.ts";
import { empty_stats, walk_named } from "./dts_ast.ts";
import type {
  DtsMember,
  DtsParam,
  DtsSpan,
  DtsType,
} from "./dts_type.ts";
import { ref_type, unsupported_type } from "./dts_type.ts";

export interface DtsSource {
  readonly file: string;
  readonly text: string;
}

interface ReadState {
  readonly source: ts.SourceFile;
  readonly file: string;
  stats: {
    interfaces: number;
    classes: number;
    aliases: number;
    vars: number;
    functions: number;
    namespaces: number;
    enums: number;
    members: number;
    unsupported: number;
  };
}

const KEYWORDS: ReadonlyMap<ts.SyntaxKind, string> = new Map<
  ts.SyntaxKind,
  string
>([
  [ts.SyntaxKind.StringKeyword, "string"],
  [ts.SyntaxKind.NumberKeyword, "number"],
  [ts.SyntaxKind.BooleanKeyword, "boolean"],
  [ts.SyntaxKind.VoidKeyword, "void"],
  [ts.SyntaxKind.AnyKeyword, "any"],
  [ts.SyntaxKind.UnknownKeyword, "unknown"],
  [ts.SyntaxKind.ObjectKeyword, "object"],
  [ts.SyntaxKind.BigIntKeyword, "bigint"],
  [ts.SyntaxKind.SymbolKeyword, "symbol"],
  [ts.SyntaxKind.NeverKeyword, "never"],
  [ts.SyntaxKind.UndefinedKeyword, "undefined"],
  [ts.SyntaxKind.NullKeyword, "null"],
]);

export function read_dts_text(file: string, text: string): DtsModule {
  const source = ts.createSourceFile(
    file,
    text,
    ts.ScriptTarget.ES2022,
    true,
    ts.ScriptKind.TS,
  );
  const state: ReadState = {
    source,
    file,
    stats: empty_stats(),
  };
  const nodes = read_statements(state, source.statements);
  const named = walk_named(nodes);
  const by_name = new Map<string, DtsNamedNode>();
  for (const node of named) {
    if (!by_name.has(node.name)) by_name.set(node.name, node);
  }
  return {
    file,
    nodes,
    by_name,
    stats: state.stats,
  };
}

export function read_dts_file(path: string): DtsModule {
  return read_dts_text(path, ts.sys.readFile(path) ?? "");
}

// --- declaraciones ---------------------------------------------------------

function read_statements(
  state: ReadState,
  statements: readonly ts.Statement[],
): DtsNode[] {
  const out: DtsNode[] = [];
  for (const statement of statements) {
    if (ts.isVariableStatement(statement)) {
      out.push(...read_variables(state, statement));
      continue;
    }
    const node = read_statement(state, statement);
    if (node !== undefined) out.push(node);
  }
  return out;
}

function read_statement(
  state: ReadState,
  statement: ts.Statement,
): DtsNode | undefined {
  if (ts.isInterfaceDeclaration(statement)) {
    return read_interface(state, statement);
  }
  if (ts.isClassDeclaration(statement)) {
    return read_class(state, statement);
  }
  if (ts.isTypeAliasDeclaration(statement)) {
    return read_alias(state, statement);
  }
  if (ts.isFunctionDeclaration(statement)) {
    return read_function(state, statement);
  }
  if (ts.isModuleDeclaration(statement)) {
    return read_module(state, statement);
  }
  if (ts.isEnumDeclaration(statement)) {
    return read_enum(state, statement);
  }
  return undefined;
}

function read_interface(
  state: ReadState,
  node: ts.InterfaceDeclaration,
): DtsInterface | undefined {
  const name = node.name.text;
  if (name === "") return undefined;
  state.stats.interfaces += 1;
  const members = read_members(state, node.members);
  state.stats.members += members.length;
  return {
    kind: "interface",
    name,
    type_params: type_params_of(node),
    heritage: read_heritage(state, node),
    members,
    span: span_of(state, node),
    ...doc_of(node),
  };
}

function read_class(
  state: ReadState,
  node: ts.ClassDeclaration,
): DtsClass | undefined {
  const name = node.name?.text;
  if (name === undefined || name === "") return undefined;
  state.stats.classes += 1;
  const members = read_members(state, node.members);
  state.stats.members += members.length;
  const abstract = has_modifier(node, ts.SyntaxKind.AbstractKeyword);
  return {
    kind: "class",
    name,
    type_params: type_params_of(node),
    heritage: read_heritage(state, node),
    members,
    abstract,
    span: span_of(state, node),
    ...doc_of(node),
  };
}

function read_alias(
  state: ReadState,
  node: ts.TypeAliasDeclaration,
): DtsTypeAlias {
  state.stats.aliases += 1;
  return {
    kind: "alias",
    name: node.name.text,
    type_params: type_params_of(node),
    type: read_type(state, node.type),
    span: span_of(state, node),
    ...doc_of(node),
  };
}

function read_variables(
  state: ReadState,
  node: ts.VariableStatement,
): DtsVar[] {
  const list = node.declarationList;
  const readonly = (list.flags & ts.NodeFlags.Const) !== 0;
  const out: DtsVar[] = [];
  for (const declaration of list.declarations) {
    if (!ts.isIdentifier(declaration.name)) continue;
    state.stats.vars += 1;
    const type =
      declaration.type === undefined
        ? unsupported_type("", "sin anotación de tipo")
        : read_type(state, declaration.type);
    out.push({
      kind: "var",
      name: declaration.name.text,
      type,
      readonly,
      span: span_of(state, declaration),
      ...doc_of(node),
    });
  }
  return out;
}

function read_function(
  state: ReadState,
  node: ts.FunctionDeclaration,
): DtsFunction | undefined {
  const name = node.name?.text;
  if (name === undefined || name === "") return undefined;
  state.stats.functions += 1;
  return {
    kind: "function",
    name,
    type_params: type_params_of(node),
    params: read_params(state, node.parameters),
    result: read_return(state, node.type),
    span: span_of(state, node),
    ...doc_of(node),
  };
}

function read_module(
  state: ReadState,
  node: ts.ModuleDeclaration,
): DtsGlobal | DtsNamespace | undefined {
  const body = node.body;
  if (body === undefined) return undefined;
  const inner: ts.Node = body;
  if (!ts.isModuleBlock(inner)) {
    return undefined;
  }
  const nodes = read_statements(state, inner.statements);
  if (node.flags & ts.NodeFlags.GlobalAugmentation) {
    return { kind: "global", nodes, span: span_of(state, node) };
  }
  if (!ts.isIdentifier(node.name)) return undefined;
  state.stats.namespaces += 1;
  return {
    kind: "namespace",
    name: node.name.text,
    nodes,
    span: span_of(state, node),
    ...doc_of(node),
  };
}

function read_enum(
  state: ReadState,
  node: ts.EnumDeclaration,
): DtsEnum | undefined {
  const name = node.name.text;
  if (name === "") return undefined;
  state.stats.enums += 1;
  const members: DtsEnumMember[] = [];
  for (const member of node.members) {
    if (!ts.isIdentifier(member.name)) continue;
    const value =
      member.initializer === undefined
        ? undefined
        : member.initializer.getText(state.source);
    members.push({
      name: member.name.text,
      value,
      span: span_of(state, member),
    });
  }
  const is_const = has_modifier(node, ts.SyntaxKind.ConstKeyword);
  return {
    kind: "enum",
    name,
    const: is_const,
    members,
    span: span_of(state, node),
    ...doc_of(node),
  };
}

// --- miembros --------------------------------------------------------------

function read_members(
  state: ReadState,
  members: readonly ts.Node[],
): DtsMember[] {
  const out: DtsMember[] = [];
  const accessors = new Map<
    string,
    { get?: ts.GetAccessorDeclaration; set?: ts.SetAccessorDeclaration }
  >();
  for (const raw of members) {
    const member = raw as ts.ClassElement | ts.TypeElement;
    if (ts.isPropertySignature(member) || ts.isPropertyDeclaration(member)) {
      if (!is_public(member)) continue;
      if (!member.name) continue;
      const name = member_name(state, member.name);
      if (name === undefined) continue;
      state.stats.members += 1;
      out.push({
        kind: "property",
        name,
        type:
          member.type === undefined
            ? unsupported_type("", "sin anotación de tipo")
            : read_type(state, member.type),
        readonly:
          has_modifier(member, ts.SyntaxKind.ReadonlyKeyword) ||
          has_modifier(member, ts.SyntaxKind.ReadonlyKeyword),
        optional: has_question_token(member),
        span: span_of(state, member),
        ...doc_of(member),
      });
      continue;
    }
    if (ts.isMethodSignature(member) || ts.isMethodDeclaration(member)) {
      if (!is_public(member)) continue;
      if (!member.name) continue;
      const name = member_name(state, member.name);
      if (name === undefined) continue;
      state.stats.members += 1;
      out.push({
        kind: "method",
        name,
        type_params: type_params_of(member),
        params: read_params(state, member.parameters),
        result: read_return(state, member.type),
        optional: has_question_token(member),
        span: span_of(state, member),
        ...doc_of(member),
      });
      continue;
    }
    if (ts.isIndexSignatureDeclaration(member)) {
      const params = read_params(state, member.parameters);
      const key = params[0]?.type ?? { kind: "keyword", name: "string" };
      state.stats.members += 1;
      out.push({
        kind: "index",
        key,
        value: read_return(state, member.type),
        readonly: has_modifier(member, ts.SyntaxKind.ReadonlyKeyword),
        span: span_of(state, member),
      });
      continue;
    }
    if (
      ts.isConstructSignatureDeclaration(member) ||
      ts.isConstructorDeclaration(member)
    ) {
      state.stats.members += 1;
      out.push({
        kind: "construct",
        params: read_params(state, member.parameters),
        span: span_of(state, member),
      });
      continue;
    }
    if (ts.isCallSignatureDeclaration(member)) {
      state.stats.members += 1;
      out.push({
        kind: "call",
        params: read_params(state, member.parameters),
        result: read_return(state, member.type),
        span: span_of(state, member),
      });
      continue;
    }
    if (ts.isGetAccessorDeclaration(member) || ts.isSetAccessorDeclaration(member)) {
      const name = member_name(state, member.name);
      if (name === undefined) continue;
      const entry = accessors.get(name) ?? {};
      if (ts.isGetAccessorDeclaration(member)) entry.get = member;
      else entry.set = member;
      accessors.set(name, entry);
      continue;
    }
  }
  for (const [name, entry] of accessors) {
    const get = entry.get;
    const set = entry.set;
    const type =
      get !== undefined && get.type !== undefined
        ? read_type(state, get.type)
        : set !== undefined && set.parameters[0]?.type !== undefined
          ? read_type(state, set.parameters[0].type)
          : unsupported_type("", "accesor sin tipo");
    state.stats.members += 1;
    out.push({
      kind: "property",
      name,
      type,
      readonly: set === undefined,
      optional: false,
      span: span_of(state, (get ?? set) as ts.Node),
      ...doc_of((get ?? set) as ts.Node),
    });
  }
  return out;
}

function member_name(
  state: ReadState,
  name: ts.PropertyName | ts.EntityName,
): string | undefined {
  if (ts.isIdentifier(name)) return name.text;
  if (ts.isStringLiteral(name) || ts.isNumericLiteral(name)) return name.text;
  if (ts.isComputedPropertyName(name)) return undefined;
  return name.getText(state.source);
}

function is_public(member: ts.Node): boolean {
  return (
    !has_modifier(member, ts.SyntaxKind.PrivateKeyword) &&
    !has_modifier(member, ts.SyntaxKind.ProtectedKeyword)
  );
}

function has_modifier(node: ts.Node, kind: ts.SyntaxKind): boolean {
  const modifiers = ts.canHaveModifiers(node) ? ts.getModifiers(node) : undefined;
  if (modifiers === undefined) return false;
  return modifiers.some((modifier) => modifier.kind === kind);
}

function has_question_token(node: ts.Node): boolean {
  return (node as { questionToken?: ts.QuestionToken }).questionToken !== undefined;
}

function type_params_of(node: ts.Node): string[] {
  const params = (node as { typeParameters?: readonly ts.TypeParameterDeclaration[] })
    .typeParameters;
  if (params === undefined) return [];
  return params.map((param) => param.name.text);
}

function read_heritage(
  state: ReadState,
  node: ts.InterfaceDeclaration | ts.ClassDeclaration,
): DtsHeritage[] {
  const clauses = node.heritageClauses;
  if (clauses === undefined) return [];
  const out: DtsHeritage[] = [];
  for (const clause of clauses) {
    if (clause.token !== ts.SyntaxKind.ExtendsKeyword) continue;
    for (const type of clause.types) {
      const args = type.typeArguments?.map((arg) => read_type(state, arg)) ?? [];
      out.push({ name: entity_name_text(state, type.expression), args });
    }
  }
  return out;
}

function entity_name_text(state: ReadState, name: ts.Node): string {
  if (ts.isIdentifier(name)) return name.text;
  return name.getText(state.source).split("\n")[0] ?? name.getText(state.source);
}

// --- parámetros y tipos ----------------------------------------------------

function read_params(
  state: ReadState,
  params: readonly ts.ParameterDeclaration[],
): DtsParam[] {
  const out: DtsParam[] = [];
  for (const [index, param] of params.entries()) {
    const rest = param.dotDotDotToken !== undefined;
    const name = ts.isIdentifier(param.name)
      ? param.name.text
      : `arg${index}`;
    const type =
      param.type === undefined
        ? unsupported_type("", "parámetro sin tipo")
        : read_type(state, param.type);
    out.push({
      name,
      type: rest && type.kind === "array" ? type.element : type,
      optional: param.questionToken !== undefined || param.initializer !== undefined,
      rest,
    });
  }
  return out;
}

function read_return(
  state: ReadState,
  type: ts.TypeNode | undefined,
): DtsType {
  if (type === undefined) return { kind: "keyword", name: "void" };
  return read_type(state, type);
}

export function read_type(state: ReadState, node: ts.TypeNode): DtsType {
  const keyword = KEYWORDS.get(node.kind);
  if (keyword !== undefined) {
    return { kind: "keyword", name: keyword as "string" };
  }
  if (ts.isParenthesizedTypeNode(node)) {
    return read_type(state, node.type);
  }
  if (ts.isTypeReferenceNode(node)) {
    return ref_type(
      entity_name_text(state, node.typeName),
      node.typeArguments?.map((arg) => read_type(state, arg)) ?? [],
    );
  }
  if (ts.isArrayTypeNode(node)) {
    return { kind: "array", element: read_type(state, node.elementType) };
  }
  if (ts.isTupleTypeNode(node)) {
    return {
      kind: "tuple",
      items: node.elements.map((element) => read_type(state, tuple_element(element))),
    };
  }
  if (ts.isUnionTypeNode(node)) {
    return {
      kind: "union",
      items: node.types.map((item) => read_type(state, item)),
    };
  }
  if (ts.isIntersectionTypeNode(node)) {
    return {
      kind: "intersection",
      items: node.types.map((item) => read_type(state, item)),
    };
  }
  if (ts.isFunctionTypeNode(node)) {
    return {
      kind: "function",
      params: read_params(state, node.parameters),
      result: read_return(state, node.type),
    };
  }
  if (ts.isConstructorTypeNode(node)) {
    return {
      kind: "function",
      params: read_params(state, node.parameters),
      result: read_return(state, node.type),
    };
  }
  if (ts.isTypeLiteralNode(node)) {
    return {
      kind: "object_literal",
      members: read_members(state, node.members),
    };
  }
  if (ts.isLiteralTypeNode(node)) {
    return read_literal(state, node);
  }
  if (ts.isTypeOperatorNode(node) && node.operator === ts.SyntaxKind.KeyOfKeyword) {
    return { kind: "keyof", object: read_type(state, node.type) };
  }
  if (ts.isIndexedAccessTypeNode(node)) {
    return {
      kind: "indexed",
      object: read_type(state, node.objectType),
      index: read_type(state, node.indexType),
    };
  }
  if (ts.isThisTypeNode(node)) {
    return { kind: "this_type" };
  }
  if (ts.isTypeQueryNode(node)) {
    return { kind: "typeof", name: entity_name_text(state, node.exprName) };
  }
  if (ts.isRestTypeNode(node) || ts.isOptionalTypeNode(node)) {
    return read_type(state, node.type);
  }
  if (ts.isTypePredicateNode(node)) {
    return { kind: "keyword", name: "boolean" };
  }
  state.stats.unsupported += 1;
  return unsupported_type(node.getText(state.source), unsupported_because(node));
}

function tuple_element(element: ts.TypeNode): ts.TypeNode {
  if (ts.isNamedTupleMember(element)) return element.type;
  if (ts.isOptionalTypeNode(element)) return element.type;
  if (ts.isRestTypeNode(element)) return element.type;
  return element;
}

function read_literal(state: ReadState, node: ts.LiteralTypeNode): DtsType {
  const literal = node.literal;
  if (ts.isStringLiteral(literal)) {
    return { kind: "literal", value: literal.text };
  }
  if (ts.isNumericLiteral(literal)) {
    return { kind: "literal", value: Number(literal.text) };
  }
  if (ts.isBigIntLiteral(literal)) {
    return { kind: "literal", value: Number(literal.text.replace(/n$/, "")) };
  }
  if (literal.kind === ts.SyntaxKind.TrueKeyword) {
    return { kind: "literal", value: true };
  }
  if (literal.kind === ts.SyntaxKind.FalseKeyword) {
    return { kind: "literal", value: false };
  }
  if (literal.kind === ts.SyntaxKind.NullKeyword) {
    return { kind: "keyword", name: "null" };
  }
  if (literal.kind === ts.SyntaxKind.UndefinedKeyword) {
    return { kind: "keyword", name: "undefined" };
  }
  if (ts.isPrefixUnaryExpression(literal)) {
    const operand = literal.operand;
    if (ts.isNumericLiteral(operand)) {
      const value = Number(operand.text);
      return {
        kind: "literal",
        value: literal.operator === ts.SyntaxKind.MinusToken ? -value : value,
      };
    }
  }
  state.stats.unsupported += 1;
  return unsupported_type(literal.getText(state.source), "literal no soportado");
}

function unsupported_because(node: ts.Node): string {
  if (ts.isConditionalTypeNode(node)) return "tipo condicional";
  if (ts.isMappedTypeNode(node)) return "mapped type";
  if (ts.isTemplateLiteralTypeNode(node)) return "template literal type";
  if (ts.isInferTypeNode(node)) return "infer";
  if (ts.isImportTypeNode(node)) return "import(...) en un tipo";
  return "tipo no soportado";
}

// --- utilidades ------------------------------------------------------------

function span_of(state: ReadState, node: ts.Node): DtsSpan {
  const position = state.source.getLineAndCharacterOfPosition(node.getStart(state.source));
  return {
    file: state.file,
    line: position.line + 1,
    column: position.character + 1,
  };
}

function doc_of(node: ts.Node): DtsDoc {
  const tags = ts.getJSDocCommentsAndTags(node);
  const parts: string[] = [];
  for (const tag of tags) {
    if (!ts.isJSDoc(tag)) continue;
    const comment = tag.comment;
    if (typeof comment === "string") {
      parts.push(comment);
      continue;
    }
    if (Array.isArray(comment)) {
      for (const part of comment) {
        if (typeof part === "object" && part !== null && "text" in part) {
          parts.push(String((part as { text: string }).text));
        }
      }
    }
  }
  const text = parts.join("\n").trim();
  return text === "" ? {} : { doc: text };
}

export type { DtsStats };
