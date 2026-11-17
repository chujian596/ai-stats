#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成 cross-<期>.json：论坛推/杀 + 图库共识 的交叉合计。
用法：python3 build_cross.py 321
"""
import json, os, sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
Z = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]

def load(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def main():
    per = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if not per:
        lp = load("latest-period.json") or {}
        per = int(lp.get("period"))
    forum = load(f"forum-{per}.json")
    cons = load(f"consensus-{per}.json")
    if not forum:
        print(f"缺 forum-{per}.json，无法合成"); return

    srcRec = {z: 0 for z in Z}
    srcKill = {z: 0 for z in Z}
    for x in (forum.get("detail") or []):
        for z in (x.get("z") or []):
            if z not in srcRec: continue
            if x.get("k"): srcKill[z] += 1
            else: srcRec[z] += 1

    imgRec = {z: 0 for z in Z}; imgKill = {z: 0 for z in Z}
    if cons:
        if isinstance(cons.get("rec"), dict):
            imgRec = {z: cons["rec"].get(z, 0) for z in Z}
            imgKill = {z: (cons.get("kill") or {}).get(z, 0) for z in Z}
        else:
            for it in (cons.get("zodiacs") or []):
                z = it.get("z")
                if z in imgRec:
                    imgRec[z] = it.get("rec", 0) or 0
                    imgKill[z] = it.get("kill", 0) or 0

    rec = {z: srcRec[z] + (imgRec.get(z) or 0) for z in Z}
    kill = {z: srcKill[z] + (imgKill.get(z) or 0) for z in Z}

    out = {"period": per, "rec": rec, "kill": kill,
           "srcRec": srcRec, "srcKill": srcKill, "imgRec": imgRec, "imgKill": imgKill,
           "imgSource": (cons or {}).get("colsTotal") and "image-ocr" or ("none")}
    with open(os.path.join(DATA, f"cross-{per}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"cross-{per}.json 已生成：论坛推 {sum(srcRec.values())} 杀 {sum(srcKill.values())}；"
          f"图库推 {sum(imgRec.values())} 杀 {sum(imgKill.values())}")

if __name__ == "__main__":
    main()
