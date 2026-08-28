import os
import subprocess
from pengu_project import ProjectConfig, PenguBuilder


def test_all_types_compilation_and_execution():
    src = """
import std.spark
import std.ward

rune FullTypeDemo:
    c as char
    b as byte
    u8_val as u8
    i8_val as i8
    u16_val as u16
    i16_val as i16
    u32_val as u32
    i32_val as i32
    u64_val as u64
    i64_val as i64
    sz as usize
    isz as isize
    f as float
    d as double
    ok as bool

rune Box shard T:
    val as T
    label as char

weave make_box shard T with v as T and l as char into Box of T:
    return with val is v and label is l

weave add_u32 with a as u32 and b as u32 into u32:
    return a + b

weave invert_char with c as ref to char into void:
    if essence of c == 'a':
        set essence of c is 'z'

weave main into void:
    var c as char is 'a'
    var b as byte is 128
    var u8_val as u8 is 255
    var i8_val as i8 is -128
    var u16_val as u16 is 65535
    var i16_val as i16 is -32768
    var u32_val as u32 is 4294967295
    var i32_val as i32 is -2147483648
    var u64_val as u64 is 18446744073709551615
    var i64_val as i64 is -9223372036854775807
    var sz as usize is 4096
    var isz as isize is -4096
    var f as float is 1.25
    var d as double is 9.87654321
    var ok as bool is true

    # Mutation test
    set c is 'b'
    set b is 64
    set u8_val is 200
    set f is 2.5
    set d is 10.0
    set ok is false

    var demo as FullTypeDemo is with c is 'k', b is 1, u8_val is 2, i8_val is 3, u16_val is 4, i16_val is 5, u32_val is 6, i32_val is 7, u64_val is 8, i64_val is 9, sz is 10, isz is 11, f is 12.0, d is 13.0, ok is true

    calling ward.assert_eq_int with demo.u8_val and 2
    calling ward.assert_true with demo.ok

    # Pointer test
    var target_char as char is 'a'
    calling invert_char with sigil of target_char
    calling ward.assert_true with target_char == 'z'

    # Generics test
    var b_char as Box of char is calling make_box of char with 'X' and 'C'
    var b_u32 as Box of u32 is calling make_box of u32 with 777 and 'N'
    var b_dbl as Box of double is calling make_box of double with 3.14159 and 'D'

    calling ward.assert_true with b_char.val == 'X'
    calling ward.assert_true with b_u32.val == 777

    # Judge char test
    var grade as char is 'A'
    var msg as string is judge grade:
        when 'A' -> "Excellent"
        when 'B' -> "Good"
        else -> "Average"
    calling ward.assert_eq_string with msg and "Excellent"

    calling spark.println with "ALL_TYPES_SUCCESS"
"""
    test_file = "scratch/test_all_types.pengu"
    os.makedirs("scratch", exist_ok=True)
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(src)

    cfg = ProjectConfig(entry=test_file, base_dir=".", output="c")
    builder = PenguBuilder(cfg)
    bundle_path, _ = builder.bundle(output_file="build/test_all_types_bundle.c")

    exe_path = "build/test_all_types.exe" if os.name == "nt" else "build/test_all_types"
    compile_cmd = [
        "gcc", bundle_path, "-I.", "-Ibuild", "-Ibuild/include", "-Lbuild/lib",
        "-lpengu_runtime", "-lpcre2-8", "-lxml2", "-lcurl", "-lmbedcrypto", "-lmicrohttpd", "-lz"
    ]
    if os.name == "nt":
        compile_cmd.extend(["-lws2_32", "-lwinmm", "-ladvapi32", "-lcrypt32", "-lbcrypt"])
    else:
        compile_cmd.extend(["-pthread", "-lm"])
    compile_cmd += ["-o", exe_path, "-lm"]

    res = subprocess.run(compile_cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Compilation failed: {res.stderr}"

    run_res = subprocess.run([exe_path], capture_output=True, text=True)
    assert run_res.returncode == 0, f"Execution failed: {run_res.stderr}"
    assert "ALL_TYPES_SUCCESS" in run_res.stdout
