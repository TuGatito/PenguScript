use std::path::PathBuf;

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
fn compiles_emits_and_runs_a_project() {
    let root = project("pengu-build", "grimoire\n    print(42)\n");
    let result = pengu_build::compile(&root);
    assert!(result.is_clean(), "{:?}", result.diagnostics);
    assert!(result.rust.contains("fn main()"));
    assert!(result.cargo_toml.contains("name = \"demo\""));
    let out = pengu_build::emit(&root, &result).unwrap();
    assert!(out.join("src/main.rs").is_file());
    assert!(out.join("sourcemap.json").is_file());
    let report = pengu_build::run(&root).unwrap();
    assert!(report.success());
    let output = report.output.expect("el binario se ejecutó");
    assert_eq!(String::from_utf8_lossy(&output.stdout), "42\n");
}

#[test]
fn cargo_builds_the_generated_project() {
    let root = project("pengu-build-cargo", "grimoire\n    print(7)\n");
    let report = pengu_build::build(&root).unwrap();
    assert!(report.success(), "{:?}", report.diagnostics);
    assert!(root.join("target/pengu/Cargo.toml").is_file());
    assert!(root.join("target/pengu/build.rs").is_file());
}

#[test]
fn lib_project_emits_and_builds_a_library() {
    let stamp = format!(
        "{}_{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    );
    let root = std::env::temp_dir().join(format!("pengu-build-lib-{stamp}"));
    std::fs::create_dir_all(&root).unwrap();
    std::fs::write(root.join("Tome.toml"), "[tome]\nname = \"demo_lib\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[lib]\nname = \"demo_lib\"\n").unwrap();
    std::fs::write(
        root.join("lib.pengu"),
        "show = (n: Int) -> Int\n    n + 1\n",
    )
    .unwrap();
    let report = pengu_build::build(&root).unwrap();
    assert!(report.success(), "{:?}", report.diagnostics);
    assert!(root.join("target/pengu/src/lib.rs").is_file());
    assert!(root.join("target/pengu/Cargo.toml").is_file());
}

#[test]
fn path_dependency_and_features_are_emitted() {
    let stamp = format!(
        "{}_{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    );
    let root = std::env::temp_dir().join(format!("pengu-build-dep-{stamp}"));
    let dep = root.join("native-dep");
    std::fs::create_dir_all(dep.join("src")).unwrap();
    std::fs::write(dep.join("Cargo.toml"), "[package]\nname = \"native_dep\"\nversion = \"0.1.0\"\nedition = \"2021\"\n\n[features]\nextra = []\n").unwrap();
    std::fs::write(dep.join("src/lib.rs"), "pub fn value() -> i32 { 49 }\n").unwrap();
    std::fs::write(root.join("Tome.toml"), "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\n\n[dependencies]\nnative_dep = { path = \"native-dep\", features = [\"extra\"] }\n").unwrap();
    std::fs::write(root.join("main.pengu"), "grimoire\n    print(1)\n").unwrap();
    let report = pengu_build::build(&root).unwrap();
    assert!(report.success(), "{:?}", report.diagnostics);
}

#[test]
fn build_rs_links_native_libraries() {
    let stamp = format!(
        "{}_{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    );
    let root = std::env::temp_dir().join(format!("pengu-build-link-{stamp}"));
    std::fs::create_dir_all(&root).unwrap();
    std::fs::write(root.join("Tome.toml"), "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\n\n[link]\nm\n").unwrap();
    std::fs::write(root.join("main.pengu"), "grimoire\n    print(1)\n").unwrap();
    let report = pengu_build::build(&root).unwrap();
    assert!(report.success(), "{:?}", report.diagnostics);
    let build_rs = std::fs::read_to_string(root.join("target/pengu/build.rs")).unwrap();
    assert!(build_rs.contains("rustc-link-lib=m"), "{build_rs}");
}

#[test]
fn test_report_runs_generated_tests() {
    let stamp = format!(
        "{}_{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    );
    let root = std::env::temp_dir().join(format!("pengu-build-test-{stamp}"));
    std::fs::create_dir_all(&root).unwrap();
    std::fs::write(root.join("Tome.toml"), "[tome]\nname = \"demo_lib\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[lib]\nname = \"demo_lib\"\n").unwrap();
    std::fs::write(
        root.join("lib.pengu"),
        "add = (a: Int, b: Int) -> Int\n    a + b\n\n@@test\ncheck = () -> Unit\n    assert(add(1, 2) == 3, \"sum\")\n",
    )
    .unwrap();
    let report = pengu_build::test_report(&root).unwrap();
    assert!(report.success(), "{:?}", report.diagnostics);
    let output = report.output.expect("cargo test output");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn run_report_returns_stdout_and_no_diagnostics() {
    let root = project("pengu-build-run-report", "grimoire\n    print(11)\n");
    let report = pengu_build::run_report(&root).unwrap();
    assert!(report.success(), "{:?}", report.diagnostics);
    let output = report.output.expect("cargo run output");
    assert_eq!(String::from_utf8_lossy(&output.stdout), "11\n");
}

#[test]
fn cargo_failure_is_reported_as_backend_diagnostic() {
    let stamp = format!(
        "{}_{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    );
    let root = std::env::temp_dir().join(format!("pengu-build-backend-{stamp}"));
    std::fs::create_dir_all(&root).unwrap();
    std::fs::write(root.join("Tome.toml"), "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\n\n[link]\npengu_definitely_missing_lib\n").unwrap();
    std::fs::write(root.join("main.pengu"), "grimoire\n    print(1)\n").unwrap();
    let report = pengu_build::build_report(&root).unwrap();
    assert!(!report.success());
    assert!(
        report.diagnostics.iter().any(|d| d.code == "PGS-E2014"),
        "{:?}",
        report.diagnostics
    );
}
