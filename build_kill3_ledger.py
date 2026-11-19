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

# ---- 历史（sites-current）
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

# ---- 当前未开奖期（最新 snapshot）
snaps = sorted((PARENT / 'snapshots').glob('snapshot-*.json'))
cur_issue = None
snap_time = None
for sp in snaps:
    d = load(sp)
    iss = d.get('issue')
    if not iss:
        continue
    cur = {}
    for key, rec in (d.get('sites') or {}).items():
        if key.startswith('bdmijg-'):
            continue
        cols = rec.get('columns') or {}
        v = (cols.get('杀特3肖') or cols.get('绝杀三肖') or cols.get('📛绝杀三肖') or {}).get('value')
        sk = str(rec.get('siteKey'))
        if v:
            if sk not in sites_meta:   # 快照里有、历史库没有的站（新站/无历史）
                sites_meta[sk] = {'siteKey': sk, 'system': key.split('-')[0] if '-' in key else 'wanpz'}
            cur[sk] = zchars(v)
    if cur:
        cur_issue = int(iss)
        snap_time = d.get('generated_at') or None
        periods.setdefault(cur_issue, {}).update(cur)

# ---- 组台账
out_periods = {}
for iss in sorted(periods):
    st = {}
    sp_num, sp_z = (draws.get(iss, (None, None)))
    for sid, zs in periods[iss].items():
        hit = None if sp_z is None else (sp_z not in zs)
        st[sid] = {
            'siteKey': sid,
            'system': sites_meta[sid]['system'],
            'status': '有三肖',
            'zodiacs': zs,
            'hit': hit,
            'changed': False,
        }
    out_periods[str(iss)] = {
        'specialNum': sp_num,
        'actual': sp_z,
        'stations': st,
    }

out = {
    'updated_at': snap_time or sc.get('updatedAt', ''),
    'rule': '杀特3肖：当期特肖不在所杀3肖内记为「中」；连对/连错按逐期尾段推导；只收本站固定杀三肖栏，跳转外站的链接不计',
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
