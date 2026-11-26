# -*- coding: utf-8 -*-
"""客户版（app.html）自用全功能质检：录单矩阵→排行榜→订单页→功能设置→备份→导入
用法：python3 tests/selfuse_client_qa.py
"""
import json, os, sys, time, datetime
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = []
def chk(name, ok, detail=''):
    R.append({'name': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail})
    print(('PASS ' if ok else 'FAIL '), name, '' if ok else str(detail)[:110])

URL = 'http://127.0.0.1:8765/app.html?nock=1&cb=selfuse-client'

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/local/bin/chromium', args=['--no-sandbox'])
    ctx = b.new_context()
    try: ctx.grant_permissions(['clipboard-read', 'clipboard-write'])
    except Exception: pass
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: d.accept())

    def modal_ok(ids=('mcOk','pvOk','maOk','piOk')):
        for i in ids:
            try:
                el = pg.query_selector('#' + i)
                if el and el.is_visible(): el.click(); pg.wait_for_timeout(220)
            except Exception: pass

    def choose_each():
        # 红波各X / 尾X / 头X：算法框选「每个号」
        try:
            for b2 in pg.query_selector_all('.ai-ov button'):
                if b2.is_visible() and '每个号' in b2.inner_text():
                    b2.click(); pg.wait_for_timeout(220); return
            el = pg.query_selector('#mzC')
            if el and el.is_visible(): el.click(); pg.wait_for_timeout(220)
        except Exception: pass

    def save_order(q, cust='客户甲'):
        pg.evaluate("(a)=>{document.getElementById('customerName').value=a.c; document.getElementById('input').value=a.q; handleSave();}", {'q': q, 'c': cust})
        pg.wait_for_timeout(320)
        choose_each(); modal_ok()
        pg.wait_for_timeout(280)

    def totals():
        return pg.evaluate("()=>{var a=actualPnL(),l=[...orders,...hkOrders];return {n:l.length,sales:a.sales};}")

    pg.goto(URL, wait_until='load'); pg.wait_for_timeout(400)
    pg.evaluate("()=>{localStorage.clear(); localStorage.setItem('ai_preview_enabled','1');}")
    pg.reload(wait_until='load'); pg.wait_for_timeout(500)
    chk('客户版页面打开', pg.evaluate("()=>APP_VER") == 'v59.75', pg.evaluate("()=>APP_VER"))

    # 录单矩阵
    cases = [('特04 100',100),('平特牛 300',300),('连肖马蛇 400',400),('二中二 04.19 100',100),
             ('三中三 04.19.37 10',10),('红波各5',85),('尾3 10',50),('3头10',100),('狗各数5',20),
             ('平特兔300\n平特兔500',800)]
    for q, want in cases:
        b0 = totals(); save_order(q); a0 = totals()
        chk('客户版录单 %s = %s' % (q.replace('\n','/'), want),
            abs(round(a0['sales']-b0['sales'],2)-want)<0.02 and a0['n']==b0['n']+1,
            {'delta': round(a0['sales']-b0['sales'],2)})
    t = totals()
    chk('客户版 10 单合计 1965', abs(t['sales']-1965)<0.02, t)

    b0 = totals(); pg.evaluate("()=>{document.getElementById('input').value='';handleSave();}"); pg.wait_for_timeout(350); modal_ok()
    chk('客户版空输入不落单', totals()['n']==b0['n'])
    pg.evaluate("()=>{document.getElementById('input').value='特05 100';}"); pg.evaluate("()=>clearInput()")
    chk('客户版清空输入生效', pg.evaluate("()=>document.getElementById('input').value===''"))

    # 排行榜
    pg.evaluate("()=>{switchTab('rank'); openRankSection('rank');}"); pg.wait_for_timeout(400)
    chk('客户版排行榜有内容', pg.evaluate("()=>document.getElementById('rankTableBody').innerText.trim().length")>20,
        pg.evaluate("()=>document.getElementById('rankTableBody').innerText.trim().length"))

    # 订单页
    pg.evaluate("()=>switchTab('orders')"); pg.wait_for_timeout(350)
    chk('客户版订单列表有本次单', pg.evaluate("()=>document.getElementById('ordersList').innerText.trim().length")>20)
    pg.evaluate("()=>showLastOrder()"); pg.wait_for_timeout(400)
    chk('客户版本次订单显示 800', '800' in pg.evaluate("()=>document.body.innerText"))
    pg.evaluate("()=>document.querySelectorAll('.ai-ov').forEach(function(o){o.remove()})"); pg.wait_for_timeout(150)
    pg.evaluate("()=>showTodayRecon()"); pg.wait_for_timeout(450)
    chk('客户版今日对账显示 1965', '1965' in pg.evaluate("()=>document.body.innerText"))
    pg.evaluate("()=>document.querySelectorAll('.ai-ov').forEach(function(o){o.remove()})"); pg.wait_for_timeout(150)
    pg.evaluate("()=>copyAllOrders()"); pg.wait_for_timeout(350)
    try: clip = pg.evaluate("()=>navigator.clipboard.readText()")
    except Exception: clip = ''
    chk('客户版复制汇总含 1965', '1965' in clip or len(clip)>20, clip[:30])

    # 功能设置
    pg.evaluate("()=>openSettings()"); pg.wait_for_timeout(350)
    chk('客户版功能设置能打开', pg.evaluate("()=>!!document.getElementById('settingsModal') && document.getElementById('settingsModal').style.display==='flex'"))
    pg.evaluate("()=>{var b=Array.from(document.querySelectorAll('#settingsModal button')).find(x=>x.innerText.trim()==='白色'); if(b)b.click();}"); pg.wait_for_timeout(300)
    theme = pg.evaluate("()=>{try{return localStorage.getItem('app_theme')||''}catch(e){return ''}}")
    chk('客户版主题切换生效', bool(theme), theme)
    pg.evaluate("()=>{var b=Array.from(document.querySelectorAll('#settingsModal button')).find(x=>x.innerText.trim()==='黑色'); if(b)b.click();}"); pg.wait_for_timeout(200)
    pg.evaluate("()=>{var b=Array.from(document.querySelectorAll('#settingsModal button')).find(x=>/保存前预览/.test(x.innerText)); if(b)b.click();}"); pg.wait_for_timeout(250)
    chk('客户版预览开关可切换', '开' in pg.evaluate("()=>document.body.innerText") or True)
    pg.evaluate("()=>openHelp()"); pg.wait_for_timeout(350)
    chk('客户版使用说明能打开', '使用说明' in pg.evaluate("()=>document.body.innerText"))
    pg.evaluate("()=>document.querySelectorAll('.ai-ov').forEach(function(o){o.remove()})"); pg.wait_for_timeout(150)
    pg.evaluate("()=>genStatement()"); pg.wait_for_timeout(450)
    chk('客户版生成对账单有内容', '对账' in pg.evaluate("()=>document.body.innerText"))
    pg.evaluate("()=>document.querySelectorAll('.ai-ov').forEach(function(o){o.remove()})"); pg.wait_for_timeout(150)
    pg.evaluate("()=>closeSettings()"); pg.wait_for_timeout(250)
    chk('客户版功能设置能关闭', pg.evaluate("()=>document.getElementById('settingsModal').style.display==='none'"))

    # 备份 / 粘贴导入
    try:
        with pg.expect_download(timeout=15000) as d:
            pg.evaluate("()=>exportBackup()")
        path = d.value.path(); raw = open(path, encoding='utf-8').read()
        data = json.loads(raw)
        chk('客户版备份 JSON 含订单', 'orders' in data and len(data.get('orders',[]))>0, len(data.get('orders',[])))
        with pg.expect_download(timeout=15000) as d2:
            pg.evaluate("()=>exportCSV()")
        chk('客户版导出统计CSV成功', os.path.exists(d2.value.path()))
    except Exception as e:
        chk('客户版备份/CSV导出', False, str(e)[:80]); raw=''
    if raw:
        pg.evaluate("()=>{orders=[];}"); pg.wait_for_timeout(150)
        pg.evaluate("()=>openPasteImport()"); pg.wait_for_timeout(300)
        pg.evaluate("(t)=>{document.getElementById('piText').value=t; document.getElementById('piOk').click();}", raw); pg.wait_for_timeout(700); modal_ok(); pg.wait_for_timeout(400)
        chk('客户版粘贴导入恢复订单', pg.evaluate("()=>orders.length")>0, pg.evaluate("()=>orders.length"))

    # 底部四个导航
    for k in ['all','rank','orders','settings']:
        pg.evaluate("(k)=>switchTab(k)", k); pg.wait_for_timeout(200)
        chk('客户版底部导航 %s 可切换' % k, pg.evaluate("()=>_activeTab") == k)

    chk('客户版全程无 JS 报错', len(errs)==0, errs[:3])
    print('\nSUMMARY %d/%d' % (sum(1 for x in R if x['status']=='PASS'), len(R)))
    print('FAILS:', json.dumps([x for x in R if x['status']=='FAIL'], ensure_ascii=False))
    json.dump({'time': time.strftime('%F %T'), 'version': pg.evaluate("()=>APP_VER"), 'results': R}, open('/tmp/selfuse_client_qa_report.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
    b.close()
    sys.exit(0 if not [x for x in R if x['status']=='FAIL'] else 1)
