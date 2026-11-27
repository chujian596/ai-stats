#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""客户版 v59.77：一套账（客户账 / 上家账 / 我的账）逐项断言。

覆盖：
1) 未开奖：三层账全部“待开奖”，不拿 0 冒充结果
2) 已开奖无飞：客户账=收-赔，上家账=0，我的账=客户账
3) 有飞有返水：上家账=赔回-已飞，我的账=客户账+上家账，含返水另加
4) 今日对账、盈亏统计、复制账单、CSV 四个出口同数、同标签
5) 旧口径“飞后净盈亏 / 上家结算 / 毛净盈亏”不再作为大数出现
"""
import os
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

FAIL = []
def chk(name, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + name + (('  ' + str(detail)) if detail else ''))
    if not cond:
        FAIL.append(name)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

httpd = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=ROOT))
threading.Thread(target=httpd.serve_forever, daemon=True).start()
URL = 'http://127.0.0.1:%d/app.html?nock=1&t=clienttb' % httpd.server_address[1]
SETUP = """() => {
  localStorage.clear();
  localStorage.setItem('rebateOn','1');
  localStorage.setItem('rebateRate','0.03');
  shop = 'A';
  payMult = 47;
  payMultSingle = 2;
  lastDraw = { period:'332', regularNums:[1,2,3,4,5,6], specialNum:10 };
  orders = [
    { id:'t1', customer:'甲', amount:100, price:100, codes:['10'], codeAmts:{'10':100}, createdAt:'2026-11-27 15:50' },
    { id:'t2', customer:'乙', amount:100, price:100, codes:['20'], codeAmts:{'20':100}, createdAt:'2026-11-27 15:50' }
  ];
  hkOrders = [];
  return true;
}"""

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/local/bin/chromium', args=['--no-sandbox'])
    pg = b.new_page(viewport={'width':420,'height':900})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until='load'); pg.wait_for_timeout(500)
    pg.evaluate(SETUP)

    # 基线：真实订单 + 真实赔付，无飞
    base = pg.evaluate("""() => {
      const tb = clientThreeBooks();
      return {sales:tb.sales,payout:tb.payout,flyOut:tb.flyOut,flyBack:tb.flyBack,
              customerNet:tb.customerNet,upNet:tb.upNet,myNet:tb.myNet,
              rebate:tb.rebate,withRebate:tb.withRebate,settled:tb.settled};
    }""")
    chk('无飞：收单 200', base['sales'] == 200, base)
    chk('无飞：客户赔付 4700', base['payout'] == 4700, base)
    chk('无飞：客户账 = 200-4700 = -4500', base['customerNet'] == -4500, base)
    chk('无飞：上家账 = 0', base['upNet'] == 0, base)
    chk('无飞：我的账 = 客户账 + 上家账 = -4500', base['myNet'] == -4500, base)

    # 今日对账：一套账标签与数值
    pg.evaluate("() => { showTodayRecon(); }")
    pg.wait_for_timeout(200)
    txt = pg.locator('.ai-ov').inner_text()
    chk('今日对账有「一套账」', '一套账' in txt, txt[:80])
    chk('今日对账有三层标签', all(x in txt for x in ['客户账','上家账','我的账']), txt[:120])
    chk('今日对账客户账 -4500.00', '-4500.00' in txt, txt[:160])
    chk('今日对账不再显示飞后净盈亏', '飞后净盈亏' not in txt)
    chk('今日对账不再显示上家结算', '上家结算' not in txt)
    chk('今日对账不再显示毛净盈亏', '毛净盈亏' not in txt)
    pg.evaluate("() => { document.querySelectorAll('.ai-ov').forEach(x=>x.remove()); }")

    # 有飞有返水：给 actualPnL 注入固定飞额/赔回，验证三层公式
    inject = pg.evaluate("""() => {
      const orig = actualPnL;
      window.actualPnL = function(){
        const r = orig();
        return Object.assign({}, r, {
          settled:true, flyOut:200, flyBack:100, rebate:6, rebateOn:true, rebateRate:0.03,
          net: r.sales - r.payout - 200 + 100,
          netWithRebate: r.sales - r.payout - 200 + 100 + 6
        });
      };
      const tb = clientThreeBooks();
      return {customerNet:tb.customerNet,upNet:tb.upNet,myNet:tb.myNet,withRebate:tb.withRebate,
              rebate:tb.rebate,flyOut:tb.flyOut,flyBack:tb.flyBack};
    }""")
    chk('有飞：上家账 = 100-200 = -100', inject['upNet'] == -100, inject)
    chk('有飞：我的账 = -4500 + -100 = -4600', inject['myNet'] == -4600, inject)
    chk('有飞：含返水 = -4600 + 6 = -4594', inject['withRebate'] == -4594, inject)
    chk('有飞：返水另加不混进三层', inject['myNet'] == -4600 and inject['rebate'] == 6, inject)

    # 今日对账注入后：四本账自检也必须用纯上家账，不能把返水混进去
    pg.evaluate("() => { showTodayRecon(); }")
    pg.wait_for_timeout(200)
    txt2 = pg.locator('.ai-ov').inner_text()
    chk('有飞今日对账上家账 -100.00', '-100.00' in txt2, txt2[:160])
    chk('有飞今日对账我的账 -4600.00', '-4600.00' in txt2, txt2[:160])
    chk('有飞今日对账含返水 -4594.00', '-4594.00' in txt2, txt2[:200])
    pg.evaluate("() => { document.querySelectorAll('.ai-ov').forEach(x=>x.remove()); }")

    # 盈亏统计页
    pg.evaluate("() => { renderPaySide(); }")
    pg.wait_for_timeout(200)
    profit = pg.evaluate("() => (document.getElementById('profitBody')||{}).innerText || ''")
    chk('盈亏统计有三层标签', all(x in profit for x in ['客户账','上家账','我的账']), profit[:160])
    chk('盈亏统计我的账 -4600', '-4600' in profit, profit[:200])
    chk('盈亏统计不再显示毛净/上家需结算/实际盈亏', all(x not in profit for x in ['毛净','上家需结算','实际盈亏']), profit[:200])

    # 复制账单
    copied = pg.evaluate("""() => {
      window.__copied = '';
      Object.defineProperty(navigator, 'clipboard', { configurable:true, value:{ writeText:(t)=>{ window.__copied = t; return Promise.resolve(); } } });
      copyProfit();
      return window.__copied;
    }""")
    chk('复制账单有三层', all(x in copied for x in ['客户账：','上家账：','我的账：']), copied[:120])
    chk('复制账单我的账 -4600', '-4600' in copied, copied[:160])
    chk('复制账单不含飞后净/上家结算', all(x not in copied for x in ['飞后净盈亏','上家结算']), copied[:200])

    # CSV
    csv = pg.evaluate("""() => {
      window.__csv = null;
      window.download = function(name, content){ window.__csv = content; };
      exportTodayReconCSV();
      return window.__csv || '';
    }""")
    chk('CSV 有三层账行', all(x in csv for x in ['"客户账",','"上家账",','"我的账",']), csv[:300])
    chk('CSV 我的账 -4600', '-4600' in csv, csv[:400])
    chk('CSV 不含飞后净/上家结算/毛净', all(x not in csv for x in ['飞后净盈亏','上家结算','毛净盈亏']), csv[:400])

    # 未开奖：不拿 0 冒充
    pg.evaluate("() => { window.actualPnL = null; lastDraw = null; }")
    # 还原真实函数太麻烦，重新开页更稳
    pg.goto(URL + '&pending=1', wait_until='load'); pg.wait_for_timeout(400)
    pg.evaluate(SETUP)
    pg.evaluate("() => { lastDraw = null; }")
    pending = pg.evaluate("""() => {
      const tb = clientThreeBooks();
      return {customerNet:tb.customerNet,upNet:tb.upNet,myNet:tb.myNet,withRebate:tb.withRebate,payout:tb.payout,flyBack:tb.flyBack};
    }""")
    chk('未开奖：客户账待开奖', pending['customerNet'] is None, pending)
    chk('未开奖：上家账待开奖', pending['upNet'] is None, pending)
    chk('未开奖：我的账待开奖', pending['myNet'] is None, pending)
    chk('未开奖：含返水待开奖', pending['withRebate'] is None, pending)
    pg.evaluate("() => { showTodayRecon(); }")
    pg.wait_for_timeout(200)
    txt3 = pg.locator('.ai-ov').inner_text()
    chk('未开奖今日对账显示待开奖', '待开奖' in txt3, txt3[:120])
    chk('未开奖不显示 0.00 冒充我的账', '我的账\n+0.00' not in txt3, txt3[:200])

    chk('客户版无 JS 报错', not errs, errs[:3])
    print('\nSUMMARY %d/%d' % (34 - len(FAIL), 34))
    b.close()
httpd.shutdown()
sys.exit(1 if FAIL else 0)
