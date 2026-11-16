<a id="sec-47-build-features"></a>
## 47. Build scripts, features y cfg

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 6 |
| Rust | `build.rs`, `[features]`, `#[cfg]`, `cfg!` |
| Palabras mágicas | `build.pengu`, `@@cfg` |
| Depende de | §3, §43, §44 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec47_build_features.pengu` |

Un **build script** es un programa que se ejecuta antes de compilar la crate.
Puede generar código, emitir directivas a Cargo, detectar el entorno y enlazar
bibliotecas nativas. En PenguScript se escribe en `build.pengu` y se traduce a
`build.rs`.

### 47.1 `build.pengu`

```pengu
summon std::env
summon std::fs

grimoire
    bind out = env.var("OUT_DIR").unwrap()
    bind path = "#{out}/generated.rs"
    fs.write(path, "pub const BUILD_ID: &str = \"demo\";").unwrap()
    print("cargo:rerun-if-changed=build.pengu")
```

Rust generado (`build.rs`):

```rust
use std::env;
use std::fs;

fn main() {
    let out = env::var("OUT_DIR").unwrap();
    let path = format!("{}/generated.rs", out);
    fs::write(&path, "pub const BUILD_ID: &str = \"demo\";").unwrap();
    println!("cargo:rerun-if-changed=build.pengu");
}
```

Reglas:

1. `build.pengu` es un programa completo con entrada `grimoire`.
2. Se ejecuta con la toolchain anfitriona, antes de compilar la crate.
3. Su salida estándar se interpreta como directivas `cargo:`.
4. `OUT_DIR` es el directorio donde puede escribir archivos generados.
5. No debe acceder a la red ni a rutas absolutas del desarrollador.
6. Si no existe `build.pengu`, no se genera `build.rs`.
7. `[build-dependencies]` en `Tome.toml` declara sus dependencias.
8. Un build script no puede importar la crate que está construyendo.

### 47.2 Directivas de Cargo

| Directiva | Efecto |
|---|---|
| `cargo:rerun-if-changed=RUTA` | reejecutar si cambia el archivo |
| `cargo:rerun-if-env-changed=VAR` | reejecutar si cambia la variable |
| `cargo:rustc-cfg=CLAVE` | activar un `cfg` |
| `cargo:rustc-check-cfg=CLAVE` | declarar un `cfg` conocido |
| `cargo:rustc-env=VAR=VALOR` | definir una variable de entorno |
| `cargo:rustc-link-lib=LIB` | enlazar una biblioteca nativa |
| `cargo:rustc-link-search=RUTA` | añadir un directorio de búsqueda |
| `cargo:rustc-link-arg=ARG` | pasar un argumento al linker |
| `cargo:warning=MENSAJE` | aviso de compilación |
| `cargo:metadata=...` | metadato para herramientas |

1. Cada directiva va en una línea, sin espacios antes de `cargo:`.
2. `rerun-if-changed` sustituye al comportamiento por defecto; si se emite, el
   script solo se reejecuta por esas rutas.
3. `rustc-check-cfg` evita el warning de `unexpected_cfgs`.
4. `rustc-env` está disponible con `env!` en el código.
5. `rustc-link-lib` y `rustc-link-search` se usan para FFI (§54).
6. `cargo:warning` no falla la compilación; para fallar, el script debe salir
   con error.

### 47.3 Features

```toml
[features]
default = ["std"]
std = []
serde = ["dep:serde"]
full = ["std", "serde"]

[dependencies]
serde = { version = "1.0", features = ["derive"], optional = true }
```

1. Una feature es una bandera de compilación; no es un valor de runtime.
2. Las features son **aditivas**: activar una no desactiva otra.
3. `default` se activa salvo `--no-default-features`.
4. `dep:serde` activa la dependencia opcional sin crear una feature implícita.
5. Una feature puede activar otras: `full = ["std", "serde"]`.
6. No hay features negativas; no se puede “quitar” una feature.
7. La unificación de features ocurre en todo el grafo de dependencias.
8. Una feature no debe cambiar la semántica de forma incompatible; debe añadir
   funcionalidad.

### 47.4 `@@cfg`

```pengu
@@cfg(feature = "serde")
serialize_user = (user: &User) -> String
    format!("{}", user.name)

@@cfg(target_os = "linux")
platform = () -> Str
    "linux"
```

Rust generado:

```rust
struct User {
    name: String,
}

#[cfg(feature = "serde")]
fn serialize_user(user: &User) -> String {
    format!("{}", user.name)
}

#[cfg(target_os = "linux")]
fn platform() -> &'static str {
    "linux"
}
```

1. `@@cfg` elimina el item si la condición es falsa; no hay rama `else`.
2. La condición usa la sintaxis de `cfg` de Rust.
3. `feature = "x"` consulta una feature del tome.
4. `target_os`, `target_arch`, `target_family`, `target_env`,
   `target_pointer_width`, `unix`, `windows` describen el target.
5. `debug_assertions` distingue debug/release.
6. `test` solo está activo al compilar tests.
7. Una condición con una feature no declarada produce `PGS-W4710`.

### 47.5 `cfg!` en runtime

```pengu
grimoire
    if cfg!(debug_assertions) then
        print("debug")
    else
        print("release")
```

Rust generado:

```rust
fn main() {
    if cfg!(debug_assertions) {
        println!("debug");
    } else {
        println!("release");
    }
}
```

1. `cfg!` es una macro de Rust que se evalúa en compilación y devuelve `Bool`.
2. Es útil para código que debe existir en ambas ramas.
3. `cfg!` no elimina el código de la rama falsa; para eso se usa `@@cfg`.
4. `cfg!` en una condición de tipo no es válido; devuelve `Bool`.
5. `cfg!` con una feature no declarada produce el mismo warning que `@@cfg`.

### 47.6 `cfg` por target

```rust
#[cfg(target_os = "linux")]
fn platform() -> &'static str {
    "linux"
}

#[cfg(target_os = "windows")]
fn platform() -> &'static str {
    "windows"
}

#[cfg(not(any(target_os = "linux", target_os = "windows")))]
fn platform() -> &'static str {
    "other"
}

fn main() {
    println!("{}", platform());
}
```

1. Solo una definición de `platform` se compila por target.
2. Las tres ramas deben cubrir todos los targets que se quieran soportar.
3. Si ninguna coincide, el símbolo no existe y el error es de resolución.
4. Los `cfg` de target no son mutuamente excluyentes por sí solos; se usa
   `not(any(...))` para el caso restante.
5. Un `cfg` desconocido no es error de compilación, pero puede ser warning.

### 47.7 Código generado

```pengu
rust
    include!(concat!(env!("OUT_DIR"), "/generated.rs"));
```

1. Un build script puede escribir `.rs` en `OUT_DIR`.
2. `include!` inserta el archivo en el crate.
3. El código incluido es Rust crudo; pasa por el compilador de Rust.
4. El código generado debe ser determinista y no contener rutas absolutas.
5. Para generarlo desde PenguScript, se escribe con `fs.write` en el build
   script; no se evalúa en tiempo de compilación de PenguScript.
6. Un `include!` de un archivo ausente es error de compilación.

### 47.8 Reproducibilidad

1. Un build script no debe acceder a la red.
2. No debe leer variables de entorno no declaradas con
   `rerun-if-env-changed`.
3. No debe incluir timestamps ni rutas absolutas en el código generado.
4. Debe emitir `rerun-if-changed` para sus entradas.
5. La salida debe ser determinista para las mismas entradas.
6. `SOURCE_DATE_EPOCH` se usa si se necesita una fecha reproducible.
7. Un build script que falla debe imprimir un mensaje claro y salir con error.

### 47.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4701` | `build.pengu` sin `grimoire` | añadir la entrada |
| `PGS-E4702` | directiva `cargo:` mal formada | revisar la línea |
| `PGS-E4703` | `OUT_DIR` no usado | escribir el archivo en `OUT_DIR` |
| `PGS-E4704` | feature no declarada | añadirla a `[features]` |
| `PGS-E4705` | `cfg` con clave desconocida | usar una clave válida |
| `PGS-E4706` | build script importa la crate actual | quitar la dependencia |
| `PGS-E4707` | código generado no determinista | eliminar timestamp/rutas |
| `PGS-W4710` | `cfg` de feature no declarada | declararla o corregir |
| `PGS-W4711` | `rerun-if-changed` ausente | declarar las entradas |

### 47.10 Criterios de aceptación

- [x] `build.pengu` mapea a `build.rs`.
- [x] Las directivas de Cargo están cubiertas.
- [x] Features, `@@cfg` y `cfg!` están definidos.
- [x] El código generado y la reproducibilidad están tratados.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
