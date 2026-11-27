"""二三复式：只按一整组展示，不逐组合展开；命中说明按复式整组结算。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
TXT='''03 500
平特马 200
三中三复式01.02.03.04.05.06.07各5
'''
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':430,'height':1000}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=rpqa',wait_until='load'); pg.wait_for_timeout(300)
    pg.evaluate("()=>{localStorage.clear();localStorage.setItem('ai_preview_enabled','0');}")
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=rpqa',wait_until='load'); pg.wait_for_timeout(500)
    pg.evaluate("(t)=>{document.getElementById('input').value=t;doSave();}",TXT); pg.wait_for_timeout(500)
    pg.evaluate("()=>renderRisk()"); pg.wait_for_timeout(300)
    tabs=pg.evaluate("()=>Array.from(document.querySelectorAll('#flyListPreview .fd-table'))")
    data=pg.evaluate("()=>{var t=Array.from(document.querySelectorAll('#flyListPreview .fd-table')).pop();return {rows:t.querySelectorAll('tbody tr').length,cells:Array.from(t.querySelectorAll('tbody tr td')).map(x=>x.innerText.trim())};}")
    chk('二三只一行',data['rows']==1,data)
    chk('显示复式整组和35组',any('三中三复式' in x for x in data['cells']) and any('35组' in x for x in data['cells']),data['cells'])
    cell=[x for x in data['cells'] if x.isdigit()]
    chk('复式注额175',cell[:1]==['175'],cell)
    foot=pg.evaluate("()=>Array.from(document.querySelectorAll('#flyListPreview .fd-table')).pop().closest('details').innerText")
    chk('写明命中按复式整组结算','命中时按复式整组结算' in foot)
    chk('不再逐组展开',pg.evaluate("()=>Array.from(document.querySelectorAll('#flyListPreview .fd-table')).pop().querySelectorAll('tbody tr.fd-sub').length")==0)
    chk('页面无通道字样','通道' not in pg.evaluate("()=>document.getElementById('flyListPreview').textContent"))
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('FAILS',len(FAIL)); sys.exit(1 if FAIL else 0)
