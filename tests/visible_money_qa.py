"""当前手机账面对齐专项：375 已飞清单不能 0 条、分账不能 0/375、旧手动 200 可补计。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':760,'height':1200})
    errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=visible',wait_until='load'); pg.wait_for_timeout(300)
    r=pg.evaluate("""()=>{
      localStorage.clear(); flownPerPos={}; flownReal={}; orders=[]; hkOrders=[];
      orders=[{id:'t1',codes:['三中三:17,20,25'],codeAmts:{'三中三:17,20,25':375},price:375}];
      autoFlyOn=true; localStorage.setItem(sk('autoFlyOn'),'1'); localStorage.setItem(sk('emFlyOn'),'1');
      var p=selfFlyPeriod();
      var hist=[{id:1,p:p,t:Date.now()-1000,txt:'连肖马蛇100 / 连肖马蛇羊100',cnt:2,sum:200,batch:[{k:'连肖马蛇',amt:100},{k:'连肖马蛇羊',amt:100}],undone:false,applied:true}];
      localStorage.setItem(sk('manualFlyHistory'),JSON.stringify(hist));
      var L=catLedgerData(); var list=flyEditListHtml(true); var dir=manualFlyDirHtml();
      return {catFly:L.em.flown,catPend:L.em.pending,catBet:L.em.bet,list:list,dir:dir,total:totalFlownReal()};
    }""")
    chk('分账总表二三已飞=375',r['catFly']==375,r['catFly'])
    chk('分账总表二三待飞=0',r['catPend']==0,r['catPend'])
    chk('分账总表二三收单=375',r['catBet']==375,r['catBet'])
    chk('已飞清单不再显示 0 条','0 条' not in r['list'],r['list'][:60])
    chk('已飞清单金额=375','value="375"' in r['list'])
    chk('旧手动 200 标未计入且有补计','未计入' in r['dir'] and '补计' in r['dir'])
    pg.evaluate("()=>manualApplyBatch(1)")
    pg.wait_for_selector('#mcOk',timeout=3000)
    pg.evaluate("()=>document.getElementById('mcOk').click()"); pg.wait_for_timeout(700)
    a=pg.evaluate("""()=>{var L=catLedgerData(); var d=manualFlyDirHtml(); return {total:totalFlownReal(),paid:flyMoneySummary().paid,reflected:/已计入/.test(d),pos:flownPerPos,em:L.em.flown};}""")
    chk('补计后总额=375+200=575',a['total']==575 and a['paid']==575,a)
    chk('补计后手动批次标已计入',a['reflected'])
    chk('补计只加连肖 100+100',a['pos'].get('连肖马蛇')==100 and a['pos'].get('连肖马蛇羊')==100,a['pos'])
    chk('补计不动二三 375',a['em']==375,a['em'])
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('\nSUMMARY %d/%d'%(11-len(FAIL),11))
sys.exit(1 if FAIL else 0)
