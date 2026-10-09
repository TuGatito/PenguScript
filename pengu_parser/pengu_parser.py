from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

if TYPE_CHECKING:  # pragma: no cover - import cycle guard, annotations only
    from .pengu_errors import ParseError

from lark import Lark, Tree, Token
from lark.exceptions import UnexpectedInput as LarkUnexpectedInput, LarkError as LarkBaseError
from lark.indenter import Indenter, DedentError

from .pengu_grammar import GRAMMAR

BOM = "\ufeff"


def strip_bom(code: str) -> str:
    """Removes a leading UTF-8 BOM.

    Editors on Windows (Notepad, Visual Studio, PowerShell's ``Set-Content``)
    commonly write a BOM; it is metadata, not part of the program, so it must
    not make the first line unparsable.

    Args:
        code: Source text, possibly starting with U+FEFF.

    Returns:
        The source text without a leading BOM (one or more).
    """
    while code.startswith(BOM):
        code = code[len(BOM):]
    return code


class PenguIndenter(Indenter):
    """Custom Lark indenter for indentation-significant parsing in PenguScript."""
    NL_type = '_NEWLINE'
    OPEN_PAREN_types = ["LSQB", "LPAR", "LBRACE"]
    CLOSE_PAREN_types = ["RSQB", "RPAR", "RBRACE"]
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 2
    STMT_STARTERS = frozenset({'VAR', 'LET', 'SET', 'CONST', 'STATIC'})

    def handle_NL(self, token: Token):
        try:
            yield from super().handle_NL(token)
        except DedentError as exc:
            exc.line = getattr(token, "end_line", getattr(token, "line", None))
            exc.column = getattr(token, "end_column", getattr(token, "column", None))
            raise

    def _process(self, stream):
        prev_token = None
        token = None
        for token in stream:
            if token.type == self.NL_type:
                yield from self.handle_NL(token)
                prev_token = None
                continue
            else:
                if token.type in self.STMT_STARTERS and self.paren_level == 0:
                    if prev_token is not None and getattr(prev_token, 'line', None) == getattr(token, 'line', None):
                        if prev_token.type not in ('COLON', 'SEMICOLON', 'DEFER', 'ERRDEFER', 'STATIC') and prev_token.value not in (':', 'defer', 'errdefer', 'static'):
                            from .pengu_errors import ParseError
                            line = getattr(token, 'line', 1)
                            col = getattr(token, 'column', 1)
                            raise ParseError(
                                "Syntax error: multiple statements on a single line require a newline delimiter",
                                code="E0000",
                                line=line,
                                column=col
                            )
                yield token

            if token.type in self.OPEN_PAREN_types:
                self.paren_level += 1
            elif token.type in self.CLOSE_PAREN_types:
                self.paren_level -= 1
                assert self.paren_level >= 0

            prev_token = token

        while len(self.indent_level) > 1:
            self.indent_level.pop()
            yield Token.new_borrow_pos(self.DEDENT_type, '', token) if token else Token(self.DEDENT_type, '', 0, 0, 0, 0, 0, 0)

        assert self.indent_level == [0], self.indent_level


class PenguParser:
    """LALR(1) parser for PenguScript v1.1.0 using embedded grammar."""
    _shared_parser = None

    def __init__(self):
        """Initializes Lark parser with embedded grammar and custom indenter."""
        if PenguParser._shared_parser is None:
            # Building the LALR tables is pure-Python work that dominates the
            # startup of every command (~2-3 s).  Lark serializes them safely:
            # the cache header carries a sha256 over the grammar, the options and
            # the Lark/Python versions, so editing the grammar invalidates it.
            cache_path = None
            try:
                from pengu_cache import grammar_digest, parser_cache_path
                cache_path = parser_cache_path(grammar_digest(GRAMMAR))
            except Exception:
                cache_path = None
            lark_kwargs = dict(
                parser='lalr',
                postlex=PenguIndenter(),
                propagate_positions=True,
                start=['start', 'expr'],
            )
            if cache_path:
                lark_kwargs['cache'] = cache_path
            try:
                PenguParser._shared_parser = Lark(GRAMMAR, **lark_kwargs)
            except Exception:
                # A corrupt or unwritable cache must never break parsing.
                lark_kwargs.pop('cache', None)
                PenguParser._shared_parser = Lark(GRAMMAR, **lark_kwargs)
        self.parser = PenguParser._shared_parser
        self.warnings: List[str] = []

    def _check_indentation_consistency(self, code: str) -> None:
        """Emits [W0005] warning if inconsistent tab/space indentation is detected."""
        self.warnings = []
        tab_line = None
        space_line = None
        for lineno, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            leading = line[:len(line) - len(line.lstrip())]
            if not leading:
                continue
            if '\t' in leading and not tab_line:
                tab_line = lineno
            if ' ' in leading and not space_line:
                space_line = lineno
            if tab_line and space_line:
                break
        if tab_line and space_line:
            msg = f"[W0005] Inconsistent indentation: line {tab_line} uses tabs, line {space_line} uses spaces"
            self.warnings.append(msg)
            warnings.warn(msg, stacklevel=2)

    @staticmethod
    def _strip_comments(code: str) -> str:
        """Blanks '#' comments and '##' documentation comments while preserving line counts.

        Supporting documentation comment styles:
          ## Single-line doc comment
          ## Inline closed doc comment ##
          ##
          Multi-line doc comment
          (preserved for LSP documentation tooltips)
          ##

        Comment text is replaced with whitespace so the Lark lexer never sees it,
        while every original newline is kept so token line numbers (used for doc
        extraction and diagnostics) stay aligned with the original source.
        """
        lines = code.splitlines(keepends=True)

        def blank(line: str) -> str:
            if line.endswith("\r\n"):
                return "\r\n"
            if line.endswith("\n"):
                return "\n"
            return "\n"

        def _has_matching_brace(line_str: str, start: int) -> bool:
            """Mirrors ``extract_string_parts``: a '{' starts an interpolation only
            when a balanced '}' follows it in the same literal.

            A JSON-ish literal such as ``"{\"k\":\"{v}\""`` opens with a brace
            that never closes, so it must stay plain text.
            """
            depth = 0
            in_q = None
            j = start
            n = len(line_str)
            while j < n:
                cj = line_str[j]
                if cj == '\\' and j + 1 < n:
                    if line_str.startswith('\\u{', j):
                        close_b = line_str.find('}', j + 3)
                        if close_b != -1:
                            j = close_b + 1
                            continue
                    j += 2
                    continue
                if in_q:
                    if cj == in_q:
                        in_q = None
                elif cj in ('"', "'"):
                    in_q = cj
                elif cj == '{':
                    depth += 1
                elif cj == '}':
                    depth -= 1
                    if depth == 0:
                        return True
                j += 1
            return False

        def _scan_line(line_str: str, state: str, brace_depth: int, str_state: str):
            """Comment stripper that tracks string state across lines.

            ``state`` is one of ``code``/``dquote``/``squote``/``triple``/``interp``;
            ``interp`` tracks a ``{expr}`` group inside a string so a ``#`` or a
            nested quote inside the expression does not end the literal.
            Returns ``(line, state, brace_depth, str_state)``.
            """
            out: List[str] = []
            i = 0
            n = len(line_str)
            while i < n:
                ch = line_str[i]
                if state == "code":
                    if ch == '#':
                        # Comment runs to the end of the line; keep the terminator
                        # so line numbers stay aligned.
                        if line_str.endswith("\r\n"):
                            nl = "\r\n"
                        elif line_str.endswith("\n"):
                            nl = "\n"
                        else:
                            nl = ""
                        return "".join(out).rstrip(" \t") + nl, "code", 0, "code"
                    if ch == 'r' and i + 1 < n and line_str[i + 1] == '"':
                        if line_str.startswith('r"""', i):
                            out.append('r"""')
                            i += 4
                            state = "triple"
                            continue
                        out.append('r"')
                        i += 2
                        state = "dquote"
                        continue
                    if ch == '"':
                        if line_str.startswith('"""', i):
                            out.append('"""')
                            i += 3
                            state = "triple"
                        else:
                            out.append('"')
                            i += 1
                            state = "dquote"
                        continue
                    if ch == "'":
                        out.append("'")
                        i += 1
                        state = "squote"
                        continue
                    out.append(ch)
                    i += 1
                    continue

                if state == "squote":
                    out.append(ch)
                    if ch == '\\' and i + 1 < n:
                        out.append(line_str[i + 1])
                        i += 2
                        continue
                    if ch == "'":
                        state = "code"
                    i += 1
                    continue

                if state == "dquote":
                    if ch == '\\' and i + 1 < n:
                        out.append(ch)
                        out.append(line_str[i + 1])
                        i += 2
                        continue
                    if ch == '{' and _has_matching_brace(line_str, i):
                        out.append(ch)
                        i += 1
                        str_state = "dquote"
                        state = "interp"
                        brace_depth = 1
                        continue
                    out.append(ch)
                    i += 1
                    if ch == '"':
                        state = "code"
                    continue

                if state == "triple":
                    if ch == '\\' and i + 1 < n:
                        out.append(ch)
                        out.append(line_str[i + 1])
                        i += 2
                        continue
                    if line_str.startswith('"""', i):
                        out.append('"""')
                        i += 3
                        state = "code"
                        continue
                    if ch == '{' and _has_matching_brace(line_str, i):
                        out.append(ch)
                        i += 1
                        str_state = "triple"
                        state = "interp"
                        brace_depth = 1
                        continue
                    out.append(ch)
                    i += 1
                    continue

                if state == "interp":
                    out.append(ch)
                    if ch in ('"', "'"):
                        quote = ch
                        i += 1
                        while i < n:
                            c2 = line_str[i]
                            out.append(c2)
                            if c2 == '\\' and i + 1 < n:
                                out.append(line_str[i + 1])
                                i += 2
                                continue
                            i += 1
                            if c2 == quote:
                                break
                        continue
                    if ch == '{':
                        brace_depth += 1
                    elif ch == '}':
                        brace_depth -= 1
                        if brace_depth == 0:
                            state = str_state
                    i += 1
                    continue

            return "".join(out), state, brace_depth, str_state

        out: List[str] = []
        i = 0
        n = len(lines)
        state = "code"
        brace_depth = 0
        str_state = "code"
        while i < n:
            line = lines[i]
            stripped = line.strip()
            if state == "code" and stripped.startswith('#'):
                if stripped.startswith('##'):
                    rest = stripped[2:].strip()
                    prev_is_comment = (i > 0 and lines[i - 1].strip().startswith('#'))
                    next_is_comment = (i + 1 < n and lines[i + 1].strip().startswith('#'))
                    if rest == '' and not prev_is_comment and not next_is_comment:
                        # Bare '##' isolated from other comments: start of a multi-line doc block.
                        j = i + 1
                        closed = -1
                        while j < n:
                            s2 = lines[j].strip()
                            if s2 == '##':
                                closed = j
                                break
                            if s2.startswith('##') and len(s2) > 2 and s2.endswith('##'):
                                closed = j
                                break
                            j += 1
                        if closed != -1:
                            for k in range(i, closed + 1):
                                out.append(blank(lines[k]))
                            i = closed + 1
                            continue
                        else:
                            for k in range(i, n):
                                out.append(blank(lines[k]))
                            break
                    else:
                        # '## doc' or '## doc ##' or bare '##' within a doc comment sequence.
                        out.append(blank(line))
                else:
                    # Regular single-line '#' comment.
                    out.append(blank(line))
            else:
                new_line, state, brace_depth, str_state = _scan_line(line, state, brace_depth, str_state)
                out.append(new_line)
            i += 1
        return ''.join(out)

    #: Tokens after which a `with` introduces a struct literal instead of a
    #: call's argument list.  `calling f with a, b` is by far the most common
    #: form in the corpus (~3400 uses against ~320 struct literals), so the
    #: rewrite below only fires on these predecessors.
    _STRUCT_INIT_WITH_PREDECESSORS = frozenset({"is", "return", "(", "with"})

    #: One token of a source line: string literals first (so a comma or `with`
    #: inside a string is never mistaken for syntax), then identifiers/numbers,
    #: then any single character.
    _STRUCT_INIT_TOKEN_RE = re.compile(
        r'r?"""(?:.|\n)*?"""'
        r'|r?"(?:[^"\\]|\\.)*"'
        r"|'(?:[^'\\]|\\.)*'"
        r'|[A-Za-z_][A-Za-z0-9_]*'
        r'|[0-9][0-9_]*'
        r'|\S'
    )

    @staticmethod
    def _merge_chain_continuations(code: str) -> str:
        """Folds lines that start with `.` or `->` into the previous line.

        A method chain reads better split over several lines::

            let clean is calling players
                .filter_alive()
                .sort_asc()

        The grammar has no line-continuation token, so the fold happens here.
        The number of lines is preserved by padding the merged-away lines with
        empty ones, which keeps ``#line`` directives and diagnostic positions
        exact (a folded line reports the position where the chain started).

        Lines inside a triple-quoted string are left alone: a string body may
        legitimately begin with `.`, and folding it would corrupt the literal.
        """
        lines = code.split("\n")
        out: List[str] = []
        index = 0
        total = len(lines)
        in_triple = False
        while index < total:
            start = index
            line = lines[index]
            if line.count('"""') % 2 == 1:
                in_triple = not in_triple
            if in_triple:
                out.append(line)
                index += 1
                continue
            merged = line
            cursor = index + 1
            while (cursor < total
                   and lines[cursor].lstrip().startswith((".", "->"))
                   and lines[cursor].count('"""') % 2 == 0):
                merged += " " + lines[cursor].strip()
                cursor += 1
            out.append(merged)
            out.extend([""] * (cursor - start - 1))
            index = cursor
        return "\n".join(out)

    @classmethod
    def _expand_short_struct_inits(cls, code: str) -> str:
        """Rewrites `with a, b` into `with a is a, b is b`.

        The short form cannot be expressed as a grammar rule: a rule that
        reduces a bare ``NAME`` to a field collides **Reduce/Reduce** against
        ``primary: NAME`` (the state is shared with general expression parsing),
        and Lark refuses to build the LALR tables at all rather than resolving
        it.  Expanding the text before parsing keeps the grammar conflict-free
        and, because the rewrite never adds or removes a line, keeps ``#line``
        directives and error positions exact.

        Only *struct literal* `with` clauses are touched: the rewrite keys on
        the token before `with` (`is`, `return`, `(`, `with`), which is what
        separates `var p as P is with a, b` from `calling f with a, b`.
        """
        if "with" not in code:
            return code
        return "\n".join(
            cls._expand_short_struct_inits_in_line(line) for line in code.split("\n")
        )

    @classmethod
    def _expand_short_struct_inits_in_line(cls, line: str) -> str:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            return line
        tokens = [
            (m.start(), m.end(), m.group(0))
            for m in cls._STRUCT_INIT_TOKEN_RE.finditer(line)
        ]
        insertions: List[Tuple[int, str]] = []
        for index, (_start, _end, text) in enumerate(tokens):
            if text != "with":
                continue
            predecessor = tokens[index - 1][2] if index else None
            if predecessor not in cls._STRUCT_INIT_WITH_PREDECESSORS:
                continue
            item_start = index + 1
            depth = 0
            cursor = index + 1
            while cursor < len(tokens):
                token = tokens[cursor][2]
                if token in "([{":
                    depth += 1
                elif token in ")]}":
                    if depth == 0:
                        break
                    depth -= 1
                elif depth == 0 and token in (",", ":"):
                    if token == ",":
                        cls._collect_shorthand_field(tokens, item_start, cursor, insertions)
                        item_start = cursor + 1
                    else:
                        break
                cursor += 1
            cls._collect_shorthand_field(tokens, item_start, cursor, insertions)
        if not insertions:
            return line
        expanded = line
        for position, text in sorted(insertions, reverse=True):
            expanded = expanded[:position] + text + expanded[position:]
        return expanded

    @staticmethod
    def _collect_shorthand_field(tokens, start: int, end: int,
                                 insertions: List[Tuple[int, str]]) -> None:
        """Records `is <name>` after a field slot holding exactly one NAME."""
        item = tokens[start:end]
        if len(item) != 1:
            return
        _s, item_end, text = item[0]
        if not text[:1].isalpha() and text[:1] != "_":
            return
        if not text.replace("_", "a").isalnum():
            return
        insertions.append((item_end, f" is {text}"))

    def parse(self, code: str) -> Tree:
        """Parses PenguScript source code into a Lark AST Tree.

        Args:
            code: PenguScript source text.

        Returns:
            Lark AST Tree root.

        Raises:
            ParseError: when the source is not valid PenguScript (Lark's syntax
                exceptions are converted, with a hint when the removed 0.10.0
                'and' separator is the likely cause).
        """
        code = strip_bom(code)
        code = code.replace("\r\n", "\n")
        self._check_indentation_consistency(code)
        clean_code = self._strip_comments(code).rstrip() + '\n'
        clean_code = self._merge_chain_continuations(clean_code)
        clean_code = self._expand_short_struct_inits(clean_code)
        try:
            return self.parser.parse(clean_code, start='start')
        except LarkUnexpectedInput as exc:
            raise self._parse_error(code, exc) from None
        except LarkBaseError as exc:
            raise self._parse_error(code, exc) from None

    def parse_expr(self, code: str) -> Tree:
        """Parses a PenguScript expression string into a Lark AST Tree.

        Args:
            code: PenguScript expression text.

        Returns:
            Lark AST Tree representing the expression.
        """
        code = strip_bom(code)
        clean_code = code.strip()
        try:
            return self.parser.parse(clean_code, start='expr')
        except LarkUnexpectedInput as exc:
            raise self._parse_error(code, exc) from None
        except LarkBaseError as exc:
            raise self._parse_error(code, exc) from None

    @staticmethod
    def _find_legacy_and(code: str):
        """Finds the first 'and' token that is not inside a string or comment.

        Used to explain the removed 0.10.0 list separator when a parse fails.

        Args:
            code: Original source text (comments included).

        Returns:
            ``(line, column)`` (1-based) of the token, or None.
        """
        for lineno, line in enumerate(code.splitlines(), 1):
            i, n = 0, len(line)
            quote = None
            while i < n:
                ch = line[i]
                if quote is None and ch == "#":
                    break
                if quote is None and ch in ('"', "'"):
                    quote = ch
                    i += 1
                    continue
                if quote is not None:
                    if ch == quote and (i == 0 or line[i - 1] != "\\"):
                        quote = None
                    i += 1
                    continue
                if (line.startswith("and", i)
                        and (i == 0 or not (line[i - 1].isalnum() or line[i - 1] == "_"))
                        and (i + 3 >= n or not (line[i + 3].isalnum() or line[i + 3] == "_"))):
                    return lineno, i + 1
                i += 1
        return None

    def _parse_error(self, code: str, exc: Any) -> ParseError:
        """Converts a Lark syntax exception into a friendly :class:`ParseError`."""
        from .pengu_errors import ParseError

        err_line = getattr(exc, "line", None)
        err_col = getattr(exc, "column", None)
        if err_line is None and hasattr(exc, "pos_in_stream") and exc.pos_in_stream is not None:
            pos = exc.pos_in_stream
            prefix = code[:pos]
            err_line = prefix.count('\n') + 1
            last_nl = prefix.rfind('\n')
            err_col = pos - last_nl if last_nl != -1 else pos + 1

        lines = code.splitlines()
        snippet = None
        if err_line and 1 <= err_line <= len(lines):
            snippet = lines[err_line - 1]

        if isinstance(exc, DedentError) or type(exc).__name__ == "DedentError":
            msg = str(exc)
            where = f" at line {err_line}, column {err_col}" if err_line else ""
            return ParseError(f"Indentation error: {msg}{where}", line=err_line, col=err_col, snippet=snippet)

        legacy = self._find_legacy_and(code)
        # The hint is only trustworthy when the parser choked *on* that 'and', or
        # right after it on the same line (the shape of `x is 1 and y is 2`).
        # An unrelated error elsewhere on the line — or a merely incomplete line,
        # which fails on the newline — must not be blamed on the removed
        # separator.
        token = getattr(exc, "token", None)
        tok_line = getattr(token, "line", None)
        tok_col = getattr(token, "column", None)
        tok_type = getattr(token, "type", "")
        if tok_line is not None and tok_col is not None:
            err_line, err_col = tok_line, tok_col

        structural = tok_type in ("_NEWLINE", "_INDENT", "_DEDENT", "$END")
        same_line = legacy is not None and err_line == legacy[0]
        on_and = same_line and legacy[1] - 1 <= err_col <= legacy[1] + 1
        after_and = same_line and err_col > legacy[1] + 1 and not structural
        # Failing on a *different* 'and' means the boolean operator lost an
        # operand (`a and and b`), which is not a separator problem.
        other_and = tok_type in ("_BOOL_AND", "_AND_SEP") and not on_and
        hint_used = legacy is not None and (
            err_line is None or ((on_and or after_and) and not other_and)
        )

        if hint_used:
            and_line, and_col = legacy
            message = (
                f"'and' is no longer a separator: use ',' "
                f"(offending 'and' at line {and_line}, column {and_col})"
            )
            return ParseError(
                message,
                line=and_line,
                col=and_col,
                snippet=snippet,
                help="Since 0.10.0 'and' is the boolean operator (short-circuit). "
                     "Separate arguments, parameters and struct fields with ',' — "
                     "e.g. 'calling f with 1, 2', 'weave g with x as int, y as int', "
                     "'with x is 1, y is 2'. ('map of K to V' still uses 'to'.)",
                note="The old 'and' list separator was removed in 0.10.0; see the "
                     "CHANGELOG migration notes (std/ and tests/ are already migrated).",
            )

        unexpected = ""
        token = getattr(exc, "token", None)
        if token is not None:
            unexpected = str(getattr(token, "value", token))
        elif getattr(exc, "char", None) is not None:
            unexpected = str(exc.char)

        # `at` is a postfix operator (CHEATSHEET §6.1 precedence), so the index
        # operand is an atom: `set xs at n - 1 is v` fails on the '-'. Point the
        # user at the parenthesised spelling instead of leaving a bare E0000.
        # (Reading `xs at n - 1` parses — as `(xs at n) - 1` — so this only bites
        # assignment targets, which is exactly where the mistake is silent-free.)
        if unexpected in ("+", "-", "*", "/", "%") and snippet and err_col:
            prefix = snippet[:max(err_col - 1, 0)]
            if re.search(r"\bat\s+[A-Za-z0-9_.\]\)]+\s*$", prefix):
                return ParseError(
                    f"The index after 'at' binds tighter than '{unexpected}': "
                    f"parenthesise the index expression",
                    line=err_line,
                    col=err_col,
                    snippet=snippet,
                    help=f"Write 'set xs at (n {unexpected} 1) is v' when the index is "
                         f"computed, or 'xs at n {unexpected} 1' when the arithmetic "
                         f"applies to the element that was read.",
                    note="'at' is a postfix operator, like '.field' or 'length': it "
                         "takes a single atom as its index. See the precedence table "
                         "in CHEATSHEET §6.1.",
                )

        where = f" at line {err_line}, column {err_col}" if err_line else ""
        message = "Syntax error"
        if unexpected:
            message += f": unexpected {unexpected!r}"
        message += where
        return ParseError(message, line=err_line, col=err_col, snippet=snippet)

    def pretty(self, code: str) -> str:
        """Parses code and returns human-readable formatted string of AST.

        Args:
            code: PenguScript source text.

        Returns:
            Pretty-printed string representation of AST.
        """
        tree = self.parse(code)
        return tree.pretty()

    def get_tokens(self, code: str) -> List[Token]:
        """Lexes PenguScript source code and returns list of tokens.

        Args:
            code: PenguScript source text.

        Returns:
            List of Lexer Token instances.
        """
        clean_code = strip_bom(code).rstrip() + '\n'
        return list(self.parser.lex(clean_code))


@dataclass
class InterpolatedPart:
    """Represents a text segment or an interpolated expression segment in a string."""
    is_expr: bool
    text: str


def extract_string_parts(raw_token_val: Any) -> Tuple[bool, bool, List[InterpolatedPart]]:
    """Parses a PenguScript string literal token into raw status, triple status, and parts.

    Handles raw strings (r\"...\", r\"\"\"...\"\"\"), triple-quoted strings with
    automatic dedent, and extracts balanced {...} expressions.

    Returns:
        (is_raw, is_triple, parts)
    """
    if isinstance(raw_token_val, Tree):
        if raw_token_val.children:
            return extract_string_parts(raw_token_val.children[0])
        return (False, False, [])
    raw_token_val = str(raw_token_val)
    if raw_token_val.startswith('r"""') and raw_token_val.endswith('"""'):
        is_raw = True
        content = raw_token_val[4:-3]
        is_triple = True
    elif raw_token_val.startswith('r"') and raw_token_val.endswith('"'):
        is_raw = True
        content = raw_token_val[2:-1]
        is_triple = False
    elif raw_token_val.startswith('"""') and raw_token_val.endswith('"""'):
        is_raw = False
        content = raw_token_val[3:-3]
        is_triple = True
    elif raw_token_val.startswith('"') and raw_token_val.endswith('"'):
        is_raw = False
        content = raw_token_val[1:-1]
        is_triple = False
    else:
        is_raw = False
        content = raw_token_val
        is_triple = False

    if is_triple:
        if content.startswith('\r\n'):
            content = content[2:]
        elif content.startswith('\n'):
            content = content[1:]
        lines = content.splitlines()
        non_empty = [l for l in lines if l.strip()]
        if non_empty:
            min_indent = min(len(l) - len(l.lstrip(' \t')) for l in non_empty)
            dedented_lines = []
            for l in lines:
                if l.strip():
                    dedented_lines.append(l[min_indent:])
                else:
                    dedented_lines.append("")
            if dedented_lines and not dedented_lines[-1].strip():
                dedented_lines.pop()
            content = "\n".join(dedented_lines) + ("\n" if lines and not lines[-1].strip() else "")

    if is_raw:
        return (is_raw, is_triple, [InterpolatedPart(is_expr=False, text=content)])

    parts: List[InterpolatedPart] = []
    i = 0
    n = len(content)
    last_pos = 0
    while i < n:
        ch = content[i]
        if ch == '\\' and i + 1 < n:
            if content.startswith('\\u{', i):
                close_b = content.find('}', i + 3)
                if close_b != -1:
                    i = close_b + 1
                    continue
            i += 2
            continue
        if ch == '{':
            start = i
            depth = 1
            j = i + 1
            in_str = None
            while j < n and depth > 0:
                cj = content[j]
                if cj == '\\' and j + 1 < n:
                    if content.startswith('\\u{', j):
                        close_b = content.find('}', j + 3)
                        if close_b != -1:
                            j = close_b + 1
                            continue
                    j += 2
                    continue
                if in_str:
                    if cj == in_str:
                        in_str = None
                elif cj in ('"', "'"):
                    in_str = cj
                elif cj == '{':
                    depth += 1
                elif cj == '}':
                    depth -= 1
                j += 1
            if depth == 0:
                expr_str = content[start + 1 : j - 1]
                if start > last_pos:
                    parts.append(InterpolatedPart(is_expr=False, text=content[last_pos:start]))
                parts.append(InterpolatedPart(is_expr=True, text=expr_str))
                i = j
                last_pos = j
                continue
        i += 1
    if last_pos < n:
        parts.append(InterpolatedPart(is_expr=False, text=content[last_pos:]))

    return (is_raw, is_triple, parts)

