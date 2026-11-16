<a id="sec-71-referencias"></a>
## 71. Referencias

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 10 |
| Rust | Rust 2024 |
| Palabras mágicas | — |
| Depende de | §1–§70 |
| Ejemplos ejecutables | `no` |

### 71.1 Documentación oficial de Rust

| Recurso | Uso en esta spec |
|---|---|
| [The Rust Reference](https://doc.rust-lang.org/reference/) | Gramática, semántica de items, patrones, atributos y edición 2024. |
| [The Rust Programming Language](https://doc.rust-lang.org/book/) | Ownership, borrowing, lifetimes, traits, closures, async. |
| [Rustonomicon](https://doc.rust-lang.org/nomicon/) | Unsafe, aliasing, `transmute`, `MaybeUninit`, FFI. |
| [The Cargo Book](https://doc.rust-lang.org/cargo/) | Manifiesto, features, targets, workspaces, publicación. |
| [The rustc Book](https://doc.rust-lang.org/rustc/) | Ediciones, targets, codegen, diagnósticos. |
| [Rust Standard Library](https://doc.rust-lang.org/std/) | Tipos, traits, colecciones, sincronización, `std::error`. |
| [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/) | Nombres, documentación, interoperabilidad. |
| [The Rust Style Guide](https://doc.rust-lang.org/style-guide/) | Formato de Rust generado. |
| [Rust RFCs](https://github.com/rust-lang/rfcs) | Origen de features estables/inestables. |
| [Rust Edition Guide](https://doc.rust-lang.org/edition-guide/) | Cambios de edición 2024. |
| [Rust Release Notes](https://doc.rust-lang.org/releases.html) | MSRV y estabilidad. |
| [Rust Security](https://www.rust-lang.org/security) | Divulgación y políticas. |

### 71.2 Herramientas del ecosistema

| Recurso | Uso |
|---|---|
| [rustfmt](https://rust-lang.github.io/rustfmt/) | Formato del Rust emitido. |
| [Clippy](https://doc.rust-lang.org/clippy/) | Lints sobre el Rust emitido. |
| [rustdoc](https://doc.rust-lang.org/rustdoc/) | Documentación y doc tests. |
| [Miri](https://github.com/rust-lang/miri) | Detección de UB en tests unsafe. |
| [cargo-fuzz](https://github.com/rust-fuzz/cargo-fuzz) | Fuzzing. |
| [proptest](https://proptest-rs.github.io/proptest/) | Property testing. |
| [criterion](https://bheisler.github.io/criterion.rs/book/) | Benchmarks. |
| [wasm-bindgen](https://rustwasm.github.io/wasm-bindgen/) | Interop WASM/JS. |
| [embassy](https://embassy.dev/) | Async embebido. |
| [cortex-m](https://github.com/rust-embedded/cortex-m) | Targets ARM Cortex-M. |

### 71.3 Lenguajes que inspiran la sintaxis

| Recurso | Uso |
|---|---|
| [MoonScript](https://moonscript.org/) | Indentación, `->`, `=>`, expresiones, estilo conciso. |
| [MoonScript Reference](https://moonscript.org/reference/) | Semántica de funciones, clases (no adoptadas) y comprensiones. |
| [CoffeeScript](https://coffeescript.org/) | `->`/`=>`, indentación, expresiones. |
| [V language](https://vlang.io/) | Variables inmutables por defecto, no globales, simplicidad. |
| [Kotlin](https://kotlinlang.org/docs/home.html) | Inferencia local, `val`/`var`, tipos estáticos. |
| [Rust](https://www.rust-lang.org/) | Ownership, traits, pattern matching, zero-cost. |

### 71.4 Estándares y especificaciones

| Recurso | Uso |
|---|---|
| [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) | “DEBE”, “DEBERÍA”, “PUEDE” en esta spec. |
| [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174) | Ambigüedad de mayúsculas en RFC 2119. |
| [Unicode UAX #31](https://www.unicode.org/reports/tr31/) | Identificadores XID. |
| [Unicode 15.0](https://www.unicode.org/versions/Unicode15.0.0/) | Tablas de `XID_Start`/`XID_Continue`. |
| [SemVer 2.0.0](https://semver.org/) | Versionado de spec/compilador. |
| [TOML 1.0.0](https://toml.io/en/v1.0.0) | `Tome.toml`. |
| [UTF-8 RFC 3629](https://www.rfc-editor.org/rfc/rfc3629) | Codificación de fuente y strings. |
| [IEEE 754](https://ieeexplore.ieee.org/document/8766229) | `F32`/`F64`. |
| [Itanium C++ ABI](https://itanium-cxx-abi.github.io/cxx-abi/) | Referencia para ABI `extern "C"`/FFI (solo como contexto). |

### 71.5 Lecturas por tema

| Tema | Secciones | Referencia principal |
|---|---|---|
| Léxico/indentación | §2, §60, §61 | Rust Reference: tokens; MoonScript. |
| Tipos/ownership | §4, §16–§21 | Rust Book: ownership; Nomicon. |
| Genéricos/traits | §33–§36 | Rust Book: generics/traits; Reference. |
| Patrones | §30 | Rust Book: patterns; Reference. |
| Async/concurrencia | §50–§51 | Rust Book: async; `std::thread`. |
| Unsafe/FFI | §52–§53 | Nomicon; Rust Reference: FFI. |
| `no_std`/embebido | §55 | Embedded Rust Book; cortex-m. |
| Testing/docs | §56–§57 | Cargo Book; rustdoc Book. |
| Tooling | §58 | rustc/Cargo/rustfmt/Clippy. |
| Diagnósticos | §65 | rustc diagnostics; esta spec. |

### 71.6 Cómo citar esta especificación

```text
PenguScript Language Specification, versión 0.1.0-dev, revisión r11.
Documento único: docs/LANGUAGE.md.
Rust 2024, MSRV 1.85.0.
```

### 71.7 Criterios de aceptación

- [x] Hay referencias para Rust, MoonScript, V, Kotlin y estándares.
- [x] Cada área técnica importante tiene una fuente.
- [x] Las URLs son oficiales o primarias.
- [x] Se distingue inspiración de semántica adoptada.
- [x] La spec se puede citar con versión y revisión.

[↑ Volver al índice](#indice)
