"""PenguScript LSP Code Actions.

Currently provides the "Add missing import" quick action: when the cursor sits
on an identifier that is not defined in the current document, we scan the
stdlib (`std/`) and the project sources for a module exporting that symbol and
suggest inserting the corresponding `import` statement.
"""

import os
import re
import threading
from typing import Dict, List, Optional, Tuple

from lsprotocol.types import (
    CodeAction,
    CodeActionKind,
    Position,
    Range,
    TextEdit,
    WorkspaceEdit,
)

STD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "std")

# Thread-safe cache of "exported symbol name" -> ("std.spark" | relative import)
_INDEX_LOCK = threading.Lock()
_SYMBOL_INDEX: Dict[str, str] = {}
_INDEX_PATHS: Tuple[str, ...] = ()


def _import_statement_spec(file_path: str, base_dir: str) -> Optional[str]:
    """Computes the 'import X.Y' spec for a source file relative to a base dir.

    Files under <base>/std become std.<stem>; other files become a dotted path
    relative to base_dir (or a bare stem when not under base_dir).
    """
    fp = os.path.abspath(file_path)
    base = os.path.abspath(base_dir) if base_dir else os.getcwd()
    if fp.startswith(base):
        rel = os.path.relpath(fp, base)
        parts = [p for p in re.split(r"[\\/]", rel) if p]
        parts[-1] = os.path.splitext(parts[-1])[0]
        if parts and parts[0] == "std":
            return ".".join(parts)
        return ".".join(parts)
    return os.path.splitext(os.path.basename(fp))[0]


def _scan_pengu_file(file_path: str, base_dir: str, index: Dict[str, str]) -> None:
    """Indexes the top-level symbol names exported by one .pengu file."""
    spec = _import_statement_spec(file_path, base_dir)
    if not spec:
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return
    decl_re = re.compile(
        r"^\s*(?:public\s+)?(?:weave|declare|const|rune|echo|omen|alias|seal|concept)\s+([A-Za-z_][A-Za-z0-9_]*)",
        re.MULTILINE,
    )
    for m in decl_re.finditer(source):
        name = m.group(1)
        if name == "main":
            continue
        index.setdefault(name, spec)


def refresh_index(std_dir: Optional[str] = None, extra_roots: Optional[List[str]] = None) -> Dict[str, str]:
    """Builds (once, then cached) a map symbol-name -> 'import spec'.

    Scans the stdlib directory plus any project roots (searched recursively).
    """
    global _SYMBOL_INDEX, _INDEX_PATHS
    roots: List[str] = []
    std_root = std_dir or STD_DIR
    if os.path.isdir(std_root):
        roots.append(std_root)
    for r in extra_roots or []:
        if r and os.path.isdir(r):
            roots.append(r)
    key = tuple(roots)
    with _INDEX_LOCK:
        if key == _INDEX_PATHS and _SYMBOL_INDEX:
            return dict(_SYMBOL_INDEX)

    index: Dict[str, str] = {}
    for root in roots:
        if root == std_root and os.path.dirname(std_root):
            base = os.path.dirname(std_root)  # std/.. => specs become std.<stem>
        else:
            base = root
        for dirpath, _, files in os.walk(root):
            for fname in files:
                if fname.endswith(".pengu"):
                    _scan_pengu_file(os.path.join(dirpath, fname), base, index)
    with _INDEX_LOCK:
        _SYMBOL_INDEX = index
        _INDEX_PATHS = key
    return dict(index)


def _existing_imports(source: str) -> List[str]:
    """Returns the import specs already present in the document."""
    return re.findall(r"^\s*import\s+([A-Za-z_][A-Za-z0-9_.]*)\s*$", source, re.MULTILINE)


def add_missing_import_action(
    uri: str,
    word: str,
    source: str,
    symbols,
    base_dir: Optional[str] = None,
    project_roots: Optional[List[str]] = None,
) -> Optional[CodeAction]:
    """Builds an 'Add missing import' code action when word is unknown here.

    Args:
        uri: Document URI (unused for indexing but kept for parity).
        word: Identifier under the cursor.
        source: Current document source text.
        symbols: SymbolTable of the current document (may be None).
        base_dir: Project root used to resolve relative imports.
        project_roots: Extra directories to scan for user modules.

    Returns:
        A CodeAction inserting the import, or None when no module exports word.
    """
    if not word or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", word):
        return None

    # Already known in this document?
    if symbols is not None:
        if getattr(symbols, "lookup", None) is not None and symbols.lookup(word) is not None:
            return None

    root_dir = base_dir or os.getcwd()
    roots = [root_dir]
    if project_roots:
        roots.extend(project_roots)
    index = refresh_index(extra_roots=roots)

    spec = index.get(word)
    if not spec:
        return None

    existing = set(_existing_imports(source))
    if spec in existing:
        return None

    lines = source.splitlines()
    insert_line = 0
    for i, line in enumerate(lines):
        if line.lstrip().startswith("import "):
            insert_line = i + 1
    # Put the insertion point at the start of the line that follows imports.
    pos = Position(line=insert_line, character=0)

    edit = TextEdit(
        range=Range(start=pos, end=pos),
        new_text=f"import {spec}\n",
    )
    action = CodeAction(
        title=f"Add missing import: import {spec}",
        kind=CodeActionKind.QuickFix,
        edit=WorkspaceEdit(changes={uri: [edit]}),
    )
    return action


def remove_unused_variable_action(
    uri: str,
    word: str,
    source: str,
    symbols,
) -> Optional[CodeAction]:
    """Builds a 'Remove unused variable' code action when safe.

    A local variable is considered unused when its name occurs exactly once in
    the document (only the declaration). The action deletes the whole line.

    Args:
        uri: Document URI.
        word: Variable name under the cursor.
        source: Current document source text.
        symbols: SymbolTable of the document (may be None).

    Returns:
        A CodeAction deleting the unused declaration line, or None.
    """
    if not word or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", word):
        return None
    if symbols is not None:
        sym = None
        try:
            sym = symbols.lookup(word)
        except Exception:
            sym = None
        if sym is not None and not getattr(sym, "is_mutable", True):
            # Immutable constants/params may be flagged elsewhere; only mutable
            # locals declared with 'var' are candidates here.
            return None
    occurrences = re.findall(rf"\b{re.escape(word)}\b", source)
    if len(occurrences) != 1:
        return None
    lines = source.splitlines()
    for i, line in enumerate(lines):
        if re.search(rf"^\s*var\s+{re.escape(word)}\b", line):
            end_char = len(lines[i]) if i < len(lines) else 0
            # Include the trailing newline when there is one.
            edit = TextEdit(
                range=Range(
                    start=Position(line=i, character=0),
                    end=Position(line=i, character=end_char),
                ),
                new_text="",
            )
            action = CodeAction(
                title=f"Remove unused variable '{word}'",
                kind=CodeActionKind.QuickFix,
                edit=WorkspaceEdit(changes={uri: [edit]}),
            )
            return action
    return None


def _import_lines(source: str) -> List[Tuple[int, str, str, Optional[str]]]:
    """Returns (line_index, raw_line, spec, alias) for every import statement.

    Args:
        source: Document source text.

    Returns:
        Tuples ordered by line index.
    """
    out: List[Tuple[int, str, str, Optional[str]]] = []
    for i, line in enumerate(source.splitlines()):
        m = re.match(r"^\s*import\s+([A-Za-z_][A-Za-z0-9_.]*)"
                     r"(?:\s+as\s+([A-Za-z_][A-Za-z0-9_]*))?\s*$", line)
        if m:
            out.append((i, line, m.group(1), m.group(2)))
    return out


def _default_return_expr(ret_name: str) -> Optional[str]:
    """A type-appropriate default return expression for a skeleton method."""
    if ret_name in ("", "void"):
        return None  # bare `return`
    if ret_name in ("bool",):
        return "false"
    if ret_name == "string":
        return '""'
    if ret_name in (
        "float", "double", "f32", "f64",
    ):
        return "0.0"
    if ret_name in (
        "int", "i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64",
        "usize", "isize", "byte", "short", "long", "int32_t", "int64_t",
        "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    ):
        return "0"
    if ret_name.startswith("maybe "):
        return "maybe none"
    return "null"


def implement_concept_methods_action(
    uri: str,
    source: str,
    position,
    symbols,
) -> Optional[CodeAction]:
    """Builds an 'Implement missing concept methods' code action.

    When the cursor sits inside a ``bind Target with Concept:`` block, every
    concept method that is not yet implemented there is appended as a weave
    skeleton with the correct parameter list, return type and a default body
    (the block must be reachable above the cursor).

    Args:
        uri: Document URI.
        source: Current document source text.
        position: Cursor position (usually the code-action range start).
        symbols: SymbolTable of the current document (may be None).

    Returns:
        A CodeAction inserting the missing method skeletons, or None.
    """
    if position is None or symbols is None:
        return None
    cursor_line = getattr(position, "line", -1)
    lines = source.splitlines()

    header_idx = None
    target = None
    concept_name = None
    block_indent = 0
    for i in range(cursor_line, -1, -1):
        if i >= len(lines):
            continue
        m = re.match(r"^(\s*)bind\s+([A-Za-z_][A-Za-z0-9_]*)\s+with\s+"
                     r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*$", lines[i])
        if m:
            header_idx = i
            block_indent = len(m.group(1))
            target = m.group(2)
            concept_name = m.group(3)
            break
    if header_idx is None:
        return None

    # Methods already implemented inside this bind block.
    implemented = set()
    j = header_idx + 1
    while j < len(lines):
        s = lines[j]
        indent = len(s) - len(s.lstrip())
        stripped = s.strip()
        if not stripped:
            j += 1
            continue
        if indent <= block_indent:
            break
        m = re.match(r"^\s*weave\s+([A-Za-z_][A-Za-z0-9_]*)\b", s)
        if m:
            implemented.add(m.group(1))
        j += 1

    concept = None
    try:
        if hasattr(symbols, "lookup_concept"):
            concept = symbols.lookup_concept(concept_name)
    except Exception:
        concept = None
    if concept is None:
        concepts = getattr(symbols, "concepts", {})
        concept = concepts.get(concept_name)
    if concept is None or not getattr(concept, "methods", None):
        return None

    missing = sorted(
        m_name for m_name in concept.methods
        if m_name not in implemented
    )
    if not missing:
        return None

    decl_indent = " " * (block_indent + 4)
    body_indent = " " * (block_indent + 8)
    skeleton: List[str] = []
    for m_name in missing:
        m_fn = concept.methods[m_name]
        params = getattr(m_fn, "params", []) or []
        if params:
            parts = []
            for p_i, p in enumerate(params):
                p_name = p[0] if p and p[0] else f"arg{p_i + 1}"
                parts.append(f"{p_name} as {p[1]}")
            sig = f"weave {m_name} with {', '.join(parts)}"
        else:
            sig = f"weave {m_name}"
        ret_name = str(getattr(m_fn, "return_type", ""))
        if ret_name and ret_name != "void":
            sig += f" into {ret_name}:"
        else:
            sig += ":"
        skeleton.append(f"{decl_indent}{sig}")
        default = _default_return_expr(ret_name)
        if default is None:
            skeleton.append(f"{body_indent}return")
        elif ret_name.startswith("maybe "):
            skeleton.append(f"{body_indent}return maybe none")
        else:
            skeleton.append(f"{body_indent}return {default}")

    new_text = "\n" + "\n".join(skeleton) + "\n"
    insert_line = header_idx + 1
    edit = TextEdit(
        range=Range(
            start=Position(line=insert_line, character=0),
            end=Position(line=insert_line, character=0),
        ),
        new_text=new_text,
    )
    action = CodeAction(
        title=f"Implement {len(missing)} missing method(s) of concept "
              f"'{concept_name}' on '{target}'",
        kind=CodeActionKind.QuickFix,
        edit=WorkspaceEdit(changes={uri: [edit]}),
    )
    return action


def organize_imports_action(uri: str, source: str) -> Optional[CodeAction]:
    """Builds an 'Organize Imports' code action for the document.

    Removes import statements whose module is never referenced outside the
    import itself, then sorts the remaining imports alphabetically by spec.
    Imports must form a contiguous block at the top of the document; the block
    is replaced in one edit.

    Args:
        uri: Document URI.
        source: Current document source text.

    Returns:
        A CodeAction, or None when there is nothing to organize (no imports,
        or the block is already tidy).
    """
    imports = _import_lines(source)
    if not imports:
        return None

    first_idx = imports[0][0]
    last_idx = imports[-1][0]
    # The import block must be contiguous (only import lines and blanks may
    # sit between the first and last import).
    for i in range(first_idx, last_idx + 1):
        line = source.splitlines()[i]
        if line.strip() and not line.lstrip().startswith("import "):
            return None

    # A reference token for each import: the alias when present, otherwise the
    # last segment of the module spec (e.g. 'spark' for std.spark).
    import_lines_set = {idx for idx, _, _, _ in imports}
    refs: List[Tuple[str, str, int, str]] = []
    for idx, raw, spec, alias in imports:
        token = alias or spec.split(".")[-1]
        refs.append((spec, raw, idx, token))

    kept: List[Tuple[str, str]] = []  # (spec, raw_line)
    changed = False
    for spec, raw, idx, token in refs:
        used = False
        for j, line in enumerate(source.splitlines()):
            if j == idx or j in import_lines_set:
                continue
            if re.search(rf"\b{re.escape(token)}\b", line):
                used = True
                break
        if used:
            kept.append((spec, raw))
        else:
            changed = True  # an unused import will be dropped

    kept.sort(key=lambda pair: pair[0])
    sorted_raw = [raw for _, raw in kept]
    # Detect reordering vs. the original import order (plus any removals).
    original_order = [raw for _, raw, _, _ in imports]
    if sorted_raw == original_order and not changed:
        return None

    lines = source.splitlines()
    end_char = len(lines[last_idx]) if last_idx < len(lines) else 0
    new_text = "\n".join(sorted_raw)
    if new_text:
        new_text += "\n"
    edit = TextEdit(
        range=Range(
            start=Position(line=first_idx, character=0),
            end=Position(line=last_idx, character=end_char),
        ),
        new_text=new_text,
    )
    action = CodeAction(
        title="Organize imports",
        kind=CodeActionKind.SourceOrganizeImports,
        edit=WorkspaceEdit(changes={uri: [edit]}),
    )
    return action


# ---------------------------------------------------------------------------
# Project-wide symbol locations (Go to Implementation / Find References)
# ---------------------------------------------------------------------------

_DECL_CACHE: Dict[Tuple[str, ...], Dict[str, List[Tuple[str, int, int]]]] = {}

_DECL_LINE = re.compile(
    r"^\s*(?:weave|declare|const|rune|echo|omen|alias|seal|concept)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)\b"
)


def declaration_locations(
    extra_roots: Optional[List[str]] = None,
    std_dir: Optional[str] = None,
) -> Dict[str, List[Tuple[str, int, int]]]:
    """Returns ``name -> [(file_path, line, column)]`` per top-level symbol.

    Indexes declarations (and enchanting/bind method definitions, which are
    indented ``weave`` lines) across the standard library and the project
    roots. ``.d.pengu`` binding bodies are skipped (they contain no
    PenguScript implementations). Results are cached per set of roots.

    Args:
        extra_roots: Project directories to scan (in addition to stdlib).
        std_dir: Standard library directory (defaults to the repo std/).

    Returns:
        Map of symbol name to a list of (file_path, 0-based line, column)
        locations.
    """
    global _DECL_CACHE
    std_root = os.path.abspath(std_dir or STD_DIR)
    roots = [std_root]
    for r in extra_roots or []:
        if r:
            roots.append(os.path.abspath(r))
    key = tuple(roots)
    cached = _DECL_CACHE.get(key)
    if cached is not None:
        return cached

    locations: Dict[str, List[Tuple[str, int, int]]] = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d for d in dirnames if not d.startswith("_") and not d.startswith(".")
            ]
            for fname in filenames:
                if fname.endswith(".d.pengu"):
                    continue
                if not fname.endswith(".pengu"):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        for i, line in enumerate(f):
                            m = _DECL_LINE.match(line)
                            if m:
                                locations.setdefault(m.group(1), []).append(
                                    (fpath, i, m.start(1))
                                )
                except OSError:
                    continue
    _DECL_CACHE[key] = locations
    return locations


def word_occurrences_in_roots(
    word: str, extra_roots: Optional[List[str]] = None,
    std_dir: Optional[str] = None,
) -> List[Tuple[str, int, int]]:
    """Finds every occurrence of ``word`` in stdlib + project ``.pengu`` files.

    ``.d.pengu`` binding bodies are skipped (their text is C-API surface, not
    PenguScript source). Occurrences are returned as
    ``(file_path, line, column)`` tuples sorted by file then line.

    Args:
        word: Identifier to search for.
        extra_roots: Project directories to scan (in addition to stdlib).
        std_dir: Standard library directory.

    Returns:
        Occurrence locations.
    """
    if not word or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", word):
        return []
    std_root = os.path.abspath(std_dir or STD_DIR)
    roots = [std_root] + [os.path.abspath(r) for r in (extra_roots or [])]
    pattern = re.compile(rf"\b{re.escape(word)}\b")
    found: List[Tuple[str, int, int]] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d for d in dirnames if not d.startswith("_") and not d.startswith(".")
            ]
            for fname in filenames:
                if fname.endswith(".d.pengu"):
                    continue
                if not fname.endswith(".pengu"):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        for i, line in enumerate(f):
                            for m in pattern.finditer(line):
                                found.append((fpath, i, m.start()))
                except OSError:
                    continue
    found.sort(key=lambda t: (t[0], t[1], t[2]))
    return found

