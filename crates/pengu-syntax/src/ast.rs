//! AST de expresiones y bloques del núcleo.
//!
//! El AST es una vista tipada y ligera sobre los tokens; el CST lossless vive
//! en [`crate::cst`]. Aquí se representan las expresiones, los items y los
//! bloques que el parser construye.

use pengu_span::Span;

use crate::StringKind;

/// Literal de string, posiblemente interpolado.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StringLit {
    /// Forma léxica.
    pub kind: StringKind,
    /// Segmentos en orden.
    pub parts: Vec<StringPart>,
}

/// Segmento de un string.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum StringPart {
    /// Texto literal, sin comillas.
    Text(String),
    /// Expresión `#{...}`.
    Expr(Expr),
}

/// Expresión con span.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Expr {
    /// Contenido.
    pub kind: ExprKind,
    /// Rango en el archivo.
    pub span: Span,
}

impl Expr {
    /// Crea una expresión.
    #[must_use]
    pub const fn new(kind: ExprKind, span: Span) -> Self {
        Self { kind, span }
    }
}

/// Operador unario.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum UnOp {
    /// `-`.
    Neg,
    /// `not`.
    Not,
}

/// Operador binario.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum BinOp {
    /// `+`.
    Add,
    /// `-`.
    Sub,
    /// `*`.
    Mul,
    /// `/`.
    Div,
    /// `%`.
    Rem,
    /// `..`.
    Range,
    /// `..=`.
    RangeInclusive,
    /// `<`.
    Lt,
    /// `<=`.
    Le,
    /// `>`.
    Gt,
    /// `>=`.
    Ge,
    /// `==`.
    Eq,
    /// `!=`.
    Ne,
    /// `is`.
    Is,
    /// `isnt`.
    Isnt,
    /// `in`.
    In,
    /// `and`.
    And,
    /// `or`.
    Or,
}

/// Contenido de una expresión.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ExprKind {
    /// `()`.
    Unit,
    /// `true` o `false`.
    Bool(bool),
    /// `none`.
    None,
    /// Entero, texto crudo.
    Int(String),
    /// Flotante, texto crudo.
    Float(String),
    /// `Char`, texto crudo.
    Char(String),
    /// `ByteChar`, texto crudo.
    ByteChar(String),
    /// String normal, triple, raw, byte o C.
    String(StringLit),
    /// Path `a::b::C`.
    Path(Vec<String>),
    /// Literal de record `Point(x: 1, y: 2)` o actualización `Point(y: 3, ..p)`.
    Record {
        /// Path del tipo.
        path: Vec<String>,
        /// Campos nombrados.
        fields: Vec<(String, Expr)>,
        /// Base de una actualización `..p`.
        base: Option<Box<Expr>>,
    },
    /// `@`.
    SelfValue,
    /// Tupla `(a, b)`; incluye la tupla de un elemento.
    Tuple(Vec<Expr>),
    /// Array `[a, b]`.
    Array(Vec<Expr>),
    /// Array repetido `[e; N]`.
    ArrayRepeat {
        /// Valor repetido.
        value: Box<Expr>,
        /// Número de elementos.
        count: Box<Expr>,
    },
    /// `Vec[a, b]`.
    Vector(Vec<Expr>),
    /// `Map[k: v]` o `{k: v}`.
    Map(Vec<(Expr, Expr)>),
    /// `Set[a, b]`.
    Set(Vec<Expr>),
    /// Operador unario.
    Unary {
        /// Operador.
        op: UnOp,
        /// Operando.
        expr: Box<Expr>,
    },
    /// Operador binario.
    Binary {
        /// Operador.
        op: BinOp,
        /// Izquierda.
        lhs: Box<Expr>,
        /// Derecha.
        rhs: Box<Expr>,
    },
    /// Rango `a..b`, `a..=b` o abierto `a..`.
    Range {
        /// Inicio.
        start: Box<Expr>,
        /// Fin, ausente en `a..`.
        end: Option<Box<Expr>>,
        /// `true` para `..=`.
        inclusive: bool,
    },
    /// `expr as Type`.
    Cast {
        /// Expresión.
        expr: Box<Expr>,
        /// Tipo destino.
        ty: Type,
    },
    /// Llamada `f(args)`.
    Call {
        /// Callee.
        callee: Box<Expr>,
        /// Argumentos.
        args: Vec<Expr>,
    },
    /// Índice `base[index]`.
    Index {
        /// Base.
        base: Box<Expr>,
        /// Índice.
        index: Box<Expr>,
    },
    /// Campo `base.name`.
    Field {
        /// Base.
        base: Box<Expr>,
        /// Nombre.
        name: String,
    },
    /// `expr?`.
    Try(Box<Expr>),
    /// `&expr` o `&mut expr`.
    Ref {
        /// `true` para `&mut`.
        mutable: bool,
        /// Expresión prestada.
        expr: Box<Expr>,
    },
    /// `if`/`unless`.
    If {
        /// Condición.
        cond: Box<Expr>,
        /// Rama verdadera.
        then_branch: Block,
        /// Rama falsa.
        else_branch: Option<Block>,
        /// `true` para `unless`.
        unless: bool,
    },
    /// `match`.
    Match {
        /// Scrutinee.
        scrutinee: Box<Expr>,
        /// Brazos.
        arms: Vec<MatchArm>,
    },
    /// `do`.
    Do(Block),
    /// `loop`.
    Loop(Block),
    /// `curse`.
    Curse(Block),
    /// Lambda `(params) => ...`.
    Lambda {
        /// Parámetros.
        params: Vec<Param>,
        /// Cuerpo.
        body: Block,
    },
}

/// Un brazo de `match`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MatchArm {
    /// Patrón; `None` para `else`.
    pub pattern: Option<Pattern>,
    /// Guard `if expr`.
    pub guard: Option<Expr>,
    /// Cuerpo.
    pub body: Block,
}

/// Parámetro de función o lambda.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Param {
    /// Nombre.
    pub name: String,
    /// Tipo.
    pub ty: Type,
    /// Span del nombre.
    pub span: Span,
}

/// Bloque de sentencias.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Block {
    /// Sentencias.
    pub stmts: Vec<Stmt>,
    /// Span completo, incluyendo INDENT/DEDENT.
    pub span: Span,
}

/// Sentencia del núcleo.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Stmt {
    /// Contenido.
    pub kind: StmtKind,
    /// Span.
    pub span: Span,
}

/// Contenido de una sentencia.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum StmtKind {
    /// `bind`/`morph`.
    Bind {
        /// `true` para `morph`.
        mutable: bool,
        /// Patrón.
        pattern: Pattern,
        /// Tipo explícito opcional.
        ty: Option<Type>,
        /// Valor.
        value: Expr,
        /// `else` opcional.
        else_block: Option<Block>,
    },
    /// Asignación `place = expr`.
    Assign {
        /// Destino.
        target: Expr,
        /// Valor.
        value: Expr,
    },
    /// Expresión evaluada por su efecto o valor.
    Expr(Expr),
    /// `while cond do ...`.
    While {
        /// Condición.
        cond: Expr,
        /// Cuerpo.
        body: Block,
    },
    /// `for pattern in iter do ...`.
    For {
        /// Patrón.
        pattern: Pattern,
        /// Iterable.
        iter: Expr,
        /// Cuerpo.
        body: Block,
    },
    /// `return`.
    Return(Option<Expr>),
    /// `break`.
    Break(Option<Expr>),
    /// `continue`.
    Continue,
}

/// Tipo del núcleo.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Type {
    /// Contenido.
    pub kind: TypeKind,
    /// Span.
    pub span: Span,
}

/// Contenido de un tipo.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum TypeKind {
    /// `()`.
    Unit,
    /// `?T`.
    Option(Box<Type>),
    /// `&T` o `&mut T`.
    Ref {
        /// `true` para `&mut`.
        mutable: bool,
        /// Tipo apuntado.
        inner: Box<Type>,
    },
    /// `[T; N]`.
    Array {
        /// Elemento.
        elem: Box<Type>,
        /// Longitud.
        len: Box<Expr>,
    },
    /// `[T]`.
    Slice(Box<Type>),
    /// `(A, B)`.
    Tuple(Vec<Type>),
    /// `path[T, U]`.
    Path {
        /// Segmentos.
        segments: Vec<String>,
        /// Argumentos de tipo.
        args: Vec<Type>,
    },
    /// `Ptr[T]`.
    Ptr(Box<Type>),
    /// `(A, B) -> C`.
    Fn {
        /// Parámetros.
        params: Vec<Type>,
        /// Retorno.
        ret: Box<Type>,
    },
    /// `Self`.
    SelfType,
}

/// Patrón.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Pattern {
    /// Contenido.
    pub kind: PatternKind,
    /// Span.
    pub span: Span,
}

/// Contenido de un patrón.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PatternKind {
    /// `_`.
    Wildcard,
    /// Identificador o path unitario.
    Path(Vec<String>),
    /// `name @ pattern`.
    Bind {
        /// Nombre.
        name: String,
        /// Subpatrón.
        pattern: Box<Pattern>,
    },
    /// `(a, b)`.
    Tuple(Vec<Pattern>),
    /// `Path(a, b)` o `Path { ... }`.
    Variant {
        /// Path.
        path: Vec<String>,
        /// Argumentos posicionales.
        args: Vec<Pattern>,
        /// Campos nombrados.
        named: Vec<(String, Pattern)>,
    },
    /// Literal.
    Literal(Expr),
    /// `a | b`.
    Or(Vec<Pattern>),
    /// `a..b` o `a..=b`; `end` ausente en `a..`.
    Range {
        /// Inicio.
        start: Box<Pattern>,
        /// Fin.
        end: Option<Box<Pattern>>,
        /// `true` para `..=`.
        inclusive: bool,
    },
    /// `[a, .., b]`.
    Slice(Vec<Pattern>),
    /// `..`.
    Rest,
}

// ---------------------------------------------------------------------------
// Items y programas (F3)
// ---------------------------------------------------------------------------

/// Archivo `.d.pengu`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DeclarationFile {
    /// ABI declarada.
    pub abi: String,
    /// Declaraciones.
    pub items: Vec<Item>,
    /// Span.
    pub span: Span,
}

/// Programa completo.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Program {
    /// Items de nivel superior.
    pub items: Vec<Item>,
    /// Span del programa.
    pub span: Span,
}

/// Visibilidad de un item.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum Visibility {
    /// Sin `unveil`.
    Private,
    /// `unveil`.
    Public,
    /// `unveil(tome)`.
    Tome,
    /// `unveil(scroll)`.
    Scroll,
}

impl Visibility {
    /// `true` si el item lleva cualquier forma de `unveil`.
    #[must_use]
    pub const fn is_unveiled(self) -> bool {
        !matches!(self, Self::Private)
    }
}

/// Item con atributos derivados.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Item {
    /// Contenido.
    pub kind: ItemKind,
    /// `@@derive(...)` aplicados al item; vacío si no hay.
    pub derives: Vec<String>,
    /// Visibilidad del item.
    pub visibility: Visibility,
    /// Span.
    pub span: Span,
}

/// Contenido de un item.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ItemKind {
    /// `scroll`.
    Scroll(Scroll),
    /// `summon`.
    Summon(Summon),
    /// `rune`.
    Rune(Rune),
    /// `enchanting`.
    Enchanting(Enchanting),
    /// `pact`.
    Pact(Pact),
    /// `ritual`.
    Ritual(Ritual),
    /// `essence`.
    Essence(Essence),
    /// `foreign`.
    Foreign(Foreign),
    /// Función de nivel superior.
    Function(Function),
    /// `sigil`/`relic`.
    Const(Const),
    /// `grimoire`.
    Grimoire(Grimoire),
    /// `@@test`.
    Test(Test),
    /// Firma de función en `.d.pengu`.
    FunctionSig(FunctionSig),
}

/// Módulo `scroll`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Scroll {
    /// Nombre.
    pub name: String,
    /// Items inline; vacío en un módulo de archivo.
    pub items: Vec<Item>,
    /// Span.
    pub span: Span,
}

/// `summon path [as name]`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Summon {
    /// Path.
    pub path: Vec<String>,
    /// Alias.
    pub alias: Option<String>,
    /// Span.
    pub span: Span,
}

/// Parámetro de tipo `[T: Bound]`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TypeParam {
    /// Nombre.
    pub name: String,
    /// Bounds.
    pub bounds: Vec<Vec<String>>,
    /// Span.
    pub span: Span,
}

/// Campo de record o variante.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Field {
    /// `unveil` del campo.
    pub unveil: bool,
    /// Nombre.
    pub name: String,
    /// Tipo.
    pub ty: Type,
    /// Span.
    pub span: Span,
}

/// Cuerpo de una variante.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum VariantFields {
    /// Sin campos.
    Unit,
    /// Campos posicionales.
    Tuple(Vec<Type>),
    /// Campos nombrados.
    Named(Vec<Field>),
}

/// Variante de `enchanting`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Variant {
    /// Nombre.
    pub name: String,
    /// Campos.
    pub fields: VariantFields,
    /// Span.
    pub span: Span,
}

/// Record `rune`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Rune {
    /// `unveil`.
    pub unveil: bool,
    /// Nombre.
    pub name: String,
    /// Parámetros de tipo.
    pub params: Vec<TypeParam>,
    /// Campos.
    pub fields: Vec<Field>,
    /// Métodos (solo `.d.pengu`).
    pub methods: Vec<Method>,
    /// Span.
    pub span: Span,
}

/// Suma `enchanting`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Enchanting {
    /// `unveil`.
    pub unveil: bool,
    /// Nombre.
    pub name: String,
    /// Parámetros de tipo.
    pub params: Vec<TypeParam>,
    /// Variantes.
    pub variants: Vec<Variant>,
    /// Span.
    pub span: Span,
}

/// Receptor de método.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Receiver {
    /// `@`.
    Ref,
    /// `@mut`.
    Mut,
    /// `@own`.
    Own,
}

/// Método de `pact` o `ritual`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Method {
    /// Nombre.
    pub name: String,
    /// Receptor.
    pub receiver: Receiver,
    /// Parámetros.
    pub params: Vec<Param>,
    /// Retorno.
    pub ret: Type,
    /// Cuerpo; `None` en una firma de `pact` o `.d.pengu`.
    pub body: Option<Block>,
    /// Span.
    pub span: Span,
}

/// `pact`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Pact {
    /// `unveil`.
    pub unveil: bool,
    /// Nombre.
    pub name: String,
    /// Parámetros de tipo.
    pub params: Vec<TypeParam>,
    /// Superpact.
    pub supertrait: Option<Vec<String>>,
    /// Métodos.
    pub methods: Vec<Method>,
    /// Span.
    pub span: Span,
}

/// Item de `ritual`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RitualItem {
    /// Método.
    Method(Method),
    /// Función asociada.
    Function(Function),
    /// Constante asociada (`sigil`/`relic`).
    Const(Const),
}

/// `ritual`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Ritual {
    /// `unveil`.
    pub unveil: bool,
    /// Parámetros de tipo.
    pub params: Vec<TypeParam>,
    /// Tipo implementado.
    pub ty: Type,
    /// Pact implementado.
    pub trait_path: Option<Vec<String>>,
    /// Items.
    pub items: Vec<RitualItem>,
    /// Span.
    pub span: Span,
}

/// `essence`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Essence {
    /// `unveil`.
    pub unveil: bool,
    /// Nombre.
    pub name: String,
    /// Parámetros de tipo.
    pub params: Vec<TypeParam>,
    /// Tipo.
    pub ty: Type,
    /// Span.
    pub span: Span,
}

/// Firma de función sin cuerpo (`foreign` y `.d.pengu`).
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FunctionSig {
    /// Nombre.
    pub name: String,
    /// Parámetros de tipo (`[T]`).
    pub generics: Vec<TypeParam>,
    /// Parámetros.
    pub params: Vec<Param>,
    /// Retorno.
    pub ret: Type,
    /// Span.
    pub span: Span,
}

/// `foreign`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Foreign {
    /// ABI.
    pub abi: String,
    /// Firmas.
    pub items: Vec<FunctionSig>,
    /// Span.
    pub span: Span,
}

/// Función de nivel superior.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Function {
    /// `unveil`.
    pub unveil: bool,
    /// `curse`.
    pub curse: bool,
    /// Nombre.
    pub name: String,
    /// Parámetros de tipo.
    pub type_params: Vec<TypeParam>,
    /// Parámetros.
    pub params: Vec<Param>,
    /// Retorno.
    pub ret: Type,
    /// Cuerpo.
    pub body: Block,
    /// Span.
    pub span: Span,
}

/// Tipo de constante.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ConstKind {
    /// `sigil`.
    Sigil,
    /// `relic`.
    Relic,
}

/// `sigil`/`relic`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Const {
    /// `unveil`.
    pub unveil: bool,
    /// Tipo.
    pub kind: ConstKind,
    /// Nombre.
    pub name: String,
    /// Tipo.
    pub ty: Type,
    /// Valor; `None` en `.d.pengu`.
    pub value: Option<Expr>,
    /// Span.
    pub span: Span,
}

/// `grimoire`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Grimoire {
    /// Tipo de retorno opcional.
    pub ret: Option<Type>,
    /// Cuerpo.
    pub body: Block,
    /// Span.
    pub span: Span,
}

/// Opción de `@@test`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TestOption {
    /// Nombre de la opción.
    pub name: String,
    /// Mensaje.
    pub message: String,
    /// Span.
    pub span: Span,
}

/// `@@test`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Test {
    /// Opciones.
    pub options: Vec<TestOption>,
    /// Nombre.
    pub name: String,
    /// Retorno.
    pub ret: Type,
    /// Cuerpo.
    pub body: Block,
    /// Span.
    pub span: Span,
}
