// Backend de generación de código.
//
// `cpp` es el backend nativo (C++20) y el principal del proyecto; `js`
// emite ESM moderno (ES2022+) ejecutable en Bun, Node.js y el navegador.
// El valor por defecto es `cpp`: ningún comando cambia de backend si no se
// pide explícitamente.

export const TARGETS = ["cpp", "js"] as const;

export type Target = (typeof TARGETS)[number];

export const DEFAULT_TARGET: Target = "cpp";

export function is_target(value: string): value is Target {
  return (TARGETS as readonly string[]).includes(value);
}

// Resultado de leer `--target`: el valor canónico o el motivo del rechazo.
export type TargetChoice =
  | { readonly ok: true; readonly target: Target }
  | { readonly ok: false; readonly message: string };

export function parse_target(raw: string | undefined): TargetChoice {
  if (raw === undefined) return { ok: true, target: DEFAULT_TARGET };
  const normalized = raw.trim().toLowerCase();
  if (is_target(normalized)) return { ok: true, target: normalized };
  return {
    ok: false,
    message: `backend desconocido «${raw}»; los disponibles son ${TARGETS.join(" y ")}`,
  };
}

// Etiqueta legible del backend en mensajes de usuario.
export function target_label(target: Target): string {
  return target === "js" ? "JavaScript (ESM)" : "C++20";
}

// ¿El backend produce un artefacto ejecutable por el sistema operativo?
export function target_is_native(target: Target): boolean {
  return target === "cpp";
}
