// Benchmark del servidor LSP con archivos grandes.
//
//   cargo build -p pengu-cli --release
//   node editors/bench.mjs [ruta-al-binario] [número-de-funciones]
//
// Mide: análisis completo tras `didOpen` (diagnósticos) y una petición de
// símbolos después de un cambio completo del documento.

import { spawn } from 'node:child_process';

const serverPath = process.argv[2] ?? 'target/release/pengu';
const functions = Number(process.argv[3] ?? 3000);

let source = '';
for (let index = 0; index < functions; index += 1) {
  source += `f${index} = (a: Int) -> Int\n    a + ${index}\n`;
}
source += '\ngrimoire\n    print(f0(1))\n';

const child = spawn(serverPath, ['lsp'], { stdio: ['pipe', 'pipe', 'pipe'] });
let buffer = Buffer.alloc(0);
let nextId = 1;
const pending = new Map();
const notifications = [];
let onNotification = () => {};

child.stdout.on('data', (chunk) => {
  buffer = Buffer.concat([buffer, chunk]);
  for (;;) {
    const headerEnd = buffer.indexOf('\r\n\r\n');
    if (headerEnd < 0) return;
    const header = buffer.subarray(0, headerEnd).toString('ascii');
    const length = Number(/content-length:\s*(\d+)/i.exec(header)?.[1]);
    const start = headerEnd + 4;
    if (buffer.length < start + length) return;
    const body = buffer.subarray(start, start + length).toString('utf8');
    buffer = buffer.subarray(start + length);
    const message = JSON.parse(body);
    if (message.method) {
      notifications.push(message);
      onNotification(message);
    } else if (pending.has(message.id)) {
      pending.get(message.id)(message);
      pending.delete(message.id);
    }
  }
});

function send(payload) {
  const body = JSON.stringify(payload);
  child.stdin.write(`Content-Length: ${Buffer.byteLength(body)}\r\n\r\n${body}`);
}

function request(method, params) {
  const id = nextId++;
  return new Promise((resolve) => {
    pending.set(id, resolve);
    send({ jsonrpc: '2.0', id, method, params });
  });
}

function notify(method, params) {
  send({ jsonrpc: '2.0', method, params });
}

function waitFor(predicate, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('tiempo de espera agotado')), timeoutMs);
    onNotification = (message) => {
      if (!predicate(message)) return;
      clearTimeout(timer);
      onNotification = () => {};
      resolve(message);
    };
  });
}

const uri = 'file:///tmp/pengu-bench/main.pengu';

await request('initialize', {
  processId: process.pid,
  rootUri: 'file:///tmp/pengu-bench',
  capabilities: { general: { positionEncodings: ['utf-16'] } },
});
notify('initialized', {});

const openStart = performance.now();
const diagnostics = waitFor(
  (message) => message.method === 'textDocument/publishDiagnostics' && message.params.uri === uri,
  120_000,
);
notify('textDocument/didOpen', {
  textDocument: { uri, languageId: 'pengu', version: 1, text: source },
});
const published = await diagnostics;
const openMs = performance.now() - openStart;
console.log(
  `didOpen ${functions} funciones (${source.split('\n').length} líneas): ${openMs.toFixed(0)} ms, ` +
    `${published.params.diagnostics.length} diagnóstico(s)`,
);

const changeStart = performance.now();
notify('textDocument/didChange', {
  textDocument: { uri, version: 2 },
  contentChanges: [{ text: `${source}\n` }],
});
const symbols = await request('textDocument/documentSymbol', {
  textDocument: { uri },
});
console.log(
  `didChange + documentSymbol: ${(performance.now() - changeStart).toFixed(0)} ms, ` +
    `${symbols.result?.length ?? 0} símbolo(s)`,
);

await request('shutdown', null);
notify('exit', null);
child.stdin.end();
