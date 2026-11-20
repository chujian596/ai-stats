#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把站方核心杀口径（快照）压成 stats.html 可直接读的 JSON。
用法: python3 build_core_view.py [期号]
读: snapshots/snapshot-<期>-*.json + signal-calibration.json
写: ai-stats/data/core-<期>.json
"""
import json, os, re, glob, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.dirname(ROOT)
DATA_DIR = os.path.join(ROOT, "data")
Z = list("鼠牛虎兔龙蛇马羊猴鸡狗猪")
CORE_KILL = ['杀特3肖', '绝杀三肖', '绝杀专区']
CORE_RE = re.compile(r'^(杀特3肖|绝杀三肖|绝杀专区|杀3肖)$')
WIDE_RE = re.compile(r'^(杀特\d肖|绝杀三肖|绝杀专区|杀\d+肖|杀1肖平特|杀特1肖)$')

def zods(s):
    return [z for z in Z if z in str(s)]

def bin_of(pct, rows):
    for r in rows:
        lo, hi = r['bin'].replace('%','').split('-')
        if float(lo) <= pct < float(hi): return r
    return None

def main():
    period = sys.argv[1] if len(sys.argv)>1 else None
    if not period:
        period = json.load(open(os.path.join(DATA_DIR,'latest-period.json'),encoding='utf-8'))['period']
    period = str(period)
    files = glob.glob(os.path.join(BASE,'snapshots',f'snapshot-{period}-*.json'))
    if not files: raise SystemExit(f'没有 {period} 期快照')
    def gen_at(f):
        try: return json.load(open(f,encoding='utf-8')).get('generated_at') or ''
        except Exception: return ''
    files = sorted(files, key=lambda f: (gen_at(f), f))
    snap = json.load(open(files[-1], encoding='utf-8'))
    sites = snap['sites']
    core_v = defaultdict(set); wide_v = defaultdict(set); den = 0; wide_den = 0
    for key, rec in sites.items():
        has = False
        for name, c in rec.get('columns', {}).items():
            zs = zods(c.get('value'))
            if not zs: continue
            if CORE_RE.match(name):
                has = True
                for z in zs: core_v[z].add(key)
            if WIDE_RE.match(name):
                for z in zs: wide_v[z].add(key)
        if has: den += 1
        if any(WIDE_RE.match(n2) and zods(c2.get('value')) for n2, c2 in rec.get('columns', {}).items()):
            wide_den += 1
    cal = json.load(open(os.path.join(BASE,'signal-calibration.json'),encoding='utf-8'))
    rows = []
    for z in Z:
        pct = round(len(core_v[z])/den*100,1) if den else 0.0
        b = bin_of(pct, cal['kill'])
        rows.append({
            'z': z,
            'coreSites': len(core_v[z]), 'coreDen': den, 'corePct': pct,
            'wideSites': len(wide_v[z]), 'widePct': round(len(wide_v[z])/wide_den*100,1) if wide_den else 0.0,
            'bin': b['bin'] if b else '',
            'histRate': b['rate'] if b else None,
            'histN': b['n'] if b else None,
            'histCi': b['ci'] if b else '',
            'verdict': (b['verdict'].split('（')[0] if b else '无档位'),
        })
    out = {'period': int(period), 'sites': len(sites), 'coreDen': den, 'wideDen': wide_den,
           'source': os.path.basename(files[-1]), 'generatedAt': snap.get('generated_at'),
           'calibIssues': cal.get('issues'),
           'rows': rows}
    p = os.path.join(DATA_DIR,f'core-{period}.json')
    json.dump(out, open(p,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print('written', p, 'coreDen', den, 'wideDen', wide_den, 'sites', len(sites))
    for r in rows: print(r['z'], r['corePct'], r['bin'], r['verdict'], r['widePct'])

main()
