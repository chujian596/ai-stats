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
    if path.startswith("bdmijg/"):
        return "bdmijg"
    m = re.match(r"h(\d+)/", path)
    if m:
        return f"wanpz-h{m.group(1)}"
    return path.split("/")[0] or "unknown"


def cohort_of(first_seen, locked, status):
    """站点批次：legacy=316-324 锁定基线；325=上一轮新增；其余按纳入期号；empty=空站。"""
    if status == "empty":
        return "empty"
    if locked:
        return "legacy"
    if first_seen in (325, "325"):
        return "325"
    return str(first_seen) if first_seen else "unknown"


def host_of(system):
    """wanpz-h8 -> h8；bdmijg 原样。"""
    return system[len("wanpz-"):] if system.startswith("wanpz-") else system


def main():
    reg = load("site-registry.json")
    aliases = (load("site-aliases.json") or {}).get("aliases") or {}
    # 候选池：已取名、分级，尚未抓当期快照；先登记身份层，tier=added、status=pending，不进 core 基线、不回填历史。
    try:
        cand = load("candidates.json")
        cand_rows = cand.get("rows") or []
    except Exception:
        cand_rows = []
    # 批次/锁定状态来自 source-registry（按 siteId 关联），重跑不丢身份判定。
    try:
        src = load("source-registry.json")
        src_by_id = {x.get("siteId"): x for x in (src.get("sites") or [])}
    except Exception:
        src_by_id = {}
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
        src = src_by_id.get(site_id, {})
        first_seen = src.get("firstSeen")
        locked = bool(src.get("locked"))
        status = src.get("status") or ("fixed" if not locked else "fixed")
        cohort = cohort_of(first_seen, locked, status)
        # core=当前在跑的原基线（legacy+325）；added=后续批次新追加站。
        tier = "core" if cohort in ("legacy", "325") else "added"
        sites.append({
            "siteId": site_id,
            "siteKey": key,
            "system": system,
            "siteName": name,
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
            "firstSeen": first_seen,
            "locked": locked,
            "status": status,
            "cohort": cohort,
            "tier": tier,
            "aliases": sorted(set(x for x in [key, site_id, name, display, s.get("base_name") or ""] if x)),
        })

    # 候选追加段：保持 candidates.json 既有分级顺序（A→B→Cn→Ck→D），不按站号重排。
    for idx, c in enumerate(cand_rows):
        system = c.get("system") or "unknown"
        key = str(c.get("siteKey") or "")
        site_id = f"{system}:{key}"
        name = (c.get("banner") or "").strip() or f"候选{key}"
        host = host_of(system)
        sites.append({
            "siteId": site_id,
            "siteKey": key,
            "system": system,
            "siteName": name,
            "name": name,
            "displayName": c.get("displayName") or f"{name}（{key}）",
            "nameSource": "candidate",
            "baseName": "",
            "path": f"{host}/{key}",
            "host": f"https://{host}.wanpz.com",
            "script": f"https://{host}.wanpz.com/script/{key}/",
            "hasNine": bool(c.get("nine")),
            "hasKill3": bool(c.get("kill3")),
            "hasPt1": bool(c.get("pt1")),
            "aggregator": False,
            "grade": c.get("grade") or "",
            "cols": c.get("cols") or 0,
            "flags": c.get("flags") or [],
            "firstSeen": 327,
            "locked": False,
            "status": "pending",
            "cohort": "added",
            "tier": "added",
            "_cand_idx": idx,
            "aliases": sorted(set(x for x in [key, site_id, name, c.get("displayName") or ""] if x)),
        })

    # 全局连续固定序号：core 基线在前、added 新站在后；core 内按 system,siteKey，added 内按候选原序。
    def _sort_key(x):
        if x["tier"] == "core":
            return (0, x["system"], x["siteKey"], 0)
        return (1, "", "", x.get("_cand_idx", 0))

    sites.sort(key=_sort_key)
    for s in sites:
        s.pop("_cand_idx", None)
    for i, s in enumerate(sites, 1):
        s["seq"] = i
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
    import collections
    print(f"  cohort {dict(collections.Counter(s['cohort'] for s in sites))}；"
          f"tier {dict(collections.Counter(s['tier'] for s in sites))}；"
          f"seq {sites[0]['seq'] if sites else '-'}–{sites[-1]['seq'] if sites else '-'}")


if __name__ == "__main__":
    main()
