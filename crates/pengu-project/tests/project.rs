use std::path::PathBuf;

use pengu_project::{load, parse_manifest, validate_link, validate_lock, validate_manifest};

fn temp_dir(name: &str) -> PathBuf {
    let path = std::env::temp_dir().join(format!("pengu-project-{name}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&path);
    std::fs::create_dir_all(&path).unwrap();
    path
}

#[test]
fn missing_manifest_uses_e2001() {
    let root = temp_dir("missing");
    let loaded = load(&root);
    assert!(loaded.diagnostics.iter().any(|d| d.code == "PGS-E2001"));
}

#[test]
fn missing_entry_uses_e2002() {
    let root = temp_dir("entry");
    std::fs::write(
        root.join("Tome.toml"),
        "[tome]\nname = \"x\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n",
    )
    .unwrap();
    let loaded = load(&root);
    assert!(loaded.diagnostics.iter().any(|d| d.code == "PGS-E2002"));
}

#[test]
fn invalid_manifest_uses_e2010() {
    let error = parse_manifest("name = \"x\"\n").unwrap_err();
    assert_eq!(error.code, "PGS-E2010");
}

#[test]
fn incompatible_pengu_uses_e1802() {
    let manifest = parse_manifest("[tome]\npengu = \"0.5\"\n").unwrap();
    let diagnostics = validate_manifest(&manifest, std::path::Path::new("."));
    assert!(diagnostics.iter().any(|d| d.code == "PGS-E1802"));
}

#[test]
fn git_without_ref_uses_e1806() {
    let manifest =
        parse_manifest("[tome]\npengu = \"0.6\"\n[dependencies]\nfoo = { git = \"https://x\" }\n")
            .unwrap();
    let diagnostics = validate_manifest(&manifest, std::path::Path::new("."));
    assert!(diagnostics.iter().any(|d| d.code == "PGS-E1806"));
}

#[test]
fn duplicate_dependency_uses_e1807() {
    let manifest =
        parse_manifest("[tome]\npengu = \"0.6\"\n[dependencies]\nfoo = \"a\"\nfoo = \"b\"\n")
            .unwrap();
    let diagnostics = validate_manifest(&manifest, std::path::Path::new("."));
    assert!(diagnostics.iter().any(|d| d.code == "PGS-E1807"));
}

#[test]
fn missing_path_dependency_uses_e1803() {
    let manifest =
        parse_manifest("[tome]\npengu = \"0.6\"\n[dependencies]\nfoo = \"missing-dir\"\n").unwrap();
    let diagnostics = validate_manifest(&manifest, std::path::Path::new("."));
    assert!(diagnostics.iter().any(|d| d.code == "PGS-E1803"));
}

#[test]
fn invalid_lock_uses_e1808() {
    let manifest = parse_manifest("[tome]\npengu = \"0.6\"\n").unwrap();
    let diagnostics = validate_lock(&manifest, "garbage\n");
    assert!(diagnostics.iter().any(|d| d.code == "PGS-E1808"));
}

#[test]
fn outdated_lock_uses_e1804() {
    let manifest = parse_manifest("[tome]\nversion = \"0.2.0\"\npengu = \"0.6\"\n").unwrap();
    let diagnostics = validate_lock(&manifest, "version = 1\nversion = \"0.1.0\"\n");
    assert!(diagnostics.iter().any(|d| d.code == "PGS-E1804"));
}

#[test]
fn missing_link_uses_e2023() {
    let manifest = parse_manifest("[tome]\npengu = \"0.6\"\n").unwrap();
    assert_eq!(validate_link("C", &manifest).unwrap().code, "PGS-E2023");
}

#[test]
fn undeclared_dependency_uses_e2011() {
    let manifest = parse_manifest("[tome]\npengu = \"0.6\"\n").unwrap();
    assert_eq!(
        pengu_project::require_dependency(&manifest, "nope")
            .unwrap()
            .code,
        "PGS-E2011"
    );
}

#[test]
fn unmapped_backend_error_uses_e2014() {
    assert_eq!(
        pengu_project::map_backend_error(false).unwrap().code,
        "PGS-E2014"
    );
}

#[test]
fn parses_features_and_rust_version() {
    let manifest = parse_manifest(
        "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\nrust-version = \"1.90.0\"\n\n[features]\ndefault = [\"extra\"]\nextra = []\n\n[dependencies]\nfoo = { path = \"../foo\", features = [\"fast\"], default-features = false, optional = true }\n",
    )
    .unwrap();
    assert_eq!(manifest.rust_version, "1.90.0");
    assert_eq!(manifest.features.len(), 2);
    assert_eq!(manifest.features[0].name, "default");
    assert_eq!(manifest.features[0].enables, vec!["extra"]);
    assert!(!manifest.dependencies[0].default_features);
    assert!(manifest.dependencies[0].optional);
    assert_eq!(manifest.dependencies[0].features, vec!["fast"]);
}
