//! Elección de la etiqueta adecuada al añadir una dependencia git.

/// Elige la mejor etiqueta: la versión semántica más alta.
///
/// Acepta `v1.2.3`, `1.2.3`, `1.2` y `1`. Las etiquetas que no son semver se ignoran;
/// si no hay ninguna, devuelve `None` y el llamador debe caer a la rama por defecto.
#[must_use]
pub fn best_tag(tags: &[String]) -> Option<String> {
    let mut best: Option<((u64, u64, u64), &String)> = None;
    for tag in tags {
        let Some(version) = parse_version(tag) else {
            continue;
        };
        if best.as_ref().is_none_or(|(current, _)| version > *current) {
            best = Some((version, tag));
        }
    }
    best.map(|(_, tag)| tag.clone())
}

/// `true` si la etiqueta tiene forma de versión (`1`, `1.2`, `1.2.3`, con `v` opcional).
#[must_use]
pub fn is_version_tag(tag: &str) -> bool {
    parse_version(tag).is_some()
}

fn parse_version(tag: &str) -> Option<(u64, u64, u64)> {
    let text = tag.strip_prefix('v').unwrap_or(tag);
    let text = text.split(['-', '+']).next()?;
    let mut parts = text.split('.');
    let major = parts.next()?.parse().ok()?;
    let minor = parts.next().map_or(Some(0), |part| part.parse().ok())?;
    let patch = parts.next().map_or(Some(0), |part| part.parse().ok())?;
    if parts.next().is_some() {
        return None;
    }
    Some((major, minor, patch))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tags(list: &[&str]) -> Vec<String> {
        list.iter().map(|tag| (*tag).to_owned()).collect()
    }

    #[test]
    fn elige_la_version_mas_alta() {
        let list = tags(&["v1.0.0", "v1.10.0", "v1.2.3", "latest"]);
        assert_eq!(best_tag(&list), Some("v1.10.0".to_owned()));
    }

    #[test]
    fn acepta_versiones_cortas_y_sin_v() {
        let list = tags(&["1.2", "2", "3.0.1"]);
        assert_eq!(best_tag(&list), Some("3.0.1".to_owned()));
    }

    #[test]
    fn ignora_no_semver() {
        let list = tags(&["release", "nightly", "v1.0.0-rc1"]);
        assert_eq!(best_tag(&list), Some("v1.0.0-rc1".to_owned()));
        assert_eq!(best_tag(&tags(&["nightly"])), None);
    }

    #[test]
    fn reconoce_formas() {
        assert!(is_version_tag("v2"));
        assert!(is_version_tag("2.1.0"));
        assert!(!is_version_tag("v2.1.0.1"));
        assert!(!is_version_tag("main"));
    }
}
