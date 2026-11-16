<a id="sec-43-crates"></a>
## 43. Crates, packages y workspaces (`tome`)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 6 |
| Rust | Cargo, `Cargo.toml`, workspaces, features |
| Palabras mágicas | `tome`, `Tome.toml` |
| Depende de | §3, §41, §47 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec43_tome.pengu` |

Un **tome** es la unidad de distribución de PenguScript: un directorio con
`Tome.toml`, código fuente y, opcionalmente, tests, ejemplos y benchmarks. Se
corresponde con un **package** de Cargo; el crate compilado es su biblioteca o
binario. Un **workspace** agrupa varios tomes.

### 43.1 Estructura de un tome

```text
pengu-demo/
  Tome.toml
  Tome.lock
  main.pengu
  lib.pengu
  build.pengu
  tests/
  examples/
  benches/
```

Reglas:

1. `Tome.toml` es obligatorio; sin él no es un tome.
2. La raíz del crate es `main.pengu` (binario), `lib.pengu` (librería) o ambos.
3. `Tome.lock` lo genera el compilador; no se edita a mano.
4. `build.pengu` es el build script (§47).
5. `tests/`, `examples/` y `benches/` siguen la convención de Cargo.
6. Un tome puede tener varias metas (`[[bin]]`, `[[test]]`, etc.).

### 43.2 `Tome.toml`

```toml
[tome]
name = "pengu-demo"
version = "0.1.0"
pengu = "0.1"
edition = "2024"
rust-version = "1.85"
description = "Demo de PenguScript"
license = "MIT"

[dependencies]
serde = { version = "1.0", features = ["derive"], optional = true }

[dev-dependencies]
pretty_assertions = "1"

[build-dependencies]
cc = "1"

[features]
default = ["std"]
std = []
serde = ["dep:serde"]

[lib]
path = "lib.pengu"

[[bin]]
name = "demo"
path = "main.pengu"

[[test]]
name = "integration"
path = "tests/integration.pengu"

[[bench]]
name = "throughput"
path = "benches/throughput.pengu"
harness = false

[profile.release]
lto = true
codegen-units = 1

[workspace]
members = ["crates/*"]
resolver = "2"

[cargo]
# Claves de Cargo sin equivalente PenguScript; se copian tal cual.
```

1. `[tome]` es la sección obligatoria; `name`, `version`, `pengu`, `edition` y
   `rust-version` son obligatorios.
2. `pengu` fija la versión del compilador; el compilador rechaza una versión
   incompatible (`PGS-E4311`).
3. `edition` es la edición de Rust generada; el valor inicial es `"2024"`.
4. `rust-version` es el MSRV; no puede ser menor que `1.85`.
5. Las tablas de dependencias son las de Cargo, con versiones semver.
6. `[features]` es aditivo; `dep:serde` activa la dependencia opcional.
7. `path` de las metas apunta a `.pengu`, no a `.rs`.
8. `[workspace]` convierte el tome en raíz de workspace.
9. `[cargo]` es el passthrough auditado; no puede sobrescribir claves
   protegidas (`package.name`, `package.version`, `lib.path`, `bin.path`).

### 43.3 De `Tome.toml` a `Cargo.toml`

El codegen produce un `Cargo.toml` en `target/pengu/`:

```toml
[package]
name = "pengu-demo"
version = "0.1.0"
edition = "2024"
rust-version = "1.85"
description = "Demo de PenguScript"
license = "MIT"

[lib]
path = "src/lib.rs"

[[bin]]
name = "demo"
path = "src/main.rs"

[features]
default = ["std"]
std = []
serde = ["dep:serde"]

[dependencies]
serde = { version = "1.0", features = ["derive"], optional = true }
```

1. Los `path` `.pengu` se reescriben a `src/*.rs`.
2. `[tome]` se convierte en `[package]`.
3. Las dependencias, features, perfiles y workspace se copian.
4. `Tome.lock` se copia a `Cargo.lock`; el lockfile es la fuente de verdad de
   las versiones resueltas.
5. El crate generado no se publica; se publica el tome y su código fuente.
6. `cargo` puede invocarse sobre `target/pengu/` para diagnóstico, pero el
   flujo normal es `pengu build`.

### 43.4 Dependencias

```toml
[dependencies]
serde = { version = "1.0", features = ["derive"] }
rand = "0.8"

[target.'cfg(target_os = "linux")'.dependencies]
libc = "0.2"

[target.'cfg(windows)'.dependencies]
windows-sys = { version = "0.59", features = ["Win32_Foundation"] }
```

1. Una dependencia normal se compila para el target.
2. Una dependencia de target solo se incluye si el `cfg` se cumple.
3. `optional = true` se activa con una feature; no se importa si no está activa.
4. `[dev-dependencies]` solo para tests, ejemplos y benches.
5. `[build-dependencies]` solo para `build.pengu`.
6. Las dependencias se resuelven con semver; `Tome.lock` fija las versiones.
7. Un path dependency usa `{ path = "../otro" }`; sigue siendo un tome.

### 43.5 Workspaces

```toml
[workspace]
members = ["crates/core", "crates/cli", "crates/macros"]
resolver = "2"

[workspace.dependencies]
serde = { version = "1.0", features = ["derive"] }
```

1. Un workspace comparte `Tome.lock` y `target/`.
2. `[workspace.dependencies]` centraliza versiones; un miembro las hereda con
   `serde.workspace = true`.
3. `resolver = "2"` es el recomendado para editiones modernas.
4. Un miembro puede ser binario, librería o ambos.
5. Los paths de workspace no pueden salir del directorio raíz sin declararlo.
6. `pengu build -p core` construye un miembro; `pengu build --workspace` todos.

### 43.6 Versiones, lockfile y registro

- La versión del tome sigue semver: `MAJOR.MINOR.PATCH`.
- `0.x` se considera inestable; un cambio incompatible sube `MINOR`.
- `Tome.lock` se versiona para binarios y se ignora para librerías publicadas.
- El registro por defecto es crates.io; `[registries]` permite registros
  alternativos.
- Un `pengu publish` empaqueta el fuente `.pengu`, no el Rust generado.
- El checksum del lockfile detecta cambios de dependencias.
- No se permite un `path` dependency en un paquete publicado; se usa una
  versión del registro.

### 43.7 Ejemplo mínimo

`Tome.toml`:

```toml
[tome]
name = "hello"
version = "0.1.0"
pengu = "0.1"
edition = "2024"
rust-version = "1.85"
```

`main.pengu`:

```pengu
grimoire
    print("hello from a tome")
```

Rust generado (`src/main.rs`):

```rust
fn main() {
    println!("hello from a tome");
}
```

### 43.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4310` | falta `Tome.toml` | crearlo en la raíz |
| `PGS-E4311` | versión de `pengu` incompatible | actualizar el compilador o el campo |
| `PGS-E4312` | `rust-version` menor que 1.85 | subir el MSRV |
| `PGS-E4313` | `path` de meta no es `.pengu` | corregir la ruta |
| `PGS-E4314` | clave protegida en `[cargo]` | quitarla del passthrough |
| `PGS-E4315` | workspace con miembro fuera de la raíz | declarar el path o moverlo |
| `PGS-W4310` | lockfile desactualizado | `pengu update` |

### 43.9 Criterios de aceptación

- [x] `Tome.toml` mapea a `Cargo.toml`.
- [x] Dependencias, features, targets y workspace están cubiertos.
- [x] Semver, lockfile y registro están definidos.
- [x] El ejemplo mínimo tiene Rust generado.
- [x] El ejemplo Rust compila.

[↑ Volver al índice](#indice)
