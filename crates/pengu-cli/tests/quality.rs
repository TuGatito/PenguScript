//! Pruebas de extremo a extremo de `pengu fmt`, `pengu lint` y `pengu explain`.

#![allow(clippy::missing_panics_doc, clippy::unwrap_used)]

use std::path::{Path, PathBuf};
use std::process::{Command, Output};

fn binary() -> &'static str {
    env!("CARGO_BIN_EXE_pengu")
}

struct Project {
    root: PathBuf,
}

impl Project {
    fn new(name: &str) -> Self {
        let root = std::env::temp_dir().join(format!(
            "pengu-quality-{}-{name}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&root).unwrap();
        std::fs::write(
            root.join("Tome.toml"),
            "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\npath = \"main.pengu\"\n",
        )
        .unwrap();
        Self { root }
    }

    fn write(&self, file: &str, contents: &str) {
        std::fs::write(self.root.join(file), contents).unwrap();
    }

    fn read(&self, file: &str) -> String {
        std::fs::read_to_string(self.root.join(file)).unwrap()
    }

    fn run(&self, args: &[&str]) -> Output {
        Command::new(binary())
            .args(args)
            .current_dir(&self.root)
            .env("PENGU_HOME", self.root.join("home"))
            .output()
            .unwrap()
    }
}

impl Drop for Project {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.root);
    }
}

fn stdout(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

fn exists(path: &Path) -> bool {
    path.exists()
}

#[test]
fn fmt_formatea_y_check_no_escribe() {
    let project = Project::new("fmt");
    let source = "f = ( x :Int ) -> Int\n    g ( x )\n";
    project.write("main.pengu", source);

    let check = project.run(&["fmt", "--check"]);
    assert_eq!(check.status.code(), Some(1), "{}", stderr(&check));
    assert!(stdout(&check).contains("main.pengu:1:"));
    assert_eq!(
        project.read("main.pengu"),
        source,
        "`--check` no debe escribir"
    );

    let format = project.run(&["fmt"]);
    assert_eq!(format.status.code(), Some(0), "{}", stderr(&format));
    assert!(stdout(&format).contains("formateado"));
    assert_eq!(
        project.read("main.pengu"),
        "f = (x: Int) -> Int\n    g(x)\n"
    );

    let clean = project.run(&["fmt", "--check"]);
    assert_eq!(clean.status.code(), Some(0), "{}", stderr(&clean));
}

#[test]
fn fmt_rechaza_archivos_que_no_compilan() {
    let project = Project::new("fmt-error");
    project.write("malo.pengu", "\tx = 1\n");
    let output = project.run(&["fmt", "malo.pengu"]);
    assert_eq!(output.status.code(), Some(1));
    assert!(stderr(&output).contains("PGS-E1805"));
}

#[test]
fn lint_avisa_sin_fallar_y_deny_falla() {
    let project = Project::new("lint");
    project.write(
        "main.pengu",
        "summon std::via\n\nf = () -> Int\n    bind sobra = 1\n    2\n",
    );
    let output = project.run(&["lint"]);
    assert_eq!(output.status.code(), Some(0), "{}", stderr(&output));
    let text = stdout(&output);
    assert!(text.contains("PGS-W2001"), "{text}");
    assert!(text.contains("PGS-W1101"), "{text}");
    assert!(text.contains("ayuda:"), "{text}");

    let denied = project.run(&["lint", "--deny", "PGS-W2001"]);
    assert_eq!(denied.status.code(), Some(1), "{}", stderr(&denied));
    assert!(stdout(&denied).contains("error PGS-W2001"));

    let allowed = project.run(&["lint", "--allow", "PGS-W2001", "--allow", "PGS-W1101"]);
    assert_eq!(allowed.status.code(), Some(0));
    assert_eq!(stdout(&allowed).len(), 0);
}

#[test]
fn lint_lista_el_catalogo_y_rechaza_codigos_desconocidos() {
    let project = Project::new("lint-list");
    project.write("main.pengu", "f = () -> Int\n    1\n");
    let list = project.run(&["lint", "--list"]);
    assert_eq!(list.status.code(), Some(0));
    let text = stdout(&list);
    assert!(text.contains("PGS-W1101"), "{text}");
    assert!(text.contains("PGS-W9001"), "{text}");

    let unknown = project.run(&["lint", "--deny", "PGS-W9999"]);
    assert_eq!(unknown.status.code(), Some(2));
    assert!(stderr(&unknown).contains("no existe el lint"));
    assert!(exists(&project.root));
}

#[test]
fn explain_muestra_la_descripcion_del_codigo() {
    let project = Project::new("explain");
    let output = project.run(&["explain", "PGS-W1102"]);
    assert_eq!(output.status.code(), Some(0), "{}", stderr(&output));
    assert!(stdout(&output).contains("Sombreado"));

    let unknown = project.run(&["explain", "PGS-X0000"]);
    assert_eq!(unknown.status.code(), Some(1));
    assert!(stderr(&unknown).contains("no aparece"));
}

#[test]
fn fix_aplica_correcciones_seguras() {
    let project = Project::new("fix");
    let before = "summon std::via\n\nf = () -> Int\n    return 1\n    2\n";
    project.write("main.pengu", before);

    let dry = project.run(&["fix", "--dry-run"]);
    assert_eq!(dry.status.code(), Some(1), "{}", stderr(&dry));
    assert!(stdout(&dry).contains("simulado"));
    assert_eq!(project.read("main.pengu"), before);

    let applied = project.run(&["fix"]);
    assert_eq!(applied.status.code(), Some(0), "{}", stderr(&applied));
    let after = project.read("main.pengu");
    assert!(!after.contains("summon std::via"), "{after}");
    assert!(
        !after.contains("2\n") || after.contains("return 1"),
        "{after}"
    );

    let lint = project.run(&["lint"]);
    assert!(!stdout(&lint).contains("PGS-W2001"), "{}", stdout(&lint));
}

#[test]
fn doc_genera_markdown_y_abre_sin_error() {
    let project = Project::new("doc");
    project.write(
        "main.pengu",
        "--- Suma dos enteros.\nsuma = (a: Int, b: Int) -> Int\n    a + b\n",
    );
    let output = project.run(&["doc"]);
    assert_eq!(output.status.code(), Some(0), "{}", stderr(&output));
    let path = stdout(&output).trim().to_owned();
    assert!(path.ends_with("demo.md"), "{path}");
    let markdown = std::fs::read_to_string(&path).unwrap();
    assert!(markdown.contains("# demo v0.1.0"), "{markdown}");
    assert!(markdown.contains("Suma dos enteros."), "{markdown}");
    assert!(
        markdown.contains("suma = (a: Int, b: Int) -> Int"),
        "{markdown}"
    );
}

#[test]
fn test_doc_ejecuta_los_bloques_de_la_documentacion() {
    let project = Project::new("doctest");
    project.write(
        "main.pengu",
        "--- Suma.\n--- ```pengu\n--- bind total = suma(2, 3)\n--- print(total)\n--- ```\nsuma = (a: Int, b: Int) -> Int\n    a + b\n",
    );
    let output = project.run(&["test", "--doc"]);
    let text = stdout(&output);
    assert_eq!(output.status.code(), Some(0), "{}", stderr(&output));
    assert!(text.contains("1 passed"), "{text}");
}

#[test]
fn bench_mide_las_etapas() {
    let project = Project::new("bench");
    project.write("main.pengu", "f = () -> Int\n    1\n");
    let output = project.run(&["bench", "--iterations", "1"]);
    assert_eq!(output.status.code(), Some(0), "{}", stderr(&output));
    let text = stdout(&output);
    assert!(text.contains("etapas"), "{text}");
    assert!(text.contains("parse"), "{text}");
    assert!(text.contains("total"), "{text}");
}
