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
from pengu_parser.pengu_types import RuneType, EchoType, OmenType, RefType, FnType


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
    cursor_line = position.line + 1

    # 0. Dot / Arrow Completion (Fields of Rune/Echo/Omen or Module members)
    if symbols and line_prefix:
        dot_match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)(?:\.|->)$", line_prefix)
        if dot_match:
            full_path = dot_match.group(1)
            parts = full_path.split(".")

            curr_sym = None
            for i, part in enumerate(parts):
                if i == 0:
                    curr_sym = symbols.lookup_at(part, cursor_line) if hasattr(symbols, "lookup_at") else symbols.lookup(part)
                    if not curr_sym and part == "self":
                        curr_sym = symbols.lookup("self")
                else:
                    if curr_sym and getattr(curr_sym, "module_scope", None):
                        curr_sym = curr_sym.module_scope.symbols.get(part)
                    elif curr_sym:
                        c_type = curr_sym.type
                        while isinstance(c_type, RefType):
                            c_type = c_type.target
                        if isinstance(c_type, (RuneType, EchoType)) and part in c_type.fields:
                            field_type = c_type.fields[part]
                            curr_sym = Symbol(name=part, type=field_type, kind="var")
                        else:
                            curr_sym = None

            sym = curr_sym

            if sym:
                actual_type = sym.type
                while isinstance(actual_type, RefType):
                    actual_type = actual_type.target

                # Module members: suggest exported symbols from imported modules
                if getattr(sym, "module_scope", None) and sym.module_scope.symbols:
                    mod_items: List[CompletionItem] = []
                    for name, m_sym in sym.module_scope.symbols.items():
                        if name.startswith("_"):
                            continue
                        if getattr(m_sym, "kind", "") == "type" and name in ("int", "i32", "i64", "float", "f32", "f64", "bool", "string", "void", "opaque"):
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

                field_items: List[CompletionItem] = []

                # RuneType: suggest fields and attached methods
                if isinstance(actual_type, RuneType):
                    for f_name, f_type in actual_type.fields.items():
                        field_items.append(
                            CompletionItem(
                                label=f_name,
                                kind=CompletionItemKind.Field,
                                detail=str(f_type),
                                insert_text=f_name,
                            )
                        )
                    for m_name, m_type in getattr(actual_type, "methods", {}).items():
                        field_items.append(
                            CompletionItem(
                                label=m_name,
                                kind=CompletionItemKind.Method,
                                detail=f"method {m_type}",
                                insert_text=m_name,
                            )
                        )
                    return CompletionList(is_incomplete=False, items=field_items)

                # EchoType: suggest fields
                elif isinstance(actual_type, EchoType):
                    for f_name, f_type in actual_type.fields.items():
                        field_items.append(
                            CompletionItem(
                                label=f_name,
                                kind=CompletionItemKind.Field,
                                detail=str(f_type),
                                insert_text=f_name,
                            )
                        )
                    return CompletionList(is_incomplete=False, items=field_items)

                # OmenType: suggest variants
                elif isinstance(actual_type, OmenType):
                    for v_name, v_fields in actual_type.variants.items():
                        v_detail = f"variant with {', '.join(f'{fn} as {ft}' for fn, ft in v_fields.items())}" if v_fields else "variant"
                        field_items.append(
                            CompletionItem(
                                label=v_name,
                                kind=CompletionItemKind.EnumMember,
                                detail=v_detail,
                                insert_text=v_name,
                            )
                        )
                    return CompletionList(is_incomplete=False, items=field_items)

            # Check if full_path is a type name directly (e.g. Rune.field or Omen.Variant)
            if hasattr(symbols, "runes") and full_path in symbols.runes:
                r_type = symbols.runes[full_path]
                field_items = [
                    CompletionItem(label=fn, kind=CompletionItemKind.Field, detail=str(ft), insert_text=fn)
                    for fn, ft in r_type.fields.items()
                ]
                return CompletionList(is_incomplete=False, items=field_items)

            if hasattr(symbols, "omens") and full_path in symbols.omens:
                o_type = symbols.omens[full_path]
                variant_items = [
                    CompletionItem(label=vn, kind=CompletionItemKind.EnumMember, detail="variant", insert_text=vn)
                    for vn in o_type.variants.keys()
                ]
                return CompletionList(is_incomplete=False, items=variant_items)

    # 1. Calling Context Completion (e.g. `calling ` or `calling`)
    if symbols and (line_prefix.strip().endswith("calling") or re.search(r"\bcalling\s+$", line_prefix)):
        call_items: List[CompletionItem] = []
        added_labels = set()

        # 1a. Callable local variables in active scopes
        if hasattr(symbols, "all_scopes"):
            for scope in symbols.all_scopes:
                if scope.start_line <= cursor_line <= scope.end_line:
                    for sym in scope.symbols.values():
                        if sym.name and sym.name not in added_labels:
                            if isinstance(getattr(sym, "type", None), FnType):
                                call_items.append(
                                    CompletionItem(
                                        label=sym.name,
                                        kind=CompletionItemKind.Function,
                                        detail=f"function {sym.type}",
                                        insert_text=sym.name,
                                    )
                                )
                                added_labels.add(sym.name)

        # 1b. Global functions, declarations, and imported modules
        table_dict = getattr(symbols, "table", None)
        if table_dict is None and hasattr(symbols, "global_scope"):
            table_dict = symbols.global_scope.symbols

        if table_dict:
            for name, sym in table_dict.items():
                if name not in added_labels:
                    if sym.kind in ("weave", "function", "declare"):
                        t_str = f" {sym.type}" if getattr(sym, "type", None) else ""
                        call_items.append(
                            CompletionItem(
                                label=name,
                                kind=CompletionItemKind.Function,
                                detail=f"{sym.kind}{t_str}",
                                documentation=sym.doc or None,
                                insert_text=name,
                            )
                        )
                        added_labels.add(name)
                    elif sym.kind == "import" or getattr(sym, "module_scope", None):
                        call_items.append(
                            CompletionItem(
                                label=name,
                                kind=CompletionItemKind.Module,
                                detail=f"module {name}",
                                documentation=sym.doc or None,
                                insert_text=name,
                            )
                        )
                        added_labels.add(name)

        return CompletionList(is_incomplete=False, items=call_items)

    items: List[CompletionItem] = []

    # 2. Base Keywords and Snippets
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

    # 3. Base Types
    for t_name, t_doc in BASE_TYPES:
        items.append(
            CompletionItem(
                label=t_name,
                kind=CompletionItemKind.TypeParameter,
                detail=t_doc,
                insert_text=t_name,
            )
        )

    # 4. Dynamic Global Symbols from SymbolTable
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

        # 5. Dynamic Local Variables from Active Scopes around cursor_line
        if hasattr(symbols, "all_scopes"):
            for scope in symbols.all_scopes:
                if scope.start_line <= cursor_line <= scope.end_line:
                    for sym in scope.symbols.values():
                        if getattr(sym, "kind", "") in ("var", "let", "param") and sym.name:
                            if not any(it.label == sym.name for it in items):
                                t_str = f" {sym.type}" if getattr(sym, "type", None) else ""
                                items.append(
                                    CompletionItem(
                                        label=sym.name,
                                        kind=CompletionItemKind.Variable,
                                        detail=f"{sym.kind}{t_str}",
                                        insert_text=sym.name,
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

