// Declaraciones de un `.d.ts` en un IR propio.
//
// Todo lo que el generador necesita saber de un archivo de declaraciones está
// aquí: nada de este módulo importa TypeScript, así que el emisor de `.d.pengu`
// y sus tests no arrastran la Compiler API.

import type { DtsMember, DtsParam, DtsSpan, DtsType } from "./dts_type.ts";

export interface DtsHeritage {
  readonly name: string;
  readonly args: readonly DtsType[];
}

export interface DtsDoc {
  readonly doc?: string;
}

export interface DtsInterface extends DtsDoc {
  readonly kind: "interface";
  readonly name: string;
  readonly type_params: readonly string[];
  readonly heritage: readonly DtsHeritage[];
  readonly members: readonly DtsMember[];
  readonly span: DtsSpan;
}

export interface DtsClass extends DtsDoc {
  readonly kind: "class";
  readonly name: string;
  readonly type_params: readonly string[];
  readonly heritage: readonly DtsHeritage[];
  readonly members: readonly DtsMember[];
  readonly abstract: boolean;
  readonly span: DtsSpan;
}

export interface DtsTypeAlias extends DtsDoc {
  readonly kind: "alias";
  readonly name: string;
  readonly type_params: readonly string[];
  readonly type: DtsType;
  readonly span: DtsSpan;
}

export interface DtsVar extends DtsDoc {
  readonly kind: "var";
  readonly name: string;
  readonly type: DtsType;
  readonly readonly: boolean;
  readonly span: DtsSpan;
}

export interface DtsFunction extends DtsDoc {
  readonly kind: "function";
  readonly name: string;
  readonly type_params: readonly string[];
  readonly params: readonly DtsParam[];
  readonly result: DtsType;
  readonly span: DtsSpan;
}

export interface DtsNamespace extends DtsDoc {
  readonly kind: "namespace";
  readonly name: string;
  readonly nodes: readonly DtsNode[];
  readonly span: DtsSpan;
}

export interface DtsEnumMember {
  readonly name: string;
  readonly value?: string;
  readonly span: DtsSpan;
}

export interface DtsEnum extends DtsDoc {
  readonly kind: "enum";
  readonly name: string;
  readonly const: boolean;
  readonly members: readonly DtsEnumMember[];
  readonly span: DtsSpan;
}

// Bloque `declare global { ... }`: lo que el archivo añade al ámbito global.
export interface DtsGlobal {
  readonly kind: "global";
  readonly nodes: readonly DtsNode[];
  readonly span: DtsSpan;
}

export type DtsNode =
  | DtsInterface
  | DtsClass
  | DtsTypeAlias
  | DtsVar
  | DtsFunction
  | DtsNamespace
  | DtsEnum
  | DtsGlobal;

export type DtsNamedNode = Exclude<DtsNode, DtsGlobal>;

export interface DtsStats {
  readonly interfaces: number;
  readonly classes: number;
  readonly aliases: number;
  readonly vars: number;
  readonly functions: number;
  readonly namespaces: number;
  readonly enums: number;
  readonly members: number;
  readonly unsupported: number;
}

export interface DtsModule {
  readonly file: string;
  readonly nodes: readonly DtsNode[];
  readonly by_name: ReadonlyMap<string, DtsNamedNode>;
  readonly stats: DtsStats;
}

export function empty_stats(): {
  interfaces: number;
  classes: number;
  aliases: number;
  vars: number;
  functions: number;
  namespaces: number;
  enums: number;
  members: number;
  unsupported: number;
} {
  return {
    interfaces: 0,
    classes: 0,
    aliases: 0,
    vars: 0,
    functions: 0,
    namespaces: 0,
    enums: 0,
    members: 0,
    unsupported: 0,
  };
}

export function node_name(node: DtsNamedNode): string {
  return node.name;
}

export function has_members(
  node: DtsNamedNode,
): node is DtsInterface | DtsClass {
  return node.kind === "interface" || node.kind === "class";
}

// Recorre el árbol (namespaces y bloques globales incluidos) y devuelve todas
// las declaraciones con nombre.
export function walk_named(nodes: readonly DtsNode[]): DtsNamedNode[] {
  const out: DtsNamedNode[] = [];
  const visit = (list: readonly DtsNode[]): void => {
    for (const node of list) {
      if (node.kind === "global" || node.kind === "namespace") {
        visit(node.nodes);
        continue;
      }
      out.push(node);
    }
  };
  visit(nodes);
  return out;
}
