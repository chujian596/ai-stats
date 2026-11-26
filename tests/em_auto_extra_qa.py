import json, sys
from playwright.sync_api import sync_playwright

CHECKS=[]
def ok(name, cond, extra=''):
    CHECKS.append((name,bool(cond),extra)); print(('PASS ' if cond else 'FAIL ')+name+(('  '+str(extra)) if extra else ''))

with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':760,'height':1000})
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1',wait_until='load'); pg.wait_for_timeout(350)
    r=pg.evaluate("""()=>{
      localStorage.removeItem(sk('flownPerPos')); localStorage.removeItem(sk('flownReal')); localStorage.removeItem(sk('emExtra')); localStorage.removeItem(sk('manualFlyHistory'));
      flownPerPos={}; flownReal={};
      orders=[{id:'t1',codes:['三中三:17,20,25'],codeAmts:{'三中三:17,20,25':375},price:375}];
      hkOrders=[];
      emExtraSave([{p:selfFlyPeriod(),code:'三中三:07,15,36',amt:5,src:'三中三 07.15.36 5',ts:1}]);
      autoFlyOn=false;
      var off=getThisRoundFly(); var offEm=off.lines.filter(l=>l.code==='二中二/三中三合计')[0];
      autoFlyOn=true; syncAutoEmFly();
      var on=getThisRoundFly(); var onEm=on.lines.filter(l=>l.code==='二中二/三中三合计')[0];
      return {offAmt:offEm.amt, offFull:offEm.full, onAmt:onEm.amt, onDone:onEm.done, onFull:onEm.full, booked:flownPerPos['_em_total'], totalOff:off.totalFly, totalOn:on.totalFly};
    }""")
    ok('自动飞关闭：二三待飞=380', r['offAmt']==380 and r['offFull']==380, r)
    ok('自动飞打开：二三待飞=0', r['onAmt']==0, r)
    ok('自动飞打开：二三已飞=380', r['onDone']==380 and r['onFull']==380, r)
    ok('自动飞打开：落账 _em_total=380', r['booked']==380, r)
    ok('自动飞开关前后总飞都=380', r['totalOff']==380 and r['totalOn']==380, r)
    ok('无 JS 报错', not errs, errs)
    b.close()

failed=[c for c in CHECKS if not c[1]]
print('\nSUMMARY %d/%d' % (len(CHECKS)-len(failed), len(CHECKS)))
if failed: print('FAILS: '+json.dumps([f[0] for f in failed],ensure_ascii=False)); sys.exit(1)
