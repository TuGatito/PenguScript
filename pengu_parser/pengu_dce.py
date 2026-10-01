"""Dead-code elimination for standard-library modules.

A script that imports ``std.spark`` just for ``println`` used to pull in *every*
weave of that module, the whole transitive ``std`` closure included.  The
generated ``bundle.c`` is then several times larger than needed, which slows the
C compiler and the reader.

The pass is intentionally *conservative* and name based:

* Every weave declared in a **non-std** module is a root and is always emitted
  (public API of the user's project, bindings, static libraries…).
* A std/lib weave is kept when its name (or its C name) appears anywhere in the
  roots' bodies, transitively.
* References are collected as raw identifiers from the body AST, so a weave that
  is only mentioned indirectly (a callback passed by name, an enchanting method
  reached through a variable) survives as well.
* Only *weave bodies and prototypes* are pruned.  Runes, omens, typedefs and
  constants are left alone: they are cheap and pruning them risks changing struct
  layouts or enum values.

Everything is best effort: with ``dce=False`` (``--no-dce``) the code generator
behaves exactly as before, which makes A/B comparisons and bug reports easy.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:  # pragma: no cover - lark is always available in practice
    from lark import Token, Tree
except Exception:  # pragma: no cover
    Token = Tree = ()  # type: ignore


#: Repository root (``<repo>/pengu_parser/pengu_dce.py`` -> ``<repo>``); the
#: bundled ``std/`` modules live directly under it.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _norm(path: str) -> str:
    return os.path.normpath(os.path.abspath(path)).replace("\\", "/")


def is_prunable_module(filepath: str, base_dir: Optional[str] = None) -> bool:
    """True for modules whose symbols may be dropped (``std/`` and ``lib/`` only).

    A module is prunable when it lives in `std/` or `lib/` directly under one
    of the known roots (the repository root or the project's ``base_dir``):

    * ``<repo>/std/spark.pengu``          -> prunable
    * ``<base_dir>/lib/vendor.pengu``     -> prunable
    * ``<base_dir>/src/main.pengu``       -> NOT prunable
    * ``/home/me/lib/project/main.pengu`` -> NOT prunable

    The last case is why the check is anchored to a root instead of scanning for
    a ``lib`` *component* anywhere in the path: a user project that happens to
    live in a directory called ``lib`` must keep every one of its weaves.

    ``.d.pengu`` binding files are never prunable: their C declarations and
    ``enchanting`` glue are emitted as a unit.
    """
    if not filepath:
        return False
    path = _norm(filepath)
    if path.endswith(".d.pengu"):
        return False
    roots = []
    if base_dir:
        roots.append(_norm(base_dir))
    roots.append(_norm(_REPO_ROOT))
    for root in roots:
        try:
            rel = os.path.relpath(path, root).replace("\\", "/")
        except ValueError:  # different drive on Windows
            continue
        if rel.startswith(".."):
            continue
        first = rel.split("/", 1)[0]
        if first in ("std", "lib"):
            return True
    return False


_IDENT_RE = None


def _identifiers_in_text(text: str) -> Set[str]:
    """Identifier-like words of an interpolated expression ('{calling f with x}')."""
    global _IDENT_RE
    if _IDENT_RE is None:
        import re
        _IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    return set(_IDENT_RE.findall(text or ""))


def collect_references(stmts: Iterable[Any]) -> Set[str]:
    """Every identifier mentioned in a statement list (conservative).

    Interpolated strings are re-parsed later by the compiler, so their
    expressions are not part of the AST: the literal's text is scanned for
    '{…}' groups and the identifiers inside them are collected as well
    (``"{calling cb64_char with v}"`` must keep ``cb64_char`` alive).
    """
    refs: Set[str] = set()
    for stmt in stmts or []:
        if not isinstance(stmt, Tree):
            continue
        try:
            for tok in stmt.scan_values(lambda v: isinstance(v, Token) and v.type == "NAME"):
                refs.add(str(tok))
        except Exception:
            pass
        try:
            for lit in stmt.iter_subtrees():
                if not (isinstance(lit, Tree) and lit.data in ("string_lit", "interpolated_string")):
                    continue
                raw = str(lit.children[0]) if lit.children else ""
                if "{" not in raw:
                    continue
                try:
                    from .pengu_parser import extract_string_parts
                    _raw, _triple, parts = extract_string_parts(raw)
                except Exception:
                    refs |= _identifiers_in_text(raw)
                    continue
                for part in parts:
                    if getattr(part, "is_expr", False):
                        refs |= _identifiers_in_text(getattr(part, "text", "") or str(part))
        except Exception:
            continue
    return refs


def _module_stem(filepath: str) -> str:
    """Module name of a weave: ``std/spark.pengu`` -> ``spark``."""
    stem = os.path.basename(filepath or "").replace("\\", "/")
    for suffix in (".d.pengu", ".pengu"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def _is_referenced(weave: Dict[str, Any], alive: Set[str]) -> bool:
    """True when any live name refers to this weave.

    Inside a module a weave is called by its *short* name (``calling println``)
    while the collected weave may carry the module-qualified one
    (``spark_println``), so the module prefix is stripped as one extra spelling.

    The matching is deliberately *not* "any suffix": a weave called
    ``unused_vendor`` inside ``lib/vendor/pengu/vendor.pengu`` would otherwise be
    kept by its own last segment (``vendor``), which appears in every call site
    that merely mentions the module alias.  Only the module's own prefix is
    stripped, plus multi-token suffixes (``cipher_cb64_char`` -> ``cb64_char``)
    for modules whose insignia differs from their file name.
    """
    names = [n for n in (str(weave.get("name", "")), str(weave.get("c_name", ""))) if n]
    if any(name in alive for name in names):
        return True

    module = _module_stem(str(weave.get("filepath", "")))
    spellings: Set[str] = set()
    for name in names:
        if module and name.startswith(module + "_"):
            spellings.add(name[len(module) + 1:])
        if "_" in name:
            parts = name.split("_")
            for i in range(1, len(parts) - 1):  # keep at least two tokens
                spellings.add("_".join(parts[i:]))
    spellings.discard("")
    return bool(spellings & alive)


def prune_weaves(weaves: Sequence[Dict[str, Any]],
                 extra_refs: Iterable[str] = (),
                 base_dir: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Splits the collected weaves into (kept, dropped).

    ``weaves`` items are the dictionaries built by the code generator; they must
    expose ``name``, ``c_name``, ``filepath`` and (optionally) ``refs``.

    ``extra_refs`` are additional root names (the bodies of ``test`` blocks, a
    plugin's entry points…).  ``base_dir`` is the project root, used to decide
    whether a weave belongs to a prunable ``lib/`` directory of the project.
    """
    kept: List[Dict[str, Any]] = []
    std_weaves: List[Dict[str, Any]] = []
    alive: Set[str] = set(extra_refs or ())

    for weave in weaves:
        # Generic templates and their monomorphized instances are never pruned:
        # the instances are created *during* body generation (after this pass)
        # and their substitution must stay exactly as the call sites built it.
        if weave.get("subst_map") or weave.get("is_generic"):
            kept.append(weave)
            alive.add(str(weave.get("name", "")))
            alive.add(str(weave.get("c_name", "")))
            alive |= set(weave.get("refs") or ())
            continue
        if is_prunable_module(weave.get("filepath", ""), base_dir):
            std_weaves.append(weave)
        else:
            kept.append(weave)
            alive.add(str(weave.get("name", "")))
            alive.add(str(weave.get("c_name", "")))
            alive |= set(weave.get("refs") or ())

    # 'main' (or an entry alias) is always a root, wherever it lives.
    for weave in std_weaves:
        if weave.get("name") == "main" or weave.get("c_name") == "pengu_main":
            alive.add(str(weave.get("name", "")))
            alive.add(str(weave.get("c_name", "")))

    keep_ids: Set[int] = set()
    changed = True
    while changed:
        changed = False
        for weave in std_weaves:
            if id(weave) in keep_ids:
                continue
            if _is_referenced(weave, alive):
                keep_ids.add(id(weave))
                alive |= set(weave.get("refs") or ())
                alive.add(str(weave.get("name", "")))
                alive.add(str(weave.get("c_name", "")))
                changed = True

    # Preserve the *original* collection order: the code generator monomorphizes
    # lazily and specialization names carry counters, so reordering the weaves
    # changes the emitted program.
    keep_all_ids = {id(w) for w in kept} | keep_ids
    ordered_kept: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    for weave in weaves:
        if id(weave) in keep_all_ids:
            ordered_kept.append(weave)
        else:
            dropped.append(weave)
    return ordered_kept, dropped


def summarize(dropped: Sequence[Dict[str, Any]], before: int, after: int) -> str:
    """One-line report for ``--verbose``."""
    names = ", ".join(sorted({str(w.get("name", "?")) for w in dropped})[:6])
    more = "" if len(dropped) <= 6 else f" (+{len(dropped) - 6} more)"
    pct = (1.0 - (after / before)) * 100.0 if before else 0.0
    return (f"DCE: dropped {len(dropped)} unused std weave(s) "
            f"[{names}{more}] — {before} -> {after} weaves (-{pct:.0f}%)")
