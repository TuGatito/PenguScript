---

<a id="sec-18"></a>
## 18. Herramientas y tomes

### 18.1 CLI

```text
pengu new <name>
pengu init
pengu build [--release]
pengu run [-- args...]
pengu check
pengu test [--doc] [--coverage]
pengu fmt [--check]
pengu lint
pengu doc [--open]
pengu clean
pengu add <dep>
pengu remove <dep>
pengu update
pengu publish
pengu lsp
pengu explain <code>
pengu metadata
```

No hay `bench`, `fuzz`, `audit` ni `deny` en el núcleo. Se instalan como
herramientas externas.

### 18.2 `Tome.toml`

```toml
[tome]
name = "hello"
version = "0.1.0"
pengu = "0.5"
edition = "2024"

[dependencies]
text = "1.2"

[features]
default = []
json = []

[[bin]]
name = "hello"
path = "main.pengu"

[[lib]]
name = "hello"
path = "lib.pengu"

[[test]]
name = "integration"
path = "tests/integration.pengu"
```

Reglas:

- `name`, `version`, `pengu` y `edition` son obligatorios.
- `pengu` declara la versión mínima del compilador.
- Las dependencias usan SemVer.
- `features` son aditivas.
- No hay `[cargo]`, `[profile]`, `[tool.*]` ni scripts de build.

### 18.3 Lockfile

`Tome.lock` registra las versiones exactas de las dependencias. Se genera con
`pengu build` y se versiona en la aplicación. `pengu update` lo actualiza.

### 18.4 Formatter

`pengu fmt` aplica:

- cuatro espacios por nivel;
- un espacio después de `:` en tipos;
- sin espacios dentro de `[]` y `()`;
- una coma por elemento, con coma final permitida;
- líneas de hasta 100 columnas.

No hay configuración por proyecto en v1. Las diferencias se reportan con
`pengu fmt --check`.

### 18.5 Linter

`pengu lint` detecta:

- bindings no usados;
- imports no usados;
- `unwrap`/`expect` en producción;
- comparaciones redundantes;
- `if` que puede ser `match`;
- código inalcanzable;
- nombres que no siguen la convención.

Los warnings se pueden silenciar con `pengu lint --allow <code>`; no hay
atributos de lint en el código.

### 18.6 LSP

`pengu lsp` ofrece:

- diagnóstico al guardar;
- autocompletado de nombres y campos;
- ir a definición;
- buscar referencias;
- renombrar;
- formato.

No hay refactors avanzados ni generación de código.

### 18.7 Reproducibilidad

Un build es reproducible si:

- `Tome.lock` está presente;
- la versión de `pengu` coincide con `pengu` del manifiesto;
- no se usan rutas absolutas;
- no se lee el entorno durante la compilación.

El backend puede producir artefactos idénticos con `--remap-path-prefix`.

### 18.8 Publicación

`pengu publish` empaqueta:

- `Tome.toml` y `Tome.lock`;
- fuentes `.pengu`;
- `README.md`, `LICENSE` y `CHANGELOG.md` si existen.

No se publican artefactos del backend ni archivos generados.

### 18.9 Diagnósticos de tooling

| Código | Situación |
|---|---|
| `PGS-E1810` | `Tome.toml` inválido. |
| `PGS-E1802` | Versión de `pengu` incompatible. |
| `PGS-E1803` | Dependencia no encontrada. |
| `PGS-E1804` | Lockfile desactualizado. |
| `PGS-E1805` | `pengu fmt` no puede formatear. |
| `PGS-E1806` | `pengu publish` sin licencia. |

[↑ Volver al índice](#indice)
