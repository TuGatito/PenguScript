// P0: `-o` es el alias corto de `--out` que `help` documenta. Sin esto,
// `pengu build main.pengu -o bin` guardaba `true` en `out` y el binario se
// quedaba en la caché sin copiarse (deuda detectada al cablear `--target`).

import { describe, expect, test } from "bun:test";
import { parse_args } from "../../src/cli/args.ts";

describe("alias cortos", () => {
  test("-o <ruta> equivale a --out", () => {
    expect(parse_args(["build", "main.pengu", "-o", "bin"]).flags["out"]).toBe("bin");
  });

  test("-o=ruta y -oruta", () => {
    expect(parse_args(["build", "main.pengu", "-o=bin"]).flags["out"]).toBe("bin");
    expect(parse_args(["build", "main.pengu", "-obin"]).flags["out"]).toBe("bin");
  });

  test("-o sin valor no se come el siguiente flag", () => {
    const args = parse_args(["build", "main.pengu", "-o", "--release"]);
    expect(args.flags["out"]).toBe(true);
    expect(args.flags["release"]).toBe(true);
  });

  test("una bandera corta desconocida sigue siendo booleana", () => {
    expect(parse_args(["build", "main.pengu", "-x"]).flags["x"]).toBe(true);
  });
});

describe("banderas de backend", () => {
  test("--target y --int64 llevan valor", () => {
    const args = parse_args(["build", "main.pengu", "--target", "js", "--int64", "number"]);
    expect(args.flags["target"]).toBe("js");
    expect(args.flags["int64"]).toBe("number");
  });

  test("--out=dir no parte el valor", () => {
    expect(parse_args(["build", "main.pengu", "--out=dist/js"]).flags["out"]).toBe("dist/js");
  });

  test("los argumentos tras -- son del programa", () => {
    const args = parse_args(["run", "main.pengu", "--target", "js", "--", "-o", "x"]);
    expect(args.flags["target"]).toBe("js");
    expect(args.passthrough).toEqual(["-o", "x"]);
  });
});
