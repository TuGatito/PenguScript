// Ámbitos léxicos del checker.
//
// Un ámbito es un mapa de variables con su tipo y si se pueden
// reasignar. Los ámbitos se anidan y se consultan hacia arriba.

import type { Span } from "../util/span.ts";
import type { PenguType } from "./types.ts";

export type VarKind = "param" | "local" | "const" | "global";

export interface VarInfo {
  readonly name: string;
  readonly type: PenguType;
  readonly mutable: boolean;
  readonly kind: VarKind;
  readonly span: Span;
  moved: boolean;
  borrowed: boolean;
}

export interface Scope {
  readonly parent: Scope | undefined;
  readonly vars: Map<string, VarInfo>;
}

export function make_scope(parent?: Scope): Scope {
  return { parent, vars: new Map() };
}

export function declare(
  scope: Scope,
  name: string,
  type: PenguType,
  options: { mutable?: boolean; kind?: VarKind; span: Span },
): VarInfo | undefined {
  if (scope.vars.has(name)) return undefined;
  const info: VarInfo = {
    name,
    type,
    mutable: options.mutable ?? false,
    kind: options.kind ?? "local",
    span: options.span,
    moved: false,
    borrowed: false,
  };
  scope.vars.set(name, info);
  return info;
}

export function declare_any(scope: Scope, info: VarInfo): void {
  scope.vars.set(info.name, info);
}

export function lookup(scope: Scope, name: string): VarInfo | undefined {
  let current: Scope | undefined = scope;
  while (current) {
    const found = current.vars.get(name);
    if (found) return found;
    current = current.parent;
  }
  return undefined;
}

export function current_scope_has(scope: Scope, name: string): boolean {
  return scope.vars.has(name);
}
