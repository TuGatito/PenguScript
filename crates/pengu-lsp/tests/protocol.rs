//! Cliente de protocolo real sobre `UnixStream::pair`.
//!
//! Habla el framing y el JSON-RPC de verdad: no hay atajos ni llamadas internas.

#![allow(
    clippy::missing_panics_doc,
    clippy::cast_possible_truncation,
    clippy::must_use_candidate
)]

use std::io::{BufReader, Write};
use std::os::unix::net::UnixStream;
use std::time::Duration;

use pengu_lsp::framing::{read_message, write_message};
use pengu_lsp::json::{self, Value};
use pengu_lsp::server::{self, Config};

pub struct Client {
    reader: BufReader<UnixStream>,
    writer: UnixStream,
    next_id: i64,
    thread: Option<std::thread::JoinHandle<i32>>,
}

impl Client {
    /// Arranca el servidor en un hilo y devuelve un cliente conectado.
    pub fn start() -> Self {
        let (client, server_stream) = UnixStream::pair().expect("par");
        server_stream
            .set_read_timeout(Some(Duration::from_secs(30)))
            .expect("timeout");
        client
            .set_read_timeout(Some(Duration::from_secs(30)))
            .expect("timeout");
        let reader = BufReader::new(server_stream.try_clone().expect("clon"));
        let writer = server_stream;
        let thread = std::thread::spawn(move || {
            server::Server::new(
                reader,
                writer,
                Config {
                    log_path: None,
                    debounce: Duration::from_millis(10),
                    max_diagnostics: 200,
                },
            )
            .serve()
        });
        Self {
            reader: BufReader::new(client.try_clone().expect("clon")),
            writer: client,
            next_id: 1,
            thread: Some(thread),
        }
    }

    /// Envía un mensaje crudo.
    pub fn send_raw(&mut self, body: &str) {
        write_message(&mut self.writer, body).expect("enviar");
    }

    /// Envía una petición y devuelve su `id`.
    pub fn request(&mut self, method: &str, params: Value) -> i64 {
        let id = self.next_id;
        self.next_id += 1;
        let message = Value::object([
            ("jsonrpc", Value::from("2.0")),
            ("id", Value::Int(id)),
            ("method", Value::from(method)),
            ("params", params),
        ]);
        write_message(&mut self.writer, &json::render(&message)).expect("petición");
        id
    }

    /// Envía una notificación.
    pub fn notify(&mut self, method: &str, params: Value) {
        let message = Value::object([
            ("jsonrpc", Value::from("2.0")),
            ("method", Value::from(method)),
            ("params", params),
        ]);
        write_message(&mut self.writer, &json::render(&message)).expect("notificación");
    }

    /// Lee el siguiente mensaje del servidor.
    pub fn read(&mut self) -> Value {
        let text = read_message(&mut self.reader)
            .expect("leer")
            .expect("mensaje");
        json::parse(&text).expect("json del servidor")
    }

    /// Lee hasta encontrar la respuesta con ese `id`, ignorando notificaciones.
    pub fn read_response(&mut self, id: i64) -> Value {
        loop {
            let message = self.read();
            if message.get("id").and_then(Value::as_i64) == Some(id) {
                return message;
            }
        }
    }

    /// Lee hasta encontrar una notificación de ese método.
    pub fn read_notification(&mut self, method: &str) -> Value {
        loop {
            let message = self.read();
            if message.get("method").and_then(Value::as_str) == Some(method) {
                return message;
            }
        }
    }

    /// Inicializa y devuelve las capacidades.
    pub fn initialize(&mut self) -> Value {
        let id = self.request(
            "initialize",
            json::parse(
                r#"{"processId":null,"rootUri":null,"capabilities":{"general":{"positionEncodings":["utf-16"]}}}"#,
            )
            .expect("json"),
        );
        let response = self.read_response(id);
        self.notify("initialized", Value::object(Vec::<(&str, Value)>::new()));
        response
            .get("result")
            .cloned()
            .expect("resultado de initialize")
    }

    /// Cierra el servidor y devuelve su código de salida.
    pub fn shutdown(mut self) -> i32 {
        let id = self.request("shutdown", Value::Null);
        let response = self.read_response(id);
        assert!(response.get("error").is_none());
        self.notify("exit", Value::Null);
        self.join()
    }

    /// Espera al hilo del servidor.
    pub fn join(&mut self) -> i32 {
        let thread = self.thread.take().expect("hilo");
        thread.join().expect("unir hilo")
    }

    /// Cierra el flujo de escritura y espera.
    pub fn close(mut self) -> i32 {
        let _ = self.writer.shutdown(std::net::Shutdown::Both);
        self.join()
    }

    /// Envía un mensaje sin `jsonrpc` para probar validación.
    pub fn send_invalid(&mut self) {
        self.send_raw("{\"id\":99,\"method\":\"x\"}");
    }

    /// `true` si el flujo sigue abierto (no se puede comprobar directamente).
    pub fn flush(&mut self) {
        let _ = self.writer.flush();
    }
}

#[test]
fn ciclo_de_vida_completo() {
    let mut client = Client::start();
    let result = client.initialize();
    let capabilities = result.get("capabilities").expect("capabilities");
    assert_eq!(
        capabilities.get("positionEncoding").and_then(Value::as_str),
        Some("utf-16")
    );
    assert_eq!(
        capabilities.get("hoverProvider").and_then(Value::as_bool),
        Some(true)
    );
    let info = result.get("serverInfo").expect("serverInfo");
    assert_eq!(info.get("name").and_then(Value::as_str), Some("pengu-lsp"));
    assert_eq!(client.shutdown(), 0);
}

#[test]
fn peticion_antes_de_initialize_es_error() {
    let mut client = Client::start();
    let id = client.request("textDocument/hover", Value::Null);
    let response = client.read_response(id);
    let error = response.get("error").expect("error");
    assert_eq!(error.get("code").and_then(Value::as_i64), Some(-32002));
    assert_eq!(client.shutdown(), 0);
}

#[test]
fn metodo_desconocido_es_method_not_found() {
    let mut client = Client::start();
    client.initialize();
    let id = client.request("textDocument/frobnicate", Value::Null);
    let response = client.read_response(id);
    let error = response.get("error").expect("error");
    assert_eq!(error.get("code").and_then(Value::as_i64), Some(-32601));
    assert_eq!(client.shutdown(), 0);
}

#[test]
fn exit_sin_shutdown_devuelve_uno() {
    let mut client = Client::start();
    client.initialize();
    client.notify("exit", Value::Null);
    assert_eq!(client.join(), 1);
}

#[test]
fn envelope_invalido_no_tumba_el_servidor() {
    let mut client = Client::start();
    client.initialize();
    client.send_invalid();
    // El servidor responde con un error y sigue vivo.
    let message = client.read();
    assert!(message.get("error").is_some());
    assert_eq!(client.shutdown(), 0);
}

#[test]
fn client_disconnect_cierra_el_servidor() {
    let mut client = Client::start();
    client.initialize();
    assert_eq!(client.close(), 0);
}

#[test]
fn publica_diagnosticos_y_los_limpia_al_corregir() {
    let mut client = Client::start();
    client.initialize();
    let uri = "file:///tmp/pengu-lsp-e2e/main.pengu";
    client.notify(
        "textDocument/didOpen",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}","languageId":"pengu","version":1,"text":"f = () -> Int\n    \"texto\"\n"}}}}"#
        ))
        .expect("json"),
    );
    let published = client.read_notification("textDocument/publishDiagnostics");
    let params = published.get("params").expect("params");
    let diagnostics = params
        .get("diagnostics")
        .and_then(Value::as_array)
        .expect("diagnósticos");
    assert_ne!(diagnostics.len(), 0, "{published:?}");
    let first = diagnostics.first().expect("primero");
    assert_eq!(first.get("source").and_then(Value::as_str), Some("pengu"));
    assert_eq!(params.get("version").and_then(Value::as_i64), Some(1));

    let changes = Value::object([(
        "textDocument",
        Value::object([("uri", Value::from(uri)), ("version", Value::Int(2))]),
    )]);
    let mut with_changes = match changes {
        Value::Object(map) => Value::Object(map),
        _ => unreachable!(),
    };
    if let Value::Object(map) = &mut with_changes {
        map.insert(
            "contentChanges".to_owned(),
            Value::Array(vec![Value::object([(
                "text",
                Value::from("f = () -> Int\n    1\n"),
            )])]),
        );
    }
    client.notify("textDocument/didChange", with_changes);
    let published = client.read_notification("textDocument/publishDiagnostics");
    let diagnostics = published
        .get("params")
        .and_then(|params| params.get("diagnostics"))
        .and_then(Value::as_array)
        .expect("diagnósticos");
    assert!(diagnostics.is_empty(), "{published:?}");
    assert_eq!(
        published
            .get("params")
            .and_then(|params| params.get("version"))
            .and_then(Value::as_i64),
        Some(2)
    );
    assert_eq!(client.shutdown(), 0);
}

#[test]
fn aplica_cambios_incrementales_de_rango() {
    let mut client = Client::start();
    client.initialize();
    let uri = "file:///tmp/pengu-lsp-e2e/inc.pengu";
    client.notify(
        "textDocument/didOpen",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}","languageId":"pengu","version":1,"text":"f = () -> Int\n    \"texto\"\n"}}}}"#
        ))
        .expect("json"),
    );
    let published = client.read_notification("textDocument/publishDiagnostics");
    assert_ne!(
        published
            .get("params")
            .and_then(|params| params.get("diagnostics"))
            .and_then(Value::as_array)
            .expect("diagnósticos")
            .len(),
        0
    );
    // Reemplaza solo `"texto"` (línea 1, caracteres 4..11) por `1`.
    let params = json::parse(&format!(
        r#"{{"textDocument":{{"uri":"{uri}","version":2}},"contentChanges":[{{"range":{{"start":{{"line":1,"character":4}},"end":{{"line":1,"character":11}}}},"text":"1"}}]}}"#
    ))
    .expect("json");
    client.notify("textDocument/didChange", params);
    let published = client.read_notification("textDocument/publishDiagnostics");
    assert!(
        published
            .get("params")
            .and_then(|params| params.get("diagnostics"))
            .and_then(Value::as_array)
            .expect("diagnósticos")
            .is_empty(),
        "{published:?}"
    );
    assert_eq!(client.shutdown(), 0);
}

fn open_source(client: &mut Client, uri: &str, text: &str) {
    let params = json::parse(&format!(
        r#"{{"textDocument":{{"uri":"{uri}","languageId":"pengu","version":1,"text":{}}}}}"#,
        json::render(&Value::from(text))
    ))
    .expect("json");
    client.notify("textDocument/didOpen", params);
    client.read_notification("textDocument/publishDiagnostics");
}

#[test]
fn hover_completion_definition_y_simbolos() {
    let mut client = Client::start();
    client.initialize();
    let uri = "file:///tmp/pengu-lsp-l3/main.pengu";
    open_source(
        &mut client,
        uri,
        "suma = (a: Int, b: Int) -> Int\n    a + b\n\ngrimoire\n    print(suma(1, 2))\n",
    );

    let id = client.request(
        "textDocument/hover",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"position":{{"line":4,"character":11}}}}"#
        ))
        .expect("json"),
    );
    let hover = client.read_response(id);
    let value = hover
        .get("result")
        .and_then(|result| result.get("contents"))
        .and_then(|contents| contents.get("value"))
        .and_then(Value::as_str)
        .expect("hover");
    assert!(value.contains("suma"), "{value}");

    let id = client.request(
        "textDocument/definition",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"position":{{"line":4,"character":11}}}}"#
        ))
        .expect("json"),
    );
    let definition = client.read_response(id);
    let location = definition.get("result").expect("resultado");
    assert_eq!(location.get("uri").and_then(Value::as_str), Some(uri));
    let start = location
        .get("range")
        .and_then(|range| range.get("start"))
        .and_then(|start| start.get("line"))
        .and_then(Value::as_i64);
    assert_eq!(start, Some(0));

    let id = client.request(
        "textDocument/completion",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"position":{{"line":4,"character":15}}}}"#
        ))
        .expect("json"),
    );
    let completion = client.read_response(id);
    let items = completion
        .get("result")
        .and_then(|result| result.get("items"))
        .and_then(Value::as_array)
        .expect("items");
    assert!(
        items
            .iter()
            .any(|item| item.get("label").and_then(Value::as_str) == Some("suma"))
    );

    let id = client.request(
        "textDocument/documentSymbol",
        json::parse(&format!(r#"{{"textDocument":{{"uri":"{uri}"}}}}"#)).expect("json"),
    );
    let symbols = client.read_response(id);
    let items = symbols
        .get("result")
        .and_then(Value::as_array)
        .expect("símbolos");
    assert!(
        items
            .iter()
            .any(|item| item.get("name").and_then(Value::as_str) == Some("suma"))
    );
    assert_eq!(client.shutdown(), 0);
}

#[test]
fn hover_muestra_tamanos_reales() {
    let mut client = Client::start();
    client.initialize();
    let uri = "file:///tmp/pengu-lsp-sizes/main.pengu";
    open_source(
        &mut client,
        uri,
        "rune Point\n    x: Int\n    y: Int\n\nrune Holder[T]\n    first: T\n    second: U8\n\nbox_point = (point: Point) -> Holder[Point]\n    Holder(first: point, second: 0 as U8)\n\ngrimoire\n    print(box_point(Point(x: 1, y: 2)))\n",
    );

    let hover_at = |client: &mut Client, line: i64, character: i64| -> String {
        let id = client.request(
            "textDocument/hover",
            json::parse(&format!(
                r#"{{"textDocument":{{"uri":"{uri}"}},"position":{{"line":{line},"character":{character}}}}}"#
            ))
            .expect("json"),
        );
        let response = client.read_response(id);
        response
            .get("result")
            .and_then(|result| result.get("contents"))
            .and_then(|contents| contents.get("value"))
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_owned()
    };

    // El `rune Point` mide 8 B y alinea a 4.
    let point = hover_at(&mut client, 0, 6);
    assert!(point.contains("tamaño 8 B"), "{point}");
    assert!(point.contains("alineación 4 B"), "{point}");

    // `box_point` es una función: se muestra su huella.
    let function = hover_at(&mut client, 8, 2);
    assert!(function.contains("huella"), "{function}");
}

#[test]
fn referencias_resaltado_y_rename() {
    let mut client = Client::start();
    client.initialize();
    let uri = "file:///tmp/pengu-lsp-refs/main.pengu";
    open_source(
        &mut client,
        uri,
        "saluda = (nombre: &Str) -> Str\n    nombre\n\ngrimoire\n    bind nombre = \"pengu\"\n    print(saluda(nombre))\n",
    );

    let id = client.request(
        "textDocument/references",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"position":{{"line":0,"character":2}},"context":{{"includeDeclaration":true}}}}"#
        ))
        .expect("json"),
    );
    let response = client.read_response(id);
    let locations = response
        .get("result")
        .and_then(Value::as_array)
        .expect("referencias");
    // Declaración y la llamada del `grimoire`.
    assert_eq!(locations.len(), 2, "{locations:?}");

    let id = client.request(
        "textDocument/prepareRename",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"position":{{"line":0,"character":2}}}}"#
        ))
        .expect("json"),
    );
    let prepared = client.read_response(id);
    let placeholder = prepared
        .get("result")
        .and_then(|result| result.get("placeholder"))
        .and_then(Value::as_str);
    assert_eq!(placeholder, Some("saluda"));

    let id = client.request(
        "textDocument/rename",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"position":{{"line":0,"character":2}},"newName":"saludar"}}"#
        ))
        .expect("json"),
    );
    let renamed = client.read_response(id);
    let edits = renamed
        .get("result")
        .and_then(|result| result.get("changes"))
        .and_then(|changes| changes.get(uri))
        .and_then(Value::as_array)
        .expect("ediciones");
    assert_eq!(edits.len(), 2, "{edits:?}");
    assert!(
        edits
            .iter()
            .all(|edit| edit.get("newText").and_then(Value::as_str) == Some("saludar"))
    );

    let id = client.request(
        "textDocument/documentHighlight",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"position":{{"line":5,"character":12}}}}"#
        ))
        .expect("json"),
    );
    let response = client.read_response(id);
    let highlights = response
        .get("result")
        .and_then(Value::as_array)
        .expect("resaltados");
    assert_eq!(highlights.len(), 2);
}

#[test]
fn tokens_semanticos_y_hints_de_tipo() {
    let mut client = Client::start();
    client.initialize();
    let uri = "file:///tmp/pengu-lsp-sem/main.pengu";
    open_source(
        &mut client,
        uri,
        "rune Point\n    x: Int\n\nsuma = (a: Int, b: Int) -> Int\n    a + b\n\ngrimoire\n    bind total: Int = suma(1, 2)\n    morph cuenta = total\n    print(cuenta)\n",
    );

    let id = client.request(
        "textDocument/semanticTokens/full",
        json::parse(&format!(r#"{{"textDocument":{{"uri":"{uri}"}}}}"#)).expect("json"),
    );
    let response = client.read_response(id);
    let data = response
        .get("result")
        .and_then(|result| result.get("data"))
        .and_then(Value::as_array)
        .expect("tokens");
    assert_ne!(data.len(), 0);
    assert_eq!(data.len() % 5, 0, "los tokens van en grupos de cinco");

    let id = client.request(
        "textDocument/semanticTokens/range",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"range":{{"start":{{"line":4,"character":0}},"end":{{"line":5,"character":0}}}}}}"#
        ))
        .expect("json"),
    );
    let response = client.read_response(id);
    let ranged = response
        .get("result")
        .and_then(|result| result.get("data"))
        .and_then(Value::as_array)
        .expect("tokens del rango");
    assert!(
        ranged.len() < data.len(),
        "el rango debe producir menos tokens"
    );

    let id = client.request(
        "textDocument/inlayHint",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"range":{{"start":{{"line":0,"character":0}},"end":{{"line":12,"character":0}}}}}}"#
        ))
        .expect("json"),
    );
    let response = client.read_response(id);
    let hints = response
        .get("result")
        .and_then(Value::as_array)
        .expect("hints");
    let labels = hints
        .iter()
        .filter_map(|hint| hint.get("label").and_then(Value::as_str))
        .collect::<Vec<_>>();
    // `a`, `b` (parámetros) y `cuenta`; `total` no porque ya lleva anotación.
    assert_eq!(labels.len(), 3, "{labels:?}");
    assert!(
        labels.iter().all(|label| label.starts_with(": Int")),
        "{labels:?}"
    );
}

#[test]
fn firma_plegado_seleccion_lentes_y_simbolos() {
    let mut client = Client::start();
    client.initialize();
    let uri = "file:///tmp/pengu-lsp-extras/main.pengu";
    open_source(
        &mut client,
        uri,
        "suma = (a: Int, b: Int) -> Int\n    a + b\n\n@@test\ncomprueba = () -> Unit\n    assert_eq(suma(1, 2), 3)\n\ngrimoire\n    if suma(1, 2) > 2 then\n        print(suma(1, 2))\n",
    );

    let id = client.request(
        "textDocument/signatureHelp",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"position":{{"line":9,"character":19}}}}"#
        ))
        .expect("json"),
    );
    let response = client.read_response(id);
    let label = response
        .get("result")
        .and_then(|result| result.get("signatures"))
        .and_then(Value::as_array)
        .and_then(|signatures| signatures.first().cloned())
        .and_then(|signature| {
            signature
                .get("label")
                .and_then(Value::as_str)
                .map(str::to_owned)
        });
    assert_eq!(label.as_deref(), Some("fn suma(Int, Int) -> Int"));

    let id = client.request(
        "textDocument/foldingRange",
        json::parse(&format!(r#"{{"textDocument":{{"uri":"{uri}"}}}}"#)).expect("json"),
    );
    let response = client.read_response(id);
    let ranges = response
        .get("result")
        .and_then(Value::as_array)
        .expect("plegados");
    assert_ne!(ranges.len(), 0);

    let id = client.request(
        "textDocument/codeLens",
        json::parse(&format!(r#"{{"textDocument":{{"uri":"{uri}"}}}}"#)).expect("json"),
    );
    let response = client.read_response(id);
    let lenses = response
        .get("result")
        .and_then(Value::as_array)
        .expect("lentes");
    let titles = lenses
        .iter()
        .filter_map(|lens| lens.get("command")?.get("title")?.as_str())
        .collect::<Vec<_>>();
    assert!(titles.contains(&"ejecutar test"), "{lenses:?}");
    assert!(titles.contains(&"▶ Ejecutar programa"), "{lenses:?}");

    let id = client.request(
        "textDocument/selectionRange",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"positions":[{{"line":9,"character":8}}]}}"#
        ))
        .expect("json"),
    );
    let response = client.read_response(id);
    let selection = response
        .get("result")
        .and_then(Value::as_array)
        .and_then(|ranges| ranges.first().cloned())
        .expect("selección");
    assert!(selection.get("parent").is_some(), "{selection:?}");

    let id = client.request(
        "workspace/symbol",
        json::parse(r#"{"query":"suma"}"#).expect("json"),
    );
    let response = client.read_response(id);
    let symbols = response
        .get("result")
        .and_then(Value::as_array)
        .expect("símbolos");
    assert!(
        symbols
            .iter()
            .any(|symbol| symbol.get("name").and_then(Value::as_str) == Some("suma"))
    );
}

#[test]
fn tipo_implementaciones_acciones_y_jerarquia() {
    let mut client = Client::start();
    client.initialize();
    let uri = "file:///tmp/pengu-lsp-adv/main.pengu";
    open_source(
        &mut client,
        uri,
        "pact Saluda\n    hola = (@) -> Int\n\nrune Punto\n    x: Int\n\nritual Punto for Saluda\n    hola = (@) -> Int\n        7\n\nusa = (punto: Punto) -> Int\n    punto.hola()\n\naux = () -> Int\n    usa(Punto(x: 1))\n\ngrimoire\n    print(aux())\n",
    );

    let id = client.request(
        "callHierarchy/prepare",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"position":{{"line":14,"character":6}}}}"#
        ))
        .expect("json"),
    );
    let response = client.read_response(id);
    let items = response
        .get("result")
        .and_then(Value::as_array)
        .expect("elementos");
    assert_eq!(items.len(), 1, "{items:?}");
    assert_eq!(items[0].get("name").and_then(Value::as_str), Some("usa"));

    let id = client.request(
        "callHierarchy/incomingCalls",
        json::parse(&format!(
            r#"{{"item":{{"name":"usa","kind":12,"uri":"{uri}","range":{{"start":{{"line":10,"character":0}},"end":{{"line":10,"character":3}}}},"selectionRange":{{"start":{{"line":10,"character":0}},"end":{{"line":10,"character":3}}}}}}}}"#
        ))
        .expect("json"),
    );
    let response = client.read_response(id);
    let calls = response
        .get("result")
        .and_then(Value::as_array)
        .expect("llamadas");
    assert!(
        !calls.is_empty(),
        "se esperaba al menos una llamada entrante"
    );

    let id = client.request(
        "textDocument/codeAction",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"range":{{"start":{{"line":3,"character":0}},"end":{{"line":3,"character":0}}}},"context":{{"diagnostics":[{{"code":"PGS-E1104","message":"el campo `x` es privado","range":{{"start":{{"line":4,"character":4}},"end":{{"line":4,"character":5}}}}}}]}}}}"#
        ))
        .expect("json"),
    );
    let response = client.read_response(id);
    let actions = response
        .get("result")
        .and_then(Value::as_array)
        .expect("acciones");
    assert_eq!(actions.len(), 1, "{actions:?}");
    assert_eq!(
        actions[0].get("title").and_then(Value::as_str),
        Some("Añadir `unveil` al campo")
    );
}

#[test]
fn formatting_devuelve_edicion_solo_si_cambia() {
    let mut client = Client::start();
    client.initialize();
    let uri = "file:///tmp/pengu-lsp-l4/fmt.pengu";
    open_source(&mut client, uri, "f = () -> Int\n    1   \n");
    let id = client.request(
        "textDocument/formatting",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"options":{{"tabSize":4,"insertSpaces":true}}}}"#
        ))
        .expect("json"),
    );
    let response = client.read_response(id);
    let edits = response
        .get("result")
        .and_then(Value::as_array)
        .expect("ediciones");
    assert_eq!(edits.len(), 1);
    let text = edits[0]
        .get("newText")
        .and_then(Value::as_str)
        .expect("texto");
    assert_eq!(text, "f = () -> Int\n    1\n");
    assert_eq!(client.shutdown(), 0);
}

#[test]
fn cancelar_una_peticion_pendiente_devuelve_error() {
    let mut client = Client::start();
    client.initialize();
    // Cancelar antes de que el servidor procese la petición: el cliente envía
    // el id cancelado y después la petición, así que se responde con -32800.
    client.notify(
        "$/cancelRequest",
        json::parse(r#"{"id":42}"#).expect("json"),
    );
    let params = json::parse("{}").expect("json");
    let message = Value::object([
        ("jsonrpc", Value::from("2.0")),
        ("id", Value::Int(42)),
        ("method", Value::from("workspace/symbol")),
        ("params", params),
    ]);
    write_message(&mut client.writer, &json::render(&message)).expect("petición");
    let response = client.read_response(42);
    assert_eq!(
        response
            .get("error")
            .and_then(|error| error.get("code"))
            .and_then(Value::as_i64),
        Some(-32800)
    );
    assert_eq!(client.shutdown(), 0);
}

#[test]
fn completion_de_modulos_y_lente_de_ejecucion() {
    let mut client = Client::start();
    client.initialize();
    let uri = "file:///tmp/pengu-lsp-e6/main.pengu";
    open_source(
        &mut client,
        uri,
        "summon std::libra\n\nvalor = () -> Int\n    1\n\ngrimoire\n    print(valor())\n",
    );

    let id = client.request(
        "textDocument/completion",
        json::parse(&format!(
            r#"{{"textDocument":{{"uri":"{uri}"}},"position":{{"line":0,"character":17}}}}"#
        ))
        .expect("json"),
    );
    let completion = client.read_response(id);
    let items = completion
        .get("result")
        .and_then(|result| result.get("items"))
        .and_then(Value::as_array)
        .expect("items");
    assert!(
        items
            .iter()
            .any(|item| item.get("label").and_then(Value::as_str) == Some("libra")),
        "{completion:?}"
    );

    let id = client.request(
        "textDocument/codeLens",
        json::parse(&format!(r#"{{"textDocument":{{"uri":"{uri}"}}}}"#)).expect("json"),
    );
    let lens = client.read_response(id);
    let lenses = lens
        .get("result")
        .and_then(Value::as_array)
        .expect("lentes");
    let run = lenses
        .iter()
        .find(|item| {
            item.get("command")
                .and_then(|command| command.get("title"))
                .and_then(Value::as_str)
                == Some("▶ Ejecutar programa")
        })
        .expect("lente de ejecución");
    assert_eq!(
        run.get("range")
            .and_then(|range| range.get("start"))
            .and_then(|start| start.get("line"))
            .and_then(Value::as_i64),
        Some(5)
    );

    client.shutdown();
}
