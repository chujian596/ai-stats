#!/usr/bin/env python3
"""抓取开奖数据，生成同源快照 draw-latest.json（避开跨域 CORS 限制）。

用法：
    python3 fetch_draw.py            # 抓取并写 draw-latest.json
    python3 fetch_draw.py --dry      # 只打印，不写文件

数据源：home-cache 接口（澳门 + 香港最新一期 + 下一期开奖时间）
输出字段：
    {
      "updated": "2026-11-14T02:30:00Z",
      "macao":  {"draw": 317, "numbers": [...7个], "drawn_at": "..."},
      "hongkong": {...},
      "next": {"macao": {"draw":318,"draw_at":"..."}, "hongkong": {...}}
    }
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

API = ("https://ismkog.xn--n8jaf0byahm4a2c4cybyssjl201en76e."
       "xn--q9jyb4c:21044/api/v1/about/home-cache")
OUT = Path(__file__).with_name("draw-latest.json")


def fetch_raw(timeout=20):
    req = Request(API, headers={
        "User-Agent": "Mozilla/5.0 (compatible; ai-stats/1.0)",
        "Accept": "application/json",
    })
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def build(raw):
    latest = raw.get("latest") or {}
    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "home-cache",
    }
    for key in ("macao", "hongkong"):
        item = latest.get(key)
        if item and item.get("winner_numbers"):
            out[key] = {
                "draw": item.get("draw"),
                "year": item.get("year"),
                "numbers": item["winner_numbers"],
                "drawn_at": item.get("drawn_at"),
            }
    nxt = raw.get("next") or {}
    out["next"] = {}
    for key in ("macao", "hongkong"):
        if nxt.get(key):
            out["next"][key] = {
                "draw": nxt[key].get("draw"),
                "draw_at": nxt[key].get("draw_at"),
            }
    return out


def main():
    dry = "--dry" in sys.argv
    try:
        raw = fetch_raw()
    except Exception as e:
        print(f"抓取失败：{e}", file=sys.stderr)
        return 2

    data = build(raw)
    if not data.get("macao") and not data.get("hongkong"):
        print("接口没有返回有效开奖号码", file=sys.stderr)
        return 3

    text = json.dumps(data, ensure_ascii=False, indent=2)
    if dry:
        print(text)
        return 0

    OUT.write_text(text, encoding="utf-8")
    m = data.get("macao", {})
    h = data.get("hongkong", {})
    print(f"已写入 {OUT.name}：澳门 {m.get('draw')} 期 {m.get('numbers')}；"
          f"香港 {h.get('draw')} 期 {h.get('numbers')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
