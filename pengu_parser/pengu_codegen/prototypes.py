"""Function prototypes, attributes and the function definitions.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

import os
import re

from ._base import (
    List,
    RefType,
    Token,
    Tree,
)
from .ctype import (
    CTypeMapper,
)

class ProtoMixin:
    """Function prototypes, attributes and the function definitions."""

    def _weave_c_decl(self, w: dict) -> tuple[str, str, str, str]:
        """C declaration (without ``;``) plus the attribute prefixes for a weave.

        Shared by the prototype and definition emitters so the two can never
        drift: a signature mismatch between them is an implicit-declaration or
        conflicting-types failure in the generated C, not a compile-time error
        in the compiler.

        Args:
            w: The collected weave record.

        Returns:
            ``(decl, inline_prefix, noreturn_prefix, actual_c_name)``.
        """
        c_name = w["c_name"]
        param_strs = []

        # Self parameter for enchanting methods (only if not ritual).  A
        # primitive / bare-`shard T` receiver is a value: `int32_t self`, not
        # `int32_t* self`, exactly as C models it.
        if w["enchanted_type"] is not None and not w.get("is_ritual", False):
            self_t_str = CTypeMapper.to_c_type(w["enchanted_type"])
            param_strs.append(
                f"{self_t_str} self" if w.get("self_is_value") else f"{self_t_str}* self"
            )

        for p_info in w["params"]:
            p_name, p_type = p_info[0], p_info[1]
            param_strs.append(CTypeMapper.to_c_decl(p_type, self._c_ident(p_name)))

        params_formatted = ", ".join(param_strs) if param_strs else "void"
        inline_pfx = self._attributes_prefix(w)
        noreturn_pfx = self._noreturn_prefix(w)
        fn_actual_name = "pengu_main" if c_name == "main" else c_name
        decl = CTypeMapper.to_c_decl(w["return_type"], f"{fn_actual_name}({params_formatted})")
        return decl, inline_pfx, noreturn_pfx, fn_actual_name

    def generate_function_prototypes(self) -> str:
        """Generates all forward function prototypes."""
        lines = [
            "/* -------------------------------------------------------------------------",
            " * Function Prototypes",
            " * ------------------------------------------------------------------------- */",
        ]

        for w in self.weaves:
            decl, inline_pfx, noreturn_pfx, _ = self._weave_c_decl(w)
            lines.append(f"{inline_pfx}{noreturn_pfx}{decl};")

        lines.append("")
        return "\n".join(lines)

    def _noreturn_prefix(self, w: dict) -> str:
        """C prefix for a `@noreturn` weave.

        A function specifier must precede the return type, so it cannot ride in
        ``_format_attributes`` (which appends after the declarator).  MSVC spells
        it ``__declspec(noreturn)``; GCC/Clang/TCC accept C11's ``_Noreturn``.
        """
        if "noreturn" not in w.get("attributes", {}):
            return ""
        if self.target_compiler == "msvc":
            return "__declspec(noreturn) "
        return "_Noreturn "

    def _attributes_prefix(self, w: dict) -> str:
        """C prefix and attribute modifiers for a weave, per target compiler.

        GNU/Clang/TCC use ``__attribute__``; MSVC uses ``__declspec`` (and
        ``__forceinline``), since it does not understand GNU attributes.
        """
        return self._format_attributes(w, self.target_compiler == "msvc")
    @staticmethod
    def _format_attributes(w: dict, is_msvc: bool = False) -> str:
        attrs = w.get("attributes", {})
        is_inline = w.get("is_inline", False) or ("inline" in attrs)
        auto_inline = w.get("auto_inline", False)

        parts = []
        c_attrs = []

        if is_inline:
            if is_msvc and not auto_inline:
                parts.append("static __forceinline")
            else:
                # The checker promotes small non-recursive weaves to `static
                # inline`, and DCE keeps a module's public entry points even
                # when the program never calls them. Clang's
                # `-Wunused-function` treats an unreferenced `static inline`
                # as a warning, and `-Werror` would reject a valid program;
                # `PENGU_MAYBE_UNUSED` is empty on MSVC and `unused` on
                # GNU/Clang. Explicit `inline weave` gets the same treatment
                # because an unreferenced one is dead code, not a mistake.
                parts.append("PENGU_MAYBE_UNUSED static inline")
                if not auto_inline:
                    c_attrs.append("always_inline")

        if "cold" in attrs and not is_msvc:
            # MSVC has no direct equivalent of __attribute__((cold)).
            c_attrs.append("cold")
        if "deprecated" in attrs:
            reason = attrs["deprecated"][0] if attrs["deprecated"] else None
            if reason:
                clean_reason = str(reason).replace('"', '\\"')
                dep = f'deprecated("{clean_reason}")'
            else:
                dep = "deprecated"
            if is_msvc:
                parts.append(f"__declspec({dep})")
            else:
                c_attrs.append(dep)

        if c_attrs:
            parts.append(f"__attribute__(({', '.join(c_attrs)}))")

        if not parts:
            return ""
        return " ".join(parts) + " "
    @staticmethod
    def _inline_prefix(w: dict) -> str:
        """GNU attribute prefix for a weave (kept for backwards compatibility)."""
        # Local import: the mixin modules must not import the assembled class at
        # module level, or `main` would be imported while it is still building.
        from .main import PenguCodegen
        return PenguCodegen._format_attributes(w, is_msvc=False)
    @staticmethod
    def _referenced_names(body_stmts) -> set:
        """Names a function body actually mentions in the generated C.

        Used to decide which parameters need a ``(void)name;`` to silence
        ``-Wunused-parameter``.  The scan is deliberately conservative — a name
        it cannot see through (an interpolation's ``{expr}`` text, a lambda body
        that shadows it) counts as *used*, so the compiler only adds the cast
        where the parameter is provably invisible to C.

        Args:
            body_stmts: The statements of the function body.

        Returns:
            The set of identifier names referenced anywhere in the body.
        """
        used: set = set()

        def note_token(token) -> None:
            if isinstance(token, Token) and token.type == "NAME":
                used.add(str(token))

        def walk(node) -> None:
            if isinstance(node, Token):
                return
            if not isinstance(node, Tree):
                return
            if node.data == "type_of":
                # `type of expr` inspects its operand's static type and emits a
                # string literal: nothing inside the operand reaches the C.
                return
            if node.data in ("var_ref", "self_ref") and node.children:
                note_token(node.children[0])
            elif node.data == "normal_target" and node.children:
                # A call/assignment target is a bare NAME (a parameter called as
                # a function pointer, or `set param is …`), not a var_ref.
                note_token(node.children[0])
            elif node.data in ("string_lit", "interpolated_string"):
                # Interpolations are re-parsed at codegen time, so their operand
                # names live in the literal's text rather than in the tree.
                text = " ".join(str(c) for c in node.children)
                for match in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", text):
                    used.add(match.group(0))
            for child in node.children:
                walk(child)

        for stmt in body_stmts or []:
            walk(stmt)
        return used

    @staticmethod
    def _local_declaration_names(body_stmts) -> set:
        """Names of the local bindings a function body declares.

        Covers `var`, `let`, `static var`, `const` (a function-local constant is
        emitted as a static local) and the destructuring forms, which carry a
        `var_name_list`.

        Args:
            body_stmts: The statements of the function body.

        Returns:
            The declared names.
        """
        names: set = set()

        def walk(node) -> None:
            if isinstance(node, Token) or not isinstance(node, Tree):
                return
            if node.data in ("var_decl", "let_decl", "static_var_decl", "const_decl") and node.children:
                first = node.children[0]
                if isinstance(first, Tree) and first.data == "var_name_list":
                    for tok in first.children:
                        names.add(str(tok))
                elif not isinstance(first, Tree):
                    names.add(str(first))
            for child in node.children:
                walk(child)

        for stmt in body_stmts or []:
            walk(stmt)
        return names

    def _unused_local_names(self, body_stmts) -> set:
        """C identifiers of the locals a body declares but never uses in C.

        Emitting ``(void)name;`` right after such a declaration keeps the bundle
        clean under ``-Wall -Wextra`` (`-Wunused-variable`,
        `-Wunused-but-set-variable`) without changing behaviour.  A binding that
        is only read by ``type of`` counts as unused, because its value never
        reaches the generated C.

        Args:
            body_stmts: The statements of the function body.

        Returns:
            The C identifiers to void.
        """
        declared = self._local_declaration_names(body_stmts)
        used = self._referenced_names(body_stmts)
        return {self._c_ident(n) for n in declared if n not in used}

    def _unused_parameter_names(self, w, body_stmts) -> list:
        """C identifiers of the parameters (and receiver) a body never reads.

        Emitting ``(void)name;`` for them keeps the generated C clean under
        ``-Wall -Wextra -Werror`` without changing behaviour: the cast is a
        no-op statement.  ``antiquus`` bodies are literal C and are left alone,
        and a parameter whose value the code generator injects implicitly (the
        receiver of an ``enchanting`` method) is never "removed" — the cast is
        merely a hint to the C compiler.

        Args:
            w: The collected weave record.
            body_stmts: The statements of its body.

        Returns:
            The C identifiers to void, in declaration order.
        """
        if w.get("c_body") is not None:
            return []
        used = self._referenced_names(body_stmts)
        names = []
        if w["enchanted_type"] is not None and not w.get("is_ritual", False):
            names.append("self")
        names.extend(p_info[0] for p_info in w["params"])
        unused = [self._c_ident(name) for name in names if name not in used]
        return unused

    def generate_function_definitions(self, weaves=None) -> str:
        """Generates function bodies, reusing the discovery cache when present.

        Phase 1 translates every reachable weave once, during reachability
        discovery, and caches the text.  Reusing that cache here is what keeps
        the emitted C identical to what the discovery pass inspected: a second
        translation would be observable (fresh temporaries, different
        counters) and could disagree with the prototype set.

        Args:
            weaves: Optional explicit weave list (tests / callers that already
                filtered the list).  Defaults to ``self.weaves``.
        """
        lines = [
            "/* -------------------------------------------------------------------------",
            " * Function Definitions",
            " * ------------------------------------------------------------------------- */",
        ]

        for w in (self.weaves if weaves is None else weaves):
            text = self._definition_cache.get(w["c_name"])
            if text is None:
                text = self._generate_one_definition(w)
                self._definition_cache[w["c_name"]] = text
            lines.append(text)

        return "\n".join(lines)

    def _generate_one_definition(self, w: dict) -> str:
        """Emits the C definition of one weave (without the section header).

        Extracted from :meth:`generate_function_definitions` so the reachability
        pass can translate a body *before* deciding whether it will be emitted.
        All generator state a body can touch is saved and restored around the
        call, so translating a weave is independent of translation order.

        Args:
            w: The collected weave record.

        Returns:
            The C definition text, including its ``#line`` marker.
        """
        lines: List[str] = []
        self._apply_main_flag(w.get("filepath"))
        self.current_source_file = w.get("filepath")
        previous_module = (self.symbols.current_module if self.symbols else None)
        if self.symbols and w.get("filepath"):
            try:
                self.symbols.current_module = os.path.normcase(
                    os.path.abspath(w["filepath"]))
            except (OSError, ValueError):  # pragma: no cover
                pass
        decl, inline_pfx, noreturn_pfx, fn_actual_name = self._weave_c_decl(w)

        marker = self._line_marker(w.get("line"), w.get("filepath"))
        if marker:
            lines.append(marker)

        c_body = w.get("c_body")
        if c_body is not None:
            # `antiquus`: the body is literal C written by the user.  It is
            # emitted verbatim, with no frame push/pop and no implicit
            # return.  The `#line` directives name the antiquus instead of
            # the bundle, so a C diagnostic inside the body points at
            #     antiquus:<name>:<line>
            # which is unambiguous and easy to grep.
            lines.append(f"{inline_pfx}{noreturn_pfx}{decl} {{")
            if self.emit_line_markers:
                lines.append(f'#line 1 "antiquus:{fn_actual_name}"')
            lines.append(c_body if c_body else f"/* antiquus {fn_actual_name}: empty C body */")
            restore = self._line_marker((w.get("line") or 1) + 1, w.get("filepath"))
            if restore:
                lines.append(restore)
            lines.append("}")
            lines.append("")
            return "\n".join(lines)

        lines.append(f"{inline_pfx}{noreturn_pfx}{decl} {{")
        self.indent_level += 1
        # A generic instantiation may be generated *while* an enclosing
        # function body is being translated (first call site wins).  The
        # generator keeps function-scoped state on `self`, so save it and
        # restore it at the end: without this, the instantiated body saw the
        # enclosing function's `local_vars` and resolved, for example,
        # `.first` to an unrelated local rune named `first`.  That produced a
        # wrong `sizeof` in `memcpy` and the oracle bundle warned under
        # -Wstringop-overflow.
        saved_gen_state = (
            dict(self.local_vars),
            self.current_function,
            self.current_return_type,
            self.current_enchanted_type,
            dict(getattr(self, "current_subst_map", {}) or {}),
            getattr(self, "current_self_is_value", False),
            list(getattr(self, "with_stack", []) or []),
            list(getattr(self, "with_type_stack", []) or []),
            getattr(self, "_void_locals", set()),
            set(getattr(self, "current_param_names", set())),
        )
        push_path = self._display_path(w.get("filepath")) or ""
        push_line = w.get("line") or 0
        lines.append(f'{self.indent()}pengu_frame_push("{fn_actual_name}", "{push_path}", {push_line});')
        self.current_function = fn_actual_name
        self.current_return_type = w["return_type"]
        self.current_enchanted_type = w.get("enchanted_type")
        self.current_subst_map = w.get("subst_map", {})
        self.local_vars = {}
        self.current_param_names = {p_info[0] for p_info in w["params"]}
        # A generic instantiation may be emitted from inside an enclosing
        # `with:` block; the new function starts with no with-context, or
        # its `.field` targets would resolve against the caller's target.
        self.with_stack = []
        self.with_type_stack = []
        # Value-vs-reference receiver comes from the collected declaration
        # (see `_collect_weave`), never from the type alone: `enchanting int:`
        # is a value, `bind int with Ordered:` is a pointer.
        self.current_self_is_value = bool(w.get("self_is_value"))
        if w["enchanted_type"] is not None and not w.get("is_ritual", False):
            # Value receiver (primitive / bare `shard T`): `self` is the value
            # itself, so `calling self.other_method` passes it by value and
            # `self % 2` is plain C arithmetic, not a pointer deref.
            if self.current_self_is_value:
                self.local_vars["self"] = w["enchanted_type"]
            else:
                self.local_vars["self"] = RefType(w["enchanted_type"])
        for p_info in w["params"]:
            self.local_vars[p_info[0]] = p_info[1]

        self.defer_stack.append([])
        self.errdefer_stack.append([])

        # Implicit return (guide §4.11): when the body's last statement is a
        # value expression and the weave returns a non-void type, that value
        # is the result.  Translating it as a real ``return_stmt`` gives the
        # same cleanup handling as an explicit ``return``.
        body_stmts = w["body_stmts"]
        # Parameters the body never mentions: one `(void)name;` each, so the
        # bundle is clean under `-Wextra -Werror` (`type of p` is exactly
        # such a case: the operand is inspected, never emitted).
        for unused_param in self._unused_parameter_names(w, body_stmts):
            lines.append(f"{self.indent()}(void){unused_param};")
        self._void_locals = self._unused_local_names(body_stmts)
        tail_expr = self._implicit_return_expr(body_stmts, w.get("return_type"))
        if tail_expr is not None:
            body_code = self._translate_block(body_stmts[:-1])
            lines.append(body_code)
            lines.append(self._translate_stmt(Tree("return_stmt", [tail_expr],
                                                   meta=getattr(tail_expr, "meta", None))))
        else:
            body_code = self._translate_block(body_stmts)
            lines.append(body_code)

        # Emit any remaining top-level defers before function exit.
        active_defers = self.defer_stack.pop() if self.defer_stack else []
        if self.errdefer_stack:
            self.errdefer_stack.pop()
        # With a synthesized implicit return the deferred cleanup is already
        # emitted *inside* the return statement; emitting it again here would
        # double-free.
        body_is_jump = self._stmts_end_with_jump(w["body_stmts"])
        if tail_expr is None and not body_is_jump:
            if active_defers:
                lines.append(f"{self.indent()}/* Deferred cleanup */")
                for d in reversed(active_defers):
                    lines.append(self._format_defer_cleanup(d, self.indent()))

        # The trailing pop is the fall-through exit.  Every `return` already
        # emits its own `pengu_frame_pop()` (see `return_stmt` in stmts.py),
        # so appending one after a jump only creates unreachable code -- and
        # unreachable *calls* after a `return` make gcc report a spurious
        # "-Wreturn-type: control reaches end of non-void function" for the
        # whole bundle when it is compiled at -O0 with -fsanitize=address.
        if tail_expr is None and not body_is_jump:
            lines.append(f"{self.indent()}pengu_frame_pop();")
        self.indent_level -= 1
        lines.append("}")
        lines.append("")
        (self.local_vars, self.current_function, self.current_return_type,
         self.current_enchanted_type, self.current_subst_map,
         self.current_self_is_value, self.with_stack,
         self.with_type_stack, self._void_locals,
         self.current_param_names) = saved_gen_state
        return "\n".join(lines)
