# 🐧 Auditoría: `maybe` vs `result of` en PenguScript

> **Estado:** los hallazgos de esta auditoría se corrigieron en **3.0.1**
> (tipado de constructores, ownership/move, `or:` sobre `result`, hover,
> tamaños y documentación). Este documento se conserva como la auditoría
> original; las referencias de línea son las del árbol anterior al fix.

> **Fecha:** 23 de octubre de 2026  
> **Repositorio:** PenguScript (`VERSION` = `3.0.0`; la referencia del lenguaje aún declara `2.0.0`)  
> **Alcance:** semántica, codegen, runtime, biblioteca estándar, LSP y documentación  
> **Modo:** auditoría estática + sondas de compilación y de LSP. **No se modificó código ni documentación existente.**

---

## 🎯 Resumen ejecutivo

- ❌ **`maybe` y `result of` no son el mismo mecanismo.** `maybe T` responde “¿hay valor?”. `result of T to E` responde “¿funcionó? y, si no, por qué no?”. El segundo puede *emular* al primero, pero no al revés.
- ✅ **Recomendación: conservar ambos**, con una frontera explícita. Eliminar cualquiera de los dos empobrece el lenguaje y rompe la biblioteca estándar actual.
- ⚠️ **La sensación de “dos sistemas” es real, pero no viene del sistema de tipos:** viene de que la biblioteca estándar mezcla APIs `maybe`/`bool` con variantes `result`, de que `std.oracle` conserva tipos heredados `MaybeInt`/`ResultInt`, y de que la documentación/editor no explican bien los constructores de `result`.
- 🐞 **Se encontraron tres problemas serios:** confusión de tipos en `ok_of`/`err_of` (UB, no solo un error de estilo), doble free por un contrato de propiedad contradictorio, y fuga del *box* en `or:` sobre un `result` rvalue.
- 📝 **`result of` no está “sin documentar”, pero está mal documentado y es casi invisible:** su semántica aparece en §12 y en la decisión D5, pero los constructores `calling ok_of with …` / `calling err_of with …` solo se mencionan 2 veces en toda la referencia y no existen en el hover ni en las completions.

### 🧭 Veredicto en una frase

> **Quédate con los dos, pero ponles frontera: `maybe` para ausencia, `result` para fallo con causa. Lo que hay que arreglar no es el tipo, sino la superficie de API, el ownership, el hover y los ejemplos.**

---

## 📑 Índice

1. [Qué es cada cosa](#sec-1)
2. [¿Son lo mismo?](#sec-2)
3. [Qué hace realmente la biblioteca estándar](#sec-3)
4. [Decisión recomendada](#sec-4)
5. [Auditoría de documentación y editor](#sec-5)
6. [Bugs y fugas encontrados](#sec-6)
7. [Plan de acción propuesto](#sec-7)
8. [Anexo: evidencia y archivos revisados](#sec-8)

---

<a id="sec-1"></a>

## 1. 🧠 Qué es cada cosa

### 1.1 `maybe T` — “¿hay un valor?”

`maybe T` es un **opcional**: o contiene un `T`, o está vacío. No transporta una causa; la ausencia *es* toda la información.

```pengu
weave find_user with id as int into maybe string:
    if id == 1:
        return some "Admin"
    return maybe none

weave main into int:
    var user as maybe string is calling find_user with 1
    if user is present:
        calling spark.println with user.value
    let name as string is user or else "Guest"
    banish user
    return 0
```

| Aspecto | Detalle |
|---|---|
| Representación C | `PenguMaybe { bool is_present; void *value; }` — **16 bytes** en 64-bit |
| Construcción | `some expr`, `maybe none` |
| Inspección | `.is_present`, `is present`, `is not present`, `.value` |
| Fallo | No hay causa tipada; en un bloque `or:` el binding `error` es el string `"none"` |
| `Donum` | Sí: `donum (maybe T)` es `pengu_maybe_none()` (vacío, sin reservar) |
| Patrones | `as some` / `as none` en `judge … over` |
| Coste | Una caja de 16 bytes cuando hay valor; cero cuando es `none` |

**Ideal para:** búsquedas, campos opcionales, “encuentra la primera coincidencia”, `getenv`, `read_symlink`, `realpath`, valores de configuración que pueden faltar sin ser un error.

---

### 1.2 `result of T to E` — “¿qué falló?”

`result of T to E` es un **resultado tipado**: o es `ok` con un `T`, o es `err` con un `E`. El tipo `E` es la causa del fallo (normalmente un `omen`).

```pengu
import std.archivum
import std.spark

omen ConfigError:
    ConfigMissing
    ConfigUnreadable
    ConfigUnknown

weave read_config with path as string into result of string to ConfigError:
    # 'or:' sobre un maybe rvalue libera la caja y mueve el payload a 'text'.
    var text as string is (calling archivum.read_file with path) or:
        return calling err_of with ConfigError.ConfigMissing
    # 'ok_of' encajona una copia de 'text'; el result pasa a poseer el búfer.
    return calling ok_of with text

weave main into int:
    var r as result of string to ConfigError is calling read_config with "app.conf"
    if not r.is_ok:
        judge r.error:
            when ConfigError.ConfigMissing -> calling spark.eprintln with "falta el archivo"
            when ConfigError.ConfigUnreadable -> calling spark.eprintln with "sin permisos"
            else -> calling spark.eprintln with "otro error"
        banish r
        return 1
    calling spark.println with r.value
    banish r
    return 0
```

| Aspecto | Detalle |
|---|---|
| Representación C | `PenguResult { bool is_ok; void *ok_val; void *err_val; }` — **24 bytes** en 64-bit |
| Construcción | `calling ok_of with v` / `calling err_of with e` (intrínsecos del compilador) |
| Inspección | `.is_ok`, `.value` (lado ok), `.error` / `.err` (lado err) |
| Fallo | Causa tipada `E`; en `or:` el binding `error` tiene tipo `E` |
| `Donum` | **No** a propósito: `donum (result of int to string)` es `E0049` |
| Patrones | `as ok` / `as err` en `judge … over` |
| Coste | Una caja de 24 bytes; además, el payload activo se boxea con `pengu_sigil_alloc` |

**Ideal para:** E/S, red, parseo, decodificación, validación, FFI y cualquier operación donde quien llama necesita distinguir *por qué* falló.

> [!WARNING]
> `ok` y `err` **no son palabras clave ni constructores del lenguaje**. Para construir un valor nuevo, la gramática solo tiene `some` (y `maybe none`); para `result` los constructores son `calling ok_of with …` y `calling err_of with …`. La referencia del lenguaje dice `ok x` / `err x` en dos sitios, y eso **no compila** (ver [BUG-06](#bug-06)).

---

### 1.3 Tabla comparativa rápida

| Criterio | `maybe T` | `result of T to E` |
|---|---|---|
| Pregunta que responde | ¿hay valor? | ¿funcionó? ¿por qué no? |
| Información de fallo | Ninguna | Causa tipada `E` |
| Representación | 16 B, un puntero al payload | 24 B, dos punteros (solo uno activo) |
| Construcción | `some x` / `maybe none` | `calling ok_of with x` / `calling err_of with e` |
| Campo de éxito | `.value` | `.value` |
| Campo de fallo | — | `.error` / `.err` |
| `Donum` | Sí | No |
| `is present` | Sí | No (usar `.is_ok`) |
| `or:` binding `error` | `string` (`"none"`) | `E` |
| Patrón `judge` | `some` / `none` | `ok` / `err` |
| Uso típico | lookup / campo opcional | I/O / parseo / red / validación |

---

<a id="sec-2"></a>

## 2. ⚖️ ¿Son lo mismo?

### 2.1 Solapamiento real

Sí hay un solapamiento: ambos son contenedores que pueden estar “vacíos” y ambos se desenvuelven con `or else`, `or return`, `try` y `or:`. También ambos se pueden `banish`.

Pero el solapamiento es **de forma**, no de propósito:

```text
maybe T     ──►  presente(T)  |  ausente
result T E  ──►  ok(T)        |  err(E)
```

`maybe` no puede responder “¿por qué no hay valor?”. `result` sí. Esa es la diferencia que importa para diagnóstico, recuperación selectiva y API pública.

### 2.2 ¿Se puede simular uno con otro?

- **`result` puede simular `maybe`** usando un tipo de error trivial (`result of T to bool`, `result of T to string`, o un `omen` con una sola variante). Pero:
  - cuesta 24 B en vez de 16 B;
  - obliga a inventar un valor de error;
  - pierde `is present`, `some`, `none` y la ergonomía de los patrones `some`/`none`;
  - hace que “no encontrado” parezca un fallo, cuando muchas veces es un resultado normal.
- **`maybe` no puede simular `result`** sin codificar la causa en un `string` o en un enum externo, que es exactamente la deuda que `result` elimina.

> [!NOTE]
> `maybe` **no es un sistema de errores**. Es un opcional. El sistema de errores tipado es `result of T to E` + los `omen` de error. Llamar “dos sistemas de errores” a `maybe`/`result` mezcla dos conceptos distintos.

### 2.3 ¿Por qué no quedarse solo con `result`?

Porque `result` no es gratis:

- **Memoria:** 24 B frente a 16 B; y el payload activo siempre se boxea.
- **Ruido:** cada lookup opcional necesita un tipo de error y un valor de error.
- **Pérdida de expresividad:** `is present`, `some`, `none`, `judge … as some/none` desaparecen.
- **Compatibilidad:** 23 módulos de la std usan `maybe`; eliminar `maybe` rompe APIs públicas y el modelo de `null` seguro.
- **Filosofía:** el lenguaje ya decidió en D5 que la migración es aditiva; quitar `maybe` va en contra de esa decisión.

### 2.4 ¿Por qué no quedarse solo con `maybe`?

Porque `maybe` no transporta causa:

- Un `read_file` que devuelve `maybe none` no distingue “no existe” de “sin permisos” o “es un directorio”.
- Un parser que devuelve `maybe none` no puede decir “falta una coma en la línea 7”.
- Una API de red que devuelve `maybe none` obliga a inventar un canal lateral para el error.
- Los módulos que ya son `result` (`lingua`, `petitio`, `compressus`, `jsonrpc`, `ward`) tendrían que degradar su información o romper su API.

### 2.5 Conclusión de la comparación

> **No son intercambiables. Son complementarios.** La decisión correcta es mantener ambos y usarlos con una regla clara; la decisión incorrecta es eliminar uno para “simplificar”.

---

<a id="sec-3"></a>

## 3. 📚 Qué hace realmente la biblioteca estándar

La percepción de “Archivum usa `maybe` y Lingua usa `result`” es correcta, pero incompleta: **Archivum usa ambos** y hay módulos result-only y módulos maybe-only.

Conteo aproximado de firmas `weave … into …` por módulo (no cuenta métodos ni funciones internas). En total, **23 módulos usan `maybe`** y **11 usan `result`**; la tabla muestra los más relevantes para la decisión:

| Módulo | `maybe` | `result` | `bool` | Lectura |
|---|---:|---:|---:|---|
| `std.archivum` | 21 | 14 | 30 | **Ambos**: compatibilidad + variantes `*_result` |
| `std.oracle` | 35 | 10 | 24 | **Ambos** + tipos heredados `MaybeInt`/`ResultInt` |
| `std.json` | 14 | 7 | 16 | **Ambos** |
| `std.rites` | 23 | 1 | 14 | Mayoritariamente `maybe` |
| `std.cipher` | 59 | 2 | 16 | Mayoritariamente `maybe` |
| `std.ledger` | 27 | 0 | 6 | Solo `maybe` |
| `std.loom` | 19 | 0 | 14 | Solo `maybe` |
| `std.lingua` | 0 | 10 | 11 | **Solo `result`** |
| `std.petitio` | 0 | 23 | 21 | **Solo `result`** |
| `std.compressus` | 1 | 15 | 0 | Prácticamente solo `result` |
| `std.jsonrpc` | 0 | 7 | 4 | **Solo `result`** |
| `std.ward` | 0 | 7 | 0 | **Solo `result`** |

### 3.1 El problema no es que existan ambos: es que no hay una política visible

La referencia dice en D5:

> “El resto de la biblioteca estándar conserva `maybe`/`bool` hasta que cada módulo reciba el mismo tratamiento aditivo…”

Eso **ya no es cierto**: `lingua`, `petitio`, `jsonrpc` y `ward` son `result`-only; `compressus` es prácticamente `result`-only (1 `maybe` residual), y `archivum`, `oracle`, `json` y `regulus` son mixtos. La frase describe una migración que en la práctica ya ocurrió de forma desigual. Ver [BUG-08](#bug-08).

### 3.2 La “tercera capa”: `std.oracle`

`std.oracle` mantiene:

- la API nativa genérica (`some_of`, `unwrap_maybe`, `unwrap_result`, …);
- los métodos `maybe`/`result`;
- los tipos heredados `MaybeInt`, `MaybeFloat`, `MaybeString`, `ResultInt`, `ResultString`, marcados `@deprecated`.

Eso no es un tercer sistema de errores, pero **sí es una tercera superficie** que confunde: un usuario puede encontrar `unwrap_int` (solo int), `unwrap_maybe` (genérico) y `MaybeInt.unwrap` (heredado) haciendo cosas parecidas. La documentación de `oracle` lo aclara, pero la referencia del lenguaje no.

---

<a id="sec-4"></a>

## 4. ✅ Decisión recomendada

### 4.1 Regla de oro

| Situación | Usa | Ejemplo |
|---|---|---|
| La ausencia es normal y no hay causa que reportar | `maybe T` | buscar un usuario, leer una variable de entorno opcional, un campo que puede faltar |
| El fallo tiene causa accionable | `result of T to E` | leer un archivo, parsear JSON/UTF-8, una petición HTTP, validar |
| Solo interesa sí/no y no hay causa | `bool` | `exists`, `is_file`, `is_dir` |
| El fallo es un invariante roto del programa | `panic` / `assert` | índice fuera de rango, estado imposible |
| Hay que propagar un fallo sin manejarlo | `try` | `try calling validate with input` |

### 4.2 Política de API pública

1. **Una operación, un estilo principal.** No expongas `read_file` → `maybe` y `read_file_result` → `result` como si fueran equivalentes sin decir cuál es el preferido.
2. **Compatibilidad sí, ambigüedad no.** Si mantienes la variante antigua, márcala como *compatibilidad* en la doc (no necesariamente `@deprecated`, para no romper `--deny-deprecated`).
3. **`result` para lo que pueda fallar con causa.** Nuevas APIs de E/S, red, parseo y validación deben nacer como `result`.
4. **`maybe` para lo que pueda faltar sin causa.** No conviertas un lookup en `result` solo por “modernizar”.
5. **No uses `result of T to string` como cajón de sastre.** Define un `omen` de error por módulo (`IoError`, `JsonError`, `LinguaError`, `HttpError`, …).
6. **No uses `bool` para operaciones que pueden fallar con causa.** `bool` está bien para predicados; para write/delete, `result` da mejor diagnóstico.
7. **Documenta el ownership del payload.** “El result posee su payload” tiene que ser una regla visible, no un detalle de codegen (ver [BUG-02](#bug-02)).

### 4.3 Qué hacer con cada módulo

| Módulo | Recomendación |
|---|---|
| `std.archivum` | Mantener `*_result` como API preferida para código nuevo; conservar `maybe`/`bool` como compatibilidad documentada. No eliminar nada en 3.x. |
| `std.lingua` | **No añadir** variantes `maybe`: decodificar UTF-8 tiene causas y offsets; `result` es la elección correcta. |
| `std.petitio` | **No añadir** `maybe`: una petición HTTP siempre tiene causa de fallo. |
| `std.compressus` | **No añadir** `maybe`: corrupción/formato no son “ausencia”. |
| `std.jsonrpc` | **No añadir** `maybe`: errores de framing/parseo son causas. |
| `std.ward` | **No añadir** `maybe`: las aserciones devuelven `result` para describir el fallo. |
| `std.json` | Mantener ambos donde el “no encontrado” sea normal; usar `result` para parseo/validación. |
| `std.oracle` | Congelar la capa heredada; dirigir código nuevo a la API nativa genérica. No crear más `MaybeInt`/`ResultInt`. |
| Módulos `maybe`-only (`ledger`, `loom`, `cipher`, …) | No migrar en masa. Añadir `result` solo donde el usuario necesite distinguir causas; documentar el criterio. |

### 4.4 Si insistes en quedarte con uno solo

| Escenario | Consecuencia | ¿Recomendado? |
|---|---|---|
| Solo `maybe` | Pierdes causas tipadas; `lingua`/`petitio`/`compressus`/`jsonrpc`/`ward` tendrían que degradar su API; vuelven los `string` de error y los centinelas. | ❌ No |
| Solo `result` | Todo lookup necesita un tipo/valor de error; +8 B por contenedor y más ruido; pierdes `some`/`none`/`is present`; ruptura masiva de APIs. | ❌ No |
| Ambos con frontera | Mantienes expresividad y compatibilidad; el coste es disciplina de API y documentación. | ✅ Sí |

### 4.5 Lo que no haría

- ❌ Reservar `ok` y `err` como palabras clave ahora: rompería identificadores existentes (la propia gramática lo evita a propósito).
- ❌ Convertir `maybe` en un alias de `result` con error `void`/`string`: pierdes ergonomía y no resuelve nada.
- ❌ Eliminar `std.oracle` de golpe: es API congelada y hay código que la usa.
- ❌ Añadir `maybe` a `lingua` “por simetría”: sería una regresión de información.
- ❌ Usar `or:` sobre `result` rvalue como patrón recomendado hasta que se arregle el ownership ([BUG-03](#bug-03)).

---

<a id="sec-5"></a>

## 5. 📝 Auditoría de documentación y editor

### 5.1 Lo que ya está bien

- ✅ La decisión **D5** existe y es conceptualmente correcta: `maybe` para ausencia, `result` para causa ([LANGUAGE_Spanish.md:2705](LANGUAGE_Spanish.md#L2705)).
- ✅ §12 documenta `.is_present`, `.is_ok`, `.value`, `.error`/`.err`, `or else`, `or return`, `try` y bloques `or:` ([LANGUAGE_Spanish.md:2629](LANGUAGE_Spanish.md#L2629)).
- ✅ `std.archivum` tiene una nota de diseño muy buena: “Two answers per question” ([std/archivum.pengu:33](std/archivum.pengu#L33)).
- ✅ `docs/ORACLE_API.md` sí dice explícitamente que `ok_of`/`err_of` son intrínsecos del compilador ([docs/ORACLE_API.md:37](docs/ORACLE_API.md#L37)).
- ✅ `std.lingua` documenta muy bien que el `result` posee su payload y que no hay que hacer `banish` de la vista extraída ([std/lingua.pengu:38](std/lingua.pengu#L38)).
- ✅ Hay tests de fugas para `banish result`, `try` y `errdefer` ([tests/stdlib/memoria/test_leaks.py:112](tests/stdlib/memoria/test_leaks.py#L112)).

### 5.2 Los huecos

| Hueco | Evidencia | Impacto |
|---|---|---|
| No hay sección de constructores de `result` equivalente a §6.6 para `maybe` | Solo 2 menciones de `ok_of`/`err_of` en toda la referencia, ambas en §11.4 (`donum`) | El usuario no sabe cómo crear un `result` |
| `result of void` no está documentado | El idioma `return calling ok_of with 0` aparece en tests y en `lingua`, pero no en la referencia | El éxito de un `result of void` parece un truco |
| `to E` es opcional en la gramática, pero la referencia solo muestra `result of T to E` | [`pengu_grammar.py:358`](pengu_parser/pengu_grammar.py#L358) | Sintaxis no descubrible; el `E` por defecto es `error` → `const char*` |
| No se explica el ownership del payload al encajonar | §13.4 dice “no clonan… liberar el original es decisión tuya”, pero `banish m` libera el payload ([§13.6](LANGUAGE_Spanish.md#L2783)) | Doble free / UAF (ver BUG-02) |
| El hover no reconoce `maybe`, `result`, `some`, `none`, `ok_of`, `err_of` | [`hover.py:23-42`](pengu_lsp/hover.py#L23-L42), [`pengu_symbols.py:269-283`](pengu_parser/pengu_symbols.py#L269-L283) | El editor no explica nada, ni siquiera en `maybe T` |
| Las completions ofrecen `maybe` y `result of`, pero no `some`, `ok_of` ni `err_of` | [`completions.py:646-647`](pengu_lsp/completions.py#L646-L647) | El constructor no se descubre escribiendo |
| La documentación generada usa `ok(...)` / `err(...)` como si fueran sintaxis | [`docs/api/archivum.md:331`](docs/api/archivum.md#L331), [`docs/api/lingua.md:152`](docs/api/lingua.md#L152) | Ejemplos que no compilan |
| La referencia enseña `ok x` / `err x` | [`LANGUAGE_Spanish.md:2796`](LANGUAGE_Spanish.md#L2796), [`LANGUAGE_Spanish.md:2894`](LANGUAGE_Spanish.md#L2894) | Error de sintaxis garantizado |
| D5 afirma que “el resto” conserva `maybe`/`bool` | [`LANGUAGE_Spanish.md:2735`](LANGUAGE_Spanish.md#L2735) | Afirmación falsa desde que existen módulos result-dominantes |
| El bullet de `banish d` está partido | [`LANGUAGE_Spanish.md:2782-2786`](LANGUAGE_Spanish.md#L2782-L2786) | La frase “destructor que el rune declaró” queda huérfana |
| La cabecera dice 2.0.0 y “sincronizada con VERSION” | [`LANGUAGE_Spanish.md:3`](LANGUAGE_Spanish.md#L3), `VERSION` = `3.0.0` | Documentación desactualizada |

### 5.3 El caso `ok` / `err` vs `ok_of` / `err_of`

La gramática es deliberada:

```text
# pengu_parser/pengu_grammar.py, comentario en 'unary'
# NOTE: 'ok expr' / 'err expr' are deliberately NOT grammar keywords yet.
# 'ok' and 'err' are ordinary identifiers throughout the stdlib and the tests...
```

Pero la referencia dice:

```pengu
# LANGUAGE_Spanish.md:2796
- `some x`, `ok x`, `err x` encajonan la carga útil...
```

Y al compilar `return ok 1`:

```text
[E0004] Undefined identifier 'ok'
```

**Conclusión:** no es que falte documentar `ok x`; es que **`ok x` no existe**. Hay que unificar toda la documentación y los ejemplos a `calling ok_of with x` / `calling err_of with e`, o cambiar la gramática (no recomendado: rompería identificadores).

### 5.4 Hover: evidencia concreta

Sonda sobre un archivo real con `maybe` y `result`:

```text
hover 'maybe': None
hover 'result': None
hover 'some': None
hover 'none': None
hover 'ok_of': ... (resuelve un símbolo equivocado, no documentación)
hover 'err_of': None
```

Y `int`/`string` sí resuelven porque están en `SymbolTable._init_builtins`:

```text
hover 'int': type int as int (32 bits / 4 bytes)
hover 'string': type string as string (128 bits / 16 bytes)
```

`maybe` y `result` no están en `_init_builtins` ni en `KEYWORD_DOCS`, así que el hover cae a `None`. No es un problema de VS Code: es del servidor LSP.

### 5.5 D5 se quedó corta

La decisión D5 es buena, pero su párrafo final está desactualizado:

- Dice que “el resto de la biblioteca estándar conserva `maybe`/`bool` hasta que cada módulo reciba el mismo tratamiento aditivo”.
- La realidad: `lingua` (0 `maybe` / 10 `result`), `petitio` (0/23), `compressus` (1/15), `jsonrpc` (0/7), `ward` (0/7).
- También dice que la migración completa “se sigue como el item 4.4 del roadmap”; en `new_std_roadmap.md`, 4.4 es un “test rápido de coherencia”, no la migración de `result`. La referencia es ambigua o incorrecta.

No es un problema de diseño; es un problema de **verdad documental**. D5 debería incluir una matriz de estado por módulo y una regla de decisión, no una promesa de migración futura.

### 5.6 Ejemplos que filtran

Varios ejemplos de `std/json.pengu` usan `or:` sobre un `result`:

```pengu
# std/json.pengu:35 (comentario de documentación)
var second as JsonValue is (calling root.pointer with "/tags/1") or:
    return 1
defer banish second
```

En el caso de expresión (`calling root.pointer …` es rvalue), el *box* del `result` se pierde: el ejemplo enseña un patrón que filtra. Ver [BUG-03](#bug-03).

---

<a id="sec-6"></a>

## 6. 🐞 Bugs y fugas encontrados

### Resumen

| ID | Severidad | Tipo | Dónde |
|---|---|---|---|
| [BUG-01](#bug-01) | 🔴 Alta | Confusión de tipos / UB | `pengu_infer.py` |
| [BUG-02](#bug-02) | 🔴 Alta | Doble free / UAF | `exprs.py` + `runtime_helpers.py` + docs |
| [BUG-03](#bug-03) | 🟠 Media-alta | Fuga de memoria | `or_block.py` |
| [BUG-04](#bug-04) | 🟠 Media | UX / documentación | `hover.py` |
| [BUG-05](#bug-05) | 🟠 Media | Datos incorrectos | `pengu_types.py` |
| [BUG-06](#bug-06) | 🟡 Baja-media | Documentación incorrecta | `LANGUAGE*.md` |
| [BUG-07](#bug-07) | 🟡 Media | Documentación / UX | docs + LSP |
| [BUG-08](#bug-08) | 🟡 Baja | Documentación obsoleta | `LANGUAGE*.md` |
| [BUG-09](#bug-09) | 🟡 Baja | Formato / metadatos | `LANGUAGE*.md` |
| [BUG-10](#bug-10) | 🟡 Baja | Datos incorrectos | `pengu_types.py` |

---

<a id="bug-01"></a>

### 🔴 BUG-01 — `ok_of`/`err_of` no comprueban el tipo del payload

**Dónde:** [`pengu_parser/pengu_infer.py:4252-4253`](pengu_parser/pengu_infer.py#L4252-L4253)  
**Severidad:** 🔴 Alta — corrupción silenciosa / comportamiento indefinido.

`_infer_result_ctor` infiere el tipo del argumento, pero **nunca lo compara con el lado esperado del `result`**. Si el contexto es un `ResultType`, devuelve `expected_type` sin validar `inner_t`:

```python
inner_t = self.infer(arg_node, expected_type=exp_inner)
...
if isinstance(expected_type, ResultType):
    return expected_type          # ← no compara inner_t con exp_inner
```

El codegen, por su parte, boxea el tipo **real** del argumento:

```python
# pengu_parser/pengu_codegen/or_block.py:526-539
decl_tmp = CTypeMapper.to_c_decl(arg_t, tmp)
...
_result.ok_val = pengu_sigil_alloc(sizeof(tmp));
memcpy(_result.ok_val, &tmp, sizeof(tmp));
```

Resultado: el `result` declara un tipo, pero la caja contiene otro. Al leerlo se hace un cast al tipo declarado.

**Reproducción:**

```pengu
weave bad_ok into result of int to string:
    return calling ok_of with "not an int"

weave main into int:
    var r as result of int to string is calling bad_ok
    if r.is_ok:
        return r.value
    return 0
```

`pengu check` dice **“Clean no errors found”**. El C generado es:

```c
PenguString _res_val_1 = pengu_string_from_cstr("not an int");
_result_2.ok_val = pengu_sigil_alloc(sizeof(_res_val_1));
...
int32_t _ret_4 = (*(int32_t *)r.ok_val);   /* lee 4 bytes de un PenguString */
```

**Impacto:** un `result of int to string` puede contener un `PenguString` en `ok_val`; el consumidor lee los primeros 4 bytes del puntero como `int32_t`. Es UB silenciosa, no un error de compilación. Lo mismo pasa con `err_of` y con el `E` por defecto (`result of int`, donde `E` es `error` → `const char*`).

**Fix sugerido (no implementado):**

1. En `_infer_result_ctor`, si `exp_inner` no es `None`, comprobar `inner_t.is_compatible(exp_inner)`; si no, `E0005` con un mensaje que nombre el lado (`ok`/`err`).
2. Decidir explícitamente el caso `result of void`: hoy se acepta `ok_of with 0` porque no hay chequeo; si se arregla, o se permite un `ok_of` sin payload para `void`, o se documenta el `0` como dummy.
3. Añadir tests negativos:
   - `ok_of "x"` en `result of int to string` → `E0005`.
   - `err_of 42` en `result of int to string` → `E0005`.
   - `err_of "x"` en `result of int` (E por defecto) → `E0005`.
4. Añadir un test positivo para `result of void` con el constructor que se elija.

---

<a id="bug-02"></a>

### 🔴 BUG-02 — Doble free por un contrato de propiedad contradictorio

**Dónde:** [`pengu_parser/pengu_codegen/exprs.py:997-1006`](pengu_parser/pengu_codegen/exprs.py#L997-L1006), [`runtime_helpers.py:209-217`](pengu_parser/pengu_codegen/runtime_helpers.py#L209-L217), [`LANGUAGE_Spanish.md:2783`](LANGUAGE_Spanish.md#L2783), [`LANGUAGE_Spanish.md:2894`](LANGUAGE_Spanish.md#L2894)  
**Severidad:** 🔴 Alta — crash por doble free / posible UAF.

El codegen de `some` copia los bytes del payload con `memcpy`:

```c
PenguString _some_1 = s;
PenguMaybe _maybe_2;
_maybe_2.value = pengu_sigil_alloc(sizeof(_some_1));
memcpy(_maybe_2.value, &_some_1, sizeof(_some_1));
```

Es una copia **superficial**: `_some_1` y `s` comparten `data` y ambos tienen `is_owned == 1`. Después, `banish m` hace:

```c
if (m.is_present && m.value) {
  pengu_banish_string((PenguString *)(m.value));  /* libera el búfer compartido */
  free(m.value);
}
```

Si el usuario también hace `banish s`, se libera dos veces el mismo búfer.

**Reproducción:**

```pengu
weave main into int:
    var s as string is "{1}"          # string con dueño (heap)
    var m as maybe string is some s
    banish m
    banish s
    return 0
```

Resultado real:

```text
free(): double free detected in tcache 2
[PENGU CRASH] fatal signal (signal/code 6)
```

Lo mismo ocurre con `calling ok_of with s` y `calling err_of with s` (probado con `result of string to string` y `result of int to string`).

**Por qué es un bug de contrato, no solo “mal uso”:**

- §13.4 dice: “no duplican ningún búfer del heap… liberar el original sigue siendo decisión tuya”.
- §13.6 dice: “`banish m` (maybe/result): libera la carga que la caja posee y después la caja misma”.
- Las dos frases no pueden ser verdaderas a la vez para un payload con dueño. El compilador no avisa, y el caso con literales (`some "Admin"`) lo oculta porque `is_owned == 0`.
- El mismo problema aplica a `list`, `map` y runes con `Nexus`: `banish m` libera el búfer del contenedor, mientras el origen sigue apuntando a él.

**Impacto:** doble free, use-after-free y corrupción de heap en código que sigue literalmente la documentación de ownership.

**Opciones de fix (decisión de diseño, no implementada):**

| Opción | Qué implica | Coste |
|---|---|---|
| A. “Boxing transfiere propiedad” | Documentar que `some x` / `ok_of with x` / `err_of with x` mueven el payload; no usar ni `banish` el origen después. El compilador no puede verificar el move. | Cambio de docs + tests; sigue siendo fácil de romper |
| B. “Boxing pide prestado” | `banish` del contenedor no libera el payload; el dueño lo libera. Los `result` devueltos por funciones tendrían que transferir de otra forma. | Rompe el patrón actual de `archivum`/`lingua` |
| C. Clonado profundo al encajonar | `some`/`ok_of`/`err_of` clonan el payload (o usan `Nexus`/`Imago`); origen y caja son independientes. | Más asignaciones; cambia el contrato “sin clonado oculto” |

Recomendación: **A + documentación explícita + tests de doble free**, y evaluar C como opt-in (`some_clone`, `ok_of_clone`) si se necesita conservar el origen. Lo importante es que la regla sea única y visible.

---

<a id="bug-03"></a>

### 🟠 BUG-03 — `or:` sobre un `result` rvalue filtra el box y el payload de error

**Dónde:** [`pengu_parser/pengu_codegen/or_block.py:179-192`](pengu_parser/pengu_codegen/or_block.py#L179-L192)  
**Severidad:** 🟠 Media-alta — fuga de memoria por evaluación.

`_translate_or_block` solo marca `own_box` cuando el operando es `maybe`:

```python
own_box = (is_maybe and isinstance(own_box_op, Tree)
           and own_box_op.data in ("some_expr", "maybe_none", "calling_expr", ...))
```

Para `result`, `own_box` siempre es `False`, así que no se emite ningún `free` ni `banish` del contenedor temporal. El comentario del código lo justifica así:

> “a result box may belong to the C side, so it is left alone.”

Pero cuando el `result` viene de `ok_of`/`err_of` o de una función PenguScript, la caja es del programa y nadie la libera.

**Reproducción:**

```pengu
weave f into result of string to string:
    return calling ok_of with "x"

weave main into int:
    var s as string is (calling f) or:
        return 1
    banish s
    return 0
```

C generado (resumen):

```c
PenguResult _res_4 = (f());
PenguString s = (PenguString){0};
if (!pengu_result_is_ok(&_res_4)) {
  PenguString error = (*((PenguString *)_res_4.err_val));
  return 1;
} else {
  s = (*((PenguString *)_res_4.ok_val));
}
/* no hay free(_res_4.ok_val) ni banish del result */
```

En éxito se pierde el box de 24 B. En fallo se pierde además el payload de error (si `E` posee memoria, como `string` o un rune con `Nexus`).

**Workaround documentable:** enlazar el `result` a un local antes del `or:` y hacer `banish` después; aun así, el binding `error` es una vista prestada y no debe sobrevivir al bloque. Pero esto no arregla el caso rvalue, que es el que usan los ejemplos de `std/json`.

**Fix sugerido (no implementado):** decidir el ownership del `error` en `or:` sobre `result`:

- Si el bloque no puede quedarse con `error`, liberar payload + caja al salir, como hace `or else` con el error descartado.
- Si `error` puede escaparse, o se mueve a un valor propio, o se documenta que es prestado y que reencajonarlo requiere clonar.
- Añadir un test de fugas con `or:` sobre `ok_of`/`err_of` y sobre una llamada que devuelve `result`.

---

<a id="bug-04"></a>

### 🟠 BUG-04 — El hover no explica `maybe` ni `result` ni sus constructores

**Dónde:** [`pengu_lsp/hover.py:23-42`](pengu_lsp/hover.py#L23-L42), [`pengu_parser/pengu_symbols.py:269-283`](pengu_parser/pengu_symbols.py#L269-L283)  
**Severidad:** 🟠 Media — UX y descubribilidad.

`KEYWORD_DOCS` no contiene `maybe`, `result`, `some`, `none`, `ok_of` ni `err_of`. Los builtins de `SymbolTable` solo registran `int`, `i32`, `i64`, `float`, `f32`, `f64`, `bool`, `string`, `void`, `opaque`; `maybe` y `result` no están.

**Sonda real:**

```text
hover 'maybe': None
hover 'result': None
hover 'some': None
hover 'none': None
hover 'ok_of': (símbolo equivocado)
hover 'err_of': None
```

**Impacto:** el usuario no puede descubrir la semántica ni la sintaxis desde el editor. Es exactamente lo que reportaste. No es un fallo de VS Code: es el servidor LSP.

**Fix sugerido (no implementado):**

- Añadir documentación contextual para `maybe`, `result`, `some`, `none`, `ok_of`, `err_of` (y `or else`, `or return`, `try`, `or:` si se quiere completar).
- Resolver `result` solo cuando va seguido de `of` (porque `result` puede ser un identificador normal; `maybe` no).
- Añadir tests de hover para cada token.
- Añadir completions/snippets para `some`, `ok_of`, `err_of` y `result of void`.

---

<a id="bug-05"></a>

### 🟠 BUG-05 — El tamaño de `result` en el hover es incorrecto

**Dónde:** [`pengu_parser/pengu_types.py:2954-2957`](pengu_parser/pengu_types.py#L2954-L2957)  
**Severidad:** 🟠 Media — información incorrecta en el editor.

`estimate_size(ResultType)` calcula:

```python
ok_sz = estimate_size(t.ok_type, ...)
err_sz = estimate_size(t.err_type, ...)
return ok_sz + err_sz + 4
```

Pero `PenguResult` es una estructura de tamaño fijo: `bool` + padding + dos punteros = **24 bytes** en 64-bit, independientemente de `T` y `E`.

**Evidencia:**

```text
var ri as result of int to int       → hover: 96 bits / 12 bytes   (real: 24)
var rs as result of string to string → hover: 288 bits / 36 bytes  (real: 24)
```

`maybe` sí es correcto (16 bytes). El problema es solo `result`.

**Impacto:** el hover y la documentación que copia esa cifra dan tamaños falsos; en tipos con payloads grandes la diferencia es enorme.

**Fix sugerido (no implementado):** devolver `24` para `ResultType` (con el mismo criterio de alineación que `PenguResult`), y añadir un test que compare `estimate_size(ResultType(...))` con `sizeof(PenguResult)`.

---

<a id="bug-06"></a>

### 🟡 BUG-06 — La documentación enseña `ok x` / `err x`, que no compilan

**Dónde:** [`LANGUAGE_Spanish.md:2796`](LANGUAGE_Spanish.md#L2796), [`LANGUAGE_Spanish.md:2894`](LANGUAGE_Spanish.md#L2894), [`LANGUAGE.md:2813`](LANGUAGE.md#L2813), [`LANGUAGE.md:2887`](LANGUAGE.md#L2887)  
**Severidad:** 🟡 Baja-media — error de sintaxis garantizado para quien copie el ejemplo.

La gramática no produce `ok_expr`/`err_expr` (el comentario en [`pengu_grammar.py:465-472`](pengu_parser/pengu_grammar.py#L465-L472) lo explica), pero la referencia dice:

```pengu
- `some x`, `ok x`, `err x` encajonan la carga útil...
```

Al compilar:

```text
[E0004] Undefined identifier 'ok'
```

**Fix sugerido:** sustituir por `some x`, `calling ok_of with x`, `calling err_of with e` en la referencia inglesa y española; revisar también `CHEATSHEET.md` y las guías.

---

<a id="bug-07"></a>

### 🟡 BUG-07 — Los constructores de `result` no están documentados ni completados

**Dónde:** [`LANGUAGE_Spanish.md`](LANGUAGE_Spanish.md) (solo 2 menciones de `ok_of`/`err_of`), [`pengu_lsp/completions.py`](pengu_lsp/completions.py)  
**Severidad:** 🟡 Media — descubribilidad.

No hay una sección “Constructores de `result`” equivalente a §6.6 “Constructores de `maybe`”. Tampoco se documenta:

- `calling ok_of with v` / `calling err_of with e`;
- el caso `result of void` (`ok_of with 0`);
- el `to E` opcional y su `E` por defecto;
- que `E` puede ser cualquier tipo (normalmente un `omen`);
- que `ok_of`/`err_of` son intrínsecos, no funciones de `std.oracle`.

Las completions ofrecen `maybe` y `result of`, pero no `ok_of`/`err_of`; el usuario no puede descubrirlos escribiendo.

**Fix sugerido:** añadir una subsección a §12 con tabla de constructores, ejemplos válidos, `result of void`, `to E` opcional y ownership; añadir snippets al LSP; enlazar desde D5.

---

<a id="bug-08"></a>

### 🟡 BUG-08 — La decisión D5 afirma algo que la std ya no cumple

**Dónde:** [`LANGUAGE_Spanish.md:2735`](LANGUAGE_Spanish.md#L2735)  
**Severidad:** 🟡 Baja — documentación obsoleta.

D5 dice:

> “El resto de la biblioteca estándar conserva `maybe`/`bool` hasta que cada módulo reciba el mismo tratamiento aditivo…”

Pero `lingua`, `petitio`, `jsonrpc` y `ward` ya son `result`-only; `compressus` es prácticamente `result`-only; `archivum`, `oracle`, `json` y `regulus` son mixtos. La frase debería ser una **matriz de estado** y una **regla de decisión**, no una promesa de migración futura.

**Fix sugerido:** reescribir el párrafo final de D5 con la tabla de módulos y el criterio “ausencia vs causa”; eliminar la referencia ambigua al “item 4.4” o apuntar al documento correcto.

---

<a id="bug-09"></a>

### 🟡 BUG-09 — Bullet roto y versión desactualizada

**Dónde:** [`LANGUAGE_Spanish.md:2782-2786`](LANGUAGE_Spanish.md#L2782-L2786), [`LANGUAGE_Spanish.md:3`](LANGUAGE_Spanish.md#L3)  
**Severidad:** 🟡 Baja — formato / metadatos.

El bullet de `banish d` termina en “el” y la frase “destructor que el rune declaró (§9.1.2)” aparece después del bullet de `banish m`:

```markdown
- `banish d` (...): emite `_pengu_cleanup_D(&d)`, el
- `banish m` (...): libera la carga...
  `banish` que tú escribiste.
  destructor que el rune declaró (§9.1.2).
```

Además, la cabecera dice “Versión cubierta: 2.0.0 (sincronizada con `VERSION`…)”, pero `VERSION` es `3.0.0`. La referencia inglesa tiene el mismo problema.

**Fix sugerido:** recomponer el bullet y actualizar la versión (o quitar la promesa de sincronización si se decide documentar una versión anterior).

---

<a id="bug-10"></a>

### 🟡 BUG-10 — Colateral: los tamaños de `list` y `map` también están obsoletos

**Dónde:** [`pengu_parser/pengu_types.py:2945-2949`](pengu_parser/pengu_types.py#L2945-L2949)  
**Severidad:** 🟡 Baja — fuera del alcance estricto, pero en el mismo estimador.

`estimate_size(ListType)` devuelve **40** y `estimate_size(MapType)` devuelve **64**, con comentarios que describen la ABI v1 (callbacks `cleanup`/`clone`). La ABI v2 real es:

- `PenguList { void *data; int len; int cap; size_t elem_size; }` → **24 bytes**.
- `PenguMap { PenguMapEntry *entries; int len; int cap; size_t key_size; size_t val_size; }` → **32 bytes**.

No afecta a `maybe`/`result`, pero el hover muestra tamaños incorrectos para listas y mapas por la misma razón que BUG-05. Conviene arreglarlo en el mismo pase.

---

<a id="sec-7"></a>

## 7. 🗺️ Plan de acción propuesto

> **Recordatorio:** esta auditoría no implementa nada. El plan es para que decidas qué hacer después.

| Prioridad | Acción | Criterio de aceptación |
|---|---|---|
| 🔴 P0 | Corregir la comprobación de tipos de `ok_of`/`err_of` | `ok_of "x"` en `result of int to string` → `E0005`; `err_of 42` → `E0005`; test positivo para `result of void` |
| 🔴 P0 | Definir y documentar el contrato de propiedad al encajonar | Un test de doble free falla o está prohibido por diseño; docs de §13.4/§13.6 coinciden |
| 🟠 P1 | Arreglar `or:` sobre `result` rvalue | Test de fugas (ASan/valgrind o contador) sin pérdida de box/payload |
| 🟠 P1 | Añadir hover de `maybe`, `result`, `some`, `none`, `ok_of`, `err_of` | Tests LSP que devuelven texto no vacío para cada token |
| 🟠 P1 | Reescribir la documentación de constructores de `result` | §12 tiene constructores, `result of void`, `to E` opcional y ownership |
| 🟠 P2 | Corregir `estimate_size(ResultType)` y la fórmula del cheatsheet | `result of int to int` muestra 24 bytes; test contra `sizeof(PenguResult)` |
| 🟡 P2 | Corregir `ok x`/`err x` y `ok(...)`/`err(...)` en docs | `grep` no encuentra esas formas en contextos de código |
| 🟡 P2 | Actualizar D5 con la matriz de módulos | D5 refleja `lingua`/`petitio`/`jsonrpc`/`ward` result-only y `compressus` casi result-only |
| 🟡 P3 | Completions de `some`/`ok_of`/`err_of` | El usuario puede insertar los constructores desde el editor |
| 🟡 P3 | Arreglar bullet roto y versión de la referencia | Cabecera coherente con `VERSION`; bullet completo |
| 🟡 P3 | Revisar tamaños de `list`/`map` en el estimador | Hover coincide con `PenguList`/`PenguMap` de la ABI v2 |

---

<a id="sec-8"></a>

## 8. 📎 Anexo: evidencia y archivos revisados

### 8.1 Archivos principales

| Archivo | Qué se revisó |
|---|---|
| [`LANGUAGE_Spanish.md`](LANGUAGE_Spanish.md) | §4.2, §6.6, §11.4, §12, §13.4–§13.6, D5, API de std |
| [`LANGUAGE.md`](LANGUAGE.md) | Mismas secciones en la versión canónica |
| [`CHEATSHEET.md`](CHEATSHEET.md) | §4.1, §11.2, §11.3, tamaños |
| [`pengu_parser/pengu_grammar.py`](pengu_parser/pengu_grammar.py) | `some`, `maybe none`, `result_type`, comentario sobre `ok`/`err` |
| [`pengu_parser/pengu_infer.py`](pengu_parser/pengu_infer.py) | `_infer_result_ctor`, `some_expr`, `maybe_none` |
| [`pengu_parser/pengu_codegen/or_block.py`](pengu_parser/pengu_codegen/or_block.py) | `or:`, `or else`, `or return`, `try`, `ok_of`/`err_of` |
| [`pengu_parser/pengu_codegen/exprs.py`](pengu_parser/pengu_codegen/exprs.py) | `some`, `banish`, `ok`/`err` lowering |
| [`pengu_parser/pengu_codegen/runtime_helpers.py`](pengu_parser/pengu_codegen/runtime_helpers.py) | `_banish_wrapper_stmts`, `_release_payload_stmts` |
| [`pengu_parser/pengu_types.py`](pengu_parser/pengu_types.py) | `MaybeType`, `ResultType`, `estimate_size` |
| [`pengu_runtime.h`](pengu_runtime.h) | `PenguMaybe`, `PenguResult`, `pengu_banish_maybe`, `pengu_banish_result` |
| [`pengu_lsp/hover.py`](pengu_lsp/hover.py) | `KEYWORD_DOCS`, resolución de tipos |
| [`pengu_lsp/completions.py`](pengu_lsp/completions.py) | `BASE_TYPES`, snippets |
| [`pengu_parser/pengu_symbols.py`](pengu_parser/pengu_symbols.py) | builtins |
| [`std/archivum.pengu`](std/archivum.pengu) | APIs `maybe`/`bool` + `*_result`, nota de diseño |
| [`std/lingua.pengu`](std/lingua.pengu) | API result-only, ownership |
| [`std/oracle.pengu`](std/oracle.pengu) | API nativa + capa heredada |
| [`std/json.pengu`](std/json.pengu) | ejemplos con `or:` sobre `result` |
| [`docs/api/archivum.md`](docs/api/archivum.md), [`docs/api/lingua.md`](docs/api/lingua.md) | ejemplos `ok(...)`/`err(...)` |
| [`docs/ORACLE_API.md`](docs/ORACLE_API.md) | nota de intrínsecos |

### 8.2 Sondas usadas

```bash
# 1. Comprobación de tipos de ok_of/err_of
.venv/bin/python pengu_project.py check /tmp/pengu_audit/typeconf.pengu --no-color
# -> Clean no errors found

# 2. C generado
.venv/bin/python pengu_project.py expand /tmp/pengu_audit/typeconf.pengu
# -> ok_val contiene PenguString; el consumidor lo lee como int32_t

# 3. Doble free
.venv/bin/python pengu_project.py run /tmp/pengu_audit/double_free_some.pengu --no-color
# -> free(): double free detected in tcache 2

# 4. Fuga en or: sobre result rvalue
.venv/bin/python pengu_project.py expand /tmp/pengu_audit/or_result.pengu
# -> no hay free del box ni del payload de error

# 5. Hover
.venv/bin/python /tmp/pengu_audit/hover_probe.py
# -> hover 'maybe': None ... hover 'result': None

# 6. Tamaños
.venv/bin/python /tmp/pengu_audit/hover_size.py
# -> result of int to int (12 bytes), result of string to string (36 bytes)
```

### 8.3 Conteo de la std

El conteo de la tabla §3 se hizo con:

```bash
for f in std/*.pengu; do
  m=$(grep -cE '^\s*weave .* into maybe' "$f")
  r=$(grep -cE '^\s*weave .* into result' "$f")
  b=$(grep -cE '^\s*weave .* into bool' "$f")
  ...
done
```

Es una aproximación de firmas `weave`; no cuenta métodos `enchanting`, funciones internas ni `declare`. Sirve para mostrar la distribución, no como métrica exacta de API pública.

### 8.4 Glosario mínimo

| Término | Significado en esta auditoría |
|---|---|
| **Box / caja** | La asignación de `pengu_sigil_alloc` que guarda el payload de un `maybe`/`result`. |
| **Payload** | El valor `T` (o `E`) que vive dentro de la caja. |
| **Ownership** | Quién es responsable de liberar el payload; en PenguScript es manual. |
| **Rvalue** | Expresión sin ubicación propia (una llamada, `some x`, `ok_of with x`). Su caja no tiene dueño después de la expresión. |
| **Lvalue** | Variable, campo o elemento con ubicación propia; su caja la posee el programa. |
| **Result-only** | Módulo cuyas operaciones falibles devuelven `result` como contenedor principal, sin variantes `maybe` equivalentes. |

---

## 🏁 Cierre

**No hay que elegir entre `maybe` y `result of`.** Son dos herramientas distintas y ambas están ya en la std. Lo que sí hay que elegir es una **política de API** y arreglar los bugs que hacen que la frontera sea peligrosa:

1. `maybe` para ausencia; `result` para fallo con causa.
2. `result` para código nuevo con causas; `maybe` para lookups y campos opcionales.
3. Una sola forma documentada de construir `result`: `calling ok_of with …` / `calling err_of with e`.
4. Un contrato de ownership explícito y probado.
5. Hover y completions que enseñen todo esto sin obligar a leer 300 KB de referencia.

> **Lo más urgente no es la decisión de diseño —esa ya está bien en D5—, sino los tres bugs de memoria y la documentación que enseña sintaxis que no compila.**

---

*Auditoría realizada sin modificar el código ni la documentación del proyecto. Los ejemplos de reproducción viven fuera del repositorio, en `/tmp/pengu_audit/`.*
