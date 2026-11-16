//! Representación intermedia entre el AST JSON de clang y el `.d.pengu`.

use std::collections::BTreeMap;

use pengu_json::Value;

use crate::types::{Context, Mapped, map_with_context, split_function};
use crate::{BindgenError, Options};

/// Una estructura C completa.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Record {
    /// Nombre.
    pub name: String,
    /// Campos en orden de declaración.
    pub fields: Vec<Field>,
}

/// Campo de una estructura.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Field {
    /// Nombre.
    pub name: String,
    /// Tipo mapeado.
    pub ty: String,
}

/// Un enum C, que se emite como constantes `Int`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Enum {
    /// Nombre del enum (informativo; los valores son constantes sueltas).
    pub name: String,
    /// Constantes con su valor.
    pub constants: Vec<Constant>,
}

/// Una constante con valor entero.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Constant {
    /// Nombre.
    pub name: String,
    /// Valor.
    pub value: i64,
    /// Enum del que procede, si aplica.
    pub origin: Option<String>,
}

/// Una función externa.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Function {
    /// Nombre.
    pub name: String,
    /// Parámetros.
    pub params: Vec<Param>,
    /// Tipo de retorno.
    pub ret: String,
}

/// Parámetro de una función.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Param {
    /// Nombre.
    pub name: String,
    /// Tipo.
    pub ty: String,
}

/// Elemento que no se generó, con el motivo.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Omitted {
    /// Nombre del elemento C.
    pub name: String,
    /// Categoría (`función`, `estructura`, `campo`, `enum`).
    pub kind: &'static str,
    /// Motivo.
    pub reason: String,
}

/// Modelo intermedio completo.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct Ir {
    /// Estructuras, en orden de dependencia.
    pub records: Vec<Record>,
    /// Enums.
    pub enums: Vec<Enum>,
    /// Funciones.
    pub functions: Vec<Function>,
    /// Constantes sueltas.
    pub constants: Vec<Constant>,
    /// Omitidos con motivo.
    pub omitted: Vec<Omitted>,
}

impl Ir {
    /// Construye el modelo a partir del AST JSON de clang.
    ///
    /// # Errors
    ///
    /// Falla si la raíz del JSON no tiene forma de nodo de clang.
    pub fn from_json(
        json: &Value,
        options: &Options,
        main_file: Option<&str>,
    ) -> Result<Self, BindgenError> {
        let translation_unit = json
            .get("kind")
            .and_then(Value::as_str)
            .filter(|kind| *kind == "TranslationUnitDecl")
            .ok_or_else(|| {
                BindgenError::new("PGS-E2101", "clang no devolvió un TranslationUnitDecl")
            })?;
        let _ = translation_unit;
        let tag_names = collect_tag_names(json);
        let mut context = Context::default();
        collect_names(json, &tag_names, &mut context);
        let mut ir = Self::default();
        walk(
            json, &tag_names, &context, options, main_file, None, &mut ir,
        );
        dedupe(&mut ir);
        sanitize(&mut ir);
        ir.records = order_records(&ir.records);
        ir.enums.sort_by(|left, right| left.name.cmp(&right.name));
        ir.functions
            .sort_by(|left, right| left.name.cmp(&right.name));
        ir.constants
            .sort_by(|left, right| left.name.cmp(&right.name));
        ir.omitted.sort_by(|left, right| left.name.cmp(&right.name));
        Ok(ir)
    }
}

fn children(node: &Value) -> &[Value] {
    node.get("inner").and_then(Value::as_array).unwrap_or(&[])
}

fn name_of(node: &Value) -> Option<&str> {
    node.get("name").and_then(Value::as_str)
}

fn kind_of(node: &Value) -> &str {
    node.get("kind").and_then(Value::as_str).unwrap_or_default()
}

/// Dentro de un `#[repr(C)]` un `CStr` es un puntero: se emite como `Ptr[I8]`
/// (o `Ptr[Ptr[I8]]` si el campo es un puntero a una cadena).
fn field_type(ty: &str) -> String {
    ty.replace("CStr", "Ptr[I8]")
}

fn qual_type(node: &Value) -> Option<&str> {
    node.get("type")
        .and_then(|node| node.get("qualType"))
        .and_then(Value::as_str)
}

fn is_implicit(node: &Value) -> bool {
    node.get("isImplicit")
        .and_then(Value::as_bool)
        .unwrap_or(false)
}

/// Nombres que los `typedef` dan a etiquetas anónimas.
fn collect_tag_names(root: &Value) -> BTreeMap<String, String> {
    fn visit(node: &Value, names: &mut BTreeMap<String, String>) {
        if is_implicit(node) {
            return;
        }
        if kind_of(node) == "TypedefDecl" {
            let Some(name) = name_of(node) else {
                return;
            };
            for child in children(node) {
                let owned = child
                    .get("isTagOwned")
                    .and_then(Value::as_bool)
                    .unwrap_or(false);
                if !owned {
                    continue;
                }
                if let Some(id) = child
                    .get("decl")
                    .and_then(|decl| decl.get("id"))
                    .and_then(Value::as_str)
                {
                    names.insert(id.to_owned(), name.to_owned());
                }
            }
        }
        for child in children(node) {
            visit(child, names);
        }
    }
    let mut names = BTreeMap::new();
    visit(root, &mut names);
    names
}

/// Primera pasada: tipos con nombre (registros, enums y alias).
fn collect_names(root: &Value, tag_names: &BTreeMap<String, String>, context: &mut Context) {
    fn visit(node: &Value, tag_names: &BTreeMap<String, String>, context: &mut Context) {
        if is_implicit(node) {
            return;
        }
        match kind_of(node) {
            "RecordDecl" => {
                if node
                    .get("completeDefinition")
                    .and_then(Value::as_bool)
                    .unwrap_or(false)
                {
                    if let Some(name) = record_name(node, tag_names) {
                        if kind_of(node) != "union"
                            && node.get("tagUsed").and_then(Value::as_str) != Some("union")
                        {
                            context.records.insert(name);
                        }
                    }
                }
            }
            "EnumDecl" => {
                if let Some(name) = record_name(node, tag_names) {
                    context.enums.insert(name);
                }
            }
            "TypedefDecl" => {
                if let (Some(name), Some(target)) = (name_of(node), qual_type(node)) {
                    let owned = children(node)
                        .iter()
                        .any(|child| child.get("decl").is_some());
                    if !owned {
                        context.add_alias(name, target);
                    }
                }
            }
            _ => {}
        }
        for child in children(node) {
            visit(child, tag_names, context);
        }
    }
    visit(root, tag_names, context);
}

fn record_name(node: &Value, tag_names: &BTreeMap<String, String>) -> Option<String> {
    if let Some(name) = name_of(node).filter(|name| !name.is_empty()) {
        return Some(name.to_owned());
    }
    let id = node.get("id").and_then(Value::as_str)?;
    tag_names.get(id).cloned()
}

#[allow(clippy::too_many_arguments)]
fn walk(
    node: &Value,
    tag_names: &BTreeMap<String, String>,
    context: &Context,
    options: &Options,
    main_file: Option<&str>,
    inherited: Option<bool>,
    ir: &mut Ir,
) {
    if is_implicit(node) {
        return;
    }
    let included = inherited == Some(true) || included_from(node);
    if main_file.is_some() && included {
        return;
    }
    match kind_of(node) {
        "RecordDecl" => visit_record(node, tag_names, context, options, ir),
        "EnumDecl" => visit_enum(node, tag_names, ctx_enums(context), options, ir),
        "FunctionDecl" => visit_function(node, context, options, ir),
        _ => {}
    }
    for child in children(node) {
        walk(
            child,
            tag_names,
            context,
            options,
            main_file,
            Some(included),
            ir,
        );
    }
}

fn ctx_enums(context: &Context) -> &std::collections::BTreeSet<String> {
    &context.enums
}

/// ¿El nodo viene de un `#include` (y no de la cabecera principal)?
fn included_from(node: &Value) -> bool {
    let loc = node
        .get("loc")
        .is_some_and(|loc| loc.get("includedFrom").is_some());
    let range = node
        .get("range")
        .and_then(|range| range.get("begin"))
        .is_some_and(|begin| begin.get("includedFrom").is_some());
    loc || range
}

fn allowed(name: &str, options: &Options) -> bool {
    if options
        .blocklist
        .iter()
        .any(|pattern| matches(pattern, name))
    {
        return false;
    }
    options.allowlist.is_empty()
        || options
            .allowlist
            .iter()
            .any(|pattern| matches(pattern, name))
}

/// Coincidencia con `*` y `?`.
#[must_use]
pub fn matches(pattern: &str, name: &str) -> bool {
    fn go(pattern: &[u8], name: &[u8]) -> bool {
        match pattern.split_first() {
            None => name.is_empty(),
            Some((b'*', rest)) => (0..=name.len()).any(|index| go(rest, &name[index..])),
            Some((b'?', rest)) => name.split_first().is_some_and(|(_, tail)| go(rest, tail)),
            Some((expected, rest)) => name
                .split_first()
                .is_some_and(|(actual, tail)| actual == expected && go(rest, tail)),
        }
    }
    go(pattern.as_bytes(), name.as_bytes())
}

fn visit_record(
    node: &Value,
    tag_names: &BTreeMap<String, String>,
    context: &Context,
    options: &Options,
    ir: &mut Ir,
) {
    let complete = node
        .get("completeDefinition")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let Some(name) = record_name(node, tag_names) else {
        return;
    };
    if !allowed(&name, options) {
        return;
    }
    if node.get("tagUsed").and_then(Value::as_str) == Some("union") {
        ir.omitted.push(Omitted {
            name,
            kind: "estructura",
            reason: "union".to_owned(),
        });
        return;
    }
    if !complete {
        ir.omitted.push(Omitted {
            name,
            kind: "estructura",
            reason: "incompleta (solo declarada)".to_owned(),
        });
        return;
    }
    let mut fields = Vec::new();
    for child in children(node) {
        if kind_of(child) != "FieldDecl" {
            continue;
        }
        let Some(field_name) = name_of(child) else {
            ir.omitted.push(Omitted {
                name: name.clone(),
                kind: "campo",
                reason: "campo anónimo (bitfield o unión anónima)".to_owned(),
            });
            continue;
        };
        if child.get("isBitfield").is_some() {
            ir.omitted.push(Omitted {
                name: format!("{name}.{field_name}"),
                kind: "campo",
                reason: "bitfield".to_owned(),
            });
            continue;
        }
        let Some(qual) = qual_type(child) else {
            continue;
        };
        match map_with_context(qual, context, 0) {
            Mapped::Ty(ty) => fields.push(Field {
                name: field_name.to_owned(),
                ty: field_type(&ty),
            }),
            Mapped::Omitted(reason) => {
                ir.omitted.push(Omitted {
                    name: format!("{name}.{field_name}"),
                    kind: "campo",
                    reason,
                });
                return;
            }
        }
    }
    ir.records.push(Record { name, fields });
}

fn visit_enum(
    node: &Value,
    tag_names: &BTreeMap<String, String>,
    _enums: &std::collections::BTreeSet<String>,
    options: &Options,
    ir: &mut Ir,
) {
    let Some(name) = record_name(node, tag_names) else {
        return;
    };
    let mut constants = Vec::new();
    let mut next = 0_i64;
    for child in children(node) {
        if kind_of(child) != "EnumConstantDecl" {
            continue;
        }
        let Some(constant_name) = name_of(child) else {
            continue;
        };
        if !allowed(constant_name, options) {
            continue;
        }
        let value = children(child)
            .first()
            .and_then(|inner| inner.get("value"))
            .and_then(Value::as_str)
            .and_then(|value| value.parse::<i64>().ok())
            .unwrap_or(next);
        next = value + 1;
        constants.push(Constant {
            name: constant_name.to_owned(),
            value,
            origin: Some(name.clone()),
        });
    }
    ir.constants.extend(constants.iter().cloned());
    ir.enums.push(Enum { name, constants });
}

fn visit_function(node: &Value, context: &Context, options: &Options, ir: &mut Ir) {
    let Some(name) = name_of(node).filter(|name| !name.is_empty()) else {
        return;
    };
    if !allowed(name, options) {
        return;
    }
    let Some(qual) = qual_type(node) else {
        return;
    };
    if node
        .get("variadic")
        .and_then(Value::as_bool)
        .unwrap_or(false)
        || qual.contains("...")
    {
        ir.omitted.push(Omitted {
            name: name.to_owned(),
            kind: "función",
            reason: "variádica".to_owned(),
        });
        return;
    }
    let Some((ret, params)) = split_function(qual) else {
        ir.omitted.push(Omitted {
            name: name.to_owned(),
            kind: "función",
            reason: format!("firma no reconocida `{qual}`"),
        });
        return;
    };
    let ret = match map_with_context(&ret, context, 0) {
        Mapped::Ty(ty) => ty,
        Mapped::Omitted(reason) => {
            ir.omitted.push(Omitted {
                name: name.to_owned(),
                kind: "función",
                reason: format!("retorno: {reason}"),
            });
            return;
        }
    };
    let declared: Vec<&str> = children(node)
        .iter()
        .filter(|child| kind_of(child) == "ParmVarDecl")
        .filter_map(name_of)
        .collect();
    let mut mapped = Vec::new();
    for (index, param) in params.iter().enumerate() {
        let ty = match map_with_context(param, context, 0) {
            Mapped::Ty(ty) => ty,
            Mapped::Omitted(reason) => {
                ir.omitted.push(Omitted {
                    name: name.to_owned(),
                    kind: "función",
                    reason: format!("parámetro {}: {reason}", index + 1),
                });
                return;
            }
        };
        let param_name = declared
            .get(index)
            .filter(|value| !value.is_empty())
            .map_or_else(|| format!("arg{index}"), |value| (*value).to_owned());
        mapped.push(Param {
            name: param_name,
            ty,
        });
    }
    ir.functions.push(Function {
        name: name.to_owned(),
        params: mapped,
        ret,
    });
}

/// Un encabezado puede declarar lo mismo bajo varias macros: se conserva la
/// primera aparición.
fn dedupe(ir: &mut Ir) {
    let mut seen = std::collections::BTreeSet::new();
    ir.records.retain(|record| seen.insert(record.name.clone()));
    let mut seen = std::collections::BTreeSet::new();
    ir.functions
        .retain(|function| seen.insert(function.name.clone()));
    let mut seen = std::collections::BTreeSet::new();
    ir.constants
        .retain(|constant| seen.insert(constant.name.clone()));
}

/// Sustituye los tipos opacos por `Ptr[U8]` y descarta lo que no se puede emitir.
fn sanitize(ir: &mut Ir) {
    let mut known: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    for record in &ir.records {
        known.insert(record.name.clone());
    }
    for enumeration in &ir.enums {
        known.insert(enumeration.name.clone());
    }
    let scalars = [
        "Bool", "Int", "I8", "I16", "I32", "I64", "Isize", "U8", "U16", "U32", "U64", "Usize",
        "F32", "F64", "CStr",
    ];
    let resolved: Vec<String> = ir
        .records
        .iter()
        .map(|record| record.name.clone())
        .collect();
    for record in &mut ir.records {
        let mut fields = Vec::new();
        let mut skip = None;
        for field in &record.fields {
            let Some(ty) = sanitize_type(&field.ty, &known, &scalars) else {
                skip = Some(field.name.clone());
                break;
            };
            fields.push(Field {
                name: field.name.clone(),
                ty,
            });
        }
        if let Some(field) = skip {
            ir.omitted.push(Omitted {
                name: format!("{}.{field}", record.name),
                kind: "campo",
                reason: "tipo opaco por valor".to_owned(),
            });
            record.fields.clear();
            continue;
        }
        record.fields = fields;
    }
    ir.records
        .retain(|record| !record.fields.is_empty() || record.name.is_empty());
    let _ = resolved;
    let mut functions = Vec::new();
    for function in &ir.functions {
        let ret = sanitize_type(&function.ret, &known, &scalars);
        let mut params = Vec::new();
        let mut failed = ret.is_none();
        for param in &function.params {
            let Some(ty) = sanitize_type(&param.ty, &known, &scalars) else {
                failed = true;
                break;
            };
            params.push(Param {
                name: param.name.clone(),
                ty,
            });
        }
        if failed {
            ir.omitted.push(Omitted {
                name: function.name.clone(),
                kind: "función",
                reason: "tipo opaco por valor".to_owned(),
            });
            continue;
        }
        functions.push(Function {
            name: function.name.clone(),
            params,
            ret: ret.unwrap_or_else(|| "Unit".to_owned()),
        });
    }
    ir.functions = functions;
}

/// Devuelve el tipo saneado, o `None` si hay un tipo desconocido por valor.
fn sanitize_type(
    ty: &str,
    known: &std::collections::BTreeSet<String>,
    scalars: &[&str],
) -> Option<String> {
    let trimmed = ty.trim();
    if let Some(inner) = trimmed
        .strip_prefix("Ptr[")
        .and_then(|rest| rest.strip_suffix(']'))
    {
        let inner = sanitize_type(inner, known, scalars).unwrap_or_else(|| "U8".to_owned());
        return Some(format!("Ptr[{inner}]"));
    }
    if scalars.contains(&trimmed) || known.contains(trimmed) {
        return Some(trimmed.to_owned());
    }
    None
}

/// Ordena las estructuras para que cada una se declare después de sus campos por valor.
fn order_records(records: &[Record]) -> Vec<Record> {
    let names: std::collections::BTreeSet<&str> =
        records.iter().map(|record| record.name.as_str()).collect();
    let mut pending: Vec<&Record> = records.iter().collect();
    let mut ordered: Vec<Record> = Vec::new();
    let mut emitted: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    while !pending.is_empty() {
        let mut progressed = false;
        let mut index = 0;
        while index < pending.len() {
            let record = pending[index];
            let ready = record
                .fields
                .iter()
                .all(|field| !names.contains(field.ty.as_str()) || emitted.contains(&field.ty));
            if ready {
                emitted.insert(record.name.clone());
                ordered.push(record.clone());
                pending.remove(index);
                progressed = true;
            } else {
                index += 1;
            }
        }
        if !progressed {
            // Dependencia circular (imposible por valor en C): se conserva el orden.
            ordered.extend(pending.drain(..).cloned());
        }
    }
    ordered
}

#[cfg(test)]
mod tests {
    use super::{Ir, matches};
    use crate::Options;

    const HEADER: &str = r"#include <stddef.h>
typedef struct { int x; int y; } Point;
typedef enum { MODE_A = 0, MODE_B = 1, MODE_C = 4 } Mode;
struct Node { const char *name; struct Node *next; double weight; unsigned flags; };
typedef unsigned long u_long;
int add(int a, int b);
size_t strlen(const char *text);
void *alloc(size_t n);
int printf(const char *format, ...);
void accepts_callback(void (*callback)(int));
void bad(long double value);
";

    fn dump() -> String {
        let mut file = std::env::temp_dir().join(format!(
            "pengu-bindgen-{}-{}.h",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::write(&file, HEADER).unwrap();
        let dump = crate::clang::dump(&file, &Options::default()).expect("clang disponible");
        let _ = std::fs::remove_file(&mut file);
        dump
    }

    #[test]
    fn mapea_una_cabecera_real() {
        let json = pengu_json::parse(&dump()).expect("JSON");
        let ir = Ir::from_json(&json, &Options::default(), Some("/tmp/header.h")).expect("IR");
        let names: Vec<&str> = ir
            .records
            .iter()
            .map(|record| record.name.as_str())
            .collect();
        assert!(names.contains(&"Point"), "{names:?}");
        assert!(names.contains(&"Node"), "{names:?}");
        let point = ir
            .records
            .iter()
            .find(|record| record.name == "Point")
            .unwrap();
        assert_eq!(point.fields.len(), 2);
        assert_eq!(point.fields[0].ty, "Int");
        let node = ir
            .records
            .iter()
            .find(|record| record.name == "Node")
            .unwrap();
        assert_eq!(node.fields[0].ty, "Ptr[I8]");
        assert_eq!(node.fields[1].ty, "Ptr[Node]");
        assert_eq!(node.fields[2].ty, "F64");
        assert_eq!(node.fields[3].ty, "U32");
        let add = ir
            .functions
            .iter()
            .find(|function| function.name == "add")
            .unwrap();
        assert_eq!(add.ret, "Int");
        assert_eq!(add.params.len(), 2);
        assert_eq!(add.params[0].name, "a");
        let strlen = ir
            .functions
            .iter()
            .find(|function| function.name == "strlen")
            .unwrap();
        assert_eq!(strlen.ret, "Usize");
        assert_eq!(strlen.params[0].ty, "CStr");
        let alloc = ir
            .functions
            .iter()
            .find(|function| function.name == "alloc")
            .unwrap();
        assert_eq!(alloc.ret, "Ptr[U8]");
        let mode_b = ir
            .constants
            .iter()
            .find(|constant| constant.name == "MODE_B")
            .unwrap();
        assert_eq!(mode_b.value, 1);
        let mode_c = ir
            .constants
            .iter()
            .find(|constant| constant.name == "MODE_C")
            .unwrap();
        assert_eq!(mode_c.value, 4);
        assert!(
            ir.omitted
                .iter()
                .any(|item| item.name == "printf" && item.reason.contains("variádica")),
            "{:?}",
            ir.omitted
        );
        assert!(
            ir.omitted
                .iter()
                .any(|item| item.name == "accepts_callback"),
            "{:?}",
            ir.omitted
        );
        assert!(
            ir.omitted
                .iter()
                .any(|item| item.name == "bad"
                    && item.reason.contains("flotante no representable")),
            "{:?}",
            ir.omitted
        );
    }

    #[test]
    fn la_allowlist_filtra() {
        let json = pengu_json::parse(&dump()).expect("JSON");
        let options = Options {
            allowlist: vec!["add".to_owned(), "Point".to_owned()],
            ..Options::default()
        };
        let ir = Ir::from_json(&json, &options, None).expect("IR");
        assert_eq!(ir.functions.len(), 1);
        assert_eq!(ir.functions[0].name, "add");
        assert_eq!(ir.records.len(), 1);
        assert_eq!(ir.records[0].name, "Point");
    }

    #[test]
    fn patrones_simples() {
        assert!(matches("zlib*", "zlibVersion"));
        assert!(matches("*Count", "deflateCount"));
        assert!(matches("a?c", "abc"));
        assert!(!matches("abc", "abcd"));
    }
}
