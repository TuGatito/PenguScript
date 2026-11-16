// Prueba de humo del servidor LSP usando el mismo framing que el cliente de
// VS Code (`editors/vscode/src/extension.js`). No necesita dependencias.
//
//   node editors/smoke.mjs [ruta-al-binario-pengu]
//
// Comprueba: initialize, didOpen, publishDiagnostics, hover, completion por
// contexto (`summon std::`), inlay hints, code lens de ejecución, semantic
// tokens y shutdown.

import { spawn } from 'node:child_process';

const serverPath = process.argv[2] ?? 'target/debug/pengu';
const child = spawn(serverPath, ['lsp'], { stdio: ['pipe', 'pipe', 'pipe'] });

let buffer = Buffer.alloc(0);
let nextId = 1;
const pending = new Map();
const notifications = [];
let waiters = [];

function onMessage(message) {
  if (message.method) {
    notifications.push(message);
    for (const waiter of waiters) {
      waiter();
    }
    return;
  }
  const entry = pending.get(message.id);
  if (entry) {
    pending.delete(message.id);
    entry(message);
  }
}

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
    onMessage(JSON.parse(body));
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

function waitFor(predicate, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('tiempo de espera agotado')), timeoutMs);
    const check = () => {
      const found = notifications.find(predicate);
      if (found) {
        clearTimeout(timer);
        waiters = waiters.filter((waiter) => waiter !== check);
        resolve(found);
      }
    };
    waiters.push(check);
    check();
  });
}

function check(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const uri = 'file:///tmp/pengu-smoke/main.pengu';
const text = [
  'summon std::libra',
  '',
  'valor = () -> Int',
  '    1',
  '',
  'grimoire',
  '    bind total = valor()',
  '    print(total)',
  '',
].join('\n');

const init = await request('initialize', {
  processId: process.pid,
  rootUri: 'file:///tmp/pengu-smoke',
  capabilities: {
    general: { positionEncodings: ['utf-16'] },
    textDocument: {
      completion: { completionItem: { snippetSupport: true } },
      inlayHint: { dynamicRegistration: false },
      codeLens: { dynamicRegistration: false },
    },
  },
});
const capabilities = init.result?.capabilities;
check(capabilities?.hoverProvider, 'initialize no anuncia hoverProvider');
check(capabilities?.inlayHintProvider, 'initialize no anuncia inlayHintProvider');
check(capabilities?.codeLensProvider, 'initialize no anuncia codeLensProvider');
check(capabilities?.semanticTokensProvider, 'initialize no anuncia semanticTokensProvider');
notify('initialized', {});

notify('textDocument/didOpen', {
  textDocument: { uri, languageId: 'pengu', version: 1, text },
});

const published = await waitFor(
  (message) => message.method === 'textDocument/publishDiagnostics' && message.params.uri === uri,
);
check(published.params.diagnostics.length === 0, 'el programa de humo tiene diagnósticos');
console.log(`diagnósticos: ${published.params.diagnostics.length}`);

const hover = await request('textDocument/hover', {
  textDocument: { uri },
  position: { line: 2, character: 1 },
});
const hovered = hover.result?.contents?.value ?? '';
check(hovered.includes('valor'), `hover inesperado: ${JSON.stringify(hover.result)}`);
console.log(`hover: ${hovered.replaceAll('\n', ' ').trim()}`);

const completion = await request('textDocument/completion', {
  textDocument: { uri },
  position: { line: 0, character: 17 },
});
const labels = (completion.result?.items ?? []).map((item) => item.label);
check(labels.includes('libra'), `completion de std:: no incluye libra: ${labels.join(', ')}`);
console.log(`completion: ${labels.length} módulos`);

const hints = await request('textDocument/inlayHint', {
  textDocument: { uri },
  range: { start: { line: 0, character: 0 }, end: { line: 8, character: 0 } },
});
const hintLabels = (hints.result ?? []).map((hint) => hint.label);
check(
  hintLabels.some((label) => label.includes('Int')),
  `sin hint de tipo: ${hintLabels.join(', ')}`,
);
console.log(`hints: ${hintLabels.join(' | ')}`);

const lens = await request('textDocument/codeLens', { textDocument: { uri } });
const runs = (lens.result ?? []).filter((item) => item.command?.title?.includes('Ejecutar'));
check(runs.length === 1, `sin lente de ejecución: ${JSON.stringify(lens.result)}`);
check(runs[0].range.start.line === 5, 'la lente de ejecución no cuelga de `grimoire`');
console.log(`lentes: ${(lens.result ?? []).length}`);

const tokens = await request('textDocument/semanticTokens/full', { textDocument: { uri } });
check((tokens.result?.data ?? []).length > 0, 'sin tokens semánticos');
console.log(`tokens: ${tokens.result.data.length / 5} bloques`);

const shutdown = await request('shutdown', null);
check(!shutdown.error, `shutdown falló: ${JSON.stringify(shutdown.error)}`);
notify('exit', null);
child.stdin.end();
console.log('ok');
