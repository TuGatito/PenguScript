<a id="sec-56-testing"></a>
## 56. Testing

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 9 |
| Rust | `#[test]`, `#[should_panic]`, `#[ignore]`, `#[cfg(test)]` |
| Palabras mágicas | `@@test`, `@@should_panic`, `@@ignore`, `@@bench` |
| Depende de | §3, §13, §31, §48 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec56_testing.pengu` |

Los tests son **items**, no un lenguaje aparte. Se escriben en PenguScript, se
transpilan a `#[test]` y se ejecutan con `pengu test` o `cargo test`.

### 56.1 Principios

1. Un test es una función sin parámetros que no retorna un valor útil.
2. Los tests viven en el mismo crate o en `tests/`.
3. No hay `describe`/`it`: el nombre de la función es el nombre del test.
4. `assert` falla con pánico; el runner lo reporta como test fallido.
5. Un test no debe depender del orden de ejecución.
6. Los tests pueden usar `curse` si el código bajo prueba es unsafe.
7. Un test no puede ser `unveil`; no forma parte de la API.
8. Los tests no se compilan en `--release` salvo `cargo test --release`.

### 56.2 `@@test`

```pengu
add = (a: Int, b: Int) -> Int
    a + b

@@test
add_works = () -> Unit
    assert_eq(add(2, 3), 5)
```

Rust generado:

```rust
fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[test]
fn add_works() {
    assert_eq!(add(2, 3), 5);
}
```

1. `@@test` marca la función como test.
2. La función no lleva parámetros.
3. El tipo de retorno es `Unit` o `!Unit` (test fallible).
4. El nombre debe ser único en el módulo.
5. `@@test` implica `@@cfg(test)`; no se compila fuera de tests.
6. Un test puede llamar a funciones privadas del módulo.
7. `@@test` no se combina con `dream`, `curse` ni `eternal` en v1.
8. Un test no puede ser `@`/`@mut`/`@own`; no es método.

### 56.3 Test fallible

```pengu
@@test
parse_works = () -> !Unit
    bind n = parse_int("42")?
    assert_eq(n, 42)
    ok(())
```

Rust generado:

```rust
fn parse_int(s: &str) -> Result<i32, Box<dyn std::error::Error>> {
    Ok(s.parse()?)
}

#[test]
fn parse_works() -> Result<(), Box<dyn std::error::Error>> {
    let n = parse_int("42")?;
    assert_eq!(n, 42);
    Ok(())
}
```

1. `!Unit` permite usar `?` dentro del test.
2. El error debe convertir a `Box<dyn Error + Send + Sync>`.
3. `ok(())` es el retorno explícito.
4. Si el test retorna `err`, el runner lo marca como fallido.
5. `!Unit` no se usa para tests que solo panican.
6. El tipo de error se puede estrechar con `!Unit` + `Error` alias.
7. `?` no se usa en tests `Unit`.

### 56.4 Aserciones

| PenguScript | Rust | Uso |
|---|---|---|
| `assert(cond)` | `assert!(cond)` | condición booleana |
| `assert(cond, "msg")` | `assert!(cond, "msg")` | con mensaje |
| `assert_eq(a, b)` | `assert_eq!(a, b)` | igualdad |
| `assert_ne(a, b)` | `assert_ne!(a, b)` | desigualdad |
| `debug_assert(cond)` | `debug_assert!(cond)` | solo debug |
| `debug_assert_eq(a, b)` | `debug_assert_eq!(a, b)` | solo debug |
| `panic("msg")` | `panic!("msg")` | fallo incondicional |

1. `assert` y `assert_eq` son funciones del preludio, no palabras clave.
2. `assert_eq` requiere `Debug + PartialEq`.
3. El mensaje es `Str` y se evalúa solo al fallar.
4. `debug_assert` no se ejecuta en `--release`.
5. `panic` es `Never`; se puede usar en una rama.
6. No hay `assert_throws`; se usa `@@should_panic`.
7. Los mensajes deben describir el valor esperado y el obtenido.

```rust
fn main() {
    let total = 2 + 3;
    assert_eq!(total, 5, "2 + 3 debe ser 5");
    assert_ne!(total, 6);
}
```

### 56.5 `@@should_panic`

```pengu
@@test
@@should_panic(expected: "divide by zero")
divide_by_zero = () -> Unit
    bind _ = 1 / 0
```

Rust generado:

```rust
#[test]
#[should_panic(expected = "divide by zero")]
fn divide_by_zero() {
    let _ = 1 / 0;
}
```

1. `@@should_panic` espera un pánico; si no ocurre, el test falla.
2. `expected` es opcional; si se omite, cualquier pánico vale.
3. `expected` busca una subcadena del mensaje, no una igualdad exacta.
4. El pánico debe ocurrir en el cuerpo del test, no en el runner.
5. `@@should_panic` no se combina con `!Unit`.
6. Un `panic` en un `Drop` también cuenta.
7. El mensaje debe ser estable; no incluir direcciones ni rutas.

### 56.6 `@@ignore`

```pengu
@@test
@@ignore(reason: "requiere red")
network_test = () -> Unit
    assert(true)
```

Rust generado:

```rust
#[test]
#[ignore = "requiere red"]
fn network_test() {
    assert!(true);
}
```

1. `@@ignore` omite el test por defecto.
2. `pengu test -- --ignored` ejecuta solo los ignorados.
3. `--include-ignored` ejecuta todos.
4. `reason` se muestra en el reporte.
5. No se usa para ocultar tests rotos; se usa para tests lentos o externos.
6. `@@ignore` no cambia el código del test.
7. Un test ignorado cuenta como omitido, no como pasado.

### 56.7 Tests unitarios en el mismo archivo

```pengu
add = (a: Int, b: Int) -> Int
    a + b

@@cfg(test)
scroll tests
    summon super::*

    @@test
    add_works = () -> Unit
        assert_eq(add(2, 3), 5)
```

Rust generado:

```rust
fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_works() {
        assert_eq!(add(2, 3), 5);
    }
}
```

1. `@@cfg(test)` hace que el módulo solo exista en tests.
2. `summon super::*` importa el módulo padre.
3. El módulo de tests puede acceder a items privados.
4. No se usa `unveil` en el módulo de tests.
5. Los tests unitarios van al final del archivo.
6. Un módulo de tests no puede declarar `grimoire`.
7. Los nombres de tests pueden repetirse en módulos distintos.

### 56.8 Tests de integración

```text
tome/
├── Tome.toml
├── main.pengu
├── lib.pengu
└── tests/
    ├── api.pengu
    └── cli.pengu
```

`Tome.toml`:

```toml
[[test]]
name = "api"
path = "tests/api.pengu"

[[test]]
name = "cli"
path = "tests/cli.pengu"
```

1. Cada archivo de `tests/` es un crate de test independiente.
2. Solo puede usar la API pública (`unveil`).
3. `summon nombre_tome` importa la librería.
4. `tests/` no se compila en `pengu build`.
5. `pengu test --test api` ejecuta uno solo.
6. Los tests de integración pueden usar `std::process`.
7. Un test de integración no ve items privados.

### 56.9 Doc tests

1. Los bloques `pengu` en comentarios `---` se ejecutan con `pengu test --doc`.
2. El bloque se compila como un crate aparte.
3. `#` al inicio de una línea oculta esa línea en la documentación.
4. Un doc test que no compila falla.
5. `no_run` compila pero no ejecuta.
6. `should_panic` se escribe en el bloque.
7. Los doc tests usan la API pública.

### 56.10 Property testing

1. `proptest`/`quickcheck` se consumen como crates Rust.
2. La propiedad es una función `(T) -> Bool`.
3. El generador se declara con `proptest!` o `quickcheck!`.
4. Un fallo produce un caso mínimo (shrinking).
5. No hay sintaxis nueva en PenguScript; se usa el macro del crate.
6. Las propiedades no reemplazan tests de ejemplo.
7. Los rangos de entrada deben ser finitos.

### 56.11 Fuzzing

1. `cargo-fuzz` usa `libFuzzer` y un target `fuzz_target!`.
2. El target recibe `&[U8]` y no debe panican por entradas válidas.
3. Un crash se guarda en `fuzz/artifacts/`.
4. `pengu fuzz` es un wrapper de `cargo fuzz`.
5. Los targets viven en `fuzz/fuzz_targets/` y son Rust.
6. Un fuzz target no se ejecuta en CI por defecto.
7. La semilla se registra para reproducir.

### 56.12 Benchmarks

```pengu
@@bench
bench_add = () -> Unit
    bind _ = add(2, 3)
```

Rust generado (nightly, `#[bench]`; no se compila en stable):

```text
#![feature(test)]
extern crate test;

#[bench]
fn bench_add(b: &mut test::Bencher) {
    b.iter(|| add(2, 3));
}
```

Equivalente estable con `criterion` (crate externo):

```rust
fn add(a: i32, b: i32) -> i32 {
    a + b
}

fn bench_add() {
    let mut total = 0;
    for _ in 0..1000 {
        total += add(2, 3);
    }
    assert_eq!(total, 5000);
}
```

1. `@@bench` genera `#[bench]`, que requiere nightly.
2. En stable se usa `criterion` como crate externo.
3. Un benchmark no es un test; no falla por lentitud.
4. `criterion` mide con intervalo de confianza.
5. Los benchmarks no se ejecutan en `pengu test`.
6. `pengu bench` ejecuta `cargo bench`.
7. Los resultados no son parte del contrato del lenguaje.

### 56.13 Cobertura y CI

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - run: cargo install --path . --locked
      - run: pengu check --deny warnings
      - run: pengu test --all
      - run: pengu test --doc
```

1. `pengu test --coverage` usa `llvm-cov` o `tarpaulin`.
2. La cobertura es una señal, no un objetivo.
3. CI debe ejecutar `check`, `test`, `fmt --check`, `lint`.
4. `--locked` garantiza `Tome.lock`.
5. Los tests de integración pueden necesitar servicios; se marcan `@@ignore`.
6. La matriz de Rust se fija en `rust-version`.
7. Un test que pasa en local y falla en CI suele ser orden/estado global.

### 56.14 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5601` | `@@test` con parámetros | quitar parámetros |
| `PGS-E5602` | `@@test` con retorno no permitido | usar `Unit`/`!Unit` |
| `PGS-E5603` | `@@test` en `ritual`/`pact` | mover a módulo libre |
| `PGS-E5604` | `@@should_panic` sin `@@test` | añadir `@@test` |
| `PGS-E5605` | `@@ignore` sin `@@test` | añadir `@@test` |
| `PGS-E5606` | test de integración usa item privado | hacer `unveil` |
| `PGS-W5601` | test sin aserción | añadir `assert` o retorno |
| `PGS-W5602` | `debug_assert` en test | usar `assert` |

### 56.15 Criterios de aceptación

- [x] `@@test`, `@@should_panic` y `@@ignore` están definidos.
- [x] Las aserciones y sus tipos están documentadas.
- [x] Tests unitarios, de integración y doc tests están cubiertos.
- [x] Property testing, fuzzing, benchmarks y cobertura están explicados.
- [x] CI tiene un ejemplo ejecutable.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
