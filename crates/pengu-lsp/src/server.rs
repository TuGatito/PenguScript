//! Bucle del servidor LSP: canal del lector, despacho y ciclo de vida.

use std::io::{BufRead, Write};
use std::path::PathBuf;
use std::sync::mpsc::{self, RecvTimeoutError};
use std::time::Duration;

use crate::framing::{self, FrameError};
use crate::json::{self, Value};
use crate::position::Encoding;
use crate::rpc::{self, Id, Incoming, RpcError};
use crate::{debug_log, error_log};

/// Configuración del servidor.
#[derive(Clone, Debug)]
pub struct Config {
    /// Ruta del log; `None` escribe a stderr.
    pub log_path: Option<PathBuf>,
    /// Espera antes de analizar tras una edición.
    pub debounce: Duration,
    /// Máximo de diagnósticos publicados por documento.
    pub max_diagnostics: usize,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            log_path: None,
            debounce: Duration::from_millis(120),
            max_diagnostics: 200,
        }
    }
}

/// Servidor LSP listo para correr sobre un par de flujos.
pub struct Server<R: BufRead + Send + 'static, W: Write> {
    reader: Option<R>,
    writer: W,
    config: Config,
    initialized: bool,
    shutdown: bool,
    encoding: Encoding,
    pub(crate) documents: crate::docs::Documents,
    pub(crate) project: Option<crate::project::Project>,
    cache: Option<Cache>,
    cancelled: std::collections::HashSet<crate::rpc::Id>,
}

struct Cache {
    file: pengu_span::FileId,
    hash: pengu_vfs::ContentHash,
    analysis: crate::analysis::Analysis,
    index: crate::index::Index,
}

impl<R: BufRead + Send + 'static, W: Write> Server<R, W> {
    /// Crea el servidor.
    pub fn new(reader: R, writer: W, config: Config) -> Self {
        Self {
            reader: Some(reader),
            writer,
            config,
            initialized: false,
            shutdown: false,
            encoding: Encoding::Utf16,
            documents: crate::docs::Documents::new(),
            project: None,
            cache: None,
            cancelled: std::collections::HashSet::new(),
        }
    }

    /// Corre el bucle hasta `exit` o el cierre del flujo. Devuelve el código de salida.
    ///
    /// # Panics
    ///
    /// Si no se puede crear el hilo lector.
    pub fn serve(mut self) -> i32 {
        if let Err(error) = crate::log::init(self.config.log_path.as_deref()) {
            eprintln!("[pengu-lsp] no se pudo abrir el log: {error}");
        }
        let Some(reader) = self.reader.take() else {
            return 1;
        };
        let (sender, receiver) = mpsc::channel::<Result<String, FrameError>>();
        std::thread::Builder::new()
            .name("pengu-lsp-reader".to_owned())
            .spawn(move || {
                let mut reader = reader;
                loop {
                    match framing::read_message(&mut reader) {
                        Ok(Some(message)) => {
                            if sender.send(Ok(message)).is_err() {
                                return;
                            }
                        }
                        Ok(None) => return,
                        Err(error) => {
                            let _ = sender.send(Err(error));
                            return;
                        }
                    }
                }
            })
            .expect("no se pudo crear el hilo lector");

        loop {
            // Sin trabajo pendiente, bloquea hasta el siguiente mensaje; con
            // trabajo, espera el debounce para agrupar ediciones.
            let pending = if self.has_pending_work() {
                match receiver.recv_timeout(self.config.debounce) {
                    Ok(message) => Some(message),
                    Err(RecvTimeoutError::Timeout) => {
                        self.on_idle();
                        continue;
                    }
                    Err(RecvTimeoutError::Disconnected) => None,
                }
            } else {
                receiver.recv().ok()
            };
            let Some(incoming) = pending else {
                debug_log!("flujo cerrado");
                return 0;
            };
            match incoming {
                Ok(message) => {
                    if let Some(code) = self.on_message(&message) {
                        return code;
                    }
                }
                Err(error) => {
                    error_log!("{error}");
                    return 1;
                }
            }
        }
    }

    /// `true` si hay documentos pendientes de analizar.
    fn has_pending_work(&self) -> bool {
        !self.documents.dirty().is_empty()
    }

    /// Analiza los documentos sucios y publica diagnósticos (L2).
    fn on_idle(&mut self) {
        self.publish_dirty();
    }

    /// Publica los diagnósticos de cada documento sucio.
    fn publish_dirty(&mut self) {
        let dirty: Vec<crate::uri::Uri> = self
            .documents
            .dirty()
            .iter()
            .map(|document| document.uri().clone())
            .collect();
        let encoding = self.encoding;
        let max_diagnostics = self.config.max_diagnostics;
        for uri in dirty {
            let Some((version, diagnostics)) =
                self.collect_diagnostics(&uri, encoding, max_diagnostics)
            else {
                continue;
            };
            let count = diagnostics.len();
            let params = Value::object([
                ("uri", Value::from(uri.as_str())),
                ("version", Value::Int(i64::from(version))),
                ("diagnostics", Value::Array(diagnostics)),
            ]);
            let notification = rpc::notification("textDocument/publishDiagnostics", params);
            if self.send(&notification).is_ok() {
                debug_log!("publicados {count} diagnóstico(s) en {}", uri.as_str());
            }
            if let Some(document) = self.documents.get_mut(&uri) {
                document.mark_clean();
            }
        }
    }

    /// Analiza el documento si hace falta y devuelve sus diagnósticos en LSP.
    ///
    /// La caché es de una entrada (el último documento analizado), así que un
    /// documento distinto siempre se reanaliza.
    fn collect_diagnostics(
        &mut self,
        uri: &crate::uri::Uri,
        encoding: crate::position::Encoding,
        max_diagnostics: usize,
    ) -> Option<(i32, Vec<Value>)> {
        {
            let Self {
                documents, cache, ..
            } = self;
            let document = documents.get(uri)?;
            let file = document.file_id();
            let hash = document.hash();
            if cache
                .as_ref()
                .is_none_or(|cache| cache.file != file || cache.hash != hash)
            {
                let analysis = crate::analysis::analyze(file, document.text());
                let index = analysis
                    .krate
                    .as_ref()
                    .map_or_else(crate::index::Index::default, crate::index::Index::build);
                *cache = Some(Cache {
                    file,
                    hash,
                    analysis,
                    index,
                });
            }
            let mut diagnostics = Vec::new();
            if let Some(cache) = cache.as_ref() {
                for diagnostic in &cache.analysis.diagnostics {
                    if let Some(value) = crate::diag::to_lsp(document, diagnostic, encoding) {
                        diagnostics.push(value);
                    }
                }
            }
            if diagnostics.len() > max_diagnostics {
                diagnostics.truncate(max_diagnostics);
            }
            Some((document.version(), diagnostics))
        }
    }

    fn on_message(&mut self, message: &str) -> Option<i32> {
        let value = match json::parse(message) {
            Ok(value) => value,
            Err(error) => {
                error_log!("{error}");
                let _ = self.send(&rpc::error_response(
                    &Id::Int(-1),
                    &RpcError::new(rpc::codes::PARSE_ERROR, error.to_string()),
                ));
                return None;
            }
        };
        match rpc::parse_incoming(&value) {
            Ok(Incoming::Request { id, method, params }) => {
                self.on_request(&id, &method, &params);
                None
            }
            Ok(Incoming::Notification { method, params }) => self.on_notification(&method, &params),
            Ok(Incoming::Response { .. }) => {
                debug_log!("se ignora una respuesta del cliente");
                None
            }
            Ok(Incoming::Invalid) => None,
            Err(error) => {
                let _ = self.send(&rpc::error_response(&Id::Int(-1), &error));
                None
            }
        }
    }

    #[allow(clippy::too_many_lines)] // un brazo por método de LSP, sin lógica compartida
    fn on_request(&mut self, id: &Id, method: &str, params: &Value) {
        debug_log!("petición {method}");
        if self.cancelled.remove(id) {
            let error = RpcError::new(
                rpc::codes::REQUEST_CANCELLED,
                "la petición se canceló antes de procesarse",
            );
            let _ = self.send(&rpc::error_response(id, &error));
            return;
        }
        if !self.initialized && !matches!(method, "initialize" | "shutdown") {
            let error = RpcError::new(
                rpc::codes::SERVER_NOT_INITIALIZED,
                "el servidor no está inicializado",
            );
            let _ = self.send(&rpc::error_response(id, &error));
            return;
        }
        match method {
            "initialize" => {
                self.encoding = negotiate_encoding(params);
                self.initialized = true;
                self.project =
                    workspace_root(params).and_then(|root| crate::project::discover(&root));
                let result = Value::object([
                    ("capabilities", server_capabilities(self.encoding)),
                    (
                        "serverInfo",
                        Value::object([
                            ("name", Value::from("pengu-lsp")),
                            ("version", Value::from(env!("CARGO_PKG_VERSION"))),
                        ]),
                    ),
                ]);
                let _ = self.send(&rpc::response(id, result));
            }
            "shutdown" => {
                self.shutdown = true;
                let _ = self.send(&rpc::response(id, Value::Null));
            }
            "textDocument/hover" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let position = json_position(params.get("position")?)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                crate::features::hover(
                    document,
                    &cache.analysis,
                    &cache.index,
                    position,
                    server.encoding,
                )
            }),
            "textDocument/definition" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let position = json_position(params.get("position")?)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                crate::features::definition(document, &cache.index, position, server.encoding)
            }),
            "textDocument/completion" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let position = json_position(params.get("position")?)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                Some(crate::features::completion(
                    document,
                    &cache.analysis,
                    &cache.index,
                    position,
                    server.encoding,
                ))
            }),
            "textDocument/documentSymbol" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                Some(crate::features::document_symbols(document, &cache.index))
            }),
            "textDocument/references" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let position = json_position(params.get("position")?)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                let include = params
                    .get("context")
                    .and_then(|context| context.get("includeDeclaration"))
                    .and_then(Value::as_bool)
                    .unwrap_or(true);
                crate::refs::references(document, &cache.index, position, server.encoding, include)
            }),
            "textDocument/documentHighlight" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let position = json_position(params.get("position")?)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                crate::refs::highlights(document, &cache.index, position, server.encoding)
            }),
            "textDocument/prepareRename" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let position = json_position(params.get("position")?)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                crate::refs::prepare_rename(document, &cache.index, position, server.encoding)
            }),
            "textDocument/rename" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let position = json_position(params.get("position")?)?;
                let new_name = params.get("newName")?.as_str()?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                crate::refs::rename(document, &cache.index, position, new_name, server.encoding)
            }),
            "textDocument/semanticTokens/full" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                Some(Value::object([(
                    "data",
                    crate::semantic::tokens(document, &cache.index),
                )]))
            }),
            "textDocument/semanticTokens/range" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let range = json_range(params.get("range")?)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                Some(Value::object([(
                    "data",
                    crate::semantic::tokens_in(document, &cache.index, Some(range)),
                )]))
            }),
            "textDocument/inlayHint" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let range = json_range(params.get("range")?)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                Some(crate::hints::inlay_hints(
                    document,
                    &cache.analysis,
                    range,
                    server.encoding,
                ))
            }),
            "textDocument/signatureHelp" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let position = json_position(params.get("position")?)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                crate::extras::signature_help(document, &cache.index, position, server.encoding)
            }),
            "textDocument/codeLens" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                Some(crate::extras::code_lens(
                    document,
                    &cache.index,
                    server.encoding,
                ))
            }),
            "textDocument/foldingRange" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let document = server.documents.get(&uri)?;
                Some(crate::extras::folding_ranges(document))
            }),
            "textDocument/selectionRange" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let document = server.documents.get(&uri)?;
                let positions = params
                    .get("positions")?
                    .as_array()?
                    .iter()
                    .map(json_position)
                    .collect::<Option<Vec<_>>>()?;
                Some(crate::extras::selection_ranges(
                    document,
                    &positions,
                    server.encoding,
                ))
            }),
            "workspace/symbol" => self.respond(id, params, |server, params| {
                let query = params.get("query").and_then(Value::as_str).unwrap_or("");
                let entries = server.documents.iter().map(|document| {
                    let analysis = crate::analysis::analyze(document.file_id(), document.text());
                    let index = crate::index::Index::build(analysis.krate.as_ref()?);
                    Some((document.clone(), index))
                });
                let documents = entries.flatten().collect::<Vec<_>>();
                Some(crate::extras::workspace_symbols(&documents, query))
            }),
            "textDocument/typeDefinition" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let position = json_position(params.get("position")?)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                crate::advanced::type_definition(
                    document,
                    &cache.analysis,
                    &cache.index,
                    position,
                    server.encoding,
                )
            }),
            "textDocument/implementation" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let position = json_position(params.get("position")?)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                let krate = cache.analysis.krate.as_ref()?;
                crate::advanced::implementation(
                    document,
                    krate,
                    &cache.index,
                    position,
                    server.encoding,
                )
            }),
            "textDocument/codeAction" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                Some(crate::advanced::code_actions(
                    document,
                    &cache.analysis,
                    params,
                ))
            }),
            "callHierarchy/prepare" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let position = json_position(params.get("position")?)?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                Some(crate::advanced::prepare_call_hierarchy(
                    document,
                    &cache.index,
                    position,
                    server.encoding,
                ))
            }),
            "callHierarchy/incomingCalls" => self.respond(id, params, |server, params| {
                let item = params.get("item")?;
                let uri = crate::uri::Uri::parse(item.get("uri")?.as_str()?).ok()?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                Some(crate::advanced::incoming_calls(
                    document,
                    &cache.index,
                    item,
                    server.encoding,
                ))
            }),
            "callHierarchy/outgoingCalls" => self.respond(id, params, |server, params| {
                let item = params.get("item")?;
                let uri = crate::uri::Uri::parse(item.get("uri")?.as_str()?).ok()?;
                let document = server.documents.get(&uri)?;
                let cache = server.cache.as_ref()?;
                Some(crate::advanced::outgoing_calls(
                    document,
                    &cache.index,
                    item,
                    server.encoding,
                ))
            }),
            "textDocument/formatting" => self.respond(id, params, |server, params| {
                let uri = text_document_uri(params)?;
                let document = server.documents.get(&uri)?;
                Some(crate::format::formatting_edits(document))
            }),
            other => {
                let error = RpcError::new(
                    rpc::codes::METHOD_NOT_FOUND,
                    format!("método no soportado `{other}`"),
                );
                let _ = self.send(&rpc::error_response(id, &error));
            }
        }
    }

    fn on_notification(&mut self, method: &str, params: &Value) -> Option<i32> {
        debug_log!("notificación {method}");
        match method {
            "textDocument/didOpen" => {
                self.did_open(params);
                None
            }
            "textDocument/didChange" => {
                self.did_change(params);
                None
            }
            "textDocument/didSave" => {
                self.did_save(params);
                None
            }
            "textDocument/didClose" => {
                self.did_close(params);
                None
            }
            "$/cancelRequest" => {
                if let Some(id) = params.get("id").and_then(crate::rpc::Id::from_value) {
                    self.cancelled.insert(id);
                }
                None
            }
            "exit" => {
                if self.shutdown {
                    Some(0)
                } else {
                    Some(1)
                }
            }
            "initialized" | "$/setTrace" => None,
            other => {
                debug_log!("notificación desconocida `{other}`");
                None
            }
        }
    }

    /// Responde con el resultado de una feature, o `null` si no aplica.
    fn respond(
        &mut self,
        id: &Id,
        params: &Value,
        feature: impl FnOnce(&Self, &Value) -> Option<Value>,
    ) {
        if let Some(uri) = text_document_uri(params) {
            self.ensure_analysis(&uri);
        }
        let result = feature(self, params).unwrap_or(Value::Null);
        let _ = self.send(&rpc::response(id, result));
    }

    /// Analiza el documento si cambió desde el último análisis.
    fn ensure_analysis(&mut self, uri: &crate::uri::Uri) {
        let Self {
            documents, cache, ..
        } = self;
        let Some(document) = documents.get(uri) else {
            return;
        };
        let file = document.file_id();
        let hash = document.hash();
        if cache
            .as_ref()
            .is_some_and(|cache| cache.file == file && cache.hash == hash)
        {
            return;
        }
        let analysis = crate::analysis::analyze(file, document.text());
        let index = analysis
            .krate
            .as_ref()
            .map_or_else(crate::index::Index::default, crate::index::Index::build);
        *cache = Some(Cache {
            file,
            hash,
            analysis,
            index,
        });
    }

    fn did_open(&mut self, params: &Value) {
        let item = params.get("textDocument");
        let uri = item
            .and_then(|item| item.get("uri"))
            .and_then(Value::as_str);
        let text = item
            .and_then(|item| item.get("text"))
            .and_then(Value::as_str);
        let version = item
            .and_then(|item| item.get("version"))
            .and_then(Value::as_i64)
            .and_then(|version| i32::try_from(version).ok())
            .unwrap_or(0);
        let (Some(uri), Some(text)) = (uri, text) else {
            return;
        };
        let Ok(uri) = crate::uri::Uri::parse(uri) else {
            return;
        };
        if self.project.is_none() {
            if let Some(path) = uri.to_path() {
                self.project = crate::project::discover(&path);
            }
        }
        self.documents.open(uri, version, text.to_owned());
    }

    fn did_change(&mut self, params: &Value) {
        let item = params.get("textDocument");
        let uri = item
            .and_then(|item| item.get("uri"))
            .and_then(Value::as_str);
        let version = item
            .and_then(|item| item.get("version"))
            .and_then(Value::as_i64)
            .and_then(|version| i32::try_from(version).ok())
            .unwrap_or(0);
        let Some(uri) = uri.and_then(|uri| crate::uri::Uri::parse(uri).ok()) else {
            return;
        };
        let changes = content_changes(params);
        if changes.is_empty() {
            return;
        }
        self.documents
            .change(&uri, version, &changes, self.encoding);
    }

    fn did_save(&mut self, params: &Value) {
        let item = params.get("textDocument");
        let uri = item
            .and_then(|item| item.get("uri"))
            .and_then(Value::as_str);
        let text = params.get("text").and_then(Value::as_str);
        let Some(uri) = uri.and_then(|uri| crate::uri::Uri::parse(uri).ok()) else {
            return;
        };
        let Some(document) = self.documents.get_mut(&uri) else {
            return;
        };
        if let Some(text) = text {
            document.apply_full(text.to_owned(), document.version());
        } else if !document.read_only() {
            if let Some(path) = uri.to_path() {
                if let Ok(text) = std::fs::read_to_string(&path) {
                    if text != document.text() {
                        document.apply_full(text, document.version());
                    }
                }
            }
        }
    }

    fn did_close(&mut self, params: &Value) {
        let item = params.get("textDocument");
        let uri = item
            .and_then(|item| item.get("uri"))
            .and_then(Value::as_str);
        let Some(uri) = uri.and_then(|uri| crate::uri::Uri::parse(uri).ok()) else {
            return;
        };
        let read_only = self
            .documents
            .get(&uri)
            .is_some_and(crate::docs::Document::read_only);
        if read_only {
            return;
        }
        self.documents.close(&uri);
        let params = Value::object([
            ("uri", Value::from(uri.as_str())),
            ("diagnostics", Value::Array(Vec::new())),
        ]);
        let notification = rpc::notification("textDocument/publishDiagnostics", params);
        let _ = self.send(&notification);
    }

    fn send(&mut self, value: &Value) -> std::io::Result<()> {
        let text = json::render(value);
        framing::write_message(&mut self.writer, &text)
    }
}

fn text_document_uri(params: &Value) -> Option<crate::uri::Uri> {
    let uri = params
        .get("textDocument")
        .and_then(|item| item.get("uri"))
        .and_then(Value::as_str)?;
    crate::uri::Uri::parse(uri).ok()
}

fn json_position(value: &Value) -> Option<crate::position::Position> {
    Some(crate::position::Position {
        line: u32::try_from(value.get("line")?.as_i64()?).ok()?,
        character: u32::try_from(value.get("character")?.as_i64()?).ok()?,
    })
}

fn content_changes(params: &Value) -> Vec<crate::docs::ContentChange> {
    let mut changes = Vec::new();
    let Some(items) = params.get("contentChanges").and_then(Value::as_array) else {
        return changes;
    };
    for item in items {
        let Some(text) = item.get("text").and_then(Value::as_str) else {
            continue;
        };
        changes.push(crate::docs::ContentChange {
            range: item.get("range").and_then(json_range),
            text: text.to_owned(),
        });
    }
    changes
}

fn json_range(value: &Value) -> Option<crate::position::Range> {
    let start = value.get("start")?;
    let end = value.get("end")?;
    let position = |value: &Value| {
        Some(crate::position::Position {
            line: u32::try_from(value.get("line")?.as_i64()?).ok()?,
            character: u32::try_from(value.get("character")?.as_i64()?).ok()?,
        })
    };
    Some(crate::position::Range::new(
        position(start)?,
        position(end)?,
    ))
}

fn workspace_root(params: &Value) -> Option<std::path::PathBuf> {
    if let Some(folders) = params.get("workspaceFolders").and_then(Value::as_array) {
        if let Some(uri) = folders
            .first()
            .and_then(|folder| folder.get("uri"))
            .and_then(Value::as_str)
        {
            if let Some(path) = crate::uri::Uri::parse(uri)
                .ok()
                .and_then(|uri| uri.to_path())
            {
                return Some(path);
            }
        }
    }
    let root = params.get("rootUri").and_then(Value::as_str)?;
    crate::uri::Uri::parse(root)
        .ok()
        .and_then(|uri| uri.to_path())
}

fn negotiate_encoding(params: &Value) -> Encoding {
    let offered = params
        .get("capabilities")
        .and_then(|capabilities| capabilities.get("general"))
        .and_then(|general| general.get("positionEncodings"))
        .and_then(Value::as_array);
    if let Some(encodings) = offered {
        for encoding in encodings {
            match encoding.as_str() {
                Some("utf-8") => return Encoding::Utf8,
                Some("utf-16") => return Encoding::Utf16,
                _ => {}
            }
        }
    }
    Encoding::Utf16
}

fn server_capabilities(encoding: Encoding) -> Value {
    Value::object([
        ("positionEncoding", Value::from(encoding.as_str())),
        (
            "textDocumentSync",
            Value::object([
                ("openClose", Value::Bool(true)),
                ("change", Value::Int(2)),
                ("save", Value::object([("includeText", Value::Bool(false))])),
            ]),
        ),
        ("hoverProvider", Value::Bool(true)),
        (
            "completionProvider",
            Value::object([
                (
                    "triggerCharacters",
                    Value::Array(vec![
                        Value::from("."),
                        Value::from(":"),
                        Value::from("("),
                        Value::from("\""),
                    ]),
                ),
                ("resolveProvider", Value::Bool(false)),
            ]),
        ),
        ("definitionProvider", Value::Bool(true)),
        ("documentSymbolProvider", Value::Bool(true)),
        ("documentFormattingProvider", Value::Bool(true)),
        ("referencesProvider", Value::Bool(true)),
        ("documentHighlightProvider", Value::Bool(true)),
        (
            "renameProvider",
            Value::object([("prepareProvider", Value::Bool(true))]),
        ),
        (
            "semanticTokensProvider",
            Value::object([
                ("legend", crate::semantic::legend()),
                ("full", Value::Bool(true)),
                ("range", Value::Bool(true)),
            ]),
        ),
        ("inlayHintProvider", Value::Bool(true)),
        (
            "signatureHelpProvider",
            Value::object([(
                "triggerCharacters",
                Value::Array(vec![Value::from("("), Value::from(",")]),
            )]),
        ),
        (
            "codeLensProvider",
            Value::object([("resolveProvider", Value::Bool(false))]),
        ),
        ("foldingRangeProvider", Value::Bool(true)),
        ("selectionRangeProvider", Value::Bool(true)),
        ("workspaceSymbolProvider", Value::Bool(true)),
        ("typeDefinitionProvider", Value::Bool(true)),
        ("implementationProvider", Value::Bool(true)),
        ("codeActionProvider", Value::Bool(true)),
        (
            "callHierarchyProvider",
            Value::object([("prepareProvider", Value::Bool(true))]),
        ),
        (
            "workspace",
            Value::object([(
                "workspaceFolders",
                Value::object([
                    ("supported", Value::Bool(true)),
                    ("changeNotifications", Value::Bool(false)),
                ]),
            )]),
        ),
    ])
}

/// Corre el servidor sobre stdin/stdout.
#[must_use]
pub fn run_stdio(config: Config) -> i32 {
    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    Server::new(std::io::BufReader::new(stdin), stdout, config).serve()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::json;

    #[test]
    fn negocia_utf8_si_el_cliente_lo_ofrece() {
        let params =
            json::parse(r#"{"capabilities":{"general":{"positionEncodings":["utf-8","utf-16"]}}}"#)
                .expect("json");
        assert_eq!(negotiate_encoding(&params), Encoding::Utf8);
    }

    #[test]
    fn usa_utf16_por_defecto() {
        let params = json::parse(r#"{"capabilities":{}}"#).expect("json");
        assert_eq!(negotiate_encoding(&params), Encoding::Utf16);
    }

    #[test]
    fn capacidades_declaran_las_features_de_la_fase() {
        let capabilities = server_capabilities(Encoding::Utf16);
        for key in [
            "hoverProvider",
            "completionProvider",
            "definitionProvider",
            "documentSymbolProvider",
            "documentFormattingProvider",
            "referencesProvider",
            "documentHighlightProvider",
            "renameProvider",
            "semanticTokensProvider",
            "inlayHintProvider",
            "signatureHelpProvider",
            "codeLensProvider",
            "foldingRangeProvider",
            "selectionRangeProvider",
            "workspaceSymbolProvider",
            "typeDefinitionProvider",
            "implementationProvider",
            "codeActionProvider",
            "callHierarchyProvider",
            "textDocumentSync",
        ] {
            assert!(capabilities.get(key).is_some(), "falta {key}");
        }
    }
}
