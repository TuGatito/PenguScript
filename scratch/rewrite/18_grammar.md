---

<a id="sec-19"></a>
## 19. Gramática

La gramática usa `NEWLINE`, `INDENT` y `DEDENT` producidos por el lexer. Los
terminales léxicos se definen en §2.

### 19.1 Programa

```ebnf
program        ::= item*
item           ::= scroll_def | summon_def | rune_def | enchanting_def
                 | pact_def | ritual_def | essence_def | foreign_def
                 | function_def | const_def | static_def | grimoire_def
                 | test_def

scroll_def     ::= "scroll" IDENT (NEWLINE INDENT item* DEDENT)?
summon_def     ::= "summon" path ("as" IDENT)?
path           ::= IDENT ("::" IDENT)*
```

### 19.2 Records y sums

```ebnf
rune_def       ::= "unveil"? "rune" IDENT type_params? NEWLINE INDENT field+ DEDENT
field          ::= "unveil"? IDENT ":" type

enchanting_def ::= "unveil"? "enchanting" IDENT type_params? NEWLINE INDENT variant+ DEDENT
variant        ::= "unveil"? IDENT (variant_fields)?
variant_fields ::= "(" (named_field ("," named_field)* | type ("," type)* ","?)? ")"
named_field    ::= IDENT ":" type
```

### 19.3 Pacts y rituals

```ebnf
pact_def       ::= "unveil"? "pact" IDENT type_params? (":" path)? NEWLINE INDENT pact_item+ DEDENT
pact_item      ::= method_sig | method_def

ritual_def     ::= "unveil"? "ritual" type_params? type ("for" path)? NEWLINE INDENT ritual_item+ DEDENT
ritual_item    ::= method_def | function_def | const_def | static_def

method_sig     ::= IDENT "=" receiver "(" params? ")" "->" type
method_def     ::= IDENT "=" receiver "(" params? ")" "->" type NEWLINE INDENT block DEDENT
receiver       ::= "@" | "@mut" | "@own"
```

### 19.4 Tipos

```ebnf
type           ::= "?" type
                 | "&" "mut"? type
                 | "[" type ";" expr "]"
                 | "(" ")" 
                 | "(" type "," ")"
                 | "(" type ("," type)+ ","? ")"
                 | path type_args?
                 | "[" type ("," type)* ","? "]"

type_args      ::= "[" type ("," type)* ","? "]"
type_params    ::= "[" type_param ("," type_param)* ","? "]"
type_param     ::= IDENT (":" bound ("+" bound)*)?
bound          ::= path
```

No hay `where`, `dyn`, `impl`, `for<...>`, `'a` ni tipos asociados.

### 19.5 Funciones

```ebnf
function_def   ::= "unveil"? "curse"? IDENT "=" type_params? "(" params? ")" "->" type
                   NEWLINE INDENT block DEDENT
params         ::= param ("," param)* ","?
param          ::= IDENT ":" type

grimoire_def   ::= "grimoire" (":" type)? NEWLINE INDENT block DEDENT
```

### 19.6 Constantes y estáticos

```ebnf
const_def      ::= "unveil"? "sigil" IDENT ":" type "=" expr
static_def     ::= "unveil"? "relic" IDENT ":" type "=" expr
```

### 19.7 FFI

```ebnf
foreign_def    ::= "foreign" STRING NEWLINE INDENT foreign_item+ DEDENT
foreign_item   ::= IDENT "=" "(" params? ")" "->" type
```

`foreign` no tiene cuerpos. `curse` aparece en `function_def` y en bloques.

### 19.8 Expresiones

```ebnf
expr           ::= assignment
assignment     ::= or_expr ("=" assignment)?
or_expr        ::= and_expr ("or" and_expr)*
and_expr       ::= not_expr ("and" not_expr)*
not_expr       ::= "not" not_expr | comparison
comparison     ::= range (comp_op range)?
comp_op        ::= "==" | "!=" | "<" | "<=" | ">" | ">=" | "is" | "isnt" | "in"
range          ::= additive (".." "="? additive)?
additive       ::= multiplicative (("+" | "-") multiplicative)*
multiplicative ::= cast (("*" | "/" | "%") cast)*
cast           ::= unary ("as" type)*
unary          ::= ("-" | "not") unary | postfix
postfix        ::= primary (("." IDENT ("(" args? ")")?) | "(" args? ")" | "[" expr "]" | "?")*
primary        ::= literal | path | "(" expr ")" | tuple | array | map | set
                 | "if" expr "then" expr "else" expr
                 | "match" expr NEWLINE INDENT match_arm+ DEDENT
                 | "do" NEWLINE INDENT block DEDENT
                 | "loop" NEWLINE INDENT block DEDENT
                 | "(" params ")" "=>" expr
```

### 19.9 Sentencias

```ebnf
block          ::= statement+
statement      ::= binding | assignment | expr | if_stmt | while_stmt
                 | for_stmt | loop_stmt | return_stmt | break_stmt | continue_stmt
                 | curse_block | item

binding        ::= ("bind" | "morph") pattern "=" expr ("else" NEWLINE INDENT block DEDENT)?
assignment     ::= expr "=" expr

if_stmt        ::= "if" expr "then" NEWLINE INDENT block DEDENT
                   ("elseif" expr "then" NEWLINE INDENT block DEDENT)*
                   ("else" NEWLINE INDENT block DEDENT)?
                 | "unless" expr "then" NEWLINE INDENT block DEDENT
                   ("else" NEWLINE INDENT block DEDENT)?
while_stmt     ::= "while" expr NEWLINE INDENT block DEDENT
for_stmt       ::= "for" pattern "in" expr NEWLINE INDENT block DEDENT
loop_stmt      ::= "loop" NEWLINE INDENT block DEDENT
return_stmt    ::= "return" expr?
break_stmt     ::= "break" expr?
continue_stmt  ::= "continue"
curse_block    ::= "curse" NEWLINE INDENT block DEDENT
```

### 19.10 Patrones

```ebnf
pattern        ::= literal
                 | "_"
                 | IDENT
                 | IDENT "@" pattern
                 | "(" pattern ("," pattern)* ","? ")"
                 | path "(" pattern ("," pattern)* ","? ")"
                 | path "(" named_pattern ("," named_pattern)* ","? ")"
                 | path
                 | pattern "|" pattern
                 | pattern ".." pattern?
                 | "[" pattern ("," pattern)* ","? "]"

named_pattern  ::= IDENT ":" pattern
```

### 19.11 Atributos y tests

```ebnf
test_def       ::= "@@test" ("(" test_opt ("," test_opt)* ")")? NEWLINE
                   IDENT "=" "(" ")" "->" type NEWLINE INDENT block DEDENT
test_opt       ::= "should_panic" ":" STRING | "ignore" ":" STRING

derive_attr    ::= "@@derive" "(" IDENT ("," IDENT)* ")"
```

Solo existen `@@test` y `@@derive`. No hay otros atributos.

### 19.12 Match

```ebnf
match_arm      ::= "when" pattern ("if" expr)? "then" expr
                 | "when" pattern ("if" expr)? NEWLINE INDENT block DEDENT
                 | "else" expr
                 | "else" NEWLINE INDENT block DEDENT
```

### 19.13 Restricciones

- `else` es obligatorio si el `match` no es exhaustivo.
- Un `break` con valor solo es válido dentro de `loop`.
- `?` solo es válido en funciones que devuelven `Option` o `Result`.
- `@` solo es válido en métodos y en patrones de binding.
- `Self` solo es válido dentro de `pact` y `ritual`.

[↑ Volver al índice](#indice)
