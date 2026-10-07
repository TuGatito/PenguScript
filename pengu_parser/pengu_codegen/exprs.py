"""Expression translation: literals, operators, field access and slicing.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    AliasType,
    Any,
    AnyType,
    ArrayType,
    BaseType,
    Dict,
    EchoType,
    FLOAT_TYPE,
    FnType,
    FrozenType,
    INT_TYPE,
    ListType,
    ManyType,
    MapType,
    MaybeType,
    OmenType,
    Optional,
    RangeType,
    RefType,
    ResultType,
    RuneType,
    STRING_TYPE,
    SealType,
    SemanticError,
    SliceType,
    Symbol,
    Token,
    Tree,
    Type,
    TypeInferrer,
    ast_to_type,
    eval_comptime,
    get_type_base_name,
    os,
    re,
)
from .ast_utils import (
    flatten_at_chain,
    get_generic_ast_name,
)
from .ctype import (
    CTypeMapper,
)

class ExprMixin:
    """Expression translation: literals, operators, field access and slicing."""

    def _translate_expr(self, node: Any, expected_type: Optional[Type] = None) -> str:
        """Translates an expression node, tracking that we are in expression context.

        Expression context suppresses `#line` markers: a statement-expression
        built here can end up as the argument of a function-like macro
        (`pengu_to_string(x)`), where a preprocessor directive would break the
        macro invocation.
        """
        self._expr_depth += 1
        try:
            return self._translate_expr_impl(node, expected_type)
        finally:
            self._expr_depth -= 1
    def _translate_expr_impl(self, node: Any, expected_type: Optional[Type] = None) -> str:
        """Translates expression node into C99 expression string."""
        if node is None:
            return ""

        if isinstance(node, Token):
            val = str(node)
            if node.type == "INT":
                return val
            elif node.type == "FLOAT":
                return val
            elif node.type == "CHAR_LIT":
                return val
            elif node.type in ("STRING", "TRIPLE_STRING", "RAW_STRING", "RAW_TRIPLE_STRING"):
                is_c_str = self._is_ref_char_type(expected_type)
                return self._translate_string_lit(val, as_c_literal=is_c_str)
            elif node.type == "NAME":
                for o_name, o_variants in self.omens.items():
                    if val.startswith(f"{o_name}_") and val[len(o_name) + 1:] in o_variants:
                        return val
                    if val in o_variants:
                        return self._get_omen_variant_c_name(o_name, val)
                return val
            return val

        if not isinstance(node, Tree):
            return str(node)

        # Check const folding for entire expression
        if node.data not in ("string_lit", "interpolated_string"):
            folded = self.const_folder.fold(node)
            if folded is not None and not (isinstance(folded, str) and node.data in ("add", "chr_expr")):
                return self._format_const_val(folded, expected_type=expected_type)

        rule = node.data

        # 1. Literals
        if rule == "int_lit":
            raw_int = str(node.children[0]).replace("_", "")
            if raw_int.lower().startswith("0b"):
                return str(int(raw_int, 2))
            if raw_int.lower().startswith("0o"):
                return str(int(raw_int, 8))
            return raw_int
        elif rule == "float_lit":
            return str(node.children[0]).replace("_", "")
        elif rule == "char_lit":
            raw_c = str(node.children[0]) if node.children else "''"
            if raw_c.startswith("'") and raw_c.endswith("'") and len(raw_c) >= 2:
                inner = raw_c[1:-1]
                if inner.startswith(r"\u{") and inner.endswith("}"):
                    try:
                        cp = int(inner[3:-1], 16)
                        return f"'\\x{cp:02x}'"
                    except ValueError:
                        pass
                elif inner.startswith(r"\u") and len(inner) == 6:
                    try:
                        cp = int(inner[2:], 16)
                        return f"'\\x{cp:02x}'"
                    except ValueError:
                        pass
            return raw_c
        elif rule == "string_lit":
            is_c_str = self._is_ref_char_type(expected_type)
            raw_s = str(node.children[0]) if node.children else ""
            return self._translate_string_lit(raw_s, as_c_literal=is_c_str)
        elif rule == "true_lit":
            return "true"
        elif rule == "false_lit":
            return "false"
        elif rule == "null_lit":
            return "NULL"
        elif rule == "maybe_none":
            return "pengu_maybe_none()"
        elif rule == "donum_expr":
            # 'donum T' lowers to the C zero-initialiser.  Compound literals
            # work for scalars, pointers and structs alike, so no runtime
            # helper call is needed.
            def lookup_tp_donum(n):
                if getattr(self, "current_subst_map", None) and n in self.current_subst_map:
                    return self.current_subst_map[n]
                sym = self.symbols.lookup(n) if self.symbols else None
                return sym.type if sym else None

            dt = expected_type
            if dt is None and node.children:
                dt = ast_to_type(node.children[0], lookup_tp_donum)
            if getattr(self, "current_subst_map", None) and dt is not None:
                dt = dt.substitute(self.current_subst_map)
            if dt is None:
                return "{0}"
            c_t = CTypeMapper.to_c_type(dt)
            if c_t.strip() in ("void", ""):
                return "{0}"
            return f"({c_t}){{0}}"
        elif rule == "error_lit":
            return "error"
        elif rule in ("try_expr", "or_else", "or_return"):
            return self._translate_unwrap_expr(rule, node, expected_type)
        elif rule == "or_block":
            left_op = node.children[0]
            block_stmts = [c for c in node.children[1:] if isinstance(c, Tree)]
            return self._translate_or_block(left_op, block_stmts)
        elif rule == "var_ref":
            # Variable reference resolution: handles constants, omen variants,
            # 'with:' target fields, and local variables or decayed function pointers.
            # (Note: 'or_block' constructs are handled explicitly above via
            # _translate_or_block and never fall through to var_ref).
            name = str(node.children[0])
            sym = self.symbols.lookup(name) if self.symbols else None
            if sym and hasattr(sym, "const_val") and sym.const_val is not None and not getattr(sym, "is_mutable", False) and getattr(sym, "kind", "") in ("const", "let"):
                return self._format_const_val(sym.const_val, expected_type=expected_type)
            if name in self.consts and self.consts[name][1] is not None:
                return self._format_const_val(self.consts[name][1], expected_type=expected_type)
            for o_name, o_variants in self.omens.items():
                if name.startswith(f"{o_name}_") and name[len(o_name) + 1:] in o_variants:
                    return name
                if name in o_variants:
                    return self._omen_variant_expr(o_name, name, expected_type)
            # Inside a 'with:' scope, a bare name means a field of the target —
            # unless it is a known local (function/loop/block local), which must
            # stay a plain identifier (e.g. a loop variable used in a builder).
            if self.with_stack and (not sym or sym.kind == "field") and name not in self.local_vars:
                base_target = self.with_stack[-1]
                base_type = self._get_current_with_target_type()
                sep = "->" if (base_target == "self" or isinstance(base_type, RefType)) else "."
                return f"{base_target}{sep}{name}"
            code = self._c_ident(name)
            is_fn_symbol = (
                getattr(sym, "kind", "") in ("declare", "weave", "function")
                or name in self.fn_info
            )
            # A local (parameter, loop variable, `var`/`let`) shadows a module
            # level weave of the same name: `var words as list of string is
            # calling s.words` followed by `words.length` must read the local,
            # not decay the function to a pointer.
            if is_fn_symbol and name not in self.local_vars:
                # A weave used as a value (callback argument, assignment).  Use
                # the symbol's recorded C name when it has one: in a prefixed
                # module (std.* modules carry an insignia) the definition is
                # emitted as '<prefix>_<name>', so decaying to a function
                # pointer must reference that same C symbol.
                resolved_c = getattr(node, "_pengu_resolved_c_name", None)
                if not resolved_c and self.current_source_file:
                    for w in self.weaves:
                        if w.get("name") == name and w.get("filepath") == self.current_source_file:
                            resolved_c = w.get("c_name")
                            break
                if not resolved_c and sym and getattr(sym, "c_name", None) and sym.c_name != name:
                    resolved_c = sym.c_name
                if not resolved_c and name in self.fn_info and self.fn_info[name].get("c_name"):
                    resolved_c = self.fn_info[name]["c_name"]
                fn_code = resolved_c or getattr(sym, "c_name", None) or code
                return self._cast_fn_value(fn_code, expected_type)
            return code

        elif rule == "self_ref":
            return "self"


        elif rule == "bool_and":
            return (f"({self._translate_expr(node.children[0])} && "
                    f"{self._translate_expr(node.children[1])})")
        elif rule == "bool_or":
            return (f"({self._translate_expr(node.children[0])} || "
                    f"{self._translate_expr(node.children[1])})")

        # 2. Binary Arithmetic and Logic
        elif rule == "add":
            # Numeric-only by design: string composition uses '{expr}'
            # interpolation and the checker rejects a string operand (E0005).
            # No pengu_string_concat / pengu_to_string promotion happens here.
            left = self._translate_expr(node.children[0])
            right = self._translate_expr(node.children[1])
            return f"({left} + {right})"

        elif rule in ("eq", "ne"):
            left_node, right_node = node.children[0], node.children[1]
            # Infer first so each side can use the other's type as context
            # (a bare algebraic-omen variant needs it to become a struct value).
            left_t = self._infer_node_type(left_node)
            right_t = self._infer_node_type(right_node)
            left = self._translate_expr(left_node, expected_type=right_t)
            right = self._translate_expr(right_node, expected_type=left_t)
            if self._is_string_expr(left_node) or self._is_string_expr(right_node):
                left_str = left if self._is_string_expr(left_node) else self._to_string_call(left, left_t)
                right_str = right if self._is_string_expr(right_node) else self._to_string_call(right, right_t)
                if rule == "eq":
                    return f"pengu_string_equal({left_str}, {right_str})"
                else:
                    return f"(!pengu_string_equal({left_str}, {right_str}))"
            def _get_derived(tp):
                while isinstance(tp, (AliasType, FrozenType, SealType)):
                    tp = getattr(tp, "target", None) or getattr(tp, "underlying", None)
                if isinstance(tp, RuneType) and not isinstance(tp, RefType):
                    return tp
                # Algebraic omens are tagged structs: C's '==' is invalid, so
                # the derived '_eq_val' helper must be called instead.  Simple
                # omens are plain enums and keep native equality.
                if isinstance(tp, OmenType) and tp.is_algebraic:
                    return tp
                return None
            derived_t = _get_derived(left_t) or _get_derived(right_t)
            if derived_t is not None:
                c_dt = self._derived_type_c_name(derived_t)
                eq_call = f"{c_dt}_eq_val({left}, {right})"
                return eq_call if rule == "eq" else f"(!{eq_call})"
            op = "==" if rule == "eq" else "!="
            return f"({left} {op} {right})"

        elif rule in ("sub", "mul", "div", "mod", "shl", "shr", "bitwise_and", "bitwise_or", "bitwise_xor",
                      "lt", "le", "gt", "ge"):
            op_map = {
                "sub": "-", "mul": "*", "div": "/", "mod": "%",
                "shl": "<<", "shr": ">>", "bitwise_and": "&", "bitwise_or": "|", "bitwise_xor": "^",
                "lt": "<", "le": "<=", "gt": ">", "ge": ">=",
            }
            left = self._translate_expr(node.children[0], expected_type=self._infer_node_type(node.children[1]))
            right = self._translate_expr(node.children[1], expected_type=self._infer_node_type(node.children[0]))
            if rule in ("lt", "le", "gt", "ge"):
                left_t = self._infer_node_type(node.children[0])
                right_t = self._infer_node_type(node.children[1])
                def _get_derived(tp):
                    while isinstance(tp, (AliasType, FrozenType, SealType)):
                        tp = getattr(tp, "target", None) or getattr(tp, "underlying", None)
                    if isinstance(tp, RuneType) and not isinstance(tp, RefType):
                        return tp
                    if isinstance(tp, OmenType) and tp.is_algebraic:
                        return tp
                    return None
                derived_t = _get_derived(left_t) or _get_derived(right_t)
                if derived_t is not None:
                    c_dt = self._derived_type_c_name(derived_t)
                    cmp_op = op_map[rule]
                    return f"({c_dt}_cmp_val({left}, {right}) {cmp_op} 0)"
            return f"({left} {op_map[rule]} {right})"

        elif rule in ("in_expr", "not_in_expr"):
            elem_node = node.children[0]
            col_node = node.children[1]

            col_t = self._infer_node_type(col_node)
            elem_t = self._infer_node_type(elem_node)

            elem_c = self._translate_expr(elem_node)
            col_c = self._translate_expr(col_node)

            is_not = (rule == "not_in_expr")

            # Check if Range
            if isinstance(col_t, RangeType) or (
                col_t is None and isinstance(col_node, Tree)
                and col_node.data in ("to_expr", "range_dotdot")
            ):
                if not self.use_gnu_extensions:
                    v_t = self.get_temp_name("_v")
                    r_t = self.get_temp_name("_r")
                    vd = (CTypeMapper.to_c_decl(elem_t, v_t) if elem_t is not None
                          else f"int64_t {v_t}")
                    cond = (f"({v_t} < {r_t}.start || {v_t} >= {r_t}.end)" if is_not
                            else f"({v_t} >= {r_t}.start && {v_t} < {r_t}.end)")
                    return self._block_expr(
                        [f"{vd} = ({elem_c});", f"PenguRange {r_t} = ({col_c});"], cond)
                if is_not:
                    return f"(__extension__({{ __auto_type _v = ({elem_c}); PenguRange _r = ({col_c}); (_v < _r.start || _v >= _r.end); }}))"
                else:
                    return f"(__extension__({{ __auto_type _v = ({elem_c}); PenguRange _r = ({col_c}); (_v >= _r.start && _v < _r.end); }}))"

            # Check if String
            if (col_t is not None and col_t.is_string()) or (isinstance(col_t, BaseType) and col_t.name == "string") or self._expr_is_string(col_node):
                unwrapped_elem_t = elem_t
                while isinstance(unwrapped_elem_t, (AliasType, FrozenType)) and getattr(unwrapped_elem_t, "target", None):
                    unwrapped_elem_t = unwrapped_elem_t.target
                elem_name = getattr(unwrapped_elem_t, "name", "")
                is_char_like = (
                    elem_name in ("char", "byte", "u8", "int8_t", "uint8_t")
                    or (isinstance(elem_node, Token) and elem_node.type == "CHAR_LIT")
                )
                if is_char_like:
                    if is_not:
                        return f"(strchr(({col_c}).data, (char)({elem_c})) == NULL)"
                    return f"(strchr(({col_c}).data, (char)({elem_c})) != NULL)"
                else:
                    if is_not:
                        return f"(strstr(({col_c}).data, ({elem_c}).data) == NULL)"
                    return f"(strstr(({col_c}).data, ({elem_c}).data) != NULL)"

            # Check if Map
            if isinstance(col_t, MapType):
                if not self.use_gnu_extensions:
                    mc = self.get_temp_name("_mc")
                    k_tmp = self.get_temp_name("_mk")
                    k_type_str = CTypeMapper.to_c_type(col_t.key)
                    check_str = (f"pengu_map_get(&{mc}, &{k_tmp}) == NULL" if is_not
                                 else f"pengu_map_get(&{mc}, &{k_tmp}) != NULL")
                    return self._block_expr(
                        [f"PenguMap {mc} = ({col_c});", f"{k_type_str} {k_tmp} = ({elem_c});"],
                        check_str)
                k_tmp = self.get_temp_name("_mk")
                k_type_str = CTypeMapper.to_c_type(col_t.key)
                check_str = f"pengu_map_get(&_mc, &{k_tmp}) != NULL" if not is_not else f"pengu_map_get(&_mc, &{k_tmp}) == NULL"
                return f"(__extension__({{ PenguMap _mc = ({col_c}); {k_type_str} {k_tmp} = ({elem_c}); {check_str}; }}))"

            # Check if Array
            if isinstance(col_t, ArrayType) and col_t.size is not None:
                if not self.use_gnu_extensions:
                    val_t = self.get_temp_name("_val")
                    arr_p = self.get_temp_name("_arrp")
                    flag = self.get_temp_name("_f")
                    idx = self.get_temp_name("_i")
                    elem_ct = CTypeMapper.to_c_type(col_t.element)
                    vd = CTypeMapper.to_c_decl(elem_t or col_t.element, val_t)
                    cmp = self._make_elem_eq(col_t.element, f"{arr_p}[{idx}]", val_t)
                    cond = f"!{flag}" if is_not else flag
                    return self._block_expr([
                        f"{vd} = ({elem_c});",
                        f"{elem_ct} *{arr_p} = ({col_c});",
                        f"bool {flag} = false;",
                        f"for (size_t {idx} = 0; {idx} < {col_t.size}; ++{idx}) {{ if ({cmp}) {{ {flag} = true; break; }} }}",
                    ], cond)
                cmp = self._make_elem_eq(col_t.element, "(_arr)[_i]", "_val")
                check_code = (
                    f"bool _f = false; "
                    f"for (size_t _i = 0; _i < {col_t.size}; ++_i) {{ "
                    f"  if ({cmp}) {{ _f = true; break; }} "
                    f"}} "
                    f"{'!_f' if is_not else '_f'};"
                )
                return f"(__extension__({{ __auto_type _val = ({elem_c}); __auto_type _arr = ({col_c}); {check_code} }}))"

            # Check if List
            if isinstance(col_t, ListType):
                elem_c_t = CTypeMapper.to_c_type(col_t.element)
                if not self.use_gnu_extensions:
                    val_t = self.get_temp_name("_val")
                    lc = self.get_temp_name("_lc")
                    flag = self.get_temp_name("_f")
                    idx = self.get_temp_name("_i")
                    vd = CTypeMapper.to_c_decl(elem_t or col_t.element, val_t)
                    cmp = self._make_elem_eq(
                        col_t.element, f"*({elem_c_t}*)pengu_list_at(&{lc}, {idx})", val_t)
                    cond = f"!{flag}" if is_not else flag
                    return self._block_expr([
                        f"{vd} = ({elem_c});",
                        f"PenguList {lc} = ({col_c});",
                        f"bool {flag} = false;",
                        f"for (int32_t {idx} = 0; {idx} < {lc}.len; ++{idx}) {{ if ({cmp}) {{ {flag} = true; break; }} }}",
                    ], cond)
                cmp = self._make_elem_eq(col_t.element, f"*({elem_c_t}*)pengu_list_at(&_lc, _i)", "_val")
                return (
                    f"(__extension__({{ __auto_type _val = ({elem_c}); "
                    f"PenguList _lc = ({col_c}); bool _f = false; "
                    f"for (int32_t _i = 0; _i < _lc.len; ++_i) {{ "
                    f"if ({cmp}) {{ _f = true; break; }} }} "
                    f"{'!_f' if is_not else '_f'}; }}))"
                )

            # Check if Slice / Many
            if isinstance(col_t, (SliceType, ManyType)):
                elem_c_t = CTypeMapper.to_c_type(col_t.element)
                if not self.use_gnu_extensions:
                    val_t = self.get_temp_name("_val")
                    sl = self.get_temp_name("_sl")
                    flag = self.get_temp_name("_f")
                    idx = self.get_temp_name("_i")
                    vd = CTypeMapper.to_c_decl(elem_t or col_t.element, val_t)
                    cmp = self._make_elem_eq(
                        col_t.element, f"(({elem_c_t}*)({sl}).data)[{idx}]", val_t)
                    cond = f"!{flag}" if is_not else flag
                    return self._block_expr([
                        f"{vd} = ({elem_c});",
                        f"PenguSlice {sl} = ({col_c});",
                        f"bool {flag} = false;",
                        f"for (int32_t {idx} = 0; {idx} < {sl}.len; ++{idx}) {{ if ({cmp}) {{ {flag} = true; break; }} }}",
                    ], cond)
                cmp = self._make_elem_eq(col_t.element, f"((({elem_c_t}*)(_sl).data)[_i])", "_val")
                return (
                    f"(__extension__({{ __auto_type _val = ({elem_c}); "
                    f"PenguSlice _sl = ({col_c}); bool _f = false; "
                    f"for (int32_t _i = 0; _i < _sl.len; ++_i) {{ "
                    f"if ({cmp}) {{ _f = true; break; }} }} "
                    f"{'!_f' if is_not else '_f'}; }}))"
                )

            # Fallback
            if is_not:
                return f"(!({elem_c} == {col_c}))"
            return f"({elem_c} == {col_c})"

        # 3. Unary
        elif rule == "neg":
            return f"(-{self._translate_expr(node.children[0])})"
        elif rule == "log_not":
            return f"(!{self._translate_expr(node.children[0])})"
        elif rule == "bit_not":
            return f"(~{self._translate_expr(node.children[0])})"
        elif rule == "sigil_of":
            return f"(&{self._translate_expr(node.children[0])})"
        elif rule == "essence_of":
            child = node.children[0]
            # Compatibility: 'essence of (x length)' evaluated directly as '(x length)' because length is already a value, not a pointer.
            if isinstance(child, Tree) and child.data == "length_expr":
                return self._translate_expr(child)
            return f"(*{self._translate_expr(node.children[0])})"
        elif rule == "transmute":
            expr_str = self._translate_expr(node.children[0])
            def lookup_tp_trans(n):
                if hasattr(self, "current_subst_map") and self.current_subst_map and n in self.current_subst_map:
                    return self.current_subst_map[n]
                sym = self.symbols.lookup(n) if self.symbols else None
                return sym.type if sym else None
            t = ast_to_type(node.children[1], lookup_tp_trans)
            if hasattr(self, "current_subst_map") and self.current_subst_map:
                t = t.substitute(self.current_subst_map)
            t_str = CTypeMapper.to_c_type(t)
            return f"(({t_str})({expr_str}))"
        elif rule == "size_of":
            def lookup_tp_size(n):
                if hasattr(self, "current_subst_map") and self.current_subst_map and n in self.current_subst_map:
                    return self.current_subst_map[n]
                sym = self.symbols.lookup(n) if self.symbols else None
                return sym.type if sym else None
            t = ast_to_type(node.children[0], lookup_tp_size)
            if hasattr(self, "current_subst_map") and self.current_subst_map:
                t = t.substitute(self.current_subst_map)
            t_str = CTypeMapper.to_c_type(t)
            return f"sizeof({t_str})"
        elif rule == "banish_expr":
            return self._translate_banish_target(node.children[0])

        # 3b. 'some expr': heap-box a value into a present PenguMaybe.
        elif rule == "some_expr":
            arg_node = node.children[0]
            # The element type of the target 'maybe T' is authoritative when the
            # payload has no inferable type of its own (e.g. a struct literal
            # 'some (with f is 1)'), which used to fail with E0005.
            arg_expected = expected_type.element if isinstance(expected_type, MaybeType) else None
            arg_c = self._translate_expr(arg_node, expected_type=arg_expected)
            arg_t = self._infer_node_type(arg_node) or arg_expected
            if arg_t is None:
                if isinstance(arg_node, Tree) and arg_node.data in ("int_lit", "true_lit", "false_lit"):
                    arg_t = INT_TYPE
                elif isinstance(arg_node, Tree) and arg_node.data == "string_lit":
                    arg_t = STRING_TYPE
                elif isinstance(arg_node, Tree) and arg_node.data == "float_lit":
                    arg_t = FLOAT_TYPE
                else:
                    # Guessing 'int32_t' here used to silently truncate the
                    # boxed payload: fail loudly instead.
                    raise SemanticError(
                        "Cannot determine the payload type of 'some'",
                        code="E0005",
                        help="Annotate the value or bind it to a typed variable first "
                             "('var v as T is ...' then 'some v').",
                        note="'some' boxes a value of a statically known type."
                    )
            tmp = self.get_temp_name("_some")
            decl_tmp = CTypeMapper.to_c_decl(arg_t, tmp)
            maybe_tmp = self.get_temp_name("_maybe")
            # The box stores the payload bytes (memcpy).  It does not clone a
            # heap payload: the source keeps ownership of its buffer, exactly as
            # in C, and releasing either side is the programmer's decision.
            stmts = [
                f"{decl_tmp} = {arg_c};",
                f"PenguMaybe {maybe_tmp};",
                f"{maybe_tmp}.is_present = true;",
                f"{maybe_tmp}.value = pengu_sigil_alloc(sizeof({tmp}));",
                f"if (!{maybe_tmp}.value) {maybe_tmp}.is_present = false;",
                f"else memcpy({maybe_tmp}.value, &({tmp}), sizeof({tmp}));",
            ]
            return self._block_expr(stmts, maybe_tmp)

        # 3b-bis. 'ok expr' / 'err expr': native result construction.
        elif rule in ("ok_expr", "err_expr"):
            arg_node = node.children[0]
            arg_c = self._translate_expr(arg_node)
            arg_t = self._infer_node_type(arg_node)
            if arg_t is None:
                if isinstance(arg_node, Tree) and arg_node.data in ("int_lit", "true_lit", "false_lit"):
                    arg_t = INT_TYPE
                elif isinstance(arg_node, Tree) and arg_node.data == "string_lit":
                    arg_t = STRING_TYPE
                elif isinstance(arg_node, Tree) and arg_node.data == "float_lit":
                    arg_t = FLOAT_TYPE
                else:
                    raise SemanticError(
                        f"Cannot determine the payload type of '{rule[:-5]}'",
                        code="E0005",
                        help="Annotate the value or bind it to a typed variable first "
                             "('var v as T is ...' then 'ok v' / 'err v').",
                        note="'ok'/'err' box a value of a statically known type."
                    )
            is_ok = rule == "ok_expr"
            side = "ok_val" if is_ok else "err_val"
            tmp = self.get_temp_name("_res_val")
            decl_tmp = CTypeMapper.to_c_decl(arg_t, tmp)
            res_tmp = self.get_temp_name("_result")
            stmts = [
                f"{decl_tmp} = {arg_c};",
                f"PenguResult {res_tmp};",
                f"{res_tmp}.is_ok = {'true' if is_ok else 'false'};",
                f"{res_tmp}.ok_val = NULL;",
                f"{res_tmp}.err_val = NULL;",
                f"{res_tmp}.{side} = pengu_sigil_alloc(sizeof({tmp}));",
                f"if (!{res_tmp}.{side}) {res_tmp}.is_ok = {'false' if is_ok else 'true'};",
                f"else memcpy({res_tmp}.{side}, &({tmp}), sizeof({tmp}));",
            ]
            return self._block_expr(stmts, res_tmp)

        # 3c. 'ord expr': byte code of a single-character string.
        elif rule == "ord_expr":
            arg_node = node.children[0]
            arg_c = self._translate_expr(arg_node)
            if self._is_side_effect_free(arg_node):
                return (
                    f"((int32_t)((unsigned char)((({arg_c}).data && ({arg_c}).len > 0) ? "
                    f"({arg_c}).data[0] : '\\0')))"
                )
            tmp = self.get_temp_name("_ord_s")
            return self._block_expr(
                [f"PenguString {tmp} = ({arg_c});"],
                f"((int32_t)((unsigned char)(({tmp}.data && {tmp}.len > 0) ? {tmp}.data[0] : 0)))",
            )

        # 3d. 'chr expr': one-character string from an integer byte value.
        elif rule == "chr_expr":
            arg_c = self._translate_expr(node.children[0])
            return f"pengu_string_from_char((char)({arg_c}))"

        # 3e. 'bytes of expr': borrow string characters (read-only) or the first
        # element of an 'array of byte' (writable) as a byte pointer.
        elif rule == "bytes_expr":
            arg_node = node.children[0]
            arg_c = self._translate_expr(arg_node)
            arg_t = self._infer_node_type(arg_node)
            if isinstance(arg_t, ArrayType):
                return f"(&(({arg_c})[0]))"
            return f"((const uint8_t*)((({arg_c})).data))"

        # 4. Invocations / Calling
        elif rule == "calling_expr":
            target_node = node.children[0]
            # Compiler-provided result constructors: 'calling ok_of with v' /
            # 'calling oracle.ok_of with v' (same for err_of).  They are handled
            # as intrinsics because 'ok'/'err' cannot become grammar keywords
            # without breaking existing code that uses them as identifiers.
            ctor = self._result_ctor_name(target_node)
            if ctor is not None:
                ctor_arg = self._first_call_arg(node)
                if ctor_arg is None:
                    raise SemanticError(
                        f"'{ctor}' expects exactly one argument",
                        code="E0005",
                        help=f"Use 'calling {ctor} with value'.",
                    )
                return self._translate_result_ctor(ctor_arg, ctor == "ok_of")
            explicit_type_args = []
            args_node = None
            for ch in node.children[1:]:
                if isinstance(ch, Tree):
                    if ch.data == "generic_args":
                        explicit_type_args = [ast_to_type(c, self._lookup_type_fn) for c in ch.children if c is not None]
                    elif ch.data == "arg_list":
                        args_node = ch

            # Translate arguments
            raw_arg_nodes = []
            args = []
            if args_node and isinstance(args_node, Tree) and args_node.data == "arg_list":
                arg_children = list(args_node.children)
                ordered = self._reorder_named_arg_nodes(arg_children, target_node)
                if ordered is not None:
                    arg_children = ordered
                for arg in arg_children:
                    if isinstance(arg, Tree):
                        if arg.data == "pos_arg":
                            raw_arg_nodes.append(arg.children[0])
                            args.append(self._translate_expr(arg.children[0]))
                        elif arg.data == "named_arg":
                            raw_arg_nodes.append(arg.children[1])
                            args.append(self._translate_expr(arg.children[1]))

            # 1. Normal target method call: obj.method(...) or self->items.method(...)
            if target_node.data == "normal_target" and len(target_node.children) >= 2 and target_node.children[-1].data in ("dot_access", "arrow_access"):
                m_name = str(target_node.children[-1].children[0])
                base_parts = target_node.children[:-1]

                obj_expr_str = str(base_parts[0])
                for part in base_parts[1:]:
                    if isinstance(part, Tree) and part.data == "arrow_access":
                        obj_expr_str += f"->{str(part.children[0])}"
                    elif isinstance(part, Tree) and part.data == "dot_access":
                        obj_expr_str += f".{str(part.children[0])}"

                obj_name = str(base_parts[0]) if len(base_parts) == 1 and isinstance(base_parts[0], (Token, str)) else None

                # Check if this is an imported module call (e.g. spark.println or webui.new_window)
                if obj_name:
                    obj_sym = self.symbols.lookup(obj_name) if self.symbols else None
                    if obj_sym is not None and obj_sym.kind == "import":
                        mod_prefix = getattr(obj_sym, "c_name", None) or obj_name
                        prefixed = f"{mod_prefix}_{m_name}"
                        alias_prefixed = f"{obj_name}_{m_name}"
                        if explicit_type_args:
                            m_suf = "_".join(t.get_mangled_name() for t in explicit_type_args)
                            for cand in (f"{prefixed}_{m_suf}", f"{alias_prefixed}_{m_suf}", f"{m_name}_{m_suf}"):
                                if cand in self.symbols.monomorphized_functions or cand in self.fn_info:
                                    prefixed = cand
                                    break
                        elif prefixed in self.fn_info:
                            prefixed = prefixed
                        elif alias_prefixed in self.fn_info:
                            prefixed = alias_prefixed
                        elif hasattr(self.symbols, "monomorphized_functions"):
                            m_matches = [m for m in self.symbols.monomorphized_functions if m.startswith(f"{prefixed}_") or m.startswith(f"{alias_prefixed}_")]
                            if not m_matches:
                                m_matches = [m for m, entry in self.symbols.monomorphized_functions.items()
                                             if m.startswith(f"{m_name}_") and get_generic_ast_name(entry[0]) == m_name]
                            if len(m_matches) == 1:
                                prefixed = m_matches[0]
                        # Prefer the unambiguous module-scoped C name when the code
                        # generator registered it (avoids collisions when another
                        # module exports a function with the same source name).
                        match_prefix = prefixed if (prefixed in self.fn_info or (hasattr(self.symbols, "monomorphized_functions") and prefixed in self.symbols.monomorphized_functions)) else (alias_prefixed if alias_prefixed in self.fn_info else None)
                        if match_prefix:
                            prefixed = match_prefix
                            fn_entry = self.fn_info.get(prefixed)
                            c_fn_name = fn_entry.get("c_name") if fn_entry and fn_entry.get("c_name") else prefixed
                            if fn_entry and fn_entry.get("params"):
                                args = self._build_call_args(fn_entry["params"], raw_arg_nodes)
                            elif fn_entry:
                                fn_params = fn_entry["params"]
                                if len(args) < len(fn_params):
                                    for p in fn_params[len(args):]:
                                        if len(p) >= 3 and p[2] is not None:
                                            args.append(self._translate_expr(p[2]))
                            return f"{c_fn_name}({', '.join(args)})"
                        # Fallback path (aliased imports, insignia-prefixed members):
                        # resolve through the imported module's own member scope.
                        mod_sym = obj_sym.module_scope.lookup(m_name) if obj_sym.module_scope else None
                        c_fn_name = mod_sym.get_c_name() if (mod_sym and hasattr(mod_sym, "get_c_name")) else None
                        if not c_fn_name:
                            if hasattr(self.symbols, "monomorphized_functions"):
                                if prefixed in self.symbols.monomorphized_functions:
                                    c_fn_name = prefixed
                                elif alias_prefixed in self.symbols.monomorphized_functions:
                                    c_fn_name = alias_prefixed
                                elif m_name in self.symbols.monomorphized_functions:
                                    c_fn_name = m_name
                            if not c_fn_name:
                                c_fn_name = prefixed if prefixed in self.fn_info else (alias_prefixed if alias_prefixed in self.fn_info else m_name)
                        fn_entry = self.fn_info.get(c_fn_name) or self.fn_info.get(prefixed) or self.fn_info.get(alias_prefixed) or self.fn_info.get(m_name)
                        if fn_entry and fn_entry.get("c_name"):
                            c_fn_name = fn_entry["c_name"]
                        if fn_entry and fn_entry.get("params"):
                            args = self._build_call_args(fn_entry["params"], raw_arg_nodes)
                        elif fn_entry:
                            fn_params = fn_entry["params"]
                            if len(args) < len(fn_params):
                                for p in fn_params[len(args):]:
                                    if len(p) >= 3 and p[2] is not None:
                                        args.append(self._translate_expr(p[2]))
                        return f"{c_fn_name}({', '.join(args)})"

                # Check if this is a static/ritual method call on a type (e.g. Vec2.zero(...) or Point.create(...))
                if obj_name and (obj_name in self.runes or obj_name in self.echos or obj_name in self.omens or obj_name in self.seals or obj_name in self.concepts or (self.symbols and (self.symbols.lookup_type(obj_name) or self.symbols.lookup_concept(obj_name)))):
                    sym_t = self.symbols.lookup_type(obj_name) if self.symbols else None
                    t_c_name = getattr(sym_t, "c_name", None) or self._c_ident(obj_name)
                    c_m_name = self._c_ident(m_name)
                    c_fn_name = f"{t_c_name}_{c_m_name}"
                    if c_fn_name not in self.fn_info and not any(w["c_name"] == c_fn_name for w in self.weaves):
                        plain_cand = f"{self._c_ident(obj_name)}_{c_m_name}"
                        if plain_cand in self.fn_info or any(w["c_name"] == plain_cand for w in self.weaves):
                            c_fn_name = plain_cand
                        elif hasattr(self.symbols, "monomorphized_methods"):
                            matches = [m for m in self.symbols.monomorphized_methods if (m.startswith(f"{self._c_ident(obj_name)}_") and m.endswith(f"_{c_m_name}")) or m.startswith(f"{plain_cand}_")]
                            if matches:
                                c_fn_name = matches[0]
                    fn_entry = self.fn_info.get(c_fn_name)
                    if fn_entry and fn_entry.get("params") is not None:
                        fn_params = fn_entry["params"]
                        call_args = self._build_call_args(fn_params, raw_arg_nodes)
                        return f"{c_fn_name}({', '.join(call_args)})"
                    elif any(w["c_name"] == c_fn_name for w in self.weaves):
                        return f"{c_fn_name}({', '.join(args)})"

                # Lookup object type
                if obj_name:
                    obj_type = self._lookup_var_type(obj_name)
                else:
                    cur_t = self._lookup_var_type(str(base_parts[0]))
                    for part in base_parts[1:]:
                        if isinstance(part, Tree) and part.children:
                            field_n = str(part.children[0])
                            cur_t = self._lookup_field_type_on(cur_t, field_n)
                    obj_type = cur_t

                actual_obj_type = obj_type
                if isinstance(actual_obj_type, AliasType):
                    actual_obj_type = actual_obj_type.target
                if isinstance(actual_obj_type, RefType) and isinstance(actual_obj_type.target, AliasType):
                    actual_obj_type = RefType(actual_obj_type.target.target)

                # Built-in ListType methods
                self_ptr = obj_expr_str if (isinstance(obj_type, RefType) or obj_expr_str == "self") else f"&{obj_expr_str}"
                if isinstance(actual_obj_type, ListType) or (isinstance(actual_obj_type, RefType) and isinstance(actual_obj_type.target, ListType)):
                    list_t = actual_obj_type.target if isinstance(actual_obj_type, RefType) else actual_obj_type
                    elem_c = CTypeMapper.to_c_type(list_t.element)
                    arg0 = args[0] if args else ""
                    tmp_elem = self.get_temp_name("_elem")
                    if m_name in ("push", "append"):
                        if not args:
                            return "0"
                        if not self.use_gnu_extensions:
                            self._hoist(f"{elem_c} {tmp_elem} = ({arg0});")
                            return f"pengu_list_push({self_ptr}, &{tmp_elem})"
                        return f"(__extension__({{ {elem_c} {tmp_elem} = ({arg0}); pengu_list_push({self_ptr}, &{tmp_elem}); }}))"
                    elif m_name == "pop":
                        return f"(*({elem_c}*)pengu_list_pop_val({self_ptr}))"
                    elif m_name == "len":
                        return f"({obj_expr_str}{self._member_sep(obj_type, obj_expr_str)}len)"
                    elif m_name == "is_empty":
                        return f"({obj_expr_str}{self._member_sep(obj_type, obj_expr_str)}len == 0)"
                    elif m_name == "clear":
                        return f"pengu_list_clear({self_ptr})"
                    elif m_name == "contains":
                        if not args:
                            return "false"
                        if not self.use_gnu_extensions:
                            return self._block_expr(
                                [f"{elem_c} {tmp_elem} = ({arg0});"],
                                f"pengu_list_contains({self_ptr}, &{tmp_elem})")
                        return f"(__extension__({{ {elem_c} {tmp_elem} = ({arg0}); pengu_list_contains({self_ptr}, &{tmp_elem}); }}))"
                    elif m_name == "index_of":
                        if not args:
                            return "-1"
                        if not self.use_gnu_extensions:
                            return self._block_expr(
                                [f"{elem_c} {tmp_elem} = ({arg0});"],
                                f"pengu_list_index_of({self_ptr}, &{tmp_elem})")
                        return f"(__extension__({{ {elem_c} {tmp_elem} = ({arg0}); pengu_list_index_of({self_ptr}, &{tmp_elem}); }}))"
                    elif m_name == "at":
                        idx_arg = args[0] if args else "0"
                        return f"(*({elem_c}*)pengu_list_at({self_ptr}, {idx_arg}))"

                # Built-in MapType methods
                if isinstance(actual_obj_type, MapType) or (isinstance(actual_obj_type, RefType) and isinstance(actual_obj_type.target, MapType)):
                    map_t = actual_obj_type.target if isinstance(actual_obj_type, RefType) else actual_obj_type
                    key_c = CTypeMapper.to_c_type(map_t.key)
                    val_c = CTypeMapper.to_c_type(map_t.value)
                    arg0 = args[0] if len(args) > 0 else ""
                    arg1 = args[1] if len(args) > 1 else ""
                    tmp_k = self.get_temp_name("_k")
                    tmp_v = self.get_temp_name("_v")
                    tmp_p = self.get_temp_name("_p")
                    if m_name in ("put", "insert", "set"):
                        if len(args) < 2:
                            return "0"
                        if not self.use_gnu_extensions:
                            self._hoist(f"{key_c} {tmp_k} = {arg0};")
                            self._hoist(f"{val_c} {tmp_v} = {arg1};")
                            return f"pengu_map_put({self_ptr}, &{tmp_k}, &{tmp_v})"
                        return f"(__extension__({{ {key_c} {tmp_k} = {arg0}; {val_c} {tmp_v} = {arg1}; pengu_map_put({self_ptr}, &{tmp_k}, &{tmp_v}); }}))"
                    elif m_name == "get":
                        val_cast = CTypeMapper.to_c_decl(map_t.value, "*")
                        val_zero = "NULL" if isinstance(map_t.value, (FnType, RefType)) else f"({val_c}){{0}}"
                        if not args:
                            return val_zero
                        if not self.use_gnu_extensions:
                            self._hoist(f"{key_c} {tmp_k} = {arg0};")
                            self._hoist(f"void* {tmp_p} = pengu_map_get({self_ptr}, &{tmp_k});")
                            return f"({tmp_p} ? (*(({val_cast}){tmp_p})) : {val_zero})"
                        return f"(__extension__({{ {key_c} {tmp_k} = {arg0}; void* {tmp_p} = pengu_map_get({self_ptr}, &{tmp_k}); {tmp_p} ? (*(({val_cast}){tmp_p})) : {val_zero}; }}))"
                    elif m_name == "remove":
                        if not args:
                            return "0"
                        if not self.use_gnu_extensions:
                            self._hoist(f"{key_c} {tmp_k} = {arg0};")
                            return f"pengu_map_remove({self_ptr}, &{tmp_k})"
                        return f"(__extension__({{ {key_c} {tmp_k} = {arg0}; pengu_map_remove({self_ptr}, &{tmp_k}); }}))"
                    elif m_name in ("contains", "contains_key", "has"):
                        if not args:
                            return "false"
                        if not self.use_gnu_extensions:
                            self._hoist(f"{key_c} {tmp_k} = {arg0};")
                            return f"pengu_map_contains({self_ptr}, &{tmp_k})"
                        return f"(__extension__({{ {key_c} {tmp_k} = {arg0}; pengu_map_contains({self_ptr}, &{tmp_k}); }}))"
                    elif m_name == "len":
                        return f"({obj_expr_str}{self._member_sep(obj_type, obj_expr_str)}len)"
                    elif m_name == "is_empty":
                        return f"({obj_expr_str}{self._member_sep(obj_type, obj_expr_str)}len == 0)"
                    elif m_name == "clear":
                        return f"pengu_map_clear({self_ptr})"

                t_name = None
                if isinstance(actual_obj_type, RefType):
                    t_name = getattr(actual_obj_type.target, "name", str(actual_obj_type.target))
                elif actual_obj_type is not None:
                    t_name = getattr(actual_obj_type, "name", str(actual_obj_type))

                base_tname = get_type_base_name(actual_obj_type)

                # Check if this is an enchanting method or concept binding method
                is_enchanting_method = False
                if t_name is not None:
                    if hasattr(self.symbols, "methods") and (t_name, m_name) in self.symbols.methods:
                        is_enchanting_method = True
                    elif hasattr(self.symbols, "monomorphized_methods") and f"{t_name}_{m_name}" in self.symbols.monomorphized_methods:
                        is_enchanting_method = True
                    elif (base_tname, m_name) in getattr(self.symbols, "generic_methods", {}):
                        is_enchanting_method = True
                    elif hasattr(self.symbols, "concept_bindings") and any((b_t == t_name or b_t == base_tname) and m_name in b_m for (b_t, _), b_m in self.symbols.concept_bindings.items()):
                        is_enchanting_method = True
                    elif hasattr(self.symbols, "functions") and f"{t_name.replace(' ', '_')}_{m_name}" in self.symbols.functions:
                        is_enchanting_method = True
                    elif any(w.get("enchanted_type") is not None and getattr(w["enchanted_type"], "name", str(w["enchanted_type"])) == t_name and w.get("name") == m_name for w in self.weaves):
                        is_enchanting_method = True

                if is_enchanting_method:
                    c_m = self._c_ident(m_name)
                    c_name = f"{t_name.replace(' ', '_')}_{c_m}"
                    rec_t = obj_type.target if isinstance(obj_type, RefType) else obj_type
                    rec_mangled = rec_t.get_mangled_name() if hasattr(rec_t, "get_mangled_name") else t_name.replace(' ', '_')
                    cand_mono = f"{rec_mangled}_{c_m}"
                    # Prefer the exact C name recorded when the method was
                    # collected: it carries the defining module's 'insignia'
                    # prefix (e.g. 'my_Player_heal'), which the logical type
                    # name alone cannot reconstruct.
                    defined_c_name = self._method_definition_c_name(t_name, m_name)
                    if defined_c_name:
                        c_name = defined_c_name
                    elif c_name in self.fn_info or any(w.get("c_name") == c_name for w in self.weaves):
                        pass
                    elif cand_mono in self.fn_info or any(w.get("c_name") == cand_mono for w in self.weaves):
                        c_name = cand_mono
                    elif hasattr(self.symbols, "monomorphized_methods") and cand_mono in self.symbols.monomorphized_methods:
                        c_name = cand_mono
                    elif (base_tname, m_name) in getattr(self.symbols, "generic_methods", {}):
                        entry = self.symbols.generic_methods[(base_tname, m_name)]
                        recv_p, m_p, method_ast = (entry[0], entry[1], entry[2]) if len(entry) == 3 else (entry[0], [], entry[1])
                        type_params = list(recv_p) + list(m_p)
                        t_args = getattr(rec_t, "type_args", [])
                        if t_args and len(t_args) == len(type_params):
                            subst_map = dict(zip(type_params, t_args))
                            self.symbols.monomorphized_methods[cand_mono] = (method_ast, subst_map, rec_t)
                            c_name = cand_mono
                    elif explicit_type_args:
                        m_suf = "_".join(t.get_mangled_name() for t in explicit_type_args)
                        for cand in (f"{c_name}_{m_suf}", f"{t_name.replace(' ', '_')}_{m_suf}_{c_m}", f"{rec_mangled}_{m_suf}_{c_m}"):
                            if (hasattr(self.symbols, "monomorphized_methods") and cand in self.symbols.monomorphized_methods) or cand in self.fn_info:
                                c_name = cand
                                break
                    if c_name not in self.fn_info and not any(w.get("c_name") == c_name for w in self.weaves):
                        plain_c = f"{t_name.replace(' ', '_')}_{m_name}"
                        if plain_c in self.fn_info or any(w.get("c_name") == plain_c for w in self.weaves):
                            c_name = plain_c
                        elif hasattr(self.symbols, "monomorphized_methods"):
                            matches = [m for m in self.symbols.monomorphized_methods if m.startswith(f"{cand_mono}_") or m.startswith(f"{c_name}_")]
                            if matches:
                                c_name = matches[0]
                    is_ritual = False
                    m_fn = self.symbols.methods.get((t_name, m_name)) if self.symbols else None
                    if m_fn and getattr(m_fn, "is_ritual", False):
                        is_ritual = True
                    if not is_ritual and hasattr(self.symbols, "concept_bindings"):
                        for (b_t, _), b_m in self.symbols.concept_bindings.items():
                            if (b_t == t_name or b_t == base_tname) and m_name in b_m:
                                if getattr(b_m[m_name], "is_ritual", False):
                                    is_ritual = True
                                    break
                    if not is_ritual and any(w.get("enchanted_type") is not None and getattr(w["enchanted_type"], "name", str(w["enchanted_type"])) == t_name and w.get("name") == m_name and w.get("is_ritual") for w in self.weaves):
                        is_ritual = True

                    if is_ritual:
                        fn_entry = self.fn_info.get(c_name) or self.fn_info.get(m_name)
                        if fn_entry and fn_entry.get("params"):
                            args = self._build_call_args(fn_entry["params"], raw_arg_nodes)
                        return f"{c_name}({', '.join(args)})"

                    if isinstance(obj_type, RefType) or obj_expr_str == "self":
                        self_arg = obj_expr_str
                    else:
                        self_arg = f"&{obj_expr_str}"
                    fn_entry = self.fn_info.get(c_name) or self.fn_info.get(m_name)
                    if fn_entry and fn_entry.get("params"):
                        fn_params = fn_entry["params"]
                        user_params = fn_params[1:] if (len(fn_params) > 0 and fn_params[0][0] in ("self", "restrict self")) else fn_params
                        all_args = [self_arg] + self._build_call_args(user_params, raw_arg_nodes)
                    else:
                        all_args = [self_arg] + args
                    return f"{c_name}({', '.join(all_args)})"
                else:
                    target_str = f"{obj_expr_str}->{m_name}" if isinstance(obj_type, RefType) else f"{obj_expr_str}.{m_name}"
                    return f"{target_str}({', '.join(args)})"

            # 2. With target method call: .method(...)
            elif target_node.data == "with_target":
                field_name = str(target_node.children[0])
                base_target = self.with_stack[-1] if self.with_stack else "self"

                base_type = self.current_enchanted_type if base_target == "self" else self._get_current_with_target_type()
                actual_with_type = base_type
                while isinstance(actual_with_type, (AliasType, FrozenType, SealType)):
                    actual_with_type = actual_with_type.target

                # Built-in ListType methods under with
                if isinstance(actual_with_type, ListType) or (isinstance(actual_with_type, RefType) and isinstance(actual_with_type.target, ListType)):
                    list_t = actual_with_type.target if isinstance(actual_with_type, RefType) else actual_with_type
                    self_ptr = base_target if (isinstance(actual_with_type, RefType) or base_target == "self") else f"&{base_target}"
                    elem_c = CTypeMapper.to_c_type(list_t.element)
                    arg0 = args[0] if args else ""
                    tmp_elem = self.get_temp_name("_elem")
                    if field_name in ("push", "append"):
                        if not args:
                            return "0"
                        return f"(__extension__({{ {elem_c} {tmp_elem} = ({arg0}); pengu_list_push({self_ptr}, &{tmp_elem}); }}))"
                    elif field_name == "pop":
                        return f"(*({elem_c}*)pengu_list_pop_val({self_ptr}))"
                    elif field_name == "len":
                        deref_obj = f"(*{self_ptr})" if (isinstance(actual_with_type, RefType) or base_target == "self") else base_target
                        return f"({deref_obj}.len)"
                    elif field_name == "is_empty":
                        deref_obj = f"(*{self_ptr})" if (isinstance(actual_with_type, RefType) or base_target == "self") else base_target
                        return f"({deref_obj}.len == 0)"
                    elif field_name == "clear":
                        return f"pengu_list_clear({self_ptr})"
                    elif field_name == "contains":
                        if not args:
                            return "false"
                        return f"(__extension__({{ {elem_c} {tmp_elem} = ({arg0}); pengu_list_contains({self_ptr}, &{tmp_elem}); }}))"
                    elif field_name == "index_of":
                        if not args:
                            return "-1"
                        return f"(__extension__({{ {elem_c} {tmp_elem} = ({arg0}); pengu_list_index_of({self_ptr}, &{tmp_elem}); }}))"
                    elif field_name == "at":
                        idx_arg = args[0] if args else "0"
                        return f"(*({elem_c}*)pengu_list_at({self_ptr}, {idx_arg}))"

                # Built-in MapType methods under with
                if isinstance(actual_with_type, MapType) or (isinstance(actual_with_type, RefType) and isinstance(actual_with_type.target, MapType)):
                    map_t = actual_with_type.target if isinstance(actual_with_type, RefType) else actual_with_type
                    self_ptr = base_target if (isinstance(actual_with_type, RefType) or base_target == "self") else f"&{base_target}"
                    key_c = CTypeMapper.to_c_type(map_t.key)
                    val_c = CTypeMapper.to_c_type(map_t.value)
                    arg0 = args[0] if len(args) > 0 else ""
                    arg1 = args[1] if len(args) > 1 else ""
                    tmp_k = self.get_temp_name("_k")
                    tmp_v = self.get_temp_name("_v")
                    tmp_p = self.get_temp_name("_p")
                    if field_name in ("put", "insert", "set"):
                        if len(args) < 2:
                            return "0"
                        if not self.use_gnu_extensions:
                            self._hoist(f"{key_c} {tmp_k} = {arg0};")
                            self._hoist(f"{val_c} {tmp_v} = {arg1};")
                            return f"pengu_map_put({self_ptr}, &{tmp_k}, &{tmp_v})"
                        return f"(__extension__({{ {key_c} {tmp_k} = {arg0}; {val_c} {tmp_v} = {arg1}; pengu_map_put({self_ptr}, &{tmp_k}, &{tmp_v}); }}))"
                    elif field_name == "get":
                        val_cast = CTypeMapper.to_c_decl(map_t.value, "*")
                        val_zero = "NULL" if isinstance(map_t.value, (FnType, RefType)) else f"({val_c}){{0}}"
                        if not args:
                            return val_zero
                        if not self.use_gnu_extensions:
                            self._hoist(f"{key_c} {tmp_k} = {arg0};")
                            self._hoist(f"void* {tmp_p} = pengu_map_get({self_ptr}, &{tmp_k});")
                            return f"({tmp_p} ? (*(({val_cast}){tmp_p})) : {val_zero})"
                        return f"(__extension__({{ {key_c} {tmp_k} = {arg0}; void* {tmp_p} = pengu_map_get({self_ptr}, &{tmp_k}); {tmp_p} ? (*(({val_cast}){tmp_p})) : {val_zero}; }}))"
                    elif field_name == "remove":
                        if not args:
                            return "0"
                        if not self.use_gnu_extensions:
                            self._hoist(f"{key_c} {tmp_k} = {arg0};")
                            return f"pengu_map_remove({self_ptr}, &{tmp_k})"
                        return f"(__extension__({{ {key_c} {tmp_k} = {arg0}; pengu_map_remove({self_ptr}, &{tmp_k}); }}))"
                    elif field_name in ("contains", "contains_key", "has"):
                        if not args:
                            return "false"
                        if not self.use_gnu_extensions:
                            self._hoist(f"{key_c} {tmp_k} = {arg0};")
                            return f"pengu_map_contains({self_ptr}, &{tmp_k})"
                        return f"(__extension__({{ {key_c} {tmp_k} = {arg0}; pengu_map_contains({self_ptr}, &{tmp_k}); }}))"
                    elif field_name == "len":
                        deref_obj = f"(*{self_ptr})" if (isinstance(actual_with_type, RefType) or base_target == "self") else base_target
                        return f"({deref_obj}.len)"
                    elif field_name == "is_empty":
                        deref_obj = f"(*{self_ptr})" if (isinstance(actual_with_type, RefType) or base_target == "self") else base_target
                        return f"({deref_obj}.len == 0)"
                    elif field_name == "clear":
                        return f"pengu_map_clear({self_ptr})"

                is_enchanting_method = False
                t_name = None
                self_arg = None

                if base_target == "self":
                    if self.current_enchanted_type is not None:
                        t_name = getattr(self.current_enchanted_type, "name", str(self.current_enchanted_type))
                        self_arg = "self"
                else:
                    base_type = self._get_current_with_target_type()
                    if isinstance(base_type, RefType):
                        t_name = getattr(base_type.target, "name", str(base_type.target))
                        self_arg = base_target
                    elif base_type is not None:
                        t_name = getattr(base_type, "name", str(base_type))
                        self_arg = f"&{base_target}"

                if t_name is not None:
                    if hasattr(self.symbols, "methods") and (t_name, field_name) in self.symbols.methods:
                        is_enchanting_method = True
                    elif any(w.get("enchanted_type") is not None and getattr(w["enchanted_type"], "name", str(w["enchanted_type"])) == t_name and w.get("name") == field_name for w in self.weaves):
                        is_enchanting_method = True

                if is_enchanting_method:
                    c_fn = self._c_ident(field_name)
                    c_name = f"{t_name.replace(' ', '_')}_{c_fn}"
                    if c_name not in self.fn_info and not any(w.get("c_name") == c_name for w in self.weaves):
                        plain_c = f"{t_name.replace(' ', '_')}_{field_name}"
                        if plain_c in self.fn_info or any(w.get("c_name") == plain_c for w in self.weaves):
                            c_name = plain_c
                    fn_entry = self.fn_info.get(c_name) or self.fn_info.get(field_name)
                    if fn_entry and fn_entry.get("params"):
                        fn_params = fn_entry["params"]
                        user_params = fn_params[1:] if (len(fn_params) > 0 and fn_params[0][0] in ("self", "restrict self")) else fn_params
                        all_args = [self_arg] + self._build_call_args(user_params, raw_arg_nodes)
                    else:
                        all_args = [self_arg] + args
                    return f"{c_name}({', '.join(all_args)})"

                target_str = f"{base_target}.{field_name}"
                return f"{target_str}({', '.join(args)})"

            # 3. Simple function or method inside with block
            elif target_node.data == "normal_target":
                target_str = str(target_node.children[0])

                if target_str == "print":
                    if args:
                        arg_expr = args_node.children[0] if args_node and args_node.children else None
                        if isinstance(arg_expr, Tree) and arg_expr.data in ("pos_arg", "named_arg"):
                            arg_expr = arg_expr.children[-1]
                        inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                        for lv_k, lv_v in self.local_vars.items():
                            inferrer.symbols.define(Symbol(name=lv_k, type=lv_v, kind="var"))
                        arg_t = None
                        if arg_expr is not None:
                            try:
                                arg_t = inferrer.infer(arg_expr)
                            except Exception:
                                pass
                        if arg_t is None:
                            arg_t = self._lookup_var_type(args[0])

                        if isinstance(arg_t, BaseType):
                            if arg_t.name == "char":
                                return f'printf("%c\\n", (char)({args[0]}))'
                            elif arg_t.name in ("u64", "uint64", "uint64_t", "ulong"):
                                return f'printf("%llu\\n", (unsigned long long)({args[0]}))'
                            elif arg_t.name in ("i64", "int64", "int64_t", "long"):
                                return f'printf("%lld\\n", (long long)({args[0]}))'
                            elif arg_t.name in ("u32", "uint32", "uint32_t", "uint", "u16", "uint16", "uint16_t", "byte", "u8", "uint8", "uint8_t", "usize", "size_t"):
                                return f'printf("%u\\n", (uint32_t)({args[0]}))'
                            elif arg_t.name in ("int", "i32", "i16", "int16", "i8", "int8", "isize"):
                                return f'printf("%d\\n", (int32_t)({args[0]}))'
                            elif arg_t.name in ("float", "f32", "f64", "double"):
                                # Phase 3 item 3.9: `%g` so `print x`, `"{x}"` and
                                # `x to string` all agree. This used to be `%f`
                                # ("3.140000") while `to string` gave "3.14".
                                return f'printf("%g\\n", (double)({args[0]}))'
                            elif arg_t.name in ("bool",):
                                return f'printf("%s\\n", ({args[0]}) ? "true" : "false")'
                            elif arg_t.name in ("string",):
                                return f'printf("%s\\n", ({args[0]}).data)'
                        elif isinstance(arg_t, RefType):
                            if isinstance(arg_t.target, BaseType) and arg_t.target.name == "char":
                                return f'printf("%s\\n", (const char*)({args[0]}))'
                            return f'printf("%p\\n", (void*)({args[0]}))'

                        lv_t = self.local_vars.get(args[0])
                        if lv_t and isinstance(lv_t, BaseType):
                            if lv_t.name == "char":
                                return f'printf("%c\\n", (char)({args[0]}))'
                            elif lv_t.name in ("int", "i32", "i16", "i8"):
                                return f'printf("%d\\n", (int32_t)({args[0]}))'
                            elif lv_t.name in ("u32", "u16", "u8", "byte"):
                                return f'printf("%u\\n", (uint32_t)({args[0]}))'

                        return f'printf("%s\\n", {args[0]}.data)'
                    return 'printf("\\n")'

                if self.with_stack:
                    base_target = self.with_stack[-1]
                    base_type = self._get_current_with_target_type()
                    t_name = None
                    self_arg = None
                    if base_target == "self":
                        if self.current_enchanted_type is not None:
                            t_name = getattr(self.current_enchanted_type, "name", str(self.current_enchanted_type))
                            self_arg = "self"
                    elif base_type is not None:
                        if isinstance(base_type, RefType):
                            t_name = getattr(base_type.target, "name", str(base_type.target))
                            self_arg = base_target
                        else:
                            t_name = getattr(base_type, "name", str(base_type))
                            self_arg = f"&{base_target}"

                    if t_name is not None:
                        if (hasattr(self.symbols, "methods") and (t_name, target_str) in self.symbols.methods) or any(w.get("enchanted_type") is not None and getattr(w["enchanted_type"], "name", str(w["enchanted_type"])) == t_name and w.get("name") == target_str for w in self.weaves):
                            c_name = f"{t_name.replace(' ', '_')}_{target_str}"
                            fn_entry = self.fn_info.get(c_name) or self.fn_info.get(target_str)
                            if fn_entry and fn_entry.get("params"):
                                fn_params = fn_entry["params"]
                                user_params = fn_params[1:] if (len(fn_params) > 0 and fn_params[0][0] in ("self", "restrict self")) else fn_params
                                all_args = [self_arg] + self._build_call_args(user_params, raw_arg_nodes)
                            else:
                                all_args = [self_arg] + args
                            return f"{c_name}({', '.join(all_args)})"

                if (self.symbols and target_str in self.symbols.generic_functions) or (target_str not in self.fn_info and self.symbols):
                    if explicit_type_args:
                        mangled = f"{target_str}_" + "_".join(t.get_mangled_name() for t in explicit_type_args)
                        if mangled in self.symbols.monomorphized_functions:
                            target_str = mangled
                        else:
                            m_suf = "_".join(t.get_mangled_name() for t in explicit_type_args)
                            cands = [m for m in self.symbols.monomorphized_functions if m == f"{target_str}_{m_suf}" or m.endswith(f"_{target_str}_{m_suf}")]
                            if len(cands) == 1:
                                target_str = cands[0]
                            elif len(cands) > 1 and self.current_source_file:
                                cur_stem = os.path.splitext(os.path.basename(self.current_source_file))[0]
                                cur_matches = [m for m in cands if m.startswith(f"{cur_stem}_")]
                                target_str = cur_matches[0] if len(cur_matches) == 1 else cands[0]
                            else:
                                matches = [m for m, entry in self.symbols.monomorphized_functions.items()
                                           if m.startswith(f"{target_str}_") and (get_generic_ast_name(entry[0]) == target_str or m.startswith(f"{target_str}__"))]
                                if len(matches) == 1:
                                    target_str = matches[0]
                    else:
                        matches = [m for m, entry in self.symbols.monomorphized_functions.items()
                                   if (m.startswith(f"{target_str}_") or f"_{target_str}_" in m) and (get_generic_ast_name(entry[0]) == target_str or m.startswith(f"{target_str}__"))]
                        if len(matches) == 1:
                            target_str = matches[0]
                        elif len(matches) > 1:
                            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                            for lv_k, lv_v in self.local_vars.items():
                                inferrer.symbols.define(Symbol(name=lv_k, type=lv_v, kind="var"))
                            arg_types = []
                            if args_node is not None:
                                for c in args_node.children:
                                    val = c.children[1] if c.data == "named_arg" else c.children[0]
                                    arg_types.append(inferrer.infer(val))
                            resolved = None
                            # The instance name is mangled from the *type
                            # parameters* (sum_int / sum_float), not from the
                            # argument types, so unify the declared parameter
                            # types against the arguments to recover them.
                            decl_fn = self.symbols.functions.get(target_str)
                            type_params = list(getattr(decl_fn, "type_params", None) or [])
                            if decl_fn and type_params:
                                subst: Dict[str, Type] = {}
                                for (_, p_type), arg_t in zip(decl_fn.params, arg_types):
                                    inferrer._unify_type(p_type, arg_t, subst)
                                if all(tp in subst for tp in type_params):
                                    cand = f"{target_str}_" + "_".join(
                                        subst[tp].get_mangled_name() for tp in type_params)
                                    if cand in self.symbols.monomorphized_functions:
                                        resolved = cand
                                    else:
                                        c_matches = [m for m in self.symbols.monomorphized_functions if m.endswith(f"_{cand}")]
                                        if len(c_matches) == 1:
                                            resolved = c_matches[0]
                            if resolved is None:
                                mangled = f"{target_str}_" + "_".join(
                                    t.get_mangled_name() for t in arg_types)
                                if mangled in self.symbols.monomorphized_functions:
                                    resolved = mangled
                                else:
                                    c_matches = [m for m in self.symbols.monomorphized_functions if m.endswith(f"_{mangled}")]
                                    if len(c_matches) == 1:
                                        resolved = c_matches[0]
                            if resolved:
                                target_str = resolved
                            elif len(matches) == 1:
                                target_str = matches[0]
                            elif len(matches) > 1 and self.current_source_file:
                                cur_stem = os.path.splitext(os.path.basename(self.current_source_file))[0]
                                cur_matches = [m for m in matches if m.startswith(f"{cur_stem}_")]
                                if len(cur_matches) == 1:
                                    target_str = cur_matches[0]

                fn_entry = None
                if self.current_source_file:
                    norm_cur = os.path.abspath(self.current_source_file)
                    for w in self.weaves:
                        if w.get("enchanted_type") is None and w.get("name") == target_str and w.get("filepath") and os.path.abspath(w["filepath"]) == norm_cur:
                            w_cname = w.get("c_name")
                            fn_entry = self.fn_info.get(w_cname) or {"c_name": w_cname, "params": w.get("params", [])}
                            break
                if not fn_entry:
                    fn_entry = self.fn_info.get(target_str)
                if fn_entry and fn_entry.get("params"):
                    args = self._build_call_args(fn_entry["params"], raw_arg_nodes)
                elif fn_entry:
                    fn_params = fn_entry["params"]
                    if len(args) < len(fn_params):
                        for p in fn_params[len(args):]:
                            if len(p) >= 3 and p[2] is not None:
                                args.append(self._translate_expr(p[2]))
                c_name = fn_entry["c_name"] if fn_entry else target_str
                return f"{c_name}({', '.join(args)})"

            return f"{str(target_node)}({', '.join(args)})"

        # 5. Member and index access
        elif rule == "field_access":
            target_node = node.children[0]
            raw_field = str(node.children[1])
            field_name = self._c_ident(raw_field)
            if isinstance(target_node, Tree) and target_node.data == "var_ref":
                var_name = str(target_node.children[0])
                sym = self.symbols.lookup(var_name) if self.symbols else None
                if sym and sym.kind == "import":
                    if sym.module_scope:
                        mod_field_sym = sym.module_scope.lookup(raw_field)
                        if not mod_field_sym:
                            mod_field_sym = sym.module_scope.lookup(f"{var_name}_{raw_field}")
                        if not mod_field_sym:
                            for s in sym.module_scope.symbols.values():
                                if getattr(s, "kind", "") == "omen_variant" and s.name.endswith(f"_{raw_field}"):
                                    mod_field_sym = s
                                    break
                        if mod_field_sym:
                            m_sym_t = getattr(mod_field_sym, "type", None)
                            if getattr(mod_field_sym, "kind", "") == "omen_variant" and isinstance(m_sym_t, OmenType):
                                o_logical = getattr(m_sym_t, "name", None) or var_name
                                return self._get_omen_variant_c_name(o_logical, raw_field)
                            if getattr(mod_field_sym, "kind", "") == "const":
                                fp = getattr(mod_field_sym, "file_path", "")
                                if fp and fp.endswith(".d.pengu"):
                                    c_val = getattr(mod_field_sym, "const_val", None)
                                    if c_val is not None and isinstance(m_sym_t, (RuneType, EchoType)):
                                        return self._format_const_val(c_val)
                                    if hasattr(mod_field_sym, "get_c_name") and mod_field_sym.get_c_name():
                                        return mod_field_sym.get_c_name()
                                    return raw_field
                            if getattr(mod_field_sym, "kind", "") in ("weave", "declare", "function"):
                                mod_prefix = getattr(sym, "c_name", None) or var_name
                                for cand in (f"{mod_prefix}_{raw_field}", f"{var_name}_{raw_field}"):
                                    if cand in self.fn_info and self.fn_info[cand].get("c_name"):
                                        return self.fn_info[cand]["c_name"]
                                if hasattr(mod_field_sym, "get_c_name") and mod_field_sym.get_c_name() != raw_field:
                                    return mod_field_sym.get_c_name()
                                return f"{var_name}_{raw_field}"
                            if hasattr(mod_field_sym, "get_c_name"):
                                return mod_field_sym.get_c_name()
                    mod_const_key = f"{var_name}_{raw_field}"
                    if mod_const_key in self.declaration_consts and mod_const_key in self.consts:
                        c_type, val = self.consts[mod_const_key]
                        if val is not None and isinstance(c_type, (RuneType, EchoType)):
                            return self._format_const_val(val)
                        return mod_const_key
                    if raw_field in self.declaration_consts and raw_field in self.consts:
                        c_type, val = self.consts[raw_field]
                        if val is not None and isinstance(c_type, (RuneType, EchoType)):
                            return self._format_const_val(val)
                        return raw_field
                    for o_name, o_vars in self.omens.items():
                        if raw_field in o_vars and (o_name in self.declaration_types or o_name.startswith(f"{var_name}_")):
                            return self._get_omen_variant_c_name(o_name, raw_field)
                    return f"{var_name}_{raw_field}"
                omen_t = sym.type if (sym and isinstance(sym.type, OmenType)) else None
                o_c_name = getattr(omen_t, "c_name", None) or var_name
                if (omen_t and raw_field in omen_t.variants) or (var_name in self.omens and raw_field in self.omens[var_name]) or (o_c_name in self.omens and raw_field in self.omens[o_c_name]):
                    omen_key = o_c_name if o_c_name in self.omens else var_name
                    var_sym = self.symbols.lookup(f"{var_name}_{raw_field}") if self.symbols else None
                    if var_sym and getattr(var_sym, "c_name", None):
                        return var_sym.c_name
                    if omen_key in self.omens and raw_field in self.omens[omen_key]:
                        return self._get_omen_variant_c_name(omen_key, raw_field)
                    return f"{omen_key}_{raw_field}"
            base = self._translate_expr(target_node)
            if base in self.omens and raw_field in self.omens[base]:
                return self._get_omen_variant_c_name(base, raw_field)
            for o_name, o_vars in self.omens.items():
                if raw_field in o_vars and (o_name == base or o_name.endswith(f"_{base}") or o_name.endswith(base)):
                    return self._get_omen_variant_c_name(o_name, raw_field)
            sym = self._lookup_symbol(base)
            if base in self.local_vars and self.local_vars[base] is not None:
                var_t = self.local_vars[base]
            elif base.startswith("_") and base[1:] in self.local_vars and self.local_vars[base[1:]] is not None:
                var_t = self.local_vars[base[1:]]
            else:
                var_t = sym.type if sym else self._lookup_var_type(base)
            if var_t is None:
                var_t = self._infer_node_type(target_node)
            is_ref = isinstance(var_t, RefType)
            inner_t = var_t.target if is_ref else var_t
            # A non-identifier base ('(essence of self)', a cast, a call...) has
            # no symbol to look up, so fall back to the checker's inferred type.
            if not isinstance(inner_t, (MaybeType, ResultType)):
                _inf = self._infer_node_type(target_node)
                _inf = _inf.target if isinstance(_inf, RefType) else _inf
                if isinstance(_inf, (MaybeType, ResultType)):
                    inner_t = _inf
            # Inside a monomorphized generic weave the container still spells its
            # element with the type parameter: substitute it or the unwrapping
            # cast is emitted as the erased 'void*' ('int32_t v = m.value').
            _subst = getattr(self, "current_subst_map", None) or {}
            if _subst and isinstance(inner_t, (MaybeType, ResultType)):
                try:
                    inner_t = inner_t.substitute(_subst)
                except Exception:
                    pass
            sep = "->" if (base == "self" or is_ref) else "."

            alias_c = self._container_field_c_name(inner_t, raw_field)
            if alias_c is not None:
                return f"{base}{sep}{alias_c}"

            if isinstance(inner_t, MaybeType) and raw_field == "value":
                elem_cast = CTypeMapper.to_c_decl(inner_t.element, "*")
                return f"(*({elem_cast}){base}{sep}value)"
            if isinstance(inner_t, ResultType) and raw_field == "value":
                elem_cast = CTypeMapper.to_c_decl(inner_t.ok_type, "*")
                return f"(*({elem_cast}){base}{sep}ok_val)"
            if isinstance(inner_t, ResultType) and raw_field in ("error", "err"):
                elem_cast = CTypeMapper.to_c_decl(inner_t.err_type, "*")
                return f"(*({elem_cast}){base}{sep}err_val)"
            eff_t = var_t if var_t is not None else (sym.type if sym else None)
            return f"{base}{sep}{field_name}"
        elif rule == "arrow_access":
            target_node = node.children[0]
            raw_field = str(node.children[1])
            field_name = self._c_ident(raw_field)
            base = self._translate_expr(target_node)
            target_t = self._infer_node_type(target_node)
            inner_t = target_t.target if isinstance(target_t, RefType) else target_t
            if isinstance(inner_t, MaybeType) and raw_field == "value":
                elem_cast = CTypeMapper.to_c_decl(inner_t.element, "*")
                return f"(*({elem_cast}){base}->value)"
            if isinstance(inner_t, ResultType) and raw_field == "value":
                elem_cast = CTypeMapper.to_c_decl(inner_t.ok_type, "*")
                return f"(*({elem_cast}){base}->ok_val)"
            if isinstance(inner_t, ResultType) and raw_field in ("error", "err"):
                elem_cast = CTypeMapper.to_c_decl(inner_t.err_type, "*")
                return f"(*({elem_cast}){base}->err_val)"
            return f"{base}->{field_name}"
        elif rule == "slice_at_expr":
            return self._emit_slice_at(node)
        elif rule == "for_comp":
            var_name = str(node.children[0])
            iter_node = node.children[1]
            has_cond = (len(node.children) == 4)
            cond_node = node.children[2] if has_cond else None
            then_node = node.children[3] if has_cond else node.children[2]

            iter_c = self._translate_expr(iter_node)

            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
            for lv_k, lv_v in self.local_vars.items():
                inferrer.symbols.define(Symbol(name=lv_k, type=lv_v, kind="var"))

            iter_t = None
            try:
                iter_t = inferrer.infer(iter_node)
            except Exception:
                pass

            iter_elem_t = iter_t.element_type() if iter_t and hasattr(iter_t, "element_type") and iter_t.element_type() else INT_TYPE
            if isinstance(iter_t, BaseType) and iter_t.name == "string":
                # Characters of a string become single-character strings.
                iter_elem_t = STRING_TYPE
            iter_elem_c = CTypeMapper.to_c_type(iter_elem_t)

            c_var_name = self._c_ident(var_name)
            decl_var = CTypeMapper.to_c_decl(iter_elem_t, c_var_name)

            _MISSING = object()
            prev = self.local_vars.get(var_name, _MISSING)
            prev_c = self.local_vars.get(c_var_name, _MISSING)
            self.local_vars[var_name] = iter_elem_t
            self.local_vars[c_var_name] = iter_elem_t
            inferrer.symbols.define(Symbol(name=var_name, type=iter_elem_t, kind="var"))

            try:
                then_t = None
                try:
                    then_t = inferrer.infer(then_node)
                except Exception:
                    pass
                then_elem_c = CTypeMapper.to_c_type(then_t) if then_t else "int32_t"

                cond_c = self._translate_expr(cond_node) if cond_node else None
                then_c = self._translate_expr(then_node)
            finally:
                if prev is _MISSING:
                    self.local_vars.pop(var_name, None)
                else:
                    self.local_vars[var_name] = prev
                if prev_c is _MISSING:
                    self.local_vars.pop(c_var_name, None)
                else:
                    self.local_vars[c_var_name] = prev_c

            def _comp_list_new(sz: str) -> str:
                return f"pengu_list_new(sizeof({then_elem_c}), {sz})"

            ind = self.indent()
            lit_decl = ""
            if isinstance(iter_t, BaseType) and iter_t.name == "string":
                # Iterating a string yields each character as a fresh
                # single-character PenguString (pengu_string_char_at allocates),
                # exactly like the 'for-in' statement.
                if not (isinstance(iter_node, Tree) and iter_node.data in (
                        "var_ref", "field_access", "arrow_access", "at_expr",
                        "array_at_expr", "essence_of", "self_arrow", "self_ref",
                        "string_lit")):
                    iter_tmp = self.get_temp_name("_iter")
                    lit_decl = f"{ind}  PenguString {iter_tmp} = {iter_c};\n"
                    iter_c = iter_tmp
                tmp_list = self.get_temp_name("_comp_list")
                tmp_val = self.get_temp_name("_comp_val")
                decl_char = self.get_temp_name("_ch")
                decl_val = CTypeMapper.to_c_decl(then_t, tmp_val) if then_t else f"{then_elem_c} {tmp_val}"
                cond_check = f"if ({cond_c}) " if cond_c else ""
                if not self.use_gnu_extensions:
                    stmts = []
                    if lit_decl:
                        stmts.append(lit_decl.strip())
                    stmts.append(f"PenguList {tmp_list} = {_comp_list_new(f'({iter_c}).len')};")
                    stmts.append(f"for (int32_t _i = 0; _i < ({iter_c}).len; _i++) {{")
                    stmts.append(f"  PenguString {decl_char} = pengu_string_char_at({iter_c}, _i);")
                    stmts.append(f"  {decl_var} = {decl_char};")
                    stmts.append(f"  {cond_check}{{")
                    stmts.append(f"    {decl_val} = {then_c};")
                    stmts.append(f"    pengu_list_push(&{tmp_list}, &{tmp_val});")
                    stmts.append("  }")
                    stmts.append("}")
                    return self._block_expr(stmts, tmp_list)
                return (
                    f"(__extension__({{\n"
                    f"{lit_decl}"
                    f"{ind}  PenguList {tmp_list} = {_comp_list_new(f'({iter_c}).len')};\n"
                    f"{ind}  for (int32_t _i = 0; _i < ({iter_c}).len; _i++) {{\n"
                    f"{ind}    PenguString {decl_char} = pengu_string_char_at({iter_c}, _i);\n"
                    f"{ind}    {decl_var} = {decl_char};\n"
                    f"{ind}    {cond_check}{{\n"
                    f"{ind}      {decl_val} = {then_c};\n"
                    f"{ind}      pengu_list_push(&{tmp_list}, &{tmp_val});\n"
                    f"{ind}    }}\n"
                    f"{ind}  }}\n"
                    f"{ind}  {tmp_list};\n"
                    f"{ind}}}))"
                )
            if isinstance(iter_t, ArrayType) and iter_t.size is not None:
                count_c = str(iter_t.size)
                if isinstance(iter_node, Tree) and iter_node.data == "array_lit" and iter_node.children:
                    lit_tmp = self.get_temp_name("_lit")
                    elems = ", ".join(self._translate_expr(c) for c in iter_node.children)
                    lit_type_decl = CTypeMapper.to_c_decl(iter_elem_t, f"{lit_tmp}[]")
                    lit_decl = f"{ind}  {lit_type_decl} = {{ {elems} }};\n"
                    elem_access = f"{lit_tmp}[_i]"
                else:
                    elem_access = f"({iter_c})[_i]"
            elif isinstance(iter_t, (SliceType, ManyType, ListType)):
                # A non-lvalue iterable ('for x in (calling make) then …') has no
                # addressable storage: bind it to a temporary first, exactly like
                # the 'for-in' statement does (otherwise '&(f())' is invalid C).
                if (isinstance(iter_node, Tree) and iter_node.data not in (
                        "var_ref", "field_access", "arrow_access", "at_expr",
                        "array_at_expr", "essence_of", "self_arrow", "self_ref",
                        "array_lit", "list_lit")):
                    iter_tmp = self.get_temp_name("_iter")
                    lit_decl = f"{ind}  {CTypeMapper.to_c_decl(iter_t, iter_tmp)} = {iter_c};\n"
                    iter_c = iter_tmp
                count_c = f"({iter_c}).len"
                iter_elem_cast = CTypeMapper.to_c_decl(iter_elem_t, "*")
                if isinstance(iter_t, (SliceType, ManyType)):
                    elem_access = f"((({iter_elem_cast})({iter_c}).data)[_i])"
                else:
                    elem_access = f"(*({iter_elem_cast})pengu_list_at(&({iter_c}), _i))"
            elif isinstance(iter_t, MapType):
                tmp_list = self.get_temp_name("_comp_list")
                tmp_val = self.get_temp_name("_comp_val")
                slot_var = self.get_temp_name("_slot")
                idx_var = self.get_temp_name("_i")
                cond_check = f"if ({cond_c}) " if cond_c else ""
                iter_elem_cast = CTypeMapper.to_c_decl(iter_elem_t, "*")
                decl_val = CTypeMapper.to_c_decl(then_t, tmp_val) if then_t else f"{then_elem_c} {tmp_val}"
                if not self.use_gnu_extensions:
                    return self._block_expr([
                        f"PenguList {tmp_list} = {_comp_list_new(f'({iter_c}).len')};",
                        f"for (int32_t {slot_var} = 0, {idx_var} = 0; {idx_var} < ({iter_c}).len && {slot_var} < ({iter_c}).cap; {slot_var}++) {{",
                        f"  if (!({iter_c}).entries || !({iter_c}).entries[{slot_var}].occupied) continue;",
                        f"  {decl_var} = *(({iter_elem_cast})({iter_c}).entries[{slot_var}].key);",
                        f"  {cond_check}{{",
                        f"    {decl_val} = {then_c};",
                        f"    pengu_list_push(&{tmp_list}, &{tmp_val});",
                        "  }",
                        f"  {idx_var}++;",
                        "}",
                    ], tmp_list)
                return (
                    f"(__extension__({{\n"
                    f"{ind}  PenguList {tmp_list} = {_comp_list_new(f'({iter_c}).len')};\n"
                    f"{ind}  for (int32_t {slot_var} = 0, {idx_var} = 0; {idx_var} < ({iter_c}).len && {slot_var} < ({iter_c}).cap; {slot_var}++) {{\n"
                    f"{ind}    if (!({iter_c}).entries || !({iter_c}).entries[{slot_var}].occupied) continue;\n"
                    f"{ind}    {decl_var} = *(({iter_elem_cast})({iter_c}).entries[{slot_var}].key);\n"
                    f"{ind}    {cond_check}{{\n"
                    f"{ind}      {decl_val} = {then_c};\n"
                    f"{ind}      pengu_list_push(&{tmp_list}, &{tmp_val});\n"
                    f"{ind}    }}\n"
                    f"{ind}    {idx_var}++;\n"
                    f"{ind}  }}\n"
                    f"{ind}  {tmp_list};\n"
                    f"{ind}}}))"
                )
            elif isinstance(iter_t, RangeType) or (
                isinstance(iter_node, Tree) and iter_node.data in ("to_expr", "range_dotdot")
            ):
                if isinstance(iter_node, Tree) and iter_node.data in ("to_expr", "range_dotdot"):
                    start_s = self._translate_expr(iter_node.children[0])
                    end_s = self._translate_expr(iter_node.children[-1])
                    init_range = ""
                    loop_head = f"for (int64_t {c_var_name} = {start_s}; {c_var_name} < {end_s}; {c_var_name}++)"
                    count_hint = f"(({end_s}) > ({start_s}) ? ({end_s}) - ({start_s}) : 0)"
                else:
                    rng_tmp = self.get_temp_name("_rng")
                    init_range = f"{ind}  PenguRange {rng_tmp} = {iter_c};\n"
                    loop_head = f"for (int64_t {c_var_name} = {rng_tmp}.start; {c_var_name} < {rng_tmp}.end; {c_var_name}++)"
                    count_hint = f"({rng_tmp}.end > {rng_tmp}.start ? {rng_tmp}.end - {rng_tmp}.start : 0)"

                tmp_list = self.get_temp_name("_comp_list")
                tmp_val = self.get_temp_name("_comp_val")
                decl_val = CTypeMapper.to_c_decl(then_t, tmp_val) if then_t else f"{then_elem_c} {tmp_val}"
                alloc_sz = "8" if cond_c else count_hint
                if cond_c:
                    if not self.use_gnu_extensions:
                        stmts = []
                        if init_range:
                            stmts.append(init_range.strip())
                        stmts += [
                            f"PenguList {tmp_list} = {_comp_list_new(alloc_sz)};",
                            f"{loop_head} {{",
                            f"  if ({cond_c}) {{",
                            f"    {decl_val} = {then_c};",
                            f"    pengu_list_push(&{tmp_list}, &{tmp_val});",
                            "  }",
                            "}",
                        ]
                        return self._block_expr(stmts, tmp_list)
                    return (
                        f"(__extension__({{\n"
                        f"{init_range}"
                        f"{ind}  PenguList {tmp_list} = {_comp_list_new(alloc_sz)};\n"
                        f"{ind}  {loop_head} {{\n"
                        f"{ind}    if ({cond_c}) {{\n"
                        f"{ind}      {decl_val} = {then_c};\n"
                        f"{ind}      pengu_list_push(&{tmp_list}, &{tmp_val});\n"
                        f"{ind}    }}\n"
                        f"{ind}  }}\n"
                        f"{ind}  {tmp_list};\n"
                        f"{ind}}}))"
                    )
                else:
                    if not self.use_gnu_extensions:
                        stmts = []
                        if init_range:
                            stmts.append(init_range.strip())
                        stmts += [
                            f"PenguList {tmp_list} = {_comp_list_new(alloc_sz)};",
                            f"{loop_head} {{",
                            f"  {decl_val} = {then_c};",
                            f"  pengu_list_push(&{tmp_list}, &{tmp_val});",
                            "}",
                        ]
                        return self._block_expr(stmts, tmp_list)
                    return (
                        f"(__extension__({{\n"
                        f"{init_range}"
                        f"{ind}  PenguList {tmp_list} = {_comp_list_new(alloc_sz)};\n"
                        f"{ind}  {loop_head} {{\n"
                        f"{ind}    {decl_val} = {then_c};\n"
                        f"{ind}    pengu_list_push(&{tmp_list}, &{tmp_val});\n"
                        f"{ind}  }}\n"
                        f"{ind}  {tmp_list};\n"
                        f"{ind}}}))"
                    )
            else:
                raise SemanticError(
                    f"Cannot iterate over non-collection type '{iter_t}' at codegen time",
                    code="E0005",
                    help="The checker should have caught this; if you see this error, it is a compiler bug.",
                )

            tmp_list = self.get_temp_name("_comp_list")
            tmp_val = self.get_temp_name("_comp_val")
            decl_val = CTypeMapper.to_c_decl(then_t, tmp_val) if then_t else f"{then_elem_c} {tmp_val}"
            if not self.use_gnu_extensions:
                stmts = []
                if lit_decl:
                    stmts.append(lit_decl.strip())
                stmts.append(f"PenguList {tmp_list} = {_comp_list_new('8' if cond_c else count_c)};")
                stmts.append(f"for (int _i = 0; _i < {count_c}; _i++) {{")
                stmts.append(f"  {decl_var} = {elem_access};")
                if cond_c:
                    stmts.append(f"  if ({cond_c}) {{")
                stmts.append(f"    {decl_val} = {then_c};")
                stmts.append(f"    pengu_list_push(&{tmp_list}, &{tmp_val});")
                if cond_c:
                    stmts.append("  }")
                stmts.append("}")
                return self._block_expr(stmts, tmp_list)
            if cond_c:
                return (
                    f"(__extension__({{\n"
                    f"{ind}  PenguList {tmp_list} = {_comp_list_new('8')};\n"
                    f"{lit_decl}"
                    f"{ind}  for (int _i = 0; _i < {count_c}; _i++) {{\n"
                    f"{ind}    {decl_var} = {elem_access};\n"
                    f"{ind}    if ({cond_c}) {{\n"
                    f"{ind}      {decl_val} = {then_c};\n"
                    f"{ind}      pengu_list_push(&{tmp_list}, &{tmp_val});\n"
                    f"{ind}    }}\n"
                    f"{ind}  }}\n"
                    f"{ind}  {tmp_list};\n"
                    f"{ind}}}))"
                )
            else:
                return (
                    f"(__extension__({{\n"
                    f"{lit_decl}"
                    f"{ind}  PenguList {tmp_list} = {_comp_list_new(count_c)};\n"
                    f"{ind}  for (int _i = 0; _i < {count_c}; _i++) {{\n"
                    f"{ind}    {decl_var} = {elem_access};\n"
                    f"{ind}    {decl_val} = {then_c};\n"
                    f"{ind}    pengu_list_push(&{tmp_list}, &{tmp_val});\n"
                    f"{ind}  }}\n"
                    f"{ind}  {tmp_list};\n"
                    f"{ind}}}))"
                )
        elif rule == "at_expr":
            parts = flatten_at_chain(node)
            base = self._translate_expr(parts[0])
            var_t = self._lookup_var_type(base) if isinstance(parts[0], Tree) and parts[0].data == "var_ref" else None
            if var_t is None and isinstance(parts[0], Tree):
                t_node = parts[0]
                if t_node.data == "arrow_access":
                    t_field = str(t_node.children[1])
                    if self.current_enchanted_type is not None:
                        t_name = getattr(self.current_enchanted_type, "name", str(self.current_enchanted_type))
                        var_t = self.runes.get(t_name, {}).get(t_field)
                elif t_node.data == "field_access":
                    t_base = str(t_node.children[0])
                    t_field = str(t_node.children[1])
                    b_type = self._lookup_var_type(t_base)
                    if b_type and hasattr(b_type, "name"):
                        var_t = self.runes.get(b_type.name, {}).get(t_field)
            if var_t is None:
                var_t = self._infer_node_type(parts[0])
            for idx_node in parts[1:]:
                current_base = base
                idx = self._translate_expr(idx_node)
                idx = self._emit_bounds_check(idx, current_base, var_t, idx_node)
                if isinstance(var_t, (SliceType, ManyType)) or (isinstance(var_t, RefType) and isinstance(var_t.target, (SliceType, ManyType))):
                    actual_slice = var_t.target if isinstance(var_t, RefType) else var_t
                    elem_cast = CTypeMapper.to_c_decl(actual_slice.element, "*")
                    access = "->" if isinstance(var_t, RefType) else "."
                    base = f"((({elem_cast})({base}){access}data)[{idx}])"
                    var_t = actual_slice.element
                elif isinstance(var_t, ListType) or (isinstance(var_t, RefType) and isinstance(var_t.target, ListType)):
                    elem_t = var_t.target.element if isinstance(var_t, RefType) else var_t.element
                    elem_cast = CTypeMapper.to_c_decl(elem_t, "*")
                    ptr = base if (isinstance(var_t, RefType) and not base.startswith("&")) else f"&({base})"
                    base = f"(*({elem_cast})pengu_list_at({ptr}, {idx}))"
                    var_t = var_t.element if isinstance(var_t, ListType) else var_t.target.element
                elif isinstance(var_t, ArrayType):
                    base = f"{base}[{idx}]"
                    var_t = var_t.element
                elif isinstance(var_t, RefType) and not isinstance(var_t.target, MapType):
                    base = f"{base}[{idx}]"
                    tgt = var_t.target
                    while isinstance(tgt, (AliasType, FrozenType)) and getattr(tgt, "target", None):
                        tgt = tgt.target
                    var_t = tgt.element if isinstance(tgt, (ArrayType, SliceType, ManyType, ListType)) else tgt
                elif self._expr_is_string(parts[0], var_t):
                    base = f"pengu_string_char_at({base}, {idx})"
                    var_t = None
                elif isinstance(var_t, (MapType, RefType)) and (isinstance(var_t, MapType) or isinstance(var_t.target, MapType)):
                    actual_map = var_t.target if isinstance(var_t, RefType) else var_t
                    key_c = CTypeMapper.to_c_type(actual_map.key)
                    val_c = CTypeMapper.to_c_type(actual_map.value)
                    ptr = base if isinstance(var_t, RefType) else f"&({base})"
                    tmp_k = self.get_temp_name("_k")
                    tmp_p = self.get_temp_name("_p")
                    val_cast = CTypeMapper.to_c_decl(actual_map.value, "*")
                    val_zero = "NULL" if isinstance(actual_map.value, (FnType, RefType)) else f"({val_c}){{0}}"
                    base = (f"({{ {key_c} {tmp_k} = ({idx}); "
                            f"void* {tmp_p} = pengu_map_get({ptr}, &{tmp_k}); "
                            f"{tmp_p} ? (*(({val_cast}){tmp_p})) : {val_zero}; }})")
                    var_t = actual_map.value
                else:
                    base = f"{base}[{idx}]"
                    var_t = None
            return base
        elif rule == "length_expr":
            target_node = node.children[0]
            base = self._translate_expr(target_node)
            var_t = self._infer_node_type(target_node)
            if var_t is None:
                if isinstance(target_node, Tree) and target_node.data == "var_ref":
                    var_t = self._lookup_var_type(str(target_node.children[0]))
                elif isinstance(target_node, Token):
                    var_t = self._lookup_var_type(str(target_node))
                else:
                    var_t = self._lookup_var_type(base)

            actual_t = var_t.target if isinstance(var_t, RefType) else var_t
            if isinstance(actual_t, ArrayType) and actual_t.size is not None:
                return str(actual_t.size)

            sym = self._lookup_symbol(base)
            eff_t = var_t if var_t is not None else (sym.type if sym else None)
            sep = "->" if (base == "self" or isinstance(eff_t, RefType)) else "."
            return f"{base}{sep}len"

        # 6. Cast
        elif rule == "cast_expr":
            base = self._translate_expr(node.children[0])
            t = ast_to_type(node.children[1], self._lookup_type_fn)
            if isinstance(t, BaseType) and t.name == "string":
                return self._to_string_call(base, self._infer_node_type(node.children[0]))
            t_str = CTypeMapper.to_c_type(t)
            return f"(({t_str})({base}))"

        elif rule == "to_expr":
            left_node = node.children[0]
            right_node = node.children[1]
            is_type_cast = False
            cast_target = None
            if isinstance(right_node, Tree):
                if right_node.data in ("base_type", "custom_type", "ref_type", "fn_type", "array_type", "slice_type"):
                    is_type_cast = True
                    cast_target = ast_to_type(right_node, self._lookup_type_fn)
                elif right_node.data == "var_ref":
                    name = str(right_node.children[0])
                    if name in ("int", "i32", "i64", "f32", "f64", "float", "double", "bool", "string", "char", "byte", "u8", "u16", "u32", "u64") or (self.symbols and (name in self.symbols.runes or self.symbols.lookup_type(name))):
                        is_type_cast = True
                        cast_target = ast_to_type(right_node, self._lookup_type_fn)
                    elif name in self.runes or name in self.seals or name in self.aliases:
                        is_type_cast = True
                        cast_target = ast_to_type(right_node, self._lookup_type_fn)
            if is_type_cast and cast_target is not None:
                base = self._translate_expr(left_node)
                if isinstance(cast_target, BaseType) and cast_target.name == "string":
                    # 'x to string' on a value that already *is* a string is the
                    # identity: going through pengu_to_string(…) would hand back
                    # the very same buffer, and an interpolation temporary would
                    # then free someone else's memory (a '.rodata' view →
                    # 'free(): invalid pointer').
                    inner_t = self._infer_node_type(left_node)
                    unwrapped_t = inner_t
                    while (isinstance(unwrapped_t, (AliasType, FrozenType))
                           and getattr(unwrapped_t, "target", None)):
                        unwrapped_t = unwrapped_t.target
                    if isinstance(unwrapped_t, BaseType) and unwrapped_t.name == "string":
                        return base
                    return self._to_string_call(base, inner_t)
                t_str = CTypeMapper.to_c_type(cast_target)
                return f"(({t_str})({base}))"
            else:
                start_c = self._translate_expr(left_node)
                end_c = self._translate_expr(right_node)
                return f"((PenguRange){{ .start = (int64_t)({start_c}), .end = (int64_t)({end_c}) }})"

        elif rule == "range_dotdot":
            # Item 2.5: `a at b..c` is a slice, exactly like `a at b to c`. The
            # grammar binds 'at' tighter than '..', so the node arrives as
            # `range_dotdot(at_expr(a, b), .., c)`. Re-shape it as the
            # `slice_at_expr` the canonical spelling produces and reuse that
            # emitter, so the two spellings cannot drift apart.
            _slice = self._dotdot_as_slice_shape(node)
            if _slice is not None:
                return self._emit_slice_at(_slice)
            start_c = self._translate_expr(node.children[0])
            end_c = self._translate_expr(node.children[-1])
            return f"((PenguRange){{ .start = (int64_t)({start_c}), .end = (int64_t)({end_c}) }})"

        # 7. Ternary if expression: if a then b else c
        elif rule == "if_expr":
            cond = self._translate_expr(node.children[0])
            then_expr = self._translate_expr(node.children[1])
            else_expr = self._translate_expr(node.children[2])
            return f"(({cond}) ? ({then_expr}) : ({else_expr}))"

        # 7b. Compile-time when expression: only the active branch is emitted.
        elif rule == "when_expr":
            val = eval_comptime(self.compile_env, node.children[0])
            if val is None or not isinstance(val, bool):
                raise SemanticError(
                    "'when' condition must evaluate to a compile-time boolean constant",
                    code="E0039",
                )
            if val is True:
                return self._translate_expr(node.children[1], expected_type=expected_type)
            return self._translate_expr(node.children[2], expected_type=expected_type)

        # 8. Struct init: with x is 1 and y is 2
        elif rule == "struct_init":
            if expected_type is None:
                inferred_t = self._infer_node_type(node)
                if isinstance(inferred_t, (RuneType, EchoType, OmenType)):
                    expected_type = inferred_t

            field_inits = []
            unwrapped_struct_t = expected_type
            while isinstance(unwrapped_struct_t, AliasType) and unwrapped_struct_t.target:
                unwrapped_struct_t = unwrapped_struct_t.target

            for f in node.children:
                if isinstance(f, Tree) and f.data == "field_init":
                    f_raw = str(f.children[0])
                    f_name = self._c_ident(f_raw)
                    exp_child_type = None
                    if unwrapped_struct_t is not None:
                        if isinstance(unwrapped_struct_t, (RuneType, EchoType)):
                            if f_raw in unwrapped_struct_t.fields:
                                exp_child_type = unwrapped_struct_t.fields[f_raw]
                            elif f_name in unwrapped_struct_t.fields:
                                exp_child_type = unwrapped_struct_t.fields[f_name]
                        elif isinstance(unwrapped_struct_t, BaseType) and unwrapped_struct_t.name in self.runes:
                            if f_raw in self.runes[unwrapped_struct_t.name]:
                                exp_child_type = self.runes[unwrapped_struct_t.name][f_raw]
                            elif f_name in self.runes[unwrapped_struct_t.name]:
                                exp_child_type = self.runes[unwrapped_struct_t.name][f_name]
                        elif isinstance(unwrapped_struct_t, BaseType) and unwrapped_struct_t.name in self.echos:
                            if f_raw in self.echos[unwrapped_struct_t.name]:
                                exp_child_type = self.echos[unwrapped_struct_t.name][f_raw]
                            elif f_name in self.echos[unwrapped_struct_t.name]:
                                exp_child_type = self.echos[unwrapped_struct_t.name][f_name]
                        elif isinstance(unwrapped_struct_t, OmenType):
                            if f_raw in unwrapped_struct_t.variants:
                                v_fields = unwrapped_struct_t.variants[f_raw] or {}
                                # 'with Msg is "x"' gives the payload directly:
                                # the expected type is the variant's only field,
                                # not the variant struct (passing the struct made
                                # '[1, 2, 3]' lower to an invalid PenguList
                                # initializer).  A nested 'with ... is with ...'
                                # keeps the struct type so its fields resolve.
                                value_node = f.children[1] if len(f.children) > 1 else None
                                nested_init = (isinstance(value_node, Tree)
                                               and value_node.data == "struct_init")
                                if len(v_fields) == 1 and not nested_init:
                                    exp_child_type = next(iter(v_fields.values()))
                                else:
                                    exp_child_type = RuneType(name=f_raw, fields=v_fields)
                            elif f_name in unwrapped_struct_t.variants:
                                v_fields = unwrapped_struct_t.variants[f_name] or {}
                                value_node = f.children[1] if len(f.children) > 1 else None
                                nested_init = (isinstance(value_node, Tree)
                                               and value_node.data == "struct_init")
                                if len(v_fields) == 1 and not nested_init:
                                    exp_child_type = next(iter(v_fields.values()))
                                else:
                                    exp_child_type = RuneType(name=f_name, fields=v_fields)

                    f_val = self._translate_expr(f.children[1], expected_type=exp_child_type) if (len(f.children) > 1 and f.children[1] is not None) else None
                    # Struct fields do not deep-copy their strings: the aggregate
                    # initialiser stores the bytes of the value, exactly like a C
                    # designated initialiser.  Managing the buffer is up to you.
                    field_inits.append((f_name, f_val, f_raw))

            if expected_type is not None and isinstance(expected_type, OmenType):
                omen_cname = getattr(expected_type, "c_name", None) or expected_type.name
                if not expected_type.is_algebraic:
                    if field_inits:
                        _, _, v_raw = field_inits[0]
                        return self._get_omen_variant_c_name(omen_cname, v_raw)
                    return f"({omen_cname})0"
                else:
                    if field_inits:
                        names = [raw for _, _, raw in field_inits]
                        variant_names = set(expected_type.variants)

                        if all(n in variant_names for n in names):
                            # Variant-selected form: `with Connected is with session_id is "x"`
                            distinct = set(names)
                            if len(distinct) > 1:
                                raise SemanticError(
                                    f"omen '{expected_type.name}' initializer selects more than one variant: {sorted(distinct)}",
                                    code="E0041",
                                )
                            v_name, v_val, v_raw = field_inits[0]
                            v_fields = expected_type.variants.get(v_raw, {})
                            tag = self._get_omen_variant_c_name(omen_cname, v_raw)
                            union_field = self._c_ident(v_raw)
                            if v_fields and v_val is not None:
                                return f"({omen_cname}){{ .tag = {tag}, .data.{union_field} = {v_val} }}"
                            return f"({omen_cname}){{ .tag = {tag} }}"

                        # Bare-payload form: `with code is 404` — resolve each
                        # field to the single variant that owns it.
                        field_to_variants = {}
                        for vn, v_fields in expected_type.variants.items():
                            for fn in v_fields:
                                field_to_variants.setdefault(fn, []).append(vn)
                        variant = None
                        for fn in names:
                            owners = field_to_variants.get(fn, [])
                            if not owners:
                                raise SemanticError(
                                    f"'{fn}' is not a field or variant of omen '{expected_type.name}'",
                                    code="E0041",
                                )
                            if len(owners) > 1:
                                raise SemanticError(
                                    f"omen field '{fn}' is ambiguous: it belongs to variants {owners}; name the variant explicitly",
                                    code="E0041",
                                )
                            if variant is None:
                                variant = owners[0]
                            elif owners[0] != variant:
                                raise SemanticError(
                                    f"omen payload fields belong to different variants "
                                    f"('{variant}' vs '{owners[0]}')",
                                    code="E0041",
                                )
                        payload = ", ".join(f".{fn} = {fv}" for fn, fv, _ in field_inits)
                        tag = self._get_omen_variant_c_name(omen_cname, variant)
                        union_field = self._c_ident(variant)
                        return (f"({omen_cname}){{ .tag = {tag}, "
                                f".data.{union_field} = {{{payload}}} }}")
                    return f"({omen_cname}){{0}}"

            type_name = ""
            if expected_type is not None and isinstance(expected_type, (RuneType, EchoType)):
                is_real_rune = (
                    expected_type.name in self.runes
                    or expected_type.name in self.echos
                    or (self.symbols is not None and (
                        expected_type.name in self.symbols.runes
                        or expected_type.name in self.symbols.echos
                        or (self.symbols.lookup(expected_type.name) and self.symbols.lookup(expected_type.name).kind in ("rune", "echo", "type", "declare"))
                    ))
                )
                if is_real_rune:
                    c_t = CTypeMapper.to_c_type(expected_type)
                    type_name = f"({c_t})"

            if not type_name and expected_type is not None:
                actual = expected_type
                while isinstance(actual, (AliasType, FrozenType)) and getattr(actual, "target", None):
                    actual = actual.target
                is_real = (
                    isinstance(actual, (RuneType, EchoType)) and (
                        actual.name in self.runes
                        or actual.name in self.echos
                        or (self.symbols is not None and (
                            actual.name in self.symbols.runes
                            or actual.name in self.symbols.echos
                            or (self.symbols.lookup(actual.name) and self.symbols.lookup(actual.name).kind in ("rune", "echo", "type", "declare"))
                        ))
                    )
                ) or (
                    isinstance(actual, BaseType) and (actual.name in self.runes or actual.name in self.echos)
                )
                if is_real:
                    c_t = CTypeMapper.to_c_type(expected_type)
                    if c_t and c_t != "void":
                        type_name = f"({c_t})"

            field_str = ", ".join(f".{name} = {val}" for name, val, _ in field_inits)
            return f"{type_name}{{{field_str}}}"

        elif rule == "with_init_expr":
            # Block-style construction: build a fresh value through
            # 'set .field is ...' / 'calling .method' statements on an implicit
            # temporary, then yield that temporary as the expression value.
            build_t = expected_type
            if build_t is None:
                build_t = self._infer_node_type(node)
            if not isinstance(build_t, (RuneType, EchoType, OmenType)):
                raise SemanticError(
                    "'with:' block construction requires a struct-like target type "
                    "(rune/echo/omen) from an explicit annotation",
                    code="E0014",
                )
            c_t = CTypeMapper.to_c_type(build_t)
            tmp = self.get_temp_name("_with")
            self.with_stack.append(tmp)
            self.with_type_stack.append(build_t)
            saved_locals = dict(self.local_vars)
            self.local_vars[tmp] = build_t
            try:
                parts = []
                for ch in node.children:
                    if isinstance(ch, Tree):
                        s_code = self._translate_stmt(ch)
                        if s_code:
                            parts.append(s_code.rstrip())
            finally:
                self.local_vars = saved_locals
                self.with_type_stack.pop()
                self.with_stack.pop()
            body = " ".join(parts)
            if not self.use_gnu_extensions:
                self._hoist(f"{c_t} {tmp} = {{0}};")
                for p in parts:
                    self._hoist(p)
                return tmp
            return f"(__extension__(({{ {c_t} {tmp} = {{0}}; {body} {tmp}; }})))"

        elif rule == "do_expr":
            # General statement-block expression: run the statements in order
            # and evaluate to the last one's value (an expression, or a
            # trailing value-position 'if').
            saved_locals = dict(self.local_vars)
            try:
                parts, val = self._translate_value_block(
                    list(node.children),
                    getattr(node, "_pengu_value_type", None) or expected_type)
                if val is not None:
                    parts.append(f"{val};")
            finally:
                self.local_vars = saved_locals
            # The last statement (with its ';') supplies the block value.
            inner_c = "\n".join(parts) if parts else "(void)0;"
            if not self.use_gnu_extensions:
                hoisted = parts[:-1] if val is not None else parts
                for p in hoisted:
                    self._hoist(p)
                return val if val is not None else "((void)0)"
            return f"(__extension__(({{\n{inner_c}\n}})))"

        elif rule == "if_stmt":
            # An 'if' reached through an expression position is a value block
            # (the checker recorded the common branch type): emit a GNU
            # statement-expression whose temporary receives the branch value.
            binding = self._binding_cond(node.children[0])
            if binding is not None:
                return self._translate_binding_value_if(node, binding, expected_type)
            return self._translate_value_if(node, expected_type)

        elif rule == "unless_stmt":
            # Same as above with the condition negated ('unless' semantics).
            return self._translate_value_if(node, expected_type, negate=True)

        elif rule in ("while_stmt", "for_range_stmt", "for_in_stmt"):
            # A loop reached through an expression position collects its body's
            # value into a list (the checker recorded 'list of T' on the node).
            return self._translate_loop_value(node, expected_type)

        elif rule == "paren_expr":
            # Keep the grouping visible in the C text; the tree already encodes
            # precedence, so this is only cosmetic.
            return f"({self._translate_expr(node.children[0], expected_type)})"

        elif rule in ("lambda_expr", "lambda_no_params"):
            # Lambdas are emitted as top-level 'static' functions by the
            # pre-scan; the value is the function name, which decays to a
            # function pointer in C.
            name = getattr(node, "_lambda_name", None)
            if name is None:
                raise SemanticError(
                    "lambda not registered; run pre-scan before codegen",
                    code="E0000")
            return self._cast_fn_value(name, expected_type)

        elif rule == "judge_expr":
            matched_node = node.children[0]
            matched_type = self._infer_node_type(matched_node)
            matched_expr = self._translate_expr(matched_node)

            res_type = expected_type or self._infer_node_type(node)
            res_c_type = CTypeMapper.to_c_type(res_type) if (res_type and not isinstance(res_type, AnyType)) else "__auto_type"

            clauses = []
            has_guards = False
            has_payloads = False
            else_val = None
            for c in node.children[1:]:
                if isinstance(c, Tree):
                    if c.data == "when_clause":
                        pat_node = c.children[0]
                        payload_node = None
                        guard_node = None
                        for sub in c.children[1:-1]:
                            if isinstance(sub, Tree):
                                if sub.data == "when_payload":
                                    payload_node = sub
                                elif sub.data == "when_guard":
                                    guard_node = sub

                        if guard_node is not None:
                            has_guards = True
                        if payload_node is not None:
                            has_payloads = True

                        pat = None
                        simple_pat = None
                        if isinstance(pat_node, Tree) and pat_node.data == "when_pattern" and pat_node.children:
                            if len(pat_node.children) > 1:
                                pat_parts = [str(p) for p in pat_node.children if str(p) != "."]
                                pat = "_".join(pat_parts)
                                simple_pat = pat_parts[-1]
                            else:
                                simple_pat = str(pat_node.children[0])
                                pat_node = pat_node.children[0]
                        if pat is None:
                            pat = self._translate_expr(pat_node)

                        target_omen = None
                        if matched_type and isinstance(matched_type, OmenType):
                            target_omen = getattr(matched_type, "c_name", None) or matched_type.name
                            if target_omen not in self.omens and matched_type.name in self.omens:
                                target_omen = matched_type.name
                        elif matched_type and isinstance(matched_type, BaseType) and matched_type.name in self.omens:
                            target_omen = matched_type.name
                        elif matched_expr in self.local_vars:
                            lv_t = self.local_vars[matched_expr]
                            if hasattr(lv_t, "c_name") and getattr(lv_t, "c_name") in self.omens:
                                target_omen = getattr(lv_t, "c_name")
                            elif hasattr(lv_t, "name") and lv_t.name in self.omens:
                                target_omen = lv_t.name

                        if target_omen and target_omen not in self.omens:
                            for o_key in self.omens:
                                if o_key == target_omen or o_key.endswith(target_omen):
                                    target_omen = o_key
                                    break

                        if not target_omen and self.omens:
                            cand_simple = pat.rsplit("_", 1)[-1] if "_" in pat else pat
                            for o_key, variants in self.omens.items():
                                if pat in variants or cand_simple in variants:
                                    target_omen = o_key
                                    break

                        variant_fields = {}
                        if target_omen:
                            variants = self.omens.get(target_omen, {})
                            if pat in variants:
                                simple_pat = pat
                            elif "_" in pat:
                                prefix, cand = pat.rsplit("_", 1)
                                matched_logical = getattr(matched_type, "name", None) if matched_type else None
                                if cand in variants and (prefix == target_omen or (matched_logical and prefix == matched_logical)):
                                    simple_pat = cand
                            if simple_pat is not None:
                                variant_fields = variants.get(simple_pat, {})
                                pat = self._get_omen_variant_c_name(target_omen, simple_pat)

                        payload_vars = []
                        if payload_node:
                            p_fields = []
                            for fn in payload_node.children:
                                if isinstance(fn, Tree) and fn.data == "when_field":
                                    p_fields.append(str(fn.children[0]))
                                elif isinstance(fn, Token):
                                    p_fields.append(str(fn))
                            for pf in p_fields:
                                p_type = variant_fields.get(pf)
                                if p_type is None and isinstance(matched_type, OmenType):
                                    p_type = matched_type.variants.get(simple_pat, {}).get(pf)
                                payload_vars.append((pf, p_type))

                        old_locals = dict(self.local_vars)
                        try:
                            for pf, pt in payload_vars:
                                self.local_vars[pf] = pt
                            guard_expr_str = None
                            if guard_node:
                                guard_expr_str = self._translate_expr(guard_node.children[0])
                            val = self._translate_expr(c.children[-1], expected_type=res_type)
                        finally:
                            self.local_vars = old_locals

                        clauses.append({
                            "pat": pat,
                            "simple_pat": simple_pat,
                            "target_omen": target_omen,
                            "payload_vars": payload_vars,
                            "guard": guard_expr_str,
                            "val": val
                        })
                    elif c.data == "else_clause":
                        else_val = self._translate_expr(c.children[0], expected_type=res_type)

            if else_val is None:
                if res_type and res_type.is_numeric():
                    else_val = "0"
                elif res_type and res_type.is_string():
                    else_val = 'pengu_string_from_cstr("")'
                elif res_type and isinstance(res_type, (FnType, RefType)):
                    else_val = "NULL"
                elif res_type and not isinstance(res_type, AnyType):
                    else_val = f"({res_c_type}){{0}}"
                elif clauses:
                    else_val = f"({clauses[0]['val']})"
                else:
                    else_val = "0"

            is_string_omen = isinstance(matched_type, OmenType) and (matched_type.is_string() or matched_type.is_string_valued)
            is_algebraic_omen = isinstance(matched_type, OmenType) and matched_type.is_algebraic
            is_enum_or_int = not is_string_omen and (matched_type is None or matched_type.is_int() or (isinstance(matched_type, OmenType) and not matched_type.is_algebraic))

            if has_guards or has_payloads:
                t_val = self.get_temp_name("_val")
                t_res = self.get_temp_name("_res")
                lbl_end = self.get_temp_name("_judge_end")
                decl_val = (CTypeMapper.to_c_decl(matched_type, t_val)
                            if (matched_type and not isinstance(matched_type, AnyType))
                            else f"__typeof__(({matched_expr})) {t_val}")
                decl_res = CTypeMapper.to_c_decl(res_type, t_res) if (res_type and not isinstance(res_type, AnyType)) else f"__typeof__(({else_val})) {t_res}"
                lines = [f"{decl_val} = ({matched_expr});", f"{decl_res};"]
                for cl in clauses:
                    pat = cl["pat"]
                    simple_pat = cl["simple_pat"]
                    payload_vars = cl["payload_vars"]
                    guard = cl["guard"]
                    val = cl["val"]
                    if is_algebraic_omen:
                        cond = f"{t_val}.tag == {pat}"
                    elif matched_type and matched_type.is_string():
                        cond = f"pengu_string_equal({t_val}, {pat})"
                    else:
                        cond = f"{t_val} == {pat}"

                    clause_code = []
                    if is_algebraic_omen and payload_vars and simple_pat:
                        for pf, pt in payload_vars:
                            c_t = CTypeMapper.to_c_type(pt) if (pt and not isinstance(pt, AnyType)) else "__auto_type"
                            field_access = f"{t_val}.data.{self._c_ident(simple_pat)}.{self._c_ident(pf)}"
                            clause_code.append(f"{c_t} {self._c_ident(pf)} = {field_access};")
                    if guard:
                        clause_code.append(f"if ({guard}) {{ {t_res} = ({val}); goto {lbl_end}; }}")
                    else:
                        clause_code.append(f"{t_res} = ({val}); goto {lbl_end};")
                    body_str = " ".join(clause_code)
                    lines.append(f"if ({cond}) {{ {body_str} }}")
                lines.append(f"{t_res} = ({else_val});")
                lines.append(f"{lbl_end}:;")
                lines.append(f"{t_res};")
                if not self.use_gnu_extensions:
                    for ln in lines[:-1]:
                        self._hoist(ln)
                    return t_res
                return f"(__extension__({{ {' '.join(lines)} }}))"

            def _is_c_switchable(p: str) -> bool:
                if p.lstrip('-').isdigit():
                    return True
                if is_algebraic_omen or (isinstance(matched_type, OmenType) and not matched_type.is_algebraic):
                    return True
                return False

            all_switchable = len(clauses) > 0 and (is_enum_or_int or is_algebraic_omen) and all(_is_c_switchable(cl["pat"]) for cl in clauses)
            if all_switchable and (is_enum_or_int or is_algebraic_omen):
                t_val = self.get_temp_name("_val")
                t_res = self.get_temp_name("_res")
                decl_val = (CTypeMapper.to_c_decl(matched_type, t_val)
                            if (matched_type and not isinstance(matched_type, AnyType))
                            else f"__typeof__(({matched_expr})) {t_val}")
                decl_res = CTypeMapper.to_c_decl(res_type, t_res) if (res_type and not isinstance(res_type, AnyType)) else f"__typeof__(({else_val})) {t_res}"
                switch_expr = f"{t_val}.tag" if is_algebraic_omen else t_val
                cases_str = " ".join(f"case {cl['pat']}: {t_res} = ({cl['val']}); break;" for cl in clauses)
                if not self.use_gnu_extensions:
                    self._hoist(f"{decl_val} = ({matched_expr});")
                    self._hoist(f"{decl_res};")
                    self._hoist(f"switch ({switch_expr}) {{ {cases_str} default: {t_res} = ({else_val}); break; }}")
                    return t_res
                return f"(__extension__({{ {decl_val} = ({matched_expr}); {decl_res}; switch ({switch_expr}) {{ {cases_str} default: {t_res} = ({else_val}); break; }} {t_res}; }}))"

            # Build ternary chain for non-integer matches
            curr = else_val
            needs_wrapper = not self._is_side_effect_free(matched_node)
            t_v = self.get_temp_name("_v")
            subj = t_v if needs_wrapper else matched_expr
            for cl in reversed(clauses):
                pat = cl["pat"]
                val = cl["val"]
                if matched_type and matched_type.is_string():
                    curr = f"(pengu_string_equal({subj}, {pat}) ? ({val}) : ({curr}))"
                elif is_algebraic_omen:
                    curr = f"(({subj}.tag == {pat}) ? ({val}) : ({curr}))"
                else:
                    curr = f"(({subj} == {pat}) ? ({val}) : ({curr}))"
            if needs_wrapper:
                decl_tv = CTypeMapper.to_c_decl(matched_type, t_v) if (matched_type and not isinstance(matched_type, AnyType)) else f"__auto_type {t_v}"
                if not self.use_gnu_extensions:
                    self._hoist(f"{decl_tv} = ({matched_expr});")
                    return curr
                return f"(__extension__({{ {decl_tv} = ({matched_expr}); {curr}; }}))"
            return curr

        # 10. Presence checks
        elif rule == "is_present":
            child = node.children[0]
            expr_str = self._translate_expr(child)
            if isinstance(child, Tree) and child.data == "var_ref":
                return f"pengu_maybe_is_present(&({expr_str}))"
            tmp = self.get_temp_name("_maybe")
            if not self.use_gnu_extensions:
                self._hoist(f"PenguMaybe {tmp} = ({expr_str});")
                return f"pengu_maybe_is_present(&{tmp})"
            return f"(__extension__({{ __auto_type {tmp} = ({expr_str}); pengu_maybe_is_present(&{tmp}); }}))"
        elif rule == "is_not_present":
            child = node.children[0]
            expr_str = self._translate_expr(child)
            if isinstance(child, Tree) and child.data == "var_ref":
                return f"(!pengu_maybe_is_present(&({expr_str})))"
            tmp = self.get_temp_name("_maybe")
            if not self.use_gnu_extensions:
                self._hoist(f"PenguMaybe {tmp} = ({expr_str});")
                return f"(!pengu_maybe_is_present(&{tmp}))"
            return f"(__extension__({{ __auto_type {tmp} = ({expr_str}); !pengu_maybe_is_present(&{tmp}); }}))"
        elif rule == "is_true":
            expr_str = self._translate_expr(node.children[0])
            return f"(({expr_str}) == true)"
        elif rule == "is_false":
            expr_str = self._translate_expr(node.children[0])
            return f"(({expr_str}) == false)"

        # 11. Collection Inits
        elif rule == "array_lit":
            if expected_type and isinstance(expected_type, ListType):
                elem_t = expected_type.element
                elem_c = CTypeMapper.to_c_type(elem_t)
                elems = [self._translate_expr(c, expected_type=elem_t) for c in node.children]
                tmp_list = self.get_temp_name("_list_lit")
                pushes = []
                for e in elems:
                    tmp_elem = self.get_temp_name("_elem")
                    pushes.append(f"{elem_c} {tmp_elem} = {e}; pengu_list_push(&{tmp_list}, &{tmp_elem});")
                cap = max(len(elems), 4)
                init_fn = f"pengu_list_new(sizeof({elem_c}), {cap})"
                return self._block_expr(
                    [f"PenguList {tmp_list} = {init_fn};"] + pushes,
                    tmp_list,
                )
            elem_expected = None
            if expected_type and isinstance(expected_type, (ArrayType, SliceType, ManyType)):
                elem_expected = expected_type.element
            elems = [self._translate_expr(c, expected_type=elem_expected) for c in node.children]
            return f"{{ {', '.join(elems)} }}"
        elif rule == "array_init_expr":
            elem_type = ast_to_type(node.children[0], self._lookup_type_fn)
            size_expr = self._translate_expr(node.children[1])
            elem_str = CTypeMapper.to_c_type(elem_type)
            return f"({elem_str}[{size_expr}]){{0}}"
        elif rule == "list_init_expr":
            elem_type = ast_to_type(node.children[0], self._lookup_type_fn)
            cap = "8"
            if len(node.children) > 1 and node.children[1] is not None:
                c_trans = self._translate_expr(node.children[1])
                if c_trans:
                    cap = c_trans
            elem_str = CTypeMapper.to_c_type(elem_type)
            return f"pengu_list_new(sizeof({elem_str}), {cap})"

        elif rule == "map_init_expr":
            key_type = ast_to_type(node.children[0], self._lookup_type_fn) if len(node.children) >= 2 else AnyType()
            val_type = ast_to_type(node.children[1], self._lookup_type_fn) if len(node.children) >= 2 else AnyType()
            k_str = CTypeMapper.to_c_type(key_type) if key_type and not isinstance(key_type, AnyType) else "PenguString"
            v_str = CTypeMapper.to_c_type(val_type) if val_type and not isinstance(val_type, AnyType) else "int32_t"
            return f"pengu_map_new(sizeof({k_str}), sizeof({v_str}))"

        # 12. Map literals: { key: value, ... }
        elif rule == "map_lit":
            entries = [c for c in node.children if isinstance(c, Tree) and c.data == "map_entry"]
            map_t = expected_type if (expected_type is not None and isinstance(expected_type, MapType)) else None
            if map_t is None:
                try:
                    inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                    for lv_k, lv_v in self.local_vars.items():
                        inferrer.symbols.define(Symbol(name=lv_k, type=lv_v, kind="var"))
                    inferred = inferrer.infer(node)
                    if isinstance(inferred, MapType):
                        map_t = inferred
                except Exception:
                    map_t = None
            if map_t is None:
                map_t = MapType(key=STRING_TYPE, value=INT_TYPE)
            key_c = CTypeMapper.to_c_type(map_t.key)
            val_c = CTypeMapper.to_c_type(map_t.value)
            map_init_call = f"pengu_map_new(sizeof({key_c}), sizeof({val_c}))"

            if not entries:
                return map_init_call

            m_tmp = self.get_temp_name("_map")
            stmts = [f"PenguMap {m_tmp} = {map_init_call};"]
            for entry in entries:
                key_node = entry.children[0]
                val_node = entry.children[1]

                k_tmp = self.get_temp_name("_mkey")
                if isinstance(key_node, Token) and key_node.type == "STRING":
                    raw_k = str(key_node)
                    k_s = raw_k[1:-1] if (raw_k.startswith('"') and raw_k.endswith('"') and len(raw_k) >= 2) else raw_k
                    key_code = self._translate_string_lit(k_s)
                elif isinstance(key_node, Token) and key_node.type == "NAME" and map_t.key == STRING_TYPE:
                    key_code = f'pengu_string_from_cstr("{str(key_node)}")'
                else:
                    key_code = self._translate_expr(key_node, expected_type=map_t.key)
                decl_k = CTypeMapper.to_c_decl(map_t.key, k_tmp)
                stmts.append(f"{decl_k} = {key_code};")

                v_tmp = self.get_temp_name("_mval")
                val_code = self._translate_expr(val_node, expected_type=map_t.value)
                decl_v = CTypeMapper.to_c_decl(map_t.value, v_tmp)
                stmts.append(f"{decl_v} = {val_code};")
                stmts.append(f"pengu_map_put(&{m_tmp}, &{k_tmp}, &{v_tmp});")

            if not self.use_gnu_extensions:
                for s in stmts:
                    self._hoist(s)
                return m_tmp
            stmts.append(f"{m_tmp};")
            inner = "\n    ".join(stmts)
            return f"(__extension__({{\n    {inner}\n  }}))"

        # 13. Indented literals: 2D/1D arrays, Runes, Maps
        elif rule == "indent_literal":
            child = node.children[0]
            if child.data == "indent_array":
                rows = child.children
                if not rows:
                    return "{0}"

                elem_t = expected_type.element if (expected_type and isinstance(expected_type, ArrayType)) else None
                inner_elem_t = elem_t.element if (elem_t and isinstance(elem_t, ArrayType)) else elem_t

                is_2d = False
                if isinstance(expected_type, ArrayType) and isinstance(expected_type.element, ArrayType):
                    is_2d = True
                elif len(rows) > 1 and len(rows[0].children) > 1:
                    is_2d = True

                if is_2d:
                    row_strs = []
                    for row in rows:
                        elem_strs = [self._translate_expr(e, expected_type=inner_elem_t) for e in row.children]
                        row_strs.append(f"{{ {', '.join(elem_strs)} }}")
                    return f"{{ {', '.join(row_strs)} }}"
                else:
                    elem_strs = []
                    for row in rows:
                        for e in row.children:
                            elem_strs.append(self._translate_expr(e, expected_type=inner_elem_t or elem_t))
                    return f"{{ {', '.join(elem_strs)} }}"

            elif child.data == "indent_entries":
                entries = child.children
                is_rune = False
                rune_name = None
                rune_type = None
                if expected_type is not None:
                    if isinstance(expected_type, (RuneType, EchoType)):
                        is_rune = True
                        rune_name = expected_type.name
                        rune_type = expected_type
                    elif isinstance(expected_type, BaseType) and (expected_type.name in self.runes or expected_type.name in self.echos):
                        is_rune = True
                        rune_name = expected_type.name
                        fields = self.runes.get(rune_name) or self.echos.get(rune_name, {})
                        rune_type = RuneType(name=rune_name, fields=fields)

                if is_rune and rune_name:
                    sym_r = self.symbols.lookup_type(rune_name) if self.symbols else None
                    c_rune_name = getattr(rune_type, "c_name", None) or getattr(expected_type, "c_name", None) or getattr(sym_r, "c_name", None) or self._c_ident(rune_name)
                    field_inits = []
                    for entry in entries:
                        f_raw = str(entry.children[0])
                        f_name = self._c_ident(f_raw)
                        f_type = (rune_type.fields.get(f_raw) or rune_type.fields.get(f_name)) if (rune_type and rune_type.fields) else None
                        f_val = self._translate_expr(entry.children[1], expected_type=f_type)
                        field_inits.append(f".{f_name} = {f_val}")
                    return f"({c_rune_name}){{ {', '.join(field_inits)} }}"
                else:
                    map_t = expected_type if (expected_type is not None and isinstance(expected_type, MapType)) else None
                    if map_t is None:
                        try:
                            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                            for lv_k, lv_v in self.local_vars.items():
                                inferrer.symbols.define(Symbol(name=lv_k, type=lv_v, kind="var"))
                            inferred = inferrer.infer(node)
                            if isinstance(inferred, MapType):
                                map_t = inferred
                        except Exception:
                            map_t = None
                    if map_t is None:
                        map_t = MapType(key=STRING_TYPE, value=INT_TYPE)

                    key_c = CTypeMapper.to_c_type(map_t.key)
                    val_c = CTypeMapper.to_c_type(map_t.value)

                    if not entries:
                        return f"pengu_map_new(sizeof({key_c}), sizeof({val_c}))"

                    m_tmp = self.get_temp_name("_map")
                    stmts = [f"PenguMap {m_tmp} = pengu_map_new(sizeof({key_c}), sizeof({val_c}));"]
                    for entry in entries:
                        key_node = entry.children[0]
                        val_node = entry.children[1]

                        k_tmp = self.get_temp_name("_mkey")
                        if isinstance(key_node, Token) and key_node.type == "STRING":
                            raw_k = str(key_node)
                            k_s = raw_k[1:-1] if (raw_k.startswith('"') and raw_k.endswith('"') and len(raw_k) >= 2) else raw_k
                            key_code = self._translate_string_lit(k_s)
                        elif isinstance(key_node, Token) and key_node.type == "NAME" and map_t.key == STRING_TYPE:
                            key_code = f'pengu_string_from_cstr("{str(key_node)}")'
                        else:
                            key_code = self._translate_expr(key_node, expected_type=map_t.key)
                        decl_k = CTypeMapper.to_c_decl(map_t.key, k_tmp)
                        stmts.append(f"{decl_k} = {key_code};")

                        v_tmp = self.get_temp_name("_mval")
                        val_code = self._translate_expr(val_node, expected_type=map_t.value)
                        decl_v = CTypeMapper.to_c_decl(map_t.value, v_tmp)
                        stmts.append(f"{decl_v} = {val_code};")
                        stmts.append(f"pengu_map_put(&{m_tmp}, &{k_tmp}, &{v_tmp});")

                    stmts.append(f"{m_tmp};")
                    inner = "\n    ".join(stmts)
                    return f"(__extension__({{\n    {inner}\n  }}))"

        # Fallback to recursively translating first child
        if node.children:
            return self._translate_expr(node.children[0], expected_type)
        return ""
    def _translate_string_lit(
        self, s_val: str, as_c_literal: bool = False
    ) -> str:
        """Translates string literal, generating pengu_string_format call for interpolated expressions or C string literal.

        NOTE: String interpolation expressions re-parse and re-infer using local_vars, which
        may in complex scopes diverge from the checker's initial AST type annotations.
        """
        # Absolute import: a mixin module is one level deeper than the old
        # monolithic `pengu_codegen.py`.
        from pengu_parser.pengu_parser import extract_string_parts, PenguParser
        is_raw, is_triple, parts = extract_string_parts(s_val)

        def _escape_c(text: str, is_raw_lit: bool) -> str:
            if is_raw_lit:
                res = []
                for ch in text:
                    if ch == '\\':
                        res.append('\\\\')
                    elif ch == '"':
                        res.append('\\"')
                    elif ch == '\n':
                        res.append('\\n')
                    elif ch == '\r':
                        res.append('\\r')
                    elif ch == '\t':
                        res.append('\\t')
                    else:
                        res.append(ch)
                return "".join(res)
            else:
                res = []
                i = 0
                n = len(text)
                while i < n:
                    ch = text[i]
                    if ch == '\\' and i + 1 < n:
                        if text.startswith('\\u{', i):
                            close_b = text.find('}', i + 3)
                            if close_b != -1:
                                hex_str = text[i + 3:close_b]
                                try:
                                    cp = int(hex_str, 16)
                                    dec_ch = chr(cp)
                                    if dec_ch == '"':
                                        res.append('\\"')
                                    elif dec_ch == '\n':
                                        res.append('\\n')
                                    elif dec_ch == '\r':
                                        res.append('\\r')
                                    elif dec_ch == '\0':
                                        res.append('\\0')
                                    else:
                                        res.append(dec_ch)
                                    i = close_b + 1
                                    continue
                                except (ValueError, OverflowError):
                                    pass
                        elif text.startswith('\\u', i) and i + 5 < n:
                            hex_str = text[i + 2:i + 6]
                            if all(c in '0123456789abcdefABCDEF' for c in hex_str):
                                try:
                                    cp = int(hex_str, 16)
                                    dec_ch = chr(cp)
                                    if dec_ch == '"':
                                        res.append('\\"')
                                    elif dec_ch == '\n':
                                        res.append('\\n')
                                    elif dec_ch == '\r':
                                        res.append('\\r')
                                    elif dec_ch == '\0':
                                        res.append('\\0')
                                    else:
                                        res.append(dec_ch)
                                    i += 6
                                    continue
                                except (ValueError, OverflowError):
                                    pass
                        if text[i + 1] == '\\':
                            res.append('\\\\')
                            i += 2
                            continue
                        res.append(ch)
                        res.append(text[i + 1])
                        i += 2
                        continue
                    if ch == '"':
                        res.append('\\"')
                    elif ch == '\n':
                        res.append('\\n')
                    elif ch == '\r':
                        res.append('\\r')
                    elif ch == '\0':
                        res.append('\\0')
                    else:
                        res.append(ch)
                    i += 1
                return "".join(res)

        has_expr = any(p.is_expr for p in parts)
        if as_c_literal:
            if has_expr:
                raise SemanticError("String interpolation is not supported when expecting a C string literal (ref to char)")
            full_lit = "".join(_escape_c(p.text, is_raw) for p in parts)
            return f'"{full_lit}"'

        if not has_expr:
            full_lit = "".join(_escape_c(p.text, is_raw) for p in parts)
            return f'pengu_string_from_cstr("{full_lit}")'
        if not hasattr(self, "_expr_parser"):
            self._expr_parser = PenguParser()
        parser = self._expr_parser
        fmt_parts = []
        c_args = []
        preamble_decls = []
        postamble_cleanups = []
        for p in parts:
            if not p.is_expr:
                fmt_parts.append(_escape_c(p.text, is_raw).replace("%", "%%"))
            else:
                expr_str = p.text.strip()
                try:
                    expr_ast = parser.parse_expr(expr_str)
                except Exception as exc:
                    raise SemanticError(
                        f"Internal: string interpolation expression '{expr_str}' failed to re-parse at codegen time",
                        code="E0019",
                        help="This is a compiler bug; please report it.",
                        note=str(exc),
                    )

                t = None
                expr_c = expr_str
                if expr_ast is not None:
                    # Reuse the general node typing helper: it seeds local_vars
                    # AND the enchanting/self scope, so interpolating
                    # 'calling self.method' works inside methods too.
                    t = self._infer_node_type(expr_ast)
                    try:
                        expr_c = self._translate_expr(expr_ast)
                    except Exception:
                        expr_c = expr_str

                if t is not None:
                    if self._is_single_char_or_byte(t):
                        fmt_parts.append("%c")
                        c_args.append(f"(char)({expr_c})")
                    elif t.is_int():
                        # Pick a specifier that cannot truncate: 64-bit and
                        # unsigned integers need their own format + cast.
                        spec, cast = self._int_interp_spec(t)
                        fmt_parts.append(spec)
                        c_args.append(f"({cast})({expr_c})")
                    elif t.is_float():
                        fmt_parts.append("%f")
                        c_args.append(f"(double)({expr_c})")
                    elif t.is_bool():
                        fmt_parts.append("%s")
                        c_args.append(f"(({expr_c}) ? \"true\" : \"false\")")
                    elif t.is_string():
                        fmt_parts.append("%.*s")
                        stripped = expr_c.strip()
                        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', stripped):
                            c_args.append(f"(int)({stripped}).len")
                            c_args.append(f"({stripped}).data")
                        else:
                            tmp_s = self.get_temp_name("_str")
                            preamble_decls.append(f"PenguString {tmp_s} = ({expr_c});")
                            c_args.append(f"(int)({tmp_s}).len")
                            c_args.append(f"({tmp_s}).data")
                            if self._expr_allocates_string(expr_ast):
                                # `pengu_string_format_ex` copies the bytes, so a
                                # *fresh* temporary (e.g. `{(x to string)}`) is done
                                # with its buffer and nobody else could release it.
                                # A field, a parameter or a call result is not fresh:
                                # the value read out of it may own its buffer, and
                                # freeing that would free storage the program still
                                # references.  `_expr_allocates_string` answers this
                                # conservatively — a missed release leaks, a wrong
                                # release corrupts.
                                postamble_cleanups.append(f"pengu_banish_string(&{tmp_s});")
                    elif self._is_ref_char_type(t):
                        fmt_parts.append("%s")
                        c_args.append(f"(const char*)({expr_c})")
                    else:
                        raise SemanticError(
                            f"Expression '{expr_str}' of type '{t}' cannot be interpolated into string",
                            help="Interpolate numeric, bool, string, char, or C-string (ref to char) values."
                        )
                else:
                    if expr_str.isdigit():
                        fmt_parts.append("%d")
                        c_args.append(f"(int32_t)({expr_c})")
                    else:
                        raise SemanticError(
                            f"Cannot determine type of interpolated expression '{expr_str}'",
                            help="Ensure expressions interpolated inside strings have known types."
                        )

        full_fmt = "".join(fmt_parts)
        # pengu_string_format_ex copies '%.*s' arguments byte-exactly, so
        # interpolation never truncates a string at an embedded NUL (hash
        # digests, base64/hex decoders, ...).  Scalar specifiers match
        # pengu_string_format exactly.
        fmt_call = f'pengu_string_format_ex("{full_fmt}", {", ".join(c_args)})'
        if postamble_cleanups:
            tmp_res = self.get_temp_name("_fmt")
            body = (f"{' '.join(preamble_decls)} PenguString {tmp_res} = {fmt_call}; "
                    f"{' '.join(postamble_cleanups)} {tmp_res};")
            if not self.use_gnu_extensions:
                for d in preamble_decls:
                    self._hoist(d)
                self._hoist(f"PenguString {tmp_res} = {fmt_call};")
                for cleanup in postamble_cleanups:
                    self._hoist(cleanup)
                return tmp_res
            return f"(__extension__({{ {body} }}))"
        if preamble_decls:
            if not self.use_gnu_extensions:
                for d in preamble_decls:
                    self._hoist(d)
                return fmt_call
            return f"(__extension__({{ {' '.join(preamble_decls)} {fmt_call}; }}))"
        return fmt_call
    @staticmethod
    def _is_side_effect_free(node: Any) -> bool:
        """Returns True if node is syntactically free of side effects."""
        if isinstance(node, Token):
            return True
        if not isinstance(node, Tree):
            return True
        if node.data in ("var_ref", "int_lit", "float_lit", "string_lit", "char_lit", "true_lit", "false_lit", "self_ref"):
            return True
        if node.data in ("field_access", "arrow_access") and node.children:
            base = node.children[0]
            if isinstance(base, Tree) and base.data == "var_ref":
                return True
            if isinstance(base, Token):
                return True
        return False
    @staticmethod
    def _int_interp_spec(t: Optional[Type]) -> tuple:
        """(format specifier, C cast) for interpolating an integer type.

        `%d` with an `int32_t` cast silently truncated `i64`/`u64` values; the
        width and signedness now select the matching specifier and cast.
        """
        u = t
        while isinstance(u, (AliasType, FrozenType, SealType)):
            u = getattr(u, "target", None) or getattr(u, "underlying", None)
        name = getattr(u, "name", "") or ""
        if name in ("u64", "uint64", "uint64_t", "ulong", "usize", "size_t"):
            return "%llu", "unsigned long long"
        if name in ("i64", "int64", "int64_t", "long", "isize", "ssize_t"):
            return "%lld", "long long"
        if name in ("u32", "uint32", "uint32_t", "uint", "u16", "uint16", "uint16_t",
                    "ushort", "u8", "uint8", "uint8_t"):
            return "%u", "uint32_t"
        return "%d", "int32_t"
    @staticmethod
    def _is_single_char_or_byte(t: Optional[Type]) -> bool:
        if t is None:
            return False
        curr = t
        while isinstance(curr, (AliasType, FrozenType, SealType)):
            if isinstance(curr, (AliasType, FrozenType)) and getattr(curr, "target", None):
                curr = curr.target
            elif isinstance(curr, SealType):
                curr = curr.underlying
            else:
                break
        # 'byte' is treated as a character on purpose: the std library (regex,
        # xml, parchment, regulus) composes text from byte values and the
        # language documents that behaviour, so interpolation uses '%c'.
        return isinstance(curr, BaseType) and curr.name in ("char", "byte")
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
