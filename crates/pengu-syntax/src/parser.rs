//! Parser Pratt de expresiones y de los bloques mínimos que las contienen.

use pengu_diag::Diagnostic;
use pengu_span::{FileId, Span};

use crate::ast::{
    BinOp, Block, Const, ConstKind, DeclarationFile, Enchanting, Essence, Expr, ExprKind, Field,
    Foreign, Function, FunctionSig, Grimoire, Item, ItemKind, MatchArm, Method, Pact, Param,
    Pattern, PatternKind, Program, Receiver, Ritual, RitualItem, Rune, Scroll, Stmt, StmtKind,
    StringLit, StringPart, Summon, Test, TestOption, Type, TypeKind, TypeParam, UnOp, Variant,
    VariantFields, Visibility,
};
use crate::cst::SyntaxTree;
use crate::limits::token_depth_diagnostic;
use crate::{Lexed, StringKind, Token, TokenKind, lex};

/// Resultado de parsear una expresión.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ParsedExpr {
    /// Expresión raíz, si se pudo construir.
    pub expr: Option<Expr>,
    /// CST lossless, incluso si hubo errores.
    pub tree: Option<SyntaxTree>,
    /// Diagnósticos léxicos y sintácticos.
    pub diagnostics: Vec<Diagnostic>,
}

impl ParsedExpr {
    /// `true` si no hubo diagnósticos.
    #[must_use]
    pub fn is_clean(&self) -> bool {
        self.diagnostics.is_empty()
    }
}

/// Resultado de parsear un programa completo.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ParsedProgram {
    /// Programa raíz, si se pudo construir.
    pub program: Option<Program>,
    /// CST lossless, incluso si hubo errores.
    pub tree: Option<SyntaxTree>,
    /// Diagnósticos léxicos y sintácticos.
    pub diagnostics: Vec<Diagnostic>,
}

impl ParsedProgram {
    /// `true` si no hubo diagnósticos.
    #[must_use]
    pub fn is_clean(&self) -> bool {
        self.diagnostics.is_empty()
    }
}

/// Parsea un programa completo desde texto fuente.
#[must_use]
pub fn parse_program(file: FileId, source: &str) -> ParsedProgram {
    let Lexed {
        tokens,
        diagnostics,
    } = lex(file, source);
    let early = diagnostics
        .iter()
        .any(|diagnostic| diagnostic.code == "PGS-E1901")
        .then_some(())
        .is_some();
    let parser_error = token_depth_diagnostic(&tokens);
    if early || parser_error.is_some() {
        let mut diagnostics = diagnostics;
        diagnostics.extend(parser_error);
        diagnostics.truncate(100);
        let tree = SyntaxTree::for_program(file, source, &tokens, None, diagnostics.clone());
        return ParsedProgram {
            program: None,
            tree: Some(tree),
            diagnostics,
        };
    }
    let mut parser = Parser::new(file, source, &tokens);
    let program = parser.parse_program_root();
    let mut diagnostics = diagnostics;
    diagnostics.extend(parser.diagnostics);
    diagnostics.truncate(100);
    let tree =
        SyntaxTree::for_program(file, source, &tokens, program.as_ref(), diagnostics.clone());
    ParsedProgram {
        program,
        tree: Some(tree),
        diagnostics,
    }
}

/// Resultado de parsear un archivo `.d.pengu`.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ParsedDeclaration {
    /// Declaraciones, si se pudo construir.
    pub file: Option<DeclarationFile>,
    /// CST lossless, incluso si hubo errores.
    pub tree: Option<SyntaxTree>,
    /// Diagnósticos léxicos y sintácticos.
    pub diagnostics: Vec<Diagnostic>,
}

impl ParsedDeclaration {
    /// `true` si no hubo diagnósticos.
    #[must_use]
    pub fn is_clean(&self) -> bool {
        self.diagnostics.is_empty()
    }
}

/// Parsea un archivo `.d.pengu`.
#[must_use]
pub fn parse_declaration_file(file: FileId, source: &str) -> ParsedDeclaration {
    let Lexed {
        tokens,
        diagnostics,
    } = lex(file, source);
    let early = diagnostics
        .iter()
        .any(|diagnostic| diagnostic.code == "PGS-E1901")
        .then_some(())
        .is_some();
    let parser_error = token_depth_diagnostic(&tokens);
    if early || parser_error.is_some() {
        let mut diagnostics = diagnostics;
        diagnostics.extend(parser_error);
        diagnostics.truncate(100);
        let tree = SyntaxTree::for_declaration(file, source, &tokens, None, diagnostics.clone());
        return ParsedDeclaration {
            file: None,
            tree: Some(tree),
            diagnostics,
        };
    }
    let mut parser = Parser::new(file, source, &tokens);
    let declaration = parser.parse_declaration_root();
    let mut diagnostics = diagnostics;
    diagnostics.extend(parser.diagnostics);
    diagnostics.truncate(100);
    let tree = SyntaxTree::for_declaration(
        file,
        source,
        &tokens,
        declaration.as_ref(),
        diagnostics.clone(),
    );
    ParsedDeclaration {
        file: declaration,
        tree: Some(tree),
        diagnostics,
    }
}

/// Parsea una expresión completa desde texto fuente.
#[must_use]
pub fn parse_expression(file: FileId, source: &str) -> ParsedExpr {
    let Lexed {
        tokens,
        diagnostics,
    } = lex(file, source);
    let early = diagnostics
        .iter()
        .any(|diagnostic| diagnostic.code == "PGS-E1901")
        .then_some(())
        .is_some();
    let parser_error = token_depth_diagnostic(&tokens);
    if early || parser_error.is_some() {
        let mut diagnostics = diagnostics;
        diagnostics.extend(parser_error);
        diagnostics.truncate(100);
        let tree = SyntaxTree::for_expression(file, source, &tokens, None, diagnostics.clone());
        return ParsedExpr {
            expr: None,
            tree: Some(tree),
            diagnostics,
        };
    }
    let mut parser = Parser::new(file, source, &tokens);
    let expr = parser.parse_root();
    let mut diagnostics = diagnostics;
    diagnostics.extend(parser.diagnostics);
    diagnostics.truncate(100);
    let tree =
        SyntaxTree::for_expression(file, source, &tokens, expr.as_ref(), diagnostics.clone());
    ParsedExpr {
        expr,
        tree: Some(tree),
        diagnostics,
    }
}

struct Parser<'a> {
    file: FileId,
    source: &'a str,
    tokens: &'a [Token],
    pos: usize,
    diagnostics: Vec<Diagnostic>,
}

impl<'a> Parser<'a> {
    fn new(file: FileId, source: &'a str, tokens: &'a [Token]) -> Self {
        Self {
            file,
            source,
            tokens,
            pos: 0,
            diagnostics: Vec::new(),
        }
    }

    fn parse_root(&mut self) -> Option<Expr> {
        self.skip_comments();
        self.skip_newlines();
        if self.at(TokenKind::Eof) {
            self.error("se esperaba una expresión");
            return None;
        }
        let expr = self.parse_bp(0);
        self.skip_comments();
        while self.at(TokenKind::Newline) {
            self.bump();
            self.skip_comments();
        }
        if !self.at(TokenKind::Eof) {
            self.error("tokens inesperados después de la expresión");
        }
        Some(expr)
    }

    // ---------------------------------------------------------------------
    // Tokens
    // ---------------------------------------------------------------------

    fn skip_comments(&mut self) {
        while matches!(
            self.tokens.get(self.pos).map(|t| t.kind),
            Some(TokenKind::Comment(_))
        ) {
            self.pos += 1;
        }
    }

    fn skip_newlines(&mut self) {
        loop {
            self.skip_comments();
            if self.at(TokenKind::Newline) {
                self.pos += 1;
            } else {
                break;
            }
        }
    }

    fn current(&mut self) -> Option<Token> {
        self.skip_comments();
        self.tokens.get(self.pos).copied()
    }

    fn peek_kind(&mut self) -> TokenKind {
        self.current().map_or(TokenKind::Eof, |t| t.kind)
    }

    fn peek_n(&mut self, n: usize) -> TokenKind {
        let mut index = self.pos;
        let mut seen = 0;
        while let Some(token) = self.tokens.get(index) {
            index += 1;
            if matches!(token.kind, TokenKind::Comment(_)) {
                continue;
            }
            if seen == n {
                return token.kind;
            }
            seen += 1;
        }
        TokenKind::Eof
    }

    fn at(&mut self, kind: TokenKind) -> bool {
        self.peek_kind() == kind
    }

    fn bump(&mut self) -> Option<Token> {
        self.skip_comments();
        let token = self.tokens.get(self.pos).copied();
        if token.is_some() && !matches!(token.map(|t| t.kind), Some(TokenKind::Eof)) {
            self.pos += 1;
        }
        token
    }

    fn expect(&mut self, kind: TokenKind, message: &str) -> bool {
        if self.at(kind) {
            self.bump();
            true
        } else {
            self.error(message);
            false
        }
    }

    fn expect_ident(&mut self, message: &str) -> Option<String> {
        let token = self.current()?;
        if token.kind == TokenKind::Ident {
            self.bump();
            Some(token.text(self.source).to_owned())
        } else {
            self.error_at(message, token.span);
            None
        }
    }

    fn current_span(&mut self) -> Span {
        self.current().map_or_else(
            || Span::empty(self.file, self.source.len() as u32),
            |t| t.span,
        )
    }

    fn last_end(&self) -> u32 {
        self.tokens
            .get(self.pos.saturating_sub(1))
            .map_or(0, |t| t.span.end)
    }

    fn span_from(&self, start: u32, end: u32) -> Span {
        Span::new(self.file, start.min(end), end)
    }

    fn error(&mut self, message: impl Into<String>) {
        let span = self.current_span();
        self.error_at(message, span);
    }

    fn error_at(&mut self, message: impl Into<String>, span: Span) {
        self.error_code_at("PGS-E1901", message, span);
    }

    fn error_code_at(&mut self, code: &'static str, message: impl Into<String>, span: Span) {
        if self.diagnostics.len() < 100 {
            self.diagnostics
                .push(Diagnostic::error(code, message, span));
        }
    }

    fn at_expr_end(&mut self) -> bool {
        matches!(
            self.peek_kind(),
            TokenKind::Newline
                | TokenKind::Dedent
                | TokenKind::Eof
                | TokenKind::RParen
                | TokenKind::RBracket
                | TokenKind::RBrace
                | TokenKind::Comma
                | TokenKind::Then
                | TokenKind::Else
                | TokenKind::Elseif
                | TokenKind::When
                | TokenKind::In
        )
    }

    // ---------------------------------------------------------------------
    // Pratt
    // ---------------------------------------------------------------------

    fn parse_bp(&mut self, min_bp: u8) -> Expr {
        let mut lhs = self.parse_prefix();
        loop {
            let kind = self.peek_kind();
            if is_comparison_kind(kind)
                && matches!(
                    lhs.kind,
                    ExprKind::Binary {
                        op: BinOp::Eq | BinOp::Ne | BinOp::Lt | BinOp::Le | BinOp::Gt | BinOp::Ge,
                        ..
                    }
                )
            {
                let span = self.current_span();
                self.error_code_at(
                    "PGS-E1408",
                    "las comparaciones no se pueden encadenar; usa `and`",
                    span,
                );
            }
            if kind == TokenKind::As {
                if 80 < min_bp {
                    break;
                }
                self.bump();
                let ty = self.parse_type();
                let span = self.span_from(lhs.span.start, ty.span.end);
                lhs = Expr::new(
                    ExprKind::Cast {
                        expr: Box::new(lhs),
                        ty,
                    },
                    span,
                );
                continue;
            }
            if matches!(kind, TokenKind::DotDot | TokenKind::DotDotEq) {
                let inclusive = kind == TokenKind::DotDotEq;
                if 50 < min_bp {
                    break;
                }
                self.bump();
                if self.at_expr_end() {
                    let span = self.span_from(lhs.span.start, self.last_end());
                    lhs = Expr::new(
                        ExprKind::Range {
                            start: Box::new(lhs),
                            end: None,
                            inclusive,
                        },
                        span,
                    );
                } else {
                    let rhs = self.parse_bp(51);
                    let span = self.span_from(lhs.span.start, rhs.span.end);
                    lhs = Expr::new(
                        ExprKind::Range {
                            start: Box::new(lhs),
                            end: Some(Box::new(rhs)),
                            inclusive,
                        },
                        span,
                    );
                }
                continue;
            }
            let Some((left_bp, right_bp, op)) = infix_binding(kind) else {
                break;
            };
            if left_bp < min_bp {
                break;
            }
            self.bump();
            let rhs = self.parse_bp(right_bp);
            let span = self.span_from(lhs.span.start, rhs.span.end);
            lhs = Expr::new(
                ExprKind::Binary {
                    op,
                    lhs: Box::new(lhs),
                    rhs: Box::new(rhs),
                },
                span,
            );
        }
        lhs
    }

    fn parse_prefix(&mut self) -> Expr {
        let start = self.current_span();
        match self.peek_kind() {
            TokenKind::Minus => {
                self.bump();
                let expr = self.parse_bp(90);
                let span = self.span_from(start.start, expr.span.end);
                Expr::new(
                    ExprKind::Unary {
                        op: UnOp::Neg,
                        expr: Box::new(expr),
                    },
                    span,
                )
            }
            TokenKind::Not => {
                self.bump();
                // `not` es unario y liga más fuerte que la comparación;
                // §14.1 lo sitúa en el nivel 2.
                let expr = self.parse_bp(90);
                let span = self.span_from(start.start, expr.span.end);
                Expr::new(
                    ExprKind::Unary {
                        op: UnOp::Not,
                        expr: Box::new(expr),
                    },
                    span,
                )
            }
            TokenKind::Amp => {
                self.bump();
                let mutable = self.at_ident("mut") || self.at(TokenKind::AtMut);
                if mutable {
                    self.bump();
                }
                let expr = self.parse_bp(90);
                let span = self.span_from(start.start, expr.span.end);
                Expr::new(
                    ExprKind::Ref {
                        mutable,
                        expr: Box::new(expr),
                    },
                    span,
                )
            }
            _ => self.parse_postfix(),
        }
    }

    fn parse_postfix(&mut self) -> Expr {
        let mut expr = self.parse_primary();
        loop {
            match self.peek_kind() {
                TokenKind::Dot => {
                    self.bump();
                    let name = if self.at(TokenKind::Int) {
                        let token = self.bump().unwrap();
                        token.text(self.source).to_owned()
                    } else if let Some(name) = self.expect_ident("se esperaba un nombre de campo") {
                        name
                    } else {
                        break;
                    };
                    if self.at(TokenKind::LParen) {
                        let args = self.parse_args();
                        let end = self.last_end();
                        let span = self.span_from(expr.span.start, end);
                        let callee = Expr::new(
                            ExprKind::Field {
                                base: Box::new(expr),
                                name,
                            },
                            span,
                        );
                        expr = Expr::new(
                            ExprKind::Call {
                                callee: Box::new(callee),
                                args,
                            },
                            span,
                        );
                    } else {
                        let span = self.span_from(expr.span.start, self.last_end());
                        expr = Expr::new(
                            ExprKind::Field {
                                base: Box::new(expr),
                                name,
                            },
                            span,
                        );
                    }
                }
                TokenKind::LParen => {
                    let named = (self.peek_n(1) == TokenKind::Ident
                        && self.peek_n(2) == TokenKind::Colon)
                        || self.peek_n(1) == TokenKind::DotDot;
                    if named {
                        let path = match &expr.kind {
                            ExprKind::Path(segments) => segments.clone(),
                            _ => {
                                self.error("un literal de record requiere un path de tipo");
                                Vec::new()
                            }
                        };
                        self.bump();
                        let mut fields = Vec::new();
                        let mut base = None;
                        while !self.at(TokenKind::RParen) && !self.at(TokenKind::Eof) {
                            if self.at(TokenKind::DotDot) {
                                self.bump();
                                base = Some(Box::new(self.parse_bp(0)));
                                if self.at(TokenKind::Comma) {
                                    self.bump();
                                }
                                break;
                            }
                            let field_name = self
                                .expect_ident("se esperaba el nombre del campo")
                                .unwrap_or_default();
                            self.expect(TokenKind::Colon, "se esperaba `:`");
                            let value = self.parse_bp(0);
                            fields.push((field_name, value));
                            if self.at(TokenKind::Comma) {
                                self.bump();
                                if self.at(TokenKind::RParen) {
                                    break;
                                }
                            } else {
                                break;
                            }
                        }
                        self.expect(TokenKind::RParen, "se esperaba `)`");
                        let span = self.span_from(expr.span.start, self.last_end());
                        expr = Expr::new(ExprKind::Record { path, fields, base }, span);
                    } else {
                        let args = self.parse_args();
                        let span = self.span_from(expr.span.start, self.last_end());
                        expr = Expr::new(
                            ExprKind::Call {
                                callee: Box::new(expr),
                                args,
                            },
                            span,
                        );
                    }
                }
                TokenKind::LBracket => {
                    self.bump();
                    let index = self.parse_bp(0);
                    self.expect(TokenKind::RBracket, "se esperaba `]`");
                    let span = self.span_from(expr.span.start, self.last_end());
                    expr = Expr::new(
                        ExprKind::Index {
                            base: Box::new(expr),
                            index: Box::new(index),
                        },
                        span,
                    );
                }
                TokenKind::Question => {
                    self.bump();
                    let span = self.span_from(expr.span.start, self.last_end());
                    expr = Expr::new(ExprKind::Try(Box::new(expr)), span);
                }
                _ => break,
            }
        }
        expr
    }

    fn parse_args(&mut self) -> Vec<Expr> {
        self.expect(TokenKind::LParen, "se esperaba `(`");
        let mut args = Vec::new();
        if self.at(TokenKind::RParen) {
            self.bump();
            return args;
        }
        loop {
            args.push(self.parse_bp(0));
            if self.at(TokenKind::Comma) {
                self.bump();
                if self.at(TokenKind::RParen) {
                    self.bump();
                    break;
                }
            } else {
                self.expect(TokenKind::RParen, "se esperaba `)`");
                break;
            }
        }
        args
    }

    fn parse_primary(&mut self) -> Expr {
        let start = self.current_span();
        let kind = self.peek_kind();
        match kind {
            TokenKind::True => {
                self.bump();
                Expr::new(ExprKind::Bool(true), start)
            }
            TokenKind::False => {
                self.bump();
                Expr::new(ExprKind::Bool(false), start)
            }
            TokenKind::None => {
                self.bump();
                Expr::new(ExprKind::None, start)
            }
            TokenKind::Int => {
                let token = self.bump().unwrap();
                Expr::new(
                    ExprKind::Int(token.text(self.source).to_owned()),
                    token.span,
                )
            }
            TokenKind::Float => {
                let token = self.bump().unwrap();
                Expr::new(
                    ExprKind::Float(token.text(self.source).to_owned()),
                    token.span,
                )
            }
            TokenKind::Char => {
                let token = self.bump().unwrap();
                Expr::new(
                    ExprKind::Char(token.text(self.source).to_owned()),
                    token.span,
                )
            }
            TokenKind::ByteChar => {
                let token = self.bump().unwrap();
                Expr::new(
                    ExprKind::ByteChar(token.text(self.source).to_owned()),
                    token.span,
                )
            }
            TokenKind::String(string_kind) => {
                let token = self.bump().unwrap();
                let parts = vec![StringPart::Text(token.text(self.source).to_owned())];
                Expr::new(
                    ExprKind::String(StringLit {
                        kind: string_kind,
                        parts,
                    }),
                    token.span,
                )
            }
            TokenKind::StringStart(string_kind) => {
                self.parse_interpolated_string(string_kind, start)
            }
            TokenKind::LParen => self.parse_paren_or_lambda(),
            TokenKind::LBracket => self.parse_array(),
            TokenKind::LBrace => self.parse_map(),
            TokenKind::If => self.parse_if(false),
            TokenKind::Unless => self.parse_if(true),
            TokenKind::Match => self.parse_match(),
            TokenKind::Do => {
                self.bump();
                let block = self.parse_block();
                let span = self.span_from(start.start, block.span.end);
                Expr::new(ExprKind::Do(block), span)
            }
            TokenKind::Loop => {
                self.bump();
                let block = self.parse_block();
                let span = self.span_from(start.start, block.span.end);
                Expr::new(ExprKind::Loop(block), span)
            }
            TokenKind::Curse => {
                self.bump();
                let block = self.parse_block();
                let span = self.span_from(start.start, block.span.end);
                Expr::new(ExprKind::Curse(block), span)
            }
            TokenKind::At => {
                self.bump();
                Expr::new(ExprKind::SelfValue, start)
            }
            TokenKind::AtMut | TokenKind::AtOwn => {
                self.bump();
                self.error_at("`@mut`/`@own` solo son válidos como receptores", start);
                Expr::new(ExprKind::SelfValue, start)
            }
            TokenKind::SelfType => {
                self.bump();
                Expr::new(ExprKind::SelfValue, start)
            }
            TokenKind::Some | TokenKind::Ok | TokenKind::Err => {
                let token = self.bump().unwrap();
                let name = token.text(self.source).to_owned();
                Expr::new(ExprKind::Path(vec![name]), token.span)
            }
            TokenKind::Ident => self.parse_path_or_literal(),
            _ => {
                self.error_at("se esperaba una expresión", start);
                self.bump();
                Expr::new(ExprKind::Unit, start)
            }
        }
    }

    fn parse_path_or_literal(&mut self) -> Expr {
        let start = self.current_span();
        let special = self.current().and_then(|token| {
            if token.kind != TokenKind::Ident {
                return None;
            }
            match token.text(self.source) {
                "Vec" if self.peek_n(1) == TokenKind::LBracket => Some("Vec"),
                "Map" if self.peek_n(1) == TokenKind::LBracket => Some("Map"),
                "Set" if self.peek_n(1) == TokenKind::LBracket => Some("Set"),
                _ => None,
            }
        });
        match special {
            Some("Vec") => return self.parse_vector(),
            Some("Map") => return self.parse_map_lit(),
            Some("Set") => return self.parse_set(),
            _ => {}
        }
        let Some(name) = self.expect_ident("se esperaba un identificador") else {
            return Expr::new(ExprKind::Unit, start);
        };
        let mut segments = vec![name];
        while self.at(TokenKind::ColonColon) {
            self.bump();
            let Some(segment) = self.expect_ident("se esperaba un segmento de path") else {
                break;
            };
            segments.push(segment);
        }
        let span = self.span_from(start.start, self.last_end());
        Expr::new(ExprKind::Path(segments), span)
    }

    fn parse_interpolated_string(&mut self, kind: StringKind, start: Span) -> Expr {
        self.bump();
        let mut parts = Vec::new();
        loop {
            match self.peek_kind() {
                TokenKind::StringText => {
                    let token = self.bump().unwrap();
                    parts.push(StringPart::Text(token.text(self.source).to_owned()));
                }
                TokenKind::InterpStart => {
                    self.bump();
                    let expr = self.parse_bp(0);
                    self.expect(TokenKind::InterpEnd, "se esperaba cerrar `#{...}`");
                    parts.push(StringPart::Expr(expr));
                }
                TokenKind::StringEnd => {
                    let token = self.bump().unwrap();
                    return Expr::new(
                        ExprKind::String(StringLit { kind, parts }),
                        self.span_from(start.start, token.span.end),
                    );
                }
                TokenKind::Eof => {
                    self.error_at("string interpolado sin cerrar", start);
                    return Expr::new(
                        ExprKind::String(StringLit { kind, parts }),
                        self.span_from(start.start, self.last_end()),
                    );
                }
                _ => {
                    self.error("segmento de string inesperado");
                    self.bump();
                }
            }
        }
    }

    fn parse_paren_or_lambda(&mut self) -> Expr {
        let start = self.current_span();
        if self.lambda_ahead() {
            self.bump(); // (
            let params = self.parse_params();
            self.expect(TokenKind::FatArrow, "se esperaba `=>`");
            let body = self.parse_lambda_body();
            let span = self.span_from(start.start, body.span.end);
            return Expr::new(ExprKind::Lambda { params, body }, span);
        }
        self.bump(); // (
        if self.at(TokenKind::RParen) {
            self.bump();
            return Expr::new(ExprKind::Unit, self.span_from(start.start, self.last_end()));
        }
        let first = self.parse_bp(0);
        if self.at(TokenKind::Comma) {
            let mut items = vec![first];
            while self.at(TokenKind::Comma) {
                self.bump();
                if self.at(TokenKind::RParen) {
                    break;
                }
                items.push(self.parse_bp(0));
            }
            self.expect(TokenKind::RParen, "se esperaba `)`");
            let span = self.span_from(start.start, self.last_end());
            Expr::new(ExprKind::Tuple(items), span)
        } else {
            self.expect(TokenKind::RParen, "se esperaba `)`");
            first
        }
    }

    fn lambda_ahead(&mut self) -> bool {
        let mut index = self.pos;
        let mut depth = 0usize;
        while let Some(token) = self.tokens.get(index) {
            match token.kind {
                TokenKind::Comment(_) => {}
                TokenKind::LParen => depth += 1,
                TokenKind::RParen => {
                    depth = depth.saturating_sub(1);
                    if depth == 0 {
                        index += 1;
                        break;
                    }
                }
                TokenKind::Eof => return false,
                _ => {}
            }
            index += 1;
        }
        while matches!(
            self.tokens.get(index).map(|t| t.kind),
            Some(TokenKind::Comment(_))
        ) {
            index += 1;
        }
        matches!(
            self.tokens.get(index).map(|t| t.kind),
            Some(TokenKind::FatArrow)
        )
    }

    fn parse_params(&mut self) -> Vec<Param> {
        let mut params = Vec::new();
        if self.at(TokenKind::RParen) {
            self.bump();
            return params;
        }
        loop {
            let start = self.current_span();
            let Some(name) = self.expect_ident("se esperaba un nombre de parámetro") else {
                break;
            };
            if !self.at(TokenKind::Colon) {
                let span = self.current_span();
                self.error_code_at("PGS-E7003", "el parámetro requiere un tipo explícito", span);
            } else {
                self.bump();
            }
            let ty = self.parse_type();
            params.push(Param {
                name,
                ty,
                span: self.span_from(start.start, self.last_end()),
            });
            if self.at(TokenKind::Comma) {
                self.bump();
                if self.at(TokenKind::RParen) {
                    self.bump();
                    break;
                }
            } else {
                self.expect(TokenKind::RParen, "se esperaba `)`");
                break;
            }
        }
        params
    }

    fn parse_array(&mut self) -> Expr {
        let start = self.current_span();
        self.bump(); // [
        if self.at(TokenKind::RBracket) {
            self.bump();
            return Expr::new(
                ExprKind::Array(Vec::new()),
                self.span_from(start.start, self.last_end()),
            );
        }
        let first = self.parse_bp(0);
        if self.at(TokenKind::Semicolon) {
            self.bump();
            let count = self.parse_bp(0);
            self.expect(TokenKind::RBracket, "se esperaba `]`");
            let span = self.span_from(start.start, self.last_end());
            return Expr::new(
                ExprKind::ArrayRepeat {
                    value: Box::new(first),
                    count: Box::new(count),
                },
                span,
            );
        }
        let mut items = vec![first];
        while self.at(TokenKind::Comma) {
            self.bump();
            if self.at(TokenKind::RBracket) {
                break;
            }
            items.push(self.parse_bp(0));
        }
        self.expect(TokenKind::RBracket, "se esperaba `]`");
        let span = self.span_from(start.start, self.last_end());
        Expr::new(ExprKind::Array(items), span)
    }

    fn parse_map(&mut self) -> Expr {
        let start = self.current_span();
        self.bump(); // {
        let entries = self.parse_map_entries(TokenKind::RBrace);
        let span = self.span_from(start.start, self.last_end());
        Expr::new(ExprKind::Map(entries), span)
    }

    fn parse_map_lit(&mut self) -> Expr {
        let start = self.current_span();
        self.bump(); // Map
        self.expect(TokenKind::LBracket, "se esperaba `[`");
        let entries = self.parse_map_entries(TokenKind::RBracket);
        let span = self.span_from(start.start, self.last_end());
        Expr::new(ExprKind::Map(entries), span)
    }

    fn parse_map_entries(&mut self, close: TokenKind) -> Vec<(Expr, Expr)> {
        let mut entries = Vec::new();
        self.skip_comments();
        if self.at(close) {
            self.bump();
            return entries;
        }
        loop {
            let key = self.parse_bp(0);
            if !self.at(TokenKind::Colon) {
                let span = self.current_span();
                self.error_code_at(
                    "PGS-E3105",
                    "entrada de mapa inválida: se esperaba `clave: valor`",
                    span,
                );
            } else {
                self.bump();
            }
            let value = self.parse_bp(0);
            entries.push((key, value));
            if self.at(TokenKind::Comma) {
                self.bump();
                if self.at(close) {
                    self.bump();
                    break;
                }
            } else {
                self.expect(close, "se esperaba cerrar el mapa");
                break;
            }
        }
        entries
    }

    fn parse_vector(&mut self) -> Expr {
        let start = self.current_span();
        self.bump(); // Vec
        self.expect(TokenKind::LBracket, "se esperaba `[`");
        let items = self.parse_expr_list(TokenKind::RBracket);
        let span = self.span_from(start.start, self.last_end());
        Expr::new(ExprKind::Vector(items), span)
    }

    fn parse_set(&mut self) -> Expr {
        let start = self.current_span();
        self.bump(); // Set
        self.expect(TokenKind::LBracket, "se esperaba `[`");
        let items = self.parse_expr_list(TokenKind::RBracket);
        let span = self.span_from(start.start, self.last_end());
        Expr::new(ExprKind::Set(items), span)
    }

    fn parse_expr_list(&mut self, close: TokenKind) -> Vec<Expr> {
        let mut items = Vec::new();
        if self.at(close) {
            self.bump();
            return items;
        }
        loop {
            items.push(self.parse_bp(0));
            if self.at(TokenKind::Comma) {
                self.bump();
                if self.at(close) {
                    self.bump();
                    break;
                }
            } else {
                self.expect(close, "se esperaba cerrar la colección");
                break;
            }
        }
        items
    }

    // ---------------------------------------------------------------------
    // Control
    // ---------------------------------------------------------------------

    fn parse_inline_branch(&mut self) -> Block {
        let expr = self.parse_bp(0);
        let span = expr.span;
        Block {
            stmts: vec![Stmt {
                kind: StmtKind::Expr(expr),
                span,
            }],
            span,
        }
    }

    fn parse_block_branch(&mut self) -> Block {
        self.skip_comments();
        if !self.at(TokenKind::Newline) {
            self.error("se esperaba un salto de línea antes del bloque");
        }
        self.parse_block()
    }

    fn parse_lambda_body(&mut self) -> Block {
        self.skip_comments();
        if self.at(TokenKind::Newline) {
            self.parse_block()
        } else {
            self.parse_inline_branch()
        }
    }

    fn parse_if(&mut self, unless: bool) -> Expr {
        let start = self.current_span();
        self.bump(); // if/unless
        let cond = self.parse_bp(0);
        self.expect(TokenKind::Then, "se esperaba `then`");
        self.skip_comments();
        let block_form = self.at(TokenKind::Newline);
        let then_branch = if block_form {
            self.parse_block_branch()
        } else {
            self.parse_inline_branch()
        };
        let else_branch = if !unless && self.at(TokenKind::Elseif) {
            // `elseif` funciona en ambas formas: la de bloque usa la cadena
            // indentada y la inline continúa la expresión en la misma línea.
            let nested = if block_form {
                self.parse_elseif()
            } else {
                self.parse_elseif_inline()
            };
            let span = nested.span;
            Some(Block {
                stmts: vec![Stmt {
                    kind: StmtKind::Expr(nested),
                    span,
                }],
                span,
            })
        } else if self.at(TokenKind::Else) {
            self.bump();
            self.skip_comments();
            if block_form {
                Some(self.parse_block_branch())
            } else {
                if self.at(TokenKind::Newline) {
                    self.error("la forma inline de `if` no admite un `else` en bloque");
                }
                Some(self.parse_inline_branch())
            }
        } else {
            None
        };
        let end = else_branch
            .as_ref()
            .map_or(then_branch.span.end, |b| b.span.end);
        Expr::new(
            ExprKind::If {
                cond: Box::new(cond),
                then_branch,
                else_branch,
                unless,
            },
            self.span_from(start.start, end),
        )
    }

    fn parse_elseif(&mut self) -> Expr {
        let start = self.current_span();
        self.bump(); // elseif
        let cond = self.parse_bp(0);
        self.expect(TokenKind::Then, "se esperaba `then`");
        self.skip_comments();
        if !self.at(TokenKind::Newline) {
            self.error("`elseif` solo se permite en la forma con bloque");
        }
        let then_branch = self.parse_block_branch();
        let else_branch = if self.at(TokenKind::Elseif) {
            let nested = self.parse_elseif();
            let span = nested.span;
            Some(Block {
                stmts: vec![Stmt {
                    kind: StmtKind::Expr(nested),
                    span,
                }],
                span,
            })
        } else if self.at(TokenKind::Else) {
            self.bump();
            self.skip_comments();
            Some(self.parse_block_branch())
        } else {
            None
        };
        let end = else_branch
            .as_ref()
            .map_or(then_branch.span.end, |b| b.span.end);
        Expr::new(
            ExprKind::If {
                cond: Box::new(cond),
                then_branch,
                else_branch,
                unless: false,
            },
            self.span_from(start.start, end),
        )
    }

    /// `elseif` en la forma inline: `if c then a elseif c2 then b else c`.
    fn parse_elseif_inline(&mut self) -> Expr {
        let start = self.current_span();
        self.bump(); // elseif
        let cond = self.parse_bp(0);
        self.expect(TokenKind::Then, "se esperaba `then`");
        self.skip_comments();
        let then_branch = self.parse_inline_branch();
        let else_branch = if self.at(TokenKind::Elseif) {
            let nested = self.parse_elseif_inline();
            let span = nested.span;
            Some(Block {
                stmts: vec![Stmt {
                    kind: StmtKind::Expr(nested),
                    span,
                }],
                span,
            })
        } else if self.at(TokenKind::Else) {
            self.bump();
            self.skip_comments();
            Some(self.parse_inline_branch())
        } else {
            None
        };
        let end = else_branch
            .as_ref()
            .map_or(then_branch.span.end, |b| b.span.end);
        Expr::new(
            ExprKind::If {
                cond: Box::new(cond),
                then_branch,
                else_branch,
                unless: false,
            },
            self.span_from(start.start, end),
        )
    }

    fn parse_match(&mut self) -> Expr {
        let start = self.current_span();
        self.bump(); // match
        let scrutinee = self.parse_bp(0);
        self.expect(
            TokenKind::Newline,
            "se esperaba un salto de línea tras `match`",
        );
        self.expect(TokenKind::Indent, "se esperaba indentación en `match`");
        let mut arms = Vec::new();
        loop {
            self.skip_newlines();
            if self.at(TokenKind::Dedent) {
                self.bump();
                break;
            }
            if self.at(TokenKind::Eof) {
                self.error("`match` sin `DEDENT`");
                break;
            }
            if self.at(TokenKind::When) {
                self.bump();
                let pattern = self.parse_pattern();
                let guard = if self.at(TokenKind::If) {
                    self.bump();
                    Some(self.parse_bp(0))
                } else {
                    None
                };
                self.skip_comments();
                let has_then = self.at(TokenKind::Then);
                let body = if has_then {
                    self.bump();
                    self.skip_comments();
                    if self.at(TokenKind::Newline) {
                        self.parse_block_branch()
                    } else {
                        self.parse_inline_branch()
                    }
                } else {
                    self.parse_block_branch()
                };
                arms.push(MatchArm {
                    pattern: Some(pattern),
                    guard,
                    body,
                });
            } else if self.at(TokenKind::Else) {
                self.bump();
                self.skip_comments();
                if self.at(TokenKind::Then) {
                    self.error("`else` en `match` no lleva `then`");
                    self.bump();
                    self.skip_comments();
                }
                let body = if self.at(TokenKind::Newline) {
                    self.parse_block_branch()
                } else {
                    self.parse_inline_branch()
                };
                arms.push(MatchArm {
                    pattern: None,
                    guard: None,
                    body,
                });
                self.skip_newlines();
                if self.at(TokenKind::Dedent) {
                    self.bump();
                    break;
                }
                self.error("`else` debe ser el último brazo");
                break;
            } else {
                self.error("se esperaba `when` o `else` en `match`");
                self.bump();
            }
        }
        if arms.is_empty() {
            self.error_at(
                "`match` necesita al menos un brazo",
                self.span_from(start.start, self.last_end()),
            );
        }
        let span = self.span_from(start.start, self.last_end());
        Expr::new(
            ExprKind::Match {
                scrutinee: Box::new(scrutinee),
                arms,
            },
            span,
        )
    }

    // ---------------------------------------------------------------------
    // Statements and blocks
    // ---------------------------------------------------------------------

    fn parse_block(&mut self) -> Block {
        let start = self.current_span();
        self.skip_comments();
        self.expect(TokenKind::Newline, "se esperaba un salto de línea");
        self.skip_comments();
        self.expect(TokenKind::Indent, "se esperaba un bloque indentado");
        let mut stmts = Vec::new();
        loop {
            self.skip_newlines();
            if self.at(TokenKind::Dedent) {
                let end = self.current_span().end;
                self.bump();
                if stmts.is_empty() {
                    self.error_at(
                        "un bloque no puede estar vacío",
                        self.span_from(start.start, end),
                    );
                }
                return Block {
                    stmts,
                    span: self.span_from(start.start, end),
                };
            }
            if self.at(TokenKind::Eof) {
                self.error("bloque sin `DEDENT`");
                return Block {
                    stmts,
                    span: self.span_from(start.start, self.last_end()),
                };
            }
            let stmt = self.parse_statement();
            stmts.push(stmt);
            self.skip_comments();
            if self.at(TokenKind::Newline) {
                self.bump();
            } else if !matches!(self.peek_kind(), TokenKind::Dedent | TokenKind::Eof)
                && !self.previous_is_dedent()
            {
                self.error("se esperaba un salto de línea");
                self.recover_to_line_end();
            }
        }
    }

    fn previous_is_dedent(&self) -> bool {
        self.tokens
            .get(self.pos.saturating_sub(1))
            .is_some_and(|token| token.kind == TokenKind::Dedent)
    }

    fn previous_is_newline(&self) -> bool {
        self.tokens
            .get(self.pos.saturating_sub(1))
            .is_some_and(|token| token.kind == TokenKind::Newline)
    }

    fn recover_to_line_end(&mut self) {
        while !matches!(
            self.peek_kind(),
            TokenKind::Newline | TokenKind::Dedent | TokenKind::Eof
        ) {
            self.bump();
        }
        if self.at(TokenKind::Newline) {
            self.bump();
        }
    }

    fn parse_statement(&mut self) -> Stmt {
        let start = self.current_span();
        if matches!(
            self.peek_kind(),
            TokenKind::Rune
                | TokenKind::Enchanting
                | TokenKind::Pact
                | TokenKind::Ritual
                | TokenKind::Essence
                | TokenKind::Scroll
                | TokenKind::Summon
                | TokenKind::Foreign
                | TokenKind::Grimoire
        ) {
            let span = self.current_span();
            self.error_code_at(
                "PGS-E6003",
                "un item no puede declararse dentro de un bloque",
                span,
            );
        }
        match self.peek_kind() {
            TokenKind::Bind | TokenKind::Morph => {
                let mutable = self.peek_kind() == TokenKind::Morph;
                self.bump();
                let pattern = self.parse_pattern();
                let ty = if self.at(TokenKind::Colon) {
                    self.bump();
                    Some(self.parse_type())
                } else {
                    None
                };
                self.expect(TokenKind::Eq, "se esperaba `=`");
                self.skip_comments();
                let value = if self.at(TokenKind::Newline) {
                    let block = self.parse_block();
                    let span = block.span;
                    Expr::new(ExprKind::Do(block), span)
                } else {
                    self.parse_bp(0)
                };
                let else_block = if self.at(TokenKind::Else) {
                    self.bump();
                    Some(self.parse_block())
                } else {
                    None
                };
                let end = else_block.as_ref().map_or(value.span.end, |b| b.span.end);
                Stmt {
                    kind: StmtKind::Bind {
                        mutable,
                        pattern,
                        ty,
                        value,
                        else_block,
                    },
                    span: self.span_from(start.start, end),
                }
            }
            TokenKind::While => {
                self.bump();
                let cond = self.parse_bp(0);
                if self.at(TokenKind::Do) {
                    self.bump();
                }
                let body = self.parse_block();
                let span = self.span_from(start.start, body.span.end);
                Stmt {
                    kind: StmtKind::While { cond, body },
                    span,
                }
            }
            TokenKind::For => {
                self.bump();
                let pattern = self.parse_pattern();
                self.expect(TokenKind::In, "se esperaba `in`");
                let iter = self.parse_bp(0);
                if self.at(TokenKind::Do) {
                    self.bump();
                }
                let body = self.parse_block();
                let span = self.span_from(start.start, body.span.end);
                Stmt {
                    kind: StmtKind::For {
                        pattern,
                        iter,
                        body,
                    },
                    span,
                }
            }
            TokenKind::Return => {
                self.bump();
                let value = if self.at_expr_end() {
                    None
                } else {
                    Some(self.parse_bp(0))
                };
                let span = self.span_from(start.start, self.last_end());
                Stmt {
                    kind: StmtKind::Return(value),
                    span,
                }
            }
            TokenKind::Break => {
                self.bump();
                let value = if self.at_expr_end() {
                    None
                } else {
                    Some(self.parse_bp(0))
                };
                let span = self.span_from(start.start, self.last_end());
                Stmt {
                    kind: StmtKind::Break(value),
                    span,
                }
            }
            TokenKind::Continue => {
                self.bump();
                let span = self.span_from(start.start, self.last_end());
                Stmt {
                    kind: StmtKind::Continue,
                    span,
                }
            }
            _ => {
                let target = self.parse_bp(0);
                if self.at(TokenKind::Eq) {
                    self.bump();
                    let value = self.parse_bp(0);
                    let span = self.span_from(target.span.start, value.span.end);
                    Stmt {
                        kind: StmtKind::Assign { target, value },
                        span,
                    }
                } else {
                    let span = target.span;
                    Stmt {
                        kind: StmtKind::Expr(target),
                        span,
                    }
                }
            }
        }
    }

    // ---------------------------------------------------------------------
    // Types and patterns
    // ---------------------------------------------------------------------

    fn parse_type(&mut self) -> Type {
        let start = self.current_span();
        if self.at_ident("dyn") {
            let span = self.current_span();
            self.error_code_at(
                "PGS-E1208",
                "`dyn` no existe en PenguScript; usa un pact o un tipo concreto",
                span,
            );
            self.bump();
        }
        match self.peek_kind() {
            TokenKind::Question => {
                self.bump();
                let inner = self.parse_type();
                Type {
                    span: self.span_from(start.start, inner.span.end),
                    kind: TypeKind::Option(Box::new(inner)),
                }
            }
            TokenKind::Amp => {
                self.bump();
                let mutable = self.at_ident("mut") || self.at(TokenKind::AtMut);
                if mutable {
                    self.bump();
                }
                let inner = self.parse_type();
                Type {
                    span: self.span_from(start.start, inner.span.end),
                    kind: TypeKind::Ref {
                        mutable,
                        inner: Box::new(inner),
                    },
                }
            }
            TokenKind::LBracket => {
                self.bump();
                let elem = self.parse_type();
                if self.at(TokenKind::Semicolon) {
                    self.bump();
                    let len = self.parse_bp(0);
                    self.expect(TokenKind::RBracket, "se esperaba `]`");
                    Type {
                        span: self.span_from(start.start, self.last_end()),
                        kind: TypeKind::Array {
                            elem: Box::new(elem),
                            len: Box::new(len),
                        },
                    }
                } else {
                    self.expect(TokenKind::RBracket, "se esperaba `]`");
                    Type {
                        span: self.span_from(start.start, self.last_end()),
                        kind: TypeKind::Slice(Box::new(elem)),
                    }
                }
            }
            TokenKind::LParen => {
                self.bump();
                let mut items = Vec::new();
                let mut had_comma = false;
                if !self.at(TokenKind::RParen) {
                    loop {
                        items.push(self.parse_type());
                        if self.at(TokenKind::Comma) {
                            had_comma = true;
                            self.bump();
                            if self.at(TokenKind::RParen) {
                                break;
                            }
                        } else {
                            break;
                        }
                    }
                }
                self.expect(TokenKind::RParen, "se esperaba `)`");
                if self.at(TokenKind::Arrow) {
                    self.bump();
                    let ret = self.parse_type();
                    Type {
                        span: self.span_from(start.start, ret.span.end),
                        kind: TypeKind::Fn {
                            params: items,
                            ret: Box::new(ret),
                        },
                    }
                } else if items.is_empty() {
                    Type {
                        span: self.span_from(start.start, self.last_end()),
                        kind: TypeKind::Unit,
                    }
                } else if items.len() == 1 && !had_comma {
                    self.error_at("un tipo entre paréntesis requiere una coma o `->`", start);
                    items.pop().unwrap()
                } else {
                    Type {
                        span: self.span_from(start.start, self.last_end()),
                        kind: TypeKind::Tuple(items),
                    }
                }
            }
            TokenKind::Ptr => {
                self.bump();
                self.expect(TokenKind::LBracket, "se esperaba `[` tras `Ptr`");
                let inner = self.parse_type();
                self.expect(TokenKind::RBracket, "se esperaba `]`");
                Type {
                    span: self.span_from(start.start, self.last_end()),
                    kind: TypeKind::Ptr(Box::new(inner)),
                }
            }
            TokenKind::SelfType => {
                self.bump();
                Type {
                    span: start,
                    kind: TypeKind::SelfType,
                }
            }
            TokenKind::Ident => {
                let mut segments = Vec::new();
                if let Some(name) = self.expect_ident("se esperaba un tipo") {
                    segments.push(name);
                }
                while self.at(TokenKind::ColonColon) {
                    self.bump();
                    if let Some(segment) = self.expect_ident("se esperaba un segmento de tipo") {
                        segments.push(segment);
                    }
                }
                let mut args = Vec::new();
                if self.at(TokenKind::LBracket) {
                    self.bump();
                    if !self.at(TokenKind::RBracket) {
                        loop {
                            args.push(self.parse_type());
                            if self.at(TokenKind::Comma) {
                                self.bump();
                                if self.at(TokenKind::RBracket) {
                                    break;
                                }
                            } else {
                                break;
                            }
                        }
                    }
                    self.expect(TokenKind::RBracket, "se esperaba `]`");
                }
                Type {
                    span: self.span_from(start.start, self.last_end()),
                    kind: TypeKind::Path { segments, args },
                }
            }
            _ => {
                self.error_at("se esperaba un tipo", start);
                Type {
                    span: start,
                    kind: TypeKind::Unit,
                }
            }
        }
    }

    fn at_ident(&mut self, text: &str) -> bool {
        self.current()
            .is_some_and(|t| t.kind == TokenKind::Ident && t.text(self.source) == text)
    }

    fn parse_pattern(&mut self) -> Pattern {
        let start = self.current_span();
        let first = self.parse_pattern_range();
        let mut alternatives = vec![first];
        while self.at(TokenKind::Pipe) {
            self.bump();
            alternatives.push(self.parse_pattern_range());
        }
        if alternatives.len() == 1 {
            alternatives.pop().unwrap()
        } else {
            Pattern {
                span: self.span_from(start.start, self.last_end()),
                kind: PatternKind::Or(alternatives),
            }
        }
    }

    fn parse_pattern_range(&mut self) -> Pattern {
        let start = self.current_span();
        let mut pattern = self.parse_pattern_atom();
        let range_kind = self.peek_kind();
        if matches!(range_kind, TokenKind::DotDot | TokenKind::DotDotEq) {
            let inclusive = range_kind == TokenKind::DotDotEq;
            self.bump();
            let end = if matches!(
                self.peek_kind(),
                TokenKind::Then
                    | TokenKind::If
                    | TokenKind::Comma
                    | TokenKind::RParen
                    | TokenKind::RBracket
                    | TokenKind::Pipe
                    | TokenKind::Newline
                    | TokenKind::Dedent
                    | TokenKind::Eof
            ) {
                None
            } else {
                Some(Box::new(self.parse_pattern_atom()))
            };
            pattern = Pattern {
                span: self.span_from(start.start, self.last_end()),
                kind: PatternKind::Range {
                    start: Box::new(pattern),
                    end,
                    inclusive,
                },
            };
        }
        pattern
    }

    fn parse_pattern_atom(&mut self) -> Pattern {
        let start = self.current_span();
        match self.peek_kind() {
            TokenKind::Ident | TokenKind::Some | TokenKind::Ok | TokenKind::Err => {
                let token = self.current().unwrap();
                if token.kind == TokenKind::Ident && token.text(self.source) == "_" {
                    self.bump();
                    return Pattern {
                        span: start,
                        kind: PatternKind::Wildcard,
                    };
                }
                let name = token.text(self.source).to_owned();
                self.bump();
                if self.at(TokenKind::At) {
                    self.bump();
                    let sub = self.parse_pattern_atom();
                    let span = self.span_from(start.start, sub.span.end);
                    return Pattern {
                        kind: PatternKind::Bind {
                            name,
                            pattern: Box::new(sub),
                        },
                        span,
                    };
                }
                let mut path = vec![name];
                while self.at(TokenKind::ColonColon) || self.at(TokenKind::Dot) {
                    self.bump();
                    if let Some(segment) = self.expect_ident("se esperaba un segmento de patrón") {
                        path.push(segment);
                    }
                }
                if self.at(TokenKind::LParen) {
                    self.bump();
                    let mut args = Vec::new();
                    let mut named = Vec::new();
                    if !self.at(TokenKind::RParen) {
                        loop {
                            if self.peek_is_named_field() {
                                let name = self
                                    .expect_ident("se esperaba un campo")
                                    .unwrap_or_default();
                                self.expect(TokenKind::Colon, "se esperaba `:`");
                                named.push((name, self.parse_pattern()));
                            } else {
                                args.push(self.parse_pattern());
                            }
                            if self.at(TokenKind::Comma) {
                                self.bump();
                                if self.at(TokenKind::RParen) {
                                    break;
                                }
                            } else {
                                break;
                            }
                        }
                    }
                    self.expect(TokenKind::RParen, "se esperaba `)`");
                    return Pattern {
                        span: self.span_from(start.start, self.last_end()),
                        kind: PatternKind::Variant { path, args, named },
                    };
                }
                Pattern {
                    span: self.span_from(start.start, self.last_end()),
                    kind: PatternKind::Path(path),
                }
            }
            TokenKind::LParen => {
                self.bump();
                if self.at(TokenKind::RParen) {
                    self.bump();
                    return Pattern {
                        span: self.span_from(start.start, self.last_end()),
                        kind: PatternKind::Tuple(Vec::new()),
                    };
                }
                let mut items = Vec::new();
                loop {
                    items.push(self.parse_pattern());
                    if self.at(TokenKind::Comma) {
                        self.bump();
                        if self.at(TokenKind::RParen) {
                            break;
                        }
                    } else {
                        break;
                    }
                }
                self.expect(TokenKind::RParen, "se esperaba `)`");
                Pattern {
                    span: self.span_from(start.start, self.last_end()),
                    kind: PatternKind::Tuple(items),
                }
            }
            TokenKind::LBracket => {
                self.bump();
                let mut items = Vec::new();
                if !self.at(TokenKind::RBracket) {
                    loop {
                        items.push(self.parse_pattern());
                        if self.at(TokenKind::Comma) {
                            self.bump();
                            if self.at(TokenKind::RBracket) {
                                break;
                            }
                        } else {
                            break;
                        }
                    }
                }
                self.expect(TokenKind::RBracket, "se esperaba `]`");
                Pattern {
                    span: self.span_from(start.start, self.last_end()),
                    kind: PatternKind::Slice(items),
                }
            }
            TokenKind::DotDot => {
                self.bump();
                Pattern {
                    span: self.span_from(start.start, self.last_end()),
                    kind: PatternKind::Rest,
                }
            }
            TokenKind::Minus if matches!(self.peek_n(1), TokenKind::Int | TokenKind::Float) => {
                self.bump();
                let literal = self.parse_primary();
                let span = self.span_from(start.start, literal.span.end);
                Pattern {
                    kind: PatternKind::Literal(Expr::new(
                        ExprKind::Unary {
                            op: UnOp::Neg,
                            expr: Box::new(literal),
                        },
                        span,
                    )),
                    span,
                }
            }
            _ => {
                let expr = self.parse_primary();
                Pattern {
                    span: expr.span,
                    kind: PatternKind::Literal(expr),
                }
            }
        }
    }

    // ---------------------------------------------------------------------
    // Items y programas (F3)
    // ---------------------------------------------------------------------

    fn parse_program_root(&mut self) -> Option<Program> {
        let start = self.current_span().start;
        let mut items = Vec::new();
        self.skip_comments();
        self.skip_newlines();
        while !self.at(TokenKind::Eof) {
            let before = self.pos;
            if let Some(item) = self.parse_item() {
                items.push(item);
            }
            self.skip_comments();
            if self.at(TokenKind::Newline) {
                self.bump();
            } else if !matches!(self.peek_kind(), TokenKind::Eof | TokenKind::Dedent)
                && !self.previous_is_dedent()
            {
                self.error("se esperaba un salto de línea entre items");
                self.recover_to_line_end();
            }
            if self.pos == before {
                self.bump();
            }
            self.skip_newlines();
        }
        let end = self.last_end().max(start);
        Some(Program {
            items,
            span: self.span_from(start, end),
        })
    }

    fn parse_item(&mut self) -> Option<Item> {
        let start = self.current_span();
        if matches!(self.peek_kind(), TokenKind::Bind | TokenKind::Morph) {
            self.error_code_at(
                "PGS-E1101",
                "no se permiten bindings globales; declara dentro de una función",
                start,
            );
            self.recover_to_line_end();
            return None;
        }
        if self.at(TokenKind::AtAt) {
            return self.parse_attribute_item(start);
        }
        let visibility = self.parse_visibility();
        self.parse_item_after(start, visibility, Vec::new())
    }

    fn parse_visibility(&mut self) -> Visibility {
        if !self.at(TokenKind::Unveil) {
            return Visibility::Private;
        }
        self.bump();
        if !self.at(TokenKind::LParen) {
            return Visibility::Public;
        }
        self.bump();
        let visibility = if self.at_ident("tome") {
            self.bump();
            Visibility::Tome
        } else if self.at(TokenKind::Scroll) {
            self.bump();
            Visibility::Scroll
        } else {
            self.error("se esperaba `tome` o `scroll` en la visibilidad");
            Visibility::Public
        };
        self.expect(TokenKind::RParen, "se esperaba `)` tras la visibilidad");
        visibility
    }

    fn parse_attribute_item(&mut self, start: Span) -> Option<Item> {
        self.bump(); // @@
        let name = self.expect_ident("se esperaba `derive` o `test` tras `@@`")?;
        if name == "test" {
            return self.parse_test(start, Vec::new());
        }
        if name != "derive" {
            self.error("solo existen `@@derive` y `@@test`");
            self.recover_to_line_end();
            return None;
        }
        self.expect(TokenKind::LParen, "se esperaba `(` tras `@@derive`");
        let mut derives = Vec::new();
        if !self.at(TokenKind::RParen) {
            while let Some(derive) = self.expect_ident("se esperaba el nombre de un derive") {
                derives.push(derive);
                if self.at(TokenKind::Comma) {
                    self.bump();
                    if self.at(TokenKind::RParen) {
                        break;
                    }
                } else {
                    break;
                }
            }
        }
        self.expect(TokenKind::RParen, "se esperaba `)`");
        self.skip_comments();
        self.expect(
            TokenKind::Newline,
            "se esperaba un salto de línea tras `@@derive`",
        );
        self.skip_comments();
        let mut item = self.parse_item()?;
        if !matches!(item.kind, ItemKind::Rune(_) | ItemKind::Enchanting(_)) {
            self.error_code_at(
                "PGS-E8008",
                "`@@derive` solo se aplica a `rune` o `enchanting`",
                start,
            );
        }
        item.derives = derives;
        item.span = self.span_from(start.start, item.span.end);
        Some(item)
    }

    fn parse_item_after(
        &mut self,
        start: Span,
        visibility: Visibility,
        derives: Vec<String>,
    ) -> Option<Item> {
        let unveil = visibility.is_unveiled();
        if self.at(TokenKind::Foreign) && visibility != Visibility::Private {
            let span = self.current_span();
            self.error_code_at(
                "PGS-E1606",
                "no se puede exportar una función PenguScript a C",
                span,
            );
        }
        let kind = match self.peek_kind() {
            TokenKind::Scroll => {
                if unveil {
                    self.error_code_at("PGS-E2007", "`unveil` no se aplica a `scroll`", start);
                }
                ItemKind::Scroll(self.parse_scroll(start)?)
            }
            TokenKind::Summon => {
                if unveil {
                    self.error_code_at("PGS-E2007", "`unveil` no se aplica a `summon`", start);
                }
                ItemKind::Summon(self.parse_summon(start)?)
            }
            TokenKind::Rune => ItemKind::Rune(self.parse_rune(start, unveil)?),
            TokenKind::Enchanting => ItemKind::Enchanting(self.parse_enchanting(start, unveil)?),
            TokenKind::Pact => ItemKind::Pact(self.parse_pact(start, unveil)?),
            TokenKind::Ritual => ItemKind::Ritual(self.parse_ritual(start, unveil)?),
            TokenKind::Essence => ItemKind::Essence(self.parse_essence(start, unveil)?),
            TokenKind::Foreign => {
                if unveil {
                    self.error_code_at("PGS-E2007", "`unveil` no se aplica a `foreign`", start);
                }
                ItemKind::Foreign(self.parse_foreign(start)?)
            }
            TokenKind::Sigil | TokenKind::Relic => {
                ItemKind::Const(self.parse_const(start, unveil)?)
            }
            TokenKind::Grimoire => {
                if unveil {
                    self.error_code_at("PGS-E2007", "`unveil` no se aplica a `grimoire`", start);
                }
                ItemKind::Grimoire(self.parse_grimoire(start)?)
            }
            TokenKind::Curse => ItemKind::Function(self.parse_function(start, unveil, true)?),
            TokenKind::Ident => ItemKind::Function(self.parse_function(start, unveil, false)?),
            _ => {
                self.error("se esperaba un item");
                self.recover_to_line_end();
                return None;
            }
        };
        Some(Item {
            span: self.span_from(start.start, self.last_end()),
            kind,
            derives,
            visibility,
        })
    }

    fn parse_scroll(&mut self, start: Span) -> Option<Scroll> {
        self.bump();
        let name = self.expect_ident("se esperaba el nombre del módulo")?;
        let mut items = Vec::new();
        self.skip_comments();
        if self.at(TokenKind::Newline) && self.peek_n(1) == TokenKind::Indent {
            self.bump();
            self.skip_comments();
            self.expect(TokenKind::Indent, "se esperaba un bloque de módulo");
            loop {
                self.skip_newlines();
                if self.at(TokenKind::Dedent) {
                    self.bump();
                    break;
                }
                if self.at(TokenKind::Eof) {
                    self.error("módulo sin `DEDENT`");
                    break;
                }
                let before = self.pos;
                if let Some(item) = self.parse_item() {
                    items.push(item);
                }
                self.skip_comments();
                if self.at(TokenKind::Newline) {
                    self.bump();
                } else if !matches!(self.peek_kind(), TokenKind::Dedent | TokenKind::Eof)
                    && !self.previous_is_dedent()
                {
                    self.error("se esperaba un salto de línea en el módulo");
                    self.recover_to_line_end();
                }
                if self.pos == before {
                    self.bump();
                }
            }
        }
        Some(Scroll {
            name,
            span: self.span_from(start.start, self.last_end()),
            items,
        })
    }

    fn parse_summon(&mut self, start: Span) -> Option<Summon> {
        self.bump();
        let path = self.parse_path();
        let alias = if self.at(TokenKind::As) {
            self.bump();
            self.expect_ident("se esperaba un alias")
        } else {
            None
        };
        Some(Summon {
            path,
            alias,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_rune(&mut self, start: Span, unveil: bool) -> Option<Rune> {
        self.bump();
        let name = self.expect_ident("se esperaba el nombre del `rune`")?;
        let params = self.parse_type_params();
        self.skip_comments();
        self.expect(
            TokenKind::Newline,
            "se esperaba un salto de línea tras `rune`",
        );
        self.skip_comments();
        if !self.at(TokenKind::Indent) {
            let span = self.current_span();
            self.error_code_at("PGS-E3010", "un `rune` necesita al menos un campo", span);
            return Some(Rune {
                unveil,
                name,
                params,
                methods: Vec::new(),
                span: self.span_from(start.start, self.last_end()),
                fields: Vec::new(),
            });
        }
        self.bump();
        let mut fields = Vec::new();
        loop {
            self.skip_newlines();
            if self.at(TokenKind::Dedent) {
                self.bump();
                break;
            }
            if self.at(TokenKind::Eof) {
                self.error("`rune` sin `DEDENT`");
                break;
            }
            fields.push(self.parse_field()?);
            self.skip_comments();
            if self.at(TokenKind::Newline) {
                self.bump();
            }
        }
        if fields.is_empty() {
            self.error("`rune` requiere al menos un campo");
        }
        Some(Rune {
            unveil,
            name,
            params,
            methods: Vec::new(),
            span: self.span_from(start.start, self.last_end()),
            fields,
        })
    }

    fn parse_field(&mut self) -> Option<Field> {
        let start = self.current_span();
        let unveil = if self.at(TokenKind::Unveil) {
            self.bump();
            true
        } else {
            false
        };
        let name = self.expect_ident("se esperaba el nombre del campo")?;
        self.expect(TokenKind::Colon, "se esperaba `:`");
        let ty = self.parse_type();
        Some(Field {
            unveil,
            name,
            ty,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_enchanting(&mut self, start: Span, unveil: bool) -> Option<Enchanting> {
        self.bump();
        let name = self.expect_ident("se esperaba el nombre del `enchanting`")?;
        let params = self.parse_type_params();
        self.skip_comments();
        self.expect(
            TokenKind::Newline,
            "se esperaba un salto de línea tras `enchanting`",
        );
        self.skip_comments();
        self.expect(TokenKind::Indent, "se esperaba un bloque de variantes");
        let mut variants = Vec::new();
        loop {
            self.skip_newlines();
            if self.at(TokenKind::Dedent) {
                self.bump();
                break;
            }
            if self.at(TokenKind::Eof) {
                self.error("`enchanting` sin `DEDENT`");
                break;
            }
            variants.push(self.parse_variant()?);
            self.skip_comments();
            if self.at(TokenKind::Newline) {
                self.bump();
            }
        }
        if variants.is_empty() {
            self.error("`enchanting` requiere al menos una variante");
        }
        Some(Enchanting {
            unveil,
            name,
            params,
            variants,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn expect_variant_name(&mut self, message: &str) -> Option<String> {
        let token = self.current()?;
        let text = match token.kind {
            TokenKind::Ident => token.text(self.source).to_owned(),
            TokenKind::Some => "some".to_owned(),
            TokenKind::None => "none".to_owned(),
            TokenKind::Ok => "ok".to_owned(),
            TokenKind::Err => "err".to_owned(),
            _ => {
                self.error_at(message, token.span);
                return None;
            }
        };
        self.bump();
        Some(text)
    }

    fn parse_variant(&mut self) -> Option<Variant> {
        let start = self.current_span();
        let name = self.expect_variant_name("se esperaba el nombre de la variante")?;
        let fields = if self.at(TokenKind::LParen) {
            self.bump();
            if self.at(TokenKind::RParen) {
                self.bump();
                VariantFields::Tuple(Vec::new())
            } else if self.peek_is_named_field() {
                let mut named = Vec::new();
                loop {
                    let field_start = self.current_span();
                    let field_name = self.expect_ident("se esperaba el nombre del campo")?;
                    self.expect(TokenKind::Colon, "se esperaba `:`");
                    let ty = self.parse_type();
                    named.push(Field {
                        unveil: false,
                        name: field_name,
                        ty,
                        span: self.span_from(field_start.start, self.last_end()),
                    });
                    if self.at(TokenKind::Comma) {
                        self.bump();
                        if self.at(TokenKind::RParen) {
                            break;
                        }
                    } else {
                        break;
                    }
                }
                self.expect(TokenKind::RParen, "se esperaba `)`");
                VariantFields::Named(named)
            } else {
                let mut tuple = Vec::new();
                loop {
                    tuple.push(self.parse_type());
                    if self.at(TokenKind::Comma) {
                        self.bump();
                        if self.at(TokenKind::RParen) {
                            break;
                        }
                    } else {
                        break;
                    }
                }
                self.expect(TokenKind::RParen, "se esperaba `)`");
                VariantFields::Tuple(tuple)
            }
        } else {
            VariantFields::Unit
        };
        Some(Variant {
            name,
            fields,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_pact(&mut self, start: Span, unveil: bool) -> Option<Pact> {
        self.bump();
        let name = self.expect_ident("se esperaba el nombre del `pact`")?;
        let params = self.parse_type_params();
        let supertrait = if self.at(TokenKind::Colon) {
            self.bump();
            let first = self.parse_trait_path();
            if self.at(TokenKind::Comma) {
                let span = self.current_span();
                self.error_code_at(
                    "PGS-E1203",
                    "un `pact` admite como máximo un superpact",
                    span,
                );
                while self.at(TokenKind::Comma) {
                    self.bump();
                    let _ = self.parse_trait_path();
                }
            }
            Some(first)
        } else {
            None
        };
        self.skip_comments();
        self.expect(
            TokenKind::Newline,
            "se esperaba un salto de línea tras `pact`",
        );
        self.skip_comments();
        self.expect(TokenKind::Indent, "se esperaba un bloque de métodos");
        let mut methods = Vec::new();
        loop {
            self.skip_newlines();
            if self.at(TokenKind::Dedent) {
                self.bump();
                break;
            }
            if self.at(TokenKind::Eof) {
                self.error("`pact` sin `DEDENT`");
                break;
            }
            if self.at(TokenKind::Essence) {
                let span = self.current_span();
                self.error_code_at("PGS-E1307", "`pact` no admite tipos asociados", span);
                self.recover_to_line_end();
                continue;
            }
            if matches!(self.peek_kind(), TokenKind::Sigil | TokenKind::Relic) {
                let span = self.current_span();
                self.error_code_at("PGS-E1204", "`pact` no admite constantes asociadas", span);
                self.recover_to_line_end();
                continue;
            }
            methods.push(self.parse_method(false)?);
            self.skip_comments();
            if self.at(TokenKind::Newline) {
                self.bump();
            }
        }
        if methods.is_empty() {
            self.error("`pact` requiere al menos un método");
        }
        Some(Pact {
            unveil,
            name,
            params,
            supertrait,
            methods,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_method(&mut self, require_body: bool) -> Option<Method> {
        let start = self.current_span();
        let name = self.expect_ident("se esperaba el nombre del método")?;
        self.expect(TokenKind::Eq, "se esperaba `=`");
        self.expect(TokenKind::LParen, "se esperaba `(`");
        let receiver = if self.at(TokenKind::At) {
            self.bump();
            Receiver::Ref
        } else if self.at(TokenKind::AtMut) {
            self.bump();
            Receiver::Mut
        } else if self.at(TokenKind::AtOwn) {
            self.bump();
            Receiver::Own
        } else {
            self.error("un método requiere `@`, `@mut` o `@own`");
            Receiver::Ref
        };
        let mut params = Vec::new();
        if self.at(TokenKind::Comma) {
            self.bump();
            if self.at(TokenKind::RParen) {
                self.bump();
            } else {
                params = self.parse_params();
            }
        } else {
            self.expect(TokenKind::RParen, "se esperaba `)`");
        }
        self.expect(TokenKind::Arrow, "se esperaba `->`");
        let ret = self.parse_type();
        self.skip_comments();
        let body = if self.at(TokenKind::Newline) && self.peek_n(1) == TokenKind::Indent {
            Some(self.parse_block())
        } else {
            if require_body {
                self.error("un método de `ritual` requiere cuerpo");
            }
            None
        };
        Some(Method {
            name,
            receiver,
            params,
            ret,
            body,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_trait_path(&mut self) -> Vec<String> {
        let path = self.parse_path();
        if self.at(TokenKind::LBracket) {
            self.bump();
            while !self.at(TokenKind::RBracket) && !self.at(TokenKind::Eof) {
                let _ = self.parse_type();
                if self.at(TokenKind::Comma) {
                    self.bump();
                } else {
                    break;
                }
            }
            self.expect(TokenKind::RBracket, "se esperaba `]`");
        }
        path
    }

    fn parse_ritual(&mut self, start: Span, unveil: bool) -> Option<Ritual> {
        self.bump();
        let params = self.parse_type_params();
        let ty = self.parse_type();
        let trait_path = if self.at(TokenKind::For) {
            self.bump();
            Some(self.parse_trait_path())
        } else {
            None
        };
        self.skip_comments();
        self.expect(
            TokenKind::Newline,
            "se esperaba un salto de línea tras `ritual`",
        );
        self.skip_comments();
        self.expect(TokenKind::Indent, "se esperaba un bloque de `ritual`");
        let mut items = Vec::new();
        loop {
            self.skip_newlines();
            if self.at(TokenKind::Dedent) {
                self.bump();
                break;
            }
            if self.at(TokenKind::Eof) {
                self.error("`ritual` sin `DEDENT`");
                break;
            }
            if self.at(TokenKind::Sigil) || self.at(TokenKind::Relic) {
                let const_start = self.current_span();
                let constant = self.parse_const(const_start, false)?;
                items.push(RitualItem::Const(constant));
                self.skip_comments();
                if self.at(TokenKind::Newline) {
                    self.bump();
                }
                continue;
            }
            let name = self.expect_ident("se esperaba un item de `ritual`")?;
            let method_ahead = self.at(TokenKind::Eq)
                && self.peek_n(1) == TokenKind::LParen
                && matches!(
                    self.peek_n(2),
                    TokenKind::At | TokenKind::AtMut | TokenKind::AtOwn
                );
            let item = if method_ahead {
                self.expect(TokenKind::Eq, "se esperaba `=`");
                let mut method = self.parse_method_after_name(name, start, true)?;
                method.span = self.span_from(start.start, self.last_end());
                RitualItem::Method(method)
            } else {
                let mut function = self.parse_function_after_name(name, start, false, false)?;
                function.span = self.span_from(start.start, self.last_end());
                RitualItem::Function(function)
            };
            items.push(item);
            self.skip_comments();
            if self.at(TokenKind::Newline) {
                self.bump();
            }
        }
        if items.is_empty() {
            self.error("`ritual` requiere al menos un item");
        }
        Some(Ritual {
            unveil,
            params,
            ty,
            trait_path,
            items,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_method_after_name(
        &mut self,
        name: String,
        start: Span,
        require_body: bool,
    ) -> Option<Method> {
        self.expect(TokenKind::LParen, "se esperaba `(`");
        let receiver = if self.at(TokenKind::At) {
            self.bump();
            Receiver::Ref
        } else if self.at(TokenKind::AtMut) {
            self.bump();
            Receiver::Mut
        } else if self.at(TokenKind::AtOwn) {
            self.bump();
            Receiver::Own
        } else {
            self.error("un método requiere `@`, `@mut` o `@own`");
            Receiver::Ref
        };
        let mut params = Vec::new();
        if self.at(TokenKind::Comma) {
            self.bump();
            if self.at(TokenKind::RParen) {
                self.bump();
            } else {
                params = self.parse_params();
            }
        } else {
            self.expect(TokenKind::RParen, "se esperaba `)`");
        }
        self.expect(TokenKind::Arrow, "se esperaba `->`");
        let ret = self.parse_type();
        self.skip_comments();
        let body = if self.at(TokenKind::Newline) && self.peek_n(1) == TokenKind::Indent {
            Some(self.parse_block())
        } else {
            if require_body {
                self.error("un método de `ritual` requiere cuerpo");
            }
            None
        };
        Some(Method {
            name,
            receiver,
            params,
            ret,
            body,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_essence(&mut self, start: Span, unveil: bool) -> Option<Essence> {
        self.bump();
        let name = self.expect_ident("se esperaba el nombre de la `essence`")?;
        let params = self.parse_type_params();
        self.expect(TokenKind::Eq, "se esperaba `=` en `essence`");
        let ty = self.parse_type();
        Some(Essence {
            unveil,
            name,
            params,
            ty,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_foreign(&mut self, start: Span) -> Option<Foreign> {
        self.bump();
        let abi = self.parse_string_value()?;
        if abi == "js" {
            let span = self.current_span();
            self.error_code_at(
                "PGS-E2022",
                "`abi \"js\"` está diferido; el backend JS no existe en 0.6.0",
                span,
            );
        }
        self.skip_comments();
        self.expect(
            TokenKind::Newline,
            "se esperaba un salto de línea tras `foreign`",
        );
        self.skip_comments();
        self.expect(TokenKind::Indent, "se esperaba un bloque `foreign`");
        let mut items = Vec::new();
        loop {
            self.skip_newlines();
            if self.at(TokenKind::Dedent) {
                self.bump();
                break;
            }
            if self.at(TokenKind::Eof) {
                self.error("`foreign` sin `DEDENT`");
                break;
            }
            let sig_start = self.current_span();
            let name = self.expect_ident("se esperaba el nombre de la función FFI")?;
            self.expect(TokenKind::Eq, "se esperaba `=`");
            let generics = self.parse_type_params();
            self.expect(TokenKind::LParen, "se esperaba `(`");
            let params = self.parse_params();
            self.expect(TokenKind::Arrow, "se esperaba `->`");
            let ret = self.parse_type();
            items.push(FunctionSig {
                name,
                generics,
                params,
                ret,
                span: self.span_from(sig_start.start, self.last_end()),
            });
            self.skip_comments();
            let body_follows = self.at(TokenKind::Indent)
                || (self.at(TokenKind::Newline) && self.peek_n(1) == TokenKind::Indent);
            if body_follows {
                let span = self.current_span();
                self.error_code_at(
                    "PGS-E1601",
                    "una declaración `foreign` no puede tener cuerpo",
                    span,
                );
                if self.at(TokenKind::Newline) {
                    self.bump();
                }
                let mut depth = 1usize;
                self.bump();
                while depth > 0 && !self.at(TokenKind::Eof) {
                    match self.peek_kind() {
                        TokenKind::Indent => depth += 1,
                        TokenKind::Dedent => depth -= 1,
                        _ => {}
                    }
                    self.bump();
                }
            }
            if self.at(TokenKind::Newline) {
                self.bump();
            }
        }
        if items.is_empty() {
            self.error("`foreign` requiere al menos una firma");
        }
        Some(Foreign {
            abi,
            items,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_function(&mut self, start: Span, unveil: bool, curse: bool) -> Option<Function> {
        if curse {
            self.bump();
        }
        let name = self.expect_ident("se esperaba el nombre de la función")?;
        self.parse_function_after_name(name, start, unveil, curse)
    }

    fn parse_function_after_name(
        &mut self,
        name: String,
        start: Span,
        unveil: bool,
        curse: bool,
    ) -> Option<Function> {
        self.expect(TokenKind::Eq, "se esperaba `=`");
        let type_params = self.parse_type_params();
        self.expect(TokenKind::LParen, "se esperaba `(`");
        let params = self.parse_params();
        if self.at(TokenKind::Arrow) {
            self.bump();
        } else {
            let span = self.current_span();
            self.error_code_at("PGS-E7001", "la función requiere un tipo de retorno", span);
        }
        let ret = self.parse_type();
        if self.at_ident("where") {
            let span = self.current_span();
            self.error_code_at(
                "PGS-E1306",
                "las cláusulas `where` no están permitidas; usa bounds en `[T: Pact]`",
                span,
            );
            while !self.at(TokenKind::Newline) && !self.at(TokenKind::Eof) {
                self.bump();
            }
        }
        let body = self.parse_block();
        if curse && !self.source[..self.last_end() as usize].contains("-- SAFETY:") {
            let span = self.span_from(start.start, self.last_end());
            self.error_code_at(
                "PGS-E1603",
                "una función `curse` requiere un comentario `-- SAFETY:`",
                span,
            );
        }
        Some(Function {
            unveil,
            curse,
            name,
            type_params,
            params,
            ret,
            body,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_const(&mut self, start: Span, unveil: bool) -> Option<Const> {
        let kind = if self.at(TokenKind::Sigil) {
            self.bump();
            ConstKind::Sigil
        } else {
            self.bump();
            ConstKind::Relic
        };
        let name = self.expect_ident("se esperaba el nombre de la constante")?;
        if !self.at(TokenKind::Colon) {
            let span = self.current_span();
            self.error_code_at(
                "PGS-E1106",
                "`sigil`/`relic` requiere un tipo explícito",
                span,
            );
        } else {
            self.bump();
        }
        let ty = self.parse_type();
        self.expect(TokenKind::Eq, "se esperaba `=`");
        let value = self.parse_bp(0);
        Some(Const {
            unveil,
            kind,
            name,
            ty,
            value: Some(value),
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_grimoire(&mut self, start: Span) -> Option<Grimoire> {
        self.bump();
        let ret = if self.at(TokenKind::Colon) {
            self.bump();
            Some(self.parse_type())
        } else {
            None
        };
        let body = self.parse_block();
        Some(Grimoire {
            ret,
            body,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_test(&mut self, start: Span, _derives: Vec<String>) -> Option<Item> {
        // `@@` ya fue consumido y el identificador `test` está en `pos - 1`.
        let mut options = Vec::new();
        if self.at(TokenKind::LParen) {
            self.bump();
            if !self.at(TokenKind::RParen) {
                loop {
                    let opt_start = self.current_span();
                    let name = self.expect_ident("se esperaba una opción de test")?;
                    if name == "should_panic" && !self.at(TokenKind::Colon) {
                        self.error_code_at(
                            "PGS-E1703",
                            "`should_panic` requiere un mensaje",
                            opt_start,
                        );
                        options.push(TestOption {
                            name,
                            message: String::new(),
                            span: opt_start,
                        });
                        if self.at(TokenKind::Comma) {
                            self.bump();
                        }
                        continue;
                    }
                    self.expect(TokenKind::Colon, "se esperaba `:`");
                    let message = self.parse_string_value()?;
                    options.push(TestOption {
                        name,
                        message,
                        span: self.span_from(opt_start.start, self.last_end()),
                    });
                    if self.at(TokenKind::Comma) {
                        self.bump();
                        if self.at(TokenKind::RParen) {
                            break;
                        }
                    } else {
                        break;
                    }
                }
            }
            self.expect(TokenKind::RParen, "se esperaba `)`");
        }
        self.skip_comments();
        self.expect(
            TokenKind::Newline,
            "se esperaba un salto de línea tras `@@test`",
        );
        self.skip_comments();
        let name = self.expect_ident("se esperaba el nombre del test")?;
        self.expect(TokenKind::Eq, "se esperaba `=`");
        self.expect(TokenKind::LParen, "se esperaba `(`");
        if !self.at(TokenKind::RParen) {
            let span = self.current_span();
            self.error_code_at("PGS-E1701", "un `@@test` no lleva parámetros", span);
            let mut depth = 1usize;
            while depth > 0 && !self.at(TokenKind::Eof) {
                match self.peek_kind() {
                    TokenKind::LParen => depth += 1,
                    TokenKind::RParen => depth -= 1,
                    _ => {}
                }
                self.bump();
            }
        }
        self.expect(TokenKind::RParen, "un test no lleva parámetros");
        self.expect(TokenKind::Arrow, "se esperaba `->`");
        let ret = self.parse_type();
        if !matches!(
            &ret.kind,
            TypeKind::Path { segments, .. } if segments.len() == 1 && segments[0] == "Unit"
        ) {
            let span = ret.span;
            self.error_code_at("PGS-E1702", "un `@@test` solo puede devolver `Unit`", span);
        }
        let body = self.parse_block();
        Some(Item {
            kind: ItemKind::Test(Test {
                options,
                name,
                ret,
                body,
                span: self.span_from(start.start, self.last_end()),
            }),
            derives: Vec::new(),
            visibility: Visibility::Private,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_type_params(&mut self) -> Vec<TypeParam> {
        let mut params = Vec::new();
        if !self.at(TokenKind::LBracket) {
            return params;
        }
        self.bump();
        if self.at(TokenKind::RBracket) {
            self.bump();
            return params;
        }
        loop {
            let start = self.current_span();
            if self.at_ident("const") {
                self.error_code_at(
                    "PGS-E1308",
                    "los genéricos `const` no están permitidos",
                    start,
                );
                while !matches!(
                    self.peek_kind(),
                    TokenKind::Comma | TokenKind::RBracket | TokenKind::Eof
                ) {
                    self.bump();
                }
                if self.at(TokenKind::Comma) {
                    self.bump();
                    continue;
                }
                break;
            }
            let Some(name) = self.expect_ident("se esperaba un parámetro de tipo") else {
                break;
            };
            let mut bounds = Vec::new();
            if self.at(TokenKind::Colon) {
                self.bump();
                loop {
                    bounds.push(self.parse_path());
                    if self.at(TokenKind::Plus) {
                        self.bump();
                    } else {
                        break;
                    }
                }
            }
            params.push(TypeParam {
                name,
                bounds,
                span: self.span_from(start.start, self.last_end()),
            });
            if self.at(TokenKind::Comma) {
                self.bump();
                if self.at(TokenKind::RBracket) {
                    break;
                }
            } else {
                break;
            }
        }
        self.expect(TokenKind::RBracket, "se esperaba `]`");
        params
    }

    fn parse_declaration_root(&mut self) -> Option<DeclarationFile> {
        let start = self.current_span().start;
        self.skip_comments();
        self.skip_newlines();
        if !self.at(TokenKind::Abi) {
            let span = self.current_span();
            self.error_code_at(
                "PGS-E2020",
                "un archivo `.d.pengu` debe empezar por `abi`",
                span,
            );
            return None;
        }
        self.bump();
        let abi = self.parse_string_value()?;
        if abi == "js" {
            let span = self.current_span();
            self.error_code_at(
                "PGS-E2022",
                "`abi \"js\"` está diferido; el backend JS no existe en 0.6.0",
                span,
            );
        }
        self.skip_comments();
        self.expect(
            TokenKind::Newline,
            "se esperaba un salto de línea tras `abi`",
        );
        self.skip_comments();
        let mut items = Vec::new();
        while !self.at(TokenKind::Eof) {
            let before = self.pos;
            if let Some(item) = self.parse_decl_item() {
                items.push(item);
            }
            self.skip_comments();
            if self.at(TokenKind::Newline) {
                self.bump();
            } else if !matches!(self.peek_kind(), TokenKind::Eof | TokenKind::Dedent)
                && !self.previous_is_dedent()
                && !self.previous_is_newline()
            {
                self.error("se esperaba un salto de línea entre declaraciones");
                self.recover_to_line_end();
            }
            if self.pos == before {
                self.bump();
            }
            self.skip_newlines();
        }
        Some(DeclarationFile {
            abi,
            items,
            span: self.span_from(start, self.last_end().max(start)),
        })
    }

    fn parse_decl_item(&mut self) -> Option<Item> {
        let start = self.current_span();
        let kind = match self.peek_kind() {
            TokenKind::Summon => ItemKind::Summon(self.parse_summon(start)?),
            TokenKind::Rune => ItemKind::Rune(self.parse_decl_rune(start)?),
            TokenKind::Enchanting => ItemKind::Enchanting(self.parse_enchanting(start, false)?),
            TokenKind::Pact => ItemKind::Pact(self.parse_decl_pact(start)?),
            TokenKind::Ident => self.parse_decl_ident(start)?,
            TokenKind::Unveil => {
                self.error_code_at(
                    "PGS-E2027",
                    "`.d.pengu` no admite `unveil`; todas las declaraciones son públicas",
                    start,
                );
                self.recover_to_line_end();
                return None;
            }
            TokenKind::Grimoire => {
                self.error_code_at("PGS-E2026", "`.d.pengu` no admite `grimoire`", start);
                self.recover_to_line_end();
                return None;
            }
            TokenKind::Sigil | TokenKind::Relic | TokenKind::Foreign => {
                self.error_code_at(
                    "PGS-E2021",
                    "`.d.pengu` no admite cuerpos, `sigil` ni `relic`",
                    start,
                );
                self.recover_to_line_end();
                return None;
            }
            _ => {
                self.error("se esperaba una declaración en `.d.pengu`");
                self.recover_to_line_end();
                return None;
            }
        };
        Some(Item {
            span: self.span_from(start.start, self.last_end()),
            kind,
            derives: Vec::new(),
            visibility: Visibility::Public,
        })
    }

    fn parse_decl_rune(&mut self, start: Span) -> Option<Rune> {
        self.bump();
        let name = self.expect_ident("se esperaba el nombre del `rune`")?;
        let params = self.parse_type_params();
        self.skip_comments();
        self.expect(
            TokenKind::Newline,
            "se esperaba un salto de línea tras `rune`",
        );
        self.skip_comments();
        let mut fields = Vec::new();
        let mut methods = Vec::new();
        if self.at(TokenKind::Indent) {
            self.bump();
            loop {
                self.skip_newlines();
                if self.at(TokenKind::Dedent) {
                    self.bump();
                    break;
                }
                if self.at(TokenKind::Eof) {
                    self.error("`rune` sin `DEDENT`");
                    break;
                }
                let member_start = self.current_span();
                let member_name = self.expect_ident("se esperaba un miembro de `rune`")?;
                if self.at(TokenKind::Colon) {
                    self.bump();
                    let ty = self.parse_type();
                    fields.push(Field {
                        unveil: false,
                        name: member_name,
                        ty,
                        span: self.span_from(member_start.start, self.last_end()),
                    });
                } else {
                    let method = self.parse_decl_method(member_name, member_start)?;
                    methods.push(method);
                }
                self.skip_comments();
                if self.at(TokenKind::Newline) {
                    self.bump();
                }
            }
        }
        Some(Rune {
            unveil: false,
            name,
            params,
            fields,
            methods,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_decl_pact(&mut self, start: Span) -> Option<Pact> {
        self.bump();
        let name = self.expect_ident("se esperaba el nombre del `pact`")?;
        let params = self.parse_type_params();
        let supertrait = if self.at(TokenKind::Colon) {
            self.bump();
            Some(self.parse_trait_path())
        } else {
            None
        };
        self.skip_comments();
        self.expect(
            TokenKind::Newline,
            "se esperaba un salto de línea tras `pact`",
        );
        self.skip_comments();
        self.expect(TokenKind::Indent, "se esperaba un bloque de métodos");
        let mut methods = Vec::new();
        loop {
            self.skip_newlines();
            if self.at(TokenKind::Dedent) {
                self.bump();
                break;
            }
            if self.at(TokenKind::Eof) {
                self.error("`pact` sin `DEDENT`");
                break;
            }
            let member_start = self.current_span();
            let member_name = self.expect_ident("se esperaba el nombre del método")?;
            methods.push(self.parse_decl_method(member_name, member_start)?);
            self.skip_comments();
            if self.at(TokenKind::Newline) {
                self.bump();
            }
        }
        Some(Pact {
            unveil: false,
            name,
            params,
            supertrait,
            methods,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_decl_method(&mut self, name: String, start: Span) -> Option<Method> {
        self.expect(TokenKind::Eq, "se esperaba `=`");
        self.expect(TokenKind::LParen, "se esperaba `(`");
        let receiver = if self.at(TokenKind::At) {
            self.bump();
            Receiver::Ref
        } else if self.at(TokenKind::AtMut) {
            self.bump();
            Receiver::Mut
        } else if self.at(TokenKind::AtOwn) {
            self.bump();
            Receiver::Own
        } else {
            self.error("un método requiere `@`, `@mut` o `@own`");
            Receiver::Ref
        };
        let mut params = Vec::new();
        if self.at(TokenKind::Comma) {
            self.bump();
            if !self.at(TokenKind::RParen) {
                params = self.parse_params();
            } else {
                self.bump();
            }
        } else {
            self.expect(TokenKind::RParen, "se esperaba `)`");
        }
        self.expect(TokenKind::Arrow, "se esperaba `->`");
        let ret = self.parse_type();
        if self.at(TokenKind::Newline) && self.peek_n(1) == TokenKind::Indent {
            self.error("`.d.pengu` no admite cuerpos de método");
        }
        Some(Method {
            name,
            receiver,
            params,
            ret,
            body: None,
            span: self.span_from(start.start, self.last_end()),
        })
    }

    fn parse_decl_ident(&mut self, start: Span) -> Option<ItemKind> {
        let name = self.expect_ident("se esperaba una declaración")?;
        if self.at(TokenKind::Colon) {
            self.bump();
            let ty = self.parse_type();
            let value = if self.at(TokenKind::Eq) {
                self.bump();
                Some(self.parse_bp(0))
            } else {
                None
            };
            return Some(ItemKind::Const(Const {
                unveil: false,
                kind: ConstKind::Sigil,
                name,
                ty,
                value,
                span: self.span_from(start.start, self.last_end()),
            }));
        }
        self.expect(TokenKind::Eq, "se esperaba `=` o `:`");
        let generics = self.parse_type_params();
        self.expect(TokenKind::LParen, "se esperaba `(`");
        let params = self.parse_params();
        self.expect(TokenKind::Arrow, "se esperaba `->`");
        let ret = self.parse_type();
        if self.at(TokenKind::Newline) && self.peek_n(1) == TokenKind::Indent {
            self.error("`.d.pengu` no admite cuerpos de función");
        }
        Some(ItemKind::FunctionSig(FunctionSig {
            name,
            generics,
            params,
            ret,
            span: self.span_from(start.start, self.last_end()),
        }))
    }

    fn parse_path(&mut self) -> Vec<String> {
        let mut segments = Vec::new();
        if let Some(name) = self.expect_ident("se esperaba un path") {
            segments.push(name);
        }
        while self.at(TokenKind::ColonColon) {
            self.bump();
            if let Some(name) = self.expect_ident("se esperaba un segmento de path") {
                segments.push(name);
            }
        }
        segments
    }

    fn parse_string_value(&mut self) -> Option<String> {
        let token = self.current()?;
        if let TokenKind::String(_) = token.kind {
            self.bump();
            let text = token.text(self.source);
            let inner = text
                .strip_prefix('"')
                .and_then(|t| t.strip_suffix('"'))
                .unwrap_or(text);
            Some(inner.to_owned())
        } else {
            self.error_at("se esperaba un string literal", token.span);
            None
        }
    }
    fn peek_is_named_field(&mut self) -> bool {
        self.at(TokenKind::Ident) && self.peek_n(1) == TokenKind::Colon
    }
}

fn infix_binding(kind: TokenKind) -> Option<(u8, u8, BinOp)> {
    let result = match kind {
        TokenKind::Or => (10, 11, BinOp::Or),
        TokenKind::And => (20, 21, BinOp::And),
        TokenKind::EqEq => (30, 31, BinOp::Eq),
        TokenKind::Is => (30, 31, BinOp::Is),
        TokenKind::NotEq => (30, 31, BinOp::Ne),
        TokenKind::Isnt => (30, 31, BinOp::Isnt),
        TokenKind::In => (30, 31, BinOp::In),
        TokenKind::Lt => (40, 41, BinOp::Lt),
        TokenKind::LtEq => (40, 41, BinOp::Le),
        TokenKind::Gt => (40, 41, BinOp::Gt),
        TokenKind::GtEq => (40, 41, BinOp::Ge),
        TokenKind::Plus => (60, 61, BinOp::Add),
        TokenKind::Minus => (60, 61, BinOp::Sub),
        TokenKind::Star => (70, 71, BinOp::Mul),
        TokenKind::Slash => (70, 71, BinOp::Div),
        TokenKind::Percent => (70, 71, BinOp::Rem),
        _ => return None,
    };
    Some(result)
}

fn is_comparison_kind(kind: TokenKind) -> bool {
    matches!(
        kind,
        TokenKind::EqEq
            | TokenKind::NotEq
            | TokenKind::Lt
            | TokenKind::LtEq
            | TokenKind::Gt
            | TokenKind::GtEq
            | TokenKind::Is
            | TokenKind::Isnt
    )
}
