"""复式解析 A/B 回归：把 v59.88（无「4号以上自动复式」规则）与当前版本并跑同一组写法，
只允许「4个以上号码 + 各组X」的两条用例出现差异，其余老写法金额/注数必须完全一致。
用法：先起两个 http.server（当前仓 8765、旧版快照目录 8766），再 python3 tests/combo_ab_regress.py
"""
import asyncio, json, subprocess, time
from playwright.async_api import async_playwright
CASES = [
 # 老写法：三/二/三中三 恰好 3 或 2 个号
 "三中三 07 24 32 100",
 "三中三 07-24-32三中三100",
 "二中二 03,10 100",
 "03,10 二中二 100",
 "三中三 09,30,31 各组5",
 "三中三 09.30.31.05.49复三",
 "三中三[21-28-39]=各组20",
 "三中三复式:09,45,12,03 各5",
 "02，38，13，37，08，20各5三中三复式",
 # 其它玩法 4+ 号码 + 各X（不该被新规则带走）
 "特号 05.12.33.44 各10",
 "平特 11.22.33.05 各10",
 "连肖 马蛇狗猪 各10",
 # 新增支持
 "三中三 19.43.03.04.27.12 各组1",
 "二中二 19.43.03.04.27.12 各组34",
]
JS = r"""(async()=>{const W=ms=>new Promise(r=>setTimeout(r,ms));
try{localStorage.clear()}catch(e){}
const out=[];const CASES=__CASES__;
for(const t of CASES){
 orders=[];shop='A';splitTakeAll=70;pteFlyTakeAll=3000;lxFlyAmt=0;autoFlyOn=true;
 flownPerPos={};flownReal={};lastDraw=null;
 window.myAlert=()=>{};window.myConfirm=(m,f)=>{if(f)f()};window.__previewConfirmed=true;
 document.getElementById('input').value=t;
 let err='';
 try{doSave()}catch(e){err=String(e.message||e)}
 await W(120); document.querySelectorAll('.ai-ov').forEach(x=>x.remove());
 out.push({t, v:typeof APP_VER!=='undefined'?APP_VER:'', n:orders.length, amt:orders.reduce((a,o)=>a+(+o.amount||0),0), codes:orders.map(o=>(o.codes||[]).length+'注').join('/'), err});
}
return out;})()"""
async def run(pg):
    cases = json.dumps(CASES, ensure_ascii=False).replace('__', '')
    js = JS.replace('__CASES__', json.dumps(CASES, ensure_ascii=False))
    return await pg.evaluate(js)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/local/bin/chromium", args=["--no-sandbox"])
        pg = await b.new_page()
        await pg.goto("http://127.0.0.1:8766/app-pro.html?nock=1", wait_until="load"); await pg.wait_for_timeout(600)
        old = await run(pg)
        await pg.goto("http://127.0.0.1:8765/app-pro.html?nock=1", wait_until="load"); await pg.wait_for_timeout(600)
        new = await run(pg)
        for a,bb in zip(old,new):
            same = (a['amt']==bb['amt'] and a['codes']==bb['codes'])
            print(('SAME ' if same else 'DIFF ')+a['t'][:46].ljust(46), '| v59.88:', a['amt'], a['codes'], '| v59.89:', bb['amt'], bb['codes'], ('ERR:'+bb['err']) if bb['err'] else '')
        await b.close()
asyncio.run(main())
