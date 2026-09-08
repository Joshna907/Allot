# Two-person split — you and Joshna

Repo: [PayoutPilot](https://github.com/Joshna907/PayoutPilot). Product name in the demo: **Allot**. Do not rename tonight.

Deadline: **8 Sept 2026, 23:59 UTC**. Submit at 80% rather than late.

---

## You (this machine) — demo + rails

You already have the code. You own anything that has to *run on screen*.

| Own | Do not touch unless it is on fire |
| --- | --- |
| `allot/` (parser, price, x402, `execute_payout`, HTTP server, MCP stdio) | Survey form, the tweet, GitHub settings |
| `web/index.html` (the counter the video points at) | Adding a fourth recipient, a risk gate, or a trading view |
| Binance MCP OAuth in Cursor | Live mainnet funding |
| Record the 90s video | |

**Today, in order**

1. Push this folder to Joshna’s repo (commands below). Tell her when it lands.
2. Cursor → MCP → enable `binance-mcp-server` → finish Binance login. Ask: *Use the Binance MCP Server to show the current USDCUSDT price.*
3. Confirm Nigeria on Binance’s live prohibited-countries list. If it is on that list, stop.
4. `python -m allot serve` → [http://127.0.0.1:8765](http://127.0.0.1:8765) → record the video from `SUBMISSION.md`.
5. Send Joshna the video file. Do not wait for the build to feel finished.

If the platform fights you, the floor is still: testnet price + Bazaar ping + hashed receipt. That is enough to film.

---

## Joshna — GitHub + entry paperwork

She created the repo. She owns anything a judge sees *without running the app*.

| Own | Do not rebuild |
| --- | --- |
| Repo public, README, LICENSE | `execute_payout`, x402, the HTML counter |
| Follow @Binance + repost the announcement | New features after freeze |
| Survey form (`SUBMISSION.md` has paste-ready answers) | |
| Quote-repost / reply: video + GitHub URL | |

**Today, in order**

1. Wait for the first push, then make **PayoutPilot public**.
2. Follow + repost **now**. Survey **now**. Do not leave either for 23:50.
3. Hold a slot for the video. When the file arrives, post the reply/quote with video + `https://github.com/Joshna907/PayoutPilot`.
4. If README needs a pass, edit `README.md` and `SUBMISSION.md` only.

Tweet draft is in `SUBMISSION.md`. GitHub link in that draft is this repo.

---

## Shared fences (both of you: the answer is no)

- No risk-gate module. No SMA / signals / alpha.
- Three recipients, `USDCUSDT`, monthly. Hardcoded in `data/book.json`.
- No auth, no user accounts, no database.
- Desktop only. Testnet / demo only.

Talk in the group chat at freeze. Do not add a fifth lane after that.
