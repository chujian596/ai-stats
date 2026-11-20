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
WAVE = "红蓝绿"
# 与 build_kill3_ledger.py 同一杀三肖栏口径
KILL_COLS = ['杀特3肖', '绝杀三肖', '📛绝杀三肖']


# ---- 四维度待开栏目提取（口径与 build_extra_ledgers.py 一致）----
def _val(cd):
    v = cd.get('value')
    return v if isinstance(v, list) else (v or '')


def pick_pingte(cols):
    order = ['平特1肖', '平特一肖', '2期1肖平特', '3期1肖平特', '1肖加对应1码平特']
    for t in order:
        cd = cols.get(t)
        if cd and cd.get('value'):
            z = [c for c in _val(cd) if c in Z]
            if len(z) == 1:
                return {'column': t, 'picks': z, 'raw': _val(cd)}
    return None


def pick_wave(cols):
    cd = cols.get('2波中特')
    if cd and cd.get('value'):
        w = [c for c in _val(cd) if c in WAVE]
        if w:
            return {'column': '2波中特', 'picks': w, 'raw': _val(cd)}
    return None


def pick_tail(cols):
    cands = [(t, cd) for t, cd in cols.items()
             if '尾中特' in t and '平特' not in t and '头' not in t
             and '单双' not in t and '各4尾' not in t and '字数字' not in t]
    cands.sort(key=lambda x: 0 if re.fullmatch(r'\d尾中特', x[0]) else 1)
    for t, cd in cands:
        v = _val(cd)
        ds = sorted(set(c for c in v if c.isdigit()))
        if ds:
            return {'column': t, 'picks': ds, 'raw': v}
    return None


def pick_head(cols):
    cands = [(t, cd) for t, cd in cols.items() if '头中特' in t and '尾' not in t]
    for t, cd in cands:
        v = _val(cd)
        ds = sorted(set(c for c in v if c.isdigit()))
        if ds:
            return {'column': t, 'picks': ds, 'raw': v}
    return None


EXTRA_PICKERS = {'pingte': pick_pingte, 'wave': pick_wave, 'tail': pick_tail, 'head': pick_head}


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

    # 收集所有待开期快照（排除 -raw 原始留档），按 issue 分组、文件名时间升序
    pending = {}
    for sp in sorted(glob.glob(os.path.join(SNAP_DIR, "snapshot-*.json"))):
        if "-raw" in os.path.basename(sp):
            continue
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
        pending.setdefault(issue, []).append((sp, snap))
    for _issue in pending:
        pending[_issue].sort(key=lambda x: os.path.basename(x[0]))

    if not pending:
        out = {
            "period": max_issue + 1,
            "status": "empty",
            "updatedAt": None,
            "source": None,
            "sites": [],
            "pendingKill": [],
            "killSites": 0,
            "pendingPingte": [],
            "pendingWave": [],
            "pendingTail": [],
            "pendingHead": [],
            "extraSites": {},
            "prevSnapshot": {"file": None, "updatedAt": None, "nine": 0},
            "missingStations": [],
            "missingCount": 0,
            "prevFirstMap": {},
        }
    else:
        issue = max(pending.keys())
        seq = pending[issue]
        sp, snap = seq[-1]
        prev = seq[-2][1] if len(seq) >= 2 else None
        prev_sp = os.path.basename(seq[-2][0]) if len(seq) >= 2 else None
        sites = []
        kill_agg = {}
        kill_sites = 0
        extra_agg = {dim: {} for dim in EXTRA_PICKERS}
        extra_sites = {dim: 0 for dim in EXTRA_PICKERS}
        for _sk, sd in (snap.get("sites") or {}).items():
            system = sd.get("system", "?")
            site_key = str(sd.get("siteKey", _sk))
            cols = sd.get("columns") or {}
            pick = pick_column(cols)
            kill = pick_kill(cols)
            extra = {dim: pk(cols) for dim, pk in EXTRA_PICKERS.items()}
            for dim, e in extra.items():
                if e:
                    extra_sites[dim] += 1
                    for p in e['picks']:
                        extra_agg[dim][p] = extra_agg[dim].get(p, 0) + 1
            if kill:
                kill_sites += 1
                for z in kill:
                    kill_agg[z] = kill_agg.get(z, 0) + 1
            base = {
                "system": system,
                "siteKey": site_key,
                "fresh": True,
                "killZodiacs": kill,
                "pingte": extra['pingte'] or {},
                "wave": extra['wave'] or {},
                "tail": extra['tail'] or {},
                "head": extra['head'] or {},
            }
            if pick:
                title, zs = pick
                base.update({"column": title, "zodiacs": zs, "status": "有九肖"})
                sites.append(base)
            elif sd.get("error") or not cols:
                # 站点本期还没放出有效栏目：标注还没更新，区别于“有栏目但非九肖”
                base.update({"column": None, "zodiacs": [], "status": "还没更新"})
                sites.append(base)
            else:
                base.update({"column": None, "zodiacs": [], "status": "无九肖栏目"})
                sites.append(base)
        sites.sort(key=lambda x: (x["status"] != "有九肖", x["siteKey"]))

        # 上一份快照参照：识别本轮未纳入的站（不计入本轮票数，仅作缺站对照，避免票数被静默稀释）
        prev_sites = (prev or {}).get("sites") or {}
        cur_keys = {f"{s['system']}-{s['siteKey']}" for s in sites}
        missing = []
        prev_first_map = {}
        prev_nine = 0
        for pk, ps in prev_sites.items():
            pcol = ps.get("columns") or {}
            pz = pick_column(pcol)
            pfirst = pz[1][0] if pz else None
            if pz:
                prev_nine += 1
            prev_first_map[pk] = pfirst
            if pk in cur_keys:
                continue
            missing.append({
                "system": ps.get("system", ""),
                "siteKey": ps.get("siteKey", pk),
                "key": pk,
                "prevZodiacs": pz[1] if pz else [],
                "prevFirst": pfirst,
            })
        missing.sort(key=lambda x: x["key"])

        pending_kill = [{"z": z, "kill": kill_agg[z]} for z in Z if kill_agg.get(z)]
        pending_kill.sort(key=lambda x: (-x["kill"], Z.index(x["z"])))

        def agg_list(dim):
            order = Z if dim == 'pingte' else None
            rows = [{"p": p, "n": n} for p, n in extra_agg[dim].items()]
            rows.sort(key=lambda x: -x['n'])
            return rows

        out = {
            "period": issue,
            "status": "pending",
            "updatedAt": snap.get("generated_at"),
            "source": os.path.basename(sp),
            "sites": sites,
            "pendingKill": pending_kill,
            "killSites": kill_sites,
            "pendingPingte": agg_list('pingte'),
            "pendingWave": agg_list('wave'),
            "pendingTail": agg_list('tail'),
            "pendingHead": agg_list('head'),
            "extraSites": extra_sites,
            "prevSnapshot": {"file": prev_sp, "updatedAt": (prev or {}).get("generated_at"), "nine": prev_nine},
            "missingStations": missing,
            "missingCount": len(missing),
            "prevFirstMap": prev_first_map,
        }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    n = sum(1 for s in out["sites"] if s["status"] == "有九肖")
    es = out.get("extraSites", {})
    print(f"current-recommend.json: status={out['status']} period={out['period']} "
          f"有九肖 {n}/{len(out['sites'])} 站 杀肖 {out['killSites']} 站 "
          f"平特 {es.get('pingte', 0)} 波色 {es.get('wave', 0)} 尾 {es.get('tail', 0)} 头 {es.get('head', 0)} 站 "
          f"updated={out['updatedAt']}")


if __name__ == "__main__":
    main()
