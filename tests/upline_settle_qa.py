import json, sys
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8765/app-pro.html?nock=1&cb=uplinesettle'
RES=[]; FAIL=[]
def chk(name, ok, detail=''):
    RES.append({'name':name,'status':'PASS' if ok else 'FAIL','detail':detail})
    if not ok: FAIL.append(name)
    print(('PASS  ' if ok else 'FAIL  ')+name+(' '+str(detail) if detail and not ok else ''))

def boot(pg, extra=False, em=0):
    pg.goto(URL, wait_until='load')
    pg.evaluate("()=>{localStorage.clear(); localStorage.setItem('ai_preview_enabled','0');}")
    pg.reload(wait_until='load'); pg.wait_for_timeout(300)
    pg.evaluate("""()=>{
      shop='A'; lastDraw={draw:'999',period:'999',regularNums:[1,2,3,4,5,6],specialNum:44}; _riskDraw=lastDraw;
      splitTakeAll=0; pteFlyTakeAll=0; lxFlyAmt=0;
      document.getElementById('customerName').value='测试';
      document.getElementById('input').value='特号18 100\\n平特马 100\\n连肖马鸡 100\\n三中三 08-17-25 100';
      handleSave();
    }""")
    pg.wait_for_timeout(350)
    for i in ('pvOk','mcOk'):
        el=pg.query_selector('#'+i)
        if el and el.is_visible(): el.click(); pg.wait_for_timeout(150)
    pg.evaluate("""(o)=>{
      flownReal={'18':60,'平特马':50,'连肖马鸡':200,'_em_total':100};
      flownPerPos={'18':60,'平特马':50,'连肖马鸡':200,'_em_total':100};
      localStorage.setItem(sk('flownReal'),JSON.stringify(flownReal));
      localStorage.setItem(sk('flownPerPos'),JSON.stringify(flownPerPos));
      selfFlySave([{p:'999',code:'连肖马鸡',amt:100}]);
      localStorage.setItem(sk('selfFlyMode'), o.extra?'extra':'in');
      emExtraSave(o.em?[{p:'999',code:'三中三 08-17-25',amt:o.em}]:[]);
      renderAll();
    }""", {'extra':extra,'em':em})
    pg.wait_for_timeout(400)

with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/local/bin/chromium',args=['--no-sandbox'])
    pg=b.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))

    # A：手飞已含在已飞
    boot(pg, False, 0)
    pg.evaluate("()=>upSettleOpen()"); pg.wait_for_timeout(300)
    D=pg.evaluate("()=>upSettleData()")
    txt=pg.evaluate("()=>{var w=document.getElementById('upSettleOv');return w?w.innerText:''}")
    sumfly=sum(c['fly'] for c in D['cats']); sumback=sum(c['back'] for c in D['cats'])
    detfly=sum(sum(i['amt'] for i in v) for v in D['detail'].values())
    chk('汇总四类飞额 410', sumfly==410, sumfly)
    chk('明细逐条合计＝汇总飞额', detfly==sumfly, [detfly,sumfly])
    chk('连肖手飞标注含手飞 100', '含手飞 100' in txt, txt[:60])
    copy_txt=pg.evaluate("()=>upSettleText()")
    chk('复制文本为发上家格式', '【999期上家结算】' in copy_txt and '特号：飞60，中0，净-60' in copy_txt and '合计：飞410，中90，净-320' in copy_txt, copy_txt)
    chk('复制文本不带净差说明和明细', ('净差' not in copy_txt) and ('已飞明细' not in copy_txt), copy_txt)
    chk('A 无 JS 报错', not errs, errs)

    # B：手飞另外单独飞
    errs.clear(); boot(pg, True, 0)
    pg.evaluate("()=>upSettleOpen()"); pg.wait_for_timeout(300)
    D=pg.evaluate("()=>upSettleData()")
    txt=pg.evaluate("()=>document.getElementById('upSettleOv').innerText")
    sumfly=sum(c['fly'] for c in D['cats']); detfly=sum(sum(i['amt'] for i in v) for v in D['detail'].values())
    chk('B 汇总飞额 510（含单独手飞）', sumfly==510, sumfly)
    chk('B 明细合计＝汇总', detfly==sumfly, [detfly,sumfly])
    chk('B 手飞单列一行', '手飞·连肖马鸡' in txt, '')
    chk('B 无 JS 报错', not errs, errs)

    # C：二三多飞
    errs.clear(); boot(pg, False, 40)
    pg.evaluate("()=>upSettleOpen()"); pg.wait_for_timeout(300)
    D=pg.evaluate("()=>upSettleData()")
    txt=pg.evaluate("()=>document.getElementById('upSettleOv').innerText")
    sumfly=sum(c['fly'] for c in D['cats']); detfly=sum(sum(i['amt'] for i in v) for v in D['detail'].values())
    chk('C 汇总飞额 450（含二三多飞 40）', sumfly==450, sumfly)
    chk('C 明细合计＝汇总', detfly==sumfly, [detfly,sumfly])
    chk('C 多飞逐笔列出', '多飞·' in txt and '40' in txt, '')
    chk('C 无 JS 报错', not errs, errs)
    b.close()

print('\nSUMMARY %d/%d' % (sum(1 for r in RES if r['status']=='PASS'), len(RES)))
print('FAILS:', json.dumps(FAIL, ensure_ascii=False))
json.dump(RES, open('/tmp/upline_settle_qa.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
sys.exit(1 if FAIL else 0)
