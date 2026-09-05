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
from typing import Dict, List, Optional, Set, Tuple

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

    # ------------------------------------------------------------ helpers

    def _warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def _doc_lines(self, comment: Optional[str]) -> List[str]:
        if self.no_comments or not comment:
            return []
        out = []
        for raw in comment.splitlines():
            line = raw.strip()
            line = re.sub(r"^/\*+", "", line)
            line = re.sub(r"\*+/$", "", line)
            line = re.sub(r"^\*+", "", line).strip()
            line = re.sub(r"^//+", "", line).strip()
            line = re.sub(r"^##*", "", line).strip()
            line = line.strip()
            out.append(line)
        return out

    def _emit_doc(self, comment: Optional[str]) -> None:
        if self.no_comments or not comment:
            return
        for line in self._doc_lines(comment):
            self.lines.append(f"## {line}")

    def _record_type(self, name: str) -> None:
        self.known_type_names.add(name)

    # ------------------------------------------------- type name mapping

    def c_type(self, tnode, fallback: str = "opaque") -> Tuple[str, Optional[str]]:
        """Maps a pycparser type node to a PenguScript type string.

        Returns (pengu_type, callback_alias_or_None). The callback alias is set
        when the node is (a pointer to) a function type that needs a dedicated
        'alias ... as ref to weave' declaration.
        """
        if tnode is None:
            return fallback, None
        # TypeDecl: unwrap qualifiers/name to inner type
        if isinstance(tnode, c_ast.TypeDecl):
            return self.c_type(tnode.type, fallback=fallback)
        if isinstance(tnode, c_ast.PtrDecl):
            inner, cb = self.c_type(tnode.type, fallback=fallback)
            if cb is not None:
                return cb, None  # pointer-to-function already an alias
            if inner == "void":
                return "ref to void", None
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
        """Emits (or reuses) an alias for an inline function-pointer type."""
        self._alias_counter += 1
        name = f"Callback{self._alias_counter}"
        params = self._func_params(func, name=name)
        ret = self._func_return(func)
        self.lines.append(f"alias {name} as ref to weave with {params} into {ret}")
        self.known_type_names.add(name)
        return name

    # ------------------------------------------- function signature pieces

    def _func_params(self, func: c_ast.FuncDecl, name: str = "") -> str:
        parts: List[str] = []
        if func.args is not None and func.args.params:
            for i, p in enumerate(func.args.params):
                if isinstance(p, c_ast.EllipsisParam):
                    self._warn(f"function '{name}': variadic '...' parameters are dropped")
                    continue
                p_name = getattr(p, "name", None)
                if p_name is None:
                    p_name = f"p{i}"
                p_t, _ = self.c_type(p.type, fallback="opaque")
                if p_t == "void":
                    continue
                p_name = self._sanitize_param(p_name)
                parts.append(f"{p_name} as {p_t}")
        return ", ".join(parts)

    @staticmethod
    def _sanitize_param(name: str) -> str:
        name = str(name)
        if name in {"self", "type"}:
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

    def _comment_before(self, lines: List[str], decl_line: int) -> Optional[str]:
        """Collects the comment block immediately above ``decl_line`` (1-based)."""
        collected: List[str] = []
        i = decl_line - 2
        while i >= 0:
            stripped = lines[i].strip()
            if not stripped:
                if collected:
                    break  # blank line separates the doc from the decl
                i -= 1
                continue
            if stripped.startswith("/*"):
                # multi-line block: gather from the end to the opening
                j = i
                block: List[str] = []
                opened = False
                while j >= 0:
                    block.append(lines[j])
                    if lines[j].rstrip().endswith("*/"):
                        # continue upward until opening or first non-comment
                        pass
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

    def emit_banner(self) -> None:
        header_name = os.path.basename(self.header_path)
        self.lines.append("## PenguScript declaration binding generated by 'pengu bind'.")
        self.lines.append(f"## Source header: {header_name}")
        self.lines.append(f"include \"{self.header_include}\"")
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
        for item in enum.values or []:
            vname = item.name
            if item.value is not None:
                try:
                    val = self._const_eval(item.value)
                    next_value = val + 1
                    self.lines.append(f"  {vname} is {val}")
                except Exception:
                    self.lines.append(f"  {vname} is {next_value}")
                    next_value += 1
            else:
                self.lines.append(f"  {vname} is {next_value}")
                next_value += 1
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
        self._emit_doc(comment)
        self.lines.append(f"{kind} {name}:")
        for field in rec.decls:
            if not isinstance(field, c_ast.Decl):
                continue
            f_name = field.name
            if f_name is None:
                f_name = f"anon_field"
            f_t, _ = self.c_type(field.type, fallback="opaque")
            f_comment = comments.get(field.coord.line) if field.coord else None
            if f_comment and not self.no_comments:
                for dline in self._doc_lines(f_comment):
                    self.lines.append(f"  ## {dline}")
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
            self._emit_doc(comment)
            params = self._func_params(base, name=name)
            ret = self._func_return(base)
            self.lines.append(f"alias {name} as ref to weave with {params} into {ret}")
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
        self._emit_doc(comment)
        params = self._func_params(func, name=decl_name)
        ret = self._func_return(func)
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


def preprocess_and_parse(
    header_path: str,
    include_paths: Optional[List[str]] = None,
    stub_dir: Optional[str] = None,
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

    stub_dir = stub_dir or _default_stub_dir()
    flags = ["-E", "-U_WIN32", "-U_MSC_VER", "-U__TINYC__", "-nostdinc", f"-I{stub_dir}"]
    for inc in include_paths or []:
        if inc:
            flags.append(f"-I{inc}")

    try:
        res = subprocess.run(
            ["gcc"] + flags + [header_abs],
            capture_output=True, text=True, timeout=240,
        )
    except Exception as e:  # noqa: BLE001
        raise HeaderParseError(f"failed to run the C preprocessor: {e}") from e
    if res.returncode != 0:
        tail = "\n".join(res.stderr.splitlines()[-12:])
        raise HeaderParseError(
            f"preprocessing failed (rc={res.returncode}):\n{tail}\n"
            "Tip: add the missing include directories with --include-paths, or "
            "pass --no-cpp to parse the file without preprocessing."
        )

    text = res.stdout
    try:
        ast = c_parser.CParser().parse(text, filename="webui_preprocessed.i")
    except Exception as e:  # noqa: BLE001
        raise HeaderParseError(
            f"pycparser could not parse the preprocessed header: {e}\n"
            "Tip: try --no-cpp for very simple headers, or extend c_bind_stubs/ "
            "with the missing types."
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

    Returns:
        Path of the written .d.pengu file.
    """
    ast, _, original = preprocess_and_parse(
        header, include_paths=include_paths, stub_dir=stub_dir,
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

    raw_lines = gen._load_original_lines()
    comments: Dict[int, str] = {}
    if not no_comments:
        for node in ast.ext:
            coord = getattr(node, "coord", None)
            if coord is not None and coord.line:
                c = gen._comment_before(raw_lines, coord.line)
                if c:
                    comments[coord.line] = c

    target_file = os.path.basename(os.path.abspath(header))
    gen.emit_banner()
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
