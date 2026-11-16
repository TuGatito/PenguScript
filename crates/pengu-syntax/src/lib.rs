#![forbid(unsafe_code)]
//! Lexer de PenguScript.
//!
//! Convierte texto UTF-8 en tokens con spans, aplica la indentación
//! significativa y construye el AST de expresiones, tipos, patrones, items y
//! archivos `.d.pengu`. El CST conserva además todo el texto y el trivia. Los
//! diagnósticos son recuperables.

pub mod ast;
pub mod cst;
pub mod format;
mod lexer;
pub mod limits;
mod parser;

pub use cst::{SyntaxElement, SyntaxKind, SyntaxNode, SyntaxToken, SyntaxTree};
pub use format::{Formatted, format_declaration, format_source, reconstructs};
pub use lexer::{Lexer, is_reserved, lex};
pub use limits::{MAX_DEPTH, MAX_LINES, MAX_SOURCE_BYTES};
pub use parser::{
    ParsedDeclaration, ParsedExpr, ParsedProgram, parse_declaration_file, parse_expression,
    parse_program,
};

use pengu_diag::Diagnostic;
use pengu_span::Span;

/// Variante de un literal de string.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum StringKind {
    /// `"..."`, con escapes e interpolación.
    Normal,
    /// `"""..."""`, multilínea, con escapes e interpolación.
    Triple,
    /// `r"..."` o `r#"..."#`, sin escapes ni interpolación.
    Raw,
    /// `b"..."`, bytes.
    Byte,
    /// `c"..."`, string C.
    C,
}

/// Tipo de comentario.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum CommentKind {
    /// `-- ...`
    Line,
    /// `--[[ ... ]]`
    Block,
    /// `--- ...`
    DocOuter,
    /// `--! ...`
    DocInner,
}

/// Tipo de token.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum TokenKind {
    // Literales
    Int,
    Float,
    Char,
    ByteChar,
    String(StringKind),
    StringStart(StringKind),
    StringText,
    StringEnd,
    InterpStart,
    InterpEnd,

    // Booleanos / ausencia
    True,
    False,
    None,

    // Identificadores y keywords
    Ident,
    Rune,
    Enchanting,
    Pact,
    Ritual,
    Essence,
    Scroll,
    Summon,
    Unveil,
    Grimoire,
    Foreign,
    Curse,
    Abi,
    Ptr,
    Bind,
    Morph,
    Sigil,
    Relic,
    If,
    Elseif,
    Else,
    Unless,
    Match,
    When,
    Then,
    For,
    While,
    Loop,
    Break,
    Continue,
    Return,
    Do,
    And,
    Or,
    Not,
    Is,
    Isnt,
    In,
    As,
    Some,
    Ok,
    Err,
    SelfType,

    // Puntuación
    LParen,
    RParen,
    LBracket,
    RBracket,
    LBrace,
    RBrace,
    Comma,
    Semicolon,
    Colon,
    ColonColon,
    Dot,
    DotDot,
    DotDotEq,
    Arrow,
    FatArrow,
    Eq,
    EqEq,
    NotEq,
    Lt,
    LtEq,
    Gt,
    GtEq,
    Plus,
    Minus,
    Star,
    Slash,
    Percent,
    Question,
    At,
    AtMut,
    AtOwn,
    AtAt,
    Pipe,
    Amp,
    Bang,

    // Trivia / estructura
    Comment(CommentKind),
    Newline,
    Indent,
    Dedent,
    /// Hueco de espacios/saltos sintetizado por el CST (nunca por el lexer).
    Whitespace,
    Eof,
}

impl TokenKind {
    /// `true` para tokens que el parser normalmente ignora.
    #[must_use]
    pub const fn is_trivia(self) -> bool {
        matches!(self, Self::Comment(_) | Self::Newline | Self::Whitespace)
    }
}

/// Token con su span en el archivo.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub struct Token {
    /// Tipo.
    pub kind: TokenKind,
    /// Ubicación.
    pub span: Span,
}

impl Token {
    /// Crea un token.
    #[must_use]
    pub const fn new(kind: TokenKind, span: Span) -> Self {
        Self { kind, span }
    }

    /// Texto exacto del token en `source`.
    #[must_use]
    pub fn text<'a>(&self, source: &'a str) -> &'a str {
        &source[self.span.start as usize..self.span.end as usize]
    }
}

/// Resultado del lexer.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct Lexed {
    /// Tokens, incluyendo trivia y `Eof`.
    pub tokens: Vec<Token>,
    /// Diagnósticos léxicos.
    pub diagnostics: Vec<Diagnostic>,
}

impl Lexed {
    /// `true` si no hay diagnósticos.
    #[must_use]
    pub fn is_clean(&self) -> bool {
        self.diagnostics.is_empty()
    }

    /// Itera tokens no-trivia.
    pub fn significant(&self) -> impl Iterator<Item = &Token> {
        self.tokens.iter().filter(|token| !token.kind.is_trivia())
    }
}
