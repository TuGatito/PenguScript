// `pengu doctor`: qué compilador y qué biblioteca estándar se están usando.
//
// Nació de los errores fantasma del LSP: el binario instalado y el proyecto
// podían tener dos `std/` distintas sin que nada lo dijera. La huella de la
// std empotrada (generada por `scripts/embed_std.ts`) se compara con la del
// proyecto para poder avisar antes de perder tiempo depurando diagnósticos
// que no existen.

import { join } from "node:path";
import { flag_bool, type ParsedArgs } from "./args.ts";
import { probe_toolchain } from "../driver/toolchain.ts";
import { find_project_root } from "../project/paths.ts";
import { project_std } from "../project/std_fingerprint.ts";
import type { StdIdentity } from "../project/std_fingerprint.ts";
import { STD_FILE_COUNT, STD_FINGERPRINT } from "../project/std_bundle.ts";
import { LANGUAGE_NAME, LANGUAGE_VERSION, TOOL_NAME, VERSION } from "../version.ts";

export interface DoctorResult {
  readonly exit_code: number;
  readonly output: string;
}

export interface ProjectStd extends StdIdentity {
  readonly matches: boolean;
}

function project_std_identity(root: string): ProjectStd | undefined {
  const identity = project_std(root);
  return identity === undefined ? undefined : { ...identity, matches: identity.fingerprint === STD_FINGERPRINT };
}

export function run_doctor(args: ParsedArgs, cwd: string): DoctorResult {
  const json = flag_bool(args, "json");
  const root = find_project_root(cwd);
  const std = project_std_identity(root);
  const toolchains = probe_toolchain();

  if (json) {
    const payload = {
      pengu: VERSION,
      language: LANGUAGE_VERSION,
      bun: process.versions.bun ?? null,
      compilers: toolchains.map((info) => ({ name: info.compiler, version: info.version })),
      std: { fingerprint: STD_FINGERPRINT, files: STD_FILE_COUNT },
      project: {
        root,
        std: std === undefined ? null : { fingerprint: std.fingerprint, files: std.files, matches: std.matches },
      },
    };
    return { exit_code: toolchains.length === 0 ? 1 : 0, output: JSON.stringify(payload, null, 2) };
  }

  const lines = [
    `${TOOL_NAME} ${VERSION} (${LANGUAGE_NAME} ${LANGUAGE_VERSION})`,
    `bun ${process.versions.bun ?? "desconocido"}`,
  ];
  if (toolchains.length === 0) lines.push("sin compilador de C++20 (instala g++ o clang++)");
  for (const info of toolchains) lines.push(`${info.compiler} ${info.version}`);
  lines.push(`std ${STD_FILE_COUNT} archivo(s) · ${STD_FINGERPRINT}`);
  lines.push(`proyecto ${root}`);
  if (std === undefined) {
    lines.push("  sin std/ propio: se usa la std empotrada en el binario");
  } else if (std.matches) {
    lines.push(`  std/ del proyecto ${std.files} archivo(s) · ${std.fingerprint} (coincide con el binario)`);
  } else {
    lines.push(`  std/ del proyecto ${std.files} archivo(s) · ${std.fingerprint} (NO coincide con el binario)`);
    lines.push("  aviso: instala el compilador (`bash scripts/install.sh`) para que CLI y LSP usen la misma stdlib");
  }
  return { exit_code: toolchains.length === 0 ? 1 : 0, output: lines.join("\n") };
}
