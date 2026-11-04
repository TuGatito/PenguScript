# psc.codegen.bundle

> Source: `src/psc/codegen/bundle.pengu`

psc/codegen/bundle.pengu — ensamblado de `bundle.c`.

CP0: cabecera, prototipos, definiciones y wrapper de entry. Las secciones de
tipos, tests, line markers y DCE se añaden por subfases.

---

### `is_libc_name`

> **is_libc_name**(c: ref to CgContext, f: CgFunction) -> bool

 ¿El `declare` corresponde a una función de la libc ya declarada por el runtime?

 ## Memoria
 O(1) por nombre.

### `finish_checked`

> **finish_checked**(e: ref to CgEmitter) -> string

 Verifica que el C generado no contenga bytes NUL (corrupción de heap).

 ## Memoria
 Consume el emisor; devuelve el string owned del llamador.

### `generate_bundle_c`

> **generate_bundle_c**(c: ref to CgContext, live_out: ref to list of int) -> string

 Emite el bundle completo.

 ## Memoria
 Devuelve string owned; el contexto conserva sus tablas.

