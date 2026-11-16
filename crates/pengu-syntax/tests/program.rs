use pengu_span::FileId;
use pengu_syntax::ast::{ItemKind, Receiver, VariantFields, Visibility};
use pengu_syntax::parse_program;

fn parse(src: &str) -> pengu_syntax::ParsedProgram {
    parse_program(FileId::new(0), src)
}

fn assert_clean(src: &str) -> pengu_syntax::ParsedProgram {
    let parsed = parse(src);
    assert!(
        parsed.diagnostics.is_empty(),
        "diagnósticos: {:?}\nfuente:\n{src}",
        parsed.diagnostics
    );
    parsed
}

#[test]
fn items_accept_visibility_modes() {
    let parsed = assert_clean(
        "scroll geometry\n    unveil(tome) origin = () -> Point\n        Point(x: 0.0)\n    unveil(scroll) hidden = () -> Int\n        1\n",
    );
    let program = parsed.program.unwrap();
    let ItemKind::Scroll(scroll) = &program.items[0].kind else {
        panic!("se esperaba scroll");
    };
    assert_eq!(scroll.items[0].visibility, Visibility::Tome);
    assert_eq!(scroll.items[1].visibility, Visibility::Scroll);
}

#[test]
fn empty_program_is_clean() {
    let parsed = assert_clean("");
    assert_eq!(parsed.program.unwrap().items.len(), 0);
}

#[test]
fn summon_paths_and_aliases() {
    let parsed = assert_clean("summon std::fmt\nsummon std::io as io\n");
    let program = parsed.program.unwrap();
    assert_eq!(program.items.len(), 2);
    let ItemKind::Summon(summon) = &program.items[0].kind else {
        panic!("se esperaba summon");
    };
    assert_eq!(summon.path, ["std", "fmt"]);
    assert!(summon.alias.is_none());
    let ItemKind::Summon(alias) = &program.items[1].kind else {
        panic!("se esperaba summon");
    };
    assert_eq!(alias.alias.as_deref(), Some("io"));
}

#[test]
fn scroll_file_and_inline() {
    let parsed = assert_clean(
        "scroll geometry\nscroll algebra\n    summon std::math\n    rune Point\n        x: Float\n        y: Float\n",
    );
    let program = parsed.program.unwrap();
    assert_eq!(program.items.len(), 2);
    let ItemKind::Scroll(geometry) = &program.items[0].kind else {
        panic!("se esperaba scroll");
    };
    assert!(geometry.items.is_empty());
    let ItemKind::Scroll(algebra) = &program.items[1].kind else {
        panic!("se esperaba scroll");
    };
    assert_eq!(algebra.items.len(), 2);
}

#[test]
fn rune_fields_and_derive() {
    let parsed =
        assert_clean("@@derive(Debug, Clone)\nunveil rune Point[T]\n    unveil x: T\n    y: T\n");
    let program = parsed.program.unwrap();
    let item = &program.items[0];
    assert_eq!(item.derives, ["Debug", "Clone"]);
    let ItemKind::Rune(rune) = &item.kind else {
        panic!("se esperaba rune");
    };
    assert!(rune.unveil);
    assert_eq!(rune.name, "Point");
    assert_eq!(rune.params.len(), 1);
    assert_eq!(rune.fields.len(), 2);
    assert!(rune.fields[0].unveil);
}

#[test]
fn enchanting_variants() {
    let parsed = assert_clean(
        "@@derive(Debug)\nenchanting Shape\n    Circle(Float)\n    Rect(w: Float, h: Float)\n",
    );
    let program = parsed.program.unwrap();
    let ItemKind::Enchanting(e) = &program.items[0].kind else {
        panic!("se esperaba enchanting");
    };
    assert_eq!(e.variants.len(), 2);
    assert!(matches!(e.variants[0].fields, VariantFields::Tuple(_)));
    assert!(matches!(e.variants[1].fields, VariantFields::Named(_)));
}

#[test]
fn pact_methods_and_superpact() {
    let parsed = assert_clean(
        "pact Show: Display\n    show = (@) -> String\n    hidden = (@mut, n: Int) -> Unit\n        n = n\n",
    );
    let program = parsed.program.unwrap();
    let ItemKind::Pact(pact) = &program.items[0].kind else {
        panic!("se esperaba pact");
    };
    assert_eq!(
        pact.supertrait.as_deref(),
        Some(&["Display".to_owned()][..])
    );
    assert_eq!(pact.methods.len(), 2);
    assert!(pact.methods[0].body.is_none());
    assert_eq!(pact.methods[1].receiver, Receiver::Mut);
    assert!(pact.methods[1].body.is_some());
}

#[test]
fn ritual_methods_and_functions() {
    let parsed = assert_clean(
        "ritual Point for Show\n    len = (@) -> Float\n        0.0\n    origin = () -> Point\n        Point(x: 0.0, y: 0.0)\n",
    );
    let program = parsed.program.unwrap();
    let ItemKind::Ritual(ritual) = &program.items[0].kind else {
        panic!("se esperaba ritual");
    };
    assert_eq!(ritual.trait_path.as_deref(), Some(&["Show".to_owned()][..]));
    assert_eq!(ritual.items.len(), 2);
}

#[test]
fn essence_alias() {
    let parsed = assert_clean("unveil essence Meters = Float\n");
    let program = parsed.program.unwrap();
    let ItemKind::Essence(e) = &program.items[0].kind else {
        panic!("se esperaba essence");
    };
    assert_eq!(e.name, "Meters");
    assert!(e.unveil);
}

#[test]
fn foreign_block() {
    let parsed = assert_clean(
        "foreign \"C\"\n    cos = (x: Float) -> Float\n    puts = (s: Ptr[U8]) -> Int\n",
    );
    let program = parsed.program.unwrap();
    let ItemKind::Foreign(f) = &program.items[0].kind else {
        panic!("se esperaba foreign");
    };
    assert_eq!(f.abi, "C");
    assert_eq!(f.items.len(), 2);
}

#[test]
fn functions_consts_and_grimoire() {
    let parsed = assert_clean(
        "-- SAFETY: test\nunveil curse fast = (x: Int) -> Int\n    x + 1\nsigil LIMIT: Int = 10\nrelic NAME: String = \"pengu\"\ngrimoire: Result[Unit, String]\n    return ok(())\n",
    );
    let program = parsed.program.unwrap();
    assert_eq!(program.items.len(), 4);
    let ItemKind::Function(f) = &program.items[0].kind else {
        panic!("se esperaba función");
    };
    assert!(f.unveil);
    assert!(f.curse);
    assert!(matches!(program.items[1].kind, ItemKind::Const(_)));
    assert!(matches!(program.items[3].kind, ItemKind::Grimoire(_)));
}

#[test]
fn test_item_with_options() {
    let parsed = assert_clean(
        "@@test(should_panic: \"boom\", ignore: \"later\")\nworks = () -> Unit\n    assert(true)\n",
    );
    let program = parsed.program.unwrap();
    let ItemKind::Test(test) = &program.items[0].kind else {
        panic!("se esperaba test");
    };
    assert_eq!(test.options.len(), 2);
    assert_eq!(test.options[0].name, "should_panic");
    assert_eq!(test.options[1].message, "later");
}

#[test]
fn generic_function_and_scroll_nesting() {
    let parsed = assert_clean(
        "scroll algebra\n    identity = [T](x: T) -> T\n        x\n    scroll inner\n        summon std::fmt\n",
    );
    let program = parsed.program.unwrap();
    let ItemKind::Scroll(algebra) = &program.items[0].kind else {
        panic!("se esperaba scroll");
    };
    assert_eq!(algebra.items.len(), 2);
    let ItemKind::Function(f) = &algebra.items[0].kind else {
        panic!("se esperaba función");
    };
    assert_eq!(f.type_params.len(), 1);
}

#[test]
fn unveil_enchanting_with_derive_and_generic_essence() {
    let parsed = assert_clean(
        "@@derive(Debug)\nunveil enchanting Result[T, E]\n    Ok(T)\n    Err(E)\nunveil essence Pair[T] = (T, T)\nunveil show = (x: Int) -> Int\n    x\n",
    );
    let program = parsed.program.unwrap();
    let ItemKind::Enchanting(e) = &program.items[0].kind else {
        panic!("se esperaba enchanting");
    };
    assert!(e.unveil);
    assert_eq!(e.params.len(), 2);
    assert_eq!(program.items[0].derives, ["Debug"]);
    let ItemKind::Essence(alias) = &program.items[1].kind else {
        panic!("se esperaba essence");
    };
    assert_eq!(alias.params.len(), 1);
    let ItemKind::Function(f) = &program.items[2].kind else {
        panic!("se esperaba función");
    };
    assert!(f.unveil);
}

#[test]
fn curse_function_without_unveil() {
    let parsed = assert_clean("-- SAFETY: test\ncurse raw = (p: Ptr[U8]) -> Int\n    0\n");
    let program = parsed.program.unwrap();
    let ItemKind::Function(f) = &program.items[0].kind else {
        panic!("se esperaba función");
    };
    assert!(f.curse);
    assert!(!f.unveil);
}

#[test]
fn comments_between_items_and_inside_blocks() {
    let parsed = assert_clean(
        "-- cabecera\nscroll a\n    -- dentro\n    rune A\n        -- campo\n        x: Int\n-- fin\n",
    );
    let program = parsed.program.unwrap();
    assert_eq!(program.items.len(), 1);
}
