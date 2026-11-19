#!/usr/bin/env python3
# 由最新快照生成站点清单：站号 / 站名 / 数据路径 / 栏目参数
import json, glob, os, datetime
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
    k3 = cols.get('杀特3肖'); k9 = cols.get('9肖中特')
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
        'has_nine': bool(k9),
        'nine': (k9 or {}).get('value', ''),
        'nine_rule': str((k9 or {}).get('ruleId', '')),
    })
rows.sort(key=lambda r: (0 if r['has_kill3'] else 1, r['path']))
out = {'updated_at': gen, 'source_snapshot': snap.name, 'issue': issue,
       'total': len(rows), 'with_kill3': sum(1 for r in rows if r['has_kill3']),
       'with_nine': sum(1 for r in rows if r['has_nine']), 'sites': rows}
json.dump(out, open(HERE/'data/site-registry.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'站点清单：{len(rows)} 站，有杀三肖 {out["with_kill3"]}，有九肖 {out["with_nine"]}，期号 {issue}，来源 {snap.name}')
