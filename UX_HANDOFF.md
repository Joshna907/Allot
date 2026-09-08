# Allot UX handoff

## Run

From this checkout, run `python -m allot serve`. No npm or frontend build.
Use one server per checkout and configure PUBLIC_BASE_URL to the origin visitors
actually use. Existing receipt payloads retain their original endpoint origin.

## Implemented navigation

- Public: landing, How it works, Verify receipt. Build notes and repository in footer.
- Product: Payout book, Activity, Help. Compact persistent no-funds notice.
- /app: fixed book, exact default allocation, draft, rail check, recent preparations.
- /app/prepare: Describe / Review / Prepare. Review query state can be restored.
- /receipts: shared activity, search in URL, refresh and empty/error states.
- /receipts/{id}: outcome, exact allocations, integrity, original instruction,
  expandable rail evidence, download, copy, print and another preparation.
- /verify: ID/hash validation, match/mismatch/unavailable/not-found states.
- Unknown routes and missing receipts: branded recovery with proper HTTP status.

## Teammate rail contract

Keep execute_payout(instruction) -> receipt. No wallet calls from the browser.

Success fields consumed:
receipt_id, issued_at, status, instruction, quote, legs, totals, receipt_hash,
evidence, bazaar, what_remains.

Spend legs use role=spend, usd, usdt, name, city, note, status=payment-required,
payout_url, network, and x402.payment_required/payment_required_header.
Held leg uses role=hold and no payment requirement.

Totals use decimal strings: gross_usd, spend_usd, hold_usd.
Quote source is displayed as returned. Fee estimates, signing, settlement,
transaction hashes, and automated scheduling are deliberately not invented.

A quote failure returns ok=false, errors, quote.ok=false, retryable=true.
Bazaar failure remains a non-blocking receipt warning.
GET /api/health provides an on-demand availability check, not a locked quote.

The HTTP wrapper accepts optional request_id for bounded in-process successful
retry deduplication (256 recent attempts). Different text with the same key is
rejected. The cache does not survive a server restart or coordinate multiple
processes. After a lost response, check activity before retrying.

## Parser changes

Labelled percentages are interpreted by meaning, including held-first and
verb-first wording. Ambiguous, negative, fractional, extra, or non-totaling
percentages are rejected. Valid parse responses include allocation and totals,
using the same Decimal calculation as execution. The browser does not
independently recalculate the review amounts.

The parser is deterministic, not an unrestricted natural-language model.

## Styling handoff

- web/app.js: route dispatch, request-generation guards, focus and metadata.
- web/public.js: landing, help, build notes.
- web/product.js: book, preparation, activity, receipts, verification.
- web/ui.js: reusable semantic components and evidence disclosures.
- web/lib.js: fetch, draft, escaping, copy/export, formatting.
- web/styles.css: neutral tokens, desktop layout, narrow-window fallback,
  dark system theme, focus and reduced motion, print rules.

Replace typography, colors and spacing without changing API contracts, input
labels, actions, state guards, monetary strings, or demo boundary copy.
No fake balances, signatures, transfer results, live countdowns or analytics.

## Verification performed September 8, 2026

- Python: 31 regression tests passed.
- Node: 12 frontend component tests passed.
- All active JavaScript modules passed syntax checks.
- Browser: actual held-first sentence -> $320 spend / $80 excluded ->
  Binance spot-testnet quote -> three x402 requirements -> stored receipt ->
  successful hash verification.
- Browser Back restored review after visiting activity.
- Activity's unmatched search removed rows and offered clear search.
- Standalone query-parameter verification passed.
- Expandable recipient payload and copy feedback were exercised.
- Desktop book layout inspected.

Browser automation did not confirm a blob-download event, so canonical exports
now use the existing receipt endpoint with Content-Disposition: attachment.
The revised canonical download was confirmed by a browser download event.
A newly created in-memory fallback remains exportable as a JSON Blob.
Server attachment behavior is covered by an HTTP regression test.

## Deliberate boundaries

Shared JSON receipt storage, no auth/database, no editable wallets or extra
recipients, no live funding, no automatic monthly execution. Integrity checks
are hash consistency checks, not authentication or settlement proof.
