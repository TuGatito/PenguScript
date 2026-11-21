// `pengu init`: crea un proyecto mínimo con `pengu.toml` y un
// `main.pengu` que ya se puede ejecutar.

import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import type { ParsedArgs } from "./args.ts";
import { VERSION } from "../version.ts";

export interface CommandResult {
  readonly exit_code: number;
  readonly output: string;
}

const MAIN_TEMPLATE = `-- Punto de entrada del proyecto.
invoke "std/io"

main = ->
  io::println("¡Hola, PenguScript!")
`;

function project_file(name: string): string {
  return `[package]
name = "${name}"
version = "${VERSION}"
entry = "src/main.pengu"
`;
}

export function run_init(args: ParsedArgs): CommandResult {
  const target = resolve(args.positionals[0] ?? ".");
  const name = args.positionals[1] ?? basename(target);

  if (existsSync(join(target, "pengu.toml"))) {
    return { exit_code: 1, output: `error: ya existe «${join(target, "pengu.toml")}»` };
  }

  mkdirSync(join(target, "src"), { recursive: true });
  writeFileSync(join(target, "pengu.toml"), project_file(name), "utf8");
  writeFileSync(join(target, "src", "main.pengu"), MAIN_TEMPLATE, "utf8");

  return {
    exit_code: 0,
    output: `Proyecto «${name}» creado en ${target}\n  pengu.toml\n  src/main.pengu\n\nEjecuta: pengu run ${join(target, "src", "main.pengu")}`,
  };
}
