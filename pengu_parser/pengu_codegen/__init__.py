"""PenguScript C code generator.

The generator used to live in a single ``pengu_codegen.py`` module.  It is
now a package whose :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`
class is assembled from one mixin per concern.  This module re-exports
everything the old module exposed, so
``from pengu_parser.pengu_codegen import PenguCodegen`` (and every other
import that used to work) keeps working unchanged.
"""
from ._base import *  # noqa: F401,F403
from ._base import (
    _decl_layout,
    PENGU_EXPECTED_ABI_VERSION,
    PENGU_VERSION,
)
from .attributes import *  # noqa: F401,F403
from .attributes import _RELEASE_UNSAFE, _RESTRICT_KW
from .ast_utils import *  # noqa: F401,F403
from .ast_utils import _extract_attributes_from_node, _normalize_banish_ident
from .ctype import *  # noqa: F401,F403
from .main import PenguCodegen
