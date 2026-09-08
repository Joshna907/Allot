from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"
BOOK_PATH = DATA_DIR / "book.json"
RECEIPTS_PATH = DATA_DIR / "receipts.json"


def load_book() -> dict[str, Any]:
    with BOOK_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)
