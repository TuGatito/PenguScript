//! Mapeo de tipos C (`qualType`) a tipos de `PenguScript`.
//!
//! La tabla es explícita y conservadora: lo que no se puede representar se
//! devuelve como [`Mapped::Omitted`] con el motivo, y el generador lo reporta.

use std::collections::{BTreeMap, BTreeSet};

/// Resultado de mapear un tipo.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Mapped {
    /// Tipo de `PenguScript`.
    Ty(String),
    /// No representable, con el motivo.
    Omitted(String),
}

impl Mapped {
    /// El tipo, si se pudo mapear.
    #[must_use]
    pub fn ty(&self) -> Option<&str> {
        match self {
            Self::Ty(ty) => Some(ty),
            Self::Omitted(_) => None,
        }
    }
}

/// Contexto de nombres del archivo que se está mapeando.
#[derive(Clone, Debug, Default)]
pub struct Context {
    /// `rune` completos conocidos.
    pub records: BTreeSet<String>,
    /// `enchanting` conocidos (se mapean a `Int`).
    pub enums: BTreeSet<String>,
    /// Alias de tipos (`typedef unsigned long u_long`).
    pub aliases: BTreeMap<String, String>,
}

impl Context {
    /// Registra un alias, ignorando ciclos.
    pub fn add_alias(&mut self, name: &str, target: &str) {
        if name != target {
            self.aliases.insert(name.to_owned(), target.to_owned());
        }
    }

    fn expand(&self, name: &str, depth: usize) -> Mapped {
        if depth > 8 {
            return Mapped::Omitted(format!("alias cíclico `{name}`"));
        }
        if let Some(target) = self.aliases.get(name) {
            return map_with_context(target, self, depth + 1);
        }
        Mapped::Omitted(format!("tipo desconocido `{name}`"))
    }

    /// Indica si `name` es un tipo conocido (registro, enum o alias).
    #[must_use]
    pub fn knows(&self, name: &str) -> bool {
        self.records.contains(name) || self.enums.contains(name) || self.aliases.contains_key(name)
    }
}

/// Mapea un `qualType` sin contexto (solo tipos primitivos y punteros).
#[must_use]
pub fn map(qual_type: &str) -> Mapped {
    map_with_context(qual_type, &Context::default(), 0)
}

/// Mapea un `qualType` con el contexto del archivo.
#[must_use]
pub fn map_with_context(qual_type: &str, context: &Context, depth: usize) -> Mapped {
    let text = normalize(qual_type);
    if text.is_empty() {
        return Mapped::Omitted("tipo vacío".to_owned());
    }
    if text.contains("(*") || text.contains("( *") {
        return Mapped::Omitted("puntero a función".to_owned());
    }
    if text.ends_with(']') {
        return Mapped::Omitted("array en línea".to_owned());
    }
    if let Some((base, pointers, is_const)) = pointer_parts(&text) {
        return map_pointer(&base, pointers, is_const, context, depth);
    }
    if text == "void" {
        return Mapped::Ty("Unit".to_owned());
    }
    map_base(&text, context, depth)
}

fn normalize(qual_type: &str) -> String {
    qual_type.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Separa la base y el número de `*` finales.
fn pointer_parts(text: &str) -> Option<(String, usize, bool)> {
    let mut rest = text.trim().to_owned();
    let mut pointers = 0;
    loop {
        let trimmed = rest.trim_end();
        if let Some(stripped) = trimmed.strip_suffix('*') {
            pointers += 1;
            rest = stripped.trim_end().to_owned();
            continue;
        }
        let mut dropped = false;
        for qualifier in ["const", "volatile", "restrict"] {
            if let Some(stripped) = trimmed.strip_suffix(qualifier) {
                let boundary =
                    stripped.is_empty() || stripped.ends_with(' ') || stripped.ends_with('*');
                if boundary {
                    rest = stripped.trim_end().to_owned();
                    dropped = true;
                    break;
                }
            }
        }
        if dropped {
            continue;
        }
        break;
    }
    if pointers == 0 {
        return None;
    }
    let is_const = rest.starts_with("const") || text.contains("const char");
    Some((rest, pointers, is_const))
}

fn map_pointer(
    base: &str,
    pointers: usize,
    is_const: bool,
    context: &Context,
    depth: usize,
) -> Mapped {
    if pointers > 1 {
        let inner = map_pointer(base, pointers - 1, is_const, context, depth);
        return match inner {
            Mapped::Ty(inner) => Mapped::Ty(format!("Ptr[{inner}]")),
            Mapped::Omitted(reason) => Mapped::Omitted(reason),
        };
    }
    let base = strip_qualifiers(base.trim());
    if base == "char" {
        return Mapped::Ty(if is_const { "CStr" } else { "Ptr[I8]" }.to_owned());
    }
    if base == "void" {
        return Mapped::Ty("Ptr[U8]".to_owned());
    }
    match map_base(base, context, depth) {
        Mapped::Ty(ty) => Mapped::Ty(format!("Ptr[{ty}]")),
        Mapped::Omitted(_) if is_unknown_record(base, context) => {
            // Punteros a estructuras opacas: se tratan como memoria cruda.
            Mapped::Ty("Ptr[U8]".to_owned())
        }
        Mapped::Omitted(reason) => Mapped::Omitted(reason),
    }
}

fn is_unknown_record(base: &str, context: &Context) -> bool {
    if let Some(name) = base
        .strip_prefix("struct ")
        .or_else(|| base.strip_prefix("union "))
    {
        return !context.knows(name);
    }
    // `typedef struct sqlite3 sqlite3;` deja un nombre opaco sin `struct `.
    !context.knows(base) && scalar_type(base).is_none() && !base.contains("(*")
}

fn strip_qualifiers(text: &str) -> &str {
    let mut current = text.trim();
    loop {
        let trimmed = current
            .strip_prefix("const ")
            .or_else(|| current.strip_prefix("volatile "))
            .or_else(|| current.strip_prefix("restrict "));
        match trimmed {
            Some(rest) => current = rest.trim(),
            None => return current,
        }
    }
}

fn map_base(base: &str, context: &Context, depth: usize) -> Mapped {
    let base = strip_qualifiers(base);
    if let Some(name) = base.strip_prefix("union ") {
        return Mapped::Omitted(format!("union `{name}`"));
    }
    if let Some(name) = base
        .strip_prefix("struct ")
        .or_else(|| base.strip_prefix("enum "))
    {
        if let Some(mapped) = context.aliases.get(name) {
            return map_with_context(mapped, context, depth + 1);
        }
        if context.enums.contains(name) {
            return Mapped::Ty("Int".to_owned());
        }
        if context.records.contains(name) {
            return Mapped::Ty(name.to_owned());
        }
        return context.expand(name, depth);
    }
    if context.enums.contains(base) {
        return Mapped::Ty("Int".to_owned());
    }
    if context.records.contains(base) {
        return Mapped::Ty(base.to_owned());
    }
    let scalar = scalar_type(base);
    if let Some(ty) = scalar {
        return ty;
    }
    context.expand(base, depth)
}

#[allow(clippy::match_same_arms)] // tabla agrupada por familia, no por tamaño
fn scalar_type(name: &str) -> Option<Mapped> {
    let key = canonical(name);
    let ty = match key.as_str() {
        "bool" | "_Bool" => "Bool",
        "char" | "char signed" => "I8",
        "char unsigned" => "U8",
        "short" => "I16",
        "int short" | "short signed" => "I16",
        "int short signed" => "I16",
        "int short unsigned" | "short unsigned" => "U16",
        "int" | "int signed" | "signed" => "Int",
        "int unsigned" | "unsigned" => "U32",
        "int long" | "long" | "long long" | "int long long" | "long signed" => "I64",
        "int long unsigned" | "long unsigned" | "long long unsigned" | "int long long unsigned" => {
            "U64"
        }
        "float" => "F32",
        "double" => "F64",
        "size_t" | "uintptr_t" | "__size_t" | "__uintptr_t" => "Usize",
        "ssize_t" | "ptrdiff_t" | "intptr_t" | "__ssize_t" | "__ptrdiff_t" | "__intptr_t" => {
            "Isize"
        }
        "int8_t" | "__int8_t" => "I8",
        "uint8_t" | "__uint8_t" => "U8",
        "int16_t" | "__int16_t" => "I16",
        "uint16_t" | "__uint16_t" => "U16",
        "int32_t" | "__int32_t" => "Int",
        "uint32_t" | "__uint32_t" => "U32",
        "int64_t" | "__int64_t" => "I64",
        "uint64_t" | "__uint64_t" => "U64",
        "_Float128" | "__float128" | "double long" => {
            return Some(Mapped::Omitted("flotante no representable".to_owned()));
        }
        _ => return None,
    };
    Some(Mapped::Ty(ty.to_owned()))
}

/// Clave insensible al orden de las palabras (`unsigned long` == `long unsigned`).
fn canonical(name: &str) -> String {
    let mut tokens: Vec<&str> = name.split_whitespace().collect();
    tokens.sort_unstable();
    tokens.join(" ")
}

/// Separa el tipo de retorno y los parámetros de un `qualType` de función.
#[must_use]
pub fn split_function(qual_type: &str) -> Option<(String, Vec<String>)> {
    let text = normalize(qual_type);
    let start = text.find('(')?;
    let ret = text[..start].trim().to_owned();
    let params = text[start..].trim();
    if !params.starts_with('(') || !params.ends_with(')') {
        return None;
    }
    let inner = &params[1..params.len() - 1];
    let inner = inner.trim();
    if inner.is_empty() || inner == "void" {
        return Some((ret, Vec::new()));
    }
    let mut parts = Vec::new();
    let mut depth = 0usize;
    let mut current = String::new();
    for character in inner.chars() {
        match character {
            '(' => {
                depth += 1;
                current.push(character);
            }
            ')' => {
                depth = depth.saturating_sub(1);
                current.push(character);
            }
            ',' if depth == 0 => {
                parts.push(current.trim().to_owned());
                current.clear();
            }
            _ => current.push(character),
        }
    }
    if !current.trim().is_empty() {
        parts.push(current.trim().to_owned());
    }
    Some((ret, parts))
}

#[cfg(test)]
mod tests {
    use super::{Context, Mapped, map, map_with_context, split_function};

    #[test]
    fn mapea_escalares() {
        assert_eq!(map("int").ty(), Some("Int"));
        assert_eq!(map("unsigned int").ty(), Some("U32"));
        assert_eq!(map("unsigned long").ty(), Some("U64"));
        assert_eq!(map("long long").ty(), Some("I64"));
        assert_eq!(map("size_t").ty(), Some("Usize"));
        assert_eq!(map("float").ty(), Some("F32"));
        assert_eq!(map("double").ty(), Some("F64"));
        assert_eq!(map("_Bool").ty(), Some("Bool"));
    }

    #[test]
    fn mapea_punteros() {
        assert_eq!(map("const char *").ty(), Some("CStr"));
        assert_eq!(map("char *").ty(), Some("Ptr[I8]"));
        assert_eq!(map("void *").ty(), Some("Ptr[U8]"));
        assert_eq!(map("int *").ty(), Some("Ptr[Int]"));
        assert_eq!(map("const char *const *").ty(), Some("Ptr[CStr]"));
    }

    #[test]
    fn omite_lo_que_no_representa() {
        assert!(matches!(map("void (*)(int)"), Mapped::Omitted(_)));
        assert!(matches!(map("long double"), Mapped::Omitted(_)));
        assert!(matches!(map("int [4]"), Mapped::Omitted(_)));
        assert!(matches!(map("union Data"), Mapped::Omitted(_)));
    }

    #[test]
    fn resuelve_alias_y_tipos_del_archivo() {
        let mut context = Context::default();
        context.add_alias("u_long", "unsigned long");
        context.records.insert("Node".to_owned());
        context.enums.insert("Mode".to_owned());
        assert_eq!(map_with_context("u_long", &context, 0).ty(), Some("U64"));
        assert_eq!(
            map_with_context("struct Node", &context, 0).ty(),
            Some("Node")
        );
        assert_eq!(
            map_with_context("struct Node *", &context, 0).ty(),
            Some("Ptr[Node]")
        );
        assert_eq!(map_with_context("Mode", &context, 0).ty(), Some("Int"));
        assert_eq!(map_with_context("enum Mode", &context, 0).ty(), Some("Int"));
    }

    #[test]
    fn separa_firmas() {
        let (ret, params) = split_function("int (const char *, int)").expect("firma");
        assert_eq!(ret, "int");
        assert_eq!(params, vec!["const char *".to_owned(), "int".to_owned()]);
        let (ret, params) = split_function("void (void)").expect("firma");
        assert_eq!(ret, "void");
        assert_eq!(params.len(), 0);
    }

    #[test]
    fn puntero_a_estructura_opaca() {
        let context = Context::default();
        assert_eq!(
            map_with_context("struct Opaque *", &context, 0).ty(),
            Some("Ptr[U8]")
        );
        assert!(matches!(
            map_with_context("struct Opaque", &context, 0),
            Mapped::Omitted(_)
        ));
    }
}
