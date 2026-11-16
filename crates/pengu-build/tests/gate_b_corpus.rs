use pengu_codegen::generate;
use pengu_hir::lower_program;
use pengu_lir::lower_crate;
use pengu_span::FileId;
use pengu_syntax::parse_program;
use pengu_types::check_crate;

/// Bloques que no son ejecutables por diseño, con el motivo. Cualquier fallo
/// nuevo que no esté aquí hace fallar el test: el corpus no puede degradarse
/// en silencio, y cada excepción queda revisada y justificada.
const DECLARED_NON_EXECUTABLE: &[(usize, &str)] = &[
    (
        217,
        "expresión suelta del doc §2 (`none` sin tipo esperado), no es un programa",
    ),
    (
        227,
        "expresión suelta del doc §2 (`42 as Usize`), no es un programa",
    ),
    (
        247,
        "expresión suelta del doc §2 (literal `1.5`), no es un programa",
    ),
    (
        308,
        "expresión suelta del doc §2 (rango `0..10`), no es un programa",
    ),
    (
        739,
        "cita §8: `Result[Int, String] = err(\"no\")`; el literal es `Str` y el constructor de variante no acepta la coerción Str→String",
    ),
    (
        984,
        "LIR: expresión de bloque en `bind` (`bind area =` + bloque indentado) no soportada (N71)",
    ),
    (
        1034,
        "LIR: expresión `do … end` en `bind` no soportada (N71)",
    ),
    (
        1998,
        "`ritual[T]` sobre `rune` genérico: `@.value` se tipa `<error>` (N72)",
    ),
    (
        2079,
        "fuente de `std` (rituales sobre primitivos): solo válida dentro de `scroll std`",
    ),
    (
        2193,
        "`ritual[T]` sobre `rune` genérico: `@.value` se tipa `<error>` (N72)",
    ),
    (
        2477,
        "cita §?: `Result[Int, String] = ok(3)`; misma limitación de coerción en variantes que 739",
    ),
    (
        2576,
        "cita con `grimoire` que usa tipos definidos en la prosa (`ConfigError`, `read_config`)",
    ),
    (
        3896,
        "cita con `grimoire` que usa tipos definidos en la prosa (`AppError`, `load`)",
    ),
];

fn has_grimoire(code: &str) -> bool {
    code.lines().any(|l| {
        let t = l.trim();
        t == "grimoire" || t.starts_with("grimoire:")
    })
}

fn blocks() -> Vec<(usize, String)> {
    let text = std::fs::read_to_string(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../docs/LANGUAGE.md"
    ))
    .unwrap();
    let mut out = Vec::new();
    let mut in_block = false;
    let mut line = 0;
    let mut buf = String::new();
    for (i, l) in text.lines().enumerate() {
        let t = l.trim_start();
        if !in_block && t.starts_with("```pengu") {
            in_block = true;
            line = i + 1;
            buf.clear();
        } else if in_block && t.starts_with("```") {
            out.push((line, std::mem::take(&mut buf)));
            in_block = false;
        } else if in_block {
            buf.push_str(l);
            buf.push('\n');
        }
    }
    out
}

fn wrap(code: &str) -> String {
    let mut out = String::from("grimoire\n");
    for line in code.lines() {
        out.push_str("    ");
        out.push_str(line);
        out.push('\n');
    }
    out
}

fn analyze(code: &str) -> Result<String, String> {
    let p = parse_program(FileId::new(0), code);
    if p.diagnostics.iter().any(pengu_diag::Diagnostic::is_error) {
        return Err(format!("parse: {:?}", p.diagnostics));
    }
    let Some(program) = p.program else {
        return Err("no program".into());
    };
    let lower = lower_program(&program);
    if lower
        .diagnostics
        .iter()
        .any(pengu_diag::Diagnostic::is_error)
    {
        return Err(format!("hir: {:?}", lower.diagnostics));
    }
    let types = check_crate(&lower.krate);
    // Los avisos (`PGS-W*`) no impiden compilar: solo los errores.
    if types
        .diagnostics
        .iter()
        .any(pengu_diag::Diagnostic::is_error)
    {
        return Err(format!("types: {:?}", types.diagnostics));
    }
    let lir = lower_crate(&lower.krate, &types);
    if lir.diagnostics.iter().any(pengu_diag::Diagnostic::is_error) {
        return Err(format!("lir: {:?}", lir.diagnostics));
    }
    let g = generate(&lower.krate, &lir);
    if g.diagnostics.iter().any(pengu_diag::Diagnostic::is_error) {
        return Err(format!("codegen: {:?}", g.diagnostics));
    }
    Ok(g.source)
}

fn compile_rust(index: usize, source: &str) {
    let dir = std::env::temp_dir().join(format!("pengu-b8-{}-{}", std::process::id(), index));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    let rs = dir.join("lib.rs");
    std::fs::write(&rs, source).unwrap();
    let out = std::process::Command::new("rustc")
        .args(["--edition", "2024", "--crate-type", "lib", "-o"])
        .arg(dir.join("libpengu.rlib"))
        .arg(&rs)
        .output()
        .unwrap();
    if !out.status.success() {
        panic!(
            "rustc failed for block {}:\n{}\n--- generated ---\n{}",
            index,
            String::from_utf8_lossy(&out.stderr),
            source
        );
    }
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn corpus_is_fully_classified_with_known_backend_gaps() {
    let blocks = blocks();
    assert_eq!(
        blocks.len(),
        146,
        "the spec corpus changed; update the B8 report"
    );
    let mut errors = 0;
    let mut compiled = 0;
    let mut declarations = 0;
    let mut fragments = 0;
    let mut backend_gaps = 0;
    let mut declared_hits = 0;
    let mut unclassified = Vec::new();
    let declared: std::collections::HashMap<usize, &str> =
        DECLARED_NON_EXECUTABLE.iter().copied().collect();
    let mut failed = Vec::new();
    let mut full_program_gaps = Vec::new();
    for (index, (line, code)) in blocks.iter().enumerate() {
        if code.lines().take(3).any(|l| l.contains("ERROR PGS-")) {
            errors += 1;
            continue;
        }
        let is_declaration = code
            .lines()
            .find(|l| !l.trim().is_empty() && !l.trim().starts_with("--"))
            .map(|l| l.trim().starts_with("abi "))
            .unwrap_or(false)
            || code.lines().any(|l| l.trim_start().starts_with("foreign "));
        let raw = parse_program(FileId::new(0), code);
        let result = if raw.diagnostics.iter().any(pengu_diag::Diagnostic::is_error) {
            analyze(&wrap(code))
        } else {
            analyze(code)
        };
        match result {
            Ok(source) => {
                if is_declaration {
                    declarations += 1;
                } else {
                    compile_rust(index, &source);
                    compiled += 1;
                }
            }
            Err(e) => {
                let excerpt = !has_grimoire(code) && e.contains("no se encuentra");
                if e.starts_with("parse:") || excerpt {
                    fragments += 1;
                } else if declared.contains_key(line) {
                    backend_gaps += 1;
                    declared_hits += 1;
                } else {
                    unclassified.push((line, e.clone()));
                    backend_gaps += 1;
                }
                if code.lines().any(|l| {
                    let t = l.trim();
                    t == "grimoire" || t.starts_with("grimoire:")
                }) {
                    full_program_gaps.push((line, e.clone()));
                }
                failed.push((line, e));
            }
        }
    }
    eprintln!(
        "COUNTS compiled={compiled} decl={declarations} frag={fragments} gaps={backend_gaps} err={errors} full_gaps={}",
        full_program_gaps.len()
    );
    if !full_program_gaps.is_empty() {
        for (line, e) in &full_program_gaps {
            eprintln!("FULL GAP {line}: {}", e.lines().next().unwrap_or(""));
        }
    }
    if std::env::var_os("B8_VERBOSE").is_some() {
        for (line, e) in &failed {
            eprintln!("DIAG {line}\t{}", e.lines().next().unwrap_or(""));
        }
    }
    assert!(
        unclassified.is_empty(),
        "bloques no ejecutables sin declarar (añádelos a DECLARED_NON_EXECUTABLE con el motivo):\n{}",
        unclassified
            .iter()
            .map(|(line, e)| format!("  ({line}, \"...\"), // {}", e.lines().next().unwrap_or("")))
            .collect::<Vec<_>>()
            .join("\n")
    );
    assert_eq!(
        declared_hits,
        DECLARED_NON_EXECUTABLE.len(),
        "hay entradas de DECLARED_NON_EXECUTABLE que ya compilan: quítalas"
    );
    assert_eq!(errors, 5, "error examples changed");
    assert_eq!(
        compiled + declarations + fragments + backend_gaps + errors,
        blocks.len()
    );
    assert_eq!(
        (compiled, declarations, fragments, backend_gaps, errors),
        (68, 4, 56, 13, 5),
        "B8 classification changed; update GATE_B_CORPUS.md"
    );
    eprintln!(
        "B8: {} blocks = {} errors + {} compiled + {} declarations + {} fragments + {} backend gaps",
        blocks.len(),
        errors,
        compiled,
        declarations,
        fragments,
        backend_gaps
    );
    if std::env::var_os("B8_VERBOSE").is_some() {
        for (line, e) in failed {
            eprintln!("line {line}: {}", e.lines().next().unwrap_or(""));
        }
    }
}
