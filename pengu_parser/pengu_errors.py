from __future__ import annotations
from typing import Optional, List, Dict, Any


class PenguError(Exception):
    """Base error class for PenguScript compiler errors with Rust-style diagnostics.

    Attributes:
        code: Error code identifier (e.g. 'E0001').
        message: Descriptive error message.
        file: Source filename where error occurred.
        line: 1-indexed line number in source code.
        col: 1-indexed column number in source code.
        snippet: Source code snippet corresponding to the error line.
        span_start: Starting column for underline carets.
        span_end: Ending column for underline carets.
        help: Optional guidance suggestion string for user.
        note: Optional contextual explanation note.
        label: Optional inline label attached to the caret underline.
        all_errors: Optional list of all accumulated errors during check.
    """

    def __init__(
        self,
        message: str = "",
        code: str = "E0000",
        file: str = "main.pengu",
        line: Optional[int] = None,
        col: Optional[int] = None,
        snippet: Optional[str] = None,
        span_start: Optional[int] = None,
        span_end: Optional[int] = None,
        help: Optional[str] = None,
        note: Optional[str] = None,
        label: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.file = file or "main.pengu"
        self.line = line if line is not None else 1
        col_val = col if col is not None else 1
        self.col = col_val
        self.snippet = snippet
        self.span_start = span_start if span_start is not None else col_val
        self.span_end = span_end
        self.help = help
        self.note = note
        self.label = label
        self.all_errors: List[PenguError] = []

    def __str__(self) -> str:
        loc = f"[line {self.line}, col {self.col}] " if self.line is not None else ""
        return f"{loc}{self.message}"

    def render(self, source_code: Optional[str] = None, use_color: bool = False) -> str:
        """Renders error in Rust compiler style with gutter, carets, help and note.

        Args:
            source_code: Optional full source text to extract context from.
            use_color: If True, formats output with ANSI terminal colors.

        Returns:
            Formatted diagnostic string.
        """
        src = source_code if source_code is not None else (self.snippet or " ")
        reporter = ErrorReporter(source=src, filename=self.file)
        return reporter.report(self, use_color=use_color)


class SemanticError(PenguError):
    """General semantic error in PenguScript AST."""
    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        col: Optional[int] = None,
        column: Optional[int] = None,
        code: str = "E0000",
        file: str = "main.pengu",
        snippet: Optional[str] = None,
        span_start: Optional[int] = None,
        span_end: Optional[int] = None,
        help: Optional[str] = None,
        note: Optional[str] = None,
        label: Optional[str] = None,
    ):
        resolved_col = col if col is not None else column
        super().__init__(
            message=message,
            code=code,
            file=file,
            line=line,
            col=resolved_col,
            snippet=snippet,
            span_start=span_start,
            span_end=span_end,
            help=help,
            note=note,
            label=label,
        )
        self.column = resolved_col or 1


class ParseError(SemanticError):
    """E0000: the source text could not be parsed (syntax error).

    Raised by ``PenguParser.parse`` instead of leaking a raw Lark exception, so
    the CLI/LSP can report syntax problems with the usual
    ``[Ecode] message`` + ``help:`` / ``note:`` shape. Kept on the generic E0000
    code: syntax problems share the "not valid source" bucket with the other
    infrastructure errors instead of consuming a new semantic code.
    """
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None,
                 column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0000")
        kwargs.setdefault(
            "help",
            "Check the syntax around this position (see LANGUAGE.md / CHEATSHEET.md).",
        )
        kwargs.setdefault(
            "note",
            "PenguScript parses indentation-sensitive blocks: statements in a block "
            "must be indented consistently, and argument/parameter/field lists are "
            "separated with ','.",
        )
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class ConstInsideWeaveError(SemanticError):
    """E0001: const declared inside weave / function body."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0001")
        kwargs.setdefault("help", "Move constant declaration outside the function or use 'let' / 'var' for local variables.")
        kwargs.setdefault("note", "PenguScript enforces V-safety: constants are top-level globals and locals are let/var.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class VarLetTopLevelError(SemanticError):
    """E0002: var/let declared at top-level."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0002")
        kwargs.setdefault("help", "Use 'const' for top-level definitions, or move inside a function. For stateful modules, use accessor weaves with 'static var' or an explicit context struct.")
        kwargs.setdefault("note", "Global mutable state is forbidden in PenguScript to guarantee safety.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class SelfDotAccessError(SemanticError):
    """E0003: self accessed with dot instead of arrow."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0003")
        kwargs.setdefault("help", "Change 'self.' to 'self->'.")
        kwargs.setdefault("note", "'self' in enchanting is always a reference (ref to SelfType).")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class UndefinedIdentifierError(SemanticError):
    """E0004: identifier not defined in symbol table."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0004")
        kwargs.setdefault("help", "Check if the variable or function name is misspelled or declared in this scope.")
        kwargs.setdefault("note", "All variables must be defined before use.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class TypeMismatchError(SemanticError):
    """E0005: types incompatible."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0005")
        kwargs.setdefault("help", "Ensure the value type matches the expected type or use explicit conversion 'to <Type>'.")
        kwargs.setdefault("note", "PenguScript requires type safety and explicit conversions.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class MutabilityError(SemanticError):
    """E0006: assignment to immutable let binding or constant."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0006")
        kwargs.setdefault("help", "Declare the variable with 'var' instead of 'let' to allow mutation.")
        kwargs.setdefault("note", "'let' bindings are immutable by default.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class InvalidControlFlowError(SemanticError):
    """E0007: break/continue outside loop."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0007")
        kwargs.setdefault("help", "Remove the control flow statement or place it inside a 'for' or 'while' loop block.")
        kwargs.setdefault("note", "Control flow operations 'break' and 'continue' require an enclosing loop.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class InvalidMemoryOpError(SemanticError):
    """E0008: invalid sigil/banish on literal/const."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0008")
        kwargs.setdefault("help", "Only mutable variables and memory references can be used with this memory operation.")
        kwargs.setdefault("note", "Memory safety requires valid pointer targets.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class InvalidWithTargetError(SemanticError):
    """E0009: leading dot access outside with block."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0009")
        kwargs.setdefault("help", "Wrap the call in a 'with' block (e.g. 'with player:') or use direct object access.")
        kwargs.setdefault("note", "Leading dot notation '.name' is only valid inside an active 'with' block.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class GenericTypeMissingArgsError(SemanticError):
    """E0021: Generic type used without required type arguments."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0021")
        kwargs.setdefault("help", "Provide type arguments using 'of', e.g. 'Pair of int and float'.")
        kwargs.setdefault("note", "All generic types must be instantiated with 'of' before use.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class TypeParamOutsideGenericError(SemanticError):
    """E0022: Type parameter used outside generic declaration context."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0022")
        kwargs.setdefault("help", "Declare type parameter with 'shard' or use a defined concrete type.")
        kwargs.setdefault("note", "Type parameters can only be used within generic declarations.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class MultipleManyParamsError(SemanticError):
    """E0023: Multiple many parameters in a function."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0023")
        kwargs.setdefault("help", "A function can only have one 'many' parameter.")
        kwargs.setdefault("note", "PenguScript allows at most one variadic parameter per function.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class ManyParamNotLastError(SemanticError):
    """E0024: many parameter is not the last parameter."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0024")
        kwargs.setdefault("help", "Move the 'many' parameter to the end of the parameter list.")
        kwargs.setdefault("note", "The variadic parameter 'many' must be the final parameter.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class MultipleInsigniaError(SemanticError):
    """E0026: Multiple insignia directives in a single file."""
    def __init__(self, message: str = "Multiple 'insignia' directives not allowed", line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0026")
        kwargs.setdefault("help", "Only one 'insignia' directive is allowed per module file.")
        kwargs.setdefault("note", "The 'insignia' directive defines the global C prefix for all subsequent declarations in this file.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class DuplicateOmenValueError(SemanticError):
    """E0027: Duplicate variant value in omen."""
    def __init__(self, message: str = "Duplicate variant value in omen", line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0027")
        kwargs.setdefault("help", "Ensure all omen variant values are unique.")
        kwargs.setdefault("note", "Omen variant values must be distinct.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class InvalidOmenPayloadValueError(SemanticError):
    """E0028: Value assignment in algebraic omen variant with payload."""
    def __init__(self, message: str = "Value assignment is not allowed on algebraic omen variants with payload ('with')", line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0028")
        kwargs.setdefault("help", "Remove 'is <value>' from algebraic variants with 'with'.")
        kwargs.setdefault("note", "Explicit numerical values are only supported on simple enums without payload.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class InvalidOmenConstantValueError(SemanticError):
    """E0029: Non-constant or non-integer value in omen variant."""
    def __init__(self, message: str = "Omen variant value must be a compile-time integer constant", line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0029")
        kwargs.setdefault("help", "Use a compile-time integer literal or constant expression.")
        kwargs.setdefault("note", "Omen values must evaluate to an integer at compile time.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class ConceptMethodMismatchError(SemanticError):
    """E0030: Concept method signature mismatch in bind implementation."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0030")
        kwargs.setdefault("help", "Ensure parameter and return types match the concept method declaration.")
        kwargs.setdefault("note", "Methods in 'bind' blocks must have signatures identical to the concept definition.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class UnimplementedConceptMethodError(SemanticError):
    """E0031: Missing required concept method implementation."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0031")
        kwargs.setdefault("help", "Implement all methods declared in the concept.")
        kwargs.setdefault("note", "A 'bind' block must provide implementations for every method of the concept.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class ConceptBoundNotSatisfiedError(SemanticError):
    """E0032: Generic type argument does not implement required concept bound."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0032")
        kwargs.setdefault("help", "Bind the required concept to the type using 'bind Type with Concept:'.")
        kwargs.setdefault("note", "Generic type arguments must satisfy all concept bounds declared in the 'where' clause.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class InvalidRitualSelfAccessError(SemanticError):
    """E0033: Using 'self' inside a ritual (static) method."""
    def __init__(self, message: str = "'self' cannot be used inside a 'ritual' method", line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0033")
        kwargs.setdefault("help", "Remove 'self' or remove the 'ritual' modifier to make this an instance method.")
        kwargs.setdefault("note", "'ritual' methods are static/associated functions and do not have an instance 'self'.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class InvalidRitualCallError(SemanticError):
    """E0034: Calling instance method statically or ritual method on instance."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0034")
        kwargs.setdefault("help", "Call ritual methods on the type (e.g. Type.method) and instance methods on an object.")
        kwargs.setdefault("note", "Ritual methods are associated with the type, while instance methods require an object.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)



class ArraySizeMismatchError(SemanticError):
    """E0041: Array literal dimensions or row length do not match declared size."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0041")
        kwargs.setdefault("help", "Ensure each row and the total number of rows match the declared array size.")
        kwargs.setdefault("note", "Fixed-size arrays require exact dimension matching at compile time.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class UnknownArrayDimensionError(SemanticError):
    """E0015: Array dimension size is unknown and cannot be inferred."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0015")
        kwargs.setdefault("help", "Specify all dimensions (e.g. 'array of array of T with size M with size N') or initialize with full literal rows.")
        kwargs.setdefault("note", "C requires fixed array sizes for all dimensions.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)



class InvalidRangeError(SemanticError):
    """E0042: Invalid range expression bounds."""
    def __init__(self, message: str = "Invalid range: 'start' must be less than or equal to 'end' when both bounds are known at compile time", line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0042")
        kwargs.setdefault("help", "Ensure the range start is less than or equal to end.")
        kwargs.setdefault("note", "Ranges must have valid ascending bounds when known at compile time.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class PrivateSymbolAccessError(SemanticError):
    """E0043: Attempted access to private symbol from another module."""
    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0043")
        kwargs.setdefault("help", "Symbols starting with '_' are private. Use a name without a leading underscore to make it public, or use 'insignia' for C binding prefixes.")
        kwargs.setdefault("note", "Symbols with a leading underscore are private to their defining module/rune.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)


class NonExhaustiveJudgeError(SemanticError):
    """E0044: Non-exhaustive judge expression without default else clause."""
    def __init__(self, message: str = "Judge over an omen/bool is not exhaustive and has no 'else ->' branch", line: Optional[int] = None, col: Optional[int] = None, column: Optional[int] = None, **kwargs):
        kwargs.setdefault("code", "E0044")
        kwargs.setdefault("help", "Add missing variant clauses or provide a default 'else ->' branch.")
        kwargs.setdefault("note", "All possible variants/cases must be covered in judge expressions.")
        super().__init__(message, line=line, col=col, column=column, **kwargs)



import difflib


def suggest_similar_identifier(target: str, candidates: list[str], max_suggestions: int = 1) -> list[str]:
    """Returns the closest identifier suggestions using fuzzy matching."""
    if not target or not candidates:
        return []
    return difflib.get_close_matches(target, candidates, n=max_suggestions, cutoff=0.6)


class ErrorReporter:
    """Renders PenguScript compiler errors and warnings in Rust-like diagnostic format."""

    def __init__(self, source: str = "", filename: str = "main.pengu"):
        self.source = source
        self.filename = filename
        self.lines = source.splitlines() if source else []

    def get_line(self, line_num: int) -> str:
        """Retrieves 1-indexed line from source text."""
        if 1 <= line_num <= len(self.lines):
            return self.lines[line_num - 1]
        return ""

    def report(self, err: PenguError, use_color: bool = True) -> str:
        red = "\033[1;31m" if use_color else ""
        cyan = "\033[1;36m" if use_color else ""
        blue = "\033[1;34m" if use_color else ""
        green = "\033[1;32m" if use_color else ""
        bold = "\033[1m" if use_color else ""
        reset = "\033[0m" if use_color else ""

        line_num = err.line or 1
        col_num = err.col or 1
        code_str = f"[{err.code}]" if getattr(err, "code", None) else ""
        
        header = f"{red}{bold}error{code_str}{reset}: {bold}{err.message}{reset}"
        loc_str = f"  {blue}-->{reset} {err.file or self.filename}:{line_num}:{col_num}"

        gutter_width = max(len(str(line_num + 1)), 2)
        bar = f"{blue}|{reset}"

        output = [header, loc_str, f"{' ' * gutter_width} {bar}"]

        lines = self.lines if self.lines else ([err.snippet] if err.snippet else [])
        if lines and 1 <= line_num <= len(lines):
            line_content = lines[line_num - 1]
            output.append(f"{str(line_num).rjust(gutter_width)} {bar} {line_content}")

            # Calcular ancho del subrayado
            span_start = max(1, err.span_start or col_num)
            span_end = err.span_end or (span_start + 1)
            left_pad = " " * (span_start - 1)
            width = max(1, span_end - span_start)
            carets = f"{red}{'^' * width}{reset}"
            label = f" {red}{err.label}{reset}" if getattr(err, "label", None) else ""

            output.append(f"{' ' * gutter_width} {bar} {left_pad}{carets}{label}")
        elif err.snippet:
            output.append(f"{str(line_num).rjust(gutter_width)} {bar} {err.snippet}")
            span_start = max(1, err.span_start or col_num)
            left_pad = " " * (span_start - 1)
            carets = f"{red}{'^' * max(1, (err.span_end - span_start) if err.span_end and err.span_end > span_start else len(err.snippet.strip()))}{reset}"
            label = f" {red}{err.label}{reset}" if getattr(err, "label", None) else ""
            output.append(f"{' ' * gutter_width} {bar} {left_pad}{carets}{label}")

        output.append(f"{' ' * gutter_width} {bar}")

        if getattr(err, "note", None):
            output.append(f"{' ' * gutter_width} {cyan}={reset} {bold}note{reset}: {err.note}")
        if getattr(err, "help", None):
            output.append(f"{' ' * gutter_width} {green}={reset} {bold}help{reset}: {err.help}")

        return "\n".join(output)

    def report_all(self, errors: List[PenguError], use_color: bool = False) -> str:
        """Renders multiple errors separated by newlines."""
        return "\n\n".join(self.report(err, use_color=use_color) for err in errors)
