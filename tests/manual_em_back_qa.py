"""手飞二三命中：赔回也要进 flyBook，不能只算客户单的三中三。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else '')); FAIL.append(n) if not c else None
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/app-pro.html?nock=1&cb=meb',wait_until='load'); pg.wait_for_timeout(400)
    def run(undone=False):
        return pg.evaluate("""(undone)=>{
          localStorage.clear(); var pp=selfFlyPeriod();
          orders=[{id:'c1',customer:'散客',raw:'三中三 12.24.48 各375',lines:[],price:375,qty:1,amount:375,
            codes:['三中三:12,24,48'],codeAmts:{'三中三:12,24,48':375},createdAt:'2026/11/27 04:50:00',originShop:'A'}];
          hkOrders=[]; flownPerPos={'_em_total':415}; flownReal={'_em_total':415};
          localStorage.setItem(sk('manualFlyHistory'),JSON.stringify([{id:1,p:pp,txt:'三中三 12.24.33 各组10',
            batch:[{k:'_em_total',amt:40}],plan:[1,2,3,4].map(function(i){return {k:'_em_total',amt:10,line:'三中三 12.24.33 各组10'};}),
            applied:true,undone:undone}]));
          var d={specialNum:'01',regularNums:[12,24,33]};
          var FB=flyBook(d); return {em:FB.em,back:FB.emBack,manual:manualEmWinBack(d)};
        }""",undone)
    r=run(False); chk('手飞二三命中赔回=24000',r['back']==24000,r); chk('手飞二三金额仍=415',r['em']==415,r['em'])
    r2=run(True); chk('撤销批次不计赔回',r2['back']==0 and r2['manual']==0,r2)
    chk('无 JS 报错',not errs,errs[:2])
    b.close()
print('FAILS',len(FAIL)); sys.exit(1 if FAIL else 0)
