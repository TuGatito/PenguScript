use std::process::Command;

use pengu_codegen::generate;
use pengu_diag::Diagnostic;
use pengu_hir::lower_program;
use pengu_lir::lower_crate;
use pengu_span::{DUMMY_SPAN, FileId};
use pengu_syntax::parse_program;
use pengu_types::check_crate;

fn generate_source(source: &str) -> String {
    let parsed = parse_program(FileId::new(0), source);
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    assert!(lowered.diagnostics.is_empty(), "{:?}", lowered.diagnostics);
    let types = check_crate(&lowered.krate);
    assert!(types.is_clean(), "{:?}", types.diagnostics);
    let lir = lower_crate(&lowered.krate, &types);
    assert!(lir.diagnostics.is_empty(), "{:?}", lir.diagnostics);
    let generated = generate(&lowered.krate, &lir);
    assert!(
        generated.diagnostics.is_empty(),
        "{:?}",
        generated.diagnostics
    );
    generated.source
}

fn compile(_source: &str, rust: &str) {
    let stamp = format!(
        "{}_{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    );
    let dir = std::env::temp_dir().join(format!("pengu-codegen-{stamp}"));
    std::fs::create_dir_all(&dir).unwrap();
    let file = dir.join("lib.rs");
    std::fs::write(&file, rust).unwrap();
    let output = Command::new("rustc")
        .args(["--edition", "2024", "--crate-type", "lib"])
        .arg(&file)
        .arg("-o")
        .arg(dir.join("lib.rlib"))
        .output()
        .expect("rustc");
    if !output.status.success() {
        panic!(
            "rustc falló\n--- generated ---\n{rust}\n--- stderr ---\n{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
    let _ = std::fs::remove_dir_all(dir);
}

fn run_source(source: &str) -> String {
    let rust = generate_source(source);
    let stamp = format!(
        "{}_{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    );
    let dir = std::env::temp_dir().join(format!("pengu-codegen-run-{stamp}"));
    std::fs::create_dir_all(&dir).unwrap();
    let file = dir.join("main.rs");
    std::fs::write(&file, &rust).unwrap();
    let exe = dir.join("main");
    let output = Command::new("rustc")
        .args(["--edition", "2024"])
        .arg(&file)
        .arg("-o")
        .arg(&exe)
        .output()
        .expect("rustc");
    if !output.status.success() {
        panic!(
            "rustc falló\n--- generated ---\n{rust}\n--- stderr ---\n{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
    let output = Command::new(&exe).output().expect("run");
    if !output.status.success() {
        panic!(
            "programa falló\n--- generated ---\n{rust}\n--- stderr ---\n{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
    let stdout = String::from_utf8(output.stdout).unwrap();
    let _ = std::fs::remove_dir_all(dir);
    stdout
}

#[test]
fn emits_record_and_function() {
    let source = "rune Point\n    x: Int\n    y: Int\n\nadd = (a: Int, b: Int) -> Int\n    a + b\n";
    let rust = generate_source(source);
    assert!(rust.contains("struct Point"), "{rust}");
    assert!(rust.contains("fn add"), "{rust}");
    compile(source, &rust);
}

#[test]
fn emits_enum_and_alias() {
    let source = "enchanting Shape\n    Circle(Float)\n    Empty\n\nessence Meter = Int\n";
    let rust = generate_source(source);
    assert!(rust.contains("enum Shape"), "{rust}");
    assert!(rust.contains("type Meter = i32;"), "{rust}");
    compile(source, &rust);
}

#[test]
fn emits_impl_and_const() {
    let source = r#"
rune Counter
    value: Int

sigil LIMIT: Int = 10

ritual Counter
    one = (@) -> Int
        1
"#;
    let generated = generate_source(source);
    assert!(generated.contains("impl crate::Counter"), "{generated}");
    assert!(generated.contains("const LIMIT: i32 = 10;"), "{generated}");
    compile(source, &generated);
}

#[test]
fn emits_foreign_block() {
    let source = "foreign \"C\"\n    abs = (x: Int) -> Int\n";
    let rust = generate_source(source);
    assert!(rust.contains("unsafe extern \"C\""), "{rust}");
    assert!(rust.contains("pub fn abs"), "{rust}");
    compile(source, &rust);
}

#[test]
fn emits_nested_modules() {
    let source =
        "scroll geometry\n    rune Point\n        x: Int\n\n    zero = () -> Int\n        0\n";
    let rust = generate_source(source);
    assert!(rust.contains("mod geometry {"), "{rust}");
    assert!(rust.contains("struct Point"), "{rust}");
    compile(source, &rust);
}

#[test]
fn emits_tests_and_grimoire() {
    let source = r#"
@@test
checks = () -> Unit
    return

@@test(should_panic: "boom")
panics = () -> Unit
    return

grimoire
    bind x = 1
"#;
    let rust = generate_source(source);
    assert!(rust.contains("#[test]"), "{rust}");
    assert!(
        rust.contains("#[should_panic(expected = \"boom\")]"),
        "{rust}"
    );
    assert!(rust.contains("fn main()"), "{rust}");
    compile(source, &rust);
}

#[test]
fn emits_unsafe_curse_function() {
    let source = "-- SAFETY: llamada auditada\nforeign \"C\"\n    abs = (x: Int) -> Int\n\ncurse danger = (x: Int) -> Int\n    abs(x)\n";
    let rust = generate_source(source);
    assert!(rust.contains("unsafe fn danger"), "{rust}");
    compile(source, &rust);
}

#[test]
fn reports_lir_errors_instead_of_emitting_broken_rust() {
    let source = "get = () -> Int\n    1\n";
    let parsed = parse_program(FileId::new(0), source);
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    assert!(lowered.diagnostics.is_empty(), "{:?}", lowered.diagnostics);
    let types = check_crate(&lowered.krate);
    assert!(types.is_clean(), "{:?}", types.diagnostics);
    let mut lir = lower_crate(&lowered.krate, &types);
    lir.diagnostics.push(Diagnostic::error(
        "PGS-E1901",
        "error de LIR simulado",
        DUMMY_SPAN,
    ));
    let generated = generate(&lowered.krate, &lir);
    assert!(generated.source.is_empty(), "{}", generated.source);
    assert!(generated.diagnostics.iter().any(|d| d.is_error()));
}

#[test]
fn qualifies_cross_module_types_and_calls() {
    let source = r#"
scroll geometry
    unveil rune Point
        x: Int

    unveil zero = () -> Int
        0

rune Holder
    point: geometry::Point

call = () -> Int
    geometry::zero()
"#;
    let rust = generate_source(source);
    assert!(rust.contains("crate::geometry::Point"), "{rust}");
    assert!(rust.contains("crate::geometry::zero()"), "{rust}");
    compile(source, &rust);
}

#[test]
fn emits_pact_default_method_body() {
    let source = r#"
pact Named
    name = (@) -> Str
        return "pengu"
"#;
    let rust = generate_source(source);
    assert!(rust.contains("trait Named"), "{rust}");
    assert!(rust.contains("fn name(&self) -> &str {"), "{rust}");
    compile(source, &rust);
}

#[test]
fn executes_records_fields_arrays_and_calls() {
    let source = r#"
rune Point
    x: Int
    y: Int

sum = (p: Point) -> Int
    p.x + p.y

first = (xs: Vec[Int]) -> Int
    xs[0]

as_float = (x: Int) -> Float
    x as Float

grimoire
    bind p = Point(x: 1, y: 2)
    print(sum(p))
    print(first(Vec[10, 20]))
    print(as_float(2))
"#;
    let stdout = run_source(source);
    assert_eq!(stdout, "3\n10\n2\n");
}

#[test]
fn locals_use_ssa_state_without_hidden_expect() {
    let source = r#"
grimoire
    bind a = format("pengu")
    bind b = a
    print(b)
"#;
    let rust = generate_source(source);
    assert!(!rust.contains("local no inicializado"), "{rust}");
    assert!(!rust.contains("local ya movido"), "{rust}");
    // El runtime y los módulos de `std` usan `Option` en sus firmas (`checked_*`,
    // `walk_depth`), así que solo se vigila el código del programa de usuario:
    // los locales no deben bajarse a `Option` + `expect`.
    let user_part = rust.split("pub mod std {").next().unwrap_or(&rust);
    assert!(!user_part.contains("__l0: Option<"), "{rust}");
    compile(source, &rust);
}

#[test]
fn compiles_try_and_record_update() {
    let source = r#"
rune Point
    x: Int
    y: Int

bump = (value: ?Int) -> ?Int
    bind v = value?
    some(v + 1)

shift = (p: Point) -> Point
    Point(y: 5, ..p)
"#;
    let rust = generate_source(source);
    assert!(rust.contains(")?"), "{rust}");
    assert!(rust.contains("..__l0"), "{rust}");
    compile(source, &rust);
}

#[test]
fn compiles_grimoire_result() {
    let source = r#"
@@derive(Debug)
rune MyErr
    code: Int

grimoire: Result[Unit, MyErr]
    return ok(())
"#;
    let rust = generate_source(source);
    assert!(
        rust.contains("fn main() -> Result<(), crate::MyErr>"),
        "{rust}"
    );
    compile(source, &rust);
}

#[test]
fn executes_inherent_method_call() {
    let source = r#"
rune Point
    x: Int
    y: Int

ritual Point
    sum = (@) -> Int
        @.x + @.y

use = (p: Point) -> Int
    p.sum()

grimoire
    bind p = Point(x: 1, y: 2)
    print(use(p))
"#;
    let stdout = run_source(source);
    assert_eq!(stdout, "3\n");
}

#[test]
fn executes_non_capturing_closure() {
    let source = r#"
grimoire
    bind inc = (x: Int) => x + 1
    print(inc(2))
"#;
    let stdout = run_source(source);
    assert_eq!(stdout, "3\n");
}

#[test]
fn executes_for_over_vector() {
    let source = r#"
grimoire
    bind xs = Vec[1, 2, 3]
    morph total = 0
    for x in xs
        total = total + x
    print(total)
"#;
    let stdout = run_source(source);
    assert_eq!(stdout, "6\n");
}

#[test]
fn executes_closure_capture() {
    let source = r#"
grimoire
    bind y = 2
    bind inc = (x: Int) => x + y
    print(inc(3))
"#;
    let stdout = run_source(source);
    assert_eq!(stdout, "5\n");
}

#[test]
fn executes_for_over_array() {
    let source = r#"
grimoire
    bind xs = [1, 2, 3]
    morph total = 0
    for x in xs
        total = total + x
    print(total)
"#;
    let stdout = run_source(source);
    assert_eq!(stdout, "6\n");
}

#[test]
fn executes_for_over_set() {
    let source = r#"
grimoire
    bind tags = Set["a", "b", "c"]
    morph n = 0
    for tag in tags
        n = n + 1
    print(n)
"#;
    assert_eq!(run_source(source), "3\n");
}

#[test]
fn executes_for_over_map_entries() {
    let source = r#"
grimoire
    bind ages = Map["a": 1, "b": 2]
    morph total = 0
    for entry in ages
        total = total + entry.1
    print(total)
"#;
    assert_eq!(run_source(source), "3\n");
}

#[test]
fn executes_vec_map_filter_fold_collect() {
    let source = r#"
grimoire
    bind doubled = Vec[1, 2, 3, 4].map((x: Int) => x * 2).collect()
    bind evens = Vec[1, 2, 3, 4].iter().filter((x: Int) => x % 2 == 0).collect()
    bind total = Vec[1, 2, 3, 4].iter().fold(0, (acc: Int, x: Int) => acc + x)
    bind copied = Vec[1, 2, 3, 4].iter().collect()
    print(doubled[1])
    print(evens[1])
    print(total)
    print(copied[0])
"#;
    assert_eq!(run_source(source), "4\n4\n10\n1\n");
}

#[test]
fn executes_for_over_iterator() {
    let source = r#"
grimoire
    morph total = 0
    for value in Vec[1, 2, 3, 4].iter().filter((x: Int) => x % 2 == 0)
        total = total + value
    print(total)
"#;
    assert_eq!(run_source(source), "6\n");
}

#[test]
fn executes_for_tuple_destructuring_over_map() {
    let source = r#"
grimoire
    bind ages = Map["a": 1, "b": 2]
    morph total = 0
    for (key, value) in ages
        total = total + value
    print(total)
"#;
    assert_eq!(run_source(source), "3\n");
}

#[test]
fn executes_nested_tuple_destructuring_in_for() {
    let source = r#"
grimoire
    bind rows = Vec[(1, (2, 3)), (4, (5, 6))]
    morph total = 0
    for (a, (b, c)) in rows
        total = total + a + b + c
    print(total)
"#;
    assert_eq!(run_source(source), "21\n");
}

#[test]
fn executes_for_nested_tuple_over_map_values() {
    let source = r#"
grimoire
    bind data = Map["a": (1, (2, 3)), "b": (4, (5, 6))]
    morph total = 0
    for (key, (a, (b, c))) in data
        total = total + a + b + c
    print(total)
"#;
    assert_eq!(run_source(source), "21\n");
}

#[test]
fn executes_for_over_map_iter() {
    let source = r#"
grimoire
    bind ages = Map["a": 1, "b": 2]
    morph total = 0
    for (key, value) in ages.iter()
        total = total + value
    print(total)
"#;
    assert_eq!(run_source(source), "3\n");
}

#[test]
fn executes_map_iterator_adapters() {
    let source = r#"
grimoire
    bind ages = Map["a": 1, "b": 2]
    bind doubled = ages.iter().map((entry: (Str, Int)) => entry.1 * 2).collect()
    print(doubled.len())
"#;
    assert_eq!(run_source(source), "2\n");
}

#[test]
fn executes_set_iterator_adapters() {
    let source = r#"
grimoire
    bind tags = Set[1, 2, 3]
    bind total = tags.iter().fold(0, (acc: Int, value: Int) => acc + value)
    print(total)
"#;
    assert_eq!(run_source(source), "6\n");
}

#[test]
fn executes_generic_inherent_impl() {
    let source = r#"
rune Wrap[T]
    value: T

ritual[T] Wrap[T]
    get = (@own) -> T
        @.value

grimoire
    bind wrapped: Wrap[Int] = Wrap(value: 7)
    print(wrapped.get())
"#;
    assert_eq!(run_source(source), "7\n");
}

#[test]
fn executes_mut_receiver_method() {
    let source = run_source(
        r#"
rune Counter
    value: Int

ritual Counter
    bump = (@mut) -> Unit
        @.value = @.value + 1

grimoire
    morph c = Counter(value: 0)
    c.bump()
    print(c.value)
"#,
    );
    assert_eq!(source, "1\n");
}

#[test]
fn executes_own_receiver_method() {
    let source = run_source(
        r#"
rune Boxy
    value: Int

ritual Boxy
    consume = (@own) -> Int
        @.value

grimoire
    bind b = Boxy(value: 7)
    print(b.consume())
"#,
    );
    assert_eq!(source, "7\n");
}

#[test]
fn executes_own_receiver_with_non_copy_field() {
    let source = run_source(
        r#"
rune Text
    value: String

ritual Text
    take = (@own) -> String
        @.value

grimoire
    bind t = Text(value: format("pengu"))
    print(t.take())
"#,
    );
    assert_eq!(source, "pengu\n");
}

#[test]
fn emits_a_source_map_for_items() {
    let source = "rune Point\n    x: Int\n\ngrimoire\n    print(1)\n";
    let parsed = parse_program(FileId::new(0), source);
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    let types = check_crate(&lowered.krate);
    let lir = lower_crate(&lowered.krate, &types);
    let generated = generate(&lowered.krate, &lir);
    assert!(
        generated.diagnostics.is_empty(),
        "{:?}",
        generated.diagnostics
    );
    assert!(!generated.sourcemap.entries.is_empty());
    assert!(generated.sourcemap.to_json().contains("\"entries\""));
}

#[test]
fn prints_borrowed_strings_through_show() {
    let source = run_source(
        r#"
grimoire
    print("pengu")
"#,
    );
    assert_eq!(source, "pengu\n");
}

#[test]
fn prints_interpolated_strings() {
    let source =
        "grimoire\n    bind name = \"pengu\"\n    bind n = 3\n    print(\"hola #{name}: #{n}\")\n";
    assert_eq!(run_source(source), "hola pengu: 3\n");
}

#[test]
fn prints_vec_option_and_tuple() {
    let source = "grimoire\n    bind xs = Vec[1, 2]\n    print(xs)\n    print(some(7))\n    print((1, true))\n";
    assert_eq!(run_source(source), "[1, 2]\nsome(7)\n(1, true)\n");
}

#[test]
fn user_show_impl_prints_record() {
    let source = "rune Point\n    x: Int\n    y: Int\n\nritual Point for Show\n    show = (@) -> String\n        format(\"#{@.x},#{@.y}\")\n\ngrimoire\n    print(Point(x: 1, y: 2))\n";
    assert_eq!(run_source(source), "1,2\n");
}

#[test]
fn prints_map_set_and_result() {
    let source = "grimoire\n    bind m = Map[\"a\": 1]\n    print(m)\n    bind s = Set[2, 1]\n    print(s)\n";
    assert_eq!(run_source(source), "{a: 1}\n{1, 2}\n");
}

#[test]
fn panic_and_assert_compile() {
    let rust = generate_source("grimoire\n    assert(true, \"ok\")\n    panic(\"boom\")\n");
    assert!(rust.contains("assert!(true"), "{rust}");
    assert!(rust.contains("panic!("), "{rust}");
}

#[test]
fn format_returns_an_interpolated_string() {
    let source = "grimoire\n    bind n = 4\n    print(format(\"n=#{n}\"))\n";
    assert_eq!(run_source(source), "n=4\n");
}

#[test]
fn panic_aborts_the_process() {
    let rust = generate_source("grimoire\n    panic(\"boom\")\n");
    let stamp = format!(
        "{}_{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    );
    let dir = std::env::temp_dir().join(format!("pengu-codegen-panic-{stamp}"));
    std::fs::create_dir_all(&dir).unwrap();
    let file = dir.join("main.rs");
    std::fs::write(&file, &rust).unwrap();
    let exe = dir.join("main");
    let output = Command::new("rustc")
        .args(["--edition", "2024"])
        .arg(&file)
        .arg("-o")
        .arg(&exe)
        .output()
        .expect("rustc");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let output = Command::new(&exe).output().expect("run");
    assert!(!output.status.success(), "panic debe abortar");
    let _ = std::fs::remove_dir_all(dir);
}

#[test]
fn sourcemap_maps_statement_lines_to_pengu_spans() {
    let source = "add = (a: Int, b: Int) -> Int\n    a + b\n";
    let parsed = parse_program(FileId::new(0), source);
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    let types = check_crate(&lowered.krate);
    assert!(types.is_clean(), "{:?}", types.diagnostics);
    let lir = lower_crate(&lowered.krate, &types);
    let generated = generate(&lowered.krate, &lir);
    let expr_start = source.find("a + b").unwrap() as u32;
    let expr_end = expr_start + "a + b".len() as u32;
    assert!(
        generated
            .sourcemap
            .entries
            .iter()
            .any(|(_, span)| span.start <= expr_start && span.end >= expr_end),
        "sourcemap: {:?}",
        generated.sourcemap.entries
    );
}

#[test]
fn std_integrum_methods_compile_and_run() {
    let source = r#"
grimoire
    print((-5).abs())
    print(42.is_even())
    print((255).to_hex())
    print(7.wrapping_add(1))
    print(10.gcd(4))
    print(5.factorial())
    print(0.max(3))
    print(2.pow(10))
"#;
    assert_eq!(run_source(source), "5\ntrue\nff\n8\n2\n120\n3\n1024\n");
}

#[test]
fn std_integrum_signed_helpers_are_minimal() {
    let source = r#"
grimoire
    print((7).is_power_of_two())
    print((8).is_power_of_two())
    print((9).next_power_of_two())
    print((-3).abs_diff(4))
    print((-7).div_euclid(2))
    print((-7).rem_euclid(2))
"#;
    assert_eq!(run_source(source), "false\ntrue\n16\n7\n-4\n1\n");
}

#[test]
fn std_floatem_methods_compile_and_run() {
    let source = r#"
grimoire
    print((9.0).sqrt())
    print((2.0).powi(10))
    print((-3.5).abs())
    print((2.5).floor())
    print((2.5).ceil())
    print((3.7).round())
    print((1.0).exp())
    print((8.0).cbrt())
    print((3.0).to_int())
"#;
    assert_eq!(
        run_source(source),
        "3\n1024\n3.5\n2\n3\n4\n2.718281828459045\n2\n3\n"
    );
}

#[test]
fn std_floatem_classify_and_ordering() {
    let source = r#"
grimoire
    print((1.0).total_cmp(2.0))
    print((2.0).total_cmp(2.0))
    print((2.0).total_cmp(1.0))
    print((0.0).is_nan())
    print((1.0 / 0.0).is_infinite())
    print((1.0).is_normal())
    print((-0.0).is_sign_negative())
"#;
    assert_eq!(
        run_source(source),
        "Less\nEqual\nGreater\nfalse\ntrue\ntrue\ntrue\n"
    );
}

#[test]
fn std_floatem_unblocks_gate_b_hypotenuse() {
    let source = r#"
rune Point
    x: Float
    y: Float

length = (p: Point) -> Float
    (p.x * p.x + p.y * p.y).sqrt()

grimoire
    bind p = Point(x: 3.0, y: 4.0)
    print(length(p))
"#;
    assert_eq!(run_source(source), "5\n");
}

#[test]
fn std_littera_methods_compile_and_run() {
    let source = r#"
grimoire
    print(('a').to_ascii_uppercase())
    print(('Z').to_ascii_lowercase())
    print(('7').is_ascii_digit())
    print(('ñ').len_utf8())
    print(('ñ').len_utf16())
    print(('ñ').is_alphabetic())
    print(('\n').is_control())
    print(('\n').escape_default())
    print(('$').is_currency())
    print(('A').eq_ignore_ascii_case('a'))
    print(('x').to_string())
"#;
    assert_eq!(
        run_source(source),
        "A\nz\ntrue\n2\n1\ntrue\ntrue\n\\n\ntrue\ntrue\nx\n"
    );
}

#[test]
fn std_opera_pact_add_is_usable() {
    let source = r#"
summon std::opera::Add

rune Point
    x: Int
    y: Int

ritual Point for Add
    add = (@own, other: Self) -> Self
        Point(x: @.x + other.x, y: @.y + other.y)

grimoire
    bind p = Point(x: 1, y: 2)
    bind q = Point(x: 10, y: 20)
    bind s = p + q
    print(s.x)
    print(s.y)
"#;
    assert_eq!(run_source(source), "11\n22\n");
}

#[test]
fn std_opera_pact_neg_is_usable() {
    let source = r#"
summon std::opera::Neg

rune Vec2
    x: Int

ritual Vec2 for Neg
    neg = (@own) -> Self
        Vec2(x: -@.x)

grimoire
    bind v = -Vec2(x: 5)
    print(v.x)
"#;
    assert_eq!(run_source(source), "-5\n");
}

#[test]
fn std_veritas_bool_methods_compile_and_run() {
    let source = r#"
grimoire
    print(true.switch())
    print(false.switch())
    print(true.to_int())
    print(false.to_int())
    print(true.to_string())
    print(true.xor(false))
    print(true.implies(false))
    print(true.nand(true))
    print(false.nor(false))
    print(true.then_int(7, 9))
    print(false.to_float())
"#;
    assert_eq!(
        run_source(source),
        "false\ntrue\n1\n0\ntrue\ntrue\nfalse\nfalse\ntrue\n7\n0\n"
    );
}

#[test]
fn std_verbum_string_mutators_compile_and_run() {
    let source = r#"
grimoire
    morph b = String.from("hi")
    b.push('!')
    b.push_str(" there")
    print(b.to_string())
    print(b.len())
    b.insert(0, '>')
    print(b.to_string())
    print(b.remove(0))
    print(b.to_string())
    b.truncate(3)
    print(b.to_string())
    print(b.split_off(2))
    print(b.to_string())
"#;
    assert_eq!(
        run_source(source),
        "hi! there\n9\n>hi! there\n>\nhi! there\nhi!\n!\nhi\n"
    );
}

#[test]
fn std_verbum_str_methods_compile_and_run() {
    let source = r#"
grimoire
    bind s = "  Hola, Mundo  "
    print(s.trim())
    print(s.trim().len())
    print("a,b,c".split(",").len())
    print("a,b,c".split(",")[1])
    print("hola".to_uppercase())
    print("Hola".to_lowercase())
    print("abc".starts_with("ab"))
    print("abc".ends_with("bc"))
    print("abc".contains("b"))
    print("abc".find("c"))
    print("a-b-c".replace("-", "+"))
    print("  x  ".trim().capitalize())
    print(String.from("hi").repeat(3))
"#;
    assert_eq!(
        run_source(source),
        "Hola, Mundo\n11\n3\nb\nHOLA\nhola\ntrue\ntrue\ntrue\nsome(2)\na+b+c\nX\nhihihi\n"
    );
}

#[test]
fn std_capsa_basics_compile_and_run() {
    let source = r#"
grimoire
    morph v = Vec.new()
    v.push(1)
    v.push(2)
    v.push(3)
    print(v.len())
    print(v.is_empty())
    print(v.pop())
    print(v.len())
    print(v.get(0))
"#;
    assert_eq!(run_source(source), "3\nfalse\nsome(3)\n2\nsome(1)\n");
}

#[test]
fn std_capsa_operations_compile_and_run() {
    let source = r#"
even = (x: Int) -> Bool
    x % 2 == 0

grimoire
    morph v = Vec[3, 1, 2]
    v.sort()
    print(v.to_string())
    v.push(5)
    v.push(4)
    v.sort_unstable()
    print(v.to_string())
    v.reverse()
    print(v.to_string())
    print(v.contains(3))
    print(v.iter().min())
    print(v.iter().max())
    v.retain(even)
    print(v.to_string())
    print(v.len())
    v.insert(0, 10)
    print(v.to_string())
    print(v.swap_remove(0))
    morph tail = v.split_off(1)
    print(v.to_string())
    print(tail.to_string())
    v.rotate_left(1)
    print(v.to_string())
    print(v.clone().len())
"#;
    assert_eq!(
        run_source(source),
        "[1, 2, 3]\n[1, 2, 3, 4, 5]\n[5, 4, 3, 2, 1]\ntrue\nsome(1)\nsome(5)\n[4, 2]\n2\n[10, 4, 2]\n10\n[2]\n[4]\n[2]\n1\n"
    );
}

#[test]
fn std_tabula_methods_compile_and_run() {
    let source = r#"
desc = (key: Str, value: Int) -> Bool
    value > 1

grimoire
    morph m = Map.new()
    print(m.insert("a", 1))
    print(m.insert("b", 2))
    print(m.len())
    print(m.contains_key("a"))
    print(m.get("b"))
    print(m.get_key_value("b"))
    print(m.remove("a"))
    print(m.is_empty())
    morph n = Map.new()
    n.insert("x", 9)
    m.extend(n)
    print(m.len())
    m.retain(desc)
    print(m.len())
    print(m.to_string())
    m.get_or_insert("z", 7)
    print(m.len())
    print(m.remove_entry("z"))
"#;
    assert_eq!(
        run_source(source),
        "none\nnone\n2\ntrue\nsome(2)\nsome((b, 2))\nsome(1)\nfalse\n2\n2\n{b: 2, x: 9}\n3\nsome((z, 7))\n"
    );
}

#[test]
fn std_fasciculus_methods_compile_and_run() {
    let source = r#"
big = (x: Int) -> Bool
    x > 1

grimoire
    morph a = Set.new()
    print(a.insert(1))
    print(a.insert(1))
    print(a.contains(1))
    print(a.len())
    morph b = Set.new()
    b.insert(2)
    b.insert(3)
    print(a.union(b).to_string())
    print(a.intersection(b).to_string())
    print(a.difference(b).to_string())
    print(a.symmetric_difference(b).to_string())
    print(a.is_subset(b))
    print(a.is_disjoint(b))
    a.extend(b)
    print(a.len())
    a.retain(big)
    print(a.to_string())
    print(a.take(2))
    print(a.replace(5))
"#;
    assert_eq!(
        run_source(source),
        "true\nfalse\ntrue\n1\n{1, 2, 3}\n{}\n{1}\n{1, 2, 3}\nfalse\ntrue\n3\n{2, 3}\nsome(2)\nnone\n"
    );
}

#[test]
fn std_numerus_functions_compile_and_run() {
    let source = r#"
summon std::numerus::sqrt
summon std::numerus::pow
summon std::numerus::abs
summon std::numerus::floor
summon std::numerus::ceil
summon std::numerus::round
summon std::numerus::min
summon std::numerus::max
summon std::numerus::clamp
summon std::numerus::lerp
summon std::numerus::gcd
summon std::numerus::lcm
summon std::numerus::factorial
summon std::numerus::comb
summon std::numerus::perm
summon std::numerus::is_nan
summon std::numerus::signum
summon std::numerus::log
summon std::numerus::distance
summon std::numerus::dot
summon std::numerus::atan2
summon std::numerus::hypot
summon std::numerus::PI

grimoire
    print(sqrt(16.0))
    print(pow(2.0, 10.0))
    print(abs(-3.5))
    print(floor(2.9))
    print(ceil(2.1))
    print(round(2.5))
    print(min(1.0, 2.0))
    print(max(1.0, 2.0))
    print(clamp(5.0, 0.0, 3.0))
    print(lerp(0.0, 10.0, 0.5))
    print(gcd(12, 18))
    print(lcm(4, 6))
    print(factorial(5))
    print(comb(5, 2))
    print(perm(5, 2))
    print(is_nan(0.0))
    print(signum(-3.0))
    print(log(8.0, 2.0))
    print(distance((0.0, 0.0), (3.0, 4.0)))
    print(dot((1.0, 2.0), (3.0, 4.0)))
    print(atan2(0.0, 1.0))
    print(hypot(3.0, 4.0))
    print(PI)
"#;
    assert_eq!(
        run_source(source),
        "4\n1024\n3.5\n2\n3\n3\n1\n2\n3\n5\n6\n12\n120\n10\n20\nfalse\n-1\n3\n5\n11\n0\n5\n3.141592653589793\n"
    );
}

#[test]
fn std_proba_assertions_compile_and_run() {
    let source = r#"
summon std::proba::assert
summon std::proba::assert_eq
summon std::proba::assert_ne
summon std::proba::assert_approx_eq

grimoire
    assert(1 + 1 == 2, "dos")
    assert_eq(2 + 2, 4)
    assert_ne(3, 4)
    assert_approx_eq(0.1 + 0.2, 0.3, 0.000001)
    print("ok")
"#;
    assert_eq!(run_source(source), "ok\n");
}

#[test]
fn std_fluxus_io_compile_and_run() {
    let source = r#"
summon std::fluxus::write_stdout
summon std::fluxus::flush_stdout

grimoire
    bind written = write_stdout("ok")
    bind flushed = flush_stdout()
"#;
    assert_eq!(run_source(source), "ok");
}

#[test]
fn associated_constants_compile_and_run() {
    let source = r#"
unveil rune Limits
    unused: Int

ritual Limits
    sigil MAX: Int = 9
    sigil MIN: Int = 1

grimoire
    print(Limits.MAX)
    print(Limits.MIN)
    print(Int.MAX)
    print(Int.MIN)
    print(Int.BITS)
    print(Int.from_str("42"))
    print(Int.from_str_radix("ff", 16))
    print(Int.from_str("zz"))
    print(Float.from_str("2.5"))
    print(Char.from_u32(65))
"#;
    assert_eq!(
        run_source(source),
        "9\n1\n2147483647\n-2147483648\n32\nsome(42)\nsome(255)\nnone\nsome(2.5)\nsome(A)\n"
    );
}

#[test]
fn qualified_variants_and_ordering_compile_and_run() {
    let source = r#"
enchanting Color
    Red
    Green
    Blue

grimoire
    bind c = Color.Green
    match c
        when Color.Red then
            print("rojo")
        when Color.Green then
            print("verde")
        when Color.Blue then
            print("azul")
    print(Int.MIN)
    print(-2147483648)
    bind o = Less
    match o
        when Less then
            print("menor")
        when Equal then
            print("igual")
        when Greater then
            print("mayor")
"#;
    assert_eq!(
        run_source(source),
        "verde\n-2147483648\n-2147483648\nmenor\n"
    );
}

#[test]
fn lambdas_with_block_bodies_compile_and_run() {
    let source = r#"
grimoire
    bind xs = Vec[3, 1, 4, 2]
    xs.sort_by((a: Int, b: Int) =>
        if a < b then
            Less
        elseif a > b then
            Greater
        else
            Equal
    )
    print(xs)
    bind ys = Vec[5, 6]
    ys.sort_by((a: Int, b: Int) => if a < b then Less elseif a > b then Greater else Equal)
    print(ys)
    bind doubled = Vec[1, 2].map((x: Int) =>
        x * 2
    )
    print(doubled.collect())
"#;
    assert_eq!(run_source(source), "[1, 2, 3, 4]\n[5, 6]\n[2, 4]\n");
}

#[test]
fn ranges_and_destructuring_compile_and_run() {
    let source = r#"
summon std::verbum

grimoire
    bind r: Range[Usize] = 0_usize..4_usize
    print(r)
    bind s = "hola mundo"
    print(s.get(0_usize..4_usize))
    bind (head, tail) = s.split_at(4_usize)
    print(head)
    print(tail)
    print(s.as_bytes())
    morph t = String.from("abcdef")
    t.replace_range(1_usize..3_usize, "XY")
    print(t)
"#;
    assert_eq!(
        run_source(source),
        "0..4\nsome(hola)\nhola\n mundo\n[104, 111, 108, 97, 32, 109, 117, 110, 100, 111]\naXYdef\n"
    );
}

#[test]
fn rune_associated_functions_and_suffixed_literals_compile_and_run() {
    let source = r#"
unveil rune Punto
    unveil x: Int
    unveil y: Int

unveil ritual Punto
    new = (x: Int, y: Int) -> Punto
        Punto(x: x, y: y)

    suma = (@, otro: Punto) -> Int
        @.x + otro.x

grimoire
    bind p = Punto.new(1, 2)
    print(p.suma(Punto.new(3, 4)))
    print(41_u64)
    print(1.5_f32)
"#;
    assert_eq!(run_source(source), "4\n41\n1.5\n");
}

#[test]
fn option_and_result_patterns_compile_and_run() {
    let source = r#"
grimoire
    bind o: Option[Int] = some(7)
    match o
        when some(v) then
            print(v)
        when none then
            print(-1)
    bind r: Result[Int, String] = ok(3)
    match r
        when ok(v) then
            print(v)
        when err(e) then
            print(e)
    bind e2: Result[Int, String] = err(String.from("fallo"))
    match e2
        when ok(v) then
            print(v)
        when err(e) then
            print(e)
"#;
    assert_eq!(run_source(source), "7\n3\nfallo\n");
}

#[test]
fn via_module_round_trips_files() {
    let source = r#"
summon std::via
summon std::via::File

grimoire
    bind dir = "/tmp/pengu-via-codegen-test"
    via::remove_dir_all(dir)
    print(via::exists(dir))
    print(via::create_dir_all(dir))
    print(via::exists(dir))
    bind file = via::join(dir, "nota.txt")
    print(via::write_string(file.as_str(), "hola"))
    print(via::read_to_string(file.as_str()))
    print(via::is_file(file.as_str()))
    print(via::file_name(file.as_str()))
    print(via::file_stem(file.as_str()))
    print(via::extension(file.as_str()))
    match via::metadata(file.as_str())
        when ok(info) then
            print(info.len)
            print(info.is_file)
        when err(e) then
            print(e.message)
    print(via::walk_files(dir))
    match File.open(file.as_str())
        when ok(handle) then
            print(handle.read_to_string())
        when err(e) then
            print(e.message)
    print(via::append_string(file.as_str(), "!"))
    print(via::read_to_string(file.as_str()))
    print(via::copy(file.as_str(), via::join(dir, "copia.txt").as_str()))
    print(via::rename(via::join(dir, "copia.txt").as_str(), via::join(dir, "otra.txt").as_str()))
    print(via::exists(via::join(dir, "otra.txt").as_str()))
    print(via::remove_file(via::join(dir, "otra.txt").as_str()))
    print(via::remove_dir_all(dir))
    print(via::exists(dir))
"#;
    assert_eq!(
        run_source(source),
        "false\nok(())\ntrue\nok(())\nok(hola)\ntrue\nsome(nota.txt)\nsome(nota)\nsome(txt)\n4\ntrue\nok([/tmp/pengu-via-codegen-test/nota.txt])\nok(hola)\nok(())\nok(hola!)\nok(5)\nok(())\ntrue\nok(())\nok(())\nfalse\n"
    );
}

#[test]
fn exsecutor_runs_programs_and_commands() {
    let source = r#"
summon std::exsecutor
summon std::exsecutor::Command

grimoire
    match exsecutor::which("sh")
        when some(path) then
            print(path.len() > 0)
        when none then
            print(false)
    bind args: Vec[String] = Vec.new()
    args.push(String.from("-c"))
    args.push(String.from("echo hola"))
    match exsecutor::run_args("/bin/sh", args)
        when ok(out) then
            print(out.status.success)
            print(out.status.code)
            print(out.stdout.len())
        when err(e) then
            print(e.message)
    bind no_args: Vec[String] = Vec.new()
    match exsecutor::status_args("/bin/sh", no_args)
        when ok(st) then
            print(st.success)
        when err(e) then
            print(e.message)
    bind command = Command.new("/bin/sh")
    command.arg("-c")
    command.arg("exit 3")
    match command.status()
        when ok(st) then
            print(st.code)
        when err(e) then
            print(e.message)
    bind names: Vec[String] = Vec.new()
    names.push(String.from("uno"))
    names.push(String.from("dos"))
    morph joined = String.new()
    for name in names
        joined.push_str(name.as_str())
    print(joined)
"#;
    assert_eq!(
        run_source(source),
        "true\ntrue\nsome(0)\n5\ntrue\nsome(3)\nunodos\n"
    );
}

#[test]
fn exsecutor_pipes_stdio_and_exposes_command_state() {
    let source = r#"
summon std::exsecutor
summon std::exsecutor::Command

grimoire
    morph cmd = exsecutor::Command.new("cat")
    cmd.arg("-")
    cmd.stdin(exsecutor::Stdio.stdio_piped())
    cmd.stdout(exsecutor::Stdio.stdio_piped())
    print(cmd.get_args().len())
    print(cmd.get_current_dir().is_none())
    print(cmd.get_program())
    match cmd.spawn()
        when ok(child) then
            print(child.process_id().is_ok())
            match child.write_stdin(Vec[104_u8, 111_u8, 108_u8, 97_u8])
                when ok(escritos) then
                    print(escritos)
                when err(e) then
                    print(e.message)
            child.close_stdin()
            match child.wait_with_output()
                when ok(salida) then
                    print(salida.stdout.len())
                    print(salida.status.success)
                when err(e) then
                    print(e.message)
        when err(e) then
            print(e.message)
    print(exsecutor::Stdio.stdio_piped())
"#;
    assert_eq!(
        run_source(source),
        "1\ntrue\ncat\ntrue\n4\n4\ntrue\nStdio(piped)\n"
    );
}

#[test]
fn ambitus_and_tempus_compile_and_run() {
    let source = r#"
summon std::ambitus
summon std::tempus

grimoire
    print(ambitus::os().len() > 0)
    print(ambitus::arch().len() > 0)
    print(ambitus::family().len() > 0)
    ambitus::set_var("PENGU_AMBITUS_TEST", "41")
    print(ambitus::var("PENGU_AMBITUS_TEST"))
    print(ambitus::var("PENGU_AMBITUS_TEST_INEXISTENTE"))
    ambitus::remove_var("PENGU_AMBITUS_TEST")
    print(ambitus::var("PENGU_AMBITUS_TEST"))
    print(ambitus::temp_dir().len() > 0)
    print(ambitus::home_dir().is_some())
    print(ambitus::args().len() > 0)
    bind seconds = tempus::duration_secs(2)
    print(seconds.as_millis())
    print(seconds.as_secs())
    print(tempus::Duration.from_millis(1500).subsec_millis())
    print(tempus::duration_secs(3).checked_sub(tempus::duration_secs(2)).is_some())
    print(tempus::duration_secs(1).checked_sub(tempus::duration_secs(2)))
    print(tempus::Duration.from_secs(1).is_zero())
    bind start = tempus::Instant.now()
    tempus::sleep_ms(1)
    print(start.elapsed().as_millis() >= 0)
    match tempus::SystemTime.now().duration_since(tempus::unix_epoch())
        when ok(elapsed) then
            print(elapsed.as_secs() > 0)
        when err(e) then
            print(e.message)
"#;
    assert_eq!(
        run_source(source),
        "true\ntrue\ntrue\nok(41)\nerr(environment variable not found)\nerr(environment variable not found)\ntrue\ntrue\ntrue\n2000\n2\n500\ntrue\nnone\nfalse\ntrue\ntrue\n"
    );
}

#[test]
fn iterator_adapters_compile_and_run() {
    let source = r#"
grimoire
    bind xs = Vec[1, 2, 3, 4, 5]
    print(xs.iter().count())
    print(xs.iter().sum())
    print(xs.iter().min())
    print(xs.iter().max())
    print(xs.iter().last())
    print(xs.iter().nth(2))
    print(xs.iter().any((x: Int) => x > 4))
    print(xs.iter().all((x: Int) => x > 0))
    print(xs.iter().find((x: Int) => x % 2 == 0))
    print(xs.iter().position((x: Int) => x == 3))
    print(xs.iter().take(2).collect())
    print(xs.iter().skip(3).collect())
    print(xs.iter().step_by(2).collect())
    print(xs.iter().rev().collect())
    print(xs.iter().enumerate().collect())
    print(xs.iter().filter((x: Int) => x > 2).map((x: Int) => x * 10).collect())
    print(xs.len())
"#;
    assert_eq!(
        run_source(source),
        "5\n15\nsome(1)\nsome(5)\nsome(5)\nsome(3)\ntrue\ntrue\nsome(2)\nsome(2)\n[1, 2]\n[4, 5]\n[1, 3, 5]\n[5, 4, 3, 2, 1]\n[(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]\n[30, 40, 50]\n5\n"
    );
}

#[test]
fn tempus_float_durations_and_ambitus_var_os() {
    let source = r#"
summon std::tempus
summon std::ambitus

grimoire
    bind segundos = tempus::Duration.from_secs_f64(1.5)
    print(segundos.millis)
    print(segundos.as_secs_f64())
    print(segundos.subsec_micros())
    print(segundos.subsec_nanos())
    print(segundos.mul_f64(2.0).millis)
    print(segundos.div_f64(3.0).millis)
    print(tempus::Duration.from_secs_f32(0.25).millis)
    bind tarde = tempus::SystemTime(millis: 5000)
    bind pronto = tempus::SystemTime(millis: 1000)
    match pronto.duration_since(tarde)
        when ok(d) then
            print(d.millis)
        when err(e) then
            print(e.message)
            print(e.duration().millis)
    print(ambitus::var_os("PENGU_NO_EXISTE").is_none())
"#;
    assert_eq!(
        run_source(source),
        "1500\n1.5\n500000\n500000000\n3000\n500\n250\nel instante es anterior\n4000\ntrue\n"
    );
}

#[test]
fn nexus_cstrings_compile_and_run() {
    let source = r#"
grimoire
    match std::nexus::cstring_new("hola")
        when some(cs) then
            print(std::nexus::cstring_len(&cs))
            print(std::nexus::cstring_is_empty(&cs))
            print(std::nexus::cstring_to_str(&cs))
            print(std::nexus::cstring_into_string(cs))
        when none then
            print("inesperado")
    match std::nexus::cstring_new("a")
        when some(cs) then
            print(std::nexus::cstring_as_bytes(&cs))
        when none then
            print("inesperado")
    match std::nexus::cstring_from_bytes(Vec[65_u8, 66_u8])
        when some(cs) then
            print(std::nexus::cstring_into_string(cs))
        when none then
            print("nul")
"#;
    assert_eq!(
        run_source(source),
        "4\nfalse\nsome(hola)\nsome(hola)\n[97]\nsome(AB)\n"
    );
}

#[test]
fn iason_parses_and_writes_json() {
    let source = r#"
grimoire
    match std::iason::parse("{\"nombre\":\"ana\",\"edad\":30,\"ok\":true,\"tags\":[1,2]}")
        when ok(v) then
            print(v.is_object())
            print(v.len())
            print(v.keys_of())
            match v.get("nombre")
                when some(n) then
                    print(n.as_string())
                when none then
                    print("falta")
            match v.get("edad")
                when some(n) then
                    print(n.as_int())
                when none then
                    print("falta")
            print(v.to_string())
        when err(e) then
            print(e.message)
    match std::iason::parse("[1, 2]")
        when ok(v) then
            print(v.len())
        when err(e) then
            print(e.message)
"#;
    assert_eq!(
        run_source(source),
        "true\n4\n[nombre, edad, ok, tags]\nsome(ana)\nsome(30)\n{\"nombre\":\"ana\",\"edad\":30,\"ok\":true,\"tags\":[1,2]}\n2\n"
    );
}

#[test]
fn versio_and_digestum_compile_and_run() {
    let source = r#"
grimoire
    match std::versio::parse("1.2.3-alpha.1+build.5")
        when ok(v) then
            print(v.to_string())
            print(v.major_value())
            print(v.prerelease())
            print(v.is_prerelease())
            print(v.compare(&std::versio::version(1, 2, 3)))
            print(v.increment_patch().to_string())
        when err(e) then
            print(e.message)
    print(std::digestum::sha256_text("abc"))
    print(std::digestum::sha1_text("abc"))
    print(std::digestum::crc32_text("123456789"))
    print(std::digestum::hex(Vec[0_u8, 255_u8]))
"#;
    assert_eq!(
        run_source(source),
        "1.2.3-alpha.1+build.5\n1\nalpha.1\ntrue\nLess\n1.2.4\nba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad\na9993e364706816aba3e25717850c26c9cd0d89d\n3421780262\n00ff\n"
    );
}

#[test]
fn rete_tcp_round_trip() {
    let source = r#"
summon std::rete::TcpListener
summon std::rete::TcpStream

grimoire
    match TcpListener.listen("127.0.0.1", 0)
        when ok(listener) then
            match listener.local_addr()
                when ok(addr) then
                    bind port = addr.port
                    print(port > 0)
                    match TcpStream.connect("127.0.0.1", port)
                        when ok(client) then
                            client.write_str("hola")
                            client.flush()
                            client.shutdown()
                            match listener.accept()
                                when ok(pair) then
                                    bind (server, peer) = pair
                                    print(peer.host)
                                    match server.read_to_string()
                                        when ok(text) then
                                            print(text)
                                        when err(e) then
                                            print(e.message)
                                    server.shutdown()
                                when err(e) then
                                    print(e.message)
                        when err(e) then
                            print(e.message)
                when err(e) then
                    print(e.message)
        when err(e) then
            print(e.message)
"#;
    assert_eq!(run_source(source), "true\n127.0.0.1\nhola\n");
}

#[test]
fn terminus_globus_and_cellula_compile_and_run() {
    let source = r#"
grimoire
    print(std::terminus::red("error"))
    print(std::terminus::bold("ok"))
    print(std::globus::matches("*.rs", "main.rs"))
    print(std::globus::matches("*.rs", "src/main.rs"))
    print(std::globus::matches("**/*.rs", "src/main.rs"))
    print(std::globus::matches("[a-c]x", "bx"))
    print(std::globus::matches("{foo,bar}.txt", "bar.txt"))
    print(std::cellula::get("clave"))
    print(std::cellula::set_once("clave", "uno"))
    print(std::cellula::set_once("clave", "dos"))
    print(std::cellula::get("clave"))
    print(std::cellula::remove("clave"))
"#;
    assert_eq!(
        run_source(source),
        "\u{1b}[31merror\u{1b}[0m\n\u{1b}[1mok\u{1b}[0m\ntrue\nfalse\ntrue\ntrue\ntrue\nnone\ntrue\nfalse\nsome(uno)\ntrue\n"
    );
}

#[test]
fn archivum_writes_and_reads_tar() {
    let dir = "/tmp/pengu-archivum-codegen-test";
    std::fs::remove_dir_all(dir).ok();
    std::fs::create_dir_all(format!("{dir}/sub")).unwrap();
    std::fs::write(format!("{dir}/a.txt"), "uno\n").unwrap();
    std::fs::write(format!("{dir}/sub/b.txt"), "dos\n").unwrap();
    let source = format!(
        r#"
summon std::archivum
summon std::via

grimoire
    match archivum::pack("{dir}/out.tar", "{dir}")
        when ok(_) then print("creado")
        when err(e) then print(e.message)
    match archivum::entries("{dir}/out.tar")
        when ok(names) then print(names)
        when err(e) then print(e.message)
    match archivum::extract("{dir}/out.tar", "{dir}/salida")
        when ok(paths) then print(paths)
        when err(e) then print(e.message)
    match via::read_to_string("{dir}/salida/sub/b.txt")
        when ok(text) then print(text)
        when err(e) then print(e.message)
"#
    );
    assert_eq!(
        run_source(&source),
        "creado\n[a.txt, sub/, sub/b.txt]\n[a.txt, sub/, sub/b.txt]\ndos\n\n"
    );
}

#[test]
fn libra_parses_toml_configuration() {
    let path = "/tmp/pengu-libra-codegen-test.toml";
    std::fs::write(
        path,
        "# configuración\ntitle = \"PenguScript\"\ndebug = true\nport = 8080\nratio = 0.75\ntags = [\"a\", \"b\"]\n\n[database]\nhost = \"localhost\"\nport = 5432\n",
    )
    .unwrap();
    let source = format!(
        r#"
summon std::libra

grimoire
    match libra::parse_file("{path}")
        when ok(table) then
            print(table)
            print(table.get("title"))
            print(table.get_int("port"))
            print(table.get_bool("debug"))
            print(table.get_float("ratio"))
            print(table.get("database.host"))
            print(table.get_int("database.port"))
            print(table.kind_of("tags"))
            print(table.get("tags"))
            print(table.has("nada"))
            print(table.keys_of("database"))
        when err(e) then
            print(e)
"#
    );
    assert_eq!(
        run_source(&source),
        "Table(7 claves)\nsome(PenguScript)\nsome(8080)\nsome(true)\nsome(0.75)\nsome(localhost)\nsome(5432)\nsome(array)\nsome(a, b)\nfalse\n[database.host, database.port]\n"
    );
}

#[test]
fn nested_match_expressions_compile_and_run() {
    let source = r#"
unveil doble = (value: Option[Int]) -> Option[Int]
    match value
        when some(_) then
            match Int.from_str("21")
                when some(n) then some(n * 2)
                when none then none
        when none then none

grimoire
    print(doble(some(1)))
    print(doble(none))
"#;
    assert_eq!(run_source(source), "some(42)\nnone\n");
}

#[test]
fn std_module_aliases_resolve() {
    let source = r#"
summon std::via
summon std::env
summon std::ffi

length = (text: &Str) -> Option[Usize]
    bind value = ffi.cstring_new(text)?
    some(ffi.cstring_len(&value))

grimoire
    bind present = via.exists("/tmp")
    print(present)
    bind args = env.args()
    print(args.len() >= 0)
    print(length("hi").is_some())
"#;
    assert_eq!(run_source(source), "true\ntrue\ntrue\n");
}

#[test]
fn via_paths_walk_options_and_metadata_compile_and_run() {
    let dir = "/tmp/pengu-via-paths-codegen-test";
    std::fs::remove_dir_all(dir).ok();
    std::fs::create_dir_all(format!("{dir}/sub")).unwrap();
    std::fs::write(format!("{dir}/a.txt"), "hola\n").unwrap();
    std::fs::write(format!("{dir}/sub/b.txt"), "mundo\n").unwrap();
    let source = format!(
        r#"
summon std::via

grimoire
    bind p = via::Path.new("{dir}/sub/b.txt")
    print(p.file_name())
    print(p.extension())
    print(p.file_stem())
    print(p.parent())
    print(p.is_absolute())
    print(p.is_file())
    print(p.components())
    print(p.starts_with(via::Path.new("{dir}")))
    print(p.strip_prefix(via::Path.new("{dir}")))
    morph buf = via::PathBuf.from_path(via::Path.new("{dir}"))
    buf.push("sub")
    buf.push("b.txt")
    print(buf)
    print(buf.with_extension("md"))
    bind options = via::WalkOptions.new()
    options.max_depth(2)
    match options.walk_files("{dir}")
        when ok(entries) then
            for entry in entries
                print(entry.file_name())
                print(entry.is_file())
        when err(e) then print(e)
    match via::file_type("{dir}/sub")
        when ok(kind) then print(kind.is_dir())
        when err(e) then print(e)
    match via::permissions("{dir}/a.txt")
        when ok(perms) then print(perms.readonly())
        when err(e) then print(e)
    match via::modified_ms("{dir}/a.txt")
        when ok(stamp) then print(stamp.is_some())
        when err(e) then print(e)
"#
    );
    assert_eq!(
        run_source(&source),
        "some(b.txt)\nsome(txt)\nsome(b)\nsome({dir}/sub)\ntrue\ntrue\n[/, tmp, pengu-via-paths-codegen-test, sub, b.txt]\ntrue\nsome(sub/b.txt)\n{dir}/sub/b.txt\n{dir}/sub/b.md\na.txt\ntrue\nb.txt\ntrue\ntrue\nfalse\ntrue\n"
            .replace("{dir}", dir)
    );
}

#[test]
fn via_open_options_and_byte_io_compile_and_run() {
    let dir = "/tmp/pengu-via-open-codegen-test";
    std::fs::remove_dir_all(dir).ok();
    std::fs::create_dir_all(dir).unwrap();
    let source = format!(
        r#"
summon std::via

grimoire
    bind data: Vec[U8] = Vec.new()
    data.push(104_u8)
    data.push(111_u8)
    data.push(108_u8)
    data.push(97_u8)
    morph options = via::OpenOptions.new()
    options.write(true).create(true).truncate(true)
    match options.open("{dir}/out.txt")
        when ok(file) then
            match file.write_bytes(data)
                when ok(written) then print(written)
                when err(e) then print(e)
            file.sync_all()
            file.close()
        when err(e) then print(e)
    match via::read_to_string("{dir}/out.txt")
        when ok(text) then print(text)
        when err(e) then print(e)
    match via::File.open("{dir}/out.txt")
        when ok(file) then
            match file.read_bytes(2_u64)
                when ok(bytes) then print(bytes)
                when err(e) then print(e)
            print(file.modified_ms())
            file.close()
        when err(e) then print(e)
"#
    );
    let output = run_source(&source);
    let lines: Vec<&str> = output.lines().collect();
    assert_eq!(lines[0], "4");
    assert_eq!(lines[1], "hola");
    assert_eq!(lines[2], "[104, 111]");
    assert!(lines[3].starts_with("ok(some("), "{output}");
}

#[test]
fn string_coercions_between_str_and_string() {
    let source = r#"
summon std::verbum

unveil saluda = () -> String
    "hola"

unveil longitud = (texto: Str) -> Usize
    texto.len()

unveil recibe_string = (texto: String) -> Usize
    texto.len()

unveil recibe_str = (texto: &Str) -> Usize
    texto.len()

grimoire
    bind literal: String = "anotado"
    bind owned = saluda()
    bind origen = String.from("mundo")
    bind copia: &Str = origen
    print(owned)
    print(literal)
    print(recibe_string("literal"))
    print(recibe_str(owned))
    print(longitud(owned))
    print(longitud("directo"))
    print(copia)
"#;
    assert_eq!(run_source(source), "hola\nanotado\n7\n4\n4\n7\nmundo\n");
}

#[test]
#[cfg(unix)]
fn std_nexus_curse_as_value() {
    let source = r#"
summon std::ffi

foreign "C"
    strlen = (text: &CStr) -> Usize

-- SAFETY: `value` vive hasta el final de la llamada y `strlen` no la guarda.
length_raw = (value: &CString) -> Usize
    curse
        strlen(&value)

grimoire
    bind created = ffi.cstring_new("cuatro")
    bind largo = match created
        when some(value) then
            curse
                length_raw(&value)
        when none then 0
    print(largo)
"#;
    assert_eq!(run_source(source), "6\n");
}

#[test]
fn std_nexus_ffi_end_to_end() {
    let source = r#"
summon std::ffi

foreign "C"
    strlen = (text: &CStr) -> Usize
    toupper = (c: Int) -> Int

-- SAFETY: la cadena pertenece al llamador y no se libera durante la llamada.
c_len = (text: &Str) -> Usize
    bind value = match ffi.cstring_new(text)
        when some(cs) then cs
        when none then
            return 0_usize
    curse
        strlen(ffi.cstring_as_c_str(&value))

describe = (text: &CStr) -> String
    ffi.cstr_to_string_lossy(text)

grimoire
    print(c_len("abcde"))
    bind owned = match ffi.cstring_new("hola")
        when some(v) then v
        when none then
            return
    print(ffi.cstring_len(&owned))
    print(ffi.cstring_is_empty(&owned))
    bind copy = ffi.cstring_clone(&owned)
    print(ffi.cstring_to_string_lossy(&copy))
    bind text = match ffi.cstring_to_str(&copy)
        when some(t) then t
        when none then
            return
    print(text)
    curse
        print(toupper(97))
        print(ffi.cstr_len(ffi.cstring_as_c_str(&owned)))
        print(ffi.cstr_equals_str(ffi.cstring_as_c_str(&owned), "hola"))
        print(describe(ffi.cstring_as_c_str(&owned)))
"#;
    assert_eq!(
        run_source(source),
        "5\n4\nfalse\nhola\nhola\n65\n4\ntrue\nhola\n"
    );
}

#[test]
fn std_funis_adapters_compile_and_run() {
    let source = r#"
summon std::iter

grimoire
    bind xs = Vec[1, 2, 3, 4, 5, 6]
    bind it = xs.iter().filter((x: Int) => x % 2 == 0)
    print(it.map((x: Int) => x * 10).collect())
    print(xs.iter().filter_map((x: Int) => if x % 2 == 0 then some(x) else none).collect())
    print(xs.iter().take_while((x: Int) => x < 4).collect())
    print(xs.iter().skip_while((x: Int) => x < 4).collect())
    print(xs.iter().reduce((a: Int, b: Int) => a + b))
    print(xs.iter().product())
    print(xs.iter().fuse().collect())
    print(xs.iter().flat_map((x: Int) => Vec[x, x * 10]).collect())
    print(Vec[Vec[1, 2], Vec[3]].iter().flatten().collect())
    print(xs.iter().chain(Vec[9, 8].iter()).collect())
    print(xs.iter().max_by((a: Int, b: Int) => if a < b then Less else if a > b then Greater else Equal))
"#;
    assert_eq!(
        run_source(source),
        "[20, 40, 60]\n[2, 4, 6]\n[1, 2, 3]\n[4, 5, 6]\nsome(21)\n720\n[1, 2, 3, 4, 5, 6]\n[1, 10, 2, 20, 3, 30, 4, 40, 5, 50, 6, 60]\n[1, 2, 3]\n[1, 2, 3, 4, 5, 6, 9, 8]\nsome(6)\n"
    );
}

#[test]
fn std_funis_str_chars_compile_and_run() {
    let source = r#"
grimoire
    bind s = "hola"
    print(s.chars().count())
    print(s.chars().collect())
    print(s.bytes().count())
    print(s.char_indices().collect())
    print(s.chars().map((c: Char) => c.to_ascii_uppercase()).collect())
"#;
    assert_eq!(
        run_source(source),
        "4\n[h, o, l, a]\n4\n[(0, h), (1, o), (2, l), (3, a)]\n[H, O, L, A]\n"
    );
}

#[test]
fn std_funis_bind_adapted_iterator() {
    let source = r#"
grimoire
    bind xs = Vec[1, 2, 3, 4]
    bind it = xs.iter().take(2)
    print(it.collect())
    bind it2 = xs.iter().skip(2)
    print(it2.rev().collect())
"#;
    assert_eq!(run_source(source), "[1, 2]\n[4, 3]\n");
}

#[test]
fn std_digestum_sha512_and_hmac() {
    let source = r#"
grimoire
    print(std::digestum::sha512_text("abc"))
    print(std::digestum::hmac_sha256_text("clave", "hola"))
    print(std::digestum::constant_time_eq(std::digestum::sha256(Vec[1_u8]), std::digestum::sha256(Vec[1_u8])))
    print(std::digestum::constant_time_eq(std::digestum::sha256(Vec[1_u8]), std::digestum::sha256(Vec[2_u8])))
"#;
    assert_eq!(
        run_source(source),
        "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f\n67c0066d5104af2bd88decc45269ddb529a0097b8da4cfbbe58ec2a5f63ca50d\ntrue\nfalse\n"
    );
}

#[test]
fn std_iason_mutators_and_paths() {
    let source = r#"
summon std::iason

grimoire
    match iason::parse("{\"a\":{\"b\":[1,2]},\"n\":1}")
        when ok(doc) then
            match doc.get_path("a.b.1")
                when some(v) then
                    print(v.as_int())
                when none then
                    print("sin ruta")
            print(doc.equals(&doc))
            print(doc.get_path("a.b").is_some())
        when err(e) then
            print(e.message)
    morph obj = iason::object_value(Vec[String.from("x")], Vec[iason::int_value(1)])
    obj.set("y", &iason::int_value(2))
    obj.insert("z", &iason::int_value(3))
    obj.set("x", &iason::int_value(9))
    print(obj.to_string())
    print(obj.remove("y"))
    print(obj.to_string())
    morph arr = iason::array_value(Vec[iason::int_value(1)])
    arr.push(&iason::int_value(2))
    print(arr.to_string())
"#;
    assert_eq!(
        run_source(source),
        "some(2)\ntrue\ntrue\n{\"x\":9,\"y\":2,\"z\":3}\ntrue\n{\"x\":9,\"z\":3}\n[1,2]\n"
    );
}

#[test]
fn std_libra_inline_tables_and_dates() {
    let source = r#"
summon std::libra

grimoire
    bind text = "titulo = \"demo\"\n[deps]\nserde = { version = \"1.0\", features = [\"derive\", \"std\"] }\nfecha = 1979-05-27\ncuando = 1979-05-27T07:32:00Z\nlista = [1, 2, 3]\n"
    match libra::parse(text)
        when ok(t) then
            print(t.get("titulo"))
            print(t.get("deps.serde.version"))
            print(t.kind_of("deps.fecha"))
            print(t.kind_of("deps.cuando"))
            print(t.get_array("deps.serde.features"))
            print(t.get_array("deps.lista"))
        when err(e) then
            print(e.message)
"#;
    assert_eq!(
        run_source(source),
        "some(demo)\nsome(1.0)\nsome(date)\nsome(datetime)\nsome([derive, std])\nsome([1, 2, 3])\n"
    );
}

#[test]
fn std_versio_requirement_grammar() {
    let source = r#"
summon std::versio

grimoire
    bind v = versio::version(1, 4, 2)
    print(v.satisfies("^1.2"))
    print(v.satisfies("^2.0"))
    print(v.satisfies("^1.0 || ^2.0"))
    print(v.satisfies(">=1.0.0 <2.0.0"))
    print(v.satisfies("1.x"))
    print(v.satisfies("1.4.x"))
    print(v.satisfies("1.5.x"))
    print(v.satisfies("*"))
    print(v.satisfies("~1.4"))
"#;
    assert_eq!(
        run_source(source),
        "ok(true)\nok(false)\nok(true)\nok(true)\nok(true)\nok(true)\nok(false)\nok(true)\nok(true)\n"
    );
}

#[test]
fn std_libra_arrays_of_tables() {
    let source = r#"
summon std::libra

grimoire
    bind text = "[[item]]\nnombre = \"a\"\npeso = 1\n[[item]]\nnombre = \"b\"\npeso = 2\n"
    match libra::parse(text)
        when ok(t) then
            print(t.get("item.0.nombre"))
            print(t.get_int("item.1.peso"))
        when err(e) then
            print(e.message)
"#;
    assert_eq!(run_source(source), "some(a)\nsome(2)\n");
}

#[test]
fn generic_functions_with_bounds_and_inference_compile_and_run() {
    let source = r#"
summon std::opera::Ord

unveil maximo = [T: Ord](a: T, b: T) -> T
    if a < b then b else a

grimoire
    print(maximo(1, 2))
    print(maximo(9_u64, 4_u64))
"#;
    assert_eq!(run_source(source), "2\n9\n");
}

#[test]
fn generic_free_functions_over_vecs_compile_and_run() {
    let source = r#"
unveil pila_push = [T](items: Vec[T], value: T) -> Vec[T]
    morph out = items
    out.push(value)
    out

unveil pila_pop = [T](items: Vec[T]) -> Option[T]
    morph out = items
    out.pop()

grimoire
    morph xs: Vec[Int] = Vec.new()
    xs = pila_push(xs, 1)
    xs = pila_push(xs, 2)
    print(xs.len())
    match pila_pop(xs)
        when some(v) then print(v)
        when none then print("vacia")
"#;
    assert_eq!(run_source(source), "2\n2\n");
}

#[test]
fn structura_containers_compile_and_run() {
    let source = r#"
grimoire
    morph xs: Vec[Int] = Vec.new()
    xs = std::structura::pila_push(xs, 1)
    xs = std::structura::pila_push(xs, 2)
    print(xs.len())
    match std::structura::pila_pop(xs)
        when some(v) then print(v)
        when none then print("vacia")
    morph ys: Vec[String] = Vec.new()
    ys = std::structura::duplex_push_front(ys, String.from("b"))
    ys = std::structura::duplex_push_front(ys, String.from("a"))
    print(ys.len())
    match std::structura::duplex_pop_front(ys)
        when some(v) then print(v)
        when none then print("vacia")
"#;
    assert_eq!(run_source(source), "2\n2\n2\na\n");
}

#[test]
fn record_fields_accept_str_and_string() {
    let source = r#"
summon std::iason::Json

grimoire
    bind j = Json(kind: "texto", flag: false, integer: 0, number: 0.0, text: String.new(), items: Vec.new(), keys: Vec.new())
    print(j.kind_of())
    print(j.is_string())
"#;
    assert_eq!(run_source(source), "texto\nfalse\n");
}

#[test]
fn std_archivum_zip_and_targz_roundtrip() {
    let source = r#"
summon std::archivum
summon std::ambitus
summon std::via

grimoire
    bind base = ambitus::temp_dir() + "/pengu-s9-zip"
    bind out = ambitus::temp_dir() + "/pengu-s9-zip/out"
    bind one = ambitus::temp_dir() + "/pengu-s9-zip/uno.txt"
    bind zip_path = ambitus::temp_dir() + "/pengu-s9-zip/pack.zip"
    bind tgz_path = ambitus::temp_dir() + "/pengu-s9-zip/pack.tar.gz"
    bind names: Vec[String] = Vec[String.from("uno.txt")]
    match via::create_dir_all(base.as_str())
        when ok(_) then print("dir")
        when err(e) then print(e.message)
    match via::write_string(one.as_str(), "hola")
        when ok(_) then print("write")
        when err(e) then print(e.message)
    match archivum::create_zip(zip_path.as_str(), base.as_str(), names.clone())
        when ok(_) then print("zip")
        when err(e) then print(e.message)
    match archivum::entries_zip(zip_path.as_str())
        when ok(list) then print(list)
        when err(e) then print(e.message)
    match archivum::extract_zip(zip_path.as_str(), out.as_str())
        when ok(list) then print(list)
        when err(e) then print(e.message)
    match archivum::create_targz(tgz_path.as_str(), base.as_str(), names.clone())
        when ok(_) then print("targz")
        when err(e) then print(e.message)
    match archivum::entries_targz(tgz_path.as_str())
        when ok(list) then print(list)
        when err(e) then print(e.message)
    print(archivum::compress_gz(Vec[65 as U8, 66 as U8]).len())
"#;
    assert_eq!(
        run_source(source),
        "dir\nwrite\nzip\n[uno.txt]\n[uno.txt]\ntargz\n[uno.txt]\n25\n"
    );
}

#[test]
fn std_s9_terminus_and_glob_helpers() {
    let source = r#"
summon std::terminus
summon std::globus
summon std::ambitus
summon std::via

grimoire
    print(terminus::progress_bar(42, 100, 10))
    print(terminus::progress_bar(0, 10, 4))
    print(globus::matches("src/**/*.pengu", "src/std/verbum.pengu"))
    print(globus::matches("*.pengu", "src/main.pengu"))
    bind root = ambitus::temp_dir() + "/pengu-s9-glob"
    bind inner = ambitus::temp_dir() + "/pengu-s9-glob/src"
    bind file = ambitus::temp_dir() + "/pengu-s9-glob/src/lib.rs"
    match via::create_dir_all(inner.as_str())
        when ok(_) then print("dir")
        when err(e) then print(e.message)
    match via::write_string(file.as_str(), "fn")
        when ok(_) then print("write")
        when err(e) then print(e.message)
    print(globus::find_with("**/*.rs", root.as_str(), 2, false, false).len())
    print(globus::find_with("**/*.rs", root.as_str(), 0, false, false).len())
"#;
    assert_eq!(
        run_source(source),
        "[####------]  42%\n[----]   0%\ntrue\nfalse\ndir\nwrite\n1\n0\n"
    );
}
