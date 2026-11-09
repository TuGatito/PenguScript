#!/usr/bin/env python3
"""Cliente DAP mínimo para verificar `psc debug-adapter` de punta a punta.

No usa dependencias externas.  lanza el adapter por stdio, hace el handshake,
pone un breakpoint, inspecciona stack/scopes/variables, evalúa una expresión,
hace un step y termina.
"""
import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time


class Adapter:
    def __init__(self, command):
        self.proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.seq = 0
        self.messages = queue.Queue()
        threading.Thread(target=self._read_loop, daemon=True).start()
        threading.Thread(target=self._stderr_loop, daemon=True).start()

    def _read_loop(self):
        while True:
            headers = {}
            while True:
                line = self.proc.stdout.readline()
                if not line:
                    return
                if line in (b"\r\n", b"\n"):
                    break
                key, _, value = line.decode("ascii", "replace").partition(":")
                headers[key.strip().lower()] = value.strip()
            try:
                length = int(headers["content-length"])
            except (KeyError, ValueError):
                return
            body = self.proc.stdout.read(length)
            try:
                self.messages.put(json.loads(body))
            except json.JSONDecodeError:
                print("respuesta DAP inválida:", body[:500], file=sys.stderr)
                return

    def _stderr_loop(self):
        for line in self.proc.stderr:
            sys.stderr.write("adapter: " + line.decode("utf-8", "replace"))

    def request(self, command, arguments=None):
        self.seq += 1
        message = {"seq": self.seq, "type": "request", "command": command}
        if arguments is not None:
            message["arguments"] = arguments
        body = json.dumps(message).encode("utf-8")
        self.proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        self.proc.stdin.flush()
        return self.seq

    def wait(self, kind=None, command=None, timeout=20.0):
        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise TimeoutError("timeout esperando %s %s" % (kind, command))
            message = self.messages.get(timeout=remaining)
            if kind is not None and message.get("type") != kind:
                continue
            if command is not None and message.get("command") != command:
                continue
            return message

    def stop(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--psc", required=True)
    parser.add_argument("--program", required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()

    adapter = Adapter([args.psc, "debug-adapter"])
    try:
        adapter.request(
            "initialize",
            {
                "clientID": "pengu-test",
                "adapterID": "pengu",
                "linesStartAt1": True,
                "columnsStartAt1": True,
                "pathFormat": "path",
            },
        )
        init = adapter.wait("response", "initialize")
        check(init["success"], "initialize falló")
        check(
            init["body"].get("supportsConfigurationDoneRequest") is True,
            "falta supportsConfigurationDoneRequest",
        )
        event = adapter.wait("event")
        check(event["event"] == "initialized", "falta evento initialized")

        adapter.request(
            "launch",
            {
                "program": args.program,
                "cwd": os.path.dirname(args.source),
                "stopOnEntry": False,
                "args": [],
            },
        )
        check(adapter.wait("response", "launch")["success"], "launch falló")
        adapter.request("setExceptionBreakpoints", {"filters": []})
        check(
            adapter.wait("response", "setExceptionBreakpoints")["success"],
            "setExceptionBreakpoints falló",
        )
        adapter.request(
            "setBreakpoints",
            {
                "source": {"path": args.source},
                "breakpoints": [{"line": 7, "condition": "base == 100", "hitCondition": "1"}],
            },
        )
        bp = adapter.wait("response", "setBreakpoints")
        check(bp["body"]["breakpoints"][0]["verified"], "breakpoint no verificado")
        adapter.request("configurationDone", {})
        check(
            adapter.wait("response", "configurationDone")["success"],
            "configurationDone falló",
        )

        stopped = None
        for _ in range(40):
            event = adapter.wait("event")
            if event["event"] == "stopped":
                stopped = event
                break
        check(stopped is not None, "no se detuvo en el breakpoint")
        check(stopped["body"]["reason"] == "breakpoint", "razón de parada inesperada")

        adapter.request("threads", {})
        threads = adapter.wait("response", "threads")
        check(len(threads["body"]["threads"]) >= 1, "sin threads")

        adapter.request("stackTrace", {"threadId": 1})
        stack = adapter.wait("response", "stackTrace")
        frames = stack["body"]["stackFrames"]
        check(frames, "stack vacío")
        check(frames[0]["line"] == 7, "frame fuera de línea 7")
        check(
            frames[0]["source"]["path"].endswith("line_markers.pengu"),
            "source.path incorrecto",
        )

        frame_id = frames[0]["id"]
        adapter.request("scopes", {"frameId": frame_id})
        scopes = adapter.wait("response", "scopes")
        ref = scopes["body"]["scopes"][0]["variablesReference"]
        adapter.request("variables", {"variablesReference": ref})
        variables = adapter.wait("response", "variables")["body"]["variables"]
        values = {item["name"]: item["value"] for item in variables}
        check(values.get("base") == "100", "falta base=100 en variables")
        check(values.get("tax") == "21", "falta tax=21 en variables")

        adapter.request(
            "evaluate",
            {"expression": "base", "frameId": frame_id, "context": "watch"},
        )
        evaluated = adapter.wait("response", "evaluate")
        check(evaluated["body"]["result"] == "100", "evaluate(base) != 100")

        adapter.request("next", {"threadId": 1})
        check(adapter.wait("response", "next")["success"], "next falló")
        stepped = None
        for _ in range(20):
            event = adapter.wait("event")
            if event["event"] == "stopped":
                stepped = event
                break
        check(stepped is not None, "step sin stopped")

        adapter.request("continue", {"threadId": 1})
        check(adapter.wait("response", "continue")["success"], "continue falló")
        terminated = None
        for _ in range(40):
            event = adapter.wait("event")
            if event["event"] == "terminated":
                terminated = event
                break
        check(terminated is not None, "no llegó terminated")

        adapter.request("disconnect", {"terminateDebuggee": True})
        check(adapter.wait("response", "disconnect")["success"], "disconnect falló")
    finally:
        adapter.stop()

    print("OK debug DAP smoke")
    return 0


if __name__ == "__main__":
    sys.exit(main())
