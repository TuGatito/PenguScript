//! JSON mínimo compartido por el LSP (JSON-RPC) y el driver de build (mensajes de Cargo).
//!
//! El parser es iterativo-recursivo con límite de profundidad, acepta los escapes
//! de la RFC 8259 (incluidos pares sustitutos) y distingue enteros de flotantes
//! para no perder precisión en los `id` del protocolo.

use std::collections::BTreeMap;
use std::fmt;
use std::fmt::Write as _;

/// Valor JSON.
#[derive(Clone, Debug, PartialEq)]
pub enum Value {
    /// `null`.
    Null,
    /// Booleano.
    Bool(bool),
    /// Entero de 64 bits.
    Int(i64),
    /// Flotante.
    Float(f64),
    /// Cadena.
    Str(String),
    /// Array.
    Array(Vec<Value>),
    /// Objeto con claves ordenadas.
    Object(BTreeMap<String, Value>),
}

impl Value {
    /// Construye un objeto a partir de pares.
    #[must_use]
    pub fn object(entries: impl IntoIterator<Item = (impl Into<String>, Value)>) -> Self {
        let mut map = BTreeMap::new();
        for (key, value) in entries {
            map.insert(key.into(), value);
        }
        Self::Object(map)
    }

    /// Devuelve el valor de la clave si es un objeto.
    #[must_use]
    pub fn get(&self, key: &str) -> Option<&Self> {
        match self {
            Self::Object(map) => map.get(key),
            _ => None,
        }
    }

    /// Acceso encadenado por claves.
    #[must_use]
    pub fn path(&self, keys: &[&str]) -> Option<&Self> {
        let mut current = self;
        for key in keys {
            current = current.get(key)?;
        }
        Some(current)
    }

    /// Cadena, si lo es.
    #[must_use]
    pub fn as_str(&self) -> Option<&str> {
        match self {
            Self::Str(text) => Some(text),
            _ => None,
        }
    }

    /// Entero, si lo es.
    #[must_use]
    pub fn as_i64(&self) -> Option<i64> {
        match self {
            Self::Int(number) => Some(*number),
            _ => None,
        }
    }

    /// Flotante, si lo es (también acepta enteros).
    #[must_use]
    #[allow(clippy::cast_precision_loss)]
    pub fn as_f64(&self) -> Option<f64> {
        match self {
            Self::Float(number) => Some(*number),
            Self::Int(number) => Some(*number as f64),
            _ => None,
        }
    }

    /// Booleano, si lo es.
    #[must_use]
    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Self::Bool(value) => Some(*value),
            _ => None,
        }
    }

    /// Array, si lo es.
    #[must_use]
    pub fn as_array(&self) -> Option<&[Self]> {
        match self {
            Self::Array(values) => Some(values),
            _ => None,
        }
    }

    /// Objeto, si lo es.
    #[must_use]
    pub fn as_object(&self) -> Option<&BTreeMap<String, Self>> {
        match self {
            Self::Object(map) => Some(map),
            _ => None,
        }
    }

    /// `true` si es `null`.
    #[must_use]
    pub fn is_null(&self) -> bool {
        matches!(self, Self::Null)
    }
}

impl From<&str> for Value {
    fn from(value: &str) -> Self {
        Self::Str(value.to_owned())
    }
}

impl From<String> for Value {
    fn from(value: String) -> Self {
        Self::Str(value)
    }
}

impl From<bool> for Value {
    fn from(value: bool) -> Self {
        Self::Bool(value)
    }
}

impl From<i64> for Value {
    fn from(value: i64) -> Self {
        Self::Int(value)
    }
}

impl From<u32> for Value {
    fn from(value: u32) -> Self {
        Self::Int(i64::from(value))
    }
}

impl From<usize> for Value {
    fn from(value: usize) -> Self {
        Self::Int(i64::try_from(value).unwrap_or(i64::MAX))
    }
}

/// Error de parseo con desplazamiento en bytes.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct JsonError {
    /// Desplazamiento donde falló el parseo.
    pub offset: usize,
    /// Mensaje legible.
    pub message: String,
}

impl fmt::Display for JsonError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "JSON inválido en {}: {}",
            self.offset, self.message
        )
    }
}

impl std::error::Error for JsonError {}

/// Profundidad máxima de anidamiento aceptada.
const MAX_DEPTH: usize = 128;

/// Parsea un documento JSON completo.
///
/// # Errors
/// Devuelve [`JsonError`] si el texto no es JSON válido o supera la profundidad.
pub fn parse(text: &str) -> Result<Value, JsonError> {
    let mut parser = Parser {
        text,
        bytes: text.as_bytes(),
        position: 0,
    };
    parser.skip_whitespace();
    let value = parser.value(0)?;
    parser.skip_whitespace();
    if parser.position != parser.bytes.len() {
        return Err(parser.error("texto sobrante tras el valor"));
    }
    Ok(value)
}

struct Parser<'a> {
    text: &'a str,
    bytes: &'a [u8],
    position: usize,
}

impl Parser<'_> {
    fn error(&self, message: &str) -> JsonError {
        JsonError {
            offset: self.position,
            message: message.to_owned(),
        }
    }

    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.position).copied()
    }

    fn skip_whitespace(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\t' | b'\n' | b'\r')) {
            self.position += 1;
        }
    }

    fn expect(&mut self, byte: u8) -> Result<(), JsonError> {
        if self.peek() == Some(byte) {
            self.position += 1;
            Ok(())
        } else {
            Err(self.error(&format!("se esperaba `{}`", byte as char)))
        }
    }

    fn value(&mut self, depth: usize) -> Result<Value, JsonError> {
        if depth > MAX_DEPTH {
            return Err(self.error("anidamiento excesivo"));
        }
        match self.peek() {
            Some(b'n') => {
                self.literal("null")?;
                Ok(Value::Null)
            }
            Some(b't') => {
                self.literal("true")?;
                Ok(Value::Bool(true))
            }
            Some(b'f') => {
                self.literal("false")?;
                Ok(Value::Bool(false))
            }
            Some(b'"') => Ok(Value::Str(self.string()?)),
            Some(b'[') => self.array(depth),
            Some(b'{') => self.object(depth),
            Some(b'-' | b'0'..=b'9') => self.number(),
            _ => Err(self.error("valor inesperado")),
        }
    }

    fn literal(&mut self, text: &str) -> Result<(), JsonError> {
        if self
            .bytes
            .get(self.position..self.position + text.len())
            .is_some_and(|slice| slice == text.as_bytes())
        {
            self.position += text.len();
            Ok(())
        } else {
            Err(self.error(&format!("se esperaba `{text}`")))
        }
    }

    fn array(&mut self, depth: usize) -> Result<Value, JsonError> {
        self.expect(b'[')?;
        let mut values = Vec::new();
        self.skip_whitespace();
        if self.peek() == Some(b']') {
            self.position += 1;
            return Ok(Value::Array(values));
        }
        loop {
            self.skip_whitespace();
            values.push(self.value(depth + 1)?);
            self.skip_whitespace();
            match self.peek() {
                Some(b',') => self.position += 1,
                Some(b']') => {
                    self.position += 1;
                    return Ok(Value::Array(values));
                }
                _ => return Err(self.error("se esperaba `,` o `]`")),
            }
        }
    }

    fn object(&mut self, depth: usize) -> Result<Value, JsonError> {
        self.expect(b'{')?;
        let mut map = BTreeMap::new();
        self.skip_whitespace();
        if self.peek() == Some(b'}') {
            self.position += 1;
            return Ok(Value::Object(map));
        }
        loop {
            self.skip_whitespace();
            let key = self.string()?;
            self.skip_whitespace();
            self.expect(b':')?;
            self.skip_whitespace();
            let value = self.value(depth + 1)?;
            map.insert(key, value);
            self.skip_whitespace();
            match self.peek() {
                Some(b',') => self.position += 1,
                Some(b'}') => {
                    self.position += 1;
                    return Ok(Value::Object(map));
                }
                _ => return Err(self.error("se esperaba `,` o `}`")),
            }
        }
    }

    fn number(&mut self) -> Result<Value, JsonError> {
        let start = self.position;
        if self.peek() == Some(b'-') {
            self.position += 1;
        }
        let digits_start = self.position;
        while matches!(self.peek(), Some(b'0'..=b'9')) {
            self.position += 1;
        }
        if self.position == digits_start {
            return Err(self.error("se esperaban dígitos"));
        }
        let mut float = false;
        if self.peek() == Some(b'.') {
            float = true;
            self.position += 1;
            let fraction_start = self.position;
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.position += 1;
            }
            if self.position == fraction_start {
                return Err(self.error("se esperaban decimales"));
            }
        }
        if matches!(self.peek(), Some(b'e' | b'E')) {
            float = true;
            self.position += 1;
            if matches!(self.peek(), Some(b'+' | b'-')) {
                self.position += 1;
            }
            let exponent_start = self.position;
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.position += 1;
            }
            if self.position == exponent_start {
                return Err(self.error("se esperaba el exponente"));
            }
        }
        let text = std::str::from_utf8(&self.bytes[start..self.position])
            .map_err(|_| self.error("número no UTF-8"))?;
        if float {
            text.parse::<f64>()
                .map(Value::Float)
                .map_err(|_| self.error("flotante fuera de rango"))
        } else {
            text.parse::<i64>()
                .map(Value::Int)
                .map_err(|_| self.error("entero fuera de rango"))
        }
    }

    fn string(&mut self) -> Result<String, JsonError> {
        self.expect(b'"')?;
        let mut out = String::new();
        loop {
            let Some(byte) = self.peek() else {
                return Err(self.error("cadena sin cerrar"));
            };
            match byte {
                b'"' => {
                    self.position += 1;
                    return Ok(out);
                }
                b'\\' => {
                    self.position += 1;
                    self.escape(&mut out)?;
                }
                0x00..=0x1F => return Err(self.error("carácter de control en la cadena")),
                _ => {
                    if byte < 0x80 {
                        out.push(char::from(byte));
                        self.position += 1;
                    } else {
                        let character = self.text[self.position..]
                            .chars()
                            .next()
                            .expect("cadena no vacía");
                        out.push(character);
                        self.position += character.len_utf8();
                    }
                }
            }
        }
    }

    fn escape(&mut self, out: &mut String) -> Result<(), JsonError> {
        let Some(byte) = self.peek() else {
            return Err(self.error("escape sin terminar"));
        };
        self.position += 1;
        let character = match byte {
            b'"' => '"',
            b'\\' => '\\',
            b'/' => '/',
            b'b' => '\u{8}',
            b'f' => '\u{c}',
            b'n' => '\n',
            b'r' => '\r',
            b't' => '\t',
            b'u' => return self.unicode_escape(out),
            _ => return Err(self.error("escape desconocido")),
        };
        out.push(character);
        Ok(())
    }

    fn unicode_escape(&mut self, out: &mut String) -> Result<(), JsonError> {
        let code = self.hex4()?;
        if (0xD800..0xDC00).contains(&code) {
            if self.peek() != Some(b'\\') {
                return Err(self.error("falta el segundo par sustituto"));
            }
            self.position += 1;
            if self.peek() != Some(b'u') {
                return Err(self.error("falta `u` en el par sustituto"));
            }
            self.position += 1;
            let low = self.hex4()?;
            if !(0xDC00..0xE000).contains(&low) {
                return Err(self.error("par sustituto inválido"));
            }
            let combined = 0x1_0000 + ((code - 0xD800) << 10) + (low - 0xDC00);
            out.push(char::from_u32(combined).ok_or_else(|| self.error("escalar inválido"))?);
        } else if (0xDC00..0xE000).contains(&code) {
            return Err(self.error("sustituto bajo sin alto"));
        } else {
            out.push(char::from_u32(code).ok_or_else(|| self.error("escalar inválido"))?);
        }
        Ok(())
    }

    fn hex4(&mut self) -> Result<u32, JsonError> {
        let mut code = 0_u32;
        for _ in 0..4 {
            let Some(byte) = self.peek() else {
                return Err(self.error("escape unicode incompleto"));
            };
            let digit = match byte {
                b'0'..=b'9' => u32::from(byte - b'0'),
                b'a'..=b'f' => u32::from(byte - b'a') + 10,
                b'A'..=b'F' => u32::from(byte - b'A') + 10,
                _ => return Err(self.error("dígito hexadecimal inválido")),
            };
            code = code * 16 + digit;
            self.position += 1;
        }
        Ok(code)
    }
}

/// Serializa compacto y determinista (claves de objeto ordenadas).
#[must_use]
pub fn render(value: &Value) -> String {
    let mut out = String::new();
    render_into(value, &mut out);
    out
}

fn render_into(value: &Value, out: &mut String) {
    match value {
        Value::Null => out.push_str("null"),
        Value::Bool(true) => out.push_str("true"),
        Value::Bool(false) => out.push_str("false"),
        Value::Int(number) => out.push_str(&number.to_string()),
        Value::Float(number) => {
            if number.is_finite() {
                out.push_str(&number.to_string());
            } else {
                out.push_str("null");
            }
        }
        Value::Str(text) => render_string(text, out),
        Value::Array(values) => {
            out.push('[');
            for (index, item) in values.iter().enumerate() {
                if index > 0 {
                    out.push(',');
                }
                render_into(item, out);
            }
            out.push(']');
        }
        Value::Object(map) => {
            out.push('{');
            for (index, (key, item)) in map.iter().enumerate() {
                if index > 0 {
                    out.push(',');
                }
                render_string(key, out);
                out.push(':');
                render_into(item, out);
            }
            out.push('}');
        }
    }
}

fn render_string(text: &str, out: &mut String) {
    out.push('"');
    for character in text.chars() {
        match character {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            character if (character as u32) < 0x20 => {
                out.push_str("\\u");
                let _ = write!(out, "{:04x}", u32::from(character));
            }
            character => out.push(character),
        }
    }
    out.push('"');
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parsea_objetos_arrays_y_escalares() {
        let value = parse(r#"{"id":1,"ok":true,"items":[1,-2,3.5,"x",null]}"#).expect("json");
        assert_eq!(value.get("id").and_then(Value::as_i64), Some(1));
        assert_eq!(value.get("ok").and_then(Value::as_bool), Some(true));
        let items = value.get("items").and_then(Value::as_array).expect("array");
        assert_eq!(items.len(), 5);
        assert_eq!(items[2].as_f64(), Some(3.5));
        assert!(items[4].is_null());
    }

    #[test]
    fn acepta_escapes_y_pares_sustitutos() {
        let value = parse(r#""a\nb\t\"c\\\u00e9\ud83d\ude00""#).expect("json");
        assert_eq!(value.as_str(), Some("a\nb\t\"c\\é😀"));
    }

    #[test]
    fn rechaza_control_y_basura() {
        assert!(parse("\"a\u{1}b\"").is_err());
        assert!(parse("{} x").is_err());
        assert!(parse("[1,]").is_err());
    }

    #[test]
    fn limita_la_profundidad() {
        let deep = format!("{}1{}", "[".repeat(200), "]".repeat(200));
        assert!(parse(&deep).is_err());
    }

    #[test]
    fn ida_y_vuelta_compacta() {
        let text = r#"{"a":[1,2,{"b":"x\ny"}],"c":true,"d":null}"#;
        let value = parse(text).expect("json");
        let rendered = render(&value);
        assert_eq!(parse(&rendered).expect("json"), value);
        assert!(!rendered.contains('\n'));
    }

    #[test]
    fn cadenas_largas_se_analizan_en_tiempo_lineal() {
        // 256 KiB de texto: con una implementación cuadrática tardaba > 1 s.
        let payload = "a".repeat(256 * 1024);
        let text = Value::object([("text", Value::from(payload.as_str()))]);
        let rendered = render(&text);
        let started = std::time::Instant::now();
        let parsed = parse(&rendered).expect("json");
        let elapsed = started.elapsed();
        assert_eq!(
            parsed.get("text").and_then(Value::as_str),
            Some(payload.as_str())
        );
        assert!(elapsed.as_millis() < 200, "tardó {elapsed:?}");
    }

    #[test]
    fn numeros_grandes_no_pierden_precision() {
        let value = parse("9007199254740993").expect("json");
        assert_eq!(value.as_i64(), Some(9_007_199_254_740_993));
    }
}
