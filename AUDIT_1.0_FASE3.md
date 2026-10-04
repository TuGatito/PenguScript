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
| 3.2 | 🔴 **B5** — `--strict-c99` compila C portable con `std` | ⏸️ **DIFERIDO a 1.1** | §6–§7: 34/61 fallan; causa raíz localizada y fix intentado sin converger |
| 3.3 | 🔴 Eliminar los statement-expressions `({...})` en modo estricto | ⏸️ **DIFERIDO a 1.1, con medición** | §14: acoplado a 3.2 (sin el hoisting no compila) y único item XL; 34/61 fallan |
| 3.4 | 🟠 `__typeof__` en vez de `__auto_type` para TCC | ⏸️ **REVERTIDO / DIFERIDO a 1.1** | §9, §11: el fix lograba tcc 61/61 pero **rompió un test de regresión**; revertido en `b22f075` |
| 3.5 | 🟠 **A15** — `PENGU_ABI_VERSION` verificable contra el `.a` | ✅ **cerrado, con matiz** | §14: `nm … \| grep pengu_abi_version` → `T pengu_abi_version`; `tests/test_abi_version.py` (5). La referencia **no** es obligatoria desde cada bundle (rompía `pengu build` en proyectos nuevos); ver §14 |
| 3.6 | 🟠 `SIGFPE`/`SIGILL`/`SIGBUS` + `sigaction` | ✅ **cerrado** | §14: `pengu eval "1/0"` → `[PENGU CRASH] … (signal/code 8)` + traza, exit **136** (antes 248 sin mensaje); `tests/test_crash_signals.py` (6) |
| 3.7 | 🟠 Volcado sin `snprintf` **o** retirar la afirmación async-signal-safe | ✅ **cerrado (implementado, no retirado)** | §14: el handler y `pengu_bounds_panic` formatean a mano y solo usan `write(2)`/`_exit()`; medido sobre el artefacto compilado; `tests/test_crash_dump_async_safe.py` (4) |
| 3.8 | 🟡 Instalación atómica del crash handler | ✅ **cerrado** | §10: `pthread_once`/`InitOnceExecuteOnce`; `frame_push` ya no instala; `tests/test_crash_handler_atomic.py` (6) |
| 3.9 | 🟡 **R3** — unificar el formateo de floats (`%g` vs `%f`) | ✅ **cerrado** | §14: `print`, `to string` e interpolación coinciden; `tests/test_floats_consistency.py` (10) |
| 3.10 | 🟡 Documentar los 55 símbolos sin Doxygen | ⏸️ **DIFERIDO a 1.1, con medición** | §14: cosmético, ninguna afirmación de comportamiento depende de ello; encaja en Fase 7 |
| 3.11 | 🟡 `docs/ABI.md` | ✅ **cerrado** | §14: `docs/ABI.md` (política de bumps + verificación) |
| 3.13 | 🟢 (**nuevo en esta fase**) Evaluar la expresión de retorno antes de retirar el frame | ✅ **cerrado** | §14: el fallo dentro de un `return` se atribuía **al llamador**; corregido |

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


---

## §7. Item 3.2 (B5) — intento de fix y decisión de aplazamiento

### El mapa real (C3), sobre los 61 programas

`tests/std_programs/*.pengu` = **61** programas (la fase decía 56), todos con `import std.`.

| Causa | Programas | Firma del compilador |
|-------|-----------|----------------------|
| Índice hoisteado fuera del bucle que declara su operando | **16** | `'k' undeclared (first use in this function)` |
| Statement-expressions `({...})` en el bundle estricto | **15** | `ISO C forbids braced-groups within expressions` |
| Cualificadores / casts | **3** | `return discards 'const' qualifier`, `ISO C forbids casting nonscalar` |
| **Total que falla** | **34 / 61** | |

Programas que **pasan** hoy: **27 / 61**.

**Confirma el desacoplamiento que pide la fase:** son dos bugs, no uno. Quitar los `({...})`
(item 3.3) no arregla los 16 de `undeclared`, y arreglar el hoisting no quita los 15 de
`braced-groups`. `atlas.pengu` (104 statement-expressions) y `tally.pengu` (0 statement-expressions,
13 `undeclared`) son los dos extremos del mismo mapa.

### Reproducción mínima — 4 líneas

```pengu
weave main into int:
  var xs as list of int is [1, 2, 3]
  var ys as list of int is [4, 5, 6]
  var zs as list of int is for k in xs then ((xs at k) + (ys at k))
  return 0
```

```
$ pengu build --strict-c99 --entry min_b5.pengu -o /tmp/min.c
$ gcc -std=c99 -pedantic-errors -c /tmp/min.c -Ibuild/include
min_b5.pengu:4:30: error: 'k' undeclared (first use in this function)
```

C generado (estricto):

```c
int64_t _p_idx_9 = (int64_t)(k);                    /* k no existe todavía */
pengu_assert_bounds(_p_idx_9, (int64_t)((xs).len), "min_b5.pengu:4");
int64_t _p_idx_10 = (int64_t)(k);
pengu_assert_bounds(_p_idx_10, (int64_t)((ys).len), "min_b5.pengu:4");
PenguList _comp_list_11 = pengu_list_new(sizeof(int32_t), (xs).len);
for (int _i = 0; _i < (xs).len; _i++) {
  int32_t k = (*(int32_t *)pengu_list_at(&(xs), _i));   /* k se declara AQUÍ */
  int32_t _comp_val_12 = (...((xs at _p_idx_9)) + ((ys at _p_idx_10)));
  ...
```

En modo GNU el mismo programa es correcto, porque `__extension__(({...}))` **crea un ámbito que
engloba el bucle**:

```c
PenguList zs = (__extension__({
  PenguList _comp_list_11 = ...;
  for (int _i = 0; ...) {
    int32_t k = ...;
    int32_t _comp_val_12 = (... (__extension__({ __auto_type _p_idx_9 = (k); ...; _p_idx_9; })) ...);
```

**Causa raíz exacta:** `_block_expr` (strict) hace `self._hoist(s)` de cada sentencia, y `_hoist`
empuja a `self.expr_prelude`, que se vuelca **antes de la sentencia envolvente**, no dentro del bucle
de la comprehensión. El cuerpo de la comprehensión se genera *antes* de que exista el `for`, así que
los temporales de índice acaban fuera del ámbito de `k`.

### El fix que se intentó, y por qué no convergió

Se probó la corrección conceptual del `AUDIT §4.1`: **mover las sentencias hoisteaddas al cuerpo del
bucle** en las ramas estrictas del emisor de comprehensiones. Se añadió un helper
`_split_loop_prelude` que separa la *declaración* del temporal (que puede quedar antes del bucle,
porque no necesita `k`) del `pengu_assert_bounds` (que sí lo necesita y debe ir dentro).

**No convergió.** El problema es de orden de emisión, no de forma:

`then_c` ya viene con el nombre `_p_idx_9` incrustado, así que dondequiera que se emita
`pengu_assert_bounds(_p_idx_9, ...)` la declaración `int64_t _p_idx_9 = (int64_t)(k);` tiene que
estar **antes** y el binding de `k` tiene que existir **en ese punto**. Mover sólo la sentencia deja
la declaración fuera; mover ambas deja la declaración dentro del bucle con el `assert` fuera; y
volver a generar `then_c` dentro del bucle exigiría reordenar la construcción del cuerpo, que es lo
que el emisor hace ahora al revés.

Se verificó además que el cambio **no arreglaba el caso mínimo** antes de revertir (el intento
mantenía `_p_idx_9 undeclared` y añadía ruido), así que se revirtió `pengu_codegen.py` a `HEAD` y se
comprobó que el árbol queda limpio y la reproducción mínima vuelve a su línea base de exactamente
1 error.

**Presupuesto:** el fix correcto exige reordenar la emisión del cuerpo de la comprehensión en las seis
ramas estrictas del emisor, con la suite completa (~20 min) y la verificación de que los bundles
**ejecutan** con la misma salida que el modo GNU como red. Es un item **L**, no el **S** que sugería
"AUDIT §4.1 Fix propuesto".

### Decisión: ⏸️ DIFERIDO a 1.1

Aplicando la regla final de la fase: **no se maquilla**. Se marca 3.2 como ⏸️ diferido con la
medición completa (arriba) y se corrigen los tres documentos que afirmaban que `--strict-c99` era un
gate de portabilidad:

| Documento | Antes | Después |
|-----------|-------|---------|
| `RELEASE_CHECKLIST.md:17` | "C99 portability gate (`--strict-c99`) and ABI layout matrix" | "❌ **NO USAR** `--strict-c99` como gate … no es funcional para programas que importan `std` en 0.16.0", con la medición |
| `LANGUAGE.md` (`--strict-c99`) | "compiles with `-std=c99 -pedantic-errors`" | `[!WARNING]` con la tabla de causas y la reproducción mínima. La afirmación era falsa |
| `AUDIT_1.0.md` §20.1 fila B5 | "→ 0 errores" | "⏸️ **NO CERRADO — DIFERIDO a 1.1**" con la medición |
| `AUDIT_1.0.md` §5.1 | (B8, sin marcar) | ✅ cerrado en Fase 3 item 3.1, commit `c3c6aed` |

**Nota sobre la etiqueta B5:** `AUDIT_1.0.md` la usa **dos veces** con significados distintos: en §1
para "tipos cualificados pierden campos" (cerrado en Fase 1 como B6/B7) y en §20.1 para
"`--strict-c99`". Sólo la segunda es este item. Se anotan por separado para que no se confundan.

### Consecuencia para la Fase 3 y para B10

- **3.2 queda ⏸️**, y con él el criterio #2 de "done" de la fase (`-pedantic-errors` → 0 errores).
- **B10 (Fase 8) sigue bloqueado**: su gate `tests/test_cli_strict_c99.py` no puede pasar mientras
  `--strict-c99` no compile. Reescribirlo "para que compile de verdad" lo pondría en rojo.
- **3.3 (los 104 statement-expressions) sigue siendo un item separado** y no se toca aquí, como pide
  el desacoplamiento.

---

## §8. Verificación de las afirmaciones documentadas

Toda cifra publicada en `LANGUAGE.md`, `RELEASE_CHECKLIST.md`, `CHANGELOG.md` y este documento se
reprodujo **después** de escribirla, con el árbol en `HEAD` y `pengu_codegen.py` sin tocar:

| Afirmación | Comando de verificación | Resultado |
|---|---|---|
| 61 programas en `tests/std_programs/` | `ls tests/std_programs/*.pengu \| wc -l` | **61** ✓ |
| 27 pasan `-pedantic-errors` | barrido completo | **27** ✓ |
| 34 fallan | barrido completo | **34** ✓ |
| La reproducción de 4 líneas falla con `'k' undeclared` | `pengu build --strict-c99` + `gcc -std=c99 -pedantic-errors` | `min_b5.pengu:4:30: error: 'k' undeclared` ✓ |
| `RELEASE_CHECKLIST.md` ya no lo llama gate | `grep -c "NO USAR"` | **1** ✓ |
| `LANGUAGE.md` ya no afirma que compila | `grep -c "not functional"` | **1** ✓ |
| El runtime compila como C11 legal sin supresiones | `tests/test_runtime_c99.py` (9 tests) | **9 passed** ✓ |

### Estado de la suite

```
2493 passed, 18 skipped, 2 xfailed, 1 xpassed, 0 failed
```

El `xpassed` es el test del leak inestable ya documentado en `AUDIT_1.0_FASE2.md` §3.5 (pasa y falla
sin cambios de por medio); no es una regresión de esta fase. No apareció el otro flaky conocido
(`test_deps_commands`) en esta ejecución.

### Estado del árbol

`pengu_codegen.py` está **en `HEAD`**, verificado con `git diff --quiet`: el intento de fix del
hoisting se revirtió por completo y no dejó residuo. El único cambio de código de la fase es el de
3.1/3.12 (`pengu_parser/pengu_runtime.c`, `build_runtime.py`), más los tests y la documentación.


---

## §9. Item 3.4 — `__auto_type` impedía a tcc compilar (cerrado)

### Medición previa (C3)

| Comprobación | Resultado |
|---|---|
| `tcc` en el PATH | no; el que usa el proyecto es el **empaquetado** en `build/tcc-dist/tcc-dist/bin/tcc` (v0.9.28rc) |
| `tcc -c <bundle de test_atlas.pengu>` | ❌ `error: '__auto_type' undeclared` |
| Programas de `tests/std_programs/` cuyo bundle **contiene** `__auto_type` | **46 / 61** |
| Programas cuyo bundle **tcc rechaza** | **46 / 61** (exactamente los mismos) |

`__auto_type` es una extensión de GCC/Clang que tcc no implementa. Como el proyecto usa tcc como
compilador de desarrollo, cada bundle afectado disparaba el camino de repliegue y `pengu run`
imprimía `development compiler failed; retrying with gcc`.

### Fix

`__auto_type X = (EXPR);` → `__typeof__(EXPR) X = (EXPR);`. En las 10 construcciones dentro de
*statement expressions* el inicializador está disponible, así que `__typeof__` —que **tanto gcc como
tcc** soportan— da el mismo tipo.

Sitios convertidos: `_emit_bounds_check` (`:1074`), el hoist `const` (`:4576`), los dos de
`maybe is present` (`:9343`, `:9353`), los cinco de comprobaciones de rango/colección
(`:7269`, `:7271`, `:7333`, `:7355`, `:7382`) y `:813`.

**Quedan 6 sitios** (`:813`, `:3221`, `:6886`, `:9112`, `:9269`, `:9326`) donde `__auto_type` es el
*fallback* para un tipo que la inferencia no pudo determinar (`AnyType`). **Medido: no se disparan en
ninguno de los 61 programas** — el bundle de `test_atlas` contiene **0** `__auto_type` tras el fix y
los 61 compilan. Se dejan como están: convertirlos requeriría elegir un tipo concreto para un caso
que el corpus no ejercita, y esa decisión no tiene medición que la respalde.

### Verificación

| Comprobación | Antes | Después |
|---|---|---|
| `tcc -c` sobre los 61 bundles | 15 ok / **46 fail** | **61 ok / 0 fail** |
| `__auto_type` en el bundle de `test_atlas` | 42 | **0** |
| `pengu run` con `import std.spark` | imprime el repliegue a gcc | **sin mensaje de repliegue** |
| `gcc -std=c11 -Wall -Wextra -fsyntax-only` sobre el bundle de atlas | 0 | **0** (sin regresión) |

El corpus completo bajo tcc es el test duro: cualquier regresión en codegen que reintroduzca
`__auto_type` lo hace fallar.

### C2 — verificado

Revierte `pengu_codegen.py` a `HEAD` (`git checkout --`):

```
FAILED tests/test_tcc_portability.py::test_tcc_compiles_the_bundle[test_cipher.pengu]
FAILED tests/test_tcc_portability.py::test_tcc_compiles_the_bundle[test_archivum.pengu]
FAILED tests/test_tcc_portability.py::test_tcc_compiles_the_bundle[test_tally.pengu]
FAILED tests/test_tcc_portability.py::test_tcc_compiles_the_bundle[test_atlas.pengu]
FAILED tests/test_tcc_portability.py::test_no_bundle_in_the_corpus_contains_gcc_only_auto_type
3 failed, 4 passed     (en la primera parametrización; con la definitiva, 5 failed)
```

### Hallazgo de método: un parámetro de test vacuo

La primera versión parametrizaba con `test_spark.pengu`. **Con el fix revertido, ese caso pasaba**:
su bundle no contiene ni un solo `__auto_type`. Era un parámetro que no podía fallar. Se midió la
emisión real por programa con el fix revertido (`cipher` 96, `archivum` 63, `tally` 59, `atlas` 42,
**`spark` 0**) y se sustituyó. Queda anotado en el propio test para que nadie lo revierta a
`spark` creyendo que da igual.


---

## §10. Item 3.8 — instalación atómica del crash handler (cerrado)

### Medición previa (C3)

`pengu_runtime.h` instalaba el handler así:

```c
static volatile int g_pengu_handler_installed = 0;

static inline void pengu_install_crash_handler(void)
{
  if (!g_pengu_handler_installed) {          /* <-- check */
    g_pengu_handler_installed = 1;           /* <-- set   */
    signal(SIGSEGV, ...); signal(SIGABRT, ...);
  }
}
```

Dos defectos:

1. **Carrera de datos.** `check` y `set` no son atómicos entre hilos: dos hilos pueden observar `0`
   y **ambos** ejecutar la instalación. `volatile` no ordena nada entre hilos; no es un primitivo de
   sincronización.
2. **Estaba en el camino caliente.** `pengu_frame_push()` llamaba al instalador **en cada empujón de
   frame**. Un bundle pequeño contiene cientos de `pengu_frame_push`, así que la comprobación se
   ejecutaba en el camino caliente sin aportar nada.

### Fix

- **`pthread_once`** en POSIX y **`InitOnceExecuteOnce`** en Windows sustituyen al flag. El cuerpo de
  la instalación se separó a `pengu_install_crash_handler_body()`, que es lo único que el
  once-primitivo ejecuta, y `pengu_install_crash_handler()` pasa a ser una entrada idempotente y
  thread-safe.
- **El instalador se llama una vez al arranque**, desde el `main` generado por `pengu_codegen`
  (justo después de `pengu_init`), y **se eliminó la llamada de `pengu_frame_push`**. Como el
  instalador ya no se alcanzaba desde ningún otro sitio del bundle, sin este traslado el handler
  nunca se habría instalado — el test `test_installed_handler_is_present_at_process_start` lo fija.

### Verificación

| Comprobación | Resultado |
|---|---|
| `gcc -std=c11 -Wall -Wextra -Werror -fsyntax-only pengu_runtime.h` | **0** (el header sigue siendo el artefacto más disciplinado) |
| `pengu_install_crash_handler()` en el bundle | **1** (antes: 0 — se alcanzaba solo por `frame_push`) |
| `pengu_frame_push` llama al instalador | **no** |
| `pengu_frame_push` como callable en el bundle | 2 (declaración + definición), **0 usos** |
| Programa con acceso fuera de rango | sigue imprimiendo `[PENGU CRASH] … Stack trace` ✓ |
| `pengu run` con `std.spark` | ejecuta y escribe la salida ✓ |

### C2 — verificado

Revirtiendo `pengu_runtime.h` y `pengu_codegen.py` a `HEAD`:

```
FAILED test_frame_push_does_not_install_the_handler
FAILED test_the_install_uses_a_once_primitive
FAILED test_installed_handler_is_present_at_process_start
3 failed, 3 passed
```

### Hallazgo colateral (no arreglado aquí)

`pengu_frame_push` resulta **no tener ningún uso** en los bundles generados: hay cientos de
**llamadas** en el código que revisé antes, pero el bundle de `tccrun.pengu` muestra 0 usos. Es decir,
el volcado de frames de PenguScript probablemente nunca se puebla, y el mensaje de crash sale con la
traza vacía. **No se investiga en esta fase** (sería un item propio); se anota porque afecta a la
calidad del diagnóstico de 3.6/3.7 y conviene medirlo antes de dar por bueno el volcado.


---

## §11. Item 3.4 — el fix funcionaba para tcc pero rompía una regresión: REVERTIDO

### Lo que sí conseguía

El cambio `__auto_type X = (EXPR)` → `__typeof__(EXPR) X = (EXPR)` **eliminaba los 46 fallos de tcc**:
61/61 bundles compilaban con tcc (antes 15/61), 0 `__auto_type` en el bundle de `test_atlas`, y
`pengu run` dejaba de imprimir el repliegue a gcc. `gcc -Wall -Wextra` seguía con 0 diagnósticos.

### Por qué se revirtió

Al correr la suite completa tras 3.4 + 3.8 aparecieron **9 fallos**. Aislados uno a uno contra el
commit base `403fa45` (con un `git worktree` limpio):

> **❌ CORRECCIÓN (ver §13).** La primera versión de esta tabla clasificaba cuatro de estos tests
> como "preexistentes". **Era falso**: los cuatro **pasan** en cuanto 3.4 se revierte por completo.
> El error de diagnóstico está corregido en §13; la tabla se conserva tachada abajo sólo para dejar
> constancia de cómo se llegó a la conclusión equivocada.

| Test | Con 3.4 aplicado | Tras revertir 3.4 | Veredicto |
|---|---|---|---|
| `test_p2_review_fixes.py::test_chained_set_index_through_ref_to_array` | falla | **pasa** | REGRESIÓN de 3.4 |
| `test_regression_0_13_11.py::test_c2_destructure_array` | falla | **pasa** | REGRESIÓN de 3.4 |
| `test_regression_0_13_11.py::test_m7_ref_to_slice_indexing` | falla | **pasa** | REGRESIÓN de 3.4 |
| `test_regression_0_13_13.py::test_h4_in_array_of_string_and_struct` | falla | **pasa** | REGRESIÓN de 3.4 |
| `test_regression_0_13_14.py::test_9_fntype_destructuring_valid_c` | falla | **pasa** | REGRESIÓN de 3.4 |

**Los cinco eran regresiones de 3.4**, no una. El diagnóstico inicial infravaloró el daño del
cambio, y la causa está explicada en §13.

La causa es que **`__typeof__` no es un simple cambio de nombre**: a diferencia de `__auto_type`,
`__typeof__(EXPR)` **conserva el tipo exacto de la expresión, incluidos los cualificadores de nivel
superior**, mientras que `__auto_type` aplica la conversión de lvalue. En
`set r at 0 at 1 is 42` el índice hoisteado pasó a producir un `__typeof__(1)` y el objetivo de la
asignación dejó de ser `r[0][1] = 42` como esperaba el test de regresión de P0 #3.

### Verificación de la reversion

Restaurando `pengu_codegen.py` al estado base (`403fa45`) **más** el cambio de 3.8 (el
startup-install, que es independiente):

```
pytest <los 5 tests> -> 5 passed
```

### Estado

**⏸️ DIFERIDO a 1.1.** El subconjunto de 3.4 que sí es seguro es el que **no cambia la forma del
código generado** — es decir, los sitios donde el temporal se usa sólo como valor y nunca como
objetivo de asignación. Identificarlos exige un barrido por sitio con la suite como red, que es
exactamente el trabajo que la fase marca como **L** y que este presupuesto no cubre.

**Lo que NO se hace:** dejar el cambio aplicado "porque mejora tcc" con una regresión conocida. La
regla final de la fase lo prohíbe explícitamente: un ✅ falso es peor que un ⏸️ honesto.

### Hallazgo de método (segundo de la fase)

El test `test_tcc_portability.py` que escribí para 3.4 pasaba **con y sin** la reversion porque
comprobaba una propiedad distinta de la que rompí: tcc compila, pero el *objetivo de asignación*
cambió de forma. Un test que sólo mira "compila" no detecta "genera otra cosa". La suite completa sí
lo detectó, y es la lección: **el criterio "compila" es necesario pero no suficiente**, exactamente
como advertía el enunciado de la fase para este tipo de cambio.


---

## §12. Verificación tras la reversión de 3.4

```
2499 passed, 18 skipped, 3 xfailed, 0 failed
```

**0 fallos.** Los 4 tests de `test_regression_0_13_1*` que fallaban con 3.4 aplicado vuelven a
fallar igual que en el commit base —es decir, son **preexistentes**— y la regresión que 3.4
introdujo (`test_p2_review_fixes.py::test_chained_set_index_through_ref_to_array`) queda resuelta.

Estado del árbol: limpio. `pengu_codegen.py` = base `403fa45` + el `startup-install` de 3.8
(`__auto_type` 16, `pengu_install_crash_handler()` 1).

### Estado real de los 12 items de la Fase 3 tras esta sesión

| Grupo | Items | Estado |
|---|---|---|
| A | 3.1 (B8), 3.12 | ✅ cerrados (sesión anterior) |
| A | 3.4 | ⏸️ revertido y diferido, con la medición y la causa del conflicto |
| A | 3.8 | ✅ cerrado en esta sesión (`9b686c1`) |
| A | 3.9 | ⏳ pendiente |
| B | 3.5, 3.11 | ⏳ pendientes |
| C | 3.6, 3.7 | ⏳ pendientes |
| D | 3.10 | ⏳ pendiente |
| E | 3.3 | ⏳ pendiente |
| — | 3.2 (B5) | ⏸️ diferido (sesión anterior) |

**Cerrados: 3/12. Diferidos con medición: 2/12 (3.2, 3.4). Pendientes: 7/12.**

### Hallazgo transversal que afectaba a 3.6 y 3.7 — **medido y refutado**

Anoté aquí que `pengu_frame_push` parecía **no tener ningún uso** en los bundles generados, y que si
eso se confirmaba la traza nunca se poblaría y 3.6/3.7 valdrían mucho menos de lo que sugiere su
criterio de "done".

**La medición (§14) refuta la hipótesis.** El codegen emite un `pengu_frame_push` por cada `weave` —
tres en un programa de tres funciones, cuatro en uno de cuatro — y el volcado se puebla con
`file:line` reales (`at inner_fn (nest.pengu:1)`). La suposición venía de contar sólo las menciones
en `pengu_runtime.h`/`pengu_runtime.c`; los puntos de emisión están en `pengu_codegen.py:2254`,
`:4041` y `:9690`. Con la traza poblada, 3.6 y 3.7 se hicieron **completos**, no la versión barata.

### Lección de método (segunda de la fase, ver §11)

Un test que sólo comprueba "esto compila" **no detecta** "esto genera otra cosa". El
`test_tcc_portability.py` que escribí para 3.4 pasaba con el fix aplicado **y** revertido, porque
comprobaba compilación y el cambio rompía la **forma del objetivo de asignación**. Lo detectó la
suite completa, no mi test. Para cambios en codegen, la red tiene que incluir los tests de
regresión que inspeccionan el C generado, no sólo los que lo compilan.


---

## §13. Corrección: los fallos NO eran preexistentes; los cinco eran regresiones de 3.4

### Qué dije y por qué estaba mal

En §11 afirmé que, de los tests que fallaban con 3.4 aplicado, **uno era regresión y cuatro eran
preexistentes**. Esa clasificación se apoyaba en haber corrido los tests en un `git worktree` sobre
`403fa45` y verlos fallar allí también.

**Era un error de método.** Los tests importan el paquete desde **el árbol de trabajo principal**, y
`pengu_runtime.h` seguía roto por 3.4 en ese árbol. Así que el "base" que creí medir no era el base:
el worktree aportaba los tests viejos pero el código compilado venía del árbol con 3.4 aplicado. Los
cuatro "preexistentes" eran, en realidad, **el mismo daño de 3.4 visto desde otro fichero de tests**.

### La medición correcta

Tras revertir 3.4 **por completo** (`17ca127`), en el árbol limpio:

| Comprobación | Resultado |
|---|---|
| Los 5 tests del grupo que fallaba | **5 passed** |
| `tests/test_compiler_core.py::TestCodegenEmissionArraysSlices` | **9 passed** |
| Los 4 de `test_regression_0_13_1*` | **4 passed** |
| **Suite completa** | **2499 passed, 18 skipped, 3 xfailed, 0 failed** |

Los **14** fallos que el barrido capturó con 3.4 aplicado (5 de `test_regression_0_13_1*`, 4 de
`test_compiler_core`/`test_p0_review_fixes`, 5 de `test_tcc_portability`) **desaparecen todos** al
revertir. No había ni un fallo preexistente.

### Por qué importa registrarlo

Una tabla que llama "preexistente" a un daño propio es exactamente el patrón "verde sobre roto" que
esta fase existe para eliminar: traslada al proyecto un fallo que introdujo el cambio. La conclusión
práctica **no cambia** —3.4 se revierte igual, y por la razón correcta (rompía tests)— pero el
registro sí: el daño de 3.4 era **cinco veces mayor** de lo que dije, y eso refuerza la decisión de
revertir en vez de matizarla.

### Lección de método (tercera de la fase)

**Un `git worktree` no aísla el entorno de compilación.** Para comparar dos versiones de código que
genera C, hay que aislar *también* el `pengu_runtime.h` y el `.a` que se usan al compilar, o la
comparación mide una mezcla. Los tres hallazgos de método de esta fase comparten la misma raíz:
**verificar que el experimento mide lo que uno cree que mide** antes de sacar conclusiones de él.


---

## §14. Cierre real de la Fase 3: medición, triaje y resultado

Esta sección cierra la fase con **una medición previa (C3)** que decide dos items, el triaje
explícito de los siete pendientes, y la verificación final.

### §14.1 Medición previa (C3): ¿se puebla la traza de frames?

La duda de §12 era si `pengu_frame_push` se emite en los bundles. Comandos y salida cruda
(evidencia completa en `/tmp/frame_push_evidence.txt`, no versionada):

```bash
$ pengu build --entry /tmp/crash.pengu -o /tmp/crash.c      # 1 weave
$ grep -c 'pengu_frame_push'  /tmp/crash.c   # 2  (definición en el header + 1 uso)
$ grep -c 'pengu_frame_push(' /tmp/crash.c   # 1
  34:  pengu_frame_push("pengu_main", "crash.pengu", 1);

$ pengu run /tmp/crash.pengu
[PENGU CRASH] fatal signal (signal/code 11)
Stack trace (most recent call first):
  at pengu_main (../crash.pengu:1)

$ # programa de 4 weaves (/tmp/deep.pengu)
push sites: 4
  at inner_fn (../deep.pengu:1)          # ← 1 frame con `return calling f`
```

| Resultado | Conclusión | Acción tomada |
|---|---|---|
| `pengu_frame_push` se emite **una vez por `weave`** (3 en un programa de 3, 4 en uno de 4) y el volcado muestra `file:line` reales | **La traza SÍ se puebla** | **3.6 → implementar (M)**; **3.7 → implementar completo (M)** |

La hipótesis de §12 (traza vacía) queda **refutada**. El punto de emisión está en
`pengu_codegen.py:2254`, `:4041` y `:9690`, no en `pengu_runtime.*`, que es donde yo había mirado.

### §14.2 Hallazgo nuevo (3.13): la traza atribuía el fallo al llamador

La medición anterior destapó un defecto más grave que un truncado: el codegen emitía
`pengu_frame_pop(); return <expr>;`, es decir retiraba el frame **antes** de evaluar la expresión de
retorno.

```c
/* antes */                          /* después (3.13) */
pengu_frame_pop();                   int32_t _ret_1 = (a / b);
return (a / b);                      pengu_frame_pop();
                                     return _ret_1;
```

```bash
# `weave divide` con `return a / b` y b == 0, ANTES:
$ pengu run div3.pengu
[PENGU CRASH] fatal signal (signal/code 8)
  at pengu_main (../div3.pengu:6)     # ← el LLAMADOR, no `divide`

# DESPUÉS:
  at divide    (div3.pengu:1)         # ← el weave donde está el fallo
  at pengu_main (div3.pengu:6)
```

Además, una cadena `return calling f` producía **un solo frame**; ahora produce la pila completa.
Esto es lo que hace verdadera la afirmación "escribe la pila de llamadas exacta" de `LANGUAGE.md`.
C2: revertir el `return_stmt` de `pengu_codegen.py` hace fallar
`test_the_call_chain_is_reported_when_the_call_is_a_statement`.

**Coste real, y por qué se documenta aquí:** el cambio rompió 7 tests que fijaban la *forma textual*
del `return` (`assert 'return X;' in bundle`), no su comportamiento. Se actualizaron preservando su
intención (el valor devuelto se sigue comprobando, ahora a través del temporal). Es exactamente el
patrón que la regla C1 desaconseja, y quedó registrado al hacerlo.

### §14.3 El matiz de 3.5: por qué NO se emite una referencia obligatoria

Implementé 3.5 como pedía el plan (referencia `extern` en cada bundle) y **rompió `pengu build` en
todo proyecto nuevo**:

```
$ pengu init ok && cd ok && pengu build
/usr/bin/ld: build/bundle.c:6:(.data.rel.ro+0x0): referencia a `pengu_abi_version' sin definir
```

Causa medida: el CLI sólo añade `-lpengu_runtime` cuando `pengu.toml` lo pide
(`pengu_project.py:380-388`). Un proyecto recién creado no lo pide y compila **header-only**, sin
archivo `.a` alguno. Hacer la referencia obligatoria exige que el CLI enlace siempre el runtime:
**Fase 4** (`pengu_project.py`, prohibido en esta fase por §8 del encargo).

Decisión: se mantiene el símbolo exportado y verificable (`nm` → `T pengu_abi_version`, que es el
criterio de "done" de 3.5), se conserva el `_Static_assert` codegen-vs-header, y `SECURITY.md` +
`docs/ABI.md` dicen **exactamente** qué se garantiza y qué no. `test_bundle_links_without_the_runtime_archive`
fija la restricción para que el error no vuelva en silencio (C2 de la reversión).

### §14.4 Triaje final

| Grupo | Items | Estado |
|---|---|---|
| ✅ **Cerrados** | 3.1, 3.5, 3.6, 3.7, 3.8, 3.9, 3.11, 3.12, **3.13** (9) | con test que falla al revertir (C2) |
| ⏸️ **Diferidos con medición** | 3.2, 3.3, 3.4, 3.10 (4) | §6–§7 (3.2, 3.3), §9/§11 (3.4), §14.5 (3.10) |

Los cuatro diferidos tienen número, no excusa:

- **3.2 / 3.3** — 34 de 61 programas de `tests/std_programs/` fallan
  `gcc -std=c99 -pedantic-errors` por tres causas independientes (§7). 3.3 está acoplado: quitar
  `({...})` sin arreglar antes el hoisting **no compila**. Único item **XL**.
- **3.4** — el fix lograba tcc 61/61 pero rompía 5 tests; revertido (§9, §11) y confirmado en §13.
- **3.10** — 55 símbolos sin Doxygen: cosmético, sin ningún gate de comportamiento colgando de él.

### §14.5 Verificación de la suite

```
$ pytest tests/ -q -p no:randomly
2524 passed, 18 skipped, 2 xfailed, 1 xpassed in 1322.17s (0:22:02)
```

Comparación con el cierre de la Fase 2 (`2499 passed, 18 skipped, 3 xfailed, 0 failed`):

| Métrica | Fase 2 | Ahora | Δ | Explicación |
|---|---|---|---|---|
| **passed** | 2499 | **2524** | **+25** | los tests de regresión nuevos: `test_abi_version.py` (5), `test_floats_consistency.py` (10), `test_crash_dump_async_safe.py` (4), `test_crash_signals.py` (6) = 25 |
| skipped | 18 | 18 | 0 | — |
| **failed** | 0 | **0** | 0 | — |
| xfailed | 3 | 2 | −1 | **no es una mejora**: ver abajo |
| xpassed | 0 | 1 | +1 | **no es una mejora**: ver abajo |

El `+25` cuadra exactamente con los 25 tests añadidos, así que no se ha perdido ni
desactivado ningún test existente para llegar al verde.

#### El `xpassed` es un *flake* preexistente, **no** un fix — no se reclama

`tests/test_string_composition_suite.py::test_string_composition_no_memory_leaks[leak_binary_interp]`
(detección de fugas vía `LD_PRELOAD`, `tests/leakcheck.c`) **no es determinista**. Medición,
6 corridas del mismo test en el mismo árbol:

```
con los cambios de esta sesión:  xpass, xfail, xpass, xfail, xfail, xpass   (3/6 xpass)
con el código de HEAD (git stash): xfail, xpass, xfail, xfail, xfail, xfail (1/6 xpass)
```

El `1 xpassed` de la corrida completa es, por tanto, **ruido de un test flaky que ya
existía** antes de esta sesión — aparece también con el código de HEAD, sin ninguno de mis
cambios. **No se reclama como consecuencia de 3.6/3.7/3.9/3.13.** Merece su propio item (la
detección de fugas tiene una carrera); no se ha tocado aquí.

### §14.6 Los 6 criterios de "Fase 3 suficientemente cerrada"

| # | Criterio | Estado |
|---|---|---|
| 1 | `nm build/lib/libpengu_runtime.a \| grep pengu_abi_version` → 1 símbolo | ✅ `T pengu_abi_version` |
| 2 | `docs/ABI.md` define la política de bumps | ✅ existe, con la sección "What is *not* enforced (yet)" |
| 3 | `(3.14 to string) == "{3.14}"`, también con `1e300`, `-0.0` | ✅ 10 casos (`float` y `f64`), incluido `1e300` |
| 4 | `pengu eval "1/0"` imprime mensaje y sale 136, **o** los docs ya no dicen "async-signal-safe" | ✅ ambas: imprime `[PENGU CRASH] … (signal/code 8)` y sale **136**; y los docs lo dicen ahora **con razón** |
| 5 | `pengu run crash.pengu` da traza con `file.pengu:line`, **o** `pengu_frame_push` documentado como no-op con medición | ✅ traza real con `file:line`; `pengu_frame_push` **no** es no-op (§14.1) |
| 6 | Suite completa en verde, 0 fallos | ✅ `2524 passed, 18 skipped, 2 xfailed, 1 xpassed, **0 failed**`. El `+25` son los tests nuevos; el `1 xpassed` es un flake preexistente que **no** se reclama (§14.5) |

