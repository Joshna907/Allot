"""Binance Spot rail: the public market data Allot sizes a payout against.

Every call is public — no API key, no KYC, no merchant onboarding. Testnet
first, then the public mainnet endpoint, matching allot.price. Nothing here
places an order; Allot reads Binance's own rules and reports them.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from allot.price import USER_AGENT

TESTNET = "https://testnet.binance.vision/api/v3"
MAINNET = "https://api.binance.com/api/v3"
SOURCES = (("binance-spot-testnet", TESTNET), ("binance-spot-mainnet", MAINNET))

# exchangeInfo changes rarely; a receipt should not re-fetch it on every click.
_CACHE_TTL = 600.0
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()


def _get(path: str, timeout: float = 8.0) -> dict[str, Any]:
    """Fetch one path from testnet, falling back to the public mainnet endpoint."""
    errors: list[str] = []
    for source, base in SOURCES:
        url = f"{base}{path}"
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return {"ok": True, "source": source, "url": url, "payload": payload}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{source}: {exc}")
    return {"ok": False, "error": "; ".join(errors), "url": f"{SOURCES[0][1]}{path}"}


def _cached(key: str, loader: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    now = time.monotonic()
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < _CACHE_TTL:
            return hit[1]
    value = loader()
    if value.get("ok"):
        with _CACHE_LOCK:
            _CACHE[key] = (now, value)
    return value


def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def server_time() -> dict[str, Any]:
    """Binance server clock, and how far this host has drifted from it."""
    local_before = time.time()
    result = _get("/time", timeout=6.0)
    local_after = time.time()
    if not result["ok"]:
        return {"ok": False, "error": result["error"], "url": result["url"]}
    binance_ms = int(result["payload"]["serverTime"])
    local_ms = int(((local_before + local_after) / 2) * 1000)
    return {
        "ok": True,
        "source": result["source"],
        "url": result["url"],
        "binance_time_ms": binance_ms,
        "binance_time": datetime.fromtimestamp(binance_ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "local_time_ms": local_ms,
        "drift_ms": local_ms - binance_ms,
        "round_trip_ms": int((local_after - local_before) * 1000),
    }


def exchange_rules(symbol: str = "USDCUSDT") -> dict[str, Any]:
    """The symbol's live trading rules: status, tick, lot step, notional bounds."""

    def load() -> dict[str, Any]:
        result = _get(f"/exchangeInfo?symbol={symbol}", timeout=10.0)
        if not result["ok"]:
            return {"ok": False, "symbol": symbol, "error": result["error"], "url": result["url"]}
        symbols = result["payload"].get("symbols") or []
        if not symbols:
            return {"ok": False, "symbol": symbol, "error": "symbol not listed", "url": result["url"]}
        entry = symbols[0]
        filters = {row["filterType"]: row for row in entry.get("filters") or []}
        price_filter = filters.get("PRICE_FILTER") or {}
        lot = filters.get("LOT_SIZE") or {}
        notional = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL") or {}
        permissions = entry.get("permissions") or [item for group in entry.get("permissionSets") or [] for item in group]
        return {
            "ok": True,
            "symbol": entry.get("symbol", symbol),
            "source": result["source"],
            "url": result["url"],
            "status": entry.get("status"),
            "tradeable": entry.get("status") == "TRADING",
            "base_asset": entry.get("baseAsset"),
            "quote_asset": entry.get("quoteAsset"),
            "base_precision": entry.get("baseAssetPrecision"),
            "quote_precision": entry.get("quoteAssetPrecision"),
            "permissions": permissions,
            "order_types": entry.get("orderTypes") or [],
            "tick_size": price_filter.get("tickSize"),
            "min_price": price_filter.get("minPrice"),
            "max_price": price_filter.get("maxPrice"),
            "step_size": lot.get("stepSize"),
            "min_qty": lot.get("minQty"),
            "max_qty": lot.get("maxQty"),
            "min_notional": notional.get("minNotional"),
            "max_notional": notional.get("maxNotional"),
            "avg_price_mins": notional.get("avgPriceMins") or (filters.get("PERCENT_PRICE_BY_SIDE") or {}).get("avgPriceMins"),
            "fetched_at": _utc(),
        }

    return _cached(f"rules:{symbol}", load)


def average_price(symbol: str = "USDCUSDT") -> dict[str, Any]:
    """The rolling average Binance itself uses for its notional and price-band filters."""
    result = _get(f"/avgPrice?symbol={symbol}", timeout=8.0)
    if not result["ok"]:
        return {"ok": False, "symbol": symbol, "error": result["error"], "url": result["url"]}
    payload = result["payload"]
    return {
        "ok": True,
        "symbol": symbol,
        "source": result["source"],
        "url": result["url"],
        "price": str(Decimal(str(payload["price"]))),
        "window_minutes": payload.get("mins"),
        "fetched_at": _utc(),
    }


def day_stats(symbol: str = "USDCUSDT") -> dict[str, Any]:
    """24h range and turnover — context for whether the quote is an outlier."""
    result = _get(f"/ticker/24hr?symbol={symbol}", timeout=8.0)
    if not result["ok"]:
        return {"ok": False, "symbol": symbol, "error": result["error"], "url": result["url"]}
    payload = result["payload"]
    return {
        "ok": True,
        "symbol": symbol,
        "source": result["source"],
        "url": result["url"],
        "last_price": payload.get("lastPrice"),
        "high_price": payload.get("highPrice"),
        "low_price": payload.get("lowPrice"),
        "weighted_avg_price": payload.get("weightedAvgPrice"),
        "price_change_percent": payload.get("priceChangePercent"),
        "base_volume": payload.get("volume"),
        "quote_volume": payload.get("quoteVolume"),
        "trades": payload.get("count"),
        "fetched_at": _utc(),
    }


def order_book(symbol: str = "USDCUSDT", limit: int = 100) -> dict[str, Any]:
    """Top of book plus the raw levels, so a payout can be walked against real depth."""
    result = _get(f"/depth?symbol={symbol}&limit={limit}", timeout=8.0)
    if not result["ok"]:
        return {"ok": False, "symbol": symbol, "error": result["error"], "url": result["url"]}
    payload = result["payload"]
    bids = [(Decimal(price), Decimal(qty)) for price, qty in payload.get("bids") or []]
    asks = [(Decimal(price), Decimal(qty)) for price, qty in payload.get("asks") or []]
    if not bids or not asks:
        return {"ok": False, "symbol": symbol, "error": "empty book", "url": result["url"]}
    best_bid, best_ask = bids[0][0], asks[0][0]
    mid = (best_bid + best_ask) / 2
    return {
        "ok": True,
        "symbol": symbol,
        "source": result["source"],
        "url": result["url"],
        "best_bid": str(best_bid),
        "best_ask": str(best_ask),
        "spread_bps": str(_bps(best_ask - best_bid, mid)),
        "bid_depth_base": str(sum(qty for _, qty in bids)),
        "ask_depth_base": str(sum(qty for _, qty in asks)),
        "levels": len(bids),
        "bids": [(str(price), str(qty)) for price, qty in bids[:5]],
        "fetched_at": _utc(),
        "_bids": bids,
    }


def _bps(difference: Decimal, reference: Decimal) -> Decimal:
    if not reference:
        return Decimal("0")
    return (difference / reference * Decimal("10000")).quantize(Decimal("0.01"))


def fill_estimate(book: dict[str, Any], base_quantity: Decimal) -> dict[str, Any]:
    """Walk the bid side selling `base_quantity` of the base asset. No order is placed."""
    if not book.get("ok"):
        return {"ok": False, "error": book.get("error", "no book")}
    bids = book.get("_bids") or []
    if not bids:
        return {"ok": False, "error": "no bid levels"}
    best_bid = bids[0][0]
    remaining = base_quantity
    proceeds = Decimal("0")
    levels_used = 0
    for price, quantity in bids:
        if remaining <= 0:
            break
        take = min(remaining, quantity)
        proceeds += take * price
        remaining -= take
        levels_used += 1
    filled = base_quantity - remaining
    if filled <= 0:
        return {"ok": False, "error": "book too thin to price this size"}
    average = proceeds / filled
    return {
        "ok": True,
        "side": "sell base into bids",
        "requested_base": str(base_quantity),
        "filled_base": str(filled),
        "fully_filled": remaining <= 0,
        "best_bid": str(best_bid),
        "average_fill_price": str(average.quantize(Decimal("0.00000001"))),
        "quote_proceeds": str(proceeds.quantize(Decimal("0.00000001"))),
        "slippage_bps": str(_bps(best_bid - average, best_bid)),
        "levels_consumed": levels_used,
        "book_source": book.get("source"),
    }


def market_snapshot(symbol: str = "USDCUSDT") -> dict[str, Any]:
    """Every public rail read Allot uses, fetched in parallel so a receipt stays quick."""
    jobs = {
        "server_time": server_time,
        "rules": lambda: exchange_rules(symbol),
        "average_price": lambda: average_price(symbol),
        "day_stats": lambda: day_stats(symbol),
        "book": lambda: order_book(symbol),
    }
    snapshot: dict[str, Any] = {"symbol": symbol, "fetched_at": _utc()}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {name: pool.submit(job) for name, job in jobs.items()}
        for name, future in futures.items():
            try:
                snapshot[name] = future.result()
            except Exception as exc:  # a rail outage is reported, never raised
                snapshot[name] = {"ok": False, "error": str(exc)}
    reads = [snapshot[name] for name in jobs]
    snapshot["reachable"] = sum(1 for read in reads if read.get("ok"))
    snapshot["reads"] = len(reads)
    return snapshot


def public_view(snapshot: dict[str, Any]) -> dict[str, Any]:
    """The snapshot minus internal book levels, safe to serialise into a receipt."""
    view = dict(snapshot)
    book = view.get("book")
    if isinstance(book, dict):
        view["book"] = {key: value for key, value in book.items() if not key.startswith("_")}
    return view
