<a id="sec-57-documentacion"></a>
## 57. Documentación

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 9 |
| Rust | `///`, `//!`, `#[doc = "..."]`, `#[must_use]`, `#[deprecated]` |
| Palabras mágicas | `---`, `--!`, `@@doc`, `@@must_use`, `@@deprecated` |
| Depende de | §3, §42, §56 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec57_docs.pengu` |

La documentación es parte del código. Los comentarios `---` y `--!` generan
`rustdoc`; los bloques `pengu` se ejecutan como doc tests.

### 57.1 Comentarios de documentación

```pengu
--- Suma dos enteros.
---
--- # Ejemplos
---
--- ```pengu
--- add(2, 3) -- 5
--- ```
unveil add = (a: Int, b: Int) -> Int
    a + b
```

Rust generado:

```rust
/// Suma dos enteros.
///
/// # Ejemplos
///
/// ```pengu
/// add(2, 3) // 5
/// ```
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

1. `---` documenta el item que sigue.
2. `--!` documenta el módulo/crate que lo contiene.
3. `---` y `--!` son comentarios; el compilador no los parsea como código.
4. El contenido es Markdown, no PenguScript.
5. La primera línea es el resumen; el resto es el cuerpo.
6. Una línea vacía separa párrafos (`---` sola).
7. Los comentarios `--` normales no se publican.
8. `---` no se usa dentro de una función; para eso hay `--`.

### 57.2 Documentación interna

```pengu
--! # `math`
--!
--! Utilidades numéricas puras.
--!
--! Este módulo no hace I/O.

scroll math
    --- Constante de Euler.
    unveil E = 2.718281828459045
```

Rust generado:

```rust
//! # `math`
//!
//! Utilidades numéricas puras.
//!
//! Este módulo no hace I/O.

pub mod math {
    /// Constante de Euler.
    pub const E: f64 = 2.718281828459045;
}
```

1. `--!` debe estar al inicio del archivo o del `scroll`.
2. Solo hay un bloque `--!` por módulo.
3. `--!` describe el crate si está en `lib.pengu`/`main.pengu`.
4. Los `---` internos documentan items.
5. `--!` no se repite después de un item.
6. El README del crate se genera desde `--!`.
7. `--!` no genera un doc test por sí solo.

### 57.3 Markdown permitido

| Elemento | Sintaxis | Rustdoc |
|---|---|---|
| Encabezado | `# Título` | `<h1>` |
| Párrafo | texto | `<p>` |
| Lista | `- item` | `<ul>` |
| Lista numerada | `1. item` | `<ol>` |
| Código inline | `` `code` `` | `<code>` |
| Bloque | ` ```pengu ` | `<pre>` |
| Énfasis | `*texto*` | `<em>` |
| Fuerte | `**texto**` | `<strong>` |
| Enlace | `[texto](url)` | `<a>` |
| Imagen | `![alt](url)` | `<img>` |
| Tabla | `| a | b |` | tabla HTML |
| Cita | `> texto` | `<blockquote>` |

1. Se permite el subconjunto CommonMark.
2. No se permite HTML crudo; se escapa.
3. Los enlaces externos llevan `https://`.
4. Las imágenes deben tener `alt`.
5. Las tablas necesitan encabezado y separador.
6. Los bloques de código declaran lenguaje (`pengu`, `rust`, `text`, `toml`).
7. Un bloque sin lenguaje se trata como `text`.

### 57.4 Enlaces intra-doc

```pengu
--- Un punto en el plano.
---
--- Se usa en [`Shape`] y en [`area`].
rune Point
    x: Float
    y: Float
```

Rust generado:

```rust
/// Un punto en el plano.
///
/// Se usa en [`Shape`] y en [`area`].
pub struct Point {
    pub x: f64,
    pub y: f64,
}
```

1. ``[`Item`]`` enlaza a un item del crate.
2. ``[`crate::math::Point`]`` usa una ruta absoluta.
3. ``[`Point::x`]`` enlaza a un campo/método.
4. ``[`add`]`` enlaza a una función.
5. Un enlace roto es warning `PGS-W5701`.
6. Los enlaces se resuelven después de typecheck.
7. No se permiten enlaces a items privados desde docs públicas.

### 57.5 `@@doc`

```pengu
@@doc("Alias de `add`.")
@@must_use(message: "el resultado debe usarse")
@@deprecated(since: "0.2.0", note: "usa `add_v2`")
unveil add_v1 = (a: Int, b: Int) -> Int
    a + b
```

Rust generado:

```rust
#[doc = "Alias de `add`."]
#[must_use = "el resultado debe usarse"]
#[deprecated(since = "0.2.0", note = "usa `add_v2`")]
pub fn add_v1(a: i32, b: i32) -> i32 {
    a + b
}
```

1. `@@doc` añade documentación sin `---`.
2. `@@doc(hidden)` oculta el item de rustdoc.
3. `@@doc(alias = "sum")` añade un alias de búsqueda.
4. `@@must_use` avisa si se descarta el valor.
5. `@@must_use(message: "...")` personaliza el aviso.
6. `@@deprecated` marca el item como obsoleto.
7. `since` debe ser una versión semver; `note` es Markdown.
8. `@@doc` y `---` se combinan; el orden es `---` primero.

### 57.6 Rustdoc

```bash
pengu doc
pengu doc --open
pengu doc --document-private-items
pengu doc --no-deps
```

1. `pengu doc` transpila y ejecuta `cargo doc`.
2. La salida va a `target/doc/`.
3. `--open` abre el navegador.
4. `--document-private-items` incluye items privados.
5. `--no-deps` no documenta dependencias.
6. Los docs de dependencias se enlazan con `--extern-html-root-url`.
7. `pengu doc` falla si un enlace intra-doc está roto y `--deny warnings` está activo.

### 57.7 Doc tests

```pengu
--- Suma dos enteros.
---
--- ```pengu
--- assert_eq(add(2, 3), 5)
--- ```
unveil add = (a: Int, b: Int) -> Int
    a + b
```

1. `pengu test --doc` extrae los bloques `pengu`.
2. Cada bloque se compila como un crate de test.
3. `assert_eq` debe estar disponible en el bloque.
4. `no_run` compila pero no ejecuta.
5. `ignore` omite el bloque.
6. `should_panic` espera un pánico.
7. Las líneas que empiezan con `# ` se ocultan en la documentación.
8. Un doc test no ve items privados.

### 57.8 README y ejemplos

1. `pengu doc --readme` genera `README.md` desde `--!`.
2. El README incluye instalación, ejemplo mínimo y enlaces.
3. Los ejemplos del README se prueban con `pengu test --doc`.
4. Un ejemplo debe ser ejecutable y no depender de red.
5. Los ejemplos largos viven en `examples/` y se enlazan.
6. `examples/` se compila con `pengu build --examples`.
7. Un ejemplo no es un test; puede imprimir.

### 57.9 Lints de documentación

| Código | Situación | Solución |
|---|---|---|
| `PGS-W5701` | enlace intra-doc roto | corregir ruta |
| `PGS-W5702` | item público sin docs | añadir `---` |
| `PGS-E5701` | `@@doc` en item privado con `--document-private-items` | revisar visibilidad |
| `PGS-E5702` | bloque de código sin lenguaje | declarar `text` |
| `PGS-E5703` | HTML crudo | usar Markdown |
| `PGS-W5703` | `@@deprecated` sin `since` | añadir versión |

1. `@@deny(missing_docs)` convierte W5702 en error.
2. `pengu lint --doc` revisa enlaces y estilo.
3. Los docs de items `unveil` son obligatorios en librerías.
4. Los docs de items privados son opcionales.
5. Un doc test roto es error, no warning.
6. Los enlaces externos no se comprueban en CI por defecto.
7. Los ejemplos deben usar la API pública.

### 57.10 Criterios de aceptación

- [x] `---` y `--!` están definidos y mapeados a rustdoc.
- [x] Markdown permitido y enlaces intra-doc están cubiertos.
- [x] `@@doc`, `@@must_use` y `@@deprecated` están especificados.
- [x] `pengu doc` y los doc tests están documentados.
- [x] Los lints de documentación tienen códigos.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
