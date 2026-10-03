## 3. Lista priorizada (detalle en `PRODUCTION_READINESS.md` §9.3)

**CRÍTICO**

1. **`modulo.CONSTANTE` genera C inválido** — `raylib.FLAG_MSAA_4X_HINT` → `raylib_FLAG_MSAA_4X_HINT` (undefined); `raylib.KEY_RIGHT`, `raylib.SHADER_UNIFORM_FLOAT` igual. El `check` pasa y el build falla. Funcionan la forma sin cualificar (`KEY_RIGHT`) y la anidada (`raylib.KeyboardKey.KEY_RIGHT`); las constantes de struct (`raylib.RAYWHITE`) no se ven afectadas. Es la grafía natural siguiendo el estilo `raylib.InitWindow` y toca justo lo que un juego necesita (flags, uniform types, enums). _(Este lo encontró la batería de build+run; mis sondas anteriores eran solo `check`.)_
2. **`{…}` en un string normal (¡shaders!) exige raw string y el error no lo dice**: `"#version 330\nvoid main() { … }"` → `E0000` genérico y mal ubicado; la solución es `r"""…"""`.
3. **`restrict` en todo parámetro `ref to T`**: UB con APIs que solapan buffers, sin diagnóstico ni opt-out.

**ALTO** 4. **`pengu bind` no emite los `typedef` primitivos de headers compañeros** (`uLong`/`uInt`/`Bytef`/`voidpf`/`z_size_t` en zlib): el binding se genera pero sus APIs dan `E0005` hasta que añades los `alias` a mano (con ellos compila y ejecuta). 5. **Divergencias `check` vs codegen aún vivas**: `printf` desnudo (solo `include`), array literal como argumento (`take({1,2,3})`), `declare … many T`. Ahora al menos señalan tu línea `.pengu`.

**MEDIO**: sin aritmética de punteros (`p + 1`), sin bounds checking, sin `pass` para bloques vacíos, headers vendor (`miniaudio`, `xxhash`, `tomlc17`, `yaml`) que aún necesitan flags.

**OPCIONAL**: flags `-I/-L/-l` en la CLI, binario por entry (hoy `build/app.exe` compartido), closures con captura, formateo numérico integrado (`{x:08}`), benchmarks públicos, `pengu test --json`/watch, CI multiplataforma para el camino GL/raylib, y guías de "portar un ejemplo de C" y de shaders/assets.

## 4. Estado verificado

- **Suite: 804 passed, 1 skipped**; ports raylib 01–06 compilan (04–06 ejecutan); **51 módulos de `std/`** limpios juntos; `regen_std_bindings --check` en 13 idénticos + 12 artesanales/saltados a propósito.
- Batería de readiness completa (A–G) en verde, con la excepción de los huecos documentados.

Si quieres, el siguiente paso natural es que arregle **C1** (resolver el nombre C real para constantes/variantes de bindings importados, con un test que compile las tres grafías), que es el que más bloquea el uso serio de raylib; y de paso C2 (diagnóstico de interpolación + raw strings) y H1 (typedefs que faltan en `pengu bind`).
