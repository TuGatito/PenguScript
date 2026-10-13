"""`std.arithmancy` — the geometric types still work.

The refactor only touched the scalar helpers; `Vec2`/`Vec3`/`Vec4`/`Mat4`/`Quat`
must be unchanged. These are smoke tests that would catch a broken import or a
collateral rename.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.arithmancy

weave eq_f with got as float, want as float, eps as float, name as string into void:
    var d as float is got - want
    if d < 0.0:
        set d is 0.0 - d
    if d > eps:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_vec2_and_vec3(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var v as arithmancy.Vec2 is with x is 3.0, y is 4.0
    calling eq_f with (calling v.length), 5.0, 1e-6, "Vec2.length"
    calling eq_f with (calling v.length_sq), 25.0, 1e-6, "Vec2.length_sq"
    var w as arithmancy.Vec2 is with x is 1.0, y is 0.0
    var d as float is calling v.dot with w
    calling eq_f with d, 3.0, 1e-6, "Vec2.dot"
    var c as float is calling v.cross_2d with w
    calling eq_f with c, -4.0, 1e-6, "Vec2.cross_2d"
    var sum_v as arithmancy.Vec2 is calling v.add with w
    calling eq_f with sum_v.x, 4.0, 1e-6, "Vec2.add x"
    var a3 as arithmancy.Vec3 is with x is 0.0, y is 3.0, z is 4.0
    calling eq_f with (calling a3.length), 5.0, 1e-6, "Vec3.length"
    var b3 as arithmancy.Vec3 is with x is 1.0, y is 0.0, z is 0.0
    var cross3 as arithmancy.Vec3 is calling a3.cross with b3
    calling eq_f with cross3.x, 0.0, 1e-6, "Vec3.cross x"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_mat4_and_quat(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var m as arithmancy.Mat4 is calling arithmancy.mat4_identity
    var v as arithmancy.Vec3 is with x is 1.0, y is 2.0, z is 3.0
    var moved as arithmancy.Vec3 is calling m.transform_point with v
    calling eq_f with moved.x, 1.0, 1e-6, "identity x"
    calling eq_f with moved.y, 2.0, 1e-6, "identity y"
    calling eq_f with moved.z, 3.0, 1e-6, "identity z"
    var t as arithmancy.Mat4 is calling arithmancy.mat4_translate with 1.0, 2.0, 3.0
    var p as arithmancy.Vec3 is calling t.transform_point with v
    calling eq_f with p.x, 2.0, 1e-6, "translate x"
    var q as arithmancy.Quat is calling arithmancy.quat_identity
    calling eq_f with (calling q.length), 1.0, 1e-6, "Quat.length"
    var axis as arithmancy.Vec3 is with x is 0.0, y is 0.0, z is 1.0
    var rot as arithmancy.Quat is calling arithmancy.quat_from_axis_angle with axis, arithmancy.HALF_PI
    var spun as arithmancy.Vec3 is calling rot.rotate_vector with v
    calling eq_f with spun.x, -2.0, 1e-5, "Quat.rotate_vector x"
    calling eq_f with spun.y, 1.0, 1e-5, "Quat.rotate_vector y"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
