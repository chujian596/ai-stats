"""首页订单输入区「最近开奖」10/30 期：能开、能切、最新一期优先、无 JS 错。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':430,'height':900}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=rdqa',wait_until='load'); pg.wait_for_timeout(400)
    chk('首页有「最近开奖」入口', pg.locator('#recentDrawToggle').count()==1)
    pg.click('#recentDrawToggle'); pg.wait_for_timeout(900)
    chk('默认展示10期', pg.locator('.rd-row').count()==10, pg.locator('.rd-row').count())
    first=pg.locator('.rd-row').first.inner_text()
    chk('最新一期是330期','330期' in first, first[:40])
    chk('330平码25 35 20 08 30 22',all(x in first for x in ['25','35','20','08','30','22']),first)
    chk('330特码26带生肖蛇','26' in first and '蛇' in first,first[-10:])
    pg.click("text=30期"); pg.wait_for_timeout(300)
    chk('切到30期',pg.locator('.rd-row').count()==30,pg.locator('.rd-row').count())
    # 新一期只在本机：331 应排最前，且不重复 330
    pg.evaluate("""()=>{lastDraw={specialNum:12,regularNums:[1,2,3,4,5,6],period:331};saveLastDraw();}""")
    pg.wait_for_timeout(300)
    rows=pg.locator('.rd-row').count()
    first2=pg.locator('.rd-row').first.inner_text()
    chk('本机新一期331排最前','331期' in first2 and '12' in first2,first2)
    chk('331不挤掉总数',rows==30,rows)
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('FAILS',len(FAIL)); sys.exit(1 if FAIL else 0)
