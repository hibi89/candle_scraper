/** Offline CSV regression. Run with: node test_report_viewer.mjs */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const html=fs.readFileSync(new URL('./CandlePatternResultsViewer.html',import.meta.url),'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script);
new vm.Script(script);
assert.doesNotMatch(html,/<script\s+src=|<link\s+[^>]*href=/i);
const start=script.indexOf(' async function readCsv');
const end=script.indexOf('\n function option(',start);
assert.ok(start>0&&end>start);
const parse=vm.runInNewContext(script.slice(start,end)+'\nreadCsv',{TextDecoder,needed:['market','unit','kst','utc','close']});
function file(text,n=1){const data=Buffer.from(text,'utf8');let i=0;return{size:data.length,stream:()=>({getReader:()=>({read:async()=>{if(i===data.length)return{done:true};const value=data.subarray(i,Math.min(i+n,data.length));i+=value.length;return{done:false,value};}})})};}
const h='exchange,market,unit,utc,kst,close,sma280,sma560,ema280,ema560,bb_upper,sma_spread_previous,sma_spread_current';
const a='upbit,KRW-BTC,240,2026-11-06T00:00:00Z,2026-11-06 09:00:00,1,1,1,1,1,1,-1,1';
const b='"up,bit",KRW-ETH,60,2026-11-05T00:00:00Z,2026-11-05 09:00:00,2,2,2,2,2,2,-2,1';
let passed=0;
for(const n of [1,2,3,16,1024]){const r=await parse(file('\ufeff'+h+'\r\n'+a+'\r\n'+b+'\r\n',n));assert.equal(r.rows.length,2);assert.equal(r.rows[1].exchange,'up,bit');assert.equal(r.rows[0].market,'KRW-BTC');passed++;}
assert.equal((await parse(file(h+'\r\n'))).rows.length,0);passed++;
await assert.rejects(()=>parse(file(h+'\r\n'+a+',extra\r\n')),/열 개수/);passed++;
await assert.rejects(()=>parse(file(h+'\r\n"broken')),/따옴표/);passed++;
await assert.rejects(()=>parse(file('x,y\n')),/열/);passed++;
console.log('Offline viewer static/CSV tests: '+passed+' PASS, 0 FAIL');
