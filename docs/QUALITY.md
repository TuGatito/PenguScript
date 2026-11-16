# Calidad: formateo, lints, correcciones, documentación y medidas

`pengu` incluye las herramientas de calidad del lenguaje. Todas funcionan sin
dependencias externas y forman parte del binario.

## Formateo (`pengu fmt`)

```sh
pengu fmt                 # formatea el programa del proyecto
pengu fmt src/a.pengu     # o los archivos indicados
pengu fmt --check         # solo verifica; sale 1 si algo cambiaría
```

El formateador trabaja sobre **tokens**, no sobre el AST: normaliza espacios,
comas, `:`, paréntesis, corchetes, líneas en blanco y sangría, pero **no**
reordena ni reinterpreta el programa. Antes de escribir verifica que la
secuencia de tokens sea idéntica; si no, aborta con `PGS-E1805`. Por eso es
idempotente y nunca cambia la semántica.

Límite conocido: no reescribe líneas que superan las 100 columnas (hacerlo
exigiría un pretty-printer por precedencia). El estilo del lenguaje está en
`docs/LANGUAGE.md` §18.4.

## Lints (`pengu lint`)

```sh
pengu lint                          # avisos del programa del proyecto
pengu lint --deny PGS-W2001         # convierte un aviso en error (sale 1)
pengu lint --allow PGS-W1501        # silencia un lint
pengu lint --list                   # catálogo con códigos y nombres
pengu lint --std std                # archivos de la stdlib (omite W1501)
```

Catálogo actual:

| Código | Nombre | Qué detecta |
| --- | --- | --- |
| `PGS-W1001` | `naming` | funciones de nivel superior que no son `snake_case` |
| `PGS-W1101` | `unused-binding` | `bind`/`morph`/`for` que no se usan |
| `PGS-W1102` | `shadowed-binding` | sombreado de un binding anterior |
| `PGS-W1201` | `redundant-comparison` | `== true`, `!= false`, `== false`, `!= true` |
| `PGS-W1301` | `if-chain` | cadena de `elseif` que debería ser `match` |
| `PGS-W1501` | `panic-in-production` | `panic`/`fail` fuera de `@@test` y de la stdlib |
| `PGS-W2001` | `unused-import` | `summon` cuyo nombre no se usa |
| `PGS-W6001` | `unreachable` | sentencias tras `return`/`break`/`continue` |
| `PGS-W6002` | `constant-loop` | `while true`/`while false` |
| `PGS-W9001` | `duplicate-arm` | patrones `when` repetidos en un `match` |

Los avisos se silencian con `--allow <código|nombre>` y **no** con atributos en
el código. La stdlib se analiza en modo estricto y se mantiene sin avisos
(`la_stdlib_no_tiene_avisos`).

## Correcciones (`pengu fix`)

```sh
pengu fix --dry-run    # muestra los cambios sin escribir
pengu fix              # aplica (y vuelve a formatear)
pengu fix src/a.pengu  # solo esos archivos
```

Solo aplica correcciones **seguras**:

| Aviso | Corrección |
| --- | --- |
| `PGS-W2001` | elimina la línea `summon` del import no usado |
| `PGS-W6001` | elimina la sentencia inalcanzable |
| `PGS-W6002` | `while true do` → `loop` |

El resto se reporta pero no se toca. Con `--dry-run` sale 1 si habría cambios,
igual que `fmt --check`.

## Documentación (`pengu doc`)

```sh
pengu doc            # genera target/pengu/doc/<paquete>.md e imprime la ruta
pengu doc --open     # además la abre con el visor del sistema
```

Documenta cada item con los comentarios `---` que lo preceden y el módulo con
`--!`. El resultado es Markdown con encabezados por firma.

### Doc tests (`pengu test --doc`)

Los bloques ` ```pengu ` dentro de un comentario `---` se convierten en
funciones `@@test` anexadas al programa y se ejecutan en un proyecto temporal
(`target/pengu/doc-tests`), de modo que un ejemplo roto falla el build:

```pengu
--- Suma dos enteros.
--- ```pengu
--- bind total = suma(2, 3)
--- print(total)
--- ```
suma = (a: Int, b: Int) -> Int
    a + b
```

## Medidas (`pengu bench`)

```sh
pengu bench --iterations 5
```

Mide las etapas del compilador (lex, parse, lower, check, LIR y codegen) y el
total, tomando el mínimo de N repeticiones. En release:

```sh
cargo build --release -p pengu-cli
./target/release/pengu bench
```

No mide funciones del programa: el lenguaje no define `@@bench` (§17.4).

## Explicar diagnósticos (`pengu explain`)

```sh
pengu explain PGS-E3001
pengu explain PGS-W1102
```

Lee `docs/LANGUAGE.md` embebido, así que la explicación es siempre la misma que
la especificación publicada.

## Integración continua

`.github/workflows/ci.yml` ejecuta en cada push y pull request:

1. `cargo fmt --all -- --check`
2. `cargo clippy --workspace --all-targets -- -D warnings`
3. `cargo test --workspace`
4. `pengu fmt --check std` y `pengu lint std`

Los cuatro pasos son obligatorios: un aviso de Clippy, un archivo sin formatear
o un test roto bloquean la integración.
