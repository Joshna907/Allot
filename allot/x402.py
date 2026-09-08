from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any

from allot.price import USER_AGENT

BAZAAR_RESOURCES = "https://www.binance.com/bapi/ramp/v1/public/ramp/b402/bazaar/resources"
BSC_USDT = "0x55d398326f99059fF775485246999027B3197955"
BSC_MAINNET = "eip155:56"


def atomic_amount(usdt: Decimal, decimals: int = 18) -> str:
    quantized = (usdt * (Decimal(10) ** decimals)).to_integral_value()
    return str(quantized)


def probe_bazaar() -> dict[str, Any]:
    """Public B402 discovery — the x402 call that does not need merchant onboarding."""
    request = urllib.request.Request(
        BAZAAR_RESOURCES,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "url": BAZAAR_RESOURCES}

    items = (body.get("data") or {}).get("items") or []
    sample = None
    if items:
        first = items[0]
        sample = {
            "resource": first.get("resource"),
            "description": (first.get("description") or "")[:160],
            "x402Version": first.get("x402Version"),
            "accepts": first.get("accepts"),
        }
    return {
        "ok": body.get("code") == "000000",
        "url": BAZAAR_RESOURCES,
        "listed_resources": len(items),
        "sample": sample,
        "note": "B402 Bazaar is public discovery. /papi/v2/b402/settle needs a merchant clientId.",
    }


def payment_required(
    leg: dict[str, Any],
    usdt: Decimal,
    instruction: dict[str, Any],
    *,
    receipt_id: str,
    base_url: str,
) -> dict[str, Any]:
    asset = instruction["asset"]
    pay_to = leg["pay_to"] or "merchant"
    amount = atomic_amount(usdt, int(asset["decimals"]))
    return {
        "x402Version": 2,
        "error": "PAYMENT-SIGNATURE header is required",
        "resource": {
            "url": f"{base_url.rstrip('/')}/payout/{receipt_id}/{leg['recipient_id']}",
            "description": f"Monthly spend leg for {leg['name']} in {leg['city']}",
            "mimeType": "application/json",
            "serviceName": "Allot payout book",
            "tags": ["payout", "x402", "binance-agent-os"],
        },
        "accepts": [
            {
                "scheme": "exact",
                "network": instruction.get("network") or BSC_MAINNET,
                "amount": amount,
                "asset": asset.get("address") or BSC_USDT,
                "payTo": pay_to,
                "maxTimeoutSeconds": 60,
                "extra": {
                    "name": asset.get("name") or "USDT",
                    "version": "1",
                    "assetTransferMethod": "permit2-exact",
                },
            }
        ],
        "extensions": {
            "allot": {
                "role": leg["role"],
                "usd": leg["usd"],
                "city": leg["city"],
            }
        },
    }


def encode_payment_required(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")
