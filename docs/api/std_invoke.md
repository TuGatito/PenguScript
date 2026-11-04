# std.invoke

> Source: `std/invoke.pengu`

---

### `INVOKE_VERSION`

> **INVOKE_VERSION** : string

 Standard library invoke module version.

### `Flag`

> rune Flag

```pengu
    long as string
    short as string
    help as string
    default as bool
```

 A boolean switch that can be passed as "--long" or "-short" (e.g. --verbose).

### `Positional`

> rune Positional

```pengu
    name as string
    help as string
    required as bool
    default as string
```

 A positional argument: a bare token collected in declaration order.

### `Option`

> rune Option

```pengu
    long as string
    short as string
    help as string
    required as bool
    default as string
```

 A value-taking option that can be passed as "--long <value>", "--long=<value>",
 "-short <value>", or "-short=<value>".

### `MultiOption`

> rune MultiOption

```pengu
    long as string
    short as string
    help as string
```

 A multi-value option that can appear multiple times on the command line.

### `Subcommand`

> rune Subcommand

```pengu
    name as string
    description as string
```

 A subcommand specification for hierarchical commands (e.g. git commit).

### `CommandParser`

> rune CommandParser

```pengu
    name as string
    description as string
    positionals as list of Positional
    options as list of Option
    flags as list of Flag
    subcommands as list of Subcommand
    multi_options as list of MultiOption
    version as string
```

 The mutable configuration of a CLI parser.

### `ParseResult`

> rune ParseResult

```pengu
    values as map of string to string
    flags as map of string to bool
    errors as list of string
    subcommand as string
    multi_keys as list of string
    multi_vals as list of string
```

 The outcome of an argument parse run.

### `new_parser`

> **new_parser**(name: string, description: string) -> CommandParser

 Creates a new empty CommandParser for a program called `name` with `description`.

 Signature: new_parser(name as string, description as string) into CommandParser
 Memory: Allocates and returns a fresh CommandParser struct.
 Example: var p as CommandParser is calling invoke.new_parser with "git", "VCS tool"

### `_levenshtein`

> **_levenshtein**(a: string, b: string) -> int

 ----------------------------------------------------------------------------
 Helper: Levenshtein Distance for Typo Suggestions
 ----------------------------------------------------------------------------

### `add_positional`

> **add_positional**(name: string, help: string, required: bool, default_val: string) -> void

 Appends a positional-argument spec to the parser.

### `add_option`

> **add_option**(long: string, short: string, help: string, required: bool, default_val: string) -> void

 Appends an option-argument spec to the parser.

### `add_option_int`

> **add_option_int**(long: string, short: string, help: string, required: bool, default_val: int) -> void

 Appends a typed integer option to the parser.

### `add_option_float`

> **add_option_float**(long: string, short: string, help: string, required: bool, default_val: float) -> void

 Appends a typed float option to the parser.

### `add_option_bool`

> **add_option_bool**(long: string, short: string, help: string, required: bool, default_val: bool) -> void

 Appends a typed boolean option to the parser.

### `add_option_multi`

> **add_option_multi**(long: string, short: string, help: string) -> void

 Appends a multi-value option to the parser (can be passed multiple times).

### `add_flag`

> **add_flag**(long: string, short: string, help: string, default_val: bool) -> void

 Appends a boolean flag spec to the parser.

### `add_subcommand`

> **add_subcommand**(name: string, description: string) -> CommandParser

 Registers a subcommand and returns a fresh CommandParser configured for it.

### `set_version`

> **set_version**(version: string) -> void

 Sets the program version string for automatic --version / -V output.

### `usage_string`

> **usage_string**() -> string

 Returns a single-line usage string (e.g. "Usage: myapp [OPTIONS] <input>").

### `full_help`

> **full_help**() -> string

 Formats a comprehensive, aligned help screen for the CLI.

### `print_help`

> **print_help**() -> void

 Prints the help text for the program to stdout.

### `parse_impl`

> **parse_impl**(argv: list of string, exit_on_help: bool) -> ParseResult

 Internal parsing engine implementing options, flags, positionals, and subcommands.

### `parse`

> **parse**(argv: list of string) -> ParseResult

 Parses argv, printing help and exiting process on --help/-h.

### `parse_no_exit`

> **parse_no_exit**(argv: list of string) -> ParseResult

 Parses argv without terminating process on --help/-h or --version.

### `parse_or_exit`

> **parse_or_exit**(argv: list of string, error_code: int) -> ParseResult

 Parses argv or exits with error code and prints errors on failure.

### `parse_or_usage`

> **parse_or_usage**(argv: list of string, error_code: int) -> ParseResult

 Parses argv or prints errors followed by usage string and exits.

### `get`

> **get**(name: string) -> string

 Returns the string value stored for an option or positional, or "".

### `get_or`

> **get_or**(name: string, fallback: string) -> string

 Returns the string value stored for an option or positional, or `fallback`.

### `get_int`

> **get_int**(name: string) -> maybe int

 Returns a parsed integer value if present and valid.

### `get_int_or`

> **get_int_or**(name: string, fallback: int) -> int

 Returns a parsed integer value, or `fallback`.

### `get_float`

> **get_float**(name: string) -> maybe float

 Returns a parsed float value if present and valid.

### `get_float_or`

> **get_float_or**(name: string, fallback: float) -> float

 Returns a parsed float value, or `fallback`.

### `get_bool`

> **get_bool**(name: string) -> maybe bool

 Returns a parsed boolean value if present and recognized.

### `get_bool_or`

> **get_bool_or**(name: string, fallback: bool) -> bool

 Returns a parsed boolean value, or `fallback`.

### `get_all`

> **get_all**(name: string) -> list of string

 Returns all values collected for a MultiOption long name.

### `is_set`

> **is_set**(name: string) -> bool

 Returns true when the flag `name` was set to true.

### `is_ok`

> **is_ok**() -> bool

 Returns true when the parse completed without any errors.

### `is_err`

> **is_err**() -> bool

 Returns true when the parse collected at least one error message.

### `to_map_values`

> **to_map_values**() -> map of string to string

 Returns a cloned map of all parsed positional and option string values.

### `to_map_flags`

> **to_map_flags**() -> map of string to bool

 Returns a cloned map of all parsed flag boolean values.

### `errors_to_string`

> **errors_to_string**() -> string

 Returns all error messages joined by newlines.

### `subcommand`

> **subcommand**() -> string

 Returns the invoked subcommand name, or "" if none.

