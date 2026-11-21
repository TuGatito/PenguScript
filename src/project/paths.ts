// Rutas de proyecto y resolución de módulos.

import { existsSync, statSync } from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const MANIFEST = "pengu.toml";

// Biblioteca estándar que acompaña al compilador (`std/` del repositorio).
const BUNDLED_STD = fileURLToPath(new URL("../../std", import.meta.url));

// Directorio del proyecto: el ancestro más cercano con `pengu.toml`.
export function find_project_root(start: string): string {
  let current = resolve(start);
  while (true) {
    if (existsSync(join(current, MANIFEST))) return current;
    const parent = dirname(current);
    if (parent === current) return resolve(start);
    current = parent;
  }
}

function is_file(path: string): boolean {
  return existsSync(path) && statSync(path).isFile();
}

// Convierte una ruta de `invoke` en un archivo `.pengu`.
export function resolve_module_file(from_file: string, spec: string, root: string): string | undefined {
  const relative = spec.startsWith(".") ? resolve(dirname(from_file), spec) : isAbsolute(spec) ? spec : undefined;
  const bases = relative !== undefined ? [relative] : [
    join(root, spec),
    ...(spec.startsWith("std/") ? [join(BUNDLED_STD, spec.slice("std/".length))] : []),
  ];
  for (const base of bases) {
    for (const candidate of [`${base}.pengu`, `${base}.d.pengu`, join(base, "index.pengu")]) {
      if (is_file(candidate)) return candidate;
    }
  }
  return undefined;
}
