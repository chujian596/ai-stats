#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从最新 snapshot + 历史库生成 data/sites-current.json（ziliao.html 数据源）"""
import json, re, glob, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
ZOD = '鼠牛虎兔龙蛇马羊猴鸡狗猪'
COLS = ['杀特3肖','杀特6肖','平特1肖','5肖中特','7肖中特','杀特1肖']

def zchars(v):
    return ''.join([c for c in (v or '') if c in ZOD])

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

official = load(ROOT/'official-history.json')
hist = {}
# 历史库（到 317 左右）
mh = load(PARENT/'multi-site-history.json')
for rec in mh:
    sk = str(rec.get('siteKey'))
    h = hist.setdefault(sk, {})
    for col, rows in (rec.get('history') or {}).items():
        if col not in COLS: continue
        h.setdefault(col, {})
        for p, v in rows.items():
            h[col][str(p)] = zchars(v)
# 所有 snapshot（318–322），最新覆盖
snaps = sorted(glob.glob(str(PARENT/'snapshots'/'snapshot-*.json')))
latest = None
for sp in snaps:
    d = load(sp)
    issue = str(d.get('issue',''))
    if not issue: continue
    latest = d
    for key, rec in (d.get('sites') or {}).items():
        if not key.startswith('wanpz-h2-'): continue
        sk = str(rec.get('siteKey'))
        h = hist.setdefault(sk, {})
        for col in COLS:
            v = (rec.get('columns') or {}).get(col,{}).get('value')
            if v:
                h.setdefault(col, {})[issue] = zchars(v)
if not latest:
    raise SystemExit('no snapshot')
issue = int(latest.get('issue'))

sites = []
for key, rec in (latest.get('sites') or {}).items():
    if not key.startswith('wanpz-h2-'): continue
    sk = str(rec.get('siteKey'))
    h = hist.get(sk, {})
    def score(col):
        hit=miss=0
        for p, v in (h.get(col) or {}).items():
            off = official.get(str(p))
            if not off or not off.get('specialZod'): continue
            sp = off['specialZod']
            if col in ('杀特3肖','杀特6肖'):
                (hit:=hit+1) if sp not in v else (miss:=miss+1)
            elif col == '平特1肖':
                if sp in v: hit+=1
                else: miss+=1
        return {'hit':hit,'miss':miss}
    history = {}
    for col in COLS:
        rows = {p:v for p,v in (h.get(col) or {}).items() if v}
        if rows:
            history[col] = dict(sorted(rows.items(), key=lambda kv: -int(kv[0])))
    sites.append({
        'id': sk,
        'widgets': len(rec.get('columns') or {}),
        'period': int(rec.get('issue') or issue),
        'kill3': score('杀特3肖'),
        'kill6': score('杀特6肖'),
        'pingte': score('平特1肖'),
        'history': history
    })

out = {'period': issue, 'updatedAt': latest.get('generated_at',''), 'sites': sites}
(ROOT/'data'/'sites-current.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',',':')), encoding='utf-8')
print(f'sites-current.json: {len(sites)} sites, period {issue}, updated {out["updatedAt"]}')
print('sample', sites[0]['id'], sites[0]['kill3'], sites[0]['kill6'])
