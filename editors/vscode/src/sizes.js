// Tamaños medidos: la extensión pregunta al servidor por el símbolo bajo el
// cursor y lo muestra en la barra de estado, sin adivinar tamaños.

const { window } = require("vscode");

// Petición propia del servidor (`pengu/sizeAt`): devuelve el tipo y el
// tamaño real del símbolo en esa posición, o `null`.
async function size_at(state, document, position) {
  const client = state.client;
  if (client === undefined || document === undefined) return undefined;
  try {
    const result = await client.sendRequest("pengu/sizeAt", {
      textDocument: { uri: document.uri.toString() },
      position: { line: position.line, character: position.character },
    });
    return result ?? undefined;
  } catch (_error) {
    return undefined;
  }
}

function format_size(info) {
  if (info === undefined || typeof info.size !== "number") return undefined;
  const name = typeof info.name === "string" && info.name.length > 0 ? `${info.name}: ` : "";
  const type = typeof info.type === "string" && info.type.length > 0 ? `${info.type} · ` : "";
  return `${name}${type}${info.size} B`;
}

// La barra de estado de la extensión (la primera) muestra el ejecutable;
// esta segunda muestra el tamaño del símbolo bajo el cursor.
function create_size_item() {
  const { StatusBarAlignment } = require("vscode");
  return window.createStatusBarItem(StatusBarAlignment.Right, 20);
}

module.exports = { size_at, format_size, create_size_item };
