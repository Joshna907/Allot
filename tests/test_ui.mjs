import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const file = name => readFile(new URL("../web/"+name,import.meta.url),"utf8");
const moduleURL = source => "data:text/javascript;base64,"+Buffer.from(source).toString("base64");
const libURL=moduleURL(await file("lib.js"));
const lib=await import(libURL);
const ui=await import(moduleURL((await file("ui.js")).replace('"/lib.js"',JSON.stringify(libURL))));
test("browser module imports reference existing local files",async()=>{
 for(const name of ["app.js","public.js","product.js","ui.js","lib.js"]){
  const source=await file(name);
  for(const match of source.matchAll(/from\s+["']\/([^"'?]+)(?:\?[^"']*)?["']/g)){
   await assert.doesNotReject(()=>file(match[1]),`${name} imports missing /${match[1]}`);
  }
 }
});
test("blocked session storage still has a usable draft",()=>assert.match(lib.appState.instructionText,/400/));
test("monetary display remains cent-exact",()=>assert.equal(lib.usd("128.03"),"$128.03"));
test("public navigation keeps build notes out of the navbar",()=>{
 assert.doesNotMatch(ui.header("/",false),/Build notes/);
 assert.match(ui.footer(false),/Build notes/);
});
test("product navigation is task focused",()=>{
 const header=ui.header("/app/prepare",true);
 assert.match(header,/Payout book/);assert.match(header,/Activity/);assert.match(header,/aria-current="page"/);
 assert.doesNotMatch(header,/Build notes/);
});
test("verification unavailable is not an endless loading state",()=>{
 const html=ui.verification(null);assert.match(html,/Could not verify/);assert.doesNotMatch(html,/aria-busy/);
});
test("mismatch is distinct from service failure",()=>{
 const html=ui.verification({ok:false,claimed:"a",recomputed:"b"});
 assert.match(html,/role="alert"/);assert.match(html,/Receipt changed/);assert.doesNotMatch(html,/Could not verify/);
});
test("verification never establishes settlement",()=>{
 assert.match(ui.verification({ok:true,claimed:"a",recomputed:"a"}),/not sender identity or blockchain settlement/);
});
test("receipt labels do not report payment",()=>{
 assert.equal(lib.humanStatus("payment-required"),"Requirement prepared");
 assert.equal(lib.humanStatus("held"),"Excluded from preparation");
});
test("script destinations are not clickable",()=>{
 assert.doesNotMatch(ui.external("javascript:alert(1)","Endpoint"),/<a/);
});
test("user content is escaped",()=>{
 assert.match(ui.errorState("<script>","<img>"),/&lt;script&gt;/);
 assert.doesNotMatch(ui.errorState("<script>","<img>"),/<script>/);
});
test("optional discovery failure is a warning with all endpoints retained",()=>{
 const html=ui.rails({legs:[{role:"spend",name:"Amara",usd:"128.00",x402:{payment_required:{x402Version:2}},payout_url:"http://localhost/payout/test/amara"}],evidence:{binance_price:true,bazaar_discovery:false}});
 assert.match(html,/Discovery unavailable/);assert.match(html,/1 payment requirements recorded/);assert.match(html,/Open HTTP 402 endpoint/);
});
test("server-calculated allocations are displayed directly",()=>{
 const html=ui.allocations([{role:"spend",name:"Amara",city:"Lagos",usd:"128.03",note:"Rent"}]);
 assert.match(html,/128\.03/);
});

