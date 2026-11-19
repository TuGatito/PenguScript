"""Abstract Syntax Tree node definitions for PenguScript."""

from __future__ import annotations

from dataclasses import dataclass, field

from penguscript.frontend.span import Span


@dataclass(frozen=True, slots=True)
class Node:
    """Base class for all AST nodes."""

    span: Span | None = field(default=None, kw_only=True)


# --- Base categories ---


@dataclass(frozen=True, slots=True)
class Declaration(Node):
    """Base class for top-level declarations."""


@dataclass(frozen=True, slots=True)
class Statement(Node):
    """Base class for statements."""


@dataclass(frozen=True, slots=True)
class Expression(Node):
    """Base class for expressions."""


@dataclass(frozen=True, slots=True)
class TypeExpr(Node):
    """Base class for type expressions."""


@dataclass(frozen=True, slots=True)
class Target(Node):
    """Base class for assignment targets."""


# --- Types ---


@dataclass(frozen=True, slots=True)
class SigilConstraint(Node):
    """Constraint on a generic type parameter (e.g. Ord, Display, Into<U>)."""

    name: str
    args: list[TypeExpr] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SigilParam(Node):
    """Generic type parameter declaration (sigil), e.g. <T needs Ord, Display>."""

    name: str
    constraints: list[SigilConstraint] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class NamedType(TypeExpr):
    """Named type, possibly generic, optional, and/or reference."""

    name: str
    args: list[TypeExpr] = field(default_factory=list)
    is_optional: bool = False
    is_mut: bool = False


@dataclass(frozen=True, slots=True)
class LiteralType(TypeExpr):
    """Literal value used as a type argument, e.g. 4 in array<int, 4>."""

    value: int | str


@dataclass(frozen=True, slots=True)
class FnType(TypeExpr):
    """Function type expression, e.g. function<(int) -> void>."""

    param_types: list[TypeExpr] = field(default_factory=list)
    return_type: TypeExpr | None = None


# --- Literals ---


@dataclass(frozen=True, slots=True)
class IntLit(Expression):
    """Integer literal."""

    value: int
    raw: str = ""


@dataclass(frozen=True, slots=True)
class HexLit(Expression):
    """Hexadecimal integer literal."""

    value: int
    raw: str = ""


@dataclass(frozen=True, slots=True)
class FloatLit(Expression):
    """Floating-point literal."""

    value: float
    raw: str = ""


@dataclass(frozen=True, slots=True)
class StringLit(Expression):
    """String literal."""

    value: str


@dataclass(frozen=True, slots=True)
class StringInterp(Expression):
    """Interpolated string containing literal text chunks and expressions."""

    parts: list[str | Expression] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BoolLit(Expression):
    """Boolean literal."""

    value: bool


@dataclass(frozen=True, slots=True)
class NoneLit(Expression):
    """None / nullopt literal."""


@dataclass(frozen=True, slots=True)
class NullptrLit(Expression):
    """Nullptr literal."""


@dataclass(frozen=True, slots=True)
class EllipsisLit(Expression):
    """Ellipsis literal, ..."""


# --- Identifiers and Accesses ---


@dataclass(frozen=True, slots=True)
class Ident(Expression):
    """Simple identifier expression."""

    name: str


@dataclass(frozen=True, slots=True)
class RealmAccess(Expression):
    """Realm-qualified access, e.g. math::sqrt."""

    realm: str
    name: str


@dataclass(frozen=True, slots=True)
class EnumVariant(Expression):
    """Enum variant access, e.g. Color::Red."""

    enum_name: str
    variant_name: str


@dataclass(frozen=True, slots=True)
class TypeStaticAccess(Expression):
    """Static type access, e.g. Vector::from."""

    type_name: str
    method_name: str


@dataclass(frozen=True, slots=True)
class SelfRef(Expression):
    """Reference to self (@)."""


@dataclass(frozen=True, slots=True)
class SelfField(Expression):
    """Self field access, e.g. @x."""

    name: str


@dataclass(frozen=True, slots=True)
class SelfMethodCall(Expression):
    """Self method call, e.g. @compute(1, 2)."""

    name: str
    args: list[Expression] = field(default_factory=list)


# --- Grouping and Operations ---


@dataclass(frozen=True, slots=True)
class Paren(Expression):
    """Parenthesized expression."""

    inner: Expression


@dataclass(frozen=True, slots=True)
class Unary(Expression):
    """Unary operation, e.g. -x, not x, #items."""

    op: str
    operand: Expression


@dataclass(frozen=True, slots=True)
class Binary(Expression):
    """Binary operation, e.g. a + b, a and b."""

    op: str
    left: Expression
    right: Expression


@dataclass(frozen=True, slots=True)
class Call(Expression):
    """Function call expression, e.g. f(x, y), f!, or make_vector<int>()."""

    callee: Expression
    args: list[Expression] = field(default_factory=list)
    type_args: list[TypeExpr] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Index(Expression):
    """Index access, e.g. arr[i] or arr[i, j]."""

    target: Expression
    indices: list[Expression] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FieldAccess(Expression):
    """Field access, e.g. a.b."""

    target: Expression
    field_name: str


@dataclass(frozen=True, slots=True)
class MethodCall(Expression):
    """Method call, e.g. a.b(1), a.b!, or a.b<T>()."""

    target: Expression
    method_name: str
    args: list[Expression] = field(default_factory=list)
    type_args: list[TypeExpr] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Range(Expression):
    """Range expression, e.g. 1..10 or 1..<10."""

    start: Expression
    end: Expression
    inclusive: bool = True


@dataclass(frozen=True, slots=True)
class Cast(Expression):
    """Type cast expression, e.g. x as int."""

    expr: Expression
    target_type: TypeExpr


# --- Collections ---


@dataclass(frozen=True, slots=True)
class TupleLiteral(Expression):
    """Tuple literal, e.g. (a, b) or (x,)."""

    elements: list[Expression] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ListLit(Expression):
    """List / vector / array literal, e.g. [1, 2, 3]."""

    elements: list[Expression] = field(default_factory=list)
    type_prefix: TypeExpr | None = None


@dataclass(frozen=True, slots=True)
class MapEntry(Node):
    """Key-value entry in a map literal."""

    key: Expression
    value: Expression


@dataclass(frozen=True, slots=True)
class MapLit(Expression):
    """Map literal, e.g. {a: 1, b: 2}."""

    entries: list[MapEntry] = field(default_factory=list)
    type_prefix: TypeExpr | None = None


@dataclass(frozen=True, slots=True)
class SetLit(Expression):
    """Set literal, e.g. set{1, 2, 3}."""

    elements: list[Expression] = field(default_factory=list)
    prefix: str = "set"


@dataclass(frozen=True, slots=True)
class ForClause(Node):
    """A for clause in a list comprehension."""

    target: str
    iterable: Expression | None = None
    index_var: str | None = None
    is_mut: bool = False
    start: Expression | None = None
    end: Expression | None = None
    step: Expression | None = None
    var_type: TypeExpr | None = None
    condition: Expression | None = None


@dataclass(frozen=True, slots=True)
class ListComp(Expression):
    """List comprehension: [expr for ... (if ...)]."""

    element: Expression
    for_clauses: list[ForClause] = field(default_factory=list)
    type_prefix: NamedType | None = None


# --- Targets and Statements ---


@dataclass(frozen=True, slots=True)
class VarTarget(Target):
    """Variable assignment target."""

    name: str


@dataclass(frozen=True, slots=True)
class SelfFieldTarget(Target):
    """Self field assignment target, e.g. @x = 1."""

    name: str


@dataclass(frozen=True, slots=True)
class ExprTarget(Target):
    """Expression assignment target, e.g. a.b = 1, arr[0] = 2."""

    expr: Expression


@dataclass(frozen=True, slots=True)
class DerefTarget(Target):
    """Pointer dereference assignment target, e.g. *p = 1."""

    target: Target | Expression


@dataclass(frozen=True, slots=True)
class Assign(Statement):
    """Variable declaration or assignment statement."""

    targets: list[Target]
    value: Expression
    type_annotation: TypeExpr | None = None
    is_mut: bool = False
    is_static: bool = False
    is_unsafe: bool = False


@dataclass(frozen=True, slots=True)
class CompoundAssign(Statement):
    """Compound assignment statement, e.g. x += 1."""

    target: Target
    op: str
    value: Expression


@dataclass(frozen=True, slots=True)
class ExprStmt(Statement):
    """Expression used as a statement."""

    expr: Expression


# --- Phase 3: Control Flow and Function AST Nodes ---


@dataclass(frozen=True, slots=True)
class Block(Statement):
    """Indented block of statements."""

    statements: list[Statement] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ElseIfClause(Node):
    """An else-if branch in an if-statement."""

    condition: Expression
    body: Block


@dataclass(frozen=True, slots=True)
class If(Statement):
    """If statement with optional else-if branches and else block."""

    condition: Expression
    then_block: Block
    else_if_clauses: list[ElseIfClause] = field(default_factory=list)
    else_block: Block | None = None


@dataclass(frozen=True, slots=True)
class IfInline(Expression):
    """Inline if-expression: if cond then a else b."""

    condition: Expression
    then_expr: Expression
    else_expr: Expression


@dataclass(frozen=True, slots=True)
class IfBlockExpr(Expression):
    """Multi-line if expression returning a value."""

    condition: Expression
    body: Block
    else_if_clauses: list[ElseIfClause] = field(default_factory=list)
    else_block: Block | None = None


@dataclass(frozen=True, slots=True)
class Unless(Statement):
    """Unless statement (if not cond)."""

    condition: Expression
    body: Block
    else_block: Block | None = None


@dataclass(frozen=True, slots=True)
class While(Statement):
    """While loop with optional else block."""

    condition: Expression
    body: Block
    else_block: Block | None = None


@dataclass(frozen=True, slots=True)
class Until(Statement):
    """Until loop (while not cond) with optional else block."""

    condition: Expression
    body: Block
    else_block: Block | None = None


@dataclass(frozen=True, slots=True)
class Repeat(Statement):
    """Repeat...until loop with optional else block."""

    body: Block
    condition: Expression
    else_block: Block | None = None


@dataclass(frozen=True, slots=True)
class ForNumeric(Statement):
    """Numeric for loop: for i = a, b[, step]."""

    var_name: str
    start: Expression
    end: Expression
    body: Block
    step: Expression | None = None
    var_type: TypeExpr | None = None
    else_block: Block | None = None


@dataclass(frozen=True, slots=True)
class ForIter(Statement):
    """Iterable for loop: for [i, ]x in seq."""

    target: str
    iterable: Expression
    body: Block
    index_var: str | None = None
    is_mut: bool = False
    else_block: Block | None = None


@dataclass(frozen=True, slots=True)
class Break(Statement):
    """Break statement, optionally with a return value."""

    value: Expression | None = None


@dataclass(frozen=True, slots=True)
class Continue(Statement):
    """Continue statement."""


@dataclass(frozen=True, slots=True)
class Pass(Statement):
    """Pass statement (no-op)."""


@dataclass(frozen=True, slots=True)
class UnsafeBlock(Statement):
    """Unsafe block."""

    body: Block


@dataclass(frozen=True, slots=True)
class ParentCall(Statement):
    """Parent constructor call in derived rune, e.g. parent(name, legs)."""

    args: list[Expression] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ConstructorCall(Expression):
    """Constructor invocation, e.g. Point(0, 0) or Box<int>(42)."""

    target_type: NamedType
    args: list[Expression] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Parameter(Node):
    """Function parameter."""

    name: str
    type_annotation: TypeExpr | None = None
    default_value: Expression | None = None
    is_mut: bool = False


@dataclass(frozen=True, slots=True)
class FunctionLiteral(Expression):
    """Function literal (anonymous or assigned)."""

    params: list[Parameter] = field(default_factory=list)
    return_type: TypeExpr | None = None
    body: Block | Expression | None = None
    sigils: list[SigilParam] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FunctionDecl(Declaration):
    """Top-level named function declaration."""

    name: str
    function: FunctionLiteral
    is_mut: bool = False
    is_static: bool = False
    is_unsafe: bool = False


# --- Top-Level Declarations (Phase 4) ---


@dataclass(frozen=True, slots=True)
class RealmDecl(Declaration):
    """Realm namespace declaration."""

    name: str


@dataclass(frozen=True, slots=True)
class ImportSymbol(Node):
    """Single imported symbol, optionally aliased."""

    name: str
    alias: str | None = None


@dataclass(frozen=True, slots=True)
class InvokeDecl(Declaration):
    """Module import declaration."""

    path: str
    alias: str | None = None
    symbols: list[ImportSymbol] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ConstDecl(Declaration):
    """Top-level constant declaration."""

    name: str
    value: Expression
    type_annotation: TypeExpr | None = None


@dataclass(frozen=True, slots=True)
class EchoDecl(Declaration):
    """Transparent type alias declaration (using / typedef)."""

    name: str
    target_type: TypeExpr
    type_params: list[str] = field(default_factory=list)
    sigils: list[SigilParam] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SealDecl(Declaration):
    """Opaque newtype declaration."""

    name: str
    target_type: TypeExpr
    type_params: list[str] = field(default_factory=list)
    sigils: list[SigilParam] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class OmenVariant(Node):
    """Variant in an omen declaration."""

    name: str
    value: Expression | None = None


@dataclass(frozen=True, slots=True)
class OmenDecl(Declaration):
    """Scoped enumeration declaration (omen / flags omen)."""

    name: str
    variants: list[OmenVariant] = field(default_factory=list)
    underlying_type: TypeExpr | None = None
    is_flags: bool = False


@dataclass(frozen=True, slots=True)
class RuneField(Node):
    """Field declaration in a rune."""

    name: str
    type_annotation: TypeExpr
    default_value: Expression | None = None


@dataclass(frozen=True, slots=True)
class ConstructorDecl(Node):
    """Constructor lifecycle method in a rune."""

    params: list[Parameter] = field(default_factory=list)
    body: Block = field(default_factory=lambda: Block([]))


@dataclass(frozen=True, slots=True)
class DestructorDecl(Node):
    """Destructor lifecycle method in a rune."""

    body: Block = field(default_factory=lambda: Block([]))


@dataclass(frozen=True, slots=True)
class RuneDecl(Declaration):
    """Rune (struct) declaration."""

    name: str
    type_params: list[str] = field(default_factory=list)
    parent: TypeExpr | None = None
    fields: list[RuneField] = field(default_factory=list)
    constructor: ConstructorDecl | None = None
    destructor: DestructorDecl | None = None
    sigils: list[SigilParam] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class MethodDecl(Declaration):
    """Method declaration inside an enchanting block."""

    name: str
    function: FunctionLiteral
    is_mut: bool = False
    is_unsafe: bool = False


@dataclass(frozen=True, slots=True)
class OperatorDecl(Declaration):
    """Overloaded operator declaration (method or free)."""

    op: str
    function: FunctionLiteral
    is_mut: bool = False
    is_unsafe: bool = False


@dataclass(frozen=True, slots=True)
class EnchantingDecl(Declaration):
    """Enchanting block adding behavior to a type."""

    target_type: TypeExpr
    members: list[MethodDecl | OperatorDecl | ConstructorDecl | DestructorDecl] = field(
        default_factory=list
    )
    body: Block | Statement | None = None


# --- Module Root ---


@dataclass(frozen=True, slots=True)
class Module(Node):
    """Top-level module containing statements and declarations."""

    declarations: list[Node] = field(default_factory=list)

    @property
    def realm(self) -> RealmDecl | None:
        for d in self.declarations:
            if isinstance(d, RealmDecl):
                return d
        return None

    @property
    def imports(self) -> list[InvokeDecl]:
        return [d for d in self.declarations if isinstance(d, InvokeDecl)]
