//! Los ejemplos del repositorio compilan, corren y producen la salida esperada.
//!
//! Cada ejemplo se copia a un proyecto temporal con su propio `Tome.toml`: se
//! prueba la fuente del ejemplo, no un manifiesto compartido. Así un cambio en
//! la stdlib que rompa un ejemplo se ve aquí y no al publicar.

use std::path::{Path, PathBuf};

const EXAMPLES: &[(&str, &str)] = &[
    ("hola", "hola, Ana\nhola, Luis\n"),
    (
        "numeros",
        "suma: 31\npares: [4, 2, 6]\nmedia: 3\nmayor: some(9)\n",
    ),
    (
        "config",
        "some(demo)\nsome(8080)\nsome(false)\nsome(localhost)\nfalse\n",
    ),
    (
        "archivos",
        "sin restos\ncreado\nescrito\nhola desde PenguScript\ntrue\n1\nborrado\n",
    ),
    ("enums", "12\n12.566370614359172\n0\nhola\n"),
];

fn examples_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("examples")
}

fn project(example: &Path) -> PathBuf {
    let stamp = format!(
        "{}_{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    );
    let dir = std::env::temp_dir().join(format!("pengu-example-{stamp}"));
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(
        dir.join("Tome.toml"),
        "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\npengu = \"0.6\"\nedition = \"2024\"\n\n[[bin]]\nname = \"demo\"\n",
    )
    .unwrap();
    std::fs::copy(example, dir.join("main.pengu")).unwrap();
    dir
}

#[test]
fn los_ejemplos_compilan_y_corren() {
    for (name, expected) in EXAMPLES {
        let source = examples_dir().join(format!("{name}.pengu"));
        assert!(source.is_file(), "falta {}", source.display());
        let root = project(&source);
        let report = pengu_build::run(&root).unwrap();
        assert!(
            report.success(),
            "{name}: {:?}",
            report
                .diagnostics
                .iter()
                .map(|d| format!("{}: {}", d.code, d.message))
                .collect::<Vec<_>>()
        );
        let output = report.output.expect("el binario se ejecutó");
        assert_eq!(String::from_utf8_lossy(&output.stdout), *expected, "{name}");
    }
}

#[test]
fn los_ejemplos_estan_formateados_y_sin_avisos() {
    let dir = examples_dir();
    let mut files: Vec<PathBuf> = std::fs::read_dir(&dir)
        .unwrap()
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| path.extension().is_some_and(|ext| ext == "pengu"))
        .filter(|path| {
            let stem = path
                .file_stem()
                .and_then(|stem| stem.to_str())
                .unwrap_or_default();
            EXAMPLES.iter().any(|(name, _)| *name == stem)
        })
        .collect();
    files.sort();
    assert_eq!(files.len(), EXAMPLES.len());
    for file in files {
        let source = std::fs::read_to_string(&file).unwrap();
        assert!(
            pengu_fmt::format_source(&source).is_ok_and(|formatted| formatted == source),
            "{} no está formateado",
            file.display()
        );
        let name = file
            .file_stem()
            .and_then(|stem| stem.to_str())
            .unwrap_or_default();
        let report = pengu_lint::lint(
            &source,
            pengu_span::FileId::new(0),
            &pengu_lint::LintConfig::default(),
        );
        assert!(
            report.diagnostics.is_empty(),
            "{name}: {:?}",
            report
                .diagnostics
                .iter()
                .map(|d| format!("{}: {}", d.code, d.message))
                .collect::<Vec<_>>()
        );
    }
}
