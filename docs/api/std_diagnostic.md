# std.diagnostic

> Source: `std/diagnostic.pengu`

std/diagnostic.pengu — source spans, labels and Rust-style diagnostics.

A general diagnostic system, not a compiler-only one: linters, validators,
migration tools and the self-hosted LSP all need the same primitives — a
position, a severity, an optional code, a message, and one or more marked
ranges. `std.diagnostic` provides them with a renderer modelled on
`rustc`/`codespan-reporting`, ANSI colour, and an LSP-compatible JSON form.

## Example
```pengu
import std.diagnostic as diag
import std.spark

weave main into int:
    var bag as DiagnosticBag is calling DiagnosticBag.new
    defer banish bag
    calling bag.add_source with "src/main.pengu", "var x as int is \"hello\"\n"

    var span as Span is calling diag.span_from_positions with "src/main.pengu", 1, 18, 1, 25, 17, 24
    calling bag.add with (calling diag.diagnostic with diag.Severity.Error, "E0005", "expected 'int', found 'string'", (calling diag.labels with (calling diag.label with span, "expected 'int' here", true)), (some "use '(s to int)'"))
    var text as string is calling bag.render_colored
    defer banish text
    calling spark.print with text
    return 0
```

Output (colours omitted):
```text
error[E0005]: expected 'int', found 'string'
  --> src/main.pengu:1:18
   |
 1 | var x as int is "hello"
   |                  ^^^^^^^ expected 'int' here
   |
   = help: use '(s to int)'
```

## Ownership (read this once)
- A `Span` owns its `file` string. `span_from_positions` copies the path, so
  the caller keeps its own string; `banish span` releases the copy.
- `Label` owns its `Span` and its `message`. The `label` helper takes
  ownership of the span and copies the message.
- `Diagnostic` owns its `message`, `code`, `labels`, `help`, `note` and
  `related`. The `diagnostic` helper copies `code`/`message`, takes ownership
  of the label list and of the `related` list, and boxes `help`/`note`
  copies.
- `DiagnosticBag` owns every `Diagnostic` it holds plus the sources added
  with `add_source`. `banish bag` releases the whole bag recursively.
- `errors_only` / `warnings_and_errors` return **deep copies**; release the
  list with `free_diagnostics`.

## Sources and context
A `Span` stores only a path, never the file contents. Register the text with
`DiagnosticBag.add_source` to get source context in the render. Without it,
the renderer still prints the primary position and every label message, but
no source line — which is exactly what a tool that only has positions (a
log parser, a remote LSP client) can do.

## Complexity
| Operation | Cost |
|---|---|
| `add`, `extend`, `error`, ... | O(1) amortised |
| `len`, `is_empty`, counts | O(1) |
| `errors_only`, `warnings_and_errors` | O(number of copied diagnostics) |
| `render`, `render_json` | O(labels × context lines + output size) |
| `clear` | O(items + sources) |

## Multiple labels on one line
Each label gets its own marker row, in label order: `^^^^` for a primary
label and `----` for a secondary one. Overlapping carets are therefore
always readable, at the cost of one row per label. This is a deliberate
choice (the alternative — one merged row with `|` separators — hides which
message belongs to which range).

---

### `DIAGNOSTIC_VERSION`

> **DIAGNOSTIC_VERSION** : string

 Diagnostic module version.

### `DIAGNOSTIC_SEVERITY_ERROR`

> **DIAGNOSTIC_SEVERITY_ERROR** : int

 LSP severity number for `Severity.Error`.

### `DIAGNOSTIC_SEVERITY_WARNING`

> **DIAGNOSTIC_SEVERITY_WARNING** : int

 LSP severity number for `Severity.Warning`.

### `DIAGNOSTIC_SEVERITY_INFO`

> **DIAGNOSTIC_SEVERITY_INFO** : int

 LSP severity number for `Severity.Info`.

### `DIAGNOSTIC_SEVERITY_HINT`

> **DIAGNOSTIC_SEVERITY_HINT** : int

 LSP severity number for `Severity.Hint`.

### `DIAGNOSTIC_ANSI_RESET`

> **DIAGNOSTIC_ANSI_RESET** : string

 ANSI reset sequence.

### `DIAGNOSTIC_ANSI_ERROR`

> **DIAGNOSTIC_ANSI_ERROR** : string

 ANSI bold-red sequence (errors).

### `DIAGNOSTIC_ANSI_WARNING`

> **DIAGNOSTIC_ANSI_WARNING** : string

 ANSI bold-yellow sequence (warnings).

### `DIAGNOSTIC_ANSI_INFO`

> **DIAGNOSTIC_ANSI_INFO** : string

 ANSI bold-blue sequence (info).

### `DIAGNOSTIC_ANSI_HINT`

> **DIAGNOSTIC_ANSI_HINT** : string

 ANSI bold-cyan sequence (hints).

### `Span`

> rune Span

```pengu
    file as string
    start_line as int
    start_col as int
    end_line as int
    end_col as int
    start_byte as int
    end_byte as int
```

 A range in a source file.

 Lines and columns are **1-indexed** and columns are byte columns (the same
 convention as `std.sourcemap`), so `start_byte + start_col - 1` is exact.
 `start_byte`/`end_byte` are absolute byte offsets; they are used for
 ordering and for JSON consumers that index a buffer directly.

 ## Memoria
 Owns `file`; `banish span` releases it.

### `Severity`

> omen Severity

```pengu
    Error
    Warning
    Info
    Hint
```

 Severity of a diagnostic.

### `Label`

> rune Label

```pengu
    span as Span
    message as string
    primary as bool
```

 A secondary annotation inside a diagnostic.

 ## Memoria
 Owns its `span` (and therefore the file path) and its `message`.

### `Diagnostic`

> rune Diagnostic

```pengu
    severity as Severity
    code as string
    message as string
    labels as list of Label
    help as maybe string
    note as maybe string
    related as list of Diagnostic
```

 A complete diagnostic.

 `labels` may be empty (a diagnostic without a position, such as "internal
 error"), and a label list without a `primary` label is treated as
 positionaless by the renderer.

 ## Memoria
 Owns every field; `banish d` releases the labels, messages and related list.

### `RenderOptions`

> rune RenderOptions

```pengu
    color as bool
    context_lines as int
    show_notes as bool
    show_help as bool
    show_related as bool
    tab_width as int
    force_color as bool
```

 Render options.

### `DiagnosticBag`

> rune DiagnosticBag

```pengu
    items as list of Diagnostic
    error_count as int
    warning_count as int
    info_count as int
    hint_count as int
    _sources as map of string to string
```

 A bag of diagnostics plus their counts and source texts.

 ## Memoria
 Owns `items` and `_sources`. `banish bag` releases everything, including the
 nested diagnostics and the copied source texts.

### `_diagnostic_is_tty`

> **_diagnostic_is_tty**() -> bool

 Reports whether stdout is a terminal.

 ## Motivo
 The runtime already includes `<unistd.h>` / `<io.h>`, so the POSIX and
 Windows spellings can live in one guarded function without a new link.

 ## Memoria
 Reads only; no allocation.

### `_diagnostic_line_count`

> **_diagnostic_line_count**(s: string) -> int

 Number of lines in a source text (at least one).

 ## Motivo
 The renderer only needs line starts; keeping the line scanner here avoids
 pulling a second source-mapping module into every diagnostics build.
 (`std.sourcemap` names its range `SourceSpan` since 2.19, so the old
 `Span` clash is gone; this module keeps its own `Span` for API stability.)

 ## Memoria
 Reads only; allocates nothing.

### `_diagnostic_line_text`

> **_diagnostic_line_text**(s: string, line: int) -> string

 Returns an owned copy of a 1-indexed line, without its terminator.

 ## Motivo
 Same as `_diagnostic_line_count`: one small bridge instead of importing
 another module for a line scan.

 ## Memoria
 Returns an owned string; release it with `banish`.

### `_diagnostic_streq`

> **_diagnostic_streq**(a: string, b: string) -> bool

 Compares two strings byte-wise.

 ## Motivo
 General string `==` through two nested field accesses (`a.span.file ==
 b.span.file`) reaches C without the runtime helper; routing it through C
 keeps the comparison explicit and always correct.

 ## Memoria
 Reads only; allocates nothing.

### `_diagnostic_clone`

> **_diagnostic_clone**(d: Diagnostic) -> Diagnostic

 Deep-copies a diagnostic with the derived `Imago` callback.

 ## Motivo
 `errors_only` and `warnings_and_errors` must return independent values; the
 derived helper is a C symbol.

 ## Memoria
 Returns a fully independent diagnostic; release it with `banish`.

### `default_render_options`

> **default_render_options**() -> RenderOptions

 The strict default render options.

 ## Retorno
 `{color: true, context_lines: 2, show_notes: true, show_help: true,
 show_related: true, tab_width: 4, force_color: false}`.

 ## Ejemplo
 ```pengu
 var opts as RenderOptions is calling diagnostic.default_render_options
 ```

### `span_from_positions`

> **span_from_positions**(file: string, sl: int, sc: int, el: int, ec: int, sb: int, eb: int) -> Span

 Builds a span from explicit positions.

 ## Parámetros
 - `file`: logical path. **Copied**; the caller keeps its string.
 - `sl`, `sc`: start line and byte column (1-indexed).
 - `el`, `ec`: end line and byte column (1-indexed).
 - `sb`, `eb`: absolute start/end byte offsets.

 ## Retorno
 A `Span` owning a copy of `file`.

 ## Efectos
 Panics when `(sl, sc, sb) > (el, ec, eb)`: a reversed span is a bug in the
 caller, not something to silently swap.

 ## Ejemplo
 ```pengu
 var s as Span is calling diagnostic.span_from_positions with "a.pengu", 3, 5, 3, 9, 21, 25
 ```

### `span_point`

> **span_point**(file: string, line: int, col: int, byte_offset: int) -> Span

 Builds a zero-width span at one position.

 ## Parámetros
 - `file`: logical path. Copied.
 - `line`, `col`: 1-indexed position.
 - `byte_offset`: absolute byte offset.

 ## Retorno
 A `Span` whose start and end are the same point.

### `span_merge`

> **span_merge**(a: Span, b: Span) -> Span

 Merges two spans into one covering both.

 The result keeps `a`'s file path. Merging spans from different files is
 allowed (the caller may use it to build a "from here to there" hint), but the
 renderer will group them by the result's single path; document that at the
 call site when it matters.

 ## Parámetros
 - `a`, `b`: spans. Borrowed; the result owns a fresh copy of `a.file`.

 ## Retorno
 A `Span` from the earlier start to the later end.

 ## Ejemplo
 ```pengu
 var both as Span is calling diagnostic.span_merge with first, second
 ```

### `label`

> **label**(span: Span, message: string, primary: bool) -> Label

 Builds a label, taking ownership of `span` and copying `message`.

 ## Parámetros
 - `span`: the range. **Ownership transfers**; do not banish it afterwards.
 - `message`: the marker text. Copied.
 - `primary`: `true` for `^^^^`, `false` for `----`.

 ## Retorno
 A `Label` owning the span and a copy of the message.

### `labels`

> **labels**(one: Label) -> list of Label

 Builds a label list from one label.

 ## Parámetros
 - `one`: the label. Ownership transfers.

 ## Retorno
 A one-element `list of Label`.

### `no_labels`

> **no_labels**() -> list of Label

 Builds an empty label list.

 ## Retorno
 A `list of Label` with no elements.

### `no_related`

> **no_related**() -> list of Diagnostic

 Builds an empty related list.

 ## Retorno
 An empty `list of Diagnostic`.

### `diagnostic`

> **diagnostic**(severity: Severity, code: string, message: string, labels_list: list of Label, help: maybe string, note: maybe string, related: list of Diagnostic) -> Diagnostic

 Builds a diagnostic.

 ## Parámetros
 - `severity`: the severity.
 - `code`: a stable code; `""` for none. Copied.
 - `message`: the headline. Copied.
 - `labels`: positional annotations. **Ownership transfers.**
 - `help`: an optional suggestion. Ownership of the `maybe string` transfers.
 - `note`: an optional explanation. Ownership transfers.
 - `related`: see-also diagnostics. Ownership transfers.

 ## Retorno
 A `Diagnostic` owning all of the above.

 ## Ejemplo
 ```pengu
 var d as Diagnostic is calling diagnostic.diagnostic with diagnostic.Severity.Warning, "lint/no-shadow", "shadows an outer binding", (calling diagnostic.labels with (calling diagnostic.label with s, "shadowed here", true)), (maybe none), (maybe none), (calling diagnostic.no_related)
 ```

### `free_diagnostics`

> **free_diagnostics**(items: list of Diagnostic) -> void

 Releases every diagnostic of a list, then the list itself.

 ## Parámetros
 - `items`: an owned `list of Diagnostic` (typically from `errors_only`).

 ## Retorno
 Nothing.

 ## Memoria
 Releases each diagnostic recursively, then the list buffer.

### `severity_number`

> **severity_number**(sev: Severity) -> int

 Returns the LSP numeric severity (1 error, 2 warning, 3 info, 4 hint).

 ## Parámetros
 - `sev`: a severity.

 ## Retorno
 `1..4`.

### `severity_name`

> **severity_name**(sev: Severity) -> string

 Returns the lowercase severity name.

 ## Parámetros
 - `sev`: a severity.

 ## Retorno
 `"error"`, `"warning"`, `"info"` or `"hint"`.

### `severity_color`

> **severity_color**(sev: Severity) -> string

 Returns the ANSI prefix for a severity.

 ## Parámetros
 - `sev`: a severity.

 ## Retorno
 One of the `DIAGNOSTIC_ANSI_*` constants.

### `new`

> **new**() -> DiagnosticBag

 Constructs an empty bag.

 ## Retorno
 A bag with no diagnostics, zero counters and no sources.

 ## Memoria
 O(1); release it with `banish`.

### `add`

> **add**(d: Diagnostic) -> void

 Adds a diagnostic, taking ownership of it.

 ## Parámetros
 - `d`: the diagnostic. Ownership transfers to the bag.

 ## Efectos
 Increments the matching severity counter.

### `extend`

> **extend**(ds: list of Diagnostic) -> void

 Adds every diagnostic of a list, taking ownership of the elements.

 The source list buffer is left empty but still allocated: `banish` it
 after the call (the elements now belong to the bag).

 ## Parámetros
 - `ds`: diagnostics. Element ownership transfers.

### `error`

> **error**(message: string, span: Span) -> void

 Adds an `Error` diagnostic with one primary label.

 ## Parámetros
 - `message`: the headline. Copied.
 - `span`: the position. Ownership transfers to the label.

### `warning`

> **warning**(message: string, span: Span) -> void

 Adds a `Warning` diagnostic with one primary label.

 ## Parámetros
 - `message`: the headline. Copied.
 - `span`: the position. Ownership transfers.

### `info`

> **info**(message: string, span: Span) -> void

 Adds an `Info` diagnostic with one primary label.

 ## Parámetros
 - `message`: the headline. Copied.
 - `span`: the position. Ownership transfers.

### `hint`

> **hint**(message: string, span: Span) -> void

 Adds a `Hint` diagnostic with one primary label.

 ## Parámetros
 - `message`: the headline. Copied.
 - `span`: the position. Ownership transfers.

### `add_source`

> **add_source**(file: string, text: string) -> void

 Registers the source text of `file`, copying both strings.

 Re-registering the same path replaces the previous text.

 ## Parámetros
 - `file`: logical path. Borrowed; copied.
 - `text`: file contents. Borrowed; copied.

### `source`

> **source**(file: string, text: string) -> void

 Adds the contents of `path` after the caller has read them.

 This is a convenience alias of `add_source`; the module never touches the
 filesystem itself, so a remote LSP client can register in-memory buffers.

 ## Parámetros
 - `file`: logical path used by spans. Copied.
 - `text`: source text. Copied.

### `len`

> **len**() -> int

 Number of diagnostics.

### `is_empty`

> **is_empty**() -> bool

 True when the bag has no diagnostics.

### `has_errors`

> **has_errors**() -> bool

 True when at least one diagnostic is an `Error`.

### `has_warnings`

> **has_warnings**() -> bool

 True when at least one diagnostic is a `Warning`.

### `count_by_severity`

> **count_by_severity**(sev: Severity) -> int

 Counts the diagnostics of one severity.

 ## Parámetros
 - `sev`: the severity to count.

 ## Retorno
 The matching stored counter.

### `errors_only`

> **errors_only**() -> list of Diagnostic

 Deep copies of every `Error` diagnostic, in insertion order.

 ## Retorno
 An owned `list of Diagnostic`; release it with `free_diagnostics`.

### `warnings_and_errors`

> **warnings_and_errors**() -> list of Diagnostic

 Deep copies of every `Warning` and `Error`, in insertion order.

 ## Retorno
 An owned `list of Diagnostic`; release it with `free_diagnostics`.

### `clear`

> **clear**() -> void

 Removes every diagnostic and every registered source.

 ## Memoria
 Releases the nested diagnostics and the source copies; the bag remains
 usable.

### `has_source`

> **has_source**(file: string) -> bool

 True when `file` has a registered source.

 ## Parámetros
 - `file`: logical path. Borrowed.

### `source_of`

> **source_of**(file: string) -> maybe string

 The registered source text as an owned copy.

 ## Parámetros
 - `file`: logical path. Borrowed.

 ## Retorno
 `some text` (an owned copy; release it with `banish`) or `none`.

### `_digits`

> **_digits**(n: int) -> int

 Number of decimal digits in a non-negative integer.

 ## Parámetros
 - `n`: a value `>= 0`.

 ## Retorno
 At least `1`.

### `_visual_col`

> **_visual_col**(line: string, byte_col: int, tab_width: int) -> int

 Visual column of a byte column inside one line.

 Tabs advance to the next multiple of `tab_width`; a multibyte UTF-8
 codepoint counts as one column (its continuation bytes count as zero). This
 is what makes a caret line up under `ñ` or an emoji even though `Span`
 columns are byte offsets.

 ## Parámetros
 - `line`: the line text (no trailing `\n`).
 - `byte_col`: number of bytes before the target column.
 - `tab_width`: tab stop width.

 ## Retorno
 A non-negative visual column.

### `_visual_width`

> **_visual_width**(line: string, start_byte: int, end_byte: int, tab_width: int) -> int

 Visual width of a byte range inside one line.

 ## Parámetros
 - `line`: the line text.
 - `start_byte`: first byte offset in the line.
 - `end_byte`: one past the last byte offset in the line.
 - `tab_width`: tab stop width.

 ## Retorno
 At least `1`, so a zero-width point still gets one caret.

### `_has_string`

> **_has_string**(xs: list of string, needle: string) -> bool

 True when a `list of string` contains `needle`.

 ## Parámetros
 - `xs`: strings to scan. Borrowed.
 - `needle`: the value to find. Borrowed.

### `_gutter_row`

> **_gutter_row**(sb: ref to StringBuilder, gutter: int) -> void

 Appends an empty-gutter separator row (`   |`).

 ## Parámetros
 - `sb`: destination builder. Mutated.
 - `gutter`: width of the line-number column.

### `_marker_row`

> **_marker_row**(sb: ref to StringBuilder, gutter: int, line_text: string, label: Label, end_col: int, opts: RenderOptions) -> void

 Appends one labelled marker row for a span.

 ## Parámetros
 - `sb`: destination builder. Mutated.
 - `gutter`: width of the line-number column.
 - `line_text`: the source line. Borrowed.
 - `label`: the annotation. Borrowed.
 - `end_col`: exclusive end byte column in the line (1-indexed).
 - `opts`: render options.

### `_render_group`

> **_render_group**(bag: ref to DiagnosticBag, group: list of Label, opts: RenderOptions, color: bool, sb: ref to StringBuilder) -> void

 Renders one file group of a diagnostic.

 ## Parámetros
 - `bag`: the bag (for registered sources). Borrowed.
 - `group`: labels sharing one file. Borrowed.
 - `opts`: render options.
 - `color`: effective colour flag (only used by the caller's header).
 - `sb`: destination builder. Mutated.

### `_render_one`

> **_render_one**(bag: ref to DiagnosticBag, d: Diagnostic, opts: RenderOptions, color: bool, sb: ref to StringBuilder) -> void

 Renders one diagnostic (header, groups, notes, related).

 ## Parámetros
 - `bag`: the bag (for sources). Borrowed.
 - `d`: the diagnostic. Borrowed.
 - `opts`: render options.
 - `color`: effective colour flag.
 - `sb`: destination builder. Mutated.

### `_main_span`

> **_main_span**(d: Diagnostic) -> Span

 Returns the main span of a diagnostic (first primary label), or a zero
 span when it has no positional label.

 ## Parámetros
 - `d`: the diagnostic. Borrowed.

 ## Retorno
 The primary `Span`, possibly `{file:"", line:1, col:1, ...}`.

### `_color_enabled`

> **_color_enabled**(requested: bool) -> bool

 True when colour should be used for `requested`.

 ## Parámetros
 - `requested`: the caller's colour preference.

 ## Retorno
 `false` when `requested` is false, when `NO_COLOR` is set, or when stdout is
 not a TTY; `true` otherwise.

### `render`

> **render**(opts: RenderOptions) -> string

 Renders every diagnostic with explicit options.

 ## Parámetros
 - `opts`: render options.

 ## Retorno
 An owned string (each diagnostic is separated by a blank line). Release
 it with `banish`.

 ## Efectos
 Colour is used only when `opts.color` is true **and** `opts.force_color`
 is true, or when `opts.color` is true and stdout is a TTY with
 `NO_COLOR` unset.

### `render_plain`

> **render_plain**() -> string

 Renders every diagnostic without colour.

 ## Retorno
 An owned string; release it with `banish`.

### `render_colored`

> **render_colored**() -> string

 Renders every diagnostic with ANSI colour, honouring `NO_COLOR` and TTY
 detection.

 ## Retorno
 An owned string; release it with `banish`.

### `_lsp_position`

> **_lsp_position**(line: int, col: int) -> JsonValue

 Builds an LSP `Position` object from a 1-indexed `(line, col)`.

 LSP positions are 0-indexed. `character` is a byte column, matching
 `Span.start_col`/`end_col`; clients that need UTF-16 code units can convert
 with the source text.

 ## Parámetros
 - `line`: 1-indexed line.
 - `col`: 1-indexed byte column.

 ## Retorno
 An owned `JsonValue` object; the caller releases the containing tree.

### `_lsp_range`

> **_lsp_range**(span: Span) -> JsonValue

 Builds an LSP `Range` object from a span.

 ## Parámetros
 - `span`: the source span. Borrowed.

 ## Retorno
 An owned `JsonValue` object.

### `_utf16_len`

> **_utf16_len**(s: string) -> int

 Cuenta code units UTF-16 de un prefijo.

### `_line_start`

> **_line_start**(text: string, line: int) -> int

 Offset de byte de una línea 1-indexed.

### `_lsp_position_u16`

> **_lsp_position_u16**(text: string, line: int, col: int) -> JsonValue

 Posición UTF-16 de un span.

### `_lsp_range_u16`

> **_lsp_range_u16**(text: string, span: Span) -> JsonValue

 Range UTF-16 de un span.

### `_lsp_diagnostic_u16`

> **_lsp_diagnostic_u16**(sources: map of string to string, d: Diagnostic) -> JsonValue

 Diagnóstico LSP con posiciones UTF-16.

### `_lsp_location`

> **_lsp_location**(file: string, span: Span) -> JsonValue

 Builds an LSP `Location` object.

 ## Parámetros
 - `file`: logical path. Borrowed.
 - `span`: the range inside `file`. Borrowed.

 ## Retorno
 An owned `JsonValue` object.

### `_lsp_diagnostic`

> **_lsp_diagnostic**(d: Diagnostic) -> JsonValue

 Builds one LSP `Diagnostic` object.

 ## Parámetros
 - `d`: the diagnostic. Borrowed.

 ## Retorno
 An owned `JsonValue` object.

### `render_json`

> **render_json**() -> string

 Renders every diagnostic as a JSON array of LSP `Diagnostic` objects.

 Each object has `range`, `severity`, an optional `code`, `source:
 "pengu"`, `message`, and `relatedInformation` when there are secondary
 labels or `related` diagnostics. Positions are 0-indexed. An empty bag
 renders as `[]`.

 ## Retorno
 An owned JSON string; release it with `banish`.

 ## Ejemplo
 ```pengu
 var payload as string is calling bag.render_json
 defer banish payload
 ```

### `render_json_utf16`

> **render_json_utf16**() -> string

 Como `render_json`, pero `character` en UTF-16.

