// `pengu lsp`: inicia el servidor de lenguaje sobre stdio.

import type { ParsedArgs } from "./args.ts";
import { start_lsp_server } from "../lsp/server.ts";

export interface CommandResult {
  readonly exit_code: number;
  readonly output: string;
}

export function run_lsp(_args: ParsedArgs): CommandResult {
  start_lsp_server();
  return { exit_code: 0, output: "" };
}
