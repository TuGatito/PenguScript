# QA de Fase 11 — PenguScript `1.0.0-rc.1`

| Campo | Valor |
|---|---|
| Fecha | 2026-11-12 |
| Documento | `docs/LANGUAGE.md` |
| Versión | `1.0.0-rc.1` (r13) |
| Líneas | 21.818 |
| Secciones | 71/71 `completo` |
| Estado | Release candidate; QA técnico y revisión adversarial completos; aprobado para implementación |

## 1. Alcance

Auditoría de la especificación completa: gramática, consistencia de términos,
diagnósticos, ejemplos Rust, navegación, referencias y estado de las 71
secciones. No se auditó una implementación del compilador porque **el
repositorio todavía no contiene una**: la especificación y los ejemplos son el
entregable de esta fase.

## 2. Revisión adversarial

| Revisor | Perfil | Veredicto inicial | Estado |
|---|---|---|---|
| `7c98654f-609e-4ff7-a139-5852ede4f62f` | Legibilidad / MoonScript | **BLOCK** | **APPROVE** (re-auditoría; sin blockers) |
| `f85e8b87-a4e3-4a82-928a-92a7c1ae34e0` | Rust / seguridad | **BLOCK** | **APPROVE** (R1–R11 y `byte_char`) |

Los informes originales se conservan en el historial de la sesión. Ambos
revisores aprobaron sus ámbitos: legibilidad (sin blockers) y Rust/seguridad
(R1–R11 y `byte_char`). Este documento declara la aprobación externa de esos
ámbitos, con las limitaciones de cobertura indicadas en §5.

## 3. Hallazgos corregidos

### Gramática §60

- `if`/`unless`: `then` solo en la forma inline; cuerpo multilínea por
  `NEWLINE INDENT body DEDENT`.
- Tuplas literales `(42,)`, `(42, "pengu")` y comprehensions de array/map.
- Etiquetas `outer: for`, `break outer`, `continue outer`.
- Parámetros `morph x: T`; se eliminó el patrón en posición de parámetro.
- `where_clause` en funciones nombradas y `for<'a>` en `where_pred`.
- `modifier*` en `pact`, `ritual` y `grimoire`.
- Llamada de macro como postfijo y azúcar `Fn(A) -> B`.
- Forma exportada de `foreign` con cuerpo.
- `struct_literal`, actualización funcional `..base`, `Vec[…]` y `Set[…]`.
- `if let`, `while let` y `let-else` con producciones propias.
- `raw_tokens`/`RAW_TOKEN` definidos; afirmaciones LL(1) retiradas.

### Desugaring

- `@@no_mangle` -> `#[unsafe(no_mangle)]` (Rust 2024).
- `dream (x) => e` -> `|x| async move { e }`, no async closure inestable.
- `panic(msg)` -> `panic!("{}", msg)`.
- `curse bits` -> `unsafe fn bits`.
- `CString::new(...)?` en vez de `unwrap()`.
- Panic a través de `extern "C"` documentada como abort, no UB obsoleta.

### Diagnósticos

- Catálogo final: **486 códigos únicos** (400 errores, 86 warnings).
- Eliminados duplicados `E2007–E2010`, `E5202`, `W1901`, `E3008`.
- Condición no-`Bool` unificada en `E9301`.
- `spell`/`spirit` retirados -> `E1010`; el resto de palabras retiradas -> `E6101`.
- `check_anchors.py` corregido para no borrar enlaces dentro de código inline.

### Tipos y ejemplos

- `Str` por valor corregido a `&Str`, `String` o `Cow[Str]` en firmas y campos.
- `String` restaurado en los bloques Rust (una sustitución global había
  producido `Stringing`/`&'static String`).
- Contextos faltantes añadidos en ejemplos de §8 y §13.
- Ejemplos completos: 59 pares `.pengu`/`.rs`; los fragmentos didácticos pueden
  omitir `grimoire` y así se documenta.

## 4. Validación ejecutada

| Comprobación | Resultado |
|---|---|
| Secciones vs plan | 71/71, orden y títulos correctos |
| Anclas explícitas | 85 únicas |
| Anclas de encabezado | 893 |
| Enlaces internos | 165, 0 rotos, 0 duplicados |
| Términos prohibidos | limpio |
| Bloques `rust` | 325/325 compilan con `rustc 1.99.1 --edition 2024` |
| Ejemplos `.pengu` | 59/59 pasan comprobación estructural |
| Ejemplos `.rs` | 59/59 compilan (`sec04` y `sec55` como librerías) |
| Diagnósticos | 486 únicos |
| Tabs | 0 |

Comandos:

```bash
python3 scratch/tools/check_sections.py
python3 scratch/tools/check_anchors.py
python3 scratch/tools/check_terms.py
python3 scratch/tools/check_pengu_examples.py
bash scratch/tools/check_rust_snippets.sh
```

## 5. Riesgos residuales

1. **Sin compilador:** no hay front-end, type checker ni codegen propios; los
   pares `.pengu`/`.rs` son manuales. La paridad §63 es documental, no ejecutable.
2. **Compilación de fragmentos:** el checker envuelve sentencias en `fn main`;
   “compila” no equivale a “item independiente válido”.
3. **Re-auditoría:** ambos revisores aprobaron sus ámbitos; las verificaciones
   fueron por lectura, sin un parser ejecutable ni ejecución de `rustc` en la
   re-auditoría final.
4. **Cobertura:** §2, §22–§32, §41–§49, §56–§59 y §67–§69 se revisaron por
   muestreo, no línea por línea.
5. **Gramática:** es una especificación EBNF, no un parser ejecutable; pueden
   quedar ambigüedades menores no detectadas por los validadores.

## 6. Criterios de cierre

- [x] Cero enlaces rotos.
- [x] Cero bloques `rust` sin compilar.
- [x] Cero `TBD` sin justificar.
- [x] Todas las secciones del Anexo A en `completo`.
- [x] Changelog r13 actualizado.
- [x] Dos revisores distintos aprueban (legibilidad y Rust/seguridad).
- [x] Release candidate `1.0.0-rc.1` congelado para revisión.

**Conclusión:** la especificación está técnicamente validada y aprobada como
release candidate `1.0.0-rc.1` por los dos revisores adversariales. Queda la
aprobación del usuario para cerrar la Fase 11.
