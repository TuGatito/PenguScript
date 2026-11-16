<a id="sec-58-herramientas"></a>
## 58. Herramientas (CLI, LSP, formatter, linter)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 9 |
| Rust | `cargo`, `rustc`, `rustfmt`, `clippy` |
| Palabras mágicas | `pengu` (CLI), `@@allow`, `@@deny`, `@@warn` |
| Depende de | §3, §43, §47, §56, §57 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec58_tooling.pengu` |

El compilador se invoca con `pengu`. La CLI transpila a Rust, invoca `cargo` y
traduce los diagnósticos de vuelta al código PenguScript mediante
`sourcemap.json`.

### 58.1 Comandos

| Comando | Uso | Efecto |
|---|---|---|
| `pengu new <name>` | crear proyecto | `Tome.toml`, `main.pengu`, `.gitignore` |
| `pengu init` | inicializar en directorio | igual, sin crear carpeta |
| `pengu build` | compilar | genera `target/pengu/` y ejecuta `cargo build` |
| `pengu run` | compilar y ejecutar | `cargo run` |
| `pengu check` | typecheck sin binario | `cargo check` |
| `pengu test` | tests | `cargo test` |
| `pengu fmt` | formatear | reescribe `.pengu` |
| `pengu lint` | lints | analiza AST + `clippy` |
| `pengu doc` | documentación | `cargo doc` |
| `pengu bench` | benchmarks | `cargo bench` |
| `pengu fuzz` | fuzzing | `cargo fuzz` |
| `pengu clean` | limpiar | borra `target/pengu/` |
| `pengu add <crate>` | dependencia | edita `Tome.toml` + lock |
| `pengu remove <crate>` | quitar dependencia | edita `Tome.toml` |
| `pengu update` | actualizar lock | respeta semver |
| `pengu publish` | publicar | valida y empaqueta |
| `pengu audit` | vulnerabilidades | `cargo audit` |
| `pengu lsp` | language server | JSON-RPC por stdio |
| `pengu explain <code>` | explicar diagnóstico | texto + ejemplo |
| `pengu metadata` | info del proyecto | JSON |

### 58.2 Flags comunes

| Flag | Comandos | Uso |
|---|---|---|
| `--release` | build/run/test/bench | perfil release |
| `--target <triple>` | build/run/check | target Rust |
| `--features <a,b>` | build/run/test | features del tome |
| `--all-features` | build/test | todas |
| `--no-default-features` | build/test | sin defaults |
| `--locked` | build/test/run | exige `Tome.lock` |
| `--offline` | build/test | no red |
| `--deny warnings` | check/build/test | warnings como errores |
| `--message-format json` | check/build | diagnósticos JSON |
| `--quiet` | todos | solo errores |
| `--verbose` | todos | comandos internos |
| `--color <auto\|always\|never>` | todos | color |

1. Los flags desconocidos son error de uso (`PGS-E5801`).
2. `--` separa flags de `pengu` de argumentos del programa.
3. `--target` no cambia el target de `Tome.toml`; lo sobrescribe.
4. `--locked` falla si el lock no existe o está desactualizado.
5. `--offline` no descarga crates; falla si falta el cache.
6. `--quiet` no suprime errores.
7. Los flags de `cargo` no documentados se pasan con `--cargo-args`.

### 58.3 Códigos de salida

| Código | Significado |
|---|---|
| `0` | éxito |
| `1` | error de compilación, test o lint |
| `2` | uso incorrecto de la CLI |
| `3` | error de configuración (`Tome.toml`) |
| `4` | error interno del compilador |
| `101` | pánico de Rust (no debería ocurrir) |

1. Un test fallido devuelve `1`.
2. Un `check` con warnings y `--deny warnings` devuelve `1`.
3. `pengu fmt --check` devuelve `1` si hay diferencias.
4. `pengu lint --deny warnings` devuelve `1` si hay warnings.
5. Un error de red en `pengu add` devuelve `1`.
6. `pengu explain` devuelve `0` si el código existe.
7. `pengu metadata` devuelve `0` aunque no haya lock.

### 58.4 Estructura del proyecto

```text
tome/
├── Tome.toml
├── Tome.lock
├── main.pengu
├── lib.pengu
├── src/
│   ├── math.pengu
│   └── math/
│       └── vector.pengu
├── tests/
│   └── api.pengu
├── examples/
│   └── demo.pengu
├── benches/
│   └── bench.pengu
├── build.pengu
└── target/
    └── pengu/
        ├── Cargo.toml
        ├── Cargo.lock
        ├── build.rs
        ├── src/
        └── sourcemap.json
```

1. `main.pengu` y `lib.pengu` son las raíces.
2. `src/` es opcional si no hay raíz.
3. `tests/`, `examples/` y `benches/` tienen el mismo rol que en Cargo.
4. `target/pengu/` es generado; no se edita.
5. `sourcemap.json` conecta Rust con PenguScript.
6. `Tome.lock` se versiona; `target/` no.
7. `build.pengu` se transpila a `build.rs`.

### 58.5 `pengu check`

1. Parsea, resuelve, typechequea y transpila sin emitir binario.
2. Ejecuta `cargo check` para validar préstamos y tipos Rust.
3. No ejecuta `build.rs` salvo que el crate lo requiera.
4. Es más rápido que `build` y apto para CI.
5. Los diagnósticos se remapean a `.pengu`.
6. `--deny warnings` convierte warnings en errores.
7. No genera `target/pengu/src/` completo si `--emit=metadata`.

### 58.6 `pengu build`

1. Transpila todos los archivos alcanzables desde las raíces.
2. Genera `Cargo.toml`, `Cargo.lock`, `build.rs` y `src/`.
3. Ejecuta `cargo build` con los flags traducidos.
4. Copia artefactos a `target/<target>/<profile>/`.
5. Escribe `sourcemap.json` para el debugger.
6. Falla si un `.pengu` no compila o si `rustc` falla.
7. No modifica los `.pengu`.

### 58.7 `pengu run`

1. Ejecuta `build` y luego el binario.
2. `--` pasa argumentos al programa.
3. El `cwd` es la raíz del tome.
4. `--release` usa el perfil release.
5. El código de salida del programa se propaga.
6. Un pánico de Rust se muestra con el mapa de líneas.
7. `run` no existe para `lib.pengu` sin `[[bin]]`.

### 58.8 `pengu test`

1. Ejecuta tests unitarios, de integración y doc tests.
2. `--all` incluye todos los targets.
3. `--test <name>` ejecuta un archivo de `tests/`.
4. `--doc` solo doc tests.
5. `-- --nocapture` pasa flags al runner.
6. `--coverage` genera un reporte (`llvm-cov`/`tarpaulin`).
7. Un test ignorado no cuenta como fallo.

### 58.9 `pengu fmt`

```bash
pengu fmt
pengu fmt --check
pengu fmt --stdin < main.pengu
pengu fmt --check --diff
```

1. El formatter es determinista e idempotente.
2. Usa 4 espacios; nunca tabs.
3. Ancho máximo: 100 columnas.
4. Una expresión/declaración por línea.
5. Comas finales en colecciones multilínea.
6. `summon` se ordena por ruta.
7. Conserva comentarios y líneas en blanco significativas.
8. `--check` no escribe; devuelve `1` si cambiaría algo.
9. `--stdin` lee de stdin y escribe a stdout.
10. `--diff` muestra el diff unificado.
11. No cambia la semántica; si lo hace, es un bug.
12. `@@fmt(off)` desactiva el formato en un rango.

### 58.10 Reglas del formatter

| Regla | Ejemplo |
|---|---|
| 4 espacios | `    bind x = 1` |
| sin tabs | `\t` -> error |
| 2 líneas entre items | `rune`/`enchanting`/`pact` |
| 1 línea entre métodos | `ritual` |
| coma final | `[1, 2, 3,]` multilínea |
| paréntesis mínimos | `(a + b) * c` conserva |
| strings | no reescribe escalas |
| imports | `summon` ordenados |
| comentarios | se conservan |
| ancho | 100 columnas |

### 58.11 Linter

```bash
pengu lint
pengu lint --deny warnings
pengu lint --fix
pengu lint --format json
```

| Código | Nombre | Categoría |
|---|---|---|
| `PGS-L101` | `unused_binding` | corrección |
| `PGS-L102` | `unreachable_code` | corrección |
| `PGS-L103` | `unused_import` | corrección |
| `PGS-L201` | `shadowing` | estilo |
| `PGS-L202` | `magic_number` | estilo |
| `PGS-L203` | `long_function` | complejidad |
| `PGS-L301` | `unsafe_without_safety` | seguridad |
| `PGS-L302` | `raw_pointer_escape` | seguridad |
| `PGS-L401` | `missing_docs` | documentación |
| `PGS-L402` | `broken_intra_doc_link` | documentación |
| `PGS-L501` | `lexicon_collision` | diseño |
| `PGS-L502` | `rust_escape_hatch` | diseño |

1. Los lints son warnings por defecto, salvo los de corrección.
2. `--deny warnings` los convierte en errores.
3. `--fix` solo aplica fixes seguros.
4. `@@allow(PGS-L201)` silencia un lint en el item.
5. `@@deny(PGS-L301)` lo convierte en error local.
6. `@@warn(PGS-L401)` lo activa localmente.
7. `PGS-L501` detecta una palabra mágica que también es identificador común.
8. `PGS-L502` avisa de cada bloque `rust`.

### 58.12 Configuración

`Tome.toml`:

```toml
[tool.pengu.fmt]
max-width = 100
indent = 4
trailing-comma = true

[tool.pengu.lint]
deny = ["PGS-L301", "PGS-L302"]
warn = ["PGS-L201"]
allow = ["PGS-L202"]

[tool.pengu.test]
coverage = false
```

1. `[tool.pengu]` no se pasa a Cargo.
2. `fmt.max-width` debe estar entre 80 y 120.
3. `lint.deny` tiene prioridad sobre `allow`.
4. La configuración del CLI se puede sobrescribir con flags.
5. `Tome.toml` inválido es `PGS-E5802`.
6. Los valores desconocidos son warning `PGS-W5801`.
7. La configuración se resuelve desde la raíz del tome.

### 58.13 LSP

```bash
pengu lsp
pengu lsp --stdio
pengu lsp --tcp 127.0.0.1:9257
```

| Capacidad | Soporte |
|---|---|
| `textDocument/publishDiagnostics` | sí |
| `textDocument/hover` | sí |
| `textDocument/completion` | sí |
| `textDocument/definition` | sí |
| `textDocument/references` | sí |
| `textDocument/rename` | sí |
| `textDocument/formatting` | sí |
| `textDocument/codeAction` | sí |
| `textDocument/inlayHint` | sí |
| `textDocument/semanticTokens` | sí |
| `workspace/symbol` | sí |
| `textDocument/documentSymbol` | sí |

1. JSON-RPC 2.0 sobre stdio o TCP.
2. `stdout` solo lleva protocolo; los logs van a `stderr`.
3. Los diagnósticos usan `sourcemap.json` para volver a `.pengu`.
4. `hover` muestra el tipo inferido y el doc.
5. `completion` incluye preludio, locales y campos.
6. `rename` respeta scopes y no renombra strings.
7. `formatting` usa el mismo formatter que `pengu fmt`.
8. `codeAction` ofrece fixes de lints seguros.
9. `inlayHint` muestra tipos de `bind` y retornos.
10. El servidor se reinicia si `Tome.toml` cambia.

### 58.14 Source maps y diagnósticos

`sourcemap.json`:

```json
{
  "version": 1,
  "generated": {
    "src/main.rs": "main.pengu",
    "src/math.rs": "src/math.pengu"
  },
  "mappings": [
    {
      "generated": { "file": "src/main.rs", "line": 3, "column": 4 },
      "source": { "file": "main.pengu", "line": 2, "column": 4 }
    }
  ]
}
```

1. Cada archivo Rust generado tiene un `.pengu` de origen.
2. Las líneas/columnas son 1-based en el JSON.
3. `rustc` emite JSON; `pengu` lo remapea.
4. Un diagnóstico sin mapping se muestra en Rust con nota.
5. `pengu explain PGS-E3001` muestra causa y ejemplo.
6. Los errores de macros apuntan al `incantation`.
7. Los errores de `build.rs` apuntan a `build.pengu`.

### 58.15 `pengu add`, `remove`, `update`

1. `add` edita `Tome.toml` y ejecuta `cargo add` sobre el `Cargo.toml` generado.
2. `--dev` añade a `[dev-dependencies]`.
3. `--features` activa features de la dependencia.
4. `remove` elimina la entrada y actualiza el lock.
5. `update` respeta el rango semver.
6. `update --precise` fija una versión exacta.
7. Un conflicto de versiones es `PGS-E5803`.

### 58.16 `pengu publish`

1. Verifica que el árbol esté limpio.
2. Ejecuta `check`, `test`, `fmt --check`, `lint`, `doc`.
3. Verifica que la versión no exista ya.
4. Empaqueta solo `Tome.toml`, fuentes, README y licencia.
5. `--dry-run` muestra el paquete sin subirlo.
6. `--allow-dirty` omite la comprobación de git.
7. Un fallo de docs o tests aborta la publicación.
8. El registro por defecto es `crates.io`; se puede cambiar en `[cargo]`.

### 58.17 Reproducibilidad y auditoría

1. `Tome.lock` fija versiones exactas.
2. `--locked` falla si el lock no coincide.
3. `--offline` exige cache local.
4. `SOURCE_DATE_EPOCH` fija timestamps en el paquete.
5. `pengu audit` ejecuta `cargo audit`.
6. `pengu deny` revisa licencias y duplicados.
7. `pengu publish` ejecuta `audit` salvo `--no-audit`.
8. Las dependencias con `unsafe` se revisan con `cargo geiger`.

### 58.18 `pengu new` y Rust generado

`pengu new hello --bin` genera:

```pengu
grimoire
    print("Hola, PenguScript!")
```

Rust generado:

```rust
fn main() {
    println!("Hola, PenguScript!");
}
```

1. `--bin` crea `main.pengu`; `--lib` crea `lib.pengu`.
2. `--vcs git` inicializa git; `--vcs none` no.
3. `--edition 2024` es el default.
4. `--name` valida el nombre del crate.
5. `new` no sobrescribe un directorio existente.
6. `init` sí acepta un directorio existente vacío.
7. La plantilla no incluye dependencias.

### 58.19 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5801` | flag desconocido | revisar `--help` |
| `PGS-E5802` | `Tome.toml` inválido | corregir TOML/claves |
| `PGS-E5803` | conflicto de versiones | fijar versión |
| `PGS-E5804` | `pengu` fuera de un tome | `pengu init` |
| `PGS-E5805` | `sourcemap.json` inválido | regenerar build |
| `PGS-E5806` | `publish` sin licencia | añadir `license` |
| `PGS-W5801` | clave de config desconocida | eliminar/renombrar |
| `PGS-W5802` | `--offline` sin cache | descargar antes |

### 58.20 Criterios de aceptación

- [x] Todos los comandos y flags están documentados.
- [x] Los códigos de salida son estables.
- [x] El formatter tiene reglas verificables.
- [x] El linter tiene catálogo y configuración.
- [x] LSP cubre las capacidades básicas.
- [x] Source maps y auditoría están cubiertos.
- [x] El ejemplo Rust compila.

[↑ Volver al índice](#indice)
