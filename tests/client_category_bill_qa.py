#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""客户版 v59.78：分类账单 + 飞单缺口只读视图逐项断言。

覆盖：
1) 分类账单按玩法拆收单/赔付/应飞/已飞/上家赔回/三层账
2) 分类合计与一套账一致，未纳入飞单 = 总单 - 应飞
3) 同一订单内重复号码只计一次，不重复计金额
4) 今日对账、盈亏统计、复制账单、CSV 四个出口都有分类账单
5) 开奖后分类账与 clientThreeBooks 同数
"""
import os
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

FAIL = []
PASSED = 0
def chk(name, cond, detail=''):
    global PASSED
    print(('PASS ' if cond else 'FAIL ') + name + (('  ' + str(detail)) if detail else ''))
    if cond:
        PASSED += 1
    else:
        FAIL.append(name)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

httpd = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=ROOT))
threading.Thread(target=httpd.serve_forever, daemon=True).start()
URL = 'http://127.0.0.1:%d/app.html?nock=1&t=clientcat' % httpd.server_address[1]

BATCH = '''03 10 05 各140
07 11 13 各160
平特马220
平特龙230
平特兔240
虎平260
连肖龙虎兔270
连肖马鸡310
平连龙虎290
三四连肖虎马龙兔300
二中二:03,10 320
三中二:03,07,11 350
三中三:07,24,32 360
特码:17 190
平特蛇250'''

DUP = '''03 10 05 各140
03 10 05 各150'''

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/local/bin/chromium', args=['--no-sandbox'])
    pg = b.new_page(viewport={'width':420,'height':900})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until='load'); pg.wait_for_timeout(500)
    pg.evaluate("""() => {
      localStorage.clear();
      localStorage.setItem('ai_preview_enabled','0');
      shop = 'A';
      payMult = 47;
      payMultSingle = 2;
      window.myConfirm = (m, cb) => { if(cb) cb(); };
      window.myAlert = (m) => { window.__alerts = (window.__alerts||[]).concat([String(m)]); };
      orders = []; hkOrders = []; flownPerPos = {}; flownReal = {};
      lastDraw = null;
    }""")

    # 重复号码：同一单里 03/10/05 两行，金额不同，分类必须只算一次合并额
    pg.evaluate("(t) => doSave(t)", DUP); pg.wait_for_timeout(600)
    dup = pg.evaluate("""() => {
      const d = todayReconData();
      const tb = clientThreeBooks();
      const c = billCategoryData(d, tb);
      return {total:c.total.sales, spec:c.rows['特号'].sales, orderOk:d.orderOk,
              catOk:c.ok, codes:orders[0].codes.length, codeAmts:orders[0].codeAmts};
    }""")
    chk('重复号码：单笔合计 870', dup['total'] == 870, dup)
    chk('重复号码：特号分类只算 870', dup['spec'] == 870, dup)
    chk('重复号码：订单明细仍对平', dup['orderOk'] is True, dup)
    chk('重复号码：分类合计与一套账一致', dup['catOk'] is True, dup)

    # 主样本：15 种玩法、4490 元、19 项
    pg.evaluate("""() => { orders=[]; hkOrders=[]; flownPerPos={}; flownReal={}; lastDraw=null; window.__alerts=[]; }""")
    pg.evaluate("(t) => doSave(t)", BATCH); pg.wait_for_timeout(900)
    pre = pg.evaluate("""() => {
      const d = todayReconData();
      const tb = clientThreeBooks();
      const c = billCategoryData(d, tb);
      return {d:{sales:d.sales,detail:d.detail,payout:d.payout,flyCalc:d.flyCalc,specFull:d.specFull,pteFull:d.pteFull,lxFull:d.lxFull,emFull:d.emFull,orderOk:d.orderOk,flyOk:d.flyOk},
              tb:{sales:tb.sales,payout:tb.payout,flyOut:tb.flyOut,flyBack:tb.flyBack,customerNet:tb.customerNet,upNet:tb.upNet,myNet:tb.myNet,settled:tb.settled},
              cat:{ok:c.ok,diffs:c.diffs,total:c.total,rows:Object.fromEntries(Object.keys(c.rows).map(k=>[k,c.rows[k]]))}};
    }""")
    chk('主样本：总收单 4490', pre['d']['sales'] == 4490, pre['d'])
    chk('主样本：订单明细对平', pre['d']['orderOk'] is True, pre['d'])
    chk('主样本：飞单表对平', pre['d']['flyOk'] is True, pre['d'])
    chk('主样本：分类特号收单 1090', pre['cat']['rows']['特号']['sales'] == 1090, pre['cat']['rows']['特号'])
    chk('主样本：分类平特收单 1200', pre['cat']['rows']['平特']['sales'] == 1200, pre['cat']['rows']['平特'])
    chk('主样本：分类连肖收单 1170', pre['cat']['rows']['连肖']['sales'] == 1170, pre['cat']['rows']['连肖'])
    chk('主样本：分类二三中三收单 1030', pre['cat']['rows']['二三中三']['sales'] == 1030, pre['cat']['rows']['二三中三'])
    chk('主样本：分类收单合计 4490', pre['cat']['total']['sales'] == 4490, pre['cat']['total'])
    chk('主样本：未纳入飞单 1870', pre['cat']['total']['gap'] == 1870, pre['cat']['total'])
    chk('主样本：特号未飞 700', pre['cat']['rows']['特号']['gap'] == 700, pre['cat']['rows']['特号'])
    chk('主样本：连肖未飞 1170', pre['cat']['rows']['连肖']['gap'] == 1170, pre['cat']['rows']['连肖'])
    chk('主样本：分类合计与一套账一致', pre['cat']['ok'] is True, pre['cat']['diffs'])

    # 今日对账 UI
    pg.evaluate("() => showTodayRecon()"); pg.wait_for_timeout(250)
    txt = pg.locator('.ai-ov').inner_text()
    chk('今日对账有分类账单', '分类账单' in txt, txt[:80])
    chk('今日对账有未纳入飞单', '未纳入飞单' in txt, txt[:120])
    chk('今日对账显示缺口 1870', '1870' in txt, txt[:180])
    chk('今日对账有分类合计一致', '分类合计与一套账一致' in txt, txt[:180])
    pg.evaluate("() => document.querySelectorAll('.ai-ov').forEach(x=>x.remove())")

    # 盈亏统计：compact 分类表
    pg.evaluate("() => renderPaySide()"); pg.wait_for_timeout(250)
    profit = pg.evaluate("() => (document.getElementById('profitBody')||{}).innerText || ''")
    chk('盈亏统计有分类账单', '分类账单' in profit, profit[:160])
    chk('盈亏统计有未纳入飞单', '未纳入飞单' in profit, profit[:200])

    # 复制账单：分类账单文本
    pg.evaluate("""() => {
      window.__copied = '';
      try { Object.defineProperty(navigator, 'clipboard', {value:{writeText:(t)=>{window.__copied=t; return Promise.resolve();}}, configurable:true}); } catch(e){}
      copyProfit();
    }"""); pg.wait_for_timeout(250)
    copied = pg.evaluate("() => window.__copied || ''")
    chk('复制账单有分类账单', '分类账单' in copied, copied[:120])
    chk('复制账单有未纳入飞单', '未纳入飞单' in copied, copied[-160:])

    # 开奖后：分类赔付/三层账与 clientThreeBooks 同数
    pg.evaluate("""() => { lastDraw = {period:'333', regularNums:[3,7,9,12,22,33], specialNum:44}; }""")
    pg.wait_for_timeout(200)
    post = pg.evaluate("""() => {
      const d = todayReconData();
      const tb = clientThreeBooks();
      const c = billCategoryData(d, tb);
      return {tb:{sales:tb.sales,payout:tb.payout,flyOut:tb.flyOut,flyBack:tb.flyBack,customerNet:tb.customerNet,upNet:tb.upNet,myNet:tb.myNet,settled:tb.settled},
              cat:{ok:c.ok,diffs:c.diffs,total:c.total,rows:Object.fromEntries(Object.keys(c.rows).map(k=>[k,c.rows[k]]))},d:{payout:d.payout}};
    }""")
    chk('开奖后：客户赔付 7460', post['tb']['payout'] == 7460, post['tb'])
    chk('开奖后：分类赔付合计 7460', post['cat']['total']['payout'] == 7460, post['cat']['total'])
    chk('开奖后：客户账 -2970', post['tb']['customerNet'] == -2970, post['tb'])
    chk('开奖后：分类客户账合计 -2970', post['cat']['total']['customerNet'] == -2970, post['cat']['total'])
    chk('开奖后：我的账 -2970', post['tb']['myNet'] == -2970, post['tb'])
    chk('开奖后：分类我的账合计 -2970', post['cat']['total']['myNet'] == -2970, post['cat']['total'])
    chk('开奖后：分类合计与一套账一致', post['cat']['ok'] is True, post['cat']['diffs'])
    pg.evaluate("() => showTodayRecon()"); pg.wait_for_timeout(250)
    txt2 = pg.locator('.ai-ov').inner_text()
    chk('开奖后今日对账有分类账单', '分类账单' in txt2, txt2[:80])
    chk('开奖后今日对账分类对平', '分类合计与一套账一致' in txt2, txt2[:180])
    pg.evaluate("() => document.querySelectorAll('.ai-ov').forEach(x=>x.remove())")

    # CSV 有分类块
    pg.evaluate("""() => {
      window.__csv = '';
      window.download = function(name, content, type){ window.__csv = String(content||''); };
      exportTodayReconCSV();
    }"""); pg.wait_for_timeout(200)
    csv = pg.evaluate("() => window.__csv || ''")
    chk('CSV 有分类账单', '分类账单' in csv, csv[:80])
    chk('CSV 有未纳入飞单', '未纳入飞单' in csv, csv[-200:])
    chk('CSV 有分类合计', '合计' in csv and '特号' in csv and '平特' in csv, csv[:200])

    chk('全程无 JS 报错', len(errs) == 0, errs[:3])
    b.close()

print('SUMMARY %d/%d' % (PASSED, PASSED + len(FAIL)))
if FAIL:
    print('FAILED:', FAIL)
    sys.exit(1)
