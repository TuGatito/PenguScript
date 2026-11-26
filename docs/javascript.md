# Backend JavaScript (`--target js`)

PenguScript compila a C++20 por defecto. Con `--target js` el mismo programa se
emite como **módulos ES2022** (`.mjs`) que se pueden importar desde cualquier
proyecto de Bun, Node.js o el navegador:

```bash
pengu build --target js examples/01_hello/main.pengu
pengu run --target js examples/01_hello/main.pengu
pengu build --target js --out dist examples/01_hello/main.pengu
```

La salida es un `.mjs` por `realm`, un `pengu_rt.mjs` con el runtime mínimo y un
`index.mjs` que arranca el programa. Solo se emiten los símbolos alcanzables
desde `main`, así que el resultado se lee como código escrito a mano.

## Forma del código emitido

- Un `rune` sin comportamiento (sin `constructor`, `destructor`, `heir` ni
  `enchanting`) es una **fábrica de objetos planos**:

  ```js
  export function Punto(x, y) {
    return { x, y };
  }
  ```

  Es estructuralmente una `interface` y se serializa directo con
  `JSON.stringify`.

- Un `rune` con comportamiento es una **clase ES2022** con `extends`, `super`,
  `this` y `_clone()` para las copias por valor.
- `omen` unitarias y `flags` son objetos congelados de enteros (`Color.Red`);
  las algebraicas son `{ tag, _0, … }` creadas por funciones congeladas.
- `seal` y `echo` desaparecen en runtime (cuestan cero).
- Las funciones de `enchanting` son funciones libres con *name mangling*
  (`string__to_upper`, `abs__int8_t`), nunca parches de `prototype`.
- Un `rune` con `destructor` emite `_destroy()` y **los bloques que declaran
  locales de ese tipo se envuelven en `try/finally`**, así que el destructor
  corre al salir del ámbito, en cada iteración de un bucle y también al volver
  antes de tiempo:

  ```js
  export function main() {
    let c;
    try {
      c = new Caja("uno");
      println("dentro");
    } finally {
      c?._destroy();
    }
  }
  ```

  Limitación conocida: un **temporal** con destructor que no se guarda en una
  variable no se destruye (C++ sí lo haría al final de la expresión).

## Semántica que se conserva

- **Valor vs. referencia**: asignar un `rune` o un contenedor sin `ref<T>`
  copia (`rt.clone`), igual que el backend C++.
- **Enteros**: `int64_t` y `uint64_t` usan `BigInt` (con `--int64 number` para
  IEEE 754, más rápido y con pérdida por encima de 2⁵³); la división entera es
  `Math.trunc(a / b)`.
- **Formato de dobles**: `echo`/`println` de un `double` reproduce el `%g` de
  C++ (6 cifras significativas), no el `Number#toString` de JavaScript.
- **`match` exhaustivo**: un `match` sin variante que coincida termina con
  `rt.panic("match sin variante")`, como el `::pengu::panic` de C++.
- **`async`/`await`**: `future<T>` se emite como `Promise<T>`; las IIFEs que
  contienen un `await` se vuelven `await (async () => { … })()`.

## Diferencias conocidas frente a C++20

| Tema | C++20 | JavaScript |
|------|-------|------------|
| `#texto` | bytes UTF-8 | unidades UTF-16 |
| Iteración de `map`/`set` | ordenada | orden de inserción |
| `int64_t` | exacto | `BigInt` (o `number` con `--int64 number`) |
| `os::arch()` | `x86_64`, `aarch64` | se traduce desde Node |
| `random` | `std::mt19937_64` | xorshift128+ |
| `async`/`await` | E0804 (no soportado) | `Promise` |
| `size`, `bindgen`, FFI, `thread`, `meld` | sí | no (solo `--target cpp`) |

Las diferencias están cubiertas por `tests/e2e/js_parity.test.ts` y
`tests/e2e/js_std_parity.test.ts`, que compilan el mismo fuente con los dos
backends y comparan la salida byte a byte.

## Rendimiento

`scripts/bench_backends.sh` compila el mismo bucle aritmético de 10⁶
iteraciones con los dos backends y mide el mínimo de cinco ejecuciones
(incluye el arranque del proceso):

| Backend | Tiempo |
|---------|--------|
| C++20 (`-O1`) | ≈3 ms |
| JavaScript en Bun | ≈36 ms |

Es decir, **≈12× más lento** en un bucle numérico apretado; el arranque de Bun
es de ≈3 ms, así que casi todo el tiempo es el bucle. Es el precio de la
aritmética dinámica: el backend JavaScript prioriza legibilidad y corrección
semántica sobre velocidad en bucles calientes. Para código intensivo en
cómputo, `--target cpp`.

## Navegador: `std/js/*`

Los módulos `std/js/*` describen objetos que solo existen en un host
JavaScript (DOM, Canvas, `localStorage`, `fetch`…). Se declaran con `host` y
solo compilan con `--target js`; usar cualquiera de ellos con `--target cpp`
informa **E0518** antes de generar código.

```pengu
invoke "std/js/types"
invoke "std/js/dom"
invoke "std/js/canvas"
invoke "std/js/console"

main = ->
  document.title = "Hola, DOM"
  mut lienzo = document.createElement("canvas") as js::HTMLCanvasElement
  lienzo.width = 320
  mut ctx = lienzo.getContext("2d")
  ctx.fillStyle = "rojo"
  ctx.fillRect(0.0, 0.0, 10.0, 10.0)
  console.log(lienzo.width)
```

Se emite exactamente lo que se escribe (`new Point(...)`, `document.title = …`,
`Math.max(...)`): los objetos del host nunca se clonan ni se cajan en `any`.
`js::String`, `js::Number` y `js::Boolean` son `echo` sobre `string`, `double` y
`bool`, así que los literales nativos pasan sin conversión; `js_array_from` y
`js_to_vector` copian explícitamente en la frontera para no compartir la
posesión. Los `future<T>` de `std/js/fetch` y compañía se esperan con `await`.

Catálogo actual: `types`, `number`, `string`, `boolean`, `array`, `object`,
`map`, `set`, `promise`, `console`, `timers`, `events`, `dom`, `canvas`,
`fetch`, `storage` y `performance`. El catálogo se escribe a mano en esta fase;
`pengu ts-bindgen` lo regenerará desde los `.d.ts` del navegador.

## Opciones

| Opción | Efecto |
|--------|--------|
| `--target cpp\|js` | backend (por defecto `cpp`) |
| `--out <ruta>` | directorio de salida de los `.mjs` |
| `--int64 bigint\|number` | representación de los enteros de 64 bits |
| `--jsdoc` | añade `@param`/`@returns` a las funciones emitidas |
| `--release` | modo de optimización del backend C++ |

Con `--target js`, `pengu size` y `pengu bindgen` responden con un error claro:
dependen del modelo de memoria de C++.
