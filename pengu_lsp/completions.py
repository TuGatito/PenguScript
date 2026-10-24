"""PenguScript LSP Autocomplete and Completion Logic."""

import os
import re
import time
from typing import Dict, List, Optional, Tuple
from lsprotocol.types import (
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    InsertTextFormat,
    Position,
    Range,
    TextEdit,
)
from pengu_parser.pengu_symbols import SymbolTable, Symbol, SHARD_RECEIVER_KEY
from .judge_over import judge_over_completions
from .labels import loop_label_completions
from pengu_parser.pengu_types import (
    BaseType,
    RuneType,
    EchoType,
    OmenType,
    RefType,
    FnType,
    canonical_primitive_name,
    get_type_base_name,
    implements_concept,
    primitive_lookup_order,
)

# Repository root (parent of pengu_lsp/); the standard library lives under it.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STD_DIR = os.path.join(_REPO_ROOT, "std")

# Cached (base_dir -> list of import specs) so repeated completions do not
# rescan the filesystem on every keystroke.
_MODULE_SPEC_CACHE: Dict[str, Tuple[float, List[str]]] = {}
_MODULE_CACHE_TTL_S = 5.0


def _module_spec_from_path(file_path: str, base_dir: str) -> Optional[str]:
    """Computes the dotted import spec for a module file.

    ``<base>/std/spark.pengu`` -> ``std.spark``; ``<base>/src/components/
    player.pengu`` -> ``components.player``. Files named ``<name>.d.pengu``
    (pure C-binding declaration files) lose their trailing ``.d`` so the spec
    reads ``std.binding`` instead of ``std.binding.d``.

    Args:
        file_path: Absolute path to the module file.
        base_dir: Directory the spec is relative to.

    Returns:
        The dotted import spec, or None when the file is not inside base_dir.
    """
    fp = os.path.abspath(file_path)
    base = os.path.abspath(base_dir) if base_dir else os.getcwd()
    try:
        rel = os.path.relpath(fp, base)
    except ValueError:
        return None
    if rel == os.pardir or rel.startswith(".." + os.sep):
        return None
    parts = [p for p in re.split(r"[\\/]", rel) if p]
    if not parts:
        return None
    name = parts[-1]
    if name.endswith(".d.pengu"):
        name = name[: -len(".d.pengu")] + ".pengu"
    if not name.endswith(".pengu"):
        return None
    stem = name[: -len(".pengu")]
    parts[-1] = stem
    return ".".join(parts)


def _available_module_specs(base_dir: str, include_stdlib: bool = True) -> List[str]:
    """Returns the import specs of every importable module for a project.

    Scans the standard library (``<repo>/std``) and the project sources
    (``<base>/src`` when it exists, plus ``<base>`` itself when it does not
    point into the repository). Results are cached briefly per base directory.

    Args:
        base_dir: Project root directory.
        include_stdlib: Whether to include ``std.*`` modules (default True).

    Returns:
        Sorted list of dotted import specs (e.g. ``std.spark``,
        ``components.player``).
    """
    global _MODULE_SPEC_CACHE
    now = time.time()
    cached = _MODULE_SPEC_CACHE.get(base_dir)
    if cached is not None and now - cached[0] < _MODULE_CACHE_TTL_S:
        return cached[1]

    specs: List[str] = []
    seen_dirs = set()

    def _scan(root: str, spec_base: str) -> None:
        root = os.path.abspath(root)
        if not os.path.isdir(root) or root in seen_dirs:
            return
        seen_dirs.add(root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d for d in dirnames if not d.startswith("_") and not d.startswith(".")
            ]
            for fname in sorted(filenames):
                if fname.startswith("_"):
                    continue
                if not (fname.endswith(".pengu") or fname.endswith(".d.pengu")):
                    continue
                spec = _module_spec_from_path(os.path.join(dirpath, fname), spec_base)
                if spec:
                    specs.append(spec)

    std_root = os.path.abspath(_STD_DIR)
    if include_stdlib and os.path.isdir(std_root):
        _scan(std_root, os.path.dirname(std_root))  # specs read std.<stem>

    base = os.path.abspath(base_dir) if base_dir else os.getcwd()
    base_parent = os.path.dirname(std_root)
    if base != base_parent and base != std_root:
        src_dir = os.path.join(base, "src")
        if os.path.isdir(src_dir):
            # Files under <base>/src import as components.player (no src prefix).
            _scan(src_dir, src_dir)
        else:
            _scan(base, base)  # loose script folder: files directly under it

    specs = sorted(set(specs))
    if len(_MODULE_SPEC_CACHE) > 64:
        _MODULE_SPEC_CACHE.clear()
    _MODULE_SPEC_CACHE[base_dir] = (now, specs)
    return specs


def _type_default_expr(t) -> str:
    """A sensible default initializer for a field type (used by snippets)."""
    name = str(getattr(t, "name", ""))
    while hasattr(t, "target") and getattr(t, "target", None) is not None:
        t = t.target
        name = str(getattr(t, "name", name))
    if name in ("bool",):
        return "false"
    if name in ("string",):
        return '""'
    if name in ("char",):
        return "''"
    if name in (
        "float", "double", "f32", "f64",
    ):
        return "0.0"
    if name in (
        "int", "i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64",
        "usize", "isize", "byte", "short", "long", "int32_t", "int64_t",
        "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    ):
        return "0"
    return "null"


def _unwrap_type(t):
    while isinstance(t, RefType):
        t = t.target
    return t


def _rune_fields_for(symbols, type_name: str):
    """Returns ``{field: Type}`` for a rune type name, or None."""
    if symbols is None:
        return None
    runes = getattr(symbols, "runes", {})
    if type_name in runes:
        fields = runes[type_name]
        if isinstance(fields, dict):
            return {k: v for k, v in fields.items() if not k.startswith("_")}
    try:
        lookup_type = getattr(symbols, "lookup_type", None)
        t = lookup_type(type_name) if lookup_type else None
    except Exception:
        t = None
    if t is not None:
        t = _unwrap_type(t)
        if isinstance(t, RuneType):
            return {k: v for k, v in t.fields.items() if not k.startswith("_")}
    return None


def _current_document_path(uri: str) -> Optional[str]:
    """Absolute path of the document being completed, or None for non-files."""
    try:
        from urllib.parse import unquote, urlparse

        parsed = urlparse(uri)
        if parsed.scheme == "file":
            return os.path.abspath(unquote(parsed.path))
    except Exception:
        pass
    return None


def _belongs_to_document(sym, current_path: Optional[str]) -> bool:
    """False for symbols collected from an imported module.

    The checker registers every imported module's top-level functions and types
    in the document's own symbol table (unqualified) so that code generation and
    type resolution can see them.  Listing all of them in plain identifier
    completion turned every keystroke into ~2 500 items (1 447 functions from
    five std imports) and buried the user's own names.  Import aliases are kept:
    they are exactly what the user types before a dot.
    """
    if current_path is None:
        return True
    if getattr(sym, "kind", "") == "import":
        return True
    file_path = getattr(sym, "file_path", None)
    if not file_path:
        return True
    try:
        return os.path.abspath(file_path) == current_path
    except Exception:
        return True


def _lookup_at(symbols, name: str, cursor_line: int):
    if symbols is None:
        return None
    try:
        if hasattr(symbols, "lookup_at"):
            return symbols.lookup_at(name, cursor_line)
        return symbols.lookup(name)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Methods of a receiver type
# ---------------------------------------------------------------------------
#
# Dot completion used to answer only for `rune` / `echo` / `omen` receivers, so
# `x.clamp` on a `float` — or anything else whose methods come from an
# `enchanting` block in an imported module — completed to nothing. The tables
# below mirror the keys the checker resolves against.

#: `T`, `K`, `V`, `E`: the type-parameter spellings a generic block registers
#: under (`enchanting map of shard K to shard V where …:` -> 'map of K to V').
_TYPE_PARAMETER = re.compile(r"^[A-Z][A-Z0-9_]*$")

#: Methods the inferrer hardcodes for containers, so no `enchanting` block
#: declares them and no symbol table carries them.
_BUILTIN_METHODS = {
    "list": ("push", "append", "pop", "clear", "len", "is_empty", "contains", "index_of", "at"),
    "slice": ("len", "is_empty", "at"),
    "array": ("len", "is_empty", "at"),
    "map": ("put", "insert", "set", "get", "remove", "contains", "contains_key", "has", "len", "clear", "is_empty"),
}


def _receiver_keys(t) -> List[str]:
    """Method-table keys a receiver of type ``t`` resolves against."""
    keys: List[str] = []
    for candidate in primitive_lookup_order(t):
        if candidate not in keys:
            keys.append(candidate)
    name = getattr(t, "name", None)
    if isinstance(name, str) and name and name not in keys:
        keys.append(name)
    base = get_type_base_name(t)
    if base and base not in keys:
        keys.append(base)
    return keys


def _generic_receiver_matches(key: str, receiver: str) -> bool:
    """True when a generic receiver key covers ``receiver``.

    ``'map of K to V'`` covers ``'map of string to int'`` (both parameters are
    wildcards) but not ``'map of int to string'``, whose concrete halves must
    match position by position.
    """
    if key == receiver:
        return True
    key_parts = re.split(r"\s+of\s+|\s+to\s+", key)
    recv_parts = re.split(r"\s+of\s+|\s+to\s+", receiver)
    if len(key_parts) != len(recv_parts):
        return False
    return all(
        k == r or _TYPE_PARAMETER.match(k)
        for k, r in zip(key_parts, recv_parts)
    )


def _shard_method_applies(symbols, method: str, t) -> bool:
    """True when a bare ``enchanting shard T where …:`` method covers ``t``."""
    canonical = canonical_primitive_name(t)
    if canonical is None:
        return False
    bounds = getattr(symbols, "shard_method_bounds", {}).get((SHARD_RECEIVER_KEY, method), {})
    concrete = BaseType(canonical)
    for bound_list in bounds.values():
        for bound in bound_list:
            if not implements_concept(concrete, bound, symbols):
                return False
    return True


def _method_item(name: str, signature) -> CompletionItem:
    return CompletionItem(
        label=name,
        kind=CompletionItemKind.Method,
        detail=f"method {signature}" if signature else "method",
        insert_text=name,
    )


def _method_items_for_type(symbols, t) -> List[CompletionItem]:
    """Every method callable on a receiver of type ``t``.

    Covers the four ways the checker learns a method: a concrete
    ``enchanting <T>:`` block, a ``enchanting shard T where …:`` block whose
    bounds ``t`` satisfies, a container block (``list of shard T``,
    ``map of shard K to shard V``), and the container methods the inferrer
    hardcodes.

    Args:
        symbols: Checked SymbolTable.
        t: Receiver type (references already unwrapped).

    Returns:
        Completion items, one per method, deduplicated by name.
    """
    items: Dict[str, CompletionItem] = {}
    if symbols is None or t is None:
        return []
    receiver = getattr(t, "name", None) or str(t)
    keys = set(_receiver_keys(t))

    for (key, name), signature in getattr(symbols, "methods", {}).items():
        if key in keys or _generic_receiver_matches(key, receiver):
            items.setdefault(name, _method_item(name, signature))
    for (key, name), entry in getattr(symbols, "generic_methods", {}).items():
        if key in keys or _generic_receiver_matches(key, receiver):
            items.setdefault(name, _method_item(name, None))
        elif key == SHARD_RECEIVER_KEY and _shard_method_applies(symbols, name, t):
            items.setdefault(name, _method_item(name, None))

    base = get_type_base_name(t)
    for name in _BUILTIN_METHODS.get(base, ()):
        items.setdefault(name, _method_item(name, None))
    return list(items.values())


def _judge_context_items(doc_text: Optional[str], position: Position, symbols) -> Optional[List[CompletionItem]]:
    """Suggests omen variants / booleans for ``when`` clauses of a ``judge``.

    Walks upward from the cursor for the nearest ``judge <subject>:`` line and
    resolves the subject's type from the symbol table: an omen offers its
    variants (as ``EnumMember``), a bool offers ``true``/``false``. An
    ``else ->`` keyword item is always offered while inside the judge block.

    Args:
        doc_text: Full document text (needed to find the judge subject).
        position: Cursor position.
        symbols: Checked SymbolTable (for subject type resolution).

    Returns:
        Completion items, or None when not inside a judge block.
    """
    if not doc_text:
        return None
    lines = doc_text.splitlines()
    if not (0 <= position.line < len(lines)):
        return None
    prefix = lines[position.line][: position.character]

    # Only active while typing a clause start on its own line.
    stripped = prefix.strip()
    typed = ""
    if re.match(r"^when\s*$", stripped):
        typed = ""
    else:
        m = re.match(r"^when\s+([A-Za-z_][A-Za-z0-9_]*)$", stripped)
        if not m:
            return None
        typed = m.group(1)

    # Find the nearest 'judge <subject>:' above this line.
    subject = None
    for i in range(position.line - 1, max(-1, position.line - 60), -1):
        s = lines[i].strip()
        if not s:
            continue
        if s.endswith(":"):
            m = re.search(r"\bjudge\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*$", s)
            if m:
                subject = m.group(1)
                break
            # A non-judge colon at a shallower indent closes the block.
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= len(prefix) - len(prefix.lstrip()):
                break
    if subject is None:
        return None

    sym = _lookup_at(symbols, subject, position.line)  # cursor line approx
    if sym is None:
        return None
    t = _unwrap_type(sym.type)
    items: List[CompletionItem] = []
    if isinstance(t, OmenType):
        for v_name in (t.variants or {}):
            if typed and not v_name.startswith(typed):
                continue
            items.append(
                CompletionItem(
                    label=v_name,
                    kind=CompletionItemKind.EnumMember,
                    detail=f"variant of {t.name}",
                    insert_text=f"{v_name} -> ",
                )
            )
    elif isinstance(t, BaseType) and t.name == "bool":
        for lit in ("true", "false"):
            if typed and not lit.startswith(typed):
                continue
            items.append(
                CompletionItem(label=lit, kind=CompletionItemKind.Keyword, insert_text=f"{lit} -> ")
            )
    else:
        return None
    items.append(
        CompletionItem(
            label="else ->", kind=CompletionItemKind.Keyword,
            detail="default branch", insert_text="else -> ",
        )
    )
    return items or None


def _rune_with_field_items(symbols, line_prefix: str) -> Optional[List[CompletionItem]]:
    """Suggests fields after ``var x as Type is with `` (rune initializer)."""
    m = re.search(
        r"(?:var|let)\s+[A-Za-z_][A-Za-z0-9_]*\s+as\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s+is\s+with\s*$",
        line_prefix,
    )
    if not m:
        return None
    fields = _rune_fields_for(symbols, m.group(1))
    if not fields:
        return None
    items: List[CompletionItem] = []
    for f_name, f_type in fields.items():
        items.append(
            CompletionItem(
                label=f_name,
                kind=CompletionItemKind.Field,
                detail=str(f_type),
                insert_text=f"{f_name} is {_type_default_expr(f_type)}",
            )
        )
    # 'Fill all fields' snippet.
    all_fields = " and ".join(
        f"{n} is {_type_default_expr(t)}" for n, t in fields.items()
    )
    items.append(
        CompletionItem(
            label="(all fields)",
            kind=CompletionItemKind.Snippet,
            detail=f"fill {len(fields)} fields",
            insert_text=all_fields,
            sort_text="~~~",
        )
    )
    return items


def _with_block_field_items(doc_text: Optional[str], position: Position, symbols) -> Optional[List[CompletionItem]]:
    """Suggests rune fields when typing ``set .`` inside a ``with target:`` block."""
    if not doc_text:
        return None
    lines = doc_text.splitlines()
    if not (0 <= position.line < len(lines)):
        return None
    prefix = lines[position.line][: position.character]
    if not re.search(r"\bset\.$", prefix):
        return None
    cursor_indent = len(prefix) - len(prefix.lstrip())
    # Walk up to the nearest enclosing 'with <name>:'.
    for i in range(position.line - 1, -1, -1):
        raw = lines[i]
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        if stripped and indent >= cursor_indent:
            continue
        m = re.match(r"^with\s+([A-Za-z_][A-Za-z0-9_.]*)\s*:\s*$", stripped)
        if m:
            target = m.group(1).split(".")[-1]
            sym = _lookup_at(symbols, target, i + 1)
            fields = None
            if sym is not None:
                t = _unwrap_type(sym.type)
                if isinstance(t, RuneType):
                    fields = {k: v for k, v in t.fields.items() if not k.startswith("_")}
            if fields is None:
                fields = _rune_fields_for(symbols, str(getattr(sym.type, "name", "")) if sym else None)
            if fields:
                return [
                    CompletionItem(
                        label=f_name,
                        kind=CompletionItemKind.Field,
                        detail=str(f_type),
                        insert_text=f_name,
                    )
                    for f_name, f_type in fields.items()
                ]
            return []
        if indent < cursor_indent:
            break
    return None


def _import_completion_items(base_dir: str, line_prefix: str, position: Position) -> Optional[List[CompletionItem]]:
    """Builds module completions when the cursor follows an ``import``.

    Returns None when the current line is not an import context.

    Args:
        base_dir: Project root used to resolve available modules.
        line_prefix: Text before the cursor on the current line.
        position: Cursor position (used to size the replacement range).

    Returns:
        Module CompletionItems, or None when not in an import context.
    """
    m = re.search(r"\bimport\s+(?:([A-Za-z_][A-Za-z0-9_.]*))?$", line_prefix)
    if m is None:
        return None
    typed = m.group(1) or ""

    # Guard: the caret sits after `import` with no module text yet.
    items: List[CompletionItem] = []
    if not base_dir:
        base_dir = os.getcwd()
    all_specs = _available_module_specs(base_dir)

    replace_start = position.character - len(typed)
    if replace_start < 0:
        replace_start = 0

    for spec in all_specs:
        if typed and not spec.startswith(typed):
            continue
        # After `import std.` only offer std modules; the label drops the
        # std. prefix so it reads like the identifier the user completes.
        if typed.startswith("std."):
            label = spec[len("std."):]
            replace_text = spec
        else:
            label = spec
            replace_text = spec
        items.append(
            CompletionItem(
                label=label,
                kind=CompletionItemKind.Module,
                detail=spec,
                documentation=None,
                insert_text=replace_text,
                insert_text_format=InsertTextFormat.PlainText,
                text_edit=TextEdit(
                    new_text=replace_text,
                    range=Range(
                        start=Position(line=position.line, character=replace_start),
                        end=Position(line=position.line, character=position.character),
                    ),
                ),
            )
        )
    items.sort(key=lambda it: it.label)
    return items


BASE_KEYWORDS = [
    # Top-level declarations
    ("weave", "weave ${1:name} with ${2:a as int} into ${3:void}:\n\t${0}", "Declare a function (weave)", CompletionItemKind.Snippet),
    ("rune", "rune ${1:Name}:\n\t${2:field} as ${3:int}", "Declare a struct (rune)", CompletionItemKind.Snippet),
    ("echo", "echo ${1:Name}:\n\t${2:field} as ${3:int}", "Declare a union (echo)", CompletionItemKind.Snippet),
    ("omen", "omen ${1:Result}:\n\tOk with value as ${2:int}\n\tErr with msg as string", "Declare an algebraic data type (omen)", CompletionItemKind.Snippet),
    ("alias", "alias ${1:NewType} as ${2:int}", "Declare a type alias", CompletionItemKind.Snippet),
    ("enchanting", "enchanting ${1:Type}:\n\tweave ${2:method} into ${3:void}:\n\t\t${0}", "Attach methods to a type", CompletionItemKind.Snippet),
    ("declare", "declare ${1:c_func} with ${2:a as int} into ${3:void}", "Declare external C function", CompletionItemKind.Snippet),
    ("import", "import ${1:module}", "Import another PenguScript module", CompletionItemKind.Snippet),
    ("include", 'include "${1:header.h}"', "Include a C header file", CompletionItemKind.Snippet),
    ("link", 'link "${1:library}"', "Link an external library", CompletionItemKind.Snippet),

    # Local statements
    ("var", "var ${1:name} as ${2:int} is ${3:0}", "Declare a mutable local variable", CompletionItemKind.Snippet),
    ("let", "let ${1:name} as ${2:int} is ${3:0}", "Declare an immutable local binding", CompletionItemKind.Snippet),
    ("const", "const ${1:NAME} as ${2:int} is ${3:0}", "Declare a top-level constant", CompletionItemKind.Snippet),
    ("set", "set ${1:target} is ${2:value}", "Reassign a mutable variable or field", CompletionItemKind.Snippet),
    ("with", "with ${1:target}:\n\tset ${2:field} is ${3:value}", "Scope field access for target", CompletionItemKind.Snippet),
    ("do", "do:\n\t${1:statement}\n\t${0}", "Statement block expression (evaluates to its last expression)", CompletionItemKind.Snippet),
    ("if", "if ${1:condition}:\n\t${0}", "Conditional statement", CompletionItemKind.Snippet),
    ("ifx", "if ${1:condition}:\n\t${2:value}\nelse:\n\t${0}", "If/else block expression (each branch ends in a value of a common type)", CompletionItemKind.Snippet),
    ("unless", "unless ${1:condition}:\n\t${0}", "Negative conditional statement", CompletionItemKind.Snippet),
    ("while", "while ${1:condition}:\n\t${0}", "While loop", CompletionItemKind.Snippet),
    ("for", "for ${1:item} in ${2:collection}:\n\t${0}", "For-in loop", CompletionItemKind.Snippet),
    ("when", "when ${1:condition}:\n\t${0}", "Compile-time conditional", CompletionItemKind.Snippet),
    ("judge", "judge ${1:expr}:\n\twhen ${2:pattern} -> ${3:result}\n\telse -> ${0}", "Pattern matching expression", CompletionItemKind.Snippet),
    ("defer", "defer ${1:action}", "Defer execution to scope exit", CompletionItemKind.Snippet),
    ("errdefer", "errdefer ${1:action}", "Defer execution on error return", CompletionItemKind.Snippet),
    ("banish", "banish ${1:pointer}", "Explicitly free heap memory", CompletionItemKind.Snippet),
    ("return", "return ${0}", "Return from function", CompletionItemKind.Keyword),
    ("break", "break", "Break out of loop", CompletionItemKind.Keyword),
    ("continue", "continue", "Continue next loop iteration", CompletionItemKind.Keyword),

    # Keywords and Operators
    ("self", "self", "Current instance reference", CompletionItemKind.Keyword),
    ("self->", "self->${1:field}", "Access field through self reference", CompletionItemKind.Snippet),
    ("sigil of", "sigil of ${1:var}", "Take pointer reference (&)", CompletionItemKind.Snippet),
    ("essence of", "essence of ${1:ptr}", "Dereference pointer (*)", CompletionItemKind.Snippet),
    ("calling", "calling ${1:func} with ${2:arg}", "Function invocation", CompletionItemKind.Snippet),
    ("some", "some ${1:value}", "Present optional value (maybe T)", CompletionItemKind.Snippet),
    ("maybe none", "maybe none", "Empty optional value", CompletionItemKind.Keyword),
    ("ok_of", "calling ok_of with ${1:value}", "Success side of a result of T to E", CompletionItemKind.Snippet),
    ("err_of", "calling err_of with ${1:error}", "Failure side of a result of T to E", CompletionItemKind.Snippet),
    ("error", "error", "Error literal", CompletionItemKind.Keyword),
    ("transmute", "transmute ${1:expr} as ${2:type}", "Unsafe bitwise cast", CompletionItemKind.Snippet),
]

BASE_TYPES = [
    ("int", "32-bit signed integer"),
    ("i32", "32-bit signed integer"),
    ("i64", "64-bit signed integer"),
    ("float", "64-bit floating point number"),
    ("f32", "32-bit floating point number"),
    ("f64", "64-bit floating point number"),
    ("bool", "Boolean (true / false)"),
    ("string", "PenguScript heap/stack string"),
    ("void", "Empty / return nothing"),
    ("list of", "Dynamic growable array (list of T)"),
    ("array of", "Fixed size array (array of T with size N)"),
    ("slice of", "Contiguous view into array (slice of T)"),
    ("map of", "Hash map (map of Key to Value)"),
    ("maybe", "Optional value (maybe T)"),
    ("result of", "Result or Error (result of T to E)"),
    ("ref to", "Pointer reference (ref to T)"),
    ("opaque", "Opaque C handle / pointer"),
]


def _type_items(symbols: Optional[SymbolTable]) -> List[CompletionItem]:
    """Builds a completion list of every type usable after 'as' / 'into'.

    Includes the built-in scalar/collection types plus every project-defined
    rune, echo, omen, alias, seal and shard-bound generic rune.
    """
    items: List[CompletionItem] = []
    seen: set = set()
    for t_name, t_doc in BASE_TYPES:
        seen.add(t_name)
        items.append(
            CompletionItem(
                label=t_name,
                kind=CompletionItemKind.TypeParameter,
                detail=t_doc,
                insert_text=t_name,
            )
        )

    imported_names = getattr(symbols, "imported_names", None) or set()
    # Import aliases: monomorphization later adds spellings such as
    # `numerus_Pair` (and `numerus_oracle_Pair`) to `generic_runes`, after the
    # checker's imported-name snapshot was taken.  Any registry key prefixed
    # with an import alias is an internal spelling, not something a user types.
    scope_symbols = getattr(getattr(symbols, "global_scope", None), "symbols", {}) or {}
    import_aliases = {
        name for name, sym in scope_symbols.items()
        if getattr(sym, "kind", "") == "import"
    }
    # An imported module's *public* types are usable by their bare name (the
    # checker registers them in the type registries), but its internal
    # `module_Type` spelling is not something a user writes.  Showing the bare
    # public names keeps imported types available without flooding the list:
    # five std imports produced 957 entries, 477 of them internal aliases.
    public_imported: set = set()
    if symbols is not None:
        scope = getattr(symbols, "global_scope", None)
        for import_symbol in getattr(scope, "symbols", {}).values():
            if getattr(import_symbol, "kind", "") != "import":
                continue
            module_scope = getattr(import_symbol, "module_scope", None)
            if module_scope is None:
                continue
            for member_name, member in getattr(module_scope, "symbols", {}).items():
                if member_name.startswith("_"):
                    continue
                if getattr(member, "kind", "") in (
                    "rune", "echo", "omen", "alias", "seal", "concept",
                ):
                    public_imported.add(member_name)

    def _add(name: str, kind: CompletionItemKind, detail: str) -> None:
        if name and name not in seen:
            if name in imported_names and name not in public_imported:
                return
            if any(name.startswith(alias + "_") for alias in import_aliases):
                return
            seen.add(name)
            items.append(
                CompletionItem(label=name, kind=kind, detail=detail, insert_text=name)
            )

    if symbols is not None:
        for r_name in getattr(symbols, "runes", {}):
            _add(r_name, CompletionItemKind.Class, "rune")
        for e_name in getattr(symbols, "echos", {}):
            _add(e_name, CompletionItemKind.Enum, "echo")
        for o_name in getattr(symbols, "omens", {}):
            _add(o_name, CompletionItemKind.Interface, "omen")
        for a_name in getattr(symbols, "aliases", {}):
            _add(a_name, CompletionItemKind.TypeParameter, "alias")
        for s_name in getattr(symbols, "seals", {}):
            _add(s_name, CompletionItemKind.TypeParameter, "seal")
        for g_name in getattr(symbols, "generic_runes", {}):
            _add(g_name, CompletionItemKind.Class, "generic rune")
        for p_name in sorted(public_imported):
            _add(p_name, CompletionItemKind.Class, "imported type")
    return items


def _when_items() -> List[CompletionItem]:
    """Compile-time variables usable as 'when' conditions."""
    items = [
        CompletionItem(
            label="main",
            kind=CompletionItemKind.Variable,
            detail="bool · true when this module is the program entry point",
            documentation="True for the module executed directly (pengu run <file> or -D main); "
                          "always false for imported modules.",
            insert_text="main",
        ),
        CompletionItem(
            label="os",
            kind=CompletionItemKind.Variable,
            detail="str · target OS ('windows', 'linux', 'macos', ...)",
            insert_text="os",
        ),
        CompletionItem(
            label="arch",
            kind=CompletionItemKind.Variable,
            detail="str · target architecture ('x64', 'x86', 'arm64', ...)",
            insert_text="arch",
        ),
        CompletionItem(
            label="compiler",
            kind=CompletionItemKind.Variable,
            detail="str · C compiler ('gcc', 'clang', 'msvc', ...)",
            insert_text="compiler",
        ),
        CompletionItem(
            label="defined",
            kind=CompletionItemKind.Snippet,
            detail="bool · true when a -D NAME macro is set",
            insert_text="defined(${1:NAME})",
            insert_text_format=InsertTextFormat.Snippet,
        ),
        CompletionItem(label="true", kind=CompletionItemKind.Keyword, detail="bool literal", insert_text="true"),
        CompletionItem(label="false", kind=CompletionItemKind.Keyword, detail="bool literal", insert_text="false"),
    ]
    return items


def _module_member_items(scope) -> List[CompletionItem]:
    """Builds completion items for every exported member of a module scope.

    Private members (leading underscore) are skipped, as are the built-in
    scalar type symbols that a module scope carries for convenience.

    Args:
        scope: A module Scope (``module_scope`` of an import symbol or a
            cached module scope from the server-wide module cache).

    Returns:
        Completion items for the module's exported symbols.
    """
    mod_items: List[CompletionItem] = []
    if scope is None:
        return mod_items
    for name, m_sym in getattr(scope, "symbols", {}).items():
        if name.startswith("_"):
            continue
        if getattr(m_sym, "kind", "") == "type" and name in ("int", "i32", "i64", "float", "f32", "f64", "bool", "string", "void", "opaque"):
            continue
        kind = (
            CompletionItemKind.Class if m_sym.kind == "rune"
            else CompletionItemKind.Function if m_sym.kind in ("weave", "function", "declare")
            else CompletionItemKind.Enum if m_sym.kind == "echo"
            else CompletionItemKind.Interface if m_sym.kind == "omen"
            else CompletionItemKind.TypeParameter if m_sym.kind == "alias"
            else CompletionItemKind.Constant if m_sym.kind == "const"
            else CompletionItemKind.Variable
        )
        t_str = f" {m_sym.type}" if getattr(m_sym, "type", None) else ""
        mod_items.append(
            CompletionItem(
                label=name,
                kind=kind,
                detail=f"{m_sym.kind}{t_str}",
                documentation=m_sym.doc or None,
                insert_text=name,
            )
        )
    return mod_items


def get_completions(
    uri: str,
    position: Position,
    symbols: Optional[SymbolTable] = None,
    line_prefix: str = "",
    module_cache: Optional[Dict[str, object]] = None,
    base_dir: Optional[str] = None,
    doc_text: Optional[str] = None,
) -> CompletionList:
    """Generates completion items including keywords, types, and scope symbols.

    Args:
        uri: Document URI.
        position: Cursor position (line, char).
        symbols: Checked SymbolTable if available.
        line_prefix: Text before cursor on current line.
        module_cache: Server-wide cache mapping import aliases to their module
            Scopes. Lets completion show module members even before the current
            document has been validated (or when it only has errors).
        base_dir: Project root used to resolve importable modules; falls back
            to the current working directory.
        doc_text: Full document text (used by multi-line contexts such as
            ``judge`` blocks and ``with target:`` scopes).

    Returns:
        CompletionList for VSCode LSP.
    """
    cursor_line = position.line + 1
    current_path = _current_document_path(uri)

    # 0aa. `judge <rune> over ` / `when <Variant> with ` — the discriminant
    # fields and the rune's fields. Checked before the plain judge context so a
    # clause inside a `judge over` block does not fall through to it.
    jor_items = judge_over_completions(doc_text, position, symbols)
    if jor_items is not None:
        return CompletionList(is_incomplete=False, items=jor_items)

    # 0aa2. `break ` / `continue ` — the labels of the loops that enclose the
    # cursor. A bare `break`/`continue` has no label position and falls through
    # to the ordinary keyword list.
    label_items = loop_label_completions(doc_text, position)
    if label_items is not None:
        return CompletionList(is_incomplete=False, items=label_items)

    # 0ab. Judge context: a `when` inside a judge block must not fall
    # through to the compile-time `when` (main/os/arch/...) suggestions.
    judge_items = _judge_context_items(doc_text, position, symbols)
    if judge_items is not None:
        return CompletionList(is_incomplete=False, items=judge_items)

    # 0a. Compile-time 'when' context: suggest main / os / arch / compiler / defined.
    if re.search(r"\bwhen\s*$", line_prefix):
        return CompletionList(is_incomplete=False, items=_when_items())

    # 0b. Type annotation contexts: after 'as' or 'into' suggest every usable type.
    if re.search(r"(?:^|\s)(?:as|into)\s+$", line_prefix):
        return CompletionList(is_incomplete=False, items=_type_items(symbols))

    # 0c. Import context: `import ` / `import std.` / partial module specs.
    import_items = _import_completion_items(base_dir, line_prefix, position)
    if import_items is not None:
        return CompletionList(is_incomplete=False, items=import_items)

    # 0d. Multi-line contextual completions (set. in with blocks, rune init).
    set_items = _with_block_field_items(doc_text, position, symbols)
    if set_items is not None:
        return CompletionList(is_incomplete=False, items=set_items)

    with_items = _rune_with_field_items(symbols, line_prefix)
    if with_items is not None:
        return CompletionList(is_incomplete=False, items=with_items)

    # 0. Dot / Arrow Completion (Fields of Rune/Echo/Omen or Module members)
    if line_prefix and (symbols is not None or module_cache):
        dot_match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)(?:\.|->)$", line_prefix)
        if dot_match:
            full_path = dot_match.group(1)
            parts = full_path.split(".")

            curr_sym = None
            if symbols is not None:
                for i, part in enumerate(parts):
                    if i == 0:
                        curr_sym = symbols.lookup_at(part, cursor_line) if hasattr(symbols, "lookup_at") else symbols.lookup(part)
                        if not curr_sym and part == "self":
                            curr_sym = symbols.lookup("self")
                    else:
                        if curr_sym and getattr(curr_sym, "module_scope", None):
                            curr_sym = curr_sym.module_scope.symbols.get(part)
                        elif curr_sym:
                            c_type = curr_sym.type
                            while isinstance(c_type, RefType):
                                c_type = c_type.target
                            if isinstance(c_type, (RuneType, EchoType)) and part in c_type.fields:
                                field_type = c_type.fields[part]
                                curr_sym = Symbol(name=part, type=field_type, kind="var")
                            else:
                                curr_sym = None

            sym = curr_sym

            if sym:
                # Module members: only the import symbol's own module scope is
                # authoritative. When the symbol exists but carries no scope
                # (e.g. the module could not be loaded during a partial check)
                # we do NOT fall back to the server cache: a stale / foreign
                # scope cached under this alias would leak the members of some
                # other module (e.g. every imported module showing spark's).
                mod_scope = getattr(sym, "module_scope", None)
                if mod_scope is not None and getattr(mod_scope, "symbols", None):
                    return CompletionList(is_incomplete=False, items=_module_member_items(mod_scope))

                actual_type = sym.type
                while isinstance(actual_type, RefType):
                    actual_type = actual_type.target

                field_items: List[CompletionItem] = []

                # RuneType: suggest fields and attached methods
                if isinstance(actual_type, RuneType):
                    for f_name, f_type in actual_type.fields.items():
                        field_items.append(
                            CompletionItem(
                                label=f_name,
                                kind=CompletionItemKind.Field,
                                detail=str(f_type),
                                insert_text=f_name,
                            )
                        )
                    by_label = {item.label: item for item in field_items}
                    for m_name, m_type in getattr(actual_type, "methods", {}).items():
                        by_label.setdefault(
                            m_name,
                            CompletionItem(
                                label=m_name,
                                kind=CompletionItemKind.Method,
                                detail=f"method {m_type}",
                                insert_text=m_name,
                            ),
                        )
                    # A rune declared in another module is a *different*
                    # RuneType instance than the one the checker attached its
                    # `enchanting` block to, so `actual_type.methods` is empty
                    # for it. `symbols.methods` is keyed by name and does hold
                    # them.
                    for item in _method_items_for_type(symbols, actual_type):
                        by_label.setdefault(item.label, item)
                    return CompletionList(is_incomplete=False, items=list(by_label.values()))

                # EchoType: suggest fields
                elif isinstance(actual_type, EchoType):
                    for f_name, f_type in actual_type.fields.items():
                        field_items.append(
                            CompletionItem(
                                label=f_name,
                                kind=CompletionItemKind.Field,
                                detail=str(f_type),
                                insert_text=f_name,
                            )
                        )
                    return CompletionList(is_incomplete=False, items=field_items)

                # OmenType: methods from an `enchanting` block. A variant is a
                # *constructor* of an algebraic omen, not a member of an
                # instance, so `root.` on a `JsonValue` used to offer `Int`,
                # `Str`, ... and no methods at all. Variants remain useful on a
                # plain (non-algebraic) enum value, where they are values.
                elif isinstance(actual_type, OmenType):
                    by_label = {item.label: item for item in _method_items_for_type(symbols, actual_type)}
                    if not actual_type.is_algebraic:
                        for v_name, v_fields in actual_type.variants.items():
                            v_detail = f"variant with {', '.join(f'{fn} as {ft}' for fn, ft in v_fields.items())}" if v_fields else "variant"
                            by_label.setdefault(
                                v_name,
                                CompletionItem(
                                    label=v_name,
                                    kind=CompletionItemKind.EnumMember,
                                    detail=v_detail,
                                    insert_text=v_name,
                                ),
                            )
                    return CompletionList(is_incomplete=False, items=list(by_label.values()))

                # Everything else — primitives, containers, aliases, and runes
                # whose methods come from an imported `enchanting` block. Without
                # this, `x.clamp` on a `float` completed to nothing at all: only
                # the RuneType branch ever looked at `symbols.methods`.
                else:
                    field_items.extend(_method_items_for_type(symbols, actual_type))
                    return CompletionList(is_incomplete=False, items=field_items)

            # Cache fallback: only reached when `sym` is None, i.e. the base
            # name is not defined anywhere in the current document (for example
            # because it is an import alias from a document that has not been
            # validated yet). A name that IS defined never consults the cache,
            # so a stale cache entry can never leak another module's members.
            if sym is None and module_cache is not None:
                mod_scope = module_cache.get(parts[0])
                if mod_scope is not None:
                    # One level: `alias.` -> members of the cached module scope.
                    if len(parts) == 1:
                        return CompletionList(is_incomplete=False, items=_module_member_items(mod_scope))
                    # Deeper: walk symbols that are themselves sub-modules.
                    ok = True
                    cur_scope = mod_scope
                    for part in parts[1:]:
                        member = None
                        if hasattr(cur_scope, "symbols"):
                            member = cur_scope.symbols.get(part)
                        nxt = getattr(member, "module_scope", None) if member is not None else None
                        if nxt is None:
                            ok = False
                            break
                        cur_scope = nxt
                    if ok and hasattr(cur_scope, "symbols"):
                        return CompletionList(is_incomplete=False, items=_module_member_items(cur_scope))

            # Check if full_path is a type name directly (e.g. Rune.field or Omen.Variant)
            if hasattr(symbols, "runes") and full_path in symbols.runes:
                r_type = symbols.runes[full_path]
                field_items = [
                    CompletionItem(label=fn, kind=CompletionItemKind.Field, detail=str(ft), insert_text=fn)
                    for fn, ft in r_type.fields.items()
                ]
                return CompletionList(is_incomplete=False, items=field_items)

            if hasattr(symbols, "omens") and full_path in symbols.omens:
                o_type = symbols.omens[full_path]
                variant_items = [
                    CompletionItem(label=vn, kind=CompletionItemKind.EnumMember, detail="variant", insert_text=vn)
                    for vn in o_type.variants.keys()
                ]
                return CompletionList(is_incomplete=False, items=variant_items)

    # 1. Calling Context Completion (e.g. `calling ` or `calling`)
    if symbols and (line_prefix.strip().endswith("calling") or re.search(r"\bcalling\s+$", line_prefix)):
        call_items: List[CompletionItem] = []
        added_labels = set()

        # 1a. Callable local variables in active scopes
        if hasattr(symbols, "all_scopes"):
            for scope in symbols.all_scopes:
                if scope.start_line <= cursor_line <= scope.end_line:
                    for sym in scope.symbols.values():
                        if sym.name and sym.name not in added_labels:
                            if isinstance(getattr(sym, "type", None), FnType):
                                call_items.append(
                                    CompletionItem(
                                        label=sym.name,
                                        kind=CompletionItemKind.Function,
                                        detail=f"function {sym.type}",
                                        insert_text=sym.name,
                                    )
                                )
                                added_labels.add(sym.name)

        # 1b. Global functions, declarations, and imported modules
        table_dict = getattr(symbols, "table", None)
        if table_dict is None and hasattr(symbols, "global_scope"):
            table_dict = symbols.global_scope.symbols

        if table_dict:
            for name, sym in table_dict.items():
                if name not in added_labels:
                    if not _belongs_to_document(sym, current_path):
                        continue
                    if sym.kind in ("weave", "function", "declare"):
                        t_str = f" {sym.type}" if getattr(sym, "type", None) else ""
                        call_items.append(
                            CompletionItem(
                                label=name,
                                kind=CompletionItemKind.Function,
                                detail=f"{sym.kind}{t_str}",
                                documentation=sym.doc or None,
                                insert_text=name,
                            )
                        )
                        added_labels.add(name)
                    elif sym.kind == "import" or getattr(sym, "module_scope", None):
                        call_items.append(
                            CompletionItem(
                                label=name,
                                kind=CompletionItemKind.Module,
                                detail=f"module {name}",
                                documentation=sym.doc or None,
                                insert_text=name,
                            )
                        )
                        added_labels.add(name)

        return CompletionList(is_incomplete=False, items=call_items)

    items: List[CompletionItem] = []

    # 2. Base Keywords and Snippets
    for kw, template, detail, kind in BASE_KEYWORDS:
        items.append(
            CompletionItem(
                label=kw,
                kind=kind,
                detail=detail,
                insert_text=template,
                insert_text_format=InsertTextFormat.Snippet if "$" in template else InsertTextFormat.PlainText,
            )
        )

    # 3. Base Types
    for t_name, t_doc in BASE_TYPES:
        items.append(
            CompletionItem(
                label=t_name,
                kind=CompletionItemKind.TypeParameter,
                detail=t_doc,
                insert_text=t_name,
            )
        )

    # 4. Dynamic Global Symbols from SymbolTable
    if symbols:
        table_dict = getattr(symbols, "table", None)
        if table_dict is None and hasattr(symbols, "global_scope"):
            table_dict = symbols.global_scope.symbols

        if table_dict:
            for name, sym in table_dict.items():
                if not _belongs_to_document(sym, current_path):
                    continue
                if getattr(sym, "kind", "") in ("rune", "echo", "omen", "weave", "function", "declare", "alias", "var", "let", "const", "import"):
                    kind = (
                        CompletionItemKind.Class if sym.kind == "rune"
                        else CompletionItemKind.Function if sym.kind in ("weave", "function", "declare")
                        else CompletionItemKind.Enum if sym.kind == "echo"
                        else CompletionItemKind.Interface if sym.kind == "omen"
                        else CompletionItemKind.TypeParameter if sym.kind == "alias"
                        else CompletionItemKind.Constant if sym.kind == "const"
                        else CompletionItemKind.Module if sym.kind == "import"
                        else CompletionItemKind.Variable
                    )
                    t_str = f" {sym.type}" if getattr(sym, "type", None) else ""
                    items.append(
                        CompletionItem(
                            label=name,
                            kind=kind,
                            detail=f"{sym.kind}{t_str}",
                            documentation=sym.doc or None,
                            insert_text=name,
                        )
                    )

        # One label set instead of `any(item.label == ...)` per candidate:
        # with imports the list holds thousands of items and the old scan made
        # completion quadratic in its own output.
        seen_labels = {item.label for item in items}
        imported_names = getattr(symbols, "imported_names", None) or set()

        # 5. Dynamic Local Variables from Active Scopes around cursor_line
        if hasattr(symbols, "all_scopes"):
            for scope in symbols.all_scopes:
                if scope.start_line <= cursor_line <= scope.end_line:
                    for sym in scope.symbols.values():
                        if getattr(sym, "kind", "") in ("var", "let", "param") and sym.name:
                            if sym.name not in seen_labels:
                                seen_labels.add(sym.name)
                                t_str = f" {sym.type}" if getattr(sym, "type", None) else ""
                                items.append(
                                    CompletionItem(
                                        label=sym.name,
                                        kind=CompletionItemKind.Variable,
                                        detail=f"{sym.kind}{t_str}",
                                        insert_text=sym.name,
                                    )
                                )

        # Collect custom runes/types registered in symbols. Names an import
        # contributed (`loom_Vec2`, `Vec2` from a module) are excluded here:
        # their qualified spelling is what the user writes, and dot completion
        # already offers them after `module.`.
        for r_name in getattr(symbols, "runes", {}):
            if r_name not in seen_labels and r_name not in imported_names:
                seen_labels.add(r_name)
                items.append(
                    CompletionItem(
                        label=r_name,
                        kind=CompletionItemKind.Class,
                        detail=f"rune {r_name}",
                        insert_text=r_name,
                    )
                )

        for e_name in getattr(symbols, "echos", {}):
            if e_name not in seen_labels and e_name not in imported_names:
                seen_labels.add(e_name)
                items.append(
                    CompletionItem(
                        label=e_name,
                        kind=CompletionItemKind.Enum,
                        detail=f"echo {e_name}",
                        insert_text=e_name,
                    )
                )

        for o_name in getattr(symbols, "omens", {}):
            if o_name not in seen_labels and o_name not in imported_names:
                seen_labels.add(o_name)
                items.append(
                    CompletionItem(
                        label=o_name,
                        kind=CompletionItemKind.Interface,
                        detail=f"omen {o_name}",
                        insert_text=o_name,
                    )
                )

    return CompletionList(is_incomplete=False, items=items)

