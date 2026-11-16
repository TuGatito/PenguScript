//! Framing de mensajes LSP (`Content-Length`) sobre flujos binarios.

use std::io::{self, BufRead, Write};

/// Tamaño máximo aceptado para un mensaje (64 MiB).
pub const MAX_MESSAGE_BYTES: usize = 64 * 1024 * 1024;

/// Error de framing.
#[derive(Debug)]
pub enum FrameError {
    /// El flujo terminó limpiamente entre mensajes.
    Closed,
    /// Cabecera o cuerpo inválidos.
    Protocol(String),
    /// Error de E/S.
    Io(io::Error),
}

impl std::fmt::Display for FrameError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Closed => formatter.write_str("flujo cerrado"),
            Self::Protocol(message) => write!(formatter, "protocolo inválido: {message}"),
            Self::Io(error) => write!(formatter, "error de E/S: {error}"),
        }
    }
}

impl std::error::Error for FrameError {}

impl From<io::Error> for FrameError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

/// Lee un mensaje completo. Devuelve `None` si el flujo terminó limpiamente.
///
/// # Errors
/// Devuelve error si las cabeceras son inválidas, falta `Content-Length`, el
/// cuerpo no es UTF-8 o el mensaje supera [`MAX_MESSAGE_BYTES`].
pub fn read_message(reader: &mut impl BufRead) -> Result<Option<String>, FrameError> {
    let mut length: Option<usize> = None;
    let mut saw_header = false;
    loop {
        let mut line = String::new();
        let read = read_line(reader, &mut line)?;
        if read == 0 {
            return if saw_header {
                Err(FrameError::Protocol("cabeceras sin cuerpo".to_owned()))
            } else {
                Ok(None)
            };
        }
        saw_header = true;
        let line = line.trim_end_matches(['\r', '\n']);
        if line.is_empty() {
            break;
        }
        let Some((name, value)) = line.split_once(':') else {
            return Err(FrameError::Protocol(format!("cabecera sin `:`: `{line}`")));
        };
        if name.eq_ignore_ascii_case("content-length") {
            let parsed = value.trim().parse::<usize>().map_err(|_| {
                FrameError::Protocol(format!("`Content-Length` inválido: `{}`", value.trim()))
            })?;
            if parsed > MAX_MESSAGE_BYTES {
                return Err(FrameError::Protocol(format!(
                    "mensaje de {parsed} bytes supera el límite de {MAX_MESSAGE_BYTES}"
                )));
            }
            length = Some(parsed);
        }
    }
    let Some(length) = length else {
        return Err(FrameError::Protocol(
            "falta la cabecera `Content-Length`".to_owned(),
        ));
    };
    let mut buffer = vec![0_u8; length];
    reader.read_exact(&mut buffer)?;
    String::from_utf8(buffer)
        .map_err(|_| FrameError::Protocol("el cuerpo no es UTF-8".to_owned()))
        .map(Some)
}

fn read_line(reader: &mut impl BufRead, line: &mut String) -> Result<usize, FrameError> {
    let mut bytes = Vec::new();
    let read = reader.read_until(b'\n', &mut bytes)?;
    if read == 0 {
        return Ok(0);
    }
    if bytes.len() > 8 * 1024 {
        return Err(FrameError::Protocol("cabecera demasiado larga".to_owned()));
    }
    let text = std::str::from_utf8(&bytes)
        .map_err(|_| FrameError::Protocol("cabecera no UTF-8".to_owned()))?;
    line.push_str(text);
    Ok(read)
}

/// Escribe un mensaje con su cabecera y vacía el búfer.
///
/// # Errors
/// Propaga errores de escritura del flujo.
pub fn write_message(writer: &mut impl Write, body: &str) -> io::Result<()> {
    write!(writer, "Content-Length: {}\r\n\r\n", body.len())?;
    writer.write_all(body.as_bytes())?;
    writer.flush()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    #[test]
    fn lee_un_mensaje_completo() {
        let mut stream = Cursor::new(b"Content-Length: 2\r\n\r\n{}".to_vec());
        let message = read_message(&mut stream).expect("mensaje").expect("alguno");
        assert_eq!(message, "{}");
    }

    #[test]
    fn acepta_cabeceras_en_minusculas_y_orden_inverso() {
        let raw = b"content-length: 7\r\nx-extra: 1\r\n\r\n{\"a\":1}".to_vec();
        let mut stream = Cursor::new(raw);
        let message = read_message(&mut stream).expect("mensaje").expect("alguno");
        assert_eq!(message, "{\"a\":1}");
    }

    #[test]
    fn lee_mensajes_concatenados_y_detecta_fin() {
        let mut raw = Vec::new();
        write_message(&mut raw, "{\"n\":1}").expect("escribir");
        write_message(&mut raw, "{\"n\":2}").expect("escribir");
        let mut stream = Cursor::new(raw);
        assert_eq!(
            read_message(&mut stream).expect("1").as_deref(),
            Some("{\"n\":1}")
        );
        assert_eq!(
            read_message(&mut stream).expect("2").as_deref(),
            Some("{\"n\":2}")
        );
        assert!(read_message(&mut stream).expect("fin").is_none());
    }

    #[test]
    fn exige_content_length() {
        let mut stream = Cursor::new(b"X: 1\r\n\r\n{}".to_vec());
        let error = read_message(&mut stream).expect_err("error");
        assert!(matches!(error, FrameError::Protocol(_)));
    }

    #[test]
    fn rechaza_tamano_excesivo() {
        let raw = format!("Content-Length: {}\r\n\r\n", MAX_MESSAGE_BYTES + 1);
        let mut stream = Cursor::new(raw.into_bytes());
        assert!(read_message(&mut stream).is_err());
    }

    #[test]
    fn escribe_cabecera_con_longitud_en_bytes() {
        let mut out = Vec::new();
        write_message(&mut out, "{\"t\":\"ñ\"}").expect("escribir");
        let text = String::from_utf8(out).expect("utf8");
        let expected = format!(
            "Content-Length: {}\r\n\r\n{{\"t\":\"ñ\"}}",
            "{\"t\":\"ñ\"}".len()
        );
        assert_eq!(text, expected);
    }
}
