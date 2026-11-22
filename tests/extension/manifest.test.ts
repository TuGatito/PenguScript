// Comprobaciones del manifiesto: todo lo que la extensión contribuye debe
// existir y coincidir con lo que registra el código.

import { describe, expect, test } from "bun:test";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const extension_root = new URL("../../editors/vscode/", import.meta.url).pathname;
const package_json = JSON.parse(readFileSync(join(extension_root, "package.json"), "utf8"));
const commands_js = readFileSync(join(extension_root, "src/commands.js"), "utf8");
const tasks_js = readFileSync(join(extension_root, "src/tasks.js"), "utf8");

function declared_commands(): string[] {
  return package_json.contributes.commands.map((command: { command: string }) => command.command);
}

function registered_commands(): string[] {
  return [...commands_js.matchAll(/register\("(pengu\.[A-Za-z]+)"/g)].map((match) => match[1] as string);
}

function contributes_path(path: string): string {
  return join(extension_root, path);
}

describe("manifiesto de la extensión", () => {
  test("versión y punto de entrada", () => {
    expect(package_json.version).toBe("0.1.0");
    expect(existsSync(contributes_path(package_json.main))).toBe(true);
    expect(package_json.activationEvents).toContain("onLanguage:pengu");
  });

  test("los archivos contribuidos existen", () => {
    const language = package_json.contributes.languages[0];
    expect(existsSync(contributes_path(language.configuration))).toBe(true);
    expect(language.extensions).toContain(".pengu");
    expect(language.filenamePatterns).toContain("*.d.pengu");
    for (const grammar of package_json.contributes.grammars) {
      expect(existsSync(contributes_path(grammar.path))).toBe(true);
    }
    for (const snippet of package_json.contributes.snippets) {
      expect(existsSync(contributes_path(snippet.path))).toBe(true);
    }
  });

  test("comandos declarados y registrados coinciden", () => {
    const declared = declared_commands().sort();
    const registered = registered_commands().sort();
    expect(registered).toEqual(declared);
    expect(declared).toContain("pengu.runFile");
    expect(declared).toContain("pengu.buildFile");
    expect(declared).toContain("pengu.checkFile");
    expect(declared).toContain("pengu.restartServer");
  });

  test("ajustes usados por el código están declarados", () => {
    const properties = Object.keys(package_json.contributes.configuration.properties);
    for (const key of ["pengu.executable", "pengu.build.args", "pengu.run.args", "pengu.check.onSave", "pengu.lsp.trace.server"]) {
      expect(properties).toContain(key);
    }
    expect(package_json.contributes.configurationDefaults["[pengu]"]["editor.tabSize"]).toBe(2);
  });

  test("tareas y problem matcher están conectados", () => {
    expect(package_json.contributes.taskDefinitions[0].type).toBe("pengu");
    expect(package_json.contributes.taskDefinitions[0].properties.command.enum).toEqual(["build", "run"]);
    expect(tasks_js).toContain('"$pengu"');
    expect(tasks_js).toContain("registerTaskProvider");
    const matcher = package_json.contributes.problemMatchers[0];
    expect(matcher.name).toBe("pengu");
    expect(matcher.source).toBe("pengu");
  });

  test("menús y atajos apuntan a comandos existentes", () => {
    const declared = new Set(declared_commands());
    for (const entries of Object.values(package_json.contributes.menus) as Array<Array<{ command: string }>>) {
      for (const entry of entries) expect(declared.has(entry.command)).toBe(true);
    }
    for (const binding of package_json.contributes.keybindings) {
      expect(declared.has(binding.command)).toBe(true);
    }
  });
});
