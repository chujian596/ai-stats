/*
 * 混搭命中/赔付回归（浏览器执行）
 * 用法：在 app-pro.html 页面执行本文件（bu.js / 控制台），返回结构化结果。
 * 目的：证明一张混搭单内部按 code/codeAmts 分开判定，不是把整单金额套一个倍数。
 */
(async()=>{
  const WAIT = ms => new Promise(r=>setTimeout(r, ms));
  const R = { version: (typeof APP_VER!=='undefined'?APP_VER:'?'), runner:'settle-mixed-v1', cases:[], failures:[] };
  const clear = () => document.querySelectorAll('.ai-ov').forEach(x=>x.remove());

  function reset(){
    try{ localStorage.clear(); }catch(e){}
    orders=[]; hkOrders=[]; shop='A'; payMult=47; payMultSingle=2;
    lastPrice=null; _texiaoChoice=null; window._waveChoice=null; window._waveCanonical=null;
    window.__ambigAbort=false; window.__previewConfirmed=true; pendingProduct=null; mode='normal';
    window.myAlert=(m)=>{ window.__qaAlerts=window.__qaAlerts||[]; window.__qaAlerts.push(String(m)); };
    window.myConfirm=(m,fn)=>{ if(fn) fn(); };
    window.prompt=()=>null;
    clear();
  }

  function fail(name, detail){
    R.cases.push({name, status:'FAIL', detail});
    R.failures.push({name, detail});
  }

  function pass(name, detail){
    R.cases.push({name, status:'PASS', detail});
  }

  async function saveAndSettle(name, input, draw, mustHave, expTotal){
    reset();
    document.getElementById('input').value = input;
    let err='';
    try{ doSave(); }catch(e){ err = e.message || String(e); }
    await WAIT(180);
    if(err || !orders.length){ fail(name, '录入失败：'+(err||'无订单')); return; }
    const o = orders[0];
    const orderAmt = Number(o.amount||0);
    try{ saveOrders(); }catch(e){}
    try{ localStorage.setItem(sk('lastDrawPeriod'),'0'); }catch(e){}
    document.getElementById('input').value = draw;
    let settleErr='';
    try{ autoPayout(); }catch(e){ settleErr = e.message || String(e); }
    await WAIT(200);
    const ov = document.querySelector('.ai-ov');
    if(!ov || settleErr){
      fail(name, '结算未出弹窗：'+(settleErr||'无弹窗'));
      return;
    }
    const text = ov.innerText.replace(/\r/g,'');
    clear();
    for(const s of mustHave){
      if(text.indexOf(s) < 0){ fail(name, '缺行：'+s+'\n实际：'+text.slice(0,900)); return; }
    }
    if(expTotal !== undefined){
      const m = text.match(/合计赔付：([\d.]+)/);
      if(!m || Math.abs(parseFloat(m[1]) - expTotal) > 0.01){
        fail(name, '合计赔付期望 '+expTotal+'，实际 '+(m?m[1]:'无')); return;
      }
    }
    pass(name, {orderAmt, total: (text.match(/合计赔付：([\d.]+)/)||[])[1]||'?', snippet: text.slice(0,700)});
  }

  // 1) 三类别混搭：特号 + 二中二 + 三中三
  await saveAndSettle(
    '混搭三日结算',
    '特号01.02.03.04各100\n二中二10,11 50\n三中三07,24,32 30',
    '321 07 24 32 10 11 12 03',
    [
      '03号 下注100.00 ×47 = 4700.00',
      '二中二:10,11 下注50.00 ×60 = 3000.00',
      '三中三:07,24,32 下注30.00 ×600 = 18000.00',
      '总单金额：480.00',
    ],
    25700
  );

  // 2) 号码 + 平特 + 连肖混搭：每类都按自己的金额和倍数
  await saveAndSettle(
    '混搭五类结算',
    '特号01.02.03.04各100\n二中二07,24 50\n三中三07,24,32 30\n平特马龙兔各数100\n连肖龙虎兔100',
    '321 01 04 05 07 24 32 03',
    [
      '03号 下注100.00 ×47 = 4700.00',
      '二中二:07,24 下注50.00 ×60 = 3000.00',
      '三中三:07,24,32 下注30.00 ×600 = 18000.00',
      '平特马 下注100.00 ×1.8 = 180.00',
      '平特龙 下注100.00 ×2 = 200.00',
      '平特兔 下注100.00 ×2 = 200.00',
      '连肖龙虎兔 下注100.00 ×10 = 1000.00',
      '总单金额：880.00',
    ],
    27280
  );

  // 3) 同一号码重复不同金额：合并成 150，不能只算最后/第一笔
  await saveAndSettle(
    '同号重复金额结算',
    '特号01 100\n特号01 50',
    '321 01',
    [
      '01号 下注150.00 ×47 = 7050.00',
      '总单金额：150.00',
    ],
    7050
  );

  // 4) 特号不算组合：二中二里有一个特号，不能判中
  await saveAndSettle(
    '特号不算组合',
    '特号01.02.03.04各100\n二中二03,10 50\n三中三07,24,32 30',
    '321 07 24 32 10 11 12 03',
    [
      '03号 下注100.00 ×47 = 4700.00',
      '三中三:07,24,32 下注30.00 ×600 = 18000.00',
      '总单金额：480.00',
    ],
    22700
  );

  R.summary = {
    total: R.cases.length,
    pass: R.cases.filter(x=>x.status==='PASS').length,
    fail: R.failures.length,
  };
  return JSON.stringify(R);
})();
