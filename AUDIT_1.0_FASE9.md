# AUDIT_1.0 — FASE 9 (ROADMAP 2.0): Herramientas de release

> **Alcance:** items 9.1–9.12 de `ROADMAP_2.0.md`.
> **Regla de la fase (C3):** ninguna premisa se da por buena sin reproducirla con un
> comando **antes** de tocar código; ninguna propiedad se aprueba inspeccionando
> texto (AUDIT §15.2).
> **Formato:** tablas con el comando y la línea decisiva, no logs.

---

## 1. Verificación de premisas (antes de tocar código)

| # | Premisa del roadmap | Comando | Resultado medido | Veredicto |
|---|---------------------|---------|------------------|-----------|
| 9.1 | *"`extern_manifest.py` descarga sin verificar el hash"* | `grep -n "hashlib\|sha256" extern_manifest.py` | rc=1, **0 coincidencias**; `MANIFEST` era `{nombre: url}`, sin sitio donde guardar un digest | ✅ **CONFIRMADA** (AUDIT §13.3 / A12) |
| 9.1b | El mensaje final afirma verificación | `extern_manifest.py:141` → `"=== All external C libraries verified. ==="` con el guardado de `:83-85` (`extracted_path.exists()`) | Imprimía "verified" mirando si existe una carpeta | ✅ **CONFIRMADA** (AUDIT §18.1 #5) |
| 9.2 | *"`pengu_tcc.py` descarga el ZIP sin verificar"* | `grep -n "hashlib\|sha256" pengu_tcc.py` | rc=1, **0 coincidencias**; `zipfile … extractall(dest_dir)` directo | ✅ **CONFIRMADA** |
| 9.3 | *"El workflow de release sólo avisa (`::notice::`) si el SHA no coincide"* | `grep -rn "PENGU_TCC_SHA256" .` | Sólo `release.yml:76,85,98`; la variable **nunca se define** en el repo; con `$expected` vacío el paso imprime `::notice::` y sigue | ✅ **CONFIRMADA** (AUDIT §13.3 #4 / §18.1 #4) |
| 9.4 | *"La extracción no está endurecida"* | `grep -rn "extractall" --include=*.py .` | **3 sitios**, ninguno con `filter=`: `extern_manifest.py:124`, `pengu_tcc.py:139`, **`build_runtime.py:932`** | ✅ **CONFIRMADA, y peor de lo documentado** → **F9-N1** |
| 9.5 | *"`docs/FUZZING.md` y `RELEASE_CHECKLIST.md` prometen 72 h de fuzzing, pero GitHub mata los jobs a las 6 h"* | `grep -rn "72 h" docs/FUZZING.md RELEASE_CHECKLIST.md` | `docs/FUZZING.md:69` → `Release branch / manual \| 72 hours per harness`; `RELEASE_CHECKLIST.md:41` → `72 h without a crash` | ✅ **CONFIRMADA** (AUDIT §13.3 #8/#9) |
| 9.5b | *"…Ya cubierto parcialmente por la Fase 8 (F8-N5)"* | `grep -n "timeout-minutes" .github/workflows/*.yml` | Máximo real **350** (`fuzz.yml`), `nightly.yml` **150** con 4 shards; los **YAML** ya estaban arreglados en `dca109f`/`nightly.yml`, **los documentos no** | ✅ **CONFIRMADA**: el arreglo de la Fase 8 era parcial → **F9-N6** |
| 9.6 | *"`ci.yml` crea el tag y `release.yml` se dispara por el push del tag, pero el traspaso no funciona"* | `sed -n '211,254p' .github/workflows/ci.yml` (antes) | El job `auto-tag` hacía `git push origin "$TAG"` con `GITHUB_TOKEN` y **no** contenía ningún `workflow_dispatch` ni `actions: write`. GitHub documenta que un push con `GITHUB_TOKEN` no crea una ejecución de workflow (`workflow_dispatch` es la excepción) | ✅ **CONFIRMADA** (AUDIT §18.1 #10, no ejecutable localmente) |
| 9.7 | `release-verify.yml` no existe | `ls .github/workflows/` | No está; el workflow `release.yml` termina en `gh release create` y nadie vuelve a tocar los artefactos | ✅ **CONFIRMADA** |
| 9.8 | No hay `SOURCE_DATE_EPOCH` ni orden fijo en `tar`/`zip` | `grep -rn "SOURCE_DATE_EPOCH" --include=*.py --include=*.yml .` | **0 coincidencias** fuera de `extern/curl-…/docs`; los workflows archivan con `tar -czvf` y `Compress-Archive` (ambos incrustan la hora) | ✅ **CONFIRMADA** |
| 9.9 | *"Los artefactos de macOS pasan `spctl --assess`"* | `grep -rn "codesign\|spctl" .github/workflows/release.yml` | Firma **ad-hoc** (`codesign --sign - --force "$t" \|\| true`) y `codesign --verify … \|\| echo "::warning::…"`. No hay cuenta de desarrollador de Apple en el proyecto, no hay `notarytool` y `spctl --assess` **rechaza** un binario ad-hoc en cuarentena | ❌ **REFUTADA** → 9.9 **retirado**, no implementado (Anexo D) |
| 9.10 | `docs/RELEASE.md` no existe | `ls docs/RELEASE.md` | No existe | ✅ **CONFIRMADA** |
| 9.11 | *"Cada casilla debe tener un gate; elimina las 5 refutadas de AUDIT §13.3"* | Parser de `tests/test_release_claims.py` sobre `git show HEAD:RELEASE_CHECKLIST.md` | **16** casillas automatizadas, **8 sin gate** (antes); 5 afirmaciones refutadas presentes, 3 de ellas sin marca `❌` | ✅ **CONFIRMADA** |
| 9.12 | *"`pengu_paths.py` ya soporta los 4 layouts — verificarlo con artefactos reales, no con tests unitarios"* | `grep -n "verify_release_artifact\|--layout" .github/workflows/ci.yml` | Nada: CI empaquetaba, subía el artefacto y **nunca lo descomprimía ni lo ejecutaba** | ✅ **CONFIRMADA** |

---

## 2. Estado item por item

| # | Estado | Commit | Qué se hizo | Evidencia (comando) |
|---|--------|--------|-------------|---------------------|
| 9.1 | ✅ cerrado | `4efb693 fase9(9.1,9.2,9.3,9.4)` | `MANIFEST` con `{url, sha256}` para los 16; hash sobre el stream **antes** de extraer; `DigestMismatchError`; sello `.pengu_verified.json`; `--verify`; `force=True` en la ruta de release | `pytest tests/test_extern_manifest_digests.py -q` → **15 passed**. Pipeline real con `zlib`: `[SUCCESS] zlib installed to zlib-1.3.2 (sha256 verified)` y sello `bb329a0a…` |
| 9.2 | ✅ cerrado | `4efb693 fase9(9.1,9.2,9.3,9.4)` | `TCC_RELEASE_SHA256 = bba01756…1fb5` en `pengu_tcc.py`; `TccIntegrityError` **aborta**; `safe_extract_zip` | `pytest tests/test_tcc_integrity.py -q` → **12 passed, 1 skipped** (el skipped es la descarga real, `PENGU_NETWORK_TESTS=1`). Medición: el ZIP upstream pesa **814 898 B** y hashea exactamente al valor fijado |
| 9.3 | ✅ cerrado | `4efb693 fase9(9.1,9.2,9.3,9.4)` | `release.yml` llama a `python pengu_tcc.py --stage build/tcc-dist`; el `::notice::` y el `Get-FileHash` en pwsh desaparecen | `grep -c "::notice::TinyCC digest" .github/workflows/release.yml` → **0**. Test `test_release_workflow_uses_the_shared_module_instead_of_reimplementing_it` |
| 9.4 | ✅ cerrado | `4efb693 fase9(9.1,9.2,9.3,9.4)` | `pengu_archive.py` (`safe_extract_zip`/`safe_extract_tar`); los 3 sitios validan los miembros antes de escribir (el único `extractall(` sin `filter=` es el interno del validador); test estructural | `pytest tests/test_archive_extraction.py -q` → **11 passed** (tar `../`, absoluto, anidado; zip `../`, absoluto, unidad `C:`, symlink; control positivo) |
| 9.5 | ✅ cerrado | `18f3b7b fase9(9.5,9.10,9.11)` | `docs/FUZZING.md` §CI schedule y `RELEASE_CHECKLIST.md` con el presupuesto real; test que falla si aparece una promesa > 6 h | `pytest tests/test_ci_workflows.py -q -k fuzz_docs` → **2 passed**. `grep -rn "72 h" docs/FUZZING.md RELEASE_CHECKLIST.md` → sólo en la frase que lo **refuta** |
| 9.6 | ✅ cerrado (con limitación registrada) | `2a8469a fase9(9.6,9.7,9.12)` | `auto-tag` marca `created=true/false`, y si **él** creó el tag hace `gh workflow run release.yml --ref main -f version=$TAG`; `actions: write` | `pytest tests/test_release_handoff.py -q` → **17 passed**. **Limitación:** no verificable end-to-end aquí (sin fork/credenciales) → §5 |
| 9.7 | ✅ cerrado | `2a8469a fase9(9.6,9.7,9.12)` | `release-verify.yml` + `scripts/verify_release_artifact.py`; matriz de 5 entradas; `release.yml` lo despacha tras publicar | `pytest tests/test_release_verify.py -q` → **13 passed**, **19 passed** y, además, medido contra el artefacto real de `make_release.py` en los dos layouts (§3c): `pengu -V → 0.16.0`, `build rc=0`, `run hello.pengu → Hello, world!` |
| 9.8 | ✅ cerrado, **medido** | `9720da7 fase9(9.8,9.9)` | `SOURCE_DATE_EPOCH` (o commit de `HEAD`), `PYTHONHASHSEED=0`, `TZ=UTC`; `--archive-only` determinista; workflows dejan de usar `tar -czf`/`Compress-Archive` | §3 (dos builds del binario y dos del archivo → **hash idéntico**) |
| 9.9 | ❌ **reivindicación retirada** | `9720da7 fase9(9.8,9.9)` | No hay cuenta Apple → no hay notarización. `release.yml` gatea `codesign --verify --strict` (antes `\|\| true`); `spctl` se registra en `release-verify.yml`; `docs/RELEASE.md` §macOS y `docs/PENGU_BUILD.md` lo dicen | `grep -rn "notariz" --include=*.md .` → todas las apariciones afirman que **no** se hace. `grep -c "codesign --verify --strict" .github/workflows/release.yml` → 1 |
| 9.10 | ✅ cerrado | `18f3b7b fase9(9.5,9.10,9.11)` | `docs/RELEASE.md`: pipeline de 4 workflows, gates, reproducibilidad, sección macOS, tabla "si un gate falla" | `pytest tests/test_release_claims.py -q` → 13 passed, incluye `test_release_documents_cross_reference_each_other` |
| 9.11 | ✅ cerrado | `18f3b7b fase9(9.5,9.10,9.11)` | Checklist reescrito: **16** casillas automatizadas, **0 sin gate**; §2 marcada `manual:`; test que lo vigila y que comprueba que cada ruta citada existe | Parser sobre la versión anterior (`git show 833766c:RELEASE_CHECKLIST.md`): **8 de 16 sin gate → 0 de 16**. C2: quitar un gate → `AssertionError` |
| 9.12 | ✅ cerrado | `2a8469a fase9(9.6,9.7,9.12)` | Matriz portable/FHS en `release-verify.yml` **y** en `ci.yml`; el portón FHS prueba que el prefijo se usó | §3c: `--layout portable` y `--layout fhs` sobre el artefacto real, éste con el control negativo; `grep -c "verify_release_artifact" .github/workflows/ci.yml` → 2 (portable + fhs) |

---

## 3. La medición de reproducibilidad (item 9.8)

Comando (idéntico en lo esencial a `workflow: ci.yml` / `release.yml`):

```bash
python - <<'PY'   # dos corridas de PyInstaller sobre el mismo commit
import make_release as mr; ...; mr.package_with_pyinstaller(py, DIST)
PY
```

| Corrida | Ruta de salida | SHA-256 de `pengu` | Tamaño |
|---|---|---|---|
| 1 | `/tmp/repro-dist` | `8bf8946097219725c5e6d2478bd3c35751f4a4dfe7dccdda5f273ab5807de738` | 17 584 704 B |
| 2 | `/tmp/repro-dist` | `8bf8946097219725c5e6d2478bd3c35751f4a4dfe7dccdda5f273ab5807de738` | 17 584 704 B |
| 3 | `/tmp/repro-dist-b` (**otra ruta**) | `8bf8946097219725c5e6d2478bd3c35751f4a4dfe7dccdda5f273ab5807de738` | 17 584 704 B |

```bash
python make_release.py --archive-only --dist-dir /tmp/repro-dist --archive /tmp/rep-a.tar.gz
python make_release.py --archive-only --dist-dir /tmp/repro-dist --archive /tmp/rep-b.tar.gz
sha256sum /tmp/rep-a.tar.gz /tmp/rep-b.tar.gz
86ec04102aad651b1aa0360a97ff7eb84e6de95a7bc98a1bb13730f88c64054b  /tmp/rep-a.tar.gz
86ec04102aad651b1aa0360a97ff7eb84e6de95a7bc98a1bb13730f88c64054b  /tmp/rep-b.tar.gz
```

**Conclusión:** la reivindicación de reproducibilidad **se mantiene** para el
mismo commit en una máquina, incluso cambiando el `--distpath` (que era el
sospechoso natural: PyInstaller incrusta rutas). Lo que **no** se afirma:
reproducibilidad **entre máquinas o sistemas operativos** (el bootloader de
PyInstaller es distinto por plataforma y no se ha medido aquí). El test que evita
la regresión es `tests/test_reproducible_release.py` (14 passed, incluido que el
gzip no lleve mtime y que el epoch salga del commit, nunca del reloj).

---

## 3b. La extracción endurecida, probada contra los archivos reales

Un validador que rechazara archivos legítimos sería un gate que rompe el build.
Medido con tres de las dependencias reales (descarga + digest + extracción por
`safe_extract_tar`, en `/tmp`, sin tocar `extern/`):

| Dependencia | Formato | Symlinks en el árbol extraído | Resultado |
|---|---|---|---|
| `mbedtls` 4.2.0 | `.tar.bz2` | **147** | ✅ extrae, digest coincide |
| `libmicrohttpd` 1.0.1 | `.tar.gz` | 0 | ✅ extrae, digest coincide |
| `raylib` 6.0 | `.tar.gz` (archivo generado por GitHub) | 0 | ✅ extrae, digest coincide |

Los symlinks de mbedtls son **relativos y quedan dentro** del destino
(`../../../mldsa/mldsa_native.h`), que es el caso que `filter="data"` admite; el
validador los rechaza si apuntan fuera (probado con un tar sintético en
`tests/test_archive_extraction.py`). Además, estas tres descargas son una
**segunda verificación independiente** de la tabla de digests: los bytes
descargados otra vez hashean a los valores fijados en el commit.

**Y la prueba completa:** `python make_release.py` (ruta de release, `force=True`)
recorrió las **16** entradas — descarga, hash contra el digest fijado y
extracción endurecida — sin un solo fallo, y dejó `extern/.pengu_verified.json`
con las 16 entradas; la llamada de `build_runtime.py` (sin `force`) las reutiliza
por el sello en vez de re-descargar.

---

## 3c. El gate de artefactos, medido contra un artefacto de verdad

`python make_release.py --skip-tests` terminó con **rc=0** (16/16 dependencias
verificadas y extraídas, runtime recompilado, VSIX y binario empaquetados). Con
ese artefacto real, el mismo comando que corre CI:

```bash
python make_release.py --archive-only --dist-dir pengucc_build --archive /tmp/pengu-linux-x64.tar.gz
python scripts/verify_release_artifact.py --artifact /tmp/pengu-linux-x64.tar.gz \
    --layout portable --expected-version 0.16.0
python scripts/verify_release_artifact.py --artifact /tmp/pengu-linux-x64.tar.gz \
    --layout fhs --expected-version 0.16.0
```

| Layout | `pengu -V` | `pengu new exe` + `build` | `pengu run hello.pengu` | Control negativo |
|---|---|---|---|---|
| `portable` | 0.16.0 | rc=0 | `Hello, world!` | — |
| `fhs` | 0.16.0 | rc=0 | `Hello, world!` | ✅ ocultar `<prefix>/lib/pengu` rompe el build con `libpengu_runtime.a not found` |

El binario real de esa corrida hashea a
`8bf8946097219725c5e6d2478bd3c35751f4a4dfe7dccdda5f273ab5807de738` — **el mismo
valor** de las dos corridas de §3, ahora a través del script completo: tres
mediciones independientes del mismo commit.

**Y el gate tenía dos defectos que sólo aparecen al ejecutarlo contra el
artefacto real (F9-N7):** (a) el directorio de trabajo se pasaba como
`<workdir>/scratch` sin crearlo, así que el primer subproceso moría con un
`FileNotFoundError` en vez de fallar un check; (b) `install_fhs` buscaba
`runtime/lib/*.a` cuando el layout portable deja los `.a` **directamente** en
`runtime/`, y `main()` confundía la ruta del binario con la del prefijo. El test
que existía usaba un árbol sintético con la suposición equivocada, así que no
podía verlo: ahora hay un artefacto sintético con el layout **real**
(`tests/fixtures/fake_pengu.py` + `test_script_verifies_a_whole_artifact_end_to_end`
en las dos variantes) y está medido que revertir (b) hace fallar 2 tests (los de
FHS) mientras el portable sigue verde.


---

## 4. Hallazgos nuevos

| ID | Hallazgo | Medición | Estado |
|----|----------|----------|--------|
| **F9-N1** | El roadmap contaba **dos** `extractall` sin endurecer; el inventario real es **tres**: `build_runtime.py:932` extraía el ZIP del WebUI precompilado sin validar rutas | `grep -rn "extractall" --include=*.py .` → 3 sitios, 0 con `filter=` | ✅ corregido en 9.4 |
| **F9-N2** | El evento `release: published` sufre la **misma** restricción de `GITHUB_TOKEN` que el push del tag: un release creado por `release.yml` no arranca `release-verify.yml`. El roadmap sólo prevía el problema en el tag | `release.yml` no definía `actions: write` ni despachaba nada; `release-verify.yml` no existía | ✅ corregido: dispatch explícito desde `create-release` |
| **F9-N3** | La firma de macOS era `codesign --sign - --force "$t" \|\| true` y la verificación un `::warning::`: un artefacto **sin firma válida** se publicaba con el job en verde | `sed -n '137,151p' .github/workflows/release.yml` (antes) | ✅ corregido en 9.9: `codesign --verify --strict` sin `\|\| true` |
| **F9-N4** | `_download_windows_tcc` envolvía descarga **y extracción** en un `except Exception → return None`: un fallo de integridad (ZIP con `../evil`) se degradaba a "TCC no disponible", indistinguible de un fallo de red, y el release seguía sin TCC | El test `test_a_hostile_zip_is_refused_by_the_shared_validator` falló con `return None` en vez de excepción antes del arreglo | ✅ corregido en 9.2 (`UnsafeArchiveError` propaga) |
| **F9-N5** | **7 de los 16** digests fijan tarballs generados por GitHub (`/archive/refs/tags/…`), que **no son estables por contrato** (GitHub ya cambió el envoltorio gzip una vez). Antes esto habría pasado desapercibido; ahora un cambio upstream **aborta** el build | `grep -o "archive/refs/tags" extern_manifest.py \| wc -l` → 7 | ⚠️ documentado + ruta de re-pin (`--update`); migrar a assets de release queda para 1.1 |
| **F9-N6** | La Fase 8 cerró F8-N5 en los **workflows** (`dca109f`, `nightly.yml`) pero los **documentos** siguieron prometiendo 72 h: el arreglo era parcial porque nadie gateaba los `.md` | `grep -rn "72 h" docs/FUZZING.md RELEASE_CHECKLIST.md` → 2 coincidencias **después** de la Fase 8 | ✅ corregido en 9.5, con test que falla si vuelve |
| **F9-N7** | El portón de artefactos (9.7/9.12) tenía dos defectos que sólo aparecen al ejecutarlo contra un artefacto real: el scratch no se creaba y `install_fhs`/`main` confundían el prefijo con el binario y buscaban `runtime/lib/*.a` (el layout portable pone los `.a` en `runtime/`). El test previo usaba un árbol sintético con la suposición equivocada | Medido: revertir el mapeo `runtime/*.a` → 2 tests fallan (FHS) y el portable pasa; revertir el scratch → 2 tests fallan | ✅ corregido en 9.7/9.12 + test hermético con el layout real |

---

## 5. Refutaciones y limitaciones

| Afirmación | Fuente | Realidad medida | Resolución |
|---|---|---|---|
| *"El tag dispara el release"* | `ci.yml:222-225` (antes) | Un push con `GITHUB_TOKEN` no crea una ejecución de workflow; el job no tenía `workflow_dispatch` ni `actions: write`, así que la vía no existía | Arreglado con dispatch explícito (9.6). **Limitación:** verificación end-to-end en un fork **no reproducible en este entorno** (sin credenciales de GitHub ni fork). Lo entregado es el mecanismo + el gate de cableado (`tests/test_release_handoff.py`), y la limitación queda escrita aquí y en `tests/test_release_handoff.py` |
| *"El artefacto de macOS pasa `spctl --assess`"* | `ROADMAP_2.0.md` 9.9 | No hay cuenta de desarrollador de Apple: no hay `notarytool`, y un binario ad-hoc en cuarentena es rechazado por Gatekeeper | **Reivindicación retirada** (regla del Anexo D). Lo que se afirma es sólo `codesign --verify --strict` |
| *"72 h per harness"* | `docs/FUZZING.md:69`, `RELEASE_CHECKLIST.md:41` | GitHub mata el job a las 6 h; el techo real medido es 350 min en `fuzz.yml` y 4 × 90 min en `nightly.yml` | Retirado de ambos documentos y gateado (9.5) |
| *"`PENGU_TCC_SHA256` (or the default digest below) must match"* | `release.yml:76-77` (antes) | No había digest por defecto ni en el workflow ni en el código; el paso sólo imprimía un `::notice::` | Implementado con un digest real **en el código** (9.2/9.3) |
| *"=== All external C libraries verified. ==="* | `extern_manifest.py:141` (antes) | Sólo comprobaba que existiera el directorio extraído | Ahora se imprime tras verificar los 16 digests (9.1) |

**Diferido a 1.1:** ninguno de los 12 items. La única salida no-✅ es la
**retirada** de la notarización (9.9), que no es un diferimiento sino una
afirmación eliminada, y **F9-N5** (migrar los 7 tarballs de GitHub a assets
estables), que está en el Anexo "⏸️ Diferido a 1.1+" con su justificación.

---

## 6. Evidencia C2 (el test falla al revertir el fix)

| Item | Test | Reversión probada | Resultado |
|------|------|-------------------|-----------|
| 9.1 | `test_wrong_digest_fails_before_extracting` | quitar la comparación del digest | el payload se extrae → falla |
| 9.2 | `test_wrong_digest_is_a_hard_failure_and_extracts_nothing` | volver al `extractall` sin comparar | el `tcc.exe` falso aparece en `dest_dir` → falla |
| 9.3 | `test_release_workflow_uses_the_shared_module…` | reponer un `Get-FileHash`/`::notice::` en el workflow | falla |
| 9.4 | `test_no_first_party_extractall_bypasses_the_guard` + los 4 casos hostiles | quitar la validación | el archivo se escribe fuera de `dest/` → falla |
| 9.5 | `test_fuzz_docs_do_not_promise_more_than_github_allows` | reponer "72 hours per harness" | `offenders` ≠ [] → falla |
| 9.6 | `test_auto_tag_dispatches_the_release_workflow` | quitar el paso de dispatch | falla |
| 9.7 | `test_script_fails_when_the_version_does_not_match` | desactivar la comparación de versión | `rc=0` en vez de 1 → falla |
| 9.11 | `test_every_automated_box_has_a_gate` | quitar el backtick de un comando | verificado: `[1. Automated] Standard library formatting…` → falla |
| 9.12 | `test_ci_verifies_the_packaged_artifact_in_both_layouts` | quitar el paso `--layout fhs` | falla |

---

## 7. Cierre

- `pytest tests -q -p no:cacheprovider --timeout=1800` tras la fase:
  **3366 passed, 27 skipped, 46 xfailed, 0 failed en 35:56**.
  Referencia de la Fase 8 en el mismo comando: **3275 passed, 25 skipped, 46
  xfailed, 0 failed**. La fase añade **+91 pasados / +2 skipped / 0 xfailed**: 7
  módulos de test nuevos con **79 funciones** (96 casos contando
  parametrizaciones) y **ningún `xfail` tocado**: los pines de la
  Fase 8 siguen intactos.
- `python make_release.py`: el packager sigue funcionando y ahora **verifica**
  cada archivo externo antes de extraerlo.
- Los tres documentos de cierre: este audit, `CHANGELOG.md`
  (`[Unreleased] — FASE 9`) y `ROADMAP_2.0.md` (tabla de estado + Anexo de
  diferidos).
- **Cómo se repartió el trabajo en commits.** Los items comparten ficheros
  (9.1/9.4 en `extern_manifest.py`; 9.2/9.3/9.4 en `pengu_tcc.py`; 9.2/9.3/9.6/
  9.7/9.8/9.9 en `release.yml`; 9.6/9.8/9.12 en `ci.yml`), así que el historial se
  agrupó por concern para que **ningún commit intermedio quedara en rojo**. El
  mapeo item → commit está en la tabla de §2; cada mensaje de commit lleva la
  evidencia (comando + medición) del grupo.
