from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Any

CENTS = Decimal("0.01")


def usd(value: Decimal | str | int) -> Decimal:
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def split_cents(total: Decimal, weights_bps: list[int]) -> list[Decimal]:
    """Split a dollar amount so parts sum exactly to the total."""
    total_cents = int((usd(total) * 100).to_integral_value(rounding=ROUND_DOWN))
    weight_sum = sum(weights_bps)
    if weight_sum <= 0:
        raise ValueError("Share weights must add to more than zero.")
    raw = [total_cents * weight // weight_sum for weight in weights_bps]
    remainder = total_cents - sum(raw)
    raw[-1] += remainder
    return [usd(Decimal(cents) / 100) for cents in raw]


def legs_from_instruction(instruction: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    gross = usd(instruction["gross_usd"])
    spend = usd(gross * Decimal(instruction["spend_bps"]) / Decimal(10000))
    hold = usd(gross - spend)
    weights = [int(row["share_bps"]) for row in instruction["recipients"]]
    parts = split_cents(spend, weights)
    spend_legs = []
    for recipient, amount in zip(instruction["recipients"], parts):
        spend_legs.append(
            {
                "role": "spend",
                "recipient_id": recipient["id"],
                "name": recipient["name"],
                "city": recipient["city"],
                "note": recipient["note"],
                "pay_to": recipient["pay_to"],
                "usd": str(amount),
            }
        )
    hold_leg = {
        "role": "hold",
        "recipient_id": "book",
        "name": "Held in the book",
        "city": "Sender",
        "note": "buffer for next month",
        "pay_to": None,
        "usd": str(hold),
    }
    totals = {
        "gross_usd": str(gross),
        "spend_usd": str(spend),
        "hold_usd": str(hold),
        "leg_sum_usd": str(usd(sum(Decimal(leg["usd"]) for leg in spend_legs) + hold)),
    }
    return spend_legs + [hold_leg], totals
