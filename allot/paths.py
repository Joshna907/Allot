from __future__ import annotations

import json
from typing import Any

from allot.config import ROOT, book_path, data_dir, receipts_path

WEB_DIR = ROOT / "web"
DATA_DIR = data_dir()
BOOK_PATH = book_path()
RECEIPTS_PATH = receipts_path()


def load_book() -> dict[str, Any]:
    with book_path().open(encoding="utf-8") as handle:
        return json.load(handle)
