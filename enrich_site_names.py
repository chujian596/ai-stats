#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把站点目录里的 siteId / 站名回填到各期台账、待开推荐和站点登记。

口径：
- 站号全局唯一；system 为 wanpz 的旧记录按 siteKey 反查真实系统；
- 回填只加字段，不改原有中/错、票数、栏目值；
- 找不到的站标 siteName="未登记站"，并保留 siteKey，绝不匿名丢掉。
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def save(name, obj):
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


DIR = load("site-directory.json")
BY_ID = DIR["bySiteId"]
BY_KEY = DIR["bySiteKey"]


def attach(rec, system=None):
    if not isinstance(rec, dict):
        return rec
    key = str(rec.get("siteKey") or "")
    if not key:
        return rec
    sysname = system or rec.get("siteSystem") or rec.get("system")
    if sysname in (None, "", "wanpz", "unknown"):
        sysname = None
    site = BY_ID.get(f"{sysname}:{key}") if sysname else None
    site = site or BY_KEY.get(key)
    if not site:
        rec.setdefault("siteName", "未登记站")
        rec.setdefault("siteId", f"{sysname or 'unknown'}:{key}")
        return rec
    rec["siteId"] = site["siteId"]
    rec["siteName"] = site["name"]
    rec["displayName"] = site["displayName"]
    rec["nameSource"] = site["nameSource"]
    # 身份分组字段：全局序号 / 批次 / 基线或追加，供档位截取与新旧分组展示。
    for f in ("seq", "cohort", "tier", "firstSeen", "locked"):
        if f in site:
            rec[f] = site[f]
    if system or rec.get("siteSystem"):
        rec.setdefault("siteSystem", site["system"])
    return rec


def walk_stations(doc):
    periods = (doc or {}).get("periods") or {}
    for per in periods.values():
        for bucket in ("stations", "gaps", "sites"):
            obj = per.get(bucket)
            if isinstance(obj, dict):
                for k, v in obj.items():
                    attach(v, None)
            elif isinstance(obj, list):
                for v in obj:
                    attach(v)
        # 有些期把 stations 直接挂在 period 下
        if isinstance(per.get("siteKey"), str):
            attach(per)


def main():
    ledgers = [
        "max-zodiac-ledger.json", "kill3-ledger.json", "pingte-ledger.json",
        "wave-ledger.json", "tail-ledger.json", "head-ledger.json",
        "size-ledger.json", "parity-ledger.json",
    ]
    for name in ledgers:
        p = os.path.join(DATA, name)
        if not os.path.exists(p):
            continue
        doc = load(name)
        walk_stations(doc)
        save(name, doc)
        print("enriched", name)

    # 待开推荐
    p = os.path.join(DATA, "current-recommend.json")
    if os.path.exists(p):
        doc = load("current-recommend.json")
        for s in doc.get("sites", []):
            attach(s)
        save("current-recommend.json", doc)
        print("enriched current-recommend.json")

    # 站点登记本体也补 siteId / displayName；空名按目录补
    reg = load("site-registry.json")
    for s in reg.get("sites", []):
        site = BY_ID.get(f"{s.get('system') or ''}:{s.get('id')}") or BY_KEY.get(str(s.get("id")))
        if site:
            s["siteId"] = site["siteId"]
            s["name"] = s.get("name") or site["name"]
            s["displayName"] = site["displayName"]
            s["nameSource"] = site["nameSource"]
    save("site-registry.json", reg)
    print("enriched site-registry.json")

    # 多站对比数据
    p = os.path.join(DATA, "sites-current.json")
    if os.path.exists(p):
        doc = load("sites-current.json")
        if isinstance(doc, dict):
            for v in doc.values():
                if isinstance(v, list):
                    for s in v:
                        attach(s)
                elif isinstance(v, dict) and "siteKey" in v:
                    attach(v)
        elif isinstance(doc, list):
            for s in doc:
                attach(s)
        save("sites-current.json", doc)
        print("enriched sites-current.json")


if __name__ == "__main__":
    main()
