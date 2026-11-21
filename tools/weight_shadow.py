#!/usr/bin/env python3
# 权重影子账：等权 / 全指纹封顶 / 维度封顶三路并行。
# 只做复盘对照，不替换 engine 方向，不发投注指令。
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
ZODIACS = list('鼠牛虎兔龙蛇马羊猴鸡狗猪')
START = 325
ARMS = ('equal', 'full_cap', 'dim_cap')


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def dval(s, key):
    if key in ('zodiacs', 'killZodiacs'):
        return s.get(key) or []
    return (s.get(key) or {}).get('picks') or []


def zscores(counts, n):
    shares = {z: (counts.get(z, 0) / n if n else 0) for z in ZODIACS}
    mean = sum(shares.values()) / len(ZODIACS)
    sd = math.sqrt(sum((v - mean) ** 2 for v in shares.values()) / len(ZODIACS)) or 1
    return {z: round((shares[z] - mean) / sd, 3) for z in ZODIACS}


def top(counts, n=3):
    return sorted(ZODIACS, key=lambda z: (-counts.get(z, 0), ZODIACS.index(z)))[:n]


def bottom(counts, n=3):
    return sorted(ZODIACS, key=lambda z: (counts.get(z, 0), ZODIACS.index(z)))[:n]


def rank(counts, z):
    return 1 + sum(1 for x in ZODIACS if counts.get(x, 0) > counts.get(z, 0))


def weff(row, dim, arm):
    if row.get('empty'):
        return 0.0
    if arm == 'equal':
        return 1.0
    if arm == 'full_cap':
        return float(row.get('weight') or 0)
    # dim_cap: 只封九肖/杀三/尾数；平特、波色、头数、大小、单双保持等权
    if dim in ('nine', 'first'):
        return float(row.get('nineWeight') or 0)
    if dim == 'kill':
        return float(row.get('killWeight') or 0)
    if dim == 'tail':
        return float(row.get('tailWeight') or 0)
    return 1.0


def build(period=None, status='PREVIEW'):
    ind = load('independence.json')
    cur = load('current-recommend.json')
    if period is None:
        period = int(cur.get('period', 0))
    if int(cur.get('period', 0)) != int(period):
        raise RuntimeError('current-recommend period mismatch')
    rows = ind.get('sites') or []
    out_arms = {}
    for arm in ARMS:
        counts = {d: defaultdict(float) for d in ('nine', 'kill', 'first', 'tail', 'head', 'pingte', 'wave', 'size', 'parity')}
        total = defaultdict(float)
        for row in rows:
            if not row.get('dataDims'):
                continue
            s = next((x for x in cur.get('sites', []) if (x.get('siteId') or (str(x.get('system')) + ':' + str(x.get('siteKey')))) == row['siteId']), None)
            if not s:
                continue
            nz = s.get('zodiacs') or []
            if nz:
                w = weff(row, 'nine', arm)
                for z in nz:
                    if z in ZODIACS:
                        counts['nine'][z] += w
                total['nine'] += w
                if nz[0] in ZODIACS:
                    counts['first'][nz[0]] += w
                    total['first'] += w
            if s.get('killZodiacs'):
                wk = weff(row, 'kill', arm)
                for z in s['killZodiacs']:
                    if z in ZODIACS:
                        counts['kill'][z] += wk
                total['kill'] += wk
            for d, key in (('tail', 'tail'), ('head', 'head'), ('pingte', 'pingte'), ('wave', 'wave'), ('size', 'size'), ('parity', 'parity')):
                vals = dval(s, key)
                if vals:
                    wd = weff(row, d, arm)
                    for v in vals:
                        counts[d][str(v)] += wd
                    total[d] += wd
        zn = zscores(counts['nine'], total['nine'])
        zk = zscores(counts['kill'], total['kill'])
        zf = zscores(counts['first'], total['first'])
        crowd = {z: round(0.5 * zn[z] + 0.25 * zk[z] + 0.25 * zf[z], 3) for z in ZODIACS}
        out_arms[arm] = {
            'label': {'equal': '等权', 'full_cap': '全指纹封顶', 'dim_cap': '九肖/杀三/尾数封顶'}[arm],
            'top3': top(crowd),
            'bottom3': bottom(crowd),
            'crowdScore': crowd,
            'ranks': {z: rank(crowd, z) for z in ZODIACS},
            'counts': {d: {z: round(v, 3) for z, v in counts[d].items()} for d in counts},
            'effectiveN': {d: round(total[d], 3) for d in total},
            'topNine': top(counts['nine']),
            'topKill': top(counts['kill']),
            'topFirst': top(counts['first']),
        }
    return {
        'schema': 'weight-shadow/v1',
        'period': int(period),
        'status': status,
        'updatedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source': cur.get('source'),
        'arms': out_arms,
        'differences': {
            'top3Changed': out_arms['equal']['top3'] != out_arms['dim_cap']['top3'],
            'fullCapChanged': out_arms['equal']['top3'] != out_arms['full_cap']['top3'],
            'dimCapChanged': out_arms['equal']['top3'] != out_arms['dim_cap']['top3'],
        },
        'notes': [
            'equal=全站等权；full_cap=同8维全指纹只算一票；dim_cap=九肖/杀三/尾数同值封顶。',
            '三路都只是影子账，不替换 engine，不生成投注指令。',
            '全指纹同模板才有较强证据；同九肖不等于同模板，dim_cap 是压力测试，不是定论。',
        ],
    }


def actual_of(period):
    dr = load('draws-recent.json')
    for p in dr.get('periods', []):
        if int(p.get('issue', 0)) == int(period):
            return p.get('specialZodiac'), p.get('special')
    for f in ('max-zodiac-ledger.json', 'kill3-ledger.json'):
        d = load(f).get('periods', {}).get(str(period), {})
        if d.get('actual'):
            return d.get('actual'), d.get('specialNum')
    return None, None


def score_one(period):
    fp = os.path.join(DATA, f'weight-freeze-{period}.json')
    if not os.path.exists(fp):
        print(f'SCORE_SKIP no freeze {period}')
        return
    fz = load(f'weight-freeze-{period}.json')
    if fz.get('status') != 'FROZEN':
        print(f'SCORE_SKIP not frozen {period}')
        return
    actual, special = actual_of(period)
    if not actual:
        print(f'SCORE_SKIP no actual {period}')
        return
    arms = {}
    for arm, a in fz['arms'].items():
        scores = a['crowdScore']
        r = rank(scores, actual)
        m1 = scores.get(actual, 0)
        others = [scores[z] for z in ZODIACS if z != actual]
        m0 = sum(others) / len(others)
        sd = (sum((scores[z] - m0) ** 2 for z in ZODIACS) / len(ZODIACS)) ** 0.5 or 1
        pb = round((m1 - m0) / sd * math.sqrt((1 / 12) * (11 / 12)), 4)
        arms[arm] = {
            'top3': a['top3'],
            'bottom3': a['bottom3'],
            'rank': r,
            'top3Hit': actual in a['top3'],
            'top1Hit': actual == a['top3'][0],
            'bottom3Avoid': actual not in a['bottom3'],
            'pointBiserial': pb,
            'effectiveN': a['effectiveN'],
        }
    out = {
        'schema': 'weight-score/v1',
        'period': int(period),
        'actual': actual,
        'specialNum': special,
        'arms': arms,
        'frozenAt': fz.get('frozenAt'),
        'source': fz.get('source'),
        'scoredAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    save(f'weight-score-{period}.json', out)
    print(f'SCORE_OK {period} actual={actual} ' + ' '.join(
        f'{a}:rank={arms[a]["rank"]},top3={arms[a]["top3Hit"]}' for a in ARMS))
    aggregate()


def aggregate():
    scores = []
    for fn in os.listdir(DATA):
        if fn.startswith('weight-score-') and fn.endswith('.json'):
            d = load(fn)
            if int(d.get('period', 0)) >= START:
                scores.append(d)
    scores.sort(key=lambda x: x['period'])
    n = len(scores)
    stats = {}
    for arm in ARMS:
        rows = [x['arms'][arm] for x in scores if arm in x.get('arms', {})]
        t3 = sum(1 for x in rows if x.get('top3Hit'))
        t1 = sum(1 for x in rows if x.get('top1Hit'))
        b3 = sum(1 for x in rows if x.get('bottom3Avoid'))
        ranks = [x.get('rank') for x in rows if x.get('rank')]
        pbs = [x.get('pointBiserial') for x in rows if x.get('pointBiserial') is not None]
        stats[arm] = {
            'n': len(rows),
            'top3': {'hits': t3, 'rate': round(t3 / len(rows), 4) if rows else None},
            'top1': {'hits': t1, 'rate': round(t1 / len(rows), 4) if rows else None},
            'bottom3': {'avoids': b3, 'rate': round(b3 / len(rows), 4) if rows else None},
            'meanRank': round(sum(ranks) / len(ranks), 3) if ranks else None,
            'meanPointBiserial': round(sum(pbs) / len(pbs), 4) if pbs else None,
        }
    eq = stats.get('equal', {})
    for arm in ARMS:
        a = stats.get(arm, {})
        a['deltaVsEqual'] = {
            'top3': (a.get('top3', {}).get('rate') or 0) - (eq.get('top3', {}).get('rate') or 0) if n else None,
            'meanRank': (a.get('meanRank') - eq.get('meanRank')) if n and a.get('meanRank') is not None and eq.get('meanRank') is not None else None,
        }
    save('weight-validation.json', {
        'schema': 'weight-validation/v1',
        'updatedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'cohortStart': START,
        'periods': [x['period'] for x in scores],
        'n': n,
        'lastPeriod': scores[-1]['period'] if scores else None,
        'status': 'COLLECTING' if n < 20 else ('REVIEW' if n < 45 else 'HARD_REVIEW'),
        'arms': stats,
        'milestones': [
            {'period': 330, 'label': '6期 · 完整性检查'},
            {'period': 335, 'label': '11期 · 首次样本外观察'},
            {'period': 344, 'label': '20期 · 进入 REVIEW，才谈权重是否有用'},
            {'period': 369, 'label': '45期 · 才谈硬规则'},
        ],
        'notes': [
            '主指标先定：Top3 命中、平均排名、Brier/logloss；不在事后换指标。',
            '20期前只观察，不因几期好看就替换实盘。',
            '全指纹封顶是结构口径；维度封顶是压力测试，失败就撤。',
        ],
    })
    print(f'VALIDATION_OK n={n} ' + ' '.join(f'{a}:{stats[a]["top3"]["hits"]}/{stats[a]["n"]}' for a in ARMS))


def write_freeze(period, force=False, preview=False):
    status = 'PREVIEW' if preview else 'FROZEN'
    out = build(period, status)
    prefix = 'weight-preview-' if preview else 'weight-freeze-'
    fname = prefix + str(period) + '.json'
    path = os.path.join(DATA, fname)
    if not preview and os.path.exists(path) and not force:
        print(f'FROZEN_SKIP {fname}')
        return
    if not preview:
        out['frozenAt'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save(fname, out)
    save('weight-shadow.json', out)
    print(f'{status} {fname} equal=' + '/'.join(out['arms']['equal']['top3']) +
          ' full=' + '/'.join(out['arms']['full_cap']['top3']) +
          ' dim=' + '/'.join(out['arms']['dim_cap']['top3']))
    if not preview:
        aggregate()


def update():
    cur = load('current-recommend.json')
    period = int(cur.get('period', 0))
    hh = datetime.now().hour
    mm = datetime.now().minute
    # 只在 20:00-21:29 冻结，避免白天提前锁死影子账
    if hh == 20 or (hh == 21 and mm < 30):
        fp = os.path.join(DATA, f'weight-freeze-{period}.json')
        if not os.path.exists(fp):
            write_freeze(period, force=False)
        else:
            print(f'FROZEN_SKIP weight-freeze-{period}.json')
    # 每次运行都尝试补分已冻结但未打分的期
    for fn in sorted(os.listdir(DATA)):
        if fn.startswith('weight-freeze-') and fn.endswith('.json'):
            p = int(fn.replace('weight-freeze-', '').replace('.json', ''))
            if not os.path.exists(os.path.join(DATA, f'weight-score-{p}.json')):
                score_one(p)
    aggregate()


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'update'
    if cmd == 'preview':
        period = int(sys.argv[2]) if len(sys.argv) > 2 else None
        write_freeze(period, preview=True)
    elif cmd == 'freeze':
        period = int(sys.argv[2]) if len(sys.argv) > 2 else None
        write_freeze(period, force=True)
    elif cmd == 'score':
        period = int(sys.argv[2]) if len(sys.argv) > 2 else int(load('current-recommend.json').get('period', 0))
        score_one(period)
    else:
        update()
