"""PenguScript v0.6 Lark Grammar Definition.

Embedded EBNF grammar containing lexical and syntactic rules for PenguScript.
Designed for pyinstaller single-file compilation without external .lark asset dependency.
"""

GRAMMAR = r"""
start: file

file: _NEWLINE* (top_stmt _NEWLINE*)*

top_stmt: import_stmt
        | include_stmt
        | link_stmt
        | const_decl
        | rune_decl
        | omen_decl
        | echo_decl
        | alias_decl
        | weave_decl
        | enchanting_decl
        | declare_stmt
        | var_decl
        | let_decl

import_stmt: "import" dotted_path _NEWLINE
dotted_path: NAME ("." NAME)*

include_stmt: "include" STRING _NEWLINE
link_stmt: "link" STRING _NEWLINE

const_decl: "const" NAME ["as" type] "is" expr _NEWLINE
var_decl: "var" NAME ["as" type] "is" expr [_NEWLINE]
let_decl: "let" var_name_list ["as" type] "is" expr [_NEWLINE]
var_name_list: NAME ("," NAME)*

shard_params: "shard" NAME (("," | "and") NAME)*

rune_decl: "rune" NAME [shard_params] ":" _NEWLINE _INDENT field_decl+ _DEDENT
echo_decl: "echo" NAME [shard_params] ":" _NEWLINE _INDENT field_decl+ _DEDENT
field_decl: NAME "as" type _NEWLINE

alias_decl: "alias" NAME [shard_params] "as" type _NEWLINE

omen_decl: "omen" NAME [shard_params] ":" _NEWLINE _INDENT omen_variant+ _DEDENT
omen_variant: NAME ["with" omen_field (("," | "and") omen_field)*] _NEWLINE
omen_field: NAME "as" type

enchanting_decl: "enchanting" type ":" _NEWLINE _INDENT weave_decl+ _DEDENT

weave_decl: ["inline"] "weave" NAME [shard_params] ["with" param_list] ["into" type] ":" _NEWLINE _INDENT stmt+ _DEDENT

param_list: param (("," | "and") param)*
param: NAME "as" type ["is" expr]

declare_stmt: "declare" NAME [shard_params] ["with" param_list] ["into" type] _NEWLINE

stmt: var_decl
    | let_decl
    | const_decl
    | set_stmt
    | named_stmt
    | if_stmt
    | unless_stmt
    | while_stmt
    | for_stmt
    | with_stmt
    | defer_stmt
    | errdefer_stmt
    | banish_stmt
    | return_stmt
    | break_stmt
    | continue_stmt
    | expr_stmt

named_stmt: NAME "is" expr [_NEWLINE]

set_stmt: "set" set_target "is" expr [_NEWLINE]
set_target: with_target
          | normal_target
          | essence_target
essence_target: "essence" "of" unary

with_target: "." NAME (access_op)*
!normal_target: (NAME | "self") (access_op)*

access_op: "." NAME -> dot_access
         | "->" NAME -> arrow_access
         | "at" bit_add -> at_access

defer_stmt: "defer" expr _NEWLINE
errdefer_stmt: "errdefer" expr _NEWLINE
banish_stmt: "banish" unary _NEWLINE

return_stmt: "return" [expr] _NEWLINE
break_stmt: "break" _NEWLINE
continue_stmt: "continue" _NEWLINE
expr_stmt: expr [_NEWLINE]

block: ":" _NEWLINE _INDENT stmt+ _DEDENT
     | ":" simple_stmt _NEWLINE

simple_stmt: "continue" -> continue_simple
           | "break"    -> break_simple
           | "return" [expr] -> return_simple
           | "set" set_target "is" expr -> set_simple
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
        | "for" NAME "in" expr block                           -> for_in_stmt

with_stmt: "with" expr ":" _NEWLINE _INDENT stmt+ _DEDENT

when_clause: "when" when_pattern ["with" when_payload] "->" expr _NEWLINE
when_payload: when_field (("," | "and") when_field)*
when_field: NAME
else_clause: "else" "->" expr _NEWLINE
when_pattern: INT
            | FLOAT
            | STRING
            | CHAR_LIT
            | "true"
            | "false"
            | "maybe" "none"
            | NAME ("." NAME)*

?type: ref_type
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
custom_type: dotted_path ["of" type (("," | "and") type)*]
!opaque_type: "opaque"
ref_type: "ref" "to" type
fn_type: "weave" ["with" fn_param_list] ["into" type]
fn_param_list: fn_param (("," | "and") fn_param)*
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
         | judge_expr
         | for_comp_expr
         | comparison

if_expr: "if" expr "then" expr "else" expr

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
      | calling_expr
      | postfix

calling_expr: "calling" (with_target | normal_target) [generic_args] ["with" arg_list]
generic_args: "of" type (("and" | ",") type)*
arg_list: arg (("," | "and") arg)*
arg: NAME "is" expr -> named_arg
   | expr           -> pos_arg

?postfix: postfix_no_cast
        | postfix "to" type               -> cast_expr

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
        | STRING                          -> string_lit
        | CHAR_LIT                        -> char_lit
        | "true"                          -> true_lit
        | "false"                         -> false_lit
        | "maybe" "none"                  -> maybe_none
        | "error"                         -> error_lit
        | "(" expr ")"
        | struct_init
        | list_init_expr
        | map_init_expr
        | array_init_expr
        | array_lit

struct_init: "with" field_init (("and" | ",") field_init)*
field_init: NAME "is" expr

array_lit: "[" [expr (("," | "and") expr)*] "]"
list_init_expr: "list" "of" type ["with" "capacity" expr]
map_init_expr: "map" "of" type "to" type
array_init_expr: "array" "of" type "with" "size" expr

%declare _INDENT _DEDENT

%import common.WS_INLINE
INT: /0[xX][0-9a-fA-F]+|[0-9]+/
%import common.FLOAT
%ignore WS_INLINE

_NEWLINE: /(\r?\n[\t ]*)+/
%ignore /#[^#\r\n]*$/m
%ignore /##[\s\S]*?##/

NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
STRING: /"([^"\\]|\\.|{[a-zA-Z_][a-zA-Z0-9_]*})*"/
CHAR_LIT: /'([^'\\]|\\.)'/
ARROW: "->"
"""
