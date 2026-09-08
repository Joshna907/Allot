from __future__ import annotations

import unittest
from decimal import Decimal

from allot.money import split_cents, usd
from allot.parser import parse_payout_book
from allot.receipt import attach_hash, sha256_hex, verify_receipt


class ParserTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        instruction = parse_payout_book(
            "send $400 to three people monthly, 80% to spend, 20% held"
        )
        self.assertTrue(instruction["valid"])
        self.assertEqual(instruction["gross_usd"], "400.00")
        self.assertEqual(instruction["spend_bps"], 8000)
        self.assertEqual(instruction["hold_bps"], 2000)
        self.assertEqual(len(instruction["recipients"]), 3)
        self.assertEqual(instruction["pair"], "USDCUSDT")
        self.assertEqual(instruction["warnings"], [])

    def test_rejects_trading(self) -> None:
        instruction = parse_payout_book("buy BTCUSDT on SMA20/50 monthly")
        self.assertFalse(instruction["valid"])

    def test_rejects_weekly(self) -> None:
        instruction = parse_payout_book("send $400 to three people weekly")
        self.assertFalse(instruction["valid"])

    def test_clamps_off_book_amount(self) -> None:
        instruction = parse_payout_book("send $900 to three people monthly")
        self.assertTrue(instruction["valid"])
        self.assertEqual(instruction["gross_usd"], "400.00")
        self.assertTrue(any("booked amount" in note for note in instruction["warnings"]))


class MoneyTests(unittest.TestCase):
    def test_split_sums_exactly(self) -> None:
        parts = split_cents(usd("320.00"), [4000, 3500, 2500])
        self.assertEqual(sum(parts, start=Decimal("0")), Decimal("320.00"))
        self.assertEqual(parts[0], Decimal("128.00"))
        self.assertEqual(parts[1], Decimal("112.00"))
        self.assertEqual(parts[2], Decimal("80.00"))


class ReceiptTests(unittest.TestCase):
    def test_hash_roundtrip(self) -> None:
        receipt = attach_hash({"receipt_id": "ALLOT-TEST", "legs": []})
        check = verify_receipt(receipt)
        self.assertTrue(check["ok"])
        self.assertEqual(check["recomputed"], sha256_hex({"receipt_id": "ALLOT-TEST", "legs": []}))


if __name__ == "__main__":
    unittest.main()
