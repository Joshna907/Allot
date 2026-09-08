# Two-person split — Allot

Repo: [Joshna907/Allot](https://github.com/Joshna907/Allot). Product name: **Allot**.

## You — runtime, receipts/API, demo UI, deploy, submission engineering

Sections 1, 4, 5, 6 of the implementation plan.

- Env-driven host/port, `/healthz`, Render (`render.yaml`).
- Receipt IDs, hashes, locks, HTTP 402, MCP tools.
- Counter UI: Prepare payout, DEMO stamp, evidence, verify.
- README / tweet copy / GitHub naming.

Do not add a fourth recipient, a risk gate, or a trade view.

## Joshna — parser + x402/price rail (lanes 2 and 3)

- Natural-language book → instruction.
- Binance USDCUSDT quote + fallback.
- x402 `PaymentRequired` generation.
- Optional local `baw x402-payment preview` (no sign, no send).

If those files need a tweak for PUBLIC_BASE_URL or HTTP 402, coordinate — the contracts already expect `payment-required` legs and public payout URLs.

## Shared fences

Three recipients, USDCUSDT, monthly. No auth, no database, no mobile, no mainnet funding, no signing.
