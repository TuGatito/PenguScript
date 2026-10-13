"""Phase 2 — the shape of the emitted C.

No C compiler here: every assertion is a substring of the generated bundle.  The
contract is small and worth pinning exactly, because it is the whole point of
the feature (zero overhead, no boxing, no vtables):

* a primitive method is `<tname>_<method>(<c_type> self, …)` — never `T* self`;
* the call site passes the receiver *by value* — never `&x`;
* a `shard T` method is monomorphized once per primitive (`int_is_even`,
  `i64_is_even`) and no generic body survives into the C.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.smoke


def test_codegen_no_ampersand_on_self(emit_c):
    c = emit_c("""
enchanting int:
    weave clamp with lo as int, hi as int into int:
        if self < lo:
            return lo
        if self > hi:
            return hi
        return self
""")
    assert "int32_t int_clamp(int32_t self," in c
    assert "int32_t* self" not in c
    assert "&self" not in c


def test_call_site_no_ampersand(emit_c):
    c = emit_c("""
enchanting int:
    weave double into int:
        return self + self

weave main into int:
    var x as int is 21
    var y as int is calling x.double
    return y
""")
    assert "int_double(x)" in c
    assert "int_double(&x)" not in c


def test_chained_primitive_call_passes_the_temporary_by_value(emit_c):
    """`calling x.abs.double`: the receiver of the second call is a temporary, so
    it must be passed by value -- there is no storage to take the address of."""
    c = emit_c("""
enchanting int:
    weave abs into int:
        return self
    weave double into int:
        return self + self

weave main into int:
    var x as int is 4
    return calling x.abs.double
""")
    assert "int_double(" in c
    assert "int_double(&" not in c
    assert "&" not in c.split("int_double(")[1].split(")")[0]


def test_method_named_like_a_c_keyword_keeps_the_suffix_form(emit_c):
    """`int_double`, not `int__double`: the method name is a suffix, never a
    standalone identifier, so the C-keyword escape must not apply."""
    c = emit_c("""
enchanting int:
    weave double into int:
        return self + self
""")
    assert "int32_t int_double(" in c
    assert "int__double" not in c


def test_shard_monomorphization(emit_c):
    c = emit_c("""
enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % (2 to T)) == donum T

weave check with a as int, b as i64 into bool:
    if calling a.is_even:
        return calling b.is_even
    return false
""")
    assert "bool int_is_even(int32_t self)" in c
    assert "bool i64_is_even(int64_t self)" in c
    # The generic template itself must never reach the C.
    assert "_is_even(T" not in c
    assert "(T)" not in c


def test_shard_monomorphization_is_transitive(emit_c):
    """`is_odd` calls `self.is_even`; monomorphizing the caller must pull in the
    callee, or the emitted body calls a function that is never defined."""
    c = emit_c("""
enchanting shard T where T: Integrum:
    weave is_even into bool:
        return (self % (2 to T)) == donum T
    weave is_odd into bool:
        return not calling self.is_even

weave main into int:
    var a as int is 3
    if calling a.is_odd:
        return 1
    return 0
""")
    assert "bool int_is_odd(int32_t self)" in c
    assert "bool int_is_even(int32_t self)" in c
    assert "int_is_even(self)" in c


def test_primitive_method_returns_the_value_not_a_pointer(emit_c):
    c = emit_c("""
enchanting char:
    weave to_upper into char:
        return self
""")
    assert "char char_to_upper(char self)" in c
    assert "char* char_to_upper" not in c


def test_bool_and_float_naming(emit_c):
    c = emit_c("""
enchanting bool:
    weave to_int into int:
        if self:
            return 1
        return 0

enchanting float:
    weave round_me into float:
        return self

enchanting f64:
    weave round_me into f64:
        return self
""")
    assert "int32_t bool_to_int(bool self)" in c
    assert "float float_round_me(float self)" in c
    assert "double f64_round_me(double self)" in c


def test_alias_spelling_emits_the_canonical_symbol(emit_c):
    """`enchanting int32_t:` must emit `int_…`: it *is* the same C type, and a
    `int32_t_f` symbol would collide with nothing while duplicating everything."""
    c = emit_c("""
enchanting int32_t:
    weave double into int:
        return self + self

weave main into int:
    var x as i32 is 21
    return calling x.double
""")
    assert "int_double(int32_t self)" in c
    assert "int32_t_double" not in c
    assert "int_double(x)" in c


def test_ref_receiver_is_dereferenced(emit_c):
    """A `ref to int` receiver is a pointer, but the method takes the value."""
    c = emit_c("""
enchanting int:
    weave double into int:
        return self + self

weave f with p as ref to int into int:
    return calling p.double
""")
    assert "int_double((*p))" in c
    assert "int_double(p)" not in c


def test_rune_method_still_takes_a_pointer(emit_c):
    """The value rule is for primitives only: a rune method keeps `T* self`."""
    c = emit_c("""
rune Player:
    hp as int
enchanting Player:
    weave heal with amount as int into void:
        set self->hp is self->hp + amount
""")
    assert "Player* self" in c


def test_concept_binding_on_a_primitive_keeps_the_pointer_receiver(emit_c):
    """`bind int with C:` is *not* `enchanting int:`.

    A concept implementation on a primitive is the established shape in
    `std/atlas.pengu` (`bind int with Ordered:`), where `self` is `ref to int`
    and the body dereferences it (`essence of self`).  The value rule belongs to
    `enchanting` only, so this must keep `T* self` and `&x` at the call site --
    deriving the receiver from the type instead of from the declaration broke
    every stdlib bench when the feature landed.
    """
    c = emit_c("""
concept Cmp:
    weave cmp with other as int into int

bind int with Cmp:
    weave cmp with other as int into int:
        var me as int is essence of self
        if me > other:
            return 1
        return 0

weave f with a as int, b as int into int:
    return calling a.cmp with b
""")
    assert "int32_t _int_cmp(int32_t* self" in c
    assert "_int_cmp(&a, b)" in c
    assert "*self" in c


def test_one_spelling_of_a_primitive_can_still_be_bound_alone(emit_c):
    """`bind i32 with C:` is reachable through an `int32_t`/`int` receiver.

    `i32` and `int32_t` are one C type, so a declaration under either spelling has
    to be found from the other; the canonical spelling is only a *preference*.
    """
    c = emit_c("""
concept Cmp:
    weave cmp with other as i32 into int

bind i32 with Cmp:
    weave cmp with other as i32 into int:
        return 0

weave f with a as int32_t into int:
    return calling a.cmp with 1
""")
    assert "int32_t i32_cmp(int32_t* self" in c
    assert "i32_cmp(&a, 1)" in c


def test_enchanting_and_bind_on_the_same_primitive_coexist(emit_c):
    """A value method and a concept implementation do not collide: the bind keeps
    its own symbol (`_int_cmp`), the enchanting method uses the canonical one."""
    c = emit_c("""
concept Cmp:
    weave cmp with other as int into int

bind int with Cmp:
    weave cmp with other as int into int:
        return 0

enchanting int:
    weave double into int:
        return self + self

weave f with a as int into int:
    return calling a.double + (calling a.cmp with 1)
""")
    assert "int32_t int_double(int32_t self" in c
    assert "int32_t _int_cmp(int32_t* self" in c
    assert "int_double(a)" in c
    assert "_int_cmp(&a, 1)" in c


def test_monomorphized_tuple_return_gets_its_struct(emit_c):
    """A `(T, T)`-returning shard method needs its product struct defined.

    Regression: the monomorphized-weave collector registered the weave but not
    the tuple type, so the bundle named `_pengu_tup_tup_int_int` without ever
    emitting the typedef (`cc` then failed with "unknown type name").
    """
    c = emit_c("""
enchanting shard T where T: Integrum:
    weave div_rem with other as T into (T, T):
        return (self / other), (self % other)

weave use with a as int, b as i64 into int:
    let (q, r) is calling a.div_rem with 3
    let (s, t) is calling b.div_rem with 3
    return (q + r) + ((s + t) to int)
""")
    assert "typedef struct" in c
    assert "_pengu_tup_tup_int_int" in c
    assert "_pengu_tup_tup_i64_i64" in c
    # The struct must be *defined*, not merely referenced.
    assert "struct _pengu_tup_tup_int_int {" in c
    assert "typedef struct _pengu_tup_tup_int_int _pengu_tup_tup_int_int;" in c


def test_transitive_monomorphization_follows_local_receivers(emit_c):
    """A shard body that calls another shard method on a *local* of type `T`
    must monomorphize that callee for every receiver too.

    Regression: the transitive scan only looked at `calling self.method`, so
    `gcd` (`calling a.abs`) and `next_prime` (`calling n._is_prime_impl`) emitted
    a call to `i16_abs` / `u32__is_prime_impl` that was never defined.
    """
    c = emit_c("""
enchanting shard T where T: Integrum:
    weave helper into bool:
        return self > donum T
    weave via_local into bool:
        var n as T is self
        return calling n.helper

weave use with a as int, b as i16 into bool:
    if calling a.via_local:
        return calling b.via_local
    return false
""")
    for symbol in ("int_helper", "i16_helper", "int_via_local", "i16_via_local"):
        assert symbol in c, f"{symbol} missing from the bundle"


def test_f64_literal_keeps_double_precision(emit_c):
    """`as f64` must deliver 64-bit precision (LANGUAGE.md §4.1).

    Regression: `_format_const_val` appended the `f` suffix to every foldable
    float literal, so `var pi as f64 is 3.141592653589793` emitted
    `double pi = 3.141592653589793f;` -- the single-precision value promoted to
    double, silently dropping 29 bits of mantissa.
    """
    c = emit_c("""
weave main into int:
    var wide as f64 is 3.141592653589793
    var alias as double is 3.141592653589793
    var narrow as float is 3.141592653589793
    var narrow_alias as f32 is 3.141592653589793
    return 0
""")
    assert "double wide = 3.141592653589793;" in c
    assert "double alias = 3.141592653589793;" in c
    assert "float narrow = 3.141592653589793f;" in c
    assert "float narrow_alias = 3.141592653589793f;" in c
    # Exactly the two single-precision variables carry the suffix.
    assert c.count("3.141592653589793f") == 2


def test_cast_to_f64_keeps_double_precision(emit_c):
    """`3.141592653589793 to f64` is a double literal, not a float one."""
    c = emit_c("""
weave main into int:
    var wide as f64 is (3.141592653589793 to f64)
    var narrow as f32 is (3.141592653589793 to f32)
    return 0
""")
    assert "((double)(3.141592653589793))" in c
    assert "((float)(3.141592653589793f))" in c


def test_real_bound_literal_follows_the_monomorphized_width(emit_c):
    """A `T: Real` body that writes `3.14 to T` must not bake in float width.

    The cast target is substituted per concrete receiver, so the `f64`
    monomorphization has to use the double literal and the `float` one the
    single-precision literal.
    """
    c = emit_c("""
enchanting shard T where T: Real:
    weave half_pi into T:
        return (3.141592653589793 to T) / (2.0 to T)

weave use_f64 with a as f64 into f64:
    return calling a.half_pi

weave use_f32 with b as float into float:
    return calling b.half_pi
""")
    assert "double f64_half_pi(double self)" in c
    assert "float float_half_pi(float self)" in c
    # The double body keeps every digit; the float body is single precision.
    assert "((double)(3.141592653589793))" in c
    assert "((float)(3.141592653589793f))" in c
