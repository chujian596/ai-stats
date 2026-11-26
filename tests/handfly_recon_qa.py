"""手飞赔回对账专项：客户连肖 100 中 350、已飞里含同号手飞 100，
风险页「自留后实际净盈亏」必须与结算明细「最终余额」一致（本例 +250）。
"""
import sys
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/app-pro.html?nock=1&cb=handflyrecon"
FAILS = []

def chk(name, cond, detail=""):
    print(("PASS " if cond else "FAIL "), name, detail)
    if not cond:
        FAILS.append({"name": name, "detail": detail})

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/local/bin/chromium", args=["--no-sandbox"])
    pg = b.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until="load")
    pg.evaluate("()=>{localStorage.clear(); localStorage.setItem('ai_preview_enabled','0');}")
    pg.reload(wait_until="load"); pg.wait_for_timeout(500)

    # 开奖号含马(01)、鸡(10)，客户连肖马鸡 100 中 3.5 倍 = 350
    pg.evaluate("""()=>{
      shop='A';
      lastDraw={draw:'999',period:'999',regularNums:[1,10,2,3,4,5],specialNum:44};
      _riskDraw=lastDraw; splitTakeAll=0; pteFlyTakeAll=0; lxFlyAmt=0;
      document.getElementById('customerName').value='测试';
      document.getElementById('input').value='连肖马鸡 100';
      handleSave();
    }""")
    pg.wait_for_timeout(400)
    for i in ('pvOk', 'mcOk'):
        el = pg.query_selector('#' + i)
        if el and el.is_visible():
            el.click(); pg.wait_for_timeout(200)

    # 已飞 200 = 客户单 100 + 同号手飞 100（手飞默认「已含在已飞」）
    pg.evaluate("""()=>{
      flownReal={'连肖马鸡':200}; flownPerPos={'连肖马鸡':200};
      localStorage.setItem(sk('flownReal'), JSON.stringify(flownReal));
      localStorage.setItem(sk('flownPerPos'), JSON.stringify(flownPerPos));
      selfFlySave([{p:'999', code:'连肖马鸡', amt:100}]);
      renderAll();
    }""")
    pg.wait_for_timeout(400)

    risk = pg.evaluate("()=>document.getElementById('riskBody').innerText")
    side = pg.evaluate("()=>{var b=document.getElementById('sideCustPay');return b?b.innerText:''}")

    chk("风险页拆出手飞赔回 350", "上家赔回·手飞" in risk and "+350" in risk, risk[-400:])
    chk("风险页客户单赔回 350", "上家赔回·客户单" in risk and "+350" in risk)
    chk("风险页上家赔回合计 700", "上家赔回合计（客户单＋手飞）" in risk and "+700" in risk)
    chk("风险页净盈亏 +250", "自留后实际净盈亏+250" in risk)
    chk("结算明细最终余额 +250", "最终余额+250.00" in side, side[-200:])
    chk("两页净盈亏一致", ("自留后实际净盈亏+250" in risk) and ("最终余额+250.00" in side))
    chk("无脚本报错", not errs, errs[:2])

    b.close()

print("\\nRESULT", "ALL PASS" if not FAILS else ("FAIL %d" % len(FAILS)))
sys.exit(0 if not FAILS else 1)
