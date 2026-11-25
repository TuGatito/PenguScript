// Huella de la biblioteca estándar: identifica la copia exacta de `std/`.
//
// El binario la lleva empotrada y `pengu doctor` la compara con la del
// proyecto. Así se detecta el caso que producía errores fantasma en el LSP:
// un compilador instalado con una std vieja analizando un proyecto cuya std
// es otra. El algoritmo es estable entre el script de empaquetado y el
// binario: sha256 sobre rutas ordenadas y contenido, separados por NUL.

import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

export function fingerprint_sources(sources: ReadonlyMap<string, string>): string {
  const hash = createHash("sha256");
  for (const path of [...sources.keys()].sort()) {
    hash.update(path);
    hash.update("\0");
    hash.update(sources.get(path) ?? "");
    hash.update("\0");
  }
  return hash.digest("hex").slice(0, 16);
}

export interface StdIdentity {
  readonly fingerprint: string;
  readonly files: number;
}

export function fingerprint_dir(dir: string, root: string): StdIdentity | undefined {
  if (!existsSync(dir)) return undefined;
  const sources = new Map<string, string>();
  const walk = (current: string): void => {
    for (const name of readdirSync(current).sort()) {
      const path = join(current, name);
      if (statSync(path).isDirectory()) walk(path);
      else if (name.endsWith(".pengu")) sources.set(relative(root, path).split("\\").join("/"), readFileSync(path, "utf8"));
    }
  };
  walk(dir);
  return { fingerprint: fingerprint_sources(sources), files: sources.size };
}

// Identidad del `std/` que el proyecto tiene en disco, si tiene uno.
export function project_std(root: string): StdIdentity | undefined {
  return fingerprint_dir(join(root, "std"), root);
}
