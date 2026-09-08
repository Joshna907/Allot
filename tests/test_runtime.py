from __future__ import annotations

import base64
import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from allot.mcp_server import TOOLS, call_tool
from allot.money import legs_from_instruction, usd
from allot.parser import parse_payout_book
from allot.price import fetch_pair_price
from allot.receipt import attach_hash, load_receipts, new_receipt_id, save_receipt, sha256_hex, verify_receipt
from allot.server import Handler
from allot.x402 import encode_payment_required, payment_required


class ParserBoundaryTests(unittest.TestCase):
    def test_blank_fails(self) -> None:
        instruction = parse_payout_book("")
        self.assertFalse(instruction["valid"])

    def test_daily_fails(self) -> None:
        instruction = parse_payout_book("send $400 to three people daily")
        self.assertFalse(instruction["valid"])


class ReceiptStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ALLOT_DATA_DIR"] = self.tmp.name

    def tearDown(self) -> None:
        self.tmp.cleanup()
        os.environ.pop("ALLOT_DATA_DIR", None)

    def test_ids_unique_in_same_second(self) -> None:
        stamp = datetime(2026, 9, 8, 18, 30, 12, tzinfo=timezone.utc)
        ids = {new_receipt_id(stamp) for _ in range(40)}
        self.assertEqual(len(ids), 40)
        self.assertTrue(all(item.startswith("ALLOT-20260908-183012-") for item in ids))

    def test_tamper_fails_verify(self) -> None:
        receipt = attach_hash({"receipt_id": "ALLOT-TEST", "legs": [{"usd": "1.00"}]})
        self.assertTrue(verify_receipt(receipt)["ok"])
        receipt["legs"][0]["usd"] = "9.00"
        self.assertFalse(verify_receipt(receipt)["ok"])

    def test_malformed_file_recovers(self) -> None:
        path = os.path.join(self.tmp.name, "receipts.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{not-json")
        self.assertEqual(load_receipts(), [])

    def test_concurrent_writes_valid_json(self) -> None:
        def write(index: int) -> None:
            save_receipt(attach_hash({"receipt_id": f"ALLOT-{index}", "n": index}))

        threads = [threading.Thread(target=write, args=(i,)) for i in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        receipts = load_receipts()
        self.assertEqual(len(receipts), 12)
        self.assertTrue(all("receipt_hash" in row for row in receipts))


class X402Tests(unittest.TestCase):
    def test_atomic_and_base64_and_public_url(self) -> None:
        from decimal import Decimal

        from allot.paths import load_book

        book = load_book()
        instruction = parse_payout_book("send $400 to three people monthly, 80% to spend, 20% held")
        instruction["asset"] = book["asset"]
        instruction["network"] = book["network"]
        legs, _ = legs_from_instruction(instruction)
        envelope = payment_required(
            legs[0],
            usd("128.03"),
            instruction,
            receipt_id="ALLOT-1",
            base_url="https://allot.example",
        )
        self.assertTrue(envelope["resource"]["url"].startswith("https://allot.example/payout/ALLOT-1/"))
        header = encode_payment_required(envelope)
        decoded = json.loads(base64.b64decode(header))
        self.assertEqual(decoded["x402Version"], 2)
        self.assertEqual(envelope["accepts"][0]["amount"], str((Decimal("128.03") * (10 ** 18)).to_integral_value()))


class PriceFallbackTests(unittest.TestCase):
    def test_testnet_success(self) -> None:
        class Response:
            def read(self) -> bytes:
                return b'{"symbol":"USDCUSDT","price":"1.00020000"}'

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

        with patch("allot.price.urllib.request.urlopen", return_value=Response()):
            quote = fetch_pair_price("USDCUSDT")
        self.assertTrue(quote["ok"])
        self.assertEqual(quote["source"], "binance-spot-testnet")
        self.assertIn("fetched_at", quote)

    def test_complete_outage(self) -> None:
        with patch("allot.price.urllib.request.urlopen", side_effect=URLError("down")):
            quote = fetch_pair_price("USDCUSDT")
        self.assertFalse(quote["ok"])


class HttpContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ALLOT_DATA_DIR"] = self.tmp.name
        os.environ["PUBLIC_BASE_URL"] = "http://127.0.0.1"
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        os.environ["PUBLIC_BASE_URL"] = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.tmp.cleanup()
        os.environ.pop("ALLOT_DATA_DIR", None)
        os.environ.pop("PUBLIC_BASE_URL", None)

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def test_healthz_no_network(self) -> None:
        with patch("allot.price.fetch_pair_price") as mocked:
            with urlopen(self._url("/healthz"), timeout=5) as response:
                body = json.loads(response.read())
                self.assertEqual(response.status, 200)
                self.assertTrue(body["ok"])
            mocked.assert_not_called()

    def test_execute_bazaar_outage_still_prepares(self) -> None:
        fake_quote = {
            "ok": True,
            "symbol": "USDCUSDT",
            "price": "1.00000000",
            "source": "binance-spot-testnet",
            "url": "https://example.test",
            "fetched_at": "2026-09-08T00:00:00Z",
        }
        with patch("allot.execute.fetch_pair_price", return_value=fake_quote):
            with patch("allot.execute.probe_bazaar", return_value={"ok": False, "error": "down"}):
                request = Request(
                    self._url("/api/execute"),
                    data=json.dumps({"text": "send $400 to three people monthly, 80% to spend, 20% held"}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=10) as response:
                    receipt = json.loads(response.read())
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["status"], "payment-requirements-created")
        self.assertFalse(receipt["evidence"]["bazaar_discovery"])
        spend = [leg for leg in receipt["legs"] if leg["role"] == "spend"]
        self.assertEqual(len(spend), 3)
        blob = json.dumps(receipt)
        self.assertNotIn("settled-demo", blob)
        self.assertTrue(all(leg["status"] == "payment-required" for leg in spend))

        first = spend[0]
        try:
            urlopen(self._url(f"/payout/{receipt['receipt_id']}/{first['recipient_id']}"), timeout=5)
            self.fail("expected 402")
        except HTTPError as exc:
            self.assertEqual(exc.code, 402)
            self.assertTrue(exc.headers.get("PAYMENT-REQUIRED"))

        signed = Request(
            self._url(f"/payout/{receipt['receipt_id']}/{first['recipient_id']}"),
            method="GET",
            headers={"PAYMENT-SIGNATURE": "nope"},
        )
        try:
            urlopen(signed, timeout=5)
            self.fail("expected 403")
        except HTTPError as exc:
            self.assertEqual(exc.code, 403)


class McpTests(unittest.TestCase):
    def test_tool_list_and_unknown(self) -> None:
        names = {tool["name"] for tool in TOOLS}
        self.assertGreaterEqual(
            names,
            {"parse_payout_book", "execute_payout", "list_receipts", "get_receipt", "verify_receipt"},
        )
        result = call_tool("not_a_tool", {})
        self.assertTrue(result.get("isError"))

    def test_parse_call(self) -> None:
        result = call_tool("parse_payout_book", {"text": "send $400 to three people monthly, 80% to spend, 20% held"})
        payload = json.loads(result["content"][0]["text"])
        self.assertTrue(payload["valid"])


if __name__ == "__main__":
    unittest.main()
