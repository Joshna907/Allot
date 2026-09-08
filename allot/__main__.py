from __future__ import annotations

import argparse
import json
import sys

from allot.execute import execute_payout
from allot.mcp_server import health, serve_stdio
from allot.parser import parse_payout_book
from allot.server import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="allot", description="Allot — a payout book, not a trading bot.")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="Open the desktop counter in a browser.")
    sub.add_parser("mcp", help="Speak MCP on stdio so an agent can parse and prepare payouts.")
    sub.add_parser("health", help="Ping Binance price and B402 Bazaar.")
    parse_cmd = sub.add_parser("parse", help="Parse a sentence into an instruction.")
    parse_cmd.add_argument("text", nargs="+")
    run_cmd = sub.add_parser("pay", help="Prepare payment requirements. Does not transfer money.")
    run_cmd.add_argument("text", nargs="+")
    args = parser.parse_args(argv)

    if args.cmd in (None, "serve"):
        serve()
        return 0
    if args.cmd == "mcp":
        serve_stdio()
        return 0
    if args.cmd == "health":
        print(json.dumps(health(), indent=2))
        return 0
    text = " ".join(args.text)
    if args.cmd == "parse":
        print(json.dumps(parse_payout_book(text), indent=2))
        return 0
    receipt = execute_payout(text)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
