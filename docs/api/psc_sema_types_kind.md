# psc.sema.types.kind

> Source: `src/psc/sema/types/kind.pengu`

psc/sema/types/kind.pengu — vocabulario del modelo de tipos.

Un tipo es un `SemaType` plano en una `SemaTypeTable`; su identidad es el
índice (`TypeId`). Los hijos variables (una tupla, los argumentos de un tipo
genérico) viven en `type_children` con `first/count`; los metadatos nominales
y de función viven en tablas laterales. Este archivo solo contiene el
vocabulario y el registro POD, sin lógica, para que `table.pengu` y
`compat.pengu` puedan importarlo sin ciclos.

## Memoria
`SemaType` es POD: no posee strings ni listas. `name` es un `NameId` del
pool del programa.

---

### `SemaTypeKind`

> omen SemaTypeKind

```pengu
    TkAny
    TkNull
    TkVoid
    TkOpaque
    TkError
    TkBase
    TkRef
    TkFrozen
    TkArray
    TkSlice
    TkMany
    TkList
    TkMap
    TkMaybe
    TkResult
    TkTuple
    TkRange
    TkCVarArgs
    TkFn
    TkRune
    TkEcho
    TkOmen
    TkAlias
    TkSeal
    TkConcept
    TkTypeParam
```

 Variante del modelo de tipos.

 `TkError` es el tipo veneno de recuperación: compatible con todo para no
 generar cascadas después del primer error. `TkVoid`/`TkOpaque`/`TkAny`/
 `TkNull`/`TkCVarArgs` son singletons creados por `table.pengu`.

### `SemaNominalKind`

> omen SemaNominalKind

```pengu
    NkRune
    NkEcho
    NkOmen
    NkAlias
    NkSeal
    NkConcept
```

 Clase nominal de una declaración de tipo.

### `SemaType`

> rune SemaType

```pengu
    kind as SemaTypeKind
    name as int
    a as int
    b as int
    c as int
    first as int
    count as int
```

 Registro POD de un tipo.

 El significado de `name/a/b/c/first/count` depende de `kind`; `table.pengu`
 documenta cada constructor y es la única puerta de creación.

### `type_kind_name`

> **type_kind_name**(kind: SemaTypeKind) -> string

 Etiqueta estable para dumps y diagnósticos.

 ## Memoria
 Devuelve un literal; no asigna.

### `nominal_kind_name`

> **nominal_kind_name**(kind: SemaNominalKind) -> string

 Etiqueta estable de una clase nominal.

 ## Memoria
 Devuelve un literal; no asigna.

### `nominal_type_kind`

> **nominal_type_kind**(kind: SemaNominalKind) -> SemaTypeKind

 Tipo de tipo que corresponde a una clase nominal.

 ## Memoria
 Devuelve un literal; no asigna.

