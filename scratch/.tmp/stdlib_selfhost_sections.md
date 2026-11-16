<a id="libra"></a>
## 24. `libra` — TOML

**Archivo:** `std/libra.pengu`
**Alias de spec:** `std.toml`
**Implementación:** parser y emisor en PenguScript puro; sin dependencias externas.

```pengu
enchanting TomlValue {
    String(String)
    Integer(Int)
    Float(Float)
    Boolean(Bool)
    Temporal(TomlTemporal)
    Array(Vec[TomlValue])
    Table(TomlTable)
}

enchanting TomlTemporal {
    Date(TomlDate)
    Time(TomlTime)
    Datetime(TomlDatetime)
}

rune TomlDate {
    year: U16
    month: U8
    day: U8
}

rune TomlTime {
    hour: U8
    minute: U8
    second: U8
    nanosecond: U32
}

rune TomlDatetime {
    date: TomlDate
    time: TomlTime
    offset_minutes: Option[Int]
}

rune TomlTable {
    entries: Map[String, TomlValue]
}

rune TomlError {
    message: String
    line: U32
    column: U32
}
```

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `parse` | `(text: &Str) -> Result[TomlTable, TomlError]` | Parsea un documento TOML 1.0. | ✅ |
| `parse_value` | `(text: &Str) -> Result[TomlValue, TomlError]` | Parsea un valor TOML suelto. | |
| `stringify` | `(table: &TomlTable) -> String` | Emite TOML canónico. | ✅ |
| `stringify_value` | `(value: &TomlValue) -> String` | Emite un valor. | |
| `TomlTable.new` | `() -> TomlTable` | Tabla vacía. | ✅ |
| `TomlTable.get` | `(@, key: &Str) -> Option[&TomlValue]` | Busca una clave. | ✅ |
| `TomlTable.get_string` | `(@, key: &Str) -> Option[&Str]` | Atajo para string. | |
| `TomlTable.get_int` | `(@, key: &Str) -> Option[Int]` | Atajo para entero. | |
| `TomlTable.get_float` | `(@, key: &Str) -> Option[Float]` | Atajo para float. | |
| `TomlTable.get_bool` | `(@, key: &Str) -> Option[Bool]` | Atajo para bool. | |
| `TomlTable.get_array` | `(@, key: &Str) -> Option[&Vec[TomlValue]]` | Atajo para array. | |
| `TomlTable.get_table` | `(@, key: &Str) -> Option[&TomlTable]` | Atajo para tabla. | |
| `TomlTable.insert` | `(@mut, key: &Str, value: TomlValue)` | Inserta o reemplaza. | |
| `TomlTable.remove` | `(@mut, key: &Str) -> Option[TomlValue]` | Elimina y devuelve. | |
| `TomlTable.contains` | `(@, key: &Str) -> Bool` | ¿Existe la clave? | |
| `TomlTable.keys` | `(@) -> Vec[String]` | Claves en orden de inserción. | |
| `TomlTable.len` | `(@) -> Usize` | Número de claves. | |
| `TomlTable.is_empty` | `(@) -> Bool` | ¿Vacía? | |
| `TomlTable.to_string` | `(@) -> String` | Emite TOML. | |
| `TomlValue.kind` | `(@) -> TomlKind` | Tipo del valor. | |
| `TomlValue.as_string` | `(@) -> Option[&Str]` | Vista string. | |
| `TomlValue.as_int` | `(@) -> Option[Int]` | Vista entero. | |
| `TomlValue.as_float` | `(@) -> Option[Float]` | Vista float. | |
| `TomlValue.as_bool` | `(@) -> Option[Bool]` | Vista bool. | |
| `TomlValue.as_array` | `(@) -> Option[&Vec[TomlValue]]` | Vista array. | |
| `TomlValue.as_table` | `(@) -> Option[&TomlTable]` | Vista tabla. | |
| `TomlValue.to_string` | `(@) -> String` | Emite el valor. | |
| `TomlTemporal.to_string` | `(@) -> String` | Fecha/hora en formato TOML. | |
| `TomlDate.new` | `(year: U16, month: U8, day: U8) -> TomlDate` | Construye fecha. | |
| `TomlTime.new` | `(hour: U8, minute: U8, second: U8, nanosecond: U32) -> TomlTime` | Construye hora. | |
| `TomlDatetime.new` | `(date: TomlDate, time: TomlTime, offset_minutes: Option[Int]) -> TomlDatetime` | Construye datetime. | |

`TomlKind` es `enchanting TomlKind { String, Integer, Float, Boolean, Temporal, Array, Table }`.

---

<a id="iason"></a>
## 25. `iason` — JSON

**Archivo:** `std/iason.pengu`
**Alias de spec:** `std.json`
**Implementación:** parser y emisor en PenguScript puro.

```pengu
enchanting JsonValue {
    Null
    Bool(Bool)
    Int(Int)
    Float(Float)
    String(String)
    Array(Vec[JsonValue])
    Object(JsonObject)
}

rune JsonObject {
    entries: Map[String, JsonValue]
}

rune JsonError {
    message: String
    line: U32
    column: U32
}
```

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `parse` | `(text: &Str) -> Result[JsonValue, JsonError]` | Parsea JSON (RFC 8259). | ✅ |
| `parse_object` | `(text: &Str) -> Result[JsonObject, JsonError]` | Exige objeto raíz. | |
| `stringify` | `(value: &JsonValue) -> String` | Emite JSON compacto. | ✅ |
| `stringify_pretty` | `(value: &JsonValue, indent: U8) -> String` | Emite con indentación. | |
| `JsonValue.kind` | `(@) -> JsonKind` | Tipo JSON. | |
| `JsonValue.is_null` | `(@) -> Bool` | ¿Null? | |
| `JsonValue.as_bool` | `(@) -> Option[Bool]` | Vista bool. | |
| `JsonValue.as_int` | `(@) -> Option[Int]` | Vista entero. | |
| `JsonValue.as_float` | `(@) -> Option[Float]` | Vista float. | |
| `JsonValue.as_string` | `(@) -> Option[&Str]` | Vista string. | |
| `JsonValue.as_array` | `(@) -> Option[&Vec[JsonValue]]` | Vista array. | |
| `JsonValue.as_object` | `(@) -> Option[&JsonObject]` | Vista objeto. | |
| `JsonValue.to_string` | `(@) -> String` | JSON compacto. | |
| `JsonObject.new` | `() -> JsonObject` | Objeto vacío. | ✅ |
| `JsonObject.get` | `(@, key: &Str) -> Option[&JsonValue]` | Busca clave. | ✅ |
| `JsonObject.get_string` | `(@, key: &Str) -> Option[&Str]` | Atajo string. | |
| `JsonObject.get_int` | `(@, key: &Str) -> Option[Int]` | Atajo entero. | |
| `JsonObject.get_bool` | `(@, key: &Str) -> Option[Bool]` | Atajo bool. | |
| `JsonObject.get_object` | `(@, key: &Str) -> Option[&JsonObject]` | Atajo objeto. | |
| `JsonObject.get_array` | `(@, key: &Str) -> Option[&Vec[JsonValue]]` | Atajo array. | |
| `JsonObject.insert` | `(@mut, key: &Str, value: JsonValue)` | Inserta o reemplaza. | |
| `JsonObject.remove` | `(@mut, key: &Str) -> Option[JsonValue]` | Elimina. | |
| `JsonObject.contains` | `(@, key: &Str) -> Bool` | ¿Existe? | |
| `JsonObject.keys` | `(@) -> Vec[String]` | Claves. | |
| `JsonObject.len` | `(@) -> Usize` | Número de claves. | |
| `JsonObject.is_empty` | `(@) -> Bool` | ¿Vacío? | |
| `JsonObject.to_string` | `(@) -> String` | JSON compacto. | |

`JsonKind` es `enchanting JsonKind { Null, Bool, Int, Float, String, Array, Object }`. Los enteros que no caben en `Int` producen `JsonError`; no se convierten silenciosamente a `Float`.

---

<a id="digestum"></a>
## 26. `digestum` — Hash y checksums

**Archivo:** `std/digestum.pengu`
**Alias de spec:** `std.digest`
**Implementación:** SHA-256/SHA-512 en PenguScript puro; sin crates.

```pengu
rune Sha256 { /* estado interno */ }
rune Sha512 { /* estado interno */ }

rune DigestError {
    message: String
}
```

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `sha256` | `(data: &[U8]) -> [U8; 32]` | SHA-256 de un buffer. | ✅ |
| `sha256_hex` | `(data: &[U8]) -> String` | SHA-256 en hex minúsculas. | ✅ |
| `sha512` | `(data: &[U8]) -> [U8; 64]` | SHA-512. | |
| `sha512_hex` | `(data: &[U8]) -> String` | SHA-512 hex. | |
| `Sha256.new` | `() -> Sha256` | Estado inicial. | ✅ |
| `Sha256.update` | `(@mut, data: &[U8])` | Añade bytes. | ✅ |
| `Sha256.finalize` | `(@own) -> [U8; 32]` | Cierra y devuelve hash. | ✅ |
| `Sha256.finalize_hex` | `(@own) -> String` | Cierra y devuelve hex. | |
| `Sha512.new` | `() -> Sha512` | Estado inicial. | |
| `Sha512.update` | `(@mut, data: &[U8])` | Añade bytes. | |
| `Sha512.finalize` | `(@own) -> [U8; 64]` | Cierra. | |
| `Sha512.finalize_hex` | `(@own) -> String` | Cierra hex. | |
| `hmac_sha256` | `(key: &[U8], data: &[U8]) -> [U8; 32]` | HMAC-SHA-256. | |
| `hmac_sha256_hex` | `(key: &[U8], data: &[U8]) -> String` | HMAC hex. | |
| `hex_encode` | `(bytes: &[U8]) -> String` | Bytes a hex. | ✅ |
| `hex_decode` | `(text: &Str) -> Result[Vec[U8], DigestError]` | Hex a bytes. | ✅ |
| `constant_time_eq` | `(a: &[U8], b: &[U8]) -> Bool` | Comparación en tiempo constante. | |

Los checksums de `Tome.lock` usan `sha256_hex`; no se acepta otro algoritmo en 0.6.0.

---

<a id="versio"></a>
## 27. `versio` — SemVer

**Archivo:** `std/versio.pengu`
**Alias de spec:** `std.semver`
**Implementación:** parser y comparador en PenguScript puro.

```pengu
rune Version {
    major: U64
    minor: U64
    patch: U64
    pre: Vec[String]
    build: Vec[String]
}

rune Comparator {
    op: ComparatorOp
    version: Version
}

enchanting ComparatorOp { Exact, Greater, GreaterEq, Less, LessEq, Tilde, Caret, Wildcard }

rune VersionReq {
    comparators: Vec[Comparator]
}

rune SemverError {
    message: String
}
```

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `Version.parse` | `(text: &Str) -> Result[Version, SemverError]` | Parsea `1.2.3-pre+build`. | ✅ |
| `Version.to_string` | `(@) -> String` | Serializa. | ✅ |
| `Version.compare` | `(@, other: &Version) -> Ordering` | Precedencia SemVer. | ✅ |
| `Version.is_prerelease` | `(@) -> Bool` | ¿Tiene pre-release? | |
| `Version.same_major` | `(@, other: &Version) -> Bool` | Mismo major. | |
| `Version.same_minor` | `(@, other: &Version) -> Bool` | Mismo major/minor. | |
| `VersionReq.parse` | `(text: &Str) -> Result[VersionReq, SemverError]` | Parsea `^1.2`, `~1.2.3`, `>=1, <2`. | ✅ |
| `VersionReq.matches` | `(@, version: &Version) -> Bool` | ¿Satisface? | ✅ |
| `VersionReq.to_string` | `(@) -> String` | Serializa. | |
| `Comparator.matches` | `(@, version: &Version) -> Bool` | Compara un comparador. | |
| `Comparator.to_string` | `(@) -> String` | Serializa. | |
| `Ordering` | `enchanting Ordering { Less, Equal, Greater }` | Resultado de comparación. | ✅ |

`Version.compare` implementa la precedencia de SemVer 2.0.0: `pre` se compara identificador por identificador; `build` se ignora. `VersionReq` es para versiones de paquetes y `pengu outdated`; las dependencias de `Tome.toml` siguen fijadas por git/commit.

---

<a id="terminus"></a>
## 28. `terminus` — Terminal

**Archivo:** `std/terminus.pengu`
**Alias de spec:** `std.term`
**Implementación:** ANSI + `foreign` de plataforma; sin hilos.

```pengu
rune TermSize {
    cols: U16
    rows: U16
}

enchanting StdStream { Stdin, Stdout, Stderr }

enchanting Color {
    Black
    Red
    Green
    Yellow
    Blue
    Magenta
    Cyan
    White
    BrightBlack
    BrightRed
    BrightGreen
    BrightYellow
    BrightBlue
    BrightMagenta
    BrightCyan
    BrightWhite
    Rgb(U8, U8, U8)
    Ansi256(U8)
}

rune Style {
    fg: Option[Color]
    bg: Option[Color]
    bold: Bool
    dim: Bool
    italic: Bool
    underline: Bool
    reverse: Bool
}

enchanting Key {
    Char(Char)
    Enter
    Escape
    Backspace
    Tab
    BackTab
    Up
    Down
    Left
    Right
    Home
    End
    PageUp
    PageDown
    Insert
    Delete
    Function(U8)
    Unknown(Vec[U8])
}

rune RawMode { /* estado */ }
```

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `is_tty` | `(stream: StdStream) -> Bool` | ¿Es terminal? | ✅ |
| `size` | `() -> Result[TermSize, IoError]` | Columnas y filas. | ✅ |
| `color_enabled` | `() -> Bool` | Respeta `NO_COLOR` y `TERM`. | |
| `enable_raw_mode` | `() -> Result[RawMode, IoError]` | Modo raw; `Drop` restaura. | ✅ |
| `RawMode.disable` | `(@own)` | Restaura el terminal. | ✅ |
| `read_key` | `() -> Result[Key, IoError]` | Lee una tecla. | ✅ |
| `read_key_timeout` | `(milliseconds: U64) -> Result[Option[Key], IoError]` | Lee con timeout. | |
| `clear` | `() -> Result[(), IoError]` | Limpia pantalla. | |
| `clear_line` | `() -> Result[(), IoError]` | Limpia línea. | |
| `move_to` | `(row: U16, column: U16) -> Result[(), IoError]` | Mueve cursor. | |
| `hide_cursor` | `() -> Result[(), IoError]` | Oculta cursor. | |
| `show_cursor` | `() -> Result[(), IoError]` | Muestra cursor. | |
| `flush` | `() -> Result[(), IoError]` | Vacía stdout. | |
| `paint` | `(text: &Str, style: &Style) -> String` | Aplica estilo ANSI. | |
| `Style.new` | `() -> Style` | Estilo vacío. | |
| `Style.fg` | `(@mut, color: Color) -> &mut Style` | Color de texto. | |
| `Style.bg` | `(@mut, color: Color) -> &mut Style` | Color de fondo. | |
| `Style.bold` | `(@mut) -> &mut Style` | Negrita. | |
| `Style.dim` | `(@mut) -> &mut Style` | Atenuado. | |
| `Style.italic` | `(@mut) -> &mut Style` | Itálica. | |
| `Style.underline` | `(@mut) -> &mut Style` | Subrayado. | |
| `Style.reverse` | `(@mut) -> &mut Style` | Invertido. | |
| `Style.reset` | `(@mut)` | Quita estilos. | |
| `Style.to_string` | `(@) -> String` | Secuencia ANSI. | |

`read_key` bloquea; para UI con timeout se usa `read_key_timeout`. En Windows se usa la consola nativa; en Unix, `termios`. No hay threads ni event loop en 0.6.0.

---

<a id="globus"></a>
## 29. `globus` — Glob

**Archivo:** `std/globus.pengu`
**Alias de spec:** `std.glob`
**Implementación:** parser de patrones en PenguScript puro; recorre con `via.walk`.

```pengu
rune GlobOptions {
    case_sensitive: Bool
    follow_links: Bool
    include_hidden: Bool
    max_depth: Option[U32]
}

enchanting GlobError {
    InvalidPattern(String)
    Io(IoError)
}
```

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `glob` | `(pattern: &Str) -> Result[Vec[PathBuf], GlobError]` | Busca desde el directorio actual. | ✅ |
| `glob_in` | `(base: &Path, pattern: &Str) -> Result[Vec[PathBuf], GlobError]` | Busca desde `base`. | ✅ |
| `matches` | `(pattern: &Str, path: &Path) -> Bool` | ¿La ruta casa? | |
| `escape` | `(literal: &Str) -> String` | Escapa metacaracteres. | |
| `GlobOptions.new` | `() -> GlobOptions` | Opciones por defecto. | |
| `GlobOptions.case_sensitive` | `(@mut, enabled: Bool) -> &mut GlobOptions` | Sensible a mayúsculas. | |
| `GlobOptions.follow_links` | `(@mut, enabled: Bool) -> &mut GlobOptions` | Sigue symlinks. | |
| `GlobOptions.include_hidden` | `(@mut, enabled: Bool) -> &mut GlobOptions` | Incluye ocultos. | |
| `GlobOptions.max_depth` | `(@mut, depth: U32) -> &mut GlobOptions` | Profundidad máxima. | |

Sintaxis: `*`, `?`, `**`, `[abc]`, `[!abc]`, `{a,b}`. Los resultados se ordenan por ruta. No se usa regex.

---

<a id="archivum"></a>
## 30. `archivum` — Archivos tar/zip

**Archivo:** `std/archivum.pengu`
**Alias de spec:** `std.archive`
**Implementación:** tar y zip en PenguScript; gzip mediante `foreign` de plataforma.

```pengu
enchanting ArchiveFormat { Tar, TarGz, Zip }

rune ArchiveEntry {
    path: PathBuf
    size: U64
    compressed_size: Option[U64]
    is_dir: Bool
    mode: U32
}

rune ExtractOptions {
    overwrite: Bool
    preserve_permissions: Bool
    strip_components: U16
}

rune ArchiveWriter { /* estado */ }

enchanting ArchiveError {
    Io(IoError)
    Format(String)
    Unsupported(String)
}
```

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `list` | `(path: &Path, format: ArchiveFormat) -> Result[Vec[ArchiveEntry], ArchiveError]` | Lista entradas. | ✅ |
| `extract` | `(path: &Path, dest: &Path, format: ArchiveFormat, options: ExtractOptions) -> Result[(), ArchiveError]` | Extrae. | ✅ |
| `create` | `(path: &Path, format: ArchiveFormat) -> Result[ArchiveWriter, ArchiveError]` | Crea archivo. | ✅ |
| `ArchiveFormat.parse` | `(text: &Str) -> Result[ArchiveFormat, ArchiveError]` | `tar`, `tar.gz`, `zip`. | |
| `ArchiveFormat.from_path` | `(path: &Path) -> Result[ArchiveFormat, ArchiveError]` | Por extensión. | |
| `ArchiveEntry.to_string` | `(@) -> String` | Representación legible. | |
| `ExtractOptions.new` | `() -> ExtractOptions` | Opciones seguras. | |
| `ExtractOptions.overwrite` | `(@mut, enabled: Bool) -> &mut ExtractOptions` | Sobrescribe. | |
| `ExtractOptions.preserve_permissions` | `(@mut, enabled: Bool) -> &mut ExtractOptions` | Conserva modo. | |
| `ExtractOptions.strip_components` | `(@mut, count: U16) -> &mut ExtractOptions` | Quita prefijos. | |
| `ArchiveWriter.add_file` | `(@mut, path: &Path, name: &Str) -> Result[(), ArchiveError]` | Añade archivo. | ✅ |
| `ArchiveWriter.add_bytes` | `(@mut, name: &Str, data: &[U8]) -> Result[(), ArchiveError]` | Añade bytes. | ✅ |
| `ArchiveWriter.add_dir` | `(@mut, name: &Str) -> Result[(), ArchiveError]` | Añade directorio. | |
| `ArchiveWriter.finish` | `(@own) -> Result[(), ArchiveError]` | Cierra. | ✅ |

`extract` rechaza rutas absolutas y `..` (`ArchiveError.Format`). `strip_components` se aplica después de validar. No se soportan enlaces simbólicos en 0.6.0.

---

<a id="rete"></a>
## 31. `rete` — Red, TLS y HTTP

**Archivo:** `std/rete.pengu`
**Alias de spec:** `std.net`, `std.tls`, `std.http`
**Implementación:** sockets con `foreign` de plataforma; TLS con el backend del sistema; HTTP/1.1 en PenguScript puro.

```pengu
enchanting IpAddr {
    V4([U8; 4])
    V6([U8; 16])
}

rune SocketAddr {
    ip: IpAddr
    port: U16
}

rune TcpListener { /* handle */ }
rune TcpStream { /* handle */ }
rune UdpSocket { /* handle */ }

rune TlsConfig {
    verify: Bool
    ca_file: Option[PathBuf]
    alpn: Vec[String]
}

rune TlsStream { /* handle */ }

enchanting HttpMethod { Get, Post, Put, Delete, Head, Patch }

rune HttpRequest {
    method: HttpMethod
    url: String
    headers: Map[String, String]
    body: Vec[U8]
}

rune HttpResponse {
    status: U16
    headers: Map[String, String]
    body: Vec[U8]
}

rune HttpClient { /* configuración */ }

enchanting NetError {
    Io(IoError)
    Dns(String)
    Tls(String)
    Http(String)
    InvalidUrl(String)
}
```

| Método | Firma | Descripción | CORE |
|---|---|---|---|
| `SocketAddr.parse` | `(text: &Str) -> Result[SocketAddr, NetError]` | `ip:puerto` o `[v6]:puerto`. | ✅ |
| `SocketAddr.to_string` | `(@) -> String` | Serializa. | |
| `lookup_host` | `(host: &Str, port: U16) -> Result[Vec[SocketAddr], NetError]` | DNS. | ✅ |
| `TcpListener.bind` | `(addr: &SocketAddr) -> Result[TcpListener, NetError]` | Escucha. | ✅ |
| `TcpListener.local_addr` | `(@) -> Result[SocketAddr, NetError]` | Dirección local. | |
| `TcpListener.accept` | `(@) -> Result[(TcpStream, SocketAddr), NetError]` | Acepta conexión. | ✅ |
| `TcpListener.set_nonblocking` | `(@mut, enabled: Bool) -> Result[(), NetError]` | No bloqueante. | |
| `TcpListener.ttl` | `(@mut, ttl: U32) -> Result[(), NetError]` | TTL. | |
| `TcpStream.connect` | `(addr: &SocketAddr) -> Result[TcpStream, NetError]` | Conecta. | ✅ |
| `TcpStream.connect_timeout` | `(addr: &SocketAddr, timeout: Duration) -> Result[TcpStream, NetError]` | Con timeout. | |
| `TcpStream.peer_addr` | `(@) -> Result[SocketAddr, NetError]` | Par. | |
| `TcpStream.local_addr` | `(@) -> Result[SocketAddr, NetError]` | Local. | |
| `TcpStream.read` | `(@mut, buf: &mut [U8]) -> Result[Usize, NetError]` | Lee. | ✅ |
| `TcpStream.write` | `(@mut, buf: &[U8]) -> Result[Usize, NetError]` | Escribe. | ✅ |
| `TcpStream.read_to_end` | `(@mut, buf: &mut Vec[U8]) -> Result[Usize, NetError]` | Lee hasta EOF. | |
| `TcpStream.write_all` | `(@mut, buf: &[U8]) -> Result[(), NetError]` | Escribe todo. | |
| `TcpStream.set_read_timeout` | `(@mut, timeout: Option[Duration]) -> Result[(), NetError]` | Timeout lectura. | |
| `TcpStream.set_write_timeout` | `(@mut, timeout: Option[Duration]) -> Result[(), NetError]` | Timeout escritura. | |
| `TcpStream.shutdown` | `(@mut, how: Shutdown) -> Result[(), NetError]` | Cierra. | |
| `TcpStream.try_clone` | `(@) -> Result[TcpStream, NetError]` | Duplica. | |
| `UdpSocket.bind` | `(addr: &SocketAddr) -> Result[UdpSocket, NetError]` | Abre UDP. | |
| `UdpSocket.local_addr` | `(@) -> Result[SocketAddr, NetError]` | Local. | |
| `UdpSocket.send_to` | `(@mut, data: &[U8], addr: &SocketAddr) -> Result[Usize, NetError]` | Envía. | |
| `UdpSocket.recv_from` | `(@mut, buf: &mut [U8]) -> Result[(Usize, SocketAddr), NetError]` | Recibe. | |
| `UdpSocket.set_broadcast` | `(@mut, enabled: Bool) -> Result[(), NetError]` | Broadcast. | |
| `TlsConfig.new` | `() -> TlsConfig` | Verifica por defecto. | ✅ |
| `TlsConfig.verify` | `(@mut, enabled: Bool) -> &mut TlsConfig` | Verificación. | |
| `TlsConfig.ca_file` | `(@mut, path: &Path) -> &mut TlsConfig` | CA extra. | |
| `TlsConfig.alpn` | `(@mut, protocols: &[&Str]) -> &mut TlsConfig` | ALPN. | |
| `TlsStream.connect` | `(host: &Str, port: U16, config: &TlsConfig) -> Result[TlsStream, NetError]` | TLS cliente. | ✅ |
| `TlsStream.read` | `(@mut, buf: &mut [U8]) -> Result[Usize, NetError]` | Lee. | ✅ |
| `TlsStream.write` | `(@mut, buf: &[U8]) -> Result[Usize, NetError]` | Escribe. | ✅ |
| `TlsStream.peer_certificate` | `(@) -> Option[Vec[U8]]` | Certificado DER. | |
| `TlsStream.shutdown` | `(@mut) -> Result[(), NetError]` | Cierra. | |
| `HttpRequest.new` | `(method: HttpMethod, url: &Str) -> HttpRequest` | Construye. | ✅ |
| `HttpRequest.header` | `(@mut, key: &Str, value: &Str) -> &mut HttpRequest` | Cabecera. | |
| `HttpRequest.body` | `(@mut, body: &[U8]) -> &mut HttpRequest` | Cuerpo. | |
| `HttpClient.new` | `() -> HttpClient` | Cliente. | ✅ |
| `HttpClient.timeout` | `(@mut, timeout: Duration) -> &mut HttpClient` | Timeout global. | |
| `HttpClient.get` | `(@mut, url: &Str) -> Result[HttpResponse, NetError]` | GET. | ✅ |
| `HttpClient.post` | `(@mut, url: &Str, body: &[U8]) -> Result[HttpResponse, NetError]` | POST. | |
| `HttpClient.request` | `(@mut, request: &HttpRequest) -> Result[HttpResponse, NetError]` | Petición arbitraria. | |
| `HttpResponse.header` | `(@, key: &Str) -> Option[&Str]` | Cabecera. | |
| `HttpResponse.text` | `(@) -> Result[String, NetError]` | Cuerpo UTF-8. | |
| `Shutdown` | `enchanting Shutdown { Read, Write, Both }` | Modo de cierre. | |

HTTP/1.1 solamente; no HTTP/2, chunked se soporta al leer, redirects no automáticos. TLS usa OpenSSL/SChannel/Security.framework vía `foreign`; el usuario no ve punteros. `HttpClient` es bloqueante y no usa hilos.

---

## 32. Notas de implementación
