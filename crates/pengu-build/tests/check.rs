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
fn check_accepts_a_valid_program_without_touching_target() {
    let root = project(
        "pengu-check-ok",
        "suma = (a: Int) -> Int\n    a + 1\n\ngrimoire\n    print(suma(1))\n",
    );
    let report = pengu_build::check(&root);
    assert!(report.is_clean(), "{:?}", report.diagnostics);
    assert!(
        !root.join("target").exists(),
        "`check` no debe generar artefactos"
    );
}

#[test]
fn check_reports_type_errors() {
    let root = project(
        "pengu-check-types",
        "suma = (a: Int) -> Int\n    \"texto\"\n\ngrimoire\n    print(suma(1))\n",
    );
    let report = pengu_build::check(&root);
    assert!(!report.is_clean());
    assert!(
        report
            .diagnostics
            .iter()
            .any(|diagnostic| diagnostic.code == "PGS-E7002"),
        "{:?}",
        report.diagnostics
    );
}

#[test]
fn check_reports_ownership_errors() {
    let root = project(
        "pengu-check-ownership",
        "rune Caja\n    valor: Int\n\nconsume = (caja: Caja) -> Int\n    caja.valor\n\nroto = () -> Int\n    bind caja = Caja(valor: 1)\n    bind a = consume(caja)\n    consume(caja) + a\n\ngrimoire\n    print(roto())\n",
    );
    let report = pengu_build::check(&root);
    assert!(!report.is_clean(), "{:?}", report.diagnostics);
    assert!(
        report
            .diagnostics
            .iter()
            .any(|diagnostic| diagnostic.code == "PGS-E4101"),
        "{:?}",
        report.diagnostics
    );
}
