#!/usr/bin/env bun
import { parse_args } from "./cli/args.ts";
import { command_help, is_command, main_help } from "./cli/help.ts";
import { run_check } from "./cli/check_command.ts";
import { run_build } from "./cli/build_command.ts";
import { run_run } from "./cli/run_command.ts";
import { run_init } from "./cli/init_command.ts";
import { run_clean } from "./cli/clean_command.ts";
import { run_fmt } from "./cli/fmt_command.ts";
import { run_lsp } from "./cli/lsp_command.ts";
import { run_bindgen } from "./cli/bindgen_command.ts";
import { probe_toolchain } from "./driver/toolchain.ts";
import { LANGUAGE_NAME, LANGUAGE_VERSION } from "./version.ts";
import { TOOL_NAME, VERSION } from "./version.ts";

// Si el consumidor cierra la tubería antes de tiempo (`pengu doctor | head`),
// salir en silencio en vez de volcar un EPIPE.
function ignore_broken_pipe(stream: NodeJS.WriteStream): void {
  stream.on("error", (error: NodeJS.ErrnoException) => {
    if (error.code === "EPIPE") process.exit(0);
    throw error;
  });
}

ignore_broken_pipe(process.stdout);
ignore_broken_pipe(process.stderr);

function print(text: string): void {
  process.stdout.write(`${text}\n`);
}

function print_error(text: string): void {
  process.stderr.write(`${text}\n`);
}

function main(argv: readonly string[]): number {
  const args = parse_args(argv);

  if (args.flags.version === true || args.command === "--version" || args.command === "version") {
    print(`${TOOL_NAME} ${VERSION}`);
    return 0;
  }
  if (args.flags.help === true || args.command === "help") {
    print(args.positionals[0] && is_command(args.positionals[0])
      ? command_help(args.positionals[0])
      : main_help());
    return 0;
  }
  if (args.command === "" || args.command === "--help") {
    print(main_help());
    return 0;
  }
  if (!is_command(args.command)) {
    print_error(`error: comando desconocido '${args.command}'`);
    print_error(`pista: ejecuta '${TOOL_NAME} --help' para ver los comandos disponibles`);
    return 2;
  }

  switch (args.command) {
    case "check": {
      const result = run_check(args.positionals, args.flags);
      // `--json` siempre va a stdout: es la salida para máquinas.
      if (result.exit_code === 0 || args.flags.json === true) print(result.output);
      else print_error(result.output);
      return result.exit_code;
    }
    case "build": {
      const result = run_build(args);
      if (result.exit_code === 0) print(result.output);
      else print_error(result.output);
      return result.exit_code;
    }
    case "run": {
      const result = run_run(args);
      if (result.output.length > 0) print_error(result.output);
      return result.exit_code;
    }
    case "fmt": {
      const result = run_fmt(args);
      if (result.exit_code === 0) print(result.output);
      else print_error(result.output);
      return result.exit_code;
    }
    case "lsp": {
      return run_lsp(args).exit_code;
    }
    case "bindgen": {
      const result = run_bindgen(args);
      if (result.exit_code === 0) print(result.output);
      else print_error(result.output);
      return result.exit_code;
    }
    case "init": {
      const result = run_init(args);
      if (result.exit_code === 0) print(result.output);
      else print_error(result.output);
      return result.exit_code;
    }
    case "clean": {
      const result = run_clean(args);
      if (result.exit_code === 0) print(result.output);
      else print_error(result.output);
      return result.exit_code;
    }
    case "doctor": {
      const toolchains = probe_toolchain();
      print(`${TOOL_NAME} ${VERSION} (${LANGUAGE_NAME} ${LANGUAGE_VERSION})`);
      print(`bun ${process.versions.bun ?? "desconocido"}`);
      if (toolchains.length === 0) {
        print("sin compilador de C++20 (instala g++ o clang++)");
        return 1;
      }
      for (const info of toolchains) print(`${info.compiler} ${info.version}`);
      return 0;
    }
    case "fmt":
    case "lsp":
    case "bindgen":
    case "init":
    case "clean":
      print_error(`error: el comando '${args.command}' todavía no está implementado (fase P0)`);
      return 3;
  }
}

process.exitCode = main(process.argv.slice(2));
