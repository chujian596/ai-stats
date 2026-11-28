#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨共识榜「开出项在榜内名次」位置频次统计，按站池档位分别累计。

口径（与前端榜单聚合/排序一致）：
- 分母＝每期有有效推荐的站次；每站推荐项各计一票。
- 榜序＝票数降序，同票生肖按生肖序、号码按数值序、其余按字符串序。
- 名次＝开出项在排序后榜内的 1-based 位置；票数为 0（未被任何站推荐）记 None（未上榜）。
- 命中判定复用台账站级 hit 字段，本脚本不另造命中口径。
- 杀三肖为反向榜（杀＝不推），名次仅作位置参考，命中语义与正向榜相反，单独标注。
- 平特一肖：特肖(actual)名次单列；另按七肖集合(actualSet)逐肖记名次，与命中口径一致。

站池档位（与 stats.html TIERS 一致；core 恒入，added 按 grade 白名单截断）：
  100 现跑基线(core) / 139 三齐全(A) / 147 双覆盖(A,B) / 151 仅杀三(A,B,Ck)
  192 仅九肖(A,B,Ck,Cn) / 194 全量(A,B,Ck,Cn,D)
各档独立计票、独立排名次，再累计 1~12 逐位出现次数。

产出: data/rank-position-stats.json
样本不足 30 期的榜在 total.tentative 标注，趋势仅供参考。
"""
import json, os, datetime
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "rank-position-stats.json")
ZOD = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
SAMPLE_MIN = 30

# key, 标题, 文件, 推荐字段, 开出字段, 是否只取首项, 方向, 选项上限
BOARDS = [
    {"key": "max_zodiac_first", "title": "九肖·首肖榜", "file": "max-zodiac-ledger.json",
     "pick": "zodiacs", "actual": "actual", "first_only": True, "direction": "forward", "opts": 12},
    {"key": "max_zodiac_all", "title": "九肖·全集榜", "file": "max-zodiac-ledger.json",
     "pick": "zodiacs", "actual": "actual", "first_only": False, "direction": "forward", "opts": 12},
    {"key": "kill3", "title": "杀三肖(反向)", "file": "kill3-ledger.json",
     "pick": "zodiacs", "actual": "actual", "first_only": False, "direction": "reverse", "opts": 12},
    {"key": "six", "title": "六肖", "file": "six-zodiac-ledger.json",
     "pick": "zodiacs", "actual": "actual", "first_only": False, "direction": "forward", "opts": 12},
    {"key": "seven", "title": "七肖", "file": "seven-zodiac-ledger.json",
     "pick": "zodiacs", "actual": "actual", "first_only": False, "direction": "forward", "opts": 12},
    {"key": "pingte", "title": "平特一肖", "file": "pingte-ledger.json",
     "pick": "picks", "actual": "actual", "actual_set": "actualSet", "first_only": False,
     "direction": "forward", "opts": 12},
    {"key": "wave", "title": "波色", "file": "wave-ledger.json", "opts": 3,
     "pick": "picks", "actual": "actualWave", "first_only": False, "direction": "forward"},
    {"key": "head", "title": "头数", "file": "head-ledger.json", "opts": 5,
     "pick": "picks", "actual": "actualHead", "first_only": False, "direction": "forward"},
    {"key": "tail", "title": "尾数", "file": "tail-ledger.json", "opts": 7,
     "pick": "picks", "actual": "actualTail", "first_only": False, "direction": "forward"},
    {"key": "size", "title": "大小", "file": "size-ledger.json", "opts": 2,
     "pick": "picks", "actual": "actualSize", "first_only": False, "direction": "forward"},
    {"key": "parity", "title": "单双", "file": "parity-ledger.json", "opts": 2,
     "pick": "picks", "actual": "actualParity", "first_only": False, "direction": "forward"},
]

SHORT = {
    "max_zodiac_first": "首肖九", "max_zodiac_all": "全集九", "kill3": "杀三",
    "six": "六肖", "seven": "七肖", "pingte": "平特", "wave": "波色",
    "head": "头数", "tail": "尾数", "size": "大小", "parity": "单双",
}

# 与 stats.html 的 TIERS 对齐
TIERS = [
    {"key": "100", "name": "现跑基线", "grades": []},
    {"key": "139", "name": "三齐全", "grades": ["A"]},
    {"key": "147", "name": "双覆盖", "grades": ["A", "B"]},
    {"key": "151", "name": "仅杀三", "grades": ["A", "B", "Ck"]},
    {"key": "192", "name": "仅九肖", "grades": ["A", "B", "Ck", "Cn"]},
    {"key": "194", "name": "全量", "grades": ["A", "B", "Ck", "Cn", "D"]},
]

DIR_BY_ID = {}


def load_directory():
    p = os.path.join(DATA, "site-directory.json")
    if not os.path.exists(p):
        return
    for s in json.load(open(p, encoding="utf-8")).get("sites", []):
        DIR_BY_ID[s["siteId"]] = s


def order_key(name):
    if name in ZOD:
        return (0, ZOD.index(name))
    try:
        return (1, int(name))
    except (ValueError, TypeError):
        return (2, str(name))


def valid_pick(rec, pick):
    """有效推荐：生肖榜 status 以『有』开头；非生肖榜以推荐列表非空为准。"""
    vals = rec.get(pick) or []
    vals = [str(v) for v in vals if v not in (None, "")]
    if not vals:
        return []
    st = rec.get("status")
    if st is not None and not str(st).startswith("有"):
        return []
    return vals


def site_allowed(rec, tier):
    d = DIR_BY_ID.get(rec.get("siteId"))
    if d is None:
        return True
    if d.get("tier") == "core":
        return True
    return d.get("grade") in tier["grades"]


def rank_of(counter, item):
    """返回开出项在票榜名次(1-based)；0票/未推荐返回 None。"""
    item = str(item)
    order = sorted(counter.items(), key=lambda kv: (-kv[1], order_key(kv[0])))
    for i, (name, cnt) in enumerate(order):
        if name == item:
            return i + 1 if cnt > 0 else None
    return None


def rank_bucket(rank):
    if rank is None:
        return "none"
    if rank == 1:
        return "r1"
    if rank <= 3:
        return "r2_3"
    if rank <= 6:
        return "r4_6"
    return "r7plus"


def fresh_tot():
    return {"elig": 0, "hit": 0, "listed": 0, "top1": 0, "top3": 0,
            "bucket": Counter(), "ranks": [], "rankDist": [0] * 13, "rankNone": 0}


def build_summary(tot, n):
    buckets = {k: tot["bucket"].get(k, 0) for k in ("r1", "r2_3", "r4_6", "r7plus", "none")}
    return {
        "periods": n,
        "elig": tot["elig"],
        "hit": tot["hit"],
        "hitRate": round(tot["hit"] / tot["elig"], 4) if tot["elig"] else None,
        "listed": tot["listed"],
        "top1": tot["top1"],
        "top3": tot["top3"],
        "bucket": buckets,
        "rankDist": tot["rankDist"][1:13],
        "rankNone": tot["rankNone"],
        "tentative": n < SAMPLE_MIN,
        "avgRank": round(sum(tot["ranks"]) / len(tot["ranks"]), 2) if tot["ranks"] else None,
    }


def analyze(board):
    path = os.path.join(DATA, board["file"])
    if not os.path.exists(path):
        return None
    ledger = json.load(open(path, encoding="utf-8"))
    periods = {}  # 备查：全量(194)口径的逐期名次与投票榜
    tier_tot = {t["key"]: fresh_tot() for t in TIERS}
    tier_periods = {t["key"]: 0 for t in TIERS}

    for issue in sorted(ledger.get("periods", {}).keys(), key=int):
        per = ledger["periods"][issue]
        actual = per.get(board["actual"])
        actual = None if actual is None else str(actual)
        set_actual = per.get(board.get("actual_set")) if board.get("actual_set") else None

        counters = {t["key"]: Counter() for t in TIERS}
        elig = {t["key"]: 0 for t in TIERS}
        hit = {t["key"]: 0 for t in TIERS}

        for rec in per.get("stations", {}).values():
            vals = valid_pick(rec, board["pick"])
            if not vals:
                continue
            for t in TIERS:
                if not site_allowed(rec, t):
                    continue
                c = counters[t["key"]]
                elig[t["key"]] += 1
                if board["first_only"]:
                    c[vals[0]] += 1
                else:
                    for v in vals:
                        c[v] += 1
                if rec.get("hit") is True:
                    hit[t["key"]] += 1

        # 备查板用全量口径
        full_counter = counters["194"]
        rank = rank_of(full_counter, actual) if actual else None
        set_ranks = None
        if set_actual:
            set_ranks = {str(a): rank_of(full_counter, a) for a in set_actual}

        periods[issue] = {
            "actual": actual,
            "actualSet": set_actual,
            "elig": elig["194"],
            "hit": hit["194"],
            "rank": rank,
            "setRanks": set_ranks,
            "board": [{"name": n, "votes": c} for n, c in
                      sorted(full_counter.items(), key=lambda kv: (-kv[1], order_key(kv[0])))]
        }

        for t in TIERS:
            tk = t["key"]
            tt = tier_tot[tk]
            if elig[tk] == 0:
                continue  # 该档此期无有效站，不计入该档分母
            tier_periods[tk] += 1
            r = rank_of(counters[tk], actual) if actual else None
            tt["elig"] += elig[tk]
            tt["hit"] += hit[tk]
            if r is not None:
                tt["listed"] += 1
                tt["ranks"].append(r)
                if r == 1:
                    tt["top1"] += 1
                if r <= 3:
                    tt["top3"] += 1
                if 1 <= r <= 12:
                    tt["rankDist"][r] += 1
            else:
                tt["rankNone"] += 1
            tt["bucket"][rank_bucket(r)] += 1

    tiers = {t["key"]: {"name": t["name"], "summary": build_summary(tier_tot[t["key"]], tier_periods[t["key"]])}
             for t in TIERS}
    return {"title": board["title"], "direction": board["direction"],
            "file": board["file"], "key": board["key"], "opts": board.get("opts", 12),
            "rule": "名次＝开出项在跨站共识票榜的1-based位置；0票记未上榜；命中复用台账hit；各档独立计票排名",
            "tiers": tiers, "periods": periods}


def _matrix_block(L, boards, keys, tier_key, title):
    heads = ["位置"] + [SHORT[k] for k in keys]
    L += [f"### {title}", "",
          "| " + " | ".join(heads) + " |",
          "|" + "---|" * len(heads)]

    def cell(k, i):
        b = boards[k]; s = b["tiers"][tier_key]["summary"]; dist = s["rankDist"]
        if i > b["opts"]:
            return "—"
        return str(dist[i - 1])

    for i in range(1, 13):
        L.append("| " + " | ".join([f"第{i}位"] + [cell(k, i) for k in keys]) + " |")
    L.append("| " + " | ".join(["未上榜"] + [str(boards[k]["tiers"][tier_key]["summary"]["rankNone"]) for k in keys]) + " |")
    L.append("| " + " | ".join(["期数"] + [str(boards[k]["tiers"][tier_key]["summary"]["periods"]) for k in keys]) + " |")
    L.append("")


def write_report(boards):
    keys = list(boards.keys())
    L = ["# 跨榜·开出位置频次成绩单", "",
         f"更新时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}　样本门槛 {SAMPLE_MIN} 期（不足标待定）", "",
         "> 一张表看全部类目：表头＝类目，行＝开出落在共识榜第几位（1~12），格子＝累计开出次数；不记生肖。选项少于 12 的类目，超出选项数的位置记 —。杀三为反向榜。各站池档位独立计票、独立排名次。", ""]

    _matrix_block(L, boards, keys, "194", "一、全量 194 站·位置频次矩阵")
    _matrix_block(L, boards, keys, "100", "二、现跑基线 100 站·位置频次矩阵")

    L += ["## 三、各档各榜最常位置", "",
          "| 类目 | 档位 | 期数 | 命中率 | 最常位置 |", "|---|---|---|---|---|"]
    for k in keys:
        b = boards[k]
        for t in TIERS:
            s = b["tiers"][t["key"]]["summary"]; dist = s["rankDist"]
            top = max(range(1, 13), key=lambda i: dist[i - 1])
            top_txt = f"第{top}位({dist[top-1]})" if dist[top - 1] > 0 else "—"
            hr = f"{s['hitRate']*100:.1f}%" if s["hitRate"] is not None else "-"
            L.append(f"| {SHORT[k]} | {t['key']} {t['name']} | {s['periods']} | {hr} | {top_txt} |")

    L += ["", "## 四、逐期名次（备查·全量口径）", ""]
    for b in boards.values():
        ps = b["periods"]; iss = sorted(ps, key=int)
        L += [f"### {b['title']}（{iss[0]}~{iss[-1]}）", "", "| 期 | 名次 |", "|---|---|"]
        for i in iss:
            q = ps[i]; r = "未上榜" if q["rank"] is None else q["rank"]
            L.append(f"| {i} | {r} |")
        L.append("")
    open(os.path.join(DATA, "rank-position-report.md"), "w", encoding="utf-8").write("\n".join(L))


def main():
    load_directory()
    boards = {}
    for b in BOARDS:
        res = analyze(b)
        if res:
            boards[b["key"]] = res

    out = {
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sample_min": SAMPLE_MIN,
        "tiers": [{"key": t["key"], "name": t["name"], "grades": t["grades"]} for t in TIERS],
        "note": "样本不足30期标 tentative，趋势仅供参考；杀三为反向榜；平特特肖名次见 rank，七肖各名次见 setRanks；各档独立计票排名。",
        "boards": boards,
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    write_report(boards)

    print(f"rank-position-stats: {len(boards)} 榜 -> {OUT}")
    for key, b in boards.items():
        s = b["tiers"]["194"]["summary"]
        print(f"  {b['title']:12s} 期{s['periods']:2d} 命中{s['hitRate']} 上榜{s['listed']} "
              f"top1={s['top1']} top3={s['top3']} 均名次={s['avgRank']} tentative={s['tentative']}")


if __name__ == "__main__":
    main()
