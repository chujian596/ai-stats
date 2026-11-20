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
import json, glob, os, re, datetime
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

# ---- 快照归集：早 18* / 晚 20* ----
def pick_nine(columns):
    for t, cd in columns.items():
        if re.fullmatch(r'9肖加对应\d+码中特', t):
            return cd.get('value', '')
    for t, cd in columns.items():
        if re.fullmatch(r'9肖中特', t):
            return cd.get('value', '')
    return None


def pick_kill(columns):
    for cn in KILL_COLS:
        if columns.get(cn) and columns[cn].get('value'):
            return columns[cn]['value']
    return None


def snapshot_map(snap, picker):
    out = {}
    for _k, rec in (snap.get('sites') or {}).items():
        v = picker(rec.get('columns') or {})
        if v is None:
            continue
        out[str(rec.get('siteKey'))] = v
    return out


snaps = {}  # issue -> {'early': {sk: raw}, 'late': {sk: raw}}
for sp in sorted(glob.glob(os.path.join(PARENT, 'snapshots', 'snapshot-*.json'))):
    d = load(Path(sp))
    iss = d.get('issue')
    if not iss:
        continue
    iss = int(iss)
    name = os.path.basename(sp)
    bucket = 'early' if '-18' in name else ('late' if '-20' in name else None)
    if not bucket:
        continue
    slot = snaps.setdefault(iss, {})
    slot.setdefault(bucket, {})['nine'] = snapshot_map(d, pick_nine)
    slot[bucket]['kill'] = snapshot_map(d, pick_kill)


anomalies = []
checked = 0
by_type = {}


def add(issue, ledger, siteKey, system, typ, detail, zodiacs=None, actual=None):
    anomalies.append({
        'issue': str(issue), 'ledger': ledger, 'siteKey': siteKey, 'system': system,
        'type': typ, 'detail': detail, 'zodiacs': zodiacs or [], 'actual': actual,
    })
    by_type[typ] = by_type.get(typ, 0) + 1


def check_ledger(fn, ledger, expect, hit_rule):
    global checked
    L = load(ROOT / 'data' / fn)
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
            if r.get('status') not in ('有九肖', '有三肖'):
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
            # 3 台账原文解析自洽
            raw = r.get('raw') or ''
            if raw:
                if set(zchars(raw)) != set(zs):
                    add(iss, ledger, sk, sys, 'RAW_PARSE',
                        f"原文「{raw}」解析 {zchars(raw)} 与入账 {zs} 不符", zs, actual)
            # 4 快照外部回比（早/晚任一份一致即通过；两份都缺则跳过）
            early = slot.get('early', {}).get(snap_key, {})
            late = slot.get('late', {}).get(snap_key, {})
            raw_e, raw_l = early.get(sk), late.get(sk)
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
            # 6 改料标记一致性（早晚两份都有记录才判）
            if raw_e is not None and raw_l is not None:
                early_diff = set(zchars(raw_e)) != set(zchars(raw_l))
                if bool(r.get('changed')) != early_diff:
                    add(iss, ledger, sk, sys, 'CHANGED_FLAG',
                        f"早晚快照{'不一致' if early_diff else '一致'}，但台账 changed={r.get('changed')}", zs, actual)


check_ledger('max-zodiac-ledger.json', '九肖', 9, 'in')
check_ledger('kill3-ledger.json', '杀三肖', 3, 'not_in')


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

report = {
    'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'rule': '质检仅做一致性核对，不修改台账成绩；无快照期跳过 SNAP_MISMATCH/CHANGED_FLAG；样本不足不下结论。',
    'summary': {
        'stations_checked': checked,
        'anomalies': len(anomalies),
        'by_type': by_type,
    },
    'anomalies': anomalies,
}
(ROOT / 'data' / 'quality-report.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

print(f"质检完成：核对 {checked} 站次，异常 {len(anomalies)} 项")
for a in anomalies[:20]:
    print(f"  [{a['type']}] {a['issue']}期 {a['ledger']} {a['siteKey']} {a['detail']}")
if by_type:
    print('分类:', by_type)
