// Traducción de tipos de C/C++ a tipos de PenguScript.

const DIRECT: Readonly<Record<string, string>> = {
  void: "void",
  bool: "bool",
  char: "char",
  "signed char": "int8_t",
  "unsigned char": "uint8_t",
  short: "short",
  "unsigned short": "unsigned short",
  int: "int",
  "unsigned int": "unsigned int",
  long: "long",
  "unsigned long": "unsigned long",
  "long long": "long long",
  "unsigned long long": "unsigned long long",
  float: "float",
  double: "double",
  "long double": "long double",
  size_t: "size_t",
  "std::size_t": "size_t",
  int8_t: "int8_t",
  int16_t: "int16_t",
  int32_t: "int32_t",
  int64_t: "int64_t",
  uint8_t: "uint8_t",
  uint16_t: "uint16_t",
  uint32_t: "uint32_t",
  uint64_t: "uint64_t",
  "std::int8_t": "int8_t",
  "std::int16_t": "int16_t",
  "std::int32_t": "int32_t",
  "std::int64_t": "int64_t",
  "std::uint8_t": "uint8_t",
  "std::uint16_t": "uint16_t",
  "std::uint32_t": "uint32_t",
  "std::uint64_t": "uint64_t",
};

export interface MappedType {
  readonly pengu: string;
  readonly ok: boolean;
}

// `const char *` se convierte en `string`; el resto de punteros, en
// `raw<T>`, que exige `unsafe` en el código PenguScript.
export function map_c_type(qual_type: string): MappedType {
  const cleaned = qual_type
    .replace(/\bconst\b/g, "")
    .replace(/\bvolatile\b/g, "")
    .replace(/\brestrict\b/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^struct\s+/, "")
    .replace(/^class\s+/, "");

  const without_ref = cleaned.replace(/[&]+$/, "").trim();
  const direct = DIRECT[without_ref];
  if (direct !== undefined) return { pengu: direct, ok: true };

  const pointer = /^(.*?)\s*\*+$/.exec(without_ref);
  if (pointer !== null) {
    const inner = (pointer[1] ?? "").trim();
    if (inner === "char") return { pengu: "string", ok: true };
    const mapped_inner = DIRECT[inner];
    if (mapped_inner !== undefined) return { pengu: `raw<${mapped_inner}>`, ok: true };
    return { pengu: "raw<void>", ok: true };
  }

  return { pengu: "int", ok: false };
}

export function is_supported(qual_type: string): boolean {
  return map_c_type(qual_type).ok;
}
