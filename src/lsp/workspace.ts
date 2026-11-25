// Raíz del workspace tal como la anuncia el editor.
//
// El protocolo permite `rootUri` (LSP 3.16) o `workspaceFolders`. Sin esto el
// servidor deducía la raíz del archivo abierto y, cuando el archivo era un
// `std/…` del proyecto, la raíz acababa siendo `std/` y todas las
// importaciones se resolvían contra la stdlib equivocada.

import { fileURLToPath } from "node:url";

export function path_from_uri(uri: string): string | undefined {
  if (!uri.startsWith("file://")) return undefined;
  try {
    return fileURLToPath(uri);
  } catch {
    return undefined;
  }
}

function folder_uri(folder: unknown): string | undefined {
  if (typeof folder !== "object" || folder === null) return undefined;
  const uri = (folder as { readonly uri?: unknown }).uri;
  return typeof uri === "string" ? uri : undefined;
}

export function workspace_root(params: Record<string, unknown> | undefined): string | undefined {
  if (params === undefined) return undefined;
  const root_uri = params["rootUri"];
  if (typeof root_uri === "string") {
    const path = path_from_uri(root_uri);
    if (path !== undefined) return path;
  }
  const folders = params["workspaceFolders"];
  if (Array.isArray(folders)) {
    for (const folder of folders) {
      const uri = folder_uri(folder);
      if (uri === undefined) continue;
      const path = path_from_uri(uri);
      if (path !== undefined) return path;
    }
  }
  return undefined;
}
