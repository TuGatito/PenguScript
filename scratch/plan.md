Aquí tienes el **Plan Maestro Actualizado** de **PenguScript 0.2.0**, diseñado específicamente para tu flujo de trabajo (**Gemini Nube** para arquitectura + **Bonsai 27B Local** en C++20) con dos etapas claras:

1. **Ronda 1 — El MVP End-to-End Extensible + CLI + Extensión de Editor:** Construimos toda la tubería completa (*Lexer → Parser → Semantic/Type Checker → Codegen C++20 → Compilador nativo*) pero en su versión mínima y modular, de modo que cada capa sea un esqueleto limpio donde solo haya que ir "enchufando" nodos nuevos.
2. **Ronda 2 — Checklist Completo de Expansión (0.2.0):** Una lista ordenada con casillas (`[ ]`) que cubre **cada una de las features de tu Language Guide** hasta llegar al lenguaje completo y listo para el auto-hospedaje (*self-hosting*).

---

## Ronda 1: Plan por Fases del MVP Extensible (Pipeline Completo + CLI + Editor)

**Regla de oro para Bonsai 27B:** Cada fase toca archivos aislados y usa C++20 estilo PenguScript (`std::variant`, `std::unique_ptr`, `const T&`, sin excepciones en el flujo del compilador, sin dependencias externas).

### Fase 0: Arquitectura Base, CLI (`penguc`) y Diagnósticos

* **Archivos:** `CMakeLists.txt`, `src/main.cpp`, `src/diagnostics.hpp`, `src/compiler.hpp/.cpp`
* **Objetivo:**
* Crear el CLI `penguc` con tres subcomandos mínimos:
* `penguc build <archivo.pengu> [-o salida]` (transpila a C++20 en `.pengu-cache/` y llama a `g++ -std=c++20` o `clang++ -std=c++20`).
* `penguc run <archivo.pengu>` (compila y ejecuta el binario resultante).
* `penguc check <archivo.pengu>` (ejecuta Lexer + Parser + Checker sin compilar C++, útil para la extensión del editor).


* Sistema de diagnósticos estructurado (`Diagnostic { Severity, line, col, file, message }`) que imprima errores limpios estilo Rust/Clang.



### Fase 1: Lexer Extensible con Indentación

* **Archivos:** `src/token.hpp`, `src/lexer.hpp`, `src/lexer.cpp`
* **Objetivo:**
* Tokenizador basado en máquina de estados con `indent_stack` para emitir `Newline`, `Indent` y `Dedent` consistentes.


* Soporte inicial para: identificadores, literales enteros (`int`), decimales (`double`), booleanos (`true`/`false`), strings básicos (`"..."`), comentarios `--`, operadores básicos (`+`, `-`, `*`, `/`, `=`, `==`, `!=`, `<`, `>`, `->`, `::`, `:`, `,`, `(`, `)`) y palabras clave base (`mut`, `const`, `if`, `else`, `return`, `realm`, `invoke`, `and`, `or`, `not`).


* *Diseño extensible:* Tabla de keywords mediante `std::unordered_map<std::string_view, TokenKind>` para agregar palabras clave futuras en 1 línea.



### Fase 2: AST Polimórfico y Parser (Recursive Descent + Pratt)

* **Archivos:** `src/ast.hpp`, `src/parser.hpp`, `src/parser.cpp`
* **Objetivo:**
* Definir el AST usando `std::variant` para `Expr` y `Stmt` (equivalente directo a `omen` en PenguScript) y `std::unique_ptr` para nodos hijos (equivalente a `unique<T>`).


* **Recursive Descent** para declaraciones top-level (`realm`, funciones `nombre = (params) -> Ret`, variables `x = ...` / `mut x = ...`), bloques indentados (`Indent`...`Dedent`), `if`/`else` y `return`.


* **Pratt Parser** para expresiones binarias/unarias con tabla de precedencia (*Binding Power*), llamadas a función `f(a, b)` y `f!`, y acceso estático `io::println`.


* *Diseño extensible:* Cada nuevo constructo (ej. `match`, `rune`, `for`) será simplemente una variante más en `Stmt`/`Expr` y una función `parse_<constructo>()` registrada en el parser.



### Fase 3: Analizador Semántico y de Tipos (Arquitectura en 2 Pasadas)

* **Archivos:** `src/types.hpp`, `src/symbols.hpp`, `src/analyzer.hpp`, `src/analyzer.cpp`
* **Objetivo:**
* **Pasada 1 (Recolección de símbolos):** Registrar funciones y tipos top-level en el `Scope` del `realm` actual (permite llamar funciones declaradas más abajo en el archivo).
* **Pasada 2 (Inferencia y verificación):**
* Inferencia de tipos en variables (`x = 42` $\rightarrow$ `int`) y retorno implícito (última expresión del bloque).


* Verificación de inmutabilidad: prohibir reasignar variables sin `mut` o modificar `const`.


* Prohibición de *truthiness* en `if` (exigir condición `bool`).


* Envoltorio de contexto (`AnalysisContext`) con banderas `in_unsafe`, `in_loop`, `current_return_type` listas para expandir reglas de seguridad.





### Fase 4: Codegen Estructurado (`CppEmitter`) + Runtime Mínimo

* **Archivos:** `src/codegen.hpp`, `src/codegen.cpp`, `runtime/pengu_rt.hpp`
* **Objetivo:**
* `CppEmitter` con buffers separados (`headers`, `type_defs`, `fn_decls`, `fn_defs`) e indentación automática.
* `runtime/pengu_rt.hpp`: cabecera C++20 mínima que implementa `pengu::io::println(...)` (usando `std::format` / `std::cout`) y `pengu::panic(msg)`.
* Transpilar el MVP: un archivo `.pengu` con `realm`, funciones con parámetros, variables `mut`/inmutables, `if/else`, aritmética y `io::println` compila y produce un ejecutable nativo funcional.



### Fase 5: Extensión de Editor (VS Code / Cursor — Reutilizable en Zed)

* **Archivos:** `editors/vscode-penguscript/package.json`, `syntaxes/penguscript.tmLanguage.json`, `language-configuration.json`, `src/extension.ts`
* **Objetivo:**
* **Resaltado de sintaxis (TextMate Grammar):** Coloreado exacto para comentarios `--`, keywords (`rune`, `omen`, `enchanting`, `realm`, `invoke`, `match`, `when`, `mut`, `unsafe`, `and`, `or`, `not`), sigils `<T>`, operadores (`->`, `::`, `@`, `#`) y strings con interpolación `#{...}`.


* **Reglas de indentación inteligente:** Auto-indentar después de `->`, `if`, `else`, `when`, `for`, `while`, `rune`, `omen`, `enchanting` y plegado de código (*code folding*) por indentación.
* **Diagnósticos en vivo:** Al guardar un archivo `.pengu`, la extensión ejecuta `penguc check <archivo>` en segundo plano y subraya en rojo los errores de sintaxis/tipos directamente en el editor. *(Nota: El archivo `.tmLanguage.json` también sirve directamente para Zed).*



---

## Ronda 2: Checklist Completo de Expansión (De MVP a PenguScript 0.2.0)

Cada ítem de esta lista está ordenado por dependencias. Para cada casilla, el flujo con **Bonsai 27B** será idéntico: **Token (si aplica) $\rightarrow$ Nodo AST + Parser $\rightarrow$ Regla en Analyzer $\rightarrow$ Emisión en `CppEmitter` $\rightarrow$ Test `.pengu**`.

### Bloque A: Primitivas, Literales y Control de Flujo Core

* [ ] **Tipos primitivos completos y multi-palabra:** `void`, `bool`, `char`, `signed/unsigned char/short/int/long/long long`, `float`, `double`, `long double`, enteros de tamaño fijo (`int8_t`..`uint64_t`), `size_t`, `ptrdiff_t`, `byte`, `nullptr_t` y modelo de plataforma portable (`LP64`/`LLP64` en `pengu.toml`).


* [ ] **Literales de `char` y strings multilínea + interpolación (`"#{expr}"`):** Escapes de `char`, strings sin escape de salto de línea, interpolación compilada a `std::format` con verificación de `Display`.


* [ ] **Operadores completos y precedencia:** Lógicos (`and`, `or`, `not`), bit a bit (`&`, `|`, `^`, `~`, `<<`, `>>`), asignación compuesta (`+=`, `-=`, etc.), tuplas y asignación múltiple (`a, b = f()`).


* [ ] **Estructuras de control como expresiones:** `if`/`else if`/`else` en posición de valor (ternario o IIFE), `unless`, y bloques léxicos `do`.


* [ ] **Bucles y control de iteración:** `while`, `until`, `repeat ... until`, `for i = a, b[, step]` (numérico), `for x in seq` / `for i, x in seq`, rangos `..` y `..<`, `break` con valor (`T?`), `continue`, y cláusulas `else` en bucles.


* [ ] **`switch` (patrones constantes):** `switch expr` con `when a, b then ...`, sin *fallthrough*, como sentencia y como expresión (`T` con `else`, `T?` sin `else`).



### Bloque B: Funciones Avanzadas, Opcionales y Contenedores STL

* [ ] **Valores opcionales (`T?`):** Azúcar `T?` $\equiv$ `optional<T>`, `none`/`nullopt`, prohibición de *unwrap* implícito y de `T??`, métodos `.value()`, `.value_or(d)`, `.is_some()`, `.is_none()`.


* [ ] **Argumentos por defecto (semántica Kotlin):** Evaluación perezosa dentro del cuerpo de la función (`std::optional<T> x_opt = std::nullopt`), permitiendo referenciar parámetros previos.


* [ ] **Strings y vistas:** `string`, `string_view` (y variantes `u8`/`u16`/`u32`/`w`), indexación con chequeo de límites `s[i]`, longitud `#s`, pertenencia `sub in s`, concatenación `+` / `+=`.


* [ ] **Arrays y Vectores (`vector<T>`, `array<T, N>`):** Literales `[...]`, inferencia de tipo, `arr[i]` (con panic), `arr.get(i)` (`T?`), `arr.get_unchecked(i)` (solo en `unsafe`), `#arr`, `in`, y métodos `.push()`, `.pop()`, `.pop_opt()`, `.insert()`, `.remove_at()`, `.clear()`.


* [ ] **Mapas y Sets (`map`, `unordered_map`, `multimap`, `set`, `unordered_set`):** Literales `{k: v}`, claves identificadores desnudas vs calculadas `[k]`, `set{...}`, acceso seguro `m[k]` (panic en lugar de insertar), `.get()`, `.get_or()`, `.extract()`, `.insert()`, `.remove()`, iteración `.keys` / `.values`.


* [ ] **Comprensiones:** List comprehensions `[expr for x in seq if cond]`, map comprehensions `{k: v for ...}` y set comprehensions `set{expr for ...}` compiladas a IIFEs.


* [ ] **Funciones de primera clase y Closures seguras (`function<Sig>`):** Captura por valor/movimiento por defecto (`[x = x]`), captura por referencia (`[&x]`) solo cuando el compilador prueba que la closure no escapa del ámbito léxico.



### Bloque C: Sistema de Tipos Nominales, ADTs y Genéricos

* [ ] **Módulos e Imports (`realm` e `invoke`):** Resolución desde raíz del proyecto y rutas relativas (`./`), imports selectivos `invoke {a, b} from "..."`, alias `as`, detección de ciclos (DAG), reapertura de `realm` y orden de inicialización de `const`.


* [ ] **Echoes y Seals:** Alias transparentes (`echo X = Y`) y *newtypes* opacos de costo cero (`seal Meters = double`), construcción `Meters(x)` y desenvolvimiento seguro `m as double`.


* [ ] **Runes y `enchanting`:** Estructuras con campos, inicialización obligatoria, `constructor`, `destructor`, acceso `@` / `@campo`, bloques `enchanting` (métodos `const` por defecto, `mut` explícito) y opt-in a `Display` vía `to_string`.


* [ ] **Herencia simple (`heir`) sin Slicing:** `rune Child heir Parent`, llamada obligatoria a `parent(...)` al inicio del constructor, prohibición de *upcasting* implícito por valor y soporte para *upcast* explícito seguro `ref<Parent>(ref(child))`.


* [ ] **Omens unitarios y `flags omen`:** `enum class` con tipo subyacente opcional, auto-numeración, `Omen::try_from(n)` / `Omen::from(n)`, y generación automática de operadores bit a bit (`|`, `&`, `^`, `~`, `.has()`) para `flags omen`.


* [ ] **Omens algebraicos (ADTs) y `match` exhaustivo:** Variantes con payload (`Circle(double)`), compilación a `std::variant`, desestructuración `when Variant(a, b)`, guardas `if cond` y error de compilación si falta alguna variante sin `else`.


* [ ] **Sobrecarga de operadores:** Operadores binarios/unarios en `enchanting`, operadores libres simétricos, indexación `operator []` (const y `mut ref`), llamada `operator ()`, y `operator <=>` con síntesis de `==` y mapeo automático a `Ordering` (`Strong`/`Weak`/`Partial`).


* [ ] **Sigils (Genéricos) y Constraints (`needs`):** Monomorfización en funciones, `rune`, `omen`, `echo` y `seal`; inferencia de tipos; y verificación estructural de constraints (`Eq`, `Ord`, `Hash`, `Copy`, `Move`, `Default`, `Numeric`, `Floating`, `Display`, `Into<U>`, `From<U>`).



### Bloque D: Memoria, Seguridad v0.2.0 y Concurrencia

* [ ] **Jerarquía de Memoria (Niveles 1, 2 y 3):**
* `ref<T>` (parámetros y alias locales `ref(x)`), prohibición de `ref<T>` como campo de `rune` y validación de retorno de referencias.


* Contrato `mut` en declaración y en llamada (`increment(mut x)`).


* Smart pointers: `unique<T>` (con rastreo de *use-after-move*), `shared<T>`, y `weak<T>` con promoción explícita `.lock() -> shared<T>?`.


* `raw<T>` y contexto `unsafe` (bloques y funciones `unsafe`).




* [ ] **Conversiones de tipo (`as`, `try_from`, `from`):** Lista blanca de casts sin pérdida en `as` seguro, casts sin chequeo dentro de `unsafe`, y generación de helpers `T::try_from` / `T::from` para narrowing, `float -> int` y parsing de strings.


* [ ] **Law of Exclusivity (Seguridad de préstamo sin borrow checker):**
* Prohibir mutar `x` o pasar `mut x` mientras exista un alias `ref(x)` activo en el mismo ámbito léxico.


* Prohibir pasar `mut x` y `ref(x)` (o dos veces `mut x`) de la misma variable en una misma llamada.
* Prohibir mutaciones estructurales (`.push()`, `.insert()`, `.remove()`, `.clear()`, reasignación) sobre un contenedor mientras se itera en un bucle `for`.




* [ ] **Concurrencia Segura (`Concurrency Safety`):**
* Aislar `static mut` exclusivamente dentro de bloques/funciones `unsafe`.


* Permitir estado global mutable seguro mediante `const` + `atomic<T>`, `mutex`, `shared_mutex`.


* Verificación estructural `ThreadSafe` al crear `thread` (rechazando `raw<T>`, `ref<T>` a variables locales de stack y contenedores mutables sin sincronización en código seguro).





### Bloque E: Auto-Hospedaje (Self-Hosting)

* [ ] **Bootstrap del compilador:** Reescribir `token`, `lexer`, `ast`, `parser`, `analyzer`, `codegen` y `main` en archivos `.pengu`, compilar `penguc` con el compilador C++20, y verificar que el binario `penguc` generado pueda compilarse a sí mismo produciendo un binario idéntico.

---
