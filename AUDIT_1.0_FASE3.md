# 🐧 AUDITORÍA 1.0 — FASE 3: RUNTIME Y ABI

> **Alcance:** `ROADMAP_2.0.md` Fase 3, items 3.1–3.12.
> **Punto de partida:** `0.16.0`, commit `403fa45` (Fase 2 cerrada).
> **Reglas aplicadas:** **C1** (todo gate **compila**, **ejecuta** o **mide**; prohibido
> `assert "texto" in bundle`), **C2** (todo fix tiene un test que falla al revertirlo, verificado),
> **C3** (medir antes de decidir), **C4** (runtime y codegen son infraestructura: un cambio por
> familia, un commit por item, suite completa entre items).

---

## §0. Estado de los items

| # | Item | Estado | Evidencia |
|---|------|--------|-----------|
| 3.1 | 🔴 **B8** — el `.c` del runtime compila sin `-Wno-implicit-function-declaration` | ✅ **cerrado** | `tests/test_runtime_c99.py` (9 tests); 24 errores → 0 |
| 3.12 | 🟢 Guardar los `#define` con `#ifndef` | ✅ **cerrado** | 3 warnings `-Wmacro-redefined` → 0 |
| 3.2 | 🔴 **B5** — `--strict-c99` compila C portable con `std` | 🔬 **diagnosticado, no arreglado** | §6: 34/61 fallan; causa raíz localizada |
| 3.3 | 🔴 Eliminar los statement-expressions `({...})` en modo estricto | ⏳ pendiente | — |
| 3.4 | 🟠 `__typeof__` en vez de `__auto_type` para TCC | ⏳ pendiente | — |
| 3.5 | 🟠 **A15** — `PENGU_ABI_VERSION` verificable contra el `.a` | ⏳ pendiente | — |
| 3.6 | 🟠 `SIGFPE`/`SIGILL`/`SIGBUS` + `sigaction` | ⏳ pendiente | — |
| 3.7 | 🟠 Volcado sin `snprintf` **o** retirar la afirmación async-signal-safe | ⏳ pendiente | — |
| 3.8 | 🟡 Instalación atómica del crash handler | ⏳ pendiente | — |
| 3.9 | 🟡 **R3** — unificar el formateo de floats (`%g` vs `%f`) | ⏳ pendiente | — |
| 3.10 | 🟡 Documentar los 55 símbolos sin Doxygen | ⏳ pendiente | — |
| 3.11 | 🟡 `docs/ABI.md` | ⏳ pendiente | — |

---

## §1. Item 3.1 (B8) — el runtime no era C válido

### Medición previa (C3)

Reproducción con el juego de flags exacto del build, antes de tocar nada:

| Configuración | Resultado |
|---|---|
| `[A]` con los dos `-Wno-*` (build actual) | rc=0, 3 warnings, **0 diagnósticos de declaración implícita** |
| `[C]` sin `-Wno-implicit-function-declaration` | rc=1, **24 errores** (`declaración implícita de 'mbedtls_md5'`, …) |
| `[D]` sin ese flag **+** `-DMBEDTLS_ALLOW_PRIVATE_ACCESS` | rc=0, **0 errores** |
| `[E]` **sin ningún** `-Wno-*` **+** el define | rc=0, solo los 3 `-Wmacro-redefined` |

Confirma `AUDIT_1.0.md` §5.1 al pie de la letra, incluidos los 24 errores y el hecho de que
`-Wno-incompatible-pointer-types` era ya innecesario.

### Diagnóstico

`pengu_runtime.c:25-28` usa `mbedtls_md5/sha1/sha256/sha512` de `<mbedtls/private/*.h>`. En mbedtls
4.2.0 esas declaraciones están tras `MBEDTLS_DECLARE_PRIVATE_IDENTIFIERS`, que solo se define cuando
se compila con `MBEDTLS_ALLOW_PRIVATE_ACCESS`. No se definía, y el flag de supresión **ocultaba los
24 errores por completo**: nunca llegaban al log. El hash funcionaba por accidente ABI en x86-64.

### Fix

En `build_runtime.py`, dentro de `build_pengu_runtime` (el **único** sitio que compila el runtime):
se eliminan los dos `-Wno-*` y se añade `-DMBEDTLS_ALLOW_PRIVATE_ACCESS`.

Los otros cinco sitios con `-Wno-*` (`build_libxml2`:271, `build_curl`:435, `build_microhttpd`:520,
`build_raylib`:999, `build_stdlib_c`:1152) compilan **librerías de terceros**, no el runtime, y
quedan **fuera de alcance**. La verificación está acotada a `build_pengu_runtime` a propósito:
aserción sobre el archivo entero sería incorrecta o forzaría churn ajeno al item.

### Verificación

```
$ gcc -std=c11 -Wall -Wextra <flags reales> -DMBEDTLS_ALLOW_PRIVATE_ACCESS \
      -c pengu_parser/pengu_runtime.c -o /tmp/e.o
  errores+warnings: 0
```

Y por la vía real del build:

```
$ build_pengu_runtime(gcc, ar)   # extraído de build_runtime.py
  [EXEC] gcc -O2 -I… -DMBEDTLS_ALLOW_PRIVATE_ACCESS -I/usr/include/libxml2 -c pengu_runtime.c
  [EXEC] ar rcs build/lib/libpengu_runtime.a build/obj_runtime/pengu_runtime.o
  -> OK
```

### C2 — verificado

Revertir el fix (restaurar los dos `-Wno-*` y quitar el define) hace fallar
`test_build_runtime_has_no_suppressions_for_the_runtime`. Medido: **1 failed, 8 passed**.

Además `test_runtime_has_no_implicit_function_declarations` compila con
`-Werror=implicit-function-declaration`, que convierte exactamente la clase que B8 ocultaba en error
duro: sin el define falla con 24 errores.

---

## §2. Item 3.12 — guardas `#ifndef` en los `#define`

### Medición previa

Con los flags reales del build (que pasan `-DPCRE2_STATIC -DLIBXML_STATIC -DCURL_STATICLIB`) se
producían **3 warnings** `-Wmacro-redefined`:

```
pengu_runtime.c:13: warning: se redefine 'PCRE2_STATIC'
pengu_runtime.c:16: warning: se redefine 'LIBXML_STATIC'
pengu_runtime.c:30: warning: se redefine 'CURL_STATICLIB'
```

### Fix

Cada uno de los tres `#define` queda dentro de un `#ifndef`/`#endif`.

### Verificación

| Configuración | errores+warnings |
|---|---|
| Con los `-D` en la línea de órdenes (build real) | **0** |
| **Sin** los `-D` | **0** |

La unidad compila limpia en ambas direcciones, que es lo que hace la guarda: no depende de que el
build pase el define.

### C2 — verificado

Quitar las tres guardas hace fallar **6 tests** (3 parametrizados de `test_static_macros_are_guarded`,
`test_the_three_guarded_macros_are_the_ones_the_build_passes`, y los dos de compilación con
diagnósticos). Medido: **6 failed, 3 passed**.

---

## §3. Correcciones a auditorías previas

De momento **ninguna**: la medición de §1 reproduce `AUDIT_1.0.md` §5.1 al pie de la letra (los 24
errores, el flag innecesario, el define que lo arregla). Se anotará aquí cualquier discrepancia que
aparezca en los items siguientes.

---

## §4. Hallazgos nuevos

- **`-Wno-incompatible-pointer-types` era innecesario desde antes de esta fase.** `AUDIT_1.0.md`
  §5.1 ya lo decía; la reproducción lo confirma: sin él, 0 errores. Se elimina junto al otro.
- **El contador `grep -c "Wno-implicit\|Wno-incompatible" build_runtime.py` no puede llegar a 0** sin
  tocar los builds de terceros. Vale **9** después de este item y los 9 restantes son de
  `build_libxml2`/`build_curl`/`build_microhttpd`/`build_raylib`/`build_stdlib_c`. El criterio de la
  fase debería leerse como "0 en la compilación del **runtime**", que es lo que B8 pedía; se deja
  anotado para que nadie persiga un 0 que exigiría modificar compilaciones ajenas al alcance.

---

## §5. Verificación de la suite

Ejecución completa tras 3.1 + 3.12:

```
2492 passed, 18 skipped, 3 xfailed, 1 failed
```

El único fallo es `tests/test_deps_commands.py::test_add_upgrade_remove_end_to_end`, uno de los
**tests flaky conocidos** (item 1.14, y anotado en `AUDIT_1.0_FASE2.md` §3.5). Comprobado que es el
flake y no una regresión de esta fase:

```
$ pytest tests/test_deps_commands.py::test_add_upgrade_remove_end_to_end   # aislado, 3 veces
  run 1: 1 passed
  run 2: 1 failed
  run 3: 1 passed
```

Pasa y falla **en aislamiento**, sin relación con el runtime: es una prueba de gestión de
dependencias que no compila el runtime ni el codegen. **No se arregla aquí** (es item 1.14, fuera del
alcance de la Fase 3). No empeora: mismo comportamiento que en Fase 2.

Además, verificación funcional del runtime reconstruido: `seal.md5("abc")` sigue dando
`900150983cd24fb0d6963f7d28e17f72`, idéntico a `md5sum`, ahora **sin** el flag que ocultaba los 24
errores de declaración implícita. El hash ya no funciona "por accidente ABI": la unidad es C11 legal.


---

## §6. Item 3.2 (B5) — reproducido y diagnosticado; el fix NO está hecho

> **Estado real: 🔬 reproducido, causa raíz localizada, sin arreglar.** Se documenta así porque
> maquillarlo sería exactamente lo que la regla final de la fase prohíbe.

### Medición (C3)

| Comprobación | Resultado |
|---|---|
| `tests/std_programs/*.pengu` | **61** programas (la fase decía 56) |
| `pengu build --strict-c99` sobre ellos | todos construyen el bundle |
| `gcc -std=c99 -pedantic-errors -c` sobre el bundle | **34 / 61 fallan** |
| Statement-expressions `({...})` en el bundle de `atlas.pengu` | **104** (coincide con la fase) |

Muestra representativa:

| Programa | stmt-exprs | ¿pedantic? |
|---|---|---|
| `atlas.pengu` | 104 | ❌ falla |
| `test_all.pengu` | 85 | ❌ falla |
| **`tally.pengu`** | **0** | ❌ **falla igual** |
| 3 de la muestra | 0 | ✅ pasan |

**El dato clave: `tally.pengu` falla con CERO statement-expressions.** Eso demuestra que B5 tiene
**al menos dos causas independientes**, y confirma la advertencia de la fase de no mezclar 3.2 con
3.3: eliminar los `({...})` (3.3) **no arregla** B5 por sí solo.

### Causa raíz localizada: el hoisting saca el índice fuera del ámbito del bucle

`gcc` señala `'k' undeclared`, `'i' undeclared`, `'r' undeclared` — siempre variables de bucle. En
`std/tally.pengu:851` (`zip_with shard T and U and V`), el bundle estricto genera:

```c
int64_t _p_idx_215 = (int64_t)(k);                       /* <-- k todavía no existe */
pengu_assert_bounds(_p_idx_215, (int64_t)((xs).len), "...:862");
int64_t _p_idx_216 = (int64_t)(k);
pengu_assert_bounds(_p_idx_216, (int64_t)((ys).len), "...:862");
PenguList _comp_list_217 = pengu_list_new(sizeof(int32_t), (idxs).len);
for (int _i = 0; _i < (idxs).len; _i++) {
  int32_t k = (*(int32_t *)pengu_list_at(&(idxs), _i));   /* <-- k se declara AQUÍ */
    int32_t _comp_val_218 = (f(((*(int32_t *)pengu_list_at(&(xs), _p_idx_215))), ...));
```

El mecanismo está en `pengu_codegen.py`:

```python
def _block_expr(self, stmts, value_expr):
    if self.use_gnu_extensions:
        return f"(__extension__(({{\n{body}\n}})))"   # el ámbito del ({...}) cubre k
    for s in stmts:
        self._hoist(s)                                  # <-- pero en estricto sube al prelude
    return value_expr
```

En modo GNU el `({...})` **crea un ámbito donde el índice del bucle es visible**, así que el
`assert_bounds` ve `k`. En modo estricto `_hoist` sube esas sentencias al prelude de la sentencia
**exterior al bucle**, y `k` deja de estar en ámbito. El `#line` lo sitúa en la línea 862, que es
exactamente el `for k in idxs then ...`.

Es decir: **el hoisting es correcto para expresiones cuyo ámbito es el prelude; es incorrecto para
las que dependen de un índice de bucle de comprehensión.** El fix tiene que emitir las expresiones
por-iteración **dentro** del cuerpo del `for`, no en el prelude, y eso toca el codegen de
comprehensiones — infraestructura (regla C4: un cambio por familia, con la suite completa como red).

### Por qué no se arregla en esta ronda

- El diagnóstico requiere tocar el emisor de comprehensiones, no una línea del `_hoist`.
- 34/61 programas afectados: un cambio así necesita iteración medida contra la suite completa
  (~20 min por corrida) y la verificación de que los bundles **ejecutan** con la salida correcta, no
  solo que compilan.
- Arrancar ese cambio con el presupuesto de contexto restante arriesgaría dejar el árbol en un estado
  intermedio peor que el actual, contra `C4` y contra la regla final de la fase.

**Queda como el trabajo principal pendiente de la Fase 3**, con la causa raíz ya localizada (que es
la parte cara del item) y el punto exacto del código señalado.
