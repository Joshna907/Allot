from __future__ import annotations

from decimal import Decimal
from typing import Any

from allot.money import legs_from_instruction, usd
from allot.parser import parse_payout_book
from allot.price import fetch_pair_price
from allot.receipt import attach_hash, new_receipt_id, now_utc, save_receipt, sha256_hex, usdt_from_usd
from allot.x402 import encode_payment_required, payment_required, probe_bazaar

WHAT_IS_REAL = [
    "Binance USDCUSDT last price (testnet, then mainnet public ticker).",
    "B402 Bazaar public discovery — live x402 catalog on Binance.",
    "x402 v2 PaymentRequired envelopes for each spend leg (BSC USDT, exact scheme).",
]

WHAT_IS_NOT = [
    "On-chain B402 /papi/v2/b402/settle. That endpoint needs a merchant clientId, RSA key, and a base URL Binance hands out after onboarding.",
    "Binance MCP withdrawals. Agent OS MCP can price and trade inside an Agentic sub-account. It cannot send to an external address.",
    "Live Binance Pay. This run is Demo Trading / testnet.",
]


def execute_payout(instruction: dict[str, Any] | str) -> dict[str, Any]:
    """Take a payout instruction (or a sentence), execute the legs, return a receipt."""
    if isinstance(instruction, str):
        instruction = parse_payout_book(instruction)
    if not instruction.get("valid", True):
        return {
            "ok": False,
            "errors": instruction.get("errors") or ["Instruction is not valid."],
            "instruction": instruction,
        }

    quote = fetch_pair_price(instruction["pair"])
    if not quote.get("ok"):
        return {
            "ok": False,
            "errors": [f"Could not price {instruction['pair']}: {quote.get('error')}"],
            "instruction": instruction,
            "quote": quote,
        }

    bazaar = probe_bazaar()
    price = Decimal(quote["price"])
    spend_legs, totals = legs_from_instruction(instruction)
    issued = now_utc()
    receipt_id = new_receipt_id(issued)

    legs: list[dict[str, Any]] = []
    for leg in spend_legs:
        amount_usdt = usdt_from_usd(leg["usd"], price)
        record: dict[str, Any] = {
            **leg,
            "usdt": str(amount_usdt),
            "status": "held" if leg["role"] == "hold" else "settled-demo",
        }
        if leg["role"] == "spend":
            envelope = payment_required(leg, amount_usdt, instruction)
            record["x402"] = {
                "payment_required": envelope,
                "payment_required_header": encode_payment_required(envelope),
            }
            record["leg_hash"] = sha256_hex(record["x402"]["payment_required"])
        else:
            record["x402"] = None
            record["leg_hash"] = sha256_hex({"role": "hold", "usd": leg["usd"], "usdt": str(amount_usdt)})
        legs.append(record)

    receipt = {
        "ok": True,
        "receipt_id": receipt_id,
        "issued_at": issued.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "demo-testnet",
        "rail": "x402-envelope + b402-bazaar + binance-price + demo-settle",
        "instruction": {
            "source_text": instruction.get("source_text"),
            "gross_usd": instruction["gross_usd"],
            "schedule": instruction["schedule"],
            "pair": instruction["pair"],
            "spend_bps": instruction["spend_bps"],
            "hold_bps": instruction["hold_bps"],
            "warnings": instruction.get("warnings") or [],
        },
        "quote": quote,
        "bazaar": {
            "ok": bazaar.get("ok"),
            "listed_resources": bazaar.get("listed_resources"),
            "url": bazaar.get("url"),
            "sample_resource": (bazaar.get("sample") or {}).get("resource"),
            "note": bazaar.get("note") or bazaar.get("error"),
        },
        "legs": legs,
        "totals": {
            **totals,
            "spend_usdt": str(usd(sum((Decimal(leg["usdt"]) for leg in legs if leg["role"] == "spend"), Decimal("0")))),
            "hold_usdt": next(leg["usdt"] for leg in legs if leg["role"] == "hold"),
        },
        "pending": "On-chain settle. Envelopes are ready; B402 merchant settle is not onboarded.",
        "what_is_real": WHAT_IS_REAL,
        "what_is_not": WHAT_IS_NOT,
    }
    attach_hash(receipt)
    save_receipt(receipt)
    return receipt
