//! Corpus de cabeceras reales: el declarado generado pasa el pipeline.

#![cfg(unix)]

use std::path::{Path, PathBuf};

struct Case {
    header: &'static str,
    link: &'static str,
    min_functions: usize,
    min_records: usize,
}

const CASES: &[Case] = &[
    Case {
        header: "/usr/include/zlib.h",
        link: "z",
        min_functions: 20,
        min_records: 1,
    },
    Case {
        header: "/usr/include/sqlite3.h",
        link: "sqlite3",
        min_functions: 150,
        min_records: 5,
    },
    Case {
        header: "/usr/include/stdio.h",
        link: "c",
        min_functions: 5,
        min_records: 0,
    },
];

fn project(name: &str) -> PathBuf {
    let stamp = format!(
        "{}_{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    );
    let dir = std::env::temp_dir().join(format!("{name}-{stamp}"));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

fn generate(header: &Path) -> pengu_bindgen::Generated {
    pengu_bindgen::generate(header, &pengu_bindgen::Options::default())
        .unwrap_or_else(|error| panic!("{}: {error}", header.display()))
}

#[test]
fn las_cabeceras_reales_generan_declarados_validos() {
    for case in CASES {
        let header = Path::new(case.header);
        if !header.exists() {
            eprintln!("omitido: {} no está instalada", case.header);
            continue;
        }
        let generated = generate(header);
        let report = &generated.report;
        assert!(
            report.functions >= case.min_functions,
            "{}: solo {} funciones ({})",
            case.header,
            report.functions,
            generated.source.len()
        );
        assert!(
            report.records >= case.min_records,
            "{}: solo {} estructuras",
            case.header,
            report.records
        );
        assert!(
            generated
                .source
                .starts_with("-- Generado por `pengu bindgen`")
        );

        let root = project("pengu-bindgen-real");
        std::fs::write(root.join("api.d.pengu"), &generated.source).unwrap();
        std::fs::write(
            root.join("Tome.toml"),
            format!(
                "[tome]\nname = \"api\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"api\"\n\n[link]\n{}\n\n[declarations]\napi = \"api.d.pengu\"\n",
                case.link
            ),
        )
        .unwrap();
        std::fs::write(root.join("main.pengu"), "grimoire\n    print(1)\n").unwrap();
        let report = pengu_build::check(&root);
        let errors: Vec<_> = report
            .diagnostics
            .iter()
            .filter(|diagnostic| diagnostic.is_error())
            .collect();
        assert!(
            errors.is_empty(),
            "{}: {} errores, primero {:?}",
            case.header,
            errors.len(),
            errors.first()
        );
    }
}

#[test]
fn el_ejemplo_de_zlib_usa_la_biblioteca_real() {
    let header = Path::new("/usr/include/zlib.h");
    if !header.exists() {
        eprintln!("omitido: zlib no está instalada");
        return;
    }
    let root = project("pengu-bindgen-zlib");
    let generated = generate(header);
    std::fs::write(root.join("zlib.d.pengu"), &generated.source).unwrap();
    std::fs::write(
        root.join("Tome.toml"),
        "[tome]\nname = \"zlib-demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"zlib-demo\"\n\n[link]\nz\n\n[declarations]\nzlib = \"zlib.d.pengu\"\n",
    )
    .unwrap();
    let example = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../examples/zlib.pengu");
    std::fs::copy(&example, root.join("main.pengu")).unwrap();
    let report = pengu_build::run(&root);
    let report = report.expect("pipeline");
    assert!(
        report
            .diagnostics
            .iter()
            .all(|diagnostic| !diagnostic.is_error()),
        "{:?}",
        report.diagnostics
    );
    let output = report.output.expect("ejecutado");
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.starts_with("1."), "{stdout}");
}
