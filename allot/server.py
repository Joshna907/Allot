from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from allot.config import host, port, public_base_url
from allot.execute import execute_payout
from allot.mcp_server import health
from allot.parser import parse_payout_book
from allot.paths import WEB_DIR, load_book
from allot.rails import DEFAULT_SYMBOL, dry_run, liquidity, rail_status, symbol_rules
from allot.receipt import find_receipt, load_receipts, verify_receipt

MAX_BODY_BYTES = 256 * 1024
MAX_DRAIN_BYTES = 8 * 1024 * 1024


class BodyTooLarge(ValueError):
    """The POST body is larger than Allot will read."""

    def __init__(self, message: str, length: int = 0) -> None:
        super().__init__(message)
        self.length = length


MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

FRONTEND_ROUTES = {
    "/",
    "/app",
    "/app/prepare",
    "/receipts",
    "/verify",
    "/how-it-works",
    "/writeup",
}

# A bounded retry cache for the current demo process. No funds are transferred.
_PREPARE_LOCK = threading.Lock()
_PREPARED: dict[str, tuple[str, dict]] = {}


class Handler(BaseHTTPRequestHandler):
    server_version = "Allot/0.1"

    def log_message(self, format: str, *args: object) -> None:
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def _send(self, status: int, body: bytes, content_type: str, extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        if extra:
            for key, value in extra.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: object, extra: dict[str, str] | None = None) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", extra)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        if length > MAX_BODY_BYTES:
            raise BodyTooLarge(f"Body must be under {MAX_BODY_BYTES // 1024} KB.", length)
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        if isinstance(data, dict):
            return data
        return {}

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, PAYMENT-SIGNATURE")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/healthz":
            self._json(200, {"ok": True, "service": "allot"})
            return
        if path == "/api/health":
            self._json(200, health())
            return
        if path == "/api/book":
            self._json(200, load_book())
            return
        query = parse_qs(parsed.query)
        symbol = (query.get("symbol") or [DEFAULT_SYMBOL])[0].upper()
        if path == "/api/rails":
            self._json(200, rail_status(symbol))
            return
        if path == "/api/exchange-rules":
            rules = symbol_rules(symbol)
            self._json(200 if rules.get("ok") else 502, rules)
            return
        if path == "/api/liquidity":
            report = liquidity(symbol, (query.get("usd") or query.get("amount") or ["320"])[0])
            self._json(200 if report.get("ok") else 502, report)
            return
        if path == "/api/receipts":
            self._json(200, load_receipts())
            return
        if path.startswith("/api/receipts/"):
            receipt = find_receipt(unquote(path.split("/", 3)[-1]))
            if receipt is None:
                self._json(404, {"ok": False, "error": "No receipt with that id or hash."})
                return
            extra = None
            if parse_qs(parsed.query).get("download") == ["1"]:
                filename = re.sub(r"[^A-Za-z0-9_-]", "_", str(receipt.get("receipt_id", "allot-receipt")))
                extra = {"Content-Disposition": f'attachment; filename="{filename}.json"'}
            self._json(200, receipt, extra)
            return
        if path.startswith("/api/verify/"):
            receipt = find_receipt(unquote(path.split("/", 3)[-1]))
            if receipt is None:
                self._json(
                    404,
                    {
                        "ok": False,
                        "error": "No stored receipt with that id or hash. Hosted receipts are cleared when the free instance sleeps — POST the receipt JSON to /api/verify to check it without this disk.",
                    },
                )
                return
            self._json(200, {**verify_receipt(receipt), "source": "stored"})
            return
        if path.startswith("/payout/"):
            self._payout(path)
            return
        if path.startswith("/api/"):
            self._json(404, {"ok": False, "error": "Unknown endpoint."})
            return
        if path in FRONTEND_ROUTES:
            self._app_shell(200)
            return
        if path.startswith("/receipts/"):
            receipt_id = unquote(path.split("/", 2)[-1])
            self._app_shell(200 if find_receipt(receipt_id) is not None else 404)
            return
        if "." not in path.rsplit("/", 1)[-1]:
            self._app_shell(404)
            return
        self._static(path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path.startswith("/payout/"):
            self._payout(path)
            return
        try:
            payload = self._read_json()
        except BodyTooLarge as exc:
            self._drain(exc.length)
            self.close_connection = True
            self._json(413, {"ok": False, "error": str(exc)})
            return
        except (json.JSONDecodeError, ValueError) as exc:
            self._json(400, {"ok": False, "error": str(exc) or "Body must be JSON."})
            return
        if path == "/api/verify":
            self._verify_pasted(payload)
            return
        text = str(payload.get("text") or "")
        if path == "/api/parse":
            self._json(200, parse_payout_book(text))
            return
        if path == "/api/preflight":
            report = dry_run(text, str(payload.get("symbol") or "").upper() or None)
            self._json(200 if report.get("ok") else 422, report)
            return
        if path == "/api/execute":
            request_id = str(payload.get("request_id") or "")
            if request_id and not re.fullmatch(r"[A-Za-z0-9-]{8,80}", request_id):
                self._json(400, {"ok": False, "error": "Invalid preparation request identifier."})
                return
            with _PREPARE_LOCK:
                previous = _PREPARED.get(request_id) if request_id else None
                if previous and previous[0] != text:
                    self._json(409, {"ok": False, "error": "This attempt belongs to another instruction. Return to review and start a new attempt."})
                    return
                if previous:
                    result = previous[1]
                else:
                    try:
                        result = execute_payout(text)
                    except Exception:
                        self._json(503, {"ok": False, "error": "Preparation could not be confirmed. Check activity before retrying.", "retryable": True})
                        return
                    if request_id and result.get("ok"):
                        if len(_PREPARED) >= 256:
                            _PREPARED.pop(next(iter(_PREPARED)))
                        _PREPARED[request_id] = (text, result)
            status = 200 if result.get("ok") else 422
            self._json(status, result)
            return
        self._json(404, {"ok": False, "error": "Unknown endpoint."})

    def _drain(self, length: int) -> None:
        """Swallow a body we refused to parse, so the client reads our 413 instead of a reset socket."""
        remaining = min(length, MAX_DRAIN_BYTES)
        while remaining > 0:
            chunk = self.rfile.read(min(65536, remaining))
            if not chunk:
                return
            remaining -= len(chunk)

    def _verify_pasted(self, payload: dict) -> None:
        """Recompute the hash of a receipt someone pasted back. Nothing is read from disk."""
        candidate = payload.get("receipt")
        receipt = candidate if isinstance(candidate, dict) else payload
        if not receipt.get("receipt_hash"):
            self._json(
                400,
                {
                    "ok": False,
                    "error": "Post the receipt JSON itself, or {\"receipt\": {...}}. It must carry its receipt_hash.",
                },
            )
            return
        self._json(200, {**verify_receipt(receipt), "source": "pasted"})

    def _payout(self, path: str) -> None:
        parts = [unquote(part) for part in path.strip("/").split("/")]
        if len(parts) != 3:
            self._json(404, {"ok": False, "error": "Payout URL must be /payout/{receipt_id}/{recipient_id}."})
            return
        _, receipt_id, recipient_id = parts
        if self.headers.get("PAYMENT-SIGNATURE"):
            self._json(
                403,
                {
                    "ok": False,
                    "error": "Settlement disabled in hackathon demo. Allot never verifies, signs, or broadcasts a payment.",
                },
            )
            return
        receipt = find_receipt(receipt_id)
        if receipt is None:
            self._json(404, {"ok": False, "error": "No receipt with that id."})
            return
        leg = next((row for row in receipt.get("legs") or [] if row.get("recipient_id") == recipient_id), None)
        if leg is None or not (leg.get("x402") or {}).get("payment_required"):
            self._json(404, {"ok": False, "error": "No payment requirement for that recipient."})
            return
        payload = leg["x402"]["payment_required"]
        header = leg["x402"]["payment_required_header"]
        self._json(402, payload, extra={"PAYMENT-REQUIRED": header})

    def _static(self, path: str) -> None:
        relative = path.lstrip("/")
        target = (WEB_DIR / relative).resolve()
        if WEB_DIR.resolve() not in target.parents and target != WEB_DIR.resolve():
            self._json(403, {"ok": False, "error": "Forbidden."})
            return
        if not target.is_file():
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        content_type = MIME.get(target.suffix, "application/octet-stream")
        self._send(200, target.read_bytes(), content_type)

    def _app_shell(self, status: int) -> None:
        target = WEB_DIR / "index.html"
        self._send(status, target.read_bytes(), MIME[".html"])


def serve(bind_host: str | None = None, bind_port: int | None = None) -> None:
    bind_host = bind_host if bind_host is not None else host()
    bind_port = bind_port if bind_port is not None else port()
    httpd = ThreadingHTTPServer((bind_host, bind_port), Handler)
    print(f"Allot counter: {public_base_url()}  (bound {bind_host}:{bind_port})", flush=True)
    httpd.serve_forever()
