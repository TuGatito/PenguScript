frontend/ — todo lo que sabe de sintaxis. grammar.lark es el único archivo que tendrás que mantener a mano cuando cambie el lenguaje. El parser.py instancia Lark con parser='lalr' y postlex=Indenter (configurando paren_table para que paréntesis, corchetes y llaves dentro de expresiones no generen indentación). El transformer.py convierte el CST de Lark en @dataclass de ast_nodes.py; los nodos llevan su Span (byte offset) desde el principio, porque lo usan tanto el checker como el LSP.

analysis/ — el type checker. diagnostics.py define un Diagnostic con code (E0012), severity, message, labels: list[Label], notes: list[str], suggestions. Ese mismo objeto se renderiza con rich en el CLI y se mapea a Diagnostic de LSP. symbols.py mantiene scopes anidados (realm → archivo → función → bloque) y es la base de hover, go-to-def y rename. El checker nunca genera C++; produce un AST anotado o un dict[int, Type] indexado por id(nodo).

backend/ — Jinja2, con una plantilla por constructo. La decisión clave es que las plantillas no contienen lógica del lenguaje: reciben un contexto ya resuelto por Python (tipos, includes necesarios, expresiones C++ pre-renderizadas). includes.py (implícito en codegen.py) acumula qué cabeceras necesita el archivo final para emitir los #include una sola vez.

project/ — carga pengu.toml con tomllib (stdlib) y resuelve rutas de invoke (foo.pengu vs foo/index.pengu), detecta ciclos y produce el orden topológico. Este módulo lo usan tanto el build como el LSP (para resolver imports entre archivos del proyecto).

lsp/ — server.py instancia pygls.LanguageServer y en initialize declara PositionEncodingKind.UTF8 para que las posiciones sean offsets de bytes, como pediste. Cada didOpen/didChange reparsea el documento (rápido con LALR) y reanaliza; el AST cacheado vive en documents.py. Las features son independientes: cada archivo de features/ registra un handler sobre el server. diagnostics.py es el que se publica tras cada análisis y el que también usa el CLI de pengu check.

driver/build.py — el pipeline completo: project.load() → frontend.parse() → analysis.check() → backend.codegen() → escribir .cpp → invocar g++/clang++. El CLI es un wrapper fino sobre esto.

stdlib/ — embebido en el paquete (via importlib.resources o MANIFEST.in), así invoke "std/io" funciona sin instalación externa.