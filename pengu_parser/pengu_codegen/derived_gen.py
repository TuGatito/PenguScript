"""Code generated for the derived concepts (Par, Ordo, Vinculum, Imago, Nexus).

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    AliasType,
    ArrayType,
    BaseType,
    CVarArgsType,
    FrozenType,
    ListType,
    MapType,
    MaybeType,
    OmenType,
    Optional,
    RefType,
    ResultType,
    RuneType,
    SealType,
    Type,
)
from .ctype import (
    CTypeMapper,
)

class DerivedGenMixin:
    """Code generated for the derived concepts (Par, Ordo, Vinculum, Imago, Nexus)."""

    def _rune_derives_explicitly(self, u: Type, concept: str) -> bool:
        """True when a rune explicitly declares ``derive <concept>`` or binds the concept.

        Checks both the monomorphized type's derived concepts and the base rune's
        entry in the symbol table, as well as explicit concept bindings.
        Does not return True for automatic/implicit Imago or Nexus derivations.
        """
        try:
            derived = list(getattr(u, "derived_concepts", []) or [])
            base_n = u.get_base_name() if hasattr(u, "get_base_name") else getattr(u, "name", "")
            if self.symbols is not None:
                entry = (getattr(self.symbols, "runes", {}) or {}).get(base_n)
                if entry is not None:
                    derived.extend(getattr(entry, "derived_concepts", []) or [])
                for key in ((getattr(u, "name", ""), concept), (base_n, concept)):
                    if self.symbols is not None and hasattr(self.symbols, "concept_bindings") \
                            and key in self.symbols.concept_bindings:
                        derived.append(concept)
                        break
            return concept in derived
        except Exception:
            return False
    def _rune_clone_helper(self, u: Type) -> str:
        """Name of the generated deep-copy helper for a rune deriving ``Imago``."""
        return f"_pengu_clone_{self._derived_type_c_name(u)}"
    def _rune_cleanup_helper(self, u: Type) -> str:
        """Name of the generated destructor for a rune deriving ``Nexus``."""
        return f"_pengu_cleanup_{self._derived_type_c_name(u)}"
    def generate_derived_implementations(self) -> str:
        """Generates automatic implementations for derived concepts (Par, Ordo, Vinculum, Imago, Nexus)."""
        forward_decls = []
        impl_blocks = []

        for rune_name, fields in self.runes.items():
            if rune_name in self.declaration_types:
                continue

            derived = []
            if self.symbols:
                r_sym = self.symbols.runes.get(rune_name) or self.symbols.monomorphized_types.get(rune_name)
                if r_sym and hasattr(r_sym, "derived_concepts"):
                    for dc in r_sym.derived_concepts:
                        if dc not in derived:
                            derived.append(dc)
                base_name = getattr(r_sym, "base_name", None) or (rune_name.split("_")[0] if "_" in rune_name else rune_name)
                base_sym = self.symbols.runes.get(base_name)
                if base_sym and hasattr(base_sym, "derived_concepts"):
                    for dc in base_sym.derived_concepts:
                        if dc not in derived:
                            derived.append(dc)
                for (t_name, c_name) in self.symbols.concept_bindings.keys():
                    if t_name in (rune_name, base_name) and c_name in ("Par", "Ordo", "Vinculum", "Imago", "Nexus"):
                        if c_name not in derived:
                            derived.append(c_name)

            # A rune only gets a deep copy or a destructor when the user asks
            # for one explicitly ('derive Imago' / 'derive Nexus', or a matching
            # 'bind').  Nothing is derived implicitly from heap-owning fields:
            # memory is managed manually, exactly like the fields of a C struct.
            if not derived:
                continue

            c_rune = rune_name

            # 1. Par (Equality: ==, !=)
            if "Par" in derived:
                forward_decls.append(f"static inline bool {c_rune}_eq(const {c_rune} *a, const {c_rune} *b);")
                forward_decls.append(f"static inline bool {c_rune}_Par(const {c_rune} *a, const {c_rune} *b);")
                forward_decls.append(f"static inline bool {c_rune}_eq_val({c_rune} a, {c_rune} b);")

                lines = [
                    f"static inline bool {c_rune}_eq(const {c_rune} *a, const {c_rune} *b) {{",
                    "  if (!a && !b) return true;",
                    "  if (!a || !b) return false;",
                ]
                for f_name, f_type in fields.items():
                    f_c = self._c_ident(f_name)
                    unwrapped_f = f_type
                    while isinstance(unwrapped_f, (AliasType, FrozenType, SealType)):
                        unwrapped_f = getattr(unwrapped_f, "target", None) or getattr(unwrapped_f, "underlying", None)
                    if isinstance(unwrapped_f, BaseType) and unwrapped_f.name == "string":
                        lines.append(f"  if (!pengu_string_equal(a->{f_c}, b->{f_c})) return false;")
                    elif isinstance(unwrapped_f, (BaseType, RefType, CVarArgsType)) or getattr(unwrapped_f, "is_numeric", lambda: False)() or getattr(unwrapped_f, "is_bool", lambda: False)():
                        lines.append(f"  if (!(a->{f_c} == b->{f_c})) return false;")
                    elif isinstance(unwrapped_f, RuneType):
                        lines.append(f"  if (!{unwrapped_f.name}_eq(&(a->{f_c}), &(b->{f_c}))) return false;")
                    elif isinstance(unwrapped_f, ArrayType) and unwrapped_f.size is not None:
                        lines.append(f"  for (int _i = 0; _i < {unwrapped_f.size}; ++_i) {{")
                        lines.append(f"    if (!(a->{f_c}[_i] == b->{f_c}[_i])) return false;")
                        lines.append("  }")
                    else:
                        lines.append(f"  if (memcmp(&(a->{f_c}), &(b->{f_c}), sizeof(a->{f_c})) != 0) return false;")
                lines.append("  return true;")
                lines.append("}")
                lines.append(f"static inline bool {c_rune}_Par(const {c_rune} *a, const {c_rune} *b) {{")
                lines.append(f"  return {c_rune}_eq(a, b);")
                lines.append("}")
                lines.append(f"static inline bool {c_rune}_eq_val({c_rune} a, {c_rune} b) {{")
                lines.append(f"  return {c_rune}_eq(&a, &b);")
                lines.append("}")
                impl_blocks.append("\n".join(lines))

            # 2. Ordo (Ordering: <, <=, >, >=)
            if "Ordo" in derived:
                forward_decls.append(f"static inline int {c_rune}_cmp(const {c_rune} *a, const {c_rune} *b);")
                forward_decls.append(f"static inline int {c_rune}_Ordo(const {c_rune} *a, const {c_rune} *b);")
                forward_decls.append(f"static inline int {c_rune}_cmp_val({c_rune} a, {c_rune} b);")

                lines = [
                    f"static inline int {c_rune}_cmp(const {c_rune} *a, const {c_rune} *b) {{",
                    "  if (!a && !b) return 0;",
                    "  if (!a) return -1;",
                    "  if (!b) return 1;",
                ]
                for f_name, f_type in fields.items():
                    f_c = self._c_ident(f_name)
                    unwrapped_f = f_type
                    while isinstance(unwrapped_f, (AliasType, FrozenType, SealType)):
                        unwrapped_f = getattr(unwrapped_f, "target", None) or getattr(unwrapped_f, "underlying", None)
                    if isinstance(unwrapped_f, BaseType) and unwrapped_f.name == "string":
                        lines.append(f"  {{ int _c = pengu_string_compare(a->{f_c}, b->{f_c}); if (_c != 0) return _c; }}")
                    elif isinstance(unwrapped_f, RuneType):
                        lines.append(f"  {{ int _c = {unwrapped_f.name}_cmp(&(a->{f_c}), &(b->{f_c})); if (_c != 0) return _c; }}")
                    else:
                        lines.append(f"  if (a->{f_c} < b->{f_c}) return -1;")
                        lines.append(f"  if (a->{f_c} > b->{f_c}) return 1;")
                lines.append("  return 0;")
                lines.append("}")
                lines.append(f"static inline int {c_rune}_Ordo(const {c_rune} *a, const {c_rune} *b) {{")
                lines.append(f"  return {c_rune}_cmp(a, b);")
                lines.append("}")
                lines.append(f"static inline int {c_rune}_cmp_val({c_rune} a, {c_rune} b) {{")
                lines.append(f"  return {c_rune}_cmp(&a, &b);")
                lines.append("}")
                impl_blocks.append("\n".join(lines))

            # 3. Vinculum (Hashing)
            if "Vinculum" in derived:
                forward_decls.append(f"static inline uint32_t {c_rune}_Vinculum(const {c_rune} *p);")
                forward_decls.append(f"static inline uint32_t {c_rune}_hash(const {c_rune} *p);")

                lines = [
                    f"static inline uint32_t {c_rune}_Vinculum(const {c_rune} *p) {{",
                    "  if (!p) return 0;",
                    "  uint32_t h = 2166136261u;",
                ]
                for f_name, f_type in fields.items():
                    f_c = self._c_ident(f_name)
                    unwrapped_f = f_type
                    while isinstance(unwrapped_f, (AliasType, FrozenType, SealType)):
                        unwrapped_f = getattr(unwrapped_f, "target", None) or getattr(unwrapped_f, "underlying", None)
                    if isinstance(unwrapped_f, BaseType) and unwrapped_f.name == "string":
                        lines.append(f"  h = ((p->{f_c}.data && p->{f_c}.len > 0) ? pengu_hash_bytes(p->{f_c}.data, (size_t)p->{f_c}.len) : 0) ^ (h * 16777619u);")
                    elif isinstance(unwrapped_f, RuneType):
                        lines.append(f"  h = {unwrapped_f.name}_Vinculum(&(p->{f_c})) ^ (h * 16777619u);")
                    else:
                        lines.append(f"  h = pengu_hash_bytes(&(p->{f_c}), sizeof(p->{f_c})) ^ (h * 16777619u);")
                lines.append("  return h;")
                lines.append("}")
                lines.append(f"static inline uint32_t {c_rune}_hash(const {c_rune} *p) {{")
                lines.append(f"  return {c_rune}_Vinculum(p);")
                lines.append("}")
                impl_blocks.append("\n".join(lines))

            # 4. Imago (Cloning) — only reachable through an explicit 'derive'.
            if "Imago" in derived:
                clone_fn = f"{c_rune}_clone"
                forward_decls.append(f"static inline void {c_rune}_clone(void *dst, const void *src);")
                forward_decls.append(f"static inline void _pengu_clone_{c_rune}(void *dst, const void *src);")

                lines = [
                    f"static inline void {clone_fn}(void *dst, const void *src) {{",
                    "  if (!dst || !src) return;",
                    f"  *({c_rune} *)dst = *(const {c_rune} *)src;",
                ]
                for f_name, f_type in fields.items():
                    f_c = self._c_ident(f_name)
                    # Shared with the algebraic-omen path: it understands nested
                    # containers, arrays and the insignia-prefixed C names.
                    stmt = self._derived_field_clone(
                        f"(({c_rune} *)dst)->{f_c}",
                        f"((const {c_rune} *)src)->{f_c}", f_type)
                    if stmt:
                        lines.append(f"  {stmt}")
                lines.append("}")
                lines.append(f"static inline void _pengu_clone_{c_rune}(void *dst, const void *src) {{")
                lines.append(f"  {c_rune}_clone(dst, src);")
                lines.append("}")
                impl_blocks.append("\n".join(lines))

            # 5. Nexus (Drop / Cleanup) — only through an explicit 'derive'.
            if "Nexus" in derived:
                body_fn = f"{c_rune}_nexus"
                forward_decls.append(f"static inline void {c_rune}_nexus(void *p);")
                forward_decls.append(f"static inline void _pengu_cleanup_{c_rune}(void *elem);")

                lines = [
                    f"static inline void {body_fn}(void *p) {{",
                    "  if (!p) return;",
                    f"  {c_rune} *pt = ({c_rune} *)p;",
                ]
                for f_name, f_type in fields.items():
                    f_c = self._c_ident(f_name)
                    stmt = self._derived_field_nexus(f"pt->{f_c}", f_type)
                    if stmt:
                        lines.append(f"  {stmt}")
                lines.append("}")
                lines.append(f"static inline void _pengu_cleanup_{c_rune}(void *elem) {{")
                lines.append(f"  {c_rune}_nexus(elem);")
                lines.append("}")
                impl_blocks.append("\n".join(lines))

        # ------------------------------------------------------------------
        # Omens: simple omens are C enums (trivial ops); algebraic omens are
        # tagged structs, so only the payload of the *active* tag is touched.
        # ------------------------------------------------------------------
        for omen_name, variants in list(self.omens.items()):
            if omen_name in self.declaration_types:
                continue
            is_algebraic = any(bool(v) for v in variants.values())
            is_string_valued = bool(
                omen_name in self.omen_values
                and any(isinstance(v, str) for v in self.omen_values[omen_name].values())
            )
            if is_string_valued:
                continue

            derived = []
            base_omen = omen_name.split("_")[0] if "_" in omen_name else omen_name
            if self.symbols:
                for key in (omen_name, base_omen):
                    o_sym = getattr(self.symbols, "omens", {}).get(key)
                    if o_sym is not None and hasattr(o_sym, "derived_concepts"):
                        for dc in o_sym.derived_concepts:
                            if dc not in derived:
                                derived.append(dc)
                for (t_name, c_name2) in self.symbols.concept_bindings.keys():
                    if t_name in (omen_name, base_omen) and c_name2 in ("Par", "Ordo", "Vinculum", "Imago", "Nexus"):
                        if c_name2 not in derived:
                            derived.append(c_name2)
            # As with runes, an omen only gets a deep copy or a destructor from
            # an explicit 'derive Imago' / 'derive Nexus'; the active variant of
            # an algebraic omen is otherwise released field by field by hand.
            if not derived:
                continue

            c_o = omen_name
            tag_of = {v: self._get_omen_variant_c_name(c_o, v) for v in variants}

            # 1. Par
            if "Par" in derived:
                forward_decls.append(f"static inline bool {c_o}_eq(const {c_o} *a, const {c_o} *b);")
                forward_decls.append(f"static inline bool {c_o}_Par(const {c_o} *a, const {c_o} *b);")
                forward_decls.append(f"static inline bool {c_o}_eq_val({c_o} a, {c_o} b);")
                lines = [
                    f"static inline bool {c_o}_eq(const {c_o} *a, const {c_o} *b) {{",
                    "  if (!a && !b) return true;",
                    "  if (!a || !b) return false;",
                ]
                if is_algebraic:
                    lines.append("  if (a->tag != b->tag) return false;")
                    lines.append("  switch (a->tag) {")
                    for v_name, v_fields in variants.items():
                        lines.append(f"    case {tag_of[v_name]}: {{")
                        for f_name, f_type in v_fields.items():
                            f_c = self._c_ident(f_name)
                            cond = self._derived_field_eq(
                                f"a->data.{self._c_ident(v_name)}.{f_c}",
                                f"b->data.{self._c_ident(v_name)}.{f_c}", f_type)
                            lines.append(f"      if (!({cond})) return false;")
                        lines.append("      break;")
                        lines.append("    }")
                    lines.append("    default: break;")
                    lines.append("  }")
                else:
                    lines.append("  return *a == *b;")
                lines.append("  return true;")
                lines.append("}")
                lines.append(f"static inline bool {c_o}_Par(const {c_o} *a, const {c_o} *b) {{")
                lines.append(f"  return {c_o}_eq(a, b);")
                lines.append("}")
                lines.append(f"static inline bool {c_o}_eq_val({c_o} a, {c_o} b) {{")
                lines.append(f"  return {c_o}_eq(&a, &b);")
                lines.append("}")
                impl_blocks.append("\n".join(lines))

            # 2. Ordo
            if "Ordo" in derived:
                forward_decls.append(f"static inline int {c_o}_cmp(const {c_o} *a, const {c_o} *b);")
                forward_decls.append(f"static inline int {c_o}_Ordo(const {c_o} *a, const {c_o} *b);")
                forward_decls.append(f"static inline int {c_o}_cmp_val({c_o} a, {c_o} b);")
                lines = [
                    f"static inline int {c_o}_cmp(const {c_o} *a, const {c_o} *b) {{",
                    "  if (!a && !b) return 0;",
                    "  if (!a) return -1;",
                    "  if (!b) return 1;",
                ]
                if is_algebraic:
                    lines.append("  if (a->tag < b->tag) return -1;")
                    lines.append("  if (a->tag > b->tag) return 1;")
                    lines.append("  switch (a->tag) {")
                    for v_name, v_fields in variants.items():
                        lines.append(f"    case {tag_of[v_name]}: {{")
                        for f_name, f_type in v_fields.items():
                            f_c = self._c_ident(f_name)
                            cmp_e = self._derived_field_cmp(
                                f"a->data.{self._c_ident(v_name)}.{f_c}",
                                f"b->data.{self._c_ident(v_name)}.{f_c}", f_type)
                            lines.append(f"      {{ int _c = {cmp_e}; if (_c != 0) return _c; }}")
                        lines.append("      break;")
                        lines.append("    }")
                    lines.append("    default: break;")
                    lines.append("  }")
                else:
                    lines.append("  if (*a < *b) return -1;")
                    lines.append("  if (*a > *b) return 1;")
                lines.append("  return 0;")
                lines.append("}")
                lines.append(f"static inline int {c_o}_Ordo(const {c_o} *a, const {c_o} *b) {{")
                lines.append(f"  return {c_o}_cmp(a, b);")
                lines.append("}")
                lines.append(f"static inline int {c_o}_cmp_val({c_o} a, {c_o} b) {{")
                lines.append(f"  return {c_o}_cmp(&a, &b);")
                lines.append("}")
                impl_blocks.append("\n".join(lines))

            # 3. Vinculum
            if "Vinculum" in derived:
                forward_decls.append(f"static inline uint32_t {c_o}_Vinculum(const {c_o} *p);")
                forward_decls.append(f"static inline uint32_t {c_o}_hash(const {c_o} *p);")
                lines = [
                    f"static inline uint32_t {c_o}_Vinculum(const {c_o} *p) {{",
                    "  if (!p) return 0;",
                ]
                if is_algebraic:
                    lines.append("  uint32_t h = 2166136261u;")
                    lines.append("  h = pengu_hash_bytes(&(p->tag), sizeof(p->tag)) ^ (h * 16777619u);")
                    lines.append("  switch (p->tag) {")
                    for v_name, v_fields in variants.items():
                        lines.append(f"    case {tag_of[v_name]}: {{")
                        for f_name, f_type in v_fields.items():
                            f_c = self._c_ident(f_name)
                            lines.append("      " + self._derived_field_hash(
                                f"p->data.{self._c_ident(v_name)}.{f_c}", f_type))
                        lines.append("      break;")
                        lines.append("    }")
                    lines.append("    default: break;")
                    lines.append("  }")
                    lines.append("  return h;")
                else:
                    lines.append("  return (uint32_t)(*p);")
                lines.append("}")
                lines.append(f"static inline uint32_t {c_o}_hash(const {c_o} *p) {{")
                lines.append(f"  return {c_o}_Vinculum(p);")
                lines.append("}")
                impl_blocks.append("\n".join(lines))

            # 4. Imago — explicit 'derive Imago' only.
            if "Imago" in derived:
                body_fn = f"{c_o}_clone"
                forward_decls.append(f"static inline void {c_o}_clone(void *dst, const void *src);")
                forward_decls.append(f"static inline void _pengu_clone_{c_o}(void *dst, const void *src);")
                lines = [
                    f"static inline void {body_fn}(void *dst, const void *src) {{",
                    "  if (!dst || !src) return;",
                    f"  *({c_o} *)dst = *(const {c_o} *)src;",
                ]
                if is_algebraic:
                    lines.append(f"  switch (((const {c_o} *)src)->tag) {{")
                    for v_name, v_fields in variants.items():
                        lines.append(f"    case {tag_of[v_name]}: {{")
                        for f_name, f_type in v_fields.items():
                            f_c = self._c_ident(f_name)
                            stmt = self._derived_field_clone(
                                f"(({c_o} *)dst)->data.{self._c_ident(v_name)}.{f_c}",
                                f"((const {c_o} *)src)->data.{self._c_ident(v_name)}.{f_c}", f_type)
                            if stmt:
                                lines.append(f"      {stmt}")
                        lines.append("      break;")
                        lines.append("    }")
                    lines.append("    default: break;")
                    lines.append("  }")
                lines.append("}")
                lines.append(f"static inline void _pengu_clone_{c_o}(void *dst, const void *src) {{")
                lines.append(f"  {c_o}_clone(dst, src);")
                lines.append("}")
                impl_blocks.append("\n".join(lines))

            # 5. Nexus — explicit 'derive Nexus' only.
            if "Nexus" in derived:
                body_fn = f"{c_o}_nexus"
                forward_decls.append(f"static inline void {c_o}_nexus(void *p);")
                forward_decls.append(f"static inline void _pengu_cleanup_{c_o}(void *elem);")
                lines = [
                    f"static inline void {body_fn}(void *p) {{",
                    "  if (!p) return;",
                ]
                if is_algebraic:
                    lines.append(f"  {c_o} *pt = ({c_o} *)p;")
                    lines.append("  switch (pt->tag) {")
                    for v_name, v_fields in variants.items():
                        lines.append(f"    case {tag_of[v_name]}: {{")
                        for f_name, f_type in v_fields.items():
                            f_c = self._c_ident(f_name)
                            stmt = self._derived_field_nexus(
                                f"pt->data.{self._c_ident(v_name)}.{f_c}", f_type)
                            if stmt:
                                lines.append(f"      {stmt}")
                        lines.append("      break;")
                        lines.append("    }")
                    lines.append("    default: break;")
                    lines.append("  }")
                lines.append("  (void)p;")
                lines.append("}")
                lines.append(f"static inline void _pengu_cleanup_{c_o}(void *elem) {{")
                lines.append(f"  {c_o}_nexus(elem);")
                lines.append("}")
                impl_blocks.append("\n".join(lines))

        if not forward_decls and not impl_blocks:
            return ""

        header = [
            "/* -------------------------------------------------------------------------",
            " * Derived Concept Implementations (Par, Ordo, Vinculum, Imago, Nexus)",
            " * ------------------------------------------------------------------------- */",
        ]
        return "\n".join(header) + "\n" + "\n".join(forward_decls) + "\n\n" + "\n\n".join(impl_blocks) + "\n"
    def _derived_field_eq(self, a_expr: str, b_expr: str, f_type: Type) -> str:
        """C condition that is true when the two field accesses compare equal."""
        u = self._derived_unwrap(f_type)
        if isinstance(u, BaseType) and u.name == "string":
            return f"pengu_string_equal({a_expr}, {b_expr})"
        if isinstance(u, RuneType):
            return f"{self._derived_type_c_name(u)}_eq(&({a_expr}), &({b_expr}))"
        if isinstance(u, OmenType) and u.is_algebraic:
            return f"{self._derived_type_c_name(u)}_eq(&({a_expr}), &({b_expr}))"
        if isinstance(u, OmenType):
            return f"({a_expr} == {b_expr})"
        return f"({a_expr} == {b_expr})"
    def _derived_field_cmp(self, a_expr: str, b_expr: str, f_type: Type) -> str:
        """C int expression ordering the two field accesses."""
        u = self._derived_unwrap(f_type)
        if isinstance(u, BaseType) and u.name == "string":
            return f"pengu_string_compare({a_expr}, {b_expr})"
        if isinstance(u, RuneType):
            return f"{self._derived_type_c_name(u)}_cmp(&({a_expr}), &({b_expr}))"
        if isinstance(u, OmenType) and u.is_algebraic:
            return f"{self._derived_type_c_name(u)}_cmp(&({a_expr}), &({b_expr}))"
        return f"(({a_expr} < {b_expr}) ? -1 : (({a_expr} > {b_expr}) ? 1 : 0))"
    def _derived_field_hash(self, acc_expr: str, f_type: Type) -> str:
        """C statement folding one field into the local 'uint32_t h' hash."""
        u = self._derived_unwrap(f_type)
        if isinstance(u, BaseType) and u.name == "string":
            return (f"h = (({acc_expr}.data && {acc_expr}.len > 0) ? "
                    f"pengu_hash_bytes({acc_expr}.data, (size_t){acc_expr}.len) : 0) ^ (h * 16777619u);")
        if isinstance(u, RuneType):
            return f"h = {self._derived_type_c_name(u)}_Vinculum(&({acc_expr})) ^ (h * 16777619u);"
        if isinstance(u, OmenType) and u.is_algebraic:
            return f"h = {self._derived_type_c_name(u)}_Vinculum(&({acc_expr})) ^ (h * 16777619u);"
        return f"h = pengu_hash_bytes(&({acc_expr}), sizeof({acc_expr})) ^ (h * 16777619u);"
    def _derived_field_clone(self, dst_expr: str, src_expr: str, f_type: Type) -> Optional[str]:
        """C statement deep-copying one field, or None when a plain copy suffices.

        Only reachable from an explicit ``derive Imago``: the user asked for a
        real copy, so strings are duplicated with ``pengu_string_copy`` and
        containers are rebuilt element by element (the runtime itself never
        clones on store).
        """
        u = self._derived_unwrap(f_type)
        if isinstance(u, BaseType) and u.name == "string":
            return f"{dst_expr} = pengu_string_copy({src_expr});"
        if isinstance(u, ListType):
            return self._clone_list_stmts(dst_expr, src_expr, u)
        if isinstance(u, MapType):
            return self._clone_map_stmts(dst_expr, src_expr, u)
        if isinstance(u, RuneType):
            if not self._type_owns_heap(u):
                return None  # POD rune: the whole-struct copy is enough
            return f"{self._rune_clone_helper(u)}(&({dst_expr}), &({src_expr}));"
        if isinstance(u, OmenType) and u.is_algebraic:
            return f"{self._rune_clone_helper(u)}(&({dst_expr}), &({src_expr}));"
        if isinstance(u, (MaybeType, ResultType)):
            return self._clone_box_stmts(dst_expr, src_expr, u)
        if isinstance(u, ArrayType) and u.size is not None:
            idx = self.get_temp_name("_ai")
            elem_stmt = self._derived_field_clone(
                f"{dst_expr}[{idx}]", f"{src_expr}[{idx}]", u.element)
            if elem_stmt is None:
                return None  # POD elements: the whole-array copy is enough
            return f"for (size_t {idx} = 0; {idx} < {u.size}; ++{idx}) {{ {elem_stmt} }}"
        return None
    def _clone_list_stmts(self, dst_expr: str, src_expr: str, u: ListType) -> str:
        """Rebuilds a ``list of T`` with its own buffer for an explicit Imago."""
        elem_c = CTypeMapper.to_c_type(u.element)
        tag = self.get_temp_name("_cl")
        dst_v, src_v = f"{tag}_dst", f"{tag}_src"
        elem_stmt = self._derived_field_clone(f"*{dst_v}", f"*{src_v}", u.element)
        head = f"{{ PenguList {tag}_d = pengu_list_new(sizeof({elem_c}), (size_t)({src_expr}).len);"
        if elem_stmt is None:
            # POD elements: one byte copy of the whole buffer is a deep copy.
            return (f"{head}\n"
                    f"    memcpy({tag}_d.data, ({src_expr}).data, (size_t)({src_expr}).len * sizeof({elem_c}));\n"
                    f"    {tag}_d.len = ({src_expr}).len; {dst_expr} = {tag}_d; }}")
        return (f"{head}\n"
                f"    for (int {tag}_i = 0; {tag}_i < ({src_expr}).len; ++{tag}_i) {{\n"
                f"      {elem_c} {tag}_e = {{0}};\n"
                f"      {elem_c} *{dst_v} = &{tag}_e;\n"
                f"      const {elem_c} *{src_v} = &((const {elem_c} *)({src_expr}).data)[{tag}_i];\n"
                f"      (void){dst_v}; (void){src_v}; {elem_stmt}\n"
                f"      pengu_list_push(&{tag}_d, &{tag}_e); }}\n"
                f"    {dst_expr} = {tag}_d; }}")
    def _clone_map_stmts(self, dst_expr: str, src_expr: str, u: MapType) -> str:
        """Rebuilds a ``map of K to V`` with its own entries for an explicit Imago."""
        key_c = CTypeMapper.to_c_type(u.key)
        val_c = CTypeMapper.to_c_type(u.value)
        tag = self.get_temp_name("_cm")
        kd, ks = f"{tag}_kdst", f"{tag}_ksrc"
        vd, vs = f"{tag}_vdst", f"{tag}_vsrc"
        key_stmt = self._derived_field_clone(f"*{kd}", f"*{ks}", u.key)
        val_stmt = self._derived_field_clone(f"*{vd}", f"*{vs}", u.value)
        lines = [f"{{ PenguMap {tag}_d = pengu_map_new(sizeof({key_c}), sizeof({val_c}));",
                 f"    for (int {tag}_i = 0; {tag}_i < ({src_expr}).cap; ++{tag}_i) {{",
                 f"      const PenguMapEntry *{tag}_s = &({src_expr}).entries[{tag}_i];",
                 f"      if (!{tag}_s->occupied) continue;",
                 f"      {key_c} {tag}_k = {{0}};",
                 f"      {val_c} {tag}_v = {{0}};"]
        if key_stmt is not None:
            lines.append(f"      {key_c} *{kd} = &{tag}_k;"
                         f" const {key_c} *{ks} = (const {key_c} *){tag}_s->key;"
                         f" (void){kd}; (void){ks}; {key_stmt}")
        else:
            lines.append(f"      memcpy(&{tag}_k, {tag}_s->key, sizeof({key_c}));")
        if val_stmt is not None:
            lines.append(f"      {val_c} *{vd} = &{tag}_v;"
                         f" const {val_c} *{vs} = (const {val_c} *){tag}_s->val;"
                         f" (void){vd}; (void){vs}; {val_stmt}")
        else:
            lines.append(f"      memcpy(&{tag}_v, {tag}_s->val, sizeof({val_c}));")
        lines.append(f"      pengu_map_put(&{tag}_d, &{tag}_k, &{tag}_v);")
        lines.append("    }")
        lines.append(f"    {dst_expr} = {tag}_d; }}")
        return "\n".join(lines)
    def _clone_box_stmts(self, dst_expr: str, src_expr: str, u: Type) -> Optional[str]:
        """Deep-copies a ``maybe``/``result`` box for an explicit Imago."""
        tag = self.get_temp_name("_cb")
        if isinstance(u, MaybeType):
            elem_c = CTypeMapper.to_c_type(u.element)
            inner = self._derived_field_clone(
                "*(" + elem_c + " *)" + tag + "_d.value",
                "*(const " + elem_c + " *)(" + src_expr + ").value",
                u.element)
            if inner is None:
                # POD payload: copying the box plus its bytes is a deep copy.
                return (
                    "if ((" + src_expr + ").is_present && (" + src_expr + ").value) {\n"
                    "  PenguMaybe " + tag + "_d = (" + src_expr + ");\n"
                    "  " + tag + "_d.value = pengu_sigil_alloc(sizeof(" + elem_c + "));\n"
                    "  if (" + tag + "_d.value) memcpy(" + tag + "_d.value, (" + src_expr + ").value, sizeof(" + elem_c + "));\n"
                    "  else " + tag + "_d.is_present = false;\n"
                    "  " + dst_expr + " = " + tag + "_d;\n"
                    "}"
                )
            return (
                "if ((" + src_expr + ").is_present && (" + src_expr + ").value) {\n"
                "  PenguMaybe " + tag + "_d = (" + src_expr + ");\n"
                "  " + tag + "_d.value = pengu_sigil_alloc(sizeof(" + elem_c + "));\n"
                "  if (" + tag + "_d.value) {\n"
                "    " + inner + "\n"
                "  } else { " + tag + "_d.is_present = false; }\n"
                "  " + dst_expr + " = " + tag + "_d;\n"
                "}"
            )
        if isinstance(u, ResultType):
            ok_c = CTypeMapper.to_c_type(u.ok_type)
            err_c = CTypeMapper.to_c_type(u.err_type)
            ok_inner = self._derived_field_clone(
                "*(" + ok_c + " *)" + tag + "_d.ok_val",
                "*(const " + ok_c + " *)(" + src_expr + ").ok_val",
                u.ok_type)
            err_inner = self._derived_field_clone(
                "*(" + err_c + " *)" + tag + "_d.err_val",
                "*(const " + err_c + " *)(" + src_expr + ").err_val",
                u.err_type)
            parts = [
                "PenguResult " + tag + "_d = (" + src_expr + ");",
                tag + "_d.ok_val = NULL; " + tag + "_d.err_val = NULL;",
            ]
            if ok_inner is not None:
                parts.append(
                    "if (" + src_expr + ".is_ok && " + src_expr + ".ok_val) {"
                    " " + tag + "_d.ok_val = pengu_sigil_alloc(sizeof(" + ok_c + "));"
                    " if (" + tag + "_d.ok_val) { " + ok_inner + " }"
                    " else { " + tag + "_d.is_ok = false; } }")
            if err_inner is not None:
                parts.append(
                    "if (!" + src_expr + ".is_ok && " + src_expr + ".err_val) {"
                    " " + tag + "_d.err_val = pengu_sigil_alloc(sizeof(" + err_c + "));"
                    " if (" + tag + "_d.err_val) { " + err_inner + " }"
                    " else { " + tag + "_d.is_ok = true; } }")
            parts.append(dst_expr + " = " + tag + "_d;")
            return "{ " + "\n  ".join(parts) + " }"
        return None
    def _derived_field_nexus(self, acc_expr: str, f_type: Type) -> Optional[str]:
        """C statement releasing one field, or None when there is nothing to free."""
        u = self._derived_unwrap(f_type)
        if isinstance(u, BaseType) and u.name == "string":
            return f"pengu_banish_string(&({acc_expr}));"
        if isinstance(u, ListType):
            return f"pengu_banish_list(&({acc_expr}));"
        if isinstance(u, MapType):
            return f"pengu_banish_map(&({acc_expr}));"
        if isinstance(u, RuneType):
            if not self._type_owns_heap(u):
                return None  # POD rune: nothing to release
            return f"{self._rune_cleanup_helper(u)}(&({acc_expr}));"
        if isinstance(u, OmenType) and u.is_algebraic:
            return f"{self._rune_cleanup_helper(u)}(&({acc_expr}));"
        if isinstance(u, (MaybeType, ResultType)):
            return self._release_payload_stmts(u, f"&({acc_expr})")
        if isinstance(u, ArrayType) and u.size is not None:
            idx = self.get_temp_name("_ai")
            elem_stmt = self._derived_field_nexus(f"{acc_expr}[{idx}]", u.element)
            if elem_stmt is None:
                return None
            return f"for (size_t {idx} = 0; {idx} < {u.size}; ++{idx}) {{ {elem_stmt} }}"
        return None
