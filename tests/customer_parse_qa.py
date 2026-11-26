"""客户版：三中三复式各种写法实际保存都必须是11码/165组/165元；凑整默认关，375不显示380。"""
import sys
from playwright.sync_api import sync_playwright
FAIL=[]
def chk(n,c,d=''):
    print(('PASS ' if c else 'FAIL ')+n+(('  '+str(d)) if d else ''))
    if not c: FAIL.append(n)
TEXTS=[
 '三中三复式12 24 48 02 14 26 18 42 03 27 39 各1',
 '12, 24, 48, 02, 14, 26, 18, 42, 03, 27, 39三中三复式各组1',
 '12, 24, 48, 02, 14, 26, 18, 42, 三中三:03,27,39 复式各组1',
]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    for idx,t in enumerate(TEXTS,1):
        pg=b.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.goto('http://127.0.0.1:8765/app.html?nock=1&cb=cust'+str(idx),wait_until='load'); pg.wait_for_timeout(700)
        pg.evaluate("()=>{localStorage.clear();orders=[];hkOrders=[];}")
        pg.fill('#input',t); pg.evaluate("()=>handleSave()")
        try:
            pg.wait_for_selector('text=确认保存',timeout=5000)
            preview=pg.locator('body').inner_text()
            has165=('165项' in preview and '165.00' in preview and '40.00' not in preview)
            pg.get_by_text('确认保存',exact=True).click(); pg.wait_for_timeout(600)
            r=pg.evaluate("()=>({n:orders.length,total:orders.reduce((s,o)=>s+(o.price||0),0),codes:(orders[0]||{}).codes?orders[0].codes.length:0})")
            chk('写法%d预览165元、不是40'%idx,has165,preview[:80])
            chk('写法%d实际入账165元/165组'%idx,r['n']==1 and r['total']==165 and r['codes']==165,r)
            chk('写法%d无 JS 报错'%idx,not errs,errs[:2])
        except Exception as e:
            chk('写法%d能保存'%idx,False,str(e)[:80])
        pg.close()
    pg=b.new_page(); pg.goto('http://127.0.0.1:8765/app.html?nock=1&cb=custfly',wait_until='load'); pg.wait_for_timeout(300)
    f=pg.evaluate("""()=>{localStorage.clear(); return {fresh:flyShowAmt(375), on:(localStorage.setItem(sk('flyRoundOn'),'1'),flyShowAmt(375)), off:(localStorage.setItem(sk('flyRoundOn'),'0'),flyShowAmt(375))};}""")
    chk('客户版默认凑整关：375=375',f['fresh']==375,f)
    chk('客户版开凑整才显示380',f['on']==380,f['on'])
    chk('客户版关凑整恢复375',f['off']==375,f['off'])
    pg.close(); b.close()
print('\nSUMMARY %d/%d'%(11-len(FAIL),11)); sys.exit(1 if FAIL else 0)
