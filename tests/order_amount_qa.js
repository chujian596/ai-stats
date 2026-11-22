/* 录入订单 / 金额对应 / 弹窗 回归质检
   目的：同一张单里同一代码出现多次时，金额只能按合并后的 codeAmts 计一次。
   页面执行后写到 window.__orderAmtQA。 */
(async()=>{
const WAIT=ms=>new Promise(r=>setTimeout(r,ms));
const results=[], fails=[];
function add(name, ok, detail){
  const row={name, status: ok?'PASS':'FAIL', detail};
  results.push(row); if(!ok) fails.push(row);
}
function num(v){ return Number(v)||0; }
function reset(){
  try{
    orders=[]; hkOrders=[]; shop='A';
    pteFlyTakeAll=0; splitTakeAll=0; lxFlyAmt=0; lxFlyName='';
    autoFlyOn=false; emFlyOn=false;
    flownPerPos={}; flownReal={};
    window.__lastSavedOrderId=null; window.__al=[]; window.__failedLines=[];
    document.querySelectorAll('.ai-ov').forEach(x=>x.remove());
  }catch(e){}
  const cn=document.getElementById('customerName'); if(cn)cn.value='质检甲';
  const sm=document.getElementById('saveMsg'); if(sm)sm.innerHTML='';
}
try{localStorage.clear(); localStorage.setItem('ai_preview_enabled','0'); localStorage.setItem('emFlyOn','0'); localStorage.setItem('autoFlyOn','0');}catch(e){}
window.__previewConfirmed=true; window.__dupConfirmed=true;
window.myAlert=m=>{window.__al=(window.__al||[]).concat(String(m));};
window.myConfirm=(m,f)=>{if(typeof f==='function')f();};

// 1) 同一单两行“平特兔”，金额 300+500，只能落成 800
reset();
const inp=document.getElementById('input'); inp.value='平特兔300\n平特兔500';
try{doSave();}catch(e){add('录入不抛错',false,e.message||String(e));}
await WAIT(450);
const all=[...orders,...hkOrders];
const one=all[0]||{};
const sum=all.reduce((s,o)=>s+num(o.amount),0);
const msg=((document.getElementById('saveMsg')||{}).innerText||'').replace(/\s+/g,' ');
add('录入落单1张', all.length===1, {n:all.length});
add('订单金额=800', Math.abs(sum-800)<0.02, {sum,amount:one.amount});
add('保存消息含800.00', msg.indexOf('800.00')>=0, {msg:msg.slice(0,80)});
add('录入无告警', (window.__al||[]).length===0, {alerts:window.__al});
add('同码保留重复标记但金额合并', (one.codes||[]).filter(c=>c==='平特兔').length===2 && num((one.codeAmts||{})['平特兔'])===800, {codes:one.codes,codeAmts:one.codeAmts});
add('订单明细合计=800', Math.abs(num(one.amount)-800)<0.02, {amount:one.amount});

// 2) 统计口径：总单 / 平特持仓 / 今日对账 / 分类应飞 必须全是 800
let grand=0, fly=null, recon=null, err='';
try{
  grand=num(grandOrderTotal());
  fly=getThisRoundFly();
  recon=todayReconData();
}catch(e){err=e.message||String(e);}
add('统计不抛错', !err, {err});
add('总单=800', Math.abs(grand-800)<0.02, {grand});
add('平特应飞=800', fly && Math.abs(num(fly.totalFly)-800)<0.02 && Math.abs(num(fly.thisRound)-800)<0.02, fly?{totalFly:fly.totalFly,thisRound:fly.thisRound}:{});
add('今日对账订单总额=800', recon && Math.abs(num(recon.sales)-800)<0.02, recon?{sales:recon.sales}:{});
add('今日对账明细合计=800', recon && Math.abs(num(recon.detail)-800)<0.02, recon?{detail:recon.detail}:{});
add('今日对账订单无差异', recon && recon.orderOk===true, recon?{orderOk:recon.orderOk,badOrders:recon.badOrders}:{});
add('今日对账平特应飞=800', recon && Math.abs(num(recon.pteFull)-800)<0.02, recon?{pteFull:recon.pteFull}:{});
add('今日对账分类合计=应飞', recon && Math.abs(num(recon.flyCalc)-num(recon.fly.totalFly))<0.02, recon?{flyCalc:recon.flyCalc,totalFly:recon.fly.totalFly}:{});
add('今日对账飞单无差异', recon && recon.flyOk===true, recon?{flyOk:recon.flyOk}:{});

// 3) 飞单明细口径：已飞 300，按现阈值还该飞 800，扣掉已飞还要补 500
flownPerPos['平特兔']=300; flownReal['平特兔']=300;
let txt='';
try{ renderRisk(); txt=((document.getElementById('riskBody')||document.body).textContent)||''; }catch(e){add('风险面板渲染不抛错',false,e.message||String(e));}
const flat=txt.replace(/\s+/g,' ');
add('飞单显示按现阈值还该飞800', flat.indexOf('按现阈值还该飞 800')>=0, {has:flat.indexOf('按现阈值还该飞 800')>=0});
add('飞单显示扣掉已飞还要补500', flat.indexOf('扣掉已飞还要补 500')>=0, {has:flat.indexOf('扣掉已飞还要补 500')>=0});
add('已飞超过应飞时不误报警', flat.indexOf('比按现阈值该飞的')<0, {hasWarning:flat.indexOf('比按现阈值该飞的')>=0});

// 4) 弹窗质检：点一次选项后必须只剩 0 个弹窗，金额与选项标注一致
reset();
inp.value='平特马兔各10';
try{doSave();}catch(e){add('弹窗用例不抛错',false,e.message||String(e));}
await WAIT(220);
const ovBefore=document.querySelectorAll('.ai-ov');
add('弹窗只弹一个', ovBefore.length===1, {n:ovBefore.length});
let sel=0, label='';
const ov=ovBefore[0];
if(ov){
  const btn=ov.querySelector('#mzA');
  if(btn){ label=(btn.innerText||'').trim(); let m=label.match(/总额([0-9]+(?:\.[0-9]+)?)/); if(!m)m=label.match(/共([0-9]+(?:\.[0-9]+)?)元/); if(!m)m=label.match(/([0-9]+(?:\.[0-9]+)?)元/); sel=m?num(m[1]):NaN; btn.click(); }
  else add('弹窗有选项', false, {txt:(ov.innerText||'').slice(0,80)});
}
await WAIT(450);
const ovAfter=document.querySelectorAll('.ai-ov');
add('点选项后弹窗关闭', ovAfter.length===0, {n:ovAfter.length});
const all2=[...orders,...hkOrders];
const sum2=all2.reduce((s,o)=>s+num(o.amount),0);
add('弹窗落单金额=选项标注', Number.isFinite(sel) && Math.abs(sum2-sel)<0.02, {sel,sum:sum2,label});
add('弹窗保存消息含金额', Number.isFinite(sel) && ((document.getElementById('saveMsg')||{}).innerText||'').indexOf(sel.toFixed(2))>=0, {sel});

// 5) 本次录入故障回归：复式冒号两种语序 + 多行横杠组合续行
async function comboCase(name, text, expAmt, expCodes){
  reset();
  inp.value=text;
  window.__failedLines=[];
  let threw='';
  try{ doSave(); }catch(e){ threw=e.message||String(e); }
  await WAIT(80);
  const all=[...orders,...hkOrders];
  const sum=all.reduce((s,o)=>s+num(o.amount),0);
  const codes=(all[0]||{}).codes||[];
  add(name+' 落单1张', all.length===1 && !threw, {n:all.length,threw});
  add(name+' 金额='+expAmt, Math.abs(sum-expAmt)<0.02, {sum});
  add(name+' 组数='+expCodes, codes.length===expCodes, {codes:codes.length});
  add(name+' 无失败行', (window.__failedLines||[]).length===0, {failed:window.__failedLines});
}
await comboCase('三中三复式冒号', '三中三复式:09,45,04，16，03，15，07，31，30，36，34，各组1', 165, 165);
await comboCase('复式三中三冒号', '复式三中三:09,45,04 ，16，03，15，07，31，30，36，34，各组1', 165, 165);
await comboCase('横杠组合续行', '三中三09-30-31\n30-31-34\n04-07-34\n09-36-45\n04-36-07各组5', 25, 5);

window.__orderAmtQA={tested:results.length,pass:results.filter(r=>r.status==='PASS').length,fail:fails.length,fails:fails.slice(0,12),results};
})();
