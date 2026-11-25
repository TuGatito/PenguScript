// Lector de `.d.ts`: la puerta de entrada de `pengu ts-bindgen`.
//
// Se prueba contra un fixture controlado y contra `lib.dom.d.ts` de verdad, para
// detectar tanto regresiones de mapeo como cambios de tamaño en la librería.

import { describe, expect, test } from "bun:test";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { DtsClass, DtsInterface, DtsTypeAlias } from "../../src/tsbindgen/dts_ast.ts";
import { walk_named } from "../../src/tsbindgen/dts_ast.ts";
import { read_dts_file, read_dts_text } from "../../src/tsbindgen/dts_reader.ts";
import type { DtsMember, DtsType } from "../../src/tsbindgen/dts_type.ts";
import { type_text } from "../../src/tsbindgen/dts_type.ts";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const fixture = join(root, "tests", "fixtures", "tsbindgen", "browser_subset.d.ts");
const dom = join(root, "third_party", "dts", "lib.dom.d.ts");

function interface_of(name: string): DtsInterface {
  const module = read_dts_file(fixture);
  const node = module.by_name.get(name);
  if (node === undefined || node.kind !== "interface") {
    throw new Error(`falta la interfaz ${name}`);
  }
  return node;
}

function member_of(name: string, member: string): DtsMember {
  const node = interface_of(name);
  const found = node.members.find((entry) => "name" in entry && entry.name === member);
  if (found === undefined) throw new Error(`falta el miembro ${name}.${member}`);
  return found;
}

function type_of_member(name: string, member: string): DtsType {
  const entry = member_of(name, member);
  if (entry.kind !== "property") throw new Error(`${name}.${member} no es propiedad`);
  return entry.type;
}

describe("lector de .d.ts > declaraciones", () => {
  test("cuenta los tipos del fixture", () => {
    const module = read_dts_file(fixture);
    expect(module.stats.interfaces).toBeGreaterThanOrEqual(15);
    expect(module.stats.aliases).toBe(2);
    expect(module.stats.vars).toBe(4);
    expect(module.stats.functions).toBeGreaterThanOrEqual(3);
    expect(module.stats.namespaces).toBe(2);
    expect(module.stats.enums).toBe(1);
    expect(module.stats.unsupported).toBeGreaterThan(0);
  });

  test("lee la herencia de una interfaz", () => {
    const element = interface_of("Element");
    expect(element.heritage.map((entry) => entry.name)).toEqual(["Node"]);
    const html = interface_of("HTMLElement");
    expect(html.heritage.map((entry) => entry.name)).toEqual(["Element"]);
  });

  test("lee genéricos y parámetros por defecto", () => {
    const document = interface_of("Document");
    const query = document.members.find(
      (entry): entry is Extract<DtsMember, { kind: "method" }> =>
        entry.kind === "method" && entry.name === "querySelector",
    );
    expect(query?.type_params).toEqual(["E"]);
    expect(query?.params.map((param) => param.name)).toEqual(["selectors"]);
    expect(type_text(query?.result ?? { kind: "keyword", name: "void" })).toBe("E | null");
  });

  test("distingue readonly, opcional y escribible", () => {
    const node = member_of("Node", "nodeName");
    expect(node.kind).toBe("property");
    expect(node.kind === "property" && node.readonly).toBe(true);
    const parent = member_of("Node", "parentNode");
    expect(parent.kind === "property" && parent.readonly).toBe(true);
    const className = member_of("Element", "className");
    expect(className.kind === "property" && className.optional).toBe(true);
    const id = member_of("Element", "id");
    expect(id.kind === "property" && id.readonly).toBe(false);
  });

  test("lee el tipo de un miembro anulable", () => {
    expect(type_text(type_of_member("Node", "parentNode"))).toBe("Node | null");
  });

  test("lee firmas de método con parámetros opcionales", () => {
    const canvas = interface_of("HTMLCanvasElement");
    const get = canvas.members.find(
      (entry): entry is Extract<DtsMember, { kind: "method" }> =>
        entry.kind === "method" && entry.name === "getContext",
    );
    expect(get?.params.length).toBe(2);
    expect(get?.params[1]?.optional).toBe(true);
    expect(type_text(get?.result ?? { kind: "keyword", name: "void" })).toBe(
      "CanvasRenderingContext2D | null",
    );
  });

  test("lee index signatures", () => {
    const style = interface_of("CSSStyleDeclaration");
    const index = style.members.find((entry) => entry.kind === "index");
    expect(index?.kind).toBe("index");
    if (index?.kind === "index") {
      expect(type_text(index.key)).toBe("number");
      expect(type_text(index.value)).toBe("string");
    }
  });

  test("lee parámetros rest en funciones declaradas", () => {
    const module = read_dts_file(fixture);
    const timeout = module.nodes.find(
      (entry) => entry.kind === "function" && entry.name === "setTimeout",
    );
    expect(timeout?.kind).toBe("function");
    if (timeout?.kind === "function") {
      expect(timeout.params[2]?.rest).toBe(true);
      expect(type_text(timeout.params[2]?.type ?? { kind: "keyword", name: "any" })).toBe(
        "unknown",
      );
    }
  });

  test("lee alias de tipo y uniones", () => {
    const module = read_dts_file(fixture);
    const alias = module.by_name.get("BodyInit");
    expect(alias?.kind).toBe("alias");
    const type = (alias as DtsTypeAlias).type;
    expect(type_text(type)).toBe("string | Uint8Array | ArrayBuffer");
  });

  test("lee enumeraciones con valores", () => {
    const module = read_dts_file(fixture);
    const node = module.nodes.find((entry) => entry.kind === "enum");
    expect(node?.kind).toBe("enum");
    if (node?.kind === "enum") {
      expect(node.const).toBe(true);
      expect(node.members.map((entry) => entry.name)).toEqual(["None", "Some"]);
      expect(node.members[1]?.value).toBe("1");
    }
  });

  test("lee namespaces con funciones y constantes", () => {
    const module = read_dts_file(fixture);
    const math = module.nodes.find(
      (entry) => entry.kind === "namespace" && entry.name === "Math",
    );
    expect(math?.kind).toBe("namespace");
    if (math?.kind === "namespace") {
      const names = math.nodes.map((entry) => ("name" in entry ? entry.name : "?"));
      expect(names).toContain("PI");
      expect(names).toContain("sin");
    }
  });

  test("lee declaraciones globales", () => {
    const module = read_dts_file(fixture);
    const global = module.nodes.find((entry) => entry.kind === "global");
    expect(global?.kind).toBe("global");
    if (global?.kind === "global") {
      const names = global.nodes.map((entry) => ("name" in entry ? entry.name : "?"));
      expect(names).toEqual(["Window", "miVarGlobal"]);
    }
  });

  test("extrae la documentación JSDoc", () => {
    expect(interface_of("Node").doc).toContain("elemento del árbol");
    const member = member_of("Node", "nodeName");
    expect("doc" in member ? member.doc : undefined).toContain("Nombre del nodo");
  });

  test("marca los tipos sin traducción con su motivo", () => {
    const unsupported = interface_of("Unsupported");
    const motives = unsupported.members
      .filter((entry): entry is Extract<DtsMember, { kind: "property" }> => entry.kind === "property")
      .map((entry) => (entry.type.kind === "unsupported" ? entry.type.because : "soportado"));
    expect(motives).toContain("tipo condicional");
    expect(motives).toContain("mapped type");
    expect(motives).toContain("template literal type");
  });

  test("los índices de línea son los del archivo", () => {
    const module = read_dts_file(fixture);
    const node = module.by_name.get("Node");
    expect(node?.span.file.endsWith("browser_subset.d.ts")).toBe(true);
    expect(node?.span.line).toBeGreaterThan(1);
    expect(node?.span.column).toBe(1);
  });
});

describe("lector de .d.ts > lib.dom.d.ts real", () => {
  test("lee la librería del navegador", () => {
    const module = read_dts_file(dom);
    expect(module.stats.interfaces).toBeGreaterThan(1000);
    expect(module.stats.members).toBeGreaterThan(10000);
    expect(module.stats.vars).toBeGreaterThan(100);
    expect(module.by_name.get("Document")).toBeDefined();
    expect(module.by_name.get("EventTarget")).toBeDefined();
    expect(module.by_name.get("CanvasRenderingContext2D")).toBeDefined();
  }, 30_000);

  test("clasifica el árbol completo sin lanzar", () => {
    const module = read_dts_file(dom);
    const named = walk_named(module.nodes);
    expect(named.length).toBeGreaterThan(module.stats.interfaces);
  }, 30_000);

  test("lee desde texto y desde archivo igual", () => {
    const text = "interface A { b: string }";
    const module = read_dts_text("memoria.d.ts", text);
    expect(module.by_name.get("A")?.kind).toBe("interface");
    expect(module.file).toBe("memoria.d.ts");
  });

  test("una clase conserva sus métodos y constructores", () => {
    const class_module = read_dts_text(
      "clase.d.ts",
      [
        "declare class Punto {",
        "  constructor(x: number, y: number);",
        "  readonly x: number;",
        "  mover(dx: number): void;",
        "}",
      ].join("\n"),
    );
    const node = class_module.by_name.get("Punto") as DtsClass | undefined;
    expect(node?.kind).toBe("class");
    const kinds = node?.members.map((entry) => entry.kind) ?? [];
    expect(kinds).toContain("construct");
    expect(kinds).toContain("method");
    expect(kinds).toContain("property");
  });
});
