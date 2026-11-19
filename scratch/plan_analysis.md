# Plan de implementación — Análisis de símbolos y resolución de nombres (`analysis/`)

## 1. Alcance y contrato

Esta fase **no verifica tipos**. Verifica **qué nombres existen, dónde viven, qué visibilidad tienen y a qué declaración apunta cada referencia**. El type checker (fase posterior) consume el resultado de esta fase; no lo reemplaza ni duplica su lógica.

**Entrada:** AST por archivo (salida de `frontend/`) + configuración del proyecto (`pengu.toml` o raíz por defecto).

**Salida:** un `AnnotatedProject` inmutable que contiene:

```python
@dataclass(frozen=True, slots=True)
class NodeId:
    path: Path
    span: Span  # Coordenadas exactas que identifican unívocamente al nodo AST

@dataclass(frozen=True, slots=True)
class AnnotatedProject:
    realms: dict[str, RealmSymbolTable]             # realm name → tabla de símbolos fusionada
    modules: dict[Path, AnnotatedModule]           # archivo → símbolos locales e imports resueltos
    references: dict[NodeId, Symbol]               # cada Ident/TypeExpr/SelfField/etc → su Symbol
    symbols_to_refs: dict[SymbolId, list[NodeId]]  # SymbolId → referencias (go-to-def, rename, find-refs)
    scopes: dict[NodeId, Scope]                    # cada nodo contenedor → su Scope activo
    diagnostics: list[Diagnostic]                  # errores E2xxx y warnings W2xxx ordenados por span
    symbol_types: dict[SymbolId, object] = field(default_factory=dict)  # reservado para el type checker
    const_values: dict[SymbolId, object] = field(default_factory=dict)  # valores evaluados de constantes
```

### Consumidores del contrato
1. **Type checker**: recorre el AST y, en cada `Ident` o nodo de tipo, consulta `project.references[node_id]` para obtener el `Symbol` correspondiente y determinar o verificar su tipo.
2. **Codegen**: usa `symbols_to_refs` y las tablas de realm para emitir forward declarations, namespaces C++ y directivas `#include` sin re-calcular dependencias.
3. **LSP**:
   - *Go-to-definition*: `references[node_id].id.span`.
   - *Find-references*: `symbols_to_refs[symbol.id]`.
   - *Rename*: reescribir todos los `NodeId.span` listados en `symbols_to_refs[symbol.id]`.
   - *Document outline / symbols*: árbol de símbolos de `modules[path]`.

---

## 2. Correcciones y adiciones al diseño original

Tras analizar la especificación en `docs/cheatsheet.md` y la arquitectura actual del compilador, se aplican las siguientes correcciones y adiciones críticas:

1. **Corrección de `ast.NodeVisitor` a `ASTVisitor` propio:**
   - La librería estándar `ast.NodeVisitor` de Python solo funciona para nodos de Python (`ast.AST`).
   - Los nodos de PenguScript (`src/penguscript/frontend/ast_nodes.py`) son `@dataclass(frozen=True, slots=True)`.
   - **Solución:** Implementar `analysis/visitor.py` con `ASTVisitor`, que recorre recursivamente los campos de los dataclasses y listas de nodos.

2. **Adición de `PreludeSymbolTable` (Tipos primitivos y built-ins):**
   - Si no existe un ámbito de tipos primitivos (`int`, `double`, `bool`, `string`, `void`, `vector`, `map`, etc.) y constantes (`none`, `nullptr`, `true`, `false`), la resolución de cualquier firma como `x: int` fallaría falsamente con `E2313` (tipo no encontrado).
   - **Solución:** Crear `analysis/prelude.py` con todos los símbolos incorporados del lenguaje. Toda resolución tiene el `prelude` como ámbito raíz.

3. **Distinción entre acceso estático (`::`) y dinámico (`.`):**
   - En PenguScript:
     - `::` es **estático** (a nivel de realm, tipo estático, variantes de enum): `math::sqrt`, `Color::Red`, `int::try_from`.
     - `.` es **dinámico** (campos y métodos de instancias): `point.x`, `point.distance()`.
     - `@` y `@field` acceden al estado del rune contenedor (`this` / `self`).
   - El analizador de símbolos valida estáticamente los accesos sobre `@`, `Type::...` y `realm::...`. Los accesos `expr.field` sobre variables locales no tipadas se delegan al type checker si la inferencia es requerida, pero se verifican aquí si el tipo de la variable fue anotado explícitamente (`p: Point`).

4. **Ampliación del catálogo de errores (`E2xxx` y `W2xxx`):**
   - Se añaden códigos para casos omitidos: ciclos de herencia (`E2221`), redeclaración en el mismo bloque (`E2317`), uso indebido de `::` sobre variables (`E2318`), uso indebido de `.` sobre realms (`E2319`), `break`/`continue` fuera de loop (`E2320`, `E2321`), parámetros duplicados (`E2219`), alias circulares (`E2220`) y auto-import (`E2008`).

---

## 3. Estructura de datos

### Símbolos (`analysis/symbols.py`)

```python
from enum import Enum, auto

class SymbolKind(Enum):
    FUNCTION = auto()
    CONST = auto()
    RUNE = auto()
    OMEN = auto()
    ECHO = auto()
    SEAL = auto()
    OPERATOR = auto()
    FREE_OPERATOR = auto()
    CONSTRUCTOR = auto()
    DESTRUCTOR = auto()
    METHOD = auto()
    FIELD = auto()         # solo en runas
    OMEN_VARIANT = auto()  # solo en omens
    PARAMETER = auto()     # solo en firmas de funciones
    LOCAL = auto()         # variables en bloques
    SIGIL = auto()         # parámetros de tipo genérico <T>
    BUILTIN_TYPE = auto()  # int, double, string, bool, void, etc.
    REALM_ALIAS = auto()   # alias de realm importado con invoke ... as ...

@dataclass(frozen=True, slots=True)
class SymbolId:
    module_path: Path
    span: Span             # span de la declaración (único por símbolo)

@dataclass(frozen=True, slots=True)
class Symbol:
    id: SymbolId
    name: str
    kind: SymbolKind
    realm: str | None                   # None para locales, parámetros y sigilos
    is_mut: bool = False                # asignado por `mut`
    is_unsafe: bool = False             # asignado por `unsafe`
    is_private: bool = False            # convención: nombre empieza por '_'
    sigils: tuple[str, ...] = ()        # parámetros genéricos (ej. <T, U>)
    decl_node_id: NodeId | None = None  # puntero al nodo declarativo (LSP hover)
```

### Tablas por Realm (`analysis/symbols.py`)

```python
@dataclass(frozen=True, slots=True)
class RealmSymbolTable:
    name: str
    symbols: Mapping[str, Symbol]                           # nombre top-level → Symbol
    rune_fields: Mapping[str, Mapping[str, Symbol]]         # rune → tabla de campos
    rune_methods: Mapping[str, Mapping[str, Symbol]]        # rune → tabla de métodos y operadores
    omen_variants: Mapping[str, Mapping[str, Symbol]]       # omen → variantes
    by_path: Mapping[Path, frozenset[str]]                  # archivo → símbolos que aporta
```

### Por archivo (`analysis/symbols.py`)

```python
@dataclass(frozen=True, slots=True)
class ResolvedImport:
    source_span: Span
    target_path: Path
    target_realm: str
    kind: Literal["plain", "selective"]
    local_alias: str | None                       # para `as alias`
    imported_symbols: Mapping[str, Symbol]        # símbolos importados selectivamente

@dataclass(frozen=True, slots=True)
class AnnotatedModule:
    path: Path
    declared_realm: str                           # explícito o implícito del nombre de archivo
    imports: tuple[ResolvedImport, ...]
    visible_realms: Mapping[str, str]             # nombre local / alias → nombre real del realm
    visible_symbols: Mapping[str, Symbol]         # símbolos directamente visibles sin prefijo
    local_symbols: Mapping[str, Symbol]           # símbolos declarados en este archivo
```

### Ámbitos (`Scope`)

```python
class ScopeKind(Enum):
    PRELUDE = auto()
    MODULE = auto()
    RUNE = auto()        # dentro de rune o enchanting
    FUNCTION = auto()    # parámetros y sigilos de función
    BLOCK = auto()       # bloque if/while/for/comprehension/unsafe

@dataclass(slots=True)
class Scope:
    kind: ScopeKind
    parent: Scope | None
    symbols: dict[str, Symbol] = field(default_factory=dict)
    owner_span: Span | None = None
    enclosing_rune: str | None = None    # nombre del rune si estamos en rune/enchanting
    in_loop: bool = False                # permite validar break/continue
    in_constructor: bool = False         # permite validar parent()
```

---

## 4. Pipeline de dos pases

```
[Archivos del Proyecto]
           │
           ▼
[Pase 1: Collector (por archivo)]
   • Extrae realm (explícito o implícito)
   • Registra declaraciones top-level crudas
   • Detecta colisiones intra-archivo (E21xx, E22xx)
           │
           ▼
[Grafo de Módulos e Imports]
   • Resuelve rutas físicas (std/ o proyecto)
   • Detecta ciclos de import (E2002) y auto-imports (E2008)
   • Ordenación topológica de módulos
           │
           ▼
[Fusión de Realms y Visibilidad]
   • Fusiona tablas de realms repartidas en múltiples archivos
   • Detecta colisiones cross-file en el mismo realm (E2201)
   • Construye tablas de visibilidad (visible_realms, visible_symbols)
           │
           ▼
[Pase 2: Resolver (por archivo)]
   • Pila de Scope (Prelude → Module/Realm → Rune → Function → Block)
   • Resuelve Ident, RealmAccess, EnumVariant, TypeStaticAccess, SelfField, etc.
   • Registra `references` y `symbols_to_refs`
   • Emite errores de resolución (E23xx)
           │
           ▼
[Scope Checks y Warnings]
   • Variables y parámetros no usados (W2301, W2302)
   • Imports no usados (W2303, W2304)
   • Accesos a miembros privados (W2305)
   • `mut` innecesario (W2306) y Shadowing (W2307)
           │
           ▼
[AnnotatedProject ensamblado y listo para Type Checker / LSP]
```

---

## 5. Catálogo completo de códigos de diagnóstico

### Imports y Módulos (`E20xx`)

| Código | Condición | Nota / Sugerencia |
|---|---|---|
| **E2001** | Archivo de módulo no encontrado en la ruta resuelta | Lista las rutas probadas (`foo.pengu`, `foo/index.pengu`) |
| **E2002** | Ciclo de dependencias entre imports detectado | Muestra la cadena circular con spans: `A -> B -> C -> A` |
| **E2003** | Símbolo no existe en el módulo importado selectivamente | Sugiere los 3 nombres más cercanos por Levenshtein |
| **E2004** | Ruta de import vacía (`invoke ""`) | — |
| **E2005** | Ruta de import relativa que escapa de la raíz del proyecto (`../../..`) | — |
| **E2006** | Alias de import colisiona con un símbolo o realm ya visible | Spans de ambas declaraciones |
| **E2007** | `invoke` declarado fuera del top-level del archivo | Los imports son exclusivamente de cabecera |
| **E2008** | Módulo se importa a sí mismo | — |

### Realms (`E21xx` y `W21xx`)

| Código | Condición |
|---|---|
| **E2101** | `realm` declarado después de sentencias ejecutables |
| **E2102** | Múltiples declaraciones de `realm` en un mismo archivo |
| **E2103** | Nombre de realm es una palabra clave reservada |
| **W2101** | El nombre de realm explícito no coincide con la convención de carpetas/archivo |

### Declaraciones y Tipos (`E22xx`)

| Código | Condición |
|---|---|
| **E2201** | Dos símbolos top-level con el mismo nombre en el mismo realm (mismo archivo o cross-file) |
| **E2202** | Campo duplicado en la definición de un `rune` |
| **E2203** | Variante duplicada en un `omen` |
| **E2204** | Método duplicado en bloque `enchanting` (mismo nombre) |
| **E2205** | Nombre de método colisiona con un campo del mismo rune |
| **E2206** | Múltiples constructores definidos en el mismo rune o su enchanting |
| **E2207** | Múltiples destructores definidos en el mismo rune o su enchanting |
| **E2208** | Operador sobrecargado duplicado con el mismo símbolo y aridad |
| **E2209** | Operador libre colisiona con operador de `enchanting` con idéntico primer parámetro |
| **E2210** | Parámetro sigilo genérico duplicado (`<T, T>`) |
| **E2211** | Sigilo genérico tiene el mismo nombre que el rune o función contenedor |
| **E2212** | Auto-herencia (`rune X heir X`) |
| **E2213** | El objetivo de `heir` no es un `rune` (ej. es un `omen` o alias) |
| **E2214** | `heir Animal` referencia a un rune genérico sin instanciar argumentos de tipo |
| **E2215** | Variante de `omen` estándar con valor asignado no entero |
| **E2216** | Variante de `flags omen` con valor que no es potencia de dos (`1, 2, 4, 8...`) |
| **E2217** | Bloque `enchanting` aplicado a un tipo no declarado en este realm ni importado |
| **E2218** | Bloque `enchanting` de tipo genérico no coincide en sigilos con su `rune` |
| **E2219** | Parámetro duplicado en la firma de una función (`(x: int, x: int)`) |
| **E2220** | Ciclo en alias de tipos (`echo A = B; echo B = A`) |
| **E2221** | Ciclo de herencia detectado (`rune A heir B; rune B heir A`) |

### Resolución de Nombres (`E23xx`)

| Código | Condición |
|---|---|
| **E2301** | Identificador no definido en el ámbito actual (sugiere top-3 por Levenshtein) |
| **E2302** | Prefijo de realm en `realm::name` no visible en este archivo |
| **E2303** | Símbolo `name` no encontrado en el realm visible `realm::name` |
| **E2304** | Acceso a campo `x.field` donde el objetivo no posee dicho campo (verificable estáticamente) |
| **E2305** | Llamada a método `x.method()` donde el objetivo no posee dicho método (verificable estáticamente) |
| **E2306** | Referencia `@` (self) utilizada fuera de método, constructor o destructor |
| **E2307** | `@field` no existe en los campos del rune contenedor |
| **E2308** | `@method()` no existe en los métodos del rune contenedor |
| **E2309** | Llamada `parent(...)` fuera de un constructor |
| **E2310** | Llamada `parent(...)` en constructor de rune sin cláusula `heir` |
| **E2311** | `parent(...)` no es la primera sentencia del constructor |
| **E2312** | Sigilo `T` usado en tipo sin haber sido declarado en parámetros genéricos |
| **E2313** | Tipo referenciado no existe (no está en realm, imports ni prelude) |
| **E2314** | Acceso miembro estático `Type::member` no soportado para este tipo |
| **E2315** | Uso de variable local antes de su declaración en el mismo bloque |
| **E2316** | `break value` con tipo inconsistente (**diferido formalmente al type checker**) |
| **E2317** | Redeclaración de variable con el mismo nombre en el mismo ámbito |
| **E2318** | Identificador de variable dinámica accedido con operador estático `::` |
| **E2319** | Realm accedido con operador dinámico `.` (sugiere `::`) |
| **E2320** | Sentencia `break` utilizada fuera de un bucle |
| **E2321** | Sentencia `continue` utilizada fuera de un bucle |

### Warnings (`W23xx`)

| Código | Condición |
|---|---|
| **W2301** | Variable local declarada y nunca utilizada |
| **W2302** | Parámetro formal no utilizado (excepto si comienza con `_`) |
| **W2303** | Realm importado con `invoke` que nunca es referenciado |
| **W2304** | Símbolo importado selectivamente que nunca es utilizado |
| **W2305** | Símbolo privado (`_nombre`) accedido desde fuera de su módulo de origen |
| **W2306** | Variable declarada con `mut` pero nunca reasignada ni mutada |
| **W2307** | Shadowing: variable local oculta un símbolo de un ámbito superior |
| **W2308** | Constante top-level que nunca es referenciada en el proyecto |

---

## 6. Fases de implementación detalladas

```
Sub-fase 1: Andamiaje de símbolos, ASTVisitor y Collector (Pase 1)
     ↓
Sub-fase 2: Grafo de módulos, imports y resolución de rutas
     ↓
Sub-fase 3: Fusión de realms y cálculo de visibilidad
     ↓
Sub-fase 4: Resolver (Pase 2: Scopes y resolución de referencias)
     ↓
Sub-fase 5: Scope checks y catálogo de warnings (W23xx)
     ↓
Sub-fase 6: Ensamblado, diagnósticos enriquecidos y CLI (`pengu check`)
     ↓
Sub-fase 7: Endurecimiento (Levenshtein, determinismo y benchmarks)
```

### Sub-fase 1 — Andamiaje de símbolos, `ASTVisitor` y `Collector` (Pase 1)
- **Archivos nuevos:**
  - `src/penguscript/analysis/visitor.py`: clase base `ASTVisitor` que navega los dataclasses `@dataclass(frozen=True, slots=True)` de `frontend/ast_nodes.py`.
  - `src/penguscript/analysis/symbols.py`: definiciones de `SymbolId`, `NodeId`, `SymbolKind`, `Symbol`, `ScopeKind`, `Scope`, `RealmSymbolTable`.
  - `src/penguscript/analysis/prelude.py`: `get_prelude_symbols()` registrando los tipos y constantes fundamentales (`int`, `double`, `string`, `bool`, `void`, `vector`, etc.).
  - `src/penguscript/analysis/collector.py`: `Collector(ASTVisitor)` que visita declaraciones top-level, construye la lista de símbolos crudos por archivo y emite `E2101-E2103`, `E2201-E2219` (locales al archivo).
- **Fixtures:** `tests/fixtures/symbols/collect/` (casos de omens, runes, enchanting, constantes, funciones).
- **Tests:** `tests/unit/analysis/test_collector.py`.

### Sub-fase 2 — Grafo de módulos, imports y rutas
- **Archivos nuevos:**
  - `src/penguscript/analysis/imports.py`:
    - `resolve_import_path(path_str, from_file, project_root) -> Path`.
    - `build_module_graph(modules, project_root) -> ModuleGraph`.
    - Detección de ciclos (algoritmo de coloración DFS), detección de auto-imports y ordenación topológica.
    - Emite `E2001, E2002, E2004, E2005, E2007, E2008`.
- **Fixtures:** `tests/fixtures/symbols/imports/` (proyectos multi-archivo válidos y con ciclos).
- **Tests:** `tests/unit/analysis/test_imports.py`.

### Sub-fase 3 — Fusión de realms y cálculo de visibilidad
- **Archivos nuevos:**
  - `src/penguscript/analysis/realms.py`:
    - `merge_realms(modules, graph) -> dict[str, RealmSymbolTable]`: fusiona símbolos del mismo realm repartidos en múltiples archivos. Emite `E2201` cross-file ante colisiones.
    - `compute_visibility(module, realms, graph) -> (visible_realms, visible_symbols)`. Emite `E2003` (símbolo selectivo inexistente) y `E2006` (colisión de alias).
- **Fixtures:** `tests/fixtures/symbols/realms/` (realms reabiertos, diamonds, selective imports).
- **Tests:** `tests/unit/analysis/test_realms.py`.

### Sub-fase 4 — `Resolver` (Pase 2: Ámbitos y referencias)
- **Archivos nuevos:**
  - `src/penguscript/analysis/resolver.py`:
    - `Resolver(ASTVisitor)`: maneja la pila de ámbitos `Scope`.
    - Resuelve `Ident`, `RealmAccess`, `EnumVariant`, `TypeStaticAccess`, `SelfField`, `SelfMethodCall`, `FieldAccess`, `TypeExpr`.
    - Valida `@` en métodos (`E2306, E2307, E2308`), `parent()` en constructores (`E2309, E2310, E2311`), tipos referenciados (`E2313`), sigilos (`E2312`) y operadores estáticos vs dinámicos (`E2318, E2319`).
    - Puebla `references: dict[NodeId, Symbol]` y `symbols_to_refs: dict[SymbolId, list[NodeId]]`.
- **Fixtures:** `tests/fixtures/symbols/resolve/` (cuerpos de funciones, métodos de runes, llamadas estáticas y locales).
- **Tests:** `tests/unit/analysis/test_resolver.py`.

### Sub-fase 5 — Scope checks y catálogo de warnings
- **Archivos nuevos:**
  - `src/penguscript/analysis/scope_checks.py`:
    - Inspecciona `references` y los símbolos declarados para detectar:
      - Variables no usadas (`W2301`) y parámetros no usados (`W2302`).
      - Imports de realm o selectivos no usados (`W2303, W2304`).
      - Violación de privacidad por convención `_private` (`W2305`).
      - Inmutabilidad efectiva (`W2306` para `mut` no mutado).
      - Shadowing (`W2307`) y constantes huérfanas (`W2308`).
    - Valida que `break` y `continue` ocurran estrictamente dentro de loops (`E2320, E2321`).
- **Tests:** `tests/unit/analysis/test_scope_checks.py`.

### Sub-fase 6 — Ensamblado, diagnósticos enriquecidos y CLI (`pengu check`)
- **Archivos modificados/creados:**
  - `src/penguscript/analysis/diagnostics.py`: integración de diagnósticos semánticos con labels secundarios, notas y sugerencias (`QuickFix` / `Suggestion`).
  - `src/penguscript/analysis/__init__.py`: función pública `analyze_project(project_root: Path) -> AnnotatedProject`.
  - `src/penguscript/cli.py`: comando `pengu check [PATH]` con renderizado estilizado de errores y código de salida 0 (limpio) o 1 (con errores).
- **Tests de integración:** `tests/integration/test_analyzer_pipeline.py`.

### Sub-fase 7 — Endurecimiento (Sugerencias Levenshtein, determinismo y benchmarks)
- **Archivos nuevos:**
  - `src/penguscript/analysis/suggestions.py`: cálculo de distancia Levenshtein adaptativo para sugerir nombres similares en `E2301`, `E2303`, `E2003`.
- **Pruebas de calidad:**
  - Cobertura completa del catálogo de códigos (test verificando que cada código `E2xxx` y `W2xxx` cuenta con prueba unitaria).
  - Test de determinismo: orden estable de diagnósticos por `(path, span.start_byte, code)`.
  - Benchmarks: análisis de proyectos medianos/grandes en menos de 500 ms.
  - Verificación total: `ruff check`, `ruff format --check`, `mypy --strict`.

---

## 7. Criterios de aceptación (Definition of Done)

1. **`AnnotatedProject` completo:** todas las referencias de identificadores resuelven a su símbolo correspondiente o reportan un error con código unívoco `E2xxx`.
2. **0 mutaciones en el AST:** el AST producido por `frontend/` permanece 100% inmutable (`frozen=True`).
3. **Consistencia con `cheatsheet.md`:** los ejemplos de realms reabiertos, imports selectivos, alias y acceso `@` analizan correctamente.
4. **Tooling y CI verde:**
   - `uv run pytest tests/` pasando al 100%.
   - `uv run ruff check src tests` limpio sin advertencias.
   - `uv run ruff format --check src tests` sin diferencias.
   - `uv run mypy` en modo estricto con 0 errores.
