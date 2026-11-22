// Generación del archivo `.d.pengu` a partir de las funciones nativas.

import type { NativeFunction } from "./clang_ast.ts";
import { map_c_type } from "./type_map.ts";

export interface BindingReport {
  readonly text: string;
  readonly functions: number;
  readonly skipped: readonly string[];
}

export function sanitize_realm(name: string): string {
  const base = name.replace(/\.[^.]*$/, "");
  let out = "";
  for (const char of base) out += /[A-Za-z0-9_]/.test(char) ? char : "_";
  return /^[A-Za-z_]/.test(out) ? out : `_${out}`;
}

export function render_bindings(header_name: string, realm: string, functions: readonly NativeFunction[]): BindingReport {
  const lines: string[] = [
    `-- Enlaces generados por «pengu bindgen» desde ${header_name}.`,
    "-- No edites este archivo a mano: vuelve a ejecutar bindgen.",
    "",
    `realm ${realm}`,
    "",
    'extern "C"',
  ];

  let emitted = 0;
  const skipped: string[] = [];

  for (const fn of functions) {
    const params: string[] = [];
    let supported = true;
    for (const param of fn.params) {
      const mapped = map_c_type(param.type);
      if (!mapped.ok) supported = false;
      params.push(`${param.name}: ${mapped.pengu}`);
    }
    const result = map_c_type(fn.result);
    if (!result.ok) supported = false;

    if (!supported) {
      skipped.push(`${fn.name}: tipo no traducible`);
      continue;
    }

    // Las funciones C variádicas se enlazan con un parámetro variádico
    // final: `printf = (...resto: any) -> int`.
    if (fn.variadic) params.push("...resto: any");
    lines.push(`  ${fn.name} = (${params.join(", ")}) -> ${result.pengu}`);
    emitted += 1;
  }

  lines.push("");
  return { text: lines.join("\n"), functions: emitted, skipped };
}
