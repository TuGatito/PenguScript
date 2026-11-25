// Genera `src/project/std_bundle.ts` con el texto de `std/` para que el
// ejecutable compilado con `bun build --compile` siga encontrando la
// biblioteca estándar aunque el binario viva en otro directorio.

import { existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { fingerprint_sources } from "../src/project/std_fingerprint.ts";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const std_dir = join(root, "std");
const target = join(root, "src", "project", "std_bundle.ts");

function std_files(): string[] {
  const files: string[] = [];
  const walk = (dir: string): void => {
    for (const name of readdirSync(dir).sort()) {
      const path = join(dir, name);
      if (statSync(path).isDirectory()) walk(path);
      else if (name.endsWith(".pengu")) files.push(relative(root, path).split("\\").join("/"));
    }
  };
  walk(std_dir);
  return files;
}

function sources(): ReadonlyMap<string, string> {
  const map = new Map<string, string>();
  for (const file of std_files()) map.set(file, readFileSync(join(root, file), "utf8"));
  return map;
}

function render(): string {
  const bundled = sources();
  const lines = [
    "// GENERADO por scripts/embed_std.ts — no editar a mano.",
    "// Copia el texto de `std/*.pengu` dentro del binario compilado.",
    "",
    `export const STD_FILE_COUNT = ${bundled.size};`,
    `export const STD_FINGERPRINT = ${JSON.stringify(fingerprint_sources(bundled))};`,
    "",
    "export const STD_SOURCES: Readonly<Record<string, string>> = {",
  ];
  for (const [file, text] of bundled) {
    lines.push(`  ${JSON.stringify(file)}: ${JSON.stringify(text)},`);
  }
  lines.push("};", "");
  return lines.join("\n");
}

const content = render();
const check = process.argv.includes("--check");

if (check) {
  const current = existsSync(target) ? readFileSync(target, "utf8") : "";
  if (current !== content) {
    console.error("src/project/std_bundle.ts está desactualizado: ejecuta `bun run embed:std`.");
    process.exit(1);
  }
  console.log("std_bundle.ts al día.");
} else {
  writeFileSync(target, content);
  console.log(`std_bundle.ts actualizado (${std_files().length} archivos).`);
}
