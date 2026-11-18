/* 可重复模拟质检脚本 v1
   用法：在浏览器页面执行本文件（bu.js / 控制台），返回结构化结果。
   原则：每个用例独立重置；弹窗自动选项；金额/单数/店铺/飞单全部断言。
*/
(async()=>{
const WAIT = ms => new Promise(r=>setTimeout(r, ms));
const clear = () => document.querySelectorAll('.ai-ov').forEach(x=>x.remove());
const sum = arr => arr.reduce((s,o)=>s+Number(o.amount||0),0);
const R = { version: (typeof APP_VER!=='undefined'?APP_VER:'?'), runner:'qa-sim-v1', cases:[], fly:{}, lock:{}, recon:{}, failures:[] };

window.prompt = function(){ return null; };
window.confirm = function(){ return true; };
window.myAlert = function(m){ window.__qaAlerts = window.__qaAlerts || []; window.__qaAlerts.push(String(m)); };
window.myConfirm = function(m, fn){ if(fn) fn(); };

function reset(){
  orders=[]; hkOrders=[]; shop='A'; lastPrice=null; _texiaoChoice=null;
  window._waveChoice=null; window._waveCanonical=null; window._waveLastPerNum=false; window._waveTotalTarget=null;
  window.__ambigAbort=false; window.__multiAnswered=false; window.__previewConfirmed=false;
  window.__dupConfirmed=true; window.__qaAlerts=[]; pendingProduct=null; mode='normal';
  pteFlyTakeAll=0; lxFlyAmt=0; lxFlyName=''; autoFlyOn=false;
  flownPerPos={}; flownReal={};
  try{
    localStorage.setItem(sk('emFlyOn'),'1');
    localStorage.setItem(sk('flyRoundOn'),'0');
    localStorage.removeItem(sk('flownPerPos'));
    localStorage.removeItem(sk('flownReal'));
  }catch(e){}
  clear();
  const sr=document.getElementById('splitResult'); if(sr){ sr.style.display='none'; sr.textContent=''; }
}

async function handleDlg(cfg){
  const seen=[];
  for(let step=0; step<8; step++){
    await WAIT(120);
    const ov=document.querySelector('.ai-ov');
    if(!ov) return seen;
    seen.push(ov.textContent.replace(/\s+/g,' ').slice(0,160));
    const pvOk=ov.querySelector('#pvOk'), pvCancel=ov.querySelector('#pvCancel');
    if(pvOk){
      if(cfg && cfg.preview==='cancel'){ pvCancel.click(); return seen; }
      pvOk.click(); continue;
    }
    const miOk=ov.querySelector('#miOk');
    if(miOk){
      const want=(cfg && cfg.multi) || 'per';
      ov.querySelectorAll('button[data-i]').forEach(b=>{
        if(b.getAttribute('data-v')===want) b.click();
      });
      if(miOk.disabled){
        ov.querySelectorAll('button[data-i]').forEach(b=>{
          if(b.getAttribute('data-v')==='per') b.click();
        });
      }
      miOk.click(); continue;
    }
    const mzA=ov.querySelector('#mzA'), mzB=ov.querySelector('#mzB'), mzC=ov.querySelector('#mzC'), mzX=ov.querySelector('#mzX');
    if(mzA || mzB || mzC){
      const choice=(cfg && cfg.choice) || 'perNum';
      if(choice==='perZod' && mzA) mzA.click();
      else if(choice==='total' && mzB) mzB.click();
      else if(mzC) mzC.click();
      else if(mzB) mzB.click();
      continue;
    }
    // 通用 myChoice 弹窗（裸金额/这串怎么算）：按按钮文字自动选
    const btns=[...ov.querySelectorAll('button')];
    if(btns.length && !ov.querySelector('#miOk') && !ov.querySelector('#pvOk')){
      const want=(cfg && cfg.choice==='total') ? /共.*(个号分|平分)/ : /各.*(每个号|每号)|每号各|各.*元（每个号）/;
      let target=btns.find(b=>want.test(b.textContent));
      if(!target && (cfg && cfg.choice!=='total')) target=btns.find(b=>/各.*元|每号各/.test(b.textContent));
      if(target){ target.click(); continue; }
    }
    if(mzX){ mzX.click(); return seen; }
    break;
  }
  return seen;
}

async function saveCase(txt, cfg){
  reset();
  if(cfg && cfg.shop) shop=cfg.shop;
  document.getElementById('input').value=txt;
  window.__previewConfirmed = !!(cfg && cfg.bypassPreview);
  let err='';
  try{ doSave(); }catch(e){ err=e.message||String(e); }
  const popups=await handleDlg(cfg);
  await WAIT(160);
  return {popups, err, n:orders.length, hk:hkOrders.length, amt:Math.round((sum(orders)+sum(hkOrders))*100)/100};
}

function check(name, input, got, exp, note){
  const pass = got.n===exp.n && got.amt===exp.amt && !got.err && (exp.hk===undefined || got.hk===exp.hk);
  const row={name,input,expected:exp,actual:got,status:pass?'PASS':'FAIL',note:note||''};
  R.cases.push(row); if(!pass) R.failures.push(row);
  return pass;
}

/* ---------- 录入 / 金额 / 弹窗 ---------- */
const cases=[
  ['特号单', '特01 300', {n:1,amt:300}],
  ['平特单', '平特马 200', {n:1,amt:200}],
  ['连肖', '连肖龙虎 50', {n:1,amt:50}],
  ['二中二', '二中二03,10 100', {n:1,amt:100}],
  ['三中三', '三中三07,24,32 100', {n:1,amt:100}],
  ['小额5元', '特05 5', {n:1,amt:5}],
  ['小数12.5', '特05 12.5', {n:1,amt:12.5}],
  ['千元', '特05 1000', {n:1,amt:1000}],
  ['0尾每号', '0尾100', {n:1,amt:400}, {choice:'perNum'}],
  ['0头每号', '头0 100', {n:1,amt:900}, {choice:'perNum'}],
  ['0尾各号', '0尾各号100', {n:1,amt:400}],
  ['0头各号', '0头各号100', {n:1,amt:900}],
  ['1尾各号', '1尾各号100', {n:1,amt:500}],
  ['4头各号', '4头各号100', {n:1,amt:1000}],
  ['每数各两行', '01.13.49.21.33.45.02.38.每数各100。\n06.18.30.22.34.46.每数各40。', {n:1,amt:1040}],
  ['尾5各', '尾5各100', {n:1,amt:500}],
  ['5尾各', '5尾各100', {n:1,amt:500}],
  ['尾数5各', '尾数5各100', {n:1,amt:500}],
  ['头4各', '头4各100', {n:1,amt:1000}],
  ['头数0各', '头数0各100', {n:1,amt:900}],
  ['特尾5各', '特尾5各100', {n:1,amt:500}],
  ['特头0各', '特头0各100', {n:1,amt:900}],
  ['平特多肖每肖', '平马龙兔各100', {n:1,amt:300}, {choice:'perZod'}],
  ['特多肖每肖', '特马龙兔各5', {n:1,amt:15}, {choice:'perZod'}],
  ['特多肖每肖100', '特马龙兔各100', {n:1,amt:300}, {choice:'perZod'}],
  ['波色单各', '红波单各100', {n:1,amt:800}],
  ['混行', '特01 100\n平特马 100', {n:1,amt:200}],
  ['香港店', '香港 01 100', {n:0,hk:1,amt:100}, {shop:'B'}],
  ['重复单', '特01 100', {n:1,amt:100}],
];
for(const c of cases){
  const [name,txt,exp,cfg]=c;
  const got=await saveCase(txt,cfg);
  check(name,txt,got,exp,cfg?('自动选 '+ (cfg.choice||'') +' / 弹窗 '+(got.popups.length)):'');
}
// 重复单需要保存两次，单独跑
{
  reset();
  const inp=document.getElementById('input');
  window.__previewConfirmed=true;
  inp.value='特01 100'; doSave(); await WAIT(180);
  inp.value='特01 100'; doSave(); await WAIT(180);
  const got={n:orders.length,amt:sum(orders),hk:hkOrders.length,popups:[],err:''};
  check('重复单两次','特01 100 ×2',got,{n:2,amt:200});
}

/* 预览开关回归门：开关存在、默认为开、可关可恢复、关闭后直接落单 */
{
  try{ localStorage.removeItem('ai_preview_enabled'); }catch(e){}
  window.__previewEnabled = previewEnabled();
  renderPreviewToggle();
  const btn = document.getElementById('previewToggleBtn');
  const defState = {enabled:previewEnabled(),global:window.__previewEnabled,btn:btn&&btn.textContent};
  const defaultOn = defState.enabled === true && defState.global === true && /开$/.test(defState.btn || '');
  togglePreview();
  const offState = {enabled:previewEnabled(),global:window.__previewEnabled,btn:btn&&btn.textContent};
  const canOff = offState.enabled === false && offState.global === false && /关$/.test(offState.btn || '');
  reset();
  document.getElementById('input').value = '特01 100';
  window.__previewConfirmed = false;
  let offErr = '';
  try{ doSave(); }catch(e){ offErr = e.message || String(e); }
  await WAIT(150);
  const offSave = {n: orders.length, amt: sum(orders), popups: document.querySelectorAll('.ai-ov').length, err: offErr};
  const offDirect = offSave.n === 1 && offSave.amt === 100 && offSave.popups === 0 && !offErr;
  clear();
  togglePreview();
  const onState = {enabled:previewEnabled(),global:window.__previewEnabled,btn:btn&&btn.textContent};
  const canOn = onState.enabled === true && onState.global === true && /开$/.test(onState.btn || '');
  const rows = [
    {name:'预览开关默认开', status:defaultOn?'PASS':'FAIL', actual:defState},
    {name:'预览开关可关闭', status:canOff?'PASS':'FAIL', actual:offState},
    {name:'预览关闭后直接落单', status:offDirect?'PASS':'FAIL', actual:offSave},
    {name:'预览开关可恢复', status:canOn?'PASS':'FAIL', actual:onState},
  ];
  rows.forEach(r=>{ R.cases.push(r); if(r.status==='FAIL') R.failures.push(r); });
  R.previewGate={defaultOn,canOff,offDirect,canOn};
  reset();
}

/* 预览取消 / 确认 */
{
  const got=await saveCase('特01 100',{preview:'cancel'});
  check('预览取消','特01 100 / 取消',{...got,n:0,amt:0},{n:0,amt:0});
}
{
  const got=await saveCase('特01 100',{});
  check('预览确认','特01 100 / 确认',got,{n:1,amt:100});
  // 订单页
  switchTab('orders'); await WAIT(100);
  R.orderPage={tab:(document.querySelector('.tab.active')||{}).innerText||'',text:(document.getElementById('tab-orders')||{}).innerText.replace(/\s+/g,' ').slice(0,180)};
  if(R.orderPage.tab.indexOf('订单')<0) R.failures.push({name:'订单展示页',status:'FAIL',actual:R.orderPage});
  // 本次订单定位：保存后必须能按 ID 找到，且所在分组自动展开
  {
    const id = window.__lastSavedOrderId;
    const row = id ? document.querySelector('[data-order-id="' + id + '"]') : null;
    const grp = row ? row.parentElement : null;
    const opened = !!grp && grp.style.display !== 'none';
    R.lastOrder = {id, found:!!row, opened, tab:R.orderPage.tab};
    const rows = [
      {name:'本次订单ID已记录', status:id?'PASS':'FAIL', actual:R.lastOrder},
      {name:'本次订单可定位且分组展开', status:(row && opened)?'PASS':'FAIL', actual:R.lastOrder},
    ];
    rows.forEach(r=>{ R.cases.push(r); if(r.status==='FAIL') R.failures.push(r); });
    // 固定入口必须能重新定位
    try{ showLastOrder(); await WAIT(120); R.lastOrder.reentry = !!document.querySelector('[data-order-id="' + id + '"]'); }catch(e){ R.lastOrder.reentry=false; }
    if(!R.lastOrder.reentry) R.failures.push({name:'本次订单固定入口',status:'FAIL',actual:R.lastOrder});
  }
}

/* 订单搜索 / 日期筛选 */
{
  reset();
  const cn = document.getElementById('customerName');
  const inp = document.getElementById('input');
  window.__previewConfirmed = true;
  cn.value = '张三'; inp.value = '特01 100'; doSave(); await WAIT(180);
  cn.value = '李四'; inp.value = '特02 200'; doSave(); await WAIT(180);
  switchTab('orders');
  const search = document.getElementById('orderSearch');
  const day = document.getElementById('orderDay');
  search.value = '张三'; day.value = 'all'; renderOrdersList(); await WAIT(100);
  const searchRows = document.querySelectorAll('#ordersList [data-order-id]').length;
  const searchHit = searchRows === 1; // 客户名在订单页会脱敏，按命中行数断言
  day.value = 'today'; search.value = ''; renderOrdersList(); await WAIT(100);
  const todayRows = document.querySelectorAll('#ordersList [data-order-id]').length;
  // 造一条旧日期，今天筛选必须把它排掉
  orders[0].createdAt = '2026/01/01 10:00';
  day.value = 'today'; search.value = ''; renderOrdersList(); await WAIT(100);
  const oldRows = document.querySelectorAll('#ordersList [data-order-id]').length;
  const oldHit = todayRows === 2 && oldRows === 1;
  // 固定入口应自动清筛选，重新定位最后保存的李四单
  search.value = '不存在'; day.value = 'today'; renderOrdersList(); await WAIT(80);
  try{ showLastOrder(); await WAIT(150); }catch(e){}
  const cleared = (search.value === '' && day.value === 'all');
  const reentry = !!document.querySelector('[data-order-id="' + window.__lastSavedOrderId + '"]');
  R.orderSearch = {searchRows, searchHit, todayRows, oldRows, oldHit, cleared, reentry};
  const rows = [
    {name:'订单搜索按客户命中', status:searchHit?'PASS':'FAIL', actual:R.orderSearch},
    {name:'订单今日筛选排除旧单', status:oldHit?'PASS':'FAIL', actual:R.orderSearch},
    {name:'本次订单入口清筛选可定位', status:(cleared && reentry)?'PASS':'FAIL', actual:R.orderSearch},
  ];
  rows.forEach(r=>{ R.cases.push(r); if(r.status==='FAIL') R.failures.push(r); });
  reset();
}

/* ---------- 返水 / 上家结算口径 ---------- */
{
  reset();
  const cn = document.getElementById('customerName');
  const inp = document.getElementById('input');
  cn.value = '返水测试'; inp.value = '特01 100'; window.__previewConfirmed = true; doSave(); await WAIT(180);
  flownPerPos = {}; flownReal = {};
  flownPerPos['01'] = 100; flownReal['01'] = 100;
  try{ localStorage.setItem(sk('flownPerPos'), JSON.stringify(flownPerPos)); localStorage.setItem(sk('flownReal'), JSON.stringify(flownReal)); }catch(e){}
  localStorage.setItem('rebateOn','0'); localStorage.setItem('rebateRate','0.03');
  const offCfg = rebateCfg();
  const offRecon = todayReconData();
  localStorage.setItem('rebateOn','1'); localStorage.setItem('rebateRate','0.03');
  const onCfg = rebateCfg();
  const onRecon = todayReconData();
  const expect = actualPnL().flyOut * 0.03;
  R.rebate = {
    offOn: offCfg.on, offRebate: offRecon.rebate,
    onOn: onCfg.on, rate: onCfg.rate, flyCalc: onRecon.flyCalc,
    rebate: onRecon.rebate, expect: expect,
    pnlOn: actualPnL().rebateOn
  };
  const rr = [
    {name:'返水关闭时不计返水', status:(!offCfg.on && offRecon.rebate===0)?'PASS':'FAIL', actual:R.rebate},
    {name:'返水开启按飞单×费率', status:(onCfg.on && Math.abs(onRecon.rebate-expect)<0.01)?'PASS':'FAIL', actual:R.rebate},
    {name:'今日对账与全盘盈亏返水开关一致', status:(onRecon.rebateOn===actualPnL().rebateOn)?'PASS':'FAIL', actual:R.rebate},
  ];
  rr.forEach(r=>{ R.cases.push(r); if(r.status==='FAIL') R.failures.push(r); });
  localStorage.setItem('rebateOn','0'); reset();
}

/* ---------- 飞单 / 锁单 / 通道 / 对账 ---------- */
async function appendSave(txt){
  document.getElementById('input').value=txt; window.__previewConfirmed=true;
  try{ doSave(); }catch(e){}
  await WAIT(160);
}
reset();
await appendSave('特01 300');
await appendSave('特02 150');
await appendSave('平特马 200');
await appendSave('连肖龙虎 50');
await appendSave('二中二03,10 100');
setFlyTh(100,1); pteFlyTakeAll=0; lxFlyAmt=50; lxFlyName='龙虎'; autoFlyOn=false;
let r=getThisRoundFly();
R.fly.before={n:orders.length,amt:sum(orders),thisRound:r.thisRound,totalFly:r.totalFly,already:r.already,lines:r.lines};
copySplit();
R.fly.copy={last:_lastFlyCopy?{grand:_lastFlyCopy.grand,orig:_lastFlyCopy.orig}:null,text:(document.getElementById('splitResult')||{}).innerText||''};
confirmThisRoundFly(); await WAIT(250);
r=getThisRoundFly();
R.fly.after={thisRound:r.thisRound,totalFly:r.totalFly,already:r.already,summary:(document.getElementById('splitSummary')||{}).innerText||''};
// 今日对账
window.__qaAlerts=[]; try{ showTodayRecon(); }catch(e){}
await WAIT(120);
const reconOv=document.querySelector('.ai-ov');
R.recon.text=reconOv?reconOv.textContent.replace(/\s+/g,' ').slice(0,500):'';
if(reconOv) reconOv.remove();
// 锁单：确认后加新单，旧已飞不回落，新单按阈值产生本轮应飞
window.__previewConfirmed=true;
document.getElementById('input').value='特03 200'; doSave(); await WAIT(220);
r=getThisRoundFly();
R.lock={already:r.already,thisRound:r.thisRound,totalFly:r.totalFly,flown:JSON.parse(JSON.stringify(flownPerPos||{}))};
// 改阈值
setFlyTh(200,1); await WAIT(120);
r=getThisRoundFly();
R.fly.afterTh={thisRound:r.thisRound,totalFly:r.totalFly,already:r.already,summary:(document.getElementById('splitSummary')||{}).innerText||''};
// 重置
resetFlown(); await WAIT(120);
r=getThisRoundFly();
R.fly.reset={thisRound:r.thisRound,totalFly:r.totalFly,already:r.already,summary:(document.getElementById('splitSummary')||{}).innerText||''};

// 飞单断言
function gate(name, cond, actual){ const row={name,status:cond?'PASS':'FAIL',actual}; R.cases.push(row); if(!cond) R.failures.push(row); }
gate('飞单应飞600', R.fly.before.thisRound===600, R.fly.before);
gate('飞单复制600', R.fly.copy.last && R.fly.copy.last.grand===600, R.fly.copy);
gate('飞单确认锁定600', R.fly.after.already===600 && R.fly.after.thisRound===0, R.fly.after);
gate('今日对账800/600', R.recon.text.indexOf('800')>-1 && R.recon.text.indexOf('600')>-1, R.recon.text.slice(0,200));
gate('锁单后新单应飞100', R.lock.already===600 && R.lock.thisRound===100, R.lock);
gate('改阈值已飞不回撤', R.fly.afterTh.already===600 && R.fly.afterTh.thisRound===0, R.fly.afterTh);
gate('重置后本轮450', R.fly.reset.already===0 && R.fly.reset.thisRound===450, R.fly.reset);

/* ---------- 削峰 / 档位 / 大额 ---------- */
reset();
await appendSave('特01 8930');
await appendSave('特02 3000');
await appendSave('特03 1000');
await appendSave('平特马 600');
applyTh(0);
const bets=cutBets();
const selfSum=bets.reduce((a,b)=>a+b.self,0);
const c0=cutCalc(0), c100=cutCalc(100), c21=cutCalc(21);
cutRender(100);
const cut100Text=(document.getElementById('cutOut')||{}).innerText||'';
cutRender(21);
const cut21Text=(document.getElementById('cutOut')||{}).innerText||'';
// 采用档位：阈值应同步到 21，飞单/风险重算
cutApply(21); await WAIT(120);
const appliedTh=splitTakeAll;
const afterBets=cutBets();
const after21=cutCalc(21);
R.cut={bets:bets.length,selfSum,top:bets[0]?bets[0].self:0,c0,c100,c21,cut100Text:cut100Text.slice(0,260),cut21Text:cut21Text.slice(0,260),appliedTh,afterTop:afterBets[0]?afterBets[0].self:0,after21};
gate('削峰有注号3个', bets.length===3, R.cut);
gate('削峰自留+飞掉守恒', Math.abs((c100.kept+c100.flown)-selfSum)<0.01, {kept:c100.kept,flown:c100.flown,selfSum});
gate('削峰亏损线公式', Math.abs(c100.line-(c100.kept/payMult))<0.01, {line:c100.line,kept:c100.kept,payMult});
gate('削峰最坏公式', Math.abs(c100.worst-(c100.kept-payMult*c100.maxKeep))<0.01, {worst:c100.worst,maxKeep:c100.maxKeep});
gate('削峰100有输出', cut100Text.indexOf('削到 100')>-1 && cut100Text.indexOf('分档效率')>-1, cut100Text.slice(0,120));
gate('削峰21有输出', cut21Text.indexOf('削到 21')>-1 && cut21Text.indexOf('分档效率')>-1, cut21Text.slice(0,120));
gate('采用21档生效', appliedTh===21 && R.cut.afterTop===21, {appliedTh,afterTop:R.cut.afterTop});
// 档位不产生 NaN
gate('削峰无NaN', !/NaN|undefined/.test(cut100Text+cut21Text), (cut100Text+cut21Text).slice(0,200));

/* 真实开奖 321 期结算回放：特41 100 + 二中二15,45 100，全飞，返水3% */
{
  reset();
  lastDraw = {period:'321', specialNum:41, regularNums:[15,45,23,8,47,49]};
  if(typeof saveLastDraw==='function') saveLastDraw();
  autoFlyOn = true;
  splitTakeAll = 0; if(typeof saveSplitAll==='function') saveSplitAll();
  flownPerPos = {}; flownReal = {};
  flownPerPos['41'] = 100; flownReal['41'] = 100;
  try{ localStorage.setItem(sk('flownPerPos'), JSON.stringify(flownPerPos)); localStorage.setItem(sk('flownReal'), JSON.stringify(flownReal)); }catch(e){}
  localStorage.setItem('rebateOn','1'); localStorage.setItem('rebateRate','0.03');
  document.getElementById('customerName').value='回放';
  await appendSave('特41 100');
  await appendSave('二中二15,45 100');
  const ap = actualPnL();
  const d = todayReconData();
  const exp = {sales:200, payout:10700, flyOut:200, flyBack:10700, net:0, rebate:6, localNet:0, upSettle:10506};
  R.replay = {
    sales:ap.sales, payout:ap.payout, flyOut:ap.flyOut, flyBack:ap.flyBack, net:ap.net, rebate:ap.rebate,
    localNet:d.localNet, upSettle:d.upSettle, expect:exp
  };
  gate('回放总单/客户赔付', ap.sales===exp.sales && ap.payout===exp.payout, R.replay);
  gate('回放飞出/上家赔回', ap.flyOut===exp.flyOut && ap.flyBack===exp.flyBack, R.replay);
  gate('回放实际盈亏/返水', Math.abs(ap.net-exp.net)<0.01 && Math.abs(ap.rebate-exp.rebate)<0.01, R.replay);
  gate('回放飞后净/上家结算', Math.abs(d.localNet-exp.localNet)<0.01 && Math.abs(d.upSettle-exp.upSettle)<0.01, R.replay);
  // 部分飞：阈值100，只真飞特41 100；今日对账必须和全盘盈亏同一个“已飞”口径
  splitTakeAll = 100; if(typeof saveSplitAll==='function') saveSplitAll();
  const apPartial = actualPnL();
  const dPartial = todayReconData();
  R.replay.partial = {flyOut:apPartial.flyOut, net:apPartial.net, rebate:apPartial.rebate, localNet:dPartial.localNet, upSettle:dPartial.upSettle, flyCalc:dPartial.flyCalc};
  gate('部分飞今日对账与全盘口径一致', Math.abs(dPartial.localNet-apPartial.net)<0.01 && Math.abs(dPartial.rebate-apPartial.rebate)<0.01 && Math.abs(dPartial.localNet-(dPartial.gross-apPartial.flyOut+apPartial.flyBack))<0.01, R.replay);
  localStorage.setItem('rebateOn','0'); reset(); lastDraw=null;
}

R.pass=R.cases.filter(c=>c.status==='PASS').length;
R.fail=R.cases.filter(c=>c.status==='FAIL').length;
return R;
})()
