from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

TESTNET_TICKER = "https://testnet.binance.vision/api/v3/ticker/price"
MAINNET_TICKER = "https://api.binance.com/api/v3/ticker/price"
USER_AGENT = "AllotPayoutBook/0.1 (Binance Agent OS hackathon; testnet)"


def _get_json(url: str, timeout: float = 8.0) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_pair_price(symbol: str = "USDCUSDT") -> dict[str, Any]:
    """Live Binance price. Testnet first, mainnet public ticker as fallback."""
    errors: list[str] = []
    for source, base in (("binance-spot-testnet", TESTNET_TICKER), ("binance-spot-mainnet", MAINNET_TICKER)):
        url = f"{base}?symbol={symbol}"
        try:
            payload = _get_json(url)
            price = Decimal(str(payload["price"]))
            return {
                "ok": True,
                "symbol": symbol,
                "price": str(price),
                "source": source,
                "url": url,
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as exc:
            errors.append(f"{source}: {exc}")
    return {
        "ok": False,
        "symbol": symbol,
        "price": None,
        "source": None,
        "url": None,
        "error": "; ".join(errors) or "ticker unreachable",
    }
