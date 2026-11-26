# Catálogo de diagnósticos

Todos los diagnósticos del compilador tienen un código estable. Los
mensajes pueden mejorar entre versiones; el código no cambia.

Formato: `archivo:línea:columna: severidad[código]: mensaje`.

## CLI (E00xx)

| Código | Nombre | Cuándo aparece |
| --- | --- | --- |
| E0001 | `cli_usage` | Comando o argumentos mal usados. |
| E0004 | `project_empty` | El proyecto no tiene archivos que compilar. |
| E0005 | `file_not_found` | No se puede leer el archivo de entrada. |

## Lexer (E01xx)

| Código | Nombre | Cuándo aparece |
| --- | --- | --- |
| E0101 | `indent_mismatch` | La sangría no coincide con ningún bloque abierto; incluye el nivel más cercano y un arreglo. |
| E0102 | `indent_mixed` | Una misma sangría mezcla espacios y tabuladores. |
| E0103 | `unexpected_char` | Carácter que no pertenece a ningún token. |
| E0104 | `unterminated_string` | Cadena sin cierre. |
| E0105 | `invalid_escape` | Secuencia de escape desconocida. |
| E0106 | `invalid_number` | Número mal formado. |
| E0107 | `invalid_char` | Literal de carácter vacío o con más de un carácter. |
| E0108 | `unterminated_interpolation` | `#{` sin `}`. |
| E0109 | `empty_interpolation` | `#{}` sin expresión. |

## Sintaxis (E02xx)

| Código | Nombre | Cuándo aparece |
| --- | --- | --- |
| E0201 | `expected_token` | Falta un token concreto (`)`, `=`, `->`, `::`…). |
| E0202 | `expected_expression` | Se esperaba una expresión. |
| E0203 | `unexpected_token` | Token inesperado en esa posición. |
| E0204 | `invalid_assignment` | Destino de asignación no válido. |
| E0205 | `invalid_block` | Bloque indentado ausente o vacío donde se exigía uno. |
| E0206 | `invalid_match_arm` | Brazo de `match` mal formado. |
| E0207 | `duplicate_modifier` | Modificador repetido (`mut mut`, `unsafe unsafe`…). |
| E0208 | `invalid_declaration` | Declaración desconocida o palabra clave mal escrita. |

## Módulos y realms (E03xx)

| Código | Nombre | Cuándo aparece |
| --- | --- | --- |
| E0301 | `module_not_found` | `invoke` apunta a un módulo que no existe (se listan las rutas probadas). |
| E0302 | `import_cycle` | Ciclo de importaciones. |
| E0303 | `import_not_top_level` | `invoke` fuera del nivel superior. |
| E0304 | `realm_duplicate` | Un tipo declarado dos veces en el mismo realm (aunque sea en archivos distintos). |
| E0305 | `realm_after_import` | `realm` declarado después de un `invoke`. |
| E0306 | `realm_missing` | Se esperaba un `realm` y no aparece. |
| E0307 | `unknown_symbol` | El módulo importado no exporta ese símbolo. |
| E0308 | `not_const_evaluable` | `static mut` con un valor que no se puede calcular en compilación. |

## Símbolos (E04xx)

| Código | Nombre | Cuándo aparece |
| --- | --- | --- |
| E0401 | `duplicate_symbol` | Nombre declarado dos veces en el mismo módulo. |
| E0402 | `reserved_name` | Nombre reservado por el lenguaje. |
| E0403 | `unknown_identifier` | Identificador que no existe; sugiere el más parecido. |
| E0404 | `unknown_realm` | Realm no importado. |
| E0405 | `private_symbol` | Símbolo no visible desde este módulo. |
| E0406 | `mutable_required` | Se muta algo inmutable: falta `mut` en el binding, en el argumento o en el parámetro. |
| E0407 | `missing_entry` | El realm de entrada no define `main`: el backend JavaScript no sabe por dónde empezar. |

## Tipos (E05xx)

| Código | Nombre | Cuándo aparece |
| --- | --- | --- |
| E0501 | `type_mismatch` | Tipo incompatible en una inicialización, argumento, retorno o asignación. |
| E0502 | `unknown_type` | Tipo que no existe. |
| E0503 | `condition_not_bool` | Condición que no es `bool`. |
| E0504 | `wrong_arity` | Número de argumentos (o de tipos) incorrecto. |
| E0505 | `not_callable` | Se llama algo que no es función. |
| E0506 | `unknown_field` | El tipo no tiene ese campo. |
| E0507 | `unknown_method` | El tipo no tiene ese método. |
| E0508 | `cannot_infer` | No se puede inferir el tipo. |
| E0509 | `invalid_cast` | Conversión no permitida. |
| E0510 | `missing_return` | Falta un `return` en un camino de la función. |
| E0511 | `unreachable_code` | Código inalcanzable. |
| E0512 | `not_display` | Se interpola o se pasa a una variádica `any` un tipo sin `Display`. |
| E0513 | `missing_capability` | Una instancia genérica no cumple las capacidades de `needs`. |
| E0514 | `invalid_any_cast` | Se intenta convertir `any` con `as` (en cualquier dirección). |
| E0515 | `not_first_class` | Se guarda como valor una función `unsafe`, una función con parámetros `mut` o un método `mut`. |
| E0516 | `await_outside_async` | `await` en una función o lambda que no es `async`. |
| E0517 | `async_not_allowed` | `async` donde no cabe (campo de `rune`, `declare`, operador libre…). |
| E0518 | `host_unsupported_target` | El programa invoca `std/js/*` (objetos del navegador) y se compila con `--target cpp`. |

## Memoria (E06xx)

| Código | Nombre | Cuándo aparece |
| --- | --- | --- |
| E0601 | `use_after_move` | Uso de un valor `unique` después de moverlo. |
| E0602 | `exclusive_borrow` | Mutación mientras hay un préstamo activo o mientras se recorre un contenedor. |
| E0603 | `unsafe_required` | Operación `unsafe` fuera de un bloque `unsafe`. |
| E0604 | `mutation_during_iteration` | Mutación estructural durante la iteración. |
| E0605 | `dangling_reference` | Referencia que sobreviviría a su valor. |
| E0606 | `borrow_across_await` | Un `ref<T>` local seguiría vivo después de un `await`. |

## Runes y omens (E07xx)

| Código | Nombre | Cuándo aparece |
| --- | --- | --- |
| E0701 | `omen_not_exhaustive` | `match`/`switch` que no cubre todas las variantes. |
| E0702 | `invalid_omen_variant` | Variante inexistente, payload incorrecto o `flags` con más de 64 bits. |
| E0703 | `invalid_parent` | `parent(...)` mal colocado o rune padre inexistente. |
| E0704 | `field_shadow` | Un campo de la hija sombrea uno heredado. |
| E0705 | `method_shadow` | Sombreo de método no permitido en ese contexto. |
| E0706 | `invalid_operator` | Operador mal declarado o duplicado. |
| E0707 | `enchant_duplicate` | La misma firma está enhechizada dos veces en un realm. |
| E0708 | `ambiguous_method` | Varias sobrecargas compatibles o dos imports con la misma firma. |
| E0709 | `unknown_enchant_target` | `enchanting` apunta a un tipo que no existe ni admite métodos. |
| E0710 | `invalid_mut_receiver` | Método `mut` sobre un tipo por valor (`int`, `double`, omens…). |
| E0711 | `enchant_arity` | El patrón declara un número de sigilos que el tipo no admite. |
| E0712 | `bitfield_width` | Un campo con `bits` no tiene tipo entero o su ancho no cabe en el tipo. |
| E0713 | `meld_field_invalid` | Un campo de `meld` no es trivial, tiene valor por defecto o usa `bits`. |
| E0714 | `meld_access_unsafe` | Se lee un campo de una unión fuera de `unsafe`. |
| E0715 | `opaque_by_value` | Un tipo `opaque` se usa por valor en vez de dentro de `raw<T>`/`ref<T>`. |

## Toolchain (E08xx)

| Código | Nombre | Cuándo aparece |
| --- | --- | --- |
| E0801 | `cpp_emit_failed` | El generador no puede traducir una construcción. |
| E0802 | `toolchain_missing` | No hay compilador de C++ disponible. |
| E0803 | `compile_failed` | El compilador de C++ rechazó el código generado (incluye stderr). |
| E0804 | `async_unsupported_target` | `async`/`await` con `--target cpp`, que todavía no los soporta. |
| E0806 | `target_invalid` | `--target` con un backend desconocido (`cpp` o `js`). |
| E0807 | `js_target_unsupported` | El backend JS todavía no cubre esa construcción o ese comando. |
| E0808 | `js_intrinsic_missing` | Un `declare` de la stdlib no tiene equivalente en el runtime JS. |
| E0809 | `js_emit_failed` | El generador de JavaScript no puede traducir una construcción. |

## LSP y bindgen (E09xx)

| Código | Nombre | Cuándo aparece |
| --- | --- | --- |
| E0901 | `lsp_protocol` | Mensaje JSON-RPC inválido. |
| E0902 | `bindgen_failed` | `clang` no pudo analizar el encabezado. |
| E0903 | `bindgen_unsupported` | Firma nativa que no se puede mapear (variádicas, tipos desconocidos). |
| E0904 | `ts_bindgen_failed` | El lector de `.d.ts` o el emisor de `.d.pengu` falló. |
| E0905 | `ts_bindgen_missing` | No se encontró la Compiler API de TypeScript o los `.d.ts` de `third_party/dts/`. |
| E0906 | `ts_bindgen_stale` | Un `.d.pengu` generado está desactualizado (`--check`). |

## Cuando el LSP marca errores que el CLI no ve

Los diagnósticos los produce el mismo checker, así que un desacuerdo casi
siempre significa que cada uno está leyendo otra cosa. En orden:

1. **Otra stdlib.** `pengu doctor` muestra la huella de la stdlib del binario
   y la del proyecto. Si no coinciden, reinstala el compilador
   (`bash scripts/install.sh`) y recarga el editor.
2. **Otra raíz.** El LSP usa la raíz que anuncia el editor; el CLI, la del
   archivo. Si el proyecto tiene su propio `std/`, necesita un `pengu.toml` en
   la raíz para que ambos coincidan.
3. **Un binario viejo.** Si `pengu doctor --json` no trae `std.fingerprint`,
   el binario es anterior a esta comprobación: reinstálalo.
4. **Un buffer sin guardar.** El LSP analiza lo que se ve en el editor; el CLI,
   lo que hay en disco.

Si tras esto sigue, abre la salida «PenguScript» del editor: ahí queda el
error exacto del servidor.
