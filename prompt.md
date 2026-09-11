# Críticos de producción — reparación (prompt para el agente)

> **Sustituye** al prompt de P2 (P2 está completado y auditado; ver `P2_PROGRESS.md`).
> **Para:** agente de implementación (gemini 3.8 flash).
> **Repo:** `D:\Proyectos\PenguScript` (Windows, PowerShell). Trabaja **en el árbol de trabajo**, sin commits.
> **Objetivo:** reparar los tres defectos **críticos** de `PRODUCTION_READINESS.md` §9.3 (C1, C2, C3),
> dejando el árbol compilando y la suite verde después de **cada** crítico.
> **Presupuesto:** si te quedas sin tokens, cierra el crítico en curso y documenta el estado en
> `CRITICALS_PROGRESS.md` (§7). No dejes tests en rojo ni el árbol a medio editar.

---

## 0. Reglas y contexto

### 0.1 Comandos (usa SIEMPRE el python del venv)

```powershell
cd D:\Proyectos\PenguScript
$env:PYTHONIOENCODING='utf-8'

# chequeo semántico (rápido)
.\.venv\Scripts\python.exe pengu_project.py check --entry scratch\port\01_core_basic_window.pengu

# compilar (esto es lo que revela los bugs de codegen: 'check' NO basta)
.\.venv\Scripts\python.exe pengu_project.py build --entry scratch\port\01_core_basic_window.pengu

# tests focalizados (siempre con -p no:cacheprovider)
.\.venv\Scripts\python.exe -m pytest tests/test_p3_criticals.py tests/test_p1_features.py tests/test_p2_features.py tests/test_p0_toolchain.py -q -p no:cacheprovider

# suite completa (obligatoria al cerrar cada crítico y al terminar)
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider

# batería de programas reales (juego raylib, zlib, multi-módulo, release, memoria)
.\.venv\Scripts\python.exe scratch\readiness_battery.py
```

Si un build "no refleja" los cambios, borra la caché de ese programa:
`Remove-Item build\app.exe,build\bundle.c,build\.bundle_hash -ErrorAction SilentlyContinue`

### 0.2 Reglas duras (idénticas a P1/P2)
1. **PROHIBIDO** `git commit`, `git add -A`, `git checkout`, `git stash`, `git clean`, `git restore`.
   Todo el trabajo está sin commitear y ya se perdió trabajo una vez con `git checkout -- std/`.
2. **No reformatees** archivos completos ni cambies finales de línea. Edita por fragmentos.
3. **No toques** `extern/` ni los `std_c/*.h` que son de librerías.
4. **No regeneres en bloque** `std/raylib.d.pengu` ni `std/sqlite3.d.pengu` (artesanales).
5. Código, comentarios, docstrings, tests y docs **en inglés**.
6. **Un crítico = un hito**: tests focalizados verdes + `CRITICALS_PROGRESS.md` actualizado + suite completa
   (o al menos `tests/test_p3_criticals.py tests/test_p1_features.py tests/test_p2_features.py tests/test_p0_toolchain.py`).

### 0.3 Recordatorios de sintaxis/semántica que necesitarás
- `import std.raylib` → usar `raylib.InitWindow`, `raylib.KeyboardKey.KEY_RIGHT`, `raylib.RAYWHITE`.
- Constantes/variantes de un binding: la forma **sin cualificar** (`KEY_RIGHT`) y la **anidada**
  (`raylib.KeyboardKey.KEY_RIGHT`) funcionan; la **desnuda cualificada** (`raylib.KEY_RIGHT`) es C1.
- `{…}` en un string normal es **interpolación**; para GLSL/regex/rutas se usa `r"…"` o `r"""…"""`.
- Los literales de struct en posición de argumento van entre paréntesis: `(with x is 1.0, y is 2.0)`.

---

## 1. Los tres críticos (orden de trabajo)

| # | Defecto | Impacto | Esfuerzo | Orden |
|---|---------|---------|----------|-------|
| C1 | `modulo.VARIANTE` (desnuda cualificada) emite `modulo_VARIANTE` → C inválido | rompe el uso normal de raylib (flags, uniform types, enums) | 2–4 h | **1º** |
| C2 | `{…}` en string (GLSL) falla con un error genérico mal ubicado | primer escollo de cualquier shader | 1–2 h | **2º** |
| C3 | `restrict` en todo parámetro `ref to T` | UB con APIs que solapan buffers | 1–2 h | **3º** |

Razón del orden: C1 es el que más bloquea (y el más “silencioso”), C2 es pequeño y muy visible,
C3 es mecánico pero toca C generado y tests existentes.

---

## 2. Hitos detallados

### C1 — `modulo.VARIANTE` desnuda resuelve al nombre C equivocado ⚠️

**Repro (hay que COMPILAR, no basta `check`):**
```pengu
import std.raylib

weave main into int:
    calling raylib.SetConfigFlags with raylib.FLAG_MSAA_4X_HINT     # -> raylib_FLAG_MSAA_4X_HINT ❌
    var d as bool is calling raylib.IsKeyDown with raylib.KEY_RIGHT # -> raylib_KEY_RIGHT ❌
    return 0
```
`pengu check` limpio; `pengu build` falla con `'raylib_FLAG_MSAA_4X_HINT' undeclared`.
**Funcionan** (no las rompas): `FLAG_MSAA_4X_HINT` (sin cualificar), `raylib.KeyboardKey.KEY_RIGHT`
(anidada), `raylib.RAYWHITE` (const de struct, se emite el valor).

**Causa (verificada):** en `pengu_parser/pengu_codegen.py`, rama `field_access` de `_translate_expr`
(~líneas 3784-3811): cuando la base es un módulo importado (`sym.kind == "import"`), se busca el miembro
en `sym.module_scope.lookup(raw_field)`; si no aparece con ese nombre se cae al fallback
`return f"{var_name}_{raw_field}"` (línea ~3804) y, si aparece, se devuelve
`mod_field_sym.get_c_name()` (línea ~3803). El caso que sí funciona (anidada) pasa por
`self._get_omen_variant_c_name(...)`, que **ya** implementa la regla correcta
(`pengu_codegen.py:1433-1448`): omens de `.d.pengu` → nombre simple del enumerador (`KEY_RIGHT`);
omens de módulos `.pengu` → prefijados (`Omen_variant`).

**Arreglo (mínimo, con esta forma):** en la rama `field_access` con base módulo:
1. Resolver el miembro probando **ambos** nombres en el scope del módulo:
   `raw_field` y `f"{var_name}_{raw_field}"` (según cómo se registre el scope importado).
2. Si el miembro resuelto es un `omen_variant` (`kind == "omen_variant"` y su `type` es `OmenType`),
   devolver **`self._get_omen_variant_c_name(<nombre lógico del omen>, raw_field)`** — no el `c_name`
   prefijado—. El nombre lógico del omen es `m_sym_t.name`.
3. Si es una `const` declarada en un `.d.pengu`, devolver el identificador **tal cual lo escribe el
   header** (`raw_field`), no el alias prefijado por módulo
   (`pengu_codegen.py:969-979` registra `f"{mod_name}_{name}"` como clave de `self.consts`; esa clave
   es para *lookup*, no un identificador C válido). Si la const tiene valor plegado y tipo struct,
   mantén el comportamiento actual (emitir el valor).
4. Deja intacto el comportamiento para omens **declarados en `.pengu`** (deben seguir prefijados) y para
   miembros que no existen (comportamiento actual). No cambies la firma de `_get_omen_variant_c_name`.

**Defensa en profundidad (opcional, si el arreglo de arriba queda limpio):** haz que los símbolos
declarados en `.d.pengu` lleven ya el `c_name` correcto al registrarse
(`pengu_parser/pengu_checker.py:870-878`): para un variant de un `omen` de binding el enumerador C es
`v_name` (el prefijo por `insignia` aplica a funciones/tipos, no a los enumeradores). Si lo haces,
documenta por qué en un comentario y corre toda la suite (el registro `f"{o_name}_{v_name}"` también
se usa en otras rutas).

**Tests (añádelos a `tests/test_p3_criticals.py`, clase `TestBindingOmenVariants`)** — deben **compilar y
ejecutar**, no solo chequear:
1. `raylib.FLAG_MSAA_4X_HINT`, `raylib.KEY_RIGHT` y `raylib.SHADER_UNIFORM_FLOAT` en un programa que
   compile y ejecute (el C generado debe contener `FLAG_MSAA_4X_HINT`, `KEY_RIGHT`,
   `SHADER_UNIFORM_FLOAT` **sin** prefijo).
2. Regresión: `raylib.KeyboardKey.KEY_RIGHT`, `KEY_RIGHT` sin cualificar y `raylib.RAYWHITE` siguen
   funcionando (build+run).
3. Un `omen` **declarado en Pengu** (no binding) con una variante sigue emitiendo el nombre prefijado:
   comprueba el C con `gen_bundle` (p. ej. `omen Color: Rojo`, `Color_Rojo` en C) y que no se rompe.
4. `raylib.TraceLogLevel.LOG_INFO` (anidada) sigue emitiendo `LOG_INFO`.

**Aceptación:** los 4 grupos de tests pasan; `scratch/readiness_battery.py` caso **A** pasa usando la
forma **cualificada desnuda** (`raylib.FLAG_MSAA_4X_HINT`), no solo la sin cualificar; suite completa verde.

---

### C2 — `{…}` dentro de un string (GLSL) debe dar un error claro

**Repro:**
```pengu
weave main into int:
    var vs as string is "#version 330\nvoid main() { gl_Position = vec4(0.0); }"
    return 0
```
Hoy: `E0000 Syntax error: unexpected '=' at line 1, column 3` — mensaje genérico y **posición relativa al
fragmento interpolado**, no al fichero. La forma correcta es `r"""…"""` (raw triple string), que ya
funciona y está documentada en `LANGUAGE.md` §15.2.

**Causa:** la expresión dentro de `{…}` se parsea por separado (vía `extract_string_parts` /
`_check_string_interpolation`, `pengu_parser/pengu_infer.py:2711`, y la ruta de codegen
`_translate_string_lit`). Al fallar, el `ParseError` propagado conserva la posición del fragmento.

**Arreglo:**
1. Localiza todos los puntos donde se parsea/valida el contenido de una interpolación
   (`_check_string_interpolation`, el codegen de strings interpolados, y cualquier `parse_expr` sobre
   `part.expr`).
2. Envuelve ese parseo en `try/except PenguError` y **re-lanza** un error con:
   - la **posición del literal** en el fichero (la `line`/`col` que ya recibe
     `_check_string_interpolation`, o `node.meta`),
   - mensaje del tipo `Invalid expression inside string interpolation '{…}': <motivo>`,
   - `help:` explícito: «Si el texto no es PenguScript (shader GLSL/HLSL, regex, JSON, rutas), usa una
     raw string: `r"…"` o `r"""…"""`; las llaves se escriben literales allí.»
   - `note:` recordando que `{expr}` es interpolación.
3. No cambies la semántica de la interpolación válida (`"score: {x}"`) ni el rechazo de interpolación en
   contextos `ref to char` (documentado).

**Tests (`tests/test_p3_criticals.py`, clase `TestInterpolationDiagnostics`):**
1. Un GLSL con llaves → error con `help` que menciona `r"""` y posición **del literal** (línea del
   fichero, no 1:3).
2. `r"""…{…}…"""` con el mismo contenido → compila y ejecuta.
3. `"score: {x}"` sigue compilando y produciendo el texto esperado (build+run).
4. Interpolación con una expresión claramente inválida (`"{1 +}"`) → error con la misma pista.

**Aceptación:** los tests pasan; el mensaje apunta a la línea correcta y sugiere la raw string.

---

### C3 — quitar `restrict` de los parámetros generados

**Problema:** todo parámetro `ref to T` (y `self`) se emite `T* restrict`, que es incorrecto para APIs C
que solapan buffers (p. ej. conversiones in-place); con `-O2` es UB que el compilador puede explotar.

**Sitios (verificados):**
- `pengu_parser/pengu_codegen.py:1505`: `param_strs.append(f"{self_t_str}* restrict self")`.
- `pengu_parser/pengu_codegen.py:1509`: `CTypeMapper.to_c_decl(p_type, self._c_ident(p_name), restrict=True)`.
- El mapper (`CTypeMapper.to_c_decl(..., restrict=False)` en `pengu_codegen.py:184-212`) **se queda como
  está**: la capacidad de pedirlo debe seguir existiendo (hay un test unitario que la cubre).

**Arreglo:** deja de pasar `restrict=True` en los dos sitios (emite `T* self` y `T* p`). No añadas flags
nuevos en este hito; si quieres dejar la puerta abierta, un comentario `# restrict is opt-in: see
CTypeMapper.to_c_decl` basta.

**Tests que hay que actualizar (búscalos y ajústalos, no los borres):**
- `tests/test_compiler_core.py:2879` y `:2881` (esperan `Vec2* restrict self`).
- `tests/test_p2_features.py:128` (espera `float (* restrict m)[3]`).
- `tests/test_frozen.py:102` (test unitario del mapper: **déjalo**, sigue siendo válido porque el mapper
  conserva el parámetro).
- Cualquier otro test/`CHEATSHEET`/`LANGUAGE` que mencione `restrict` en firmas generadas.

**Tests nuevos (`tests/test_p3_criticals.py`, clase `TestNoRestrictInGeneratedParams`):**
1. Un `weave` con 2 parámetros `ref to T` genera `void f(T* a, T* b)` (sin `restrict`).
2. Una `enchanting` genera `void T_move(T* self, …)` (sin `restrict`).
3. El mapper sigue soportando `to_c_decl(t, "a", restrict=True) == "…* restrict a"` (test unitario).

**Aceptación:** los tests pasan; suite completa verde; `PRODUCTION_READINESS.md` §9.3 C3 se marca
resuelto y `LANGUAGE.md` §20 deja de listar la advertencia de `restrict`.

---

## 3. Verificación obligatoria (tras cada crítico y al final)

```powershell
# 1. críticos
.\.venv\Scripts\python.exe -m pytest tests/test_p3_criticals.py tests/test_p1_features.py tests/test_p2_features.py tests/test_p0_toolchain.py -q -p no:cacheprovider

# 2. suite completa
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider

# 3. batería de programas reales (juego raylib, zlib, multi-módulo, release, memoria)
.\.venv\Scripts\python.exe scratch\readiness_battery.py

# 4. ports raylib 01–06 compilan (y 04–06 ejecutan)
foreach ($f in @("01_core_basic_window","02_core_input_keys","03_shapes_basic_shapes","04_text_format_text","05_rotating_cube_raymath","06_rlgl_solar_system")) {
  Remove-Item build\app.exe,build\bundle.c,build\.bundle_hash -ErrorAction SilentlyContinue
  .\.venv\Scripts\python.exe pengu_project.py build --entry "scratch\port\$f.pengu"
}

# 5. los 51 módulos de std/ juntos y los bindings sincronizados
.\.venv\Scripts\python.exe pengu_project.py check --entry scratch\all_std_p2_check.pengu
.\.venv\Scripts\python.exe regen_std_bindings.py --check
```

Además, al terminar:
- `PRODUCTION_READINESS.md`: marca **C1/C2/C3 como resueltos** en §9.3 (con la evidencia: test + comando),
  y ajusta §9.2 y la tabla de veredictos si procede.
- `CHANGELOG.md`: añade un bloque `### Fixed (production criticals)` describiendo los tres arreglos y los
  cambios de C generado (`restrict`).
- `LANGUAGE.md`: si C1 se resuelve, quita el `[!WARNING]` de §14.2 sobre la forma cualificada desnuda;
  actualiza §20 (quitar la advertencia de `restrict`); si C2 añade mensaje nuevo, documéntalo en §15.2.

---

## 4. Trampas conocidas (no las reintroduzcas)

1. **`check` no basta**: los tres críticos son de codegen/emisión. Verifica siempre con `build` (y ejecuta).
2. **`#line`**: el C generado lleva directivas que devuelven el error a tu línea `.pengu`; no las rompas
   (`tests/test_p0_toolchain.py::TestLineDirectives`).
3. **Caché del builder**: la clave es contenido (entry + módulos + C glue); si tocas la generación de C,
   borra `build\bundle.c`/`build\.bundle_hash` antes de verificar.
4. **Nombres de variantes**: `_get_omen_variant_c_name` es la única fuente de verdad; no dupliques la
   lógica de prefijado en otros sitios.
5. **Tests existentes que asertan `restrict`**: actualízalos (no los borres) — son la red que detectará
   el cambio.
6. **Sanitización de nombres en `pengu_bind`**: los miembros y los parámetros de `declare` se emiten
   **verbatim** (solo `self`/`type` se sanean; los alias de callback sanean nombres tipo-token). No lo
   cambies aquí.
7. PowerShell: evita `Select-String` con `|` en el patrón (el shell se lo come); usa el tool de búsqueda
   del harness o comillas simples.

## 5. Qué NO hacer

- No añadas features nuevas ni toques los frentes MEDIO/OPCIONAL de `PRODUCTION_READINESS.md` §9.3.
- No cambies la semántica de interpolación válida ni la de `ref to char`.
- No reescribas `pengu_codegen.py` "para limpiar": cambios mínimos y localizados.
- No commitees. No borres `scratch/` (contiene la batería y los ports).

## 6. Definición de "hecho"

1. `raylib.KEY_RIGHT`, `raylib.FLAG_MSAA_4X_HINT` y `raylib.SHADER_UNIFORM_FLOAT` **compilan y ejecutan**;
   las formas sin cualificar y anidadas siguen funcionando; los omens de Pengu siguen prefijados.
2. Un string con `{…}` (GLSL) produce un error que apunta al literal y sugiere `r"""…"""`; la raw string
   correspondiente compila y ejecuta.
3. Ningún parámetro `ref to T` ni `self` se emite `restrict`; el mapper conserva la opción y sus tests.
4. `tests/test_p3_criticals.py` con ≥ 12 tests verdes, suite completa verde, batería de readiness en verde,
   ports 01–06 compilando, y `PRODUCTION_READINESS.md`/`CHANGELOG.md`/`LANGUAGE.md` actualizados.

## 7. Handoff obligatorio: `CRITICALS_PROGRESS.md`

Crea el fichero antes de empezar (con el baseline) y actualízalo **tras cada crítico**:

```markdown
# Criticals progress (handoff)

Última actualización: <fecha/hora> · Agente: <modelo>

## Baseline (no borrar)
- Suite: 804 passed, 1 skipped · ports 01–06 OK · 51 módulos std/ limpios
- Batería: scratch/readiness_battery.py (A–G) en verde salvo los huecos documentados (C1/C2/C3)

## Estado por crítico
| Crítico | Estado | Evidencia (test + comando + resultado) |
|---------|--------|----------------------------------------|
| C1 variantes cualificadas | ⬜/🟡/✅ | ... |
| C2 diagnóstico de interpolación | ... | ... |
| C3 restrict en parámetros | ... | ... |

## Cambios de archivos (con líneas)
## Tests (nombres, resultado de la última corrida, suite completa)
## Lo que falta / siguiente paso concreto (archivo:línea + comando)
## Bloqueos y decisiones
```

Reglas: escribe tras cada crítico, no al final; sé literal (rutas, líneas, comandos y salida resumida);
si algo queda a medias, el árbol debe compilar y pasar la suite y lo incompleto debe estar **revertido a
mano** (nunca con `git checkout`) y documentado. Si te quedas sin presupuesto, prioriza **C1** (es el que
más bloquea) y deja C2/C3 documentados como pendientes.
