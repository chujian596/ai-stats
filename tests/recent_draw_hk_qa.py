"""香港店首页「最近开奖」：只显示香港历史，不串澳门库，特码无光圈。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':430,'height':900}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=rdhk',wait_until='load')
    pg.evaluate("()=>{localStorage.setItem('current_shop','B');location.reload();}")
    pg.wait_for_timeout(800)
    chk('切到香港店',pg.locator('body').inner_text().find('香港')>=0)
    pg.click('#recentDrawToggle'); pg.wait_for_timeout(1200)
    chk('香港默认展示10期',pg.locator('.rd-row').count()==10,pg.locator('.rd-row').count())
    meta=pg.locator('#recentDrawMeta').inner_text()
    chk('香港历史库124期','124' in meta,meta)
    chk('香港库不是澳门328/330','328' not in meta and '330' not in meta,meta)
    head=pg.locator('.rd-head').inner_text()
    chk('标题写香港', '香港' in head, head[:20])
    chk('不再提示未接入','未接入' not in pg.locator('#recentDrawPanel').inner_text())
    first=pg.locator('.rd-row').first.inner_text()
    chk('香港最新124期','124期' in first,first[:30])
    chk('124特码36带生肖羊','36' in first and '羊' in first,first[-12:])
    sh=pg.evaluate("getComputedStyle(document.querySelector('.rd-sp')).boxShadow")
    chk('香港特码没有金色光圈','251, 191, 36' not in sh and '2px' not in sh,sh)
    pg.click('text=30期'); pg.wait_for_timeout(300)
    chk('香港切30期仍最多124条',pg.locator('.rd-row').count()==30,pg.locator('.rd-row').count())
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('FAILS',len(FAIL)); sys.exit(1 if FAIL else 0)
