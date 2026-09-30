# String composition tests

PenguScript composes strings **only** with `"{expr}"` interpolation:

- `+` is numeric-only. `"a" + b`, `a + b` (strings), `"a" + 1` and `1 + "a"`
  are `E0005`.
- `+=` is numeric-only. `set s += "b"` is `E0005`; rebind with
  `set s is "{s}b"`.
- Interpolation arguments are copied **byte-exactly**, so strings that hold
  binary data (a NUL in the middle, hash digests, decoded base64) survive
  composition — `printf`'s `%.*s` would truncate them.

## Layout

| Pattern | Meaning |
|---|---|
| `err_*.pengu` | must be rejected with the `# EXPECTED: EXXXX` code |
| `ok_*.pengu` | must compile, link and exit 0 |
| `leak_*.pengu` | additionally checked for zero lost allocations |

## Running

```bash
./tests/test_string_composition/run_all.sh        # compile + run every ok_/leak_ program
./tests/test_string_composition/run_leakcheck.sh  # leak-check the leak_ programs
python -m pytest tests/test_string_composition_suite.py -q
```
