#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐期体检：每期应有的资料文件是否齐、文件内声明的期号是否与文件名一致（防串期）。
输出 data/period-matrix.json 供页面读取。
"""
import json, os, re, glob, datetime

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TYPES = ["forum", "tpl", "ratio", "three", "pingte", "archive-report", "consensus", "cross"]

def load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def period_of_filename(p):
    m = re.search(r"-(\d{3})\.json$", os.path.basename(p))
    return int(m.group(1)) if m else None

def declared_period(obj):
    if isinstance(obj, dict):
        for k in ("period", "per", "draw", "issue"):
            if isinstance(obj.get(k), int):
                return obj[k]
    return None

def main():
    periods = set()
    for p in glob.glob(os.path.join(DATA, "*.json")):
        n = period_of_filename(p)
        if n: periods.add(n)
    latest = load(os.path.join(DATA, "latest-period.json")) or {}
    cur = latest.get("period")
    if cur: periods.add(int(cur))
    ps = load(os.path.join(DATA, "periods.json")) or {}
    for x in ps.get("periods", []):
        periods.add(int(x))
    periods = sorted(periods)

    matrix = {"generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "current": cur, "periods": []}
    for per in periods:
        row = {"period": per, "files": {}, "missing": [], "mismatch": []}
        for t in TYPES:
            fp = os.path.join(DATA, f"{t}-{per}.json")
            if os.path.exists(fp):
                obj = load(fp)
                dp = declared_period(obj)
                row["files"][t] = {"ok": True, "bytes": os.path.getsize(fp), "declared": dp}
                if dp is not None and int(dp) != per:
                    row["mismatch"].append(f"{t}-{per}.json 内含期号 {dp}")
            else:
                row["files"][t] = {"ok": False}
                row["missing"].append(t)
        row["complete"] = len(row["missing"]) == 0
        matrix["periods"].append(row)

    out = os.path.join(DATA, "period-matrix.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=1)

    print("期号  完整  缺          串期")
    for r in matrix["periods"]:
        print(f"{r['period']}  {'是' if r['complete'] else '否'}   {','.join(r['missing']) or '-':<40} {','.join(r['mismatch']) or '-'}")
    print(f"\n当前期 {cur}，已写 {out}")

if __name__ == "__main__":
    main()
