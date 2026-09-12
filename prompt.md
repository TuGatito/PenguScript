# Prompt de reparación — Cierre de Fase 2 antes de Async/Await

## 0. Contexto

Se auditó la implementación de Fase 2 (scope-owned locals / auto-banish) contra el `prompt.md` original. La implementación pasa 27/27 tests de Fase 2, 867/869 del suite completo y 26/26 de `pengu check tests/std_programs/`. Sin embargo, quedan **tres defectos**:

1. **Bug crítico (bloqueante)**: la rama `or_block` en codegen no abre/cierra un scope de auto-banish, generando C inválido (variable `s` declarada dentro de un `if` y baneada fuera).
2. **Deuda cosmética**: `BorrowedEscapeError` (E0049) está definido y documentado pero nunca se eleva.
3. **Deuda conocida**: `or_block` en posición de expresión que no sea initializer de `var`/`let` produce C silenciosamente incorrecto.

**Objetivo:** cerrar (1) con código y test, resolver (2) por eliminación o implementación, y documentar (3) como known-issue para Phase 3. **No tocar ninguna otra cosa.** No refactorizar `auto_banish_stack`, no cambiar la semántica de Fase 2, no añadir features.

---

## 1. Fix 1 — Scope de auto-banish en `or_block` (CRÍTICO)

### 1.1 Archivo

`pengu_parser/pengu_codegen.py`

### 1.2 Ubicación exacta

Método `_translate_stmt`, rama `var_decl`, bloque `if isinstance(expr_node, Tree) and expr_node.data == "or_block":`.

Actualmente el código (líneas ~940–960 del archivo, buscar por `block_stmts = expr_node.children[1:]`) es:

```python
if isinstance(expr_node, Tree) and expr_node.data == "or_block":
    left_op = expr_node.children[0]
    block_stmts = expr_node.children[1:]
    tmp_res = self.get_temp_name("_res")
    left_c = self._translate_expr(left_op)
    self.local_vars["error"] = STRING_TYPE
    self.indent_level += 1
    inner_body = [self._translate_stmt(bs) for bs in block_stmts]
    self.indent_level -= 1
    block_c = "\n".join(inner_body)
    return (
        f"{ind}PenguResult {tmp_res} = {left_c};\n"
        f"{ind}if (!pengu_result_is_ok(&{tmp_res})) {{\n"
        f"{ind}  PenguString error = pengu_string_from_cstr({tmp_res}.err_val ? {tmp_res}.err_val : \"error\");\n"
        f"{block_c}\n"
        f"{ind}}}\n"
        f"{ind}{t_str} {name} = ({t_str})({tmp_res}.ok_val);"
    )
```

**El mismo patrón aparece en la rama `let_decl`** (buscar por el segundo `block_stmts = expr_node.children[1:]`) — hay que arreglar **las dos**.

### 1.3 Cambio exacto

Envolver la traducción de `block_stmts` con push/pop de la pila `auto_banish_stack` y emitir el flush **antes** del cierre de la llave del `if (!ok) {`:

```python
if isinstance(expr_node, Tree) and expr_node.data == "or_block":
    left_op = expr_node.children[0]
    block_stmts = expr_node.children[1:]
    tmp_res = self.get_temp_name("_res")
    left_c = self._translate_expr(left_op)
    prev_error_t = self.local_vars.get("error")
    self.local_vars["error"] = STRING_TYPE
    self._auto_banish_push("block")
    try:
        self.indent_level += 1
        inner_body = [self._translate_stmt(bs) for bs in block_stmts]
        self.indent_level -= 1
    finally:
        banish = self._flush_current_scope_banish()
        if self.auto_banish_stack and self.auto_banish_stack[-1][0] == "block":
            self.auto_banish_stack.pop()
        if prev_error_t is None:
            self.local_vars.pop("error", None)
        else:
            self.local_vars["error"] = prev_error_t
    block_c = "\n".join(inner_body + banish)
    return (
        f"{ind}PenguResult {tmp_res} = {left_c};\n"
        f"{ind}if (!pengu_result_is_ok(&{tmp_res})) {{\n"
        f"{ind}  PenguString error = pengu_string_from_cstr({tmp_res}.err_val ? {tmp_res}.err_val : \"error\");\n"
        f"{block_c}\n"
        f"{ind}}}\n"
        f"{ind}{t_str} {name} = ({t_str})({tmp_res}.ok_val);"
    )
```

**Notas importantes:**

- El `flush` debe ir **dentro** del `try/finally` para que se ejecute incluso si `_translate_stmt` lanza una excepción — de lo contrario la pila queda corrupta.
- El `pop` de la pila ocurre **después** del flush (el flush consume las entradas del tope, pero no saca el marcador; el `pop` saca el marcador).
- Guardar/restaurar `prev_error_t` es importante para no filtrar `error` al scope padre (pre-existente, pero se aprovecha el cambio para corregirlo). Si prefieres no tocar esto, elimina las 4 líneas relacionadas con `prev_error_t` — **no es parte del bug crítico**.
- **No** cambiar el nombre `"block"` por `"or"` ni añadir categorías nuevas: el sistema de marcadores por identidad de posición no lo necesita.

### 1.4 Test obligatorio

Añadir a `tests/test_phase2_ownership.py` (al final, antes del cierre):

```python
def test_or_block_creates_own_auto_banish_scope():
    """Regresión: `or:` block bodies must auto-banish their own locals
    at the closing brace of the error-handler, not at the outer scope.
    Before the fix, the generated C contained a `pengu_banish_string(&s)`
    after the block where `s` was already out of scope."""
    c = gen_bundle(
        'weave may_fail into maybe int:\n'
        '  return some 1\n'
        'weave f into void:\n'
        '  var r is calling may_fail or:\n'
        '    var s is "a" + "b"\n'
        '    calling print with s\n'
        '  return\n'
    )
    # 's' se declara dentro del if (!ok) y debe liberarse dentro también.
    # Debe haber exactamente un banish de 's' y debe aparecer antes del
    # cierre del if (!pengu_result_is_ok(...)).
    assert c.count("pengu_banish_string(&s);") == 1
    idx_if = c.find("if (!pengu_result_is_ok")
    idx_banish = c.find("pengu_banish_string(&s);")
    assert idx_if != -1 and idx_banish != -1
    # El banish debe estar después del if (dentro) — buscar el cierre del bloque
    # encontrando el `}` que cierra ese if contando llaves desde idx_if.
    depth = 0
    idx_close = -1
    for i in range(idx_if, len(c)):
        if c[i] == '{':
            depth += 1
        elif c[i] == '}':
            depth -= 1
            if depth == 0:
                idx_close = i
                break
    assert idx_close != -1, "if (!ok) block not closed"
    assert idx_banish < idx_close, (
        "auto-banish must be emitted inside the or: block, "
        "not after it (would reference 's' outside its scope)"
    )


@requires_cc
@requires_runtime
def test_or_block_runs_clean():
    """Compile+run: an or: block that declares a heap local must run without
    crashes and without leaks (ASan-less smoke: just must not abort)."""
    src = (
        'weave may_fail with x as int into maybe int:\n'
        '  if x > 0:\n'
        '    return some x\n'
        '  return maybe none\n'
        'weave main into int:\n'
        '  var v is calling may_fail with 1 or:\n'
        '    var s is "err" + "or"\n'
        '    calling print with s\n'
        '  return 0\n'
    )
    res = compile_run(src, tag="or_block_auto_banish")
    assert res.returncode == 0
```

(Asumo que `requires_cc`/`requires_runtime`/`gen_bundle`/`compile_run`/`check_error`/`check_ok` ya están disponibles desde `tests/conftest.py` — es el mismo patrón que el resto del archivo.)

---

## 2. Fix 2 — `BorrowedEscapeError` (E0049): eliminar o implementar

### 2.1 Decisión requerida

Elige **una** de las dos rutas y documéntalo en el CHANGELOG con la etiqueta `Notas de implementación` (el plan original ya pedía documentar desviaciones ahí).

#### Opción A (recomendada) — Eliminar

`BorrowedEscapeError` nunca se eleva. El CHANGELOG afirma que previene "retornos directos de variables `borrowed`", pero eso no es lo que dice el plan original (que lo reservaba para `borrowed` sin init, que ya es un error de parseo). Mantener una clase muerta es deuda cosmética que confunde a futuros contribuidores.

**Acciones:**

1. `pengu_parser/pengu_errors.py`: eliminar la clase `BorrowedEscapeError` completa.
2. `CHANGELOG.md`, sección `### P2 — Scope-owned locals (auto-banish)`, sub-bullet `Nuevos diagnósticos de ownership`: eliminar la línea:
   ```
   - `BorrowedEscapeError` (`E0049`): previene retornos directos de variables `borrowed` como tipos que requieren ownership o el uso de `borrowed` sin inicializador.
   ```
3. Verificar que ningún archivo del repo la importe: `grep -rn "BorrowedEscapeError\|E0049" pengu_parser/ pengu_lsp/ tests/`.

#### Opción B — Implementar

Si prefieres mantenerla con la semántica del CHANGELOG ("un `borrowed` no puede retornarse como owned"), tendrías que:

1. En `_check_symbol_escape`, detectar si el símbolo es `is_borrowed` **y** escapa vía `return x` cuando el tipo de retorno del weave requiere ownership.
2. Pero esto **no está en el plan original** y abre preguntas de diseño (¿qué pasa con `borrowed` pasado a otra función? ¿con `borrowed` guardado en un rune?). **No lo recomiendo en este prompt.**

### 2.2 Verificación

- Si eliges A: `pytest tests/ -q` sigue verde y `grep -rn "E0049" .` (excluyendo `.git/`) no encuentra nada salvo quizás comentarios históricos que también debes limpiar.
- Si eliges B: añade tests específicos y sé explícito en el CHANGELOG.

---

## 3. Fix 3 — Documentar `or_block` en expresión (KNOWN ISSUE, no fix)

`or_block` en posición de expresión que **no** sea initializer de `var`/`let` (por ejemplo `return foo or: ...`, `calling f with (foo or: ...)`, `var x is a + (foo or: ...)`) cae hoy en el fallback genérico de `_translate_expr_impl` (solo traduce el primer hijo) y produce C silenciosamente incorrecto.

**No arreglar en este prompt.** Solo documentar como known-issue.

### 3.1 Cambio

En `LANGUAGE.md`, §12 (Optionals & errors), tras la lista de semántica de `or:`, añadir:

```markdown
> [!WARNING]
> `or:` sólo es válido como initializer directo de `var` / `let`
> (`var x is <expr> or: ...`). Usarlo dentro de una expresión más grande
> (`return f() or: ...`, `calling g with (x or: ...)`, `a + (b or: ...)`)
> no está soportado: usa `or else` o `or return`, o extrae el `or:` a una
> variable intermedia.
```

Y en `CHANGELOG.md`, dentro de la sección `### P2 — Scope-owned locals`, añadir al final:

```markdown
- **Known issue (no bloqueante):** `or:` blocks en posición de expresión
  distinta al initializer directo de `var` / `let` (p. ej. `return f() or: ...`
  o `calling g with (x or: ...)`) caen en el fallback genérico de codegen y
  emiten C silenciosamente incorrecto. Workaround: extraer a una variable
  intermedia o usar `or else` / `or return`. Planificado para Phase 3.
```

---

## 4. Tests de regresión

### 4.1 Obligatorios

- `test_or_block_creates_own_auto_banish_scope` (§1.4)
- `test_or_block_runs_clean` (§1.4)

### 4.2 Opcionales pero recomendados

Añade a `tests/test_phase2_ownership.py` un test que confirme que **el resto de ramas de `_translate_stmt` que manejan `or_block`** (si las hay) también crean scope. Búscalo así:

```bash
grep -n "or_block" pengu_parser/pengu_codegen.py
```

Si además de las dos ramas `var_decl` / `let_decl` hay una tercera (por ejemplo en `return_stmt` o `_value_branch`), **documentarla como parte del Fix 3** y no tocarla. El prompt actual solo arregla el caso del initializer.

---

## 5. Criterios de aceptación

Marcar al final del trabajo:

- [x] Ambas ramas (`var_decl` y `let_decl`) del `or_block` en `pengu_codegen.py` empujan y sacan un scope de auto-banish y emiten el flush **dentro** del `if (!ok) { ... }`.
- [x] `tests/test_phase2_ownership.py` gana al menos 2 tests nuevos (`test_or_block_creates_own_auto_banish_scope` y `test_or_block_runs_clean`) que pasan.
- [x] `pytest tests/test_phase2_ownership.py -v` → **29/29 verde** (o 27 + los nuevos, nunca menos de 29).
- [x] `pytest tests/ -q` → **no bajar** de 867 passed. Si subes, mejor.
- [x] `pengu check tests/std_programs/` → **26/26 clean**.
- [x] `BorrowedEscapeError` eliminado (Opción A) o implementado con test (Opción B). Si A, eliminar la línea correspondiente del CHANGELOG.
- [x] `LANGUAGE.md` §12 tiene el warning de `or:` en expresión.
- [x] `CHANGELOG.md` documenta el known-issue de `or:` en expresión y (si Opción A) elimina la línea de `E0049`.
- [x] `grep -rn "BorrowedEscapeError" .` (excluyendo `.git/`) no devuelve resultados en Opción A.
- [x] No se ha modificado ningún archivo fuera de los listados en §1, §2 y §3.

---

## 6. Formato de respuesta del agente

1. Diff conceptual por archivo, en orden: `pengu_codegen.py` → `pengu_errors.py` (o CHANGELOG si Opción B) → tests → docs.
2. Salida de `pytest tests/test_phase2_ownership.py -v` y `pytest tests/ -q`.
3. Salida de `pengu check tests/std_programs/`.
4. Lista de archivos modificados con resumen de una línea.
5. Checklist de §5 marcado.

---

## 7. Notas para el agente

1. **No refactorices** `_flush_current_scope_banish`, `_auto_banish_push`, `_auto_banish_register` ni el diseño por identidad de pila. Están bien.
2. **No añadas** categorías nuevas al `auto_banish_stack` (nada de `"or"` distinto de `"block"`).
3. **No toques** `_check_symbol_escape` ni `_compute_auto_banished` — la semántica de Fase 2 está cerrada.
4. **No implementes** `BorrowedEscapeError` con semántica nueva sin consultarlo primero; Opción A es la respuesta esperada.
5. Si algún test de `test_p2_features.py` falla tras tu cambio (porque ahora se emite un banish dentro de un `or_block` previamente testeado), **para y pregunta** — significa que algún test preexistente dependía del bug.
6. **Cero regresiones en `std/`**. Si `pengu check tests/std_programs/` baja de 26/26, para y diagnostica.
