//! Pruebas de C1: módulos, items, scopes y resolución de nombres.

use pengu_hir::{DefKind, HirCrate, Res, lower_declaration, lower_program};
use pengu_span::FileId;
use pengu_syntax::ast::Visibility;
use pengu_syntax::{parse_declaration_file, parse_program};

fn lower(source: &str) -> HirCrate {
    let parsed = parse_program(FileId::new(0), source);
    assert!(
        parsed.diagnostics.is_empty(),
        "errores de parser: {:?}",
        parsed.diagnostics
    );
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    assert_eq!(lowered.diagnostics, lowered.krate.diagnostics);
    lowered.krate
}

fn def_id(krate: &HirCrate, name: &str, kind: DefKind) -> pengu_hir::DefId {
    krate
        .defs
        .iter()
        .find(|def| def.name == name && def.kind == kind)
        .unwrap_or_else(|| panic!("no se encontró {name} como {kind:?}"))
        .id
}

/// Módulos declarados por el usuario (sin el árbol reservado `std`).
fn user_modules(krate: &HirCrate) -> usize {
    krate
        .modules
        .iter()
        .filter(|module| module.id != krate.root && !under_std(krate, module.id))
        .count()
}

fn under_std(krate: &HirCrate, module: pengu_hir::ModuleId) -> bool {
    let mut current = Some(module);
    while let Some(id) = current {
        let data = krate.module(id);
        if data.name == "std" {
            return true;
        }
        current = data.parent;
    }
    false
}

fn codes(krate: &HirCrate) -> Vec<&'static str> {
    krate.diagnostics.iter().map(|d| d.code).collect()
}

#[test]
fn top_level_items_are_declared() {
    let krate = lower(
        r#"
rune Point
    x: Float
    y: Float

enchanting Shape
    Circle(Float)
    Empty

pact Show
    show = (@) -> String

area = (p: Point) -> Float
    p.x

sigil LIMIT: Int = 10

grimoire
    print("hola")
"#,
    );

    assert_eq!(user_modules(&krate), 0);
    assert!(krate.diagnostics.is_empty(), "{:?}", krate.diagnostics);
    for (name, kind) in [
        ("Point", DefKind::Type),
        ("Shape", DefKind::Type),
        ("Show", DefKind::Pact),
        ("area", DefKind::Function),
        ("LIMIT", DefKind::Const),
        ("main", DefKind::Function),
    ] {
        let _ = def_id(&krate, name, kind);
    }
    let area = def_id(&krate, "area", DefKind::Function);
    assert!(krate.bodies.iter().any(|body| body.owner == area));
}

#[test]
fn nested_scroll_creates_a_module_and_imports_type() {
    let krate = lower(
        r"
scroll geometry
    unveil rune Point
        x: Int
        y: Int

summon crate::geometry::Point

origin = () -> Point
    Point(x: 0, y: 0)
",
    );

    assert_eq!(user_modules(&krate), 1);
    assert!(krate.diagnostics.is_empty(), "{:?}", krate.diagnostics);
    let root = krate.module(krate.root);
    let imported = krate
        .scope(root.scope)
        .types
        .get("Point")
        .expect("Point importado");
    assert!(matches!(imported.res, Res::Def(_)));
}

#[test]
fn locals_and_params_resolve_to_local_ids() {
    let krate = lower(
        r"
f = (x: Int) -> Int
    bind y = x
    y
",
    );

    assert!(krate.diagnostics.is_empty(), "{:?}", krate.diagnostics);
    let body = krate
        .bodies
        .iter()
        .find(|body| krate.def(body.owner).name == "f")
        .expect("cuerpo de `f`");
    assert_eq!(body.params.len(), 1);
    assert_eq!(body.locals.len(), 2);
    assert!(
        body.resolutions
            .iter()
            .any(|r| matches!(r.res, Res::Local(_)))
    );
}

#[test]
fn generic_parameter_resolves_as_a_type() {
    let krate = lower(
        r"
identity = [T](value: T) -> T
    value
",
    );

    assert!(krate.diagnostics.is_empty(), "{:?}", krate.diagnostics);
    assert!(
        krate
            .defs
            .iter()
            .any(|def| def.name == "T" && def.kind == DefKind::Generic)
    );
}

#[test]
fn unknown_value_reports_e2004() {
    let krate = lower(
        r"
f = () -> Int
    missing
",
    );

    assert!(
        codes(&krate).contains(&"PGS-E2004"),
        "{:?}",
        krate.diagnostics
    );
}

#[test]
fn unknown_type_reports_e2004() {
    let krate = lower(
        r"
f = (x: Missing) -> Int
    1
",
    );

    assert!(
        codes(&krate).contains(&"PGS-E2004"),
        "{:?}",
        krate.diagnostics
    );
}

#[test]
fn duplicate_local_reports_e1102() {
    let krate = lower(
        r"
f = () -> Int
    bind x = 1
    bind x = 2
    x
",
    );

    assert!(
        codes(&krate).contains(&"PGS-E1102"),
        "{:?}",
        krate.diagnostics
    );
}

#[test]
fn private_item_import_reports_e2006() {
    let krate = lower(
        r"
scroll inner
    hidden = () -> Int
        1

summon inner::hidden
",
    );

    assert!(
        codes(&krate).contains(&"PGS-E2006"),
        "{:?}",
        krate.diagnostics
    );
}

#[test]
fn self_outside_ritual_reports_e1209() {
    let krate = lower(
        r"
f = () -> Self
    1
",
    );

    assert!(
        codes(&krate).contains(&"PGS-E1209"),
        "{:?}",
        krate.diagnostics
    );
}

#[test]
fn tome_and_scroll_visibility_are_accessible_from_parent() {
    let krate = lower(
        r"
scroll inner
    unveil(tome) rune TomeOnly
        x: Int
    unveil(scroll) rune ScrollOnly
        x: Int
    rune Hidden
        x: Int

summon inner::TomeOnly
summon inner::ScrollOnly
summon inner::Hidden
",
    );

    let codes = codes(&krate);
    assert!(codes.contains(&"PGS-E2006"), "{:?}", krate.diagnostics);
    let hidden = krate
        .defs
        .iter()
        .find(|d| d.name == "Hidden" && d.kind == DefKind::Type)
        .unwrap();
    let imports = krate.module(krate.root).scope;
    assert!(krate.scope(imports).types.contains_key("TomeOnly"));
    assert!(krate.scope(imports).types.contains_key("ScrollOnly"));
    assert!(!krate.scope(imports).types.contains_key("Hidden"));
    assert_eq!(hidden.vis, pengu_syntax::ast::Visibility::Private);
}

#[test]
fn module_alias_and_type_import_resolve() {
    let krate = lower(
        r"
scroll geometry
    unveil rune Point
        x: Int

summon crate::geometry as geo
summon crate::geometry::Point as P

make = () -> P
    P(x: 1)
",
    );

    assert!(krate.diagnostics.is_empty(), "{:?}", krate.diagnostics);
    let root = krate.scope(krate.module(krate.root).scope);
    assert!(root.modules.contains_key("geo"));
    assert!(root.types.contains_key("P"));
}

#[test]
fn self_inside_ritual_resolves() {
    let krate = lower(
        r"
rune Point
    x: Int

ritual Point
    clone = (@) -> Self
        Point(x: @.x)
",
    );

    assert!(krate.diagnostics.is_empty(), "{:?}", krate.diagnostics);
}

#[test]
fn declaration_file_resolves_ptr_type() {
    use pengu_hir::lower_declaration;
    use pengu_syntax::parse_declaration_file;

    let parsed = parse_declaration_file(
        FileId::new(1),
        r#"
abi "C"
rune File
fopen = (path: Str, mode: Str) -> Ptr[File]
"#,
    );
    assert!(
        parsed.diagnostics.is_empty(),
        "parser: {:?}",
        parsed.diagnostics
    );
    let lowered = lower_declaration(&parsed.file.expect("declaración"));
    assert!(lowered.diagnostics.is_empty(), "{:?}", lowered.diagnostics);
    assert!(lowered.krate.defs.iter().any(|d| d.name == "fopen"));
}

#[test]
fn duplicate_import_reports_e2005() {
    let krate = lower(
        r"
scroll inner
    unveil x = () -> Int
        1

summon inner::x
summon inner::x as x
",
    );

    assert!(
        codes(&krate).contains(&"PGS-E2005"),
        "{:?}",
        krate.diagnostics
    );
}

#[test]
fn value_import_resolves_call_target() {
    let krate = lower(
        r"
scroll inner
    unveil f = () -> Int
        1

summon inner::f

g = () -> Int
    f()
",
    );

    assert!(krate.diagnostics.is_empty(), "{:?}", krate.diagnostics);
}

#[test]
fn duplicate_module_and_item_report_codes() {
    let krate = lower(
        r"
scroll dup
    x = () -> Int
        1

scroll dup
    y = () -> Int
        2

f = () -> Int
    1

f = () -> Int
    2
",
    );

    let codes = codes(&krate);
    assert!(codes.contains(&"PGS-E2013"), "{:?}", krate.diagnostics);
    assert!(codes.contains(&"PGS-E2005"), "{:?}", krate.diagnostics);
}

#[test]
fn missing_module_import_reports_e2003() {
    let krate = lower(
        r"
summon missing::thing
",
    );

    assert!(
        codes(&krate).contains(&"PGS-E2003"),
        "{:?}",
        krate.diagnostics
    );
}

#[test]
fn pact_self_type_resolves_in_default_method() {
    let krate = lower(
        r"
pact Identity
    itself = (@) -> Self
        @
",
    );

    assert!(krate.diagnostics.is_empty(), "{:?}", krate.diagnostics);
}

#[test]
fn prelude_patterns_resolve_without_e2004() {
    let krate = lower(
        r"
f = (opt: ?Int) -> Int
    match opt
        when Some(x) then x
        when None then 0
",
    );

    assert!(krate.diagnostics.is_empty(), "{:?}", krate.diagnostics);
}

#[test]
fn or_pattern_bindings_are_not_duplicated() {
    let krate = lower(
        r"
f = (x: Int) -> Int
    match x
        when 1 | 2 then 10
        else 0
",
    );

    assert!(krate.diagnostics.is_empty(), "{:?}", krate.diagnostics);
}

#[test]
fn pact_signature_without_body_resolves_types() {
    let krate = lower(
        r"
pact Shape
    area = (@) -> Missing
",
    );

    assert!(krate.diagnostics.iter().any(|d| d.code == "PGS-E2004"));
}

#[test]
fn pact_signature_accepts_self_without_e1209() {
    let krate = lower(
        r"
pact Node
    next = (@) -> Self
",
    );

    assert!(krate.diagnostics.is_empty(), "{:?}", krate.diagnostics);
}

#[test]
fn module_and_type_cannot_share_name() {
    let krate = lower(
        r"
scroll geometry
    origin = () -> Point
        Point(x: 0.0, y: 0.0)

rune geometry
    x: Float
",
    );

    assert!(krate.diagnostics.iter().any(|d| d.code == "PGS-E2005"));
}

#[test]
fn field_visibility_comes_from_unveil() {
    let krate = lower(
        r"
rune Point
    unveil x: Float
    y: Float
",
    );

    let fields: Vec<_> = krate
        .defs
        .iter()
        .filter(|d| d.kind == DefKind::Field && !krate.is_std_module(d.module))
        .collect();
    assert_eq!(fields.len(), 2);
    assert!(
        fields
            .iter()
            .any(|d| d.name == "x" && d.vis == Visibility::Public)
    );
    assert!(
        fields
            .iter()
            .any(|d| d.name == "y" && d.vis == Visibility::Private)
    );
}

#[test]
fn module_import_cycle_reports_e2012() {
    let krate = lower(
        r"
scroll a
    unveil rune Inner
        x: Int
    summon crate::Root

unveil rune Root
    x: Int

summon a::Inner
",
    );

    assert!(
        krate.diagnostics.iter().any(|d| d.code == "PGS-E2012"),
        "{:?}",
        krate.diagnostics
    );
}

#[test]
fn declaration_rune_method_signatures_are_resolved() {
    let parsed = parse_declaration_file(
        FileId::new(0),
        r#"
abi "C"
rune FILE
    read = (@) -> Missing
"#,
    );
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
    let file = parsed.file.unwrap();
    let lowered = lower_declaration(&file);
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-E2004"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn reference_field_uses_e3006() {
    let parsed = parse_program(FileId::new(0), "rune R\n    x: &Int\n");
    let program = parsed.program.expect("program");
    let lowered = lower_program(&program);
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-E3006"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn duplicate_variant_uses_e8004() {
    let parsed = parse_program(FileId::new(0), "enchanting E\n    A\n    A\n");
    let program = parsed.program.expect("program");
    let lowered = lower_program(&program);
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-E8004"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn duplicate_grimoire_uses_e2008() {
    let source = "grimoire\n    print(1)\n\ngrimoire\n    print(2)\n";
    let parsed = pengu_syntax::parse_program(pengu_span::DUMMY_FILE, source);
    let lowered = pengu_hir::lower_program(parsed.program.as_ref().unwrap());
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-E2008"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn ptr_in_field_uses_e2025() {
    let source = "rune Handle\n    raw: Ptr[Int]\n";
    let parsed = pengu_syntax::parse_program(pengu_span::DUMMY_FILE, source);
    let lowered = pengu_hir::lower_program(parsed.program.as_ref().unwrap());
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-E2025"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn primitive_ritual_outside_std_uses_e1210() {
    let source = "ritual Int\n    twice = (@) -> Int\n        @ * 2\n";
    let parsed = pengu_syntax::parse_program(pengu_span::DUMMY_FILE, source);
    let lowered = pengu_hir::lower_program(parsed.program.as_ref().unwrap());
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-E1210"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn missing_import_module_uses_e2003() {
    let source = "summon missing::Thing\n";
    let parsed = pengu_syntax::parse_program(pengu_span::DUMMY_FILE, source);
    let lowered = pengu_hir::lower_program(parsed.program.as_ref().unwrap());
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-E2003"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn recursive_alias_uses_e3009() {
    let source = "essence Loop = Loop\n";
    let parsed = pengu_syntax::parse_program(pengu_span::DUMMY_FILE, source);
    let lowered = pengu_hir::lower_program(parsed.program.as_ref().unwrap());
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-E3009"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn duplicate_test_uses_e1706() {
    let source = "@@test\nt = () -> Unit\n    return\n@@test\nt = () -> Unit\n    return\n";
    let parsed = pengu_syntax::parse_program(pengu_span::DUMMY_FILE, source);
    let lowered = pengu_hir::lower_program(parsed.program.as_ref().unwrap());
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-E1706"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn shadowed_local_uses_w1102() {
    let source = "f = () -> Unit\n    bind x = 1\n    bind x = 2\n    return\n";
    let parsed = pengu_syntax::parse_program(pengu_span::DUMMY_FILE, source);
    let lowered = pengu_hir::lower_program(parsed.program.as_ref().unwrap());
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-W1102"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn blanket_impl_uses_e1207() {
    let source =
        "pact Show\n    show = (@) -> String\nritual[T] T for Show\n    show = (@) -> String\n";
    let parsed = pengu_syntax::parse_program(pengu_span::DUMMY_FILE, source);
    let lowered = pengu_hir::lower_program(parsed.program.as_ref().unwrap());
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-E1207"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn unused_import_uses_w2001() {
    let source =
        "scroll geometry\n    unveil area = () -> Float\n        1.0\nsummon geometry::area\n";
    let parsed = pengu_syntax::parse_program(pengu_span::DUMMY_FILE, source);
    let lowered = pengu_hir::lower_program(parsed.program.as_ref().unwrap());
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-W2001"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn empty_pengu_abi_uses_e2024() {
    let source = "abi \"pengu\"\n";
    let parsed = pengu_syntax::parse_declaration_file(pengu_span::DUMMY_FILE, source);
    let lowered = pengu_hir::lower_declaration(parsed.file.as_ref().unwrap());
    assert!(
        lowered.diagnostics.iter().any(|d| d.code == "PGS-E2024"),
        "{:?}",
        lowered.diagnostics
    );
}

#[test]
fn binary_without_grimoire_uses_e2009() {
    let krate = lower("rune P\n    x: Int\n");
    let diagnostics = pengu_hir::check_binary(&krate);
    assert!(
        diagnostics.iter().any(|d| d.code == "PGS-E2009"),
        "{diagnostics:?}"
    );
}

#[test]
fn ritual_constants_are_registered() {
    let krate = lower(
        "rune Limits\n    unused: Int\n\nritual Limits\n    sigil MAXIMO: Int = 7\n    relic CACHE: Int = 9\n",
    );
    let consts = krate
        .assoc_consts
        .get("Limits")
        .expect("constantes de Limits");
    assert_eq!(consts.len(), 2);
    let names: Vec<&str> = consts
        .iter()
        .map(|def| krate.def(*def).name.as_str())
        .collect();
    assert!(names.contains(&"MAXIMO"), "{names:?}");
    assert!(names.contains(&"CACHE"), "{names:?}");
    let impls = krate
        .impls
        .iter()
        .find(|imp| imp.consts.len() == 2)
        .expect("impl con constantes");
    assert_eq!(impls.methods.len(), 0);
}
