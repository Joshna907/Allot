# Allot

Hackathon repo: [Joshna907/PayoutPilot](https://github.com/Joshna907/PayoutPilot). Two-person split: [`TEAM.md`](TEAM.md).

**Everyone built an agent that trades. This one pays.**

Allot is a cross-border payout agent for Binance Agent OS. A sender describes a payout book in plain English — *send $400 to three people monthly, 80% to spend, 20% held* — and Allot parses it, prices it on Binance, writes an [x402](https://developers.binance.com/en/docs/products/onchainpay-x402/introduction) envelope for each spend leg, and issues a receipt anyone can hash.

It is not a trading bot. It does not gate risk. It does not invent a fourth recipient. Three names, one pair, one schedule.

## The gap

Track A filled up with trader copilots and safety layers. The safety-layer lane already has Governor, CHARTER, Countersign, Magister, Haptix, Gate, and Deltr. The SMA20/50 lane is a pile of the same chart. Nobody shipped agent-driven **payments**. Nobody used x402 or Binance Pay for a non-trader.

Remittance is the job most people actually have. Allot is the counter for that job.

## What it does

1. **Parse.** A sentence becomes a validated instruction. Recipients, pair (`USDCUSDT`), and cadence (`monthly`) are the book. Off-book amounts snap back. Trading language is rejected.
2. **Price.** Live last price from Binance Spot Testnet, with the public mainnet ticker as fallback.
3. **Envelope.** Each spend leg is an x402 v2 `PaymentRequired` object for BSC USDT (`exact` scheme), plus the base64 `PAYMENT-REQUIRED` header the protocol expects.
4. **Discover.** A real call to [B402 Bazaar](https://www.binance.com/bapi/ramp/v1/public/ramp/b402/bazaar/resources) — Binance's public x402 catalog.
5. **Receipt.** Totals, pending settle, SHA-256 of the canonical JSON. Stored in `data/receipts.json`. No database, no accounts.

## What is real, and what is not

Say this out loud in the demo.

**Real**

- Binance `USDCUSDT` last price (testnet, then mainnet public ticker).
- B402 Bazaar public discovery.
- Protocol-correct x402 v2 payment envelopes.

**Not real tonight**

- On-chain `/papi/v2/b402/settle`. Binance hands that base URL out with a merchant `clientId`, RSA key, and IP allowlist. That is not a same-day signup.
- Withdrawals through Agent OS MCP. The [MCP server](https://developers.binance.com/en/docs/agent-native/mcp-server/agentic) can price and trade inside an Agentic sub-account. It cannot send to an external address. That is why payouts are x402-shaped, not "transfer out via MCP".
- Live Binance Pay. Demo Trading / testnet only.

Rail decision, made when the settle docs said "please contact us for access": **x402 envelopes + Bazaar + Binance price + demo settle.** Named fallback. Not a quiet extension.

## The booked three

| Name | City | Share of the spend pool | Why |
| --- | --- | --- | --- |
| Amara Okafor | Lagos | 40% | rent and food |
| Kwame Boateng | Accra | 35% | studio invoice |
| Elena Cruz | Manila | 25% | design retainer |

$400 monthly. 80% ($320) is sent. 20% ($80) stays held in the book. Pair is USDCUSDT. Change the names in `data/book.json` after the hackathon, not during it.

## Run it

Python 3.11+. No third-party packages.

```bash
python -m allot health
python -m allot parse 'send $400 to three people monthly, 80% to spend, 20% held'
python -m allot pay 'send $400 to three people monthly, 80% to spend, 20% held'
python -m allot serve
```

Then open [http://127.0.0.1:8765](http://127.0.0.1:8765). Desktop only.

```bash
python tests/test_allot.py
```

## Agent OS / MCP

Project `.cursor/mcp.json` points Cursor at Binance Agent OS:

```text
https://agent.binance.com/mcp/agentic
```

Connect it in Cursor MCP settings and complete the Binance OAuth consent. Do not paste that URL into chat. After it is connected, ask: *Use the Binance MCP Server to show the current USDCUSDT price.*

Allot also speaks MCP on stdio so an agent can parse and pay without the HTML counter:

```bash
python -m allot mcp
```

Tools: `parse_payout_book`, `execute_payout`, `list_receipts`, `verify_receipt`.

## Why this shape

Governor and Deltr placed on writeup as much as code. The sentence we are defending is not "we integrated five APIs". It is: **a non-trader can read the paper in fifteen seconds, and the paper tells the truth about the rail.**

`execute_payout(instruction) -> receipt` is the whole execution module. The UI is a money-order counter, not a dashboard.

## Eligibility (read before you tweet)

Hackathon named exclusions: United States, United Kingdom, EEA, Hong Kong, Singapore. Nigeria is not on that named list. Binance's live [List of Prohibited Countries](https://www.binance.com/en/terms) still has to be checked by the person submitting — naira rails are suspended; this demo never touches NGN.

Entry does not count without all three: follow + repost, reply with video and GitHub, **survey form**.

## License

Hackathon demo. Testnet only. Not an offer to transmit money in production.
