#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从九肖台账复算「特肖在推荐名单各位置」的命中分布，累积落盘。

口径：
- 分母＝每期有九肖栏目的站次；命中＝特肖落在该站九肖内。
- 位置＝特肖在站点九肖名单里的原序位置（第1位 … 第9位）；firstHit＝落在第1位（首肖）。
- 随机基准 1/9 ≈ 11.1%。

产出: data/zodiac-position-stats.json（供后续攒样本看首肖/各位置开出趋势）
"""
import json, os, datetime
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(ROOT, "data", "max-zodiac-ledger.json")
OUT = os.path.join(ROOT, "data", "zodiac-position-stats.json")
Z = "鼠牛虎兔龙蛇马羊猴鸡狗猪"


def empty_pos():
    return [0] * 9


def seg_of(pos):
    if pos <= 3:
        return "p1_3"
    if pos <= 6:
        return "p4_6"
    if pos <= 9:
        return "p7_9"
    return "p10_12"


def main():
    with open(LEDGER, encoding="utf-8") as f:
        ledger = json.load(f)

    periods = {}
    tot = {"elig": 0, "hit": 0, "first": 0, "pos": empty_pos()}
    first_rank_positions = []

    for issue in sorted(ledger.get("periods", {}).keys(), key=int):
        per = ledger["periods"][issue]
        actual = per.get("actual")
        elig = hit = first = 0
        pos = empty_pos()
        first_votes = Counter()
        for r in per.get("stations", {}).values():
            if r.get("status") != "有九肖" or not r.get("zodiacs"):
                continue
            elig += 1
            zs = r["zodiacs"]
            first_votes[zs[0]] += 1
            if actual in zs:
                hit += 1
                idx = zs.index(actual)
                if 0 <= idx < 9:
                    pos[idx] += 1
                if idx == 0:
                    first += 1
        order = [z for z, _ in first_votes.most_common()]
        first_rank = order.index(actual) + 1 if actual in order else None
        if first_rank:
            first_rank_positions.append(first_rank)
        periods[issue] = {
            "actual": actual,
            "elig": elig,
            "hit": hit,
            "firstHit": first,
            "pos": pos,
            "firstRank": first_rank,
        }
        tot["elig"] += elig
        tot["hit"] += hit
        tot["first"] += first
        for i in range(9):
            tot["pos"][i] += pos[i]

    seg = Counter(seg_of(p) for p in first_rank_positions)
    tot["firstRank"] = {
        "n": len(first_rank_positions),
        "positions": first_rank_positions,
        "seg": {k: seg.get(k, 0) for k in ("p1_3", "p4_6", "p7_9", "p10_12")},
    }

    out = {
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "baseline": round(1 / 9, 4),
        "rule": "位置＝特肖在站点九肖名单原序中的位次；firstHit＝第1位(首肖)；firstRank＝特肖在跨站首肖票数排行中的名次；分母为有九肖站次",
        "periods": periods,
        "total": tot,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"position-stats: {len(periods)} 期, 推荐 {tot['elig']} 站次, 命中 {tot['hit']}, "
          f"首肖 {tot['first']} ({tot['first']/tot['elig']*100:.1f}%)")


if __name__ == "__main__":
    main()
