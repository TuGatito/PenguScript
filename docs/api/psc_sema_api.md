# psc.sema.api

> Source: `src/psc/sema/api.pengu`

psc/sema/api.pengu — API pública de F3.

`check_file`/`check_text` construyen un `SemaProgram`, descubren imports,
crean scopes por módulo y ejecutan collector + checker. El CLI y los tests
consumen la misma API.

## Memoria
Devuelve un `SemaResult` owned; `free_result` libera todo el programa.

---

### `SemaResult`

> rune SemaResult

```pengu
    ok as bool
    program as ref to SemaProgram
```

 Resultado de una comprobación.

 ## Memoria
 `program` es owned; liberar con `free_result`.

### `free_result`

> **free_result**(r: ref to SemaResult) -> void

 Libera un resultado.

 ## Memoria
 Libera el programa completo.

### `check_file`

> **check_file**(path: string, options: SemaOptions) -> SemaResult

 Comprueba un archivo del disco.

 ## Memoria
 Devuelve un resultado owned.

### `configure_options`

> **configure_options**(path: string, opts: ref to SemaOptions) -> void

 Ajusta `base_dir`/`src_dir`/`lib_dir`/`std_dirs` con el proyecto real.

 La búsqueda de stdlib no depende del `cwd`: cubre una stdlib vendorizada en
 el proyecto, una instalación portable (`bin/psc` + `std/`), una instalación
 FHS (`share/pengu/std`), `PENGU_STD_DIR`/`PSC_STD_DIR` y `PENGU_HOME`.

 ## Memoria
 Reemplaza strings owned de las opciones.

### `configure_manifest`

> **configure_manifest**(opts: ref to SemaOptions) -> void

 Lee `pengu.toml` si existe y aplica `src_dir`/`lib_dir`.

 ## Memoria
 Copia los strings del manifiesto antes de liberarlo.

### `has_string`

> **has_string**(xs: list of string, s: string) -> bool

 `true` si la lista ya contiene `s`.

 ## Memoria
 O(n); no asigna.

### `add_std_dir`

> **add_std_dir**(opts: ref to SemaOptions, path: string) -> void

 Añade un directorio de stdlib si existe y no está repetido.

 ## Memoria
 Hace una copia owned del path.

### `env_text`

> **env_text**(name: string) -> string

 Variable de entorno como string owned (o `""`).

 ## Memoria
 Devuelve owned si existe; `""` es literal prestado.

### `exe_dir`

> **exe_dir**() -> string

 Directorio del ejecutable actual (`""` si no se puede resolver).

 ## Memoria
 Devuelve string owned.

### `configure_std_dirs`

> **configure_std_dirs**(opts: ref to SemaOptions) -> void

 Añade las raíces de stdlib conocidas.

 ## Memoria
 Copia cada path añadido.

### `find_project_root`

> **find_project_root**(abs: string) -> string

 Sube desde el archivo hasta encontrar `pengu.toml`/`pengu.yaml`.

 ## Memoria
 Devuelve el path owned o `""`.

### `check_text`

> **check_text**(path: string, text: string, options: SemaOptions) -> SemaResult

 Comprueba texto en memoria con un path lógico.

 ## Memoria
 Devuelve un resultado owned.

### `check_bodies`

> **check_bodies**(p: ref to SemaProgram) -> void

 Chequea cuerpos después de recolectar todas las firmas.

 ## Memoria
 Abre/cierra scopes; no libera módulos.

### `collect_all`

> **collect_all**(p: ref to SemaProgram) -> void

 Ejecuta collector/checker en orden topológico.

 ## Memoria
 Presta el programa; no libera módulos.

