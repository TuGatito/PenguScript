"use strict";
// Modelo puro de los bloques `antiquus` (sin dependencias de la API de VS Code).
// Se prueba en test/antiquus.test.js.
Object.defineProperty(exports, "__esModule", { value: true });
exports.findAntiquusBlocks = findAntiquusBlocks;
exports.cType = cType;
exports.declSignature = declSignature;
exports.buildMirrorContent = buildMirrorContent;
exports.toMirrorPosition = toMirrorPosition;
exports.insideBody = insideBody;
exports.fromMirrorRange = fromMirrorRange;
const DECL = /^\s*antiquus\s+([A-Za-z_][A-Za-z0-9_]*)/i;
const OPEN = /^\s*r"""/;
const CLOSE = /^\s*"""/;
/** Localiza los bloques `antiquus` de un documento. */
function findAntiquusBlocks(text) {
    const lines = text.split(/\r?\n/);
    const blocks = [];
    let pending;
    let bodyStart = -1;
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (bodyStart >= 0) {
            if (CLOSE.test(line)) {
                if (pending) {
                    blocks.push({
                        name: pending.name,
                        declLine: pending.declLine,
                        bodyStart,
                        bodyEnd: i
                    });
                    pending = undefined;
                }
                bodyStart = -1;
            }
            continue;
        }
        const decl = DECL.exec(line);
        if (decl) {
            pending = { name: decl[1], declLine: i };
            continue;
        }
        if (pending && OPEN.test(line)) {
            bodyStart = i + 1;
        }
    }
    return blocks;
}
const C_TYPES = {
    int: 'int',
    i8: 'signed char',
    i16: 'short',
    i32: 'int',
    i64: 'long long',
    u8: 'unsigned char',
    u16: 'unsigned short',
    u32: 'unsigned int',
    u64: 'unsigned long long',
    f32: 'float',
    f64: 'double',
    float: 'double',
    bool: 'bool',
    rune: 'int',
    string: 'const char*',
    bytes: 'const char*',
    void: 'void'
};
/** Traduce un tipo de PenguScript a un tipo de C. */
function cType(type) {
    const cleaned = type
        .trim()
        .replace(/^ref\s+to\s+/, '')
        .replace(/^ptr\s+to\s+/, '');
    return C_TYPES[cleaned] ?? cleaned;
}
/** Extrae parámetros y tipo de retorno de la línea `antiquus`. */
function declSignature(declLine) {
    const params = [];
    const inner = /with\s+(.+?)\s+into\s+[^:]+:\s*$/.exec(declLine);
    if (inner) {
        for (const raw of inner[1].split(',')) {
            const m = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s+as\s+(.+)$/.exec(raw);
            if (m) {
                params.push({ name: m[1], type: cType(m[2]) });
            }
        }
    }
    const ret = /into\s+([^:]+):\s*$/.exec(declLine);
    return { params, ret: cType(ret ? ret[1] : 'void') };
}
/**
 * Construye el contenido del espejo. Los dos estilos de cuerpo se soportan:
 * fragmentos (`return ...;`), que se envuelven en una función con los
 * parámetros de la declaración, y declaraciones completas, que se emiten tal
 * cual. Las líneas del cuerpo quedan en su posición para que la traducción
 * de posiciones sea una simple suma.
 */
function buildMirrorContent(text, block) {
    const all = text.split(/\r?\n/);
    const body = all.slice(block.bodyStart, block.bodyEnd);
    const decl = all[block.declLine] ?? '';
    const hasBraces = body.some((line) => line.includes('{'));
    const pre = [];
    for (const line of body) {
        if (/^\s*#/.test(line)) {
            pre.push(line);
        }
    }
    const header = [`// antiquus ${block.name} (generado por extensión PenguScript)`];
    header.push(...pre);
    if (!hasBraces) {
        const { params, ret } = declSignature(decl);
        const names = params.map((p) => `${p.type} ${p.name}`).join(', ');
        header.push(`static ${ret} ${block.name}(${names}) {`);
    }
    const lines = [...header];
    for (const line of body) {
        if (/^\s*#/.test(line)) {
            const indent = /^\s*/.exec(line)?.[0] ?? '';
            lines.push(`${indent}//${line.slice(indent.length)}`);
        }
        else {
            lines.push(line);
        }
    }
    if (!hasBraces) {
        lines.push('}');
    }
    return { lines, offset: header.length };
}
/** Posición del documento de origen → posición del espejo. */
function toMirrorPosition(block, position) {
    const offset = block.offset ?? 0;
    return { line: position.line - block.bodyStart + offset, character: position.character };
}
/** ¿Cae la posición dentro del cuerpo C del bloque? */
function insideBody(block, position) {
    return position.line >= block.bodyStart && position.line < block.bodyEnd;
}
/** Rango del espejo → rango del documento de origen. */
function fromMirrorRange(block, range) {
    const offset = block.offset ?? 0;
    const startLine = range.start.line - offset + block.bodyStart;
    const endLine = range.end.line - offset + block.bodyStart;
    if (endLine < block.bodyStart || startLine >= block.bodyEnd) {
        return undefined;
    }
    return {
        start: { line: Math.max(startLine, block.bodyStart), character: range.start.character },
        end: {
            line: Math.min(endLine, block.bodyEnd - 1),
            character: range.end.character
        }
    };
}
//# sourceMappingURL=antiquusModel.js.map