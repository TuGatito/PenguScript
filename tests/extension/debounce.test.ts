// El debounce de la barra de estado: mover el cursor no debe lanzar una
// petición por cada paso, solo una cuando el cursor se detiene.

import { describe, expect, test } from "bun:test";

const { make_debounced } = require("../../editors/vscode/src/debounce");

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

describe("debounce de la extensión", () => {
  test("varias peticiones seguidas se convierten en una", async () => {
    let calls = 0;
    const debounced = make_debounced(20, () => {
      calls += 1;
    });
    debounced.schedule();
    debounced.schedule();
    debounced.schedule();
    expect(calls).toBe(0);
    await sleep(60);
    expect(calls).toBe(1);
  });

  test("cancelar impide la ejecución pendiente", async () => {
    let calls = 0;
    const debounced = make_debounced(20, () => {
      calls += 1;
    });
    debounced.schedule();
    debounced.cancel();
    await sleep(60);
    expect(calls).toBe(0);
  });
});
