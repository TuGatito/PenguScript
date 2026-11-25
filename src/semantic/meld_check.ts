// Comprobaciones de las construcciones nuevas de `.d.pengu`:
// uniones (`meld`) y campos con ancho en bits (`bits`).

import type { FieldDecl, MeldDecl } from "../frontend/ast_decl.ts";
import { CODES } from "../diagnostics/codes.ts";
import { error as make_error } from "../diagnostics/diagnostic.ts";
import type { CheckContext } from "./checker_context.ts";
import { reject_opaque_by_value } from "./opaque_check.ts";
import { integer_shape, type_display } from "./types.ts";
import type { PenguType } from "./types.ts";

const MAX_DEPTH = 8;

export function check_meld(ctx: CheckContext, decl: MeldDecl): void {
  for (const field of decl.fields) {
    const info = ctx.module.env.runes.get(decl.name)?.fields.get(field.name);
    const type = info?.type;
    if (type === undefined) continue;

    if (field.bits !== undefined) {
      ctx.sink.add(
        make_error(
          CODES.meld_field_invalid,
          `la unión «${decl.name}» no admite «bits» en el campo «${field.name}»`,
          field.span,
          "usa un «rune» si necesitas un campo con ancho en bits",
        ),
      );
    }
    if (field.default_value !== undefined) {
      ctx.sink.add(
        make_error(
          CODES.meld_field_invalid,
          `el campo «${field.name}» de la unión «${decl.name}» no puede tener valor por defecto`,
          field.span,
          "una unión solo reserva el espacio: el valor se escribe al asignar el campo",
        ),
      );
    }
    reject_opaque_by_value(ctx, type, field.span, "un campo de unión");
    if (!is_trivial(ctx, type, 0)) {
      ctx.sink.add(
        make_error(
          CODES.meld_field_invalid,
          `el campo «${field.name}» de la unión «${decl.name}» tiene tipo «${type_display(type)}», que C++ no puede guardar en una «union»`,
          field.span,
          "solo se admiten tipos triviales (números, lógicos, caracteres, punteros «raw», omens y runes sin constructor)",
        ),
      );
    }
  }
}

export function check_bitfield(
  ctx: CheckContext,
  type: PenguType,
  bits: number,
  span: FieldDecl["span"],
): void {
  const shape = integer_shape(type);
  if (shape === undefined) {
    ctx.sink.add(
      make_error(
        CODES.bitfield_width,
        `un campo con «bits» necesita un tipo entero, se encontró «${type_display(type)}»`,
        span,
      ),
    );
    return;
  }
  if (bits < 1 || bits > shape.bits) {
    ctx.sink.add(
      make_error(
        CODES.bitfield_width,
        `el ancho ${bits} no cabe en «${type_display(type)}» (1–${shape.bits})`,
        span,
      ),
    );
  }
}

function is_trivial(ctx: CheckContext, type: PenguType, depth: number): boolean {
  if (depth > MAX_DEPTH) return false;
  switch (type.kind) {
    case "primitive":
      // `string` es `std::string`: tiene constructor y destructor.
      return type.name !== "string" && type.name !== "void";
    case "raw":
      return true;
    case "array":
      return is_trivial(ctx, type.element, depth + 1);
    case "tuple":
      return type.items.every((item) => is_trivial(ctx, item, depth + 1));
    case "optional":
      return is_trivial(ctx, type.inner, depth + 1);
    case "named": {
      const omen = ctx.module.env.omens.get(type.name);
      if (omen !== undefined) {
        return [...omen.variants.values()].every((variant) =>
          variant.payload.every((item) => is_trivial(ctx, item, depth + 1)),
        );
      }
      const rune = ctx.module.env.runes.get(type.name);
      if (rune !== undefined) {
        if (rune.constructor !== undefined || rune.meld === true) return false;
        return [...rune.fields.values()].every((field) => is_trivial(ctx, field.type, depth + 1));
      }
      return false;
    }
    default:
      return false;
  }
}
