#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图库「电脑视角」读取对账脚本（17图库 plaintext API + XOR-8 图纸解码）

流程（模拟人坐在电脑前看站点）：
  fetch     : 拉官方历史开奖 + 图库栏目清单 → 下载加扰图片 → XOR-8 解码落盘 → 写 manifest
  （识图）   : 由助手逐张读图，把读出的生肖回填到 gallery-reads.json（脚本不做 OCR）
  reconcile : 合并 reads，用官方特肖逐栏对账，算命中率/分类，写 gallery-snapshot.json

只取澳门（macao）；只对标特号那一个生肖（特肖），不看平号平肖。
"""
import json, os, re, subprocess, sys, time, datetime

BASE = "https://ismkog.xn--n8jaf0byahm4a2c4cybyssjl201en76e.xn--q9jyb4c:21044"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
ROOT = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(ROOT, "gallery-pilot")
MANIFEST = os.path.join(ROOT, "gallery-manifest.json")
READS = os.path.join(ROOT, "gallery-reads.json")
SNAPSHOT = os.path.join(ROOT, "gallery-snapshot.json")

ZOD = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
NUM2Z = {}
for z, ns in [("马", [1, 13, 25, 37, 49]), ("蛇", [2, 14, 26, 38]), ("龙", [3, 15, 27, 39]),
              ("兔", [4, 16, 28, 40]), ("虎", [5, 17, 29, 41]), ("牛", [6, 18, 30, 42]),
              ("鼠", [7, 19, 31, 43]), ("猪", [8, 20, 32, 44]), ("狗", [9, 21, 33, 45]),
              ("鸡", [10, 22, 34, 46]), ("猴", [11, 23, 35, 47]), ("羊", [12, 24, 36, 48])]:
    for n in ns:
        NUM2Z[n] = z

# 栏目归类关键词（按标题）
KILL_RE = re.compile(r"杀一肖|亡肖|禁肖|杀杀杀|爆一肖|禁两肖|绝杀|杀肖|禁一肖")
REC_RE = re.compile(r"九肖|六肖|五肖|四肖|三肖|两肖|一肖|18码|30码|36码|八码|四码|三码|两码|十码")


def curl(url, binary=False, timeout=15):
    cmd = ["curl", "-sk", "--compressed", "-m", str(timeout), "-A", UA, url]
    p = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
    data = p.stdout
    if binary:
        return data
    return data.decode("utf-8", errors="ignore")


def fetch_json(url):
    txt = curl(url)
    return json.loads(txt)


def classify(topic):
    if KILL_RE.search(topic or ""):
        return "kill"
    if REC_RE.search(topic or ""):
        return "rec"
    return ""


def decode_image(raw):
    """XOR-8：前 8 字节密钥，后续字节按密钥循环异或。返回 (ext, bytes)。"""
    if len(raw) <= 8:
        return None, None
    key = raw[:8]
    payload = raw[8:]
    out = bytes(payload[u] ^ key[u % 8] for u in range(len(payload)))
    if out[:3] == b"\xff\xd8\xff":
        ext = "jpg"
    elif out[:4] == b"\x89PNG":
        ext = "png"
    elif out[:4] == b"GIF8":
        ext = "gif"
    else:
        ext = "bin"
    return ext, out


def load_official():
    arr = fetch_json(BASE + "/api/v1/lotteries/macao/histories?year=2026")
    off = {}
    for x in arr or []:
        nums = x.get("winner_numbers") or []
        if not nums:
            continue
        sp = nums[-1]
        off[x["draw"]] = {"specialNum": sp, "specialZod": NUM2Z.get(sp), "all": nums}
    return off


def full_url(thumb):
    return thumb.replace("/epy/thumb/", "/epy/gallery/") if "/epy/thumb/" in thumb else thumb


def cmd_fetch():
    os.makedirs(IMG_DIR, exist_ok=True)
    official = load_official()
    print(f"官方历史 {len(official)} 期")

    records = []
    page = 1
    while True:
        d = fetch_json(f"{BASE}/api/v1/forums/galleries/macao?page={page}&per_page=50")
        items = d if isinstance(d, list) else d.get("data", [])
        if not items:
            break
        for it in items:
            kind = classify(it.get("topic", ""))
            if not kind:
                continue
            imgs = it.get("images") or []
            if not imgs:
                continue
            records.append({
                "id": it["id"], "topic": it["topic"], "kind": kind,
                "draw": it.get("draw"), "year": it.get("year"),
                "thumb": imgs[0], "img": "", "officialZod": official.get(it.get("draw"), {}).get("specialZod"),
            })
        page += 1
        if page > 12:
            break
        time.sleep(0.3)

    # 逐条调详情，取全尺寸图（列表缩略图 hash 与详情不一致，直接替换会拿到占位图）
    for rec in records:
        try:
            d = fetch_json(f"{BASE}/api/v1/forums/galleries/{rec['id']}")
            imgs = d.get("images") or []
            if imgs:
                rec["thumb"] = imgs[0]
        except Exception as e:
            print("  详情异常", rec["topic"], e)
        time.sleep(0.15)

    # 下载 + 解码落盘
    for rec in records:
        try:
            raw = curl(rec["thumb"], binary=True)
            ext, out = decode_image(raw)
            if not out or len(out) < 500:
                print("  解码/占位", rec["topic"], len(out) if out else 0)
                continue
            fn = f"{rec['draw']}_{rec['id']}.{ext}"
            with open(os.path.join(IMG_DIR, fn), "wb") as f:
                f.write(out)
            rec["img"] = f"gallery-pilot/{fn}"
        except Exception as e:
            print("  下载异常", rec["topic"], e)

    manifest = {"fetchedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "officialCount": len(official), "records": records}
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    reads = {}
    if os.path.exists(READS):
        reads = json.load(open(READS, encoding="utf-8"))
    print(f"栏目 {len(records)} 条；已解码 {sum(1 for r in records if r['img'])} 张；manifest -> {MANIFEST}")


def judge(kind, zods, off_zod):
    if not off_zod:
        return None
    if kind == "kill":
        return "miss" if off_zod in zods else "hit"
    return "hit" if off_zod in zods else "miss"


def cmd_reconcile():
    man = json.load(open(MANIFEST, encoding="utf-8"))
    reads = json.load(open(READS, encoding="utf-8")) if os.path.exists(READS) else {}
    cols = {}
    for rec in man["records"]:
        rd = reads.get(str(rec["id"])) or {}
        zods = rd.get("zods") or []
        if not zods:
            continue
        j = judge(rec["kind"], zods, rec["officialZod"])
        c = cols.setdefault(rec["topic"], {"topic": rec["topic"], "kind": rec["kind"],
                                           "hit": 0, "miss": 0, "unresolved": 0, "rows": []})
        if j == "hit":
            c["hit"] += 1
        elif j == "miss":
            c["miss"] += 1
        else:
            c["unresolved"] += 1
        c["rows"].append({"draw": rec["draw"], "zods": zods,
                          "officialZod": rec["officialZod"], "judge": j})

    columns = []
    for c in cols.values():
        total = c["hit"] + c["miss"]
        acc = c["hit"] / total if total > 0 else None
        cls = "watch"
        if total >= 10:
            cls = "good" if (acc is not None and acc >= 0.7) else "bad"
        c["total"] = total
        c["acc"] = round(acc, 3) if acc is not None else None
        c["cls"] = cls
        columns.append(c)
    columns.sort(key=lambda x: (x["cls"] != "good", -(x["acc"] or 0)))

    snap = {"fetchedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "officialCount": man.get("officialCount", 0), "columns": columns}
    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)

    g = sum(1 for c in columns if c["cls"] == "good")
    b = sum(1 for c in columns if c["cls"] == "bad")
    w = sum(1 for c in columns if c["cls"] == "watch")
    print(f"对账栏目 {len(columns)}：准 {g} · 差 {b} · 观察 {w}；快照 -> {SNAPSHOT}")
    for c in columns:
        pct = f"{round(c['acc']*100)}%" if c["acc"] is not None else "—"
        print(f"  [{c['cls']}] {c['topic']} 中{c['hit']} 错{c['miss']} 待{c['unresolved']} {pct}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arg in ("fetch", "all"):
        cmd_fetch()
    if arg in ("reconcile", "all"):
        cmd_reconcile()
