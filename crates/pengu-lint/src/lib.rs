#![forbid(unsafe_code)]
//! Lints de `PenguScript` (§18.5 de `docs/LANGUAGE.md`).
//!
//! Los lints de estructura (control de flujo, sombreado, imports) se calculan
//! con un análisis por líneas sobre la indentación significativa del lenguaje;
//! los de nombres usan el AST. Se silencian desde la CLI (`--allow <código>`),
//! nunca con atributos en el código.

use std::collections::{BTreeMap, BTreeSet};

use pengu_diag::{Diagnostic, Severity};
use pengu_span::{DUMMY_SPAN, FileId, Span};
use pengu_syntax::parse_program;

/// Nivel con el que se emite un lint.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Level {
    /// No se emite.
    Allow,
    /// Se emite como advertencia.
    Warn,
    /// Se emite como error (útil en CI).
    Deny,
}

/// Catálogo de lints: código, nombre, descripción y nivel por defecto.
#[derive(Clone, Copy, Debug)]
pub struct LintInfo {
    /// Código estable `PGS-Wxxxx`.
    pub code: &'static str,
    /// Nombre corto para `--allow`.
    pub name: &'static str,
    /// Qué detecta.
    pub description: &'static str,
    /// Nivel por defecto.
    pub default: Level,
}

const LINTS: &[LintInfo] = &[
    LintInfo {
        code: "PGS-W1101",
        name: "unused-binding",
        description: "un `bind`/`morph`/`for` no se vuelve a usar",
        default: Level::Warn,
    },
    LintInfo {
        code: "PGS-W1102",
        name: "shadowed-binding",
        description: "un nombre local tapa otro del mismo bloque o de un bloque exterior",
        default: Level::Warn,
    },
    LintInfo {
        code: "PGS-W1201",
        name: "redundant-comparison",
        description: "comparación redundante con `true`/`false`",
        default: Level::Warn,
    },
    LintInfo {
        code: "PGS-W1301",
        name: "if-chain",
        description: "una cadena de `if`/`elseif` que se lee mejor como `match`",
        default: Level::Warn,
    },
    LintInfo {
        code: "PGS-W1501",
        name: "panic-in-production",
        description: "`panic(...)`/`fail(...)` fuera de un test o de la stdlib",
        default: Level::Warn,
    },
    LintInfo {
        code: "PGS-W2001",
        name: "unused-import",
        description: "`summon` cuyo nombre no se usa",
        default: Level::Warn,
    },
    LintInfo {
        code: "PGS-W6001",
        name: "unreachable",
        description: "sentencia inalcanzable tras `return`/`break`/`continue`",
        default: Level::Warn,
    },
    LintInfo {
        code: "PGS-W6002",
        name: "constant-loop",
        description: "bucle con condición constante",
        default: Level::Warn,
    },
    LintInfo {
        code: "PGS-W9001",
        name: "duplicate-arm",
        description: "dos brazos de `match` con el mismo patrón",
        default: Level::Warn,
    },
    LintInfo {
        code: "PGS-W1001",
        name: "naming",
        description: "nombre fuera de la convención (funciones snake_case, tipos CamelCase, sigil MAYÚSCULAS)",
        default: Level::Warn,
    },
];

/// Catálogo completo.
#[must_use]
pub fn lints() -> &'static [LintInfo] {
    LINTS
}

/// Busca un lint por código o por nombre.
#[must_use]
pub fn lint_info(key: &str) -> Option<&'static LintInfo> {
    LINTS
        .iter()
        .find(|info| info.code.eq_ignore_ascii_case(key) || info.name == key)
}

/// Configuración de niveles por código.
#[derive(Clone, Debug, Default)]
pub struct LintConfig {
    levels: BTreeMap<&'static str, Level>,
}

impl LintConfig {
    /// Configuración por defecto (todo según el catálogo).
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Fija el nivel de un lint; devuelve `false` si el código no existe.
    pub fn set(&mut self, key: &str, level: Level) -> bool {
        match lint_info(key) {
            Some(info) => {
                self.levels.insert(info.code, level);
                true
            }
            None => false,
        }
    }

    /// Nivel efectivo de un lint.
    #[must_use]
    pub fn level(&self, code: &str) -> Level {
        if let Some(level) = self.levels.get(code) {
            return *level;
        }
        LINTS
            .iter()
            .find(|info| info.code == code)
            .map_or(Level::Allow, |info| info.default)
    }
}

/// Resultado de un análisis de lints.
#[derive(Clone, Debug, Default)]
pub struct Report {
    /// Diagnósticos ordenados por posición.
    pub diagnostics: Vec<Diagnostic>,
}

impl Report {
    /// `true` si hay algún error (lint en nivel `deny`).
    #[must_use]
    pub fn has_errors(&self) -> bool {
        self.diagnostics
            .iter()
            .any(|diagnostic| diagnostic.severity == Severity::Error)
    }
}

/// Ejecuta todos los lints sobre un archivo.
#[must_use]
pub fn lint(source: &str, file: FileId, config: &LintConfig) -> Report {
    lint_with(source, file, config, pengu_std::is_std_file(file))
}

/// Ejecuta los lints indicando explícitamente si el archivo es de la stdlib.
#[must_use]
pub fn lint_with(source: &str, file: FileId, config: &LintConfig, is_std: bool) -> Report {
    let lines = Lines::new(source);
    let mut report = Report::default();
    lint_imports(&lines, config, file, &mut report);
    lint_bindings(&lines, config, file, &mut report);
    lint_control_flow(&lines, config, file, &mut report);
    lint_panics(&lines, config, file, &mut report, is_std);
    lint_naming(source, config, file, &mut report);
    report
        .diagnostics
        .sort_by_key(|diagnostic| (diagnostic.primary.start, diagnostic.code));
    report
}

/// Línea con su rango y su indentación.
struct Line<'a> {
    start: u32,
    end: u32,
    indent: usize,
    text: &'a str,
}

struct Lines<'a> {
    lines: Vec<Line<'a>>,
}

impl<'a> Lines<'a> {
    fn new(source: &'a str) -> Self {
        let mut lines = Vec::new();
        let mut offset = 0u32;
        for (index, raw) in source.split_inclusive('\n').enumerate() {
            let text = raw.trim_end_matches(['\n', '\r']);
            let indent = text.len() - text.trim_start_matches(' ').len();
            let _ = index;
            lines.push(Line {
                start: offset,
                end: offset + u32::try_from(text.len()).unwrap_or(0),
                indent,
                text,
            });
            offset += u32::try_from(raw.len()).unwrap_or(0);
        }
        Self { lines }
    }

    fn span(&self, index: usize) -> Span {
        match self.lines.get(index) {
            Some(line) => Span::new(
                FileId::new(0),
                line.start + u32::try_from(line.indent).unwrap_or(0),
                line.end,
            ),
            None => DUMMY_SPAN,
        }
    }
}

fn push(
    report: &mut Report,
    config: &LintConfig,
    code: &'static str,
    message: String,
    span: Span,
    help: Option<String>,
) {
    let level = config.level(code);
    if level == Level::Allow {
        return;
    }
    let severity = match level {
        Level::Deny => Severity::Error,
        _ => Severity::Warning,
    };
    let mut diagnostic = Diagnostic::new(code, severity, message, span);
    diagnostic.help = help;
    report.diagnostics.push(diagnostic);
}

fn lint_imports(lines: &Lines<'_>, config: &LintConfig, _file: FileId, report: &mut Report) {
    for (index, line) in lines.lines.iter().enumerate() {
        let trimmed = line.text.trim_start();
        let Some(rest) = trimmed.strip_prefix("summon ") else {
            continue;
        };
        let name = rest
            .split([' ', ':'])
            .rfind(|part| !part.is_empty())
            .unwrap_or("")
            .trim();
        if name.is_empty() || name == "as" {
            continue;
        }
        let needle = name;
        let used = lines
            .lines
            .iter()
            .enumerate()
            .any(|(other, candidate)| other != index && contains_word(candidate.text, needle));
        if !used {
            push(
                report,
                config,
                "PGS-W2001",
                format!("el import `{name}` no se usa"),
                lines.span(index),
                Some("quita el `summon` o usa el nombre".to_owned()),
            );
        }
    }
}

fn lint_bindings(lines: &Lines<'_>, config: &LintConfig, _file: FileId, report: &mut Report) {
    let ranges = function_ranges(lines);
    for (index, line) in lines.lines.iter().enumerate() {
        let Some((name, is_for)) = declared_name(line.text.trim_start()) else {
            continue;
        };
        let Some(&(first, last)) = ranges
            .iter()
            .find(|(first, last)| index >= *first && index <= *last)
        else {
            continue;
        };
        let declared_before = lines.lines[first..index].iter().any(|candidate| {
            declared_name(candidate.text.trim_start())
                .is_some_and(|(other, _)| other == name && candidate.indent < line.indent)
        });
        if declared_before {
            push(
                report,
                config,
                "PGS-W1102",
                format!("`{name}` tapa un binding anterior"),
                lines.span(index),
                Some(format!("renombra uno de los dos `{name}`")),
            );
            continue;
        }
        let used = lines.lines[first..=last]
            .iter()
            .enumerate()
            .any(|(offset, candidate)| {
                first + offset != index && contains_word(candidate.text, name)
            });
        if !used && !is_for && !name.starts_with('_') {
            push(
                report,
                config,
                "PGS-W1101",
                format!("el binding `{name}` no se usa"),
                lines.span(index),
                Some("elimínalo o usa `_`".to_owned()),
            );
        }
    }
}

/// Rangos de líneas de cada función de nivel superior.
fn function_ranges(lines: &Lines<'_>) -> Vec<(usize, usize)> {
    let mut starts = Vec::new();
    for (index, line) in lines.lines.iter().enumerate() {
        if line.indent == 0
            && !line.text.trim().is_empty()
            && (line.text.contains(" = ") || line.text.contains("=("))
        {
            starts.push(index);
        }
    }
    let mut ranges = Vec::new();
    for (position, start) in starts.iter().enumerate() {
        let end = starts
            .get(position + 1)
            .map_or(lines.lines.len(), |next| *next);
        ranges.push((*start, end.saturating_sub(1)));
    }
    ranges
}

fn declared_name(trimmed: &str) -> Option<(&str, bool)> {
    for prefix in ["bind ", "morph "] {
        if let Some(rest) = trimmed.strip_prefix(prefix) {
            return first_identifier(rest).map(|name| (name, false));
        }
    }
    if let Some(rest) = trimmed.strip_prefix("for ") {
        if let Some((name, _)) = rest.split_once(" in ") {
            return first_identifier(name).map(|name| (name, true));
        }
    }
    None
}

fn first_identifier(text: &str) -> Option<&str> {
    let end = text
        .char_indices()
        .find(|(_, character)| {
            !(character.is_alphanumeric() || *character == '_' || *character == '@')
        })
        .map_or(text.len(), |(index, _)| index);
    let name = &text[..end];
    if name.is_empty() { None } else { Some(name) }
}

fn lint_control_flow(lines: &Lines<'_>, config: &LintConfig, _file: FileId, report: &mut Report) {
    for (index, line) in lines.lines.iter().enumerate() {
        let trimmed = line.text.trim();
        if trimmed == "while true do" || trimmed == "while false do" {
            push(
                report,
                config,
                "PGS-W6002",
                format!("condición de bucle constante (`{trimmed}`)"),
                lines.span(index),
                Some("usa `loop` para un bucle infinito o una condición real".to_owned()),
            );
        }
        let jumps = trimmed == "return"
            || trimmed == "break"
            || trimmed == "continue"
            || trimmed.starts_with("return ")
            || trimmed.starts_with("break ")
            || trimmed.starts_with("continue ");
        if jumps {
            if let Some(next) = lines.lines.get(index + 1) {
                if !next.text.trim().is_empty() && next.indent >= line.indent {
                    push(
                        report,
                        config,
                        "PGS-W6001",
                        "sentencia inalcanzable después de un salto".to_owned(),
                        lines.span(index + 1),
                        Some("quítala o muévela antes del salto".to_owned()),
                    );
                }
            }
        }
        if trimmed.contains("== true") || trimmed.contains("!= false") {
            push(
                report,
                config,
                "PGS-W1201",
                "comparación redundante con un booleano".to_owned(),
                lines.span(index),
                Some("usa el valor directamente".to_owned()),
            );
        }
        if trimmed.contains("== false") || trimmed.contains("!= true") {
            push(
                report,
                config,
                "PGS-W1201",
                "comparación redundante con un booleano".to_owned(),
                lines.span(index),
                Some("niega el valor con `not`".to_owned()),
            );
        }
    }
    lint_if_chains(lines, config, report);
    lint_match_arms(lines, config, report);
}

fn lint_if_chains(lines: &Lines<'_>, config: &LintConfig, report: &mut Report) {
    let mut index = 0;
    while index < lines.lines.len() {
        let line = &lines.lines[index];
        let trimmed = line.text.trim();
        let Some((scrutinee, _)) = trimmed
            .strip_prefix("if ")
            .and_then(|rest| rest.split_once(" == "))
        else {
            index += 1;
            continue;
        };
        let mut arms = 1;
        let mut cursor = index + 1;
        while let Some(candidate) = lines.lines.get(cursor) {
            let text = candidate.text.trim();
            if !text.starts_with("elseif ") {
                break;
            }
            if text
                .strip_prefix("elseif ")
                .and_then(|rest| rest.split_once(" == "))
                .is_some_and(|(other, _)| other.trim() == scrutinee.trim())
            {
                arms += 1;
            }
            cursor += 1;
        }
        if arms >= 2 {
            push(
                report,
                config,
                "PGS-W1301",
                format!(
                    "cadena de {arms} comparaciones sobre `{}`; se lee mejor como `match`",
                    scrutinee.trim()
                ),
                lines.span(index),
                Some("usa `match` con brazos `when`".to_owned()),
            );
        }
        index += 1;
    }
}

fn lint_match_arms(lines: &Lines<'_>, config: &LintConfig, report: &mut Report) {
    let mut index = 0;
    while index < lines.lines.len() {
        if lines.lines[index].text.trim() != "match"
            && !lines.lines[index].text.trim().starts_with("match ")
        {
            index += 1;
            continue;
        }
        let base = lines.lines[index].indent;
        let mut seen = BTreeSet::new();
        let mut cursor = index + 1;
        while let Some(candidate) = lines.lines.get(cursor) {
            if candidate.indent <= base && !candidate.text.trim().is_empty() {
                break;
            }
            if candidate.text.trim().starts_with("match ") {
                break;
            }
            if let Some(pattern) = candidate.text.trim().strip_prefix("when ") {
                let pattern = pattern
                    .split(" then")
                    .next()
                    .unwrap_or(pattern)
                    .trim()
                    .to_owned();
                if !seen.insert(pattern.clone()) {
                    push(
                        report,
                        config,
                        "PGS-W9001",
                        format!("el brazo `when {pattern}` nunca se alcanza: ya hay uno igual"),
                        lines.span(cursor),
                        Some("quita el brazo duplicado".to_owned()),
                    );
                }
            }
            cursor += 1;
        }
        index = cursor;
    }
}

fn lint_panics(
    lines: &Lines<'_>,
    config: &LintConfig,
    _file: FileId,
    report: &mut Report,
    is_std: bool,
) {
    if is_std {
        return;
    }
    let mut pending_test = false;
    let mut in_test = false;
    for (index, line) in lines.lines.iter().enumerate() {
        if line.indent == 0 && !line.text.trim().is_empty() {
            let declaration = line.text.contains(" = ") || line.text.contains("=(");
            if declaration {
                in_test = pending_test;
            } else {
                in_test = false;
            }
            pending_test = false;
        }
        if line.text.trim() == "@@test" {
            pending_test = true;
            continue;
        }
        if in_test {
            continue;
        }
        if line.text.contains("panic(") || line.text.contains("fail(") {
            push(
                report,
                config,
                "PGS-W1501",
                "`panic`/`fail` en código de producción".to_owned(),
                lines.span(index),
                Some("devuelve un `Result` o valida antes de fallar".to_owned()),
            );
        }
    }
}

fn lint_naming(source: &str, config: &LintConfig, file: FileId, report: &mut Report) {
    let parsed = parse_program(file, source);
    let Some(program) = parsed.program else {
        return;
    };
    for item in &program.items {
        let pengu_syntax::ast::ItemKind::Function(function) = &item.kind else {
            continue;
        };
        if function.name.is_empty() {
            continue;
        }
        if !is_snake_case(&function.name) {
            push(
                report,
                config,
                "PGS-W1001",
                format!("la función `{}` no está en snake_case", function.name),
                item.span,
                Some("usa minúsculas con `_` entre palabras".to_owned()),
            );
        }
    }
}

fn is_snake_case(name: &str) -> bool {
    !name.is_empty()
        && name
            .chars()
            .all(|character| character.is_lowercase() || character.is_numeric() || character == '_')
}

fn contains_word(text: &str, word: &str) -> bool {
    let bytes = text.as_bytes();
    let mut from = 0;
    while let Some(offset) = text[from..].find(word) {
        let start = from + offset;
        let end = start + word.len();
        let before_ok =
            start == 0 || !(bytes[start - 1].is_ascii_alphanumeric() || bytes[start - 1] == b'_');
        let after_ok =
            end == bytes.len() || !(bytes[end].is_ascii_alphanumeric() || bytes[end] == b'_');
        if before_ok && after_ok {
            return true;
        }
        from = end;
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(source: &str) -> Vec<String> {
        let report = lint(source, FileId::new(0), &LintConfig::new());
        report
            .diagnostics
            .iter()
            .map(|diagnostic| diagnostic.code.to_owned())
            .collect()
    }

    #[test]
    fn detecta_bindings_sin_uso_y_sombreado() {
        let source = "f = () -> Int\n    bind usado = 1\n    bind sobra = 2\n    if usado == 1 then\n        bind usado = 3\n        usado\n    else\n        usado\n";
        let codes = run(source);
        assert!(codes.contains(&"PGS-W1101".to_owned()));
        assert!(codes.contains(&"PGS-W1102".to_owned()));
    }

    #[test]
    fn detecta_import_sin_uso() {
        let source = "summon std::via\n\nf = () -> Int\n    1\n";
        assert_eq!(run(source), vec!["PGS-W2001"]);
    }

    #[test]
    fn detecta_panic_en_produccion_pero_no_en_tests() {
        let source =
            "f = () -> Int\n    panic(\"no\")\n\n@@test\ng = () -> Unit\n    panic(\"test\")\n";
        let codes = run(source);
        assert_eq!(codes.iter().filter(|code| *code == "PGS-W1501").count(), 1);
    }

    #[test]
    fn detecta_salto_y_sentencia_inalcanzable() {
        let source = "f = () -> Int\n    return 1\n    print(2)\n";
        assert!(run(source).contains(&"PGS-W6001".to_owned()));
    }

    #[test]
    fn detecta_bucle_constante_y_comparacion_redundante() {
        let source =
            "f = () -> Int\n    while true do\n        break\n    bind x = 1 == true\n    1\n";
        let codes = run(source);
        assert!(codes.contains(&"PGS-W6002".to_owned()));
        assert!(codes.contains(&"PGS-W1201".to_owned()));
    }

    #[test]
    fn detecta_brazos_duplicados_de_match() {
        let source = "f = (x: Int) -> Int\n    match x\n        when 1 then 1\n        when 1 then 2\n        else 3\n";
        assert!(run(source).contains(&"PGS-W9001".to_owned()));
    }

    #[test]
    fn detecta_cadena_de_if_que_es_un_match() {
        let source =
            "f = (x: Int) -> Int\n    if x == 1 then 1\n    elseif x == 2 then 2\n    else 3\n";
        assert!(run(source).contains(&"PGS-W1301".to_owned()));
    }

    #[test]
    fn detecta_nombres_fuera_de_convencion() {
        let source = "MalNombre = () -> Int\n    1\n";
        assert!(run(source).contains(&"PGS-W1001".to_owned()));
    }

    #[test]
    fn la_stdlib_no_tiene_avisos() {
        let mut checked = 0usize;
        for (index, file) in pengu_std::files().iter().enumerate() {
            let report = lint(file.text, pengu_std::file_id(index), &LintConfig::new());
            assert!(
                report.diagnostics.is_empty(),
                "{}: {:?}",
                file.name,
                report
                    .diagnostics
                    .iter()
                    .map(|diagnostic| (diagnostic.code, &diagnostic.message))
                    .collect::<Vec<_>>()
            );
            checked += 1;
        }
        assert!(
            checked > 20,
            "se esperaban los módulos de std, se vieron {checked}"
        );
    }

    #[test]
    fn el_config_permite_silenciar_por_codigo_o_nombre() {
        let mut config = LintConfig::new();
        assert!(config.set("PGS-W2001", Level::Allow));
        assert!(config.set("unused-binding", Level::Allow));
        assert!(!config.set("no-existe", Level::Warn));
        let source = "summon std::via\n\nf = () -> Int\n    1\n";
        let report = lint(source, FileId::new(0), &config);
        assert_eq!(report.diagnostics.len(), 0);
    }

    #[test]
    fn deny_convierte_en_error() {
        let mut config = LintConfig::new();
        config.set("PGS-W1501", Level::Deny);
        let report = lint("f = () -> Int\n    fail(\"no\")\n", FileId::new(0), &config);
        assert!(report.has_errors());
    }
}
