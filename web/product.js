import {api,postJson,appState,setDraft,DEFAULT_BOOK_TEXT,esc,attr,usd,percent,formatUtc,downloadJson} from "/lib.js";
import {heading,link,skeleton,errorState,empty,notice,warningList,totals,allocations,roster,receiptRow,verification,rails} from "/ui.js";
let preparation = null;
let requestKey = null;
const shell = body => `<div class="shell product-page">${body}</div>`;
const stageUrl = step => "/app/prepare?step="+step;
function progress(step){
 const names=["Describe","Review","Prepare","Receipt"], index=names.indexOf(step);
 return `<ol class="progress-list" aria-label="Payout progress">${names.map((name,i)=>`<li class="${i===index?"current":i<index?"complete":"future"}" ${i===index?'aria-current="step"':""}>${step!=="Receipt"&&i<index&&i<2?link(stageUrl(name.toLowerCase()),name):esc(name)}</li>`).join("")}</ol>`;
}
function focusStage(root){root.querySelector("[data-stage-heading]")?.focus({preventScroll:true});}
function updateStep(step){history.replaceState({},"",stageUrl(step));}
function receiptLink(r){return "/receipts/"+encodeURIComponent(r.receipt_id);}

export const bookPage={
 title:"Payout book",
 render:()=>shell(heading("Monthly payout book","One budget, three people, and a record of every preparation.")+'<div id="book-content">'+skeleton("Loading payout book")+'</div>'),
 async mount({root,navigate,alive}){
  const slot=root.querySelector("#book-content");
  const [book,allocation]=await Promise.all([api("/api/book"),postJson("/api/parse",{text:DEFAULT_BOOK_TEXT})]);
  if(!alive())return;
  slot.innerHTML=`<div class="book-intro"><div><span class="status-label">Fixed demo book</span><h2>A clear allocation for every person.</h2><p>Review the fixed budget below, then describe this preparation in your own words.</p></div><div>${link("/app/prepare",appState.parsedInstruction?"Continue review":"Prepare payout",true)}</div></div>${totals(allocation.totals)}${notice("Monthly allocation. Each preparation is started manually. Automatic payments are not enabled.")}<section class="receipt-section"><h2>Who is in this book</h2><p>These three recipients and their shares are fixed. Amounts below use the default 80% spend allocation.</p>${allocations(allocation.allocation)}</section><div class="book-support"><section><h2>Your current draft</h2><p class="draft-text">${esc(appState.instructionText)}</p>${link("/app/prepare","Continue draft")}<p class="helper">The sentence is saved in this browser tab when storage is available. Receipts are shared across this demo.</p></section><section><h2>Payment rail</h2><p>Binance pricing and x402 requirements. No wallet connection or signing is needed.</p><button class="button button-secondary" id="check-rail">Check rail availability</button><div id="rail-status" aria-live="polite"></div></section></div><section class="receipt-section"><div class="section-toolbar"><h2>Recent preparations</h2><a href="/receipts" data-link>View all activity</a></div><div id="recent">${skeleton("Loading recent activity")}</div></section>`;
  root.querySelector("#check-rail").addEventListener("click",async event=>{
   const button=event.currentTarget, status=root.querySelector("#rail-status");
   button.disabled=true;status.innerHTML=skeleton("Checking pricing and discovery");
   try{const health=await api("/api/health");if(!alive())return;status.innerHTML=`<div class="context-note"><strong>${health.quote?.ok?"Price source reachable":"Price source unavailable"}</strong><p>${health.quote?.ok?esc(health.quote.source)+" · "+esc(health.quote.price)+" "+esc(health.quote.symbol||"USDCUSDT"):"Preparation requires a successful quote. Retry this check later."}</p><p>Bazaar discovery: ${health.bazaar?.ok?"available":"unavailable (optional)"}. Wallet signing and settlement: disabled.</p><small>Checked ${formatUtc(new Date().toISOString())}. This is not a locked execution quote.</small></div>`;}
   catch(error){if(alive())status.innerHTML=errorState("Availability check failed",error.message);}
   finally{button.disabled=false;}
  });
  const recent=root.querySelector("#recent");
  async function loadRecent(){recent.innerHTML=skeleton("Loading activity");try{const rows=await api("/api/receipts");if(alive())recent.innerHTML=rows.length?rows.slice(0,3).map(receiptRow).join(""):empty("No preparations yet","Prepare the first payout to create a receipt.");}catch(error){if(alive()){recent.innerHTML=errorState("Activity unavailable",error.message,"retry-recent");root.querySelector("#retry-recent").onclick=loadRecent;}}}
  await loadRecent();
 }
};

export const preparePage={
 title:"Prepare payout",
 render:()=>shell('<a class="back-link" href="/app" data-link>Back to payout book</a>'+heading("Prepare a payout","Describe the allocation, check the interpretation, then create its receipt.")+'<div id="workspace">'+skeleton("Loading workspace")+'</div>'),
 async mount(context){
  const {root,navigate,alive}=context, workspace=root.querySelector("#workspace");
  const book=await api("/api/book");if(!alive())return;
  const showDescribe=(error="")=>{
   if(!alive())return;
   updateStep("describe");
   workspace.innerHTML=`${progress("Describe")}<div class="workspace-grid"><section class="workspace-main"><h2 data-stage-heading tabindex="-1">Describe the payout</h2><form id="describe-form" novalidate><label for="payout-text">Your instruction</label><p class="helper" id="payout-help">$400 budget, three fixed recipients, monthly allocation. Label both spend and held percentages.</p><textarea id="payout-text" name="instruction" maxlength="2000" rows="5" aria-describedby="payout-help payout-error" ${error?'aria-invalid="true"':""}>${esc(appState.instructionText)}</textarea><p class="field-error" id="payout-error" role="alert">${esc(error)}</p><div class="examples"><span>Use an example</span><button type="button" data-example="${attr(DEFAULT_BOOK_TEXT)}">80% spend, 20% held</button><button type="button" data-example="prepare 400 dollars monthly for three people, 20% held and 80% to spend">Held amount first</button></div><button class="button button-primary" type="submit">Review payout</button><p class="helper">No funds move. This demo does not schedule automatic payments.</p></form></section><aside class="workspace-aside"><h2>Fixed recipients</h2>${roster(book)}<p class="helper">Held means excluded from preparation, not stored in an Allot wallet.</p></aside></div>`;
   const form=root.querySelector("#describe-form"),text=root.querySelector("#payout-text");
   text.oninput=()=>{setDraft(text.value);requestKey=null;};
   root.querySelectorAll("[data-example]").forEach(button=>button.onclick=()=>{text.value=button.dataset.example;setDraft(text.value);requestKey=null;text.focus();});
   form.onsubmit=async event=>{
    event.preventDefault();const sentence=text.value.trim();
    if(!sentence){showDescribe("Enter a payout instruction before continuing.");root.querySelector("#payout-text").focus();return;}
    setDraft(sentence);requestKey=null;
    form.setAttribute("aria-busy","true");form.querySelectorAll("button,textarea").forEach(el=>el.disabled=true);
    root.querySelector("#payout-error").textContent="Reviewing your instruction…";
    try{
     const parsed=await postJson("/api/parse",{text:sentence});
     if(!alive())return;
     if(!parsed.valid){showDescribe(parsed.errors.join(" "));root.querySelector("#payout-text").focus();return;}
     appState.parsedInstruction=parsed;showReview();focusStage(root);
    }catch(error){if(alive()){showDescribe(error.message);root.querySelector("#payout-text").focus();}}
   };
  };
  const showReview=()=>{
   if(!alive())return;
   const instruction=appState.parsedInstruction;
   if(!instruction?.valid){showDescribe();return;}
   updateStep("review");
   workspace.innerHTML=`${progress("Review")}<section><h2 data-stage-heading tabindex="-1">Check the allocation</h2><div class="review-source"><h3>You asked</h3><blockquote>${esc(instruction.source_text)}</blockquote></div>${warningList(instruction.warnings)}<h3>Allot will use</h3>${totals(instruction.totals)}${allocations(instruction.allocation)}<div class="review-facts"><p><strong>Frequency</strong><br>Monthly allocation, prepared manually.</p><p><strong>Conversion</strong><br>A fresh Binance ${esc(instruction.pair)} quote is fetched when you prepare.</p><p><strong>Fees</strong><br>Settlement fees are not estimated. No funds are charged by this demo.</p></div><details><summary>How are the amounts calculated?</summary><p>${percent(instruction.spend_bps)} of the $400 budget is allocated to recipients. Their fixed shares are 40%, 35%, and 25%. ${percent(instruction.hold_bps)} is excluded. USD is treated as a USDC-equivalent budget for this demo, then converted using USDCUSDT. This is not a local-currency or guaranteed cash-out quote.</p></details></section><div class="review-actions"><button class="button button-secondary" id="edit-instruction">Edit instruction</button><div><p>This creates unsigned requirements and a receipt. It does not send funds.</p><button class="button button-primary" id="prepare-requirements">Prepare requirements</button></div></div>`;
   root.querySelector("#edit-instruction").onclick=()=>{showDescribe();focusStage(root);};
   root.querySelector("#prepare-requirements").onclick=()=>runPreparation(instruction);
  };
  const runPreparation=async instruction=>{
   if(!alive())return;
   updateStep("prepare");
   workspace.innerHTML=`${progress("Prepare")}<section class="preparing-state" aria-busy="true"><h2 data-stage-heading tabindex="-1">Preparing payment requirements</h2><p>Fetching the quote, building recipient requirements, and saving a receipt. No funds move.</p>${skeleton("Preparing payment requirements")}<p>You may browse the book while this finishes. Return here to see the result.</p></section>`;focusStage(root);
   if(!preparation){
    requestKey ||= crypto.randomUUID();
    preparation=postJson("/api/execute",{text:instruction.source_text,request_id:requestKey});
   }
   const pending=preparation;
   try{
    const receipt=await pending;
    if(!receipt?.receipt_id||!Array.isArray(receipt.legs))throw new Error("The rail returned an incomplete receipt. Check activity before retrying.");
    appState.currentReceipt=receipt;
    if(alive())await navigate(receiptLink(receipt));
   }catch(error){
    if(!alive())return;
    const quoteFailure=error.data?.quote?.ok===false;
    workspace.innerHTML=`${progress("Prepare")}${errorState(quoteFailure?"Price source unavailable":"Preparation could not be confirmed",quoteFailure?"Binance pricing did not respond successfully. No requirements were prepared. You can retry with the same instruction.":error.message)}<div class="inline-actions"><button class="button button-primary" id="retry-prepare">Try again</button><button class="button button-secondary" id="review-after-error">Return to review</button>${link("/receipts","Check activity")}</div><details><summary>Technical error details</summary><pre>${esc(error.data?JSON.stringify(error.data,null,2):error.message)}</pre></details>`;
    root.querySelector("#retry-prepare").onclick=()=>runPreparation(instruction);
    root.querySelector("#review-after-error").onclick=showReview;
   }finally{if(preparation===pending)preparation=null;}
  };
  let requested=new URLSearchParams(location.search).get("step");
  if(preparation&&appState.parsedInstruction){await runPreparation(appState.parsedInstruction);return;}
  if(!appState.parsedInstruction&&requested==="review"){
   const parsed=await postJson("/api/parse",{text:appState.instructionText});
   if(!alive())return;
   if(parsed.valid)appState.parsedInstruction=parsed;
  }
  if(requested!=="describe"&&appState.parsedInstruction)showReview();else showDescribe();
 }
};

export const activityPage={
 title:"Payout activity",
 render:()=>shell(heading("Payout activity","Preparations stored on this shared demo instance.",link("/app/prepare","Prepare payout",true))+notice("No private account history. Download important receipts: hosted storage may reset.")+'<div class="section-toolbar"><div class="field search-control"><label for="receipt-search">Search by receipt ID or hash</label><input type="search" id="receipt-search" name="search" autocomplete="off" spellcheck="false"></div><button class="button button-secondary" id="refresh-activity">Refresh</button></div><div id="activity-output">'+skeleton("Loading activity")+'</div>'),
 async mount({root,alive}){
  const output=root.querySelector("#activity-output"),input=root.querySelector("#receipt-search"),button=root.querySelector("#refresh-activity");
  let rows=[];
  input.value=new URLSearchParams(location.search).get("q")||"";
  function render(){
   const needle=input.value.trim().toLowerCase(),filtered=rows.filter(r=>(r.receipt_id+" "+r.receipt_hash).toLowerCase().includes(needle));
   output.innerHTML=!rows.length?empty("No preparations yet","Your first preparation creates a receipt here."):!filtered.length?`<div class="state-panel"><h2>No matching receipt</h2><p>Try another ID or hash.</p><button class="button button-secondary" id="clear-search">Clear search</button></div>`:`<p role="status">${filtered.length} matching receipt${filtered.length===1?"":"s"}</p>${filtered.map(receiptRow).join("")}`;
   root.querySelector("#clear-search")?.addEventListener("click",()=>{input.value="";search();input.focus();});
  }
  function search(){history.replaceState({},"","/receipts"+(input.value?"?q="+encodeURIComponent(input.value):""));render();}
  async function load(){
   button.disabled=true;output.innerHTML=skeleton("Loading activity");
   try{rows=await api("/api/receipts");rows.sort((a,b)=>String(b.issued_at).localeCompare(String(a.issued_at)));if(alive())render();}
   catch(error){if(alive()){output.innerHTML=errorState("Activity unavailable",error.message,"retry-activity");root.querySelector("#retry-activity").onclick=load;}}
   finally{button.disabled=false;}
  }
  input.oninput=search;button.onclick=load;await load();
 }
};
function receiptMarkup(r,fallback){
 const count=r.legs.filter(l=>l.role==="spend").length;
 return shell(`<a class="back-link" href="/receipts" data-link>Back to activity</a>${progress("Receipt")}<div class="receipt-outcome"><div><h1 tabindex="-1">Payout requirements prepared</h1><p class="outcome-copy">${usd(r.totals.spend_usd)} allocated across ${count} recipients. ${usd(r.totals.hold_usd)} excluded from preparation.</p><p>${formatUtc(r.issued_at)}<br><code>${esc(r.receipt_id)}</code></p></div><span class="demo-badge">Demo, not settled</span></div>${notice("No funds moved. Allot does not hold the excluded amount or start automatic monthly payments.")}${fallback?'<aside class="warning-panel"><strong>Showing the newly created copy</strong><p>The stored copy is unavailable. Download this receipt now; retry the stored copy before sharing.</p><button class="button button-secondary" id="retry-stored">Retry stored copy</button></aside>':""}<div class="receipt-actions"><button class="button button-primary" id="download-receipt">Download receipt JSON</button><button class="button button-secondary copy-value" data-copy="${attr(new URL(receiptLink(r),location.origin).href)}">Copy receipt link</button><button class="button button-secondary" id="print-receipt">Print</button>${link("/app/prepare?step=describe","Prepare another payout")}</div><section class="receipt-section"><h2>Allocation</h2>${totals(r.totals,true)}${allocations(r.legs,true)}<p class="helper">USDT equivalents use ${esc(r.quote?.symbol||r.instruction?.pair)} at ${esc(r.quote?.price)} from ${esc(r.quote?.source)}. USD is treated as USDC-equivalent in this demo. Settlement fees are not estimated.</p></section><section class="receipt-section"><div class="section-toolbar"><h2>Receipt integrity</h2><button class="button button-secondary" id="recheck">Check again</button></div><div id="receipt-verification">${skeleton("Checking receipt")}</div><details><summary>Receipt hash</summary><pre>${esc(r.receipt_hash)}</pre><button class="button button-secondary copy-value" data-copy="${attr(r.receipt_hash)}">Copy hash</button></details></section><section class="receipt-section"><h2>Original instruction</h2><blockquote>${esc(r.instruction?.source_text)}</blockquote>${warningList(r.instruction?.warnings)}</section>${rails(r)}<section class="receipt-section"><h2>What has not happened</h2><p>No user signature, transaction broadcast, or on-chain settlement. These are outside this demo, not jobs waiting to run automatically.</p><details><summary>Rail integration boundaries</summary><ul>${(r.what_remains||[]).map(item=>`<li>${esc(item)}</li>`).join("")}</ul></details></section>`);
}
export const receiptPage={
 title:"Payout receipt",
 render:()=>shell(skeleton("Loading receipt")),
 async mount({root,params,navigate,alive}){
  let value;try{value=decodeURIComponent(params.id);}catch{value=params.id;}
  let receipt,fallback=false;
  try{receipt=await api("/api/receipts/"+encodeURIComponent(value));}
  catch(error){
   if(!alive())return;
   if(appState.currentReceipt?.receipt_id===value){receipt=appState.currentReceipt;fallback=true;}
   else{
    root.innerHTML=shell(heading(error.status===404?"Receipt not found":"Receipt unavailable",error.status===404?"The ID may be incorrect or this demo's storage may have reset.":"The service could not load this receipt. This does not mean it was deleted.")+(error.status===404?`<form action="/verify" class="inline-form"><div class="field"><label for="other-receipt">Receipt ID or hash</label><input name="value" id="other-receipt" value="${attr(value)}" autocomplete="off" spellcheck="false"></div><button class="button button-primary">Check receipt</button></form>`:errorState("Please retry",error.message,"retry-receipt"))+`<div class="inline-actions">${link("/receipts","Browse activity")}${link("/app/prepare","Prepare payout",true)}</div>`);
    root.querySelector("#retry-receipt")?.addEventListener("click",()=>navigate(location.href,{replace:true}));return;
   }
  }
  if(!alive())return;
  root.innerHTML=receiptMarkup(receipt,fallback);document.title=receipt.receipt_id+" | Allot";
  root.querySelector("#download-receipt").onclick=()=>downloadJson(receipt,!fallback);
  root.querySelector("#print-receipt").onclick=()=>window.print();
  root.querySelector("#retry-stored")?.addEventListener("click",()=>navigate(location.href,{replace:true}));
  let checkRevision=0;
  async function check(){
   const current=++checkRevision,output=root.querySelector("#receipt-verification"),button=root.querySelector("#recheck");
   button.disabled=true;output.innerHTML=skeleton("Checking receipt integrity");
   try{const result=await api("/api/verify/"+encodeURIComponent(receipt.receipt_id));if(alive()&&current===checkRevision)output.innerHTML=verification(result);}
   catch{
    try{const result=await postJson("/api/verify",receipt);if(alive()&&current===checkRevision)output.innerHTML=verification(result)+'<p class="helper">The stored copy is unavailable, so the hash was recomputed from the receipt on this page.</p>';}
    catch{if(alive()&&current===checkRevision)output.innerHTML=verification(null);}
   }
   finally{button.disabled=false;}
  }
  root.querySelector("#recheck").onclick=check;await check();
 }
};
export const verifyPage={
 title:"Verify a receipt",
 render:()=>shell(heading("Verify a receipt","Check whether stored receipt content matches its printed hash.")+`<form id="verify-form" class="verify-form" novalidate><div class="field"><label for="verify-value">Receipt ID or SHA-256 hash</label><p id="verify-help" class="helper">Use the complete value from a receipt. This checks integrity, not payment settlement.</p><input id="verify-value" name="value" autocomplete="off" spellcheck="false" aria-describedby="verify-help verify-error"><p class="field-error" id="verify-error" role="alert"></p></div><button class="button button-primary">Check receipt</button></form><details class="verify-paste"><summary>Verify a receipt this instance no longer stores</summary><div class="field"><label for="verify-json">Receipt JSON</label><p id="paste-help" class="helper">Paste a downloaded receipt. The hash is recomputed from what you paste; storage is not read.</p><textarea id="verify-json" spellcheck="false" aria-describedby="paste-help paste-error"></textarea><p class="field-error" id="paste-error" role="alert"></p></div><button class="button button-secondary" id="verify-paste-run" type="button">Check pasted receipt</button></details><div id="verification-output" aria-live="polite"></div>`+notice("Lookup is limited to this demo instance. If storage resets, a downloaded JSON receipt remains readable, but its ID may no longer be found here.")+link("/receipts","Browse demo activity")),
 async mount({root,alive}){
  const input=root.querySelector("#verify-value"),form=root.querySelector("#verify-form"),output=root.querySelector("#verification-output"),error=root.querySelector("#verify-error");
  let sequence=0;
  async function check(){
   const value=input.value.trim();
   if(!/^(ALLOT-[A-Za-z0-9-]+|[a-fA-F0-9]{64})$/.test(value)){error.textContent="Enter a complete ALLOT receipt ID or a 64-character SHA-256 hash.";input.setAttribute("aria-invalid","true");input.focus();return;}
   error.textContent="";input.removeAttribute("aria-invalid");
   history.replaceState({},"","/verify?value="+encodeURIComponent(value));
   const current=++sequence;form.querySelector("button").disabled=true;output.innerHTML=skeleton("Checking receipt");
   try{
    const result=await api("/api/verify/"+encodeURIComponent(value));
    if(!alive()||current!==sequence)return;
    output.innerHTML=verification(result)+`<p>${link("/receipts/"+encodeURIComponent(result.receipt_id),"View full receipt")}</p><div id="verify-context"></div>`;
    const metadata=root.querySelector("#verify-context");
    try{const r=await api("/api/receipts/"+encodeURIComponent(value));if(alive()&&current===sequence)metadata.innerHTML=`<p>${esc(r.receipt_id)}<br>${usd(r.totals?.gross_usd)} budget · ${formatUtc(r.issued_at)}</p>`;}catch{if(alive()&&current===sequence)metadata.textContent="Supporting receipt details are unavailable. The verification result above is still valid.";}
   }catch(cause){if(alive()&&current===sequence){output.innerHTML=cause.status===404?empty("Receipt not found","Check the ID, or browse the current instance. Hosted receipts may have expired — if you downloaded the JSON, paste it above instead.","/receipts","Browse activity"):errorState("Could not verify",cause.message,"retry-verify");root.querySelector("#retry-verify")?.addEventListener("click",check);}}
   finally{if(current===sequence)form.querySelector("button").disabled=false;}
  }
  const pasteField=root.querySelector("#verify-json"),pasteError=root.querySelector("#paste-error"),pasteButton=root.querySelector("#verify-paste-run");
  pasteButton.onclick=async()=>{
   let pasted;
   try{pasted=JSON.parse(pasteField.value);}
   catch{pasteError.textContent="That is not valid JSON. Paste the whole downloaded receipt file.";pasteField.setAttribute("aria-invalid","true");pasteField.focus();return;}
   pasteError.textContent="";pasteField.removeAttribute("aria-invalid");
   const current=++sequence;pasteButton.disabled=true;output.innerHTML=skeleton("Checking pasted receipt");
   try{const result=await postJson("/api/verify",pasted);if(alive()&&current===sequence)output.innerHTML=verification(result)+'<p class="helper">Recomputed from the JSON you pasted. Storage was not used.</p>';}
   catch(cause){if(alive()&&current===sequence){pasteError.textContent=cause.message;output.innerHTML="";}}
   finally{if(current===sequence)pasteButton.disabled=false;}
  };
  form.onsubmit=event=>{event.preventDefault();check();};
  input.oninput=()=>{sequence++;form.querySelector("button").disabled=false;output.innerHTML="";};
  input.value=new URLSearchParams(location.search).get("value")||"";
  if(input.value)await check();
 }
};
