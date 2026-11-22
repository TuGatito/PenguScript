// Rutas de proyecto y resolución de módulos.

import { existsSync, statSync } from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { STD_SOURCES } from "./std_bundle.ts";

const MANIFEST = "pengu.toml";

// Biblioteca estándar que acompaña al compilador (`std/` del repositorio).
const BUNDLED_STD = fileURLToPath(new URL("../../std", import.meta.url));

// Los módulos de `std/` viajan dentro del binario compilado: cuando el
// archivo no está en disco se usa esta ruta virtual.
const STD_PREFIX = "std:";

// `std/` es de solo lectura: el proyecto no debe renombrarlo ni editarlo.
export function is_bundled(path: string): boolean {
  return path.startsWith(STD_PREFIX) || path === BUNDLED_STD || path.startsWith(`${BUNDLED_STD}/`);
}

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

// Texto del módulo cuando vive dentro del binario (`std:`); `undefined` si es
// un archivo normal, que se lee de disco.
export function read_source(path: string): string | undefined {
  return path.startsWith(STD_PREFIX) ? STD_SOURCES[path.slice(STD_PREFIX.length)] : undefined;
}

function bundled_candidates(spec: string): string[] {
  return [`${spec}.pengu`, `${spec}.d.pengu`, `${spec}/index.pengu`];
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
  // Sin `std/` en disco (binario instalado fuera del repositorio): se resuelve
  // contra la copia empotrada.
  if (relative !== undefined || !spec.startsWith("std/")) return undefined;
  for (const candidate of bundled_candidates(spec)) {
    if (STD_SOURCES[candidate] !== undefined) return `${STD_PREFIX}${candidate}`;
  }
  return undefined;
}
