from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from allot.money import usd
from allot.paths import DATA_DIR, RECEIPTS_PATH


def canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(payload: Any) -> str:
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


def new_receipt_id(issued_at: datetime) -> str:
    stamp = issued_at.strftime("%Y%m%d-%H%M%S")
    return f"ALLOT-{stamp}"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_receipts() -> list[dict[str, Any]]:
    if not RECEIPTS_PATH.exists():
        return []
    with RECEIPTS_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return data
    return []


def save_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    receipts = load_receipts()
    receipts.insert(0, receipt)
    with RECEIPTS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(receipts, handle, indent=2)
        handle.write("\n")
    return receipt


def find_receipt(receipt_id: str) -> dict[str, Any] | None:
    for receipt in load_receipts():
        if receipt.get("receipt_id") == receipt_id or receipt.get("receipt_hash") == receipt_id:
            return receipt
    return None


def verify_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    claimed = receipt.get("receipt_hash")
    body = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    recomputed = sha256_hex(body)
    return {
        "ok": claimed == recomputed,
        "receipt_id": receipt.get("receipt_id"),
        "claimed": claimed,
        "recomputed": recomputed,
    }


def attach_hash(receipt: dict[str, Any]) -> dict[str, Any]:
    body = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    receipt["receipt_hash"] = sha256_hex(body)
    return receipt


def usdt_from_usd(amount_usd: str, price: Decimal) -> Decimal:
    return usd(Decimal(amount_usd) * price)
