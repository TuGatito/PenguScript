import re

from lark import Lark, Tree, Token
from lark.exceptions import UnexpectedInput as LarkUnexpectedInput
from lark.indenter import Indenter
from typing import List

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


class PenguParser:
    """LALR(1) parser for PenguScript v0.9.0 using embedded grammar."""
    _shared_parser = None

    def __init__(self):
        """Initializes Lark parser with embedded grammar and custom indenter."""
        if PenguParser._shared_parser is None:
            PenguParser._shared_parser = Lark(
                GRAMMAR,
                parser='lalr',
                postlex=PenguIndenter(),
                propagate_positions=True,
                start=['start', 'expr']
            )
        self.parser = PenguParser._shared_parser

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
            return ""

        out: List[str] = []
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith('#'):
                if stripped.startswith('##'):
                    rest = stripped[2:].strip()
                    if rest == '':
                        # Bare '##': start of a multi-line doc block.
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
                        out.append(blank(line))
                    else:
                        # '## doc' or '## doc ##' single-line documentation.
                        out.append(blank(line))
                else:
                    # Regular single-line '#' comment.
                    out.append(blank(line))
            else:
                out.append(line)
            i += 1
        return ''.join(out)

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
        clean_code = self._strip_comments(code).rstrip() + '\n'
        try:
            return self.parser.parse(clean_code, start='start')
        except LarkUnexpectedInput as exc:
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

    def _parse_error(self, code: str, exc: "LarkUnexpectedInput") -> "ParseError":
        """Converts a Lark syntax exception into a friendly :class:`ParseError`."""
        from .pengu_errors import ParseError

        err_line = getattr(exc, "line", None)
        err_col = getattr(exc, "column", None)

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

        lines = code.splitlines()
        snippet = None
        if err_line and 1 <= err_line <= len(lines):
            snippet = lines[err_line - 1]

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
        clean_code = code.rstrip() + '\n'
        return list(self.parser.lex(clean_code))


from dataclasses import dataclass


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

