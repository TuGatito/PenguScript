//! Render del árbol de dependencias a partir del manifiesto y del lock.

use std::fmt::Write as _;

use pengu_project::Manifest;

use crate::lock::Lockfile;

/// Renderiza el árbol con conectores de caja, en orden alfabético.
#[must_use]
pub fn render(manifest: &Manifest, lock: &Lockfile) -> String {
    let mut out = format!("{} v{}\n", manifest.name, manifest.version);
    let mut root_children: Vec<String> = manifest
        .dependencies
        .iter()
        .map(|dependency| dependency.name.clone())
        .collect();
    root_children.sort();
    root_children.dedup();
    let total = root_children.len();
    for (index, name) in root_children.iter().enumerate() {
        let last = index + 1 == total;
        render_node(&mut out, lock, name, "", last, &mut Vec::new());
    }
    out
}

fn render_node(
    out: &mut String,
    lock: &Lockfile,
    name: &str,
    prefix: &str,
    last: bool,
    stack: &mut Vec<String>,
) {
    let connector = if last { "└── " } else { "├── " };
    match lock.package(name) {
        Some(package) => {
            writeln!(
                out,
                "{prefix}{connector}{} v{} ({})",
                package.name, package.version, package.source
            )
            .expect("escribir en String");
            stack.push(package.name.clone());
            let mut children = package.dependencies.clone();
            children.sort();
            children.dedup();
            let child_prefix = format!("{prefix}{}", if last { "    " } else { "│   " });
            let total = children.len();
            for (index, child) in children.iter().enumerate() {
                if stack.contains(child) {
                    let child_last = index + 1 == total;
                    let connector = if child_last {
                        "└── "
                    } else {
                        "├── "
                    };
                    writeln!(out, "{child_prefix}{connector}{child} (ciclo)")
                        .expect("escribir en String");
                    continue;
                }
                render_node(out, lock, child, &child_prefix, index + 1 == total, stack);
            }
            stack.pop();
        }
        None => {
            writeln!(out, "{prefix}{connector}{name} (ausente en el lock)")
                .expect("escribir en String");
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::lock::LockedPackage;

    #[test]
    fn arbol_con_hijos_y_ausentes() {
        let manifest = pengu_project::parse_manifest(
            "[tome]\nname = \"raiz\"\nversion = \"0.1.0\"\npengu = \"0.6\"\n\
             [dependencies]\njson = { path = \"../json\" }\ntext = { path = \"../text\" }\n",
        )
        .expect("manifiesto");
        let lock = Lockfile::new(vec![
            LockedPackage {
                name: "json".into(),
                version: "0.3.1".into(),
                source: "path+../json".into(),
                commit: String::new(),
                checksum: format!("sha256-{}", "aa".repeat(32)),
                features: Vec::new(),
                dependencies: vec!["text".into()],
            },
            LockedPackage {
                name: "text".into(),
                version: "1.2.3".into(),
                source: "path+../text".into(),
                commit: String::new(),
                checksum: format!("sha256-{}", "bb".repeat(32)),
                features: Vec::new(),
                dependencies: Vec::new(),
            },
        ])
        .expect("lock");
        let text = render(&manifest, &lock);
        assert!(text.starts_with("raiz v0.1.0\n"), "{text}");
        assert!(text.contains("├── json v0.3.1"), "{text}");
        assert!(text.contains("│   └── text v1.2.3"), "{text}");
        assert!(text.contains("└── text v1.2.3"), "{text}");
    }
}
