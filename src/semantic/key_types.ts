// Requisitos de las claves de los contenedores asociativos.
//
// `map`/`set` están ordenados: la clave necesita «<=>» o «<». Las formas
// `unordered_*` necesitan «==» y un hash; el hash de las runes se sintetiza
// campo a campo, así que todos los campos deben ser hasheables.

import type { Span } from "../util/span.ts";
import type { DiagnosticSink } from "../diagnostics/sink.ts";
import { CODES } from "../diagnostics/codes.ts";
import { make_diagnostic } from "../diagnostics/diagnostic.ts";
import type { PenguType } from "./types.ts";
import { type_display } from "./types.ts";
import type { TypeEnv } from "./type_env.ts";

const ORDERED_CONTAINERS = new Set(["map", "multimap", "set", "multiset"]);
const HASHED_CONTAINERS = new Set([
  "unordered_map",
  "unordered_multimap",
  "unordered_set",
  "unordered_multiset",
]);

const HASHABLE_PRIMITIVES = new Set([
  "bool",
  "char",
  "signed char",
  "unsigned char",
  "short",
  "unsigned short",
  "int",
  "unsigned int",
  "long",
  "unsigned long",
  "long long",
  "unsigned long long",
  "float",
  "double",
  "long double",
  "char8_t",
  "char16_t",
  "char32_t",
  "wchar_t",
  "size_t",
  "ptrdiff_t",
  "intptr_t",
  "uintptr_t",
  "byte",
  "int8_t",
  "int16_t",
  "int32_t",
  "int64_t",
  "uint8_t",
  "uint16_t",
  "uint32_t",
  "uint64_t",
  "string",
  "wstring",
  "u8string",
  "u16string",
  "u32string",
  "string_view",
]);

const ORDERED_PRIMITIVES = HASHABLE_PRIMITIVES;

/** ¿Se puede hashear este tipo con `std::hash`? */
export function is_hashable(env: TypeEnv, type: PenguType, seen: Set<string> = new Set()): boolean {
  switch (type.kind) {
    case "primitive":
      return HASHABLE_PRIMITIVES.has(type.name);
    case "optional":
      return is_hashable(env, type.inner, seen);
    case "tuple":
      return type.items.every((item) => is_hashable(env, item, seen));
    case "named": {
      const rune = env.runes.get(type.name);
      if (rune !== undefined) {
        if (seen.has(type.name)) return false;
        seen.add(type.name);
        return [...rune.fields.values()].every((field) => is_hashable(env, field.type, seen));
      }
      const alias = env.aliases.get(type.name);
      if (alias !== undefined) {
        return alias.seal ? is_hashable(env, alias.target, seen) : is_hashable(env, alias.target, seen);
      }
      if (env.omens.has(type.name)) return true;
      if (type.name === "pair" && type.args.length === 2) {
        return type.args.every((arg) => is_hashable(env, arg, seen));
      }
      return false;
    }
    default:
      return false;
  }
}

/** ¿Se puede ordenar este tipo con `<`? */
export function is_ordered(env: TypeEnv, type: PenguType, seen: Set<string> = new Set()): boolean {
  switch (type.kind) {
    case "primitive":
      return ORDERED_PRIMITIVES.has(type.name);
    case "optional":
      return is_ordered(env, type.inner, seen);
    case "tuple":
      return type.items.every((item) => is_ordered(env, item, seen));
    case "named": {
      const rune = env.runes.get(type.name);
      if (rune !== undefined) {
        if (seen.has(type.name)) return false;
        seen.add(type.name);
        return rune.methods.has("<=>") || rune.methods.has("<");
      }
      const alias = env.aliases.get(type.name);
      if (alias !== undefined) return is_ordered(env, alias.target, seen);
      if (env.omens.has(type.name)) return true;
      if (type.name === "pair" && type.args.length === 2) {
        return type.args.every((arg) => is_ordered(env, arg, seen));
      }
      return false;
    }
    default:
      return false;
  }
}

/** Comprueba que la clave de un contenedor asociativo cumple su contrato. */
export function check_key_requirements(
  env: TypeEnv,
  container: string,
  args: readonly PenguType[],
  span: Span,
  sink: DiagnosticSink,
): void {
  const hashed = HASHED_CONTAINERS.has(container);
  if (!hashed && !ORDERED_CONTAINERS.has(container)) return;
  const key = args[0];
  if (key === undefined) return;
  // Dentro de un cuerpo genérico la clave es un sigilo: se comprobará al
  // instanciar el contenedor con un tipo concreto.
  if (key.kind === "named" && key.generic === true) return;
  if (key.kind === "any") return;
  if (hashed) {
    check_hashed_key(env, container, key, span, sink);
  } else {
    check_ordered_key(env, container, key, span, sink);
  }
}

function check_ordered_key(
  env: TypeEnv,
  container: string,
  key: PenguType,
  span: Span,
  sink: DiagnosticSink,
): void {
  if (is_ordered(env, key)) return;
  sink.add(
    make_diagnostic({
      code: CODES.type_mismatch,
      severity: "error",
      message: `«${type_display(key)}» se usa como clave de «${container}» y no define «<=>» ni «<»`,
      span,
      notes: ["declara «operator <=>» o «operator <» en el tipo, o usa un contenedor «unordered_»"],
    }),
  );
}

function check_hashed_key(
  env: TypeEnv,
  container: string,
  key: PenguType,
  span: Span,
  sink: DiagnosticSink,
): void {
  const rune = key.kind === "named" ? env.runes.get(key.name) : undefined;
  if (rune !== undefined && !rune.methods.has("==")) {
    sink.add(
      make_diagnostic({
        code: CODES.type_mismatch,
        severity: "error",
        message: `«${type_display(key)}» se usa como clave de «${container}» y no declara «operator ==»`,
        span,
        notes: ["las claves «unordered_» comparan con «==»; el hash se sintetiza"],
      }),
    );
  }
  if (is_hashable(env, key)) return;
  sink.add(
    make_diagnostic({
      code: CODES.type_mismatch,
      severity: "error",
      message: `«${type_display(key)}» no se puede hashear y se usa como clave de «${container}»`,
      span,
      notes: ["los campos hasheables son primitivos, texto, omens y otros tipos hasheables"],
    }),
  );
}
