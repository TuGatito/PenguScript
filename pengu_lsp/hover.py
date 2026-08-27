"""PenguScript LSP Hover Information Logic."""

import re
from typing import Optional, Dict
from lsprotocol.types import (
    Hover,
    MarkupContent,
    MarkupKind,
    Position,
)
from pengu_parser.pengu_symbols import SymbolTable, Symbol, Scope
from pengu_parser.pengu_types import (
    Type, RuneType, EchoType, OmenType, FnType, AliasType,
    estimate_size,
)


KEYWORD_DOCS = {
    "weave": "**weave**: Defines a function or method in PenguScript.\n\nExample:\n```pengus\nweave add with a as int and b as int into int:\n  return a + b\n```",
    "rune": "**rune**: Defines a composite struct with typed fields.\n\nExample:\n```pengus\nrune Vec2:\n  x as float\n  y as float\n```",
    "echo": "**echo**: Defines a C-compatible tagged union.\n\nExample:\n```pengus\necho Value:\n  i as int\n  f as float\n```",
    "omen": "**omen**: Defines an algebraic data type (enum with payloads).\n\nExample:\n```pengus\nomen Result:\n  Ok with value as int\n  Err with msg as string\n```",
    "enchanting": "**enchanting**: Attaches methods to a struct or type.\n`self` is always a pointer reference (`ref to T`) and accessed via `->`.",
    "var": "**var**: Declares a mutable local variable.\nOnly allowed inside functions/blocks (V-safety).",
    "let": "**let**: Declares an immutable local binding.\nOnly allowed inside functions/blocks (V-safety).",
    "const": "**const**: Declares a top-level compile-time global constant.\nEvaluated at compile-time and translated to `#define` in C.",
    "with": "**with**: Scopes implicit field access for a struct or target.\n\nExample:\n```pengus\nwith player:\n  set x is 10\n  set y is 20\n```",
    "defer": "**defer**: Defers execution of an expression or call until the current scope exits (LIFO order).",
    "errdefer": "**errdefer**: Defers execution of an expression only when an error is returned.",
    "banish": "**banish**: Explicitly deallocates a heap-allocated pointer reference.",
    "sigil": "**sigil of**: Takes the memory address/pointer of a variable (`&x`).",
    "essence": "**essence of**: Dereferences a pointer (`*ptr`).",
    "judge": "**judge**: Pattern matching control expression (equivalent to switch/match).",
    "when": "**when**: Pattern matching branch in a `judge` expression.",
    "declare": "**declare**: Declares an external C function binding.",
    "import": "**import**: Imports a PenguScript module or stdlib package.",
}


def get_word_at_position(text: str, position: Position) -> Optional[str]:
    """Extracts identifier word at cursor position in text.

    Args:
        text: Entire document text.
        position: Position containing line and character.

    Returns:
        Word string under cursor (e.g. 'println', 'self->field'), or None.
    """
    lines = text.splitlines()
    if position.line < 0 or position.line >= len(lines):
        return None

    line = lines[position.line]
    col = position.character
    if col < 0 or col > len(line):
        return None

    # Handle self-> prefix when cursor is on member
    left = col
    while left > 0 and (line[left - 1].isalnum() or line[left - 1] in "_"):
        left -= 1

    if left >= 6 and line[left - 6:left] == "self->":
        left -= 6
        right = col
        while right < len(line) and (line[right].isalnum() or line[right] in "_"):
            right += 1
        return line[left:right].strip()

    right = col
    while right < len(line) and (line[right].isalnum() or line[right] in "_"):
        right += 1

    # Check if identifier is self followed by -> (when cursor is on 'self')
    if line[left:right] == "self" and right + 2 <= len(line) and line[right:right + 2] == "->":
        right += 2
        while right < len(line) and (line[right].isalnum() or line[right] in "_"):
            right += 1

    word = line[left:right].strip()
    return word if word else None


def format_symbol_hover(sym: Symbol, custom_types: Optional[Dict[str, Type]] = None) -> str:
    """Formats rich markdown hover information for a Symbol.

    Includes type signature, memory size in bytes, C extern annotations, and docstrings.
    """
    kind = sym.kind or "var"
    doc_lines = []

    # 1. Functions and Weaves
    if kind in ("weave", "function", "declare") or isinstance(sym.type, FnType):
        fn_t: FnType = sym.type if isinstance(sym.type, FnType) else FnType()
        params_formatted = []
        for p_name, p_type in fn_t.params:
            p_sz = estimate_size(p_type, custom_types)
            sz_str = f" /* {p_sz}B */" if p_sz > 0 else ""
            if p_name:
                params_formatted.append(f"{p_name} as {p_type}{sz_str}")
            else:
                params_formatted.append(f"{p_type}{sz_str}")

        param_str = f" with {', '.join(params_formatted)}" if params_formatted else ""
        ret_t = fn_t.return_type
        ret_sz = estimate_size(ret_t, custom_types)
        ret_sz_str = f" /* {ret_sz}B */" if ret_sz > 0 else ""
        decl_kind = "declare" if (kind == "declare" or sym.is_defined_in_c) else "weave"

        doc_lines.append("```pengus")
        doc_lines.append(f"{decl_kind} {sym.name}{param_str} into {ret_t}{ret_sz_str}")
        doc_lines.append("```")

        if decl_kind == "declare" or sym.is_defined_in_c:
            doc_lines.append("*(External C runtime function)*")
        if sym.is_inline:
            doc_lines.append("*(inline function)*")

    # 2. Runes (Structs)
    elif kind == "rune" or isinstance(sym.type, RuneType):
        r_type = sym.type if isinstance(sym.type, RuneType) else None
        fields_dict = r_type.fields if r_type else {}
        total_sz = estimate_size(sym.type, custom_types)
        fields_lines = []
        for f_name, f_type in fields_dict.items():
            f_sz = estimate_size(f_type, custom_types)
            fields_lines.append(f"  {f_name} as {f_type}  // {f_sz} bytes")

        fields_str = "\n".join(fields_lines) if fields_lines else "  // (opaque or empty)"
        doc_lines.append("```pengus")
        doc_lines.append(f"rune {sym.name} ({total_sz} bytes):\n{fields_str}")
        doc_lines.append("```")
        doc_lines.append(f"**Composite Struct Type** (Total size: {total_sz} bytes)")

    # 3. Echos (Tagged Unions)
    elif kind == "echo" or isinstance(sym.type, EchoType):
        e_type = sym.type if isinstance(sym.type, EchoType) else None
        fields_dict = e_type.fields if e_type else {}
        total_sz = estimate_size(sym.type, custom_types)
        fields_lines = []
        for f_name, f_type in fields_dict.items():
            f_sz = estimate_size(f_type, custom_types)
            fields_lines.append(f"  {f_name} as {f_type}  // {f_sz} bytes")

        fields_str = "\n".join(fields_lines) if fields_lines else "  // (opaque or empty)"
        doc_lines.append("```pengus")
        doc_lines.append(f"echo {sym.name} ({total_sz} bytes):\n{fields_str}")
        doc_lines.append("```")
        doc_lines.append(f"**Tagged Union Type** (Total size: {total_sz} bytes)")

    # 4. Omens (Algebraic Data Types)
    elif kind == "omen" or isinstance(sym.type, OmenType):
        o_type = sym.type if isinstance(sym.type, OmenType) else None
        variants_dict = o_type.variants if o_type else {}
        total_sz = estimate_size(sym.type, custom_types)
        variant_lines = []
        for v_name, v_fields in variants_dict.items():
            vf_parts = [f"{fn} as {ft} ({estimate_size(ft, custom_types)}B)" for fn, ft in v_fields.items()]
            vf_str = f" with {', '.join(vf_parts)}" if vf_parts else ""
            variant_lines.append(f"  {v_name}{vf_str}")

        variants_str = "\n".join(variant_lines) if variant_lines else "  // (variants)"
        doc_lines.append("```pengus")
        doc_lines.append(f"omen {sym.name} ({total_sz} bytes):\n{variants_str}")
        doc_lines.append("```")
        doc_lines.append(f"**Algebraic Data Type / Enum** (Total size: {total_sz} bytes)")

    # 5. Modules
    elif kind == "import":
        doc_lines.append("```pengus")
        doc_lines.append(f"import {sym.name}")
        doc_lines.append("```")
        doc_lines.append(f"**Imported Module**: `{sym.name}`")
        if sym.module_scope and sym.module_scope.symbols:
            exports = [f"`{s}`" for s in sorted(sym.module_scope.symbols.keys()) if not s.startswith("_")]
            if exports:
                doc_lines.append(f"**Exported symbols**: {', '.join(exports)}")

    # 6. Variables, Bindings, and Constants
    else:
        type_str = str(sym.type) if sym.type else "unknown"
        sz = estimate_size(sym.type, custom_types)
        const_str = f" = {sym.const_val}" if sym.const_val is not None else ""
        mut_str = "mut " if sym.is_mutable else ""

        doc_lines.append("```pengus")
        doc_lines.append(f"{kind} {mut_str}{sym.name} as {type_str} ({sz} bytes){const_str}")
        doc_lines.append("```")

        if sym.is_defined_in_c:
            doc_lines.append("*(C header foreign symbol)*")
        if sym.is_stack_alloc:
            doc_lines.append("*(stack allocated)*")

    # Append custom documentation if available
    if sym.doc:
        doc_lines.append("---")
        doc_lines.append(sym.doc)

    return "\n\n".join(doc_lines)


def get_hover(
    uri: str,
    position: Position,
    symbols: Optional[SymbolTable],
    text: str
) -> Optional[Hover]:
    """Computes hover markdown content for identifier under cursor.

    Args:
        uri: Document URI.
        position: Cursor position.
        symbols: Document SymbolTable from checker.
        text: Document text content.

    Returns:
        Hover object with markdown documentation, or None.
    """
    word = get_word_at_position(text, position)
    if not word:
        return None

    # Handle keyword documentation
    clean_kw = word.replace("->", "").strip()
    if clean_kw in KEYWORD_DOCS:
        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.Markdown,
                value=KEYWORD_DOCS[clean_kw]
            )
        )

    if not symbols:
        return None

    custom_types = getattr(symbols, "runes", {})

    # 1. Check if word is part of a module access (e.g. spark.println)
    lines = text.splitlines() if text else []
    if 0 <= position.line < len(lines):
        line_str = lines[position.line]
        col = position.character
        prefix_to_word = line_str[:col]
        dot_m = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)?$", prefix_to_word)
        if dot_m:
            mod_name = dot_m.group(1)
            mod_sym = symbols.lookup(mod_name)
            if mod_sym and mod_sym.module_scope and word in mod_sym.module_scope.symbols:
                target_sym = mod_sym.module_scope.symbols[word]
                return Hover(
                    contents=MarkupContent(
                        kind=MarkupKind.Markdown,
                        value=format_symbol_hover(target_sym, custom_types)
                    )
                )

    if "." in word:
        parts = word.split(".")
        mod_name = parts[-2]
        member_name = parts[-1]
        mod_sym = symbols.lookup(mod_name)
        if mod_sym and mod_sym.module_scope and member_name in mod_sym.module_scope.symbols:
            return Hover(
                contents=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=format_symbol_hover(mod_sym.module_scope.symbols[member_name], custom_types)
                )
            )

    # 2. Direct symbol lookup
    sym = symbols.lookup(word)
    if sym:
        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.Markdown,
                value=format_symbol_hover(sym, custom_types)
            )
        )

    # 3. Custom types
    if hasattr(symbols, "runes") and word in symbols.runes:
        r_type = symbols.runes[word]
        dummy_sym = Symbol(name=word, type=r_type, kind="rune")
        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.Markdown,
                value=format_symbol_hover(dummy_sym, custom_types)
            )
        )

    if hasattr(symbols, "echos") and word in symbols.echos:
        e_type = symbols.echos[word]
        dummy_sym = Symbol(name=word, type=e_type, kind="echo")
        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.Markdown,
                value=format_symbol_hover(dummy_sym, custom_types)
            )
        )

    if hasattr(symbols, "omens") and word in symbols.omens:
        o_type = symbols.omens[word]
        dummy_sym = Symbol(name=word, type=o_type, kind="omen")
        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.Markdown,
                value=format_symbol_hover(dummy_sym, custom_types)
            )
        )

    return None
