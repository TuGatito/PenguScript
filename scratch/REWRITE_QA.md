# QA de la reescritura 0.6.0

Fecha: 2026-11-12

## Alcance

Reescritura de `docs/LANGUAGE.md` bajo el brief de misión `0.5.0`, con las
adiciones `0.6.0`: lenguaje propio con backend Rust invisible, ~15 conceptos,
núcleo minimalista.

## Estado

- Documento: `docs/LANGUAGE.md`, versión `0.6.0`, 28 secciones.
- Spec anterior archivada en `scratch/legacy/LANGUAGE_rc1.md`.
- Fuentes de composición en `scratch/rewrite/` (histórico; `docs/LANGUAGE.md` es la fuente autoritativa).

## Comprobaciones estructurales

Ejecutadas con `python3 scratch/tools/check_rewrite.py`:

- 28 secciones, 29 anchors, 56 enlaces internos, 0 roto.
- 159 códigos de diagnóstico únicos (151 errores, 8 warnings; ≤ 160).
- 33 filas de garantías (≤ 50).
- 0 términos prohibidos en §§1–21.
- Sin tabuladores; fences balanceados.

Ejecutadas con `python3 scratch/tools/check_pengu_blocks.py`:

- 146 bloques `pengu`.
- Indentación de 4 espacios, delimitadores balanceados, sin términos retirados.
- 0 errores.

## Correcciones tras la revisión m03968

Se corrigieron los bloqueantes de la revisión editorial:

- `Ordering` en la prelude; `Ord.cmp` devuelve `Ordering`.
- `curse` como expresión en la gramática; `if`/`loop` unificados como expresiones.
- Patrones con nombre y brazos `match` con bloque ya presentes; se verificaron.
- `bind ok(...)` en ejemplos que desempaquetan `Result`.
- Códigos duplicados eliminados; `E1801` → `E4109`; 7 warnings reintroducidos.
- `Vec`/`Map`/`Set` fuera de keywords contextuales.
- Métodos pueden devolver vistas ligadas al receptor; funciones libres no.
- Items solo en módulos, `pact` y `ritual`.
- Menores: `grimoire` con `return`, `Show`/`Ordering` documentados, `std.iter`, `in` al mismo nivel que igualdad, campos `unveil`, `Box` justificado.

## Adiciones 0.6.0

- `ritual` inherente sobre primitivos solo dentro de `std`; pact local permitido. Códigos `PGS-E1210` y `PGS-W1210`.
- `.d.pengu` con cabecera `abi` (`"C"`, `"system"`, `"js"`, `"pengu"`), declaraciones sin cuerpo, visibilidad pública implícita, `[declarations]` en `Tome.toml`.
- `Ptr[T]` como tipo de borde para opacos de FFI, solo en `.d.pengu`, `foreign` y `curse`.
- Nuevas producciones §19.14 y `ptr_type` en §19.4.
- ADR D35/D36 y changelog `0.6.0`.
- Catálogo: 159 códigos (151 errores, 8 warnings); límite 160.

## Cierre de huecos semánticos

- Overflow entero comprobado siempre; métodos wrapping/checked/saturating.
- `Float` IEEE 754: sin `Eq`/`Ord`/`Hash`, sin claves de `Map`/`Set`.
- `Tome.lock` TOML, formato 1, commit/checksum, features y resolución determinista git/path.
- Mapeo de errores del backend vía `sourcemap.json`; fallback `PGS-E2014`.
- Módulos duplicados/ambiguos `PGS-E2013`; namespaces de módulos/tipos/valores.
- `CStr`/`CString` en `std.ffi`; firmas completas de `Option`/`Result`.
- `match` sobre `Bool` sin `else` si cubre `true`/`false`; `return` normal en
  `grimoire`; `bind ... else` solo como sentencia; variantes sin `unveil`
  propio.

## Cierre de regresiones 0.6.0

- `as` documentado con tabla: entero -> entero trunca; `Float` -> entero
  satura y `NaN` -> 0; const eval idéntico. `300 as U8` = 44; `sigil X: U8 = 300`
  es error.
- `?` prohibido en closures; `PGS-E7004` cubre `return` y `?`.
- `abi "js"` diferido; en 0.6.0 siempre `PGS-E2022`; solo backend Rust.
- `[link]` en `Tome.toml` para `abi "C"`/`"system"`; falta de entrada o
  librería es `PGS-E2023`/`PGS-E1803`.
- `sigil`/`relic` fuera de `ritual`; `PGS-E1204` cubre asociados no
  soportados.
- `panic` desenrolla, ejecuta `Drop` y termina; cruzar FFI aborta.
- `sigil` solo acepta literales, casts, operadores, constructores, arrays,
  tuplas, `some`/`none`/`ok`/`err` y otros `sigil`; sin llamadas.
- `.d.pengu` de módulos distintos pueden repetir nombres; conflicto por
  módulo duplicado (`PGS-E2013`) o import sin alias (`PGS-E2005`).

## Modelo de paquetes git (D37)

- `[dependencies]` solo acepta git (`tag`, `branch` o `rev`) o `path`; no hay registry central.
- `Tome.lock` registra `source` canónico, `commit` (solo git), `checksum`, `features` y nombres de dependencias.
- Resolución sin SAT ni rangos SemVer de dependencias: un ref/commit por nombre.
- `pengu publish` se retira; `PGS-E1806` pasa a “ref git inválido” y `PGS-E1807` a conflicto de dependencias.
- ADR D37 y changelog `0.6.0` actualizados.

## Limitaciones

No existe todavía un compilador ni un generador Rust para PenguScript. Por eso
no se pudieron compilar los ejemplos normativos: la validación es estructural y
de consistencia editorial. La verificación de tipos, ownership y codegen
requiere implementar el compilador. No se afirma que los 146 bloques compilen.

## Pendiente para la implementación

- Parser real y tests de aceptación de la gramática §19.
- Chequeo de tipos y de ownership.
- Codegen Rust y compilación de los 146 bloques `pengu`.
- Suite de conformidad para `std` y FFI.
