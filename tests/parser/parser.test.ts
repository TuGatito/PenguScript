// Tests del parser: un caso por construcción del lenguaje.

import { describe, expect, test } from "bun:test";
import { parse_text } from "../../src/frontend/parser.ts";
import type { Program } from "../../src/frontend/ast.ts";
import type { FunctionDecl, RuneDecl, EnchantingDecl } from "../../src/frontend/ast_decl.ts";

function parse_ok(code: string): Program {
  const result = parse_text("test.pengu", code);
  if (result.diagnostics.length > 0) {
    const messages = result.diagnostics.map((d) => `${d.code}: ${d.message}`).join("\n");
    throw new Error(`diagnósticos inesperados:\n${messages}`);
  }
  return result.program;
}

function first_function(program: Program): FunctionDecl {
  const decl = program.decls[0];
  if (decl?.kind !== "function_decl") throw new Error(`se esperaba function_decl, hay ${decl?.kind}`);
  return decl;
}

describe("declaraciones", () => {
  test("invoke simple y selectivo", () => {
    const program = parse_ok(`invoke "std/io"\ninvoke {sqrt, pow} from "std/math" as m\n`);
    expect(program.decls.map((d) => d.kind)).toEqual(["invoke_decl", "invoke_decl"]);
    const selective = program.decls[1] as { items?: readonly { name: string }[]; alias?: string };
    expect(selective.items?.map((item) => item.name)).toEqual(["sqrt", "pow"]);
    expect(selective.alias).toBe("m");
  });

  test("bloque declare de funciones intrínsecas", () => {
    const program = parse_ok(`realm fs
declare
  read_to_string = (path: string) -> string?
  exists = (path: string) -> bool
  now_millis = -> int
`);
    expect(program.decls.map((d) => d.kind)).toEqual(["realm_decl", "intrinsic_decl"]);
    const group = program.decls[1] as { declares: readonly { name: string }[] };
    expect(group.declares.map((d) => d.name)).toEqual(["read_to_string", "exists", "now_millis"]);
  });

  test("realm, echo y seal", () => {
    const program = parse_ok(`realm geometria\necho Entity = int\nseal UserId = int\n`);
    expect(program.decls.map((d) => d.kind)).toEqual(["realm_decl", "echo_decl", "seal_decl"]);
  });

  test("constante y función con tipo de retorno", () => {
    const program = parse_ok(`const LIMITE = 10\nadd = (a: int, b: int) -> int\n    return a + b\n`);
    expect(program.decls[0]?.kind).toBe("const_decl");
    const fn = first_function({ ...program, decls: [program.decls[1]!] });
    expect(fn.name).toBe("add");
    expect(fn.params.map((p) => p.name)).toEqual(["a", "b"]);
    expect(fn.result?.kind).toBe("primitive_type");
  });

  test("función sin parámetros con cuerpo de bloque", () => {
    const fn = first_function(parse_ok(`main = ->\n    x = 1\n    x + 1\n`));
    expect(fn.params).toHaveLength(0);
    expect(fn.result).toBeUndefined();
    expect(fn.body.statements).toHaveLength(2);
  });

  test("parámetros por defecto y sigilos con needs", () => {
    const program = parse_ok(`buscar = <T needs Ord, Copy>(items: ref<vector<T>>, x: T = items[0]) -> T?\n    none\n`);
    const fn = program.decls[0] as FunctionDecl;
    expect(fn.sigils).toEqual(["T"]);
    expect(fn.needs).toEqual(["Ord", "Copy"]);
    expect(fn.params[0]?.type?.kind).toBe("ref_type");
    expect(fn.params[1]?.default_value?.kind).toBe("index");
    expect(fn.result?.kind).toBe("optional_type");
  });

  test("unsafe en la firma", () => {
    const program = parse_ok(`unsafe write_u8 = (p: raw<uint8_t>, v: uint8_t) -> void\n    pass\n`);
    expect((program.decls[0] as FunctionDecl).is_unsafe).toBe(true);
  });
});

describe("runes y enchanting", () => {
  test("campos, constructor y destructor", () => {
    const program = parse_ok(`rune Animal
  name: string
  edad: int = 0
  constructor(name: string)
    @name = name
  destructor
    pass
`);
    const rune = program.decls[0] as RuneDecl;
    expect(rune.fields.map((f) => f.name)).toEqual(["name", "edad"]);
    expect(rune.fields[1]?.default_value?.kind).toBe("int_lit");
    expect(rune.constructor?.params).toHaveLength(1);
    expect(rune.destructor?.statements).toHaveLength(1);
  });

  test("herencia con heir", () => {
    const rune = parse_ok(`rune Dog heir Animal\n  raza: string\n`).decls[0] as RuneDecl;
    expect(rune.parent).toBe("Animal");
  });

  test("métodos, mut y operadores", () => {
    const program = parse_ok(`rune Point
  x: double
  y: double
enchanting Point
  len = -> double
    @x
  mut translate = (dx: double, dy: double) -> void
    @x += dx
  operator + = (other: Point) -> Point
    Point(@x, @y)
  operator [] = (i: size_t) -> ref<double>
    @x
  operator () = -> double
    @x
`);
    const ench = program.decls[1] as EnchantingDecl;
    expect(ench.target).toBe("Point");
    expect(ench.methods.map((m) => m.name)).toEqual(["len", "translate", "operator", "operator", "operator"]);
    expect(ench.methods[1]?.mutable).toBe(true);
    expect(ench.methods[2]?.operator).toBe("+");
    expect(ench.methods[3]?.operator).toBe("[]");
    expect(ench.methods[4]?.operator).toBe("()");
  });
});

describe("omens", () => {
  test("omen unitario con valores", () => {
    const omen = parse_ok(`omen Color: uint8_t\n  Red\n  Green = 5\n  Blue\n`).decls[0] as {
      variants: readonly { name: string }[];
      underlying?: { kind: string };
      is_flags: boolean;
    };
    expect(omen.variants.map((v) => v.name)).toEqual(["Red", "Green", "Blue"]);
    expect(omen.underlying?.kind).toBe("primitive_type");
    expect(omen.is_flags).toBe(false);
  });

  test("flags omen y omen algebraico", () => {
    const program = parse_ok(`flags omen Permission
  Read
  Write
omen Shape
  Circle(double)
  Rect(double, double)
`);
    expect((program.decls[0] as { is_flags: boolean }).is_flags).toBe(true);
    const shape = program.decls[1] as { variants: readonly { payload: readonly unknown[] }[] };
    expect(shape.variants[0]?.payload).toHaveLength(1);
    expect(shape.variants[1]?.payload).toHaveLength(2);
  });
});

describe("control de flujo", () => {
  test("if inline con then y else if", () => {
    const fn = first_function(parse_ok(`signo = (x: int) -> string
    if x > 0 then "positivo" else if x < 0 then "negativo" else "cero"
`));
    const expr = fn.body.statements[0];
    expect(expr?.kind).toBe("expr_stmt");
    if (expr?.kind !== "expr_stmt") return;
    expect(expr.expr.kind).toBe("if");
  });

  test("unless y switch con patrones múltiples", () => {
    const fn = first_function(parse_ok(`f = (x: int) -> string
    unless x == 0
      pass
    switch x
      when 200, 201 then "ok"
      when 500 then "error"
      else "raro"
`));
    expect(fn.body.statements).toHaveLength(2);
    const sw = fn.body.statements[1];
    if (sw?.kind !== "expr_stmt" || sw.expr.kind !== "switch") throw new Error("se esperaba switch");
    expect(sw.expr.arms[0]?.patterns).toHaveLength(2);
    expect(sw.expr.else_block).toBeDefined();
  });

  test("match con payload y guard", () => {
    const fn = first_function(parse_ok(`area = (s: Shape) -> double
    match s
      when Circle(r) then 3.14 * r * r
      when Rect(w, h) if w > 0.0 then w * h
      when Rect(_, _) then 0.0
`));
    const stmt = fn.body.statements[0];
    if (stmt?.kind !== "expr_stmt" || stmt.expr.kind !== "match") throw new Error("se esperaba match");
    expect(stmt.expr.arms).toHaveLength(3);
    const guarded = stmt.expr.arms[1];
    expect(guarded?.guard?.kind).toBe("binary");
  });

  test("bucles: for numérico, for iterable, repeat y else", () => {
    const fn = first_function(parse_ok(`f = (items: vector<int>) -> int
    for i = 0, 10, 2
      continue
    for i, mut x in items
      x += i
    else
      pass
    repeat
      pass
    until true
    0
`));
    expect(fn.body.statements).toHaveLength(4);
    const numeric = fn.body.statements[0];
    if (numeric?.kind !== "expr_stmt" || numeric.expr.kind !== "for_numeric") {
      throw new Error("se esperaba for_numeric");
    }
    expect(numeric.expr.step?.kind).toBe("int_lit");
    const iter = fn.body.statements[1];
    if (iter?.kind !== "expr_stmt" || iter.expr.kind !== "for_iter") throw new Error("se esperaba for_iter");
    expect(iter.expr.variables).toHaveLength(2);
    expect(iter.expr.else_block).toBeDefined();
  });

  test("break con valor y do", () => {
    const fn = first_function(parse_ok(`f = -> int?
    do
      while true
        break 42
`));
    expect(fn.body.statements[0]?.kind).toBe("expr_stmt");
  });
});

describe("expresiones", () => {
  test("llamadas, miembros, índice y llamada sin paréntesis", () => {
    const fn = first_function(parse_ok(`f = -> int
    println!("hola")
    Point(1.0, 2.0).len()
    xs[0]
`));
    const calls = fn.body.statements.map((s) => (s.kind === "expr_stmt" ? s.expr.kind : ""));
    expect(calls).toEqual(["call", "call", "index"]);
  });

  test("comprehensions de vector, mapa y set", () => {
    const fn = first_function(parse_ok(`f = ->
    xs = [x * x for x in 1..10 if x % 2 == 0]
    m = {x: x for x in xs}
    s = set{x for x in xs}
`));
    const kinds = fn.body.statements.map((s) =>
      s.kind === "assign" ? s.value.kind : s.kind,
    );
    expect(kinds).toEqual(["comprehension", "comprehension", "comprehension"]);
  });

  test("interpolación de strings", () => {
    const fn = first_function(parse_ok(`f = -> string
    "hola #{nombre} y #{1 + 2}"
`));
    const stmt = fn.body.statements[0];
    if (stmt?.kind !== "expr_stmt" || stmt.expr.kind !== "string_lit") throw new Error("se esperaba string_lit");
    expect(stmt.expr.parts.map((p) => p.kind)).toEqual(["text_part", "expr_part", "text_part", "expr_part"]);
  });

  test("rangos, casts y llamada con sigilos", () => {
    const fn = first_function(parse_ok(`f = ->
    a = 1..10
    b = 1..<10
    c = x as double
    d = max<int>(1, 2)
`));
    const values = fn.body.statements.map((s) => (s.kind === "assign" ? s.value : undefined));
    expect(values[0]?.kind).toBe("range");
    expect(values[1]?.kind).toBe("range");
    expect(values[2]?.kind).toBe("cast");
    expect(values[3]?.kind).toBe("call");
  });
});

describe("errores", () => {
  test("falta la flecha en una función", () => {
    const result = parse_text("test.pengu", `f = (x: int) int\n    x\n`);
    expect(result.diagnostics.length).toBeGreaterThan(0);
  });

  test("bloque sin indentar", () => {
    const result = parse_text("test.pengu", `f = ->\nx\n`);
    expect(result.diagnostics.some((d) => d.code === "E0205")).toBe(true);
  });

  test("declaración desconocida", () => {
    const result = parse_text("test.pengu", `???\n`);
    expect(result.diagnostics.length).toBeGreaterThan(0);
  });
});
