"""PenguScript LSP Autocomplete and Completion Logic."""

import re
from typing import List, Optional
from lsprotocol.types import (
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    InsertTextFormat,
    Position,
)
from pengu_parser.pengu_symbols import SymbolTable, Symbol


BASE_KEYWORDS = [
    # Top-level declarations
    ("weave", "weave ${1:name} with ${2:a as int} into ${3:void}:\n\t${0}", "Declare a function (weave)", CompletionItemKind.Snippet),
    ("rune", "rune ${1:Name}:\n\t${2:field} as ${3:int}", "Declare a struct (rune)", CompletionItemKind.Snippet),
    ("echo", "echo ${1:Name}:\n\t${2:field} as ${3:int}", "Declare a union (echo)", CompletionItemKind.Snippet),
    ("omen", "omen ${1:Result}:\n\tOk with value as ${2:int}\n\tErr with msg as string", "Declare an algebraic data type (omen)", CompletionItemKind.Snippet),
    ("alias", "alias ${1:NewType} as ${2:int}", "Declare a type alias", CompletionItemKind.Snippet),
    ("enchanting", "enchanting ${1:Type}:\n\tweave ${2:method} into ${3:void}:\n\t\t${0}", "Attach methods to a type", CompletionItemKind.Snippet),
    ("declare", "declare ${1:c_func} with ${2:a as int} into ${3:void}", "Declare external C function", CompletionItemKind.Snippet),
    ("import", "import ${1:module}", "Import another PenguScript module", CompletionItemKind.Snippet),
    ("include", 'include "${1:header.h}"', "Include a C header file", CompletionItemKind.Snippet),
    ("link", 'link "${1:library}"', "Link an external library", CompletionItemKind.Snippet),

    # Local statements
    ("var", "var ${1:name} as ${2:int} is ${3:0}", "Declare a mutable local variable", CompletionItemKind.Snippet),
    ("let", "let ${1:name} as ${2:int} is ${3:0}", "Declare an immutable local binding", CompletionItemKind.Snippet),
    ("const", "const ${1:NAME} as ${2:int} is ${3:0}", "Declare a top-level constant", CompletionItemKind.Snippet),
    ("set", "set ${1:target} is ${2:value}", "Reassign a mutable variable or field", CompletionItemKind.Snippet),
    ("with", "with ${1:target}:\n\tset ${2:field} is ${3:value}", "Scope field access for target", CompletionItemKind.Snippet),
    ("if", "if ${1:condition}:\n\t${0}", "Conditional statement", CompletionItemKind.Snippet),
    ("unless", "unless ${1:condition}:\n\t${0}", "Negative conditional statement", CompletionItemKind.Snippet),
    ("while", "while ${1:condition}:\n\t${0}", "While loop", CompletionItemKind.Snippet),
    ("for", "for ${1:item} in ${2:collection}:\n\t${0}", "For-in loop", CompletionItemKind.Snippet),
    ("judge", "judge ${1:expr}:\n\twhen ${2:pattern} -> ${3:result}\n\telse -> ${0}", "Pattern matching expression", CompletionItemKind.Snippet),
    ("defer", "defer ${1:action}", "Defer execution to scope exit", CompletionItemKind.Snippet),
    ("errdefer", "errdefer ${1:action}", "Defer execution on error return", CompletionItemKind.Snippet),
    ("banish", "banish ${1:pointer}", "Explicitly free heap memory", CompletionItemKind.Snippet),
    ("return", "return ${0}", "Return from function", CompletionItemKind.Keyword),
    ("break", "break", "Break out of loop", CompletionItemKind.Keyword),
    ("continue", "continue", "Continue next loop iteration", CompletionItemKind.Keyword),

    # Keywords and Operators
    ("self", "self", "Current instance reference", CompletionItemKind.Keyword),
    ("self->", "self->${1:field}", "Access field through self reference", CompletionItemKind.Snippet),
    ("sigil of", "sigil of ${1:var}", "Take pointer reference (&)", CompletionItemKind.Snippet),
    ("essence of", "essence of ${1:ptr}", "Dereference pointer (*)", CompletionItemKind.Snippet),
    ("calling", "calling ${1:func} with ${2:arg}", "Function invocation", CompletionItemKind.Snippet),
    ("maybe none", "maybe none", "Empty optional value", CompletionItemKind.Keyword),
    ("error", "error", "Error literal", CompletionItemKind.Keyword),
    ("transmute", "transmute ${1:expr} as ${2:type}", "Unsafe bitwise cast", CompletionItemKind.Snippet),
]

BASE_TYPES = [
    ("int", "32-bit signed integer"),
    ("i32", "32-bit signed integer"),
    ("i64", "64-bit signed integer"),
    ("float", "64-bit floating point number"),
    ("f32", "32-bit floating point number"),
    ("f64", "64-bit floating point number"),
    ("bool", "Boolean (true / false)"),
    ("string", "PenguScript heap/stack string"),
    ("void", "Empty / return nothing"),
    ("list of", "Dynamic growable array (list of T)"),
    ("array of", "Fixed size array (array of T with size N)"),
    ("slice of", "Contiguous view into array (slice of T)"),
    ("map of", "Hash map (map of Key to Value)"),
    ("maybe", "Optional value (maybe T)"),
    ("result of", "Result or Error (result of T to E)"),
    ("ref to", "Pointer reference (ref to T)"),
    ("opaque", "Opaque C handle / pointer"),
]


def get_completions(
    uri: str,
    position: Position,
    symbols: Optional[SymbolTable] = None,
    line_prefix: str = ""
) -> CompletionList:
    """Generates completion items including keywords, types, and scope symbols.

    Args:
        uri: Document URI.
        position: Cursor position (line, char).
        symbols: Checked SymbolTable if available.
        line_prefix: Text before cursor on current line.

    Returns:
        CompletionList for VSCode LSP.
    """
    # 0. Check for module dot context completion (e.g. `spark.` or `ledger.`)
    if symbols and line_prefix:
        dot_match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\.$", line_prefix)
        if dot_match:
            target_path = dot_match.group(1)
            mod_name = target_path.split(".")[-1]
            sym = symbols.lookup(mod_name)
            if sym and sym.module_scope:
                mod_items: List[CompletionItem] = []
                for name, m_sym in sym.module_scope.symbols.items():
                    if name.startswith("_"):
                        continue
                    kind = (
                        CompletionItemKind.Class if m_sym.kind == "rune"
                        else CompletionItemKind.Function if m_sym.kind in ("weave", "function", "declare")
                        else CompletionItemKind.Enum if m_sym.kind == "echo"
                        else CompletionItemKind.Interface if m_sym.kind == "omen"
                        else CompletionItemKind.TypeParameter if m_sym.kind == "alias"
                        else CompletionItemKind.Constant if m_sym.kind == "const"
                        else CompletionItemKind.Variable
                    )
                    t_str = f" {m_sym.type}" if getattr(m_sym, "type", None) else ""
                    mod_items.append(
                        CompletionItem(
                            label=name,
                            kind=kind,
                            detail=f"{m_sym.kind}{t_str}",
                            documentation=m_sym.doc or None,
                            insert_text=name,
                        )
                    )
                return CompletionList(is_incomplete=False, items=mod_items)

    items: List[CompletionItem] = []

    # 1. Base Keywords and Snippets
    for kw, template, detail, kind in BASE_KEYWORDS:
        items.append(
            CompletionItem(
                label=kw,
                kind=kind,
                detail=detail,
                insert_text=template,
                insert_text_format=InsertTextFormat.Snippet if "$" in template else InsertTextFormat.PlainText,
            )
        )

    # 2. Base Types
    for t_name, t_doc in BASE_TYPES:
        items.append(
            CompletionItem(
                label=t_name,
                kind=CompletionItemKind.TypeParameter,
                detail=t_doc,
                insert_text=t_name,
            )
        )

    # 3. Dynamic Symbols from SymbolTable
    if symbols:
        table_dict = getattr(symbols, "table", None)
        if table_dict is None and hasattr(symbols, "global_scope"):
            table_dict = symbols.global_scope.symbols

        if table_dict:
            for name, sym in table_dict.items():
                if getattr(sym, "kind", "") in ("rune", "echo", "omen", "weave", "function", "declare", "alias", "var", "let", "const", "import"):
                    kind = (
                        CompletionItemKind.Class if sym.kind == "rune"
                        else CompletionItemKind.Function if sym.kind in ("weave", "function", "declare")
                        else CompletionItemKind.Enum if sym.kind == "echo"
                        else CompletionItemKind.Interface if sym.kind == "omen"
                        else CompletionItemKind.TypeParameter if sym.kind == "alias"
                        else CompletionItemKind.Constant if sym.kind == "const"
                        else CompletionItemKind.Module if sym.kind == "import"
                        else CompletionItemKind.Variable
                    )
                    t_str = f" {sym.type}" if getattr(sym, "type", None) else ""
                    items.append(
                        CompletionItem(
                            label=name,
                            kind=kind,
                            detail=f"{sym.kind}{t_str}",
                            documentation=sym.doc or None,
                            insert_text=name,
                        )
                    )

        # Collect custom runes/types registered in symbols
        for r_name in getattr(symbols, "runes", {}):
            if not any(it.label == r_name for it in items):
                items.append(
                    CompletionItem(
                        label=r_name,
                        kind=CompletionItemKind.Class,
                        detail=f"rune {r_name}",
                        insert_text=r_name,
                    )
                )

        for e_name in getattr(symbols, "echos", {}):
            if not any(it.label == e_name for it in items):
                items.append(
                    CompletionItem(
                        label=e_name,
                        kind=CompletionItemKind.Enum,
                        detail=f"echo {e_name}",
                        insert_text=e_name,
                    )
                )

        for o_name in getattr(symbols, "omens", {}):
            if not any(it.label == o_name for it in items):
                items.append(
                    CompletionItem(
                        label=o_name,
                        kind=CompletionItemKind.Interface,
                        detail=f"omen {o_name}",
                        insert_text=o_name,
                    )
                )

    return CompletionList(is_incomplete=False, items=items)
