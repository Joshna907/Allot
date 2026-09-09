import {api,postJson,DEFAULT_BOOK_TEXT,esc,usd,formatUtc} from "/lib.js";
import {mountHeroFlow} from "/hero-canvas.js?v=5";
import {heading,link,external,GITHUB,skeleton,errorState,empty,totals,allocations,receiptRow,notice,verification} from "/ui.js";

const referenceWorkflow=()=>`<section class="interactive-scroll-scene" id="how-allot-works" aria-labelledby="allocation-walkthrough-title"><div class="interactive-layout"><div class="interactive-left"><div class="interactive-left-header"><h2 id="allocation-walkthrough-title">One instruction.<br>A record you can trust.</h2><p>Follow the book from plain language to a receipt you can check.</p></div><div class="interactive-accordion" role="tablist" aria-label="Allocation workflow"><button class="interactive-list-item active" type="button" role="tab" aria-selected="true" aria-controls="allocation-visual" data-step="0"><h3>Describe</h3><p>Write your payout in everyday language.</p></button><button class="interactive-list-item" type="button" role="tab" aria-selected="false" aria-controls="allocation-visual" data-step="1"><h3>Review</h3><p>Check every amount and correction.</p></button><button class="interactive-list-item" type="button" role="tab" aria-selected="false" aria-controls="allocation-visual" data-step="2"><h3>Prepare</h3><p>Create unsigned payment requirements.</p></button><button class="interactive-list-item" type="button" role="tab" aria-selected="false" aria-controls="allocation-visual" data-step="3"><h3>Verify</h3><p>Keep a receipt and check its integrity.</p></button></div></div><div class="interactive-right"><div class="workflow-slides" aria-hidden="true"><figure class="workflow-slide active" data-slide="0"><img src="/assets/workflow-river.webp" alt=""></figure><figure class="workflow-slide" data-slide="1"><img src="/assets/workflow-lake.webp" alt=""></figure><figure class="workflow-slide" data-slide="2"><img src="/assets/workflow-glacier.webp" alt=""></figure><figure class="workflow-slide" data-slide="3"><img src="/assets/workflow-coast.webp" alt=""></figure></div><div class="workflow-photo-scrim" aria-hidden="true"></div><div class="interactive-visual" id="allocation-visual" role="tabpanel" aria-live="polite">${skeleton("Loading allocation")}</div><div class="workflow-pagination" aria-hidden="true"><span class="active"></span><span></span><span></span><span></span></div></div></div></section>`;

const receiptPreview=()=>`<div class="ledger-terminal ledger-preview"><div class="ledger-header"><div class="ledger-badge">DEMO PREVIEW</div><div class="ledger-time">Create a preparation to save a live receipt</div></div><div class="ledger-body"><div class="ledger-row"><span class="ledger-label">Receipt reference</span><code class="ledger-hash">ALLOT-DEMO-PREVIEW</code></div><div class="ledger-grid"><div><span class="ledger-label">Total budget</span><strong class="ledger-value">$400.00</strong></div><div><span class="ledger-label">Recipients</span><strong class="ledger-value">3</strong></div><div><span class="ledger-label">Prepared</span><strong class="ledger-value ledger-value-ready">$320.00</strong></div><div><span class="ledger-label">Excluded</span><strong class="ledger-value">$80.00</strong></div></div></div><div class="ledger-footer"><p class="ledger-status">Preview only. No receipt has been created and no funds moved.</p><a class="button button-small button-secondary" href="/app" data-link>Open payout book</a></div></div>`;
export const landingPage={
 title:"A clear plan for every payout",
 description:"Describe a monthly payout, review three recipient allocations, and prepare a receipt you can check. Demo only, no funds move.",
 render:()=>`<div class="landing-page"><section class="hero shell"><canvas class="hero-flow" id="hero-flow"></canvas><div class="hero-veil"></div><div class="hero-copy"><h1>One budget.<br>Everyone accounted for.</h1><p>Describe your payout. Review each person's share. Prepare a receipt you can check.</p><div class="hero-actions">${link("/app","Open payout book",true)}<a href="#receipt-proof">See receipt proof</a></div></div><aside class="hero-book" id="hero-book" aria-label="Live demo payout book">${skeleton("Loading the demo allocation")}</aside></section><div class="shell">${notice("Demo only. No funds move. Monthly allocations are prepared manually, not scheduled automatically.")}<section class="workflow-section" id="how-allot-works"><span class="workflow-corner workflow-corner-tl" aria-hidden="true"></span><span class="workflow-corner workflow-corner-tr" aria-hidden="true"></span><span class="workflow-corner workflow-corner-bl" aria-hidden="true"></span><span class="workflow-corner workflow-corner-br" aria-hidden="true"></span><div class="workflow-inner"><header class="workflow-heading"><div class="workflow-intro"><p>How Allot works</p><p>A $400 monthly instruction becomes a checked allocation, unsigned requirements, and a receipt you can verify. No funds move.</p></div><h2><span>From a sentence</span><span>to a clear record.</span></h2></header><div class="workflow-body"><div class="workflow-index" id="workflow-index" role="tablist" aria-label="Allot workflow"><button class="workflow-step active" type="button" role="tab" aria-selected="true" aria-controls="interactive-visual" data-step="0"><span class="workflow-step-number">01</span><strong>Describe</strong><span class="workflow-step-copy">Name the budget, recipients, split, and monthly intent.</span></button><button class="workflow-step" type="button" role="tab" aria-selected="false" aria-controls="interactive-visual" data-step="1"><span class="workflow-step-number">02</span><strong>Review</strong><span class="workflow-step-copy">Confirm $320 across three people and $80 excluded.</span></button><button class="workflow-step" type="button" role="tab" aria-selected="false" aria-controls="interactive-visual" data-step="2"><span class="workflow-step-number">03</span><strong>Prepare</strong><span class="workflow-step-copy">Create unsigned x402 requirements with Binance pricing.</span></button><button class="workflow-step" type="button" role="tab" aria-selected="false" aria-controls="interactive-visual" data-step="3"><span class="workflow-step-number">04</span><strong>Verify</strong><span class="workflow-step-copy">Check the saved receipt's content integrity.</span></button></div><div class="workflow-panel" id="interactive-visual" role="tabpanel" aria-live="polite">${skeleton("Loading workflow visualization")}</div></div></div><div class="workflow-scroll-stages" aria-hidden="true"><span data-workflow-stage="0"></span><span data-workflow-stage="1"></span><span data-workflow-stage="2"></span><span data-workflow-stage="3"></span></div></section><section class="content-section" id="receipt-proof"><div class="section-heading"><h2>A record you can come back to.</h2><p>The newest preparation from this shared demo appears below. Download receipts you want to keep.</p></div><div class="ledger-terminal-wrapper"><div id="latest-receipt">${skeleton("Loading receipt proof")}</div></div></section><section class="content-section duality-grid"><div class="duality-card card-action"><h2>What happens here</h2><p>Your instruction becomes a checked allocation. Allot retrieves a Binance quote, prepares x402 requirements, and saves a hashed receipt.</p><div class="edge-stream"></div></div><div class="duality-card card-secure"><h2>What does not happen</h2><p>No wallet credentials, signatures, broadcasts, or settlement. This is a payout preparation demo, not a live transfer service.</p><div class="laser-scanner"></div></div></section><section class="faq-section"><div class="faq-hero"><h1>YOU HAVE QUESTIONS.<br>WE HAVE <span class="badge-answers"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg></span> ANSWERS.</h1><div class="scroll-explore">Scroll to explore &darr;</div></div><div class="faq-grid"><div class="faq-left"><p>Whatever you need to know about verifiable allocations, we got you covered.</p></div><div class="faq-list">
 <details><summary>What is a payout book?</summary><p>A record of who an allocation is for, how much each person receives, and how often it is intended. Here, the recipients, budget, and monthly frequency are fixed.</p></details>
 <details><summary>Does the demo send money every month?</summary><p>No. Monthly is the intended allocation frequency. Each demonstration must be started manually, and no transfer occurs.</p></details>
 <details><summary>What does prepared mean?</summary><p>The information needed to request a payment exists. No wallet approved it and no recipient was paid.</p></details>
 <details><summary>What happens to the held amount?</summary><p>It is excluded from the payment requirements. There is no deposit, custody, lock, or automatic release.</p></details>
 <details><summary>What does verification prove?</summary><p>It checks whether the receipt content matches its printed hash. It does not establish sender identity, authenticity, or settlement.</p></details>
 <details><summary>Why can a receipt disappear?</summary><p>The demo stores receipts in a JSON file. Hosted temporary storage can reset after redeployment. Downloading a receipt preserves a readable copy.</p></details>
 <details><summary>Is Allot a trading bot?</summary><p>No. The quote is used to prepare a payout allocation, not to predict markets or place trades.</p></details></div></div></section><section class="final-cta"><canvas class="hero-flow" id="cta-flow"></canvas><div class="hero-veil"></div><div class="cta-content"><div><h2>Start with one sentence.</h2><p>See what Allot understands before anything is prepared.</p></div>${link("/app","Open payout book",true)}</div></section></div></div>`,
 async mount({root,alive}){
   const stopHeroFlow=mountHeroFlow(root.querySelector("#hero-flow"));
   const stopCtaFlow=mountHeroFlow(root.querySelector("#cta-flow"));
   let stopWorkflow=()=>{};
   const heroCleanup=window.setInterval(()=>{if(!alive()){stopHeroFlow();stopCtaFlow();stopWorkflow();window.clearInterval(heroCleanup);}},500);
   const workflow=root.querySelector(".workflow-section");
   if(workflow){workflow.insertAdjacentHTML("beforebegin",referenceWorkflow());workflow.remove();}

  async function book(){
   const heroBook=root.querySelector("#hero-book");
   if(heroBook)heroBook.innerHTML=skeleton("Loading allocation");
   try{
    const parsed=await postJson("/api/parse",{text:DEFAULT_BOOK_TEXT});if(!alive())return;
    if(heroBook)heroBook.innerHTML=`<div class="preview-head"><h2>Monthly demo book</h2><strong>${usd(parsed.totals.gross_usd)}</strong></div><p>${usd(parsed.totals.spend_usd)} allocated to three people</p><div class="recipient-list">${parsed.allocation.filter(r=>r.role==="spend").map(r=>`<div class="recipient-row"><div><strong>${esc(r.name)}</strong><span>${esc(r.city)}</span></div><strong>${usd(r.usd)}</strong></div>`).join("")}</div><p class="preview-held">${usd(parsed.totals.hold_usd)} excluded from preparation</p>`;
    const visual=root.querySelector("#allocation-visual");
    const items=root.querySelectorAll(".interactive-list-item");
    if(visual&&items.length){
      const slides=root.querySelectorAll(".workflow-slide");
      const cardContent=[
        `<div class="interactive-card"><header class="interactive-card-head"><span>Monthly payout book</span><b>Describe</b></header><span class="interactive-kicker">Plain-language instruction</span><blockquote>${esc(DEFAULT_BOOK_TEXT)}</blockquote><div class="interactive-card-facts"><span>Budget <strong>$400.00</strong></span><span>Frequency <strong>Monthly</strong></span></div></div>`,
        `<div class="interactive-card interactive-table"><header class="interactive-card-head"><span>Monthly payout book</span><b>Review</b></header><div class="interactive-amount"><strong>${usd(parsed.totals.gross_usd)}</strong><span>${usd(parsed.totals.spend_usd)} allocated</span></div>${allocations(parsed.allocation)}</div>`,
        `<div class="interactive-card"><header class="interactive-card-head"><span>Payment requirements</span><b>Prepare</b></header><span class="interactive-kicker">Unsigned x402 records</span><strong class="balance-amount">3 requirements</strong><p>Each recipient gets a prepared requirement. Nothing is signed, sent, or settled.</p><div class="interactive-card-facts"><span>Prepared <strong>$320.00</strong></span><span>Excluded <strong>$80.00</strong></span></div></div>`,
        `<div class="interactive-card"><header class="interactive-card-head"><span>Saved receipt</span><b>Verify</b></header><span class="interactive-kicker">Content integrity</span><strong class="interactive-check">Receipt matches</strong><p>SHA-256 checks the saved content. It does not prove sender identity or settlement.</p><code class="interactive-hash">ALLOT-9F3C-71E2-4A06</code></div>`
      ];
      visual.innerHTML=cardContent.map((content,index)=>`<div class="interactive-panel-layer${index===0?" active":""}" aria-hidden="${index===0?"false":"true"}" data-panel="${index}">${content}</div>`).join("");
      const panels=visual.querySelectorAll(".interactive-panel-layer");
      const pagination=root.querySelectorAll(".workflow-pagination span");
      const scene=root.querySelector(".interactive-scroll-scene");
      let activeStep=-1;
      const renderStep=(step)=>{
        if(step===activeStep)return;
        activeStep=step;
        items.forEach((item,itemIndex)=>{const active=itemIndex===step;item.classList.toggle("active",active);item.setAttribute("aria-selected",String(active));item.tabIndex=active?0:-1;});
        slides.forEach((slide,index)=>slide.classList.toggle("active",index===step));
        panels.forEach((panel,index)=>{const active=index===step;panel.classList.toggle("active",active);panel.setAttribute("aria-hidden",String(!active));});
        pagination.forEach((indicator,index)=>indicator.classList.toggle("active",index===step));
      };
      items.forEach((item,itemIndex)=>{
        item.onclick=()=>renderStep(itemIndex);
        item.onkeydown=event=>{const direction={ArrowDown:1,ArrowRight:1,ArrowUp:-1,ArrowLeft:-1}[event.key];if(!direction)return;event.preventDefault();const next=(itemIndex+direction+items.length)%items.length;items[next].focus();renderStep(next);};
      });
      let scrollFrame=0;
      const updateFromScroll=()=>{
        scrollFrame=0;
        if(!scene||!alive())return;
        const bounds=scene.getBoundingClientRect();
        const distance=Math.max(1,scene.offsetHeight-window.innerHeight);
        const progress=Math.max(0,Math.min(1,-bounds.top/distance));
        renderStep(Math.min(items.length-1,Math.floor(progress*items.length)));
      };
      const requestScrollUpdate=()=>{if(!scrollFrame)scrollFrame=window.requestAnimationFrame(updateFromScroll);};
      window.addEventListener("scroll",requestScrollUpdate,{passive:true});
      window.addEventListener("resize",requestScrollUpdate,{passive:true});
      stopWorkflow=()=>{window.removeEventListener("scroll",requestScrollUpdate);window.removeEventListener("resize",requestScrollUpdate);if(scrollFrame)window.cancelAnimationFrame(scrollFrame);};
      updateFromScroll();
    }
   }catch(error){if(alive()){if(heroBook)heroBook.innerHTML=errorState("Demo book unavailable",error.message,"retry-book-0");root.querySelectorAll('[id^="retry-book-"]').forEach(button=>button.onclick=book);}}
  }
  async function latest(){
   const target=root.querySelector("#latest-receipt");
   try{const rows=await api("/api/receipts");if(!alive())return;
    if(!rows.length){target.innerHTML=receiptPreview();return;}
    const r=rows[0];
    
    target.innerHTML = `
      <div class="ledger-terminal">
        <div class="ledger-header">
          <div class="ledger-badge">VERIFIED BLOCK</div>
          <div class="ledger-time">${formatUtc(r.issued_at)}</div>
        </div>
        <div class="ledger-body">
          <div class="ledger-row">
            <span class="ledger-label">Transaction Hash</span>
            <code class="ledger-hash scramble-text" data-hash="${esc(r.receipt_id)}">........................................</code>
          </div>
          <div class="ledger-grid">
            <div><span class="ledger-label">Total Budget</span><strong class="ledger-value">${usd(r.totals?.gross_usd)}</strong></div>
            <div><span class="ledger-label">Recipients</span><strong class="ledger-value">${(r.legs||[]).filter(l=>l.role==="spend").length}</strong></div>
            <div><span class="ledger-label">Prepared</span><strong class="ledger-value" style="color:#7bd3a7">${usd(r.totals?.spend_usd)}</strong></div>
            <div><span class="ledger-label">Excluded</span><strong class="ledger-value">${usd(r.totals?.hold_usd)}</strong></div>
          </div>
        </div>
        <div class="ledger-footer">
          <p id="latest-check" role="status" class="ledger-status"><span class="radar-dot"></span> Checking receipt integrity…</p>
          <a class="button button-small button-secondary" href="/receipts/${encodeURIComponent(r.receipt_id)}" data-link>View Record</a>
        </div>
      </div>
    `;

    const hashEl = target.querySelector('.scramble-text');
    const finalHash = hashEl.dataset.hash;
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    let iteration = 0;
    const scrambleInterval = setInterval(() => {
      if(!alive()) { clearInterval(scrambleInterval); return; }
      hashEl.innerText = finalHash.split('').map((letter, index) => {
        if(index < iteration) return finalHash[index];
        return chars[Math.floor(Math.random() * chars.length)];
      }).join('');
      if(iteration >= finalHash.length) clearInterval(scrambleInterval);
      iteration += 1;
    }, 20);

    const status=root.querySelector("#latest-check");
    try{const result=await api("/api/verify/"+encodeURIComponent(r.receipt_id));if(!alive())return;
      status.innerHTML=result.ok?`<span class="radar-dot active"></span> Receipt content matches its hash. No funds moved.`:`<span class="radar-dot error"></span> Integrity warning: receipt content does not match its hash.`;
      status.className=result.ok?"ledger-status match-text":"ledger-status field-error";
      if(!result.ok)status.setAttribute("role","alert");
    } catch{if(alive())status.innerHTML='Verification unavailable. <a href="/verify?value='+encodeURIComponent(r.receipt_id)+'" data-link>Try verification again</a>';}
   }catch(error){if(alive()){target.innerHTML=errorState("Receipt proof unavailable",error.message,"retry-proof");root.querySelector("#retry-proof").onclick=latest;}}
  }
  await Promise.all([book(),latest()]);
 }
};
export const howPage={
 title:"How it works",
 render:()=>`<div class="shell narrative-page">${heading("How Allot works","A payout preparation, explained from the sender's point of view.",link("/app","Open payout book",true))}
 <nav class="help-index" aria-label="On this page"><a href="#describe">Describe</a><a href="#review">Review</a><a href="#prepare">Prepare</a><a href="#verify">Verify</a></nav>
 <section class="story-block" id="describe"><div><h2>Describe the allocation</h2><p>Start with the fixed $400 monthly book. The three recipients and their relative shares are already defined. Tell Allot how much is for spending and how much to exclude.</p></div><div class="example-box"><strong>Try this</strong><code>${esc(DEFAULT_BOOK_TEXT)}</code><p>Weekly or daily schedules and recognized trading instructions are rejected. Missing values use clearly explained defaults. Unclear percentages need correction.</p></div></section>
 <section class="story-block" id="review"><div><h2>Check what Allot understood</h2><p>Review the original sentence alongside the accepted budget, split, and recipient amounts. If you entered a different budget, the fixed $400 amount is clearly shown before preparation.</p></div><div><h3>For the default allocation</h3><p>$320 goes into recipient requirements: $128 for Amara, $112 for Kwame, and $80 for Elena. The other $80 is excluded.</p><p>Held is bookkeeping language. No funds are deposited or locked.</p></div></section>
 <section class="story-block" id="prepare"><div><h2>Prepare, without sending</h2><p>Allot fetches a Binance USDCUSDT quote. The USD budget is treated as USDC-equivalent for this demo. It creates three x402 payment requirements and a stored receipt.</p></div><div><h3>What the rail tells you</h3><p>Price source and conversion amounts appear on the receipt. A quote failure blocks preparation. Optional Bazaar discovery failure becomes a warning.</p><p>The payload may reference BSC mainnet. This is an unsigned envelope, not a testnet or mainnet transfer. No wallet is connected.</p><p>Settlement fees and local-currency cash-out are not estimated.</p></div></section>
 <section class="story-block" id="verify"><div><h2>Keep and check the receipt</h2><p>Open a receipt from activity, download its JSON, copy its link, or print it. Verification recomputes a SHA-256 hash of the stored receipt content.</p></div><div><h3>Match does not mean paid</h3><p>The hash checks content consistency. It is not a digital signature and does not prove sender identity, authenticity, or blockchain settlement.</p><p>Hosted storage is temporary. A downloaded file remains readable after an instance reset; online lookup may no longer work.</p></div></section>
 <section class="content-section"><h2>Common problems</h2><div class="faq-list"><details><summary>My instruction was corrected</summary><p>The budget, recipients, and frequency are fixed. Review each warning. Edit the sentence if the accepted instruction is not what you intend. Unclear percentages cannot proceed.</p></details><details><summary>Pricing failed</summary><p>Try preparing again later. A successful quote is required before payment requirements can be created.</p></details><details><summary>The request timed out</summary><p>Check activity first. A server may have saved a receipt even when the browser missed its response. Retrying the same attempt uses the same request identifier while this page session remains open.</p></details><details><summary>A receipt is missing</summary><p>Check the ID and current demo instance. Storage may have reset. Use your downloaded copy for a readable record.</p></details></div></section>
 <section class="final-cta"><h2>Review your first allocation.</h2>${link("/app","Open payout book",true)}</section></div>`
};
export const writeupPage={
 title:"Build notes",
 render:()=>`<div class="shell narrative-page">${heading("Build notes","Implementation details for teammates, reviewers, and hackathon judges.",external(GITHUB,"View repository"))}<div class="prose">
 <section><h2>A payments use case for non-traders</h2><p>Allot explores agent-assisted payout preparation. One plain-English instruction becomes a fixed three-recipient allocation, unsigned x402 requirements, and a verifiable receipt.</p></section>
 <section><h2>Working product surfaces</h2><p>The book overview provides context, the guided workspace handles describe and review, activity stores preparation history, and receipt pages combine outcomes with expandable technical evidence.</p><p>Draft text stays in session storage when available. Receipts are server-side JSON, shared by this demo instance. There are no user accounts or database.</p></section>
 <section><h2>Parser and agent interface</h2><p>A deterministic parser recognizes supported money, monthly cadence, and labelled spend/held percentages. It is not a general-purpose language model. Invalid or ambiguous splits are rejected. Server-side decimal arithmetic produces the review allocation and execution amounts.</p><p>The website uses HTTP APIs. MCP tools call the same parser, execution, lookup, and verification functions.</p></section>
 <section><h2>Rail integration</h2><p>The rail fetches a Binance USDCUSDT quote, using spot testnet with a public mainnet ticker fallback. It builds x402 v2 exact-scheme requirements for BSC USDT and records optional Bazaar discovery evidence.</p><p>GET payout endpoints return HTTP 402 and PAYMENT-REQUIRED. Requests with PAYMENT-SIGNATURE are rejected. There is no signing, broadcasting, settlement, or automatic monthly scheduler.</p></section>
 <section><h2>API reference</h2><dl class="api-reference"><dt>GET /api/book</dt><dd>Fixed payout configuration</dd><dt>POST /api/parse</dt><dd>Instruction, validation, warnings, and decimal-calculated allocation</dd><dt>POST /api/execute</dt><dd>Prepare unsigned requirements and store a receipt</dd><dt>GET /api/receipts</dt><dd>Shared demo history</dd><dt>GET /api/receipts/{id-or-hash}</dt><dd>Canonical stored receipt</dd><dt>GET /api/verify/{id-or-hash}</dt><dd>Claimed and recomputed hashes</dd><dt>GET /api/health</dt><dd>Current quote and optional discovery availability</dd><dt>GET /healthz</dt><dd>Lightweight service health</dd><dt>GET /payout/{receipt_id}/{recipient_id}</dt><dd>HTTP 402 payment requirement</dd></dl></section>
 <section><h2>Teammate integration contract</h2><p>The interface consumes receipt_id, issued_at, status, instruction, quote, legs, totals, evidence, bazaar, receipt_hash, and what_remains. A failed quote returns ok: false and retryable: true. Discovery failure is non-blocking.</p><p>Rail outputs are shown as returned. The website does not invent transaction hashes, fees, wallet approvals, or settlement status.</p></section>
 <section><h2>Verification boundaries</h2><p>SHA-256 is computed from canonical receipt JSON excluding receipt_hash. Matching content and hash demonstrates consistency only. Anyone able to change both can recompute a hash; this is not signed authentication.</p></section>
 <section><h2>Run and test locally</h2><pre>python -m allot serve</pre><p>No npm installation or frontend build is required.</p><pre>python -m unittest discover -s tests -v</pre><p>Regression tests cover parsing, exact allocations, receipt hashing, public routes, and HTTP payment boundaries. See the repository for executable tests and the latest results.</p></section>
 </div></div>`
};

