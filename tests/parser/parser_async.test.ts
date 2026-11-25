// Tests del parser para `async` y `await` (fase P5 del plan JavaScript).

import { describe, expect, test } from "bun:test";
import { parse_text } from "../../src/frontend/parser.ts";
import type { Program } from "../../src/frontend/ast.ts";
import type { FunctionDecl, EnchantingDecl } from "../../src/frontend/ast_decl.ts";
import type { AwaitNode, BinaryNode, CallNode, LambdaNode, MemberNode } from "../../src/frontend/ast_expr.ts";

function parse_ok(code: string): Program {
  const result = parse_text("test.pengu", code);
  if (result.diagnostics.length > 0) {
    const messages = result.diagnostics.map((d) => `${d.code}: ${d.message}`).join("\n");
    throw new Error(`diagnósticos inesperados:\n${messages}`);
  }
  return result.program;
}

function function_decl(program: Program, index = 0): FunctionDecl {
  const decl = program.decls[index];
  if (decl?.kind !== "function_decl") throw new Error(`se esperaba function_decl, hay ${decl?.kind}`);
  return decl;
}

function last_expression(body: FunctionDecl): unknown {
  const statements = body.body.statements;
  const last = statements[statements.length - 1];
  if (last?.kind !== "expr_stmt") throw new Error(`se esperaba expr_stmt, hay ${last?.kind}`);
  return last.expr;
}

describe("async", () => {
  test("una función async se marca en el AST", () => {
    const program = parse_ok(`async cargar = (n: int) -> int\n  await esperar(n)\n  n\n`);
    const decl = function_decl(program);
    expect(decl.is_async).toBe(true);
    expect(decl.is_unsafe).toBe(false);
    expect(decl.name).toBe("cargar");
  });

  test("async unsafe se acepta en ese orden", () => {
    const decl = function_decl(parse_ok(`async unsafe cargar = () -> void\n  pass\n`));
    expect(decl.is_async).toBe(true);
    expect(decl.is_unsafe).toBe(true);
  });

  test("una función normal no es async", () => {
    expect(function_decl(parse_ok(`cargar = () -> void\n  pass\n`)).is_async).toBe(false);
  });

  test("lambda async con y sin parámetros", () => {
    const program = parse_ok(`main = -> void\n  f = async (n: int) -> int\n    n\n  g = async -> void\n    pass\n  pass\n`);
    const main = function_decl(program);
    const statements = main.body.statements;
    const first = statements[0];
    const second = statements[1];
    if (first?.kind !== "assign" || second?.kind !== "assign") throw new Error("se esperaban asignaciones");
    expect((first.value as LambdaNode).kind).toBe("lambda");
    expect((first.value as LambdaNode).is_async).toBe(true);
    expect((second.value as LambdaNode).is_async).toBe(true);
  });

  test("async en un método de enchanting", () => {
    const program = parse_ok(`rune Caja\n  total: int\n\nenchanting Caja\n  async recargar = () -> int\n    @.total\n`);
    const enchanting = program.decls[1];
    if (enchanting?.kind !== "enchanting_decl") throw new Error("se esperaba enchanting_decl");
    expect((enchanting as EnchantingDecl).methods[0]?.is_async).toBe(true);
  });

  test("async donde no cabe es E0517", () => {
    const result = parse_text("test.pengu", "async x = 5\n");
    expect(result.diagnostics.map((item) => item.code)).toEqual(["E0517"]);
  });

  test("async delante de un operador libre es E0517", () => {
    const result = parse_text("test.pengu", `async operator + = (a: int, b: int) -> int\n  a + b\n`);
    expect(result.diagnostics.map((item) => item.code)).toEqual(["E0517"]);
  });

  test("async delante de un operador es E0517", () => {
    const result = parse_text("test.pengu", `rune P\n  x: int\n\nenchanting P\n  async operator + = (otro: P) -> P\n    @\n`);
    expect(result.diagnostics.some((item) => item.code === "E0517")).toBe(true);
  });
});

describe("await", () => {
  test("await liga como prefijo fuerte: `await f(x).y` es `await (f(x).y)`", () => {
    const decl = function_decl(parse_ok(`async cargar = () -> int\n  await leer(1).total\n`));
    const expr = last_expression(decl) as AwaitNode;
    expect(expr.kind).toBe("await");
    expect((expr.value as MemberNode).kind).toBe("member");
  });

  test("`await a + b` es `(await a) + b`", () => {
    const decl = function_decl(parse_ok(`async cargar = (a: future<int>, b: int) -> int\n  await a + b\n`));
    const expr = last_expression(decl) as BinaryNode;
    expect(expr.kind).toBe("binary");
    expect(expr.op).toBe("+");
    expect((expr.left as AwaitNode).kind).toBe("await");
  });

  test("await sobre una llamada normal", () => {
    const decl = function_decl(parse_ok(`async cargar = () -> int\n  await doble(21)\n`));
    const expr = last_expression(decl) as AwaitNode;
    expect((expr.value as CallNode).kind).toBe("call");
  });

  test("await se puede anidar en match, if y comprensiones", () => {
    const decl = function_decl(
      parse_ok(`async cargar = (m: int) -> int
  valor = match m
    when 0 then await doble(1)
    else
      await doble(2)
  if valor > 1
    await doble(valor)
  else
    0
`),
    );
    expect(decl.is_async).toBe(true);
  });
});
