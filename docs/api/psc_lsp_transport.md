# psc.lsp.transport

> Source: `src/psc/lsp/transport.pengu`

psc/lsp/transport.pengu — framing LSP sobre stdio o TCP.

---

### `Transport`

> rune Transport

```pengu
    tcp as bool
    sock as Socket
```

 Transporte activo.

### `stdio`

> **stdio**() -> Transport

 Crea un transporte stdio.

### `tcp_with`

> **tcp_with**(sock: Socket) -> Transport

 Crea un transporte TCP.

### `copy`

> **copy**(s: string) -> string

 Copia owned.

### `read_exact`

> **read_exact**(t: ref to Transport, n: int) -> maybe string

 Lee exactamente `n` bytes.

### `read_line`

> **read_line**(t: ref to Transport) -> maybe string

 Lee una línea (sin `\r\n`).

### `read_frame`

> **read_frame**(t: ref to Transport) -> maybe string

 Lee un frame LSP completo (body).

 Devuelve `none` en EOF; body owned.

### `write_frame`

> **write_frame**(t: ref to Transport, body: string) -> bool

 Envía un body con framing y flush.

### `close`

> **close**(t: ref to Transport) -> void

 Cierra el socket TCP.

### `starts_with`

> **starts_with**(s: string, p: string) -> bool

 `true` si `s` empieza por `p`.

### `ends_with`

> **ends_with**(s: string, p: string) -> bool

 `true` si `s` termina en `p`.

