#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 data/kill3-ledger.json：每站杀特3肖逐期台账
数据源：
  1) data/sites-current.json 的 history['杀特3肖']（293~322，21 站）
  2) ../snapshots/ 最新 snapshot 的 杀特3肖 列（当前未开奖期，如 323）
  3) 开奖结果 ../4901988-draws.json（特码→特肖）
口径：命中＝当期特肖不在该站所杀 3 肖内。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
DRAW = PARENT / '4901988-draws.json'
Z12 = ["马", "蛇", "龙", "兔", "虎", "牛", "鼠", "猪", "狗", "鸡", "猴", "羊"]
ZOD = '鼠牛虎兔龙蛇马羊猴鸡狗猪'


def zchar_of(n):
    return Z12[(int(n) - 1) % 12]


def zchars(v):
    return [c for c in (v or '') if c in ZOD]


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


# ---- 开奖：期号 -> (特码, 特肖)
draws = {}
for k, v in load(DRAW).items():
    if not isinstance(v, dict):
        continue
    sp = v.get('special') or v.get('t') or v.get('code')
    if sp:
        draws[int(k)] = (int(sp), zchar_of(int(sp)))

# ---- 历史库补充（早期无本地快照的期，仅作补充；快照为准）----
sc = load(ROOT / 'data' / 'sites-current.json')
periods = {}
sites_meta = {}
for s in sc['sites']:
    h = (s.get('history') or {}).get('杀特3肖') or {}
    if not h:
        continue
    sites_meta[s['id']] = {'siteKey': s['id'], 'system': 'wanpz'}
    for iss, val in h.items():
        periods.setdefault(int(iss), {})[s['id']] = zchars(val)

# ---- 本地快照按期归集：每期取 generated_at 最晚一份（改料复检后为准）----
# 快照留存当晚各站实际所杀三肖；原站事后删帖/改料不影响已留存记录。
KILL_COLS = ['杀特3肖', '绝杀三肖', '📛绝杀三肖']
by_issue = {}
for sp in sorted((PARENT / 'snapshots').glob('snapshot-*.json')):
    d = load(sp)
    iss = d.get('issue')
    if not iss:
        continue
    iss = int(iss)
    at = d.get('generated_at') or ''
    if iss not in by_issue or at >= by_issue[iss][0]:
        by_issue[iss] = (at, sp, d)

VALID_PREFIX = ('wanpz-h2-', 'wanpz-h9-', 'bdmijg-js-')
snapshot_issues = set()
for iss, (at, sp, d) in sorted(by_issue.items()):
    cur = {}
    for key, rec in (d.get('sites') or {}).items():
        if not key.startswith(VALID_PREFIX):
            continue
        cols = rec.get('columns') or {}
        v = None
        for cn in KILL_COLS:
            v = (cols.get(cn) or {}).get('value')
            if v:
                break
        if not v:
            continue
        if key.startswith('bdmijg-js-'):
            hk = 'bdmijg-' + key[len('bdmijg-js-'):]
            sys = 'bdmijg'
        else:
            hk = str(rec.get('siteKey'))
            sys = key.split('-')[0]
        if hk not in sites_meta:   # 快照里有、历史库没有的站（新站/无历史）
            sites_meta[hk] = {'siteKey': hk, 'system': sys}
        cur[hk] = zchars(v)
    if cur:
        snapshot_issues.add(iss)
        periods.setdefault(iss, {}).update(cur)   # 快照覆盖历史库同站同期

# ---- 组台账
out_periods = {}
for iss in sorted(periods):
    st = {}
    sp_num, sp_z = (draws.get(iss, (None, None)))
    for sid, zs in periods[iss].items():
        if not zs:
            continue
        meta = sites_meta.get(sid, {'system': 'wanpz'})
        hit = None if sp_z is None else (sp_z not in zs)
        st[sid] = {
            'siteKey': sid,
            'system': meta['system'],
            'status': '有三肖',
            'zodiacs': zs,
            'hit': hit,
            'changed': False,
        }
    out_periods[str(iss)] = {
        'specialNum': sp_num,
        'actual': sp_z,
        'hasSnapshot': iss in snapshot_issues,
        'stations': st,
    }

latest_snap_at = max((at for at, _, _ in by_issue.values()), default='')
out = {
    'updated_at': latest_snap_at or sc.get('updatedAt', ''),
    'rule': '杀特3肖：当期特肖不在所杀3肖内记为「中」；连对/连错按逐期尾段推导；只收本站固定杀三肖栏，跳转外站的链接不计；有本地快照的期以快照留存为准，历史库仅补早期无快照期',
    'periods': out_periods,
}
(ROOT / 'data' / 'kill3-ledger.json').write_text(
    json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

for iss in sorted(out_periods, key=int)[-4:]:
    p = out_periods[iss]
    hit = sum(1 for v in p['stations'].values() if v['hit'])
    tot = sum(1 for v in p['stations'].values() if v['hit'] is not None)
    print(f'{iss}期 特{str(p["specialNum"]):>3s}/{p["actual"] or "-"} 站{len(p["stations"])} 判定{tot} 中{hit}')
print('期数', len(out_periods), '文件 data/kill3-ledger.json')
