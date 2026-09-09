import { copyText } from "/lib.js";
import { header, footer, errorState } from "/ui.js";
import { landingPage, howPage, writeupPage } from "/public.js";
import { bookPage, preparePage, activityPage, receiptPage, verifyPage } from "/product.js";
const root = document.getElementById("main-content");
let revision = 0;

function enhanceInfrastructureStrip(){
  const hero=root.querySelector(".hero");
  if(!hero)return;
  root.querySelector(".context-note")?.remove();
  const brands=["BINANCE","AGENT OS","x402","BNB CHAIN","USDC","USDT","BAZAAR"];
  const brandRow=brands.map((brand,index)=>`<span class="infra-brand infra-brand-${index+1}">${brand}</span>`).join("");
  const strip=document.createElement("section");
  strip.className="infra-strip shell";
  strip.id="infrastructure";
  strip.setAttribute("aria-label","Infrastructure used by Allot");
  strip.innerHTML=`<p class="infra-eyebrow">BUILT ON OPEN PAYMENT INFRASTRUCTURE</p><div class="infra-window"><div class="infra-track"><div class="infra-set">${brandRow}</div><div class="infra-set" aria-hidden="true">${brandRow}</div></div></div><p class="infra-boundary">Demo preparation only. No signatures, broadcast, or settlement.</p>`;
  hero.insertAdjacentElement("afterend",strip);
}
function match(path) {
  const pages = {"/":landingPage,"/app":bookPage,"/app/prepare":preparePage,"/receipts":activityPage,"/verify":verifyPage,"/how-it-works":howPage,"/writeup":writeupPage};
  if (pages[path]) return {page:pages[path],params:{}};
  const receipt = path.match(/^\/receipts\/([^/]+)$/);
  if (receipt) return {page:receiptPage,params:{id:receipt[1]}};
  return {page:{title:"Page not found",render:()=>'<div class="shell product-page"><h1 tabindex="-1">Page not found</h1><p>This address is not part of Allot.</p><a class="button button-primary" href="/" data-link>Return home</a></div>'},params:{}};
}
export async function navigate(url,{replace=false}={}) {
  const target=new URL(url,location.origin);
  if(target.origin!==location.origin){location.assign(target.href);return;}
  const path=target.pathname.replace(/\/$/,"")||"/";
  if(!replace) history.pushState({},"",target.pathname+target.search+target.hash);
  const current=++revision, alive=()=>current===revision;
  const {page,params}=match(path);
  document.title=page.title+" | Allot";
  document.querySelector('meta[name="description"]').content=page.description||"Prepare a payout allocation and inspect its receipt. Demo only, no funds move.";
  const product=path.startsWith("/app")||path.startsWith("/receipts");
  document.getElementById("site-header").innerHTML=header(path,product);
  document.getElementById("site-footer").innerHTML=footer(product);
  root.innerHTML=page.render(params);
  if(path==="/")enhanceInfrastructureStrip();
  root.querySelector("h1")?.focus({preventScroll:true});
  window.scrollTo(0,0);
  try{await page.mount?.({root,params,navigate,alive});}
  catch(error){if(alive())root.innerHTML='<div class="shell product-page"><h1 tabindex="-1">Page unavailable</h1>'+errorState("Could not load this page",error.message,"route-retry")+'</div>';}
  if(!alive())return;
  root.querySelector("#route-retry")?.addEventListener("click",()=>navigate(location.href,{replace:true}));
  if(document.activeElement===document.body)root.querySelector("h1")?.focus({preventScroll:true});
  if(target.hash)document.getElementById(target.hash.slice(1))?.scrollIntoView();
}
document.addEventListener("click",async event=>{
  const copy=event.target.closest(".copy-value");
  if(copy){try{await copyText(copy.dataset.copy||"",copy);}catch{document.getElementById("global-live").textContent="Copy unavailable. Select the displayed value manually.";}return;}
  const link=event.target.closest("a[data-link]");
  if(!link||event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
  const url=new URL(link.href,location.origin);
  if(url.origin!==location.origin)return;
  event.preventDefault();await navigate(url.href);
});
window.addEventListener("popstate",()=>navigate(location.href,{replace:true}));
navigate(location.href,{replace:true});
