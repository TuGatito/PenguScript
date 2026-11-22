import { afterAll, describe, expect, test } from "bun:test";
import { start_server, stop_all, wait_for } from "./harness.ts";

afterAll(stop_all);

const uri = "file:///tmp/pengu_lsp_test.pengu";
const good_text = "sumar = (a: int, b: int) -> int\n  a + b\n\nmain = ->\n  x:int=sumar(1,2)\n  io::println(\"#{x}\")\n";
const bad_text = "main = ->\n  x = 1 + \"dos\"\n";

describe("servidor LSP", () => {
  test("responde initialize y publica diagnósticos", async () => {
    const server = start_server();
    server.send({ jsonrpc: "2.0", id: 1, method: "initialize", params: { processId: null, rootUri: null, capabilities: {} } });
    server.send({ jsonrpc: "2.0", method: "initialized", params: {} });
    server.send({ jsonrpc: "2.0", method: "textDocument/didOpen", params: { textDocument: { uri, languageId: "pengu", version: 1, text: bad_text } } });

    const init = await wait_for(server.messages, (message) => message.id === 1);
    expect((init.result as { capabilities: { hoverProvider: boolean } }).capabilities.hoverProvider).toBe(true);

    const published = await wait_for(
      server.messages,
      (message) => message.method === "textDocument/publishDiagnostics",
    );
    const diagnostics = (published.params as { diagnostics: readonly { code: string }[] }).diagnostics;
    expect(diagnostics.some((diagnostic) => diagnostic.code === "E0501")).toBe(true);

    server.send({ jsonrpc: "2.0", id: 2, method: "shutdown", params: {} });
    await wait_for(server.messages, (message) => message.id === 2);
    server.send({ jsonrpc: "2.0", method: "exit", params: {} });
  });

  test("hover y finalización de métodos enhechizados", async () => {
    const enchanted_text = `enchanting string
  compare = (otro: string) -> int
    if @ < otro then -1 else if @ > otro then 1 else 0

main = ->
  a = "manzana"
  x = a.compare("banana")
`;
    const server = start_server();
    server.send({ jsonrpc: "2.0", id: 1, method: "initialize", params: { processId: null, rootUri: null, capabilities: {} } });
    server.send({
      jsonrpc: "2.0",
      method: "textDocument/didOpen",
      params: { textDocument: { uri, languageId: "pengu", version: 1, text: enchanted_text } },
    });

    server.send({
      jsonrpc: "2.0",
      id: 3,
      method: "textDocument/hover",
      params: { textDocument: { uri }, position: { line: 6, character: 10 } },
    });
    const hover = await wait_for(server.messages, (message) => message.id === 3);
    expect(JSON.stringify(hover.result)).toContain("compare");
    expect(JSON.stringify(hover.result)).toContain("string");

    server.send({
      jsonrpc: "2.0",
      id: 4,
      method: "textDocument/completion",
      params: { textDocument: { uri }, position: { line: 6, character: 8 } },
    });
    const completion = await wait_for(server.messages, (message) => message.id === 4);
    const labels = (completion.result as readonly { label: string }[]).map((item) => item.label);
    expect(labels).toContain("compare");
    expect(labels[0]).toBe("compare");

    server.send({
      jsonrpc: "2.0",
      id: 5,
      method: "textDocument/documentSymbol",
      params: { textDocument: { uri } },
    });
    const symbols = await wait_for(server.messages, (message) => message.id === 5);
    const names = (symbols.result as readonly { name: string }[]).map((symbol) => symbol.name);
    expect(names).toContain("enchanting string");

    server.send({ jsonrpc: "2.0", id: 2, method: "shutdown", params: {} });
    await wait_for(server.messages, (message) => message.id === 2);
    server.send({ jsonrpc: "2.0", method: "exit", params: {} });
  });

  test("hover, finalización y formato", async () => {
    const server = start_server();
    server.send({ jsonrpc: "2.0", id: 1, method: "initialize", params: { processId: null, rootUri: null, capabilities: {} } });
    server.send({ jsonrpc: "2.0", method: "textDocument/didOpen", params: { textDocument: { uri, languageId: "pengu", version: 1, text: good_text } } });

    server.send({
      jsonrpc: "2.0",
      id: 3,
      method: "textDocument/hover",
      params: { textDocument: { uri }, position: { line: 4, character: 2 } },
    });
    const hover = await wait_for(server.messages, (message) => message.id === 3);
    expect(JSON.stringify(hover.result)).toContain("int");

    server.send({
      jsonrpc: "2.0",
      id: 4,
      method: "textDocument/completion",
      params: { textDocument: { uri }, position: { line: 4, character: 7 } },
    });
    const completion = await wait_for(server.messages, (message) => message.id === 4);
    const labels = (completion.result as readonly { label: string }[]).map((item) => item.label);
    expect(labels).toContain("sumar");
    expect(labels).toContain("main");

    server.send({
      jsonrpc: "2.0",
      id: 5,
      method: "textDocument/formatting",
      params: { textDocument: { uri }, options: { tabSize: 2, insertSpaces: true } },
    });
    const formatting = await wait_for(server.messages, (message) => message.id === 5);
    const edits = formatting.result as readonly { newText: string }[];
    expect(edits.length).toBe(1);
    expect(edits[0]!.newText).toContain("x: int = sumar(1, 2)");

    server.send({
      jsonrpc: "2.0",
      id: 6,
      method: "textDocument/definition",
      params: { textDocument: { uri }, position: { line: 4, character: 12 } },
    });
    const definition = await wait_for(server.messages, (message) => message.id === 6);
    expect((definition.result as { uri: string }).uri).toBe(uri);

    server.send({
      jsonrpc: "2.0",
      id: 7,
      method: "textDocument/documentSymbol",
      params: { textDocument: { uri } },
    });
    const symbols = await wait_for(server.messages, (message) => message.id === 7);
    const names = (symbols.result as readonly { name: string }[]).map((symbol) => symbol.name);
    expect(names).toContain("sumar");
    expect(names).toContain("main");

    server.send({ jsonrpc: "2.0", id: 2, method: "shutdown", params: {} });
    await wait_for(server.messages, (message) => message.id === 2);
    server.send({ jsonrpc: "2.0", method: "exit", params: {} });
  });
});
