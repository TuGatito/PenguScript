// Prepara `third_party/dts/` con los `.d.ts` que necesita `pengu ts-bindgen`.
//
// Los archivos vienen del paquete `typescript5` (alias de `typescript@5.7.3`,
// una dependencia de desarrollo). Se copian al repositorio para que `--check`
// y la suite funcionen sin red y sin `bun install`, y se firman en
// `MANIFEST.json` para detectar cambios silenciosos del paquete.
//
// Uso:
//   bun run scripts/fetch_dts.ts            # copia y escribe el manifiesto
//   bun run scripts/fetch_dts.ts --check    # verifica que coincide con el manifiesto

import { createHash } from "node:crypto";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const target_dir = join(root, "third_party", "dts");
const manifest_path = join(target_dir, "MANIFEST.json");

// Solo lo que necesitan el navegador y los tipos base: ES5..ES2022 y DOM.
const WANTED = /^lib\.(es5|es2015|es2016|es2017|es2018|es2019|es2020|es2021|es2022|dom)(\..+)?\.d\.ts$/;

export interface ManifestFile {
  readonly name: string;
  readonly bytes: number;
  readonly sha256: string;
}

export interface DtsManifest {
  readonly source: string;
  readonly version: string;
  readonly files: readonly ManifestFile[];
}

export function sha256_of(bytes: Uint8Array): string {
  return createHash("sha256").update(bytes).digest("hex");
}

function package_dir(): string {
  const candidates = [
    join(root, "node_modules", "typescript5"),
    join(root, "node_modules", "@typescript", "typescript5"),
  ];
  for (const candidate of candidates) {
    if (existsSync(join(candidate, "package.json"))) return candidate;
  }
  throw new Error(
    "no se encontró «typescript5»: ejecuta «bun add -d typescript5@npm:typescript@5.7.3»",
  );
}

function lib_dir(): string {
  return join(package_dir(), "lib");
}

function lib_version(): string {
  const raw = readFileSync(join(package_dir(), "package.json"), "utf8");
  const parsed = JSON.parse(raw) as { version?: string };
  return parsed.version ?? "desconocida";
}

function wanted_files(): string[] {
  return readdirSync(lib_dir())
    .filter((name) => WANTED.test(name))
    .sort();
}

function manifest_of(names: readonly string[]): DtsManifest {
  const files: ManifestFile[] = [];
  for (const name of names) {
    const bytes = readFileSync(join(lib_dir(), name));
    files.push({ name, bytes: bytes.length, sha256: sha256_of(bytes) });
  }
  return {
    source: "typescript@5.7.3 (paquete «typescript5»)",
    version: lib_version(),
    files,
  };
}

function render_manifest(manifest: DtsManifest): string {
  return `${JSON.stringify(manifest, null, 2)}\n`;
}

function read_manifest(): DtsManifest | undefined {
  if (!existsSync(manifest_path)) return undefined;
  return JSON.parse(readFileSync(manifest_path, "utf8")) as DtsManifest;
}

function copy_all(names: readonly string[]): void {
  mkdirSync(target_dir, { recursive: true });
  for (const name of names) {
    copyFileSync(join(lib_dir(), name), join(target_dir, name));
  }
  const license = join(package_dir(), "LICENSE.txt");
  if (existsSync(license)) copyFileSync(license, join(target_dir, "LICENSE.txt"));
  writeFileSync(manifest_path, render_manifest(manifest_of(names)));
}

function check_all(): number {
  const manifest = read_manifest();
  if (manifest === undefined) {
    console.error(`falta ${manifest_path}: ejecuta «bun run dts:prepare»`);
    return 1;
  }
  const expected = new Map(manifest.files.map((file) => [file.name, file]));
  let failures = 0;
  for (const file of manifest.files) {
    const path = join(target_dir, file.name);
    if (!existsSync(path)) {
      console.error(`falta ${file.name}`);
      failures += 1;
      continue;
    }
    const bytes = readFileSync(path);
    const digest = sha256_of(bytes);
    if (digest !== file.sha256 || bytes.length !== file.bytes) {
      console.error(`${file.name} no coincide con el manifiesto`);
      failures += 1;
    }
  }
  const present = readdirSync(target_dir).filter((name) => name.endsWith(".d.ts"));
  for (const name of present) {
    if (!expected.has(name)) {
      console.error(`${name} no está en el manifiesto`);
      failures += 1;
    }
  }
  if (failures > 0) return 1;
  console.log(`third_party/dts al día: ${manifest.files.length} archivos`);
  return 0;
}

function main(argv: readonly string[]): number {
  if (argv.includes("--check")) return check_all();
  const names = wanted_files();
  if (existsSync(target_dir)) rmSync(target_dir, { recursive: true, force: true });
  copy_all(names);
  console.log(`copiados ${names.length} archivos a third_party/dts (typescript ${lib_version()})`);
  return 0;
}

if (import.meta.main) {
  process.exit(main(process.argv.slice(2)));
}
