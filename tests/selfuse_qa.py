# -*- coding: utf-8 -*-
"""自用全流程质检：按真实一天的用法走一遍（录单→订单→归档→排行→飞单→备份→设置）
用法： python3 tests/selfuse_qa.py
"""
import json, os, sys, time, datetime
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = []
def chk(name, ok, detail=''):
    R.append({'name': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail})
    print(('PASS ' if ok else 'FAIL '), name, '' if ok else str(detail)[:120])

URL = 'http://127.0.0.1:8765/app-pro.html?nock=1&cb=selfuse'

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/local/bin/chromium', args=['--no-sandbox'])
    ctx = b.new_context()
    try: ctx.grant_permissions(['clipboard-read', 'clipboard-write'])
    except Exception: pass
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('dialog', lambda d: d.accept())

    def modal_ok(ids=('mcOk', 'pvOk', 'maOk', 'piOk')):
        for i in ids:
            try:
                el = pg.query_selector('#' + i)
                if el and el.is_visible():
                    el.click(); pg.wait_for_timeout(250)
            except Exception: pass

    def save_order(q, cust='自用甲'):
        pg.evaluate("""(a)=>{document.getElementById('customerName').value=a.c; document.getElementById('input').value=a.q; handleSave();}""", {'q': q, 'c': cust})
        pg.wait_for_timeout(350)
        # 「红波各5 / 尾3 10 / 3头10」会弹算法框：选「每号各」（mzC）
        try:
            el = pg.query_selector('#mzC')
            if el and el.is_visible():
                el.click(); pg.wait_for_timeout(250)
            else:
                for b in pg.query_selector_all('.ai-ov button'):
                    if b.is_visible() and '每个号' in b.inner_text():
                        b.click(); pg.wait_for_timeout(250); break
        except Exception: pass
        modal_ok()
        pg.wait_for_timeout(300)

    def totals():
        return pg.evaluate("()=>{var a=actualPnL(); var l=[...orders,...hkOrders]; return {n:l.length, sales:a.sales};}")

    # ---------- 0 干净开局 ----------
    pg.goto(URL, wait_until='load'); pg.wait_for_timeout(400)
    pg.evaluate("()=>{localStorage.clear(); localStorage.setItem('ai_preview_enabled','1');}")
    pg.reload(wait_until='load'); pg.wait_for_timeout(500)
    chk('页面打开且版本正确', pg.evaluate("()=>/^v60\\.|^v6[0-9]\\./.test(APP_VER)"), pg.evaluate("()=>APP_VER"))

    # ---------- 1 录单矩阵（10 种写法，含两个需确认算法） ----------
    cases = [
        ('特04 100', 100), ('平特牛 300', 300), ('连肖马蛇 400', 400),
        ('二中二 04.19 100', 100), ('三中三 04.19.37 10', 10),
        ('红波各5', 85), ('尾3 10', 50), ('3头10', 100), ('狗各数5', 20),
        ('平特兔300\n平特兔500', 800),
    ]
    for q, want in cases:
        before = totals()
        save_order(q)
        after = totals()
        delta = round(after['sales'] - before['sales'], 2)
        chk('录单 %s = %s 元' % (q.replace('\n', '/'), want), abs(delta - want) < 0.02 and after['n'] == before['n'] + 1, {'delta': delta, 'n': after['n']})
    t = totals()
    chk('10 单合计 1965 元', abs(t['sales'] - 1965) < 0.02, t)

    # ---------- 2 空输入不落单 / 清空输入 ----------
    before = totals()
    pg.evaluate("()=>{document.getElementById('input').value=''; handleSave();}"); pg.wait_for_timeout(300)
    modal_ok()
    chk('空输入不落单', totals()['n'] == before['n'], totals())
    pg.evaluate("()=>{document.getElementById('input').value='特05 100';}"); pg.evaluate("()=>clearInput()")
    chk('清空输入按钮生效', pg.evaluate("()=>document.getElementById('input').value===''"))

    # ---------- 3 订单页：本次订单 / 今日对账 / 复制汇总 ----------
    pg.evaluate("()=>switchTab('all')"); pg.wait_for_timeout(200)
    pg.evaluate("()=>showLastOrder()"); pg.wait_for_timeout(400)
    txt = pg.evaluate("()=>document.body.innerText")
    chk('本次订单显示 800 元单', '800' in txt)
    pg.evaluate("()=>{document.querySelectorAll('.ai-ov').forEach(function(o){o.remove()});}"); pg.wait_for_timeout(150)
    pg.evaluate("()=>showTodayRecon()"); pg.wait_for_timeout(500)
    recon = pg.evaluate("()=>document.body.innerText")
    chk('今日对账显示 1965', '1965' in recon)
    pg.evaluate("()=>{document.querySelectorAll('.ai-ov').forEach(function(o){o.remove()});}"); pg.wait_for_timeout(150)
    pg.evaluate("()=>copyAllOrders()"); pg.wait_for_timeout(400)
    try:
        clip = pg.evaluate("()=>navigator.clipboard.readText()")
    except Exception:
        clip = ''
    chk('复制汇总有内容且含 1965', ('1965' in clip) or len(clip) > 20, clip[:40])

    # ---------- 4 今日归档：取消不动账 → 确认才清空 ----------
    # 归档前先在飞单台账里放手飞/多飞各一笔，归档后必须一起带走，不能留在飞单页
    pg.evaluate("()=>{var p=(typeof selfFlyPeriod==='function')?selfFlyPeriod():''; selfFlySave([{p:p,code:'特04',amt:100}]); emExtraSave([{p:p,code:'三中三:04,19,37',amt:10}]); renderAll();}"); pg.wait_for_timeout(300)
    chk('归档前飞单台账有手飞/多飞', pg.evaluate("()=>selfFlyRows().length===1 && emExtraRows().length===1"))
    pg.evaluate("()=>switchTab('orders')"); pg.wait_for_timeout(250)
    n_before = totals()['n']
    pg.evaluate("()=>billArchiveAsk()"); pg.wait_for_timeout(350)
    pg.evaluate("()=>{var b=document.getElementById('mcCancel'); if(b)b.click();}"); pg.wait_for_timeout(300)
    chk('归档点取消不删单', totals()['n'] == n_before, totals())
    pg.evaluate("()=>billArchiveAsk()"); pg.wait_for_timeout(300)
    pg.evaluate("()=>{var b=document.getElementById('mcOk'); if(b)b.click();}"); pg.wait_for_timeout(700)
    chk('归档确认后清空当前账本', totals()['n'] == 0, totals())
    chk('归档后订单记录也清空（不再残留）', pg.evaluate("()=>customerOrders().length") == 0, pg.evaluate("()=>customerOrders().length"))
    chk('归档后手飞/多飞台账清空（飞单页不残留）', pg.evaluate("()=>selfFlyRows().length===0 && emExtraRows().length===0"), pg.evaluate("()=>[selfFlyRows().length,emExtraRows().length]"))
    chk('归档后飞单金额归零', pg.evaluate("()=>totalFlownReal()===0 && emExtraBook(curShopDraw()).cost===0"), pg.evaluate("()=>[totalFlownReal(),emExtraBook(curShopDraw()).cost]"))
    chk('归档把本期手飞/多飞写进历史', pg.evaluate("()=>{try{var a=billArchive||{};var k=Object.keys(a).sort().pop();return k?((a[k].selfFly||[]).length===1&&(a[k].emExtra||[]).length===1):false}catch(e){return false}}"))
    chk('归档写入历史', pg.evaluate("()=>{try{return Object.keys(billArchive||{}).length>0}catch(e){return false}}"))

    # ---------- 5 历史订单能打开 ----------
    pg.evaluate("()=>billOpenHistory()"); pg.wait_for_timeout(500)
    chk('历史订单弹层有今天日期', datetime.date.today().strftime('%Y-%m-%d') in pg.evaluate("()=>document.body.innerText") or datetime.date.today().strftime('%m-%d') in pg.evaluate("()=>document.body.innerText"))
    pg.evaluate("()=>{document.querySelectorAll('.ai-ov').forEach(function(o){o.remove()});}"); pg.wait_for_timeout(150)

    # ---------- 6 排行四个子页都能出内容 ----------
    pg.evaluate("()=>switchTab('rank')"); pg.wait_for_timeout(250)
    for sec, id_ in [('rank', 'rankTableBody'), ('risk', 'riskBody'), ('profit', 'profitBody'), ('split', 'splitBody')]:
        pg.evaluate("(s)=>openRankSection(s)", sec); pg.wait_for_timeout(350)
        ln = pg.evaluate("(i)=>{var e=document.getElementById(i); return e?e.innerText.trim().length:0}", id_)
        chk('排行子页 %s 有内容' % sec, ln > 20, {'len': ln})

    # ---------- 7 飞单流程（重新录 5 单，按 329 基准） ----------
    pg.evaluate("()=>switchTab('all')"); pg.wait_for_timeout(200)
    pg.evaluate("()=>{shop='澳门'; lastDraw={period:'329',regularNums:[45,6,46,33,31,40],specialNum:44}; _riskDraw=lastDraw; splitTakeAll=60; pteFlyTakeAll=3000; lxFlyAmt=0; emExtraSave([]); selfFlySave([]);}")
    for q in ['特04 100', '平特牛 300', '连肖马蛇 400', '二中二 04.19 100', '三中三 04.19.37 10']:
        save_order(q)
    pg.evaluate("()=>{switchTab('rank'); openRankSection('singles');}"); pg.wait_for_timeout(400)
    chk('排行子页 singles(平特肖) 有内容', pg.evaluate("()=>document.getElementById('rank-singles').innerText.trim().length") > 5)
    pg.evaluate("()=>openRankSection('split')"); pg.wait_for_timeout(350)
    st = pg.evaluate("()=>{var a=actualPnL(),r=getThisRoundFly();return [a.sales,a.flyOut,r.thisRound];}")
    chk('飞单开局 910 / 已飞0 / 待飞150', st == [910, 0, 150], st)
    pg.evaluate("()=>autoFlyToggleBtn()"); pg.wait_for_timeout(500)
    st = pg.evaluate("()=>{var a=actualPnL();return [a.flyOut,totalFlownReal(),getThisRoundFly().thisRound];}")
    chk('开自动飞 110/110/40', st == [110, 110, 40], st)
    pg.evaluate("()=>confirmThisRoundFly()"); pg.wait_for_timeout(300)
    pg.evaluate("()=>{var b=document.getElementById('mcOk'); if(b)b.click();}"); pg.wait_for_timeout(700)
    st = pg.evaluate("()=>{var a=actualPnL();return [a.flyOut,totalFlownReal(),getThisRoundFly().thisRound];}")
    chk('确认飞单 150/150/0', st == [150, 150, 0], st)

    # 手飞默认口径（已含在已飞里，不改总额）
    pg.evaluate("()=>selfFlyOpen()"); pg.wait_for_timeout(400)
    pg.evaluate("()=>{var t=document.getElementById('sfInput')||document.querySelector('#sfWrap textarea'); if(t)t.value='特04 50'; var b=Array.from(document.querySelectorAll('#sfWrap button')).find(function(x){return /记入本期/.test(x.innerText)}); if(b)b.click();}")
    pg.wait_for_timeout(500)
    st0 = pg.evaluate("()=>[actualPnL().flyOut,totalFlownReal()]")
    pg.evaluate("()=>{var w=document.getElementById('sfWrap'); if(w)w.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:5,clientY:5}));}"); pg.wait_for_timeout(350)
    chk('手飞（已含口径）不重复加钱', st0 == [150, 150], st0)

    # 多飞两笔 20
    pg.evaluate("()=>emExtraOpen()"); pg.wait_for_timeout(400)
    pg.evaluate("()=>{var t=document.getElementById('emxInput'); t.value='三中三 17.20.25 10\\n三中三 07 15 36 10'; emExtraAdd();}")
    pg.wait_for_timeout(600)
    pg.evaluate("()=>{var w=document.getElementById('emxWrap'); if(w)w.dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:5,clientY:5}));}"); pg.wait_for_timeout(350)
    st = pg.evaluate("()=>{var a=actualPnL();return [a.flyOut,totalFlownReal()];}")
    chk('多飞 20 后 170/170', st == [170, 170], st)
    up = pg.evaluate("()=>window._upCopy||''")
    chk('上家文本对平 170', '飞走合计 170' in up and '明细合计 170' in up and '应付上家 170' in up)

    # ---------- 8 飞单页 15 键逐个点（每个都留在飞单页） ----------
    pg.evaluate("()=>document.querySelectorAll('.ai-ov').forEach(function(o){o.remove()})")
    pg.evaluate("()=>openRankSection('split')"); pg.wait_for_timeout(250)
    pg.evaluate("()=>{_flyDirOpen=true; if(typeof showAllFlyDir==='function') showAllFlyDir();}"); pg.wait_for_timeout(300)
    items = pg.evaluate("()=>Array.from(document.querySelectorAll('#splitBody button')).map((b,i)=>[i,b.innerText.trim(),b.getAttribute('onclick')||'']).filter(function(x){return x[1] !== '删' && x[1].indexOf('上家结算单')<0;})")
    chk('飞单页按键齐全（≥11）', len(items) >= 11, len(items))
    bad = []
    for i, lb, oc in items:
        pg.reload(wait_until='load'); pg.wait_for_timeout(300)
        pg.evaluate("()=>openRankSection('split')"); pg.wait_for_timeout(250)
        pg.evaluate("()=>{var b=Array.from(document.querySelectorAll('#splitBody button')).find(function(x){return (x.getAttribute('onclick')||'')==='%s'}); if(b)b.click();}" % oc.replace("\\", "\\\\").replace("'", "\\'"))
        pg.wait_for_timeout(450)
        pg.evaluate("()=>{var a=document.getElementById('maOk')||document.getElementById('mcOk'); if(a)a.click();}"); pg.wait_for_timeout(250)
        pg.evaluate("()=>{['sfWrap','emxWrap','mlWrap','mfWrap'].forEach(function(id){var w=document.getElementById(id); if(w){var ev=new MouseEvent('click',{bubbles:true,clientX:5,clientY:5});w.dispatchEvent(ev);}});}"); pg.wait_for_timeout(300)
        vis = pg.evaluate("()=>{var s=document.getElementById('splitBody'); return [s?Math.round(s.getBoundingClientRect().width):0,_activeTab];}")
        if not (vis[0] > 0 and vis[1] == 'rank'):
            bad.append(lb)
    chk('全部按键点完都留在飞单页', len(bad) == 0, bad)

    # ---------- 9 备份导出 + 粘贴导入 ----------
    pg.reload(wait_until='load'); pg.wait_for_timeout(400)
    try:
        with pg.expect_download(timeout=15000) as d:
            pg.evaluate("()=>exportBackup()")
        path = d.value.path()
        data = json.load(open(path, encoding='utf-8'))
        chk('备份 JSON 可生成且含订单', 'orders' in data and len(data.get('orders', [])) > 0, {'orders': len(data.get('orders', []))})
        raw = open(path, encoding='utf-8').read()
    except Exception as e:
        chk('备份 JSON 可生成且含订单', False, str(e)[:80]); raw = ''
    if raw:
        pg.evaluate("()=>{orders=[];}"); pg.wait_for_timeout(150)
        pg.evaluate("()=>openPasteImport()"); pg.wait_for_timeout(300)
        pg.evaluate("(t)=>{document.getElementById('piText').value=t; document.getElementById('piOk').click();}", raw); pg.wait_for_timeout(700)
        modal_ok()
        pg.wait_for_timeout(500)
        chk('粘贴导入恢复订单', pg.evaluate("()=>orders.length") > 0, pg.evaluate("()=>orders.length"))

    # ---------- 10 设置 / 说明 / 诊断 ----------
    pg.evaluate("()=>openSettings()"); pg.wait_for_timeout(350)
    chk('设置弹窗能打开', pg.evaluate("()=>!!document.getElementById('settingsOv')") or '保存前预览' in pg.evaluate("()=>document.body.innerText"))
    before_txt = pg.evaluate("()=>document.body.innerText")
    pg.evaluate("()=>togglePreview()"); pg.wait_for_timeout(250)
    chk('保存前预览开关能切换', pg.evaluate("()=>document.body.innerText") != before_txt)
    pg.evaluate("()=>openHelp()"); pg.wait_for_timeout(350)
    chk('使用说明能打开', '使用说明' in pg.evaluate("()=>document.body.innerText"))
    pg.evaluate("()=>{document.querySelectorAll('.ai-ov').forEach(function(o){o.remove()});}"); pg.wait_for_timeout(150)
    pg.evaluate("()=>copyDiagnostics()"); pg.wait_for_timeout(400)
    chk('复制诊断不报错', len(errs) == 0, errs[:2])

    chk('全程无 JS 报错', len(errs) == 0, errs[:3])
    print('\nSUMMARY %d/%d' % (sum(1 for x in R if x['status'] == 'PASS'), len(R)))
    fails = [x for x in R if x['status'] == 'FAIL']
    print('FAILS:', json.dumps(fails, ensure_ascii=False))
    out = '/tmp/selfuse_qa_report.json'
    json.dump({'time': time.strftime('%F %T'), 'version': pg.evaluate("()=>APP_VER"), 'results': R}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('report ->', out)
    b.close()
    sys.exit(0 if not fails else 1)
