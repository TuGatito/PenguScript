🗺️ Plan por fases
Fase	Entregable	Depende de
0. Esqueleto	pyproject.toml, uv sync, pengu --version, ruff+mypy verdes	—
1. Frontend	grammar.lark mínimo (rune, enchanting, fn), parser LALR+Indenter, AST, transformer, errores de sintaxis con rich	0
2. Análisis	symbols, tipos primitivos, resolución de realms e invoke, checker con diagnósticos por código, pengu check	1
3. Backend	plantillas Jinja2 para rune, enchanting, fn, omen, echo, seal; includes; pengu build end-to-end (compila un hello.pengu a binario)	2
4. CLI completo	build, check, run, lsp, new, clean con Typer + Rich	3
5. LSP	pygls server, didOpen/didChange con diagnósticos, hover, go-to-def, document symbols, semantic tokens, formatting	2
6. Extensión VSCode	cliente LSP, TextMate grammar, language config, snippets, icon	4, 5
7. Pulido	rename, completion contextual, cache incremental en el LSP, avanzar la gramática a toda la spec (sigils, operators, unsafe, echo/seal, comprehensions, etc.)	6