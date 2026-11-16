# Plan de STDLIB — PenguScript

Fecha: 2026-11-13
Base: `7a5e856` (B8, sin push)
Especificación vigente: `docs/LANGUAGE.md`, `docs/STDLIB.md` 0.3.0
Inventario de superficie: [`scratch/STDLIB_SURFACE.md`](STDLIB_SURFACE.md)

---

## 0. Cómo leer este plan

El plan no reescribe `docs/STDLIB.md`: lo **corrige y completa fase a fase**. Cada
fase Sx cierra con una actualización del doc normativo y del inventario
`STDLIB_SURFACE.md`. Si el plan y el doc discrepan, gana el doc **después** de la
fase que lo actualiza; mientras tanto, este plan es la referencia de ejecución.

Regla de oro del usuario, que manda sobre todo lo demás:

> No haremos los módulos con los métodos indispensables. Los haremos completos,
> buscando en la web qué métodos tienen otras librerías de otros lenguajes para
> que cada módulo quede completísimo.

Eso significa: ningún módulo se cierra con "lo que pedía el ejemplo". Un módulo se
cierra cuando su superficie cubre el **superconjunto razonable** de Rust
(`std`/`core`), Python 3.12, Go `strings`/`sort`/`os`, Kotlin stdlib y V, filtrado
por lo que el lenguaje puede expresar (sin `unsafe`, sin `dyn`, sin lifetimes
escritas). El protocolo de barrido está en el Anexo B del inventario.

---

## 1. Veredicto: ¿basta Core + Core de auto-hospedaje?

**Sí, con dos matices.** La intuición del usuario es correcta, pero el orden de
trabajo no es el que sugiere el informe de Gate B.

### 1.1 Qué necesita cada hito

| Hito | Módulos necesarios | Módulos que NO hacen falta |
|---|---|---|
| Compilador "funcional" (Gate B sin bloqueos por stdlib) | `integrum`, `floatem`, `verbum`, `bool` (switch), `nexus` (CStr/CString/Ptr), `ambitus` (`args`, `var`) | todo lo demás |
| Auto-hospedaje H3 (el compilador se compila a sí mismo) | lo anterior + `via`, `exsecutor`, `libra`, `iason`, `digestum`, `versio`, `terminus`, `globus`, `archivum`, `fluxus`, `proba` | `rete`, `somnium`, `structura` (salvo `BTreeMap` si se usa) |
| Apps de usuario (cookbook, ejemplos completos) | todo Core + `vinculum`, `frenum`, `cellula`, `funis`, `structura` | — |
| Red | `rete` | **nunca para el compilador** |

`scratch/COMPILER_PLAN.md` §10 ya lo dice explícitamente: "`std.net` no es
necesario para el compilador (solo `git` externo)". `rete` queda fuera del
camino crítico y se decide en S10.

### 1.2 El matiz que el informe de Gate B no dice

Los 10 programas bloqueados no fallan solo por métodos. Fallan por **tres cosas
distintas**, y la más cara no es la que el informe destaca:

1. **No existe la std.** No hay ni un `std/*.pengu` en el repo (los 59 `.pengu`
   del árbol están en `scratch/legacy/examples_rc1/`). `summon std::ffi::CStr` no
   resuelve porque no hay módulo `std`.
2. **No hay cargador multi-archivo.** `crates/pengu-build/src/lib.rs:112-140` lee
   exactamente un archivo (`main.pengu` o `lib.pengu`). `parse_program` produce un
   único `Program`; `lower_program` (`crates/pengu-hir/src/lower.rs:33`) no conoce
   más fuente que esa. Sin esto, ningún `std` puede existir, por completo que sea
   el doc.
3. **No hay binding de `abi "pengu"`.** `emit_foreign`
   (`crates/pengu-codegen/src/codegen.rs:423-450`) emite literalmente
   `unsafe extern "pengu" { ... }`, que **no es Rust válido**. Y `ritual Int { ... }`
   emitiría `impl i32 { ... }`, tampoco válido. La capa que convierte declaraciones
   de std en código Rust no existe.

Orden real de dependencias: **2 → 1 → 3 → métodos**. El informe de Gate B mide el
síntoma (faltan `trim`/`sqrt`/`ffi`), no la causa.

### 1.3 Respuesta corta

- Core + Core de auto-hospedaje es la lista correcta de módulos.
- Pero antes hay que construir **la infraestructura que hace posible cualquier
  std** (fase S0), que no está en `docs/STDLIB.md` ni en `COMPILER_PLAN.md`.
- `std::ffi` y `std::env` no son "dos módulos más": son la prueba de que el
  binding `abi "pengu"` y los alias de módulo funcionan. Por eso S0 los incluye
  como caso de prueba mínimo, y S6 los cierra completos.

---

## 2. Auditoría: qué hay y qué no

### 2.1 Estado del compilador (verificado con `grep`/`sed` en esta sesión)

| Pieza | Estado | Evidencia |
|---|---|---|
| Parser | ✅ completo | `crates/pengu-syntax/src/parser.rs` (3261 líneas) |
| HIR / módulos `scroll` | ✅ un archivo | `crates/pengu-hir/src/lower.rs:33`, `:2113` |
| Carga `.d.pengu` | ✅ | `lower_declaration`, `crates/pengu-hir/src/lower.rs:41` |
| Checker de métodos | 🔶 tabla ad-hoc | `method_signature`, `crates/pengu-types/src/check.rs:2137` |
| Codegen de métodos | ✅ emite `recv.m(args)` | `crates/pengu-codegen/src/codegen.rs:965-990` |
| Codegen de `impl` | ✅ para tipos de usuario | `emit_impl`, `codegen.rs:533` |
| Codegen `abi "pengu"` | ❌ roto | `emit_foreign`, `codegen.rs:423` → `unsafe extern "pengu"` |
| Carga multi-archivo | ❌ | `pengu-build/src/lib.rs:112-140` |
| `std/` | ❌ no existe | `ls std/` → no such directory |
| Tabla de alias `std.int`→`integrum` | ❌ | no hay ocurrencias de alias de módulo en `crates/` |
| Prelude | parcial | `Show`, `print`, `format`, `Vec/Map/Set/Option/Result/String/Box/Ordering` |
| Tests | 519 ✅ | `cargo test --workspace` |

### 2.2 Lo que el doc ya especifica (y no hay que rediseñar)

`docs/STDLIB.md` (1928 líneas) define 31 módulos con firmas, tipos y semántica:
`integrum`, `floatem`, `littera`, `verbum`, `capsa`, `tabula`, `fasciculus`,
`numerus`, `fluxus`, `via`, `exsecutor`, `ambitus`, `tempus`, `nexus`,
`vinculum`, `frenum`, `cellula`, `proba`, `opera`, `funis`, `structura`,
`libra`, `iason`, `digestum`, `versio`, `terminus`, `globus`, `archivum`, `rete`,
`somnium` (diferido). La §32.2 fija la estrategia:

> los métodos que requieren intrinsics (`sqrt`, `sin`, `push`, `lock`) se declaran
> en `.d.pengu` con `abi "pengu"` y el backend los resuelve a Rust. Los métodos
> que se pueden escribir en PenguScript puro (`trim`, `split`, `lerp`) se
> implementan en `.pengu` para dogfooding.

El plan adopta esa estrategia y la operacionaliza. Lo único que corrige es el
reparto concreto (qué es intrínseco y qué es puro), que la §32.2 deja abierto.

### 2.3 Contradicciones de la spec que hay que resolver en S0

1. **`summon` vs. métodos de primitivo.** `LANGUAGE.md:1685` dice que los métodos
   de iterador viven en `std.iter` y se importan. Pero el ejemplo normativo de
   `LANGUAGE.md:2060-2090` usa `"  hola  ".trim()` y `42.is_even()` **sin
   `summon`**. Decisión: **los métodos inherentes de primitivos y de tipos de la
   prelude están siempre en scope**; solo los *tipos* y *funciones libres* de std
   requieren `summon`. Es como Rust: `Vec::push` no necesita `use`.
2. **`std::env` no es un módulo.** `docs/STDLIB.md` §32.1 mapea `std.env` →
   `ambitus`. Pero `find_module_path` no tiene aliases. Decisión: tabla estática
   de alias de módulo en el resolvedor (§4.2).
3. **`abi "pengu"` y `.d.pengu`.** El doc dice que los intrínsecos se declaran en
   `.d.pengu`; pero un `.d.pengu` no genera código y `PGS-E2024` exige
   implementación en la misma crate. Decisión: los intrínsecos se declaran
   **dentro de `std/*.pengu`** con `foreign abi "pengu"`, y la "implementación"
   es el módulo Rust `__pengu_std` que el codegen inyecta. `PGS-E2024` se satisface
   por construcción para los nombres declarados en el manifiesto de intrínsecos.

---

## 3. Arquitectura de la std

### 3.1 Capas

```
┌──────────────────────────────────────────────────────────────┐
│ std/*.pengu            firmas + cuerpos en PenguScript       │  fuente de verdad
│   ritual Int / Float / Str / Vec ...                          │
│   fn parse(...) -> Result[...]                                │
│   foreign abi "pengu"  fn str_trim(s: &Str) -> &Str          │  (intrínseco)
└──────────────────────────────────────────────────────────────┘
            │ lower_program + check_crate (normal)
            ▼
┌──────────────────────────────────────────────────────────────┐
│ pengu-codegen                                                 │
│   · cuerpo Pengu puro  → fn Rust normal (dogfooding)          │
│   · ritual de primitivo → fn libre __pengu_<tipo>_<m>(self,…) │
│   · abi "pengu"        → llamada a __pengu_std::<mod>::<n>    │
│   · método 1:1 con Rust → recv.m(args) (ya funciona)          │
└──────────────────────────────────────────────────────────────┘
            ▼
┌──────────────────────────────────────────────────────────────┐
│ __pengu_std.rs   (Rust, generado/embebido por codegen)        │
│   ~180 funciones thin: str_trim, vec_push, sqrt, args, …      │
│   sin `unsafe` salvo el bloque FFI de `nexus`                 │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Reglas de binding (D1–D9)

- **D1 — La std es fuente PenguScript.** Toda firma vive en `std/*.pengu`. El
  compilador la baja, la chequea y la codegena como código de usuario. No hay un
  "registro de firmas" paralelo en Rust como fuente de verdad.
- **D2 — Tres clases de cuerpo.**
  - *(a) puro*: se escribe en PenguScript y se compila normal (`abs`, `is_even`,
    `clamp`, `capitalize`, `lerp`, `versio`, `iason`, `globus`…). Objetivo ≥ 55 %
    de los métodos.
  - *(b) intrínseco*: `foreign abi "pengu" fn …` + entrada en
    `pengu-codegen/src/std_rt.rs` (tabla nombre → cuerpo Rust). Para todo lo que
    toca el SO, el allocador, floats o el runtime (`sqrt`, `push`, `read_file`,
    `now`, `args`, `sha256`).
  - *(c) paso directo*: cuando el nombre del método coincide 1:1 con Rust y el
    receptor ya es el tipo Rust correcto (`Str`→`&str`, `Vec`→`Vec`), el codegen
    emite `recv.m(args)` como hoy. Se declara igual en el ritual con cuerpo
    intrínseco trivial (`str_trim(@)`) para que el checker vea la firma. **No es
    una cuarta vía**: es una optimización del intrínseco.
- **D3 — Primitivos no generan `impl`.** `ritual Int/Float/Str/Bool/Char` se
  emiten como funciones libres `__pengu_prim_<tipo>_<m>(recv, args…)` y las
  llamadas se reescriben a `__pengu_prim_int_abs(x)`. Vale para cualquier
  primitivo y evita tocar el emisor de `impl`.
- **D4 — `abi "pengu"` no emite `extern`.** `emit_foreign` omite los bloques
  `"pengu"` y las llamadas se redirigen a `__pengu_std`. Un nombre declarado sin
  entrada en la tabla = error de compilación del propio compilador (test de
  cobertura, no diagnóstico de usuario). No se añaden códigos `PGS-*`: el
  presupuesto de 160 está cerrado (`COMPILER_PLAN.md` §1.2).
- **D5 — Alias de módulo estáticos.** `find_module_path` sustituye prefijos según
  la tabla de `docs/STDLIB.md` §32.1 antes de resolver.
- **D6 — `std` no se puede sombrear.** `scroll std` en código de usuario es
  `PGS-E2005` (nombre reservado), igual que `crate`/`super`/`self`.
- **D7 — Carga determinista y hermética.** La std se embebe con `include_str!` en
  la crate del compilador; no se lee del disco en tiempo de compilación del
  usuario. Orden de módulos = orden declarado en `std/mod.pengu` (índice), no
  orden de `read_dir`.
- **D8 — Sin `unsafe` en la std de usuario.** `#![forbid(unsafe_code)]` sigue
  vigente en las crates; el único `unsafe` es el `extern "C"` de `nexus` en
  `__pengu_std`, aislado en `std_rt/ffi.rs`.
- **D9 — Toda fase actualiza el doc.** El criterio de salida incluye PR de
  `docs/STDLIB.md` con las firmas finales; `STDLIB_SURFACE.md` marca ✅ por
  método (una fila por método, no por módulo).

### 3.3 Estructura de archivos

```
std/
  mod.pengu            -- índice: scroll integrum; scroll floatem; …
  integrum.pengu
  floatem.pengu
  littera.pengu
  verbum.pengu
  capsa.pengu
  tabula.pengu
  fasciculus.pengu
  numerus.pengu
  fluxus.pengu
  proba.pengu
  opera.pengu
  via.pengu
  exsecutor.pengu
  ambitus.pengu
  tempus.pengu
  nexus.pengu          -- FFI: CStr, CString, CChar, Ptr
  vinculum.pengu
  frenum.pengu
  cellula.pengu
  funis.pengu
  structura.pengu
  libra.pengu
  iason.pengu
  digestum.pengu
  versio.pengu
  terminus.pengu
  globus.pengu
  archivum.pengu
  rete.pengu           -- diferido (S10)
  somnium.pengu        -- diferido explícito
```

Cada archivo declara `scroll <nombre> { … }` con el nombre latino. Los alias
(`std::int`, `std::fs`, `std::env`…) los resuelve D5.

---

## 4. S0 — Infraestructura (prerrequisito de todo)

**Objetivo:** que un programa de usuario pueda usar `std` y que el código de std
llegue a Rust válido. Sin esta fase, S1–S10 no tienen dónde escribirse.

### 4.1 Carga multi-archivo

- `crates/pengu-build/src/lib.rs:112-140`: localizar el árbol de fuentes del
  paquete (`src/**/*.pengu` + `std/` embebida) y construir **un** `Program`
  sintético envolviendo cada archivo en `scroll <stem> { … }`.
- Regla de módulo: `src/foo.pengu` → módulo `foo`; `src/foo/bar.pengu` → `foo::bar`.
  `main.pengu`/`lib.pengu` son la raíz. Colisión de stems = diagnóstico existente
  `PGS-E2005`.
- La std se envuelve en `scroll std { … }` y se antepone a los items del usuario.
- `pengu-project` gana `fn sources(root) -> Vec<SourceFile>` con orden
  determinista (BTreeMap por ruta relativa).
- Test: `crates/pengu-build/tests/multifile.rs` — dos archivos que se importan
  mutuamente vía `summon`.

### 4.2 Alias de módulo (D5)

- `crates/pengu-hir/src/lower.rs:2113` `find_module_path`: aplicar
  `std_alias(path)` antes de resolver. Tabla en `pengu-hir/src/std_alias.rs`,
  generada a mano desde `docs/STDLIB.md` §32.1.
- `std::env::args` ⇒ `std::ambitus::args`. `std::ffi::CStr` ⇒ `std::nexus::CStr`.
- Test: `summon std::env::args` y `summon std::ffi::CStr` resuelven al `DefId`
  correcto; un alias debe apuntar a un módulo existente (test de tabla completa).

### 4.3 Binding `abi "pengu"` (D4)

- `crates/pengu-codegen/src/codegen.rs:423` `emit_foreign`: separar por abi;
  `"pengu"` no se emite como `extern`.
- Nuevo `crates/pengu-codegen/src/std_rt/mod.rs`:
  ```rust
  pub struct Intrinsic { pub module: &'static str, pub name: &'static str,
                         pub rust: &'static str } // plantilla con $0/$1/$args
  pub fn lookup(module: &str, name: &str) -> Option<&'static Intrinsic>
  ```
- `call_name` (`codegen.rs:1342`) y `LExpr::Method` (`codegen.rs:965`) detectan
  `foreign_fns` con abi `"pengu"` y emiten `__pengu_std::<module>::<name>(args)`.
- El módulo `__pengu_std` se inyecta una vez por crate generada, con
  `include_str!` de `std_rt/runtime.rs` y las funciones de intrínsecos.
- Test de cobertura: todo `foreign abi "pengu"` declarado en `std/` tiene entrada
  en la tabla, y viceversa (falla el build si no).

### 4.4 Primitivos sin `impl` (D3)

- `emit_impl` (`codegen.rs:533`): si `imp.target` es un primitivo, emitir
  `fn __pengu_prim_<ty>_<m>(…)` en lugar de `impl i32`.
- `LExpr::Method` (`codegen.rs:965`): si el `def` pertenece a un `impl` de
  primitivo, emitir la llamada libre.
- `Receiver::Own` ⇒ primer parámetro por valor; `@` ⇒ `&T`; `@mut` ⇒ `&mut T`.
- Test: `ritual Int { abs }` + `(-5).abs()` compila y ejecuta.

### 4.5 Checker

- `method_signature` (`crates/pengu-types/src/check.rs:2137`): consultar primero
  `krate.methods` (impls cargados, incluidos los de `std`), y dejar la tabla
  hardcodeada **solo** para los métodos de la prelude (`len`, `push`? no: `push`
  viene de std). Documentar en el módulo qué queda hardcodeado y por qué.
- Test: un método de std con firma nueva (`Str.split`) chequea sin tocar la tabla.

### 4.6 Harness de conformidad

- `crates/pengu-build/tests/std_conformance.rs`: recorre
  `tests/std/<modulo>/<caso>.pengu` + `.expected`, ejecuta el binario y compara
  stdout. Un caso por método es el objetivo de S1–S9 (≈ 900 casos).
- `cargo run -p pengu-build --example std_matrix` imprime la matriz
  ✅/🔶/❌ por módulo (entrada para `STDLIB_SURFACE.md`).

### 4.7 Criterio de salida de S0

```sh
cargo test --workspace                 # 519 + nuevos
cargo clippy --workspace --all-targets -- -D warnings
cargo fmt --all -- --check
```

- `summon std::ffi::CStr` resuelve y genera Rust que compila con rustc (aunque el
  cuerpo de `CStr` esté vacío todavía).
- `42.is_even()` compila y ejecuta (`is_even` escrito en Pengu puro en
  `std/integrum.pengu`).
- `(-5).abs()` ídem.
- Ningún `unsafe extern "pengu"` en la salida.
- Test de cobertura de intrínsecos verde.

---

## 5. Superficie: qué se implementa

El detalle método a método está en [`scratch/STDLIB_SURFACE.md`](STDLIB_SURFACE.md).
Resumen de magnitudes (doc actual → objetivo tras deltas):

| Módulo | Métodos en doc | Delta | Objetivo | Intrínsecos |
|---|---:|---:|---:|---:|
| `integrum` | ~60 | +18 | 78 | 40 |
| `floatem` | ~55 | +12 | 67 | 55 |
| `littera` | ~37 | +6 | 43 | 20 |
| `verbum` | ~80 | +34 | 114 | 45 |
| `capsa` | ~80 | +16 | 96 | 30 |
| `tabula` | ~30 | +6 | 36 | 16 |
| `fasciculus` | ~25 | +6 | 31 | 14 |
| `numerus` | ~60 | +20 | 80 | 30 |
| `fluxus` | ~20 | +8 | 28 | 12 |
| `via` | ~100 | +14 | 114 | 45 |
| `exsecutor` | ~30 | +6 | 36 | 18 |
| `ambitus` | ~18 | +2 | 20 | 12 |
| `tempus` | ~45 | +10 | 55 | 20 |
| `nexus` | ~20 | +14 | 34 | 20 |
| `vinculum` | ~30 | +4 | 34 | 20 |
| `frenum` | ~22 | +8 | 30 | 16 |
| `cellula` | ~21 | +6 | 27 | 14 |
| `proba` | ~11 | +4 | 15 | 4 |
| `opera` | ~12 | +2 | 14 | 0 |
| `funis` | ~50 | +30 | 80 | 25 |
| `structura` | 5 tipos | +5 tipos completos | 5×~30 | 25 |
| `libra` | ~25 | +15 | 40 | 6 |
| `iason` | ~25 | +15 | 40 | 4 |
| `digestum` | 6 | +6 | 12 | 12 |
| `versio` | ~15 | +10 | 25 | 2 |
| `terminus` | ~30 | +12 | 42 | 30 |
| `globus` | 4 | +4 | 8 | 4 |
| `archivum` | ~15 | +8 | 23 | 18 |
| `rete` | ~40 | +10 | 50 | 45 |
| **Total** | **~950** | **~330** | **~1280** | **~640** |

El número de intrínsecos parece alto porque incluye los métodos 1:1 con Rust
(clase (c) de D2), que son mecánicos: una línea de tabla cada uno.

---

## 6. Fases

Cada fase: **1–3 sesiones**, PR único, doc actualizado, matriz de conformidad
actualizada. Orden pensado para que Gate B se desbloquee en S6 y el auto-hospedaje
sea posible al final de S9.

### S0 — Infraestructura
- Alcance: §4 completo.
- Depende de: nada.
- Cierre: los 7 puntos de §4.7.
- Riesgo: la carga multi-archivo toca el driver y el sourcemap (hoy todos los
  spans usan `FileId(0)`). Mitigación: `FileId` por archivo desde el principio;
  `SourceMap` guarda `(línea, Span)` y `Span` ya lleva `FileId`
  (`crates/pengu-codegen/src/codegen.rs:27-30`), así que el remapeo de errores
  sigue funcionando si cada archivo tiene su `FileId` y `remap_rustc_diagnostics`
  resuelve el `FileId` del span.

### S1 — Núcleo de primitivos
- Módulos: `bool`, `integrum`, `floatem`, `littera`, `opera`.
- Contenido: los 78 de `integrum` (checked/wrapping/saturating/overflowing
  completos, bits, bytes, radix), los 67 de `floatem` (trig, hiperbólicas,
  `next_up/down`, `classify`, `to_bits/from_bits`, `total_cmp`), los 43 de
  `littera` (`is_ascii_*`, `to_digit`, `len_utf8/16`, `encode_utf8`), y `opera`
  (los `ritual Int/Float for Add/Sub/…`).
- Cierre: `tests/std/primitivos/` verde; `300 as U8` y `-1 as U8` siguen
  compilando; `Float.sqrt` ejecuta y coincide con `f64::sqrt` en 1000 valores
  aleatorios (diferencial).
- Riesgo: `to_bits`/`from_bits` requieren `Int` de 64 bits; hoy `Int` = `i32`
  (`COMPILER_PLAN.md` §5.3). Decisión: `to_bits` devuelve `I64` de `std.int` o se
  aplaza a S8. **Decidir en S1, no después.**

### S2 — Texto
- Módulo: `verbum` (114 métodos) + `Str`/`String`.
- Contenido: todo Unicode-consciente (`chars`, `graphemes`?, `len_utf8`), búsqueda
  (`find`, `rfind`, `matches`, `match_indices`, `split_once`, `rsplit_once`,
  `split_inclusive`), transformación (`capitalize`, `title`, `swapcase`,
  `casefold`, `expandtabs`, `zfill`, `center/ljust/rjust`), predicados
  (`is_alpha/digit/alnum/space/lower/upper/title/identifier/printable/decimal`),
  Go (`cut`, `cut_prefix`, `cut_suffix`, `index_any`, `contains_any`, `fields`,
  `replace_all`, `equal_fold`), Kotlin (`chunked`, `windowed`, `if_empty`,
  `if_blank`, `substring_before/after`, `common_prefix_with`).
- Cierre: 114 casos; `"  hola  ".trim()`, `"a,b,c".split(",")`, `"x".repeat(3)`
  ejecutan; `format("#{s}")` con `Str` y `String` no confunde tipos (bloqueo 321
  de Gate B).
- Riesgo: `Str` es `&str`; los métodos que devuelven substrings deben devolver
  `&Str` con la misma lifetime implícita, y el checker no tiene lifetimes
  escritas. Si el borrow checker de Pengu no lo permite, se devuelve `String` y se
  documenta el coste. **Decisión en S2, con test de `split` que sobreviva al
  scope.**

### S3 — Colecciones
- Módulos: `capsa`, `tabula`, `fasciculus`.
- Contenido: 96 + 36 + 31 métodos, incluidos `Entry`
  (`or_insert`/`or_insert_with`/`or_default`/`and_modify`/`key`/`value`),
  `retain`, `drain`, `splice`, `chunk_by`, `windows`, `chunks_exact`,
  `binary_search_by`, `sort_by_key`, `dedup_by_key`, `select_nth_unstable`,
  operaciones de conjunto completas.
- Cierre: 163 casos; `Vec`/`Map`/`Set` de `LANGUAGE.md` §10 ejecutan sin
  `summon` (D-prelude); `for (k, v) in map` sigue funcionando.
- Riesgo: `Entry` es un `rune` opaco (nota §32), así que `or_insert` no puede
  devolver `&mut V` sin lifetimes escritas. Solución: `Entry` con métodos que
  *mutan y devuelven* el valor por copia (`or_insert(v) -> V` con `V: Copy`) o
  `or_insert_with([V] -> V)`. Documentar el límite; no fingir un `&mut`.

### S4 — Soporte
- Módulos: `numerus`, `fluxus`, `proba`.
- Contenido: 80 + 28 + 15. `numerus` incluye `erf/erfc/gamma/lgamma/beta`,
  `isclose`, `lerp`, `smoothstep`, `wrap`, `ping_pong`, `move_towards`,
  `next_power_of_two`, `div_ceil/div_floor`, estadística básica sobre `&[Float]`.
- `fluxus`: `Reader`/`Writer` como `pact`, `BufReader/BufWriter`, `read_line`,
  `stdin/stdout/stderr`, `flush`.
- `proba`: `assert*`, `fail`, `skip`, `should_panic`, `TestContext`; integración
  con `pengu test` (B7).
- Cierre: 123 casos; `print`/`format`/`eprint` no regresan; `pengu test` reporta
  1 pass / 1 fail / 1 skip correctamente.

### S5 — Frontera con el sistema operativo
- Módulos: `via`, `exsecutor`, `ambitus`, `tempus`.
- Contenido: 114 + 36 + 20 + 55. `via` completo (File/Path/PathBuf/Metadata/
  DirEntry/WalkOptions/walk/OpenOptions/symlink/hard_link/canonicalize/tempfile),
  `exsecutor` (Command/Child/ExitStatus/Stdio/Output/which/wait_with_output),
  `ambitus` (args/var/vars/current_dir/temp_dir/home_dir/current_exe/consts),
  `tempus` (Instant/Duration/SystemTime/sleep/UNIX_EPOCH).
- Cierre: 225 casos; los bloques 3798 (`std::env`) y 3951 (`std::fs`) de Gate B
  ejecutan; `via.walk` recursivo con `max_depth` y `follow_links`.
- Riesgo: es la fase con más `unsafe` potencial (rutas OS). `std::fs` de Rust es
  seguro; `tempfile` requiere creación atómica — se implementa con
  `OpenOptions::create_new` en bucle, sin `unsafe`.

### S6 — FFI y cierre de Gate B
- Módulos: `nexus` (34).
- Contenido: `CStr` (`from_ptr` solo en `.d.pengu`, `to_str`, `to_bytes`,
  `to_string_lossy`), `CString` (`new`, `as_c_str`, `into_raw`, `from_raw`,
  `into_bytes`), `CChar`, `Ptr[T]` (null, is_null, cast), `OsStr`/`OsString`.
- Cierre: **Gate B sin bloqueos por stdlib**. Los 10 programas completos de
  `scratch/GATE_B_CORPUS.md` compilan y ejecutan (o quedan clasificados como
  "no ejecutables por decisión", con la razón escrita: `ConfigError`/
  `read_config`/`AppError`/`load` son símbolos de usuario, no de std — eso se
  arregla en el ejemplo, no en la std).
- Este es el hito que el usuario pidió: compilador funcional y tests verdes.

### S7 — Iteradores y colecciones avanzadas
- Módulos: `funis` (80), `structura` (`VecDeque`, `BTreeMap`, `BTreeSet`,
  `BinaryHeap`, `LinkedList`).
- Contenido: la cadena completa de adaptadores (`map`, `filter`, `filter_map`,
  `flat_map`, `flatten`, `zip`, `enumerate`, `chain`, `take_while`, `skip_while`,
  `step_by`, `rev`, `peekable`, `scan`, `inspect`, `cycle`, `fuse`, `try_*` fuera),
  terminales (`fold`, `reduce`, `sum`, `product`, `count`, `last`, `nth`,
  `position`, `find`, `find_map`, `any`, `all`, `min/max*`, `collect`, `partition`,
  `unzip`, `for_each`, `join`), y constructores (`empty`, `once`, `repeat`,
  `successors`, `from_iter`, `lines`, `chars`, `split`).
- Cierre: 80 + 5 tipos; `LANGUAGE.md:1685` deja de ser falso (los métodos de
  iterador existen tras `summon std::iter`).
- Riesgo: `Iter[T]` es un `rune` opaco sin `dyn`; los adaptadores se bajan a
  closures de Rust (ya soportado) pero el tipo `Iter` debe envolver
  `Box<dyn Iterator>`… prohibido. Alternativa: `Iter[T]` como enum de adaptadores
  (`enum __Iter { Map(…), Filter(…) }`) o monomorfización por uso. **Es el mayor
  riesgo técnico del plan; se decide en S7 con prototipo de 1 día.**

### S8 — Auto-hospedaje textual
- Módulos: `libra` (TOML, 40), `iason` (JSON, 40), `digestum` (12), `versio` (25).
- Contenido: parsers y serializadores **en Pengu puro** (dogfooding real), con
  `digestum` como intrínseco (`sha1`, `sha256`, `sha512`, `md5`, `hmac_*`,
  `hex_*`, `base64_*`). `libra` con fecha/hora TOML completa; `iason` con
  números, escapes, `pretty`.
- Cierre: los 4 módulos pasan un corpus de ficheros reales (los `Cargo.toml` de
  exemplos, `.json` de fixtures) comparados contra `toml`/`serde_json` de Rust
  como oráculo (test diferencial offline, sin dependencia en runtime).
- Riesgo: parsers en Pengu puro exponen cualquier carencia del lenguaje
  (strings, `while`, `match`). Es intencional: es el detector de deuda del
  compilador. Si un parser necesita algo que el lenguaje no tiene, se anota y se
  resuelve en el compilador, no con un intrínseco.

### S9 — Auto-hospedaje de sistema
- Módulos: `terminus` (42), `globus` (8), `archivum` (23), `vinculum` (34),
  `frenum` (30), `cellula` (27).
- Cierre: `pengu` puede leer/escribir TOML, hashear, comparar versiones, pintar
  en terminal, expandir globs y desempaquetar un `.tar.gz`. Es la lista de
  `COMPILER_PLAN.md` §10, completa.
- Hito: **H3 desbloqueado** (bootstrap del compilador).

### S10 — Cierre y decisión sobre `rete`
- `rete` (50): se decide entre implementar (TcpListener/Stream, UdpSocket, TLS,
  HTTP cliente) o declararlo diferido con justificación. Si se implementa, es una
  fase propia S11 con su propio riesgo (TLS sin deps es un proyecto en sí).
- Conformidad final: matriz 100 %, doc `docs/STDLIB.md` 0.4.0, `CHANGELOG`,
  `scratch/STDLIB_SURFACE.md` cerrado.

---

## 7. Tests

| Nivel | Qué | Dónde |
|---|---|---|
| Unitario | cada intrínseco contra su equivalente Rust | `crates/pengu-codegen/src/std_rt/tests.rs` |
| Conformidad | 1 `.pengu` + `.expected` por método | `crates/pengu-build/tests/std/` |
| Diferencial | std de Pengu vs. Rust/Python en datos generados | `tests/std/diff/` |
| Corpus | los 146 bloques de Gate B | `crates/pengu-build/tests/gate_b_corpus.rs` |
| Dogfooding | std compilada por el propio compilador | `tests/std/bootstrap.rs` |

Regla: **un método sin test no está implementado**. El test de conformidad es la
definición de "hecho" de cada fila de `STDLIB_SURFACE.md`.

---

## 8. Riesgos

| # | Riesgo | Impacto | Mitigación |
|---|---|---|---|
| R1 | Carga multi-archivo rompe spans/sourcemaps | Alto | `FileId` por archivo desde S0; test de span por archivo |
| R2 | `ritual` de primitivo no se puede codegenar sin tocar `emit_impl` | Alto | D3 (fn libre) aislado en S0, con test antes de escribir std |
| R3 | `Str` devolviendo `&Str` sin lifetimes escritas | Alto | Decidir en S2: `&Str` si el borrow checker lo permite, si no `String` documentado |
| R4 | `Iter[T]` sin `dyn` | Alto | Prototipo de enum de adaptadores en S7 antes de comprometer 80 métodos |
| R5 | 1280 métodos es un volumen enorme | Medio | Fases de 1–3 sesiones; los métodos mecánicos (clase c) se generan con script y se revisan |
| R6 | El doc y la implementación divergen | Medio | D9: PR de doc por fase; matriz generada, no escrita a mano |
| R7 | `unsafe` se cuela en `nexus`/`via` | Alto | D8: `forbid(unsafe_code)` en todas las crates; `unsafe` solo en `std_rt/ffi.rs` con `#![allow]` local y revisión |
| R8 | Auto-hospedaje descubre carencias del lenguaje en S8 | Medio | Es el objetivo: registrar cada carencia como issue de compilador, no parchear con intrínsecos |

---

## 9. No-objetivos

- **No** se implementa `std.async`/`somnium` (diferido en `COMPILER_PLAN.md`).
- **No** se añaden códigos `PGS-*` nuevos (presupuesto cerrado).
- **No** se introduce `dyn`/`unsafe`/lifetimes escritas en la superficie.
- **No** se reescribe `docs/STDLIB.md` desde cero: se parchea por fase.
- **No** se implementa `rete` en el camino crítico.

---

## 10. Seguimiento

| Fase | Estado | PR | Gate B | Notas |
|---|---|---|---|---|
| S0 | ✅ | | | infraestructura de carga + `abi "pengu"` |
| S1 | ✅ | | | `integrum`, `floatem`, `littera`, `opera` y `veritas` (Bool) cerrados |
| S2 | ✅ | | bloqueo 321 | `verbum` (50 `Str` + 22 `String`) |
| S3 | ✅ | | | `capsa`, `tabula` y `fasciculus` como paso directo a Rust |
| S4 | ✅ | | | `numerus`, `fluxus` y `proba` |
| S5 | ✅ | | bloqueo 3798 | `via`, `exsecutor`, `ambitus`, `tempus` (otra sesión) |
| S6 | ✅ | | **Gate B sin bloqueos de stdlib** | `nexus` completo (`CString` + `CStr`), `curse` verificado de punta a punta, `match` exhaustivo sin aristas falsas |
| S7 | ✅ | | | **S7a ✅** `funis` completo (34 adaptadores, `chars`/`bytes`/`char_indices`, `Box::new` para iteradores guardables); **S7b ❌** `structura` bloqueada por `rune Iter[T]` (N36) y genéricos con `Ord` (N59) |
| S8 | ✅ | | | `versio`, `digestum`, `iason`, `libra`: cerrados en S8 con SHA-512/HMAC, comparación profunda de JSON, mutadores de JSON, tablas en línea y fechas en TOML, y requisitos con `||`/comodines en SemVer |
| S9 | ✅ | | | `terminus`, `globus`, `cellula` |
| S10 | ✅ | | | `rete` (TCP) |
| S11 | ✅ | | | `libra`, `archivum`, `match` anidado (N48) |
| — | 🔄 | | A4 (bloqueos 321/499) | coerción `Str` → `String` pendiente |

> **Nota (2026-11-14).** Las fases S5–S11 las ejecutó otra sesión (commits `8e7cee4` …
> `c82b149`, ver `scratch/STATUS.md`). Esta tabla se actualiza para reflejar el estado real.
> El trabajo posterior (alias `std::*` y llamadas cualificadas por módulo) está en
> `scratch/GATE_B_CORPUS.md` y `scratch/LIMITATIONS_AUDIT.md` §3.1; con ello Gate B bajó a
> 55 compilados y 4 bloqueos completos. Con la tanda T1–T6 bajó a 58 compilados y, tras
> cerrar S6 en esta sesión (y corregir el ejemplo §2.7 de `docs/LANGUAGE.md`, que estaba
> mal tipado), el corpus queda en **59 compilados y 3 bloqueos**, todos de ejemplos y
> ninguno de stdlib.

Leyenda: ⬜ pendiente · 🔄 en curso · ✅ cerrado · ❌ bloqueado.

---

## 11. Registro de implementación

### S0 — cerrado

Lo que existe hoy en el repo:

| Pieza | Dónde | Notas |
|---|---|---|
| Crate de la std | `crates/pengu-std/src/lib.rs` | `std_program()` (OnceLock), `with_std()`, `defines_std()`. Embebe los `.pengu` con `include_str!` (D7). |
| Fuente de la std | `std/integrum.pengu` | `scroll integrum` dentro de `scroll std`; se compone como texto y se parsea una vez. |
| Fusión con el usuario | `crates/pengu-hir/src/lower.rs:33` | `lower_program` hace `let program = pengu_std::with_std(program)` antes de bajar. |
| `abi "pengu"` | `crates/pengu-hir/src/lower.rs:809` | Permitido **solo** en `std` (si no, `PGS-E1210`); sin comprobación `is_ffi_type` (`PGS-E1604`) y sin exigir `curse`. |
| Codegen de intrínsecos | `crates/pengu-codegen/src/codegen.rs` | `emit_foreign` salta `pengu`; las llamadas se reescriben a `crate::__pengu_std::<nombre>`. |
| Codegen de primitivos | `crates/pengu-codegen/src/codegen.rs` (`emit_primitive_method`) | `ritual Int` se emite como `pub fn <m>(__self: i32, …)`; `self_name()` devuelve `__self` en los 4 puntos de emisión del receptor. |
| Runtime | `crates/pengu-codegen/src/std_rt.rs` | 51 funciones Rust; se emite como `mod __pengu_std { … }` (D4). |
| Visibilidad | `HirCrate::is_std_module` | Los módulos de `std` se emiten `pub mod` para que `crate::std::integrum::abs` sea alcanzable. |
| Checker | `crates/pengu-types/src/check.rs` | El receptor `self` ya no dispara `PGS-W1101`; `IntVar`/`FloatVar` resuelven a los métodos de `Int`/`Float`; `abi "pengu"` exento de `PGS-E1602`. |

Consecuencia: **todo programa pasa por la stdlib**, así que los tests que contaban
módulos/items/bodies crudos ahora filtran por `krate.is_std_module(...)`
(`crates/pengu-hir/tests/names.rs`, `crates/pengu-lir/tests/control.rs`).

### S1 — `integrum` cerrado

- Superficie: **66 métodos** de `Int` (los 63 de `STDLIB.md` §2 más `to_string`,
  `div_ceil`, `unsigned_abs`, `is_positive`, `is_negative`, `digits`), y **51
  intrínsecos** `foreign "pengu"`.
- Cuerpo puro (dogfooding): `abs`, `min`, `max`, `clamp`, `signum`, `is_even`,
  `is_odd`, `is_positive`, `is_negative`, `gcd`, `lcm`, `factorial`.
- Intrínsecos con detalle no obvio:
  - `is_power_of_two`/`next_power_of_two`/`checked_next_power_of_two` se
    implementan a mano: Rust solo los tiene para enteros sin signo.
  - `div_ceil` se implementa a mano: `i32::div_ceil` sigue detrás de
    `int_roundings` (inestable).
  - `saturating_div` usa `i32::saturating_div` (estable desde 1.58; la MSRV del
    workspace es 1.85, sin problema).
- Tests: `crates/pengu-std` (parseo, fusión, superficie), `crates/pengu-codegen`
  (`std_integrum_methods_compile_and_run`, `std_integrum_signed_helpers_are_minimal`),
  más la suite existente (que ahora arrastra la std en cada programa).
- Diferido y por qué: `from_str`/`from_str_radix` necesitan funciones asociadas
  (`Int.from_str`); `MIN`/`MAX`/`BITS` necesitan constantes asociadas. Anotado en
  `docs/STDLIB.md` §2.

### Siguiente paso

S1 continúa con `floatem` (`Float.sqrt` es el bloqueo 125 de Gate B), luego
`littera`, `bool`/`switch` y `opera`. El orden sugerido es `floatem` →
`littera` → `bool` → `opera`, porque `Float` desbloquea un programa de Gate B y
`Char` es la base de `verbum` (S2).

### S1 — `floatem` cerrado

- Superficie: **57 métodos** de `Float` (los de `STDLIB.md` §3 menos las constantes
  y `from_str`) y **50 intrínsecos** `f_*`.
- Cuerpo Pengu puro: `clamp`, `lerp`, `smoothstep`, `log`, `to_radians`,
  `to_degrees`, `is_nan` (`@ != @`), `is_normal` y `classify`.
- `classify` usa las variantes unitarias del `enchanting FloatClass` como
  expresiones sueltas (`Zero`, `Normal`, …). `FloatClass.NaN` **no** parsea en
  posición de expresión (se lee como acceso a campo); la forma correcta es el
  identificador suelto.
- Dos límites del compilador encontrados y anotados (no bloquean S1, sí S2):
  1. Un patrón `when Zero` en un módulo **distinto** del que declara el
     `enchanting` no resuelve: el resolvedor intenta el espacio de tipos primero
     (`PGS-E2004 no se encuentra el tipo \`Zero\``). Dentro del módulo dueño sí
     funciona. Arreglo parcial ya aplicado en `crates/pengu-hir/src/lower.rs`
     (`bind_pattern` busca variante en el espacio de valores antes de caer a
     `resolve_type_path`), pero las variantes no se importan con el tipo.
  2. Un método de primitivo que devuelve `Str` con receptor `@own` genera
     `fn f(__self: f64) -> &str` sin lifetime de origen (`E0106`). Es el riesgo R1
     del plan; por eso `classify_name` se retiró y `classify` queda como único
     acceso al tipo.
- Test de aceptación: `std_floatem_methods_compile_and_run`,
  `std_floatem_classify_and_ordering` y `std_floatem_unblocks_gate_b_hypotenuse`
  (el ejemplo de `LANGUAGE.md` §1.5 con `Point` + `sqrt` imprime `5`).
- Gate B: el bloque 125 compila → `compiled` 40 → **43**, `full_gaps` 10 → **9**
  (`crates/pengu-build/tests/gate_b_corpus.rs` y `scratch/GATE_B_CORPUS.md`
  actualizados).

### Siguiente paso (S1)

`littera` (`Char`), luego `bool` (`switch`) y `opera` (rituales de operadores),
y después S2 `verbum`.

### S1 — `littera` cerrado

- Superficie: **33 métodos** de `Char` y **35 intrínsecos** `c_*` (los dos
  intrínsecos extra son `c_from_u32`/`c_from_digit`, reservados para cuando haya
  funciones asociadas).
- Bugs de infraestructura encontrados y arreglados:
  1. `resolve_method_def` (`crates/pengu-lir/src/lower.rs:873`) solo mapeaba
     `Int`, `Float`, `Str`, `String`, `Vec`, `Map`, `Set` y `Adt`. Para `Char`
     devolvía `None`, así que `LExpr::Method.def` llegaba vacío al codegen y la
     llamada se emitía **nativa** (`'x'.is_math()`), con tres errores de `rustc`.
     Ahora mapea todos los primitivos (`Bool`, `Int|I32|IntVar`, `I8..Isize`,
     `U8..Usize`, `Float|F64|FloatVar`, `F32`, `Char`, `Str`, `String`).
  2. Sin `def`, `is_primitive_method` no podía reescribir la llamada. El mismo
     mapeo faltaba en el checker (`Ty::IntVar`/`FloatVar` ya se habían añadido en
     S1-integrum); conviene mantener los dos mapas sincronizados.
- `is_punctuation`, `is_symbol`, `is_math` e `is_currency` no tienen equivalente
  directo en Rust (no expone la categoría general UAX #44). Se aproximan con
  rangos Unicode documentados en `crates/pengu-codegen/src/std_rt.rs`:
  `0x2200..=0x22FF | 0x27C0..=0x27EF | 0x2980..=0x29FF | 0x2A00..=0x2AFF` para
  matemáticos y `0x24 | 0xA2..=0xA5 | 0x20A0..=0x20CF` para moneda.
- Diferidos: `encode_utf8` (`&mut [U8]`), `from_u32` y `from_digit` (funciones
  asociadas).
- Test de aceptación: `std_littera_methods_compile_and_run` y
  `littera_expone_la_superficie_de_char` (33 métodos).
- Suite: **530 tests** en verde.

### Siguiente paso (S1)

`bool` (`switch`) y `opera`, y después S2 `verbum`.

### S1 — `opera` cerrado

- `std/opera.pengu` declara los **8 pactos** (`Add`, `Sub`, `Mul`, `Div`, `Rem`,
  `Neg`, `Eq`, `Ord`) con sus firmas del documento.
- Cuatro arreglos de infraestructura hicieron falta para que un `ritual T for
  Add` funcionara:
  1. **Orden de imports.** `Lowerer::build` bajaba los items (y por tanto
     resolvía `ritual … for Pacto`) antes de aplicar los `summon`. Ahora el
     pacto se busca sin diagnosticar (`fn pact_def`), se anota en
     `pending_pacts` y `resolve_pending_pacts` lo resuelve después de
     `resolve_imports`. `pact_def` también acepta rutas multi-segmento
     (`ritual P for std::opera::Add`).
  2. **`Self` en firmas.** `signature_matches`/`type_matches`
     (`crates/pengu-types/src/check.rs`) no equiparaban `TypeKind::SelfType` con
     el tipo del `ritual`: daba `PGS-E1407`. Se añadió la equivalencia
     `Self <-> <tipo del ritual>`, también dentro de `&Self` y `Option[Self]`.
  3. **`Self` en LIR.** `ast_type_ty` devolvía `Ty::Error` para `SelfType`, así
     que el codegen emitía `fn add(self, other: _) -> _`. Ahora `ast_type_ty`
     recibe `self_ty: Option<&Ty>` y `FunctionLower::impl_ty()` lo calcula desde
     `krate.impls`.
  4. **Operadores.** `LExpr::TraitCall { pact, method, args }` es nuevo: `a + b`,
     `-a` sobre un `Adt` se bajan a `std::opera::Add::add(a, b)` etc., en vez de
     al operador de Rust (que exigiría `std::ops`). Solo aplica a tipos de
     usuario; los primitivos siguen con sus operadores nativos.
- Tests: `std_opera_pact_add_is_usable` (imprime `"11\n22\n"`) y
  `std_opera_pact_neg_is_usable` (`"-5\n"`).
- Gap detectado y **no** cubierto: el checker no marca el uso de un valor
  movido; el primer test tuvo que reescribirse con `bind s = p + q` porque
  `p + q` con `@own` consume ambos.

### Siguiente paso (S1)

`bool` (`switch`), luego S2 `verbum`.

### S1 — `veritas` (Bool) y cierre de S1

- `std/veritas.pengu`: **9 métodos** de `Bool` (`switch`, `to_int`, `to_string`,
  `xor`, `implies`, `nand`, `nor`, `then_int`, `to_float`) y un intrínseco
  (`b_to_string`). Nombre del módulo: `veritas` ("verdad"), en la línea latina
  del resto (`integrum`, `floatem`, `littera`).
- Añadido a `docs/STDLIB.md` como §4.1 para no renumerar las secciones.
- Test: `std_veritas_bool_methods_compile_and_run`.
- **Hallazgo que condiciona S2:** un literal de cadena es `Str`, así que un
  método declarado `-> String` que devuelve `"true"` falla con
  `PGS-E7002 tipos incompatibles: String y Str`. Por eso `to_string` es
  intrínseco. La coerción `Str → String` (y `String → Str` en argumentos) es el
  primer trabajo de S2/R1.
- Con esto S1 queda cerrado: `integrum` (63), `floatem` (57), `littera` (33),
  `opera` (8 pactos) y `veritas` (9).

### S2 — `verbum` cerrado

- `std/verbum.pengu`: **50 métodos de `Str`** + **22 de `String`** y **75
  intrínsecos** `s_*`/`str_*`. Diferidos a S7 (`funis`): `chars`, `bytes`,
  `char_indices`, `matches`, `match_indices`, `parse[T]`, `get(Range)`,
  `as_bytes`, `from_utf8*`, `drain`, `retain`.
- Infraestructura nueva que desbloquea el resto de la std:
  - **funciones asociadas** `Tipo.metodo(args)` (`String.new`, `String.from`,
    `Int.from_str`, `Iter.empty`, `Version.parse`): registradas en
    `self.methods` del lowerer, resueltas en `associated_call` del checker y
    bajadas a `LExpr::Call` en LIR;
  - **coerción implícita de préstamo** en `unify` (`Ref(T)` ↔ `T`), que hace
    que `@` (`String`) encaje con parámetros `&mut String`/`&String`;
  - `ty_by_name` como respaldo cuando `res_at` no resolvió un tipo dentro de
    `&T`/`&mut T`;
  - normalización `&Str` → `Str` en checker y LIR;
  - `parser.rs`: `&mut T` (el `mut` de tipo llegaba como `Ident`) y `-> Unit`
    obligatorio en `foreign` y en métodos de `ritual`;
  - codegen: `primitive_label`/`primitive_fn_name` (`str__len`,
    `string__len`), receptor `&String`/`&mut String`/`String` según `@`/`@mut`/
    `@own`, y lifetimes `<'a>` automáticos cuando el retorno presta `&str`.
- Tests: `std_verbum_str_methods_compile_and_run` y
  `std_verbum_string_mutators_compile_and_run` (este último valida `push`,
  `push_str`, `insert`, `remove`, `truncate`, `split_off` con `&mut String`).
- **Gate B: 46 → 47 compilados, 82 → 81 fallos, 6 → 7 bloqueos completos.**

### S3 — `capsa`, `tabula` y `fasciculus` cerrado

Las colecciones se implementan como **paso directo** a los tipos de Rust (clase
T3 del plan): el cuerpo del método es `panic("passthrough")`, que el backend
nunca emite; la llamada se traduce al método nativo (`(vec).push(x)`) o a un
ayudante genérico del runtime (`vec_sort_by`, `set_union`, `map_to_string`…).
La ventaja para un lenguaje de sistemas es que el coste y la semántica son los
de Rust, sin capa intermedia.

- `std/capsa.pengu`: **55 métodos** de `Vec[T]`.
- `std/tabula.pengu`: **20 métodos** de `Map[K, V]` + `to_string`.
- `std/fasciculus.pengu`: **25 métodos** de `Set[T]`.
- Infraestructura nueva:
  - `ritual[T] Vec[T]` / `ritual[K, V] Map[K, V]` / `ritual[T] Set[T]`: el
    parser ya admitía parámetros de tipo en `ritual`; solo hubo que bindearlos
    en `associated_call` y `method_signature` (`is_builtin_type_name`,
    `builtin_args`).
  - Codegen: `builtin_impl_label` evita emitir `impl Vec<T>`; `builtin_label`,
    `associated_builtin_path` (`::std::vec::Vec::new`) y `builtin_helper`
    enrutan los métodos que Rust no expone con ese nombre; `builtin_args`
    antepone `&` a los parámetros declarados `&T`.
  - Los ayudantes reciben el receptor por referencia (`&(recv)` para `@`,
    `&mut (recv)` para `@mut`, por valor para `@own`) porque son funciones
    libres y no hacen auto-borrow.
  - `LExpr::FuncRef(DefId)` en LIR: pasar una función con nombre como valor
    (`v.retain(even)`), antes `PGS-E1901 "path no soportado en LIR"`.
- Límites del compilador encontrados: `Less`/`Equal`/`Greater` no resuelven
  como valores (`Ordering` es `Primitive::Ordering`, sin variantes en el
  espacio de valores), así que los comparadores escritos a mano no se pueden
  construir todavía; y las lambdas en línea con `if/then/else` no parsean como
  argumento. Los callbacks se declaran con `T` por valor y el runtime copia
  (`T: Clone`), porque `&T` no admite operadores al no haber auto-deref.
- Tests: `std_capsa_basics_compile_and_run`, `std_capsa_operations_compile_and_run`,
  `std_tabula_methods_compile_and_run` y `std_fasciculus_methods_compile_and_run`.

### S4 — `numerus`, `fluxus` y `proba` cerrado

Fase de soporte: utilidades matemáticas, IO estándar y aserciones.

- `std/numerus.pengu`: 9 `sigil` (`PI`, `E`, `TAU`, `INFINITY`, `NEG_INFINITY`,
  `NAN`, `EPSILON`, `MIN`, `MAX`) y **65 funciones libres**. 43 son intrínsecos
  `num_*` (todo lo que toca `libm` o los bits del `f64`); 22 son cuerpos
  PenguScript puros (`abs`, `min`, `max`, `clamp`, `lerp`, `smoothstep`,
  `to_radians`, `to_degrees`, `gcd`, `lcm`, `factorial`, `comb`, `perm`,
  `distance`, `dot`, `cross`, `angle_between`, `normalize`, `isclose`, `log`,
  `log1p`, `recip`, `signum`, `is_nan`/`is_infinite`/`is_finite`).
- `std/fluxus.pengu`: `rune IoError`, seis funciones de IO
  (`read_line`, `read_stdin_to_string`, `write_stdout`, `write_stderr`,
  `flush_stdout`, `flush_stderr`) y los pactos `Reader` y `Writer`, que `via`
  implementará en S5.
- `std/proba.pengu`: nueve aserciones como intrínsecos (`assert`, `assert_eq`,
  `assert_ne`, `assert_eq_msg`, `assert_ne_msg`, `assert_approx_eq`,
  `debug_assert`, `debug_assert_eq`, `fail`).
- Infraestructura nueva:
  - **Genéricos en `foreign`**: `FunctionSig` gana `generics`, el parser acepta
    `nombre = [T](params) -> Ret` y `build_foreign` crea el scope de genéricos y
    usa `Pending::Signature` (antes las firmas foráneas no admitían `[T]`, lo
    que impedía declarar `assert_eq`).
  - `LExpr::ConstRef(DefId)`: las constantes (`sigil`/`relic`) no se podían
    referenciar desde LIR (`PGS-E1901 "path no soportado en LIR"`); ahora se
    renderizan con `def_path` como las funciones.
  - Los ítems de un `scroll` son privados: `unveil` en cada función y `sigil`.
    Los campos de un `rune` también lo necesitan (`unveil message: String`).
- Límites del compilador encontrados: **un `else` en línea propia seguido de un
  bloque indentado no parsea** (`PGS-E1901 "se esperaba una expresión"`); hay
  que usar `if ... then` de bloque con sentencia final o el `else` en la misma
  línea. Se reescribieron `isclose`, `comb` y `perm` por eso.
- Tests: `std_numerus_functions_compile_and_run`,
  `std_proba_assertions_compile_and_run` y `std_fluxus_io_compile_and_run`.
- Suite: **542 tests** en verde; fmt y clippy limpios. Gate B sigue en
  `(53, 1, 12, 75, 5)`.

### Siguiente paso (S5)

Sistema: `via` (FS completo), `exsecutor` (procesos), `ambitus` (entorno,
desbloquea el bloqueo 3798 de Gate B) y `tempus` (tiempo).

### S6 — `nexus` cerrado (esta sesión)

`std/nexus.pengu` pasa de 7 funciones (solo `CString`) a **17 funciones** con la
superficie segura completa de las dos caras de la FFI:

- `CString` (10): `cstring_new`, `cstring_from_bytes`, `cstring_into_string`,
  `cstring_to_str`, `cstring_to_string_lossy`, `cstring_as_bytes`,
  `cstring_len`, `cstring_is_empty`, `cstring_clone`, `cstring_as_c_str`.
- `CStr` (7): `cstr_to_str` (vista `&Str` sin copiar), `cstr_to_string_lossy`,
  `cstr_as_bytes`, `cstr_len`, `cstr_is_empty`, `cstr_equals_str` (compara con
  `Str` sin asignar), `cstr_to_cstring`.
- Las llamadas a C se declaran con `foreign "C"` y se ejecutan en `curse`; el
  runtime resuelve las 15 operaciones sobre `std::ffi::{CString, CStr}`.

Arreglos de compilador que hizo falta hacer (todos verificados con `rustc` real,
no solo en el corpus):

1. **`curse` en posición intermedia** perdía las sentencias posteriores y
   convertía la última expresión del bloque FFI en `return` de la función
   (`error[E0308] expected usize, found i32`). `lower_block_to` ahora distingue
   el `curse` de cola (su valor es el retorno) del `curse` como sentencia
   (continúa en un bloque nuevo).
2. **Liveness con locales definidos en un solo brazo de `match`**: el
   fallthrough tras el último brazo iba al `join` y obligaba a que locales como
   `CString` (sin `Default`) fueran *live-in* del bloque de entrada, que se
   inicializaban con `unreachable!()` → panic al arrancar. El checker ya exige
   exhaustividad (`PGS-E9001`), así que ese fallthrough se marca
   `LTerm::Unreachable`.
3. **`CStr` por valor era unsized** (N49): `Ty::CStr` se renderiza como
   `&::std::ffi::CStr`, `&CStr` se normaliza a `CStr` (igual que `&Str` → `Str`)
   y `ast_type` no duplica la referencia. `ty_has_ref`/`ty_rust_state` incluyen
   `CStr` para el lifetime del state machine.
4. **Llamar a una función `curse` estaba permitido en código seguro**: ahora da
   `PGS-E1602` ("llamada a una función `curse` fuera de un bloque `curse`") y
   cuenta como uso de la frontera FFI (`curse_used`).

Tests nuevos:

- `crates/pengu-codegen/tests/codegen.rs::std_nexus_ffi_end_to_end`: declara
  `strlen`/`toupper` de libc, ejecuta una función `curse` y usa `CStr` como
  temporal en la misma expresión. Salida esperada
  `"5\n4\nfalse\nhola\nhola\n65\n4\ntrue\nhola\n"`; el test **enlaza y ejecuta**
  el binario, así que valida la FFI de verdad.
- `crates/pengu-types/tests/check.rs::curse_function_call_outside_curse_is_rejected`
  y `::curse_function_call_inside_curse_is_accepted`.

Limitación nueva documentada (N55): una vista `CStr` no puede guardarse en un
`bind` y usarse después — el state machine mueve la `CString` dueña y el préstamo
no sobrevive (`error[E0597]`). Se usa como temporal; las conversiones que copian
no tienen el problema.

### S7 — `funis` cerrado (esta sesión)

`std/funis.pengu` no existía: los adaptadores estaban escritos a mano en la
tabla de `Ty::Iterator` del checker y `summon std::iter` fallaba. S7 los
completa y añade los que faltaban.

1. **13 adaptadores nuevos**: `filter_map`, `flat_map`, `flatten`, `chain`,
   `take_while`, `skip_while`, `reduce`, `product`, `for_each`, `inspect`,
   `fuse`, `max_by`, `min_by`. Se tocan las tres capas: `VecAdapterKind`
   (`crates/pengu-lir/src/lir.rs`), el mapa nombre→kind y el filtro de "solo
   sobre `Iterator`" (`crates/pengu-lir/src/lower.rs`), las firmas de
   `method_signature` (`crates/pengu-types/src/check.rs`) y la emisión
   (`crates/pengu-codegen/src/codegen.rs`).
2. **Iteradores guardables en un `bind`**: `take`, `skip`, `step_by` y `rev`
   emitían el tipo concreto de Rust, no `Box<dyn Iterator>`; ahora se envuelven
   en `Box::new(…)`. `rev` materializa porque `Box<dyn Iterator>` no implementa
   `DoubleEndedIterator`.
3. **`Str.chars()` / `bytes()` / `char_indices()`**: nuevos
   `VecAdapterKind::StrChars/StrBytes/StrCharIndices`; cierran tres diferidos de
   S2 y permiten `s.chars().map(…).collect()`.
4. **Cuerpos de lambda**: no se bajan por LIR, los renderiza `lower_ast_expr`
   desde el AST (`crates/pengu-codegen/src/codegen.rs:2334`) con un `_ => "()"`
   silencioso. Se añadió: `none` (`ExprKind::None`), `some`/`ok`/`err`,
   `print`/`format`, literales `Vec[…]`/`[…]`, interpolación de strings y
   construcción de records. Sigue siendo un subconjunto (N59).
5. `flat_map` recibe un cierre `(T) -> Vec[U]` (en Rust `IntoIterator`), no
   `Iter[U]`, porque el cuerpo de la lambda se renderiza sin tipos.

Tests nuevos: `std_funis_adapters_compile_and_run`,
`std_funis_str_chars_compile_and_run` y `std_funis_bind_adapted_iterator`.

Suite: 573 tests. **`structura` no se implementó**: ver N60 en
`scratch/LIMITATIONS_AUDIT.md` (necesita o 5 tipos integrados nuevos en el
compilador, o genéricos con `Ord`, y hoy `[T: Ord]` no resuelve o hace
desbordar la pila al compilador).

### S8 — auto-hospedaje textual cerrado (esta sesión)

Las cuatro piezas de S8 ya existían (otra sesión); aquí se cierran sus
pendientes declarados.

**`digestum`** — SHA-512 en Rust puro (`digest_sha512`, relleno de 128 bytes
con longitud de 128 bits), `hmac_sha256` (RFC 2104) y `constant_time_eq`
(compara sin cortocircuitar). Verificado contra `sha512("abc") = ddaf35a1…` y
HMAC de RFC 4231.

**`iason`** — `equals` (igualdad estructural; en objetos el orden de claves no
importa; `int` ≠ `float`), `get_path("a.b.0")` (ruta punteada con índices),
`push`/`insert`/`set`/`remove` (`@mut`) para construir y mutar árboles.
`get_path` se escribe con `for part in path.split(".")`: un `parts.get(i)` deja
un préstamo del `Vec` local que el state machine mueve (N61).

**`libra`** — tablas en línea `{ a = 1, b = { c = 2 } }` aplanadas como
`clave.a`/`clave.b.c`, fechas y horas clasificadas (`date`, `time`,
`datetime`) y `get_array` con separador interno (los elementos pueden contener
comas). `get` sigue devolviendo el array formateado.

**`versio`** — gramática de requisitos completa: uniones `||`, conjunciones
`>=1.0.0 <2.0.0`, comodines de cola (`1.x`, `1.2.x`, `*`) y versiones
incompletas con operador rellenadas con ceros (`^1.2` = `^1.2.0`).

Tests nuevos: `std_digestum_sha512_and_hmac`, `std_iason_mutators_and_paths`,
`std_libra_inline_tables_and_dates` y `std_versio_requirement_grammar`.

### S9 — `terminus`, `globus` y `archivum` cerrados (esta sesión)

- **`terminus`**: `clear_screen`, `move_cursor`, `hide_cursor`/`show_cursor`,
  `cursor_up`/`down`/`left`/`right`, `progress_bar` y `read_key`. Todo son
  secuencias ANSI sobre `print!`, sin dependencias; `read_key` no entra en modo
  crudo (N70).
- **`globus`**: `find_with(pattern, root, max_depth, include_hidden, follow_links)`
  en el runtime (`globus_find_with`), con profundidad y filtro de ocultos.
- **`archivum`**: superficie de compresión —`create_targz`/`entries_targz`/
  `extract_targz`, `create_zip`/`entries_zip`/`extract_zip` y `compress_gz`/
  `decompress_gz`— sobre el gzip/zip del runtime. El escritor emite bloques
  deflate *stored*; el lector implementa inflate completo (fijo y dinámico) y
  valida CRC y longitud del gzip, así que acepta archivos de otras herramientas.
  Contrastado con `unzip -t`, `gzip -t` y `tar -tzf`.
- Arreglos de paso: `usize::from(u32)` inválido en el lector zip, fecha DOS
  válida (1980-01-01) en las cabeceras y verificación de CRC al descomprimir.
