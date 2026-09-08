from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
import threading
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from allot.config import data_dir, receipts_path
from allot.money import usd

_LOCK = threading.Lock()


def canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(payload: Any) -> str:
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


def new_receipt_id(issued_at: datetime | None = None) -> str:
    stamp = (issued_at or now_utc()).strftime("%Y%m%d-%H%M%S")
    return f"ALLOT-{stamp}-{secrets.token_hex(2).upper()}"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_receipts() -> list[dict[str, Any]]:
    path = receipts_path()
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return data
    return []


def save_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = receipts_path()
    with _LOCK:
        receipts = load_receipts()
        receipts.insert(0, receipt)
        _atomic_write(path, receipts)
    return receipt


def _atomic_write(path: Path, receipts: list[dict[str, Any]]) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix="receipts.", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(receipts, handle, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def find_receipt(receipt_id: str) -> dict[str, Any] | None:
    needle = (receipt_id or "").strip()
    for receipt in load_receipts():
        if receipt.get("receipt_id") == needle or receipt.get("receipt_hash") == needle:
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
