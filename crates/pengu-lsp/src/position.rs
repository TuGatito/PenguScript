//! Conversión entre desplazamientos UTF-8 e posiciones LSP.

/// Codificación de posición negociada con el cliente.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum Encoding {
    /// `character` cuenta bytes UTF-8 (LSP 3.17).
    Utf8,
    /// `character` cuenta unidades UTF-16 (valor por defecto del protocolo).
    #[default]
    Utf16,
}

impl Encoding {
    /// Nombre del protocolo.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Utf8 => "utf-8",
            Self::Utf16 => "utf-16",
        }
    }
}

/// Posición LSP: línea y carácter, ambos 0-based.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct Position {
    /// Línea, 0-based.
    pub line: u32,
    /// Carácter, 0-based, en la codificación negociada.
    pub character: u32,
}

/// Rango LSP: inicio inclusivo y fin exclusivo.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct Range {
    /// Inicio.
    pub start: Position,
    /// Fin.
    pub end: Position,
}

impl Position {
    /// Forma JSON que espera el protocolo.
    #[must_use]
    pub fn to_json(self) -> crate::json::Value {
        crate::json::Value::object([
            ("line", crate::json::Value::Int(i64::from(self.line))),
            (
                "character",
                crate::json::Value::Int(i64::from(self.character)),
            ),
        ])
    }
}

impl Range {
    /// Forma JSON que espera el protocolo.
    #[must_use]
    pub fn to_json(self) -> crate::json::Value {
        crate::json::Value::object([("start", self.start.to_json()), ("end", self.end.to_json())])
    }

    /// Construye un rango.
    #[must_use]
    pub const fn new(start: Position, end: Position) -> Self {
        Self { start, end }
    }

    /// `true` si el rango está vacío.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.start == self.end
    }
}

/// Índice de inicios de línea de un texto.
#[derive(Clone, Debug, Default)]
pub struct LineIndex {
    starts: Vec<u32>,
    length: u32,
}

impl LineIndex {
    /// Construye el índice de un texto.
    #[must_use]
    pub fn new(text: &str) -> Self {
        let mut starts = vec![0_u32];
        for (offset, byte) in text.bytes().enumerate() {
            if byte == b'\n' {
                starts.push(u32::try_from(offset + 1).unwrap_or(u32::MAX));
            }
        }
        Self {
            starts,
            length: u32::try_from(text.len()).unwrap_or(u32::MAX),
        }
    }

    /// Número de líneas.
    #[must_use]
    pub fn line_count(&self) -> u32 {
        u32::try_from(self.starts.len()).unwrap_or(u32::MAX)
    }

    /// Desplazamiento del inicio de una línea 0-based.
    #[must_use]
    pub fn line_start(&self, line: u32) -> u32 {
        self.starts
            .get(usize::try_from(line).unwrap_or(usize::MAX))
            .copied()
            .unwrap_or(self.length)
    }

    /// Longitud total del texto.
    #[must_use]
    pub fn len(&self) -> u32 {
        self.length
    }

    /// `true` si el texto está vacío.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.length == 0
    }

    /// Convierte un desplazamiento en posición.
    #[must_use]
    pub fn position(&self, text: &str, offset: u32) -> Position {
        self.position_with(text, offset, Encoding::Utf16)
    }

    /// Convierte un desplazamiento en posición con la codificación dada.
    #[must_use]
    pub fn position_with(&self, text: &str, offset: u32, encoding: Encoding) -> Position {
        let offset = offset.min(self.length);
        let line = match self.starts.binary_search(&offset) {
            Ok(index) => index,
            Err(index) => index.saturating_sub(1),
        };
        let start = self.line_start(u32::try_from(line).unwrap_or(u32::MAX));
        Position {
            line: u32::try_from(line).unwrap_or(u32::MAX),
            character: character_units(text, start, offset, encoding),
        }
    }

    /// Convierte una posición en desplazamiento, recortando al borde de carácter.
    #[must_use]
    pub fn offset(&self, text: &str, position: Position, encoding: Encoding) -> u32 {
        if position.line >= self.line_count() {
            return self.length;
        }
        let start = self.line_start(position.line);
        let end = if position.line + 1 < self.line_count() {
            self.line_start(position.line + 1)
        } else {
            self.length
        };
        if encoding == Encoding::Utf8 {
            let mut offset = start.saturating_add(position.character).min(end);
            while offset < end && !text.is_char_boundary(usize::try_from(offset).unwrap_or(0)) {
                offset += 1;
            }
            return offset;
        }
        let slice = char_slice(text, start, end);
        let mut units = 0_u32;
        let mut bytes = 0_u32;
        for character in slice.chars() {
            let width = u32::try_from(character.len_utf16()).unwrap_or(1);
            if units + width > position.character {
                break;
            }
            units += width;
            bytes = bytes.saturating_add(u32::try_from(character.len_utf8()).unwrap_or(1));
        }
        start.saturating_add(bytes).min(end)
    }
}

fn char_slice(text: &str, start: u32, end: u32) -> &str {
    let start = usize::try_from(start).unwrap_or(usize::MAX);
    let end = usize::try_from(end).unwrap_or(usize::MAX);
    if start <= end && end <= text.len() {
        text.get(start..end).unwrap_or("")
    } else {
        ""
    }
}

fn character_units(text: &str, start: u32, offset: u32, encoding: Encoding) -> u32 {
    if offset <= start {
        return 0;
    }
    match encoding {
        Encoding::Utf8 => offset - start,
        Encoding::Utf16 => {
            let slice = char_slice(text, start, offset);
            u32::try_from(slice.chars().map(char::len_utf16).sum::<usize>()).unwrap_or(u32::MAX)
        }
    }
}

#[cfg(test)]
#[allow(clippy::cast_possible_truncation)]
mod tests {
    use super::*;

    const TEXT: &str = "hola\nmundo 😀\nfinal";

    #[test]
    fn indexa_lineas() {
        let index = LineIndex::new(TEXT);
        assert_eq!(index.line_count(), 3);
        assert_eq!(index.line_start(0), 0);
        assert_eq!(index.line_start(1), 5);
        assert_eq!(index.line_start(2), 16);
    }

    #[test]
    fn convierte_offsets_a_posiciones_utf16() {
        let index = LineIndex::new(TEXT);
        let emoji = TEXT.find('😀').expect("emoji") as u32;
        let position = index.position_with(TEXT, emoji, Encoding::Utf16);
        assert_eq!(
            position,
            Position {
                line: 1,
                character: 6
            }
        );
        let after = index.position_with(TEXT, emoji + 4, Encoding::Utf16);
        assert_eq!(
            after,
            Position {
                line: 1,
                character: 8
            }
        );
    }

    #[test]
    fn convierte_posiciones_a_offsets_y_vuelve() {
        let index = LineIndex::new(TEXT);
        let emoji = TEXT.find('😀').expect("emoji") as u32;
        for offset in 0..=TEXT.len() as u32 {
            if !TEXT.is_char_boundary(offset as usize) {
                continue;
            }
            for encoding in [Encoding::Utf8, Encoding::Utf16] {
                let position = index.position_with(TEXT, offset, encoding);
                let back = index.offset(TEXT, position, encoding);
                assert_eq!(back, offset, "offset {offset} en {encoding:?}");
            }
        }
        // Un desplazamiento dentro de un carácter se recorta al borde siguiente.
        let inside = emoji + 1;
        let position = index.position_with(TEXT, inside, Encoding::Utf8);
        assert_eq!(index.offset(TEXT, position, Encoding::Utf8), emoji + 4);
        assert_eq!(
            index.offset(
                TEXT,
                Position {
                    line: 1,
                    character: 6
                },
                Encoding::Utf16
            ),
            emoji
        );
    }

    #[test]
    fn recorta_lineas_fuera_de_rango() {
        let index = LineIndex::new(TEXT);
        let offset = index.offset(
            TEXT,
            Position {
                line: 99,
                character: 0,
            },
            Encoding::Utf16,
        );
        assert_eq!(offset, TEXT.len() as u32);
    }

    #[test]
    fn texto_vacio() {
        let index = LineIndex::new("");
        assert_eq!(index.line_count(), 1);
        assert_eq!(index.len(), 0);
        assert_eq!(
            index.position_with("", 0, Encoding::Utf16),
            Position::default()
        );
    }
}
