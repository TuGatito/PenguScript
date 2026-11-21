// `pengu fmt`: formatea archivos PenguScript en su lugar.
//
// Con `--check` no escribe nada: devuelve 1 si algún archivo quedaría
// distinto y lista los archivos afectados.

import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import type { ParsedArgs } from "./args.ts";
import { flag_bool } from "./args.ts";
import { format_text } from "../formatter/format_tokens.ts";

export interface CommandResult {
  readonly exit_code: number;
  readonly output: string;
}

const SOURCE_EXTENSION = ".pengu";
const SKIPPED = new Set([".pengu-cache", "node_modules", ".git", "dist", "build"]);

function is_pengu_file(path: string): boolean {
  return path.endsWith(SOURCE_EXTENSION);
}

function collect(path: string, found: string[]): void {
  if (!existsSync(path)) return;
  if (statSync(path).isFile()) {
    if (is_pengu_file(path)) found.push(path);
    return;
  }
  for (const name of readdirSync(path)) {
    if (SKIPPED.has(name) || name.startsWith(".")) continue;
    collect(join(path, name), found);
  }
}

export function run_fmt(args: ParsedArgs): CommandResult {
  const check_only = flag_bool(args, "check");
  const targets = args.positionals.length > 0 ? args.positionals.map((value) => resolve(value)) : [resolve(".")];

  const files: string[] = [];
  for (const target of targets) collect(target, files);

  if (files.length === 0) {
    return { exit_code: 1, output: "no se encontraron archivos .pengu" };
  }

  const changed: string[] = [];
  for (const file of files) {
    const source = readFileSync(file, "utf8");
    const formatted = format_text(file, source);
    if (formatted === source) continue;
    changed.push(file);
    if (!check_only) writeFileSync(file, formatted, "utf8");
  }

  if (check_only) {
    if (changed.length === 0) return { exit_code: 0, output: `${files.length} archivo(s) ya formateados.` };
    return {
      exit_code: 1,
      output: `estos archivos necesitan formato:\n${changed.map((file) => `  ${file}`).join("\n")}`,
    };
  }

  return {
    exit_code: 0,
    output: changed.length === 0
      ? `${files.length} archivo(s) ya formateados.`
      : `Formateados ${changed.length} de ${files.length} archivo(s).`,
  };
}
