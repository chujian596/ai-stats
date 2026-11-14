# -*- coding: utf-8 -*-
"""订单解析引擎：先抽号码序列，再抽玩法，最后抽金额。

核心原则（踩过的坑，不许改回去）：
1. 号码序列整体吃掉，绝不参与金额判定 —— 05.17 是 05 和 17，不是 5.17 元
2. 行首「特/各」后面紧跟的数字是号码，不是金额
3. 号码抽完，剩下的数字才是金额
4. 汇总行（共XX米）跳过，不重复计钱
5. 金额摊法有歧义 → 必须返回 need_confirm，不许自己猜
"""
import re
from . import rules

# ---------- 中文数字 ----------
_CN = {"零":0,"一":1,"二":2,"两":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9}
_CN_UNIT = {"十":10,"百":100,"千":1000}

def cn2int(s):
    """十 / 十五 / 二十 / 一百 → int"""
    if s.isdigit():
        return int(s)
    total, cur = 0, 0
    for ch in s:
        if ch in _CN:
            cur = _CN[ch]
        elif ch in _CN_UNIT:
            total += (cur or 1) * _CN_UNIT[ch]
            cur = 0
        else:
            return 0
    return total + cur

# ---------- 预处理 ----------
_FULL2HALF = {ord(k): v for k, v in zip("０１２３４５６７８９．－／，：、", "0123456789.-/,:、")}

SUMMARY_RE = re.compile(r"(共|合计|合计|总计|共计)")
HAS_DIGIT = re.compile(r"[0-9]|[零一二两三四五六七八九十百千]")

def preprocess(text):
    """按行切分并清理：标题行走掉、汇总行走掉、特字折叠、玩法归一。"""
    lines = []
    for raw in text.replace("\r", "").split("\n"):
        ln = raw.translate(_FULL2HALF).strip()
        if not ln:
            continue
        # 标题/说明行：既没有数字也没有生肖 → 跳过
        if not HAS_DIGIT.search(ln) and not any(z in ln for z in rules.ZODIAC_CHARS):
            continue
        # 汇总行：共 / 合计，且不含「各」→ 跳过
        if SUMMARY_RE.search(ln) and "各" not in ln:
            continue
        # 特号/特碼/特码 → 特；连续特折叠
        ln = re.sub(r"特[号碼码]", "特", ln)
        ln = re.sub(r"特{2,}", "特", ln)
        # 裸单/双 → 单数/双数
        ln = re.sub(r"(?<![合数])单(?![双特])", "单数", ln)
        ln = re.sub(r"(?<![合数])双(?![双特])", "双数", ln)
        lines.append(ln)
    return lines

# ---------- 各要素抽取 ----------
NUM_SEQ = re.compile(r"(\d{1,2})((?:[.\-、/ ]+\d{1,2})+)")
SINGLE_NUM = re.compile(r"((?<=特)|(?<=平))?(?<![\d])(0?[1-9]|[1-4][0-9])\s*(?=各)")

MIDDLE_RE = re.compile(r"(三中三|三中二|二中二|二中三)")
LIAN_RES = [
    re.compile(r"(\w{1,2})连([^\d各连]{2,})"),   # 马连龙兔 / 平连龙虎
    re.compile(r"连肖([^\d各连]{2,})"),          # 连肖龙虎兔
    re.compile(r"([^\d各连]{2,})[二三]?连肖"),   # 龙虎兔三连肖
]
COLOR_RE = re.compile(r"(红波|蓝波|绿波|合数)")
ODDEVEN_RE = re.compile(r"(单数|双数|大|小)")
AMOUNT_RE = re.compile(
    r"(?:各[数额]?|每[号个]?)?\s*(\d{1,4}|[零一二两三四五六七八九十百千]{1,4})\s*(元|块|米|钱|个)?"
)
ZOD_RE = re.compile("(" + "|".join(rules.ZODIAC_CHARS) + ")")


def _strip(text, span_list):
    """把已识别的片段从文本里挖掉，避免互相干扰（号码绝不参与金额判定）。"""
    chars = list(text)
    for s, e in span_list:
        for i in range(s, min(e, len(chars))):
            chars[i] = " "
    return "".join(chars)


def parse_clause(clause):
    """解析一个最小子句 → dict"""
    info = {"nums": [], "zods": [], "middle": None, "lianxiao": False,
            "ping": False, "te": False, "color": None, "money": None,
            "has_ge": "各" in clause, "raw": clause}
    spans = []

    # 1) 中特词（先挖掉，否则「二」「三」会被当金额）
    m = MIDDLE_RE.search(clause)
    if m:
        info["middle"] = m.group(1)
        spans.append(m.span())

    # 2) 连肖
    rest_wo_mid = _strip(clause, spans)
    for cre in LIAN_RES:
        m = cre.search(rest_wo_mid)
        if m:
            seg = re.sub("[^" + rules.ZODIAC_CHARS + "]", "", m.group(0))
            if len(seg) >= 2:
                info["lianxiao"] = True
                info["zods"] = [c for c in seg]
                if "平" in clause:
                    info["ping"] = True
                spans.append(m.span())
                break

    # 3) 号码序列（整体吃掉）
    for m in NUM_SEQ.finditer(clause):
        parts = [p for p in re.split(r"[.\-、,，/ ]+", m.group(0)) if p]
        nums = [int(p) for p in parts]
        if len(nums) >= 2 and all(1 <= n <= 49 for n in nums):
            info["nums"].extend(nums)
            spans.append(m.span())
    if not info["nums"]:
        m = SINGLE_NUM.search(clause)
        if m:
            info["nums"] = [int(m.group(2))]
            spans.append(m.span())

    # 4) 生肖（连肖已经吃过就不重复）
    rest = _strip(clause, spans)
    if not info["lianxiao"]:
        zods = ZOD_RE.findall(rest)
        if zods:
            info["zods"] = zods

    # 5) 波色 / 单双 / 大小 / 合数 —— 拼成产品表里的完整玩法名
    info["color"] = _norm_play(rest)

    # 6) 金额：号码挖掉后，取带单位或最靠后的数字
    rest_amt = _strip(clause, spans)
    cands = []
    for m in AMOUNT_RE.finditer(rest_amt):
        v = cn2int(m.group(1))
        if v > 0:
            cands.append((bool(m.group(2)), v))   # (有单位, 值)
    if cands:
        with_unit = [v for u, v in cands if u]
        info["money"] = with_unit[-1] if with_unit else cands[-1][1]

    return info


def _amount_count(line):
    """数这一行里有几个「金额」（先把号码整体挖掉，避免把号码当金额）"""
    spans = []
    for m in NUM_SEQ.finditer(line):
        parts = [p for p in re.split(r"[.\-、,，/ ]+", m.group(0)) if p]
        nums = [int(p) for p in parts]
        if len(nums) >= 2 and all(1 <= n <= 49 for n in nums):
            spans.append(m.span())
    m0 = MIDDLE_RE.search(line)
    if m0:
        spans.append(m0.span())
    rest = _strip(line, spans)
    return len([m for m in AMOUNT_RE.finditer(rest) if cn2int(m.group(1)) > 0])


def _number_only(seg):
    """这一段是不是「纯号码段」（没有玩法词、没有金额单位）"""
    if re.search(r"各|每|元|块|米|钱|肖|波|单|双|中|连", seg):
        return False
    return bool(re.fullmatch(r"[0-9.\-、/ ]+", seg))


def split_into_bets(line):
    """逗号既可能是号码分隔，也可能是注的分隔。
       判据：纯号码段 → 并进下一段；含玩法/金额 → 独立成一注。"""
    parts = [p.strip() for p in re.split(r"[，,；;]", line) if p.strip()]
    groups, buf = [], ""
    for p in parts:
        buf = (buf + "." + p) if buf else p
        if _number_only(p):
            continue
        groups.append(buf)
        buf = ""
    if buf:
        groups.append(buf)
    return groups or [line]


def parse_line(line):
    """一行 → 若干 order / confirm / fail"""
    results = {"orders": [], "confirm": [], "fail": []}
    for g in split_into_bets(line):
        r = _classify(parse_clause(g))
        key = {"order": "orders", "confirm": "confirm", "fail": "fail"}[r["kind"]]
        results[key].append(r)
    return results


def _classify(info):
    nums, money, play = info["nums"], info["money"], "特"
    if info["ping"]:
        play = "平特"

    # 号码 + 中特词
    if info["middle"] and nums and money:
        units = len(nums) if info["middle"] == "三中三" else 1
        return {"kind": "order", "play": info["middle"], "nums": nums,
                "money": money, "units": units, "amount": money * units}

    # 号码注（「各10」= 每号各 10，不是摊法歧义）
    if nums and money:
        return {"kind": "order", "play": play, "nums": nums,
                "money": money, "units": len(nums), "amount": money * len(nums)}

    # 连肖：一注，金额即下单额
    if info["lianxiao"] and money:
        return {"kind": "order", "play": "平连" if info["ping"] else "连肖",
                "nums": [], "zods": info["zods"], "money": money,
                "units": 1, "amount": money}

    # 生肖：带「各」或平特 → 摊法有歧义，必须问人
    if info["zods"] and money:
        reason = "平特肖总额摊到号码还是每肖各下" if info["ping"] else "生肖总额摊到号码还是每肖首号"
        return {"kind": "confirm", "play": ("平特" if info["ping"] else "特") + info["zods"][0],
                "zods": info["zods"], "money": money, "reason": reason}

    # 波色 / 单双 / 大小 / 合数 → 摊法有歧义
    if info["color"] and money:
        return {"kind": "confirm", "play": info["color"], "money": money,
                "reason": "总额摊到该玩法全部号码，还是每个号码各下"}

    # 什么都认不出 → 给补救信息，绝不直接报错
    return {"kind": "fail", "raw": info["raw"], "nums": nums,
            "zods": info["zods"], "money": money,
            "reason": "缺金额" if not money else "认不出玩法"}


def _norm_play(rest):
    """把「绿波小单」这类口语拼成产品表里的标准名（绿波单小）。
       顺序：合数 → 波+单双+大小 → 波+单双 → 波+大小 → 波 → 单双 → 大小"""
    color = None
    for name in ("红波", "蓝波", "绿波"):
        if name in rest:
            color = name
    oe = "单" if "单" in rest else ("双" if "双" in rest else None)
    sz = "大" if "大" in rest else ("小" if "小" in rest else None)
    hs = "合数" in rest

    cands = []
    if hs and oe:            cands.append("合数" + oe)
    if color and oe and sz:  cands.append(color + oe + sz)
    if color and oe:         cands.append(color + oe)
    if color and sz:         cands.append(color + sz)
    if color:                cands.append(color)
    if oe:                   cands.append("单数" if oe == "单" else "双数")
    if sz:                   cands.append(sz)
    for c in cands:
        if c in rules.PRODUCTS:
            return c
    return cands[0] if cands else None


VERSION = "v58.38-Py"

def parse_text(text):
    """整段文本 → 一单"""
    orders, confirms, fails = [], [], []
    for line in preprocess(text):
        r = parse_line(line)
        orders.extend(r["orders"])
        confirms.extend(r["confirm"])
        fails.extend(r["fail"])

    if fails:
        return {"ok": False, "need_fix": fails, "need_confirm": confirms,
                "orders": [], "version": VERSION}
    if confirms:
        return {"ok": False, "need_confirm": confirms, "need_fix": [],
                "orders": [], "version": VERSION}
    if not orders:
        return {"ok": False, "need_fix": [{"raw": text, "reason": "整段没有可识别的订单"}],
                "need_confirm": [], "orders": [], "version": VERSION}

    total_amount = sum(o["amount"] for o in orders)
    all_codes = []
    total_qty = 0
    for o in orders:
        total_qty += o["units"]
        all_codes.extend(["%02d" % n for n in o["nums"]])
    return {"ok": True, "orders": orders, "need_confirm": [], "need_fix": [],
            "total_meter": total_amount, "total_numbers": total_qty,
            "codes": all_codes, "version": VERSION}
