# Allot

A payout agent for Binance Agent OS. It turns a plain-English payout book into [x402](https://developers.binance.com/en/docs/products/onchainpay-x402/introduction) v2 payment requirements, checks them against Binance Spot's live trading rules, and issues a receipt anyone can recompute.

![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen) ![Tests](https://img.shields.io/badge/tests-59%20python%20%2B%2012%20node-brightgreen) ![License](https://img.shields.io/badge/license-MIT-blue) ![Status](https://img.shields.io/badge/status-demo%20only-orange)

> **Disclaimer.** Allot is a hackathon demo. It prepares payment requirements and never signs, broadcasts, settles, or custodies anything. It holds no keys, requires no Binance API key, and moves no funds. Prices come from Binance Spot Testnet with the public mainnet ticker as fallback. Nothing here is an offer to transmit money.

## Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [The Binance rail](#the-binance-rail)
- [The payout book](#the-payout-book)
- [HTTP API](#http-api)
- [MCP tools](#mcp-tools)
- [Web interface](#web-interface)
- [Verifying a receipt](#verifying-a-receipt)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Testing](#testing)
- [Project layout](#project-layout)
- [Design principles](#design-principles)
- [Scope and limits](#scope-and-limits)
- [Security](#security)
- [Team](#team)
- [License](#license)

## Overview

Most agents built on exchange infrastructure trade. Allot pays. A sender describes a recurring payout in the way they would say it out loud — *send $400 to three people monthly, 80% to spend, 20% held* — and Allot parses that into a validated instruction, prices it on Binance, checks the allocation against Binance's own exchange filters, writes an x402 `PaymentRequired` envelope for each spend leg, and issues a hashed receipt.

It is not a trading bot, and it refuses to behave like one: trading language is rejected at the parser, the roster is fixed at three recipients, and the schedule is monthly. Off-book amounts snap back to the booked figure with a warning rather than being obeyed silently.

The distinguishing claim is not "it calls the Binance API". It is that **the paper tells the truth about the rail**: every number on a receipt is traceable to a public Binance read, and everything the demo cannot do is written on the receipt itself.

## Prerequisites

| Requirement | Notes |
| --- | --- |
| Python 3.11+ | 3.13.5 in deployment. Standard library only — `requirements.txt` installs nothing |
| Node 18+ | Optional. Test runner for the frontend component tests only, not an app dependency |
| `baw` CLI | Optional. Binance Agentic Wallet, for local `x402-payment preview`. Allot never calls `sign` or `wallet send` |

No Binance API key, no merchant `clientId`, and no Agent OS OAuth are required. Every Binance endpoint Allot reads is public.

## Quick start

```bash
git clone https://github.com/Joshna907/Allot.git
cd Allot
python -m allot serve
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). Liveness probe: [`/healthz`](http://127.0.0.1:8765/healthz).

The CLI covers the same surface without the browser:

```bash
python -m allot health                                                        # rail reachability
python -m allot parse 'send $400 to three people monthly, 80% to spend, 20% held'
python -m allot pay   'send $400 to three people monthly, 80% to spend, 20% held'
python -m allot mcp                                                           # MCP server on stdio
```

## How it works

1. **Parse.** The sentence becomes a validated instruction. Recipients, pair (`USDCUSDT`), and cadence (`monthly`) come from the book. Amounts and splits are read from the sentence; off-book amounts snap back to the booked figure with a warning. Trading verbs — buy, sell, swap, long, short, leverage — are rejected outright.
2. **Price.** Last price from Binance Spot Testnet, falling back to the public mainnet ticker.
3. **Check against Binance's rules.** Five public Spot endpoints are read in parallel and turned into seven pass/warn/fail checks on the prepared allocation. See [The Binance rail](#the-binance-rail).
4. **Build requirements.** Each spend leg becomes an x402 v2 `PaymentRequired` object for BSC USDT (`exact` scheme), plus its Base64 `PAYMENT-REQUIRED` header. Allot never signs.
5. **Discover.** A live call to the [B402 Bazaar](https://www.binance.com/bapi/ramp/v1/public/ramp/b402/bazaar/resources) public resource list. Failure is a warning; it does not block preparation.
6. **Issue a receipt.** Totals, per-leg detail, every rail read, the preflight report, what is still pending, and a SHA-256 over the canonical JSON.
7. **Serve the requirement.** `GET /payout/{receipt}/{recipient}` returns a real HTTP 402 carrying that leg's requirement. Presenting a `PAYMENT-SIGNATURE` header returns 403 — settlement is disabled, deliberately and in code.

## The Binance rail

Reading a price is not an integration. Before a receipt is issued, the prepared book is checked against Binance's own live trading rules. Five public Spot endpoints are read concurrently; `exchangeInfo` is cached for ten minutes.

| Binance endpoint | Used for |
| --- | --- |
| `GET /api/v3/exchangeInfo` | pair status, tick size, lot step, min/max notional, permissions |
| `GET /api/v3/avgPrice` | the same rolling average Binance's own price-band filter uses |
| `GET /api/v3/ticker/24hr` | 24h high, low, change, and turnover as context for the quote |
| `GET /api/v3/depth` | real bid levels, walked to price the conversion |
| `GET /api/v3/time` | Binance server clock, checked against the receipt timestamp |

Seven checks are recorded on every receipt, each `pass`, `warn`, `fail`, or `skipped`:

| # | Check | Fails or warns when |
| --- | --- | --- |
| 1 | Pair is live | symbol status is not `TRADING` |
| 2 | Each leg clears the exchange minimum | a spend leg is under `minNotional` — the leg is named |
| 3 | Total sits inside the ceiling | the book exceeds `maxNotional` |
| 4 | Amounts match the lot step | a leg is not a whole multiple of `stepSize`; the remainder is reported, not hidden |
| 5 | Quote agrees with the rolling average | last price is more than 50 bps from `avgPrice` |
| 6 | Live book can absorb the payout | the bid-side walk slips more than 25 bps, or cannot fill the size |
| 7 | Receipt clock matches Binance | the host clock is more than 5s from Binance server time |

Check 6 walks the real bid side for the full spend size and reports average fill price, slippage in basis points, and levels consumed. It is arithmetic over public order-book data — **no order is placed**.

Degradation is explicit: unreachable endpoints become `skipped` checks, preparation still succeeds, and `evidence.binance_reads` records how many of the five answered (`"5/5"`, `"3/5"`, `"0/5"`). A Binance outage costs you evidence, never a receipt.

## The payout book

| Recipient | City | Share of spend pool | Purpose |
| --- | --- | --- | --- |
| Amara Okafor | Lagos | 40% | rent and food |
| Kwame Boateng | Accra | 35% | studio invoice |
| Elena Cruz | Manila | 25% | design retainer |

A $400 monthly allocation. By default 80% ($320) becomes payment requirements and 20% ($80) is excluded from preparation. Allot does not hold the excluded amount. Each preparation is manual — there is no scheduler, and nothing recurs on its own. Pair is `USDCUSDT`.

## HTTP API

| Method | Route | Returns |
| --- | --- | --- |
| `GET` | `/healthz` | liveness, no network calls |
| `GET` | `/api/health` | quote, Bazaar reachability, book summary |
| `GET` | `/api/book` | the fixed payout configuration |
| `GET` | `/api/rails` | the whole Binance rail in one call: status, filters, prices, book, clock, Bazaar |
| `GET` | `/api/exchange-rules?symbol=` | live exchange filters for the pair |
| `GET` | `/api/liquidity?usd=&symbol=` | depth walk: average fill, slippage bps, levels consumed |
| `POST` | `/api/parse` | sentence → validated instruction, warnings, allocation |
| `POST` | `/api/preflight` | all seven checks on a sentence, no receipt issued |
| `POST` | `/api/execute` | prepare requirements and store a receipt |
| `GET` | `/api/receipts` | stored demo receipts |
| `GET` | `/api/receipts/{id\|hash}` | one receipt; `?download=1` sets a download filename |
| `GET` | `/api/verify/{id\|hash}` | claimed vs recomputed hash for a stored receipt |
| `POST` | `/api/verify` | same, for a receipt you post — reads no storage |
| `GET`/`POST` | `/payout/{receipt}/{recipient}` | HTTP 402 with the x402 requirement; 403 if a signature is presented |

```bash
curl -s http://127.0.0.1:8765/api/rails
curl -s 'http://127.0.0.1:8765/api/liquidity?usd=320'
curl -s -X POST http://127.0.0.1:8765/api/preflight \
  -H 'Content-Type: application/json' \
  -d '{"text":"send $400 to three people monthly, 80% to spend, 20% held"}'
```

`POST /api/execute` accepts an optional `request_id`. A bounded in-process cache (256 recent attempts) returns the same receipt for an identical retry, so a lost response does not become a second preparation. It does not survive a restart; after an uncertain response, check activity before retrying. Request bodies over 256 KB are refused with 413.

## MCP tools

Allot speaks MCP over stdio, so an agent can use the whole surface without the web interface:

```bash
python -m allot mcp
```

| Tool | Does |
| --- | --- |
| `get_payout_book` | the fixed roster, schedule, pair, and split |
| `parse_payout_book` | sentence → validated instruction |
| `preflight_payout` | all seven Binance checks, no receipt issued |
| `execute_payout` | prepare requirements and issue a hashed receipt — no transfer |
| `binance_rail_status` | full Spot rail: status, filters, prices, book, clock, Bazaar |
| `exchange_rules` | Binance's live filters for the pair |
| `check_liquidity` | walk the live book for a size; fill price and slippage |
| `probe_rails` | quick Binance + Bazaar reachability ping |
| `list_receipts` | stored demo receipts |
| `get_receipt` | one stored receipt by id or hash |
| `verify_receipt` | recompute a hash from a stored id, or from a receipt object |

`.cursor/mcp.json` also points Cursor at Binance Agent OS (`https://agent.binance.com/mcp/agentic`). That OAuth is optional — every tool above works without it.

## Web interface

The Python server hosts the complete no-build website. There is no `package.json` and no npm command.

| Route | Purpose |
| --- | --- |
| `/` | Product explanation and live payout-book preview |
| `/app` | Book overview, recipients, draft, recent activity, rail availability |
| `/app/prepare` | Recoverable describe, review, and preparation journey |
| `/receipts` | Searchable shared demo activity |
| `/receipts/{receipt_id}` | One receipt: legs, evidence, x402 requirements |
| `/verify` | Verify by ID, hash, or pasted receipt JSON |
| `/how-it-works` | Nontechnical product flow, limitations, troubleshooting |
| `/writeup` | Implementation notes and boundaries |

Frontend modules: `web/app.js` (router), `web/product.js` (working pages), `web/public.js` (public pages), `web/ui.js` (shared components), `web/lib.js` (API and formatting), and token-based `web/styles.css`. See [UX_HANDOFF.md](UX_HANDOFF.md).

## Verifying a receipt

The hash is SHA-256 over the canonical JSON of the receipt with `receipt_hash` removed — sorted keys, no whitespace, ASCII. Two ways to check one:

```bash
curl https://<host>/api/verify/<receipt id or hash>      # against the server's stored copy
curl -X POST https://<host>/api/verify -d @receipt.json  # against a receipt you were handed
```

Both return the claimed hash, the recomputed hash, and whether they match. The second reads nothing from storage, so a downloaded receipt stays verifiable after the hosted instance sleeps and clears `/tmp`.

## Configuration

| Variable | Local default | Deployment |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | `0.0.0.0` |
| `PORT` | `8765` | supplied by the platform |
| `PUBLIC_BASE_URL` | `http://127.0.0.1:8765` | the public HTTPS origin, no trailing slash |
| `ALLOT_DATA_DIR` | `./data` | `/tmp/allot-data` |

`PUBLIC_BASE_URL` is not cosmetic: it is the origin written into every x402 `resource.url`. Set it to the deployed origin or the payment requirements will point at a private address.

## Deployment

`render.yaml` defines a free Python web service: start `python -m allot serve`, health check `/healthz`, Python pinned by `PYTHON_VERSION`. Deploy as a Blueprint, then set `PUBLIC_BASE_URL` to the assigned HTTPS origin and redeploy.

Free instances sleep when idle and clear `/tmp`, so hosted receipts are ephemeral by design. Download the JSON, or verify it later with `POST /api/verify`.

## Testing

```bash
python -m unittest discover -s tests -v   # 59 tests, no network required
node --test tests/test_ui.mjs             # 12 frontend component tests
```

The Python suite mocks every outbound call, including full Binance outages, thin order books, halted pairs, legs below the exchange minimum, and clock skew. `tests/test_runtime.py` covers the HTTP contract; `tests/test_binance.py` covers the rail and preflight checks.

## Project layout

```
allot/
  __main__.py     CLI: serve, mcp, health, parse, pay
  parser.py       sentence -> validated instruction; rejects trading language
  money.py        decimal allocation across the booked recipients
  price.py        Binance last price, testnet then public mainnet
  binance.py      Spot rail client: exchangeInfo, avgPrice, 24hr, depth, time
  preflight.py    the seven checks against Binance's live rules
  rails.py        composed rail views shared by HTTP and MCP
  x402.py         x402 v2 PaymentRequired envelopes and B402 Bazaar discovery
  execute.py      preparation: quote, rail, legs, receipt
  receipt.py      canonical JSON, SHA-256, atomic storage, verification
  server.py       HTTP API, HTTP 402 payout routes, static and app-shell serving
  mcp_server.py   MCP over stdio
web/              no-build frontend
tests/            Python and Node test suites
data/book.json    the fixed payout book
```

## Design principles

- **Read-only against Binance.** Public endpoints only. No API key, no signing, no order placement, no custody.
- **Every number is traceable.** If it is on the receipt, a named Binance read or a documented calculation produced it.
- **Degrade, never fake.** An unreachable endpoint becomes a `skipped` check with the count recorded — not a plausible-looking default.
- **The fences are code, not copy.** Trading language is refused by the parser; a presented payment signature is refused with 403.
- **No hidden state.** Receipts are canonical JSON with a hash anyone can recompute offline.

## Scope and limits

**Working against live infrastructure**

- Binance `USDCUSDT` last price — Spot Testnet, then the public mainnet ticker.
- Binance exchange filters — pair status, lot step, min and max notional — applied per leg.
- Binance rolling average price, 24h range, live order-book depth, and server-clock drift.
- B402 Bazaar public resource discovery.
- x402 v2 payment requirements, served as real HTTP 402 responses.

**Deliberately not implemented**

- No signature, no broadcast, no on-chain settlement.
- No B402 merchant settle (`/papi/v2/b402/settle`) — that needs partner credentials Allot does not have.
- No live Binance Pay.
- No scheduler. Nothing recurs without a person asking for it.
- Agentic Wallet can preview requirements locally (`baw x402-payment preview`); Allot never calls `sign` or `wallet send`.

## Security

Allot stores no credentials and needs none. It never holds funds, and `POST /payout/...` refuses a presented `PAYMENT-SIGNATURE` with 403 rather than attempting verification. Static file serving is path-contained; request bodies are capped at 256 KB; receipt writes are atomic and lock-guarded. Demo receipts are public within an instance — do not put anything private in a payout note.

## Team

Two-person build; the split is in [TEAM.md](TEAM.md). Submission details are in [SUBMISSION.md](SUBMISSION.md).

## License

MIT — see [LICENSE](LICENSE). The demo is testnet-only and is not an offer to transmit money in production.
