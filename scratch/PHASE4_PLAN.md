# Fase 4 — Lowering, codegen y build/run reales

Estado: en curso (2026-11-15). Este documento es el plan y el registro de la
fase; se actualiza al cerrar cada tramo.

## 0. Punto de partida (auditoría)

La fase se dio por hecha cuando `pengu build` ya invocaba a Cargo, pero faltan
piezas que el propio plan exige. Evidencia recogida antes de tocar código:

| Entregable del plan | Estado real |
| --- | --- |
| `pengu build/run/test` con cargo | ✅ existe, pero **re-emite y recompila siempre** |
| Codegen + `Cargo.toml` + `sourcemap.json` | ✅ `crates/pengu-build/src/lib.rs:257` |
| Remapeo de errores de `rustc` | ❌ **roto**: lee `"message"` del objeto externo (es un objeto, no una cadena) y descarta el texto `rendered`; todo error sale como "error del backend Rust" con span 0 |
| Caché incremental | ❌ no existe: `emit` reescribe los archivos en cada build (mtime cambia) y Cargo recompila; medido 1,9 s y 0,86 s en dos builds idénticos de un programa de 2 líneas |
| `pengu check` (front-end sin cargo) | ❌ **el subcomando no existe** (tabla de comandos de `TOOLING_PLAN.md` línea 1048: `build`, `run`, `test`, `check --watch`) |
| `pengu check --watch` / `pengu watch` | ❌ no existe |
| Ejemplos end-to-end | ❌ no hay `examples/` |
| Lowering con moves/drops explícitos | 🟡 moves verificados en `crates/pengu-check/src/ownership.rs` (`PGS-E4106` uso tras movimiento, `PGS-E4107` doble movimiento, `E4108` asignar a prestado); drops los coloca Rust y el LIR no los duplica (ver D7) |

Prueba del remapeo, con el código generado de un proyecto real:

```text
{"reason":"compiler-message","message":{"level":"error","message":"mismatched types",
 "spans":[{"file_name":"src/main.rs","line_start":19145,"column_start":28,"is_primary":true}],
 "rendered":"error[E0308]: mismatched types\n --> src/main.rs:19145:28\n ..."}}
```

`json_string(line, "message")` encuentra primero `"message":{` del objeto
externo y devuelve `None`, así que el diagnóstico pierde el texto real.

## 1. Objetivo y criterio de cierre

Cerrar la Fase 4 significa poder decir, con pruebas:

1. `pengu check` analiza un proyecto **sin invocar Cargo** y devuelve 0/1 con
   diagnósticos completos (sintaxis, tipos, ownership).
2. `pengu check --watch` (y `pengu watch <check|build|run|test>`) re-ejecuta al
   cambiar un `.pengu` del proyecto, con una sola dependencia del sistema: el
   reloj.
3. Un error de `rustc` en código generado se presenta con su texto real, su
   código (`E0308`…) y, cuando el sourcemap lo permite, con el span del
   `.pengu` que lo originó; nunca aparece "sin un diagnóstico JSON
   reconocible".
4. Un build sin cambios no re-emite ni invoca a Cargo, y tarda < 100 ms.
5. `examples/` contiene programas reales que compilan y se ejecutan, con un
   test de integración que fija su salida.
6. El modelo de moves/drops está documentado y probado (uso tras movimiento,
   doble movimiento, orden de drops).
7. `cargo test --workspace`, `fmt` y `clippy -D warnings` limpios; Gate B
   intacto (68 compilados / 4 decl / 56 frag / 13 declarados / 5 errores).
8. La caché es determinista: mismo fingerprint ⇒ mismo resultado, y un cambio
   de fuente la invalida.
9. Nada de `unsafe` ni dependencias externas nuevas.
10. Documentación actualizada: `docs/BUILD.md`, `scratch/PHASE4_PLAN.md`,
    `scratch/TOOLING_PLAN.md` y `scratch/STATUS.md`.

## 2. Decisiones

- **D1 — `pengu check` es el front-end completo.** `parse → lower_program →
  check_crate → check_ownership_with`, sin LIR, sin codegen y sin Cargo. Se
  implementa en `pengu-build::check` para que `build` y `check` no diverjan.
- **D2 — `watch` por polling de mtimes** cada 250 ms: sin dependencias, sin
  `inotify` (no portable), y suficiente para archivos de este tamaño. Ignora
  `target/` y `.git/`. La primera ejecución es inmediata; cada cambio reinicia
  el comando.
- **D3 — Una caché, en disco, por contenido.** Fingerprint = SHA-256 de
  (versión de caché + manifiesto + fuentes propias + fuentes de los paquetes +
  fuentes de `std` embebidas + versión del crate de codegen). Vive en
  `target/pengu/fingerprint`. Si coincide, `build` no re-emite ni llama a
  Cargo; `check` solo compara fuentes.
- **D4 — `emit` idempotente.** Solo escribe un archivo si el contenido cambió.
  Esto mantiene el fingerprint de Cargo y evita recompilaciones espurias.
- **D5 — Remapeo real de `rustc`.** Se parsea `reason == "compiler-message"`,
  `message.level == "error"`, `message.spans[0]` (`file_name`, `line_start`,
  `column_start`, `is_primary`) y se usa `message.rendered` como texto. El
  span Pengu sale de `SourceMap::lookup(line_start)`; si no hay entrada, el
  diagnóstico se emite con `PGS-E2014` y una nota que dice que el error está en
  código generado, con el archivo y la línea.
- **D6 — `pengu-json` compartido.** El parser JSON de `pengu-lsp` se mueve a un
  crate propio (`pengu-json`) y lo usan LSP y build. Sin dependencias externas.
- **D7 — Moves y drops.** El LIR **no** inserta nodos `Drop`: Rust ya coloca los
  drops al final de cada bloque y en orden inverso de declaración, y añadirlos
  produciría dobles liberaciones. Lo que sí se garantiza y prueba: los moves
  se comprueban estáticamente (E4106/E4107/E4108), el valor movido no se vuelve
  a usar, y el orden de drops es determinista. Se documenta en `docs/BUILD.md`
  para que nadie lo tome por una carencia.
- **D8 — Ejemplos reales, no de juguete.** `examples/` con programas que usan
  la stdlib (texto, colecciones, `rune` + pactos, `via`/`ambitus`) y un test
  que los compila y compara la salida.
- **D9 — Sin dependencias nuevas** (ni `notify`, ni `walkdir`, ni `serde`).

## 3. Arquitectura

```text
crates/pengu-json        nuevo: parse/render JSON (movido de pengu-lsp)
crates/pengu-build
    src/lib.rs           API pública (compile, build, run, test)
    src/check.rs         nuevo: check(root) sin cargo
    src/cache.rs         nuevo: fingerprint + lectura/escritura atómica
    src/remap.rs         nuevo: cargo JSON -> Diagnostic
crates/pengu-cli
    src/commands.rs      check, watch, build/run/test con caché
    src/watch.rs         nuevo: polling de mtimes
examples/                programas end-to-end
crates/pengu-build/tests/examples.rs   compila y ejecuta cada ejemplo
```

## 4. Fases

### P0 — Auditoría y plan ✅

- [x] Medir el estado real (tabla de §0).
- [x] Congelar decisiones D1–D9.
- [x] Criterio de cierre.

### P1 — `pengu check`

- [ ] `pengu_build::check(root) -> CheckReport { diagnostics }` con la misma
      secuencia que `compile` hasta ownership.
- [ ] `Command::Check` con `--watch`; salida con `render_compact`.
- [ ] Tests: proyecto válido (0), error de tipo (1, `PGS-E7…`), error de
      ownership, y comprobación de que **no** se crea `target/pengu`.

### P2 — `pengu-json` y remapeo de `rustc`

- [ ] Extraer `pengu-lsp/src/json.rs` a `crates/pengu-json` (misma API).
- [ ] `pengu-lsp` reexporta (`pub use pengu_json as json;`).
- [ ] `pengu-build/src/remap.rs` con `remap_cargo_json(stdout+stderr, sourcemap)`.
- [ ] Tests con las líneas JSON reales de `rustc` (mensaje, spans, rendered) y
      con un error sin span (nota de código generado).
- [ ] `BuildReport` expone los errores ya remapeados y no añade el genérico si
      hubo alguno.

### P3 — Caché incremental

- [ ] `pengu-build/src/cache.rs`: `Fingerprint::of(root, packages)`, `read`,
      `write` (atómico), `matches`.
- [ ] `emit` escribe solo diferencias.
- [ ] `build_report`/`run_report`/`test_report` consultan la caché antes de
      emitir y de llamar a Cargo; `BuildReport.cached: bool`.
- [ ] La CLI informa `sin cambios` (con `--verbose`).
- [ ] Tests: segundo build no invoca Cargo (marcador en un wrapper de `cargo`
      en el PATH del test), cambiar una fuente lo invalida, y la caché no
      sobrevive a un cambio de manifiesto.

### P4 — `--watch`

- [ ] `pengu watch <check|build|run|test>` y `pengu check --watch`.
- [ ] Polling cada 250 ms de `*.pengu`/`Tome.toml` bajo el proyecto (ignora
      `target/`, `.git/`); re-ejecuta al cambiar.
- [ ] Test: arrancar `pengu check --watch` con la salida a un archivo, tocar un
      fuente y comprobar que hay una segunda ejecución; matar con `SIGTERM`.

### P5 — Ejemplos y moves/drops

- [ ] `examples/hola.pengu`, `colecciones.pengu`, `geometria.pengu`,
      `ficheros.pengu`, `iteradores.pengu`.
- [ ] `crates/pengu-build/tests/examples.rs`: compila, ejecuta y compara salida.
- [ ] Tests de ownership: uso tras movimiento, doble movimiento, préstamo vivo;
      test de orden de drops con un `Rc` (contador de referencias) si la
      stdlib lo permite, o con el runtime de `Show`.

### P6 — Cierre

- [ ] `docs/BUILD.md` (pipeline, caché, remapeo, watch, moves/drops).
- [ ] `scratch/TOOLING_PLAN.md` Fase 4 ✅, `scratch/STATUS.md` §15.
- [ ] Suite completa, Gate B, `fmt`, `clippy -D warnings`.
- [ ] Commit.

## 5. Riesgos

| Riesgo | Mitigación |
| --- | --- |
| La caché da falsos positivos y sirve un binario viejo | Fingerprint incluye fuentes, manifiesto y std; test explícito de invalidación |
| `watch` entra en bucle porque el propio build escribe en el proyecto | Se ignoran `target/` y `.git/`; los `.pengu` no se escriben nunca |
| El remapeo mueve errores a líneas equivocadas | `SourceMap` se prueba con líneas generadas conocidas; si no hay entrada se dice claramente |
| Los ejemplos se pudren | Se compilan en CI vía `cargo test` |
| `check` y `build` divergen | Ambos llaman a la misma función de análisis |

## 6. Seguimiento

| Fase | Estado |
| --- | --- |
| P0 | ✅ |
| P1 | ✅ |
| P2 | ✅ |
| P3 | ✅ |
| P4 | ✅ |
| P5 | ✅ |
| P6 | ✅ |

## 7. Resultado

- `pengu check` (con `--watch`) analiza sin Cargo ni `target/`.
- Remapeo real: `E0308: mismatched types` + span Pengu + nota con la línea generada.
- Caché por contenido: segundo `build` en 18 ms sin invocar a Cargo; `run` en 16 ms.
- `emit` idempotente: el mtime de `src/main.rs` no cambia entre builds.
- `examples/` con cuatro programas reales, compilados y ejecutados por
  `crates/pengu-build/tests/examples.rs`, que además exige formato y cero avisos.
- `docs/BUILD.md` documenta pipeline, `check`, caché, fingerprint, `watch`,
  remapeo y ejemplos; CI verifica formato y lints de `std` y de `examples`.
