from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def host() -> str:
    return os.environ.get("HOST", "127.0.0.1")


def port() -> int:
    return int(os.environ.get("PORT", "8765"))


def public_base_url() -> str:
    configured = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    return f"http://{host()}:{port()}"


def data_dir() -> Path:
    raw = os.environ.get("ALLOT_DATA_DIR", "").strip()
    return Path(raw) if raw else ROOT / "data"


def book_path() -> Path:
    return ROOT / "data" / "book.json"


def receipts_path() -> Path:
    return data_dir() / "receipts.json"
