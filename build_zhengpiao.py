# -*- coding: utf-8 -*-
"""正票自动出下一期：开奖数据进 official-history 后，重算 q 期纯正票并写回页面。

口径已与 323 期线上页对齐：
  方向兵 249 + 弱战区 1393 = 1642；触发 103；有效票 824；池均 8.0。
  前 18 名、票数、四档与线上 323 期完全一致。

用法：
  python3 build_zhengpiao.py              # 默认：official-history 最新一期 + 1
  python3 build_zhengpiao.py --target 323 # 指定期（用于复算校验）
  python3 build_zhengpiao.py --check 323  # 只复算并对比当前页面，不写文件

数据链：
  ai-stats/official-history.json
    -> 家族系统_320_vault2 引擎副本（补 304 期以后序列）
    -> 罗盘合成板 ALLC / 正票两军投票
    -> ai-stats/data/zhengpiao-<期>.json + zhengpiao.html 内联 DATA
"""
import argparse, csv, datetime, io, json, os, re, shutil, sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(ROOT)
FAMILY = os.path.join(PROJECT, "家族系统", "家族系统_320_vault2")
WORK = os.environ.get("ZP_ENGINE_WORK", "/tmp/zp_engine")
PAGE = os.path.join(ROOT, "zhengpiao.html")
DATA_DIR = os.path.join(ROOT, "data")
HISTORY = os.path.join(ROOT, "official-history.json")

Z = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
RED = {1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46}
BLUE = {3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48}
# 农历年段：春节换肖
CNY = {
    2024: (2, 10, "龙年"), 2025: (1, 29, "蛇年"), 2026: (2, 17, "马年"),
    2027: (2, 6, "羊年"), 2028: (1, 26, "猴年"), 2029: (2, 13, "鸡年"),
}


def seg_of(d):
    y = d.year
    if y in CNY and (d.month, d.day) >= CNY[y][:2]:
        return CNY[y][2]
    if (y - 1) in CNY:
        return CNY[y - 1][2]
    # 兜底：按 2026 马年线性推
    base = Z.index("马")
    return Z[(base + (y - 2026)) % 12] + "年"


def zodiac(n, seg):
    return Z[(Z.index(seg[0]) - (n - 1) % 12) % 12]


def wave(n):
    return "红" if n in RED else ("蓝" if n in BLUE else "绿")


def load_history():
    raw = json.load(open(HISTORY, encoding="utf-8"))
    return {int(k): v for k, v in raw.items()}


def sync_draw_latest(hist):
    """draw-latest 已更新、official-history 还没补时，先把最新一期接进来。"""
    p = os.path.join(ROOT, "draw-latest.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8")).get("macao") or {}
    q = int(d.get("draw") or 0)
    nums = d.get("numbers") or []
    if q and q not in hist and len(nums) == 7:
        dt = datetime.datetime.fromisoformat(d.get("drawn_at", "")).date() if d.get("drawn_at") else datetime.date.today()
        seg = seg_of(dt)
        hist[q] = {"specialNum": nums[6], "specialZod": zodiac(nums[6], seg), "all": nums}
        return q
    return None


def append_sequence(hist, seq_path):
    rows = list(csv.reader(open(seq_path, encoding="utf-8-sig")))
    last_q = int(rows[-1][1])
    last_date = datetime.date.fromisoformat(rows[-1][2])
    added = 0
    for q in range(last_q + 1, max(hist) + 1):
        rec = hist.get(q)
        if not rec:
            raise SystemExit(f"official-history 缺 {q} 期，无法出下一期")
        d = last_date + datetime.timedelta(days=q - last_q)
        seg = seg_of(d)
        alln = rec["all"]
        ping = " ".join(f"{n:02d}{zodiac(n, seg)}" for n in alln[:6])
        te = alln[6]
        rows.append(["2026" if d.year == 2026 else str(d.year), str(q), d.isoformat(),
                     seg, ping, f"{te:02d}{zodiac(te, seg)}"])
        added += 1
    if added:
        with open(seq_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
    return added


def ensure_engine():
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    shutil.copytree(FAMILY, WORK)
    seq = os.path.join(WORK, "01_数据", "943期序列数据.csv")
    added = append_sequence(load_history(), seq)
    return seq, added


def run_engine(target_date):
    """在引擎副本里跑罗盘合成板，返回 g（ALLC/orders/投票结果都在里面）。"""
    src_path = os.path.join(WORK, "13_罗盘", "罗盘合成板.py")
    src = open(src_path, encoding="utf-8").read()
    old_argv = sys.argv[:]
    sys.argv = ["罗盘合成板.py", target_date.isoformat()]
    g = {"__name__": "__main__", "__file__": src_path}
    buf = io.StringIO()
    try:
        with __import__("contextlib").redirect_stdout(buf):
            exec(compile(src, src_path, "exec"), g)
    finally:
        sys.argv = old_argv
    return g


def tally(g):
    ALLC = g["ALLC"]
    poolset = g["poolset"]
    f = g["N0"]  # 预测帧：q 期，使用 q-1 数据
    army = g["b3"]["兵册"] + g["b5"]["兵册"]  # 249 + 1393 = 1642
    votes = Counter()
    trig = valid = empty = 0
    pools = set()
    for s in army:
        m = ALLC.get(s["条件"])
        if m is None or not m[f]:
            continue
        trig += 1
        p = poolset(s["格"], f)
        if not p:
            empty += 1
            continue
        valid += len(p)
        pools.add(frozenset(p))
        w = s.get("票权", 1) or 1
        for n in p:
            votes[n] += w
    return votes, {
        "兵": len(army), "触发": trig, "有效票": valid,
        "池均": round(valid / trig, 1) if trig else 0.0,
        "空池": empty, "异常": 0, "池集数": len(pools),
    }


def make_ranking(votes, target_date):
    seg = seg_of(target_date)
    rows = []
    ranked = sorted(range(1, 50), key=lambda n: (-votes.get(n, 0), n))
    for i, n in enumerate(ranked, 1):
        tier = 12 if i <= 12 else 14 if i <= 14 else 16 if i <= 16 else 18 if i <= 18 else 0
        rows.append({"名": i, "号": n, "票": float(votes.get(n, 0)),
                     "正": float(votes.get(n, 0)), "反": 0.0, "钉": False,
                     "波": wave(n), "肖": zodiac(n, seg), "档": tier})
    return rows


def build_data(g, votes, stats, hist, target):
    last_q = max(k for k in hist if k < target)
    last = hist[last_q]
    last_date = None
    # 从引擎序列取日期
    seq = list(csv.reader(open(os.path.join(WORK, "01_数据", "943期序列数据.csv"), encoding="utf-8")))
    for r in seq:
        if r[1].isdigit() and int(r[1]) == last_q and r[0] == "2026":
            last_date = datetime.date.fromisoformat(r[2])
    if last_date is None:
        last_date = target - datetime.timedelta(days=1)

    rows = make_ranking(votes, last_date + datetime.timedelta(days=target - last_q))
    target_date = last_date + datetime.timedelta(days=target - last_q)
    tiers = {
        "12": [r["号"] for r in rows[:12]],
        "14": [r["号"] for r in rows[:14]],
        "16": [r["号"] for r in rows[:16]],
        "18": [r["号"] for r in rows[:18]],
    }
    # 特码后：历史上特码相同的期，下一期平码/生肖/特码频次
    post = post_special(g, last["all"][6])
    # 往年今日
    past = past_today(g, target_date, target)
    # 上期体质：用当前页面（上一期票）算命中
    prev = current_page_data()
    physique = physique_of(prev, last_q, last["all"][6])
    reg = update_registry(prev, last_q, last_date, last["all"][6])

    return {
        "期": target, "日期": target_date.isoformat(),
        "上一期": {"期": last_q, "日期": last_date.isoformat(),
                   "特码": last["all"][6], "生肖": last["specialZod"], "波色": wave(last["all"][6])},
        "四档": tiers, "钉死码": [], "钉死作用档": "仅显示·不剔除",
        "口径": "纯正票（正向1642 · 反0 · 正票序）· 逐期截断序列+当期条件库、用 q-1 帧（空占位）出 q 期票的滚动口径 · 样本以流水为准",
        "排行": rows,
        "统计": {**stats, "条件数": prev.get("统计", {}).get("条件数", len(g["ALLC"])),
                 "池集数": prev.get("统计", {}).get("池集数", stats["池集数"])},
        "特码后": post, "往年今日": past,
        "偏向": prev.get("偏向", {}),
        "上期体质": physique,
        "口径说明": prev.get("口径说明", {
            "滚动口径": "逐期截断序列 + 当期条件库，用 q-1 帧（空占位）出 q 期票",
            "旧口径": "旧页错位口径已作废", "四档": "T12/T14/T16/T18"}),
        "四档登记": reg,
        "生成": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def post_special(g, special):
    orders, segs = g["orders"], g["segs"]
    N = len(orders)
    pingc, zodiacc, nextc = Counter(), Counter(), Counter()
    sample = 0
    # 只统计“后面确实还有一期实际开奖”的样本，排除最后一期与预测帧
    for i in range(g["N0"] - 1):
        if orders[i][6] != special:
            continue
        sample += 1
        for n in orders[i + 1][:6]:
            pingc[n] += 1
            zodiacc[zodiac(n, segs[i + 1])] += 1
        nextc[orders[i + 1][6]] += 1
    ping = [{"号": n, "次": c, "肖": zodiac(n, segs[-1]), "波": wave(n)}
            for n, c in sorted(pingc.items(), key=lambda x: -x[1])]
    zc = [{"肖": z, "次": c} for z, c in sorted(zodiacc.items(), key=lambda x: -x[1])]
    nc = [{"号": n, "次": c} for n, c in sorted(nextc.items(), key=lambda x: -x[1])[:10]]
    return {"特码": special, "样本": sample, "平码": ping, "生肖": zc, "下期特码": nc}


def past_today(g, target_date, target_period):
    # 用 2021-2023 开荒 + 2024 以后序列重建日期表
    recs = []
    raw = json.load(open(os.path.join(WORK, "原版军火库", "开荒三年全字段.json"), encoding="utf-8"))
    for y in ("2021", "2022", "2023"):
        for r in raw[y]:
            recs.append((int(r["date"][:4]), int(r["date"][5:7]), int(r["date"][8:10]),
                         int(r["q"]), r["date"], " ".join(f"{p['n']:02d}{p['z']}" for p in r["ping"]),
                         f"{r['te']['n']:02d}{r['te']['z']}"))
    seq = list(csv.reader(open(os.path.join(WORK, "01_数据", "943期序列数据.csv"), encoding="utf-8")))
    for r in seq:
        if not r[1].isdigit():
            continue
        d = datetime.date.fromisoformat(r[2])
        recs.append((d.year, d.month, d.day, int(r[1]), r[2], r[4], r[5]))
    out = []
    for y, m, d, q, ds, ping, te in recs:
        if q == target_period and y < target_date.year:
            out.append({"年": y, "期": q, "日期": ds, "平": ping, "特": te})
    return sorted(out, key=lambda x: x["年"])


def current_page_data():
    text = open(PAGE, encoding="utf-8").read()
    m = re.search(r"const DATA = (\{.*?\});", text, re.S)
    if not m:
        raise SystemExit("zhengpiao.html 找不到 DATA")
    return json.loads(m.group(1))


def physique_of(prev, last_q, special):
    if prev.get("期") != last_q:
        return {"期": last_q, "触发": 0, "命中": 0.0, "未命中": 0.0, "命中率": 0.0, "名次": 0}
    row = next((r for r in prev["排行"] if r["号"] == special), None)
    trig = prev["统计"]["触发"]
    hit = float(row["正"]) if row else 0.0
    return {"期": last_q, "触发": trig, "命中": hit, "未命中": round(trig - hit, 1),
            "命中率": round(hit / trig * 100, 1) if trig else 0.0,
            "名次": row["名"] if row else 0}


def update_registry(prev, q, d, special):
    tr = prev.get("四档登记")
    if not tr:
        return tr
    near = tr.get("近30", [])
    if near and near[-1]["期"] == q:
        return tr  # 已登记
    h = [1 if special in prev["四档"][t] else 0 for t in ("12", "14", "16", "18")]
    # 汇总
    for i, t in enumerate(("12", "14", "16", "18")):
        s = tr["汇总"][t]
        s["全期命中"] += h[i]
        s["全期期数"] += 1
        s["全期率"] = round(s["全期命中"] / s["全期期数"] * 100, 1)
    # 近30
    near.append({"期": q, "特": str(special), "h": h})
    if len(near) > 30:
        near = near[-30:]
    tr["近30"] = near
    for i, t in enumerate(("12", "14", "16", "18")):
        tr["汇总"][t]["近30命中"] = sum(x["h"][i] for x in near)
    # 月度
    month = d.strftime("%Y-%m")
    mm = next((x for x in tr["月度"]["分月"] if x["月"] == month), None)
    if mm is None:
        mm = {"月": month, "期数": 0, "命中": {"12": 0, "14": 0, "16": 0, "18": 0},
              "连对": 0, "连错": 0}
        tr["月度"]["分月"].append(mm)
    mm["期数"] += 1
    for i, t in enumerate(("12", "14", "16", "18")):
        mm["命中"][t] += h[i]
    return tr


def write_outputs(data, check=False):
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if check:
        return js
    os.makedirs(DATA_DIR, exist_ok=True)
    out = os.path.join(DATA_DIR, f"zhengpiao-{data['期']}.json")
    json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    text = open(PAGE, encoding="utf-8").read()
    text = re.sub(r"const DATA = \{.*?\};", "const DATA = " + js + ";", text, count=1, flags=re.S)
    text = re.sub(r"<title>正票 \d+期", f"<title>正票 {data['期']}期", text, count=1)
    open(PAGE, "w", encoding="utf-8").write(text)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int)
    ap.add_argument("--check", type=int)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    hist = load_history()
    synced = sync_draw_latest(hist)
    if synced:
        print(f"draw-latest 同步 {synced} 期")
    latest = max(hist)
    target = args.check or args.target or latest + 1
    seq, added = ensure_engine()
    # 取 q 期日期：上一期日期 + 1
    seqrows = list(csv.reader(open(seq, encoding="utf-8")))
    lastrow = next(r for r in seqrows if r[0] == "2026" and int(r[1]) == latest)
    target_date = datetime.date.fromisoformat(lastrow[2]) + datetime.timedelta(days=target - latest)
    print(f"引擎序列补 {added} 期；目标 {target} 期（{target_date}）")
    g = run_engine(target_date)
    votes, stats = tally(g)
    stats["条件数"] = len(g["ALLC"])
    if not args.check and not args.force:
        try:
            if current_page_data().get("期") == target:
                print(f"页面已是 {target} 期，跳过写入")
                return
        except Exception:
            pass
    data = build_data(g, votes, stats, hist, target)
    js = write_outputs(data, check=bool(args.check))
    if args.check:
        prev = current_page_data()
        print("当前页期", prev.get("期"), "目标", target)
        print("统计 生成", data["统计"], "页面", prev.get("统计"))
        print("前18 生成", [r["号"] for r in data["排行"][:18]])
        print("前18 页面", [r["号"] for r in prev["排行"][:18]])
        print("票数一致", [r["票"] for r in data["排行"][:18]] == [r["票"] for r in prev["排行"][:18]])
        print("特码后 生成样本", data["特码后"]["样本"], "页面", prev["特码后"]["样本"])
        print("往年今日 生成", len(data["往年今日"]), "页面", len(prev["往年今日"]))
        print("特码后明细一致", data["特码后"] == prev["特码后"])
        print("生成平码前5", data["特码后"]["平码"][:5])
        print("页面平码前5", prev["特码后"]["平码"][:5])
        print("生成下期前5", data["特码后"]["下期特码"][:5])
        print("页面下期前5", prev["特码后"]["下期特码"][:5])
        print("往年今日明细一致", data["往年今日"] == prev["往年今日"])
        print("生成往年", data["往年今日"])
        print("页面往年", prev["往年今日"])
        return
    print("已写", os.path.join(DATA_DIR, f"zhengpiao-{target}.json"), "并更新 zhengpiao.html")


if __name__ == "__main__":
    main()
