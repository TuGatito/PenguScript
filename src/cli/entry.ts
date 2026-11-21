// Resolución del archivo de entrada de un proyecto PenguScript.
//
// Sin argumentos, un comando busca el `pengu.toml` más cercano y usa su
// `entry`; si no hay proyecto, cae en `main.pengu` como antes.

import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { find_project_root } from "../project/paths.ts";

function project_entry(root: string): string | undefined {
  const manifest = join(root, "pengu.toml");
  if (!existsSync(manifest)) return undefined;
  let text: string;
  try {
    text = readFileSync(manifest, "utf8");
  } catch {
    return undefined;
  }
  for (const line of text.split("\n")) {
    const match = /^\s*entry\s*=\s*"([^"]+)"\s*$/.exec(line);
    if (match !== null) return join(root, match[1] as string);
  }
  return undefined;
}

export function default_entry(positionals: readonly string[]): string {
  const explicit = positionals[0];
  if (explicit !== undefined) return resolve(explicit);
  const root = find_project_root(process.cwd());
  const entry = project_entry(root);
  if (entry !== undefined) return entry;
  return resolve(dirname(join(root, "x")), "main.pengu");
}
