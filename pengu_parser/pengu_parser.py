from lark import Lark, Tree, Token
from lark.indenter import Indenter
from typing import List

from .pengu_grammar import GRAMMAR


class PenguIndenter(Indenter):
    """Custom Lark indenter for indentation-significant parsing in PenguScript."""
    NL_type = '_NEWLINE'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 2


class PenguParser:
    """LALR(1) parser for PenguScript v0.6 using embedded grammar."""
    _shared_parser = None

    def __init__(self):
        """Initializes Lark parser with embedded grammar and custom indenter."""
        if PenguParser._shared_parser is None:
            PenguParser._shared_parser = Lark(
                GRAMMAR,
                parser='lalr',
                postlex=PenguIndenter(),
                propagate_positions=True,
                start='start'
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
        """
        clean_code = self._strip_comments(code).rstrip() + '\n'
        return self.parser.parse(clean_code)

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
