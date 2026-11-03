#!/usr/bin/env node
// Pruebas del modelo de bloques `antiquus` (detección, espejo y traslado de
// posiciones). No necesita la API de VS Code: el módulo puro se compila a
// out/antiquusModel.js con `npm run compile`.

const assert = require('assert');
const path = require('path');

const model = require(path.join(__dirname, '..', 'out', 'antiquusModel.js'));

const SOURCE = [
    'import std.spark',
    '',
    'antiquus suma_c with a as int, b as int into int:',
    '    r"""',
    '    return a + b;',
    '    """',
    '',
    'antiquus completa into void:',
    '    r"""',
    'int doble(int x) {',
    '    return x * 2;',
    '}',
    '    """',
    ''
].join('\n');

let failures = 0;
function check(name, fn) {
    try {
        fn();
        console.log(`ok - ${name}`);
    } catch (error) {
        failures += 1;
        console.log(`FAIL - ${name}\n     ${error.message}`);
    }
}

check('detecta los dos bloques y sus límites', () => {
    const blocks = model.findAntiquusBlocks(SOURCE);
    assert.strictEqual(blocks.length, 2);
    assert.strictEqual(blocks[0].name, 'suma_c');
    assert.deepStrictEqual([blocks[0].declLine, blocks[0].bodyStart, blocks[0].bodyEnd], [2, 4, 5]);
    assert.strictEqual(blocks[1].name, 'completa');
    assert.deepStrictEqual([blocks[1].declLine, blocks[1].bodyStart, blocks[1].bodyEnd], [7, 9, 12]);
});

check('traduce tipos de PenguScript a C', () => {
    assert.strictEqual(model.cType('int'), 'int');
    assert.strictEqual(model.cType('i64'), 'long long');
    assert.strictEqual(model.cType('string'), 'const char*');
    assert.strictEqual(model.cType('ref to Foo'), 'Foo');
    assert.strictEqual(model.cType('MiStruct'), 'MiStruct');
});

check('lee parámetros y retorno de la declaración', () => {
    const sig = model.declSignature('antiquus suma_c with a as int, b as string into i64:');
    assert.deepStrictEqual(sig.params, [
        { name: 'a', type: 'int' },
        { name: 'b', type: 'const char*' }
    ]);
    assert.strictEqual(sig.ret, 'long long');
    const plain = model.declSignature('antiquus f into void:');
    assert.deepStrictEqual(plain.params, []);
    assert.strictEqual(plain.ret, 'void');
});

check('envuelve un fragmento en una función', () => {
    const blocks = model.findAntiquusBlocks(SOURCE);
    const { lines, offset } = model.buildMirrorContent(SOURCE, blocks[0]);
    assert.strictEqual(offset, 2);
    assert.ok(lines[0].includes('suma_c'));
    assert.strictEqual(lines[1], 'static int suma_c(int a, int b) {');
    assert.strictEqual(lines[2], '    return a + b;');
    assert.strictEqual(lines[lines.length - 1], '}');
});

check('emite las declaraciones completas tal cual', () => {
    const blocks = model.findAntiquusBlocks(SOURCE);
    const { lines, offset } = model.buildMirrorContent(SOURCE, blocks[1]);
    assert.strictEqual(offset, 1);
    assert.deepStrictEqual(lines.slice(1), [
        'int doble(int x) {',
        '    return x * 2;',
        '}'
    ]);
});

check('sube los #include y conserva las posiciones', () => {
    const text = ['antiquus t into int:', '    r"""', '    #include <string.h>', '    return 1;', '    """'].join('\n');
    const blocks = model.findAntiquusBlocks(text);
    const { lines, offset } = model.buildMirrorContent(text, blocks[0]);
    assert.strictEqual(offset, 3);
    assert.strictEqual(lines[1], '    #include <string.h>');
    assert.strictEqual(lines[2], 'static int t() {');
    assert.strictEqual(lines[3], '    //#include <string.h>');
    assert.strictEqual(lines[4], '    return 1;');
});

check('las posiciones van y vuelven sin perder líneas', () => {
    const blocks = model.findAntiquusBlocks(SOURCE);
    const block = blocks[0];
    block.offset = 2;
    const sourcePos = { line: 4, character: 11 };
    const mirrorPos = model.toMirrorPosition(block, sourcePos);
    assert.deepStrictEqual(mirrorPos, { line: 2, character: 11 });
    assert.ok(model.insideBody(block, sourcePos));
    assert.ok(!model.insideBody(block, { line: 2, character: 0 }));
    const back = model.fromMirrorRange(block, { start: mirrorPos, end: { line: 2, character: 20 } });
    assert.deepStrictEqual(back, { start: { line: 4, character: 11 }, end: { line: 4, character: 20 } });
});

if (failures > 0) {
    console.log(`\n${failures} prueba(s) fallida(s)`);
    process.exit(1);
}
console.log('\nALL OK');
