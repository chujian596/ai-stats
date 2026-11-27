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
    fh=pg.evaluate("()=>{var h=document.querySelector('[onclick*=\"flyListPreview\"]');return h&&h.parentElement&&h.parentElement.nextElementSibling?h.parentElement.nextElementSibling.id:''}")
    chk('分组持仓已并入飞单卡片',fh=='rkGroupCard',fh)
    tabs=pg.evaluate("()=>Array.from(document.querySelectorAll('#tab-rank .rank-btn')).map(x=>x.innerText.trim())")
    chk('按键顺序与改名',';'.join(tabs)=='排行;归档;订单;清除;风险;账单;盈亏;飞单',tabs)
    chk('平特肖入口已撤',pg.evaluate("()=>Array.from(document.querySelectorAll('.rank-btn')).some(x=>x.innerText.includes('平特肖'))")==False)
    chk('四个玩法分组',pg.evaluate("()=>document.querySelectorAll('#flyListPreview .fd-sec').length")==4)
    titles=pg.evaluate("()=>Array.from(document.querySelectorAll('#flyListPreview .fd-sec-title')).map(x=>x.innerText.trim())")
    chk('分组名称不带通道',';'.join(titles)=='特号;平特;连肖;二/三',titles)
    chk('飞单旧四格总览已撤',pg.evaluate("()=>document.querySelectorAll('#flyListPreview .fd-sum').length")==0)
    grow=pg.evaluate("()=>Array.from(document.querySelectorAll('#rkGroupTable tbody tr')).map(r=>Array.from(r.children).map(x=>x.innerText.trim()))")
    chk('分组持仓合计下注3304',grow[-1][1]=='3,304',grow[-1])
    chk('分组持仓合计待飞2005',grow[-1][3]=='2,005',grow[-1])
    chk('分组持仓合计自留3304',grow[-1][4]=='3,304',grow[-1])
    ths=pg.evaluate("()=>Array.from(document.querySelectorAll('#flyListPreview .fd-table thead tr')).map(r=>Array.from(r.children).map(x=>x.innerText.trim()).join('|'))")
    chk('每张表都有下注/已飞/待飞/自留四列',len(ths)==4 and all(x.endswith('下注|已飞|待飞|自留') for x in ths),ths)
    bad=pg.evaluate("""()=>Array.from(document.querySelectorAll('#flyListPreview .fd-table tbody tr:not(.fd-sub)')).filter(r=>r.children.length!==5).length""")
    chk('数据行都是5栏，不再左右乱窜',bad==0,bad)
    sums=pg.evaluate("""()=>{var a=[0,0,0,0];Array.from(document.querySelectorAll('#flyListPreview .fd-table tbody tr:not(.fd-sub)')).forEach(r=>{if(r.children.length===5){for(var i=0;i<4;i++)a[i]+=Number((r.children[i+1].innerText||'0').replace(/[^0-9.-]/g,''))||0;}});return a;}""")
    chk('各分组下注合计3304',sums[0]==3304,sums)
    chk('各分组已飞合计0',sums[1]==0,sums)
    chk('各分组待飞合计2005',sums[2]==2005,sums)
    chk('各分组自留合计3304',sums[3]==3304,sums)
    # 点“不飞”后，分组表和飞单明细都必须立即把该组待飞扣掉，不能留旧数
    pg.evaluate("()=>flySkipMany('平特马')"); pg.wait_for_timeout(300)
    grow2=pg.evaluate("()=>Array.from(document.querySelectorAll('#rkGroupTable tbody tr')).map(r=>Array.from(r.children).map(x=>x.innerText.trim()))")
    chk('不飞平特马后合计待飞1805',grow2[-1][3]=='1,805',grow2[-1])
    chk('不飞后分组表仍只一套合计',len(grow2)==5,grow2)
    sums2=pg.evaluate("""()=>{var a=[0,0,0,0];Array.from(document.querySelectorAll('#flyListPreview .fd-table tbody tr:not(.fd-sub)')).forEach(r=>{if(r.children.length===5){for(var i=0;i<4;i++)a[i]+=Number((r.children[i+1].innerText||'0').replace(/[^0-9.-]/g,''))||0;}});return a;}""")
    chk('不飞后飞单明细待飞同步1805',sums2[2]==1805,sums2)
    chk('不飞后飞单明细无平特马',pg.evaluate("()=>Array.from(document.querySelectorAll('#flyListPreview .fd-table tbody tr')).some(r=>r.innerText.includes('平特马'))")==False)
    # 特号点“不飞”同样要立刻扣掉，不能只在分组表扣
    pg.evaluate("()=>flySkipMany('02')"); pg.wait_for_timeout(300)
    grow3=pg.evaluate("()=>Array.from(document.querySelectorAll('#rkGroupTable tbody tr')).map(r=>Array.from(r.children).map(x=>x.innerText.trim()))")
    chk('不飞02后合计待飞1205',grow3[-1][3]=='1,205',grow3[-1])
    sums3=pg.evaluate("""()=>{var a=[0,0,0,0];Array.from(document.querySelectorAll('#flyListPreview .fd-table tbody tr:not(.fd-sub)')).forEach(r=>{if(r.children.length===5){for(var i=0;i<4;i++)a[i]+=Number((r.children[i+1].innerText||'0').replace(/[^0-9.-]/g,''))||0;}});return a;}""")
    chk('不飞02后飞单明细待飞同步1205',sums3[2]==1205,sums3)
    rr02=pg.evaluate("""()=>{var r=Array.from(document.querySelectorAll('#flyListPreview .fd-table tbody tr')).find(x=>x.innerText.trim().startsWith('02 '));return r?Array.from(r.children).map(x=>x.innerText.trim()):[];}""")
    chk('02行待飞归0、自留700',rr02[3]=='0' and rr02[4]=='700',rr02)
    txt=pg.evaluate("()=>document.getElementById('flyListPreview').textContent")
    chk('旧三栏合并文案已取消','特码02' not in txt)
    chk('入口不写通道版','飞单明细 · 通道版' not in pg.evaluate("()=>document.documentElement.textContent") and '通道' not in txt)
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('FAILS',len(FAIL)); sys.exit(1 if FAIL else 0)
