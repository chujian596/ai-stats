"""清空订单后，额外目录不能还挂着一排已撤销手动批次。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=hide',wait_until='load'); pg.wait_for_timeout(300)
    r=pg.evaluate("""()=>{
      localStorage.clear(); orders=[]; hkOrders=[]; selfFlySave([]); emExtraSave([]);
      var p=selfFlyPeriod();
      var h=[
        {id:1,p:p,t:Date.now(),txt:'三中三 17-20-25',cnt:4,sum:40,batch:[],undone:true,applied:true},
        {id:2,p:p,t:Date.now(),txt:'连肖马蛇100',cnt:2,sum:200,batch:[],undone:true,applied:true},
        {id:3,p:p,t:Date.now(),txt:'三中三 17-20-25',cnt:4,sum:40,batch:[],undone:true,applied:true}
      ];
      localStorage.setItem(sk('manualFlyHistory'),JSON.stringify(h));
      return {dir:manualFlyDirHtml()};
    }""")
    chk('全撤销后额外目录不再显示3笔','3 笔' not in r['dir'],r['dir'][:80])
    chk('全撤销后不再出现已撤销字样','已撤销' not in r['dir'])
    chk('全撤销后显示本期还没有额外飞单','本期还没有额外飞单' in r['dir'])
    a=pg.evaluate("""()=>{
      var p=selfFlyPeriod();
      var h=[{id:9,p:p,t:Date.now(),txt:'连肖马蛇100',cnt:1,sum:100,batch:[{k:'连肖马蛇',amt:100}],undone:false,applied:true}];
      localStorage.setItem(sk('manualFlyHistory'),JSON.stringify(h));
      return {dir:manualFlyDirHtml()};
    }""")
    chk('有1笔有效批次仍显示1笔','1 笔' in a['dir'])
    chk('有效批次可见','连肖马蛇100' in a['dir'])
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('\nSUMMARY %d/%d'%(6-len(FAIL),6)); sys.exit(1 if FAIL else 0)
