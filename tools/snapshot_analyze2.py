#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三体系快照分析（通用版）：改料检测 / 跨站共识 / 异常站 / 今日结论"""
import json, os, re, glob, sys, shutil
from collections import Counter, defaultdict
from datetime import datetime

BASE = "/home/user/Doubao/chats/36344898080638210"
ZODIAC = list("鼠牛虎兔龙蛇马羊猴鸡狗猪")

def _best_snapshot():
    paths = [p for p in glob.glob(os.path.join(BASE, 'snapshots', 'snapshot-*.json'))
             if '-raw' not in os.path.basename(p)]
    cands = []
    for p in paths:
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        issue = int(d.get('issue') or 0)
        ok = sum(1 for v in (d.get('sites') or {}).values() if v.get('columns'))
        cols = sum(len(v.get('columns') or {}) for v in (d.get('sites') or {}).values())
        cands.append((issue, ok, cols, str(d.get('generated_at') or ''), os.path.basename(p), p))
    if not cands:
        return None
    max_issue = max(x[0] for x in cands)
    same = [x for x in cands if x[0] == max_issue]
    # 覆盖率优先；同覆盖率取 generated_at 最新，避免跨午夜按 HHMM 文件名选到旧快照。
    return max(same, key=lambda x: (x[1], x[2], x[3], x[4]))[5]


# 默认不取“文件名最新”，取同一期覆盖最全的一份；晚班漏站时不会把下午的票数打回去。
snap_path = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != '--best' else _best_snapshot()
if not snap_path:
    raise SystemExit('没有可用快照')
snap = json.load(open(snap_path, encoding='utf-8'))
sites = snap['sites']
issue = snap.get('issue')
if not issue:
    c = Counter(r.get('issue') for r in sites.values() if r.get('issue'))
    issue = c.most_common(1)[0][0] if c else os.path.basename(snap_path).split('-')[1]
today = snap['generated_at'][:10]

KILL_CORE = ['杀特3肖', '绝杀三肖', '杀特6肖', '绝杀专区']
KILL_RE = re.compile(r'^(杀特\d肖|绝杀三肖|绝杀专区|杀\d+肖|杀1肖平特|杀特1肖)$')

def zods(s):
    return [z for z in ZODIAC if z in str(s)]

# ---------- 0. 当日基线（用于改料检测）----------
base_path = os.path.join(BASE, 'snapshots', f'daily-baseline-{today}.json')
if os.path.basename(snap_path) != os.path.basename(base_path) and not os.path.exists(base_path):
    shutil.copy(snap_path, base_path)

# ---------- 1. 改料检测 ----------
changes = []
prev_candidates = [p for p in glob.glob(os.path.join(BASE, 'snapshots', 'snapshot-*.json'))
                   if os.path.basename(p) != os.path.basename(snap_path) and json.load(open(p, encoding='utf-8')).get('generated_at', '')[:10] == today]
if os.path.exists(base_path) and os.path.basename(base_path) != os.path.basename(snap_path):
    prev_candidates.append(base_path)
changes_source = None
if prev_candidates:
    prev = json.load(open(sorted(prev_candidates)[-1], encoding='utf-8'))
    changes_source = os.path.basename(sorted(prev_candidates)[-1])
    for key, rec in sites.items():
        if key not in prev['sites']:
            continue
        for cname, c in rec['columns'].items():
            if cname not in KILL_CORE and not KILL_RE.match(cname):
                continue
            old = prev['sites'][key]['columns'].get(cname, {}).get('value')
            if old != c['value']:
                changes.append({"site": key, "column": cname, "before": old, "after": c['value']})
else:
    # 与累积库中同期刊值比对（若已有本期记录）
    hist0 = json.load(open(os.path.join(BASE, 'all-sites-kill3.json'), encoding='utf-8'))
    def hkey(key):
        m = re.match(r'wanpz-(h\d+)-(.+)$', key)
        if m: return f'{m.group(1)}-{m.group(2)}'
        if key.startswith('bdmijg-js-'): return 'bdmijg-' + key[10:]
        return None
    for key, rec in sites.items():
        hk = hkey(key)
        if not hk or hk not in hist0:
            continue
        for cname in KILL_CORE:
            if cname not in rec['columns']:
                continue
            old = next((e['value'] for e in hist0[hk].get('kill3', []) if e.get('issue') == issue), None)
            if old is not None and old != rec['columns'][cname]['value']:
                changes.append({"site": key, "column": cname, "before": old,
                                "after": rec['columns'][cname]['value']})

# ---------- 2. 跨站共识 ----------
kill_votes = defaultdict(set)
kill_counts = Counter()
site_kill = {}
for key, rec in sites.items():
    ks = set()
    for name, c in rec['columns'].items():
        if name in KILL_CORE or KILL_RE.match(name):
            zs = zods(c['value'])
            if not zs:
                continue
            for z in zs:
                kill_counts[z] += 1
            ks |= set(zs)
    site_kill[key] = ks
    for z in ks:
        kill_votes[z].add(key)

n_sites = len(sites)
consensus = sorted([{"zodiac": z, "sites": len(kill_votes[z]), "votes": kill_counts[z],
                     "pct": round(len(kill_votes[z]) / n_sites * 100, 1),
                     "note": "allowed" if len(kill_votes[z]) == 0 else ""} for z in ZODIAC],
                   key=lambda x: -x["sites"])

# ---------- 3. 异常站 ----------
top3 = {c['zodiac'] for c in consensus[:3]}
top6 = {c['zodiac'] for c in consensus[:6]}
abnormal = []
for key, ks in site_kill.items():
    if not ks:
        continue
    ov = len(ks & top3)
    if ov == 0:
        abnormal.append({"site": key, "kill": "".join(sorted(ks, key=ZODIAC.index)), "overlap_top3": 0})

# ---------- 4. 结论 ----------
least_likely = [c['zodiac'] for c in consensus[:3]]
likely = [c['zodiac'] for c in consensus[::-1][:3]]

res = {
    "snapshot": os.path.basename(snap_path),
    "generated_at": snap['generated_at'],
    "issue": issue,
    "site_count": n_sites,
    "systems": dict(Counter(r['system'] for r in sites.values())),
    "failed": snap['failed'],
    "changes_source": changes_source,
    "changes": changes,
    "consensus": consensus,
    "abnormal_sites": abnormal,
    "conclusion": {"least_likely": least_likely, "relatively_bullish": likely},
}
out = os.path.join(BASE, f'analysis-{issue}.json')
json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print(f"快照 {os.path.basename(snap_path)} | 期号 {issue} | 有效站 {n_sites} | 失败 {len(snap['failed'])}")
print(f"体系分布 {res['systems']}")
print(f"\n【改料】基准={changes_source or '累积库'} 差异 {len(changes)} 条")
for c in changes[:30]:
    print('  ', c)
print("\n【跨站共识·杀肖】")
for c in consensus:
    bar = '#' * int(c['pct'] / 5)
    print(f"  {c['zodiac']}: {c['sites']:>2}站/{c['votes']:>2}票 {c['pct']:>5}% {bar}")
print(f"\n【异常站】{len(abnormal)}")
for a in abnormal[:25]:
    print('  ', a['site'], a['kill'])
print(f"\n【结论】最不可能开: {''.join(least_likely)}  相对看好: {''.join(likely)}")
print('ANALYSIS', out)

# ---------- 5. 共识一致度信号（过热/假一致/推荐反向）----------
import subprocess
subprocess.run([sys.executable, os.path.join(BASE, 'consensus_signal.py'), snap_path], check=False)
# ---------- 6. 开奖前封存当期预测 ----------
subprocess.run([sys.executable, os.path.join(BASE, 'pred_lock.py'), str(issue)], check=False)
