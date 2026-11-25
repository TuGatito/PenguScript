// Regresión de F4 (`scratch/plan_lsp_errores.md`): el LSP usa la raíz del
// workspace, no el directorio del archivo abierto, y avisa una sola vez si la
// stdlib del proyecto no es la del compilador.

import { afterAll, describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { start_server, stop_all, wait_for } from "./harness.ts";

afterAll(stop_all);

function project(): { root: string; rootUri: string } {
  const root = mkdtempSync(join(tmpdir(), "pengu_lsp_root_"));
  writeFileSync(join(root, "pengu.toml"), `[package]\nname = "demo"\n`);
  mkdirSync(join(root, "lib"), { recursive: true });
  writeFileSync(join(root, "lib", "util.pengu"), `realm util\n\nsaludo = -> string\n  "hola"\n`);
  return { root, rootUri: pathToFileURL(root).href };
}

describe("raíz del workspace en el LSP", () => {
  test("las importaciones se resuelven contra rootUri, no contra el archivo", async () => {
    const { rootUri } = project();
    const outside = mkdtempSync(join(tmpdir(), "pengu_lsp_outside_"));
    const file = join(outside, "main.pengu");
    const uri = pathToFileURL(file).href;
    const server = start_server();
    server.send({
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: { processId: null, rootUri, capabilities: {} },
    });
    server.send({ jsonrpc: "2.0", method: "initialized", params: {} });
    server.send({
      jsonrpc: "2.0",
      method: "textDocument/didOpen",
      params: {
        textDocument: { uri, languageId: "pengu", version: 1, text: `invoke "lib/util"\n\nmain = -> void\n  util::saludo()\n` },
      },
    });
    const published = await wait_for(
      server.messages,
      (message) => message.method === "textDocument/publishDiagnostics" && (message.params as { uri: string }).uri === uri,
    );
    const diagnostics = (published.params as { diagnostics: readonly { code: string }[] }).diagnostics;
    expect(diagnostics.map((diagnostic) => diagnostic.code)).not.toContain("E0301");
    expect(diagnostics).toHaveLength(0);
  });

  test("avisa una sola vez si la stdlib del proyecto no coincide", async () => {
    const { root, rootUri } = project();
    mkdirSync(join(root, "std"), { recursive: true });
    writeFileSync(join(root, "std", "propia.pengu"), `realm propia\n\nvalor = -> int\n  1\n`);
    const server = start_server();
    server.send({
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: { processId: null, workspaceFolders: [{ uri: rootUri, name: "demo" }], capabilities: {} },
    });
    const warning = await wait_for(server.messages, (message) => message.method === "window/showMessage");
    const params = warning.params as { type: number; message: string };
    expect(params.type).toBe(2);
    expect(params.message).toContain("no coincide con la del compilador");
    expect(params.message).toContain("scripts/install.sh");
  });
});
