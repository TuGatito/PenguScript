use std::path::PathBuf;
use std::process::Command;

use pengu_codegen::SourceMap;
use pengu_span::{FileId, Span};

fn project(name: &str, source: &str) -> PathBuf {
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
    std::fs::write(
        dir.join("Tome.toml"),
        "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\n",
    )
    .unwrap();
    std::fs::write(dir.join("main.pengu"), source).unwrap();
    dir
}

#[test]
fn remapea_un_mensaje_con_span() {
    let mut sourcemap = SourceMap::default();
    sourcemap.push(3, Span::new(FileId::new(0), 10, 20));
    let line = r#"{"reason":"compiler-message","message":{"level":"error","message":"mismatched types","code":{"code":"E0308"},"spans":[{"file_name":"src/main.rs","line_start":3,"column_start":7,"is_primary":true}],"rendered":"error[E0308]: mismatched types\n --> src/main.rs:3:7"}}"#;
    let diagnostics = pengu_build::remap_rustc_diagnostics(line, &sourcemap);
    assert_eq!(diagnostics.len(), 1);
    assert!(diagnostics[0].message.contains("E0308"));
    assert!(diagnostics[0].message.contains("mismatched types"));
    assert_eq!(diagnostics[0].primary, Span::new(FileId::new(0), 10, 20));
    assert!(
        diagnostics[0]
            .notes
            .iter()
            .any(|note| note.contains("generado en `src/main.rs:3:7`"))
    );
}

#[test]
fn sin_span_conserva_el_texto_y_lo_anota() {
    let sourcemap = SourceMap::default();
    let line = r#"{"reason":"compiler-message","message":{"level":"error","message":"cannot find value `x` in this scope","code":{"code":"E0425"},"spans":[],"rendered":"error[E0425]: cannot find value `x`"}}"#;
    let diagnostics = pengu_build::remap_rustc_diagnostics(line, &sourcemap);
    assert_eq!(diagnostics.len(), 1);
    assert!(diagnostics[0].message.contains("E0425"));
    assert!(
        diagnostics[0]
            .notes
            .iter()
            .any(|note| note.contains("sin ubicación en el código generado"))
    );
}

#[test]
fn ignora_avisos_y_lineas_que_no_son_compiler_message() {
    let sourcemap = SourceMap::default();
    let warning = r#"{"reason":"compiler-message","message":{"level":"warning","message":"unused","spans":[]}}"#;
    let artifact = r#"{"reason":"compiler-artifact","package_id":"demo"}"#;
    let garbage = "error: something went wrong";
    let output = format!("{warning}\n{artifact}\n{garbage}");
    assert!(pengu_build::remap_rustc_diagnostics(&output, &sourcemap).is_empty());
}

#[test]
fn no_duplica_el_mismo_error() {
    let mut sourcemap = SourceMap::default();
    sourcemap.push(1, Span::new(FileId::new(0), 0, 4));
    let line = r#"{"reason":"compiler-message","message":{"level":"error","message":"boom","code":{"code":"E0001"},"spans":[{"file_name":"src/main.rs","line_start":1,"column_start":1}],"rendered":"error[E0001]: boom"}}"#;
    let output = format!("{line}\n{line}");
    assert_eq!(
        pengu_build::remap_rustc_diagnostics(&output, &sourcemap).len(),
        1
    );
}

#[test]
fn remapea_un_error_real_de_rustc() {
    let root = project("pengu-remap", "grimoire\n    print(1)\n");
    let result = pengu_build::compile(&root);
    assert!(result.is_clean(), "{:?}", result.diagnostics);

    // Se inyecta un error de tipos al final del Rust generado y se compila: el
    // remapeador debe conservar el texto real de rustc y anotar la ubicación.
    let mut rust = result.rust.clone();
    rust.push_str("\nfn __roto() { let x: i32 = \"a\"; }\n");
    let dir = root.join("injected");
    std::fs::create_dir_all(dir.join("src")).unwrap();
    std::fs::write(dir.join("src/main.rs"), rust).unwrap();
    std::fs::write(
        dir.join("Cargo.toml"),
        "[package]\nname = \"injected\"\nversion = \"0.1.0\"\nedition = \"2024\"\n",
    )
    .unwrap();
    let output = Command::new("cargo")
        .args(["build", "--quiet", "--message-format=json"])
        .arg("--manifest-path")
        .arg(dir.join("Cargo.toml"))
        .output()
        .unwrap();
    let text = format!(
        "{}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    let diagnostics = pengu_build::remap_rustc_diagnostics(&text, &result.sourcemap);
    assert!(!diagnostics.is_empty(), "no se remapeó ningún error");
    assert!(
        diagnostics
            .iter()
            .any(|diagnostic| diagnostic.message.contains("E0308")),
        "{:?}",
        diagnostics
    );
    assert!(
        diagnostics.iter().any(|diagnostic| diagnostic
            .notes
            .iter()
            .any(|note| note.contains("generado en `src/main.rs:"))),
        "{:?}",
        diagnostics
    );
}
