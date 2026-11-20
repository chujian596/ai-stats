#!/usr/bin/env python3
"""浏览器端到端门禁：qa_sim + 全词库 + 混搭结算 + 23项选择对账。
用法：python3 tests/browser_gate.py
依赖：本机 chromium（/usr/local/bin/chromium）与 playwright。
"""
import json
import os
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = os.environ.get("CHROME_BIN", "/usr/local/bin/chromium")
PAGE_NAME = os.environ.get("APP_PAGE", "app-pro.html")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def start_server():
    httpd = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=ROOT)
    )
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, httpd.server_address[1]


def main():
    from playwright.sync_api import sync_playwright

    httpd, port = start_server()
    base = "http://127.0.0.1:%d/%s?nock=1&t=%d" % (port, PAGE_NAME, int(time.time()))
    checks = {}
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, executable_path=CHROME, args=["--no-sandbox"]
            )
            page = browser.new_page(viewport={"width": 420, "height": 900})
            page.set_default_timeout(120000)

            def fresh():
                page.goto(base + "&r=" + str(time.time()), wait_until="load", timeout=30000)
                page.evaluate("try{localStorage.clear()}catch(e){}")

            fresh()
            qa = page.evaluate(
                """async () => {
                const t=await (await fetch('/tests/qa_sim.js?t='+Date.now())).text();
                const R=await eval(t);
                return {version:R.version,pass:R.pass,total:(R.cases||[]).length,fail:R.fail};
            }"""
            )
            checks["qa_sim"] = qa
            if qa["pass"] != qa["total"] or qa["fail"] != 0:
                errors.append("qa_sim: %s/%s fail=%s" % (qa["pass"], qa["total"], qa["fail"]))

            fresh()
            lex = page.evaluate(
                """async () => {
                const t=await (await fetch('/tests/lexicon_full_flow.js?t='+Date.now())).text();
                const R=await eval(t);
                return {version:R.version,pass:R.summary.pass,total:R.summary.total,fail:R.summary.fail};
            }"""
            )
            checks["lexicon"] = lex
            if lex["pass"] != lex["total"] or lex["fail"] != 0:
                errors.append("lexicon: %s/%s fail=%s" % (lex["pass"], lex["total"], lex["fail"]))

            fresh()
            mix = page.evaluate(
                """async () => {
                const t=await (await fetch('/tests/settle_mixed.js?t='+Date.now())).text();
                const raw=await eval(t);
                const R=(typeof raw==='string')?JSON.parse(raw):raw;
                return {version:R.version,pass:R.summary.pass,total:R.summary.total,fail:R.summary.fail};
            }"""
            )
            checks["settle_mixed"] = mix
            if mix["pass"] != mix["total"] or mix["fail"] != 0:
                errors.append("settle_mixed: %s/%s fail=%s" % (mix["pass"], mix["total"], mix["fail"]))

            fresh()
            page.evaluate(
                """() => {
                window.__choiceQA=null;
                fetch('/tests/choice_settle_qa.js?t='+Date.now()).then(r=>r.text()).then(t=>{
                    try{eval(t)}catch(e){window.__choiceQA={err:String(e)}}
                });
                return true;
            }"""
            )
            page.wait_for_function("window.__choiceQA !== null", timeout=120000)
            choice = page.evaluate(
                """() => window.__choiceQA ? {
                tested:window.__choiceQA.tested,pass:window.__choiceQA.pass,
                fail:window.__choiceQA.fail,fails:window.__choiceQA.fails,
                err:window.__choiceQA.err||''
            } : null"""
            )
            checks["choice_settle"] = choice
            if not choice or choice.get("err") or choice["pass"] != choice["tested"] or choice["fail"] != 0:
                errors.append("choice_settle: %s" % json.dumps(choice, ensure_ascii=False))

            fresh()
            page.evaluate(
                """() => {
                window.__archiveQA=null;
                fetch('/tests/archive_audit_qa.js?t='+Date.now()).then(r=>r.text()).then(t=>{
                    try{eval(t)}catch(e){window.__archiveQA={err:String(e)}}
                });
                return true;
            }"""
            )
            page.wait_for_function("window.__archiveQA !== null", timeout=60000)
            ar = page.evaluate("() => window.__archiveQA")
            checks["archive_audit"] = {
                "total": len(ar.get("cases", [])),
                "pass": len([c for c in ar.get("cases", []) if c.get("status") == "PASS"]),
                "fail": len(ar.get("fails", [])),
                "err": ar.get("err", ""),
            }
            if ar.get("err") or ar.get("fails"):
                errors.append("archive_audit: %s" % json.dumps(ar, ensure_ascii=False))

            # 开奖按钮不能卡死：本期已结算 / 服务器给旧期，都必须把按钮解锁
            fresh()
            drawbtn = page.evaluate(
                '''async () => {
                const btn=document.getElementById('drawFetchBtn');
                const wait=ms=>new Promise(r=>setTimeout(r,ms));
                const mk=draw=>({macao:{draw:String(draw),numbers:['08','02','09','15','41','47','33']},hongkong:null});
                window.__mockDraw=323;
                window.fetch=async function(u){
                    if(String(u).indexOf('/api/draw')>=0){
                        return {ok:true,json:async()=>mk(window.__mockDraw)};
                    }
                    return {ok:false,json:async()=>({})};
                };
                localStorage.setItem(sk('lastDrawPeriod'),'323');
                autoFetchDraw();
                for(let i=0;i<40 && _drawFetchBusy;i++) await wait(25);
                const same={busy:_drawFetchBusy,disabled:btn.disabled,text:btn.textContent};
                window.__mockDraw=322;
                autoFetchDraw();
                for(let i=0;i<40 && _drawFetchBusy;i++) await wait(25);
                const older={busy:_drawFetchBusy,disabled:btn.disabled,text:btn.textContent};
                return {same:same,older:older};
            }'''
            )
            checks["draw_button"] = {
                "tested": 2,
                "pass": len([1 for k in ("same", "older") if not drawbtn[k]["busy"] and not drawbtn[k]["disabled"] and drawbtn[k]["text"] == "自动获取开奖"]),
                "fail": len([1 for k in ("same", "older") if drawbtn[k]["busy"] or drawbtn[k]["disabled"] or drawbtn[k]["text"] != "自动获取开奖"]),
                "detail": drawbtn,
            }
            if checks["draw_button"]["fail"]:
                errors.append("draw_button: %s" % json.dumps(drawbtn, ensure_ascii=False))

            browser.close()
    finally:
        httpd.shutdown()

    print(json.dumps(checks, ensure_ascii=False, indent=2))
    if errors:
        print("\n浏览器门禁失败：")
        for e in errors:
            print(" - " + e)
        return 1
    a = checks["archive_audit"]
    total = (
        checks["qa_sim"]["total"] + checks["lexicon"]["total"] +
        checks["settle_mixed"]["total"] + checks["choice_settle"]["tested"] +
        a["total"] + checks["draw_button"]["tested"]
    )
    print("\n浏览器门禁通过：QA %d/%d、词库 %d/%d、混搭 %d/%d、选择对账 %d/%d、归档/日志/诊断 %d/%d、开奖按钮 %d/%d，共 %d/%d" % (
        checks["qa_sim"]["pass"], checks["qa_sim"]["total"],
        checks["lexicon"]["pass"], checks["lexicon"]["total"],
        checks["settle_mixed"]["pass"], checks["settle_mixed"]["total"],
        checks["choice_settle"]["pass"], checks["choice_settle"]["tested"],
        a["pass"], a["total"],
        checks["draw_button"]["pass"], checks["draw_button"]["tested"],
        total, total
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
