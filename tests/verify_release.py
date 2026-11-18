#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发版前硬校验：版本三处一致 + 关键页面元素在 + 无整块丢失。
每次改完 app-pro.html 必须跑，失败就绝不允许打包/推送。
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAIL = []
OK = []

def chk(name, cond, detail=''):
    (OK if cond else FAIL).append(name + ((' -> ' + detail) if detail else ''))

page = (ROOT / 'app-pro.html').read_text(encoding='utf-8')
backup = (ROOT / 'app-pro-backup.html').read_text(encoding='utf-8')
vtxt = (ROOT / 'version.txt').read_text(encoding='utf-8').strip()

# 1) 版本三处一致
m1 = re.search(r"APP_VER\s*=\s*'([^']*)'", page)
m2 = re.search(r"APP_VER\s*=\s*'([^']*)'", backup)
v1 = m1.group(1) if m1 else 'MISSING'
v2 = m2.group(1) if m2 else 'MISSING'
chk('页面 APP_VER 存在', v1 != 'MISSING', v1)
chk('备份 APP_VER 存在', v2 != 'MISSING', v2)
chk('三处版本一致', v1 == v2 == vtxt, f'page={v1} backup={v2} txt={vtxt}')
chk('版本号格式合法', bool(re.match(r'v\d{2}\.\d+(?:\.\d+)?-Pro$', v1)), v1)

# 2) 关键函数必须在
for fn in ['renderRisk', 'cutCalc', 'cutBets', 'pickCut', 'switchCutMode',
           'setFlyTh', 'applyCutTolerance', 'buildNeedList', 'renderNeedList',
           'copyNeedList', 'simAddNum', 'simNeedAmount', 'preflightReport',
           'toggleRiskBox', 'renderSplit']:
    chk(f'函数 {fn}', f'function {fn}(' in page)

# 3) 关键 UI 锚点必须在
for el in ['riskBody', 'cutThInput', 'riskAnalysisBox', 'cutTolerance',
           'needBox', 'needTarget', 'needBudget', 'needUnit', 'simBox', 'simTarget']:
    chk(f'元素 #{el}', f'id="{el}"' in page or f"id='{el}'" in page or el in page)

# 4) 削峰核心数字不能丢
for token in ['纯赚', '小亏', '大亏', '最优落点', '要收的号', '复制清单发出去']:
    chk(f'文案「{token}」', token in page)

# 5) 两处削峰面板长度明显缩水（整块被删）
chk('页面体积正常', len(page) > 300_000, str(len(page)))

# 6) 页面与备份同步
chk('备份与页面同构', page == backup, f'{len(page)} vs {len(backup)}')

# 7) 不得残留旧硬编码误导文案
for bad in ['都按吃最大 100 元/号 对比']:
    chk(f'无过期文案「{bad}」', bad not in page)

print('=== 发版硬校验 ===')
print('通过 %d 项' % len(OK))
if FAIL:
    print('失败 %d 项：' % len(FAIL))
    for x in FAIL:
        print('  [X]', x)
    sys.exit(1)
print('全部通过，可以打包推送。')
