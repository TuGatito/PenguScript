use pengu_span::FileId;
use pengu_syntax::lex;

/// Lexes every ```pengu block in the normative spec. This catches tokens that
/// the unit tests miss and keeps F1 honest as the language evolves.
#[test]
fn every_spec_code_block_lexes_cleanly() {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../../docs/LANGUAGE.md");
    let text = std::fs::read_to_string(path).expect("docs/LANGUAGE.md must exist");

    let mut blocks = Vec::new();
    let mut start_line = 0usize;
    let mut in_block = false;
    let mut buf = String::new();

    for (index, line) in text.lines().enumerate() {
        if !in_block && line.trim_start().starts_with("```pengu") {
            in_block = true;
            start_line = index + 1;
            buf.clear();
        } else if in_block && line.trim_start().starts_with("```") {
            in_block = false;
            blocks.push((start_line, std::mem::take(&mut buf)));
        } else if in_block {
            buf.push_str(line);
            buf.push('\n');
        }
    }

    assert!(
        blocks.len() >= 146,
        "only {} pengu blocks found",
        blocks.len()
    );

    let mut failures = Vec::new();
    for (line, code) in &blocks {
        let lexed = lex(FileId::new(1), code);
        if !lexed.is_clean() {
            failures.push((*line, code, lexed));
        }
    }

    if !failures.is_empty() {
        for (line, code, lexed) in &failures {
            eprintln!("--- pengu block at docs/LANGUAGE.md:{line} ---");
            for diagnostic in &lexed.diagnostics {
                eprintln!("{}: {}", diagnostic.code, diagnostic.message);
            }
            eprintln!(
                "first lines:\n{}",
                code.lines().take(4).collect::<Vec<_>>().join("\n")
            );
        }
        panic!(
            "{} of {} spec code blocks have lexical errors",
            failures.len(),
            blocks.len()
        );
    }
}
