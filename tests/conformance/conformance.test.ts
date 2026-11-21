// Banco de conformidad: cada carpeta declara su expectativa en
// `esperado.json` y se ejecuta contra el compilador real.

import { describe, expect, test } from "bun:test";
import { conformance_root, find_cases, run_case } from "./run.ts";

const cases = find_cases(conformance_root());

describe("conformidad", () => {
  test("hay casos declarados", () => {
    expect(cases.length).toBeGreaterThan(0);
  });

  for (const item of cases) {
    test(item.name, () => {
      run_case(item);
    }, 30000);
  }
});
