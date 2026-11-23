import asyncio, json, sys
from playwright.async_api import async_playwright

async def main():
    js = open('/tmp/recon_sim.js', encoding='utf-8').read()
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/local/bin/chromium", args=["--no-sandbox"])
        pg = await b.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto("http://127.0.0.1:8765/app-pro.html?nock=1", wait_until="load")
        await pg.wait_for_timeout(500)
        r = await pg.evaluate(js)
        s = r["summary"]
        print("version", s["version"])
        for c in s["cases"]:
            print(("PASS " if c["status"] == "PASS" else "FAIL ") + c["name"])
            if c["status"] != "PASS":
                print("   ", json.dumps(c["detail"], ensure_ascii=False)[:900])
        print("failures:", len(s["failures"]))
        if len(sys.argv) > 1:
            for k, v in r["data"].items():
                print("=====", k, {kk: v.get(kk) for kk in ("total","parts","should","thisRound","realFly","gap","payFly","riskFly","payBal","riskNet","riskCust")})
                print("PAY>>", " | ".join(v["payText"])[:400])
                print("RLINES>>", (v.get("riskLines") or [])[:6])
                print("RSK>>", " | ".join([x for x in v["riskText"] if ("已飞" in x) or ("凑整" in x) or ("自留" in x) or ("客户总赔付" in x)])[:700])
        if errs:
            print("pageerrors:", errs[:3])
        await b.close()

asyncio.run(main())
