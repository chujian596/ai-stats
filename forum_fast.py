#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
论坛资料快速抓取（12 线程并发版）
用途：开奖前 1.5 小时抓取公开论坛「文字帖」，产出 forum-snapshot.json / forum-summary.json
用法：python3 forum_fast.py
"""
import sys, os, json, hashlib, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forum_reader as F
from concurrent.futures import ThreadPoolExecutor

official = F.load_official()
print("官方历史", len(official), "期", flush=True)

threads = {}
page = 1
while page <= F.MAX_PAGES:
    try:
        items = F.fetch_json(f"{F.BASE}/api/v1/forums?lottery=macao&page={page}&per_page={F.PAGE_SIZE}")
        items = items.get("data", []) if isinstance(items, dict) else items
    except Exception as e:
        print("列表异常", page, e, flush=True)
        break
    if not items:
        break
    new = 0
    for it in items:
        i = it["id"]
        if i in threads:
            continue
        threads[i] = {"id": i, "topic": it.get("topic") or "",
                      "user": (it.get("user") or {}).get("nickname") or "匿名"}
        new += 1
    if new == 0:
        break
    page += 1
print("列表共", len(threads), "帖，最大id", max(threads) if threads else None, flush=True)

todo = [t for t in threads.values() if F.classify(t["topic"]) in ("kill", "rec")]
todo.sort(key=lambda t: t["id"], reverse=True)   # 先拉最新
todo = todo[:F.DETAIL_CAP]
cache = json.load(open(F.DETAIL_CACHE, encoding="utf-8")) if os.path.exists(F.DETAIL_CACHE) else {}
need = [t for t in todo if str(t["id"]) not in cache]
print("待拉", len(need), flush=True)


def get(t):
    tid = str(t["id"])
    try:
        d = F.fetch_json(f"{F.BASE}/api/v1/forums/{tid}")
        dd = d.get("data", d) if isinstance(d, dict) else d
        return tid, (dd.get("content") or "")
    except Exception:
        return tid, ""


done = 0
with ThreadPoolExecutor(max_workers=12) as ex:
    for tid, c in ex.map(get, need):
        cache[tid] = c
        done += 1
        if done % 400 == 0:
            print("  已拉", done, flush=True)
            json.dump(cache, open(F.DETAIL_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
json.dump(cache, open(F.DETAIL_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
print("详情拉取完成", done, flush=True)

columns = []
for t in todo:
    tid = str(t["id"])
    content = cache.get(tid, "")
    rows = F.parse_rows(content)
    kind = F.classify(t["topic"])
    if not any(r["zods"] for r in rows):
        kind = "other"
    columns.append({
        "threadId": tid, "name": t["user"], "topic": t["topic"], "kind": kind,
        "sourceUrl": f"{F.BASE}/api/v1/forums/{tid}", "apiUrl": f"/api/v1/forums/{tid}",
        "fetchedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rawSha": hashlib.sha1(content.encode("utf-8", "ignore")).hexdigest()[:10],
        "rows": rows,
    })
F.reconcile(columns, official)
