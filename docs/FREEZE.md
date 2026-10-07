# PenguScript 1.0 — Public API Freeze

> Frozen at **1.0.0** (2026-10-07). Nothing on this surface changes without a MAJOR.
> Every `<!-- freeze:… -->` block below is read back by
> [`tests/test_freeze_manifest.py`](tests/test_freeze_manifest.py) and compared against the
> tree itself (parser introspection, files on disk, the error catalog, the LSP feature
> registry), so this file is a manifest rather than an essay: if the code drifts from it,
> the build fails.
>
> "🔒 Frozen" means a change needs `2.0`. "🟡 Permitted in 1.x" means the surface exists but
> its shape is explicitly not promised.

## 1. Language

| Surface | State | Why |
|---|---|---|
| Reserved words (LANGUAGE.md §3.4) | 🔒 Frozen — 69 tokens | A new reserved word breaks source compatibility; additions need 2.0 |
| Soft keywords (`frozen`, `inline`, `ritual`) | 🔒 Frozen | Contextual only, so they can be used as identifiers; the *positions* are promised. `borrowed` was a soft keyword and was removed in 1.0 |
| Range syntax `a to b` | 🔒 Frozen as canonical | `..` is deprecated (`W0013`), kept through 1.x, removed in 2.0 |
| `ref to frozen T` | 🔒 Frozen as canonical | `frozen ref to T` is an accepted alias that normalises to it (LANGUAGE.md §9.5) |
| Primitive → C type table (LANGUAGE.md §4.1) | 🔒 Frozen | It is the ABI |
| Semantics of `weave`/`rune`/`omen`/`enchanting`/`ritual`/`shard`/`where`/`judge`/`with:` | 🔒 Frozen | The core language |
| Diagnostics *codes* `Exxxx`/`Wxxxx` | 🔒 Frozen (§6) | Tooling keys off them |
| Diagnostic *wording* | 🟡 Permitted in 1.x | Humans read it; nothing parses it |

<!-- freeze:keywords -->
```text
alias
and
as
banish
bind
break
bytes
calling
chr
concept
const
continue
cyclus
declare
defer
defined
derive
donum
echo
else
enchanting
errdefer
error
essence
false
for
from
if
import
in
include
insignia
into
is
judge
lambda
let
link
many
maybe
none
not
null
of
omen
or
ord
return
rune
seal
set
shard
sigil
size
some
static
step
test
to
transmute
true
try
unless
var
weave
when
where
while
with
```
<!-- /freeze:keywords -->

<!-- freeze:soft-keywords -->
```text
frozen
inline
ritual
```
<!-- /freeze:soft-keywords -->

## 2. ABI

`PENGU_ABI_VERSION` is **2**. The runtime layout (PenguString, PenguList, PenguMap,
PenguMaybe, PenguResult, the frame stack) is frozen for 1.x; changing any layout is a
two-step operation documented in [`docs/ABI.md`](docs/ABI.md).

v2 is the manual-memory layout: `PenguList` (24 bytes) and `PenguMap` (32 bytes) no
longer carry element cleanup/clone callbacks, and containers never clone on store.

| Surface | State | Why |
|---|---|---|
| `PENGU_ABI_VERSION` | 🔒 Frozen at 2 | A bump means a binary-incompatible layout change |
| Struct layouts in `pengu_runtime.h` | 🔒 Frozen | Same reason |
| The `_Static_assert` + `pengu_abi_version()` link gate | 🔒 Frozen | It is how a mismatched archive fails loudly |
| Adding a **new** exported runtime symbol | 🟡 Permitted in 1.x | Additive; guarded by `tests/test_abi_version.py` |

<!-- freeze:abi-version -->
```text
PENGU_ABI_VERSION = 2
```
<!-- /freeze:abi-version -->

## 3. CLI

Global flags are exactly the ones on the top-level parser. `--verbose` and `-D` are **not**
global: each subcommand that has them declares its own (measured:
`create_cli_parser()._actions`).

| Surface | State | Why |
|---|---|---|
| The 27 subcommand names | 🔒 Frozen | Scripts and CI invoke them |
| Global flags | 🔒 Frozen | `--quiet`, `--no-color` are the whole cross-cutting surface |
| Exit-code contract | 🔒 Frozen | `0` success, `1` compilation/program failure, `2` usage error |
| `--help` text and per-subcommand flags | 🟡 Permitted in 1.x | Additive flags are allowed; removal is not |
| Output formatting of any subcommand | 🟡 Permitted in 1.x | Except `--json` payload *keys*, which are additive-only |

<!-- freeze:global-flags -->
```text
--help
--no-color
--quiet
--version
```
<!-- /freeze:global-flags -->

<!-- freeze:subcommands -->
```text
add
assets
benchmark
bind
build
check
clean
doc
doctor
eval
expand
fmt
gc
init
lsp
metadata
new
remove
run
test
time
tree
update
upgrade
vendor
verify
watch
```
<!-- /freeze:subcommands -->

<!-- freeze:rc-contract -->
```text
0  success
1  compilation error, type error, or a program that exited non-zero
2  usage error (unknown flag, unknown subcommand, missing argument)
```
<!-- /freeze:rc-contract -->

## 4. Stdlib

27 pure modules + 25 C bindings = **52**.
The version policy is LANGUAGE.md §19.0: every `<MODULE>_VERSION` constant holds the
**toolchain** version, not an independent module version.

| Surface | State | Why |
|---|---|---|
| Module names and file paths | 🔒 Frozen | `import std.<name>` is the API |
| Public `weave`/`rune` signatures | 🔒 Frozen | Additive parameters with defaults only |
| `<MODULE>_VERSION` policy (§19.0) | 🔒 Frozen | One version for the toolchain |
| Deprecated aliases in `docs/DEPRECATIONS.md` | 🔒 Kept for all of 1.x | Removed in 2.0 |
| The 3 opt-in modules (`celeris`, `xlsx`, `trial`) | 🔒 Stay opt-in | They pull heavy dependencies; never auto-imported |
| The bodies of the modules | 🟡 Permitted in 1.x | Behaviour-preserving rewrites are not a break |

<!-- freeze:stdlib-modules -->
```text
archivum.pengu
arithmancy.pengu
atlas.pengu
celeris.pengu
chronicle.pengu
cipher.pengu
compass.pengu
coven.pengu
ffi.pengu
filum.pengu
invoke.pengu
ledger.pengu
loom.pengu
lot.pengu
oracle.pengu
parchment.pengu
precis.pengu
regulus.pengu
rites.pengu
scrolls.pengu
seal.pengu
spark.pengu
tally.pengu
trial.pengu
ward.pengu
whisper.pengu
xlsx.pengu
```
<!-- /freeze:stdlib-modules -->

<!-- freeze:stdlib-bindings -->
```text
datastructura.d.pengu
fenestra.d.pengu
imago.d.pengu
miniaudio.d.pengu
minicoro.d.pengu
nanosvg.d.pengu
nanosvgrast.d.pengu
pactum.d.pengu
perlinum.d.pengu
raygui.d.pengu
raylib.d.pengu
raymath.d.pengu
rlgl.d.pengu
rlights.d.pengu
scriptor.d.pengu
sqlite3.d.pengu
stb_herringbone_wang_tile.d.pengu
stb_image_resize2.d.pengu
tomlum.d.pengu
typis.d.pengu
uuid.d.pengu
webui.d.pengu
xlsxio.d.pengu
xxhash.d.pengu
yaml.d.pengu
```
<!-- /freeze:stdlib-bindings -->

<!-- freeze:opt-in-modules -->
```text
celeris.pengu
trial.pengu
xlsx.pengu
```
<!-- /freeze:opt-in-modules -->

## 5. LSP

The promised surface is the set of `textDocument/*` and `workspace/*` features this server
registers, measured below. Capability *shapes* come from `pygls`/`lsprotocol`, so the freeze
is on the feature list, not on the JSON schema of each request.

| Surface | State | Why |
|---|---|---|
| Registered features (21) | 🔒 Frozen | Editors bind to them |
| `textDocument/formatting`, `definition`, `references`, `rename`, `workspace/symbol` | 🔒 Frozen | Published in the editor docs |
| `pengu.runTest` code-lens command | 🔒 Frozen | The VS Code extension invokes it by name |
| Adding a new feature | 🟡 Permitted in 1.x | Additive |
| Message wording of a diagnostic | 🟡 Permitted in 1.x | Only the code is promised |

<!-- freeze:lsp-features -->
```text
textDocument/codeAction
textDocument/codeLens
textDocument/completion
textDocument/definition
textDocument/didSave
textDocument/documentHighlight
textDocument/documentSymbol
textDocument/foldingRange
textDocument/formatting
textDocument/hover
textDocument/implementation
textDocument/inlayHint
textDocument/onTypeFormatting
textDocument/prepareRename
textDocument/references
textDocument/rename
textDocument/semanticTokens/full
textDocument/signatureHelp
workspace/didChangeConfiguration
workspace/didChangeWatchedFiles
workspace/symbol
```
<!-- /freeze:lsp-features -->

## 6. Diagnostics

64 error codes and 9 warning codes. The catalogue is
[`docs/error_catalog.json`](docs/error_catalog.json); code numbers are never reused, so a
retired code leaves a hole rather than being recycled (`E0059`/`E0060` are such holes).

| Surface | State | Why |
|---|---|---|
| The `Exxxx`/`Wxxxx` identifiers | 🔒 Frozen | `--deny-deprecated`, CI greps and editor actions key off them |
| Severity of a code | 🔒 Frozen | Changing it changes CI outcomes |
| The human-readable message | 🟡 Permitted in 1.x | Explicitly out of the freeze |
| Adding a new code | 🟡 Permitted in 1.x | Must be added to the catalogue (gated) |

<!-- freeze:error-codes -->
```text
E0000
E0001
E0002
E0003
E0004
E0005
E0006
E0007
E0008
E0009
E0010
E0011
E0012
E0013
E0014
E0015
E0016
E0017
E0018
E0019
E0020
E0021
E0022
E0023
E0024
E0025
E0026
E0027
E0028
E0029
E0030
E0031
E0032
E0033
E0034
E0035
E0036
E0037
E0038
E0039
E0040
E0041
E0042
E0043
E0044
E0045
E0046
E0049
E0050
E0051
E0052
E0053
E0054
E0055
E0056
E0057
E0058
E0061
E0062
E0063
E0064
E0065
```
<!-- /freeze:error-codes -->

<!-- freeze:warning-codes -->
```text
W0000
W0001
W0002
W0003
W0004
W0005
W0006
W0007
W0013
```
<!-- /freeze:warning-codes -->

## 7. Outside the freeze

Explicitly **not** promised in 1.x — a 1.x release may change any of these:

| Surface | Why it is out |
|---|---|
| Iteration order of `map` | Documented as hash order, not insertion order |
| Inlining heuristic | A performance knob, not semantics |
| Exact wording/formatting of diagnostics | Only the code and the severity are frozen |
| `pengu benchmark` output layout | Informational |
| `.pengu`/cache/temp file layout on disk | Internal |
| Compiler-internal Python module structure | Only the CLI and the emitted C are the interface |
| Timing of the frame-trace instrumentation | A documented knob (`PENGU_FRAME_TRACE`), not a promise |
