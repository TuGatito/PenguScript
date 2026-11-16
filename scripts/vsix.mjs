#!/usr/bin/env node
// Empaqueta la extensión de VS Code en un .vsix e, opcionalmente, la instala.
//
// Uso:
//   node scripts/vsix.mjs [--out dist/pengu-lsp-0.1.0.vsix] [--install]
//                         [--code code] [--check] [--verbose]
//
// No usa dependencias de npm: valida el manifiesto, arma el árbol de la
// extensión y comprime con `zip` (o `Compress-Archive` en Windows). El .vsix es
// un ZIP con:
//   [Content_Types].xml
//   extension.vsixmanifest
//   extension/...            copia de editors/vscode

import { spawnSync } from "node:child_process";
import {
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const extensionDir = join(root, "editors", "vscode");

function fail(message) {
  console.error(`error: ${message}`);
  process.exit(1);
}

function parseArgs(argv) {
  const options = {
    out: "",
    install: false,
    code: process.env.PENGU_CODE || "code",
    check: false,
    verbose: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--install") options.install = true;
    else if (value === "--check") options.check = true;
    else if (value === "--verbose") options.verbose = true;
    else if (value === "--out") {
      options.out = argv[index + 1] ?? "";
      index += 1;
    } else if (value.startsWith("--out=")) options.out = value.slice(6);
    else if (value === "--code") {
      options.code = argv[index + 1] ?? "code";
      index += 1;
    } else if (value.startsWith("--code=")) options.code = value.slice(7);
    else if (value === "-h" || value === "--help") {
      console.log(
        "uso: node scripts/vsix.mjs [--out RUTA] [--install] [--code BIN] [--check] [--verbose]",
      );
      process.exit(0);
    } else fail(`opción desconocida \`${value}\``);
  }
  return options;
}

function readManifest() {
  const path = join(extensionDir, "package.json");
  if (!existsSync(path)) fail(`no existe ${path}`);
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    fail(`package.json inválido: ${error.message}`);
  }
  for (const field of ["name", "publisher", "version", "engines", "main"]) {
    if (!manifest[field]) fail(`package.json no declara \`${field}\``);
  }
  if (!manifest.engines.vscode) fail("package.json no declara `engines.vscode`");
  if (!existsSync(join(extensionDir, manifest.main))) {
    fail(`el \`main\` declarado no existe: ${manifest.main}`);
  }
  const grammars = manifest.contributes?.grammars ?? [];
  for (const grammar of grammars) {
    if (!existsSync(join(extensionDir, grammar.path))) {
      fail(`la gramática declarada no existe: ${grammar.path}`);
    }
  }
  const languages = manifest.contributes?.languages ?? [];
  for (const language of languages) {
    if (language.configuration && !existsSync(join(extensionDir, language.configuration))) {
      fail(`la configuración declarada no existe: ${language.configuration}`);
    }
  }
  return manifest;
}

function compilerVersion() {
  const result = spawnSync("pengu", ["version", "--json"], { encoding: "utf8" });
  if (result.status !== 0) return null;
  try {
    return JSON.parse(result.stdout).version ?? null;
  } catch {
    return null;
  }
}

function escapeXml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

const CONTENT_TYPES = `<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension=".json" ContentType="application/json"/>
  <Default Extension=".js" ContentType="application/javascript"/>
  <Default Extension=".md" ContentType="text/markdown"/>
  <Default Extension=".png" ContentType="image/png"/>
  <Default Extension=".svg" ContentType="image/svg+xml"/>
  <Default Extension=".txt" ContentType="text/plain"/>
  <Default Extension=".vsixmanifest" ContentType="text/xml"/>
  <Default Extension=".xml" ContentType="text/xml"/>
</Types>
`;

function manifestXml(manifest) {
  const icon = manifest.icon
    ? `\n    <Icon>extension/${escapeXml(manifest.icon)}</Icon>`
    : "";
  const description = escapeXml(manifest.description ?? "");
  const categories = (manifest.categories ?? []).map(escapeXml).join(",");
  const tags = (manifest.keywords ?? []).map(escapeXml).join(",");
  return `<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="${escapeXml(manifest.name)}" Version="${escapeXml(
    manifest.version,
  )}" Publisher="${escapeXml(manifest.publisher)}" />
    <DisplayName>${escapeXml(manifest.displayName ?? manifest.name)}</DisplayName>
    <Description xml:space="preserve">${description}</Description>
    <Tags>${tags}</Tags>
    <Categories>${categories}</Categories>${icon}
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="${escapeXml(
        manifest.engines.vscode,
      )}" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="workspace" />
      <Property Id="Microsoft.VisualStudio.Code.LocalizedLanguages" Value="" />
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
  </Assets>
</PackageManifest>
`;
}

function copyExtension(target) {
  const skip = new Set(["node_modules", ".git", "dist", "*.vsix"]);
  mkdirSync(target, { recursive: true });
  for (const entry of readdirSync(extensionDir)) {
    if (skip.has(entry) || entry.endsWith(".vsix")) continue;
    const from = join(extensionDir, entry);
    if (statSync(from).isDirectory()) {
      cpSync(from, join(target, entry), { recursive: true });
    } else {
      cpSync(from, join(target, entry));
    }
  }
}

function zipDirectory(staging, output) {
  mkdirSync(dirname(output), { recursive: true });
  if (existsSync(output)) rmSync(output);
  const zip = spawnSync("zip", ["-q", "-X", "-r", output, "."], {
    cwd: staging,
    encoding: "utf8",
  });
  if (zip.error?.code === "ENOENT" || zip.status === 127) {
    const powershell = spawnSync(
      "powershell",
      [
        "-NoProfile",
        "-Command",
        `Compress-Archive -Path '${staging}\\*' -DestinationPath '${output}' -Force`,
      ],
      { encoding: "utf8" },
    );
    if (powershell.status !== 0) {
      fail(`no hay \`zip\` ni PowerShell para comprimir: ${powershell.stderr ?? ""}`);
    }
    return;
  }
  if (zip.status !== 0) fail(`\`zip\` falló: ${zip.stderr || zip.stdout}`);
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const manifest = readManifest();
  const id = `${manifest.publisher}.${manifest.name}`;
  const compiler = compilerVersion();
  if (compiler && compiler !== manifest.version) {
    fail(
      `la extensión declara ${manifest.version} y el compilador es ${compiler}; ` +
        "igualá las versiones antes de empaquetar",
    );
  }
  const out = resolve(options.out || `dist/${id}-${manifest.version}.vsix`);
  console.log(`extensión ${id} ${manifest.version}`);
  if (options.check) {
    console.log("manifiesto válido");
    return;
  }
  const staging = mkdtempSync(join(tmpdir(), "pengu-vsix-"));
  try {
    writeFileSync(join(staging, "[Content_Types].xml"), CONTENT_TYPES);
    writeFileSync(join(staging, "extension.vsixmanifest"), manifestXml(manifest));
    copyExtension(join(staging, "extension"));
    zipDirectory(staging, out);
  } finally {
    rmSync(staging, { recursive: true, force: true });
  }
  const size = statSync(out).size;
  console.log(`generado ${relative(root, out)} (${size} bytes)`);
  if (options.verbose) {
    const list = spawnSync("unzip", ["-l", out], { encoding: "utf8" });
    if (list.status === 0) console.log(list.stdout);
  }
  if (options.install) {
    const install = spawnSync(
      options.code,
      ["--install-extension", out, "--force"],
      { encoding: "utf8" },
    );
    if (install.error?.code === "ENOENT") {
      console.log(
        `aviso: \`${options.code}\` no está en el PATH; instala a mano: ${relative(root, out)}`,
      );
      return;
    }
    if (install.status !== 0) {
      fail(`\`${options.code} --install-extension\` falló: ${install.stderr || install.stdout}`);
    }
    process.stdout.write(install.stdout);
    console.log(`instalada ${id}`);
  }
}

main();
