#!/usr/bin/env python3
# 独立模板审计：按当期公开推荐指纹找同模板/同维度重票。
# 只做统计口径，不生成方向，不接订单/资金。
import hashlib
import json
import os
from collections import defaultdict, OrderedDict
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
ZODIACS = list('鼠牛虎兔龙蛇马羊猴鸡狗猪')
DIMS = [
    ('nine', 'zodiacs', True),
    ('kill', 'killZodiacs', True),
    ('pingte', 'pingte', False),
    ('wave', 'wave', False),
    ('tail', 'tail', True),
    ('head', 'head', False),
    ('size', 'size', False),
    ('parity', 'parity', False),
]


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=False)


def sid(s):
    return s.get('siteId') or (str(s.get('system', '')) + ':' + str(s.get('siteKey', '')))


def dval(s, key):
    if key in ('zodiacs', 'killZodiacs'):
        return tuple(sorted(s.get(key) or []))
    return tuple(sorted((s.get(key) or {}).get('picks') or []))


def hid(prefix, value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')
    return prefix + '-' + hashlib.sha1(raw).hexdigest()[:8]


def cluster(sites, key):
    groups = defaultdict(list)
    for s in sites:
        v = dval(s, key)
        if v:
            groups[v].append(s)
    return groups


def member(s):
    return {
        'siteId': sid(s),
        'name': s.get('displayName') or s.get('siteName') or sid(s),
    }


def dup_groups(groups):
    rows = []
    for value, members in groups.items():
        if len(members) <= 1:
            continue
        rows.append({
            'clusterId': hid('C', list(value)),
            'value': list(value),
            'size': len(members),
            'members': [member(x) for x in sorted(members, key=lambda x: sid(x))],
        })
    return sorted(rows, key=lambda x: (-x['size'], x['value']))


def main():
    cur = load('current-recommend.json')
    sites = cur.get('sites') or []
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    full_groups = defaultdict(list)
    empty_sites = []
    for s in sites:
        sig = tuple(dval(s, key) for _, key, _ in DIMS)
        if any(sig):
            full_groups[sig].append(s)
        else:
            empty_sites.append(s)

    dims = OrderedDict()
    site_rows = []
    full_info = {}
    for sig, members in full_groups.items():
        cid = hid('T', list(sig))
        for s in members:
            full_info[sid(s)] = {
                'clusterId': cid,
                'size': len(members),
                'weight': round(1.0 / len(members), 6),
            }

    for dim, key, cap in DIMS:
        g = cluster(sites, key)
        rows = dup_groups(g)
        dims[dim] = {
            'sites': sum(len(v) for v in g.values()),
            'unique': len(g),
            'duplicateSites': sum(len(v) - 1 for v in g.values()),
            'maxCluster': max((len(v) for v in g.values()), default=0),
            'capApplied': bool(cap),
            'duplicateGroups': rows,
        }

    for s in sites:
        s_id = sid(s)
        row = {
            'siteId': s_id,
            'name': s.get('displayName') or s.get('siteName') or s_id,
            'dataDims': [dim for dim, key, _ in DIMS if dval(s, key)],
            'empty': not any(dval(s, key) for _, key, _ in DIMS),
        }
        row.update(full_info.get(s_id, {'clusterId': None, 'size': 0, 'weight': 0}))
        for dim, key, cap in DIMS:
            v = dval(s, key)
            if not v:
                row[dim + 'ClusterId'] = None
                row[dim + 'ClusterSize'] = 0
                row[dim + 'Weight'] = 0
                continue
            gid = hid('C', list(v))
            size = sum(1 for x in sites if dval(x, key) == v)
            row[dim + 'ClusterId'] = gid
            row[dim + 'ClusterSize'] = size
            row[dim + 'Weight'] = round(1.0 / size, 6) if cap else 1.0
        site_rows.append(row)

    full_dups = dup_groups(full_groups)
    # 22:30 后 current 可能已切到下一期空快照；此时保留上一份有数据的模板审计，
    # 避免把 325 的审计页覆盖成 0 站。
    if len(sites) == len(empty_sites):
        old_path = os.path.join(DATA, 'independence.json')
        if os.path.exists(old_path):
            old = load('independence.json')
            if (old.get('counts') or {}).get('withData', 0) > 0:
                print('INDEPENDENCE_SKIP_EMPTY keep period=%s' % old.get('period'))
                return
    out = {
        'schema': 'independence/v1',
        'updatedAt': now,
        'period': cur.get('period'),
        'source': cur.get('source'),
        'counts': {
            'registered': len(sites),
            'withData': len(sites) - len(empty_sites),
            'empty': len(empty_sites),
            'fullTemplates': len(full_groups),
            'fullDuplicateGroups': len(full_dups),
            'emptySites': [member(x) for x in empty_sites],
            'fullDuplicates': full_dups,
        },
        'effective': {
            'full': len(full_groups),
            'withData': len(sites) - len(empty_sites),
            'nine': dims['nine']['unique'],
            'kill': dims['kill']['unique'],
            'tail': dims['tail']['unique'],
            'head': dims['head']['unique'],
        },
        'dimensions': dims,
        'sites': sorted(site_rows, key=lambda x: x['siteId']),
        'notes': [
            '全指纹=8个维度都完全一致；同九肖只说明这一维重票，不等于同站或同模板。',
            '只有全指纹重复才按整站封顶；九肖/杀三/尾数按维度封顶，仅用于影子对照。',
            '低熵维度（平特/波色/大小/单双）不做封顶，否则会把正常共识压成假独立。',
            '当期无票站不计入模板数；它们不是独立判断，也不是有效票。',
        ],
    }
    save('independence.json', out)
    print('INDEPENDENCE_OK', 'registered=%s' % out['counts']['registered'],
          'withData=%s' % out['counts']['withData'],
          'full=%s' % out['counts']['fullTemplates'],
          'nine=%s/%s' % (dims['nine']['sites'], dims['nine']['unique']),
          'kill=%s/%s' % (dims['kill']['sites'], dims['kill']['unique']),
          'empty=%s' % out['counts']['empty'])


if __name__ == '__main__':
    main()
