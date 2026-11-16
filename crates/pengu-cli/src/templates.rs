//! Templates embebidos de `pengu new`.
//!
//! Cada template es una lista de archivos con su contenido. Se copian tal cual y no
//! ejecutan código: lo único que hace `pengu new` es escribir el proyecto y, si el
//! template declara dependencias, dejar que `pengu fetch` resuelva el lock.

/// Un archivo del template.
pub struct TemplateFile {
    /// Ruta relativa al proyecto.
    pub path: &'static str,
    /// Contenido exacto.
    pub content: &'static str,
}

/// Un template embebido.
pub struct Template {
    /// Nombre para `--template`.
    pub name: &'static str,
    /// Descripción de una línea.
    pub description: &'static str,
    /// Archivos que escribe.
    pub files: &'static [TemplateFile],
}

/// Los templates disponibles.
pub const TEMPLATES: &[Template] = &[BIN, LIB, WITH_DEPENDENCY];

/// Binario mínimo.
pub const BIN: Template = Template {
    name: "bin",
    description: "binario «hola mundo» con un test",
    files: &[
        TemplateFile {
            path: "Tome.toml",
            content: TOME_BIN,
        },
        TemplateFile {
            path: "main.pengu",
            content: MAIN,
        },
    ],
};

/// Biblioteca.
pub const LIB: Template = Template {
    name: "lib",
    description: "biblioteca con una función y su test",
    files: &[
        TemplateFile {
            path: "Tome.toml",
            content: TOME_LIB,
        },
        TemplateFile {
            path: "lib.pengu",
            content: LIB_SOURCE,
        },
    ],
};

/// Binario que usa una dependencia local (sin red).
pub const WITH_DEPENDENCY: Template = Template {
    name: "with-dependency",
    description: "binario que usa una dependencia local en `deps/util`",
    files: &[
        TemplateFile {
            path: "Tome.toml",
            content: TOME_DEP,
        },
        TemplateFile {
            path: "main.pengu",
            content: MAIN_DEP,
        },
        TemplateFile {
            path: "deps/util/Tome.toml",
            content: TOME_UTIL,
        },
        TemplateFile {
            path: "deps/util/lib.pengu",
            content: UTIL_SOURCE,
        },
    ],
};

/// Busca un template por nombre.
#[must_use]
pub fn find(name: &str) -> Option<&'static Template> {
    TEMPLATES.iter().find(|template| template.name == name)
}

/// Nombres válidos para `--template list`.
#[must_use]
pub fn names() -> String {
    let mut text = String::from("templates:\n");
    for template in TEMPLATES {
        use std::fmt::Write as _;
        let _ = writeln!(text, "    {:<15} {}", template.name, template.description);
    }
    text
}

const TOME_BIN: &str = "\
[tome]
name = \"{{name}}\"
version = \"0.1.0\"
pengu = \"0.6\"
edition = \"2024\"

[[bin]]
name = \"{{name}}\"
path = \"main.pengu\"
";

const TOME_LIB: &str = "\
[tome]
name = \"{{name}}\"
version = \"0.1.0\"
pengu = \"0.6\"
edition = \"2024\"

[[lib]]
name = \"{{name}}\"
path = \"lib.pengu\"
";

const TOME_DEP: &str = "\
[tome]
name = \"{{name}}\"
version = \"0.1.0\"
pengu = \"0.6\"
edition = \"2024\"

[dependencies]
util = { path = \"deps/util\" }

[[bin]]
name = \"{{name}}\"
path = \"main.pengu\"
";

const TOME_UTIL: &str = "\
[tome]
name = \"util\"
version = \"1.0.0\"
pengu = \"0.6\"
edition = \"2024\"

[[lib]]
name = \"util\"
path = \"lib.pengu\"
";

const MAIN: &str = "\
grimoire
    print(\"hola desde {{name}}\")
";

const MAIN_DEP: &str = "\
summon util::greet

grimoire
    print(greet(\"{{name}}\"))
";

const LIB_SOURCE: &str = "\
scroll {{name}}

unveil double = (value: Int) -> Int
    value * 2

@@test
duplica = () -> Unit
    assert_eq(double(2), 4)
";

const UTIL_SOURCE: &str = "\
scroll util

unveil greet = (name: &Str) -> String
    \"hola, #{name}!\"
";

/// Aplica el nombre del proyecto a los archivos de un template.
#[must_use]
pub fn render(template: &Template, name: &str) -> Vec<(String, String)> {
    template
        .files
        .iter()
        .map(|file| {
            (
                file.path.replace("{{name}}", name),
                file.content.replace("{{name}}", name),
            )
        })
        .collect()
}
