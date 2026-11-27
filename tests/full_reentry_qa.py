"""全流程重录对账：7415 四类逐笔金额 → 分账总表/分组/飞单明细/台账 全部同数。
订单：特号4740（10个号）+平特1500（马/蛇/鸡）+连肖800（2组）+二三375（15笔）
额外飞：二三40（4笔各10）+连肖200（马鸡100/马鸡羊100）
已飞：特1410、平特马700、连肖客户800+额外200、二三自动375+额外40
不飞：特号其余6个号、平特蛇/鸡 → 待飞0
"""
import sys, re
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)

SPEC='\n'.join(['01 1000','02 300','03 100','04 10','05 900','06 700','07 600','08 500','09 400','10 230'])
PTE='\n'.join(['平特马 700','平特蛇 500','平特鸡 300'])
LX='\n'.join(['连肖猪蛇 500','连肖鸡鼠 300'])
EM='\n'.join(['三中三:08,24,33 80','三中三:31,32,33 165']+['三中三:%02d,%02d,%02d 10'%(i+1,i+2,i+3) for i in range(13)])
TXT='\n'.join([SPEC,PTE,LX,EM])

def nums(s):
    return re.sub(r'\s','',s).replace(',','')

with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':430,'height':1600}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=fullreentry',wait_until='load'); pg.wait_for_timeout(300)
    pg.evaluate("()=>{localStorage.clear();localStorage.setItem('ai_preview_enabled','0');localStorage.setItem(sk('autoFlyOn'),'1');localStorage.setItem(sk('emFlyOn'),'1');}")
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=fullreentry',wait_until='load'); pg.wait_for_timeout(500)
    pg.evaluate("(t)=>{document.getElementById('input').value=t;doSave();}",TXT); pg.wait_for_timeout(700)

    # 1) 重录后的每一行金额
    lines=pg.evaluate("()=>{var o=activeOrders()[0]||{};return orderLineItems(o).map(function(l){return {r:String(l.r||''),a:Number(l.a||0)}});}")
    chk('订单逐行30笔',len(lines)==30,len(lines))
    chk('每行金额均>0',all(x['a']>0 for x in lines),[x for x in lines if x['a']<=0])
    def sumcat(pref):
        return sum(x['a'] for x in lines if x['r'].startswith(pref))
    chk('特号逐行合计4740',sumcat('01')+sumcat('02')+sumcat('03')+sumcat('04')+sumcat('05')+sumcat('06')+sumcat('07')+sumcat('08')+sumcat('09')+sumcat('10')==4740)
    chk('平特逐行合计1500',sum(x['a'] for x in lines if x['r'].startswith('平特'))==1500)
    chk('连肖逐行合计800',sum(x['a'] for x in lines if x['r'].startswith('连肖'))==800)
    chk('二三逐行合计375',sum(x['a'] for x in lines if re.match(r'^(三中三|三中二|二中二)',x['r']))==375)
    chk('全单逐行合计7415',sum(x['a'] for x in lines)==7415)

    # 2) 额外飞 / 已飞 / 不飞
    pg.evaluate("""()=>{window.myAlert=function(){};
      _applyManualFlyCore('三中三:17,20,25 10\\n三中三:07,15,36 10\\n三中三:12,24,37 10\\n三中三:12,23,36 10', null, false);
      _applyManualFlyCore('连肖马鸡 100\\n连肖马鸡羊 100', null, false);
      flownPerPos['01']=1000; flownReal['01']=1000;
      flownPerPos['02']=300;  flownReal['02']=300;
      flownPerPos['03']=100;  flownReal['03']=100;
      flownPerPos['04']=10;   flownReal['04']=10;
      flownPerPos['平特马']=700; flownReal['平特马']=700;
      flownPerPos['连肖猪蛇']=500; flownReal['连肖猪蛇']=500;
      flownPerPos['连肖鸡鼠']=300; flownReal['连肖鸡鼠']=300;
      localStorage.setItem(sk('flownPerPos'),JSON.stringify(flownPerPos));
      localStorage.setItem(sk('flownReal'),JSON.stringify(flownReal));
      localStorage.setItem(flySkipKey(),JSON.stringify(['05','06','07','08','09','10','平特蛇','平特鸡']));
      switchTab('rank'); openRankSection('risk'); renderRisk();
    }"""); pg.wait_for_timeout(700)
    pg.evaluate("()=>{var e=document.getElementById('flyListPreview');if(e.style.display==='none')document.querySelector('[onclick*=\"flyListPreview\"]').click();}"); pg.wait_for_timeout(350)

    # 3) 分账总表（四类）
    led=nums(pg.inner_text('#catLedgerBox'))
    chk('分账四类逐项同数', all(x in led for x in ['特号4740141003330','平特15007000800','连肖80010000-200','二三3754150-40','合计7415352503890']),led[:220])
    chk('分账标签只写特号','特号/特肖' not in led)

    # 4) 分组持仓
    rows=pg.evaluate("()=>Array.from(document.querySelectorAll('#rkGroupTable tbody tr')).map(r=>Array.from(r.children).map(x=>x.innerText.trim().replace(/,/g,'')))")
    chk('分组特号4740/1410/0/3330',rows[0][1:5]==['4740','1410','0','3330'],rows[0])
    chk('分组平特1500/700/0/800',rows[1][1:5]==['1500','700','0','800'],rows[1])
    chk('分组连肖800/1000/0/-200',rows[2][1:5]==['800','1000','0','-200'],rows[2])
    chk('分组二三375/415/0/-40',rows[3][1:5]==['375','415','0','-40'],rows[3])
    chk('分组合计7415/3525/0/3890',rows[4][1:5]==['7415','3525','0','3890'],rows[4])

    # 5) 飞单明细四组小计 + 总 footer
    rawfoots=pg.evaluate("()=>Array.from(document.querySelectorAll('#flyListPreview .fd-foot')).map(x=>x.innerText)")
    foots=[]
    for x in rawfoots:
        m=re.search(r'(小计：下注\s*\d+\s*｜\s*已飞\s*\d+\s*｜\s*待飞\s*\d+\s*｜\s*自留\s*-?\d+|分组合计：下注\s*\d+\s*｜\s*已飞\s*\d+\s*｜\s*待飞\s*\d+\s*｜\s*自留\s*-?\d+)',x)
        if m: foots.append(nums(m.group(1)))
    feet=['小计：下注4740｜已飞1410｜待飞0｜自留3330','小计：下注1500｜已飞700｜待飞0｜自留800','小计：下注800｜已飞1000｜待飞0｜自留-200','小计：下注375｜已飞415｜待飞0｜自留-40','分组合计：下注7415｜已飞3525｜待飞0｜自留3890']
    chk('四组小计与总footer同数', all(any(f==e for f in foots) for e in feet),[f for f in foots if '小计' in f or '分组合计' in f])
    chk('无“与总单差”', all('与总单差' not in f for f in foots))

    # 6) 二三 & 连肖额外飞逐笔
    sec_em=pg.evaluate("()=>{var s=Array.from(document.querySelectorAll('#flyListPreview .fd-sec')).find(x=>x.innerText.includes('二/三'));return s?s.innerText:''}")
    chk('二三15笔375额外4笔40','15笔订单 · 下注375 · 额外飞4笔40' in sec_em,sec_em[:80])
    extra_em=pg.evaluate("""()=>{var s=Array.from(document.querySelectorAll('#flyListPreview .fd-sec')).find(x=>x.innerText.includes('二/三'));return s?Array.from(s.querySelectorAll('.fd-table tbody tr')).filter(r=>r.innerText.includes('额外飞')&&r.children.length===5).map(r=>Array.from(r.children).map(x=>x.innerText.trim())):[]}""")
    chk('二三额外飞4行各10/自留-10',len(extra_em)==4 and all(r[2]=='10' and r[4]=='-10' for r in extra_em),extra_em)
    sec_lx=pg.evaluate("()=>{var s=Array.from(document.querySelectorAll('#flyListPreview .fd-sec')).find(x=>x.innerText.includes('连肖'));return s?s.innerText:''}")
    extra_lx=pg.evaluate("""()=>{var s=Array.from(document.querySelectorAll('#flyListPreview .fd-sec')).find(x=>x.innerText.includes('连肖'));return s?Array.from(s.querySelectorAll('.fd-table tbody tr')).filter(r=>r.innerText.includes('额外飞')&&r.children.length===5).map(r=>Array.from(r.children).map(x=>x.innerText.trim())):[]}""")
    chk('连肖额外飞2行各100/自留-100',len(extra_lx)==2 and all(r[2]=='100' and r[4]=='-100' for r in extra_lx),extra_lx)

    # 7) 点分账行看目录，不报错
    pg.evaluate("()=>toggleCatLedger('spec')"); pg.wait_for_timeout(200)
    chk('点特号目录可展开','特号目录' in pg.inner_text('#catLedgerBox') and '收 4740' in pg.inner_text('#catLedgerBox'),pg.inner_text('#catLedgerBox')[-120:])
    chk('无 JS 报错',not errs,errs[:3])
    b.close()
print('FAILS',len(FAIL)); sys.exit(1 if FAIL else 0)
