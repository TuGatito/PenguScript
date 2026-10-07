"""The assembled :class:`PenguCodegen`.

A single object built from the mixins in this package: the public API and
the runtime behaviour are identical to those of the old monolithic
``pengu_codegen.py``.
"""
from __future__ import annotations

from .symbols import SymbolMixin
from .declarations import CollectMixin
from .lambdas import LambdaMixin
from .types_gen import TypesMixin
from .derived_gen import DerivedGenMixin
from .constants import ConstMixin
from .prototypes import ProtoMixin
from .exprs import ExprMixin
from .interpolate import InterpMixin
from .slicing import SlicingMixin
from .calls import CallMixin
from .stmts import StmtMixin
from .loops import LoopMixin
from .value_if import ValueIfMixin
from .bindings import BindingMixin
from .or_block import OrBlockMixin
from .runtime_helpers import RuntimeMixin
from .line_markers import LineMarkerMixin
from .tests_gen import TestsMixin
from .entry import EntryMixin
from .bundle import BundleMixin

from ._base import (
    Any,
    CompileTimeEnv,
    ConstFolder,
    Dict,
    List,
    Optional,
    PENGU_EXPECTED_ABI_VERSION,
    Set,
    SymbolTable,
    Tree,
    Tuple,
    Type,
    default_env,
    os,
)
from .attributes import (
    _RELEASE_UNSAFE,
    set_restrict_keyword,
)
from .bindings import (
    BindingMixin,
)
from .bundle import (
    BundleMixin,
)
from .calls import (
    CallMixin,
)
from .constants import (
    ConstMixin,
)
from .declarations import (
    CollectMixin,
)
from .derived_gen import (
    DerivedGenMixin,
)
from .entry import (
    EntryMixin,
)
from .exprs import (
    ExprMixin,
)
from .interpolate import (
    InterpMixin,
)
from .lambdas import (
    LambdaMixin,
)
from .line_markers import (
    LineMarkerMixin,
)
from .loops import (
    LoopMixin,
)
from .or_block import (
    OrBlockMixin,
)
from .prototypes import (
    ProtoMixin,
)
from .runtime_helpers import (
    RuntimeMixin,
)
from .slicing import (
    SlicingMixin,
)
from .stmts import (
    StmtMixin,
)
from .symbols import (
    SymbolMixin,
)
from .tests_gen import (
    TestsMixin,
)
from .types_gen import (
    TypesMixin,
)
from .value_if import (
    ValueIfMixin,
)

class PenguCodegen(
    SymbolMixin,
    CollectMixin,
    LambdaMixin,
    TypesMixin,
    DerivedGenMixin,
    ConstMixin,
    ProtoMixin,
    ExprMixin,
    InterpMixin,
    SlicingMixin,
    CallMixin,
    StmtMixin,
    LoopMixin,
    ValueIfMixin,
    BindingMixin,
    OrBlockMixin,
    RuntimeMixin,
    LineMarkerMixin,
    TestsMixin,
    EntryMixin,
    BundleMixin,
):
    _VIEW_EXPR_RULES = (
        "var_ref", "field_access", "arrow_access", "self_arrow", "self_ref",
        "at_expr", "array_at_expr", "essence_of", "null_lit", "none_lit",
        "slice_at_expr",
    )
    def __init__(self, symbols: Optional[SymbolTable] = None, import_order: Optional[List[str]] = None, base_dir: str = ".",
                 compile_env: Optional[CompileTimeEnv] = None,
                 use_gnu_extensions: Optional[bool] = None,
                 target_compiler: str = ""):
        """Initializes code generator.

        Args:
            symbols: Semantic symbol table with resolved types.
            import_order: List of source files in topological dependency order.
            base_dir: Root directory of project.
            compile_env: Optional compile-time environment for 'when' clauses.
            use_gnu_extensions: Emit GNU statement expressions (default) or
                portable C99 via statement hoisting.  None = read the
                PENGU_STRICT_C99 environment variable.
            target_compiler: "gcc" | "clang" | "msvc" | "tcc" (attribute and
                restrict dialect); empty = infer from the environment.
        """
        self.symbols = symbols
        self.import_order = import_order or []
        self.base_dir = base_dir
        self.compile_env = compile_env if compile_env is not None else default_env()
        self.target_compiler = (target_compiler or os.environ.get("PENGU_TARGET_COMPILER", "") or "gcc").strip().lower()
        set_restrict_keyword(self.target_compiler)
        # ABI the generated bundle is compiled against; mirrored as a
        # _Static_assert so a stale libpengu_runtime.a fails at build time.
        self.expected_abi_version: int = PENGU_EXPECTED_ABI_VERSION
        self.debug_mode: bool = bool(getattr(self.compile_env, "is_debug", False))
        # Bounds/overflow checking is on by default in every profile; an
        # `unsafe:` block (or --release-unsafe) is the only way out.
        self.bounds_check_enabled: bool = not _RELEASE_UNSAFE
        self.overflow_check_enabled: bool = not _RELEASE_UNSAFE
        self._unsafe_depth: int = 0
        # Entry-as-main mode: only the *entry* module compiles with the
        # compile-time 'main' flag true (see _apply_main_flag). Defaults keep
        # every module compiled with 'main' false.
        self.entry_main_mode = False
        self.entry_file: Optional[str] = None
        # `#line` support: markers are emitted for statements (and top-level
        # items) so gcc/clang diagnostics point at the .pengu source. They are
        # suppressed inside expression contexts, where the generated code may be
        # a GCC statement-expression passed to a function-like macro
        # (`pengu_to_string(x)`), which a directive would break.
        self.emit_line_markers = True
        self.line_base_dir: Optional[str] = None
        self.current_source_file: Optional[str] = None
        self.bundle_display_path: Optional[str] = None
        self._expr_depth = 0
        self.const_folder = ConstFolder(symbols) if symbols else ConstFolder(SymbolTable())

        # Declarations registry
        self.runes: Dict[str, Dict[str, Type]] = {}
        self.rune_attributes: Dict[str, Dict[str, List[Any]]] = {}
        self.rune_field_attributes: Dict[str, Dict[str, Dict[str, List[Any]]]] = {}
        # Source file of each rune: std/binding runes manage memory explicitly
        # (free_* helpers), so they do not get the implicit Imago/Nexus.
        self._rune_file_paths: Dict[str, str] = {}
        self.echos: Dict[str, Dict[str, Type]] = {}
        self.omens: Dict[str, Dict[str, Dict[str, Type]]] = {}
        self.omen_values: Dict[str, Dict[str, int]] = {}
        self.aliases: Dict[str, Type] = {}
        self.seals: Dict[str, Type] = {}
        self.concepts: Dict[str, Any] = {}
        self.consts: Dict[str, Tuple[Optional[Type], Any]] = {}
        self.const_nodes: Dict[str, Tree] = {}
        self.declaration_types: Set[str] = set()
        self.declaration_consts: Set[str] = set()
        self.c_defines: List[str] = []
        self.weaves: List[Dict[str, Any]] = []
        # Dead-code elimination of unused std/lib weaves (pengu_dce.py).
        # PENGU_NO_DCE=1 disables it (bug reports, A/B comparisons).
        _no_dce = os.environ.get("PENGU_NO_DCE", "").strip().lower() in {"1", "true", "yes", "on"}
        self.dce_enabled = not _no_dce
        self.dce_stats: Dict[str, Any] = {}
        self.fn_info: Dict[str, Dict[str, Any]] = {}
        self.tests: List[Dict[str, Any]] = []
        self.includes: List[str] = []
        self.links: List[str] = []
        self.has_main = False
        # Return type of 'weave main', used as the process exit status.
        self.main_return_type: Optional[Type] = None
        # Lambda expressions compile to top-level 'static' C functions (no
        # capture, so no GCC nested functions): 'lambdas' collects their
        # definitions and '_lambda_counter' names them uniquely.
        self.lambdas: List[str] = []
        self._lambda_counter = 0

        # Translation state
        self.current_function: Optional[str] = None
        self.current_return_type: Optional[Type] = None
        self.current_enchanted_type: Optional[Type] = None
        self.local_vars: Dict[str, Type] = {}
        self.indent_level = 0
        self.defer_stack: List[List[str]] = []
        self.errdefer_stack: List[List[str]] = []
        self.with_stack: List[str] = []
        self.with_type_stack: List[Optional[Type]] = []
        # Statement hoisting (roadmap 2.1.a): when strict C99 mode is active the
        # code generator must not emit GNU statement expressions `({ ... })`.
        # Constructs that need statements accumulate them here and return a
        # simple temporary; `_translate_stmt` flushes the prelude before the
        # statement that owns the expression.
        self.expr_prelude: List[str] = []
        # GNU statement expressions are the default (they keep the generated C
        # compact).  `--strict-c99` / `PENGU_STRICT_C99=1` switches to portable
        # C99 by hoisting expression statements into the enclosing statement.
        if use_gnu_extensions is None:
            self.use_gnu_extensions = (
                os.environ.get("PENGU_STRICT_C99", "").strip().lower()
                not in {"1", "true", "yes", "on"}
            )
        else:
            # An explicit False always means strict; PENGU_STRICT_C99=1 is a
            # debug override that forces strict even if the caller passed True.
            env_strict = (
                os.environ.get("PENGU_STRICT_C99", "").strip().lower()
                in {"1", "true", "yes", "on"}
            )
            self.use_gnu_extensions = bool(use_gnu_extensions) and not env_strict
        self.temp_counter = 0
