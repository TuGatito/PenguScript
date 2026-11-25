// Driver de compilación: fuente PenguScript → C++20 → ejecutable.
//
// Cada compilación vive en `.pengu-cache/<hash>/`, junto a la cabecera
// del runtime. La caché es deliberadamente simple (sin manifiesto de
// dependencias todavía): el hash incluye ruta y contenido.

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import type { Diagnostic } from "../diagnostics/diagnostic.ts";
import { make_diagnostic } from "../diagnostics/diagnostic.ts";
import { CODES } from "../diagnostics/codes.ts";
import { make_sink } from "../diagnostics/sink.ts";
import { analyze_graph } from "./analyze.ts";
import { generate_program, collect_type_realms } from "../codegen/cpp_module.ts";
import type { ProgramUnit } from "../codegen/cpp_module.ts";
import { check_program } from "../semantic/checker.ts";
import { RUNTIME_HEADER } from "../codegen/runtime_source.ts";
import type { ExprNode } from "../frontend/ast_expr.ts";
import type { ModuleInfo } from "../semantic/module_info.ts";
import type { PenguType } from "../semantic/types.ts";
import { make_source, span_from } from "../util/span.ts";
import { find_cxx } from "./toolchain.ts";
import { link_flags } from "./link.ts";
import { compile_js_file } from "./compile_js.ts";
import type { Target } from "./target.ts";
import { DEFAULT_TARGET } from "./target.ts";
import type { Int64Mode } from "../codegen/js_types.ts";

export interface CompileOptions {
  // Objetos o bibliotecas extra para el enlazador (`.o`, `.a`, `-lm`...).
  readonly link?: readonly string[];
  readonly compiler?: string;
  readonly out_dir?: string;
  // Backend de generación (`--target`). Por defecto, C++20.
  readonly target?: Target;
  // Salida del backend JS: un directorio (§12.1 #3).
  readonly out?: string;
  // `--release`: optimiza (`-O2`) en vez de `-O1`.
  readonly release?: boolean;
  // Representación de los enteros de 64 bits en JS (`--int64`).
  readonly int64?: Int64Mode;
  // Comentarios JSDoc en el código generado (`--jsdoc`, P6).
  readonly jsdoc?: boolean;
}

export interface CompileResult {
  readonly ok: boolean;
  readonly diagnostics: readonly Diagnostic[];
  readonly output: string;
  readonly target?: Target;
  readonly source_path?: string;
  readonly cpp_path?: string;
  readonly binary_path?: string;
  readonly cache_dir?: string;
  readonly reused?: boolean;
  // Backend JS: directorio con los `.mjs` y punto de entrada del programa.
  readonly output_dir?: string;
  readonly js_entry_path?: string;
  readonly files?: readonly string[];
}

export function compile_file(path: string, options: CompileOptions = {}): CompileResult {
  const target = options.target ?? DEFAULT_TARGET;
  const source_path = resolve(path);
  if (!existsSync(source_path)) {
    return {
      ok: false,
      target,
      output: "",
      diagnostics: [
        make_diagnostic({
          code: CODES.file_not_found,
          message: `no existe el archivo «${path}»`,
          span: { file: source_path, start: { line: 1, column: 1, offset: 0 }, end: { line: 1, column: 1, offset: 0 } },
        }),
      ],
    };
  }
  if (target === "js") return compile_js_file(source_path, options);
  return compile_cpp_file(source_path, options);
}

function compile_cpp_file(path: string, options: CompileOptions): CompileResult {
  const source_path = resolve(path);
  const text = readFileSync(source_path, "utf8");
  const source = make_source(source_path, text);
  const sink = make_sink({ max: 200 });

  const analysis = analyze_graph(source_path, sink);
  const units = analysis.units;
  const entry_module = analysis.entry_module;
  if (entry_module === undefined) {
    return { ok: false, target: "cpp", diagnostics: sink.diagnostics, output: "", source_path };
  }
  // Los módulos pueden declarar sus bibliotecas con `link "..."`; se
  // suman a las de la línea de órdenes.
  const link = link_flags([...units.flatMap((unit) => unit.module.links), ...(options.link ?? [])]);
  const generated = generate_program(units, entry_module, sink);

  if (sink.has_errors()) {
    return { ok: false, target: "cpp", diagnostics: sink.diagnostics, output: "", source_path };
  }

  const compiler = options.compiler ?? find_cxx();
  if (compiler === undefined) {
    return {
      ok: false,
      target: "cpp",
      output: "",
      diagnostics: [
        make_diagnostic({
          code: CODES.toolchain_missing,
          message: "no se encontró un compilador de C++20 (g++ o clang++)",
          span: span_from(source, 0, 0),
          notes: ["instala g++ o clang++ y vuelve a intentarlo"],
        }),
      ],
      source_path,
    };
  }

  // La clave de caché depende del C++ generado, del runtime y de las
  // opciones de enlace: si cambia cualquier módulo importado, cambia.
  const cache_key = [
    generated.code,
    RUNTIME_HEADER,
    compiler,
    ...link,
  ].join("\u0000");
  const cache_dir = options.out_dir ?? join(dirname(source_path), ".pengu-cache", content_hash(source_path, cache_key));
  mkdirSync(cache_dir, { recursive: true });
  const cpp_path = join(cache_dir, "module.cpp");
  const binary_path = join(cache_dir, "program");

  if (existsSync(binary_path) && existsSync(cpp_path)) {
    return {
      ok: true,
      target: "cpp",
      diagnostics: [],
      output: "",
      source_path,
      cpp_path,
      binary_path,
      cache_dir,
      reused: true,
    };
  }

  writeFileSync(join(cache_dir, "pengu_rt.hpp"), RUNTIME_HEADER);
  writeFileSync(cpp_path, generated.code);

  const optimization = options.release === true ? "-O2" : "-O1";
  const compile = spawnSync(
    compiler,
    [cpp_path, "-std=c++20", optimization, "-Wall", "-Wextra", "-Wno-unused-parameter", "-Wno-unused-variable", "-Wno-unused-but-set-variable", "-o", binary_path, ...link],
    { encoding: "utf8" },
  );

  if (compile.status !== 0) {
    const stderr = (compile.stderr ?? "").trim();
    return {
      ok: false,
      target: "cpp",
      output: stderr,
      diagnostics: [
        make_diagnostic({
          code: CODES.compile_failed,
          message: "el compilador de C++ rechazó el código generado",
          span: span_from(source, 0, 0),
          notes: stderr.length > 0 ? [stderr.slice(-4000)] : [],
        }),
      ],
      source_path,
      cpp_path,
      cache_dir,
    };
  }

  return {
    ok: true,
    target: "cpp",
    diagnostics: sink.diagnostics,
    output: (compile.stderr ?? "").trim(),
    source_path,
    cpp_path,
    binary_path,
    cache_dir,
  };
}

function content_hash(path: string, text: string): string {
  let hash = 2166136261;
  const input = `${path}\u0000${text}`;
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}
