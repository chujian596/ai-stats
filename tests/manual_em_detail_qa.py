"""手飞二三40必须进二/三明细与飞走合计，不能只算进实付再报“明细差40”。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
def setup(pg, real, manual, undone=False):
    pg.evaluate("""([real,manual,undone])=>{
      localStorage.clear(); var p=selfFlyPeriod();
      orders=[{id:'c1',customer:'散客',raw:'三中三 12.24.48 各375',
        lines:[{r:'三中三 12.24.48 各375',a:375,hk:false}],price:375,qty:1,amount:375,
        codes:['三中三:12,24,48'],codeAmts:{'三中三:12,24,48':375},
        createdAt:'2026/11/27 04:50:00',originShop:'A'}]; hkOrders=[];
      flownPerPos={'_em_total':real}; flownReal={'_em_total':real};
      localStorage.setItem(sk('manualFlyHistory'),JSON.stringify([{id:1,p:p,
        txt:'三中三 12-24-37 / 12-23-36 各组10 ×4',
        batch:[{k:'_em_total',amt:manual}],applied:true,undone:undone}]));
      renderAll();
    }""",[real,manual,undone])
    pg.wait_for_timeout(500)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    for name,real,manual,undone,expect_detail,expect_total in [
        ('真账415含手飞40',415,40,False,415,415),
        ('旧账只落375，手飞40仍要算',375,40,False,415,415),
        ('手飞批次已撤销，不得计入',375,40,True,375,375),
    ]:
        pg=b.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=med'+str(real)+str(undone),wait_until='load'); pg.wait_for_timeout(500)
        setup(pg,real,manual,undone)
        txt=pg.locator('#upDetail').inner_text()
        body=pg.locator('body').inner_text()
        chk(name+'：明细合计对平'+str(expect_detail),('✓ 明细对平：'+str(expect_detail)) in txt, txt[-160:])
        chk(name+'：飞走合计'+str(expect_total),('0 + 0 + '+str(expect_total)+' = '+str(expect_total)) in __import__('re').sub(r'\s+',' ',txt), body[-120:])
        if not undone: chk(name+'：明细里能看到手飞40',('手飞二三' in txt and '40' in txt),txt[:160])
        else: chk(name+'：撤销批次不显示',('手飞二三' not in txt),txt[:160])
        chk(name+'：无 JS 报错',not errs,errs[:2])
        pg.close()
    b.close()
print('\nSUMMARY %d/%d'%(11-len(FAIL),11)); sys.exit(1 if FAIL else 0)
