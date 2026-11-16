use pengu_span::{DUMMY_FILE, FileId, Span};
use pengu_syntax::ast::ExprKind;
use pengu_syntax::{
    SyntaxKind, SyntaxTree, parse_declaration_file, parse_expression, parse_program,
};

fn prog(source: &str) -> pengu_syntax::ParsedProgram {
    parse_program(DUMMY_FILE, source)
}

fn assert_lossless(source: &str, tree: &SyntaxTree) {
    assert_eq!(tree.reconstruct(), source);
    assert_eq!(tree.leaf_tokens().len(), tree.tokens.len());
}

#[test]
fn reconstructs_source_with_trivia_and_comments() {
    let source = "-- cabecera\n\nscroll magia\n    rune Point\n        x: Int\n";
    let parsed = prog(source);
    let tree = parsed.tree.expect("CST");
    assert_lossless(source, &tree);
    assert!(tree.leaf_tokens().iter().any(|t| {
        matches!(t.kind, pengu_syntax::TokenKind::Comment(_)) && t.text.contains("cabecera")
    }));
}

#[test]
fn contains_item_nodes() {
    let source = "rune Point\n    x: Int\n\ngrimoire\n    bind p = Point(x: 1)\n";
    let parsed = prog(source);
    let tree = parsed.tree.expect("CST");
    assert!(has_kind(&tree, SyntaxKind::Rune));
    assert!(has_kind(&tree, SyntaxKind::Grimoire));
    assert!(has_kind(&tree, SyntaxKind::Expr));
}

fn has_kind(tree: &SyntaxTree, kind: SyntaxKind) -> bool {
    fn walk(node: &pengu_syntax::SyntaxNode, kind: SyntaxKind) -> bool {
        if node.kind == kind {
            return true;
        }
        node.children.iter().any(|child| match child {
            pengu_syntax::SyntaxElement::Node(node) => walk(node, kind),
            pengu_syntax::SyntaxElement::Token(_) => false,
        })
    }
    walk(&tree.root, kind)
}

#[test]
fn partial_tree_survives_errors() {
    let source = "rune";
    let parsed = prog(source);
    assert!(!parsed.diagnostics.is_empty());
    let tree = parsed.tree.expect("CST parcial");
    assert_eq!(tree.reconstruct(), source);
    assert_eq!(tree.errors, parsed.diagnostics);
}

#[test]
fn diagnostics_are_capped_at_one_hundred() {
    let source = "\u{0001}".repeat(150);
    let parsed = prog(&source);
    assert!(parsed.diagnostics.len() <= 100);
    let tree = parsed.tree.expect("CST");
    assert!(tree.errors.len() <= 100);
    assert_eq!(tree.reconstruct(), source);
}

#[test]
fn node_at_maps_ast_spans_to_cst() {
    let source = "rune Point\n    x: Int\n";
    let parsed = prog(source);
    let program = parsed.program.as_ref().expect("programa");
    let item = &program.items[0];
    let tree = parsed.tree.expect("CST");
    let node = tree.node_at(item.span).expect("nodo del item");
    assert!(
        matches!(node.kind, SyntaxKind::Rune | SyntaxKind::Item),
        "kind={:?} span={:?} item={:?}",
        node.kind,
        node.span,
        item.span
    );
    assert!(
        tree.node_at(Span::new(FileId::new(7), 0, item.span.end))
            .is_none()
    );
}

#[test]
fn program_root_is_a_program_node() {
    let parsed = prog("grimoire\n    return 0\n");
    let tree = parsed.tree.expect("CST");
    assert_eq!(tree.root.kind, SyntaxKind::Program);
    assert!(has_kind(&tree, SyntaxKind::Program));
}

#[test]
fn expression_diagnostics_are_capped_at_one_hundred() {
    let source = "\u{0001}".repeat(150);
    let parsed = parse_expression(DUMMY_FILE, &source);
    assert!(parsed.diagnostics.len() <= 100);
    let tree = parsed.tree.expect("CST");
    assert!(tree.errors.len() <= 100);
    assert_eq!(tree.reconstruct(), source);
}

#[test]
fn declaration_file_has_lossless_tree() {
    let source = "abi \"C\"\nputs = (s: &Str) -> Int\n";
    let parsed = parse_declaration_file(DUMMY_FILE, source);
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
    let tree = parsed.tree.expect("CST");
    assert!(has_kind(&tree, SyntaxKind::DeclarationFile));
    assert_lossless(source, &tree);
}

#[test]
fn record_update_base_is_in_cst() {
    let parsed = parse_expression(DUMMY_FILE, "Point(y: 2, ..p)");
    assert!(parsed.diagnostics.is_empty(), "{:?}", parsed.diagnostics);
    let expr = parsed.expr.expect("expression");
    let base = match expr.kind {
        ExprKind::Record {
            base: Some(base), ..
        } => *base,
        other => panic!("expected record update, got {other:?}"),
    };
    let tree = parsed.tree.expect("CST");
    let node = tree.node_at(base.span).expect("base node");
    assert!(node.span.start <= base.span.start && node.span.end >= base.span.end);
}

#[test]
fn expression_parse_is_clean() {
    let source = "1 + 2 * 3";
    let parsed = parse_expression(DUMMY_FILE, source);
    assert!(parsed.is_clean(), "{:?}", parsed.diagnostics);
    assert!(parsed.expr.is_some());
    let tree = parsed.tree.expect("CST de expresión");
    assert_eq!(tree.reconstruct(), source);
    assert!(has_kind(&tree, SyntaxKind::Expr));
}

#[test]
fn corpus_pengu_blocks_reconstruct_exactly() {
    let doc = std::fs::read_to_string(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../docs/LANGUAGE.md"
    ))
    .expect("LANGUAGE.md");
    let mut blocks = Vec::new();
    let mut current: Option<String> = None;
    for line in doc.lines() {
        if current.is_none() && line.trim_start().starts_with("```pengu") {
            current = Some(String::new());
        } else if current.is_some() && line.trim_start().starts_with("```") {
            blocks.push(current.take().unwrap());
        } else if let Some(block) = current.as_mut() {
            block.push_str(line);
            block.push('\n');
        }
    }
    assert!(blocks.len() > 100, "bloques: {}", blocks.len());
    for (index, source) in blocks.iter().enumerate() {
        let parsed = prog(source);
        let tree = parsed.tree.expect("CST");
        assert_eq!(tree.reconstruct(), *source, "bloque {index} no reconstruye");
        assert_eq!(
            tree.leaf_tokens().len(),
            tree.tokens.len(),
            "bloque {index}"
        );
        assert_well_formed(&tree.root, tree.root.span);
    }
}

#[test]
fn nodes_are_nested_and_ordered() {
    let source = "-- antes\nscroll outer\n    rune Point\n        x: Int\n    length = (p: Point) -> Int\n        p.x\n\ngrimoire\n    bind p = Point(x: 1)\n    print(length(p))\n";
    let parsed = prog(source);
    let tree = parsed.tree.expect("CST");
    assert_well_formed(&tree.root, tree.root.span);
    assert_eq!(tree.root.span.start, 0);
    assert_eq!(tree.root.span.end, source.len() as u32);
}

fn assert_well_formed(node: &pengu_syntax::SyntaxNode, parent: pengu_span::Span) {
    assert!(node.span.start >= parent.start);
    assert!(node.span.end <= parent.end);
    let mut previous = 0;
    for child in &node.children {
        let span = child.span();
        assert!(span.start >= node.span.start);
        assert!(span.end <= node.span.end);
        assert!(span.start >= previous || span.start == 0);
        previous = span.end;
        if let pengu_syntax::SyntaxElement::Node(child) = child {
            assert_well_formed(child, node.span);
        }
    }
}

#[test]
fn recovers_to_later_items() {
    let source = "rune\n\ngrimoire\n    print(1)\n";
    let parsed = prog(source);
    assert!(!parsed.diagnostics.is_empty());
    let tree = parsed.tree.expect("CST");
    assert!(has_kind(&tree, SyntaxKind::Grimoire));
    assert_eq!(tree.reconstruct(), source);
}

#[test]
fn pseudo_random_sources_do_not_panic_and_reconstruct() {
    const ALPHABET: &[char] = &[
        'a', 'Z', '_', '0', '1', ' ', ' ', '\n', '\t', 'r', 'u', 'n', 'e', ':', '=', '+', '-', '*',
        '/', '(', ')', '[', ']', '{', '}', ',', ';', '.', '@', '&', '?', '"', '\'', 'π', 'ß', '💥',
    ];
    let mut state = 0x1234_5678_u64;
    for _ in 0..200 {
        let mut source = String::new();
        let length = (state % 110) as usize;
        for _ in 0..length {
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            source.push(ALPHABET[(state as usize) % ALPHABET.len()]);
        }
        let parsed = prog(&source);
        let tree = parsed.tree.expect("CST");
        assert_eq!(tree.reconstruct(), source);
        assert_eq!(tree.leaf_tokens().len(), tree.tokens.len());
    }
}

#[test]
fn preserves_utf8_crlf_bom_tabs_and_interpolation() {
    for source in [
        "\u{feff}grimoire\n    return 0\n",
        "grimoire\r\n    return 0\r\n",
        "bind nombre = \"pengüino\"\nbind s = \"hola #{nombre}\"\n",
        "bind ñ = 1\n",
        "grimoire\n\treturn 0\n",
        "grimoire\n\n\n    -- comentario\n    return 0\n",
    ] {
        let parsed = parse_program(DUMMY_FILE, source);
        let tree = parsed.tree.expect("tree");
        assert_eq!(tree.reconstruct(), source);
        assert_well_formed(&tree.root, tree.root.span);
        assert_eq!(tree.leaf_tokens().len(), tree.tokens.len());
    }
}
