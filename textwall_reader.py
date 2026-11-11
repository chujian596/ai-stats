#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联盟站「文字墙」读取解码对账脚本（4901996 / h3.wanpz.com 静态 JS）

与图库图纸频道是两类载体：
  - 图库频道：content 空，只给 XOR 加扰图片，需识图（见 gallery_reader.py）。
  - 本脚本：栏目正文是静态 JS，atob(b64) -> JSON -> html 二次 JSON，明文 HTML 一行一期，
    自带约 20 期历史与准/错标注；静态 JS 裸 curl 直连，不随页面首屏滑块。

每条栏目都登记来源路径（页面 URL / JS URL / 访问方式 / 解码方式 / 抓取时间 / 原始字节），
便于复查是否改料、是否靠谱、命中率与错误率。对账只对标澳门特号特肖。

子命令：
  fetch     : 拉全部 ruleId 的 JS -> 解码解析 -> 对照官方特肖 -> 写 textwall-snapshot.json
  reconcile : 只用已落盘的解析结果重算统计（不重新下载）
"""
import json, os, re, subprocess, sys, time, datetime, base64, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(ROOT, "textwall-rules.json")
SNAPSHOT = os.path.join(ROOT, "textwall-snapshot.json")
OFFICIAL_JSON = os.path.join(ROOT, "official-history.json")

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
OFFICIAL_BASE = "https://ismkog.xn--n8jaf0byahm4a2c4cybyssjl201en76e.xn--q9jyb4c:21044"

# 站点来源登记（同一套引擎可能套娃多个镜像站；新增站点在此追加）
SOURCE = {
    "siteName": "澳门大联盟 4901996",
    "pageHost": "https://yyaann490137.4901996gg.app:8450",
    "siteNo": "490137",
    "jsBase": "https://h3.wanpz.com/script/490137",
    "pagePattern": "{pageHost}/book-detail?ruleId={ruleId}&lotteryType=1",
    "jsPattern": "{jsBase}/dynamic_{ruleId}_1.js",
    "access": "静态 JS，curl -sk 直连、免 token、免登录；页面首屏有滑块拼图，但数据 JS 不随滑块",
    "decode": "JS 体 var G_xxx=JSON.parse(__ras(atob('<b64>')))；base64 解码得 JSON，html 字段为二次 JSON 串需再 json.loads；__ras 本族实测恒等",
    "captcha": "浏览器首访页面需人工过滑块；数据 JS 可裸 curl 复查",
    "lottery": "macao",
}

ZOD = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
NUM2Z = {}
for z, ns in [("马", [1, 13, 25, 37, 49]), ("蛇", [2, 14, 26, 38]), ("龙", [3, 15, 27, 39]),
              ("兔", [4, 16, 28, 40]), ("虎", [5, 17, 29, 41]), ("牛", [6, 18, 30, 42]),
              ("鼠", [7, 19, 31, 43]), ("猪", [8, 20, 32, 44]), ("狗", [9, 21, 33, 45]),
              ("鸡", [10, 22, 34, 46]), ("猴", [11, 23, 35, 47]), ("羊", [12, 24, 36, 48])]:
    for n in ns:
        NUM2Z[n] = z

KILL_RE = re.compile(r"杀|亡|禁|绝|稳杀")
REC_RE = re.compile(r"肖|码|中特|平特")
# 非生肖维度标题（读不出生肖或本就不是肖）
NONZOD_RE = re.compile(r"尾|波|头|段|单双|大小|五行|三合|东南|西北|家禽|野兽|成语|琴棋|三国|四季|风雨|雷电|天地|朝夕|日夜|男女|黑白|前后|左右|胆大|胆小|合数|两季|吉美|凶丑|文房|买啥|一行|二字|三字|六四二|吃肉|吃草|肉菜草")

TAG_RE = re.compile(r"<[^>]+>")


def curl(url, timeout=15):
    p = subprocess.run(["curl", "-sk", "--compressed", "-m", str(timeout), "-A", UA, url],
                       capture_output=True, timeout=timeout + 5)
    return p.stdout.decode("utf-8", errors="ignore")


def load_official():
    """官方历史：{期号int: {specialNum, specialZod, all}}。优先本地缓存，缺失再拉。"""
    if os.path.exists(OFFICIAL_JSON):
        try:
            return json.load(open(OFFICIAL_JSON, encoding="utf-8"))
        except Exception:
            pass
    arr = json.loads(curl(OFFICIAL_BASE + "/api/v1/lotteries/macao/histories?year=2026"))
    off = {}
    for x in arr or []:
        nums = x.get("winner_numbers") or []
        if not nums:
            continue
        sp = nums[-1]
        off[str(x["draw"])] = {"specialNum": sp, "specialZod": NUM2Z.get(sp), "all": nums}
    json.dump(off, open(OFFICIAL_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return off


def decode_js(raw):
    """从 JS 体取 b64 -> JSON；返回 dict（含 html 或 data 结构化行）。失败返回 None。"""
    m = re.search(r"atob\('([A-Za-z0-9+/=]+)'", raw)
    if not m:
        return None
    try:
        j = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
    except Exception:
        return None
    if isinstance(j, dict) and "html" in j:
        h = j["html"]
        if isinstance(h, str) and h.startswith('"'):
            h = json.loads(h)
        j["html"] = h
    return j


def clean_title(h):
    m = re.search(r'ny-title">(.*?)</div>', h, re.S)
    t = TAG_RE.sub("", m.group(1)) if m else ""
    return re.sub(r"\s+", " ", t).strip()


def parse_rows(h):
    """解析 HTML 行 -> [{period, zods, openedText, openedZod, selfMark}]。"""
    rows = []
    for li in re.findall(r"<li[^>]*>(.*?)</li>", h, re.S):
        mp = re.search(r"(\d+)期", li)
        if not mp:
            continue
        period = int(mp.group(1))
        mo = re.search(r"开[:：]\s*<span[^>]*>([^<]+)</span>", li)
        opened_text = mo.group(1).strip() if mo else ""
        opened_zod = next((z for z in ZOD if z in opened_text), None)
        if "？" in opened_text or "?" in opened_text:
            opened_zod = None
        # 生肖取「开:」之前所有 span 里的生肖字（部分栏生肖在 <i> 外，如三肖+五码）
        pick_part = li.split("开")[0]
        zods = [s for s in re.findall(r"<span[^>]*>([^<]+)</span>", pick_part) if s in ZOD]
        self_mark = "准" if "准" in li else ("错" if "错" in li else "")
        rows.append({"period": period, "zods": zods, "openedText": opened_text,
                     "openedZod": opened_zod, "selfMark": self_mark})
    return rows


def classify(title):
    if KILL_RE.search(title or ""):
        return "kill"
    if REC_RE.search(title or ""):
        return "rec"
    return "other"


def judge(kind, zods, off_zod):
    if not off_zod or not zods:
        return None
    if kind == "kill":
        return "miss" if off_zod in zods else "hit"
    return "hit" if off_zod in zods else "miss"


def fetch_all():
    rules = json.load(open(RULES, encoding="utf-8"))
    official = load_official()
    prev = {}
    if os.path.exists(SNAPSHOT):
        try:
            old = json.load(open(SNAPSHOT, encoding="utf-8"))
            prev = {c["ruleId"]: {r["period"]: r["zods"] for r in c["rows"]} for c in old.get("columns", [])}
        except Exception:
            prev = {}

    columns = []
    for rule_id, link_title in rules.items():
        js_url = SOURCE["jsPattern"].format(jsBase=SOURCE["jsBase"], ruleId=rule_id)
        page_url = SOURCE["pagePattern"].format(pageHost=SOURCE["pageHost"], ruleId=rule_id)
        raw = curl(js_url)
        j = decode_js(raw)
        col = {"ruleId": rule_id, "title": link_title, "sourceUrl": page_url, "jsUrl": js_url,
               "access": SOURCE["access"], "decode": SOURCE["decode"], "siteNo": SOURCE["siteNo"],
               "fetchedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               "rawBytes": len(raw), "rawSha": hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()[:10],
               "rows": []}
        if not j or "html" not in j:
            col["kind"] = "other"
            col["note"] = "JS 无 html 正文"
            col.update({"hit": 0, "miss": 0, "unresolved": 0, "total": 0, "acc": None,
                        "missRate": None, "cls": "watch", "changed": False, "changedPeriods": [],
                        "mismatch": []})
            columns.append(col)
            continue

        h = j["html"]
        title = clean_title(h) or link_title
        col["title"] = title
        col["kind"] = classify(title)
        rows = parse_rows(h)

        changed_periods = []
        old_rows = prev.get(rule_id, {})
        for r in rows:
            off = official.get(str(r["period"]))
            off_zod = off["specialZod"] if off else None
            verdict = judge(col["kind"], r["zods"], off_zod)
            r["officialZod"] = off_zod
            r["verdict"] = verdict
            # 改料复查：历史期生肖与上次快照不一致
            if r["period"] in old_rows and old_rows[r["period"]] != r["zods"]:
                changed_periods.append({"period": r["period"], "before": old_rows[r["period"]], "after": r["zods"]})
            col["rows"].append(r)

        col["changed"] = bool(changed_periods)
        col["changedPeriods"] = changed_periods

        # 统计
        hit = sum(1 for r in col["rows"] if r["verdict"] == "hit")
        miss = sum(1 for r in col["rows"] if r["verdict"] == "miss")
        unresolved = sum(1 for r in col["rows"] if r["verdict"] is None)
        total = hit + miss
        acc = hit / total if total else None
        miss_rate = miss / total if total else None
        col.update({"hit": hit, "miss": miss, "unresolved": unresolved, "total": total,
                    "acc": round(acc, 3) if acc is not None else None,
                    "missRate": round(miss_rate, 3) if miss_rate is not None else None})
        col["cls"] = "watch"
        if total >= 10:
            col["cls"] = "good" if (acc is not None and acc >= 0.7) else "bad"
        # 站点自标与独立对账不一致的期（靠谱度参考）
        col["mismatch"] = [{"period": r["period"], "selfMark": r["selfMark"], "verdict": r["verdict"]}
                           for r in col["rows"] if r["selfMark"] and r["verdict"]
                           and ((r["selfMark"] == "准" and r["verdict"] == "miss")
                                or (r["selfMark"] == "错" and r["verdict"] == "hit"))]
        if NONZOD_RE.search(title) or not any(r["zods"] for r in rows):
            col["nonZodiac"] = True
        columns.append(col)
        time.sleep(0.15)

    snap = {"fetchedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "officialCount": len(official), "source": SOURCE, "columns": columns}
    json.dump(snap, open(SNAPSHOT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    report(snap)


def report(snap):
    cols = snap["columns"]
    kill = [c for c in cols if c["kind"] == "kill"]
    rec = [c for c in cols if c["kind"] == "rec"]
    g = sum(1 for c in cols if c["cls"] == "good")
    b = sum(1 for c in cols if c["cls"] == "bad")
    w = sum(1 for c in cols if c["cls"] == "watch")
    print(f"栏目 {len(cols)}（杀肖 {len(kill)} / 推荐 {len(rec)} / 其他 {len(cols)-len(kill)-len(rec)}）；"
          f"官方历史 {snap['officialCount']} 期；准 {g} · 差 {b} · 观察 {w}")
    for c in cols:
        if c["kind"] == "other":
            continue
        pct = f"{round(c['acc']*100)}%" if c["acc"] is not None else "—"
        flag = " 改料!" if c.get("changed") else ""
        mm = f" 自标不符{len(c['mismatch'])}" if c.get("mismatch") else ""
        print(f"  [{c['cls']}] {c['title']} 中{c['hit']} 错{c['miss']} 待{c['unresolved']} {pct}{flag}{mm}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    if arg == "fetch":
        fetch_all()
    else:
        snap = json.load(open(SNAPSHOT, encoding="utf-8"))
        report(snap)
