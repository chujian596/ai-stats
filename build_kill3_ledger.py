#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 data/kill3-ledger.json：每站杀特3肖逐期台账
数据源：
  1) data/sites-current.json 的 history['杀特3肖']（293~322，21 站，早期无快照期补充）
  2) ../snapshots/ 早份(18点)/晚份(20点) 快照的 杀特3肖 列（当前未开奖期，如 323）
  3) 开奖结果 ../4901988-draws.json（特码→特肖）
口径：命中＝当期特肖不在该站所杀 3 肖内。
质检留底：每站留存网站原始文本 raw；早/晚两份快照肖组不一致标 changed 并存 lateZodiacs。
"""
import json, glob, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
DRAW = PARENT / '4901988-draws.json'
Z12 = ["马", "蛇", "龙", "兔", "虎", "牛", "鼠", "猪", "狗", "鸡", "猴", "羊"]
ZOD = '鼠牛虎兔龙蛇马羊猴鸡狗猪'


def zchar_of(n):
    return Z12[(int(n) - 1) % 12]


def zchars(v):
    return [c for c in (v or '') if c in ZOD]


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


# ---- 开奖：期号 -> (特码, 特肖) ----
draws = {}
for k, v in load(DRAW).items():
    if not isinstance(v, dict):
        continue
    sp = v.get('special') or v.get('t') or v.get('code')
    if sp:
        draws[int(k)] = (int(sp), zchar_of(int(sp)))

# ---- 历史库补充（早期无本地快照的期，仅作补充；快照为准）----
sc = load(ROOT / 'data' / 'sites-current.json')
# periods[iss][sid] = {'zs': [...], 'raw': 原文, 'src': 'history'|'snap'}
periods = {}
sites_meta = {}
for s in sc['sites']:
    h = (s.get('history') or {}).get('杀特3肖') or {}
    if not h:
        continue
    sites_meta[s['id']] = {'siteKey': s['id'], 'system': 'wanpz'}
    for iss, val in h.items():
        periods.setdefault(int(iss), {})[s['id']] = {'zs': zchars(val), 'raw': val, 'src': 'history'}

# ---- 本地快照按期归集：早份 18* / 晚份 20*；早份入账，晚份用于改料比对 ----
KILL_COLS = ['杀特3肖', '绝杀三肖', '📛绝杀三肖']
VALID_PREFIX = ('wanpz-h1-', 'wanpz-h2-', 'wanpz-h3-', 'wanpz-h5-', 'wanpz-h6-', 'wanpz-h8-', 'wanpz-h9-', 'bdmijg-js-')
snapshot_issues = set()


def pick_kill(columns):
    for cn in KILL_COLS:
        v = (columns or {}).get(cn)
        if v and v.get('value'):
            return v['value']
    return None


def snapshot_pick(snap):
    out = {}
    for key, rec in (snap.get('sites') or {}).items():
        if not key.startswith(VALID_PREFIX):
            continue
        v = pick_kill(rec.get('columns') or {})
        if not v:
            continue
        if key.startswith('bdmijg-js-'):
            hk = 'bdmijg-' + key[len('bdmijg-js-'):]
            sys = 'bdmijg'
        else:
            hk = str(rec.get('siteKey'))
            sys = key.split('-')[0]
        out[hk] = {'zs': zchars(v), 'raw': v, 'system': sys}
    return out


def find_snapshots(issue):
    early = sorted(glob.glob(os.path.join(PARENT, 'snapshots', f'snapshot-{issue}-18*.json')))
    late = sorted(glob.glob(os.path.join(PARENT, 'snapshots', f'snapshot-{issue}-20*.json')))
    return (early[0] if early else None, late[-1] if late else None)


for iss in sorted({int(p.split('-')[1]) for p in glob.glob(os.path.join(PARENT, 'snapshots', 'snapshot-*.json')) if p.split('-')[1].isdigit()}):
    early_path, late_path = find_snapshots(iss)
    if not early_path:
        continue
    early = load(Path(early_path))
    early_pick = snapshot_pick(early)
    late_pick = snapshot_pick(load(Path(late_path))) if late_path else {}
    if not early_pick and not late_pick:
        continue
    snapshot_issues.add(iss)
    for hk in set(early_pick) | set(late_pick):
        e = early_pick.get(hk)
        l = late_pick.get(hk)
        rec = l or e  # 晚份优先入账，与旧口径「取最晚有效一份」一致
        sites_meta.setdefault(hk, {'siteKey': hk, 'system': rec['system']})
        periods.setdefault(iss, {})[hk] = {
            'zs': rec['zs'], 'raw': rec['raw'], 'src': 'snap',
            'late_zs': l['zs'] if l else None,
            'early_zs': e['zs'] if e else None,
        }

# ---- 组台账（只收已开奖对账的期；未开奖的待开期不进台账，待开推荐走 current-recommend）----
out_periods = {}
for iss in sorted(periods):
    sp_num, sp_z = (draws.get(iss, (None, None)))
    if sp_z is None:
        continue
    st = {}
    for sid, rec in periods[iss].items():
        zs = rec['zs']
        if not zs:
            continue
        meta = sites_meta.get(sid, {'system': 'wanpz'})
        hit = sp_z not in zs
        early_zs = rec.get('early_zs')
        late_zs = rec.get('late_zs')
        changed = bool(early_zs is not None and late_zs is not None and early_zs != late_zs)
        st[sid] = {
            'siteKey': sid,
            'system': meta['system'],
            'status': '有三肖',
            'zodiacs': zs,
            'raw': rec.get('raw') or '',
            'hit': hit,
            'changed': changed,
            'lateZodiacs': late_zs if changed else None,
        }
    out_periods[str(iss)] = {
        'specialNum': sp_num,
        'actual': sp_z,
        'hasSnapshot': iss in snapshot_issues,
        'stations': st,
    }

# ---- 跳期存疑：前后相邻两期都有、唯独本期无记录的站（仅标记，不判对错、不补票）----
issue_list = sorted(out_periods, key=int)
for idx, iss in enumerate(issue_list):
    cur = set(out_periods[iss]['stations'])
    prev = set(out_periods[issue_list[idx - 1]]['stations']) if idx > 0 else set()
    nxt = set(out_periods[issue_list[idx + 1]]['stations']) if idx < len(issue_list) - 1 else set()
    out_periods[iss]['gaps'] = sorted((prev & nxt) - cur)

# ---- 站档位（只新增观察用字段，不改任何中/错判定）----
WIN = 20
TIER_ORDER = ['S', 'A', 'B', 'C', 'D']


def _profiles(out_periods):
    keys = sorted(out_periods, key=int)
    res = {}
    for iss in keys:
        st = out_periods[iss]['stations']
        n_all = len(st)
        wins_all = sum(1 for v in st.values() if v['hit'])
        maj = (wins_all / n_all) if n_all else 0
        for sid, v in st.items():
            r = res.setdefault(sid, {'seq': []})
            r['seq'].append((iss, bool(v['hit']), maj))
    prof = {}
    for sid, r in res.items():
        seq = r['seq'][-WIN:]
        n = len(seq)
        win = sum(1 for _, h, _ in seq if h)
        acc = (win / n) if n else 0
        max_loss = cur = 0
        for _, h, _ in seq:
            cur = 0 if h else cur + 1
            max_loss = max(max_loss, cur)
        lone = sum(1 for _, h, m in seq if (not h) and m >= 0.75)
        coll = sum(1 for _, h, m in seq if not h) - lone
        tail = ''.join('W' if h else 'L' for _, h, _ in seq[-10:])
        if n < 8:
            tier = 'OBS'
        elif acc >= 0.90 and max_loss <= 1:
            tier = 'S'
        elif acc >= 0.80 and max_loss <= 2:
            tier = 'A'
        elif acc >= 0.65:
            tier = 'B'
        elif acc >= 0.55:
            tier = 'C'
        else:
            tier = 'D'
        if tier != 'OBS' and lone >= 3:
            tier = TIER_ORDER[min(TIER_ORDER.index(tier) + 1, 4)]
        prof[sid] = {
            'tier': tier,
            'n': n,
            'win': win,
            'loss': n - win,
            'acc': round(acc, 3),
            'maxLoss': max_loss,
            'loneErr': lone,
            'collectErr': coll,
            'tail': tail,
            'window': WIN,
            'sampleWarn': n < 15,
        }
    return prof


latest_snap_at = ''
for sp in glob.glob(os.path.join(PARENT, 'snapshots', 'snapshot-*.json')):
    try:
        latest_snap_at = max(latest_snap_at, load(Path(sp)).get('generated_at') or '')
    except Exception:
        pass
out = {
    'updated_at': latest_snap_at or sc.get('updatedAt', ''),
    'rule': '杀特3肖：当期特肖不在所杀3肖内记为「中」；连对/连错按逐期尾段推导；只收本站固定杀三肖栏，跳转外站的链接不计；有本地快照的期以快照留存为准，历史库仅补早期无快照期；raw 为网站原始文本，changed 为早/晚两份快照肖组不一致（改料）',
    'periods': out_periods,
    'profiles': _profiles(out_periods),
    'profile_rule': '档位仅为观察标记，不参与中/错判定。取最近20个有记录的期：S=准确率≥90%且最长连错≤1；A=≥80%且连错≤2；B=≥65%；C=≥55%；D=<55%；样本<8期记OBS(观察)，<15期标样本偏小。个性错(同期≥75%的站都对而它错)累计≥3次自动降一档。',
}
(ROOT / 'data' / 'kill3-ledger.json').write_text(
    json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

for iss in sorted(out_periods, key=int)[-4:]:
    p = out_periods[iss]
    hit = sum(1 for v in p['stations'].values() if v['hit'])
    chg = sum(1 for v in p['stations'].values() if v['changed'])
    print(f'{iss}期 特{str(p["specialNum"]):>3s}/{p["actual"] or "-"} 站{len(p["stations"])} 中{hit} 改料{chg}')
print('期数', len(out_periods), '文件 data/kill3-ledger.json')
