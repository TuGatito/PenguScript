//! Envelopes JSON-RPC 2.0 usados por LSP.

use crate::json::Value;

/// Códigos de error JSON-RPC/LSP usados por el servidor.
pub mod codes {
    /// JSON mal formado.
    pub const PARSE_ERROR: i64 = -32700;
    /// Envelope inválido.
    pub const INVALID_REQUEST: i64 = -32600;
    /// Método no soportado.
    pub const METHOD_NOT_FOUND: i64 = -32601;
    /// Parámetros inválidos.
    pub const INVALID_PARAMS: i64 = -32602;
    /// Error interno.
    pub const INTERNAL_ERROR: i64 = -32603;
    /// Petición antes de `initialize`.
    pub const SERVER_NOT_INITIALIZED: i64 = -32002;
    /// Petición cancelada por el cliente.
    pub const REQUEST_CANCELLED: i64 = -32800;
    /// Contenido modificado; el cliente debe repetir la petición.
    pub const CONTENT_MODIFIED: i64 = -32801;
}

/// Identificador de petición.
#[derive(Clone, Debug, Eq, PartialEq, Hash, Ord, PartialOrd)]
pub enum Id {
    /// Numérico.
    Int(i64),
    /// Cadena.
    Str(String),
}

impl Id {
    /// Convierte a JSON.
    #[must_use]
    pub fn to_value(&self) -> Value {
        match self {
            Self::Int(number) => Value::Int(*number),
            Self::Str(text) => Value::Str(text.clone()),
        }
    }

    /// Interpreta un `id` de JSON.
    #[must_use]
    pub fn from_value(value: &Value) -> Option<Self> {
        Self::parse(value)
    }

    fn parse(value: &Value) -> Option<Self> {
        match value {
            Value::Int(number) => Some(Self::Int(*number)),
            Value::Str(text) => Some(Self::Str(text.clone())),
            _ => None,
        }
    }
}

/// Error JSON-RPC.
#[derive(Clone, Debug)]
pub struct RpcError {
    /// Código.
    pub code: i64,
    /// Mensaje.
    pub message: String,
    /// Datos opcionales.
    pub data: Option<Value>,
}

impl RpcError {
    /// Error con código y mensaje.
    #[must_use]
    pub fn new(code: i64, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
            data: None,
        }
    }

    /// Añade datos estructurados.
    #[must_use]
    pub fn with_data(mut self, data: Value) -> Self {
        self.data = Some(data);
        self
    }
}

/// Mensaje entrante del cliente.
#[derive(Clone, Debug)]
pub enum Incoming {
    /// Petición con `id`.
    Request {
        /// Identificador.
        id: Id,
        /// Método.
        method: String,
        /// Parámetros.
        params: Value,
    },
    /// Notificación sin `id`.
    Notification {
        /// Método.
        method: String,
        /// Parámetros.
        params: Value,
    },
    /// Respuesta del cliente a una petición nuestra (no usada en Fase 6).
    Response {
        /// Identificador.
        id: Option<Id>,
    },
    /// Envelope inválido sin `id` útil.
    Invalid,
}

/// Parsea un mensaje del cliente.
///
/// # Errors
/// Devuelve error si el objeto no es un envelope JSON-RPC válido.
pub fn parse_incoming(value: &Value) -> Result<Incoming, RpcError> {
    let Some(object) = value.as_object() else {
        return Err(RpcError::new(
            codes::INVALID_REQUEST,
            "el mensaje no es un objeto JSON",
        ));
    };
    if object.get("jsonrpc").and_then(Value::as_str) != Some("2.0") {
        return Err(RpcError::new(
            codes::INVALID_REQUEST,
            "falta `jsonrpc: \"2.0\"`",
        ));
    }
    let id = object.get("id").and_then(Id::parse);
    let method = object
        .get("method")
        .and_then(Value::as_str)
        .map(str::to_owned);
    let params = object.get("params").cloned().unwrap_or(Value::Null);
    match (id, method) {
        (Some(id), Some(method)) => Ok(Incoming::Request { id, method, params }),
        (None, Some(method)) => Ok(Incoming::Notification { method, params }),
        (id, None) => Ok(Incoming::Response { id }),
    }
}

/// Envelope de respuesta correcta.
#[must_use]
pub fn response(id: &Id, result: Value) -> Value {
    Value::object([
        ("jsonrpc", Value::from("2.0")),
        ("id", id.to_value()),
        ("result", result),
    ])
}

/// Envelope de respuesta con error.
#[must_use]
pub fn error_response(id: &Id, error: &RpcError) -> Value {
    let mut payload = vec![
        ("code", Value::Int(error.code)),
        ("message", Value::from(error.message.as_str())),
    ];
    if let Some(data) = &error.data {
        payload.push(("data", data.clone()));
    }
    Value::object([
        ("jsonrpc", Value::from("2.0")),
        ("id", id.to_value()),
        ("error", Value::object(payload)),
    ])
}

/// Notificación del servidor.
#[must_use]
pub fn notification(method: &str, params: Value) -> Value {
    Value::object([
        ("jsonrpc", Value::from("2.0")),
        ("method", Value::from(method)),
        ("params", params),
    ])
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::json;

    fn parse(text: &str) -> Incoming {
        parse_incoming(&json::parse(text).expect("json")).expect("envelope")
    }

    #[test]
    fn distingue_peticiones_y_notificaciones() {
        let request = parse(r#"{"jsonrpc":"2.0","id":7,"method":"initialize","params":{}}"#);
        match request {
            Incoming::Request { id, method, .. } => {
                assert_eq!(id, Id::Int(7));
                assert_eq!(method, "initialize");
            }
            other => panic!("{other:?}"),
        }
        let notification = parse(r#"{"jsonrpc":"2.0","method":"initialized"}"#);
        assert!(matches!(notification, Incoming::Notification { .. }));
    }

    #[test]
    fn acepta_ids_de_cadena() {
        let request = parse(r#"{"jsonrpc":"2.0","id":"abc","method":"shutdown"}"#);
        match request {
            Incoming::Request { id, .. } => assert_eq!(id, Id::Str("abc".to_owned())),
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn rechaza_envelopes_invalidos() {
        let value = json::parse(r#"{"id":1,"method":"x"}"#).expect("json");
        let error = parse_incoming(&value).expect_err("error");
        assert_eq!(error.code, codes::INVALID_REQUEST);
        let value = json::parse("[]").expect("json");
        assert!(parse_incoming(&value).is_err());
    }

    #[test]
    fn renderiza_respuestas_y_errores() {
        let ok = response(&Id::Int(1), Value::Null);
        assert_eq!(
            json::render(&ok),
            r#"{"id":1,"jsonrpc":"2.0","result":null}"#
        );
        let error = error_response(&Id::Int(2), &RpcError::new(codes::METHOD_NOT_FOUND, "no"));
        let text = json::render(&error);
        assert!(text.contains("\"code\":-32601"));
        assert!(text.contains("\"message\":\"no\""));
    }
}
