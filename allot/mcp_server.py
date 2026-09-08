from __future__ import annotations

import json
import sys
from typing import Any

from allot.execute import execute_payout
from allot.parser import parse_payout_book
from allot.paths import load_book
from allot.price import fetch_pair_price
from allot.receipt import find_receipt, load_receipts, verify_receipt
from allot.x402 import probe_bazaar

TOOLS = [
    {
        "name": "get_payout_book",
        "description": "Return Allot's fixed payout roster, monthly schedule, currency pair, and spend/hold split.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "parse_payout_book",
        "description": "Turn a plain-English payout book into a validated Allot instruction. Recipients, pair, and monthly cadence are hardcoded.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "The sentence said at the counter."}},
            "required": ["text"],
        },
    },
    {
        "name": "execute_payout",
        "description": "Prepare x402 payment requirements and a hashed receipt. Does not transfer money, sign, or settle.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "The sentence said at the counter."}},
            "required": ["text"],
        },
    },
    {
        "name": "probe_rails",
        "description": "Ping Binance testnet USDCUSDT and B402 Bazaar. Does not need Agent OS OAuth or KYC.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_receipts",
        "description": "List stored Allot receipts from the JSON file on disk.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_receipt",
        "description": "Load one stored receipt by id or hash.",
        "inputSchema": {
            "type": "object",
            "properties": {"receipt_id": {"type": "string"}},
            "required": ["receipt_id"],
        },
    },
    {
        "name": "verify_receipt",
        "description": "Recompute the SHA-256 of a stored receipt and compare it to the printed hash.",
        "inputSchema": {
            "type": "object",
            "properties": {"receipt_id": {"type": "string", "description": "Receipt id or receipt hash."}},
            "required": ["receipt_id"],
        },
    },
]


def _ok(value: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(value, indent=2)}]}


def _err(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    arguments = arguments or {}
    if name == "get_payout_book":
        return _ok(load_book())
    if name == "parse_payout_book":
        return _ok(parse_payout_book(str(arguments.get("text") or "")))
    if name == "execute_payout":
        return _ok(execute_payout(str(arguments.get("text") or "")))
    if name == "probe_rails":
        return _ok(health())
    if name == "list_receipts":
        return _ok(load_receipts())
    if name == "get_receipt":
        receipt = find_receipt(str(arguments.get("receipt_id") or ""))
        if receipt is None:
            return _err("No receipt with that id or hash.")
        return _ok(receipt)
    if name == "verify_receipt":
        receipt = find_receipt(str(arguments.get("receipt_id") or ""))
        if receipt is None:
            return _err("No receipt with that id or hash.")
        return _ok(verify_receipt(receipt))
    return _err(f"Unknown tool: {name}")


def _read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode("utf-8").partition(":")
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length") or "0")
    if length <= 0:
        return None
    raw = sys.stdin.buffer.read(length)
    return json.loads(raw.decode("utf-8"))


def _write_message(payload: dict[str, Any]) -> None:
    raw = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def serve_stdio() -> None:
    while True:
        message = _read_message()
        if message is None:
            return
        method = message.get("method")
        req_id = message.get("id")
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "allot", "version": "0.1.0"},
            }
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = message.get("params") or {}
            result = call_tool(params.get("name"), params.get("arguments"))
        elif method == "ping":
            result = {}
        else:
            if req_id is None:
                continue
            _write_message({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method {method}"}})
            continue
        if req_id is None:
            continue
        _write_message({"jsonrpc": "2.0", "id": req_id, "result": result})


def health() -> dict[str, Any]:
    quote = fetch_pair_price()
    bazaar = probe_bazaar()
    book = load_book()
    return {
        "service": "allot",
        "book": {
            "pair": book["pair"],
            "schedule": book["schedule"],
            "gross_usd": book["gross_usd"],
            "recipients": [row["name"] for row in book["recipients"]],
        },
        "quote": quote,
        "bazaar": {
            "ok": bazaar.get("ok"),
            "listed_resources": bazaar.get("listed_resources"),
        },
        "rail": "x402 payment-requirements + binance-price + optional bazaar",
    }
