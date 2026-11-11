#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公开论坛「文字帖」读取对账脚本（ismkog plaintext API）

与图库图纸频道、联盟站文字墙并列的第三类载体：
  - 论坛帖：详情 content 是 HTML，一行一期，自带约几十期历史与准/错标注；
    列表只给当期摘要，必须按 threadId 调详情接口取全量历史。

每条帖子登记来源路径（帖子 URL / 接口 / 访问方式 / 抓取时间 / 内容指纹），
对照官方特肖独立对账，算命中率/错误率/分类，并比对站点自标准/错。
只取澳门（macao）；只对标特号那一个生肖（特肖），不看平号平肖。

子命令：
  fetch     : 翻全部分页 -> 拉详情 -> 解析 -> 对账 -> 写 forum-snapshot.json
  reconcile : 只用已落盘详情缓存重算统计（不重新下载）
"""
import json, os, re, subprocess, sys, time, datetime, html, hashlib

BASE = "https://ismkog.xn--n8jaf0byahm4a2c4cybyssjl201en76e.xn--q9jyb4c:21044"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
ROOT = os.path.dirname(os.path.abspath(__file__))
OFFICIAL_JSON = os.path.join(ROOT, "official-history.json")
DETAIL_CACHE = os.path.join(ROOT, "forum-details-cache.json")
SNAPSHOT = os.path.join(ROOT, "forum-snapshot.json")
SUMMARY = os.path.join(ROOT, "forum-summary.json")

# 分页与详情拉取上限（防止失控；后续可放宽）
MAX_PAGES = int(os.environ.get("FORUM_MAX_PAGES", "60"))
DETAIL_CAP = int(os.environ.get("FORUM_DETAIL_CAP", "4000"))
PAGE_SIZE = 200

ZOD = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
NUM2Z = {}
for z, ns in [("马", [1, 13, 25, 37, 49]), ("蛇", [2, 14, 26, 38]), ("龙", [3, 15, 27, 39]),
              ("兔", [4, 16, 28, 40]), ("虎", [5, 17, 29, 41]), ("牛", [6, 18, 30, 42]),
              ("鼠", [7, 19, 31, 43]), ("猪", [8, 20, 32, 44]), ("狗", [9, 21, 33, 45]),
              ("鸡", [10, 22, 34, 46]), ("猴", [11, 23, 35, 47]), ("羊", [12, 24, 36, 48])]:
    for n in ns:
        NUM2Z[n] = z

KILL_RE = re.compile(r"杀|禁|亡|绝")
REC_RE = re.compile(r"肖|中特|平特")
# 非生肖维度标题（头/波/尾/段/单双/大小/五行/方位/家禽野兽等）
NONZOD_RE = re.compile(r"尾|波|头|段|单双|大小|五行|三合|东南|西北|家禽|野兽|成语|琴棋|三国|四季|风雨|雷电|天地|朝夕|日夜|男女|黑白|前后|左右|胆大|胆小|合数|两季|吉美|凶丑|文房|一行|二字|三字|六四二|吃肉|吃草|肉菜草|双波|单波|红波|蓝波|绿波")
MARK_HIT = ["准", "对", "中"]
MARK_MISS = ["错"]


def curl(url, timeout=15):
    p = subprocess.run(["curl", "-sk", "--compressed", "-m", str(timeout), "-A", UA, url],
                       capture_output=True, timeout=timeout + 5)
    return p.stdout.decode("utf-8", errors="ignore")


def fetch_json(url):
    return json.loads(curl(url))


def load_official():
    if os.path.exists(OFFICIAL_JSON):
        try:
            return json.load(open(OFFICIAL_JSON, encoding="utf-8"))
        except Exception:
            pass
    arr = fetch_json(BASE + "/api/v1/lotteries/macao/histories?year=2026")
    off = {}
    for x in arr or []:
        nums = x.get("winner_numbers") or []
        if not nums:
            continue
        sp = nums[-1]
        off[str(x["draw"])] = {"specialNum": sp, "specialZod": NUM2Z.get(sp), "all": nums}
    return off


def classify(title):
    t = title or ""
    # 杀/禁/亡/绝 且明确是「肖」才归杀肖；杀头/杀波/杀尾等非生肖维度归 other
    if KILL_RE.search(t) and "肖" in t:
        return "kill"
    if REC_RE.search(t):
        return "rec"
    return "other"


def clean_html(c):
    c = re.sub(r"<[^>]+>", "", c)
    c = html.unescape(c)
    return c.replace("開", "开").replace("鷄", "鸡").replace("錯", "错").replace("　", " ")


def parse_rows(content):
    """按期号切段，取预测生肖、开号、站点自标。返回 rows 列表。"""
    c = clean_html(content or "")
    marks = []
    for m in re.finditer(r"(\d{2,3})期", c):
        marks.append((m.start(), int(m.group(1))))
    rows = []
    for i, (pos, period) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(c)
        seg = c[pos:end]
        open_idx = seg.find("开")
        pred = seg[:open_idx] if open_idx >= 0 else seg
        zods = []
        for ch in pred:
            if ch in ZOD and ch not in zods:
                zods.append(ch)
        rm = re.search(r"开[:：]?\s*([鼠牛虎兔龙蛇马羊猴鸡狗猪])?\s*(\d{1,2})?\s*(准|对|中|错)?", seg)
        rz = rm.group(1) if rm else None
        rn = rm.group(2) if rm else None
        mk = rm.group(3) if rm else None
        rows.append({"period": period, "zods": zods, "openedZod": rz,
                      "openedNum": rn, "selfMark": mk or ""})
    # 同一期号重复出现时保留首次出现的一行，避免重复计数
    seen = set()
    deduped = []
    for r in rows:
        if r["period"] in seen:
            continue
        seen.add(r["period"])
        deduped.append(r)
    return deduped


def judge(kind, zods, off_zod):
    if not off_zod or not zods:
        return None
    if kind == "kill":
        return "miss" if off_zod in zods else "hit"
    return "hit" if off_zod in zods else "miss"


def cmd_fetch():
    official = load_official()
    print(f"官方历史 {len(official)} 期")

    # 1. 翻列表，收集帖子
    threads = {}
    page = 1
    while page <= MAX_PAGES:
        try:
            items = fetch_json(f"{BASE}/api/v1/forums?lottery=macao&page={page}&per_page={PAGE_SIZE}")
            items = items.get("data", []) if isinstance(items, dict) else items
        except Exception as e:
            print("  列表异常 page", page, e)
            break
        if not items:
            break
        new = 0
        for it in items:
            i = it["id"]
            if i in threads:
                continue
            threads[i] = {"id": i, "topic": it.get("topic") or "",
                          "draw": it.get("draw"), "year": it.get("year"),
                          "user": (it.get("user") or {}).get("nickname") or "匿名",
                          "comments": it.get("number_of_comments", 0)}
            new += 1
        print(f"  列表 page {page}: 累计 {len(threads)} 帖（本页新增 {new}）")
        if new == 0:
            break
        page += 1
        time.sleep(0.2)

    # 2. 归类，只对有生肖维度的帖子拉详情
    cache = {}
    if os.path.exists(DETAIL_CACHE):
        try:
            cache = json.load(open(DETAIL_CACHE, encoding="utf-8"))
        except Exception:
            cache = {}

    todo = [t for t in threads.values() if classify(t["topic"]) in ("kill", "rec")]
    todo.sort(key=lambda t: t["id"])
    print(f"列表共 {len(threads)} 帖；生肖类待拉详情 {len(todo)}（上限 {DETAIL_CAP}）")

    columns = []
    for n, t in enumerate(todo[:DETAIL_CAP]):
        tid = str(t["id"])
        if tid in cache:
            content = cache[tid]
        else:
            try:
                d = fetch_json(f"{BASE}/api/v1/forums/{tid}")
                dd = d.get("data", d) if isinstance(d, dict) else d
                content = dd.get("content") or ""
                cache[tid] = content
            except Exception as e:
                print("  详情异常", t["topic"], e)
                content = ""
            time.sleep(0.12)
        rows = parse_rows(content)
        kind = classify(t["topic"])
        # 标题是生肖类但正文解析不出生肖，归 other
        if not any(r["zods"] for r in rows):
            kind = "other"
        columns.append({
            "threadId": tid, "name": t["user"], "topic": t["topic"], "kind": kind,
            "sourceUrl": f"{BASE}/api/v1/forums/{tid}",
            "apiUrl": f"/api/v1/forums/{tid}",
            "fetchedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "rawSha": hashlib.sha1(content.encode("utf-8", "ignore")).hexdigest()[:10],
            "rows": rows,
        })
        if n % 50 == 0:
            json.dump(cache, open(DETAIL_CACHE, "w", encoding="utf-8"), ensure_ascii=False)

    json.dump(cache, open(DETAIL_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    reconcile(columns, official)


def missing_periods(rows, kind, official):
    """近期窗口内官方已开奖、但源站漏发的期（视为未交付/隐藏错期，计 miss）。

    窗口取最晚期号往前回溯「已发期数」那么多期（下限 10），避免早年串入期号
    或上墙只保留近几十期造成的截断把旧期误算成缺更。
    """
    if kind not in ("kill", "rec"):
        return []
    settled = [r["period"] for r in rows if r.get("officialZod")]
    if not settled:
        return []
    hi = max(settled)
    depth = len(settled)
    lo = hi - depth + 1
    off_periods = {int(k) for k, v in official.items() if v and v.get("specialZod")}
    published = set(settled)
    return sorted(p for p in off_periods if lo <= p <= hi and p not in published)


def reconcile(columns, official):
    out = []
    for c in columns:
        hit = miss = unresolved = 0
        mismatch = []
        for r in c["rows"]:
            off = official.get(str(r["period"]))
            off_zod = off["specialZod"] if off else None
            r["officialZod"] = off_zod
            v = judge(c["kind"], r["zods"], off_zod)
            r["verdict"] = v
            if v == "hit":
                hit += 1
            elif v == "miss":
                miss += 1
                if r["selfMark"] in MARK_HIT:
                    mismatch.append({"period": r["period"], "selfMark": r["selfMark"], "verdict": v})
            else:
                unresolved += 1
        # 缺更期：窗口内官方已开奖但源站没发，按未交付计错
        missing = missing_periods(c["rows"], c["kind"], official)
        miss += len(missing)
        total = hit + miss
        acc = hit / total if total > 0 else None
        miss_rate = miss / total if total > 0 else None
        expected = len([r for r in c["rows"] if r.get("officialZod")]) + len(missing)
        coverage = (expected - len(missing)) / expected if expected > 0 else None
        cls = "watch"
        if total >= 10:
            cls = "good" if (acc is not None and acc >= 0.7) else "bad"
        c.update({"hit": hit, "miss": miss, "unresolved": unresolved, "total": total,
                  "acc": round(acc, 3) if acc is not None else None,
                  "missRate": round(miss_rate, 3) if miss_rate is not None else None,
                  "cls": cls, "mismatch": mismatch,
                  "missingPeriods": missing, "missingCount": len(missing),
                  "expected": expected, "coverage": round(coverage, 3) if coverage is not None else None})
        out.append(c)

    out.sort(key=lambda x: (x["cls"] != "good", -(x["acc"] or 0)))
    snap = {
        "source": {
            "siteName": "17图库公开论坛",
            "apiBase": BASE,
            "listApi": "/api/v1/forums?lottery=macao&page={page}&per_page=200",
            "detailApi": "/api/v1/forums/{id}",
            "access": "明文 JSON，CORS *，免 token、免登录；curl -sk 直连",
            "lottery": "macao",
        },
        "fetchedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "officialCount": len(official),
        "columns": out,
    }
    json.dump(snap, open(SNAPSHOT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 精简汇总：去掉逐期明细，供手机端页面加载；全量明细留在 forum-snapshot.json 存证
    max_p = max((int(k) for k in official), default=0)
    slim = []
    for c in out:
        if c["kind"] not in ("kill", "rec"):
            continue
        # 最新一期：优先未开奖（待开）行，取距官方最新期最近者，避免跨年高期号串进来；否则取已收录最新期
        unresolved = [r for r in c["rows"] if r["verdict"] is None]
        if unresolved:
            latest = min(unresolved, key=lambda r: (abs(r["period"] - max_p), -r["period"]))
        else:
            settled = [r for r in c["rows"] if r["officialZod"]]
            latest = max(settled or c["rows"], key=lambda r: r["period"])
        slim.append({
            "threadId": c["threadId"], "name": c["name"], "topic": c["topic"], "kind": c["kind"],
            "sourceUrl": c["sourceUrl"], "apiUrl": c["apiUrl"], "fetchedAt": c["fetchedAt"],
            "rawSha": c["rawSha"], "hit": c["hit"], "miss": c["miss"], "unresolved": c["unresolved"],
            "total": c["total"], "acc": c["acc"], "missRate": c["missRate"], "cls": c["cls"],
            "mismatchCount": len(c["mismatch"]), "missingCount": c["missingCount"],
            "expected": c["expected"], "coverage": c["coverage"],
            "current": latest and {"period": latest["period"], "zods": latest["zods"],
                                   "openedZod": latest["openedZod"], "verdict": latest["verdict"]},
        })
    summary = {"source": snap["source"], "fetchedAt": snap["fetchedAt"],
               "officialCount": snap["officialCount"], "columns": slim}
    json.dump(summary, open(SUMMARY, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    g = sum(1 for c in out if c["cls"] == "good")
    b = sum(1 for c in out if c["cls"] == "bad")
    w = sum(1 for c in out if c["cls"] == "watch")
    k = sum(1 for c in out if c["kind"] == "kill")
    r = sum(1 for c in out if c["kind"] == "rec")
    print(f"对账帖子 {len(out)}（杀 {k} · 荐 {r} · 其他 {len(out)-k-r}）；准 {g} · 差 {b} · 观察 {w}")
    print(f"快照 -> {SNAPSHOT}")


def cmd_reconcile():
    snap = json.load(open(SNAPSHOT, encoding="utf-8"))
    official = load_official()
    reconcile(snap["columns"], official)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    if arg == "fetch":
        cmd_fetch()
    elif arg == "reconcile":
        cmd_reconcile()
