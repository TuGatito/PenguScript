// Comando `pengu run`: compila y ejecuta el programa.
//
// Los argumentos posteriores a `--` se pasan al ejecutable generado.

import { spawnSync } from "node:child_process";
import { compile_file } from "../driver/compile.ts";
import { explain_failure } from "./build_command.ts";
import { flag_string, type ParsedArgs } from "./args.ts";
import { default_entry } from "./entry.ts";

export interface RunResult {
  readonly exit_code: number;
  readonly output: string;
}

export function run_run(args: ParsedArgs): RunResult {
  const file = default_entry(args.positionals);
  const link = flag_string(args, "link");
  const result = compile_file(file, {
    compiler: flag_string(args, "compiler"),
    link: link === undefined ? [] : link.split(",").map((item) => item.trim()).filter((item) => item.length > 0),
  });
  if (!result.ok || result.binary_path === undefined) {
    return { exit_code: 1, output: explain_failure(result, file) };
  }

  const execution = spawnSync(result.binary_path, args.passthrough, { stdio: "inherit" });
  return { exit_code: execution.status ?? 1, output: "" };
}
