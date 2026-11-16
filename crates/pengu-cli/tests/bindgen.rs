//! `pengu bindgen` de extremo a extremo con el binario real.

#![cfg(unix)]

use std::path::{Path, PathBuf};
use std::process::Command;

const HEADER: &str = r"typedef struct { int x; int y; } Point;
enum Mode { MODE_A = 0, MODE_C = 4 };
extern unsigned long strlen(const char *text);
";

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

fn pengu() -> Command {
    Command::new(env!("CARGO_BIN_EXE_pengu"))
}

fn setup(root: &Path) {
    std::fs::write(root.join("libc.h"), HEADER).unwrap();
    std::fs::write(
        root.join("Tome.toml"),
        "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\n\n[link]\nc\n\n[declarations]\nlibc = \"libc.d.pengu\"\n",
    )
    .unwrap();
    std::fs::write(root.join("main.pengu"), "grimoire\n    print(1)\n").unwrap();
}

#[test]
fn genera_un_declarado_que_el_pipeline_acepta() {
    let root = project("pengu-cli-bindgen");
    setup(&root);
    let output = pengu()
        .current_dir(&root)
        .args(["bindgen", "libc.h"])
        .output()
        .unwrap();
    assert!(output.status.success(), "{output:?}");
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("libc.d.pengu"), "{stdout}");
    let source = std::fs::read_to_string(root.join("libc.d.pengu")).unwrap();
    assert!(source.contains("rune Point"));
    assert!(source.contains("MODE_C: Int = 4"));
    assert!(source.contains("strlen = (text: &CStr) -> "));

    let check = pengu().current_dir(&root).arg("check").output().unwrap();
    assert!(check.status.success(), "{check:?}");

    let verified = pengu()
        .current_dir(&root)
        .args(["bindgen", "libc.h", "--check"])
        .output()
        .unwrap();
    assert!(verified.status.success(), "{verified:?}");

    std::fs::write(
        root.join("libc.h"),
        format!("{HEADER}extern int abs(int value);\n"),
    )
    .unwrap();
    let stale = pengu()
        .current_dir(&root)
        .args(["bindgen", "libc.h", "--check"])
        .output()
        .unwrap();
    assert_eq!(stale.status.code(), Some(1), "{stale:?}");
    assert!(String::from_utf8_lossy(&stale.stderr).contains("no coincide"));

    let regenerated = pengu()
        .current_dir(&root)
        .args(["bindgen", "libc.h"])
        .output()
        .unwrap();
    assert!(regenerated.status.success(), "{regenerated:?}");
    let again = pengu()
        .current_dir(&root)
        .args(["bindgen", "libc.h", "--check"])
        .output()
        .unwrap();
    assert!(again.status.success(), "{again:?}");
}

#[test]
fn rechaza_una_cabecera_que_no_compila() {
    let root = project("pengu-cli-bindgen-rota");
    setup(&root);
    std::fs::write(root.join("rota.h"), "struct { int x }\n").unwrap();
    let output = pengu()
        .current_dir(&root)
        .args(["bindgen", "rota.h", "-o", "rota.d.pengu"])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(1), "{output:?}");
    assert!(String::from_utf8_lossy(&output.stderr).contains("clang"));
}

#[test]
fn respeta_allowlist_y_bloqueos() {
    let root = project("pengu-cli-bindgen-filtros");
    setup(&root);
    let output = pengu()
        .current_dir(&root)
        .args([
            "bindgen",
            "libc.h",
            "-o",
            "filtrado.d.pengu",
            "--allow",
            "strlen",
            "--block",
            "MODE_*",
        ])
        .output()
        .unwrap();
    assert!(output.status.success(), "{output:?}");
    let source = std::fs::read_to_string(root.join("filtrado.d.pengu")).unwrap();
    assert!(source.contains("strlen ="));
    assert!(!source.contains("rune Point"));
    assert!(!source.contains("MODE_A"));
}
