// Modelo puro de los bloques `antiquus` (sin dependencias de la API de VS Code).
// Se prueba en test/antiquus.test.js.

export interface AntiquusBlock {
    /** Nombre declarado en `antiquus <name> ...`. */
    name: string;
    /** Línea (0-based) de la declaración `antiquus ...:`. */
    declLine: number;
    /** Primera línea (0-based) del cuerpo, es decir, la siguiente a `r"""`. */
    bodyStart: number;
    /** Línea (0-based) del cierre `"""` (exclusiva para el cuerpo). */
    bodyEnd: number;
    /** Líneas antes del cuerpo en el espejo (cabecera + includes + firma). */
    offset?: number;
}


const DECL = /^\s*antiquus\s+([A-Za-z_][A-Za-z0-9_]*)/i;
const OPEN = /^\s*r"""/;
const CLOSE = /^\s*"""/;

/** Localiza los bloques `antiquus` de un documento. */
export function findAntiquusBlocks(text: string): AntiquusBlock[] {
    const lines = text.split(/\r?\n/);
    const blocks: AntiquusBlock[] = [];
    let pending: { name: string; declLine: number } | undefined;
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

const C_TYPES: Record<string, string> = {
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
export function cType(type: string): string {
    const cleaned = type
        .trim()
        .replace(/^ref\s+to\s+/, '')
        .replace(/^ptr\s+to\s+/, '');
    return C_TYPES[cleaned] ?? cleaned;
}

/** Extrae parámetros y tipo de retorno de la línea `antiquus`. */
export function declSignature(declLine: string): { params: { name: string; type: string }[]; ret: string } {
    const params: { name: string; type: string }[] = [];
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
export function buildMirrorContent(text: string, block: AntiquusBlock): { lines: string[]; offset: number } {
    const all = text.split(/\r?\n/);
    const body = all.slice(block.bodyStart, block.bodyEnd);
    const decl = all[block.declLine] ?? '';
    const hasBraces = body.some((line) => line.includes('{'));
    const pre: string[] = [];
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
        } else {
            lines.push(line);
        }
    }
    if (!hasBraces) {
        lines.push('}');
    }
    return { lines, offset: header.length };
}


export interface SimplePosition {
    line: number;
    character: number;
}

/** Posición del documento de origen → posición del espejo. */
export function toMirrorPosition(block: AntiquusBlock, position: SimplePosition): SimplePosition {
    const offset = block.offset ?? 0;
    return { line: position.line - block.bodyStart + offset, character: position.character };
}

/** ¿Cae la posición dentro del cuerpo C del bloque? */
export function insideBody(block: AntiquusBlock, position: SimplePosition): boolean {
    return position.line >= block.bodyStart && position.line < block.bodyEnd;
}

/** Rango del espejo → rango del documento de origen. */
export function fromMirrorRange(
    block: AntiquusBlock,
    range: { start: SimplePosition; end: SimplePosition }
): { start: SimplePosition; end: SimplePosition } | undefined {
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
