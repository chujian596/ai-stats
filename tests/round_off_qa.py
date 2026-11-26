"""凑整关掉时 375 不能显示 380；开时才允许 380。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=round',wait_until='load'); pg.wait_for_timeout(300)
    r=pg.evaluate("""()=>{
      localStorage.clear(); orders=[{id:'t',codes:['三中三:17,20,25'],codeAmts:{'三中三:17,20,25':375},price:375}]; hkOrders=[];
      localStorage.setItem(sk('flyRoundOn'),'0');
      var off=getThisRoundFly(); var line=off.lines.filter(l=>l.code==='二中二/三中三合计')[0];
      var p=buildFlyGroups(off.lines.filter(l=>l.amt>0.01),false);
      return {show:flyShowAmt(375),line:line.amt,showSum:p.showSum,groupAmt:p.groups[0].amt};
    }""")
    chk('凑整关：flyShowAmt(375)=375',r['show']==375,r)
    chk('凑整关：总飞行=375',r['line']==375,r['line'])
    chk('凑整关：目录合计=375',r['showSum']==375,r['showSum'])
    chk('凑整关：档位=375',r['groupAmt']==375,r['groupAmt'])
    a=pg.evaluate("""()=>{localStorage.setItem(sk('flyRoundOn'),'1'); return {show:flyShowAmt(375),showSum:buildFlyGroups(getThisRoundFly().lines.filter(l=>l.amt>0.01),false).showSum};}""")
    chk('凑整开：375才显示380',a['show']==380 and a['showSum']==380,a)
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('\nSUMMARY %d/%d'%(6-len(FAIL),6)); sys.exit(1 if FAIL else 0)
