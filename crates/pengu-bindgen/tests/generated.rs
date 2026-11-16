//! El `.d.pengu` generado compila y se usa desde un programa real.

#![cfg(unix)]

use std::path::{Path, PathBuf};

const HEADER: &str = r"typedef struct { int x; int y; } Point;
struct Node { const char *name; struct Node *next; double weight; unsigned flags; };
enum Mode { MODE_A = 0, MODE_B = 1, MODE_C = 4 };
extern int puts(const char *text);
extern unsigned long strlen(const char *text);
";

const PROGRAM: &str = r#"summon std::ffi
summon libc::puts

-- SAFETY: `value` vive hasta el final de la llamada y `puts` no lo guarda.
saluda = (text: &Str) -> Int
    bind value = match ffi.cstring_new(text)
        when some(value) then value
        when none then
            return -1
    curse
        puts(ffi.cstring_as_c_str(&value))

grimoire
    print(saluda("desde C") >= 0)
"#;

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

fn header_file(dir: &Path) -> PathBuf {
    let path = dir.join("libc.h");
    std::fs::write(&path, HEADER).unwrap();
    path
}

#[test]
fn el_declarado_generado_compila_y_corre() {
    let root = project("pengu-bindgen-e2e");
    let header = header_file(&root);
    let options = pengu_bindgen::Options::default();
    let generated = pengu_bindgen::generate(&header, &options).expect("clang disponible");
    assert!(generated.source.contains("rune Node"));
    assert!(generated.source.contains("next: Ptr[Node]"));
    assert!(generated.source.contains("MODE_C: Int = 4"));
    assert!(generated.source.contains("puts = (text: &CStr) -> Int"));
    assert!(generated.source.contains("strlen = (text: &CStr) -> "));
    std::fs::write(root.join("libc.d.pengu"), &generated.source).unwrap();
    std::fs::write(
        root.join("Tome.toml"),
        "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\n\n[link]\nc\n\n[declarations]\nlibc = \"libc.d.pengu\"\n",
    )
    .unwrap();
    std::fs::write(root.join("main.pengu"), PROGRAM).unwrap();
    let report = pengu_build::run(&root).unwrap();
    assert!(report.success(), "{:?}", report.diagnostics);
    let output = report.output.expect("el binario se ejecutó");
    assert_eq!(String::from_utf8_lossy(&output.stdout), "true\ndesde C\n");
}

#[test]
fn el_reporte_cuenta_los_generados() {
    let root = project("pengu-bindgen-report");
    let header = header_file(&root);
    let generated = pengu_bindgen::generate(&header, &pengu_bindgen::Options::default())
        .expect("clang disponible");
    assert_eq!(generated.report.functions, 2);
    assert_eq!(generated.report.records, 2);
    assert_eq!(generated.report.constants, 3);
    assert!(generated.report.is_complete(), "{:?}", generated.report);
    assert!(generated.header.ends_with("libc.h"));
}

#[test]
fn la_salida_es_determinista() {
    let root = project("pengu-bindgen-stable");
    let header = header_file(&root);
    let options = pengu_bindgen::Options::default();
    let first = pengu_bindgen::generate(&header, &options).expect("clang disponible");
    let second = pengu_bindgen::generate(&header, &options).expect("clang disponible");
    assert_eq!(first.source, second.source);
}
