import os
import subprocess
from pengu_project import ProjectConfig, PenguBuilder


class TestStdlib:
    def _compile_and_run(self, entry: str, bundle_file: str, bin_name: str) -> subprocess.CompletedProcess:
        bundle_target = f"build/{bundle_file}"
        if os.path.exists(bundle_target):
            try:
                os.remove(bundle_target)
            except Exception:
                pass
        cfg = ProjectConfig(entry=entry, base_dir=".", output="c")
        builder = PenguBuilder(cfg)
        bundle_path, _ = builder.bundle(output_file=bundle_target)
        assert os.path.exists(bundle_path)

        exe_path = f"build/{bin_name}.exe" if os.name == "nt" else f"build/{bin_name}"
        compile_cmd = ["gcc", bundle_path, "-I.", "-Ibuild", "-Ibuild/include", "-Lbuild/lib"]
        if os.path.exists("build/lib/libpengu_runtime.a"):
            compile_cmd += [
                "-lpengu_runtime", "-lpcre2-8", "-lxml2", "-lcurl",
                "-lmbedcrypto", "-lmicrohttpd", "-lz"
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
        return run_res

    def test_std_spark_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_spark.pengu", "test_spark_bundle.c", "test_spark_bin")
        assert "=== Test Spark ===" in res.stdout
        assert "0.6.0-spark" in res.stdout
        assert "HOLA PERGAMINO" in res.stdout
        assert "spark ok" in res.stdout

    def test_std_oracle_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_oracle.pengu", "test_oracle_bundle.c", "test_oracle_bin")
        assert "=== Test Oracle ===" in res.stdout
        assert "some_s is_present ok" in res.stdout
        assert "pengu value" in res.stdout
        assert "none_s is_none ok" in res.stdout
        assert "fallback" in res.stdout
        assert "some_i unwrap_or ok" in res.stdout
        assert "none_i unwrap_or ok" in res.stdout
        assert "res_ok is_ok ok" in res.stdout
        assert "success" in res.stdout
        assert "res_err is_err ok" in res.stdout
        assert "file not found" in res.stdout
        assert "res_ok_i unwrap_or ok" in res.stdout
        assert "res_err_i unwrap_or ok" in res.stdout
        assert "oracle ok" in res.stdout

    def test_std_whisper_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_whisper.pengu", "test_whisper_bundle.c", "test_whisper_bin")
        assert "=== Test Whisper ===" in res.stdout
        assert "whisper level ok" in res.stdout
        assert "whisper ok" in res.stdout

    def test_std_arithmancy_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_arithmancy.pengu", "test_arithmancy_bundle.c", "test_arithmancy_bin")
        assert "=== Test Arithmancy ===" in res.stdout
        assert "sqrt ok" in res.stdout
        assert "prime ok" in res.stdout
        assert "gcd ok" in res.stdout
        assert "arithmancy ok" in res.stdout

    def test_std_chronicle_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_chronicle.pengu", "test_chronicle_bundle.c", "test_chronicle_bin")
        assert "=== Test Chronicle ===" in res.stdout
        assert "time ok" in res.stdout
        assert "utc_year ok" in res.stdout
        assert "chronicle ok" in res.stdout

    def test_std_lot_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_lot.pengu", "test_lot_bundle.c", "test_lot_bin")
        assert "=== Test Lot ===" in res.stdout
        assert "rand_range ok" in res.stdout
        assert "lot ok" in res.stdout

    def test_std_rites_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_rites.pengu", "test_rites_bundle.c", "test_rites_bin")
        assert "=== Test Rites ===" in res.stdout
        assert "pid ok" in res.stdout
        assert "rites ok" in res.stdout

    def test_std_scrolls_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_scrolls.pengu", "test_scrolls_bundle.c", "test_scrolls_bin")
        assert "=== Test Scrolls ===" in res.stdout
        assert "HELLO WORLD" in res.stdout
        assert "hello world" in res.stdout
        assert "Hello World" in res.stdout
        assert "contains ok" in res.stdout
        assert "starts_with ok" in res.stdout
        assert "ends_with ok" in res.stdout
        assert "index_of ok" in res.stdout
        assert "last_index_of ok" in res.stdout
        assert "Hello Pengu" in res.stdout
        assert "split ok" in res.stdout
        assert "is_alpha ok" in res.stdout
        assert "is_digit ok" in res.stdout
        assert "is_alnum ok" in res.stdout
        assert "scrolls ok" in res.stdout

    def test_std_tally_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_tally.pengu", "test_tally_bundle.c", "test_tally_bin")
        assert "=== Test Tally ===" in res.stdout
        assert "init empty ok" in res.stdout
        assert "len 3 ok" in res.stdout
        assert "contains 20 ok" in res.stdout
        assert "not contains 99 ok" in res.stdout
        assert "index_of 20 ok" in res.stdout
        assert "pop 30 ok" in res.stdout
        assert "len 2 ok" in res.stdout
        assert "words len 2 ok" in res.stdout
        assert "tally ok" in res.stdout

    def test_std_atlas_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_atlas.pengu", "test_atlas_bundle.c", "test_atlas_bin")
        assert "=== Test Atlas ===" in res.stdout
        assert "init empty ok" in res.stdout
        assert "len 3 ok" in res.stdout
        assert "get one ok" in res.stdout
        assert "get two ok" in res.stdout
        assert "get three ok" in res.stdout
        assert "contains_key two ok" in res.stdout
        assert "not has foo ok" in res.stdout
        assert "update two ok" in res.stdout
        assert "remove two ok" in res.stdout
        assert "len after remove ok" in res.stdout
        assert "not contains two after remove ok" in res.stdout
        assert "atlas ok" in res.stdout

    def test_std_coven_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_coven.pengu", "test_coven_bundle.c", "test_coven_bin")
        assert "=== Test Coven ===" in res.stdout
        assert "set contains ok" in res.stdout
        assert "coven ok" in res.stdout

    def test_std_all_grimoires_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_all.pengu", "test_all_bundle.c", "test_all_bin")
        assert "=== Test All 5 ===" in res.stdout
        assert "valor" in res.stdout
        assert "all std ok" in res.stdout

    def test_std_compass_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_compass.pengu", "test_compass_bundle.c", "test_compass_bin")
        assert "=== Test Compass ===" in res.stdout
        assert "name: baz.txt" in res.stdout
        assert "stem: baz" in res.stdout
        assert "suffix: .txt" in res.stdout
        assert "=== Compass OK ===" in res.stdout

    def test_std_invoke_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_invoke.pengu", "test_invoke_bundle.c", "test_invoke_bin")
        assert "=== Test Invoke ===" in res.stdout
        assert "parse status: OK" in res.stdout
        assert "config: custom.cfg" in res.stdout
        assert "target: build_output" in res.stdout
        assert "verbose: true" in res.stdout
        assert "=== Invoke OK ===" in res.stdout

    def test_std_loom_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_loom.pengu", "test_loom_bundle.c", "test_loom_bin")
        assert "=== Test Loom ===" in res.stdout
        assert "range len: 5" in res.stdout
        assert "sum: 15" in res.stdout
        assert "product: 120" in res.stdout
        assert "max: 5" in res.stdout
        assert "min: 1" in res.stdout
        assert "take 2 len: 2" in res.stdout
        assert "skip 2 len: 3" in res.stdout
        assert "chain len: 5" in res.stdout
        assert "repeat len: 3" in res.stdout
        assert "chunks count: 3" in res.stdout
        assert "windows count: 3" in res.stdout
        assert "=== Loom OK ===" in res.stdout

    def test_std_archivum_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_archivum.pengu", "test_archivum_bundle.c", "test_archivum_bin")
        assert "=== Test Archivum ===" in res.stdout
        assert "create_dir: true" in res.stdout
        assert "write_file: true" in res.stdout
        assert "exists: true" in res.stdout
        assert "is_file: true" in res.stdout
        assert "is_dir: true" in res.stdout
        assert "content: Hello Pengu!" in res.stdout
        assert "append_file: true" in res.stdout
        assert "read_lines: ok" in res.stdout
        assert "metadata: ok" in res.stdout
        assert "copy_file: true" in res.stdout
        assert "move_file: true" in res.stdout
        assert "rename: true" in res.stdout
        assert "touch: true" in res.stdout
        assert "read_dir: ok" in res.stdout
        assert "remove_dir: true" in res.stdout
        assert "=== Archivum OK ===" in res.stdout

    def test_std_cipher_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_cipher.pengu", "test_cipher_bundle.c", "test_cipher_bin")
        assert "=== Test Cipher ===" in res.stdout
        assert "encoded: SGVsbG8gUGVuZ3UgV29ybGQh" in res.stdout
        assert "decoded: Hello Pengu World!" in res.stdout
        assert "is_base64: true" in res.stdout
        assert "parse_json: ok" in res.stdout
        assert "stringify_json: ok" in res.stdout
        assert "pretty_json: ok" in res.stdout
        assert "parse_value: 12345" in res.stdout
        assert "=== Cipher OK ===" in res.stdout

    def test_std_ledger_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_ledger.pengu", "test_ledger_bundle.c", "test_ledger_bin")
        assert "=== Test Ledger ===" in res.stdout
        assert "parse_csv: ok" in res.stdout
        assert "detected_delim: ," in res.stdout
        assert "parse_line: ok" in res.stdout
        assert "escaped: \"Hello, World!\"" in res.stdout
        assert "to_csv_string: ok" in res.stdout
        assert "to_tsv_string: ok" in res.stdout
        assert "write_csv: true" in res.stdout
        assert "read_csv: ok" in res.stdout
        assert "=== Ledger OK ===" in res.stdout

    def test_std_filum_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_filum.pengu", "test_filum_bundle.c", "test_filum_bin")
        assert "=== Test Filum ===" in res.stdout
        assert "mutex: ok" in res.stdout
        assert "waitgroup: ok" in res.stdout
        assert "atomic load: 10" in res.stdout
        assert "atomic inc: 11" in res.stdout
        assert "atomic swap: 20" in res.stdout
        assert "atomic compare_swap: ok" in res.stdout
        assert "num_cpu: ok" in res.stdout
        assert "goroutine_id: ok" in res.stdout
        assert "sleep: ok" in res.stdout
        assert "=== Filum OK ===" in res.stdout

    def test_std_regulus_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_regulus.pengu", "test_regulus_bundle.c", "test_regulus_bin")
        assert "=== Test Regulus ===" in res.stdout
        assert "compile: ok" in res.stdout
        assert "is_match: true" in res.stdout
        assert "search: ok" in res.stdout
        assert "is_full_match: true" in res.stdout
        assert "find_all: ok" in res.stdout
        assert "replace: hello pengu world" in res.stdout
        assert "split: ok" in res.stdout
        assert "quick_match: ok" in res.stdout
        assert "quick_replace: the dog sleeps" in res.stdout
        assert "=== Regulus OK ===" in res.stdout

    def test_std_parchment_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_parchment.pengu", "test_parchment_bundle.c", "test_parchment_bin")
        assert "=== Test Parchment ===" in res.stdout
        assert "parse_xml: ok" in res.stdout
        assert "root tag: root" in res.stdout
        assert "to_string: ok" in res.stdout
        assert "find: ok" in res.stdout
        assert "find_all: ok" in res.stdout
        assert "create_element: div" in res.stdout
        assert "create_text: text" in res.stdout
        assert "append_child: ok" in res.stdout
        assert "is_valid_xml: true" in res.stdout
        assert "=== Parchment OK ===" in res.stdout

    def test_std_seal_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_seal.pengu", "test_seal_bundle.c", "test_seal_bin")
        assert "=== Testing Seal ===" in res.stdout
        assert "md5 ok" in res.stdout
        assert "sha1 ok" in res.stdout
        assert "sha256 ok" in res.stdout
        assert "sha512 len ok" in res.stdout
        assert "crc32 ok" in res.stdout
        assert "gzip compressed ok" in res.stdout
        assert "gzip decompressed match ok" in res.stdout
        assert "zlib compressed ok" in res.stdout
        assert "zlib decompressed match ok" in res.stdout
        assert "verify hash ok" in res.stdout
        assert "=== Seal OK ===" in res.stdout

    def test_std_precis_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_precis.pengu", "test_precis_bundle.c", "test_precis_bin")
        assert "=== Testing Precis ===" in res.stdout
        assert "url encode ok" in res.stdout
        assert "url decode ok" in res.stdout
        assert "query parsed user ok" in res.stdout
        assert "dns lookup ok" in res.stdout
        assert "response rune ok" in res.stdout
        assert "=== Precis OK ===" in res.stdout

    def test_std_ward_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_ward.pengu", "test_ward_bundle.c", "test_ward_bin")
        assert "=== Testing Ward ===" in res.stdout
        assert "truth assertions ok" in res.stdout
        assert "equality assertions ok" in res.stdout
        assert "inequality assertions ok" in res.stdout
        assert "maybe and result assertions ok" in res.stdout
        assert "check ok" in res.stdout
        assert "check_eq_int ok" in res.stdout
        assert "check_eq_string ok" in res.stdout
        assert "=== Ward OK ===" in res.stdout

    def test_std_trial_bundle_and_execution(self):
        res = self._compile_and_run("tests_std/test_trial.pengu", "test_trial_bundle.c", "test_trial_bin")
        assert "=== Testing Trial ===" in res.stdout
        assert "Suite: Math & String Tests" in res.stdout
        assert "[PASS] 1 + 1 == 2" in res.stdout
        assert "[PASS] string concat" in res.stdout
        assert "[PASS] manual boolean check" in res.stdout
        assert "trial summary ok" in res.stdout
        assert "=== Trial OK ===" in res.stdout




