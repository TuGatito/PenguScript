// Ciclo de vida del cliente LSP: arranque, reinicio y parada.

const { workspace, window, Trace } = require("vscode");
const { inlay_sizes, inlay_types, completion_docs, status_size } = require("./settings");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

function trace_setting() {
  const value = workspace.getConfiguration("pengu").get("lsp.trace.server", "off");
  if (value === "verbose") return Trace.Verbose;
  if (value === "messages") return Trace.Messages;
  return Trace.Off;
}

function server_options(executable, cwd) {
  const options = cwd === undefined ? {} : { cwd };
  return { command: executable, args: ["lsp"], transport: TransportKind.stdio, options };
}

function client_options(output) {
  return {
    documentSelector: [{ scheme: "file", language: "pengu" }],
    outputChannel: output,
    synchronize: { fileEvents: workspace.createFileSystemWatcher("**/*.pengu") },
    // El servidor decide con esto si añade tamaños a los hints.
    initializationOptions: {
      inlayHints: { types: inlay_types(), sizes: inlay_sizes() },
      completion: { docs: completion_docs() },
      statusBar: { size: status_size() },
    },
  };
}

async function start_client(state, executable, cwd, on_missing) {
  const client = new LanguageClient(
    "pengu",
    "PenguScript",
    server_options(executable, cwd),
    client_options(state.output),
  );
  state.client = client;
  try {
    await client.start();
    await client.setTrace(trace_setting());
  } catch (_error) {
    state.client = undefined;
    on_missing();
  }
}

async function stop_client(state) {
  const client = state.client;
  state.client = undefined;
  if (client !== undefined) await client.stop();
}

// Se llama al cambiar `pengu.executable` o `pengu.lsp.trace.server`.
async function restart_client(state, executable, cwd, on_missing) {
  await stop_client(state);
  await start_client(state, executable, cwd, on_missing);
}

module.exports = { start_client, stop_client, restart_client, client_options, server_options };
