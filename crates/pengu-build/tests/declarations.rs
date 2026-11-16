//! Pruebas de `[declarations]`: archivos `.d.pengu` como módulos del programa.

#![cfg(unix)]

use std::path::{Path, PathBuf};

fn project(name: &str, manifest_extra: &str, source: &str) -> PathBuf {
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
        format!(
            "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\n{manifest_extra}"
        ),
    )
    .unwrap();
    std::fs::write(dir.join("main.pengu"), source).unwrap();
    dir
}

fn write_declaration(root: &Path, source: &str) {
    std::fs::write(root.join("libc.d.pengu"), source).unwrap();
}

const DECLARATION: &str = "abi \"C\"\n\nstrlen = (text: &CStr) -> Usize\n";

const PROGRAM: &str = r#"summon std::ffi
summon libc::strlen

-- SAFETY: `value` vive hasta el final de la llamada y `strlen` no la guarda.
length_raw = (value: &CString) -> Usize
    curse
        strlen(&value)

grimoire
    bind created = ffi.cstring_new("hola")
    bind largo = match created
        when some(value) then
            curse
                length_raw(&value)
        when none then 0
    print(largo)
"#;

#[test]
fn las_declaraciones_se_cargan_y_ejecutan() {
    let root = project(
        "pengu-decl-run",
        "\n[link]\nc\n\n[declarations]\nlibc = \"libc.d.pengu\"\n",
        PROGRAM,
    );
    write_declaration(&root, DECLARATION);
    let report = pengu_build::run(&root).unwrap();
    assert!(report.success(), "{:?}", report.diagnostics);
    let output = report.output.expect("el binario se ejecutó");
    assert_eq!(String::from_utf8_lossy(&output.stdout), "4\n");
}

#[test]
fn una_declaracion_sin_link_es_un_error() {
    let root = project(
        "pengu-decl-link",
        "\n[declarations]\nlibc = \"libc.d.pengu\"\n",
        PROGRAM,
    );
    write_declaration(&root, DECLARATION);
    let report = pengu_build::check(&root);
    let message = report
        .diagnostics
        .iter()
        .find(|diagnostic| diagnostic.code == "PGS-E2023")
        .map(|diagnostic| diagnostic.message.clone())
        .unwrap_or_default();
    assert!(message.contains("libc"), "{:?}", report.diagnostics);
    assert!(message.contains("[link]"), "{:?}", report.diagnostics);
}

#[test]
fn un_tipo_no_representable_es_un_error() {
    let root = project(
        "pengu-decl-ffi",
        "\n[link]\nc\n\n[declarations]\nlibc = \"libc.d.pengu\"\n",
        "grimoire\n    print(1)\n",
    );
    write_declaration(&root, "abi \"C\"\n\nroto = (text: String) -> Int\n");
    let report = pengu_build::check(&root);
    assert!(
        report
            .diagnostics
            .iter()
            .any(|diagnostic| diagnostic.code == "PGS-E1604"),
        "{:?}",
        report.diagnostics
    );
}

#[test]
fn una_declaracion_inexistente_se_reporta() {
    let root = project(
        "pengu-decl-missing",
        "\n[declarations]\nlibc = \"no-existe.d.pengu\"\n",
        "grimoire\n    print(1)\n",
    );
    let report = pengu_build::check(&root);
    assert!(
        report
            .diagnostics
            .iter()
            .any(|diagnostic| diagnostic.code == "PGS-E2003"),
        "{:?}",
        report.diagnostics
    );
}

#[test]
fn un_nombre_con_punto_no_es_un_modulo() {
    let root = project(
        "pengu-decl-name",
        "\n[link]\nc\n\n[declarations]\n\"libc.x\" = \"libc.d.pengu\"\n",
        "grimoire\n    print(1)\n",
    );
    write_declaration(&root, DECLARATION);
    let report = pengu_build::check(&root);
    assert!(
        !report.is_clean(),
        "una declaración con punto no puede ser un módulo"
    );
}

#[test]
fn un_path_de_modulo_no_es_un_valor() {
    let root = project(
        "pengu-decl-vis",
        "\n[link]\nc\n\n[declarations]\nlibc = \"libc.d.pengu\"\n",
        "grimoire\n    print(libc.strlen)\n",
    );
    write_declaration(&root, DECLARATION);
    let report = pengu_build::check(&root);
    assert!(!report.is_clean(), "el path no es una expresión válida");
}
