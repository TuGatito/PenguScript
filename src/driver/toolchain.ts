// Detección del compilador de C++ disponible.
//
// PenguScript no empaqueta un compilador: usa el que el usuario ya
// tenga instalado. Preferimos g++ porque el runtime se prueba contra
// él; clang++ sirve igual.

import { spawnSync } from "node:child_process";

const CANDIDATES = ["g++", "clang++", "c++"] as const;

export interface ToolchainInfo {
  readonly compiler: string;
  readonly version: string;
}

export function find_cxx(preferred?: string): string | undefined {
  if (preferred !== undefined) {
    return command_available(preferred) ? preferred : undefined;
  }
  for (const candidate of CANDIDATES) {
    if (command_available(candidate)) return candidate;
  }
  return undefined;
}

export function probe_toolchain(): readonly ToolchainInfo[] {
  const found: ToolchainInfo[] = [];
  for (const candidate of CANDIDATES) {
    const version = command_version(candidate);
    if (version !== undefined) found.push({ compiler: candidate, version });
  }
  return found;
}

function command_available(command: string): boolean {
  return command_version(command) !== undefined;
}

function command_version(command: string): string | undefined {
  const result = spawnSync(command, ["-dumpversion"], { encoding: "utf8" });
  if (result.status !== 0) return undefined;
  const version = (result.stdout ?? "").trim();
  return version.length > 0 ? version : undefined;
}
