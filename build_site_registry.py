#!/usr/bin/env python3
# 由最新快照生成站点清单：站号 / 站名 / 数据路径 / 栏目参数
import json, glob, os, datetime, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
alias = json.load(open(HERE/'data/site-aliases.json', encoding='utf-8')).get('aliases', {})
snaps = sorted((PARENT/'snapshots').glob('snapshot-*.json'), key=os.path.getmtime)
snap = snaps[-1]
d = json.load(open(snap, encoding='utf-8'))
issue = d.get('issue'); gen = d.get('generated_at') or ''
rows = []
i = 0
for key, s in d.get('sites', {}).items():
    site = s.get('siteKey'); sysname = s.get('system', '')
    host = sysname.replace('wanpz-', '')  # h2 / h9
    cols = s.get('columns', {})
    k3 = cols.get('杀特3肖') or cols.get('绝杀三肖') or cols.get('📛绝杀三肖')
    k3_name = '杀特3肖' if '杀特3肖' in cols else ('绝杀三肖' if ('绝杀三肖' in cols or '📛绝杀三肖' in cols) else '')
    k9 = next((c for c in cols if c == '9肖中特' or re.fullmatch(r'9肖加(?:对应)?\d+码中特', c)), None)
    k9cd = cols.get(k9) or {}
    i += 1
    rows.append({
        'no': i,
        'id': site,
        'name': alias.get(site, ''),
        'path': f'{host}/{site}',
        'host': f'https://{host}.wanpz.com',
        'script': f'https://{host}.wanpz.com/script/{site}/',
        'has_kill3': bool(k3),
        'kill3': (k3 or {}).get('value', ''),
        'kill3_rule': str((k3 or {}).get('ruleId', '')),
        'kill3_col': k3_name,
        'aggregator': sysname.startswith('bdmijg'),
        'has_nine': bool(k9),
        'nine': k9cd.get('value', ''),
        'nine_rule': str(k9cd.get('ruleId', '')),
    })
rows.sort(key=lambda r: (0 if r['has_kill3'] else 1, r['path']))
# 同名站自动编号：铁算盘一 / 铁算盘二
import collections
cnt = collections.Counter(r['name'] for r in rows if r['name'])
order = {}
for r in sorted(rows, key=lambda x: x['path']):
    if cnt.get(r['name'], 0) > 1:
        order.setdefault(r['name'], []).append(r)
CN = ['一','二','三','四','五','六']
for nm, items in order.items():
    for idx, r in enumerate(items):
        r['base_name'] = nm
        r['name'] = nm + (CN[idx] if idx < len(CN) else str(idx+1))
        r['dup'] = True
out = {'updated_at': gen, 'source_snapshot': snap.name, 'issue': issue,
       'total': len(rows), 'with_kill3': sum(1 for r in rows if r['has_kill3'] and not r.get('aggregator')),
       'with_nine': sum(1 for r in rows if r['has_nine']), 'sites': rows}
json.dump(out, open(HERE/'data/site-registry.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'站点清单：{len(rows)} 站，有杀三肖 {out["with_kill3"]}，有九肖 {out["with_nine"]}，期号 {issue}，来源 {snap.name}')
