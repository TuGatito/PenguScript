// Comando `pengu run`: compila y ejecuta el programa.
//
// Los argumentos posteriores a `--` se pasan al ejecutable generado (o al
// runtime de JavaScript cuando `--target js`).

import { spawnSync } from "node:child_process";
import { compile_file } from "../driver/compile.ts";
import { explain_failure } from "./build_command.ts";
import { flag_bool, flag_string, type ParsedArgs } from "./args.ts";
import { default_entry } from "./entry.ts";
import { parse_target } from "../driver/target.ts";
import { parse_int64_mode } from "../codegen/js_types.ts";
import { run_js_entry } from "../driver/js_runner.ts";

export interface RunResult {
  readonly exit_code: number;
  readonly output: string;
}

export function run_run(args: ParsedArgs): RunResult {
  const file = default_entry(args.positionals);
  const link = flag_string(args, "link");
  const choice = parse_target(flag_string(args, "target"));
  if (!choice.ok) return { exit_code: 1, output: `error: ${choice.message}` };
  const int64 = parse_int64_mode(flag_string(args, "int64"));
  if (!int64.ok) return { exit_code: 1, output: `error: ${int64.message}` };

  const result = compile_file(file, {
    compiler: flag_string(args, "compiler"),
    link: link === undefined ? [] : link.split(",").map((item) => item.trim()).filter((item) => item.length > 0),
    target: choice.target,
    release: flag_bool(args, "release"),
    int64: int64.mode,
  });
  if (!result.ok) {
    return { exit_code: 1, output: explain_failure(result, file) };
  }

  if (choice.target === "js") {
    if (result.js_entry_path === undefined) {
      return { exit_code: 1, output: "no se generó el punto de entrada de JavaScript" };
    }
    return run_js_entry(result.js_entry_path, args.passthrough);
  }

  if (result.binary_path === undefined) {
    return { exit_code: 1, output: explain_failure(result, file) };
  }
  const execution = spawnSync(result.binary_path, args.passthrough, { stdio: "inherit" });
  return { exit_code: execution.status ?? 1, output: "" };
}
