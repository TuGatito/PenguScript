"""``std.jsonrpc`` — decoding errors, batches and framing."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_SRC = r'''
import std.spark
import std.json
import std.jsonrpc as rpc

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave fails with s as string, kind as rpc.JsonRpcErrorKind, name as string into void:
    var r as result of JsonRpcMessage to rpc.JsonRpcParseError is calling rpc.parse_message with s
    if r.is_ok:
        calling spark.println with "FAIL {name}: accepted"
    else:
        if r.error.kind != kind:
            calling spark.println with "FAIL {name}: wrong kind"
    banish r

weave main into int:
    calling fails with "", rpc.JsonRpcErrorKind.InvalidJson, "empty"
    calling fails with r"[]", rpc.JsonRpcErrorKind.NotAnObject, "array"
    calling fails with r"{}", rpc.JsonRpcErrorKind.MissingJsonrpcField, "missing jsonrpc"
    calling fails with r"""{"jsonrpc":"1.0"}""", rpc.JsonRpcErrorKind.WrongJsonrpcVersion, "version"
    calling fails with r"""{"jsonrpc":"2.0"}""", rpc.JsonRpcErrorKind.MissingMethod, "missing method"
    calling fails with r"""{"jsonrpc":"2.0","id":null}""", rpc.JsonRpcErrorKind.InvalidId, "null id"
    calling fails with r"""{"jsonrpc":"2.0","id":1.5}""", rpc.JsonRpcErrorKind.InvalidId, "float id"
    calling fails with r"""{"jsonrpc":"2.0","id":1,"result":1,"error":{"code":1,"message":"x"}}""", rpc.JsonRpcErrorKind.InvalidRequest, "both"
    calling fails with r"""{"jsonrpc":"2.0","id":1,"method":"m","params":1}""", rpc.JsonRpcErrorKind.InvalidParams, "params"
    calling fails with r"""{"jsonrpc":"2.0","id":1,"error":{"code":"x","message":"m"}}""", rpc.JsonRpcErrorKind.InvalidRequest, "error code"
    var e1 as rpc.JsonRpcError is calling rpc.error_parse
    calling eq_i with e1.code, rpc.PARSE_ERROR, "parse code"
    banish e1
    var e2 as rpc.JsonRpcError is calling rpc.error_invalid_request
    calling eq_i with e2.code, rpc.INVALID_REQUEST, "invalid code"
    banish e2
    var e3 as rpc.JsonRpcError is calling rpc.error_invalid_params with "d"
    calling eq_i with e3.code, rpc.INVALID_PARAMS, "params code"
    banish e3
    var e4 as rpc.JsonRpcError is calling rpc.error_internal with "d"
    calling eq_i with e4.code, rpc.INTERNAL_ERROR, "internal code"
    banish e4
    var e5 as rpc.JsonRpcError is calling rpc.error_server with -32000, "app", (maybe none)
    calling eq_i with e5.code, -32000, "server code"
    banish e5

    var br as result of list of JsonRpcMessage to rpc.JsonRpcParseError is calling rpc.parse_batch with r"""[{},{"jsonrpc":"2.0","method":"x"}]"""
    if br.is_ok:
        calling spark.println with "FAIL bad batch"
    else:
        calling eq_i with br.error.kind, rpc.JsonRpcErrorKind.MissingJsonrpcField, "batch first error"
    banish br

    var body as string is r"""{"jsonrpc":"2.0","method":"m"}"""
    var frame_text as string is "Content-Length: 30\r\n\r\n{body}"
    var items as result of list of rpc.JsonRpcBatchItem to rpc.JsonRpcParseError is calling rpc.parse_batch_items with r"""[{"jsonrpc":"2.0","method":"a"},{}]"""
    if items.is_ok:
        var its as list of rpc.JsonRpcBatchItem is calling rpc.take_batch_items with (sigil of items)
        calling eq_i with its.len, 2, "batch items"
        let first_item is its at 0
        if not first_item.message.is_present:
            calling spark.println with "FAIL batch item 0 message"
        let second_item is its at 1
        if not second_item.error.is_present:
            calling spark.println with "FAIL batch item 1 error"
        calling rpc.free_batch_items with its
    else:
        calling spark.println with "FAIL batch items outer"
        banish items

    var fr as result of rpc.FramedDecode to rpc.JsonRpcParseError is calling rpc.decode_framed_bytes with frame_text
    banish frame_text
    if fr.is_ok:
        var f as rpc.FramedDecode is fr.value
        if f.consumed <= 0:
            calling spark.println with "FAIL framed consumed"
        if f.message.is_present:
            var m as rpc.JsonRpcMessage is f.message.value
            var back as string is calling rpc.encode_message with m
            if back != body:
                calling spark.println with "FAIL framed body"
            banish back
        else:
            calling spark.println with "FAIL framed message"
    else:
        calling spark.println with "FAIL framed decode"
    banish fr
    banish body
    var bad as result of rpc.FramedDecode to rpc.JsonRpcParseError is calling rpc.decode_framed_bytes with "oops"
    if bad.is_ok:
        calling spark.println with "FAIL malformed frame"
    else:
        calling eq_i with bad.error.kind, rpc.JsonRpcErrorKind.FramingError, "framing error"
    banish bad
    calling spark.println with "DONE"
    return 0
'''


def test_jsonrpc_edge_cases(compile_and_run):
    out = compile_and_run(_SRC)
    assert "DONE" in out, out
    assert "FAIL" not in out, out
