// Transporte JSON-RPC con cabeceras `Content-Length`.
//
// Acumula bytes de la entrada estándar y entrega mensajes ya
// deserializados. Sin clases: el estado vive en el cierre.

import type { JsonRpcMessage } from "./protocol.ts";

export interface Transport {
  send(message: unknown): void;
  on_message(handler: (message: JsonRpcMessage) => void): void;
  on_close(handler: () => void): void;
}

export interface FramedWriter {
  write(text: string): void;
}

function encode_frame(body: string): string {
  return `Content-Length: ${Buffer.byteLength(body, "utf8")}\r\n\r\n${body}`;
}

export function make_transport(reader: NodeJS.ReadableStream, writer: FramedWriter): Transport {
  let buffer = Buffer.alloc(0);
  let message_handler: ((message: JsonRpcMessage) => void) | undefined;
  let close_handler: (() => void) | undefined;

  function dispatch(body: string): void {
    let parsed: JsonRpcMessage;
    try {
      parsed = JSON.parse(body) as JsonRpcMessage;
    } catch {
      return;
    }
    if (message_handler !== undefined) message_handler(parsed);
  }

  function pump(): void {
    while (true) {
      const header_end = buffer.indexOf("\r\n\r\n");
      if (header_end < 0) return;

      const header = buffer.subarray(0, header_end).toString("ascii");
      const match = /content-length:\s*(\d+)/i.exec(header);
      if (match === null) {
        buffer = buffer.subarray(header_end + 4);
        continue;
      }

      const length = Number.parseInt(match[1] as string, 10);
      const start = header_end + 4;
      if (buffer.length < start + length) return;

      const body = buffer.subarray(start, start + length).toString("utf8");
      buffer = buffer.subarray(start + length);
      dispatch(body);
    }
  }

  reader.on("data", (chunk: Buffer) => {
    buffer = Buffer.concat([buffer, chunk]);
    pump();
  });
  reader.on("end", () => {
    if (close_handler !== undefined) close_handler();
  });

  return {
    send(message: unknown): void {
      writer.write(encode_frame(JSON.stringify(message)));
    },
    on_message(handler): void {
      message_handler = handler;
    },
    on_close(handler): void {
      close_handler = handler;
    },
  };
}
