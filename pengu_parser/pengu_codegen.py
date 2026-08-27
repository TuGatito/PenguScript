#!/usr/bin/env python3
"""PenguScript v0.6 C Code Generator (pengu_codegen.py).

Translates verified ASTs from all modules in topological order into a single monolithic bundle.c.
Employs a multi-pass architecture:
1. Declarations collection (runes, echos, omens, aliases, consts, weaves, enchantings).
2. Forward declarations of all types and function prototypes (eliminates circular/ordering issues).
3. Complete type definitions (structs, unions, tagged enums).
4. Function definitions in topological module order.
5. Entry point generation (for executable targets).
"""

from __future__ import annotations
import os
import sys
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from lark import Tree, Token

from pengu_parser.pengu_types import (
    Type, BaseType, RefType, ArrayType, SliceType, ListType, MapType, MaybeType,
    RuneType, EchoType, OmenType, ResultType, FnType, AliasType, AnyType,
    TypeParam, INT_TYPE, I32_TYPE, I64_TYPE, FLOAT_TYPE, F32_TYPE, F64_TYPE, BOOL_TYPE,
    STRING_TYPE, VOID_TYPE, ERROR_TYPE, OPAQUE_TYPE, ast_to_type
)
from pengu_parser.pengu_symbols import SymbolTable, Symbol
from pengu_parser.pengu_infer import ConstFolder, TypeInferrer


class CTypeMapper:
    """Maps PenguScript semantic types to C99 type representations."""

    @staticmethod
    def to_c_type(t: Optional[Type], const: bool = False) -> str:
        """Converts PenguScript Type to C99 type string.

        Args:
            t: PenguScript Type instance.
            const: True to add const qualifier.

        Returns:
            C99 type string.
        """
        if t is None:
            return "void"

        prefix = "const " if const else ""

        if isinstance(t, BaseType):
            name = t.name
            if name in ("int", "i32"):
                return f"{prefix}int32_t"
            elif name == "i64":
                return f"{prefix}int64_t"
            elif name in ("float", "f32"):
                return f"{prefix}float"
            elif name == "f64":
                return f"{prefix}double"
            elif name == "bool":
                return f"{prefix}bool"
            elif name == "string":
                return f"{prefix}PenguString"
            elif name == "void":
                return "void"
            elif name == "opaque":
                return f"{prefix}void*"
            elif name == "error":
                return f"{prefix}const char*"
            return f"{prefix}{name}"

        elif isinstance(t, RefType):
            target_str = CTypeMapper.to_c_type(t.target)
            if target_str == "void":
                return "void*"
            return f"{target_str}*"

        elif isinstance(t, RuneType):
            return f"{prefix}{t.name}"

        elif isinstance(t, EchoType):
            return f"{prefix}{t.name}"

        elif isinstance(t, OmenType):
            return f"{prefix}{t.name}"

        elif isinstance(t, AliasType):
            return f"{prefix}{t.name}"

        elif isinstance(t, ArrayType):
            elem_str = CTypeMapper.to_c_type(t.element)
            return f"{elem_str}*"

        elif isinstance(t, SliceType):
            return "PenguSlice"

        elif isinstance(t, ListType):
            return "PenguList"

        elif isinstance(t, MapType):
            return "PenguMap"

        elif isinstance(t, MaybeType):
            return "PenguMaybe"

        elif isinstance(t, ResultType):
            return "PenguResult"

        elif isinstance(t, FnType):
            ret_str = CTypeMapper.to_c_type(t.return_type)
            param_strs = [CTypeMapper.to_c_type(p[1]) for p in t.params] or ["void"]
            return f"{ret_str} (*)({', '.join(param_strs)})"

        return f"{prefix}void*"

    @staticmethod
    def to_c_decl(t: Optional[Type], ident: str = "", const: bool = False, restrict: bool = False) -> str:
        """Declares a variable or parameter with C99 identifier, supporting function pointers and restrict qualifier."""
        if t is None:
            return f"void {ident}".strip()
        if isinstance(t, FnType):
            ret_str = CTypeMapper.to_c_type(t.return_type)
            param_strs = [CTypeMapper.to_c_type(p[1]) for p in t.params] or ["void"]
            return f"{ret_str} (*{ident})({', '.join(param_strs)})" if ident else f"{ret_str} (*)({', '.join(param_strs)})"
        if isinstance(t, RefType) and restrict and ident:
            target_str = CTypeMapper.to_c_type(t.target)
            return f"{target_str}* restrict {ident}"
        base = CTypeMapper.to_c_type(t, const=const)
        return f"{base} {ident}".strip() if ident else base


class PenguCodegen:
    """Translates verified PenguScript module ASTs into high-performance C99 code."""

    def __init__(self, symbols: SymbolTable, import_order: List[str], base_dir: str):
        """Initializes code generator.

        Args:
            symbols: Semantic symbol table with resolved types.
            import_order: List of source files in topological dependency order.
            base_dir: Root directory of project.
        """
        self.symbols = symbols
        self.import_order = import_order
        self.base_dir = base_dir
        self.const_folder = ConstFolder(symbols)

        # Declarations registry
        self.runes: Dict[str, Dict[str, Type]] = {}
        self.echos: Dict[str, Dict[str, Type]] = {}
        self.omens: Dict[str, Dict[str, Dict[str, Type]]] = {}
        self.aliases: Dict[str, Type] = {}
        self.consts: Dict[str, Tuple[Optional[Type], Any]] = {}
        self.c_defines: List[str] = []
        self.weaves: List[Dict[str, Any]] = []
        self.fn_info: Dict[str, Dict[str, Any]] = {}
        self.includes: List[str] = []
        self.links: List[str] = []
        self.has_main = False

        # Translation state
        self.current_function: Optional[str] = None
        self.current_return_type: Optional[Type] = None
        self.current_enchanted_type: Optional[Type] = None
        self.local_vars: Dict[str, Type] = {}
        self.indent_level = 0
        self.defer_stack: List[List[str]] = []
        self.errdefer_stack: List[List[str]] = []
        self.with_stack: List[str] = []
        self.temp_counter = 0

    def _lookup_var_type(self, name: str) -> Optional[Type]:
        """Looks up semantic type for identifier in local or symbol context."""
        if name in self.local_vars and self.local_vars[name] is not None:
            return self.local_vars[name]
        sym = self.symbols.lookup(name) if self.symbols else None
        if sym and sym.type:
            return sym.type
        if name in self.runes:
            return RuneType(name, self.runes[name])
        return None

    def get_temp_name(self, prefix: str = "_tmp") -> str:
        """Generates unique local variable identifier.

        Args:
            prefix: Name prefix.

        Returns:
            Unique identifier string.
        """
        self.temp_counter += 1
        return f"{prefix}_{self.temp_counter}"

    def indent(self) -> str:
        """Returns current indentation spaces string."""
        return "  " * self.indent_level

    def _lookup_type_fn(self, name: str) -> Optional[Type]:
        """Type lookup resolver for AST conversion during codegen."""
        sym = self.symbols.lookup(name) if self.symbols else None
        if sym and sym.type:
            return sym.type
        if name in self.runes:
            return RuneType(name, self.runes[name])
        if name in self.echos:
            return EchoType(name, self.echos[name])
        if name in self.omens:
            return OmenType(name, self.omens[name])
        if name in self.aliases:
            return self.aliases[name]
        return None

    def _format_const_val(self, val: Any) -> str:
        """Formats evaluated constant Python value into C literal."""
        if isinstance(val, bool):
            return "true" if val else "false"
        elif isinstance(val, int):
            return str(val)
        elif isinstance(val, float):
            return f"{val}f" if abs(val) < 1e7 else str(val)
        elif isinstance(val, str):
            return f'pengu_string_from_cstr("{val}")'
        return str(val)

    def collect_declarations(self, trees: List[Tuple[str, Tree]]) -> None:
        """Two-pass declarations collection to resolve forward and circular references.

        Pass 1: Registers all type and function names.
        Pass 2: Populates complete field definitions and signatures.

        Args:
            trees: List of (module_filepath, AST_tree) tuples in topological order.
        """
        top_stmts: List[Tuple[Tree, str]] = []
        for filepath, tree in trees:
            for node in tree.children:
                if not isinstance(node, Tree):
                    continue
                if node.data == "file":
                    for top_node in node.children:
                        if isinstance(top_node, Tree):
                            top_stmts.append((top_node, filepath))
                elif node.data == "top_stmt":
                    top_stmts.append((node, filepath))

        # Pass 1: Register names (skipping generic templates)
        for top_node, filepath in top_stmts:
            stmt = top_node.children[0] if top_node.data == "top_stmt" and top_node.children else top_node
            if not isinstance(stmt, Tree):
                continue
            rule = stmt.data
            has_shards = len(stmt.children) > 1 and isinstance(stmt.children[1], Tree) and stmt.children[1].data == "shard_params"
            if has_shards:
                continue
            if rule == "rune_decl":
                name = str(stmt.children[0])
                self.runes[name] = {}
            elif rule == "echo_decl":
                name = str(stmt.children[0])
                self.echos[name] = {}
            elif rule == "omen_decl":
                name = str(stmt.children[0])
                self.omens[name] = {}
            elif rule == "alias_decl":
                name = str(stmt.children[0])
                self.aliases[name] = VOID_TYPE

        # Pass 2: Populate definitions
        for top_node, filepath in top_stmts:
            self._collect_top_stmt(top_node, filepath)

        # Pass 3: Collect monomorphized types and functions from symbol table
        if self.symbols:
            for m_name, m_type in self.symbols.monomorphized_types.items():
                if m_name in self.symbols._generated_instances:
                    continue
                self.symbols._generated_instances.add(m_name)
                if isinstance(m_type, RuneType) and m_name not in self.runes:
                    self.runes[m_name] = m_type.fields
                elif isinstance(m_type, EchoType) and m_name not in self.echos:
                    self.echos[m_name] = m_type.fields
                elif isinstance(m_type, OmenType) and m_name not in self.omens:
                    self.omens[m_name] = m_type.variants
                elif isinstance(m_type, AliasType) and m_name not in self.aliases:
                    self.aliases[m_name] = m_type.target

            for m_fn_name, (fn_ast, subst_map) in self.symbols.monomorphized_functions.items():
                if m_fn_name in self.symbols._generated_instances:
                    continue
                self.symbols._generated_instances.add(m_fn_name)
                if not any(w["c_name"] == m_fn_name for w in self.weaves):
                    self._collect_monomorphized_weave(m_fn_name, fn_ast, subst_map, None, filepath=".")

            for m_m_name, (m_ast, subst_map) in self.symbols.monomorphized_methods.items():
                if m_m_name in self.symbols._generated_instances:
                    continue
                self.symbols._generated_instances.add(m_m_name)
                parts = m_m_name.rsplit("_", 1)
                rec_tname = parts[0]
                rec_type = self.symbols.lookup_type(rec_tname) or RuneType(name=rec_tname)
                if not any(w["c_name"] == m_m_name for w in self.weaves):
                    self._collect_monomorphized_weave(m_m_name, m_ast, subst_map, rec_type, filepath=".")

    def _collect_top_stmt(self, top_node: Tree, filepath: str) -> None:
        """Dispatches top-level statement collection."""
        stmt = top_node.children[0] if top_node.data == "top_stmt" and top_node.children else top_node
        if not isinstance(stmt, Tree):
            return

        rule = stmt.data
        has_shards = len(stmt.children) > 1 and isinstance(stmt.children[1], Tree) and stmt.children[1].data == "shard_params"

        if rule == "rune_decl":
            if has_shards:
                return
            name = str(stmt.children[0])
            fields = {}
            for f in stmt.children[1:]:
                if isinstance(f, Tree) and f.data == "field_decl":
                    f_name = str(f.children[0])
                    f_type = ast_to_type(f.children[1], self._lookup_type_fn)
                    fields[f_name] = f_type
            self.runes[name] = fields

        elif rule == "echo_decl":
            if has_shards:
                return
            name = str(stmt.children[0])
            fields = {}
            for f in stmt.children[1:]:
                if isinstance(f, Tree) and f.data == "field_decl":
                    f_name = str(f.children[0])
                    f_type = ast_to_type(f.children[1], self._lookup_type_fn)
                    fields[f_name] = f_type
            self.echos[name] = fields

        elif rule == "omen_decl":
            if has_shards:
                return
            name = str(stmt.children[0])
            variants = {}
            for v in stmt.children[1:]:
                if isinstance(v, Tree) and v.data == "omen_variant":
                    v_name = str(v.children[0])
                    v_fields = {}
                    for f in v.children[1:]:
                        if isinstance(f, Tree) and f.data == "omen_field":
                            f_name = str(f.children[0])
                            f_type = ast_to_type(f.children[1], self._lookup_type_fn)
                            v_fields[f_name] = f_type
                    variants[v_name] = v_fields
            self.omens[name] = variants

        elif rule == "alias_decl":
            if has_shards:
                return
            name = str(stmt.children[0])
            rem_children = [c for c in stmt.children[1:] if c is not None]
            target_t = ast_to_type(rem_children[0], self._lookup_type_fn)
            self.aliases[name] = target_t

        elif rule == "const_decl":
            name = str(stmt.children[0])
            c_type = None
            expr_idx = 1
            if len(stmt.children) == 3:
                c_type = ast_to_type(stmt.children[1], self._lookup_type_fn)
                expr_idx = 2
            expr_node = stmt.children[expr_idx]
            val = self.const_folder.fold(expr_node)
            self.consts[name] = (c_type, val)
            if filepath:
                norm_fp = os.path.abspath(filepath)
                norm_order = [os.path.abspath(p) for p in self.import_order]
                if len(norm_order) > 1 and norm_fp != norm_order[-1]:
                    is_std = "std" in norm_fp.replace("/", "\\").split("\\")
                    if is_std:
                        mod_name = os.path.splitext(os.path.basename(norm_fp))[0]
                        if mod_name and not name.startswith(f"{mod_name}_"):
                            self.consts[f"{mod_name}_{name}"] = (c_type, val)

        elif rule == "declare_stmt":
            if any(isinstance(c, Tree) and c.data == "shard_params" for c in stmt.children):
                return
            fn_name = str(stmt.children[0])
            rem_children = [c for c in stmt.children[1:] if c is not None]
            params = []
            ret_type = VOID_TYPE
            for child_n in rem_children:
                if isinstance(child_n, Tree) and child_n.data == "param_list":
                    for p in child_n.children:
                        if isinstance(p, Tree) and p.data == "param":
                            pn = str(p.children[0])
                            pt = ast_to_type(p.children[1], self._lookup_type_fn) if len(p.children) >= 2 else AnyType()
                            pd = p.children[2] if len(p.children) >= 3 else None
                            params.append((pn, pt, pd))
                elif isinstance(child_n, Tree) and child_n.data in ("base_type", "custom_type", "ref_type", "array_type", "slice_type", "list_type", "map_type", "maybe_type", "result_type"):
                    ret_type = ast_to_type(child_n, self._lookup_type_fn)
                elif isinstance(child_n, Token) and child_n.type == "NAME":
                    ret_type = ast_to_type(child_n, self._lookup_type_fn)
            self.fn_info[fn_name] = {"c_name": fn_name, "params": params, "return_type": ret_type}

        elif rule == "include_stmt":
            inc_val = str(stmt.children[0]).strip('"')
            if inc_val not in self.includes:
                self.includes.append(inc_val)

        elif rule == "link_stmt":
            link_val = str(stmt.children[0]).strip('"')
            if link_val not in self.links:
                self.links.append(link_val)

        elif rule == "weave_decl":
            if any(isinstance(c, Tree) and c.data == "shard_params" for c in stmt.children):
                return
            self._collect_weave(stmt, filepath, None)

        elif rule == "enchanting_decl":
            type_node = stmt.children[0]
            enchanted_type = ast_to_type(type_node, self._lookup_type_fn)
            base_tname = enchanted_type.name.split("_")[0]
            if (self.symbols and base_tname in self.symbols.generic_runes) or getattr(enchanted_type, "type_params", None) or any(isinstance(t, TypeParam) for t in getattr(enchanted_type, "type_args", [])):
                return
            for w in stmt.children[1:]:
                if isinstance(w, Tree) and w.data == "weave_decl":
                    self._collect_weave(w, filepath, enchanted_type)

    def _collect_monomorphized_weave(self, specialized_name: str, node: Tree, subst_map: Dict[str, Type], enchanted_type: Optional[Type], filepath: str = ".") -> None:
        """Collects specialized monomorphized function details."""
        is_inline = False
        idx = 0
        if isinstance(node.children[0], Token) and node.children[0].type == "INLINE":
            is_inline = True
            idx += 1

        raw_name = str(node.children[idx])
        idx += 1

        while idx < len(node.children) and node.children[idx] is None:
            idx += 1

        if idx < len(node.children) and isinstance(node.children[idx], Tree) and node.children[idx].data == "shard_params":
            idx += 1

        while idx < len(node.children) and node.children[idx] is None:
            idx += 1

        def lookup_subst_tp(tname: str):
            if tname in subst_map:
                return subst_map[tname]
            return self._lookup_type_fn(tname)

        params = []
        if idx < len(node.children):
            if isinstance(node.children[idx], Tree) and node.children[idx].data == "param_list":
                param_list_node = node.children[idx]
                for p in param_list_node.children:
                    if isinstance(p, Tree) and p.data == "param":
                        p_name = str(p.children[0])
                        p_type = ast_to_type(p.children[1], lookup_subst_tp) if len(p.children) > 1 else AnyType()
                        p_type = p_type.substitute(subst_map)
                        p_default = p.children[2] if len(p.children) >= 3 else None
                        params.append((p_name, p_type, p_default))
                idx += 1

        while idx < len(node.children) and node.children[idx] is None:
            idx += 1

        ret_type = VOID_TYPE
        if idx < len(node.children):
            if isinstance(node.children[idx], Tree) and node.children[idx].data not in ("stmt", "block", "file"):
                ret_type = ast_to_type(node.children[idx], lookup_subst_tp)
                ret_type = ret_type.substitute(subst_map)
                idx += 1
            elif isinstance(node.children[idx], Token) and node.children[idx].type == "NAME":
                ret_type = ast_to_type(node.children[idx], lookup_subst_tp)
                ret_type = ret_type.substitute(subst_map)
                idx += 1

        body_stmts = []
        for s in node.children[idx:]:
            if isinstance(s, Tree):
                body_stmts.append(s)

        c_name = specialized_name

        self.fn_info[specialized_name] = {"c_name": c_name, "params": params, "return_type": ret_type}
        self.fn_info[c_name] = {"c_name": c_name, "params": params, "return_type": ret_type}

        if not any(w["c_name"] == c_name for w in self.weaves):
            self.weaves.append({
                "name": specialized_name,
                "c_name": c_name,
                "enchanted_type": enchanted_type,
                "params": params,
                "return_type": ret_type,
                "is_inline": is_inline,
                "body_stmts": body_stmts,
                "subst_map": subst_map,
                "filepath": filepath,
            })

    def _collect_weave(self, node: Tree, filepath: str, enchanted_type: Optional[Type]) -> None:
        """Collects function declaration details."""
        is_inline = False
        idx = 0
        if isinstance(node.children[0], Token) and node.children[0].type == "INLINE":
            is_inline = True
            idx += 1

        name = str(node.children[idx])
        idx += 1

        while idx < len(node.children) and node.children[idx] is None:
            idx += 1

        if idx < len(node.children) and isinstance(node.children[idx], Tree) and node.children[idx].data == "shard_params":
            idx += 1

        while idx < len(node.children) and node.children[idx] is None:
            idx += 1

        params = []
        if idx < len(node.children):
            if isinstance(node.children[idx], Tree) and node.children[idx].data == "param_list":
                param_list_node = node.children[idx]
                for p in param_list_node.children:
                    if isinstance(p, Tree) and p.data == "param":
                        p_name = str(p.children[0])
                        p_type = ast_to_type(p.children[1], self._lookup_type_fn) if len(p.children) > 1 else AnyType()
                        p_default = p.children[2] if len(p.children) >= 3 else None
                        params.append((p_name, p_type, p_default))
                idx += 1

        while idx < len(node.children) and node.children[idx] is None:
            idx += 1

        ret_type = VOID_TYPE
        if idx < len(node.children):
            if isinstance(node.children[idx], Tree) and node.children[idx].data not in ("stmt", "block", "file"):
                ret_type = ast_to_type(node.children[idx], self._lookup_type_fn)
                idx += 1
            elif isinstance(node.children[idx], Token) and node.children[idx].type == "NAME":
                ret_type = ast_to_type(node.children[idx], self._lookup_type_fn)
                idx += 1

        body_stmts = []
        for s in node.children[idx:]:
            if isinstance(s, Tree):
                body_stmts.append(s)

        c_name = name
        if enchanted_type is not None:
            t_name = getattr(enchanted_type, "name", str(enchanted_type)).replace(" ", "_")
            c_name = f"{t_name}_{name}"
        elif filepath:
            norm_fp = os.path.abspath(filepath)
            norm_order = [os.path.abspath(p) for p in self.import_order]
            if len(norm_order) > 1 and norm_fp != norm_order[-1]:
                is_std = "std" in norm_fp.replace("/", "\\").split("\\")
                if is_std:
                    mod_name = os.path.splitext(os.path.basename(norm_fp))[0]
                    if mod_name and not name.startswith(f"{mod_name}_"):
                        c_name = f"{mod_name}_{name}"

        if name == "main" and enchanted_type is None:
            self.has_main = True

        self.fn_info[name] = {"c_name": c_name, "params": params, "return_type": ret_type}
        self.fn_info[c_name] = {"c_name": c_name, "params": params, "return_type": ret_type}

        self.weaves.append({
            "name": name,
            "c_name": c_name,
            "enchanted_type": enchanted_type,
            "params": params,
            "return_type": ret_type,
            "is_inline": is_inline,
            "body_stmts": body_stmts,
            "filepath": filepath,
        })

    def generate_forward_declarations(self) -> str:
        """Generates consistent forward struct/union/omen declarations and function prototypes."""
        lines = [
            "/* -------------------------------------------------------------------------",
            " * Forward Declarations",
            " * ------------------------------------------------------------------------- */",
        ]

        # Runes
        for name in self.runes:
            lines.append(f"struct {name};")
            lines.append(f"typedef struct {name} {name};")

        # Echos
        for name in self.echos:
            lines.append(f"union {name};")
            lines.append(f"typedef union {name} {name};")

        # Omens
        for name in self.omens:
            lines.append(f"struct {name};")
            lines.append(f"typedef struct {name} {name};")

        lines.append("")
        return "\n".join(lines)

    def generate_type_definitions(self) -> str:
        """Generates full struct, union, enum, and typedef definitions."""
        lines = [
            "/* -------------------------------------------------------------------------",
            " * Type Definitions",
            " * ------------------------------------------------------------------------- */",
        ]

        # 1. Type Aliases
        for name, target in self.aliases.items():
            target_str = CTypeMapper.to_c_type(target)
            lines.append(f"typedef {target_str} {name};")

        if self.aliases:
            lines.append("")

        # 2. Runes (Structs)
        for name, fields in self.runes.items():
            lines.append(f"struct {name} {{")
            for f_name, f_type in fields.items():
                if isinstance(f_type, ArrayType) and f_type.size is not None:
                    elem_str = CTypeMapper.to_c_type(f_type.element)
                    lines.append(f"  {elem_str} {self._c_ident(f_name)}[{f_type.size}];")
                else:
                    f_str = CTypeMapper.to_c_type(f_type)
                    lines.append(f"  {f_str} {self._c_ident(f_name)};")
            lines.append("};")
            lines.append("")

        # 3. Echos (Unions)
        for name, fields in self.echos.items():
            lines.append(f"union {name} {{")
            for f_name, f_type in fields.items():
                if isinstance(f_type, ArrayType) and f_type.size is not None:
                    elem_str = CTypeMapper.to_c_type(f_type.element)
                    lines.append(f"  {elem_str} {self._c_ident(f_name)}[{f_type.size}];")
                else:
                    f_str = CTypeMapper.to_c_type(f_type)
                    lines.append(f"  {f_str} {self._c_ident(f_name)};")
            lines.append("};")
            lines.append("")

        # 4. Omens (Tagged Unions)
        for name, variants in self.omens.items():
            enum_name = f"{name}Tag"
            lines.append(f"typedef enum {enum_name} {{")
            for v_name in variants:
                lines.append(f"  {name.upper()}_{v_name.upper()},")
            lines.append(f"}} {enum_name};")
            lines.append("")

            lines.append(f"struct {name} {{")
            lines.append(f"  {enum_name} tag;")
            lines.append("  union {")
            for v_name, v_fields in variants.items():
                lines.append(f"    struct {{")
                for f_name, f_type in v_fields.items():
                    if isinstance(f_type, ArrayType) and f_type.size is not None:
                        elem_str = CTypeMapper.to_c_type(f_type.element)
                        lines.append(f"      {elem_str} {f_name}[{f_type.size}];")
                    else:
                        f_str = CTypeMapper.to_c_type(f_type)
                        lines.append(f"      {f_str} {f_name};")
                lines.append(f"    }} {v_name.lower()};")
            lines.append("  } as;")
            lines.append("};")
            lines.append("")

        return "\n".join(lines)

    def generate_constants(self) -> str:
        """Generates top-level immutable constants as C #define or const globals."""
        if not self.consts:
            return ""

        lines = [
            "/* -------------------------------------------------------------------------",
            " * Global Constants",
            " * ------------------------------------------------------------------------- */",
        ]

        for name, (c_type, val) in self.consts.items():
            if val is not None:
                if isinstance(val, str):
                    lines.append(f'#define {name} pengu_string_from_cstr("{val}")')
                elif isinstance(val, bool):
                    lines.append(f'#define {name} {"true" if val else "false"}')
                else:
                    lines.append(f"#define {name} {val}")
            else:
                t_str = CTypeMapper.to_c_type(c_type, const=True)
                lines.append(f"{t_str} {name};")

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _c_ident(name: str) -> str:
        if name in (
            "default", "case", "switch", "register", "goto", "volatile", "union", "enum", "struct", "auto",
            "long", "short", "int", "char", "float", "double", "signed", "unsigned", "void", "const",
            "static", "extern", "inline", "restrict", "return", "sizeof", "typedef"
        ):
            return f"_{name}"
        return name

    def generate_function_prototypes(self) -> str:
        """Generates all forward function prototypes."""
        lines = [
            "/* -------------------------------------------------------------------------",
            " * Function Prototypes",
            " * ------------------------------------------------------------------------- */",
        ]

        for w in self.weaves:
            c_name = w["c_name"]
            ret_str = CTypeMapper.to_c_type(w["return_type"])
            param_strs = []

            # Self parameter for enchanting methods
            if w["enchanted_type"] is not None:
                self_t_str = CTypeMapper.to_c_type(w["enchanted_type"])
                param_strs.append(f"{self_t_str}* self")

            for p_info in w["params"]:
                p_name, p_type = p_info[0], p_info[1]
                param_strs.append(CTypeMapper.to_c_decl(p_type, self._c_ident(p_name)))

            params_formatted = ", ".join(param_strs) if param_strs else "void"
            inline_pfx = "static inline __attribute__((always_inline)) " if w["is_inline"] else ""

            if c_name == "main":
                # Expose main wrapper or standard signature
                lines.append(f"{inline_pfx}{ret_str} pengu_main({params_formatted});")
            else:
                lines.append(f"{inline_pfx}{ret_str} {c_name}({params_formatted});")

        lines.append("")
        return "\n".join(lines)

    def generate_function_definitions(self) -> str:
        """Generates function implementation bodies in topological module order."""
        lines = [
            "/* -------------------------------------------------------------------------",
            " * Function Definitions",
            " * ------------------------------------------------------------------------- */",
        ]

        for w in self.weaves:
            c_name = w["c_name"]
            ret_str = CTypeMapper.to_c_type(w["return_type"])
            param_strs = []

            if w["enchanted_type"] is not None:
                self_t_str = CTypeMapper.to_c_type(w["enchanted_type"])
                param_strs.append(f"{self_t_str}* restrict self")

            for p_info in w["params"]:
                p_name, p_type = p_info[0], p_info[1]
                param_strs.append(CTypeMapper.to_c_decl(p_type, self._c_ident(p_name), restrict=True))

            params_formatted = ", ".join(param_strs) if param_strs else "void"
            inline_pfx = "static inline __attribute__((always_inline)) " if w["is_inline"] else ""
            fn_actual_name = "pengu_main" if c_name == "main" else c_name

            lines.append(f"{inline_pfx}{ret_str} {fn_actual_name}({params_formatted}) {{")
            self.indent_level += 1
            self.current_function = fn_actual_name
            self.current_return_type = w["return_type"]
            self.current_enchanted_type = w.get("enchanted_type")
            self.current_subst_map = w.get("subst_map", {})
            self.local_vars = {}
            if w["enchanted_type"] is not None:
                self.local_vars["self"] = RefType(w["enchanted_type"])
            for p_info in w["params"]:
                self.local_vars[p_info[0]] = p_info[1]

            self.defer_stack.append([])
            self.errdefer_stack.append([])

            body_code = self._translate_block(w["body_stmts"])
            lines.append(body_code)

            # Emit any remaining top-level defers before function exit
            active_defers = self.defer_stack.pop() if self.defer_stack else []
            if self.errdefer_stack:
                self.errdefer_stack.pop()
            if active_defers:
                lines.append(f"{self.indent()}/* Deferred cleanup */")
                for d in reversed(active_defers):
                    lines.append(f"{self.indent()}{d};")

            self.indent_level -= 1
            lines.append("}")
            lines.append("")

        return "\n".join(lines)

    def _translate_block(self, stmts: List[Tree]) -> str:
        """Translates a list of statements in a block."""
        lines = []
        for stmt in stmts:
            s_code = self._translate_stmt(stmt)
            if s_code:
                lines.append(s_code)
        return "\n".join(lines)

    def _translate_stmt(self, node: Tree) -> str:
        """Translates single statement node to C99."""
        if not isinstance(node, Tree):
            return ""

        if node.data == "stmt" and node.children:
            return self._translate_stmt(node.children[0])

        rule = node.data
        ind = self.indent()

        if rule == "var_decl":
            name = str(node.children[0])
            type_node = None
            expr_idx = 1
            if len(node.children) == 3:
                type_node = node.children[1]
                expr_idx = 2
            expr_node = node.children[expr_idx]

            t = None
            sym = self.symbols.lookup(name) if self.symbols else None
            if type_node is not None:
                t = ast_to_type(type_node, self._lookup_type_fn)
            else:
                if sym:
                    t = sym.type

            if t is not None:
                self.local_vars[name] = t

            t_str = CTypeMapper.to_c_type(t) if t is not None else "int32_t"
            if t_str == "void":
                t_str = "void /* invalid variable type */"

            if isinstance(expr_node, Tree) and expr_node.data == "or_block":
                left_op = expr_node.children[0]
                block_stmts = expr_node.children[1:]
                tmp_res = self.get_temp_name("_res")
                left_c = self._translate_expr(left_op)
                self.local_vars["error"] = STRING_TYPE
                self.indent_level += 1
                inner_body = [self._translate_stmt(bs) for bs in block_stmts]
                self.indent_level -= 1
                block_c = "\n".join(inner_body)
                return (
                    f"{ind}PenguResult {tmp_res} = {left_c};\n"
                    f"{ind}if (!pengu_result_is_ok(&{tmp_res})) {{\n"
                    f"{ind}  PenguString error = pengu_string_from_cstr({tmp_res}.err_val ? {tmp_res}.err_val : \"error\");\n"
                    f"{block_c}\n"
                    f"{ind}}}\n"
                    f"{ind}{t_str} {name} = ({t_str})({tmp_res}.ok_val);"
                )

            alloc_comment = " /* stack */" if (isinstance(t, (RuneType, ArrayType)) or (sym and sym.is_stack_alloc)) else ""
            expr_code = self._translate_expr(expr_node, expected_type=t)
            if isinstance(t, ArrayType) and t.size is not None:
                elem_str = CTypeMapper.to_c_type(t.element)
                return f"{ind}{elem_str} {name}[{t.size}] = {expr_code};{alloc_comment}"
            if isinstance(t, ArrayType) and t.size is None and isinstance(expr_node, Tree) and expr_node.data == "array_init_expr":
                array_size = self._translate_expr(expr_node.children[1])
                elem_str = CTypeMapper.to_c_type(t.element)
                return f"{ind}{elem_str} {name}[{array_size}] = {{0}};{alloc_comment}"
            return f"{ind}{t_str} {name} = {expr_code};{alloc_comment}"


        elif rule == "let_decl":
            var_names_node = node.children[0]
            names = []
            if isinstance(var_names_node, Tree) and var_names_node.data == "var_name_list":
                names = [str(tok) for tok in var_names_node.children]
            else:
                names = [str(var_names_node)]

            expr_idx = 1
            type_node = None
            if len(node.children) == 3:
                type_node = node.children[1]
                expr_idx = 2
            expr_node = node.children[expr_idx]

            if len(names) == 1:
                name = names[0]
                t = None
                sym = self.symbols.lookup(name) if self.symbols else None
                if type_node is not None:
                    t = ast_to_type(type_node, self._lookup_type_fn)
                else:
                    if sym:
                        t = sym.type
                if t is not None:
                    self.local_vars[name] = t
                t_str = CTypeMapper.to_c_type(t, const=True)
                if t_str == "void":
                    t_str = "void /* invalid variable type */"

                if isinstance(expr_node, Tree) and expr_node.data == "or_block":
                    left_op = expr_node.children[0]
                    block_stmts = expr_node.children[1:]
                    tmp_res = self.get_temp_name("_res")
                    left_c = self._translate_expr(left_op)
                    self.local_vars["error"] = STRING_TYPE
                    self.indent_level += 1
                    inner_body = [self._translate_stmt(bs) for bs in block_stmts]
                    self.indent_level -= 1
                    block_c = "\n".join(inner_body)
                    return (
                        f"{ind}PenguResult {tmp_res} = {left_c};\n"
                        f"{ind}if (!pengu_result_is_ok(&{tmp_res})) {{\n"
                        f"{ind}  PenguString error = pengu_string_from_cstr({tmp_res}.err_val ? {tmp_res}.err_val : \"error\");\n"
                        f"{block_c}\n"
                        f"{ind}}}\n"
                        f"{ind}{t_str} {name} = ({t_str})({tmp_res}.ok_val);"
                    )

                alloc_comment = " /* stack */" if (sym and sym.is_stack_alloc) else ""
                expr_code = self._translate_expr(expr_node, expected_type=t)
                if isinstance(t, ArrayType) and t.size is not None:
                    elem_str = CTypeMapper.to_c_type(t.element, const=True)
                    return f"{ind}{elem_str} {name}[{t.size}] = {expr_code};{alloc_comment}"
                return f"{ind}{t_str} {name} = {expr_code};{alloc_comment}"
            else:
                # Destructuring
                tmp = self.get_temp_name("_destruct")
                expr_code = self._translate_expr(expr_node)

                # Match rune struct
                matched_rune = None
                for r_name, r_fields in self.runes.items():
                    if len(r_fields) == len(names):
                        matched_rune = r_name
                        break

                tmp_type = matched_rune if matched_rune else "const void*"
                lines = [f"{ind}{tmp_type} {tmp} = {expr_code};"]

                rune_field_names = list(self.runes[matched_rune].keys()) if (matched_rune and matched_rune in self.runes) else []

                for i, name in enumerate(names):
                    sym = self.symbols.lookup(name) if self.symbols else None
                    t_str = CTypeMapper.to_c_type(sym.type, const=True) if sym else "const int32_t"
                    if t_str == "void":
                        t_str = "const int32_t"
                    if i < len(rune_field_names):
                        lines.append(f"{ind}{t_str} {name} = {tmp}.{rune_field_names[i]};")
                    else:
                        lines.append(f"{ind}{t_str} {name} = {tmp}[{i}];")
                return "\n".join(lines)

        elif rule == "set_stmt":
            target_node = node.children[0]
            expr_node = node.children[1]
            target_str = self._translate_set_target(target_node)
            expr_str = self._translate_expr(expr_node)

            inner_target = target_node.children[0] if (isinstance(target_node, Tree) and target_node.data == "set_target" and target_node.children) else target_node
            target_type = None
            if isinstance(inner_target, Tree) and inner_target.data == "normal_target":
                obj_name = str(inner_target.children[0])
                target_type = self._lookup_var_type(obj_name)
            elif isinstance(inner_target, Token):
                target_type = self._lookup_var_type(str(inner_target))

            rune_name = None
            if target_type is not None:
                if isinstance(target_type, RuneType):
                    rune_name = target_type.name
                elif isinstance(target_type, BaseType) and target_type.name in self.runes:
                    rune_name = target_type.name

            if rune_name and rune_name in self.runes and len(self.runes[rune_name]) >= 3:
                return f"{ind}memcpy(&({target_str}), &({expr_str}), sizeof({rune_name}));"

            return f"{ind}{target_str} = {expr_str};"

        elif rule == "calling_stmt":
            call_tree = Tree("calling_expr", node.children)
            expr_code = self._translate_expr(call_tree)
            return f"{ind}{expr_code};"

        elif rule == "named_stmt":
            name = str(node.children[0])
            expr_str = self._translate_expr(node.children[1])
            return f"{ind}{name} = {expr_str};"


        elif rule == "if_stmt":
            cond_node = node.children[0]
            block_node = node.children[1]
            else_node = node.children[2] if len(node.children) > 2 else None

            # Dead code elimination for constant condition
            folded = self.const_folder.fold(cond_node)
            if folded is not None:
                if bool(folded) is True:
                    body_str = self._translate_nested_block(block_node)
                    return f"{ind}/* dead code eliminated (branch always true) */\n{body_str}"
                else:
                    if else_node:
                        self.indent_level += 1
                        else_str = self._translate_else_block(else_node)
                        self.indent_level -= 1
                        return f"{ind}/* dead code eliminated (branch always false) */\n{else_str}"
                    return f"{ind}/* dead code eliminated (branch always false) */"

            cond_str = self._translate_if_cond(cond_node)
            self.indent_level += 1
            body_str = self._translate_nested_block(block_node)
            self.indent_level -= 1

            res = f"{ind}if ({cond_str}) {{\n{body_str}\n{ind}}}"
            if else_node:
                self.indent_level += 1
                else_str = self._translate_else_block(else_node)
                self.indent_level -= 1
                res += f" else {{\n{else_str}\n{ind}}}"
            return res

        elif rule == "unless_stmt":
            cond_node = node.children[0]
            block_node = node.children[1]
            else_node = node.children[2] if len(node.children) > 2 else None

            folded = self.const_folder.fold(cond_node)
            if folded is not None:
                if bool(folded) is False:
                    body_str = self._translate_nested_block(block_node)
                    return f"{ind}/* dead code eliminated (unless always true) */\n{body_str}"
                else:
                    if else_node:
                        self.indent_level += 1
                        else_str = self._translate_else_block(else_node)
                        self.indent_level -= 1
                        return f"{ind}/* dead code eliminated (unless always false) */\n{else_str}"
                    return f"{ind}/* dead code eliminated (unless always false) */"

            cond_str = self._translate_expr(cond_node)
            self.indent_level += 1
            body_str = self._translate_nested_block(block_node)
            self.indent_level -= 1

            res = f"{ind}if (!({cond_str})) {{\n{body_str}\n{ind}}}"
            if else_node:
                self.indent_level += 1
                else_str = self._translate_else_block(else_node)
                self.indent_level -= 1
                res += f" else {{\n{else_str}\n{ind}}}"
            return res

        elif rule == "while_stmt":
            cond_node = node.children[0]
            block_node = node.children[1]
            cond_str = self._translate_expr(cond_node)

            self.indent_level += 1
            body_str = self._translate_nested_block(block_node)
            self.indent_level -= 1

            return f"{ind}while ({cond_str}) {{\n{body_str}\n{ind}}}"

        elif rule == "for_stmt":
            first_child = node.children[0]
            if isinstance(first_child, Tree) and first_child.data == "for_range_stmt":
                return self._translate_for_range(first_child)
            elif isinstance(first_child, Tree) and first_child.data == "for_in_stmt":
                return self._translate_for_in(first_child)
            elif node.data == "for_range_stmt":
                return self._translate_for_range(node)
            elif node.data == "for_in_stmt":
                return self._translate_for_in(node)
            return ""

        elif rule == "with_stmt":
            target_expr = node.children[0]
            stmts = node.children[1:]
            target_str = self._translate_expr(target_expr)

            self.with_stack.append(target_str)
            self.indent_level += 1
            body_str = self._translate_block(stmts)
            self.indent_level -= 1
            self.with_stack.pop()

            return f"{ind}/* with ({target_str}) */\n{body_str}"

        elif rule == "defer_stmt":
            defer_expr = node.children[0]
            defer_str = self._translate_expr(defer_expr)
            if self.defer_stack:
                self.defer_stack[-1].append(defer_str)
            return f"{ind}/* defer {defer_str} */"

        elif rule == "errdefer_stmt":
            errdefer_expr = node.children[0]
            errdefer_str = self._translate_expr(errdefer_expr)
            if self.errdefer_stack:
                self.errdefer_stack[-1].append(errdefer_str)
            return f"{ind}/* errdefer {errdefer_str} */"

        elif rule == "banish_stmt":
            target_expr = node.children[0]
            target_str = self._translate_expr(target_expr)
            return f"{ind}pengu_banish((void*)({target_str}));"

        elif rule == "return_stmt":
            ret_expr = node.children[0] if node.children else None
            ret_val_str = self._translate_expr(ret_expr, expected_type=self.current_return_type) if ret_expr is not None else ""

            is_err_ret = False
            if "pengu_result_err" in ret_val_str or "error" in ret_val_str:
                is_err_ret = True

            cleanup_lines = []
            if is_err_ret and self.errdefer_stack:
                for d in reversed(self.errdefer_stack[-1]):
                    cleanup_lines.append(f"{ind}{d};")

            if self.defer_stack:
                for d in reversed(self.defer_stack[-1]):
                    cleanup_lines.append(f"{ind}{d};")

            cleanup_str = "\n".join(cleanup_lines) + ("\n" if cleanup_lines else "")
            if ret_expr is not None:
                if cleanup_lines:
                    tmp = self.get_temp_name("_ret")
                    ret_t_str = CTypeMapper.to_c_type(self.current_return_type)
                    return f"{ind}{ret_t_str} {tmp} = {ret_val_str};\n{cleanup_str}{ind}return {tmp};"
                return f"{ind}return {ret_val_str};"
            return f"{cleanup_str}{ind}return;"

        elif rule == "break_stmt":
            return f"{ind}break;"

        elif rule == "continue_stmt":
            return f"{ind}continue;"

        elif rule == "expr_stmt":
            expr_code = self._translate_expr(node.children[0])
            return f"{ind}{expr_code};"

        return ""

    def _translate_for_range(self, node: Tree) -> str:
        """Translates for i from start to end [step s] loop."""
        ind = self.indent()
        var_name = str(node.children[0])
        start_str = self._translate_expr(node.children[1])
        end_str = self._translate_expr(node.children[2])
        step_str = "1"
        block_node = node.children[3]
        if len(node.children) == 5:
            step_str = self._translate_expr(node.children[3])
            block_node = node.children[4]

        self.indent_level += 1
        body_str = self._translate_nested_block(block_node)
        self.indent_level -= 1

        return (
            f"{ind}for (int32_t {var_name} = {start_str}; "
            f"{var_name} <= {end_str}; {var_name} += {step_str}) {{\n"
            f"{body_str}\n{ind}}}"
        )

    def _translate_for_in(self, node: Tree) -> str:
        """Translates for item in collection loop."""
        ind = self.indent()
        var_name = str(node.children[0])
        col_expr = node.children[1]
        block_node = node.children[2]

        col_str = self._translate_expr(col_expr)
        iter_idx = self.get_temp_name("_i")
        col_tmp = self.get_temp_name("_col")

        var_sym = self.symbols.lookup(var_name) if self.symbols else None
        item_t = var_sym.type if var_sym else None
        item_t_str = CTypeMapper.to_c_type(item_t) if item_t else "int32_t"
        if item_t_str == "void":
            item_t_str = "int32_t"

        col_t_str = "PenguList"
        if isinstance(col_expr, Tree) and col_expr.data == "var_ref":
            c_sym = self.symbols.lookup(str(col_expr.children[0])) if self.symbols else None
            if c_sym and isinstance(c_sym.type, SliceType):
                col_t_str = "PenguSlice"

        self.indent_level += 1
        body_str = self._translate_nested_block(block_node)
        self.indent_level -= 1

        return (
            f"{ind}{col_t_str} {col_tmp} = {col_str};\n"
            f"{ind}for (size_t {iter_idx} = 0; {iter_idx} < (size_t)({col_tmp}.len); {iter_idx}++) {{\n"
            f"{ind}  {item_t_str} {var_name} = (({item_t_str}*){col_tmp}.data)[{iter_idx}];\n"
            f"{body_str}\n{ind}}}"
        )

    def _translate_nested_block(self, node: Tree) -> str:
        """Translates a block node."""
        if not isinstance(node, Tree):
            return ""
        if node.data == "block":
            if len(node.children) == 1 and isinstance(node.children[0], Tree) and node.children[0].data == "simple_stmt":
                return self._translate_stmt(node.children[0])
            return self._translate_block(node.children)
        return self._translate_stmt(node)

    def _translate_else_block(self, node: Tree) -> str:
        """Translates an else block or else if statement."""
        if isinstance(node, Tree) and node.data == "else_block":
            if len(node.children) == 1 and isinstance(node.children[0], Tree) and node.children[0].data == "if_stmt":
                return self._translate_stmt(node.children[0])
            return self._translate_block(node.children)
        elif isinstance(node, Tree) and node.data == "if_stmt":
            return self._translate_stmt(node)
        return ""

    def _translate_set_target(self, node: Any) -> str:
        """Translates the left-hand side target of a set statement."""
        if not isinstance(node, Tree):
            name = str(node)
            sym = self.symbols.lookup(name) if self.symbols else None
            if self.with_stack and (not sym or sym.kind == "field"):
                base_target = self.with_stack[-1]
                sep = "->" if base_target == "self" else "."
                return f"{base_target}{sep}{name}"
            return name

        if node.data == "set_target":
            return self._translate_set_target(node.children[0])

        if node.data == "with_target":
            field_name = str(node.children[0])
            base_target = self.with_stack[-1] if self.with_stack else "self"
            sep = "->" if base_target == "self" else "."
            target_str = f"{base_target}{sep}{field_name}"
            for acc in node.children[1:]:
                target_str = self._translate_access_op(target_str, acc)
            return target_str

        elif node.data == "normal_target":
            base_name = str(node.children[0])
            sym = self.symbols.lookup(base_name) if self.symbols else None
            if self.with_stack and (not sym or sym.kind == "field"):
                base_target = self.with_stack[-1]
                sep = "->" if base_target == "self" else "."
                target_str = f"{base_target}{sep}{base_name}"
            else:
                target_str = base_name
            for acc in node.children[1:]:
                target_str = self._translate_access_op(target_str, acc)
            return target_str

        elif node.data == "essence_target":
            inner_str = self._translate_expr(node.children[0])
            return f"(*{inner_str})"

        return str(node)


    def _translate_access_op(self, base_str: str, acc_node: Tree) -> str:
        """Translates member and index access operators."""
        if acc_node.data == "dot_access":
            sym = self.symbols.lookup(base_str) if self.symbols else None
            sep = "->" if (base_str == "self" or (sym and isinstance(sym.type, RefType))) else "."
            return f"{base_str}{sep}{acc_node.children[0]}"
        elif acc_node.data == "arrow_access":
            return f"{base_str}->{acc_node.children[0]}"
        elif acc_node.data == "at_access":
            idx = self._translate_expr(acc_node.children[0])
            return f"{base_str}[{idx}]"
        return base_str

    def _translate_if_cond(self, node: Any) -> str:
        """Translates if condition, including maybe binding pattern."""
        if isinstance(node, Tree):
            if node.data == "if_cond_binding_present" or node.data == "if_cond_binding":
                # NAME as type is expr is present
                var_name = str(node.children[0])
                type_node = node.children[1]
                expr_node = node.children[2]
                expr_str = self._translate_expr(expr_node)
                t = ast_to_type(type_node, lambda n: self.symbols.lookup(n).type if self.symbols.lookup(n) else None)
                t_str = CTypeMapper.to_c_type(t)
                return f"({t_str} {var_name} = {expr_str}, pengu_maybe_is_present(&{var_name}))"
        return self._translate_expr(node)

    def _translate_string_lit(self, s_val: str) -> str:
        """Translates string literal, generating pengu_string_format call for interpolated expressions."""
        import re
        matches = list(re.finditer(r'\{([^}]+)\}', s_val))
        if not matches:
            return f'pengu_string_from_cstr("{s_val}")'

        fmt_parts = []
        c_args = []
        last_end = 0
        for m in matches:
            literal_prefix = s_val[last_end:m.start()]
            fmt_parts.append(literal_prefix.replace("%", "%%"))
            expr_str = m.group(1).strip()

            var_t = self._lookup_var_type(expr_str)
            sym = self.symbols.lookup(expr_str) if self.symbols else None
            t = var_t or (sym.type if sym else None)

            expr_c = self._c_ident(expr_str)
            if t is not None:
                if t.is_int():
                    fmt_parts.append("%d")
                    c_args.append(f"(int32_t)({expr_c})")
                elif t.is_float():
                    fmt_parts.append("%f")
                    c_args.append(f"(double)({expr_c})")
                elif isinstance(t, BaseType) and t.name == "bool":
                    fmt_parts.append("%s")
                    c_args.append(f"(({expr_c}) ? \"true\" : \"false\")")
                elif isinstance(t, BaseType) and t.name == "string":
                    fmt_parts.append("%s")
                    c_args.append(f"({expr_c}).data")
                else:
                    fmt_parts.append("%s")
                    c_args.append(f"({expr_c}).data")
            else:
                fmt_parts.append("%s")
                c_args.append(f"({expr_c}).data" if not expr_str.isdigit() else expr_c)
            last_end = m.end()

        fmt_parts.append(s_val[last_end:].replace("%", "%%"))
        full_fmt = "".join(fmt_parts)
        return f'pengu_string_format("{full_fmt}", {", ".join(c_args)})'

    def _is_string_expr(self, n: Any) -> bool:
        """Checks if an AST expression node evaluates to a PenguString."""
        if n is None:
            return False
        if isinstance(n, Token):
            return n.type == "STRING"
        if isinstance(n, Tree):
            rule = n.data
            if rule in ("string_lit", "interpolated_string"):
                return True
            if rule == "var_ref":
                vt = self._lookup_var_type(str(n.children[0]))
                return vt is not None and getattr(vt, "name", "") == "string"
            if rule == "self_arrow":
                field_name = str(n.children[0])
                if self.current_enchanted_type and isinstance(self.current_enchanted_type, (RuneType, EchoType)):
                    ft = self.current_enchanted_type.fields.get(field_name)
                    return ft is not None and getattr(ft, "name", "") == "string"
                return False
            if rule == "field_access":
                target_node = n.children[0]
                field_name = str(n.children[1])
                target_type = None
                if isinstance(target_node, Tree) and target_node.data == "var_ref":
                    target_type = self._lookup_var_type(str(target_node.children[0]))
                elif isinstance(target_node, Tree) and target_node.data == "self_ref":
                    target_type = self.current_enchanted_type
                if target_type and isinstance(target_type, (RuneType, EchoType)):
                    ft = target_type.fields.get(field_name)
                    return ft is not None and getattr(ft, "name", "") == "string"
                return False
            if rule == "cast_expr":
                t = ast_to_type(n.children[1], lambda name: self.symbols.lookup(name).type if self.symbols and self.symbols.lookup(name) else None)
                return t is not None and getattr(t, "name", "") == "string"
            if rule == "add":
                return self._is_string_expr(n.children[0]) or self._is_string_expr(n.children[1])
            if rule == "calling_expr":
                fn_node = n.children[0]
                fn_name = ""
                if isinstance(fn_node, Token):
                    fn_name = str(fn_node)
                elif isinstance(fn_node, Tree):
                    if fn_node.data == "var_ref":
                        fn_name = str(fn_node.children[0])
                    elif fn_node.data == "field_access":
                        obj_node = fn_node.children[0]
                        m_name = str(fn_node.children[1])
                        if isinstance(obj_node, Tree) and obj_node.data == "var_ref":
                            obj_type = self._lookup_var_type(str(obj_node.children[0]))
                            if obj_type and hasattr(obj_type, "name"):
                                fn_name = f"{obj_type.name}_{m_name}"
                        elif isinstance(obj_node, Tree) and obj_node.data == "self_ref":
                            if self.current_enchanted_type and hasattr(self.current_enchanted_type, "name"):
                                fn_name = f"{self.current_enchanted_type.name}_{m_name}"
                if fn_name:
                    sym = self.symbols.lookup(fn_name) if self.symbols else None
                    if sym and isinstance(sym.type, FnType) and sym.type.return_type:
                        return getattr(sym.type.return_type, "name", "") == "string"
                    if fn_name in self.fn_info:
                        ret_t = self.fn_info[fn_name].get("return_type")
                        return ret_t is not None and getattr(ret_t, "name", "") == "string"
            if rule == "if_expr":
                return self._is_string_expr(n.children[1]) or self._is_string_expr(n.children[2])

            try:
                inferrer = TypeInferrer(self.symbols)
                inferred_t = inferrer.infer(n)
                if inferred_t is not None and getattr(inferred_t, "name", "") == "string":
                    return True
            except Exception:
                pass
        return False

    def _translate_expr(self, node: Any, expected_type: Optional[Type] = None) -> str:
        """Translates expression node into C99 expression string."""
        if node is None:
            return ""

        if isinstance(node, Token):
            val = str(node)
            if node.type == "INT":
                return val
            elif node.type == "FLOAT":
                return val
            elif node.type == "STRING":
                return self._translate_string_lit(val.strip('"'))
            elif node.type == "NAME":
                return val
            return val

        if not isinstance(node, Tree):
            return str(node)

        # Check const folding for entire expression
        if node.data not in ("string_lit", "interpolated_string"):
            folded = self.const_folder.fold(node)
            if folded is not None:
                return self._format_const_val(folded)

        rule = node.data

        # 1. Literals
        if rule == "int_lit":
            return str(node.children[0])
        elif rule == "float_lit":
            return str(node.children[0])
        elif rule == "string_lit":
            return self._translate_string_lit(str(node.children[0]).strip('"'))
        elif rule == "true_lit":
            return "true"
        elif rule == "false_lit":
            return "false"
        elif rule == "maybe_none":
            return "pengu_maybe_none()"
        elif rule == "error_lit":
            return "error"
        elif rule == "var_ref":
            name = str(node.children[0])
            sym = self.symbols.lookup(name) if self.symbols else None
            if sym and hasattr(sym, "const_val") and sym.const_val is not None:
                return self._format_const_val(sym.const_val)
            if name in self.consts and self.consts[name][1] is not None:
                return self._format_const_val(self.consts[name][1])
            if self.with_stack and (not sym or sym.kind == "field"):
                base_target = self.with_stack[-1]
                sep = "->" if base_target == "self" else "."
                return f"{base_target}{sep}{name}"
            return self._c_ident(name)

        elif rule == "self_ref":
            return "self"


        # 2. Binary Arithmetic and Logic
        elif rule == "add":
            left_node, right_node = node.children[0], node.children[1]
            left = self._translate_expr(left_node)
            right = self._translate_expr(right_node)
            if self._is_string_expr(left_node) or self._is_string_expr(right_node):
                left_str = left if self._is_string_expr(left_node) else f"pengu_to_string({left})"
                right_str = right if self._is_string_expr(right_node) else f"pengu_to_string({right})"
                return f"pengu_string_concat({left_str}, {right_str})"
            return f"({left} + {right})"

        elif rule in ("eq", "ne"):
            left_node, right_node = node.children[0], node.children[1]
            left = self._translate_expr(left_node)
            right = self._translate_expr(right_node)
            if self._is_string_expr(left_node) or self._is_string_expr(right_node):
                left_str = left if self._is_string_expr(left_node) else f"pengu_to_string({left})"
                right_str = right if self._is_string_expr(right_node) else f"pengu_to_string({right})"
                if rule == "eq":
                    return f"pengu_string_equal({left_str}, {right_str})"
                else:
                    return f"(!pengu_string_equal({left_str}, {right_str}))"
            op = "==" if rule == "eq" else "!="
            return f"({left} {op} {right})"

        elif rule in ("sub", "mul", "div", "mod", "shl", "shr", "bitwise_and", "bitwise_or", "bitwise_xor",
                      "lt", "le", "gt", "ge"):
            op_map = {
                "sub": "-", "mul": "*", "div": "/", "mod": "%",
                "shl": "<<", "shr": ">>", "bitwise_and": "&", "bitwise_or": "|", "bitwise_xor": "^",
                "lt": "<", "le": "<=", "gt": ">", "ge": ">=",
            }
            left = self._translate_expr(node.children[0])
            right = self._translate_expr(node.children[1])
            return f"({left} {op_map[rule]} {right})"

        # 3. Unary
        elif rule == "neg":
            return f"(-{self._translate_expr(node.children[0])})"
        elif rule == "log_not":
            return f"(!{self._translate_expr(node.children[0])})"
        elif rule == "bit_not":
            return f"(~{self._translate_expr(node.children[0])})"
        elif rule == "sigil_of":
            return f"(&{self._translate_expr(node.children[0])})"
        elif rule == "essence_of":
            child = node.children[0]
            if isinstance(child, Tree) and child.data == "length_expr":
                return self._translate_expr(child)
            return f"(*{self._translate_expr(node.children[0])})"
        elif rule == "transmute":
            expr_str = self._translate_expr(node.children[0])
            t = ast_to_type(node.children[1], lambda n: self.symbols.lookup(n).type if self.symbols.lookup(n) else None)
            t_str = CTypeMapper.to_c_type(t)
            return f"(({t_str})({expr_str}))"
        elif rule == "size_of":
            t = ast_to_type(node.children[0], lambda n: self.symbols.lookup(n).type if self.symbols.lookup(n) else None)
            t_str = CTypeMapper.to_c_type(t)
            return f"sizeof({t_str})"
        elif rule == "banish_expr":
            target = self._translate_expr(node.children[0])
            return f"pengu_banish((void*)({target}))"

        # 4. Invocations / Calling
        elif rule == "calling_expr":
            target_node = node.children[0]
            args_node = node.children[1] if len(node.children) > 1 else None

            # Translate arguments
            args = []
            if args_node and isinstance(args_node, Tree) and args_node.data == "arg_list":
                for arg in args_node.children:
                    if isinstance(arg, Tree):
                        if arg.data == "pos_arg":
                            args.append(self._translate_expr(arg.children[0]))
                        elif arg.data == "named_arg":
                            args.append(self._translate_expr(arg.children[1]))

            # 1. Normal target method call: obj.method(...) or self->items.method(...)
            if target_node.data == "normal_target" and len(target_node.children) >= 2 and target_node.children[-1].data in ("dot_access", "arrow_access"):
                m_name = str(target_node.children[-1].children[0])
                base_parts = target_node.children[:-1]

                obj_expr_str = str(base_parts[0])
                for part in base_parts[1:]:
                    if isinstance(part, Tree) and part.data == "arrow_access":
                        obj_expr_str += f"->{str(part.children[0])}"
                    elif isinstance(part, Tree) and part.data == "dot_access":
                        obj_expr_str += f".{str(part.children[0])}"

                obj_name = str(base_parts[0]) if len(base_parts) == 1 and isinstance(base_parts[0], (Token, str)) else None

                # Check if this is an imported module call (e.g. spark.println)
                if obj_name:
                    obj_sym = self.symbols.lookup(obj_name) if self.symbols else None
                    if obj_sym is not None and obj_sym.kind == "import":
                        fn_name = f"{obj_name}_{m_name}" if f"{obj_name}_{m_name}" in self.fn_info else m_name
                        fn_entry = self.fn_info.get(fn_name) or self.fn_info.get(m_name)
                        if fn_entry:
                            fn_params = fn_entry["params"]
                            if len(args) < len(fn_params):
                                for p in fn_params[len(args):]:
                                    if len(p) >= 3 and p[2] is not None:
                                        args.append(self._translate_expr(p[2]))
                        return f"{fn_name}({', '.join(args)})"

                # Lookup object type
                if obj_name:
                    obj_type = self._lookup_var_type(obj_name)
                else:
                    cur_t = self._lookup_var_type(str(base_parts[0]))
                    for part in base_parts[1:]:
                        field_n = str(part.children[0])
                        if cur_t is not None:
                            if isinstance(cur_t, RefType):
                                cur_t = cur_t.target
                            if isinstance(cur_t, RuneType):
                                cur_t = cur_t.fields.get(field_n)
                            elif isinstance(cur_t, BaseType) and cur_t.name in self.runes:
                                cur_t = dict(self.runes[cur_t.name]).get(field_n)
                            else:
                                cur_t = None
                    obj_type = cur_t

                actual_obj_type = obj_type
                if isinstance(actual_obj_type, AliasType):
                    actual_obj_type = actual_obj_type.target
                if isinstance(actual_obj_type, RefType) and isinstance(actual_obj_type.target, AliasType):
                    actual_obj_type = RefType(actual_obj_type.target.target)

                # Built-in ListType methods
                self_ptr = obj_expr_str if (isinstance(obj_type, RefType) or obj_expr_str == "self") else f"&{obj_expr_str}"
                if isinstance(actual_obj_type, ListType) or (isinstance(actual_obj_type, RefType) and isinstance(actual_obj_type.target, ListType)):
                    list_t = actual_obj_type.target if isinstance(actual_obj_type, RefType) else actual_obj_type
                    elem_c = CTypeMapper.to_c_type(list_t.element)
                    arg0 = args[0] if args else ""
                    if elem_c == "PenguString":
                        e_ptr = f"&(({elem_c}){{ ({arg0}).data, ({arg0}).len }})"
                    elif elem_c == "PenguList":
                        e_ptr = f"&(({elem_c}){{ ({arg0}).data, ({arg0}).len, ({arg0}).cap, ({arg0}).elem_size }})"
                    elif elem_c == "PenguMap":
                        e_ptr = f"&(({elem_c}){{ ({arg0}).entries, ({arg0}).len, ({arg0}).cap, ({arg0}).key_size, ({arg0}).val_size }})"
                    elif elem_c in ("int32_t", "int64_t", "float", "double", "bool", "uint8_t", "int8_t", "uint16_t", "int16_t", "uint32_t", "uint64_t"):
                        e_ptr = f"&(({elem_c}){{ {arg0} }})"
                    else:
                        e_ptr = f"&({arg0})"
                    if m_name in ("push", "append"):
                        return f"pengu_list_push({self_ptr}, {e_ptr})"
                    elif m_name == "pop":
                        return f"(*({elem_c}*)pengu_list_pop_val({self_ptr}))"
                    elif m_name == "len":
                        return f"({obj_expr_str}.len)"
                    elif m_name == "is_empty":
                        return f"({obj_expr_str}.len == 0)"
                    elif m_name == "clear":
                        return f"pengu_list_clear({self_ptr})"
                    elif m_name == "contains":
                        return f"pengu_list_contains({self_ptr}, {e_ptr})"
                    elif m_name == "index_of":
                        return f"pengu_list_index_of({self_ptr}, {e_ptr})"
                    elif m_name == "at":
                        return f"(*({elem_c}*)pengu_list_at({self_ptr}, {args[0]}))"

                # Built-in MapType methods
                if isinstance(actual_obj_type, MapType) or (isinstance(actual_obj_type, RefType) and isinstance(actual_obj_type.target, MapType)):
                    map_t = actual_obj_type.target if isinstance(actual_obj_type, RefType) else actual_obj_type
                    key_c = CTypeMapper.to_c_type(map_t.key)
                    val_c = CTypeMapper.to_c_type(map_t.value)
                    arg0 = args[0] if len(args) > 0 else ""
                    arg1 = args[1] if len(args) > 1 else ""
                    k_ptr = f"&(({key_c}){{ ({arg0}).data, ({arg0}).len }})" if key_c == "PenguString" else f"&(({key_c}){{ {arg0} }})"
                    v_ptr = f"&(({val_c}){{ ({arg1}).data, ({arg1}).len }})" if val_c == "PenguString" else f"&(({val_c}){{ {arg1} }})"
                    if m_name in ("put", "insert", "set"):
                        return f"pengu_map_put({self_ptr}, {k_ptr}, {v_ptr})"
                    elif m_name == "get":
                        return f"(*({val_c}*)pengu_map_get({self_ptr}, {k_ptr}))"
                    elif m_name == "remove":
                        return f"pengu_map_remove({self_ptr}, {k_ptr})"
                    elif m_name in ("contains", "contains_key", "has"):
                        return f"pengu_map_contains({self_ptr}, {k_ptr})"
                    elif m_name == "len":
                        return f"({obj_expr_str}.len)"
                    elif m_name == "is_empty":
                        return f"({obj_expr_str}.len == 0)"
                    elif m_name == "clear":
                        return f"pengu_map_clear({self_ptr})"

                t_name = None
                if isinstance(actual_obj_type, RefType):
                    t_name = getattr(actual_obj_type.target, "name", str(actual_obj_type.target))
                elif actual_obj_type is not None:
                    t_name = getattr(actual_obj_type, "name", str(actual_obj_type))

                # Check if this is an enchanting method
                is_enchanting_method = False
                if t_name is not None:
                    if hasattr(self.symbols, "methods") and (t_name, m_name) in self.symbols.methods:
                        is_enchanting_method = True
                    elif hasattr(self.symbols, "monomorphized_methods") and f"{t_name}_{m_name}" in self.symbols.monomorphized_methods:
                        is_enchanting_method = True
                    elif (t_name.split("_")[0], m_name) in getattr(self.symbols, "generic_methods", {}):
                        is_enchanting_method = True
                    elif hasattr(self.symbols, "functions") and f"{t_name.replace(' ', '_')}_{m_name}" in self.symbols.functions:
                        is_enchanting_method = True
                    elif any(w.get("enchanted_type") is not None and getattr(w["enchanted_type"], "name", str(w["enchanted_type"])) == t_name and w.get("name") == m_name for w in self.weaves):
                        is_enchanting_method = True

                if is_enchanting_method:
                    c_name = f"{t_name.replace(' ', '_')}_{m_name}"
                    if isinstance(obj_type, RefType) or obj_expr_str == "self":
                        self_arg = obj_expr_str
                    else:
                        self_arg = f"&{obj_expr_str}"
                    all_args = [self_arg] + args
                    fn_entry = self.fn_info.get(c_name) or self.fn_info.get(m_name)
                    if fn_entry:
                        fn_params = fn_entry["params"]
                        if len(all_args) < len(fn_params):
                            for p in fn_params[len(all_args):]:
                                if len(p) >= 3 and p[2] is not None:
                                    all_args.append(self._translate_expr(p[2]))
                    return f"{c_name}({', '.join(all_args)})"
                else:
                    target_str = f"{obj_expr_str}->{m_name}" if isinstance(obj_type, RefType) else f"{obj_expr_str}.{m_name}"
                    return f"{target_str}({', '.join(args)})"

            # 2. With target method call: .method(...)
            elif target_node.data == "with_target":
                field_name = str(target_node.children[0])
                base_target = self.with_stack[-1] if self.with_stack else "self"

                is_enchanting_method = False
                t_name = None
                self_arg = None

                if base_target == "self":
                    if self.current_enchanted_type is not None:
                        t_name = getattr(self.current_enchanted_type, "name", str(self.current_enchanted_type))
                        self_arg = "self"
                else:
                    base_type = self._lookup_var_type(base_target)
                    if isinstance(base_type, RefType):
                        t_name = getattr(base_type.target, "name", str(base_type.target))
                        self_arg = base_target
                    elif base_type is not None:
                        t_name = getattr(base_type, "name", str(base_type))
                        self_arg = f"&{base_target}"

                if t_name is not None:
                    if hasattr(self.symbols, "methods") and (t_name, field_name) in self.symbols.methods:
                        is_enchanting_method = True
                    elif any(w.get("enchanted_type") is not None and getattr(w["enchanted_type"], "name", str(w["enchanted_type"])) == t_name and w.get("name") == field_name for w in self.weaves):
                        is_enchanting_method = True

                if is_enchanting_method:
                    c_name = f"{t_name.replace(' ', '_')}_{field_name}"
                    all_args = [self_arg] + args
                    fn_entry = self.fn_info.get(c_name) or self.fn_info.get(field_name)
                    if fn_entry:
                        fn_params = fn_entry["params"]
                        if len(all_args) < len(fn_params):
                            for p in fn_params[len(all_args):]:
                                if len(p) >= 3 and p[2] is not None:
                                    all_args.append(self._translate_expr(p[2]))
                    return f"{c_name}({', '.join(all_args)})"

                target_str = f"{base_target}.{field_name}"
                return f"{target_str}({', '.join(args)})"

            # 3. Simple function or method inside with block
            elif target_node.data == "normal_target":
                target_str = str(target_node.children[0])

                if target_str == "print":
                    if args:
                        return f'printf("%s\\n", {args[0]}.data)'
                    return 'printf("\\n")'

                if self.with_stack:
                    base_target = self.with_stack[-1]
                    base_sym = self.symbols.lookup(base_target) if self.symbols else None
                    base_type = base_sym.type if base_sym else None
                    t_name = None
                    self_arg = None
                    if base_target == "self":
                        if self.current_enchanted_type is not None:
                            t_name = getattr(self.current_enchanted_type, "name", str(self.current_enchanted_type))
                            self_arg = "self"
                    elif base_type is not None:
                        if isinstance(base_type, RefType):
                            t_name = getattr(base_type.target, "name", str(base_type.target))
                            self_arg = base_target
                        else:
                            t_name = getattr(base_type, "name", str(base_type))
                            self_arg = f"&{base_target}"

                    if t_name is not None:
                        if (hasattr(self.symbols, "methods") and (t_name, target_str) in self.symbols.methods) or any(w.get("enchanted_type") is not None and getattr(w["enchanted_type"], "name", str(w["enchanted_type"])) == t_name and w.get("name") == target_str for w in self.weaves):
                            c_name = f"{t_name.replace(' ', '_')}_{target_str}"
                            all_args = [self_arg] + args
                            fn_entry = self.fn_info.get(c_name) or self.fn_info.get(target_str)
                            if fn_entry:
                                fn_params = fn_entry["params"]
                                if len(all_args) < len(fn_params):
                                    for p in fn_params[len(all_args):]:
                                        if len(p) >= 3 and p[2] is not None:
                                            all_args.append(self._translate_expr(p[2]))
                            return f"{c_name}({', '.join(all_args)})"

                if (self.symbols and target_str in self.symbols.generic_functions) or (target_str not in self.fn_info and self.symbols):
                    matches = [m for m in self.symbols.monomorphized_functions if m.startswith(f"{target_str}_")]
                    if len(matches) == 1:
                        target_str = matches[0]
                    elif len(matches) > 1:
                        inferrer = TypeInferrer(self.symbols)
                        arg_types = []
                        if len(node.children) > 1 and node.children[1] is not None:
                            for c in node.children[1].children:
                                val = c.children[1] if c.data == "named_arg" else c.children[0]
                                arg_types.append(inferrer.infer(val))
                        mangled = f"{target_str}_" + "_".join(t.get_mangled_name() for t in arg_types)
                        if mangled in self.symbols.monomorphized_functions:
                            target_str = mangled
                        else:
                            target_str = matches[0]

                fn_entry = self.fn_info.get(target_str)
                if fn_entry:
                    fn_params = fn_entry["params"]
                    if len(args) < len(fn_params):
                        for p in fn_params[len(args):]:
                            if len(p) >= 3 and p[2] is not None:
                                args.append(self._translate_expr(p[2]))
                c_name = fn_entry["c_name"] if fn_entry else target_str
                return f"{c_name}({', '.join(args)})"

            return f"{str(target_node)}({', '.join(args)})"

        # 5. Member and index access
        elif rule == "field_access":
            target_node = node.children[0]
            raw_field = str(node.children[1])
            field_name = self._c_ident(raw_field)
            if isinstance(target_node, Tree) and target_node.data == "var_ref":
                var_name = str(target_node.children[0])
                sym = self.symbols.lookup(var_name) if self.symbols else None
                if sym and sym.kind == "import":
                    return f"{var_name}_{raw_field}"
            base = self._translate_expr(target_node)
            sym = self.symbols.lookup(base) if self.symbols else None
            var_t = sym.type if sym else self._lookup_var_type(base)
            if isinstance(var_t, MaybeType) and raw_field == "value":
                elem_c = CTypeMapper.to_c_type(var_t.element)
                return f"(*({elem_c}*){base}.value)"
            if isinstance(var_t, ResultType) and raw_field == "value":
                elem_c = CTypeMapper.to_c_type(var_t.ok_type)
                return f"(*({elem_c}*){base}.ok_val)"
            if isinstance(var_t, ResultType) and raw_field in ("error", "err"):
                elem_c = CTypeMapper.to_c_type(var_t.err_type)
                return f"(*({elem_c}*){base}.err_val)"
            sep = "->" if (base == "self" or (sym and isinstance(sym.type, RefType))) else "."
            return f"{base}{sep}{field_name}"
        elif rule == "arrow_access":
            base = self._translate_expr(node.children[0])
            field_name = self._c_ident(str(node.children[1]))
            return f"{base}->{field_name}"
        elif rule == "at_expr":
            base = self._translate_expr(node.children[0])
            idx = self._translate_expr(node.children[1])
            var_t = self._lookup_var_type(base)
            if var_t is None and isinstance(node.children[0], Tree):
                t_node = node.children[0]
                if t_node.data == "arrow_access":
                    t_field = str(t_node.children[1])
                    if self.current_enchanted_type is not None:
                        t_name = getattr(self.current_enchanted_type, "name", str(self.current_enchanted_type))
                        var_t = self.runes.get(t_name, {}).get(t_field)
                elif t_node.data == "field_access":
                    t_base = str(t_node.children[0])
                    t_field = str(t_node.children[1])
                    b_type = self._lookup_var_type(t_base)
                    if b_type and hasattr(b_type, "name"):
                        var_t = self.runes.get(b_type.name, {}).get(t_field)
            if isinstance(var_t, ListType) or (isinstance(var_t, RefType) and isinstance(var_t.target, ListType)):
                elem_t = var_t.target.element if isinstance(var_t, RefType) else var_t.element
                elem_c = CTypeMapper.to_c_type(elem_t)
                ptr = base if (isinstance(var_t, RefType) and not base.startswith("&")) else f"&({base})"
                return f"(*({elem_c}*)pengu_list_at({ptr}, {idx}))"
            return f"{base}[{idx}]"
        elif rule == "length_expr":
            base = self._translate_expr(node.children[0])
            sym = self.symbols.lookup(base) if self.symbols else None
            var_t = self._lookup_var_type(base)
            sep = "->" if (base == "self" or isinstance(var_t, RefType) or (sym and isinstance(sym.type, RefType))) else "."
            return f"{base}{sep}len"

        # 6. Cast
        elif rule == "cast_expr":
            base = self._translate_expr(node.children[0])
            t = ast_to_type(node.children[1], lambda n: self.symbols.lookup(n).type if self.symbols.lookup(n) else None)
            if isinstance(t, BaseType) and t.name == "string":
                return f"pengu_to_string({base})"
            t_str = CTypeMapper.to_c_type(t)
            return f"(({t_str})({base}))"

        # 7. Ternary if expression: if a then b else c
        elif rule == "if_expr":
            cond = self._translate_expr(node.children[0])
            then_expr = self._translate_expr(node.children[1])
            else_expr = self._translate_expr(node.children[2])
            return f"(({cond}) ? ({then_expr}) : ({else_expr}))"

        # 8. Struct init: with x is 1 and y is 2
        elif rule == "struct_init":
            field_inits = []
            for f in node.children:
                if isinstance(f, Tree) and f.data == "field_init":
                    f_name = self._c_ident(str(f.children[0]))
                    f_val = self._translate_expr(f.children[1])
                    field_inits.append(f".{f_name} = {f_val}")

            type_name = ""
            if expected_type is not None and isinstance(expected_type, (RuneType, EchoType)):
                type_name = f"({expected_type.name})"

            return f"{type_name}{{{', '.join(field_inits)}}}"

        # 9. Judge expression
        elif rule == "judge_expr":
            matched_expr = self._translate_expr(node.children[0])
            clauses = []
            else_val = "0"
            for c in node.children[1:]:
                if isinstance(c, Tree):
                    if c.data == "when_clause":
                        pat_node = c.children[0]
                        if isinstance(pat_node, Tree) and pat_node.data == "when_pattern" and pat_node.children:
                            pat_node = pat_node.children[0]
                        pat = self._translate_expr(pat_node)
                        val = self._translate_expr(c.children[-1])
                        clauses.append((pat, val))
                    elif c.data == "else_clause":
                        else_val = self._translate_expr(c.children[0])

            all_int_literals = all(pat.lstrip('-').isdigit() for pat, _ in clauses) and len(clauses) > 0
            if all_int_literals:
                cases_str = " ".join(f"case {pat}: _res = ({val}); break;" for pat, val in clauses)
                return f"(__extension__({{ int32_t _val = ({matched_expr}); int32_t _res; switch (_val) {{ {cases_str} default: _res = ({else_val}); break; }} _res; }}))"

            # Build ternary chain
            curr = else_val
            for pat, val in reversed(clauses):
                curr = f"(({matched_expr} == {pat}) ? ({val}) : ({curr}))"
            return curr

        # 10. Presence checks
        elif rule == "is_present":
            expr_str = self._translate_expr(node.children[0])
            return f"pengu_maybe_is_present(&({expr_str}))"
        elif rule == "is_not_present":
            expr_str = self._translate_expr(node.children[0])
            return f"(!pengu_maybe_is_present(&({expr_str})))"
        elif rule == "is_true":
            expr_str = self._translate_expr(node.children[0])
            return f"(({expr_str}) == true)"
        elif rule == "is_false":
            expr_str = self._translate_expr(node.children[0])
            return f"(({expr_str}) == false)"

        # 11. Collection Inits
        elif rule == "array_init_expr":
            elem_type = ast_to_type(node.children[0], self._lookup_type_fn)
            size_expr = self._translate_expr(node.children[1])
            elem_str = CTypeMapper.to_c_type(elem_type)
            return f"({elem_str}[{size_expr}]){{0}}"
        elif rule == "list_init_expr":
            elem_type = ast_to_type(node.children[0], self._lookup_type_fn)
            cap = "8"
            if len(node.children) > 1 and node.children[1] is not None:
                c_trans = self._translate_expr(node.children[1])
                if c_trans:
                    cap = c_trans
            elem_str = CTypeMapper.to_c_type(elem_type)
            return f"pengu_list_new(sizeof({elem_str}), {cap})"

        elif rule == "map_init_expr":
            key_type = ast_to_type(node.children[0], self._lookup_type_fn) if len(node.children) >= 2 else AnyType()
            val_type = ast_to_type(node.children[1], self._lookup_type_fn) if len(node.children) >= 2 else AnyType()
            k_str = CTypeMapper.to_c_type(key_type) if key_type and not isinstance(key_type, AnyType) else "PenguString"
            v_str = CTypeMapper.to_c_type(val_type) if val_type and not isinstance(val_type, AnyType) else "int32_t"
            return f"pengu_map_new(sizeof({k_str}), sizeof({v_str}))"

        # Fallback to recursively translating first child
        if node.children:
            return self._translate_expr(node.children[0], expected_type)
        return ""


    def generate_entry_point(self) -> str:
        """Generates standard C main function wrapper for executable output."""
        if not self.has_main:
            return ""

        lines = [
            "/* -------------------------------------------------------------------------",
            " * Entry Point Wrapper",
            " * ------------------------------------------------------------------------- */",
            "int main(int argc, char** argv) {",
            "  (void)argc;",
            "  (void)argv;",
            "  pengu_main();",
            "  fflush(stdout);",
            "  fflush(stderr);",
            "  return 0;",
            "}",
            "",
        ]

        return "\n".join(lines)

    def generate_bundle(
        self,
        custom_includes: Optional[List[str]] = None,
        is_library: bool = False,
        output_path: Optional[str] = None
    ) -> str:
        """Generates single monolithic bundle.c combining all modules and runtime header.

        Layout:
        1. Auto-generated header comment.
        2. #include "pengu_runtime.h"
        3. Project custom #include <header.h> directives.
        4. Forward declarations of all types.
        5. Type definitions (runes, echos, omens, aliases, consts).
        6. Function prototypes for all modules.
        7. Function implementations in topological dependency order.
        8. Entry point wrapper (if executable output).

        Args:
            custom_includes: Additional C headers from pengu.yaml.
            is_library: True if generating static or shared library artifact.
            output_path: Optional destination file path to write bundle.c.

        Returns:
            Generated C code string.
        """
        all_includes = list(self.includes)
        if custom_includes:
            for inc in custom_includes:
                if inc not in all_includes:
                    all_includes.append(inc)

        sections = [
            "/* Auto-generated by PenguScript v0.6 */",
            '#include "pengu_runtime.h"',
        ]

        for inc in all_includes:
            if inc.startswith("<") or inc.startswith('"'):
                sections.append(f"#include {inc}")
            else:
                sections.append(f'#include "{inc}"')

        sections.append("")
        sections.append("/* Compiled modules in topological order:")
        for mod in self.import_order:
            sections.append(f" * - {os.path.basename(mod)}")
        sections.append(" */")
        sections.append("")


        sections.append(self.generate_forward_declarations())
        sections.append(self.generate_type_definitions())
        sections.append(self.generate_constants())
        sections.append(self.generate_function_prototypes())
        sections.append(self.generate_function_definitions())


        if not is_library:
            entry_code = self.generate_entry_point()
            if entry_code:
                sections.append(entry_code)

        bundle_code = "\n".join(sections)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(bundle_code)

        return bundle_code
        sections.append(self.generate_function_prototypes())
        sections.append(self.generate_function_definitions())


        if not is_library:
            entry_code = self.generate_entry_point()
            if entry_code:
                sections.append(entry_code)

        bundle_code = "\n".join(sections)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(bundle_code)

        return bundle_code
