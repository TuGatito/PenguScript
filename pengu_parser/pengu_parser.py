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

    def parse(self, code: str) -> Tree:
        """Parses PenguScript source code into a Lark AST Tree.

        Args:
            code: PenguScript source text.

        Returns:
            Lark AST Tree root.
        """
        lines = []
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith('#') and not stripped.startswith('##'):
                lines.append('')
            else:
                lines.append(line)
        clean_code = '\n'.join(lines).rstrip() + '\n'
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
