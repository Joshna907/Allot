# Allot

Hackathon repo: [Joshna907/Allot](https://github.com/Joshna907/Allot). Two-person split: [`TEAM.md`](TEAM.md). Hosted demo: set `PUBLIC_BASE_URL` after the first Render deploy, then paste the HTTPS origin here.

**Everyone built an agent that trades. This one pays.**

Allot is a cross-border payout agent for Binance Agent OS. A sender describes a payout book in plain English — *send $400 to three people monthly, 80% to spend, 20% held* — and Allot parses it, prices it on Binance, writes an [x402](https://developers.binance.com/en/docs/products/onchainpay-x402/introduction) envelope for each spend leg, and issues a receipt anyone can hash.

It is not a trading bot. It does not gate risk. It does not invent a fourth recipient. Three names, one pair, one schedule.

## The gap

Track A filled up with trader copilots and safety layers. The safety-layer lane already has Governor, CHARTER, Countersign, Magister, Haptix, Gate, and Deltr. The SMA20/50 lane is a pile of the same chart. Nobody shipped agent-driven **payments**. Nobody used x402 or Binance Pay for a non-trader.

Remittance is the job most people actually have. Allot is the counter for that job.

## What it does

1. **Parse.** A sentence becomes a validated instruction. Recipients, pair (`USDCUSDT`), and cadence (`monthly`) are the book. Off-book amounts snap back. Trading language is rejected.
2. **Price.** Live last price from Binance Spot Testnet, with the public mainnet ticker as fallback.
3. **Requirements.** Each spend leg is an x402 v2 `PaymentRequired` object for BSC USDT (`exact` scheme), plus the Base64 `PAYMENT-REQUIRED` header. Validated through Agentic Wallet preview locally if `baw` is available. Allot never signs.
4. **Discover.** A real call to [B402 Bazaar](https://www.binance.com/bapi/ramp/v1/public/ramp/b402/bazaar/resources). Failure is a warning; it does not block preparation.
5. **Receipt.** Totals, pending confirmation, SHA-256 of the canonical JSON. Hosted receipts on Render live in `/tmp` and disappear after sleep/redeploy.

## What is real, and what is not

Say this out loud in the demo.

**Real**

- Binance `USDCUSDT` last price (testnet, then mainnet public ticker).
- B402 Bazaar public discovery (supporting evidence).
- x402 v2 payment requirements, also served as HTTP 402.

**Not settled**

- No signature, no broadcast, no B402 merchant settle.
- Agentic Wallet can preview requirements locally (`baw x402-payment preview`). Allot does not call `sign` or `wallet send`.
- Live Binance Pay. Demo preview only.

Rail decision: **Wallet preview plus demo-only payout preparation. No signing.**

## The booked three

| Name | City | Share of the spend pool | Why |
| --- | --- | --- | --- |
| Amara Okafor | Lagos | 40% | rent and food |
| Kwame Boateng | Accra | 35% | studio invoice |
| Elena Cruz | Manila | 25% | design retainer |

$400 monthly. 80% ($320) is prepared as payment requirements. 20% ($80) stays held in the book. Pair is USDCUSDT.

## Run it

Python 3.11+ locally (Render uses 3.13). No third-party packages.

```bash
python -m allot health
python -m allot parse 'send $400 to three people monthly, 80% to spend, 20% held'
python -m allot pay 'send $400 to three people monthly, 80% to spend, 20% held'
python -m allot serve
```

Then open [http://127.0.0.1:8765](http://127.0.0.1:8765). Desktop only. Fast probe: [http://127.0.0.1:8765/healthz](http://127.0.0.1:8765/healthz).

```bash
python -m unittest discover -s tests -v
```

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

Tools: `parse_payout_book`, `execute_payout` (preparation only), `list_receipts`, `get_receipt`, `verify_receipt`.

## Why this shape

Governor and Deltr placed on writeup as much as code. The sentence we are defending is not "we integrated five APIs". It is: **a non-trader can read the paper in fifteen seconds, and the paper tells the truth about the rail.**

`execute_payout(instruction) -> receipt` prepares payment requirements. It does not transfer money.

## Eligibility (read before you tweet)

Hackathon named exclusions: United States, United Kingdom, EEA, Hong Kong, Singapore. Nigeria is not on that named list. Binance's live [List of Prohibited Countries](https://www.binance.com/en/terms) still has to be checked by the person submitting — naira rails are suspended; this demo never touches NGN.

Entry does not count without all three: follow + repost, reply with video and GitHub, **survey form**.

## License

Hackathon demo. Testnet only. Not an offer to transmit money in production.
