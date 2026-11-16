<a id="sec-55-no-std"></a>
## 55. `no_std`, embebidos y wasm

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 8 |
| Rust | `#![no_std]`, `core`, `alloc`, `#[panic_handler]`, `#[global_allocator]` |
| Palabras mágicas | `@@no_std`, `@@panic_handler`, `@@global_allocator` |
| Depende de | §3, §6, §51, §53 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec55_no_std.pengu` |

PenguScript puede compilar sin `std`. El subconjunto `core` está siempre
disponible; `alloc` solo si se declara un allocator. El objetivo es que el
mismo lenguaje sirva para sistemas, embebidos y wasm sin un runtime propio.

### 55.1 `@@no_std`

```pengu
@@no_std

unveil add = (a: Int, b: Int) -> Int
    a + b
```

Rust generado:

```rust
#![no_std]

pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

1. `@@no_std` debe estar en la raíz del crate (`main.pengu`/`lib.pengu`).
2. Desactiva `std`; deja `core` y, si se declara, `alloc`.
3. No se puede usar `std::` en un crate `no_std`.
4. `print`, `Vec`, `String` y `HashMap` requieren `alloc` o `std`.
5. `@@no_std` no desactiva el borrow checker ni los checks de seguridad.
6. Un crate `no_std` puede depender de crates `no_std`.
7. `@@no_std` es incompatible con `grimoire` de runtime normal; se usa una
   entry point del target.

### 55.2 `core` y `alloc`

| Necesidad | Crate | Ejemplo |
|---|---|---|
| tipos primitivos, `Option`, `Result` | `core` | `Option[Int]` |
| slices, arrays, iteradores | `core` | `&[U8]` |
| `fmt`, `cmp`, `ops` | `core` | `Display`, `Add` |
| `Vec`, `String`, `Box`, `Rc` | `alloc` | `Vec[U8]` |
| `HashMap`, `File`, `TcpStream` | `std` | no en `no_std` |

1. `core` no asigna memoria.
2. `alloc` requiere un allocator global.
3. `alloc` no incluye `HashMap`; se usa `alloc::collections::BTreeMap`.
4. `std` reexporta `core` y `alloc`.
5. Un crate `no_std` puede usar `alloc` con `extern crate alloc`.
6. Los iteradores de `core` son los mismos que los de `std`.
7. `format!` requiere `alloc`; `write!` puede usar `core::fmt::Write`.

```rust
#![no_std]

extern crate alloc;

use alloc::vec::Vec;

pub fn squares(n: usize) -> Vec<usize> {
    (0..n).map(|x| x * x).collect()
}
```

### 55.3 Panic handler

```pengu
@@no_std

@@panic_handler
panic = (info: &PanicInfo) -> !
    -- SAFETY: no hay runtime; se detiene el core.
    loop
```

Rust generado:

```rust
#![no_std]

use core::panic::PanicInfo;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {}
}
```

1. Un binario `no_std` necesita exactamente un `#[panic_handler]`.
2. Una librería `no_std` no lo necesita; el binario final lo aporta.
3. El handler debe ser `-> !` y no puede retornar.
4. En embebidos, suele reiniciar, hacer `udf` o escribir en un puerto.
5. En wasm, puede llamar a `unreachable`.
6. No se puede usar `println!` dentro del handler si no hay I/O.
7. `@@panic_handler` se marca con `@@deny(unconditional_panic)` si el cuerpo
   puede entrar en pánico.

### 55.4 Allocator

```pengu
@@global_allocator
relic ALLOC: System = System
```

Rust generado:

```rust
#[global_allocator]
static ALLOC: std::alloc::System = std::alloc::System;
```

1. `@@global_allocator` marca el allocator del crate.
2. Solo puede haber uno.
3. En `no_std`, se implementa `GlobalAlloc` o se usa un crate como `linked_list_allocator`.
4. El allocator debe ser seguro para todos los hilos o declarar su política.
5. `alloc` sin allocator falla en el link.
6. Un allocator de embebido suele usar un heap estático.
7. `System` solo existe con `std`; el ejemplo es para un crate con `std`.

### 55.5 Entry point y target

```pengu
@@no_std
@@no_main

@@panic_handler
panic = (info: &PanicInfo) -> !
    loop

@@entry
start = () -> !
    loop
```

Rust generado (`#[entry]` lo aporta el crate del target; aquí se usa
`#[unsafe(no_mangle)]` para que el bloque compile aislado):

```rust
#![no_std]
#![no_main]

use core::panic::PanicInfo;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {}
}

#[unsafe(no_mangle)]
pub extern "C" fn start() -> ! {
    loop {}
}
```

1. `@@no_main` desactiva el `main` de Rust.
2. `@@entry` lo aporta el crate del target (`cortex-m-rt`, `riscv-rt`,
   `wasm-bindgen`, etc.); no es un atributo del núcleo.
3. El símbolo de entrada debe ser `extern "C"` y `-> !` en embebidos.
4. El linker script define Flash/RAM y el vector table.
5. `start` no retorna; si retorna, el comportamiento es indefinido.
6. En wasm, la entry la genera `wasm-bindgen` o el runtime JS.
7. En un SO, `grimoire` sigue siendo la entrada normal.

### 55.6 Target triples

| Target | Uso | `std` |
|---|---|---|
| `thumbv6m-none-eabi` | Cortex-M0/M0+ | no |
| `thumbv7em-none-eabihf` | Cortex-M4F/M7F | no |
| `thumbv8m.main-none-eabihf` | Cortex-M33 | no |
| `riscv32imac-unknown-none-elf` | RISC-V embebido | no |
| `x86_64-unknown-none` | kernel/bare metal | no |
| `wasm32-unknown-unknown` | navegador | no |
| `wasm32-wasip1` | WASI | parcial |

1. El target se elige en `Tome.toml` o en la CLI.
2. `Tome.toml` declara `[[bin]] target = "..."`.
3. El target por defecto es el host.
4. Los targets `none` no tienen SO ni allocator.
5. Los targets wasm tienen memoria lineal y no threads por defecto.
6. La compilación cruzada requiere el target instalado (`rustup target add`).
7. `build-std` compila `core`/`alloc` desde fuente; requiere nightly.

### 55.7 Cross-compilation y linker

`Tome.toml`:

```toml
[tome]
name = "blink"
version = "0.1.0"
pengu = "0.1"
edition = "2024"
rust-version = "1.85"

[[bin]]
name = "blink"
path = "main.pengu"
target = "thumbv7em-none-eabihf"
```

`.cargo/config.toml`:

```toml
[target.thumbv7em-none-eabihf]
runner = "probe-rs run --chip STM32F401RE"
rustflags = ["-C", "link-arg=-Tlink.x"]

[build]
target = "thumbv7em-none-eabihf"
```

`memory.x`:

```ld
MEMORY
{
  FLASH : ORIGIN = 0x08000000, LENGTH = 512K
  RAM   : ORIGIN = 0x20000000, LENGTH = 128K
}
```

1. El linker script lo aporta el crate del chip (`cortex-m-rt`).
2. `memory.x` define las regiones; se incluye con `include!("memory.x")` en
   `build.rs` o con `-Tlink.x`.
3. `runner` permite `cargo run` sobre hardware.
4. `rustflags` debe ser reproducible; se documenta en el tome.
5. `probe-rs`/`openocd` no forman parte del compilador.
6. Un error de linker no es un error de tipos; se muestra con el comando.

### 55.8 Volatile y MMIO

```pengu
curse write_reg = (addr: Usize, value: U32) -> Unit
    -- SAFETY: `addr` es un registro MMIO válido y alineado.
    write_volatile(addr as *mut U32, value)
```

Rust generado:

```rust
fn write_reg(addr: usize, value: u32) {
    // SAFETY: `addr` es un registro MMIO válido y alineado.
    unsafe { core::ptr::write_volatile(addr as *mut u32, value) }
}
```

1. `read_volatile`/`write_volatile` no se optimizan ni se reordenan.
2. No reemplazan una barrera de memoria; para eso se usa `fence`.
3. El registro debe ser `*mut U32` alineado.
4. `Usize` no garantiza que la dirección sea válida.
5. En embebidos, los registros suelen ser `static` con `UnsafeCell`.
6. `volatile` no es para sincronización entre hilos.
7. `asm!` puede ser necesario para instrucciones especiales.

### 55.9 Interrupciones

1. Una interrupción es una función `extern "C"` con un vector asociado.
2. El atributo `@@interrupt` lo aporta el crate del chip; no es del núcleo.
3. El handler no debe bloquear ni asignar memoria.
4. El estado compartido se protege con `critical-section` o atomics.
5. `static mut` no se usa; se usa `@@shared` con `Mutex`/`RefCell` según el
   contexto.
6. La prioridad y el nesting dependen del chip.
7. En Cortex-M, el vector table lo genera `cortex-m-rt`.

### 55.10 `cortex-m` y `embassy`

1. `cortex-m` aporta `interrupt`, `entry`, `Peripherals` y `NVIC`.
2. `cortex-m-rt` aporta el runtime y el linker script.
3. `embassy` aporta async sin `std`; se usa `dream`/`awaken`.
4. `embassy-executor` es el executor; no hay runtime del lenguaje.
5. `embedded-hal` define traits de periféricos.
6. `defmt` es logging binario; no es `print`.
7. `panic-probe` implementa el panic handler sobre `defmt`.

### 55.11 wasm

1. `wasm32-unknown-unknown` no tiene `std`; se usa `core`/`alloc`.
2. `wasm32-wasip1` tiene `std` parcial y filesystem virtual.
3. `wasm-bindgen` expone funciones y tipos JS.
4. `#[wasm_bindgen]` es un proc macro; se consume, no se define.
5. La memoria se exporta como `WebAssembly.Memory`.
6. No hay threads por defecto; `wasm-bindgen-rayon` requiere features.
7. El tamaño de `Usize` es 32 bits en wasm32.
8. Las llamadas JS pueden lanzar excepciones; se capturan en el borde.

`Tome.toml` para wasm:

```toml
[tome]
name = "pengu-wasm"
version = "0.1.0"
pengu = "0.1"
edition = "2024"
rust-version = "1.85"

[lib]
path = "lib.pengu"
crate-type = ["cdylib"]

[dependencies]
wasm-bindgen = "0.2"
```

### 55.12 `build-std`

```toml
[unstable]
build-std = ["core", "alloc"]
build-std-features = ["compiler-builtins-mem"]
```

1. `build-std` compila `core`/`alloc` con el target actual.
2. Requiere nightly y `rust-src`.
3. Se usa cuando el target no tiene artifacts precompilados.
4. Aumenta el tiempo de build.
5. `compiler-builtins-mem` aporta `memcpy`/`memset`.
6. No se usa en el camino normal del compilador.
7. Las features inestables se documentan en §66.

### 55.13 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5501` | `std` en crate `no_std` | usar `core`/`alloc` |
| `PGS-E5502` | binario `no_std` sin panic handler | añadir `@@panic_handler` |
| `PGS-E5503` | `alloc` sin allocator | añadir `@@global_allocator` |
| `PGS-E5504` | entry point ausente | añadir `@@entry` |
| `PGS-E5505` | volatile fuera de `curse` | envolver en `curse` |
| `PGS-E5506` | target sin soporte | instalar target/`build-std` |
| `PGS-W5501` | `no_std` innecesario | usar `std` |
| `PGS-W5502` | handler de panic que retorna | usar `-> !` |

### 55.14 Criterios de aceptación

- [x] `@@no_std`, `core`/`alloc` y panic handler están definidos.
- [x] El allocator y la entry point están cubiertos.
- [x] Los targets, linker y `build-std` están documentados.
- [x] Volatile/MMIO e interrupciones están limitados a `curse`.
- [x] wasm y `wasm-bindgen` están integrados.
- [x] Los ejemplos Rust compilan como librería `no_std`.

[↑ Volver al índice](#indice)
