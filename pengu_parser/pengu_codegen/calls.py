"""Argument lowering for `calling ... with ...`.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    AliasType,
    Any,
    ArrayType,
    CVarArgsType,
    FrozenType,
    List,
    ManyType,
    Optional,
    SliceType,
    Type,
)
from .ctype import (
    CTypeMapper,
)

class CallMixin:
    """Argument lowering for `calling ... with ...`."""

    def _translate_call_arg(self, a: Any, pt: Optional[Type]) -> str:
        slice_arg = self._slice_argument(a, pt)
        if slice_arg is not None:
            return slice_arg
        compound = self._array_lit_argument(a, pt)
        if compound is not None:
            return compound
        return self._translate_expr(a, expected_type=pt)
    def _build_call_args(self, fn_params: List[Any], raw_args: List[Any]) -> List[str]:
        """Formats and translates call arguments, filling defaults and constructing PenguSlice for ManyType."""
        if not fn_params:
            return [self._translate_expr(a) for a in raw_args]

        has_variadic = len(fn_params) > 0 and isinstance(fn_params[-1][1], ManyType)
        has_c_varargs = len(fn_params) > 0 and isinstance(fn_params[-1][1], CVarArgsType)
        if not has_variadic and not has_c_varargs:
            args = []
            for i, a in enumerate(raw_args):
                pt = fn_params[i][1] if i < len(fn_params) else None
                args.append(self._translate_call_arg(a, pt))
            if len(args) < len(fn_params):
                for p in fn_params[len(args):]:
                    if len(p) >= 3 and p[2] is not None:
                        args.append(self._translate_call_arg(p[2], p[1]))
            return args

        if has_c_varargs:
            fixed_params = fn_params[:-1]
            res_args = []
            for i, p in enumerate(fixed_params):
                if i < len(raw_args):
                    res_args.append(self._translate_call_arg(raw_args[i], p[1]))
                elif len(p) >= 3 and p[2] is not None:
                    res_args.append(self._translate_call_arg(p[2], p[1]))
            for a in raw_args[len(fixed_params):]:
                res_args.append(self._translate_expr(a))
            return res_args

        fixed_params = fn_params[:-1]
        variadic_param = fn_params[-1]
        var_elem_type = variadic_param[1].element
        elem_c = CTypeMapper.to_c_type(var_elem_type)

        res_args = []
        fixed_count = len(fixed_params)

        for i, p in enumerate(fixed_params):
            if i < len(raw_args):
                res_args.append(self._translate_call_arg(raw_args[i], p[1]))
            elif len(p) >= 3 and p[2] is not None:
                res_args.append(self._translate_call_arg(p[2], p[1]))

        var_raw_args = raw_args[fixed_count:]
        if len(var_raw_args) == 1:
            arg_t = self._infer_node_type(var_raw_args[0])
            raw_arg_t = arg_t
            while isinstance(raw_arg_t, (AliasType, FrozenType)):
                raw_arg_t = getattr(raw_arg_t, "target", None)
            if isinstance(raw_arg_t, (ManyType, SliceType)):
                res_args.append(self._translate_expr(var_raw_args[0], expected_type=variadic_param[1]))
            elif isinstance(raw_arg_t, ArrayType):
                arr_len = raw_arg_t.size if (raw_arg_t.size is not None and str(raw_arg_t.size).isdigit()) else len(getattr(var_raw_args[0], "children", []))
                arg_code = self._translate_expr(var_raw_args[0], expected_type=raw_arg_t)
                tmp_slice = self.get_temp_name("_tmp_slice")
                if arg_code.strip().startswith("{") and arg_code.strip().endswith("}"):
                    tmp_arr = self.get_temp_name("_tmp_arr")
                    slice_code = f"({{ {elem_c} {tmp_arr}[] = {arg_code}; PenguSlice {tmp_slice} = (PenguSlice){{ .data = {tmp_arr}, .len = {arr_len}, .elem_size = sizeof({elem_c}) }}; {tmp_slice}; }})"
                else:
                    slice_code = f"({{ PenguSlice {tmp_slice} = (PenguSlice){{ .data = (void*){arg_code}, .len = {arr_len}, .elem_size = sizeof({elem_c}) }}; {tmp_slice}; }})"
                res_args.append(slice_code)
            else:
                arg_code = self._translate_expr(var_raw_args[0], expected_type=var_elem_type)
                tmp_arr = self.get_temp_name("_tmp_arr")
                tmp_slice = self.get_temp_name("_tmp_slice")
                slice_code = f"({{ {elem_c} {tmp_arr}[] = {{ {arg_code} }}; PenguSlice {tmp_slice} = (PenguSlice){{ .data = {tmp_arr}, .len = 1, .elem_size = sizeof({elem_c}) }}; {tmp_slice}; }})"
                res_args.append(slice_code)
        elif len(var_raw_args) == 0:
            tmp_slice = self.get_temp_name("_tmp_slice")
            slice_code = f"({{ PenguSlice {tmp_slice} = (PenguSlice){{ .data = NULL, .len = 0, .elem_size = sizeof({elem_c}) }}; {tmp_slice}; }})"
            res_args.append(slice_code)
        else:
            elem_codes = [self._translate_expr(a, expected_type=var_elem_type) for a in var_raw_args]
            elems_str = ", ".join(elem_codes)
            tmp_arr = self.get_temp_name("_tmp_arr")
            tmp_slice = self.get_temp_name("_tmp_slice")
            slice_code = f"({{ {elem_c} {tmp_arr}[] = {{ {elems_str} }}; PenguSlice {tmp_slice} = (PenguSlice){{ .data = {tmp_arr}, .len = {len(var_raw_args)}, .elem_size = sizeof({elem_c}) }}; {tmp_slice}; }})"
            res_args.append(slice_code)

        return res_args
