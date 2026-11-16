//! Lector TOML mínimo para `Tome.toml` y `Tome.lock`.
//!
//! Cubre el subconjunto que usan la norma y el lockfile: tablas, arrays de tablas,
//! tablas en línea, arrays, cadenas con escapes, enteros, booleanos y comentarios. No
//! se admiten fechas, floats ni cadenas multilínea porque el formato no los necesita;
//! si aparecen, el error dice la línea.

use std::collections::BTreeMap;
use std::fmt;

/// Valor TOML del subconjunto soportado.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Value {
    /// Cadena.
    String(String),
    /// Entero.
    Integer(i64),
    /// Booleano.
    Bool(bool),
    /// Array (posiblemente heterogéneo, como el propio TOML).
    Array(Vec<Value>),
    /// Tabla.
    Table(Table),
}

/// Tabla ordenada por clave.
pub type Table = BTreeMap<String, Value>;

impl Value {
    /// Cadena, si lo es.
    #[must_use]
    pub fn as_str(&self) -> Option<&str> {
        match self {
            Self::String(value) => Some(value),
            _ => None,
        }
    }

    /// Tabla, si lo es.
    #[must_use]
    pub fn as_table(&self) -> Option<&Table> {
        match self {
            Self::Table(table) => Some(table),
            _ => None,
        }
    }

    /// Array, si lo es.
    #[must_use]
    pub fn as_array(&self) -> Option<&[Value]> {
        match self {
            Self::Array(values) => Some(values),
            _ => None,
        }
    }

    /// Entero, si lo es.
    #[must_use]
    pub fn as_integer(&self) -> Option<i64> {
        match self {
            Self::Integer(value) => Some(*value),
            _ => None,
        }
    }
}

/// Error de sintaxis con línea.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TomlError {
    /// Línea (1-based).
    pub line: usize,
    /// Motivo.
    pub message: String,
}

impl fmt::Display for TomlError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "línea {}: {}", self.line, self.message)
    }
}

impl std::error::Error for TomlError {}

/// Parsea un documento TOML.
///
/// # Errors
/// Devuelve [`TomlError`] con la línea si el documento no es TOML válido del
/// subconjunto soportado.
pub fn parse(source: &str) -> Result<Table, TomlError> {
    let mut parser = Parser {
        bytes: source.as_bytes(),
        position: 0,
        line: 1,
    };
    parser.document()
}

struct Parser<'a> {
    bytes: &'a [u8],
    position: usize,
    line: usize,
}

impl Parser<'_> {
    fn document(&mut self) -> Result<Table, TomlError> {
        let mut root = Table::new();
        let mut current = Vec::<String>::new();
        loop {
            self.skip_trivia();
            if self.at_end() {
                break;
            }
            if self.peek() == Some(b'[') {
                self.bump();
                let array = self.peek() == Some(b'[');
                if array {
                    self.bump();
                }
                let path = self.dotted_key()?;
                self.skip_spaces();
                self.expect(b']')?;
                if array {
                    self.expect(b']')?;
                }
                self.finish_line()?;
                if array {
                    push_array_table(&mut root, &path, self.line)?;
                } else {
                    ensure_table(&mut root, &path, self.line)?;
                }
                current = path;
                continue;
            }
            let path = self.dotted_key()?;
            self.skip_spaces();
            self.expect(b'=')?;
            self.skip_spaces();
            let value = self.value()?;
            self.finish_line()?;
            let table = table_at(&mut root, &current, self.line)?;
            insert_path(table, &path, value, self.line)?;
        }
        Ok(root)
    }

    fn value(&mut self) -> Result<Value, TomlError> {
        self.skip_spaces();
        match self.peek() {
            Some(b'"') => Ok(Value::String(self.basic_string()?)),
            Some(b'\'') => Ok(Value::String(self.literal_string()?)),
            Some(b'[') => self.array(),
            Some(b'{') => self.inline_table(),
            Some(b't') => {
                self.expect_word("true")?;
                Ok(Value::Bool(true))
            }
            Some(b'f') => {
                self.expect_word("false")?;
                Ok(Value::Bool(false))
            }
            Some(byte) if byte == b'-' || byte.is_ascii_digit() => self.integer(),
            other => Err(self.error(format!(
                "valor no soportado `{}`",
                other.map_or_else(|| "fin".to_owned(), |byte| char::from(byte).to_string())
            ))),
        }
    }

    fn array(&mut self) -> Result<Value, TomlError> {
        self.expect(b'[')?;
        let mut items = Vec::new();
        loop {
            self.skip_trivia();
            if self.peek() == Some(b']') {
                self.bump();
                break;
            }
            items.push(self.value()?);
            self.skip_trivia();
            match self.peek() {
                Some(b',') => {
                    self.bump();
                }
                Some(b']') => {
                    self.bump();
                    break;
                }
                _ => return Err(self.error("se esperaba `,` o `]` en el array")),
            }
        }
        Ok(Value::Array(items))
    }

    fn inline_table(&mut self) -> Result<Value, TomlError> {
        self.expect(b'{')?;
        let mut table = Table::new();
        loop {
            self.skip_spaces();
            if self.peek() == Some(b'}') {
                self.bump();
                break;
            }
            let path = self.dotted_key()?;
            self.skip_spaces();
            self.expect(b'=')?;
            self.skip_spaces();
            let value = self.value()?;
            insert_path(&mut table, &path, value, self.line)?;
            self.skip_spaces();
            match self.peek() {
                Some(b',') => {
                    self.bump();
                }
                Some(b'}') => {
                    self.bump();
                    break;
                }
                _ => return Err(self.error("se esperaba `,` o `}` en la tabla en línea")),
            }
        }
        Ok(Value::Table(table))
    }

    fn integer(&mut self) -> Result<Value, TomlError> {
        let start = self.position;
        if self.peek() == Some(b'-') {
            self.bump();
        }
        while matches!(self.peek(), Some(byte) if byte.is_ascii_digit() || byte == b'_') {
            self.bump();
        }
        let text: String =
            String::from_utf8_lossy(&self.bytes[start..self.position]).replace('_', "");
        text.parse::<i64>().map(Value::Integer).map_err(|_| {
            self.error(format!(
                "entero no válido `{text}` (no se admiten floats ni fechas)"
            ))
        })
    }

    fn basic_string(&mut self) -> Result<String, TomlError> {
        self.expect(b'"')?;
        let mut out = String::new();
        loop {
            let Some(byte) = self.peek() else {
                return Err(self.error("cadena sin cerrar"));
            };
            self.bump();
            match byte {
                b'"' => return Ok(out),
                b'\\' => {
                    let Some(escape) = self.peek() else {
                        return Err(self.error("escape sin terminar"));
                    };
                    self.bump();
                    match escape {
                        b'n' => out.push('\n'),
                        b't' => out.push('\t'),
                        b'r' => out.push('\r'),
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        other => {
                            return Err(self
                                .error(format!("escape no soportado `\\{}`", char::from(other))));
                        }
                    }
                }
                other => {
                    out.push_str(&String::from_utf8_lossy(&[other]));
                }
            }
        }
    }

    fn literal_string(&mut self) -> Result<String, TomlError> {
        self.expect(b'\'')?;
        let start = self.position;
        loop {
            match self.peek() {
                Some(b'\'') => {
                    let value =
                        String::from_utf8_lossy(&self.bytes[start..self.position]).into_owned();
                    self.bump();
                    return Ok(value);
                }
                Some(b'\n') | None => return Err(self.error("cadena sin cerrar")),
                Some(_) => self.bump(),
            }
        }
    }

    fn dotted_key(&mut self) -> Result<Vec<String>, TomlError> {
        let mut parts = Vec::new();
        loop {
            self.skip_spaces();
            let part = match self.peek() {
                Some(b'"') => self.basic_string()?,
                Some(b'\'') => self.literal_string()?,
                Some(byte) if is_bare_key(byte) => {
                    let start = self.position;
                    while matches!(self.peek(), Some(value) if is_bare_key(value)) {
                        self.bump();
                    }
                    String::from_utf8_lossy(&self.bytes[start..self.position]).into_owned()
                }
                _ => return Err(self.error("se esperaba una clave")),
            };
            parts.push(part);
            if self.peek() == Some(b'.') {
                self.bump();
                continue;
            }
            return Ok(parts);
        }
    }

    fn expect_word(&mut self, word: &str) -> Result<(), TomlError> {
        let bytes = word.as_bytes();
        if self.bytes[self.position..].starts_with(bytes) {
            self.position += bytes.len();
            return Ok(());
        }
        Err(self.error(format!("se esperaba `{word}`")))
    }

    fn expect(&mut self, byte: u8) -> Result<(), TomlError> {
        if self.peek() == Some(byte) {
            self.bump();
            return Ok(());
        }
        Err(self.error(format!("se esperaba `{}`", char::from(byte))))
    }

    fn finish_line(&mut self) -> Result<(), TomlError> {
        self.skip_spaces();
        if self.at_end() {
            return Ok(());
        }
        match self.peek() {
            Some(b'\n') => {
                self.bump();
                Ok(())
            }
            Some(b'#') => {
                self.skip_comment();
                self.skip_spaces();
                if self.at_end() {
                    return Ok(());
                }
                if self.peek() == Some(b'\n') {
                    self.bump();
                    return Ok(());
                }
                Err(self.error("contenido inesperado tras el comentario"))
            }
            Some(byte) => Err(self.error(format!("contenido inesperado `{}`", char::from(byte)))),
            None => Ok(()),
        }
    }

    fn skip_trivia(&mut self) {
        loop {
            self.skip_spaces();
            match self.peek() {
                Some(b'#') => self.skip_comment(),
                Some(b'\n') => {
                    self.bump();
                }
                _ => return,
            }
        }
    }

    fn skip_spaces(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\t' | b'\r')) {
            self.position += 1;
        }
    }

    fn skip_comment(&mut self) {
        while !matches!(self.peek(), Some(b'\n') | None) {
            self.position += 1;
        }
    }

    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.position).copied()
    }

    fn bump(&mut self) {
        if self.peek() == Some(b'\n') {
            self.line += 1;
        }
        self.position += 1;
    }

    fn at_end(&self) -> bool {
        self.position >= self.bytes.len()
    }

    fn error(&self, message: impl Into<String>) -> TomlError {
        TomlError {
            line: self.line,
            message: message.into(),
        }
    }
}

fn is_bare_key(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-')
}

fn insert_path(
    table: &mut Table,
    path: &[String],
    value: Value,
    line: usize,
) -> Result<(), TomlError> {
    let (last, parents) = path.split_last().ok_or_else(|| TomlError {
        line,
        message: "clave vacía".to_owned(),
    })?;
    let mut current = table;
    for part in parents {
        let entry = current
            .entry(part.clone())
            .or_insert_with(|| Value::Table(Table::new()));
        current = match entry {
            Value::Table(inner) => inner,
            _ => {
                return Err(TomlError {
                    line,
                    message: format!("`{part}` no es una tabla"),
                });
            }
        };
    }
    if current.insert(last.clone(), value).is_some() {
        return Err(TomlError {
            line,
            message: format!("clave duplicada `{last}`"),
        });
    }
    Ok(())
}

/// Recorre `path` creando tablas; si el último tramo es un array de tablas, entra en su
/// último elemento.
fn table_at<'a>(
    root: &'a mut Table,
    path: &[String],
    line: usize,
) -> Result<&'a mut Table, TomlError> {
    let mut current = root;
    for part in path {
        let entry = current
            .entry(part.clone())
            .or_insert_with(|| Value::Table(Table::new()));
        current = match entry {
            Value::Table(inner) => inner,
            Value::Array(items) => match items.last_mut() {
                Some(Value::Table(inner)) => inner,
                _ => {
                    return Err(TomlError {
                        line,
                        message: format!("`{part}` no es una tabla"),
                    });
                }
            },
            _ => {
                return Err(TomlError {
                    line,
                    message: format!("`{part}` no es una tabla"),
                });
            }
        };
    }
    Ok(current)
}

fn ensure_table(root: &mut Table, path: &[String], line: usize) -> Result<(), TomlError> {
    let (last, parents) = path.split_last().ok_or_else(|| TomlError {
        line,
        message: "tabla sin nombre".to_owned(),
    })?;
    let table = table_at(root, parents, line)?;
    match table.get(last.as_str()) {
        Some(Value::Table(_)) => Ok(()),
        Some(_) => Err(TomlError {
            line,
            message: format!("`{last}` ya existe y no es una tabla"),
        }),
        None => {
            table.insert(last.clone(), Value::Table(Table::new()));
            Ok(())
        }
    }
}

fn push_array_table(root: &mut Table, path: &[String], line: usize) -> Result<(), TomlError> {
    let (last, parents) = path.split_last().ok_or_else(|| TomlError {
        line,
        message: "tabla sin nombre".to_owned(),
    })?;
    let table = table_at(root, parents, line)?;
    match table.get_mut(last.as_str()) {
        Some(Value::Array(items)) => {
            items.push(Value::Table(Table::new()));
            Ok(())
        }
        Some(_) => Err(TomlError {
            line,
            message: format!("`{last}` ya existe y no es un array de tablas"),
        }),
        None => {
            table.insert(last.clone(), Value::Array(vec![Value::Table(Table::new())]));
            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lee_tablas_arrays_y_comentarios() {
        let source = r#"
# comentario
version = 1

[[package]]
name = "json"
version = "0.3.1"
source = "git+https://example.com/json?tag=v1"
commit = "9f1c"
features = ["std", "extra"]
dependencies = []

[[package]]
name = "text"
version = "1.2.3"
source = "git+https://example.com/text?rev=4a7d"
commit = "4a7d"

[meta]
cuenta = 3
activo = true
inline = { a = 1, b = "dos" }
"#;
        let table = parse(source).expect("parse");
        assert_eq!(table["version"].as_integer(), Some(1));
        let packages = table["package"].as_array().expect("array");
        assert_eq!(packages.len(), 2);
        let first = packages[0].as_table().expect("tabla");
        assert_eq!(first["name"].as_str(), Some("json"));
        assert_eq!(
            first["features"].as_array().expect("features"),
            [Value::String("std".into()), Value::String("extra".into())]
        );
        let meta = table["meta"].as_table().expect("meta");
        assert_eq!(meta["cuenta"].as_integer(), Some(3));
        assert_eq!(meta["activo"], Value::Bool(true));
        let inline = meta["inline"].as_table().expect("inline");
        assert_eq!(inline["b"].as_str(), Some("dos"));
    }

    #[test]
    fn arrays_multilinea_y_anidados() {
        let table = parse("x = [\n  [1, 2],\n  [3],\n]\n").expect("parse");
        let rows = table["x"].as_array().expect("array");
        assert_eq!(rows.len(), 2);
        assert_eq!(rows[1].as_array().expect("fila")[0].as_integer(), Some(3));
    }

    #[test]
    fn rechaza_basura() {
        assert!(parse("name =\n").is_err());
        assert!(parse("[tabla\n").is_err());
        assert!(parse("clave = 1.5\n").is_err());
        assert!(parse("x = \"sin cerrar\n").is_err());
        assert!(parse("x = 1\nx = 2\n").is_err());
    }

    #[test]
    fn cadenas_con_escapes_y_almohadillas() {
        let table = parse("url = \"a#b\\nc\"\n").expect("parse");
        assert_eq!(table["url"].as_str(), Some("a#b\nc"));
    }
}
