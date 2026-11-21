// `pengu clean`: borra los directorios de caché `.pengu-cache` del
// proyecto (o del directorio indicado).

import { existsSync, readdirSync, rmSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import type { ParsedArgs } from "./args.ts";

export interface CommandResult {
  readonly exit_code: number;
  readonly output: string;
}

const CACHE_DIRECTORY = ".pengu-cache";

function collect(root: string, found: string[]): void {
  if (!existsSync(root)) return;
  const entry = join(root, CACHE_DIRECTORY);
  if (existsSync(entry)) found.push(entry);

  for (const name of readdirSync(root)) {
    if (name === CACHE_DIRECTORY || name === "node_modules" || name.startsWith(".")) continue;
    const path = join(root, name);
    if (statSync(path).isDirectory()) collect(path, found);
  }
}

export function run_clean(args: ParsedArgs): CommandResult {
  const root = resolve(args.positionals[0] ?? ".");
  const found: string[] = [];
  collect(root, found);

  for (const directory of found) rmSync(directory, { recursive: true, force: true });

  return {
    exit_code: 0,
    output: found.length === 0
      ? "No hay caché que borrar."
      : `Eliminados ${found.length} directorio(s) de caché.`,
  };
}
