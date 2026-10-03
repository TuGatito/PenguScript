## 5. Plan de acción priorizado

### Fase 0 — Cerrar deuda técnica de la evaluación (1–2 semanas)

**Objetivo:** el documento dice que hay H1/H2/H3 abiertos. Ciérralos antes de añadir features.

1. **H1 — `pengu bind` no emite typedefs de headers compañeros.** Cuando `zlib.h` incluye `zconf.h` con `uLong`, el generador debe emitir `alias uLong as u64` (o el underlying primitivo). Sin esto, cualquier binding de librería C real con typedefs se rompe. **Es el bug más importante abierto hoy.**

2. **H2 — Divergencias check vs codegen.** Los tres casos citados (printf sin declare, `[1,2,3]` como argumento, `declare … many`) deben ser errores semánticos o generar C válido. No puede haber "el checker pasa pero gcc falla". Invierte la regla: **si no estás seguro, rechaza**.

3. **H3 — Patrón de ownership C documentado.** En `std/ffi`, expón una guía corta: cómo hacer `defer calling lib_free with p`.

### Fase 1 — Confianza operativa (2–4 semanas)

**Objetivo:** que un crash sea debuggeable y que un bug de memoria no sea silencioso.

1. **Backtrace mínimo en `pengu_runtime.h`.** No necesitas DWARF completo. Un `signal(SIGSEGV, handler)` que imprima los últimos N `#line` markers en un buffer circular _en runtime_ es suficiente. Coste: 1–2 días. Impacto: enorme para producción.

   ```c
   // Idea: g_pengu_frame_stack[64] con push/pop en cada weave call
   // handler imprime los frames que tienen .pengu line
   ```

2. **Bounds checking opt-in.** Bajo `--debug` (o `when debug:`), `xs at i` emite un check con `pengu_assert_bounds(i, len, "file:line")`. En release, cero coste. Esto convierte bugs UB en errores claros **durante desarrollo**, que es cuando importan.

3. **`pengu test --json` y `--watch`.** Ya tienes tests integrados; solo falta el output estructurado para CI.

### Fase 2 — Memoria sin traicionar la identidad (1–3 meses)

Esta es **la decisión arquitectónica más importante** del lenguaje. Hay tres caminos:

#### Opción A: "Scope-owned locals" (recomendado)

El compilador infiere qué locales son "dueños" de sus buffers y emite `banish` automático al salir de scope, **a menos que la variable escape** (que ya analizas con `_check_symbol_escape`).

```pengu
weave process:
    let greeting is "Hello, " + name + "!"    # dueño, se banish-a al salir
    calling print with greeting
    # banish greeting implícito aquí
```

- ✅ No cambia la sintaxis visible
- ✅ Reusa análisis que ya existe
- ✅ Mantiene la "magia": el código se lee como intención, no como gestión
- ⚠️ Necesitas definir "escapa" con cuidado (return, asignación a campo, paso a C)
- ⚠️ Introduce un `move`/`borrow` conceptual que hay que documentar

Esta es **la dirección más Pengu**: no añades sintaxis, añades inteligencia del compilador.

#### Opción B: Arena / Contexto explícito

Un tipo `arena` con `banish` en bloque. Los objetos creados dentro se liberan juntos.

- ✅ Simple de implementar (runtime ya lo soporta casi)
- ⚠️ Requiere disciplina del usuario
- ⚠️ Menos "mágico"

#### Opción C: RAII completo

Descartado por ahora. Es un lenguaje distinto.

**Mi recomendación: Opción A, en modo "opt-out".** Por defecto, locales son owned y auto-banished. Se puede marcar `let borrowed s is ...` para desactivar. Esto es lo que hace que el lenguaje se sienta mágico sin ser mentiroso.

### Fase 3 — Async mínimo (2–3 meses)

No necesitas un runtime nuevo. Ya tienes `filum` sobre `libuv` (o lo que uses). Lo que falta es **azúcar sintáctico**:

```pengu
weave async fetch with url as string into string:
    let body is await http.get with url
    return body
```

Bajo el capó, el compilador:

- Transforma `async weave` en una state machine
- `await` cede el control al event loop
- El event loop es un loop en `main` que corre `pengu_filum_poll()`

Esto es 10x más trabajo que RAII pero es la feature que desbloquea "microservicios". **Puede esperar a que RAII esté estable.**

### Fase 4 — Ecosistema (continuo)

1. **`pengu.lock` + resolución semántica de versiones.** No necesitas un registry central. Con git tags + semver ranges (`^1.2.0`) + hash de commit, resuelves el 90% del caso.
2. **Registry minimalista** (puede ser un repo git con `index.toml`).
3. **3–5 librerías "de bandera"** que demuestren el lenguaje en dominios distintos: un CLI real, un servidor HTTP pequeño, un juego, un parser de datos.
4. **Docs**: guía de "porting a C library" y sección de memoria/ownership.

---

## 6. Qué NO hacer (aunque el documento lo sugiera)

- ❌ **No implementes macros AST.** Rompen minimalismo, complican el LSP, y 95% del código no las necesita.
- ❌ **No implementes un compile-time VM.** `when` + const folding cubre el 90%.
- ❌ **No copies el modelo ARC de Nim.** Es un lenguaje distinto con un problema distinto.
- ❌ **No priorices "portar los 218 ejemplos de raylib".** Portar 50 y escribir 10 juegos reales te enseña más que 218 ports.

---

## 7. Cómo medir progreso (métricas honestas)

En vez del "53.2%" inventado del documento, mide:

| Métrica                                                    | Cómo medirla               | Objetivo 2025                |
| ---------------------------------------------------------- | -------------------------- | ---------------------------- |
| **Ejemplos de código real que compilan sin warnings de C** | Contar                     | 100% de tus tests            |
| **Tiempo de `pengu check` en un proyecto de 50 archivos**  | Medir                      | <2s                          |
| **Ratio "aceptado por checker pero falla en gcc"**         | Correr suite con `-Werror` | 0                            |
| **LOC de C generado por LOC de Pengu**                     | Ratio                      | 1.0–1.3 (indica C limpio)    |
| **Leaks en un programa que corre 1M iteraciones**          | `valgrind --leak-check`    | 0 bytes                      |
| **Tiempo a primera contribución externa**                  | GitHub                     | <3 meses después de publicar |

---

## 8. Resumen ejecutivo

**El PRODUCTION_READINESS.md es mayormente honesto y muy útil.** Pero:

1. Los porcentajes contra Nim son ruido; el análisis cualitativo es sólido.
2. El roadmap de "RAII + async + macros" es un roadmap para _otro_ lenguaje.
3. Los H1/H2/H3 son reales y deben cerrarse **ya**.
4. El mayor riesgo estratégico no es "no llegar a Nim" — es **"intentar llegar a Nim y perder la identidad"**.

**Tu ventaja competitiva es la magia + C limpio + interop fácil.** Profundiza en eso. Un lenguaje que hace _una_ cosa (juegos + C interop) de forma brillante, y que además sirve para CLIs y embebidos, es más valioso que un "Nim pero peor".

**Plan concreto en orden:**

1. **Semanas 1–2:** H1, H2, H3. Cerrar divergencias check/codegen.
2. **Semanas 3–6:** backtrace mínimo + bounds check en debug + `pengu test --json`.
3. **Meses 2–4:** memoria scope-owned (Opción A). **Esta es la decisión clave.**
4. **Meses 5–7:** `pengu.lock` + resolución semver + 3 librerías de bandera.
5. **Meses 8–10:** async/await azucarado sobre `filum`.

Si al final del punto 3 tienes memoria determinista sin RAII pesado, ya estás en terreno de C moderno con esteroides. Eso _es_ un lenguaje de propósito general. No necesitas Nim.
