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
import json, os, re, glob, copy

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


def pick_size(cols):
    cd = cols.get('大小中特')
    if cd and cd.get('value'):
        v = [c for c in _val(cd) if c in '大小']
        if len(v) == 1:
            return {'column': '大小中特', 'picks': v, 'raw': _val(cd)}
    return None


def pick_parity(cols):
    cd = cols.get('单双中特')
    if cd and cd.get('value'):
        v = [c for c in _val(cd) if c in '单双']
        if len(v) == 1:
            return {'column': '单双中特', 'picks': v, 'raw': _val(cd)}
    return None


EXTRA_PICKERS = {'pingte': pick_pingte, 'wave': pick_wave, 'tail': pick_tail,
                 'head': pick_head, 'size': pick_size, 'parity': pick_parity}


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


def _col_has_value(cd):
    """栏目是否真有内容；空栏/只报错不能覆盖早先抓到的有效值。"""
    if not isinstance(cd, dict):
        return False
    v = cd.get("value")
    return bool(v) or bool(cd.get("parts"))


def merge_pending(seq):
    """同一期的多份快照按站点累计合并，只增不减。

    - 先出现的有效栏目先入账；后抓到的有效栏目覆盖同栏目旧值（真改料）；
    - 后一份整站缺失或栏目为空时，保留前一份，不把站点/票数打回去；
    - 同站多份快照的栏目取并集，避免“站还在但栏目少了”导致票数下降。
    """
    merged = {}
    sources = []
    for sp, snap in seq:
        fname = os.path.basename(sp)
        sources.append(fname)
        for key, rec in (snap.get("sites") or {}).items():
            if key not in merged:
                merged[key] = copy.deepcopy(rec)
                merged[key]["_lastSource"] = fname
                merged[key]["_lastSeen"] = snap.get("generated_at")
                continue
            cur = merged[key]
            new_cols = rec.get("columns") or {}
            has_new = any(_col_has_value(cd) for cd in new_cols.values())
            if has_new:
                old_cols = cur.get("columns") or {}
                for title, cd in new_cols.items():
                    if _col_has_value(cd):
                        old_cols[title] = copy.deepcopy(cd)
                cur["columns"] = old_cols
                for field in ("system", "siteKey", "issue"):
                    if rec.get(field) not in (None, ""):
                        cur[field] = rec[field]
                cur["carried"] = False
                cur["carryFrom"] = None
                cur["fresh"] = True
            else:
                # 本轮没抓到该站或栏目为空：保留旧栏目，标沿用
                if cur.get("columns"):
                    cur["carried"] = True
                    cur["carryFrom"] = fname
                    cur["fresh"] = False
                else:
                    cur.update(copy.deepcopy(rec))
            cur["_lastSource"] = fname
            cur["_lastSeen"] = snap.get("generated_at")
    return merged, sources


def _snapshot_score(snap):
    sites = snap.get("sites") or {}
    ok = sum(1 for v in sites.values() if v.get("columns"))
    cols = sum(len(v.get("columns") or {}) for v in sites.values())
    return ok, cols


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
        # 同一期可能跨午夜；文件名只有 HHMM，必须按 generated_at 真实时间排序，
        # 否则 00:05 会排到 23:31 前面，旧数据反覆盖新数据。
        pending[_issue].sort(key=lambda x: (str(x[1].get("generated_at") or ""), os.path.basename(x[0])))

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
            "carriedCount": 0,
        }
    else:
        issue = max(pending.keys())
        seq = pending[issue]
        sp, snap = seq[-1]
        merged_sites, merged_sources = merge_pending(seq)

        # 收集各份快照里没进 sites 的失败站：fetch_error=连接抓取失败；not_updated=站点还没更新
        fail_map = {}
        for _sp, _snap in seq:
            for fr in _snap.get("failedStations", []) or []:
                fk = f"{fr.get('system')}-{fr.get('siteKey')}"
                fail_map[fk] = fr

        def _ok_n(s):
            return sum(1 for v in (s.get("sites") or {}).values() if "columns" in v)

        # 基准取当天同期最完整的一份（排除本轮），缺站对照对齐最佳水平
        prev, prev_sp = None, None
        for p, s in seq[:-1]:
            if prev is None or _snapshot_score(s) > _snapshot_score(prev):
                prev, prev_sp = s, os.path.basename(p)
        sites = []
        kill_agg = {}
        kill_sites = 0
        extra_agg = {dim: {} for dim in EXTRA_PICKERS}
        extra_sites = {dim: 0 for dim in EXTRA_PICKERS}
        for _sk, sd in merged_sites.items():
            system = sd.get("system", "?")
            site_key = str(sd.get("siteKey", _sk))
            carried = bool(sd.get("carry"))
            carry_from = sd.get("carryFrom")
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
                "fresh": not carried,
                "carried": carried,
                "carryFrom": carry_from,
                "killZodiacs": kill,
                "pingte": extra['pingte'] or {},
                "wave": extra['wave'] or {},
                "tail": extra['tail'] or {},
                "head": extra['head'] or {},
                "size": extra['size'] or {},
                "parity": extra['parity'] or {},
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
        # 补齐没进 sites 的失败站：区分「抓取失败（连接/抓取问题）」与「还没更新（站点未放料）」
        have_keys = {f"{s['system']}-{s['siteKey']}" for s in sites}
        for fk, fr in fail_map.items():
            if fk in have_keys:
                continue
            kind = fr.get("failKind", "fetch_error")
            status = "抓取失败" if kind == "fetch_error" else "还没更新"
            sites.append({
                "system": fr.get("system", ""), "siteKey": str(fr.get("siteKey", "")),
                "fresh": False, "carried": False, "carryFrom": None,
                "status": status, "failKind": kind, "error": fr.get("error"),
                "column": None, "zodiacs": [], "killZodiacs": [],
                "pingte": {}, "wave": {}, "tail": {}, "head": {}, "size": {}, "parity": {},
            })
        sites.sort(key=lambda x: (x["status"] != "有九肖", x["siteKey"]))
        carried_count = sum(1 for s in sites if s.get("carried"))

        # 上一份快照参照：识别既没抓到、也未沿用兜底的站（仅作缺站对照；沿用站已计入榜单）
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
            "mergeMode": "same-period-union",
            "mergedSources": merged_sources,
            "coverage": {
                "sites": len(sites),
                "nine": sum(1 for s in sites if s.get("status") == "有九肖"),
                "noNine": sum(1 for s in sites if s.get("status") == "无九肖栏目"),
                "notUpdated": sum(1 for s in sites if s.get("status") == "还没更新"),
                "fetchFail": sum(1 for s in sites if s.get("status") == "抓取失败"),
                "kill": kill_sites,
                "pingte": extra_sites.get("pingte", 0),
                "wave": extra_sites.get("wave", 0),
                "tail": extra_sites.get("tail", 0),
                "head": extra_sites.get("head", 0),
                "size": extra_sites.get("size", 0),
                "parity": extra_sites.get("parity", 0),
            },
            "sites": sites,
            "pendingKill": pending_kill,
            "killSites": kill_sites,
            "pendingPingte": agg_list('pingte'),
            "pendingWave": agg_list('wave'),
            "pendingTail": agg_list('tail'),
            "pendingHead": agg_list('head'),
            "pendingSize": agg_list('size'),
            "pendingParity": agg_list('parity'),
            "extraSites": extra_sites,
            "prevSnapshot": {"file": prev_sp, "updatedAt": (prev or {}).get("generated_at"), "nine": prev_nine},
            "missingStations": missing,
            "missingCount": len(missing),
            "prevFirstMap": prev_first_map,
            "carriedCount": carried_count,
        }

    with open(OUT, "w", encoding="utf-8") as f:
        try:
            from enrich_site_names import attach
            for s in out.get("sites", []):
                attach(s)
        except Exception:
            pass
        json.dump(out, f, ensure_ascii=False, indent=2)
    n = sum(1 for s in out["sites"] if s["status"] == "有九肖")
    es = out.get("extraSites", {})
    print(f"current-recommend.json: status={out['status']} period={out['period']} "
          f"有九肖 {n}/{len(out['sites'])} 站 杀肖 {out['killSites']} 站 "
          f"平特 {es.get('pingte', 0)} 波色 {es.get('wave', 0)} 尾 {es.get('tail', 0)} 头 {es.get('head', 0)} "
          f"大小 {es.get('size', 0)} 单双 {es.get('parity', 0)} 站 "
          f"updated={out['updatedAt']}")


if __name__ == "__main__":
    main()
