// Orden de emisión de las declaraciones de tipo.
//
// C++ exige que un tipo esté completo antes de usarse: una rune hija
// necesita a su padre, y un alias necesita el tipo al que apunta. El
// código de PenguScript no obliga a declararlos en orden, así que aquí
// se ordenan topológicamente antes de emitirlos.

import type { DeclNode } from "../frontend/ast_decl.ts";

export type TypeDecl = Extract<DeclNode, { kind: "rune_decl" | "meld_decl" | "omen_decl" | "echo_decl" | "seal_decl" }>;

export function is_type_decl(decl: DeclNode): decl is TypeDecl {
  return (
    decl.kind === "rune_decl" ||
    decl.kind === "meld_decl" ||
    decl.kind === "omen_decl" ||
    decl.kind === "echo_decl" ||
    decl.kind === "seal_decl"
  );
}

// Nombres de tipos que esta declaración necesita completos antes de
// poder emitirse.
function dependencies_of(decl: TypeDecl): readonly string[] {
  switch (decl.kind) {
    case "rune_decl":
      return decl.parent === undefined ? [] : [decl.parent];
    case "meld_decl":
      return [];
    case "echo_decl":
      return decl.target.kind === "named_type" ? [decl.target.name] : [];
    case "seal_decl":
      return decl.target.kind === "named_type" ? [decl.target.name] : [];
    case "omen_decl":
      return [];
  }
}

export function type_decl_name(decl: TypeDecl): string {
  return decl.name;
}

// Orden estable: conserva el orden original salvo cuando un tipo
// depende de otro declarado más tarde.
export function order_type_decls(decls: readonly TypeDecl[]): readonly TypeDecl[] {
  const by_name = new Map<string, TypeDecl>();
  for (const decl of decls) by_name.set(type_decl_name(decl), decl);

  const ordered: TypeDecl[] = [];
  const visiting = new Set<string>();
  const done = new Set<string>();

  const visit = (decl: TypeDecl): void => {
    const name = type_decl_name(decl);
    if (done.has(name)) return;
    if (visiting.has(name)) return; // ciclo: se queda en orden de aparición
    visiting.add(name);
    for (const dependency of dependencies_of(decl)) {
      const target = by_name.get(dependency);
      if (target !== undefined) visit(target);
    }
    visiting.delete(name);
    done.add(name);
    ordered.push(decl);
  };

  for (const decl of decls) visit(decl);
  return ordered;
}

// ¿Cuántos hijos directos declara el módulo para esta rune?
export function heir_names(decls: readonly DeclNode[]): ReadonlySet<string> {
  const heirs = new Set<string>();
  for (const decl of decls) {
    if (decl.kind === "rune_decl" && decl.parent !== undefined) heirs.add(decl.parent);
  }
  return heirs;
}
