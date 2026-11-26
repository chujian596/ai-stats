"""清除所有订单后，不飞标记不能残留（任何店/任何期）。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=skip',wait_until='load'); pg.wait_for_timeout(300)
    pg.evaluate("""()=>{
      localStorage.clear(); orders=[{id:'t',codes:['三中三:17,20,25'],codeAmts:{'三中三:17,20,25':375},price:375}]; hkOrders=[];
      localStorage.setItem('flySkip_shopA_330',JSON.stringify(['三中三:17,20,25','三中三:07,15,36']));
      localStorage.setItem('flySkip_shopB_331',JSON.stringify(['04']));
      clearOrders();
    }""")
    pg.wait_for_selector('#mcOk'); pg.evaluate("()=>document.getElementById('mcOk').click()"); pg.wait_for_timeout(700)
    r=pg.evaluate("""()=>{
      var keys=[]; for(var i=0;i<localStorage.length;i++){var k=localStorage.key(i); if(String(k).indexOf('flySkip_')===0) keys.push(k);}
      return {keys:keys, txt:document.getElementById('sideSplitResult')?document.getElementById('sideSplitResult').innerText:''};
    }""")
    chk('所有店/期的 flySkip_* 都清空',r['keys']==[],r['keys'])
    chk('飞单页不再出现已排除','已排除' not in r['txt'])
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('\nSUMMARY %d/%d'%(3-len(FAIL),3)); sys.exit(1 if FAIL else 0)
