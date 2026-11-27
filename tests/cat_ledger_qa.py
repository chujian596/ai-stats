"""分账四类专项质检：特号(含特肖) / 平特 / 连肖 / 二三
逐类录单 → 核对收单 → 确认飞单 → 核对各类已飞/待飞/自留 → 逐个目录展开 → 归档归零。
"""
import sys, datetime
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/app-pro.html?nock=1&cb=catledger"
FAILS = []

def chk(name, cond, detail=""):
    if cond:
        print("PASS ", name, detail)
    else:
        print("FAIL ", name, detail)
        FAILS.append({"name": name, "detail": detail})

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/local/bin/chromium", args=["--no-sandbox"])
    pg = b.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.evaluate("()=>{localStorage.clear(); localStorage.setItem('ai_preview_enabled','0');}")
    pg.reload(wait_until="load"); pg.wait_for_timeout(500)
    pg.evaluate("""()=>{
      shop='A';
      lastDraw={period:'330',regularNums:[45,6,46,33,31,40],specialNum:44};
      _riskDraw=lastDraw; splitTakeAll=60; pteFlyTakeAll=0; lxFlyAmt=300; lxFlyName='鸡鼠';
      autoFlyOn=true; localStorage.setItem(sk('autoFlyOn'),'1'); localStorage.setItem(sk('emFlyOn'),'1');
    }""")

    orders = [
        ('特04 100', 100), ('特05 50', 50),
        ('平特牛 300', 300), ('平特马 100', 100),
        ('连肖鸡鼠 300', 300), ('连肖马鸡 100', 100),
        ('二中二 04.19 100', 100),
        ('三中二 04.19.37 50', 50),
        ('三中三 04.19.37 10', 10),
    ]
    for q, _ in orders:
        pg.evaluate("(q)=>{document.getElementById('customerName').value='叶';document.getElementById('input').value=q;handleSave();}", q)
        pg.wait_for_timeout(320)

    pg.evaluate("()=>{switchTab('rank'); openRankSection('split');}"); pg.wait_for_timeout(500)
    L = pg.evaluate("()=>{var L=catLedgerData(); return {spec:L.spec.bet,pte:L.pte.bet,lx:L.lx.bet,em:L.em.bet};}")
    chk("四类收单：特号150", L['spec'] == 150, L)
    chk("四类收单：平特400", L['pte'] == 400, L)
    chk("四类收单：连肖400", L['lx'] == 400, L)
    chk("四类收单：二三160", L['em'] == 160, L)
    chk("四类收单合计1110", sum(L.values()) == 1110, sum(L.values()))

    # 确认飞单
    pg.evaluate("()=>confirmThisRoundFly()"); pg.wait_for_timeout(300)
    pg.evaluate("()=>{var b=document.getElementById('mcOk'); if(b)b.click()}"); pg.wait_for_timeout(900)
    pg.evaluate("()=>{_keepFlyPanel();}"); pg.wait_for_timeout(400)
    F = pg.evaluate("""()=>{var L=catLedgerData();
      return {spec:L.spec.flown,pte:L.pte.flown,lx:L.lx.flown,em:L.em.flown,
              pendSpec:L.spec.pending,pendPte:L.pte.pending,pendLx:L.lx.pending,pendEm:L.em.pending,
              sum:L.spec.flown+L.pte.flown+L.lx.flown+L.em.flown, real:totalFlownReal()};}""")
    chk("已飞：特号 40（04 飞40、05 低于阈值）", F['spec'] == 40, F)
    chk("已飞：平特 400", F['pte'] == 400, F)
    chk("已飞：连肖 300（马鸡100自留）", F['lx'] == 300, F)
    chk("已飞：二三 160", F['em'] == 160, F)
    chk("四类已飞相加 = 总飞 900", F['sum'] == 900 and F['real'] == 900, F)

    # 总表与目录
    txt = pg.evaluate("()=>{var b=document.getElementById('catLedgerBox'); return b?b.innerText:'';}")
    chk("分账总表出现", "分账总表（四类）" in txt)
    chk("总表四行齐全", all(k in txt for k in ["特号", "平特", "连肖", "二三"]))
    pg.evaluate("()=>toggleCatLedger('spec')"); pg.wait_for_timeout(250)
    t = pg.evaluate("()=>document.getElementById('catLedgerBox').innerText")
    chk("特号目录有 04 且收100/已飞40", "04" in t and "100" in t and "40" in t)
    pg.evaluate("()=>toggleCatLedger('pte')"); pg.wait_for_timeout(250)
    t = pg.evaluate("()=>document.getElementById('catLedgerBox').innerText")
    chk("平特目录有 牛/马", "牛" in t and "马" in t)
    pg.evaluate("()=>toggleCatLedger('lx')"); pg.wait_for_timeout(250)
    t = pg.evaluate("()=>document.getElementById('catLedgerBox').innerText")
    chk("连肖目录有 鸡鼠/马鸡", "鸡鼠" in t and "马鸡" in t)
    pg.evaluate("()=>toggleCatLedger('em')"); pg.wait_for_timeout(250)
    t = pg.evaluate("()=>document.getElementById('catLedgerBox').innerText")
    chk("二三目录有三条组合", "二中二" in t and "三中二" in t and "三中三" in t)

    # 特肖：按号码拆分后归入特号本
    pg.evaluate("()=>{document.getElementById('customerName').value='叶';document.getElementById('input').value='特肖虎500';handleSave();}"); pg.wait_for_timeout(400)
    pg.evaluate("()=>{var b=Array.from(document.querySelectorAll('.ai-ov button')).find(x=>x.innerText.indexOf('平分')>=0); if(b)b.click();}"); pg.wait_for_timeout(400)
    pg.evaluate("()=>{var ov=Array.from(document.querySelectorAll('.ai-ov')).find(o=>o.innerText.indexOf('刚存过')>=0); if(ov){var b=Array.from(ov.querySelectorAll('button')).find(x=>x.innerText.indexOf('确')>=0); if(b)b.click();}}"); pg.wait_for_timeout(300)
    pg.evaluate("()=>{var b=document.getElementById('pvOk'); if(b)b.click()}"); pg.wait_for_timeout(500)
    SB = pg.evaluate("()=>{var L=catLedgerData(); return [L.spec.bet, L.pte.bet, L.lx.bet, L.em.bet];}")
    chk("特肖500并入特号（总650）", SB[0] == 650 and SB[1] == 400 and SB[2] == 400 and SB[3] == 160, SB)

    # 归档：四类账全部归零，历史保留
    pg.evaluate("()=>{switchTab('orders'); billArchiveAsk();}"); pg.wait_for_timeout(300)
    pg.evaluate("()=>{var b=document.getElementById('mcOk'); if(b)b.click()}"); pg.wait_for_timeout(900)
    pg.evaluate("()=>{switchTab('rank'); _keepFlyPanel();}"); pg.wait_for_timeout(500)
    A = pg.evaluate("()=>{var L=catLedgerData(); return [L.spec.bet,L.pte.bet,L.lx.bet,L.em.bet,L.spec.flown+L.pte.flown+L.lx.flown+L.em.flown];}")
    chk("归档后四类收单归零", A[:4] == [0,0,0,0], A)
    chk("归档后四类已飞归零", A[4] == 0, A)
    chk("归档历史可打开", pg.evaluate("()=>{try{return Object.keys(billArchive||{}).length>0}catch(e){return false}}"))

    chk("全程无 JS 报错", len(errs) == 0, errs[:2])
    b.close()

print("FAILS: %s" % FAILS)
sys.exit(1 if FAILS else 0)
