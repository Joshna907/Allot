"""Check a prepared payout against Binance's own live trading rules.

Allot never places an order. These checks answer a different question: if the
sender took this allocation to Binance Spot, would the exchange accept it, and
what would the conversion actually cost? Every answer comes from public data.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from allot.binance import fill_estimate, market_snapshot

# Tolerances Allot reports on. They gate warnings, never the preparation itself.
PRICE_DRIFT_WARN_BPS = Decimal("50")
SLIPPAGE_WARN_BPS = Decimal("25")
CLOCK_DRIFT_WARN_MS = 5000


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _check(name: str, title: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"check": name, "title": title, "status": status, "detail": detail, **extra}


def _quantize_down(quantity: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return quantity
    return (quantity // step) * step


def preflight(instruction: dict[str, Any], legs: list[dict[str, Any]], quote: dict[str, Any], snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run every Binance rule check over the prepared legs. Never raises."""
    symbol = instruction.get("pair") or "USDCUSDT"
    snapshot = snapshot or market_snapshot(symbol)
    rules = snapshot.get("rules") or {}
    average = snapshot.get("average_price") or {}
    book = snapshot.get("book") or {}
    clock = snapshot.get("server_time") or {}
    spend = [leg for leg in legs if leg.get("role") == "spend"]
    checks: list[dict[str, Any]] = []

    # 1. Is the pair actually trading right now?
    if rules.get("ok"):
        tradeable = bool(rules.get("tradeable"))
        checks.append(
            _check(
                "symbol_status",
                "Pair is live on Binance Spot",
                "pass" if tradeable else "fail",
                f"{symbol} status is {rules.get('status')}."
                + ("" if tradeable else " Preparation is priced but the pair is not currently tradeable."),
                symbol=symbol,
                status_value=rules.get("status"),
                permissions=rules.get("permissions"),
            )
        )
    else:
        checks.append(_check("symbol_status", "Pair is live on Binance Spot", "skipped", "Exchange rules unavailable; the price quote still stands."))

    # 2. Does every leg clear Binance's minimum notional?
    min_notional = _decimal(rules.get("min_notional")) if rules.get("ok") else None
    if min_notional is not None:
        below = [leg for leg in spend if (_decimal(leg.get("usdt")) or Decimal("0")) < min_notional]
        checks.append(
            _check(
                "min_notional",
                "Each leg clears the exchange minimum",
                "pass" if not below else "fail",
                f"Binance requires at least {min_notional} {rules.get('quote_asset', 'USDT')} per order. "
                + (
                    f"All {len(spend)} legs clear it."
                    if not below
                    else "Below the minimum: " + ", ".join(f"{leg.get('name')} ({leg.get('usdt')})" for leg in below)
                ),
                min_notional=str(min_notional),
                legs_checked=len(spend),
                legs_below=[leg.get("recipient_id") for leg in below],
            )
        )
    else:
        checks.append(_check("min_notional", "Each leg clears the exchange minimum", "skipped", "Notional filter unavailable."))

    # 3. Does the whole book fit under the maximum?
    max_notional = _decimal(rules.get("max_notional")) if rules.get("ok") else None
    total_usdt = sum((_decimal(leg.get("usdt")) or Decimal("0")) for leg in spend)
    if max_notional is not None:
        checks.append(
            _check(
                "max_notional",
                "Total sits inside the exchange ceiling",
                "pass" if total_usdt <= max_notional else "fail",
                f"{total_usdt} against a {max_notional} ceiling.",
                total=str(total_usdt),
                max_notional=str(max_notional),
            )
        )

    # 4. Would the legs survive the lot-size filter if converted on Spot?
    step = _decimal(rules.get("step_size")) if rules.get("ok") else None
    if step is not None and step > 0:
        adjustments = []
        for leg in spend:
            amount = _decimal(leg.get("usdt")) or Decimal("0")
            accepted = _quantize_down(amount, step)
            if accepted != amount:
                adjustments.append(
                    {
                        "recipient_id": leg.get("recipient_id"),
                        "name": leg.get("name"),
                        "requested": str(amount),
                        "accepted": str(accepted),
                        "remainder": str(amount - accepted),
                    }
                )
        checks.append(
            _check(
                "lot_size",
                "Amounts match the exchange lot step",
                "pass" if not adjustments else "warn",
                f"Lot step is {step}. "
                + (
                    "Every leg is already a whole step."
                    if not adjustments
                    else f"{len(adjustments)} leg(s) would be rounded down at conversion, leaving a remainder in the sender's balance."
                ),
                step_size=str(step),
                adjustments=adjustments,
            )
        )

    # 5. Is the quote inside Binance's own rolling average band?
    last = _decimal(quote.get("price")) if quote.get("ok") else None
    avg = _decimal(average.get("price")) if average.get("ok") else None
    if last is not None and avg is not None and avg > 0:
        drift_bps = ((last - avg) / avg * Decimal("10000")).quantize(Decimal("0.01"))
        wide = abs(drift_bps) > PRICE_DRIFT_WARN_BPS
        checks.append(
            _check(
                "price_band",
                "Quote agrees with the rolling average",
                "warn" if wide else "pass",
                f"Last {last} against the {average.get('window_minutes')}-minute average {avg}: {drift_bps} bps apart."
                + (" Wider than Allot's tolerance; re-quote before acting." if wide else ""),
                last_price=str(last),
                average_price=str(avg),
                drift_bps=str(drift_bps),
                tolerance_bps=str(PRICE_DRIFT_WARN_BPS),
                window_minutes=average.get("window_minutes"),
            )
        )
    else:
        checks.append(_check("price_band", "Quote agrees with the rolling average", "skipped", "Average price unavailable."))

    # 6. Is there enough real depth to convert this size?
    conversion = fill_estimate(book, total_usdt) if book.get("ok") and total_usdt > 0 else {"ok": False, "error": "book unavailable"}
    if conversion.get("ok"):
        slippage = _decimal(conversion.get("slippage_bps")) or Decimal("0")
        thin = slippage > SLIPPAGE_WARN_BPS or not conversion.get("fully_filled")
        checks.append(
            _check(
                "liquidity",
                "Live book can absorb the payout",
                "warn" if thin else "pass",
                f"Selling {conversion['requested_base']} {rules.get('base_asset', 'USDC')} into the live bids fills at "
                f"{conversion['average_fill_price']} against a {conversion['best_bid']} top of book — {conversion['slippage_bps']} bps of slippage "
                f"across {conversion['levels_consumed']} level(s)."
                + ("" if conversion.get("fully_filled") else " The visible book could not absorb the full size."),
                **{key: value for key, value in conversion.items() if key not in ("ok", "side")},
            )
        )
    else:
        checks.append(_check("liquidity", "Live book can absorb the payout", "skipped", str(conversion.get("error", "order book unavailable"))))

    # 7. Is this host's clock close enough to Binance's to timestamp honestly?
    if clock.get("ok"):
        drift = abs(int(clock.get("drift_ms") or 0))
        checks.append(
            _check(
                "clock_sync",
                "Receipt clock matches Binance",
                "warn" if drift > CLOCK_DRIFT_WARN_MS else "pass",
                f"{drift} ms from Binance server time (round trip {clock.get('round_trip_ms')} ms).",
                drift_ms=clock.get("drift_ms"),
                binance_time=clock.get("binance_time"),
                tolerance_ms=CLOCK_DRIFT_WARN_MS,
            )
        )
    else:
        checks.append(_check("clock_sync", "Receipt clock matches Binance", "skipped", "Binance server time unavailable."))

    failures = [check for check in checks if check["status"] == "fail"]
    warnings = [check for check in checks if check["status"] == "warn"]
    skipped = [check for check in checks if check["status"] == "skipped"]
    return {
        "ok": not failures,
        "symbol": symbol,
        "checked": len(checks),
        "passed": len([check for check in checks if check["status"] == "pass"]),
        "failed": len(failures),
        "warned": len(warnings),
        "skipped": len(skipped),
        "blocking": [check["detail"] for check in failures],
        "warnings": [check["detail"] for check in warnings],
        "checks": checks,
        "conversion_preview": conversion if conversion.get("ok") else None,
        "note": "Read-only checks against public Binance data. Allot places no orders and signs nothing.",
    }
