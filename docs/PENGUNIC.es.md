# El Manual Pengunic

Cómo escribir PenguScript seguro, idiomático y rápido: el manual de ingeniería
del lenguaje que implementa `psc` 0.60.0.

Es el documento de *práctica* del conjunto de documentación:

| Documento | Responde |
| --- | --- |
| [LANGUAGE.es.md](LANGUAGE.es.md) | ¿Cómo escribo esta construcción y en qué se convierte en C? |
| **PENGUNIC.es.md** (este archivo) | ¿Cómo escribo PenguScript seguro, idiomático y rápido? |
| [STDLIB.es.md](STDLIB.es.md) | ¿Qué módulo estándar uso y dónde está su API? |

English: [PENGUNIC.md](PENGUNIC.md).

<!-- toc -->
- [0. El contrato Pengunic](#0-el-contrato-pengunic)
  - [0.1 Los seis principios](#01-los-seis-principios)
  - [0.2 Cuando los principios chocan](#02-cuando-los-principios-chocan)
  - [0.3 Los tres hábitos](#03-los-tres-hábitos)
  - [0.4 Cómo usar este manual](#04-cómo-usar-este-manual)
  - [0.5 Lo que este manual no es](#05-lo-que-este-manual-no-es)
- [Parte I — Proyecto y toolchain](#parte-i-proyecto-y-toolchain)
- [1. Instalar `psc` y preparar el editor](#1-instalar-psc-y-preparar-el-editor)
  - [1.1 Lo que necesitas](#11-lo-que-necesitas)
  - [1.2 Los comandos que vas a escribir de verdad](#12-los-comandos-que-vas-a-escribir-de-verdad)
  - [1.3 Editor y LSP](#13-editor-y-lsp)
  - [1.4 Formateo](#14-formateo)
  - [1.5 Fijar la versión](#15-fijar-la-versión)
- [2. Anatomía de un proyecto](#2-anatomía-de-un-proyecto)
  - [2.1 `pengu.toml`](#21-pengutoml)
  - [2.2 Estructura de directorios](#22-estructura-de-directorios)
  - [2.3 Lo que produce el build](#23-lo-que-produce-el-build)
- [3. Dependencias](#3-dependencias)
  - [3.1 Declararlas](#31-declararlas)
  - [3.2 El conjunto de comandos](#32-el-conjunto-de-comandos)
  - [3.3 El archivo de lock](#33-el-archivo-de-lock)
  - [3.4 Librerías de C como satélites](#34-librerías-de-c-como-satélites)
- [4. El pipeline de build](#4-el-pipeline-de-build)
  - [4.1 Etapas](#41-etapas)
  - [4.2 Eliminación de código muerto](#42-eliminación-de-código-muerto)
  - [4.3 Perfiles y flags](#43-perfiles-y-flags)
  - [4.4 Medir el build](#44-medir-el-build)
- [Parte II — Estilo y estructura](#parte-ii-estilo-y-estructura)
- [5. Nombres](#5-nombres)
  - [5.1 Archivos, directorios y módulos](#51-archivos-directorios-y-módulos)
  - [5.2 Tipos](#52-tipos)
  - [5.3 Funciones (`weave`)](#53-funciones-weave)
  - [5.4 Métodos y rituales](#54-métodos-y-rituales)
  - [5.5 Variables, constantes, campos, genéricos](#55-variables-constantes-campos-genéricos)
  - [5.6 Prefijos reservados](#56-prefijos-reservados)
- [6. Estructura del módulo y documentación](#6-estructura-del-módulo-y-documentación)
  - [6.1 Orden canónico](#61-orden-canónico)
  - [6.2 Tamaño y cohesión](#62-tamaño-y-cohesión)
  - [6.3 Imports](#63-imports)
  - [6.4 Comentarios de documentación](#64-comentarios-de-documentación)
  - [6.5 Qué publica `psc doc`](#65-qué-publica-psc-doc)
- [7. Expresiones en lugar de sentencias](#7-expresiones-en-lugar-de-sentencias)
  - [7.1 Devuelve la expresión](#71-devuelve-la-expresión)
  - [7.2 `judge` es un valor](#72-judge-es-un-valor)
  - [7.3 Comprensiones en lugar de acumuladores](#73-comprensiones-en-lugar-de-acumuladores)
  - [7.4 `with:` para builders](#74-with-para-builders)
  - [7.5 `do:` para un ámbito local](#75-do-para-un-ámbito-local)
  - [7.6 Cláusulas de guarda en lugar de anidamiento](#76-cláusulas-de-guarda-en-lugar-de-anidamiento)
  - [7.7 Recursión](#77-recursión)
  - [7.8 Nombra el argumento que carga el significado](#78-nombra-el-argumento-que-carga-el-significado)
  - [7.9 Repite un receptor con `with`](#79-repite-un-receptor-con-with)
  - [7.10 Construye mapas con literales](#710-construye-mapas-con-literales)
  - [7.11 Itera con la forma propia del contenedor](#711-itera-con-la-forma-propia-del-contenedor)
  - [7.12 Desestructura una runa cuando sus campos son lo importante](#712-desestructura-una-runa-cuando-sus-campos-son-lo-importante)
- [8. Anti-patrones](#8-anti-patrones)
  - [8.1 Construcción de strings](#81-construcción-de-strings)
  - [8.2 Propiedad de los parámetros](#82-propiedad-de-los-parámetros)
  - [8.3 Errores que pierden la causa](#83-errores-que-pierden-la-causa)
  - [8.4 Copiar y pegar por tipo](#84-copiar-y-pegar-por-tipo)
- [Parte III — Código seguro](#parte-iii-código-seguro)
- [9. Tipos, representación y aritmética](#9-tipos-representación-y-aritmética)
  - [9.1 La tabla de tipos](#91-la-tabla-de-tipos)
  - [9.2 Semántica de valor y de referencia](#92-semántica-de-valor-y-de-referencia)
  - [9.3 Aritmética y overflow](#93-aritmética-y-overflow)
  - [9.4 Comprobación de límites](#94-comprobación-de-límites)
  - [9.5 Elegir el tipo correcto](#95-elegir-el-tipo-correcto)
- [10. Conversiones](#10-conversiones)
  - [10.1 Las conversiones numéricas truncan](#101-las-conversiones-numéricas-truncan)
  - [10.2 Texto a números](#102-texto-a-números)
  - [10.3 Caracteres y bytes](#103-caracteres-y-bytes)
  - [10.4 Strings, slices y bytes](#104-strings-slices-y-bytes)
  - [10.5 Newtypes](#105-newtypes)
  - [10.6 `transmute`](#106-transmute)
- [11. Errores](#11-errores)
  - [11.1 `maybe` o `result`](#111-maybe-o-result)
  - [11.2 Diseñar el tipo de error](#112-diseñar-el-tipo-de-error)
  - [11.3 Propagación](#113-propagación)
  - [11.4 `error` y `or:`](#114-error-y-or)
  - [11.5 Política de `panic`](#115-política-de-panic)
- [12. `defer`, `errdefer` y `banish`](#12-defer-errdefer-y-banish)
  - [12.1 Las tres herramientas de limpieza](#121-las-tres-herramientas-de-limpieza)
  - [12.2 `defer`](#122-defer)
  - [12.3 `errdefer`](#123-errdefer)
  - [12.4 Colocación](#124-colocación)
  - [12.5 Caminos de error](#125-caminos-de-error)
- [13. Concurrencia](#13-concurrencia)
  - [13.1 Qué existe](#131-qué-existe)
  - [13.2 Mutex](#132-mutex)
  - [13.3 Atómicos](#133-atómicos)
  - [13.4 Canales](#134-canales)
  - [13.5 Reglas para compartir](#135-reglas-para-compartir)
  - [13.6 Testear concurrencia](#136-testear-concurrencia)
  - [13.7 Corrutinas](#137-corrutinas)
  - [13.8 El reactor: planificar es explícito](#138-el-reactor-planificar-es-explícito)
- [14. Interoperabilidad con C, con seguridad](#14-interoperabilidad-con-c-con-seguridad)
  - [14.1 El archivo de frontera](#141-el-archivo-de-frontera)
  - [14.2 Propiedad a través de la frontera](#142-propiedad-a-través-de-la-frontera)
  - [14.3 Envolver](#143-envolver)
  - [14.4 `antiquus`](#144-antiquus)
  - [14.5 `psc bind`](#145-psc-bind)
  - [14.6 ABI](#146-abi)
- [15. Entrada no confiable](#15-entrada-no-confiable)
  - [15.1 Dónde acaba la confianza](#151-dónde-acaba-la-confianza)
  - [15.2 Validar y luego convertir](#152-validar-y-luego-convertir)
  - [15.3 Rutas](#153-rutas)
  - [15.4 URLs, JSON y regex](#154-urls-json-y-regex)
  - [15.5 Límites de descompresión y asignación](#155-límites-de-descompresión-y-asignación)
  - [15.6 Secretos](#156-secretos)
- [16. Checklist de seguridad](#16-checklist-de-seguridad)
  - [16.1 Memoria](#161-memoria)
  - [16.2 Entrada](#162-entrada)
  - [16.3 FFI](#163-ffi)
  - [16.4 Vías de escape](#164-vías-de-escape)
- [Parte IV — Memoria manual](#parte-iv-memoria-manual)
- [17. El modelo de memoria](#17-el-modelo-de-memoria)
  - [17.1 Qué garantiza el lenguaje](#171-qué-garantiza-el-lenguaje)
  - [17.2 La tabla de propiedad](#172-la-tabla-de-propiedad)
  - [17.3 Runes con `Nexus`](#173-runes-con-nexus)
  - [17.4 Mover es copiar](#174-mover-es-copiar)
  - [17.5 La pila y el montón, para quien viene de Python o Java](#175-la-pila-y-el-montón-para-quien-viene-de-python-o-java)
  - [17.6 Puntero, dueño y préstamo](#176-puntero-dueño-y-préstamo)
  - [17.7 Capa 1 — `derive Drop`](#177-capa-1-derive-drop)
  - [17.8 Capa 2 — `std.consortium`](#178-capa-2-stdconsortium)
  - [17.9 Capa 3 — copy-on-write](#179-capa-3-copy-on-write)
  - [17.10 Caso de estudio: un ECS](#1710-caso-de-estudio-un-ecs)
  - [17.11 Cómo elegir capa](#1711-cómo-elegir-capa)
  - [17.12 Reglas](#1712-reglas)
- [18. `banish` en profundidad](#18-banish-en-profundidad)
  - [18.1 Qué acepta](#181-qué-acepta)
  - [18.2 Comportamiento por tipo](#182-comportamiento-por-tipo)
  - [18.3 Contenedores de contenedores](#183-contenedores-de-contenedores)
  - [18.4 Vistas y parámetros](#184-vistas-y-parámetros)
- [19. Vistas, préstamos y tiempos de vida](#19-vistas-préstamos-y-tiempos-de-vida)
  - [19.1 Las tres vistas](#191-las-tres-vistas)
  - [19.2 Devolver una vista](#192-devolver-una-vista)
  - [19.3 Reglas de préstamo](#193-reglas-de-préstamo)
- [20. Patrones](#20-patrones)
  - [20.1 Parejas constructor / destructor](#201-parejas-constructor-destructor)
  - [20.2 Transferencia de propiedad](#202-transferencia-de-propiedad)
  - [20.3 Parámetros de salida](#203-parámetros-de-salida)
  - [20.4 Estado de módulo](#204-estado-de-módulo)
  - [20.5 Builder para strings](#205-builder-para-strings)
  - [20.6 Arena para una fase](#206-arena-para-una-fase)
- [21. Fugas y corrupción](#21-fugas-y-corrupción)
  - [21.1 Caso 1 — handle de string copiado](#211-caso-1-handle-de-string-copiado)
  - [21.2 Caso 2 — camino de error antes del `defer`](#212-caso-2-camino-de-error-antes-del-defer)
  - [21.3 Caso 3 — liberar una vista](#213-caso-3-liberar-una-vista)
  - [21.4 Caso 4 — lista de strings](#214-caso-4-lista-de-strings)
  - [21.5 Caso 5 — doble banish de un rune `Nexus`](#215-caso-5-doble-banish-de-un-rune-nexus)
  - [21.6 Herramientas](#216-herramientas)
- [22. Estrategia de asignación](#22-estrategia-de-asignación)
  - [22.1 La pila primero](#221-la-pila-primero)
  - [22.2 Una asignación y luego crecer](#222-una-asignación-y-luego-crecer)
  - [22.3 Reutilizar en lugar de reasignar](#223-reutilizar-en-lugar-de-reasignar)
  - [22.4 Agrupar por tiempo de vida](#224-agrupar-por-tiempo-de-vida)
  - [22.5 Medir](#225-medir)
- [Parte V — Tests](#parte-v-tests)
- [23. La pirámide de tests](#23-la-pirámide-de-tests)
  - [23.1 Qué testear y dónde](#231-qué-testear-y-dónde)
  - [23.2 Qué debe testearse](#232-qué-debe-testearse)
- [24. Bloques `test`, `ward` y `trial`](#24-bloques-test-ward-y-trial)
  - [24.1 Un bloque de test](#241-un-bloque-de-test)
  - [24.2 `std.ward`](#242-stdward)
  - [24.3 Estructura: preparar, actuar, afirmar](#243-estructura-preparar-actuar-afirmar)
  - [24.4 Tests dirigidos por tabla](#244-tests-dirigidos-por-tabla)
  - [24.5 Errores y propiedad](#245-errores-y-propiedad)
  - [24.6 `std.trial`](#246-stdtrial)
- [25. `psc test`](#25-psc-test)
  - [25.1 Ejecutar](#251-ejecutar)
  - [25.2 `--json`](#252---json)
  - [25.3 Escribir para el runner](#253-escribir-para-el-runner)
- [26. Casos difíciles](#26-casos-difíciles)
  - [26.1 Ficheros y fixtures](#261-ficheros-y-fixtures)
  - [26.2 FFI](#262-ffi)
  - [26.3 Concurrencia](#263-concurrencia)
  - [26.4 Memoria](#264-memoria)
  - [26.5 Wasm](#265-wasm)
  - [26.6 Determinismo](#266-determinismo)
- [27. CI](#27-ci)
  - [27.1 El pipeline](#271-el-pipeline)
  - [27.2 Un job de memoria](#272-un-job-de-memoria)
  - [27.3 Puertas](#273-puertas)
- [Parte VI — Librerías y bindings](#parte-vi-librerías-y-bindings)
- [28. Diseñar una API pública](#28-diseñar-una-api-pública)
  - [28.1 Las reglas](#281-las-reglas)
  - [28.2 Forma](#282-forma)
  - [28.3 Rune de opciones](#283-rune-de-opciones)
- [29. Versionado y deprecación](#29-versionado-y-deprecación)
  - [29.1 Versiones](#291-versiones)
  - [29.2 Deprecación](#292-deprecación)
  - [29.3 Changelog](#293-changelog)
- [30. Empaquetar una librería](#30-empaquetar-una-librería)
  - [30.1 Estructura](#301-estructura)
  - [30.2 Símbolos](#302-símbolos)
  - [30.3 Consumir una librería](#303-consumir-una-librería)
  - [30.4 Documentación](#304-documentación)
- [31. Escribir un binding de C](#31-escribir-un-binding-de-c)
  - [31.1 Archivos](#311-archivos)
  - [31.2 Reglas del wrapper](#312-reglas-del-wrapper)
  - [31.3 Checklist](#313-checklist)
- [32. `psc bind`](#32-psc-bind)
  - [32.1 Generar](#321-generar)
  - [32.2 Revisar](#322-revisar)
  - [32.3 Regenerar](#323-regenerar)
- [33. Satélites](#33-satélites)
- [34. ABI y release](#34-abi-y-release)
  - [34.1 Qué es estable](#341-qué-es-estable)
  - [34.2 Layout](#342-layout)
  - [34.3 Símbolos exportados](#343-símbolos-exportados)
  - [34.4 Checklist de release](#344-checklist-de-release)
- [Parte VII — Rendimiento y entrega](#parte-vii-rendimiento-y-entrega)
- [35. Rendimiento](#35-rendimiento)
  - [35.1 Perfiles](#351-perfiles)
  - [35.2 Eliminación de código muerto](#352-eliminación-de-código-muerto)
  - [35.3 Microoptimizaciones que importan](#353-microoptimizaciones-que-importan)
  - [35.4 Medir](#354-medir)
  - [35.5 `--release-unsafe`](#355---release-unsafe)
- [36. WebAssembly y assets](#36-webassembly-y-assets)
  - [36.1 Objetivo](#361-objetivo)
  - [36.2 `std.web`](#362-stdweb)
  - [36.3 Assets](#363-assets)
  - [36.4 Tamaño](#364-tamaño)
- [37. Entrega](#37-entrega)
  - [37.1 El checklist de release](#371-el-checklist-de-release)
  - [37.2 Qué necesitan los usuarios](#372-qué-necesitan-los-usuarios)
  - [37.3 Después de la release](#373-después-de-la-release)
- [Apéndice A — De C a Pengunic](#apéndice-a-de-c-a-pengunic)
- [Apéndice B — Checklist de estilo](#apéndice-b-checklist-de-estilo)
- [Apéndice C — Checklist de pull request](#apéndice-c-checklist-de-pull-request)
- [Apéndice D — Glosario](#apéndice-d-glosario)
- [Apéndice E — FAQ](#apéndice-e-faq)
<!-- /toc -->

## 0. El contrato Pengunic

"Pengunic" es el adjetivo para el código que pertenece a este ecosistema: seguro
por defecto, explícito con la propiedad, rápido sin trucos y legible seis meses
después por alguien que no lo escribió. No es un rasgo de personalidad del
compilador ni lo impone un linter: es un conjunto de decisiones que este manual
toma por ti, con el motivo adjunto.

### 0.1 Los seis principios

1. **El compilador comprueba lo que puede; tú eres dueño de lo que no.** Se
   comprueban tipos, aridad, exhaustividad y límites. No se comprueban tiempos
   de vida, aliasing ni ausencia de fugas. Cada capítulo dice en qué lado de esa
   línea estás.
2. **La propiedad es explícita, siempre.** Un valor es propio, prestado o
   movido. Si una función toma propiedad, su nombre y su documentación lo dicen.
   No hay copia oculta ni recolector de basura que esconda un error.
3. **Valores primero, referencias cuando hacen falta.** Devuelve `Task`, no
   `ref to Task`. Toma `string` por valor; recurre a `ref to T` solo para mutar
   o para datos grandes que no deben moverse.
4. **Los errores son valores.** La ausencia es `maybe`; el fallo con causa es
   `result`. `panic` es para bugs, nunca para una entrada que podrías haber
   rechazado.
5. **C predecible.** Cada construcción baja a C que podrías haber escrito tú.
   Si no puedes imaginar el C, la construcción no sirve para el trabajo.
6. **La documentación es parte de la API.** Los comentarios `##` son el
   contrato que publica `psc doc`; una API pública sin documentar es una API
   inacabada.

### 0.2 Cuando los principios chocan

Usa este orden, y solo este:

```
safety  >  clarity  >  performance
```

El rendimiento es una propiedad medida, no estética. Puedes romper la
"claridad" por una mejora medida, y puedes romper la "seguridad" solo a través
de las vías de escape documentadas (`transmute`, `unsafe`, `--release-unsafe`,
`antiquus`), en un comentario que explique por qué, con un test que fije el
comportamiento.

### 0.3 Los tres hábitos

* **Libera lo que asignas.** Cada asignación con propiedad tiene exactamente un
  `banish` o un `defer banish` en todos los caminos, incluidos los de error.
* **Nombra el fallo.** El tipo de error de un `result` es un `omen` con
  nombre, no `string` ni un parámetro de salida `bool`.
* **Testea la frontera.** El código con más probabilidad de estar mal es donde
  entran los datos: argv, ficheros, red, FFI. Testea eso primero.

### 0.4 Cómo usar este manual

| Si estás… | Lee |
| --- | --- |
| empezando un proyecto | Capítulos 1–4 |
| escribiendo tu primer módulo | Capítulos 5–8 |
| revisando un PR | 8.3, 16.6, 21.5, 34.6 |
| depurando un crash o una fuga | Capítulos 17–21 |
| añadiendo tests a una librería sin tests | Capítulos 23–27 |
| publicando una librería o un binding | Capítulos 28–34 |
| haciendo algo más rápido | Capítulos 22 y 35 |
| portando código C | Capítulos 9, 14 y Apéndice A |

Cada capítulo termina con una caja **Reglas**: la versión corta que puedes
aplicar sin releer el capítulo.

### 0.5 Lo que este manual no es

No enseña sintaxis: eso es [LANGUAGE.md](LANGUAGE.md), construcción a
construcción, con el C que genera. No cataloga la librería estándar: eso es
[STDLIB.es.md](STDLIB.es.md), módulo a módulo, con enlaces a la API generada.

## Parte I — Proyecto y toolchain

## 1. Instalar `psc` y preparar el editor

### 1.1 Lo que necesitas

Un compilador de C (`gcc` o `clang`), el build sin `make` que hace `psc`, y el
binario `psc`. Desde un checkout:

```console
$ bash tools/build_bootstrap.sh     # builds build/psc-stage0 from the C bundle
$ ./build/psc-stage0 build .        # self-hosts build/psc
$ ./build/psc --version
psc 0.60.0 (F13)
```

A partir de ahí usas `build/psc`. `psc doctor` informa de lo que encontró: el
compilador de C, las rutas de include/runtime y las piezas opcionales (libcurl
para `std.petitio`, libffi para `std.ffi_call`, libsodium para `std.secrets`).

### 1.2 Los comandos que vas a escribir de verdad

| Comando | Cuándo |
| --- | --- |
| `psc check` | tras cada edición; no genera C |
| `psc build` | para producir el artefacto |
| `psc run FILE -- args` | para probar un archivo suelto o el proyecto |
| `psc test` | antes de cada commit |
| `psc fmt` | antes de cada commit |
| `psc doc` | cuando cambió la API pública |

`psc check` es el bucle rápido; `psc build --profile release` es el lento. Ambos
son incrementales gracias a la caché de build, salvo que pases `--no-cache`.

### 1.3 Editor y LSP

`psc lsp` habla el Language Server Protocol por stdio. El repositorio incluye un
cliente de VS Code en `vscode-extension/`, y sirve cualquier cliente que sepa
lanzar un servidor stdio:

```console
$ psc lsp
```

El servidor publica diagnósticos (los mismos códigos que `psc check`),
completado, ir a definición y hover sobre la documentación `##`. No sustituye
al chequeo de tipos: mantén `psc check` en tu hook de guardado.

### 1.4 Formateo

`psc fmt` es el formateador canónico. Lee `.pengufmt.toml` desde el directorio
del archivo hacia arriba (líneas planas `clave = valor`):

| Clave | Valores | Por defecto |
| --- | --- | --- |
| `indent` / `tab_size` / `indent_size` / `indent_width` | entero positivo | `4` |
| `tabs` | `true` / `false` | `false` |
| `insert_spaces` | `true` / `false` (inverso de `tabs`) | `true` |
| `blank_lines_max` | entero ≥ 0 | `2` |

```console
$ psc fmt --check        # exit 1 if a file would change
$ psc fmt --diff         # show the change
$ psc fmt src/ lib/      # format in place
```

Formatea antes de la revisión, no durante: un diff de formato mezclado con un
diff de lógica no se puede revisar.

### 1.5 Fijar la versión

`psc --version` informa la versión del compilador, que afecta al ABI generado
para `rune`, `echo` y `omen`. Anota en el README la versión con la que probaste
el proyecto y ejecuta `psc doctor` en CI.

**Reglas**

* Una versión de compilador por proyecto, escrita.
* `psc check` al guardar, `psc fmt --check` y `psc test` antes del commit.
* Nunca mezcles un cambio de formato con un cambio de comportamiento en un
  commit.

## 2. Anatomía de un proyecto

### 2.1 `pengu.toml`

`pengu.toml` es el único formato de manifiesto aceptado (`pengu.yaml` y
`pengu.json` se rechazan con un error explícito). Un ejemplo completo:

```toml
[project]
name = "tasks"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"            # exe | c | obj | static | shared
output_name = "tasks"

[build]
src_dir = "src"
lib_dir = "lib"
include_dir = "include"
c_dir = "c"
build_dir = "build"
target = ""               # triple, or "wasm"
strict_c99 = false
links = []
lib_dirs = []
include_dirs = []
cflags = ["-Wall", "-std=c11"]
ldflags = []
defines = []
cc = "gcc"

[assets]
dir = "assets"
module = "arca"
embed = true
exclude = ["**/*.tmp"]

[profiles.release]
cflags = ["-O3", "-DNDEBUG", "-ffunction-sections", "-fdata-sections"]
defines = ["NDEBUG"]
```

Todas las claves son opcionales; los valores por defecto de arriba son los que
escribe `psc init`. Dos detalles importan en la práctica:

* `output` cambia el artefacto, no el lenguaje. `static`/`shared` construyen
  una librería y omiten el envoltorio `main`; `c` se detiene tras emitir C.
* `profiles.<nombre>` se selecciona con `--profile=<nombre>`; `debug` y
  `release` existen siempre, y cualquier otro nombre que definas se suma.

### 2.2 Estructura de directorios

```
tasks/
  pengu.toml
  src/
    main.pengu
    tasks/
      model.pengu
      store.pengu
  lib/            # dependencies installed by psc add
  include/        # your C headers, for bindings
  c/              # hand-written C compiled alongside
  assets/         # embedded by psc assets
  build/          # artifacts and cache (never edit)
```

Las rutas de módulo siguen a los directorios: `src/tasks/store.pengu` es
`tasks.store`. El archivo de entrada es `project.entry` y debe existir.

### 2.3 Lo que produce el build

| `output` | Artefacto |
| --- | --- |
| `exe` | ejecutable `build/<output_name>` |
| `c` | solo `build/<output_name>.c` |
| `obj` | `build/<output_name>.o` |
| `static` | `build/lib<output_name>.a` |
| `shared` | `build/lib<output_name>.so` (`.dylib` en macOS) |

`build/` es desechable: `psc clean` lo borra, `psc gc` elimina solo las entradas
de caché obsoletas.

**Reglas**

* `pengu.toml` se versiona; `build/` nunca.
* Un proyecto, un `src_dir`. Los experimentos van en `scratch/`.
* Para librerías, `output = "static"` o `"shared"`, nunca `exe`.

## 3. Dependencias

### 3.1 Declararlas

Las dependencias viven bajo `[dependencies]` en `pengu.toml`:

```toml
[dependencies.json]
url = "https://github.com/example/pengu-json"
tag = "v1.2.0"
version = "^1.2"

[dependencies.internal]
path = "../internal-lib"
```

`url` significa git, `path` significa un checkout local. `branch`, `tag` y
`version` acotan la resolución; `version` acepta una restricción semver.

### 3.2 El conjunto de comandos

| Comando | Efecto |
| --- | --- |
| `psc add SOURCE` | resuelve, instala en `lib/`, escribe `pengu.lock` |
| `psc remove NAME` | desinstala y quita la entrada del lock |
| `psc update` | vuelve a resolver dentro de las restricciones declaradas |
| `psc upgrade NAME` | mueve una dependencia a una versión más nueva |
| `psc verify` | comprueba que `lib/` coincide con `pengu.lock` |
| `psc vendor` | copia las dependencias a `vendor/` |

`psc add` ejecuta el script de build de la dependencia salvo que pases
`--no-build`; hace falta `--trust` para ejecutarlo, porque un script de build
ejecuta código.

### 3.3 El archivo de lock

`pengu.lock` registra los commits y versiones resueltos exactos. Versiónalo.

`psc build --locked` falla si el lock falta o está desactualizado; `--frozen` hace
lo mismo y nunca toca la red. Usa `--frozen` en CI y en builds de release,
`--locked` en la máquina de desarrollo.

### 3.4 Librerías de C como satélites

`std_c/<nombre>/` contiene fuentes de C vendorizadas (cada una con `README.md`,
`LICENSE`, `SOURCE`, `pengu.pkg`). No se descargan en el build;
`tools/fetch_satellite.sh` las vendoriza y `tools/satellite_new.sh` crea una
nueva. El capítulo 33 cubre las convenciones.

**Reglas**

* Versiona `pengu.lock`; nunca lo edites a mano.
* CI construye con `--frozen`.
* Fija un tag o un commit para todo lo que publiques; una rama no es una
  versión.

## 4. El pipeline de build

### 4.1 Etapas

```
.pengu files
   │ lexer        tokens, layout, literals
   │ parser       AST
   │ sema         names, types, ownership, exhaustiveness, bounds
   │ codegen      C (with #line markers), DCE, monomorphisation
   ▼
C compiler (gcc/clang)  →  object files  →  linker
```

`psc emit-c FILE` se detiene tras el codegen e imprime el C; `psc expand`
imprime el bundle completo, incluido el runtime. Cuando un diagnóstico no se
entiende, leer el C suele explicarlo.

### 4.2 Eliminación de código muerto

El compilador solo emite código alcanzable: `main`, las raíces `@export` y todo
lo que usan transitivamente. `--prune-types` elimina además helpers de tipo sin
uso (`_pengu_clone_*`, `_pengu_cleanup_*`), y `--prune-native` quita las
librerías nativas que ninguna función viva necesita. `--no-dce` lo desactiva
todo y solo sirve para depurar el compilador.

### 4.3 Perfiles y flags

| Flag | Efecto |
| --- | --- |
| `--profile=debug` | `-O0 -g`, comprobaciones activas |
| `--profile=release` | `-O3 -DNDEBUG`, comprobaciones activas salvo `--release-unsafe` |
| `--release-unsafe` | elimina las comprobaciones de límites y overflow |
| `--strict-c99` | C99 portable, sin statement expressions |
| `--target=wasm` | Emscripten |

`--release-unsafe` es una decisión medida, documentada en el commit que la toma,
con tests que cubren las entradas cuyas comprobaciones se eliminaron.

### 4.4 Medir el build

```console
$ psc time            # per-phase timings
$ psc build --verbose # the exact cc command line
$ psc tree            # the module graph
```

La caché se direcciona por contenido; `--no-cache` fuerza un build en frío y
`psc gc` elimina las entradas que ningún proyecto actual referencia.

**Reglas**

* Lee `psc emit-c` antes de optimizar; sabe qué estás optimizando.
* `--release-unsafe` exige un comentario, un test y una medición.
* Si el build es lento, perfila con `psc time` antes de tocar flags.

## Parte II — Estilo y estructura

## 5. Nombres

Los nombres son la documentación más barata y lo más caro de cambiar después.
Cada regla de abajo existe porque un nombre que la cumple se puede leer sin
abrir el archivo.

### 5.1 Archivos, directorios y módulos

| Elemento | Regla | Ejemplo |
| --- | --- | --- |
| Archivo fuente | `snake_case.pengu` | `store.pengu`, `json_pointer.pengu` |
| Archivo de declaraciones | `snake_case.d.pengu` | `curl.d.pengu` |
| Archivo de tests | `<module>_test.pengu` | `store_test.pengu` |
| Directorio | `snake_case/` | `src/tasks/` |
| Módulo | `snake_case`, sustantivo concreto | `std.scrolls`, `tasks.store` |

El nombre de un módulo es un sustantivo. Si no puedes nombrarlo con un
sustantivo, no tiene una sola responsabilidad: divídelo. Nunca `utils`,
`helpers`, `common`, `misc`, `base`, `core`, `manager`.

### 5.2 Tipos

| Constructo | Estilo | Ejemplo |
| --- | --- | --- |
| `rune` | `PascalCase`, singular, concreto | `Task`, `HttpRequest` |
| `omen` | `PascalCase`, singular, categoría | `Priority`, `JsonKind` |
| `echo` | `PascalCase`, singular | `Number`, `Value` |
| `seal` | `PascalCase`, lo que mide | `UserId`, `Meters` |
| `alias` | `PascalCase` | `Handler`, `Buffer` |
| `concept` | `PascalCase`, capacidad, singular | `Formatter`, `Nexus` |
| `shard` | `T`, `U`, `K`, `V`, `E` o un `PascalCase` descriptivo | `Item`, `Key` |

Un tipo que envuelve un recurso se nombra por el recurso, no por la operación:
`Mutex`, `ChanInt`, `Arena` — no `LockHelper`, `Syncer`.

### 5.3 Funciones (`weave`)

`snake_case`, verbo en forma base, sin `-ing`, sin el tipo en el nombre.

| Tipo | Forma | Ejemplo |
| --- | --- | --- |
| Acción | verbo transitivo | `parse`, `split`, `merge` |
| Predicado | `is_`, `has_`, `can_`, `should_` | `is_empty`, `has_key` |
| Conversión infalible | `to_*` | `to_string`, `to_upper` |
| Conversión falible | `parse_*` → `maybe`/`result` | `parse_int` |
| Constructor | `new`, `from_*`, `with_*` | `new`, `from_json` |
| Mutación | verbo | `push`, `clear`, `set_volume` |
| Getter no trivial | `get_*` | `get_or`, `getenv_or` |
| Getter trivial | sustantivo | `len`, `first`, `keys` |
| I/O de línea | `read_*`, `write_*` | `read_file` |
| Validación | `check_*` → `bool`; `assert_*` aborta | `check_range` |
| Iteración | `iter_*`, `each_*`, `gen_*` | `gen_digits` |
| Extracción con valor por defecto | sufijo `_or` | `at_or`, `arg_at_or` |

### 5.4 Métodos y rituales

* Un método no repite su tipo: `Task.complete`, no `Task.complete_task`.
* Los mutadores son verbos y usan `self->`; las consultas son sustantivos o
  `is_*`/`has_*`.
* Los constructores `ritual` son `new`, `from_*`, `with_*`, `default`; un
  constructor falible es `try_*`. Nunca `create`, `make`, `build` como nombre
  principal.
* Un método que devuelve un valor nuevo del mismo tipo (`plus`,
  `with_capacity`) no muta `self`. Un método `@mutates` se nombra con el verbo
  que aplica y devuelve el receptor.

### 5.5 Variables, constantes, campos, genéricos

| Elemento | Regla | Ejemplo |
| --- | --- | --- |
| Local | sustantivo `snake_case` | `retry_count`, `user` |
| Constante de nivel superior | `SCREAMING_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_PORT` |
| Campo | sustantivo `snake_case` | `created_at`, `is_ready` |
| Índice de bucle | `i`, `j`, `k` en bucles cortos; si no, un sustantivo | `for i from 0 to n` |
| Parámetro genérico | una mayúscula o `PascalCase` | `T`, `E`, `Item` |

Sin notación húngara (`str_name`), sin sufijos de tipo (`count_int`), sin
abreviaturas que no estén en el glosario (`cfg` → `config`, `req` → `request`,
`ctx` → `context`). Los nombres de una letra son solo para índices de bucle y
para parámetros genéricos.

### 5.6 Prefijos reservados

* `pengu_*` y `_pengu_*` pertenecen al runtime y al C generado. Nunca los
  declares.
* `std_*` pertenece a la capa C de la librería estándar.
* Para `@export("symbol")`, usa un prefijo de proyecto: `tasks_fast_hash`, no
  `fast_hash` (que puede colisionar con libc).

**Reglas**

* El nombre dice qué es, no cómo está implementado.
* Singular para tipos; plural solo para colecciones del mismo tipo.
* Sin módulo `utils`/`helpers`/`misc`, sin `manager`, sin `data`, sin `info`.
* Un renombrado es un cambio de API pública: depreca, no renombres en silencio.

## 6. Estructura del módulo y documentación

### 6.1 Orden canónico

Un módulo se lee de arriba abajo en este orden. El revisor debe poder encontrar
una declaración por su posición.

```pengu-fragment
## Module docstring: what it does, what it does not do, ownership rules.

include "mylib.h"
link "mylib"

import std.spark
import std.scrolls as s
import tasks.model

const MAX_RETRIES as int is 3

concept Formatter:
    weave format into string

rune Task:
    title as string
    done as bool

echo Value:
    number as int
    text as string

omen Priority:
    Low is 0
    Normal is 1
    High is 2

seal TaskId as int

bind Task with Formatter:
    weave format into string:
        return self->title

enchanting Task:
    weave complete into void:
        set self->done is true

weave make_task with title as string into Task:
    return with title is title, done is false

weave helper_pattern with t as Task into bool:
    return t.done

test "make_task defaults to pending":
    let t is calling make_task with "x"
    calling ward.assert_eq_bool with t.done, false
```

### 6.2 Tamaño y cohesión

* Una responsabilidad por módulo. Si el docstring necesita un "y", divídelo.
* Límite blando: 400 líneas de cuerpo. Más allá, el módulo suele esconder dos
  módulos.
* Los helpers viven junto a su único llamador; un helper usado por dos módulos
  pasa a público y documentado (o se mueve a un módulo compartido).
* Sin estado mutable a nivel de módulo salvo que el estado *sea* el tema del
  módulo (la configuración de `std.whisper`). Documenta cada `static var`.

### 6.3 Imports

* Importa lo que usas; el formateador mantiene un `import` por línea.
* Alias solo para resolver una colisión real o acortar un nombre de módulo muy
  largo (`import std.scrolls as s`). Nunca un alias engañoso.
* Los imports no son re-exports: un módulo que re-exporta debe decirlo en su
  docstring.
* Importar `std.*` es gratis en tiempo de ejecución (DCE elimina lo que no se
  usa), así que no hay razón para esconder una dependencia de std tras un alias.

### 6.4 Comentarios de documentación

`##` es la documentación; `#` es una nota para quien lee el fuente. `psc doc`
publica solo `##`.

```pengu-fragment
## Parses a decimal integer.
##
## Returns `maybe none` when the text is not a complete integer; the caller
## decides whether that is an error. Never panics.
##
## ## Example
## ```pengu
## let n as maybe int is calling parse_int with "42"
## ```
weave parse_int with text as string into maybe int:
    ...
```

Reglas del docstring de módulo: una frase de propósito; qué **no** hace;
reglas de propiedad/tiempo de vida si hay alguna asignación; un ejemplo corto.
Para una función: qué devuelve en cada camino de fallo, si el resultado es
propio y si los argumentos son prestados.

### 6.5 Qué publica `psc doc`

Una página por módulo, una sección `###` por símbolo exportado, la firma y el
texto `##`. `docs/api/` en este repositorio es la salida de referencia. Si un
símbolo no tiene `##`, su página dice `_Undocumented._`: eso es un bug.

**Reglas**

* Todo símbolo público tiene un comentario `##`; los helpers privados pueden
  tenerlo.
* La primera línea es una frase completa en imperativo ("Parsea…", "Devuelve…").
* Documenta propiedad y fallo explícitamente para todo lo que asigne memoria.
* `psc doc` debe ejecutarse limpio antes de una release.

## 7. Expresiones en lugar de sentencias

Una expresión de PenguScript produce un valor; una sentencia produce un efecto.
Cuando lo que necesitas es un valor, prefiere la forma de expresión: tiene una
sola asignación, ningún acumulador mutable y ninguna rama que pueda olvidarse de
asignarlo.

### 7.1 Devuelve la expresión

```pengu-fragment
# ❌ con forma de sentencia
weave grade with score as int into string:
    var g as string is "F"
    if score >= 90:
        set g is "A"
    else if score >= 80:
        set g is "B"
    return g

# ✅ con forma de expresión
weave grade with score as int into string:
    return if score >= 90:
        "A"
    else if score >= 80:
        "B"
    else:
        "F"
```

### 7.2 `judge` es un valor

```pengu-fragment
weave priority_name with p as Priority into string:
    return judge p:
        when Priority.Low -> "low"
        when Priority.Normal -> "normal"
        when Priority.High -> "high"
```

`judge` debe ser exhaustivo (`E0044`); la rama `else` es solo para un comodín
sobre un conjunto abierto.

### 7.3 Comprensiones en lugar de acumuladores

```pengu-fragment
# ❌ asignación por iteración y O(n²)
var out as list of string is list of string
for x in xs:
    calling out.push with "{x}"

# ✅ una expresión, una asignación
let out as list of string is for x in xs then "{x}"
```

### 7.4 `with:` para builders

`with:` convierte una secuencia de sentencias `set .field` en una construcción
con nombre. Es el único sitio donde `.field` aparece a la izquierda de `set`.

```pengu-fragment
let req as Request is with:
    set .method is "GET"
    set .timeout_ms is 5000
```

### 7.5 `do:` para un ámbito local

Usa `do:` cuando un temporal no deba filtrarse al ámbito que lo rodea:

```pengu-fragment
let total as int is do:
    let base is 100
    let tax is 21
    base + tax
```

### 7.6 Cláusulas de guarda en lugar de anidamiento

```pengu-fragment
weave handle with req as Request into result of Response to HttpError:
    if not req.is_valid:
        return calling err_of with HttpError.BadRequest
    let body as string is try calling read_body with req
    defer banish body
    return calling ok_of with (calling respond with body)
```

### 7.7 Recursión

La recursión está bien cuando los datos son recursivos (árboles, JSON, rutas).
Cuando no lo son, un bucle es más claro y no hace crecer la pila de C:

```pengu-fragment
# ✅ recursivo por naturaleza
weave depth with node as Node into int:
    if node.children.len == 0:
        return 1
    var best as int is 0
    for c in node.children:
        let d is calling depth with c
        if d > best:
            set best is d
    return best + 1
```

**Reglas**

* Una asignación por valor calculado; nada de "declarar y asignar en cada rama".
* `judge` para categorías, `if` para condiciones, comprensiones para listas.
* Cláusulas de guarda arriba; el camino feliz al final.
* Recursión solo sobre datos recursivos.

### 7.8 Nombra el argumento que carga el significado

Tres enteros sueltos en una llamada no dicen nada; una bandera booleana dice
menos que su nombre. Nombra un argumento cuando el nombre del parámetro forma
parte del significado, y déjalo posicional cuando el orden es obvio:

```pengu-fragment
calling window.resize with 800, 600
calling window.configure with resizable is false, title is "Logs"
```

**Reglas**

* Nombra argumentos que sean banderas, modos o unidades; deja posicionales los
  órdenes obvios.
* Posicionales primero, luego nombrados: nunca un posicional después de un nombre.
* Un argumento nombrado no cuesta nada en tiempo de ejecución: el compilador lo
  ordena y emite la misma llamada C que la forma posicional.
* Los pasos de cadena y tubería aceptan solo posicionales; cuando un paso
  necesite nombre, llama al método directamente sobre su receptor.

### 7.9 Repite un receptor con `with`

Cuando un valor protagoniza la mayor parte de un bloque, ligéralo una vez con
`with` y escribe `.campo` / `calling .metodo` en el cuerpo. El receptor se
evalúa una vez, los nombres de campo quedan junto a su dueño y una errata es un
error de compilación en vez de un acceso silenciosamente equivocado:

```pengu-fragment
with window:
    set .title is "Logs"
    calling .resize with 800, 600
    calling .refresh
```

**Reglas**

* Usa `with` cuando tres o más líneas toquen el mismo receptor; por debajo de
  eso el receptor explícito se lee mejor.
* El objetivo debe ser un lugar direccionable: liga un temporal primero (`var
  tmp as T is …`) en vez de `with make_widget():` (`E0077`).
* Dentro del cuerpo no hay un segundo receptor: los `with` anidados se apilan y
  gana el más interno.

### 7.10 Construye mapas con literales

Prefiere un literal de mapa a una secuencia de `.put` cuando las entradas se
conocen en el punto de construcción: dice el contenido en un solo sitio y el
compilador emite una inserción por entrada.

```pengu-fragment
var ages as map of string to int is {"ada": 36, "alan": 41}
defer banish ages
```

**Reglas**

* Escribe el tipo en el binding (`var ages as map of string to int is …`); un
  `{"a": 1}` suelto no tiene tipo de clave ni de valor y es `E0076`.
* Usa `.put` para entradas calculadas después, y un literal para la forma
  inicial.
* El literal es dueño del mapa; báñalo como cualquier otro mapa.

### 7.11 Itera con la forma propia del contenedor

`for` conoce todos los contenedores, así que la aritmética de índices es una
señal de alarma: esconde la regla de longitud de cada tipo y la recalcula en el
momento equivocado.

```pengu-fragment
# ❌ índice manual, incorrecto para slices y mapas
var i as int is 0
while i < (calling xs.length):
    calling handle with (xs at i)
    set i is i + 1

# ✅ un solo bucle, el compilador elige el accesor
for x in xs:
    calling handle with x

# ✅ un mapa liga sus dos mitades; no hay índice que simular
for key, value in counts:
    calling emit_pair with key, value
```

Prefiere un bucle etiquetado a una bandera booleana para salir de bucles
anidados (`continue outer`), y una comprensión a un acumulador con `push`.
Iterar un string produce vistas prestadas de un byte: sin reservar por carácter
y sin suponer fronteras de varios bytes.

### 7.12 Desestructura una runa cuando sus campos son lo importante

Una runa es un registro; desempaquétala una vez en lugar de nombrarla sólo para
llegar a sus campos. Los nombres ligan en orden de declaración y la cantidad
debe coincidir (`E0079`).

```pengu-fragment
# ❌ la runa existe sólo para ser desreferenciada
var point as Pair is with left is 7, right is 3
calling print with "{point.left} {point.right}\n"

# ✅ los campos son el dato; la runa es la forma
var (left, right) as Pair is point
calling print with "{left} {right}\n"
```

Una runa necesita `as T` para desestructurarse: el compilador debe conocer el
orden de los campos. Cuando una llamada devuelve varios valores, lígalos de una
vez en lugar de guardar una tupla anónima.

### 7.13 Compón con `fundere`, no imites la herencia

`fundere` sirve para "este valor *tiene* aquel valor, y entrar en él es ruido".
No es una forma de construir una jerarquía: el host no es subtipo del embed y no
hay dispatch.

```pengu-fragment
rune GameObj:
    position as Vec2
    bounds as Rect

rune Enemy fundere GameObj:
    health as int
```

Úsalo cuando se cumplan todas estas:

* el host realmente posee un embed de ese tipo (un `GameObj`, un `Physics`);
* el embed es parte estable del layout del host, no un puntero a uno compartido;
* quieres `enemy.position` porque el embed no tiene identidad propia.

Escribe el campo explícito cuando se cumpla alguna de estas:

* necesitas pasar el embed a C (`sigil of e.gameObj` sigue siendo la forma, pero
  un campo con nombre deja clara la frontera);
* el host tiene varios embeds del mismo tipo — nómbralos (`as left`, `as right`);
* la relación es "puede hacer", no "está hecho de". Eso es un `concept` y un
  `bind` explícito, nunca un `fundere`;
* el embed sería un puntero o una vista. `fundere` guarda el valor inline.

Dos trampas:

* **El shadowing como diseño.** Si un campo del host tapa un campo promovido,
  gana el host en silencio. Es legal y a veces correcto (estrechar un tipo), pero
  `--lint=shadow` existe porque normalmente es un renombrado pendiente.
* **Herencia disfrazada.** `rune Dog fundere Animal` se lee como `Dog es un
  Animal`, y no lo es: `ref to Dog` no se puede pasar donde se espera
  `ref to Animal`, los rituales de `Animal` no se heredan y los conceptos de
  `Animal` tampoco. Si quieres substituibilidad, define un `concept` y haz
  `bind` de los dos tipos.

`fundere` propaga exactamente dos cosas, porque la memoria lo exige: `Drop` y
`Nexus`. Un host con un embed `Drop` es `Drop` (move-only, destructor compuesto)
y un host con un embed `Nexus` puede `banish`. Todo lo demás se escribe en el
host a propósito.

Liberar el embed y después el host es seguro, y hacerlo dos veces también:
`banish` deja a cero el handle que libera, y el destructor compuesto solo libera
lo que aún posee. Lo que **no** es seguro es liberar a través de un segundo
binding que te fabricaste:

```pengu-malo
var g as GameObj is e.gameObj
banish g
banish e            # no libera dos veces, pero `g` era una vista
```

`e.gameObj` es una vista del almacenamiento del host, no un segundo dueño.
Léelo, pásalo, promociona a través de él; no lo banishees y luego esperes que el
host siga poseyendo el string.

## 8. Anti-patrones

Cada fila es un error real visto en este código o en código portado de C. Los
ejemplos desarrollados tras la tabla muestran los cuatro más caros.

| ❌ No hagas | ✅ Haz esto | Por qué |
| --- | --- | --- |
| `"a" + b` | `"a {b}"` | `+` es numérico; la composición de strings es interpolación |
| `set acc is "{acc}{x}"` en un bucle | comprensión + `scrolls.join` | asignación O(n²) |
| `let MAX is 100` en el nivel superior | `const MAX as int is 100` | `let` en el nivel superior es `E0002` |
| `if m.is_present: m.value` | `if v as T is m:` | una comprobación, un binding |
| `var r is 0` + `if`/`else` | `if cond then a else b` | una asignación |
| `x.foo` para llamar | `calling x.foo` | la invocación es siempre explícita |
| `self.hp` | `self->hp` | `self` es una referencia (`E0003`) |
| `rune Dog fundere Animal` para modelar "es-un" | `concept` + `bind`, o un campo con nombre | `fundere` es composición: sin subtipado ni métodos heredados |
| `bool` de éxito + parámetro de salida | `result of T to E` | el fallo lleva una causa |
| `panic` para entrada de usuario | `maybe`/`result` | panic es para bugs |
| `return maybe none` para señalar un error | `result` con un error con nombre | la ausencia no es una causa |
| tipo de error `string` | tipo de error `omen` | exhaustividad y códigos estables |
| ignorar un `result` | `try`, `or:`, o gestionarlo | un error descartado es un bug |
| `var b is a` para un `string`/`list` propio | `calling scrolls.copy with a`, o prestar `a` | la copia comparte el búfer y ambos dueños lo liberan |
| `banish` de un parámetro | documentar los parámetros prestados | el destinatario no es su dueño |
| `banish` de un slice/vista | liberar al dueño | las vistas no poseen almacenamiento |
| `banish` dentro de un bucle sobre una lista de strings | `pengu_banish_string_list` o política por elemento | el contenedor no libera los elementos |
| liberar y luego usar | `banish` una vez, al final del ámbito dueño | uso después de liberar |
| `defer banish x` después de `return` | poner `defer` justo tras la asignación | defer inalcanzable |
| asignar en un bucle sin liberar | asignar una vez, o arena | fuga por iteración |
| `std.memoria.alloc` para un array fijo | `array of T with size N` | pila, sin liberación |
| devolver `ref to T` de un local | devolver el valor | referencia colgante (`E0051`) |
| `transmute` para convertir números | `as`, `to_int`, `to_float` | reinterpretación, no conversión |
| `unsafe` por comodidad | solo con comentario, test y medición | elimina las comprobaciones |
| `--release-unsafe` global | por objetivo, documentado | elimina los checks de límites |
| `antiquus` para lógica normal | `weave` | los cuerpos C no se comprueban |
| `antiquus` sin contrato `##` | documentar pre/postcondiciones | el compilador no puede ayudar |
| `@packed` en un struct corriente | solo formatos de red/disco | cambia el ABI |
| `@export` sin prefijo | `@export("mylib_x")` | colisiones con libc |
| `@noreturn` en algo que retorna | solo funciones que de verdad no retornan | UB en el punto de llamada |
| `cyclus` para callar una referencia adelantada | reordenar declaraciones o usar un puntero | esconde errores de tamaño infinito |
| `seal` para un alias simple | `alias` | `seal` es nominal y añade conversiones |
| `T` genérico sin bound cuando hace falta | añadir el `where` mínimo | los errores aparecen en la definición |
| duplicar una función por tipo | `shard T` | una implementación, un conjunto de tests |
| `concept` para una sola implementación | una función normal | los conceptos son para polimorfismo |
| implementar `Par`/`Ordo` a mano | `derive Par, Ordo` | el derive es el orden canónico |
| `ritual` dentro de `concept` | no soportado; usa `weave` | el checker lo rechaza |
| `@mutates` en posición de valor | llamarlo como sentencia | `E0066` |
| encadenar una mutación y luego leer | separar en dos sentencias | sorpresas de orden de evaluación |
| `while` con índice acumulador | `for i from a to b` | el bucle es dueño del índice |
| `for ch in s` para texto UTF-8 | iteración de `std.lingua` | bytes vs puntos de código |
| regex para parsear JSON/HTML | `std.json`, un parser de verdad | regex no es un parser |
| regex por carácter | precompilar con `std.regulus` | compilación por llamada |
| confiar en `argv`/env | validar y convertir con `parse_*` | la entrada no es confiable |
| confiar en tamaños de red/fichero | comprobar antes de asignar | DoS de asignación |
| `File` abierto sin `defer close` | `defer` del cierre | fuga en el retorno temprano |
| `@deprecated` sin reemplazo | nombrar la alternativa | el aviso debe ser accionable |
| símbolo público sin `##` | documentarlo | `psc doc` muestra `_Undocumented._` |
| test que depende del reloj de pared | inyectar un reloj o usar un rango | test inestable |
| test que toca la red | fixture o un doble | inestable y lento |
| `test` que afirma sobre un mensaje de panic | afirmar sobre el error del `result` | el mensaje no es API |
| `main` de 500 líneas | una función por paso | no testeable |
| módulo llamado `utils` | un sustantivo con una responsabilidad | ninguna responsabilidad |

### 8.1 Construcción de strings

```pengu-fragment
# ❌ E0005 — `+` no concatena strings
let msg is "Hello, " + name

# ✅ interpolación
let msg is "Hello, {name}"

# ✅ muchas piezas: un builder, una asignación
var b as StringBuilder is calling StringBuilder.new
defer banish b
for part in parts:
    calling b.append with part
let joined as string is calling b.finish
```

### 8.2 Propiedad de los parámetros

```pengu-fragment
# ❌ el destinatario no puede saber si quien llama aún lo necesita
weave normalize with path as string into string:
    banish path                 # libera el string de quien llama
    return calling to_lower with path

# ✅ presta; copia si de verdad debes devolver uno nuevo
weave normalize with path as string into string:
    return calling scrolls.lower with path
```

### 8.3 Errores que pierden la causa

```pengu-fragment
# ❌ la ausencia no dice a quien llama qué arreglar
weave load with path as string into maybe Config:
    let text as maybe string is calling archivum.read_text with path
    if text is not present:
        return maybe none
    return calling parse_config with text.value

# ✅ quien llama puede reaccionar, y la causa cruza la frontera
weave load with path as string into result of Config to IoError:
    let text as string is try calling archivum.read_file_result with path
    defer banish text
    let cfg as maybe Config is calling parse_config with text
    if cfg is not present:
        return calling err_of with IoError.Unknown
    return calling ok_of with cfg.value
```

`try` se niega a cruzar dominios de error (`E0045`): si la función devuelve
`result of Config to LoadError`, el `try` de arriba no compila. Mapea el error
explícitamente en vez de ensancharlo a `string`.

### 8.4 Copiar y pegar por tipo

```pengu-fragment
# ❌ una función por tipo de elemento
weave sum_ints with xs as list of int into int: ...
weave sum_floats with xs as list of float into float: ...

# ✅ una función genérica con el bound que necesita
weave sum shard T where T: Num with xs as list of T into T:
    var total as T is donum T
    for x in xs:
        set total is total + x
    return total
```

La misma regla vale para los objetos de transferencia. Antes de `derive Json`,
cada DTO necesitaba un par de recorridos escritos a mano sobre `std.json`, y cada
uno era un sitio donde olvidar un `banish`. Ahora el códec se compila a partir
del propio rune:

```pengu
rune Address derive Json:
    city as string
    zip as int

rune User derive Json:
    id as i64
    name as string
    @json("e-mail") email as string
    @skip password as string
    tags as list of string
    nick as maybe string
    address as Address

weave handle with body as string into result of User to string:
    return calling User.from_json with body

weave send with user as ref to User into string:
    return calling user.to_json
```

Lo que aporta, y lo que no:

- **Compila a C, no a un runtime.** `to_json` se convierte en
  `_pengu_json_encode_User` y `from_json` en `_pengu_json_decode_User`; no hay
  reflexión, ni tabla RTTI, ni dependencia de `std.json`. El resultado se lee
  como el serializador que habrías escrito a mano.
- **El camino de error limpia lo suyo.** Si falla la decodificación, el
  decodificador libera los campos ya reservados con `_pengu_json_free_User` y
  devuelve `err` con `line`/`col`, así que el llamante nunca recibe un valor a
  medio construir. No confíes en `banish` para eso: `Nexus` es
  deliberadamente superficial (ver [LANGUAGE.es.md §9.1](LANGUAGE.es.md#91-rune--structs)).
- **La validación no es trabajo del códec.** `@format("email")`, rangos o reglas
  de negocio van en un `weave validate` en la frontera; el compilador rechaza
  esos atributos dentro de un rune Json (`E0054`) en vez de fingir que los
  aplica.
- **El esquema vive en el DTO, no en el compilador.** `derive Json` no expone
  nada de OpenAPI ni de JSON Schema; una herramienta satélite (`psc doc`,
  `portus`) lee el rune y escribe la especificación que necesite.

Referencia completa: [LANGUAGE.es.md §9.7.1](LANGUAGE.es.md#971-derive-json).

## Parte III — Código seguro

## 9. Tipos, representación y aritmética

### 9.1 La tabla de tipos

| PenguScript | C | Tamaño | Notas |
| --- | --- | --- | --- |
| `int` | `int32_t` | 4 | entero por defecto; el overflow envuelve |
| `i8`/`i16`/`i32`/`i64` | `intN_t` | 1/2/4/8 | con signo |
| `u8`/`u16`/`u32`/`u64` | `uintN_t` | 1/2/4/8 | sin signo |
| `isize`/`usize` | `intptr_t`/`uintptr_t` | puntero | índices, tamaños |
| `float` / `f32` | `float` | 4 | float por defecto |
| `f64` / `double` | `double` | 8 | úsalo para dinero, tiempo, precisión |
| `bool` | `bool` | 1 | sin conversión implícita a int |
| `char` | `char` | 1 | byte, no un punto de código |
| `byte` | `uint8_t` | 1 | byte crudo |
| `string` | `PenguString` | 16 | puntero + longitud + flag de propiedad |
| `list of T` | `PenguList` | 24 | heap, redimensionable |
| `map of K to V` | `PenguMap` | 32 | heap, hash |
| `array of T with size N` | `T[N]` | N×sizeof(T) | pila, fijo |
| `slice of T` | `PenguSlice` | 16 | vista prestada |
| `ref to T` | `T *` | 8 | puntero prestado |
| `maybe T` | `PenguMaybe` | 16 | flag + payload boxeado |
| `result of T to E` | `PenguResult` | 24 | flag + payload/error boxeado |

### 9.2 Semántica de valor y de referencia

`rune`, `echo`, `omen`, `seal` y los tipos numéricos son valores: asignar uno
copia los bytes. `list`, `map`, `string`, `maybe`, `result` son handles: se copia
el struct, no el almacenamiento al que apunta.

Esa última frase es el origen de la mayoría de los bugs de propiedad:

```pengu-fragment
var a as string is "hello"
var b as string is a          # copia el handle, NO el texto
banish a                      # libera el texto; b queda colgando
calling print with b          # uso después de liberar
```

Cuando necesites un segundo dueño, pide una copia explícita:

```pengu-fragment
var a as string is "hello"
defer banish a
var b as string is calling scrolls.copy with a
defer banish b
```

La misma regla vale para `list`, `map`, `maybe` y `result`. Para mover en vez de
copiar, pasa el valor a una función que toma propiedad y deja de usarlo.

### 9.3 Aritmética y overflow

La aritmética entera envuelve al ancho del tipo. No hay comprobación de overflow,
ni en debug ni en release:

```pengu
weave main into int:
    var max as int is 2147483647
    var next as int is max + 1
    calling print with "{next}"      # -2147483648
    return 0
```

Que envuelva está bien para hashing y checksums; es un bug para contadores,
dinero y tamaños. Cuando el overflow sea posible:

* acumula en `i64` y comprueba el rango antes de estrechar con `to`;
* o comprueba el operando antes de sumar (`if a > INT_MAX - b: …`) con las
  constantes de `std.integrum`.

```pengu-fragment
weave add_checked with a as int, b as int into result of int to ArithError:
    if b > 0 and a > 2147483647 - b:
        return calling err_of with ArithError.Overflow
    return calling ok_of with a + b
```

La división y el módulo por cero provocan una trampa en C (SIGFPE). Protege el
divisor, o usa los helpers de `std.integrum` que devuelven un `result`.

La aritmética de coma flotante sigue IEEE-754: `0.0 / 0.0` es NaN y NaN no es
igual a sí mismo. Nunca compares floats con `==`; compara con tolerancia
(`std.fractio` trae los helpers) o compara enteros.

### 9.4 Comprobación de límites

Indexar un `list`, `slice`, `array` o `string` se comprueba por defecto:

```
[PENGU] Index out of bounds: 5 (length 3)
[PENGU CRASH] bounds check failed
```

La comprobación se elimina dentro de bloques `unsafe` y con `--release-unsafe`.
Esa es toda la historia de seguridad del indexado: déjala activada y, si tienes
que desactivarla, demuestra el límite con un test.

`array of T with size N` se comprueba igual; su tamaño debe ser una constante de
tiempo de compilación (`E0041`).

### 9.5 Elegir el tipo correcto

* Tamaños e índices: `usize`/`isize`, no `int`.
* Dinero: céntimos enteros en `i64`, nunca `float`.
* Tiempo: `std.chrono.Instant`/`Duration` (nanosegundos enteros) para intervalos,
  `std.chronicle` para reloj de pared.
* Texto: `string` para UTF-8, `slice of byte`/`bytes of` para datos crudos.
* Ausencia: `maybe T`. Fallo: `result of T to E`. Nunca `T` más un `bool`.

**Reglas**

* `float` es de 32 bits; anota `f64` para todo lo que necesite precisión.
* Nunca confíes en el envolvimiento del overflow en lógica de negocio.
* Nunca compares floats por igualdad.
* Mantén los checks de límites; `unsafe` necesita una prueba, no una esperanza.
* Copia los handles propios explícitamente (`scrolls.copy`, clonar `list`) antes
  de que otro los libere.

## 10. Conversiones

### 10.1 Las conversiones numéricas truncan

`to` convierte y estrecha en silencio:

```pengu
weave main into int:
    var big as int is 300
    var small as u8 is big to u8
    calling print with "{small}"     # 44
    return 0
```

Eso es semántica de C, no una comprobación. Si el valor debe caber, dilo:

```pengu-fragment
weave to_u8_checked with n as int into result of u8 to RangeError:
    if n < 0 or n > 255:
        return calling err_of with RangeError.OutOfRange
    return calling ok_of with n to u8
```

### 10.2 Texto a números

`std.spark.parse_int` y `parse_float` devuelven `maybe`; `std.scrolls` y
`std.integrum` exponen los mismos helpers. Nunca uses `atoi` de C desde un
binding: no puede informar de un fallo.

```pengu-fragment
let n as maybe int is calling spark.parse_int with text
if n is not present:
    return calling err_of with ConfigError.NotANumber
let port as int is n.value
```

La salida formateada pasa por interpolación o por `str_int`/`str_float`; en el
lenguaje no hay cadenas de formato tipo `printf`, así que las vulnerabilidades de
formato no existen por construcción.

### 10.3 Caracteres y bytes

`ord c` da el valor de byte de un `char`; `chr n` construye un `char` a partir de
un entero en 0–255 (`E0057` fuera de rango). Un `char` es un byte, no un punto de
código Unicode: para UTF-8 usa `std.lingua` (`codepoint_at`, `utf8_len`,
`decode`), nunca `for ch in s` más aritmética de bytes.

### 10.4 Strings, slices y bytes

* `bytes of s` — vista `ref to frozen byte`, sin copia, válida mientras viva `s`.
* `slice of T` — ventana prestada sobre una lista/array/string.
* `s at i` sobre un `string` devuelve un `string` de un carácter; `s at i to j`
  devuelve un substring (propio).
* `s.len` son bytes, no caracteres; usa `lingua.utf8_len` para puntos de código.

### 10.5 Newtypes

`seal UserId as int` es nominal: `int to UserId` y `id to int` son las únicas
conversiones, y son explícitas. Usa un `seal` para valores que no deben
mezclarse (ids, unidades, hashes). `alias` es transparente y no añade seguridad.

### 10.6 `transmute`

`transmute x to T` reinterpreta los bits y emite `W0001`. Usos legítimos: leer un
formato de red en un struct, inspeccionar el patrón de bits de un float en un
test. Cualquier otra cosa es un bug esperando a la próxima versión del
compilador. Nunca hagas `transmute` entre tipos de puntero para esquivar el
sistema de tipos; usa `opaque` y `declare`.

**Reglas**

* Todo estrechamiento o está demostrado (`if` de rango) o trunca a propósito
  (hashing, checksums) con un comentario.
* Parsea texto con `parse_*`, nunca con funciones de conversión de C.
* `char` es un byte; UTF-8 pasa por `std.lingua`.
* `seal` para identidad, `alias` para legibilidad, nada para magia.
* `transmute` exige un comentario y un test que fije el layout.

## 11. Errores

### 11.1 `maybe` o `result`

| Pregunta | Tipo |
| --- | --- |
| ¿Está? (lookup, campo opcional, argv) | `maybe T` |
| ¿Funcionó y, si no, por qué? (I/O, parse, red, validación) | `result of T to E` |
| Error del programador, invariante roto | `panic` |
| Control de flujo normal | ninguno: un `if` |

Si quien llama puede hacer algo distinto según *por qué* falló, es un `result`.
Si la única reacción es "usar el valor por defecto", es un `maybe`.

### 11.2 Diseñar el tipo de error

Un tipo de error es un `omen` con variantes estables y significativas:

```pengu-fragment
omen ConfigError:
    Missing
    PermissionDenied
    NotANumber
    OutOfRange
```

Reglas:

* Un tipo de error por frontera de módulo, no por función.
* Las variantes son causas, no mensajes: `Missing`, no `FileNotFoundAtPath`.
* Sin payload salvo que quien llama necesite el dato (p. ej. `Invalid { index }`).
* Sin errores `string`: no son exhaustivos y no se pueden emparejar.
* Mantén las variantes estables; añadir una está bien, renombrar una es un cambio
  incompatible (capítulo 29).

### 11.3 Propagación

| Forma | Funciona con | Comportamiento |
| --- | --- | --- |
| `x or else fallback` | `maybe`, `result` | valor por defecto, perezoso |
| `x or return expr` | `maybe`, `result` | retorna `expr` del weave que lo contiene |
| `try x` | `maybe`, `result` | propaga el mismo fallo |
| `x or:` | solo `maybe` | bloque con `error` ligado a la ausencia |

```pengu-fragment
weave first_line with path as string into result of string to IoError:
    let text as string is try calling archivum.read_file_result with path
    defer banish text
    let line as maybe string is calling first_line_of with text
    return calling ok_of with (line or else "")
```

`try` no convierte dominios de error: una función que devuelve
`result of T to ConfigError` no puede hacer `try` de un `result of T to IoError`
(`E0045`). Mapea explícitamente:

```pengu-fragment
weave load_config with path as string into result of Config to ConfigError:
    let read as result of string to IoError is calling archivum.read_file_result with path
    if not read.is_ok:
        return calling err_of with ConfigError.Missing
    let text as string is read.value
    defer banish text
    return calling parse_config with text
```

### 11.4 `error` y `or:`

`or:` gestiona la ausencia de un `maybe`; dentro del bloque, `error` es el
payload (un `string` para `maybe`), y solo ahí (`E0015` en otro sitio).

```pengu-fragment
let port as maybe int is calling spark.parse_int with raw
let p as int is port or:
    calling spark.eprintln with "bad port: {error}"
    return 2
```

No uses `or:` con un `result`: desempaqueta con `if r.is_ok` o propaga con
`try`.

### 11.5 Política de `panic`

`panic` es para estados que no pueden ocurrir si el código es correcto: un
invariante de una estructura de datos, una rama `judge` inalcanzable sobre un
omen cerrado. Nunca es una respuesta a entrada de usuario, a un fichero que falta
o a una asignación fallida que podrías informar.

Un panic imprime el mensaje y una traza y aborta. Los tests pueden afirmar que
ocurre un panic solo mediante los death tests de `std.trial`, no comparando el
texto del mensaje.

**Reglas**

* Ausencia vs causa: elige el tipo antes de escribir la función.
* Un `omen` de error por frontera de módulo; las variantes son causas.
* `try` solo entre tipos de error compatibles; si no, mapea.
* Sin errores `string`, sin códigos de error escondidos en un bool.
* `panic` solo para invariantes rotos, con un mensaje que nombre el invariante.

## 12. `defer`, `errdefer` y `banish`

### 12.1 Las tres herramientas de limpieza

| Herramienta | Se ejecuta | Úsala para |
| --- | --- | --- |
| `defer stmt` | en cada salida del ámbito, LIFO | liberar valores propios |
| `errdefer stmt` | solo cuando el ámbito retorna un error | deshacer trabajo parcial |
| `banish x` | inmediatamente | liberar en un punto conocido |

Los temporales de cadena son la excepción que confirma la regla: la
interpolación (`"{x}"`), la concatenación (`+`) y una vista (`s at a to b`) te
entregan un `string` con dueño, y el compilador lo libera al final de la
sentencia cuando lo usas como argumento. `set s += v` añade en el sitio, así
que el manejador que tienes sigue siendo válido. Para esos casos nunca escribes
`banish`.

### 12.2 `defer`

`defer` se ejecuta cuando termina el bloque que lo contiene: normalmente, por
`return`, por `break`/`continue` o por un error propagado con `try`/`or return`.
Corre en orden inverso al registro.

```pengu
import std.archivum

weave main into int:
    var text as string is "hello"
    defer banish text
    calling print with text
    return 0
```

Dentro de un bucle, cada iteración es su propio ámbito: un `defer` en el cuerpo
corre al final de cada iteración, no al final del bucle.

### 12.3 `errdefer`

`errdefer` sirve para deshacer un efecto secundario cuando la función está a
punto de retornar un error: cerrar una transacción, borrar un fichero parcial,
liberar un recurso que se había cedido. Se ejecutan tanto `errdefer` como
`defer`, y `errdefer` primero cuando se registró el último.

```pengu-fragment
weave write_atomic with path as string, data as string into result of void to IoError:
    let tmp as string is "{path}.tmp"
    defer banish tmp
    let w as result of int to IoError is calling archivum.write_file_result with tmp, data
    errdefer calling archivum.delete_file with tmp
    if not w.is_ok:
        return calling err_of with w.error
    return calling ok_of with 0
```

### 12.4 Colocación

* `defer banish x` va en la línea siguiente a la asignación, antes de cualquier
  cosa que pueda fallar.
* Nunca pongas `defer` dentro de un `if` salvo que el valor se asigne ahí.
* Nunca hagas `defer banish` de un parámetro: el destinatario no es su dueño.
* Nunca hagas `defer banish` de una vista (`slice`, `bytes of`, campo `ref to`).
* Si una función transfiere propiedad a quien llama, no debe hacer
  `defer banish` del valor retornado.

### 12.5 Caminos de error

La fuga más común es un `return` en un camino de error antes de que el `defer`
esté registrado:

```pengu-fragment
# ❌ filtra `buffer` cuando `parse` falla
var buffer as string is calling read_all with path
let value as maybe V is calling parse with buffer
if value is not present:
    return calling err_of with LoadError.Invalid
banish buffer

# ✅ defer primero
var buffer as string is calling read_all with path
defer banish buffer
let value as maybe V is calling parse with buffer
if value is not present:
    return calling err_of with LoadError.Invalid
```

**Reglas**

* Un dueño, un `banish`/`defer banish`, en todos los caminos.
* `defer` inmediatamente después de la asignación, nunca tras el primer punto de
  fallo.
* `errdefer` solo para efectos secundarios que deban deshacerse.
* Nunca liberes parámetros, vistas ni valores que retornas.
* Testea el camino de error: ahí están las fugas.

## 13. Concurrencia

### 13.1 Qué existe

`std.filum` ofrece las primitivas de sincronización — `Mutex`, `WaitGroup`,
`Once`, `Cond`, `AtomicInt` y canales tipados (`ChanInt`, `ChanString`,
`ChanFloat`, `ChanBool`) — y, desde 0.30.0, hilos de primera clase:
`filum.start` devuelve un `Thread` que se puede `join`, `detach` o liberar.
`std.coro` añade corrutinas: tareas cooperativas que viven en el hilo que las
creó y avanzan solo cuando su dueño las reanuda.

Un hilo es paralelismo del sistema operativo; una corrutina es control
cooperativo dentro de un hilo. El capítulo cubre ambos: las reglas de compartir
datos aplican a los hilos, y la afinidad de las corrutinas elimina las carreras
sin necesidad de locks.

### 13.2 Mutex

```pengu-fragment
rune Counter:
    lock as Mutex
    value as int

enchanting Counter:
    weave increment into void:
        calling lock with sigil of self->lock
        set self->value is self->value + 1
        calling unlock with sigil of self->lock
```

Reglas:

* Un mutex protege un invariante; nómbralo por lo que protege.
* Retenlo el menor tiempo posible: ni I/O, ni asignación, ni callbacks bajo el
  lock.
* `try_lock` sirve para evitar deadlocks, nunca para "probablemente libre".
* Un `defer unlock` solo es seguro si la sección crítica no puede retornar antes;
  un `return` dentro de ella dejaría el mutex bloqueado.

### 13.3 Atómicos

`AtomicInt` es un entero de 32 bits con consistencia secuencial:
`add_atomic`, `sub_atomic`, `swap`, `compare_swap`, `inc`, `dec`,
`inc_and_get`, `dec_and_get`. Úsalo para contadores y flags, no para invariantes
de varios campos (para eso, un mutex).

```pengu-fragment
rune Stats:
    requests as AtomicInt
    errors as AtomicInt
```

### 13.4 Canales

```pengu-fragment
let jobs as ChanInt is calling ChanInt.with_capacity with 64
defer banish jobs

# productor
let ok as bool is calling jobs.send with 42

# consumidor
let v as maybe int is calling jobs.recv
if v is not present:
    return 0
calling handle with v.value
```

* `send` devuelve `false` cuando el canal está cerrado; ignorarlo pierde trabajo.
* `recv` devuelve `maybe none` cuando el canal está cerrado y vacío.
* `close` avisa de que no habrá más envíos; el receptor drena y luego ve `none`.
* Libera un canal exactamente una vez, cuando todos sus usuarios hayan acabado.

### 13.5 Reglas para compartir

| Valor | Entre hilos |
| --- | --- |
| números, `bool`, `char`, `seal` de ellos | copiar libremente |
| `rune` de valores | copiar; lo más seguro es una copia por hilo |
| `string`, `list`, `map` | **nunca** compartir propiedad; muévelo o cópialo |
| `ref to T` | solo con un lock que cubra cada acceso |
| `slice of T` | solo mientras el dueño viva y no se mute |
| `maybe`/`result` | valores; el payload sigue la regla de su tipo |

El compilador comprueba la frontera de `filum.start`: un valor con dueño debe
ser un binding local y se mueve al worker; un `ref to T` solo se acepta si `T`
está marcado `@shared`. No demuestra que los métodos de `T` bloqueen, ni rastrea
alias hechas antes del movimiento. Si dos hilos pueden ver el mismo
`PenguString`, el programa sigue mal salvo que ambos lo traten como inmutable y
el dueño viva más que ellos.

### 13.6 Testear concurrencia

Ejecuta el C generado bajo ThreadSanitizer cuando un binding lo permita
(`cflags = ["-fsanitize=thread"]` en un perfil de debug), y escribe tests que
ejerciten los entrelazados que te importan con canales o un `WaitGroup`. Un test
de concurrencia que pasa una vez no demuestra nada: ejecútalo en bucle en CI.

**Reglas**

* Ningún dato compartido sin un lock, un atómico o un canal.
* Un mutex protege un invariante, y nada más corre dentro.
* Nunca ignores el resultado de `send`.
* Libera canales y mutex una vez, con un comentario que diga quién es el dueño.
* Los tests de concurrencia corren en bucle; un único verde no es evidencia.
### 13.7 Corrutinas

Una corrutina no es un hilo ni una promesa: es una función que se puede
suspender y reanudar explícitamente. `std.coro.start` la crea suspendida,
`resume` la ejecuta hasta el siguiente `yield` o hasta que retorne, y `status`
dice en qué estado está. `std.coro` no trae planificador ni sintaxis
`async`/`await`, y no hay migración de hilo: si el dueño no la reanuda, no
avanza. La política de planificación es explícita y vive en `std.reactor`
(§13.8).

```pengu
import std.coro

weave worker with out as ref to int into void:
    set essence of out is 1
    calling coro.yield
    set essence of out is 2

weave main into int:
    var n as int is 0
    var co as coro.Coroutine is calling coro.start with worker, (sigil of n)
    calling co.resume
    calling co.resume
    calling co.free
    return n
```

La misma afinidad que hace seguras las corrutinas impone sus reglas:

* Un `ref to T` puede pasar a `coro.start` sin `@shared`; el worker no cambia
  de hilo. Un `string`/`list`/`map` con dueño se mueve, igual que en un hilo, y
  el binding original queda inutilizable (`E0008`).
* `free` solo se llama sobre una corrutina terminada. Una suspendida se
  descarta con `abandon`, que no ejecuta sus `defer`: si el worker tenía recursos
  con dueño, el programa los filtra. Es una decisión explícita, no un olvido.
* `yield` fuera de una corrutina, `resume` sobre una terminada o `free` sobre
  una suspendida son panics. Son bugs de programa; no se convierten en `result`.
* La pila es de 64 KiB y se recicla en una arena. Una recursión más profunda es
  un desbordamiento de pila: reduce la recursión o mueve el trabajo a un hilo.

Las corrutinas son la base para generadores e iteradores perezosos, pero
PenguScript no añade sintaxis de generador: el patrón se escribe con `resume` y
`yield`, y los valores viajan por `ref to` o por el estado del dueño. Tampoco
hay `async`/`await` como palabras clave: las variantes `*_async` de la stdlib
son funciones normales que suspenden la corrutina actual y exigen estar dentro
de una tarea del reactor. No hay transformación de color de función, ni
closures con captura, ni una máquina de estados generada a escondidas.

### 13.8 El reactor: planificar es explícito

`std.reactor` es la política de planificación, en espacio de usuario. El
programa crea el loop, registra tareas y decide cuándo ejecutarlas:

```pengu
import std.reactor

weave tick with loop as ref to reactor.EventLoop, n as ref to int into void:
    calling loop.sleep_ms with 10

weave main into int:
    var loop as reactor.EventLoop is calling reactor.EventLoop.new
    calling loop.spawn with tick, 0
    calling loop.run
    calling loop.close
    return 0
```

`spawn` no ejecuta el worker en línea: lo deja listo para la siguiente pasada.
`run` es el único que hace `epoll_wait`/`poll` y reanuda tareas. `park_read` y
`park_write` estacionan la corrutina actual hasta que el descriptor esté listo;
`sleep_ms` la estaciona con un temporizador; `offload` manda trabajo bloqueante
al pool del loop y `await_token` espera su finalización. `close` se llama fuera
de una corrutina, abandona las suspendidas y no cierra los descriptores del
usuario.

**Cuándo usarlo.** E/S de red, timers, servidores con muchas conexiones y
trabajo bloqueante que no quieres que pare el resto (ficheros, libcurl). Es la
opción correcta cuando el coste dominante es esperar, no calcular.

**Cuándo no usarlo.** CPU pura o paralelismo real: usa `std.filum` y su `Pool`.
Tampoco lo uses para esconder una librería bloqueante que no controlas: si no
hay una variante `*_async`, el `offload` es la frontera honesta y el coste es un
hilo del pool por operación en vuelo (varios offloads concurrentes necesitan
varios workers). En Windows el reactor usa `WSAEventSelect`; `std.net` sigue
siendo POSIX, así que el servidor TCP con `std.net` no es portable a Windows.

**Reglas que el compilador no puede salvarte:**

* Un loop pertenece al hilo que lo creó. `new`, `spawn`, `run`, `stop` y
  `close` se llaman desde ese hilo; un worker nunca toca el loop directamente.
* Un `*_async` solo se llama dentro de una tarea del loop. Fuera de ella es un
  panic, no un bloqueo silencioso.
* No llames `coro.yield` a mano dentro de una tarea: usa `park_*`, `sleep_ms` o
  `await_token` para que el loop sepa por qué está suspendida. Un `yield` suelto
  es un panic en la siguiente pasada de `run`.
* Una tarea puede tener varios `offload` en vuelo; cada uno tiene su token y
  `await_token` consume exactamente el que le pides. El `job_free` libera la
  caja al consumir la completion; si la tarea termina con jobs pendientes, el
  loop hace panic.
* No cierres un descriptor que el loop todavía tiene registrado; cierra la
  tarea o el socket después de que `run` la haya reanudado.
* `close` no cierra tus sockets ni tus ficheros: esa responsabilidad sigue
  siendo tuya.
* `std.filum` no gana canales que suspendan corrutinas. Sus `Mutex`, `Cond`,
  `Chan*` y `Pool` son primitivas de hilo; el estacionamiento de corrutinas vive
  en el reactor. Si necesitas esperar un `Thread` desde una tarea, usa
  `Thread.is_finished` + `reactor.await_thread`.

**Anti-patrones.** Crear un loop por petición; hacer `join` de un hilo dentro de
un worker; usar `Thread.sleep` para esperar E/S; lanzar dos `offload` y esperar
solo uno; cerrar el loop desde dentro de una tarea; o envolver una operación
bloqueante en `spawn` y llamarla "async" sin pasar por el reactor.


## 14. Interoperabilidad con C, con seguridad

### 14.1 El archivo de frontera

Un binding vive en `<lib>.d.pengu` y contiene solo declaraciones:

```pengu-fragment
include "mylib.h"
link "mylib"
insignia mylib_

declare mylib_open with path as ref to char into ref to opaque
declare mylib_read with h as ref to opaque, buf as ref to byte, n as usize into isize
declare mylib_close with h as ref to opaque into int
```

Reglas:

* Tipos C exactos: `usize` para `size_t`, `isize` para `ssize_t`, `i64` para
  `int64_t`, `ref to frozen char` para `const char *`, `ref to opaque` para un
  handle.
* Sin cuerpos en `.d.pengu`; ni `weave` ni `antiquus` ahí.
* `insignia` prefija cada declaración para que los nombres de C queden agrupados
  y no colisionen con libc.
* `include` para las cabeceras que necesites; `link` para la librería; `ldflag`
  solo para lo que un nombre de librería no puede expresar.

### 14.2 Propiedad a través de la frontera

Para cada función que devuelve un puntero, responde tres preguntas en un
comentario `##`: quién es dueño del resultado, cómo se libera y cuál es el tiempo
de vida de los argumentos prestados.

| C devuelve | PenguScript |
| --- | --- |
| `char *` propio de quien llama | `string` si lo envuelves; `banish` libera con el asignador de C correspondiente |
| `const char *` prestado | `frozen ref to char`; nunca lo liberes |
| handle `void *` | `opaque`; liberar con la función de cierre de la propia librería |
| struct por valor | un `rune` que refleje el layout exactamente |
| `NULL` en fallo | `maybe`, tras comprobarlo en el wrapper |

Nunca liberes memoria asignada por una librería de C con un asignador distinto,
y nunca dejes que una librería de C libere memoria asignada por el runtime.
Envuelve ambas direcciones en un helper que use la función de liberación
correspondiente.

### 14.3 Envolver

El `.d.pengu` es la declaración; el módulo `pengu` con nombre latino es la API
segura:

```pengu-fragment
import std.ffi

rune Handle:
    raw as ref to opaque

weave open with path as string into result of Handle to IoError:
    let c_path as ref to frozen char is calling ffi.cstr_from_string with path
    let h as ref to opaque is calling mylib_open with c_path
    if h == null:
        return calling err_of with IoError.NotFound
    return calling ok_of with (with raw is h)
```

Un **literal** se convierte solo donde se espera `ref to char`; una variable
`string` no (el compilador de C ve `PenguString`), así que el wrapper debe pasar
por `ffi.cstr_from_string` (o por una conversión propia del módulo).

El wrapper: valida argumentos, convierte `string` a cadenas C terminadas en NUL
solo cuando el lado C lo exige, mapea los códigos de error de C al `omen` de
error del módulo y es dueño de toda asignación que hace.

### 14.4 `antiquus`

`antiquus` incrusta un cuerpo C literal. Úsalo solo cuando la operación no pueda
expresarse en el lenguaje (intrínsecos, ensamblador en línea, una macro que no es
una función). Todo `antiquus` necesita: un contrato `##`, un test y un comentario
que explique por qué. El compilador no comprueba el cuerpo.

### 14.5 `psc bind`

`psc bind header.h` genera el `.d.pengu` desde una cabecera C con el helper
`pengu-bind` incluido (basado en clang):

```console
$ psc bind include/mylib.h --prefix mylib_ --links mylib -o src/mylib.d.pengu
```

Después revisa el archivo generado: el generador no puede conocer la propiedad,
así que añade los comentarios `##` y el módulo wrapper a mano. Regenerar
sobrescribe tus comentarios: mantenlos en el wrapper, no en el `.d.pengu`.

### 14.6 ABI

El C generado usa un ABI de runtime documentado (capítulo 34). Dos reglas lo
mantienen estable: nunca expongas un `rune` por valor a través de una frontera C
salvo que el lado C replique el layout, y nunca hagas `@export` de un símbolo sin
prefijo de proyecto.

**Reglas**

* `.d.pengu` contiene solo declaraciones; la API segura vive en un wrapper.
* Toda pregunta de propiedad se responde en un comentario `##`.
* Nunca mezcles asignadores.
* `antiquus` es el último recurso, documentado y testeado.
* Vuelve a ejecutar `psc bind` tras cambiar una cabecera y revisa el diff.

## 15. Entrada no confiable

### 15.1 Dónde acaba la confianza

Todo esto es no confiable hasta validarlo: `argv` y el entorno, ficheros, stdin,
respuestas de red, payloads JSON/TOML/YAML, cabeceras, query strings, búferes de
FFI cuya longitud vino de fuera.

La función de frontera es donde se valida, una vez, y el resto del programa
trabaja con tipos ya validados.

### 15.2 Validar y luego convertir

```pengu-fragment
weave parse_port with raw as string into result of int to ConfigError:
    let n as maybe int is calling spark.parse_int with raw
    if n is not present:
        return calling err_of with ConfigError.NotANumber
    let port as int is n.value
    if port < 1 or port > 65535:
        return calling err_of with ConfigError.OutOfRange
    return calling ok_of with port
```

* Parsea con `parse_*`, nunca con `atoi`/`scanf` de un binding.
* Comprueba rangos antes de estrechar.
* Acota longitudes antes de asignar: un campo de longitud que viene de la red es
  una petición, no un hecho.
* Rechaza, no sanes, cuando el formato es estricto.

### 15.3 Rutas

`std.compass` normaliza rutas (`cp_normalize`, `cp_absolute`, `cp_components`).
Cuando una ruta viene de fuera:

* rechaza rutas absolutas y componentes `..` salvo que el usuario tenga permiso
  para elegirlas;
* resuélvela contra una raíz fija y luego verifica que el resultado sigue
  empezando por esa raíz;
* nunca pases un string del usuario a un shell.

### 15.4 URLs, JSON y regex

* Construye URLs con `std.web.url` (`parse`, `query_set`, `encode_component`);
  nunca concatenes una query string.
* Parsea JSON con `std.json`; valida la forma con los helpers de esquema y luego
  lee campos con los accesores `as_*`, no con `if kind ==`.
* Regex (`std.regulus`) es para patrones de texto, no para parsear JSON, HTML o
  ficheros de configuración. Compila una vez y reutiliza; nunca construyas un
  patrón desde entrada de usuario sin escapar (`regulus.escape`).

### 15.5 Límites de descompresión y asignación

La entrada comprimida puede expandirse sin límite. `std.compressus` expone el
tamaño descomprimido; compáralo con un límite antes de asignar. Lo mismo vale
para formatos de imagen o archivo en bindings.

### 15.6 Secretos

`std.secrets` (libsodium) ofrece `random_bytes`, `sha256_raw`, `compare` y
`wipe`. Reglas: nunca registres un secreto, nunca lo incluyas en un mensaje de
error, limpia los búferes que ya no necesites y compara con `compare` (tiempo
constante), no con `==`.

**Reglas**

* Una frontera validada por fuente de entrada; el núcleo nunca ve texto crudo.
* Parsea, comprueba rango y longitud, y solo entonces asigna.
* Las rutas se resuelven y se confinan a una raíz.
* Las URLs se construyen, no se concatenan; los patrones regex se escapan.
* Los secretos nunca llegan a logs, errores ni mensajes de `panic`.

## 16. Checklist de seguridad

Pasa esta lista en cada cambio que toque entrada, FFI, memoria o caminos de error.

### 16.1 Memoria

- [ ] Toda asignación con propiedad tiene un dueño y un `banish`/`defer banish`.
- [ ] Ningún `banish` de parámetros, vistas, valores retornados o literales.
- [ ] Ninguna copia de un handle `string`/`list`/`map` propio sin copia explícita.
- [ ] Los caminos de error liberan todo lo que libera el camino de éxito.
- [ ] Ningún `defer` después de un `return` que pueda ejecutarse antes.

### 16.2 Entrada

- [ ] Todo valor externo se parsea en la frontera.
- [ ] Longitudes y cuentas se comprueban antes de asignar.
- [ ] Las rutas se normalizan y se confinan.
- [ ] URLs, JSON y regex se construyen con los helpers de std.
- [ ] Los errores no repiten secretos ni la entrada completa.

### 16.3 FFI

- [ ] `.d.pengu` no tiene cuerpos y usa tipos exactos.
- [ ] La propiedad de cada puntero retornado está documentada.
- [ ] Los asignadores coinciden en ambos lados.
- [ ] `antiquus` tiene contrato, test y motivo.
- [ ] Los símbolos `@export` llevan prefijo de proyecto.

### 16.4 Vías de escape

| Vía | Permitida cuando | Obligatorio |
| --- | --- | --- |
| bloque `unsafe` | un límite está demostrado por construcción | comentario + test |
| `--release-unsafe` | camino caliente medido, checks cubiertos por tests | comentario + benchmark |
| `transmute` | layout de red o inspección de bits | comentario + test |
| `antiquus` | no expresable en el lenguaje | contrato + test |
| `@packed`/`@align` | ABI de un formato externo | declaración C espejo |
| `@export` | punto de entrada para C o un plugin | símbolo con prefijo |

**Reglas**

* El checklist forma parte de la descripción del PR, no de un ejercicio de
  memoria.
* Una vía de escape sin test es un bug.
* La revisión de seguridad empieza por las funciones de frontera.

## Parte IV — Memoria manual

## 17. El modelo de memoria

### 17.1 Qué garantiza el lenguaje

PenguScript no tiene recolector de basura ni borrow checker. Tiene tres capas de
gestión de memoria, cada una opt-in y visible en el tipo:

* **Capa 1** — `derive Drop`: la runa se destruye sola al salir del scope y no se
  copia: se mueve (§17.7).
* **Capa 2** — `std.consortium`: `Rc`/`Arc`/`Weak` cuando varios dueños deben
  sobrevivirse unos a otros (§17.8).
* **Capa 3** — contenedores copy-on-write: copiar es O(1) y la primera mutación
  clona el búfer (§17.9).

Fuera de esas tres capas el modelo sigue siendo manual. El compilador garantiza
que todo valor está bien tipado, que `banish` (E0008) solo acepta algo que de
verdad puede liberar, y que un valor `Drop` no se usa después de moverse (E0080)
ni se copia por accidente (E0081).

Lo demás es una convención que sostienen la revisión y los tests:

* quién es dueño de un valor,
* cuándo se libera,
* qué hace una función con sus argumentos.

El resto de esta parte convierte esas convenciones en reglas lo bastante precisas
para comprobarlas en revisión.

### 17.2 La tabla de propiedad

| Tipo | Dueño | Liberación | Semántica de copia |
| --- | --- | --- | --- |
| `string` | quien tenga el `PenguString` con `is_owned == 1` | `banish s` | copia el handle, **no** el texto |
| `list of T` | el valor lista | `banish xs` | copia el handle; los elementos se comparten |
| `map of K to V` | el valor mapa | `banish m` | copia el handle |
| `maybe T` | la caja, si está presente | `banish m` | copia la caja |
| `result of T to E` | la caja, si está presente | `banish r` | copia la caja |
| `ref to T` de `memoria.alloc` | quien llama | `banish p` | copia el puntero |
| `ref to T` prestado | el dueño original | **nunca** | copia el puntero |
| `slice of T` | el contenedor original | **nunca** | copia la vista |
| `bytes of s` | el string | **nunca** | copia la vista |
| `rune` sin `Nexus` | sus campos son independientes | por campo | copia de bytes |
| `rune derive Nexus` | el valor | `banish v` → `_pengu_cleanup_T` | copia de bytes (peligrosa) |
| número, `bool`, `char`, `seal` | nadie | — | copia de bytes |
| literal `"..."` | el binario | **nunca** | vista |

Lee la última columna dos veces: **cada copia de un handle propio crea un segundo
dueño del mismo búfer**. Ahí está la raíz del doble free y del uso después de
liberar.

### 17.3 Runes con `Nexus`

`derive Nexus` genera `_pengu_cleanup_T`, que libera cada campo propio
recursivamente:

```pengu
rune User derive Nexus:
    name as string
    tags as list of int

weave main into int:
    var u as User is with name is "ab", tags is [1, 2]
    banish u
    return 0
```

emite

```c
static inline void _pengu_cleanup_User(User* p) {
    pengu_banish_string(&(p->name));
    pengu_banish_list(&(p->tags));
}
```

Sin `Nexus`, `banish u` es `E0008`; los campos siguen siendo tuyos para
liberarlos uno a uno. Con `Nexus`, **el valor es dueño de sus campos** — y una
copia de bytes de ese valor es un segundo dueño, exactamente igual que un
`string` copiado.

### 17.4 Mover es copiar

No hay operador de movimiento. Pasar un valor a una función lo copia; asignarlo
lo copia; retornarlo lo copia. La transferencia de propiedad es una convención:
después de entregar un valor a una función que toma propiedad, deja de usarlo, y
el compilador no te avisará si lo haces.

Por eso la propiedad debe verse en la firma y en la documentación `##`:
`weave take with s as string into void` significa "ahora soy dueño de `s`";
`with s as ref to frozen string` significa "lo presto".

Esto vale para los tipos sin destructor. En un tipo `derive Drop` (§17.7) sí hay
movimiento de verdad: la asignación vacía el origen y el compilador lo sabe, así
que usar el origen después es `E0080` y copiarlo sin `.clone()` es `E0081`.

**Reglas**

* Todo valor propio tiene exactamente un dueño, nombrado en la documentación.
* Copiar un handle propio es un bug salvo que sea una copia profunda explícita.
* `derive Drop` hace que un rune sea dueño de sus campos y que el compilador
  compruebe los movimientos; `derive Nexus` solo aporta la limpieza.
* La transferencia de propiedad es una convención que documentas, salvo en los
  tipos `Drop`, donde la comprueba el compilador.

### 17.5 La pila y el montón, para quien viene de Python o Java

En Python o Java no piensas dónde vive un valor: `x = [1, 2]` crea una lista y
ya está. En PenguScript hay dos lugares donde puede vivir, y elegir es parte de
escribir el programa.

* **La pila (stack)** son las variables locales. Vive mientras dura la llamada
  y muere sola al volver: no hay nada que liberar. Un `int`, un `bool`, un
  `Vec2`, un `Buffer` con sus campos dentro, viven en la pila si los declaras
  como locales.
* **El montón (heap)** son los búferes que crecen o que deben sobrevivir a la
  llamada. `string`, `list of T`, `map of K to V`, `Rc of T` y `std.arena` viven
  ahí. Un valor de la pila puede contener un *handle* de 24 bytes que apunta a
  un búfer del montón.

```pengu-fragment
var n as int is 7                      # pila, se va sola
var s as string is "hola"              # pila el handle, montón el texto
banish s                               # libera el texto
```

Una `string` vacía o un `list` vacío no tienen búfer: el handle está a cero y
`banish` no hace nada. Por eso banishear dos veces no es "seguro" pero tampoco
revienta siempre: deja el handle a cero solo si el tipo es `Drop`.

**Por qué no hay GC.** Un recolector necesita pausas, memoria extra y saber
dónde están todos los punteros. PenguScript compila a C y quiere que el coste de
cada línea sea el que ves: si una función reserva, se nota en su firma y en su
`##`; si libera, también. El GC esconde ese coste.

### 17.6 Puntero, dueño y préstamo

Tres palabras que en Python o Java no necesitas y aquí sí.

* **Puntero** (`ref to T`): una dirección a un valor que vive en otro sitio. No
  eres dueño de lo que apunta. `ref to frozen T` es lo mismo, pero el compilador
  no te deja escribir a través de él.
* **Dueño**: quien tiene la obligación de liberar. En un `string` propio es el
  binding que lo creó; en un `Rc` es el contador; en una `list` propia es el
  binding que la creó.
* **Préstamo**: pasar un valor a una función sin transferir la obligación. Un
  parámetro de tipo contenedor **es** un préstamo por defecto (`§13.7` de
  `LANGUAGE`): el callee no debe banishearlo.

```pengu
import std.scrolls

weave describe with s as string into int:    # prestamo: no libera
    return calling scrolls.len with s

weave take with s as string into void:       # toma propiedad (documentado)
    banish s
```

La regla que evita casi todos los bugs: **si guardas un parámetro, copia**. Un
parámetro es un préstamo; si lo metes en un campo y el que llamó libera el
temporal, tu campo queda colgando.

```pengu-fragment
# MAL: guarda el préstamo
return with data is s

# BIEN: guarda una copia propia (concatenar crea un string nuevo)
return with data is (s + "")
```

### 17.7 Capa 1 — `derive Drop`

Úsala cuando un valor tenga **un** dueño y su vida coincida con un scope. Es el
caso normal: un `Buffer` que se lee de un archivo, un `Parser`, una conexión,
un `World` de un juego.

```pengu
rune Frame derive Drop:
    name as string
    ticks as int

weave read_frame with path as string into Frame:
    return with name is (path + ""), ticks is 0

weave main into int:
    var f as Frame is calling read_frame with "a.txt"
    calling print with "{f.ticks}"
    return 0        # _pengu_cleanup_Frame(&(f)) insertado aquí
```

No escribes `banish f`: el compilador lo hace en cada salida (`return`, `break`,
`continue`, fin de bloque, `or return`). El destructor es el de `derive Nexus`
más un `memset` que lo deja a cero, así que `banish` manual sigue funcionando y
el drop posterior es no-op.

Y no se copia: se mueve.

```pengu-fragment
var a as Frame is calling read_frame with "a.txt"
var b as Frame is a            # mueve: `a` ya no existe
calling print with "{a.ticks}" # error[E0080]
```

**Cuándo no usarla.** Cuando el valor tiene varios dueños que no sabes cuál
muere al final: ahí va la capa 2. Cuando el valor es un componente diminuto que
vive en un array contiguo: no le pongas destructor, el array es el dueño.

**Anti-ejemplo.** Guardar un parámetro prestado en un campo `Drop` y no copiarlo.
El destructor libera lo que el llamador sigue usando. Ese fue un bug real en
`std/compass` (`Path.from_str`), arreglado con `cp_own`.

### 17.8 Capa 2 — `std.consortium`

Úsala cuando dos partes del programa deben ver el mismo valor y no hay una
jerarquía clara: un documento con dos vistas, un nodo con padre y caché, un
asset que comparten varias escenas.

```pengu
import std.consortium
import std.spark

weave main into int:
    var doc as Rc of int is calling Rc.new with 42
    var view as Rc of int is doc          # un incremento, O(1)
    calling spark.println with "{calling view.strong_count}"   # 2
    banish doc
    banish view
    return 0
```

`Rc` copia implícita porque cuesta un incremento no atómico. `Arc` cruza hilos,
y su copia es atómica: por eso se escribe `.clone()`.

```pengu-fragment
var shared as Arc of Counter is calling Arc.new with c
var other as Arc of Counter is calling shared.clone   # explícito y atómico
```

Para mutar hay tres puertas, y las tres dicen lo que cuestan:

* `get` devuelve `ref to frozen T`: leer, nunca escribir.
* `get_mut` devuelve `maybe ref to T` y solo funciona si eres el único dueño.
* `make_mut` clona el valor si está compartido; puede costar O(n).

**Cuándo no usarla.** Para un valor con un dueño claro: `Rc` es más caro y
esconde quién libera. Para un contador dentro de un bucle: el contador es
tráfico de caché.

**Ciclos.** Un padre que apunta a un hijo y un hijo que apunta al padre con
`Rc` no se libera nunca. El hijo guarda `WeakRc` y sube con `upgrade`, que
devuelve `maybe Rc`.

### 17.9 Capa 3 — copy-on-write

`string`, `list of T` y `map of K to V` comparten el búfer al copiar. Copiar es
O(1) y la primera mutación clona:

```pengu-fragment
var a as list of int is [1, 2]
var b as list of int is a          # O(1), comparten bufer
calling b.push with 3              # clona el bufer de b
# a.len == 2, b.len == 3
```

Esto hace que el patrón "paso una lista a una función que la modifica" deje de
ser una copia silenciosa de O(n) y pase a ser gratis hasta que se mute. El
precio: mutar una copia compartida cuesta una copia entera, y por eso existe el
aviso `W0008`:

```bash
psc check --lint=cow src/
```

El aviso señala un `var x is y` dentro de un bucle cuyo cuerpo muta `x`: cada
iteración clona el búfer. La solución es sacar la copia fuera del bucle, o
`make_unique` una vez y reutilizar.

Tres métodos hacen visible el estado: `is_shared`, `ref_count` y `make_unique`.

**Cuándo no usarla.** Cuando el contenedor se muta una vez por iteración y no se
copia; ahí el COW solo añade un contador que nadie usa. Y no la confundas con
propiedad: `banish` sigue siendo tu responsabilidad.

### 17.10 Caso de estudio: un ECS

Un ECS (entidad-componente-sistema) es el ejemplo perfecto porque cada pieza
tiene una vida distinta.

```pengu
rune Position:
    x as float
    y as float

rune Velocity:
    dx as float
    dy as float

rune World derive Drop:
    positions as list of Position
    velocities as list of Velocity
    alive as list of bool
    assets as map of string to Rc of Asset
```

* **`World` y sus `Storage`**: capa 1. El mundo es dueño de sus arrays y muere
  con el scope del juego o de la escena. `derive Drop` libera los tres búferes y
  nadie escribe `banish world`.
* **Componentes** (`Position`, `Velocity`): ninguna capa. Son datos planos,
  `~8` bytes, viven dentro del array contiguo del mundo. Darles destructor haría
  que cada `push` registrara una limpieza que no hace nada.
* **Sistemas**: ninguna capa. Reciben `ref to World` o `ref to frozen World` y
  no son dueños de nada.
* **Assets compartidos** (una textura que usan dos escenas): capa 2, con `Rc`.
  La escena que muere primero suelta su handle; la textura se libera cuando se
  va la última.
* **Snapshots / replays**: capa 3. Copiar el estado del mundo para un replay es
  O(1) por array; si el replay solo lee, nunca se clona el búfer.

```pengu-fragment
var snapshot as World is world      # O(1): comparte los tres arrays
calling snapshot.positions.push with p   # clona solo ese array
```

**Anti-ejemplo.** Poner `Rc` en cada componente "por si acaso": cada componente
pasa de 8 bytes a 16 más una reserva y un contador por acceso. El ECS existe
para evitar exactamente eso.

### 17.11 Cómo elegir capa

| Si el valor… | Usa | Coste visible |
| --- | --- | --- |
| tiene un dueño y una vida de scope | `derive Drop` | destructor en cada salida |
| lo comparten varios dueños sin jerarquía | `Rc` | incremento por copia |
| lo comparten varios hilos | `Arc` + `@shared` | atómico por copia, move-only |
| es un ciclo | `WeakRc` / `WeakArc` | `upgrade` devuelve `maybe` |
| es dato plano dentro de un array | nada | cero |
| se copia mucho y se muta poco | COW (por defecto) | copia completa al mutar |
| se copia y se muta en un bucle | COW + `make_unique` | una copia, no por iteración |

### 17.12 Reglas

1. Si tiene un dueño y vive en un scope, `derive Drop`. No escribas `banish`.
2. Si un parámetro es contenedor o `Drop`, es un préstamo: si lo guardas, copia.
3. Si hay varios dueños y no sabes cuál muere al final, `Rc`. Si cruzan hilos,
   `Arc` y `clone` explícito.
4. Si hay un ciclo, un lado es `Weak`; `upgrade` antes de usar.
5. Para mutar un valor compartido: `get_mut` si eres el único dueño, `make_mut`
   si puede estar compartido. Nunca mutar por `get`.
6. Los componentes y los datos planos no llevan destructor: el array es el
   dueño.
7. Copiar un contenedor es barato; mutar una copia compartida no. Si el
   `--lint=cow` avisa en un bucle, saca la copia o `make_unique`.
8. Documenta en `##` quién libera cuando la firma no lo diga.

## 18. `banish` en profundidad

### 18.1 Qué acepta

`banish x` exige que `x` sea un lvalue mutable de: `string`, `list of T`,
`map of K to V`, `maybe T`, `result of T to E`, `ref to T`, o un rune con
`derive Nexus`. Cualquier otra cosa es `E0008`: literales, temporales, newtypes
`seal`, valores `frozen` y constantes.

```pengu-fragment
banish "hello"                  # E0008
banish calling read with p      # E0008: temporal
var s as string is calling read with p
banish s                        # correcto
```

### 18.2 Comportamiento por tipo

| Objetivo | C emitido | Después |
| --- | --- | --- |
| `string` propio | `pengu_banish_string(&s)` | vacío, `is_owned = 0` |
| `string` prestado | la misma llamada, no-op | sin cambios |
| `list`/`map` | `pengu_banish_*` | vacío |
| `ref to T` | `pengu_banish((void*)p)` | puntero colgante |
| `maybe`/`result` presente | payload + caja liberados | `none` |
| rune `Nexus` | `_pengu_cleanup_T(&v)` | campos liberados |
| elemento (`xs at 0`) | libera ese elemento in situ | la posición sigue ahí |

`banish` **no** pone el puntero a null ni marca el valor como muerto: después de
`banish p`, `p` conserva la dirección antigua. Ponlo a `null` si puede volver a
usarse, o mantenlo en un ámbito cerrado.

### 18.3 Contenedores de contenedores

`banish xs` libera solo el búfer de elementos de la lista. Para `list of string`
los strings de dentro se filtran:

```pengu-fragment
var names as list of string is ["a", "b"]
for n in names:
    banish n          # libera cada string propio
banish names          # libera el array
```

Lo mismo vale para `list of list of int`, `map of string to string` (claves y
valores) y `list` de runes `Nexus`: libera los elementos y luego el contenedor.
`std.loom` y `std.atlas` documentan qué helpers devuelven elementos propios.

### 18.4 Vistas y parámetros

Nunca liberes:

* un parámetro (`with s as string` presta; quien llama libera),
* una vista (`slice`, `bytes of`, un campo `ref to`),
* un literal,
* un valor que retornas.

Si una función toma propiedad, dilo en el nombre y en la documentación
(`take_*`/`free_*`), y no hagas `defer banish` del parámetro.

**Reglas**

* Un `banish` por valor propio, en todos los caminos.
* Libera los elementos antes que el contenedor cuando los elementos son propios.
* Nunca liberes parámetros, vistas, literales ni valores retornados.
* Después de `banish p`, trata `p` como inválido: asigna `null` o cierra el
  ámbito.

## 19. Vistas, préstamos y tiempos de vida

### 19.1 Las tres vistas

| Vista | Se crea con | Válida mientras |
| --- | --- | --- |
| `slice of T` | `xs at i to j`, `slice of …` | el contenedor viva y no se redimensione |
| `bytes of s` | `bytes of s` | el string viva |
| `ref to T` | `sigil of x`, campo `ref to` | el valor viva |

Una vista es un puntero más una longitud. No mantiene vivo al dueño; nada en el
compilador comprueba que el dueño sobreviva a la vista.

### 19.2 Devolver una vista

Devolver una vista de un local siempre está mal: el dueño muere al retornar.

```pengu-fragment
# ❌ colgante: `s` se libera al retornar
weave bad into ref to byte:
    var s as string is "abc"
    defer banish s
    return bytes of s

# ✅ devuelve una copia propia
weave good into string:
    return "abc"
```

Las vistas son para parámetros y temporales dentro de una función, no para
retornos de API. Si una API debe exponer una ventana, devuelve el dueño y un
rango (`start`, `end`), o copia.

### 19.3 Reglas de préstamo

* Un préstamo no debe sobrevivir a su dueño: mantén el dueño en el ámbito o
  devuelve un valor propio.
* No redimensiones un `list` mientras exista un `slice` sobre él: el búfer puede
  moverse.
* No liberes un dueño mientras una vista esté viva.
* Un `ref to frozen T` no puede usarse para mutar; es el tipo correcto para
  parámetros de solo lectura.
* Las vistas pasadas a C solo son válidas durante la llamada.

**Reglas**

* Devuelve dueños, no vistas.
* Una vista nunca sobrevive al valor al que apunta.
* Sin redimensionar mientras una slice esté viva.
* `ref to frozen T` para parámetros de solo lectura; `ref to T` solo al mutar.

## 20. Patrones

### 20.1 Parejas constructor / destructor

Todo módulo que asigna memoria expone una pareja, documentada junta:

```pengu-fragment
weave reader_open with path as string into result of Reader to IoError:
    ...

weave reader_close with r as ref to Reader into void:
    ...
```

Quien llama hace `defer calling reader_close with sigil of r`. El `##` de
`reader_open` dice "quien llama es dueño del resultado y debe llamar a
`reader_close`".

### 20.2 Transferencia de propiedad

```pengu-fragment
## Takes ownership of `buf`; the caller must not use or free it afterwards.
weave send_frame with conn as ref to Conn, buf as list of byte into result of void to NetError:
    defer banish buf
    ...
```

`take_*`/`consume_*` en el nombre, "toma propiedad" en la documentación,
`defer banish` en el cuerpo: el valor tiene exactamente un dueño en cada punto.

### 20.3 Parámetros de salida

Prefiere devolver un `rune` o un `maybe`/`result`. Cuando C exige un parámetro de
salida, envuélvelo para que el puntero no escape:

```pengu-fragment
weave read_size with p as ref to int into bool:
    if p == null:
        return false
    set essence of p is 42
    return true
```

### 20.4 Estado de módulo

Un `static var` de nivel de módulo vive todo el programa: inicialízalo una vez y
no lo liberes durante la operación normal. No guardes ahí datos por petición.

### 20.5 Builder para strings

Repetir `+` sobre strings reasigna el búfer entero cada vez. Usa `std.builder` y
`finish` una sola vez:

```pengu-fragment
var sb as StringBuilder is calling StringBuilder.new
defer banish sb
for i in 0 to 3:
    calling sb.append_int with i
    calling sb.append with ","
var out as string is calling sb.finish
defer banish out
```

### 20.6 Arena para una fase

Cuando muchos objetos pequeños comparten tiempo de vida (un parse, una petición,
un frame), asígnalos en un `Arena` y libera la arena una vez:

```pengu
import std.arena

weave main into int:
    var a as Arena is calling Arena.new
    defer banish a
    var xs as ref to int is calling arena.arena_alloc of int with sigil of a, 10
    set xs at 0 is 7
    calling print with "{xs at 0}"
    return 0
```

La arena libera todos los bloques en `banish a`; los objetos individuales nunca
se liberan. No dejes que los punteros de la arena escapen de la fase.

**Reglas**

* Todo asignador tiene una función de liberación documentada.
* Nombra las transferencias de propiedad (`take_*`, `consume_*`) y documéntalas.
* Crece strings con un builder, no con un bucle de `+`.
* Usa una arena para grafos con ámbito de fase; nunca filtres un puntero de arena
  a una estructura más longeva.

## 21. Fugas y corrupción

### 21.1 Caso 1 — handle de string copiado

```pengu-fragment
var a as string is calling read_all with path
var b as string is a
banish a
calling print with b          # uso después de liberar
```

Arreglo: `var b as string is calling scrolls.copy with a`, o pasar `a` prestado.

### 21.2 Caso 2 — camino de error antes del `defer`

```pengu-fragment
var buf as string is calling read_all with path
let v as maybe V is calling parse with buf
if v is not present:
    return calling err_of with LoadError.Invalid   # `buf` se filtra
banish buf
```

Arreglo: `defer banish buf` inmediatamente después de la asignación.

### 21.3 Caso 3 — liberar una vista

```pengu-fragment
var s as string is "hello"
var v as slice of byte is bytes of s
banish v          # E0008: las vistas no son propias
```

Si compilara en alguna versión futura, corrompería el heap. Las vistas nunca se
liberan.

### 21.4 Caso 4 — lista de strings

```pengu-fragment
var names as list of string is ["a", "b"]
banish names      # filtra "a" y "b"
```

Arreglo: libera cada elemento primero, o usa `pengu_banish_string_list` a través
de un binding si la lista vino de C.

### 21.5 Caso 5 — doble banish de un rune `Nexus`

```pengu-fragment
rune User derive Nexus:
    name as string

var u as User is with name is "ab"
var copy as User is u
banish u
banish copy       # doble free de `name`
```

Arreglo: un solo dueño. Pasa por `ref to User` cuando una función solo lee.

### 21.6 Herramientas

* AddressSanitizer: compila con `cflags = ["-fsanitize=address", "-g"]` en un
  perfil de debug, ejecuta el binario; las fugas se imprimen al salir.
* LeakSanitizer: incluido en ASan en Linux (`ASAN_OPTIONS=detect_leaks=1`).
* Valgrind: `valgrind --leak-check=full ./build/app` para una segunda opinión.
* `MALLOC_CHECK_=3`/`MALLOC_PERTURB_` de glibc para que el uso después de liberar
  falle rápido.
* Tests: ejecuta la suite bajo ASan en CI para los módulos sensibles a memoria.

**Reglas**

* El camino de error es donde viven las fugas: testéalo.
* Las vistas nunca se liberan; los dueños se liberan una vez.
* Un rune `Nexus` tiene un dueño, como un string.
* Ejecuta ASan en todo PR que toque asignación.

## 22. Estrategia de asignación

### 22.1 La pila primero

Números, runes pequeños, arrays fijos (`array of T with size N`) y strings cortos
viven en la pila: sin asignación, sin liberación. Recurre al heap solo cuando el
tamaño sea dinámico o el valor deba sobrevivir a la función.

### 22.2 Una asignación y luego crecer

`list`/`map` crecen geométricamente; cada crecimiento copia. Estima el tamaño y
reserva una vez (helpers de `std.loom`/`std.atlas`), o construye con un
`StringBuilder` y `finish`.

### 22.3 Reutilizar en lugar de reasignar

Un búfer propiedad de un objeto longevo puede limpiarse y reutilizarse
(`builder.reset`, `list.clear`) en vez de liberarlo y reasignarlo en cada
iteración.

### 22.4 Agrupar por tiempo de vida

Agrupa las asignaciones por tiempo de vida: por petición (arena), por frame
(arena), por conexión (struct dueño con `Nexus`). Liberar un dueño libera el
grupo, y no hay contabilidad por objeto.

### 22.5 Medir

Primero `psc time` y `--profile release`; luego `perf`/`heaptrack` sobre el
binario generado. No optimices la asignación antes de que el perfil la señale.

**Reglas**

* Pila salvo que el tamaño sea dinámico o el tiempo de vida escape.
* Reserva una vez; crece geométricamente, nunca elemento a elemento.
* Reutiliza búferes longevos en vez de reasignar.
* Agrupa las asignaciones por tiempo de vida y libéralas juntas.

## Parte V — Tests

## 23. La pirámide de tests

### 23.1 Qué testear y dónde

| Capa | Corre en | Coste | Qué demuestra |
| --- | --- | --- | --- |
| funciones puras | bloques `test` | milisegundos | lógica, casos límite, aritmética |
| contratos de módulo | bloques `test` | milisegundos | invariantes, parejas de propiedad, mapeo de errores |
| integración | invocación del binario / fixtures | segundos | CLI, ficheros, FFI, red |
| extremo a extremo | el artefacto construido | minutos | lo que se entrega funciona |

La mayoría de los tests viven en las dos primeras capas. Si un comportamiento se
puede testear como función, testéalo ahí; un test extremo a extremo que cubre
diez funciones no te dice nada cuando falla.

### 23.2 Qué debe testearse

Toda función pública, al menos una vez, con:

* el camino feliz,
* el límite (vacío, cero, máximo, un elemento),
* el camino de fallo (`maybe none`, `err`, el `E00xx` que gestionas),
* la propiedad: qué se libera en cada camino.

Todo lo que toque memoria, FFI o validación de entrada lleva un test extra.

## 24. Bloques `test`, `ward` y `trial`

### 24.1 Un bloque de test

```pengu
import std.ward

test "arithmetic":
    calling ward.assert_eq_int with 1 + 1, 2

test string_formatting:
    calling ward.assert_eq_string with "abc", "abc"
```

Un test es `test <nombre>:` donde el nombre es un literal de string o un
identificador. Los cuerpos se comprueban en todos los modos; `psc test` emite el
arnés de C y los ejecuta.

### 24.2 `std.ward`

| Helper | Uso |
| --- | --- |
| `assert c` | condición simple |
| `assert_msg c, msg` | condición con mensaje |
| `assert_true` / `assert_false` | booleanos |
| `assert_eq_int` / `assert_ne_int` | enteros |
| `assert_eq_string` / `assert_ne_string` | strings |
| `assert_eq_bool` / `assert_ne_bool` | booleanos |
| `assert_eq_float a, b, eps` | floats con tolerancia (por defecto `0.000001`) |

Una aserción fallida imprime fichero, línea y esperado/obtenido, y aborta la
ejecución de los tests.

### 24.3 Estructura: preparar, actuar, afirmar

```pengu-fragment
import std.ward

weave parse_pair with text as string into maybe (int, int):
    ...

test "parse_pair rejects half a pair":
    let got as maybe (int, int) is calling parse_pair with "7"
    calling ward.assert_false with got is present

test "parse_pair reads two numbers":
    let got as maybe (int, int) is calling parse_pair with "7,9"
    calling ward.assert_true with got is present
    calling ward.assert_eq_int with got.value.first, 7
    calling ward.assert_eq_int with got.value.second, 9
```

Un comportamiento por test, nombrado por el comportamiento ("rejects half a
pair"), no por la función.

### 24.4 Tests dirigidos por tabla

```pengu-fragment
rune Case:
    input as string
    expected as int

weave run_cases with cases as list of Case into void:
    for c in cases:
        let got as maybe int is calling spark.parse_int with c.input
        calling ward.assert_true with got is present
        calling ward.assert_eq_int with got.value, c.expected
```

Una tabla gana a diez tests copiados: añade una fila, no una función.

### 24.5 Errores y propiedad

```pengu-fragment
test "load_config maps a missing file to Missing":
    let r as result of Config to ConfigError is calling load_config with "/nonexistent"
    calling ward.assert_false with r.is_ok
    calling ward.assert_eq_int with (r.error to int), (ConfigError.Missing to int)
```

Comprueba que la variante de fallo es la esperada, no solo que "falló".

### 24.6 `std.trial`

Para runners de estilo suite (los usan los tests de std), `std.trial` ofrece
`new_suite`, `test_case`, `test` y `summary`:

```pengu-fragment
var suite as TestSuite is calling trial.new_suite with "parsing"
defer banish suite
calling trial.test_case with sigil of suite, "empty input", (calling parse with "") is present, ""
let ok as bool is calling trial.summary with sigil of suite
```

Usa bloques `test` para código nuevo; `trial` es para hosts que quieren su propio
runner y formato de informe.

**Reglas**

* Un comportamiento por test; el nombre dice el comportamiento.
* Afirma sobre la variante de fallo, no solo sobre el fallo.
* Tablas para familias de entrada/salida.
* Toda pareja de propiedad lleva también un test del camino de error.

## 25. `psc test`

### 25.1 Ejecutar

```console
$ psc test              # every test block in the project
$ psc test --watch      # rerun on change
$ psc test --json       # JSON Lines events, for CI
$ psc test --verbose    # show each test
```

Flags: `--profile`, `--cc`, `--target`, `--entry`, `--json`, `--watch`,
`--verbose`. En 0.28.0 no hay filtro por nombre: si necesitas ejecutar un
subconjunto, separa las suites lentas en su propio proyecto o archivo.

El comando termina con código distinto de cero si algún test falla, que es lo que
mira CI.

### 25.2 `--json`

Cada evento es una línea JSON con el nombre y el estado del test, para que CI
pueda anotar fallos sin parsear la salida de consola.

### 25.3 Escribir para el runner

* Sin estado mutable global compartido entre tests; cada test prepara lo que
  necesita.
* Sin dependencia del orden de ejecución.
* Limpia lo que creas (`defer` del borrado de ficheros y directorios temporales).
* Mantén los tests rápidos: sin esperas, sin red salvo que sea el tema.

## 26. Casos difíciles

### 26.1 Ficheros y fixtures

```pengu-fragment
import std.archivum
import std.compass

test "write then read a temp file":
    let dir as string is calling archivum.temp_dir
    defer banish dir
    defer calling archivum.remove_dir with dir, true
    let path as string is calling compass.join with [dir, "sample.txt"]
    defer banish path
    calling ward.assert_true with (calling archivum.write_file with path, "hi")
    let back as maybe string is calling archivum.read_file with path
    defer banish back
    calling ward.assert_true with back is present
    calling ward.assert_eq_string with back.value, "hi"
```

Las fixtures viven en `tests/fixtures/` para datos estáticos y en un directorio
temporal para datos generados. Nunca escribas en el repositorio durante un test.

### 26.2 FFI

Testea el wrapper, no la librería de C. Dale valores conocidos, comprueba las
variantes de error mapeadas y ejecuta al menos un test bajo ASan para que una
liberación incorrecta salte.

### 26.3 Concurrencia

Ejecuta el test muchas veces (`for i in 0 to 1000`) y usa canales o un
`WaitGroup` para crear entrelazados reales. Un único verde no demuestra nada.

### 26.4 Memoria

Compila el binario de test con `-fsanitize=address` y ejecútalo: las fugas y los
dobles free abortan con traza. Es el test de propiedad más barato que hay.

### 26.5 Wasm

Los tests con `--target wasm` corren en el arnés del navegador (`tests/wasm`); los
módulos ligados al DOM (`std.web.*`) se testean ahí, no en `psc test` nativo.

### 26.6 Determinismo

Siembra la aleatoriedad (`std.lot`) explícitamente en los tests. El código
dependiente del tiempo recibe el reloj como parámetro, para que el test pueda
pasar un instante fijo.

**Reglas**

* Las fixtures nunca escriben en el repositorio.
* Testea el wrapper alrededor de C, no la librería de C.
* Los tests de concurrencia se repiten; los de memoria corren bajo ASan.
* La aleatoriedad y el tiempo se inyectan, no se leen del entorno.

## 27. CI

### 27.1 El pipeline

```yaml
- run: tools/build_bootstrap.sh
- run: build/psc-stage0 build . --profile release
- run: ./tests/run.sh
- run: build/psc test
- run: python3 tools/docs/validate_docs.py docs/LANGUAGE.md docs/LANGUAGE.es.md
```

El `.github/workflows/ci.yml` existente hace el bootstrap, construye `psc` en
Ubuntu y macOS y ejecuta la suite. Añade después los tests de tu proyecto.

### 27.2 Un job de memoria

```yaml
- run: build/psc build . --profile debug --cc "cc -fsanitize=address -g"
- run: ./build/app --self-test
```

ASan en CI caza lo que la revisión deja pasar. Ejecútalo en los módulos que
asignan memoria.

### 27.3 Puertas

Un pull request está en verde solo cuando:

- [ ] `psc check` está limpio.
- [ ] `psc test` pasa.
- [ ] el código nuevo tiene tests de éxito y de fallo.
- [ ] las docs se construyen y los enlaces validan (si cambiaron las docs).
- [ ] no hay warnings nuevos en el C generado.

**Reglas**

* CI ejecuta los mismos comandos que ejecutas en local.
* Los módulos sensibles a memoria tienen un job de ASan.
* Un pipeline rojo bloquea el merge; no hay "merge y arreglo luego".
* Las docs se validan como el código: enlaces rotos y ejemplos que no compilan
  fallan.

## Parte VI — Librerías y bindings

## 28. Diseñar una API pública

### 28.1 Las reglas

1. **Nombra la acción, no la implementación.** `read_file`, no `do_read2`.
2. **Devuelve la verdad.** `maybe` para ausencia, `result` para fallo, nunca un
   `bool` más un parámetro de salida.
3. **Una forma obvia.** Si dos funciones hacen lo mismo, borra una.
4. **Superficie pequeña.** Todo símbolo público es una promesa: haz que sean
   pocas.
5. **Consistente con std.** Mismo verbo (`read`, `write`, `open`, `close`,
   `parse`, `format`), mismo orden de parámetros (objetivo primero, opciones al
   final).
6. **La propiedad está en la firma.** `take_*`/`consume_*` toman propiedad;
   `ref to frozen T` presta; todo lo demás devuelve valores propios.
7. **Las opciones son un rune,** no ocho booleanos.
8. **Sin flags que cambien el tipo de retorno.** Divide la función.
9. **Un `omen` de error por frontera,** documentado variante a variante.
10. **Documentado, o no existe.** `##` en todo símbolo público.

### 28.2 Forma

```pengu-fragment
## Opens a reader for `path`. The caller owns the result and must call
## `reader_close`. Returns `IoError.NotFound` if the file does not exist.
weave reader_open with path as string into result of Reader to IoError:
    ...

## Reads up to `n` bytes into `buf`. Returns the number of bytes read.
weave reader_read with r as ref to Reader, buf as ref to byte, n as usize into result of usize to IoError:
    ...

## Releases the reader. Safe to call once; the value must not be used after.
weave reader_close with r as ref to Reader into void:
    ...
```

El trío documenta quién es dueño de qué en cada paso; quien llama nunca tiene que
leer la implementación para saber cuándo liberar.

### 28.3 Rune de opciones

```pengu-fragment
rune OpenOptions:
    create as bool
    truncate as bool
    mode as int

weave default_open_options into OpenOptions:
    return with create is false, truncate is false, mode is 0o644
```

Añadir un campo no es un cambio incompatible; añadir un parámetro sí.

**Reglas**

* Una promesa por símbolo público; documéntala con `##`.
* La propiedad se declara en la documentación y se refleja en el nombre.
* Rune de opciones para todo lo que tenga más de dos mandos opcionales.
* Sin parámetros booleanos que cambien el comportamiento en silencio.

## 29. Versionado y deprecación

### 29.1 Versiones

* Un paquete tiene una `version` en `pengu.toml`, semver: `MAJOR.MINOR.PATCH`.
* `MAJOR` cambia por un cambio incompatible, `MINOR` por añadidos, `PATCH` por
  correcciones.
* La versión del compilador y la del paquete son independientes; el paquete
  declara en su README el rango de compilador que soporta.

### 29.2 Deprecación

```pengu-fragment
@deprecated("use read_file_result; this returns a bool and hides the cause")
weave read_file with path as string into bool:
    ...
```

`@deprecated` emite un aviso en cada uso. El ciclo de deprecación:

1. Añade el reemplazo.
2. Marca el símbolo viejo `@deprecated("use X")` y documenta la migración en el
   mismo `##`.
3. Mantenlo al menos una release menor.
4. Elimínalo en la siguiente mayor.

### 29.3 Changelog

Una entrada por release, en el `CHANGELOG.md` del repositorio, agrupada como
Added, Changed, Deprecated, Removed, Fixed. El changelog es para usuarios: di qué
deben hacer, no qué archivo interno cambió.

**Reglas**

* Semver, con honestidad: un renombrado es un cambio mayor.
* Depreca antes de eliminar, con el reemplazo en el mensaje.
* Toda release tiene entrada de changelog.
* El README declara el rango de compilador soportado.

## 30. Empaquetar una librería

### 30.1 Estructura

```
mylib/
  pengu.toml
  src/
    mylib.pengu          # public API, module docstring
    mylib_internal.pengu # helpers, not imported by users
  tests/
    mylib_test.pengu
  README.md
  CHANGELOG.md
  LICENSE
```

`pengu.toml`:

```toml
[project]
name = "mylib"
version = "0.1.0"
entry = "src/mylib.pengu"
output = "static"

[build]
src_dir = "src"
```

`psc build` escribe `build/libmylib.a`. `output = "shared"` escribe
`build/libmylib.so` (o `.dylib`). Un proyecto de librería no tiene `main`; el
módulo de entrada contiene la API pública.

### 30.2 Símbolos

Los símbolos C generados llevan el prefijo del módulo, no el del proyecto. Fija
los nombres que exportas con `insignia mylib_` en el módulo de entrada:

```pengu-fragment
insignia mylib_

weave add with a as int, b as int into int:
    return a + b
```

produce `int32_t mylib_add(int32_t a, int32_t b)`.

### 30.3 Consumir una librería

Quien consume enlaza el archivo y el runtime:

```console
$ cc app.c build/libmylib.a runtime/pengu_runtime.c -I runtime -lm -lpthread -o app
```

El README de la librería debe indicar esta línea y la versión de ABI con la que se
construyó. Los archivos estáticos no incluyen el runtime.

### 30.4 Documentación

`psc doc --output docs/api` genera una página por módulo a partir de los
comentarios `##`. Publica esas páginas con la librería; son la referencia de API
que leen los usuarios.

**Reglas**

* Los proyectos de librería no tienen `main`; el módulo de entrada es la API
  pública.
* Fija los símbolos exportados con `insignia`.
* El README lleva la línea de enlace exacta y la versión de ABI.
* La salida de `psc doc` se publica con la release.

## 31. Escribir un binding de C

### 31.1 Archivos

| Archivo | Contenido |
| --- | --- |
| `src/mylib.d.pengu` | `include`, `link`, `insignia`, `declare`, tipos de layout |
| `src/mylib.pengu` | la API segura: wrappers, mapeo de errores, propiedad |
| `tests/mylib_test.pengu` | tests del wrapper, incluidos los caminos de error |

El `.d.pengu` se genera (`psc bind`) o se escribe a mano; el wrapper siempre se
escribe a mano y siempre está documentado.

### 31.2 Reglas del wrapper

* Valida las entradas antes de llamar a C.
* Convierte `string` con `ffi.cstr_from_string` (la conversión automática solo
  vale para literales).
* Mapea cada código de error de C a una variante del `omen`; conserva el código
  numérico en el mensaje si ayuda a depurar.
* Sé dueño de toda asignación; nunca devuelvas un puntero C desnudo.
* Libera con el asignador que produjo la memoria.

### 31.3 Checklist

- [ ] `.d.pengu` no tiene cuerpos y usa tipos exactos.
- [ ] La propiedad de cada puntero retornado está documentada.
- [ ] El wrapper mapea errores a un `omen`.
- [ ] El wrapper no filtra: toda asignación tiene un `banish`.
- [ ] Los tests cubren éxito, fallo y un argumento incorrecto.
- [ ] El README declara la dependencia nativa y cómo instalarla.

**Reglas**

* El archivo de declaraciones y el wrapper están separados.
* Ningún puntero C crudo escapa del wrapper.
* Los códigos de error se convierten en variantes, no en strings.
* Todo binding tiene un test que falla cuando falta la librería.

## 32. `psc bind`

### 32.1 Generar

```console
$ psc bind include/mylib.h --prefix mylib_ --links mylib -o src/mylib.d.pengu
```

El helper (`pengu-bind`, construido desde C con clang) lee la cabecera y emite
`declare`s, tipos de layout y directivas `include`/`link`. Flags: `--prefix`,
`--output`, `--cpp-flags`, `--preprocessed`, `--auto-import`, `--define/-D`,
`--links`, `--ignore`, `--include-paths`, `--no-comments`, `--system-includes`,
`--no-blank-extensions`, `--no-cpp`, `--helper-version`, `--print-helper`.

### 32.2 Revisar

El generador no puede conocer la propiedad, así que revisa cada función:

* `char *` → ¿quién lo libera? Normalmente `ref to char` en la declaración y un
  wrapper que copia o posee.
* `void *` → `ref to opaque`, nunca `ref to void` en la API pública.
* `size_t` → `usize`; `ssize_t` → `isize`.
* structs por valor → un `rune` con `@packed`/`@align` que replique la cabecera.

### 32.3 Regenerar

Mantén los comentarios a mano en el wrapper, nunca en el `.d.pengu`; regenerar
sobrescribe el archivo. Trata el diff regenerado como entrada de revisión.

**Reglas**

* Genera y luego revisa cada declaración.
* Los comentarios y la propiedad viven en el wrapper.
* Regenera tras cada cambio de cabecera y commitea el diff junto al cambio.

## 33. Satélites

Un satélite es una dependencia C vendorizada bajo `std_c/<name>/`:

```
std_c/mylib/
  README.md      # what it is, version, license, how it is built
  LICENSE
  SOURCE         # upstream URL and commit/tag
  pengu.pkg      # build metadata used by the doc/build tooling
  mylib.c
  mylib.h
```

Reglas:

* Fija el commit de origen en `SOURCE`; nunca sigas una rama.
* Registra la licencia en `LICENSE` y en `THIRD_PARTY.md`.
* Añade el binding (`std/<lib>.d.pengu`) y el wrapper (`std/<latin>.pengu`).
* Política de enlace: `link "mylib"` se convierte en `-lmylib` solo si alguna
  función viva lo necesita; las builds de release podan el código nativo no
  usado, así que un satélite no cuesta nada si no se usa.
* Los scripts de descarga (`tools/fetch_satellite.sh`) deben ser reproducibles.

**Reglas**

* Un directorio por satélite, con versión, licencia y origen fijados.
* El binding y el wrapper forman parte del cambio del satélite.
* Un satélite sin usar no debe añadir flags de enlace ni tamaño al binario.

## 34. ABI y release

### 34.1 Qué es estable

`PENGU_ABI_VERSION` (ahora 3) fija el layout de los structs del runtime y los
nombres de sus funciones. El C generado lo comprueba en tiempo de compilación:

```c
_Static_assert(PENGU_ABI_VERSION == 3, "pengu_runtime.h ABI mismatch: bundle expects v3");
```

Una librería compilada contra una versión del runtime debe enlazarse con un
runtime compatible. Por eso el README declara la versión.

### 34.2 Layout

| Tipo | Layout | Notas |
| --- | --- | --- |
| `string` | `{ char *data; int len; int32_t is_owned; }` | 16 bytes en 64 bits |
| `list` | `{ void *data; int len; int cap; size_t elem_size; }` | 24 bytes |
| `maybe` | `{ bool is_present; void *value; }` | payload boxeado |
| `rune` | campos en orden de declaración | padding según el ABI de C |

`@packed` elimina el padding; `@align(N)` sube la alineación. Úsalos solo para
igualar un ABI externo, y declara el struct C espejo al lado.

### 34.3 Símbolos exportados

* Por defecto: `<module>_<name>`.
* `insignia <prefix>` sobrescribe el prefijo.
* `@export("symbol")` fuerza un nombre y marca el símbolo como raíz de DCE.
* Nunca `@export` sin prefijo de proyecto: la colisión con libc es un error de
  enlace en el mejor caso y la función equivocada en el peor.

### 34.4 Checklist de release

- [ ] `psc check` y `psc test` limpios.
- [ ] Build `--profile release`, sin warnings nuevos.
- [ ] Versión subida en `pengu.toml`, changelog escrito.
- [ ] `psc doc` regenerado y publicado.
- [ ] Símbolos exportados con `insignia`/`@export` revisados.
- [ ] Versión de ABI documentada en el README.
- [ ] LICENSE y THIRD_PARTY.md actualizados.

**Reglas**

* Nunca publiques una librería sin la versión de ABI en el README.
* Atributos de layout solo para un ABI externo, con la declaración C espejo.
* `@export` siempre con espacio de nombres.
* El checklist de release forma parte del PR de release.

## Parte VII — Rendimiento y entrega

## 35. Rendimiento

### 35.1 Perfiles

| Perfil | Flags | Uso |
| --- | --- | --- |
| `debug` | `-O0 -g` | desarrollo, ASan |
| `release` | `-O2 -DNDEBUG` | entrega |
| `small` | `-Os -DPENGU_SIZE_OPT` | wasm, embebido, tamaño restringido |

Añade los tuyos en `pengu.toml`:

```toml
[profiles.fast]
cflags = ["-O3", "-march=native"]
```

### 35.2 Eliminación de código muerto

El compilador poda funciones y tipos sin usar antes de emitir:

* `--prune-types` elimina declaraciones de tipo sin usar,
* `--prune-native` elimina flags de enlace nativo sin usar,
* `--dce-scope=user` limita la poda a los módulos de usuario (mantiene std
  completo),
* `--no-dce` conserva todo (depuración).

`@export("name")` marca un símbolo como raíz de DCE: úsalo para puntos de entrada
llamados desde C, y siempre con prefijo de proyecto.

### 35.3 Microoptimizaciones que importan

* `@inline` en funciones calientes muy pequeñas; no lo pongas en todo — daña la
  caché de instrucciones.
* `@cold` en caminos de error, para que el camino caliente quede compacto.
* Prefiere `array of T with size N` a `list` para datos fijos y calientes.
* Construye strings con `StringBuilder`, no con `+` repetido.
* Reserva capacidad de `list` cuando el tamaño se conoce.
* Evita la indirección `ref to opaque` en bucles ajustados.

### 35.4 Medir

```console
$ psc time build --profile release
$ psc build --profile release --verbose
$ perf stat ./build/app
$ heaptrack ./build/app
```

Mide antes y después; un cambio sin número antes/después no es una optimización.

### 35.5 `--release-unsafe`

Elimina las comprobaciones de límites. Solo es una ganancia medible en código con
mucho indexado, y convierte un bug en corrupción de memoria. Úsalo solo con tests
que cubran los límites, y documéntalo en el perfil de build.

**Reglas**

* `release` para entregar, `small` para objetivos con restricción de tamaño.
* DCE activado; `@export` solo para raíces reales.
* Perfila primero, optimiza después y conserva los números.
* `--release-unsafe` necesita un test que demuestre los límites.

## 36. WebAssembly y assets

### 36.1 Objetivo

```console
$ psc build --target wasm
$ psc run   --target wasm
$ psc test  --target wasm
```

`wasm32-unknown-emscripten` es el único objetivo wasm; `wasm32-wasi` se rechaza.
Emscripten (`emcc`, `emar`) debe estar instalado y activado (`emsdk`), y el
runtime wasm se construye una vez con `./tools/build_runtime_wasm.sh`.

Artefactos para `output = "exe"`: `app.html`, `app.js`, `app.wasm` — viajan
juntos y deben servirse por HTTP (`file://` bloquea la carga del `.wasm`).

### 36.2 `std.web`

`std.web` es el puente de Emscripten: `console_*`, el bucle principal, DOM
(`dom`, `event`), canvas, storage, fetch (`http`), websockets, clipboard,
history, location, router, browser, file y crypto. `std.web.url` y
`std.web.security` son puros y también corren de forma nativa.

Protege el código exclusivo del navegador con `when wasm:`; la rama inactiva se
elimina antes de emitir.

### 36.3 Assets

```toml
[assets]
dir = "assets"
module = "assets"
embed = true
exclude = ["*.tmp"]
```

`psc assets` escribe `src/<module>.pengu` (constantes `ASSET_<NAME>` y
`declare`s `_<module>_count`, `_<module>_name`, `_<module>_data`,
`_<module>_size`, `_<module>_string`) y los archivos C en `build/`. Con
`embed = true` los bytes se compilan dentro del binario; si no, se leen del disco
en tiempo de ejecución.

```pengu-fragment
import assets

weave main into int:
    let data as ref to frozen void is calling _assets_data with "logo.png"
    let size as usize is calling _assets_size with "logo.png"
    calling print with "{size} bytes at {data}"
    return 0
```

### 36.4 Tamaño

Los binarios wasm llevan el runtime: mide con `psc build --profile small
--target wasm` y `ls -l build/app.wasm`. `--prune-native` y el perfil `small` son
las primeras palancas; `-Oz` mediante un perfil propio es la segunda.

**Reglas**

* Sirve los tres artefactos wasm juntos por HTTP.
* Protege el código exclusivo del navegador con `when wasm:`.
* Los assets se generan, nunca se editan a mano.
* Mide el tamaño wasm en el job de release.

## 37. Entrega

### 37.1 El checklist de release

- [ ] Versión subida (`pengu.toml`, changelog).
- [ ] `psc check` y `psc test` limpios en las plataformas soportadas.
- [ ] Build `--profile release`, sin warnings nuevos de C.
- [ ] Módulos sensibles a memoria testeados bajo ASan.
- [ ] Docs regeneradas (`psc doc`) y validadas (`validate_docs.py`).
- [ ] Los ejemplos siguen compilando.
- [ ] Versión de ABI y dependencias nativas declaradas en el README.
- [ ] LICENSE y THIRD_PARTY.md al día.
- [ ] Artefactos nombrados y con checksum por el job de release.

### 37.2 Qué necesitan los usuarios

Una release no es solo un binario:

* el README con instalación, línea de enlace y rango de compilador soportado;
* la documentación de API de `psc doc`;
* el changelog de esta versión;
* la licencia y los avisos de terceros.

### 37.3 Después de la release

Etiqueta, publica el changelog y abre un issue para el siguiente ciclo de
deprecación. Una release sin seguimiento es una release que nadie mantiene.

**Reglas**

* El checklist es el PR de release, no un recordatorio.
* Los usuarios reciben docs, changelog y licencia con el artefacto.
* Toda release arranca el siguiente ciclo de deprecación.

## Apéndice A — De C a Pengunic

| Modismo C | Pengunic |
| --- | --- |
| `for (i = 0; i < n; i++)` | `for i in 0 to n:` |
| `for (i = n - 1; i >= 0; i--)` | construye un `list` invertido y `for x in xs:`, o un `while` explícito |
| `if (p == NULL)` | `if p == null:` |
| `if (!ok) return -1;` | `return calling err_of with E.Failed` |
| `char *s = malloc(n + 1)` | `var s as string is ""` + builder |
| `strlen(s)` | `s.len` |
| `strcmp(a, b) == 0` | `a == b` |
| `strcpy(dst, src)` | `set dst is calling scrolls.copy with src` |
| `struct { int x, y; }` | `rune Point:` con campos |
| `typedef struct X X; X *p` | `rune X` + `ref to X` |
| `enum { A, B }` | `omen E:` + `A`, `B` |
| `union` | `omen` con payloads `@packed` |
| `switch (x) { case 1: … }` | `judge x:` + `is 1:` |
| `goto cleanup` | `defer` / `errdefer` |
| `free(p)` | `banish p` |
| `p = NULL` tras liberar | asigna `null` explícitamente |
| `assert(c)` | `ward.assert` en tests; `panic` para invariantes |
| `printf("%d", n)` | `calling print with "{n}"` |
| `snprintf(buf, n, …)` | `StringBuilder` + `finish` |
| `errno` | `result of T to E` |
| `bool ok, T *out` | `result of T to E` |
| `sizeof(T)` | `size of T` |
| `(uint8_t *)p` | `transmute` (documentado) o `bytes of` |
| global `static` | `static var` a nivel de módulo |
| `#define N 10` | `const N as int is 10` |
| `#include <x.h>` | `include "x.h"` en un `.d.pengu` |
| `-lx` | `link "x"` |
| `#ifdef __EMSCRIPTEN__` | `when wasm:` |

## Apéndice B — Checklist de estilo

- [ ] El archivo se llama `snake_case.pengu`; el módulo coincide.
- [ ] Los tipos son `PascalCase`; los runes son sustantivos.
- [ ] Las funciones son verbos `snake_case`; los predicados se leen como preguntas.
- [ ] Las constantes son `SCREAMING_SNAKE_CASE`.
- [ ] Orden del módulo: directivas, imports, constantes, conceptos, tipos, binds,
      enchantings, funciones, helpers, tests.
- [ ] Todo símbolo público tiene un docstring `##` con nota de propiedad.
- [ ] Sin `+` sobre strings en un bucle; sin acumulación con `+=`.
- [ ] `let` cuando el binding nunca cambia; `var` en caso contrario.
- [ ] Los errores son `maybe`/`result`, no `bool` más parámetros de salida.
- [ ] Las transferencias de propiedad se llaman `take_*`/`consume_*` y están
      documentadas.
- [ ] Sin `antiquus` sin contrato y test.
- [ ] Sin `@export` sin prefijo.
- [ ] `psc fmt` aplicado; `psc check` limpio.

## Apéndice C — Checklist de pull request

- [ ] El cambio tiene un solo propósito y una frase que explica por qué.
- [ ] Tests: éxito, fallo, límite; propiedad en los caminos de error.
- [ ] `psc check`, `psc test`, `psc fmt --check` pasan.
- [ ] El código sensible a memoria corrió bajo ASan.
- [ ] Docs actualizadas (`##`, referencia, changelog) si cambió el comportamiento.
- [ ] Sin dependencia nueva sin entrada de licencia.
- [ ] Sin prints de depuración, sin código comentado.
- [ ] El diff es revisable: sin reformateos no relacionados.

## Apéndice D — Glosario

| Término | Significado |
| --- | --- |
| owned | el valor es responsable de liberar su almacenamiento |
| view / borrow | puntero más longitud hacia almacenamiento de otro |
| banish | liberar un valor propio; `E0008` si no lo es |
| payload | el valor dentro de un `maybe`/`result` |
| lowering | el C que se emite para una construcción |
| rune | tipo producto (struct) |
| echo | tipo suma (parecido a union) |
| omen | enumeración de variantes, opcionalmente con payloads |
| seal | newtype nominal |
| insignia | prefijo para los nombres de símbolos C generados |
| bounds | rango de índices válidos de una secuencia |
| DCE | eliminación de código muerto |
| ABI | contrato binario entre el C generado, el runtime y quien llama desde C |

## Apéndice E — FAQ

**¿Por qué `banish` es explícito?**
Porque el lenguaje no tiene GC ni borrow checker; la liberación explícita es el
único modelo que el compilador puede comprobar del todo (`E0008`) sin seguir
tiempos de vida.

**¿Por qué copiar un string no copia el texto?**
Porque `PenguString` es un handle. Copia el handle cuando quieras compartir
(prestar), o llama a `scrolls.copy` cuando quieras un segundo búfer propio.

**¿Por qué no puedo hacer `try` de otro tipo de error?**
Los dominios de error son explícitos; mapear entre ellos es una decisión que
quien llama debe ver (`E0045`).

**¿Por qué `as` solo funciona en condiciones?**
`as` estrecha un `maybe`/`result` en un `if`; la conversión numérica es `to`, que
trunca, y `transmute`, que reinterpreta bits.

**¿Hay hilos y corrutinas?**
Sí. 0.30.0 añadió hilos de primera clase (`filum.start`, `join`, `detach`,
`free`), 0.31.0 añadió `std.coro` (corrutinas stackful explícitas con `resume` y
`yield`, en el mismo hilo) y 0.53.9 añade `std.reactor`: un `EventLoop` explícito
que hace `epoll_wait`/`poll` y reanuda las tareas. No hay `async`/`await` como
palabras clave ni un planificador escondido: tú creas el loop, haces `spawn` y
llamas `run`. Las variantes `*_async` de la stdlib son funciones que suspenden la
corrutina actual y solo funcionan dentro de una tarea del loop.

**¿Por qué `float` es de 32 bits?**
Porque coincide con el `float` de C; usa `f64` cuando importe la precisión.

**¿Por qué `@export` necesita prefijo?**
Los símbolos sin prefijo colisionan con libc y otras librerías en el enlace.

**¿Por qué las docs insisten en `##`?**
`psc doc` lee solo `##`; un comentario `#` es invisible en la API generada.

**¿Por qué `many T` no se puede usar?**
Está reservado para variádicos y aún no está conectado a ningún punto de llamada;
usa `slice of T`.

**¿Por qué los tests necesitan ASan?**
El compilador no detecta fugas ni dobles free; ASan sí, y es más barato que un
incidente en producción.
