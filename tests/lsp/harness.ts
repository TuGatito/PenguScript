// Cliente mínimo del servidor LSP por stdio, para las pruebas de integración.

import { spawn } from "node:child_process";
import type { ChildProcess } from "node:child_process";

export interface RpcMessage {
  readonly id?: number | string;
  readonly method?: string;
  readonly result?: unknown;
  readonly params?: unknown;
}

export interface TestServer {
  readonly child: ChildProcess;
  readonly messages: RpcMessage[];
  send: (message: unknown) => void;
}

const root = new URL("../..", import.meta.url).pathname;
const children: ChildProcess[] = [];

export function stop_all(): void {
  for (const child of children) child.kill();
}

export function start_server(): TestServer {
  const child = spawn("bun", ["run", "src/main.ts", "lsp"], { cwd: root });
  children.push(child);
  const messages: RpcMessage[] = [];
  let buffer = Buffer.alloc(0);

  child.stdout!.on("data", (chunk: Buffer) => {
    buffer = Buffer.concat([buffer, chunk]);
    while (true) {
      const header_end = buffer.indexOf("\r\n\r\n");
      if (header_end < 0) break;
      const header = buffer.subarray(0, header_end).toString("ascii");
      const match = /content-length:\s*(\d+)/i.exec(header);
      if (match === null) {
        buffer = buffer.subarray(header_end + 4);
        continue;
      }
      const length = Number.parseInt(match[1] as string, 10);
      const start = header_end + 4;
      if (buffer.length < start + length) break;
      messages.push(JSON.parse(buffer.subarray(start, start + length).toString("utf8")) as RpcMessage);
      buffer = buffer.subarray(start + length);
    }
  });

  return {
    child,
    messages,
    send(message: unknown): void {
      const body = JSON.stringify(message);
      child.stdin!.write(`Content-Length: ${Buffer.byteLength(body)}\r\n\r\n${body}`);
    },
  };
}

export function wait_for(
  messages: RpcMessage[],
  predicate: (message: RpcMessage) => boolean,
  timeout_ms = 8000,
): Promise<RpcMessage> {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeout_ms;
    const timer = setInterval(() => {
      const found = messages.find(predicate);
      if (found !== undefined) {
        clearInterval(timer);
        resolve(found);
      } else if (Date.now() > deadline) {
        clearInterval(timer);
        reject(new Error("tiempo de espera agotado"));
      }
    }, 20);
  });
}
