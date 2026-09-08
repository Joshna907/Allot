from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from allot.paths import load_book

MONEY = re.compile(
    r"(?:usd\s*)?\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)"
    r"|([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:usd|dollars?|usdt)\b",
    re.I,
)
PCT = re.compile(r"(\d{1,3})\s*%")
COUNT = re.compile(r"\b(three|3)\b", re.I)
MONTHLY = re.compile(r"\b(monthly|every\s+month|each\s+month|per\s+month)\b", re.I)
WEEKLY = re.compile(r"\b(weekly|every\s+week)\b", re.I)
DAILY = re.compile(r"\b(daily|every\s+day)\b", re.I)
TRADE = re.compile(
    r"\b(sma|ema|rsi|macd|signal|alpha|backtest)\d*\b"
    r"|\blong\s+btc\b|\bshort\s+eth\b|\bbuy\s+btc\b|\bsell\s+eth\b",
    re.I,
)

TWO_PLACES = Decimal("0.01")


def _money(text: str) -> Decimal | None:
    match = MONEY.search(text)
    if not match:
        return None
    raw = match.group(1) or match.group(2)
    return Decimal(raw.replace(",", "")).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _split(text: str) -> tuple[int, int] | None:
    found = [int(value) for value in PCT.findall(text)]
    if len(found) < 2:
        return None
    spend, hold = found[0], found[1]
    if spend + hold != 100:
        return None
    return spend * 100, hold * 100


def parse_payout_book(text: str, book: dict[str, Any] | None = None) -> dict[str, Any]:
    """Turn a sentence into a validated instruction. Recipients and pair are the book."""
    book = book or load_book()
    source = (text or "").strip()
    errors: list[str] = []
    warnings: list[str] = []

    if not source:
        errors.append("The book is blank. Write the payout the way you'd say it at the counter.")

    if TRADE.search(source):
        errors.append("Allot does not trade. No signals, no SMAs, no alpha. Describe a payout.")

    if WEEKLY.search(source) or DAILY.search(source):
        errors.append("The booked schedule is monthly. Weekly and daily runs are off the book.")

    if source and not MONTHLY.search(source):
        warnings.append("No monthly cadence found. Using the booked schedule: monthly.")

    if source and not COUNT.search(source):
        warnings.append("The book is three people. Extra names are ignored; missing names are filled from the roster.")

    amount = _money(source) if source else None
    booked = Decimal(book["gross_usd"])
    if amount is None:
        amount = booked
        if source:
            warnings.append(f"No dollar amount found. Using the booked amount: ${booked}.")
    elif amount != booked:
        warnings.append(f"You said ${amount}. The booked amount is ${booked}. Running the booked amount.")
        amount = booked

    parsed_split = _split(source) if source else None
    spend_bps = book["spend_bps"]
    hold_bps = book["hold_bps"]
    if parsed_split is None:
        if source:
            warnings.append("No 80/20 split found. Using the booked split: 80% spend, 20% held.")
    else:
        spend_bps, hold_bps = parsed_split
        if spend_bps != book["spend_bps"] or hold_bps != book["hold_bps"]:
            warnings.append("Off-book split. Recipients stay the booked three; the split follows your sentence.")

    recipients = book.get("recipients") or []
    recipient_total = sum(int(row.get("share_bps") or 0) for row in recipients)
    if len(recipients) != 3 or recipient_total != 10_000:
        errors.append("The payout roster is not configured correctly. It must contain three recipients whose shares add to 100%.")

    instruction = {
        "source_text": source,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "gross_usd": str(amount),
        "schedule": "monthly",
        "pair": book["pair"],
        "quote_asset": book["quote_asset"],
        "settle_asset": book["settle_asset"],
        "spend_bps": spend_bps,
        "hold_bps": hold_bps,
        "network": book["network"],
        "asset": book["asset"],
        "recipients": recipients,
    }
    return instruction
