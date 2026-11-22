// Ajustes de la extensión en un solo lugar.

const { workspace } = require("vscode");

function configuration() {
  return workspace.getConfiguration("pengu");
}

// Lista de argumentos configurados (`pengu.build.args`, `pengu.run.args`).
function extra_args(key) {
  const configured = configuration().get(key, []);
  return Array.isArray(configured) ? configured.filter((item) => typeof item === "string") : [];
}

function check_on_save() {
  return configuration().get("check.onSave", false);
}

function inlay_sizes() {
  return configuration().get("inlayHints.sizes", false);
}

function inlay_types() {
  return configuration().get("inlayHints.types", true);
}

function completion_docs() {
  return configuration().get("completion.docs", true);
}

function status_size() {
  return configuration().get("statusBar.size", true);
}

module.exports = {
  configuration,
  extra_args,
  check_on_save,
  inlay_sizes,
  inlay_types,
  completion_docs,
  status_size,
};
