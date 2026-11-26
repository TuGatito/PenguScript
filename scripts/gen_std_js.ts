// Genera el catálogo `std/js/*` desde las librerías de TypeScript.
//
// Uso:
//   bun run gen:std-js            # escribe los `.d.pengu` del catálogo
//   bun run gen:std-js --check    # falla si alguno no está al día
//
// Los `.d.ts` de origen viven en `third_party/dts` (ver `scripts/fetch_dts.ts`)
// y el generador es `pengu ts-bindgen`, así que este script solo decide qué
// archivos se generan, con qué realm y qué `invoke` necesitan.

import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";

interface Target {
  readonly lib: string;
  readonly out: string;
  readonly realm: string;
  /** Dominio de `src/tsbindgen/domain.ts`; estrecha el archivo a ese dominio. */
  readonly only?: string;
  readonly invokes: readonly string[];
}

// Un archivo por dominio, con el realm `js_<dominio>` (decisión §10.7).
export const TARGETS: readonly Target[] = [
  {
    lib: "lib.dom.d.ts",
    out: "std/js/dom_generated.d.pengu",
    realm: "js_dom_generated",
    invokes: ["std/js/types"],
  },
  // Dominios pequeños y autoconsistentes: su cierre de dependencias no arrastra
  // `Document`/`Window`, así que se generan recortados (`--only`). `dom`,
  // `events` y `canvas` no aparecen aquí porque su cierre es prácticamente
  // `lib.dom.d.ts` entero (760/758/757 de 1123 tipos) y ya están en
  // `dom_generated`.
  {
    lib: "lib.dom.d.ts",
    out: "std/js/fetch_generated.d.pengu",
    realm: "js_fetch_generated",
    only: "fetch",
    invokes: ["std/js/types"],
  },
  {
    lib: "lib.dom.d.ts",
    out: "std/js/storage_generated.d.pengu",
    realm: "js_storage_generated",
    only: "storage",
    invokes: ["std/js/types"],
  },
  {
    lib: "lib.dom.d.ts",
    out: "std/js/performance_generated.d.pengu",
    realm: "js_performance_generated",
    only: "performance",
    invokes: ["std/js/types"],
  },
  {
    lib: "lib.es5.d.ts",
    out: "std/js/es5_generated.d.pengu",
    realm: "js_es5_generated",
    invokes: ["std/js/types"],
  },
];

const ROOT = resolve(import.meta.dir, "..");

export function main(argv: readonly string[]): number {
  const check = argv.includes("--check");
  const failures: string[] = [];

  for (const target of TARGETS) {
    const source = join(ROOT, "third_party", "dts", target.lib);
    if (!existsSync(source)) {
      failures.push(`falta ${target.lib}: ejecuta bun run dts:prepare`);
      continue;
    }
    const args = ["run", "src/main.ts", "ts-bindgen", source, "--realm", target.realm, "--out", join(ROOT, target.out)];
    if (target.only !== undefined) args.push("--only", target.only);
    if (check) args.push("--check");
    const run = spawnSync("bun", args, { cwd: ROOT, encoding: "utf8" });
    if (run.status !== 0) {
      failures.push((run.stdout + run.stderr).trim());
      continue;
    }
    if (check) console.log(`ok ${target.out}`);
  }

  if (failures.length > 0) {
    for (const failure of failures) console.error(failure);
    return 1;
  }
  return 0;
}

if (import.meta.main) {
  process.exit(main(process.argv.slice(2)));
}
