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

