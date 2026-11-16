use pengu_span::FileId;
use pengu_syntax::ast::ItemKind;
use pengu_syntax::parse_declaration_file;

fn assert_clean(src: &str) -> pengu_syntax::ParsedDeclaration {
    let parsed = parse_declaration_file(FileId::new(0), src);
    assert!(
        parsed.diagnostics.is_empty(),
        "diagnósticos: {:?}\nfuente:\n{src}",
        parsed.diagnostics
    );
    parsed
}

#[test]
fn declaration_file_with_all_item_kinds() {
    let parsed = assert_clean(
        "abi \"C\"\nsummon std::ffi\nrune FILE\n    fd: Int\n    close = (@) -> Int\nenchanting Kind\n    A\n    B(Int)\npact Reader\n    read = (@, n: Int) -> Vec[U8]\nopen = (path: Ptr[U8]) -> Int\nVERSION: Int\n",
    );
    let file = parsed.file.unwrap();
    assert_eq!(file.abi, "C");
    assert_eq!(file.items.len(), 6);
    let ItemKind::Rune(rune) = &file.items[1].kind else {
        panic!("se esperaba rune");
    };
    assert_eq!(rune.fields.len(), 1);
    assert_eq!(rune.methods.len(), 1);
    assert!(rune.methods[0].body.is_none());
    let ItemKind::Pact(pact) = &file.items[3].kind else {
        panic!("se esperaba pact");
    };
    assert_eq!(pact.methods.len(), 1);
    let ItemKind::FunctionSig(sig) = &file.items[4].kind else {
        panic!("se esperaba firma");
    };
    assert_eq!(sig.name, "open");
    let ItemKind::Const(k) = &file.items[5].kind else {
        panic!("se esperaba const");
    };
    assert!(k.value.is_none());
}

#[test]
fn declaration_file_accepts_libc_header() {
    let parsed = assert_clean(
        "abi \"C\"\nsummon std::ffi::CStr\nrune FILE\n    _private: [U8; 0]\nputs = (text: &CStr) -> Int\nfopen = (path: &CStr, mode: &CStr) -> Ptr[FILE]\nfclose = (file: Ptr[FILE]) -> Int\n",
    );
    let file = parsed.file.unwrap();
    assert_eq!(file.abi, "C");
    assert_eq!(file.items.len(), 5);
    let ItemKind::Rune(rune) = &file.items[1].kind else {
        panic!("se esperaba rune");
    };
    assert_eq!(rune.fields.len(), 1);
    let ItemKind::FunctionSig(f) = &file.items[2].kind else {
        panic!("se esperaba firma");
    };
    assert_eq!(f.name, "puts");
}

#[test]
fn declaration_file_rejects_bodies() {
    let parsed = parse_declaration_file(FileId::new(0), "abi \"C\"\nopen = () -> Int\n    1\n");
    assert!(!parsed.diagnostics.is_empty());
}

#[test]
fn declaration_without_abi_uses_e2020() {
    let parsed = parse_declaration_file(FileId::new(0), "rune X\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E2020"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn declaration_with_sigil_uses_e2021() {
    let parsed = parse_declaration_file(FileId::new(0), "abi \"C\"\n\nsigil X: Int = 1\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E2021"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn js_abi_uses_e2022() {
    let parsed = parse_declaration_file(FileId::new(0), "abi \"js\"\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E2022"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn declaration_with_unveil_uses_e2027() {
    let parsed = parse_declaration_file(FileId::new(0), "abi \"C\"\n\nunveil rune X\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E2027"),
        "{:?}",
        parsed.diagnostics
    );
}

#[test]
fn grimoire_in_declaration_uses_e2026() {
    let parsed = parse_declaration_file(FileId::new(0), "abi \"C\"\n\ngrimoire\n");
    assert!(
        parsed.diagnostics.iter().any(|d| d.code == "PGS-E2026"),
        "{:?}",
        parsed.diagnostics
    );
}
