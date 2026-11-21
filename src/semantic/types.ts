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
): FunctionType {
  return { kind: "function", params, result, variadic };
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
      return types_equal(a.params, other.params) && type_equals(a.result, other.result);
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
    return is_float(a) || is_float(b) ? FLOAT : a;
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
      const params = type.params.map(type_display).join(", ");
      const dots = type.variadic ? (params.length > 0 ? ", ..." : "...") : "";
      return `function<(${params}${dots}) -> ${type_display(type.result)}>`;
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
