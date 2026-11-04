# psc.sema.symbols.symbol

> Source: `src/psc/sema/symbols/symbol.pengu`

psc/sema/symbols/symbol.pengu — símbolos y valores constantes.

`SemaSymbol` es un registro POD en `SemaSymbols.symbols`. Los nombres son
`NameId`; los tipos, `TypeId`. Todo lo que un símbolo posee (doc, attrs,
valor constante) es un índice a otra tabla del programa.

## Memoria
Los símbolos son POD; las tablas que los contienen se liberan en bloque desde
`SemaProgram`.

---

### `SemaSymbolKind`

> omen SemaSymbolKind

```pengu
    SkVar
    SkLet
    SkConst
    SkParam
    SkStaticVar
    SkWeave
    SkDeclare
    SkType
    SkRune
    SkEcho
    SkOmen
    SkAlias
    SkSeal
    SkConcept
    SkImport
    SkCDefine
    SkTest
```

 Clase de un símbolo.

### `SYM_MUTABLE`

> **SYM_MUTABLE** : int

 Bits de `SemaSymbol.flags`.

### `SYM_PUBLIC`

> **SYM_PUBLIC** : int

_Undocumented._

### `SYM_STATIC`

> **SYM_STATIC** : int

_Undocumented._

### `SYM_RITUAL`

> **SYM_RITUAL** : int

_Undocumented._

### `SYM_INLINE`

> **SYM_INLINE** : int

_Undocumented._

### `SYM_ANTIQUUS`

> **SYM_ANTIQUUS** : int

_Undocumented._

### `SYM_SELF_VALUE`

> **SYM_SELF_VALUE** : int

_Undocumented._

### `SYM_DEFINED_IN_C`

> **SYM_DEFINED_IN_C** : int

_Undocumented._

### `SYM_MUTATING`

> **SYM_MUTATING** : int

_Undocumented._

### `SYM_HAS_DOC`

> **SYM_HAS_DOC** : int

_Undocumented._

### `SYM_NO_RETURN`

> **SYM_NO_RETURN** : int

_Undocumented._

### `SYM_EXPORT`

> **SYM_EXPORT** : int

_Undocumented._

### `SYM_GET_ALIAS`

> **SYM_GET_ALIAS** : int

 Alias puro `get_<metodo>` generado por `@mutates`.

### `SemaConstKind`

> omen SemaConstKind

```pengu
    CkNone
    CkInt
    CkFloat
    CkBool
    CkString
    CkChar
    CkTypeName
```

 Clase de valor constante.

### `SemaConst`

> rune SemaConst

```pengu
    kind as SemaConstKind
    i as i64
    f as f64
    b as bool
    name as int
```

 Valor constante POD.

### `SemaSymbol`

> rune SemaSymbol

```pengu
    name as int
    type as int
    kind as SemaSymbolKind
    flags as int
    c_name as int
    alias_of as int
    module as int
    line as int
    col as int
    start as int
    end as int
    attrs_node as int
    doc as int
    const_id as int
    bounds_first as int
    bounds_count as int
    module_scope as int
```

 Símbolo resuelto.

### `SemaTemplate`

> rune SemaTemplate

```pengu
    name as int
    owner as int
    node as int
    params_first as int
    params_count as int
    kind as SemaSymbolKind
```

 Plantilla genérica registrada.

### `SemaInstance`

> rune SemaInstance

```pengu
    kind as SemaSymbolKind
    template_node as int
    template_symbol as int
    template_type as int
    args_first as int
    args_count as int
    receiver as int
    type as int
    flags as int
```

 Instancia monomorfizada.

### `symbol_kind_name`

> **symbol_kind_name**(kind: SemaSymbolKind) -> string

 Nombre de una clase de símbolo para dumps.

 ## Memoria
 Devuelve un literal.

