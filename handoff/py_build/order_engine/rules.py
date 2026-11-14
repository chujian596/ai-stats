# -*- coding: utf-8 -*-
"""单一真源：产品表、波色、生肖、AI 词表。全部从 products.json 导出，禁止手抄。"""
import json, pathlib

BASE = pathlib.Path(__file__).parent
try:
    from .rules_data import PRODUCTS          # APK 内用内联数据（不依赖外部文件）
except Exception:
    PRODUCTS = json.loads((BASE / "products.json").read_text(encoding="utf-8"))

RED   = {1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46}
BLUE  = {3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48}
GREEN = {5,6,11,16,17,21,22,27,28,32,33,38,39,43,44,49}

ZODIAC = {
 "马":[1,13,25,37,49], "蛇":[2,14,26,38], "龙":[3,15,27,39], "兔":[4,16,28,40],
 "虎":[5,17,29,41],    "牛":[6,18,30,42], "鼠":[7,19,31,43], "猪":[8,20,32,44],
 "狗":[9,21,33,45],    "鸡":[10,22,34,46],"猴":[11,23,35,47],"羊":[12,24,36,48]}

ZODIAC_CHARS = "马蛇龙兔虎牛鼠猪狗鸡猴羊"

# AI 合法词表：从产品表自动导出，不许手写
PLAY_VOCAB = [k for k in PRODUCTS if not k.isdigit()]

COLOR = {"红波":"#c0392b", "蓝波":"#2471a3", "绿波":"#1e8449"}

def color_of(n):
    n = int(n)
    if n in RED: return "红波"
    if n in BLUE: return "蓝波"
    if n in GREEN: return "绿波"
    return ""

def play_exists(name):
    return name in PRODUCTS
