from __future__ import annotations

from decimal import Decimal
from typing import Any

from allot.config import public_base_url
from allot.money import legs_from_instruction, usd
from allot.parser import parse_payout_book
from allot.price import fetch_pair_price
from allot.receipt import attach_hash, new_receipt_id, now_utc, save_receipt, sha256_hex, usdt_from_usd
from allot.x402 import encode_payment_required, payment_required, probe_bazaar

WHAT_IS_REAL = [
    "Binance USDCUSDT last price (testnet, then mainnet public ticker).",
    "x402 v2 PaymentRequired payloads for each spend leg (BSC USDT, exact scheme).",
    "HTTP 402 endpoints that return those requirements. Settlement is disabled.",
]

WHAT_REMAINS = [
    "User confirmation, signature, and on-chain settlement. Allot never signs or broadcasts.",
    "Binance B402 merchant /papi/v2/b402/settle. That needs partner credentials Allot does not have.",
    "Agentic Wallet preview (baw x402-payment preview) is optional and local-only. Not run in this hosted demo.",
]


def execute_payout(instruction: dict[str, Any] | str) -> dict[str, Any]:
    """Prepare payment requirements and a hashed receipt. Does not transfer money."""
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
            "retryable": True,
        }

    bazaar = probe_bazaar()
    price = Decimal(quote["price"])
    spend_legs, totals = legs_from_instruction(instruction)
    issued = now_utc()
    receipt_id = new_receipt_id(issued)
    base_url = public_base_url()

    legs: list[dict[str, Any]] = []
    for leg in spend_legs:
        amount_usdt = usdt_from_usd(leg["usd"], price)
        record: dict[str, Any] = {
            **leg,
            "usdt": str(amount_usdt),
            "network": instruction.get("network"),
            "asset": instruction.get("asset"),
            "status": "held" if leg["role"] == "hold" else "payment-required",
        }
        if leg["role"] == "spend":
            envelope = payment_required(
                leg,
                amount_usdt,
                instruction,
                receipt_id=receipt_id,
                base_url=base_url,
            )
            record["x402"] = {
                "payment_required": envelope,
                "payment_required_header": encode_payment_required(envelope),
            }
            record["payout_url"] = envelope["resource"]["url"]
            record["leg_hash"] = sha256_hex(record["x402"]["payment_required"])
        else:
            record["x402"] = None
            record["payout_url"] = None
            record["leg_hash"] = sha256_hex({"role": "hold", "usd": leg["usd"], "usdt": str(amount_usdt)})
        legs.append(record)

    receipt = {
        "ok": True,
        "receipt_id": receipt_id,
        "issued_at": issued.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "demo-preview",
        "status": "payment-requirements-created",
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
        "evidence": {
            "binance_price": True,
            "bazaar_discovery": bool(bazaar.get("ok")),
            "wallet_preview": "not-run",
        },
        "pending": "User confirmation, signature and on-chain settlement",
        "what_is_real": WHAT_IS_REAL,
        "what_remains": WHAT_REMAINS,
    }
    attach_hash(receipt)
    save_receipt(receipt)
    return receipt
