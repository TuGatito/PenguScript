//! Identificadores estables de la representación intermedia.

macro_rules! id_type {
    ($name:ident, $doc:literal) => {
        #[doc = $doc]
        #[derive(Clone, Copy, Debug, Eq, PartialEq, Hash, Ord, PartialOrd)]
        pub struct $name(pub u32);

        impl $name {
            /// Primer identificador de esta clase.
            pub const FIRST: Self = Self(0);

            /// Índice entero.
            #[must_use]
            pub const fn index(self) -> usize {
                self.0 as usize
            }
        }

        impl std::fmt::Display for $name {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                self.0.fmt(f)
            }
        }
    };
}

id_type!(ModuleId, "Identificador de un módulo.");
id_type!(DefId, "Identificador global de una definición.");
id_type!(
    LocalId,
    "Identificador de un binding local dentro de un cuerpo."
);
id_type!(ScopeId, "Identificador de un scope.");
id_type!(BodyId, "Identificador de un cuerpo.");

/// Un item de módulo se identifica por su `DefId`.
pub type ItemId = DefId;
