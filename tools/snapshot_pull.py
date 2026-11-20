#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开奖前数据快照：三体系全站抓取
wanpz-h2 / wanpz-h9 / bdmijg
"""
import requests, re, base64, zlib, json, os, sys, time, glob
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

requests.packages.urllib3.disable_warnings()
BASE = "/home/user/Doubao/chats/36344898080638210"
HEAD = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"}
ZODIAC = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
# 掉站回补规矩：上一版有票、本轮漏抓的站，先重试，再兜底沿用当天上一版；跨期不补
RETRY_ROUNDS = 3
RETRY_GAP = 8


def _load_site_directory():
    p = os.path.join(BASE, "ai-stats", "data", "site-directory.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"bySiteId": {}, "bySiteKey": {}}


SITE_DIRECTORY = _load_site_directory()


def attach_site_name(rec):
    """给每个抓取记录固化 siteId / 站名，后续任何一期都能追回同站。"""
    key = str(rec.get("siteKey") or "")
    system = rec.get("system") or ""
    site = (SITE_DIRECTORY.get("bySiteId") or {}).get(f"{system}:{key}") \
        or (SITE_DIRECTORY.get("bySiteKey") or {}).get(key)
    if site:
        rec["siteId"] = site["siteId"]
        rec["siteName"] = site["name"]
        rec["displayName"] = site["displayName"]
        rec["nameSource"] = site["nameSource"]
    else:
        rec.setdefault("siteName", "未登记站")
        rec.setdefault("siteId", f"{system}:{key}")
    return rec


def hourly_hash():
    n = datetime.now()
    s = f"{n.year}{n.month:02d}{n.day:02d}_{n.hour}"
    h = 0
    for c in s:
        h = ((h << 5) - h + ord(c)) | 0
    return abs(h).__format__('x')


def get(url, timeout=25):
    # 代理不稳时自动回退直连（2026-11-15/16 均出现 vortex 代理 502 导致整批失败）
    try:
        return requests.get(url, timeout=timeout, verify=False, headers=HEAD)
    except Exception:
        # 代理体质的任何失败（502 RemoteDisconnected / ReadTimeout / ProxyError）一律回退直连
        s = requests.Session(); s.trust_env = False
        return s.get(url, timeout=timeout, verify=False, headers=HEAD)

def fetch_js(url):
    r = get(url)
    if r.status_code != 200:
        return None
    m = re.search(r"atob\('([^']+)'\)", r.text)
    if not m:
        return None
    try:
        return json.loads(base64.b64decode(m.group(1)).decode('utf-8'))
    except Exception:
        return None


def extract_wanpz(system, site_key, js):
    """从 temps_result js 提取当期各栏目推荐"""
    items = js.get('data') if isinstance(js, dict) else None
    if not items:
        return None
    # 只保留新澳彩(Macau)
    valid = []
    target = 0
    for it in items:
        dd = it.get('data')
        if not isinstance(dd, dict) or not dd.get('data'):
            continue
        rtype = dd.get('ruleType') or ''
        ck = it.get('cacheKey') or ''
        if rtype and rtype != 'Macau':
            continue
        if not rtype and 'Macau' not in ck:
            continue
        title = (dd.get('title') or '').strip()
        if not title or '获取' in title:
            continue
        rows = dd['data']
        for r in rows:
            si = r.get('shortIssue')
            if isinstance(si, (int, float)) and si:
                target = max(target, int(si))
        valid.append((it.get('widgetId'), dd.get('ruleId'), title, rows))

    if not valid or target == 0:
        return None

    cols = {}
    for wid, rid, title, rows in valid:
        cur = None
        for r in rows:
            g = r.get('g') or {}
            issues = g.get('issues') or []
            if r.get('shortIssue') == target or (str(target) in [str(x) for x in issues]):
                cur = r
                break
        if not cur:
            continue
        g = cur.get('g') or {}
        vals = []
        for k in sorted(g.keys()):
            if k == 'issues':
                continue
            v = g[k]
            if isinstance(v, list):
                vals.extend([str(x) for x in v])
            elif v:
                vals.append(str(v))
        if not vals:
            continue
        joined = ''.join(vals)
        if '更新' in joined:
            continue
        cols[title] = {
            "value": "".join(vals),
            "parts": vals,
            "ruleId": rid,
            "widgetId": wid,
        }
    if not cols:
        return None
    return {"system": system, "siteKey": site_key, "issue": target, "columns": cols}


def pull_h2(site_key):
    hh = hourly_hash()
    url = f"https://h2.wanpz.com/script/{site_key}/temps_result_1.js?v={hh}"
    js = fetch_js(url)
    if not js:
        return {"system": "wanpz-h2", "siteKey": site_key, "error": "no_data"}
    res = extract_wanpz("wanpz-h2", site_key, js)
    if not res:
        return {"system": "wanpz-h2", "siteKey": site_key, "error": "empty"}
    # 0491 等站的绝杀专区等额外列已在 temps 内，无需 dynamic
    return res


def pull_h9(site_key):
    hh = hourly_hash()
    url = f"https://h9.wanpz.com/script/{site_key}/temps_result_1.js?v={hh}"
    js = fetch_js(url)
    if not js:
        return {"system": "wanpz-h9", "siteKey": site_key, "error": "no_data"}
    res = extract_wanpz("wanpz-h9", site_key, js)
    if not res:
        return {"system": "wanpz-h9", "siteKey": site_key, "error": "empty"}
    # 12460 绝杀三肖在 dynamic_1036811
    if site_key == '12460':
        dj = fetch_js(f"https://h9.wanpz.com/script/12460/dynamic_1036811_1.js?v={hh}")
        if dj:
            txt = dj.get('html') if isinstance(dj, dict) else ''
            txt = re.sub(r'<[^>]+>', '', str(txt)).replace('\n', '')
            found = re.findall(r"(\d{3})期[：:]?\s*绝杀三肖【([^】]+)】", txt)
            for iss, val in found:
                if int(iss) == res["issue"]:
                    res["columns"]["绝杀三肖"] = {"value": val.strip(), "parts": list(val.strip()),
                                                "ruleId": "dynamic_1036811", "widgetId": None}
                    break
    return res


def pull_wanpz(system, site_key):
    """任意 wanpz 子域：h1/h2/h3/h5/h6/h8/h9/h10。"""
    if system == 'wanpz-h9':
        return pull_h9(site_key)
    if system == 'wanpz-h2':
        return pull_h2(site_key)
    host = system.replace('wanpz-', '')
    hh = hourly_hash()
    url = f"https://{host}.wanpz.com/script/{site_key}/temps_result_1.js?v={hh}"
    js = fetch_js(url)
    if not js:
        return {"system": system, "siteKey": site_key, "error": "no_data"}
    res = extract_wanpz(system, site_key, js)
    if not res:
        return {"system": system, "siteKey": site_key, "error": "empty"}
    return res


def pull_bdmijg(jsid, target_issue=None):
    key = jsid if jsid.startswith('js-') else f"js-{jsid}"
    url = f"https://api.bdmijg.com/{key}-index?v=11122"
    try:
        r = get(url, timeout=30)
    except Exception:
        return {"system": "bdmijg", "siteKey": key, "error": "net"}
    if r.status_code != 200:
        return {"system": "bdmijg", "siteKey": key, "error": f"http{r.status_code}"}
    m = re.search(r"var\s+__jGr\s*=\s*'(.*?)';", r.text, re.S)
    if not m:
        return {"system": "bdmijg", "siteKey": key, "error": "no_jGr"}
    try:
        obj = json.loads(m.group(1))
    except Exception:
        return {"system": "bdmijg", "siteKey": key, "error": "bad_json"}
    chunks = []
    for val in obj.values():
        if isinstance(val, list):
            for v in val:
                if not isinstance(v, str):
                    continue
                try:
                    chunks.append(zlib.decompress(base64.b64decode(v), -15).decode('utf-8', 'ignore'))
                except Exception:
                    pass
        elif isinstance(val, str) and len(val) > 20:
            try:
                chunks.append(zlib.decompress(base64.b64decode(val), -15).decode('utf-8', 'ignore'))
            except Exception:
                pass
    html = ''.join(chunks)
    if not html:
        return {"system": "bdmijg", "siteKey": key, "error": "empty_html"}
    pairs = re.findall(r"(\d{3})期[：:]([^\s【】<>「」]{2,14})【([^】]{0,60})】", html)
    counts = {}
    for iss, name, val in pairs:
        if '更新' in name or '更新' in val:
            continue
        counts[iss] = counts.get(iss, 0) + 1
    target = target_issue or max((int(k) for k in counts), default=0)
    cols = {}
    for iss, name, val in pairs:
        if int(iss) != target:
            continue
        name = name.strip()
        if '更新' in name or '更新' in val or '發' in val:
            continue
        if name in cols:
            continue
        cols[name] = {"value": val.strip(), "parts": [val.strip()], "ruleId": None, "widgetId": None}
    if not cols:
        return {"system": "bdmijg", "siteKey": key, "issue": target, "error": "no_cols"}
    return {"system": "bdmijg", "siteKey": key, "issue": target, "columns": cols}


def repull(system, site_key, issue):
    """对掉站按体系重抓一次，返回站点结果（成功带 columns，失败带 error）"""
    if system.startswith('wanpz-'):
        return pull_wanpz(system, site_key)
    if system == 'bdmijg':
        return pull_bdmijg(site_key, issue)
    return {"system": system, "siteKey": site_key, "error": "unknown_system"}


def main():
    sites = json.load(open(os.path.join(BASE, 'all-sites-kill3.json')))
    wan = [(v['system'], str(v['siteKey'])) for v in sites.values() if str(v.get('system','')).startswith('wanpz-')]
    bd = [v['siteKey'] for v in sites.values() if v['system'] == 'bdmijg']
    from collections import Counter
    print('wanpz=' + str(len(wan)) + ' ' + str(dict(Counter(x[0] for x in wan))) + f' bdmijg={len(bd)}')

    results = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = {ex.submit(pull_wanpz, s, k): (s, k) for s, k in wan}
        for f, meta in futs.items():
            try:
                results.append(f.result())
            except Exception as e:
                results.append({"system": meta[0], "siteKey": meta[1], "error": str(e)})

    from collections import Counter
    iss_cnt = Counter(r.get('issue') for r in results if 'columns' in r)
    main_issue = iss_cnt.most_common(1)[0][0] if iss_cnt else 0

    with ThreadPoolExecutor(max_workers=5) as ex:
        futs2 = {ex.submit(pull_bdmijg, k, main_issue): ('bd', k) for k in bd}
        for f, meta in futs2.items():
            try:
                results.append(f.result())
            except Exception as e:
                results.append({"system": meta[0], "siteKey": meta[1], "error": str(e)})

    # 名单内但本轮既未成功也未报错的站，补记为 not_submitted，避免静默丢站
    listed = {f"{s}-{k}": (s, k) for s, k in wan}
    listed.update({f"bdmijg-{k}": ("bdmijg", k) for k in bd})
    have = {f"{r['system']}-{r['siteKey']}" for r in results}
    for lk, (sysname, sk) in listed.items():
        if lk not in have:
            results.append({"system": sysname, "siteKey": sk, "error": "not_submitted"})

    now = datetime.now()
    issue = main_issue or max((r.get('issue', 0) for r in results if 'columns' in r), default=0)

    # 基准：同一期、成功站数最多的一份快照（不含 -raw 留档）。
    # 不按时间最近取——最近一轮可能本身残缺；对齐同期最完整版，保证本轮不低于最佳水平；只补同期，不跨期。
    snap_dir = os.path.join(BASE, 'snapshots')
    today = now.strftime('%Y-%m-%d')
    existing = [g for g in glob.glob(os.path.join(snap_dir, f"snapshot-{issue}-*.json"))
                if '-raw' not in os.path.basename(g)]
    prev_path, prev_snap = None, None
    prev_ok, prev_same_day = {}, False
    best_n = -1
    for g in sorted(existing):
        try:
            cand = json.load(open(g, encoding='utf-8'))
        except Exception:
            continue
        if int(cand.get('issue', 0) or 0) != issue:
            continue
        # 只按同一期判断；同一期可能跨午夜，不能因为自然日变了就不兜底。
        # 期号变化后旧期自然被排除，不会跨期补。
        ok_n = sum(1 for v in (cand.get('sites') or {}).values() if 'columns' in v)
        if ok_n > best_n:
            best_n, prev_path, prev_snap = ok_n, g, cand
    if prev_snap:
        prev_ok = {k: v for k, v in (prev_snap.get('sites') or {}).items() if 'columns' in v}
        prev_same_day = True

    cur_ok = {f"{r['system']}-{r['siteKey']}": r for r in results if 'columns' in r}
    dropped = [k for k in prev_ok if k not in cur_ok] if prev_same_day else []

    # 规矩一：掉站先重试，直到覆盖不低于上一版，或达到重试上限
    retry_rounds = 0
    carried = []
    if dropped:
        for _ in range(RETRY_ROUNDS):
            if not dropped:
                break
            retry_rounds += 1
            still = []
            for k in dropped:
                ps = prev_ok[k]
                res = repull(ps.get('system'), str(ps.get('siteKey')), issue)
                if 'columns' in res:
                    results.append(res)
                    cur_ok[k] = res
                else:
                    still.append(k)
            dropped = still
            if dropped:
                time.sleep(RETRY_GAP)
        # 规矩二：重试仍缺的站，沿用当天上一版的票兜底（标注 carry，跨期不补）
        for k in dropped:
            ps = dict(prev_ok[k])
            ps['carry'] = True
            ps['carryFrom'] = os.path.basename(prev_path)
            results.append(ps)
            cur_ok[k] = ps
            carried.append(k)

    # 规矩三：站还在、但本轮栏目比上一版少，按栏目并集补齐；后到的有效值可覆盖，
    # 空栏不能覆盖早先的有效值。这样“站没掉、栏目掉了”也不会把票数打回去。
    merged_columns = []
    if prev_same_day:
        for k, ps in prev_ok.items():
            cur = cur_ok.get(k)
            if not cur or 'columns' not in cur:
                continue
            old_cols = ps.get('columns') or {}
            cur_cols = cur.get('columns') or {}
            filled = []
            for cname, cd in old_cols.items():
                old_has = bool(cd.get('value')) or bool(cd.get('parts'))
                cur_has = bool((cur_cols.get(cname) or {}).get('value')) or bool((cur_cols.get(cname) or {}).get('parts'))
                if old_has and not cur_has:
                    cur_cols[cname] = cd
                    filled.append(cname)
            if filled:
                cur['columns'] = cur_cols
                cur['mergedColumns'] = sorted(set(cur.get('mergedColumns') or []) | set(filled))
                merged_columns.append(k)

    ok = [r for r in results if 'columns' in r]
    for r in ok:
        attach_site_name(r)
    bad = [r for r in results if 'error' in r]
    print(f'成功 {len(ok)} 站, 失败 {len(bad)} 站, 重试 {retry_rounds} 轮, 沿用兜底 {len(carried)} 站')
    for b in bad:
        print('  FAIL', b['system'], b['siteKey'], b['error'])
    for k in carried:
        print('  CARRY', k, '<-', os.path.basename(prev_path))

    snap = {
        "generated_at": now.strftime('%Y-%m-%d %H:%M:%S'),
        "issue": issue,
        "hourly_hash": hourly_hash(),
        "prev_snapshot": os.path.basename(prev_path) if prev_path else None,
        "retry_rounds": retry_rounds,
        "carried": carried,
        "carried_count": len(carried),
        "merged_columns": merged_columns,
        "merged_columns_count": len(merged_columns),
        "sites": {f"{r['system']}-{r['siteKey']}": r for r in ok},
        "failed": [f"{b['system']}-{b['siteKey']}:{b['error']}" for b in bad],
    }
    os.makedirs(os.path.join(BASE, 'snapshots'), exist_ok=True)
    path = os.path.join(BASE, 'snapshots', f"snapshot-{issue}-{now.strftime('%H%M')}.json")
    json.dump(snap, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('SNAPSHOT', path)
    return path


if __name__ == '__main__':
    main()
