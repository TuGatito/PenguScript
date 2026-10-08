#!/usr/bin/env python3
"""The ``python -m pengu_lsp`` entry point (``pengu_lsp/__main__.py``).

``tests/lsp/test_lsp.py`` proves the protocol server works by *spawning* it, so the
entry point itself was never imported by the coverage run and its argument
parsing and shutdown handling were untested.  These tests drive ``main()``
in-process with a stand-in for the pygls server, which is what makes the
transport selection and the disconnect handling assertable without a client.

Contract under test:

* ``--stdio`` (the default) calls ``server.start_io()``;
* ``--tcp`` calls ``server.start_tcp(host, port)`` with the parsed values and
  the documented defaults (``127.0.0.1:2087``);
* a client disconnect (``BrokenPipeError`` / the PyInstaller-frozen "closed
  file" ``ValueError``) and ``Ctrl-C`` end the process quietly;
* any *other* transport error is reported on stderr and still does not turn
  into a traceback.
"""

from __future__ import annotations

import sys

import pytest

import pengu_lsp.__main__ as entry


class _FakeServer:
    """Records the transport call instead of opening one."""

    def __init__(self, raises=None):
        self.calls = []
        self._raises = raises

    def _record(self, *args):
        self.calls.append(args)
        if self._raises is not None:
            raise self._raises

    def start_io(self):
        self._record("io")

    def start_tcp(self, host, port):
        self._record("tcp", host, port)


def _main(monkeypatch, argv=(), server=None):
    server = server if server is not None else _FakeServer()
    monkeypatch.setattr(entry, "server", server)
    monkeypatch.setattr(sys, "argv", ["pengu-lsp", *argv])
    entry.main()
    return server


def test_plain_invocation_starts_the_stdio_transport(monkeypatch):
    assert _main(monkeypatch).calls == [("io",)]


def test_explicit_stdio_flag_starts_the_stdio_transport(monkeypatch):
    assert _main(monkeypatch, ["--stdio"]).calls == [("io",)]


def test_tcp_transport_uses_the_documented_defaults(monkeypatch):
    assert _main(monkeypatch, ["--tcp"]).calls == [("tcp", "127.0.0.1", 2087)]


def test_tcp_transport_passes_the_parsed_host_and_port(monkeypatch):
    server = _main(monkeypatch, ["--tcp", "--host", "0.0.0.0", "--port", "9111"])
    assert server.calls == [("tcp", "0.0.0.0", 9111)]


def test_tcp_announces_the_bind_address_on_stderr(monkeypatch, capsys):
    _main(monkeypatch, ["--tcp", "--port", "9111"])
    assert "0.0.0.0" not in capsys.readouterr().err
    _main(monkeypatch, ["--tcp", "--host", "0.0.0.0", "--port", "9111"])
    assert "0.0.0.0:9111" in capsys.readouterr().err


@pytest.mark.parametrize(
    "error",
    [
        BrokenPipeError("Broken pipe"),
        ConnectionResetError("Broken pipe"),
        ValueError("I/O operation on closed file"),
    ],
    ids=["broken-pipe", "connection-reset", "closed-file"],
)
def test_client_disconnect_shuts_down_quietly(monkeypatch, capsys, error):
    """A client going away is a normal exit, not an error to report."""
    _main(monkeypatch, server=_FakeServer(raises=error))
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "[LSP] Server stopped" not in captured.err


def test_keyboard_interrupt_shuts_down_quietly(monkeypatch, capsys):
    _main(monkeypatch, server=_FakeServer(raises=KeyboardInterrupt()))
    assert "[LSP] Server stopped" not in capsys.readouterr().err


def test_unexpected_transport_error_is_reported_without_a_traceback(monkeypatch, capsys):
    _main(monkeypatch, server=_FakeServer(raises=ValueError("bind failed")))
    assert "[LSP] Server stopped: bind failed" in capsys.readouterr().err
