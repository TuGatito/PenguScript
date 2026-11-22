// Presupuestos de rendimiento del LSP: el editor no debe esperar a que se
// compile un sondeo C++ para responder, y una ráfaga de teclas no debe
// publicar diagnósticos intermedios.

import { afterAll, describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { build_project } from "../../src/lsp/project.ts";
import { probe_source } from "../../src/driver/layout.ts";
import { start_server, stop_all, wait_for } from "./harness.ts";
import type { RpcMessage } from "./harness.ts";

afterAll(stop_all);

const quiet_options = {
  initializationOptions: { hover: { sizes: false }, inlayHints: { sizes: false }, statusBar: { size: false } },
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function published_for(messages: readonly RpcMessage[], uri: string) {
  return messages.filter((message) => {
    if (message.method !== "textDocument/publishDiagnostics") return false;
    return (message.params as { uri?: string }).uri === uri;
  });
}

function contents_of(message: RpcMessage): readonly { code: string }[] {
  return (message.params as { diagnostics?: readonly { code: string }[] }).diagnostics ?? [];
}

describe("sondeo de tamaños", () => {
  test("editar un cuerpo no cambia el sondeo", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu-probe-"));
    const entry = join(dir, "main.pengu");
    writeFileSync(entry, "rune Punto\n  x: int\n\nmain = ->\n  p:Punto=Punto(1)\n  io::println(\"#{p.x}\")\n");
    const before = build_project(entry);
    const first = probe_source(before.units, before.entry_module);

    writeFileSync(entry, "rune Punto\n  x: int\n\nmain = ->\n  p:Punto=Punto(1)\n  q:Punto=Punto(2)\n  io::println(\"#{p.x + q.x}\")\n");
    const after = build_project(entry);
    expect(probe_source(after.units, after.entry_module)).toBe(first);
  });

  test("añadir un campo sí cambia el sondeo", () => {
    const dir = mkdtempSync(join(tmpdir(), "pengu-probe-"));
    const entry = join(dir, "main.pengu");
    writeFileSync(entry, "rune Punto\n  x: int\n\nmain = ->\n  p:Punto=Punto(1)\n  io::println(\"#{p.x}\")\n");
    const before = build_project(entry);
    writeFileSync(entry, "rune Punto\n  x: int\n  y: int\n\nmain = ->\n  p:Punto=Punto(1, 2)\n  io::println(\"#{p.y}\")\n");
    const after = build_project(entry);
    expect(probe_source(after.units, after.entry_module)).not.toBe(probe_source(before.units, before.entry_module));
  });
});

describe("presupuesto del servidor", () => {
  test("una ráfaga de cambios produce una sola publicación", async () => {
    const uri = "file:///tmp/pengu_perf_burst.pengu";
    const server = start_server();
    server.send({ jsonrpc: "2.0", id: 1, method: "initialize", params: { processId: null, rootUri: null, capabilities: {}, ...quiet_options } });
    server.send({ jsonrpc: "2.0", method: "initialized", params: {} });
    server.send({
      jsonrpc: "2.0",
      method: "textDocument/didOpen",
      params: { textDocument: { uri, languageId: "pengu", version: 1, text: "main = ->\n  x = 1\n" } },
    });
    await wait_for(server.messages, (message) => message.method === "textDocument/publishDiagnostics");
    const before = published_for(server.messages, uri).length;

    for (let version = 2; version <= 8; version += 1) {
      server.send({
        jsonrpc: "2.0",
        method: "textDocument/didChange",
        params: {
          textDocument: { uri, version },
          contentChanges: [{ range: { start: { line: 1, character: 2 }, end: { line: 1, character: 2 } }, text: " " }],
        },
      });
    }
    await sleep(500);
    const after = published_for(server.messages, uri).length;
    expect(after - before).toBeLessThanOrEqual(1);
  });

  test("hover responde sin esperar a la medición", async () => {
    const uri = "file:///tmp/pengu_perf_hover.pengu";
    const server = start_server();
    server.send({ jsonrpc: "2.0", id: 1, method: "initialize", params: { processId: null, rootUri: null, capabilities: {}, ...quiet_options } });
    server.send({ jsonrpc: "2.0", method: "initialized", params: {} });
    server.send({
      jsonrpc: "2.0",
      method: "textDocument/didOpen",
      params: { textDocument: { uri, languageId: "pengu", version: 1, text: "doble = (x: int) -> int\n  x * 2\n\nmain = ->\n  y = doble(3)\n" } },
    });
    await wait_for(server.messages, (message) => message.method === "textDocument/publishDiagnostics");

    const started = performance.now();
    server.send({ jsonrpc: "2.0", id: 9, method: "textDocument/hover", params: { textDocument: { uri }, position: { line: 4, character: 2 } } });
    const hovered = await wait_for(server.messages, (message) => message.id === 9);
    const elapsed = performance.now() - started;
    expect(hovered.result).not.toBeNull();
    expect(elapsed).toBeLessThan(500);
  });

  test("el identificador a medio escribir no se publica hasta el reposo", async () => {
    const uri = "file:///tmp/pengu_perf_typing.pengu";
    const server = start_server();
    server.send({ jsonrpc: "2.0", id: 1, method: "initialize", params: { processId: null, rootUri: null, capabilities: {}, ...quiet_options } });
    server.send({ jsonrpc: "2.0", method: "initialized", params: {} });
    server.send({
      jsonrpc: "2.0",
      method: "textDocument/didOpen",
      params: { textDocument: { uri, languageId: "pengu", version: 1, text: "main = ->\n  x = 1\n" } },
    });
    await wait_for(server.messages, (message) => message.method === "textDocument/publishDiagnostics");

    server.send({
      jsonrpc: "2.0",
      method: "textDocument/didChange",
      params: {
        textDocument: { uri, version: 2 },
        contentChanges: [{ range: { start: { line: 1, character: 7 }, end: { line: 1, character: 7 } }, text: " + zz" }],
      },
    });
    await sleep(400);
    const during = published_for(server.messages, uri).filter((message) => contents_of(message).some((item) => item.code === "E0403"));
    expect(during.length).toBe(0);

    await sleep(900);
    const settled = published_for(server.messages, uri).filter((message) => contents_of(message).some((item) => item.code === "E0403"));
    expect(settled.length).toBeGreaterThan(0);
  });

  test("pengu/perf informa los tiempos del último análisis", async () => {
    const uri = "file:///tmp/pengu_perf_times.pengu";
    const server = start_server();
    server.send({ jsonrpc: "2.0", id: 1, method: "initialize", params: { processId: null, rootUri: null, capabilities: {}, ...quiet_options } });
    server.send({ jsonrpc: "2.0", method: "initialized", params: {} });
    server.send({
      jsonrpc: "2.0",
      method: "textDocument/didOpen",
      params: { textDocument: { uri, languageId: "pengu", version: 1, text: "main = ->\n  io::println(\"hola\")\n" } },
    });
    await wait_for(server.messages, (message) => message.method === "textDocument/publishDiagnostics");
    server.send({ jsonrpc: "2.0", id: 5, method: "pengu/perf", params: {} });
    const perf = await wait_for(server.messages, (message) => message.id === 5);
    const result = perf.result as { analysis_ms: number; sizes_ms: number; stale: boolean };
    expect(result.analysis_ms).toBeGreaterThanOrEqual(0);
    expect(result.analysis_ms).toBeLessThan(2000);
    expect(result.sizes_ms).toBe(0);
    expect(result.stale).toBe(true);
  });
});
