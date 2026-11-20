#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从最新「尚未入账」的站点快照生成待开期九肖推荐 data/current-recommend.json。

口径与 max_zodiac_ledger.py 的九肖栏识别一致：
- 取每站九肖主栏（优先阶梯「9肖加对应X码中特」，其次纯「9肖中特」）；
- 排除杀栏 / 平特栏 / 图片栏 / 非九肖栏；生肖按原序保留。

待开期判定：快照 issue > 台账已入账最大期（该期尚未开奖对账入账）。
- 有待开快照 → status=pending，附各站九肖；
- 无待开快照（当期已入账、下一期资料还没抓）→ status=empty。

产出: data/current-recommend.json（供 nine-zodiac.html 待开期推荐视图读取）
"""
import json, os, re, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(ROOT)
LEDGER_PUB = os.path.join(ROOT, "data", "max-zodiac-ledger.json")
SNAP_DIR = os.path.join(PARENT, "snapshots")
OUT = os.path.join(ROOT, "data", "current-recommend.json")
Z = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
# 与 build_kill3_ledger.py 同一杀三肖栏口径
KILL_COLS = ['杀特3肖', '绝杀三肖', '📛绝杀三肖']


def pick_kill(columns):
    for cn in KILL_COLS:
        cd = (columns or {}).get(cn)
        if isinstance(cd, dict):
            v = cd.get('value')
            if v:
                return [c for c in v if c in Z]
    return []


def eligible(title, zs):
    if "#pic" in title:
        return False
    if title.startswith("杀") or "绝杀" in title:
        return False
    if "平特" in title:
        return False
    return len(zs) == 9


def pick_column(columns):
    cands = []
    for title, cd in (columns or {}).items():
        if not isinstance(cd, dict):
            continue
        zs = [p for p in cd.get("parts", []) if p in Z]
        if not eligible(title, zs):
            continue
        ladder = 1 if re.fullmatch(r"9肖加对应\d+码中特", title) else 0
        plain = 1 if re.fullmatch(r"9肖中特", title) else 0
        extra = title.count("加对应")
        cands.append((ladder, plain, -extra, title, zs))
    if not cands:
        return None
    cands.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    _, _, _, title, zs = cands[0]
    return title, zs


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    ledger = load_json(LEDGER_PUB) if os.path.exists(LEDGER_PUB) else {"periods": {}}
    issues = [int(i) for i in ledger.get("periods", {}).keys() if str(i).isdigit()]
    max_issue = max(issues) if issues else 0

    # 收集所有快照，按 issue 分组，issue > max_issue 的为待开期
    pending = {}
    for sp in sorted(glob.glob(os.path.join(SNAP_DIR, "snapshot-*.json"))):
        try:
            snap = load_json(sp)
        except Exception:
            continue
        issue = snap.get("issue")
        if issue is None:
            continue
        try:
            issue = int(issue)
        except Exception:
            continue
        if issue <= max_issue:
            continue
        # 同一期取时间戳最新的一份（文件名 HHMM 越靠后越新）
        pending[issue] = (sp, snap)

    if not pending:
        out = {
            "period": max_issue + 1,
            "status": "empty",
            "updatedAt": None,
            "source": None,
            "sites": [],
            "pendingKill": [],
            "killSites": 0,
        }
    else:
        issue = max(pending.keys())
        sp, snap = pending[issue]
        sites = []
        kill_agg = {}
        kill_sites = 0
        for _sk, sd in (snap.get("sites") or {}).items():
            system = sd.get("system", "?")
            site_key = str(sd.get("siteKey", _sk))
            pick = pick_column(sd.get("columns", {}))
            cols = sd.get("columns") or {}
            kill = pick_kill(cols)
            if kill:
                kill_sites += 1
                for z in kill:
                    kill_agg[z] = kill_agg.get(z, 0) + 1
            if pick:
                title, zs = pick
                sites.append({
                    "system": system,
                    "siteKey": site_key,
                    "column": title,
                    "zodiacs": zs,
                    "killZodiacs": kill,
                    "status": "有九肖",
                })
            elif sd.get("error") or not cols:
                # 站点本期还没放出有效栏目：标注还没更新，区别于“有栏目但非九肖”
                sites.append({
                    "system": system,
                    "siteKey": site_key,
                    "column": None,
                    "zodiacs": [],
                    "killZodiacs": kill,
                    "status": "还没更新",
                })
            else:
                sites.append({
                    "system": system,
                    "siteKey": site_key,
                    "column": None,
                    "zodiacs": [],
                    "killZodiacs": kill,
                    "status": "无九肖栏目",
                })
        sites.sort(key=lambda x: (x["status"] != "有九肖", x["siteKey"]))
        pending_kill = [{"z": z, "kill": kill_agg[z]} for z in Z if kill_agg.get(z)]
        pending_kill.sort(key=lambda x: (-x["kill"], Z.index(x["z"])))
        out = {
            "period": issue,
            "status": "pending",
            "updatedAt": snap.get("generated_at"),
            "source": os.path.basename(sp),
            "sites": sites,
            "pendingKill": pending_kill,
            "killSites": kill_sites,
        }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    n = sum(1 for s in out["sites"] if s["status"] == "有九肖")
    print(f"current-recommend.json: status={out['status']} period={out['period']} "
          f"有九肖 {n}/{len(out['sites'])} 站 杀肖 {out['killSites']} 站 updated={out['updatedAt']}")


if __name__ == "__main__":
    main()
