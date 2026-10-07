"""Slice/array arguments and the `at a to b` lowering.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    AliasType,
    Any,
    ArrayType,
    FnType,
    FrozenType,
    ListType,
    ManyType,
    Optional,
    RefType,
    SliceType,
    Tree,
    Type,
)
from .ast_utils import (
    flatten_at_chain,
)
from .ctype import (
    CTypeMapper,
)

class SlicingMixin:
    """Slice/array arguments and the `at a to b` lowering."""

    def _slice_argument(self, node: Any, pt: Optional[Type]) -> Optional[str]:
        """Wrap array expressions/literals into PenguSlice when expected type is SliceType."""
        if pt is None:
            return None
        raw_pt = pt
        while isinstance(raw_pt, (AliasType, FrozenType)):
            raw_pt = getattr(raw_pt, "target", None)
        if not isinstance(raw_pt, SliceType):
            return None

        # Check if argument is already a SliceType or ManyType
        arg_t = self._infer_node_type(node)
        raw_arg_t = arg_t
        while isinstance(raw_arg_t, (AliasType, FrozenType)):
            raw_arg_t = getattr(raw_arg_t, "target", None)
        if isinstance(raw_arg_t, (SliceType, ManyType)):
            return None

        curr = node
        while isinstance(curr, Tree) and curr.data in ("paren_expr", "value_expr") and len(curr.children) == 1:
            curr = curr.children[0]

        if raw_arg_t is None and isinstance(curr, Tree) and curr.data == "var_ref":
            v_name = str(curr.children[0])
            raw_arg_t = self._lookup_var_type(v_name)
            while isinstance(raw_arg_t, (AliasType, FrozenType)):
                raw_arg_t = getattr(raw_arg_t, "target", None)

        elem_t = raw_pt.element
        elem_c = CTypeMapper.to_c_type(elem_t)

        if isinstance(curr, Tree) and curr.data == "array_lit":
            arr_len = len([c for c in curr.children if c is not None])
            elems = ", ".join(self._translate_expr(c, expected_type=elem_t) for c in curr.children if c is not None)
            return f"((PenguSlice){{ .data = ({elem_c}[]){{ {elems} }}, .len = {arr_len}, .elem_size = sizeof({elem_c}) }})"

        if isinstance(raw_arg_t, RefType) and isinstance(raw_arg_t.target, ArrayType):
            arr_len = raw_arg_t.target.size if (raw_arg_t.target.size is not None and str(raw_arg_t.target.size).isdigit()) else (raw_arg_t.target.size if raw_arg_t.target.size is not None else 0)
            arg_code = f"(*({self._translate_expr(node)}))"
            return f"((PenguSlice){{ .data = (void*)({arg_code}), .len = {arr_len}, .elem_size = sizeof({elem_c}) }})"

        if isinstance(raw_arg_t, ArrayType):
            arr_len = raw_arg_t.size if (raw_arg_t.size is not None and str(raw_arg_t.size).isdigit()) else (raw_arg_t.size if raw_arg_t.size is not None else 0)
            arg_code = self._translate_expr(node, expected_type=raw_arg_t)
            return f"((PenguSlice){{ .data = (void*)({arg_code}), .len = {arr_len}, .elem_size = sizeof({elem_c}) }})"

        return None
    def _array_lit_argument(self, node: Any, t: Optional[Type]) -> Optional[str]:
        """C expression for a bare array literal used as an argument.

        A declaration initializer wants ``{ 1, 2, 3 }``, but an argument needs
        an *expression*: a C99 compound literal ``((int32_t[3]){ 1, 2, 3 })``,
        which also decays to the pointer the parameter expects.
        """
        if not (isinstance(node, Tree) and node.data == "array_lit"
                and isinstance(t, (ArrayType,))):
            return None
        size = t.size
        if size is None or not str(size).isdigit():
            size = len([c for c in node.children if c is not None])
        elem_c = CTypeMapper.to_c_type(t.element)
        elems = ", ".join(self._translate_expr(c, expected_type=t.element)
                          for c in node.children if c is not None)
        return f"(({elem_c}[{size}]){{ {elems} }})"
    def _cast_fn_value(self, code: str, expected_type: Optional[Type]) -> str:
        """Casts a function value to the expected function-pointer type.

        C APIs declare callbacks with qualifiers a `.d.pengu` binding cannot
        express (``const void*`` for ``qsort``, ``const char*`` for raylib's
        ``TraceLogCallback``) and GCC 14+ rejects a bare function pointer whose
        signature differs only in those qualifiers. Casting to the declared
        callback type is ABI-neutral and makes those APIs usable.

        Args:
            code: Translated C expression (a function name or lambda name).
            expected_type: The declared parameter/annotation type.

        Returns:
            ``code`` wrapped in a cast when the target is a function pointer.
        """
        target = expected_type
        while isinstance(target, AliasType):
            target = target.target
        is_fn_ptr = (
            isinstance(target, FnType)
            or (isinstance(target, RefType) and isinstance(target.target, FnType))
        )
        if not is_fn_ptr:
            return code
        return f"(({CTypeMapper.to_c_type(expected_type)}){code})"
    def _emit_slice_at(self, node):
        """Emits the slice for a node shaped like `slice_at_expr`."""
        base_node = node.children[0]
        slice_range = node.children[1]
        start_c = self._translate_expr(slice_range.children[0])
        end_c = self._translate_expr(slice_range.children[1])
        base_c = self._translate_expr(base_node)
        base_t = self._infer_node_type(base_node)
        unwrapped_t = base_t.target if isinstance(base_t, RefType) else base_t
        while isinstance(unwrapped_t, (AliasType, FrozenType)) and getattr(unwrapped_t, "target", None):
            unwrapped_t = unwrapped_t.target

        if self._expr_is_string(base_node) or (base_t is not None and base_t.is_string()):
            return f"pengu_string_substring({base_c}, {start_c}, {end_c})"
        if isinstance(unwrapped_t, (SliceType, ManyType)):
            if not self.use_gnu_extensions:
                sl = self.get_temp_name("_sl")
                return self._block_expr(
                    [f"PenguSlice {sl} = ({base_c});"],
                    f"pengu_slice_new((char*){sl}.data + ((size_t)({start_c}) * {sl}.elem_size), {sl}.elem_size, (({end_c}) - ({start_c})))")
            return f"(__extension__({{ PenguSlice _sl = ({base_c}); pengu_slice_new((char*)_sl.data + ((size_t)({start_c}) * _sl.elem_size), _sl.elem_size, (({end_c}) - ({start_c}))); }}))"
        if isinstance(unwrapped_t, ListType):
            if not self.use_gnu_extensions:
                li = self.get_temp_name("_l")
                return self._block_expr(
                    [f"PenguList {li} = ({base_c});"],
                    f"pengu_slice_new((char*){li}.data + ((size_t)({start_c}) * {li}.elem_size), {li}.elem_size, (({end_c}) - ({start_c})))")
            return f"(__extension__({{ PenguList _l = ({base_c}); pengu_slice_new((char*)_l.data + ((size_t)({start_c}) * _l.elem_size), _l.elem_size, (({end_c}) - ({start_c}))); }}))"
        return f"pengu_slice_new(&(({base_c})[{start_c}]), sizeof(({base_c})[0]), (({end_c}) - ({start_c})))"
    def _dotdot_as_slice_shape(self, node):
        """Re-shapes a `range_dotdot` that is really a slice into `slice_at_expr`.

        Returns None for a genuine range. Mirrors `TypeInferrer._range_as_slice`
        so the checker and the generator agree on which `..` nodes are slices.
        """
        children = [c for c in node.children if isinstance(c, Tree)]
        if len(children) != 2:
            return None
        left, right = children[0], children[-1]
        if not (isinstance(left, Tree) and left.data == "at_expr"):
            return None
        chain = flatten_at_chain(left)
        if len(chain) != 2:
            return None
        # slice_at_expr expects (base, slice_range(start, end)).
        slice_range = Tree("slice_range", [chain[1], right])
        return Tree("slice_at_expr", [chain[0], slice_range])
