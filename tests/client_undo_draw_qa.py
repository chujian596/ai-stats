#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""客户版 v59.79：撤销开奖记录在香港无缓存时的空指针回归。

现象：只有澳门开奖、香港开奖缓存为 null 时，点“撤销”报
Cannot read properties of null (reading 'nums')，位置 clearDrawRecordAll。
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
URL = 'http://127.0.0.1:%d/app.html?nock=1&t=undoqa' % httpd.server_address[1]

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/local/bin/chromium', args=['--no-sandbox'])
    pg = b.new_page(viewport={'width':420,'height':900})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until='load'); pg.wait_for_timeout(450)

    # 澳门有开奖、香港缓存为 null：旧代码在拼确认文案时读 hkc.nums 抛空指针
    pg.evaluate("""() => {
      localStorage.clear();
      localStorage.setItem('lastDraw_shopA', JSON.stringify({draw:330, specialNum:26, regularNums:[25,35,20,8,30,22]}));
      localStorage.removeItem('hk_draw_cache_global');
      localStorage.removeItem('hk_draw_cache_shopA');
      window.__confirmMsg = '';
      window.myConfirm = (m, cb) => { window.__confirmMsg = m; if(cb) cb(); };
      window.myAlert = (m) => { window.__alert = m; };
    }""")
    r = pg.evaluate("() => { try{ clearDrawRecordAll(); return 'ok'; } catch(e){ return 'ERR:' + e.message; } }")
    chk('澳门只开奖、香港无缓存：点撤销不抛错', r == 'ok', r)
    chk('澳门只开奖：仍弹出一期确认', '撤销这一期开奖记录' in pg.evaluate("() => window.__confirmMsg || ''"), pg.evaluate("() => window.__confirmMsg || ''")[:120])
    chk('澳门只开奖：确认文案带澳门期号/特号', '期330' in pg.evaluate("() => window.__confirmMsg || ''") and '特26' in pg.evaluate("() => window.__confirmMsg || ''"), pg.evaluate("() => window.__confirmMsg || ''")[:160])
    chk('撤销后无 JS 报错', len(errs) == 0, errs[:3])

    # 完全无开奖：应提示“当前没有开奖记录”，也不能抛空指针
    pg.evaluate("""() => {
      lastDraw = null;
      try{ localStorage.removeItem('lastDraw_shopA'); }catch(e){}
      try{ localStorage.removeItem('hk_draw_cache_global'); }catch(e){}
      window.__confirmMsg = ''; window.__alert = ''; errs = [];
    }""")
    r2 = pg.evaluate("() => { try{ clearDrawRecordAll(); return 'ok'; } catch(e){ return 'ERR:' + e.message; } }")
    chk('无开奖：点撤销不抛错', r2 == 'ok', r2)
    chk('无开奖：提示当前没有开奖记录', '当前没有开奖记录' in pg.evaluate("() => window.__alert || ''"), pg.evaluate("() => window.__alert || ''"))
    chk('无开奖：无 JS 报错', len(errs) == 0, errs[:3])

    b.close()

httpd.shutdown()
print('SUMMARY %d/%d' % (PASSED, PASSED + len(FAIL)))
if FAIL:
    print('FAILED:', FAIL)
    sys.exit(1)
