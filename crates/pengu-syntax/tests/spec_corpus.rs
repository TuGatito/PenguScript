use pengu_span::FileId;
use pengu_syntax::{parse_declaration_file, parse_expression, parse_program};

struct Block {
    line: usize,
    code: String,
}

fn spec_blocks() -> Vec<Block> {
    let text = std::fs::read_to_string(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../docs/LANGUAGE.md"
    ))
    .expect("docs/LANGUAGE.md");
    let mut blocks = Vec::new();
    let mut in_block = false;
    let mut line = 0;
    let mut buf = String::new();
    for (index, text_line) in text.lines().enumerate() {
        let trimmed = text_line.trim_start();
        if !in_block && trimmed.starts_with("```pengu") {
            in_block = true;
            line = index + 1;
            buf.clear();
        } else if in_block && trimmed.starts_with("```") {
            blocks.push(Block {
                line,
                code: std::mem::take(&mut buf),
            });
            in_block = false;
        } else if in_block {
            buf.push_str(text_line);
            buf.push('\n');
        }
    }
    blocks
}

fn clean_program(code: &str) -> bool {
    parse_program(FileId::new(1), code).diagnostics.is_empty()
}

fn clean_decl(code: &str) -> bool {
    parse_declaration_file(FileId::new(1), code)
        .diagnostics
        .is_empty()
}

fn clean_expr(code: &str) -> bool {
    parse_expression(FileId::new(1), code)
        .diagnostics
        .is_empty()
}

fn wrapped(code: &str) -> String {
    let mut out = String::from("grimoire\n");
    for line in code.lines() {
        out.push_str("    ");
        out.push_str(line);
        out.push('\n');
    }
    out
}

fn is_declaration(code: &str) -> bool {
    code.lines()
        .map(str::trim_start)
        .find(|line| !line.is_empty() && !line.starts_with("--"))
        .is_some_and(|line| line.starts_with("abi "))
}

fn accepts(code: &str) -> bool {
    if is_declaration(code) {
        return clean_decl(code);
    }
    clean_program(code) || clean_expr(code) || clean_program(&wrapped(code))
}

fn top_level_chunks(code: &str) -> Vec<String> {
    let mut chunks: Vec<String> = Vec::new();
    let mut current = String::new();
    for line in code.lines() {
        let starts_top = !line.trim().is_empty() && !line.starts_with(' ');
        if starts_top && !current.trim().is_empty() {
            chunks.push(std::mem::take(&mut current));
        }
        current.push_str(line);
        current.push('\n');
    }
    if !current.trim().is_empty() {
        chunks.push(current);
    }
    chunks
}

fn accepted_fragment(code: &str) -> bool {
    if accepts(code) {
        return true;
    }
    let chunks = top_level_chunks(code);
    chunks.len() > 1 && chunks.iter().all(|chunk| accepts(chunk))
}

#[test]
fn every_spec_block_parses_or_is_an_error_example() {
    let blocks = spec_blocks();
    assert!(
        blocks.len() >= 146,
        "expected at least 146 pengu blocks, found {}",
        blocks.len()
    );
    let mut errors = 0;
    let mut failures = Vec::new();
    for block in &blocks {
        let is_error = block
            .code
            .lines()
            .take(3)
            .any(|line| line.contains("ERROR PGS-"));
        if is_error {
            errors += 1;
            continue;
        }
        if !accepted_fragment(&block.code) {
            failures.push(block);
        }
    }
    assert!(errors >= 5, "expected the semantic error examples");
    if !failures.is_empty() {
        for block in &failures {
            eprintln!("--- docs/LANGUAGE.md:{} ---", block.line);
            for line in block.code.lines().take(6) {
                eprintln!("| {line}");
            }
        }
        panic!("{} spec blocks do not parse", failures.len());
    }
}
