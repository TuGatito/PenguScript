#!/usr/bin/env python3
"""End-to-end tests for the PenguScript standard library.

Every std module ships an exercise program under ``tests/std_programs/``
(``test_<module>.pengu``). Each program imports its module, exercises it, and
prints deterministic marker lines. This single file runs all of them (several
libraries per test area) through the real pipeline:
Pengu source -> C bundle -> gcc -> executable, then asserts the markers.

Marker expectations were extracted from the historical per-module suite and
kept verbatim, so a regression in any std module fails loudly.
"""
from pathlib import Path

import pytest

from tests.conftest import REPO, BUILD_DIR, compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"

# program file -> list of strings that must appear in stdout.
EXPECTED_MARKERS = {
    "tally.pengu": [
        "=== Tally Pengunic ===",
        "sum: module=14 method=14 float=5.5",
        "stats: max=5 min=1 median=3 mode=1",
        "order: asc0=1 desc0=4.5 unique=4",
        "search: contains=ok count1=2 first_gt=4",
        "access: at_safe0=3 at_safe9=none",
        "select: take=2 drop=3 slice=2",
        "combine: concat=5 zip_sum=2 dot=7 repeat=3",
        "filter/map: evens=1 odds=4 fpos=2 double0=5 inc0=13",
        "predicates: sorted=false positive=true negative_float=true",
        "new: zip_with=3 running_last=14 scan_last=5.5",
        "chunk/windowed: chunks=3 windows=3",
        "aggregate: partition=1/4 pairs0=(0,3) min_max=(1,5) freq1=2",
        "edge: empty sum=0 product=1 single=42",
        "tally ok",
    ],
    "scrolls.pengu": [
        "=== Scrolls Pengunic ===",
        "scrolls trim ok [",
        "scrolls case ok [",
        "scrolls len ok [",
        "scrolls search ok [",
        "scrolls slice ok [",
        "scrolls words ok [",
        "scrolls lines ok [",
        "scrolls join ok [",
        "scrolls style ok [",
        "scrolls numbers ok",
        "scrolls padding ok [",
        "scrolls legacy ok",
        "scrolls ok",
    ],
    # New Pengunic program (generic native containers + compiler result constructors).
    "oracle.pengu": [
        "=== Oracle Pengunic ===", "oracle present unwrap_or ok 7", "oracle is_some ok true",
        "oracle is_none ok true", "oracle none unwrap_or ok 42",
        "oracle result ok value=5 is_ok=true", "oracle result err error=boom is_ok=false",
        "oracle legacy describe ok", "oracle ok",
    ],
    "atlas.pengu": [
        "=== Atlas Pengunic ===",
        "atlas str_int size ok",
        "atlas str_int has_key ok",
        "atlas str_int get_or ok",
        "atlas str_int sum ok",
        "atlas str_int max ok",
        "atlas str_int keys_sorted ok",
        "atlas str_int filter ok",
        "atlas str_int map_values ok",
        "atlas str_int remove ok",
        "atlas str_str size ok",
        "atlas str_str get_or ok",
        "atlas str_str clone ok",
        "atlas str_str values_sorted ok",
        "atlas str_str filter_values ok",
        "atlas int_int size ok",
        "atlas int_int sum ok",
        "atlas int_int keys_sorted ok",
        "atlas int_int negate ok",
        "atlas int_int merge ok",
        "atlas str_bool size ok",
        "atlas str_bool count ok",
        "atlas str_bool filter ok",
        "atlas module size ok",
        "atlas module has_key ok",
        "atlas module get_or ok",
        "atlas module from_lists ok",
        "atlas ok",
    ],
    "loom.pengu": [
        "=== Loom Pengunic ===",
        "legacy: range=5 sum=15 product=120 max=5 min=1",
        "slicing: take=2 skip=3 chain=5 repeat=3 reverse=5",
        "batching: chunks=3 windows=3 chunk_every=5 windowed=3",
        "unfold: up=5,7,9 down=5,3,1",
        "folds: running=15 rmax=5 rmin=1 diffs=4 squares=55",
        "predicates: any_zero=false all_equal=false asc=true desc=true",
        "zip: add=11 sub=9 min=3 op=33",
        "pairs: zip_longest=3 enumerate=3 enumerate_pairs=3",
        "merge: interleave=6 round_robin=6",
        "rotate: left=20,30,10 right=30,10,20 intersperse=5 pairwise=2 flat=6",
        "sets: union=6 intersect=2 difference=2 symdiff=4",
        "search: first=1 last=3 binary=2 miss=none",
        "index: evens=5 positive=5 min=0 max=2 min_max=10,30 partitioned=true",
        "editing: insert=6 remove=5 replace=77 swap=77 pad=7",
        "stats: median=2 mode=2 variance=2.16 stddev=1.4696 p50=2 p100=5",
        "scan_left: last=15",
        "generic: first_or=100 take=2 take_last=2 reverse=3 chain=4 index=2/-1",
        "edge: empty sum=0 product=1 min_max=none chunks=0",
        "loom ok",
    ],
    "test_spark.pengu": ["=== Test Spark ===", "0.6.0-spark", "HOLA PERGAMINO", "spark ok"],
    "test_oracle.pengu": [
        "=== Test Oracle ===", "some_s is_present ok", "pengu value", "none_s is_none ok",
        "fallback", "some_i unwrap_or ok", "none_i unwrap_or ok", "res_ok is_ok ok",
        "success", "res_err is_err ok", "file not found", "res_ok_i unwrap_or ok",
        "res_err_i unwrap_or ok", "oracle ok",
    ],
    "test_whisper.pengu": ["=== Test Whisper ===", "whisper level ok", "whisper ok"],
    "test_arithmancy.pengu": ["=== Test Arithmancy ===", "sqrt ok", "prime ok", "gcd ok",
                              "arithmancy ok"],
    "test_chronicle.pengu": ["=== Test Chronicle ===", "time ok", "utc_year ok",
                             "chronicle ok"],
    "test_lot.pengu": ["=== Test Lot ===", "rand_range ok", "lot ok"],
    "test_rites.pengu": ["=== Test Rites ===", "pid ok", "rites ok"],
    "test_scrolls.pengu": [
        "=== Test Scrolls ===", "HELLO WORLD", "hello world", "Hello World",
        "contains ok", "starts_with ok", "ends_with ok", "index_of ok",
        "last_index_of ok", "Hello Pengu", "split ok", "is_alpha ok",
        "is_digit ok", "is_alnum ok", "scrolls ok",
    ],
    "test_tally.pengu": [
        "=== Test Tally ===", "init empty ok", "len 3 ok", "contains 20 ok",
        "not contains 99 ok", "index_of 20 ok", "pop 30 ok", "len 2 ok",
        "words len 2 ok", "tally ok",
    ],
    "test_atlas.pengu": [
        "=== Test Atlas ===", "init empty ok", "len 3 ok", "get one ok", "get two ok",
        "get three ok", "contains_key two ok", "not has foo ok", "update two ok",
        "remove two ok", "len after remove ok", "not contains two after remove ok",
        "atlas ok",
    ],
    "test_coven.pengu": ["=== Test Coven ===", "set contains ok", "coven ok"],
    "test_all.pengu": ["=== Test All 5 ===", "valor", "all std ok"],
    "test_compass.pengu": ["=== Test Compass ===", "name: baz.txt", "stem: baz",
                           "suffix: .txt", "=== Compass OK ==="],
    "test_invoke.pengu": ["=== Test Invoke ===", "parse status: OK", "config: custom.cfg",
                          "target: build_output", "verbose: true", "=== Invoke OK ==="],
    "test_loom.pengu": [
        "=== Test Loom ===", "range len: 5", "sum: 15", "product: 120", "max: 5",
        "min: 1", "take 2 len: 2", "skip 2 len: 3", "chain len: 5", "repeat len: 3",
        "chunks count: 3", "windows count: 3", "=== Loom OK ===",
    ],
    "test_archivum.pengu": [
        "=== Test Archivum ===", "create_dir: true", "write_file: true", "exists: true",
        "is_file: true", "is_dir: true", "content: Hello Pengu!", "append_file: true",
        "read_lines: ok", "metadata: ok", "copy_file: true", "move_file: true",
        "rename: true", "touch: true", "read_dir: ok", "remove_dir: true",
        "=== Archivum OK ===",
    ],
    "test_cipher.pengu": [
        "=== Test Cipher ===", "encoded: SGVsbG8gUGVuZ3UgV29ybGQh",
        "decoded: Hello Pengu World!", "is_base64: true", "parse_json: ok",
        "stringify_json: ok", "pretty_json: ok", "parse_value: 12345",
        "=== Cipher OK ===",
    ],
    "test_ledger.pengu": [
        "=== Test Ledger ===", "parse_csv: ok", "detected_delim: ,", "parse_line: ok",
        'escaped: "Hello, World!"', "to_csv_string: ok", "to_tsv_string: ok",
        "write_csv: true", "read_csv: ok", "=== Ledger OK ===",
    ],
    "test_filum.pengu": [
        "=== Test Filum ===", "mutex: ok", "waitgroup: ok", "atomic load: 10",
        "atomic inc: 11", "atomic swap: 20", "atomic compare_swap: ok", "num_cpu: ok",
        "goroutine_id: ok", "sleep: ok", "=== Filum OK ===",
    ],
    "test_regulus.pengu": [
        "=== Test Regulus ===", "compile: ok", "is_match: true", "search: ok",
        "is_full_match: true", "find_all: ok", "replace: hello pengu world",
        "split: ok", "quick_match: ok", "quick_replace: the dog sleeps",
        "=== Regulus OK ===",
    ],
    "test_parchment.pengu": [
        "=== Test Parchment ===", "parse_xml: ok", "root tag: root", "to_string: ok",
        "find: ok", "find_all: ok", "create_element: div", "create_text: text",
        "append_child: ok", "is_valid_xml: true", "=== Parchment OK ===",
    ],
    "test_seal.pengu": [
        "=== Testing Seal ===", "md5 ok", "sha1 ok", "sha256 ok", "sha512 len ok",
        "crc32 ok", "gzip compressed ok", "gzip decompressed match ok",
        "zlib compressed ok", "zlib decompressed match ok", "verify hash ok",
        "=== Seal OK ===",
    ],
    "test_precis.pengu": [
        "=== Testing Precis ===", "url encode ok", "url decode ok",
        "query parsed user ok", "dns lookup ok", "response rune ok", "=== Precis OK ===",
    ],
    "test_ward.pengu": [
        "=== Testing Ward ===", "truth assertions ok", "equality assertions ok",
        "inequality assertions ok", "maybe and result assertions ok", "check ok",
        "check_eq_int ok", "check_eq_string ok", "=== Ward OK ===",
    ],
    "test_trial.pengu": [
        "=== Testing Trial ===", "Suite: Math & String Tests", "[PASS] 1 + 1 == 2",
        "[PASS] string concat", "[PASS] manual boolean check", "trial summary ok",
        "=== Trial OK ===",
    ],
    "test_ffi.pengu": [
        "=== Testing FFI ===", "string round trip ok", "bytes view ok",
        "slice from ptr ok", "list from ptr ok", "float list from ptr ok",
        "map from slices ok", "=== FFI OK ===",
    ],
}


def _program_markers(program: str):
    return EXPECTED_MARKERS[program]


@requires_runtime
@pytest.mark.parametrize("program", sorted(EXPECTED_MARKERS))
def test_std_module_program(program):
    """Compile+run one std exercise program and check its marker lines."""
    source = (STD_PROGRAMS / program).read_text(encoding="utf-8")
    # Run inside a gitignored working dir so file-based modules (archivum,
    # ledger) write there instead of polluting the repository root.
    cwd = BUILD_DIR / "std_run"
    cwd.mkdir(parents=True, exist_ok=True)
    tag = program.replace(".pengu", "").replace("test_", "")
    result = compile_run(source, tag=tag, cwd=str(cwd))
    missing = [m for m in _program_markers(program) if m not in result.stdout]
    assert not missing, f"{program}: markers missing from stdout: {missing}\n{result.stdout}"
