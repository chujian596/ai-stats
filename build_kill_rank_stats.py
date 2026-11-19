#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从杀三肖台账复算每期「各肖被杀票数」排行，按期累积落盘。

口径：
- 杀肖票数＝当期把该肖列入本站杀三肖的站点数；排行按票数降序（同票按生肖固定序）。
- specialKilled＝特肖出现在多少个站的杀肖名单内（即这些站杀错了特肖）。
- 累计 total：每肖累计被杀站次、特肖累计被杀期次，供后续看高杀票肖的开出率。

产出: data/kill-rank-stats.json
"""
import json, os, datetime
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(ROOT, "data", "kill3-ledger.json")
OUT = os.path.join(ROOT, "data", "kill-rank-stats.json")
ZOD = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
ZIDX = {z: i for i, z in enumerate(ZOD)}


def rank_of(votes):
    return sorted(votes.items(), key=lambda kv: (-kv[1], ZIDX[kv[0]]))


def main():
    with open(LEDGER, encoding="utf-8") as f:
        ledger = json.load(f)

    periods = {}
    tot_votes = Counter()
    special_killed_times = 0
    n_periods = 0

    for issue in sorted(ledger.get("periods", {}).keys(), key=int):
        per = ledger["periods"][issue]
        actual = per.get("actual")
        votes = Counter()
        sites = 0
        special_killed = 0
        for r in per.get("stations", {}).values():
            if r.get("status") != "有三肖" or not r.get("zodiacs"):
                continue
            sites += 1
            for z in r["zodiacs"]:
                votes[z] += 1
            if actual and actual in r["zodiacs"]:
                special_killed += 1
        periods[issue] = {
            "actual": actual,
            "sites": sites,
            "specialKilled": special_killed,
            "rank": [{"z": z, "kill": n} for z, n in rank_of(votes)],
        }
        tot_votes.update(votes)
        special_killed_times += special_killed
        n_periods += 1

    out = {
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rule": "杀肖票数＝当期把该肖列入杀三肖的站点数；排行按票数降序；specialKilled＝特肖被多少站杀掉（杀错）",
        "periods": periods,
        "total": {
            "periods": n_periods,
            "killVotes": {z: tot_votes.get(z, 0) for z in ZOD},
            "specialKilledTimes": special_killed_times,
        },
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    top = rank_of(tot_votes)[:3]
    print(f"kill-rank-stats: {n_periods} 期, 累计被杀票次 {sum(tot_votes.values())}, "
          f"特肖被杀 {special_killed_times} 站次; 累计被杀最多: {top}")


if __name__ == "__main__":
    main()
