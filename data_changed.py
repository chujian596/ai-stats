#!/usr/bin/env python3
"""判断指定 JSON 是否有实质内容变化。
做法：把工作区版本与 HEAD 版本都做「稳定序列化」——递归剔除时间戳类字段、字典键排序，
再逐字节比较。只差时间戳/键序时视为无变化，不产生提交。
用法: python3 data_changed.py data/a.json data/b.json ...
输出: 每行一个「有实质变化」的文件路径；全部无变化则不输出任何内容，退出码 0。
"""
import json
import subprocess
import sys

TS_KEYS = {
    "updated_at", "update_at", "updatedAt", "generated_at", "generatedAt",
    "created_at", "createdAt", "_updated", "ts", "timestamp", "checked_at",
}


def canon(obj):
    if isinstance(obj, dict):
        return {k: canon(v) for k, v in sorted(obj.items()) if k not in TS_KEYS}
    if isinstance(obj, list):
        return [canon(v) for v in obj]
    return obj


def sig(text):
    try:
        return json.dumps(canon(json.loads(text)), ensure_ascii=False,
                          sort_keys=True, separators=(",", ":"))
    except Exception:
        return text  # 非 JSON 或损坏：按原文比较，宁可报变化


def head_text(path):
    try:
        return subprocess.check_output(["git", "show", f"HEAD:{path}"],
                                       stderr=subprocess.DEVNULL).decode("utf-8")
    except Exception:
        return None


def main():
    changed = []
    for p in sys.argv[1:]:
        try:
            cur = open(p, encoding="utf-8").read()
        except FileNotFoundError:
            continue
        old = head_text(p)
        if old is None or sig(cur) != sig(old):
            changed.append(p)
    for p in changed:
        print(p)


if __name__ == "__main__":
    main()
