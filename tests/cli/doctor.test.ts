// Regresión de F3 (`scratch/plan_lsp_errores.md`): `doctor` dice qué std usa
// el compilador y si el proyecto tiene otra distinta. Es lo que faltaba para
// detectar un binario instalado con una stdlib vieja.

import { describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse_args } from "../../src/cli/args.ts";
import { run_doctor } from "../../src/cli/doctor_command.ts";
import { STD_FILE_COUNT, STD_FINGERPRINT } from "../../src/project/std_bundle.ts";

const ROOT = join(import.meta.dir, "..", "..");

function doctor(argv: readonly string[], cwd: string): { exit_code: number; output: string } {
  return run_doctor(parse_args(["doctor", ...argv]), cwd);
}

describe("pengu doctor", () => {
  test("en el repositorio, la std del proyecto coincide con la del binario", () => {
    const result = doctor([], ROOT);
    expect(result.exit_code).toBe(0);
    expect(result.output).toContain(`std ${STD_FILE_COUNT} archivo(s) · ${STD_FINGERPRINT}`);
    expect(result.output).toContain("coincide con el binario");
  });

  test("un proyecto con su propia std avisa de que no coincide", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu_doctor_"));
    writeFileSync(join(dir, "pengu.toml"), `[package]\nname = "demo"\n`);
    mkdirSync(join(dir, "std"), { recursive: true });
    writeFileSync(join(dir, "std", "propia.pengu"), `realm propia\n\nvalor = -> int\n  1\n`);
    const result = doctor([], dir);
    expect(result.exit_code).toBe(0);
    expect(result.output).toContain("NO coincide con el binario");
    expect(result.output).toContain("bash scripts/install.sh");
  });

  test("--json expone la huella y el estado del proyecto", () => {
    const result = doctor(["--json"], ROOT);
    const payload = JSON.parse(result.output) as {
      pengu: string;
      std: { fingerprint: string; files: number };
      project: { root: string; std: { matches: boolean } | null };
    };
    expect(payload.pengu).toBe("0.1.0");
    expect(payload.std.fingerprint).toBe(STD_FINGERPRINT);
    expect(payload.std.files).toBe(STD_FILE_COUNT);
    expect(payload.project.root).toBe(ROOT);
    expect(payload.project.std?.matches).toBe(true);
  });
});
