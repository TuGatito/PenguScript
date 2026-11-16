//! CST lossless construido a partir del AST y del flujo de tokens.
//!
//! El CST conserva todos los tokens, incluidos comentarios, `NEWLINE`,
//! `INDENT`, `DEDENT` y `EOF`. El AST sigue siendo la vista tipada; este árbol
//! se usa para formateo, análisis incremental y diagnóstico con spans.

use std::cmp::Reverse;

use pengu_diag::Diagnostic;
use pengu_span::{FileId, Span};

use crate::ast::{
    Block, Const, DeclarationFile, Enchanting, Essence, Expr, ExprKind, Field, Foreign, Function,
    FunctionSig, Grimoire, Item, ItemKind, Method, Pact, Param, Pattern, PatternKind, Program,
    Ritual, RitualItem, Rune, Scroll, Stmt, StmtKind, StringPart, Summon, Test, TestOption, Type,
    TypeKind, TypeParam, Variant, VariantFields,
};
use crate::{Token, TokenKind};

/// Tipo de nodo del CST.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum SyntaxKind {
    /// Raíz del archivo.
    Root,
    /// Programa completo.
    Program,
    /// Archivo `.d.pengu`.
    DeclarationFile,
    /// Item genérico.
    Item,
    /// `scroll`.
    Scroll,
    /// `summon`.
    Summon,
    /// `rune`.
    Rune,
    /// `enchanting`.
    Enchanting,
    /// `pact`.
    Pact,
    /// `ritual`.
    Ritual,
    /// `essence`.
    Essence,
    /// `foreign`.
    Foreign,
    /// Función.
    Function,
    /// `sigil`/`relic`.
    Const,
    /// `grimoire`.
    Grimoire,
    /// `@@test`.
    Test,
    /// Firma de función.
    FunctionSig,
    /// Parámetro de tipo.
    TypeParam,
    /// Campo de record/variante.
    Field,
    /// Variante.
    Variant,
    /// Método.
    Method,
    /// Parámetro.
    Param,
    /// Bloque.
    Block,
    /// Sentencia.
    Stmt,
    /// Expresión.
    Expr,
    /// Tipo.
    Type,
    /// Patrón.
    Pattern,
    /// Nodo de error recuperable.
    Error,
}

/// Token hoja del CST.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SyntaxToken {
    /// Tipo de token.
    pub kind: TokenKind,
    /// Rango en el archivo.
    pub span: Span,
    /// Texto exacto.
    pub text: String,
}

/// Elemento del CST.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum SyntaxElement {
    /// Nodo interno.
    Node(Box<SyntaxNode>),
    /// Token hoja.
    Token(SyntaxToken),
}

impl SyntaxElement {
    /// Span del elemento.
    #[must_use]
    pub fn span(&self) -> Span {
        match self {
            Self::Node(node) => node.span,
            Self::Token(token) => token.span,
        }
    }
}

/// Nodo interno del CST.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SyntaxNode {
    /// Tipo de nodo.
    pub kind: SyntaxKind,
    /// Rango que cubre.
    pub span: Span,
    /// Hijos en orden de fuente.
    pub children: Vec<SyntaxElement>,
}

impl SyntaxNode {
    /// Crea un nodo.
    #[must_use]
    pub fn new(kind: SyntaxKind, span: Span, children: Vec<SyntaxElement>) -> Self {
        Self {
            kind,
            span,
            children,
        }
    }

    /// Recorre todos los tokens hoja en orden.
    pub fn for_each_token(&self, f: &mut impl FnMut(&SyntaxToken)) {
        for child in &self.children {
            match child {
                SyntaxElement::Node(node) => node.for_each_token(f),
                SyntaxElement::Token(token) => f(token),
            }
        }
    }
}

/// Árbol sintáctico concreto lossless.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SyntaxTree {
    /// Raíz.
    pub root: SyntaxNode,
    /// Diagnósticos léxicos y sintácticos.
    pub errors: Vec<Diagnostic>,
    /// Todos los tokens, en orden.
    pub tokens: Vec<SyntaxToken>,
    /// Texto fuente original.
    pub source: String,
}

impl SyntaxTree {
    /// Construye el CST de un programa.
    #[must_use]
    pub(crate) fn for_program(
        file: FileId,
        source: &str,
        tokens: &[Token],
        program: Option<&Program>,
        errors: Vec<Diagnostic>,
    ) -> Self {
        let mut collector = Collector::new();
        if let Some(program) = program {
            collector.program(program);
        }
        let root_kind = if program.is_some() {
            SyntaxKind::Program
        } else {
            SyntaxKind::Root
        };
        Self::build(file, source, tokens, collector.nodes, errors, root_kind)
    }

    /// Construye el CST de una expresión.
    #[must_use]
    pub(crate) fn for_expression(
        file: FileId,
        source: &str,
        tokens: &[Token],
        expr: Option<&Expr>,
        errors: Vec<Diagnostic>,
    ) -> Self {
        let mut collector = Collector::new();
        if let Some(expr) = expr {
            collector.expr(expr);
        }
        let root_kind = if expr.is_some() {
            SyntaxKind::Expr
        } else {
            SyntaxKind::Root
        };
        Self::build(file, source, tokens, collector.nodes, errors, root_kind)
    }

    /// Construye el CST de un archivo `.d.pengu`.
    #[must_use]
    pub(crate) fn for_declaration(
        file: FileId,
        source: &str,
        tokens: &[Token],
        declaration: Option<&DeclarationFile>,
        errors: Vec<Diagnostic>,
    ) -> Self {
        let mut collector = Collector::new();
        if let Some(declaration) = declaration {
            collector.declaration_file(declaration);
        }
        let root_kind = if declaration.is_some() {
            SyntaxKind::DeclarationFile
        } else {
            SyntaxKind::Root
        };
        Self::build(file, source, tokens, collector.nodes, errors, root_kind)
    }

    fn build(
        file: FileId,
        source: &str,
        tokens: &[Token],
        raw_nodes: Vec<RawNode>,
        errors: Vec<Diagnostic>,
        root_kind: SyntaxKind,
    ) -> Self {
        let mut source_tokens = Vec::with_capacity(tokens.len());
        let mut cursor = 0usize;
        for token in tokens {
            let start = token.span.start as usize;
            let end = token.span.end as usize;
            if start > cursor {
                source_tokens.push(SyntaxToken {
                    kind: TokenKind::Whitespace,
                    span: Span::new(file, cursor as u32, start as u32),
                    text: source[cursor..start].to_owned(),
                });
            }
            let start = start.max(cursor);
            let end = end.max(start);
            source_tokens.push(SyntaxToken {
                kind: token.kind,
                span: Span::new(file, start as u32, end as u32),
                text: source[start..end].to_owned(),
            });
            cursor = end;
        }
        if cursor < source.len() {
            source_tokens.push(SyntaxToken {
                kind: TokenKind::Whitespace,
                span: Span::new(file, cursor as u32, source.len() as u32),
                text: source[cursor..].to_owned(),
            });
        }

        let root_span = Span::new(file, 0, source.len() as u32);
        let mut nodes = vec![RawNode {
            kind: root_kind,
            span: root_span,
        }];
        let mut seen: std::collections::HashSet<(u32, u32, SyntaxKind)> =
            std::collections::HashSet::with_capacity(raw_nodes.len());
        for node in raw_nodes {
            if node.span.end <= node.span.start {
                continue;
            }
            if seen.insert((node.span.start, node.span.end, node.kind)) {
                nodes.push(node);
            }
        }

        let mut order: Vec<usize> = (1..nodes.len()).collect();
        order.sort_by_key(|&index| {
            let span = nodes[index].span;
            (span.start, Reverse(span.end))
        });

        let mut children: Vec<Vec<usize>> = vec![Vec::new(); nodes.len()];
        let mut stack = vec![0usize];
        for index in order {
            while let Some(&parent) = stack.last() {
                if contains(nodes[parent].span, nodes[index].span) {
                    break;
                }
                stack.pop();
            }
            if let Some(&parent) = stack.last() {
                if parent != index {
                    children[parent].push(index);
                }
            }
            stack.push(index);
        }

        let owners = assign_owners(&nodes, &children, &source_tokens);
        let mut buckets: Vec<Vec<usize>> = vec![Vec::new(); nodes.len()];
        for (token_index, &owner) in owners.iter().enumerate() {
            buckets[owner].push(token_index);
        }
        let root = build_node(0, &nodes, &children, &source_tokens, &buckets);
        Self {
            root,
            errors,
            tokens: source_tokens,
            source: source.to_owned(),
        }
    }

    /// Devuelve el nodo más pequeño que contiene `span`.
    ///
    /// El AST no guarda referencias al CST; sus spans públicos se usan con
    /// esta consulta para obtener el nodo concreto correspondiente.
    #[must_use]
    pub fn node_at(&self, span: Span) -> Option<&SyntaxNode> {
        fn visit(node: &SyntaxNode, span: Span) -> Option<&SyntaxNode> {
            for child in &node.children {
                if let SyntaxElement::Node(child) = child {
                    if contains(child.span, span) {
                        return visit(child, span);
                    }
                }
            }
            contains(node.span, span).then_some(node)
        }
        visit(&self.root, span)
    }

    /// Reconstruye el texto original concatenando los tokens hoja.
    #[must_use]
    pub fn reconstruct(&self) -> String {
        let mut out = String::with_capacity(self.source.len());
        self.root
            .for_each_token(&mut |token| out.push_str(&token.text));
        out
    }

    /// Devuelve los tokens hoja en orden.
    #[must_use]
    pub fn leaf_tokens(&self) -> Vec<&SyntaxToken> {
        fn walk<'a>(node: &'a SyntaxNode, out: &mut Vec<&'a SyntaxToken>) {
            for child in &node.children {
                match child {
                    SyntaxElement::Node(node) => walk(node, out),
                    SyntaxElement::Token(token) => out.push(token),
                }
            }
        }

        let mut out = Vec::new();
        walk(&self.root, &mut out);
        out
    }
}

fn contains(outer: Span, inner: Span) -> bool {
    outer.file == inner.file && inner.start >= outer.start && inner.end <= outer.end
}

fn assign_owners(nodes: &[RawNode], children: &[Vec<usize>], tokens: &[SyntaxToken]) -> Vec<usize> {
    let mut owners = vec![0usize; tokens.len()];

    // Los tokens de ancho cero (Indent/Dedent) no están *dentro* de ningún
    // span; se asignan al nodo que empieza o termina exactamente en su
    // posición, igual que hacía la búsqueda lineal original.
    let mut dedent: std::collections::HashMap<u32, usize> = std::collections::HashMap::new();
    let mut indent: std::collections::HashMap<u32, usize> = std::collections::HashMap::new();
    for (index, node) in nodes.iter().enumerate().skip(1) {
        if node.span.end <= node.span.start {
            continue;
        }
        dedent
            .entry(node.span.end)
            .and_modify(|current| {
                if node.span.start >= nodes[*current].span.start {
                    *current = index;
                }
            })
            .or_insert(index);
        indent
            .entry(node.span.start)
            .and_modify(|current| {
                if node.span.end >= nodes[*current].span.end {
                    *current = index;
                }
            })
            .or_insert(index);
    }

    // Los tokens con span real se asignan al nodo más interno que los
    // contiene, avanzando una pila de contención en orden de documento: cada
    // nodo y cada token se visitan una sola vez.
    let mut stack = vec![0usize];
    let mut cursors = vec![0usize];
    for (index, token) in tokens.iter().enumerate() {
        if token.span.start == token.span.end {
            let exact = match token.kind {
                TokenKind::Eof => Some(0),
                TokenKind::Dedent => dedent.get(&token.span.start).copied(),
                TokenKind::Indent => indent.get(&token.span.start).copied(),
                _ => None,
            };
            if let Some(owner) = exact {
                owners[index] = owner;
                continue;
            }
        }
        while stack.len() > 1 && token.span.start >= nodes[stack[stack.len() - 1]].span.end {
            stack.pop();
            cursors.pop();
        }
        loop {
            let depth = stack.len() - 1;
            let node = stack[depth];
            while cursors[depth] < children[node].len()
                && nodes[children[node][cursors[depth]]].span.end <= token.span.start
            {
                cursors[depth] += 1;
            }
            let Some(&child) = children[node].get(cursors[depth]) else {
                break;
            };
            if contains(nodes[child].span, token.span) {
                stack.push(child);
                cursors.push(0);
            } else {
                break;
            }
        }
        owners[index] = stack[stack.len() - 1];
    }

    owners
}

fn build_node(
    index: usize,
    nodes: &[RawNode],
    children: &[Vec<usize>],
    tokens: &[SyntaxToken],
    buckets: &[Vec<usize>],
) -> SyntaxNode {
    let node = nodes[index];
    let mut elements: Vec<SyntaxElement> = Vec::new();

    for &child in &children[index] {
        elements.push(SyntaxElement::Node(Box::new(build_node(
            child, nodes, children, tokens, buckets,
        ))));
    }

    for &token_index in &buckets[index] {
        elements.push(SyntaxElement::Token(tokens[token_index].clone()));
    }

    elements.sort_by_key(|element| {
        let span = element.span();
        (span.start, span.end)
    });

    SyntaxNode::new(node.kind, node.span, elements)
}

#[derive(Clone, Copy)]
struct RawNode {
    kind: SyntaxKind,
    span: Span,
}

struct Collector {
    nodes: Vec<RawNode>,
    seen: std::collections::HashSet<(u32, u32, SyntaxKind)>,
}

impl Collector {
    fn new() -> Self {
        Self {
            nodes: Vec::new(),
            seen: std::collections::HashSet::new(),
        }
    }

    fn add(&mut self, kind: SyntaxKind, span: Span) {
        if span.end <= span.start {
            return;
        }
        if !self.seen.insert((span.start, span.end, kind)) {
            return;
        }
        self.nodes.push(RawNode { kind, span });
    }

    fn program(&mut self, program: &Program) {
        for item in &program.items {
            self.item(item);
        }
    }

    fn declaration_file(&mut self, file: &DeclarationFile) {
        for item in &file.items {
            self.item(item);
        }
    }

    fn item(&mut self, item: &Item) {
        let kind = match &item.kind {
            ItemKind::Scroll(_) => SyntaxKind::Scroll,
            ItemKind::Summon(_) => SyntaxKind::Summon,
            ItemKind::Rune(_) => SyntaxKind::Rune,
            ItemKind::Enchanting(_) => SyntaxKind::Enchanting,
            ItemKind::Pact(_) => SyntaxKind::Pact,
            ItemKind::Ritual(_) => SyntaxKind::Ritual,
            ItemKind::Essence(_) => SyntaxKind::Essence,
            ItemKind::Foreign(_) => SyntaxKind::Foreign,
            ItemKind::Function(_) => SyntaxKind::Function,
            ItemKind::Const(_) => SyntaxKind::Const,
            ItemKind::Grimoire(_) => SyntaxKind::Grimoire,
            ItemKind::Test(_) => SyntaxKind::Test,
            ItemKind::FunctionSig(_) => SyntaxKind::FunctionSig,
        };
        self.add(kind, item.span);
        match &item.kind {
            ItemKind::Scroll(scroll) => self.scroll(scroll),
            ItemKind::Summon(summon) => self.summon(summon),
            ItemKind::Rune(rune) => self.rune(rune),
            ItemKind::Enchanting(enchanting) => self.enchanting(enchanting),
            ItemKind::Pact(pact) => self.pact(pact),
            ItemKind::Ritual(ritual) => self.ritual(ritual),
            ItemKind::Essence(essence) => self.essence(essence),
            ItemKind::Foreign(foreign) => self.foreign(foreign),
            ItemKind::Function(function) => self.function(function),
            ItemKind::Const(constant) => self.constant(constant),
            ItemKind::Grimoire(grimoire) => self.grimoire(grimoire),
            ItemKind::Test(test) => self.test(test),
            ItemKind::FunctionSig(sig) => self.function_sig(sig),
        }
    }

    fn scroll(&mut self, scroll: &Scroll) {
        for item in &scroll.items {
            self.item(item);
        }
    }

    fn summon(&mut self, _summon: &Summon) {}

    fn rune(&mut self, rune: &Rune) {
        for param in &rune.params {
            self.type_param(param);
        }
        for field in &rune.fields {
            self.field(field);
        }
        for method in &rune.methods {
            self.method(method);
        }
    }

    fn enchanting(&mut self, enchanting: &Enchanting) {
        for param in &enchanting.params {
            self.type_param(param);
        }
        for variant in &enchanting.variants {
            self.variant(variant);
        }
    }

    fn pact(&mut self, pact: &Pact) {
        for param in &pact.params {
            self.type_param(param);
        }
        for method in &pact.methods {
            self.method(method);
        }
    }

    fn ritual(&mut self, ritual: &Ritual) {
        for param in &ritual.params {
            self.type_param(param);
        }
        self.ty(&ritual.ty);
        for item in &ritual.items {
            match item {
                RitualItem::Method(method) => self.method(method),
                RitualItem::Function(function) => self.function(function),
                RitualItem::Const(constant) => self.constant(constant),
            }
        }
    }

    fn essence(&mut self, essence: &Essence) {
        for param in &essence.params {
            self.type_param(param);
        }
        self.ty(&essence.ty);
    }

    fn foreign(&mut self, foreign: &Foreign) {
        for sig in &foreign.items {
            self.function_sig(sig);
        }
    }

    fn function(&mut self, function: &Function) {
        for param in &function.type_params {
            self.type_param(param);
        }
        for param in &function.params {
            self.param(param);
        }
        self.ty(&function.ret);
        self.block(&function.body);
    }

    fn constant(&mut self, constant: &Const) {
        self.ty(&constant.ty);
        if let Some(value) = &constant.value {
            self.expr(value);
        }
    }

    fn grimoire(&mut self, grimoire: &Grimoire) {
        if let Some(ret) = &grimoire.ret {
            self.ty(ret);
        }
        self.block(&grimoire.body);
    }

    fn test(&mut self, test: &Test) {
        for option in &test.options {
            self.test_option(option);
        }
        self.ty(&test.ret);
        self.block(&test.body);
    }

    fn test_option(&mut self, option: &TestOption) {
        self.add(SyntaxKind::Param, option.span);
    }

    fn function_sig(&mut self, sig: &FunctionSig) {
        for param in &sig.params {
            self.param(param);
        }
        self.ty(&sig.ret);
    }

    fn type_param(&mut self, param: &TypeParam) {
        self.add(SyntaxKind::TypeParam, param.span);
    }

    fn field(&mut self, field: &Field) {
        self.add(SyntaxKind::Field, field.span);
        self.ty(&field.ty);
    }

    fn variant(&mut self, variant: &Variant) {
        self.add(SyntaxKind::Variant, variant.span);
        match &variant.fields {
            VariantFields::Unit => {}
            VariantFields::Tuple(types) => {
                for ty in types {
                    self.ty(ty);
                }
            }
            VariantFields::Named(fields) => {
                for field in fields {
                    self.field(field);
                }
            }
        }
    }

    fn method(&mut self, method: &Method) {
        self.add(SyntaxKind::Method, method.span);
        for param in &method.params {
            self.param(param);
        }
        self.ty(&method.ret);
        if let Some(body) = &method.body {
            self.block(body);
        }
    }

    fn param(&mut self, param: &Param) {
        self.add(SyntaxKind::Param, param.span);
        self.ty(&param.ty);
    }

    fn block(&mut self, block: &Block) {
        self.add(SyntaxKind::Block, block.span);
        for stmt in &block.stmts {
            self.stmt(stmt);
        }
    }

    fn stmt(&mut self, stmt: &Stmt) {
        self.add(SyntaxKind::Stmt, stmt.span);
        match &stmt.kind {
            StmtKind::Bind {
                pattern,
                ty,
                value,
                else_block,
                ..
            } => {
                self.pattern(pattern);
                if let Some(ty) = ty {
                    self.ty(ty);
                }
                self.expr(value);
                if let Some(block) = else_block {
                    self.block(block);
                }
            }
            StmtKind::Assign { target, value } => {
                self.expr(target);
                self.expr(value);
            }
            StmtKind::Expr(expr) => self.expr(expr),
            StmtKind::While { cond, body } => {
                self.expr(cond);
                self.block(body);
            }
            StmtKind::For {
                pattern,
                iter,
                body,
            } => {
                self.pattern(pattern);
                self.expr(iter);
                self.block(body);
            }
            StmtKind::Return(value) | StmtKind::Break(value) => {
                if let Some(value) = value {
                    self.expr(value);
                }
            }
            StmtKind::Continue => {}
        }
    }

    fn expr(&mut self, expr: &Expr) {
        self.add(SyntaxKind::Expr, expr.span);
        match &expr.kind {
            ExprKind::Unit
            | ExprKind::Bool(_)
            | ExprKind::None
            | ExprKind::Int(_)
            | ExprKind::Float(_)
            | ExprKind::Char(_)
            | ExprKind::ByteChar(_)
            | ExprKind::Path(_)
            | ExprKind::SelfValue => {}
            ExprKind::String(string) => {
                for part in &string.parts {
                    if let StringPart::Expr(expr) = part {
                        self.expr(expr);
                    }
                }
            }
            ExprKind::Record { fields, base, .. } => {
                for (_, value) in fields {
                    self.expr(value);
                }
                if let Some(base) = base {
                    self.expr(base);
                }
            }
            ExprKind::Tuple(items) | ExprKind::Array(items) | ExprKind::Vector(items) => {
                for item in items {
                    self.expr(item);
                }
            }
            ExprKind::ArrayRepeat { value, count } => {
                self.expr(value);
                self.expr(count);
            }
            ExprKind::Map(entries) => {
                for (key, value) in entries {
                    self.expr(key);
                    self.expr(value);
                }
            }
            ExprKind::Set(items) => {
                for item in items {
                    self.expr(item);
                }
            }
            ExprKind::Unary { expr, .. } => self.expr(expr),
            ExprKind::Binary { lhs, rhs, .. } => {
                self.expr(lhs);
                self.expr(rhs);
            }
            ExprKind::Range { start, end, .. } => {
                self.expr(start);
                if let Some(end) = end {
                    self.expr(end);
                }
            }
            ExprKind::Cast { expr, ty } => {
                self.expr(expr);
                self.ty(ty);
            }
            ExprKind::Call { callee, args } => {
                self.expr(callee);
                for arg in args {
                    self.expr(arg);
                }
            }
            ExprKind::Index { base, index } => {
                self.expr(base);
                self.expr(index);
            }
            ExprKind::Field { base, .. } | ExprKind::Try(base) => self.expr(base),
            ExprKind::Ref { expr, .. } => self.expr(expr),
            ExprKind::If {
                cond,
                then_branch,
                else_branch,
                ..
            } => {
                self.expr(cond);
                self.block(then_branch);
                if let Some(block) = else_branch {
                    self.block(block);
                }
            }
            ExprKind::Match { scrutinee, arms } => {
                self.expr(scrutinee);
                for arm in arms {
                    if let Some(pattern) = &arm.pattern {
                        self.pattern(pattern);
                    }
                    if let Some(guard) = &arm.guard {
                        self.expr(guard);
                    }
                    self.block(&arm.body);
                }
            }
            ExprKind::Do(block) | ExprKind::Loop(block) | ExprKind::Curse(block) => {
                self.block(block);
            }
            ExprKind::Lambda { params, body } => {
                for param in params {
                    self.param(param);
                }
                self.block(body);
            }
        }
    }

    fn ty(&mut self, ty: &Type) {
        self.add(SyntaxKind::Type, ty.span);
        match &ty.kind {
            TypeKind::Unit | TypeKind::SelfType => {}
            TypeKind::Option(inner) | TypeKind::Slice(inner) | TypeKind::Ptr(inner) => {
                self.ty(inner);
            }
            TypeKind::Ref { inner, .. } => self.ty(inner),
            TypeKind::Array { elem, len } => {
                self.ty(elem);
                self.expr(len);
            }
            TypeKind::Tuple(types) => {
                for ty in types {
                    self.ty(ty);
                }
            }
            TypeKind::Fn { params, ret } => {
                for ty in params {
                    self.ty(ty);
                }
                self.ty(ret);
            }
            TypeKind::Path { args, .. } => {
                for arg in args {
                    self.ty(arg);
                }
            }
        }
    }

    fn pattern(&mut self, pattern: &Pattern) {
        self.add(SyntaxKind::Pattern, pattern.span);
        match &pattern.kind {
            PatternKind::Wildcard | PatternKind::Path(_) | PatternKind::Rest => {}
            PatternKind::Bind { pattern, .. } => self.pattern(pattern),
            PatternKind::Tuple(items) => {
                for item in items {
                    self.pattern(item);
                }
            }
            PatternKind::Variant { args, named, .. } => {
                for arg in args {
                    self.pattern(arg);
                }
                for (_, pattern) in named {
                    self.pattern(pattern);
                }
            }
            PatternKind::Literal(expr) => self.expr(expr),
            PatternKind::Or(items) => {
                for item in items {
                    self.pattern(item);
                }
            }
            PatternKind::Range { start, end, .. } => {
                self.pattern(start);
                if let Some(end) = end {
                    self.pattern(end);
                }
            }
            PatternKind::Slice(items) => {
                for item in items {
                    self.pattern(item);
                }
            }
        }
    }
}
