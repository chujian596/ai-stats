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
    if lp:
        d = _mzl.load_snapshot(lp)
        slot['late'] = {'nine': snapshot_map(d, pick_nine), 'kill': snapshot_map(d, pick_kill),
                        'six': snapshot_map(d, pick_six), 'seven': snapshot_map(d, pick_seven)}


anomalies = []
checked = 0
by_type = {}


def add(issue, ledger, siteKey, system, typ, detail, zodiacs=None, actual=None, level='error'):
    anomalies.append({
        'issue': str(issue), 'ledger': ledger, 'siteKey': siteKey, 'system': system,
        'type': typ, 'detail': detail, 'zodiacs': zodiacs or [], 'actual': actual,
        'level': level,
    })
    by_type[typ] = by_type.get(typ, 0) + 1


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


WAVE_C = '红蓝绿'

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
