#!/usr/bin/env python3
# 群众走向验证：开奖前冻结 12 肖拥挤分，开奖后打分。
# 只读公开推荐数据；不接订单、资金、上家。
import json, math, os, sys
from collections import defaultdict
from datetime import datetime
from statistics import pstdev

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_engine import DATA, ZODIACS, zscores, norm_entropy, rank_desc, top_set, wilson

START = 325
STATE_PATH = os.path.join(DATA, 'crowd-validation.json')


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def sid(s):
    return s.get('siteId') or (str(s.get('system', '')) + ':' + str(s.get('siteKey', '')))


def compute_from_recommend(period):
    cur = load('current-recommend.json')
    if int(cur.get('period', 0)) != int(period):
        raise RuntimeError(f'current-recommend period={cur.get("period")} != {period}')
    kill_counts = defaultdict(int)
    nine_counts = defaultdict(int)
    first_counts = defaultdict(int)
    kill_sites = nine_sites = first_sites = 0
    seen = set()
    for s in cur.get('sites', []):
        k = sid(s)
        if k in seen:
            continue
        seen.add(k)
        kz = s.get('killZodiacs') or []
        if len(kz) == 3:
            kill_sites += 1
            for z in kz:
                if z in ZODIACS:
                    kill_counts[z] += 1
        nz = s.get('zodiacs') or []
        if len(nz) == 9:
            nine_sites += 1
            first_sites += 1
            for z in nz:
                if z in ZODIACS:
                    nine_counts[z] += 1
            if nz[0] in ZODIACS:
                first_counts[nz[0]] += 1
    if not kill_sites or not nine_sites:
        raise RuntimeError('not enough recommendation sites')
    zk, sk = zscores(kill_counts, kill_sites)
    zn, sn = zscores(nine_counts, nine_sites)
    zf, sf = zscores(first_counts, first_sites)
    crowd = {z: round(0.5 * zn[z] + 0.25 * zk[z] + 0.25 * zf[z], 3) for z in ZODIACS}
    top_nine = top_set(nine_counts, 1)[0]
    top_kill = top_set(kill_counts, 1)[0]
    top_first = top_set(first_counts, 1)[0]
    top_nine_all = [z for z in ZODIACS if nine_counts.get(z, 0) == nine_counts[top_nine]]
    top_kill_all = [z for z in ZODIACS if kill_counts.get(z, 0) == kill_counts[top_kill]]
    top_first_all = [z for z in ZODIACS if first_counts.get(z, 0) == first_counts[top_first]]
    ordered = sorted(ZODIACS, key=lambda z: (-crowd[z], ZODIACS.index(z)))
    return {
        'period': int(period),
        'source': cur.get('source'),
        'updatedAt': cur.get('updatedAt'),
        'mergeMode': cur.get('mergeMode'),
        'mergedSources': cur.get('mergedSources'),
        'coverage': cur.get('coverage'),
        'killSites': kill_sites,
        'nineSites': nine_sites,
        'firstSites': first_sites,
        'counts': {
            'kill3': {z: kill_counts.get(z, 0) for z in ZODIACS},
            'nine': {z: nine_counts.get(z, 0) for z in ZODIACS},
            'first': {z: first_counts.get(z, 0) for z in ZODIACS},
        },
        'shares': {
            'kill3': {z: round(sk[z], 4) for z in ZODIACS},
            'nine': {z: round(sn[z], 4) for z in ZODIACS},
            'first': {z: round(sf[z], 4) for z in ZODIACS},
        },
        'zscores': {'kill3': zk, 'nine': zn, 'first': zf},
        'crowdScore': crowd,
        'ranks': {
            'kill3': {z: rank_desc(kill_counts, z) for z in ZODIACS},
            'nine': {z: rank_desc(nine_counts, z) for z in ZODIACS},
            'first': {z: rank_desc(first_counts, z) for z in ZODIACS},
        },
        'top': {'nine': top_nine, 'kill3': top_kill, 'first': top_first},
        'topTies': {'nine': top_nine_all, 'kill3': top_kill_all, 'first': top_first_all},
        'top3': ordered[:3],
        'bottom3': ordered[-3:],
        'entropy': {
            'kill3': norm_entropy(kill_counts),
            'nine': norm_entropy(nine_counts),
            'first': norm_entropy(first_counts),
        },
        'topGap': {
            'nine': nine_counts[top_nine] - sorted(nine_counts.values(), reverse=True)[1],
            'kill3': kill_counts[top_kill] - sorted(kill_counts.values(), reverse=True)[1],
            'first': first_counts[top_first] - sorted(first_counts.values(), reverse=True)[1],
        },
        'note': '开奖前冻结；冻结后不改权重、不改区间。',
    }


def freeze(period=None, preview=False, force=False):
    cur = load('current-recommend.json')
    if period is None:
        period = int(cur.get('period', 0))
    out = compute_from_recommend(period)
    name = ('crowd-preview-' if preview else 'crowd-freeze-') + str(period) + '.json'
    path = os.path.join(DATA, name)
    out['schema'] = 'crowd-freeze/v1'
    out['status'] = 'PREVIEW' if preview else 'FROZEN'
    out['frozenAt'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    out['validation'] = not preview
    if os.path.exists(path) and not force and not preview:
        print(f'FROZEN_SKIP {name}')
        return
    save(name, out)
    print(f'{"PREVIEW" if preview else "FROZEN"} {name} top3=' + '/'.join(out['top3']))
    if not preview:
        aggregate()


def actual_of(period):
    dr = load('draws-recent.json')
    for p in dr.get('periods', []):
        if int(p.get('issue', 0)) == int(period):
            return p.get('specialZodiac'), p.get('special')
    # fallback: 开奖后台账
    for f in ('max-zodiac-ledger.json', 'kill3-ledger.json'):
        d = load(f).get('periods', {}).get(str(period), {})
        if d.get('actual'):
            return d.get('actual'), d.get('specialNum')
    return None, None


def score(period):
    fname = f'crowd-freeze-{period}.json'
    if not os.path.exists(os.path.join(DATA, fname)):
        print(f'SCORE_SKIP no {fname}')
        return
    fz = load(fname)
    if fz.get('status') != 'FROZEN':
        print(f'SCORE_SKIP {fname} status={fz.get("status")}')
        return
    actual, special = actual_of(period)
    if not actual:
        print(f'SCORE_SKIP no actual for {period}')
        return
    scores = fz['crowdScore']
    rank = rank_desc({z: scores.get(z, 0) for z in ZODIACS}, actual)
    m1 = scores.get(actual, 0)
    others = [scores[z] for z in ZODIACS if z != actual]
    m0 = sum(others) / len(others)
    sd = pstdev([scores[z] for z in ZODIACS]) or 1
    pb = round((m1 - m0) / sd * math.sqrt((1 / 12) * (11 / 12)), 4)
    out = {
        'schema': 'crowd-score/v1',
        'period': int(period),
        'actual': actual,
        'specialNum': special,
        'rank': rank,
        'percentile': round(rank / 12, 4),
        'top3': fz['top3'],
        'bottom3': fz['bottom3'],
        'top3Hit': actual in fz['top3'],
        'top1Hit': actual == fz['top3'][0],
        'bottom3Avoid': actual not in fz['bottom3'],
        'pointBiserial': pb,
        'crowdScore': scores,
        'frozenAt': fz.get('frozenAt'),
        'source': fz.get('source'),
        'scoredAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'validation': True,
    }
    save(f'crowd-score-{period}.json', out)
    print(f'SCORE_OK {period} actual={actual} rank={rank} top3={out["top3Hit"]}')
    aggregate()


def aggregate():
    scores = []
    for fn in os.listdir(DATA):
        if fn.startswith('crowd-score-') and fn.endswith('.json'):
            d = load(fn)
            if d.get('validation') and int(d.get('period', 0)) >= START:
                scores.append(d)
    scores.sort(key=lambda x: x['period'])
    n = len(scores)
    top3 = sum(1 for x in scores if x.get('top3Hit'))
    top1 = sum(1 for x in scores if x.get('top1Hit'))
    b3 = sum(1 for x in scores if x.get('bottom3Avoid'))
    ranks = [x.get('rank') for x in scores if x.get('rank')]
    pbs = [x.get('pointBiserial') for x in scores if x.get('pointBiserial') is not None]
    doc = {
        'schema': 'crowd-validation/v1',
        'updatedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'periods': [x['period'] for x in scores],
        'n': n,
        'lastPeriod': scores[-1]['period'] if scores else None,
        'status': 'COLLECTING' if n < 20 else ('REVIEW' if n < 45 else 'HARD_REVIEW'),
        'top3': {
            'hits': top3,
            'rate': round(top3 / n, 4) if n else None,
            'baseline': 0.25,
            'ci': [round(x, 4) for x in wilson(top3, n)] if n else [None, None],
        },
        'top1': {
            'hits': top1,
            'rate': round(top1 / n, 4) if n else None,
            'baseline': round(1 / 12, 4),
            'ci': [round(x, 4) for x in wilson(top1, n)] if n else [None, None],
        },
        'bottom3': {
            'avoids': b3,
            'rate': round(b3 / n, 4) if n else None,
            'baseline': 0.75,
            'ci': [round(x, 4) for x in wilson(b3, n)] if n else [None, None],
        },
        'meanRank': round(sum(ranks) / len(ranks), 3) if ranks else None,
        'meanPointBiserial': round(sum(pbs) / len(pbs), 4) if pbs else None,
        'milestones': [
            {'period': 330, 'label': '15期完整性 + 初次信号观察'},
            {'period': 335, 'label': '20期第一次样本外检验'},
            {'period': 360, 'label': '45期硬门槛'},
        ],
        'notes': [
            '只统计 325 起、开奖前冻结的期；316–324 是探索样本，不进入验证。',
            'top3 随机基线 25%，top1 随机基线 8.33%，bottom3 规避基线 75%。',
            '先定主指标，再看结果；不按事后最小 p 值换指标。',
        ],
    }
    save('crowd-validation.json', doc)
    print(f'VALIDATION_OK n={n} top3={top3}/{n}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'freeze'
    if cmd == 'freeze':
        args = sys.argv[2:]
        period = None; preview = False; force = False
        for a in args:
            if a == '--preview': preview = True
            elif a == '--force': force = True
            elif a.startswith('--period='): period = int(a.split('=', 1)[1])
        freeze(period, preview, force)
    elif cmd == 'score':
        period = None
        for a in sys.argv[2:]:
            if a.startswith('--period='): period = int(a.split('=', 1)[1])
        if period is None:
            period = int(load('current-recommend.json').get('period', 0))
        score(period)
    elif cmd == 'aggregate':
        aggregate()
    else:
        raise SystemExit('usage: crowd_validation.py freeze|score|aggregate [--period=325] [--preview] [--force]')
