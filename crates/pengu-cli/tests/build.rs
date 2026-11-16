//! Pruebas de extremo a extremo de `pengu check` y `pengu watch`.

#![allow(clippy::missing_panics_doc, clippy::unwrap_used)]

use std::os::unix::fs::PermissionsExt;

use std::path::PathBuf;
use std::process::{Command, Output, Stdio};
use std::time::{Duration, Instant};

fn binary() -> &'static str {
    env!("CARGO_BIN_EXE_pengu")
}

struct Project {
    root: PathBuf,
}

impl Project {
    fn new(name: &str) -> Self {
        let root = std::env::temp_dir().join(format!(
            "pengu-check-{}-{name}-{}",
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

#[test]
fn check_analiza_sin_cargo_y_sin_artefactos() {
    let project = Project::new("ok");
    project.write(
        "main.pengu",
        "suma = (a: Int) -> Int\n    a + 1\n\ngrimoire\n    print(suma(1))\n",
    );
    let output = project.run(&["check"]);
    assert_eq!(output.status.code(), Some(0));
    assert!(String::from_utf8_lossy(&output.stdout).contains("sin errores"));
    assert!(
        !project.root.join("target").exists(),
        "`check` no debe generar `target/`"
    );

    project.write("main.pengu", "suma = (a: Int) -> Int\n    \"texto\"\n");
    let output = project.run(&["check"]);
    assert_eq!(output.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&output.stderr).contains("PGS-E7002"));
}

#[test]
fn watch_repite_al_cambiar_un_fuente() {
    let project = Project::new("watch");
    project.write("main.pengu", "grimoire\n    print(1)\n");
    let log = project.root.join("watch.log");
    let file = std::fs::File::create(&log).unwrap();
    let mut child = Command::new(binary())
        .args(["check", "--watch"])
        .current_dir(&project.root)
        .env("PENGU_HOME", project.root.join("home"))
        .stdout(Stdio::from(file))
        .stderr(Stdio::null())
        .spawn()
        .unwrap();

    let runs = |text: &str| text.matches("── check ──").count();
    let deadline = Instant::now() + Duration::from_secs(10);
    while runs(&std::fs::read_to_string(&log).unwrap_or_default()) < 1 {
        assert!(
            Instant::now() < deadline,
            "watch no ejecutó el primer check"
        );
        std::thread::sleep(Duration::from_millis(50));
    }

    std::thread::sleep(Duration::from_millis(300));
    project.write("main.pengu", "grimoire\n    print(2)\n");
    let deadline = Instant::now() + Duration::from_secs(10);
    while runs(&std::fs::read_to_string(&log).unwrap_or_default()) < 2 {
        assert!(
            Instant::now() < deadline,
            "watch no re-ejecutó tras el cambio"
        );
        std::thread::sleep(Duration::from_millis(50));
    }
    let _ = child.kill();
    let _ = child.wait();
}

#[test]
fn watch_rechaza_comandos_desconocidos() {
    let project = Project::new("watch-bad");
    project.write("main.pengu", "grimoire\n    print(1)\n");
    let output = project.run(&["watch", "publicar"]);
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("no reconoce"));

    let output = project.run(&["build", "--watch"]);
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("`--watch` solo"));
}

fn cargo_shim(dir: &std::path::Path, log: &std::path::Path) -> (PathBuf, PathBuf) {
    let bin = dir.join("bin");
    std::fs::create_dir_all(&bin).unwrap();
    let script = bin.join("cargo");
    let real = std::env::var("CARGO").unwrap_or_else(|_| "cargo".to_owned());
    std::fs::write(
        &script,
        format!(
            "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"{}\"\nexec \"{}\" \"$@\"\n",
            log.display(),
            real
        ),
    )
    .unwrap();
    let mut perms = std::fs::metadata(&script).unwrap().permissions();
    perms.set_mode(0o755);
    std::fs::set_permissions(&script, perms).unwrap();
    (bin, log.to_path_buf())
}

#[test]
fn build_reutiliza_la_cache_y_solo_invoca_cargo_una_vez() {
    let project = Project::new("cache");
    project.write("main.pengu", "grimoire\n    print(40 + 2)\n");
    let log = project.root.join("cargo.log");
    let (bin, log) = cargo_shim(&project.root.join("shim"), &log);
    let run = |extra: &[&str]| {
        Command::new(binary())
            .args(["build"])
            .args(extra)
            .current_dir(&project.root)
            .env("PENGU_HOME", project.root.join("home"))
            .env(
                "PATH",
                format!(
                    "{}:{}",
                    bin.display(),
                    std::env::var("PATH").unwrap_or_default()
                ),
            )
            .env(
                "CARGO",
                std::env::var("CARGO").unwrap_or_else(|_| "cargo".to_owned()),
            )
            .output()
            .unwrap()
    };

    let first = run(&[]);
    assert_eq!(
        first.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&first.stderr)
    );
    let invocations = || {
        std::fs::read_to_string(&log)
            .unwrap_or_default()
            .lines()
            .count()
    };
    let after_first = invocations();
    assert!(after_first > 0, "el primer build debe llamar a cargo");

    let second = run(&["-v"]);
    assert_eq!(second.status.code(), Some(0));
    assert!(
        String::from_utf8_lossy(&second.stderr).contains("sin cambios"),
        "{}",
        String::from_utf8_lossy(&second.stderr)
    );
    assert_eq!(
        invocations(),
        after_first,
        "la caché no debe invocar a cargo"
    );

    // Cambiar la fuente invalida la caché.
    project.write("main.pengu", "grimoire\n    print(40 + 3)\n");
    let third = run(&[]);
    assert_eq!(third.status.code(), Some(0));
    assert!(invocations() > after_first, "un cambio debe recompilar");
}

#[test]
fn run_usa_el_binario_cuando_la_cache_es_valida() {
    let project = Project::new("cache-run");
    project.write("main.pengu", "grimoire\n    print(7)\n");
    let log = project.root.join("cargo.log");
    let (bin, log) = cargo_shim(&project.root.join("shim"), &log);
    let spawn = |args: &[&str]| {
        Command::new(binary())
            .args(args)
            .current_dir(&project.root)
            .env("PENGU_HOME", project.root.join("home"))
            .env(
                "PATH",
                format!(
                    "{}:{}",
                    bin.display(),
                    std::env::var("PATH").unwrap_or_default()
                ),
            )
            .env(
                "CARGO",
                std::env::var("CARGO").unwrap_or_else(|_| "cargo".to_owned()),
            )
            .output()
            .unwrap()
    };
    assert_eq!(spawn(&["build"]).status.code(), Some(0));
    let after_build = std::fs::read_to_string(&log)
        .unwrap_or_default()
        .lines()
        .count();
    let output = spawn(&["run"]);
    assert_eq!(output.status.code(), Some(0));
    assert_eq!(String::from_utf8_lossy(&output.stdout), "7\n");
    assert_eq!(
        std::fs::read_to_string(&log)
            .unwrap_or_default()
            .lines()
            .count(),
        after_build,
        "`run` no debe invocar a cargo si la caché es válida"
    );
}
