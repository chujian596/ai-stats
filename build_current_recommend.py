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
CHANGE_LEDGER = os.path.join(PARENT, "改料台账.json")
SITE_DIRECTORY = os.path.join(ROOT, "data", "site-directory.json")
Z = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
WAVE = "红蓝绿"
# 与 build_kill3_ledger.py 同一杀三肖栏口径
KILL_COLS = ['杀特3肖', '绝杀三肖', '📛绝杀三肖']


# ---- 四维度待开栏目提取（口径与 build_extra_ledgers.py 一致）----
def _val(cd):
    v = cd.get('value')
    return v if isinstance(v, list) else (v or '')


def pick_pingte(cols):
    order = ['平特1肖', '平特一肖', '1肖加对应1码平特']
    for t in order:
        if re.search(r'\d期', t):
            continue
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
             and '单双' not in t and '各4尾' not in t and '字数字' not in t
             and not re.search(r'\d期', t)]
    cands.sort(key=lambda x: 0 if re.fullmatch(r'\d尾中特', x[0]) else 1)
    for t, cd in cands:
        v = _val(cd)
        ds = sorted(set(c for c in v if c.isdigit()))
        if ds:
            return {'column': t, 'picks': ds, 'raw': v}
    return None


def pick_head(cols):
    cands = [(t, cd) for t, cd in cols.items()
             if '头中特' in t and '尾' not in t and not re.search(r'\d期', t)]
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

# 六肖 / 七肖择栏口径与 build_six_seven_ledgers.py 完全一致（1期 + 带码主推栏）
try:
    from build_six_seven_ledgers import pick_column as _pick_n
except Exception:
    _pick_n = None


def pick_six_seven(cols, n):
    if _pick_n is None:
        return None
    p = _pick_n(cols, n)
    if not p:
        return None
    title, zs, nums = p
    return {'column': title, 'zodiacs': zs, 'codes': nums,
            'raw': (cols.get(title) or {}).get('value', '')}


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
    if re.search(r'\d期', title):
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


def load_known_site_keys():
    """目录里登记过名字的站（siteId 归一成 system-siteKey），用于剔除常态空站。"""
    ks = set()
    try:
        d = load_json(SITE_DIRECTORY)
        for s in d.get("sites", []):
            if (s.get("name") or "").strip() or (s.get("displayName") or "").strip():
                sid = s.get("siteId") or f"{s.get('system')}:{s.get('siteKey')}"
                ks.add(sid.replace(":", "-"))
    except Exception:
        pass
    return ks


def load_change_changes(issue):
    """待开期改料台账：siteId -> {dims, added, removed}；只取未结算（待开奖）条目。"""
    m = {}
    if not os.path.exists(CHANGE_LEDGER):
        return m
    try:
        L = load_json(CHANGE_LEDGER)
    except Exception:
        return m
    for e in L.get("entries", []):
        if str(e.get("period")) != str(issue) or e.get("result"):
            continue
        sid = e.get("siteId")
        if not sid:
            continue
        rec = m.setdefault(sid, {"dims": [], "added": [], "removed": []})
        dim = e.get("dim") or e.get("kind")
        if dim and dim not in rec["dims"]:
            rec["dims"].append(dim)
        for z in e.get("added") or []:
            if z not in rec["added"]:
                rec["added"].append(z)
        for z in e.get("removed") or []:
            if z not in rec["removed"]:
                rec["removed"].append(z)
    return m


def _col_has_value(cd):
    """栏目是否真有内容；空栏/只报错不能覆盖早先抓到的有效值。"""
    if not isinstance(cd, dict):
        return False
    v = cd.get("value")
    return bool(v) or bool(cd.get("parts"))


def _station_has_value(rec):
    return any(_col_has_value(cd) for cd in (rec.get("columns") or {}).values())


def _select_early_late(seq):
    """同期快照按 generated_at 真实时间排序；剔除站点数明显偏少的残缺/跨午夜旧版，
    取最早完整版=早版、最晚完整版=晚版。口径与基准 max_zodiac_ledger.find_snapshots 一致。"""
    loaded = []
    for sp, snap in seq:
        loaded.append((str(snap.get("generated_at") or ""), os.path.basename(sp),
                       sp, snap, len(snap.get("sites", {}))))
    if not loaded:
        return None, None
    loaded.sort(key=lambda t: (t[0], t[1]))
    med = sorted(x[4] for x in loaded)[len(loaded) // 2]
    good = [x for x in loaded if x[4] >= max(1, int(med * 0.8))] or loaded
    early = good[0]
    late = good[-1] if len(good) > 1 else good[0]
    return early, late


def merge_pending(early_slot, late_slot):
    """同期累计合并（same-period-union）：
    - 同一站点以晚版为骨干，晚版栏目值优先（真改料照实记）；
    - 晚版整站缺失 → 沿用早版该站，标 carried + carryFrom；
    - 晚版整站还在但某栏目缺失/空值 → 用早版该栏目补齐（空栏不能覆盖有效值）；
    - 缺站对照告警仍由 main 用 prev 基准完成。
    slot = (generated_at, fname, path, snap, site_count) 或 None。
    """
    merged = {}
    sources = []
    early_snap = early_slot[3] if early_slot else None
    late_snap = late_slot[3] if late_slot else None
    single = early_slot is late_slot
    if early_snap is not None:
        sources.append(os.path.basename(early_slot[2]))
        for key, rec in (early_snap.get("sites") or {}).items():
            if not _station_has_value(rec):
                continue
            m = copy.deepcopy(rec)
            m["_lastSource"] = os.path.basename(early_slot[2])
            m["_lastSeen"] = early_snap.get("generated_at")
            m["carried"] = not single
            m["carryFrom"] = None if single else sources[-1]
            m["fresh"] = single
            merged[key] = m
    if late_snap is not None and not single:
        sources.append(os.path.basename(late_slot[2]))
        for key, rec in (late_snap.get("sites") or {}).items():
            if not _station_has_value(rec):
                continue
            m = copy.deepcopy(rec)
            # 栏目并集：晚版缺失/空值的栏目用早版有效值补齐，空栏不覆盖有效值
            prev_rec = merged.get(key)
            if prev_rec:
                union_cols = dict(prev_rec.get("columns") or {})
                for title, cd in (m.get("columns") or {}).items():
                    if _col_has_value(cd):
                        union_cols[title] = copy.deepcopy(cd)
                m["columns"] = union_cols
                if not any(_col_has_value(cd) for cd in (m.get("columns") or {}).values()):
                    continue
            m["_lastSource"] = os.path.basename(late_slot[2])
            m["_lastSeen"] = late_snap.get("generated_at")
            m["carried"] = False
            m["carryFrom"] = None
            m["fresh"] = True
            merged[key] = m
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
            "pendingSix": {"zodiacs": [], "codes": []},
            "pendingSeven": {"zodiacs": [], "codes": []},
            "sixSites": 0,
            "sevenSites": 0,
            "extraSites": {},
            "coverage": {"sites": 0, "nine": 0, "kill": 0, "six": 0, "seven": 0},
            "prevSnapshot": {"file": None, "updatedAt": None, "nine": 0},
            "missingStations": [],
            "missingCount": 0,
            "prevFirstMap": {},
            "carriedCount": 0,
            "emptyStations": [],
            "emptyCount": 0,
            "changeStatus": "no_baseline",
            "changeBaseline": None,
        }
    else:
        issue = max(pending.keys())
        seq = pending[issue]
        early_slot, late_slot = _select_early_late(seq)
        sp = late_slot[2] if late_slot else seq[-1][0]
        snap = late_slot[3] if late_slot else seq[-1][1]
        merged_sites, merged_sources = merge_pending(early_slot, late_slot)
        # 本期待开改料台账（未结算条目）：供待开视图标注「本期有改动」
        change_map = load_change_changes(issue)

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
        six_zod, six_code, seven_zod, seven_code = {}, {}, {}, {}
        six_sites = seven_sites = 0
        for _sk, sd in merged_sites.items():
            system = sd.get("system", "?")
            site_key = str(sd.get("siteKey", _sk))
            carried = bool(sd.get("carried"))
            carry_from = sd.get("carryFrom")
            cols = sd.get("columns") or {}
            pick = pick_column(cols)
            kill = pick_kill(cols)
            extra = {dim: pk(cols) for dim, pk in EXTRA_PICKERS.items()}
            six = pick_six_seven(cols, 6)
            seven = pick_six_seven(cols, 7)
            if six:
                six_sites += 1
                for z in six['zodiacs']:
                    six_zod[z] = six_zod.get(z, 0) + 1
                for c in six['codes']:
                    six_code[c] = six_code.get(c, 0) + 1
            if seven:
                seven_sites += 1
                for z in seven['zodiacs']:
                    seven_zod[z] = seven_zod.get(z, 0) + 1
                for c in seven['codes']:
                    seven_code[c] = seven_code.get(c, 0) + 1
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
                "six": six or {},
                "seven": seven or {},
            }
            site_id = f"{system}-{site_key}"
            ch = change_map.get(site_id)
            if ch:
                base["changed"] = True
                base["changedDims"] = ch["dims"]
                base["changedAdded"] = ch["added"]
                base["changedRemoved"] = ch["removed"]
            else:
                base["changed"] = False
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
        known_keys = load_known_site_keys()
        empty_stations = []
        for fk, fr in fail_map.items():
            if fk in have_keys:
                continue
            kind = fr.get("failKind", "fetch_error")
            # 常态空站（目录里无名字的站）：不计入 100 站榜单，但单独登记，供待开视图复查
            if kind == "not_updated" and fk not in known_keys:
                empty_stations.append({
                    "system": fr.get("system", ""),
                    "siteKey": str(fr.get("siteKey", "")),
                    "siteId": fk,
                    "status": "空站未放料",
                    "failKind": kind,
                    "error": fr.get("error"),
                    "counted": False,
                })
                continue
            status = "抓取失败" if kind == "fetch_error" else "还没更新"
            sites.append({
                "system": fr.get("system", ""), "siteKey": str(fr.get("siteKey", "")),
                "fresh": False, "carried": False, "carryFrom": None,
                "status": status, "failKind": kind, "error": fr.get("error"),
                "changed": False,
                "column": None, "zodiacs": [], "killZodiacs": [],
                "pingte": {}, "wave": {}, "tail": {}, "head": {}, "size": {}, "parity": {},
                "six": {}, "seven": {},
            })
        sites.sort(key=lambda x: (x["status"] != "有九肖", x["siteKey"]))
        empty_stations.sort(key=lambda x: x["siteKey"])
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

        def zod_rank(agg):
            rows = [{"p": z, "n": n} for z, n in agg.items()]
            rows.sort(key=lambda x: (-x["n"], Z.index(x["p"])))
            return rows

        def code_rank(agg):
            rows = [{"p": c, "n": n} for c, n in agg.items()]
            rows.sort(key=lambda x: (-x["n"], int(x["p"])))
            return rows

        def six_seven_rank(zod_agg, code_agg):
            return {"zodiacs": zod_rank(zod_agg), "codes": code_rank(code_agg)}

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
                "empty": len(empty_stations),
                "kill": kill_sites,
                "pingte": extra_sites.get("pingte", 0),
                "wave": extra_sites.get("wave", 0),
                "tail": extra_sites.get("tail", 0),
                "head": extra_sites.get("head", 0),
                "size": extra_sites.get("size", 0),
                "parity": extra_sites.get("parity", 0),
                "six": six_sites,
                "seven": seven_sites,
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
            "pendingSix": six_seven_rank(six_zod, six_code),
            "pendingSeven": six_seven_rank(seven_zod, seven_code),
            "sixSites": six_sites,
            "sevenSites": seven_sites,
            "extraSites": extra_sites,
            "prevSnapshot": {"file": prev_sp, "updatedAt": (prev or {}).get("generated_at"), "nine": prev_nine},
            "missingStations": missing,
            "missingCount": len(missing),
            "prevFirstMap": prev_first_map,
            "carriedCount": carried_count,
            "emptyStations": empty_stations,
            "emptyCount": len(empty_stations),
            "changeStatus": "compared" if prev_sp else "no_baseline",
            "changeBaseline": prev_sp,
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
