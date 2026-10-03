"""PenguScript Language Server Implementation using pygls."""

import asyncio
import hashlib
import os
import sys
import threading
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
    TEXT_DOCUMENT_IMPLEMENTATION,
    TEXT_DOCUMENT_REFERENCES,
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
    ImplementationParams,
    ReferenceParams,
    ReferenceContext,
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
    TEXT_DOCUMENT_CODE_ACTION,
    CodeActionParams,
    TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    SemanticTokens,
    SemanticTokensLegend,
    SemanticTokensOptions,
    SemanticTokensParams,
    TEXT_DOCUMENT_INLAY_HINT,
    InlayHint,
    InlayHintKind,
    InlayHintParams,
    TEXT_DOCUMENT_CODE_LENS,
    CodeLens,
    CodeLensParams,
    Command,
    TEXT_DOCUMENT_ON_TYPE_FORMATTING,
    DocumentOnTypeFormattingParams,
    DocumentOnTypeFormattingOptions,
)

from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import PenguError
from pengu_parser.pengu_symbols import SymbolTable
from pengu_parser.pengu_types import FnType

from .formatting import format_pengu_source, load_format_config
from .completions import get_completions
from .hover import get_hover, get_word_at_position
from .code_actions import (
    add_missing_import_action,
    remove_unused_variable_action,
    implement_concept_methods_action,
    declaration_locations,
    word_occurrences_in_roots,
)


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


# Milliseconds of quiet typing to wait before revalidating a document after a
# didChange notification. Batching keystrokes this way cuts full parse+check
# runs from once-per-keystroke to once per pause in typing.
VALIDATION_DEBOUNCE_S = 0.35


class PenguLanguageServer(LanguageServer):
    """Custom language server subclass storing parsed symbols and document buffers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._symbols: Dict[str, SymbolTable] = {}
        self._docs: Dict[str, str] = {}
        # Per-URI debounced validation tasks (didChange batching).
        self._validate_tasks: Dict[str, "asyncio.Task[None]"] = {}
        # uri -> (source content hash, last published diagnostics). Revalidating
        # a document whose content did not change is skipped.
        self._validation_cache: Dict[str, Tuple[str, List[Diagnostic]]] = {}
        # Guards _symbols / _docs / _validation_cache against worker threads.
        self._validation_lock = threading.Lock()

    def cancel_pending_validation(self, uri: str) -> None:
        """Cancels any scheduled (debounced) validation pending for a URI."""
        task = self._validate_tasks.pop(uri, None)
        if task is not None:
            task.cancel()

    @staticmethod
    def _source_hash(source: str) -> str:
        """Stable content hash used to skip redundant validations."""
        return hashlib.sha1(source.encode("utf-8", "replace")).hexdigest()

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

# Server-wide module cache: import alias -> module Scope (from any document that
# has been validated successfully). Lets completions show the members of an
# imported module (std.spark, project modules, aliased imports) even when the
# current document has not been validated yet or only holds partial symbols.
# Modules do not change while the LSP session is alive, so the cache is never
# invalidated except by being refreshed with fresher scopes on each check.
_MODULE_CACHE: Dict[str, object] = {}


def _refresh_module_cache(symbols) -> None:
    """Records every resolved import's module_scope into ``_MODULE_CACHE``.

    The checker resolves an import by loading and collecting the target module
    into a ``Scope(kind="module")`` attached to the import symbol. Each module
    symbol is registered in the global scope of the *importing* document, so
    the cache is refreshed whenever any document is checked.

    Args:
        symbols: SymbolTable produced by a checker run (may be partial when the
            document has semantic errors).
    """
    if symbols is None:
        return
    global_scope = getattr(symbols, "global_scope", None)
    if global_scope is None:
        return
    for name, sym in getattr(global_scope, "symbols", {}).items():
        if getattr(sym, "kind", "") == "import":
            mod_scope = getattr(sym, "module_scope", None)
            # Only cache resolved, non-empty scopes under a non-empty alias;
            # empty scopes (module file missing / failed to load) must not be
            # cached, or completion could serve stale members later.
            if mod_scope is not None and name and getattr(mod_scope, "symbols", None):
                # Keyed under the import alias (e.g. 'spark' or an explicit
                # alias from `import std.spark as sp`).
                _MODULE_CACHE[name] = mod_scope


def _style_warning_diagnostics(source: str) -> List[Diagnostic]:
    """Runs lightweight lint checks over a document that parsed cleanly.

    Produces warnings (not errors) for unused imports and unused local
    ``var`` / ``let`` declarations using a conservative textual scan: a symbol
    counts as used whenever its name appears outside its own declaration line,
    so references through module members, `with` scopes or string contents all
    count. Private names (``_``-prefixed) are exempt, matching the language's
    discard convention.

    Args:
        source: Text content of a cleanly-parsed document.

    Returns:
        List of Warning diagnostics.
    """
    import re

    diags: List[Diagnostic] = []
    lines = source.splitlines()

    def _warn(msg: str, line_no: int, start_c: int, end_c: int) -> Diagnostic:
        return Diagnostic(
            range=Range(
                start=Position(line=line_no, character=start_c),
                end=Position(line=line_no, character=max(end_c, start_c + 1)),
            ),
            message=msg,
            severity=DiagnosticSeverity.Warning,
            source="pengus",
        )

    # Unused imports: an import is used when its alias (or the last spec
    # segment) appears somewhere outside the import block.
    import_lines: List[tuple] = []
    for i, line in enumerate(lines):
        m = re.match(
            r"^\s*import\s+([A-Za-z_][A-Za-z0-9_.]*)"
            r"(?:\s+as\s+([A-Za-z_][A-Za-z0-9_]*))?\s*$",
            line,
        )
        if m:
            import_lines.append((i, line, m.group(1), m.group(2)))
    import_idx = {i for i, _, _, _ in import_lines}
    for i, _, spec, alias in import_lines:
        token = alias or spec.split(".")[-1]
        used = False
        for j, line in enumerate(lines):
            if j == i or j in import_idx:
                continue
            if re.search(rf"\b{re.escape(token)}\b", line):
                used = True
                break
        if not used:
            diags.append(_warn(f"Unused import '{spec}'", i, 0, len(lines[i]) if i < len(lines) else 0))

    # Unused local variables.
    for i, line in enumerate(lines):
        m = re.match(r"^\s*(?:var|let)\s+([A-Za-z_][A-Za-z0-9_]*)\s", line)
        if not m:
            continue
        name = m.group(1)
        if name.startswith("_"):
            continue
        total = len(re.findall(rf"\b{re.escape(name)}\b", source))
        if total == 1:  # only its own declaration appears
            col = line.find(name)
            diags.append(_warn(f"Unused variable '{name}'", i, col, col + len(name)))
    return diags


def _compute_diagnostics(uri: str, source: str) -> List[Diagnostic]:
    """Runs parse + semantic check for one document (pure computation).

    Refreshes the cached document buffer and symbol table for ``uri`` and
    returns the diagnostics to publish. This function is called from worker
    threads by the debounced path, so shared maps are mutated under
    ``server._validation_lock``.

    Args:
        uri: Document URI.
        source: Text content of the document.

    Returns:
        List of LSP Diagnostic items (empty when the document is clean).
    """
    server._docs[uri] = source
    file_path = uri_to_path(uri)
    check_path = file_path
    shadow = None
    if not os.path.exists(file_path):
        # The document is an unsaved editor buffer. The semantic checker loads
        # imported modules relative to the entry file, so materialize the
        # buffer to a temporary shadow file (same directory when possible) to
        # keep imports and 'enchanting' methods of std modules visible.
        import tempfile
        base_dir_for_shadow = os.path.dirname(file_path) or os.getcwd()
        try:
            fd, shadow = tempfile.mkstemp(
                suffix=".pengu",
                prefix=".pengu_lsp_shadow_",
                dir=base_dir_for_shadow if os.path.isdir(base_dir_for_shadow) else None,
                text=True,
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(source)
            check_path = shadow
        except OSError:
            shadow = None
    base_dir = os.getcwd()
    if os.path.dirname(file_path) and os.path.isdir(os.path.dirname(file_path)):
        base_dir = os.path.dirname(file_path)

    parser = PenguParser()
    # Mirror the builder: resolve imports from the *project root* and honour the
    # manifest's 'lib_dir' (a project may keep bindings outside './lib').
    project_root = _project_root_for_path(file_path) if file_path else base_dir
    checker = PenguChecker(base_dir=project_root,
                           lib_dir=_lib_dir_for_project(project_root))

    try:
        tree = parser.parse(source)
        checker.check(tree, source=source, filename=check_path)
        # If check succeeds without exception: the document is clean; lint it.
        with server._validation_lock:
            server._symbols[uri] = checker.symbols
            _refresh_module_cache(checker.symbols)
        return _style_warning_diagnostics(source)

    except PenguError as e:
        all_errs = e.all_errors if hasattr(e, "all_errors") and e.all_errors else [e]
        diags = diagnostics_from_errors(all_errs, source)
        with server._validation_lock:
            if hasattr(checker, "symbols"):
                server._symbols[uri] = checker.symbols
                # Imports are collected in pass 1, so even an errored document
                # still refreshes the module cache for autocompletion.
                _refresh_module_cache(checker.symbols)
        return diags

    except Exception as e:
        # Fallback for syntax/parser exceptions (Lark UnexpectedToken, ...).
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
        return [diag]

    finally:
        if shadow is not None:
            try:
                os.unlink(shadow)
            except OSError:
                pass


def _cached_diagnostics(uri: str, source: str) -> Optional[List[Diagnostic]]:
    """Returns previously computed diagnostics when the content is unchanged."""
    key = server._source_hash(source)
    with server._validation_lock:
        hit = server._validation_cache.get(uri)
    if hit is not None and hit[0] == key:
        return hit[1]
    return None


def validate_document(uri: str, source: str) -> None:
    """Parses and type-checks a document, publishing diagnostics immediately.

    Used by programmatic callers (tests, save/open handlers). When the content
    hash is unchanged since the last validation the cached diagnostics are
    re-published and the expensive parse+check pass is skipped.

    Args:
        uri: Document URI.
        source: Text content of the document.
    """
    server._docs[uri] = source
    cached = _cached_diagnostics(uri, source)
    if cached is not None:
        server.publish_diagnostics(uri, cached)
        return
    diags = _compute_diagnostics(uri, source)
    with server._validation_lock:
        server._validation_cache[uri] = (server._source_hash(source), diags)
    server.publish_diagnostics(uri, diags)


async def _schedule_validation(uri: str, source: str, delay: float = 0.0) -> None:
    """Validates one document, optionally debounced.

    Any previously scheduled validation for ``uri`` is cancelled first, so a
    burst of didChange notifications collapses into a single run after the
    latest edit.

    * ``delay == 0`` (didOpen / didSave / flush): validates inline so the
      handler only returns once diagnostics are published — subsequent client
      requests always see fresh symbols.
    * ``delay > 0`` (didChange): the expensive parse+check pass runs in a
      worker thread so the asyncio event loop stays responsive for hover /
      completion requests; diagnostics are published on the loop thread.

    Args:
        uri: Document URI.
        source: Current text content.
        delay: Seconds to wait for typing to settle.
    """
    server.cancel_pending_validation(uri)

    if delay <= 0:
        cached = _cached_diagnostics(uri, source)
        if cached is not None:
            server.publish_diagnostics(uri, cached)
            return
        diags = _compute_diagnostics(uri, source)
        with server._validation_lock:
            server._validation_cache[uri] = (server._source_hash(source), diags)
        server.publish_diagnostics(uri, diags)
        return

    async def _job() -> None:
        if delay > 0:
            await asyncio.sleep(delay)
        cached = _cached_diagnostics(uri, source)
        if cached is not None:
            server.publish_diagnostics(uri, cached)
            return
        loop = asyncio.get_running_loop()
        diags = await loop.run_in_executor(None, _compute_diagnostics, uri, source)
        with server._validation_lock:
            server._validation_cache[uri] = (server._source_hash(source), diags)
        server.publish_diagnostics(uri, diags)

    task = asyncio.ensure_future(_job())
    server._validate_tasks[uri] = task

    def _finished(t: "asyncio.Task[None]") -> None:
        if server._validate_tasks.get(uri) is t:
            server._validate_tasks.pop(uri, None)

    task.add_done_callback(_finished)



@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def _wire_did_open(params: DidOpenTextDocumentParams):
    """textDocument/didOpen: validate the freshly opened document right away."""
    uri = params.text_document.uri
    source = server.get_document_source(uri) or params.text_document.text
    if source:
        server._docs[uri] = source
        await _schedule_validation(uri, source, 0.0)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
async def _wire_did_change(params: DidChangeTextDocumentParams):
    """textDocument/didChange: debounce validation until typing settles."""
    uri = params.text_document.uri
    source = server.get_document_source(uri)

    # Full-sync mode: a change without a range carries the whole document text.
    if params.content_changes:
        first_change = params.content_changes[0]
        if not getattr(first_change, "range", None):
            source = first_change.text

    if source:
        server._docs[uri] = source
        await _schedule_validation(uri, source, VALIDATION_DEBOUNCE_S)


@server.feature(TEXT_DOCUMENT_DID_SAVE)
async def _wire_did_save(params: DidSaveTextDocumentParams):
    """textDocument/didSave: cancel pending debounce and validate immediately."""
    uri = params.text_document.uri
    source = server.get_document_source(uri)
    if getattr(params, "text", None) is not None:
        source = params.text
    if source:
        server._docs[uri] = source
        await _schedule_validation(uri, source, 0.0)


def did_open(params: DidOpenTextDocumentParams):
    """Programmatic didOpen: immediate validation (used by tests/embedders)."""
    uri = params.text_document.uri
    source = server.get_document_source(uri) or params.text_document.text
    if source:
        server._docs[uri] = source
        validate_document(uri, source)


def did_change(params: DidChangeTextDocumentParams):
    """Programmatic didChange: immediate validation (used by tests/embedders)."""
    uri = params.text_document.uri
    source = server.get_document_source(uri)
    if params.content_changes:
        first_change = params.content_changes[0]
        if not getattr(first_change, "range", None):
            source = first_change.text
    if source:
        server._docs[uri] = source
        validate_document(uri, source)


def did_save(params: DidSaveTextDocumentParams):
    """Programmatic didSave: immediate validation (used by tests/embedders)."""
    uri = params.text_document.uri
    source = server.get_document_source(uri)
    if getattr(params, "text", None) is not None:
        source = params.text
    if source:
        server._docs[uri] = source
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
    base_dir = os.path.dirname(uri_to_path(uri)) or os.getcwd()
    return get_completions(uri, params.position, symbols, line_prefix, _MODULE_CACHE, base_dir, doc_text)


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


def _project_root_for_path(file_path: str) -> str:
    """Walks up from a document until it finds a project marker (src/ or
    pengu.yaml); falls back to the document's own directory. The walk is
    bounded so a loose file never escalates to a filesystem root."""
    cur = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
    start = os.path.abspath(cur)
    cur = start
    for _ in range(8):
        if os.path.isfile(os.path.join(cur, "pengu.yaml")) or os.path.isdir(os.path.join(cur, "src")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return start


def _lib_dir_for_project(project_root: str) -> str:
    """Reads ``lib_dir`` from the project's manifest (default ``'lib'``).

    The LSP used to look for bindings exclusively in ``./lib``, so a project
    with ``lib_dir: "external"`` reported every import from that directory as
    unresolved (roadmap 0.20).  Falls back to ``'lib'`` when there is no
    manifest or it cannot be read.
    """
    try:
        from pengu_project import ProjectConfig
        cfg = ProjectConfig.load(project_root)
        return getattr(cfg, "lib_dir", "lib") or "lib"
    except Exception:
        return "lib"


@server.feature(TEXT_DOCUMENT_IMPLEMENTATION)
def implementation(params: ImplementationParams):
    """Handles textDocument/implementation requests.

    For a function / method / type name, returns every matching declaration
    across the standard library and the current project (enchanting and bind
    method definitions are indexed like any other ``weave``).
    """
    uri = params.text_document.uri
    doc_text = server.get_document_source(uri)
    if not doc_text:
        return None
    word = get_word_at_position(doc_text, params.position)
    if not word:
        return None
    root = _project_root_for_path(uri_to_path(uri))
    index = declaration_locations(extra_roots=[root])
    hits = index.get(word) or []
    if not hits:
        return None
    out: List[Location] = []
    seen = set()
    for fpath, line, col in hits:
        key = (os.path.abspath(fpath), line)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            Location(
                uri=path_to_uri(fpath),
                range=Range(
                    start=Position(line=line, character=col),
                    end=Position(line=line, character=col + len(word)),
                ),
            )
        )
    out.sort(key=lambda loc: (loc.uri, loc.range.start.line))
    return out


def _is_declaration_occurrence(line: str, col: int, word: str) -> bool:
    """True when ``word`` at column ``col`` starts a top-level declaration."""
    import re
    m = re.match(
        r"^\s*(?:weave|declare|const|rune|echo|omen|alias|seal|concept)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\b",
        line,
    )
    return bool(m and m.start(1) == col and m.group(1) == word)


# ---------------------------------------------------------------------------
# Semantic occurrence machinery (roadmap 3.1)
#
# rename/highlight/references used to run a plain ``\bword\b`` regex over the
# raw text, so they rewrote homonyms in other scopes, field names after a dot,
# comments and string literals.  These helpers tokenize with the real lexer:
# only NAME tokens match (comments and string *literals* are invisible) and
# string *interpolations* are handled explicitly because ``"{x}"`` is a real
# reference that must follow a rename.
# ---------------------------------------------------------------------------

_LSP_LEXER = None


def _lsp_lexer():
    """Shared parser/lexer instance for token-level occurrence scanning."""
    global _LSP_LEXER
    if _LSP_LEXER is None:
        _LSP_LEXER = PenguParser()
    return _LSP_LEXER


def _interpolation_positions(raw: str, name: str, line: int, col: int) -> List[Tuple[int, int]]:
    """0-based positions of ``name`` inside the ``{...}`` parts of a string token."""
    import re
    try:
        from pengu_parser.pengu_parser import extract_string_parts
        _is_raw, _is_triple, parts = extract_string_parts(raw)
    except Exception:
        return []
    out: List[Tuple[int, int]] = []
    search = 0
    for part in parts:
        if not getattr(part, "is_expr", False):
            continue
        idx = raw.find(part.text, search)
        if idx < 0:
            continue
        search = idx + len(part.text)
        prefix = raw[:idx]
        if "\n" in prefix:
            base_line = line + prefix.count("\n")
            base_col = len(prefix.rsplit("\n", 1)[1]) + 1
        else:
            base_line, base_col = line, col + idx
        for m in re.finditer(rf"\b{re.escape(name)}\b", part.text):
            before = part.text[:m.start()].rstrip()
            if before.endswith(".") or before.endswith("->"):
                continue
            inner = part.text[:m.start()]
            if "\n" in inner:
                mm_line = base_line + inner.count("\n")
                mm_col = len(inner.rsplit("\n", 1)[1]) + 1
            else:
                mm_line, mm_col = base_line, base_col + m.start()
            out.append((mm_line - 1, mm_col - 1))
    return out


def _identifier_occurrences(
    doc_text: str, name: str, symbols: Optional[SymbolTable] = None, sym=None,
) -> List[Tuple[int, int]]:
    """0-based ``(line, col)`` of every identifier occurrence of ``name``.

    When ``symbols``/``sym`` are given, an occurrence only counts when looking
    it up at its own line resolves back to the *same* symbol object.  That is
    exact for lexical scoping: a homonym in a sibling/child scope (shadowing) is
    rejected without needing a hand-tuned line range.  Comments and string
    literals never match; string interpolations do.
    """
    if not doc_text or not name:
        return []

    def _belongs(line1: int) -> bool:
        if symbols is None or sym is None:
            return True
        try:
            return symbols.lookup_at(name, line1) is sym
        except Exception:
            return False

    try:
        parser = _lsp_lexer()
        tokens = parser.get_tokens(parser._strip_comments(doc_text))
    except Exception:
        return []
    out: List[Tuple[int, int]] = []
    for i, tok in enumerate(tokens):
        ttype = getattr(tok, "type", "")
        val = str(getattr(tok, "value", ""))
        line = getattr(tok, "line", None)
        col = getattr(tok, "column", None)
        if line is None or col is None:
            continue
        if ttype == "NAME" and val == name:
            prev = tokens[i - 1] if i > 0 else None
            if prev is not None and str(getattr(prev, "value", "")) in (".", "->"):
                continue  # member access `obj.name` / `obj->name`
            if _belongs(line):
                out.append((line - 1, col - 1))
        elif ttype in ("STRING", "RAW_STRING", "TRIPLE_STRING", "RAW_TRIPLE_STRING"):
            for ln, cl in _interpolation_positions(val, name, line, col):
                if _belongs(ln + 1):
                    out.append((ln, cl))
    return out


def _resolve_symbol_at(symbols: Optional[SymbolTable], position, name: str):
    """Symbol the identifier at ``position`` resolves to, or None."""
    if symbols is None or not name:
        return None
    try:
        if hasattr(symbols, "lookup_at"):
            return symbols.lookup_at(name, position.line + 1)
        return symbols.lookup(name)
    except Exception:
        return None


_SKIP_SCAN_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "build",
    "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "target",
}


def _iter_project_sources(root: str, limit: int = 500):
    """Yields project ``.pengu`` sources, skipping generated ``.d.pengu``.

    The walk prunes VCS/vendor/build directories and stops after ``limit``
    files, so a loose document can never turn a references/rename request into a
    multi-second filesystem sweep.
    """
    count = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _SKIP_SCAN_DIRS and not d.startswith(".")]
        for fname in sorted(files):
            if fname.endswith(".pengu") and not fname.endswith(".d.pengu"):
                count += 1
                if count > limit:
                    return
                yield os.path.join(dirpath, fname)


def _project_scan_root(file_path: str) -> Optional[str]:
    """Directory to scan for cross-file references, or None.

    ``_project_root_for_path`` falls back to the document's own directory, which
    for a loose file can be ``/`` or the user's home directory; walking those
    would be a filesystem sweep.  Everything else is scanned with the pruning /
    file cap of :func:`_iter_project_sources`.
    """
    root = _project_root_for_path(file_path)
    if not root:
        return None
    root_abs = os.path.abspath(root)
    if root_abs == os.path.abspath(os.sep):
        return None
    try:
        if root_abs == os.path.abspath(os.path.expanduser("~")):
            return None
    except Exception:
        pass
    return root_abs


@server.feature(TEXT_DOCUMENT_REFERENCES)
def references(params: ReferenceParams):
    """Handles textDocument/references requests.

    Local symbols (var/let/param) resolve within the current document only;
    global symbols (functions, types, constants, imported aliases) resolve
    across the standard library and the current project. ``.d.pengu`` bodies
    are excluded from the scan.
    """
    uri = params.text_document.uri
    doc_text = server.get_document_source(uri)
    if not doc_text:
        return None
    word = get_word_at_position(doc_text, params.position)
    if not word:
        return None
    include_decl = bool(params.context.include_declaration) if params.context else True

    symbols = server._symbols.get(uri)
    sym = _resolve_symbol_at(symbols, params.position, word)
    is_local = sym is not None and getattr(sym, "kind", "") in ("var", "let", "param")

    root = _project_scan_root(uri_to_path(uri))
    current_abs = os.path.abspath(uri_to_path(uri))

    # Semantic occurrences in the active document (comments / string literals are
    # skipped; interpolations are kept).
    hits: List[Tuple[str, int, int]] = [
        (current_abs, ln, col) for ln, col in _identifier_occurrences(doc_text, word, symbols, sym)
    ]
    if not is_local and root:
        # Global symbol: scan the other project sources token-wise too, so a
        # homonym inside a string literal or a comment is never reported.
        for fpath in _iter_project_sources(root):
            f_abs = os.path.abspath(fpath)
            if f_abs == current_abs:
                continue
            try:
                with open(f_abs, "r", encoding="utf-8") as fh:
                    other = fh.read()
            except OSError:
                continue
            hits.extend((f_abs, ln, col) for ln, col in _identifier_occurrences(other, word))

    out: List[Location] = []
    seen = set()
    for fpath, line, col in hits:
        f_abs = os.path.abspath(fpath)
        key = (f_abs, line, col)
        if key in seen:
            continue
        seen.add(key)
        if not include_decl and f_abs == current_abs:
            src_line = doc_text.splitlines()[line] if line < len(doc_text.splitlines()) else ""
            if _is_declaration_occurrence(src_line, col, word):
                continue
        out.append(
            Location(
                uri=path_to_uri(fpath),
                range=Range(
                    start=Position(line=line, character=col),
                    end=Position(line=line, character=col + len(word)),
                ),
            )
        )
    out.sort(key=lambda loc: (loc.uri, loc.range.start.line, loc.range.start.character))
    return out if out else None


@server.feature(TEXT_DOCUMENT_CODE_ACTION)
def code_action(params: CodeActionParams):
    """Handles textDocument/codeAction requests.

    Currently offers an "Add missing import" quick fix when the cursor sits on
    an undefined identifier that some stdlib/project module exports.
    """
    uri = params.text_document.uri
    source = server.get_document_source(uri)
    if not source:
        return []
    symbols = server._symbols.get(uri)
    start = params.range.start if params.range is not None else params.position
    word = get_word_at_position(source, start)
    if not word:
        return []

    file_path = uri_to_path(uri)
    base_dir = os.path.dirname(file_path) if os.path.exists(file_path) else os.getcwd()
    actions = []
    imp_action = add_missing_import_action(uri, word, source, symbols, base_dir=base_dir)
    if imp_action:
        actions.append(imp_action)
    unused_action = remove_unused_variable_action(uri, word, source, symbols)
    if unused_action:
        actions.append(unused_action)
    concept_action = implement_concept_methods_action(uri, source, start, symbols)
    if concept_action:
        actions.append(concept_action)
    return actions


@server.feature(TEXT_DOCUMENT_SIGNATURE_HELP,
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
    """Handles textDocument/documentHighlight requests.

    Highlights every real reference of the symbol under the cursor: local
    variables/parameters are restricted to their lexical scope, and occurrences
    inside comments, string literals or member access (``obj.name``) are never
    highlighted.
    """
    import re
    uri = params.text_document.uri
    doc_text = server.get_document_source(uri)
    if not doc_text:
        return None

    word = get_word_at_position(doc_text, params.position)
    if not word:
        return None

    clean_word = word.replace("self->", "").replace(".", "").strip()
    if not clean_word:
        return None

    symbols = server._symbols.get(uri)
    sym = _resolve_symbol_at(symbols, params.position, clean_word)
    is_local = sym is not None and getattr(sym, "kind", "") in ("var", "let", "param")
    positions = _identifier_occurrences(doc_text, clean_word, symbols, sym)
    if not positions:
        return None

    lines = doc_text.splitlines()
    highlights: List[DocumentHighlight] = []
    for line_idx, start_col in positions:
        end_col = start_col + len(clean_word)
        src = lines[line_idx] if 0 <= line_idx < len(lines) else ""
        before = src[:start_col]
        kind = DocumentHighlightKind.Read
        if re.search(r"\b(var|let|const|set)\s+$", before):
            kind = DocumentHighlightKind.Write
        highlights.append(
            DocumentHighlight(
                range=Range(
                    start=Position(line=line_idx, character=start_col),
                    end=Position(line=line_idx, character=end_col),
                ),
                kind=kind,
            )
        )
    return highlights


@server.feature(TEXT_DOCUMENT_RENAME)
def rename_symbol(params: RenameParams) -> Optional[WorkspaceEdit]:
    """Handles textDocument/rename requests.

    Local symbols are renamed only inside their lexical scope; global symbols
    are renamed across the project when their declaration is unambiguous (a
    single top-level declaration), and only in the active document otherwise.
    Comments, string literals and member accesses are never rewritten; string
    interpolations (``"{x}"``) are, because they are real references.
    """
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
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", new_name):
        return None

    def _edits(positions) -> List[TextEdit]:
        return [
            TextEdit(
                range=Range(
                    start=Position(line=ln, character=col),
                    end=Position(line=ln, character=col + len(clean_old)),
                ),
                new_text=new_name,
            )
            for ln, col in positions
        ]

    symbols = server._symbols.get(uri)
    sym = _resolve_symbol_at(symbols, params.position, clean_old)
    is_local = sym is not None and getattr(sym, "kind", "") in ("var", "let", "param")

    changes: Dict[str, List[TextEdit]] = {}
    if is_local:
        edits = _edits(_identifier_occurrences(doc_text, clean_old, symbols, sym))
        if edits:
            changes[uri] = edits
        return WorkspaceEdit(changes=changes) if changes else None

    root = _project_scan_root(uri_to_path(uri))
    current_abs = os.path.abspath(uri_to_path(uri))
    try:
        name_decls = declaration_locations(extra_roots=[root] if root else []).get(clean_old) or []
    except Exception:
        name_decls = []

    if root and len(name_decls) <= 1:
        # Unambiguous global: rename every real occurrence across the project.
        for fpath in _iter_project_sources(root):
            f_abs = os.path.abspath(fpath)
            try:
                with open(f_abs, "r", encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                continue
            edits = _edits(_identifier_occurrences(text, clean_old))
            if edits:
                changes[path_to_uri(f_abs)] = edits
    else:
        edits = _edits(_identifier_occurrences(doc_text, clean_old, symbols, sym))
        if edits:
            changes[uri] = edits
    return WorkspaceEdit(changes=changes) if changes else None


@server.feature(TEXT_DOCUMENT_FORMATTING)
def document_formatting(params: DocumentFormattingParams) -> Optional[List[TextEdit]]:
    """Handles textDocument/formatting requests.

    Indentation honors the client FormattingOptions when provided; otherwise a
    ``pengu.yaml`` project config (``tab_size`` / ``indent`` /
    ``insert_spaces`` / ``use_tabs``) is used, falling back to 2 spaces.
    """
    from .formatting import format_pengu_source, load_format_config
    uri = params.text_document.uri
    doc_text = server.get_document_source(uri)
    if not doc_text:
        return None

    cfg = load_format_config(uri_to_path(uri))
    tab_size = 2
    insert_spaces = True
    options = getattr(params, "options", None)
    client_tab = getattr(options, "tab_size", None) if options is not None else None
    if client_tab:
        tab_size = int(client_tab)
    elif cfg is not None and cfg.get("tab_size") is not None:
        tab_size = int(cfg["tab_size"])

    client_insert = getattr(options, "insert_spaces", None) if options is not None else None
    if client_insert is not None:
        insert_spaces = bool(client_insert)
    elif cfg is not None and cfg.get("insert_spaces") is not None:
        insert_spaces = bool(cfg["insert_spaces"])

    blank_max = cfg.get("blank_lines_max") if cfg is not None else None
    new_full_text = format_pengu_source(
        doc_text, tab_size=tab_size, insert_spaces=insert_spaces,
        blank_lines_max=blank_max if isinstance(blank_max, int) else None,
    )
    lines = doc_text.splitlines()
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



# ---------------------------------------------------------------------------
# Semantic tokens, inlay hints and code lenses (roadmap 3.2 / 3.9)
# ---------------------------------------------------------------------------

_SEMANTIC_TOKEN_TYPES = [
    "namespace", "type", "class", "enum", "interface", "struct", "typeParameter",
    "parameter", "variable", "property", "enumMember", "event", "function",
    "method", "macro", "keyword", "modifier", "comment", "string", "number",
    "regexp", "operator", "decorator",
]
_SEMANTIC_TOKEN_MODIFIERS = [
    "declaration", "definition", "readonly", "static", "deprecated",
    "abstract", "async", "modification", "documentation", "defaultLibrary",
]
_TOKEN_TYPE_INDEX = {name: i for i, name in enumerate(_SEMANTIC_TOKEN_TYPES)}
_TOKEN_MOD_INDEX = {name: i for i, name in enumerate(_SEMANTIC_TOKEN_MODIFIERS)}

# Lexer terminal -> semantic token type.
_KEYWORD_TERMINALS = {
    "WEAVE", "DECLARE", "VAR", "LET", "CONST", "IF", "UNLESS", "ELSE", "WHILE",
    "FOR", "IN", "FROM", "TO", "RETURN", "JUDGE", "WHEN", "BREAK", "CONTINUE",
    "IMPORT", "INCLUDE", "LINK", "RUNE", "ECHO", "OMEN", "ALIAS", "SEAL",
    "CONCEPT", "BIND", "ENCHANTING", "RITUAL", "BORROWED", "SET", "BANISH",
    "DEFER", "WITH", "AS", "IS", "INTO", "TRY", "TEST", "SHARD", "WHERE",
    "DERIVE", "TRUE", "FALSE", "NULL", "AND", "OR", "NOT", "INSIGNIA",
}

# Symbol.kind -> semantic token type.
_SYMBOL_KIND_TOKEN = {
    "weave": "function", "declare": "function", "function": "function",
    "rune": "struct", "echo": "struct", "omen": "enum", "alias": "type",
    "seal": "type", "concept": "interface", "import": "namespace",
    "var": "variable", "let": "variable", "const": "variable",
    "param": "parameter", "c_define": "macro",
}

_STRING_TERMINALS = {"STRING", "RAW_STRING", "TRIPLE_STRING", "RAW_TRIPLE_STRING", "CHAR_LIT"}


def _semantic_token_entry(tok, symbols) -> Optional[Tuple[int, int, int, int, int]]:
    """0-based ``(line, col, length, type_index, modifiers_bitset)`` or None."""
    ttype = getattr(tok, "type", "")
    val = str(getattr(tok, "value", ""))
    line = getattr(tok, "line", None)
    col = getattr(tok, "column", None)
    if line is None or col is None:
        return None
    t_idx = None
    mods = 0
    if ttype in _KEYWORD_TERMINALS:
        t_idx = _TOKEN_TYPE_INDEX["keyword"]
    elif ttype in _STRING_TERMINALS:
        t_idx = _TOKEN_TYPE_INDEX["string"]
    elif ttype in ("INT", "FLOAT"):
        t_idx = _TOKEN_TYPE_INDEX["number"]
    elif ttype == "AT":
        t_idx = _TOKEN_TYPE_INDEX["decorator"]
    elif ttype == "NAME":
        t_idx = _TOKEN_TYPE_INDEX["variable"]
        sym = None
        if symbols is not None:
            try:
                sym = symbols.lookup_at(val, line)
            except Exception:
                sym = None
        if sym is not None:
            kind = getattr(sym, "kind", "") or ""
            t_idx = _TOKEN_TYPE_INDEX.get(_SYMBOL_KIND_TOKEN.get(kind, "variable"), t_idx)
            if getattr(sym, "line", None) == line:
                mods |= 1 << _TOKEN_MOD_INDEX["declaration"]
            if kind in ("let", "const") or not getattr(sym, "is_mutable", True):
                mods |= 1 << _TOKEN_MOD_INDEX["readonly"]
            attrs = getattr(sym, "attributes", None) or {}
            if "deprecated" in attrs:
                mods |= 1 << _TOKEN_MOD_INDEX["deprecated"]
            fpath = str(getattr(sym, "file_path", "") or "")
            if os.sep + "std" + os.sep in fpath:
                mods |= 1 << _TOKEN_MOD_INDEX["defaultLibrary"]
    if t_idx is None:
        return None
    return (line - 1, col - 1, max(1, len(val)), t_idx, mods)


@server.feature(TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    SemanticTokensLegend(
        token_types=_SEMANTIC_TOKEN_TYPES,
        token_modifiers=_SEMANTIC_TOKEN_MODIFIERS,
    )
)
def semantic_tokens_full(params: SemanticTokensParams) -> Optional[SemanticTokens]:
    """Handles textDocument/semanticTokens/full.

    Tokens come from the real lexer and are classified with the symbol table
    (functions, types, namespaces, readonly/deprecated/defaultLibrary modifiers),
    so the editor gets semantic highlighting on top of the TextMate grammar.
    """
    uri = params.text_document.uri
    doc_text = server.get_document_source(uri)
    if not doc_text:
        return None
    symbols = server._symbols.get(uri)
    parser = _lsp_lexer()
    try:
        tokens = parser.get_tokens(parser._strip_comments(doc_text))
    except Exception:
        return None

    raw: List[Tuple[int, int, int, int, int]] = []
    for tok in tokens:
        entry = _semantic_token_entry(tok, symbols)
        if entry is not None:
            raw.append(entry)

    raw.sort(key=lambda e: (e[0], e[1], e[2]))
    data: List[int] = []
    prev_line = 0
    prev_col = 0
    seen = set()
    for line, col, length, t_idx, mods in raw:
        key = (line, col, length)
        if key in seen:
            continue
        seen.add(key)
        delta_line = line - prev_line
        delta_col = col - prev_col if delta_line == 0 else col
        data.extend([delta_line, delta_col, length, t_idx, mods])
        prev_line, prev_col = line, col
    return SemanticTokens(data=data)


def _split_top_level(text: str) -> List[str]:
    """Splits ``text`` on top-level commas (ignoring nesting and quotes)."""
    parts: List[str] = []
    depth = 0
    quote = None
    start = 0
    for i, ch in enumerate(text):
        if quote:
            if ch == "\\":
                continue
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return parts


@server.feature(TEXT_DOCUMENT_INLAY_HINT)
def inlay_hints(params: InlayHintParams) -> Optional[List[InlayHint]]:
    """Handles textDocument/inlayHint.

    Adds the inferred type after untyped ``var``/``let`` declarations and the
    parameter name before each call argument (``calling f with 1, 2`` →
    ``x: 1, y: 2``).  Explicitly typed bindings or parameters are not annotated.
    """
    import re
    uri = params.text_document.uri
    doc_text = server.get_document_source(uri)
    if not doc_text:
        return None
    symbols = server._symbols.get(uri)
    if symbols is None:
        return None

    hints: List[InlayHint] = []
    lines = doc_text.splitlines()

    untyped_re = re.compile(r"^(\s*)(?:var|let)\s+([A-Za-z_][A-Za-z0-9_]*)\s+is\b")
    for i, line_text in enumerate(lines):
        m = untyped_re.match(line_text)
        if not m:
            continue
        name = m.group(2)
        try:
            sym = symbols.lookup_at(name, i + 1)
        except Exception:
            sym = None
        if sym is None or getattr(sym, "type", None) is None:
            continue
        type_name = getattr(sym.type, "name", None) or str(sym.type)
        hints.append(InlayHint(
            position=Position(line=i, character=m.end(2)),
            label=f": {type_name}",
            kind=InlayHintKind.Type,
            padding_right=True,
        ))

    call_re = re.compile(
        r"\bcalling\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s+with\s+(.*)$"
    )
    for i, line_text in enumerate(lines):
        cm = call_re.search(line_text)
        if not cm:
            continue
        fname = cm.group(1).split(".")[-1]
        try:
            sym = symbols.lookup_at(fname, i + 1)
        except Exception:
            sym = None
        fn_type = getattr(sym, "type", None) if sym is not None else None
        params_list = getattr(fn_type, "params", None)
        if not params_list:
            continue
        args_text = cm.group(2)
        base_col = cm.start(2)
        args = _split_top_level(args_text)
        search = 0
        for idx, arg in enumerate(args):
            if idx >= len(params_list):
                break
            arg_str = arg.strip()
            if not arg_str:
                continue
            pos = args_text.find(arg_str, search)
            if pos < 0:
                continue
            search = pos + len(arg_str)
            p = params_list[idx]
            p_name = p[0] if isinstance(p, (tuple, list)) else getattr(p, "name", "arg")
            hints.append(InlayHint(
                position=Position(line=i, character=base_col + pos),
                label=f"{p_name}:",
                kind=InlayHintKind.Parameter,
                padding_right=True,
            ))
    return hints


@server.feature(TEXT_DOCUMENT_CODE_LENS)
def code_lenses(params: CodeLensParams) -> Optional[List[CodeLens]]:
    """Handles textDocument/codeLens: a "Run test" lens per ``test`` block."""
    import re
    uri = params.text_document.uri
    doc_text = server.get_document_source(uri)
    if not doc_text:
        return None
    lenses: List[CodeLens] = []
    test_re = re.compile(r'^(\s*)test\s+"([^"]+)"')
    for i, line_text in enumerate(doc_text.splitlines()):
        m = test_re.match(line_text)
        if not m:
            continue
        name = m.group(2)
        lenses.append(CodeLens(
            range=Range(
                start=Position(line=i, character=len(m.group(1))),
                end=Position(line=i, character=len(line_text)),
            ),
            command=Command(
                title=f"▶ Run test: {name}",
                command="pengu.runTest",
                arguments=[uri, name],
            ),
        ))
    return lenses


def _leading_ws(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" \t"))]


@server.feature(TEXT_DOCUMENT_ON_TYPE_FORMATTING,
    DocumentOnTypeFormattingOptions(first_trigger_character=":", more_trigger_character=["\n"]),
)
def on_type_formatting(params: DocumentOnTypeFormattingParams) -> Optional[List[TextEdit]]:
    """Handles textDocument/onTypeFormatting.

    Typing ``:`` at the end of a block opener indents the following line one
    level deeper; typing a newline right after such an opener fixes the new
    line's indentation.  Only the affected line's leading whitespace is edited,
    so a keystroke never reflows the whole document.
    """
    uri = params.text_document.uri
    doc_text = server.get_document_source(uri)
    if not doc_text:
        return None
    ch = params.ch
    lines = doc_text.splitlines()
    line_no = params.position.line
    if not (0 <= line_no < len(lines)):
        return None
    cfg = load_format_config(uri_to_path(uri))
    tab_size = 2
    insert_spaces = True
    if cfg is not None:
        if cfg.get("tab_size") is not None:
            tab_size = int(cfg["tab_size"])
        if cfg.get("insert_spaces") is not None:
            insert_spaces = bool(cfg["insert_spaces"])
    unit = " " * tab_size if insert_spaces else "\t"

    edits: List[TextEdit] = []

    def _reindent(idx: int, target_ws: str) -> None:
        if not (0 <= idx < len(lines)):
            return
        current_ws = _leading_ws(lines[idx])
        if current_ws == target_ws:
            return
        edits.append(TextEdit(
            range=Range(
                start=Position(line=idx, character=0),
                end=Position(line=idx, character=len(current_ws)),
            ),
            new_text=target_ws,
        ))

    if ch == ":":
        # The opener line just got its ':' — indent the next non-empty line.
        base_ws = _leading_ws(lines[line_no])
        nxt = line_no + 1
        while nxt < len(lines) and not lines[nxt].strip():
            nxt += 1
        if nxt < len(lines):
            _reindent(nxt, base_ws + unit)
    elif ch == "\n":
        # The cursor sits on a fresh line; align it with the previous statement,
        # one level deeper when that statement opened a block.
        prev_idx = line_no - 1
        if prev_idx >= 0:
            prev = lines[prev_idx]
            prev_ws = _leading_ws(prev)
            target = prev_ws + unit if prev.rstrip().endswith(":") else prev_ws
            _reindent(line_no, target)
    return edits or None
