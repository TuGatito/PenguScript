/**
 * TextMate regression tests for the raylib bindings corpus.
 *
 * The wrapper header uses bare `##` separator lines; they must stay line
 * documentation and must not start an invented block comment. The binding
 * files use `const ... as i64 is ...`, so keyword/type alternations must work.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const vsctm = require('vscode-textmate');
const onig = require('vscode-oniguruma');

const ROOT = path.resolve(__dirname, '..');
const GRAMMAR_PATH = path.join(ROOT, 'syntaxes', 'pengus.tmLanguage.json');
const RAYLIB = process.env.RAYLIB_PENGU || path.resolve(ROOT, '..', '..', 'raylib-pengu');
const grammar = JSON.parse(fs.readFileSync(GRAMMAR_PATH, 'utf8'));
// Stub of the C grammar that VS Code ships (`source.c`). The antiquus body
// delegates to it; without a C grammar loaded the include is a no-op, so the
// test registers a minimal stub to prove the embedding is wired correctly.
const C_STUB = {
    scopeName: 'source.c',
    patterns: [
        { match: '\\b(int|char|void|double|float|return|struct|if|else)\\b', name: 'keyword.control.c' },
        { match: '#\\s*include.*$', name: 'keyword.control.preprocessor.c' }
    ],
    repository: {}
};
const wasm = fs.readFileSync(require.resolve('vscode-oniguruma/release/onig.wasm'));

let failures = 0;
function check(name, condition, detail) {
    if (condition) {
        console.log(`ok   ${name}`);
    } else {
        failures += 1;
        console.log(`FAIL ${name}${detail ? `\n  ${detail}` : ''}`);
    }
}

function tokenize(grammarObject, lines) {
    const lib = onig.loadWASM(wasm.buffer);
    const registry = new vsctm.Registry({
        onigLib: lib.then(() => ({
            createOnigScanner: (patterns) => new onig.OnigScanner(patterns),
            createOnigString: (s) => new onig.OnigString(s)
        })),
        loadGrammar: (scopeName) => Promise.resolve(
            scopeName === 'source.c' ? C_STUB : (scopeName === 'source.pengus' ? grammarObject : null)
        )
    });
    return registry.loadGrammar('source.pengus').then((g) => {
        let stack = vsctm.INITIAL;
        return lines.map((line) => {
            const result = g.tokenizeLine(line, stack);
            stack = result.ruleStack;
            return result.tokens.map((t) => ({
                text: line.slice(t.startIndex, t.endIndex),
                scopes: t.scopes
            }));
        });
    });
}

function hasScope(tokens, text, prefix) {
    return tokens.some((t) => t.text === text && t.scopes.some((s) => s.startsWith(prefix)));
}
function anyScope(tokens, prefix) {
    return tokens.some((t) => t.scopes.some((s) => s.startsWith(prefix)));
}

async function main() {
    const synthetic = [
        '## Header',
        '##',
        '## Details',
        '##',
        'import raylib',
        'enchanting raylib.Mesh:',
        '    ## Uploads the mesh.',
        '    weave upload with dynamic as bool into void:',
        '        return',
        '',
        'const X as i64 is 6',
        'const C as Color is with r is 1',
        'antiquus suma_c with a as int, b as int into int:',
        '    r"""',
        '    int total = a + b;',
        '    #include <stdio.h>',
        '    return total;',
        '    """',
        '',
        'weave after_antiquus into int:',
        '    return 0'
    ];
    const tokens = await tokenize(grammar, synthetic);

    check('bare ## is line documentation, not a block', tokens[1].every((t) => t.scopes.some((s) => s.startsWith('comment.line.documentation'))), JSON.stringify(tokens[1]));
    check('import after bare ## is not a comment', hasScope(tokens[4], 'import', 'keyword.other'), JSON.stringify(tokens[4]));
    check('enchanting after bare ## is a declaration', hasScope(tokens[5], 'enchanting', 'keyword.declaration.type'), JSON.stringify(tokens[5]));
    check('dotted enchanting type is a type', hasScope(tokens[5], 'raylib.Mesh', 'entity.name.type'), JSON.stringify(tokens[5]));
    check('weave inside enchanting is a function', hasScope(tokens[7], 'weave', 'keyword.declaration.function'), JSON.stringify(tokens[7]));
    check('const keyword is highlighted', hasScope(tokens[10], 'const', 'keyword.other'), JSON.stringify(tokens[10]));
    check('i64 builtin type is highlighted', hasScope(tokens[10], 'i64', 'storage.type.primitive'), JSON.stringify(tokens[10]));
    check('as keyword is highlighted', hasScope(tokens[10], 'as', 'keyword.other'), JSON.stringify(tokens[10]));
    check('is keyword is highlighted', hasScope(tokens[10], 'is', 'keyword.other'), JSON.stringify(tokens[10]));
    check('with keyword is highlighted', hasScope(tokens[11], 'with', 'keyword.other'), JSON.stringify(tokens[11]));
    check('Color type is highlighted', hasScope(tokens[11], 'Color', 'entity.name.type'), JSON.stringify(tokens[11]));

    // antiquus: the C body is embedded and highlighted with the C grammar.
    check('antiquus declaration keeps the function keyword', hasScope(tokens[12], 'antiquus', 'keyword.declaration.function'), JSON.stringify(tokens[12]));
    check('antiquus C body is embedded', tokens[14].every((t) => t.text.trim() === '' || t.scopes.some((sc) => sc.startsWith('meta.embedded.block.c'))), JSON.stringify(tokens[14]));
    check('antiquus C type is highlighted by source.c', hasScope(tokens[14], 'int', 'keyword.control.c'), JSON.stringify(tokens[14]));
    check('antiquus C preprocessor is highlighted', hasScope(tokens[15], '#include <stdio.h>', 'keyword.control.preprocessor.c'), JSON.stringify(tokens[15]));
    check('antiquus block closes before the next weave', hasScope(tokens[19], 'weave', 'keyword.declaration.function'), JSON.stringify(tokens[19]));

    const wrapper = path.join(RAYLIB, 'pengu', 'raylibx', 'models.pengu');
    const binding = path.join(RAYLIB, 'pengu', 'raylib.d.pengu');
    if (fs.existsSync(wrapper) && fs.existsSync(binding)) {
        const wrapperLines = fs.readFileSync(wrapper, 'utf8').split(/\n/);
        const wrapperTokens = await tokenize(grammar, wrapperLines);
        const importLine = wrapperLines.findIndex((l) => l === 'import raylib');
        check('models.pengu: import raylib is not comment', importLine >= 0 && hasScope(wrapperTokens[importLine], 'import', 'keyword.other'), importLine >= 0 ? JSON.stringify(wrapperTokens[importLine]) : 'missing import');
        const enchantLine = wrapperLines.findIndex((l) => l === 'enchanting raylib.Mesh:');
        check('models.pengu: enchanting raylib.Mesh is visible', enchantLine >= 0 && hasScope(wrapperTokens[enchantLine], 'enchanting', 'keyword.declaration.type'), enchantLine >= 0 ? JSON.stringify(wrapperTokens[enchantLine]) : 'missing enchanting');

        const bindingLines = fs.readFileSync(binding, 'utf8').split(/\n/);
        const bindingTokens = await tokenize(grammar, bindingLines);
        const constLine = bindingLines.findIndex((l) => l.startsWith('const RAYLIB_VERSION_MAJOR as i64 is '));
        check('raylib.d.pengu: const/as/i64/is are highlighted', constLine >= 0 && ['const', 'as', 'i64', 'is'].every((w) => hasScope(bindingTokens[constLine], w, w === 'i64' ? 'storage.type' : 'keyword.other')), constLine >= 0 ? JSON.stringify(bindingTokens[constLine]) : 'missing const');
    } else {
        console.log(`skip real raylib corpus (not found at ${RAYLIB})`);
    }

    console.log(failures === 0 ? 'ALL OK' : `${failures} FAILURE(S)`);
    process.exit(failures === 0 ? 0 : 1);
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
