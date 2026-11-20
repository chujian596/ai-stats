#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""录入失败诊断闭环流水线。

流程：
  pull    从 /api/diag 拉取失败批次，落 raw JSON
  build   归并同类失败，生成《诊断修复单.md》、tickets.json、cases_diag.json
  list    查看未关闭工单
  qa      跑 tests/release_check.sh，保存 qa-<version>.json
  close   校验 QA 与线上版本后关单，生成《修复报告-<工单>.md》
  selftest 用内置样本验证归并/分类/出单，不访问网络

原则：
- 只自动归并、分类、生成复现和工单；不自动改 parser。
- 没有“期望结果”的工单不能标记修复完成。
- 关单必须同时满足：QA 通过、主站/备用站版本一致、已部署。
- 原始失败只写项目目录下的 diag-work，不提交到公开仓库。
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT.parent / "diag-work"
CST = timezone(timedelta(hours=8))
API = os.environ.get("DIAG_ENDPOINT", "https://aistats-9uo.pages.dev/api/diag")
KEY_FILE = Path("/home/user/.cf-diag-keys")


def now_text():
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")


def stamp():
    return datetime.now(CST).strftime("%Y%m%d-%H%M%S")


def read_key(name):
    if os.environ.get(name):
        return os.environ[name].strip()
    if KEY_FILE.exists():
        for line in KEY_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == name:
                return v.strip().strip('"').strip("'")
    return ""


def api_get(path, key_name="DIAG_READ_KEY", timeout=30, retries=4):
    key = read_key(key_name)
    if not key:
        raise RuntimeError("缺少读取密钥：%s" % key_name)
    req = urllib.request.Request(
        API.rstrip("/") + path,
        headers={
            "x-diag-read-key": key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Connection": "close",
        },
    )
    last = None
    for i in range(max(1, retries)):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (401, 403):
                raise
        except Exception as e:
            last = e
        if i + 1 < retries:
            time.sleep(1.5 * (i + 1))
    raise RuntimeError("诊断接口请求失败（已重试 %d 次）：%r" % (retries, last))


def ensure_out(path):
    path.mkdir(parents=True, exist_ok=True)
    return path


def classify(msg):
    msg = str(msg or "")
    if "整批没有识别到任何项目" in msg or "没有识别到产品" in msg:
        return ("zero", "整批零识别", "先看 rawInput 是否整段乱码、只有标题/客户名；确认零识别拦截是否应触发")
    if "这一行没有识别到号码/生肖/玩法" in msg:
        return ("silent_drop", "静默丢行", "检查行预处理的关键词过滤/分行规则；确认这一行原本应落到哪个玩法")
    if "尾数" in msg or "头数" in msg:
        return ("tail_head", "尾数/头数", "检查尾数/头数的语法、范围和展开规则")
    if "范围" in msg:
        return ("range", "号码范围", "检查号码范围写法与逐个写号码的兼容")
    if "没找到价格" in msg or "价格" in msg or "金额" in msg:
        return ("price", "价格/金额", "检查金额提取：各/每/共/米/元/组，以及上一行价格继承")
    if "组合" in msg or "复式" in msg or "三中三" in msg or "二中二" in msg or "连肖" in msg:
        return ("combo", "组合/复式", "检查组合码、复式、连肖的拆分与金额口径")
    if "无法识别" in msg:
        return ("unknown_token", "残留词/未知产品", "看残留 token：客户名、分隔符、未知玩法、行首标题是否被误送进解析器")
    return ("other", "其它", "先看 rawInput 和失败行，补最小复现后再判断")


def message_signature(msg):
    s = str(msg or "")
    s = re.sub(r"\[客户\]|\[手机\]", "[P]", s)
    s = re.sub(r"\d+(?:\.\d+)?", "#", s)
    s = re.sub(r"[「」『』]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:120]


def ticket_id(category, msg):
    raw = category + "|" + message_signature(msg)
    return "T-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]


def load_doc_batches(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("batches"), list):
        return data.get("batches") or []
    if isinstance(data, list):
        return data
    raise RuntimeError("无法识别的诊断文件结构：%s" % path)


def collect_batches(raw_dir, date=None):
    batches = []
    for f in sorted(raw_dir.glob("*.json")):
        if date and f.stem != date:
            continue
        try:
            batches.extend(load_doc_batches(f))
        except Exception as e:
            print("跳过 %s：%s" % (f, e), file=sys.stderr)
    return batches


def build_tickets(batches, outdir):
    existing = {}
    tpath = outdir / "tickets.json"
    if tpath.exists():
        try:
            for t in json.loads(tpath.read_text(encoding="utf-8")):
                existing[t.get("id")] = t
        except Exception:
            pass

    grouped = {}
    for b in batches:
        for f in (b.get("failures") or []):
            msg = str((f or {}).get("msg") or "未知解析错误")
            cat, label, hint = classify(msg)
            tid = ticket_id(cat, msg)
            t = grouped.get(tid)
            if not t:
                t = {
                    "id": tid,
                    "category": cat,
                    "categoryName": label,
                    "status": "open",
                    "count": 0,
                    "batchCount": 0,
                    "versions": [],
                    "shops": [],
                    "firstSeen": now_text(),
                    "lastSeen": now_text(),
                    "samples": [],
                    "rawInputs": [],
                    "minimalRepro": "",
                    "expected": None,
                    "fixHint": hint,
                    "fix": "",
                    "result": "",
                    "fixVersion": "",
                    "commit": "",
                    "qaPass": None,
                    "closedAt": "",
                }
                grouped[tid] = t
            t["count"] += 1
            t["batchCount"] += 1
            for key, dest in (("appVersion", "versions"), ("shop", "shops")):
                val = str(b.get(key) or "")
                if val and val not in t[dest]:
                    t[dest].append(val)
            t["lastSeen"] = now_text()
            raw_input = str(b.get("rawInput") or "")
            if raw_input and raw_input not in t["rawInputs"]:
                t["rawInputs"].append(raw_input[:2000])
            sample = {
                "lineNo": int(f.get("lineNo") or 0),
                "raw": str(f.get("raw") or "")[:500],
                "msg": msg[:300],
            }
            if len(t["samples"]) < 20:
                t["samples"].append(sample)
            if not t["minimalRepro"]:
                t["minimalRepro"] = sample["raw"] or raw_input[:500]

    merged = []
    for tid, t in grouped.items():
        old = existing.get(tid) or {}
        for key in ("status", "expected", "fix", "result", "fixVersion", "commit", "qaPass", "closedAt"):
            if old.get(key) not in (None, ""):
                t[key] = old[key]
        merged.append(t)
    merged.sort(key=lambda x: (x.get("status") != "open", x.get("category"), x.get("id")))

    ensure_out(outdir)
    tpath.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    cases = []
    cpath = outdir / "cases_diag.json"
    old_cases = {}
    if cpath.exists():
        try:
            for c in json.loads(cpath.read_text(encoding="utf-8")):
                old_cases[c.get("id")] = c
        except Exception:
            pass
    for t in merged:
        cid = "D-" + t["id"].replace("T-", "")
        old = old_cases.get(cid) or {}
        case_input = t.get("rawInputs", [""])[0] if t.get("rawInputs") else t.get("minimalRepro", "")
        # 回归用例要去掉脱敏占位符，不能让 parser 把「[客户]」当真实客户名
        case_input = re.sub(r"\[客户\]\s*", "", str(case_input))
        case_input = re.sub(r"\[手机\]", "", case_input).strip()
        if not case_input:
            case_input = t.get("minimalRepro", "")
        cases.append({
            "id": cid,
            "ticketId": t["id"],
            "input": case_input,
            "expect": old.get("expect"),
            "status": old.get("status") or "needs_expectation",
            "appVersion": t.get("versions", [""])[0] if t.get("versions") else "",
        })
    cpath.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")

    write_ticket_md(merged, outdir)
    write_summary(merged, batches, outdir)
    return merged


def write_summary(tickets, batches, outdir):
    summary = {
        "generatedAt": now_text(),
        "batches": len(batches),
        "failureLines": sum(len((b.get("failures") or [])) for b in batches),
        "tickets": len(tickets),
        "open": len([t for t in tickets if t.get("status") == "open"]),
        "fixedVerified": len([t for t in tickets if t.get("status") == "fixed-verified"]),
        "closed": len([t for t in tickets if t.get("status") == "closed"]),
    }
    (outdir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("汇总：批次 %(batches)s / 失败行 %(failureLines)s / 工单 %(tickets)s（待修 %(open)s，已验 %(fixedVerified)s，已关 %(closed)s）" % summary)


def write_ticket_md(tickets, outdir):
    lines = [
        "# 录入失败修复单",
        "",
        "生成时间：%s" % now_text(),
        "",
        "> 说明：这里只做归并、分类和复现，不自动改 parser。每条工单必须补“期望结果”后才能修复；修完必须跑全量质检并核对线上版本才能关单。",
        "",
    ]
    if not tickets:
        lines += ["当前没有失败批次。", ""]
    else:
        lines += ["| 工单 | 分类 | 次数 | 版本 | 最小复现 | 状态 |", "|---|---|---|---|---|---|"]
        for t in tickets:
            repro = str(t.get("minimalRepro") or "").replace("|", "\\|")[:60]
            lines.append("| %s | %s | %s | %s | %s | %s |" % (
                t["id"], t.get("categoryName"), t.get("count"),
                ",".join(t.get("versions") or []), repro, t.get("status"),
            ))
        lines.append("")
        for t in tickets:
            lines += [
                "## %s · %s" % (t["id"], t.get("categoryName")),
                "",
                "- 状态：%s" % t.get("status"),
                "- 次数：%s 行 / %s 批" % (t.get("count"), t.get("batchCount")),
                "- 版本：%s" % (", ".join(t.get("versions") or []) or "未知"),
                "- 盘口：%s" % (", ".join(t.get("shops") or []) or "未知"),
                "- 修复提示：%s" % t.get("fixHint"),
                "- 最小复现：`%s`" % str(t.get("minimalRepro") or ""),
                "- 期望结果：%s" % ("待填写（项目数/金额/盘口）" if t.get("expected") in (None, "") else t.get("expected")),
                "",
                "失败样本：",
            ]
            for s in t.get("samples") or []:
                lines.append("- 第 %s 行：`%s` → %s" % (s.get("lineNo"), s.get("raw"), s.get("msg")))
            if t.get("rawInputs"):
                lines += ["", "原始输入（已脱敏）：", "```text", str(t["rawInputs"][0])[:2000], "```"]
            lines.append("")
    (outdir / "诊断修复单.md").write_text("\n".join(lines), encoding="utf-8")


def cmd_pull(args):
    outdir = ensure_out(Path(args.out).expanduser())
    rawdir = ensure_out(outdir / "raw")
    if args.date:
        dates = [args.date]
    else:
        data = api_get("?list=1")
        dates = data.get("dates") or []
        if not dates:
            print("诊断仓库当前没有日期数据。")
            build_tickets([], outdir)
            return 0
    total = 0
    for day in dates[: args.limit]:
        try:
            doc = api_get("?date=%s&limit=100" % day)
        except Exception as e:
            print("拉取 %s 失败：%s" % (day, e), file=sys.stderr)
            continue
        (rawdir / (day + ".json")).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        total += len(doc.get("batches") or [])
        print("已拉取 %s：%s 批" % (day, len(doc.get("batches") or [])))
    batches = collect_batches(rawdir, args.date)
    build_tickets(batches, outdir)
    print("输出目录：%s" % outdir)
    return 0 if total or dates else 1


def cmd_build(args):
    outdir = ensure_out(Path(args.out).expanduser())
    rawdir = ensure_out(outdir / "raw")
    if args.input and args.input != "-":
        batches = load_doc_batches(args.input)
    elif args.input == "-":
        data = json.load(sys.stdin)
        batches = data.get("batches") if isinstance(data, dict) else data
    else:
        batches = collect_batches(rawdir, args.date)
    build_tickets(batches, outdir)
    print("输出目录：%s" % outdir)
    return 0


def load_tickets(outdir):
    p = outdir / "tickets.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def cmd_list(args):
    outdir = Path(args.out).expanduser()
    tickets = load_tickets(outdir)
    if not tickets:
        print("没有工单；先执行 pull/build。")
        return 0
    for t in tickets:
        print("%s | %-14s | %-9s | %s行 | %s" % (
            t.get("id"), t.get("categoryName"), t.get("status"), t.get("count"), t.get("minimalRepro", "")[:60],
        ))
    return 0


def cmd_qa(args):
    outdir = ensure_out(Path(args.out).expanduser())
    version = args.version or (ROOT / "version.txt").read_text(encoding="utf-8").strip()
    log_path = outdir / ("qa_%s_%s.log" % (version, stamp()))
    proc = subprocess.run(["bash", "tests/release_check.sh"], cwd=str(ROOT), capture_output=True, text=True)
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    log_path.write_text(text, encoding="utf-8")
    checks = {
        "exit": proc.returncode,
        "matrixPro": "失败 0" in text and "app-pro.html" in text,
        "matrixClient": "失败 0" in text and "app.html" in text,
        "browserGate": "浏览器门禁通过" in text,
        "gate348": "348/348" in text,
        "flySettle": "混搭 4/4" in text,
        "hardCheck": "全部通过，可以打包推送" in text,
    }
    ok = proc.returncode == 0 and checks["browserGate"] and checks["gate348"] and checks["flySettle"] and checks["hardCheck"]
    data = {
        "version": version,
        "at": now_text(),
        "ok": ok,
        "checks": checks,
        "log": str(log_path),
        "tail": "\n".join(text.splitlines()[-20:]),
    }
    (outdir / ("qa-%s.json" % version)).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"version": version, "ok": ok, "checks": checks, "log": str(log_path)}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def online_version(url):
    # 只取页头 80KB，避免整页 600KB 在网络慢时超时；APP_VER 在页面前部
    req = urllib.request.Request(
        url + ("&" if "?" in url else "?") + "t=%d" % int(time.time()),
        headers={"Range": "bytes=0-80000", "User-Agent": "ai-stats-diag-qa/1.0"},
    )
    m = None
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                text = r.read(80000).decode("utf-8", "ignore")
            m = re.search(r"var APP_VER\s*=\s*'([^']+)'", text)
            if m:
                return m.group(1)
        except Exception:
            pass
        time.sleep(1.0)
    return ""


def cmd_close(args):
    outdir = ensure_out(Path(args.out).expanduser())
    tickets = load_tickets(outdir)
    t = next((x for x in tickets if x.get("id") == args.ticket), None)
    if not t:
        print("找不到工单：%s" % args.ticket, file=sys.stderr)
        return 2
    if t.get("expected") in (None, ""):
        print("工单还没有“期望结果”，不能关单：%s" % args.ticket, file=sys.stderr)
        return 2
    version = args.version or (ROOT / "version.txt").read_text(encoding="utf-8").strip()
    qa_path = outdir / ("qa-%s.json" % version)
    if not qa_path.exists():
        print("缺少 QA 记录：%s；先跑 qa --version %s" % (qa_path, version), file=sys.stderr)
        return 2
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    if not qa.get("ok"):
        print("QA 未通过，不能关单：%s" % qa_path, file=sys.stderr)
        return 2
    if not args.deployed:
        print("还没标记已部署；确认线上版本后再加 --deployed。", file=sys.stderr)
        return 2
    main_v = online_version("https://chujian596.github.io/ai-stats/app-pro.html")
    backup_v = online_version("https://chujian596.github.io/ai-stats/app-pro-backup.html")
    if main_v != version or backup_v != version:
        print("线上版本不一致：main=%s backup=%s 期望=%s" % (main_v, backup_v, version), file=sys.stderr)
        return 2

    t["status"] = "closed"
    t["fix"] = args.fix or t.get("fix")
    t["result"] = args.result or t.get("result")
    t["fixVersion"] = version
    t["commit"] = args.commit or ""
    t["qaPass"] = True
    t["closedAt"] = now_text()
    (outdir / "tickets.json").write_text(json.dumps(tickets, ensure_ascii=False, indent=2), encoding="utf-8")
    report = [
        "# 修复报告 · %s" % t["id"],
        "",
        "- 分类：%s" % t.get("categoryName"),
        "- 关闭时间：%s" % t["closedAt"],
        "- 修复版本：%s" % version,
        "- 提交：%s" % (t.get("commit") or "未填写"),
        "",
        "## 1. 出现了什么错误",
        "",
        "- 次数：%s 行 / %s 批" % (t.get("count"), t.get("batchCount")),
        "- 最小复现：`%s`" % t.get("minimalRepro"),
        "- 失败原因：%s" % (t.get("samples", [{}])[0].get("msg") if t.get("samples") else ""),
        "",
        "## 2. 怎么修",
        "",
        t.get("fix") or "未填写",
        "",
        "## 3. 修后结果",
        "",
        t.get("result") or "未填写",
        "",
        "## 4. 质检与上线",
        "",
        "- QA：通过（%s）" % qa.get("at"),
        "- 主站版本：%s" % main_v,
        "- 备用站版本：%s" % backup_v,
        "- QA 日志：`%s`" % qa.get("log"),
        "",
        "## 5. 回归用例",
        "",
        "- `D-%s`" % t["id"].replace("T-", ""),
        "",
    ]
    (outdir / ("修复报告-%s.md" % t["id"])).write_text("\n".join(report), encoding="utf-8")
    print("已关单：%s；报告：%s" % (t["id"], outdir / ("修复报告-%s.md" % t["id"])))
    return 0


def cmd_selftest(args):
    outdir = ensure_out(Path(args.out).expanduser() / "selftest")
    sample = {
        "date": "2026-11-20",
        "batches": [
            {
                "batchId": "selftest-silent-1",
                "appVersion": "v59.60-Pro",
                "shop": "A",
                "rawInput": "[客户] 平特龙10 尾数a",
                "failures": [{"lineNo": 2, "raw": "尾数a", "msg": "这一行没有识别到号码/生肖/玩法"}],
            },
            {
                "batchId": "selftest-zero-1",
                "appVersion": "v59.60-Pro",
                "shop": "B",
                "rawInput": "[客户] 乱码xyz 不存在",
                "failures": [{"lineNo": 1, "raw": "[客户] 乱码xyz 不存在", "msg": "整批没有识别到任何项目"}],
            },
            {
                "batchId": "selftest-silent-2",
                "appVersion": "v59.60-Pro",
                "shop": "A",
                "rawInput": "[客户] 平特龙10 尾数a",
                "failures": [{"lineNo": 3, "raw": "尾数a", "msg": "这一行没有识别到号码/生肖/玩法"}],
            },
        ],
    }
    rawdir = ensure_out(outdir / "raw")
    (rawdir / "2026-11-20.json").write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    tickets = build_tickets(sample["batches"], outdir)
    assert len(tickets) == 2, tickets
    silent = [t for t in tickets if t["category"] == "silent_drop"][0]
    assert silent["count"] == 2 and silent["batchCount"] == 2, silent
    assert silent["minimalRepro"] == "尾数a", silent
    assert (outdir / "诊断修复单.md").exists()
    assert (outdir / "cases_diag.json").exists()
    print("selftest 通过：2 个工单，静默丢行归并 2 次；输出 %s" % outdir)
    return 0


def main():
    ap = argparse.ArgumentParser(description="录入失败诊断闭环流水线")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="输出目录，默认项目下 diag-work")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pull", help="拉取云端失败批次")
    p.add_argument("--date", help="只拉某一天 YYYY-MM-DD")
    p.add_argument("--limit", type=int, default=30, help="最多拉多少天")
    p.set_defaults(func=cmd_pull)

    p = sub.add_parser("build", help="从 raw/或输入文件生成工单")
    p.add_argument("--input", help="诊断 JSON；- 表示 stdin")
    p.add_argument("--date")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("list", help="列出工单")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("qa", help="跑完整发版质检")
    p.add_argument("--version", help="默认读 version.txt")
    p.set_defaults(func=cmd_qa)

    p = sub.add_parser("close", help="QA+线上版本通过后关单并生成报告")
    p.add_argument("--ticket", required=True)
    p.add_argument("--version")
    p.add_argument("--fix", help="怎么修的")
    p.add_argument("--result", help="修后结果")
    p.add_argument("--commit", help="提交号")
    p.add_argument("--deployed", action="store_true", help="确认已部署并核对线上版本")
    p.set_defaults(func=cmd_close)

    p = sub.add_parser("selftest", help="内置样本自测，不访问网络")
    p.set_defaults(func=cmd_selftest)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
