#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""六肖 / 七肖逐站逐期台账（两套独立维度，互不派生）。

口径（按用户拍板）：
- 只取当期 1 期料：排除 2期/3期/两期/三期 跨期栏。
- 必须带号码：纯「6肖中特」「7肖中特」（无码）不纳入；只取「{n}肖加对应X码中特」类带码主推栏。
- 排除：杀栏（杀特/绝杀/杀平）、平特栏、图片栏(#pic)、解谜混合栏（生肖数不等于 n 的自动剔出，归质检）。
- 生肖按站点原始排序保留；号码为 parts 中两位数字，去重保序。
- 命中＝当期特肖落在推荐 n 肖内；号码从推荐肖里挑出，肖中号必中，号码不单独记命中。
- 早晚两份快照：晚版优先入账，早晚肖组不一致标 changed 并存 lateZodiacs。

产出: data/six-zodiac-ledger.json / data/seven-zodiac-ledger.json
用法:
  python3 build_six_seven_ledgers.py            # 重建全部有快照的期
  python3 build_six_seven_ledgers.py <期号>     # 单期入账
"""
import json, os, sys, glob, re, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
SNAP_DIR = PARENT / "snapshots"
DRAW_LATEST = ROOT / "draw-latest.json"
HISTORY = PARENT / "official-history.json"
Z = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
Z12 = ["马", "蛇", "龙", "兔", "虎", "牛", "鼠", "猪", "狗", "鸡", "猴", "羊"]

DIM = {"six": 6, "seven": 7}
FILES = {"six": "six-zodiac-ledger.json", "seven": "seven-zodiac-ledger.json"}
RULES = {
    "six": "六肖：只取当期1期、带对应号码的「6肖加对应X码中特」主推栏；纯6肖/2期3期/杀/平特/图片/解谜混合栏不计。命中＝特肖在推荐6肖内；号码从6肖挑出，肖中号必中，号码不单独记命中。",
    "seven": "七肖：只取当期1期、带对应号码的「7肖加对应X码中特」主推栏；纯7肖/2期/杀/平特/图片/解谜混合栏不计。命中＝特肖在推荐7肖内；号码从7肖挑出，肖中号必中，号码不单独记命中。",
}


def _parse_dt(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.datetime.strptime(str(s), fmt)
        except ValueError:
            continue
    return None


def deadline_for(issue):
    """开奖时点；开奖后生成的快照只归档，不进当期封存料/入账/改料比对。"""
    try:
        d = json.loads(DRAW_LATEST.read_text(encoding="utf-8"))
        m = d.get("macao") or {}
        if str(m.get("draw")) == str(issue):
            return _parse_dt(m.get("drawn_at"))
    except Exception:
        pass
    return None


MAX_CODES = {6: 18, 7: 14}  # 每肖最多 3 码(六肖18)/2 码(七肖14)；超出即全包/混合栏


def eligible(title, zs, nums, n):
    """是否为合格的 n 肖带码主推栏。返回 (是否合格, 排除原因)。"""
    if "#pic" in title:
        return False, "图片栏"
    if title.startswith("杀") or "绝杀" in title:
        return False, "杀栏"
    if "平特" in title:
        return False, "平特栏"
    if re.search(r"2期|3期|两期|三期", title):
        return False, "多期栏"
    if re.search(r"尾中特|头中特|公式|规律|#gongshi|gongshiguilv", title):
        return False, "非主推栏(尾/头/公式规律)"
    # 只认标准主推栏「{n}肖加对应X码中特」；加玄机字/诗句/成语/天地肖等复合解谜栏剔出归质检
    if not re.fullmatch(rf"{n}肖加对应\d+码中特", title):
        return False, "非标准主推栏"
    if len(zs) != n:
        return False, f"非{n}肖栏"
    if not nums:
        return False, "无号码"
    # 号码必须两位、落在 01-49；单位数视为尾/头数，剔除。
    if any(not (len(c) == 2 and 1 <= int(c) <= 49) for c in nums):
        return False, "号码格式异常"
    if len(nums) > MAX_CODES[n]:
        return False, "号码超上限(全包/混合)"
    return True, ""


def _code_zod_ok(zs, nums):
    zset = set(zs)
    return all(Z12[(int(c) - 1) % 12] in zset for c in nums)


def pick_column(columns, n):
    """选本站 n 肖带码主栏。优先标准阶梯「{n}肖加对应X码中特」，其次其他带码栏；同阶梯号码少者优先。"""
    cands = []
    for title, cd in (columns or {}).items():
        if not isinstance(cd, dict):
            continue
        parts = cd.get("parts", [])
        zs = [p for p in parts if p in Z]
        nums = [p for p in parts if str(p).isdigit()]
        ok, _ = eligible(title, zs, nums, n)
        if not ok:
            continue
        if not re.search(rf"{n}肖|{'六' if n == 6 else '七'}肖", title):
            continue
        if not _code_zod_ok(zs, nums):
            continue  # 号码生肖与推荐肖不自洽，混合/解析异常栏，剔出归质检
        ladder = 1 if re.fullmatch(rf"{n}肖加对应\d+码中特", title) else 0
        cands.append((ladder, len(nums), title, zs, nums))
    if not cands:
        return None
    cands.sort(key=lambda x: (x[0], -x[1]), reverse=True)
    _, _, title, zs, nums = cands[0]
    return title, zs, nums


def load_snapshot(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def snapshot_pick(snap, n):
    out = {}
    for _sk, sd in snap.get("sites", {}).items():
        key = f"{sd.get('system', '?')}:{sd.get('siteKey', _sk)}"
        cols = sd.get("columns", {})
        pick = pick_column(cols, n)
        if pick:
            title, zs, nums = pick
            raw = (cols.get(title) or {}).get("value", "")
            out[key] = {
                "system": sd.get("system", "?"),
                "siteKey": sd.get("siteKey", _sk),
                "column": title,
                "zodiacs": zs,
                "codes": nums,
                "raw": raw,
                "count": len(zs),
                "codeCount": len(nums),
                "status": f"有{n}肖",
            }
        else:
            out[key] = {
                "system": sd.get("system", "?"),
                "siteKey": sd.get("siteKey", _sk),
                "column": None,
                "zodiacs": [],
                "codes": [],
                "raw": "",
                "count": 0,
                "codeCount": 0,
                "status": f"无{n}肖栏目",
            }
    return out


def find_snapshots(issue):
    """同期快照按 generated_at 真实时间排序；剔除残缺/跨午夜旧版；开奖后快照不参与入账。"""
    fs = [f for f in glob.glob(str(SNAP_DIR / f"snapshot-{issue}-*.json"))
          if "-raw" not in os.path.basename(f) and "raw77" not in os.path.basename(f)]
    dl = deadline_for(issue)
    loaded = []
    for f in fs:
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            ga = d.get("generated_at") or ""
            dt = _parse_dt(ga)
            if dl and dt and dt > dl:
                continue
            loaded.append((ga, os.path.basename(f), f, len(d.get("sites", {}))))
        except Exception:
            continue
    if not loaded:
        return (None, None)
    loaded.sort(key=lambda t: (t[0], t[1]))
    med = sorted(x[3] for x in loaded)[len(loaded) // 2]
    good = [x for x in loaded if x[3] >= max(1, int(med * 0.8))] or loaded
    early = good[0][2]
    late = good[-1][2] if len(good) > 1 else None
    return (early, late)


def build_period(issue, hist, n):
    early_path, late_path = find_snapshots(issue)
    if not early_path:
        return None
    early = load_snapshot(early_path)
    early_pick = snapshot_pick(early, n)
    late_pick = snapshot_pick(load_snapshot(late_path), n) if late_path else {}

    actual = hist["specialZod"]
    stations = {}
    for key, rec in early_pick.items():
        late = late_pick.get(key)
        late_ok = bool(late and late["status"] != f"无{n}肖栏目")
        eff = late if late_ok else rec
        if eff["status"] == f"无{n}肖栏目":
            stations[key] = {**eff, "hit": None, "changed": False, "lateZodiacs": None}
            continue
        changed = bool(late_ok and late["zodiacs"] != rec["zodiacs"])
        stations[key] = {
            "system": eff["system"],
            "siteKey": eff["siteKey"],
            "column": eff["column"],
            "zodiacs": eff["zodiacs"],
            "codes": eff["codes"],
            "raw": eff.get("raw", ""),
            "count": eff["count"],
            "codeCount": eff["codeCount"],
            "status": eff["status"],
            "hit": actual in eff["zodiacs"],
            "changed": changed,
            "lateZodiacs": late["zodiacs"] if late_ok and changed else None,
        }
    return {
        "issue": int(issue),
        "specialNum": hist["specialNum"],
        "actual": actual,
        "earlySnapshot": os.path.basename(early_path),
        "lateSnapshot": os.path.basename(late_path) if late_path else None,
        "stations": stations,
    }


def main():
    hist_all = json.loads(HISTORY.read_text(encoding="utf-8"))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ledgers = {dim: {"updated_at": None, "rule": RULES[dim], "periods": {}} for dim in DIM}

    if args:
        issues = [args[0]]
    else:
        issues = [k for k in hist_all if find_snapshots(k)[0]]

    for issue in sorted(issues, key=int):
        hist = hist_all.get(str(issue)) or hist_all.get(int(issue))
        if not hist:
            print(f"  {issue}期: 历史缺失，跳过")
            continue
        for dim, n in DIM.items():
            rec = build_period(issue, hist, n)
            if not rec:
                continue
            ledgers[dim]["periods"][str(issue)] = rec
            eligible_n = [r for r in rec["stations"].values() if r["status"] == f"有{n}肖"]
            wins = sum(1 for r in eligible_n if r["hit"])
            print(f"  {issue}期 {dim}: 站{len(eligible_n)} 中{wins}")

    latest_at = ""
    for f in glob.glob(str(SNAP_DIR / "snapshot-*.json")):
        try:
            latest_at = max(latest_at, load_snapshot(f).get("generated_at") or "")
        except Exception:
            pass

    for dim, fn in FILES.items():
        ledgers[dim]["updated_at"] = latest_at
        (ROOT / "data" / fn).write_text(
            json.dumps(ledgers[dim], ensure_ascii=False, indent=2), encoding="utf-8")
        ps = ledgers[dim]["periods"]
        tail = "  ".join(f"{i}:站{len([r for r in ps[i]['stations'].values() if r['status'].startswith('有')])}"
                         for i in sorted(ps, key=int)[-4:])
        print(f"{dim} {len(ps)} 期  {tail}")
    print("台账已写: data/six-zodiac-ledger.json, data/seven-zodiac-ledger.json")


if __name__ == "__main__":
    main()
