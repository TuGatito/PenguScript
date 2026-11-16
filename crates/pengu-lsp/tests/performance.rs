//! Presupuesto de rendimiento del análisis que usa el servidor.
//!
//! Los umbrales son deliberadamente generosos: se ejecutan en `debug` y en
//! máquinas compartidas. Su objetivo es detectar regresiones cuadráticas, no
//! medir el rendimiento exacto (para eso está `editors/bench.mjs`).

use std::fmt::Write as _;
use std::time::{Duration, Instant};

use pengu_span::FileId;

fn big_program(functions: usize) -> String {
    let mut source = String::with_capacity(functions * 40);
    for index in 0..functions {
        let _ = write!(source, "f{index} = (a: Int) -> Int\n    a + {index}\n");
    }
    source.push_str("\ngrimoire\n    print(f0(1))\n");
    source
}

#[test]
fn analiza_diez_mil_lineas_sin_regresion_cuadratica() {
    let source = big_program(2_500);
    let start = Instant::now();
    let analysis = pengu_lsp::analysis::analyze(FileId::new(1), &source);
    let elapsed = start.elapsed();
    assert!(
        analysis.diagnostics.is_empty(),
        "diagnósticos inesperados: {:?}",
        analysis.diagnostics.first()
    );
    assert!(
        elapsed < Duration::from_secs(10),
        "el análisis de {} líneas tardó {elapsed:?}",
        source.lines().count()
    );
}

#[test]
fn el_indice_se_construye_en_una_pasada() {
    let source = big_program(2_500);
    let parsed = pengu_syntax::parse_program(FileId::new(1), &source);
    let program = parsed.program.expect("programa válido");
    let lowered = pengu_hir::lower_program(&program);
    let start = Instant::now();
    let index = pengu_lsp::index::Index::build(&lowered.krate);
    let elapsed = start.elapsed();
    assert!(index.len() > 2_500);
    assert!(
        elapsed < Duration::from_secs(5),
        "el índice tardó {elapsed:?}"
    );
}
