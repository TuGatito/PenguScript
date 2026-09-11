"""PenguScript Lark Grammar Definition.

Embedded EBNF grammar containing lexical and syntactic rules for PenguScript.
Designed for pyinstaller single-file compilation without external .lark asset dependency.
The language version is not spelled out here: it lives in ``VERSION`` and is
exposed by ``pengu_version.py`` (see ``tests/test_version.py``).
"""

GRAMMAR = r"""
start: file

file: _NEWLINE* (top_stmt _NEWLINE*)*

top_stmt: import_stmt
        | include_stmt
        | link_stmt
        | insignia_stmt
        | const_decl
        | rune_decl
        | omen_decl
        | echo_decl
        | alias_decl
        | concept_decl
        | bind_decl
        | seal_decl
        | weave_decl
        | enchanting_decl
        | declare_stmt
        | var_decl
        | let_decl
        | when_top_decl
        | test_decl

import_stmt: "import" dotted_path ["as" NAME] _NEWLINE
dotted_path: NAME ("." NAME)*

include_stmt: "include" STRING _NEWLINE
link_stmt: "link" STRING _NEWLINE
insignia_stmt: "insignia" NAME _NEWLINE

const_decl: "const" NAME ["as" type] "is" (expr _NEWLINE | indent_literal)
var_decl: "var" NAME ["as" type] ("is" (value_expr [_NEWLINE] | indent_literal) | with_init_expr)
static_var_decl: "static" "var" NAME ["as" type] ("is" (value_expr [_NEWLINE] | indent_literal) | with_init_expr)
let_decl: "let" var_name_list ["as" type] ("is" (value_expr [_NEWLINE] | indent_literal) | with_init_expr)
var_name_list: NAME ("," NAME)*

indent_literal: [":"] _NEWLINE _INDENT (indent_array | indent_entries) _DEDENT
indent_array: indent_row+
indent_row: list_expr ("," list_expr)* (",")? _NEWLINE
indent_entries: indent_entry+
indent_entry: (NAME | string_token) ":" list_expr _NEWLINE -> map_entry
            | NAME "is" list_expr _NEWLINE                -> field_entry


# Compile-time conditional declarations / statements
when_top_decl: "when" expr ":" _NEWLINE _INDENT top_stmt+ _DEDENT [when_top_else]
when_top_else: "else" ":" _NEWLINE _INDENT top_stmt+ _DEDENT -> when_top_else_plain
             | "else" when_top_decl                            -> when_top_else_when

when_stmt: "when" expr block [when_else]
when_else: "else" ":" _NEWLINE _INDENT stmt+ _DEDENT -> when_else_plain
         | "else" when_stmt                          -> when_else_when

# Integrated unit tests (top-level; compiled only in --test mode)
test_decl: "test" (string_token | NAME) ":" _NEWLINE _INDENT stmt+ _DEDENT

shard_params: "shard" NAME (("," | _AND_SEP) NAME)* [where_clause]
where_clause: "where" where_bound (("," | _AND_SEP) where_bound)*
where_bound: (NAME | type) ":" custom_type

rune_decl: "rune" NAME [shard_params] ":" _NEWLINE _INDENT field_decl+ _DEDENT
echo_decl: "echo" NAME [shard_params] ":" _NEWLINE _INDENT field_decl+ _DEDENT
field_decl: NAME "as" type _NEWLINE

alias_decl: "alias" NAME [shard_params] "as" type _NEWLINE
seal_decl: "seal" NAME "as" type _NEWLINE

RITUAL.2: "ritual"
INLINE.2: "inline"
weave_modifier: INLINE | RITUAL

concept_decl: "concept" NAME [shard_params] ":" _NEWLINE _INDENT concept_method+ _DEDENT
concept_method: weave_modifier* "weave" weave_modifier* NAME [shard_params] ["with" param_list] ["into" type] _NEWLINE

bind_decl: "bind" type "with" custom_type [shard_params] ":" _NEWLINE _INDENT weave_decl+ _DEDENT

omen_decl: "omen" NAME [shard_params] ["with" omen_string_kind] ":" _NEWLINE _INDENT omen_variant+ _DEDENT
omen_string_kind: "string"
omen_variant: NAME ["is" expr] ["with" omen_field (("," | _AND_SEP) omen_field)*] _NEWLINE
omen_field: NAME "as" type

enchanting_decl: "enchanting" type [shard_params] ":" _NEWLINE _INDENT weave_decl+ _DEDENT

weave_decl: weave_modifier* "weave" weave_modifier* NAME [shard_params] ["with" param_list] ["into" type] ":" _NEWLINE _INDENT stmt+ _DEDENT

param_list: param ("," param)*
param: NAME "as" type ["is" list_expr]

declare_stmt: weave_modifier* "declare" weave_modifier* NAME [shard_params] ["with" declare_params] ["into" type] _NEWLINE
declare_params: param ("," param)* ["," VARARGS] | VARARGS

stmt: var_decl
    | static_var_decl
    | let_decl
    | const_decl
    | set_stmt
    | named_stmt
    | if_stmt
    | unless_stmt
    | while_stmt
    | for_stmt
    | when_stmt
    | with_stmt
    | defer_stmt
    | errdefer_stmt
    | banish_stmt
    | return_stmt
    | break_stmt
    | continue_stmt
    | expr_stmt

named_stmt: NAME "is" expr [_NEWLINE]

set_stmt: "set" set_target "is" value_expr [_NEWLINE]
        | "set" set_target COMPOUND_OP expr [_NEWLINE]   -> compound_set_stmt
set_target: with_target
          | normal_target
          | essence_target
essence_target: "essence" "of" unary

with_target: "." NAME (access_op)*
!normal_target: (NAME | "self") (access_op)*

access_op: "." NAME -> dot_access
         | "->" NAME -> arrow_access
         | "at" primary -> at_access

defer_stmt: "defer" (expr _NEWLINE | block)
errdefer_stmt: "errdefer" (expr _NEWLINE | block)
banish_stmt: "banish" unary _NEWLINE


# The trailing _NEWLINE is optional: a block-expression value anywhere in the
# returned expression ('return if c: …', 'return calling f with if c: …') already
# consumed the line break, exactly like 'expr_stmt' and 'var_decl'.
return_stmt: "return" [value_expr] [_NEWLINE]
break_stmt: "break" _NEWLINE
continue_stmt: "continue" _NEWLINE
expr_stmt: expr [_NEWLINE]

block: ":" _NEWLINE _INDENT stmt+ _DEDENT
     | ":" simple_stmt _NEWLINE

simple_stmt: "continue" -> continue_simple
           | "break"    -> break_simple
           | "return" [expr] -> return_simple
           | "set" set_target "is" expr -> set_simple
           | "set" set_target COMPOUND_OP expr -> compound_set_simple
           | NAME "is" expr -> named_simple
           | expr

if_stmt: "if" if_cond block [else_block]
if_cond: NAME "as" type "is" expr "is" "present" -> if_cond_binding_present
       | NAME "as" type "is" expr               -> if_cond_binding
       | expr

else_block: "else" ":" _NEWLINE _INDENT stmt+ _DEDENT
          | "else" if_stmt

unless_stmt: "unless" expr block [else_block]

while_stmt: "while" expr block

for_stmt: "for" NAME "from" expr_no_cast "to" expr_no_cast ["step" expr_no_cast] block -> for_range_stmt
        | "for" NAME ("," NAME)? "in" expr block                                   -> for_in_stmt

with_stmt: "with" expr ":" _NEWLINE _INDENT stmt+ _DEDENT

when_clause: "when" when_pattern ["with" when_payload] "->" expr _NEWLINE
when_payload: when_field (("," | _AND_SEP) when_field)*
when_field: NAME
else_clause: "else" "->" expr _NEWLINE
when_pattern: INT
            | FLOAT
            | string_token
            | CHAR_LIT
            | "true"
            | "false"
            | "maybe" "none"
            | NAME ("." NAME)*

?type: ref_type
     | frozen_type
     | fn_type
     | array_type
     | slice_type
     | many_type
     | list_type
     | map_type
     | maybe_type
     | result_type
     | opaque_type
     | base_type
     | custom_type
     | "(" type ")"

!base_type: "int" | "i32" | "i64" | "float" | "f32" | "f64" | "bool" | "string" | "void" | "char" | "byte" | "u8" | "i8" | "u16" | "i16" | "u32" | "u64" | "int8" | "uint8" | "int16" | "uint16" | "int32" | "uint32" | "int64" | "uint64" | "usize" | "isize" | "size_t" | "short" | "ushort" | "long" | "ulong" | "double" | "int8_t" | "uint8_t" | "int16_t" | "uint16_t" | "int32_t" | "uint32_t" | "int64_t" | "uint64_t" | "uint"
custom_type: dotted_path ["of" type (("," | _AND_SEP) type)*]
!opaque_type: "opaque"
ref_type: "ref" "to" type

# 'frozen' is a *soft* keyword: it is a plain string literal, so Lark's
# contextual lexer only prefers it where a type may start. An identifier named
# 'frozen' keeps working everywhere else (variables, fields, modules), which is
# why no new terminal is declared. It means C's 'const': 'frozen T' → 'const T',
# 'ref to frozen T' → 'const T*'.
frozen_type: "frozen" type
fn_type: "weave" ["with" fn_param_list] ["into" type]
fn_param_list: fn_param (("," | _AND_SEP) fn_param)*
fn_param: [NAME "as"] type
array_type: "array" "of" type ["with" "size" (INT | NAME)]
slice_type: "slice" "of" type
many_type: "many" type
list_type: "list" "of" type
map_type: "map" "of" type "to" type
maybe_type: "maybe" type
result_type: "result" "of" type ["to" type]

?expr: or_else_expr

?or_else_expr: try_expr
            | or_else_expr "or" "else" try_expr      -> or_else
            | or_else_expr "or" "return" try_expr    -> or_return
            | or_else_expr "or" ":" _NEWLINE _INDENT stmt+ _DEDENT -> or_block

?try_expr: "try" try_expr    -> try_expr
         | if_expr
         | when_expr
         | judge_expr
         | for_comp_expr
         | bool_or_expr

# Boolean logical operators (short-circuit). They are separate terminals from the
# 'or' keyword used by 'or else' / 'or return' / 'or:' so LALR(1) never has to
# guess: a negative lookahead keeps the unwrap forms on the plain OR terminal,
# and _BOOL_OR (higher priority than the plain keyword) wins for a boolean 'or'.
# _BOOL_AND is *lower* priority than _AND_SEP so the 'and' that is still a
# separator in pure type/name lists keeps winning there. All three are filtered
# out of the AST (leading underscore), so bool_or/bool_and nodes have exactly two
# children: left and right. '&'/'|' stay bitwise (integer-only).
_BOOL_OR.3: /or\b(?!\s*(else|return|:))/
_BOOL_AND.2: /and\b/
_AND_SEP.5: "and"

?bool_or_expr: bool_or_expr _BOOL_OR bool_and_expr  -> bool_or
             | bool_and_expr

?bool_and_expr: bool_and_expr _BOOL_AND comparison  -> bool_and
              | comparison

if_expr: "if" expr "then" expr "else" expr

when_expr: "when" expr "then" expr "else" expr

judge_expr: "judge" expr ":" _NEWLINE _INDENT when_clause+ [else_clause] _DEDENT

for_comp_expr: "for" NAME "in" expr ["when" expr] "then" expr -> for_comp

?comparison: comparison "==" logic_or               -> eq
           | comparison "!=" logic_or               -> ne
           | comparison "<=" logic_or               -> le
           | comparison ">=" logic_or               -> ge
           | comparison "<" logic_or                -> lt
           | comparison ">" logic_or                -> gt
           | comparison "is" "present"              -> is_present
           | comparison "is" "not" "present"        -> is_not_present
           | comparison "is" "false"                -> is_false
           | comparison "is" "true"                 -> is_true
           | comparison "in" range_expr               -> in_expr
           | comparison "not" "in" range_expr         -> not_in_expr
           | range_expr

?range_expr: logic_or DOTDOT logic_or  -> range_dotdot
           | logic_or "to" logic_or    -> to_expr
           | logic_or

?logic_or: logic_or "|" logic_and  -> bitwise_or

         | logic_and

?logic_and: logic_and "&" bit_xor -> bitwise_and
          | bit_xor

?bit_xor: bit_xor "^" bit_shift -> bitwise_xor
        | bit_shift

?bit_shift: bit_shift "<<" bit_add -> shl
          | bit_shift ">>" bit_add -> shr
          | bit_add

?bit_add: bit_add "+" bit_mul -> add
        | bit_add "-" bit_mul -> sub
        | bit_mul

?bit_mul: bit_mul "*" unary -> mul
        | bit_mul "/" unary -> div
        | bit_mul "%" unary -> mod
        | unary

?unary: "~" unary                        -> bit_not
      | "not" unary                      -> log_not
      | "-" unary                        -> neg
      | "sigil" "of" unary               -> sigil_of
      | "essence" "of" unary             -> essence_of
      | "transmute" unary_no_cast "to" type -> transmute
      | "size" "of" type                 -> size_of
      | "banish" unary                   -> banish_expr
      | "some" unary                     -> some_expr
      | "ord" unary                      -> ord_expr
      | "chr" unary                      -> chr_expr
      | "bytes" "of" unary               -> bytes_expr
      | calling_expr
      | postfix

calling_expr: "calling" (with_target | normal_target) [generic_args] ["with" arg_list]
generic_args: "of" type ((_AND_SEP | ",") type)*
arg_list: arg ("," arg)*
arg: NAME "is" list_value_expr -> named_arg
   | list_value_expr          -> pos_arg

?postfix: postfix_no_cast

?postfix_no_cast: primary

                | postfix_no_cast "at" slice_range        -> slice_at_expr
                | postfix_no_cast "at" unary_no_cast      -> at_expr
                | postfix_no_cast "length"                -> length_expr
                | postfix_no_cast "." NAME                -> field_access
                | postfix_no_cast "->" NAME               -> arrow_access

slice_range: unary_no_cast "to" unary_no_cast

?expr_no_cast: logic_or_no_cast (("==" | "!=" | "<=" | ">=" | "<" | ">") logic_or_no_cast)*
?logic_or_no_cast: logic_or_no_cast "|" logic_and_no_cast -> bitwise_or
                 | logic_and_no_cast
?logic_and_no_cast: logic_and_no_cast "&" bit_xor_no_cast -> bitwise_and
                  | bit_xor_no_cast
?bit_xor_no_cast: bit_xor_no_cast "^" bit_shift_no_cast -> bitwise_xor
                | bit_shift_no_cast
?bit_shift_no_cast: bit_shift_no_cast "<<" bit_add_no_cast -> shl
                  | bit_shift_no_cast ">>" bit_add_no_cast -> shr
                  | bit_add_no_cast
?bit_add_no_cast: bit_add_no_cast "+" bit_mul_no_cast -> add
                | bit_add_no_cast "-" bit_mul_no_cast -> sub
                | bit_mul_no_cast
?bit_mul_no_cast: bit_mul_no_cast "*" unary_no_cast -> mul
                | bit_mul_no_cast "/" unary_no_cast -> div
                | bit_mul_no_cast "%" unary_no_cast -> mod
                | unary_no_cast
?unary_no_cast: "~" unary_no_cast -> bit_not
              | "not" unary_no_cast -> log_not
              | "-" unary_no_cast -> neg
              | "sigil" "of" unary_no_cast -> sigil_of
              | "essence" "of" unary_no_cast -> essence_of
              | calling_expr
              | postfix_no_cast

?primary: NAME                            -> var_ref
        | "self"                          -> self_ref
        | INT                             -> int_lit
        | FLOAT                           -> float_lit
        | string_lit
        | CHAR_LIT                        -> char_lit
        | "true"                          -> true_lit
        | "false"                         -> false_lit
        | "null"                          -> null_lit
        | "maybe" "none"                  -> maybe_none
        | "error"                         -> error_lit
        | "(" expr ")"                    -> paren_expr
        | struct_init
        | with_init_expr
        | do_expr
        | lambda_expr
        | list_init_expr
        | map_init_expr
        | array_init_expr
        | array_lit
        | map_lit
        | defined_expr

defined_expr: "defined" "(" NAME ")"

# Lambda expression: parameters are explicitly typed (static language) and there
# is no capture — the body only sees its parameters and module-level symbols,
# which is what lets codegen emit a plain top-level 'static' C function.
lambda_expr: "lambda" lambda_param_list "into" expr
           | "lambda" "into" expr                     -> lambda_no_params
lambda_param_list: lambda_param ("," lambda_param)*
lambda_param: NAME "as" type

struct_init: "with" field_init ("," field_init)*
field_init: NAME "is" list_value_expr

# Block-style construction expression: builds a new value by mutating an
# implicit temporary through 'set .field' / 'calling .method' statements.
with_init_expr: "with" ":" _NEWLINE _INDENT stmt+ _DEDENT

# General statement-block expression: runs statements in a fresh scope and
# evaluates to the value of its last expression statement (or void).
do_expr: "do" ":" _NEWLINE _INDENT stmt+ _DEDENT

# Value position: an expression, or a statement-shaped block construct used for
# its value. 'if'/'unless'/'while'/'for' deliberately keep a single grammar rule
# each: the token sequence 'if <cond>:' + block (etc.) is identical whether the
# values are used or discarded, so a second "value form" rule would be ambiguous
# and LALR would silently route every statement-level construct into it. Instead,
# the checker/codegen decide by *position* whether the construct is used as a
# value.
?value_expr: unless_stmt
           | if_stmt
           | while_stmt
           | for_stmt
           | expr

# Elements of comma-separated lists — call arguments, struct-init fields, array
# and map literals, indented literals and parameter defaults — deliberately stop
# *below* the boolean operator levels. A bare 'and'/'or' is not an operand
# there, so the removed 0.10.0 list separator can never be silently read as one
# boolean element ('calling f with a and b' is now a hard error instead of a
# single bool argument; parenthesise to pass a boolean: '(a and b)'). The
# 'or else' / 'or return' / 'or:' unwrap forms and the block-valued expressions
# stay available, because they are not list separators.
?list_value_expr: unless_stmt
                | if_stmt
                | while_stmt
                | for_stmt
                | list_expr

?list_expr: list_or_else_expr

?list_or_else_expr: list_try_expr
                  | list_or_else_expr "or" "else" list_try_expr   -> or_else
                  | list_or_else_expr "or" "return" list_try_expr -> or_return
                  | list_or_else_expr "or" ":" _NEWLINE _INDENT stmt+ _DEDENT -> or_block

?list_try_expr: "try" list_try_expr -> try_expr
              | if_expr
              | when_expr
              | judge_expr
              | for_comp_expr
              | comparison

map_lit: "{" [map_entry ("," map_entry)*] "}"
map_entry: (NAME | string_token) ":" list_expr

string_lit: string_token
?string_token: STRING | TRIPLE_STRING | RAW_STRING | RAW_TRIPLE_STRING

array_lit: "[" _NEWLINE* [list_expr ("," _NEWLINE* list_expr)* (",")? _NEWLINE*] "]"
list_init_expr: "list" "of" type ["with" "capacity" expr]
map_init_expr: "map" "of" type "to" type
array_init_expr: "array" "of" type "with" "size" expr

LSQB: "["
RSQB: "]"
LPAR: "("
RPAR: ")"
LBRACE: "{"
RBRACE: "}"

%declare _INDENT _DEDENT

%import common.WS_INLINE
INT: /0[xX][0-9a-fA-F]+|[0-9]+/
FLOAT: /[0-9]+\.[0-9]+([eE][-+]?[0-9]+)?|[0-9]+[eE][-+]?[0-9]+/
%ignore WS_INLINE

_NEWLINE: /(\r?\n[\t ]*)+/
%ignore /#[^#\r\n]*$/m
%ignore /##[\s\S]*?##/

NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
TRIPLE_STRING.2: /\"\"\"[\s\S]*?\"\"\"/
RAW_TRIPLE_STRING.2: /r\"\"\"[\s\S]*?\"\"\"/
RAW_STRING.2: /r\"[^\"]*\"/
STRING: /"([^"\\]|\\.)*"/
CHAR_LIT: /'([^'\\]|\\.)'/
# Compound assignment operators. Declared after the single-char operators with
# higher priority so '<<='/'>>=' win over '<<'/'>=' at lexing time.
COMPOUND_OP.3: "+=" | "-=" | "*=" | "/=" | "%=" | "&=" | "|=" | "^=" | "<<=" | ">>="
ARROW: "->"
DOTDOT.5: ".."
VARARGS.6: "..."
"""

# Single-line block statements ('if c: return 0') parse as their own grammar
# nodes (aliased from ``simple_stmt``); each one is exactly the canonical
# statement rule without the trailing _NEWLINE, so the checker and codegen
# re-dispatch on this map instead of duplicating the handling.
SIMPLE_STMT_ALIASES = {
    "continue_simple": "continue_stmt",
    "break_simple": "break_stmt",
    "return_simple": "return_stmt",
    "set_simple": "set_stmt",
    "named_simple": "named_stmt",
    "compound_set_simple": "compound_set_stmt",
}
