# psc.pkg.build_script

> Source: `src/psc/pkg/build_script.pengu`

psc/pkg/build_script.pengu — build.pengu de dependencias con --trust.

---

### `trusted_by_env`

> **trusted_by_env**() -> bool

 Trust: flag, `PENGU_TRUST_ALL`, o prompt interactivo (no implementado).

### `exists`

> **exists**(base: string, lib_dir: string, name: string) -> bool

 `true` si la dependencia declara `build.pengu`.

### `run`

> **run**(base: string, lib_dir: string, name: string, trusted: bool, force: bool, exe: string) -> bool

 Ejecuta `build.pengu` de una dependencia.

 Devuelve true sólo si el script existía, se ejecutó y terminó con código 0.

