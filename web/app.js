const $ = (id) => document.getElementById(id);
const bookEl = $("book");
const notice = $("notice");
const paper = $("paper");
const run = $("run");
const preview = $("preview");
const STEPS = [
  "Parsing payout book",
  "Fetching Binance price",
  "Creating three payment requirements",
  "Issuing receipt",
];

const money = (value) =>
  Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok && data && data.error) throw new Error(data.error);
  if (!response.ok && data && data.errors) throw new Error(data.errors.join(" "));
  if (!response.ok) throw new Error("The counter could not finish that request.");
  return data;
}

function roster(book) {
  $("roster").innerHTML =
    `<h2>The three</h2>` +
    book.recipients
      .map(
        (person, i) => `
        <div class="person">
          <span class="n">${String(i + 1).padStart(2, "0")}</span>
          <div>
            <b>${esc(person.name)}</b>
            <small>${esc(person.city)} · ${esc(person.note)}</small>
          </div>
          <span class="share">${(person.share_bps / 100).toFixed(0)}%</span>
        </div>
      `,
      )
      .join("");
}

function startProgress() {
  let index = 0;
  notice.textContent = STEPS[0];
  return setInterval(() => {
    index = Math.min(index + 1, STEPS.length - 1);
    notice.textContent = STEPS[index];
  }, 420);
}

let onPaper = null;

function renderReceipt(receipt) {
  preview.classList.remove("show");
  onPaper = receipt.ok ? receipt : null;
  if (!receipt.ok) {
    notice.innerHTML =
      esc((receipt.errors || ["The book did not run."]).join(" ")) +
      ` <button class="ghost retry" type="button" id="retry-run">Retry</button>`;
    paper.classList.remove("show");
    return;
  }
  const warnings = [];
  if (receipt.instruction && receipt.instruction.warnings) {
    warnings.push(...receipt.instruction.warnings);
  }
  if (receipt.evidence && receipt.evidence.bazaar_discovery === false) {
    warnings.push("Bazaar discovery failed. Preparation continued without it.");
  }
  notice.textContent = warnings.join(" ");
  const spend = receipt.legs.filter((leg) => leg.role === "spend");
  const hold = receipt.legs.find((leg) => leg.role === "hold");
  paper.innerHTML = `
        <article class="receipt">
          <div class="mark-stamp">Demo / not settled</div>
          <div class="receipt-top">
            <div>
              <p class="kicker">Carbon copy</p>
              <h2>Payout receipt</h2>
            </div>
            <p class="serial">
              ${esc(receipt.receipt_id)}<br>
              ${esc(receipt.issued_at)}<br>
              ${esc(receipt.quote.symbol)} @ ${esc(receipt.quote.price)}<br>
              ${esc(receipt.quote.source)}
            </p>
          </div>
          <table>
            <thead>
              <tr><th>Name</th><th>City</th><th>USD</th><th>USDT</th><th>Status</th></tr>
            </thead>
            <tbody>
              ${spend
                .map(
                  (leg) => `
                <tr>
                  <td>${esc(leg.name)}<div class="muted">${esc(leg.note)}</div></td>
                  <td>${esc(leg.city)}</td>
                  <td>${money(leg.usd)}</td>
                  <td>${money(leg.usdt)}</td>
                  <td>${esc(leg.status)}</td>
                </tr>
              `,
                )
                .join("")}
              <tr class="hold">
                <td>${esc(hold.name)}<div class="muted">${esc(hold.note)}</div></td>
                <td>${esc(hold.city)}</td>
                <td>${money(hold.usd)}</td>
                <td>${money(hold.usdt)}</td>
                <td>${esc(hold.status)}</td>
              </tr>
            </tbody>
          </table>
          <div class="totals">
            <span>Gross</span><span>$${money(receipt.totals.gross_usd)}</span>
            <span>Prepared</span><span>$${money(receipt.totals.spend_usd)}</span>
            <span>Held</span><span>$${money(receipt.totals.hold_usd)}</span>
          </div>
          <p class="hash">
            Hash ${esc(receipt.receipt_hash)}<br>
            Pending: ${esc(receipt.pending)}
          </p>
          <p>
            <button class="ghost" type="button" id="check-hash" data-hash="${esc(receipt.receipt_hash)}">Verify receipt</button>
            <span id="check-out" class="muted"></span>
          </p>
          ${spend
            .map(
              (leg) => `
            <details class="evidence">
              <summary>x402 requirement — ${esc(leg.name)}</summary>
              <div class="copy-row">
                <a href="${esc(leg.payout_url)}">HTTP 402 endpoint</a>
                <button class="ghost copy-x402" type="button" data-copy="${esc(leg.x402.payment_required_header)}">Copy PAYMENT-REQUIRED</button>
              </div>
              <pre class="payload">${esc(JSON.stringify(leg.x402.payment_required, null, 2))}</pre>
            </details>
          `,
            )
            .join("")}
          <div class="bounds">
            <div>
              <h3>What is real</h3>
              <ul>${(receipt.what_is_real || []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
            </div>
            <div>
              <h3>What remains</h3>
              <ul>${(receipt.what_remains || receipt.what_is_not || []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
            </div>
          </div>
        </article>
      `;
  paper.classList.add("show");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  paper.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
  const verify = $("check-hash");
  if (verify) verify.focus();
}

async function prepare() {
  run.disabled = true;
  run.textContent = "Preparing…";
  const tick = startProgress();
  try {
    const receipt = await api("/api/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: bookEl.value }),
    });
    clearInterval(tick);
    renderReceipt(receipt);
  } catch (error) {
    clearInterval(tick);
    notice.innerHTML =
      esc(error.message || "The counter could not reach Allot.") +
      ` <button class="ghost retry" type="button" id="retry-run">Retry</button>`;
    paper.classList.remove("show");
  } finally {
    run.disabled = false;
    run.textContent = "Prepare payout";
  }
}

$("book-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await prepare();
});

document.addEventListener("click", async (event) => {
  const retry = event.target.closest("#retry-run");
  if (retry) {
    await prepare();
    return;
  }
  const copy = event.target.closest(".copy-x402");
  if (copy && copy.dataset.copy) {
    navigator.clipboard.writeText(copy.dataset.copy);
    copy.textContent = "Copied";
    return;
  }
  const button = event.target.closest("#check-hash");
  if (!button) return;
  const out = $("check-out");
  out.textContent = " Checking…";
  try {
    const result = await api("/api/verify/" + button.dataset.hash);
    out.textContent = result.ok ? " Hash matches the paper on disk." : " Hash does not match.";
    return;
  } catch (error) {
    if (!onPaper) {
      out.textContent = " " + (error.message || "Could not verify.");
      return;
    }
  }
  try {
    const result = await api("/api/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(onPaper),
    });
    out.textContent = result.ok
      ? " Hash matches. Recomputed from this receipt — the server's copy is gone."
      : " Hash does not match.";
  } catch (error) {
    out.textContent = " " + (error.message || "Could not verify.");
  }
});

$("parse-only").addEventListener("click", async () => {
  notice.textContent = "";
  try {
    const instruction = await api("/api/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: bookEl.value }),
    });
    if (!instruction.valid) {
      preview.classList.remove("show");
      notice.textContent = instruction.errors.join(" ");
      return;
    }
    const warnings = instruction.warnings.length
      ? `<p class="warnings">${esc(instruction.warnings.join(" "))}</p>`
      : "";
    preview.innerHTML = `
      <h2>Book checked</h2>
      <p>Three people, ${esc(instruction.schedule)}, ${esc(instruction.pair)}. ${instruction.spend_bps / 100}% is prepared to send and ${instruction.hold_bps / 100}% stays held.</p>
      <p class="preview-total">$${money(instruction.gross_usd)} booked</p>
      ${warnings}
    `;
    preview.classList.add("show");
  } catch (error) {
    preview.classList.remove("show");
    notice.textContent = error.message || "The counter could not check this book.";
  }
});

api("/api/health")
  .then((health) => {
    const quote = health.quote || {};
    const bazaar = health.bazaar || {};
    $("rail-line").textContent = quote.ok
      ? `${quote.symbol} ${quote.price} · ${quote.source} · Bazaar ${bazaar.listed_resources ?? "—"} listings`
      : "Ticker unreachable — start python -m allot serve";
  })
  .catch(() => {
    $("rail-line").textContent = "Counter offline. Run python -m allot serve";
  });

api("/api/book")
  .then(roster)
  .catch(() => {
    notice.textContent = "Could not load the booked three. Is the Allot server running?";
  });
