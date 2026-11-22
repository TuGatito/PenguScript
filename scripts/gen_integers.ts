// Genera `std/integers.pengu`: los enteros de ancho fijo comparten la misma
// superficie, así que el archivo se escribe desde una tabla en vez de a mano.
//
// Se ejecuta con `bun run scripts/gen_integers.ts` y el archivo generado se
// versiona como cualquier otro módulo de `std/`.

import { writeFileSync } from "node:fs";
import { join } from "node:path";

interface Block {
  readonly type: string;
  readonly signed: boolean;
}

const BLOCKS: readonly Block[] = [
  { type: "int8_t", signed: true },
  { type: "int16_t", signed: true },
  { type: "int32_t", signed: true },
  { type: "int64_t", signed: true },
  { type: "uint8_t", signed: false },
  { type: "uint16_t", signed: false },
  { type: "uint32_t", signed: false },
  { type: "uint64_t", signed: false },
];

// `size_t` y `ptrdiff_t` son alias de `uint64_t` e `int64_t` en LP64: si se
// emitieran sus bloques, las funciones libres del realm colisionarían (mismo
// nombre y mismo tipo de C++). Para usarlos, convierte con `as` (es seguro:
// mismo ancho y signo).

function limits_decl(block: Block): string {
  const name = block.type.replace(/_t$/, "");
  return [
    `  ${name}_max = () -> ${block.type}`,
    `  ${name}_min = () -> ${block.type}`,
  ].join("\n");
}

function method_block(block: Block): string {
  const type = block.type;
  const lines: string[] = [`enchanting ${type}`];

  if (block.signed) {
    lines.push(
      "  abs = -> " + type,
      "    if @ < 0 then -@ else @",
      "",
    );
  }

  lines.push(
    `  min = (otro: ${type}) -> ${type}`,
    "    if @ < otro then @ else otro",
    "",
    `  max = (otro: ${type}) -> ${type}`,
    "    if @ > otro then @ else otro",
    "",
    `  clamp = (minimo: ${type}, maximo: ${type}) -> ${type}`,
    "    if @ < minimo then minimo else if @ > maximo then maximo else @",
    "",
  );

  if (block.signed) {
    lines.push(
      "  sign = -> int",
      "    if @ > 0 then 1 else if @ < 0 then -1 else 0",
      "",
    );
  }

  lines.push(
    "  is_even = -> bool",
    "    (@ & 1) == 0",
    "",
    "  is_odd = -> bool",
    "    (@ & 1) != 0",
    "",
    "  is_positive = -> bool",
    "    @ > 0",
    "",
    "  is_negative = -> bool",
    "    @ < 0",
    "",
    "  is_zero = -> bool",
    "    @ == 0",
    "",
    `  min_value = -> ${type}`,
    `    ${type.replace(/_t$/, "")}_min()`,
    "",
    `  max_value = -> ${type}`,
    `    ${type.replace(/_t$/, "")}_max()`,
    "",
    "  to_int = -> int?",
    "    int::try_from(@)",
    "",
    "  to_int64 = -> int64_t?",
    "    int64_t::try_from(@)",
    "",
    "  to_uint64 = -> uint64_t?",
    "    uint64_t::try_from(@)",
    "",
    "  to_double = -> double",
    "    @ as double",
    "",
    "  to_size = -> size_t?",
    "    size_t::try_from(@)",
  );

  return lines.join("\n");
}

const header = [
  "realm integers",
  "",
  "-- Enteros de ancho fijo. Archivo generado por scripts/gen_integers.ts:",
  "-- no lo edites a mano, cambia la tabla del generador y vuelve a ejecutarlo.",
  "",
  "declare",
];

const decls = BLOCKS.map(limits_decl).join("\n");
const blocks = BLOCKS.map(method_block).join("\n\n");
const content = `${[...header, decls].join("\n")}\n\n${blocks}\n`;

const target = join(import.meta.dir, "..", "std", "integers.pengu");
writeFileSync(target, content, "utf8");
console.log(`escrito ${target} (${content.split("\n").length} líneas)`);
