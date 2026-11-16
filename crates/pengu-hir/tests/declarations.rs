//! Las declaraciones `.d.pengu` se bajan como módulos con firmas `foreign`.

use pengu_hir::{DefKind, lower_program_with_declarations};
use pengu_span::FileId;
use pengu_syntax::{parse_declaration_file, parse_program};

const DECLARATION: &str = "abi \"C\"\n\nstrlen = (text: &CStr) -> Usize\n";

#[test]
fn la_declaracion_es_un_modulo_con_firmas_foreign() {
    let source = "summon libc::strlen\n\ngrimoire\n    print(1)\n";
    let program = parse_program(FileId::new(0), source)
        .program
        .expect("parsea");
    let declaration = parse_declaration_file(FileId::new(0x3E00_0000), DECLARATION)
        .file
        .expect("parsea la declaración");
    let lowered = lower_program_with_declarations(&program, &[("libc".to_owned(), declaration)]);
    assert!(
        lowered
            .diagnostics
            .iter()
            .all(|diagnostic| !diagnostic.is_error()),
        "{:?}",
        lowered.diagnostics
    );
    let krate = &lowered.krate;
    let module = krate
        .modules
        .iter()
        .find(|module| module.name == "libc")
        .expect("el módulo de la declaración existe");
    assert_eq!(
        krate.def(module.def.expect("tiene def")).kind,
        DefKind::Module
    );
    let strlen = krate
        .defs
        .iter()
        .find(|def| def.name == "strlen" && def.module == module.id)
        .expect("la función declarada existe");
    assert!(krate.foreign_fns.contains(&strlen.id));
    assert_eq!(
        krate.foreign_abis.get(&strlen.id).map(String::as_str),
        Some("C")
    );
    assert!(krate.signature(strlen.id).is_some());
}
