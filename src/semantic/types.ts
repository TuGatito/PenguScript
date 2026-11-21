// Representación interna de tipos del checker.
//
// Es independiente del AST: el AST describe lo que el usuario
// escribió y esta representación describe lo que el checker sabe.

export type PenguType =
  | PrimitiveType
  | NamedType
  | OptionalType
  | RefType
  | RawType
  | UniqueType
  | SharedType
  | WeakType
  | FunctionType
  | TupleType
  | ArrayType
  | RangeType
  | VoidType
  | AnyType
  | NoneType
  | NullptrType;

export interface PrimitiveType {
  readonly kind: "primitive";
  readonly name: string;
}

export interface NamedType {
  readonly kind: "named";
  readonly name: string;
  readonly args: readonly PenguType[];
}

export interface OptionalType {
  readonly kind: "optional";
  readonly inner: PenguType;
}

export interface RefType {
  readonly kind: "ref";
  readonly inner: PenguType;
  readonly mutable: boolean;
}

export interface RawType {
  readonly kind: "raw";
  readonly inner: PenguType;
}

export interface UniqueType {
  readonly kind: "unique";
  readonly inner: PenguType;
}

export interface SharedType {
  readonly kind: "shared";
  readonly inner: PenguType;
}

export interface WeakType {
  readonly kind: "weak";
  readonly inner: PenguType;
}

export interface FunctionType {
  readonly kind: "function";
  readonly params: readonly PenguType[];
  readonly result: PenguType;
  // Las funciones variádicas aceptan argumentos extra (`io::println`).
  readonly variadic: boolean;
  // Parámetros sin valor por defecto: la aridad mínima de la llamada.
  readonly required: number;
}

export interface TupleType {
  readonly kind: "tuple";
  readonly items: readonly PenguType[];
}

export interface ArrayType {
  readonly kind: "array";
  readonly element: PenguType;
  readonly size: number;
}

export interface RangeType {
  readonly kind: "range";
  readonly element: PenguType;
}

export interface VoidType {
  readonly kind: "void";
}

export interface AnyType {
  readonly kind: "any";
  readonly reason?: string;
}

export interface NoneType {
  readonly kind: "none";
}

export interface NullptrType {
  readonly kind: "nullptr";
}

export const INT: PrimitiveType = { kind: "primitive", name: "int" };
export const FLOAT: PrimitiveType = { kind: "primitive", name: "double" };
export const DOUBLE: PrimitiveType = FLOAT;
export const BOOL: PrimitiveType = { kind: "primitive", name: "bool" };
export const CHAR: PrimitiveType = { kind: "primitive", name: "char" };
export const STRING: PrimitiveType = { kind: "primitive", name: "string" };
export const SIZE_T: PrimitiveType = { kind: "primitive", name: "size_t" };
export const VOID: VoidType = { kind: "void" };
export const NONE: NoneType = { kind: "none" };
export const NULLPTR: NullptrType = { kind: "nullptr" };
export const UNKNOWN: AnyType = { kind: "any", reason: "unknown" };

export function primitive(name: string): PrimitiveType {
  return { kind: "primitive", name };
}

export function named(name: string, args: readonly PenguType[] = []): NamedType {
  return { kind: "named", name, args };
}

export function optional(inner: PenguType): OptionalType {
  return { kind: "optional", inner };
}

export function ref_to(inner: PenguType, mutable: boolean): RefType {
  return { kind: "ref", inner, mutable };
}

export function unique_type(inner: PenguType): UniqueType {
  return { kind: "unique", inner };
}

export function shared_type(inner: PenguType): SharedType {
  return { kind: "shared", inner };
}

export function weak_type(inner: PenguType): WeakType {
  return { kind: "weak", inner };
}

export function function_type(
  params: readonly PenguType[],
  result: PenguType,
  variadic = false,
  required = params.length,
): FunctionType {
  return { kind: "function", params, result, variadic, required };
}

export function tuple_type(items: readonly PenguType[]): TupleType {
  return { kind: "tuple", items };
}

export function any_type(reason: string): AnyType {
  return { kind: "any", reason };
}

const INTEGER_NAMES: ReadonlySet<string> = new Set([
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
  "int8_t",
  "int16_t",
  "int32_t",
  "int64_t",
  "uint8_t",
  "uint16_t",
  "uint32_t",
  "uint64_t",
  "size_t",
  "ptrdiff_t",
  "intptr_t",
  "uintptr_t",
  "byte",
]);

const FLOAT_NAMES: ReadonlySet<string> = new Set(["float", "double", "long double"]);

const STRING_NAMES: ReadonlySet<string> = new Set([
  "string",
  "wstring",
  "u8string",
  "u16string",
  "u32string",
  "string_view",
]);

export function is_any(type: PenguType): boolean {
  return type.kind === "any";
}

export function is_void(type: PenguType): boolean {
  return type.kind === "void";
}

export function is_integer(type: PenguType): boolean {
  if (type.kind === "primitive") return INTEGER_NAMES.has(type.name);
  return false;
}

export function is_float(type: PenguType): boolean {
  if (type.kind === "primitive") return FLOAT_NAMES.has(type.name);
  return false;
}

export function is_string(type: PenguType): boolean {
  if (type.kind === "primitive") return STRING_NAMES.has(type.name);
  return false;
}

export function is_numeric(type: PenguType): boolean {
  return is_integer(type) || is_float(type);
}

// Anchos del modelo portable del lenguaje. `long` y los tipos de
// tamaño fijo son de 64 bits en LP64 (lo que asume el proyecto).
export interface IntegerShape {
  readonly bits: number;
  readonly signed: boolean;
}

export const INTEGER_SHAPES: Readonly<Record<string, IntegerShape>> = {
  bool: { bits: 8, signed: false },
  char: { bits: 8, signed: true },
  "signed char": { bits: 8, signed: true },
  "unsigned char": { bits: 8, signed: false },
  byte: { bits: 8, signed: false },
  short: { bits: 16, signed: true },
  "unsigned short": { bits: 16, signed: false },
  int: { bits: 32, signed: true },
  "unsigned int": { bits: 32, signed: false },
  long: { bits: 64, signed: true },
  "unsigned long": { bits: 64, signed: false },
  "long long": { bits: 64, signed: true },
  "unsigned long long": { bits: 64, signed: false },
  int8_t: { bits: 8, signed: true },
  uint8_t: { bits: 8, signed: false },
  int16_t: { bits: 16, signed: true },
  uint16_t: { bits: 16, signed: false },
  int32_t: { bits: 32, signed: true },
  uint32_t: { bits: 32, signed: false },
  int64_t: { bits: 64, signed: true },
  uint64_t: { bits: 64, signed: false },
  size_t: { bits: 64, signed: false },
  ptrdiff_t: { bits: 64, signed: true },
  intptr_t: { bits: 64, signed: true },
  uintptr_t: { bits: 64, signed: false },
  wchar_t: { bits: 32, signed: true },
};

export const FLOAT_RANKS: Readonly<Record<string, number>> = {
  float: 1,
  double: 2,
  "long double": 3,
};

export function integer_shape(type: PenguType): IntegerShape | undefined {
  if (type.kind !== "primitive") return undefined;
  return INTEGER_SHAPES[type.name];
}

export function float_rank(type: PenguType): number | undefined {
  if (type.kind !== "primitive") return undefined;
  return FLOAT_RANKS[type.name];
}

// Nombre del tipo entero que C++ produciría tras la promoción.
function promoted_integer_name(bits: number, signed: boolean): string {
  if (bits <= 16) return "int";
  if (bits === 32) return signed ? "int" : "unsigned int";
  return signed ? "long" : "unsigned long";
}

// Tipo resultado de una operación aritmética. `undefined` cuando hay
// que convertir de forma explícita (mismo ancho, signo distinto).
export function numeric_join(a: PenguType, b: PenguType): PenguType | undefined {
  const a_float = float_rank(a);
  const b_float = float_rank(b);
  if (a_float !== undefined || b_float !== undefined) {
    const rank = Math.max(a_float ?? 0, b_float ?? 0);
    const name = rank === 3 ? "long double" : rank === 2 ? "double" : "float";
    return primitive(name);
  }

  const a_int = integer_shape(a);
  const b_int = integer_shape(b);
  if (a_int === undefined || b_int === undefined) return undefined;
  if (a_int.bits === b_int.bits && a_int.signed !== b_int.signed) return undefined;

  const bits = Math.max(a_int.bits, b_int.bits);
  const signed = bits === a_int.bits ? a_int.signed : b_int.signed;
  return primitive(promoted_integer_name(bits, signed));
}

export function is_name(type: PenguType, name: string): boolean {
  return type.kind === "primitive" && type.name === name;
}

// Igualdad estructural. `any` es compatible con todo y nunca se
// considera distinto: evita errores en cascada.
export function type_equals(a: PenguType, b: PenguType): boolean {
  if (a.kind === "any" || b.kind === "any") return true;
  if (a.kind !== b.kind) return false;

  switch (a.kind) {
    case "primitive":
      return a.name === (b as PrimitiveType).name;
    case "named": {
      const other = b as NamedType;
      return a.name === other.name && types_equal(a.args, other.args);
    }
    case "optional":
      return type_equals(a.inner, (b as OptionalType).inner);
    case "ref": {
      const other = b as RefType;
      return a.mutable === other.mutable && type_equals(a.inner, other.inner);
    }
    case "raw":
      return type_equals(a.inner, (b as RawType).inner);
    case "unique":
      return type_equals(a.inner, (b as UniqueType).inner);
    case "shared":
      return type_equals(a.inner, (b as SharedType).inner);
    case "weak":
      return type_equals(a.inner, (b as WeakType).inner);
    case "function": {
      const other = b as FunctionType;
      return (
        a.variadic === other.variadic &&
        types_equal(a.params, other.params) &&
        type_equals(a.result, other.result)
      );
    }
    case "tuple":
      return types_equal(a.items, (b as TupleType).items);
    case "array": {
      const other = b as ArrayType;
      return a.size === other.size && type_equals(a.element, other.element);
    }
    case "range":
      return type_equals(a.element, (b as RangeType).element);
    default:
      return true;
  }
}

export function types_equal(a: readonly PenguType[], b: readonly PenguType[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((item, index) => type_equals(item, b[index] as PenguType));
}

// Tipo común de dos ramas: `int` y `double` se promocionan, dos
// tipos iguales se conservan y lo demás deja de ser común.
export function join_types(a: PenguType, b: PenguType): PenguType | undefined {
  if (a.kind === "any") return b;
  if (b.kind === "any") return a;
  if (type_equals(a, b)) return a;
  if (a.kind === "none") return optional(b);
  if (b.kind === "none") return optional(a);
  if (a.kind === "optional" && type_equals(a.inner, b)) return a;
  if (b.kind === "optional" && type_equals(b.inner, a)) return b;
  if (a.kind === "optional" && b.kind === "optional") {
    const inner = join_types(a.inner, b.inner);
    return inner ? optional(inner) : undefined;
  }
  if (is_numeric(a) && is_numeric(b)) {
    return numeric_join(a, b);
  }
  return undefined;
}

export function type_display(type: PenguType): string {
  switch (type.kind) {
    case "primitive":
      return type.name;
    case "named":
      return type.args.length === 0
        ? type.name
        : `${type.name}<${type.args.map(type_display).join(", ")}>`;
    case "optional":
      return `${type_display(type.inner)}?`;
    case "ref":
      return `${type.mutable ? "mut " : ""}ref<${type_display(type.inner)}>`;
    case "raw":
      return `raw<${type_display(type.inner)}>`;
    case "unique":
      return `unique<${type_display(type.inner)}>`;
    case "shared":
      return `shared<${type_display(type.inner)}>`;
    case "weak":
      return `weak<${type_display(type.inner)}>`;
    case "function": {
      const parts = type.variadic ? type.params.slice(0, -1) : type.params;
      const items = parts.map(type_display);
      if (type.variadic) {
        const element = type.params[type.params.length - 1];
        items.push(`...${element === undefined ? "any" : type_display(element)}`);
      }
      return `function<(${items.join(", ")}) -> ${type_display(type.result)}>`;
    }
    case "tuple":
      return `(${type.items.map(type_display).join(", ")})`;
    case "array":
      return `array<${type_display(type.element)}, ${type.size}>`;
    case "range":
      return `range<${type_display(type.element)}>`;
    case "void":
      return "void";
    case "any":
      return type.reason ?? "any";
    case "none":
      return "none";
    case "nullptr":
      return "nullptr";
  }
}
