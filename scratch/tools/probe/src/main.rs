//! Sonda de desarrollo: pasa un `.pengu` por todo el pipeline y muestra el
//! diagnóstico de cada etapa. No forma parte del compilador.

use std::process::Command;

use pengu_codegen::generate;
use pengu_diag::{Diagnostic, Severity};
use pengu_hir::lower_program;
use pengu_lir::lower_crate;
use pengu_span::FileId;
use pengu_std::with_std;
use pengu_syntax::ast::{Item, ItemKind, Program};
use pengu_syntax::parse_program;
use pengu_types::check_crate;

fn line_of(source: &str, offset: u32) -> usize {
    source[..(offset as usize).min(source.len())]
        .bytes()
        .filter(|b| *b == b'\n')
        .count()
        + 1
}

fn report(stage: &str, diags: &[Diagnostic], source: &str, std_source: &str) -> bool {
    let mut bad = false;
    for d in diags {
        if d.severity == Severity::Note || d.severity == Severity::Help {
            continue;
        }
        eprintln!(
            "[{stage}] {} (file {:?} línea {})",
            d.render_compact(),
            d.primary.file,
            if d.primary.file == FileId::new(u32::MAX) {
                line_of(std_source, d.primary.start)
            } else {
                line_of(source, d.primary.start)
            }
        );
        bad |= d.is_error();
    }
    bad
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let path = args.get(1).expect("uso: probe <archivo.pengu> [--emit] [--rustc] [--run]");
    let emit = args.iter().any(|a| a == "--emit");
    let run = args.iter().any(|a| a == "--rustc" || a == "--run");
    let execute = args.iter().any(|a| a == "--run");

    let source = std::fs::read_to_string(path).expect("leer archivo");
    let std_source = pengu_std::source();
    if args.iter().any(|a| a == "--tokens") {
        let lexed = pengu_syntax::lex(FileId::new(0), &source);
        for token in &lexed.tokens {
            if token.kind == pengu_syntax::TokenKind::Whitespace {
                continue;
            }
            println!("{:>5} {:?}", token.span.start, token.kind);
        }
        return;
    }
    let parsed = parse_program(FileId::new(0), &source);
    if report("parse", &parsed.diagnostics, &source, &std_source) {
        std::process::exit(1);
    }
    let program = parsed.program.expect("programa");
    // `--inject <archivo>`: mete los items del archivo dentro del `scroll std`
    // fusionado, para poder probar lo que solo se permite dentro de la stdlib.
    let mut program: Program = program;
    if let Some(pos) = args.iter().position(|a| a == "--inject") {
        let inject = args.get(pos + 1).expect("--inject requiere un archivo");
        let text = std::fs::read_to_string(inject).expect("leer inyección");
        let injected = parse_program(FileId::new(1), &text);
        report("inject", &injected.diagnostics, &source, &std_source);
        let items: Vec<Item> = injected.program.expect("inyección").items;
        program = with_std(&program);
        let std_scroll = program
            .items
            .iter_mut()
            .find_map(|item| match &mut item.kind {
                ItemKind::Scroll(scroll) if scroll.name == "std" => Some(scroll),
                _ => None,
            })
            .expect("scroll std");
        std_scroll.items.extend(items);
    }
    let lowered = lower_program(&program);
    if report("hir", &lowered.diagnostics, &source, &std_source) {
        std::process::exit(1);
    }
    let types = check_crate(&lowered.krate);
    if report("types", &types.diagnostics, &source, &std_source) {
        std::process::exit(1);
    }
    let lir = lower_crate(&lowered.krate, &types);
    if report("lir", &lir.diagnostics, &source, &std_source) {
        std::process::exit(1);
    }
    let generated = generate(&lowered.krate, &lir);
    if report("codegen", &generated.diagnostics, &source, &std_source) {
        std::process::exit(1);
    }
    if emit {
        println!("{}", generated.source);
    }
    if run {
        let dir = std::env::temp_dir().join(format!("pengu-probe-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let file = dir.join("main.rs");
        std::fs::write(&file, &generated.source).unwrap();
        let exe = dir.join("main");
        let out = Command::new("rustc")
            .args(["--edition", "2024", "-A", "warnings"])
            .arg(&file)
            .arg("-o")
            .arg(&exe)
            .output()
            .expect("rustc");
        if !out.status.success() {
            eprintln!("--- rustc stderr ---\n{}", String::from_utf8_lossy(&out.stderr));
            std::process::exit(1);
        }
        if execute {
            let out = Command::new(&exe).output().expect("ejecutar");
            print!("{}", String::from_utf8_lossy(&out.stdout));
            eprint!("{}", String::from_utf8_lossy(&out.stderr));
            if !out.status.success() {
                std::process::exit(out.status.code().unwrap_or(1));
            }
        }
        let _ = std::fs::remove_dir_all(&dir);
    }
}
