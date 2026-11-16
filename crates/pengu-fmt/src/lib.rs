#![forbid(unsafe_code)]
//! Formateador determinista de `PenguScript`.
//!
//! La indentación es significativa, así que el formateador **no** reconstruye
//! bloques: trabaja sobre la secuencia de tokens del lexer real y solo normaliza
//! los huecos entre tokens. Antes de devolver el resultado verifica que la
//! secuencia de tokens (tipo y lexema) es idéntica, de modo que un cambio de
//! semántica es imposible por construcción.

use pengu_diag::Diagnostic;
use pengu_span::FileId;
use pengu_syntax::{TokenKind, lex};

/// Error de formato, con el código `PGS-E1805` de §18.8.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FormatError {
    /// Código de diagnóstico.
    pub code: &'static str,
    /// Mensaje para el usuario.
    pub message: String,
    /// Ayuda accionable.
    pub help: Option<String>,
}

impl FormatError {
    fn new(message: impl Into<String>) -> Self {
        Self {
            code: "PGS-E1805",
            message: message.into(),
            help: Some("corrige los errores de sintaxis antes de formatear".to_owned()),
        }
    }
}

impl std::fmt::Display for FormatError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "{}: {}", self.code, self.message)?;
        if let Some(help) = &self.help {
            write!(formatter, " ({help})")?;
        }
        Ok(())
    }
}

impl std::error::Error for FormatError {}

/// Diferencia de formato en una línea (1-based).
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Difference {
    /// Línea del archivo original.
    pub line: usize,
    /// Texto actual.
    pub current: String,
    /// Texto que produciría el formateador.
    pub formatted: String,
}

/// Formatea un archivo completo.
///
/// # Errors
///
/// Devuelve [`FormatError`] si el archivo no lexa o si el resultado cambiara la
/// secuencia de tokens.
pub fn format_source(source: &str) -> Result<String, FormatError> {
    let lexed = lex(FileId::new(0), source);
    if let Some(diagnostic) = lexed.diagnostics.first() {
        return Err(FormatError::new(diagnostic_summary(diagnostic)));
    }
    let formatted = rebuild(source, &lexed.tokens);
    verify(source, &formatted)?;
    Ok(formatted)
}

/// Comprueba si el texto ya está formateado.
///
/// # Errors
///
/// Igual que [`format_source`].
pub fn is_formatted(source: &str) -> Result<bool, FormatError> {
    Ok(format_source(source)? == source)
}

/// Diferencias entre el texto actual y su formato canónico.
///
/// Compara alineando el prefijo y el sufijo comunes: el formateador nunca
/// reordena líneas, así que las diferencias reales están en el tramo central.
///
/// # Errors
///
/// Igual que [`format_source`].
pub fn differences(source: &str) -> Result<Vec<Difference>, FormatError> {
    let formatted = format_source(source)?;
    if formatted == source {
        return Ok(Vec::new());
    }
    let current: Vec<&str> = source.lines().collect();
    let expected: Vec<&str> = formatted.lines().collect();
    let prefix = current
        .iter()
        .zip(&expected)
        .take_while(|(left, right)| left == right)
        .count();
    let suffix = current
        .iter()
        .rev()
        .zip(expected.iter().rev())
        .take_while(|(left, right)| left == right)
        .count()
        .min(current.len() - prefix)
        .min(expected.len() - prefix);
    let middle_current = &current[prefix..current.len() - suffix];
    let middle_expected = &expected[prefix..expected.len() - suffix];
    let mut result = Vec::new();
    for index in 0..middle_current.len().max(middle_expected.len()) {
        let left = middle_current.get(index).copied().unwrap_or("");
        let right = middle_expected.get(index).copied().unwrap_or("");
        if left != right {
            result.push(Difference {
                line: prefix + index + 1,
                current: left.to_owned(),
                formatted: right.to_owned(),
            });
        }
    }
    Ok(result)
}

fn diagnostic_summary(diagnostic: &Diagnostic) -> String {
    format!("no se puede formatear: {}", diagnostic.message)
}

/// Reconstruye el archivo desde la secuencia de tokens.
fn rebuild(source: &str, tokens: &[pengu_syntax::Token]) -> String {
    let mut out = String::with_capacity(source.len());
    let mut previous_end = 0usize;
    let mut previous_kind: Option<TokenKind> = None;
    for token in tokens {
        match token.kind {
            TokenKind::Indent | TokenKind::Dedent | TokenKind::Newline | TokenKind::Eof => continue,
            _ => {}
        }
        let gap = &source[previous_end..token.span.start as usize];
        match previous_kind {
            None => out.push_str(gap.trim_start()),
            Some(previous) => {
                if let Some(index) = gap.rfind('\n') {
                    let newlines = gap.matches('\n').count().min(2);
                    for _ in 0..newlines {
                        out.push('\n');
                    }
                    out.push_str(&gap[index + 1..]);
                } else {
                    out.push_str(&separator(previous, token.kind, gap));
                }
            }
        }
        out.push_str(token.text(source));
        previous_end = token.span.end as usize;
        previous_kind = Some(token.kind);
    }
    let trimmed = out.trim_end();
    let mut result = String::with_capacity(trimmed.len() + 1);
    result.push_str(trimmed);
    result.push('\n');
    result
}

fn separator(previous: TokenKind, current: TokenKind, gap: &str) -> String {
    if closes_tightly(previous) || opens_tightly(current) {
        return String::new();
    }
    if current == TokenKind::Colon {
        return String::new();
    }
    if previous == TokenKind::Colon || previous == TokenKind::Comma {
        return " ".to_owned();
    }
    if matches!(
        current,
        TokenKind::LParen | TokenKind::LBracket | TokenKind::LBrace
    ) && matches!(
        previous,
        TokenKind::Ident
            | TokenKind::RParen
            | TokenKind::RBracket
            | TokenKind::Some
            | TokenKind::Ok
            | TokenKind::Err
            | TokenKind::SelfType
    ) {
        return String::new();
    }
    gap.to_owned()
}

fn closes_tightly(kind: TokenKind) -> bool {
    matches!(
        kind,
        TokenKind::LParen
            | TokenKind::LBracket
            | TokenKind::Dot
            | TokenKind::ColonColon
            | TokenKind::AtAt
    )
}

fn opens_tightly(kind: TokenKind) -> bool {
    matches!(
        kind,
        TokenKind::RParen
            | TokenKind::RBracket
            | TokenKind::Comma
            | TokenKind::Dot
            | TokenKind::ColonColon
            | TokenKind::Semicolon
    )
}

fn verify(before: &str, after: &str) -> Result<(), FormatError> {
    let left: Vec<_> = lex(FileId::new(0), before)
        .tokens
        .iter()
        .map(|token| (token.kind, token.text(before).to_owned()))
        .collect();
    let right: Vec<_> = lex(FileId::new(0), after)
        .tokens
        .iter()
        .map(|token| (token.kind, token.text(after).to_owned()))
        .collect();
    if left == right {
        return Ok(());
    }
    Err(FormatError {
        code: "PGS-E1805",
        message: "el formateo cambiaría la secuencia de tokens; no se aplica".to_owned(),
        help: Some("reporta este caso: es un fallo del formateador".to_owned()),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pretty(source: &str) -> String {
        format_source(source).expect("formatea")
    }

    #[test]
    fn normaliza_espacios_alrededor_de_puntos_y_parentesis() {
        let source = "f = ( a : Int , b :Int ) -> Int\n    g ( a , b )\n";
        let formatted = pretty(source);
        assert_eq!(formatted, "f = (a: Int, b: Int) -> Int\n    g(a, b)\n");
    }

    #[test]
    fn normaliza_indentacion_y_espacios_finales() {
        let source = "f = () -> Int   \n    1  \n\n\n\ngrimoire\n    print(f())\n";
        let formatted = pretty(source);
        assert_eq!(
            formatted,
            "f = () -> Int\n    1\n\ngrimoire\n    print(f())\n"
        );
    }

    #[test]
    fn no_toca_el_interior_de_strings_ni_comentarios() {
        let source = "x = \"a:b, c ( d ) #{e}\"\n-- comentario:   raro (  x  )\n";
        assert_eq!(pretty(source), source);
    }

    #[test]
    fn no_toca_comentarios_de_bloque() {
        let source = "--[[\n  texto   con   espacios\n]]\ny = 1\n";
        assert_eq!(pretty(source), source);
    }

    #[test]
    fn es_idempotente() {
        let source = "rune   Punto\n    x:Int\n    y :Int\n";
        let once = pretty(source);
        let twice = pretty(&once);
        assert_eq!(once, twice);
    }

    #[test]
    fn conserva_la_secuencia_de_tokens() {
        let source = "rune Caja[T]\n    valor: T\n\nf = [T](x: T) -> Caja[T]\n    Caja(valor: x)\n";
        let formatted = pretty(source);
        let before: Vec<_> = lex(FileId::new(0), source)
            .tokens
            .iter()
            .map(|token| token.kind)
            .collect();
        let after: Vec<_> = lex(FileId::new(0), &formatted)
            .tokens
            .iter()
            .map(|token| token.kind)
            .collect();
        assert_eq!(before, after);
    }

    #[test]
    fn mantiene_rutas_de_modulo_pegadas() {
        let source = "summon std :: ffi\n";
        assert_eq!(pretty(source), "summon std::ffi\n");
    }

    #[test]
    fn la_stdlib_esta_formateada() {
        let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../std");
        let mut checked = 0usize;
        for entry in std::fs::read_dir(dir).expect("std") {
            let path = entry.expect("entrada").path();
            if path.extension().and_then(|value| value.to_str()) != Some("pengu") {
                continue;
            }
            let source = std::fs::read_to_string(&path).expect("lee");
            let formatted = pretty(&source);
            assert_eq!(formatted, source, "{} no está formateado", path.display());
            checked += 1;
        }
        assert!(
            checked > 20,
            "se esperaban los módulos de std, se vieron {checked}"
        );
    }

    #[test]
    fn informa_del_error_de_sintaxis() {
        let error = format_source("\tx = 1\n").expect_err("tab no permitido");
        assert_eq!(error.code, "PGS-E1805");
        assert!(error.message.contains("no se puede formatear"));
    }

    #[test]
    fn encuentra_diferencias_con_linea() {
        let diffs = differences("f = () -> Int\n    1   \n").expect("diferencias");
        assert_eq!(diffs.len(), 1);
        assert_eq!(diffs[0].line, 2);
        assert_eq!(diffs[0].formatted, "    1");
    }

    #[test]
    fn reconoce_texto_ya_formateado() {
        assert!(is_formatted("f = () -> Int\n    1\n").expect("formateado"));
        assert!(!is_formatted("f = () -> Int\n    1  \n").expect("no formateado"));
    }
}
