#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成来源名单 data/source-registry.json。

口径：
  - 站点：扫描 316-325 每期最新快照，固定 ID = 系统:站号；
    同时把快照 failed 里的空站补进登记表（enabled=false）。
  - 论坛：只统计 319 以后扩量抓取的帖子作者化名，按出现期数分常驻/一次性。
  - 只做来源治理，不反向修改任何历史 ratio/core 结果。
"""
import json, glob, os, re, datetime, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
DATA = ROOT / 'data'
SNAP = PARENT / 'snapshots'

CORE_KEYS = ('杀特3肖', '绝杀三肖', '绝杀专区', '杀3肖', '📛绝杀三肖')
FORUM_PERIODS = []
LATEST = 0


def load(p, default=None):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return default


def latest_snapshots():
    by = {}
    for p in SNAP.glob('snapshot-*.json'):
        m = re.match(r'snapshot-(\d+)-', p.name)
        if not m:
            continue
        per = int(m.group(1))
        d = load(p, {})
        t = d.get('generated_at') or ''
        if per not in by or t > by[per]['t']:
            by[per] = {'t': t, 'file': p.name, 'data': d, 'path': p}
    return by


def sys_of(sid):
    return sid.split(':', 1)[0] if ':' in sid else sid


def host_of(system):
    if system == 'bdmijg':
        return 'https://bdmijg.wanpz.com'
    tail = system.replace('wanpz-', '')
    return f'https://{tail}.wanpz.com'


def path_of(system, key):
    if system == 'bdmijg':
        return f'bdmijg/{key}'
    return f'{system.replace("wanpz-", "")}/{key}'


def main():
    snaps = latest_snapshots()
    LATEST = max(snaps) if snaps else 325
    FORUM_PERIODS = list(range(max(319, LATEST-6), LATEST+1))
    directory = load(DATA / 'site-directory.json', {}) or {}
    alias_doc = load(DATA / 'site-aliases.json', {}) or {}
    aliases = alias_doc.get('aliases') or {}
    by_id = directory.get('bySiteId') or {}
    prev_doc = load(DATA / 'source-registry.json', {}) or {}
    prev_sites = {x.get('siteId'): x for x in (prev_doc.get('sites') or [])}
    prev_authors = {x.get('name'): x for x in ((prev_doc.get('forum') or {}).get('authors') or [])}

    seen = collections.defaultdict(list)
    site_recs = {}
    failed_empty = set()
    for per in sorted(snaps):
        d = snaps[per]['data']
        for key, s in (d.get('sites') or {}).items():
            system = s.get('system') or key.rsplit('-', 1)[0]
            site_key = str(s.get('siteKey') or key.rsplit('-', 1)[-1])
            sid = f'{system}:{site_key}'
            seen[sid].append(per)
            site_recs[sid] = s
        for f in (d.get('failed') or []):
            text = str(f)
            if ':empty' not in text:
                continue
            raw = text.split(':', 1)[0]
            m = re.match(r'(.+)-([^-]+)$', raw)
            if not m:
                continue
            system, site_key = m.group(1), m.group(2)
            sid = f'{system}:{site_key}'
            failed_empty.add(sid)
            seen.setdefault(sid, [])

    sites = []
    for sid in set(seen) | set(by_id) | set(prev_sites):
        system = sys_of(sid)
        site_key = sid.split(':', 1)[-1]
        d = by_id.get(sid) or {}
        snap = site_recs.get(sid) or {}
        name = (d.get('name') or aliases.get(sid) or aliases.get(site_key) or '').strip()
        if not name:
            name = f'空站{site_key}' if sid in failed_empty else f'站点{site_key}'
        cols = (snap.get('columns') or {})
        core_cols = [k for k in CORE_KEYS if k in cols]
        periods = sorted(set(seen.get(sid) or []))
        prev = prev_sites.get(sid) or {}
        is_empty = sid in failed_empty and not periods
        status = 'empty' if is_empty else ('fixed' if all(p in periods for p in (LATEST-2, LATEST-1, LATEST)) else 'transient')
        if prev:
            name = prev.get('name') or name
        sites.append({
            'siteId': sid,
            'siteKey': site_key,
            'name': name,
            'displayName': d.get('displayName') or f'{name}（{site_key}）',
            'aliases': sorted(set([site_key, sid, name, d.get('displayName') or '', d.get('baseName') or ''])),
            'system': system,
            'path': path_of(system, site_key),
            'host': host_of(system),
            'script': f'{host_of(system)}/script/{site_key}/',
            'aggregator': bool(d.get('aggregator') or system == 'bdmijg'),
            'hasNine': bool(d.get('hasNine') or snap.get('columns', {}).get('9肖中特')),
            'hasKill3': bool(d.get('hasKill3') or any(k in cols for k in ('杀特3肖', '绝杀三肖', '📛绝杀三肖'))),
            'coreKill': bool(core_cols),
            'coreColumns': core_cols,
            'periods': periods,
            'firstSeen': periods[0] if periods else None,
            'lastSeen': periods[-1] if periods else None,
            'periodsCount': len(periods),
            'status': status,
            'enabled': prev.get('enabled', not is_empty) if prev else (not is_empty),
            'locked': prev.get('locked', status == 'fixed') if prev else (status == 'fixed'),
            'note': prev.get('note') if prev and prev.get('note') is not None else ('站点返回空，持续失败' if is_empty else ('聚合站，品牌名待确认' if system == 'bdmijg' and name.startswith('聚合站') else '')),
        })
    sites.sort(key=lambda x: (0 if x['status'] != 'empty' else 1, x['system'], x['siteKey']))

    # 论坛作者池：319-325
    fcounts = collections.Counter()
    fposts = collections.defaultdict(collections.Counter)
    fvotes = collections.defaultdict(collections.Counter)
    fraw = {}
    for per in FORUM_PERIODS:
        d = load(DATA / f'forum-{per}.json', {}) or {}
        fraw[per] = {'fetched': d.get('total_fetched'), 'valid': len(d.get('detail') or [])}
        for x in (d.get('detail') or []):
            a = x.get('a')
            if not a:
                continue
            fcounts[a] += 1
            fposts[a][per] += 1
            fvotes[a][per] += len(x.get('z') or [])
    authors = []
    for name in set(fcounts):
        periods = sorted(fposts[name])
        core = len(periods) >= 2
        authors.append({
            'name': name,
            'periods': periods,
            'periodCount': len(periods),
            'posts': sum(fposts[name].values()),
            'votes': sum(fvotes[name].values()),
            'lastPeriod': max(periods),
            'currentPosts': fposts[name].get(LATEST, 0),
            'currentVotes': fvotes[name].get(LATEST, 0),
            'tier': 'core' if core else 'oneoff',
            'enabled': True,
            'includeCore': (prev_authors.get(name) or {}).get('includeCore', core) if prev_authors.get(name) else core,
        })
    authors.sort(key=lambda x: (0 if x['tier'] == 'core' else 1, -x['periodCount'], -x['posts'], x['name']))

    current = [a for a in authors if LATEST in a['periods']]
    prev = set(a['name'] for a in authors if (LATEST-1) in a['periods'])
    repeat_current = [a for a in current if a['name'] in prev]
    core = [a for a in authors if a['tier'] == 'core']
    oneoff = [a for a in authors if a['tier'] == 'oneoff']
    core45 = load(DATA / f'core-{LATEST}.json', {}) or {}
    core_votes = sum(a['currentVotes'] for a in current if a['includeCore'])
    all_votes = sum(a['currentVotes'] for a in current)
    total_posts = sum(fraw[p]['valid'] or 0 for p in FORUM_PERIODS)
    coverage = round(core_votes / all_votes * 100, 1) if all_votes else 0
    latest_detail = (load(DATA / f'forum-{LATEST}.json', {}) or {}).get('detail') or []
    rec_posts = sum(1 for x in latest_detail if not x.get('k'))
    kill_posts = sum(1 for x in latest_detail if x.get('k'))
    snap_name = snaps[LATEST]['file'] if LATEST in snaps else f'snapshot-{LATEST}-0000.json'
    doc = {
        'schema': 'source-registry/v1',
        'updatedAt': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'dataThrough': LATEST,
        'periods': {'sites': sorted(snaps), 'forum': FORUM_PERIODS},
        'summary': {
            'siteRegistered': len(sites),
            'siteActive': sum(1 for s in sites if s['enabled']),
            'siteEmpty': sum(1 for s in sites if not s['enabled']),
            'siteFixed': sum(1 for s in sites if s['status'] == 'fixed'),
            'siteSystems': len(set(s['system'] for s in sites)),
            'coreKillSites': int(core45.get('coreDen') or 0),
            'coreColumnSites': sum(1 for s in sites if s['coreKill']),
            'forumUnique': len(authors),
            'forumCore': len(core),
            'forumOneoff': len(oneoff),
            'forumCurrent': len(current),
            'forumCurrentCore': sum(1 for a in current if a['includeCore']),
            'forumCurrentOneoff': sum(1 for a in current if not a['includeCore']),
            'forumCurrentPosts': len(current),
            'forumCurrentRec': rec_posts,
            'forumCurrentKill': kill_posts,
            'forumCurrentPicks': all_votes,
            'forumRepeatFromPrev': len(repeat_current),
            'forumNewThisPeriod': len(current) - len(repeat_current),
            'forumCoreVoteCoverage': coverage,
            'forumPages': 6,
            'effectiveEndpoints': sum(1 for s in sites if s['enabled']) + 6,
            'forumCurrentVotes': all_votes,
        },
        'sources': [
            {'key': 'forum', 'name': '公开论坛文字帖', 'kind': '论坛 API', 'count': 6,
             'detail': '6 页 / 600 条抓取，%d 条当期有效帖' % len(current), 'url': 'https://ismkog.xn--n8jaf0byahm4a2c4cybyssjl201en76e.xn--q9jyb4c:21044/api/v1/forums'},
            {'key': 'snapshot', 'name': '站点快照', 'kind': '站点目录', 'count': len(sites),
             'detail': '%d 个登记站，%d 个成功，%d 个空站' % (len(sites), sum(1 for s in sites if s['enabled']), sum(1 for s in sites if not s['enabled'])), 'url': 'snapshots/' + snap_name},
            {'key': 'ratio', 'name': '推杀强度', 'kind': '派生数据', 'count': 1,
             'detail': '论坛 204 条有效帖 → ratio-%d.json' % LATEST, 'url': 'data/ratio-%d.json' % LATEST},
            {'key': 'core', 'name': '站方核心杀', 'kind': '派生数据', 'count': int((core45 or {}).get('coreDen') or 0),
             'detail': '%d/%d 站有核心杀栏目 → core-%d.json' % (int((core45 or {}).get('coreDen') or 0), sum(1 for s in sites if s['enabled']), LATEST), 'url': 'data/core-%d.json' % LATEST},
        ],
        'sites': sites,
        'forum': {'periods': FORUM_PERIODS, 'raw': fraw, 'totalPosts': total_posts, 'authors': authors},
        'audit': prev_doc.get('audit') or [],
        'notes': [
            '站点从 323 起固定 %d 站；%d 个空站持续失败，不计入统计。' % (sum(1 for s in sites if s['enabled']), sum(1 for s in sites if not s['enabled'])),
            '论坛不是固定 %d 人，而是 %d 个发帖化名的轮换池；%d 个至少出现 2 期，%d 个只出现 1 期。' % (len(current), len(authors), len(core), len(oneoff)),
            '%d 期 %d 个发帖名中，%d 个与上期同名、%d 个新出现；按历史≥2期算常驻 %d 个，覆盖 %s%% 的生肖票。' % (LATEST, len(current), len(repeat_current), len(current)-len(repeat_current), sum(1 for a in current if a['includeCore']), coverage),
            '本名单只做来源治理，不反向修改历史 ratio/core 数字。',
        ],
    }
    out = DATA / 'source-registry.json'
    json.dump(doc, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'来源名单：登记 {len(sites)} 站（启用 {doc["summary"]["siteActive"]}，空 {doc["summary"]["siteEmpty"]}）；论坛 {len(authors)} 名，常驻 {len(core)}，一次性 {len(oneoff)}；{LATEST} 活跃 {len(current)}，常驻覆盖 {coverage}%')
    print(f'写入 {out}')


if __name__ == '__main__':
    main()
