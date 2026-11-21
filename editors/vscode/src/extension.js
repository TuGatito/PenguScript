// Extensión de VS Code: arranca `pengu lsp` y conecta el cliente LSP.

const path = require("node:path");
const { workspace } = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function activate(context) {
  const configured = workspace.getConfiguration("pengu").get("executable", "pengu");
  const serverOptions = {
    command: configured,
    args: ["lsp"],
    transport: TransportKind.stdio,
  };

  const clientOptions = {
    documentSelector: [{ scheme: "file", language: "pengu" }],
    synchronize: {
      fileEvents: workspace.createFileSystemWatcher("**/*.pengu"),
    },
  };

  client = new LanguageClient("pengu", "PenguScript", serverOptions, clientOptions);
  context.subscriptions.push(client.start());
}

function deactivate() {
  return client === undefined ? undefined : client.stop();
}

module.exports = { activate, deactivate };
