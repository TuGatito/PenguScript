"""PenguScript Language Server Implementation using pygls."""

import asyncio
import os
import sys
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

# --- Critical: Force SelectorEventLoopPolicy on Windows ---
# Python 3.14+ defaults to ProactorEventLoop, which causes hangs with pygls
# in PyInstaller-frozen executables. Must be set before any asyncio usage.
# The API is deprecated in 3.14 and slated for removal in 3.16; we guard against that.
if sys.platform == "win32":
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass  # API removed in future Python; pygls may handle this internally

from pygls.lsp.server import LanguageServer
from lsprotocol.types import (
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_SAVE,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_SIGNATURE_HELP,
    TEXT_DOCUMENT_RENAME,
    TEXT_DOCUMENT_DOCUMENT_HIGHLIGHT,
    TEXT_DOCUMENT_FORMATTING,
    TEXT_DOCUMENT_DOCUMENT_SYMBOL,
    TEXT_DOCUMENT_FOLDING_RANGE,
    DidOpenTextDocumentParams,
    DidChangeTextDocumentParams,
    DidSaveTextDocumentParams,
    CompletionParams,
    CompletionOptions,
    HoverParams,
    DefinitionParams,
    SignatureHelpParams,
    SignatureHelp,
    SignatureInformation,
    ParameterInformation,
    SignatureHelpOptions,
    RenameParams,
    WorkspaceEdit,
    TextEdit,
    DocumentHighlightParams,
    DocumentHighlight,
    DocumentHighlightKind,
    DocumentFormattingParams,
    DocumentSymbolParams,
    DocumentSymbol,
    SymbolKind,
    FoldingRangeParams,
    FoldingRange,
    FoldingRangeKind,
    PublishDiagnosticsParams,
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
    Location,
)

from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import PenguError
from pengu_parser.pengu_symbols import SymbolTable
from pengu_parser.pengu_types import FnType

from .completions import get_completions
from .hover import get_hover, get_word_at_position


def uri_to_path(uri: str) -> str:
    """Converts a file URI to a filesystem path.

    Args:
        uri: RFC file URI (e.g. file:///path or file:///d:/path).

    Returns:
        Local filesystem path string.
    """
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme == "file":
        return urllib.request.url2pathname(parsed.path)
    return uri


def diagnostics_from_errors(errors: List[PenguError], code: str) -> List[Diagnostic]:
    """Converts PenguScript checker errors into LSP Diagnostic objects.

    Args:
        errors: List of PenguError instances.
        code: Source code text string.

    Returns:
        List of LSP Diagnostic items.
    """
    diags: List[Diagnostic] = []
    lines = code.splitlines() if code else []

    all_err_list: List[PenguError] = []
    seen = set()

    for err in errors:
        sub_list = getattr(err, "all_errors", None) or [err]
        for sub_err in sub_list:
            key = (getattr(sub_err, "code", ""), getattr(sub_err, "line", 0), getattr(sub_err, "col", 0), str(getattr(sub_err, "message", "")))
            if key not in seen:
                seen.add(key)
                all_err_list.append(sub_err)


    for err in all_err_list:
        err_line = err.line if err.line is not None else 1
        err_col = err.col if err.col is not None else 1

        start_line = max(0, err_line - 1)
        start_char = max(0, err_col - 1)

        # Determine end character
        line_len = len(lines[start_line]) if start_line < len(lines) else 0
        if getattr(err, "span_end", None) is not None and err.span_end > start_char:
            end_char = min(line_len, err.span_end) if line_len else err.span_end
        elif getattr(err, "span_start", None) and getattr(err, "span_end", None):
            end_char = min(line_len, err.span_end) if line_len else err.span_end
        else:
            word_len = 5
            end_char = min(line_len, start_char + word_len) if line_len else start_char + 1

        diag_range = Range(
            start=Position(line=start_line, character=start_char),
            end=Position(line=start_line, character=max(start_char + 1, end_char))
        )

        code_prefix = f"[{err.code}] " if getattr(err, "code", None) else ""
        msg_parts = [f"{code_prefix}{err.message}"]

        if getattr(err, "help", None):
            msg_parts.append(f"help: {err.help}")
        if getattr(err, "note", None):
            msg_parts.append(f"note: {err.note}")
        if getattr(err, "label", None):
            msg_parts.append(f"label: {err.label}")

        diags.append(
            Diagnostic(
                range=diag_range,
                message="\n".join(msg_parts),
                severity=DiagnosticSeverity.Error,
                code=getattr(err, "code", "E0000"),
                source="pengus"
            )
        )

    return diags


class PenguLanguageServer(LanguageServer):
    """Custom language server subclass storing parsed symbols and document buffers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._symbols: Dict[str, SymbolTable] = {}
        self._docs: Dict[str, str] = {}

    def get_document_source(self, uri: str) -> str:
        """Retrieves text document source code from pygls workspace, test cache, or filesystem fallback."""
        try:
            if hasattr(self.workspace, "get_text_document"):
                return self.workspace.get_text_document(uri).source
            if hasattr(self.workspace, "get_document"):
                return self.workspace.get_document(uri).source
        except Exception:
            pass
        if hasattr(self, "_docs") and uri in self._docs:
            return self._docs[uri]
        file_path = uri_to_path(uri)
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return ""

    def publish_diagnostics(self, uri: str, diagnostics: List[Diagnostic]) -> None:
        """Publishes LSP diagnostics to the client using the native pygls method."""
        print(f"[LSP] Publishing {len(diagnostics)} diagnostics for {uri}", file=sys.stderr)
        try:
            self.text_document_publish_diagnostics(
                PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
            )
        except Exception as e:
            print(f"[LSP ERROR] Failed to publish diagnostics for {uri}: {e}", file=sys.stderr)


def _get_version() -> str:
    """Reads version from VERSION file."""
    version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION")
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        version_file = os.path.join(meipass, "VERSION")
    try:
        with open(version_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.1.0"


server = PenguLanguageServer("pengus-lsp", f"v{_get_version()}")


def validate_document(uri: str, source: str) -> None:
    """Parses and type-checks a document, publishing diagnostics and updating symbol table.

    Args:
        uri: Document URI.
        source: Text content of the document.
    """
    import sys
    print(f"[LSP] validate_document called for {uri} ({len(source)} chars)", file=sys.stderr)
    server._docs[uri] = source
    file_path = uri_to_path(uri)
    base_dir = os.path.dirname(file_path) if os.path.exists(file_path) else os.getcwd()

    parser = PenguParser()
    checker = PenguChecker(base_dir=base_dir)

    try:
        tree = parser.parse(source)
        checker.check(tree, source=source, filename=file_path)
        # If check succeeds without exception: clear diagnostics
        print(f"[LSP] Validation clean (0 errors) for {uri}", file=sys.stderr)
        server.publish_diagnostics(uri, [])
        server._symbols[uri] = checker.symbols

    except PenguError as e:
        all_errs = e.all_errors if hasattr(e, "all_errors") and e.all_errors else [e]
        print(f"[LSP] Validation found {len(all_errs)} semantic error(s) for {uri}", file=sys.stderr)
        diags = diagnostics_from_errors(all_errs, source)
        server.publish_diagnostics(uri, diags)
        if hasattr(checker, "symbols"):
            server._symbols[uri] = checker.symbols

    except Exception as e:
        # Fallback for syntax/parser exceptions (e.g. Lark UnexpectedToken, UnexpectedCharacters)
        print(f"[LSP] Validation caught syntax/parser error for {uri}: {e}", file=sys.stderr)
        err_line = getattr(e, "line", 1) or 1
        err_col = getattr(e, "column", 1) or 1
        start_l = max(0, err_line - 1)
        start_c = max(0, err_col - 1)
        diag = Diagnostic(
            range=Range(start=Position(line=start_l, character=start_c), end=Position(line=start_l, character=start_c + 1)),
            message=str(e),
            severity=DiagnosticSeverity.Error,
            source="pengus"
        )
        server.publish_diagnostics(uri, [diag])



@server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(params: DidOpenTextDocumentParams):
    """Handles textDocument/didOpen notifications."""
    uri = params.text_document.uri
    source = server.get_document_source(uri) or params.text_document.text
    validate_document(uri, source)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(params: DidChangeTextDocumentParams):
    """Handles textDocument/didChange notifications."""
    uri = params.text_document.uri
    
    # 1. Usar el helper robusto en lugar de get_text_document directamente
    source = server.get_document_source(uri)

    # 2. Mantener tu lógica de Full Sync por si acaso
    if params.content_changes:
        first_change = params.content_changes[0]
        if not getattr(first_change, 'range', None):
            source = first_change.text

    if source:
        server._docs[uri] = source
        validate_document(uri, source)


@server.feature(TEXT_DOCUMENT_DID_SAVE)
def did_save(params: DidSaveTextDocumentParams):
    """Handles textDocument/didSave notifications."""
    uri = params.text_document.uri
    source = server.get_document_source(uri)
    if source:
        validate_document(uri, source)


def path_to_uri(path: str) -> str:
    """Converts a filesystem path to a file URI."""
    from pathlib import Path
    try:
        return Path(os.path.abspath(path)).as_uri()
    except Exception:
        normalized_path = path.replace("\\", "/")
        return f"file:///{normalized_path}"


@server.feature(
    TEXT_DOCUMENT_COMPLETION,
    CompletionOptions(trigger_characters=[".", ">"])
)
def completions(params: CompletionParams):
    """Handles textDocument/completion requests."""
    uri = params.text_document.uri
    symbols = server._symbols.get(uri)
    doc_text = server.get_document_source(uri)
    lines = doc_text.splitlines() if doc_text else []
    line_prefix = ""
    if 0 <= params.position.line < len(lines):
        curr_line = lines[params.position.line]
        line_prefix = curr_line[:params.position.character]
    return get_completions(uri, params.position, symbols, line_prefix)


@server.feature(TEXT_DOCUMENT_HOVER)
def hover(params: HoverParams):
    """Handles textDocument/hover requests."""
    uri = params.text_document.uri
    symbols = server._symbols.get(uri)
    doc_text = server.get_document_source(uri)
    return get_hover(uri, params.position, symbols, doc_text)


@server.feature(TEXT_DOCUMENT_DEFINITION)
def definition(params: DefinitionParams):
    """Handles textDocument/definition requests."""
    import re
    uri = params.text_document.uri
    symbols = server._symbols.get(uri)
    doc_text = server.get_document_source(uri)
    if not symbols or not doc_text:
        return None

    word = get_word_at_position(doc_text, params.position)
    if not word:
        return None

    target_sym = None
    target_uri = uri

    # 1. Check for dotted module member (e.g. spark.println)
    if "." in word:
        parts = word.split(".")
        mod_name = parts[-2]
        member_name = parts[-1]
        mod_sym = symbols.lookup(mod_name)
        if mod_sym and mod_sym.module_scope:
            target_sym = mod_sym.module_scope.symbols.get(member_name)
            if target_sym and target_sym.file_path:
                target_uri = path_to_uri(target_sym.file_path)
            elif mod_sym.file_path:
                target_uri = path_to_uri(mod_sym.file_path)

    # 2. Check if cursor was positioned on a member following a module dot
    if not target_sym:
        lines = doc_text.splitlines()
        if 0 <= params.position.line < len(lines):
            line_str = lines[params.position.line]
            col = params.position.character
            prefix_to_word = line_str[:col]
            dot_m = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)?$", prefix_to_word)
            if dot_m:
                mod_name = dot_m.group(1)
                mod_sym = symbols.lookup(mod_name)
                if mod_sym and mod_sym.module_scope and word in mod_sym.module_scope.symbols:
                    target_sym = mod_sym.module_scope.symbols[word]
                    if target_sym and target_sym.file_path:
                        target_uri = path_to_uri(target_sym.file_path)
                    elif mod_sym.file_path:
                        target_uri = path_to_uri(mod_sym.file_path)

    # 3. Fallback to direct symbol lookup
    if not target_sym:
        cursor_line = params.position.line + 1
        target_sym = symbols.lookup_at(word, cursor_line) if hasattr(symbols, "lookup_at") else symbols.lookup(word)
        if target_sym and target_sym.file_path:
            target_uri = path_to_uri(target_sym.file_path)

    if target_sym and target_sym.line is not None and target_sym.column is not None:
        line = max(0, target_sym.line - 1)
        col = max(0, target_sym.column - 1)
        return Location(
            uri=target_uri,
            range=Range(
                start=Position(line=line, character=col),
                end=Position(line=line, character=col + len(target_sym.name))
            )
        )
    return None


@server.feature(
    TEXT_DOCUMENT_SIGNATURE_HELP,
    SignatureHelpOptions(trigger_characters=["(", ",", " "])
)
def signature_help(params: SignatureHelpParams) -> Optional[SignatureHelp]:
    """Handles textDocument/signatureHelp requests."""
    import re
    uri = params.text_document.uri
    symbols = server._symbols.get(uri)
    doc_text = server.get_document_source(uri)
    if not symbols or not doc_text:
        return None

    lines = doc_text.splitlines()
    if not (0 <= params.position.line < len(lines)):
        return None

    line_str = lines[params.position.line][:params.position.character]

    # Detecta llamadas tipo `calling func with a, b` o `calling mod.func with a` o `func(a, b`
    calling_m = re.search(r"\bcalling\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)(?:\s+with\s+|\s+)?(.*)$", line_str)
    paren_m = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\(([^()]*)$", line_str)

    func_path = None
    args_sub = ""
    if calling_m:
        func_path = calling_m.group(1)
        args_sub = calling_m.group(2) or ""
    elif paren_m:
        func_path = paren_m.group(1)
        args_sub = paren_m.group(2) or ""
    else:
        return None

    # Contar argumentos activos según comas o la palabra 'and'
    active_param = 0
    if args_sub.strip():
        active_param = max(0, len(re.split(r",|\band\b", args_sub)) - 1)

    # Buscar el símbolo de la función
    sym = None
    if "." in func_path:
        parts = func_path.split(".")
        mod_sym = symbols.lookup(parts[0])
        if mod_sym and getattr(mod_sym, "module_scope", None):
            sym = mod_sym.module_scope.symbols.get(parts[1])
    else:
        cursor_line = params.position.line + 1
        sym = symbols.lookup_at(func_path, cursor_line) if hasattr(symbols, "lookup_at") else symbols.lookup(func_path)

    if not sym:
        return None

    fn_type = getattr(sym, "type", None)
    if not isinstance(fn_type, FnType) and not hasattr(fn_type, "params"):
        return None

    # Construir información de los parámetros
    param_infos = []
    param_labels = []
    for p in fn_type.params:
        p_name = p[0] if isinstance(p, (tuple, list)) else getattr(p, "name", "arg")
        p_type = p[1] if isinstance(p, (tuple, list)) else getattr(p, "type", "any")
        label = f"{p_name} as {p_type}"
        param_labels.append(label)
        param_infos.append(ParameterInformation(label=label))

    ret_str = f" into {fn_type.return_type}" if getattr(fn_type, "return_type", None) else ""
    decl_label = f"weave {sym.name} with {', '.join(param_labels)}{ret_str}"

    sig_info = SignatureInformation(
        label=decl_label,
        documentation=sym.doc or None,
        parameters=param_infos
    )

    return SignatureHelp(
        signatures=[sig_info],
        active_signature=0,
        active_parameter=min(max(0, active_param), max(0, len(param_infos) - 1))
    )


@server.feature(TEXT_DOCUMENT_DOCUMENT_HIGHLIGHT)
def document_highlight(params: DocumentHighlightParams) -> Optional[List[DocumentHighlight]]:
    """Handles textDocument/documentHighlight requests."""
    import re
    uri = params.text_document.uri
    doc_text = server.get_document_source(uri)
    if not doc_text:
        return None

    word = get_word_at_position(doc_text, params.position)
    if not word:
        return None

    # Limpiar posibles prefijos como `self->`
    clean_word = word.replace("self->", "").replace(".", "").strip()
    if not clean_word:
        return None

    highlights: List[DocumentHighlight] = []
    lines = doc_text.splitlines()

    pattern = re.compile(rf"\b{re.escape(clean_word)}\b")
    for line_idx, line in enumerate(lines):
        for match in pattern.finditer(line):
            start_col = match.start()
            end_col = match.end()
            
            # Detectar si es una escritura (declaración o set)
            prefix = line[:start_col].strip()
            kind = DocumentHighlightKind.Read
            if prefix.startswith(("var ", "let ", "const ", "set ")) or " is " in line:
                kind = DocumentHighlightKind.Write

            highlights.append(
                DocumentHighlight(
                    range=Range(
                        start=Position(line=line_idx, character=start_col),
                        end=Position(line=line_idx, character=end_col)
                    ),
                    kind=kind
                )
            )

    return highlights


@server.feature(TEXT_DOCUMENT_RENAME)
def rename_symbol(params: RenameParams) -> Optional[WorkspaceEdit]:
    """Handles textDocument/rename requests."""
    import re
    uri = params.text_document.uri
    doc_text = server.get_document_source(uri)
    if not doc_text:
        return None

    old_word = get_word_at_position(doc_text, params.position)
    if not old_word:
        return None

    clean_old = old_word.replace("self->", "").replace(".", "").strip()
    new_name = params.new_name.strip()
    if not clean_old or not new_name or clean_old == new_name:
        return None

    lines = doc_text.splitlines()
    edits: List[TextEdit] = []
    pattern = re.compile(rf"\b{re.escape(clean_old)}\b")

    for line_idx, line in enumerate(lines):
        for match in pattern.finditer(line):
            edits.append(
                TextEdit(
                    range=Range(
                        start=Position(line=line_idx, character=match.start()),
                        end=Position(line=line_idx, character=match.end())
                    ),
                    new_text=new_name
                )
            )

    return WorkspaceEdit(changes={uri: edits})


@server.feature(TEXT_DOCUMENT_FORMATTING)
def document_formatting(params: DocumentFormattingParams) -> Optional[List[TextEdit]]:
    """Handles textDocument/formatting requests."""
    import re
    uri = params.text_document.uri
    doc_text = server.get_document_source(uri)
    if not doc_text:
        return None

    lines = doc_text.splitlines()
    formatted_lines = []
    tab_size = params.options.tab_size if hasattr(params, "options") and params.options else 2
    indent_unit = " " * tab_size if getattr(params.options, "insert_spaces", True) else "\t"

    for line in lines:
        stripped_right = line.rstrip()
        if not stripped_right:
            formatted_lines.append("")
            continue

        # Normalizar sangría inicial
        leading_spaces = len(stripped_right) - len(stripped_right.lstrip(" "))
        leading_tabs = len(stripped_right) - len(stripped_right.lstrip("\t"))
        
        indent_level = 0
        if leading_tabs > 0:
            indent_level = leading_tabs
        elif leading_spaces > 0:
            indent_level = leading_spaces // tab_size

        content = stripped_right.strip()

        # Pequeños ajustes cosméticos de espaciado estándar si no es un comentario
        if not content.startswith("#"):
            content = re.sub(r"\s+is\s+", " is ", content)
            content = re.sub(r"\s+as\s+", " as ", content)
            content = re.sub(r"\s+into\s+", " into ", content)
            content = re.sub(r",\s*", ", ", content)

        formatted_lines.append((indent_unit * indent_level) + content)

    new_full_text = "\n".join(formatted_lines) + ("\n" if doc_text.endswith("\n") else "")
    
    # Reemplazar todo el documento con el texto formateado
    last_line = max(0, len(lines) - 1)
    last_char = len(lines[last_line]) if lines else 0

    return [
        TextEdit(
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=last_line, character=last_char)
            ),
            new_text=new_full_text
        )
    ]


@server.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbols(params: DocumentSymbolParams) -> Optional[List[DocumentSymbol]]:
    """Generates document symbols for the outline and breadcrumbs view."""
    uri = params.text_document.uri
    symbols = server._symbols.get(uri)
    doc_text = server.get_document_source(uri)
    if not symbols or not doc_text:
        return None

    lines = doc_text.splitlines()
    doc_symbols: List[DocumentSymbol] = []

    table_dict = getattr(symbols, "table", None)
    if table_dict is None and hasattr(symbols, "global_scope"):
        table_dict = symbols.global_scope.symbols

    if not table_dict:
        return None

    for name, sym in table_dict.items():
        if sym.line is None:
            continue

        sym_line = max(0, sym.line - 1)
        sym_col = max(0, (sym.column or 1) - 1)
        line_len = len(lines[sym_line]) if sym_line < len(lines) else 1

        sym_range = Range(
            start=Position(line=sym_line, character=0),
            end=Position(line=sym_line, character=line_len)
        )
        selection_range = Range(
            start=Position(line=sym_line, character=sym_col),
            end=Position(line=sym_line, character=sym_col + len(sym.name))
        )

        kind = SymbolKind.Variable
        detail = ""
        children: List[DocumentSymbol] = []

        if sym.kind in ("weave", "function", "declare"):
            kind = SymbolKind.Function
            detail = f"into {sym.type.return_type}" if getattr(sym, "type", None) and hasattr(sym.type, "return_type") else "function"
        elif sym.kind == "rune":
            kind = SymbolKind.Struct
            detail = "rune"
            if hasattr(sym.type, "fields"):
                for f_name, f_type in sym.type.fields.items():
                    children.append(
                        DocumentSymbol(
                            name=f_name,
                            kind=SymbolKind.Field,
                            detail=str(f_type),
                            range=sym_range,
                            selection_range=sym_range
                        )
                    )
        elif sym.kind == "echo":
            kind = SymbolKind.Enum
            detail = "echo"
        elif sym.kind == "omen":
            kind = SymbolKind.Enum
            detail = "omen"
            if hasattr(sym.type, "variants"):
                for v_name in sym.type.variants.keys():
                    children.append(
                        DocumentSymbol(
                            name=v_name,
                            kind=SymbolKind.EnumMember,
                            detail="variant",
                            range=sym_range,
                            selection_range=sym_range
                        )
                    )
        elif sym.kind == "alias":
            kind = SymbolKind.TypeParameter
            detail = "alias"
        elif sym.kind == "const":
            kind = SymbolKind.Constant
            detail = str(sym.type)
        elif sym.kind == "import":
            kind = SymbolKind.Module
            detail = "import"
        else:
            continue

        doc_symbols.append(
            DocumentSymbol(
                name=sym.name,
                kind=kind,
                detail=detail,
                range=sym_range,
                selection_range=selection_range,
                children=children if children else None
            )
        )

    return doc_symbols


@server.feature(TEXT_DOCUMENT_FOLDING_RANGE)
def folding_ranges(params: FoldingRangeParams) -> Optional[List[FoldingRange]]:
    """Calculates code folding regions based on indentation and AST scopes."""
    uri = params.text_document.uri
    doc_text = server.get_document_source(uri)
    if not doc_text:
        return None

    lines = doc_text.splitlines()
    ranges: List[FoldingRange] = []
    
    # 1. Plegado basado en bloques indentados (Python/PenguScript style)
    stack: List[Tuple[int, int]] = []  # (indent_level, start_line)

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" \t"))

        while stack and stack[-1][0] >= indent:
            _, start_line = stack.pop()
            if idx - 1 > start_line:
                ranges.append(
                    FoldingRange(
                        start_line=start_line,
                        end_line=idx - 1,
                        kind=FoldingRangeKind.Region
                    )
                )

        if line.rstrip().endswith(":"):
            stack.append((indent, idx))

    while stack:
        _, start_line = stack.pop()
        if len(lines) - 1 > start_line:
            ranges.append(
                FoldingRange(
                    start_line=start_line,
                    end_line=len(lines) - 1,
                    kind=FoldingRangeKind.Region
                )
            )

    # 2. Plegado para bloques de comentarios multilínea (## ... ## o consecutivos)
    in_comment_block = False
    comment_start = 0

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            if not in_comment_block:
                in_comment_block = True
                comment_start = idx
        else:
            if in_comment_block:
                in_comment_block = False
                if idx - 1 > comment_start:
                    ranges.append(
                        FoldingRange(
                            start_line=comment_start,
                            end_line=idx - 1,
                            kind=FoldingRangeKind.Comment
                        )
                    )

    if in_comment_block and len(lines) - 1 > comment_start:
        ranges.append(
            FoldingRange(
                start_line=comment_start,
                end_line=len(lines) - 1,
                kind=FoldingRangeKind.Comment
            )
        )

    return ranges

