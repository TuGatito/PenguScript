#!/usr/bin/env python3
import json
import subprocess
import sys
import time

def send_message(proc, msg):
    """Envía un mensaje JSON con el encabezado Content-Length."""
    data = json.dumps(msg)
    content = f"Content-Length: {len(data)}\r\n\r\n{data}"
    proc.stdin.write(content)
    proc.stdin.flush()

def read_response(proc):
    """Lee una respuesta del servidor (encabezado + JSON)."""
    line = proc.stdout.readline()
    if not line:
        return None
    # Leer el Content-Length
    if line.startswith("Content-Length:"):
        length = int(line.split(":")[1].strip())
        # Leer la línea vacía
        proc.stdout.readline()
        # Leer el cuerpo
        body = proc.stdout.read(length)
        return json.loads(body)
    return None

def main():
    # Iniciar el servidor LSP (usar python -m pengu_lsp o pengu lsp)
    # Asegúrate de que el módulo esté accesible
    cmd = [sys.executable, "-m", "pengu_lsp", "--stdio"]
    # Si prefieres usar el ejecutable empaquetado:
    # cmd = ["pengu", "lsp", "--stdio"]

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=1  # Línea por línea
    )

    # 1. Inicialización
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "processId": None,
            "rootUri": "file:///tmp",
            "capabilities": {}
        }
    }
    send_message(proc, init_msg)
    resp = read_response(proc)
    print("Initialize response:", resp)

    # 2. Notificación didOpen con un archivo que tiene un error
    open_msg = {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": "file:///test.pengu",
                "languageId": "pengus",
                "version": 1,
                "text": "weave main into void:\n  var x as int is 'error'\n"
            }
        }
    }
    send_message(proc, open_msg)

    # 3. Esperar posibles diagnósticos (hasta que el servidor cierre o no haya más)
    # El servidor enviará notificaciones publishDiagnostics.
    # Vamos a leer durante unos segundos.
    timeout = 5  # segundos
    start = time.time()
    while time.time() - start < timeout:
        # Intentar leer una línea (podría ser un encabezado)
        line = proc.stdout.readline()
        if not line:
            break
        if line.startswith("Content-Length:"):
            length = int(line.split(":")[1].strip())
            proc.stdout.readline()  # línea vacía
            body = proc.stdout.read(length)
            try:
                msg = json.loads(body)
                if "method" in msg and msg["method"] == "textDocument/publishDiagnostics":
                    print("Diagnóstico recibido:", json.dumps(msg, indent=2))
                else:
                    print("Otro mensaje:", json.dumps(msg, indent=2))
            except Exception as e:
                print("Error al parsear:", e)
        else:
            # Podría ser una respuesta de error, etc.
            print("Línea no esperada:", line.strip())

    # Terminar proceso
    proc.terminate()
    proc.wait()

if __name__ == "__main__":
    main()