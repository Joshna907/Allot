import {esc,attr,usd,numeric,formatUtc,shortHash,humanStatus,percent} from "/lib.js";
export const GITHUB="https://github.com/Joshna907/Allot";
export const link=(href,label,primary=false)=>`<a class="button ${primary?"button-primary":"button-secondary"}" href="${attr(href)}" data-link>${esc(label)}</a>`;
export const external=(href,label)=>{
 try { if(!["http:","https:"].includes(new URL(href).protocol))return `<span>${esc(label)} (invalid destination)</span>`; }
 catch { return `<span>${esc(label)} (destination unavailable)</span>`; }
 return `<a href="${attr(href)}" target="_blank" rel="noreferrer">${esc(label)} <span aria-hidden="true">↗</span><span class="sr-only"> (external destination)</span></a>`;
};
export const heading=(title,intro,action="")=>`<div class="page-heading"><div><h1 tabindex="-1">${esc(title)}</h1><p>${esc(intro)}</p></div>${action}</div>`;
export function header(path,product=false){
 const items=product?[["/app","Payout book"],["/receipts","Activity"],["/how-it-works","Help"]]:[["/how-it-works","How it works"],["/verify","Verify receipt"]];
 return `<header class="site-header"><div class="shell nav-shell"><a class="wordmark" href="/" data-link aria-label="Allot home">Allot</a><nav class="main-nav" aria-label="Main navigation">${items.map(([href,label])=>`<a href="${href}" data-link ${path===href||(href==="/receipts"&&path.startsWith("/receipts/"))||(href==="/app"&&path.startsWith("/app/"))?'aria-current="page" class="active"':""}>${label}</a>`).join("")}</nav><div class="nav-actions">${product?'<span class="demo-badge">Demo only. No funds move.</span>':link("/app","Open payout book",true)}</div></div></header>`;
}
export function footer(product=false){
 if(product)return `<footer class="workspace-footer shell"><span>Shared demo. Receipts may disappear after redeployment.</span><nav aria-label="Support">${external(GITHUB,"GitHub")} <a href="/verify" data-link>Verify receipt</a> <a href="/how-it-works" data-link>Help</a></nav></footer>`;
 return `<footer class="site-footer"><div class="shell footer-grid"><div class="footer-intro"><a class="wordmark" href="/" data-link>Allot</a><p>A plain-English payout book, a clear allocation, and a receipt you can check.</p></div><div><h2>Product</h2><a href="/app" data-link>Open payout book</a><a href="/receipts" data-link>Demo activity</a><a href="/verify" data-link>Verify receipt</a></div><div><h2>Learn</h2><a href="/how-it-works" data-link>How it works</a><a href="/writeup" data-link>Build notes</a></div><div><h2>Project</h2>${external(GITHUB,"GitHub")}${external("https://developers.binance.com/en/docs/products/onchainpay-x402/introduction","x402 documentation")}${external("https://agent.binance.com/","Binance Agent OS")}</div></div><div class="shell footer-bottom"><p>Demo preparation only. No custody, signatures, broadcast, or settlement. Monthly describes the allocation, not an active automatic payment.</p><p>© 2026 Allot<br>Binance Agent OS Mini Hackathon</p></div></footer>`;
}
export const skeleton=(label="Loading")=>`<div class="skeleton" role="status" aria-busy="true"><span class="sr-only">${esc(label)}</span><span style="--w:85%"></span><span style="--w:65%"></span><span style="--w:75%"></span></div>`;
export const errorState=(title,message,id="")=>`<div class="state-panel state-error" role="alert"><h2>${esc(title)}</h2><p>${esc(message)}</p>${id?`<button class="button button-secondary" id="${id}">Try again</button>`:""}</div>`;
export const empty=(title,message,href="/app/prepare",label="Prepare payout")=>`<div class="state-panel"><h2>${esc(title)}</h2><p>${esc(message)}</p>${link(href,label,true)}</div>`;
export const notice=(text)=>`<p class="context-note">${esc(text)}</p>`;
export const warningList=(warnings=[])=>warnings.length?`<aside class="warning-panel" role="status"><strong>Check these adjustments</strong><ul>${warnings.map(w=>`<li>${esc(w)}</li>`).join("")}</ul></aside>`:"";
export function totals(data,prepared=false){
 return `<dl class="amount-summary"><div><dt>Total budget</dt><dd>${usd(data.gross_usd)}</dd></div><div><dt>${prepared?"Requirements prepared":"Allocated to recipients"}</dt><dd>${usd(data.spend_usd)}</dd></div><div><dt>Excluded (held in book)</dt><dd>${usd(data.hold_usd)}</dd></div></dl>`;
}
export function allocations(rows,usdt=false){
 return `<div class="table-wrap"><table><caption class="sr-only">Recipient allocation and excluded amount</caption><thead><tr><th scope="col">Recipient</th><th scope="col">Purpose</th><th scope="col">USD allocation</th>${usdt?'<th scope="col">USDT equivalent</th><th scope="col">Result</th>':""}</tr></thead><tbody>${rows.map(row=>`<tr class="${row.role==="hold"?"held-row":""}"><td><strong>${esc(row.role==="hold"?"Excluded from preparation":row.name)}</strong><span>${esc(row.role==="hold"?"No payment requirement created":row.city)}</span></td><td>${esc(row.role==="hold"?"Recorded only. Allot does not hold funds.":row.note)}</td><td>${usd(row.usd)}</td>${usdt?`<td>${esc(numeric(row.usdt))}</td><td>${esc(humanStatus(row.status))}</td>`:""}</tr>`).join("")}</tbody></table></div>`;
}
export function roster(book){
 return `<div class="recipient-list">${book.recipients.map(r=>`<div class="recipient-row"><div><strong>${esc(r.name)}</strong><span>${esc(r.city)} · ${esc(r.note)}</span></div><div class="recipient-share"><strong>${percent(r.share_bps)}</strong><span>of recipient allocation</span></div></div>`).join("")}</div>`;
}
export function receiptRow(r){
 return `<article class="receipt-row" data-search="${attr((r.receipt_id+" "+r.receipt_hash).toLowerCase())}"><div><a class="receipt-id" href="/receipts/${encodeURIComponent(r.receipt_id)}" data-link>Monthly payout preparation</a><span>${formatUtc(r.issued_at)}</span><code>${esc(r.receipt_id)}</code></div><div><span>Total budget</span><strong>${usd(r.totals?.gross_usd)}</strong></div><div><span>Recipients</span><strong>${(r.legs||[]).filter(l=>l.role==="spend").length}</strong></div><div><span>${esc(humanStatus(r.status))}</span><strong>${usd(r.totals?.spend_usd)} prepared</strong><span>${usd(r.totals?.hold_usd)} excluded</span></div><div class="row-actions"><a href="/receipts/${encodeURIComponent(r.receipt_id)}" data-link>View receipt<span class="sr-only"> ${esc(r.receipt_id)}</span></a></div></article>`;
}
export function verification(result){
 if(result===undefined)return skeleton("Checking receipt integrity");
 if(result===null)return `<div class="state-panel"><h2>Could not verify</h2><p>The receipt remains readable. Verification is unavailable; try checking again.</p></div>`;
 return `<div class="verification-panel ${result.ok?"verification-ok":"verification-bad"}" role="${result.ok?"status":"alert"}"><div><h2>${result.ok?"Receipt matches":"Receipt changed"}</h2><p>${result.ok?"The content matches its printed hash.":"The stored content no longer matches its printed hash. Treat this receipt as inconsistent."}</p><p>This checks content integrity, not sender identity or blockchain settlement.</p></div><details><summary>Compare full hashes</summary><dl class="hash-list"><dt>Printed hash</dt><dd>${esc(result.claimed)}</dd><dt>Recomputed hash</dt><dd>${esc(result.recomputed)}</dd></dl></details></div>`;
}
export function rails(r){
 const legs=(r.legs||[]).filter(l=>l.role==="spend");
 return `<section class="receipt-section"><h2>Preparation evidence</h2><ul class="evidence-checks"><li>Instruction validated and allocation recorded</li><li>${r.evidence?.binance_price?"Binance price received":"Price evidence unavailable"}</li><li>${legs.filter(l=>l.x402?.payment_required).length} payment requirements recorded</li><li>Excluded amount recorded without a payment requirement</li><li>Receipt hash recorded</li></ul>
 ${!r.evidence?.bazaar_discovery?'<aside class="warning-panel"><strong>Discovery unavailable</strong><p>Optional Bazaar discovery did not succeed. This does not invalidate the prepared requirements.</p></aside>':""}
 <details class="technical"><summary>Technical evidence and payment endpoints</summary><div class="details-body">
 <dl class="detail-list"><dt>Quote pair</dt><dd>${esc(r.quote?.symbol||r.instruction?.pair)}</dd><dt>Quote price</dt><dd>${esc(r.quote?.price)}</dd><dt>Price source</dt><dd>${esc(r.quote?.source)}</dd><dt>Bazaar discovery</dt><dd>${r.evidence?.bazaar_discovery?"Available":"Unavailable"} · ${esc(r.bazaar?.note||"")}</dd><dt>Wallet preview</dt><dd>${esc(r.evidence?.wallet_preview||"Not run")}</dd><dt>Network envelope</dt><dd>${esc(legs[0]?.network||"Not recorded")} (payload format only, no transaction broadcast)</dd></dl>
 <p>These are unsigned x402 requirements. HTTP 402 means payment is required, not paid. The demo rejects PAYMENT-SIGNATURE headers.</p>
 ${legs.map(l=>`<details class="endpoint"><summary>${esc(l.name)}: ${usd(l.usd)} requirement</summary><div class="details-body"><p><strong>Endpoint</strong><br><code>${esc(l.payout_url)}</code></p><div class="inline-actions">${l.payout_url?external(l.payout_url,"Open HTTP 402 endpoint"):"Endpoint unavailable"}<button class="button button-secondary copy-value" data-copy="${attr(l.x402?.payment_required_header||"")}">Copy header</button><button class="button button-secondary copy-value" data-copy="${attr(JSON.stringify(l.x402?.payment_required,null,2))}">Copy payload</button></div><details><summary>PAYMENT-REQUIRED header</summary><pre>${esc(l.x402?.payment_required_header)}</pre></details><pre>${esc(JSON.stringify(l.x402?.payment_required,null,2))}</pre></div></details>`).join("")}
 </div></details></section>`;
}
