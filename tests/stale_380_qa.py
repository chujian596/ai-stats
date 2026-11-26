"""旧版遗留 _em_total=380、但客户单只有 375 时，不能再显示 380/多飞5。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=stale',wait_until='load'); pg.wait_for_timeout(300)
    r=pg.evaluate("""()=>{
      localStorage.clear(); orders=[{id:'t1',codes:['三中三:17,20,25'],codeAmts:{'三中三:17,20,25':375},price:375}]; hkOrders=[];
      flownReal={'_em_total':380}; flownPerPos={'_em_total':380}; autoFlyOn=false;
      localStorage.setItem(sk('autoFlyOn'),'0'); localStorage.setItem(sk('emExtra'),'[]'); localStorage.setItem(sk('manualFlyHistory'),'[]');
      var off=getThisRoundFly(); var e=off.lines.filter(l=>l.code==='二中二/三中三合计')[0];
      var L=catLedgerData();
      return {amt:e.amt,full:e.full,done:e.done,total:off.totalFly,catPend:L.em.pending,catFly:L.em.flown};
    }""")
    chk('自动飞关：二三待飞=375',r['amt']==375 and r['full']==375,r)
    chk('自动飞关：已飞=0（旧380不算）',r['done']==0,r['done'])
    chk('总飞=375，不出现 380/多飞5',r['total']==375,r['total'])
    chk('分账二三待飞=375',r['catPend']==375 and r['catFly']==0,r)
    a=pg.evaluate("""()=>{autoFlyOn=true; syncAutoEmFly(); var x=getThisRoundFly(); var e=x.lines.filter(l=>l.code==='二中二/三中三合计')[0]; var L=catLedgerData(); return {full:e.full,done:e.done,booked:flownPerPos['_em_total'],cat:L.em.flown};}""")
    chk('自动飞开：二三=375，落账也清成375',a['full']==375 and a['done']==375 and a['booked']==375,a)
    chk('分账二三已飞=375',a['cat']==375,a['cat'])
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('\nSUMMARY %d/%d'%(7-len(FAIL),7)); sys.exit(1 if FAIL else 0)
