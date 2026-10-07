# AUDIT — Fase 11 (PenguScript 1.0.0)

> **Alcance:** items 11.1–11.6 de `ROADMAP_1.1.md` (entonces `ROADMAP_2.0.md`),
> más la verificación de las 6 premisas sospechosas del encargo.
> **Base:** `37313d5` (Fase 10 cerrada, `VERSION = 1.0.0-rc1`).
> **Regla aplicada a este mismo roadmap:** ningún gate puede aprobar una propiedad
> inspeccionando texto; se compila, se ejecuta o se mide. Los dos hallazgos que más
> importan aquí (F11-N7, F11-N8) **no** vinieron de leer código: vinieron de correr
> el release de verdad.

## Tabla de items

| # | Estado | Commit | Evidencia de una línea |
|---|--------|--------|------------------------|
| 11.1 | ✅ cerrado | `f44c8b1` | `pengu -V` → `pengu 1.0.0`; `pytest tests/test_version.py tests/test_std_versioning.py tests/test_migration_doc.py -q` → **47 passed, 6 skipped** |
| 11.2 | ✅ cerrado | `2d3c70f` | `python scripts/release_version.py` → `v1.0.0`; `pytest tests/test_migration_doc.py tests/test_ci_workflows.py -q` → **115 passed** |
| 11.3 | ✅ mecanismo / ⏸️ tag humano | este commit | `pytest tests/test_release_handoff.py -q` → 17 passed; dry-run portable: `pengu`, 17 `runtime/*.a` y `pengus-1.0.0.vsix`, 229 archivos con SHA-256; `git tag -s` **no ejecutable aquí** (sin clave GPG) |
| 11.4 | ✅ cerrado | este commit | `docs/ANNOUNCEMENT_1.0.md`; matriz medida en esta máquina: gcc **54/54**, clang **54/54** (`run_all.py --cc gcc|clang`) |
| 11.5 | ✅ cerrado | `4dfa524` | `git mv ROADMAP_2.0.md ROADMAP_1.1.md`; `pytest tests/test_version.py -q` → **30 passed, 6 skipped** tras reapuntar `HISTORICAL` |
| 11.6 | ✅ cerrado | `7bdc7b2` | `pytest tests/test_compliance_corpus.py -q` → **61 passed** (1 m 43 s); `pytest tests/test_migration_doc.py tests/test_language_policy.py tests/test_migration_corpus.py -q` → **44 passed** (el corpus pasa de 10 a 11 programas con `1.0.0/frozen-surface.pengu`, F11-N12) |

## Verificación de las premisas del encargo

| # | Premisa | Comando | Resultado |
|---|---------|---------|-----------|
| **A** | "Subir la versión a 1.0.0 en todos los sitios" | `grep -rn "1\.0\.0-rc1"` | ✅ **CONFIRMADA**, y con más superficie de la que listaba el encargo: **89 ficheros** en el commit (`git show --numstat`), no solo los 12 claims + 26 módulos — 26 son `docs/api/*.md` regenerados. Incluye `pengu_parser/pengu_codegen.py`, los **14** `tests/std_programs/*.pengu` (F10-N13) y el *badge* del `README.md` |
| **B** | "`pengu -V` → `1.0.0`" | `python -m pengu_project -V` | ✅ **CONFIRMADA**: antes `pengu 1.0.0-rc1`, ahora `pengu 1.0.0`. El texto exacto sigue siendo `pengu <ver>` y el gate no lo afirma de otra forma (F10-N11) |
| **C** | "Tag firmado y publicado aquí" | `git config user.signingkey` | ❌ **REFUTADA como automatizable** (exit 1, sin clave) → **F11-N4**: ⏸️ humano, con comando exacto en el anuncio §Publicación |
| **D** | "Los artefactos pasan `release-verify.yml`" | `python make_release.py --layout portable --print-hashes` | ✅ **CONFIRMADA en local**: los 3 artefactos se construyen y el smoke test pasa. El workflow no corre aquí (sin credenciales) |
| **E** | "`CHANGELOG` con `[1.0.0]`" | `grep -n "^## \[" CHANGELOG.md` | ✅ **CONFIRMADA**: entrada nueva arriba con fecha ISO; las `[Unreleased] — FASE N` históricas intactas |
| **F** | "Corpus de compliance y migración" | `ls tests/compliance/ tests/migration/` | ⚠️ **PARCIALMENTE REFUTADA** → **F11-N1**: `tests/migration/README.md` existía, `tests/compliance/README.md` **no**. Lo que sí existía y se ejecuta es `corpus.json` + `run_all.py` + `EXPECTED.md` |

## Hallazgos nuevos (`F11-N*`)

| Código | Hallazgo | Estado |
|--------|----------|--------|
| **F11-N1** | `tests/compliance/README.md` **no existía**; el item 11.6 pedía "añadir cabecera normativa" a un fichero inexistente. Se creó con el alcance **medido** (54 programas, §2–§19; §20–§21 fuera) y su límite declarado | Cerrado (11.6) |
| **F11-N2** | `CONTRIBUTING.md` seguía en **"Current version: 0.16.0, in beta"** y el *badge* del `README.md` en `1.0.0-rc1`; **ninguna** de las 12 afirmaciones gateadas los cubría. La Fase 10 declaró "0 deriva de versión" midiendo solo sus 6 ficheros | Cerrado (11.1): ambos sitios añadidos a `CURRENT_VERSION_CLAIMS` |
| **F11-N3** | Promover el `CHANGELOG` rompía `test_release_version_skips_unreleased`, que fijaba `v0.16.0` a mano: un test sobre "saltar `[Unreleased]`" que en realidad fijaba *qué* release era el último | Cerrado (11.2): el test deriva de `VERSION` |
| **F11-N4** | El entorno **no tiene clave GPG**: 11.3 no es automatizable. No es un defecto del repo | ⏸️ humano |
| **F11-N5** | `SECURITY.md` mantenía `0.16.x` como "con fixes hasta que salga 1.0.0" y `1.0.0-rc1` como "current pre-release": publicada 1.0.0, las dos frases eran falsas. El ratchet de tokens no las cubría porque `0.16.x` estaba justificado por una razón que dejó de ser cierta | Cerrado (11.1) |
| **F11-N6** | `RELEASE_CHECKLIST.md` §2 pedía "publish checksums **+ GPG signature**" mientras `SECURITY.md` §Release integrity dice que **no se firma con GPG**. Dos documentos de release afirmando lo contrario; el gate de reivindicaciones refutadas no cubría esa caja | Cerrado (11.3) |
| **F11-N7** | `make_release.py` copiaba **todos** los `*.vsix` de `vscode-extension/`. Como `*.vsix` está en `.gitignore`, un árbol que ya cortó un release arrastra el anterior: **medido** en el dry-run, `pengucc_build/` quedó con `pengus-1.0.0.vsix` **y** el obsoleto `pengus-1.0.0-rc1.vsix` | Cerrado (11.3): `select_vsix_artifacts()`; gate con C2 verificado |
| **F11-N8** | `--print-hashes` **solo se honraba con `--archive-only`**. El comando que el roadmap y el anuncio citan para reproducibilidad no imprimía **nada**: un "mismos hashes" podía pasar mirando una pantalla vacía — un gate por apariencia, justo lo que la regla C1 prohíbe | Cerrado (11.3): la ruta de empaquetado imprime los SHA-256; gate con C2 verificado |
| **F11-N9** | Con F11-N8 arreglado, dos corridas del **mismo commit** dan **227 de 229** hashes idénticos: difieren `pengus-1.0.0.vsix` (`12e7108b…` vs `0af4fae1…`; zip con marcas de tiempo de `vsce`) y `runtime/include/pengu_runtime.h.gch` (`7722efa5…` vs `77b8b4f8…`; PCH de gcc). El brief de la fase pedía "mismos hashes" y el docstring de `test_reproducible_release.py` decía "two builds of the same commit must produce the same bytes": las dos frases son **más anchas** que lo medido | **Documentado** (no se arregla en 1.0): candidato **X** de 1.1; el contrato que sí se gatea es re-archivar el mismo árbol byte a byte |
| **F11-N10** | El brief cita **`F8-N11`** como el hallazgo que retiró MSVC. Ese código **no existe**: `AUDIT_1.0_FASE8.md` enumera F8-N1…N10 (sin N11) y la retirada es el **item 8.11**; el dialecto MSVC lo arregló **F8-N3**. Un identificador de hallazgo inventado es una afirmación sin gate, justo lo que la fase persigue | Cerrado: el anuncio y el CHANGELOG citan "Fase 8, item 8.11" |
| **F11-N11** | Correr el release documentado (`python make_release.py`) dejaba `scratch/smoke_release_test/` en el árbol. `scratch/` está en `.gitignore`, pero `test_audit_regressions.py::test_historical_cleanup_targets_are_gone` exige que **no exista**: "corre el release y luego `pytest tests`" fallaba. Medido en la suite completa posterior al dry-run (**2 failed** de 3 499: este y F11-N12) | Cerrado: `cleanup_smoke_scratch()` en un `finally` de `main()`; gate con C2 verificado |
| **F11-N12** | Promover el `CHANGELOG` a `[1.0.0]` hizo fallar `test_migration_corpus.py::test_corpus_covers_every_documented_published_version`: la línea minor `1.0` no tenía programa de migración. Misma clase que F11-N3 — un corpus indexado por la lista de versiones del changelog | Cerrado: `tests/migration/1.0.0/frozen-surface.pengu` + entrada en `EXPECTED.json`; el corpus pasa de 10 a 11 programas (9 ok, 2 error) |

### C2 de F11-N7 / F11-N8 / F11-N11 (verificado, no afirmado)

Se revirtió cada arreglo por separado y se corrió su gate:

- quitar el bloque `if args.print_hashes:` posterior al banner → `test_print_hashes_is_not_a_no_op_on_the_packaging_path` **FAILED**;
- volver a `list(ext_dir.glob("*.vsix"))` → `test_a_stale_vsix_is_not_shipped` **FAILED** (el `-rc1` se copiaba);
- quitar el `finally: cleanup_smoke_scratch()` → `test_the_smoke_test_scratch_is_cleaned_up` **FAILED** (el `scratch/` quedaba).

Con los arreglos: `pytest tests/test_reproducible_release.py -q` → **17 passed**.

## Diferido (con medición, a `ROADMAP_1.1.md`)

Ninguno de los diferidos es nuevo de esta fase: los candidatos A–W del roadmap
siguen tal cual, cada uno con su medición y su criterio de reapertura. De los
hallazgos **F11-N1…N12**, **diez se cerraron en la fase**, uno se registró como ⏸️
humano (**F11-N4**) y uno se difirió **con medición** a 1.1: **F11-N9** (los dos
artefactos de herramienta que no son byte-reproducibles run-to-run), como
candidato **X** de `ROADMAP_1.1.md`.

## Refutaciones honestas

- **"Los 3 artefactos pasan `release-verify.yml`"** no se puede afirmar aquí: el
  workflow no tiene credenciales ni un release publicado. Lo que se midió es el
  dry-run local (los 3 artefactos se construyen, el smoke test pasa y `pengu -V`
  del artefacto dice `1.0.0`). El encargo pedía exactamente eso y no se maquilla.
- **"El tag firmado cierra 11.3"**: no. 11.3 queda **⏸️ humano** con el mecanismo
  verificado. Un audit que marcara 11.3 como cerrado estaría mintiendo.
- **"La subida de versión toca 12 afirmaciones"**: son 12 *claims* gateados, pero
  la superficie real del bump es de **89 ficheros** (`git show --numstat` f44c8b1;
  26 son `docs/api/*.md` regenerados), incluido el *badge* del README
  y dos sitios sin gate que llevaban releases de retraso (F11-N2).

## Cierre

```console
$ pengu -V                                     # pengu 1.0.0
$ pytest tests/test_version.py tests/test_std_versioning.py tests/test_migration_doc.py -q
$ pytest tests/test_compliance_corpus.py tests/test_migration_corpus.py -q
$ pytest tests/test_freeze_manifest.py tests/test_release_claims.py -q
$ pytest tests/test_reproducible_release.py -q
$ python make_release.py --layout portable --print-hashes
$ python make_release.py --layout portable --print-hashes   # 227/229 iguales; 2 no (F11-N9)
$ python -m pengu_project check --bogus; echo $?               # 2
$ python -m pengu_project check no_existe.pengu; echo $?       # 1
```

La línea de los hashes lleva la anotación medida, no la promesa del brief: el
comando imprime 229 SHA-256 y **dos** cambian entre corridas (F11-N9). El
contrato que el gate sí sostiene es el de `make_archive` sobre el mismo árbol.

**Suite completa, medida tras los arreglos:** `pytest tests -q` →
**3 429 passed, 27 skipped, 46 xfailed, 0 failed** (29 min 31 s). La primera
corrida, antes de F11-N11/F11-N12, dio **2 failed de 3 499**; los dos se
diagnosticaron, se arreglaron con un gate que falla al revertir y no reaparecen.

**Estado final:** `pengu -V` → `pengu 1.0.0`; suite verde; `ROADMAP_1.1.md` con lo
diferido; anuncio con la lista explícita de lo que 1.0 **no** es; y el tag firmado
en manos humanas, declarado como tal.
