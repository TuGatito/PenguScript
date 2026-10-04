# 🗺️ ROADMAP 2.0 — CAMINO A PENGUSCRIPT 1.0

> **Punto de partida:** 0.16.0, con 11 bloqueantes verificados (`AUDIT_1.0.md` §20.1).
> **Punto de llegada:** 1.0.0 declarable con criterios de "done" verificables por comando.
> **Principio rector:** *ningún gate puede aprobar una propiedad inspeccionando texto: debe compilar,
> ejecutar o medir* (AUDIT §15.2). Este principio se aplica a **este mismo roadmap**: cada criterio de
> done es un comando o una aserción, no una intención.

## Convenciones

| Símbolo | Significado |
|---------|-------------|
| **S** | 1-2 días |
| **M** | 3-5 días |
| **L** | 1-2 semanas |
| **XL** | >2 semanas |
| 🔴/🟠/🟡/🟢 | Severidad heredada de `AUDIT_1.0.md` |
| ⏸️ | Diferido a 1.1+ con justificación |
| ✅ | Ya resuelto (no requiere trabajo) |

**Regla de estimación:** las estimaciones asumen **un** desarrollador familiarizado con el código.
Se han redondeado hacia arriba cuando el item toca `pengu_codegen.py`, `pengu_infer.py` o
`pengu_checker.py`, porque son archivos de 518 KB / 238 KB / 380 KB y cualquier cambio requiere
navegación.

## Mapa de dependencias (visión global)

```
Fase 0 (limpieza, sin romper nada)
   │
   ├──► Fase 1 (bloqueantes de correctitud: B1,B2,B3,B6,B7)
   │        │
   │        ├──► Fase 2 (lenguaje: bounds, alias, sugar)
   │        │
   │        └──► Fase 3 (codegen/runtime: B5,B8, ABI, TCC)
   │                 │
   │                 ├──► Fase 9 (herramientas de release)
   │                 │
   │                 └──► Fase 10 (congelación) ──► Fase 11 (1.0.0)
   │
   ├──► Fase 4 (CLI: B4, A3-A7)  ──► Fase 7 (docs)
   ├──► Fase 5 (LSP: A8, A9, M11)
   ├──► Fase 6 (stdlib: A10, M3-M8)
   └──► Fase 8 (tests: B9, B10, A11, A13)

Nota: las Fases 4, 5, 6 y 8 pueden ejecutarse en paralelo con 2/3 en cuanto la Fase 1 cierre.
```

---

## Fase 0 — Limpieza y consolidación

> **Requiere:** nada
> **Bloquea:** todas las demás fases (reduce el ruido de diffs y el riesgo de conflicto)
> **Duración estimada:** **S** (2 días)

### Objetivo

Eliminar el ruido del repositorio (archivos muertos, cachés sucios, documentos de proceso) **sin
tocar una sola línea de lógica** y sin romper ningún import, test ni workflow.

### Items

| # | Item | Archivos | Estimación | Done |
|---|------|----------|------------|------|
| 0.1 | Eliminar `pengu_runtime.c` (raíz, **0 bytes**, rastreado en git desde `ef57c84`) | `pengu_runtime.c` | S | `git cat-file -s HEAD:pengu_runtime.c` falla; `build_runtime.py` sigue usando `pengu_parser/pengu_runtime.c`; los tests pasan |
| 0.2 | Mover 7 documentos de proceso a `docs/archive/` o borrarlos | `AUDIT_RESPONSE.md`, `PRODUCTION_READINESS.md`, `P1_PROGRESS.md`, `P2_PROGRESS.md`, `CRITICALS_PROGRESS.md`, `Plan.md`, `roadmap.md` | S | `ls *.md` en la raíz baja de 20 a ≤14; ninguna referencia rota (`grep -rn <nombre>` → solo en `docs/archive/`) |
| 0.3 | Borrar `__pycache__/` y `.pytest_cache/` del árbol de trabajo y verificar el `.gitignore` | 7 directorios `__pycache__` fuera de `extern/`, `.pytest_cache/` | S | `find . -name __pycache__ -not -path './extern/*' \| wc -l` → 0; `git status --short` limpio |
| 0.4 | Mover `README_RELEASE.md` y `PENGU_BUILD.md` a `docs/` y actualizar los enlaces entrantes | `README_RELEASE.md`, `PENGU_BUILD.md`, `README.md` | S | `grep -rn "README_RELEASE\|PENGU_BUILD" --include="*.md" --include="*.yml"` → todas las rutas actualizadas; ningún enlace roto |
| 0.5 | Auditar `c_bind_stubs/` (76 KB) y decidir | `c_bind_stubs/` | S | `grep -rn "c_bind_stubs"` → si 0 referencias en código/tests/workflows, se borra; si lo usa `regen_std_bindings.py`, se documenta su propósito en un `README.md` |
| 0.6 | Convertir `pengu_dce.py` (raíz, shim de 491 B) en un alias explícito documentado o en un re-export con deprecación | `pengu_dce.py`, `docs/PERFORMANCE.md:163`, `tests/test_dce_tcc_pch.py:12` | S | El shim conserva `__all__` y un docstring que dice "use `pengu_parser.pengu_dce`"; los 2 importadores siguen funcionando |
| 0.7 | Verificar y documentar que `scratch/`, `tests_std/` y `pengu_runtime_original.h` no existen | — | S | `ls -d scratch tests_std pengu_runtime_original.h` → todos fallan; queda registrado en `CLEANUP_PLAN.md` §1 |
| 0.8 | Confirmar el `.gitignore` contra el árbol real (sin cambios salvo justificación) | `.gitignore` | S | `git ls-files \| grep -E '^(build/\|extern/\|__pycache__)'` → vacío |
| 0.9 | Añadir `docs/` con un índice que apunte a los documentos vivos | `docs/README.md` | S | El índice lista cada documento de la raíz con una frase de propósito y su estado (vivo/histórico) |
| 0.10 | Etiquetar los 105 bloques `pengu` de `LANGUAGE.md` como `pengu` (completo) o `pengu-fragment` (fragmento) | `LANGUAGE.md`, `LANGUAGE_Spanish.md`, `CHEATSHEET.md` | M | Un script cuenta: `pengu` completos ≥ 40; los que hoy fallan por ser fragmentos quedan fuera del gate de CI de §13.1 |

### Estado de ejecución — Fase 0 COMPLETADA

Ejecutada contra `0.16.0` (commits `f74fc23`, `5791872` y el commit de Fase 0/C+D). Resultados
verificados:

| Item | Resultado | Evidencia |
|------|-----------|-----------|
| 0.1 `pengu_runtime.c` raíz (0 bytes) | ✅ **eliminado** | `git rm`; `build_runtime.py:1174` sigue usando `pengu_parser/pengu_runtime.c` |
| 0.2 7 documentos de proceso → `docs/archive/` | ✅ **movidos** con `git mv` + `docs/archive/README.md` | `ls *.md` en la raíz: 23 → 14 |
| 0.3 `__pycache__` / `.pytest_cache` | ✅ **eliminados** (5 `__pycache__` propios + `.pytest_cache`) | `find . -name __pycache__ -not -path './extern/*'` → 0 |
| 0.4 `PENGU_BUILD.md` → `docs/` | ✅ **movido**; 8 referencias de `README.md` actualizadas, 2 tablas y 2 árboles realineados | 132 enlaces relativos verificados, 0 rotos |
| 0.4b `README_RELEASE.md` | ⚠️ **hallazgo no previsto**: es **generado** por `make_release.py:746` en la raíz en cada release. Movido a `docs/` **y el generador redirigido**; `.gitignore` ancla `/README_RELEASE.md` para que un checkout viejo no ensucie el árbol | `make_release.py:746-753` |
| 0.5 `c_bind_stubs/` | ❌ **REFUTADA mi propia recomendación**: está **en uso activo** y **ya tiene** `README.md`. Se conserva sin cambios | `pengu_bind.py:197,1061-1073`, `make_release.py:332`, `CHEATSHEET.md:64,2339,2575`, `tests/test_modules_bindings.py:987` |
| 0.6 `pengu_dce.py` shim | ✅ conservado; era un shim deliberado, no código muerto | `tests/test_dce_tcc_pch.py:12` |
| 0.7 `scratch/`, `tests_std/`, `pengu_runtime_original.h` | ✅ confirmado que **no existen** | — |
| 0.8 `.gitignore` | ✅ ampliado (+30 líneas justificadas), verificado que **nada rastreado queda ignorado** | `git ls-files -i -c --exclude-from=.gitignore` → vacío |
| 0.9 `docs/README.md` (índice) | ✅ creado, más `docs/archive/README.md` | 132 enlaces relativos resuelven |
| 0.10 etiquetar 274 bloques `pengu` | ⏸️ **DIFERIDO a la Fase 7** — ver nota abajo | — |

**Items de código muerto (Bloque C) — alcance revisado:**

| Item | Resultado |
|------|-----------|
| `pengu_bind.py:main()` | ⚠️ **REFUTADA mi etiqueta de "código muerto"**: es un entry point **funcional** (`python pengu_bind.py header.h`, con `if __name__ == "__main__"`). No se toca. Su duplicación de argparse se reasigna a la Fase 1 (item 1.12) |
| `undefined name` ×3 (`Set`, `Tree`, `ParseError`) | ✅ resueltos con `TYPE_CHECKING` / imports reales |
| `f-string is missing placeholders` ×6 | ✅ resueltos (prefijo `f` eliminado; contenido idéntico) |
| 13 locales sin usar | ⚠️ **NO se tocaron**: un intento de limpieza mecánica borró 7 usos **vivos** de `base_target` y rompió `pengu_bind.py`. Revertido. Reasignado a la Fase 1 (item 1.13) con un método seguro (AST por ámbito) |

**Corrección de cifras propias:** la cuenta de bloques de `LANGUAGE.md` era 105 por una regex que no
reconocía un bloque **indentado**; con un parser de fences por líneas son **104**, y los que fallan
**71**, no 72. `AUDIT_1.0.md` §13.1 queda corregido.

**Hallazgo nuevo (no estaba en la auditoría): un test es flaky.**
`tests/test_string_composition_suite.py::test_string_composition_no_memory_leaks[leak_binary_interp]`
está marcado `xfail(strict=False)` y **alterna xpass/xfail en ejecuciones aisladas** (medido 3/6
xpass). La suite completa reportó `2 xfailed, 1 xpassed` una vez y `3 xfailed` otra. No rompe CI
(`strict=False`) pero hace que el resumen de la suite **no sea reproducible**. Incorporado como item
**1.14** de la Fase 1. Mi afirmación en `AUDIT_1.0.md` §11.4 ("no se observó ningún test flaky") se
basaba en dos ejecuciones y **era una verificación insuficiente**.

### Criterio de "done" de la fase

- [ ] `pytest tests/ -q` → mismas cifras exactas que antes de la fase (2074 passed, 12 skipped,
      2 xfailed, 1 xpassed).
- [ ] `git ls-files | wc -l` decrece en al menos 8 (los 7 documentos + `pengu_runtime.c`).
- [ ] `git status --short` limpio tras el commit.
- [ ] Ningún workflow de `.github/workflows/` referencia un archivo movido o borrado.
- [ ] `pengu build`, `pengu check -c <proyecto>`, `pengu test`, `pengu doc` siguen funcionando.

### Riesgos

- **Riesgo:** mover documentos puede romper enlaces en `README.md`, `CHANGELOG.md` o issues.
  **Mitigación:** `grep -rn` por cada nombre antes de mover, y usar `git mv` (preserva historia).
- **Riesgo:** borrar `c_bind_stubs/` si algún script de release lo usa de forma indirecta.
  **Mitigación:** `grep -rn "c_bind_stubs"` sobre `.py`, `.yml`, `.md`, `.sh` antes; si hay cualquier
  duda, **no borrar** y documentar.
- **Riesgo:** el reetiquetado de bloques de `LANGUAGE.md` (0.10) toca 105 sitios y puede desalinear
  la versión española. **Mitigación:** hacerlo con un script determinista aplicado a ambos archivos.

---

## Fase 1 — Cierre de la Fase 5/6 residual: correctitud del compilador

> **Requiere:** Fase 0
> **Bloquea:** Fases 2, 3, 4, 5, 6, 8 (todas dependen de un compilador correcto)
> **Duración estimada:** **M** (4-5 días)

### Objetivo

Cerrar los cinco bloqueantes de **correctitud del compilador y de la CLI** que hoy producen crashes,
errores silenciosos o falsos verdes: B1, B2, B3, B6, B7.

### Items

| # | Item | Archivos | Estimación | Done |
|---|------|----------|------------|------|
| 1.1 | 🔴 **B3** — `parse_known_args` debe rechazar flags desconocidos | `pengu_project.py:4881` | S | `pengu check --bogus` → rc=2 con `unrecognized arguments: --bogus`; allow-list estrecha para `pengu run <script> -- <args>`; test paramétrico por cada subcomando |
| 1.2 | 🔴 **B1** — `pengu check` acepta posiciónales y los valida | `pengu_project.py:4745,5052`, `check_project` | M | `pengu check archivo_con_error.pengu` → rc=1 y emite el diagnóstico; `pengu check a.pengu b.pengu dir/` valida los tres; test de CLI con archivo roto |
| 1.3 | 🔴 **B2** — entry inexistente debe ser error | `pengu_project.py:1272` (`check_sources_diagnostics`) | S | `pengu check` en un directorio sin `src/main.pengu` → rc≠0 y mensaje `entry point not found: …`; test |
| 1.4 | 🔴 **B6** — `node` → `target_node` en el diagnóstico de símbolo privado | `pengu_infer.py:4055` | S | Acceder a `lib._privado` desde otro módulo emite `E0043`, no `NameError`; test de regresión con 2 módulos |
| 1.5 | 🔴 **B7** — tipos cualificados a través de un módulo re-exportador conservan los campos | `pengu_infer.py:1463-1478` | M | Test de 3 módulos (`dep` → `lib`) con `var v as dep.Vec is with x is 1.0`; `raymath.Vector2` del `std` real funciona; los bloques 28, 94 de `LANGUAGE.md` compilan |
| 1.6 | Normalizar el nombre antes del fallback de `lookup_type` (parte de 1.5, separada para testear) | `pengu_infer.py:1465-1468` | S | Un test unitario que pase un `RuneType` con nombre `"dep.Vec"` y `fields == {}` y verifique que el fallback encuentra `"Vec"` |
| 1.7 | Auditar **todos** los `raise self._make_error(...)` por parámetros mal referenciados | `pengu_infer.py`, `pengu_checker.py` | M | `pyflakes` con `F821` → 0 `undefined name` reales; test que recorra cada `code="Exxxx"` y confirme que ningún camino lanza `NameError` |
| 1.8 | Añadir los tests de regresión de 1.1–1.5 al corpus permanente | `tests/test_cli_contract.py` (nuevo), `tests/test_module_qualified_types.py` (nuevo) | S | Los 5 tests existen, fallan si se revierte el fix, y están en CI |
| 1.9 | Falso positivo: `while true: return 1` no debe dar `E0020` | `pengu_checker.py:5366` (`_check_weave_decl`) | S | `weave f into int: while true: return 1` compila; se sigue avisando de un `while` que puede no ejecutarse |
| 1.10 | Mensaje útil para `E0013` cuando `fields` está vacío (el `note` dice `fields are: .`) | `pengu_infer.py:1469-1478` | S | Si `fields` está vacío, el mensaje dice "the type's definition could not be resolved from module X" en vez de mostrar una lista vacía |
| 1.11 | Registro de las suposiciones falsas del encargo como tests anti-regresión | `tests/test_audit_regressions.py` (nuevo) | S | Los 14 ❌ REFUTADO de AUDIT §18.2 tienen un test que documenta el comportamiento real |
| 1.12 | Eliminar la duplicación de CLI en `pengu_bind.py`: hacer que su `main()` construya el parser desde `pengu_project.create_cli_parser()` en vez de redefinir 13 flags | `pengu_bind.py:1567-1617`, `pengu_project.py:4509` | M | `python pengu_bind.py <header>` sigue funcionando con los mismos flags; un solo `--help` para el subcomando `bind`; test de contrato comparando ambos parsers |
| 1.13 | Retirar los 13 locales sin usar **con un método seguro** (análisis AST por ámbito, o `ruff --select F841 --fix`) | `pengu_checker.py`, `pengu_codegen.py`, `pengu_lsp/server.py`, `pengu_bind.py` | M | `pyflakes \| grep -c "assigned to but never used"` → 0 **y** la suite completa verde. Un intento mecánico previo borró 7 usos vivos de `base_target`; no repetirlo |
| 1.14 | Hacer **deterministas** los tests flaky. Hay **dos**: el de leak (alterna xpass/xfail en aislamiento) y `tests/test_deps_commands.py::test_add_upgrade_remove_end_to_end` (falló 1 de 2 ejecuciones completas idénticas; pasa en aislamiento y en su archivo) | `tests/test_string_composition_suite.py:72`, `tests/test_deps_commands.py` (caché `~/.cache/pengu/deps/`), `tests/conftest.py` | M | Dos ejecuciones consecutivas de la suite completa reportan **la misma** tupla `(passed, skipped, xfailed, xpassed)`. Nótese que el item **8.17** solo exige `0 xpassed`; este item exige además **reproducibilidad** |


### Criterio de "done" de la fase

- [ ] `pengu check archivo_con_error.pengu` → rc=1 y diagnóstico (B1).
- [ ] `pengu check` sin entry → rc≠0 (B2).
- [ ] `pengu check --bogus` → rc=2 (B3).
- [ ] `pengu check <archivo_inexistente>` → rc≠0.
- [ ] El programa de 3 módulos con `dep.Vec` compila (B7).
- [ ] El acceso a símbolo privado emite `E0043`, no `NameError` (B6).
- [ ] `pyflakes pengu_parser/ pengu_lsp/ *.py | grep -c "undefined name"` → **0** (los 3 falsos
      positivos de PEP 563 se silencian con un `# noqa` justificado o se añade `Set`/`Tree` al import
      de tipos).
- [ ] `pytest tests/ -q` → todos verdes, sin regresiones.
- [ ] Cada uno de los 6 fixes tiene su test de regresión en el corpus permanente.

### Riesgos

- **Riesgo:** aceptar posiciónales en `check` puede romper la invocación existente
  `pengu check -c <proyecto> -e <entry>` si `nargs="*"` interfiere con los flags.
  **Mitigación:** `nargs="*"` con default `None` y precedencia explícita documentada: si hay
  posiciónales, se validan **esos**; si no, se usa `-e`/config.
- **Riesgo:** arreglar B7 tocando la resolución de nombres puede afectar a la monomorfización de
  genéricos. **Mitigación:** ejecutar los 174 tests de std y los 16 de `test_codegen_generic_subst.py`
  después de cada cambio; B7 es un fallback, no una reescritura.
- **Riesgo:** el ítem 1.7 (auditar todos los `_make_error`) puede revelar más de un `node` mal
  referenciado. **Mitigación:** es exactamente el objetivo; presupuestar a **L** si aparecen más de 3.

---

## Fase 2 — Completar 1.0 del lenguaje

> **Requiere:** Fase 1
> **Bloquea:** Fase 6 (stdlib depende de la semántica de bounds), Fase 7 (docs)
> **Duración estimada:** **M** (5 días)

### Objetivo

Hacer que el sistema de tipos y la sintaxis sean **coherentes y honestos** con lo documentado, y
retirar o implementar el azúcar que hoy es ficción.

### Items

| # | Item | Archivos | Estimación | Done |
|---|------|----------|------------|------|
| 2.1 | 🟠 **A1** — decidir y hacer cumplir la jerarquía de bounds en **un solo sitio** | `pengu_types.py` (tabla de concepts), `pengu_checker.py`/`pengu_infer.py` (consultas) | M | Matriz operador × bound es coherente: si `Num` concede `==`/`<`, entonces `Par`/`Ordo` conceden `Num`; o al revés. Test paramétrico que fija la matriz completa (los 30 pares de AUDIT §3.1) |
| 2.2 | Re-documentar los bounds como "conjuntos de operadores habilitados" (o como cadena monótona, según 2.1) | `LANGUAGE.md:1535-1560`, `LANGUAGE_Spanish.md` | S | La tabla documental coincide con la matriz medida; el test de 2.1 lee de la misma fuente |
| 2.3 | 🔴 **A18/§1.2** — Implementar `alias NAME` en `concept` **o** retirar el ejemplo | `pengu_grammar.py:92-93`, `pengu_checker.py`, `LANGUAGE.md` bloque 59 | M (implementar) / S (retirar) | **Decisión Requerida.** Si se retira: el bloque 59 desaparece y §9.1 lo marca ⏸️ con justificación. Si se implementa: `concept Iterabilis shard Self:` + `alias Item` compila y `Self.Item` se resuelve en bounds |
| 2.4 | ⏸️ **DIFERIDO a 1.1.** Reducir los 188 conflictos shift/reduce: **no es reducible sin un cambio de sintaxis** — 9 vías medidas, todas fallidas (ver `AUDIT_1.0_FASE2.md` §7, §10, §12, §14, §18, §21) | `pengu_grammar.py`, jerarquía de expresiones | **XL** (era L) | **Reformulado.** No es "reducir 188": `return` necesita aceptar expresiones terminadas en bloque (6 archivos) y `expr` necesita contenerlas (`judge` es también sentencia, usada en `archivum`); LALR(1) no puede distinguir ambos caminos en el token `JUDGE` y **ningún reordenamiento de producciones lo arregla porque ambas rutas son necesarias**. La salida es introducir sintaxis delimitada para una de las dos formas (p. ej. `return do:`), lo que es **decisión de lenguaje**, no implementación. Criterio `strict=True` **no cumplido**: 188 |
| 2.4b | ✅ **CERRADO.** Test que fija la precedencia y asociatividad explícitamente | `tests/test_precedence.py` | S | ✅ 99 tests: las 9 expresiones de AUDIT §1.1 dan el valor numérico y el nodo raíz esperados, y falla si la heurística de Lark cambia. El *dangling else* queda fijado por 3 tests conductuales en `tests/test_grammar_strict.py` |
| 2.5 | Unificar la doble sintaxis de rango `to` / `..` | `pengu_grammar.py:341-342`, `LANGUAGE.md` | S | Una sola forma canónica; la otra emite warning `W0013 RangeSyntaxDeprecated` durante 1.x |
| 2.6 | Documentar (o rechazar) `frozen ref to T` vs `ref to frozen T` | `pengu_grammar.py:265-272`, `LANGUAGE.md` | S | Una forma documentada; la otra emite error de sintaxis o warning |
| 2.7 | Verificar y documentar la expansión de variádicos en el call site | `pengu_grammar.py:390-394`, `LANGUAGE.md` | S | Test: `weave f with xs as many int` + llamada con N args funciona; si no hay expansión, documentarlo como ⏸️ |
| 2.8 | Verificar `derive` para `Vinculum`/`Nexus`/`Imago`/`Forma`/`Iterabilis`/`Donum` | `pengu_codegen.py:3372` (`generate_derived_implementations`) | M | Por cada concept derivable: test de compile-and-run; matriz documentada de qué se puede derivar |
| 2.9 | Documentar que los identificadores son ASCII | `LANGUAGE.md` §2 | S | Una línea explícita + ejemplo; `test` que confirma que `日本語` es error |
| 2.10 | Auditoría de los 41 alias de tipo base y decisión sobre los redundantes | `pengu_grammar.py:262`, `pengu_types.py` | M | Documento o tabla que mapea cada alias a su tipo canónico; los 4 nombres de float reducidos o justificados |
| 2.11 | Warnings nuevos: `W0008 UnusedImport`, `W0011 EmptyTestBody`, `W0012 DeprecatedAliasUse` | `pengu_checker.py` | M | Cada warning tiene test positivo y negativo; documentado en `LANGUAGE.md` §22.3 |
| 2.12 | Silenciar `W0005` en bloques `test` y renombrar los 29 locales de la stdlib | `pengu_checker.py` (supresión), `std/*.pengu` | M | `pengu check --entry std/loom.pengu` → 0 W0005; los bloques `test` no emiten shadowing |

### Criterio de "done" de la fase

- [x] Matriz de bounds medida y coherente con la documentación (test paramétrico de 30 pares). — **5 de 6 criterios cumplidos (Fase 2, 36 commits).** Ver `AUDIT_1.0_FASE2.md` §20.
- [ ] `Lark(..., strict=True)` no lanza en CI. — **⏸️ DIFERIDO a 1.1.** Sigue en 188 conflictos. Nueve vías medidas y descartadas; la causa raíz está identificada (§21) y es una **decisión de sintaxis**, no una tarea de implementación. Herramienta de diagnóstico entregada: `tools/grammar_conflicts.py`.
- [x] Los 4 ejemplos documentales que no compilaban (bloques 15, 28, 59, 94) compilan **o** han sido
      retirados de `LANGUAGE.md` con marca ⏸️. — 15/28/94 compilan (Fase 1, B7); el 59 se retiró y §11.7 lo marca ⏸️.
- [x] Una sola sintaxis de rango canónica, con deprecación de la otra. — `to` canónica; `..` emite `W0013` y además ahora **hace slice** (antes solo funcionaba en `for … in`).
- [x] Matriz de `derive` documentada y probada por concept. — `tests/test_derive_matrix.py`, 14 tests.
- [x] `stderr` de `pengu check --entry std/<mod>.pengu` para los 52 módulos → **0 warnings propios**. — **71 → 0** (W0005 50→0, W0001 21→0).

### Riesgos

- **Riesgo:** 2.1 (bounds) puede **romper código existente** de la stdlib si se endurece `Num`.
  **Mitigación:** medir primero cuántos sitios de `std/` dependen de `T: Num` + `<` o `==`; si son
  pocos, cambiar; si son muchos, elegir la dirección permisiva (un retículo) y documentar.
  **Presupuestar medición de 1 día antes de decidir.**
- **Riesgo:** 2.4 (eliminar el conflicto LALR) puede requerir reescribir `unless` y cambiar la
  asociación del `else` en programas existentes. **Mitigación:** añadir el test de asociación
  *antes* del cambio, y verificar los 2074 tests + los 52 módulos.
- **Riesgo:** implementar `alias` en concepts (2.3) es una feature de lenguaje con resolución en
  bounds; puede ser **L** en vez de M. **Mitigación:** si el presupuesto se agota, **retirar el
  ejemplo** y diferir; la doc honesta es preferible a la feature a medias.

---

## Fase 3 — Completar runtime y ABI

> **Requiere:** Fase 1
> **Bloquea:** Fase 9 (release), Fase 10 (congelación)
> **Duración estimada:** **L** (1-2 semanas)

### Objetivo

Hacer que el runtime sea **C99 legal sin flags de supresión**, que la portabilidad declarada sea real
(`--strict-c99`, TCC, MSVC) y que la ABI esté verificada de extremo a extremo.

### Items

| # | Item | Archivos | Estimación | Done |
|---|------|----------|------------|------|
| 3.1 | 🔴 **B8** — el runtime debe compilar sin `-Wno-implicit-function-declaration` | `pengu_parser/pengu_runtime.c:25-28`, `build_runtime.py:1195-1204` (y `:272,436,521,999,1152`) | M | Añadir `-DMBEDTLS_ALLOW_PRIVATE_ACCESS`, eliminar los dos `-Wno-*`; `gcc -std=c11 -Wall -Wextra -c` → **0 errores**; verificado que el fix funciona (AUDIT §5.1) |
| 3.2 | 🟠 **B5** — `--strict-c99` debe emitir C portable en programas con `std` | `pengu_codegen.py:4232-4256` (`_hoist`/`_block_expr`), `:5853-5855`, `:8707-8709`, `:1339-1358` | **L** | El bundle estricto de los 56 `tests/std_programs/*.pengu` compila con `gcc -std=c99 -pedantic-errors` → 0 errores, y **ejecuta** con salida correcta |
| 3.3 | ⏸️ **DIFERIDO a 1.1** — Reemplazar statement-expressions `({...})` por C99 puro en modo estricto | `pengu_codegen.py` (los 104 sitios restantes) | **XL** | Diferido **con medición**, no por presupuesto: acoplado a 3.2 (eliminar `({...})` sin arreglar antes el *hoisting* del índice **no compila**) y único item XL del roadmap. Medición: 34/61 programas de `tests/std_programs/` fallan `-std=c99 -pedantic-errors` (AUDIT_1.0_FASE3.md §6–§7) |
| 3.4 | Emitir `__typeof__` en lugar de `__auto_type` para que TCC acepte bundles con `std` | `pengu_codegen.py`, `build_runtime.py` | S | `tcc -c` sobre el bundle de `atlas.pengu` → 0 errores; `pengu run` deja de imprimir "development compiler failed; retrying with gcc" |
| 3.5 | ✅ **A15** — `PENGU_ABI_VERSION` verificable contra `libpengu_runtime.a` | `pengu_parser/pengu_runtime.c`, `docs/ABI.md` | M | **Hecho.** `nm libpengu_runtime.a \| grep pengu_abi_version` → **1 símbolo `T`**; un consumidor que enlace el `.a` y referencie el símbolo falla en **link** si el archivo es anterior, en vez de reinterpretar campos. La referencia **no** es obligatoria desde cada bundle: forzarla rompía `pengu build` en todo proyecto nuevo (`pengu init` no enlaza el runtime, el bundle es header-only), y hacerla obligatoria es Fase 4. `SECURITY.md`/`docs/ABI.md` dicen qué se garantiza y qué no. Ver `AUDIT_1.0_FASE3.md` §14 |
| 3.6 | ✅ Añadir `SIGFPE`/`SIGILL`/`SIGBUS` y usar `sigaction` | `pengu_runtime.h` | M | **Hecho.** `pengu eval "1/0"` → `[PENGU CRASH] fatal signal (signal/code 8)` con traza `.pengu` y exit **136** (antes: sin mensaje, exit 248). `sigaction` con `SA_RESETHAND`; `tests/test_crash_signals.py` (6 tests) |
| 3.7 | ✅ Formatear el volcado sin `snprintf` (se **mantiene** la afirmación) | `pengu_runtime.h` | M | **Hecho.** El handler y `pengu_bounds_panic` formatean a mano (aritmética + división entera) y solo usan `write(2)`/`_exit()`. Medido sobre el artefacto compilado: el cierre de enlace del camino de crash no referencia `snprintf`, `malloc` ni stdio. `tests/test_crash_dump_async_safe.py` (4 tests) |
| 3.8 | Hacer atómica la instalación del crash handler | `pengu_runtime.h:399,459-460,471` | S | `call_once`/atómico; `pengu_frame_push` no escribe un global en cada frame |
| 3.9 | ✅ **R3** — unificar el formateo de floats (`%g` vs `%f`) | `pengu_runtime.h`, `pengu_codegen.py` | S | **Hecho.** `print x`, `(x to string)` y `"{x}"` coinciden byte a byte; cubre `3.14`, `0.0`, `-0.0`, `1.0/3.0`, `1e300` y `1e-300`, con `float`/`f32` (32-bit) y `f64`/`double` (64-bit). `tests/test_floats_consistency.py` (10 tests) |
| 3.10 | ⏸️ **DIFERIDO a 1.1** — Documentar los 55 símbolos del runtime sin Doxygen | `pengu_runtime.h` | M | Diferido con medición: cosmético, ninguna afirmación de comportamiento depende de ello, y encaja en la Fase 7 (docs), donde el catálogo se genera de una vez |
| 3.11 | ✅ Exportar `pengu_abi_version()` y documentar qué rompe la ABI | `pengu_parser/pengu_runtime.c`, `docs/ABI.md` (nuevo) | M | **Hecho.** `docs/ABI.md` define la política: qué cambia la versión (layout de structs —incluido añadir al final— y firmas), qué no (añadir funciones), y cómo se verifica |
| 3.12 | Guardar los `#define` de `pengu_runtime.c:12-15,29` con `#ifndef` | `pengu_parser/pengu_runtime.c` | S | 0 warnings de `-Wmacro-redefined` |
| 3.13 | ✅ (**nuevo**) Evaluar la expresión de retorno **antes** de retirar el frame | `pengu_codegen.py` (`return_stmt`) | S | **Hecho.** El codegen emitía `pengu_frame_pop(); return <expr>;`, así que un fallo dentro del `return` se atribuía **al llamador** (`return a / b` con división por cero → `at pengu_main`) y `return calling f` producía un solo frame. Ahora se evalúa en un temporal antes del `pop`. Es lo que hace verdadera la afirmación "pila de llamadas exacta" |

### Criterio de "done" de la fase

- [x] `gcc -std=c11 -Wall -Wextra -c` sobre `pengu_runtime.c` con los flags **reales** de build →
      **0 errores, 0 warnings de supresión**. (`tests/test_runtime_c99.py`, 9 tests)
- [ ] `gcc -std=c99 -pedantic-errors` sobre el bundle `--strict-c99` de los 56 programas de `std` →
      0 errores, y cada uno produce la salida esperada al ejecutarse.
      **NO CUMPLIDO — diferido a 1.1** (items 3.2 y 3.3). Medición: 34/61 fallan.
- [ ] `grep -c '({'` en cada bundle estricto → 0.
      **NO CUMPLIDO — diferido a 1.1** (item 3.3, ver su fila).
- [ ] `tcc -c` sobre el bundle de `atlas.pengu` → 0 errores.
      **NO CUMPLIDO — diferido a 1.1** (item 3.4, fix revertido; ver AUDIT_1.0_FASE3.md §11).
- [x] `pengu_runtime.h` sigue con 0 warnings bajo `-Wall -Wextra -Werror` (no debe regresar).
      Verificado además en 4 combinaciones de `PENGU_FRAME_TRACE`/`PENGU_BOUNDS_CHECK` × `-std=c99/c11`.
- [x] `nm libpengu_runtime.a | grep -i abi` → 1 símbolo. → `T pengu_abi_version`
- [x] Una división por cero volca los frames y `pengu eval "1/0"` imprime un mensaje, no exit 248.
      → imprime `[PENGU CRASH] fatal signal (signal/code 8)` con traza y sale con **136**.

### Riesgos

- **Riesgo:** 3.3 (eliminar 104 statement-expressions) es el item más grande del roadmap y toca la
  función de 2605 líneas. **Mitigación:** hacerlo **después** de 3.2 (que arregla el hoisting, el
  error duro) y **antes** de cualquier refactor de `_translate_expr_impl`; si el presupuesto se
  agota, `--strict-c99` puede declararse "parcialmente portable" con una lista honesta de lo que no
  cubre, pero **nunca** puede seguir diciendo "gate de portabilidad" mientras emita C inválido.
- **Riesgo:** 3.5 puede requerir cambios en `make_release.py` (el `.a` lo produce el build de
  runtime). **Mitigación:** verificar el flujo `build_runtime.py` → `libpengu_runtime.a` →
  `make_release.py` antes de empezar.
- **Riesgo:** 3.9 cambia la salida visible de programas existentes (tests que asertan `3.140000`).
  **Mitigación:** `grep -rn "\.000000\|%f" tests/` antes; actualizar los golden values con la
  justificación de que `%g` es más correcto.

---

## Fase 4 — Completar CLI

> **Requiere:** Fase 1 (B1/B2/B3)
> **Bloquea:** Fase 7 (la documentación describe el CLI), Fase 9 (release usa el CLI)
> **Duración estimada:** **M** (4-5 días)

### Objetivo

Hacer que el CLI **haga lo que su ayuda dice**: sin flags que no hacen nada, sin pérdida de datos,
con errores formateados de forma consistente y con el contrato `--json` completo.

### Items

| # | Item | Archivos | Estimación | Done |
|---|------|----------|------------|------|
| 4.1 | 🔴 **B4** — `fmt --indent N` no debe corromper la indentación | `pengu_lsp/formatting.py:234,251` | M | Detecta la unidad de indentación del fuente (mcd de los deltas de espacios iniciales) y reescala; `fmt(fmt(x))==fmt(x)` y `check(fmt(x))==check(x)` sobre los 27 módulos puros |
| 4.2 | 🟠 **A7** — `pengu fmt` default a **4** espacios, coherente con doc y stdlib | `pengu_project.py:4793` | S | `pengu fmt --check std/` → 0 archivos cambiarían; la ayuda dice "(default: 4)" |
| 4.3 | Añadir `.pengufmt.toml` a la raíz y a `std/` declarando `tab_size = 4` | `.pengufmt.toml`, `std/.pengufmt.toml` | S | `pengu fmt --check` es idempotente sobre todo el repo |
| 4.4 | 🟠 **A4** — `--quiet` debe suprimir la salida de progreso | `pengu_project.py:4538-4541`, todos los `print` de progreso | M | `pengu --quiet build \| wc -c` → 0 (salvo errores); test por subcomando |
| 4.5 | 🟠 **A4** — `--no-color` y `NO_COLOR=1` deben desactivar ANSI | `pengu_project.py`, ~77 sitios con `\033[1;…` | M | `pengu --no-color check \| cat -v` no contiene `^[[`; `NO_COLOR=1 pengu check` idem; helper `style()` único |
| 4.6 | 🟠 **A5** — `pengu test --json` debe emitir JSON Lines en fallo | `pengu_project.py:4469,5034` | M | `pengu test --json` con error de compilación emite `{"type":"diagnostic",…}` + `{"type":"summary","ok":false,…}`; nada de tracebacks |
| 4.7 | Unificar el formato JSON: `metadata`/`tree --json` deben ser JSON Lines | `pengu_project.py` | S | Los 5 comandos con `--json` emiten JSON Lines; `pengu run` **rechaza** `--json` o lo implementa |
| 4.8 | 🟠 **A6** — errores del camino de script con el reporter estándar | `pengu_project.py:4138` (`run_script`), `eval`, `expand`, `time`, `watch` | M | `pengu run noexiste.pengu`, `pengu eval "1 +"`, `pengu expand roto.pengu` → mensaje formateado Rust-style, rc≠0, sin traceback |
| 4.9 | Mapear códigos de retorno negativos del hijo a `128+señal` con mensaje | `pengu_project.py:4982` | S | `pengu eval "1/0"` → "terminated by SIGFPE (division by zero?)" y rc=136 |
| 4.10 | 🟠 **A3** — `--target-compiler` debe validarse contra el compilador real | `pengu_project.py:1465-1500`, `pengu_codegen.py:3955` | M | `pengu build --target-compiler msvc` sin `--cc cl` → **error** explicando el desajuste, no C inválido generado en silencio |
| 4.11 | Completar el mapeo de flags de `cl.exe` (`/Fe:`, `/I`, `/link`) | `pengu_project.py:1467-1490` | M | La línea de comandos de MSVC no contiene ningún flag GNU |
| 4.12 | 🟡 **L7** — `--cc tcc` debe encontrar el TCC incluido | `pengu_project.py`, `pengu_tcc.py:40-68` | S | `pengu build --cc tcc` funciona sin ruta absoluta |
| 4.13 | Eliminar el `main()`/argparse duplicado de `pengu_bind.py` | `pengu_bind.py:1567-1617` | S | `grep -c "def main" pengu_bind.py` → 0; `pengu bind` sigue funcionando |
| 4.14 | Añadir los subcomandos que faltan para 1.0: `pengu migrate`, `pengu new` | `pengu_project.py` | M | `pengu migrate --from 0.15 --to 1.0` reescribe un proyecto; `pengu new <tipo> <nombre>` crea desde plantilla |
| 4.15 | `pengu benchmark` (alias de la suite de `benches/`) | `pengu_project.py` | S | Ejecuta `benches/` y reporta; **debe** incluir al menos un bench que importe `std` |
| 4.16 | Documentar el contrato de cada subcomando en `--help` (qué hace, rc, efectos) | `pengu_project.py:4509` (`create_cli_parser`) | M | Cada subcomando tiene descripción de ≥1 frase, epílogo con rc esperados, y un ejemplo |

### Criterio de "done" de la fase

- [ ] `pengu fmt --check` es idempotente sobre el repo completo y no cambia ningún archivo de `std/`.
- [ ] `pengu --quiet build` no imprime nada en éxito.
- [ ] `--no-color` y `NO_COLOR=1` eliminan todo ANSI en los 25 subcomandos.
- [ ] Los 5 comandos con `--json` emiten JSON Lines válido (verificado con un parser JSON por línea).
- [ ] Ningún camino de error del CLI produce un traceback de Python.
- [ ] `pengu build --target-compiler msvc` sin `--cc cl` falla con un mensaje claro.
- [ ] `pengu migrate` y `pengu new` existen, tienen test, y aparecen en `--help`.
- [ ] `pengu benchmark` corre e incluye benchmarks sobre la stdlib.

### Riesgos

- **Riesgo:** 4.5 (los 77 `print` con ANSI) es un cambio extenso y mecánico con riesgo de romper
  golden outputs de tests. **Mitigación:** introducir el helper `style()` con default
  "color si TTY", y hacer `grep -rn '\x1b\[' pengu_project.py` → 0 al final.
- **Riesgo:** 4.6 (`test --json`) requiere entender cómo `test_project` propaga errores; puede
  revelar que el camino de test no usa el mismo motor que build/check. **Mitigación:** presupuestar
  **L** si `test_project` tiene su propio camino de compilación.
- **Riesgo:** 4.14 (`pengu migrate`) es una herramienta nueva, no un fix. **Mitigación:** el mínimo
  viable es migrar las construcciones que el CHANGELOG marca como eliminadas (`and`/`or` como
  separadores), con `--dry-run` por defecto.

---

## Fase 5 — Completar LSP

> **Requiere:** Fase 1
> **Bloquea:** Fase 7 (docs del LSP)
> **Duración estimada:** **S-M** (3 días)

### Objetivo

Cerrar los dos bugs de corrección semántica (rename global, ubicaciones fantasma) y convertir en
funcional el código muerto ya escrito (organize imports, code lens), más las dos features ausentes
que un usuario de VS Code nota.

### Items

| # | Item | Archivos | Estimación | Done |
|---|------|----------|------------|------|
| 5.1 | 🟠 **A8** — rename global debe ser semántico | `pengu_lsp/server.py:1281-1294`, `:884-929` | M | Renombrar `weave helper` **no** reescribe un `var helper` local; test con homónimo en 2 archivos |
| 5.2 | 🟠 **A9** — go to definition no debe devolver rutas shadow | `pengu_lsp/server.py:403-420,469-471` | M | `textDocument/definition` en un buffer sin guardar devuelve la URI real; test |
| 5.3 | Conectar `organize_imports_action` (código muerto ya implementado) | `pengu_lsp/server.py:1059-1089`, `code_actions.py:396` | S | La acción aparece con `source.organizeImports` y ordena/elimina imports; test |
| 5.4 | Registrar `pengu.runTest` o eliminar el code lens | `pengu_lsp/server.py:1790`, capacidades `executeCommandProvider` | S | El lens ejecuta el test y muestra el resultado, o el lens no se emite |
| 5.5 | 🟠 **M11** — `workspace/symbol` | `pengu_lsp/server.py` (capacidades + handler) | M | `workspace/symbol` devuelve símbolos del proyecto; verificado con cliente LSP |
| 5.6 | `prepareRename` para rechazar rename de no-símbolos | `pengu_lsp/server.py:1224` | S | `prepareRename` sobre un keyword devuelve error; sobre un símbolo, su rango |
| 5.7 | Gatear el log de depuración tras `PENGU_LSP_DEBUG` | `pengu_lsp/server.py:252` | S | Sin la variable, no hay `[LSP] Publishing …` en stderr |
| 5.8 | Actualizar los docstrings obsoletos | `pengu_lsp/__init__.py:1`, `server.py:1062-1064` | S | La versión se lee de `pengu_version`; el docstring de `code_action` menciona las 4 acciones |
| 5.9 | Semantic tokens por rango y delta | `pengu_lsp/server.py:1614` | M | `SEMANTIC_TOKENS_RANGE` y delta implementados; editor sin re-tokenizar el archivo completo |
| 5.10 | `didChangeConfiguration` y `didChangeWatchedFiles` | `pengu_lsp/server.py` | S | El servidor reacciona al cambio de configuración y a cambios en disco |
| 5.11 | Test de estabilidad a 10 000 líneas | `tests/test_lsp_stability.py` | M | 13 peticiones responden sin error en un archivo de 10 000 líneas; tiempo medido |

### Criterio de "done" de la fase

- [ ] Rename global con homónimo local: solo el símbolo objetivo se edita.
- [ ] Go to definition nunca devuelve `.pengu_lsp_shadow_*`.
- [ ] Las 4 code actions están conectadas (incluida organize imports).
- [ ] El code lens ejecuta algo o no se emite.
- [ ] `workspace/symbol` y `prepareRename` en las capacidades y funcionando.
- [ ] Sin `PENGU_LSP_DEBUG`, el servidor no escribe nada en stderr en operación normal.
- [ ] Estable y medido a 10 000 líneas.

### Riesgos

- **Riesgo:** 5.1 (rename global semántico) requiere resolver cada ocurrencia contra **su propio**
  archivo, lo que implica indexar símbolos por archivo — puede ser **L** si no existe ya ese índice.
  **Mitigación:** verificar si `_compute_diagnostics` ya construye una tabla por archivo
  reutilizable; si no, un indexado perezoso por URI con caché por hash.
- **Riesgo:** 5.9 (semantic tokens por rango) puede interactuar con la caché de diagnósticos.
  **Mitigación:** es el último item de la fase y puede diferirse a 1.1 si el presupuesto se agota
  (no es bloqueante).

---

## Fase 6 — Completar stdlib

> **Requiere:** Fase 1, Fase 2 (bounds)
> **Bloquea:** Fase 7 (el guide se aplica a la stdlib)
> **Duración estimada:** **L** (1-2 semanas)

### Objetivo

Cerrar el bug de corrección de `seal`, eliminar los 50 warnings propios, resolver las duplicaciones
de API y elevar la documentación inline de los 3 módulos con huecos.

### Items

| # | Item | Archivos | Estimación | Done |
|---|------|----------|------------|------|
| 6.1 | 🟠 **A10** — `seal.crc32` debe devolver `u32` | `std/seal.pengu:44,71`, `pengu_parser/pengu_runtime.c:1242` | S | `crc32("a")` → `390611389` (positivo) y coincide con `crc32` estándar; test con valores ≥0x80000000 |
| 6.2 | `std/ffi.pengu` — sustituir `transmute 0 to ref to T` por `null` | `std/ffi.pengu:133,137,141` | S | 0 W0001 de size mismatch en `ffi` (verificado que `return null` compila limpio) |
| 6.3 | Propagar la posición AST en los diagnósticos `W0001` | `pengu_checker.py` (chequeo de transmute) | M | `std/filum.pengu:0:0` → `std/filum.pengu:<línea>:<col>`; los 21 W0001 son localizables |
| 6.4 | 🟠 **M3** — renombrar los 29 locales que sombrean funciones globales | `std/loom.pengu` (21), `std/tally.pengu` (3), `std/precis.pengu` (4), `std/archivum`, `std/arithmancy`, `std/parchment` | M | `pengu check --entry std/<mod>.pengu` para los 52 → 0 W0005 (o solo los de bloques `test`, si 2.12 los silencia) |
| 6.5 | 🟠 **M4** — resolver la duplicación `loom` ∩ `tally` (15 nombres) | `std/loom.pengu`, `std/tally.pengu`, `LANGUAGE.md` | M | **Decisión Requerida:** unificar semántica (preferir `loom`, más segura con `maybe`) o renombrar la familia de `tally` |
| 6.6 | 🟠 **M7** — `SPARK_VERSION`/`STD_VERSION` y el test vacuo | `std/spark.pengu:30,33,80`, `tests/std_programs/test_spark.pengu:7` | S | Ambas constantes coherentes con `VERSION`; el test **asevera** (`sv == SPARK_VERSION`), no imprime |
| 6.7 | 🟠 **M8** — elevar la doc inline de `atlas` (32 %), `arithmancy` (39 %), `scrolls` (52 %) | `std/atlas.pengu`, `std/arithmancy.pengu`, `std/scrolls.pengu` | **L** | Los 3 módulos ≥90 % de `weave` públicos con doc inline; `tests/test_std_docs_completeness.py` bajado a ≥90 % |
| 6.8 | Añadir `<MOD>_VERSION` a los 19 bindings que no la tienen | `std/*.d.pengu` | M | 25/25 bindings con constante; `tests/test_std_versioning.py` lo verifica |
| 6.9 | `std/cipher.pengu` — `decode_base64` debe rechazar `=` no final | `std/cipher.pengu:162` | S | `"QQ==QQ=="` → `none`; test con padding inválido |
| 6.10 | `std/ledger.pengu` — `escape_field` debe comparar el delimitador completo | `std/ledger.pengu` | S | `"::"` entrecomilla correctamente; test |
| 6.11 | `std/compass.pengu` — prefijar los 32 helpers `cp_*` con `_` | `std/compass.pengu` | M | Superficie pública reducida a la API documentada; `grep -c "weave cp_"` → 0 |
| 6.12 | `std/chronicle.pengu` — `days_in_month` debe validar `m ∈ [1,12]` | `std/chronicle.pengu` | S | `m=0` y `m=13` devuelven 0; test |
| 6.13 | 🟠 **M5** — corregir 3 nombres en `CHEATSHEET.md` y el recuento de módulos | `CHEATSHEET.md:2367,2388,2391` | S | `compress`→`zlib_compress`, `product`→`product_num`, `max`→`max_int`, `min`→`min_int`; "25 modules"→"27" |
| 6.14 | Resolver los 3 módulos huérfanos (`celeris`, `xlsx`, `trial`) | `std/celeris.pengu`, `std/xlsx.pengu`, `std/trial.pengu` | M | **Decisión Requerida:** cada uno tiene un importador en `std/` o pasa a `std/contrib/` documentado como opt-in, o se deprecia |
| 6.15 | Listar las deprecations de la stdlib con fecha de retirada | `std/tally.pengu`, `std/oracle.pengu`, `docs/DEPRECATIONS.md` (nuevo) | S | Cada alias (`average`, `argmin`, `argmax`, `filter_range`) tiene entrada con versión de retirada |
| 6.16 | Benchmarks que importen `std` | `benches/*.pengu` (nuevos) | M | ≥6 benchmarks, uno por tier; `pengu benchmark` los ejecuta |
| 6.17 | Documentar `loom` como recomendado frente a `tally` para colecciones vacías | `LANGUAGE.md`, `CHEATSHEET.md`, docinline de ambos | S | La doc explica cuándo usar cada uno |

### Criterio de "done" de la fase

- [ ] Los 52 módulos: `pengu check --entry std/<mod>.pengu` → **0 errores y 0 warnings propios**.
- [ ] `crc32` coincide con el estándar para valores ≥ `0x80000000`.
- [ ] 0 `transmute` con size mismatch en la stdlib.
- [ ] 0 W0005 en la stdlib (o solo en bloques `test`, silenciados por 2.12).
- [ ] `loom`/`tally` sin nombres públicos en conflicto.
- [ ] 25/25 bindings con `<MOD>_VERSION`; todas las versiones coinciden con `VERSION`.
- [ ] ≥90 % de doc inline en `atlas`, `arithmancy`, `scrolls`; 100 % en el resto.
- [ ] `CHEATSHEET.md` sin nombres de función inexistentes (test que cruce nombres documentados con
      los `weave` reales).
- [ ] ≥6 benchmarks que importen `std` y corran en CI (`bench.yml`).

### Riesgos

- **Riesgo:** 6.7 (doc inline de 3 módulos grandes) es **L** por volumen: `atlas` 135 funciones,
  `arithmancy` 111, `scrolls` 66. **Mitigación:** es trabajo paralelizable; puede hacerse con varios
  contribuidores y no bloquea nada más que el gate de doc.
- **Riesgo:** 6.5 (`loom`/`tally`) puede romper a los usuarios que ya usan `tally.mean` esperando
  `int`. **Mitigación:** unificar hacia `loom` **añadiendo** alias deprecados en `tally` durante 1.x,
  no renombrando en seco.
- **Riesgo:** 6.14 puede revelar que `celeris`/`xlsx` dependen de `extern/` no construido.
  **Mitigación:** verificar con `test_ffi_libs.py` antes de decidir; si dependen de libs opcionales,
  moverlos a `std/contrib/` es la opción correcta.

---

## Fase 7 — Completar Style Guide y Docs

> **Requiere:** Fase 2, Fase 4, Fase 6
> **Bloquea:** Fase 10 (congelación)
> **Duración estimada:** **M** (5 días)

### Objetivo

Hacer que **cada afirmación de la documentación sea verificable por un test** y que las guías de
estilo describan el lenguaje que el compilador realmente implementa.

### Items

| # | Item | Archivos | Estimación | Done |
|---|------|----------|------------|------|
| 7.1 | 🟠 **A2** — generar §22.2 y §22.3 desde el código | `pengu_errors.py` (registro), `tools/gen_error_catalog.py` (nuevo), `LANGUAGE.md` | M | La tabla se genera; un test falla si el doc y el código divergen; las 5 clases fantasma desaparecen o se implementan |
| 7.2 | Eliminar la clase de bug de códigos compartidos | `pengu_checker.py`, `pengu_infer.py`, `pengu_errors.py` | M | Cada `(código, mensaje)` es único; `E0035` deja de cubrir 4 condiciones; `test_error_codes_uniqueness.py` analiza también las emisiones crudas |
| 7.3 | 🟠 **A17** — documentar la sintaxis canónica de rango y `frozen` | `LANGUAGE.md`, `LANGUAGE_Spanish.md` | S | Una sola forma canónica documentada; la deprecada marcada |
| 7.4 | Re-ejecutar y reparar los 105 bloques de `LANGUAGE.md` | `LANGUAGE.md`, `LANGUAGE_Spanish.md` | M | CI compila los bloques `pengu` completos → **0 fallos**; los `pengu-fragment` excluidos |
| 7.5 | 📝 **M6** — sincronizar versiones en los 13 archivos | `.md` de la raíz, `pengu_parser.py:92`, `pengu_lsp/__init__.py:1` | S | `tests/test_version.py` extendido escanea los `.md` y docstrings; 0 deriva |
| 7.6 | Aplicar el style guide a la stdlib de forma verificable | `std/*.pengu`, `PenguScriptGuide{English,Spanish}.md` | M | Reglas nuevas de §10.5 aplicadas; un test por regla (indentación, sin `transmute` fuera de ffi/filum, versiones asertadas) |
| 7.7 | Eliminar o relajar las reglas incumplibles | `PenguScriptGuide{English,Spanish}.md` | S | Las 5 reglas de AUDIT §10.4 ajustadas con excepción documentada |
| 7.8 | Añadir `CONTRIBUTING.md` | `CONTRIBUTING.md` (nuevo) | M | Cubre: cómo correr los tests, el principio "ningún gate por texto" (AUDIT §15.2), el estilo, y el proceso de release |
| 7.9 | Añadir `docs/ARCHITECTURE.md` | `docs/ARCHITECTURE.md` (nuevo) | M | Mapa de fases (parse → collect → check → infer → codegen → cache) con archivos y puntos de entrada |
| 7.10 | Añadir `docs/ABI.md` (ver 3.11) | `docs/ABI.md` | S | Qué es `PENGU_ABI_VERSION`, qué cambios lo bumpean |
| 7.11 | Añadir `docs/CROSS_COMPILATION.md` | `docs/CROSS_COMPILATION.md` (nuevo) | S | Cómo usar `--target`, toolchains requeridos, limitaciones |
| 7.12 | Añadir `MIGRATION.md` | `MIGRATION.md` (nuevo) | M | Guía por versión: qué cambió, cómo migrar; alimentado por `pengu migrate` (4.14) |
| 7.13 | Generar referencia de API por módulo | `tools/gen_api_docs.py`, `docs/api/*.md` | M | Los 1463 nombres públicos aparecen con firma y doc; el 37 % sin documentar baja a <10 % |
| 7.14 | Política de idioma: inglés canónico, español marcado no normativo | `README.md`, guías | S | Cada documento bilingüe declara su estado; CI verifica que el número de bloques `pengu` coincide entre los pares |

### Criterio de "done" de la fase

- [ ] El catálogo de errores de `LANGUAGE.md` se genera y un test detecta la divergencia.
- [ ] Ningún `(código, mensaje)` de diagnóstico está duplicado.
- [ ] CI compila los bloques `pengu` completos de `LANGUAGE.md` → 0 fallos.
- [ ] 0 deriva de versión en los 13 archivos.
- [ ] Cada regla del style guide tiene un test que la verifica en la stdlib.
- [ ] `CONTRIBUTING.md`, `docs/ARCHITECTURE.md`, `docs/ABI.md`, `docs/CROSS_COMPILATION.md`,
      `MIGRATION.md` existen.
- [ ] La referencia de API cubre ≥90 % de los nombres públicos de la stdlib.

### Riesgos

- **Riesgo:** 7.1 (generar el catálogo) puede revelar que hay que **implementar** las 5 clases
  fantasma o **cambiar** los códigos de 24 emisiones, lo que tocaría tests y usuarios.
  **Mitigación:** la opción honesta y barata es **documentar la realidad** (clases genéricas con
  código) en vez de crear 5 clases nuevas; decidir eso primero.
- **Riesgo:** 7.13 (docs de API para 1463 nombres) es **L** por volumen.
  **Mitigación:** parte del trabajo lo cubre 6.7; generar primero las firmas y dejar la prosa
  pendiente como deuda visible.
- **Riesgo:** 7.6 (aplicar el guide a la stdlib) puede entrar en conflicto con 6.4/6.7 si se hacen en
  paralelo. **Mitigación:** secuenciar Fase 6 → Fase 7.

---

## Fase 8 — Completar tests

> **Requiere:** Fase 1 (los bloqueantes definen qué testear); se solapa con 4, 5, 6
> **Bloquea:** Fase 10 (sin gates reales no hay congelación creíble)
> **Duración estimada:** **L** (1-2 semanas)

### Objetivo

Cerrar el agujero de cobertura que permitió que 11 bloqueantes convivieran con 2074 tests verdes:
**convertir todo gate que inspecciona texto en un gate que compila, ejecuta o mide**.

### Items

| # | Item | Archivos | Estimación | Done |
|---|------|----------|------------|------|
| 8.1 | 🔴 **B10** — convertir los 4 gates de texto | `tests/test_cli_strict_c99.py:50`, `tests/test_c99_portability.py`, `tests/test_error_codes_uniqueness.py`, `tests/test_attributes_msvc.py:39` | M | Los 4 **compilan o ejecutan**: strict-c99 compila los 56 programas de std; el de errores analiza las emisiones crudas; el de MSVC invoca un compilador o se renombra a `test_attributes_msvc_text.py` |
| 8.2 | 🔴 **B9** — el job de sanitizers debe estar verde | `.github/workflows/sanitizers.yml:58-70,104` | S | El 3er paso hereda el `--deselect`; valgrind también; el job pasa |
| 8.3 | 🔴 **A11** — añadir `ruff` a CI con `F821` como error | `requirements.txt`, `pyproject.toml` (nuevo), `.github/workflows/ci.yml` | S | `ruff check --select F821,E9` → 0 violaciones; **habría cazado B6** |
| 8.4 | 🟠 **A13** — corpus de compliance: 50 programas canónicos | `tests/compliance/` (nuevo, 50 archivos + runner) | L | 50 programas numerados, uno por sección de `LANGUAGE.md`, todos compilan y ejecutan en CI |
| 8.5 | 🟠 **A13** — corpus de migración | `tests/migration/` (nuevo) | M | Programas de cada versión publicada compilan sin cambios; los que deben fallar, fallan con el código esperado |
| 8.6 | Añadir `pytest-cov` y un umbral | `requirements.txt`, `ci.yml`, `.coveragerc` | S | Cobertura medida y reportada; umbral inicial fijado en el valor actual y **no decreciente** |
| 8.7 | 🟠 **M13** — property-based testing con `hypothesis` | `requirements.txt`, `tests/test_properties.py` (nuevo) | M | Las 7 propiedades de AUDIT §11.5 implementadas; en particular **idempotencia del fmt** y **preservación de semántica del fmt** |
| 8.8 | Test de contrato de CLI (rc y efectos por subcomando) | `tests/test_cli_contract.py` (nuevo) | M | Los 25 subcomandos: rc esperado en éxito y en cada clase de fallo, con y sin posiciónales |
| 8.9 | Test de cada `code="Exxxx"` alcanzable | `tests/test_error_reachability.py` (nuevo) | M | Cada uno de los 58 códigos tiene un programa mínimo que lo dispara; los inalcanzables se marcan |
| 8.10 | Test de estrés: 10 000 líneas | `tests/test_scale.py` (nuevo) | M | Un archivo de 10 000 líneas compila; `check` y `build` miden y reportan tiempo |
| 8.11 | Job real de MSVC **o** retirar la afirmación | `.github/workflows/ci.yml` o `msvc.yml` (nuevo), `RELEASE_CHECKLIST.md:13` | M | Job `windows-latest` + `cl.exe` verde, **o** la afirmación MSVC eliminada de todos los documentos |
| 8.12 | `cross-compile.yml` | `.github/workflows/cross-compile.yml` (nuevo) | M | `--target x86_64-w64-mingw32` produce un `.exe` en Linux con mingw instalado; el `.exe` se ejecuta con wine o se valida su cabecera PE |
| 8.13 | `compliance.yml` / `migrate.yml` | `.github/workflows/` | S | Los corpus 8.4/8.5 corren en workflows propios o como jobs de `ci.yml` |
| 8.14 | `codeql.yml` | `.github/workflows/codeql.yml` (nuevo) | S | CodeQL analiza Python y C; 0 alertas de severidad alta |
| 8.15 | Fijar las actions a SHA de commit | todos los `.github/workflows/*.yml` | S | `grep -n "uses:.*@v[0-9]" .github/` → 0 |
| 8.16 | `nightly.yml` con presupuesto realista | `.github/workflows/nightly.yml` (nuevo) | S | Fuzz en shards de ≤6 h por harness (respetando el límite de GitHub) |
| 8.17 | Arreglar el `xpassed` | `tests/` | S | El test pasa a `xfail(strict=True)` o se desmarca; `pytest -q` reporta 0 xpassed. Complementa al item **1.14**, que además exige que el resultado sea reproducible |
| 8.18 | `conftest.py`: añadir fixtures de compilación C reutilizables | `tests/conftest.py` | M | Los tests de portabilidad y MSVC usan las mismas fixtures que `:227` |

### Criterio de "done" de la fase

- [ ] `ruff check --select F821,E9` → 0 violaciones, corriendo en CI.
- [ ] El job de sanitizers está verde.
- [ ] `pytest -q` reporta **0 xpassed**.
- [ ] Los 50 programas canónicos compilan y ejecutan en CI.
- [ ] El corpus de migración cubre cada versión publicada.
- [ ] Cobertura medida con umbral no decreciente.
- [ ] Las 7 propiedades de property-based testing activas, incluidas las 2 del formateador.
- [ ] Los 25 subcomandos tienen test de contrato de rc.
- [ ] Cada uno de los 58 códigos de error tiene un programa que lo dispara (o está documentado como
      inalcanzable).
- [ ] MSVC: job verde **o** afirmación retirada.
- [ ] Cross-compile produciendo un `.exe` real.
- [ ] CodeQL en CI con 0 alertas altas.
- [ ] Todas las actions fijadas por SHA.
- [ ] **Ningún test del repositorio verifica una propiedad inspeccionando texto.**

### Riesgos

- **Riesgo:** 8.11 (MSVC real) puede destapar una cadena larga de incompatibilidades del runtime y de
  los `std_c/*.h` de terceros. **Mitigación:** presupuestar como **L** y, si el coste excede el
  presupuesto de 1.0, **retirar la afirmación MSVC** (opción igualmente válida y honesta); lo
  inaceptable es mantener la afirmación con la matriz en MinGW.
- **Riesgo:** 8.4 (50 canónicos) es trabajo de autoría, no de ingeniería. **Mitigación:** derivarlos
  de las secciones de `LANGUAGE.md` es mecánico; paralelizable.
- **Riesgo:** 8.7 (property-based) puede descubrir bugs nuevos y desestabilizar el calendario.
  **Mitigación:** es un objetivo, no un riesgo: ejecutarlos primero en modo no bloqueante y
  convertirlos en bloqueantes cuando pasen.
- **Riesgo:** 8.6 (umbral de cobertura) con un valor inicial bajo puede dar falsa confianza.
  **Mitigación:** el umbral debe ser "no decreciente" y reportarse por archivo, con atención a
  `pengu_project.py` y a los 3 archivos grandes del compilador.

---

## Fase 9 — Herramientas de release

> **Requiere:** Fase 3 (runtime/ABI), Fase 4 (CLI)
> **Bloquea:** Fase 10, Fase 11
> **Duración estimada:** **M** (4-5 días)

### Objetivo

Hacer que la cadena de release **verifique lo que descarga**, **produzca artefactos reproducibles** y
**publique solo lo que pasó los gates**.

### Items

| # | Item | Archivos | Estimación | Done |
|---|------|----------|------------|------|
| 9.1 | 🟠 **A12** — SHA-256 en el manifest de externos | `extern_manifest.py:16-43,123-141` | M | Cada entrada tiene `sha256`; el stream se verifica **antes** de extraer; `force=True` en la ruta de release |
| 9.2 | 🟠 **A12** — verificación del TCC descargado | `pengu_tcc.py:118-152` | S | Digest fijado como constante; `zipfile` verificado; fallo duro en mismatch |
| 9.3 | 🟠 **A12** — fijar un digest por defecto para `PENGU_TCC_SHA256` | `.github/workflows/release.yml:76-99` | S | Existe un default; el workflow falla si no coincide (no un `::notice::`) |
| 9.4 | `tarfile.extractall(filter="data")` y validación de rutas en zip | `extern_manifest.py:124`, `pengu_tcc.py:143` | S | Sin rutas de escape; extracción endurecida explícitamente (no por defecto de la versión de Python) |
| 9.5 | 🟠 **A16** — presupuestos de fuzzing realistas | `docs/FUZZING.md:69`, `RELEASE_CHECKLIST.md:27`, `fuzz.yml:23,39` | S | Documentado ≤6 h por harness; el workflow corre en shards; sin afirmaciones imposibles |
| 9.6 | Hacer que el traspaso tag→release funcione | `ci.yml:205-221`, `release.yml` | M | El tag dispara `release.yml` (PAT/App o `workflow_dispatch` explícito); verificado en un fork de prueba |
| 9.7 | `release-verify.yml` | `.github/workflows/release-verify.yml` (nuevo) | M | Tras publicar, descarga cada artefacto y lo ejecuta (`pengu -V`, un build, un run) |
| 9.8 | Reproducibilidad de `make_release.py` | `make_release.py` | M | Dos ejecuciones del mismo commit producen artefactos con el mismo hash (con `SOURCE_DATE_EPOCH`) |
| 9.9 | Notarización macOS | `make_release.py`, `release.yml` | M | El artefacto de macOS pasa `spctl --assess`; documentado en `docs/RELEASE.md` |
| 9.10 | `docs/RELEASE.md` con el proceso completo | `docs/RELEASE.md` (nuevo) | M | Proceso paso a paso, con los gates que deben estar verdes y qué hacer si uno falla |
| 9.11 | Reescribir `RELEASE_CHECKLIST.md` para que **cada** casilla tenga un gate | `RELEASE_CHECKLIST.md` | M | Cada casilla referencia un workflow o un comando reproducible; 0 afirmaciones sin gate (elimina las 5 refutadas de AUDIT §13.3) |
| 9.12 | Verificar el layout portable y FHS en CI | `ci.yml` o `release-verify.yml` | M | Se instala el artefacto en un prefijo FHS y en modo portable y se ejecutan |

### Criterio de "done" de la fase

- [ ] `grep -c "hashlib" extern_manifest.py` ≥ 1 y cada entrada del manifest tiene digest verificado.
- [ ] El TCC descargado se verifica con un digest que **existe** por defecto.
- [ ] Ningún `extractall` sin `filter`/validación.
- [ ] `docs/FUZZING.md` y `RELEASE_CHECKLIST.md` no contienen afirmaciones de duración imposibles.
- [ ] El tag dispara el release (verificado end-to-end).
- [ ] `release-verify.yml` descarga y ejecuta los artefactos publicados.
- [ ] Dos builds del mismo commit son byte-idénticos.
- [ ] El artefacto macOS pasa `spctl --assess`.
- [ ] `RELEASE_CHECKLIST.md`: cada casilla tiene un comando o workflow asociado.

### Riesgos

- **Riesgo:** 9.1 requiere descargar todas las fuentes para calcular digests (329 MB de `extern/`).
  **Mitigación:** hacerlo una vez y versionar la tabla de digests; no recalcular en cada build.
- **Riesgo:** 9.6 puede requerir un PAT, que es un secreto organizacional.
  **Mitigación:** la alternativa `workflow_dispatch` desde el job del tag funciona con
  `GITHUB_TOKEN` y no necesita secretos nuevos.
- **Riesgo:** 9.9 (notarización macOS) requiere una cuenta de desarrollador de Apple.
  **Mitigación:** si no está disponible, **retirar la reivindicación** de notarización en vez de
  dejarla sin verificar.

---

## Fase 10 — Congelación y RC

> **Requiere:** Fases 1-9
> **Bloquea:** Fase 11
> **Duración estimada:** **M** (4-5 días)

### Objetivo

Congelar la superficie pública, cortar un release candidate y someter **todas** las afirmaciones de
la documentación a un gate antes de declarar 1.0.

### Items

| # | Item | Archivos | Estimación | Done |
|---|------|----------|------------|------|
| 10.1 | Congelar la superficie pública: lenguaje, ABI, CLI, stdlib, LSP | `docs/FREEZE.md` (nuevo) | M | Documento que enumera exactamente qué es API pública y qué puede cambiar en 1.x |
| 10.2 | Auditar **línea a línea** las afirmaciones de los 3 documentos de release | `RELEASE_CHECKLIST.md`, `BENCHMARKS.md`, `SECURITY.md` | M | Cada afirmación tiene un gate o se ha retirado; 0 ❌ REFUTADO pendientes |
| 10.3 | Re-ejecutar la matriz completa de compiladores sobre el RC | CI | M | gcc, clang, MinGW, **tcc** y (si 8.11 salió bien) **MSVC**: todos compilan y ejecutan el corpus de compliance |
| 10.4 | Re-ejecutar sanitizers y valgrind sobre el RC | CI | S | ASan/UBSan/valgrind verdes; los leaks conocidos en `xfail(strict=True)` |
| 10.5 | Fuzzing del RC con el presupuesto real | `fuzz.yml` | M | ≥6 h por harness sin crash |
| 10.6 | Verificar la migración desde 0.14.x/0.15.0 | `tests/migration/`, `pengu migrate` | M | Los programas del corpus de migración compilan y corren |
| 10.7 | Actualizar todas las versiones a `1.0.0-rc1` | `VERSION`, `pengu_version.py:FALLBACK_VERSION`, stdlib, docs | S | `tests/test_version.py` verde; `pengu -V` → `1.0.0-rc1` |
| 10.8 | Publicar el RC y congelar `main` durante la validación | `release.yml` | S | RC publicado; rama `release/1.0` cortada |
| 10.9 | Periodo de validación del RC | — | L | ≥1 semana sin bloqueantes nuevos; los 3 documentos de release sin cambios |
| 10.10 | Ensayo de release completo en un fork | — | M | El proceso de `docs/RELEASE.md` corre de principio a fin sin intervención manual |
| 10.11 | Test de instalación desde cero en las 3 plataformas | `release-verify.yml` | M | Un contenedor/VM limpio instala el RC y compila "hello world" |

### Criterio de "done" de la fase

- [ ] `docs/FREEZE.md` publicado y la superficie pública declarada congelada.
- [ ] **Cero** afirmaciones refutadas en `RELEASE_CHECKLIST.md`, `BENCHMARKS.md`, `SECURITY.md`.
- [ ] La matriz completa de compiladores verde sobre el RC.
- [ ] Sanitizers y valgrind verdes; fuzzing ≥6 h/harness sin crash.
- [ ] El corpus de migración verde.
- [ ] `pengu -V` → `1.0.0-rc1` y todas las versiones sincronizadas.
- [ ] ≥1 semana de RC sin bloqueantes nuevos.
- [ ] Ensayo de release completo reproducible en un fork.
- [ ] Instalación desde cero verificada en Linux, macOS y Windows.

### Riesgos

- **Riesgo:** el periodo de validación revela un bloqueante nuevo. **Mitigación:** es el propósito de
  la fase; el RC existe para eso. Un bloqueante nuevo retrasa 1.0 pero no invalida el proceso.
- **Riesgo:** 10.2 puede encontrar una afirmación que no se puede verificar
  (p. ej. la notarización macOS sin cuenta Apple). **Mitigación:** **retirar la afirmación**; una
  promesa sin gate es peor que una promesa ausente.

---

## Fase 11 — 1.0.0

> **Requiere:** Fase 10
> **Bloquea:** nada
> **Duración estimada:** **S** (2 días)

### Objetivo

Publicar 1.0.0.

### Items

| # | Item | Archivos | Estimación | Done |
|---|------|----------|------------|------|
| 11.1 | Subir la versión a `1.0.0` en todos los sitios | `VERSION`, `pengu_version.py`, stdlib, docs | S | `tests/test_version.py` verde; `pengu -V` → `1.0.0` |
| 11.2 | Mover `CHANGELOG.md` de `Unreleased` a `[1.0.0]` | `CHANGELOG.md` | S | Entrada `## [1.0.0] — <fecha>` con resumen de los 11 bloqueantes cerrados |
| 11.3 | Crear el tag firmado y publicar | `git tag -s v1.0.0`, `release.yml` | S | Tag firmado; artefactos publicados y verificados por `release-verify.yml` |
| 11.4 | Escribir el anuncio de 1.0 | `docs/ANNOUNCEMENT_1.0.md` (nuevo) | M | Explica qué es 1.0, qué no es (con la lista ⏸️ de §20.6), y en qué confiar |
| 11.5 | Actualizar el roadmap vivo | `ROADMAP_2.0.md` → `ROADMAP_1.1.md` | S | Nuevo roadmap con los items ⏸️ de §20.6 como candidatos |
| 11.6 | Depositar el corpus de compliance y migración como referencia pública | `tests/compliance/`, `tests/migration/` | S | Documentado como "esto define la compatibilidad de 1.x" |

### Criterio de "done" de la fase

- [ ] `pengu -V` → `1.0.0`.
- [ ] Tag `v1.0.0` firmado y publicado.
- [ ] Los artefactos publicados pasan `release-verify.yml`.
- [ ] `CHANGELOG.md` con la entrada `[1.0.0]`.
- [ ] El anuncio declara explícitamente qué **no** incluye 1.0 (los items ⏸️).
- [ ] `ROADMAP_1.1.md` existe con los items diferidos.

### Riesgos

- **Riesgo:** publicar con una promesa no verificada. **Mitigación:** 10.2 es bloqueante para 11.3.
- **Riesgo:** que el anuncio sobrevenda. **Mitigación:** el anuncio debe incluir la sección ⏸️ de
  `AUDIT_1.0.md` §20.6 y el resultado de la matriz de compiladores **tal cual**.

---

## ⏸️ Diferido a 1.1+ (con justificación técnica)

| Item | Justificación | Fase candidata |
|------|---------------|----------------|
| **Borrow checking real** | Cambio de análisis, no de sintaxis. Requiere modelar tiempos de vida y puede invalidar código válido; hacerlo antes de 1.0 rompería compatibilidad hacia atrás. Es el "holy grail" (AUDIT §9.11) y merece su propia versión con periodo de deprecación | 1.1 (feature estrella) |
| **Associated types (`alias Item` en `concept`)** | Feature de lenguaje mediana con resolución en bounds. Hoy el trabajo se hace con `shard T and U`. **Mientras no exista, el ejemplo debe retirarse de la doc** (item 2.3, rama "retirar") | 1.1 |
| **Async/await nativo** | Sin GC y con ownership determinista, un runtime async es un proyecto de meses; no hay demanda en la stdlib ni en los 56 programas de test | 1.2+ |
| **Closures con captura** | Rompe la decisión de diseño de emitir funciones C `static` de nivel superior; requeriría struct + función, que es una feature de lenguaje completa | 1.2+ |
| **Macros de AST** | Superficie enorme, riesgo de incompatibilidad, y `when`/`comptime`/`shard` cubren el 80 % de los casos de uso reales | 1.3+ |
| **Dynamic dispatch / vtable** | Contradice la reivindicación central de "zero runtime overhead" de los concepts; debe ser una decisión explícita con documento propio | 1.3+ (solo si hay demanda) |
| **Reflection / RTTI** | Rompería el modelo de C puro y el tamaño cero de los concepts | No planificado |
| **Backtracking completo en resolución de deps** | No hay evidencia de fallo en casos reales; el resolvedor actual maneja los 52 módulos y las deps locales. Añadirlo es especulativo | 1.1 si aparece un caso real |
| **Migración completa de `Result` en la stdlib** | La API de doble vía (`write_file` + `write_file_result`) funciona; forzar la migración rompería los 174 tests de std y a los usuarios | 1.2, con deprecación larga |
| **Playground WASM** | Requiere un target WASM que no existe; ya estaba diferido | 1.3+ |
| **`derive` para el 100 % de los concepts** | `Par`/`Ordo` cubren los casos reales; el resto no tiene demanda medida. Se documenta la matriz en 2.8 | 1.1 |
| **Semantic tokens por rango/delta en el LSP** | Mejora de rendimiento, no de correctitud; el editor funciona con tokens completos | 1.1 (item 5.9) |
| **`pengu repl`** | `pengu eval` cubre la necesidad puntual; un REPL real requiere estado incremental en el compilador (que hoy reconstruye el `inferrer` por llamada) | 1.1 |
| **Windows `__declspec(thread)` en DLLs dinámicas** | Limitación de la plataforma documentada por Microsoft; solo aplica a DLLs cargadas con `LoadLibrary` | Documentar, no arreglar |
| **Cobertura de `clang -Weverything` (389 warnings)** | 267 son `-Wunsafe-buffer-usage`, que es una preferencia de estilo de una toolchain, no un bug. Se mantiene el estándar `-Wall -Wextra -Werror` | No planificado |
| **Idioma único en la documentación** | La cobertura bilingüe real es un activo (72 bloques sincronizados en cada guía). Se formaliza la política (item 7.14) en vez de eliminar un idioma | N/A |

---

---

## Anexo A — Diagnóstico de partida verificado

Esta tabla es la entrada del roadmap: cada cifra fue medida en la auditoría y es la línea base contra
la que se comprobará el progreso. **Cualquier fase que empeore uno de estos números debe justificarlo.**

| Métrica de partida | Valor | Comando de verificación |
|--------------------|-------|-------------------------|
| Versión | `0.16.0` | `cat VERSION` |
| Tests | **2074 passed, 12 skipped, 2 xfailed, 1 xpassed** en 910.67 s | `pytest tests/ -q -p no:cacheprovider --timeout=900` |
| Archivos de test | 155 | `ls tests/*.py \| wc -l` |
| LOC de test | 36 590 | `wc -l tests/*.py \| tail -1` |
| LOC del compilador | 27 204 (`pengu_parser/`) | `wc -l pengu_parser/*.py \| tail -1` |
| LOC del LSP | 4 144 | `wc -l pengu_lsp/*.py \| tail -1` |
| LOC del tooling (raíz) | 12 085 | `wc -l *.py \| tail -1` |
| Módulos de stdlib | 52 (27 puros + 25 bindings) | `ls std/*.pengu \| wc -l` |
| LOC de stdlib | 35 910 | `wc -l std/*.pengu \| tail -1` |
| Errores de `check` en la stdlib | **0** | `for m in std/*.pengu; do pengu check --entry $m; done` |
| Warnings propios de la stdlib | **50** (29 W0005 + 21 W0001) | idem |
| Clases de error definidas | 38 (35 con código) | `grep -c '^class ' pengu_parser/pengu_errors.py` |
| Códigos de error emitidos | 58 | `grep -ohP 'E\d{4}' pengu_parser/*.py \| sort -u \| wc -l` |
| Clases de error fantasma | **5** | `grep -rn DanglingSliceError --include="*.py" .` |
| Warnings de pyflakes | **132** (4 `undefined name`, 1 real) | `pyflakes pengu_parser/*.py pengu_lsp/*.py *.py` |
| `undefined name` reales | **1** (`pengu_infer.py:4055`) | idem + verificación manual |
| Funciones > 200 líneas | 18 | AST sobre los 5 archivos grandes |
| Función más larga | **2870** (`infer`) | AST |
| Warnings de C en el bundle | **0** | `gcc -Wall -Wextra -Wshadow -fsyntax-only atlas.c` |
| Warnings de C en el runtime header | **0** | `gcc -std=c11 -Wall -Wextra -Werror -fsyntax-only pengu_runtime.h` |
| Errores de C en el runtime `.c` sin supresión | **24** | `gcc … -c pengu_parser/pengu_runtime.c` sin `-Wno-implicit-function-declaration` |
| Error duro en bundle `--strict-c99` | **13** | `gcc -std=c11 -Wall -Wextra -c h_strict.c` |
| Statement-expressions restantes en estricto | **104** | `grep -c '({' atlas_strict.c` |
| Ciclos de importación | **0** | inspección de los 5 pares sospechosos |
| Subcomandos del CLI | **25** | `pengu --help` |
| Subcomandos con test de contrato de rc | **0** | `grep -rn "parse_known_args\|rc=2" tests/` |
| Features LSP implementadas | **13 de 16** | introspección del dict de capacidades |
| Bloques de `LANGUAGE.md` que pasan `check` | **33 de 105** | bucle por proyecto |
| Bloques que fallan por defecto documental real | **4** (bloques 15, 28, 59, 94) | clasificación manual del resultado |
| Afirmaciones documentales refutadas | **23** | `AUDIT_1.0.md` §18.1 |
| Suposiciones del encargo refutadas | **14** | `AUDIT_1.0.md` §18.2 |
| Afirmaciones subestimadas | **12** | `AUDIT_1.0.md` §18.3 |
| `TODO`/`FIXME` totales | **94** (68 en terceros) | `grep -rn` |
| Workflows | **5** | `ls .github/workflows/` |
| Workflows en rojo | **1** (`sanitizers.yml`) | inspección + reproducción |
| Jobs con `cl.exe` | **0** | `grep -rn "cl.exe\|cl /" .github/` |
| Pasos de SAST | **0** | `grep -rn "codeql\|semgrep" .github/` |
| Verificación SHA-256 de descargas | **0** | `grep -c hashlib extern_manifest.py` |

**Objetivo de la línea base al final de la Fase 1:** los 5 bloqueantes de correctitud cerrados, y
`pyflakes | grep -c "undefined name"` → 0.
**Objetivo al final de la Fase 8:** `ruff check --select F821,E9` → 0, 0 xpassed, corpus de
compliance y migración en CI, cobertura medida.
**Objetivo al final de la Fase 10:** 0 afirmaciones refutadas en los 3 documentos de release.

---

## Anexo B — Matriz bloqueante → fase → test de regresión

Cada bloqueante de `AUDIT_1.0.md` §20.1 debe tener **exactamente** un item que lo cierre y **al menos**
un test que falle si se revierte. Esta matriz es el contrato de la auditoría con el roadmap.

| Bloqueante | Severidad | Fase / item | Test de regresión | Comando que debe pasar |
|-----------|-----------|-------------|-------------------|------------------------|
| **B1** `check <archivo>` ignora el archivo | 🔴 | 1.2 | `tests/test_cli_contract.py::test_check_positional` | `pengu check roto.pengu; echo $?` → `1` |
| **B2** entry inexistente devuelve ok | 🔴 | 1.3 | `tests/test_cli_contract.py::test_check_missing_entry` | `cd /tmp/vacio && pengu check; echo $?` → ≠0 |
| **B3** `parse_known_args` descarta flags | 🔴 | 1.1 | `tests/test_cli_contract.py::test_unknown_flag` | `pengu check --bogus; echo $?` → `2` |
| **B4** `fmt --indent` corrompe | 🔴 | 4.1, 4.2 | `tests/test_properties.py::test_fmt_idempotent`, `::test_fmt_preserves_semantics` | `pengu fmt --check std/` → 0 cambios |
| **B5** `--strict-c99` no compila | 🔴 | 3.2, 3.3 | `tests/test_c99_portability.py::test_strict_mode_over_std_programs` | `gcc -std=c99 -pedantic-errors` sobre los 56 bundles → 0 errores |
| **B6** `node`→`target_node` (`NameError`) | 🔴 | 1.4 | `tests/test_module_qualified_types.py::test_private_symbol_access_raises_E0043` | programa con `lib._privado` → `E0043`, no traceback |
| **B7** tipos cualificados pierden campos | 🔴 | 1.5, 1.6 | `tests/test_module_qualified_types.py::test_dep_qualified_rune_fields` | programa de 3 módulos compila; `raymath.Vector2` funciona |
| **B8** runtime `.c` no compila sin supresión | 🟠 | 3.1 | `tests/test_runtime_clean_compile.py` | `gcc -Wall -Wextra -c pengu_parser/pengu_runtime.c` (flags reales) → 0 errores |
| **B9** job de sanitizers rojo | 🔴 | 8.2 | (workflow) | El job `sanitizers` pasa en CI |
| **B10** gates por texto | 🔴 | 8.1 | Los 4 tests reescritos | `grep -rn 'not in bundle\|not in result' tests/` → 0 gates por texto |
| **B11** 188 conflictos shift/reduce | 🟠 | 2.4, 2.4b | `tests/test_precedence.py::test_associativity_and_precedence` | `Lark(GRAMMAR, parser='lalr', strict=True)` sin excepción; los 9 árboles de §1.1 intactos |

---

## Anexo C — Criterios de aceptación transversales

Estos criterios aplican a **todas** las fases y a cualquier PR. Se proponen como contenido de
`CONTRIBUTING.md` (item 7.8).

### C1. Ninguna propiedad se aprueba inspeccionando texto

**Prohibido:**
```python
assert "__extension__" not in bundle          # ✗ no prueba portabilidad
assert "product" in cheatsheet                # ✗ no prueba que la función exista
assert "MSVC" in matrix                       # ✗ no prueba que MSVC funcione
```

**Requerido:**
```python
subprocess.run(["gcc", "-std=c99", "-pedantic-errors", "-c", bundle], check=True)
assert module.has_public_function("product_num")   # introspección real
subprocess.run(["cl.exe", "/W4", "/WX", bundle], check=True)
```

**Cómo verificar que se cumple:** `grep -rn "not in " tests/*.py | grep -i "bundle\|matrix\|cheatsheet"` → 0.

### C2. Todo bloqueante tiene un test que falla al revertir el fix

**Cómo verificar que se cumple:** para cada item de la matriz del Anexo B, revertir el cambio y
confirmar que el test de regresión falla. Sin esa comprobación, el test no se considera válido.

### C3. Toda afirmación de la documentación de release tiene un gate

**Cómo verificar que se cumple:** cada casilla de `RELEASE_CHECKLIST.md` referencia un workflow, un
job o un comando reproducible. `grep -c "^- \[ \]" RELEASE_CHECKLIST.md` debe igualar el número de
casillas con un `backtick` de comando en la misma línea.

### C4. El compilador nunca lanza una excepción no-PenguError sobre entrada de usuario

**Cómo verificar que se cumple:**
```bash
# Fuzz ligero de entradas malformadas: ninguna debe producir un traceback de Python
for f in tests/fuzz_corpus/*.pengu; do
  out=$(pengu check "$f" 2>&1)
  if echo "$out" | grep -q "Traceback (most recent call last)"; then echo "FAIL: $f"; fi
done
```
Esto habría cazado B6 y habría detectado cualquier `NameError`/`AttributeError` futuro.

### C5. Ningún cambio de sintaxis sin entrada en el corpus de compliance y de migración

Toda feature nueva o modificada añade: (a) un programa en `tests/compliance/`, (b) si rompe
compatibilidad, una entrada en `tests/migration/` y una en `MIGRATION.md`.

### C6. Las funciones nuevas no superan un umbral de tamaño acordado

Umbral propuesto: **80 líneas** para funciones nuevas en `pengu_parser/`. Las 18 funciones existentes
>200 líneas se refactorizan de forma oportunista (no como prerequisito de 1.0), pero **no crecen**.

**Cómo verificar que se cumple:** un test que compare el `end_lineno - lineno` de cada función contra
un baseline versionado en `tools/function_size_baseline.json`; cualquier función que **crezca** falla.

### C7. `ruff --select F821,E9` limpio

Nombres no definidos y errores de sintaxis son **errores de CI**, no warnings. Habría cazado B6.

---

## Anexo D — Comandos de verificación por fase

Script reproducible para comprobar el avance de cada fase. Se propone como `scripts/verify_roadmap.sh`.

```bash
#!/usr/bin/env bash
# Uso: scripts/verify_roadmap.sh [fase]
set -uo pipefail
PENGU="./.venv/bin/pengu"
PY="./.venv/bin/python"
fail=0
ok()   { printf "  \033[32mOK\033[0m   %s\n" "$1"; }
bad()  { printf "  \033[31mFAIL\033[0m %s\n" "$1"; fail=1; }
chk()  { if eval "$2" >/dev/null 2>&1; then ok "$1"; else bad "$1"; fi; }

echo "== Fase 0: limpieza =="
chk "pengu_runtime.c raíz eliminado"      "! git cat-file -s HEAD:pengu_runtime.c"
chk "sin __pycache__ propio"              "[ \$(find . -name __pycache__ -not -path './extern/*' | wc -l) -eq 0 ]"
chk "git status limpio"                   "[ -z \"\$(git status --short)\" ]"
chk "suite sin regresiones"               "$PY -m pytest tests/ -q -p no:cacheprovider --timeout=900"

echo "== Fase 1: correctitud =="
chk "B1 check valida el archivo"          "printf 'weave main:\n  basura @@@\n' > /tmp/r.pengu && ! $PENGU check /tmp/r.pengu"
chk "B2 entry inexistente es error"       "(cd /tmp && $PENGU check) ; [ \$? -ne 0 ]"
chk "B3 flags desconocidos rechazados"    "! $PENGU check --bogus"
chk "B6 sin undefined name"               "[ \$($PY -m pyflakes pengu_parser/ pengu_lsp/ *.py 2>&1 | grep -c 'undefined name') -eq 0 ]"
chk "B7 tipos cualificados"               "$PY -m pytest tests/test_module_qualified_types.py -q"

echo "== Fase 3: runtime y portabilidad =="
chk "B8 runtime C99 legal sin supresión"  "$PY -m pytest tests/test_runtime_clean_compile.py -q"
chk "B5 strict-c99 sobre std"             "$PY -m pytest tests/test_c99_portability.py -q"
chk "ABI exportada"                       "nm build/lib/libpengu_runtime.a | grep -q pengu_abi_version"
chk "runtime header sin warnings"         "gcc -std=c11 -Wall -Wextra -Werror -fsyntax-only pengu_runtime.h"

echo "== Fase 4: CLI =="
chk "B4 fmt idempotente"                  "$PENGU fmt --check std/ ; [ \$? -eq 0 ]"
chk "A4 --quiet silencioso"               "[ -z \"\$($PENGU --quiet build 2>/dev/null)\" ]"
chk "A4 --no-color sin ANSI"              "! $PENGU --no-color check | cat -v | grep -q '\^\[\['"
chk "A5 test --json emite JSON"           "$PENGU test --json | head -1 | $PY -c 'import json,sys; json.loads(sys.stdin.read())'"

echo "== Fase 8: tests =="
chk "C7 ruff F821 limpio"                 "$PY -m ruff check --select F821,E9 . "
chk "sin gates por texto (C1)"            "[ \$(grep -rn 'not in ' tests/*.py | grep -ci 'bundle\\|matrix\\|cheatsheet') -eq 0 ]"
chk "C4 sin tracebacks en corpus"         "! bash -c 'for f in tests/fuzz_corpus/*.pengu; do $PENGU check \$f 2>&1 | grep -q Traceback && exit 1; done'"
chk "0 xpassed"                           "! $PY -m pytest tests/ -q 2>&1 | grep -q xpassed"
chk "corpus de compliance"                "[ \$(ls tests/compliance/*.pengu | wc -l) -ge 50 ]"

echo "== Fase 9: release =="
chk "manifest con SHA-256"                "grep -q hashlib extern_manifest.py && grep -q sha256 extern_manifest.py"
chk "TCC con digest por defecto"          "grep -qP 'PENGU_TCC_SHA256\s*=\s*\"[0-9a-f]{64}\"' pengu_tcc.py .github/workflows/release.yml"

echo "== Fase 10: afirmaciones =="
chk "RELEASE_CHECKLIST sin afirmaciones sin gate" "$PY -m pytest tests/test_release_claims.py -q"

if [ $fail -eq 0 ]; then
  echo -e "\n\033[32mTodos los gates de la fase pasan.\033[0m"
else
  echo -e "\n\033[31mHay gates en rojo.\033[0m"
fi
exit $fail
```

---

## Anexo E — Qué se puede hacer en paralelo

Para un equipo de 2-3 personas, la secuencia óptima no es lineal. Después de la **Fase 0 + Fase 1**
(que son el punto de sincronización obligatorio), el trabajo se abre en tres vías independientes
durante ~3 semanas:

| Vía | Fases | Por qué es independiente |
|-----|-------|-------------------------|
| **Vía A — Compilador** | Fase 2 → Fase 3 | Toca `pengu_grammar.py`, `pengu_types.py`, `pengu_codegen.py`, `pengu_runtime.*`. No solapa con CLI ni con docs |
| **Vía B — Superficie** | Fase 4 → Fase 5 | Toca `pengu_project.py` y `pengu_lsp/`. Fase 4 depende de la 1, no de la 2/3 |
| **Vía C — Contenido** | Fase 6 → Fase 8 | Toca `std/*.pengu` y `tests/`. Fase 6 depende de la 2 solo para 2.1 (bounds); el resto es independiente |

**Puntos de sincronización:**

1. Tras Fase 1: las tres vías arrancan. **Único requisito: los 5 bloqueantes de correctitud cerrados.**
2. Fase 6 necesita la decisión de 2.1 (bounds). **Decidir 2.1 en la primera semana de la Fase 2 y
   comunicarlo**, porque condiciona si hay que tocar la stdlib.
3. Fase 7 (docs) necesita Fases 2, 4 y 6 completas. **Es la vía de convergencia.**
4. Fase 8 (tests) se solapa deliberadamente con 4, 5 y 6: cada vía escribe los tests de lo que toca.
   El item 8.1 (gates de texto) es transversal y debe hacerse **temprano**, no al final.
5. Fases 9-11 son lineales y secuenciales.

**Recomendación de reparto para 2 personas:**

| Semana | Persona 1 | Persona 2 |
|--------|-----------|-----------|
| 1 | Fase 0 + 1.1-1.4 | Fase 0 + 1.5-1.11 |
| 2 | Fase 2 (2.1, 2.2, 2.4) | Fase 3 (3.1, 3.4, 3.12) |
| 3 | Fase 3 (3.2, 3.5, 3.6) | Fase 4 (4.1-4.5) |
| 4 | Fase 3 (3.3, 3.9, 3.10) | Fase 4 (4.6-4.16) |
| 5 | Fase 2 (2.3, 2.5-2.12) | Fase 5 (5.1-5.11) |
| 6-7 | Fase 8 (8.1, 8.3, 8.4, 8.7) | Fase 6 (6.1-6.6, 6.9-6.13) |
| 8-9 | Fase 6 (6.7, 6.8, 6.14-6.17) | Fase 8 (8.2, 8.5, 8.6, 8.8-8.18) |
| 10 | Fase 7 (7.1-7.7) | Fase 7 (7.8-7.14) |
| 11 | Fase 9 | Fase 9 |
| 12 | Fase 10 | Fase 10 |
| 13 | Fase 11 | Fase 11 |

---

## Anexo F — Riesgos globales del roadmap

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|-------------|---------|------------|
| G1 | El ítem 3.3 (eliminar 104 statement-expressions) excede el presupuesto y retrasa 1.0 | **Alta** | Alto (bloquea el release) | Desacoplar 3.2 (el error duro) de 3.3 (la limpieza). 3.2 es **obligatorio**; 3.3 puede declararse parcialmente completo con una lista honesta de lo que no cubre, retirando la palabra "gate" de la documentación |
| G2 | El ítem 2.1 (bounds) rompe código de la stdlib o de usuarios | **Media** | Alto | Medir primero cuántos sitios dependen del comportamiento permisivo; si son muchos, elegir la dirección permisiva (retículo) y documentar |
| G3 | El ítem 8.11 (MSVC real) revela incompatibilidades profundas en el runtime y en los headers de terceros | **Alta** | Medio | La salida aceptable es **retirar la afirmación MSVC**; no es aceptable mantener la afirmación con la matriz en MinGW |
| G4 | La Fase 6 (stdlib) crece sin control porque "ya que estamos" se añaden mejoras | Media | Medio | Congelar el alcance de la Fase 6 a los 17 items listados; cualquier feature nueva va a 1.1 |
| G5 | Los fixes de la Fase 1 introducen regresiones en los 2074 tests | Media | Alto | Ejecutar la suite completa tras **cada** item de la Fase 1, no al final; cada fix con su test primero |
| G6 | El refactor de `pengu_project.py` / `pengu_codegen.py` se mezcla con los fixes y se pierde el rastro | **Alta** | Alto | **Prohibido refactorizar antes de cerrar los bloqueantes.** El refactor es 1.1+ (ver `CLEANUP_PLAN.md` §3, nota de secuencia) |
| G7 | La deriva de versiones se reintroduce tras la Fase 7 | Media | Bajo | El test extendido de versión (7.5) es permanente |
| G8 | El periodo de RC (10.9) descubre un bloqueante y hay presión por publicar igualmente | Media | **Muy alto** | Regla explícita en `CONTRIBUTING.md`: un bloqueante abierto retrasa 1.0; la fecha no es un criterio de done |
| G9 | La documentación bilingüe se desincroniza durante las Fases 7 y 10 | **Alta** | Medio | El ítem 7.14 añade un test que compara el número de bloques `pengu` entre los pares de documentos |
| G10 | El corpus de compliance (8.4) se escribe para pasar, no para cubrir | Media | Medio | Cada programa debe corresponder a una sección de `LANGUAGE.md` y usar la feature de esa sección, verificado en revisión |

---

## Anexo G — Definición de "1.0 listo para producción"

Para evitar que "1.0" signifique cosas distintas según quién lo lea, esta es la definición
operativa. **Todas** las condiciones son necesarias.

### G.1 Corrección

- [ ] Los 11 bloqueantes de `AUDIT_1.0.md` §20.1 cerrados, cada uno con un test que falla al revertir.
- [ ] `pengu check <archivo>` y `pengu check` sin entry devuelven rc≠0 ante error.
- [ ] Ninguna entrada de usuario produce un traceback de Python (Anexo C4).
- [ ] `ruff --select F821,E9` limpio.

### G.2 Portabilidad declarada y verificada

- [ ] `--strict-c99` compila y ejecuta los 56 programas de `std` bajo `-std=c99 -pedantic-errors`.
- [ ] gcc, clang y tcc compilan y ejecutan el corpus de compliance.
- [ ] MSVC: **o** verde, **o** sin ninguna afirmación de soporte en la documentación.
- [ ] Cross-compile Linux→Windows produce un `.exe` válido.

### G.3 Honestidad documental

- [ ] 0 afirmaciones refutadas en `RELEASE_CHECKLIST.md`, `BENCHMARKS.md`, `SECURITY.md`.
- [ ] El catálogo de errores se genera del código.
- [ ] CI compila los bloques `pengu` completos de `LANGUAGE.md` → 0 fallos.
- [ ] 0 deriva de versión en los `.md` y docstrings.
- [ ] Cada regla del style guide tiene un test que la verifica.

### G.4 Compatibilidad

- [ ] Corpus de compliance (50 programas) verde.
- [ ] Corpus de migración (cada versión publicada) verde.
- [ ] `pengu migrate` existe y funciona con `--dry-run`.

### G.5 Calidad medida

- [ ] Cobertura medida con umbral no decreciente.
- [ ] Property-based testing activo, incluidas idempotencia y preservación de semántica del formateador.
- [ ] ASan/UBSan/valgrind verdes; leaks conocidos en `xfail(strict=True)`.
- [ ] Fuzzing ≥6 h por harness sin crash (presupuesto real, en shards).

### G.6 Release verificable

- [ ] Descargas verificadas con SHA-256 (externos y TCC).
- [ ] Artefactos reproducibles (mismo hash para el mismo commit).
- [ ] `release-verify.yml` descarga y ejecuta lo publicado.
- [ ] Instalación desde cero verificada en Linux, macOS y Windows.
- [ ] Tag firmado.

### G.7 Lo que 1.0 **no** promete

El anuncio de 1.0 debe declarar explícitamente, citando `AUDIT_1.0.md` §20.6, que **no** incluye:
borrow checking, async/await, closures con captura, macros de AST, dynamic dispatch, reflection,
backtracking de deps, `Result` completo en la stdlib, playground WASM, associated types ni REPL.
Un 1.0 que dice lo que no es vale más que uno que calla.

## Resumen de fases

| Fase | Nombre | Requiere | Duración | Items | Bloqueantes que cierra |
|------|--------|----------|----------|-------|------------------------|
| 0 | Limpieza y consolidación | — | **S** | 10 | — |
| 1 | Cierre residual: correctitud | 0 | **M** | 11 | B1, B2, B3, B6, B7 |
| 2 | Completar 1.0 del lenguaje | 1 | **M** | 12 | (habilita B5, B10) |
| 3 | Completar runtime y ABI | 1 | **L** | 12 | B5, B8 |
| 4 | Completar CLI | 1 | **M** | 16 | B4 |
| 5 | Completar LSP | 1 | **S-M** | 11 | — |
| 6 | Completar stdlib | 1, 2 | **L** | 17 | — |
| 7 | Completar Style Guide y Docs | 2, 4, 6 | **M** | 14 | — |
| 8 | Completar tests | 1 | **L** | 18 | B9, B10 |
| 9 | Herramientas de release | 3, 4 | **M** | 12 | — |
| 10 | Congelación y RC | 1-9 | **M** | 11 | — |
| 11 | 1.0.0 | 10 | **S** | 6 | — |

**Esfuerzo total estimado (un desarrollador):**

| Bloque | Estimación |
|--------|-----------|
| Fase 0 + 1 (bloqueantes de correctitud) | ~1.5 semanas |
| Fases 2 + 3 (lenguaje + runtime) | ~3 semanas |
| Fases 4 + 5 + 6 (CLI + LSP + stdlib) | ~4 semanas |
| Fases 7 + 8 (docs + tests) | ~2.5 semanas |
| Fases 9 + 10 + 11 (release + RC + 1.0) | ~2.5 semanas |
| **Total** | **~13.5 semanas (~3.5 meses)** |

**Camino crítico:** Fase 0 → 1 → 3 (el más largo por causa de 3.3) → 9 → 10 → 11.

**Camino más corto y honesto a 1.0, en una frase:** cerrar los 5 bloqueantes de correctitud y los
5 de portabilidad/verificación (Fases 0, 1, 3 y los items B4/B9/B10 de las Fases 4 y 8), y **retirar
o gatear cada afirmación de la documentación que no se pueda verificar** — porque un 1.0 con 60
comandos y 13 features LSP documentadas con precisión vale más que un 1.0 que promete MSVC,
C99 portable y fuzzing de 72 h sin cumplirlo.

