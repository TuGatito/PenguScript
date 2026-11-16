//! Programas completos válidos: el checker debe aceptarlos sin diagnósticos.

use pengu_hir::lower_program;
use pengu_span::FileId;
use pengu_syntax::parse_program;
use pengu_types::check_crate;

fn clean(source: &str) {
    let parsed = parse_program(FileId::new(0), source);
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    assert!(lowered.diagnostics.is_empty(), "{:?}", lowered.diagnostics);
    let checked = check_crate(&lowered.krate);
    assert!(checked.is_clean(), "{:?}", checked.diagnostics);
}

#[test]
fn hello_world() {
    clean("grimoire\n    print(\"hola\")\n");
}

#[test]
fn records_and_match() {
    clean(
        "rune Point\n    x: Float\n    y: Float\n\n\
         length = (p: Point) -> Float\n    p.x\n\n\
         grimoire\n    bind p = Point(x: 1.0, y: 2.0)\n    bind l = length(p)\n    print(l)\n",
    );
}

#[test]
fn sum_and_exhaustive_match() {
    clean(
        "enchanting Shape\n    Circle(Float)\n    Point\n\n\
         area = (s: Shape) -> Float\n    match s\n        when Circle(r) then r * r\n        when Point then 0.0\n\n\
         grimoire\n    bind a = area(Circle(2.0))\n    print(a)\n",
    );
}

#[test]
fn generic_function() {
    clean(
        "identity = [T](value: T) -> T\n    value\n\n\
         grimoire\n    bind n = identity[Int](42)\n    print(n)\n",
    );
}

#[test]
fn option_question() {
    clean(
        "parse = (s: Str) -> Result[Int, Str]\n    if s == \"\" then\n        err(\"vacío\")\n    else\n        ok(1)\n\n\
         grimoire: Result[Unit, Str]\n    bind n = parse(\"x\")?\n    print(n)\n    ok(())\n",
    );
}

fn invalid(source: &str, expected: &str) {
    let parsed = parse_program(FileId::new(0), source);
    assert!(
        parsed.diagnostics.is_empty(),
        "parser: {:?}",
        parsed.diagnostics
    );
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    assert!(
        lowered.diagnostics.is_empty(),
        "hir: {:?}",
        lowered.diagnostics
    );
    let checked = check_crate(&lowered.krate);
    assert!(
        checked.diagnostics.iter().any(|d| d.code == expected),
        "faltó {expected}: {:?}",
        checked.diagnostics
    );
}

fn fragment(expr: &str, ty: &str) {
    clean(&format!("f = () -> {ty}\n    {expr}\n"));
}

#[test]
fn valid_collections_and_loops() {
    clean(
        "grimoire\n    bind xs = Vec[1, 2, 3]\n    morph total = 0\n    for x in xs\n        total = total + x\n    bind m = Map[\"a\": total]\n    print(m[\"a\"])\n",
    );
}

#[test]
fn valid_closure_and_method() {
    clean(
        "rune Counter\n    value: Int\n\nritual Counter\n    bump = (@mut) -> Unit\n        @.value = @.value + 1\n\ngrimoire\n    morph c = Counter(value: 0)\n    c.bump()\n    bind f = (x: Int) => x + c.value\n    print(f(2))\n",
    );
}

#[test]
fn valid_option_and_result() {
    clean(
        "f = (x: ?Int) -> Int\n    bind some(v) = x else\n        return 0\n    v\n\ngrimoire\n    print(f(some(3)))\n    print(f(none))\n",
    );
}

#[test]
fn invalid_type_mismatch() {
    invalid("grimoire\n    bind x: Int = \"no\"\n", "PGS-E3001");
}

#[test]
fn invalid_non_exhaustive_match() {
    invalid(
        "enchanting E\n    A\n    B\n\ngrimoire\n    bind e = A\n    match e\n        when A then 1\n",
        "PGS-E9001",
    );
}

#[test]
fn invalid_unconstrained_generic_call() {
    invalid(
        "pact P\n    p = (@) -> Int\n\ng = [T: P](x: T) -> Int\n    x.p()\n\ngrimoire\n    print(g(1))\n",
        "PGS-E1302",
    );
}

#[test]
fn fragment_arithmetic() {
    fragment("1 + 2 * 3", "Int");
}

#[test]
fn fragment_if_expression() {
    fragment("if true then 1 else 2", "Int");
}

#[test]
fn fragment_match_expression() {
    fragment(
        "match some(1)\n        when some(x) then x\n        when none then 0",
        "Int",
    );
}
