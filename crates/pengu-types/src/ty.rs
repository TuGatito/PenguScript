//! Representación de tipos del checker.

use std::fmt;

use pengu_hir::DefId;

/// Tipo del núcleo.
#[derive(Clone, Debug, Eq, PartialEq, Hash)]
pub enum Ty {
    /// `Bool`.
    Bool,
    /// `Int` (i32).
    Int,
    /// `I8`.
    I8,
    /// `I16`.
    I16,
    /// `I32`.
    I32,
    /// `I64`.
    I64,
    /// `Isize`.
    Isize,
    /// `U8`.
    U8,
    /// `U16`.
    U16,
    /// `U32`.
    U32,
    /// `U64`.
    U64,
    /// `Usize`.
    Usize,
    /// `Float` (f64).
    Float,
    /// `F32`.
    F32,
    /// `F64`.
    F64,
    /// `Char`.
    Char,
    /// `String` owned.
    String,
    /// `Str` prestado.
    Str,
    /// `Unit`.
    Unit,
    /// `Never`.
    Never,
    /// Tupla.
    Tuple(Vec<Ty>),
    /// Array fijo.
    Array(Box<Ty>, u64),
    /// Slice prestado; el bool indica mutabilidad.
    Slice(Box<Ty>, bool),
    /// Referencia; el bool indica mutabilidad.
    Ref(Box<Ty>, bool),
    /// `Ptr[T]`, solo borde.
    Ptr(Box<Ty>),
    /// `Vec[T]`.
    Vec(Box<Ty>),
    /// `Map[K, V]`.
    Map(Box<Ty>, Box<Ty>),
    /// `Set[T]`.
    Set(Box<Ty>),
    /// `Option[T]`.
    Option(Box<Ty>),
    /// `Result[T, E]`.
    Result(Box<Ty>, Box<Ty>),
    /// `Box[T]`.
    Box(Box<Ty>),
    /// `Rc[T]`.
    Rc(Box<Ty>),
    /// `Arc[T]`.
    Arc(Box<Ty>),
    /// Tipo nominal definido en el crate.
    Adt(DefId, Vec<Ty>),
    /// Parámetro genérico.
    Generic(DefId),
    /// `CStr`.
    CStr,
    /// `CString`.
    CString,
    /// `Ordering`.
    Ordering,
    /// Tipo función.
    Fn(Vec<Ty>, Box<Ty>),
    /// Rango de un tipo.
    Range(Box<Ty>),
    /// Iterador perezoso de elementos `T`.
    Iterator(Box<Ty>),
    /// Variable de inferencia.
    Infer(u32),
    /// Variable de literal entero.
    IntVar(u32),
    /// Variable de literal flotante.
    FloatVar(u32),
    /// Error de tipo; evita cascadas.
    Error,
}

impl Ty {
    /// `true` si es un tipo entero.
    #[must_use]
    pub const fn is_integer(&self) -> bool {
        matches!(
            self,
            Self::Int
                | Self::I8
                | Self::I16
                | Self::I32
                | Self::I64
                | Self::Isize
                | Self::U8
                | Self::U16
                | Self::U32
                | Self::U64
                | Self::Usize
                | Self::IntVar(_)
        )
    }

    /// `true` si es un tipo flotante.
    #[must_use]
    pub const fn is_float(&self) -> bool {
        matches!(
            self,
            Self::Float | Self::F32 | Self::F64 | Self::FloatVar(_)
        )
    }

    /// `true` si es numérico.
    #[must_use]
    pub const fn is_numeric(&self) -> bool {
        self.is_integer() || self.is_float()
    }

    /// `true` si es un tipo de error.
    #[must_use]
    pub const fn is_error(&self) -> bool {
        matches!(self, Self::Error)
    }
}

impl fmt::Display for Ty {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Bool => f.write_str("Bool"),
            Self::Int => f.write_str("Int"),
            Self::I8 => f.write_str("I8"),
            Self::I16 => f.write_str("I16"),
            Self::I32 => f.write_str("I32"),
            Self::I64 => f.write_str("I64"),
            Self::Isize => f.write_str("Isize"),
            Self::U8 => f.write_str("U8"),
            Self::U16 => f.write_str("U16"),
            Self::U32 => f.write_str("U32"),
            Self::U64 => f.write_str("U64"),
            Self::Usize => f.write_str("Usize"),
            Self::Float => f.write_str("Float"),
            Self::F32 => f.write_str("F32"),
            Self::F64 => f.write_str("F64"),
            Self::Char => f.write_str("Char"),
            Self::String => f.write_str("String"),
            Self::Str => f.write_str("Str"),
            Self::Unit => f.write_str("Unit"),
            Self::Never => f.write_str("Never"),
            Self::Tuple(items) => {
                f.write_str("(")?;
                for (index, item) in items.iter().enumerate() {
                    if index > 0 {
                        f.write_str(", ")?;
                    }
                    write!(f, "{item}")?;
                }
                f.write_str(")")
            }
            Self::Array(elem, len) => write!(f, "[{elem}; {len}]"),
            Self::Slice(elem, mutable) => {
                if *mutable {
                    write!(f, "&mut [{elem}]")
                } else {
                    write!(f, "&[{elem}]")
                }
            }
            Self::Ref(inner, mutable) => {
                if *mutable {
                    write!(f, "&mut {inner}")
                } else {
                    write!(f, "&{inner}")
                }
            }
            Self::Ptr(inner) => write!(f, "Ptr[{inner}]"),
            Self::Vec(inner) => write!(f, "Vec[{inner}]"),
            Self::Map(key, value) => write!(f, "Map[{key}, {value}]"),
            Self::Set(inner) => write!(f, "Set[{inner}]"),
            Self::Option(inner) => write!(f, "Option[{inner}]"),
            Self::Result(ok, err) => write!(f, "Result[{ok}, {err}]"),
            Self::Box(inner) => write!(f, "Box[{inner}]"),
            Self::Rc(inner) => write!(f, "Rc[{inner}]"),
            Self::Arc(inner) => write!(f, "Arc[{inner}]"),
            Self::Adt(def, args) => {
                write!(f, "Adt({:?}", def)?;
                if !args.is_empty() {
                    f.write_str("[")?;
                    for (index, arg) in args.iter().enumerate() {
                        if index > 0 {
                            f.write_str(", ")?;
                        }
                        write!(f, "{arg}")?;
                    }
                    f.write_str("]")?;
                }
                f.write_str(")")
            }
            Self::Generic(def) => write!(f, "Generic({:?})", def),
            Self::CStr => f.write_str("CStr"),
            Self::CString => f.write_str("CString"),
            Self::Ordering => f.write_str("Ordering"),
            Self::Fn(params, ret) => {
                f.write_str("(")?;
                for (index, param) in params.iter().enumerate() {
                    if index > 0 {
                        f.write_str(", ")?;
                    }
                    write!(f, "{param}")?;
                }
                write!(f, ") -> {ret}")
            }
            Self::Range(inner) => write!(f, "Range[{inner}]"),
            Self::Iterator(inner) => write!(f, "Iterator[{inner}]"),
            Self::Infer(id) | Self::IntVar(id) | Self::FloatVar(id) => {
                write!(f, "_#{id}")
            }
            Self::Error => f.write_str("<error>"),
        }
    }
}
