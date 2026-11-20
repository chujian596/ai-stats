#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成统一站点目录 data/site-directory.json。

每个站固定：
  siteId    = 系统:站号，例如 wanpz-h2:0491
  siteKey   = 原站号
  name      = 站名（registry 优先，别名兜底）
  display   = 站名（站号）
这样任何一期、任何维度的记录都能回到同一个站，不会只剩一个匿名票数。
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def system_of(path):
    if path.startswith("h2/"):
        return "wanpz-h2"
    if path.startswith("h9/"):
        return "wanpz-h9"
    if path.startswith("bdmijg/"):
        return "bdmijg"
    return path.split("/")[0] or "unknown"


def main():
    reg = load("site-registry.json")
    aliases = (load("site-aliases.json") or {}).get("aliases") or {}
    sites = []
    for s in reg.get("sites", []):
        system = system_of(s.get("path", ""))
        key = str(s.get("id") or "")
        site_id = f"{system}:{key}"
        name = (s.get("name") or "").strip()
        source = "registry"
        if not name:
            name = aliases.get(site_id) or aliases.get(key) or ""
            source = "alias" if name else "derived"
        if not name:
            # 聚合站没有公开中文名时，用稳定代号，不能留空。
            num = re.sub(r"^js-", "", key)
            name = f"聚合站{num}"
        display = f"{name}（{key}）"
        sites.append({
            "siteId": site_id,
            "siteKey": key,
            "system": system,
            "name": name,
            "displayName": display,
            "nameSource": source,
            "baseName": s.get("base_name") or "",
            "path": s.get("path") or "",
            "host": s.get("host") or "",
            "script": s.get("script") or "",
            "hasNine": bool(s.get("has_nine")),
            "hasKill3": bool(s.get("has_kill3")),
            "aggregator": bool(s.get("aggregator")),
            "aliases": sorted(set(x for x in [key, site_id, name, display, s.get("base_name") or ""] if x)),
        })

    sites.sort(key=lambda x: (x["system"], x["siteKey"]))
    out = {
        "updatedAt": reg.get("updated_at"),
        "sourceSnapshot": reg.get("source_snapshot"),
        "issue": reg.get("issue"),
        "total": len(sites),
        "sites": sites,
        "bySiteId": {s["siteId"]: s for s in sites},
        "bySiteKey": {s["siteKey"]: s for s in sites},
    }
    with open(os.path.join(DATA, "site-directory.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # 页面的 ALIAS 继续用短名；聚合站补稳定名，避免页面只显示 js-143。
    changed = 0
    for s in sites:
        for k in (s["siteKey"], s["siteId"]):
            if aliases.get(k) != s["name"]:
                aliases[k] = s["name"]
                changed += 1
    with open(os.path.join(DATA, "site-aliases.json"), "w", encoding="utf-8") as f:
        json.dump({"_comment": "站号 -> 中文站名对照。主源 site-directory.json；页面按 siteKey 或 system:siteKey 查。",
                   "aliases": aliases}, f, ensure_ascii=False, indent=1)
    print(f"site-directory.json: {len(sites)} 站；aliases 更新 {changed} 条；空名 {sum(1 for s in sites if not s['name'])}")


if __name__ == "__main__":
    main()
