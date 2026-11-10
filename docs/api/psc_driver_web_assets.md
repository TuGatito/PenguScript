# psc.driver.web_assets

> Source: `src/psc/driver/web_assets.pengu`

psc/driver/web_assets.pengu — copia e inyección de artefactos web.

Lee `[web]` de `pengu.toml`, copia scripts y assets al directorio del
artefacto y añade `<script src="...">` antes de `</head>`.

## Memoria
Todas las funciones liberan lo que crean salvo el `result` devuelto, que el
llamador consume.

---

### `configured`

> **configured**(man: ref to Manifest) -> bool

 `true` si hay algo configurado en `[web]`.

 ## Memoria
 O(1).

### `safe_src`

> **safe_src**(name: string) -> result of string to string

 Convierte un nombre de archivo en un `src` seguro para atributo HTML.

 Solo se permiten letras, dígitos, `.`, `_`, `-` y `/`; el resto se rechaza
 para no inyectar markup.

 ## Memoria
 Devuelve string owned.

### `copy_asset`

> **copy_asset**(src: string, outdir: string) -> result of bool to string

 Copia un asset (archivo o directorio) al directorio de salida.

 ## Memoria
 No retiene handles.

### `copy_script`

> **copy_script**(src: string, outdir: string) -> result of string to string

 Copia un script al directorio de salida y devuelve su nombre base.

 ## Memoria
 El nombre devuelto es owned.

### `inject_scripts`

> **inject_scripts**(html: string, tags: string) -> result of string to string

 Inyecta los tags de scripts en el HTML.

 ## Memoria
 Devuelve el HTML owned; libera el original.

### `apply_web`

> **apply_web**(man: ref to Manifest, artifact: string) -> result of bool to string

 Aplica `[web]` al artefacto.

 ## Retorno
 `ok=true` si no había configuración o si todo se copió e inyectó.

 ## Errores
 Path inválido, script/asset ausente, fallo de copia o HTML sin `</head>`
 (en ese caso se inyecta al principio, que también carga antes del loader).

 ## Memoria
 Consume el resultado el llamador.

