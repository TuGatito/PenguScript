//! Tests de extremo a extremo del binario `pengu` (proceso real).

use std::path::{Path, PathBuf};
use std::process::{Command, Output};

struct TempDir(PathBuf);

impl TempDir {
    fn new(name: &str) -> Self {
        let unique = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("reloj")
            .as_nanos();
        let path =
            std::env::temp_dir().join(format!("pengu-cli-{name}-{}-{unique}", std::process::id()));
        let _ = std::fs::remove_dir_all(&path);
        std::fs::create_dir_all(&path).expect("temp");
        Self(path)
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn git(dir: &Path, args: &[&str]) {
    let output = Command::new("git")
        .args(args)
        .current_dir(dir)
        .env("GIT_TERMINAL_PROMPT", "0")
        .output()
        .expect("git");
    assert!(
        output.status.success(),
        "git {args:?}: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

fn make_dependency(dir: &Path) {
    git(dir, &["init", "--quiet", "-b", "main"]);
    std::fs::write(
        dir.join("Tome.toml"),
        "[tome]\nname = \"text\"\nversion = \"1.0.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\
         [lib]\nname = \"text\"\n",
    )
    .expect("manifiesto");
    std::fs::write(
        dir.join("lib.pengu"),
        "unveil shout = (name: &Str) -> String\n    String.from(name) + \"!\"\n",
    )
    .expect("fuente");
    git(dir, &["add", "."]);
    git(
        dir,
        &[
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "commit",
            "--quiet",
            "-m",
            "inicial",
        ],
    );
    git(dir, &["tag", "v1"]);
}

fn project(dir: &Path, dependency: &Path) -> String {
    let manifest = format!(
        "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\
         [[bin]]\nname = \"demo\"\n\
         [dependencies]\ntext = {{ git = \"{}\", tag = \"v1\" }}\n",
        dependency.display()
    );
    std::fs::write(dir.join("Tome.toml"), &manifest).expect("manifiesto");
    std::fs::write(
        dir.join("main.pengu"),
        "summon text::shout\n\ngrimoire\n    print(shout(\"hola\"))\n",
    )
    .expect("main");
    manifest
}

fn pengu(args: &[&str], dir: &Path, home: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_pengu"))
        .args(args)
        .current_dir(dir)
        .env("PENGU_HOME", home)
        .output()
        .expect("pengu")
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

#[test]
fn fetch_escribe_lock_tree_y_build_locked() {
    let dependency = TempDir::new("dep");
    make_dependency(dependency.path());
    let root = TempDir::new("proyecto");
    let manifest = project(root.path(), dependency.path());
    let home = TempDir::new("home");

    let fetch = pengu(&["fetch", "--verbose"], root.path(), home.path());
    assert!(fetch.status.success(), "{}", stderr(&fetch));
    let lock = std::fs::read_to_string(root.path().join("Tome.lock")).expect("lock");
    assert!(lock.contains("name = \"text\""), "{lock}");
    assert!(lock.contains("checksum = \"sha256-"), "{lock}");
    assert!(String::from_utf8_lossy(&fetch.stdout).contains("lock: 1 paquete"));

    let tree = pengu(&["tree"], root.path(), home.path());
    assert!(tree.status.success(), "{}", stderr(&tree));
    let rendered = String::from_utf8_lossy(&tree.stdout);
    assert!(rendered.contains("demo v0.1.0"), "{rendered}");
    assert!(rendered.contains("text v1.0.0"), "{rendered}");

    let build = pengu(&["build", "--locked"], root.path(), home.path());
    assert!(build.status.success(), "{}", stderr(&build));

    let run = pengu(&["run", "--locked"], root.path(), home.path());
    assert!(run.status.success(), "{}", stderr(&run));
    assert!(
        String::from_utf8_lossy(&run.stdout).contains("hola!"),
        "{}",
        String::from_utf8_lossy(&run.stdout)
    );

    let version = pengu(&["version"], root.path(), home.path());
    assert!(version.status.success());
    assert!(String::from_utf8_lossy(&version.stdout).starts_with("pengu "));

    // Cambiar el manifiesto deja el lock desactualizado y `--locked` lo detecta.
    let changed = manifest.replace("tag = \"v1\"", "tag = \"v2\"");
    std::fs::write(root.path().join("Tome.toml"), changed).expect("manifiesto");
    let stale = pengu(&["build", "--locked"], root.path(), home.path());
    assert!(!stale.status.success());
    assert!(stderr(&stale).contains("PGS-E1804"), "{}", stderr(&stale));
}

#[test]
fn size_muestra_tamanos_reales() {
    let project = TempDir::new("tamanos");
    let home = TempDir::new("home-tamanos");
    std::fs::write(
        project.path().join("Tome.toml"),
        "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\npath = \"main.pengu\"\n",
    )
    .expect("manifiesto");
    std::fs::write(
        project.path().join("main.pengu"),
        "rune Punto\n    x: Int\n    y: Int\n\nsuma = (a: Int, b: Int) -> Int\n    a + b\n\ngrimoire\n    print(suma(1, 2))\n",
    )
    .expect("programa");

    let output = pengu(&["size"], project.path(), home.path());
    assert_eq!(output.status.code(), Some(0), "{}", stderr(&output));
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("tipo Punto · 8 B"), "{stdout}");
    assert!(stdout.contains("fn suma · huella 12 B"), "{stdout}");
}

#[test]
fn sin_manifiesto_es_error_de_uso() {
    let empty = TempDir::new("vacio");
    let home = TempDir::new("home2");
    let output = pengu(&["build"], empty.path(), home.path());
    assert_eq!(output.status.code(), Some(2));
    assert!(stderr(&output).contains("Tome.toml"));
}

fn lock_commit(lock: &str) -> String {
    lock.lines()
        .find_map(|line| line.trim().strip_prefix("commit = \""))
        .map(|rest| rest.trim_end_matches('"').to_owned())
        .expect("commit en el lock")
}

fn commit_file(dir: &Path, name: &str, contents: &str) {
    std::fs::write(dir.join(name), contents).expect("archivo");
    git(dir, &["add", "."]);
    git(
        dir,
        &[
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "commit",
            "--quiet",
            "-m",
            "cambio",
        ],
    );
}

#[test]
fn add_remove_y_update_gestionan_dependencias() {
    let dependency = TempDir::new("dep-acciones");
    make_dependency(dependency.path());
    // Segunda versión para comprobar que `add` prefiere la etiqueta más alta.
    commit_file(
        dependency.path(),
        "lib.pengu",
        "unveil shout = (name: &Str) -> String\n    String.from(name) + \"!!\"\n",
    );
    git(dependency.path(), &["tag", "v2"]);
    let root = TempDir::new("proyecto-acciones");
    std::fs::write(
        root.path().join("Tome.toml"),
        "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\n",
    )
    .expect("manifiesto");
    std::fs::write(
        root.path().join("main.pengu"),
        "grimoire\n    print(\"hola\")\n",
    )
    .expect("main");
    let home = TempDir::new("home-acciones");

    let add = pengu(
        &["add", "--git", &dependency.path().display().to_string()],
        root.path(),
        home.path(),
    );
    assert!(add.status.success(), "{}", stderr(&add));
    let manifest = std::fs::read_to_string(root.path().join("Tome.toml")).expect("manifiesto");
    assert!(manifest.contains("git = "), "{manifest}");
    assert!(manifest.contains("tag = \"v2\""), "{manifest}");
    assert!(manifest.contains("text ="), "{manifest}");

    let lock = std::fs::read_to_string(root.path().join("Tome.lock")).expect("lock");
    assert!(lock.contains("name = \"text\""), "{lock}");

    let remove = pengu(&["remove", "text"], root.path(), home.path());
    assert!(remove.status.success(), "{}", stderr(&remove));
    let manifest = std::fs::read_to_string(root.path().join("Tome.toml")).expect("manifiesto");
    assert!(!manifest.contains("text ="), "{manifest}");
    let lock = std::fs::read_to_string(root.path().join("Tome.lock")).expect("lock");
    assert!(!lock.contains("name = \"text\""), "{lock}");

    // `add --branch` sigue la rama y `update` recoge el commit nuevo.
    let add = pengu(
        &[
            "add",
            "--git",
            &dependency.path().display().to_string(),
            "--branch",
            "main",
        ],
        root.path(),
        home.path(),
    );
    assert!(add.status.success(), "{}", stderr(&add));
    let first = lock_commit(&std::fs::read_to_string(root.path().join("Tome.lock")).expect("lock"));
    commit_file(
        dependency.path(),
        "lib.pengu",
        "unveil shout = (name: &Str) -> String\n    String.from(name) + \"!!!\"\n",
    );
    let update = pengu(&["update"], root.path(), home.path());
    assert!(update.status.success(), "{}", stderr(&update));
    let second =
        lock_commit(&std::fs::read_to_string(root.path().join("Tome.lock")).expect("lock"));
    assert_ne!(first, second, "`update` debe mover la rama");
    assert!(
        String::from_utf8_lossy(&update.stdout).contains("actualizados 1 paquete")
            || String::from_utf8_lossy(&update.stdout).contains("actualizados")
    );

    let missing = pengu(&["remove", "nope"], root.path(), home.path());
    assert_eq!(missing.status.code(), Some(1));
    assert!(
        stderr(&missing).contains("PGS-E1803"),
        "{}",
        stderr(&missing)
    );
}

#[test]
fn vendor_copia_verifica_y_habilita_build_offline() {
    let dependency = TempDir::new("dep-vendor");
    make_dependency(dependency.path());
    let root = TempDir::new("proyecto-vendor");
    std::fs::write(
        root.path().join("Tome.toml"),
        format!(
            "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\n\n[dependencies]\ntext = {{ git = \"{}\", tag = \"v1\" }}\n",
            dependency.path().display()
        ),
    )
    .expect("manifiesto");
    std::fs::write(
        root.path().join("main.pengu"),
        "summon text::shout\n\ngrimoire\n    print(shout(\"hola\"))\n",
    )
    .expect("main");
    let home = TempDir::new("home-vendor");

    let fetch = pengu(&["fetch"], root.path(), home.path());
    assert!(fetch.status.success(), "{}", stderr(&fetch));
    let vendor = pengu(&["vendor"], root.path(), home.path());
    assert!(vendor.status.success(), "{}", stderr(&vendor));
    assert!(root.path().join("vendor/text/lib.pengu").is_file());
    assert!(root.path().join("vendor/text/.pengu-checksum").is_file());

    let check = pengu(&["vendor", "--check"], root.path(), home.path());
    assert!(check.status.success(), "{}", stderr(&check));

    // Con vendor, el build funciona sin red ni caché.
    let empty_home = TempDir::new("home-vendor-vacio");
    let build = pengu(&["build", "--offline"], root.path(), empty_home.path());
    assert!(build.status.success(), "{}", stderr(&build));

    // Una copia editada a mano se detecta y no se compila en silencio.
    std::fs::write(
        root.path().join("vendor/text/lib.pengu"),
        "unveil shout = (name: &Str) -> String\n    String.from(\"trampa\")\n",
    )
    .expect("edita");
    let broken = pengu(&["build", "--offline"], root.path(), empty_home.path());
    assert_eq!(broken.status.code(), Some(1));
    assert!(stderr(&broken).contains("PGS-E1808"), "{}", stderr(&broken));
}

#[test]
fn new_crea_proyectos_desde_los_templates() {
    let home = TempDir::new("home-new");
    let work = TempDir::new("work-new");

    let list = pengu(&["new", "--template", "list"], work.path(), home.path());
    assert!(list.status.success(), "{}", stderr(&list));
    let text = String::from_utf8_lossy(&list.stdout);
    assert!(text.contains("with-dependency"), "{text}");

    let created = pengu(&["new", "saludo"], work.path(), home.path());
    assert!(created.status.success(), "{}", stderr(&created));
    let root = work.path().join("saludo");
    assert!(root.join("Tome.toml").is_file());
    assert!(root.join("main.pengu").is_file());

    let run = pengu(&["run"], &root, home.path());
    assert!(run.status.success(), "{}", stderr(&run));
    assert_eq!(
        String::from_utf8_lossy(&run.stdout).trim(),
        "hola desde saludo"
    );

    let again = pengu(&["new", "saludo"], work.path(), home.path());
    assert_eq!(again.status.code(), Some(2), "{}", stderr(&again));
    assert!(stderr(&again).contains("ya existe"), "{}", stderr(&again));
}

#[test]
fn new_con_dependencia_resuelve_el_lock_sin_red() {
    let home = TempDir::new("home-new-dep");
    let work = TempDir::new("work-new-dep");
    let created = pengu(
        &["new", "con-dep", "--template", "with-dependency"],
        work.path(),
        home.path(),
    );
    assert!(created.status.success(), "{}", stderr(&created));
    let root = work.path().join("con-dep");
    let lock = std::fs::read_to_string(root.join("Tome.lock")).expect("lock");
    assert!(lock.contains("name = \"util\""), "{lock}");
    assert!(lock.contains("source = \"path+"), "{lock}");

    let run = pengu(&["run", "--offline"], &root, home.path());
    assert!(run.status.success(), "{}", stderr(&run));
    assert_eq!(
        String::from_utf8_lossy(&run.stdout).trim(),
        "hola, con-dep!"
    );

    let unknown = pengu(
        &["new", "x", "--template", "nope"],
        work.path(),
        home.path(),
    );
    assert_eq!(unknown.status.code(), Some(2));
    assert!(stderr(&unknown).contains("template desconocido"));
}

#[test]
fn new_lib_ejecuta_su_test() {
    let home = TempDir::new("home-new-lib");
    let work = TempDir::new("work-new-lib");
    let created = pengu(
        &["new", "matematica", "--template", "lib"],
        work.path(),
        home.path(),
    );
    assert!(created.status.success(), "{}", stderr(&created));
    let root = work.path().join("matematica");
    let test = pengu(&["test"], &root, home.path());
    assert!(test.status.success(), "{}", stderr(&test));
    let summary = String::from_utf8_lossy(&test.stdout);
    assert!(summary.contains("test result: ok"), "{summary}");
    assert!(summary.contains("1 passed"), "{summary}");
}
