# Referencia del lenguaje PenguScript — backend C++

**Versión del documento:** 1.0 (para el backend C++ de `psc`)
**Dialecto:** C++20
**Estado:** referencia de diseño. Describe el lenguaje **completo** que compila a C++ y, para cada construcción, el código que se genera.

> Esta referencia sustituye a [`LANGUAGE.es.md`](LANGUAGE.es.md) para el backend C++. Todo lo que aquí aparece está vivo; lo que desaparece se lista en el §19.7 y en el apéndice D. La justificación de cada decisión está en [`scratch/AUDITORIA_CPP.es.md`](../scratch/AUDITORIA_CPP.es.md).
>
> **Evidencia.** Las formas que el documento promete se compilan y ejecutan con `g++ 16.2.1` y `clang++ 23.1.4` con `-std=c++20 -fno-exceptions -fno-rtti -Wall -Wextra -Wpedantic` (cero avisos, ASan/UBSan limpio): la sonda está en [`scratch/audit_cpp/probe_conceptos.cpp`](../scratch/audit_cpp/probe_conceptos.cpp) el ejemplo completo del §20 está extraído y verificado en [`scratch/audit_cpp/example_s20.cpp`](../scratch/audit_cpp/example_s20.cpp), y las formas de este documento que no aparecen allí (bucles como expresión, `unless` como expresión, `judge` en posición de valor, defaults en todos los parámetros, `with` que omite campos) están en [`scratch/audit_cpp/probe_moon.cpp`](../scratch/audit_cpp/probe_moon.cpp), y las de las dos últimas revisiones (`Forma` con ADL, `@repr(c)` con `born`, `@public`, prefijos de módulo, `operator ()`, omens de una sola variante) en [`probe_review2.cpp`](../scratch/audit_cpp/probe_review2.cpp) y [`probe_review3.cpp`](../scratch/audit_cpp/probe_review3.cpp). MSVC no está disponible aquí: la verificación con `cl` queda como riesgo abierto (R2 de la auditoría).

---

## Índice

La referencia va de la sintaxis más básica a la más avanzada. Si vienes de C++, empieza por §0.3; si vienes de PenguScript, por §19.7 (lo que ya no existe).

| Si buscas… | Ve a |
|---|---|
| cómo se escribe un tipo (`vector of`, `map of K, V`, `maybe`) | §2.2 |
| el C++ que se genera para cada cosa | §6, apéndice D |
| bucles como valor (`for`/`while` que producen un contenedor) | §5.3, §5.6, §5.8 |
| constructores, destructores y copia (`born`, `die`, `mirror`) | §9.3 |
| comparar y sobrecargar operadores | §4.8, §4.3 |
| errores y opcionales (`maybe`, `result`, `try`, `or:`) | §12 |
| memoria y propiedad (`banish`, `unique`, `shared`) | §13 |
| métodos, `enchanting` y conceptos | §10 |
| genéricos (`shard`, `where`) | §11 |
| mezclar C y C++ (`extern c`, `extern cpp`, `regnum`) | §6.4, §8 |
| hilos y corrutinas | §15 |
| diagnósticos y códigos de error | §19 |
| qué se ha retirado y por qué | §19.7, apéndice D.1 |

- [Índice](#índice)
- [0. Cómo leer esta referencia](#0-cómo-leer-esta-referencia)
    - [0.1 Las tres capas de nombres](#01-las-tres-capas-de-nombres)
    - [0.2 El contrato Pengunic en C++](#02-el-contrato-pengunic-en-c)
    - [0.3 Qué necesita saber un programador de C++](#03-qué-necesita-saber-un-programador-de-c)
    - [0.4 El runtime: `pengu/core.hpp`](#04-el-runtime-pengucorehpp)
- [1. Estructura léxica](#1-estructura-léxica)
    - [1.1 Archivos y módulos](#11-archivos-y-módulos)
    - [1.2 Comentarios](#12-comentarios)
    - [1.3 Identificadores y keywords](#13-identificadores-y-keywords)
        - [1.3.1 Nombres C++ de los símbolos de módulo](#131-nombres-c-de-los-símbolos-de-módulo)
    - [1.4 Disposición](#14-disposición)
    - [1.5 Literales](#15-literales)
- [2. Tipos](#2-tipos)
    - [2.1 Tipos primitivos y de runtime](#21-tipos-primitivos-y-de-runtime)
    - [2.2 Tipos compuestos](#22-tipos-compuestos)
    - [2.2.1 `vector of bool` es especial](#221-vector-of-bool-es-especial)
    - [2.3 Valor frente a referencia](#23-valor-frente-a-referencia)
- [3. Variables y constantes](#3-variables-y-constantes)
    - [3.1 Declaraciones](#31-declaraciones)
    - [3.2 Asignación y `set`](#32-asignación-y-set)
    - [3.3 Scope y shadowing](#33-scope-y-shadowing)
    - [3.4 Garantías de seguridad y renuncias](#34-garantías-de-seguridad-y-renuncias)
- [4. Operadores](#4-operadores)
    - [4.1 Precedencia](#41-precedencia)
    - [4.2 Aritmética y bit a bit](#42-aritmética-y-bit-a-bit)
    - [4.3 Comparación, pertenencia y tests de palabras](#43-comparación-pertenencia-y-tests-de-palabras)
    - [4.4 Dirección, desreferencia, tamaño](#44-dirección-desreferencia-tamaño)
    - [4.5 Primitivas de carácter y byte](#45-primitivas-de-carácter-y-byte)
    - [4.6 Casts y conversiones](#46-casts-y-conversiones)
    - [4.7 `defined`, `size of` y valores de tiempo de compilación](#47-defined-size-of-y-valores-de-tiempo-de-compilación)
    - [4.8 Sobrecarga de operadores](#48-sobrecarga-de-operadores)
        - [Llamar a un valor: `operator ()`](#llamar-a-un-valor-operator)
- [5. Control de flujo](#5-control-de-flujo)
    - [5.1 `if`, `unless` y bindings de `if`](#51-if-unless-y-bindings-de-if)
    - [5.2 `while`](#52-while)
    - [5.3 `for`](#53-for)
        - [5.3.1 `for` como expresión](#531-for-como-expresión)
    - [5.4 `judge` — coincidencia de patrones](#54-judge-coincidencia-de-patrones)
    - [5.5 `break`, `continue`, `return`](#55-break-continue-return)
        - [5.5.1 Control de flujo dentro de expresiones de bucle](#551-control-de-flujo-dentro-de-expresiones-de-bucle)
    - [5.6 Expresiones de bloque](#56-expresiones-de-bloque)
        - [5.6.1 `while` como expresión](#561-while-como-expresión)
    - [5.7 `with` como sentencia](#57-with-como-sentencia)
    - [5.8 Lo que MoonScript tiene y aquí no entra](#58-lo-que-moonscript-tiene-y-aquí-no-entra)
- [6. Funciones](#6-funciones)
    - [6.1 `weave`](#61-weave)
    - [6.2 Convenciones de llamada](#62-convenciones-de-llamada)
    - [6.3 Parámetros variádicos](#63-parámetros-variádicos)
    - [6.4 Declaraciones externas: `extern c` y `extern cpp`](#64-declaraciones-externas-extern-c-y-extern-cpp)
        - [6.4.1 `regnum` + `import`](#641-regnum-import)
    - [6.5 Lambdas](#65-lambdas)
    - [6.6 Métodos `ritual`](#66-métodos-ritual)
    - [6.7 Punto de entrada](#67-punto-de-entrada)
- [7. Módulos e imports](#7-módulos-e-imports)
    - [7.1 Módulo = archivo](#71-módulo-archivo)
    - [7.2 `import`](#72-import)
    - [7.3 Estado a nivel de módulo](#73-estado-a-nivel-de-módulo)
    - [7.4 Privacidad](#74-privacidad)
    - [7.5 Resolución de nombres](#75-resolución-de-nombres)
- [8. Interop con C y C++](#8-interop-con-c-y-c)
    - [8.1 `include`, `link`, `ldflag`, `insignia`](#81-include-link-ldflag-insignia)
    - [8.2 `extern c`: la frontera C](#82-extern-c-la-frontera-c)
    - [8.3 `extern cpp`: la frontera C++](#83-extern-cpp-la-frontera-c)
    - [8.4 `opaque`, `ref to`, `bytes of`](#84-opaque-ref-to-bytes-of)
    - [8.5 Archivos de declaración `.d.pengu`](#85-archivos-de-declaración-dpengu)
    - [8.6 `antiquus` — código incrustado](#86-antiquus-código-incrustado)
    - [8.7 `transmute`, `@packed`, `@align`, `@repr(c)`](#87-transmute-packed-align-reprc)
- [9. Tipos compuestos](#9-tipos-compuestos)
    - [9.1 `rune` — structs](#91-rune-structs)
    - [9.2 Campos con defecto y agregados](#92-campos-con-defecto-y-agregados)
    - [9.3 `born`, `born mirror` y `die` — constructores y destructor](#93-born-born-mirror-y-die-constructores-y-destructor)
    - [9.4 `echo` — uniones](#94-echo-uniones)
    - [9.5 `omen` — enums y tipos suma](#95-omen-enums-y-tipos-suma)
    - [9.6 `seal`, `alias` y `opaque`](#96-seal-alias-y-opaque)
    - [9.7 `frozen`](#97-frozen)
    - [9.8 Constructores `with:`](#98-constructores-with)
    - [9.9 `inherit` — herencia real](#99-inherit-herencia-real)
    - [9.10 Ejemplo completo de tipos](#910-ejemplo-completo-de-tipos)
- [10. Métodos y conceptos](#10-métodos-y-conceptos)
    - [10.1 `enchanting` — métodos sobre un tipo](#101-enchanting-métodos-sobre-un-tipo)
    - [10.2 `concept` — contratos de tiempo de compilación](#102-concept-contratos-de-tiempo-de-compilación)
    - [10.3 `bind` — implementar un concepto](#103-bind-implementar-un-concepto)
    - [10.4 `bind` sobre tipos de C++ (FFI de clases)](#104-bind-sobre-tipos-de-c-ffi-de-clases)
    - [10.5 Resolución de métodos](#105-resolución-de-métodos)
    - [10.6 Conceptos integrados](#106-conceptos-integrados)
        - [`Forma` en la práctica](#forma-en-la-práctica)
- [11. Genéricos](#11-genéricos)
    - [11.1 `shard`](#111-shard)
    - [11.2 Bounds](#112-bounds)
    - [11.3 `donum T`](#113-donum-t)
    - [11.4 Métodos genéricos y derivación](#114-métodos-genéricos-y-derivación)
    - [11.5 Límites](#115-límites)
- [12. Opcionales y errores](#12-opcionales-y-errores)
    - [12.1 `maybe T` y `result of T to E`](#121-maybe-t-y-result-of-t-to-e)
    - [12.2 Constructores](#122-constructores)
    - [12.3 Inspección y desenvolvimiento](#123-inspección-y-desenvolvimiento)
    - [12.4 `or else`, `or return`, `try`, `or:`](#124-or-else-or-return-try-or)
    - [12.5 `panic`](#125-panic)
    - [12.6 `defer` y `errdefer`](#126-defer-y-errdefer)
    - [12.7 Propiedad de los valores opcionales](#127-propiedad-de-los-valores-opcionales)
- [13. Memoria](#13-memoria)
    - [13.1 El modelo](#131-el-modelo)
    - [13.2 `banish`](#132-banish)
    - [13.3 `defer` y `errdefer`](#133-defer-y-errdefer)
    - [13.4 Lo que el compilador no hace](#134-lo-que-el-compilador-no-hace)
    - [13.5 Temporales con dueño en expresiones](#135-temporales-con-dueño-en-expresiones)
    - [13.6 Los valores se mueven, no se copian](#136-los-valores-se-mueven-no-se-copian)
    - [13.7 Valores devueltos y parámetros](#137-valores-devueltos-y-parámetros)
    - [13.8 Depurar fugas](#138-depurar-fugas)
    - [13.9 `unique`, `shared`, `weak`](#139-unique-shared-weak)
    - [13.10 Sin copy-on-write](#1310-sin-copy-on-write)
    - [13.11 Ciclos y recursión](#1311-ciclos-y-recursión)
- [14. Atributos](#14-atributos)
    - [14.1 `@shared`](#141-shared)
    - [14.2 `@no_cmp`](#142-no_cmp)
- [15. Hilos y corrutinas](#15-hilos-y-corrutinas)
    - [15.1 Hilos (`std.filum`)](#151-hilos-stdfilum)
    - [15.2 Corrutinas (`std.coro`)](#152-corrutinas-stdcoro)
    - [15.3 Reactor](#153-reactor)
- [16. Tests y herramientas](#16-tests-y-herramientas)
    - [16.1 Bloques `test`](#161-bloques-test)
    - [16.1.1 Cómo funciona el arnés](#1611-cómo-funciona-el-arnés)
    - [16.2 Comandos](#162-comandos)
    - [16.3 Opciones de build](#163-opciones-de-build)
    - [16.4 Manifiesto](#164-manifiesto)
    - [16.5 `psc doc`](#165-psc-doc)
- [17. Encadenamiento, pipes, tuplas y forma corta](#17-encadenamiento-pipes-tuplas-y-forma-corta)
    - [17.1 Cadenas de métodos](#171-cadenas-de-métodos)
    - [17.2 Pipes](#172-pipes)
    - [17.3 Tuplas y retornos múltiples](#173-tuplas-y-retornos-múltiples)
    - [17.4 Inicializadores abreviados de struct](#174-inicializadores-abreviados-de-struct)
- [18. Deprecación](#18-deprecación)
- [19. Diagnósticos](#19-diagnósticos)
    - [19.1 Cómo se lee un diagnóstico](#191-cómo-se-lee-un-diagnóstico)
    - [19.2 Códigos que no cambian](#192-códigos-que-no-cambian)
    - [19.3 Códigos nuevos](#193-códigos-nuevos)
    - [19.4 Códigos que cambian de detalle](#194-códigos-que-cambian-de-detalle)
    - [19.5 Qué cambia de comportamiento y de rendimiento](#195-qué-cambia-de-comportamiento-y-de-rendimiento)
    - [19.6 Traducción de errores del compilador de C++](#196-traducción-de-errores-del-compilador-de-c)
    - [19.7 Lo que se retira](#197-lo-que-se-retira)
- [20. Ejemplo completo](#20-ejemplo-completo)
- [Apéndice A. Keywords](#apéndice-a-keywords)
- [Apéndice B. Representaciones](#apéndice-b-representaciones)
- [Apéndice C. Esbozo de gramática](#apéndice-c-esbozo-de-gramática)
- [Apéndice D. Correspondencia rápida](#apéndice-d-correspondencia-rápida)
    - [D.1 Lo que ya no existe](#d1-lo-que-ya-no-existe)
---

## 0. Cómo leer esta referencia

Cada construcción se presenta así:

1. el fragmento **Pengu** (bloque `pengu`),
2. el **C++ que emite el compilador** (bloque `cpp`),
3. las reglas y los diagnósticos que la rodean.

Los fragmentos marcados `pengu-fragment` son sintaxis válida pero no forman una unidad compilable por sí solos.

### 0.1 Las tres capas de nombres

El lenguaje tiene tres vocabularios y conviene saber a cuál pertenece cada palabra:

| Capa | Qué nombra | Ejemplos |
|---|---|---|
| **Tipos de frontera (inglés)** | lo que existe en C++ y en la ABI | `string`, `vector`, `map`, `umap`, `set`, `uset`, `array`, `span`, `unique`, `shared`, `weak`, `maybe`, `result`, `seal`, `opaque`, `frozen` |
| **Palabras del lenguaje (latín)** | lo que inventa Pengu y no existe en C++ | `weave`, `rune`, `omen`, `antiquus`, `banish`, `sigil`, `essence`, `shard`, `insignia`, `regnum`, `inherit` |
| **Inglés mágico** | verbos y conectores que se leen como una frase | `echo`, `seal`, `judge`, `calling`, `with`, `defer`, `errdefer`, `born`, `die`, `mirror`, `operator` |

La regla para acuñar nombres nuevos: **verbo para acciones, sustantivo para entidades, y nunca reutilizar una palabra que C++ ya tenga con otro significado**.

### 0.2 El contrato Pengunic en C++

El principio 5 de [`PENGUNIC.es.md`](PENGUNIC.es.md) —«C predecible»— se reescribe así para este backend:

> **C++ predecible.** Cada construcción baja a C++ que podrías haber escrito tú: sin `virtual`, sin excepciones, sin `typeid`, sin `new`/`delete` a mano, sin magia de biblioteca más allá de la que el propio C++ estandariza.

Los otros cinco principios no cambian: el compilador comprueba lo que puede; la propiedad es explícita; valores primero; los errores son valores; la documentación es parte de la API.

### 0.3 Qué necesita saber un programador de C++

- Los tipos de la biblioteca son **los de C++**, sin `std::`: `vector of int` es `std::vector<int32_t>`, `string` es `std::string`.
- Todo tipo de usuario es un `struct` con métodos miembros; no hay `class`, ni herencia con `virtual`, ni constructores implícitos de copia ocultos: la copia es profunda y visible.
- `ref to T` es `T*`; `ref to frozen T` es `const T*`.
- `maybe T` es `std::optional<T>` y `result of T to E` es `pengu::Result<T, E>`. No hay cajas: no hay `malloc` por valor.
- `map` es `std::map` (ordenado) y `umap` es `std::unordered_map` (hash).
- La propiedad se declara: `unique of T` (`std::unique_ptr`), `shared of T` (`std::shared_ptr`), `weak of T` (`std::weak_ptr`).
- `defer` es un guard de alcance (`pengu::defer`), no una construcción del lenguaje traducida a `goto`.

### 0.4 El runtime: `pengu/core.hpp`

Todo lo que el emisor necesita y C++ no da vive en una cabecera pequeña (`pengu/core.hpp`, ~250 líneas) y en `pengu/plat.c`. No hay `std::format`, ni `iostream`, ni excepciones:

```cpp
namespace pengu {

[[noreturn]] void panic(const char* msg, const char* file, int line);

template <typename F> class ScopeGuard { /* … */ };
template <typename F> ScopeGuard<F> defer(F f);          // §12.6

size_t check_index(int64_t i, size_t n, const char* file, int line);

std::string format(const char* fmt, ...);                // printf, no std::format
void print(std::string_view s);

template <typename T, typename E> class Result;          // §12.1
template <typename E> class Result<void, E>;

// Punteros: nullptr si el valor no está (nunca lanzan; llaman a panic con el
// archivo y la línea del .pengu cuando la operación exige que el valor exista).
template <typename T> T* some_value(std::optional<T>& o, const char* f, int l);
template <typename T, typename E> T* result_ok_value(Result<T, E>& r, const char* f, int l);
template <typename T, typename E> E* result_err_value(Result<T, E>& r, const char* f, int l);
template <typename T, typename E> E& err_value_of(Result<T, E>& r, const char* f, int l);

template <typename T> std::shared_ptr<T> lock(std::weak_ptr<T>& w);   // §13.9

template <typename T> concept Hashable = /* … */;        // §10.6
template <typename T> concept Formattable = /* … */;

} // namespace pengu
```

Las tres funciones `some_value`/`result_ok_value`/`result_err_value` existen porque `.value()` y `.at()` de la biblioteca lanzan excepciones y el dialecto se compila con `-fno-exceptions`: estas devuelven un puntero al valor, o llaman a `panic` con el archivo y la línea del `.pengu` cuando el valor es obligatorio (§12.3).

---


## 1. Estructura léxica

### 1.1 Archivos y módulos

Un archivo `.pengu` es un módulo. El nombre del archivo es el nombre del módulo; las carpetas forman un camino con puntos: `std/scrolls.pengu` es `std.scrolls`.

Los archivos `.d.pengu` son **declaraciones puras** (§8.4): no generan código salvo el `include` y los `declare`/`extern` que contienen.

Cada archivo se compila a una **unidad de traducción** `.cpp` con su guard de inclusión y sus `#line` hacia el `.pengu` original.

```cpp
// Auto-generated by PSC (C++ backend, F1) — do not edit.
#ifndef PENGU_TU_std_scrolls_HPP
#define PENGU_TU_std_scrolls_HPP

#include <pengu/core.hpp>
#include <stdint.h>
#include <stddef.h>
#include <string>
#include <vector>
#include <map>
#include <optional>
#include <variant>
#include <tuple>
#include <array>
#include <span>
#include <memory>
#include <unordered_map>

#line 1 "std/scrolls.pengu"
```

### 1.2 Comentarios

```pengu-fragment
# comentario de línea
## comentario de documentación (lo extraen `psc doc` y el LSP)
```

Los comentarios no llegan al C++ generado: `psc emit-cpp` los descarta. La documentación `##` se conserva en el índice del LSP y en `psc doc`, no en el código.

### 1.3 Identificadores y keywords

Un identificador empieza por letra o `_` y sigue con letras, dígitos o `_`. Las keywords reales están en el apéndice A; estas son **contextuales**: solo son palabras en su posición y siguen siendo identificadores válidos en cualquier otra:

| Contextual | Dónde es palabra | Ejemplo válido fuera de sitio |
|---|---|---|
| `judge` | inicio de sentencia | `let judge as int is 1` |
| `over` | tras la expresión de un `judge` | `var over as int is 2` |
| `pipe` | inicio de línea de un pipe | `weave pipe into int` |
| `lambda` | inicio de expresión | `var lambda as int is 3` |
| `operator` | dentro de `enchanting` | `var operator as int is 4` |
| `born` / `die` / `mirror` | como nombre de `weave` dentro de `enchanting` | `weave born_extra into void` |
| `inherit` | tras el nombre de un `rune` | `var inherit as int is 5` |
| `then` / `step` | en `for` y comprensiones | `var then as int is 6` |
| `main` | nombre de la función de entrada | `weave main_helper into int` |
| `extern` | inicio de bloque; `extern c`/`extern cpp` | `var extern_p as int is 7` |

Un nombre de una capa no se puede reutilizar como tipo sin `W0018` (§7.5).

Los identificadores se emiten **sin cambios** al C++, con tres excepciones:

| Caso | Pengu | C++ |
|---|---|---|
| Colisión con palabra clave de C++ | `class`, `template`, `new`, `delete`, `namespace`, `operator`… | sufijo `_p` → `class_p` |
| Símbolo de módulo | `weave split` en `std.scrolls` | `std_scrolls_split` (§1.3.1) |
| Temporal interno | (generado) | `_t0`, `_t1`, … `_r0`, `_w0` |

Un tipo de usuario que se llame igual que un tipo de la biblioteca (`rune string`) es `W0018` y gana el tipo del usuario en su módulo.

#### 1.3.1 Nombres C++ de los símbolos de módulo

El backend C plano ya tenía este problema resuelto con prefijos; el de C++ no puede renunciar a él, porque dos módulos pueden declarar el mismo nombre y el enlazador vería dos `add` con enlace externo en el mismo programa.

**Regla**: todo símbolo de un módulo que no sea interno (`static`) se emite con el **prefijo del módulo**, calculado de su ruta con `/` → `_` y los puntos de la ruta de import como `_`:

| Pengu | Módulo | C++ |
|---|---|---|
| `weave split` | `std.scrolls` | `std_scrolls_split` |
| `rune Buffer` | `std.scrolls` | `std_scrolls_Buffer` |
| `weave add` | `mylib` | `mylib_add` |
| `weave helper` | `src.main` | `src_main_helper` |

Las tres excepciones, y solo tres:

| Directiva | Efecto sobre el nombre | Ejemplo |
|---|---|---|
| `@export("sym")` | **sustituye** el prefijo: el símbolo C++ es exactamente `sym` | `@export("pengu_open") weave open` → `pengu_open` |
| `insignia pengu_` (nivel de módulo) | el prefijo del módulo pasa a ser `pengu_` + módulo | `insignia pengu_` en `std.scrolls` → `pengu_std_scrolls_split` |
| `antiquus` | no lleva prefijo: su cuerpo es C++ escrito a mano y el nombre del `antiquus` es el que el usuario puso | `antiquus raw_sum with …` → `raw_sum` |

Consecuencias que conviene tener presentes:

- `@export("sym")` **no añade** el prefijo: lo reemplaza. Si el usuario quiere prefijo manual, lo escribe en el nombre (`@export("mylib_sym")`).
- `insignia` y `@export` son ortogonales: si un símbolo lleva `@export`, el `insignia` del módulo no le afecta.
- El prefijo se aplica a **declaraciones**, no a usos: desde Pengu se sigue llamando `calling std.scrolls.split with …` (`calling split with …` si está importado sin alias); el emisor traduce a `std_scrolls_split(...)`.
- Las funciones `static` (`inline`, `lambda`, `_pengu_lambda_N`, helpers de módulo) no llevan prefijo: su enlace es interno.
- Los `declare` de `extern c`/`extern cpp` **no** se prefijan: el símbolo ya existe en la biblioteca externa con su nombre real (§6.4).
- `extern "C"` y prefijo conviven sin problema: el prefijo va **dentro** del nombre, así que un `weave helper` definido en un bloque `extern c` de `std.scrolls` emite `extern "C" int32_t std_scrolls_helper(...)`. Lo único que no admite prefijo es el `declare`, porque el símbolo es de fuera.
- Los ayudantes que genera el emisor usan el nombre C++ ya prefijado, para que no colisionen: `_pengu_clone_std_scrolls_Buffer`, `_pengu_cleanup_std_scrolls_Buffer`, y el enum de etiquetas de un `omen` es `std_scrolls_Slot_Tag` (§9.5).

### 1.4 Disposición

La indentación define bloques: **cuatro espacios** por nivel, sin tabuladores (`psc fmt` normaliza). Una línea de continuación empieza por `.` o `->` (cadena de métodos, §17.1) o por `pipe` (§17.2) y se pliega en la línea anterior antes del lexado.

El compilador es **sensible a mayúsculas** y no hay punto y coma: el fin de línea termina la sentencia salvo continuación explícita.

### 1.5 Literales

```pengu-fragment
42              # int (int32_t)
0xFF            # int, hexadecimal
0b1010          # int, binario
3.5             # float (f32 de 32 bits)
3.5f64          # f64 (doble)
'a'             # char (byte firmado, 'a' = 97)
true / false    # bool
null            # puntero nulo (nullptr)
"hola"          # string
r"C:\tmp"       # string verbal (sin escapes)
"""texto
multilínea"""   # string de varias líneas
"n = {n}"       # interpolación
"pi = {x:.2f}"  # interpolación con formato printf
[1, 2, 3]       # vector (necesita tipo en el contexto o anotación)
{"k": 1}        # map (necesita anotación de tipo, E0076)
1 to 4          # rango [1, 4) — también 1 .. 4
```

La interpolación se compila a una sola llamada de formato, sin temporales intermedios:

```cpp
pengu::format("%d, %s", n, s.c_str())
```
```cpp
// "pi = {x:.2f}"  →  el formato se valida en compilación (E0019)
pengu::format("pi = %.2f", x)
```

El emisor construye la cadena de formato con el verbo de cada hueco **según el tipo del valor**, y pasa el argumento ya convertido al tipo que `printf` espera:

| Tipo del valor | Verbo por defecto | Argumento emitido |
|---|---|---|
| `int`, `i16`, `i8`, `u8`, `u16`, `u32`, `uint` | `%d` / `%u` | convertido a `int` / `unsigned` |
| `i64`, `u64`, `usize`, `isize`, `size_t`, `long`, `ulong` | `%lld` / `%llu` | `(long long)` / `(unsigned long long)` |
| `float`, `f64` | `%g` | `(double)` |
| `string` | `%s` | `x.c_str()` |
| `char` | `%c` | `x` |
| `bool` | `%s` | `x ? "true" : "false"` |
| tipo con `Forma` ligado (§10.6) | el de su `format` | `to_str(x)` |
| `opaque` (`void*`) | `%p` | `static_cast<const void*>(x)` |

- Un hueco con formato (`{x:.2f}`, `{n:04d}`, `{id:x}`, `{name:10s}`) se valida en compilación (`E0019`) y debe casar con el tipo: `d i o u x X` con enteros, `f e g` con flotantes, `s` con `string`. Un verbo que no casa es `E0019`.
- `{{` y `}}` producen llaves literales y se emiten como `{` y `}`.
- Una `%` **literal** del texto se emite `%%`: si no, `"50% {n}"` produciría la cadena de formato `"50% %d"` y `printf` leería un especificador inválido.
- Un valor de tipo de usuario (una `rune`, `omen`, `echo`, `seal`) sin `bind Forma` en un hueco es **`E0128`**: no hay verbo que le corresponda.

**Quién necesita `bind Forma` y quién no** (esta es la regla que evita la ambigüedad de si hace falta importar `std.spark`):

| Tipo del hueco | Verbo | ¿Necesita `bind Forma`? | ¿Necesita `import std.spark`? |
|---|---|---|---|
| `int`, `i64`, `u32`, `u8`, `usize`… | tabla fija de arriba | **no** | **no** |
| `float`, `f64` | `%g` | **no** | **no** |
| `bool` | `%s` con `"true"`/`"false"` | **no** | **no** |
| `char` | `%c` | **no** | **no** |
| `string` | `%s` con `.c_str()` | **no** | **no** |
| `opaque` | `%p` | **no** | **no** |
| `rune`/`omen`/`echo`/`seal` | el de su `to_str` | **sí** | **no** |

El emisor tiene la tabla de verbos **incorporada**: los tipos nativos se interpolan en cualquier módulo, sin importar nada. `std.spark` **no** liga `Forma` a los escalares (no hace falta) y solo un módulo que quiera interpolar **sus propios** tipos necesita escribir el `bind`.

Un literal `vector` se emite como `std::vector<T>{}` con `push_back` en orden; el tipo `T` sale de la anotación o del contexto (parámetro, retorno, primer uso).

```pengu-fragment
var xs as vector of int is [1, 2, 3]
var m as map of string, int is {"a": 1, "b": 2}
```

```cpp
std::vector<int32_t> xs{1, 2, 3};
std::map<std::string, int32_t> m{{"a", 1}, {"b", 2}};
```

---

## 2. Tipos

### 2.1 Tipos primitivos y de runtime

| Pengu | C++ | Tamaño | Notas |
|---|---|---|---|
| `int` | `int32_t` | 4 | entero por defecto |
| `i64`, `long` | `int64_t` | 8 | |
| `i16`, `short` | `int16_t` | 2 | |
| `i8` | `int8_t` | 1 | |
| `u32`, `uint` | `uint32_t` | 4 | |
| `u64`, `ulong` | `uint64_t` | 8 | |
| `u16`, `ushort` | `uint16_t` | 2 | |
| `byte`, `u8` | `uint8_t` | 1 | |
| `size_t`, `usize` | `size_t` | — | índices y tamaños |
| `isize` | `ptrdiff_t` | — | diferencia de punteros |
| `float`, `f32` | `float` | 4 | |
| `f64`, `double` | `double` | 8 | |
| `char` | `char` | 1 | un byte; `ord`/`chr` lo convierten |
| `bool` | `bool` | 1 | |
| `void` | `void` | — | |
| `string` | `std::string` | — | UTF-8 por convención, sin validar |
| `opaque` | `void*` | — | handle opaco (§8.3) |

Todos los enteros son de ancho fijo y **no hay promociones implícitas** entre ellos: `int to i64` es explícito.

### 2.2 Tipos compuestos

| Pengu | C++ | Notas |
|---|---|---|
| `vector of T` | `std::vector<T>` | elemento propio, copia profunda |
| `map of K, V` | `std::map<K, V>` | **ordenado**, `K` debe ser ordenable |
| `umap of K, V` | `std::unordered_map<K, V>` | hash, `K` debe implementar `Vinculum` |
| `set of T` / `uset of T` | `std::set<T>` / `std::unordered_set<T>` | igual que `map`/`umap` |
| `array of T with size N` | `std::array<T, N>` | tamaño obligatorio (`E0109`) |
| `span of T` | `std::span<T>` | vista, no posee |
| `span of frozen T` | `std::span<const T>` | vista de solo lectura |
| `string` | `std::string` | |
| `maybe T` | `std::optional<T>` | sin caja |
| `result of T to E` | `pengu::Result<T, E>` | sin caja |
| `ref to T` | `T*` | préstamo mutable |
| `ref to frozen T` | `const T*` | préstamo de solo lectura |
| `unique of T` | `std::unique_ptr<T>` | propiedad exclusiva, move-only |
| `shared of T` | `std::shared_ptr<T>` | propiedad compartida, atómica |
| `weak of T` | `std::weak_ptr<T>` | observador sin propiedad |
| `many T` | `std::span<const T>` | solo en parámetros (§6.3); no copia |
| `fn` / `weave with T into U` | `U (*)(T)` | puntero a función |
| `(T, U)` | `std::tuple<T, U>` | tupla |
| `seal` | struct envoltorio nominal | §9.5 |
| `frozen T` | `const T` | solo en tipos de parámetro y campos |

**Aridad fija.** Cada constructor de tipo tiene una aridad: `vector` toma 1, `map` toma 2, `array` toma 2 (elemento y `size`), `ref` toma 1, etc. Los argumentos se separan por comas; un argumento que a su vez lleva comas va **entre paréntesis**:

```pengu-fragment
var a as map of int, string is {}
var b as Box of (map of int, string), string
```

```cpp
std::map<int32_t, std::string> a{};
Box<std::map<int32_t, std::string>, std::string> b{};
```

Una aridad incorrecta es `E0115`: `vector of int, string` y `map of int` no compilan.

`slice of T` era el nombre antiguo de `span of T`: **se retira** (§19.7). En un fuente viejo produce un error con fix-it a `span of T`; `slice` deja de ser palabra reservada.

**Sin `std::` en la sintaxis.** El emisor añade `std::`; el programador nunca lo escribe. El emisor sí puede cualificar cuando hace falta (`std::move`, `std::bit_cast`), pero eso es invisible en el fuente.

### 2.2.1 `vector of bool` es especial

`vector of bool` se emite `std::vector<bool>`, que **no guarda `bool` sino bits**. Es una ventaja de espacio y dos restricciones reales, que el lenguaje hace explícitas:

- `for b in xs` liga un **`bool` normal** dentro del cuerpo: el emisor escribe `for (auto&& _b : xs) { const bool b = _b; … }`. El binding es de solo lectura; el elemento se muta con `set xs at i is …`.
- **No hay dirección de un elemento**: `sigil of xs at i`, un `ref to bool` a un elemento, un `span of bool` construido desde el vector y `many bool` con el vector como argumento son **`E0127`**. Para mutar por referencia, usa `set` o cambia el tipo a `vector of byte`.
- Todo lo demás funciona igual: `xs at i` da `bool`, `set xs at i is true` compila, `xs.push`, comparar y recorrer.

```pengu
var flags as vector of bool is [true, false]
for f in flags:
    if f:
        calling print with "sí\n"
set flags at 1 is true
```

```cpp
std::vector<bool> flags{true, false};
for (auto&& _f : flags) {
    const bool f = _f;
    if (f) {
        print("sí\n");
    }
}
flags[1] = true;
```

### 2.3 Valor frente a referencia

| Forma | Semántica | Emisión |
|---|---|---|
| `T` | valor; se copia y se mueve | `T` |
| `ref to T` | préstamo mutable, no posee | `T*` |
| `ref to frozen T` | préstamo de solo lectura | `const T*` |
| `span of T` | vista contigua de elementos | `std::span<T>` |
| `unique of T` | propietario único | `std::unique_ptr<T>` |

Un valor se pasa **por valor** salvo que sea grande o haya que mutarlo; entonces se pasa `ref to T` (regla ya vigente en Pengunic: «valores primero, referencias cuando hacen falta»). El emisor decide el *modo* de paso, no la sintaxis:

- parámetro `T` de tipo trivial (≤16 bytes) → `T`.
- parámetro `T` de tipo grande (runas con contenedores) → `const T&` **solo si el sema garantiza que el cuerpo no lo reasigna**; si se reasigna, `T` por valor (ver R6 en la auditoría).
- parámetro `ref to T` → `T*`.
- retorno `T` → `T` (mover, no copiar).

---

## 3. Variables y constantes

### 3.1 Declaraciones

```pengu
var count as int is 0
let name as string is "Ada"
var xs is [1, 2, 3]              # tipo inferido del literal
let (q, r) is calling divmod with 7, 2
let Point { x, y } is p           # destructuring de rune
```

| Palabra | Mutabilidad | C++ |
|---|---|---|
| `var` | reasignable | `T nombre = …;` (o `T nombre{…};`) |
| `let` | no reasignable | `const T nombre = …;` |
| `const` | valor de tiempo de compilación, solo a nivel de módulo | `constexpr T nombre = …;` |
| `static var` | persistente entre llamadas | `static T nombre = …;` |

```cpp
int32_t count = 0;
const std::string name = "Ada";
std::vector<int32_t> xs{1, 2, 3};
auto [q, r] = divmod(7, 2);
Point p2 = p;                 // destructuring de rune: copia campo a campo
```

Un `let` sin tipo y sin valor inicial es `E0001`; un `var` sin tipo necesita valor inicial (`E0001`).

El **destructuring de rune** se emite campo a campo (no hay `auto [a, b]` sobre un struct ajeno):

```pengu
let Point { x, y } is p
```
```cpp
const int32_t x = p.x;
const int32_t y = p.y;
```

Un `let` de tipo contenedor es `const std::vector<T>`: se pueden leer sus elementos y llamar a sus métodos `const`, no modificarlo.

**`static var` dentro de un bucle** se inicializa **una sola vez**, en la primera ejecución del bloque (es un `static` de C++); las iteraciones siguientes ven el valor mutado. Por eso un `static var` dentro de un `for`/`while` acumula entre iteraciones y entre llamadas:

```pengu
weave next_id into int:
    static var id as int is 0
    set id += 1
    return id
```

```cpp
int32_t next_id() {
    static int32_t id = 0;
    id += 1;
    return id;
}
```

### 3.2 Asignación y `set`

```pengu-fragment
set count is count + 1
set count += 1                   # += -= *= /= %=
set name is "Grace"
```

```cpp
count = count + 1;
count += 1;
name = "Grace";                  // error de compilación: name es const
```

`set` sobre un `let` es `E0002`. Los operadores compuestos exigen el tipo del operador (`+=` sobre `string` es `+=` de C++, válido). Sobre un tipo de usuario, `+=` usa `operator+=` si existe (§4.8); si no, `E0117`.

### 3.3 Scope y shadowing

Un bloque crea un scope. Un nombre nuevo que oculta uno del scope exterior es `W0009` (aviso, no error). `set` busca el nombre en el scope actual y hacia fuera.

```pengu-fragment
var x as int is 1
if true:
    var x as string is "otra"    # W0009
```

En C++ esto es un scope real (`{ … }`), así que no hay que renombrar nada.

### 3.4 Garantías de seguridad y renuncias

El compilador comprueba tipos, aridad, exhaustividad de `judge` sobre `omen`/`bool`, límites de índice en `at` (§5.3), propiedad (`banish`, movimiento) y préstamos. **No** comprueba tiempos de vida, aliasing ni fugas: eso es del programador. Las vías de escape son `transmute`, `--release-unsafe` y `antiquus`.

---

## 4. Operadores

### 4.1 Precedencia

De mayor a menor:

| Nivel | Operadores |
|---|---|
| 1 | `.` (método/campo), `at`, llamada `calling … with` |
| 2 | `sigil of`, `essence of`, `size of`, `align of`, `bytes of`, `ord`, `chr`, `not` |
| 3 | `*`, `/`, `%` |
| 4 | `+`, `-` |
| 5 | `..`, `to` (rango solo dentro de `for … in`) |
| 6 | `<`, `<=`, `>`, `>=` |
| 7 | `==`, `!=` |
| 8 | `and` |
| 9 | `or` |
| 10 | `to` (cast) |
| 11 | `pipe` (solo inicio de línea) |

```pengu-fragment
let ok as bool is a + b * 2 < c and not d
```

```cpp
const bool ok = ((a + b * 2) < c) && (!d);
```

### 4.2 Aritmética y bit a bit

| Pengu | C++ |
|---|---|
| `a + b`, `a - b`, `a * b`, `a / b`, `a % b` | `+ - * / %` (misma precedencia) |
| `a and b`, `a or b`, `not a` | `&&`, `\|\|`, `!` |
| `a & b`, `a \| b`, `a ^ b`, `not a` (bit a bit con `~`) | `&`, `\|`, `^`, `~` |
| `a << b`, `a >> b` | `<<`, `>>` |

La división entera trunca hacia cero (igual que C++). Dividir por cero es comportamiento indefinido: no se comprueba.

### 4.3 Comparación, pertenencia y tests de palabras

```pengu-fragment
if a == b:
if a < b and b <= c:
if a != b:
if x is present:          # maybe
if "a" in m:              # pertenencia en map/set/umap/uset
if ch in "aeiou":         # pertenencia en string
```

```cpp
if (a == b) { }
if (a < b && b <= c) { }
if (a != b) { }
if (x.has_value()) { }
if (m.contains("a")) { }
if (std::string("aeiou").find(ch) != std::string::npos) { }
```

La pertenencia `in` sobre `map`/`set`/`umap`/`uset` es `contains`; sobre `vector`/`span`/`string` es una búsqueda lineal `std::find` (o `find` de `string`).

### 4.4 Dirección, desreferencia, tamaño

| Pengu | C++ | Notas |
|---|---|---|
| `sigil of x` | `&(x)` | dirección de un lugar; un elemento de `vector of bool` no tiene (`E0127`, §2.2.1) |
| `essence of p` | `*(p)` | desreferencia |
| `p at i` | `p[pengu::check_index(i, p.size(), "f", 12)]` | con comprobación de límites |
| `size of T` | `sizeof(T)` | tiempo de compilación |
| `align of T` | `alignof(T)` | tiempo de compilación |
| `bytes of x` | `std::as_bytes(std::span{x})` | vista de bytes |

```pengu
let n as int is size of Point        # 8
let a as int is align of Point       # 4
let b as ref to byte is bytes of p   # span de bytes
```

```cpp
const int32_t n = sizeof(Point);
const int32_t a = alignof(Point);
std::span<const std::byte> b = std::as_bytes(std::span{&p, 1});
```

### 4.5 Primitivas de carácter y byte

```pengu-fragment
let c as char is chr 65        # 'A'
let n as int is ord 'A'        # 65
```

```cpp
const char c = static_cast<char>(65);
const int32_t n = static_cast<int32_t>('A');
```

### 4.6 Casts y conversiones

Hay tres conversiones y **ninguna es implícita** entre tipos numéricos:

| Forma | Qué hace | C++ |
|---|---|---|
| `x to T` | conversión estática, puede truncar | `static_cast<T>(x)` |
| `x as T` | estrecha un valor opcional o un omen en una condición | `if (auto* p = …)` (§5.1) |
| `transmute x to T` | reinterpreta bytes (mismo tamaño o menor) | `std::bit_cast<T>(x)` si los tamaños coinciden; si `T` es menor, `memcpy` de los primeros bytes |

```pengu-fragment
let small as byte is big to byte       # trunca en silencio
let f as float is 3 to float
```

```cpp
const uint8_t small = static_cast<uint8_t>(big);
const float f = static_cast<float>(3);
```

`transmute` exige que `sizeof(T) <= sizeof(x)`; si `sizeof(T) > sizeof(x)` es **`E0133`** (§19.3), un error y no un warning, porque el destino no se puede rellenar y `std::bit_cast` ni siquiera compila. Avisa `W0001` porque el resultado depende de la representación. El emisor elige la forma según los tamaños, porque **`std::bit_cast` exige que coincidan**:

| Caso | Emisión |
|---|---|
| `sizeof(T) == sizeof(x)` y ambos triviales | `std::bit_cast<T>(x)` |
| `sizeof(T) < sizeof(x)` | `T _r{}; std::memcpy(&_r, &x, sizeof _r);` — copia los primeros bytes (en little-endian, los de menor peso) |
| alguno no es trivialmente copiable | igual que el caso anterior (con `memcpy`), y el resultado es *implementation-defined* |

```pengu
transmute bits to float            # u32 → float: mismo tamaño
transmute wide to float            # u64 → float: T es menor
```
```cpp
const float r = std::bit_cast<float>(bits);

float _r{};
std::memcpy(&_r, &wide, sizeof _r);
```

Un cast entre `seal` y su tipo base **sí** es explícito y obligatorio (§9.5, `E0112`).

### 4.7 `defined`, `size of` y valores de tiempo de compilación

`defined(NAME)` comprueba un `-D` del compilador; se resuelve en tiempo de compilación y **desaparece** del C++ emitido (la rama no tomada no se emite). `size of`, `align of` y `const` son igualmente de tiempo de compilación.

```pengu-fragment
when defined(PENGU_DEBUG):
    calling log with "debug"
```

```cpp
// si PENGU_DEBUG está definido:
log("debug");
```

**`when` a nivel de módulo.** Una declaración (no solo una sentencia) puede ir bajo `when defined(...)`: el compilador evalúa la condición y **solo emite la rama tomada**, así que en el `.cpp` no aparece ningún `#ifdef`.

```pengu
when defined(LINUX):
    weave platform_init into void:
        calling linux_init
else:
    weave platform_init into void:
        calling generic_init
```

```cpp
// en Linux, el .cpp contiene solo esto:
void platform_init() { linux_init(); }
```

Reglas: la condición es una expresión constante de tiempo de compilación (`defined` y aritmética/`and`/`or`/`not` sobre ella); `else:` es opcional; las dos ramas deben declarar el mismo nombre con la misma firma si se van a usar desde fuera; un `import` **no** puede ir bajo `when`.

### 4.8 Sobrecarga de operadores

Un tipo puede declarar operadores dentro de `enchanting`. La sintaxis es `operator <símbolo>`:

```pengu
rune Vec2:
    x as float
    y as float

enchanting Vec2:
    weave operator + with other as Vec2 into Vec2:
        return with x is self->x + other.x, y is self->y + other.y

    weave operator += with other as Vec2 into void:
        set self->x is self->x + other.x
        set self->y is self->y + other.y

    weave operator [] with i as int into ref to float:
        if i == 0:
            return sigil of self->x
        return sigil of self->y
```

```cpp
struct Vec2 {
    float x;
    float y;

    Vec2 operator+(const Vec2& other) const { return Vec2{this->x + other.x, this->y + other.y}; }
    Vec2& operator+=(const Vec2& other) { this->x += other.x; this->y += other.y; return *this; }
    float& operator[](int32_t i) { return i == 0 ? this->x : this->y; }
    const float& operator[](int32_t i) const { return i == 0 ? this->x : this->y; }
    // == y <=> son automáticos: el emisor los escribe siempre
    bool operator==(const Vec2&) const = default;
    auto operator<=>(const Vec2&) const = default;
};
```

Reglas:

1. **Símbolos declarables**: `+`, `-`, `*`, `/`, `%`, `==`, `<=>`, `[]`, `()`, `+=`, `-=`, `*=`, `/=`, `%=`.
2. **`!=`, `<`, `<=`, `>`, `>=` no se declaran**: C++20 los deriva de `==` y `<=>`. Si escribes `operator !=` es `E0117`, con el consejo de declarar `==`.
3. **`operator ==` y `operator <=>` son automáticos** en toda runa (comparación campo a campo) y el emisor los escribe siempre con `= default`; no hay que declararlos. Si los declaras, mandan los tuyos. `@no_cmp` los desactiva y hace que comparar sea `E0117`.
4. **Firma**: los operadores binarios toman el otro operando por valor (`const T&` en el emit); los de asignación devuelven `void` en Pengu y se emiten devolviendo la referencia (`T&`), como exige C++.
5. **`operator []`**: se emiten **dos** sobrecargas, `T&` y `const T&`, para que funcione también sobre un `ref to frozen T`. Se declara una vez y el emisor duplica la firma con `const`.
6. **Sin conversiones implícitas**: no hay `operator T()`. Para convertir, se usa `x to T` con un `weave to` (§10.1) y un cast explícito.
7. Un operador declarado en un tipo que no es de usuario (p. ej. `enchanting int:`) es `E0117`.

El cuerpo de `operator []` suele necesitar dos variantes por el `const`; en Pengu se escribe una sola y el emisor duplica la firma con `const` y sin él.

#### Llamar a un valor: `operator ()`

`operator ()` es el **operador de llamada** de C++. Un tipo que lo declara se puede llamar como una función; desde Pengu la llamada es `calling <valor> with <args>`, sin nombre de método:

```pengu
rune Adder:
    base as int

enchanting Adder:
    weave operator () with x as int into int:
        return self->base + x

var a as Adder is with base is 10
let r as int is calling a with 5      # 15
```

```cpp
struct Adder {
    int32_t base;
    int32_t operator()(int32_t x) const { return this->base + x; }
};

Adder a = Adder{.base = 10};
const int32_t r = a(5);
```

Reglas:

- La firma es `weave operator () with <params> into T`; el emisor escribe `T operator()(<params>) const` (o sin `const` si el cuerpo muta `self`).
- Se llama con `calling a with 5`, igual que una función: el receptor es el valor y no lleva `.método`.
- Un tipo con `operator ()` **no** es un puntero a función y **no** se puede pasar a un `declare` que espere `fn` (§6.4): para eso se envuelve en un `weave` normal y se pasa esa función.
- Solo los tipos de usuario lo pueden declarar (`E0117` fuera de ellos), y como `==`/`<=>`, no hay versión automática.

---

## 5. Control de flujo

### 5.1 `if`, `unless` y bindings de `if`

```pengu
if x > 0:
    calling print with "positivo\n"
else if x < 0:
    calling print with "negativo\n"
else:
    calling print with "cero\n"

unless done:
    calling tick with 1
```

```cpp
if (x > 0) {
    print("positivo\n");
} else if (x < 0) {
    print("negativo\n");
} else {
    print("cero\n");
}

if (!done) {
    tick(1);
}
```

Un `if` puede **ligar** un valor estrechado y usarlo en el cuerpo:

```pengu
if v as maybe of int is some:
    calling print with "{v}"          # v es int
if r as result of int to string is ok:
    calling print with "{r}"          # r es int
if e as result of int to string is err:
    calling print with "{e}"          # e es string
```

```cpp
if (auto v = pengu::some_value(m, __FILE__, __LINE__)) {
    print(std::to_string(*v));
}
if (auto r = pengu::result_ok_value(res, __FILE__, __LINE__)) {
    print(std::to_string(*r));
}
if (auto e = pengu::result_err_value(res, __FILE__, __LINE__)) {
    print(*e);
}
```

Reglas:

- El binding es **inmutable** y vive solo en el cuerpo del `if`.
- `as maybe of T is some` liga el valor; `is none` no liga.
- `as result of T to E is ok` liga el valor; `is err` liga el error (§12.3).
- Las tres formas se emiten con `if (auto … = …)` y el cuerpo dentro del `if`, sin temporales fuera. El emisor usa las funciones de `pengu/core.hpp`, no `.value()` ni `.at()`: esas lanzarían y el lenguaje no tiene excepciones (§12.3).
- El estrechamiento de un `omen` con payload es un `judge` con `as` (§5.4), no un `if`.
- Un `else` que liga el caso contrario se escribe `else:` y usa la variable del primer binding solo si es válida; si no, no se liga.

Un `if`/`unless` es también **expresión** cuando las dos ramas dan valor (§5.6):

```pengu
let msg as string is if retries > 3 then "rinde" else "sigue"
let note as string is unless ok then "fallo" else "bien"
```

```cpp
const std::string msg = (retries > 3) ? std::string{"rinde"} : std::string{"sigue"};
const std::string note = !(ok) ? std::string{"fallo"} : std::string{"bien"};
```

- Las **dos** ramas son obligatorias, también en `unless`. Sin `else`, `unless` es solo sentencia y descarta el valor.
- Los tipos de las dos ramas deben unificar; si una es `ref to T` y la otra `T`, unifica a `T` y se copia el valor (la copia se ve, §2.1).
- `else if` encadena ternarios: `c1 ? a : (c2 ? b : c)`.
- Con cuerpo de bloque, la forma de valor es un IIFE (§5.6).

### 5.2 `while`

```pengu
while n > 0:
    set n is n - 1
```

```cpp
while (n > 0) {
    n = n - 1;
}
```

No hay `do`/`while` ni `loop`; se escribe `while true:`.

### 5.3 `for`

```pengu-fragment
for i from 0 to 10:
    calling tick with i

for i from 10 to 0 step -1:
    calling tick with i

for item in items:
    calling handle with item

for i, item in indexed:
    calling handle with i

for _, v in values:
    calling handle with v
```

| Forma | Itera sobre | Elemento |
|---|---|---|
| `for i from a to b` | `[a, b)` | `int` |
| `… step k` | rango con paso (negativo desciende) | `int` |
| `for x in vector` | `vector of T` | `T` |
| `for x in array` | `array of T with size N` | `T` |
| `for x in span` | `span of T` | `T` |
| `for ch in s` | `string` | `char` (un byte) |
| `for k in map` | claves, en orden ascendente | `K` |
| `for k, v in map` | clave y valor, en orden ascendente | `K`, `V` |
| `for k in umap` | claves, en orden de hash (no especificado) | `K` |
| `for i, v in vec` | índice + elemento | `size_t`, `T` |
| `for x in a to b` | rango entero `[a, b)` | `int` |

```cpp
for (int32_t i = 0; i < 10; i++) { tick(i); }

for (int32_t i = 10; i > 0; i += -1) { tick(i); }

for (auto&& item : items) { handle(item); }

for (size_t i = 0; i < indexed.size(); ++i) {
    auto&& item = indexed[i];
    handle(i);
}

for (char ch : s) { handle(ch); }

for (auto&& [k, v] : m) { handle_key(k); }

for (auto&& v : values) { handle(v); }
```

`for ch in s` da un **`char`**, no un `string` de un byte: es el cambio de comportamiento más visible (§19.5). Para obtener un `string` de un byte, `calling s.substr with i, 1` (§2.19 de la auditoría).

La forma con índice exige nombres distintos (`E0037`); `_` descarta cualquiera de los dos. El índice es `size_t`. La forma con índice se emite como **bucle contado** (`for (size_t i = 0; i < c.size(); ++i)`) y el elemento se liga dentro con `auto&& item = c[i];`: así un `continue` en el cuerpo no desincroniza el índice, y el nombre del índice es el que escribió el usuario, sin sombras. Cuando el índice se descarta (`for _, v in values`), el emisor no cuenta nada y usa un range-for normal.

Borrar el índice **no** vale para `umap`: su orden de hash no es estable entre ejecuciones y no se debe usar como índice.

**Orden de `map`.** `for k in map` y `for k, v in map` recorren en el orden de `std::map`: por el `operator<` de la clave. Para una `rune`, el `<=>` automático campo a campo (orden de declaración); para un `seal`, el `<=>` del valor envuelto; para un `int`/`string`, el orden natural. Un `map` cuya clave no sea ordenable es `E0104` (§10.6).

**El binding no cambia de tipo.** `for x in xs` liga `x` con el tipo del elemento y no se puede forzar otro: `for x as byte in xs` es un error de sintaxis. Para convertir, liga un nombre y castea dentro del cuerpo.

**Comprensiones.** Construyen un contenedor a partir de una expresión:

```pengu
let squares as vector of int is for x in nums then x * x
let evens as vector of int is for x in nums when x % 2 == 0 then x
```

```cpp
std::vector<int32_t> squares = [&] {
    std::vector<int32_t> _r;
    for (auto&& x : nums) { _r.push_back(x * x); }
    return _r;
}();
```

La comprensión se emite como una **lambda invocada en el acto** (IIFE) que devuelve el contenedor; el tipo del contenedor sale de la anotación. Sin anotación, el compilador lo infiere del primer `push` y es `E0076` si no puede.

#### 5.3.1 `for` como expresión

La comprensión de una sola expresión es el caso corto de una forma general: un `for` con **cuerpo de bloque** en posición de valor. El valor de cada iteración es la última expresión del cuerpo; las iteraciones que no llegan a esa expresión no aportan nada.

```pengu
let results as vector of int is for x in xs:
    var y as int is x * 2
    y + 1
```

```cpp
const std::vector<int32_t> results = [&] {
    std::vector<int32_t> _r;
    for (auto&& x : xs) {
        int32_t y = x * 2;
        _r.push_back(y + 1);
    }
    return _r;
}();
```

Reglas:

- La anotación (`as vector of T`, `as map of K, V`) fija el contenedor de salida; sin anotación se infiere del primer `push`/`insert_or_assign` y es `E0076` si no hay ninguno.
- El contenedor se crea vacío dentro del IIFE y **no** se puede usar otra salida: no hay acumulador explícito para `vector` (para eso está `while`, §5.6.1).
- `when` actúa de guarda y se emite como `continue`: `for x in xs when x % 2 == 0:` equivale a `if (!(x % 2 == 0)) continue;` como primera sentencia del cuerpo.
- Cualquier forma de iteración vale: `for i from 0 to 10:`, `for x in xs:`, `for i, x in indexed:`, `for k, v in m:`. Las formas con índice emiten el bucle contado de §5.3.
- `break` cierra la construcción y devuelve lo acumulado hasta ahí; `continue` salta la iteración sin acumular (§5.5). `return` dentro del cuerpo es `E0100`, y `break`/`continue` que tendrían que cruzar el límite del IIFE son `E0126`.
- La última sentencia del cuerpo puede no ser una expresión (`set`, `banish`, un `if` sin `else`): en ese caso la iteración no acumula y el emisor no emite `_r.push_back`.
- El IIFE captura por referencia (`[&]`), así que el cuerpo ve y muta los locales de la función, igual que el código escrito a mano.

**Comprensión de `map`.** Si la anotación es `map of K, V` (o `umap of K, V`), el valor de la iteración es una **tupla `(clave, valor)`** y el emisor inserta con `insert_or_assign`:

```pengu
let by_name as map of string, int is for k, v in by_id then (v, k)
```

```cpp
const std::map<std::string, int32_t> by_name = [&] {
    std::map<std::string, int32_t> _r;
    for (auto&& [k, v] : by_id) {
        auto _e = std::make_pair(v, k);
        _r.insert_or_assign(std::get<0>(_e), std::get<1>(_e));
    }
    return _r;
}();
```

Si el valor de la iteración **no** es una tupla de dos elementos y la anotación es `map`/`umap`, es **`E0131`** (no se inventa una clave ni se envuelve en una tupla de uno). Un `set of T`/`uset of T` como anotación de una comprensión tampoco vale: para eso se acumula en un `vector` y se inserta con `set.insert` (§2.7 de la auditoría).

Un `umap of K, V` sale como `std::unordered_map` y necesita `Vinculum` en la clave (§10.6); un `map`/`set` necesita clave ordenable (`E0104`).

### 5.4 `judge` — coincidencia de patrones

```pengu
let desc as string is judge state:
    when Ready -> "ready"
    when Loading -> "loading"
    when Done -> "done"
    else -> "unknown"
```

Sujetos: `omen`, `bool`, `int`, `string`, `char`.

| Patrón | Ejemplo |
|---|---|
| Variante desnuda | `when Ready ->` |
| Variante cualificada | `when Phase.Ready ->` |
| Nombre C completo | `when Phase_Ready ->` |
| Literal | `when 42 ->`, `when "admin" ->`, `when 'X' ->` |
| Alternativas | `when Ready \| Loading ->` |
| Binding de payload | `when Ok with value ->` |
| Guarda | `when Val with n if n > 0 ->` |
| Defecto | `else ->` |

La exhaustividad se exige para `omen` y `bool` (`E0044`); para `int`, `string` y `char`, un caso ausente produce el valor cero salvo que haya `else ->`. Un brazo con guarda no cuenta como cobertura.

**`judge` en posición de valor.** Cuando el `judge` es una expresión, el `else ->` es obligatorio salvo que el sujeto sea exhaustivo por sí mismo: un `omen` con todas sus variantes cubiertas, o un `bool` con `true` y `false`, y sin guardas. Si falta un caso, `E0044`.

```pengu
let name as string is judge code:
    when 1 -> "uno"
    when 7 -> "siete"
    else -> "otro"
```

```cpp
const std::string name = [&]() -> std::string {
    if (code == 1) { return "uno"; }
    if (code == 7) { return "siete"; }
    return "otro";
}();
```

Con un sujeto exhaustivo el emisor **no** genera `default:`; después del `switch` escribe una llamada a `pengu::panic` para que la función tenga un camino de salida y el compilador no avise de «control reaches end of non-void function»:

```pengu
let st as string is judge state:
    when Ready -> "ready"
    when Loading -> "loading"
    when Done -> "done"
```

```cpp
const std::string st = [&]() -> std::string {
    switch (state) {
        case State::Ready: return "ready";
        case State::Loading: return "loading";
        case State::Done: return "done";
    }
    pengu::panic("judge no exhaustivo", __FILE__, __LINE__);
}();
```

El `panic` es inalcanzable si el `omen` está completo (lo garantiza `E0044`) y cubre el caso de un valor corrupto que llegue desde `antiquus` o desde C.

`judge` también es sentencia (sin posición de valor); cada brazo corre por sus efectos. Las guardas se evalúan de arriba abajo y un brazo guardado que no se cumple pasa al siguiente que case.

```pengu
omen State:
    Ready is 0
    Loading is 1
    Done is 2

weave handle with state as State:
    judge state:
        when Ready ->
            calling print with "run\n"
        when Loading | Done ->
            calling print with "waiting\n"
        else ->
            calling print with "unknown\n"
```

```cpp
void handle(State state) {
    switch (state) {
        case State::Ready: print("run\n"); break;
        case State::Loading:
        case State::Done: print("waiting\n"); break;
        default: print("unknown\n"); break;
    }
}
```

Un sujeto `bool` se emite como `if`/`else if` (no `switch`, para no duplicar `case`). Un sujeto `string` o `char` se emite como cadena de `if` con `==`. Un brazo con guarda se emite como `if (cond) { … } else if (…)`.

**`judge … over`** hace coincidir un rune cuyo discriminante es uno de sus campos:

```pengu
rune Expr:
    kind as ExprKind
    value as int

omen ExprKind:
    Lit is 0
    Add is 1

weave eval with e as ref to Expr into int:
    return judge e over kind:
        when Lit with value -> value
        when Add -> 0
```

```cpp
int32_t eval(Expr* e) {
    switch (e->kind) {
        case ExprKind::Lit: { int32_t value = e->value; return value; }
        case ExprKind::Add: { return 0; }
    }
    pengu::panic("judge no exhaustivo", __FILE__, __LINE__);
}
```

`over` es contextual: `var over as int is 5` sigue compilando. Admite payloads estrechados (`field as some`, `field as ok`, `field as (a, b)`).

**Omens algebraicos.** Un `omen` con variantes que llevan datos se emite como `std::variant` con un `monostate` para la variante vacía (§9.4):

```pengu
omen Slot:
    Empty
    Filled with text as string

weave describe with s as Slot into string:
    return judge s:
        when Empty -> "vacío"
        when Filled with t -> t
```

```cpp
std::string describe(Slot s) {
    switch (s.data.index()) {
        case 0: { return "vacío"; }
        case 1: { std::string t = std::get<1>(s.data); return t; }
    }
    pengu::panic("judge no exhaustivo", __FILE__, __LINE__);
}
```

### 5.5 `break`, `continue`, `return`

`break` y `continue` requieren un bucle que los contenga (`E0007`). `return` debe coincidir con el tipo del `into` (`E0020`); un `return` desnudo solo es válido en un `weave` `void`.

```pengu-fragment
outer: for line in lines:
    for ch in line:
        if ch == ";":
            continue outer
        if ch == "}":
            break outer
```

```cpp
for (auto&& line : lines) {
    for (char ch : line) {
        if (ch == ';') { goto _pengu_label_outer_continue; }
        if (ch == '}') { goto _pengu_label_outer_break; }
    }
    _pengu_label_outer_continue: continue;
}
_pengu_label_outer_break: ;
```

Las etiquetas son locales a la función, únicas por función (`E0069`). En C++ se emiten con `goto` a etiquetas al final del bucle, y los `defer` del scope del bucle se ejecutan antes del salto (el emisor envuelve el bucle en un bloque con sus guardas).

#### 5.5.1 Control de flujo dentro de expresiones de bucle

Cuando un `for` o un `while` es una **expresión** (§5.3.1, §5.6.1), el cuerpo está dentro de un IIFE y estas sentencias cambian de significado:

| Sentencia | En un `for`/`while` que es expresión |
|---|---|
| `break` | cierra el bucle y devuelve **lo acumulado hasta ahí** (un contenedor parcial es válido). |
| `continue` | salta la iteración y **no** acumula valor. |
| `return` | `E0100`: un `return` pertenece a la función, no a la expresión. |
| `break`/`continue` de un bucle **externo** | `E0126`: el IIFE es una frontera; no se puede saltar fuera de la expresión. |
| `defer` | corre al salir de su bloque dentro del cuerpo; el `break` ejecuta los `defer` del scope abandonado. |

Para salir de un bucle externo desde dentro de una expresión de bucle, la expresión se guarda en una variable y el salto se hace fuera:

```pengu
var found as maybe of int is none
for line in lines:
    let hits as vector of char is for ch in line when ch == '#':
        ch
    if calling hits.size > 0:
        set found is some 1
        break
```

### 5.6 Expresiones de bloque

Una comprensión, el condicional de una línea (`if c then a else b`) y un **bloque indentado** en posición de valor son valores. `do:` y un `if`/`unless` multilínea evalúan a su última expresión; las sentencias anteriores corren en el scope del bloque.

```pengu
weave main into int:
    let v as int is do:
        var a as int is 5
        a + 4
    let w as int is if v > 0:
        1
    else:
        0
    calling print with "{v} {w}"    # 9 1
    return 0
```

```cpp
const int32_t v = [&]() -> int32_t {
    int32_t a = 5;
    return a + 4;
}();
const int32_t w = (v > 0) ? 1 : 0;
print(pengu::format("%d %d", v, w));
```

Un `if` de una línea (`if c then a else b`) **siempre** lleva `else`: es una expresión y necesita valor en las dos ramas. Para un `if` de una línea sin `else` se usa la forma de sentencia (§5.1). `unless` sigue la misma regla, con el sentido invertido: `unless c then a else b` (§5.1).

`for` y `while` **sí** son expresiones cuando producen un contenedor (§5.3.1 y §5.6.1). Un bucle usado como sentencia no produce valor; para construir un valor con un bucle dentro sin acumular, se usa `do:`.

Los bloques bajan a **IIFE** (`[&] { … }()`), no a sentencias-expresión de GNU: así compilan g++, clang++ y MSVC. Un `return` dentro de un bloque en posición de valor es `E0100`/`E0101` (un `return` pertenece a la función, no al bloque); para salir del bloque se usa `do:` como último valor o se reestructura con una variable.

`defer` dentro del bloque se ejecuta al salir del bloque (el IIFE crea un scope y su guarda corre en su destructor). Un bucle en posición de valor (`for x in xs then expr`) recoge cada iteración en un nuevo `vector of T` (comprensión).

#### 5.6.1 `while` como expresión

Un `while` en posición de valor acumula en un `vector of T` el valor de la última expresión de cada iteración:

```pengu
var n as int is 0
let evens as vector of int is while n < 10:
    set n += 1
    if n % 2 != 0:
        continue
    n
```

```cpp
int32_t n = 0;
const std::vector<int32_t> evens = [&] {
    std::vector<int32_t> _r;
    while (n < 10) {
        n += 1;
        if (n % 2 != 0) { continue; }
        _r.push_back(n);
    }
    return _r;
}();
```

- La anotación es obligatoria (`as vector of T`): un `while` puede no ejecutarse nunca y no hay primer `push` del que inferir el tipo (`E0076`).
- Solo `vector of T`: `map`, `umap`, `set`, `uset`, `array` o cualquier otra anotación son **`E0076`** (y sin anotación también). Para un `map` se usa un `for` sobre una colección o se construye con `set` sobre un `map` vacío.
- El cuerpo debe terminar en expresión en las rutas que acumulan; un `continue` o un `if` sin `else` al final no acumulan.
- `break` devuelve lo acumulado; `return` es `E0100`; cruzar una frontera de expresión es `E0126` (§5.5).
- Si el bucle no termina, tampoco termina la expresión: el IIFE no cambia el control de flujo.

### 5.7 `with` como sentencia

Un bloque `with` nombra un receptor una vez y permite abordarlo con `.campo` y `calling .metodo`:

```pengu
rune Point:
    x as int
    y as int

enchanting Point:
    weave shift with dx as int, dy as int into void:
        set self->x is self->x + dx
        set self->y is self->y + dy

weave main into int:
    var p as Point is with x is 1, y is 2
    with p:
        var y0 as int is .y
        set .x is .x + 1
        calling .shift with 2, 1
    return p.x + p.y
```

```cpp
Point p = Point{.x = 1, .y = 2};
{
    auto& _w0 = p;
    int32_t y0 = _w0.y;
    _w0.x = _w0.x + 1;
    Point_shift(&_w0, 2, 1);
}
return p.x + p.y;
```

El objetivo se evalúa **una vez** y debe ser un lugar direccionable (variable, campo, elemento, préstamo); si no, `E0077`. `.campo` lee o escribe; `calling .metodo` despacha según el tipo.

**Anidado.** Un `with` puede contener otro `with`, y el receptor interno se resuelve contra el `.campo` del externo:

```pengu
with enemy:
    set .health is .health - 10
    with .position:
        set .x is .x + 1.0
```

```cpp
{
    auto& _w0 = enemy;
    _w0.health = _w0.health - 10;
    {
        auto& _w1 = _w0.position;
        _w1.x = _w1.x + 1.0;
    }
}
```

Si el receptor es un `ref to T`, el `.` lo desreferencia: `auto& _w0 = *enemy;`. Sobre un `vector`, `map` o `string` el cuerpo llama a los métodos incorporados (`calling .push with 4`, `calling .put with "k", 1`).

Un builder `with` en posición de valor (`var p as Point with: …`) es §9.8.

### 5.8 Lo que MoonScript tiene y aquí no entra

PenguScript toma de MoonScript las expresiones de bloque, los constructores con `with`, los valores por defecto y los bucles como valor; lo que no entra es lo que C++ no puede emitir de forma predecible sin cambiar el modelo de propiedad:

| MoonScript | En PenguScript |
|---|---|
| `class`, `extends`, `super`, `@@` | no hay clases: `rune`/`omen` + `inherit` sin `virtual`; el despacho es estático (§9.9) |
| `a, b = b, a` (asignación múltiple) | `set a, b is b, a` no existe; usa una tupla: `let (x, y) is (b, a)` y `set a is x` / `set b is y` |
| `for` con varias cláusulas (`for x in xs for y in ys`) | anida dos expresiones de bucle o escribe dos `for` con una variable acumuladora |
| `switch` con *fallthrough* | `judge` no cae en el brazo siguiente; agrupa variantes con `\|` |
| `^` como *self* corto | `self` (§9.3) |
| `s\sub 1, 3`, `#s` | `calling s.substr with 1, 3`, `calling s.size` (§2.19 de la auditoría) |
| `import` de tablas | `import` de módulos, un archivo por módulo (§7) |

---

## 6. Funciones

### 6.1 `weave`

```pengu
weave greet with name as string, times as int is 2 into void:
    for _ in 0 to times:
        calling print with "hola, {name}\n"

weave add with a as int, b as int into int:
    return a + b

weave max0 with a as int, b as int into int:
    if a > b:
        a
    else:
        b
```

```cpp
void greet(const std::string& name, int32_t times = 2) {
    for (int32_t _ = 0; _ < times; _++) {
        print(pengu::format("hola, %s\n", name.c_str()));
    }
}

int32_t add(int32_t a, int32_t b) {
    return a + b;
}

int32_t max0(int32_t a, int32_t b) {
    return a > b ? a : b;
}
```

Reglas:

- `with` introduce parámetros; `into T` el retorno. Sin `into`, el retorno es `void`.
- Un parámetro con `is` tiene **valor por defecto**: debe ser una constante de compilación y encajar con el tipo (`E0073`), y se emite como `= valor` en la firma. Los que llevan default van al final; uno sin default después de uno con default es `E0072`.
- Los defaults se escriben **una vez, en la firma**, y las llamadas simplemente omiten el argumento: no se reevalúan por llamada (en el backend C se plegaban en la llamada, §19.5).
- La misma regla vale para todo lo que tiene parámetros: `born` (§9.3), `ritual` (§6.6), `declare` (§6.4) y `antiquus` (§8.6).
- La última **expresión** del cuerpo es el valor de retorno (retorno implícito) y se emite como `return`.
- Los parámetros son `const` para punteros a datos que no se mutan; `ref to T` se emite `T*` (puede ser `nullptr`: el contrato es del programador).
- `inline` delante de `weave` fuerza `inline` en C++ (solo para funciones de cabecera).

Sin `into`, el retorno es `void`: si la última sentencia del cuerpo es una expresión, el emisor la envuelve en `(void)` para que `-Wunused-value` no avise. Un `return` con valor en un `weave` `void` es `E0020`.

### 6.2 Convenciones de llamada

```pengu-fragment
calling greet with "Ada", 3         # función libre
calling spark.println with "hi"     # cualificada por módulo
calling player.heal with 25         # método sobre un valor
calling Player.new_hero with "Ada"  # ritual (estático), sobre el tipo
calling items.push with 4           # método de contenedor
```

```cpp
greet("Ada", 3);
spark::println("hi");
player.heal(25);
Player::new_hero("Ada");
items.push_back(4);
```

Un argumento nombrado se une a su parámetro **por nombre, en cualquier orden**; el emisor los coloca en el orden de la declaración:

```pengu
calling greet with "Ada", times is 3
calling greet with times is 3, name is "Ada"
```

```cpp
greet("Ada", 3);
```

- Los posicionales van primero; un posicional después de un nombrado es `E0071`.
- Cada parámetro se cubre como mucho una vez (`E0071`).
- Dejar un parámetro sin defecto sin cubrir, o pasar de más, es `E0005`.
- Los pasos de cadena y de pipe solo aceptan posicionales (`E0071`).

**Métodos sin paréntesis.** En la sintaxis del lenguaje no se escriben paréntesis: `s.len` es una llamada sin argumentos y `calling s.at with i` es una llamada con uno. El emisor traduce:

```pengu-fragment
let n as int is xs.len
calling xs.push with 4
calling m.put with "k", 1
```

```cpp
const int32_t n = xs.size();
xs.push_back(4);
m.insert_or_assign("k", 1);
```

La tabla completa de operaciones que el compilador conoce está en §2.19 de la auditoría: `.len`, `at`, `push`, `pop`, `put`, `remove`, `contains`, `keys`, `values`, `clear`. Todo lo demás es API de módulo y **no se traduce**: si `std.scrolls` define `split`, el emit es `s.split(...)`.

### 6.3 Parámetros variádicos

```pengu
weave sum with xs as many int into int:
    var total as int is 0
    for x in xs:
        set total is total + x
    return total
```

```cpp
int32_t sum(std::span<const int32_t> xs) {
    int32_t total = 0;
    for (auto&& x : xs) {
        total = total + x;
    }
    return total;
}
```

`many T` es **solo** para parámetros y llega como `std::span<const T>`: es un **préstamo**, no una copia. Se llama de dos maneras, y el emisor elige:

- con valores sueltos (`calling sum with 1, 2, 3`), envuelve los argumentos en un `std::array` temporal, que vive hasta el final de la llamada;
- con un contenedor existente (`calling sum with xs`), pasa la vista directamente, sin copiar (también vale un `array`, un `span` o una `vector`).

Un `vector of bool` **no** se puede pasar a `many bool` (`E0127`, §2.2.1): `std::vector<bool>` no expone `bool*`.

```pengu
calling sum with 1, 2, 3
calling sum with xs
```

```cpp
sum(std::array<int32_t, 3>{1, 2, 3});
sum(xs);
```

No confundir con `span of T`: `span` es un tipo de primera clase que se puede guardar y devolver; un `many T` es **azúcar de firma**, no se puede devolver ni guardar, y solo existe en parámetros. Un `std::initializer_list` no serviría: no acepta un `vector` existente sin copiar, y el préstamo es una de las razones de ser de `many`.

Varargs de C (`...`) existen **solo dentro de `extern c`** y solo para funciones de la frontera (§8.2).

### 6.4 Declaraciones externas: `extern c` y `extern cpp`

Toda función externa se declara dentro de un bloque `extern`. Un `declare` suelto es `E0116`.

```pengu
extern c:
    declare pengu_print with s as string into void
    declare strlen_c with s as ref to char into usize
    declare printf with fmt as ref to frozen char, ... into int

extern cpp:
    include <mylib/mylib.hpp>
    regnum mylib
    declare open with path as ref to frozen char into ref to opaque
    declare close with h as ref to opaque into void
```

```cpp
extern "C" {
    void pengu_print(const char* s, int32_t len);
    size_t strlen_c(char* s);
    int32_t printf(const char* fmt, ...);
}

#include <mylib/mylib.hpp>
void* mylib::open(const char* path);
void mylib::close(void* h);
```

Reglas:

1. `extern c` emite `extern "C" { … }` y prohíbe los tipos que no tienen ABI C (`E0110`): `string`, `vector`, `map`, `umap`, `set`, `uset`, `array`, `span`, `maybe`, `result`, `many`, `seal`, tuplas.
2. `extern cpp` emite declaraciones de C++ **sin** `extern "C"`; acepta cualquier tipo del lenguaje.
3. `regnum ns` declara el namespace de C++ en el que viven los `declare` siguientes; es **por bloque** y no se hereda entre bloques. Solo dentro de `extern cpp`; fuera es `E0116`, y dentro de `extern c` es `E0108`.
4. `regnum` **no crea** el namespace: solo cualifica las declaraciones. Escribir `namespace milyb { … }` es ilegal (UB reabrir `std`, y Pengu no lo hace).
5. El nombre de la función no se traduce; si quieres un nombre Pengu distinto, declara un alias con `weave` encima (§10.1).
6. `include`, `link`, `ldflag`, `insignia` y `regnum` tienen sitio fijo (tabla siguiente). `include` se emite arriba del todo, una sola vez, y en el orden en que aparece.
7. `insignia` prefija los símbolos que el módulo **exporta** (`@export`, `extern c`); **no** toca los `declare` de `extern cpp`, que conservan su nombre y su namespace originales (§1.4 y §6.4.1).
8. `extern c` y `extern cpp` pueden convivir en el mismo módulo y en el mismo archivo.
9. Un `declare` acepta `is` para un **argumento por defecto de C++** (`declare f with x as int is 5`). Se emite solo en la declaración, no forma parte del símbolo y el emisor no lo repite en la llamada. Debe ser constante (`E0073`) y no puede servir para saltarse un parámetro intermedio: como en C++, los defaults van al final (`E0072`). Con `...` van antes de los puntos suspensivos. Un `declare` que se usa como **puntero a función** (se pasa como valor) no admite defaults: C++ no los permite en un tipo.

```pengu
extern c:
    declare compute with a as int, b as int is 10 into int
```

```cpp
extern "C" {
    int32_t compute(int32_t a, int32_t b = 10);
}

compute(4);        // b = 10
compute(4, 3);     // b = 3
```

| Directiva | Dónde va | Emisión |
|---|---|---|
| `include <stdio.h>` (cabecera C) | nivel de módulo | `#include <stdio.h>` al principio del `.cpp` |
| `include <mylib.hpp>` (cabecera C++) | dentro de `extern cpp:` | `#include <mylib.hpp>` |
| `link "m"` | nivel de módulo | `-lm` al enlazador |
| `ldflag "-L/opt/lib"` | nivel de módulo | tal cual al enlazador |
| `insignia pengu_` | nivel de módulo, una vez (`E0026`) | prefijo de los `@export` y de los símbolos `extern c` |
| `regnum mylib` | dentro de `extern cpp:`, por bloque | cualifica los `declare` siguientes |

#### 6.4.1 `regnum` + `import`

`regnum` **no crea** un namespace en el fuente de Pengu: solo decide cómo se escribe el nombre en el C++ emitido. El nombre con el que se llama desde Pengu es siempre el del **módulo** (o el alias del `import`):

```pengu
# mylib.d.pengu
extern cpp:
    regnum mylib
    declare open with path as ref to frozen char into ref to opaque
```

```pengu
# main.pengu
import mylib
calling mylib.open with "/tmp/x"
```

```cpp
// main.cpp
mylib::open("/tmp/x");
```

Reglas:

- El prefijo de llamada es el **módulo**, no el `regnum`: `mylib_wrapper.open` con `regnum mylib` emite `mylib::open(...)`.
- Si dos módulos declaran el mismo `regnum`, cada uno emite su propio namespace; un `declare` no se puede resolver contra el namespace de otro módulo.
- `regnum` no añade un `namespace { }`: emite el nombre cualificado en cada declaración y cada llamada.
- Un `declare` dentro de `extern c` no puede llevar `regnum` (`E0108`): las funciones C no viven en namespaces.

Con alias, el prefijo sigue siendo el alias del `import` y el namespace lo sigue poniendo el `regnum` del módulo declarante:

```pengu
import mylib as m
calling m.open with "/tmp/x"
```

```cpp
mylib::open("/tmp/x");
```

### 6.5 Lambdas

```pengu-fragment
let no_args as weave into int is lambda into 42
let double as weave with x as int into int is lambda x as int into x * 2
let add as weave with a as int, b as int into int is lambda a as int, b as int into a + b
```

```cpp
static int32_t _pengu_lambda_0() { return 42; }
static int32_t _pengu_lambda_1(int32_t x) { return x * 2; }
static int32_t _pengu_lambda_2(int32_t a, int32_t b) { return a + b; }

using weave_into_int = int32_t (*)();
using weave_int_into_int = int32_t (*)(int32_t);
using weave_int_int_into_int = int32_t (*)(int32_t, int32_t);

const weave_into_int no_args = _pengu_lambda_0;
const weave_int_into_int double_ = _pengu_lambda_1;
const weave_int_int_into_int add = _pengu_lambda_2;
```

Una lambda es una **función estática** con nombre generado y un puntero a función, sin capturas: solo ve sus parámetros y las declaraciones de nivel de módulo. Los tipos de parámetro son obligatorios; el retorno se infiere del cuerpo.

Una lambda que usa un nombre local es `E0114`: para eso se pasa el valor como parámetro. No hay `std::function` ni cierres: es una decisión de diseño (sin asignaciones en el heap, sin `virtual`) y es también lo que hace que una lambda se pueda usar como callback de C (`qsort`, `pthread_create`).

### 6.6 Métodos `ritual`

Un `ritual` es una función asociada (estática) de un tipo. No recibe `self` y se llama sobre el nombre del tipo:

```pengu
rune Player:
    name as string
    hp as int

enchanting Player:
    weave ritual new_hero with name as string into Player:
        return with name is name, hp is 100
```

```cpp
struct Player {
    std::string name;
    int32_t hp;
    static Player new_hero(const std::string& name);
};

Player Player::new_hero(const std::string& name) {
    return Player{.name = name, .hp = 100};
}
```

Los parámetros de un `ritual` aceptan `is` con una constante, igual que un `weave` (§6.1): el default se emite en la firma del método estático. Un `ritual` con todos los parámetros por defecto se puede llamar sin argumentos (`calling Point.make`).

```pengu
enchanting Point:
    weave ritual make with x as int is 0, y as int is 0 into Point:
        return with x is x, y is y
```

```cpp
struct Point {
    int32_t x = 0;
    int32_t y = 0;
    static Point make(int32_t x = 0, int32_t y = 0);
};

Point Point::make(int32_t x, int32_t y) {
    return Point{.x = x, .y = y};
}
```

`ritual` es la única forma de tener una función "de tipo"; no hay `static` en el cuerpo y no hereda `self`.

### 6.7 Punto de entrada

```pengu
weave main into int:
    calling print with "hola\n"
    return 0
```

```cpp
int32_t pengu_main() {
    print("hola\n");
    return 0;
}

int main(int argc, char** argv) {
    pengu::init(argc, argv);
    return static_cast<int>(pengu_main());
}
```

El `main` de C++ lo genera el emisor: inicializa el runtime, instala el manejador de `panic` y llama a `pengu_main`, que es el `weave main` del usuario. Un programa sin `weave main` es `E0030` (salvo `--lib`).

---

## 7. Módulos e imports

### 7.1 Módulo = archivo

```pengu-fragment
src/main.pengu          → módulo main
std/scrolls.pengu       → módulo std.scrolls
```

Un módulo se compila a una unidad de traducción `.cpp` con su guard. Los módulos no se compilan en orden: el compilador resuelve el grafo de `import` topológicamente y emite cada unidad por separado.

### 7.2 `import`

```pengu
import std.spark
import std.scrolls as str
import mylib
```

```cpp
#include "std_spark.hpp"
#include "std_scrolls.hpp"
#include "mylib.hpp"
```

- `import a.b` incluye el módulo y trae sus símbolos públicos al scope con el nombre `b` (o el alias de `as`).
- Un ciclo de imports es `E0004`.
- `import` no genera código: solo incluye la cabecera del módulo.
- `import main` es **`E0130`**: `main` es la entrada del programa, no un módulo importable (y su `weave main` no es un símbolo reutilizable). La cabecera `main.hpp` no se genera.

### 7.3 Estado a nivel de módulo

```pengu
var counter as int is 0          # global del módulo, mutable
const LIMIT as int is 64         # constexpr
```

```cpp
int32_t counter = 0;
constexpr int32_t LIMIT = 64;
```

Un global mutable se emite como variable con enlace interno (`static`) salvo que sea `@public`; el estado compartido entre hilos exige `@shared` (§14), igual que hoy.

### 7.4 Privacidad

**Por defecto todo es público.** Un nombre que empieza por `_` es **privado del módulo** (`E0043` al usarlo desde fuera):

```pengu
rune _Internal:          # tipo privado
    x as int

weave _helper into int:  # función privada
    return 1

const _MAX as int is 8   # constante privada

rune Config:
    _secret as string    # campo privado del módulo
    @public port as int  # campo abierto
```

- Vale para `rune`, `omen`, `echo`, `seal`, `alias`, `weave`, `const`, `var` de módulo y campos.
- `@public` abre un campo (o un símbolo) que la regla del `_` cerraría; no hay otra forma de abrir un `_campo`.
- Lo privado **sí** es visible desde el propio módulo, incluidos sus `test`.
- Un `import` trae solo los nombres públicos y los privados con `@public`.
- La privacidad es del **módulo** (el archivo), no del paquete: `std.scrolls` puede usar lo privado de `std.scrolls` y nada más.

**Qué abre `@public`.** Actúa sobre **una** declaración y solo sobre ella:

| Declaración con `_` | ¿`_` la hace privada? | ¿`@public` en ella la abre? |
|---|---|---|
| `rune _Internal:`, `omen _Kind:`, `echo _Value:`, `seal _Id`, `alias _T` | ✅ el tipo | ✅ |
| `weave _helper`, `antiquus _raw`, `const _MAX`, `var _counter` de módulo | ✅ | ✅ |
| `concept _C`, `bind T with _C` | ✅ | ✅ |
| `enchanting _T:` | ✅ la sección | ✅ (y cada método `_m` se abre por separado) |
| `_campo as int` dentro de un tipo | ✅ el campo | ✅ en la línea del campo |
| `static var _x` dentro de una función | ❌ | ❌: un `static` local no tiene enlace de módulo |
| `test "x"` | ❌ | ❌: un test no se exporta nunca |

- `@public` en el **tipo** no abre sus campos `_`: cada campo se abre en su propia línea (y `@public` en un campo de un tipo público es la única forma de abrirlo).
- `@public` sobre un nombre que ya es público no hace nada (no avisa).
- `@public` no cambia el layout ni la ABI: solo la visibilidad dentro del módulo.

### 7.5 Resolución de nombres

Un nombre sin cualificar se busca en este orden, y el primero que aparece gana:

1. el scope local (parámetros, `let`/`var`, bindings de `if`/`for`/`judge`);
2. los scopes externos, del más cercano al más lejano;
3. los nombres del módulo actual;
4. los nombres de los `import` directos, en orden de `import`;
5. los nombres de los `import` transitivos, en orden de `import`;
6. si no aparece, `E0004`.

Reglas:

- Si dos candidatos del mismo nivel empatan, es `E0004` con "ambiguo": cualifica con el alias del módulo.
- `import a.b as x` añade **solo** el nombre `x` (el alias), no los nombres del módulo; para usar un símbolo suelto hay que importar sin alias.
- Un `import` hace visibles los nombres del módulo importado, pero **no** re-exporta los suyos: la transitividad llega a los símbolos, no a los `import` del importado.
- Un tipo del módulo actual eclipsa un tipo de biblioteca con el mismo nombre y avisa `W0018`.
- Los nombres de método no participan en esta resolución: se buscan en el tipo del receptor (§10.5).

---

## 8. Interop con C y C++

### 8.1 `include`, `link`, `ldflag`, `insignia`

```pengu
include <stdio.h>
link "m"
ldflag "-L/usr/local/lib"
insignia pengu_
```

```cpp
#include <stdio.h>
// link y ldflag van a la línea de órdenes del enlazador
// insignia: los símbolos exportados llevan el prefijo "pengu_"
```

`insignia` prefija los símbolos que el módulo **exporta** a C (`extern "C"`), no los internos. Es la forma de evitar colisiones entre módulos.

### 8.2 `extern c`: la frontera C

```pengu
extern c:
    declare puts with s as ref to frozen char into int
    declare qsort with base as ref to void, n as usize, size as usize,
        cmp as weave with ref to frozen void, ref to frozen void into int
        into void
```

```cpp
extern "C" {
    int32_t puts(const char* s);
    void qsort(void* base, size_t n, size_t size,
               int32_t (*cmp)(const void*, const void*));
}
```

Un `declare` de `extern c` no puede usar tipos de la biblioteca (`E0110`); si necesitas pasar un `string` a C, pasas `s.c_str()` con un `ref to frozen char` (§10.1). El emisor garantiza que `extern c` no produce `throw` ni excepciones.

### 8.3 `extern cpp`: la frontera C++

```pengu
extern cpp:
    include <mylib/mylib.hpp>
    regnum mylib
    declare open with path as ref to frozen char into ref to opaque
    declare close with h as ref to opaque into void
    declare version into string
```

```cpp
#include <mylib/mylib.hpp>
void* mylib::open(const char* path);
void mylib::close(void* h);
std::string mylib::version();
```

Con `extern cpp` sí se pueden usar los tipos del lenguaje (`string`, `vector`…), y el compilador enlaza con el símbolo cualificado `mylib::open`. Para una **clase** de C++ (con métodos, no funciones libres), se declara como handle opaco más `regnum` y se escribe un `bind` que la envuelva (§10.4).

**`psc bind --extern=cpp`.** Lee una cabecera (con `clang` o con el parser propio, según `--target`) y escribe un `.d.pengu`. Qué genera:

| Declaración en la cabecera | Qué emite el `.d.pengu` |
|---|---|
| función libre en un namespace | `declare` dentro de `extern cpp:` con el `regnum` del namespace |
| sobrecargas de una función | **varios** `declare` con el mismo nombre; el checker resuelve por tipos |
| clase con métodos públicos | `alias X as opaque` + `declare` de cada método con `ref to opaque` como primer parámetro; el `bind` se escribe a mano |
| `struct` de datos trivial | `rune` con `@repr(c)` (no `opaque`) |
| constructor | **no** se genera: se escribe `born` o un `weave ritual` que llame a `new`/`make_unique` sobre el handle |
| *default arguments* constantes | `declare … with x as int is 5` (`E0073` si no son constantes) |
| plantilla instanciable | `declare` con los argumentos de tipo explícitos (`declare foo of int`) |
| plantilla no instanciable | **no** se genera; `bind` lo lista como omitido y se envuelve a mano |
| macros / `#define` | no se traducen: usa `const` o `when defined(...)` |

Los métodos que devuelven referencias a miembros se declaran como `ref to T`; los que devuelven por valor, con el tipo. Lo que `bind` no puede deducir (propiedad, si el puntero se libera, si el método es `const`) se anota a mano después de generarlo.

### 8.4 `opaque`, `ref to`, `bytes of`

```pengu
alias Buffer as opaque
var h as opaque is calling ccx_dyn_open with "lib"
declare ccx_dyn_symbol with handle as opaque, name as ref to char into ref to void
```

```cpp
using Buffer = void*;
void* h = ccx_dyn_open("lib");
void* ccx_dyn_symbol(void* handle, char* name);
```

`opaque` es `void*` **por valor** (un handle); `ref to opaque` es `void**` (out-param). Un `opaque` no se puede instanciar ni desreferenciar: solo se pasa.

### 8.5 Archivos de declaración `.d.pengu`

Un `.d.pengu` contiene solo `include`, `extern`, `declare`, `alias` y `link`: no genera código, solo la cabecera de declaraciones. Es el formato de salida de `psc bind`.

```pengu
# mylib.d.pengu
include <mylib.h>

extern c:
    declare mylib_init with cfg as ref to frozen Config into int
    declare mylib_run with h as opaque into int
```

### 8.6 `antiquus` — código incrustado

```pengu
antiquus sum3 with a as int, b as int, c as int into int:
    """
    return a + b + c;
    """
```

```cpp
int32_t sum3(int32_t a, int32_t b, int32_t c) {
    return a + b + c;
}
```

`antiquus` lleva **siempre** firma: nombre, parámetros y retorno (§8.6 es la misma forma que en el backend C). Sus parámetros admiten `is` con una constante, igual que un `weave` (§6.1); el default se emite en la definición y el cuerpo lo ve como un parámetro más. El cuerpo es una cadena de tres comillas con C++ **crudo**, que se inserta tal cual dentro de la función emitida y se compila como C++20; los parámetros están en el scope con su nombre. Un `antiquus` sin firma es `E0123`: sin nombre y sin tipos no se puede llamar desde Pengu.

Sirve para lo que el lenguaje no expresa; el compilador no comprueba el cuerpo (ni tipos, ni fugas). Una función `antiquus` que se exporta necesita `@export` para no ser eliminada por DCE.

### 8.7 `transmute`, `@packed`, `@align`, `@repr(c)`

```pengu
@packed
rune Header:
    magic as u32
    version as u16
    flags as u16

@repr(c)
rune CPair:
    a as int
    b as int
```

```cpp
#pragma pack(push, 1)
struct Header {
    uint32_t magic;
    uint16_t version;
    uint16_t flags;
};
#pragma pack(pop)

struct CPair {
    int32_t a;
    int32_t b;
};
static_assert(std::is_standard_layout_v<CPair>);
static_assert(std::is_trivially_copyable_v<CPair>);
```

`@packed` se emite con `#pragma pack` (los tres compiladores lo soportan) y sigue siendo *implementation-defined*: documenta el layout.

`@align(N)` solo se aplica a una `rune` (§14) y se emite **en el `struct`**, no delante de él, porque `alignas` sobre un `struct`-specifier no compila en los tres compiladores:

| Pengu | C++ |
|---|---|
| `@align(16)` sobre `rune Vec` | `struct alignas(16) Vec { … };` |
| `@packed` sobre `rune Header` | `#pragma pack(push, 1)` … `#pragma pack(pop)` |

```cpp
struct alignas(16) Vec {
    float x, y, z, w;
};
static_assert(alignof(Vec) == 16);
```

Para una variable suelta, `alignas(N)` sí va delante del tipo (`alignas(32) int32_t buf[8];`), pero el lenguaje no expone `@align` para locales: se reserva al layout de tipos. `@repr(c)` exige que el tipo sea trivial (sin `born`, `die`, `mirror`, campos con defecto no constante: `E0119`) y es requisito para cruzar `extern c` (§8.2) y para `@export` con tipos de usuario.

**`@repr(c)` y agregados:**

| Tipo | `@repr(c)` | Motivo |
|---|---|---|
| `rune` de campos triviales | ✅ | `static_assert(std::is_standard_layout_v<T>)` |
| `rune` con solo `born` | ✅ | un constructor cualquiera no afecta a la copia trivial |
| `rune` con `born mirror` o `die` | ❌ `E0119` | constructor de copia / destructor propios: deja de ser trivially copyable |
| `rune` con campos no triviales | ❌ `E0111` | `string`, `vector`… no cruzan C |
| `echo` (unión de triviales) | ✅ | es una unión C |
| `omen` numérico | ✅ | es un `enum class : int32_t` |
| `omen` algebraico | ❌ `E0119` | `std::variant` no es trivial |
| `rune` con campo `opaque` | ✅ | `void*` es trivial |

**`@export`: qué tipos cruzan la frontera C.** La firma de un `@export` (y de un `declare` dentro de `extern c`) solo admite tipos con representación C:

| Tipo | `@export` / `extern c` |
|---|---|
| escalares (`int`, `i64`, `f32`, `f64`, `char`, `bool`, `byte`, `usize`, `opaque`) | ✅ |
| `ref to T` / `ref to frozen T` | ✅ (es `T*`/`const T*`) |
| `weave with … into …` (puntero a función) | ✅ |
| `rune` con `@repr(c)` | ✅ |
| `rune` sin `@repr(c)` | ❌ `E0119` |
| `echo` | ✅ |
| `omen` numérico | ✅ (viaja como `int32_t`) |
| `omen` algebraico | ❌ `E0110` |
| `string`, `vector`, `map`, `umap`, `set`, `uset`, `array`, `span`, `many`, `maybe`, `result`, `unique`, `shared`, `weak`, `seal`, tuplas | ❌ `E0110` |
| `void` (retorno) | ✅ |

**`@packed` y `inherit`.** `@packed` en el hijo emite `#pragma pack` **alrededor del `struct` del hijo**; la base conserva su layout (si no es `@packed`, no se le aplica). El resultado es *implementation-defined*: valídalo con `static_assert`/`offsetof` o con un test.

**`@packed`/`@align` en `seal` y `echo`:**

| Tipo | `@packed` | `@align(N)` | Por qué |
|---|---|---|---|
| `seal` | ❌ `E0111` | ❌ `E0111` | un `seal` tiene un solo campo: no hay relleno que quitar ni alineación que subir sin cambiar la base |
| `echo` | ✅ `#pragma pack(push,1)` alrededor de la `union` | ✅ `union alignas(N)` | válido; el layout sigue siendo *implementation-defined* |
| `omen` numérico | ❌ `E0111` | ❌ `E0111` | es un `enum class`: su tamaño lo fija el tipo subyacente |
| `omen` algebraico | ❌ `E0111` | ❌ `E0111` | contiene un `std::variant` |

`@repr(c)` + `@packed` + `@align(N)` a la vez es legal si `N` es compatible con el tamaño packed; si no, el `static_assert` de `alignof` falla con `#line` al rune y el mensaje se traduce (§19.6). El emisor no intenta comprobarlo: es una promesa que verifica C++.

---

## 9. Tipos compuestos

### 9.1 `rune` — structs

Un `rune` es un `struct` con campos con nombre:

```pengu
rune Point:
    x as int
    y as int
    label as string is "p"       # campo con defecto
```

```cpp
struct Point {
    int32_t x;
    int32_t y;
    std::string label = "p";     // campo con defecto (NSDMI)
    bool operator==(const Point&) const = default;
    auto operator<=>(const Point&) const = default;
};
```

Todo `rune` es **agregado** (sin constructor propio) salvo que declare `born`/`die`/`mirror`. Los campos se inicializan en el orden declarado, y `with` usa designadores de C++20 (`Point{.x = 1, .y = 2}`), que exigen el orden de declaración.

Un campo con defecto se emite como *non-static data member initializer*; una runa con campo sin defecto sigue siendo agregada, así que `Point{}` compila (campos a cero) y `Point{}` sobre un campo `string` deja el `string` vacío.

### 9.2 Campos con defecto y agregados

```pengu
rune Config:
    port as int is 8080
    host as string is "localhost"
    debug as bool is false

var a as Config is with port is 9090
var b as Config is donum Config
```

```cpp
struct Config {
    int32_t port = 8080;
    std::string host = "localhost";
    bool debug = false;
};

Config a = Config{.port = 9090};
Config b = Config{};
```

`donum T` es `T{}`: el valor por defecto del tipo (§11.3).

### 9.3 `born`, `born mirror` y `die` — constructores y destructor

Los tres miembros especiales se declaran dentro de `enchanting` y se emiten como constructores, constructores de copia y destructor.

```pengu
rune Buffer:
    data as string
    size as int

enchanting Buffer:
    weave born with cap as int:
        set self->data is ""
        set self->size is cap

    weave born mirror with other as ref to frozen Buffer:
        set self->data is other->data
        set self->size is other->size

    weave die:
        calling print with "adiós\n"
```

```cpp
struct Buffer {
    std::string data;
    int32_t size;

    explicit Buffer(int32_t cap) : data{}, size{cap} {}
    Buffer(const Buffer& other) : data{other.data}, size{other.size} {}
    Buffer(Buffer&& other) noexcept : data{std::move(other.data)}, size{other.size} { other.size = 0; }
    Buffer& operator=(const Buffer&) = default;
    Buffer& operator=(Buffer&& other) noexcept {
        data = std::move(other.data);
        size = other.size;
        other.size = 0;
        return *this;
    }
    ~Buffer() { print("adiós\n"); }
};
```

**La tabla de miembros especiales.** Se lee «si declaras esto, el emisor escribe aquello»:

| Declaras | Copia | Asignación copia | Movimiento | Asignación movimiento | Destructor | ¿Agregado? |
|---|---|---|---|---|---|---|
| nada | implícita | implícita | implícita | implícita | implícita | **sí** |
| `born` | implícita | implícita | implícita | implícita | implícita | no |
| `born mirror` | **la tuya** | `= default` | **emitido** | **emitido** | implícita | no |
| `die` | `= delete` | `= delete` | **emitido** | **emitido** | **el tuyo** | no |
| `born mirror` + `die` | **la tuya** | `= default` | **emitido** | **emitido** | **el tuyo** | no |

El movimiento se emite a mano porque un constructor de copia o un destructor declarados por el usuario **inhiben** el movimiento implícito; sin él, `return with …` copiaría y un `vector of Buffer` no compilaría.

**Reglas.**

1. `born` sin parámetros es opcional. Si todos los campos tienen defecto, no hace falta; si falta un campo sin defecto y no aparece en `born`, es `E0105`.
2. Un `born` de **un solo parámetro es `explicit`**: `calling Buffer.new with 10` es `Buffer{10}`, y `10` no se convierte en `Buffer` en ningún sitio.
3. `born mirror` y el movimiento nunca son `explicit`.
4. **Delegación**: `calling born with args` como primera sentencia de un `born` delega.
5. **Base**: `calling Base.born with args` como primera sentencia encadena la base (§9.9). Si la base no tiene constructor por defecto y no se llama, `E0107`.
6. `born mirror` genera el constructor de copia; la asignación de copia es `= default` (campo a campo). No hay sintaxis para una asignación de copia a mano en esta versión.
7. `die` **no** necesita `banish` de campos: el cuerpo corre antes de que los campos se destruyan. `die` es para lo que RAII no cubre (descriptores, handles, memoria de `antiquus`).
8. `inherit` y `die`: el destructor del hijo corre primero y luego el de la base, automáticamente.
9. `with` dentro de `born` es `E0118`; un `born` cuyo único parámetro es `T` o `ref to frozen T` también es `E0118` (eso es una copia: se declara con `born mirror`).
10. `banish` sobre un valor con `die` es válido e idempotente: asigna `{}` (que ejecuta el destructor) y deja el valor a cero.
11. Un `born` genérico (`born with value as T` dentro de `enchanting Box shard T`) funciona; el emisor escribe `Box<T>::Box(T value)`.
12. Los parámetros de `born` aceptan `is` con una constante, igual que un `weave` (§6.1): el default se emite en la lista de parámetros del constructor y los que lo llevan van al final (`E0072`). Un `born` con **todos** los parámetros por defecto se puede llamar sin argumentos: `calling Buffer.new` emite `Buffer{}`, y `donum Buffer` (§11.3) también emite `Buffer{}`.

**Trivialidad y `@repr(c)`.** El criterio de `@repr(c)` es `std::is_standard_layout_v<T> && std::is_trivially_copyable_v<T>` (`E0119`, §8.7). Un `born` normal **no** rompe ninguna de las dos: un constructor cualquiera no afecta a la copia trivial. Lo que sí las rompe es `born mirror` (constructor de copia propio) y `die` (destructor propio), así que:

| Miembros declarados | `is_trivially_copyable` | `@repr(c)` |
|---|---|---|
| ninguno (agregado) | ✅ | ✅ |
| solo `born` | ✅ | ✅ (pero no es agregado: se construye con `calling T.new`) |
| `born mirror` | ❌ | ❌ `E0119` |
| `die` | ❌ | ❌ `E0119` |
| cualquiera de ellos con campos no triviales | ❌ | ❌ `E0111` |

```pengu
@repr(c)
rune Handle:
    fd as int

enchanting Handle:
    weave born with fd as int:       # ✅: un `born` normal no rompe la trivialidad
        set self->fd is fd
```

```pengu
@repr(c)                              # E0119: `born mirror` declara la copia a mano
rune Label:
    id as int

enchanting Label:
    weave born mirror with other as ref to frozen Label:
        set self->id is other.id
```

```pengu
enchanting Buffer:
    weave born with cap as int is 16:
        set self->data is ""
        set self->size is cap
```

```cpp
struct Buffer {
    std::string data;
    int32_t size;

    explicit Buffer(int32_t cap = 16) : data{}, size{cap} {}
};

Buffer b0{};        // calling Buffer.new
Buffer b1{32};      // calling Buffer.new with 32
```

Un `born` de un solo parámetro es `explicit` aunque el parámetro tenga default: `Buffer{}` sigue siendo válido (C++ permite llamar al constructor con todos los argumentos por defecto), pero `Buffer b = 10;` no compila, como en Pengu.

**Llamada.** `calling Buffer.new with 10` se emite `Buffer{10}`; `calling Buffer.mirror with b` se emite `Buffer{b}` (copia); el destructor **no se llama a mano**: `banish b` es la operación.

```pengu
var b as Buffer is calling Buffer.new with 10
var b2 as Buffer is calling Buffer.mirror with b
defer banish b
```

```cpp
Buffer b{10};
Buffer b2{b};
defer([&] { banish(b); });
```

Un `born` que no inicializa un campo es `E0105`; un `born` con `return` es `E0100`.

### 9.4 `echo` — uniones

Un `echo` es una unión de C, **solo con campos triviales** (`E0113`): números, `char`, `bool`, punteros, `opaque`, arrays y otras uniones triviales. Un campo con destructor no cabe en una unión.

```pengu
@repr(c)
echo Value:
    i as int
    f as float
    p as opaque
```

```cpp
union Value {
    int32_t i;
    float f;
    void* p;
};
```

Leer un campo distinto del último escrito es comportamiento indefinido (`W0002`). Si necesitas seguridad, usa `omen` con payload (§9.5).

### 9.5 `omen` — enums y tipos suma

**Omens numéricos** son `enum class` con tipo subyacente fijo:

```pengu
omen State:
    Ready is 0
    Loading is 1
    Done is 2
```

```cpp
enum class State : int32_t {
    Ready = 0,
    Loading = 1,
    Done = 2,
};
```

**Omens algebraicos** llevan datos en algunas variantes; se emiten como `std::variant` con `std::monostate` para las vacías:

```pengu
omen Slot:
    Empty
    Filled with text as string
    Number with value as int
```

```cpp
struct Slot {
    std::variant<std::monostate, std::string, int32_t> data;

    static Slot Empty() { return Slot{}; }
    static Slot Filled(std::string text) {
        Slot s{};
        s.data.emplace<1>(std::move(text));
        return s;
    }
    static Slot Number(int32_t value) {
        Slot s{};
        s.data.emplace<2>(value);
        return s;
    }
    bool operator==(const Slot&) const = default;
};
```

Los constructores de variante son **fábricas estáticas** con el nombre de la variante, y construyen la alternativa con `emplace<I>` sobre un valor por defecto (no hay constructores posicionales: `Slot{std::in_place_index<0>}` no compila en un agregado, y `Slot(std::string)` sería ambiguo con `Slot(int32_t)` cuando coinciden tipos). La variante de índice 0 se llama `Empty()` y no `Slot{}` en el `.pengu`: en C++ son lo mismo.

Se construye con `calling Slot.Filled with "x"` y se inspecciona con `judge` (§5.4) o con `is present` sobre la variante:

```pengu
var s as Slot is calling Slot.Filled with "hola"
if s.value is present:
    calling print with "{s.value}"
```

```cpp
Slot s = Slot::Filled("hola");
if (std::holds_alternative<std::string>(s.data)) {
    print(std::get<std::string>(s.data));
}
```

Una variante con payload **no admite valores por defecto en sus campos**: `Filled with text as string is ""` es `E0125`. Un default haría que `Filled()` y `Empty()` fueran la misma construcción y que `judge` no pudiera distinguirlas; si el campo puede faltar, se modela con `maybe T` dentro de la variante o con dos variantes.

Un `omen` vacío (`Empty`) **no** ocupa espacio: `std::monostate` es vacío y el `variant` guarda solo el índice. Con dos o más variantes el emit es siempre `struct` + `std::variant` + `monostate`s, aunque todas estén vacías, para que `judge` se emita igual en todos los casos (`switch (s.data.index())`, §5.4).

**Los dos casos degenerados** tienen emit propio, porque un `variant` de un solo tipo (o de ningún payload) sería absurdo:

| Forma | Emisión |
|---|---|
| Una sola variante, vacía: `omen X:` / `    Empty` | `enum class X : uint8_t { Empty = 0 };` |
| Una sola variante, con payload: `omen X:` / `    V with n as int` | `struct X { std::variant<int32_t> data; static X V(int32_t n); };` |

En los dos casos `judge` es trivialmente exhaustivo: el primero se emite como `switch (x) { case X::Empty: … }` (sin `default`), y el segundo como `switch (x.data.index()) { case 0: … }`. No hay `E` para estas formas: son legales y el emisor las cubre.

### 9.6 `seal`, `alias` y `opaque`

**`seal`** es un tipo nominal nuevo sobre un tipo base: no hay conversión implícita en ninguna dirección.

```pengu
seal UserId from int
seal Meters from f64

var id as UserId is UserId from 42
var n as int is id to int
```

```cpp
struct UserId {
    int32_t _v;

    explicit UserId(int32_t v) : _v{v} {}
    explicit operator int32_t() const { return _v; }
    bool operator==(const UserId&) const = default;
    auto operator<=>(const UserId&) const = default;
};
```

La construcción `UserId from 42` es `UserId{42}` y el `to int` es `static_cast<int32_t>(id)`; sin el cast, `E0112`.

**Qué puede envolver un `seal`:**

| Base | Permitido | Nota |
|---|---|---|
| Escalares (`int`, `f64`, `bool`, `char`, `byte`, `usize`, `opaque`) | ✅ | el caso normal |
| `string`, `vector`, `map`, `umap`, `set`, `uset`, `array`, `maybe`, `result` | ✅ | el `seal` copia/mueve el campo |
| `rune` / `omen` / `echo` | ✅ | el `seal` es un envoltorio del campo |
| `ref to T`, `span of T` | ✅ | el `seal` **copia el préstamo**: no alarga la vida del destino |
| `unique of T` | ✅ | el `seal` resultante es **move-only** |
| `shared of T`, `weak of T` | ✅ | copia el contador |
| `weave with … into …` | ✅ | puntero a función |
| `void` | ❌ | `E0122` |

El `seal` **hereda los operadores del tipo base**: emite `==`/`<=>` solo si la base los tiene. Un `seal` sobre una `rune` con `@no_cmp` no se puede comparar (`E0117`), y un `seal` sobre `opaque` sí (compara direcciones, como `std::less<void*>`).

**`@repr(c)` en un `seal`.** Un `seal` es `struct S { T _v; }` con constructor y cast explícitos, y esos dos no afectan a la copia trivial: el `seal` hereda la trivialidad de su base.

| Base del `seal` | `@repr(c)` |
|---|---|
| escalares (`int`, `f64`, `bool`, `char`, `byte`, `usize`, `opaque`) | ✅ |
| `ref to T`, `ref to frozen T`, `span of T`, puntero a función | ✅ |
| `rune` sin `born mirror`/`die` y de campos triviales | ✅ |
| `omen` numérico, `echo` de triviales | ✅ |
| `seal` anidado | ✅ si la base lo es |
| `string`, `vector`, `map`, `umap`, `set`, `uset`, `array`, `maybe`, `result` | ❌ `E0119` |
| `unique`, `shared`, `weak` | ❌ `E0119` |
| `omen` algebraico | ❌ `E0119` |
| `rune` con `born mirror` o `die`, o con campos no triviales | ❌ `E0119` / `E0111` |

El `seal` de un escalar sigue siendo válido para `extern c` y `@export` aunque tenga constructor explícito: `is_trivially_copyable` no mira los constructores que no son de copia/movimiento.

**`alias`** es un alias transparente:

```pengu
alias ByteBuf as vector of byte
```

```cpp
using ByteBuf = std::vector<uint8_t>;
```

**`opaque`** es `void*` (§8.4).

### 9.7 `frozen`

```pengu
weave read with p as ref to frozen Point into int:
    return p->x
```

```cpp
int32_t read(const Point* p) { return p->x; }
```

`frozen T` es `const T`. Un `ref to frozen T` es un `const T*`: no se puede mutar ni pasar a un `ref to T` (`E0005`).

### 9.8 Constructores `with:`

Un builder construye un valor campo a campo y devuelve el valor:

```pengu
rune Task:
    title as string
    done as bool
    points as vector of int

var t as Task is with:
    title is "comprar"
    done is false
    points is [1, 2]

var u as Task is with title is "leer", done is true, points is []
```

```cpp
Task t = [&] {
    Task _t{};
    _t.title = "comprar";
    _t.done = false;
    _t.points = std::vector<int32_t>{1, 2};
    return _t;
}();

Task u = Task{.title = "leer", .done = true, .points = {}};
```

Reglas:

1. Si **todos** los campos son asignables por designador (triviales, o el `with` no omite ninguno), se emite un designador directo `Task{.a = …, .b = …}`.
1-bis. Un `with` puede **omitir** cualquier campo que tenga valor por defecto (§9.2): el designador simplemente no lo nombra y el NSDMI del campo lo rellena. Omitir un campo **sin** defecto también compila y lo deja a cero (comportamiento de agregado), salvo que la runa tenga `born`, en cuyo caso el `with` es `E0106` y hay que pasar por el constructor.

```pengu
rune Config:
    port as int is 8080
    host as string is "localhost"

var c as Config is with port is 9090          # host queda "localhost"
var d as Config is with:                       # sin campos: todo por defecto
```

```cpp
Config c = Config{.port = 9090};
Config d = Config{};
```
2. Si algún campo es omitido y la runa no es agregada (tiene `born`), se emite la **IIFE** que construye con el constructor por defecto y asigna.
3. Un `with` sobre un tipo con `born` es `E0106`: usa `calling T.new with …`.
4. Un `with` sobre un `omen` construye la variante (`calling Slot.Filled with …`).
5. Los builders anidados (`with position is (with x is 0.0, y is 0.0)`) se emiten anidados igual.

### 9.9 `inherit` — herencia real

```pengu
rune GameObj:
    position as Vec2
    bounds as Rect

rune Enemy inherit GameObj:
    health as int
```

```cpp
struct GameObj {
    Vec2 position;
    Rect bounds;
};

struct Enemy : GameObj {
    int32_t health;
};
```

Reglas:

1. Sin `virtual`, sin RTTI, sin polimorfismo: la herencia es **layout + promoción de campos**.
2. Los campos del padre se acceden **promovidos** (`e.position`), no con `.gameObj.`. El emisor traduce a `static_cast<GameObj&>(e).position` cuando hay ambigüedad o cuando el hijo oculta el nombre.
3. Conversión **implícita** de `ref to Enemy` a `ref to GameObj` (upcast): es segura porque `GameObj` es prefijo de `Enemy`. Es un cambio respecto a hoy (antes `E0005`).
4. Conversión de `ref to GameObj` a `ref to Enemy` **no** es implícita: se escribe `x to Enemy`, se emite `static_cast<Enemy*>(x)` y avisa `W0007` (no hay comprobación de tipo en ejecución).
5. **Slicing**: asignar un `Enemy` a un `GameObj` es `E0102` (corta los campos del hijo sin avisar).
6. **Constructor heredado**: no se hereda. `calling Enemy.new` no llama a `GameObj.new`; el usuario escribe el `born` del hijo y encadena con `calling GameObj.born with …` (`E0107` si la base no tiene constructor por defecto).
7. `inherit` repetido es herencia múltiple: el layout es *implementation-defined*; con `@packed` avisa `W0017`. Los campos con el mismo nombre en dos bases son `E0087`, y un método ambiguo es `E0088`; se resuelve con `e.gameObj.position` o con `e.physics.position`.
8. Una runa con `die` que hereda de una con `die` corre ambos destructores en orden inverso, automáticamente.
9. **Ocultar, no sobrescribir.** Un método del hijo con el mismo nombre que uno de la base lo *oculta*: no hay despacho virtual, así que la llamada se resuelve por el tipo estático del receptor. Para llamar al de la base se toma una referencia a la base y se llama sobre ella; el emisor usa una llamada cualificada (`this->GameObj::describe()`).

```pengu
enchanting Enemy:
    weave describe into string:
        let base as ref to GameObj is self
        return "{calling base.describe} y {self->health} hp"
```

```cpp
std::string Enemy::describe() {
    GameObj* base = static_cast<GameObj*>(this);
    return pengu::format("%s y %d hp", base->describe().c_str(), this->health);
}
```

10. **Copia y herencia.** `born mirror` del hijo copia la base campo a campo. Si la base es move-only (tiene `die` y no tiene `born mirror`), el hijo tampoco puede ser copiable: `born mirror` en el hijo es `E0081`.
11. **Comparación.** El `==`/`<=>` automático de `= default` incluye la base como primer subobjeto: dos hijos son iguales si su base y sus campos lo son. `@no_cmp` en la base hace que el hijo tampoco tenga comparación (`E0117`).
12. **`with` y base.** Los campos de la base son promovidos, así que un `with` los nombra como propios: `with health is 100, bounds is with w is 32` (§9.8). Si el hijo tiene `born`, el `with` es `E0106` como en cualquier runa.

```pengu
weave hit with o as ref to GameObj into void:
    set o->bounds.w is o->bounds.w + 1

weave main into int:
    var e as Enemy is with health is 100
    calling hit with sigil of e        # upcast implícito
    let g as ref to GameObj is sigil of e
    let back as ref to Enemy is g to Enemy   # W0007
    return 0
```

```cpp
void hit(GameObj* o) { o->bounds.w = o->bounds.w + 1; }

Enemy e = Enemy{.health = 100};
hit(&e);
GameObj* g = &e;
Enemy* back = static_cast<Enemy*>(g);   // W0007
```

### 9.10 Ejemplo completo de tipos

```pengu
rune Vec2:
    x as float
    y as float

enchanting Vec2:
    weave born with x as float, y as float:
        set self->x is x
        set self->y is y

    weave operator + with o as Vec2 into Vec2:
        return with x is self->x + o.x, y is self->y + o.y

rune Entity inherit GameObj:
    name as string
    hp as int is 100

enchanting Entity:
    weave born with name as string:
        set self->name is name

    weave die:
        calling print with "entidad fuera\n"

omen Event:
    Spawn with entity as Entity
    Move with delta as Vec2
    Despawn
```

> `GameObj` es agregado y se inicializa por defecto; si la base **no** tuviera constructor por defecto, la primera sentencia del `born` del hijo sería `calling GameObj.born with …` y el emisor la emitiría como inicializador de la base.

```cpp
struct Vec2 {
    float x, y;
    Vec2(float x, float y) : x{x}, y{y} {}
    Vec2 operator+(const Vec2& o) const { return Vec2{this->x + o.x, this->y + o.y}; }
    bool operator==(const Vec2&) const = default;
    auto operator<=>(const Vec2&) const = default;
};

struct Entity : GameObj {
    std::string name;
    int32_t hp = 100;

    explicit Entity(std::string name) : name{std::move(name)} {}
    Entity(const Entity&) = default;
    Entity(Entity&&) noexcept = default;
    Entity& operator=(const Entity&) = default;
    Entity& operator=(Entity&&) noexcept = default;
    ~Entity() { print("entidad fuera\n"); }
};

struct Event {
    std::variant<Entity, Vec2, std::monostate> data;
    static Event Spawn(Entity e);
    static Event Move(Vec2 d);
    static Event Despawn();
};
```

---

## 10. Métodos y conceptos

### 10.1 `enchanting` — métodos sobre un tipo

```pengu
rune Player:
    name as string
    hp as int

enchanting Player:
    weave heal with amount as int into void:
        set self->hp is self->hp + amount

    weave is_alive into bool:
        return self->hp > 0

    weave ritual new_hero with name as string into Player:
        return with name is name, hp is 100
```

```cpp
struct Player {
    std::string name;
    int32_t hp;

    void heal(int32_t amount) { this->hp = this->hp + amount; }
    bool is_alive() const { return this->hp > 0; }
    static Player new_hero(std::string name);
};

Player Player::new_hero(std::string name) {
    return Player{.name = std::move(name), .hp = 100};
}
```

Reglas:

1. `self` es `this` y **es implícito**: no se declara como parámetro.
2. `self->campo` es `this->campo`. `self` a secas (pasarlo a otra función) es `this` y su tipo es `T*`.
3. Un método que **no muta** se emite `const`; es obligatorio, y es lo que permite llamarlo sobre un temporal o un `ref to frozen T`.
4. Un método que muta no lleva `const` y exige receptor *lvalue* (igual que hoy).
5. `ritual` es `static`.
6. `enchanting string:` / `enchanting vector of T:` es **`E0120`**: no se pueden añadir métodos a un tipo de la biblioteca. Se escribe un `weave` libre:

```pengu
weave trim with s as ref to frozen string into string:
    return s->substr(0, s->size())
```

```cpp
std::string trim(const std::string& s) { return s.substr(0, s.size()); }
```

7. Un método puede devolver `ref to T` solo si devuelve un campo del propio `self` (si no, `E0005`).
8. Los métodos se ordenan en el `struct` después de los campos, en el orden de declaración.

**Conversión de tipos de usuario.** No hay `operator T()`; la conversión se declara como método y se usa `x to T`:

```pengu
enchanting UserId:
    weave to int into int:
        return self->_v
```

```cpp
int32_t UserId::to_int() const { return this->_v; }
// uso: static_cast<int32_t>(id) se traduce a id.to_int()
```

### 10.2 `concept` — contratos de tiempo de compilación

```pengu
concept Speaker:
    weave greet with target as string into string
```

Un concepto solo enumera firmas: sin cuerpos, sin campos, sin estado. Puede tomar parámetros de tipo (`concept Container shard T:`), y sus métodos `ritual` no están soportados (§11.4).

`concept` se emite como un **`concept` de C++20**:

```cpp
template <typename T>
concept Speaker = requires(T self, std::string target) {
    { self.greet(target) } -> std::convertible_to<std::string>;
};
```

### 10.3 `bind` — implementar un concepto

```pengu
rune Dog:
    name as string

bind Dog with Speaker:
    weave greet with target as string into string:
        return "Woof, {target}!"
```

```cpp
static_assert(Speaker<Dog>);
std::string Dog::greet(std::string target) const {
    return pengu::format("Woof, %s!", target.c_str());
}
```

| Regla | Diagnóstico |
|---|---|
| Todo método requerido debe implementarse | `E0031` |
| Parámetros y retorno deben coincidir exactamente | `E0030` |
| El tipo y el concepto deben existir antes del `bind` | `E0004` |
| Un tipo puede ligar cualquier número de conceptos | — |
| No hay métodos por defecto: cada `bind` escribe todos los cuerpos | — |

El emisor añade un `static_assert(Concepto<T>)` por cada `bind`: si el cuerpo no satisface el contrato, el error sale en C++ con `#line` al `bind`.

### 10.4 `bind` sobre tipos de C++ (FFI de clases)

Para envolver una clase de C++ se declara el handle en `extern cpp` y se liga el concepto:

```pengu
extern cpp:
    include <mylib/socket.hpp>
    regnum mylib
    declare Socket_open with host as ref to frozen char into ref to opaque
    declare Socket_send with fd as ref to opaque, data as ref to frozen char into int

concept Sink:
    weave send with data as ref to frozen char into int

bind opaque with Sink:
    weave send with data as ref to frozen char into int:
        return calling Socket_send with self, data
```

```cpp
int32_t mylib::Socket_send(void* fd, const char* data);
static_assert(Sink<void*>);
int32_t Sink_send(void* self, const char* data) { return mylib::Socket_send(self, data); }
```

### 10.5 Resolución de métodos

`calling x.m with …` se resuelve:

1. Desenvuelve `ref to`, `alias`, `seal` y `frozen` hasta el tipo base.
2. Si `x` es un parámetro de tipo, usa sus bounds `where`.
3. Busca `(tipo base, método)` en la tabla que llenan `enchanting` y `bind`.
4. Busca el nombre monomorfizado (`Box<int>` → `Box`).
5. Busca en la tabla de `bind`s de conceptos.
6. Cae a las **operaciones de lenguaje** de contenedor (`.len`, `at`, `push`, `put`, …).
7. Si no, `E0004`.

La resolución es estática: no hay vtable, no hay despacho dinámico, y el nombre del método no se traduce al emitir.

### 10.6 Conceptos integrados

| Concepto | Habilita | `std::concept` de C++20 |
|---|---|---|
| `Num` | `+`, `-`, `*`, `/`, `-` unario | `pengu::Num` (arith. o float) |
| `Integrum` | `%`, `&`, `\|`, `^`, `<<`, `>>`, `~`, comparaciones | `std::integral` |
| `Real` | aritmética y comparaciones de coma flotante | `std::floating_point` |
| `Par` | `==`, `!=` (automático en runas) | `std::equality_comparable` |
| `Ordo` | `<`, `<=`, `>`, `>=` (automático en runas) | `std::totally_ordered` |
| `Vinculum` | clave de `umap`/`uset`: `hash` + `==` | `pengu::Hashable` |
| `Forma` | interpolación (`"{x}"`) | `pengu::Formattable` |
| `Iterabilis` | `for x in col` | `std::ranges::range` |

`Integrum` y `Real` son refinamientos disjuntos de `Num`: un tipo satisface `Num` a través de uno u otro. `Imago`, `Nexus`, `Json` y `Drop` **ya no existen** como conceptos (apéndice D).

Estas definiciones viven en `pengu/core.hpp`:

```cpp
namespace pengu {

template <typename T>
concept Num = std::is_arithmetic_v<T>;

template <typename T>
concept Hashable = requires(const T& a) {
    { std::hash<T>{}(a) } -> std::convertible_to<size_t>;
    { a == a } -> std::convertible_to<bool>;
};

template <typename T>
concept Formattable = requires(const T& a) {
    { to_str(a) } -> std::convertible_to<std::string>;   // sin cualificar: ADL
};

} // namespace pengu

using pengu::to_str;   // los `to_str` de la biblioteca quedan visibles sin cualificar
```

`Vinculum` es el único concepto que abre `std`: cuando un tipo de usuario se liga a `Vinculum`, el emisor especializa `std::hash<T>` junto al `struct` (§2.7 de la auditoría). Es la única apertura legítima del namespace de la biblioteca en todo el backend.

#### `Forma` en la práctica

`Forma` se liga con `bind T with Forma:` y **un solo método**: `weave to_str into string` (un `weave`, no un `ritual`: recibe `self`). El emisor lo baja a una función libre `to_str` en el espacio global del módulo, y cada hueco de interpolación de ese tipo pasa por ella.

```pengu
rune Money:
    cents as i64
    currency as string

bind Money with Forma:
    weave to_str into string:
        return "{self->cents / 100}.{self->cents % 100:02d} {self->currency}"

var m as Money is with cents is 1234, currency is "EUR"
calling print with "total: {m}\n"      # total: 12.34 EUR
```

```cpp
struct Money {
    int64_t cents;
    std::string currency;
};

std::string to_str(const Money& self) {          // bind Money with Forma
    return pengu::format("%lld.%02lld %s",
        static_cast<long long>(self.cents / 100),
        static_cast<long long>(self.cents % 100),
        self.currency.c_str());
}

const std::string line = pengu::format("total: %s\n", to_str(m).c_str());
print(line);
```

Reglas:

- La firma del `bind` es exactamente `weave to_str into string`; otra firma no satisface el concepto y es `E0005`.
- El emisor llama `to_str(x)` **sin cualificar**: resuelve los tipos de usuario por ADL y los de la biblioteca por el `using pengu::to_str;` de `core.hpp` (§0.4).
- En un hueco `{x}` se emite `to_str(x).c_str()` con verbo `%s`; un hueco con formato (`{x:.2f}`) solo vale para numéricos y `string` (`E0019`), no para un `Forma`.
- Un tipo **sin** `bind Forma` en un hueco es **`E0128`**.
- Los tipos **nativos** (`int`, `i64`, `u*`, `f*`, `bool`, `char`, `string`, `opaque`) **no** pasan por `Forma`: tienen verbo fijo en el emisor (§1.5) y se interpolan sin importar nada. `std.spark` no liga `Forma` a los escalares; un hueco con un tipo de usuario sin `bind Forma` es `E0128`.
- El cuerpo de `to_str` puede llamar a `to_str` de otros tipos; el emisor no detecta ciclos (un `Money` que formatea un `Money` es recursión infinita en runtime).

---

## 11. Genéricos

### 11.1 `shard`

```pengu
rune Box shard T:
    value as T

enchanting Box shard T:
    weave get into T:
        return self->value

weave first shard T with xs as span of T into T:
    return xs at 0
```

```cpp
template <typename T>
struct Box {
    T value;
    bool operator==(const Box&) const = default;
    auto operator<=>(const Box&) const = default;
};

template <typename T>
T Box<T>::get() const { return this->value; }

template <typename T>
T first(std::span<T> xs) {
    return xs[pengu::check_index(0, xs.size(), __FILE__, __LINE__)];
}
```

Los genéricos son **plantillas de C++**: no hay borrado, no hay `void*`, no hay sufijos `_instN`. Las instanciaciones las genera el compilador de C++.

Una runa genérica se emite como plantilla y admite el mismo nombre de método en múltiples instanciaciones sin colisión. La vieja limitación de autorreferencia (`rune Node shard T` no podía tener un campo `Node`/`list of Node`) **desaparece**: con plantillas, `Node<T>` puede contener `std::unique_ptr<Node<T>>`:

```pengu
rune Node shard T:
    value as T
    next as unique of (Node of T)
```

```cpp
template <typename T>
struct Node {
    T value;
    std::unique_ptr<Node<T>> next;
};
```

### 11.2 Bounds

```pengu
weave max_of shard T where T: Ordo with a as T, b as T into T:
    return if a > b then a else b

weave hash_of shard T where T: Vinculum with x as T into usize:
    return calling Hash.hash with x
```

```cpp
template <std::totally_ordered T>
T max_of(T a, T b) { return a > b ? a : b; }

template <pengu::Hashable T>
size_t hash_of(const T& x) { return Hash::hash(x); }
```

`where T: C1 and C2` se emite `requires C1<T> && C2<T>` (o `template <C1 T> requires C2<T>` cuando solo hay una restricción de tipo).

### 11.3 `donum T`

```pengu
var p as Point is donum Point
var s as string is donum string
```

```cpp
Point p = Point{};
std::string s = std::string{};
```

`donum T` es `T{}`. No hay concepto `Donum`: cualquier tipo construible por defecto sirve, y si no lo es, el error lo da C++ con `#line` al `donum`.

### 11.4 Métodos genéricos y derivación

Los métodos de un tipo genérico son plantillas de método:

```pengu
enchanting Box shard T:
    weave map shard U with f as weave with T into U into Box of U:
        return with value is calling f with self->value
```

```cpp
template <typename T>
template <typename U>
Box<U> Box<T>::map(U (*f)(T)) const {
    return Box<U>{.value = f(this->value)};
}
```

Un método `ritual` dentro de un `concept` no está soportado (`E0033`); declara los rituales en `enchanting`. Un tipo genérico no se puede **especializar** por caso: no hay `where T is string` ni `@specialize`. Si necesitas comportamientos distintos, usa un concepto encima y dos `bind`.

### 11.5 Límites

- **Sin especialización** ni parcial: una plantilla, un cuerpo.
- **Sin argumentos de tipo de valor** (`array of T with size N` toma `N` como entero, no como parámetro de plantilla del usuario).
- **Sin deducción a través de `ref to`**: `weave f shard T with x as ref to T` exige `calling f with sigil of v`.
- Los argumentos de tipo explícitos se escriben `calling identity of int with 5`.
- Un tipo genérico no puede ser `@repr(c)` si tiene miembros con plantilla (`E0119`).

---

## 12. Opcionales y errores

### 12.1 `maybe T` y `result of T to E`

```pengu
var a as maybe int is some 5
var b as maybe int is none
var c as result of int to string is ok_of 42
var d as result of int to string is err_of "no encontrado"
```

```cpp
std::optional<int32_t> a = std::optional<int32_t>{5};
std::optional<int32_t> b = std::nullopt;
pengu::Result<int32_t, std::string> c =
    pengu::Result<int32_t, std::string>::ok_value(42);
pengu::Result<int32_t, std::string> d =
    pengu::Result<int32_t, std::string>::err_value(std::string("no encontrado"));
```

`maybe T` es `std::optional<T>` y `result of T to E` es `pengu::Result<T, E>`. **No hay cajas**: el valor vive dentro del `optional`/`Result`, no en el heap. Esto elimina el `malloc` por `ok_of`/`err_of` que hacía el backend C.

`pengu::Result` es:

```cpp
namespace pengu {

template <typename T, typename E>
class Result {
    std::variant<T, E> v_;
    explicit Result(std::variant<T, E> v) : v_{std::move(v)} {}
public:
    static Result ok_value(T t) {
        return Result{std::variant<T, E>{std::in_place_index<0>, std::move(t)}};
    }
    static Result err_value(E e) {
        return Result{std::variant<T, E>{std::in_place_index<1>, std::move(e)}};
    }
    bool has_value() const { return v_.index() == 0; }
    T& value() & { return std::get<0>(v_); }
    const T& value() const& { return std::get<0>(v_); }
    E& error() & { return std::get<1>(v_); }
    const E& error() const& { return std::get<1>(v_); }
};

template <typename E>
class Result<void, E> { /* … */ };

} // namespace pengu
```

Las fábricas se llaman `ok_value`/`err_value` y no son constructores porque `result of string to string` es legal y `Result(T)`/`Result(E)` sería ambiguo. El emisor **siempre las cualifica con el tipo del `result`** (`pengu::Result<int32_t, std::string>::ok_value(42)`): así la fábrica no depende de deducción de tipos, que en `ok_of 42` no existe. Para `result of void to E` la llamada es `pengu::Result<void, E>::ok_value()`.

### 12.2 Constructores

```pengu-fragment
some 5            # maybe int presente
none              # maybe int ausente
ok_of 42          # result ok
err_of "fallo"    # result err
```

```cpp
std::optional<int32_t>{5}
std::nullopt
pengu::Result<int32_t, std::string>::ok_value(42)
pengu::Result<int32_t, std::string>::err_value(std::string("fallo"))
```

En un `result of T to E` donde `T == E`, `ok_of`/`err_of` siguen siendo inequívocos (son fábricas distintas).

### 12.3 Inspección y desenvolvimiento

```pengu
if v is present:
    calling print with "{v}"
if v is not present:
    calling print with "vacío\n"
if r is ok:
    calling print with "{r}"
if r is err:
    calling print with "error: {r.error}"
```

```cpp
if (v.has_value()) { print(pengu::format("%d", *v)); }
if (!v.has_value()) { print("vacío\n"); }
if (r.has_value()) { print(pengu::format("%d", r.value())); }
if (!r.has_value()) { print(pengu::format("error: %s", r.error().c_str())); }
```

**Formas que lanzan, y por eso no se emiten.** El emisor **nunca** usa `optional::value()` ni `vector::at()`: con `-fno-exceptions` abortan. En su lugar:

| Pengu | C++ |
|---|---|
| `m.value` (sin comprobar) | `*pengu::some_value(m, __FILE__, __LINE__)` → `panic` si vacío |
| `m at k` | `pengu::map_at(m, k, __FILE__, __LINE__)` → `panic` si falta |
| `xs at i` | `xs[pengu::check_index(i, xs.size(), __FILE__, __LINE__)]` |
| `r.error` (sin comprobar) | `pengu::err_value_of(r, __FILE__, __LINE__)` → `panic` si ok |

Un `maybe`/`result` **no** tiene `unwrap` que lance: si quieres el valor, o lo compruebas con `is present`, o usas `or else`/`or return`/`try`.

### 12.4 `or else`, `or return`, `try`, `or:`

```pengu
let n as int is m or else 0
let n as int is m or return
let n as int is try read_count with path
let n as int is r or:
    calling log with "falló: {error}"
    0
```

```cpp
const int32_t n = m.value_or(0);
// or return: dentro de una función que devuelve maybe/result
if (!m.has_value()) return std::nullopt;
const int32_t n = *m;

auto _r = read_count(path);
if (!_r.has_value()) return _r.error();
const int32_t n = _r.value();

const int32_t n = [&] {
    if (!r.has_value()) {
        auto& error = r.error();
        log(pengu::format("falló: %s", error.c_str()));
        return 0;
    }
    return r.value();
}();
```

- `or else v` es `value_or(v)`.
- `or return` exige que la función devuelva un `maybe`/`result` **del mismo tipo**; emite la comprobación y `return`.
- `try f with args` propaga el error: si `f` devuelve `err`, el `try` devuelve ese error de la función actual.
- `or:` liga el nombre `error` al error (en `result`) o a `"no value"` (en `maybe`), y evalúa su bloque como valor.

**Compatibilidad de tipos.** Ni `try` ni `or return` convierten de un dominio de error a otro (`E0045`):

| La función devuelve | `try f` | `or return expr` |
|---|---|---|
| `maybe T` | `f` debe devolver `maybe T` | `expr` debe ser `maybe T` (o `none`) |
| `result of T to E` | `f` debe devolver `result of T to E` | `expr` debe ser `result of T to E` (o `err_of …`) |
| `T` | `E0045` | `E0045` |
| `void` | `E0045` | `E0045` |
| con `E1 != E2` | `E0045` | `E0045` |

El mensaje es explícito: *"`try` propaga el mismo tipo de error; para cambiar de dominio, mapea con `if` + `err_of`"*. Tampoco se puede mezclar `maybe` con `result` en la misma función: `try` de un `maybe` dentro de una función que devuelve `result` es `E0045`.

**El binding `error`.** En el bloque `or:` el nombre `error` es un binding **nuevo**, inmutable y de alcance del bloque:

- su tipo es `E` en un `result` y `string` en un `maybe` (con el valor fijo `"no value"`);
- shadowea cualquier `error` exterior (avisa `W0009`, como cualquier sombra);
- si el cuerpo no usa `error`, el binding se emite igual y el emisor no se queja;
- para usar otro nombre, liga el resultado antes (`let r as result of int to string is …`) y usa `r.error` dentro del bloque.

### 12.5 `panic`

```pengu
panic "invariante roto"
```

```cpp
pengu::panic("invariante roto", __FILE__, __LINE__);
```

`pengu::panic` imprime el mensaje con archivo y línea y llama a `std::abort()`. Es la única forma de terminar el programa por un bug; no hay excepciones.

### 12.6 `defer` y `errdefer`

```pengu
weave open_it with path as ref to frozen char into result of int to string:
    let f as opaque is calling stdio_open with path, "r"
    defer calling stdio_close with f
    errdefer calling log with "no se pudo abrir"
    if f == null:
        return err_of "no existe"
    return ok_of 1
```

```cpp
pengu::Result<int32_t, std::string> open_it(const char* path) {
    void* f = stdio_open(path, "r");
    auto _d0 = pengu::defer([&] { stdio_close(f); });
    auto _d1 = pengu::defer([&] { log("no se pudo abrir"); });   // armada
    if (f == nullptr) {
        return pengu::Result<int32_t, std::string>::err_value(std::string("no existe"));
    }
    _d1.dismiss();                    // salida buena: no se ejecuta
    return pengu::Result<int32_t, std::string>::ok_value(1);
}
```

- `defer` ejecuta al salir del **bloque** (scope), en orden inverso (LIFO).
- `errdefer` se emite como la misma guarda, **armada por defecto**, y el emisor inserta `dismiss()` justo antes de cada salida que no es un error.
- Un `defer` con cuerpo `void` funciona; devolver un valor desde el cuerpo de un `defer` es `E0121`.
- El guard ejecuta su cuerpo en el destructor: por eso `defer` funciona con retornos tempranos y con `goto` de etiquetas. En un `panic` **no** se ejecutan: `std::abort` no desenrolla la pila.

**Alcance exacto del `defer`:**

| Sitio | Se ejecuta al salir de |
|---|---|
| cuerpo de `weave` | la función (cualquier `return`) |
| rama de `if`/`unless` | la rama |
| iteración de `while`/`for` | la iteración (también en `continue`) |
| bloque `do:` | el bloque |
| bloque `with` | el bloque |
| bloque `or:` | el bloque |
| brazo de `judge` | el brazo |
| IIFE de una expresión de bloque | el bloque |

En `break`/`continue` corren los `defer` del scope que se abandona, **antes** del salto. En `return` corren todos los scopes hasta la función, en LIFO.

**Cuándo se arma un `errdefer`.** Solo en funciones que devuelven `result of _ to _`; en una función `maybe` o `void` es `E0114`. Se arma si el bloque puede salir con un `err` alcanzable: un `return err_of …`, un `try` de un `result` alcanzable o un `or return` de un `result` alcanzable. El análisis es **conservador**: si el compilador no puede probar que hay un camino de error, `E0114`. Un `errdefer` en el cuerpo de un `if` que no puede fallar es `E0114` aunque la función sí tenga caminos de error.

### 12.7 Propiedad de los valores opcionales

Un `maybe`/`result` **posee** su valor: al copiarlo se copia el contenido, al moverlo se mueve, y al `banish` se destruye. Ya no hay cajas que liberar por separado y `banish` de un `maybe`/`result` es una asignación (`x = {}`), no una llamada a `pengu_banish_maybe`.

---

## 13. Memoria

### 13.1 El modelo

La propiedad es **explícita y estática**:

| Forma | Dueño | Se copia | Se libera |
|---|---|---|---|
| `T` (valor) | el binding | sí, profundo | al salir del scope (destructor de campos) |
| `ref to T` | nadie (préstamo) | copia el préstamo | nunca |
| `unique of T` | el binding | no (solo mover) | al salir del scope |
| `shared of T` | todos los `shared` | comparte (contador) | al último `shared` |
| `weak of T` | nadie (observa) | comparte | no |

No hay recolector: hay RAII. Cada valor que posee memoria la libera en su destructor, y `banish` es la forma explícita de hacerlo antes de tiempo.

### 13.2 `banish`

`banish x` destruye el valor y lo deja a cero:

```pengu
var s as string is "hola"
banish s                     # s queda como string vacía

var xs as vector of int is [1, 2]
banish xs

var p as ref to Point is sigil of q
# banish p                  # E0103: p no posee
```

```cpp
std::string s = "hola";
s = {};                      // libera y deja vacío

std::vector<int32_t> xs{1, 2};
xs = {};

Point* p = &q;
// banish p → E0103
```

Reglas:

1. `banish` solo sobre **dueños**: `string`, `vector`, `map`, `umap`, `set`, `uset`, `maybe`, `result`, una runa con `die`, `unique`, `shared`, `weak`, y elementos de un contenedor (`xs at i`).
2. `banish` de un `ref to T` es `E0103` (no posee).
3. `banish` de un literal, un temporal, un `frozen` o un `const` es `E0008`.
4. `banish` de un `maybe`/`result` vacío es inocuo.
5. `banish` de un valor con `die` ejecuta el destructor y asigna `{}`; es idempotente (el segundo `banish` no hace nada).
6. `banish` no devuelve capacidad: `x = {}` libera de verdad y `clear()` no (la capacidad queda). Es el precio de usar `std::vector`, y está documentado.

### 13.3 `defer` y `errdefer`

Ver §12.6. `defer` es la forma idiomática de liberar en un camino con varios retornos; `banish` es la forma de liberar *ya*.

### 13.4 Lo que el compilador no hace

- No comprueba tiempos de vida: usar un `ref to T` después de `banish` del dueño es un *use-after-free* (el compilador no lo ve).
- No comprueba aliasing: dos `ref to T` al mismo objeto son tu responsabilidad.
- No inserta `free` mágicos: la liberación es el destructor del tipo o el `banish` explícito.
- No hay GC ni *escape analysis*.

Los diagnósticos de movimiento (`E0080`) y de copia de un *move-only* (`E0081`) sí se comprueban, y el emisor emite los chequeos de `check_index`.

### 13.5 Temporales con dueño en expresiones

Un temporal con dueño se destruye al final de la sentencia que lo contiene:

```pengu
calling consume with calling make_string into int
```

```cpp
consume(make_string());
// make_string() devuelve std::string por valor: se destruye al final de la sentencia
```

No hay fugas por olvidar un `banish` de un temporal: el destructor de C++ lo cubre. Lo que sigue siendo error es **guardar un `ref to` a un temporal** (el compilador no lo detecta).

### 13.6 Los valores se mueven, no se copian

Un `return` de un valor local lo **mueve** (`std::move` implícito por elisión de copia); un `let b is a` copia. Un tipo con `die` y sin `born mirror` es *move-only*: usarlo después de moverlo es `E0080`, y copiarlo es `E0081`.

```pengu
var f as File is calling File.open with "x"
var g as File is f          # E0081: File es move-only
var h as File is calling File.move with sigil of f   # mueve
```

```cpp
File f = File::open("x");
// File g = f;            → E0081
File h = std::move(f);
```

### 13.7 Valores devueltos y parámetros

- Un parámetro `T` de tipo contenedor se emite `const T&` si el cuerpo no lo reasigna, `T` si lo reasigna (R6 de la auditoría).
- Un parámetro `ref to T` se emite `T*` y no se comprueba `nullptr`.
- Un retorno `T` se emite `T` y se mueve, nunca se copia.
- Un retorno `ref to T` exige que el referente sobreviva; el compilador no lo comprueba (`E0005` solo comprueba que se devuelve un campo de `self` o un parámetro).

### 13.8 Depurar fugas

Con `--backend=cpp` las fugas se buscan con las herramientas del compilador de C++, no con el runtime: ASan (`-fsanitize=address`) y `valgrind` funcionan sin cambios porque los contenedores son los de la biblioteca estándar. La instrumentación propia (`pengu/gc`, `W0008`) desaparece.

### 13.9 `unique`, `shared`, `weak`

```pengu
var u as unique of Task is calling unique.new with (calling Task.new with "x")
var s as shared of Task is calling shared.new with (calling Task.new with "y")
var w as weak of Task is calling shared.weak with s

if t as shared of Task is calling shared.upgrade with w:
    calling print with "{t.name}"
```

```cpp
std::unique_ptr<Task> u = std::make_unique<Task>(Task::new("x"));
std::shared_ptr<Task> s = std::make_shared<Task>(Task::new("y"));
std::weak_ptr<Task> w = s;

if (auto t = w.lock()) {
    print(t->name);
}
```

| Operación | Emisión |
|---|---|
| `unique.new with v` | `std::make_unique<T>(v)` |
| `unique.get` | `u.get()` |
| `unique.reset` / `unique.release` | `u.reset()` / `u.release()` |
| `shared.new with v` | `std::make_shared<T>(v)` |
| `shared.get` / `shared.get_frozen` | `s.get()` / `s.get()` (const) |
| `shared.count` | `s.use_count()` |
| `shared.weak` | `std::weak_ptr<T>{s}` |
| `shared.downgrade` / `weak.upgrade` | `weak.lock()` → `maybe` |
| `banish u` / `banish s` | `u.reset()` / `s.reset()` |

Reglas:

1. **Un solo `shared`**: no hay `Rc` no atómico; `shared` es siempre `std::shared_ptr` (atómico). Se paga un incremento atómico en un solo hilo; se gana un solo modelo.
2. **`weak` no posee**: `weak.upgrade` devuelve `maybe shared of T` (`w.lock()`); un `weak` expirado es `none`.
3 `shared` y `weak` de un tipo con `die` ejecutan el destructor cuando el contador llega a cero.
4. **Sin `make_mut` ni `get_mut`**: para mutar un valor compartido, `shared.get` (el valor es tuyo mientras el `shared` viva) o se copia y se crea uno nuevo.
5. Pasar un `unique` a un parámetro `unique` lo **mueve** (el argumento queda vacío); pasar un `shared` lo comparte.

### 13.10 Sin copy-on-write

No hay COW: `var b is a` sobre un `string`/`vector`/`map` **copia los datos**. Desaparecen `is_shared`, `ref_count`, `make_unique`, `W0008`. Es el cambio de rendimiento más grande del backend C++ (§19.5) y el más honesto: dos bindings nunca comparten memoria sin decirlo.

### 13.11 Ciclos y recursión

`cyclus` desaparece: un tipo recursivo se escribe con `unique` o con `ref to` y C++ lo permite sin marcador.

```pengu
rune Node:
    value as int
    next as unique of Node
```

```cpp
struct Node {
    int32_t value;
    std::unique_ptr<Node> next;
};
```

Un tipo que se contiene **por valor** es `E0050` (tamaño infinito), igual que hoy.

---

## 14. Atributos

Se escriben `@nombre` en la línea anterior a la declaración (o dentro de una lista `@a @b`).

| Atributo | Qué hace | Emisión C++ |
|---|---|---|
| `@inline` | sugiere inline | `inline` |
| `@cold` | ruta fría | `[[gnu::cold]]`; en MSVC, `__declspec(noinline)` |
| `@deprecated("msg")` | aviso al usar | `[[deprecated("msg")]]` |
| `@noreturn` | no vuelve | `[[noreturn]]` |
| `@export("sym")` | símbolo C público | `extern "C"` + `visibility("default")` |
| `@packed` | sin relleno | `#pragma pack(push,1)` |
| `@align(N)` | alineación de una `rune` | `struct alignas(N) T { … };` |
| `@repr(c)` | layout C, tipo trivial | `static_assert(std::is_standard_layout_v<T>)` |
| `@public` | visible fuera del módulo (§7.4) | enlace externo |
| `@shared` | seguro entre hilos (§14.1) | documental (el tipo debe serlo) |
| `@spawn` | lanza en un hilo | `std::thread` (ver §15.1) |
| `@coroutine` | arranca una corrutina | `pengu::coro` (ver §15.2) |
| `@no_cmp` | sin `==`/`<=>` automáticos | omite los `= default` |

Ya **no existen** `@mutates`, `@json` y `@skip` (§19.7).

```pengu
@deprecated("usa read_text")
@noreturn
weave fail with msg as string into void:
    panic msg

@export("pengu_add")
weave add with a as int, b as int into int:
    return a + b
```

```cpp
[[deprecated("usa read_text")]]
[[noreturn]]
void fail(const std::string& msg) { pengu::panic(msg.c_str(), __FILE__, __LINE__); }

extern "C" __attribute__((visibility("default")))
int32_t pengu_add(int32_t a, int32_t b) { return a + b; }
```

`@export` exige que los tipos de la firma sean de C (`E0110`) y que una runa exportada sea `@repr(c)` (`E0119`). La tabla de tipos permitidos está en §8.7.

En MSVC, `@inline` no emite nada (`inline` es del lenguaje y MSVC la respeta igual), `@cold` se traduce a `__declspec(noinline)` y `@noreturn` a `[[noreturn]]`.

**Atributos que no aplican a ciertas declaraciones** (el compilador avisa y los ignora; no son error):

| Atributo | No aplica a | Motivo |
|---|---|---|
| `@inline`, `@cold`, `@noreturn` | `antiquus` | el cuerpo es texto crudo: el `inline`/`cold` va en el texto, y `@noreturn` no se puede garantizar |
| `@inline`, `@cold` | `declare` | es una declaración externa: el atributo va en la cabecera de C/C++, no en el `declare` |
| `@export` | `declare` | un `declare` ya es externo: exportarlo no significa nada |
| `@public` | `test` | un test no se exporta nunca (§7.4) |
| `@deprecated` | `test` | nadie lo llama desde fuera: el aviso no tiene sentido (`E0056`) |
| `@shared` | `static var`, `weave`, `concept`, `enchanting` | `@shared` describe un tipo (§14.1, `E0132`) |
| `@no_cmp` | `omen` | los omens se comparan por índice de variante (§14.2) |
| `@packed`, `@align(N)`, `@repr(c)` | `alias` | un alias no tiene layout propio |

### 14.1 `@shared`

`@shared` es una **promesa del programador**, no una comprobación: dice que los métodos del tipo son seguros entre hilos. El compilador no la verifica; solo la usa para permitir pasar `ref to T` a un hilo.

| Valor | Cruza `filum.start` sin `@shared` | Notas |
|---|---|---|
| escalares (`int`, `f64`, `char`, `bool`, `opaque`, `usize`, `seal` de escalar) | ✅ | se copian |
| `ref to T` | ❌ `E0082` | ✅ si `T` lleva `@shared` |
| `shared of T` / `weak of T` | ✅ | el contador ya es atómico; `@shared` en `T` es recomendable si `T` no es trivial |
| `vector`, `map`, `string`, `rune` con contenedores | ❌ | se **mueven** al hilo, no se comparten |
| `unique of T` | ❌ | se mueve |
| `rune` sin contenedores (solo escalares) | ✅ | se copia |

Un `shared of int` cruza sin `@shared`: el valor es trivial y el contador es atómico. Un `shared of Buffer` cruza igual, pero si dos hilos llaman a métodos que mutan el `Buffer` a la vez, el resultado es una carrera: eso es exactamente lo que promete `@shared` en `Buffer`.

**Dónde se puede poner `@shared`:**

| Tipo | `@shared` | Nota |
|---|---|---|
| `rune` | ✅ | promesa del programador sobre sus métodos |
| `omen` numérico | ✅ | es un `enum class`: trivial, se copia |
| `omen` algebraico | ✅ solo si todos sus payloads son triviales o `@shared` | el `variant` copia/mueve sus payloads |
| `seal` | ✅ si su base es trivial o `@shared` | hereda la promesa del base |
| `alias` | ✅ | la hereda del tipo aliaseado |
| `echo` | ❌ `E0129` | una unión sin comprobación no se puede prometer segura entre hilos |
| `concept` | ❌ `E0132` | `@shared` describe un tipo, no un contrato |
| `enchanting T:` | ❌ `E0132` | el atributo va en el `rune`, no en la sección de métodos |
| `weave` / `static var` | ❌ `E0132` | el `static` es por proceso, no por hilo |

### 14.2 `@no_cmp`

`@no_cmp` desactiva la comparación automática de una `rune` o un `seal`:

- no se emiten `operator==` ni `operator<=>`;
- `a == b`, `a < b`, … son `E0117`;
- el tipo no se puede usar como clave de `map`/`set` (`E0104`); como clave de `umap`/`uset` sí, si además liga `Vinculum`;
- `judge` sobre el tipo sigue funcionando (compara por variante/valor, no con el `==` del tipo);
- `is present`/`is ok` sobre un `maybe`/`result` del tipo no se ven afectados;
- `@no_cmp` en un `omen` no aplica: los omens se comparan por índice de variante y eso no se puede desactivar;
- comparar un campo de un tipo con `@no_cmp` usando `==` es `E0117`.

---

## 15. Hilos y corrutinas

### 15.1 Hilos (`std.filum`)

```pengu
import std.filum

@spawn
weave worker with msg as string into void:
    calling print with "{msg}\n"

weave main into int:
    let h as Thread is calling filum.start with worker, "hola"
    let r as result of void to ThreadError is calling filum.join with h
    return 0
```

```cpp
void worker(std::string msg) { print(pengu::format("%s\n", msg.c_str())); }

std::thread h = filum::start(worker, std::string("hola"));
pengu::Result<void, ThreadError> r = filum::join(h);
```

- `filum.start` **mueve** los argumentos con dueño; un local movido no puede releerse (`E0080`).
- `start0`/`start2`/`start3` para 0/2/3 argumentos; `detach` y `free` para el ciclo de vida.
- `Thread` es un id copiable; `join` devuelve `result of void to ThreadError`.
- Un `ref to T` compartido entre hilos exige `@shared` en `T`; los escalares se copian.
- La bajada usa `std::thread` (estándar, sin excepciones) en lugar de pthread/CreateThread; la parte específica de plataforma queda en `pengu/plat.c` (tamaño de pila, TLS).

### 15.2 Corrutinas (`std.coro`)

```pengu
import std.coro

weave count with n as int, out as ref to int into void:
    for i in 0 to n:
        set essence of out is i
        calling coro.yield

weave main into int:
    var slot as int is 0
    let c as Coroutine is calling coro.start with count, 3, sigil of slot
    while calling coro.status with c == CoroutineState.suspended:
        calling coro.resume with c
        if calling coro.status with c == CoroutineState.suspended:
            calling print with "{slot}\n"
    calling coro.free with c
    return 0
```

```cpp
void count(int32_t n, int32_t* out) {
    for (int32_t i = 0; i < n; i++) {
        *out = i;
        coro::yield();
    }
}

int32_t pengu_main() {
    int32_t slot = 0;
    pengu::Coroutine c = coro::start(count, 3, &slot);
    while (coro::status(c) == CoroutineState::suspended) {
        coro::resume(c);
        if (coro::status(c) == CoroutineState::suspended) {
            print(pengu::format("%d\n", slot));
        }
    }
    coro::free(c);
    return 0;
}
```

Las corrutinas son **stackful** (pila de 64 KiB, `minicoro` sobre `pengu/plat.c`), cooperativas y explícitas: no hay planificador automático, ni `async`/`await`, ni cancelación, ni valor de retorno por `yield`. **`coro.yield` no toma ni devuelve valor** (`mco_yield` tampoco): para comunicar datos, escribe en un `ref to` (o en un `shared`) antes de `yield`, como en el ejemplo. `resume` devuelve `CoroutineState` (`suspended`/`finished`); `free` solo sobre una terminada; `abandon` descarta una suspendida y **no** ejecuta sus `defer` (por eso es una herramienta de último recurso). `yield` fuera de una corrutina o `resume` sobre una terminada es `panic`.

`@coroutine` marca la función que arranca una corrutina: primer argumento `worker`, resto sus argumentos, retorno `void`.

### 15.3 Reactor

`std.reactor.EventLoop` (epoll/poll) ofrece `spawn`, `run`, `sleep_ms` y `close`; las variantes `*_async` hacen `panic` fuera del bucle. El emit sigue igual que en el backend C: el bucle es código del módulo, no del lenguaje.

---

## 16. Tests y herramientas

### 16.1 Bloques `test`

```pengu
test "la suma funciona":
    let r as int is calling add with 2, 3
    if r != 5:
        panic "esperaba 5"
```

```cpp
static void _pengu_test_la_suma_funciona() {
    const int32_t r = add(2, 3);
    if (r != 5) { pengu::panic("esperaba 5", __FILE__, __LINE__); }
}
```

Los cuerpos de los `test` se comprueban en `check`, `build` y `run`, pero el arnés de C++ solo se emite con `psc test`. Un `test` puede llamar a `panic` y el arnés lo traduce a un test fallido (no aborta el proceso).

### 16.1.1 Cómo funciona el arnés

- El arnés es una tabla `{ nombre, fn }` en orden de declaración, más un `main` propio (`pengu_test_main`).
- `pengu::panic` no llama a `abort()` cuando hay un test activo: llama a un `panic_handler` global. El arnés lo instala y hace `longjmp` al runner, que marca el test como fallido e imprime `archivo:línea: mensaje`. Sin test activo, el handler imprime y llama a `abort()` (comportamiento normal).
- `longjmp` es la única salida: el dialecto no tiene excepciones, así que los `defer` del test **no** se ejecutan al fallar (igual que en `panic` normal, §12.6).
- Un test que termina sin `panic` pasa.
- Los tests se ejecutan **en el hilo principal**, de uno en uno: un `@spawn` dentro de un test es responsabilidad del test (hay que hacer `join`).
- `--test-filter patrón` filtra por nombre (subcadena); `--watch` reejecuta al cambiar el fuente; `--diagnostics=json` emite el resultado en JSON.
- `std.ward` sigue siendo la API de aserciones (`ward.expect`/`ward.require`); sus fallos también pasan por `panic`.
- `--backend=cpp` no cambia el arnés: cambia solo el `.cpp` emitido.

### 16.2 Comandos

| Comando | Con `--backend=cpp` | Notas |
|---|---|---|
| `psc build` | ✅ | compila a `.cpp` y enlaza con `g++`/`clang++`/`cl` |
| `psc run` | ✅ | build + ejecutar |
| `psc check` | ✅ | añade `--dialect=cpp20`; avisa de lo que no es portable al backend C |
| `psc emit-cpp` | ✅ | nuevo; escribe el `.cpp` sin compilar (antiguo `emit-c`) |
| `psc test` | ✅ | mismo arnés (§16.1.1); `--test-filter`, `--watch` |
| `psc bind --extern=cpp` | ✅ | nuevo; genera `.d.pengu` desde una cabecera C++ (§8.3) |
| `psc fmt` | ✅ | sin cambios: formatea `.pengu` con la gramática nueva |
| `psc doc` | ✅ | sin cambios: extrae `##` |
| `psc init` / `add` / `remove` / `update` | ✅ | sin cambios en el manifiesto salvo `backend`/`cxxstd`/`cxxflags` |
| `psc lsp` | ✅ | usa los diagnósticos nuevos (§19) |
| `psc doctor` | ✅ | comprueba `g++`, `clang++` y `cl`, y el `--dialect` disponible |
| `psc assets` / `gc` / `tree` / `time` / `watch` / `eval` / `version` | ✅ | sin cambios |

### 16.3 Opciones de build

| Flag | Efecto |
|---|---|
| `--backend=c` / `--backend=cpp` | backend (por defecto `c` durante la transición) |
| `--dialect=cpp20` | dialecto (con `--backend=cpp` es el único válido) |
| `--cc g++` / `clang++` / `cl` | compilador de C++ |
| `--dialect=c99` / `cpp20` | dialecto portable; con `--backend=cpp`, `c99` es `E0124` |
| `--strict-c99` | **retirado**: error con el fix-it `--dialect=c99` (no se acepta en silencio) |
| `--release-unsafe` | define `PENGU_UNSAFE`: `pengu::check_index` devuelve el índice sin comprobar |
| `--profile`, `--target`, `--out`, `--exe`, `--verbose` | como hoy |
| `--diagnostics=json` | diagnósticos en JSON |

### 16.4 Manifiesto

`pengu.toml` gana tres claves:

```toml
[build]
backend  = "cpp"
cxxstd   = "c++20"
cxxflags = "-Wall -Wextra -Wpedantic"
```

`cflags` sigue existiendo para el backend C; `cxxflags` es solo para el compilador de C++ (no va al enlazador). `lib_dirs`/`include_dirs` siguen aplicando a los dos backends (`-L`/`-I` en compilación y enlace).

Perfiles: `cxxflags` de `[profiles.X]` se **suman** a los de `[build]`.

```toml
[profiles.release]
cxxflags = ["-O2", "-DNDEBUG"]
```

`output` admite un valor nuevo:

| `output` | Artefacto |
|---|---|
| `"exe"` | ejecutable (por defecto) |
| `"static"` | `.a` (`.lib` en MSVC) |
| `"shared"` | `.so`/`.dll` |
| `"c"` | solo el `.c` generado (backend C) |
| `"cpp"` | solo el `.cpp` generado (backend C++), sin compilar |

### 16.5 `psc doc`

`##` sigue siendo la documentación de API; `psc doc` extrae los mismos bloques y los tipos mostrados son los del lenguaje (no los de C++). No hay cambios.

---

## 17. Encadenamiento, pipes, tuplas y forma corta

### 17.1 Cadenas de métodos

```pengu
rune Counter:
    value as int

enchanting Counter:
    weave plus with n as int into Counter:
        return with value is self->value + n

weave main into int:
    var c as Counter is with value is 1
    var d as Counter is calling c.plus with 2
        .plus with 3          # 6
    return d.value
```

```cpp
Counter c = Counter{.value = 1};
Counter d = c.plus(2).plus(3);
return d.value;
```

Cada eslabón es una llamada a método; todos menos el último deben devolver valor. En C++ se emite como llamadas encadenadas, sin temporales: `c.plus(2).plus(3)` funciona porque `plus` devuelve por valor y se puede llamar sobre un temporal.

### 17.2 Pipes

```pengu
var text as string is 42
    pipe spark.str_int

weave editar with value as int, delta as int into int:
    return value + delta

var total as int is calling base
    pipe editar with 2
    pipe editar with 3
```

```cpp
std::string text = spark::str_int(42);
int32_t total = editar(editar(base(), 2), 3);
```

`pipe` encadena **funciones libres**: el valor anterior es el primer argumento. Un método es `E0053`. Un paso que devuelve `void` **no** produce valor: el pipe continúa con el valor anterior, guardado en un temporal.

```pengu
var x as int is 5
    pipe log_int        # log_int: (int) -> void
    pipe double_int     # double_int: (int) -> int
```

```cpp
int32_t x = 5;
log_int(x);
x = double_int(x);
```

### 17.3 Tuplas y retornos múltiples

```pengu
weave divmod with a as int, b as int into (int, int):
    return a / b, a % b

weave main into int:
    let (q, r) is calling divmod with 7, 2
    return q + r
```

```cpp
std::tuple<int32_t, int32_t> divmod(int32_t a, int32_t b) {
    return std::tuple<int32_t, int32_t>{a / b, a % b};
}

int32_t pengu_main() {
    auto [q, r] = divmod(7, 2);
    return q + r;
}
```

Una tupla es `std::tuple<T, U>`; se desempaqueta con `auto [a, b]` (structured binding). Un `let a, b is expr` evalúa `expr` una sola vez (el `auto [a, b]` ya lo garantiza).

### 17.4 Inicializadores abreviados de struct

```pengu-fragment
weave make into Player:
    let name is "Ada"
    var hp is 100
    return with name, hp        # igual que: with name is name, hp is hp
```

```cpp
Player make() {
    const std::string name = "Ada";
    int32_t hp = 100;
    return Player{.name = name, .hp = hp};
}
```

Un campo abreviado debe ser un nombre simple; si el valor es una expresión, se escribe `campo is expr`.

---

## 18. Deprecación

```pengu
@deprecated("usa read_text")
weave read_file with path as string into string:
    ...
```

**`@deprecated` aplica a cualquier declaración con nombre:** `weave`, `declare`, `antiquus`, `rune`, `omen`, `echo`, `seal`, `alias`, `concept`, `bind`, `enchanting` (la sección), `const` y `var` de módulo. **No** en un `test`: nadie lo llama desde fuera, así que el aviso no tiene sentido y es `E0056` (§14). Se emite siempre en la declaración de C++ (`[[deprecated]]` en la función, el `struct`, el `using`…), así que también avisa desde código de C++ que incluya la cabecera.

En un `rune`, el aviso salta al nombrar el tipo en cualquier sitio: un `var`, un parámetro, un campo de otro tipo, `T{}`, `with …` o `calling T.new`. En un `omen`, al nombrar el tipo o cualquiera de sus variantes. En un `alias`, al nombrar el alias o su uso en una firma.

Un uso de una función `@deprecated` emite un aviso (`W0006`) con el mensaje y la línea del uso. El código se mantiene: `W0006` (el de hoy) no se renumera, para no romper el LSP ni los filtros de diagnóstico existentes. En C++ se traduce además a `[[deprecated]]`, así que también avisa si el símbolo se usa desde código de C++ (`antiquus`, otro módulo).

---

## 19. Diagnósticos

### 19.1 Cómo se lee un diagnóstico

Un diagnóstico apunta **siempre** al `.pengu`, nunca al `.cpp`: el emisor intercala `#line` alrededor de cada declaración y cada sentencia generada. Si el error es del compilador de C++, `psc` lo recoge, lo traduce (§19.6) y lo muestra con la línea de Pengu.

```
error[E0103]: un préstamo no se libera
  --> src/main.pengu:12:5
   |
12 |     banish p
   |     ^^^^^^^^ `p` es `ref to Point`; `banish` solo actúa sobre dueños
   |
ayuda: libera el dueño (`unique`, `shared`) o quita el `banish`
```

### 19.2 Códigos que no cambian

Los códigos existentes conservan número y significado. Esta es la lista completa de los que siguen vivos, con la nota de lo que cambia en el backend C++ (última columna):

| Código | Cuándo | Nota en C++ |
|---|---|---|
| `E0000` | error de sintaxis | — |
| `E0001` | `const` dentro de un `weave` | — |
| `E0002` | `var`/`let` en top level | — |
| `E0003` | `self.` en vez de `self->` | `self` se emite como `this->` |
| `E0004` | nombre, miembro, módulo o etiqueta indefinidos; import ambiguo (§7.5) | el emit no compila si llega aquí |
| `E0005` | discrepancia de tipos | ya no cubre `+=` sobre `string` |
| `E0006` | violación de mutabilidad (`let` reasignado, escribir por `ref to frozen`) | — |
| `E0007` | `break`/`continue` fuera de bucle o etiqueta que no lo envuelve | — |
| `E0008` | operación de memoria inválida (`banish` de temporal, literal, `frozen`) | `banish` de `ref`/`span`/`many` pasa a `E0103` |
| `E0014` | sentencia inválida dentro de un constructor `with:` | ahora también `born` (§9.3) |
| `E0015` | dimensión de array desconocida | `array of T` sin `with size` es `E0109` |
| `E0019` | expresión de interpolación inválida | — |
| `E0020` | discrepancia en el tipo de `return` | — |
| `E0021` | número incorrecto de argumentos genéricos | se mantiene; la vieja limitación de autorreferencia desaparece sin código |
| `E0022` | parámetro de tipo usado fuera de su declaración | — |
| `E0023` | más de un parámetro `many` | — |
| `E0024` | `many` no es el último parámetro | — |
| `E0026` | más de un `insignia` | — |
| `E0027` | valor de variante de `omen` duplicado | — |
| `E0029` | valor de variante de `omen` no constante | — |
| `E0030` | firma de método de concepto incorrecta | ahora se compara con un `concept` de C++ (§10.6) |
| `E0031` | método de concepto no implementado | `static_assert` en el `bind` |
| `E0032` | bound no satisfecho | `requires` (§11.2) |
| `E0033` | `self` dentro de un `ritual` | `ritual` es `static`: no hay `this` |
| `E0034` | ritual sobre una instancia, o método sobre un tipo | — |
| `E0035` | nombre que no es un identificador C válido | importa más: el símbolo pasa por el compilador C++ |
| `E0036` | alias de `import` inválido | — |
| `E0037` | nombre de binding duplicado (índice/elemento) | — |
| `E0038` | nombre reservado de C | se amplía a las palabras reservadas de C++ (§1.3) |
| `E0039` | campo que choca con un nombre de C | ídem |
| `E0041` | tamaño de `array` inválido | — |
| `E0042` | rango inválido | — |
| `E0043` | símbolo privado accedido desde otro módulo | §7.4 |
| `E0044` | `judge` no exhaustivo | el emit añade `panic` en el `default` |
| `E0045` | dominio de error incompatible en `try`/`or return` | §12.4 |
| `E0047` | método no disponible sobre un primitivo | ya no existe `enchanting string:` (`E0120`) |
| `E0049` | operador no permitido por el bound | §4.8 |
| `E0050` | tipo de tamaño infinito | recursion por valor: usa `unique` (§13.10) |
| `E0051` | referencia colgante | el compilador C++ no la ve; sigue siendo del checker |
| `E0052` | concepto duplicado | — |
| `E0053` | forma de composición incorrecta (`.` frente a `pipe`) | `x.m` sin argumentos ahora es `x.m()` |
| `E0056` | atributo no permitido aquí | `@mutates`/`@json`/`@skip` ya no existen (`W0014`) |
| `E0057` | carácter fuera de rango | — |
| `E0059` | `antiquus` sin cuerpo | — |
| `E0063` | `static` en la posición incorrecta | — |
| `E0064` | nombre de `test` inválido | — |
| `E0065` | colisión de nombre de campo con C | ídem con C++ |
| `E0069` | etiqueta de bucle duplicada | — |
| `E0070` | nombre de tipo duplicado en un módulo | incluye los tipos de biblioteca (`W0018` al eclipsarlos) |
| `E0071` | argumento nombrado desconocido, repetido o fuera de lugar | — |
| `E0072` | parámetro sin default después de uno con default | — |
| `E0073` | default no constante | — |
| `E0074` | parámetro `many` con valor por defecto | — |
| `E0075` | parámetro `many` en `declare` | — |
| `E0076` | literal de mapa sin anotación de tipo | — |
| `E0077` | el objetivo de `with` no es un lugar direccionable | también en `with` como sentencia (§5.7) |
| `E0079` | `destructuring` con cantidad de nombres incorrecta | — |
| `E0080` | uso de un valor movido | §13.7 |
| `E0081` | copia implícita de un valor move-only | el fix-it ahora dice `born mirror` |
| `E0082` | `ref to T` sin `@shared` cruzando un hilo | antes era `Rc` |
| `E0083` | `shared of T` que cruza un hilo necesita `@shared` en `T` | antes era `Arc` |
| `E0084` | `@export` de un método que no puede cruzar C | se une con `E0110`/`E0119` |
| `E0085` | el tipo de un `inherit` no es una `rune` | antes `fundere` |
| `E0087` | un campo promovido por `inherit` es ambiguo entre dos bases | antes `fundere` |
| `E0088` | un método promovido por `inherit` es ambiguo entre dos bases | ídem |
| `E0089` | el tipo de un `inherit` no tiene nombre de campo implícito | ídem |
| `W0001` | se usó `transmute` | ahora es `std::bit_cast` |
| `W0002` | acceso a campo de `echo` (unión sin comprobar) | — |
| `W0004` | código inalcanzable | — |
| `W0005` | binding ocultado | — |
| `W0006` | símbolo deprecado usado | §18 |
| `W0007` | operación insegura (downcast) | `static_cast` sin comprobación (§9.9) |
| `W0009` | `shadowing` de un nombre | incluye el binding `error` de `or:` (§12.4) |
| `W0013` | rango vacío o invertido | — |

**Retirados:** `E0028` (payload en un `omen` de strings), `E0054` (`derive Json` inválido), `E0066`/`E0067`/`E0068` (`@mutates`), `W0008` (COW), y la rama de `E0005` para `+=` sobre `string`.

### 19.3 Códigos nuevos

| Código | Cuándo | Fix-it |
|---|---|---|
| `E0100` | `return` dentro de una expresión de bloque | extrae a `weave` o usa `if` |
| `E0101` | `break`/`continue` dentro de una expresión de bloque | ídem |
| `E0102` | copiar un derivado como base (*slicing*) | usa `ref to GameObj` |
| `E0103` | `banish` sobre un préstamo (`ref to`, `span`, `many`) | libera al dueño |
| `E0104` | clave de `map`/`set` no ordenable | usa `umap`/`uset` con `Vinculum` |
| `E0105` | campo sin inicializar en `born` | `set self->campo is …` o un defecto |
| `E0106` | `with` sobre una runa con `born` | `calling T.new with …` |
| `E0107` | base sin constructor por defecto | `calling Base.new with …` al principio |
| `E0108` | `regnum` o símbolo cualificado dentro de `extern c` | muévelo a `extern cpp` |
| `E0109` | `array of T` sin `with size N` | `array of T with size N` o `vector of T` |
| `E0110` | tipo sin ABI C en `declare`/`@export` | `ref to frozen char` + `usize`, o `@repr(c)` |
| `E0111` | campo no-C en una runa `@repr(c)` | — |
| `E0112` | conversión implícita hacia/desde un `seal` | `x to UserId` |
| `E0113` | campo no trivial en un `echo` | usa `omen` |
| `E0114` | `errdefer` en una función sin camino de error | `defer`, o devuelve `result` |
| `E0115` | aridad de tipo incorrecta (o comas sin paréntesis) | `map of K, V`; agrupa con paréntesis |
| `E0116` | `declare` fuera de `extern c`/`extern cpp`, o `regnum` fuera de `extern cpp` | envuélvelo en un bloque `extern` |
| `E0117` | operador no declarable o no aplicable | declara `==` o `<=>` |
| `E0118` | `born` ambiguo (con `with:`, o con un solo parámetro del propio tipo) | `born mirror` para copiar |
| `E0119` | `@repr(c)` en un tipo no trivial | quita el constructor o el atributo |
| `E0120` | `enchanting` sobre un tipo de la biblioteca | escribe un `weave` libre |
| `E0121` | `defer` cuyo cuerpo devuelve un valor | usa un bloque `do:` |
| `E0122` | `seal X from void` | envuelve un tipo real, o usa `opaque` |
| `E0123` | `antiquus` sin firma | escribe `antiquus name with … into …:` (§8.6) |
| `E0124` | `--dialect=c99` con `--backend=cpp` | usa `--dialect=cpp20` |
| `E0125` | campo con valor por defecto en una variante de `omen` | envuelve el campo en `maybe T` o separa la variante |
| `E0126` | `break`/`continue` que cruzaría el límite de una expresión (IIFE) | saca la expresión a una variable y salta fuera |
| `E0127` | dirección de un elemento de `vector of bool` (`sigil of`, `ref to bool`, `span`/`many`) | usa `set xs at i is …` o `vector of byte` |
| `E0128` | interpolar un tipo sin `bind T with Forma` | liga `Forma` con `weave to_str into string` (§10.6) |
| `E0129` | `@shared` en un `echo` | usa un `rune` con campos atómicos o un `omen` |
| `E0130` | `import main` | `main` es la entrada del programa, no un módulo |
| `E0131` | comprensión `map`/`umap` cuyo valor no es una tupla `(clave, valor)` | devuelve `(clave, valor)` o acumula en un `vector` |
| `E0132` | `@shared` en algo que no es un tipo (`concept`, `enchanting`, `weave`, `static var`) | ponlo en el `rune` |
| `E0133` | `transmute` a un tipo mayor que el origen (`sizeof(T) > sizeof(x)`) | usa un tipo de igual tamaño o `x to T` |
| `W0014` | `@json`/`@skip` en backend C++ | se rehará en la fase 5 |
| `W0015` | `regnum` sin `include` | añade el `include` |
| `W0016` | copia profunda implícita de un contenedor grande | `ref to` (apagado por defecto) |
| `W0017` | `inherit` con `@packed` | layout *implementation-defined* |
| `W0018` | un tipo de usuario eclipsa un tipo de biblioteca | renombra la runa |

### 19.4 Códigos que cambian de detalle

| Código | Antes | Ahora |
|---|---|---|
| `E0005` | incluía `+=` sobre `string` | ya no: `+=` es válido |
| `E0081` | "copia de un `Drop`" | "copia de un tipo con `die` sin `born mirror`"; el fix-it sugiere `born mirror` |
| `E0082` | `Rc` cruzando un hilo | `ref to T` cruzando un hilo sin `@shared` en `T` |
| `E0083` | `Arc of T` sin `@shared` en `T` | `shared of T` cruzando un hilo sin `@shared` en `T` |
| `E0084` | `@export` devolvía un `Drop` | `@export` con un tipo que no cruza C (se une a `E0110`/`E0119`) |
| `E0085`/`E0087`/`E0088`/`E0089` | hablaban de `fundere` | hablan de `inherit`; el resto igual |
| `E0108` | *(no existía)* | `regnum` fuera de `extern cpp` |

### 19.5 Qué cambia de comportamiento y de rendimiento

| Tema | Antes (C) | Ahora (C++) |
|---|---|---|
| Copiar un `string`/`vector`/`map` | COW: O(1), compartido | **copia profunda**: O(n), independiente |
| `clone()` / `drop()` | métodos de runtime | **no existen**: copia normal / `banish` |
| `for ch in s` | `string` de un byte | **`char`** |
| `s at i` | `string` de un byte | **`char`** |
| `s[i] = 'x'` | `s at i` con `string` | `s[i]` con `char` |
| Orden de `map` | orden de hash | **orden ascendente de clave**; `umap` para hash |
| Clave de `map` | `Vinculum` (hash) | ordenable (`Ordo`); `umap` exige `Vinculum` |
| `ok_of`/`err_of` | `malloc` por valor | **sin caja**, el valor vive en el `Result` |
| `at` | comprobación con `assert` | `check_index` (siempre, salvo `--release-unsafe`) |
| `push` en un bucle | puede reasignar (COW) | puede reasignar (vector); `reserve` explícito si importa |
| Comparar runas | `derive Par` | `==`/`<=>` **siempre** |
| Arranque | runtime propio | `pengu::init` + STL; arranque más rápido |
| Tiempo de compilación | ~1 s por 1.605 líneas en C | ~1 s por 1.605 líneas en C++ a `-O0`; el compilador de 62k líneas ronda 40–90 s |
| Defaults de parámetros | se plegaban en la **llamada** | viven en la **firma**: la llamada omite el argumento y C++ aplica el valor |
| `for`/`while` | solo sentencia | también **expresión**: acumulan en un contenedor (§5.3.1, §5.6.1) |
| `judge` en posición de valor | `switch` con `default` de cero | `switch` exhaustivo + `pengu::panic` inalcanzable detrás |
| `vector of bool` | lista normal de `bool` | `std::vector<bool>` (bits): sin dirección de elemento (`E0127`) |
| `transmute` a un tipo menor | `memcpy` de `min(sizeof)` | `std::bit_cast` si los tamaños coinciden; `memcpy` si no (§4.6) |
| `@repr(c)` con `born` | no aplicaba (no existía) | **sí vale**: un constructor no rompe la copia trivial; `born mirror` y `die` sí (`E0119`) |
| Interpolar un tipo de usuario | no existía | exige `bind T with Forma` + `to_str`; sin él, `E0128` |
| `import main` | no se comprobaba | `E0130` |
| `@shared` | solo en `rune` | también `omen`/`seal`/`alias`; nunca en `echo` (`E0129`) |
| Nombre C++ de un símbolo | pelado (`split`), con prefijo manual | prefijo del módulo (`std_scrolls_split`); `@export` lo sustituye (§1.3.1) |
| Interpolar un nativo | — | verbo fijo del emisor, sin `bind Forma` ni `import std.spark` (§1.5) |
| `operator ()` | no existía | call operator; se llama `calling a with 5` → `a(5)` (§4.8) |

### 19.6 Traducción de errores del compilador de C++

`psc` clasifica los errores de C++ en cuatro familias y los reescribe:

| Familia | Ejemplo de C++ | Mensaje de Pengu |
|---|---|---|
| Plantilla no satisface el concepto | `constraints not satisfied for Hashable<T>` | "`T` no cumple `Vinculum`: falta `weave hash`" + línea del `where` |
| Tipo no copiable | `use of deleted function 'File(const File&)'` | "`File` es *move-only*: no se puede copiar" (`E0081`) |
| `no matching function` | `no matching function for call to 'greet(int)'` | "`greet` espera `string`, recibió `int`" + candidatos |
| `-fno-exceptions` / STL | `Aborted` en ejecución | se evita en el emit: nunca se emiten `.at()`/`.value()` |

### 19.7 Lo que se retira

| Se retira | Sustituto |
|---|---|
| `derive` y sus conceptos (`Imago`, `Nexus`, `Drop`, `Par`, `Ordo`, `Vinculum`, `Json`, `Donum`) | copia por defecto, RAII, `born mirror`/`die`, `==`/`<=>` automáticos, `bind T with Vinculum`, fuera de alcance |
| `Rc`, `Arc`, `WeakRc`, `WeakArc` | `shared of T`, `weak of T` |
| COW, `is_shared`, `ref_count`, `make_unique`, `W0008` | copia profunda + `unique`/`shared` |
| `cyclus` | `unique`/`ref to` |
| `@mutates` | dos métodos: uno que muta y otro que devuelve |
| `@json`, `@skip`, `derive Json` | JSON fuera de alcance (fase 5) |
| `_instN`, tabla de instanciaciones | plantillas de C++ |
| `.clone()`, `.drop()` | copia normal, `banish` |
| `declare` suelto | `extern c:` / `extern cpp:` |
| `op_eq`, `op_cmp`, `is default` | `operator ==` / `operator <=>`, automáticos |
| `--strict-c99` | `--dialect=c99` |
| `namespace` para declarar C++ | `regnum` dentro de `extern cpp` |
| `slice of T` | `span of T` (§2.2) |
| `antiquus` sin firma | `antiquus … with … into …:` (§8.6) |
| `type X as Y` (nunca existió; no se añade) | `alias X as Y` |
| códigos `E0028`, `E0054`, `E0066`, `E0067`, `E0068`, `W0008` | sin equivalente: desaparecen |

Un uso de lo retirado produce un diagnóstico con el sustituto exacto; `psc fmt --migrate` aplica las transformaciones mecánicas (renombrados, `derive` → equivalentes, `list of` → `vector of`, `slice of` → `span of`).

---

## 20. Ejemplo completo

Un programa de inventario que usa runas, herencia, omens algebraicos, operadores, genéricos, `maybe`, `result`, `defer` y `judge`.

```pengu
import std.spark

rune Item:
    name as string
    weight as float

enchanting Item:
    weave operator + with other as Item into Item:
        return with name is self->name + other.name,
                    weight is self->weight + other.weight

    weave describe into string:
        return "{self->name} ({self->weight:.1f} kg)"

rune Container:
    items as vector of Item
    capacity as int

enchanting Container:
    weave born with capacity as int:
        set self->items is []
        set self->capacity is capacity

    weave add with item as Item into result of void to string:
        if self->items.len >= self->capacity:
            return err_of "contenedor lleno"
        calling self->items.push with item
        return ok_of 0

    weave total_weight into float:
        var total as float is 0.0
        for it in self->items:
            set total is total + it.weight
        return total

rune Chest inherit Container:
    locked as bool is false

enchanting Chest:
    weave born with capacity as int:
        calling Container.born with capacity

    weave open into void:
        set self->locked is false

omen FindResult:
    Missing
    Found with index as int

weave find_item with c as ref to Container, name as string into FindResult:
    for i, it in c->items:
        if it.name == name:
            return calling FindResult.Found with i
    return FindResult.Missing

weave main into int:
    var chest as Chest is calling Chest.new with 2
    let sword as Item is with name is "espada", weight is 3.5
    let shield as Item is with name is "escudo", weight is 5.0

    let added as result of void to string is calling chest.add with sword
    if added is err:
        calling spark.println with "error: {added.error}"
        return 1
    let added2 as result of void to string is calling chest.add with shield
    if added2 is err:
        calling spark.println with "error: {added2.error}"
        return 1

    let found as FindResult is calling find_item with sigil of chest, "escudo"
    judge found:
        when Found with i ->
            let it as Item is calling chest.items.at with i
            calling spark.println with "en {i}: {it.describe}"
        when Missing ->
            calling spark.println with "no está"

    calling spark.println with "peso total: {chest.total_weight:.1f} kg"
    return 0
```

```cpp
// ---- Item ----
struct Item {
    std::string name;
    float weight;

    Item operator+(const Item& other) const {
        return Item{.name = this->name + other.name, .weight = this->weight + other.weight};
    }
    std::string describe() const {
        return pengu::format("%s (%.1f kg)", this->name.c_str(), this->weight);
    }
    bool operator==(const Item&) const = default;
    auto operator<=>(const Item&) const = default;
};

// ---- Container ----
struct Container {
    std::vector<Item> items;
    int32_t capacity;

    explicit Container(int32_t capacity) : items{}, capacity{capacity} {}

    pengu::Result<void, std::string> add(Item item) {
        if (this->items.size() >= static_cast<size_t>(this->capacity)) {
            return pengu::Result<void, std::string>::err_value(std::string("contenedor lleno"));
        }
        this->items.push_back(std::move(item));
        return pengu::Result<void, std::string>::ok_value();
    }

    float total_weight() const {
        float total = 0.0f;
        for (auto&& it : this->items) {
            total = total + it.weight;
        }
        return total;
    }
    bool operator==(const Container&) const = default;
    auto operator<=>(const Container&) const = default;
};

// ---- Chest ----
struct Chest : Container {
    bool locked = false;

    explicit Chest(int32_t capacity) : Container{capacity} {}
    void open() { this->locked = false; }
    bool operator==(const Chest&) const = default;
    auto operator<=>(const Chest&) const = default;
};

// ---- FindResult ----
struct FindResult {
    std::variant<std::monostate, int32_t> data;

    static FindResult Missing() { return FindResult{std::monostate{}}; }
    static FindResult Found(int32_t index) {
        FindResult r{};
        r.data.emplace<1>(index);
        return r;
    }
    bool operator==(const FindResult&) const = default;
};

FindResult find_item(Container* c, const std::string& name) {
    for (size_t i = 0; i < c->items.size(); ++i) {
        auto&& it = c->items[i];
        if (it.name == name) {
            return FindResult::Found(static_cast<int32_t>(i));
        }
    }
    return FindResult::Missing();
}

int32_t pengu_main() {
    Chest chest{2};
    const Item sword = Item{.name = "espada", .weight = 3.5f};
    const Item shield = Item{.name = "escudo", .weight = 5.0f};

    auto added = chest.add(sword);
    if (!added.has_value()) {
        spark::println(pengu::format("error: %s", added.error().c_str()));
        return 1;
    }
    auto added2 = chest.add(shield);
    if (!added2.has_value()) {
        spark::println(pengu::format("error: %s", added2.error().c_str()));
        return 1;
    }

    const FindResult found = find_item(&chest, "escudo");
    switch (found.data.index()) {
        case 1: {
            int32_t i = std::get<1>(found.data);
            const Item it = chest.items[static_cast<size_t>(i)];
            spark::println(pengu::format("en %d: %s", i, it.describe().c_str()));
            break;
        }
        case 0: {
            spark::println("no está");
            break;
        }
    }

    spark::println(pengu::format("peso total: %.1f kg", chest.total_weight()));
    return 0;
}
```

Observa el orden de los miembros en el `struct`: campos, constructores, métodos, operadores de comparación. Es determinista y no depende del orden del `.pengu`, para que el `.cpp` sea estable y los *golden* no cambien por reordenar métodos.

---

## Apéndice A. Keywords

Palabras reservadas del lenguaje (tipos, operadores y declaraciones incluidas):

`alias`, `align`, `and`, `antiquus`, `as`, `at`, `banish`, `bind`, `bool`, `born`, `break`, `byte`, `calling`, `char`, `concept`, `const`, `continue`, `defer`, `defined`, `die`, `do`, `donum`, `echo`, `else`, `enchanting`, `err_of`, `errdefer`, `essence`, `extern`, `f32`, `f64`, `float`, `for`, `frozen`, `i16`, `i64`, `i8`, `if`, `import`, `include`, `inherit`, `inline`, `insignia`, `int`, `into`, `is`, `judge`, `lambda`, `ldflag`, `let`, `link`, `long`, `main`, `many`, `map`, `maybe`, `mirror`, `none`, `not`, `null`, `of`, `ok_of`, `omen`, `opaque`, `operator`, `or`, `ord`, `pipe`, `ref`, `regnum`, `result`, `return`, `ritual`, `rune`, `seal`, `self`, `set`, `shard`, `short`, `sigil`, `size`, `size_t`, `some`, `span`, `static`, `step`, `string`, `then`, `to`, `transmute`, `u16`, `u32`, `u64`, `u8`, `uint`, `ulong`, `umap`, `unique`, `unless`, `uset`, `ushort`, `usize`, `var`, `vector`, `void`, `weak`, `weave`, `when`, `where`, `while`, `with`, `shared`, `bytes`.

`ord`, `chr` y `size of`/`align of`/`bytes of` son funciones del preludio, no palabras reservadas.

Son **contextuales** (siguen siendo identificadores fuera de su posición): `judge`, `over`, `pipe`, `lambda`, `operator`, `born`, `die`, `mirror`, `inherit`, `then`, `step`, `main`, `extern`.

Los nombres de tipo de la biblioteca (`vector`, `map`, `umap`, `set`, `uset`, `array`, `span`, `maybe`, `result`, `string`, `unique`, `shared`, `weak`, `many`) son **palabras reservadas**: no se pueden usar como nombre de `rune`, `weave` o variable (declararlo da `W0018` y el tipo de usuario eclipsa al de la biblioteca en su módulo, §7.5).

Retiradas: `derive`, `cyclus`, `fundere`, `nasci`, `mori`, `imago`, `list`, `slice`, `Rc`, `Arc`, `WeakRc`, `WeakArc`, `@mutates`, `@json`, `@skip`.

---

## Apéndice B. Representaciones

| Pengu | C++ | Tamaño / notas |
|---|---|---|
| `int` | `int32_t` | 4 |
| `i64` | `int64_t` | 8 |
| `string` | `std::string` | 32 bytes típicos (SSO 15) |
| `vector of T` | `std::vector<T>` | 24 bytes |
| `map of K, V` | `std::map<K, V>` | árbol; nodo por elemento |
| `umap of K, V` | `std::unordered_map<K, V>` | tabla hash |
| `array of T with size N` | `std::array<T, N>` | N·sizeof(T) |
| `span of T` | `std::span<T>` | puntero + tamaño |
| `many T` | `std::span<const T>` | puntero + tamaño; solo en parámetros |
| `fn` / `weave with T into U` | `U (*)(T)` | puntero a función |
| `maybe T` | `std::optional<T>` | sizeof(T) + alineación |
| `result of T to E` | `pengu::Result<T, E>` | max(T, E) + índice |
| `ref to T` | `T*` | 8 |
| `unique of T` | `std::unique_ptr<T>` | 8 |
| `shared of T` | `std::shared_ptr<T>` | 16 (puntero + control) |
| `weak of T` | `std::weak_ptr<T>` | 16 |
| `(T, U)` | `std::tuple<T, U>` | suma con alineación |
| `omen` numérico | `enum class : int32_t` | 4 |
| `omen` algebraico | `std::variant<…>` | índice + max(payload) |
| `seal X from T` | `struct { T _v; }` | sizeof(T) |
| `opaque` | `void*` | 8 |

La ABI de `@export` sigue siendo C: las runas exportadas son `@repr(c)` y los tipos de la biblioteca no cruzan la frontera (`E0110`).

---

## Apéndice C. Esbozo de gramática

Solo lo que **cambia** o es nuevo. El resto es la gramática de [`LANGUAGE.es.md`](LANGUAGE.es.md), apéndice C.

```ebnf
(* ---------- tipos ---------- *)
Type        = TypeAtom { "of" TypeArgList } ;
TypeArgList = TypeArg { "," TypeArg } ;
TypeArg     = Type | "(" TypeArgList ")" ;          (* un argumento con comas va entre paréntesis *)
TypeAtom    = "int" | "i64" | "i16" | "i8" | "u8" | "u16" | "u32" | "u64"
            | "float" | "f32" | "f64" | "bool" | "char" | "void" | "string"
            | "opaque" | "vector" | "map" | "umap" | "set" | "uset"
            | "array" | "span" | "many" | "maybe" | "result"
            | "ref" | "frozen" | "unique" | "shared" | "weak"
            | "seal" | Ident ;

ArrayType   = "array" "of" Type "with" "size" INT ;
RefType     = "ref" "to" [ "frozen" ] Type ;
MaybeType   = "maybe" Type ;
ResultType  = "result" "of" Type "to" Type ;

(* ---------- parámetros: el default es un parámetro más ---------- *)
Param       = Ident "as" Type [ "is" Expr ] ;      (* default: constante, al final; E0072/E0073 *)
ParamList   = Param { "," Param } ;

(* ---------- miembros especiales ---------- *)
Special     = "born" [ "mirror" ] [ "with" ParamList ]
            | "die" ;
OperatorDef = "operator" OpSym [ "with" Param { "," Param } ] "into" Type ":" Block ;
OpSym       = "+" | "-" | "*" | "/" | "%" | "==" | "<=>" | "[]" | "()"
            | "+=" | "-=" | "*=" | "/=" | "%=" ;

(* ---------- condicional de módulo ---------- *)
WhenDecl    = "when" Expr ":" { TopItem } [ "else" ":" { TopItem } ] ;

(* ---------- código incrustado ---------- *)
AntiquusDecl = "antiquus" Ident "with" [ ParamList ] "into" Type ":" STRING ;

(* ---------- declaraciones de tipo ---------- *)
RuneDecl    = "rune" Ident [ "shard" Ident ] [ "inherit" Ident { "," Ident } ] ":" Runebody ;
EchoDecl    = "echo" Ident ":" { Field } ;
OmenDecl    = "omen" Ident ":" { Variant } ;
Variant     = Ident [ "with" Field { "," Field } ] [ "is" INT ] ;
SealDecl    = "seal" Ident "from" Type ;
Enchanting  = "enchanting" Ident [ "shard" Ident ] [ "where" Bounds ] ":" { Member } ;
Member      = Weave | Special | OperatorDef | "ritual" Weave ;

(* ---------- FFI ---------- *)
ExternBlock = "extern" ( "c" | "cpp" ) ":" { ExternItem } ;
ExternItem  = "include" ( "&#60;" Path "&#62;" | STRING )
            | "regnum" Ident
            | "declare" Ident "with" [ ParamList ] "into" Type
            | "link" STRING | "ldflag" STRING | "insignia" Ident ;

(* ---------- sentencias ---------- *)
WithStmt    = "with" Expr ":" Block ;
WithBuilder = "with" ":" { FieldAssign } | "with" FieldAssign { "," FieldAssign } ;
ForIn       = "for" [ Ident "," ] Ident "in" Expr [ "when" Expr ] ":" Block ;
JudgeArm    = "when" Pattern [ "with" BindingList ] [ "if" Expr ] "->" ( Block | Expr ) ;
Pattern     = Ident { "." Ident } | Literal | Pattern "|" Pattern ;
OverClause  = "judge" Expr "over" Ident ":" { JudgeArm } ;

(* ---------- expresiones: las formas de valor ----------
   Un bloque/for/while en posición de valor es una expresión; el mismo texto
   en posición de sentencia es una sentencia. La diferencia la decide el sitio,
   no la gramática. *)
ValueExpr   = IfExpr | UnlessExpr | ForExpr | WhileExpr | DoExpr | JudgeExpr ;
IfExpr      = "if" Expr "then" Expr "else" Expr
            | "if" Expr ":" Block "else" ":" Block ;
UnlessExpr  = "unless" Expr "then" Expr "else" Expr
            | "unless" Expr ":" Block "else" ":" Block ;
DoExpr      = "do" ":" Block ;
ForExpr     = "for" ForHead ":" Block            (* el último valor del cuerpo se acumula *)
            | "for" ForHead "then" Expr ;        (* comprensión *)
ForHead     = [ Ident "," ] Ident "in" Expr [ "when" Expr ] ;
WhileExpr   = "while" Expr ":" Block ;           (* acumula en vector of T; T anotado *)
JudgeExpr   = "judge" Expr [ "over" Ident ] ":" { JudgeArm } ;  (* else obligatorio salvo exhaustivo *)

(* ---------- operadores ---------- *)
OperatorDecl = "operator" OpSym ;
```

**Alcance de este esbozo.** Solo recoge lo que **cambia** respecto del apéndice C de `docs/LANGUAGE.es.md`: tipos con `of` y comas, `array … with size`, `born`/`die`/`mirror`/`operator` como palabras contextuales dentro de `enchanting`, `rune … inherit`, `extern c`/`extern cpp` con `regnum`, `with` como sentencia y como expresión, y los bucles en posición de valor. Todo lo demás —`ImportDecl`, `TestDecl`, `TopItem`, `Stmt`, `Block`, `Expr`, `Field`, `BindingList`, `Literal`, `Path`— es **exactamente** la gramática de `LANGUAGE.es.md`, apéndice C, sin cambios: la sintaxis del lenguaje no se toca para compilar a C++. Si hay una discrepancia entre los dos apéndices, manda `LANGUAGE.es.md` para lo que no aparezca aquí.

---

## Apéndice D. Correspondencia rápida

| Pengu | C++ emitido |
|---|---|
| `rune P:` | `struct P { … };` |
| `rune D inherit B:` | `struct D : B { … };` |
| `enchanting T:` + `weave m` | método miembro de `T` (`const` si no muta) |
| `weave ritual m` | `static` miembro |
| `weave born with …` | constructor (`explicit` si un parámetro) |
| `weave born with cap as int is 16` | `explicit T(int32_t cap = 16)`; `calling T.new` → `T{}` |
| `weave ritual m with x as int is 0` | `static T m(int32_t x = 0)` |
| `declare f with x as int is 5` | `int32_t f(int32_t x = 5);` (solo declaración) |
| `for x in xs:` en posición de valor | IIFE con `std::vector<T> _r` + `_r.push_back(…)` |
| `for x in xs:` … `as map of K, V` | IIFE con `std::map<K,V> _r` + `_r.insert_or_assign(…)` |
| `while c:` en posición de valor | IIFE con `while` + `_r.push_back(…)` |
| `unless c then a else b` | `!(c) ? a : b` |
| `judge x:` en posición de valor | IIFE con `switch`/`if` y `return` por brazo |
| `with` que omite un campo con defecto | designador sin ese campo (el NSDMI lo rellena) |
| `weave born mirror with other as ref to frozen T` | constructor de copia |
| `weave die` | destructor (+ copia `= delete`) |
| `weave operator +` | `T operator+(const T&) const` |
| `weave operator () with x as int into int` | `int32_t operator()(int32_t) const`; `calling a with 5` → `a(5)` |
| `weave split` en `std.scrolls` | `std_scrolls_split` (prefijo del módulo, §1.3.1) |
| `@export("pengu_open") weave open` | `pengu_open` (el `@export` sustituye el prefijo) |
| `omen X:` numérico | `enum class X : int32_t` |
| `omen X:` con payload | `struct X { std::variant<…> data; static X V(…); }` |
| `omen X:` con una sola variante vacía | `enum class X : uint8_t { Empty = 0 };` |
| `omen X:` con una sola variante con payload | `struct X { std::variant<T> data; static X V(T); };` |
| `echo X:` | `union X { … };` |
| `seal X from T` | `struct X { T _v; explicit X(T); }` |
| `alias A as B` | `using A = B;` |
| `opaque` | `void*` |
| `var x as T is v` | `T x = v;` |
| `let x as T is v` | `const T x = v;` |
| `const X as T is v` | `constexpr T X = v;` |
| `static var x` | `static T x;` |
| `set x is v` / `set x += v` | `x = v;` / `x += v;` |
| `if` / `unless` | `if` / `if (!…)` |
| `while` | `while` |
| `for i from a to b step s` | `for (T i = a; i < b; i += s)` |
| `for x in c` | `for (auto&& x : c)` |
| `for i, x in c` | `for (size_t i = 0; i < c.size(); ++i) { auto&& x = c[i]; … }` |
| `for ch in s` | `for (char ch : s)` |
| comprensión | IIFE `[&]{ std::vector<T> r; … return r; }()` |
| `judge` numérico | `switch` |
| `judge` con guardas / string | cadena de `if`/`else if` |
| `judge … over campo` | `switch (x.campo)` |
| `for k, v in map` | `for (auto&& [k, v] : m)` (orden por `operator<` de la clave) |
| `do:` | IIFE `[&]() -> T { … }()` |
| `if c then a else b` | `c ? a : b` |
| `with x:` | bloque con `auto& _w0 = x;` |
| `with:` builder | designador `T{.a = …}` o IIFE |
| `calling f with a, b is 2` | `f(a, 2)` |
| `calling x.m with a` | `x.m(a)` |
| `x.m` (sin args) | `x.m()` |
| `sigil of x` | `&(x)` |
| `essence of p` | `*(p)` |
| `x at i` | `x[pengu::check_index(i, x.size(), …)]` |
| `x to T` | `static_cast<T>(x)` |
| `transmute x to T` | `std::bit_cast<T>(x)` |
| `some v` / `none` | `std::optional<T>{v}` / `std::nullopt` |
| `ok_of v` / `err_of e` | `pengu::Result<T, E>::ok_value(v)` / `::err_value(e)` |
| `is present` / `is not present` | `.has_value()` / `!.has_value()` |
| `x or else d` | `x.value_or(d)` |
| `x or return` | `if (!x) return …; *x` |
| `try f with a` | `auto r = f(a); if (!r) return r.error();` |
| `x or: …` | IIFE con el error ligado |
| `defer` / `errdefer` | `pengu::defer(…)` / la misma guarda armada, con `dismiss()` en la salida buena |
| `banish x` | `x = {};` (destructor + vacío) |
| `donum T` | `T{}` |
| `many T` | `std::span<const T>` (con `std::array` en la llamada) |
| `unique.new` | `std::make_unique<T>(…)` |
| `shared.new` | `std::make_shared<T>(…)` |
| `unique of T` / `shared of T` / `weak of T` | `std::unique_ptr` / `std::shared_ptr` / `std::weak_ptr` |
| `extern c:` | `extern "C" { … }` |
| `extern cpp:` + `regnum ns` | declaraciones `ns::f(…)` |
| `include <x>` | `#include <x>` |
| `antiquus f with … into T:` + cuerpo | `T f(…) { <texto tal cual> }` |
| `@export("s")` | `extern "C"` + `visibility("default")` |
| `@repr(c)` en `rune` | `static_assert(std::is_standard_layout_v<T>)` |
| `@repr(c)` en `omen` numérico | `enum class` (ya es C) |
| `@repr(c)` en `seal` | `static_assert` de standard layout + trivially copyable (§9.6), solo si la base lo es |
| `bind T with Forma` | `std::string to_str(const T&)` + `to_str(x).c_str()` en cada hueco (§10.6) |
| `import main` | `E0130` |
| `@repr(c)` en `echo` | `union` (ya es C) |
| `@packed` | `#pragma pack(push,1)` |
| `@align(N)` | `struct alignas(N) T` (§8.7) |
| lambda | función `static` + puntero a función |
| `test "x":` | función `static` del arnés |

### D.1 Lo que ya no existe

`derive` (y `Imago`, `Nexus`, `Drop`, `Par`, `Ordo`, `Vinculum`, `Json`, `Donum` como conceptos), `Rc`/`Arc`/`WeakRc`/`WeakArc`, COW, `cyclus`, `@mutates`, `@json`/`@skip`, `_instN`, `.clone()`, `.drop()`, `list of`, `slice of`, `fundere`, `nasci`/`mori`/`imago`, `declare` suelto, `op_eq`/`op_cmp`/`is default`, `--strict-c99`.

| Antes | Ahora |
|---|---|
| `derive Imago` | nada: la copia es por defecto |
| `derive Nexus` | nada: RAII |
| `derive Drop` | `weave die` sin `born mirror` (move-only) |
| `derive Par` | `==` automático |
| `derive Ordo` | `<=>` automático |
| `derive Vinculum` | `bind T with Vinculum:` + `weave hash into usize` |
| `derive Json` | fuera de alcance (fase 5) |
| `Rc of T` / `Arc of T` | `shared of T` |
| `WeakRc` / `WeakArc` | `weak of T` |
| `list of T` | `vector of T` |
| `slice of T` | `span of T` |
| `fundere` | `inherit` |
| `cyclus` | `unique of T` / `ref to T` |
| `@mutates` | dos métodos |
| `nasci` | `born` |
| `mori` | `die` |
| `imago` | `mirror` |
| `.clone()` | `born mirror` o copia normal |
| `.drop()` | `banish` |
| `namespace ns` | `regnum ns` dentro de `extern cpp` |
| `declare` suelto | `extern c:` / `extern cpp:` |
