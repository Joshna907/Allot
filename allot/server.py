from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from allot.execute import execute_payout
from allot.mcp_server import health
from allot.parser import parse_payout_book
from allot.paths import WEB_DIR, load_book
from allot.receipt import find_receipt, load_receipts, verify_receipt

HOST = "127.0.0.1"
PORT = 8765
MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "Allot/0.1"

    def log_message(self, format: str, *args: object) -> None:
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/api/health":
            self._json(200, health())
            return
        if path == "/api/book":
            self._json(200, load_book())
            return
        if path == "/api/receipts":
            self._json(200, load_receipts())
            return
        if path.startswith("/api/receipts/"):
            receipt = find_receipt(path.split("/", 3)[-1])
            if receipt is None:
                self._json(404, {"ok": False, "error": "No receipt with that id or hash."})
                return
            self._json(200, receipt)
            return
        if path.startswith("/api/verify/"):
            receipt = find_receipt(path.split("/", 3)[-1])
            if receipt is None:
                self._json(404, {"ok": False, "error": "No receipt with that id or hash."})
                return
            self._json(200, verify_receipt(receipt))
            return
        self._static(path)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            payload = self._read_json()
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "Body must be JSON."})
            return
        text = str(payload.get("text") or "")
        if path == "/api/parse":
            self._json(200, parse_payout_book(text))
            return
        if path == "/api/execute":
            result = execute_payout(text)
            status = 200 if result.get("ok") else 422
            self._json(status, result)
            return
        self._json(404, {"ok": False, "error": "Unknown endpoint."})

    def _static(self, path: str) -> None:
        relative = "index.html" if path == "/" else path.lstrip("/")
        target = (WEB_DIR / relative).resolve()
        if WEB_DIR.resolve() not in target.parents and target != WEB_DIR.resolve():
            self._json(403, {"ok": False, "error": "Forbidden."})
            return
        if not target.is_file():
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        content_type = MIME.get(target.suffix, "application/octet-stream")
        self._send(200, target.read_bytes(), content_type)


def serve(host: str = HOST, port: int = PORT) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Allot counter: http://{host}:{port}", flush=True)
    httpd.serve_forever()
