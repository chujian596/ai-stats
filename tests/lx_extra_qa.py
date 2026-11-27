"""连肖额外飞：客户800 + 手动200，明细逐笔列，合计800/1000/0/-200。"""
import sys, re
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':430,'height':1200}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=lxextra',wait_until='load'); pg.wait_for_timeout(300)
    pg.evaluate("()=>{localStorage.clear();localStorage.setItem('ai_preview_enabled','0');localStorage.setItem(sk('autoFlyOn'),'1');localStorage.setItem(sk('emFlyOn'),'1');}")
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=lxextra',wait_until='load'); pg.wait_for_timeout(500)
    pg.evaluate("(t)=>{document.getElementById('input').value=t;doSave();}",'连肖猪蛇 500\n连肖鸡鼠 300'); pg.wait_for_timeout(600)
    pg.evaluate("""()=>{window.myAlert=function(){};_applyManualFlyCore('连肖马鸡 100\\n连肖马鸡羊 100', null, false);flownPerPos['连肖猪蛇']=500;flownReal['连肖猪蛇']=500;flownPerPos['连肖鸡鼠']=300;flownReal['连肖鸡鼠']=300;}"""); pg.wait_for_timeout(500)
    pg.evaluate("()=>{switchTab('rank');openRankSection('risk');renderRisk();}"); pg.wait_for_timeout(400)
    pg.evaluate("()=>{var e=document.getElementById('flyListPreview');if(e.style.display==='none')document.querySelector('[onclick*=\"flyListPreview\"]').click();}"); pg.wait_for_timeout(300)
    sec=pg.evaluate("()=>{var s=Array.from(document.querySelectorAll('#flyListPreview .fd-sec')).find(x=>x.innerText.includes('连肖'));return s?s.innerText:'';}")
    chk('连肖客户下注800','4组 · 下注800' in sec,sec[:100])
    chk('额外飞写明2笔200','额外飞（客户单以外' in sec and '马鸡 额外飞' in sec and '马鸡羊 额外飞' in sec)
    m=re.search(r'小计：下注 (\d+) ｜ 已飞 (\d+) ｜ 待飞 (\d+) ｜ 自留 (-?\d+)',sec)
    chk('连肖小计 800/1000/0/-200',m and m.groups()==('800','1000','0','-200'),m.groups() if m else sec[-100:])
    chk('无 JS 报错',not errs,errs[:2]); b.close()
print('FAILS',len(FAIL)); sys.exit(1 if FAIL else 0)
