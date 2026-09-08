"""Composed Binance rail views shared by the HTTP API and the MCP tools."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from allot.binance import exchange_rules, fill_estimate, market_snapshot, order_book, public_view
from allot.money import legs_from_instruction
from allot.parser import parse_payout_book
from allot.preflight import preflight
from allot.price import fetch_pair_price
from allot.receipt import usdt_from_usd
from allot.x402 import probe_bazaar

DEFAULT_SYMBOL = "USDCUSDT"


def rail_status(symbol: str = DEFAULT_SYMBOL) -> dict[str, Any]:
    """Everything Allot reads from Binance before it prepares anything."""
    snapshot = market_snapshot(symbol)
    bazaar = probe_bazaar()
    rules = snapshot.get("rules") or {}
    book = snapshot.get("book") or {}
    return {
        "ok": snapshot.get("reachable", 0) > 0,
        "symbol": symbol,
        "reads": f"{snapshot.get('reachable')}/{snapshot.get('reads')} Binance endpoints reachable",
        "tradeable": bool(rules.get("tradeable")),
        "summary": {
            "status": rules.get("status"),
            "last_price": (snapshot.get("day_stats") or {}).get("last_price"),
            "average_price": (snapshot.get("average_price") or {}).get("price"),
            "spread_bps": book.get("spread_bps"),
            "min_notional": rules.get("min_notional"),
            "step_size": rules.get("step_size"),
            "clock_drift_ms": (snapshot.get("server_time") or {}).get("drift_ms"),
        },
        "binance": public_view(snapshot),
        "bazaar": {
            "ok": bazaar.get("ok"),
            "listed_resources": bazaar.get("listed_resources"),
            "url": bazaar.get("url"),
            "sample_resource": (bazaar.get("sample") or {}).get("resource"),
            "note": bazaar.get("note") or bazaar.get("error"),
        },
        "signing": "disabled — Allot reads Binance, it does not trade or settle",
    }


def symbol_rules(symbol: str = DEFAULT_SYMBOL) -> dict[str, Any]:
    return exchange_rules(symbol)


def liquidity(symbol: str = DEFAULT_SYMBOL, amount: str | float | Decimal = "320") -> dict[str, Any]:
    """What converting this size would actually cost against the live book."""
    try:
        size = Decimal(str(amount))
    except (ArithmeticError, TypeError, ValueError):
        return {"ok": False, "error": "Amount must be a number."}
    if size <= 0:
        return {"ok": False, "error": "Amount must be greater than zero."}
    book = order_book(symbol)
    if not book.get("ok"):
        return {"ok": False, "symbol": symbol, "error": book.get("error", "order book unavailable")}
    estimate = fill_estimate(book, size)
    return {
        "ok": estimate.get("ok", False),
        "symbol": symbol,
        "requested": str(size),
        "book": public_view({"book": book})["book"],
        "estimate": estimate,
        "note": "Depth walk only. No order is placed and no funds move.",
    }


def dry_run(text: str, symbol: str | None = None) -> dict[str, Any]:
    """Run every Binance rule check over a sentence without issuing a receipt."""
    instruction = parse_payout_book(text)
    if not instruction.get("valid"):
        return {"ok": False, "errors": instruction.get("errors") or ["Instruction is not valid."], "instruction": instruction}
    pair = symbol or instruction["pair"]
    quote = fetch_pair_price(pair)
    if not quote.get("ok"):
        return {"ok": False, "errors": [f"Could not price {pair}: {quote.get('error')}"], "quote": quote, "retryable": True}
    price = Decimal(quote["price"])
    spend_legs, totals = legs_from_instruction(instruction)
    legs = [{**leg, "usdt": str(usdt_from_usd(leg["usd"], price))} for leg in spend_legs]
    report = preflight(instruction, legs, quote)
    return {
        "ok": report["ok"],
        "symbol": pair,
        "quote": quote,
        "totals": totals,
        "legs": legs,
        "preflight": report,
        "receipt_issued": False,
        "note": "Preflight only. Nothing was stored, signed, or sent.",
    }
