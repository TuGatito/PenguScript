//! Representación intermedia de nombres, módulos y cuerpos.
//!
//! En C1 la HIR conserva la forma de los items y resuelve nombres; el checker
//! de tipos/ownership de C2 en adelante añadirá información semántica.

use std::collections::{HashMap, HashSet};

use pengu_diag::Diagnostic;
use pengu_span::Span;
use pengu_syntax::ast::{Block, Expr, Receiver, Type, Visibility};

use crate::ids::{BodyId, DefId, LocalId, ModuleId, ScopeId};

/// Nombre de un item o binding.
pub type Symbol = String;

/// Clase de una definición.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum DefKind {
    /// Módulo `scroll`.
    Module,
    /// Tipo nominal (`rune`, `enchanting`, `essence`, `pact`).
    Type,
    /// Variante de un `enchanting`.
    Variant,
    /// Campo de un `rune` o variante.
    Field,
    /// Función, método, test o `grimoire`.
    Function,
    /// `sigil`.
    Const,
    /// `relic`.
    Static,
    /// `pact`.
    Pact,
    /// `ritual`.
    Impl,
    /// Binding local.
    Local,
    /// Parámetro de tipo.
    Generic,
}

impl DefKind {
    /// Namespace en el que se declara este kind.
    #[must_use]
    pub const fn namespace(self) -> Namespace {
        match self {
            Self::Module => Namespace::Module,
            Self::Type | Self::Variant | Self::Pact | Self::Generic => Namespace::Type,
            Self::Field
            | Self::Function
            | Self::Const
            | Self::Static
            | Self::Impl
            | Self::Local => Namespace::Value,
        }
    }
}

/// Namespaces de nombres.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum Namespace {
    /// Valores: funciones, constantes, statics y locales.
    Value,
    /// Tipos, variantes, pacts y parámetros genéricos.
    Type,
    /// Módulos.
    Module,
}

/// Una definición del crate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Def {
    /// Identificador.
    pub id: DefId,
    /// Clase.
    pub kind: DefKind,
    /// Nombre.
    pub name: Symbol,
    /// Visibilidad declarada.
    pub vis: Visibility,
    /// Span del nombre/definición.
    pub span: Span,
    /// Módulo que la contiene.
    pub module: ModuleId,
}

/// Un módulo del crate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Module {
    /// Identificador.
    pub id: ModuleId,
    /// Módulo padre; `None` para la raíz.
    pub parent: Option<ModuleId>,
    /// Nombre; vacío para la raíz.
    pub name: Symbol,
    /// Items declarados directamente.
    pub items: Vec<DefId>,
    /// Scope de los nombres del módulo.
    pub scope: ScopeId,
    /// Definición del módulo; `None` para la raíz.
    pub def: Option<DefId>,
    /// Span.
    pub span: Span,
}

/// Scope de nombres.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Scope {
    /// Identificador.
    pub id: ScopeId,
    /// Scope padre.
    pub parent: Option<ScopeId>,
    /// Clase de scope.
    pub kind: ScopeKind,
    /// Nombres de valor.
    pub values: HashMap<Symbol, Binding>,
    /// Nombres de tipo.
    pub types: HashMap<Symbol, Binding>,
    /// Nombres de módulo.
    pub modules: HashMap<Symbol, Binding>,
}

/// Clase de scope.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum ScopeKind {
    /// Scope de un módulo.
    Module,
    /// Scope de un cuerpo (parámetros, genéricos).
    Body,
    /// Scope de un bloque.
    Block,
    /// Scope de un brazo de `match`.
    MatchArm,
    /// Scope de un `for`.
    For,
    /// Scope de una lambda.
    Lambda,
}

/// Binding de un nombre en un scope.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Binding {
    /// Resolución.
    pub res: Res,
    /// Span de la declaración/importación.
    pub span: Span,
}

/// Resultado de resolver un nombre.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum Res {
    /// Item del crate.
    Def(DefId),
    /// Binding local.
    Local(LocalId),
    /// Tipo o constructor de la prelude.
    Primitive(Primitive),
    /// Nombre no resuelto.
    Error,
}

/// Tipos y constructores de la prelude.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum Primitive {
    /// `Bool`.
    Bool,
    /// `Int`.
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
    /// `F32`.
    F32,
    /// `F64`.
    F64,
    /// `Float`.
    Float,
    /// `Char`.
    Char,
    /// `String`.
    String,
    /// `Str`.
    Str,
    /// Categoría estructural: `&T` / `&mut T`.
    Ref,
    /// Categoría estructural: `[T; N]`.
    Array,
    /// Categoría estructural: `[T]`.
    Slice,
    /// Categoría estructural: tupla.
    Tuple,
    /// Categoría estructural: función/closure.
    Fn,
    /// `Unit`.
    Unit,
    /// `Never`.
    Never,
    /// `Vec`.
    Vec,
    /// `Map`.
    Map,
    /// `Set`.
    Set,
    /// `Option`.
    Option,
    /// `Result`.
    Result,
    /// `Box`.
    Box,
    /// `Rc`.
    Rc,
    /// `Arc`.
    Arc,
    /// `Ptr`.
    Ptr,
    /// `CStr`.
    CStr,
    /// `CString`.
    CString,
    /// `Ordering`.
    Ordering,
    /// Variante `Ordering.Less`.
    OrderingLess,
    /// Variante `Ordering.Equal`.
    OrderingEqual,
    /// Variante `Ordering.Greater`.
    OrderingGreater,
    /// `Range[T]`.
    Range,
    /// `print`.
    Print,
    /// `format`.
    Format,
    /// `assert`.
    Assert,
    /// `panic`.
    Panic,
    /// `assert_eq`.
    AssertEq,
    /// `assert_ne`.
    AssertNe,
    /// `some`.
    Some,
    /// `none`.
    None,
    /// `ok`.
    Ok,
    /// `err`.
    Err,
}

/// Un binding local dentro de un cuerpo.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Local {
    /// Identificador por cuerpo.
    pub id: LocalId,
    /// Nombre.
    pub name: Symbol,
    /// `morph`.
    pub mutable: bool,
    /// Span del nombre.
    pub span: Span,
}

/// Un cuerpo de función/método/test.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Body {
    /// Identificador.
    pub id: BodyId,
    /// Definición propietaria.
    pub owner: DefId,
    /// Parámetros.
    pub params: Vec<LocalId>,
    /// Locales declarados.
    pub locals: Vec<Local>,
    /// Resoluciones de paths encontrados.
    pub resolutions: Vec<Resolution>,
    /// Tipo de `Self` en un método; `None` fuera de `pact`/`ritual`.
    pub self_ty: Option<Res>,
    /// Bloque AST del cuerpo; `None` para firmas sin cuerpo.
    pub ast: Option<Block>,
    /// Local sintético para `@` en métodos.
    pub self_local: Option<LocalId>,
}

/// Parámetro genérico resuelto.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GenericParam {
    /// Definición del parámetro.
    pub def: DefId,
    /// Nombre.
    pub name: Symbol,
    /// Pacts exigidos, resueltos.
    pub bounds: Vec<DefId>,
}

/// Firma de una función o método, en tipos del AST.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Signature {
    /// Parámetros, en orden.
    pub params: Vec<Type>,
    /// Tipo de retorno.
    pub ret: Type,
    /// Receptor si es un método (`@`, `@mut`, `@own`).
    pub receiver: Option<Receiver>,
    /// Parámetros genéricos.
    pub generics: Vec<GenericParam>,
}

/// Contrato de un `pact`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PactDef {
    /// Definición del pact.
    pub def: DefId,
    /// Módulo donde se declara.
    pub module: ModuleId,
    /// Superpact, si existe.
    pub superpact: Option<DefId>,
    /// Métodos declarados.
    pub methods: Vec<DefId>,
    /// Parámetros genéricos.
    pub generics: Vec<GenericParam>,
}

/// Implementación de un `ritual`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ImplDef {
    /// Definición auxiliar del ritual.
    pub def: DefId,
    /// Módulo donde se declara.
    pub module: ModuleId,
    /// Tipo implementado, en AST.
    pub ty: Type,
    /// Resoluciones de nombres dentro de `ty`.
    pub resolutions: Vec<Resolution>,
    /// Pact implementado; `None` para inherente.
    pub pact: Option<DefId>,
    /// Métodos implementados.
    pub methods: Vec<DefId>,
    /// Constantes asociadas (`Int.MAX`).
    pub consts: Vec<DefId>,
    /// Parámetros genéricos.
    pub generics: Vec<GenericParam>,
}

/// Resolución de un path/expresión.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Resolution {
    /// Span del path.
    pub span: Span,
    /// Resultado.
    pub res: Res,
}

/// Clase de un tipo algebraico.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum AdtKind {
    /// `rune`.
    Record,
    /// `enchanting`.
    Sum,
}

/// Campo de un record o variante.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AdtField {
    /// Definición auxiliar del campo.
    pub def: DefId,
    /// Nombre del campo.
    pub name: Symbol,
    /// Tipo declarado.
    pub ty: Type,
    /// Visibilidad declarada.
    pub vis: Visibility,
    /// Resoluciones de nombres dentro de `ty`.
    pub resolutions: Vec<Resolution>,
}

/// Variante de una suma.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AdtVariant {
    /// Definición de la variante.
    pub def: DefId,
    /// Nombre.
    pub name: Symbol,
    /// Campos.
    pub fields: Vec<AdtField>,
    /// `true` si los campos son posicionales.
    pub tuple: bool,
}

/// Información semántica de un `rune` o `enchanting`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AdtDef {
    /// Definición del tipo.
    pub def: DefId,
    /// Módulo donde se declara.
    pub module: ModuleId,
    /// Clase.
    pub kind: AdtKind,
    /// Campos del record; vacío en sumas.
    pub fields: Vec<AdtField>,
    /// Variantes de la suma; vacío en records.
    pub variants: Vec<AdtVariant>,
    /// Parámetros genéricos.
    pub generics: Vec<GenericParam>,
    /// `true` si el record/suma declara `@@derive(Copy, ...)`.
    pub is_copy: bool,
    /// Nombres de `@@derive` declarados, en orden.
    pub derives: Vec<String>,
}

/// Un `sigil`/`relic` con su tipo y valor inicial.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ConstDef {
    /// Definición.
    pub def: DefId,
    /// Módulo.
    pub module: ModuleId,
    /// Tipo declarado.
    pub ty: Type,
    /// Valor inicial; `None` en `.d.pengu`.
    pub value: Option<Expr>,
}

/// Metadata de un `@@test`.
#[derive(Clone, Debug, Eq, PartialEq, Default)]
pub struct TestInfo {
    /// Mensaje esperado de `should_panic`, si se declaró.
    pub should_panic: Option<String>,
    /// Mensaje de `ignore`, si se declaró.
    pub ignore: Option<String>,
}

/// Crate completo en HIR.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HirCrate {
    /// Módulo raíz.
    pub root: ModuleId,
    /// Módulos.
    pub modules: Vec<Module>,
    /// Definiciones.
    pub defs: Vec<Def>,
    /// Cuerpos.
    pub bodies: Vec<Body>,
    /// Scopes.
    pub scopes: Vec<Scope>,
    /// Firmas de funciones/métodos por definición.
    pub signatures: HashMap<DefId, Signature>,
    /// Información de records y sumas.
    pub adts: HashMap<DefId, AdtDef>,
    /// Pacts declarados.
    pub pacts: HashMap<DefId, PactDef>,
    /// `Show` de la prelude.
    pub show_pact: Option<DefId>,
    /// Rituales (inherentes y de pact).
    pub impls: Vec<ImplDef>,
    /// Funciones declaradas en bloques `foreign`.
    pub foreign_fns: HashSet<DefId>,
    /// ABI de cada función `foreign`.
    pub foreign_abis: HashMap<DefId, String>,
    /// Funciones marcadas `curse`.
    pub curse_fns: HashSet<DefId>,
    /// Tests declarados con `@@test`.
    pub tests: HashMap<DefId, TestInfo>,
    /// `grimoire` entry points.
    pub grimoires: HashSet<DefId>,
    /// Constantes `sigil`/`relic`.
    pub consts: HashMap<DefId, ConstDef>,
    /// Alias `essence` por definición.
    pub aliases: HashMap<DefId, Type>,
    /// Tipo propietario de cada variante.
    pub variant_owners: HashMap<DefId, DefId>,
    /// Métodos asociados por nombre de tipo (`Point`, `Int`, ...).
    pub methods: HashMap<String, Vec<DefId>>,
    /// Constantes asociadas por nombre de tipo (`Int`, `Float`, ...).
    pub assoc_consts: HashMap<String, Vec<DefId>>,
    /// Diagnósticos de resolución.
    pub diagnostics: Vec<Diagnostic>,
}

impl HirCrate {
    /// Módulo por id.
    #[must_use]
    pub fn module(&self, id: ModuleId) -> &Module {
        &self.modules[id.index()]
    }

    /// Definición por id.
    #[must_use]
    pub fn def(&self, id: DefId) -> &Def {
        &self.defs[id.index()]
    }

    /// Scope por id.
    #[must_use]
    pub fn scope(&self, id: ScopeId) -> &Scope {
        &self.scopes[id.index()]
    }

    /// Firma de una función, si existe.
    #[must_use]
    pub fn signature(&self, id: DefId) -> Option<&Signature> {
        self.signatures.get(&id)
    }

    /// ¿El módulo es `std` o cuelga de él?
    #[must_use]
    pub fn is_std_module(&self, module: ModuleId) -> bool {
        let mut current = Some(module);
        while let Some(id) = current {
            let data = self.module(id);
            if data.name == "std" {
                return true;
            }
            current = data.parent;
        }
        false
    }

    /// Información de un record o suma.
    #[must_use]
    pub fn adt(&self, id: DefId) -> Option<&AdtDef> {
        self.adts.get(&id)
    }

    /// Tipo propietario de una variante.
    #[must_use]
    pub fn variant_owner(&self, id: DefId) -> Option<DefId> {
        self.variant_owners.get(&id).copied()
    }

    /// `true` si hubo errores de resolución.
    #[must_use]
    pub fn has_errors(&self) -> bool {
        self.diagnostics
            .iter()
            .any(pengu_diag::Diagnostic::is_error)
    }
}

/// Comprueba que un crate binario tenga un `grimoire`.
#[must_use]
pub fn check_binary(krate: &HirCrate) -> Vec<Diagnostic> {
    let root = krate.module(krate.root);
    let has_grimoire = root.items.iter().any(|item| {
        let def = &krate.defs[item.index()];
        def.kind == DefKind::Function && def.name == "main"
    });
    if has_grimoire {
        Vec::new()
    } else {
        vec![Diagnostic::error(
            "PGS-E2009",
            "un binario necesita un `grimoire`",
            root.span,
        )]
    }
}
