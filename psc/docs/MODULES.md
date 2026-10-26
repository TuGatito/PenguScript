# Módulos, imports y bindings (F3)

## Resolución

`modules/resolver.pengu` busca, en este orden:

1. `std_dirs` (p. ej. `<proyecto>/std`, `<cwd>/std`);
2. el directorio del módulo importador;
3. `<base>/<src_dir>`;
4. `<base>/<lib_dir>/<primer-componente>/pengu`;
5. `<base>/<nombre>`.

Para cada candidato prueba `.pengu`, `.d.pengu`, `__init__.pengu` y
`__init__.d.pengu`. `std.*` se marca `is_std` para no tratarlo como entrada.

`modules/program.pengu` descubre en DFS, mantiene `by_path`, `order`, detecta
ciclos (`visiting`) y limita la profundidad. El `root` es el módulo de entrada.

## Bindings C companion

Si existe `<modulo>.d.pengu`, se carga junto al módulo. Sus `include`,
`declare`, `link`, `ldflag` y tipos se recolectan en el **scope del módulo
padre**; así el cuerpo puede llamar `utf8len` o usar `re_t` sin importarlos.

Los `declare` no se re-validan por ABI en las llamadas: la firma C es autoridad
y el checker no reinterpreta function pointers ni `void *`. Los tipos de
cabecera desconocidos se representan como `opaque` cuando el proyecto tiene
`include`.

## Exports y visibilidad

Un import crea un símbolo `SkImport` con `module_scope`. El acceso cualificado
`mod.member` busca en ese scope y devuelve el tipo del símbolo. Las funciones y
consts también caen al registro global para respetar stage0 y los helpers de
proyecto.

`sk_import` no copia símbolos: es un alias de scope. Los métodos no se exportan
como miembros; se resuelven por receptor.

## Compilación condicional

`when wasm:` y `when not wasm:` top-level se evalúan con:

- `SemaOptions.wasm_target`;
- defines `-D`;
- `is_main`, `is_debug`, `os`, `arch`.

Sólo se recolecta la rama activa. `when` dentro de cuerpos se infiere como
expresión; `defined`/`when` de constantes se pliega cuando el checker puede.

## API

```pengu
var opts as sopts.SemaOptions is calling sopts.default_options with "."
var r as sema_api.SemaResult is calling sema_api.check_file with path, opts
...
calling sema_api.free_result with (sigil of r)
```

`check_text(path, text, opts)` permite analizar stdin/tests sin archivo.
