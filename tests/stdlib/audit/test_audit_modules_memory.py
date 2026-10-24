"""ASan gate for the modules added to close the self-hosting audit gaps.

Run with the sanitizer flags documented in ``test_leaks_comprehensive.py``:

    PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all" \
    PENGU_LDFLAGS="-fsanitize=address,undefined" \
    ASAN_OPTIONS="detect_leaks=1:halt_on_error=1:abort_on_error=1" \
    python -m pytest tests/stdlib/audit/test_audit_modules_memory.py -q -n 0

Without the flags the program still runs; it simply no longer proves the
absence of leaks.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


def test_digest_toml_yaml_process_are_leak_free(compile_and_run):
    out = compile_and_run("""
import std.digest
import std.toml
import std.yaml
import std.rites
import std.spark

weave main into int:
    var i as int is 0
    while i < 100:
        var h as string is calling digest.sha256_hex with "abc"
        banish h
        var raw as string is calling digest.sha256_raw with "abc"
        banish raw

        let doc as result of list of toml.TomlEntry to string is calling toml.parse with "name = \\"demo\\"\\narr = [1, 2, 3]\\n"
        if doc.is_ok:
            calling toml.free_entries with doc.value
        var text as string is calling toml.stringify with (list of toml.TomlEntry)
        banish text

        let ydoc as result of list of yaml.YamlEntry to string is calling yaml.parse with "a:\\n  b: c\\n"
        if ydoc.is_ok:
            calling yaml.free_entries with ydoc.value
        set i is i + 1

    var args as list of string is ["-c", "printf out; printf err >&2; exit 0"]
    set i is 0
    while i < 5:
        var r as rites.ProcessResult is calling rites.run_capture_all with "sh", args
        banish r.stdout
        banish r.stderr
        set i is i + 1

    calling spark.println with "DONE"
    return 0
""", timeout=240)
    assert "DONE" in out, out
