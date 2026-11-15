#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图库改图检测：比对同一期栏目图的指纹，判断开奖后是否被替换。

用法：
    python3 check_img_snap.py 319          # 检查 319 期
    python3 check_img_snap.py 319 --save   # 只存指纹，不比对

原理：118 图库的栏目图放在 col/<期号>/<栏目>.jpg，开奖前就已发布。
如果开奖后同一文件名下的字节发生变化，说明该站在事后换图（换掉没中的那张），
则其公开命中率与 0491 的网页删行属于同一类操作，不可信。
"""
import hashlib
import json
import os
import ssl
import sys
import urllib.request

BASE = "https://amo.jlidesign.com:4949/col/{}/{}"
SNAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "img-snap")
UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"}


def fetch(period, name):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    url = BASE.format(period, name + ".jpg")
    req = urllib.request.Request(url, headers=UA)
    body = urllib.request.urlopen(req, timeout=20, context=ctx).read()
    return body


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    period = sys.argv[1]
    save_only = "--save" in sys.argv
    d = os.path.join(SNAP_DIR, period)
    os.makedirs(d, exist_ok=True)
    mf = os.path.join(d, "manifest.json")
    before = json.load(open(mf, encoding="utf-8")) if os.path.exists(mf) else {"files": {}}

    names = sorted(before["files"].keys())
    if not names:
        print("该期还没有基线指纹，请先 --save 存一次。")
        return 1

    changed, missing, same = [], [], []
    for n in names:
        try:
            body = fetch(period, n)
        except Exception as e:
            missing.append((n, str(e)[:40]))
            continue
        h = hashlib.md5(body).hexdigest()
        old = before["files"][n]["md5"]
        if h == old:
            same.append(n)
        else:
            changed.append({"name": n, "old": old, "new": h,
                            "old_bytes": before["files"][n]["bytes"], "new_bytes": len(body)})

    print(f"期号 {period}　栏目 {len(names)} 个")
    print(f"  未变 {len(same)}　被换 {len(changed)}　取不到 {len(missing)}")
    for c in changed:
        print(f"    [换图] {c['name']:<10} {c['old'][:10]}({c['old_bytes']}B) -> {c['new'][:10]}({c['new_bytes']}B)")
    for n, e in missing:
        print(f"    [缺失] {n:<10} {e}")

    if changed:
        print("\n结论：开奖后有条目图被替换，该库存在事后改图，公开结果不可信。")
    else:
        print("\n结论：全部指纹一致，该库未事后改图，其当期预测与结果均为事前锁定。")

    if save_only:
        for n in same:
            pass
        out = os.path.join(d, "check-%s.json" % period)
        json.dump({"period": period, "changed": changed, "missing": missing},
                  open(out, "w"), ensure_ascii=False, indent=1)
        print("明细已写入", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
