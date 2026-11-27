"""二三飞单：每一笔原始订单各一行；复式只显示该笔号码/组数，不展开组合，也不合并成一整行。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
TXT='''03 500
平特马 200
三中三复式01.02.03.04.05.06.07各5
三中三复式08.09.10.11.12.13各10
三中三:01,02,03 20
'''
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':430,'height':1200}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=foqa',wait_until='load'); pg.wait_for_timeout(300)
    pg.evaluate("()=>{localStorage.clear();localStorage.setItem('ai_preview_enabled','0');}")
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=foqa',wait_until='load'); pg.wait_for_timeout(500)
    pg.evaluate("(t)=>{document.getElementById('input').value=t;doSave();}",TXT); pg.wait_for_timeout(600)
    pg.evaluate("()=>renderRisk()"); pg.wait_for_timeout(400)
    data=pg.evaluate("""()=>{var t=Array.from(document.querySelectorAll('#flyListPreview .fd-table')).pop();return {rows:Array.from(t.querySelectorAll('tbody tr')).map(r=>Array.from(r.children).map(x=>x.innerText.trim())),sub:t.querySelectorAll('tbody tr.fd-sub').length};}""")
    chk('三笔订单三行',len(data['rows'])==3,data['rows'])
    chk('第一笔复式35组/175',('35组' in data['rows'][0][0]) and data['rows'][0][1]=='175',data['rows'][0])
    chk('第二笔复式20组/200',('20组' in data['rows'][1][0]) and data['rows'][1][1]=='200',data['rows'][1])
    chk('第三笔单式1组/20',('1组' in data['rows'][2][0]) and data['rows'][2][1]=='20',data['rows'][2])
    chk('三行下注合计395',sum(float(x[1]) for x in data['rows'])==395,data['rows'])
    chk('无分组小标题',data['sub']==0,data)
    meta=pg.evaluate("()=>Array.from(document.querySelectorAll('#flyListPreview .fd-sec-meta')).pop().innerText")
    chk('头部写3笔订单而不是合并组数','3笔订单' in meta and '55组' not in meta,meta)
    foot=pg.evaluate("()=>Array.from(document.querySelectorAll('#flyListPreview .fd-sec')).pop().querySelector('.fd-foot').innerText")
    chk('写明每笔一行', '每一笔订单各占一行' in foot)
    chk('写明复式整组结算', '命中时按复式整组结算' in foot)
    chk('不出现逐组合行',len(data['rows'])==3)
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('FAILS',len(FAIL)); sys.exit(1 if FAIL else 0)
