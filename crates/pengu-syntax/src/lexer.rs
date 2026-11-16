use pengu_diag::{Diagnostic, Severity};
use pengu_span::{FileId, Span};
use unicode_ident::{is_xid_continue, is_xid_start};

use crate::limits::source_diagnostic;
use crate::{CommentKind, Lexed, StringKind, Token, TokenKind};

/// Lexer de PenguScript.
#[derive(Debug)]
pub struct Lexer<'a> {
    file: FileId,
    source: &'a str,
    pos: usize,
    offset: u32,
    tokens: Vec<Token>,
    diagnostics: Vec<Diagnostic>,
    indents: Vec<u32>,
    at_line_start: bool,
    line_blank: bool,
    line_comment_only: bool,
    pending_indent: Option<(u32, usize)>,
    delimiter_depth: usize,
    fragment: bool,
}

impl<'a> Lexer<'a> {
    /// Crea un lexer para un archivo completo.
    #[must_use]
    pub fn new(file: FileId, source: &'a str) -> Self {
        Self {
            file,
            source,
            pos: 0,
            offset: 0,
            tokens: Vec::new(),
            diagnostics: Vec::new(),
            indents: vec![0],
            at_line_start: true,
            line_blank: false,
            line_comment_only: false,
            pending_indent: None,
            delimiter_depth: 0,
            fragment: false,
        }
    }

    fn fragment(file: FileId, source: &'a str, offset: u32) -> Self {
        Self {
            file,
            source,
            pos: 0,
            offset,
            tokens: Vec::new(),
            diagnostics: Vec::new(),
            indents: vec![0],
            at_line_start: false,
            line_blank: false,
            line_comment_only: false,
            pending_indent: None,
            delimiter_depth: 0,
            fragment: true,
        }
    }

    /// Ejecuta el lexer hasta EOF.
    #[must_use]
    pub fn run(mut self) -> Lexed {
        if !self.fragment && self.source.starts_with('\u{feff}') {
            self.error(
                "PGS-E1001",
                "el archivo empieza con un BOM; debe ser UTF-8 sin BOM",
                0,
                3,
            );
            self.pos = 3;
        }

        while self.pos < self.source.len() {
            if self.at_line_start && self.delimiter_depth == 0 && !self.fragment {
                self.handle_line_start();
            }

            self.skip_inline_whitespace();
            if self.pos >= self.source.len() {
                break;
            }

            let start = self.pos;
            if self.at_newline() {
                self.handle_newline(start);
                continue;
            }
            self.at_line_start = false;
            if self.starts_with("--") {
                self.lex_comment();
                self.finish_comment_indent();
                continue;
            }
            self.line_comment_only = false;

            let current = self.current_char();
            if is_xid_start(current) || current == '_' {
                if self.try_string_prefix() {
                    continue;
                }
                self.lex_ident_or_keyword();
                continue;
            }

            match current {
                '0'..='9' => self.lex_number(),
                '"' => self.lex_string(StringKind::Normal, start, 0),
                '\'' => self.lex_char(false),
                '@' => self.lex_at(),
                '(' => {
                    self.advance_ascii();
                    self.push(TokenKind::LParen, start, self.pos);
                    self.delimiter_depth += 1;
                }
                ')' => {
                    self.advance_ascii();
                    self.push(TokenKind::RParen, start, self.pos);
                    self.delimiter_depth = self.delimiter_depth.saturating_sub(1);
                }
                '[' => {
                    self.advance_ascii();
                    self.push(TokenKind::LBracket, start, self.pos);
                    self.delimiter_depth += 1;
                }
                ']' => {
                    self.advance_ascii();
                    self.push(TokenKind::RBracket, start, self.pos);
                    self.delimiter_depth = self.delimiter_depth.saturating_sub(1);
                }
                '{' => {
                    self.advance_ascii();
                    self.push(TokenKind::LBrace, start, self.pos);
                    self.delimiter_depth += 1;
                }
                '}' => {
                    self.advance_ascii();
                    self.push(TokenKind::RBrace, start, self.pos);
                    self.delimiter_depth = self.delimiter_depth.saturating_sub(1);
                }
                ',' => self.single(TokenKind::Comma),
                ';' => self.single(TokenKind::Semicolon),
                ':' => {
                    self.advance_ascii();
                    if self.take_char(':') {
                        self.push(TokenKind::ColonColon, start, self.pos);
                    } else {
                        self.push(TokenKind::Colon, start, self.pos);
                    }
                }
                '.' => {
                    self.advance_ascii();
                    if self.take_char('.') {
                        if self.take_char('=') {
                            self.push(TokenKind::DotDotEq, start, self.pos);
                        } else {
                            self.push(TokenKind::DotDot, start, self.pos);
                        }
                    } else {
                        self.push(TokenKind::Dot, start, self.pos);
                    }
                }
                '-' => {
                    self.advance_ascii();
                    if self.take_char('>') {
                        self.push(TokenKind::Arrow, start, self.pos);
                    } else {
                        self.push(TokenKind::Minus, start, self.pos);
                    }
                }
                '=' => {
                    self.advance_ascii();
                    if self.take_char('=') {
                        self.push(TokenKind::EqEq, start, self.pos);
                    } else if self.take_char('>') {
                        self.push(TokenKind::FatArrow, start, self.pos);
                    } else {
                        self.push(TokenKind::Eq, start, self.pos);
                    }
                }
                '!' => {
                    self.advance_ascii();
                    if self.take_char('=') {
                        self.push(TokenKind::NotEq, start, self.pos);
                    } else {
                        self.push(TokenKind::Bang, start, self.pos);
                    }
                }
                '<' => {
                    self.advance_ascii();
                    if self.take_char('=') {
                        self.push(TokenKind::LtEq, start, self.pos);
                    } else {
                        self.push(TokenKind::Lt, start, self.pos);
                    }
                }
                '>' => {
                    self.advance_ascii();
                    if self.take_char('=') {
                        self.push(TokenKind::GtEq, start, self.pos);
                    } else {
                        self.push(TokenKind::Gt, start, self.pos);
                    }
                }
                '+' => self.single(TokenKind::Plus),
                '*' => self.single(TokenKind::Star),
                '/' => self.single(TokenKind::Slash),
                '%' => self.single(TokenKind::Percent),
                '?' => self.single(TokenKind::Question),
                '|' => self.single(TokenKind::Pipe),
                '&' => self.single(TokenKind::Amp),
                other => {
                    self.error(
                        "PGS-E1011",
                        format!("carácter no reconocido: {other:?}"),
                        start,
                        start + other.len_utf8(),
                    );
                    self.advance_char();
                }
            }
        }

        self.emit_dedents();
        self.push(TokenKind::Eof, self.pos, self.pos);
        Lexed {
            tokens: self.tokens,
            diagnostics: self.diagnostics,
        }
    }

    fn handle_line_start(&mut self) {
        let start = self.pos;
        let mut spaces = 0usize;
        while self.peek_char() == Some(' ') {
            self.pos += 1;
            spaces += 1;
        }
        while self.peek_char() == Some('\t') {
            self.error(
                "PGS-E1002",
                "tabulador en la indentación; usa cuatro espacios",
                self.pos,
                self.pos + 1,
            );
            self.pos += 1;
        }

        if self.at_newline() {
            self.line_blank = true;
            self.line_comment_only = false;
            self.at_line_start = false;
            return;
        }
        if self.starts_with("--") {
            self.line_comment_only = true;
            self.line_blank = false;
            self.pending_indent = Some((spaces as u32, start));
            self.at_line_start = false;
            return;
        }

        self.line_blank = false;
        self.line_comment_only = false;
        self.pending_indent = None;
        self.apply_indent(spaces as u32, start);
        self.at_line_start = false;
    }

    fn apply_indent(&mut self, indent: u32, start: usize) {
        if indent % 4 != 0 {
            self.error(
                "PGS-E1003",
                "la indentación debe ser múltiplo de cuatro espacios",
                start,
                start + indent as usize,
            );
        }

        let top = *self.indents.last().unwrap_or(&0);
        if indent > top {
            self.indents.push(indent);
            self.push(TokenKind::Indent, start, start);
        } else if indent < top {
            while indent < *self.indents.last().unwrap_or(&0) {
                self.indents.pop();
                self.push(TokenKind::Dedent, start, start);
            }
            let top = *self.indents.last().unwrap_or(&0);
            if indent != top {
                self.error(
                    "PGS-E1004",
                    "DEDENT sin un nivel de indentación correspondiente",
                    start,
                    start,
                );
                self.indents.push(indent);
            }
        }
    }

    /// Aplica la indentación pendiente si un comentario de bloque al inicio
    /// de línea termina y deja código en la misma línea.
    fn finish_comment_indent(&mut self) {
        if !self.line_comment_only {
            return;
        }
        let mut i = self.pos;
        while i < self.source.len() && self.source.as_bytes()[i] == b' ' {
            i += 1;
        }
        if i >= self.source.len() || self.at_newline_at(i) || self.source[i..].starts_with("--") {
            return;
        }
        self.line_comment_only = false;
        if let Some((indent, start)) = self.pending_indent.take() {
            self.apply_indent(indent, start);
        }
    }

    fn skip_inline_whitespace(&mut self) {
        loop {
            match self.peek_char() {
                Some(' ') => self.pos += 1,
                Some('\t') => {
                    self.error(
                        "PGS-E1002",
                        "tabulador fuera de un string o comentario",
                        self.pos,
                        self.pos + 1,
                    );
                    self.pos += 1;
                }
                _ => break,
            }
        }
    }

    fn handle_newline(&mut self, start: usize) {
        let len = if self.starts_with("\r\n") { 2 } else { 1 };
        self.pos += len;
        self.at_line_start = true;

        if self.line_blank || self.line_comment_only {
            self.line_blank = false;
            self.line_comment_only = false;
            self.pending_indent = None;
            return;
        }
        if self.delimiter_depth > 0 || self.fragment {
            return;
        }
        if self.should_continue(start, len) {
            self.skip_continuation_indent();
            self.at_line_start = false;
            return;
        }

        self.push(TokenKind::Newline, start, start + len);
    }

    fn should_continue(&self, start: usize, newline_len: usize) -> bool {
        let Some(last) = self.last_significant() else {
            return false;
        };
        if !is_binary_operator(last.kind) {
            return false;
        }
        let current = *self.indents.last().unwrap_or(&0);
        let next_start = start + newline_len;
        let Some(spaces) = self.next_code_indent(next_start) else {
            return false;
        };
        spaces > current
    }

    /// Devuelve la indentación de la siguiente línea con código, saltando
    /// líneas en blanco y comentarios. No modifica el cursor.
    fn next_code_indent(&self, mut i: usize) -> Option<u32> {
        let bytes = self.source.as_bytes();
        while i < bytes.len() {
            let mut indent = 0u32;
            while i < bytes.len() && bytes[i] == b' ' {
                indent += 1;
                i += 1;
            }
            if i >= bytes.len() {
                return None;
            }
            if self.at_newline_at(i) {
                i += if bytes[i] == b'\r' && bytes.get(i + 1) == Some(&b'\n') {
                    2
                } else {
                    1
                };
                continue;
            }
            if self.source[i..].starts_with("--[[") {
                let close = self.source[i + 4..].find("]]")?;
                i += 4 + close + 2;
                while i < bytes.len() && bytes[i] == b' ' {
                    i += 1;
                }
                if i >= bytes.len() {
                    return None;
                }
                if self.at_newline_at(i) {
                    i += if bytes[i] == b'\r' && bytes.get(i + 1) == Some(&b'\n') {
                        2
                    } else {
                        1
                    };
                    continue;
                }
                if self.source[i..].starts_with("--") {
                    while i < bytes.len() && !self.at_newline_at(i) {
                        i += 1;
                    }
                    continue;
                }
                return Some(indent);
            }
            if self.source[i..].starts_with("--") {
                while i < bytes.len() && !self.at_newline_at(i) {
                    i += 1;
                }
                continue;
            }
            return Some(indent);
        }
        None
    }

    fn skip_continuation_indent(&mut self) {
        while self.peek_char() == Some(' ') {
            self.pos += 1;
        }
        while self.peek_char() == Some('\t') {
            self.error(
                "PGS-E1002",
                "tabulador en la continuación de línea",
                self.pos,
                self.pos + 1,
            );
            self.pos += 1;
        }
    }

    fn last_significant(&self) -> Option<&Token> {
        self.tokens
            .iter()
            .rev()
            .find(|token| !token.kind.is_trivia())
    }

    fn lex_comment(&mut self) {
        let start = self.pos;
        if self.starts_with("--[[") {
            self.pos += 4;
            if let Some(end) = self.source[self.pos..].find("]]") {
                self.pos += end + 2;
                self.push(TokenKind::Comment(CommentKind::Block), start, self.pos);
            } else {
                self.pos = self.source.len();
                self.error(
                    "PGS-E1009",
                    "comentario de bloque sin cerrar",
                    start,
                    self.pos,
                );
                self.push(TokenKind::Comment(CommentKind::Block), start, self.pos);
            }
            return;
        }

        let kind = if self.starts_with("---") {
            CommentKind::DocOuter
        } else if self.starts_with("--!") {
            CommentKind::DocInner
        } else {
            CommentKind::Line
        };
        while self.pos < self.source.len() && !self.at_newline() {
            self.advance_char();
        }
        self.push(TokenKind::Comment(kind), start, self.pos);
    }

    fn lex_ident_or_keyword(&mut self) {
        let start = self.pos;
        self.advance_char();
        while let Some(c) = self.peek_char() {
            if !is_xid_continue(c) {
                break;
            }
            self.advance_char();
        }
        let text = &self.source[start..self.pos];
        if let Some(kind) = keyword(text) {
            self.push(kind, start, self.pos);
            return;
        }
        if is_retired(text) {
            self.error(
                "PGS-E1010",
                format!("`{text}` es un término retirado y no puede usarse como identificador"),
                start,
                self.pos,
            );
        }
        self.push(TokenKind::Ident, start, self.pos);
    }

    fn lex_at(&mut self) {
        let start = self.pos;
        self.pos += 1;
        if self.take_char('@') {
            self.push(TokenKind::AtAt, start, self.pos);
            return;
        }
        for (text, kind) in [("mut", TokenKind::AtMut), ("own", TokenKind::AtOwn)] {
            if self.starts_with(text) {
                let after = self.pos + text.len();
                if after >= self.source.len()
                    || !self.source[after..]
                        .chars()
                        .next()
                        .is_some_and(is_xid_continue)
                {
                    self.pos = after;
                    self.push(kind, start, self.pos);
                    return;
                }
            }
        }
        self.push(TokenKind::At, start, self.pos);
    }

    fn try_string_prefix(&mut self) -> bool {
        let start = self.pos;
        let rest = &self.source[start..];
        if rest.starts_with("b'") {
            self.lex_char(true);
            return true;
        }
        if rest.starts_with("b\"") {
            self.pos += 1;
            self.lex_string(StringKind::Byte, start, 0);
            return true;
        }
        if rest.starts_with("c\"") {
            self.pos += 1;
            self.lex_string(StringKind::C, start, 0);
            return true;
        }
        if rest.starts_with("r\"") {
            self.pos += 1;
            self.lex_string(StringKind::Raw, start, 0);
            return true;
        }
        if let Some((hashes, quote_at)) = raw_prefix(rest) {
            self.pos += quote_at;
            self.lex_string(StringKind::Raw, start, hashes);
            return true;
        }
        false
    }

    fn lex_number(&mut self) {
        let start = self.pos;
        let bytes = self.source.as_bytes();
        let mut i = self.pos;
        let mut is_float = false;

        if bytes.get(i) == Some(&b'0')
            && matches!(
                bytes.get(i + 1),
                Some(b'x' | b'X' | b'o' | b'O' | b'b' | b'B')
            )
        {
            let (base, valid) = match bytes[i + 1] {
                b'x' | b'X' => ("hexadecimal", 16u8),
                b'o' | b'O' => ("octal", 8),
                b'b' | b'B' => ("binaria", 2),
                _ => unreachable!(),
            };
            i += 2;
            let mut has_digit = false;
            while i < bytes.len() && (digit_for_base(bytes[i], valid) || bytes[i] == b'_') {
                if digit_for_base(bytes[i], valid) {
                    has_digit = true;
                }
                i += 1;
            }
            if !has_digit {
                self.error(
                    "PGS-E1011",
                    format!("literal entero {base} sin dígitos"),
                    start,
                    i,
                );
                while i < bytes.len() && (bytes[i].is_ascii_alphanumeric() || bytes[i] == b'_') {
                    i += 1;
                }
            } else {
                let suffix_start = i;
                let suffix = self.suffix_end(i);
                if suffix != i {
                    let suffix_text = self.source[suffix_start..suffix].to_ascii_lowercase();
                    if matches!(suffix_text.as_str(), "f32" | "f64") {
                        self.error(
                            "PGS-E1011",
                            "un literal entero no admite sufijo flotante",
                            suffix_start,
                            suffix,
                        );
                    }
                    i = suffix;
                } else if bytes
                    .get(i)
                    .is_some_and(|b| b.is_ascii_alphanumeric() || *b == b'_')
                {
                    let bad = i;
                    self.error(
                        "PGS-E1011",
                        format!("dígito inválido para base {base}"),
                        bad,
                        bad + 1,
                    );
                    while i < bytes.len() && (bytes[i].is_ascii_alphanumeric() || bytes[i] == b'_')
                    {
                        i += 1;
                    }
                }
            }
            self.pos = i;
            self.push(TokenKind::Int, start, i);
            return;
        }

        while i < bytes.len() && (bytes[i].is_ascii_digit() || bytes[i] == b'_') {
            i += 1;
        }

        if bytes.get(i) == Some(&b'.') {
            if bytes.get(i + 1).is_some_and(u8::is_ascii_digit) {
                is_float = true;
                i += 1;
                while i < bytes.len() && (bytes[i].is_ascii_digit() || bytes[i] == b'_') {
                    i += 1;
                }
            } else if bytes.get(i + 1) != Some(&b'.')
                && !bytes
                    .get(i + 1)
                    .is_some_and(|b| b.is_ascii_alphabetic() || *b == b'_')
            {
                self.error("PGS-E1011", "punto decimal sin dígitos", i, i + 1);
                is_float = true;
                i += 1;
            }
        }

        if matches!(bytes.get(i), Some(b'e' | b'E')) {
            let exp_start = i;
            let mut j = i + 1;
            if matches!(bytes.get(j), Some(b'+' | b'-')) {
                j += 1;
            }
            if bytes.get(j).is_some_and(u8::is_ascii_digit) {
                is_float = true;
                i = j + 1;
                while i < bytes.len() && (bytes[i].is_ascii_digit() || bytes[i] == b'_') {
                    i += 1;
                }
            } else {
                self.error(
                    "PGS-E1011",
                    "exponente incompleto",
                    exp_start,
                    j.max(exp_start + 1),
                );
                is_float = true;
                i = j;
            }
        }

        let suffix_start = i;
        let suffix_end = self.suffix_end(i);
        if suffix_end != i {
            let suffix = self.source[suffix_start..suffix_end].to_ascii_lowercase();
            if matches!(suffix.as_str(), "f32" | "f64") {
                is_float = true;
            } else if is_float {
                self.error(
                    "PGS-E1011",
                    "un literal flotante solo admite sufijo F32 o F64",
                    suffix_start,
                    suffix_end,
                );
            }
            i = suffix_end;
        }
        self.pos = i;
        self.push(
            if is_float {
                TokenKind::Float
            } else {
                TokenKind::Int
            },
            start,
            i,
        );
    }

    fn suffix_end(&self, i: usize) -> usize {
        let bytes = self.source.as_bytes();
        let mut j = i;
        while j < bytes.len() && (bytes[j].is_ascii_alphanumeric() || bytes[j] == b'_') {
            j += 1;
        }
        if j == i {
            return i;
        }
        let suffix = self.source[i..j].to_ascii_lowercase();
        if matches!(
            suffix.as_str(),
            "i8" | "i16"
                | "i32"
                | "i64"
                | "isize"
                | "u8"
                | "u16"
                | "u32"
                | "u64"
                | "usize"
                | "f32"
                | "f64"
        ) {
            j
        } else {
            i
        }
    }

    fn lex_char(&mut self, byte: bool) {
        let start = self.pos;
        if byte {
            self.pos += 1;
        }
        self.pos += 1;

        if self.pos >= self.source.len() || self.at_newline() {
            self.error("PGS-E1006", "char sin cerrar", start, self.pos);
            self.push(
                if byte {
                    TokenKind::ByteChar
                } else {
                    TokenKind::Char
                },
                start,
                self.pos,
            );
            return;
        }

        let content_start = self.pos;
        let is_hex_escape = self.source[content_start..].starts_with("\\x");
        let (value, mut i) = if self.peek_char() == Some('\\') {
            self.parse_escape_char(self.pos)
        } else {
            let c = self.current_char();
            (c, self.pos + c.len_utf8())
        };

        if i >= self.source.len() || self.source.as_bytes().get(i) != Some(&b'\'') {
            self.error(
                "PGS-E1006",
                "char sin cerrar o con más de un carácter",
                start,
                i.min(self.source.len()),
            );
            while i < self.source.len()
                && !self.at_newline_at(i)
                && self.source.as_bytes()[i] != b'\''
            {
                i += self.source[i..].chars().next().map_or(1, char::len_utf8);
            }
            if self.source.as_bytes().get(i) == Some(&b'\'') {
                i += 1;
            }
            self.pos = i;
            self.push(
                if byte {
                    TokenKind::ByteChar
                } else {
                    TokenKind::Char
                },
                start,
                self.pos,
            );
            return;
        }
        i += 1;

        if byte && !value.is_ascii() && !is_hex_escape {
            self.error(
                "PGS-E1008",
                "byte char debe ser ASCII o un escape \\xNN",
                start,
                i,
            );
        }

        self.pos = i;
        self.push(
            if byte {
                TokenKind::ByteChar
            } else {
                TokenKind::Char
            },
            start,
            i,
        );
    }

    fn parse_escape_char(&mut self, start: usize) -> (char, usize) {
        let Some(c) = self.source[start + 1..].chars().next() else {
            self.error("PGS-E1007", "escape incompleto", start, self.source.len());
            return ('\u{fffd}', self.source.len());
        };
        let next = start + 1 + c.len_utf8();
        match c {
            'n' => ('\n', next),
            'r' => ('\r', next),
            't' => ('\t', next),
            '\\' => ('\\', next),
            '"' => ('"', next),
            '\'' => ('\'', next),
            '0' => ('\0', next),
            'x' => {
                let end = next + 2;
                if end <= self.source.len() {
                    if let Ok(byte) = u8::from_str_radix(&self.source[next..end], 16) {
                        return (char::from(byte), end);
                    }
                }
                self.error(
                    "PGS-E1007",
                    "escape \\xNN inválido",
                    start,
                    end.min(self.source.len()),
                );
                ('\u{fffd}', end.min(self.source.len()))
            }
            'u' => {
                if self.source.as_bytes().get(next) != Some(&b'{') {
                    self.error("PGS-E1007", "escape \\u{...} inválido", start, next);
                    return ('\u{fffd}', next);
                }
                if let Some(close) = self.source[next + 1..].find('}') {
                    let digits_start = next + 1;
                    let digits_end = digits_start + close;
                    if let Ok(value) =
                        u32::from_str_radix(&self.source[digits_start..digits_end], 16)
                    {
                        if let Some(ch) = char::from_u32(value) {
                            return (ch, digits_end + 1);
                        }
                    }
                    self.error(
                        "PGS-E1007",
                        "escape \\u{...} inválido",
                        start,
                        digits_end + 1,
                    );
                    return ('\u{fffd}', digits_end + 1);
                }
                self.error("PGS-E1007", "escape \\u{...} sin cerrar", start, next);
                ('\u{fffd}', next)
            }
            other => {
                self.error(
                    "PGS-E1007",
                    format!("escape desconocido: \\{other}"),
                    start,
                    next,
                );
                (other, next)
            }
        }
    }

    fn lex_string(&mut self, kind: StringKind, start: usize, hashes: usize) {
        // `pos` apunta a la comilla de apertura.
        let triple = kind == StringKind::Normal && self.starts_with("\"\"\"");
        let kind = if triple { StringKind::Triple } else { kind };
        self.pos += if triple { 3 } else { 1 };
        let content_start = self.pos;

        if kind == StringKind::Raw {
            let terminator = format!("\"{}", "#".repeat(hashes));
            if let Some(rel) = self.source[content_start..].find(&terminator) {
                let close = content_start + rel + terminator.len();
                self.pos = close;
                self.push(TokenKind::String(StringKind::Raw), start, close);
            } else {
                self.pos = self.source.len();
                self.error("PGS-E1005", "string raw sin cerrar", start, self.pos);
                self.push(TokenKind::String(StringKind::Raw), start, self.pos);
            }
            return;
        }

        let closing: &str = if triple { "\"\"\"" } else { "\"" };
        let mut i = content_start;
        let mut close_at = None;
        let mut interps: Vec<(usize, usize, usize, usize)> = Vec::new();
        let mut error_at = None;

        while i < self.source.len() {
            if self.source[i..].starts_with(closing) {
                close_at = Some(i);
                i += closing.len();
                break;
            }
            if !triple && self.at_newline_at(i) {
                error_at = Some(i);
                break;
            }
            let c = self.source[i..].chars().next().unwrap();
            if c == '\\' {
                if self.source[i..].starts_with("\\#{") {
                    i += 3;
                    continue;
                }
                let next = self.scan_escape(i, false);
                i = next;
                continue;
            }
            if matches!(kind, StringKind::Normal | StringKind::Triple)
                && self.source[i..].starts_with("#{")
            {
                let Some(end) = self.find_interp_end(i + 2) else {
                    error_at = Some(i);
                    i = self.source.len();
                    break;
                };
                interps.push((i, i + 2, end, end + 1));
                i = end + 1;
                continue;
            }
            i += c.len_utf8();
        }

        let (close_start, end) = match close_at {
            Some(c) => (c, c + closing.len()),
            None => {
                let at = error_at.unwrap_or(i.min(self.source.len()));
                self.error("PGS-E1005", "string sin cerrar", start, at.max(start));
                (i, at.min(self.source.len()))
            }
        };

        if interps.is_empty() {
            self.pos = end;
            self.push(TokenKind::String(kind), start, end);
            return;
        }

        self.pos = end;
        self.push(TokenKind::StringStart(kind), start, content_start);
        let mut segment = content_start;
        for (hash_start, inner_start, inner_end, brace_end) in interps {
            if segment < hash_start {
                self.push(TokenKind::StringText, segment, hash_start);
            }
            self.push(TokenKind::InterpStart, hash_start, hash_start + 2);
            let fragment = Lexer::fragment(
                self.file,
                &self.source[inner_start..inner_end],
                self.offset + inner_start as u32,
            )
            .run();
            self.tokens.extend(
                fragment
                    .tokens
                    .into_iter()
                    .filter(|token| token.kind != TokenKind::Eof),
            );
            self.diagnostics.extend(fragment.diagnostics);
            self.push(TokenKind::InterpEnd, inner_end, brace_end);
            segment = brace_end;
        }
        if segment < close_start {
            self.push(TokenKind::StringText, segment, close_start);
        }
        self.push(TokenKind::StringEnd, close_start, end);
    }

    fn scan_escape(&mut self, i: usize, byte: bool) -> usize {
        let Some(c) = self.source[i + 1..].chars().next() else {
            self.error("PGS-E1007", "escape incompleto", i, self.source.len());
            return self.source.len();
        };
        let next = i + 1 + c.len_utf8();
        match c {
            'n' | 'r' | 't' | '\\' | '"' | '\'' | '0' => next,
            'x' => {
                let end = next + 2;
                if end <= self.source.len()
                    && self.source[next..end]
                        .chars()
                        .all(|c| c.is_ascii_hexdigit())
                {
                    if byte {
                        return end;
                    }
                    return end;
                }
                self.error(
                    "PGS-E1007",
                    "escape \\xNN inválido",
                    i,
                    end.min(self.source.len()),
                );
                end.min(self.source.len())
            }
            'u' => {
                if self.source.as_bytes().get(next) != Some(&b'{') {
                    self.error("PGS-E1007", "escape \\u{...} inválido", i, next);
                    return next;
                }
                if let Some(close) = self.source[next + 1..].find('}') {
                    let end = next + 1 + close;
                    if self.source[next + 1..end]
                        .chars()
                        .all(|c| c.is_ascii_hexdigit())
                        && u32::from_str_radix(&self.source[next + 1..end], 16)
                            .ok()
                            .and_then(char::from_u32)
                            .is_some()
                    {
                        return end + 1;
                    }
                    self.error("PGS-E1007", "escape \\u{...} inválido", i, end + 1);
                    return end + 1;
                }
                self.error("PGS-E1007", "escape \\u{...} sin cerrar", i, next);
                next
            }
            other => {
                self.error(
                    "PGS-E1007",
                    format!("escape desconocido: \\{other}"),
                    i,
                    next,
                );
                next
            }
        }
    }

    fn find_interp_end(&self, start: usize) -> Option<usize> {
        let mut depth = 1usize;
        let mut i = start;
        while i < self.source.len() {
            let c = self.source[i..].chars().next().unwrap();
            match c {
                '{' => {
                    depth += 1;
                    i += 1;
                }
                '}' => {
                    depth -= 1;
                    if depth == 0 {
                        return Some(i);
                    }
                    i += 1;
                }
                '"' => {
                    i = self.skip_quoted(i, '"');
                }
                '\'' => {
                    i = self.skip_quoted(i, '\'');
                }
                '-' if self.source[i..].starts_with("--") => {
                    i = self.skip_comment(i);
                }
                _ => i += c.len_utf8(),
            }
        }
        None
    }

    fn skip_quoted(&self, start: usize, quote: char) -> usize {
        let mut i = start + quote.len_utf8();
        while i < self.source.len() {
            let c = self.source[i..].chars().next().unwrap();
            if c == '\\' {
                i = (i + 2).min(self.source.len());
                continue;
            }
            if c == quote {
                return i + quote.len_utf8();
            }
            i += c.len_utf8();
        }
        i
    }

    fn skip_comment(&self, start: usize) -> usize {
        if self.source[start..].starts_with("--[[") {
            if let Some(rel) = self.source[start + 4..].find("]]") {
                return start + 4 + rel + 2;
            }
            return self.source.len();
        }
        let mut i = start;
        while i < self.source.len() && !self.at_newline_at(i) {
            i += self.source[i..].chars().next().unwrap().len_utf8();
        }
        i
    }

    fn emit_dedents(&mut self) {
        let at = self.pos;
        while self.indents.pop().is_some_and(|level| level > 0) {
            self.push(TokenKind::Dedent, at, at);
        }
    }

    fn single(&mut self, kind: TokenKind) {
        let start = self.pos;
        self.advance_ascii();
        self.push(kind, start, self.pos);
    }

    fn push(&mut self, kind: TokenKind, start: usize, end: usize) {
        self.tokens.push(Token::new(kind, self.span(start, end)));
    }

    fn error(&mut self, code: &'static str, message: impl Into<String>, start: usize, end: usize) {
        self.diagnostics.push(Diagnostic::new(
            code,
            Severity::Error,
            message,
            self.span(start, end),
        ));
    }

    fn span(&self, start: usize, end: usize) -> Span {
        Span::new(
            self.file,
            self.offset + u32::try_from(start).unwrap_or(u32::MAX),
            self.offset + u32::try_from(end).unwrap_or(u32::MAX),
        )
    }

    fn current_char(&self) -> char {
        self.source[self.pos..].chars().next().unwrap_or('\0')
    }

    fn peek_char(&self) -> Option<char> {
        self.source[self.pos..].chars().next()
    }

    fn advance_char(&mut self) {
        if let Some(c) = self.peek_char() {
            self.pos += c.len_utf8();
        }
    }

    fn advance_ascii(&mut self) {
        self.pos += 1;
    }

    fn starts_with(&self, text: &str) -> bool {
        self.source[self.pos..].starts_with(text)
    }

    fn take_char(&mut self, c: char) -> bool {
        if self.peek_char() == Some(c) {
            self.pos += c.len_utf8();
            true
        } else {
            false
        }
    }

    fn at_newline(&self) -> bool {
        self.at_newline_at(self.pos)
    }

    fn at_newline_at(&self, i: usize) -> bool {
        matches!(self.source.as_bytes().get(i), Some(b'\n' | b'\r'))
    }
}

fn digit_for_base(byte: u8, base: u8) -> bool {
    match base {
        2 => matches!(byte, b'0' | b'1'),
        8 => matches!(byte, b'0'..=b'7'),
        16 => byte.is_ascii_hexdigit(),
        _ => false,
    }
}

fn keyword(text: &str) -> Option<TokenKind> {
    Some(match text {
        "rune" => TokenKind::Rune,
        "enchanting" => TokenKind::Enchanting,
        "pact" => TokenKind::Pact,
        "ritual" => TokenKind::Ritual,
        "essence" => TokenKind::Essence,
        "scroll" => TokenKind::Scroll,
        "summon" => TokenKind::Summon,
        "unveil" => TokenKind::Unveil,
        "grimoire" => TokenKind::Grimoire,
        "foreign" => TokenKind::Foreign,
        "curse" => TokenKind::Curse,
        "abi" => TokenKind::Abi,
        "Ptr" => TokenKind::Ptr,
        "bind" => TokenKind::Bind,
        "morph" => TokenKind::Morph,
        "sigil" => TokenKind::Sigil,
        "relic" => TokenKind::Relic,
        "if" => TokenKind::If,
        "elseif" => TokenKind::Elseif,
        "else" => TokenKind::Else,
        "unless" => TokenKind::Unless,
        "match" => TokenKind::Match,
        "when" => TokenKind::When,
        "then" => TokenKind::Then,
        "for" => TokenKind::For,
        "while" => TokenKind::While,
        "loop" => TokenKind::Loop,
        "break" => TokenKind::Break,
        "continue" => TokenKind::Continue,
        "return" => TokenKind::Return,
        "do" => TokenKind::Do,
        "and" => TokenKind::And,
        "or" => TokenKind::Or,
        "not" => TokenKind::Not,
        "is" => TokenKind::Is,
        "isnt" => TokenKind::Isnt,
        "in" => TokenKind::In,
        "as" => TokenKind::As,
        "true" => TokenKind::True,
        "false" => TokenKind::False,
        "none" => TokenKind::None,
        "some" => TokenKind::Some,
        "ok" => TokenKind::Ok,
        "err" => TokenKind::Err,
        "Self" => TokenKind::SelfType,
        _ => return None,
    })
}

fn is_retired(text: &str) -> bool {
    matches!(
        text,
        "spell"
            | "spirit"
            | "fn"
            | "def"
            | "function"
            | "class"
            | "this"
            | "self"
            | "null"
            | "nil"
            | "try"
            | "catch"
            | "throw"
            | "macro"
            | "impl"
            | "trait"
            | "where"
    )
}

/// Indica si `text` no puede usarse como identificador (palabra reservada o
/// retirada). Lo consumen el formateador, el generador de bindings y las
/// herramientas que construyen código.
#[must_use]
pub fn is_reserved(text: &str) -> bool {
    keyword(text).is_some() || is_retired(text)
}

fn is_binary_operator(kind: TokenKind) -> bool {
    matches!(
        kind,
        TokenKind::Plus
            | TokenKind::Minus
            | TokenKind::Star
            | TokenKind::Slash
            | TokenKind::Percent
            | TokenKind::DotDot
            | TokenKind::DotDotEq
            | TokenKind::Lt
            | TokenKind::LtEq
            | TokenKind::Gt
            | TokenKind::GtEq
            | TokenKind::EqEq
            | TokenKind::NotEq
            | TokenKind::Is
            | TokenKind::Isnt
            | TokenKind::In
            | TokenKind::And
            | TokenKind::Or
            | TokenKind::As
    )
}

/// Lexea un archivo completo.
#[must_use]
pub fn lex(file: FileId, source: &str) -> Lexed {
    if let Some(diagnostic) = source_diagnostic(file, source) {
        return Lexed {
            tokens: vec![Token {
                kind: TokenKind::Eof,
                span: Span::new(file, 0, 0),
            }],
            diagnostics: vec![diagnostic],
        };
    }
    Lexer::new(file, source).run()
}

fn raw_prefix(rest: &str) -> Option<(usize, usize)> {
    let mut chars = rest.char_indices();
    if chars.next()?.1 != 'r' {
        return None;
    }
    let mut hashes = 0usize;
    let mut quote_at = None;
    for (index, c) in chars {
        match c {
            '#' => hashes += 1,
            '"' => {
                quote_at = Some(index);
                break;
            }
            _ => return None,
        }
    }
    Some((hashes, quote_at?))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn lex(source: &str) -> Lexed {
        super::super::lex(FileId::new(1), source)
    }

    fn kinds(source: &str) -> Vec<TokenKind> {
        lex(source)
            .tokens
            .into_iter()
            .map(|token| token.kind)
            .collect()
    }

    fn significant(source: &str) -> Vec<TokenKind> {
        lex(source).significant().map(|token| token.kind).collect()
    }

    #[test]
    fn simple_indentation() {
        let source = "grimoire\n    bind x = 1\n    if x\n        x\n";
        assert_eq!(
            kinds(source),
            vec![
                TokenKind::Grimoire,
                TokenKind::Newline,
                TokenKind::Indent,
                TokenKind::Bind,
                TokenKind::Ident,
                TokenKind::Eq,
                TokenKind::Int,
                TokenKind::Newline,
                TokenKind::If,
                TokenKind::Ident,
                TokenKind::Newline,
                TokenKind::Indent,
                TokenKind::Ident,
                TokenKind::Newline,
                TokenKind::Dedent,
                TokenKind::Dedent,
                TokenKind::Eof
            ]
        );
    }

    #[test]
    fn blank_and_comment_lines_do_not_indent() {
        let source = "if true\n\n    -- comentario\n    bind x = 1\n";
        assert_eq!(
            significant(source),
            vec![
                TokenKind::If,
                TokenKind::True,
                TokenKind::Indent,
                TokenKind::Bind,
                TokenKind::Ident,
                TokenKind::Eq,
                TokenKind::Int,
                TokenKind::Dedent,
                TokenKind::Eof
            ]
        );
    }

    #[test]
    fn new_and_switch_are_valid_identifiers() {
        let source = "String.new() Bool.switch()";
        let result = lex(source);
        assert!(result.is_clean(), "{:?}", result.diagnostics);
        assert_eq!(
            result
                .significant()
                .map(|token| token.kind)
                .collect::<Vec<_>>(),
            vec![
                TokenKind::Ident,
                TokenKind::Dot,
                TokenKind::Ident,
                TokenKind::LParen,
                TokenKind::RParen,
                TokenKind::Ident,
                TokenKind::Dot,
                TokenKind::Ident,
                TokenKind::LParen,
                TokenKind::RParen,
                TokenKind::Eof
            ]
        );
    }

    #[test]
    fn semicolon_is_a_token_for_array_repeat() {
        let result = lex("[0; 4] [Int; 3]");
        assert!(result.is_clean(), "{:?}", result.diagnostics);
        assert_eq!(
            result
                .significant()
                .map(|token| token.kind)
                .collect::<Vec<_>>(),
            vec![
                TokenKind::LBracket,
                TokenKind::Int,
                TokenKind::Semicolon,
                TokenKind::Int,
                TokenKind::RBracket,
                TokenKind::LBracket,
                TokenKind::Ident,
                TokenKind::Semicolon,
                TokenKind::Int,
                TokenKind::RBracket,
                TokenKind::Eof
            ]
        );
    }

    #[test]
    fn keywords_and_retired_words() {
        let source = "rune Ptr Self abi spell";
        let result = lex(source);
        assert_eq!(
            result
                .significant()
                .map(|token| token.kind)
                .collect::<Vec<_>>(),
            vec![
                TokenKind::Rune,
                TokenKind::Ptr,
                TokenKind::SelfType,
                TokenKind::Abi,
                TokenKind::Ident,
                TokenKind::Eof
            ]
        );
        assert_eq!(result.diagnostics[0].code, "PGS-E1010");
    }

    #[test]
    fn numbers() {
        assert_eq!(
            kinds("42 0xFF 0o755 0b1010 1_000 42_i64 42_usize"),
            vec![
                TokenKind::Int,
                TokenKind::Int,
                TokenKind::Int,
                TokenKind::Int,
                TokenKind::Int,
                TokenKind::Int,
                TokenKind::Int,
                TokenKind::Eof
            ]
        );
        assert_eq!(
            kinds("1.5 1.0e10 2.5_f32"),
            vec![
                TokenKind::Float,
                TokenKind::Float,
                TokenKind::Float,
                TokenKind::Eof
            ]
        );
        assert_eq!(
            kinds("42.is_even()"),
            vec![
                TokenKind::Int,
                TokenKind::Dot,
                TokenKind::Ident,
                TokenKind::LParen,
                TokenKind::RParen,
                TokenKind::Eof
            ]
        );
    }

    #[test]
    fn punctuation_and_at() {
        assert_eq!(
            significant("@ @@ @mut @own -> => .. ..= :: | & ? ;"),
            vec![
                TokenKind::At,
                TokenKind::AtAt,
                TokenKind::AtMut,
                TokenKind::AtOwn,
                TokenKind::Arrow,
                TokenKind::FatArrow,
                TokenKind::DotDot,
                TokenKind::DotDotEq,
                TokenKind::ColonColon,
                TokenKind::Pipe,
                TokenKind::Amp,
                TokenKind::Question,
                TokenKind::Semicolon,
                TokenKind::Eof
            ]
        );
    }

    #[test]
    fn chars() {
        assert_eq!(
            kinds("'a' '\\n' '\\u{1F600}' b'P' b'\\x41'"),
            vec![
                TokenKind::Char,
                TokenKind::Char,
                TokenKind::Char,
                TokenKind::ByteChar,
                TokenKind::ByteChar,
                TokenKind::Eof
            ]
        );
    }

    #[test]
    fn strings_and_interpolation() {
        let result =
            lex("\"hola\" \"a #{name} b\" r\"x\\n\" b\"ok\" c\"C\" \"\"\"multi\nline\"\"\"");
        assert_eq!(
            result
                .significant()
                .map(|token| token.kind)
                .collect::<Vec<_>>(),
            vec![
                TokenKind::String(StringKind::Normal),
                TokenKind::StringStart(StringKind::Normal),
                TokenKind::StringText,
                TokenKind::InterpStart,
                TokenKind::Ident,
                TokenKind::InterpEnd,
                TokenKind::StringText,
                TokenKind::StringEnd,
                TokenKind::String(StringKind::Raw),
                TokenKind::String(StringKind::Byte),
                TokenKind::String(StringKind::C),
                TokenKind::String(StringKind::Triple),
                TokenKind::Eof
            ]
        );
    }

    #[test]
    fn raw_hashes() {
        let result = lex("r#\"a \" b\"#");
        assert_eq!(
            result
                .significant()
                .map(|token| token.kind)
                .collect::<Vec<_>>(),
            vec![TokenKind::String(StringKind::Raw), TokenKind::Eof]
        );
    }

    #[test]
    fn delimiters_allow_newlines_without_indentation_tokens() {
        assert_eq!(
            significant("Map[\n  \"a\": 1,\n  \"b\": 2,\n]"),
            vec![
                TokenKind::Ident,
                TokenKind::LBracket,
                TokenKind::String(StringKind::Normal),
                TokenKind::Colon,
                TokenKind::Int,
                TokenKind::Comma,
                TokenKind::String(StringKind::Normal),
                TokenKind::Colon,
                TokenKind::Int,
                TokenKind::Comma,
                TokenKind::RBracket,
                TokenKind::Eof
            ]
        );
    }

    #[test]
    fn diagnostics() {
        assert_eq!(lex("\u{feff}bind x").diagnostics[0].code, "PGS-E1001");
        assert_eq!(lex("\tbind x").diagnostics[0].code, "PGS-E1002");
        assert_eq!(lex("  bind x").diagnostics[0].code, "PGS-E1003");
        assert_eq!(lex("\"sin cerrar").diagnostics[0].code, "PGS-E1005");
        assert_eq!(lex("'a").diagnostics[0].code, "PGS-E1006");
        assert_eq!(lex("\"\\q\"").diagnostics[0].code, "PGS-E1007");
        assert_eq!(lex("b'é'").diagnostics[0].code, "PGS-E1008");
        assert_eq!(lex("--[[ sin cerrar").diagnostics[0].code, "PGS-E1009");
        assert_eq!(lex("spell").diagnostics[0].code, "PGS-E1010");
        assert_eq!(lex("😀").diagnostics[0].code, "PGS-E1011");
    }

    #[test]
    fn continuation_after_operator() {
        assert_eq!(
            significant("bind x = 1 +\n    2"),
            vec![
                TokenKind::Bind,
                TokenKind::Ident,
                TokenKind::Eq,
                TokenKind::Int,
                TokenKind::Plus,
                TokenKind::Int,
                TokenKind::Eof
            ]
        );
    }

    #[test]
    fn crlf_and_bom_spans() {
        let result = lex("bind x\r\n    1");
        assert!(result.is_clean());
        assert!(
            result
                .tokens
                .iter()
                .any(|token| token.kind == TokenKind::Newline)
        );
    }

    #[test]
    fn no_panic_on_random_utf8() {
        for source in ["", "a", "\u{0}", "😀", "bind x = \"#{😀}\"", "--[[ ]]"] {
            let _ = lex(source);
        }
    }
    #[test]
    fn every_keyword_is_lexed() {
        assert_eq!(
            significant(
                "rune enchanting pact ritual essence scroll summon unveil grimoire foreign curse abi Ptr bind morph sigil relic if elseif else unless match when then for while loop break continue return do and or not is isnt in as true false none some ok err Self"
            ),
            vec![
                TokenKind::Rune,
                TokenKind::Enchanting,
                TokenKind::Pact,
                TokenKind::Ritual,
                TokenKind::Essence,
                TokenKind::Scroll,
                TokenKind::Summon,
                TokenKind::Unveil,
                TokenKind::Grimoire,
                TokenKind::Foreign,
                TokenKind::Curse,
                TokenKind::Abi,
                TokenKind::Ptr,
                TokenKind::Bind,
                TokenKind::Morph,
                TokenKind::Sigil,
                TokenKind::Relic,
                TokenKind::If,
                TokenKind::Elseif,
                TokenKind::Else,
                TokenKind::Unless,
                TokenKind::Match,
                TokenKind::When,
                TokenKind::Then,
                TokenKind::For,
                TokenKind::While,
                TokenKind::Loop,
                TokenKind::Break,
                TokenKind::Continue,
                TokenKind::Return,
                TokenKind::Do,
                TokenKind::And,
                TokenKind::Or,
                TokenKind::Not,
                TokenKind::Is,
                TokenKind::Isnt,
                TokenKind::In,
                TokenKind::As,
                TokenKind::True,
                TokenKind::False,
                TokenKind::None,
                TokenKind::Some,
                TokenKind::Ok,
                TokenKind::Err,
                TokenKind::SelfType,
                TokenKind::Eof,
            ]
        );
    }

    #[test]
    fn unicode_identifiers_and_invalid_chars() {
        let result = lex("ñandú café 变量 _x");
        assert!(result.is_clean());
        assert_eq!(
            result
                .significant()
                .map(|token| token.kind)
                .collect::<Vec<_>>(),
            vec![
                TokenKind::Ident,
                TokenKind::Ident,
                TokenKind::Ident,
                TokenKind::Ident,
                TokenKind::Eof
            ]
        );
        assert_eq!(lex("a😀b").diagnostics[0].code, "PGS-E1011");
    }

    #[test]
    fn invalid_base_digits_are_diagnosed() {
        for source in ["0b102", "0o8", "0x", "0xG"] {
            let lexed = lex(source);
            let errors: Vec<_> = lexed
                .diagnostics
                .iter()
                .filter(|d| d.code == "PGS-E1011")
                .collect();
            assert_eq!(errors.len(), 1, "{source}: {:?}", lexed.diagnostics);
        }
        for source in ["0b1010", "0o755", "0xFF", "0b10_i32", "0x1_f"] {
            let lexed = lex(source);
            assert!(
                lexed.diagnostics.iter().all(|d| d.code != "PGS-E1011"),
                "{source}: {:?}",
                lexed.diagnostics
            );
        }
    }

    #[test]
    fn numeric_suffixes_and_floats() {
        let source = "0xDEAD_BEEF 0o755 0b1010_1010 1_000_000 42_i8 42_I8 42_i16 42_i32 42_i64 42_isize 42_u8 42_u16 42_u32 42_u64 42_usize 2.5_f32 1.0_F64 1e-3";
        let result = lex(source);
        assert!(result.is_clean(), "{:?}", result.diagnostics);
        assert_eq!(
            result
                .significant()
                .filter(|token| token.kind != TokenKind::Eof)
                .count(),
            18
        );
        assert!(
            result
                .tokens
                .iter()
                .any(|token| token.text(source) == "42_isize")
        );
    }

    #[test]
    fn escapes_and_raw_strings() {
        let source = "\"a\\n\\t\\x41\\u{1F600}\\\"\\'\" r\"a\\n\" r#\"a \" b\"# b\"\\x41\" c\"C\\0\" \"\\#{x}\"";
        let result = lex(source);
        assert!(result.is_clean(), "{:?}", result.diagnostics);
        assert_eq!(
            result
                .significant()
                .filter(|token| matches!(token.kind, TokenKind::String(_)))
                .count(),
            6
        );
        assert_eq!(lex("b'\\xFF'").diagnostics.len(), 0);
        assert_eq!(lex("b'é'").diagnostics[0].code, "PGS-E1008");
    }

    #[test]
    fn comments_and_doc_comments() {
        let source = "-- línea\n--[[ bloque ]] \n--- doc\n--! doc interna\n";
        let result = lex(source);
        assert!(result.is_clean());
        let kinds: Vec<_> = result
            .tokens
            .iter()
            .filter_map(|token| match token.kind {
                TokenKind::Comment(kind) => Some(kind),
                _ => None,
            })
            .collect();
        assert_eq!(
            kinds,
            vec![
                CommentKind::Line,
                CommentKind::Block,
                CommentKind::DocOuter,
                CommentKind::DocInner
            ]
        );
        assert!(
            !result
                .significant()
                .any(|token| matches!(token.kind, TokenKind::Indent | TokenKind::Dedent))
        );
    }

    #[test]
    fn indentation_levels_and_dedents() {
        let source = "a\n    b\n        c\n    d\n";
        assert_eq!(
            significant(source),
            vec![
                TokenKind::Ident,
                TokenKind::Indent,
                TokenKind::Ident,
                TokenKind::Indent,
                TokenKind::Ident,
                TokenKind::Dedent,
                TokenKind::Ident,
                TokenKind::Dedent,
                TokenKind::Eof
            ]
        );
        assert_eq!(lex("a\n  b").diagnostics[0].code, "PGS-E1003");
        assert_eq!(lex("a\n      b").diagnostics[0].code, "PGS-E1003");
        assert_eq!(lex("a\n        b\n    c").diagnostics[0].code, "PGS-E1004");
    }

    #[test]
    fn tabs_are_rejected_outside_strings_and_comments() {
        assert_eq!(lex("\tbind x").diagnostics[0].code, "PGS-E1002");
        assert_eq!(lex("bind x\t+ 1").diagnostics[0].code, "PGS-E1002");
        assert!(lex("\"a\tb\"").is_clean());
        assert!(lex("-- a\tb").is_clean());
    }

    #[test]
    fn closing_delimiter_mid_line_does_not_fake_indentation() {
        let source = "bind x = Map[\n    \"a\": 1,\n    ] + 1\n";
        let kinds = significant(source);
        assert!(!kinds.contains(&TokenKind::Dedent));
        assert!(!kinds.contains(&TokenKind::Indent));
        assert!(kinds.contains(&TokenKind::Plus));
        assert_eq!(lex(source).diagnostics.len(), 0);
    }

    #[test]
    fn token_spans_and_text_are_exact() {
        let source = "bind x = \"hola\"\n";
        let result = lex(source);
        let string = result
            .tokens
            .iter()
            .find(|token| matches!(token.kind, TokenKind::String(StringKind::Normal)))
            .unwrap();
        assert_eq!(string.text(source), "\"hola\"");
        assert_eq!(string.span.start, 9);
        assert_eq!(string.span.end, 15);
    }

    #[test]
    fn interpolation_spans_are_absolute() {
        let source = "\"x #{name} y\"";
        let result = lex(source);
        assert!(result.is_clean());
        let name = result
            .tokens
            .iter()
            .find(|token| token.kind == TokenKind::Ident && token.text(source) == "name")
            .unwrap();
        assert_eq!(name.span.start, 5);
        assert_eq!(name.span.end, 9);
    }

    #[test]
    fn empty_and_newline_only_inputs_end_with_eof() {
        for source in ["", "\n", "\n\n", "   \n"] {
            let result = lex(source);
            assert_eq!(result.tokens.last().unwrap().kind, TokenKind::Eof);
            assert!(result.is_clean());
        }
    }
    #[test]
    fn triple_strings_keep_newlines_without_indentation_tokens() {
        let source = "\"\"\"uno\ndos\n    tres\"\"\"";
        let result = lex(source);
        assert!(result.is_clean());
        assert_eq!(
            result
                .significant()
                .map(|token| token.kind)
                .collect::<Vec<_>>(),
            vec![TokenKind::String(StringKind::Triple), TokenKind::Eof]
        );
        assert!(
            !result
                .tokens
                .iter()
                .any(|token| matches!(token.kind, TokenKind::Indent | TokenKind::Dedent))
        );
    }

    #[test]
    fn block_comments_do_not_emit_structure() {
        let source = "bind x = 1\n--[[ bloque\ncon varias líneas\n]]\nbind y = 2\n";
        let result = lex(source);
        assert!(result.is_clean());
        assert_eq!(
            result
                .significant()
                .filter(|token| matches!(token.kind, TokenKind::Bind))
                .count(),
            2
        );
        assert!(
            !result
                .tokens
                .iter()
                .any(|token| matches!(token.kind, TokenKind::Indent | TokenKind::Dedent))
        );
    }

    #[test]
    fn escaped_interpolation_is_literal_text() {
        let result = lex("\"\\#{x}\"");
        assert!(result.is_clean());
        assert_eq!(
            result
                .significant()
                .map(|token| token.kind)
                .collect::<Vec<_>>(),
            vec![TokenKind::String(StringKind::Normal), TokenKind::Eof]
        );
    }

    #[test]
    fn nested_interpolation_expression() {
        let source = "\"#{ { \"a\": 1 } }\"";
        let result = lex(source);
        assert!(result.is_clean(), "{:?}", result.diagnostics);
        assert_eq!(
            result
                .significant()
                .map(|token| token.kind)
                .collect::<Vec<_>>(),
            vec![
                TokenKind::StringStart(StringKind::Normal),
                TokenKind::InterpStart,
                TokenKind::LBrace,
                TokenKind::String(StringKind::Normal),
                TokenKind::Colon,
                TokenKind::Int,
                TokenKind::RBrace,
                TokenKind::InterpEnd,
                TokenKind::StringEnd,
                TokenKind::Eof
            ]
        );
    }

    #[test]
    fn raw_byte_and_c_strings_never_interpolate() {
        for (source, kind) in [
            ("r\"#{x}\"", StringKind::Raw),
            ("b\"#{x}\"", StringKind::Byte),
            ("c\"#{x}\"", StringKind::C),
        ] {
            let result = lex(source);
            assert!(result.is_clean(), "{source}: {:?}", result.diagnostics);
            assert_eq!(
                result
                    .significant()
                    .map(|token| token.kind)
                    .collect::<Vec<_>>(),
                vec![TokenKind::String(kind), TokenKind::Eof]
            );
        }
    }

    #[test]
    fn eof_closes_open_indentation() {
        let result = lex("a\n    b");
        let kinds: Vec<_> = result.tokens.iter().map(|token| token.kind).collect();
        assert_eq!(kinds[kinds.len() - 2], TokenKind::Dedent);
        assert_eq!(kinds[kinds.len() - 1], TokenKind::Eof);
    }

    #[test]
    fn bom_only_and_unclosed_constructs_do_not_panic() {
        assert_eq!(lex("\u{feff}").diagnostics[0].code, "PGS-E1001");
        assert_eq!(lex("--[[\n").diagnostics[0].code, "PGS-E1009");
        assert_eq!(lex("\"\"\"uno\ndos").diagnostics[0].code, "PGS-E1005");
        assert_eq!(lex("b'").diagnostics[0].code, "PGS-E1006");
        assert_eq!(lex("\"\\xZZ\"").diagnostics[0].code, "PGS-E1007");
    }

    #[test]
    fn at_variants_and_ampersand_are_separate() {
        assert_eq!(
            significant("@mutx @own @mut @own @@ &mut"),
            vec![
                TokenKind::At,
                TokenKind::Ident,
                TokenKind::AtOwn,
                TokenKind::AtMut,
                TokenKind::AtOwn,
                TokenKind::AtAt,
                TokenKind::Amp,
                TokenKind::Ident,
                TokenKind::Eof
            ]
        );
    }
    #[test]
    fn all_punctuation_is_lexed() {
        assert_eq!(
            significant("()[]{} , ; : :: . .. ..= -> => = == != < <= > >= + - * / % ? | & ! @@"),
            vec![
                TokenKind::LParen,
                TokenKind::RParen,
                TokenKind::LBracket,
                TokenKind::RBracket,
                TokenKind::LBrace,
                TokenKind::RBrace,
                TokenKind::Comma,
                TokenKind::Semicolon,
                TokenKind::Colon,
                TokenKind::ColonColon,
                TokenKind::Dot,
                TokenKind::DotDot,
                TokenKind::DotDotEq,
                TokenKind::Arrow,
                TokenKind::FatArrow,
                TokenKind::Eq,
                TokenKind::EqEq,
                TokenKind::NotEq,
                TokenKind::Lt,
                TokenKind::LtEq,
                TokenKind::Gt,
                TokenKind::GtEq,
                TokenKind::Plus,
                TokenKind::Minus,
                TokenKind::Star,
                TokenKind::Slash,
                TokenKind::Percent,
                TokenKind::Question,
                TokenKind::Pipe,
                TokenKind::Amp,
                TokenKind::Bang,
                TokenKind::AtAt,
                TokenKind::Eof,
            ]
        );
    }

    #[test]
    fn indentation_widths_follow_the_four_space_rule() {
        for width in [0usize, 4, 8] {
            let source = format!("a\n{}b\n", " ".repeat(width));
            let result = lex(&source);
            assert!(result.is_clean(), "width {width}: {:?}", result.diagnostics);
        }
        for width in [1usize, 2, 3, 5, 6, 7] {
            let source = format!("a\n{}b\n", " ".repeat(width));
            assert_eq!(
                lex(&source).diagnostics[0].code,
                "PGS-E1003",
                "width {width}"
            );
        }
    }

    #[test]
    fn random_soup_always_terminates_with_eof() {
        let alphabet = [
            'a', 'Z', '_', '0', '9', ' ', '\t', '\n', '\r', '"', '\'', '\\', '#', '{', '}', '[',
            ']', '(', ')', '@', '-', '.', ':', '/', '=', 'é', '😀', '\u{feff}',
        ];
        let mut seed = 0x1234_5678u32;
        for _ in 0..500 {
            let mut source = String::new();
            let len = (seed % 24) as usize;
            for _ in 0..len {
                seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
                source.push(alphabet[(seed as usize) % alphabet.len()]);
            }
            let result = lex(&source);
            assert_eq!(result.tokens.last().unwrap().kind, TokenKind::Eof);
        }
    }
    #[test]
    fn code_after_a_block_comment_on_the_same_line_keeps_newline() {
        let source = "--[[\n]] bind x = 1\nbind y = 2\n";
        let result = lex(source);
        assert!(result.is_clean());
        assert_eq!(
            result
                .significant()
                .filter(|token| token.kind == TokenKind::Bind)
                .count(),
            2
        );
        assert!(
            result
                .tokens
                .iter()
                .filter(|token| token.kind == TokenKind::Newline)
                .count()
                >= 1
        );
    }

    #[test]
    fn numeric_suffixes_choose_int_or_float() {
        assert_eq!(significant("42f32"), vec![TokenKind::Float, TokenKind::Eof]);
        assert_eq!(significant("42_i64"), vec![TokenKind::Int, TokenKind::Eof]);
        assert_eq!(
            significant("1.0_f32"),
            vec![TokenKind::Float, TokenKind::Eof]
        );
        assert_eq!(
            significant("1..2"),
            vec![
                TokenKind::Int,
                TokenKind::DotDot,
                TokenKind::Int,
                TokenKind::Eof
            ]
        );
    }

    #[test]
    fn base_literals_require_at_least_one_digit() {
        for source in ["0x", "0x_", "0b", "0b_", "0o", "0o_"] {
            let result = lex(source);
            assert!(
                result
                    .diagnostics
                    .iter()
                    .any(|diagnostic| diagnostic.code == "PGS-E1011"),
                "{source}: {:?}",
                result.diagnostics
            );
        }
    }

    #[test]
    fn malformed_numeric_literals_are_diagnosed() {
        for source in ["1e", "1e+", "1.", "1.0_i64"] {
            let result = lex(source);
            assert!(
                result
                    .diagnostics
                    .iter()
                    .any(|diagnostic| diagnostic.code == "PGS-E1011"),
                "{source}: {:?}",
                result.diagnostics
            );
        }
    }
}
