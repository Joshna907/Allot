# Allot

Hackathon repo: [Joshna907/Allot](https://github.com/Joshna907/Allot). Two-person split: [`TEAM.md`](TEAM.md). Hosted demo: set `PUBLIC_BASE_URL` after the first Render deploy, then paste the HTTPS origin here.

**One budget. Everyone accounted for.**

Allot is a cross-border payout agent for Binance Agent OS. A sender describes a payout book in plain English — *send $400 to three people monthly, 80% to spend, 20% held* — and Allot parses it, prices it on Binance, writes an [x402](https://developers.binance.com/en/docs/products/onchainpay-x402/introduction) envelope for each spend leg, and issues a receipt anyone can hash.

It is not a trading bot. It does not gate risk. It does not invent a fourth recipient. Three names, one pair, one schedule.

## The gap

Allot explores a payments use case for non-traders: coordinating a fixed monthly allocation across three recipients, with an inspectable record of what was prepared.

Remittance is the job most people actually have. Allot is the counter for that job.

## What it does

1. **Parse.** A sentence becomes a validated instruction. Recipients, pair (`USDCUSDT`), and cadence (`monthly`) are the book. Off-book amounts snap back. Trading language is rejected.
2. **Price.** Live last price from Binance Spot Testnet, with the public mainnet ticker as fallback.
3. **Check it against Binance's own rules.** Five public Spot reads in parallel — `exchangeInfo`, `avgPrice`, `ticker/24hr`, `depth`, `time` — become seven pass/warn/fail checks on the prepared book. See [the Binance rail](#the-binance-rail).
4. **Requirements.** Each spend leg is an x402 v2 `PaymentRequired` object for BSC USDT (`exact` scheme), plus the Base64 `PAYMENT-REQUIRED` header. Validated through Agentic Wallet preview locally if `baw` is available. Allot never signs.
5. **Discover.** A real call to [B402 Bazaar](https://www.binance.com/bapi/ramp/v1/public/ramp/b402/bazaar/resources). Failure is a warning; it does not block preparation.
6. **Receipt.** Totals, pending confirmation, SHA-256 of the canonical JSON. Hosted receipts on Render live in `/tmp` and disappear after sleep/redeploy.

## What is real, and what is not

Say this out loud in the demo.

**Real**

- Binance `USDCUSDT` last price (testnet, then mainnet public ticker).
- Binance exchange filters — pair status, lot step, minimum and maximum notional — applied to every leg.
- Binance rolling average price, 24h range, live order-book depth, and server-clock drift.
- B402 Bazaar public discovery (supporting evidence).
- x402 v2 payment requirements, also served as HTTP 402.

**Not settled**

- No signature, no broadcast, no B402 merchant settle.
- Agentic Wallet can preview requirements locally (`baw x402-payment preview`). Allot does not call `sign` or `wallet send`.
- Live Binance Pay. Demo preview only.

Rail decision: **Wallet preview plus demo-only payout preparation. No signing.**

## The Binance rail

Allot does not just read a price off Binance and call it an integration. Before a receipt is issued, the prepared book is checked against Binance's own live trading rules. Five public Spot endpoints are read in parallel — no API key, no KYC, no merchant onboarding — and `exchangeInfo` is cached for ten minutes.

| Binance read | Used for |
| --- | --- |
| `GET /api/v3/exchangeInfo` | pair status, tick size, lot step, min/max notional, permissions |
| `GET /api/v3/avgPrice` | the same rolling average Binance's own price-band filter uses |
| `GET /api/v3/ticker/24hr` | 24h high, low, change, and turnover as context for the quote |
| `GET /api/v3/depth` | real bid levels, walked to price the conversion |
| `GET /api/v3/time` | Binance server clock, against which the receipt timestamp is checked |

That produces seven checks on every receipt, each `pass`, `warn`, `fail`, or `skipped`:

1. **Pair is live** — the symbol's status is `TRADING`.
2. **Each leg clears the exchange minimum** — every spend leg is compared to `minNotional`. A leg too small to be a real Binance order is named.
3. **Total sits inside the ceiling** — the book is compared to `maxNotional`.
4. **Amounts match the lot step** — legs are quantized down to `stepSize`, and any remainder is reported rather than hidden.
5. **Quote agrees with the rolling average** — last price against `avgPrice`, in basis points, with a 50 bps tolerance.
6. **Live book can absorb the payout** — the bid side is walked for the full spend size to give an average fill, slippage in bps, and levels consumed. A partial fill is reported as a partial fill.
7. **Receipt clock matches Binance** — drift in milliseconds from Binance server time.

A failed check does not silently pass and a Binance outage does not break preparation: unreachable reads become `skipped`, and the receipt still issues with `evidence.binance_reads` recording how many of the five endpoints answered. No order is ever placed. The depth walk is arithmetic over public data, not a trade.

## The booked three

| Name | City | Share of the spend pool | Why |
| --- | --- | --- | --- |
| Amara Okafor | Lagos | 40% | rent and food |
| Kwame Boateng | Accra | 35% | studio invoice |
| Elena Cruz | Manila | 25% | design retainer |

$400 monthly allocation. By default, 80% ($320) becomes payment requirements and 20% ($80) is excluded. Allot does not hold funds. Each preparation is manual; there is no automatic scheduler. Pair is USDCUSDT.

## Run it

Python 3.11+ locally (Render uses 3.13). No third-party packages.

```bash
python -m allot health
python -m allot parse 'send $400 to three people monthly, 80% to spend, 20% held'
python -m allot pay 'send $400 to three people monthly, 80% to spend, 20% held'
python -m allot serve
```

Then open [http://127.0.0.1:8765](http://127.0.0.1:8765). Desktop only. Fast probe: [http://127.0.0.1:8765/healthz](http://127.0.0.1:8765/healthz).

The Python server hosts the complete no-build website. There is no `package.json` and no npm command:

| Route | Purpose |
| --- | --- |
| `/` | Product explanation and live payout-book preview |
| `/app` | Book overview, recipients, draft, recent activity, rail availability |
| `/app/prepare` | Recoverable describe, review, and preparation journey |
| `/receipts` | Searchable shared demo activity |
| `/receipts/{receipt_id}` | Inspect one receipt, its legs, evidence, and x402 requirements |
| `/verify` | Verify a receipt by ID or SHA-256 hash |
| `/how-it-works` | Nontechnical product flow, limitations, and troubleshooting |
| `/writeup` | Hackathon implementation notes and boundaries |

```bash
python -m unittest discover -s tests -v
```

Optional frontend component regression tests (Node is only a test runner, not an app dependency):

```bash
node --test tests/test_ui.mjs
```

Frontend modules: `web/app.js` (router), `web/product.js` (working pages),
`web/public.js` (public pages), `web/ui.js` (shared components), `web/lib.js`
(API and formatting), and token-based `web/styles.css`.
See [UX handoff](UX_HANDOFF.md) for teammate integration details and verification evidence.

The execute endpoint accepts an optional `request_id`. A bounded in-process cache
reuses successful results for identical retry attempts (up to 256 recent attempts).
It does not survive server restart. After an uncertain response, check activity
before retrying. Receipt JSON can be downloaded from the existing receipt endpoint
with `?download=1`.

Environment:

| Variable | Local default | Render |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | `0.0.0.0` |
| `PORT` | `8765` | supplied by Render |
| `PUBLIC_BASE_URL` | `http://127.0.0.1:8765` | your `https://….onrender.com` |
| `ALLOT_DATA_DIR` | `./data` | `/tmp/allot-data` |

Deploy: `render.yaml` defines a free Python web service named `allot`, start `python -m allot serve`, health `/healthz`. Set `PUBLIC_BASE_URL` to the public HTTPS origin after the first deploy. Hosted receipts vanish when the free instance sleeps.

## Agent OS / MCP

Project `.cursor/mcp.json` points Cursor at Binance Agent OS:

```text
https://agent.binance.com/mcp/agentic
```

Agent OS MCP OAuth is optional. If Identification/KYC hangs, ship the counter anyway — prices still come from Binance Spot Testnet and B402 Bazaar.

Allot also speaks MCP on stdio so an agent can parse and pay without the HTML counter:

```bash
python -m allot mcp
```

Eleven tools, all usable without Agent OS OAuth or KYC:

| Tool | Does |
| --- | --- |
| `get_payout_book` | the fixed roster, schedule, pair, and split |
| `parse_payout_book` | sentence → validated instruction |
| `execute_payout` | prepare requirements and issue a hashed receipt (no transfer) |
| `preflight_payout` | run all seven Binance checks with no receipt issued |
| `binance_rail_status` | the whole Spot rail: status, filters, prices, book, clock, Bazaar |
| `exchange_rules` | Binance's live filters for the pair |
| `check_liquidity` | walk the live book for a size, return fill price and slippage |
| `probe_rails` | quick Binance + Bazaar reachability ping |
| `list_receipts` / `get_receipt` | stored demo receipts |
| `verify_receipt` | recompute a hash from a stored id or a whole receipt object |

## HTTP API

| Route | Does |
| --- | --- |
| `GET /api/rails` | full Binance rail status, one call |
| `GET /api/exchange-rules?symbol=` | live exchange filters |
| `GET /api/liquidity?usd=320&symbol=` | depth walk: average fill, slippage bps, levels used |
| `POST /api/preflight` | all seven checks on a sentence, no receipt stored |
| `POST /api/parse` / `POST /api/execute` | parse, and prepare with an optional `request_id` |
| `GET /api/book` / `GET /api/receipts` / `GET /api/receipts/{id}` | book and stored receipts |
| `GET /api/verify/{id}` / `POST /api/verify` | verify a stored receipt, or one you post |
| `GET\|POST /payout/{receipt}/{recipient}` | the x402 requirement, as a real HTTP 402 |
| `GET /api/health` / `GET /healthz` | rail probe and liveness |

```bash
curl -s http://127.0.0.1:8765/api/rails
curl -s 'http://127.0.0.1:8765/api/liquidity?usd=320'
curl -s -X POST http://127.0.0.1:8765/api/preflight -H 'Content-Type: application/json' \
  -d '{"text":"send $400 to three people monthly, 80% to spend, 20% held"}'
```

## Verifying a receipt

The hash is SHA-256 over the canonical JSON of the receipt with `receipt_hash` removed — sorted keys, no whitespace. Two ways to check one:

```bash
curl https://<host>/api/verify/<receipt id or hash>          # stored on the server's disk
curl -X POST https://<host>/api/verify -d @receipt.json      # a receipt you were handed
```

The second route reads nothing from disk, so it still answers after the free Render instance sleeps and clears `/tmp`. Both return the claimed hash, the recomputed hash, and whether they match.

## Why this shape

Governor and Deltr placed on writeup as much as code. The sentence we are defending is not "we integrated five APIs". It is: **a non-trader can read the paper in fifteen seconds, and the paper tells the truth about the rail.**

`execute_payout(instruction) -> receipt` prepares payment requirements. It does not transfer money.

## Eligibility (read before you tweet)

Hackathon named exclusions: United States, United Kingdom, EEA, Hong Kong, Singapore. Nigeria is not on that named list. Binance's live [List of Prohibited Countries](https://www.binance.com/en/terms) still has to be checked by the person submitting — naira rails are suspended; this demo never touches NGN.

Entry does not count without all three: follow + repost, reply with video and GitHub, **survey form**.

## License

Hackathon demo. Testnet only. Not an offer to transmit money in production.
