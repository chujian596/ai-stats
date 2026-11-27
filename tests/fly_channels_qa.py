"""飞单明细·四组：按玩法分组、五列对齐、金额与总览一致、无旧三栏。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
TXT='''02 700
08 300
09 500
10 10
11 93
13 95
14 10
15 35
18 200
19 85
20 10
21 10
22 60
25 25
26 35
30 135
34 70
35 143
37 20
38 90
42 5
46 20
47 38
平特马 200
平特蛇 300
连肖马蛇 100
三中三:08,17,25 5
三中三:08,17,36 5
三中三:08,25,36 5
'''
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':430,'height':1000}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=fdqa',wait_until='load'); pg.wait_for_timeout(300)
    pg.evaluate("()=>{localStorage.clear();localStorage.setItem('ai_preview_enabled','0');}")
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=fdqa',wait_until='load'); pg.wait_for_timeout(500)
    pg.evaluate("""(t)=>{document.getElementById('input').value=t;doSave();}""",TXT); pg.wait_for_timeout(500)
    pg.evaluate("()=>renderRisk()"); pg.wait_for_timeout(300)
    chk('四个玩法分组',pg.evaluate("()=>document.querySelectorAll('#flyListPreview .fd-sec').length")==4)
    titles=pg.evaluate("()=>Array.from(document.querySelectorAll('#flyListPreview .fd-sec-title')).map(x=>x.innerText.trim())")
    chk('分组名称不带通道',';'.join(titles)=='特号;平特;连肖;二/三',titles)
    cards=pg.evaluate("()=>Array.from(document.querySelectorAll('#flyListPreview .fd-stat b')).map(x=>x.innerText.trim())")
    chk('总览下注3304',cards[0]=='3304',cards)
    chk('总览待飞2005',cards[2]=='2005',cards)
    chk('总览自留1299',cards[3]=='1299',cards)
    ths=pg.evaluate("()=>Array.from(document.querySelectorAll('#flyListPreview .fd-table thead tr')).map(r=>Array.from(r.children).map(x=>x.innerText.trim()).join('|'))")
    chk('每张表都有下注/已飞/待飞/自留四列',len(ths)==4 and all(x.endswith('下注|已飞|待飞|自留') for x in ths),ths)
    bad=pg.evaluate("""()=>Array.from(document.querySelectorAll('#flyListPreview .fd-table tbody tr:not(.fd-sub)')).filter(r=>r.children.length!==5).length""")
    chk('数据行都是5栏，不再左右乱窜',bad==0,bad)
    sums=pg.evaluate("""()=>{var a=[0,0,0,0];Array.from(document.querySelectorAll('#flyListPreview .fd-table tbody tr:not(.fd-sub)')).forEach(r=>{if(r.children.length===5){for(var i=0;i<4;i++)a[i]+=Number((r.children[i+1].innerText||'0').replace(/[^0-9.-]/g,''))||0;}});return a;}""")
    chk('各分组下注合计3304',sums[0]==3304,sums)
    chk('各分组已飞合计0',sums[1]==0,sums)
    chk('各分组待飞合计2005',sums[2]==2005,sums)
    chk('各分组自留合计1299',sums[3]==1299,sums)
    txt=pg.evaluate("()=>document.getElementById('flyListPreview').textContent")
    chk('旧三栏合并文案已取消','特码02' not in txt)
    chk('入口不写通道版','飞单明细 · 通道版' not in pg.evaluate("()=>document.documentElement.textContent") and '通道' not in txt)
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('FAILS',len(FAIL)); sys.exit(1 if FAIL else 0)
