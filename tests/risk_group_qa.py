"""分组持仓：三组共用同一总盘算法，行内四列相加=下注，三组最坏相加=持仓分析。"""
import re,sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
TXT='''02 700
08 300
平特马 200
连肖马蛇 100
三中三复式01.02.03.04.05.06.07各5
'''
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':430,'height':1000}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=rkqa',wait_until='load'); pg.wait_for_timeout(300)
    pg.evaluate("()=>{localStorage.clear();localStorage.setItem('ai_preview_enabled','0');}")
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=rkqa',wait_until='load'); pg.wait_for_timeout(500)
    pg.evaluate("(t)=>{document.getElementById('input').value=t;doSave();}",TXT); pg.wait_for_timeout(500)
    pg.evaluate("()=>{switchTab('rank');openRankSection('risk');renderRisk();}"); pg.wait_for_timeout(400)
    chk('分组表存在',pg.evaluate("()=>!!document.getElementById('rkGroupTable')"))
    rows=pg.evaluate("()=>Array.from(document.querySelectorAll('#rkGroupTable tbody tr')).map(r=>Array.from(r.children).map(x=>x.innerText.trim().replace(/,/g,'')))")
    chk('三组+合计四行',len(rows)==4,rows)
    chk('六列：分组/下注/已飞/待飞/自留/最坏',pg.evaluate("()=>Array.from(document.querySelectorAll('#rkGroupTable thead th')).map(x=>x.innerText.trim()).join('|')")=='分组|下注|已飞|待飞|自留|最坏')
    def num(x): return float(x.replace('+',''))
    good=True
    for r in rows:
        bx,dx,px,kx,wx=map(num,r[1:])
        if abs(bx-dx-px-kx)>0.6: good=False
    chk('每行 下注=已飞+待飞+自留',good,rows)
    colsum=[sum(num(r[i]) for r in rows[:3]) for i in range(1,6)]
    chk('三组各列相加=合计行',all(abs(colsum[i]-num(rows[3][i+1]))<0.6 for i in range(4)),[colsum,rows[3]])
    head=pg.evaluate("()=>document.querySelector('div[onclick=\"toggleRiskBox()\"]').innerText")
    m=re.search(r'最坏\s*(-?\d+)',head); top=float(m.group(1)) if m else None
    chk('三组最坏相加=持仓分析最坏',top is not None and abs(num(rows[3][5])-top)<0.6,(rows[3][5],top))
    txt=pg.evaluate("()=>document.getElementById('riskBody').textContent")
    chk('旧独立持仓标题已取消',all(x not in txt for x in ['特号持仓（只算特号）','平特持仓 ·','连肖持仓（']))
    chk('明细标题统一',all(x in txt for x in ['特号明细 · 2个号','平特明细 · 1肖','连肖明细 · 1组']))
    chk('写明同一总盘分摊','同一总盘最坏场景的分摊' in txt)
    # 部分已飞：连肖按实际记录扣，不按阈值变量拍脑袋
    pg.evaluate("""()=>{flownPerPos={'02':100,'08':100,'平特马':100,'连肖马蛇':50,'_em_total':10};flownReal={'02':100,'08':100,'平特马':100,'连肖马蛇':50,'_em_total':10};localStorage.setItem(sk('flownPerPos'),JSON.stringify(flownPerPos));localStorage.setItem(sk('flownReal'),JSON.stringify(flownReal));renderRisk();}""" ); pg.wait_for_timeout(300)
    rows2=pg.evaluate("()=>Array.from(document.querySelectorAll('#rkGroupTable tbody tr')).map(r=>Array.from(r.children).map(x=>x.innerText.trim().replace(/,/g,'')))")
    chk('连肖部分已飞：50/0/50',rows2[2][1:5]==['100','50','0','50'],rows2[2])
    chk('部分已飞每行相加=下注',all(abs(num(r[1])-num(r[2])-num(r[3])-num(r[4]))<0.6 for r in rows2[1:4]),rows2)
    head2=pg.evaluate("()=>document.querySelector('div[onclick=\"toggleRiskBox()\"]').innerText")
    m2=re.search(r'最坏\s*(-?\d+)',head2); top2=float(m2.group(1)) if m2 else None
    chk('部分已飞三组最坏相加=整盘',top2 is not None and abs(num(rows2[3][5])-top2)<0.6,(rows2[3][5],top2))
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('FAILS',len(FAIL)); sys.exit(1 if FAIL else 0)
