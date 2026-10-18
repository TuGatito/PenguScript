"""Generated-C checks for ``std.json``/``std.diagnostic``/``std.jsonrpc``.

Three properties are checked here rather than in the behaviour tests:

* the bundle compiles with every available C compiler under
  ``-Wall -Wextra -Werror`` (this suite found the nested-variant initializer
  and the derived-``Par`` container bugs while 2.10.0 was being built);
* ``JsonValue``'s derived ``Nexus`` is genuinely recursive, i.e. the array and
  object cases loop over their elements and call the element destructor;
* an adversarial parser corpus never crashes (every input is a ``result``).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

_SOURCE = r'''
import std.spark
import std.json
import std.diagnostic as diag
import std.jsonrpc as rpc

weave main into int:
    var pr as result of JsonValue to json.JsonError is calling json.parse with r"""{"a":[1,{"b":[true,null,"ñ😀"]}],"c":1.5}"""
    if not pr.is_ok:
        calling spark.println with "FAIL parse"
        banish pr
        return 1
    var root as JsonValue is pr.value
    var text as string is calling json.stringify with root
    var back as result of JsonValue to json.JsonError is calling json.parse with text
    if back.is_ok:
        var bv as JsonValue is back.value
        if not calling root.equals with bv:
            calling spark.println with "FAIL roundtrip"
    banish back
    banish text
    banish root
    banish pr

    var bag as DiagnosticBag is calling DiagnosticBag.new
    calling bag.add_source with "x.pengu", "one\ntwo\n"
    var span as Span is calling diag.span_from_positions with "x.pengu", 2, 1, 2, 4, 4, 7
    calling bag.add with (calling diag.diagnostic with diag.Severity.Error, "E1", "boom", (calling diag.labels with (calling diag.label with span, "here", true)), (some "fix"), (some "why"), (calling diag.no_related))
    var rendered as string is calling bag.render_json
    banish rendered
    banish bag

    var id as JsonRpcId is with Number is 1
    var msg as JsonRpcMessage is calling rpc.request with id, "m", (maybe none)
    var wire as string is calling rpc.encode_framed with msg
    banish wire
    banish msg
    calling spark.println with "DONE"
    return 0
'''

_ADVERSARIAL = r'''
import std.spark
import std.json

weave try_one with s as string into void:
    var r as result of JsonValue to json.JsonError is calling json.parse with s
    if r.is_ok:
        calling spark.println with "FAIL accepted: {s}"
    banish r

weave main into int:
    calling try_one with ""
    calling try_one with "["
    calling try_one with "{"
    calling try_one with "01"
    calling try_one with "1."
    calling try_one with "\"\\uD800\""
    calling try_one with "\"\\uDC00\""
    calling try_one with "\"\\uZZZZ\""
    calling try_one with r"""{"a":}"""
    calling try_one with "[1,,2]"
    calling try_one with "nul"
    calling try_one with "tru"
    calling try_one with r"""{"a":1}{}"""
    var raw as array of byte with size 3 is [34, 255, 34]
    var sr as slice of byte is raw at 0 to 3
    var br as result of JsonValue to json.JsonError is calling json.parse_bytes with sr
    if br.is_ok:
        calling spark.println with "FAIL invalid utf8 accepted"
    banish br
    calling spark.println with "DONE"
    return 0
'''


def _build(pengu_cli, tmp_path, source: str, name: str) -> str:
    src = tmp_path / f"{name}.pengu"
    src.write_text(source, encoding="utf-8")
    bundle = tmp_path / f"{name}.c"
    res = pengu_cli("build", "--entry", str(src), "--output", str(bundle))
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    return bundle.read_text(encoding="utf-8")


def _compile(bundle_text: str, tmp_path, cc: str) -> None:
    c_path = tmp_path / "bundle.c"
    c_path.write_text(bundle_text, encoding="utf-8")
    res = subprocess.run(
        [cc, "-c", str(c_path), "-o", str(tmp_path / "out.o"),
         "-O0", "-std=c11", "-Wall", "-Wextra", "-Werror",
         "-Wno-unused-function",
         "-I", str(ROOT), "-I", str(ROOT / "build" / "include")],
        capture_output=True, text=True, timeout=600,
    )
    assert res.returncode == 0, f"{cc} rejected the bundle:\n{res.stdout}\n{res.stderr}"


def test_bundle_compiles_cleanly_with_every_compiler(pengu_cli, tmp_path):
    c = _build(pengu_cli, tmp_path, _SOURCE, "json_stack")
    compilers = [p for p in (shutil.which("gcc"), shutil.which("clang")) if p]
    if not compilers:
        pytest.skip("no C compiler available")
    for cc in compilers:
        _compile(c, tmp_path, cc)


def test_json_value_nexus_is_recursive(pengu_cli, tmp_path):
    c = _build(pengu_cli, tmp_path, _SOURCE, "json_nexus")
    assert "JsonValue_nexus" in c
    body = c.split("static inline void JsonValue_nexus(void *p) {", 1)[1]
    arr_case = body.split("case JsonValue_Arr:", 1)[1].split("case JsonValue_Obj:", 1)[0]
    assert "_pengu_cleanup_JsonValue" in arr_case, arr_case
    assert "pengu_banish_list" in arr_case, arr_case
    obj_case = body.split("case JsonValue_Obj:", 1)[1].split("default:", 1)[0]
    assert "_pengu_cleanup_JsonEntry" in obj_case, obj_case
    assert "pengu_banish_list" in obj_case, obj_case


def test_adversarial_inputs_return_errors(pengu_cli, tmp_path):
    c = _build(pengu_cli, tmp_path, _ADVERSARIAL, "json_adversarial")
    compilers = [p for p in (shutil.which("gcc"), shutil.which("clang")) if p]
    if not compilers:
        pytest.skip("no C compiler available")
    cc = compilers[0]
    c_path = tmp_path / "adv.c"
    c_path.write_text(c, encoding="utf-8")
    exe = tmp_path / "adv"
    res = subprocess.run(
        [cc, str(c_path), "-o", str(exe), "-O0", "-std=c11",
         "-I", str(ROOT), "-I", str(ROOT / "build" / "include"),
         "-L", str(ROOT / "build" / "lib"), "-Wl,--start-group",
         "-lpengu_runtime", "-pthread", "-lm", "-ldl", "-Wl,--end-group"],
        capture_output=True, text=True, timeout=600,
    )
    assert res.returncode == 0, f"{res.stdout}\n{res.stderr}"
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, f"{run.stdout}\n{run.stderr}"
    assert "DONE" in run.stdout, run.stdout
    assert "FAIL" not in run.stdout, run.stdout
