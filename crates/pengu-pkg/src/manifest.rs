//! Edición quirúrgica de `Tome.toml` para `pengu add` y `pengu remove`.
//!
//! No se reescribe el manifiesto completo: se conserva el formato y los comentarios y
//! solo se toca la línea de la dependencia indicada.

use crate::PkgError;

/// Nombre de sección donde viven las dependencias.
const SECTION: &str = "[dependencies]";

/// Inserta o reemplaza `name` en `[dependencies]` con la especificación dada.
///
/// # Errors
/// Devuelve `PGS-E2010` si el nombre no es un identificador válido o si hay dos
/// secciones `[dependencies]`.
pub fn set_dependency(text: &str, name: &str, spec: &str) -> Result<String, PkgError> {
    validate_name(name)?;
    let (start, end) = section_bounds(text)?;
    let line = format!("{name} = {spec}");
    let Some((start, end)) = start.zip(end) else {
        return Ok(append_section(text, &line));
    };
    let mut lines: Vec<String> = text.lines().map(str::to_owned).collect();
    let position = lines
        .iter()
        .enumerate()
        .skip(start + 1)
        .take(end.saturating_sub(start + 1))
        .find(|(_, existing)| is_dependency_line(existing, name))
        .map(|(index, _)| index);
    match position {
        Some(index) => lines[index] = line,
        None => lines.insert(end, line),
    }
    Ok(finish(&lines, text.ends_with('\n')))
}

/// Elimina `name` de `[dependencies]`.
///
/// # Errors
/// Devuelve `PGS-E2010` si la dependencia no existe.
pub fn remove_dependency(text: &str, name: &str) -> Result<String, PkgError> {
    validate_name(name)?;
    let (start, end) = section_bounds(text)?;
    let (Some(start), Some(end)) = (start, end) else {
        return Err(PkgError::dependency_not_found(name));
    };
    let mut lines: Vec<String> = text.lines().map(str::to_owned).collect();
    let found = lines
        .iter()
        .enumerate()
        .skip(start + 1)
        .take(end.saturating_sub(start + 1))
        .find(|(_, line)| is_dependency_line(line, name))
        .map(|(index, _)| index);
    let Some(index) = found else {
        return Err(PkgError::dependency_not_found(name));
    };
    lines.remove(index);
    Ok(finish(&lines, text.ends_with('\n')))
}

/// `true` si el manifiesto declara `name`.
#[must_use]
pub fn has_dependency(text: &str, name: &str) -> bool {
    let Ok((Some(start), Some(end))) = section_bounds(text) else {
        return false;
    };
    text.lines()
        .skip(start + 1)
        .take(end.saturating_sub(start + 1))
        .any(|line| is_dependency_line(line, name))
}

fn is_dependency_line(line: &str, name: &str) -> bool {
    line.trim_start()
        .strip_prefix(name)
        .is_some_and(|rest| rest.trim_start().starts_with('='))
}

fn finish(lines: &[String], trailing_newline: bool) -> String {
    let mut out = lines.join("\n");
    if trailing_newline {
        out.push('\n');
    }
    out
}

fn append_section(text: &str, line: &str) -> String {
    let mut out = text.to_owned();
    if !out.ends_with('\n') {
        out.push('\n');
    }
    out.push('\n');
    out.push_str(SECTION);
    out.push('\n');
    out.push_str(line);
    out.push('\n');
    out
}

fn validate_name(name: &str) -> Result<(), PkgError> {
    let valid = !name.is_empty()
        && !name.starts_with(|ch: char| ch.is_ascii_digit())
        && name
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || ch == '_');
    if valid {
        Ok(())
    } else {
        Err(PkgError::plain(
            "PGS-E2010",
            format!("`{name}` no es un nombre de dependencia válido"),
        ))
    }
}

/// Devuelve `(cabecera, fin)` de la sección de dependencias: índices de línea donde
/// `header` es la línea `[dependencies]` y `fin` la primera línea de otra sección.
fn section_bounds(text: &str) -> Result<(Option<usize>, Option<usize>), PkgError> {
    let lines: Vec<&str> = text.lines().collect();
    let mut header = None;
    let mut end = None;
    for (index, line) in lines.iter().enumerate() {
        let trimmed = line.trim();
        if trimmed == SECTION {
            if header.is_some() {
                return Err(PkgError::plain(
                    "PGS-E2010",
                    "`Tome.toml` tiene dos secciones `[dependencies]`",
                ));
            }
            header = Some(index);
            continue;
        }
        if header.is_some() && trimmed.starts_with('[') && trimmed.ends_with(']') {
            end = Some(index);
            break;
        }
    }
    Ok((header, end.or_else(|| header.map(|_| lines.len()))))
}

#[cfg(test)]
mod tests {
    use super::*;

    const BASE: &str = "[tome]\nname = \"demo\"\nversion = \"0.1.0\"\n";

    #[test]
    fn crea_la_seccion_si_no_existe() {
        let out = set_dependency(BASE, "text", "{ git = \"u\", tag = \"v1\" }").expect("alta");
        assert!(out.contains("[dependencies]\ntext = { git = \"u\", tag = \"v1\" }"));
    }

    #[test]
    fn reemplaza_la_entrada_existente() {
        let text = format!(
            "{BASE}\n[dependencies]\ntext = {{ path = \"../x\" }}\njson = {{ tag = \"v1\" }}\n"
        );
        let out = set_dependency(&text, "text", "{ git = \"u\", tag = \"v2\" }").expect("alta");
        assert!(out.contains("text = { git = \"u\", tag = \"v2\" }"));
        assert!(out.contains("json = { tag = \"v1\" }"));
        assert_eq!(out.matches("text =").count(), 1);
    }

    #[test]
    fn quita_una_entrada() {
        let text = format!(
            "{BASE}\n[dependencies]\ntext = {{ path = \"../x\" }}\njson = {{ tag = \"v1\" }}\n\n[link]\nm = {{ lib = \"m\" }}\n"
        );
        let out = remove_dependency(&text, "text").expect("baja");
        assert!(!out.contains("text ="));
        assert!(out.contains("json ="));
        assert!(out.contains("[link]"));
    }

    #[test]
    fn quitar_inexistente_es_error() {
        assert!(remove_dependency(BASE, "nope").is_err());
    }

    #[test]
    fn nombre_invalido() {
        assert!(set_dependency(BASE, "2bad", "{}").is_err());
        assert!(set_dependency(BASE, "", "{}").is_err());
    }

    #[test]
    fn conserva_comentarios_y_orden() {
        let text = format!("{BASE}# deps\n[dependencies]\n# texto\ntext = {{ path = \"../x\" }}\n");
        let out = set_dependency(&text, "text", "{ path = \"../y\" }").expect("alta");
        assert!(out.contains("# texto"));
        assert!(out.contains("# deps"));
    }

    #[test]
    fn devuelve_si_existe() {
        let text = format!("{BASE}\n[dependencies]\ntext = {{ path = \"../x\" }}\n");
        assert!(has_dependency(&text, "text"));
        assert!(!has_dependency(&text, "json"));
    }
}
