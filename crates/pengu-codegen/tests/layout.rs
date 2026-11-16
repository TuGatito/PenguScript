//! Verificación del motor de layout contra `rustc`.
//!
//! El backend emite `#[repr(C)]`/`#[repr(C, u32)]`/`#[repr(u32)]` justamente
//! para que el layout sea calculable. Este test cierra el círculo: compila el
//! Rust real del compilador e imprime `size_of`/`align_of`, y compara con
//! `pengu_layout::layout_of`. Una divergencia rompe la suite.

use std::fmt::Write as _;
use std::process::Command;

use pengu_codegen::generate;
use pengu_hir::lower_program;
use pengu_lir::lower_crate;
use pengu_span::FileId;
use pengu_syntax::parse_program;
use pengu_types::{Ty, check_crate};

const SOURCE: &str = r#"rune Point
    x: Int
    y: Int

rune Mixed
    flag: Bool
    big: I64
    small: U8

rune Nested
    point: Point
    label: String
    maybe: Option[Point]

rune Holder[T]
    first: T
    second: U8

enchanting Shape
    Circle(Float)
    Rect(Point)
    Empty

enchanting Flag
    A
    B
    C

enchanting Payload
    Big(I64)
    Tiny
"#;

fn build() -> (
    pengu_hir::HirCrate,
    Vec<(String, pengu_hir::DefId, Vec<Ty>)>,
) {
    let parsed = parse_program(FileId::new(0), SOURCE);
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
    let program = parsed.program.expect("programa");
    let lowered = lower_program(&program);
    assert!(lowered.diagnostics.is_empty(), "{:?}", lowered.diagnostics);
    let krate = lowered.krate;
    let types = check_crate(&krate);
    assert!(types.is_clean(), "{:?}", types.diagnostics);
    let lir = lower_crate(&krate, &types);
    assert!(lir.diagnostics.is_empty(), "{:?}", lir.diagnostics);
    let generated = generate(&krate, &lir);
    assert!(
        generated.diagnostics.is_empty(),
        "{:?}",
        generated.diagnostics
    );

    let mut defs: Vec<(String, pengu_hir::DefId, Vec<Ty>)> = krate
        .adts
        .iter()
        .filter(|(def, _)| krate.def(**def).module == krate.root)
        .map(|(def, adt)| {
            let args = if adt.generics.is_empty() {
                Vec::new()
            } else {
                vec![Ty::Int; adt.generics.len()]
            };
            (krate.def(*def).name.clone(), *def, args)
        })
        .collect();
    defs.sort_by(|left, right| left.0.cmp(&right.0));

    let mut probe = String::from("\nfn main() {\n");
    let mut rust_type = String::new();
    for (name, def, args) in &defs {
        let adt = krate.adt(*def).expect("adt");
        rust_type.clear();
        let _ = write!(rust_type, "crate::{name}");
        if !adt.generics.is_empty() {
            rust_type.push('<');
            for (index, arg) in args.iter().enumerate() {
                if index > 0 {
                    rust_type.push_str(", ");
                }
                rust_type.push_str(&rust_type_name(arg));
            }
            rust_type.push('>');
        }
        let _ = writeln!(
            probe,
            "    println!(\"{name}\\t{{}}\\t{{}}\", ::std::mem::size_of::<{rust_type}>(), ::std::mem::align_of::<{rust_type}>());"
        );
    }
    probe.push_str("}\n");

    let file = std::env::temp_dir().join(format!(
        "pengu-layout-{}_{}.rs",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::write(&file, format!("{}{probe}", generated.source)).unwrap();
    let binary = file.with_extension("bin");
    let output = Command::new("rustc")
        .args(["--edition", "2024"])
        .arg(&file)
        .arg("-o")
        .arg(&binary)
        .output()
        .expect("rustc");
    assert!(
        output.status.success(),
        "rustc falló\n--- probe ---\n{probe}\n--- stderr ---\n{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let run = Command::new(&binary).output().expect("ejecutar");
    assert!(run.status.success());
    let stdout = String::from_utf8(run.stdout).unwrap();
    let _ = std::fs::remove_file(&file);
    let _ = std::fs::remove_file(&binary);

    for (name, def, args) in &defs {
        let Some(line) = stdout
            .lines()
            .find(|line| line.split('\t').next() == Some(name.as_str()))
        else {
            panic!("falla el sondeo de `{name}`: {stdout}");
        };
        let mut parts = line.split('\t').skip(1);
        let size: usize = parts.next().expect("size").parse().expect("número");
        let align: usize = parts.next().expect("align").parse().expect("número");
        let layout = pengu_layout::layout_of_adt(*def, args, &krate)
            .unwrap_or_else(|| panic!("sin layout para `{name}`"));
        assert_eq!(
            (layout.size, layout.align),
            (size, align),
            "`{name}`: el motor dice {layout:?} y rustc {size}/{align}"
        );
    }
    (krate, defs)
}

fn rust_type_name(ty: &Ty) -> String {
    match ty {
        Ty::Int => "i32".to_owned(),
        Ty::Bool => "bool".to_owned(),
        Ty::I64 => "i64".to_owned(),
        Ty::Char => "char".to_owned(),
        Ty::String => "String".to_owned(),
        Ty::Str => "&str".to_owned(),
        _ => panic!("tipo sin nombre Rust en el test: {ty:?}"),
    }
}

#[test]
fn el_layout_coincide_con_rustc() {
    let (krate, defs) = build();
    assert!(!defs.is_empty());
    // Un ADT recursivo por `Vec` sigue siendo calculable.
    assert!(pengu_layout::layout_of(&Ty::Vec(Box::new(Ty::Int)), &krate).is_some());
}

#[test]
fn option_coincide_con_rustc() {
    let (krate, defs) = build();
    for (name, def, args) in &defs {
        let adt = krate.adt(*def).expect("adt");
        if !adt.generics.is_empty() {
            continue;
        }
        let ty = Ty::Adt(*def, args.clone());
        let inner = pengu_layout::layout_of(&ty, &krate).expect("layout");
        let option = pengu_layout::layout_of(&Ty::Option(Box::new(ty)), &krate).expect("layout");
        let expected = if inner.niche {
            inner.size
        } else {
            pengu_layout::align_to(inner.size, inner.align) + inner.align
        };
        assert_eq!(option.size, expected, "`Option[{name}]` no cuadra");
    }
}
