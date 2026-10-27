# PLAN F7 — Herramientas de desarrollo

> **Estado:** propuesta para aprobación. No implementado todavía.
> **Base:** F6 cerrada en `main` (CLI completo, caché, `fmt/doc/assets/watch/
> benchmark/selftest` en versión MVP, bootstrap en punto fijo).
> **Objetivo:** convertir esas herramientas de “funcionan” a **paridad de
> producción con stage0**, con tests, determinismo y CI.

---

## 1. Resumen ejecutivo

F6 entregó la superficie completa del CLI, pero varias herramientas nacieron
como versiones conservadoras:

- `fmt` ya reindenta y normaliza espacios, pero no es byte-idéntico a
  `pengu_lsp.formatting`.
- `doc` genera Markdown/HTML básico desde texto, no desde símbolos F3.
- `assets` cubre embed/disk/exclude, pero no `.incbin`, hash incremental ni
  todos los casos de stage0.
- `watch` sólo mira el entry, no el grafo de imports.
- `benchmark` y `selftest` son wrappers dev-only de Python.

**F7 no añade comandos nuevos.** Completa, endurece y hace paritarias las
herramientas existentes, y establece el **arnés de paridad** que F8/F9 usarán.

**Fuera de F7:** LSP (F8), dependencias/package manager (F9), `bind` (F10),
cross/WASM/MSVC/switchover (F11).

---

## 2. Estado actual (F6) frente al objetivo F7

| Herramienta | F6 | F7 |
|---|---|---|
| `fmt` | unidad, `.pengufmt.toml`, reindentación, espacios, `--diff` | paridad byte a byte con stage0, strings/triples/antiquus, CRLF/BOM, escritura atómica, corpus |
| `doc` | Markdown por módulo, índice HTML con búsqueda | modelo de símbolos F3, firmas/tipos/constantes/tests, enlaces, paridad de contenido |
| `assets` | embed/disk, exclude, list, C+header+interface | `.incbin`, hash incremental, colisiones, symlinks, `--json`, paridad |
| `watch` | mtime del script, polling 300 ms | grafo de imports, manifiesto/std, debounce, kill del hijo, `--once`, `--test` |
| `benchmark` | wrapper de `benches/run_bench.py` | runner nativo PSC, CSV/JSON, warmup/repeat, baselines opcionales |
| `selftest` | wrapper pytest | detección de venv, `--smoke`/`--json`/`--affected`, dev-only documentado |
| Paridad | tests F6 básicos | arnés dual stage0/PSC para fmt/doc/assets |

### Deuda concreta que F7 debe cerrar

1. `fmt` no reproduce exactamente el formatter de stage0.
2. `doc` no usa el grafo de símbolos de F3 y puede divergir en contenido.
3. `assets` no soporta `.incbin`, hash incremental ni todos los patrones.
4. `watch` no reacciona a imports ni a cambios del manifiesto.
5. `benchmark` depende de Python y no es determinista como runner nativo.
6. No hay paridad automatizada de herramientas contra stage0.
7. Tests F7 inexistentes; CI sólo cubre F6.

---

## 3. Decisiones

### D1 — Alcance de F7

- ✅ **Recomendado:** F7 = paridad y endurecimiento de `fmt`, `doc`, `assets`,
  `watch`, `benchmark`, `selftest` + arnés de paridad. Sin comandos nuevos.
- ⚠️ Alternativa: reimplementar desde cero. F6 ya tiene base; sería desperdicio.

### D2 — Formatter

- ✅ **Recomendado:** portar **fielmente** la semántica de
  `pengu_lsp/formatting.py` a PSC, línea a línea, con las mismas reglas:
  detección de unidad, `_split_code_and_strings`, triples, `antiquus`,
  `is/as/into`, comas, blank lines.
- ⚠️ Alternativa: formatter basado en AST. Es más limpio, pero cambia el output
  y rompe paridad C.

### D3 — Documentación

- ✅ **Recomendado:** `doc` basado en **símbolos F3** (tipos, firmas, doc
  comments, constantes, tests, omens) y no en líneas de texto. Markdown
  determinista + HTML con búsqueda.
- ⚠️ Alternativa: mantener el extractor textual de F6. Menos trabajo, no
  paritario.

### D4 — Assets

- ✅ **Recomendado:** portar `pengu_assets.py` completo: `.incbin` con umbral
  (`PENGU_ASSETS_INCBIN_THRESHOLD`, default 1 MB), fallback portable,
  embed/disk, exclude, colisiones, hash incremental, `--force`, `--json`.
- ⚠️ Alternativa: sólo arrays C. Simple, pero assets grandes inflan el binario.

### D5 — Watch

- ✅ **Recomendado:** polling del **grafo de imports resuelto por F3** +
  manifiesto + `std/` + runtime; 300 ms; debounce 150 ms; matar el hijo anterior
  al recompiar; `--once`, `--interval`, `--clear`.
- ⚠️ Alternativa: inotify/kqueue. Más eficiente, más código y plataformas.

### D6 — Benchmark

- ✅ **Recomendado:** runner **nativo PSC** para los casos `.pengu` de
  `benches/` (build/run/size, warmup, repeat, CSV/JSON). Los baselines
  C/Rust/Zig son opcionales y se marcan `skipped` si falta toolchain.
- ⚠️ Alternativa: seguir llamando `benches/run_bench.py`. Dependencia Python en
  una herramienta de usuario; no.

### D7 — Selftest

- ✅ **Recomendado:** mantenerlo dev-only, con detección de `.venv/bin/python`
  o `PSC_PYTHON`; `--smoke`, `--json`, `--affected`; documentar que no es parte
  del build de usuario.
- ⚠️ Alternativa: portar pytest a PSC. Es F8+ y no aporta a F7.

### D8 — Arnés de paridad

- ✅ **Recomendado:** `psc/tools/parity_tools.py` (Python dev-only) que ejecuta
  stage0 y PSC sobre el mismo corpus y compara salida normalizada. `--check` en
  CI, `--update` local.
- ⚠️ Alternativa: comparar sólo goldens estáticos. Detecta menos regresiones.

### D9 — Refactor de módulos

- ✅ **Recomendado:** mover lógica de `cmd/fmt|doc|assets` a
  `psc/src/psc/fmt|docgen|assets`; `cmd/*` queda como CLI fina.
- ⚠️ Alternativa: dejar todo en `cmd/`. Más deuda y difícil de testear.

### D10 — Escritura y seguridad

- ✅ **Recomendado:** escritura atómica (tmp + rename) para fmt/doc/assets;
  validar symlinks; no escribir fuera del proyecto salvo `--output` explícito;
  no seguir enlaces en `clean`/assets.
- ⚠️ Alternativa: escritura directa. Riesgo de corrupción si se corta.

### D11 — Sin cambios de runtime/ABI

- ✅ **Recomendado:** F7 sólo toca `psc/src/**`, `psc/tools/**`, tests/docs.
  Los assets generados pueden incluir C, pero no cambian `pengu_runtime.h`.
- ⚠️ Alternativa: tocar el runtime para `.incbin`/assets. No hace falta.

### D12 — Timebox y cierre

- ✅ **Recomendado:** 6–8 semanas; si `doc`/`assets` se desbordan, F7.5 con
  aprobación. `fmt` y `watch` no se difieren.
- ⚠️ Alternativa: cerrar F7 sólo con `fmt`/`watch` y dejar doc/assets en F7.5.

---

## 4. Arquitectura propuesta

```text
psc/src/psc/fmt/
  config.pengu       # .pengufmt.toml, defaults
  lex.pengu          # split code/literals, triple/raw/antiquus
  format.pengu       # algoritmo line-based, idempotente
  diff.pengu         # unified diff mínimo
psc/src/psc/docgen/
  model.pengu        # símbolos F3 -> doc model
  render.pengu       # Markdown determinista
  html.pengu         # índice + búsqueda
psc/src/psc/assets/
  collect.pengu      # recorrido, exclude, symlinks, orden
  emit.pengu         # interface .pengu, header C, embed/disk/incbin
  cache.pengu        # hash/digest incremental
psc/src/psc/watch/
  graph.pengu        # dependencias desde SemaProgram
  poll.pengu         # mtime/size, debounce, kill
psc/src/psc/bench/
  cases.pengu        # casos y metadatos
  run.pengu          # build/run/size, repeat, CSV/JSON
psc/src/psc/cmd/
  fmt.pengu doc.pengu assets.pengu watch.pengu benchmark.pengu selftest.pengu
psc/tools/
  parity_tools.py    # dev-only stage0 vs PSC
tests/psc/
  test_f7_fmt.py test_f7_doc.py test_f7_assets.py
  test_f7_watch.py test_f7_benchmark.py test_f7_parity.py
psc/tests/fixtures/f7/**
```

`main.pengu` no cambia salvo registrar los mismos comandos.

---

## 5. Formatter (`psc fmt`)

### 5.1 Contrato

```bash
psc fmt [paths...] [--check] [--diff] [--stdin] [--verbose]
        [--indent=N] [--tabs] [--config=PATH]
```

- `paths` archivos/directorios; recursivo `.pengu`.
- `--check`: no escribe; exit 1 si cambiaría.
- `--diff`: diff por línea (formato estable).
- `--stdin`: stdin -> stdout; `--check` compara.
- `--config`: `.pengufmt.toml`; `indent`/`tab_size`, `tabs`/`insert_spaces`,
  `blank_lines_max`.
- Omite `@generated`.
- No toca cuerpos `antiquus`, strings, triples, comentarios de contenido.
- Idempotente: `fmt(fmt(x)) == fmt(x)`.
- Preserva BOM/CRLF de forma explícita (o normaliza con flag documentada).

### 5.2 Algoritmo

1. Partir en líneas preservando el terminador.
2. `split_code_and_strings`: segmentos código/literal; reconocer `r"`, `"""`,
   `'''`, chars, escapes.
3. Detectar unidad de indentación (mínima sangría no cero; tab = 1).
4. Reindentar por niveles con `width`/tabs.
5. Normalizar código (nunca literales): `is/as/into`, comas, espacios.
6. Conservar blank lines hasta `blank_lines_max`.
7. Reponer el terminador final.
8. Escritura atómica; si `@generated`, skip.

### 5.3 Tests

- Corpus: `std/`, `psc/src/`, `tests/`, fixtures F1–F6.
- Byte-idéntico contra stage0 en cada archivo (modo paridad).
- Idempotencia en 2 pasadas.
- CRLF, BOM, UTF-8, emoji, triples, raw, `antiquus`, comentarios con `"""`.
- `--check`/`--stdin`/`--diff`/`.pengufmt.toml`.
- Fuzz: líneas aleatorias con strings sin cerrar; no crash.
- No reescribe archivos con symlink fuera del proyecto sin `--force`.

---

## 6. Documentación (`psc doc`)

### 6.1 Contrato

```bash
psc doc [--entry=PATH] [--output=DIR] [--html] [--json]
```

- Markdown por módulo + `README.md`.
- `--html`: `index.html` con búsqueda y enlaces.
- `--json`: modelo de documentación (schema_version 1).
- Determinista: módulos y símbolos en orden estable.

### 6.2 Modelo

Desde F3 (`SemaProgram`, `SemaSymbol`, tipos):

- módulo: nombre, path, doc de cabecera;
- `weave`: firma, parámetros, retorno, flags, doc, ejemplos;
- `rune`/`echo`/`omen`: campos/variantes, doc;
- `const`/`static`: tipo y valor;
- `alias`/`seal`/`concept`;
- `test`: nombre y doc;
- enlaces cruzados a tipos/módulos.

### 6.3 Render

- Markdown:
  - título, resumen, tabla de contenidos;
  - secciones por símbolo, firma en code fence;
  - parámetros/retorno/errores/ejemplos.
- HTML: índice + filtro; sin JS externo.
- No timestamps ni rutas absolutas.
- Escapado correcto de código/HTML.

### 6.4 Tests

- Diff normalizado contra `pengu_doc` para `std/` y proyectos fixture.
- Orden estable.
- Doc comments con markdown, code fences, `<`, `&`.
- `--entry` y módulos huérfanos.
- `--json` schema.
- Determinismo byte a byte en dos ejecuciones.

---

## 7. Assets (`psc assets`)

### 7.1 Contrato

```bash
psc assets [--list] [--force] [--json]
```

- `[assets] dir/module/embed/exclude`.
- `embed=true`: arrays C; `.incbin` para >= umbral.
- `embed=false`: lectura/caché runtime (ya existe; endurecer).
- `--list`: nombre, bytes, constante, modo; `--json`.
- `--force`: ignora hash incremental.
- Genera `src/<module>.pengu`, `build/<module>_assets.h`,
  `build/<module>_assets.c`, `<module>_assets.hash`.

### 7.2 Paridad

- Orden por path relativo; nombres sanitizados; colisiones -> error.
- `PENGU_ASSETS_INCBIN_THRESHOLD` (default 1 MB; 0 desactiva).
- Fallback portable para TCC/MSVC.
- Hash SHA-256 de nombres+bytes+modo+threshold.
- Escritura atómica; no seguir symlinks fuera del proyecto.
- `.incbin` usa paths relativos al bundle/proyecto, seguros para espacios.

### 7.3 Tests

- Fixtures con 0, 1, varios assets, binarios, nombres con espacios/Unicode.
- Compilar y ejecutar `arca.count/name/size/string/bytes`.
- embed y disk (`PENGU_ASSETS_DIR`).
- `.incbin` con umbral 1 y 0; TCC fallback.
- Incremental: mismo hash no reescribe; cambio sí.
- `--list`/`--json`; colisión de identificadores; symlink.
- Build real de proyecto con assets y C glue.

---

## 8. Watch (`psc watch`)

### 8.1 Contrato

```bash
psc watch SCRIPT [--cc=NAME] [--interval=MS] [--once] [--clear]
psc test --watch
```

- Polling (sin inotify).
- Observa entry + **todos los imports resueltos** + `pengu.toml` + runtime/std
  del compilador + assets referenciados.
- Recompila y ejecuta; mata el proceso anterior antes de recompilar.
- Debounce 150 ms; intervalo 300 ms.
- `--once`: una ejecución y sale (CI).
- `--clear`: limpia pantalla entre runs.
- Ctrl-C: mata hijo y sale 130.

### 8.2 Diseño

- Obtener el grafo de F3 tras un check; guardar paths.
- `stat` (mtime + size) de cada path; comparar huella.
- Si cambia: build (cache) + exec; si el proceso anterior sigue, terminarlo.
- Si falla el build, seguir observando.
- `test --watch`: mismo motor, comando de test.

### 8.3 Tests

- Modificar entry -> segunda ejecución.
- Modificar import -> segunda ejecución.
- Modificar manifiesto -> rebuild.
- `--once` y timeout.
- Proceso largo: se mata al cambiar; sin zombis.
- Ctrl-C/SIGINT limpio.

---

## 9. Benchmark (`psc benchmark`)

### 9.1 Contrato

```bash
psc benchmark [--repeat=N] [--warmup=N] [--csv=PATH] [--json] [--only=NAME]
```

- Casos PSC de `benches/` (tabla en `benches/cases.toml` o código).
- Mide build, run (mejor de N), tamaño.
- Warmup antes de medir.
- `--csv`/`--json`; tabla humana.
- Baselines C/Rust/Zig opcionales; `skipped` si falta toolchain.
- No falla por baseline ausente.
- Sin Python en el camino normal.

### 9.2 Tests

- Smoke con 1–2 casos y `--repeat=1`.
- CSV/JSON parseables; columnas estables.
- Toolchain ausente -> skipped, no error.
- No altera fuentes.

---

## 10. Selftest (`psc selftest`)

- Dev-only: exige checkout y Python.
- Detecta `.venv/bin/python`, `PSC_PYTHON`, `python3`.
- `--smoke`, `--json`, `--affected`.
- No se ejecuta en build/run de usuario.
- Documentado en `psc/docs/CLI.md` y CI.

---

## 11. Arnés de paridad

`psc/tools/parity_tools.py` (Python dev-only):

```bash
python psc/tools/parity_tools.py --check
python psc/tools/parity_tools.py --update
python psc/tools/parity_tools.py --only fmt --path std/
```

- Ejecuta stage0 y PSC sobre el mismo archivo/proyecto.
- Normaliza rutas absolutas, line endings y timestamps.
- Compara:
  - `fmt`: bytes.
  - `doc`: Markdown/HTML normalizado.
  - `assets`: interface/header/C (salvo rutas).
- `--update`: escribe goldens (sólo local).
- CI: `--check` en job `psc-tools`.
- Corpus: std, psc/src, fixtures F1–F7, 66 de conformidad.

---

## 12. Fases y estimación

| Fase | Contenido | Semanas |
|---|---|---:|
| F7.0 | Arnés de paridad + fixtures + refactor `cmd/` a módulos | 1 |
| F7a | `fmt` paritario (split, triples, CRLF/BOM, atómico) | 1.5 |
| F7b | `doc` desde símbolos F3 + HTML/búsqueda | 1.5 |
| F7c | `assets` completo (incbin/hash/colisiones) | 1.5 |
| F7d | `watch` con grafo de imports y kill | 1 |
| F7e | `benchmark` nativo + CSV/JSON | 1 |
| F7f | `selftest` dev-only + UX | 0.5 |
| F7g | Tests, CI, ASan, docs, corpus | 1 |
| **Total** | | **7–8** |

Timebox: 6–8 semanas si el arnés y el port de `fmt` se reutilizan bien. Si
`doc`/`assets` se desbordan, F7.5 con aprobación; `fmt`/`watch` no se difieren.

---

## 13. Criterios de aceptación

1. `fmt` es byte-idéntico a stage0 en el corpus acordado y idempotente.
2. `fmt` preserva strings/triples/antiquus y soporta CRLF/BOM.
3. `doc` produce el mismo contenido que `pengu_doc` (orden estable permitido).
4. `doc --html` genera índice con búsqueda; `--json` schema 1.
5. `assets` cubre embed/disk/incbin/exclude/hash y compila/ejecuta.
6. `watch` reacciona a entry, imports, manifiesto y std; mata el hijo anterior.
7. `benchmark` es nativo PSC, CSV/JSON y no falla por baselines ausentes.
8. `selftest` está documentado como dev-only y detecta venv.
9. Paridad `--check` verde en CI para fmt/doc/assets.
10. F1–F6 y bootstrap stage1→stage4 siguen verdes.
11. Preflight gcc/clang/TCC y ASan/UBSan siguen verdes.
12. Sin Python en `build`/`run`/`fmt`/`doc`/`assets`/`watch`/`benchmark`.
13. Escritura atómica y sin seguir symlinks fuera del proyecto.
14. Docs y CHANGELOG actualizados; commit final en `main` (sin push).

---

## 14. Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| `fmt` no alcanza byte-paridad | Alta | Medio | port 1:1 + corpus + fuzz |
| `doc` desde F3 no cubre símbolos | Media | Medio | modelo incremental; fallback textual temporal |
| `.incbin` rompe TCC/MSVC | Media | Medio | fallback por compilador; tests TCC |
| `watch` flaky | Media | Medio | `--once`, fingerprints, tests con timeout |
| Benchmark no determinista | Media | Bajo | warmup, best-of, entorno documentado |
| Scope creep a LSP/deps | Alta | Alto | F8/F9 fuera; stubs |
| Regresión bootstrap | Baja | Alto | gate stage1→stage4 |
| Escritura parcial | Baja | Alto | tmp+rename, fsync, tests de fallo |

---

## 15. Fuera de alcance

- LSP (F8).
- Dependencias/lockfile/package manager (F9).
- `bind` (F10).
- Cross/WASM/MSVC/switchover (F11).
- Cambios de lenguaje, runtime o ABI.
- Publicación/registro.

---

## 16. Archivos previstos

```text
psc/src/psc/fmt/*.pengu
psc/src/psc/docgen/*.pengu
psc/src/psc/assets/*.pengu
psc/src/psc/watch/*.pengu
psc/src/psc/bench/*.pengu
psc/src/psc/cmd/{fmt,doc,assets,watch,benchmark,selftest}.pengu
psc/tools/parity_tools.py
psc/tests/fixtures/f7/**
tests/psc/test_f7_*.py
psc/docs/TOOLS.md
docs/selfhost/F7.md
.github/workflows/ci.yml
.github/workflows/nightly.yml
```

---

## 17. Preguntas para aprobar

1. ¿Aprobado el alcance D1 (sólo paridad/endurecimiento, sin comandos nuevos)?
2. ¿Aprobado portar `fmt` 1:1 de stage0 (D2)?
3. ¿Aprobado `doc` basado en símbolos F3 (D3)?
4. ¿Aprobado `assets` completo con `.incbin` (D4)?
5. ¿Aprobado `watch` con grafo de imports y kill (D5)?
6. ¿Aprobado `benchmark` nativo PSC (D6)?
7. ¿Aprobado el arnés de paridad dev-only (D8)?
8. ¿Aprobado el presupuesto de 6–9 semanas y F7.5 si hace falta?

Si se aprueba, empiezo por **F7.0** (arnés + fixtures + refactor) y **F7a**
(formatter), que son la base de la paridad.
