"""Regression tests for the stdlib gaps named in the self-hosting audit.

These are end-to-end: the compiler must parse the module, generate C, link the
runtime and run the result.  They cover B3 (process capture), B4 (binary stdio
and sockets), B5 (SHA-256/TOML/YAML) and the byte-exact behaviour behind B10/B11.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_CLI_NOISE = ("Scripting", "Compiling", "Building", "Linking", "Finished", "Running", "Cached", "Testing")


def _run_source(tmp_path: Path, source: str, *, stdin_data: bytes | None = None,
                timeout: int = 120) -> subprocess.CompletedProcess:
    script = tmp_path / "case.pengu"
    script.write_text(source, encoding="utf-8")
    if stdin_data is None:
        return subprocess.run(
            [sys.executable, str(ROOT / "pengu_project.py"), "run", "--ephemeral", str(script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(tmp_path),
            env={**os.environ, "PYTHONPATH": str(ROOT)},
        )
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "run", "--ephemeral", str(script)],
        input=stdin_data,
        capture_output=True,
        text=False,
        timeout=timeout,
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    return subprocess.CompletedProcess(
        res.args, res.returncode,
        res.stdout.decode("utf-8", errors="replace"),
        res.stderr.decode("utf-8", errors="replace"),
    )


def _clean_stdout(stdout: str) -> str:
    return "\n".join(line for line in stdout.splitlines() if not line.strip().startswith(_CLI_NOISE))


def test_b3_run_capture_all_keeps_stdout_stderr_and_exit_code(compile_and_run):
    out = compile_and_run("""
import std.rites
import std.spark

weave main into int:
    var args as list of string is ["-c", "printf out; printf err >&2; exit 3"]
    var r as rites.ProcessResult is calling rites.run_capture_all with "sh", args
    calling spark.println with r.stdout
    calling spark.println with r.stderr
    calling spark.println_int with r.code
    banish r.stdout
    banish r.stderr
    return 0
""")
    assert out.strip().splitlines() == ["out", "err", "3"]


def test_b4_binary_stdio_preserves_nul_and_exact_length(tmp_path):
    source = """
import std.io
import std.spark

weave main into int:
    let all as string is calling io.read_stdin_all
    calling spark.println_int with all length
    calling spark.println_int with (ord (all at 1))
    calling io.write_stdout with all
    calling io.flush_stdout
    banish all
    return 0
"""
    res = _run_source(tmp_path, source, stdin_data=b"A\x00B\n")
    assert res.returncode == 0, res.stderr + res.stdout
    lines = _clean_stdout(res.stdout).strip().splitlines()
    assert lines[0] == "4"
    assert lines[1] == "0"
    # The raw bytes survive the round-trip (the trailing newline is stripped by
    # splitlines, so assert on the captured stdout prefix instead).
    assert "A\x00B" in res.stdout


def test_b4_read_stdin_exact_reports_short_read(tmp_path):
    source = """
import std.io
import std.spark

weave main into int:
    let m as maybe string is calling io.read_stdin_exact with 4
    if m is present:
        calling spark.println with m.value
        banish m
    else:
        calling spark.println with "short"
    return 0
"""
    res = _run_source(tmp_path, source, stdin_data=b"ab")
    assert res.returncode == 0, res.stderr + res.stdout
    assert "short" in res.stdout


def test_b4_tcp_listen_accept_read_write(tmp_path):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    received: list[bytes] = []

    def _serve() -> None:
        try:
            conn, _ = server.accept()
            with conn:
                data = conn.recv(1024)
                received.append(data)
                conn.sendall(b"pong")
        finally:
            server.close()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    try:
        res = _run_source(tmp_path, f"""
import std.net
import std.spark

weave main into int:
    let c as result of net.Socket to string is calling net.connect with "127.0.0.1", {port}
    if c.is_ok:
        calling net.write with (sigil of c.value), "ping"
        let reply as maybe string is calling net.read_exact with (sigil of c.value), 4
        if reply is present:
            calling spark.println with reply.value
            banish reply
        calling net.close with (sigil of c.value)
    else:
        calling spark.println with c.error
    return 0
""")
    finally:
        thread.join(timeout=5)
    assert res.returncode == 0, res.stderr + res.stdout
    assert received == [b"ping"]
    assert "pong" in res.stdout


def test_b5_sha256_known_vectors_and_file(compile_and_run, tmp_path):
    payload = tmp_path / "payload.txt"
    payload.write_bytes(b"abc")
    out = compile_and_run(f"""
import std.digest
import std.spark

weave main into int:
    let a as string is calling digest.sha256_hex with "abc"
    calling spark.println with a
    banish a
    let e as string is calling digest.sha256_hex with ""
    calling spark.println with e
    banish e
    let f as maybe string is calling digest.sha256_file with "{payload}"
    if f is present:
        calling spark.println with f.value
        banish f
    return 0
""")
    lines = out.strip().splitlines()
    assert lines[0] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert lines[1] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert lines[2] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_b5_toml_parse_and_stringify_roundtrip(compile_and_run):
    out = compile_and_run("""
import std.toml
import std.spark

weave main into int:
    var text as string is "[project]\\nname = \\"demo\\"\\n\\n[build]\\nlinks = [\\"m\\", \\"c\\"]\\n\\n[[package]]\\nname = \\"leaf\\"\\n"
    let doc as result of list of toml.TomlEntry to string is calling toml.parse with text
    if doc.is_ok:
        calling spark.println with (calling toml.get with doc.value, "project.name")
        var links as list of string is calling toml.get_array with doc.value, "build.links"
        for l in links:
            calling spark.println with l
            banish l
        banish links
        calling spark.println with (calling toml.get with doc.value, "package[0].name")
        let rendered as string is calling toml.stringify with doc.value
        calling spark.println with rendered
        banish rendered
        calling toml.free_entries with doc.value
    else:
        calling spark.println with doc.error
    return 0
""")
    lines = out.strip().splitlines()
    assert lines[0] == "demo"
    assert lines[1] == "m"
    assert lines[2] == "c"
    assert lines[3] == "leaf"
    rendered = "\n".join(lines[4:])
    assert 'links = ["m", "c"]' in rendered
    assert "[[package]]" in rendered


def test_b5_toml_rejects_malformed_input(compile_and_run):
    out = compile_and_run("""
import std.toml
import std.spark

weave main into int:
    let doc as result of list of toml.TomlEntry to string is calling toml.parse with "name = [1,"
    if not doc.is_ok:
        calling spark.println with "error"
    return 0
""")
    assert out.strip() == "error"


def test_b5_yaml_legacy_subset(compile_and_run):
    out = compile_and_run("""
import std.yaml
import std.spark

weave main into int:
    var text as string is "project:\\n  name: demo\\n  version: \\"0.1.0\\"\\nbuild:\\n  links: [\\"m\\", c]\\n"
    let doc as result of list of yaml.YamlEntry to string is calling yaml.parse with text
    if doc.is_ok:
        calling spark.println with (calling yaml.get with doc.value, "project.name")
        calling spark.println with (calling yaml.get with doc.value, "project.version")
        var links as list of string is calling yaml.get_array with doc.value, "build.links"
        for l in links:
            calling spark.println with l
            banish l
        banish links
        calling yaml.free_entries with doc.value
    else:
        calling spark.println with doc.error
    return 0
""")
    assert out.strip().splitlines() == ["demo", "0.1.0", "m", "c"]


def test_b4_spark_read_line_has_no_4096_byte_limit(tmp_path):
    payload = ("x" * 9000).encode() + b"\n"
    source = """
import std.spark

weave main into int:
    let line as string is calling spark.read_line
    calling spark.println_int with line length
    banish line
    return 0
"""
    res = _run_source(tmp_path, source, stdin_data=payload)
    assert res.returncode == 0, res.stderr + res.stdout
    lines = _clean_stdout(res.stdout).strip().splitlines()
    assert lines[-1] == "9000"


def test_b5_toml_edge_syntax_and_nested_arrays(compile_and_run):
    out = compile_and_run('''
import std.toml
import std.spark

weave main into int:
    var text as string is r"""# comment
title = "TOML Example"
[owner]
name = 'Tom'
dob = 1979-05-27T07:32:00Z
[database]
ports = [8000, 8001, 8002]
matrix = [[1, 2], [3]]
enabled = true
threshold = 1.5
[[servers]]
ip = "10.0.0.1"
[[servers]]
ip = "10.0.0.2"
inline = { x = 1, y = 2 }
"""
    let d as result of list of toml.TomlEntry to string is calling toml.parse with text
    if d.is_ok:
        calling spark.println with (calling toml.get with d.value, "title")
        calling spark.println with (calling toml.get with d.value, "owner.name")
        calling spark.println with (calling toml.get with d.value, "database.ports[2]")
        calling spark.println with (calling toml.get with d.value, "database.matrix[1][0]")
        calling spark.println with (calling toml.get with d.value, "database.enabled")
        calling spark.println with (calling toml.get with d.value, "database.threshold")
        calling spark.println with (calling toml.get with d.value, "servers[1].ip")
        calling spark.println with (calling toml.get with d.value, "servers[1].inline.y")
        let rendered as string is calling toml.stringify with d.value
        calling spark.println with rendered
        banish rendered
        calling toml.free_entries with d.value
    else:
        calling spark.println with d.error
    return 0
''')
    lines = out.strip().splitlines()
    assert lines[:8] == ["TOML Example", "Tom", "8002", "3", "true", "1.5",
                         "10.0.0.2", "2"]
    rendered = "\n".join(lines[8:])
    assert "matrix = [[1, 2], [3]]" in rendered
    assert "[[servers]]" in rendered
