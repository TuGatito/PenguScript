"""Code-generation attributes (`restrict`, release-unsafe mode).

Part of :mod:`pengu_parser.pengu_codegen`; see
:class:`~pengu_parser.pengu_codegen.main.PenguCodegen` for the assembled
generator.
"""
from __future__ import annotations


_RESTRICT_KW = "restrict"
def set_restrict_keyword(target_compiler: str) -> None:
    """Selects the C restrict spelling for the target compiler."""
    global _RESTRICT_KW
    _RESTRICT_KW = "__restrict" if (target_compiler or "").strip().lower() == "msvc" else "restrict"
_RELEASE_UNSAFE = False
def set_release_unsafe(enabled: bool) -> None:
    """Global opt-out of bounds/overflow checks (roadmap 5.2). Callers must also
    pass -DPENGU_BOUNDS_CHECK=0 / -DPENGU_OVERFLOW_CHECK=0 to the C compiler."""
    global _RELEASE_UNSAFE
    _RELEASE_UNSAFE = bool(enabled)
def is_release_unsafe() -> bool:
    return _RELEASE_UNSAFE
