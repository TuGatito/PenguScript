"""String literals and `{expr}` interpolation.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    AliasType,
    Any,
    BaseType,
    FrozenType,
    List,
    Optional,
    RefType,
    SealType,
    SemanticError,
    Token,
    Tree,
    Type,
    re,
)

class InterpMixin:
    """String literals and `{expr}` interpolation."""

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

        has_expr = any(p.is_expr for p in parts)
        decoded_parts = [self._decode_literal(p.text, is_raw) for p in parts]
        if as_c_literal:
            if has_expr:
                raise SemanticError("String interpolation is not supported when expecting a C string literal (ref to char)")
            full_bytes = b"".join(decoded_parts)
            return '"' + self._c_escape_bytes(full_bytes) + '"'

        if not has_expr:
            full_bytes = b"".join(decoded_parts)
            literal = self._c_escape_bytes(full_bytes)
            # Keep the borrowed static view spelling for ordinary literals
            # (many code-shape tests and docs quote it); only the NUL-bearing
            # case needs the explicit-length constructor, because strlen would
            # truncate there.
            if 0 in full_bytes:
                return f'pengu_string_from_cstr_len("{literal}", {len(full_bytes)})'
            return f'pengu_string_from_cstr("{literal}")'
        if not hasattr(self, "_expr_parser"):
            self._expr_parser = PenguParser()
        parser = self._expr_parser
        fmt_parts = []
        c_args = []
        preamble_decls = []
        postamble_cleanups = []
        for p, decoded in zip(parts, decoded_parts):
            if not p.is_expr:
                if b"\x00" in decoded:
                    raise SemanticError(
                        "A NUL byte cannot appear in the literal part of an interpolated string",
                        code="E0019",
                        help="Build the value with 'pengu_string_format_ex' over a non-NUL format, or concatenate at runtime.",
                        note="C format strings are NUL-terminated; the compiler rejects this instead of truncating silently.",
                    )
                fmt_parts.append(self._c_escape_bytes(decoded, for_format=True))
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
    def _decode_literal(text: str, is_raw_lit: bool) -> bytes:
        """Decodes a string literal body to its exact byte sequence.

        This happens *before* C generation on purpose: ``\\xNN`` is a byte,
        not a Unicode code point, and the C compiler must never decide
        where the escape ends (``"\\x41B"`` means 0x41B to a C compiler,
        not ``A`` followed by ``B``).  ``\\x00`` also has to survive: the
        old path emitted a NUL into a `pengu_string_from_cstr` literal and
        strlen truncated the value to zero bytes.
        """
        if is_raw_lit:
            return text.encode("utf-8")
        out = bytearray()
        i = 0
        n = len(text)
        simple = {
            "n": 0x0A, "r": 0x0D, "t": 0x09, "b": 0x08,
            "f": 0x0C, "v": 0x0B, "a": 0x07, "\\": 0x5C,
            '"': 0x22, "'": 0x27, "?": 0x3F,
        }
        while i < n:
            ch = text[i]
            if ch != "\\":
                out.extend(ch.encode("utf-8"))
                i += 1
                continue
            if i + 1 >= n:
                out.append(0x5C)
                break
            nxt = text[i + 1]
            if text.startswith("\\u{", i):
                close_b = text.find("}", i + 3)
                if close_b != -1:
                    try:
                        cp = int(text[i + 3:close_b], 16)
                        out.extend(chr(cp).encode("utf-8"))
                        i = close_b + 1
                        continue
                    except (ValueError, OverflowError):
                        pass
            if nxt == "u" and i + 5 < n:
                hex_str = text[i + 2:i + 6]
                if all(c in "0123456789abcdefABCDEF" for c in hex_str):
                    try:
                        cp = int(hex_str, 16)
                        out.extend(chr(cp).encode("utf-8"))
                        i += 6
                        continue
                    except (ValueError, OverflowError):
                        pass
            if nxt in ("x", "X"):
                j = i + 2
                digits = ""
                while j < n and len(digits) < 2 and text[j] in "0123456789abcdefABCDEF":
                    digits += text[j]
                    j += 1
                if digits:
                    out.append(int(digits, 16) & 0xFF)
                    i = j
                    continue
            if nxt in "01234567":
                j = i + 1
                digits = ""
                while j < n and len(digits) < 3 and text[j] in "01234567":
                    digits += text[j]
                    j += 1
                if digits == "":
                    out.append(0)
                    i += 2
                    continue
                out.append(int(digits, 8) & 0xFF)
                i = j
                continue
            code = simple.get(nxt)
            if code is not None:
                out.append(code)
                i += 2
                continue
            # Unknown escape: preserve the backslash and the character as
            # data.  The C emitter will escape the backslash, so the
            # generated literal still contains exactly what was written.
            out.append(0x5C)
            out.extend(nxt.encode("utf-8"))
            i += 2
        return bytes(out)

    @staticmethod
    def _c_escape_bytes(data: bytes, for_format: bool = False) -> str:
        """Renders decoded bytes as the contents of a C string literal."""
        out = []
        for b in data:
            if b == 0x22:
                out.append('\\"')
            elif b == 0x5C:
                out.append("\\\\")
            elif b == 0x0A:
                out.append("\\n")
            elif b == 0x0D:
                out.append("\\r")
            elif b == 0x09:
                out.append("\\t")
            elif b == 0x08:
                out.append("\\b")
            elif b == 0x0C:
                out.append("\\f")
            elif 0x20 <= b <= 0x7E:
                ch = chr(b)
                if for_format and ch == "%":
                    out.append("%%")
                else:
                    out.append(ch)
            else:
                # Three-digit octal escapes are self-delimiting: unlike
                # \\xNN they cannot absorb a following hex digit.
                out.append("\\%03o" % b)
        return "".join(out)

    def _translate_string_value(self, s_val: Any) -> str:
        """C expression for a string literal/constant, preserving NUL bytes.

        Constants and folded literals go through the same escape decoder as
        ordinary literals, so ``const Z as string is "\x00"`` is a one-byte
        value rather than an empty `strlen` view.
        """
        from pengu_parser.pengu_parser import extract_string_parts

        text = str(s_val)
        is_raw, _is_triple, parts = extract_string_parts(text)
        if any(p.is_expr for p in parts):
            return self._translate_string_lit(text)
        data = b"".join(self._decode_literal(p.text, is_raw) for p in parts)
        literal = self._c_escape_bytes(data)
        if 0 in data:
            return f'pengu_string_from_cstr_len("{literal}", {len(data)})'
        return f'pengu_string_from_cstr("{literal}")'

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
        # 'byte' is treated as a character on purpose: the std library composes
        # text from byte values and the language documents that behaviour, so
        # interpolation uses '%c'.
        return isinstance(curr, BaseType) and curr.name in ("char", "byte")
    def _expr_allocates_string(self, node: Any) -> bool:
        """True when an interpolated expression allocates a fresh PenguString.

        Only fresh producers may be released by the interpolation temporary:
        a field access, parameter or call result may be a view whose buffer
        belongs to someone else.
        """
        if not isinstance(node, Tree):
            return False
        # Mirror the constant folding performed by _translate_expr: a folded
        # string lowers to pengu_string_from_cstr(...), i.e. a static '.rodata'
        # view that must NOT be released by the interpolation temporary.
        # '(chr 65)' folds to "A" through the paren wrapper, while a bare
        # 'chr n' is excluded from folding and stays a fresh allocation.
        if node.data not in ("string_lit", "interpolated_string"):
            try:
                folded = self.const_folder.fold(node)
            except Exception:
                folded = None
            if isinstance(folded, str) and node.data not in ("add", "chr_expr"):
                return False
        # Look through grouping wrappers: the interpolation expression is
        # re-parsed, so '(n to string)' arrives as paren_expr(to_expr(...)).
        while (isinstance(node, Tree) and node.data in ("paren_expr", "value_expr", "expr")
               and len(node.children) == 1):
            node = node.children[0]
        if not isinstance(node, Tree):
            return False
        if node.data in ("to_expr", "cast_expr"):
            target = node.children[1] if len(node.children) >= 2 else None
            if target is None:
                return False
            is_string_target = False
            stack = [target]
            while stack:
                cur = stack.pop()
                if isinstance(cur, Token):
                    if str(cur) == "string":
                        is_string_target = True
                        break
                    continue
                if isinstance(cur, Tree):
                    stack.extend(cur.children)
            if not is_string_target:
                return False
            # 'x to string' with 'x' already a string is the identity: the value
            # reuses x's buffer, so releasing it would free memory it does not own.
            # 'bool to string' is also NOT owned: pengu_string_from_bool returns
            # a static '.rodata' view ("true"/"false") and the runtime header
            # documents banishing it as undefined behaviour.
            operand_t = self._infer_node_type(node.children[0]) if node.children else None
            while (isinstance(operand_t, (AliasType, FrozenType))
                   and getattr(operand_t, "target", None)):
                operand_t = operand_t.target
            if isinstance(operand_t, BaseType) and operand_t.name in ("string", "bool"):
                return False
            return True
        if node.data == "chr_expr":
            return True
        if node.data in ("if_stmt", "unless_stmt", "do_expr"):
            # A value block is fresh only when *every* branch produces a fresh
            # string: a branch yielding a parameter or a field view aliases
            # storage that another name owns and must never be released.
            return self._block_value_is_fresh_string(node)
        if node.data == "string_lit" and node.children:
            from pengu_parser.pengu_parser import extract_string_parts
            try:
                _raw, _triple, parts = extract_string_parts(str(node.children[0]))
                return any(getattr(p, "is_expr", False) for p in parts)
            except Exception:
                return False
        return False
    def _block_value_is_fresh_string(self, node: Any, _depth: int = 0) -> bool:
        """True when every value of a 'do:'/'if' block is a fresh string.

        Used by the interpolation temporary cleanup: a single non-fresh branch
        (a parameter, a field view) makes the whole expression non-owned.
        """
        if not isinstance(node, Tree) or _depth > 16:
            return False
        branches: List[Any] = []
        if node.data == "do_expr":
            branches = [node]
        elif node.data in ("if_stmt", "unless_stmt"):
            for branch in node.children[1:]:
                if isinstance(branch, Tree):
                    branches.append(branch)
            if not branches:
                return False
        else:
            return False

        seen_value = False
        for branch in branches:
            if branch.data in ("block", "else_block", "when_else_plain", "when_else_when"):
                stmts = [c for c in branch.children if isinstance(c, Tree)]
            else:
                stmts = [branch]
            value = self._block_last_value_node(stmts)
            if value is None:
                return False
            seen_value = True
            if not self._expr_allocates_string(value):
                return False
        return seen_value
    def _to_string_call(self, expr_code: str, t: Optional[Type]) -> str:
        """Converts a value to ``PenguString`` without the C11 ``_Generic`` macro.

        The code generator always knows the static type, so it can call the
        concrete ``pengu_string_from_*`` producer directly.  This keeps the
        emitted C free of ``_Generic`` (roadmap 2.2.e) and therefore compilable
        as C99; the macro survives only as a host-C convenience, guarded on
        ``__STDC_VERSION__ >= 201112L``.
        """
        u = self._unwrap_owned_type(t)
        if isinstance(u, BaseType):
            if u.name == "string":
                return expr_code
            if u.name == "bool":
                return f"pengu_string_from_bool({expr_code})"
            if u.name == "char":
                return f"pengu_string_from_char({expr_code})"
            if u.name in ("float", "f32", "f64", "double"):
                return f"pengu_string_from_float({expr_code})"
            return f"pengu_string_from_int((int64_t)({expr_code}))"
        if isinstance(u, RefType):
            pointee = self._unwrap_owned_type(getattr(u, "target", None))
            if isinstance(pointee, BaseType) and pointee.name in ("char", "byte"):
                return f"pengu_string_from_cstr((const char *)({expr_code}))"
        # Concrete type the mapper does not specialise (rune, omen, …): the
        # numeric producer is the only sensible fallback, and using it keeps
        # the bundle free of _Generic.
        return f"pengu_string_from_int((int64_t)({expr_code}))"
