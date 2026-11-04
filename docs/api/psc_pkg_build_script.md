# psc.pkg.build_script

> Source: `src/psc/pkg/build_script.pengu`

psc/pkg/build_script.pengu — build.pengu de dependencias con --trust.

---

### `trusted_by_env`

> **trusted_by_env**() -> bool

 Trust: flag, `PENGU_TRUST_ALL`, o prompt interactivo (no implementado).

### `run`

> **run**(base: string, lib_dir: string, name: string, trusted: bool, force: bool, exe: string) -> bool

 Ejecuta `build.pengu` de una dependencia directa.

 Devuelve true si existía y se ejecutó (aunque fallara).

