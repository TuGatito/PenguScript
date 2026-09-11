"""pengu_bind: translate a C header (.h) into a PenguScript .d.pengu binding.

Strategy:
  1. Preprocess the header with the C preprocessor (gcc) using an optional
     extra include-path set and a small vendored stub include tree
     (``c_bind_stubs/``) so system headers resolve without dragging platform
     SDKs into the parse. The Windows/SDK guarded sections can be excluded by
     undefining their guard macros (``-U_WIN32`` etc. by default), keeping the
     header self-contained and parseable by pycparser.
  2. Parse the preprocessed text with pycparser (line markers are retained so
     each node keeps its origin file; nodes from stub/system headers are
     skipped).
  3. Extract ``#define`` object-like integer/string macros from the *original*
     header text (preprocessing removes them from the AST).
  4. Extract documentation comments from the original source lines preceding
     each declaration and attach them as ``##`` doc comments.
  5. Walk the AST and emit, in order:
       - const lines (numeric/string #define macros),
       - rune (struct) / echo (union) / omen (enum) declarations,
       - alias lines (simple typedefs and callback/function-pointer typedefs),
       - the ``insignia <prefix>`` directive (when a prefix is given),
       - declare lines for every function.
  6. ``include "<header>"`` and ``link "..."`` lines are emitted at the top.

The generated file is a declaration file: it only *declares* the native
surface. The real C header is ``include``d, so the compiler sees the actual
definitions and never emits conflicting struct/enum/prototype C.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Set, Tuple, Union

try:
    from pycparser import c_ast, c_parser
except Exception:  # pragma: no cover - pycparser is optional at import time
    c_ast = None
    c_parser = None

# --------------------------------------------------------------------------
# C <-> PenguScript type tables
# --------------------------------------------------------------------------

_PRIMITIVES: Dict[str, str] = {
    "int": "int",
    "signed int": "int",
    "unsigned int": "u32",
    "unsigned": "u32",
    "long": "i64",
    "long int": "i64",
    "signed long": "i64",
    "unsigned long": "u64",
    "long long": "i64",
    "long long int": "i64",
    "signed long long": "i64",
    "unsigned long long": "u64",
    "long long unsigned int": "u64",
    "unsigned long long int": "u64",
    "short": "i16",
    "short int": "i16",
    "unsigned short": "u16",
    "unsigned short int": "u16",
    "char": "char",
    "signed char": "char",
    "unsigned char": "byte",
    "float": "f32",
    "double": "f64",
    "long double": "f64",
    "bool": "bool",
    "_Bool": "bool",
    "void": "void",
    "size_t": "size_t",
    "ssize_t": "isize",
    "ptrdiff_t": "isize",
    "wchar_t": "i32",
    "int8_t": "i8",
    "uint8_t": "byte",
    "int16_t": "i16",
    "uint16_t": "u16",
    "int32_t": "int",
    "uint32_t": "u32",
    "int64_t": "i64",
    "uint64_t": "u64",
    "intptr_t": "isize",
    "uintptr_t": "usize",
    "intmax_t": "i64",
    "uintmax_t": "u64",
    # <stdarg.h> / compiler builtins that survive preprocessing.
    "va_list": "va_list",
    "__builtin_va_list": "va_list",
    "__gnuc_va_list": "va_list",
}

_C_STD_FILES = {
    "ctype.h", "errno.h", "inttypes.h", "math.h", "stdbool.h", "stddef.h",
    "stdint.h", "stdio.h", "stdlib.h", "string.h", "time.h", "stdarg.h",
    "assert.h", "limits.h", "wchar.h", "stdalign.h", "stdatomic.h",
}


class HeaderParseError(RuntimeError):
    """Raised when the C header cannot be preprocessed or parsed."""


class BindGenerator:
    """Converts a parsed pycparser AST into .d.pengu declaration text."""

    def __init__(
        self,
        header_path: str,
        prefix: str = "",
        links: Optional[List[str]] = None,
        ignore: Optional[List[str]] = None,
        include_paths: Optional[List[str]] = None,
        use_cpp: bool = True,
        header_include: Optional[str] = None,
        no_comments: bool = False,
        stub_dir: Optional[str] = None,
    ):
        self.header_path = os.path.abspath(header_path)
        self.prefix = prefix
        self.links = list(links or [])
        self.ignore = list(ignore or [])
        self.include_paths = list(include_paths or [])
        self.use_cpp = use_cpp
        self.header_include = header_include or os.path.basename(self.header_path)
        self.no_comments = no_comments
        self.stub_dir = stub_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "c_bind_stubs")
        self.lines: List[str] = []
        self.warnings: List[str] = []
        self.known_type_names: Set[str] = set(_PRIMITIVES)
        self.emitted_names: Set[str] = set()
        self._alias_counter = 0
        # Callback aliases discovered while translating a signature are queued
        # and flushed *before* the declaration that needs them: emitting them
        # where they are found would put them inside a 'rune' body.
        self._pending_aliases: List[str] = []

    # ------------------------------------------------------------ helpers

    def _warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def _doc_lines(self, comment: Optional[str]) -> List[str]:
        """Flattens a C comment block into PenguScript single-line comments.

        A multi-line C comment (``/* … */``) or a run of ``//`` lines becomes one
        ``# …`` line per source line: PenguScript has no block comments, so the
        text has to be re-emitted line by line. Comment markers, decoration
        (``*`` gutters, ``#`` doc markers) and trailing whitespace are stripped.

        Args:
            comment: Raw comment text collected next to a declaration.

        Returns:
            One entry per emitted comment line (empty for blank lines).
        """
        if self.no_comments or not comment:
            return []
        out: List[str] = []
        for raw in comment.splitlines():
            line = raw.strip()
            line = re.sub(r"^/\*+", "", line)
            line = re.sub(r"\*+/$", "", line)
            line = re.sub(r"^\*+", "", line).strip()
            line = re.sub(r"^//+", "", line).strip()
            line = re.sub(r"^[!/]+", "", line).strip()
            line = re.sub(r"^##*", "", line).strip()
            out.append(line)
        # Drop leading/trailing blank decoration lines.
        while out and not out[0]:
            out.pop(0)
        while out and not out[-1]:
            out.pop()
        return out

    def _emit_doc(self, comment: Optional[str]) -> None:
        for line in self._doc_lines(comment):
            self.lines.append(f"# {line}" if line else "#")

    def _record_type(self, name: str) -> None:
        self.known_type_names.add(name)

    # ------------------------------------------------- type name mapping

    @staticmethod
    def _is_const(node) -> bool:
        """True when a pycparser declarator carries the ``const`` qualifier."""
        quals = getattr(node, "quals", None) or []
        return "const" in quals

    def c_type(self, tnode, fallback: str = "opaque") -> Tuple[str, Optional[str]]:
        """Maps a pycparser type node to a PenguScript type string.

        Returns (pengu_type, callback_alias_or_None). The callback alias is set
        when the node is (a pointer to) a function type that needs a dedicated
        'alias ... as ref to weave' declaration.

        ``const`` becomes ``frozen`` (PenguScript's spelling of C's qualifier):
        ``const T`` → ``frozen T`` and ``const T*`` → ``ref to frozen T``. A
        *const pointer* (``T* const p``) is dropped, because that is what
        ``let`` already expresses (``frozen`` always qualifies the pointee).
        """
        if tnode is None:
            return fallback, None
        # TypeDecl: unwrap qualifiers/name to inner type
        if isinstance(tnode, c_ast.TypeDecl):
            inner, cb = self.c_type(tnode.type, fallback=fallback)
            if cb is not None:
                return cb, None
            if self._is_const(tnode) and not inner.startswith(("frozen ", "ref to frozen ")):
                return f"frozen {inner}", None
            return inner, None
        if isinstance(tnode, c_ast.PtrDecl):
            inner, cb = self.c_type(tnode.type, fallback=fallback)
            if cb is not None:
                return cb, None  # pointer-to-function already an alias
            if inner == "void":
                return "ref to void", None
            # 'const' on the pointee is preserved by c_type above; it shows up
            # here as 'frozen …' and must not be qualified twice.
            if inner.startswith("ref to"):
                return f"ref to {inner}", None
            return f"ref to {inner}", None
        if isinstance(tnode, c_ast.ArrayDecl):
            inner, cb = self.c_type(tnode.type, fallback=fallback)
            if cb is not None:
                return f"ref to {cb}", None
            return inner, None  # arrays decay to plain element type
        if isinstance(tnode, c_ast.FuncDecl):
            alias = self._callback_alias(tnode)
            return alias, alias
        if isinstance(tnode, c_ast.IdentifierType):
            name = " ".join(str(x) for x in tnode.names)
            mapped = _PRIMITIVES.get(name)
            if mapped is not None:
                return mapped, None
            self._record_type(name)
            return name, None
        if isinstance(tnode, (c_ast.Struct, c_ast.Union, c_ast.Enum)):
            tag = getattr(tnode, "name", None)
            if tag:
                self._record_type(tag)
                return tag, None
            return fallback, None
        if isinstance(tnode, c_ast.Enum):
            tag = getattr(tnode, "name", None)
            if tag:
                self._record_type(tag)
                return tag, None
            return "int", None
        if isinstance(tnode, (c_ast.IdentifierType,)):
            return str(tnode), None
        return fallback, None

    def _callback_alias(self, func: c_ast.FuncDecl) -> str:
        """Registers an alias for an inline function-pointer type.

        The alias line is queued (see :meth:`_flush_aliases`) so it is emitted
        before the declaration that uses it rather than in the middle of a
        struct body.
        """
        self._alias_counter += 1
        name = f"Callback{self._alias_counter}"
        params = self._func_params(func, name=name, c_variadic=False, for_callback=True)
        ret = self._func_return(func)
        if params:
            self._pending_aliases.append(f"alias {name} as ref to weave with {params} into {ret}")
        else:
            self._pending_aliases.append(f"alias {name} as ref to weave into {ret}")
        self.known_type_names.add(name)
        return name

    def _flush_aliases(self) -> None:
        """Emits the queued callback aliases (one per line, blank-separated)."""
        for line in self._pending_aliases:
            self.lines.append(line)
            self.lines.append("")
        self._pending_aliases.clear()

    # ------------------------------------------- function signature pieces

    def _func_params(self, func: c_ast.FuncDecl, name: str = "", c_variadic: bool = True,
                     for_callback: bool = False) -> str:
        """Formats the parameter list of a C function as PenguScript.

        Args:
            func: The C function declaration.
            name: Function name, used in warnings.
            c_variadic: True to keep a trailing `...` (declare), False for
                callback aliases, which cannot be C-variadic.
            for_callback: True when the result goes into a callback alias, whose
                grammar rejects parameters named like a type.

        Returns:
            The comma-separated parameter list.
        """
        parts: List[str] = []
        if func.args is not None and func.args.params:
            for i, p in enumerate(func.args.params):
                if isinstance(p, c_ast.EllipsisParam):
                    if c_variadic:
                        parts.append("...")
                    else:
                        self._warn(f"function '{name}': variadic '...' parameters are dropped")
                    continue
                p_name = getattr(p, "name", None)
                if p_name is None:
                    p_name = f"p{i}"
                p_t, _ = self.c_type(p.type, fallback="opaque")
                if p_t == "void":
                    continue
                p_name = self._sanitize_param(p_name, for_callback=for_callback)
                parts.append(f"{p_name} as {p_t}")
        return ", ".join(parts)

    # Parameter names that cannot be spelled in a PenguScript signature: `self`
    # is the implicit receiver of an `enchanting` method and `type` is reserved
    # in type position, so a C parameter with either name would produce a
    # signature the parser rejects. Everything else is kept verbatim on purpose:
    #   * no other name breaks a `declare` signature (checked against every
    #     keyword, e.g. `declare f with size as i32 into void` parses);
    #   * a few names (`size`, `bytes`, `some`, `do`, `static`) only fail as
    #     *named arguments* (`calling f with size is 1`), which is a spelling the
    #     caller chooses — renaming the parameter would silently change the
    #     generated API and break existing bindings;
    #   * struct members are never sanitized (see `_emit_struct`).
    _PENGU_RESERVED: Set[str] = {"self", "type"}

    # Callback signatures (`alias Cb as ref to weave with …`) are stricter than
    # `declare … with …`: there a parameter name that the lexer reads as the
    # start of a *type* is a syntax error (`with opaque as voidpf`, `with int as
    # x`, `with void as p` all fail), so those names get an underscore inside
    # callback aliases only. Renaming them is harmless: a callback alias's
    # parameter names are documentation, not an API the caller spells out.
    _PENGU_CALLBACK_RESERVED: Set[str] = _PENGU_RESERVED | {
        "opaque", "void", "int", "i32", "i64", "float", "f32", "f64", "bool",
        "string", "char", "byte", "u8", "i8", "u16", "i16", "u32", "u64",
        "usize", "isize", "null",
    }

    @classmethod
    def _sanitize_param(cls, name: str, for_callback: bool = False) -> str:
        """Returns the PenguScript spelling of a C parameter name.

        Args:
            name: Raw C parameter name.
            for_callback: True when the name is going into a callback alias
                (`ref to weave with …`), whose grammar is stricter.

        Returns:
            The name, prefixed with ``_`` when it cannot be spelled as-is.
        """
        name = str(name)
        reserved = cls._PENGU_CALLBACK_RESERVED if for_callback else cls._PENGU_RESERVED
        if name in reserved:
            return f"_{name}"
        return name

    def _func_return(self, func: c_ast.FuncDecl) -> str:
        ret_t, _ = self.c_type(func.type, fallback="void")
        if ret_t == "void":
            return "void"
        return ret_t

    # ------------------------------------------------------ source helpers

    def _load_original_lines(self) -> List[str]:
        with open(self.header_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()

    def _included_headers(self, raw_lines: List[str]) -> List[str]:
        """Returns the header names this header ``#include``s (in order)."""
        out: List[str] = []
        for line in raw_lines:
            m = re.match(r'\s*#\s*include\s+"([^"]+)"', line)
            if m:
                name = os.path.basename(m.group(1))
                if name not in out:
                    out.append(name)
        return out

    @staticmethod
    def module_name_for(directory: str, filename: str) -> str:
        """Returns the PenguScript module path of a binding file.

        ``("std", "raygui.d.pengu")`` → ``"std.raygui"``. The ``.d.pengu``
        suffix has two dots, so it has to be stripped by hand (``splitext``
        would leave ``raygui.d``).
        """
        stem = os.path.basename(filename)
        if stem.endswith(".d.pengu"):
            stem = stem[: -len(".d.pengu")]
        else:
            stem = os.path.splitext(stem)[0]
        package = os.path.basename(os.path.normpath(directory))
        return f"{package}.{stem}" if package and package != "." else stem

    @staticmethod
    def discover_binding_headers(directory: str) -> Dict[str, str]:
        """Maps ``header.h`` → ``module.path`` for the bindings in ``directory``.

        Bindings record their source header in the banner
        (``## Source header: raygui.h``), which is what lets ``pengu bind`` emit
        the ``import`` lines a binding needs to reuse the *same* types as the
        headers it includes (``raygui.h`` includes ``raylib.h``, so
        ``std/raygui.d.pengu`` must ``import std.raylib``).
        """
        found: Dict[str, str] = {}
        if not directory or not os.path.isdir(directory):
            return found
        package = os.path.basename(os.path.normpath(directory))
        for entry in sorted(os.listdir(directory)):
            if not entry.endswith(".d.pengu"):
                continue
            path = os.path.join(directory, entry)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    head = f.read(600)
            except OSError:
                continue
            m = re.search(r"^#+\s*Source header:\s*(\S+)", head, re.MULTILINE)
            if not m:
                continue
            module = BindGenerator.module_name_for(directory, entry)
            found.setdefault(os.path.basename(m.group(1)), module)
        return found

    def _comment_before(self, lines: List[str], decl_line: int) -> Optional[str]:
        """Collects the comment block immediately above ``decl_line`` (1-based)."""
        collected: List[str] = []
        if decl_line - 2 >= len(lines):
            return None
        i = decl_line - 2
        while i >= 0:
            stripped = lines[i].strip()
            if not stripped:
                if collected:
                    break  # blank line separates the doc from the decl
                i -= 1
                continue
            if stripped.startswith("/*") or stripped.startswith("*"):
                # C block comment: walk upward to its opening '/*'. A multi-line
                # block reaches this branch through its closing ' */' line, and
                # its inner lines usually start with '*' decoration.
                j = i
                block: List[str] = []
                opened = False
                while j >= 0:
                    block.append(lines[j])
                    if "/*" in lines[j]:
                        opened = True
                        break
                    if j == 0:
                        break
                    j -= 1
                if opened:
                    block.reverse()
                    collected = block + collected
                else:
                    collected = [stripped] + collected
                i = j - 1
                continue
            if stripped.startswith("//") or stripped.startswith("///"):
                collected.insert(0, stripped)
                i -= 1
                continue
            if stripped.startswith("##"):
                collected.insert(0, stripped)
                i -= 1
                continue
            break
        if not collected:
            return None
        return "\n".join(collected)

    # ------------------------------------------------------------ emission

    def emit_banner(self, imports: Optional[List[Tuple[str, str]]] = None) -> None:
        """Emits the file banner, the ``include`` line and any auto imports.

        Args:
            imports: ``(module_path, header)`` pairs for headers this header
                includes that already have a binding in the same directory.
        """
        header_name = os.path.basename(self.header_path)
        self.lines.append("## PenguScript declaration binding generated by 'pengu bind'.")
        self.lines.append(f"## Source header: {header_name}")
        self.lines.append(f"include \"{self.header_include}\"")
        if imports:
            self.lines.append("")
            self.lines.append("# Bindings of the headers included above: the types they declare")
            self.lines.append("# must be the very same ones this file uses, so import them.")
            for module, header in imports:
                self.lines.append(f"#   {header}")
                self.lines.append(f"import {module}")
        self.lines.append("")

    def emit_links(self) -> None:
        for lib in self.links:
            self.lines.append(f'link "{lib}"')
        if self.links:
            self.lines.append("")

    def emit_consts(self, raw_text: str) -> None:
        """Emits object-like numeric/string #define macros from the original text."""
        consts: List[Tuple[str, str]] = []
        for m in re.finditer(
            r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.*?)\s*(?://.*)?$",
            raw_text, re.MULTILINE,
        ):
            name = m.group(1)
            value = m.group(2).strip().rstrip("\\")
            if not value or value.startswith(("(", "/*")):
                continue
            if "\\" in value or "(" in value and value.rstrip().endswith(")"):
                if value.startswith("(") and value.endswith(")") and self._is_int(value[1:-1].strip()):
                    value = value[1:-1].strip()
                elif re.match(r"^[A-Za-z_][A-Za-z0-9_]*\(", value):
                    continue  # function-like macro
                else:
                    continue
            if self._is_ignored(name):
                continue
            if self._is_int(value):
                consts.append((name, value))
            elif self._is_string(value):
                consts.append((name, value))
        if consts:
            self.lines.append("# -- Constants (#define) ------------------------------")
            self.lines.append("")
            seen_consts = set()
            for name, value in consts:
                if name in seen_consts:
                    self._warn(f"skipping duplicate #define '{name}' (macro depends on #ifdef context)")
                    continue
                seen_consts.add(name)
                if self._is_string(value):
                    # value already includes quotes; keep inner only
                    inner = value[1:-1]
                    self.lines.append(f'const {name} as string is "{inner}"')
                else:
                    # C integer suffixes (u/l/ll) are not valid Pengu literals.
                    clean = re.sub(r"[uUlL]+$", "", value.strip())
                    self.lines.append(f"const {name} as i64 is {clean}")
                self.emitted_names.add(name)
            self.lines.append("")

    @staticmethod
    def _is_int(value: str) -> bool:
        v = value.strip()
        sign = ""
        if v[:1] in "+-":
            sign, v = v[0], v[1:].strip()
        if re.fullmatch(r"(0[xX][0-9a-fA-F]+|0[0-7]*|[0-9]+)[uUlL]*", v):
            return True
        return False

    @staticmethod
    def _is_string(value: str) -> bool:
        return value.startswith('"') and value.endswith('"')

    def _is_ignored(self, name: str) -> bool:
        for pat in self.ignore:
            if re.fullmatch(pat, name):
                return True
        return False

    def emit_record(self, decl: c_ast.Decl, comments: Dict[int, str], raw_lines: List[str]) -> None:
        """Emits a standalone struct/union/enum declaration."""
        t = decl.type
        while isinstance(t, c_ast.TypeDecl):
            t = t.type
        if isinstance(t, c_ast.Enum):
            self._emit_enum(t, decl, comments, raw_lines)
        elif isinstance(t, c_ast.Struct):
            self._emit_struct(t, decl, comments, raw_lines, kind="rune")
        elif isinstance(t, c_ast.Union):
            self._emit_struct(t, decl, comments, raw_lines, kind="echo")

    def _emit_enum(self, enum: c_ast.Enum, decl, comments, raw_lines, force_name: Optional[str] = None) -> None:
        name = force_name or enum.name
        if not name or self._is_ignored(name) or name in self.emitted_names:
            return
        self.emitted_names.add(name)
        comment = comments.get(decl.coord.line) if decl.coord else None
        self._emit_doc(comment)
        self.lines.append(f"omen {name}:")
        next_value = 0
        seen_values: Set[int] = set()
        for item in enum.values or []:
            vname = item.name
            if item.value is not None:
                try:
                    val = self._const_eval(item.value)
                except Exception:
                    val = next_value
            else:
                val = next_value
            next_value = val + 1
            if val in seen_values:
                # C enums can alias two names onto one value; PenguScript omens
                # cannot, so the duplicate is dropped with a warning.
                self._warn(f"enum '{name}': variant '{vname}' repeats value {val} "
                           f"of an earlier variant and was skipped")
                continue
            seen_values.add(val)
            self.lines.append(f"  {vname} is {val}")
        self.lines.append("")
        self._record_type(name)

    def _emit_struct(self, rec, decl, comments, raw_lines, kind: str, force_name: Optional[str] = None) -> None:
        name = force_name or rec.name or getattr(decl, "name", None) or getattr(decl.type, "declname", None)
        if not name or self._is_ignored(name) or name in self.emitted_names:
            return
        if not rec.decls:
            self.lines.append(f"alias {name} as opaque")
            self.lines.append("")
            self.emitted_names.add(name)
            self._record_type(name)
            return
        self.emitted_names.add(name)
        comment = comments.get(decl.coord.line) if decl.coord else None
        # Resolve every field type first: that is what may register a callback
        # alias, which has to be flushed before the 'rune' line.
        fields: List[Tuple[str, str, Optional[str]]] = []
        for field in rec.decls:
            if not isinstance(field, c_ast.Decl):
                continue
            # Struct members keep their C name verbatim: a member called 'type'
            # or 'size' is perfectly usable from PenguScript (`s.type`, `s.size`,
            # `with size is 3`), and renaming it would silently break both the
            # shipped bindings that use such members (nanosvg, typis) and any
            # hand-written code that reads them. Only *parameter* names, which
            # can shadow a type or a keyword inside the signature, are sanitized.
            f_name = field.name or "anon_field"
            f_t, _ = self.c_type(field.type, fallback="opaque")
            f_comment = comments.get(field.coord.line) if field.coord else None
            fields.append((f_name, f_t, f_comment))
        self._flush_aliases()
        self._emit_doc(comment)
        self.lines.append(f"{kind} {name}:")
        for f_name, f_t, f_comment in fields:
            if f_comment and not self.no_comments:
                for dline in self._doc_lines(f_comment):
                    self.lines.append(f"  # {dline}" if dline else "  #")
            self.lines.append(f"  {f_name} as {f_t}")
        self.lines.append("")
        self._record_type(name)

    def emit_typedef(self, td: c_ast.Typedef, comments, raw_lines) -> None:
        name = td.name
        if self._is_ignored(name):
            return
        # Decide what the typedef aliases by peeling declarator layers
        # (TypeDecl / PtrDecl / ArrayDecl) to reach the underlying kind.
        base = td.type
        while isinstance(base, (c_ast.TypeDecl, c_ast.PtrDecl, c_ast.ArrayDecl)):
            base = base.type
        comment = comments.get(td.coord.line) if td.coord else None

        if isinstance(base, c_ast.FuncDecl):
            if name in self.emitted_names:
                return
            self.emitted_names.add(name)
            # A named function-pointer typedef (`typedef int (*cb)(void* opaque, int)`)
            # becomes a callback alias, so its parameters need the stricter
            # callback sanitization.
            params = self._func_params(base, name=name, for_callback=True)
            ret = self._func_return(base)
            self._flush_aliases()
            self._emit_doc(comment)
            if params:
                self.lines.append(f"alias {name} as ref to weave with {params} into {ret}")
            else:
                self.lines.append(f"alias {name} as ref to weave into {ret}")
            self.lines.append("")
            self._record_type(name)
            return

        # Typedef of an inline struct/union/enum definition becomes the record.
        if isinstance(base, (c_ast.Struct, c_ast.Union, c_ast.Enum)):
            kind = "rune" if isinstance(base, c_ast.Struct) else ("echo" if isinstance(base, c_ast.Union) else "omen")
            if isinstance(base, c_ast.Enum):
                self._emit_enum(base, td, comments, raw_lines, force_name=name)
            else:
                self._emit_struct(base, td, comments, raw_lines, kind, force_name=name)
            return

        target, _ = self.c_type(td.type, fallback="opaque")
        if target == name:
            return
        self._record_type(name)
        if name in self.emitted_names:
            return
        self.emitted_names.add(name)
        self._emit_doc(comment)
        self.lines.append(f"alias {name} as {target}")
        self.lines.append("")

    def emit_function(self, decl: c_ast.Decl, comments, raw_lines) -> None:
        name = decl.name
        if not name or self._is_ignored(name):
            return
        if name.startswith("__"):
            return
        # The 'insignia' directive re-adds the prefix to the C name, so strip a
        # prefix that the header already spells out (webui_new_window -> new_window).
        decl_name = name
        if self.prefix and name.startswith(self.prefix):
            decl_name = name[len(self.prefix):]
            if not decl_name:
                decl_name = name
        if decl_name in self.emitted_names:
            return
        # Skip C standard-library / stub functions that leaked through.
        func = decl.type
        self.emitted_names.add(decl_name)
        comment = comments.get(decl.coord.line) if decl.coord else None
        params = self._func_params(func, name=decl_name)
        ret = self._func_return(func)
        self._flush_aliases()
        self._emit_doc(comment)
        if params:
            self.lines.append(f"declare {decl_name} with {params} into {ret}")
        else:
            self.lines.append(f"declare {decl_name} into {ret}")
        self.lines.append("")

    def _const_eval(self, node) -> int:
        """Folds simple constant int expressions from pycparser nodes."""
        if isinstance(node, c_ast.Constant):
            text = node.value
            text = re.sub(r"[uUlL]+$", "", text)
            return int(text, 0)
        if isinstance(node, c_ast.UnaryOp) and node.op == "-":
            return -self._const_eval(node.expr)
        if isinstance(node, c_ast.BinaryOp):
            lhs = self._const_eval(node.left)
            rhs = self._const_eval(node.right)
            if node.op == "+":
                return lhs + rhs
            if node.op == "-":
                return lhs - rhs
            if node.op == "*":
                return lhs * rhs
            if node.op == "/":
                return int(lhs / rhs)
            if node.op == "|":
                return lhs | rhs
            if node.op == "&":
                return lhs & rhs
            if node.op == "<<":
                return lhs << rhs
            if node.op == ">>":
                return lhs >> rhs
        raise ValueError("not a constant")


# --------------------------------------------------------------------------
# Preprocessing + parsing
# --------------------------------------------------------------------------

def _default_stub_dir() -> str:
    """Locates the bundled c_bind_stubs/ tree (source checkout or PyInstaller)."""
    here = os.path.dirname(os.path.abspath(__file__))
    meipass = getattr(sys, "_MEIPASS", "") or ""
    candidates = [
        os.environ.get("PENGU_BIND_STUBS", ""),
        os.path.join(meipass, "c_bind_stubs"),
        os.path.join(here, "c_bind_stubs"),
        os.path.join(os.getcwd(), "c_bind_stubs"),
    ]
    for cand in candidates:
        if cand and os.path.isdir(cand):
            return cand
    return os.path.join(here, "c_bind_stubs")


GNU_EXTENSION_BLANKING_FLAGS: List[str] = [
    "-D__attribute__(x)=",
    "-D__attribute__=",
    "-D__extension__=",
    "-D__restrict=",
    "-D__restrict__=",
    "-D__inline__=inline",
    "-D__inline=inline",
    "-D__asm__(x)=",
    "-D__asm__=",
    "-D__declspec(x)=",
    "-D__volatile__=volatile",
]


def preprocess_and_parse(
    header_path: str,
    include_paths: Optional[List[str]] = None,
    stub_dir: Optional[str] = None,
    defines: Optional[List[str]] = None,
    cpp_flags: Optional[Union[str, List[str]]] = None,
    system_includes: bool = False,
    preprocessed: Optional[str] = None,
    blank_extensions: bool = True,
) -> Tuple[c_ast.FileAST, str, str]:
    """Preprocesses the header and parses it with pycparser.

    Returns (ast, preprocessed_text, original_text).
    """
    if c_parser is None:
        raise HeaderParseError("pycparser is not installed; run: pip install pycparser")

    header_abs = os.path.abspath(header_path)
    if not os.path.isfile(header_abs):
        raise FileNotFoundError(f"Header not found: {header_path}")
    with open(header_abs, "r", encoding="utf-8", errors="replace") as f:
        original = f.read()

    if preprocessed:
        prep_abs = os.path.abspath(preprocessed)
        if not os.path.isfile(prep_abs):
            raise FileNotFoundError(f"Preprocessed file not found: {preprocessed}")
        with open(prep_abs, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    else:
        stub_dir = stub_dir or _default_stub_dir()
        flags = ["-E"]
        if not system_includes:
            flags.extend(["-U_WIN32", "-U_MSC_VER", "-U__TINYC__", "-nostdinc", f"-I{stub_dir}"])
        if blank_extensions:
            flags.extend(GNU_EXTENSION_BLANKING_FLAGS)
        for d in defines or []:
            if d:
                flags.append(f"-D{d}")
        for inc in include_paths or []:
            if inc:
                flags.append(f"-I{inc}")
        if cpp_flags:
            if isinstance(cpp_flags, str):
                import shlex
                flags.extend(shlex.split(cpp_flags))
            else:
                flags.extend(cpp_flags)

        try:
            res = subprocess.run(
                ["gcc"] + flags + [header_abs],
                capture_output=True, text=True, timeout=240,
            )
        except Exception as e:  # noqa: BLE001
            raise HeaderParseError(f"failed to run the C preprocessor: {e}") from e
        if res.returncode != 0:
            tail = "\n".join(res.stderr.splitlines()[-15:])
            suggestions = [
                "Tip: Check if the library header has a standalone mode (e.g. '--define Z_SOLO').",
                "Tip: Try '--system-includes' to use standard host compiler headers instead of minimal stubs.",
                "Tip: Pass custom preprocessor flags via '--cpp-flags \"...\"' or include dirs with '--include-paths'.",
                "Tip: Preprocess manually with 'gcc -E ...' and use '--preprocessed <file.i>'."
            ]
            sug_str = "\n".join(f"  * {s}" for s in suggestions)
            raise HeaderParseError(
                f"preprocessing failed (rc={res.returncode}):\n{tail}\n\nSuggestions:\n{sug_str}"
            )

        text = res.stdout

    try:
        ast = c_parser.CParser().parse(text, filename=os.path.basename(header_abs))
    except Exception as e:  # noqa: BLE001
        err_str = str(e)
        context_snippet = ""
        m = re.search(r"(?:^|(?<=\s)|(?<=[a-zA-Z]:))(?P<path>[^:]+?):(?P<line>\d+)(?::(?P<col>\d+))?:", err_str)
        if not m:
            m = re.search(r":(?P<line>\d+)(?::(?P<col>\d+))?:", err_str)
        line_num = int(m.group("line")) if m else None
        err_file = m.group("path").strip() if m and "path" in m.groupdict() and m.group("path") else None

        snippets: List[str] = []
        target_path = err_file or header_abs
        if target_path and not os.path.isabs(target_path):
            target_path = os.path.abspath(target_path)
        if target_path and os.path.isfile(target_path) and line_num:
            try:
                with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                    orig_lines = f.read().splitlines()
                start_l = max(0, line_num - 5)
                end_l = min(len(orig_lines), line_num + 4)
                src_lines = []
                for idx in range(start_l, end_l):
                    curr = idx + 1
                    mark = ">>> " if curr == line_num else "    "
                    src_lines.append(f"{mark}{curr:5d} | {orig_lines[idx]}")
                if src_lines:
                    snippets.append(f"Source context ({os.path.basename(target_path)} around line {line_num}):\n" + "\n".join(src_lines))
            except Exception:
                pass

        t_lines = text.splitlines()
        pp_idx = None
        if line_num:
            curr_l = 0
            for idx, l in enumerate(t_lines):
                marker = re.match(r'^#\s+(\d+)\s+"([^"]+)"', l)
                if marker:
                    curr_l = int(marker.group(1))
                    continue
                if curr_l == line_num:
                    pp_idx = idx
                    break
                curr_l += 1

        if pp_idx is not None:
            start_p = max(0, pp_idx - 4)
            end_p = min(len(t_lines), pp_idx + 5)
            pp_snippet = []
            for idx in range(start_p, end_p):
                curr = idx + 1
                mark = ">>> " if idx == pp_idx else "    "
                pp_snippet.append(f"{mark}{curr:5d} | {t_lines[idx]}")
            if pp_snippet:
                snippets.append("Preprocessed code context around failure:\n" + "\n".join(pp_snippet))
        elif line_num and line_num <= len(t_lines):
            start_p = max(0, line_num - 5)
            end_p = min(len(t_lines), line_num + 4)
            pp_snippet = []
            for idx in range(start_p, end_p):
                curr = idx + 1
                mark = ">>> " if curr == line_num else "    "
                pp_snippet.append(f"{mark}{curr:5d} | {t_lines[idx]}")
            if pp_snippet:
                snippets.append("Preprocessed code context:\n" + "\n".join(pp_snippet))

        if snippets:
            context_snippet = "\n\n" + "\n\n".join(snippets)

        suggestions = [
            "Tip 1: If macro expansions caused syntax errors, try '--define NAME' (e.g. '--define Z_SOLO') or '--cpp-flags'.",
            "Tip 2: Try '--no-blank-extensions' if GNU extension stripping caused unbalanced tokens.",
            "Tip 3: Try '--system-includes' if types from host standard headers are required.",
            "Tip 4: Preprocess and clean the header manually, then pass '--preprocessed <path.i>'."
        ]
        sug_str = "\n".join(f"  * {s}" for s in suggestions)
        raise HeaderParseError(
            f"pycparser could not parse the preprocessed header: {err_str}"
            f"{context_snippet}\n\nSuggestions:\n{sug_str}"
        ) from e
    return ast, text, original


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def generate_bind_file(
    header: str,
    output: Optional[str] = None,
    prefix: str = "",
    links: Optional[List[str]] = None,
    ignore: Optional[List[str]] = None,
    include_paths: Optional[List[str]] = None,
    use_cpp: bool = True,
    header_include: Optional[str] = None,
    no_comments: bool = False,
    stub_dir: Optional[str] = None,
    auto_import: Optional[str] = None,
    defines: Optional[List[str]] = None,
    cpp_flags: Optional[Union[str, List[str]]] = None,
    system_includes: bool = False,
    preprocessed: Optional[str] = None,
    blank_extensions: bool = True,
) -> str:
    """Generates a .d.pengu binding for a C header and writes it to disk.

    Args:
        header: Path to the C header (.h) to translate.
        output: Destination .d.pengu path (default: <header dir>/<stem>.d.pengu).
        prefix: Insignia prefix added to every function (e.g. ``webui_``).
        links: Native libraries to emit as ``link "..."`` lines.
        ignore: Symbol names / regexes to skip.
        include_paths: Extra include directories for the preprocessor.
        use_cpp: Run the C preprocessor first (True by default).
        header_include: Literal text for the emitted ``include`` line.
        no_comments: Do not emit documentation comments.
        stub_dir: Directory with minimal C stub headers.
        auto_import: Directory whose ``*.d.pengu`` bindings are scanned to emit
            ``import`` lines for the headers this header includes ("std" for the
            standard library). Defaults to the output file's directory; pass an
            empty string to disable the scan.
        defines: Preprocessor macro definitions (-D NAME or NAME=val).
        cpp_flags: Raw extra flags passed to the C preprocessor.
        system_includes: Use host compiler standard headers (keep _WIN32/_MSC_VER and omit -nostdinc).
        preprocessed: Path to an already preprocessed .i file to parse directly.
        blank_extensions: Strip GNU extensions (__attribute__, __asm__, etc.) during preprocessing.

    Returns:
        Path of the written .d.pengu file.
    """
    ast, _, original = preprocess_and_parse(
        header,
        include_paths=include_paths,
        stub_dir=stub_dir,
        defines=defines,
        cpp_flags=cpp_flags,
        system_includes=system_includes,
        preprocessed=preprocessed,
        blank_extensions=blank_extensions,
    ) if use_cpp else (_parse_raw(header))

    gen = BindGenerator(
        header_path=header,
        prefix=prefix,
        links=links,
        ignore=ignore,
        include_paths=include_paths,
        use_cpp=use_cpp,
        header_include=header_include,
        no_comments=no_comments,
        stub_dir=stub_dir,
    )

    target_file = os.path.basename(os.path.abspath(header))
    out_dir = os.path.dirname(os.path.abspath(output)) if output \
        else os.path.dirname(os.path.abspath(header))
    import_dir = out_dir if auto_import is None else auto_import
    known_bindings = BindGenerator.discover_binding_headers(import_dir)
    auto_imports: List[Tuple[str, str]] = []
    if known_bindings:
        own_module = BindGenerator.module_name_for(import_dir, output or target_file)
        for inc in gen._included_headers(gen._load_original_lines()):
            module = known_bindings.get(inc)
            if module and module != own_module:
                auto_imports.append((module, inc))

    raw_lines = gen._load_original_lines()
    comments: Dict[int, str] = {}
    if not no_comments:
        for node in ast.ext:
            coord = getattr(node, "coord", None)
            if coord is not None and coord.line:
                c_file = getattr(coord, "file", None)
                if c_file is None or os.path.abspath(c_file) == os.path.abspath(header):
                    c = gen._comment_before(raw_lines, coord.line)
                    if c:
                        comments[coord.line] = c

    gen.emit_banner(auto_imports)
    gen.emit_links()
    gen.emit_consts(original)

    # Types first (before insignia), so PenguScript names match C identifiers.
    type_nodes: List = []
    func_nodes: List = []
    for node in ast.ext:
        origin = ""
        coord = getattr(node, "coord", None)
        if coord is not None and getattr(coord, "file", None):
            origin = os.path.basename(str(coord.file))
        if target_file and origin and origin != target_file:
            continue
        if isinstance(node, c_ast.Typedef):
            type_nodes.append(node)
        elif isinstance(node, c_ast.Decl):
            if isinstance(node.type, c_ast.FuncDecl):
                func_nodes.append(node)
            else:
                type_nodes.append(node)

    gen.lines.append("# ------------------------------------------------------------------")
    gen.lines.append("# Types (structs, unions, enums, aliases)")
    gen.lines.append("# ------------------------------------------------------------------")
    gen.lines.append("")
    for node in type_nodes:
        if isinstance(node, c_ast.Typedef):
            gen.emit_typedef(node, comments, raw_lines)
        else:
            base = node.type
            is_record = False
            probe = base
            while isinstance(probe, c_ast.TypeDecl):
                probe = probe.type
            if isinstance(probe, (c_ast.Struct, c_ast.Union, c_ast.Enum)):
                is_record = True
            if is_record:
                gen.emit_record(node, comments, raw_lines)

    # Callback aliases found in the type section must precede the functions.
    gen._flush_aliases()
    if gen.prefix:
        gen.lines.append("# ------------------------------------------------------------------")
        gen.lines.append("# Functions (every name receives the insignia prefix)")
        gen.lines.append("# ------------------------------------------------------------------")
        gen.lines.append("")
        gen.lines.append(f"insignia {gen.prefix}")
        gen.lines.append("")
    for node in func_nodes:
        gen.emit_function(node, comments, raw_lines)

    # Strip any trailing empty lines, keep one.
    gen._flush_aliases()
    while gen.lines and gen.lines[-1] == "":
        gen.lines.pop()
    gen.lines.append("")

    out_path = output
    if not out_path:
        stem = os.path.splitext(os.path.basename(header))[0]
        out_path = os.path.join(os.path.dirname(os.path.abspath(header)), f"{stem}.d.pengu")
    out_path = os.path.abspath(out_path)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(gen.lines))

    if gen.warnings:
        for w in gen.warnings:
            print(f"[pengu bind] warning: {w}", file=sys.stderr)
    return out_path


def _parse_raw(header: str):
    """Fallback: parse a very simple header without the preprocessor."""
    if c_parser is None:
        raise HeaderParseError("pycparser is not installed; run: pip install pycparser")
    with open(header, "r", encoding="utf-8") as f:
        original = f.read()
    # Minimal stripping of preprocessor lines and block comments so pycparser
    # can handle simple headers.
    cleaned = re.sub(r"/\*.*?\*/", "", original, flags=re.DOTALL)
    cleaned = re.sub(r"^\s*#.*$", "", cleaned, flags=re.MULTILINE)
    try:
        ast = c_parser.CParser().parse(cleaned, filename="header_raw.i")
    except Exception as e:  # noqa: BLE001
        raise HeaderParseError(f"pycparser could not parse the header directly: {e}") from e
    return ast, cleaned, original


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Generate a .d.pengu binding from a C header")
    parser.add_argument("header", help="Path to the C header file (.h) to translate")
    parser.add_argument("--prefix", default="", help="Insignia prefix added to function names (e.g. webui_)")
    parser.add_argument("--links", nargs="*", default=[], help="Native libraries to emit as link \"...\" lines")
    parser.add_argument("--output", default="", help="Output .d.pengu path (default: next to the header)")
    parser.add_argument("--no-comments", action="store_true", help="Do not emit documentation comments")
    parser.add_argument("--ignore", nargs="*", default=[], help="Symbol names / regexes to skip")
    parser.add_argument("--include-paths", nargs="*", default=[], help="Extra include directories for the preprocessor")
    parser.add_argument("--define", "-D", dest="defines", action="append", default=[],
                        help="Define a preprocessor macro (e.g. -D Z_SOLO or --define NAME=val)")
    parser.add_argument("--cpp-flags", default=None,
                        help="Raw flags passed directly to the preprocessor (e.g. \"-DZ_SOLO -DXXH_INLINE_ALL=0\")")
    parser.add_argument("--system-includes", action="store_true", default=False,
                        help="Use compiler system headers instead of minimal stubs")
    parser.add_argument("--preprocessed", default=None, metavar="FILE.i",
                        help="Parse an already preprocessed .i file directly without running gcc")
    parser.add_argument("--no-blank-extensions", dest="blank_extensions", action="store_false", default=True,
                        help="Do not blank GNU compiler extensions (__attribute__, __asm__, etc.)")
    parser.add_argument("--no-cpp", dest="use_cpp", action="store_false", default=True,
                        help="Do not run the C preprocessor (simple headers only)")
    parser.add_argument("--auto-import", dest="auto_import", default=None, metavar="DIR",
                        help="Directory with sibling .d.pengu bindings")
    args = parser.parse_args()
    try:
        out = generate_bind_file(
            header=args.header,
            output=args.output or None,
            prefix=args.prefix,
            links=args.links,
            ignore=args.ignore,
            include_paths=args.include_paths,
            use_cpp=args.use_cpp,
            no_comments=args.no_comments,
            auto_import=args.auto_import,
            defines=args.defines,
            cpp_flags=args.cpp_flags,
            system_includes=args.system_includes,
            preprocessed=args.preprocessed,
            blank_extensions=args.blank_extensions,
        )
        print(f"Generated binding: {out}")
    except (HeaderParseError, FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

