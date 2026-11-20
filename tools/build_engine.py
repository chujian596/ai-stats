#!/usr/bin/env python3
# 研判引擎：把 316 后的九肖/杀三肖/首位票，收束成“拥挤度审计”。
# 输出 data/engine.json（最新）与 data/engine-<期>.json（按期留档）。
# 只做历史统计与信号分级，不生成投注指令。
import json, math, os, random
from collections import defaultdict
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
START = 316
ZODIACS = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']
PERM_B = 5000
SEED = 316324


def wilson(k, n, z=1.96):
    if n <= 0:
        return None, None
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, center - half), min(1.0, center + half)


def rank_desc(counts, z):
    return 1 + sum(1 for x in ZODIACS if counts.get(x, 0) > counts.get(z, 0))


def rank_asc(counts, z):
    return 1 + sum(1 for x in ZODIACS if counts.get(x, 0) < counts.get(z, 0))


def band(rank):
    if rank <= 3:
        return 'top'
    if rank >= 10:
        return 'bottom'
    return 'mid'


def top_set(counts, n=3):
    ordered = sorted(ZODIACS, key=lambda z: (-counts.get(z, 0), ZODIACS.index(z)))
    return ordered[:n]


def norm_entropy(counts):
    total = sum(counts.values())
    if total <= 0:
        return None
    p = [v / total for v in counts.values() if v > 0]
    return round(-sum(x * math.log(x) for x in p) / math.log(len(ZODIACS)), 4)


def zscores(counts, n_sites):
    shares = {z: (counts.get(z, 0) / n_sites if n_sites else 0) for z in ZODIACS}
    mean = sum(shares.values()) / len(ZODIACS)
    var = sum((v - mean) ** 2 for v in shares.values()) / len(ZODIACS)
    sd = math.sqrt(var) if var > 0 else 1
    return {z: round((shares[z] - mean) / sd, 3) for z in ZODIACS}, shares


def binom_p_ge(k, n, p):
    if n <= 0:
        return None
    return round(sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1)), 4)


def binom_p_le(k, n, p):
    if n <= 0:
        return None
    return round(sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(0, k + 1)), 4)


def load_periods():
    kill = json.load(open(os.path.join(DATA, 'kill3-ledger.json'), encoding='utf-8'))
    nine = json.load(open(os.path.join(DATA, 'max-zodiac-ledger.json'), encoding='utf-8'))
    periods = sorted(set(kill.get('periods', {})) & set(nine.get('periods', {})), key=int)
    rows = []
    for p in periods:
        if int(p) < START:
            continue
        kp = kill['periods'][p]
        np = nine['periods'][p]
        actual = np.get('actual') or kp.get('actual')
        kill_counts = defaultdict(int)
        nine_counts = defaultdict(int)
        first_counts = defaultdict(int)
        kill_sites = nine_sites = first_sites = 0
        for s in kp.get('stations', {}).values():
            z = s.get('zodiacs') or []
            if len(z) == 3:
                kill_sites += 1
                for x in z:
                    kill_counts[x] += 1
        for s in np.get('stations', {}).values():
            z = s.get('zodiacs') or []
            if len(z) == 9:
                nine_sites += 1
                first_sites += 1
                for x in z:
                    nine_counts[x] += 1
                first_counts[z[0]] += 1
        if not actual or not kill_sites or not nine_sites:
            continue
        zk, sk = zscores(kill_counts, kill_sites)
        zn, sn = zscores(nine_counts, nine_sites)
        zf, sf = zscores(first_counts, first_sites)
        crowd = {z: round(0.5 * zn[z] + 0.25 * zk[z] + 0.25 * zf[z], 3) for z in ZODIACS}
        top_nine = top_set(nine_counts, 1)[0]
        top_kill = top_set(kill_counts, 1)[0]
        top_first = top_set(first_counts, 1)[0]
        top_kill3 = top_set(kill_counts, 3)
        top_nine_all = [z for z in ZODIACS if nine_counts.get(z,0)==nine_counts[top_nine]]
        top_kill_all = [z for z in ZODIACS if kill_counts.get(z,0)==kill_counts[top_kill]]
        top_first_all = [z for z in ZODIACS if first_counts.get(z,0)==first_counts[top_first]]
        rows.append({
            'period': int(p),
            'actual': actual,
            'specialNum': np.get('specialNum') or kp.get('specialNum'),
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
            'topKill3': top_kill3,
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
            'actualRanks': {
                'kill3': rank_desc(kill_counts, actual),
                'nine': rank_desc(nine_counts, actual),
                'first': rank_desc(first_counts, actual),
            },
            'actualBands': {
                'kill3': band(rank_desc(kill_counts, actual)),
                'nine': band(rank_desc(nine_counts, actual)),
                'first': band(rank_desc(first_counts, actual)),
            },
            'checks': {
                'killTop3Avoid': actual not in top_kill3,
                'nineTopAvoid': actual != top_nine,
                'firstTopAvoid': actual != top_first,
                'nineMiddle': 4 <= rank_desc(nine_counts, actual) <= 9,
            },
        })
    return rows


def hypothesis_stats(rows):
    rng = random.Random(SEED)
    n = len(rows)

    def perm_stat(fn):
        hits = 0
        for _ in range(PERM_B):
            ph = 0
            for r in rows:
                z = rng.choice(ZODIACS)
                ph += bool(fn(r, z))
            hits += ph >= fn_total
        return round((hits + 1) / (PERM_B + 1), 4)

    # 先算观测值
    fn_total = sum(r['checks']['killTop3Avoid'] for r in rows)
    p_kill = perm_stat(lambda r, z: z not in r['topKill3'])
    fn_total = sum(r['checks']['nineTopAvoid'] for r in rows)
    p_nine = perm_stat(lambda r, z: z != r['top']['nine'])
    fn_total = sum(r['checks']['firstTopAvoid'] for r in rows)
    p_first = perm_stat(lambda r, z: z != r['top']['first'])
    fn_total = sum(r['checks']['nineMiddle'] for r in rows)
    p_mid = perm_stat(lambda r, z: 4 <= r['ranks']['nine'][z] <= 9)

    return [
        {
            'id': 'kill_top3_avoid',
            'label': '杀三肖最高3名未开',
            'observed': f"{sum(r['checks']['killTop3Avoid'] for r in rows)}/{n}",
            'observedRate': round(sum(r['checks']['killTop3Avoid'] for r in rows) / n, 4),
            'nullRate': 0.75,
            'pValue': p_kill,
            'status': 'not_significant' if p_kill >= 0.05 else 'watch',
            'note': '杀3肖/12肖，随机不中就是75%；单看8/9不稀奇。',
        },
        {
            'id': 'nine_top_avoid',
            'label': '九肖最高票未开',
            'observed': f"{sum(r['checks']['nineTopAvoid'] for r in rows)}/{n}",
            'observedRate': round(sum(r['checks']['nineTopAvoid'] for r in rows) / n, 4),
            'nullRate': 0.9167,
            'pValue': p_nine,
            'status': 'not_significant' if p_nine >= 0.05 else 'watch',
            'note': '九肖覆盖9个，最高票只是其中1个；不在最高票是常态。',
        },
        {
            'id': 'first_top_avoid',
            'label': '九肖首位最高票未开',
            'observed': f"{sum(r['checks']['firstTopAvoid'] for r in rows)}/{n}",
            'observedRate': round(sum(r['checks']['firstTopAvoid'] for r in rows) / n, 4),
            'nullRate': 0.9167,
            'pValue': p_first,
            'status': 'not_significant' if p_first >= 0.05 else 'watch',
            'note': '首位票是1/12，单条命中低不等于可硬排。',
        },
        {
            'id': 'nine_middle_band',
            'label': '九肖实际落在中段(4–9)',
            'observed': f"{sum(r['checks']['nineMiddle'] for r in rows)}/{n}",
            'observedRate': round(sum(r['checks']['nineMiddle'] for r in rows) / n, 4),
            'nullRate': 0.5,
            'pValue': p_mid,
            'status': 'post_hoc' if p_mid < 0.05 else 'not_significant',
            'note': '9/9落在中段值得跟踪，但这是事后挑选的区间，先不算规律。',
        },
    ]


def mirror_pairs():
    nine = json.load(open(os.path.join(DATA, 'max-zodiac-ledger.json'), encoding='utf-8'))
    periods = [p for p in nine.get('periods', {}) if int(p) >= START]
    sites = defaultdict(dict)
    for p in periods:
        for s in nine['periods'][p].get('stations', {}).values():
            z = s.get('zodiacs') or []
            if len(z) == 9:
                sites[s.get('displayName') or s.get('siteName') or s.get('siteId')][p] = tuple(z)
    names = list(sites)
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            common = set(sites[a]) & set(sites[b])
            if len(common) >= 7 and all(sites[a][p] == sites[b][p] for p in common):
                pairs.append({'a': a, 'b': b, 'periods': len(common)})
    return sorted(pairs, key=lambda x: -x['periods'])


def main():
    rows = load_periods()
    if not rows:
        print('ENGINE_SKIP no rows')
        return
    latest = rows[-1]['period']
    hypotheses = hypothesis_stats(rows)
    pairs = mirror_pairs()
    # 总体信号：只给历史统计，不给方向。
    kill_n = sum(r['killSites'] for r in rows)
    nine_n = sum(r['nineSites'] for r in rows)
    # 用 hit 字段重算总命中，避免把“未中”误读成“杀对”。
    kill_hit = nine_hit = 0
    kill_ledger = json.load(open(os.path.join(DATA, 'kill3-ledger.json'), encoding='utf-8'))
    nine_ledger = json.load(open(os.path.join(DATA, 'max-zodiac-ledger.json'), encoding='utf-8'))
    for p in [str(r['period']) for r in rows]:
        for s in kill_ledger['periods'][p].get('stations', {}).values():
            if len(s.get('zodiacs') or []) == 3 and s.get('hit') is not None:
                kill_hit += bool(s['hit'])
        for s in nine_ledger['periods'][p].get('stations', {}).values():
            if len(s.get('zodiacs') or []) == 9 and s.get('hit') is not None:
                nine_hit += bool(s['hit'])
    klo, khi = wilson(kill_hit, kill_n)
    nlo, nhi = wilson(nine_hit, nine_n)
    first_n = sum(r['firstSites'] for r in rows)
    first_hit = 0
    for p in [str(r['period']) for r in rows]:
        for s in nine_ledger['periods'][p].get('stations', {}).values():
            z = s.get('zodiacs') or []
            if len(z) == 9:
                first_hit += bool(z[0] == nine_ledger['periods'][p].get('actual'))
    flo, fhi = wilson(first_hit, first_n)
    top_kill_hits = sum(r['checks']['killTop3Avoid'] for r in rows)
    top_nine_hits = sum(r['checks']['nineTopAvoid'] for r in rows)
    top_first_hits = sum(r['checks']['firstTopAvoid'] for r in rows)

    doc = {
        'schema': 'engine/v1',
        'generatedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'dataThrough': latest,
        'window': {'from': START, 'to': latest, 'nPeriods': len(rows)},
        'state': {
            'status': 'WATCH_ONLY',
            'hardRules': 0,
            'reason': f'{len(rows)} 期低于 20 期门槛；只做拥挤度审计，不输出方向。',
            'targets': [
                {'period': 330, 'label': '15期完整率', 'rule': '77/77站成功、缺站0；上榜站n≥15'},
                {'period': 335, 'label': '20期第一次长期检验', 'rule': '只有95%下限高于基线且连续两窗过线才升级'},
                {'period': 360, 'label': '45期硬规则门槛', 'rule': '首位0中也要45期，才可能把上限压到随机线以下'},
            ],
        },
        'signals': {
            'kill3': {
                'label': '杀三肖', 'n': kill_n, 'hits': kill_hit,
                'rate': round(kill_hit / kill_n, 4) if kill_n else None,
                'baseline': 0.75, 'ciLow': round(klo, 4) if klo else None,
                'ciHigh': round(khi, 4) if khi else None,
                'top3Avoid': f'{top_kill_hits}/{len(rows)}',
                'top3AvoidRate': round(top_kill_hits / len(rows), 4),
            },
            'nine': {
                'label': '九肖', 'n': nine_n, 'hits': nine_hit,
                'rate': round(nine_hit / nine_n, 4) if nine_n else None,
                'baseline': 0.75, 'ciLow': round(nlo, 4) if nlo else None,
                'ciHigh': round(nhi, 4) if nhi else None,
                'topAvoid': f'{top_nine_hits}/{len(rows)}',
                'topAvoidRate': round(top_nine_hits / len(rows), 4),
            },
            'first': {
                'label': '九肖首位', 'n': first_n, 'hits': first_hit,
                'rate': round(first_hit / first_n, 4) if first_n else None,
                'baseline': round(1 / 12, 4), 'ciLow': round(flo, 4) if flo else None,
                'ciHigh': round(fhi, 4) if fhi else None,
                'topAvoid': f'{top_first_hits}/{len(rows)}',
                'topAvoidRate': round(top_first_hits / len(rows), 4),
            },
        },
        'hypotheses': hypotheses,
        'network': {
            'killSites': max(r['killSites'] for r in rows),
            'nineSites': max(r['nineSites'] for r in rows),
            'mirrorPairs': pairs,
            'note': '站点推荐不等于注码；镜像站只算一票，不按站点数量放大。',
        },
        'periods': rows,
        'notes': [
            '拥挤度=九肖收录+杀三票+首位票的标准化合分；高分是“人多”，不是“会开”。',
            '杀三/九肖的顶端未开，很大一部分是分母：3/12、9/12 的基数本身就是75%。',
            '所有 p 值都是9期置换/二项结果，只能筛异常，不能当硬规则。',
            '本引擎只做研究与风控，不生成投注指令。',
        ],
    }
    os.makedirs(DATA, exist_ok=True)
    for name in ['engine.json', f'engine-{latest}.json']:
        path = os.path.join(DATA, name)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f'ENGINE_OK through={latest} periods={len(rows)} kill={kill_n} nine={nine_n} mirrors={len(pairs)}')


if __name__ == '__main__':
    main()
