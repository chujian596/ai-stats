#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""四维度逐站逐期台账：平特一肖 / 波色 / 尾数 / 头数。

数据源：
  - 本地快照 ../snapshots/（early 18* / late 20*，晚份优先入账，早晚不一致标 changed）
  - 历史库 data/sites-current.json 的 history['平特1肖']（仅平特一肖可回溯早期）
  - 开奖 ../4901988-draws.json（七肖集合 / 特码波色 / 尾 / 头）

判定口径：
  平特一肖：推肖 ∈ 当期 6 平码生肖 ∪ 特肖（七肖集合）
  波色：    特码波色 ∈ 推色集合（红/蓝/绿）
  尾数：    特码个位 ∈ 推尾集合（0-9）
  头数：    特码头位 ∈ 推头集合（0-9，0 代表个位数号）

产出：data/pingte-ledger.json / wave-ledger.json / tail-ledger.json / head-ledger.json
样本不足只记录不定论；质检只做一致性核对，不改成绩。
"""
import json, glob, os, re, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
DRAW = PARENT / '4901988-draws.json'
SNAP = PARENT / 'snapshots'
ZOD = '鼠牛虎兔龙蛇马羊猴鸡狗猪'
WAVE = '红蓝绿'


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


# ---- 开奖源 ----
draws = {}
for k, v in load(DRAW).items():
    if not isinstance(v, dict):
        continue
    sp = v.get('special')
    if not sp:
        continue
    sp = int(sp)
    meta = {m['n']: m for m in v.get('meta', [])}
    plains = v.get('plains', [])
    plains_zod = [meta[n]['zodiac'] for n in plains if n in meta]
    sp_zod = meta[sp]['zodiac'] if sp in meta else v.get('special_zodiac')
    draws[int(k)] = {
        'sp': sp, 'sp_zod': sp_zod,
        'seven': set(plains_zod) | {sp_zod},
        'wave': meta[sp]['wave'] if sp in meta else None,
        'tail': sp % 10, 'head': sp // 10,
    }

# ---- 栏目提取：返回 (栏目名, picks, 原文) 或 None ----
def pick_pingte(cols):
    order = ['平特1肖', '平特一肖', '2期1肖平特', '3期1肖平特', '1肖加对应1码平特']
    for t in order:
        cd = cols.get(t)
        if cd and cd.get('value'):
            z = [c for c in cd['value'] if c in ZOD]
            if len(z) == 1:
                return (t, z, cd['value'])
    return None


def pick_wave(cols):
    cd = cols.get('2波中特')
    if cd and cd.get('value'):
        w = [c for c in cd['value'] if c in WAVE]
        if w:
            return ('2波中特', w, cd['value'])
    return None


def pick_tail(cols):
    cands = [(t, cd) for t, cd in cols.items()
             if '尾中特' in t and '平特' not in t and '头' not in t
             and '单双' not in t and '各4尾' not in t and '字数字' not in t]
    cands.sort(key=lambda x: 0 if re.fullmatch(r'\d尾中特', x[0]) else 1)
    for t, cd in cands:
        v = cd.get('value') or ''
        ds = sorted(set(c for c in v if c.isdigit()))
        if ds:
            return (t, ds, v)
    return None


def pick_head(cols):
    cands = [(t, cd) for t, cd in cols.items() if '头中特' in t and '尾' not in t]
    for t, cd in cands:
        v = cd.get('value') or ''
        ds = sorted(set(c for c in v if c.isdigit()))
        if ds:
            return (t, ds, v)
    return None


PICKERS = {'pingte': pick_pingte, 'wave': pick_wave, 'tail': pick_tail, 'head': pick_head}
DIM_TITLE = {'pingte': '平特一肖', 'wave': '波色', 'tail': '尾数', 'head': '头数'}


def site_of(rec, key):
    sk = str(rec.get('siteKey') or key.split('-')[-1])
    sys = key.split('-')[0]
    return sk, sys


def snap_pick(snap, dim):
    out = {}
    picker = PICKERS[dim]
    for key, rec in (snap.get('sites') or {}).items():
        pk = picker(rec.get('columns') or {})
        if not pk:
            continue
        sk, sys = site_of(rec, key)
        out[sk] = {'system': sys, 'column': pk[0], 'picks': pk[1], 'raw': pk[2]}
    return out


def find_snapshots(issue):
    e = sorted(glob.glob(os.path.join(SNAP, f'snapshot-{issue}-18*.json')))
    l = sorted(glob.glob(os.path.join(SNAP, f'snapshot-{issue}-20*.json')))
    return (e[0] if e else None, l[-1] if l else None)


def hit_of(dim, picks, dr):
    if dim == 'pingte':
        return picks[0] in dr['seven']
    if dim == 'wave':
        return dr['wave'] in picks
    if dim == 'tail':
        return str(dr['tail']) in picks
    if dim == 'head':
        return str(dr['head']) in picks
    return False


# ---- 历史库（仅平特1肖）----
sc = load(ROOT / 'data' / 'sites-current.json')
hist = {}  # hist[iss][sk] = {'picks':[z], 'raw':val}
for s in sc['sites']:
    h = (s.get('history') or {}).get('平特1肖') or {}
    for iss, val in h.items():
        z = [c for c in val if c in ZOD]
        if len(z) == 1:
            hist.setdefault(int(iss), {})[s['id']] = {'picks': z, 'raw': val, 'system': 'wanpz'}

# ---- 快照按期归集 ----
snap_issues = sorted({int(os.path.basename(f).split('-')[1])
                      for f in glob.glob(os.path.join(SNAP, 'snapshot-*.json'))
                      if os.path.basename(f).split('-')[1].isdigit()})

ledgers = {dim: {'updated_at': None, 'rule': '', 'periods': {}} for dim in PICKERS}

for iss, dr in draws.items():
    early_path, late_path = find_snapshots(iss)
    # 各维度分别取快照
    snap_data = {}
    if early_path:
        es = load(Path(early_path))
        ls = load(Path(late_path)) if late_path else None
        for dim in PICKERS:
            snap_data[dim] = (snap_pick(es, dim), snap_pick(ls, dim) if ls else {})

    for dim in PICKERS:
        stations = {}
        # 历史库仅平特
        if dim == 'pingte' and iss in hist:
            for sk, hrec in hist[iss].items():
                stations[sk] = {'system': hrec['system'], 'siteKey': sk, 'column': '平特1肖(历史库)',
                                'picks': hrec['picks'], 'raw': hrec['raw'],
                                'hit': hit_of(dim, hrec['picks'], dr),
                                'changed': False, 'latePicks': None}
        # 快照覆盖/补充
        if early_path:
            ep, lp = snap_data[dim]
            for sk in set(ep) | set(lp):
                e = ep.get(sk); l = lp.get(sk)
                rec = l or e
                changed = bool(e and l and e['picks'] != l['picks'])
                stations[sk] = {
                    'system': rec['system'], 'siteKey': sk, 'column': rec['column'],
                    'picks': rec['picks'], 'raw': rec['raw'],
                    'hit': hit_of(dim, rec['picks'], dr),
                    'changed': changed,
                    'latePicks': l['picks'] if changed else None,
                }
        if stations:
            ledgers[dim]['periods'][str(iss)] = {
                'specialNum': dr['sp'], 'actual': dr['sp_zod'],
                'actualWave': dr['wave'], 'actualTail': dr['tail'], 'actualHead': dr['head'],
                'hasSnapshot': early_path is not None,
                'source': 'snapshot' if early_path else 'history',
                'stations': stations,
            }

rules = {
    'pingte': '平特一肖：推肖落在当期 6 平码生肖 ∪ 特肖（七肖）内记「中」；只取单肖栏，多肖/成语诗句/杀平栏不计。',
    'wave': '波色：特码波色落在站推双色内记「中」；取「2波中特」栏。',
    'tail': '尾数：特码个位落在站推尾数集合内记「中」；取纯数字尾栏，单双/复合尾栏不计。',
    'head': '头数：特码头位落在站推头数集合内记「中」；取纯数字头栏。',
}
out_files = {'pingte': 'pingte-ledger.json', 'wave': 'wave-ledger.json',
             'tail': 'tail-ledger.json', 'head': 'head-ledger.json'}

latest_at = ''
for f in glob.glob(os.path.join(SNAP, 'snapshot-*.json')):
    try:
        latest_at = max(latest_at, load(Path(f)).get('generated_at') or '')
    except Exception:
        pass

for dim, fn in out_files.items():
    ledgers[dim]['updated_at'] = latest_at
    ledgers[dim]['rule'] = rules[dim]
    (ROOT / 'data' / fn).write_text(
        json.dumps(ledgers[dim], ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    ps = ledgers[dim]['periods']
    line = []
    for i in sorted(ps, key=int)[-4:]:
        st = ps[i]['stations']
        hit = sum(1 for r in st.values() if r['hit'])
        line.append(f"{i}:站{len(st)}/中{hit}")
    print(f"{DIM_TITLE[dim]} {len(ps)} 期  " + '  '.join(line))
