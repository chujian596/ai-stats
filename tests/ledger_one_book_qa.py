"""一套账目联通性：飞单页、上家结算单、账单、实际盈亏、总飞必须同一数。"""
import sys, re
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
def setup(pg, real, manual, undone=False, special=0):
    pg.evaluate("""([real,manual,undone,special])=>{
      localStorage.clear(); var p=selfFlyPeriod();
      orders=[{id:'c1',customer:'散客',raw:'三中三 12.24.48 各375',
        lines:[{r:'三中三 12.24.48 各375',a:375,hk:false}],price:375,qty:1,amount:375,
        codes:['三中三:12,24,48'],codeAmts:{'三中三:12,24,48':375},
        createdAt:'2026/11/27 04:50:00',originShop:'A'}]; hkOrders=[];
      flownPerPos={'_em_total':real}; flownReal={'_em_total':real};
      if(special>0){ flownPerPos['22']=special; flownReal['22']=special; }
      localStorage.setItem(sk('manualFlyHistory'),JSON.stringify([{id:1,p:p,
        txt:'三中三 12-24-37 / 12-23-36 各组10 ×4',
        batch:[{k:'_em_total',amt:manual}],applied:true,undone:undone}]));
      renderAll();
    }""",[real,manual,undone,special])
    pg.wait_for_timeout(500)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    for name,real,manual,undone,special,total in [
        ('真账415含手飞',415,40,False,0,415),
        ('旧账375+手飞40',375,40,False,0,415),
        ('撤销手飞',375,40,True,0,375),
        ('特号1000+二三415',375,40,False,1000,1415),
    ]:
        pg=b.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=led'+str(real)+str(undone)+str(special),wait_until='load'); pg.wait_for_timeout(500)
        setup(pg,real,manual,undone,special)
        data=pg.evaluate("""()=>{
          const FB=flyBook(null), D=upSettleData(), B=buildBill(), A=actualPnL();
          return {em:FB.em, emBack:FB.emBack, fly:D.totalFly, emFly:(D.cats.filter(c=>c.k==='em')[0]||{}).fly,
            detailEm:(D.detail.em||[]).reduce((s,x)=>s+(Number(x.amt)||0),0), detailText:JSON.stringify(D.detail.em||[]),
            billFly:B.fly, billEm:((B.cats||[]).filter(c=>c.k==='em')[0]||{}).fly,
            pnlFly:A.flyOut, allFly:totalFlownReal(), copy:window._upCopy||''};
        }""")
        txt=pg.locator('#upDetail').inner_text(); flat=re.sub(r'\s+',' ',txt)
        chk(name+'：明细对平'+str(total- (0 if not special else 0)),('✓ 明细对平：'+str(415 if not undone else 375)) in flat, flat[-100:])
        chk(name+'：页面合计'+str(total),('='+str(total)) in flat.replace(' ',''),flat[-100:])
        chk(name+'：flyBook.em='+str(415 if not undone else 375),data['em']==(415 if not undone else 375),data['em'])
        chk(name+'：上家结算em='+str(415 if not undone else 375),data['emFly']==(415 if not undone else 375),data['emFly'])
        chk(name+'：上家结算总飞='+str(total),data['fly']==total,data['fly'])
        chk(name+'：账单飞='+str(total),data['billFly']==total,data['billFly'])
        chk(name+'：账单二三='+str(415 if not undone else 375),data['billEm']==(415 if not undone else 375),data['billEm'])
        chk(name+'：实际盈亏飞='+str(total),data['pnlFly']==total,data['pnlFly'])
        chk(name+'：总飞='+str(total),data['allFly']==total,data['allFly'])
        chk(name+'：上家明细合计='+str(415 if not undone else 375),data['detailEm']==(415 if not undone else 375),data['detailEm'])
        if not undone:
            chk(name+'：明细有手飞二三','手飞二三' in txt)
            chk(name+'：复制文本有手飞二三','手飞二三' in data['copy'])
            chk(name+'：表头标了手飞40',('＋手飞40' in flat.replace(' ','')) or ('手飞 40' in data['copy']))
        else:
            chk(name+'：撤销不显示手飞',('手飞二三' not in txt) and ('手飞二三' not in data['copy']))
        chk(name+'：无 JS 报错',not errs,errs[:2])
        pg.close()
    b.close()
print('\nSUMMARY %d/%d'%(len(FAIL)+0, len(FAIL)+0) if False else '')
print('FAILS',len(FAIL)); sys.exit(1 if FAIL else 0)
