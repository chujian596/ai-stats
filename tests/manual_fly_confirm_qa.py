import json, sys
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8765/app-pro.html?nock=1'
CHECKS = []
def ok(name, cond, extra=''):
    CHECKS.append((name, bool(cond), extra))
    print(('PASS ' if cond else 'FAIL ') + name + (('  ' + str(extra)) if extra else ''))

def reset(pg):
    pg.evaluate("""()=>{
      ['flownPerPos','flownReal','manualLastBatch','manualFlyHistory'].forEach(k=>localStorage.removeItem(sk(k)));
      flownPerPos={}; flownReal={}; manualFlyClose();
    }""")

def start(pg):
    pg.evaluate("()=>manualFlyOpen()")
    pg.wait_for_timeout(150)

def set_text(pg, txt):
    pg.evaluate("""(t)=>{var el=document.getElementById('manualFlyInput');el.value=t;window._manualFlyBuf=t;}""", txt)

def click_ok(pg):
    pg.evaluate("""()=>{var o=Array.from(document.querySelectorAll('.ai-ov')).pop();var b=o?Array.from(o.querySelectorAll('button')).find(x=>x.innerText.trim()==='确定'):null;if(b)b.click();}""")
    pg.wait_for_timeout(250)

def click_cancel(pg):
    pg.evaluate("""()=>{var o=Array.from(document.querySelectorAll('.ai-ov')).pop();var b=o?Array.from(o.querySelectorAll('button')).find(x=>x.innerText.trim()==='取消'):null;if(b)b.click();}""")
    pg.wait_for_timeout(150)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/local/bin/chromium', args=['--no-sandbox'])
    pg = b.new_page(viewport={'width': 760, 'height': 1000})
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.goto(BASE, wait_until='load'); pg.wait_for_timeout(300)
    reset(pg); start(pg)

    # 1. 预览按输入行分组，不落账
    set_text(pg, '平马猪100\n平马猪羊100')
    pg.evaluate("()=>applyManualFlyList()"); pg.wait_for_timeout(150)
    preview = pg.evaluate("()=>{var o=Array.from(document.querySelectorAll('.ai-ov')).pop();return o?o.innerText:''}")
    ok('预览显示两行原文', '平马猪100' in preview and '平马猪羊100' in preview, preview)
    ok('预览显示按行分摊', '平特马 50' in preview and '平特羊 33' in preview, preview)
    ok('预览合计200', '合计 200 元' in preview, preview)
    ok('预览阶段未落账', pg.evaluate("()=>Object.keys(flownPerPos).length===0"))
    click_cancel(pg)
    ok('取消后未落账', pg.evaluate("()=>Object.keys(flownPerPos).length===0"))

    # 2. 确认后落账，历史可查可撤
    set_text(pg, '平马猪100\n平马猪羊100')
    pg.evaluate("()=>applyManualFlyList()"); pg.wait_for_timeout(150); click_ok(pg)
    ok('确认后落账', pg.evaluate("()=>Number(flownPerPos['平特马']||0)>0 && Number(flownPerPos['平特羊']||0)>0"))
    alert2 = pg.evaluate("()=>{var o=Array.from(document.querySelectorAll('.ai-ov')).pop();return o?o.innerText:''}")
    ok('成功明细带输入原文', '平马猪100' in alert2 and '平特马' in alert2, alert2)
    pg.evaluate("()=>{Array.from(document.querySelectorAll('.ai-ov')).forEach(o=>o.remove());manualFlyClose();manualFlyOpen();}")
    pg.wait_for_timeout(150)
    sheet = pg.evaluate("()=>{var w=document.getElementById('mfWrap');return w?w.innerText:''}")
    ok('手动登记记录可见', '手动登记记录' in sheet and '5笔/200元' in sheet, sheet)
    dirhtml = pg.evaluate("()=>manualFlyDirHtml()")
    ok('飞单页额外目录显示手动批次', '手动' in dirhtml and '平马猪100' in dirhtml and '200 元' in dirhtml, dirhtml)
    ok('额外目录有明细和撤销', '明细' in dirhtml and '撤销' in dirhtml, dirhtml)
    ok('记录里有撤销入口', '撤销' in sheet)
    pg.evaluate("()=>{var a=Array.from(document.querySelectorAll('#mfWrap a')).find(x=>x.innerText.trim()==='撤销');if(a)a.click();}")
    pg.wait_for_timeout(150); click_ok(pg); pg.wait_for_timeout(250)
    ok('按笔撤销后清零', pg.evaluate("()=>Object.keys(flownPerPos).length===0"))
    ok('撤销后标记已撤销', pg.evaluate("()=>{var h=JSON.parse(localStorage.getItem(sk('manualFlyHistory'))||'[]');return h.length>0 && h[0].undone===true;}"))

    # 3. 各100 是每个100（三个肖共300）
    reset(pg); start(pg)
    set_text(pg, '平马猪羊 各100')
    pg.evaluate("()=>applyManualFlyList()"); pg.wait_for_timeout(150)
    preview2 = pg.evaluate("()=>{var o=Array.from(document.querySelectorAll('.ai-ov')).pop();return o?o.innerText:''}")
    ok('各100预览每个100', '合计 300 元' in preview2 and '平特马 100' in preview2, preview2)
    click_cancel(pg)

    # 4. 认不出整单不落账
    reset(pg); start(pg)
    set_text(pg, '平特虎100\n这不是一行')
    pg.evaluate("()=>applyManualFlyList()"); pg.wait_for_timeout(150)
    bad = pg.evaluate("()=>{var o=Array.from(document.querySelectorAll('.ai-ov')).pop();return o?o.innerText:''}")
    ok('坏行提示整单不登记', '一分钱都没登记' in bad, bad)
    ok('坏行未落账', pg.evaluate("()=>Object.keys(flownPerPos).length===0"))

    ok('全程无页面异常', not errors, errors)
    b.close()

failed = [c for c in CHECKS if not c[1]]
print('\nSUMMARY %d/%d' % (len(CHECKS) - len(failed), len(CHECKS)))
if failed:
    print('FAILS: ' + json.dumps([f[0] for f in failed], ensure_ascii=False))
    sys.exit(1)
