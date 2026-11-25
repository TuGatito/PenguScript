// Normalización de las opciones de enlace.
//
// `pengu build --link raylib` significa «enlaza con la biblioteca raylib»,
// así que un nombre suelto se convierte en `-lraylib`. Una ruta, un objeto
// o una bandera que ya empieza por `-` se dejan tal cual.

export function link_flag(value: string): string {
  const trimmed = value.trim();
  if (trimmed.length === 0) return trimmed;
  if (trimmed.startsWith("-")) return trimmed;
  if (trimmed.includes("/") || trimmed.includes("\\")) return trimmed;
  if (/\.(o|a|so|dylib|dll|lib)$/i.test(trimmed)) return trimmed;
  return `-l${trimmed}`;
}

export function link_flags(values: readonly string[]): string[] {
  const result: string[] = [];
  for (const value of values) {
    const normalized = link_flag(value);
    if (normalized.length > 0 && !result.includes(normalized)) result.push(normalized);
  }
  return result;
}
