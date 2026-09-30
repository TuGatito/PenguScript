<USER_REQUEST>
# 🐧 Análisis Profundo y Plan Maestro: Genéricos de Nivel Producción en PenguScript

> **Audiencia:** Agente implementador del compilador.  
> **Objetivo:** Llevar los genéricos de PenguScript al nivel de Go / Rust / C++ en seguridad y expresividad, sin romper el minimalismo del lenguaje y **sin fugas de memoria**, para que la stdlib pueda apoyarse en ellos (listas, sets, maps, iteradores, opcionales, resultados, etc.).  
> **Alcance:** `pengu_runtime.h`, `pengu_grammar.py`, `pengu_checker.py`, `pengu_infer.py`, `pengu_codegen.py`, `pengu_types.py`, `pengu_symbols.py`, `LANGUAGE.md`.

---

## 📊 Parte 1 — Estado actual de los genéricos

Lo que ya existe hoy en PenguScript 0.14/0.15:

| Feature | Estado | Notas |
|---|---|---|
| Plantillas de `rune`, `echo`, `omen`, `alias`, `concept` con `shard T` | ✅ Funciona | `generic_runes`, `generic_echos`, `generic_omens`, `generic_aliases`, `generic_concepts` |
| `weave` genéricos con `shard T` | ✅ Funciona | Monomorphización por `mangle_type` |
| Bounds con `where T: Concept` | ✅ Funciona (parcial) | Se valida solo en call-site, no en el cuerpo |
| `enchanting map of shard K to shard V:` | ✅ Funciona | 0.15 introdujo métodos genéricos sobre contenedores |
| Monomorphización por mangling (`Box_int`, `map_of_string_to_int`) | ✅ Funciona | Pero frágil (`name.split("_")[0]`) |
| Sustitución de tipos (`Type.substitute`) | ✅ Funciona | Limitada, no maneja HKT ni parciales |
| Métodos genéricos en tipos genéricos | ⚠️ Parcial | `_check_enchanting_decl` mezcla params de receptor y de método |
| Inferencia en call-site | ⚠️ Parcial | Falla cuando un param solo aparece en el retorno |
| `generic_args` explícitos (`calling id of int with 5`) | ⚠️ Parcial | El grammar lo soporta; el checker lo usa solo en algunos caminos |
| Runtime para contenedores genéricos (`list of string`, `map of string to list of int`) | ❌ **Roto / leak** | El banish no es recursivo, el push no clona |

---

## 🔍 Parte 2 — Comparación honesta con Go, Rust y C++

| Capacidad | Go | Rust | C++ | PenguScript (hoy) | ¿Falta? |
|---|---|---|---|---|---|
| Genéricos a nivel de tipo | ✅ | ✅ | ✅ (templates) | ✅ | — |
| Genéricos a nivel de función | ✅ (1.18+) | ✅ | ✅ | ✅ | — |
| Bounds/constraints | ✅ (interfaces) | ✅ (traits) | ✅ (concepts C++20) | ✅ (concepts) | ⚠️ builtins |
| Type sets / uniones de constraints | ✅ (`~int \| ~string`) | ⚠️ (con `where` + auto traits) | ✅ (`requires`) | ❌ | **Sí** |
| Associated types | ❌ | ✅ | ✅ (typedef en traits) | ❌ | **Sí (crítico)** |
| Const generics (valores como parámetros) | ❌ (usa `[N]T` con `N` de expr) | ✅ (`const N: usize`) | ✅ (NTTP) | ⚠️ (`with size N`) | **Sí** |
| Derivación automática de traits (Eq, Hash, Ord, Clone, Drop) | ❌ (structural) | ✅ (`derive`) | ⚠️ (manual) | ❌ | **Sí (crítico)** |
| Drop / destructores para contenedores | N/A (GC) | ✅ (`Drop`) | ✅ (destructores) | ❌ | **Sí (crítico)** |
| Clone / deep-copy controlado | N/A | ✅ (`Clone`) | ✅ (copy ctor) | ❌ | **Sí (crítico)** |
| Iteradores genéricos (`Iterator<Item=T>`) | ✅ (interfaces) | ✅ (trait) | ✅ (concepts) | ❌ | Sí |
| Especialización / partial spec | ❌ | ⚠️ (inestable) | ✅ | ❌ | Opcional |
| Trait objects / dynamic dispatch | ✅ | ✅ (`dyn Trait`) | ✅ | ❌ (por diseño) | Opcional |
| Default type params | ❌ | ✅ | ✅ | ❌ | Nice-to-have |
| Variadic generics | ❌ | ❌ (en nightly) | ✅ | ⚠️ (`many T`) | Solo `many` ya existe |
| F-bounded polymorphism (`T: Ord<T>`) | ❌ | ✅ | ✅ | ❌ | Nice-to-have |
| Coherence / orphan rules | N/A | ✅ | ⚠️ (ADL) | ❌ | **Sí** |

**Conclusión:** PenguScript tiene el 60 % del camino. Lo que falta para "estar a la par" son cuatro cosas:

1. **Drop / clone automáticos** (fuga de memoria en contenedores anidados).
2. **Derivación de traits built-in** (`Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Forma`).
3. **Operadores genéricos con bounds numéricos** (`a + b` dentro de `weave sum shard T where T: Num`).
4. **Associated types** (para iteradores y colecciones abstractas).

Todo lo demás es *nice-to-have*.

---

## 🐛 Parte 3 — Bugs y huecos concretos

### 🔴 Bug 1 — `TypeParam` no satisface operadores aritméticos
En `pengu_infer.py::infer`:
```python
elif rule in ("add", "sub", ...):
    left_t = self.infer(node.children[0])
    ...
    if not left_t.is_numeric() and not isinstance(left_t, AnyType):
        raise ...
```
`TypeParam.is_numeric()` devuelve `False` (hereda de `Type`), así que:
```pengu
weave add shard T with a as T, b as T into T:
    return a + b
```
falla con `E0005: Arithmetic operator 'add' requires numeric type, got 'T'`. **Rompe todo genérico numérico.**

**Fix:** `TypeParam` debe respetar sus bounds: si `T` tiene bound `Num`, `is_numeric()` devuelve `True`. Alternativa: tratar `TypeParam` como `AnyType` en el checker de operadores (acepta, no comprueba). Recomiendo lo primero + builtin `Num`.

### 🔴 Bug 2 — `_check_enchanting_decl` mezcla params de receptor y de método
```python
if type_params or m_tparams:
    comb = (type_params or []) + (m_tparams or [])
    self.symbols.methods[(base_tname, m_name)] = impl_fn_t
    self.symbols.generic_methods[(base_tname, m_name)] = (comb, m_decl)
```
Y luego en `pengu_infer.py::_resolve_call_target`:
```python
t_args = getattr(rec_type, "type_args", [])
if t_args and len(t_args) == len(type_params):   # ⚠️ type_params aquí es `comb`
```
Si `weave map shard U` dentro de `enchanting Box shard T`, `comb = ["T", "U"]` pero `t_args` solo tiene `[int]` para `Box of int`. La condición falla y no se monomorfiza. **Bug real.**

**Fix:** separar `receiver_type_params` (vienen de `rec_type.type_args`) y `method_type_params` (se infieren/explicitan en el call-site). Guardar tupla `(receiver_params, method_params, ast)`.

### 🔴 Bug 3 — `ast_to_type` produce placeholders vacíos para genéricos no registrados aún
```python
if type_args:
    args_str = "_".join(a.get_mangled_name() for a in type_args)
    mangled = f"{name}_{args_str}"
    return RuneType(name=mangled, type_args=type_args)
```
Cuando un rune genérico se referencia a sí mismo:
```pengu
rune Node shard T:
    value as T
    next as maybe ref to Node of T
```
`Node of T` cae en la rama de placeholder, devolviendo un `RuneType(name="Node_T")` **sin `fields`**. Al sustituir `T=int`, obtenemos `Node_int` sin campos → el checker rechaza `p.next.value` porque no encuentra `value`.

**Fix:** si el nombre no está registrado pero sí en `generic_runes`, instanciar el template (con `TypeParam` como args) y guardarlo como "plantilla parcial" cacheada. Aplicar idempotencia en `substitute`.

### 🔴 Bug 4 — `RuneType.name.split("_")[0]` es frágil
`RuneType.substitute` y `mangle_type` usan `name.split("_")[0]` para recuperar el nombre base de un tipo monomorfizado. Falla si el usuario nombra un rune `My_Box`:
```pengu
rune My_Box shard T: ...
var b as My_Box of int is ...
# En algún lugar: mangled = "My_Box_int", luego name.split("_")[0] -> "My" 💥
```

**Fix:** añadir `base_name` explícito a `RuneType`/`EchoType`/`OmenType`/`AliasType`, o mantener un mapa `mangled → base_name` en el `SymbolTable`.

### 🔴 Bug 5 — `pengu_banish_list` NO libera strings anidados
```c
static inline void pengu_banish_list(PenguList *list) {
    if (list && list->data) {
        free(list->data);      // ← solo el buffer externo
        ...
    }
}
```
Uso típico de la stdlib:
```pengu
var parts as list of string is calling scrolls.split with text, ","
# ... usar parts
banish parts
```
**Fuga:** todos los strings dentro de `parts` filtran. Igual para `list of list of X`, `list of map of ...`.

### 🔴 Bug 6 — `pengu_banish_map` solo limpia strings planos
```c
if (map->key_size == sizeof(PenguString)) pengu_banish_string(...);
if (map->val_size == sizeof(PenguString)) pengu_banish_string(...);
```
Para `map of string to list of int`, los values (listas) leak. Para `map of Point to string` (Point = rune con string dentro), el string dentro de Point leak.

### 🔴 Bug 7 — `pengu_map_put` copia shallow para tipos no-string
```c
if (map->key_size == sizeof(PenguString))
    *(PenguString *)k = pengu_string_copy(...);
else
    memcpy(k, key, map->key_size);  // ⚠️ shallow
```
Si `K` es un rune con un campo string, se copia el puntero `data`, compartiendo el buffer. Al banishing uno de los dos, el otro queda colgando.

### 🔴 Bug 8 — `pengu_list_push` copia shallow
Mismo problema con listas: `memcpy(target, item, list->elem_size)` copia solo la estructura. Si el elemento es `PenguString`, copia `{data, len}` y comparte `data`.

### 🔴 Bug 9 — Sin validación de ciclos de tamaño infinito
```pengu
rune Bad shard T:
    inner as Bad of T       # ← ciclo por valor
```
El codegen emite:
```c
struct Bad_int {
    struct Bad_int inner;   // 💥 incomplete type
};
```
No hay detección. Debería reportarse `E0044: InfiniteTypeSizeError`.

### 🔴 Bug 10 — Sin validación de coherencia en `bind`
```pengu
bind Foo with Bar: ...
bind Foo with Bar: ...   # ← duplicado, se sobrescribe silenciosamente
```
Falta `E0047: DuplicateConceptBindingError`. Igual para `enchanting Foo:` repetido con el mismo método.

### 🔴 Bug 11 — `_generated_instances` es un set global por sesión
Vive en `SymbolTable`, compartido entre todas las compilaciones del proyecto. En un proyecto con múltiples módulos puede impedir la generación de instancias en el orden correcto si un módulo se compila dos veces.

**Fix:** hacerlo por pase de `collect_declarations`, no persistente.

### 🔴 Bug 12 — `_collect_monomorphized_weave` no propaga `subst_map` transitivamente
Cuando `Box of Box of int` se monomorfiza, la llamada interna a `Box_int.metodo` dentro del cuerpo del método puede no instanciar `Box_int` primero. El código compila por suerte (todo se emite al final) pero el orden de emisión en C puede violar dependencias.

**Fix:** Topological sort de instancias monomorfizadas antes de emitir.

### 🟡 Hueco 13 — Operadores no se validan dentro de genéricos con bounds
Incluso arreglando el Bug 1, no hay forma de que el checker sepa que `T: Num` implica `+`, `-`, `*`, `/`, `%`. Necesitamos builtin concepts.

### 🟡 Hueco 14 — `try` no funciona con genéricos
```pengu
weave parsey shard T with s as string into result of T to string:
    return try parse_T(s)   # no se puede saber que parse_T devuelve result of T to string
```
Falta resolver el tipo de retorno en presencia de `TypeParam`.

### 🟡 Hueco 15 — Sin acceso a "el tipo del elemento" en el cuerpo de un genérico
```pengu
weave process shard T with xs as list of T into void:
    for x in xs:
        # no puedo declarar `var copy as T` sin saber T en runtime
        var copy as T is x     # ⚠️ el checker puede no permitirlo
```
En realidad sí funciona por sustitución, pero necesita validarse.

---

## 💧 Parte 4 — Fugas de memoria: análisis detallado

Ejemplo real de la stdlib (`std.scrolls`):

```pengu
weave demonstrate into void:
    var parts as list of string is calling scrolls.split with "a,b,c", ","
    for p in parts:
        calling spark.println with p
    banish parts   # ← deja 3 strings sin liberar
```

Y este:

```pengu
var cache as map of string to list of int is map of string to int
with cache:
    calling .put with "a", [1, 2, 3]   # ⚠️ la lista [1,2,3] se copia shallow → fuga o corrupción
banish cache                            # ⚠️ el buffer de la lista interna no se libera
```

### 🎯 Estrategia de solución

Introducir en el runtime un **modelo de "deinit vtable"** minimalista pero completo:

1. `PenguElemCleanup` y `PenguElemClone`: punteros a función almacenados **en la estructura del contenedor**.
2. `PenguList` y `PenguMap` ganan campos `elem_cleanup`, `elem_clone` (y análogos para key/val en el map).
3. El codegen, al construir un contenedor, elige las funciones correctas **según el tipo del elemento** (en compile-time, monomorfizado).
4. `pengu_list_push`/`pengu_map_put` **clonan profundo** usando el `clone` registrado.
5. `pengu_banish_list`/`pengu_banish_map` **liberan recursivamente** llamando al `cleanup`.

Esto resuelve **Bug 5, 6, 7, 8** de un golpe y hace segura toda la stdlib.

---

## 🎯 Parte 5 — Plan de Implementación

### 5.1 🆕 Palabras clave nuevas (mínimas, latinas, "mágicas")

Solo **dos** son realmente necesarias. Las demás se implementan como **conceptos built-in** (no keywords).

| Keyword | Latin | Rol | Ejemplo |
|---|---|---|---|
| `derive` | *derivare* | Genera impls automáticas para concepts built-in | `rune Point derive Par, Ordo, Vinculum: ...` |
| `cyclus` | *cyclus* | Marca un tipo genérico como recursivo-por-referencia (evita el error de tamaño infinito) | `rune Node cyclus shard T: ...` |

**Concepts built-in** (no keywords; viven en `SymbolTable._init_builtins()`):

| Concept | Latin | Métodos / Operadores que habilita |
|---|---|---|
| `Num` | *numerus* | `+`, `-`, `*`, `/`, `%`, unario `-` |
| `Par` | *par* | `==`, `!=` |
| `Ordo` | *ordo* | `<`, `<=`, `>`, `>=` |
| `Vinculum` | *vinculum* | hashing (para claves de `map`) |
| `Imago` | *imago* | clone profundo (para push/put) |
| `Nexus` | *nexus* | cleanup (drop) para banish recursivo |
| `Forma` | *forma* | interpolación `{x}` (display) |
| `Iterabilis` | *iterabilis* | `for x in coll` genérico |
| `Donum` | *donum* | valor por defecto (`donum T`) |

**Por qué estos y no más:**  
- `Num/Par/Ordo/Vinculum/Imago/Nexus` son necesarios para que las colecciones genéricas funcionen sin leaks y con semántica predecible.
- `Forma` es para `string.format` e interpolación en genéricos.
- `Iterabilis` es para `for x in xs` donde `xs: T` con `T: Iterabilis`.
- `Donum` es opcional, pero permite `list of T` con elementos default.

**No añadir `derive` como palabra reservada completa**: tratarla como **modificador de declaración** (como `inline`/`ritual`), activa solo tras `rune`/`echo`/`omen`. Así no rompe código existente con variables llamadas `derive`.

### 5.2 🔧 Cambios en el runtime (`pengu_runtime.h`)

#### 5.2.1 Nuevos typedefs y campos

```c
/* Vtable mínima para contenedores genéricos. */
typedef void (*PenguElemCleanup)(void *elem);
typedef void (*PenguElemClone)(void *dst, const void *src);

typedef struct {
    void *data;
    int len;
    int cap;
    size_t elem_size;
    PenguElemCleanup elem_cleanup;  /* NULL = POD */
    PenguElemClone   elem_clone;    /* NULL = memcpy */
} PenguList;

typedef struct {
    PenguMapEntry *entries;
    int len;
    int cap;
    size_t key_size;
    size_t val_size;
    PenguElemCleanup key_cleanup;
    PenguElemCleanup val_cleanup;
    PenguElemClone   key_clone;
    PenguElemClone   val_clone;
} PenguMap;
```

**Compatibilidad binaria:** los campos nuevos van al final; los constructores antiguos siguen funcionando.

#### 5.2.2 Constructores nuevos

```c
static inline PenguList pengu_list_new_owned(size_t elem_size, int cap,
                                             PenguElemCleanup cleanup,
                                             PenguElemClone clone) {
    PenguList list = pengu_list_new(elem_size, cap);
    list.elem_cleanup = cleanup;
    list.elem_clone = clone;
    return list;
}

static inline PenguMap pengu_map_new_owned(size_t ksz, size_t vsz,
                                           PenguElemCleanup kcln, PenguElemCleanup vcln,
                                           PenguElemClone kcln_, PenguElemClone vcln_) {
    PenguMap map = pengu_map_new(ksz, vsz);
    map.key_cleanup = kcln;
    map.val_cleanup = vcln;
    map.key_clone = kcln_;
    map.val_clone = vcln_;
    return map;
}
```

#### 5.2.3 Banish recursivo

```c
static inline void pengu_banish_list(PenguList *list) {
    if (list && list->data) {
        if (list->elem_cleanup) {
            for (int i = 0; i < list->len; ++i) {
                list->elem_cleanup((char *)list->data + (size_t)i * list->elem_size);
            }
        }
        free(list->data);
        list->data = NULL;
        list->len = 0;
        list->cap = 0;
        list->elem_cleanup = NULL;
        list->elem_clone = NULL;
    }
}

static inline void pengu_banish_map(PenguMap *map) {
    if (map && map->entries) {
        for (int i = 0; i < map->cap; ++i) {
            if (map->entries[i].occupied) {
                if (map->entries[i].key) {
                    if (map->key_cleanup) map->key_cleanup(map->entries[i].key);
                    free(map->entries[i].key);
                }
                if (map->entries[i].val) {
                    if (map->val_cleanup) map->val_cleanup(map->entries[i].val);
                    free(map->entries[i].val);
                }
            }
        }
        free(map->entries);
        map->entries = NULL;
        map->len = 0;
        map->cap = 0;
        map->key_cleanup = NULL;
        map->val_cleanup = NULL;
        map->key_clone = NULL;
        map->val_clone = NULL;
    }
}
```

#### 5.2.4 Push/put con clonado profundo

```c
static inline void pengu_list_push(PenguList *list, const void *item) {
    if (!list || !item) return;
    if (list->len >= list->cap) {
        /* ... realloc como antes ... */
    }
    char *target = (char *)list->data + ((size_t)list->len * list->elem_size);
    if (list->elem_clone) {
        list->elem_clone(target, item);
    } else {
        memcpy(target, item, list->elem_size);
    }
    list->len++;
}
```

Análogo para `pengu_map_alloc_slot` (usar `key_clone`/`val_clone` si están seteados).

#### 5.2.5 Wrappers de clone/cleanup para tipos comunes

```c
static inline void pengu_string_clone(void *dst, const void *src) {
    *(PenguString *)dst = pengu_string_copy(*(const PenguString *)src);
}
/* pengu_banish_string ya tiene la firma correcta: void(PenguString*) */

static inline void pengu_list_clone(void *dst, const void *src) {
    PenguList *d = (PenguList *)dst;
    const PenguList *s = (const PenguList *)src;
    *d = pengu_list_new_owned(s->elem_size, s->len,
                              s->elem_cleanup, s->elem_clone);
    for (int i = 0; i < s->len; ++i) {
        pengu_list_push(d, (const char *)s->data + (size_t)i * s->elem_size);
    }
}

static inline void pengu_map_clone(void *dst, const void *src) {
    PenguMap *d = (PenguMap *)dst;
    const PenguMap *s = (const PenguMap *)src;
    *d = pengu_map_new_owned(s->key_size, s->val_size,
                             s->key_cleanup, s->val_cleanup,
                             s->key_clone, s->val_clone);
    for (int i = 0; i < s->cap; ++i) {
        if (s->entries[i].occupied) {
            pengu_map_put(d, s->entries[i].key, s->entries[i].val);
        }
    }
}
```

Nota: `pengu_banish_list` y `pengu_banish_map` ya tienen la firma `void(void*)` tras un cast trivial, así que pueden usarse directamente como `PenguElemCleanup`.

### 5.3 🧠 Cambios en `pengu_types.py`

#### 5.3.1 `TypeParam` con bounds operativos

```python
@dataclass
class TypeParam(Type):
    name: str
    bounds: List[str] = field(default_factory=list)

    def is_numeric(self) -> bool:
        return "Num" in self.bounds

    def is_int(self) -> bool:
        return "Num" in self.bounds  # conservador: Num incluye floats

    def is_float(self) -> bool:
        return "Num" in self.bounds

    def is_string(self) -> bool:
        return "Forma" in self.bounds

    def is_bool(self) -> bool:
        return "Par" in self.bounds and "Num" not in self.bounds
```

#### 5.3.2 `RuneType`/`EchoType`/`OmenType` con `base_name` explícito

```python
@dataclass
class RuneType(Type):
    name: str
    fields: Dict[str, Type] = field(default_factory=dict)
    ...
    base_name: Optional[str] = None   # NUEVO

    def get_base_name(self) -> str:
        return self.base_name or self.name.split("_")[0]
```

`mangle_type` y `substitute` deben usar `get_base_name()`. Los sitios que hoy usan `name.split("_")[0]` deben migrarse.

#### 5.3.3 `substitute` con manejo de placeholders parciales

```python
def substitute(self, type_map: Dict[str, Type]) -> Type:
    if not type_map:
        return self
    new_fields = {k: v.substitute(type_map) for k, v in self.fields.items()}
    new_args = [a.substitute(type_map) for a in self.type_args]
    if not new_args and self.type_params:
        new_args = [type_map.get(tp, TypeParam(tp)) for tp in self.type_params]
    if new_args and not any(isinstance(a, TypeParam) for a in new_args):
        mangled = f"{self.get_base_name()}_{'_'.join(a.get_mangled_name() for a in new_args)}"
        return RuneType(name=mangled, fields=new_fields,
                        base_name=self.get_base_name(),
                        type_args=new_args)
    return RuneType(name=self.name, fields=new_fields,
                    base_name=self.get_base_name(),
                    type_params=self.type_params, type_args=new_args)
```

#### 5.3.4 Asociar built-in concepts

```python
BUILTIN_CONCEPTS = {
    "Num":      ConceptType(name="Num",      methods={}),
    "Par":      ConceptType(name="Par",      methods={}),
    "Ordo":     ConceptType(name="Ordo",     methods={}),
    "Vinculum": ConceptType(name="Vinculum", methods={}),
    "Imago":    ConceptType(name="Imago",    methods={}),
    "Nexus":    ConceptType(name="Nexus",    methods={}),
    "Forma":    ConceptType(name="Forma",    methods={}),
    "Iterabilis": ConceptType(name="Iterabilis", methods={}),
    "Donum":    ConceptType(name="Donum",    methods={}),
}

# Auto-impls para primitivos:
PRIMITIVE_IMPLS = {
    "int":   {"Num", "Par", "Ordo", "Vinculum", "Imago", "Forma", "Donum"},
    "i8":    {"Num", "Par", "Ordo", "Vinculum", "Imago", "Forma", "Donum"},
    "i16":   {...},
    "i32":   {...},
    "i64":   {...},
    "u8":    {...},
    "u16":   {...},
    "u32":   {...},
    "u64":   {...},
    "usize": {...},
    "isize": {...},
    "float": {"Num", "Par", "Ordo", "Forma", "Donum"},
    "f32":   {"Num", "Par", "Ordo", "Forma", "Donum"},
    "f64":   {"Num", "Par", "Ordo", "Forma", "Donum"},
    "bool":  {"Par", "Vinculum", "Imago", "Forma", "Donum"},
    "char":  {"Par", "Ordo", "Vinculum", "Imago", "Forma"},
    "byte":  {"Par", "Ordo", "Vinculum", "Imago"},
    "string":{"Par", "Ordo", "Vinculum", "Imago", "Forma", "Donum", "Iterabilis"},
    # containers
    "<list>":   {"Par", "Iterabilis", "Imago", "Nexus"},
    "<map>":    {"Par", "Iterabilis", "Imago", "Nexus"},
    "<slice>":  {"Par", "Iterabilis"},
    "<maybe>":  {"Par", "Imago", "Nexus"},
    "<result>": {"Par", "Imago", "Nexus"},
}
```

`implements_concept()` debe consultar este diccionario antes del `concept_bindings` del usuario.

### 5.4 🕵️ Cambios en `pengu_symbols.py`

- Añadir `generic_method_receiver_params` y `generic_method_method_params` a las entradas de `generic_methods`:
  ```python
  self.generic_methods[(base_name, m_name)] = (recv_params, method_params, ast)
  ```
- Añadir `BUILTIN_CONCEPTS` al `_init_builtins()`.
- Añadir validación en `define` para detectar `bind` duplicados (Bug 10).

### 5.5 ✅ Cambios en `pengu_checker.py`

#### 5.5.1 Validar operadores dentro de genéricos (Bug 1 + Hueco 13)

En `_check_weave_decl`, cuando procesamos un `TypeParam` con bounds, el checker debe propagar los bounds al `TypeInferrer` para que `add`, `eq`, etc. sepan qué permitir.

Actualizar `TypeInferrer.infer`:
```python
elif rule in ("add", "sub", "mul", "div", "mod"):
    left_t = self.infer(node.children[0])
    right_t = self.infer(node.children[1])
    if isinstance(left_t, TypeParam) or isinstance(right_t, TypeParam):
        tp = left_t if isinstance(left_t, TypeParam) else right_t
        if "Num" not in tp.bounds and "Any" not in tp.bounds:
            raise self._make_error(...  # E0049: MissingNumBound
        return tp if isinstance(left_t, TypeParam) else right_t
    ...
```

Lo mismo para `eq/ne` (requieren `Par`), `lt/le/gt/ge` (requieren `Ordo`), e iteración (`Iterabilis`).

Nuevo código de error: **`E0049: MissingBoundForOperationError`**.

#### 5.5.2 Detectar ciclos infinitos de tamaño (Bug 9)

Nuevo pase en `_check_rune_decl` / `_check_echo_decl`:

```python
def _check_infinite_type(t: Type, visiting: Set[str]) -> Optional[str]:
    if isinstance(t, RuneType):
        if t.name in visiting:
            return t.name  # ciclo
        visiting.add(t.name)
        for f in t.fields.values():
            if _check_infinite_type(f, visiting):
                return t.name
        visiting.discard(t.name)
    elif isinstance(t, RefType):
        return None   # ref rompe el ciclo
    ...
```

Si hay ciclo sin `ref` intermedio → **`E0050: InfiniteTypeSizeError`**.

#### 5.5.3 Coherencia de `bind` (Bug 10)

```python
key = (target_name, concept_name)
if key in self.symbols.concept_bindings:
    raise SemanticError(
        f"Duplicate concept binding: '{target_name}' already bound to '{concept_name}'",
        code="E0047"
    )
```

#### 5.5.4 Validar `derive`

Si el usuario escribe `rune Point derive Par, Ordo:`:
1. Verificar que todos los campos son `Par` y `Ordo`.
2. Registrar en `symbols.concept_bindings[(Point, Par)]` con métodos auto-generados.
3. Emitir código C en el codegen.

#### 5.5.5 Aceptar `TypeParam` como clave/valor de contenedores con bounds

```pengu
weave invert shard K, V where K: Par and K: Vinculum, V: Imago
    with m as map of K to V into map of V to K:
    ...
```

Hoy falla porque `TypeParam` no satisface `is_compatible` para las operaciones de map. Debe pasar si `K` tiene `Par` y `Vinculum`.

### 5.6 🏭 Cambios en `pengu_codegen.py`

#### 5.6.1 Emitir las funciones de cleanup/clone por instancia

Añadir al final del bundle:

```c
/* Auto-generated: cleanup/clone para instancias monomorfizadas */
static void _pengu_clone_string(void *dst, const void *src) {
    *(PenguString *)dst = pengu_string_copy(*(const PenguString *)src);
}

static void _pengu_cleanup_string(void *elem) {
    pengu_banish_string((PenguString *)elem);
}

static void _pengu_clone_list_of_string(void *dst, const void *src) {
    pengu_list_clone(dst, src);  /* ya es recursivo */
}
/* ... etc */
```

Realmente, como los clones/cleanups de string/list/map ya existen en el runtime, el codegen solo necesita mapear el tipo al puntero de función correcto:

```python
def _element_cleanup_fn(t: Type) -> str:
    t = unwrap(t)
    if isinstance(t, BaseType) and t.name == "string":
        return "((PenguElemCleanup)pengu_banish_string)"
    if isinstance(t, ListType):
        return "((PenguElemCleanup)pengu_banish_list)"
    if isinstance(t, MapType):
        return "((PenguElemCleanup)pengu_banish_map)"
    if isinstance(t, MaybeType):
        return "((PenguElemCleanup)pengu_banish_maybe)"  # NUEVO en runtime
    if isinstance(t, RuneType) and t.implements("Nexus"):
        return f"((PenguElemCleanup){t.name}_nexus)"
    return "NULL"

def _element_clone_fn(t: Type) -> str:
    t = unwrap(t)
    if isinstance(t, BaseType) and t.name == "string":
        return "_pengu_clone_string"
    if isinstance(t, ListType):
        return "_pengu_clone_list"
    if isinstance(t, MapType):
        return "_pengu_clone_map"
    if isinstance(t, MaybeType):
        return "_pengu_clone_maybe"
    if isinstance(t, RuneType) and t.implements("Imago"):
        return f"_pengu_clone_{t.name}"
    return "NULL"
```

#### 5.6.2 Emitir constructores con cleanup/clone

En `_translate_expr_impl` para `list_init_expr`:
```python
elem_t = ast_to_type(node.children[0], ...)
elem_c = CTypeMapper.to_c_type(elem_t)
cln = self._element_cleanup_fn(elem_t)
clo = self._element_clone_fn(elem_t)
return f"pengu_list_new_owned(sizeof({elem_c}), {cap}, {cln}, {clo})"
```

Análogo para `map_init_expr`.

**Compatibilidad hacia atrás:** `list of int` sigue emitiendo `pengu_list_new(sizeof(int32_t), cap)` cuando `cln == "NULL"` y `clo == "NULL"` (optimización). Cuando hay cleanup/clone, usar `_owned`.

#### 5.6.3 Emitir la vtable para runes con `derive`

Si `rune Point derive Par, Ordo, Vinculum, Imago:`:

```c
static inline bool Point_Par(const Point *a, const Point *b) {
    return (a->x == b->x) && (a->y == b->y);
}
static inline int Point_Ordo(const Point *a, const Point *b) {
    if (a->x < b->x) return -1;
    if (a->x > b->x) return 1;
    if (a->y < b->y) return -1;
    if (a->y > b->y) return 1;
    return 0;
}
static inline uint32_t Point_Vinculum(const Point *p) {
    uint32_t h = 2166136261u;
    h = pengu_hash_bytes(&p->x, sizeof(p->x)) ^ (h * 16777619u);
    h = pengu_hash_bytes(&p->y, sizeof(p->y)) ^ (h * 16777619u);
    return h;
}
static inline void Point_clone(void *dst, const void *src) {
    *(Point *)dst = *(const Point *)src;
}
static inline void Point_nexus(void *p) {
    Point *pt = (Point *)p;
    /* si algún campo tiene Nexus, llamar aquí */
}
```

#### 5.6.4 Soporte para `generic_args` explícitos

Actualmente, `calling identity of int with 5` no se explota bien. En `_translate_expr_impl`:

```python
elif rule == "calling_expr":
    for ch in node.children[1:]:
        if isinstance(ch, Tree) and ch.data == "generic_args":
            explicit_type_args = [...]
    if explicit_type_args and target_str in self.symbols.generic_functions:
        mangled = f"{target_str}_{'_'.join(t.get_mangled_name() for t in explicit_type_args)}"
        return f"{mangled}(...)"
```

### 5.7 🌊 Cambios en `pengu_infer.py`

#### 5.7.1 Inferencia de genéricos con más de un parámetro

`_resolve_call_target` debe:
1. Unificar param por param contra los argumentos.
2. Si quedan parámetros sin resolver:
   - Si hay `generic_args` explícitos, aplicarlos.
   - Si hay un `expected_type` de retorno, intentar unificar contra él.
   - Si aún quedan, error claro `E0005: Could not infer type parameter 'U'`.

#### 5.7.2 `try` con genéricos

En `_check_try_enclosing_return`, aceptar `TypeParam` como `err_type` si el `curr_ret` también lo es.

#### 5.7.3 Iteración sobre `TypeParam: Iterabilis`

```python
elif rule == "for_in_stmt":
    iter_t = self.infer(iter_node)
    if isinstance(iter_t, TypeParam):
        if "Iterabilis" not in iter_t.bounds:
            raise self._make_error(
                SemanticError,
                f"Cannot iterate over type parameter '{iter_t.name}' without 'Iterabilis' bound",
                iter_node,
                code="E0049",
                help=f"Add 'where {iter_t.name}: Iterabilis' to the generic signature.",
            )
        elem_type = AnyType()  # no se puede saber sin associated types
    ...
```

#### 5.7.4 Tratar `T: Num` como numeric

En `add/sub/mul/div/mod`, si `TypeParam` con `Num`, devolver el `TypeParam` (o su "primer" bound concreto). Ver 5.5.1.

### 5.8 📝 Cambios en `pengu_grammar.py`

#### 5.8.1 Añadir `derive` a las declaraciones

```ebnf
rune_decl: "rune" NAME [cyclus_kw] [shard_params] [derive_clause] ":" _NEWLINE _INDENT field_decl+ _DEDENT
echo_decl: "echo" NAME [cyclus_kw] [shard_params] [derive_clause] ":" ...
omen_decl: "omen" NAME [cyclus_kw] [shard_params] ["with" omen_string_kind] [derive_clause] ":" ...

cyclus_kw: "cyclus"
derive_clause: "derive" custom_type (("," | _AND_SEP) custom_type)*
```

#### 5.8.2 Añadir `donum T` como expresión

```ebnf
donum_expr: "donum" type
?primary: ... | donum_expr
```

#### 5.8.3 Añadir `associated` en concepts (para iteradores)

```ebnf
concept_decl: "concept" NAME [shard_params] ":" _NEWLINE _INDENT concept_member+ _DEDENT
concept_member: concept_method | concept_assoc
concept_assoc: "alias" NAME "as" type _NEWLINE
```

Y uso: `T.Item` resuelve al associated type en el contexto de un bound.

### 5.9 📚 Cambios en `pengu_comptime.py`

Añadir soporte para `is_generic(...)`, `size_of_generic(...)` — opcional, fuera del MVP.

### 5.10 🧪 Testing

Crear `tests/test_generics/` con:

- `test_generic_identity.pengu` — `shard T` en función pura.
- `test_generic_rune.pengu` — `rune Box shard T` + fields + métodos.
- `test_generic_nested.pengu` — `Box of Box of int`.
- `test_generic_list_cleanup.pengu` — push/banish sin leak (valgrind).
- `test_generic_map_cleanup.pengu` — map anidado sin leak.
- `test_derive_par_ordo.pengu` — `derive Par, Ordo`.
- `test_bounds_missing.pengu` — error E0049.
- `test_infinite_size.pengu` — error E0050.
- `test_duplicate_bind.pengu` — error E0047.
- `test_generic_methods_container.pengu` — `enchanting map of shard K to shard V`.

Cada test debe ejecutarse con valgrind (`valgrind --error-exitcode=1 --leak-check=full`). Añadir un target `make test-valgrind` que corra toda la suite con detección de leaks.

---

## 📚 Parte 6 — Ejemplos completos de cómo debe verse

### 6.1 Genérico numérico

```pengu
import std.spark

weave sum shard T where T: Num with xs as list of T into T:
    var acc as T is donum T
    for x in xs:
        set acc is acc + x
    return acc

weave main into int:
    var nums as list of int is [1, 2, 3, 4, 5]
    calling spark.println with (calling sum with nums to string)
    return 0
```

### 6.2 Rune genérico con derive

```pengu
rune Point shard T derive Par, Ordo, Vinculum, Imago:
    x as T
    y as T

enchanting Point shard T:
    weave ritual origin into Point of T:
        return with x is donum T, y is donum T

    weave translate with dx as T, dy as T into Point of T:
        return with x is self->x + dx, y is self->y + dy

weave main into int:
    var p as Point of int is calling Point.origin
    var q as Point of int is calling p.translate with 3, 4
    return 0
```

### 6.3 Iterador con associated types (fase 2)

```pengu
concept Iterabilis shard Self:
    alias Item
    weave next with it as ref to Self into maybe Self.Item

rune Counter:
    current as int
    max as int

bind Counter with Iterabilis:
    alias Item as int
    weave next with it as ref to Counter into maybe int:
        if it->current >= it->max:
            return maybe none
        var v as int is it->current
        set it->current is it->current + 1
        return some v

weave sum_iter shard I where I: Iterabilis with it as ref to I into I.Item:
    var total as I.Item is donum I.Item
    while true:
        var v as maybe I.Item is calling it.next
        if v is not present: break
        set total is total + essence of v.value
    return total
```

### 6.4 Contenedor genérico sin leaks

```pengu
weave demonstrate_no_leak into void:
    var cache as map of string to list of int is map of string to list of int
    with cache:
        calling .put with "primes", [2, 3, 5, 7]
        calling .put with "evens", [2, 4, 6, 8]
    for k in cache:
        var v as list of int is cache at k
        calling spark.println with k + ": " + (v.length to string)
    banish cache   # ← libera: la estructura + cada string + cada lista interna
```

---

## 🗺️ Parte 7 — Roadmap por fases

### Fase 1 (crítica, 1-2 semanas) 🔥
- Runtime: `PenguElemCleanup` + `PenguElemClone` en list/map.
- Codegen: emite `_owned` constructors y vtable por tipo.
- Bug 1: `TypeParam.is_numeric` con bounds.
- Bug 4: `base_name` explícito.
- Bug 5/6/7/8: leaks resueltos.
- Conceptos built-in `Num`, `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus`, `Donum`.

### Fase 2 (importante, 1-2 semanas) 🎯
- `derive` para runes/omens.
- Bug 2: separar receiver/method params.
- Bug 3: placeholders de genéricos auto-referenciales.
- Bug 9/10: validaciones (`E0047`, `E0050`).
- Inferencia multi-parámetro robusta.

### Fase 3 (nice-to-have, 2-4 semanas) 🚀
- Associated types (`concept ... alias Item`).
- `Iterabilis` + iteradores genéricos.
- `donum T`.
- Soporte `list of slice of T`, etc.
- Depuración de `generic_args` explícitos.

### Fase 4 (futuro) 🔮
- Default type params.
- F-bounded polymorphism.
- Const generics extendidos.
- Type sets de Go (`~int | ~string`).

---

## 🎬 Parte 8 — Checklist de aceptación

Al terminar, deben pasar TODOS estos:

- [ ] `valgrind --leak-check=full` sin leaks en `tests/test_generics/*`.
- [ ] `list of string` banish libera cada string.
- [ ] `map of string to list of int` banish libera todo.
- [ ] `weave sum shard T where T: Num` compila y ejecuta.
- [ ] `rune Point shard T derive Par, Ordo:` genera impls.
- [ ] `rune Bad shard T: inner as Bad of T` da `E0050`.
- [ ] `bind Foo with Bar` duplicado da `E0047`.
- [ ] `shard T where T: Num; return a + b` compila.
- [ ] `enchanting map of shard K to shard V: weave has_key with k as K into bool` funciona para `map of string to int`.
- [ ] `Box of Box of int` monomorfiza correctamente y sin re-declaraciones.
- [ ] `LANGUAGE.md` documenta todos los nuevos conceptos built-in, `derive`, `cyclus`.
- [ ] Tests unitarios y de integración cubren cada nuevo path.

---

## 🏁 Conclusión

PenguScript ya tiene el 60 % del camino andado. Con las **dos keywords nuevas** (`derive`, `cyclus`) y **nueve conceptos built-in**, más el **modelo de vtable runtime** (`elem_cleanup`/`elem_clone`), los genéricos quedan:

- ✅ Al nivel de **seguridad de memoria** de Rust (sin leaks en contenedores anidados).
- ✅ Al nivel de **expresividad** de Go (bounds simples, sin HKT complejos).
- ✅ Al nivel de **poder** de C++ (monomorfización completa, derive automático).
- ✅ Manteniendo el **minimalismo** de PenguScript (dos keywords, no veinte).

La deuda técnica más urgente es el **runtime de contenedores** (Fase 1), porque hoy **cualquier** `list of string` en la stdlib filtra memoria. Eso se arregla con el diseño de `PenguElemCleanup`/`PenguElemClone` presentado arriba.

El resto es enriquecimiento incremental, sin romper la compatibilidad hacia atrás.

🎯 **Prioridad de implementación:** Fase 1 → Fase 2 → Fase 3 → Fase 4. No saltar la Fase 1 porque todo lo demás se apoya en ella.
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-09-27T10:23:41-06:00.
</ADDITIONAL_METADATA>