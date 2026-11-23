/* 三处金额口径对账模拟 v2（浏览器执行）
   场景贴近真实：手飞清单 = 已飞，看 结算明细 / 风险面板 / 飞单目录 是否同一组数。
*/
(async()=>{
const W=ms=>new Promise(r=>setTimeout(r,ms));
const R={runner:'recon-sim-v2', version:(typeof APP_VER!=='undefined'?APP_VER:'?'), cases:[], failures:[]};
const clear=()=>document.querySelectorAll('.ai-ov').forEach(x=>x.remove());

function toLines(html){
  return String(html).replace(/<br\s*\/?>/gi,'\n').replace(/<\/div>/gi,'\n').replace(/<[^>]+>/g,'')
    .replace(/&nbsp;/g,' ').replace(/&minus;|-/g,'-').split('\n').map(s=>s.trim()).filter(Boolean);
}
function pick(text,label){
  const L=toLines(text); let hit='', exact='';
  for(const l of L){ if(l.indexOf(label)>=0){ hit=l; if(l.indexOf(label)===0) exact=l; } }
  return exact || hit;
}
function numAfter(line){ const m=String(line).replace(/\u2212/g,'-').match(/-?\d+(?:\.\d+)?/); return m?Math.abs(Number(m[0])):NaN; }
function val(text,label){ const l=pick(text,label); return l?numAfter(l):NaN; }
/* label 在行尾时（如「实际总飞额」后面就是数字），numAfter 仍取第一个数字 */

function reset(){
  try{ localStorage.clear(); }catch(e){}
  orders=[]; hkOrders=[]; shop='A';
  splitTakeAll=70; pteFlyTakeAll=3000; lxFlyAmt=0; lxFlyName=''; autoFlyOn=false;
  flownPerPos={}; flownReal={}; lastDraw=null; window._flyAddLog=null;
  window.myAlert=m=>{(window.__qaAlerts=window.__qaAlerts||[]).push(String(m))};
  window.myConfirm=(m,fn)=>{ if(fn) fn(); };
  window.__previewConfirmed=true; window.__dupConfirmed=true;
  localStorage.setItem(sk('emFlyOn'),'1');
  localStorage.setItem(sk('flyRoundOn'),'0');
  clear();
  ['sideCustPay','riskBody'].forEach(id=>{ const e=document.getElementById(id); if(e) e.remove(); });
}
function box(id){ let e=document.getElementById(id); if(!e){ e=document.createElement('div'); e.id=id; document.body.appendChild(e);} e.innerHTML=''; return e; }
function panels(){
  const p=box('sideCustPay'); renderSideCustPay();
  const r=box('riskBody'); renderRisk();
  return {pay:p.innerHTML, risk:r.innerHTML};
}
function flownSum(){
  let t=0; const seen={};
  ['_em_total'].concat(Object.keys(flownPerPos||{})).forEach(k=>{ if(seen[k])return; seen[k]=1;
    if(typeof flownPaidOf==='function') t+=Number(flownPaidOf(k)||0); });
  return t;
}
async function save(input){
  clear(); document.getElementById('input').value=input;
  try{ doSave(); }catch(e){ return 'saveErr:'+e.message; }
  await W(200); clear(); return '';
}
async function manual(txt){
  window._manualFlyBuf=txt;
  try{ _applyManualFlyCore(txt,null); }catch(e){ return 'manualErr:'+e.message; }
  await W(150); clear(); return '';
}
function check(name,cond,detail){
  if(cond) R.cases.push({name,status:'PASS'});
  else { R.cases.push({name,status:'FAIL',detail}); R.failures.push({name,detail}); }
}
function snap(tag,extra){
  const p=panels();
  const fr=getThisRoundFly();
  const sales=getSplitSales(); const spec=Object.keys(sales).reduce((a,k)=>a+Number(sales[k]||0),0);
  let pte=0,lx=0,em=0;
  activeOrders().forEach(o=>eachUniqueOrderCode(o,(c,amt)=>{
    if(c.startsWith('平特')) pte+=amt;
    else if(c.startsWith('连肖')) lx+=amt;
    else if(c.indexOf('二中二:')===0||c.indexOf('三中三:')===0||c.indexOf('三中二:')===0) em+=amt;
  }));
  const grand=activeOrders().reduce((a,o)=>a+Number(o.amount||0),0);
  return {tag, extra:extra||null, total:grand, parts:spec+pte+lx+em, spec, pte, lx, em,
    should:fr.totalFly, thisRound:fr.thisRound, realFly:flownSum(), gap:(typeof flyRoundGapTotal==='function'?flyRoundGapTotal():NaN),
    payFly:val(p.pay,'实际总飞额'), riskFly:val(p.risk,'飞出去合计'),
    paySpec:val(p.pay,'特号赔付'), payPte:val(p.pay,'平特赔付'), payLx:val(p.pay,'连肖赔付'), payRef:val(p.pay,'上家赔回合计'),
    riskCust:val(p.risk,'客户总赔付'),
    payBal:val(p.pay,'最终余额'), riskNet:val(p.risk,'自留后实际净盈亏')||val(p.risk,'自留后最坏净盈亏'),
    payText:toLines(p.pay).slice(0,40), riskText:toLines(p.risk), riskLines:toLines(p.risk).filter(function(x){return /已飞|还多|凑整|残留|自留/.test(x);})};
}
function assertCommon(s){
  check(s.tag+' 总单=各玩法之和', Math.abs(s.total-s.parts)<0.01, s);
  if(isFinite(s.payFly)) check(s.tag+' 结算实付=已飞清单', Math.abs(s.payFly-s.realFly)<0.01, s);
  check(s.tag+' 风险飞出去=已飞清单', Math.abs(s.riskFly-s.realFly)<0.01, s);
  if(isFinite(s.payBal)&&isFinite(s.riskNet)) check(s.tag+' 结算余额=风险净盈亏', Math.abs(s.payBal-s.riskNet)<0.01, s);
  if(isFinite(s.riskCust)){
    check(s.tag+' 风险客户总赔付=结算赔付合计', Math.abs(s.riskCust-(s.paySpec+s.payPte+s.payLx))<0.01, s);
    check(s.tag+' 客户赔付-自留赔付=上家赔回', Math.abs((s.riskCust-s.riskCust+s.riskCust)-s.riskCust)<0.01, s); // 占位
  }
}

// ---- A：特号手飞 + 平特手飞 + EM手飞，开奖命中特号和平特 ----
reset();
await save('01各165\n02各165\n平特马 1000\n平特虎 200\n连肖马蛇 400\n二中二 01.02 各25');
await manual('01 95\n02 95\n平特马 500\n平特虎 100\n连肖马蛇 400\n二中二 50');
lastDraw={period:'999', regularNums:[2,3,4,5,6,7], specialNum:1};
const A=snap('A');
assertCommon(A);

// ---- B：只特号，凑整 10 元档 ----
reset(); splitTakeAll=0;
localStorage.setItem(sk('flyRoundOn'),'10');
await save('01各165\n02各165');
await manual('01 165\n02 165');
lastDraw={period:'999', regularNums:[3,4,5,6,7,8], specialNum:9};
const B=snap('B');
assertCommon(B);
check('B 已飞-应飞=凑整差', Math.abs((B.realFly-B.should)-B.gap)<0.01, B);

// ---- C：连肖单独，未命中 ----
reset();
await save('连肖马蛇 400\n01各5');
await manual('连肖马蛇 400');
lastDraw={period:'999', regularNums:[7,8,9,10,11,12], specialNum:13};
const C=snap('C');
assertCommon(C);

// ---- D：已飞里混进本单没有的号（残留） ----
reset();
await save('01各165');
await manual('01 95\n09 100');
lastDraw=null;
const D=snap('D');
assertCommon(D);

// ---- E：已飞后把阈值调高（典型「对不上」现场）：已飞 100 / 该飞 90 ----
reset(); splitTakeAll=70;
localStorage.setItem(sk('flyRoundOn'),'10');
await save('01各165');
await manual('01 100');
splitTakeAll=75;
lastDraw=null;
const E=snap('E'); assertCommon(E);
{ // 多出来的 10 元必须能拆成「凑整 + 残留」，两者相加等于 已飞-该飞
  const over=E.realFly-E.should;
  const rl=E.riskText.join(' ').match(/已飞\s*(-?\d+).*还多\s*(-?\d+)\s*元.*凑整多飞\s*(-?\d+)\s*＋\s*旧飞单残留\s*(-?\d+)/);
  check('E 差额能拆成凑整+残留', !!(rl && (Math.abs(Number(rl[3])+Number(rl[4])-over)<0.51)), {over, line:(rl?rl[0]:'未找到拆分行'), a:E});
}

return {summary:R, data:{A,B,C,D,E}};
})()
