# PenguScript

**El lenguaje chico con backend filoso.**

| Campo | Valor |
|---|---|
| Lenguaje | PenguScript |
| Versión de la spec | `0.5.0` |
| Estado | Reescritura de misión; núcleo minimalista |
| Fecha | 2026-11-12 |
| Backend | Rust 2024, invisible para el usuario |
| MSRV del backend | 1.85.0 |
| Archivo | `docs/LANGUAGE.md` |

PenguScript es un lenguaje de sistemas pequeño y directo. Usa un backend filoso
para producir código máquina, pero **el usuario nunca escribe ni ve el
backend**. No es un transpilador, no es azúcar sobre otro lenguaje y no busca
retrocompatibilidad con las decisiones de Rust. Es un lenguaje propio.

La personalidad del lenguaje se resume así:

> Records, sums, pattern matching y ownership, sin lifetimes escritos, sin
> traits complejos, sin macros y sin unsafe general. ~15 conceptos. Se lee en
> una tarde. Se usa durante años.

La metáfora operativa es un cuchillo karambit: chico, curvo, filoso, capaz. No
es una navaja suiza. La regla que gobierna el diseño es:

> **Cada concepto que el usuario debe aprender debe justificar su existencia
> con potencia, no con paridad.** Si una feature no da potencia para el 95% del
> código, no entra. Si entra, se simplifica hasta que quepa en una línea.

## Índice

1. [Misión y los ~15 conceptos](#sec-01)
2. [Léxico](#sec-02)
3. [Programa, módulos y entrada](#sec-03)
4. [Tipos](#sec-04)
5. [Bindings, mutabilidad y constantes](#sec-05)
6. [Expresiones y control](#sec-06)
7. [Funciones y closures](#sec-07)
8. [Records y sums](#sec-08)
9. [Pattern matching](#sec-09)
10. [Colecciones](#sec-10)
11. [Ownership y referencias](#sec-11)
12. [Pacts y rituals](#sec-12)
13. [Genéricos y bounds](#sec-13)
14. [Operadores](#sec-14)
15. [Errores, `Option` y `Result`](#sec-15)
16. [FFI: `foreign` y `curse`](#sec-16)
17. [Testing y documentación](#sec-17)
18. [Herramientas y tomes](#sec-18)
19. [Gramática](#sec-19)
20. [Diagnósticos](#sec-20)
21. [Garantías del lenguaje](#sec-21)
22. [Diferido y no soportado](#sec-22)
23. [Glosario](#sec-23)
24. [Cookbook](#sec-24)
25. [Decisiones de diseño (ADR)](#sec-25)
26. [Changelog](#sec-26)
27. [Apéndice Z: qué se eliminó y por qué](#sec-27)
28. [Referencias](#sec-28)

---

<a id="sec-01"></a>
## 1. Misión y los ~15 conceptos

### 1.1 Qué es

PenguScript es un lenguaje:

- **estático**, con inferencia local y firmas explícitas en items;
- **de sistemas**, con ownership y movimiento, pero sin lifetimes escritos;
- **propio**, con un backend que el usuario no ve ni edita;
- **chico**, con una superficie que cabe en una tarde de lectura;
- **explícito**, sin coerción implícita, sin excepciones y sin control oculto.

### 1.2 Qué no es

- No es un transpilador de Rust.
- No es un subconjunto de Rust con otro nombre.
- No es un lenguaje de macros.
- No es un lenguaje async.
- No es un lenguaje de traits con tipos asociados.
- No es una navaja suiza.

### 1.3 Los conceptos del núcleo

| # | Concepto | Sintaxis |
|---|---|---|
| 1 | Primitivos: `Bool`, `Int`, `Float`, `Char`, `String`, `Unit`, `Never` | — |
| 2 | Tuplas | `(A, B)` |
| 3 | Arrays y slices | `[T; N]`, `&[T]` |
| 4 | Colecciones | `Vec[T]`, `Map[K, V]`, `Set[T]` |
| 5 | Records | `rune` |
| 6 | Sums | `enchanting` |
| 7 | Funciones nombradas | `->` |
| 8 | Closures | `=>` |
| 9 | Genéricos con bounds simples | `[T: Pact]` |
| 10 | Contratos e implementaciones | `pact` / `ritual` |
| 11 | Pattern matching | `match` / `when` / `then` |
| 12 | Errores y ausencia | `Option[T]`, `Result[T, E]`, `?T`, `?` |
| 13 | Módulos, imports y visibilidad | `scroll` / `summon` / `unveil` |
| 14 | Bindings, mutabilidad y constantes | `bind` / `morph` / `sigil` / `relic` |
| 15 | Control de flujo | `if` / `elseif` / `else`, `for`, `while`, `loop`, `return`, `break`, `continue` |
| 16 | FFI auditada | `foreign` / `curse` |
| 17 | Punto de entrada | `grimoire` |

Ningún otro keyword entra al núcleo. Si una sección introduce un concepto que
no está en esta tabla, se elimina, se difiere a §22 o se mueve a la librería
estándar.

### 1.4 Valores por defecto, referencias explícitas

Los valores se mueven o se copian; no hay recolección de basura y no hay
lifetimes que el usuario deba escribir. Las referencias `&T` y `&mut T` solo
viven en parámetros y variables locales. Para compartir datos que sobreviven a
una función se usa `Rc[T]` o `Arc[T]`, importados explícitamente.

### 1.5 Ejemplo mínimo

```pengu
rune Point
    x: Float
    y: Float

length = (p: Point) -> Float
    (p.x * p.x + p.y * p.y).sqrt()

grimoire
    bind p = Point(x: 3.0, y: 4.0)
    print(length(p))
```

El programa imprime `5.0`. No hay `main`, no hay `#[...]` y no hay Rust a la
vista: `grimoire` es la entrada.

### 1.6 Criterio de admisión

Una feature entra solo si cumple las cuatro condiciones:

1. Resuelve un problema del 95% del código de sistemas.
2. Se puede explicar en una tabla o en una frase.
3. No duplica otro concepto del núcleo.
4. El backend puede implementarla sin filtraciones en la superficie.

[↑ Volver al índice](#indice)
