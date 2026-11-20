#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每期开奖前论坛资料存档脚本
抓取6页列表(每页100条)，解析当期推荐/杀肖，生成模板指纹、提及率、三肖、平特文件。
"""
import json, os, re, sys, html, subprocess, datetime
from concurrent.futures import ThreadPoolExecutor

BASE = "https://ismkog.xn--n8jaf0byahm4a2c4cybyssjl201en76e.xn--q9jyb4c:21044"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_last_drawn_period():
    """读开奖库 official-history.json，返回最新已开奖期号（int）；读不到返回 None。"""
    try:
        off = json.load(open(os.path.join(ROOT_DIR, "official-history.json"), encoding="utf-8"))
        ks = [int(k) for k in off.keys() if str(k).isdigit()]
        return max(ks) if ks else None
    except Exception:
        return None

ZODIACS = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]
ZOD_RE = re.compile(r"[鼠牛虎兔龙蛇马羊猴鸡狗猪]")

# 玩法分类关键词
PINGTE_RE = re.compile(r"平特|平肖")
SANXIAO_RE = re.compile(r"三肖|3肖")
KILL_TITLE_RE = re.compile(r"杀|禁|亡|绝")
# 非生肖维度标题（波/尾/头/段/单双/大小等），不纳入生肖统计
NON_ZOD_RE = re.compile(r"波|尾|头|段|单双|大小|合数|五行|方位|笔画|单双|家禽|野兽|成语|三国|四季|风雨|天地|琴棋|一行|二字|三字|六四|吃肉|吃草|肉菜|吉美|凶丑|文房|三合|东南|西北|两澳|报字|一字|生肖报")


def curl(url, timeout=20):
    p = subprocess.run(["curl","-sk","--compressed","-m",str(timeout),"-A",UA,url],
                       capture_output=True, timeout=timeout+5)
    return p.stdout.decode("utf-8", errors="ignore")


def fetch_page(page):
    url = f"{BASE}/api/v1/forums?lottery=macao&page={page}&per_page=100"
    try:
        raw = curl(url)
        d = json.loads(raw)
        items = d.get("data", []) if isinstance(d, dict) else d
        return page, items
    except Exception as e:
        print(f"  [WARN] page {page} failed: {e}", file=sys.stderr)
        return page, []


def clean_html(c):
    c = re.sub(r"<[^>]+>", "", c)
    c = html.unescape(c)
    return c.replace("開","开").replace("鷄","鸡").replace("　"," ").replace("","")


def extract_current_period_line(content, period):
    """从content中提取当期那一行文本。"""
    c = clean_html(content or "")
    # 找到 "XXX期" 的位置
    pat = re.compile(rf"{period}\s*期")
    m = pat.search(c)
    if not m:
        return None
    # 从匹配位置取到下一个 "XXX期" 或行尾/200字符
    start = m.start()
    rest = c[start:]
    # 找下一个期号标记
    next_m = re.search(r"\d{2,3}\s*期", rest[len(m.group()):])
    if next_m:
        line = rest[:len(m.group()) + next_m.start()]
    else:
        line = rest[:250]
    return line.strip()


def extract_zodiacs(text):
    """从文本中提取生肖字，保持出现顺序去重。"""
    seen = []
    for ch in text:
        if ch in ZODIACS and ch not in seen:
            seen.append(ch)
    return seen


def classify_post(topic, content, period):
    """
    返回 (zodiacs, is_kill, play_type) 或 None（非生肖类帖子）。
    play_type: 'pingte', 'sanxiao', 'kill', 'rec'
    """
    t = topic or ""
    c = content or ""

    # 判断是否杀肖类
    is_kill = bool(KILL_TITLE_RE.search(t)) and ("肖" in t or "杀" in t)

    # 提取当期行
    line = extract_current_period_line(c, period)
    if line is None:
        # 有些帖子content没有期号标记，用整个content
        line = clean_html(c)[:300]

    # 判断玩法
    is_pingte = bool(PINGTE_RE.search(t)) or bool(PINGTE_RE.search(line[:50]))
    is_sanxiao = bool(SANXIAO_RE.search(t))

    # 提取生肖
    zods = extract_zodiacs(line)

    # 杀肖帖：标题有"杀"且明确是肖
    if is_kill and ("肖" in t or "杀" in t):
        # 如果标题有"绝杀三肖"之类
        if not zods:
            return None
        return (zods, True, "kill")

    # 平特帖
    if is_pingte:
        if not zods:
            return None
        return (zods, False, "pingte")

    # 三肖帖
    if is_sanxiao and not is_kill:
        if not zods:
            return None
        return (zods, False, "sanxiao")

    # 普通推荐帖：标题含"肖"且不是非生肖维度
    if "肖" in t and not NON_ZOD_RE.search(t):
        if not zods:
            return None
        return (zods, False, "rec")

    # 有些帖子标题不含"肖"但content里当期行有明确生肖组合（如"两澳一肖"内容就一个"虎"）
    # 只在content行里明确出现生肖且不是非生肖维度时纳入
    if zods and len(zods) >= 1 and not NON_ZOD_RE.search(t):
        # 排除纯号码帖、纯波色帖等
        if len(zods) <= 8:
            return (zods, False, "rec")

    return None


def main():
    # Step 1: 并发抓取6页
    print("=== Step 1: 抓取6页论坛列表 ===", flush=True)
    all_items = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for page, items in ex.map(fetch_page, range(1, 7)):
            print(f"  page {page}: {len(items)} items", flush=True)
            all_items.extend(items)

    print(f"  总计抓取: {len(all_items)} 条", flush=True)

    if not all_items:
        print("ERROR: 论坛API返回空，抓取失败", file=sys.stderr)
        # 输出空结果
        result = {"period": None, "error": "forum_api_empty", "fetched_at": datetime.datetime.now().isoformat()}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    # 确定当前期号：优先「最新已开奖期 +1」（待开期）；论坛投票最大值仅作兜底。
    # 开奖库已并入上一期开奖结果后，待开期自然推进到下一期，不再被论坛帖期号投票带偏。
    draw_counts = {}
    for it in all_items:
        d = it.get("draw")
        if d is not None and str(d).isdigit():
            di = int(d)
            draw_counts[di] = draw_counts.get(di, 0) + 1

    last_drawn = load_last_drawn_period()
    target = last_drawn + 1 if last_drawn else None

    if target and draw_counts.get(target, 0) > 0:
        period = target
        print(f"  当前期号: {period}（已开奖 {last_drawn} +1；论坛 {draw_counts[period]} 帖）", flush=True)
    elif draw_counts:
        period = max(draw_counts, key=draw_counts.get)
        if target:
            print(f"  WARN 待开期 {target} 论坛暂无帖，回退论坛投票最大期 {period}（出现{draw_counts[period]}次）", flush=True)
        else:
            print(f"  当前期号: {period}（开奖库不可用，按论坛投票 {draw_counts[period]} 次）", flush=True)
    else:
        period = target
        print(f"  当前期号: {period}（开奖库待开期；论坛无 draw 标记）", flush=True)

    # Step 2: 解析每条帖子
    print("=== Step 2: 解析帖子 ===", flush=True)
    raw_posts = []
    seen = set()  # (author, title) 去重

    for it in all_items:
        d = it.get("draw")
        if d is None or not str(d).isdigit() or int(d) != period:
            continue
        topic = it.get("topic") or ""
        author = (it.get("user") or {}).get("nickname") or "匿名"
        content = it.get("content") or ""
        key = (author, topic)
        if key in seen:
            continue

        result = classify_post(topic, content, period)
        if result is None:
            continue
        zods, is_kill, play_type = result
        if not zods:
            continue

        seen.add(key)
        raw_posts.append({
            "a": author,
            "t": topic,
            "z": zods,
            "k": is_kill,
            "type": play_type
        })

    print(f"  去重后有效帖子: {len(raw_posts)}", flush=True)

    # Step 3: 统计 rec/kill 生肖提及
    rec_counts = {z: 0 for z in ZODIACS}
    kill_counts = {z: 0 for z in ZODIACS}
    for p in raw_posts:
        for z in p["z"]:
            if p["k"]:
                kill_counts[z] += 1
            else:
                rec_counts[z] += 1

    sum_rec = sum(rec_counts.values())
    sum_kill = sum(kill_counts.values())
    print(f"  推票总数: {sum_rec}, 杀票总数: {sum_kill}", flush=True)

    # 保存 forum-{period}.json
    forum_data = {
        "period": period,
        "fetched_at": datetime.datetime.now().isoformat(),
        "total_fetched": len(all_items),
        "rec": rec_counts,
        "kill": kill_counts,
        "detail": [{"a": p["a"], "t": p["t"], "z": p["z"], "k": p["k"]} for p in raw_posts]
    }
    forum_path = os.path.join(DATA_DIR, f"forum-{period}.json")
    with open(forum_path, "w", encoding="utf-8") as f:
        json.dump(forum_data, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {forum_path}", flush=True)

    # Step 4: 模板指纹 - 按「玩法+生肖组合」去重
    print("=== Step 3: 生成模板指纹 ===", flush=True)
    # 分类: 平特, 三肖, 杀
    cat_templates = {"pingte": set(), "sanxiao": set(), "kill": set()}
    cat_zod_raw = {z: {"pingte": 0, "sanxiao": 0, "kill": 0} for z in ZODIACS}
    cat_zod_tpl = {z: {"pingte": set(), "sanxiao": set(), "kill": set()} for z in ZODIACS}

    for p in raw_posts:
        combo = tuple(sorted(p["z"]))
        if p["type"] == "pingte":
            cat = "pingte"
        elif p["type"] == "sanxiao":
            cat = "sanxiao"
        elif p["k"]:
            cat = "kill"
        else:
            continue  # 普通推荐不计入模板指纹的分类统计？看之前的数据，tpl里只有平特/三肖/杀

        tpl_key = (cat, combo)
        cat_templates[cat].add(tpl_key)
        for z in p["z"]:
            cat_zod_raw[z][cat] += 1
            cat_zod_tpl[z][cat].add(tpl_key)

    total_templates = sum(len(v) for v in cat_templates.values())
    print(f"  模板总数: {total_templates} (平特{len(cat_templates['pingte'])}, 三肖{len(cat_templates['sanxiao'])}, 杀{len(cat_templates['kill'])})", flush=True)

    tpl_rows = []
    for z in ZODIACS:
        pt_raw = cat_zod_raw[z]["pingte"]
        pt_tpl = len(cat_zod_tpl[z]["pingte"])
        sx_raw = cat_zod_raw[z]["sanxiao"]
        sx_tpl = len(cat_zod_tpl[z]["sanxiao"])
        kl_raw = cat_zod_raw[z]["kill"]
        kl_tpl = len(cat_zod_tpl[z]["kill"])
        total_tpl = pt_tpl + sx_tpl + kl_tpl
        tpl_rows.append({
            "s": z,
            "平特": {"raw": pt_raw, "tpl": pt_tpl},
            "三肖": {"raw": sx_raw, "tpl": sx_tpl},
            "杀": {"raw": kl_raw, "tpl": kl_tpl},
            "totalTpl": total_tpl
        })
    tpl_rows.sort(key=lambda x: -x["totalTpl"])

    tpl_data = {
        "period": period,
        "totalEntries": len(raw_posts),
        "templates": total_templates,
        "dupTemplates": len(raw_posts) - total_templates,
        "rows": tpl_rows
    }
    tpl_path = os.path.join(DATA_DIR, f"tpl-{period}.json")
    with open(tpl_path, "w", encoding="utf-8") as f:
        json.dump(tpl_data, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {tpl_path}", flush=True)

    # Step 5: ratio - 提及率与相对强度
    print("=== Step 4: 计算提及率 ===", flush=True)
    ratio_rows = []
    for z in ZODIACS:
        r = rec_counts[z]
        k = kill_counts[z]
        rec_rate = r / sum_rec if sum_rec > 0 else 0
        kill_rate = k / sum_kill if sum_kill > 0 else 0
        rec_lift = round(rec_rate * 12, 2)
        kill_lift = round(kill_rate * 12, 2)
        ratio_rows.append({
            "z": z, "rec": r, "kill": k,
            "recRate": round(rec_rate, 4),
            "killRate": round(kill_rate, 4),
            "recLift": rec_lift,
            "killLift": kill_lift
        })

    ratio_data = {
        "period": period,
        "sumRec": sum_rec,
        "sumKill": sum_kill,
        "method": "提及率=票数/该类总票；相对强度=提及率*12（1.00=平均水平）",
        "rows": ratio_rows
    }
    ratio_path = os.path.join(DATA_DIR, f"ratio-{period}.json")
    with open(ratio_path, "w", encoding="utf-8") as f:
        json.dump(ratio_data, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {ratio_path}", flush=True)

    # Step 6: three - 真三肖
    print("=== Step 5: 提取三肖 ===", flush=True)
    rec3_counts = {z: 0 for z in ZODIACS}
    kill3_counts = {z: 0 for z in ZODIACS}
    rec3_list = []
    kill3_list = []
    total3 = 0
    for p in raw_posts:
        if p["type"] == "sanxiao":
            total3 += 1
            if p["k"]:
                for z in p["z"]:
                    kill3_counts[z] += 1
                kill3_list.append({"z": p["z"], "t": p["t"], "a": p["a"]})
            else:
                for z in p["z"]:
                    rec3_counts[z] += 1
                rec3_list.append({"z": p["z"], "t": p["t"], "a": p["a"]})

    rec3_sorted = sorted([{"s": z, "n": rec3_counts[z]} for z in ZODIACS], key=lambda x: -x["n"])
    kill3_sorted = sorted([{"s": z, "n": kill3_counts[z]} for z in ZODIACS], key=lambda x: -x["n"])

    three_data = {
        "period": period,
        "source": f"论坛{len(all_items)}帖(去重{len(raw_posts)})",
        "total3": total3,
        "rec3": len(rec3_list),
        "kill3": len(kill3_list),
        "rec": rec3_sorted,
        "kill": kill3_sorted,
        "recList": rec3_list,
        "killList": kill3_list
    }
    three_path = os.path.join(DATA_DIR, f"three-{period}.json")
    with open(three_path, "w", encoding="utf-8") as f:
        json.dump(three_data, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {three_path}", flush=True)

    # Step 7: pingte - 平特品类
    print("=== Step 6: 提取平特 ===", flush=True)
    pt_counts = {z: 0 for z in ZODIACS}
    pt_list = []
    for p in raw_posts:
        if p["type"] == "pingte" and not p["k"]:
            kind = "平特一肖" if len(p["z"]) == 1 else ("多肖平特" if len(p["z"]) <= 3 else "多肖平特")
            for z in p["z"]:
                pt_counts[z] += 1
            pt_list.append({"z": p["z"], "t": p["t"], "a": p["a"], "kind": kind})

    pt_sorted = sorted([{"s": z, "n": pt_counts[z]} for z in ZODIACS], key=lambda x: -x["n"])

    pingte_data = {
        "period": period,
        "source": f"论坛{len(all_items)}帖(去重{len(raw_posts)})",
        "total": len(pt_list),
        "rec": pt_sorted,
        "list": pt_list
    }
    pingte_path = os.path.join(DATA_DIR, f"pingte-{period}.json")
    with open(pingte_path, "w", encoding="utf-8") as f:
        json.dump(pingte_data, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {pingte_path}", flush=True)

    # Step 8: 输出报告
    print("\n=== 报告 ===", flush=True)
    print(f"期号: {period}", flush=True)
    print(f"抓取帖子数: {len(all_items)}", flush=True)
    print(f"去重后有效条数: {len(raw_posts)}", flush=True)
    print(f"推票总数: {sum_rec}", flush=True)
    print(f"杀票总数: {sum_kill}", flush=True)

    print(f"\n各生肖独立模板数排名:", flush=True)
    for i, row in enumerate(tpl_rows):
        print(f"  {i+1}. {row['s']}: {row['totalTpl']} (平特{row['平特']['tpl']}/三肖{row['三肖']['tpl']}/杀{row['杀']['tpl']})", flush=True)

    # 击杀强度最低和最高
    kill_lift_sorted = sorted(ratio_rows, key=lambda x: x["killLift"])
    print(f"\n击杀强度最低: {kill_lift_sorted[0]['z']} (killLift={kill_lift_sorted[0]['killLift']})", flush=True)
    print(f"击杀强度最高: {kill_lift_sorted[-1]['z']} (killLift={kill_lift_sorted[-1]['killLift']})", flush=True)

    # 保存报告摘要
    report = {
        "period": period,
        "fetched": len(all_items),
        "deduped": len(raw_posts),
        "sumRec": sum_rec,
        "sumKill": sum_kill,
        "tplRank": tpl_rows,
        "killLow": {"z": kill_lift_sorted[0]["z"], "lift": kill_lift_sorted[0]["killLift"]},
        "killHigh": {"z": kill_lift_sorted[-1]["z"], "lift": kill_lift_sorted[-1]["killLift"]}
    }
    # 写「最新期号」，stats.html 靠它自动切期
    try:
        # 历期索引：stats.html 的「往期资料存档」和期号切换都读这个
        try:
            import glob as _glob, re as _re
            _pers = set()
            for _f in _glob.glob(os.path.join(DATA_DIR, "forum-*.json")):
                _m = _re.search(r"forum-(\d+)\.json$", _f)
                if _m:
                    _pers.add(int(_m.group(1)))
            if period:
                _pers.add(int(period))
            with open(os.path.join(DATA_DIR, "periods.json"), "w", encoding="utf-8") as f:
                json.dump({"periods": sorted(_pers)}, f, ensure_ascii=False)
        except Exception as e:
            print("WARN periods:", e)
        with open(os.path.join(DATA_DIR, "latest-period.json"), "w", encoding="utf-8") as f:
            json.dump({"period": period, "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False)
    except Exception as e:
        print("WARN latest-period:", e)

    report_path = os.path.join(DATA_DIR, f"archive-report-{period}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n完成!", flush=True)


if __name__ == "__main__":
    main()
