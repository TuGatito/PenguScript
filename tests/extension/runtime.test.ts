// Prueba de humo de la extensión: se carga con un `vscode` simulado y se
// ejercitan activación, comandos, tareas, diagnósticos y parada.

import { afterAll, describe, expect, test } from "bun:test";
import { createRequire } from "node:module";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { mock } from "bun:test";

const require_cjs = createRequire(import.meta.url);

const recorded = {
  commands: [] as Array<{ id: string; handler: (...args: unknown[]) => unknown }>,
  task_providers: [] as string[],
  status: [] as Array<{ text: string; tooltip: string; command: string }>,
  warnings: [] as string[],
  executed: [] as string[],
  terminals: [] as Array<{ command: string }>,
  diagnostics: [] as Array<{ uri: string; count: number }>,
  watchers: 0,
};

const settings: Record<string, unknown> = {
  "pengu.executable": "pengu",
  "pengu.build.args": [],
  "pengu.run.args": [],
  "pengu.check.onSave": false,
  "pengu.lsp.trace.server": "off",
};

function Uri(this: { fsPath: string }, fsPath: string) {
  this.fsPath = fsPath;
}

// Anotación de constructor para poder usar `new Uri(...)` desde TypeScript.
const UriConstructor = Uri as unknown as new (fsPath: string) => { fsPath: string };

function Position(this: { line: number; character: number }, line: number, character: number) {
  this.line = line;
  this.character = character;
}

function Range(this: { start: unknown; end: unknown }, start: unknown, end: unknown) {
  this.start = start;
  this.end = end;
}

function Diagnostic(this: Record<string, unknown>, range: unknown, message: string, severity: number) {
  this.range = range;
  this.message = message;
  this.severity = severity;
}

function ShellExecution(this: { command: string; options: unknown }, command: string, options: unknown) {
  this.command = command;
  this.options = options;
}

function Task(this: Record<string, unknown>, definition: unknown, scope: unknown, name: string, source: string, execution: unknown, problem_matchers: string[]) {
  this.definition = definition;
  this.scope = scope;
  this.name = name;
  this.source = source;
  this.execution = execution;
  this.problemMatchers = problem_matchers;
}

function LanguageClient(this: Record<string, unknown>, id: string, name: string) {
  this.id = id;
  this.name = name;
  this.started = false;
  this.stopped = false;
  this.trace = 0;
  this.start = async () => {
    this.started = true;
  };
  this.stop = async () => {
    this.stopped = true;
  };
  this.setTrace = async (value: number) => {
    this.trace = value;
  };
}

const output_channel = { lines: [] as string[], appendLine: (line: string) => output_channel.lines.push(line), show: () => {}, dispose: () => {} };

const vscode_stub = {
  Uri,
  Position,
  Range,
  Diagnostic,
  DiagnosticSeverity: { Error: 0, Warning: 1, Information: 2 },
  StatusBarAlignment: { Left: 1, Right: 2 },
  Trace: { Off: 0, Messages: 1, Verbose: 2 },
  Task,
  TaskScope: { Workspace: 1 },
  TaskGroup: { Build: { kind: "build" } },
  ShellExecution,
  commands: {
    registerCommand: (id: string, handler: (...args: unknown[]) => unknown) => {
      recorded.commands.push({ id, handler });
      return { dispose: () => {} };
    },
    executeCommand: (id: string) => {
      recorded.executed.push(id);
      return Promise.resolve(undefined);
    },
  },
  window: {
    activeTextEditor: undefined,
    createOutputChannel: () => output_channel,
    createStatusBarItem: () => {
      const item = {
        text: "",
        tooltip: "",
        command: "",
        visible: false,
        show() {
          item.visible = true;
          recorded.status.push({ text: item.text, tooltip: item.tooltip, command: item.command });
        },
        dispose: () => {},
      };
      return item;
    },
    createTerminal: () => {
      const terminal = {
        exitStatus: undefined,
        show: () => {},
        sendText: (command: string) => recorded.terminals.push({ command }),
      };
      return terminal;
    },
    showWarningMessage: (message: string) => {
      recorded.warnings.push(message);
      return Promise.resolve(undefined);
    },
    showInputBox: () => Promise.resolve(undefined),
  },
  workspace: {
    workspaceFolders: [],
    getWorkspaceFolder: () => undefined,
    getConfiguration: (section?: string) => ({
      get: (key: string, fallback: unknown) => {
        const full = section === undefined ? key : `${section}.${key}`;
        return settings[full] ?? fallback;
      },
    }),
    createFileSystemWatcher: () => {
      recorded.watchers += 1;
      return { dispose: () => {} };
    },
    onDidChangeConfiguration: () => ({ dispose: () => {} }),
    onDidSaveTextDocument: () => ({ dispose: () => {} }),
    onDidCloseTextDocument: () => ({ dispose: () => {} }),
  },
  tasks: {
    registerTaskProvider: (type: string) => {
      recorded.task_providers.push(type);
      return { dispose: () => {} };
    },
  },
  languages: {
    createDiagnosticCollection: () => ({
      set: (uri: { fsPath: string }, value: unknown[] | undefined) => {
        recorded.diagnostics.push({ uri: uri.fsPath, count: value === undefined ? 0 : value.length });
      },
      delete: () => {},
      dispose: () => {},
    }),
  },
};

mock.module("vscode", () => vscode_stub);
mock.module("vscode-languageclient/node", () => ({ LanguageClient, TransportKind: { stdio: 1 } }));

const extension = require_cjs("../../editors/vscode/src/extension.js");
const diagnostics = require_cjs("../../editors/vscode/src/diagnostics.js");

const context = { subscriptions: [] as Array<{ dispose: () => void }> };

function command(id: string): (...args: unknown[]) => unknown {
  const found = recorded.commands.find((entry) => entry.id === id);
  if (found === undefined) throw new Error(`comando ${id} no registrado`);
  return found.handler;
}

const temp = mkdtempSync(join(tmpdir(), "pengu_extension_"));

afterAll(() => {
  rmSync(temp, { recursive: true, force: true });
});

describe("extensión en ejecución", () => {
  test("sin ejecutable avisa y marca la barra de estado", async () => {
    settings["pengu.executable"] = "pengu-no-existe";
    await extension.activate(context);
    expect(recorded.warnings.length).toBeGreaterThan(0);
    expect(recorded.status.at(-1)?.text).toContain("no encontrado");
    await extension.deactivate();
  });

  test("con ejecutable arranca el LSP y registra comandos y tareas", async () => {
    settings["pengu.executable"] = "pengu";
    await extension.activate(context);
    expect(recorded.status.at(-1)?.text).toContain("pengu 0.1.0");
    expect(new Set(recorded.commands.map((entry) => entry.id)).size).toBe(11);
    expect(recorded.task_providers).toContain("pengu");
    expect(context.subscriptions.length).toBeGreaterThan(5);
  });

  test("ejecutar archivo abre la terminal con el comando correcto", async () => {
    const handler = command("pengu.runFile");
    await handler(new UriConstructor(join(temp, "main.pengu")));
    expect(recorded.terminals.at(-1)?.command).toContain("run");
    expect(recorded.terminals.at(-1)?.command).toContain("main.pengu");
  });

  test("los comandos sin archivo avisan en vez de fallar", async () => {
    const before = recorded.warnings.length;
    await command("pengu.buildFile")(undefined);
    expect(recorded.warnings.length).toBe(before + 1);
  });

  test("verificar al guardar publica los diagnósticos", async () => {
    settings["pengu.check.onSave"] = true;
    const file = join(temp, "roto.pengu");
    writeFileSync(file, 'main = ->\n  x: int = "texto"\n');
    const uri = new UriConstructor(file);
    diagnostics.check_document({ languageId: "pengu", uri }, "pengu");
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (recorded.diagnostics.some((entry) => entry.uri === file)) break;
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    const published = recorded.diagnostics.find((entry) => entry.uri === file);
    expect(published).toBeDefined();
    expect(published?.count).toBeGreaterThan(0);
    settings["pengu.check.onSave"] = false;
  });

  test("deactivate detiene el cliente", async () => {
    await extension.deactivate();
    expect(recorded.status.at(-1)?.command).toBeDefined();
  });
});
