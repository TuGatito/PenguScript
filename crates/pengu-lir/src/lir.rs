//! Representación intermedia de bajo nivel, explícita y cercana a Rust.

use pengu_hir::DefId;
use pengu_span::Span;
use pengu_types::Ty;

/// Índice de bloque dentro de una función.
pub type BlockId = usize;
/// Índice de local dentro de una función.
pub type LocalIndex = usize;

/// Destino de una desestructuración de tupla.
#[derive(Clone, Debug, PartialEq)]
pub enum DestructureTarget {
    /// Binding local.
    Local(LocalIndex),
    /// Tupla anidada.
    Tuple(Vec<DestructureTarget>),
    /// Elemento ignorado.
    Ignore,
}

/// Programa LIR completo.
#[derive(Clone, Debug, Default)]
pub struct LProgram {
    /// Funciones bajadas.
    pub functions: Vec<LFunction>,
    /// Instancias monomórficas alcanzables (B2).
    pub instances: Vec<crate::mono::MonoInstance>,
    /// Diagnósticos de bajada.
    pub diagnostics: Vec<pengu_diag::Diagnostic>,
}

/// Función LIR.
#[derive(Clone, Debug, PartialEq)]
pub struct LFunction {
    /// Definición HIR propietaria.
    pub def: DefId,
    /// Nombre.
    pub name: String,
    /// Parámetros.
    pub params: Vec<LParam>,
    /// Tipo de retorno.
    pub ret: Ty,
    /// Locales.
    pub locals: Vec<LLocal>,
    /// Bloques.
    pub blocks: Vec<LBlock>,
    /// Bloque de entrada.
    pub entry: BlockId,
    /// Usa `curse`: el cuerpo se emite dentro de `unsafe`.
    pub has_curse: bool,
}

/// Parámetro LIR.
#[derive(Clone, Debug, PartialEq)]
pub struct LParam {
    /// Local asociado.
    pub local: LocalIndex,
    /// Nombre.
    pub name: String,
    /// Tipo.
    pub ty: Ty,
}

/// Local LIR.
#[derive(Clone, Debug, PartialEq)]
pub struct LLocal {
    /// Identificador estable.
    pub id: LocalIndex,
    /// Nombre.
    pub name: String,
    /// Mutabilidad.
    pub mutable: bool,
    /// Tipo.
    pub ty: Ty,
}

/// Bloque básico.
#[derive(Clone, Debug, PartialEq)]
pub struct LBlock {
    /// Identificador.
    pub id: BlockId,
    /// Sentencias.
    pub stmts: Vec<LStmt>,
    /// Terminador.
    pub term: LTerm,
}

/// Sentencia LIR.
#[derive(Clone, Debug, PartialEq)]
pub enum LStmt {
    /// Declara un local.
    Let(LocalIndex, LExpr, Span),
    /// Asigna a un local.
    Assign(LocalIndex, LExpr, Span),
    /// Asigna a un campo de un local.
    SetField(LocalIndex, String, LExpr, Span),
    /// Expresión evaluada por efecto.
    Eval(LExpr, Span),
    /// Desestructura `source` según un patrón de tuplas.
    Destructure(LExpr, DestructureTarget, Span),
}

/// Terminador LIR.
#[derive(Clone, Debug, PartialEq)]
pub enum LTerm {
    /// Avanza un iterador; escribe el item y salta a `some` o `none`.
    Next {
        /// Local que guarda el iterador.
        iter: LocalIndex,
        /// Local que recibe el item.
        item: LocalIndex,
        /// Bloque si hay item.
        some: BlockId,
        /// Bloque si el iterador terminó.
        none: BlockId,
    },
    /// Salto incondicional.
    Goto(BlockId),
    /// Bifurcación.
    If(LExpr, BlockId, BlockId),
    /// Retorno.
    Return(Option<LExpr>),
    /// Pánico.
    Panic(LExpr),
    /// Bloque aún no sellado o inalcanzable.
    Unreachable,
}

/// Parte de un string interpolado.
#[derive(Clone, Debug, PartialEq)]
pub enum LStringPart {
    /// Texto literal.
    Text(String),
    /// Expresión interpolada.
    Expr(LExpr),
}

/// Variantes de `Option` y `Result` que no tienen `DefId` propio.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BuiltinVariant {
    Some,
    Ok,
    Err,
}

/// Expresión LIR.
#[derive(Clone, Debug, PartialEq)]
pub enum LExpr {
    /// `()`.
    Unit,
    /// Booleano.
    Bool(bool),
    /// Entero.
    Int(i64),
    /// Flotante.
    Float(f64),
    /// Cadena.
    Str(String),
    /// Cadena interpolada.
    Interpolate(Vec<LStringPart>),
    /// Carácter.
    Char(String),
    /// Byte char.
    ByteChar(String),
    /// Local.
    Local(LocalIndex),
    /// Campo de un valor.
    Field(Box<LExpr>, String),
    /// Índice de un valor.
    Index(Box<LExpr>, Box<LExpr>),
    /// Array.
    Array(Vec<LExpr>),
    /// Array repetido.
    ArrayRepeat(Box<LExpr>, usize),
    /// Vector.
    Vector(Vec<LExpr>),
    /// Mapa.
    Map(Vec<(LExpr, LExpr)>),
    /// Set.
    Set(Vec<LExpr>),
    /// Construcción de un ADT.
    Record {
        def: Option<DefId>,
        path: Vec<String>,
        fields: Vec<(String, LExpr)>,
        base: Option<Box<LExpr>>,
    },
    /// Variante de un sum.
    Variant(DefId, Option<Vec<LExpr>>),
    /// `matches!(value, Variant(..))`.
    IsVariant(Box<LExpr>, DefId),
    /// Extrae el campo posicional `index` de una variante.
    VariantField(Box<LExpr>, DefId, u32),
    /// `matches!(value, Some(_))` / `Ok(_)` / `Err(_)` para variantes integradas.
    IsBuiltin(Box<LExpr>, BuiltinVariant),
    /// Extrae el payload de `Some`/`Ok`/`Err` de una variante integrada.
    BuiltinField(Box<LExpr>, BuiltinVariant),
    /// Llamada a una primitiva del lenguaje (`some`, `ok`, `err`, `print`...).
    Primitive(String, Vec<LExpr>),
    /// Cast `as`.
    Cast(Box<LExpr>, Ty),
    /// Propagación `?`.
    Try(Box<LExpr>),
    /// Referencia `&`/`&mut`.
    Ref(bool, Box<LExpr>),
    /// Rango.
    Range(Box<LExpr>, Option<Box<LExpr>>, bool),
    /// Operación binaria.
    Binary(LBinOp, Box<LExpr>, Box<LExpr>),
    /// Operación unaria.
    Unary(LUnOp, Box<LExpr>),
    /// Llamada a un método de un `pact` de operadores (`Add::add(a, b)`):
    /// el operador sobre un tipo de usuario se despacha al pacto.
    TraitCall {
        /// `DefId` del pacto (`std::opera::Add`).
        pact: DefId,
        /// Nombre del método del pacto.
        method: String,
        /// Argumentos en orden.
        args: Vec<LExpr>,
    },
    /// Llamada a método.
    Method {
        /// Receptor.
        receiver: Box<LExpr>,
        /// Método resuelto (si existe).
        def: Option<DefId>,
        /// Nombre del método.
        name: String,
        /// Argumentos.
        args: Vec<LExpr>,
    },
    /// Llamada a función.
    Call(DefId, Vec<Ty>, Vec<LExpr>),
    /// Referencia a una función como valor (`v.sort_by(compare)`).
    FuncRef(DefId),
    /// Referencia a una constante (`sigil`, `relic`).
    ConstRef(DefId),
    /// `CString.new(text)`: `Result[CString, NulError]` del núcleo.
    CStringNew(Box<LExpr>),
    /// Tupla.
    Tuple(Vec<LExpr>),
    /// Closure no capturante.
    Closure {
        /// Parámetros `(nombre, tipo)`.
        params: Vec<(String, Ty)>,
        /// Tipo de retorno.
        ret: Ty,
        /// Cuerpo AST.
        body: Box<pengu_syntax::ast::Block>,
        /// Capturas del scope exterior `(nombre, local)`.
        captures: Vec<(String, LocalIndex)>,
    },
    /// Llamada a un valor invocable (closure).
    ClosureCall(Box<LExpr>, Vec<LExpr>),
    CollectVec(Box<LExpr>),
    IntoIter(Box<LExpr>),
    /// `.iter().cloned()`: recorre por valor sin consumir el contenedor.
    IterCloned(Box<LExpr>),
    VecAdapter {
        kind: VecAdapterKind,
        base: Box<LExpr>,
        args: Vec<LExpr>,
        /// Tipo del resultado, cuando el codegen lo necesita para desambiguar
        /// (por ejemplo `sum::<T>()`).
        ty: Option<Ty>,
    },
}

/// Operador binario LIR.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LBinOp {
    Add,
    Sub,
    Mul,
    Div,
    Rem,
    Eq,
    Ne,
    Lt,
    Le,
    Gt,
    Ge,
    And,
    Or,
}

/// Adaptador de Vec (B3d).
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum VecAdapterKind {
    Map,
    Filter,
    Fold,
    Collect,
    Count,
    Last,
    Nth,
    Sum,
    Min,
    Max,
    Any,
    All,
    Find,
    Position,
    Take,
    Skip,
    StepBy,
    Rev,
    Enumerate,
    Zip,
    FilterMap,
    FlatMap,
    Flatten,
    Chain,
    TakeWhile,
    SkipWhile,
    Reduce,
    Product,
    ForEach,
    Inspect,
    Fuse,
    MaxBy,
    MinBy,
    StrChars,
    StrBytes,
    StrCharIndices,
}

/// Operador unario LIR.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LUnOp {
    Neg,
    Not,
}
