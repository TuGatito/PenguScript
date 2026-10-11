# Bugs fixed in Chunk 6 — `std/lot` + `std/whisper`

Chunk 6 of the Pengunic 2.0 migration re-verified and fixed **every** bug found
in `std/lot.pengu` and `std/whisper.pengu`. This file is the mandated record:
one entry per bug, with the symptom, the root cause, the impact, the fix and the
regression test that fails without the fix.

The list starts from the 24 bugs the brief already identified (B1–B24) and adds
the defects the audit found on top (B25–B27). Bugs that need a compiler change
are collected separately at the end: §5.3 of the brief forbids touching the
compiler, so those are **documented and worked around**, never ignored, and are
handed to the next compiler chunk.

Regression tests live in two places:

* the internal `test "…"` blocks at the bottom of each module
  (`pengu test --entry std/lot.pengu`, `pengu test --entry std/whisper.pengu`);
* the self-contained end-to-end suites `tests/stdlib/test_lot.py` and
  `tests/stdlib/test_whisper.py`, which compile and run a throw-away program per
  case and assert its stdout/stderr/exit code.

Every entry names the internal test that pins it; the external suite carries the
same cases end to end.

---

## `std/lot` — randomness (LOT_VERSION `2.0.0` → `2.1.0`)

### BUG-1: `rand_gamma` returned a bogus value when its rejection loop ran out
- **Módulo:** std/lot
- **Función:** `rand_gamma`
- **Síntoma:** After 1000 rejected Marsaglia–Tsang proposals the function fell
  out of the loop and `return scale * d`. That is `scale * (shape - 1/3)`, which
  is **not** a draw from `Gamma(shape, scale)`: it is a constant, and the caller
  had no way to know the sampler had failed.
- **Causa raíz:** The acceptance loop had a hard cap and no failure path. The
  "give up" branch returned a plausible-looking number instead of signalling
  exhaustion, so a PRNG hiccup would silently bias every later statistic.
- **Impacto:** Silent statistical corruption of every distribution built on
  `rand_gamma` (`rand_beta`, `rand_chi_squared`) and of user simulations. A
  production user could not detect it.
- **Fix aplicado:** The bounded acceptance pass moved into the private
  `_gamma_mt`, which returns `maybe float` — `maybe none` on exhaustion, which is
  observable and testable. `rand_gamma` now retries the whole sample and can only
  return an accepted proposal; it panics (loudly) after 1024 retries, which is
  astronomically unreachable for a working generator. The bogus `scale * d`
  return no longer exists.
- **Test de regresión:** internal `test "BUG-1: the gamma core reports exhaustion
  instead of a bogus sample"` (`_gamma_mt(2.0, 1.0, 0)` must be `none`), plus
  `test "rand_gamma returns positive finite samples…"` and
  `tests/stdlib/test_lot.py`.

### BUG-2: `rand_weibull` could loop forever or return `inf`
- **Módulo:** std/lot
- **Función:** `rand_weibull`
- **Síntoma:** `while u <= 0.0 or u >= 1.0: u = rand_float` re-draws on a
  boundary value; a generator that can return `1.0` makes the loop unprovable.
  Separately, `log(1.0 - u)` with `u` close to `1.0` underflows to `-inf`, so
  `scale * pow(-log(1-u), 1/shape)` returned `inf`.
- **Causa raíz:** The function bounded the loop by re-drawing instead of
  clamping, and passed the raw draw straight into `log`. The open interval
  `(0, 1)` the formula requires was never actually guaranteed.
- **Impacto:** A hang, or `inf`/`nan` propagating into physics/queueing models.
- **Fix aplicado:** The new private `_unit_open` returns a draw guaranteed to be
  in `(0.0, 1.0)` (boundary draws become `LOT_EPSILON`), and `rand_weibull` uses
  it. No loop, no `log(0)`, no `inf`.
- **Test de regresión:** internal `test "BUG-2: rand_weibull never produces inf or
  NaN"` (200 draws, all finite and `>= 0`).

### BUG-3: `choice_weighted` / `choice_weighted_string` overflowed on large weights
- **Módulo:** std/lot
- **Función:** `choice_weighted`, `choice_weighted_string`
- **Síntoma:** `total` was an `int`; two weights of `INT_MAX` wrapped the sum
  negative, `total <= 0` reported "no weight" (or, without the guard, produced a
  negative range) and the choice was wrong.
- **Causa raíz:** 32-bit accumulation of a quantity that is a sum of 32-bit
  weights, then a 32-bit comparison.
- **Impacto:** Wrong or impossible results for legitimate weight scales, e.g.
  weighted load balancing with large counters.
- **Fix aplicado:** The selection moved into `_weighted_index`, which accumulates
  in `i64` and compares a scaled `float` target against an `i64` total. There is
  no 32-bit addition left, so the sum cannot wrap.
- **Test de regresión:** internal `test "BUG-3: weighted choice cannot overflow
  with huge weights"` (`[INT_MAX, INT_MAX]`, 200 draws, index always `0` or `1`).

### BUG-4: `rand_bytes_hex` faked bytes with random hex characters
- **Módulo:** std/lot
- **Función:** `rand_bytes_hex` (and the missing `rand_bytes`)
- **Síntoma:** `rand_bytes_hex(n)` called `rand_hex_string(2n)`: it produced `2n`
  random *hex digits*, not the hex encoding of `n` random bytes. There was no
  way to obtain raw random bytes at all.
- **Causa raíz:** The function was implemented at the wrong layer (character
  sampling) and never had a byte generator to build on.
- **Impacto:** Callers who needed real bytes (crypto-shaped APIs, binary
  protocols, `rand_uuid4`) could not get them, and the name lied about the
  output.
- **Fix aplicado:** New `rand_bytes(n)` (a `list of int` of real bytes) and
  `rand_bytes_string(n)` (the same bytes packed into a `string`). `rand_bytes_hex`
  now hex-encodes `rand_bytes(n)`; `rand_hex_upper`, `rand_base64` and `rand_uuid4`
  are built on the same primitive.
- **Test de regresión:** internal `test "BUG-4: rand_bytes produces real bytes and
  rand_bytes_string packs them"` and `test "rand_bytes_hex hex-encodes real
  bytes…"`.

### BUG-5: `rand_password` used a `chr 123` / `chr 125` hack for braces
- **Módulo:** std/lot
- **Función:** `rand_password`
- **Síntoma:** The symbol alphabet embedded `{(chr 123)}` and `{(chr 125)}`
  because a bare `{`/`}` in a normal string opens string interpolation. The
  result compiled but was unreadable and easy to break.
- **Causa raíz:** Braces are interpolation syntax in ordinary string literals, so
  the author reached for `chr` instead of the raw-string form the language
  provides for exactly this.
- **Impacto:** Maintainability; the alphabet could be silently corrupted by a
  later edit.
- **Fix aplicado:** The alphabet is now the raw literal
  `r"!@#$%^&*()-_=+[]{}|;:,.<>?"`, exposed as the public weave `password_symbols`.
  It is a weave rather than a `const` because of out-of-scope compiler finding
  C-1 below.
- **Test de regresión:** internal `test "BUG-5: the password alphabet carries real
  braces through a raw string"`.

### BUG-6: `shuffle` / `shuffle_string` rebuilt the list with `push`
- **Módulo:** std/lot
- **Función:** `shuffle`, `shuffle_string`
- **Síntoma:** The copy loop pushed element by element into a fresh list,
  reallocating as it grew, instead of using the list-comprehension idiom.
- **Causa raíz:** The Fisher–Yates algorithm itself was correct; only the copy
  was written the long way.
- **Impacto:** Performance and idiom; O(n) reallocations per shuffle.
- **Fix aplicado:** `var res as list of int is for x in items then x` (the
  idiomatic copy) in `shuffle`, `shuffle_string` and the new generic
  `rand_shuffle_shard`.
- **Test de regresión:** internal `test "BUG-6: shuffle permutes the list instead
  of rebuilding it element by element"` (length and multiset preserved).

### BUG-7: `seed` truncated negative seeds silently
- **Módulo:** std/lot
- **Función:** `seed`
- **Síntoma:** `seed` takes a 32-bit `int` while C `srand` takes `unsigned int`;
  a negative seed is converted modulo 2^32. The behaviour was correct C but
  undocumented, so `seed(-1)` looked like a bug.
- **Causa raíz:** A narrowing/reinterpretation at the language/C boundary that the
  docstring did not mention.
- **Impacto:** Surprise for callers hashing arbitrary inputs into a seed.
- **Fix aplicado:** The conversion is now documented explicitly, and the
  regression test pins the property that matters: the same negative seed
  reproduces the same sequence. `seed_from_time` and `seed_from_pid` were added
  so callers do not have to invent a seed at all.
- **Test de regresión:** internal `test "BUG-7: a negative seed is repeatable and
  does not truncate silently"`.

### BUG-8: `rand_lognormal` did not validate `sigma`
- **Módulo:** std/lot
- **Función:** `rand_lognormal`
- **Síntoma:** With `sigma <= 0`, `rand_normal(mu, 0)` returns `mu` and the
  result is the constant `exp(mu)`. The function never said so.
- **Causa raíz:** A degenerate parameter reaching a distribution whose
  "distribution" then collapses to a point.
- **Impacto:** A caller could believe it had a distribution when it had a
  constant.
- **Fix aplicado:** The degenerate case is handled explicitly (`return exp(mu)`)
  and documented; the parameter is no longer passed through by accident.
- **Test de regresión:** internal `test "BUG-8: rand_lognormal validates sigma…"`.

### BUG-9: `choice` / `choice_string` did not defend against an empty payload
- **Módulo:** std/lot
- **Función:** `choice`, `choice_string`
- **Síntoma:** The 2.0.0 guard was `n == 0`; a list whose length is 0 is the only
  representable empty state the runtime can produce, but the guard did not also
  reject a negative length and the code was split between `== 0` and a later
  index computation.
- **Causa raíz:** An incomplete guard (`n == 0` instead of `n <= 0`) around an
  index that assumes a non-empty payload.
- **Impacto:** A malformed/zeroed list container could reach `items at idx` with
  no valid element.
- **Fix aplicado:** Both functions now guard with `n <= 0` and return
  `maybe none` in one place, so no path reaches the indexer without a
  non-empty list. The empty-list contract is stated in the docstring.
- **Test de regresión:** internal `test "BUG-9: choice returns none on an empty
  list and a member otherwise"`.

### BUG-10: `rand_int` could return a negative value
- **Módulo:** std/lot
- **Función:** `rand_int`
- **Síntoma:** `rand_int` returned the raw `rand()` result. The C standard allows
  a negative return, so "uniform in `[0, RAND_MAX]`" was a promise the code did
  not keep on every libc.
- **Causa raíz:** Trusting an implementation-defined range instead of clamping to
  the documented one.
- **Impacto:** Negative "random" values silently broke modular arithmetic, index
  computation and the range helpers built on the draw.
- **Fix aplicado:** The raw draw is clamped with
  `return if r < 0 then 0 else r`, which the docstring now states.
- **Test de regresión:** internal `test "BUG-10: rand_int is always non-negative
  and at most rand_max"`.

### BUG-11: the module was not thread-safe
- **Módulo:** std/lot
- **Función:** all generator entry points
- **Síntoma:** Two threads calling `rand()` (or `seed`) at once race on the
  process-global C PRNG state.
- **Causa raíz:** The C standard says nothing about concurrent `rand()`, and the
  2.0.0 module simply called the bridge.
- **Impacto:** Corrupted generator state, duplicated/dropped draws, and data
  races under any threaded caller.
- **Fix aplicado:** A process-wide mutex is taken from the runtime's portable
  thread layer through three `antiquus` blocks (`_mtx`, `_lock`, `_unlock`).
  Every bridge call that touches the generator runs inside the critical section,
  so concurrent single draws are atomic. The module docstring is explicit that a
  *compound* sequence ("seed then draw ten values") still needs the caller to
  serialise itself, because the lock is released between calls.
- **Test de regresión:** the whole internal suite runs through the locked path;
  `tests/stdlib/test_lot.py` adds a dedicated concurrency-smoke case.

### BUG-12 (new): `rand_beta` did not validate its parameters
- **Módulo:** std/lot
- **Función:** `rand_beta`
- **Síntoma:** `rand_beta(a, b)` with `a <= 0` or `b <= 0` did not return early;
  it delegated to `rand_gamma`, which returned `0.0`, and then computed
  `0 / 0`-shaped ratios.
- **Causa raíz:** Two layers each assumed the other validated the parameter, so
  neither did.
- **Impacto:** `nan`/`0.0` results for an invalid input instead of a documented
  value.
- **Fix aplicado:** `rand_beta` validates `a <= 0.0 or b <= 0.0` first and
  returns `0.0`, matching `rand_gamma`'s contract.
- **Test de regresión:** internal `test "rand_beta stays in [0, 1] and validates
  its parameters"`.

### BUG-13 (new): `sample` / `sample_string` could not clamp `k`
- **Módulo:** std/lot
- **Función:** `sample`, `sample_string`
- **Síntoma:** The 2.0.0 code tried to clamp `k` by assigning to the parameter
  (`set k is n`). Parameters are immutable in Pengunic 2.0, so that statement is
  an error; the intended clamp never ran.
- **Causa raíz:** Treating a parameter as a mutable local.
- **Impacto:** `sample(xs, len+1)` would have requested more elements than the
  list holds.
- **Fix aplicado:** Both functions copy `k` into a local `take`, clamp that, and
  loop on it.
- **Test de regresión:** internal `test "sample draws distinct elements and clamps
  k to the pool size"`.

---

## `std/whisper` — logging (WHISPER_VERSION `2.0.0` → `2.1.0`)

### BUG-12b (brief B12): `Logger.child` dropped the parent's `file_path`
- **Módulo:** std/whisper
- **Función:** `Logger.child`
- **Síntoma:** The child was built with `file_path is ""`, so a child of a
  file-backed logger silently stopped writing to the parent's file and started
  writing to stdout instead.
- **Causa raíz:** A literal `""` where `self->file_path` was meant, in the only
  constructor that has to copy the whole configuration.
- **Impacto:** Log loss: every line emitted through a child logger vanished from
  the log file (it went to stdout, which is often discarded in production).
- **Fix aplicado:** `child` now builds the result through `_copy_of` and copies
  `file_path` (and the new `stream`, `fmt` and `context` fields), so the child
  inherits the parent's destination exactly.
- **Test de regresión:** internal `test "BUG-12: Logger.child preserves the parent
  file path and settings"`; external case in `tests/stdlib/test_whisper.py`.

### BUG-13 (brief B13): file output cannot be colourised
- **Módulo:** std/whisper
- **Función:** `Logger.log`, `Logger.to_file`
- **Síntoma:** Documented only. A caller that wants ANSI colours *inside* a file
  cannot get them; a caller that wants plain text gets it automatically.
- **Causa raíz:** A deliberate design choice, not a defect: an ANSI escape in a
  log file breaks every grep and every log shipper.
- **Impacto:** None functional; the behaviour was undocumented, which made it
  look like a bug.
- **Fix aplicado:** Documentation. `to_file`'s docstring now states that file
  lines are always plain and points at `set_format` for layout changes.
- **Test de regresión:** external `tests/stdlib/test_whisper.py` asserts a file
  written by a colour-enabled logger contains no `\x1b` byte.

### BUG-14 (brief B14): `_json_escape` ignored `\b`, `\f` and control bytes
- **Módulo:** std/whisper
- **Función:** `_json_escape`
- **Síntoma:** Only `"`, `\`, `\n`, `\r` and `\t` were escaped. A backspace, a
  form feed or any other byte below `0x20` went into the JSON document raw.
- **Causa raíz:** A fixed chain of `replace_all` calls, which cannot express the
  "any control byte" rule and always misses the next one someone forgets.
- **Impacto:** Invalid JSON. A log shipper or `jq` fails on the whole line, so one
  stray control byte loses the record.
- **Fix aplicado:** The escaper is a single character loop. It emits `\b`, `\f`,
  `\n`, `\r`, `\t`, `\"`, `\\` and, for every other byte below `0x20`, a
  `\u00XX` escape. Bytes `>= 0x20` (including UTF-8 continuation bytes) pass
  through unchanged.
- **Test de regresión:** internal `test "BUG-14: _json_escape handles backspace,
  form feed and control bytes"`; external case in `tests/stdlib/test_whisper.py`.

### BUG-15 (brief B15): `log_json` never included a timestamp
- **Módulo:** std/whisper
- **Función:** `log_json` (module level and method), `log_json_ex`
- **Síntoma:** A structured log line had no time member, even with
  `show_timestamp` enabled. A production log without a timestamp cannot be
  correlated across services.
- **Causa raíz:** The two JSON paths rendered their own document and neither
  consulted the timestamp setting.
- **Impacto:** Structured logs were almost useless for incident analysis.
- **Fix aplicado:** Rendering moved into `_render_json`, which takes an
  `include_time` flag. `Logger.log_json` passes `self->show_timestamp`; the new
  `Logger.log_json_ex` lets a caller choose; the module-level `log_json` always
  includes the member. The value is an ISO-8601 UTC string.
- **Test de regresión:** internal `test "BUG-15: _render_json includes a
  timestamp only when asked"`; external case in `tests/stdlib/test_whisper.py`.

### BUG-16 (brief B16): `log_json` emitted fields in hash order
- **Módulo:** std/whisper
- **Función:** `log_json` (both variants)
- **Síntoma:** `for k in fields` walks the map's hash table, so the same logical
  event produced a different byte string on every run. Diffing two logs for the
  same event reported spurious changes.
- **Causa raíz:** Iterating an unordered container and calling the result
  "deterministic".
- **Impacto:** Non-reproducible structured output; a JSON-line differ is useless.
- **Fix aplicado:** `_sorted_keys` materialises the keys (through the runtime
  `pengu_map_keys_string`) and sorts them bytewise with the `_cmp_string`
  `antiquus` comparator (`memcmp` + length tie-break, exact for NUL-containing
  keys). `_render_json` emits in that order.
- **Test de regresión:** internal `test "BUG-16: _render_json emits fields in a
  deterministic order"` and `test "BUG-16: _sorted_keys returns byte-sorted
  keys"`.

### BUG-17 (brief B17): `Logger.from_env` could not tell "unset" from "invalid"
- **Módulo:** std/whisper
- **Función:** `Logger.from_env`, `set_level_from_env`
- **Síntoma:** An unset `LOG_LEVEL` and `LOG_LEVEL=garbage` both fell back to
  `LOG_INFO` with no signal, so a typo in the environment silently changed the
  log volume.
- **Causa raíz:** The two cases shared one `if` and one fallback.
- **Impacto:** A misconfigured deployment looks configured; the operator cannot
  see that the value was rejected.
- **Fix aplicado:** `_level_from_env_or` reports a set-but-unparseable value on
  stderr (`whisper: ignoring invalid NAME="VALUE"`) and keeps scanning; an unset
  variable is skipped silently. The fallback is explicit.
- **Test de regresión:** internal `test "BUG-17: a set-but-invalid environment
  level is ignored…"`; external case asserts the stderr warning.

### BUG-18 (brief B18): `set_level_from_env` left the level at the most verbose value
- **Módulo:** std/whisper
- **Función:** `set_level_from_env`
- **Síntoma:** With no environment variable set, the function did nothing. The
  global level had been initialised to `LOG_TRACE` (0), so a production program
  that "configured" its logging still printed every trace line.
- **Causa raíz:** No default; "no env var" was treated as "no configuration
  needed" instead of "use the documented default".
- **Impacto:** Log spam in production, and a real cost once each line is written
  to a file or a shipper.
- **Fix aplicado:** A configurable default level (initially `LOG_INFO`) lives in
  a shared C cell exposed by `set_default_level` / `get_default_level`.
  `set_level_from_env` applies it when no variable names a valid level.
- **Test de regresión:** internal `test "BUG-18: set_level_from_env falls back to
  the configured default"`; external case runs with a clean environment.

### BUG-19 (brief B19): there was no way to log to stderr
- **Módulo:** std/whisper
- **Función:** `Logger.to_stderr`, `Logger.to_stdout`
- **Síntoma:** A `Logger` could write to stdout or to a file, never to stderr.
  Diagnostics could therefore not be separated from program output.
- **Causa raíz:** The destination was a `file_path` string only; the stdout/stderr
  choice had no representation.
- **Impacto:** Tools that capture stdout as data (pipelines, `$(…)`, JSON
  consumers) were polluted by log lines.
- **Fix aplicado:** A `stream` field (`0` = stdout, `1` = stderr) plus
  `to_stderr` / `to_stdout`; `_emit` routes through `spark.eprintln` for stream 1.
  File mode still wins, and `is_stderr_mode` reports the effective destination.
- **Test de regresión:** internal `test "Logger stream helpers report their
  destination"`; external case asserts stderr vs stdout.

### BUG-20 (brief B20): `Logger.new("app")` twice built two independent loggers
- **Módulo:** std/whisper
- **Función:** `Logger.get_or_create`, `named_logger`
- **Síntoma:** Every `Logger.new` / `Logger.named` call produced a fresh value, so
  two subsystems asking for "app" could not share a level. Python's
  `logging.getLogger(name)` returns the same logger.
- **Causa raíz:** No registry. The language forbids top-level `var`, and the
  module had not used the `static var` accessor pattern.
- **Impacto:** Configuration drift: setting the level on one "app" logger left
  every other "app" logger at its old level.
- **Fix aplicado:** `_registry` is an accessor weave whose `static var` holds the
  one `map of string to Logger`, returned by reference. `Logger.get_or_create`
  registers on first use and returns the registered configuration thereafter;
  `Logger.set_level` publishes the new level back into the registry through
  `_registry_store_level`, so a later `get_or_create` observes it.
  `named_logger` is module-level sugar and `default_logger` now uses the registry
  too.
- **Test de regresión:** internal `test "BUG-20: Logger.get_or_create returns one
  registered logger per name"` and `test "BUG-20: a level set on a named logger is
  visible to a later get_or_create"`; external case in
  `tests/stdlib/test_whisper.py`.

### BUG-21 (brief B21): a failed file append was discarded silently
- **Módulo:** std/whisper
- **Función:** `Logger.log` (file path)
- **Síntoma:** `archivum.append_file` returns `bool`; the result was ignored. On a
  full disk or a permission error the line was simply lost and the program
  behaved as if it had been logged.
- **Causa raíz:** A fallible call whose result was dropped.
- **Impacto:** Silent audit-trail loss exactly when things are going wrong.
- **Fix aplicado:** `_emit` checks the `bool` and reports a failure on stderr
  (`whisper: cannot append to "…"`). The program is not interrupted.
- **Test de regresión:** internal `test "BUG-21: a logger pointed at an
  unwritable file does not crash"`; external case asserts the stderr message and
  exit code 0.

### BUG-22 (brief B22): the module was not thread-safe
- **Módulo:** std/whisper
- **Función:** `log`, `log_json`, `Logger.log`, `Logger.log_json*`
- **Síntoma:** Two threads emitting at once could interleave their bytes inside a
  single line.
- **Causa raíz:** `spark.println` / `archivum.append_file` were called with no
  mutual exclusion.
- **Impacto:** Corrupted log records, which is worse than a missing one.
- **Fix aplicado:** The same runtime-backed mutex pattern as `lot`
  (`_mtx` / `_lock` / `_unlock`) wraps every emission: the whole line, including
  the newline, is written inside the critical section.
- **Test de regresión:** the internal suite exercises every emission path through
  the locked code; `tests/stdlib/test_whisper.py` adds a concurrency smoke case.

### BUG-23 (brief B23): `Logger.child` accepted an unvalidated segment
- **Módulo:** std/whisper
- **Función:** `Logger.child`
- **Síntoma:** The child name was `"{parent}.{sub}"` with no checks. An empty
  `sub` produced a trailing dot (`"app."`); a segment with spaces or dots made the
  hierarchy unparseable.
- **Causa raíz:** String concatenation with no validation.
- **Impacto:** Broken logger names, ambiguous hierarchies, and `"app."` versus
  `"app"` treated as different loggers.
- **Fix aplicado:** `_child_name` returns the parent unchanged for an empty
  segment and replaces every byte outside `[A-Za-z0-9_.-]` with `_`.
- **Test de regresión:** internal `test "BUG-23: Logger.child sanitises empty and
  whitespace segments"`.

### BUG-24 (brief B24): the text layout was hard-coded
- **Módulo:** std/whisper
- **Función:** `Logger.set_format`, `_apply_format`
- **Síntoma:** Every line was `[LEVEL] [name] msg`; a caller could not request
  `{time} {level} {name}: {msg}` or any other shape.
- **Causa raíz:** The layout was built inline in `log`.
- **Impacto:** No way to match an existing log format without post-processing.
- **Fix aplicado:** `set_format` stores a template, `_apply_format` substitutes
  `{level}`, `{name}`, `{msg}` and `{time}`, unknown/unterminated placeholders are
  copied through, and `_format_line` uses the template when present. Templates are
  raw strings (`r"…"`), which the docstring shows.
- **Test de regresión:** internal `test "_apply_format substitutes the four
  placeholders"` and `test "Logger.set_format changes the rendered text layout"`.

### BUG-25 (new): the C symbol `log` collided with `math.h`
- **Módulo:** std/whisper
- **Función:** `log`
- **Síntoma:** When `std/whisper.pengu` was compiled as the **entry** module
  (`pengu test --entry std/whisper.pengu`), its top-level weave emitted an
  unprefixed C function literally named `log`. `<math.h>` declares
  `double log(double)`; the bundle failed to compile with
  `conflicting types for 'log'`. Imported modules get a `<module>_` prefix, so a
  user program never saw it — the module could not even build its own tests.
- **Causa raíz:** The module had no `insignia`, so its entry-module C names were
  unprefixed. `log`, `info`, `error` and `warn` are ordinary words that collide
  with libc or other translation units.
- **Impacto:** `pengu test --entry std/whisper.pengu` failed outright, and any
  program that compiled whisper as its entry would have failed too.
- **Fix aplicado:** `insignia whisper_` after the `declare` blocks (so the runtime
  bridges keep their exact `pengu_log_*` names). Every module symbol now emits as
  `whisper_*`, exactly like `spark`, `atlas`, `tally`, `loom`, `rites` and
  `archivum` already do.
- **Test de regresión:** the entire internal suite is the regression — it only
  compiles thanks to the insignia.

### BUG-26 (new): `default_logger` built a fresh logger on every call
- **Módulo:** std/whisper
- **Función:** `default_logger`
- **Síntoma:** The documented "default logger" was `Logger.new("default")` each
  time, so two callers held two different defaults.
- **Causa raíz:** Same missing registry as BUG-20.
- **Impacto:** Inconsistent default configuration.
- **Fix aplicado:** `default_logger` is now `Logger.get_or_create("default")`, so
  every caller shares the registered value.
- **Test de regresión:** covered by the BUG-20 internal tests and the external
  suite.

### BUG-27 (new): `set_level` on a singleton did not reach the registry
- **Módulo:** std/whisper
- **Función:** `Logger.set_level`
- **Síntoma:** Once `get_or_create` existed, a later `get_or_create` for the same
  name returned the *stored* level, so a `set_level` performed in between was
  silently lost.
- **Causa raíz:** The registry was write-once; the setter only touched the local
  value.
- **Impacto:** The singleton would have been a "same name, stale level" trap.
- **Fix aplicado:** `set_level` calls `_registry_store_level`, which re-publishes
  the updated configuration when the name is registered (and does nothing
  otherwise).
- **Test de regresión:** internal `test "BUG-20: a level set on a named logger is
  visible to a later get_or_create"`.

---

## Out-of-scope findings (compiler / tooling)

These are real defects found during Chunk 6. Fixing them requires touching the
compiler or the formatter, which §5.3 of the brief forbids. They are **not
ignored**: each is documented here, worked around inside this chunk, and handed
to the compiler workstream.

### C-1: const folding loses the raw-string flag for brace-bearing constants
- **Where:** `pengu_parser/pengu_codegen/constants.py::_format_const_val` →
  `interpolate.py::_translate_string_lit(as_c_literal=True)`.
- **Symptom:** A `const S as string is r"a{b}c"` passed as a function argument
  fails with `E0000 String interpolation is not supported when expecting a C
  string literal (ref to char)` — even in a plain `pengu run`, with no `test`
  block involved. Minimal reproduction:
  ```pengu
  const SYM as string is r"{}"
  weave show with s as string into void:
      calling spark.println with s
  weave main into int:
      calling show with SYM
      return 0
  ```
- **Root cause:** Folding a `const` string yields its *value*; the `r` marker that
  told the interpolation parser "braces are literal" is gone, so `{}` is parsed
  as an interpolation and the `as_c_literal` guard fires.
- **Impact:** Any brace-bearing constant (`{}`, `{x}`, JSON templates, regexes) is
  unusable as a call argument.
- **Workaround in Chunk 6:** `password_symbols` is a **weave** returning the raw
  literal, not a `const`. The raw-string form still removes the `chr` hack, and
  the value can be passed anywhere.

### C-2: dotted ritual calls (`module.Type.ritual`) do not resolve
- **Where:** method resolution for a `ritual` reached through a module-qualified
  type (`symbols.methods[(type_name, method)]`).
- **Symptom:** `calling whisper.Logger.get_or_create with "app"` fails with
  `E0004 Type 'whisper' has no method 'get_or_create'`. The same is true for every
  imported module (`m3.Thing.new` → `Type 'm3' has no method 'new'`) and for the
  pre-migration `std/whisper.pengu` as well, so it is not a Chunk 6 regression.
- **Root cause:** The resolver reads the first segment as the *type* name instead
  of the receiver of a qualified type path.
- **Impact:** The brief's §7.7 smoke program spells the constructor as
  `whisper.Logger.get_or_create`; that line cannot compile. The supported and
  documented form is the unqualified `calling Logger.get_or_create with "app"`
  (this is also what the existing conformance corpus uses).
- **Workaround in Chunk 6:** the public API is unchanged, and every docstring
  example uses the unqualified form.

### C-3: `pengu fmt` re-indents the whole file for a `/* … */` comment in an `antiquus` body
- **Where:** the formatter's raw-string / comment state tracking.
- **Symptom:** An `antiquus` body containing a C block comment makes
  `pengu fmt` treat every weave body in the file as one level deeper and rewrite
  the whole file (the `r"""` line became 16-space indented and every body line
  gained 12 spaces). `pengu fmt --check std/whisper.pengu` reported the whole file.
- **Root cause:** `/*` inside the raw body is tracked as a PenguScript comment and
  the indentation stack desynchronises; the closing `*/` is never seen where the
  formatter expects it.
- **Impact:** A module can be pushed out of `fmt --check` compliance by a single
  C comment, and running `fmt` produces a badly indented file.
- **Workaround in Chunk 6:** `_default_cell` uses `//` line comments instead of a
  `/* … */` block comment. This is recorded in the checklist so the next module
  does not rediscover it.

### C-4: `==` / `!=` between two module-level `string` values emits invalid C
- **Where:** string-equality lowering in the code generator.
- **Symptom:** `if whisper.COLOR_GREEN == whisper.COLOR_RESET:` (both operands are
  module-level `string` values) emits a raw C `==` between two `PenguString`
  structs: `invalid operands to binary == (have 'PenguString' and 'PenguString')`.
  Comparing a local `string` variable against a string literal (what
  `std/whisper` itself does through `parse_level_string`) is lowered correctly.
- **Root cause:** Only the local-versus-literal shape reaches the
  `pengu_string_equal` helper; the two-symbols shape does not.
- **Impact:** A user cannot compare two exported string constants directly;
  `std/whisper`'s own tests had to print the constants and compare in Python.
- **Workaround in Chunk 6:** the external suite prints `COLOR_*` and compares the
  bytes on the Python side. No module code relies on the unsupported shape.

### C-5: `"…{(chr 34)}…"` folds a raw quote into the generated C literal
- **Where:** constant folding of an interpolation whose expression is a literal
  character.
- **Symptom:** `"a{(chr 34)}b"` folds to `"a"b"` in the generated C, producing
  `expected ')' before 'b'` / an unterminated string.
- **Root cause:** The folded value is re-escaped as a C literal without escaping
  the interpreter-generated quote.
- **Impact:** Building a string that contains a double quote from `chr 34` (rather
  than the `\"` source escape) breaks the build.
- **Workaround in Chunk 6:** `_json_escape` uses `\"` source escapes, and the
  external suite does the same.

---

## Summary

| Module | Brief bugs | New bugs | Total fixed |
|---|---|---|---|
| `std/lot` | B1–B11 (11) | BUG-12, BUG-13 (2) | **13** |
| `std/whisper` | B12–B24 (13) | BUG-25, BUG-26, BUG-27 (3) | **16** |
| **Total** | **24** | **5** | **29** |

Out-of-scope compiler/tooling findings: **5** (C-1 … C-5), each documented and
worked around.
