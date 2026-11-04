# psc.span

> Source: `src/psc/span.pengu`

psc/span.pengu — rangos de bytes half-open.

Un `ByteSpan` es el tipo mínimo que comparten tokens, literales y
diagnósticos: `[start, end)` medido en bytes sobre `SourceFile.text`.
No tiene heap y se copia por valor.

## Ejemplo
```pengu
var s as ByteSpan is with start is 3, end is 8
calling spark.println_int with (calling span_len with s)   # 5
```

## Memoria
Todos los helpers devuelven valores puros; ninguno asigna ni libera.

---

### `ByteSpan`

> rune ByteSpan

```pengu
    start as int
    end as int
```

 Un rango de bytes half-open `[start, end)`.

 ## Memoria
 Valor puro: no tiene heap.

### `span_len`

> **span_len**(s: ByteSpan) -> int

 Longitud en bytes del rango.

 ## Retorno
 `end - start`; puede ser `0`.

 ## Memoria
 O(1), no asigna.

### `span_is_empty`

> **span_is_empty**(s: ByteSpan) -> bool

 `true` cuando el rango no cubre ningún byte.

 ## Memoria
 O(1), no asigna.

### `span_contains`

> **span_contains**(s: ByteSpan, offset: int) -> bool

 `true` cuando `offset` cae en `[start, end)`.

 ## Memoria
 O(1), no asigna.

### `ps_span_merge`

> **ps_span_merge**(a: ByteSpan, b: ByteSpan) -> ByteSpan

 Une dos rangos en el menor rango que contiene a ambos.

 ## Memoria
 O(1), no asigna.

### `span_clamp`

> **span_clamp**(s: ByteSpan, limit: int) -> ByteSpan

 Normaliza un rango: clampa a `[0, limit]` y lo ordena.

 Un span construido por un token de recuperación puede venir invertido o
 fuera de rango; este helper garantiza que `SourceFile.span_at` y
 `std.diagnostic.span_from_positions` nunca reciban posiciones inválidas.

 ## Parámetros
 - `s`: rango de entrada.
 - `limit`: longitud máxima permitida (normalmente `SourceFile.byte_len`).

 ## Retorno
 Un rango con `0 <= start <= end <= limit`.

 ## Memoria
 O(1), no asigna.

