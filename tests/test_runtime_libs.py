"""tests/test_runtime_libs.py - Integration tests for real PCRE2, libxml2, and concurrency.
"""

import os
import subprocess
from pengu_project import ProjectConfig, PenguBuilder


def test_real_regex_and_xml_execution():
    """Validates that real regex matching with PCRE2 and XML parsing with libxml2 work in PenguScript."""
    src = """
import std.spark
import std.oracle
import std.regulus
import std.parchment

weave main into void:
    calling spark.println with "=== Testing Real Regulus & Parchment ==="
    
    # 1. Regulus Regex with PCRE2
    var re_m as maybe Regex is calling regulus.compile with "[a-zA-Z0-9_]+@[a-zA-Z0-9_]+\\\\.[a-zA-Z0-9_]+" and ""
    if re_m.is_present:
        calling spark.println with "regex compiled ok"
        var re as Regex is re_m.value
        var m as maybe Match is calling re.search with "Contact us at support@penguscript.org for info"
        if m.is_present:
            var matched as Match is m.value
            calling spark.println with "matched: " + matched.matched

    # 2. Parchment XML with libxml2
    var xml_data as string is "<pengu version=\\"1.0\\"><wizard name=\\"Merlin\\"><spell>Fireball</spell></wizard></pengu>"
    var doc_m as maybe Document is calling parchment.parse_xml with xml_data
    if doc_m.is_present:
        calling spark.println with "xml parsed ok"
        var doc as Document is doc_m.value
        var root_node as Node is doc.root
        calling spark.println with "root tag: " + root_node.tag
        
        var wiz as maybe Node is calling parchment.find with sigil of root_node and "wizard"
        if wiz.is_present:
            var wnode as Node is wiz.value
            var attr_val as maybe string is calling parchment.attr with sigil of wnode and "name"
            if attr_val.is_present:
                calling spark.println with "wizard name: " + attr_val.value

    calling spark.println with "=== Real Libs OK ==="
"""
    test_file = "scratch/test_real_libs.pengu"
    os.makedirs("scratch", exist_ok=True)
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(src)

    cfg = ProjectConfig(entry=test_file, base_dir=".", output="c")
    builder = PenguBuilder(cfg)
    bundle_path, _ = builder.bundle(output_file="build/test_real_libs_bundle.c")

    exe_path = "build/test_real_libs.exe" if os.name == "nt" else "build/test_real_libs"
    compile_cmd = [
        "gcc", bundle_path, "-I.", "-Ibuild", "-Ibuild/include", "-Lbuild/lib",
        "-lpengu_runtime", "-lpcre2-8", "-lxml2", "-lcurl", "-lmbedcrypto", "-lmicrohttpd", "-lz"
    ]
    if os.name == "nt":
        compile_cmd.extend(["-lws2_32", "-lwinmm", "-ladvapi32", "-lcrypt32", "-lbcrypt"])
    else:
        compile_cmd.extend(["-pthread", "-lm"])
    compile_cmd += ["-o", exe_path, "-lm"]

    comp_res = subprocess.run(compile_cmd, capture_output=True, text=True)
    assert comp_res.returncode == 0, f"Compilation failed: {comp_res.stderr}"

    run_res = subprocess.run([exe_path], capture_output=True, text=True)
    assert run_res.returncode == 0, f"Execution failed: {run_res.stderr}"
    assert "=== Testing Real Regulus & Parchment ===" in run_res.stdout
    assert "regex compiled ok" in run_res.stdout
    assert "matched: support@penguscript.org" in run_res.stdout
    assert "xml parsed ok" in run_res.stdout
    assert "root tag: pengu" in run_res.stdout
    assert "wizard name: Merlin" in run_res.stdout
    assert "=== Real Libs OK ===" in run_res.stdout


def test_real_concurrency_execution():
    """Validates that real concurrency primitives (AtomicInt, Mutex, WaitGroup) work in PenguScript."""
    src = """
import std.spark
import std.oracle
import std.filum

weave main into void:
    calling spark.println with "=== Testing Real Filum Concurrency ==="
    
    # 1. AtomicInt
    var counter as AtomicInt is calling filum.atomic_int with 10
    var cur_val as int is calling counter.load
    calling spark.println with "atomic load: " + cur_val
    
    var added as int is calling counter.add with 5
    var new_val as int is calling counter.load
    calling spark.println with "atomic new: " + new_val

    # 2. Mutex
    var mtx as Mutex is calling filum.mutex
    calling mtx.lock
    calling spark.println with "mutex locked"
    calling mtx.unlock
    calling spark.println with "mutex unlocked"

    # 3. WaitGroup
    var wg as WaitGroup is calling filum.wait_group
    calling wg.add with 1
    calling spark.println with "wg added 1"
    calling wg.done
    calling spark.println with "wg done"
    calling wg.wait
    calling spark.println with "wg wait ok"

    # 4. Sleep
    calling filum.sleep with 10
    calling spark.println with "sleep ok"

    calling spark.println with "=== Filum OK ==="
"""
    test_file = "scratch/test_real_filum.pengu"
    os.makedirs("scratch", exist_ok=True)
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(src)

    cfg = ProjectConfig(entry=test_file, base_dir=".", output="c")
    builder = PenguBuilder(cfg)
    bundle_path, _ = builder.bundle(output_file="build/test_real_filum_bundle.c")

    exe_path = "build/test_real_filum.exe" if os.name == "nt" else "build/test_real_filum"
    compile_cmd = [
        "gcc", bundle_path, "-I.", "-Ibuild", "-Ibuild/include", "-Lbuild/lib",
        "-lpengu_runtime", "-lpcre2-8", "-lxml2", "-lcurl", "-lmbedcrypto", "-lmicrohttpd", "-lz"
    ]
    if os.name == "nt":
        compile_cmd.extend(["-lws2_32", "-lwinmm", "-ladvapi32", "-lcrypt32", "-lbcrypt"])
    else:
        compile_cmd.extend(["-pthread", "-lm"])
    compile_cmd += ["-o", exe_path, "-lm"]

    comp_res = subprocess.run(compile_cmd, capture_output=True, text=True)
    assert comp_res.returncode == 0, f"Compilation failed: {comp_res.stderr}"

    run_res = subprocess.run([exe_path], capture_output=True, text=True)
    assert run_res.returncode == 0, f"Execution failed: {run_res.stderr}"
    assert "=== Testing Real Filum Concurrency ===" in run_res.stdout
    assert "atomic load: 10" in run_res.stdout
    assert "atomic new: 15" in run_res.stdout
    assert "mutex locked" in run_res.stdout
    assert "mutex unlocked" in run_res.stdout
    assert "wg added 1" in run_res.stdout
    assert "wg done" in run_res.stdout
    assert "wg wait ok" in run_res.stdout
    assert "sleep ok" in run_res.stdout
    assert "=== Filum OK ===" in run_res.stdout
