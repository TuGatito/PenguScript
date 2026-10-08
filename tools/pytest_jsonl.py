#!/usr/bin/env python3
"""A pytest plugin that writes one JSON object per test to a JSONL file.

Selected with ``-p pytest_jsonl`` and ``PENGU_SELFTEST_JSONL=<path>``.

Why a plugin and not a stdout format: pytest owns stdout, so a test cannot
reliably print machine-readable lines from inside a run -- they are captured,
buffered and re-emitted in whatever order a failure needs. A plugin sees every
test's outcome and duration directly, for *all* tests (unit, integration and
conformance), and writes them somewhere a caller can read afterwards.

One line per test, emitted when its ``teardown`` report arrives (the last phase
of every test)::

    {"name": "tests/test_lexer.py::test_bom", "status": "pass", "duration_ms": 3.1}
    {"name": "tests/test_x.py::test_y", "status": "fail", "duration_ms": 12.0,
     "message": "AssertionError: ..."}

``status`` is one of ``pass``, ``fail``, ``skip``, ``xfail``, ``xpass``.
"""
from __future__ import annotations

import json
import os
import time

_PATH_ENV = "PENGU_SELFTEST_JSONL"

_records: dict = {}
_started: dict = {}
_write = True


def pytest_configure(config):
    """Decide who owns the file.

    Under ``pytest-xdist`` the controller also receives a ``logreport`` for every
    test a worker ran, so writing unconditionally records each test twice -- once
    by the worker and once by the controller. Only a worker writes when the run is
    actually distributed; otherwise this single process writes.

    Detecting "distributed" matters: xdist *installed* is not the same as xdist
    *used*, and ``hasplugin("xdist")`` is true even for a plain serial run, so
    keying on it would silently produce an empty file.
    """
    global _write
    is_worker = hasattr(config, "workerinput")
    numprocesses = getattr(config.option, "numprocesses", None)
    distributing = numprocesses not in (None, 0, "0")
    _write = is_worker or not distributing


def _status(rec: dict) -> str:
    if rec.get("xpass"):
        return "xpass"
    if rec.get("xfail"):
        return "xfail"
    if rec.get("setup") == "failed" or rec.get("call") == "failed":
        return "fail"
    if rec.get("setup") == "skipped" or rec.get("call") == "skipped":
        return "skip"
    return "pass"


def pytest_runtest_logstart(nodeid, location):
    _started[nodeid] = time.perf_counter()


def pytest_runtest_logreport(report):
    nodeid = report.nodeid
    rec = _records.setdefault(
        nodeid,
        {"setup": None, "call": None, "teardown": None, "duration": 0.0,
         "message": "", "xfail": False, "xpass": False},
    )
    rec[report.when] = report.outcome
    rec["duration"] += float(report.duration or 0.0)

    if report.outcome == "failed" and not rec["message"]:
        rec["message"] = str(report.longrepr)[:4000] if report.longrepr else ""
    wasxfail = getattr(report, "wasxfail", None)
    if wasxfail is not None:
        # xfail/xpass are reported as skipped/failed with `wasxfail` set; the
        # distinction only exists on the `call` phase.
        if report.when == "call":
            if report.outcome == "skipped":
                rec["xfail"] = True
            elif report.outcome == "failed":
                rec["xpass"] = True
                rec["message"] = str(wasxfail)[:4000]

    if report.when != "teardown":
        return

    path = os.environ.get(_PATH_ENV)
    if not path or not _write:
        return
    started = _started.pop(nodeid, None)
    duration_ms = (time.perf_counter() - started) * 1000.0 if started else rec["duration"] * 1000.0
    line = {"name": nodeid, "status": _status(rec), "duration_ms": round(duration_ms, 3)}
    if line["status"] in ("fail", "xpass") and rec["message"]:
        line["message"] = rec["message"]
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError:
        pass
