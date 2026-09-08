from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from allot.paths import load_book
from allot.money import legs_from_instruction

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
    r"|\b(buy|sell|swap|trade|trading|short|long|hedge|arbitrage|leverage|margin|futures|perp|perps)\b",
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
    matches = list(PCT.finditer(text))
    if not matches:
        return None
    if len(matches) != 2:
        raise ValueError("Include exactly two percentages, labelled spend and held, adding up to 100%.")
    values = [int(match.group(1)) for match in matches]
    if sum(values) != 100 or any(value > 100 for value in values):
        raise ValueError("Spend and held percentages must add up to 100%.")
    if re.search(r"-\s*\d+\s*%|\d+\.\d+\s*%", text):
        raise ValueError("Use whole, non-negative percentages for this demo.")
    role_pattern = r"(spend|spent|spending|held|hold|save|saved|reserve|reserved)\b"
    roles = []
    for index, match in enumerate(matches):
        after = text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(text)]
        before = text[matches[index - 1].end() if index else 0:match.start()]
        suffix = re.match(r"\s*(?:(?:to|for|as)\s+)?" + role_pattern, after, re.I)
        prefix = re.search(role_pattern + r"\s*[:=]?\s*$", before, re.I)
        found = prefix if index == 0 and prefix else suffix or prefix
        roles.append("spend" if found and found.group(1).lower() in ("spend", "spent", "spending") else "hold" if found else None)
    if set(roles) != {"spend", "hold"}:
        raise ValueError("Label both percentages clearly, for example: 80% to spend, 20% held.")
    return values[roles.index("spend")] * 100, values[roles.index("hold")] * 100


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

    try:
        parsed_split = _split(source) if source else None
    except ValueError as exc:
        errors.append(str(exc))
        parsed_split = None
    spend_bps = book["spend_bps"]
    hold_bps = book["hold_bps"]
    if parsed_split is None:
        if source:
            warnings.append("No usable split found. The demo default is 80% spend, 20% held.")
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
    if instruction["valid"]:
        instruction["allocation"], instruction["totals"] = legs_from_instruction(instruction)
    return instruction
