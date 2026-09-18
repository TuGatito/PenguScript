Actualmente Github Actions no puede terminar los procesos para subir el artefacto de linux, mac y windows ya que no pasan los tests.

Asegurate de saber si es error del test, que es antiguo, o si es un error real del compilador. Luego solucionalos para que los tests pasen y Github Actions pueda terminar satisfactoriamente.

Asegurate de no romper nada en el proceso.

Mac:

Run python -m pytest tests -q -p no:cacheprovider
........................................................................ [ 7%]
...............FF............F.............F.......F.................... [ 14%]
........F............................................................... [ 21%]
........................................................F....F.......... [ 28%]
...F.F..........................................................F....... [ 35%]
........................................................................ [ 42%]
.............................................................s..ss...... [ 49%]
........................................................................ [ 56%]
........................................................................ [ 63%]
......................................s..............................s.. [ 70%]
..................s.....................s.s............................. [ 77%]
........................................................................ [ 85%]
........................................................................ [ 92%]
...................s.................................................... [ 99%]
........ [100%]
=================================== FAILURES ===================================
******\_\_\_\_****** TestStructFieldAccess.test_valid_field_access ********\_********

self = <tests.test_compiler_core.TestStructFieldAccess object at 0x107c08190>

    def test_valid_field_access(self):

>       check_ok(

            VEC2
            + "weave main into float:\n  let v as Vec2 is with x is 10, y is 20\n  return v.x + v.y\n"
        )

tests/test_compiler_core.py:383:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b45d4f0>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'rune_d..., Token('NAME', 'x')]), Tree('field_access', [Tree('var_ref', [Token('NAME', 'v')]), Token('NAME', 'y')])])])])])])])])
source = 'rune Vec2:\n x as float\n y as float\nweave main into float:\n let v as Vec2 is with x is 10, y is 20\n return v.x + v.y\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'

pengu_parser/pengu_checker.py:329: SemanticError
******\_\_\_\_****** TestStructFieldAccess.test_unknown_field_fails ******\_\_\_\_******

self = <tests.test_compiler_core.TestStructFieldAccess object at 0x107c082d0>

    def test_unknown_field_fails(self):

>       expect_error(

            VEC2
            + "weave main into float:\n  let v as Vec2 is with x is 10, y is 20\n  return v.z\n",
            contains=["E0013", "has no field 'z'"],
        )

tests/test_compiler_core.py:389:

---

source = 'rune Vec2:\n x as float\n y as float\nweave main into float:\n let v as Vec2 is with x is 10, y is 20\n return v.z\n'
filename = 't.pengu', contains = ['E0013', "has no field 'z'"]

    def expect_error(source, filename="t.pengu", contains=None):
        """Assert ``source`` fails to compile; return the error text.

        ``contains`` may be a substring (or a list of substrings) of the message;
        an error code such as ``E0001`` is also accepted (codes are stored on the
        raised error, not in its message).

        Note: ``tests.conftest.check_error`` currently raises NameError (it refers
        to an undefined ``base_dir``), so this module carries its own equivalent.
        """
        tree = PenguParser().parse(source)
        checker = PenguChecker(base_dir=".")
        try:
            checker.check(tree, source=source, filename=filename)
        except PenguError as exc:
            text = str(exc)
            codes = [e.code for e in getattr(exc, "all_errors", [])] + [exc.code]
        except Exception as exc:  # noqa: BLE001 - keep whatever error was raised
            text = str(exc)
            codes = []
        else:
            raise AssertionError("expected a compile error but the source is clean")
        if contains is not None:
            wanted = [contains] if isinstance(contains, str) else contains
            for w in wanted:
                if w in text or w in codes:
                    continue

>               raise AssertionError(

                    f"error {text!r} (codes {codes}) does not mention {w!r}"
                )

E AssertionError: error "[line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'" (codes ['E0020', 'E0013', 'E0020']) does not mention "has no field 'z'"

tests/test_compiler_core.py:81: AssertionError
******\_\_\_****** TestEchoOmenSemantics.test_simple_enum_variants ******\_\_\_\_******

self = <tests.test_compiler_core.TestEchoOmenSemantics object at 0x10882aad0>

        def test_simple_enum_variants(self):

>           check_ok(

                """omen Level:
      ONE
      TWO
      THREE

    weave main into string:
      var l1 as Level is Level_ONE
      var l2 as Level is Level.TWO
      var l3 as Level is THREE
      let res is judge l2:
        when Level_ONE -> "1"
        when Level.TWO -> "2"
        when THREE -> "3"
        else -> "other"
      return res
    """
            )

tests/test_compiler_core.py:499:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b45f540>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'omen_d...), Tree(Token('RULE', 'stmt'), [Tree(Token('RULE', 'return_stmt'), [Tree('var_ref', [Token('NAME', 'res')])])])])])])])
source = 'omen Level:\n ONE\n TWO\n THREE\n\nweave main into string:\n var l1 as Level is Level_ONE\n var l2 as Level is L... l2:\n when Level_ONE -> "1"\n when Level.TWO -> "2"\n when THREE -> "3"\n else -> "other"\n return res\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 6, col 1] Entry point 'main' must return an integer or 'void', got 'string'

pengu*parser/pengu_checker.py:329: SemanticError
* TestCollectionsSemantics.test*array_slice_list_map_ops[weave main into void:\n let arr is array of int with size 10\n let first is arr at 0\n set arr at 0 is 99\n let part as slice of int is arr at 1 to 3\n let n is part length\n var l as list of int is list of int with capacity 10\n var m as map of int to string is map of int to string\n] *

self = <tests.test_compiler_core.TestCollectionsSemantics object at 0x107c08f50>
source = 'weave main into void:\n let arr is array of int with size 10\n let first is arr at 0\n set arr at 0 is 99\n let p...gth\n var l as list of int is list of int with capacity 10\n var m as map of int to string is map of int to string\n'

    @pytest.mark.parametrize(
        "source",
        [
            "weave main into int:\n"
            "  let arr is array of int with size 10\n"
            "  let first is arr at 0\n"
            "  let slice_part is arr at 1 to 4\n"
            "  let length_val is arr length\n"
            "  return first\n",
            "weave main into void:\n"
            "  let arr is array of int with size 10\n"
            "  let first is arr at 0\n"
            "  set arr at 0 is 99\n"
            "  let part as slice of int is arr at 1 to 3\n"
            "  let n is part length\n"
            "  var l as list of int is list of int with capacity 10\n"
            "  var m as map of int to string is map of int to string\n",
        ],
    )
    def test_array_slice_list_map_ops(self, source):

>       check_ok(source)

tests/test_compiler_core.py:701:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)
pengu_parser/pengu_checker.py:329: in check
raise first_err

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b4b9390>
node = Tree(Token('RULE', 'set_stmt'), [Tree(Token('RULE', 'set_target'), [Tree(Token('RULE', 'normal_target'), [Token('NAME', 'arr'), Tree('at_access', [Tree('int_lit', [Token('INT', '0')])])])]), Tree('int_lit', [Token('INT', '99')])])

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                while isinstance(with_t, RefType):
                    with_t = with_t.target
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (ArrayType, SliceType, ManyType, ListType)):
                                target_type = curr_t.element

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"

>                               raise self._make_error(

                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )

E pengu_parser.pengu_errors.MutabilityError: [line 4, col 7] Cannot mutate element of immutable 'let' variable 'arr'

pengu_parser/pengu_checker.py:3342: MutabilityError
******\_\_****** TestMaybeResultOrError.test_maybe_decl_and_unwrap ******\_\_\_******

self = <tests.test_compiler_core.TestMaybeResultOrError object at 0x107c09310>

        def test_maybe_decl_and_unwrap(self):

>           check_ok(

                """rune User:
      name as string

    weave main into string:
      let u as maybe User is maybe none
      let guest as string is "guest"
      let u2 as maybe string is maybe none
      let result is u2 or else guest
      return result
    """
            )

tests/test_compiler_core.py:770:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b46da70>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'rune_d...Tree(Token('RULE', 'stmt'), [Tree(Token('RULE', 'return_stmt'), [Tree('var_ref', [Token('NAME', 'result')])])])])])])])
source = 'rune User:\n name as string\n\nweave main into string:\n let u as maybe User is maybe none\n let guest as string is "guest"\n let u2 as maybe string is maybe none\n let result is u2 or else guest\n return result\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'string'

pengu*parser/pengu_checker.py:329: SemanticError
* TestEnchantingSemantics.test*enchanting_methods_check[rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with x is self->x + other.x, y is self->y + other.y\n\n weave length into float:\n (self->x * self->x + self->y * self->y) to float\n\n weave move with dx as float, dy as float into void:\n set self->x is self->x + dx\n set self->y is self->y + dy\n\nweave main into void:\n let a as Vec2 is with x is 10, y is 20\n let b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n] *

self = <tests.test_compiler_core.TestEnchantingSemantics object at 0x107c09bd0>
source = 'rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with...b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n'

        @pytest.mark.parametrize(
            "source",
            [
                VEC2
                + """enchanting Vec2:
      weave add with other as Vec2 into void:
        set self->x is self->x + other.x
        set self->y is self->y + other.y
    """,
                VEC2
                + """enchanting Vec2:
      weave add with other as Vec2 into Vec2:
        Vec2 is with x is self->x + other.x, y is self->y + other.y

      weave length into float:
        (self->x * self->x + self->y * self->y) to float

      weave move with dx as float, dy as float into void:
        set self->x is self->x + dx
        set self->y is self->y + dy

    weave main into void:
      let a as Vec2 is with x is 10, y is 20
      let b as Vec2 is with x is 5, y is 5
      let c is calling a.add with b
      var d as Vec2 is a
      calling d.move with 10, 0
    """,
            ],
        )
        def test_enchanting_methods_check(self, source):

>           check_ok(source)

tests/test_compiler_core.py:1149:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:86: in check
tree = parser.parse(source)
^^^^^^^^^^^^^^^^^^^^

---

self = <pengu_parser.pengu_parser.PenguParser object at 0x109862490>
code = 'rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with...b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n'

    def parse(self, code: str) -> Tree:
        """Parses PenguScript source code into a Lark AST Tree.

        Args:
            code: PenguScript source text.

        Returns:
            Lark AST Tree root.

        Raises:
            ParseError: when the source is not valid PenguScript (Lark's syntax
                exceptions are converted, with a hint when the removed 0.10.0
                'and' separator is the likely cause).
        """
        code = strip_bom(code)
        clean_code = self._strip_comments(code).rstrip() + '\n'
        try:
            return self.parser.parse(clean_code, start='start')
        except LarkUnexpectedInput as exc:

>           raise self._parse_error(code, exc) from None
>
> E pengu_parser.pengu_errors.ParseError: [line 6, col 13] Syntax error: unexpected 'with' at line 6, column 13

pengu_parser/pengu_parser.py:143: ParseError
******\_\_\_****** TestDestructuring.test_rune_destructuring_valid ******\_\_\_\_******

self = <tests.test_compiler_core.TestDestructuring object at 0x107c0ccd0>

    def test_rune_destructuring_valid(self):

>       check_ok(

            VEC2
            + "weave main into float:\n  let v as Vec2 is with x is 1.0, y is 2.0\n  let px, py is v\n  return px + py\n"
        )

tests/test_compiler_core.py:2651:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b4966d0>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'rune_d...turn_stmt'), [Tree('add', [Tree('var_ref', [Token('NAME', 'px')]), Tree('var_ref', [Token('NAME', 'py')])])])])])])])])
source = 'rune Vec2:\n x as float\n y as float\nweave main into float:\n let v as Vec2 is with x is 1.0, y is 2.0\n let px, py is v\n return px + py\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'

pengu_parser/pengu_checker.py:329: SemanticError
**\_\_** TestStringInterpolation.test_interpolation_format_string_emission **\_\_\_**

self = <tests.test_compiler_core.TestStringInterpolation object at 0x107c78640>

    def test_interpolation_format_string_emission(self):
        c = gen_bundle(
            'weave main into void:\n'
            '  let name is "player1"\n'
            '  let x is 10\n'
            '  let msg is "player {name} at {x}"\n'
        )

>       assert 'pengu_string_format("player %s at %d"' in c
>
> E assert 'pengu_string_format("player %s at %d"' in '/_ Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...t_args()\' etc. _/\n pengu_init(argc, argv);\n pengu_main();\n fflush(stdout);\n fflush(stderr);\n return 0;\n}\n'

tests/test_compiler_core.py:2694: AssertionError
**\_\_\_** TestCodegenEmissionArraysSlices.test_collection_emission_shapes **\_\_\_\_**

self = <tests.test_compiler_core.TestCodegenEmissionArraysSlices object at 0x107c0dbd0>

        def test_collection_emission_shapes(self):

>           c = gen_bundle(

                VEC2
                + """weave test_collections into void:
      let arr is array of int with size 10
      let first is arr at 0
      set arr at 0 is 99
      let part as slice of int is arr at 1 to 3
      let n is part length
      let evens is for x in arr when x % 2 == 0 then x
      let doubled is for x in arr then x * 2
      var vertices as list of Vec2 is list of Vec2 with capacity 100
      var lookup as map of int to Vec2 is map of int to Vec2
    """
            )

tests/test_compiler_core.py:2957:

---

tests/conftest.py:147: in gen_bundle
checker.check(tree, source=code, filename=fname)
pengu_parser/pengu_checker.py:329: in check
raise first_err

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b4485d0>
node = Tree(Token('RULE', 'set_stmt'), [Tree(Token('RULE', 'set_target'), [Tree(Token('RULE', 'normal_target'), [Token('NAME', 'arr'), Tree('at_access', [Tree('int_lit', [Token('INT', '0')])])])]), Tree('int_lit', [Token('INT', '99')])])

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                while isinstance(with_t, RefType):
                    with_t = with_t.target
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (ArrayType, SliceType, ManyType, ListType)):
                                target_type = curr_t.element

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"

>                               raise self._make_error(

                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )

E pengu_parser.pengu_errors.MutabilityError: [line 7, col 7] Cannot mutate element of immutable 'let' variable 'arr'

pengu_parser/pengu_checker.py:3342: MutabilityError
****\_**** TestCodegenEmissionArraysSlices.test_loop_and_index_emission ****\_****

self = <tests.test_compiler_core.TestCodegenEmissionArraysSlices object at 0x107c78e90>

        def test_loop_and_index_emission(self):

>           c = gen_bundle(

                """weave loops_demo into void:
      var x as int is 0
      while x < 10:
        set x is x + 1
        if x == 5:
          continue
        if x == 9:
          break

      var arr as array of int with size 5 is [1, 2, 3, 4, 5]
      for i from 0 to 5:
        set arr at i is (arr at i) * 2

      let part as slice of int is arr at 1 to 4
      for i from 0 to part.len:
        set part at i is (part at i) + 10

      for num in arr:
        let doubled is num * 2

      var lst as list of int is list of int with capacity 10
      for i from 0 to 5:
        calling lst.push with i * 10
      for i from 0 to lst.len:
        set lst at i is (lst at i) + 100
    """
            )

tests/test_compiler_core.py:2989:

---

tests/conftest.py:147: in gen_bundle
checker.check(tree, source=code, filename=fname)
pengu_parser/pengu_checker.py:329: in check
raise first_err

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b4494f0>
node = Tree(Token('RULE', 'set_stmt'), [Tree(Token('RULE', 'set_target'), [Tree(Token('RULE', 'normal_target'), [Token('NAME'...ar_ref', [Token('NAME', 'part')]), Tree('var_ref', [Token('NAME', 'i')])])]), Tree('int_lit', [Token('INT', '10')])])])

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                while isinstance(with_t, RefType):
                    with_t = with_t.target
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (ArrayType, SliceType, ManyType, ListType)):
                                target_type = curr_t.element

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"

>                               raise self._make_error(

                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )

E pengu_parser.pengu_errors.MutabilityError: [line 16, col 9] Cannot mutate element of immutable 'let' variable 'part'

pengu_parser/pengu_checker.py:3342: MutabilityError
********\_\_******** TestIndexedFor.test_indexed_for_over_list ********\_\_\_********

self = <tests.test_compiler_features.TestIndexedFor object at 0x107c199d0>

        def test_indexed_for_over_list(self):
            code = """weave test_for with nums as list of int into void:
      var acc as int is 0
      for i, v in nums:
        set acc is acc + i * v
    """
            c = gen_bundle(code)
            assert "for (int32_t i = 0; i < (nums).len; i++) {" in c

>           assert "int32_t v = (*(int32_t*)pengu_list_at(&(nums), i));" in c
>
> E assert 'int32_t v = (_(int32_t_)pengu_list_at(&(nums), i));' in '/_ Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...sers/runner/work/PenguScript/PenguScript/t.pengu"\n acc = (acc + (i _ v));\n }\n pengu_frame_pop();\n}\n\n#line 1'

tests/test_compiler_features.py:425: AssertionError
=========================== short test summary info ============================
FAILED tests/test_compiler_core.py::TestStructFieldAccess::test_valid_field_access - pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'
FAILED tests/test_compiler_core.py::TestStructFieldAccess::test_unknown_field_fails - AssertionError: error "[line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'" (codes ['E0020', 'E0013', 'E0020']) does not mention "has no field 'z'"
FAILED tests/test_compiler_core.py::TestEchoOmenSemantics::test_simple_enum_variants - pengu_parser.pengu_errors.SemanticError: [line 6, col 1] Entry point 'main' must return an integer or 'void', got 'string'
FAILED tests/test_compiler_core.py::TestCollectionsSemantics::test_array_slice_list_map_ops[weave main into void:\n let arr is array of int with size 10\n let first is arr at 0\n set arr at 0 is 99\n let part as slice of int is arr at 1 to 3\n let n is part length\n var l as list of int is list of int with capacity 10\n var m as map of int to string is map of int to string\n] - pengu_parser.pengu_errors.MutabilityError: [line 4, col 7] Cannot mutate element of immutable 'let' variable 'arr'
FAILED tests/test_compiler_core.py::TestMaybeResultOrError::test_maybe_decl_and_unwrap - pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'string'
FAILED tests/test_compiler_core.py::TestEnchantingSemantics::test_enchanting_methods_check[rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with x is self->x + other.x, y is self->y + other.y\n\n weave length into float:\n (self->x * self->x + self->y * self->y) to float\n\n weave move with dx as float, dy as float into void:\n set self->x is self->x + dx\n set self->y is self->y + dy\n\nweave main into void:\n let a as Vec2 is with x is 10, y is 20\n let b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n] - pengu_parser.pengu_errors.ParseError: [line 6, col 13] Syntax error: unexpected 'with' at line 6, column 13
FAILED tests/test_compiler_core.py::TestDestructuring::test_rune_destructuring_valid - pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'
FAILED tests/test_compiler_core.py::TestStringInterpolation::test_interpolation_format_string_emission - assert 'pengu_string_format("player %s at %d"' in '/_ Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...t_args()\' etc. _/\n pengu_init(argc, argv);\n pengu_main();\n fflush(stdout);\n fflush(stderr);\n return 0;\n}\n'
FAILED tests/test_compiler_core.py::TestCodegenEmissionArraysSlices::test_collection_emission_shapes - pengu_parser.pengu_errors.MutabilityError: [line 7, col 7] Cannot mutate element of immutable 'let' variable 'arr'
FAILED tests/test_compiler_core.py::TestCodegenEmissionArraysSlices::test_loop_and_index_emission - pengu_parser.pengu_errors.MutabilityError: [line 16, col 9] Cannot mutate element of immutable 'let' variable 'part'
FAILED tests/test_compiler_features.py::TestIndexedFor::test_indexed_for_over_list - assert 'int32_t v = (_(int32_t_)pengu_list_at(&(nums), i));' in '/_ Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...sers/runner/work/PenguScript/PenguScript/t.pengu"\n acc = (acc + (i _ v));\n }\n pengu_frame_pop();\n}\n\n#line 1'
11 failed, 996 passed, 9 skipped in 111.84s (0:01:51)
Error: Process completed with exit code 1.

mac:

Run python -m pytest tests -q -p no:cacheprovider
........................................................................ [ 7%]
...............FF............F.............F.......F.................... [ 14%]
........F............................................................... [ 21%]
........................................................F....F.......... [ 28%]
...F.F..........................................................F....... [ 35%]
........................................................................ [ 42%]
.............................................................s..ss...... [ 49%]
........................................................................ [ 56%]
........................................................................ [ 63%]
......................................s..............................s.. [ 70%]
..................s.....................s.s............................. [ 77%]
........................................................................ [ 85%]
........................................................................ [ 92%]
...................s.................................................... [ 99%]
........ [100%]
=================================== FAILURES ===================================
******\_\_\_\_****** TestStructFieldAccess.test_valid_field_access ********\_********

self = <tests.test_compiler_core.TestStructFieldAccess object at 0x107c08190>

    def test_valid_field_access(self):

>       check_ok(

            VEC2
            + "weave main into float:\n  let v as Vec2 is with x is 10, y is 20\n  return v.x + v.y\n"
        )

tests/test_compiler_core.py:383:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b45d4f0>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'rune_d..., Token('NAME', 'x')]), Tree('field_access', [Tree('var_ref', [Token('NAME', 'v')]), Token('NAME', 'y')])])])])])])])])
source = 'rune Vec2:\n x as float\n y as float\nweave main into float:\n let v as Vec2 is with x is 10, y is 20\n return v.x + v.y\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'

pengu_parser/pengu_checker.py:329: SemanticError
******\_\_\_\_****** TestStructFieldAccess.test_unknown_field_fails ******\_\_\_\_******

self = <tests.test_compiler_core.TestStructFieldAccess object at 0x107c082d0>

    def test_unknown_field_fails(self):

>       expect_error(

            VEC2
            + "weave main into float:\n  let v as Vec2 is with x is 10, y is 20\n  return v.z\n",
            contains=["E0013", "has no field 'z'"],
        )

tests/test_compiler_core.py:389:

---

source = 'rune Vec2:\n x as float\n y as float\nweave main into float:\n let v as Vec2 is with x is 10, y is 20\n return v.z\n'
filename = 't.pengu', contains = ['E0013', "has no field 'z'"]

    def expect_error(source, filename="t.pengu", contains=None):
        """Assert ``source`` fails to compile; return the error text.

        ``contains`` may be a substring (or a list of substrings) of the message;
        an error code such as ``E0001`` is also accepted (codes are stored on the
        raised error, not in its message).

        Note: ``tests.conftest.check_error`` currently raises NameError (it refers
        to an undefined ``base_dir``), so this module carries its own equivalent.
        """
        tree = PenguParser().parse(source)
        checker = PenguChecker(base_dir=".")
        try:
            checker.check(tree, source=source, filename=filename)
        except PenguError as exc:
            text = str(exc)
            codes = [e.code for e in getattr(exc, "all_errors", [])] + [exc.code]
        except Exception as exc:  # noqa: BLE001 - keep whatever error was raised
            text = str(exc)
            codes = []
        else:
            raise AssertionError("expected a compile error but the source is clean")
        if contains is not None:
            wanted = [contains] if isinstance(contains, str) else contains
            for w in wanted:
                if w in text or w in codes:
                    continue

>               raise AssertionError(

                    f"error {text!r} (codes {codes}) does not mention {w!r}"
                )

E AssertionError: error "[line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'" (codes ['E0020', 'E0013', 'E0020']) does not mention "has no field 'z'"

tests/test_compiler_core.py:81: AssertionError
******\_\_\_****** TestEchoOmenSemantics.test_simple_enum_variants ******\_\_\_\_******

self = <tests.test_compiler_core.TestEchoOmenSemantics object at 0x10882aad0>

        def test_simple_enum_variants(self):

>           check_ok(

                """omen Level:
      ONE
      TWO
      THREE

    weave main into string:
      var l1 as Level is Level_ONE
      var l2 as Level is Level.TWO
      var l3 as Level is THREE
      let res is judge l2:
        when Level_ONE -> "1"
        when Level.TWO -> "2"
        when THREE -> "3"
        else -> "other"
      return res
    """
            )

tests/test_compiler_core.py:499:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b45f540>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'omen_d...), Tree(Token('RULE', 'stmt'), [Tree(Token('RULE', 'return_stmt'), [Tree('var_ref', [Token('NAME', 'res')])])])])])])])
source = 'omen Level:\n ONE\n TWO\n THREE\n\nweave main into string:\n var l1 as Level is Level_ONE\n var l2 as Level is L... l2:\n when Level_ONE -> "1"\n when Level.TWO -> "2"\n when THREE -> "3"\n else -> "other"\n return res\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 6, col 1] Entry point 'main' must return an integer or 'void', got 'string'

pengu*parser/pengu_checker.py:329: SemanticError
* TestCollectionsSemantics.test*array_slice_list_map_ops[weave main into void:\n let arr is array of int with size 10\n let first is arr at 0\n set arr at 0 is 99\n let part as slice of int is arr at 1 to 3\n let n is part length\n var l as list of int is list of int with capacity 10\n var m as map of int to string is map of int to string\n] *

self = <tests.test_compiler_core.TestCollectionsSemantics object at 0x107c08f50>
source = 'weave main into void:\n let arr is array of int with size 10\n let first is arr at 0\n set arr at 0 is 99\n let p...gth\n var l as list of int is list of int with capacity 10\n var m as map of int to string is map of int to string\n'

    @pytest.mark.parametrize(
        "source",
        [
            "weave main into int:\n"
            "  let arr is array of int with size 10\n"
            "  let first is arr at 0\n"
            "  let slice_part is arr at 1 to 4\n"
            "  let length_val is arr length\n"
            "  return first\n",
            "weave main into void:\n"
            "  let arr is array of int with size 10\n"
            "  let first is arr at 0\n"
            "  set arr at 0 is 99\n"
            "  let part as slice of int is arr at 1 to 3\n"
            "  let n is part length\n"
            "  var l as list of int is list of int with capacity 10\n"
            "  var m as map of int to string is map of int to string\n",
        ],
    )
    def test_array_slice_list_map_ops(self, source):

>       check_ok(source)

tests/test_compiler_core.py:701:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)
pengu_parser/pengu_checker.py:329: in check
raise first_err

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b4b9390>
node = Tree(Token('RULE', 'set_stmt'), [Tree(Token('RULE', 'set_target'), [Tree(Token('RULE', 'normal_target'), [Token('NAME', 'arr'), Tree('at_access', [Tree('int_lit', [Token('INT', '0')])])])]), Tree('int_lit', [Token('INT', '99')])])

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                while isinstance(with_t, RefType):
                    with_t = with_t.target
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (ArrayType, SliceType, ManyType, ListType)):
                                target_type = curr_t.element

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"

>                               raise self._make_error(

                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )

E pengu_parser.pengu_errors.MutabilityError: [line 4, col 7] Cannot mutate element of immutable 'let' variable 'arr'

pengu_parser/pengu_checker.py:3342: MutabilityError
******\_\_****** TestMaybeResultOrError.test_maybe_decl_and_unwrap ******\_\_\_******

self = <tests.test_compiler_core.TestMaybeResultOrError object at 0x107c09310>

        def test_maybe_decl_and_unwrap(self):

>           check_ok(

                """rune User:
      name as string

    weave main into string:
      let u as maybe User is maybe none
      let guest as string is "guest"
      let u2 as maybe string is maybe none
      let result is u2 or else guest
      return result
    """
            )

tests/test_compiler_core.py:770:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b46da70>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'rune_d...Tree(Token('RULE', 'stmt'), [Tree(Token('RULE', 'return_stmt'), [Tree('var_ref', [Token('NAME', 'result')])])])])])])])
source = 'rune User:\n name as string\n\nweave main into string:\n let u as maybe User is maybe none\n let guest as string is "guest"\n let u2 as maybe string is maybe none\n let result is u2 or else guest\n return result\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'string'

pengu*parser/pengu_checker.py:329: SemanticError
* TestEnchantingSemantics.test*enchanting_methods_check[rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with x is self->x + other.x, y is self->y + other.y\n\n weave length into float:\n (self->x * self->x + self->y * self->y) to float\n\n weave move with dx as float, dy as float into void:\n set self->x is self->x + dx\n set self->y is self->y + dy\n\nweave main into void:\n let a as Vec2 is with x is 10, y is 20\n let b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n] *

self = <tests.test_compiler_core.TestEnchantingSemantics object at 0x107c09bd0>
source = 'rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with...b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n'

        @pytest.mark.parametrize(
            "source",
            [
                VEC2
                + """enchanting Vec2:
      weave add with other as Vec2 into void:
        set self->x is self->x + other.x
        set self->y is self->y + other.y
    """,
                VEC2
                + """enchanting Vec2:
      weave add with other as Vec2 into Vec2:
        Vec2 is with x is self->x + other.x, y is self->y + other.y

      weave length into float:
        (self->x * self->x + self->y * self->y) to float

      weave move with dx as float, dy as float into void:
        set self->x is self->x + dx
        set self->y is self->y + dy

    weave main into void:
      let a as Vec2 is with x is 10, y is 20
      let b as Vec2 is with x is 5, y is 5
      let c is calling a.add with b
      var d as Vec2 is a
      calling d.move with 10, 0
    """,
            ],
        )
        def test_enchanting_methods_check(self, source):

>           check_ok(source)

tests/test_compiler_core.py:1149:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:86: in check
tree = parser.parse(source)
^^^^^^^^^^^^^^^^^^^^

---

self = <pengu_parser.pengu_parser.PenguParser object at 0x109862490>
code = 'rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with...b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n'

    def parse(self, code: str) -> Tree:
        """Parses PenguScript source code into a Lark AST Tree.

        Args:
            code: PenguScript source text.

        Returns:
            Lark AST Tree root.

        Raises:
            ParseError: when the source is not valid PenguScript (Lark's syntax
                exceptions are converted, with a hint when the removed 0.10.0
                'and' separator is the likely cause).
        """
        code = strip_bom(code)
        clean_code = self._strip_comments(code).rstrip() + '\n'
        try:
            return self.parser.parse(clean_code, start='start')
        except LarkUnexpectedInput as exc:

>           raise self._parse_error(code, exc) from None
>
> E pengu_parser.pengu_errors.ParseError: [line 6, col 13] Syntax error: unexpected 'with' at line 6, column 13

pengu_parser/pengu_parser.py:143: ParseError
******\_\_\_****** TestDestructuring.test_rune_destructuring_valid ******\_\_\_\_******

self = <tests.test_compiler_core.TestDestructuring object at 0x107c0ccd0>

    def test_rune_destructuring_valid(self):

>       check_ok(

            VEC2
            + "weave main into float:\n  let v as Vec2 is with x is 1.0, y is 2.0\n  let px, py is v\n  return px + py\n"
        )

tests/test_compiler_core.py:2651:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b4966d0>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'rune_d...turn_stmt'), [Tree('add', [Tree('var_ref', [Token('NAME', 'px')]), Tree('var_ref', [Token('NAME', 'py')])])])])])])])])
source = 'rune Vec2:\n x as float\n y as float\nweave main into float:\n let v as Vec2 is with x is 1.0, y is 2.0\n let px, py is v\n return px + py\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'

pengu_parser/pengu_checker.py:329: SemanticError
**\_\_** TestStringInterpolation.test_interpolation_format_string_emission **\_\_\_**

self = <tests.test_compiler_core.TestStringInterpolation object at 0x107c78640>

    def test_interpolation_format_string_emission(self):
        c = gen_bundle(
            'weave main into void:\n'
            '  let name is "player1"\n'
            '  let x is 10\n'
            '  let msg is "player {name} at {x}"\n'
        )

>       assert 'pengu_string_format("player %s at %d"' in c
>
> E assert 'pengu_string_format("player %s at %d"' in '/_ Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...t_args()\' etc. _/\n pengu_init(argc, argv);\n pengu_main();\n fflush(stdout);\n fflush(stderr);\n return 0;\n}\n'

tests/test_compiler_core.py:2694: AssertionError
**\_\_\_** TestCodegenEmissionArraysSlices.test_collection_emission_shapes **\_\_\_\_**

self = <tests.test_compiler_core.TestCodegenEmissionArraysSlices object at 0x107c0dbd0>

        def test_collection_emission_shapes(self):

>           c = gen_bundle(

                VEC2
                + """weave test_collections into void:
      let arr is array of int with size 10
      let first is arr at 0
      set arr at 0 is 99
      let part as slice of int is arr at 1 to 3
      let n is part length
      let evens is for x in arr when x % 2 == 0 then x
      let doubled is for x in arr then x * 2
      var vertices as list of Vec2 is list of Vec2 with capacity 100
      var lookup as map of int to Vec2 is map of int to Vec2
    """
            )

tests/test_compiler_core.py:2957:

---

tests/conftest.py:147: in gen_bundle
checker.check(tree, source=code, filename=fname)
pengu_parser/pengu_checker.py:329: in check
raise first_err

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b4485d0>
node = Tree(Token('RULE', 'set_stmt'), [Tree(Token('RULE', 'set_target'), [Tree(Token('RULE', 'normal_target'), [Token('NAME', 'arr'), Tree('at_access', [Tree('int_lit', [Token('INT', '0')])])])]), Tree('int_lit', [Token('INT', '99')])])

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                while isinstance(with_t, RefType):
                    with_t = with_t.target
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (ArrayType, SliceType, ManyType, ListType)):
                                target_type = curr_t.element

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"

>                               raise self._make_error(

                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )

E pengu_parser.pengu_errors.MutabilityError: [line 7, col 7] Cannot mutate element of immutable 'let' variable 'arr'

pengu_parser/pengu_checker.py:3342: MutabilityError
****\_**** TestCodegenEmissionArraysSlices.test_loop_and_index_emission ****\_****

self = <tests.test_compiler_core.TestCodegenEmissionArraysSlices object at 0x107c78e90>

        def test_loop_and_index_emission(self):

>           c = gen_bundle(

                """weave loops_demo into void:
      var x as int is 0
      while x < 10:
        set x is x + 1
        if x == 5:
          continue
        if x == 9:
          break

      var arr as array of int with size 5 is [1, 2, 3, 4, 5]
      for i from 0 to 5:
        set arr at i is (arr at i) * 2

      let part as slice of int is arr at 1 to 4
      for i from 0 to part.len:
        set part at i is (part at i) + 10

      for num in arr:
        let doubled is num * 2

      var lst as list of int is list of int with capacity 10
      for i from 0 to 5:
        calling lst.push with i * 10
      for i from 0 to lst.len:
        set lst at i is (lst at i) + 100
    """
            )

tests/test_compiler_core.py:2989:

---

tests/conftest.py:147: in gen_bundle
checker.check(tree, source=code, filename=fname)
pengu_parser/pengu_checker.py:329: in check
raise first_err

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x10b4494f0>
node = Tree(Token('RULE', 'set_stmt'), [Tree(Token('RULE', 'set_target'), [Tree(Token('RULE', 'normal_target'), [Token('NAME'...ar_ref', [Token('NAME', 'part')]), Tree('var_ref', [Token('NAME', 'i')])])]), Tree('int_lit', [Token('INT', '10')])])])

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                while isinstance(with_t, RefType):
                    with_t = with_t.target
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (ArrayType, SliceType, ManyType, ListType)):
                                target_type = curr_t.element

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"

>                               raise self._make_error(

                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )

E pengu_parser.pengu_errors.MutabilityError: [line 16, col 9] Cannot mutate element of immutable 'let' variable 'part'

pengu_parser/pengu_checker.py:3342: MutabilityError
********\_\_******** TestIndexedFor.test_indexed_for_over_list ********\_\_\_********

self = <tests.test_compiler_features.TestIndexedFor object at 0x107c199d0>

        def test_indexed_for_over_list(self):
            code = """weave test_for with nums as list of int into void:
      var acc as int is 0
      for i, v in nums:
        set acc is acc + i * v
    """
            c = gen_bundle(code)
            assert "for (int32_t i = 0; i < (nums).len; i++) {" in c

>           assert "int32_t v = (*(int32_t*)pengu_list_at(&(nums), i));" in c
>
> E assert 'int32_t v = (_(int32_t_)pengu_list_at(&(nums), i));' in '/_ Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...sers/runner/work/PenguScript/PenguScript/t.pengu"\n acc = (acc + (i _ v));\n }\n pengu_frame_pop();\n}\n\n#line 1'

tests/test_compiler_features.py:425: AssertionError
=========================== short test summary info ============================
FAILED tests/test_compiler_core.py::TestStructFieldAccess::test_valid_field_access - pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'
FAILED tests/test_compiler_core.py::TestStructFieldAccess::test_unknown_field_fails - AssertionError: error "[line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'" (codes ['E0020', 'E0013', 'E0020']) does not mention "has no field 'z'"
FAILED tests/test_compiler_core.py::TestEchoOmenSemantics::test_simple_enum_variants - pengu_parser.pengu_errors.SemanticError: [line 6, col 1] Entry point 'main' must return an integer or 'void', got 'string'
FAILED tests/test_compiler_core.py::TestCollectionsSemantics::test_array_slice_list_map_ops[weave main into void:\n let arr is array of int with size 10\n let first is arr at 0\n set arr at 0 is 99\n let part as slice of int is arr at 1 to 3\n let n is part length\n var l as list of int is list of int with capacity 10\n var m as map of int to string is map of int to string\n] - pengu_parser.pengu_errors.MutabilityError: [line 4, col 7] Cannot mutate element of immutable 'let' variable 'arr'
FAILED tests/test_compiler_core.py::TestMaybeResultOrError::test_maybe_decl_and_unwrap - pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'string'
FAILED tests/test_compiler_core.py::TestEnchantingSemantics::test_enchanting_methods_check[rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with x is self->x + other.x, y is self->y + other.y\n\n weave length into float:\n (self->x * self->x + self->y * self->y) to float\n\n weave move with dx as float, dy as float into void:\n set self->x is self->x + dx\n set self->y is self->y + dy\n\nweave main into void:\n let a as Vec2 is with x is 10, y is 20\n let b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n] - pengu_parser.pengu_errors.ParseError: [line 6, col 13] Syntax error: unexpected 'with' at line 6, column 13
FAILED tests/test_compiler_core.py::TestDestructuring::test_rune_destructuring_valid - pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'
FAILED tests/test_compiler_core.py::TestStringInterpolation::test_interpolation_format_string_emission - assert 'pengu_string_format("player %s at %d"' in '/_ Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...t_args()\' etc. _/\n pengu_init(argc, argv);\n pengu_main();\n fflush(stdout);\n fflush(stderr);\n return 0;\n}\n'
FAILED tests/test_compiler_core.py::TestCodegenEmissionArraysSlices::test_collection_emission_shapes - pengu_parser.pengu_errors.MutabilityError: [line 7, col 7] Cannot mutate element of immutable 'let' variable 'arr'
FAILED tests/test_compiler_core.py::TestCodegenEmissionArraysSlices::test_loop_and_index_emission - pengu_parser.pengu_errors.MutabilityError: [line 16, col 9] Cannot mutate element of immutable 'let' variable 'part'
FAILED tests/test_compiler_features.py::TestIndexedFor::test_indexed_for_over_list - assert 'int32_t v = (_(int32_t_)pengu_list_at(&(nums), i));' in '/_ Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...sers/runner/work/PenguScript/PenguScript/t.pengu"\n acc = (acc + (i _ v));\n }\n pengu_frame_pop();\n}\n\n#line 1'
11 failed, 996 passed, 9 skipped in 111.84s (0:01:51)
Error: Process completed with exit code 1.

Linux:

Run python -m pytest tests -q -p no:cacheprovider
........................................................................ [ 7%]
...............FF............F.............F.......F.................... [ 14%]
........F............................................................... [ 21%]
........................................................F....F.......... [ 28%]
...F.F..........................................................F....... [ 35%]
........................................................................ [ 42%]
.............................................................s..ss...... [ 49%]
........................................................................ [ 56%]
........................................................................ [ 63%]
......................................s..............................s.. [ 70%]
..................s.....................s.s............................. [ 77%]
........................................................................ [ 85%]
........................................................................ [ 92%]
...................s.................................................... [ 99%]
........ [100%]
=================================== FAILURES ===================================
**\*\***\_\_\_\_**\*\*** TestStructFieldAccess.test_valid_field_access **\*\*\*\***\_**\*\*\*\***

self = <tests.test_compiler_core.TestStructFieldAccess object at 0x7fcfadf89a90>

    def test_valid_field_access(self):

>       check_ok(

            VEC2
            + "weave main into float:\n  let v as Vec2 is with x is 10, y is 20\n  return v.x + v.y\n"
        )

tests/test_compiler_core.py:383:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x7fcfad4c24c0>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'rune_d..., Token('NAME', 'x')]), Tree('field_access', [Tree('var_ref', [Token('NAME', 'v')]), Token('NAME', 'y')])])])])])])])])
source = 'rune Vec2:\n x as float\n y as float\nweave main into float:\n let v as Vec2 is with x is 10, y is 20\n return v.x + v.y\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'

pengu_parser/pengu_checker.py:329: SemanticError
**\*\***\_\_\_\_**\*\*** TestStructFieldAccess.test_unknown_field_fails **\*\***\_\_\_\_**\*\***

self = <tests.test_compiler_core.TestStructFieldAccess object at 0x7fcfadf89bd0>

    def test_unknown_field_fails(self):

>       expect_error(

            VEC2
            + "weave main into float:\n  let v as Vec2 is with x is 10, y is 20\n  return v.z\n",
            contains=["E0013", "has no field 'z'"],
        )

tests/test_compiler_core.py:389:

---

source = 'rune Vec2:\n x as float\n y as float\nweave main into float:\n let v as Vec2 is with x is 10, y is 20\n return v.z\n'
filename = 't.pengu', contains = ['E0013', "has no field 'z'"]

    def expect_error(source, filename="t.pengu", contains=None):
        """Assert ``source`` fails to compile; return the error text.

        ``contains`` may be a substring (or a list of substrings) of the message;
        an error code such as ``E0001`` is also accepted (codes are stored on the
        raised error, not in its message).

        Note: ``tests.conftest.check_error`` currently raises NameError (it refers
        to an undefined ``base_dir``), so this module carries its own equivalent.
        """
        tree = PenguParser().parse(source)
        checker = PenguChecker(base_dir=".")
        try:
            checker.check(tree, source=source, filename=filename)
        except PenguError as exc:
            text = str(exc)
            codes = [e.code for e in getattr(exc, "all_errors", [])] + [exc.code]
        except Exception as exc:  # noqa: BLE001 - keep whatever error was raised
            text = str(exc)
            codes = []
        else:
            raise AssertionError("expected a compile error but the source is clean")
        if contains is not None:
            wanted = [contains] if isinstance(contains, str) else contains
            for w in wanted:
                if w in text or w in codes:
                    continue

>               raise AssertionError(

                    f"error {text!r} (codes {codes}) does not mention {w!r}"
                )

E AssertionError: error "[line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'" (codes ['E0020', 'E0013', 'E0020']) does not mention "has no field 'z'"

tests/test_compiler_core.py:81: AssertionError
**\*\***\_\_\_**\*\*** TestEchoOmenSemantics.test_simple_enum_variants **\*\***\_\_\_\_**\*\***

self = <tests.test_compiler_core.TestEchoOmenSemantics object at 0x7fcfae63b240>

        def test_simple_enum_variants(self):

>           check_ok(

                """omen Level:
      ONE
      TWO
      THREE

    weave main into string:
      var l1 as Level is Level_ONE
      var l2 as Level is Level.TWO
      var l3 as Level is THREE
      let res is judge l2:
        when Level_ONE -> "1"
        when Level.TWO -> "2"
        when THREE -> "3"
        else -> "other"
      return res
    """
            )

tests/test_compiler_core.py:499:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x7fcfad49d7b0>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'omen_d...), Tree(Token('RULE', 'stmt'), [Tree(Token('RULE', 'return_stmt'), [Tree('var_ref', [Token('NAME', 'res')])])])])])])])
source = 'omen Level:\n ONE\n TWO\n THREE\n\nweave main into string:\n var l1 as Level is Level_ONE\n var l2 as Level is L... l2:\n when Level_ONE -> "1"\n when Level.TWO -> "2"\n when THREE -> "3"\n else -> "other"\n return res\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 6, col 1] Entry point 'main' must return an integer or 'void', got 'string'

pengu\*parser/pengu_checker.py:329: SemanticError

- TestCollectionsSemantics.test*array_slice_list_map_ops[weave main into void:\n let arr is array of int with size 10\n let first is arr at 0\n set arr at 0 is 99\n let part as slice of int is arr at 1 to 3\n let n is part length\n var l as list of int is list of int with capacity 10\n var m as map of int to string is map of int to string\n] *

self = <tests.test_compiler_core.TestCollectionsSemantics object at 0x7fcfadf8a850>
source = 'weave main into void:\n let arr is array of int with size 10\n let first is arr at 0\n set arr at 0 is 99\n let p...gth\n var l as list of int is list of int with capacity 10\n var m as map of int to string is map of int to string\n'

    @pytest.mark.parametrize(
        "source",
        [
            "weave main into int:\n"
            "  let arr is array of int with size 10\n"
            "  let first is arr at 0\n"
            "  let slice_part is arr at 1 to 4\n"
            "  let length_val is arr length\n"
            "  return first\n",
            "weave main into void:\n"
            "  let arr is array of int with size 10\n"
            "  let first is arr at 0\n"
            "  set arr at 0 is 99\n"
            "  let part as slice of int is arr at 1 to 3\n"
            "  let n is part length\n"
            "  var l as list of int is list of int with capacity 10\n"
            "  var m as map of int to string is map of int to string\n",
        ],
    )
    def test_array_slice_list_map_ops(self, source):

>       check_ok(source)

tests/test_compiler_core.py:701:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)
pengu_parser/pengu_checker.py:329: in check
raise first_err

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x7fcfad49dde0>
node = Tree(Token('RULE', 'set_stmt'), [Tree(Token('RULE', 'set_target'), [Tree(Token('RULE', 'normal_target'), [Token('NAME', 'arr'), Tree('at_access', [Tree('int_lit', [Token('INT', '0')])])])]), Tree('int_lit', [Token('INT', '99')])])

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                while isinstance(with_t, RefType):
                    with_t = with_t.target
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (ArrayType, SliceType, ManyType, ListType)):
                                target_type = curr_t.element

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"

>                               raise self._make_error(

                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )

E pengu_parser.pengu_errors.MutabilityError: [line 4, col 7] Cannot mutate element of immutable 'let' variable 'arr'

pengu_parser/pengu_checker.py:3342: MutabilityError
**\*\***\_\_**\*\*** TestMaybeResultOrError.test_maybe_decl_and_unwrap **\*\***\_\_\_**\*\***

self = <tests.test_compiler_core.TestMaybeResultOrError object at 0x7fcfadf8ac10>

        def test_maybe_decl_and_unwrap(self):

>           check_ok(

                """rune User:
      name as string

    weave main into string:
      let u as maybe User is maybe none
      let guest as string is "guest"
      let u2 as maybe string is maybe none
      let result is u2 or else guest
      return result
    """
            )

tests/test_compiler_core.py:770:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x7fcfad4b05d0>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'rune_d...Tree(Token('RULE', 'stmt'), [Tree(Token('RULE', 'return_stmt'), [Tree('var_ref', [Token('NAME', 'result')])])])])])])])
source = 'rune User:\n name as string\n\nweave main into string:\n let u as maybe User is maybe none\n let guest as string is "guest"\n let u2 as maybe string is maybe none\n let result is u2 or else guest\n return result\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'string'

pengu\*parser/pengu_checker.py:329: SemanticError

- TestEnchantingSemantics.test*enchanting_methods_check[rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with x is self->x + other.x, y is self->y + other.y\n\n weave length into float:\n (self->x * self->x + self->y _ self->y) to float\n\n weave move with dx as float, dy as float into void:\n set self->x is self->x + dx\n set self->y is self->y + dy\n\nweave main into void:\n let a as Vec2 is with x is 10, y is 20\n let b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n] _

self = <tests.test_compiler_core.TestEnchantingSemantics object at 0x7fcfadf8b4d0>
source = 'rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with...b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n'

        @pytest.mark.parametrize(
            "source",
            [
                VEC2
                + """enchanting Vec2:
      weave add with other as Vec2 into void:
        set self->x is self->x + other.x
        set self->y is self->y + other.y
    """,
                VEC2
                + """enchanting Vec2:
      weave add with other as Vec2 into Vec2:
        Vec2 is with x is self->x + other.x, y is self->y + other.y

      weave length into float:
        (self->x * self->x + self->y * self->y) to float

      weave move with dx as float, dy as float into void:
        set self->x is self->x + dx
        set self->y is self->y + dy

    weave main into void:
      let a as Vec2 is with x is 10, y is 20
      let b as Vec2 is with x is 5, y is 5
      let c is calling a.add with b
      var d as Vec2 is a
      calling d.move with 10, 0
    """,
            ],
        )
        def test_enchanting_methods_check(self, source):

>           check_ok(source)

tests/test_compiler_core.py:1149:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:86: in check
tree = parser.parse(source)
^^^^^^^^^^^^^^^^^^^^

---

self = <pengu_parser.pengu_parser.PenguParser object at 0x7fcfac335e50>
code = 'rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with...b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n'

    def parse(self, code: str) -> Tree:
        """Parses PenguScript source code into a Lark AST Tree.

        Args:
            code: PenguScript source text.

        Returns:
            Lark AST Tree root.

        Raises:
            ParseError: when the source is not valid PenguScript (Lark's syntax
                exceptions are converted, with a hint when the removed 0.10.0
                'and' separator is the likely cause).
        """
        code = strip_bom(code)
        clean_code = self._strip_comments(code).rstrip() + '\n'
        try:
            return self.parser.parse(clean_code, start='start')
        except LarkUnexpectedInput as exc:

>           raise self._parse_error(code, exc) from None
>
> E pengu_parser.pengu_errors.ParseError: [line 6, col 13] Syntax error: unexpected 'with' at line 6, column 13

pengu_parser/pengu_parser.py:143: ParseError
**\*\***\_\_\_**\*\*** TestDestructuring.test_rune_destructuring_valid **\*\***\_\_\_\_**\*\***

self = <tests.test_compiler_core.TestDestructuring object at 0x7fcfae03e5d0>

    def test_rune_destructuring_valid(self):

>       check_ok(

            VEC2
            + "weave main into float:\n  let v as Vec2 is with x is 1.0, y is 2.0\n  let px, py is v\n  return px + py\n"
        )

tests/test_compiler_core.py:2651:

---

tests/conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x7fcfab0e5180>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'rune_d...turn_stmt'), [Tree('add', [Tree('var_ref', [Token('NAME', 'px')]), Tree('var_ref', [Token('NAME', 'py')])])])])])])])])
source = 'rune Vec2:\n x as float\n y as float\nweave main into float:\n let v as Vec2 is with x is 1.0, y is 2.0\n let px, py is v\n return px + py\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'

pengu_parser/pengu_checker.py:329: SemanticError
**\_\_** TestStringInterpolation.test_interpolation_format_string_emission **\_\_\_**

self = <tests.test_compiler_core.TestStringInterpolation object at 0x7fcfae01efd0>

    def test_interpolation_format_string_emission(self):
        c = gen_bundle(
            'weave main into void:\n'
            '  let name is "player1"\n'
            '  let x is 10\n'
            '  let msg is "player {name} at {x}"\n'
        )

>       assert 'pengu_string_format("player %s at %d"' in c
>
> E assert 'pengu*string_format("player %s at %d"' in '/* Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...t*args()\' etc. */\n pengu_init(argc, argv);\n pengu_main();\n fflush(stdout);\n fflush(stderr);\n return 0;\n}\n'

tests/test_compiler_core.py:2694: AssertionError
**\_\_\_** TestCodegenEmissionArraysSlices.test_collection_emission_shapes **\_\_\_\_**

self = <tests.test_compiler_core.TestCodegenEmissionArraysSlices object at 0x7fcfae03f4d0>

        def test_collection_emission_shapes(self):

>           c = gen_bundle(

                VEC2
                + """weave test_collections into void:
      let arr is array of int with size 10
      let first is arr at 0
      set arr at 0 is 99
      let part as slice of int is arr at 1 to 3
      let n is part length
      let evens is for x in arr when x % 2 == 0 then x
      let doubled is for x in arr then x * 2
      var vertices as list of Vec2 is list of Vec2 with capacity 100
      var lookup as map of int to Vec2 is map of int to Vec2
    """
            )

tests/test_compiler_core.py:2957:

---

tests/conftest.py:147: in gen_bundle
checker.check(tree, source=code, filename=fname)
pengu_parser/pengu_checker.py:329: in check
raise first_err

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x7fcfab0e6d00>
node = Tree(Token('RULE', 'set_stmt'), [Tree(Token('RULE', 'set_target'), [Tree(Token('RULE', 'normal_target'), [Token('NAME', 'arr'), Tree('at_access', [Tree('int_lit', [Token('INT', '0')])])])]), Tree('int_lit', [Token('INT', '99')])])

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                while isinstance(with_t, RefType):
                    with_t = with_t.target
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (ArrayType, SliceType, ManyType, ListType)):
                                target_type = curr_t.element

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"

>                               raise self._make_error(

                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )

E pengu_parser.pengu_errors.MutabilityError: [line 7, col 7] Cannot mutate element of immutable 'let' variable 'arr'

pengu_parser/pengu_checker.py:3342: MutabilityError \***\*\_\*\*** TestCodegenEmissionArraysSlices.test_loop_and_index_emission \***\*\_\*\***

self = <tests.test_compiler_core.TestCodegenEmissionArraysSlices object at 0x7fcfae01f820>

        def test_loop_and_index_emission(self):

>           c = gen_bundle(

                """weave loops_demo into void:
      var x as int is 0
      while x < 10:
        set x is x + 1
        if x == 5:
          continue
        if x == 9:
          break

      var arr as array of int with size 5 is [1, 2, 3, 4, 5]
      for i from 0 to 5:
        set arr at i is (arr at i) * 2

      let part as slice of int is arr at 1 to 4
      for i from 0 to part.len:
        set part at i is (part at i) + 10

      for num in arr:
        let doubled is num * 2

      var lst as list of int is list of int with capacity 10
      for i from 0 to 5:
        calling lst.push with i * 10
      for i from 0 to lst.len:
        set lst at i is (lst at i) + 100
    """
            )

tests/test_compiler_core.py:2989:

---

tests/conftest.py:147: in gen_bundle
checker.check(tree, source=code, filename=fname)
pengu_parser/pengu_checker.py:329: in check
raise first_err

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x7fcfab0ec890>
node = Tree(Token('RULE', 'set_stmt'), [Tree(Token('RULE', 'set_target'), [Tree(Token('RULE', 'normal_target'), [Token('NAME'...ar_ref', [Token('NAME', 'part')]), Tree('var_ref', [Token('NAME', 'i')])])]), Tree('int_lit', [Token('INT', '10')])])])

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                while isinstance(with_t, RefType):
                    with_t = with_t.target
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (ArrayType, SliceType, ManyType, ListType)):
                                target_type = curr_t.element

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"

>                               raise self._make_error(

                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )

E pengu_parser.pengu_errors.MutabilityError: [line 16, col 9] Cannot mutate element of immutable 'let' variable 'part'

pengu_parser/pengu_checker.py:3342: MutabilityError
**\*\*\*\***\_\_**\*\*\*\*** TestIndexedFor.test_indexed_for_over_list **\*\*\*\***\_\_\_**\*\*\*\***

self = <tests.test_compiler_features.TestIndexedFor object at 0x7fcfae042140>

        def test_indexed_for_over_list(self):
            code = """weave test_for with nums as list of int into void:
      var acc as int is 0
      for i, v in nums:
        set acc is acc + i * v
    """
            c = gen_bundle(code)
            assert "for (int32_t i = 0; i < (nums).len; i++) {" in c

>           assert "int32_t v = (*(int32_t*)pengu_list_at(&(nums), i));" in c
>
> E assert 'int32*t v = (*(int32*t*)pengu*list_at(&(nums), i));' in '/* Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...home/runner/work/PenguScript/PenguScript/t.pengu"\n acc = (acc + (i \_ v));\n }\n pengu_frame_pop();\n}\n\n#line 1'

tests/test*compiler_features.py:425: AssertionError
=========================== short test summary info ============================
FAILED tests/test_compiler_core.py::TestStructFieldAccess::test_valid_field_access - pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'
FAILED tests/test_compiler_core.py::TestStructFieldAccess::test_unknown_field_fails - AssertionError: error "[line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'" (codes ['E0020', 'E0013', 'E0020']) does not mention "has no field 'z'"
FAILED tests/test_compiler_core.py::TestEchoOmenSemantics::test_simple_enum_variants - pengu_parser.pengu_errors.SemanticError: [line 6, col 1] Entry point 'main' must return an integer or 'void', got 'string'
FAILED tests/test_compiler_core.py::TestCollectionsSemantics::test_array_slice_list_map_ops[weave main into void:\n let arr is array of int with size 10\n let first is arr at 0\n set arr at 0 is 99\n let part as slice of int is arr at 1 to 3\n let n is part length\n var l as list of int is list of int with capacity 10\n var m as map of int to string is map of int to string\n] - pengu_parser.pengu_errors.MutabilityError: [line 4, col 7] Cannot mutate element of immutable 'let' variable 'arr'
FAILED tests/test_compiler_core.py::TestMaybeResultOrError::test_maybe_decl_and_unwrap - pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'string'
FAILED tests/test_compiler_core.py::TestEnchantingSemantics::test_enchanting_methods_check[rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with x is self->x + other.x, y is self->y + other.y\n\n weave length into float:\n (self->x * self->x + self->y * self->y) to float\n\n weave move with dx as float, dy as float into void:\n set self->x is self->x + dx\n set self->y is self->y + dy\n\nweave main into void:\n let a as Vec2 is with x is 10, y is 20\n let b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n] - pengu_parser.pengu_errors.ParseError: [line 6, col 13] Syntax error: unexpected 'with' at line 6, column 13
FAILED tests/test_compiler_core.py::TestDestructuring::test_rune_destructuring_valid - pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'
FAILED tests/test_compiler_core.py::TestStringInterpolation::test_interpolation_format_string_emission - assert 'pengu_string_format("player %s at %d"' in '/* Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...t*args()\' etc. */\n pengu*init(argc, argv);\n pengu_main();\n fflush(stdout);\n fflush(stderr);\n return 0;\n}\n'
FAILED tests/test_compiler_core.py::TestCodegenEmissionArraysSlices::test_collection_emission_shapes - pengu_parser.pengu_errors.MutabilityError: [line 7, col 7] Cannot mutate element of immutable 'let' variable 'arr'
FAILED tests/test_compiler_core.py::TestCodegenEmissionArraysSlices::test_loop_and_index_emission - pengu_parser.pengu_errors.MutabilityError: [line 16, col 9] Cannot mutate element of immutable 'let' variable 'part'
FAILED tests/test_compiler_features.py::TestIndexedFor::test_indexed_for_over_list - assert 'int32_t v = (*(int32*t*)pengu*list_at(&(nums), i));' in '/* Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...home/runner/work/PenguScript/PenguScript/t.pengu"\n acc = (acc + (i \_ v));\n }\n pengu_frame_pop();\n}\n\n#line 1'
11 failed, 996 passed, 9 skipped in 132.13s (0:02:12)
Error: Process completed with exit code 1.

Windows:

Run python -m pytest tests -q -p no:cacheprovider
........................................................................ [ 7%]
...............FF............F.............F.......F.................... [ 14%]
........F............................................................... [ 21%]
........................................................F....F.......... [ 28%]
...F.F..........................................................F....... [ 35%]
........................................................................ [ 42%]
........................................................................ [ 49%]
........................................................................ [ 56%]
........................................................................ [ 63%]
......................................s................................. [ 70%]
..................................................................s..... [ 77%]
........................................................................ [ 85%]
........................................................................ [ 92%]
...................s.................................................... [ 99%]
........ [100%]
================================== FAILURES ===================================
**\*\***\_\_\_\_**\*\*** TestStructFieldAccess.test_valid_field_access **\*\***\_\_\_\_**\*\***

self = <tests.test_compiler_core.TestStructFieldAccess object at 0x0000012A4371F750>

    def test_valid_field_access(self):

>       check_ok(

            VEC2
            + "weave main into float:\n  let v as Vec2 is with x is 10, y is 20\n  return v.x + v.y\n"
        )

tests\test_compiler_core.py:383:

---

tests\conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x0000012A43F34520>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'rune_d..., Token('NAME', 'x')]), Tree('field_access', [Tree('var_ref', [Token('NAME', 'v')]), Token('NAME', 'y')])])])])])])])])
source = 'rune Vec2:\n x as float\n y as float\nweave main into float:\n let v as Vec2 is with x is 10, y is 20\n return v.x + v.y\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'

pengu_parser\pengu_checker.py:329: SemanticError
**\*\***\_\_\_**\*\*** TestStructFieldAccess.test_unknown_field_fails **\*\***\_\_\_\_**\*\***

self = <tests.test_compiler_core.TestStructFieldAccess object at 0x0000012A4371F890>

    def test_unknown_field_fails(self):

>       expect_error(

            VEC2
            + "weave main into float:\n  let v as Vec2 is with x is 10, y is 20\n  return v.z\n",
            contains=["E0013", "has no field 'z'"],
        )

tests\test_compiler_core.py:389:

---

source = 'rune Vec2:\n x as float\n y as float\nweave main into float:\n let v as Vec2 is with x is 10, y is 20\n return v.z\n'
filename = 't.pengu', contains = ['E0013', "has no field 'z'"]

    def expect_error(source, filename="t.pengu", contains=None):
        """Assert ``source`` fails to compile; return the error text.

        ``contains`` may be a substring (or a list of substrings) of the message;
        an error code such as ``E0001`` is also accepted (codes are stored on the
        raised error, not in its message).

        Note: ``tests.conftest.check_error`` currently raises NameError (it refers
        to an undefined ``base_dir``), so this module carries its own equivalent.
        """
        tree = PenguParser().parse(source)
        checker = PenguChecker(base_dir=".")
        try:
            checker.check(tree, source=source, filename=filename)
        except PenguError as exc:
            text = str(exc)
            codes = [e.code for e in getattr(exc, "all_errors", [])] + [exc.code]
        except Exception as exc:  # noqa: BLE001 - keep whatever error was raised
            text = str(exc)
            codes = []
        else:
            raise AssertionError("expected a compile error but the source is clean")
        if contains is not None:
            wanted = [contains] if isinstance(contains, str) else contains
            for w in wanted:
                if w in text or w in codes:
                    continue

>               raise AssertionError(

                    f"error {text!r} (codes {codes}) does not mention {w!r}"
                )

E AssertionError: error "[line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'" (codes ['E0020', 'E0013', 'E0020']) does not mention "has no field 'z'"

tests\test_compiler_core.py:81: AssertionError
**\*\***\_\_\_**\*\*** TestEchoOmenSemantics.test_simple_enum_variants **\*\***\_\_\_**\*\***

self = <tests.test_compiler_core.TestEchoOmenSemantics object at 0x0000012A43184F30>

        def test_simple_enum_variants(self):

>           check_ok(

                """omen Level:
      ONE
      TWO
      THREE

    weave main into string:
      var l1 as Level is Level_ONE
      var l2 as Level is Level.TWO
      var l3 as Level is THREE
      let res is judge l2:
        when Level_ONE -> "1"
        when Level.TWO -> "2"
        when THREE -> "3"
        else -> "other"
      return res
    """
            )

tests\test_compiler_core.py:499:

---

tests\conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x0000012A43F36780>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'omen_d...), Tree(Token('RULE', 'stmt'), [Tree(Token('RULE', 'return_stmt'), [Tree('var_ref', [Token('NAME', 'res')])])])])])])])
source = 'omen Level:\n ONE\n TWO\n THREE\n\nweave main into string:\n var l1 as Level is Level_ONE\n var l2 as Level is L... l2:\n when Level_ONE -> "1"\n when Level.TWO -> "2"\n when THREE -> "3"\n else -> "other"\n return res\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 6, col 1] Entry point 'main' must return an integer or 'void', got 'string'

pengu\*parser\pengu_checker.py:329: SemanticError

- TestCollectionsSemantics.test*array_slice_list_map_ops[weave main into void:\n let arr is array of int with size 10\n let first is arr at 0\n set arr at 0 is 99\n let part as slice of int is arr at 1 to 3\n let n is part length\n var l as list of int is list of int with capacity 10\n var m as map of int to string is map of int to string\n] *

self = <tests.test_compiler_core.TestCollectionsSemantics object at 0x0000012A431A4550>
source = 'weave main into void:\n let arr is array of int with size 10\n let first is arr at 0\n set arr at 0 is 99\n let p...gth\n var l as list of int is list of int with capacity 10\n var m as map of int to string is map of int to string\n'

    @pytest.mark.parametrize(
        "source",
        [
            "weave main into int:\n"
            "  let arr is array of int with size 10\n"
            "  let first is arr at 0\n"
            "  let slice_part is arr at 1 to 4\n"
            "  let length_val is arr length\n"
            "  return first\n",
            "weave main into void:\n"
            "  let arr is array of int with size 10\n"
            "  let first is arr at 0\n"
            "  set arr at 0 is 99\n"
            "  let part as slice of int is arr at 1 to 3\n"
            "  let n is part length\n"
            "  var l as list of int is list of int with capacity 10\n"
            "  var m as map of int to string is map of int to string\n",
        ],
    )
    def test_array_slice_list_map_ops(self, source):

>       check_ok(source)

tests\test_compiler_core.py:701:

---

tests\conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\conftest.py:88: in check
checker.check(tree, source=source, filename=filename)
pengu_parser\pengu_checker.py:329: in check
raise first_err

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x0000012A43F352E0>
node = Tree(Token('RULE', 'set_stmt'), [Tree(Token('RULE', 'set_target'), [Tree(Token('RULE', 'normal_target'), [Token('NAME', 'arr'), Tree('at_access', [Tree('int_lit', [Token('INT', '0')])])])]), Tree('int_lit', [Token('INT', '99')])])

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                while isinstance(with_t, RefType):
                    with_t = with_t.target
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (ArrayType, SliceType, ManyType, ListType)):
                                target_type = curr_t.element

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"

>                               raise self._make_error(

                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )

E pengu_parser.pengu_errors.MutabilityError: [line 4, col 7] Cannot mutate element of immutable 'let' variable 'arr'

pengu_parser\pengu_checker.py:3342: MutabilityError
**\*\***\_\_**\*\*** TestMaybeResultOrError.test_maybe_decl_and_unwrap **\*\***\_\_**\*\***

self = <tests.test_compiler_core.TestMaybeResultOrError object at 0x0000012A431A4910>

        def test_maybe_decl_and_unwrap(self):

>           check_ok(

                """rune User:
      name as string

    weave main into string:
      let u as maybe User is maybe none
      let guest as string is "guest"
      let u2 as maybe string is maybe none
      let result is u2 or else guest
      return result
    """
            )

tests\test_compiler_core.py:770:

---

tests\conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x0000012A43F84730>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'rune_d...Tree(Token('RULE', 'stmt'), [Tree(Token('RULE', 'return_stmt'), [Tree('var_ref', [Token('NAME', 'result')])])])])])])])
source = 'rune User:\n name as string\n\nweave main into string:\n let u as maybe User is maybe none\n let guest as string is "guest"\n let u2 as maybe string is maybe none\n let result is u2 or else guest\n return result\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'string'

pengu\*parser\pengu_checker.py:329: SemanticError

- TestEnchantingSemantics.test*enchanting_methods_check[rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with x is self->x + other.x, y is self->y + other.y\n\n weave length into float:\n (self->x * self->x + self->y _ self->y) to float\n\n weave move with dx as float, dy as float into void:\n set self->x is self->x + dx\n set self->y is self->y + dy\n\nweave main into void:\n let a as Vec2 is with x is 10, y is 20\n let b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n] _

self = <tests.test_compiler_core.TestEnchantingSemantics object at 0x0000012A431A51D0>
source = 'rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with...b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n'

        @pytest.mark.parametrize(
            "source",
            [
                VEC2
                + """enchanting Vec2:
      weave add with other as Vec2 into void:
        set self->x is self->x + other.x
        set self->y is self->y + other.y
    """,
                VEC2
                + """enchanting Vec2:
      weave add with other as Vec2 into Vec2:
        Vec2 is with x is self->x + other.x, y is self->y + other.y

      weave length into float:
        (self->x * self->x + self->y * self->y) to float

      weave move with dx as float, dy as float into void:
        set self->x is self->x + dx
        set self->y is self->y + dy

    weave main into void:
      let a as Vec2 is with x is 10, y is 20
      let b as Vec2 is with x is 5, y is 5
      let c is calling a.add with b
      var d as Vec2 is a
      calling d.move with 10, 0
    """,
            ],
        )
        def test_enchanting_methods_check(self, source):

>           check_ok(source)

tests\test_compiler_core.py:1149:

---

tests\conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\conftest.py:86: in check
tree = parser.parse(source)
^^^^^^^^^^^^^^^^^^^^

---

self = <pengu_parser.pengu_parser.PenguParser object at 0x0000012A462AC2D0>
code = 'rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with...b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n'

    def parse(self, code: str) -> Tree:
        """Parses PenguScript source code into a Lark AST Tree.

        Args:
            code: PenguScript source text.

        Returns:
            Lark AST Tree root.

        Raises:
            ParseError: when the source is not valid PenguScript (Lark's syntax
                exceptions are converted, with a hint when the removed 0.10.0
                'and' separator is the likely cause).
        """
        code = strip_bom(code)
        clean_code = self._strip_comments(code).rstrip() + '\n'
        try:
            return self.parser.parse(clean_code, start='start')
        except LarkUnexpectedInput as exc:

>           raise self._parse_error(code, exc) from None
>
> E pengu_parser.pengu_errors.ParseError: [line 6, col 13] Syntax error: unexpected 'with' at line 6, column 13

pengu_parser\pengu_parser.py:143: ParseError
**\*\***\_\_\_**\*\*** TestDestructuring.test_rune_destructuring_valid **\*\***\_\_\_**\*\***

self = <tests.test_compiler_core.TestDestructuring object at 0x0000012A431D82D0>

    def test_rune_destructuring_valid(self):

>       check_ok(

            VEC2
            + "weave main into float:\n  let v as Vec2 is with x is 1.0, y is 2.0\n  let px, py is v\n  return px + py\n"
        )

tests\test_compiler_core.py:2651:

---

tests\conftest.py:94: in check_ok
return check(source, filename=filename, base_dir=base_dir)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\conftest.py:88: in check
checker.check(tree, source=source, filename=filename)

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x0000012A48BF5440>
tree = Tree(Token('RULE', 'start'), [Tree(Token('RULE', 'file'), [Tree(Token('RULE', 'top_stmt'), [Tree(Token('RULE', 'rune_d...turn_stmt'), [Tree('add', [Tree('var_ref', [Token('NAME', 'px')]), Tree('var_ref', [Token('NAME', 'py')])])])])])])])])
source = 'rune Vec2:\n x as float\n y as float\nweave main into float:\n let v as Vec2 is with x is 1.0, y is 2.0\n let px, py is v\n return px + py\n'
filename = 't.pengu', symbols = None, reset_symbols = True, import_order = None

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all

>           raise first_err
>
> E pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'

pengu_parser\pengu_checker.py:329: SemanticError
**\_\_** TestStringInterpolation.test_interpolation_format_string_emission **\_\_**

self = <tests.test_compiler_core.TestStringInterpolation object at 0x0000012A431F5BA0>

    def test_interpolation_format_string_emission(self):
        c = gen_bundle(
            'weave main into void:\n'
            '  let name is "player1"\n'
            '  let x is 10\n'
            '  let msg is "player {name} at {x}"\n'
        )

>       assert 'pengu_string_format("player %s at %d"' in c
>
> E assert 'pengu*string_format("player %s at %d"' in '/* Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...t*args()\' etc. */\n pengu_init(argc, argv);\n pengu_main();\n fflush(stdout);\n fflush(stderr);\n return 0;\n}\n'

tests\test_compiler_core.py:2694: AssertionError
**\_\_\_** TestCodegenEmissionArraysSlices.test_collection_emission_shapes **\_\_\_**

self = <tests.test_compiler_core.TestCodegenEmissionArraysSlices object at 0x0000012A431D91D0>

        def test_collection_emission_shapes(self):

>           c = gen_bundle(

                VEC2
                + """weave test_collections into void:
      let arr is array of int with size 10
      let first is arr at 0
      set arr at 0 is 99
      let part as slice of int is arr at 1 to 3
      let n is part length
      let evens is for x in arr when x % 2 == 0 then x
      let doubled is for x in arr then x * 2
      var vertices as list of Vec2 is list of Vec2 with capacity 100
      var lookup as map of int to Vec2 is map of int to Vec2
    """
            )

tests\test_compiler_core.py:2957:

---

tests\conftest.py:147: in gen_bundle
checker.check(tree, source=code, filename=fname)
pengu_parser\pengu_checker.py:329: in check
raise first_err

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x0000012A48C10C00>
node = Tree(Token('RULE', 'set_stmt'), [Tree(Token('RULE', 'set_target'), [Tree(Token('RULE', 'normal_target'), [Token('NAME', 'arr'), Tree('at_access', [Tree('int_lit', [Token('INT', '0')])])])]), Tree('int_lit', [Token('INT', '99')])])

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                while isinstance(with_t, RefType):
                    with_t = with_t.target
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (ArrayType, SliceType, ManyType, ListType)):
                                target_type = curr_t.element

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"

>                               raise self._make_error(

                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )

E pengu_parser.pengu_errors.MutabilityError: [line 7, col 7] Cannot mutate element of immutable 'let' variable 'arr'

pengu_parser\pengu_checker.py:3342: MutabilityError
**\_\_\_\_** TestCodegenEmissionArraysSlices.test_loop_and_index_emission \***\*\_\*\***

self = <tests.test_compiler_core.TestCodegenEmissionArraysSlices object at 0x0000012A431F63F0>

        def test_loop_and_index_emission(self):

>           c = gen_bundle(

                """weave loops_demo into void:
      var x as int is 0
      while x < 10:
        set x is x + 1
        if x == 5:
          continue
        if x == 9:
          break

      var arr as array of int with size 5 is [1, 2, 3, 4, 5]
      for i from 0 to 5:
        set arr at i is (arr at i) * 2

      let part as slice of int is arr at 1 to 4
      for i from 0 to part.len:
        set part at i is (part at i) + 10

      for num in arr:
        let doubled is num * 2

      var lst as list of int is list of int with capacity 10
      for i from 0 to 5:
        calling lst.push with i * 10
      for i from 0 to lst.len:
        set lst at i is (lst at i) + 100
    """
            )

tests\test_compiler_core.py:2989:

---

tests\conftest.py:147: in gen_bundle
checker.check(tree, source=code, filename=fname)
pengu_parser\pengu_checker.py:329: in check
raise first_err

---

self = <pengu_parser.pengu_checker.PenguChecker object at 0x0000012A48C128E0>
node = Tree(Token('RULE', 'set_stmt'), [Tree(Token('RULE', 'set_target'), [Tree(Token('RULE', 'normal_target'), [Token('NAME'...ar_ref', [Token('NAME', 'part')]), Tree('var_ref', [Token('NAME', 'i')])])]), Tree('int_lit', [Token('INT', '10')])])])

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                while isinstance(with_t, RefType):
                    with_t = with_t.target
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            curr_t = target_type
                            while isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            if isinstance(curr_t, (ArrayType, SliceType, ManyType, ListType)):
                                target_type = curr_t.element

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"

>                               raise self._make_error(

                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )

E pengu_parser.pengu_errors.MutabilityError: [line 16, col 9] Cannot mutate element of immutable 'let' variable 'part'

pengu_parser\pengu_checker.py:3342: MutabilityError
**\*\*\*\***\_\_**\*\*\*\*** TestIndexedFor.test_indexed_for_over_list **\*\*\*\***\_\_**\*\*\*\***

self = <tests.test_compiler_features.TestIndexedFor object at 0x0000012A43187DF0>

        def test_indexed_for_over_list(self):
            code = """weave test_for with nums as list of int into void:
      var acc as int is 0
      for i, v in nums:
        set acc is acc + i * v
    """
            c = gen_bundle(code)
            assert "for (int32_t i = 0; i < (nums).len; i++) {" in c

>           assert "int32_t v = (*(int32_t*)pengu_list_at(&(nums), i));" in c
>
> E assert 'int32*t v = (*(int32*t*)pengu*list_at(&(nums), i));' in '/* Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...;\n#line 4 "D:/a/PenguScript/PenguScript/t.pengu"\n acc = (acc + (i \_ v));\n }\n pengu_frame_pop();\n}\n\n#line 1'

tests\test*compiler_features.py:425: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_compiler_core.py::TestStructFieldAccess::test_valid_field_access - pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'
FAILED tests/test_compiler_core.py::TestStructFieldAccess::test_unknown_field_fails - AssertionError: error "[line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'" (codes ['E0020', 'E0013', 'E0020']) does not mention "has no field 'z'"
FAILED tests/test_compiler_core.py::TestEchoOmenSemantics::test_simple_enum_variants - pengu_parser.pengu_errors.SemanticError: [line 6, col 1] Entry point 'main' must return an integer or 'void', got 'string'
FAILED tests/test_compiler_core.py::TestCollectionsSemantics::test_array_slice_list_map_ops[weave main into void:\n let arr is array of int with size 10\n let first is arr at 0\n set arr at 0 is 99\n let part as slice of int is arr at 1 to 3\n let n is part length\n var l as list of int is list of int with capacity 10\n var m as map of int to string is map of int to string\n] - pengu_parser.pengu_errors.MutabilityError: [line 4, col 7] Cannot mutate element of immutable 'let' variable 'arr'
FAILED tests/test_compiler_core.py::TestMaybeResultOrError::test_maybe_decl_and_unwrap - pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'string'
FAILED tests/test_compiler_core.py::TestEnchantingSemantics::test_enchanting_methods_check[rune Vec2:\n x as float\n y as float\nenchanting Vec2:\n weave add with other as Vec2 into Vec2:\n Vec2 is with x is self->x + other.x, y is self->y + other.y\n\n weave length into float:\n (self->x * self->x + self->y * self->y) to float\n\n weave move with dx as float, dy as float into void:\n set self->x is self->x + dx\n set self->y is self->y + dy\n\nweave main into void:\n let a as Vec2 is with x is 10, y is 20\n let b as Vec2 is with x is 5, y is 5\n let c is calling a.add with b\n var d as Vec2 is a\n calling d.move with 10, 0\n] - pengu_parser.pengu_errors.ParseError: [line 6, col 13] Syntax error: unexpected 'with' at line 6, column 13
FAILED tests/test_compiler_core.py::TestDestructuring::test_rune_destructuring_valid - pengu_parser.pengu_errors.SemanticError: [line 4, col 1] Entry point 'main' must return an integer or 'void', got 'float'
FAILED tests/test_compiler_core.py::TestStringInterpolation::test_interpolation_format_string_emission - assert 'pengu_string_format("player %s at %d"' in '/* Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...t*args()\' etc. */\n pengu*init(argc, argv);\n pengu_main();\n fflush(stdout);\n fflush(stderr);\n return 0;\n}\n'
FAILED tests/test_compiler_core.py::TestCodegenEmissionArraysSlices::test_collection_emission_shapes - pengu_parser.pengu_errors.MutabilityError: [line 7, col 7] Cannot mutate element of immutable 'let' variable 'arr'
FAILED tests/test_compiler_core.py::TestCodegenEmissionArraysSlices::test_loop_and_index_emission - pengu_parser.pengu_errors.MutabilityError: [line 16, col 9] Cannot mutate element of immutable 'let' variable 'part'
FAILED tests/test_compiler_features.py::TestIndexedFor::test_indexed_for_over_list - assert 'int32_t v = (*(int32*t*)pengu*list_at(&(nums), i));' in '/* Auto-generated by PenguScript v0.13.7 _/\n#include "pengu_runtime.h"\n\n/_ Compiled modules in topological order:\...;\n#line 4 "D:/a/PenguScript/PenguScript/t.pengu"\n acc = (acc + (i \_ v));\n }\n pengu_frame_pop();\n}\n\n#line 1'
11 failed, 1002 passed, 3 skipped in 310.78s (0:05:10)
Error: Process completed with exit code 1.
