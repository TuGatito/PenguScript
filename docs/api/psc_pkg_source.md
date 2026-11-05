# psc.pkg.source

> Source: `src/psc/pkg/source.pengu`

psc/pkg/source.pengu — fuentes local/git.

Git se ejecuta con argv (nunca shell) para no inyectar opciones ni comandos.

---

### `copy`

> **copy**(s: string) -> string

_Undocumented._

### `is_git`

> **is_git**(s: string) -> bool

 ¿Es una URL git?

### `contains`

> **contains**(s: string, p: string) -> bool

 `true` si `s` contiene `p` (subcadena literal, sin regex).

### `is_ignored_rel`

> **is_ignored_rel**(rel: string) -> bool

 `true` si la ruta relativa cae dentro de un artefacto generado o de un
 repositorio (`.git`, `lib`, `build`).

 Copiar esos directorios al instalar una dependencia `path` provoca
 recursión (el `lib/` de un ejemplo contiene otra copia del paquete) y
 llena el disco; además nunca son parte del código de la dependencia.

### `copy_local`

> **copy_local**(src: string, dst: string) -> bool

 Copia un árbol local a `dst` (elimina dst antes).

### `clone_git`

> **clone_git**(src: string, dst: string, ref: string) -> bool

 Clona un repo git y hace checkout de `ref` (tag/branch) si no está vacío.

### `commit`

> **commit**(path: string) -> string

 `git -C path rev-parse HEAD`; `""` si falla.

### `tags`

> **tags**(src: string) -> list of string

 Tags git (`git ls-remote --tags URL`), sin `^{}`.

### `starts_with`

> **starts_with**(s: string, p: string) -> bool

 `true` si `s` empieza por `p`.

### `ends_with`

> **ends_with**(s: string, p: string) -> bool

 `true` si `s` termina en `p`.

