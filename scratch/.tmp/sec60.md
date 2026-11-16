<a id="sec-60-ebnf"></a>
## 60. Gramática EBNF

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 10 |
| Rust | — (gramática del front-end) |
| Palabras mágicas | todas |
| Depende de | §2, §3, §11–§15, §28–§47 |
| Ejemplos ejecutables | `no` |

Esta gramática es normativa para el parser. `INDENT`/`DEDENT` son tokens
sintéticos producidos por el algoritmo de §60.10. `NEWLINE` termina una
sentencia; dentro de delimitadores inline se ignora.

### 60.1 Convenciones

```ebnf
letter        ::= "A"…"Z" | "a"…"z" | "_" | unicode_xid_start
digit         ::= "0"…"9"
xid_continue  ::= letter | digit | unicode_xid_continue
ident         ::= (letter | unicode_xid_start) xid_continue*
literal       ::= "true" | "false" | "none" | int_lit | float_lit | string | char
raw_region    ::= RAW_TOKEN*   (* tokens crudos hasta el DEDENT que cierra el bloque *)
```

1. La gramática es LL(1) salvo las ambigüedades indicadas en §62.
2. `?` en EBNF significa opcional; `*` repetición cero o más; `+` una o más.
3. Los literales terminales van entre comillas.
4. `NEWLINE`, `INDENT`, `DEDENT` y `EOF` son terminales sintéticos.
5. Una producción por línea; `|` separa alternativas.
6. Los comentarios `(* … *)` son explicativos, no parte del lenguaje.

### 60.2 Programa y módulos

```ebnf
program        ::= shebang? module_body EOF
shebang        ::= "#!" [^\n]* NEWLINE
module_body    ::= (NEWLINE | item)*
item           ::= attributes? visibility? item_kind
item_kind      ::= function_def
                 | struct_def
                 | enum_def
                 | trait_def
                 | impl_def
                 | alias_def
                 | const_def
                 | static_def
                 | mod_def
                 | use_def
                 | foreign_def
                 | macro_def
                 | rust_block
                 | grimoire_def

const_def      ::= "sigil" ident ":" type "=" expr NEWLINE
static_def     ::= "relic" ident ":" type "=" expr NEWLINE
mod_def        ::= "scroll" ident ( NEWLINE INDENT module_body DEDENT | "=" string NEWLINE )?
use_def        ::= "summon" path ("as" ident)? NEWLINE
foreign_def    ::= "foreign" string NEWLINE INDENT foreign_item* DEDENT
foreign_item   ::= attributes? "curse"? ident "=" "(" params? ")" "->" type NEWLINE
macro_def      ::= "incantation" ident NEWLINE INDENT raw_region DEDENT
rust_block     ::= "rust" NEWLINE INDENT raw_region DEDENT
grimoire_def   ::= "grimoire" (":" type)? NEWLINE INDENT body DEDENT

attributes     ::= attribute+
attribute      ::= "@@" attr_name ( "(" attr_args? ")" )? NEWLINE
inner_attrs    ::= "@@!" attr_name ( "(" attr_args? ")" )? NEWLINE
attr_name      ::= ident ("::" ident)*
attr_args      ::= attr_arg ("," attr_arg)* ","?
attr_arg       ::= literal | ident | "(" attr_args? ")" | "[" attr_args? "]"
visibility     ::= "unveil" ( "(" ( "tome" | "scroll" | "in" path ) ")" )?
```

1. `attributes` se aplica al item siguiente.
2. `inner_attrs` solo al inicio de un `scroll` o crate.
3. `visibility` sin paréntesis es `pub`.
4. `unveil(tome)` es `pub(crate)`; `unveil(scroll)` es `pub(super)`.
5. Un item sin `visibility` es privado.
6. `NEWLINE` es obligatorio entre items de nivel superior.
7. `EOF` debe seguir a un `DEDENT` si hay bloques abiertos.

### 60.3 Funciones y tests

```ebnf
function_def   ::= modifier* ident "=" type_params? "(" params? ")" "->" type
                   ( NEWLINE INDENT body DEDENT )?
modifier       ::= "dream" | "curse" | "eternal"
type_params    ::= "[" type_param ("," type_param)* ","? "]"
type_param     ::= ident (":" bounds)?
                 | "const" ident ":" type
                 | lifetime
params         ::= param ("," param)* ","?
param          ::= receiver | pattern ":" type
receiver       ::= "@" | "@mut" | "@own"
body           ::= statement+
```

1. El tipo de retorno es obligatorio.
2. El cuerpo, si existe, va indentado en las líneas siguientes; no hay cuerpo
   inline `= expr` para funciones nombradas.
3. `dream` genera `async`; `curse` genera `unsafe`; `eternal` genera `const`.
4. Un `pact`/`foreign` puede omitir el cuerpo (solo firma).
5. `@@test`/`@@bench` son atributos de una `function_def` normal; no hay
   producción separada.
6. Las funciones nombradas no capturan; las lambdas sí.
7. `@`/`@mut`/`@own` solo son válidos como primer parámetro de un método.

### 60.4 Structs, enums y aliases

```ebnf
struct_def     ::= "rune" ident type_params? where_clause? struct_body
struct_body    ::= NEWLINE INDENT field* DEDENT
                 | "(" field_list ")"
                 | NEWLINE
field          ::= visibility? ident ":" type NEWLINE
field_list     ::= type ("," type)* ","?
enum_def       ::= "enchanting" ident type_params? where_clause? NEWLINE
                   INDENT variant+ DEDENT
variant        ::= ident ( "(" field_list ")" | NEWLINE INDENT field* DEDENT )?
                   ("=" int_lit)?
alias_def      ::= "essence" ident type_params? "=" type NEWLINE
```

1. `rune Marker` sin cuerpo es unit struct.
2. `rune Pair(Int, Int)` es tuple struct.
3. Los campos de tuple struct son privados.
4. `enchanting Shape` requiere al menos una variante.
5. Un discriminante solo se permite en variantes sin campos.
6. `essence` no crea un tipo nuevo; es un alias.
7. `where_clause` se define en §60.6.

### 60.5 Traits e impls

```ebnf
trait_def      ::= "pact" ident type_params? (":" bounds)? where_clause? NEWLINE
                   INDENT trait_item* DEDENT
trait_item     ::= function_def
                 | "essence" ident (":" bounds)? ("=" type)? NEWLINE
                 | "sigil" ident ":" type ("=" expr)? NEWLINE
impl_def       ::= "ritual" type ("for" type)? where_clause? NEWLINE
                   INDENT impl_item* DEDENT
impl_item      ::= function_def
                 | "essence" ident "=" type NEWLINE
                 | "sigil" ident ":" type "=" expr NEWLINE
```

1. `pact` declara un trait; `ritual Tipo for Pact` lo implementa.
2. Los métodos usan `@`, `@mut` o `@own` como primer parámetro.
3. Un método sin `@` es función asociada.
4. `essence` dentro de `pact` es associated type.
5. `sigil` dentro de `pact` es associated const.
6. Las implementaciones no pueden añadir métodos a un trait externo.
7. La coherencia/orphan la valida rustc.

### 60.6 Tipos

```ebnf
type           ::= type_primary type_suffix*
type_primary   ::= path type_args?
                 | "(" ")"                              (* Unit *)
                 | "(" type ")"
                 | "(" type ("," type)+ ","? ")"
                 | "(" type ("," type)* ")" "->" type  (* fn type *)
                 | "[" type ";" expr "]"
                 | "[" type "]"
                 | "&" lifetime? "mut"? type
                 | "*" ("const" | "mut") type
                 | "!" type                              (* Result<T, Error> *)
                 | "?" type                              (* Option<T> *)
                 | "dyn" bounds
                 | "impl" bounds
                 | "for" "<" lifetime ">" type
                 | "Self"
                 | "Never"
type_suffix    ::= "?" | "!"
type_args      ::= generic_arg ("," generic_arg)* ","?
generic_arg    ::= lifetime | type | int_lit
path           ::= ident ("::" ident)*
bounds         ::= bound ("+" bound)*
bound          ::= path type_args? | lifetime
where_clause   ::= "where" where_pred ("," where_pred)* ","?
where_pred     ::= type ":" bounds
lifetime       ::= "'" ident
```

1. `?T` y `!T` son azúcar; se normalizan a `Option[T]`/`Result[T, Error]`.
2. `&T`/`&mut T` son referencias; `*const T`/`*mut T` son raw pointers.
3. `[T; N]` es array; `[T]` es slice (sin tamaño).
4. `dyn Trait` es trait object; `impl Trait` es tipo opaco.
5. `for<'a> T` es HRTB; `T` puede ser un fn type.
6. `Never` es `!`; `Unit` es `()`.
7. Los tipos de función son `(A, B) -> C`.

### 60.7 Expresiones y sentencias

```ebnf
statement      ::= binding
                 | assignment
                 | "return" expr? NEWLINE
                 | "break" expr? NEWLINE
                 | "continue" NEWLINE
                 | expr NEWLINE
binding        ::= ("bind" | "morph") pattern (":" type)? "=" expr NEWLINE
assignment     ::= assignment_expr NEWLINE
branch         ::= expr | NEWLINE INDENT body DEDENT

expr           ::= assignment_expr
assignment_expr::= range_expr (assignment_op assignment_expr)?
assignment_op  ::= "=" | "+=" | "-=" | "*=" | "/=" | "%=" | "&=" | "|=" | "^="
                 | "<<=" | ">>="
range_expr     ::= or_expr ( (".." | "..=") or_expr? )?
or_expr        ::= and_expr ("or" and_expr)*
and_expr       ::= not_expr ("and" not_expr)*
not_expr       ::= "not" not_expr | comparison
comparison     ::= bitor_expr ( ("==" | "!=" | "<" | "<=" | ">" | ">=" | "is" | "isnt" | "in") bitor_expr )?
bitor_expr     ::= bitxor_expr ("|" bitxor_expr)*
bitxor_expr    ::= bitand_expr ("^" bitand_expr)*
bitand_expr    ::= shift_expr ("&" shift_expr)*
shift_expr     ::= additive (("<<" | ">>") additive)*
additive       ::= multiplicative (("+" | "-") multiplicative)*
multiplicative ::= cast_expr (("*" | "/" | "%") cast_expr)*
cast_expr      ::= unary_expr ("as" type)*
unary_expr     ::= ("-" | "+" | "!" | "*" | "&" "mut"? | "awaken") unary_expr
                 | postfix_expr
postfix_expr   ::= primary_expr postfix*
postfix        ::= "." ident
                 | "." int_lit
                 | "(" args? ")"
                 | "[" expr "]"
                 | "?"
                 | "[" type_args "]" "(" args? ")"   (* turbofish call *)
primary_expr   ::= literal
                 | path
                 | "(" expr ")"
                 | "(" ")"
                 | "[" array_items? "]"
                 | "{" map_items? "}"
                 | indented_collection
                 | "if" expr "then" branch ("elseif" expr "then" branch)* ("else" branch)?
                 | "unless" expr "then" branch ("else" branch)?
                 | "match" expr NEWLINE INDENT match_arm+ DEDENT
                 | "loop" NEWLINE INDENT body DEDENT
                 | "while" expr NEWLINE INDENT body DEDENT
                 | "for" pattern "in" expr ("by" expr)? NEWLINE INDENT body DEDENT
                 | "do" NEWLINE INDENT body DEDENT
                 | lambda
                 | block_expr
```

1. La asignación es expresión solo en el parser; el typechecker la trata como
   sentencia (valor `Unit`).
2. `..`/`..=` tienen menor precedencia que `or` pero mayor que `=`.
3. `as` es left-associative; `a as T as U` = `(a as T) as U`.
4. `?` es postfix y solo en funciones compatibles.
5. `awaken` es prefijo y solo en `dream`.
6. `is`/`isnt` son `==`/`!=`; no encadenan.
7. `in` es membresía; no es un operador de rango.

### 60.8 Colecciones, lambdas y bloques

```ebnf
array_items    ::= expr ("," expr)* ","?
map_items      ::= map_item ("," map_item)* ","?
map_item       ::= (ident | expr) ":" expr
indented_collection ::= NEWLINE INDENT collection_body DEDENT
collection_body::= (map_item | expr) (NEWLINE (map_item | expr))*
lambda         ::= "move"? "(" params? ")" "=>" (expr | NEWLINE INDENT body DEDENT)
block_expr     ::= NEWLINE INDENT body DEDENT

match_arm      ::= "when" pattern ("if" expr)? "then" branch NEWLINE
                 | "when" pattern ("if" expr)? NEWLINE INDENT body DEDENT
                 | "else" "then"? branch NEWLINE
args           ::= expr ("," expr)* ","?
```

1. Una colección indentada sin delimitadores se clasifica en §2.6.
2. `map_item` con `ident` usa el nombre como clave string.
3. Un `lambda` con `=>` captura; `move` fuerza captura por valor.
4. Un `block_expr` devuelve el valor de su última expresión.
5. `match` debe ser exhaustivo o tener `else`.
6. `when` es contextual; no es palabra reservada global.

### 60.9 Patrones

```ebnf
pattern        ::= or_pattern
or_pattern     ::= primary_pattern ("|" primary_pattern)*
primary_pattern::= "_"
                 | literal
                 | ident ("@" pattern)?
                 | "ref" "mut"? ident
                 | "(" pattern ("," pattern)* ","? ")"
                 | "[" pattern ("," pattern)* ","? "]"
                 | path ("(" pattern_list? ")" | "{" field_patterns? "}")?
                 | path ".." 
                 | range_pattern
field_patterns ::= ident (":" pattern)? ("," ident (":" pattern)?)* ","?
pattern_list   ::= pattern ("," pattern)* ","?
range_pattern  ::= literal (".." | "..=") literal
```

1. `@` en patrón liga el valor completo; no es el receptor `@`.
2. `ref`/`ref mut` toman referencia al campo.
3. `..` en struct/lista ignora el resto.
4. Un rango de patrón debe ser exhaustivo o tener `else`.
5. Los patrones de camino deben resolver a una variante/struct.
6. `_` es irrefutable; los literales son refutables.
7. `if let`/`while let` usan `pattern` + `=`.

### 60.10 Indentación

```text
algoritmo:
  stack = [0]
  al inicio de cada línea lógica:
    si la línea está vacía o es solo comentario: ignorar
    medir indent = número de espacios iniciales
    si hay tab en la indentación: error PGS-E1003
    si indent > stack.top:
        emitir INDENT; push(indent)
    mientras indent < stack.top:
        emitir DEDENT; pop()
    si indent != stack.top: error PGS-E1004
    emitir tokens de la línea
    emitir NEWLINE
  al final: emitir DEDENT por cada nivel > 0; emitir EOF
```

1. La indentación se mide en espacios, no en columnas visuales.
2. Un nivel debe ser múltiplo de 4; si no, `PGS-E1005`.
3. No se permite mezclar tabs y espacios.
4. Una línea de continuación dentro de `()`/`[]`/`{}` no genera INDENT.
5. Un `NEWLINE` dentro de delimitadores inline se ignora.
6. Un `NEWLINE` después de `..`/`..=` continúa el rango.
7. Un `DEDENT` inesperado es `PGS-E1006`.

### 60.11 Manifiesto

`Tome.toml` no es PenguScript; su gramática es TOML 1.0. Las claves de
`[tome]`, `[dependencies]`, `[features]`, `[[bin]]`, `[[test]]`, `[profile.*]`
y `[workspace]` se definen en §43. El compilador valida:

1. `name` y `version` obligatorios.
2. `pengu` y `rust-version` compatibles.
3. `path` de targets con extensión `.pengu`.
4. `[cargo]` no puede sobrescribir claves protegidas.
5. Un `Tome.lock` generado no se edita.

### 60.12 Criterios de aceptación

- [x] La gramática cubre todos los ejemplos del documento.
- [x] Léxico, items, tipos, expresiones, patrones y atributos están definidos.
- [x] El algoritmo de indentación es determinista.
- [x] Las ambigüedades se resuelven en §62.
- [x] La gramática puede alimentar un parser LL(1) con lookahead acotado.

[↑ Volver al índice](#indice)
