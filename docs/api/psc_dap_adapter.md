# psc.dap.adapter

> Source: `src/psc/dap/adapter.pengu`

psc/dap/adapter.pengu — servidor Debug Adapter Protocol sobre stdio.

Habla DAP (JSON con framing `Content-Length`) por stdin/stdout y GDB/MI por
las tuberías de un proceso `gdb -i=mi2`. El estado del adapter vive en el
hilo principal; dos hilos lectores solo empujan líneas etiquetadas a un
`ChanString`, de modo que no hay carreras sobre el DOM ni sobre los fds.

---

### `starts_with`

> **starts_with**(s: string, p: string) -> bool

_Undocumented._

### `Adapter`

> rune Adapter

```pengu
    q as ChanString
    tr as Transport
    seq as int
    token as int
    gdb_in as int
    gdb_out as int
    gdb_err as int
    gdb_pid as int
    mi_th as Thread
    err_th as Thread
    mi_started as bool
    launched as bool
    running as bool
    terminated as bool
    stop_on_entry as bool
    entry_bp as int
    program as string
    cwd as string
    source as string
    gdb_path as string
    printers as string
    bp_ids as list of int
    bp_sources as list of string
    frame_levels as list of int
    frame_files as list of string
    frame_lines as list of int
    frame_funcs as list of string
    last_file as string
    last_line as int
    step_mode as bool
    step_line as int
    step_tries as int
```

 Estado completo de una sesión de depuración.

### `tagged`

> **tagged**(tag: string, line: string) -> string

 Etiqueta una línea para el hilo principal.

### `err_reader`

> **err_reader**(q: ref to ChanString, fd: int) -> void

 Hilo que drena stderr de gdb para que el pipe no se llene.

### `dap_reader`

> **dap_reader**(q: ref to ChanString) -> void

 Hilo lector de DAP (stdin).

### `mi_reader`

> **mi_reader**(q: ref to ChanString, fd: int) -> void

 Hilo lector de MI (stdout de gdb).

### `jq`

> **jq**(s: string) -> string

 Escapa un string como literal JSON.

 ## Memoria
 Devuelve un string owned.

### `add_field`

> **add_field**(sb: ref to StringBuilder, first: ref to bool, key: string, raw: string) -> void

 Añade `"clave":valor` a un objeto JSON.

 ## Memoria
 `key` y `raw` son borrowed.

### `add_str`

> **add_str**(sb: ref to StringBuilder, first: ref to bool, key: string, val: string) -> void

 Añade un campo string JSON.

### `send_raw`

> **send_raw**(a: ref to Adapter, body: string) -> void

 Envía un frame DAP ya serializado.

### `send_response`

> **send_response**(a: ref to Adapter, req_seq: int, command: string, body: string) -> void

 Envía una respuesta DAP.

### `send_error`

> **send_error**(a: ref to Adapter, req_seq: int, command: string, message: string) -> void

 Envía una respuesta de error DAP.

### `send_event`

> **send_event**(a: ref to Adapter, event: string, body: string) -> void

 Envía un evento DAP.

### `req_args`

> **req_args**(req: JsonValue) -> JsonValue

 ---------------------------------------------------------------------------
 Helpers de requests
 ---------------------------------------------------------------------------

### `req_str`

> **req_str**(obj: JsonValue, key: string) -> string

_Undocumented._

### `req_int`

> **req_int**(obj: JsonValue, key: string, fallback: int) -> int

_Undocumented._

### `req_bool`

> **req_bool**(obj: JsonValue, key: string, fallback: bool) -> bool

_Undocumented._

### `mi_send`

> **mi_send**(a: ref to Adapter, cmd: string) -> int

 Envía un comando MI y devuelve su token (o -1 si falló el write).

### `stream_text`

> **stream_text**(line: string) -> string

 Extrae el texto de un registro `~"..."`, `@"..."` o `&"..."`.

### `handle_mi_async`

> **handle_mi_async**(a: ref to Adapter, line: string) -> void

 Emite los eventos DAP de un registro MI asíncrono.

### `mi_wait`

> **mi_wait**(a: ref to Adapter, token: int) -> string

 Espera la respuesta MI con `token`; procesa eventos mientras tanto.

### `mi_cmd`

> **mi_cmd**(a: ref to Adapter, cmd: string) -> string

 Ejecuta un comando MI y espera su respuesta.

### `do_initialize`

> **do_initialize**(a: ref to Adapter, seq: int) -> void

 ---------------------------------------------------------------------------
 DAP: handlers
 ---------------------------------------------------------------------------

### `do_launch`

> **do_launch**(a: ref to Adapter, seq: int, req: JsonValue) -> void

_Undocumented._

### `do_configuration_done`

> **do_configuration_done**(a: ref to Adapter, seq: int) -> void

_Undocumented._

### `do_set_breakpoints`

> **do_set_breakpoints**(a: ref to Adapter, seq: int, req: JsonValue) -> void

_Undocumented._

### `do_set_exception_breakpoints`

> **do_set_exception_breakpoints**(a: ref to Adapter, seq: int, req: JsonValue) -> void

_Undocumented._

### `mi_escape`

> **mi_escape**(s: string) -> string

 Escapa un string para un comando MI entre comillas.

### `do_continue`

> **do_continue**(a: ref to Adapter, seq: int, cmd: string) -> void

_Undocumented._

### `do_pause`

> **do_pause**(a: ref to Adapter, seq: int) -> void

_Undocumented._

### `do_stack_trace`

> **do_stack_trace**(a: ref to Adapter, seq: int) -> void

_Undocumented._

### `do_scopes`

> **do_scopes**(a: ref to Adapter, seq: int, req: JsonValue) -> void

_Undocumented._

### `is_temp_name`

> **is_temp_name**(name: string) -> bool

_Undocumented._

### `do_variables`

> **do_variables**(a: ref to Adapter, seq: int, req: JsonValue) -> void

_Undocumented._

### `do_evaluate`

> **do_evaluate**(a: ref to Adapter, seq: int, req: JsonValue) -> void

_Undocumented._

### `do_threads`

> **do_threads**(a: ref to Adapter, seq: int) -> void

_Undocumented._

### `do_disconnect`

> **do_disconnect**(a: ref to Adapter, seq: int, cmd: string) -> void

_Undocumented._

### `handle_dap`

> **handle_dap**(a: ref to Adapter, body: string) -> void

 Despacha un request DAP.

### `run_debug_adapter`

> **run_debug_adapter**(args: list of string) -> int

 Bucle principal del adapter.

