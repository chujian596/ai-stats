#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从本地完整开奖源 ../4901988-draws.json 生成最近 30 期公开开奖记录 data/draws-recent.json。

每期列出 6 个平码 + 1 个特码，每号带号码 / 生肖 / 波色（取自开奖源 meta），
特码单独标出。按期号倒序（最新在前），供 draws.html 直接展示。
样本与开奖源一致；缺 meta 的早期号生肖 / 波色留空，不臆造。
"""
import json, os, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
DRAW = PARENT / '4901988-draws.json'
OUT = ROOT / 'data' / 'draws-recent.json'
RECENT_N = 30


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def main():
    draws = load(DRAW)
    issues = sorted((int(k) for k in draws.keys() if str(k).isdigit()))
    recent = issues[-RECENT_N:]

    periods = []
    latest_at = ''
    for iss in reversed(recent):
        v = draws[str(iss)]
        meta = {m['n']: m for m in v.get('meta', [])}
        plains = v.get('plains') or []
        sp = v.get('special')
        fetched = v.get('fetched_at') or ''
        latest_at = max(latest_at, fetched)

        def cell(n, is_special):
            m = meta.get(n, {})
            return {
                'n': n,
                'zodiac': m.get('zodiac') or v.get('special_zodiac') if is_special else m.get('zodiac'),
                'wave': m.get('wave'),
                'special': is_special,
            }

        numbers = [cell(n, False) for n in plains]
        if sp is not None:
            numbers.append(cell(sp, True))
        sp_meta = meta.get(sp, {})
        periods.append({
            'issue': iss,
            'special': sp,
            'specialZodiac': sp_meta.get('zodiac') or v.get('special_zodiac'),
            'specialWave': sp_meta.get('wave'),
            'plains': plains,
            'numbers': numbers,
        })

    out = {
        'updated_at': latest_at or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'rule': '号码按开奖顺序：前 6 个平码 + 末位特码；波色 / 生肖取自开奖源 meta，特码已标出。',
        'count': len(periods),
        'periods': periods,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'draws-recent.json: {len(periods)} 期 ({recent[0]}~{recent[-1]}) updated={out["updated_at"]}')


if __name__ == '__main__':
    main()
