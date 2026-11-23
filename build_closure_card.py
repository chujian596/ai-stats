#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资料闭环分段报告卡片：把每天四段（09:30/15:30/18:00/20:00）的执行结果压成 data/closure-report.json，
供 stats.html「资料闭环 · 今日分段」卡片读取。快照+归档+台账跑完后调用，页面自动更新。

全部从本地真实文件算，不写死：
  快照    ../snapshots/snapshot-{期}-*.json     按 generated_at 真实时间分段（开奖后补抓不计入四段）
  覆盖    data/current-recommend.json            同期并集口径
  改料    data/change-ledger.json                按 at 时间落到对应段
  封存    ../预测封存-{期}.json / ../4901988-locked.json
  论坛    data/forum-{期}.json / data/cross-{期}.json
  开奖    ../official-history.json
  线上    data/latest-period.json（+ /tmp/draw_refresh.log 若有）
"""
import json
import os
import re
import glob
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, 'data')
SNAPDIR = os.path.join(ROOT, 'snapshots')

import build_current_recommend as bcr  # 复用同一套栏目口径
ZOD = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']

STAGE_DEF = [
    ('0930', '09:30 上午更新', 6.0, 10.0),
    ('1530', '15:30 下午更新', 10.0, 16.75),
    ('1800', '18:00 盘前封存', 16.75, 19.0),
    ('2000', '20:00 开奖前补充', 19.0, 21.5),
]
ORDER = [s[0] for s in STAGE_DEF]
LABEL = {s[0]: s[1] for s in STAGE_DEF}


def load(p, default=None):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def dump(p, obj):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def stkey(dt):
    h = dt.hour + dt.minute / 60.0
    for k, _, lo, hi in STAGE_DEF:
        if lo <= h < hi:
            return k
    if 0.0 <= h < 6.0:
        return 'late'
    return None


def coverage_of(sites):
    cov = {'nine': 0, 'kill': 0, 'pingte': 0, 'wave': 0, 'tail': 0, 'head': 0, 'size': 0, 'parity': 0}
    for s in sites.values():
        cols = s.get('columns')
        if not cols:
            continue
        if bcr.pick_column(cols):
            cov['nine'] += 1
        if bcr.pick_kill(cols):
            cov['kill'] += 1
        for dim, fn in bcr.EXTRA_PICKERS.items():
            if fn(cols):
                cov[dim] += 1
    return cov


def snap_inventory(issue):
    files = []
    for g in sorted(glob.glob(os.path.join(SNAPDIR, 'snapshot-%s-*.json' % issue))):
        if '-raw' in os.path.basename(g):
            continue
        d = load(g, {}) or {}
        ts = str(d.get('generated_at') or '')
        try:
            dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
        except Exception:
            continue
        if int(d.get('issue', 0) or 0) != int(issue):
            continue
        ok = sum(1 for v in (d.get('sites') or {}).values() if 'columns' in v)
        files.append({'dt': dt, 'file': g, 'snap': d, 'ok': ok, 'key': stkey(dt)})
    files.sort(key=lambda x: x['dt'])
    return files


def build_stages(issue, ledger):
    files = snap_inventory(issue)
    if not files:
        return [], files
    buckets = {}
    for f in files:
        k = f['key']
        if not k or k == 'late':
            continue
        cur = buckets.get(k)
        if (not cur) or (f['ok'], f['dt']) > (cur['ok'], cur['dt']):
            buckets[k] = f

    ents = [e for e in (ledger.get('entries') or []) if str(e.get('period')) == str(issue)]
    top3 = []
    cfz = load(os.path.join(DATA, 'crowd-freeze-%s.json' % issue), {}) or {}
    for key in ('top3', 'crowdTop3'):
        if isinstance(cfz.get(key), list):
            top3 = [str(x) for x in cfz[key]]

    stages = []
    prev_dt = None
    for k in ORDER:
        b = buckets.get(k)
        if not b:
            stages.append({'key': k, 'label': LABEL[k], 'done': False})
            continue
        d = b['snap']
        sites = d.get('sites') or {}
        win = [e for e in ents
               if (prev_dt is None or str(e.get('at') or '') > prev_dt.strftime('%Y-%m-%d %H:%M:%S'))
               and str(e.get('at') or '') <= b['dt'].strftime('%Y-%m-%d %H:%M:%S')]
        EX_FLAG = ('新站首期', '模板轮换', '模板微调', '回滚')
        sub_win = [e for e in win if not any(t in str(e.get('flag') or '') for t in EX_FLAG)]
        ch_sites = len({(e.get('siteId') or e.get('siteName')) for e in win})
        sub_sites = len({(e.get('siteId') or e.get('siteName')) for e in sub_win})
        zs = set()  # 只算真正变动掉的肖（前后对称差），不是整条名单
        for e in sub_win:
            bb = set(e.get('beforeSet') or [])
            aa = set(e.get('afterSet') or [])
            if bb or aa:
                zs |= (aa ^ bb)
            else:
                zs |= set(re.findall(r'[鼠牛虎兔龙蛇马羊猴鸡狗猪]', str(e.get('after') or ''))) ^ \
                      set(re.findall(r'[鼠牛虎兔龙蛇马羊猴鸡狗猪]', str(e.get('before') or '')))
        stages.append({
            'key': k, 'label': LABEL[k], 'done': True,
            'time': b['dt'].strftime('%H:%M'),
            'generated_at': d.get('generated_at'),
            'snapshot': os.path.basename(b['file']),
            'ok': b['ok'],
            'fail': len(d.get('failed_fetch') or []),
            'notUpdated': len(d.get('failed_not_updated') or []),
            'carry': int(d.get('carried_count') or 0),
            'retry': int(d.get('retry_rounds') or 0) + int(d.get('fetch_retry_rounds') or 0),
            'coverage': coverage_of(sites),
            'changes': len(win), 'changeStations': ch_sites,
            'substantive': len(sub_win), 'substantiveStations': sub_sites,
            'changeZodiacs': sorted(z for z in zs if z in ZOD),
            'significant': (sub_sites >= 5) or bool(zs & set(top3)),
            'changeDetail': [{'siteName': e.get('siteName'), 'column': e.get('column'),
                              'before': e.get('before'), 'after': e.get('after')} for e in win[:8]],
        })
        prev_dt = b['dt']
    return stages, files


def latest_issue():
    issues = []
    for g in glob.glob(os.path.join(SNAPDIR, 'snapshot-*-*.json')):
        m = re.match(r'snapshot-(\d+)-\d{4}\.json$', os.path.basename(g))
        if m:
            issues.append(int(m.group(1)))
    withdata = []
    for i in sorted(set(issues)):
        for f in snap_inventory(i):
            if f['ok'] and f['key'] and f['key'] != 'late':
                withdata.append(i)
                break
    return (withdata[-1] if withdata else (sorted(issues)[-1] if issues else 0)), sorted(set(issues), reverse=True)


def period_report(issue):
    ledger = load(os.path.join(DATA, 'change-ledger.json'), {}) or {}
    stages, files = build_stages(issue, ledger)

    union = set()
    for f in files:
        union |= set((f['snap'].get('sites') or {}).keys())

    cur = load(os.path.join(DATA, 'current-recommend.json'), {}) or {}
    cov = cur.get('coverage') if str(cur.get('period')) == str(issue) else None
    if not cov:
        done = [s for s in stages if s.get('done')]
        cov = done[-1]['coverage'] if done else {}

    direc = load(os.path.join(DATA, 'site-directory.json'), {}) or {}
    reg = {'total': len(direc.get('sites') or []),
           'core': sum(1 for s in (direc.get('sites') or []) if s.get('tier') == 'core'),
           'added': sum(1 for s in (direc.get('sites') or []) if s.get('tier') == 'added')}

    ents = [e for e in (ledger.get('entries') or []) if str(e.get('period')) == str(issue)]
    stages_done = [s for s in stages if s.get('done')]
    cut = stages_done[-1]['generated_at'] if stages_done else '9999'
    in_stages = [e for e in ents if str(e.get('at') or '') <= str(cut)]
    settled = sum(1 for e in in_stages if ((e.get('result') or {}).get('verdict')))
    pending = len(in_stages) - settled
    after = len(ents) - len(in_stages)

    seal = load(os.path.join(ROOT, '预测封存-%s.json' % issue), {}) or {}
    lock = (load(os.path.join(ROOT, '4901988-locked.json'), {}) or {}).get(str(issue)) or {}
    lock_first = min([v.get('first_seen', '') for v in lock.values()] or ['']) if lock else ''

    forum = load(os.path.join(DATA, 'forum-%s.json' % issue), {}) or {}
    cross = load(os.path.join(DATA, 'cross-%s.json' % issue), {}) or {}
    rec = cross.get('rec') or forum.get('rec') or {}
    kil = cross.get('kill') or forum.get('kill') or {}
    if isinstance(rec, str):
        rec = eval(rec) if rec.startswith('{') else {}
    if isinstance(kil, str):
        kil = eval(kil) if kil.startswith('{') else {}

    hist = load(os.path.join(ROOT, 'official-history.json'), {}) or {}
    drawn = hist.get(str(issue)) or {}

    lp = load(os.path.join(DATA, 'latest-period.json'), {}) or {}
    cf = gh = ''
    try:
        with open('/tmp/draw_refresh.log', encoding='utf-8', errors='ignore') as f:
            tail = f.read()[-4000:]
        c = re.findall(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) Cloudflare 已同步', tail)
        g2 = re.findall(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) GitHub Pages 已同步', tail)
        cf = c[-1] if c else ''
        gh = g2[-1] if g2 else ''
    except Exception:
        pass

    top3 = []
    cfz = load(os.path.join(DATA, 'crowd-freeze-%s.json' % issue), {}) or {}
    for key in ('top3', 'crowdTop3'):
        if isinstance(cfz.get(key), list):
            top3 = [str(x) for x in cfz[key]]

    notes = []
    sig = [s['label'] for s in stages_done if s.get('significant')]
    if sig:
        notes.append('显著改料段：' + '、'.join(sig) + '（≥5 站或涉及共识 Top3）')
    if after:
        notes.append('开奖后补抓另有 %d 条登记，不计入四段。' % after)

    return {
        'period': int(issue),
        'updatedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'currentStage': stages_done[-1]['key'] if stages_done else None,
        'currentStageLabel': stages_done[-1]['label'] if stages_done else '未出料',
        'registry': reg,
        'unionSites': len(union),
        'notUpdated': stages_done[-1]['notUpdated'] if stages_done else 0,
        'emptySites': int((cov or {}).get('empty') or 0),
        'coverage': cov or {},
        'stages': stages,
        'changes': {'periodTotal': len(in_stages), 'settled': settled, 'pending': pending,
                    'afterDraw': after},
        'seal': {'sha': (seal.get('sha256') or '')[:12], 'lockedAt': seal.get('locked_at') or '',
                 'lockColumns': len(lock), 'lockFirstSeen': lock_first,
                 'claims': [{'id': c.get('id'), 'name': c.get('name'), 'zodiacs': c.get('zodiacs')}
                            for c in (seal.get('claims') or [])]},
        'drawn': {'specialNum': drawn.get('specialNum'), 'specialZod': drawn.get('specialZod')},
        'forum': {'posts': forum.get('total_fetched'), 'push': sum(rec.values()) if rec else None,
                  'kill': sum(kil.values()) if kil else None,
                  'at': forum.get('fetched_at')},
        'online': {'latestPeriod': lp.get('period'), 'latestUpdatedAt': lp.get('updatedAt'),
                   'cloudflare': cf, 'githubPages': gh},
        'top3': top3,
        'notes': notes,
        'snapshots': [os.path.basename(f['file']) for f in files],
    }


def history(limit=8):
    _, issues = latest_issue()
    ledger = load(os.path.join(DATA, 'change-ledger.json'), {}) or {}
    hist = load(os.path.join(ROOT, 'official-history.json'), {}) or {}
    rows = []
    for iss in issues[:limit]:
        stages, files = build_stages(iss, ledger)
        done = [s for s in stages if s.get('done')]
        union = set()
        for f in files:
            union |= set((f['snap'].get('sites') or {}).keys())
        cov = done[-1]['coverage'] if done else {}
        ents = [e for e in (ledger.get('entries') or []) if str(e.get('period')) == str(iss)]
        cut = done[-1]['generated_at'] if done else '9999'
        in_st = [e for e in ents if str(e.get('at') or '') <= str(cut)]
        seal = load(os.path.join(ROOT, '预测封存-%s.json' % iss), {}) or {}
        d = hist.get(str(iss)) or {}
        rows.append({'period': iss, 'stagesDone': len(done),
                     'lastStage': done[-1]['key'] if done else None,
                     'lastTime': done[-1]['time'] if done else '',
                     'unionSites': len(union), 'changes': len(in_st),
                     'nine': cov.get('nine'), 'kill': cov.get('kill'),
                     'seal': (seal.get('sha256') or '')[:8],
                     'drawn': (str(d.get('specialNum')) + ' ' + str(d.get('specialZod'))) if d else ''})
    return rows


def main():
    import sys
    iss, issues = latest_issue()
    if len(sys.argv) > 1:
        iss = int(sys.argv[1])
    rep = period_report(iss)
    rep['history'] = history()
    rep['nextPeriod'] = (iss + 1) if iss else None
    nxt = load(os.path.join(DATA, 'current-recommend.json'), {}) or {}
    rep['nextPending'] = str(nxt.get('period')) == str(iss + 1) and not (nxt.get('sites') or [])
    dump(os.path.join(DATA, 'closure-report.json'), rep)
    print('closure-report.json：期 %s，完成 %d 段，并集 %d 站，改料 %d 条，封存 %s，开奖 %s' % (
        rep['period'], sum(1 for s in rep['stages'] if s.get('done')), rep['unionSites'],
        rep['changes']['periodTotal'], rep['seal']['sha'] or '—',
        (str(rep['drawn']['specialNum']) + ' ' + rep['drawn']['specialZod']) if rep['drawn']['specialNum'] else '未开'))


if __name__ == '__main__':
    main()
