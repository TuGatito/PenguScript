// P0: selección de backend (`--target`). El backend por defecto sigue siendo
// C++20; un valor desconocido nunca debe degradar a "cpp" en silencio.

import { describe, expect, test } from "bun:test";
import {
  DEFAULT_TARGET,
  TARGETS,
  is_target,
  parse_target,
  target_is_native,
  target_label,
} from "../../src/driver/target.ts";

describe("parse_target", () => {
  test("sin --target se usa cpp", () => {
    expect(DEFAULT_TARGET).toBe("cpp");
    expect(parse_target(undefined)).toEqual({ ok: true, target: "cpp" });
  });

  test("acepta los backends conocidos", () => {
    expect(TARGETS).toEqual(["cpp", "js"]);
    expect(parse_target("cpp")).toEqual({ ok: true, target: "cpp" });
    expect(parse_target("js")).toEqual({ ok: true, target: "js" });
    expect(parse_target("JS")).toEqual({ ok: true, target: "js" });
  });

  test("rechaza un backend desconocido con un mensaje útil", () => {
    const result = parse_target("python");
    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.message).toContain("python");
    expect(result.message).toContain("cpp");
    expect(result.message).toContain("js");
  });

  test("is_target", () => {
    expect(is_target("js")).toBe(true);
    expect(is_target("wasm")).toBe(false);
  });

  test("etiquetas para el usuario", () => {
    expect(target_label("js")).toBe("JavaScript (ESM)");
    expect(target_label("cpp")).toBe("C++20");
    expect(target_is_native("cpp")).toBe(true);
    expect(target_is_native("js")).toBe(false);
  });
});
