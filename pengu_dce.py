"""Dead-code elimination over the collected weaves.

The implementation lives in :mod:`pengu_parser.pengu_dce` (it is a compiler
pass); this module re-exports it so ``import pengu_dce`` keeps working from the
toolchain root, as documented in ``docs/PERFORMANCE.md``.
"""

from pengu_parser.pengu_dce import (  # noqa: F401
    collect_references,
    is_prunable_module,
    prune_weaves,
    summarize,
)

__all__ = ["collect_references", "is_prunable_module", "prune_weaves", "summarize"]
