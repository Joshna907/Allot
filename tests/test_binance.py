"""Binance rail tests. Every network call is mocked; these run offline."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from decimal import Decimal
from unittest.mock import patch

from allot import binance
from allot.execute import execute_payout
from allot.preflight import preflight
from allot.rails import dry_run, liquidity, rail_status

SYMBOL = "USDCUSDT"

RULES = {
    "ok": True,
    "symbol": SYMBOL,
    "status": "TRADING",
    "tradeable": True,
    "base_asset": "USDC",
    "quote_asset": "USDT",
    "tick_size": "0.00001000",
    "step_size": "0.01000000",
    "min_qty": "0.01000000",
    "min_notional": "5.00000000",
    "max_notional": "9000000.00000000",
    "avg_price_mins": 5,
    "source": "binance-spot-testnet",
}
BOOK = {
    "ok": True,
    "symbol": SYMBOL,
    "best_bid": "1.00000000",
    "best_ask": "1.00010000",
    "spread_bps": "1.00",
    "source": "binance-spot-testnet",
    "_bids": [(Decimal("1.00000000"), Decimal("200")), (Decimal("0.99000000"), Decimal("500"))],
}
QUOTE = {"ok": True, "symbol": SYMBOL, "price": "1.00000000", "source": "binance-spot-testnet"}
INSTRUCTION = {"pair": SYMBOL, "gross_usd": "400.00"}


def snapshot(**overrides):
    base = {
        "symbol": SYMBOL,
        "rules": RULES,
        "book": BOOK,
        "average_price": {"ok": True, "price": "1.00000000", "window_minutes": 5},
        "day_stats": {"ok": True, "last_price": "1.00000000"},
        "server_time": {"ok": True, "drift_ms": -120, "round_trip_ms": 90, "binance_time": "2026-09-08T00:00:00Z"},
        "reachable": 5,
        "reads": 5,
    }
    base.update(overrides)
    return base


def legs(*amounts: str):
    return [
        {"role": "spend", "recipient_id": f"r{index}", "name": f"Recipient {index}", "usd": amount, "usdt": amount}
        for index, amount in enumerate(amounts)
    ]


class FilterCheckTests(unittest.TestCase):
    def status_of(self, report, name):
        return next(check["status"] for check in report["checks"] if check["check"] == name)

    def test_healthy_book_passes_every_check(self) -> None:
        report = preflight(INSTRUCTION, legs("128.00", "112.00", "80.00"), QUOTE, snapshot())
        self.assertTrue(report["ok"])
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["skipped"], 0)

    def test_leg_below_binance_minimum_notional_fails(self) -> None:
        report = preflight(INSTRUCTION, legs("128.00", "112.00", "2.50"), QUOTE, snapshot())
        self.assertFalse(report["ok"])
        self.assertEqual(self.status_of(report, "min_notional"), "fail")
        self.assertIn("r2", next(c for c in report["checks"] if c["check"] == "min_notional")["legs_below"])

    def test_amount_off_the_lot_step_is_reported_with_its_remainder(self) -> None:
        report = preflight(INSTRUCTION, legs("128.005", "112.00", "80.00"), QUOTE, snapshot())
        self.assertEqual(self.status_of(report, "lot_size"), "warn")
        adjustment = next(c for c in report["checks"] if c["check"] == "lot_size")["adjustments"][0]
        self.assertEqual(Decimal(adjustment["accepted"]), Decimal("128.00"))
        self.assertEqual(Decimal(adjustment["remainder"]), Decimal("0.005"))

    def test_quote_far_from_the_rolling_average_warns(self) -> None:
        drifted = snapshot(average_price={"ok": True, "price": "1.05000000", "window_minutes": 5})
        report = preflight(INSTRUCTION, legs("128.00", "112.00", "80.00"), QUOTE, drifted)
        self.assertEqual(self.status_of(report, "price_band"), "warn")

    def test_thin_book_warns_and_reports_partial_fill(self) -> None:
        thin = snapshot(book={**BOOK, "_bids": [(Decimal("1.00000000"), Decimal("10"))]})
        report = preflight(INSTRUCTION, legs("128.00", "112.00", "80.00"), QUOTE, thin)
        self.assertEqual(self.status_of(report, "liquidity"), "warn")
        self.assertFalse(report["conversion_preview"]["fully_filled"])

    def test_halted_pair_fails_the_status_check(self) -> None:
        halted = snapshot(rules={**RULES, "status": "HALT", "tradeable": False})
        report = preflight(INSTRUCTION, legs("128.00", "112.00", "80.00"), QUOTE, halted)
        self.assertFalse(report["ok"])
        self.assertEqual(self.status_of(report, "symbol_status"), "fail")

    def test_wide_clock_drift_warns(self) -> None:
        skewed = snapshot(server_time={"ok": True, "drift_ms": 40000, "round_trip_ms": 100})
        report = preflight(INSTRUCTION, legs("128.00", "112.00", "80.00"), QUOTE, skewed)
        self.assertEqual(self.status_of(report, "clock_sync"), "warn")

    def test_binance_outage_skips_checks_without_failing(self) -> None:
        dark = snapshot(
            rules={"ok": False, "error": "down"},
            book={"ok": False, "error": "down"},
            average_price={"ok": False, "error": "down"},
            server_time={"ok": False, "error": "down"},
            reachable=0,
        )
        report = preflight(INSTRUCTION, legs("128.00", "112.00", "80.00"), QUOTE, dark)
        self.assertTrue(report["ok"])
        self.assertEqual(report["failed"], 0)
        self.assertGreaterEqual(report["skipped"], 4)


class FillEstimateTests(unittest.TestCase):
    def test_walks_multiple_levels_and_prices_the_slippage(self) -> None:
        estimate = binance.fill_estimate(BOOK, Decimal("400"))
        self.assertTrue(estimate["ok"])
        self.assertEqual(estimate["levels_consumed"], 2)
        self.assertTrue(estimate["fully_filled"])
        # 200 @ 1.00 + 200 @ 0.99 = 398 for 400 base -> 0.995 average, 50 bps under top of book.
        self.assertEqual(estimate["average_fill_price"], "0.99500000")
        self.assertEqual(estimate["slippage_bps"], "50.00")

    def test_reports_a_partial_fill_rather_than_pretending(self) -> None:
        estimate = binance.fill_estimate({**BOOK, "_bids": [(Decimal("1"), Decimal("5"))]}, Decimal("400"))
        self.assertFalse(estimate["fully_filled"])
        self.assertEqual(estimate["filled_base"], "5")

    def test_unreachable_book_is_an_error_not_a_crash(self) -> None:
        self.assertFalse(binance.fill_estimate({"ok": False, "error": "down"}, Decimal("400"))["ok"])


class SnapshotTests(unittest.TestCase):
    def tearDown(self) -> None:
        binance.clear_cache()

    def test_snapshot_survives_one_dead_endpoint(self) -> None:
        binance.clear_cache()
        with patch.object(binance, "order_book", return_value={"ok": False, "error": "down"}):
            with patch.object(binance, "server_time", return_value={"ok": True, "drift_ms": 0}):
                with patch.object(binance, "exchange_rules", return_value=RULES):
                    with patch.object(binance, "average_price", return_value={"ok": True, "price": "1.0"}):
                        with patch.object(binance, "day_stats", return_value={"ok": True}):
                            snap = binance.market_snapshot(SYMBOL)
        self.assertEqual(snap["reachable"], 4)
        self.assertEqual(snap["reads"], 5)

    def test_public_view_drops_internal_book_levels(self) -> None:
        view = binance.public_view({"book": BOOK})
        self.assertNotIn("_bids", view["book"])
        json.dumps(view)

    def test_exchange_rules_are_cached(self) -> None:
        binance.clear_cache()
        payload = {"ok": True, "source": "binance-spot-testnet", "url": "u", "payload": {"symbols": [{"symbol": SYMBOL, "status": "TRADING", "filters": []}]}}
        with patch.object(binance, "_get", return_value=payload) as fetch:
            binance.exchange_rules(SYMBOL)
            binance.exchange_rules(SYMBOL)
        self.assertEqual(fetch.call_count, 1)


class RailCompositionTests(unittest.TestCase):
    def test_rail_status_reports_reachability_and_stays_read_only(self) -> None:
        with patch("allot.rails.market_snapshot", return_value=snapshot()):
            with patch("allot.rails.probe_bazaar", return_value={"ok": True, "listed_resources": 25}):
                status = rail_status(SYMBOL)
        self.assertTrue(status["ok"])
        self.assertTrue(status["tradeable"])
        self.assertEqual(status["summary"]["min_notional"], "5.00000000")
        self.assertIn("does not trade", status["signing"])

    def test_liquidity_rejects_a_nonsense_size(self) -> None:
        self.assertFalse(liquidity(SYMBOL, "-5")["ok"])
        self.assertFalse(liquidity(SYMBOL, "abc")["ok"])

    def test_dry_run_checks_without_issuing_a_receipt(self) -> None:
        with patch("allot.rails.fetch_pair_price", return_value=QUOTE):
            with patch("allot.preflight.market_snapshot", return_value=snapshot()):
                report = dry_run("send $400 to three people monthly, 80% to spend, 20% held")
        self.assertTrue(report["ok"])
        self.assertFalse(report["receipt_issued"])
        self.assertEqual(len([leg for leg in report["legs"] if leg["role"] == "spend"]), 3)
        self.assertEqual(len([leg for leg in report["legs"] if leg["role"] == "hold"]), 1)

    def test_dry_run_refuses_a_trading_sentence(self) -> None:
        self.assertFalse(dry_run("buy 2 BTC")["ok"])


class ReceiptEnrichmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ALLOT_DATA_DIR"] = self.tmp.name

    def tearDown(self) -> None:
        self.tmp.cleanup()
        os.environ.pop("ALLOT_DATA_DIR", None)

    def test_receipt_carries_the_binance_rail_and_preflight(self) -> None:
        with patch("allot.execute.fetch_pair_price", return_value=QUOTE):
            with patch("allot.execute.probe_bazaar", return_value={"ok": True, "listed_resources": 25}):
                with patch("allot.execute.market_snapshot", return_value=snapshot()):
                    receipt = execute_payout("send $400 to three people monthly, 80% to spend, 20% held")
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["binance"]["rules"]["status"], "TRADING")
        self.assertTrue(receipt["evidence"]["exchange_filters"])
        self.assertEqual(receipt["evidence"]["binance_reads"], "5/5")
        self.assertTrue(receipt["preflight"]["ok"])
        self.assertNotIn("_bids", receipt["binance"]["book"])
        json.dumps(receipt)

    def test_a_binance_outage_still_produces_a_receipt(self) -> None:
        dark = snapshot(
            rules={"ok": False, "error": "down"},
            book={"ok": False, "error": "down"},
            average_price={"ok": False, "error": "down"},
            server_time={"ok": False, "error": "down"},
            day_stats={"ok": False, "error": "down"},
            reachable=0,
        )
        with patch("allot.execute.fetch_pair_price", return_value=QUOTE):
            with patch("allot.execute.probe_bazaar", return_value={"ok": False, "error": "down"}):
                with patch("allot.execute.market_snapshot", return_value=dark):
                    receipt = execute_payout("send $400 to three people monthly, 80% to spend, 20% held")
        self.assertTrue(receipt["ok"])
        self.assertFalse(receipt["evidence"]["exchange_filters"])
        self.assertTrue(receipt["preflight"]["ok"])
        self.assertGreaterEqual(receipt["preflight"]["skipped"], 4)


if __name__ == "__main__":
    unittest.main()
