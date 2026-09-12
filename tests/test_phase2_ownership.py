"""Tests for Phase 2: Scope-owned locals and 'borrowed' modifier."""

import pytest
from tests.conftest import (
    check_ok,
    check_error,
    gen_bundle,
    compile_run,
    requires_cc,
    requires_runtime,
)


# ==========================================================================
# 1. Checker — Introspection and semantic checks
# ==========================================================================

def test_banish_on_auto_owned_errors():
    """Manual banish of an auto-owned local is an error (E0047)."""
    check_error(
        'weave f into void:\n  var s is "a" + "b"\n  banish s\n',
        contains="E0047",
    )


def test_banish_on_borrowed_errors():
    """Manual banish of a borrowed binding is an error (E0048)."""
    check_error(
        'weave f with src as string into void:\n  let borrowed v is src\n  banish v\n',
        contains="E0048",
    )




def test_borrowed_disables_auto_banish():
    """Borrowed variables are non-owning views and never auto-banished."""
    c = gen_bundle(
        'weave f with src as string into void:\n  var borrowed v is src\n  return\n',
    )
    assert "pengu_banish_string(&v)" not in c


def test_defer_banish_disables_auto_banish():
    """An explicit defer banish disables auto-banish (runs only once via defer)."""
    c = gen_bundle(
        'weave f into void:\n  var s is "a" + "b"\n  defer banish s\n  return\n',
    )
    assert c.count("pengu_banish_string(&s)") == 1


def test_return_of_string_disables_auto_banish():
    """Returning an owned string transfers ownership to caller, no auto-banish."""
    c = gen_bundle(
        'weave f into string:\n  var s is "a" + "b"\n  return s\n',
    )
    assert "pengu_banish_string(&s)" not in c


def test_list_push_disables_auto_banish():
    """Pushing an owned value into a collection transfers ownership."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var lst as list of string is list of string\n'
        '  var s is "a" + "b"\n'
        '  calling lst.push with s\n'
        '  return\n'
    )
    assert "pengu_banish_string(&s)" not in c
    assert "pengu_banish_list(&lst)" in c


def test_map_put_disables_auto_banish():
    """Putting an owned value into a map transfers ownership."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var m as map of string to string is map of string to string\n'
        '  var v is "a" + "b"\n'
        '  calling m.put with "k", v\n'
        '  return\n'
    )
    assert "pengu_banish_string(&v)" not in c


def test_set_field_disables_auto_banish():
    """Assigning an owned value to a struct field transfers ownership."""
    c = gen_bundle(
        'rune Holder:\n  name as string\n'
        'weave f into void:\n'
        '  var h as Holder is with name is "x"\n'
        '  var s is "a" + "b"\n'
        '  set h.name is s\n'
        '  return\n'
    )
    assert "pengu_banish_string(&s)" not in c


def test_alias_init_disables_auto_banish():
    """Initializing from an existing variable does not take ownership."""
    c = gen_bundle(
        'weave f with src as string into void:\n'
        '  var s is src\n'
        '  return\n'
    )
    assert "pengu_banish_string(&s)" not in c


def test_ref_type_not_auto_banished():
    """Pointers and references are not heap-owned and not auto-banished."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var i as int is 42\n'
        '  var p as ref to int is sigil of i\n'
        '  return\n'
    )
    assert "pengu_banish" not in c


def test_scalar_not_auto_banished():
    """Scalars are not heap-owned and not auto-banished."""
    c = gen_bundle('weave f into void:\n  var x as int is 42\n  return\n')
    assert "pengu_banish" not in c


def test_for_loop_binding_not_auto_banished():
    """For-loop iteration variables are views and not auto-banished."""
    c = gen_bundle(
        'weave f with xs as list of string into int:\n'
        '  for s in xs:\n'
        '    calling print with s\n'
        '  return 0\n'
    )
    assert "pengu_banish_string(&s)" not in c


def test_string_literal_init_not_auto_banished():
    """String literals point to static rodata and are not auto-banished."""
    c = gen_bundle('weave f into void:\n  var s is "literal"\n  return\n')
    assert "pengu_banish_string(&s)" not in c


def test_defer_banish_inside_if_disables_auto_banish():
    """Defer banish inside an if block disables auto-banish for the variable."""
    c = gen_bundle(
        'weave f with c as bool into int:\n'
        '  var s is "a" + "b"\n'
        '  if c:\n'
        '    defer banish s\n'
        '  return (s length)\n'
    )
    assert c.count("pengu_banish_string(&s);") == 1


def test_reassignment_inside_if_disables_auto_banish():
    """Reassigning a variable inside an if disables auto-banish."""
    c = gen_bundle(
        'weave f with c as bool into int:\n'
        '  var s is "a" + "b"\n'
        '  if c:\n'
        '    set s is "c" + "d"\n'
        '  return (s length)\n'
    )
    assert "pengu_banish_string(&s)" not in c


def test_borrowed_after_var_is_parse_error():
    """'borrowed' cannot be used as variable name immediately after var/let."""
    check_error(
        'weave f into void:\n  var borrowed is 5\n',
        contains="Syntax error",
    )


def test_borrowed_as_identifier_elsewhere_is_ok():
    """Outside var/let modifier position, borrowed is a normal identifier."""
    check_ok(
        'rune R:\n  borrowed as int\n'
        'weave f with borrowed as int into int:\n'
        '  return borrowed\n'
    )


# ==========================================================================
# 2. Codegen — Scope emission and control flow
# ==========================================================================

def test_banish_emitted_at_scope_end():
    """Auto-banish is emitted before returning or at scope exit."""
    c = gen_bundle(
        'weave f into int:\n  var s is "a" + "b"\n  return (s length)\n'
    )
    assert "pengu_banish_string(&s);" in c


def test_banish_emitted_in_if_branch():
    """Auto-banish is emitted inside the if block when declared inside it."""
    c = gen_bundle(
        'weave f with c as bool into int:\n'
        '  if c:\n'
        '    var s is "a" + "b"\n'
        '    return (s length)\n'
        '  return 0\n'
    )
    assert "pengu_banish_string(&s);" in c


def test_early_return_transfers_ownership():
    """Early return of the owned local transfers ownership without auto-banish."""
    c = gen_bundle(
        'weave f with c as bool into string:\n'
        '  var s is "a" + "b"\n'
        '  if c:\n'
        '    return s\n'
        '  return s\n'
    )
    assert c.count("pengu_banish_string(&s)") == 0


def test_break_emits_only_inner_scope_banish():
    """Break emits auto-banish for scopes internal to loop, not loop scope itself."""
    c = gen_bundle(
        'weave f into int:\n'
        '  for i from 0 to 3:\n'
        '    var outer is "o" + "1"\n'
        '    if (outer length) > 0:\n'
        '      var inner is "i" + "2"\n'
        '      if (inner length) > 0:\n'
        '        break\n'
        '  return 0\n'
    )
    assert c.count("pengu_banish_string(&inner);") >= 1
    assert "pengu_banish_string(&outer);" in c


def test_auto_banish_emitted_on_each_exit_path():
    """Auto-banish is emitted once on each exit path for variables in scope."""
    c = gen_bundle(
        'weave f with c as bool into int:\n'
        '  var s is "a" + "b"\n'
        '  if c:\n'
        '    return 0\n'
        '  return (s length)\n'
    )
    # Both paths exit the function, so both emit banish for s
    assert c.count("pengu_banish_string(&s);") == 2


def test_auto_banish_scoped_to_if_branch():
    """A variable declared inside an if branch is only banished on that branch."""
    c = gen_bundle(
        'weave f with c as bool into int:\n'
        '  if c:\n'
        '    var s is "a" + "b"\n'
        '    return 0\n'
        '  return 1\n'
    )
    assert c.count("pengu_banish_string(&s);") == 1


def test_auto_banish_lifo_order():
    """Auto-banishes are emitted in LIFO order (last declared, first freed)."""
    c = gen_bundle(
        'weave f into int:\n'
        '  var a is "x" + "1"\n'
        '  var b is "y" + "2"\n'
        '  return (a length) + (b length)\n'
    )
    idx_a = c.find("pengu_banish_string(&a)")
    idx_b = c.find("pengu_banish_string(&b)")
    assert idx_a != -1 and idx_b != -1
    assert idx_b < idx_a, "b must be freed before a (LIFO)"


# ==========================================================================
# 3. Runtime — Compile and Run (clean execution)
# ==========================================================================

@requires_cc
@requires_runtime
def test_loop_of_strings_runs_clean():
    """Loop creating auto-owned strings in each iteration runs cleanly."""
    src = (
        'weave main into int:\n'
        '  var total as int is 0\n'
        '  for i from 0 to 100:\n'
        '    var s is "item_" + (i to string)\n'
        '    set total is total + (s length)\n'
        '  return 0\n'
    )
    res = compile_run(src, tag="scope_owned_loop")
    assert res.returncode == 0


@requires_cc
@requires_runtime
def test_borrowed_does_not_crash():
    """Using a borrowed view does not cause crashes or double-frees."""
    src = (
        'weave f with src as string into int:\n'
        '  var borrowed v is src\n'
        '  return (v length)\n'
        'weave main into int:\n'
        '  var s is "hello world"\n'
        '  var len as int is calling f with s\n'
        '  if len == 11:\n'
        '    return 0\n'
        '  return 1\n'
    )
    res = compile_run(src, tag="borrowed_no_crash")
    assert res.returncode == 0


@requires_cc
@requires_runtime
def test_defer_banish_runs_exactly_once():
    """Explicit defer banish runs cleanly and exactly once."""
    src = (
        'weave main into int:\n'
        '  var s is "a" + "b"\n'
        '  defer banish s\n'
        '  calling print with s\n'
        '  return 0\n'
    )
    res = compile_run(src, tag="defer_banish_once")
    assert res.returncode == 0
    assert "ab" in res.stdout


def test_or_block_creates_own_auto_banish_scope():
    """Regresión: `or:` block bodies must auto-banish their own locals
    at the closing brace of the error-handler, not at the outer scope.
    Before the fix, the generated C contained a `pengu_banish_string(&s)`
    after the block where `s` was already out of scope."""
    c = gen_bundle(
        'weave may_fail into maybe int:\n'
        '  return some 1\n'
        'weave f into void:\n'
        '  var r is calling may_fail or:\n'
        '    var s is "a" + "b"\n'
        '    calling print with s\n'
        '  return\n'
    )
    assert c.count("pengu_banish_string(&s);") == 1
    idx_if = c.find("if (!pengu_result_is_ok")
    idx_banish = c.find("pengu_banish_string(&s);")
    assert idx_if != -1 and idx_banish != -1
    depth = 0
    idx_close = -1
    for i in range(idx_if, len(c)):
        if c[i] == '{':
            depth += 1
        elif c[i] == '}':
            depth -= 1
            if depth == 0:
                idx_close = i
                break
    assert idx_close != -1, "if (!ok) block not closed"
    assert idx_banish < idx_close, (
        "auto-banish must be emitted inside the or: block, "
        "not after it (would reference 's' outside its scope)"
    )


def test_let_or_block_creates_own_auto_banish_scope():
    """`let ... is expr or:` also auto-banishes locals inside error handler."""
    c = gen_bundle(
        'weave may_fail into maybe int:\n'
        '  return some 1\n'
        'weave f into void:\n'
        '  let r is calling may_fail or:\n'
        '    var s is "a" + "b"\n'
        '    calling print with s\n'
        '  return\n'
    )
    assert c.count("pengu_banish_string(&s);") == 1
    idx_if = c.find("if (!pengu_result_is_ok")
    idx_banish = c.find("pengu_banish_string(&s);")
    assert idx_if != -1 and idx_banish != -1
    depth = 0
    idx_close = -1
    for i in range(idx_if, len(c)):
        if c[i] == '{':
            depth += 1
        elif c[i] == '}':
            depth -= 1
            if depth == 0:
                idx_close = i
                break
    assert idx_close != -1, "if (!ok) block not closed"
    assert idx_banish < idx_close


@requires_cc
@requires_runtime
def test_or_block_runs_clean():
    """Compile+run: an or: block that declares a heap local must run without
    crashes and without leaks (ASan-less smoke: just must not abort)."""
    src = (
        'weave may_fail with x as int into maybe int:\n'
        '  if x > 0:\n'
        '    return some x\n'
        '  return maybe none\n'
        'weave main into int:\n'
        '  var v is calling may_fail with 1 or:\n'
        '    var s is "err" + "or"\n'
        '    calling print with s\n'
        '  return 0\n'
    )
    res = compile_run(src, tag="or_block_auto_banish")
    assert res.returncode == 0


def test_struct_init_escapes_disables_auto_banish():
    """Embedding an owned variable into a struct literal transfers ownership, disabling auto-banish."""
    c = gen_bundle(
        'rune Task:\n'
        '  s as string\n'
        'weave f into void:\n'
        '  var sp is "hello" + "world"\n'
        '  var t as Task is with s is sp\n'
        '  return\n'
    )
    assert "pengu_banish_string(&sp)" not in c


def test_list_lit_escapes_disables_auto_banish():
    """Embedding an owned variable into a list literal transfers ownership, disabling auto-banish."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var s is "hello" + "world"\n'
        '  var xs is [s]\n'
        '  return\n'
    )
    assert "pengu_banish_string(&s)" not in c


def test_aliased_var_decl_escapes_disables_auto_banish():
    """Aliasing an owned variable into another local transfers/shares ownership, disabling auto-banish on the source."""
    c = gen_bundle(
        'weave f into void:\n'
        '  var s is "hello" + "world"\n'
        '  var b is s\n'
        '  return\n'
    )
    assert "pengu_banish_string(&s)" not in c

