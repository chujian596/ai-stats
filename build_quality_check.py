#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台账一致性质检（每期重建后自动跑）。

对九肖 / 杀三肖两份台账逐期逐站核对：
  NUM_COUNT     肖数符合栏目标称（九肖 9 / 杀三肖 3）
  NUM_DUP       肖组无重复
  RAW_PARSE     台账留存原文 raw 解析出的生肖 == 入账肖组（解析未丢/增）
  SNAP_MISMATCH 快照网站原文 == 入账肖组（外部回比；无快照期跳过）
  HIT_RECOMPUTE 命中判定按硬逻辑复算与台账一致
  SPECIAL_MAP   特码反推生肖与开奖源 special_zodiac 一致（按期一次）
  CHANGED_FLAG  改料标记与早/晚两份快照是否一致

产出: data/quality-report.json；无异常时 anomalies 为空。
口径：样本与台账一致；质检只做一致性核对，不修改台账成绩。
"""
import json, glob, os, re, datetime, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
DRAW = PARENT / '4901988-draws.json'
ZOD = '鼠牛虎兔龙蛇马羊猴鸡狗猪'
Z12 = ["马", "蛇", "龙", "兔", "虎", "牛", "鼠", "猪", "狗", "鸡", "猴", "羊"]
WAVE_C = '红蓝绿'
KILL_COLS = ['杀特3肖', '绝杀三肖', '📛绝杀三肖']


def zchars(v):
    return [c for c in (v or '') if c in ZOD]


def zchar_of(n):
    return Z12[(int(n) - 1) % 12]


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


# ---- 开奖源 ----
draws = {}
for k, v in load(DRAW).items():
    if not isinstance(v, dict):
        continue
    sp = v.get('special') or v.get('t') or v.get('code')
    if sp:
        sp = int(sp)
        meta = {m['n']: m for m in v.get('meta', [])}
        plains = v.get('plains', [])
        seven = {meta[n]['zodiac'] for n in plains if n in meta}
        if sp in meta:
            seven.add(meta[sp]['zodiac'])
        draws[int(k)] = {
            'special': sp, 'zod': v.get('special_zodiac') or zchar_of(sp),
            'seven': seven,
            'wave': meta[sp]['wave'] if sp in meta else None,
            'tail': sp % 10, 'head': sp // 10,
        }

# ---- 快照归集：早 / 晚完整版（择栏口径与台账 max_zodiac_ledger.pick_column 完全一致）----
def pick_nine(columns):
    # 复用台账统一选栏函数：同一站、同一栏目名，质检与台账挑到同一栏。
    pick = _mzl.pick_column(columns or {})
    if not pick:
        return None
    title, _zs = pick
    return (columns or {}).get(title, {}).get('value', '')


def pick_kill(columns):
    for cn in KILL_COLS:
        if columns.get(cn) and columns[cn].get('value'):
            return columns[cn]['value']
    return None


# 六肖 / 七肖择栏复用台账统一选栏函数（1 期 + 带码主推栏）；模块在下方 _iu 加载后赋值
_ss = None


def _pick_n(columns, n):
    if _ss is None:
        return None
    p = _ss.pick_column(columns or {}, n)
    if not p:
        return None
    title, _zs, _nums = p
    return (columns or {}).get(title, {}).get('value', '')


def pick_six(columns):
    return _pick_n(columns, 6)


def pick_seven(columns):
    return _pick_n(columns, 7)


def snapshot_map(snap, picker):
    out = {}
    for _k, rec in (snap.get('sites') or {}).items():
        v = picker(rec.get('columns') or {})
        if v is None:
            continue
        sysname = rec.get('system') or ''
        out[f"{sysname}:{rec.get('siteKey')}"] = v
    return out


# ---- 六维择栏（与 build_extra_ledgers.py / build_current_recommend.py 同款；内联避免导入即重建台账）----
def _ep_pingte(cols):
    order = ['平特1肖', '平特一肖', '1肖加对应1码平特']
    for t in order:
        if re.search(r'\d期', t):
            continue
        cd = cols.get(t)
        if cd and cd.get('value'):
            z = [c for c in cd['value'] if c in ZOD]
            if len(z) == 1:
                return (t, z, cd['value'])
    return None


def _ep_wave(cols):
    cd = cols.get('2波中特')
    if cd and cd.get('value'):
        w = [c for c in cd['value'] if c in WAVE_C]
        if w:
            return ('2波中特', w, cd['value'])
    return None


def _ep_tail(cols):
    cands = [(t, cd) for t, cd in cols.items()
             if '尾中特' in t and '平特' not in t and '头' not in t
             and '单双' not in t and '各4尾' not in t and '字数字' not in t
             and not re.search(r'\d期', t)]
    cands.sort(key=lambda x: 0 if re.fullmatch(r'\d尾中特', x[0]) else 1)
    for t, cd in cands:
        v = cd.get('value') or ''
        ds = sorted(set(c for c in v if c.isdigit()))
        if ds:
            return (t, ds, v)
    return None


def _ep_head(cols):
    cands = [(t, cd) for t, cd in cols.items()
             if '头中特' in t and '尾' not in t and not re.search(r'\d期', t)]
    for t, cd in cands:
        v = cd.get('value') or ''
        ds = sorted(set(c for c in v if c.isdigit()))
        if ds:
            return (t, ds, v)
    return None


def _ep_size(cols):
    cd = cols.get('大小中特')
    if cd and cd.get('value'):
        v = [c for c in cd['value'] if c in '大小']
        if len(v) == 1:
            return ('大小中特', v, cd['value'])
    return None


def _ep_parity(cols):
    cd = cols.get('单双中特')
    if cd and cd.get('value'):
        v = [c for c in cd['value'] if c in '单双']
        if len(v) == 1:
            return ('单双中特', v, cd['value'])
    return None


EXTRA_PARSED = {'pingte': _ep_pingte, 'wave': _ep_wave, 'tail': _ep_tail,
                'head': _ep_head, 'size': _ep_size, 'parity': _ep_parity}

KILL_VALID_PREFIX = ('wanpz-h1-', 'wanpz-h2-', 'wanpz-h3-', 'wanpz-h5-',
                     'wanpz-h6-', 'wanpz-h8-', 'wanpz-h9-', 'bdmijg-js-')


def parsed_map(snap, kind, n=None):
    """按台账同款择栏从快照解析每站推荐列表；key 口径与对应台账 sid 对齐。"""
    out = {}
    for _k, rec in (snap.get('sites') or {}).items():
        cols = rec.get('columns') or {}
        zs = None
        if kind == 'nine':
            p = _mzl.pick_column(cols)
            if p:
                zs = p[1]
        elif kind == 'kill':
            if not _k.startswith(KILL_VALID_PREFIX):
                continue
            v = pick_kill(cols)
            if v is not None:
                zs = zchars(v)
        elif kind in ('six', 'seven'):
            p = _ss.pick_column(cols, n)
            if p:
                zs = p[1]
        else:
            pk = EXTRA_PARSED[kind](cols)
            if pk:
                zs = pk[1]
        if zs is None:
            if kind in ('nine', 'six', 'seven'):
                zs = []  # 无栏站也登记，供晚版有效兜底晋升，对齐台账 universe
            else:
                continue
        sk = str(rec.get('siteKey') or _k)
        sysn = rec.get('system') or ''
        if kind == 'kill':
            canon = ('bdmijg-' + _k[len('bdmijg-js-'):]) if _k.startswith('bdmijg-js-') else sk
        else:
            canon = f"{sysn}:{sk}"
        out[canon] = zs
    return out


PARSED_KINDS = ['nine', 'kill', 'six', 'seven', 'pingte', 'wave', 'tail', 'head', 'size', 'parity']


def _parsed_slot(d):
    return {k: parsed_map(d, k, 6 if k == 'six' else 7 if k == 'seven' else None)
            for k in PARSED_KINDS}


snaps = {}  # issue -> {'early': {sk: raw}, 'late': {sk: raw}}
# 早晚快照口径与 max_zodiac_ledger.find_snapshots 一致：generated_at 排序 + 覆盖度过滤取首/尾完整版
import importlib.util as _iu
_spec = _iu.spec_from_file_location('mzl', str(PARENT / 'max_zodiac_ledger.py'))
_mzl = _iu.module_from_spec(_spec); _spec.loader.exec_module(_mzl)
_spec_ss = _iu.spec_from_file_location('ss', str(ROOT / 'build_six_seven_ledgers.py'))
_ss = _iu.module_from_spec(_spec_ss); _spec_ss.loader.exec_module(_ss)

_issues = set()
for sp in glob.glob(os.path.join(PARENT, 'snapshots', 'snapshot-*.json')):
    try:
        _issues.add(int(load(Path(sp)).get('issue')))
    except Exception:
        pass
for iss in sorted(_issues):
    ep, lp = _mzl.find_snapshots(str(iss))
    slot = snaps.setdefault(iss, {})
    if ep:
        d = _mzl.load_snapshot(ep)
        slot['early'] = {'nine': snapshot_map(d, pick_nine), 'kill': snapshot_map(d, pick_kill),
                         'six': snapshot_map(d, pick_six), 'seven': snapshot_map(d, pick_seven)}
        slot['early_parsed'] = _parsed_slot(d)
    if lp:
        d = _mzl.load_snapshot(lp)
        slot['late'] = {'nine': snapshot_map(d, pick_nine), 'kill': snapshot_map(d, pick_kill),
                        'six': snapshot_map(d, pick_six), 'seven': snapshot_map(d, pick_seven)}
        slot['late_parsed'] = _parsed_slot(d)


anomalies = []
checked = 0
by_type = {}
warn_by_type = {}


def add(issue, ledger, siteKey, system, typ, detail, zodiacs=None, actual=None, level='error'):
    anomalies.append({
        'issue': str(issue), 'ledger': ledger, 'siteKey': siteKey, 'system': system,
        'type': typ, 'detail': detail, 'zodiacs': zodiacs or [], 'actual': actual,
        'level': level,
    })
    if level == 'error':
        by_type[typ] = by_type.get(typ, 0) + 1
    else:
        warn_by_type[typ] = warn_by_type.get(typ, 0) + 1


def check_ledger(fn, ledger, expect, hit_rule, snap_key=None, status_ok=('有九肖', '有三肖'), check_codes=False):
    global checked
    L = load(ROOT / 'data' / fn)
    if snap_key is None:
        snap_key = 'nine' if ledger == '九肖' else 'kill'
    for iss, per in L['periods'].items():
        iss_i = int(iss)
        actual = per.get('actual')
        # 特肖映射按期核对一次
        dr = draws.get(iss_i)
        if dr and actual and dr['zod'] != actual:
            add(iss, ledger, '-', '-', 'SPECIAL_MAP',
                f"开奖源特肖 {dr['zod']} 与台账特肖 {actual} 不符", actual=actual)
        slot = snaps.get(iss_i, {})
        for sid, r in per.get('stations', {}).items():
            if r.get('status') not in status_ok:
                continue
            checked += 1
            zs = r.get('zodiacs') or []
            sk = r.get('siteKey') or sid
            sys = r.get('system', '')
            # 1 肖数
            if len(zs) != expect:
                add(iss, ledger, sk, sys, 'NUM_COUNT', f"肖数 {len(zs)} ≠ 标称 {expect}", zs, actual)
            # 2 重复
            if len(set(zs)) != len(zs):
                add(iss, ledger, sk, sys, 'NUM_DUP', '肖组存在重复生肖', zs, actual)
            # 2b 号码生肖自洽（六/七肖带码栏）
            if check_codes:
                codes = r.get('codes') or []
                bad = [c for c in codes if zchar_of(c) not in set(zs)]
                if bad:
                    add(iss, ledger, sk, sys, 'CODE_ZOD', f"号码 {bad} 生肖不在推荐肖内", zs, actual)
            # 3 台账原文解析自洽
            raw = r.get('raw') or ''
            if raw:
                if set(zchars(raw)) != set(zs):
                    add(iss, ledger, sk, sys, 'RAW_PARSE',
                        f"原文「{raw}」解析 {zchars(raw)} 与入账 {zs} 不符", zs, actual)
            # 4 快照外部回比（早/晚任一份一致即通过；两份都缺则跳过）
            early = slot.get('early', {}).get(snap_key, {})
            late = slot.get('late', {}).get(snap_key, {})
            ck = f"{sys}:{sk}" if sys else sk
            raw_e, raw_l = early.get(ck), late.get(ck)
            if raw_e is None:
                raw_e = early.get(sk)
            if raw_l is None:
                raw_l = late.get(sk)
            if raw_e is not None or raw_l is not None:
                sets = [set(zchars(x)) for x in (raw_e, raw_l) if x is not None]
                if sets and set(zs) not in sets:
                    add(iss, ledger, sk, sys, 'SNAP_MISMATCH',
                        f"快照原文 {[x for x in (raw_e, raw_l) if x]} 与入账 {zs} 不符", zs, actual)
            # 5 命中复算
            if actual and r.get('hit') is not None:
                recompute = actual in zs if hit_rule == 'in' else actual not in zs
                if bool(r['hit']) != recompute:
                    add(iss, ledger, sk, sys, 'HIT_RECOMPUTE',
                        f"台账 hit={r['hit']} 复算应为 {recompute}", zs, actual)
            # 6 改料标记一致性（早晚两份都有记录才判；改料跟踪不回填历史，仅核 325 及以后）
            if raw_e is not None and raw_l is not None and iss_i >= 325:
                early_diff = set(zchars(raw_e)) != set(zchars(raw_l))
                if bool(r.get('changed')) != early_diff:
                    add(iss, ledger, sk, sys, 'CHANGED_FLAG',
                        f"早晚快照{'不一致' if early_diff else '一致'}，但台账 changed={r.get('changed')}", zs, actual)


check_ledger('max-zodiac-ledger.json', '九肖', 9, 'in')
check_ledger('kill3-ledger.json', '杀三肖', 3, 'not_in')
check_ledger('six-zodiac-ledger.json', '六肖', 6, 'in', snap_key='six', status_ok=('有6肖',), check_codes=True)
check_ledger('seven-zodiac-ledger.json', '七肖', 7, 'in', snap_key='seven', status_ok=('有7肖',), check_codes=True)


# ---- 连对/连错/总中总错复算（复刻前端 streakFor）----
# 连段：按期号升序建序列；从最近一期往前数，命中状态连续才算，状态一变即中断；
# 缺记录或 hit===null/undefined 立即中断（不计入连段）。总数单独统计，不被连段打断。
def _streak_key(sid, r):
    sk = r.get('siteKey') or sid
    sysn = r.get('system') or ''
    if ':' in sid:
        return sid
    return f"{sysn}:{sk}" if sysn else sk


def check_streak(fn, ledger, status_ok):
    global checked
    L = load(ROOT / 'data' / fn)
    issues = sorted((int(i) for i in L['periods'].keys()))
    issue_set = set(issues)
    # station_key -> {issue: record}
    series = {}
    for iss in issues:
        per = L['periods'][str(iss)] if str(iss) in L['periods'] else L['periods'][iss]
        for sid, r in per.get('stations', {}).items():
            if status_ok is not None and r.get('status') not in status_ok:
                continue
            series.setdefault(_streak_key(sid, r), {})[iss] = r

    for key, recs in series.items():
        present = sorted(recs.keys())
        if not present:
            continue
        sk = recs[present[-1]].get('siteKey') or key.split(':', 1)[-1]
        sysn = recs[present[-1]].get('system', '')
        latest = present[-1]

        # 命中类型合法性 + 总数统计
        total_w = total_l = total_n = 0
        invalid_iss = None
        for iss in present:
            r = recs[iss]
            hit = r.get('hit', None)
            if hit is None:
                continue  # null/undefined：空期，连段中断、总数不计
            if not isinstance(hit, bool):
                invalid_iss = iss
                add(iss, ledger, sk, sysn, 'STREAK_HIT_INVALID',
                    f"hit 类型非法：{hit!r}（应为 true/false 或 null）", actual=None)
                continue
            total_n += 1
            if hit:
                total_w += 1
            else:
                total_l += 1

        if total_n == 0:
            continue  # 无有效 hit 序列的状态站跳过
        checked += 1

        # 1 总数不平
        if total_w + total_l != total_n:
            add(latest, ledger, sk, sysn, 'STREAK_TOTAL',
                f"总数不平：totalW={total_w} + totalL={total_l} ≠ totalN={total_n}")

        # 3 缺期缺口：相邻两条记录之间跨过台账已存在的期号
        for a, b in zip(present, present[1:]):
            missing = [p for p in issue_set if a < p < b]
            if missing:
                add(b, ledger, sk, sysn, 'STREAK_GAP',
                    f"序列缺期：{a} 与 {b} 之间缺 {missing}", level='warn')

        # 4 连段自洽：反向回溯（前端口径，从台账最近一期起算，缺记录/空期即中断）
        # 与正向末段两种算法互校
        w = l = 0
        started = False
        cur = False
        for iss in reversed(issues):
            r = recs.get(iss)
            if r is None or r.get('hit', None) is None:
                break
            h = bool(r['hit'])
            if not started:
                started, cur = True, h
                w, l = (1, 0) if h else (0, 1)
            elif h == cur:
                if h:
                    w += 1
                else:
                    l += 1
            else:
                break
        # 正向末段（缺记录/空期同样重置连段）
        w2 = l2 = 0
        prev = None
        run_len = 0
        run_cur = None
        for iss in issues:
            r = recs.get(iss)
            hit = r.get('hit', None) if r else None
            if hit is None:
                prev, run_cur = None, None
                run_len = 0
                continue
            h = bool(hit)
            if prev is None or h == prev:
                run_len += 1
            else:
                run_len = 1
            prev, run_cur = h, h
        if run_cur is not None:
            if run_cur:
                w2 = run_len
            else:
                l2 = run_len
        if (w, l) != (w2, l2):
            add(latest, ledger, sk, sysn, 'STREAK_SEGMENT',
                f"连段自洽矛盾：反向 连对{w}/连错{l}，正向末段 连对{w2}/连错{l2}")


check_streak('max-zodiac-ledger.json', '九肖', ('有九肖',))
check_streak('kill3-ledger.json', '杀三肖', ('有三肖',))
check_streak('six-zodiac-ledger.json', '六肖', ('有6肖',))
check_streak('seven-zodiac-ledger.json', '七肖', ('有7肖',))


def extra_recompute(dim, picks, dr):
    if dim == 'pingte':
        return picks[0] in dr['seven']
    if dim == 'wave':
        return dr['wave'] in picks
    if dim == 'tail':
        return str(dr['tail']) in picks
    if dim == 'head':
        return str(dr['head']) in picks
    return False


def check_extra(fn, ledger, dim):
    global checked
    L = load(ROOT / 'data' / fn)
    for iss, per in L['periods'].items():
        iss_i = int(iss)
        dr = draws.get(iss_i)
        for sid, r in per.get('stations', {}).items():
            picks = r.get('picks') or []
            if not picks:
                continue
            checked += 1
            sk = r.get('siteKey') or sid
            sys = r.get('system', '')
            raw = r.get('raw') or ''
            # 原文解析自洽
            if dim == 'pingte':
                parsed = zchars(raw)
            elif dim == 'wave':
                parsed = [c for c in raw if c in WAVE_C]
            else:
                parsed = [c for c in raw if c.isdigit()]
            if raw and set(parsed) != set(picks):
                add(iss, ledger, sk, sys, 'RAW_PARSE',
                    f"原文「{raw}」解析 {parsed} 与入账 {picks} 不符", picks, per.get('actual'))
            # 命中复算
            if dr and r.get('hit') is not None:
                recompute = extra_recompute(dim, picks, dr)
                if bool(r['hit']) != recompute:
                    add(iss, ledger, sk, sys, 'HIT_RECOMPUTE',
                        f"台账 hit={r['hit']} 复算应为 {recompute}", picks, per.get('actual'))


check_extra('pingte-ledger.json', '平特一肖', 'pingte')
check_extra('wave-ledger.json', '波色', 'wave')
check_extra('tail-ledger.json', '尾数', 'tail')
check_extra('head-ledger.json', '头数', 'head')


# ---- 逐维聚合对账卡口：从快照按统一规则重算站数 + 每号/每肖票数，与台账落盘值逐维比对 ----
def _norm_sk(canon):
    return canon.split(':', 1)[1] if ':' in canon else canon


def _comb_map(kind, slot, union=True):
    e = (slot.get('early_parsed') or {}).get(kind) or {}
    l = (slot.get('late_parsed') or {}).get(kind) or {}
    if union:
        # 杀三 / 波色 / 头 / 尾 / 大小 / 单双 / 平特：台账按 siteKey 合并，晚版有效覆盖早版
        out = {}
        for src in (e, l):
            for canon, zs in src.items():
                out[_norm_sk(canon)] = zs
        return out
    # 九肖 / 六肖 / 七肖：台账以早版站点为基准，晚版有效兜底；晚版独有站不补入
    out = {}
    for canon, zs in e.items():
        out[canon] = l.get(canon) or l.get(_norm_sk(canon)) or zs
    return out


def _led_keys(per, statuses):
    keys = set()
    for sid, r in per.get('stations', {}).items():
        if statuses is not None and r.get('status') not in statuses:
            continue
        sk = r.get('siteKey') or sid
        sysn = r.get('system', '')
        keys.add(f"{sysn}:{sk}")
        keys.add(sk)
    return keys


def _station_sets(comb, per, statuses):
    """canon 优先、siteKey 兜底对齐两侧站点（台账 system 常记泛化 wanpz，快照为 wanpz-hN）；
    仅比对有有效推荐的站，无栏空组不参与缺站对照。"""
    exp_canon, exp_sk = set(), set()
    for canon, zs in comb.items():
        if zs:
            exp_canon.add(canon)
            exp_sk.add(canon.split(':', 1)[1] if ':' in canon else canon)
    led_canon, led_sk = set(), set()
    for sid, r in per.get('stations', {}).items():
        if statuses is not None and r.get('status') not in statuses:
            continue
        sk = r.get('siteKey') or sid
        led_sk.add(sk)
        if r.get('system'):
            led_canon.add(f"{r['system']}:{sk}")
    missing = [c for c in exp_canon if c not in led_canon and _norm_sk(c) not in led_sk]
    extra = [c for c in led_canon if c not in exp_canon and _norm_sk(c) not in exp_sk]
    return sorted(missing), sorted(extra)


def _agg_report(iss, dim, exp_n, led_n, exp_c, led_c, missing, extra,
                full_exp=None, full_led=None, level='error'):
    diffs = {k: (exp_c.get(k, 0), led_c.get(k, 0)) for k in set(exp_c) | set(led_c)
             if exp_c.get(k, 0) != led_c.get(k, 0)}
    full_diffs = None
    if full_exp is not None:
        full_diffs = {k: (full_exp.get(k, 0), full_led.get(k, 0))
                      for k in set(full_exp) | set(full_led)
                      if full_exp.get(k, 0) != full_led.get(k, 0)}
    if exp_n == led_n and not diffs and not full_diffs and not missing and not extra:
        return
    detail = f"聚合对账 站数 预期{exp_n}/台账{led_n}"
    if missing:
        detail += f"；快照有台账缺 {missing[:5]}"
    if extra:
        detail += f"；台账有快照缺 {extra[:5]}"
    if diffs:
        detail += f"；票数差 {dict(list(diffs.items())[:10])}"
    if full_diffs:
        detail += f"；全集票数差 {dict(list(full_diffs.items())[:10])}"
    add(iss, dim, '-', '-', 'AGG_MISMATCH', detail, actual=None, level=level)


def agg_check_nine():
    L = load(ROOT / 'data' / 'max-zodiac-ledger.json')
    for iss, per in L['periods'].items():
        slot = snaps.get(int(iss))
        if not slot or not (per.get('earlySnapshot') or per.get('hasSnapshot')):
            continue
        comb = _comb_map('nine', slot, union=False)
        exp_n = sum(1 for zs in comb.values() if zs)
        exp_first = collections.Counter(zs[0] for zs in comb.values() if zs)
        exp_full = collections.Counter(z for zs in comb.values() if zs for z in zs)
        elig = [r for r in per['stations'].values() if r['status'] == '有九肖']
        led_n = len(elig)
        led_first = collections.Counter(r['zodiacs'][0] for r in elig)
        led_full = collections.Counter(z for r in elig for z in r['zodiacs'])
        missing, extra = _station_sets(comb, per, ('有九肖',))
        _agg_report(iss, '九肖', exp_n, led_n, exp_first, led_first,
                    missing, extra, exp_full, led_full, level='warn')


def agg_check_simple(fn, dim, statuses, kind, field='zodiacs', union=True):
    L = load(ROOT / 'data' / fn)
    for iss, per in L['periods'].items():
        slot = snaps.get(int(iss))
        if not slot or not per.get('hasSnapshot'):
            continue
        comb = _comb_map(kind, slot, union=union)
        exp_n = sum(1 for v in comb.values() if v)
        exp_c = collections.Counter(x for v in comb.values() if v for x in v)
        elig = [r for r in per['stations'].values()
                if statuses is None or r.get('status') in statuses]
        led_n = len(elig)
        led_c = collections.Counter(x for r in elig for x in (r.get(field) or []))
        exp_keys = set(comb.keys())
        missing, extra = _station_sets(comb, per, statuses)
        _agg_report(iss, dim, exp_n, led_n, exp_c, led_c,
                    missing, extra)


agg_check_nine()
agg_check_simple('kill3-ledger.json', '杀三肖', ('有三肖',), 'kill')
agg_check_simple('six-zodiac-ledger.json', '六肖', ('有6肖',), 'six', union=False)
agg_check_simple('seven-zodiac-ledger.json', '七肖', ('有7肖',), 'seven', union=False)
agg_check_simple('pingte-ledger.json', '平特一肖', None, 'pingte', field='picks')
agg_check_simple('wave-ledger.json', '波色', None, 'wave', field='picks')
agg_check_simple('tail-ledger.json', '尾数', None, 'tail', field='picks')
agg_check_simple('head-ledger.json', '头数', None, 'head', field='picks')
agg_check_simple('size-ledger.json', '大小', None, 'size', field='picks')
agg_check_simple('parity-ledger.json', '单双', None, 'parity', field='picks')


# 待开期快照掉站预警：本轮未纳入站对照上一份快照，体系性整批缺失需复核是否补齐
try:
    pend = load(ROOT / 'data' / 'current-recommend.json')
    if pend.get('status') == 'pending' and pend.get('missingStations'):
        miss = pend['missingStations']
        by_sys = collections.Counter(m.get('system', '') for m in miss)
        for sysname, n in by_sys.items():
            if n >= 5:
                add(pend['period'], '待开推荐', '-', sysname, 'SNAP_DROP',
                    f"本轮快照较上版缺失 {n} 站（{sysname}），未计入本轮票数；下一轮快照需复核是否补齐",
                    actual=None, level='warn')
except Exception:
    pass

report = {
    'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'rule': '质检仅做一致性核对，不修改台账成绩；无快照期跳过 SNAP_MISMATCH/CHANGED_FLAG；样本不足不下结论。',
    'summary': {
        'stations_checked': checked,
        'anomalies': sum(1 for a in anomalies if a.get('level', 'error') == 'error'),
        'warnings': sum(1 for a in anomalies if a.get('level') == 'warn'),
        'by_type': by_type,
        'warn_by_type': warn_by_type,
    },
    'anomalies': anomalies,
}
(ROOT / 'data' / 'quality-report.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

hard = [a for a in anomalies if a.get('level', 'error') == 'error']
warns = [a for a in anomalies if a.get('level') == 'warn']
print(f"质检完成：核对 {checked} 站次，硬异常 {len(hard)} 项，预警 {len(warns)} 项")
for a in anomalies[:20]:
    lvl = '预警' if a.get('level') == 'warn' else '异常'
    print(f"  [{lvl}][{a['type']}] {a['issue']}期 {a['ledger']} {a['siteKey']} {a['detail']}")
if by_type:
    print('分类:', by_type)
