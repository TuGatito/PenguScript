<a id="sec-64-desugaring"></a>
## 64. Desugaring

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 10 |
| Rust | Rust 2024 |
| Palabras mágicas | todas |
| Depende de | §2–§59 |
| Ejemplos ejecutables | `no` |

El desugaring es la transformación de la forma superficial de PenguScript a
una forma core explícita; después el generador emite Rust. Las tablas son
normativas para el compilador y para entender el código generado.

### 64.1 Declaraciones y tipos

| Azúcar | Forma core | Rust |
|---|---|---|
| `bind x = e` | `let x: T = e` | `let x = e;` |
| `morph x = e` | `let mut x: T = e` | `let mut x = e;` |
| `sigil N: T = e` | constante de módulo | `const N: T = e;` |
| `relic N: T = e` | static inmutable | `static N: T = e;` |
| `rune P` + campos | struct nominal | `struct P { … }` |
| `rune P(A, B)` | tuple struct | `struct P(A, B);` |
| `rune M` | unit struct | `struct M;` |
| `enchanting E` | enum nominal | `enum E { … }` |
| `pact T` | trait | `trait T { … }` |
| `ritual T for U` | impl de trait | `impl T for U { … }` |
| `ritual T` | impl inherente | `impl T { … }` |
| `essence A = B` | alias | `type A = B;` |
| `scroll m` | módulo | `mod m { … }` |
| `summon p` | import | `use p;` |
| `unveil` | visibilidad | `pub` |
| `unveil(tome)` | visibilidad crate | `pub(crate)` |
| `unveil(scroll)` | visibilidad padre | `pub(super)` |
| `unveil(in p)` | visibilidad path | `pub(in p)` |
| `@@attr` | atributo externo | `#[attr]` |
| `@@!attr` | atributo interno | `#![attr]` |
| `grimoire` | entry point | `fn main()` |
| `incantation n` | macro declarativa | `macro_rules! n` |
| `chimera U` | union | `union U` |
| `foreign "C"` | extern block | `extern "C"` |
| `rust` block | passthrough auditado | tokens Rust |

### 64.2 Funciones, lambdas y métodos

| Azúcar | Forma core | Rust |
|---|---|---|
| `f = (x: T) -> U` + cuerpo | función item | `fn f(x: T) -> U { … }` |
| `f = (...) -> U = e` | función item de una expresión | `fn f(...) -> U { e }` |
| `(x: T) => e` | lambda que captura | `|x: T| e` |
| `move (x: T) => e` | lambda move | `move |x: T| e` |
| `@` | receiver inmutable | `&self` |
| `@mut` | receiver mutable | `&mut self` |
| `@own` | receiver por valor | `self` |
| `dream f = ...` | función async | `async fn f(...)` |
| `curse f = ...` | función unsafe | `unsafe fn f(...)` |
| `eternal f = ...` | función const | `const fn f(...)` |
| `f?` en retorno `!T` | propagación | `f?` |
| `return e` | retorno temprano | `return e;` |
| `panic(msg)` | divergencia | `panic!(msg)` |

Una lambda sin `move` captura por referencia cuando es posible; el borrow
checker decide. Una lambda con `move` captura por valor. Las funciones
nombradas nunca capturan.

### 64.3 Expresiones y control

| Azúcar | Forma core | Rust |
|---|---|---|
| `if c then a else b` | `match c { true => a, false => b }` | `if c { a } else { b }` |
| `unless c then a` | `if not c then a` | `if !c { a; }` |
| `if c then a` sin else | rama `Unit` | `if c { a; }` |
| `match e` + `when p then x` | match | `match e { p => x, … }` |
| `when p if g then x` | guard | `p if g => x` |
| `else x` | wildcard | `_ => x` |
| `loop` + `break v` | loop con valor | `loop { break v; }` |
| `while c` | while | `while c { … }` |
| `for p in xs` | for | `for p in xs { … }` |
| `for p in a..b` | range for | `for p in a..b { … }` |
| `for p in xs by n` | step_by | `for p in xs.step_by(n) { … }` |
| `break` | break unit | `break;` |
| `continue` | continue | `continue;` |
| `outer: for …` | label | `'outer: for …` |
| `[e for x in xs if p]` | filter/map/collect | `xs.iter().filter(…).map(…).collect::<Vec<_>>()` |
| `{k: v for x in xs}` | map collect | `xs.iter().map(…).collect::<HashMap<_,_>>()` |
| `do` + bloque | block expression | `{ … }` |
| `a and b` | cortocircuito | `a && b` |
| `a or b` | cortocircuito | `a \|\| b` |
| `not a` | negación | `!a` |
| `a is b` | igualdad | `a == b` |
| `a isnt b` | desigualdad | `a != b` |
| `x in xs` | membresía | `xs.contains(&x)` |
| `a..b` | range | `a..b` |
| `a..=b` | range inclusive | `a..=b` |
| `a?` | try | `a?` |
| `awaken f` | await | `f.await` |
| `&raw const x` | raw ref | `&raw const x` |
| `&raw mut x` | raw ref mut | `&raw mut x` |

### 64.4 Colecciones y literal patterns

| Azúcar | Forma core | Rust |
|---|---|---|
| `[a, b]` | array | `[a, b]` |
| `[e; n]` | array repetido | `[e; n]` |
| `Vec[a, b]` | vector | `vec![a, b]` |
| `Set[a, b]` | set | `HashSet::from([a, b])` |
| `{ "k": v }` | map | `HashMap::from([("k", v)])` |
| `(a, b)` | tupla | `(a, b)` |
| `(a,)` | tupla de uno | `(a,)` |
| `()` | unit | `()` |
| `@` en patrón | binding | `x @ pat` |
| `ref x` | referencia | `ref x` |
| `ref mut x` | referencia mutable | `ref mut x` |
| `p1 \| p2` | or-pattern | `p1 \| p2` |
| `[first, .., last]` | slice pattern | `[first, .., last]` |
| `0..=9` en patrón | range pattern | `0..=9` |
| `if p = e then a` | if let | `if let p = e { a }` |
| `while p = e` | while let | `while let p = e { … }` |
| `bind p = e else b` | let-else | `let p = e else { b };` |

### 64.5 Errores, iteradores, async y concurrencia

| Azúcar | Forma core | Rust |
|---|---|---|
| `?T` | `Option<T>` | `Option<T>` |
| `!T` | `Result<T, Error>` | `Result<T, Box<dyn Error + Send + Sync>>` |
| `none` | `None` | `None` |
| `some(x)` | `Some(x)` | `Some(x)` |
| `ok(x)` | `Ok(x)` | `Ok(x)` |
| `err(e)` | `Err(e)` | `Err(e)` |
| `?` | early return | `?` |
| `panic(msg)` | panic | `panic!(msg)` |
| `assert(c)` | assert | `assert!(c)` |
| `iter` | `iter()` | `.iter()` |
| `iter_mut` | `iter_mut()` | `.iter_mut()` |
| `into_iter` | `into_iter()` | `.into_iter()` |
| `dream do` | async block | `async { … }` |
| `dream (x) => e` | async closure | `async move \|x\| e` |
| `awaken e` | await | `e.await` |
| `thread.spawn` | thread spawn | `std::thread::spawn` |
| `Arc.new(Mutex.new(x))` | shared state | `Arc::new(Mutex::new(x))` |
| `lock` | lock guard | `.lock().unwrap()` |
| `@@thread_local` | TLS | `thread_local!` |
| `@@shared` | shared static | `static` + `Mutex`/atomics |

### 64.6 Macros, atributos y build

| Azúcar | Forma core | Rust |
|---|---|---|
| `incantation n` | macro_rules | `macro_rules! n { … }` |
| `n!(tokens)` | macro invocation | `n!(tokens)` |
| `$x` | metavariable | `$x` |
| `$(…)*` | repetición | `$(…)*` |
| `$crate` | crate de la macro | `$crate` |
| `unveil incantation` | export | `#[macro_export]` |
| `@@derive(A, B)` | derive | `#[derive(A, B)]` |
| `@@repr(C)` | repr | `#[repr(C)]` |
| `@@cfg(...)` | cfg | `#[cfg(...)]` |
| `@@cfg_attr(...)` | cfg_attr | `#[cfg_attr(...)]` |
| `@@test` | test | `#[test]` |
| `@@should_panic` | test panic | `#[should_panic]` |
| `@@ignore` | test ignore | `#[ignore]` |
| `@@no_mangle` | symbol | `#[no_mangle]` |
| `build.pengu` | build script | `build.rs` |
| `out_dir()` | env var | `std::env::var("OUT_DIR")` |
| `println("cargo:...")` | directive | `println!("cargo:...")` |

### 64.7 Manifiesto y codegen

| PenguScript | Rust/Cargo |
|---|---|
| `Tome.toml` | `Cargo.toml` generado |
| `[tome] name` | `[package] name` |
| `[tome] version` | `[package] version` |
| `[tome] edition` | `[package] edition` |
| `[tome] rust-version` | `[package] rust-version` |
| `[dependencies]` | `[dependencies]` (versiones compatibles) |
| `[[bin]] path = "main.pengu"` | `[[bin]] path = "src/main.rs"` |
| `[[test]] path = "tests/x.pengu"` | `[[test]] path = "tests/x.rs"` |
| `[features]` | `[features]` |
| `[workspace]` | `[workspace]` |
| `[cargo]` | claves passthrough permitidas |
| `main.pengu` | `src/main.rs` |
| `lib.pengu` | `src/lib.rs` |
| `foo.pengu` | `src/foo.rs` |
| `foo/scroll.pengu` | `src/foo/mod.rs` |
| `build.pengu` | `build.rs` |
| `sourcemap.json` | mapa byte/rango Pengu -> Rust |

### 64.8 Invariantes

1. El desugaring preserva el orden de evaluación de izquierda a derecha.
2. No introduce `unsafe` salvo que la construcción lo exija (`curse`, `transmute`,
   `asm`, raw pointer).
3. No oculta asignaciones: `morph` es la única forma de mutación de un binding.
4. No hay asignación dentro de una expresión salvo como sentencia explícita.
5. Las macros expanden tokens, no AST de PenguScript.
6. Un bloque `rust` se copia tal cual; no se desugara.
7. Los nombres generados son deterministas (misma entrada -> mismo Rust).
8. El sourcemap conserva la relación expresión/token con el Rust emitido.

### 64.9 Criterios de aceptación

- [x] Cada azúcar importante tiene fila.
- [x] Las filas incluyen la forma core y el Rust.
- [x] Las transformaciones no cambian la semántica.
- [x] Las construcciones que requieren `unsafe` lo indican.
- [x] El codegen y el manifiesto están cubiertos.

[↑ Volver al índice](#indice)
