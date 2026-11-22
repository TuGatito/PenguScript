// Verificación al guardar usando `pengu check --json` (independiente del LSP,
// para que funcione también si el servidor está apagado).

const { execFile } = require("node:child_process");
const { Diagnostic, DiagnosticSeverity, Range, Position, languages } = require("vscode");
const { check_on_save } = require("./settings");

const collection = languages.createDiagnosticCollection("pengu-cli");

const SEVERITIES = {
  error: DiagnosticSeverity.Error,
  warning: DiagnosticSeverity.Warning,
  info: DiagnosticSeverity.Information,
};

function to_diagnostic(item) {
  const start = new Position(Math.max(item.line - 1, 0), Math.max(item.column - 1, 0));
  const end = new Position(Math.max(item.endLine - 1, 0), Math.max(item.endColumn - 1, 0));
  const diagnostic = new Diagnostic(new Range(start, end), item.message, SEVERITIES[item.severity] ?? DiagnosticSeverity.Error);
  diagnostic.code = item.code;
  diagnostic.source = "pengu";
  return diagnostic;
}

function check_document(document, executable) {
  if (document.languageId !== "pengu") return;
  if (!check_on_save()) return;
  execFile(executable, ["check", "--json", document.uri.fsPath], { timeout: 30000 }, (_error, stdout) => {
    let payload;
    try {
      payload = JSON.parse(stdout);
    } catch (_parse_error) {
      return;
    }
    const diagnostics = Array.isArray(payload.diagnostics) ? payload.diagnostics.map(to_diagnostic) : [];
    collection.set(document.uri, diagnostics.length === 0 ? undefined : diagnostics);
  });
}

function clear(uri) {
  collection.delete(uri);
}

module.exports = { check_document, clear, collection };
