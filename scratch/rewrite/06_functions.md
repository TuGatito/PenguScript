---

<a id="sec-07"></a>
## 7. Funciones y closures

### 7.1 Función nombrada

```pengu
add = (a: Int, b: Int) -> Int
    a + b
```

Una función nombrada:

- es un item, no un binding;
- puede estar en el nivel de módulo;
- no captura variables;
- tiene tipo de retorno explícito;
- devuelve la última expresión.

No hay `spell`, `fn`, `def` ni `function`.

### 7.2 Llamada

```pengu
bind total = add(2, 3)
bind inc = add(1, _)
```

No hay aplicación parcial en el núcleo: `_` no es un placeholder. La segunda
línea es un error.

### 7.3 Retorno

```pengu
absolute = (n: Int) -> Int
    if n < 0 then
        return -n
    n
```

`return` sale inmediatamente. La última expresión también es el valor de
retorno; no hace falta escribir `return` al final.

### 7.4 Parámetros

```pengu
repeat = (text: &Str, times: Int) -> String
    bind out = String.new()
    for _ in 0..times do
        out.push_str(text)
    out
```

- Los parámetros se separan con comas.
- Cada parámetro tiene nombre y tipo.
- No hay parámetros opcionales, valores por defecto, varargs ni sobrecarga.
- No hay `morph` en parámetros: un parámetro es inmutable. Para mutar una copia,
  se crea un `morph` local.

### 7.5 Funciones que no retornan

```pengu
fail = (message: &Str) -> Never
    panic(message)
```

`Never` se usa para funciones que siempre fallan o divergen.

### 7.6 Closures

```pengu
bind inc = (x: Int) => x + 1

bind add = (a: Int, b: Int) =>
    a + b
```

Una closure:

- usa `=>`;
- puede capturar variables del scope;
- infiere el tipo de retorno;
- no puede usar `return`;
- se guarda en un `bind`/`morph` o se pasa como argumento.

La captura es por referencia cuando es posible y por movimiento cuando la
closure escapa o cuando el valor no se puede prestar. No se escribe `move` ni
`ref`; el compilador decide.

### 7.7 Tipo de función

```pengu
bind op: (Int, Int) -> Int = add
bind make = (n: Int) -> (Int) -> Int
    (x: Int) => x + n
```

El tipo `(A, B) -> C` describe una función o closure. No hay `Fn`, `FnMut` ni
`FnOnce` en la superficie.

### 7.8 Pasar funciones

```pengu
apply = (f: (Int) -> Int, value: Int) -> Int
    f(value)

bind doubled = apply((x: Int) => x * 2, 21)
```

No hay closures genéricas ni polimorfismo de rango superior. Si una función
necesita un tipo distinto, se usa un genérico en la función contenedora.

### 7.9 `grimoire`

`grimoire` no es una función normal: no recibe parámetros y no se llama desde
PenguScript. Se define en §3.

### 7.10 Diagnósticos de funciones

| Código | Situación |
|---|---|
| `PGS-E7001` | Falta el tipo de retorno. |
| `PGS-E7002` | Retorno incompatible con la firma. |
| `PGS-E7003` | Parámetro sin tipo. |
| `PGS-E7004` | `return` en una closure. |
| `PGS-E7005` | Llamada con número de argumentos incorrecto. |
| `PGS-E7006` | Tipo de argumento incorrecto. |
| `PGS-E7007` | Función usada como valor sin tipo. |
| `PGS-E7008` | `Never` en una posición que requiere valor. |

[↑ Volver al índice](#indice)
