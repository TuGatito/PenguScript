"""Roadmap Phase 2 / §2.2.c — attribute mapping per target compiler (text pins).

GNU/Clang/TCC keep `__attribute__`; MSVC gets `__declspec` and the pack pragma.

This file is deliberately a *text* suite: it unit-tests the dialect mapper by
pinning the exact spelling it produces for each target. It was renamed from
`test_attributes_msvc.py` by roadmap Phase 8 item 8.1 (blocker B10), because it
used to be presented as the MSVC gate while never invoking a compiler — and it
passed for years while the MSVC output was `int32_t head __declspec(align(8));`,
which `cl.exe`/clang-MS reject. The *compiler* gate now lives next to it in
`tests/test_attributes_msvc_native.py`.
"""

from tests.conftest import gen_bundle

_SRC = """\
@inline
weave add with a as int, b as int into int:
  a + b

@cold
weave log_error with code as int:
  var x is code

@deprecated("use modern instead")
weave old into int:
  42

@packed
rune Packet:
  tag as int
  length as int

@align(16)
rune Aligned:
  @align(8)
  head as int

weave main into int:
  var p as Packet is with tag is 1, length is 2
  var a as Aligned is with head is 0
  return calling add with p.tag, a.head
"""


def test_msvc_attribute_mapping():
    c = gen_bundle(_SRC, target_compiler="msvc")
    assert "__forceinline" in c
    assert "#pragma pack(push, 1)" in c
    assert "#pragma pack(pop)" in c
    assert "__declspec(align(16))" in c
    assert '__declspec(deprecated("use modern instead"))' in c
    # No GNU attributes must survive in MSVC output.
    assert "__attribute__((packed))" not in c
    assert "__attribute__((cold))" not in c
    assert "always_inline" not in c


def test_gnu_attribute_mapping_unchanged():
    c = gen_bundle(_SRC, target_compiler="gcc")
    assert "static inline __attribute__((always_inline))" in c
    assert "__attribute__((cold))" in c
    assert 'deprecated("use modern instead")' in c
    assert "struct __attribute__((packed)) Packet" in c
    assert "aligned(16)" in c
    assert "aligned(8)" in c
    assert "__declspec" not in c
    assert "#pragma pack" not in c
