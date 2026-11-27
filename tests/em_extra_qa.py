"""二三额外飞：客户下注/额外飞分开，逐笔列明细，合计与分账总表同一算法。"""
import sys, re
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
# 16笔客户三中三，合计 375
lines=['三中三:08,24,33 80','三中三:31,32,33 165']
for i in range(12): lines.append('三中三:%02d,%02d,%02d 10'%(i+1,i+2,i+3))
lines += ['三中三:20,21,22 5','三中三:23,24,25 5']
TXT='\n'.join(lines)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':430,'height':1200}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=emxqa',wait_until='load'); pg.wait_for_timeout(300)
    pg.evaluate("()=>{localStorage.clear();localStorage.setItem('ai_preview_enabled','0');localStorage.setItem(sk('autoFlyOn'),'1');localStorage.setItem(sk('emFlyOn'),'1');}")
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=emxqa',wait_until='load'); pg.wait_for_timeout(500)
    pg.evaluate("(t)=>{document.getElementById('input').value=t;doSave();}",TXT); pg.wait_for_timeout(600)
    pg.evaluate("""()=>{_applyManualFlyCore('三中三:17,20,25 10\\n三中三:07,15,36 10\\n三中三:12,24,37 10\\n三中三:12,23,36 10', null, false); syncAutoEmFly(); renderRisk();}"""); pg.wait_for_timeout(500)
    pg.evaluate("()=>{switchTab('rank');openRankSection('risk');renderRisk();}"); pg.wait_for_timeout(400)
    # 打开飞单明细
    pg.evaluate("()=>{var e=document.getElementById('flyListPreview');if(e.style.display==='none')document.querySelector('[onclick*=\\\"flyListPreview\\\"]').click();}")
    pg.wait_for_timeout(300)
    sec=pg.evaluate("()=>{var s=Array.from(document.querySelectorAll('#flyListPreview .fd-sec')).find(x=>x.innerText.includes('二/三'));return s?s.innerText:'';}")
    chk('客户下注仍是375','16笔订单 · 下注375' in sec,sec[:120])
    chk('额外飞写明4笔40','额外飞4笔40' in sec,sec[:120])
    chk('不再出现下注395','下注 395' not in sec and '下注395' not in sec)
    extra=pg.evaluate("""()=>Array.from(document.querySelectorAll('#flyListPreview .fd-table tbody tr')).filter(r=>r.innerText.includes('额外飞') && r.children.length===5).map(r=>Array.from(r.children).map(x=>x.innerText.trim().replace(/,/g,'')) )""")
    chk('额外飞逐笔四行',len(extra)==4,extra)
    chk('额外飞行下注为空、已飞10、自留-10',all(r[1]=='—' and r[2]=='10' and r[4]=='-10' for r in extra),extra)
    chk('额外飞号码可追溯',all(('172025' in r[0].replace(' ','').replace(',','') or '071536' in r[0].replace(' ','').replace(',','') or '122437' in r[0].replace(' ','').replace(',','') or '122336' in r[0].replace(' ','').replace(',','')) for r in extra),extra)
    m=re.search(r'小计：下注 (\d+) ｜ 已飞 (\d+) ｜ 待飞 (\d+) ｜ 自留 (-?\d+)',sec)
    chk('二三小计 375/415/0/-40',m and m.groups()==('375','415','0','-40'),m.groups() if m else sec[-120:])
    grow=pg.evaluate("()=>Array.from(document.querySelectorAll('#rkGroupTable tbody tr')).map(r=>Array.from(r.children).map(x=>x.innerText.trim().replace(/,/g,'')) )")
    chk('分组表二三 375/415/0/-40',grow[4][1:5]==['375','415','0','-40'],grow[4])
    chk('分组合计同数',grow[-1][1:5]==['375','415','0','-40'],grow[-1])
    # 明细漏一行时，按“同一笔订单二三合计”补齐：30 不能变 20
    hh=pg.evaluate("""()=>{var o={raw:'三中三:01,02,03 10;三中三:04,05,06 20',codes:['三中三:01,02,03','三中三:04,05,06'],codeAmts:{'三中三:01,02,03':10,'三中三:04,05,06':20},price:0,lines:[{r:'三中三:01,02,03',a:10}]};return renderFlyChannelsV2({riskList:[o],lines:[],emFlyOn:true,autoFlyOn:true,totalBet:30,sales:{},pteBetByZod:{},splitTakeAll:100,pteFlyTakeAll:0});}""")
    chk('缺行按订单合计补齐 30', '小计：下注 30' in hh and '1笔订单 · 下注30' in hh)
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('FAILS',len(FAIL)); sys.exit(1 if FAIL else 0)
