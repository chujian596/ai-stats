# -*- coding: utf-8 -*-
"""双跑对比：同一批用例，网页版(JS) 与 App版(Python) 各跑一遍，逐条比对金额和号数。
用法：python3 dual_check.py <页面html> ; node /tmp/_cmp.js ; python3 dual_check.py --compare
"""
import sys, json, re

MODE = sys.argv[1].lstrip("-") if len(sys.argv) > 1 else "build"

if MODE == "compare":
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "handoff", "py_build"))
    from order_engine.parse import parse_text
    js = json.load(open("/tmp/js_result.json", encoding="utf-8"))
    golden = json.load(open("tests/cases_golden.json", encoding="utf-8"))
    diff, same = [], 0
    for j, g in zip(js, golden):
        py = parse_text(g["input"])
        if j["kind"] == "order":
            js_r = ("order", float(j["amount"]), int(j["qty"]))
            if py["ok"]:
                py_r = ("order", float(py["total_meter"]), int(py["total_numbers"]))
            else:
                py_r = (("confirm", None, None) if py["need_confirm"] else ("fail", None, None))
            same_case = (js_r == py_r)
        else:
            py_kind = "order" if py["ok"] else ("confirm" if py["need_confirm"] else "fail")
            js_r, py_r = (j["kind"], None, None), (py_kind, None, None)
            same_case = (j["kind"] == py_kind)
        if same_case:
            same += 1
        else:
            diff.append((g["name"], js_r, py_r))
    print("逐条对比：一致 %d / 不一致 %d（共 %d）" % (same, len(diff), len(js)))
    for n, a, b in diff:
        print("  差异 |%-18s| 网页版=%s  App版=%s" % (n, a, b))
    sys.exit(0)

f = sys.argv[1]
s = open(f, encoding="utf-8").read()

def grab(pat):
    m = re.search(pat, s)
    a = m.start(); d = 0; i = a
    while i < len(s):
        if s[i] == "{": d += 1
        elif s[i] == "}":
            d -= 1
            if d == 0: break
        i += 1
    return s[a:i + 1]

doSave = grab(r"function doSave\(")
parseLine = grab(r"function parseLine\(text\)")
fix = grab(r"function showFixDialog\(rawLine, msg\)")
i2 = s.index('return [{"code": "01"'); j2 = s.index(";", i2)
prods = s[i2 + len("return "):j2]
cases = json.load(open("tests/cases_golden.json", encoding="utf-8"))
case_list = [[c["name"], c["input"]] for c in cases]

pre = """
const window={}; const els={};
let _popupCount=0;
function _el(id){ if(!els[id]) els[id]={id:id,value:'',innerHTML:'',textContent:'',style:{},appendChild:function(){},remove:function(){},querySelector:function(){return {onclick:null,style:{}}},addEventListener:function(){}}; return els[id]; }
const document={getElementById:_el,createElement:function(){_popupCount++;return {style:{},innerHTML:'',appendChild:function(){},remove:function(){},querySelector:function(){return {onclick:null,style:{}}}}},body:{appendChild:function(){}},addEventListener:function(){}};
const localStorage={getItem:function(){return null;},setItem:function(){},removeItem:function(){}};
function myAlert(m){ console.log('[ALERT] '+m); } function prompt(){ return null; }
var orders=[],roster=[],storageOK=true,lastPrice=null,_texiaoChoice=null,mode='normal',pendingProduct=null;
function saveOrders(){} function saveRoster(){} function restoreIfNeeded(){} function renderAll(){} function switchTab(){} function exportBackup(){} function autoPayout(){}
const NUM2ZODIAC_REV={'马':[1,13,25,37,49],'蛇':[2,14,26,38],'龙':[3,15,27,39],'兔':[4,16,28,40],'虎':[5,17,29,41],'牛':[6,18,30,42],'鼠':[7,19,31,43],'猪':[8,20,32,44],'狗':[9,21,33,45],'鸡':[10,22,34,46],'猴':[11,23,35,47],'羊':[12,24,36,48]};
const products = """ + prods + """;
function toPriceNum(x){const n=parseFloat(x);if(!isNaN(n))return n;const cn={零:0,一:1,二:2,两:2,三:3,四:4,五:5,六:6,七:7,八:8,九:9};const m=String(x).match(/(十|[一二两三四五六七八九][千百十]?[一二两三四五六七八九]?十?[一二两三四五六七八九]?)/);if(!m)return 0;const t=m[1];let v=0,p=0;while(p<t.length){const c=t[p];if(cn[c]!==undefined){v+=cn[c];p++;}else if(c==='十'){v=(v||1)*10;p++;}else if(c==='百'){v*=100;p++;}else if(c==='千'){v*=1000;p++;}else p++;}return v||0;}
"""

tail = """

const CASES = """ + json.dumps(case_list, ensure_ascii=False) + """;
let ok=0, needConfirm=0, fail=0;
const RESULT=[];
for(let k=0;k<CASES.length;k++){
  const name=CASES[k][0], text=CASES[k][1];
  orders=[]; _popupCount=0; _texiaoChoice=null;
  let alertMsg='';
  const _oa = myAlert;
  myAlert = function(mm){ alertMsg = mm; };
  _el('input').value = text;
  let threw=null;
  try{ doSave(); }catch(e){ threw = e.message; }
  myAlert = _oa;
  if(orders.length > 0){
    ok++;
    RESULT.push({name:name, kind:'order', amount:orders[0].amount, qty:orders[0].qty});
  } else if(_popupCount > 0){
    needConfirm++;
    RESULT.push({name:name, kind:'confirm'});
  } else {
    fail++;
    RESULT.push({name:name, kind:'fail', msg:(alertMsg||threw||'')});
  }
}
console.log('网页版JS：一次过 '+ok+' / 需确认 '+needConfirm+' / 失败 '+fail);
require('fs').writeFileSync('/tmp/js_result.json', JSON.stringify(RESULT));
"""

runner = pre + "\n" + parseLine + "\n" + fix + "\n" + doSave + "\n" + tail
open("/tmp/_cmp.js", "w", encoding="utf-8").write(runner)
print("已生成 /tmp/_cmp.js")
