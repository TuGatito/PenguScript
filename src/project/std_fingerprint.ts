// Huella de la biblioteca estándar: identifica la copia exacta de `std/`.
//
// El binario la lleva empotrada y `pengu doctor` la compara con la del
// proyecto. Así se detecta el caso que producía errores fantasma en el LSP:
// un compilador instalado con una std vieja analizando un proyecto cuya std
// es otra. El algoritmo es estable entre el script de empaquetado y el
// binario: sha256 sobre rutas ordenadas y contenido, separados por NUL.

import { createHash } from "node:crypto";

export function fingerprint_sources(sources: ReadonlyMap<string, string>): string {
  const hash = createHash("sha256");
  for (const path of [...sources.keys()].sort()) {
    hash.update(path);
    hash.update("\0");
    hash.update(sources.get(path) ?? "");
    hash.update("\0");
  }
  return hash.digest("hex").slice(0, 16);
}
