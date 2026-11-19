"""Unit tests for Analysis Sub-fase 1: ASTVisitor, symbols, prelude, and Collector."""

from __future__ import annotations

from pathlib import Path

from penguscript.analysis.collector import collect
from penguscript.analysis.diagnostics import Diagnostic, Label
from penguscript.analysis.prelude import (
    BUILTIN_CONSTANTS,
    BUILTIN_PRIMITIVES,
    get_prelude_scope,
    get_prelude_symbols,
)
from penguscript.analysis.symbols import (
    Scope,
    ScopeKind,
    Symbol,
    SymbolId,
    SymbolKind,
)
from penguscript.analysis.visitor import ASTVisitor
from penguscript.frontend.ast_nodes import ConstDecl, IntLit, Node
from penguscript.frontend.parser import parse
from penguscript.frontend.span import Span

FIXTURES_COLLECT_DIR = Path(__file__).parent.parent.parent / "fixtures" / "symbols" / "collect"


def test_ast_visitor_custom_and_fallback() -> None:
    """Test ASTVisitor dispatch to custom visit_<Node> and generic_visit."""
    visited: list[str] = []

    class CountingVisitor(ASTVisitor):
        def visit_const_decl(self, node: ConstDecl) -> None:
            visited.append(f"const:{node.name}")
            self.generic_visit(node)

        def visit_int_lit(self, node: IntLit) -> None:
            visited.append(f"int:{node.value}")

    mod = parse("const A = 10\nconst B = 20\n")
    visitor = CountingVisitor()
    visitor.visit(mod)

    assert visited == ["const:A", "int:10", "const:B", "int:20"]


def test_ast_visitor_handles_none_and_non_node() -> None:
    """Test ASTVisitor gracefully handles None and non-node items."""
    visitor = ASTVisitor()
    assert visitor.visit(None) is None

    class EmptyNode(Node):
        pass

    node = EmptyNode()
    visitor.visit(node)


def test_prelude_types_and_constants() -> None:
    """Verify that all primitive types and constants from cheatsheet are registered."""
    symbols = get_prelude_symbols()

    # Primitives & integers
    assert "int" in symbols
    assert "double" in symbols
    assert "bool" in symbols
    assert "string" in symbols
    assert "void" in symbols
    assert "size_t" in symbols
    assert "uint8_t" in symbols
    assert "u32" in symbols

    # Containers
    assert "vector" in symbols
    assert "map" in symbols
    assert "set" in symbols
    assert "tuple" in symbols

    # Pointers & refs
    assert "unique" in symbols
    assert "shared" in symbols
    assert "ref" in symbols
    assert "raw" in symbols

    # Constants
    assert "true" in symbols
    assert "false" in symbols
    assert "none" in symbols
    assert "nullptr" in symbols

    for name in BUILTIN_PRIMITIVES:
        assert name in symbols, f"Missing primitive '{name}'"
        assert symbols[name].kind == SymbolKind.BUILTIN_TYPE

    for name in BUILTIN_CONSTANTS:
        assert name in symbols, f"Missing constant '{name}'"
        assert symbols[name].kind == SymbolKind.CONST

    scope = get_prelude_scope()
    assert scope.kind == ScopeKind.PRELUDE
    assert scope.lookup("vector") is not None


def test_scope_lookup_chain() -> None:
    """Verify lexical scope lookup through parent hierarchy."""
    parent = Scope(kind=ScopeKind.MODULE)
    child = Scope(kind=ScopeKind.BLOCK, parent=parent)

    sym_span = Span(start_byte=0, end_byte=1, line=1, col=1)
    global_sym = Symbol(
        id=SymbolId(Path("main.pengu"), sym_span),
        name="global_var",
        kind=SymbolKind.CONST,
    )
    local_sym = Symbol(
        id=SymbolId(Path("main.pengu"), sym_span),
        name="local_var",
        kind=SymbolKind.LOCAL,
    )

    parent.define(global_sym)
    child.define(local_sym)

    assert child.lookup("local_var") == local_sym
    assert child.lookup("global_var") == global_sym
    assert child.lookup_local("global_var") is None
    assert parent.lookup("local_var") is None


def test_collector_good_shapes() -> None:
    """Validate Pass 1 collection on comprehensive shapes fixture."""
    file = FIXTURES_COLLECT_DIR / "good" / "shapes.pengu"
    text = file.read_text(encoding="utf-8")
    mod = parse(text)

    raw = collect(mod, path=file)

    assert raw.declared_realm == "geometry"
    assert raw.is_explicit_realm is True
    assert len(raw.diagnostics) == 0, [str(d) for d in raw.diagnostics]

    # Verify top-level symbols
    assert "PI" in raw.symbols
    assert raw.symbols["PI"].kind == SymbolKind.CONST

    assert "Distance" in raw.symbols
    assert raw.symbols["Distance"].kind == SymbolKind.ECHO

    assert "Angle" in raw.symbols
    assert raw.symbols["Angle"].kind == SymbolKind.SEAL

    assert "Color" in raw.symbols
    assert raw.symbols["Color"].kind == SymbolKind.OMEN
    assert "Red" in raw.omen_variants["Color"]
    assert "Green" in raw.omen_variants["Color"]
    assert "Blue" in raw.omen_variants["Color"]

    assert "RenderFlags" in raw.symbols
    assert raw.symbols["RenderFlags"].kind == SymbolKind.OMEN
    assert "Visible" in raw.omen_variants["RenderFlags"]

    assert "Point" in raw.symbols
    assert raw.symbols["Point"].kind == SymbolKind.RUNE
    assert "x" in raw.rune_fields["Point"]
    assert "y" in raw.rune_fields["Point"]
    assert "distance" in raw.rune_methods["Point"]
    assert "translate" in raw.rune_methods["Point"]
    assert raw.rune_methods["Point"]["translate"].is_mut is True

    assert "distance_squared" in raw.symbols
    assert raw.symbols["distance_squared"].kind == SymbolKind.FUNCTION
    assert raw.symbols["distance_squared"].sigils == ("T",)


def test_collector_implicit_realm() -> None:
    """Validate implicit realm derivation from file path."""
    file = FIXTURES_COLLECT_DIR / "good" / "implicit_realm.pengu"
    text = file.read_text(encoding="utf-8")
    mod = parse(text)

    raw = collect(mod, path=file)
    assert raw.declared_realm == "implicit_realm"
    assert raw.is_explicit_realm is False
    assert "VERSION" in raw.symbols
    assert "calculate" in raw.symbols
    assert len(raw.diagnostics) == 0


def test_collector_index_implicit_realm() -> None:
    """Validate implicit realm derivation for index.pengu files."""
    code = "const A = 1\n"
    mod = parse(code)
    raw = collect(mod, path=Path("utils/strings/index.pengu"))
    assert raw.declared_realm == "strings"
    assert raw.is_explicit_realm is False


def test_collector_bad_fixtures() -> None:
    """Verify that bad fixtures in collect/ produce corresponding diagnostic error codes."""
    bad_dir = FIXTURES_COLLECT_DIR / "bad"
    files = sorted(bad_dir.glob("*.pengu"))
    assert len(files) >= 10, f"Expected at least 10 bad fixtures, got {len(files)}"

    expected_codes = {
        "duplicate_symbol.pengu": "E2201",
        "duplicate_field.pengu": "E2202",
        "duplicate_variant.pengu": "E2203",
        "duplicate_method.pengu": "E2204",
        "method_field_collision.pengu": "E2205",
        "duplicate_sigil.pengu": "E2210",
        "sigil_name_collision.pengu": "E2211",
        "self_inheritance.pengu": "E2212",
        "bad_flags_power_of_two.pengu": "E2216",
        "duplicate_param.pengu": "E2219",
        "reserved_realm_name.pengu": "E2103",
    }

    for file in files:
        text = file.read_text(encoding="utf-8")
        mod = parse(text)
        raw = collect(mod, path=file)
        expected_code = expected_codes.get(file.name)
        assert len(raw.diagnostics) > 0, f"{file.name} did not emit any diagnostics"
        codes = [d.code for d in raw.diagnostics]
        if expected_code:
            assert expected_code in codes, (
                f"{file.name}: expected code {expected_code}, got {codes}"
            )


def test_diagnostic_formatting_with_secondary_labels() -> None:
    """Verify rich diagnostic output with secondary label pointers."""
    span1 = Span(start_byte=10, end_byte=18, line=2, col=7)
    span2 = Span(start_byte=35, end_byte=43, line=3, col=7)
    source = "realm test\nconst FOO = 1\nconst FOO = 2\n"

    diag = Diagnostic(
        code="E2201",
        message="Duplicate top-level symbol 'FOO'",
        span=span2,
        source_file="test.pengu",
        secondary_labels=(Label(span=span1, message="previously declared here"),),
        notes=("Realms merge across files",),
        hint="Rename one of the declarations",
    )

    rendered = diag.format(source_text=source, filename="test.pengu")

    assert "error[E2201]: Duplicate top-level symbol 'FOO'" in rendered
    assert "--> test.pengu:3:7" in rendered
    assert "3 | const FOO = 2" in rendered
    assert "2 | const FOO = 1" in rendered
    assert "previously declared here" in rendered
    assert "= note: Realms merge across files" in rendered
    assert "= help: Rename one of the declarations" in rendered
