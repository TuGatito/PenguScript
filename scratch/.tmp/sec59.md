<a id="sec-59-estilo"></a>
## 59. Guía de estilo

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 9 |
| Rust | `rustfmt`, `clippy` |
| Palabras mágicas | `pengu fmt`, `pengu lint` |
| Depende de | §2, §15, §31, §56, §58 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec59_style.pengu` |

El estilo no es cosmético: hace que el código se lea como magia clara, no como
ruido. Las reglas de esta sección son verificables por el formatter y el linter.

### 59.1 Principios

1. La claridad gana a la brevedad.
2. La indentación reemplaza llaves; no se mezcla con `{}` de bloque.
3. Una línea expresa una idea.
4. Los nombres dicen qué, no cómo.
5. La magia se concentra en las palabras clave; el resto es familiar.
6. El código se escribe una vez y se lee muchas.
7. El formatter decide el espacio; el autor decide la estructura.
8. Un `@@allow` necesita una razón.

### 59.2 Nombres

| Elemento | Convención | Ejemplo |
|---|---|---|
| Tome/paquete | `kebab-case` | `pengu-http` |
| Crate | `snake_case` | `pengu_http` |
| Módulo (`scroll`) | `snake_case` | `scroll geometry` |
| Tipo (`rune`/`enchanting`) | `PascalCase` | `rune Point` |
| Variante de enum | `PascalCase` | `Circle` |
| Función | `snake_case` | `compute_area` |
| Binding (`bind`/`morph`) | `snake_case` | `bind user_count` |
| Constante (`sigil`) | `UPPER_SNAKE` | `sigil MAX_SIZE` |
| Static (`relic`) | `UPPER_SNAKE` | `relic REGISTRY` |
| Tipo genérico | `T`, `K`, `V`, `E` | `rune Map[K, V]` |
| Lifetime | `'a`, `'de`, `'src` | `&'a Str` |
| Archivo | `snake_case.pengu` | `http_client.pengu` |
| Test | `behavior_condition` | `add_returns_sum` |

1. Los tipos son sustantivos; las funciones son verbos.
2. Un booleano empieza con `is_`, `has_`, `can_` o `should_`.
3. Una función que muta empieza con un verbo (`push`, `clear`, `update`).
4. Una función pura no lleva `get_`; se llama por lo que calcula.
5. Evita abreviaturas salvo `id`, `url`, `http`, `api`.
6. No uses `I`/`l`/`O` como nombres de una letra.
7. Los nombres mágicos (`rune`, `pact`, `curse`) van en minúscula.

### 59.3 Archivos y módulos

1. Un archivo = un módulo.
2. El nombre del archivo usa `snake_case`.
3. `scroll` no se usa para un archivo que ya es módulo.
4. Un módulo pequeño puede vivir inline; uno grande, en archivo.
5. `mod.pengu` es el módulo de `mod/`.
6. Los tests unitarios van al final del archivo.
7. Los ejemplos van en `examples/`, no en `src/`.

### 59.4 Indentación y líneas

1. 4 espacios por nivel.
2. Tabs prohibidos, incluso en strings multilínea.
3. Ancho máximo: 100 columnas.
4. Una declaración por línea.
5. Sin punto y coma al final.
6. Sin espacios al final de línea.
7. El archivo termina con un newline.
8. Dos líneas en blanco entre items de nivel superior.
9. Una línea en blanco entre métodos de un `ritual`.
10. Una línea en blanco antes de un comentario de bloque.

```pengu
-- bien
rune Point
    x: Float
    y: Float

    length = (@) -> Float
        (x * x + y * y).sqrt()

-- mal: dos declaraciones en una línea
rune Point2
    x: Float; y: Float
```

### 59.5 Espacios

1. Un espacio alrededor de operadores binarios: `a + b`.
2. Sin espacio antes de `(` en llamadas: `add(1, 2)`.
3. Sin espacio dentro de `[]`/`()`/`{}` inline: `[1, 2]`.
4. Un espacio después de `,` y `:` en mapas: `{name: "pengu"}`.
5. Sin espacio antes de `:` en un tipo: `x: Int`.
6. Un espacio después de `then`/`else`: `if x then 1 else 0`.
7. Sin espacio antes de `?`/`!`: `value?`, `!flag`.
8. `->` y `=>` llevan un espacio a cada lado.

### 59.6 Imports

```pengu
summon std::fmt
summon std::collections::HashMap
summon serde::Serialize
summon crate::geometry::Point
```

1. Orden: `std`, externos, `crate`, `super`, `self`.
2. Dentro de cada grupo, orden alfabético.
3. Un `summon` por línea; el formatter no agrupa.
4. `summon path::*` solo en tests o preludio.
5. Alias solo para colisión: `summon crate::a::Point as PointA`.
6. No importes lo que no usas; `PGS-L103`.
7. Los imports van al inicio del módulo, después de `--!`.

### 59.7 Funciones y expresiones

1. Prefiere el cuerpo de expresión; evita `return` al final.
2. Una función hace una cosa.
3. Máximo orientativo: 40 líneas; si es más, extrae.
4. Los parámetros son explícitos; no hay defaults ni varargs.
5. El tipo de retorno es obligatorio en funciones nombradas.
6. Usa `if`/`match` como expresión cuando devuelven un valor.
7. Evita anidar más de 3 niveles; extrae o usa `match`.
8. Un `match` cubre todos los casos o tiene `else`.

```pengu
-- bien
classify = (n: Int) -> Str
    if n < 0 then "negative"
    elseif n == 0 then "zero"
    else "positive"

-- mal: return redundante
classify2 = (n: Int) -> Str
    if n < 0 then
        return "negative"
    else
        return "positive"
```

### 59.8 Condicionales y bucles

1. `if`/`elseif`/`else` en líneas separadas; `then` en la misma línea.
2. `unless` para una negación simple; no para `elseif`.
3. No uses `if cond then true else false`; usa `cond`.
4. `for` para iterar; `while` para condición; `loop` para repetir hasta `break`.
5. Un `loop` debe tener una salida clara.
6. No uses `break`/`continue` para flujo complejo; extrae.
7. Las etiquetas se usan solo para bucles anidados.

### 59.9 Errores

1. Usa `?` para propagar; no envuelvas manualmente.
2. `expect("contexto")` cuando la ausencia es un bug.
3. `unwrap()` solo en tests, ejemplos y prototipos.
4. `panic` solo para invariantes imposibles.
5. Un error de dominio se modela con `enchanting`.
6. No uses `String` como error si hay un tipo.
7. Un mensaje de error dice qué falló y qué hacer.

```pengu
read_config = (path: Str) -> !Config
    bind text = std::fs::read_to_string(path)?
    bind config = parse_config(&text)?
    ok(config)
```

### 59.10 Unsafe

1. Todo `curse` tiene un comentario `-- SAFETY:`.
2. La superficie unsafe es mínima; envuelve en una API segura.
3. No uses `transmute` si `as`/`From` sirve.
4. No uses `static mut`; usa `@@shared`.
5. Un `curse` no se propaga a toda la función si no hace falta.
6. Los invariantes se documentan en el `---` del item.
7. `PGS-L301` exige el comentario.

```pengu
curse read_u32 = (ptr: *const U32) -> U32
    -- SAFETY: el llamador garantiza alineación y validez.
    *ptr
```

### 59.11 Comentarios

1. `--` explica el porqué, no el qué.
2. `---` documenta la API; `--!` documenta el módulo.
3. No comentes código obvio.
4. Un TODO lleva dueño: `-- TODO(ana): ...`.
5. No dejes código comentado; usa git.
6. Un comentario de bloque empieza con mayúscula y termina con punto.
7. Los comentarios no se alinean con espacios.

```pengu
-- Reintentamos porque el servicio tiene un límite de 3 req/s.
```

### 59.12 Tests

1. El nombre describe el comportamiento: `parse_empty_returns_none`.
2. Un test prueba una cosa.
3. Estructura arrange-act-assert.
4. Sin `sleep`; usa relojes inyectables.
5. Sin dependencia de orden ni de red.
6. Los casos límite son explícitos.
7. Un test que falla debe decir qué esperaba.

### 59.13 Documentación

1. Todo item `unveil` tiene `---`.
2. El resumen cabe en una línea.
3. Los ejemplos son ejecutables.
4. Los enlaces intra-doc son relativos al crate.
5. `@@deprecated` dice el reemplazo.
6. No documentes la implementación; documenta el contrato.
7. `--!` describe el módulo, no la historia.

### 59.14 Interop con Rust

1. Prefiere `foreign` para FFI; usa el bloque `rust` solo si no hay otra opción.
2. Un bloque `rust` lleva un comentario de justificación.
3. No uses `#[allow]` global; usa `@@allow` local.
4. Los tipos `extern "C"` son `@@repr(C)`.
5. No expongas `std` en una API `no_std`.
6. Los nombres de Rust se mapean a `snake_case`.
7. `PGS-L502` avisa de cada bloque `rust`.

### 59.15 Lints y excepciones

1. `pengu lint` debe pasar sin warnings en CI.
2. `@@allow` va en el item más pequeño posible.
3. Un `@@allow` lleva un comentario con la razón.
4. No se usa `@@allow` para silenciar un bug.
5. Los lints de seguridad no se desactivan globalmente.
6. Los lints nuevos se documentan en §58.
7. Un `@@allow` sin razón es `PGS-L503`.

### 59.16 Formato de ejemplo

```rust
fn mean(values: &[f64]) -> f64 {
    let sum: f64 = values.iter().sum();
    sum / values.len() as f64
}

fn main() {
    let data = [1.0, 2.0, 3.0];
    println!("{:.1}", mean(&data));
}
```

1. El Rust generado sigue `rustfmt`.
2. No se edita a mano `target/pengu/`.
3. El formatter de PenguScript no cambia la semántica.
4. `pengu fmt --check` se ejecuta en CI.
5. Un diff de formato se revisa como cualquier cambio.

### 59.17 Diagnósticos de estilo

| Código | Situación | Solución |
|---|---|---|
| `PGS-L201` | shadowing innecesario | renombrar |
| `PGS-L202` | número mágico | `sigil` |
| `PGS-L203` | función larga | extraer |
| `PGS-L301` | `curse` sin `-- SAFETY:` | añadir razón |
| `PGS-L401` | item público sin docs | añadir `---` |
| `PGS-L501` | colisión de léxico | renombrar |
| `PGS-L502` | bloque `rust` | justificar |
| `PGS-L503` | `@@allow` sin razón | añadir comentario |

### 59.18 Criterios de aceptación

- [x] Nombres, archivos e indentación están definidos.
- [x] Espacios, imports y expresiones son verificables.
- [x] Errores, unsafe y comentarios tienen reglas.
- [x] Tests y documentación tienen guía.
- [x] La interop con Rust está limitada.
- [x] El ejemplo Rust compila.

[↑ Volver al índice](#indice)
