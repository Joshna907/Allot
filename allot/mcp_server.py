from __future__ import annotations

import json
import sys
from typing import Any

from allot.execute import execute_payout
from allot.parser import parse_payout_book
from allot.paths import load_book
from allot.price import fetch_pair_price
from allot.rails import DEFAULT_SYMBOL, dry_run, liquidity, rail_status, symbol_rules
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
        "name": "binance_rail_status",
        "description": "Read the whole Binance Spot rail Allot depends on: pair status, exchange filters, last and rolling average price, 24h range, live book spread, server-clock drift, and B402 Bazaar discovery. Public data only — no API key, no KYC.",
        "inputSchema": {
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "Spot symbol, default USDCUSDT."}},
        },
    },
    {
        "name": "exchange_rules",
        "description": "Binance's own trading rules for the pair: TRADING status, tick size, lot step, minimum and maximum notional, permissions. These are the constraints Allot sizes payouts against.",
        "inputSchema": {
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "Spot symbol, default USDCUSDT."}},
        },
    },
    {
        "name": "check_liquidity",
        "description": "Walk the live Binance order book for a payout-sized conversion and report average fill, slippage in bps, and levels consumed. Read-only depth walk; no order is placed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "amount": {"type": "string", "description": "Size to convert, in the base asset."},
                "symbol": {"type": "string", "description": "Spot symbol, default USDCUSDT."},
            },
            "required": ["amount"],
        },
    },
    {
        "name": "preflight_payout",
        "description": "Run every Binance rule check over a payout sentence without issuing a receipt: pair status, per-leg minimum notional, lot step, price band against the rolling average, book depth, and clock sync.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "The sentence said at the counter."}},
            "required": ["text"],
        },
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
        "description": "Recompute the SHA-256 of a receipt and compare it to the printed hash. Pass a stored receipt_id, or the receipt object itself to check one that is no longer on disk.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "receipt_id": {"type": "string", "description": "Receipt id or receipt hash of a stored receipt."},
                "receipt": {"type": "object", "description": "A receipt JSON object, verified without touching disk."},
            },
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
    if name == "binance_rail_status":
        return _ok(rail_status(str(arguments.get("symbol") or DEFAULT_SYMBOL).upper()))
    if name == "exchange_rules":
        return _ok(symbol_rules(str(arguments.get("symbol") or DEFAULT_SYMBOL).upper()))
    if name == "check_liquidity":
        report = liquidity(str(arguments.get("symbol") or DEFAULT_SYMBOL).upper(), str(arguments.get("amount") or "0"))
        return _ok(report) if report.get("ok") else _err(str(report.get("error") or "Liquidity unavailable."))
    if name == "preflight_payout":
        return _ok(dry_run(str(arguments.get("text") or "")))
    if name == "list_receipts":
        return _ok(load_receipts())
    if name == "get_receipt":
        receipt = find_receipt(str(arguments.get("receipt_id") or ""))
        if receipt is None:
            return _err("No receipt with that id or hash.")
        return _ok(receipt)
    if name == "verify_receipt":
        pasted = arguments.get("receipt")
        if isinstance(pasted, dict):
            if not pasted.get("receipt_hash"):
                return _err("That receipt object carries no receipt_hash.")
            return _ok({**verify_receipt(pasted), "source": "pasted"})
        receipt = find_receipt(str(arguments.get("receipt_id") or ""))
        if receipt is None:
            return _err("No stored receipt with that id or hash. Pass the receipt object instead to verify it without disk.")
        return _ok({**verify_receipt(receipt), "source": "stored"})
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
